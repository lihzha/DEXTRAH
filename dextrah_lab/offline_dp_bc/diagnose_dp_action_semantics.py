"""Compare official DP predictions against dataset action-index semantics.

This diagnostic is intentionally bounded and offline. It does not train or
roll out. It answers whether an official Diffusion Policy checkpoint's returned
lowdim action sequence aligns best with dataset labels at the current row,
previous row, next row, or a future horizon offset.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from .analyze_policy_trace import POSITION_FEATURE_IDX
from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


ACTION_NAMES = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]
CONTACT_RELABEL_PHASE_ORDER = ("align_open", "close_hold", "lift")


def _phase_names(phase_ids: np.ndarray | None = None) -> list[str]:
    if phase_ids is not None:
        unique = set(int(v) for v in np.unique(phase_ids))
        if unique and unique.issubset(set(range(len(CONTACT_RELABEL_PHASE_ORDER)))):
            return list(CONTACT_RELABEL_PHASE_ORDER)
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _load_workspace(checkpoint: Path) -> Any:
    try:
        from diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace import (
            TrainDiffusionUnetLowdimWorkspace,
        )
    except Exception as exc:  # pragma: no cover - exercised without official DP.
        raise ImportError(
            "Official diffusion_policy is not importable. Add the official "
            "real-stanford/diffusion_policy checkout to PYTHONPATH."
        ) from exc
    return TrainDiffusionUnetLowdimWorkspace.create_from_checkpoint(str(checkpoint))


def _select_policy(workspace: Any, policy_source: str) -> tuple[Any, str]:
    has_ema = getattr(workspace, "ema_model", None) is not None
    if policy_source == "auto":
        if has_ema:
            return workspace.ema_model, "ema"
        return workspace.model, "model"
    if policy_source == "ema":
        if not has_ema:
            raise ValueError("policy_source=ema requested but the checkpoint has no ema_model")
        return workspace.ema_model, "ema"
    if policy_source == "model":
        return workspace.model, "model"
    raise ValueError(f"Unsupported policy_source {policy_source!r}")


def _episode_starts(episode_ends: np.ndarray) -> np.ndarray:
    return np.concatenate(([0], episode_ends[:-1])).astype(np.int64)


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    ep_idx = min(max(ep_idx, 0), int(episode_ends.shape[0] - 1))
    start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    end = int(episode_ends[ep_idx])
    return ep_idx, start, end


def _clipped_indices(start_idx: int, length: int, ep_start: int, ep_end: int) -> np.ndarray:
    return np.clip(np.arange(start_idx, start_idx + length, dtype=np.int64), ep_start, ep_end - 1)


def _obs_history_for_row(obs: np.ndarray, row_idx: int, episode_ends: np.ndarray, n_obs_steps: int) -> np.ndarray:
    _ep, ep_start, ep_end = _episode_for_row(row_idx, episode_ends)
    ids = _clipped_indices(int(row_idx) - n_obs_steps + 1, n_obs_steps, ep_start, ep_end)
    return obs[ids].astype(np.float32)


def _label_sequence(
    action: np.ndarray,
    row_idx: int,
    episode_ends: np.ndarray,
    *,
    start_offset: int,
    length: int,
) -> np.ndarray:
    _ep, ep_start, ep_end = _episode_for_row(row_idx, episode_ends)
    ids = _clipped_indices(int(row_idx) + int(start_offset), length, ep_start, ep_end)
    return action[ids].astype(np.float32)


def _first_matching_row(mask: np.ndarray, ep_start: int, ep_end: int) -> int | None:
    idx = np.flatnonzero(mask[int(ep_start) : int(ep_end)])
    if idx.size == 0:
        return None
    return int(ep_start + idx[0])


def _episode_reference_rows(
    action: np.ndarray,
    phase_ids: np.ndarray,
    episode_ends: np.ndarray,
    *,
    episode_index: int,
) -> list[tuple[str, int]]:
    names = _phase_names(phase_ids)
    phase_to_id = {name: idx for idx, name in enumerate(names)}
    starts = _episode_starts(episode_ends)
    if episode_index < 0 or episode_index >= int(episode_ends.shape[0]):
        raise ValueError(f"episode_index must be in [0, {episode_ends.shape[0]}), got {episode_index}")
    ep_start = int(starts[episode_index])
    ep_end = int(episode_ends[episode_index])
    if set(names) == set(CONTACT_RELABEL_PHASE_ORDER):
        refs: list[tuple[str, int | None]] = [
            ("episode_start", ep_start),
            ("first_align_open", _first_matching_row(phase_ids == phase_to_id["align_open"], ep_start, ep_end)),
            ("first_close_hold", _first_matching_row(phase_ids == phase_to_id["close_hold"], ep_start, ep_end)),
            ("first_negative_gripper", _first_matching_row(action[:, 6] < 0.0, ep_start, ep_end)),
            ("first_lift", _first_matching_row(phase_ids == phase_to_id["lift"], ep_start, ep_end)),
        ]
    else:
        refs = [
            ("episode_start", ep_start),
            (
                "first_go_to_pregrasp",
                _first_matching_row(phase_ids == phase_to_id["go_to_pre_grasp_pose"], ep_start, ep_end),
            ),
            (
                "first_pregrasp_to_grasp",
                _first_matching_row(phase_ids == phase_to_id["go_from_pre_grasp_to_grasp_pose"], ep_start, ep_end),
            ),
            ("first_negative_gripper", _first_matching_row(action[:, 6] < 0.0, ep_start, ep_end)),
            ("first_hard_close", _first_matching_row(action[:, 6] <= -0.9, ep_start, ep_end)),
            ("first_lift", _first_matching_row(phase_ids == phase_to_id["lift_object"], ep_start, ep_end)),
        ]
    out: list[tuple[str, int]] = []
    seen: set[int] = set()
    for label, idx in refs:
        if idx is None or idx in seen:
            continue
        out.append((label, int(idx)))
        seen.add(int(idx))
    return out


def _spread_rows(candidates: np.ndarray, count: int) -> np.ndarray:
    candidates = np.asarray(candidates, dtype=np.int64)
    if candidates.size == 0 or count <= 0:
        return np.empty((0,), dtype=np.int64)
    if candidates.size <= count:
        return candidates
    take = np.linspace(0, candidates.size - 1, num=count, dtype=np.int64)
    return candidates[take]


def _selector_rows(
    obs: np.ndarray,
    action: np.ndarray,
    phase_ids: np.ndarray,
    *,
    selector: str,
    count: int,
) -> np.ndarray:
    names = _phase_names(phase_ids)
    phase_to_id = {name: idx for idx, name in enumerate(names)}
    if selector == "first":
        candidates = np.arange(obs.shape[0], dtype=np.int64)
    elif selector == "gripper_open":
        candidates = np.flatnonzero(action[:, 6] > 0.5)
    elif selector == "gripper_closed":
        candidates = np.flatnonzero(action[:, 6] < -0.5)
    elif selector == "lift_high":
        closed = action[:, 6] < -0.5
        lift_name = "lift" if "lift" in phase_to_id else "lift_object"
        lift_phase = phase_ids == phase_to_id[lift_name]
        candidates = np.flatnonzero(closed & lift_phase)
        if candidates.size == 0:
            candidates = np.flatnonzero(closed)
        if candidates.size:
            order = np.argsort(obs[candidates, 2], kind="stable")
            candidates = candidates[order]
    else:
        raise ValueError(f"Unsupported row selector {selector!r}")
    return _spread_rows(candidates, count)


def _nearest_dataset_row(obs: np.ndarray, query_obs: np.ndarray) -> tuple[int, float]:
    std = np.maximum(obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4)
    dist = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - query_obs[POSITION_FEATURE_IDX]) / std) ** 2).mean(axis=1))
    idx = int(np.argmin(dist))
    return idx, float(dist[idx])


def _live_trace_records(trace_path: Path, *, max_records: int) -> list[tuple[str, dict[str, Any]]]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    records = trace["policy_calls"]
    selected: list[tuple[str, dict[str, Any]]] = []

    def add(label: str, idx: int | None) -> None:
        if idx is None:
            return
        idx = min(max(int(idx), 0), len(records) - 1)
        record = records[idx]
        if any(int(existing["policy_call_index"]) == int(record["policy_call_index"]) for _, existing in selected):
            return
        selected.append((label, record))

    neg_idx = next((i for i, r in enumerate(records) if float(r["first_action"][6]) < 0.0), None)
    hard_idx = next((i for i, r in enumerate(records) if float(r["first_action"][6]) <= -0.9), None)
    width_idx = next((i for i, r in enumerate(records) if float(r["lowdim_obs"][20]) < 0.01), None)
    add("live_start", 0)
    add("live_first_negative", neg_idx)
    add("live_first_hard_close", hard_idx)
    add("live_width_lt_1cm", width_idx)
    add("live_final", len(records) - 1)
    return selected[:max_records]


def _mse_by_offsets(
    pred: np.ndarray,
    action: np.ndarray,
    row_idx: int,
    episode_ends: np.ndarray,
    *,
    offsets: list[int],
) -> tuple[dict[int, dict[str, float]], int]:
    out: dict[int, dict[str, float]] = {}
    for offset in offsets:
        label = _label_sequence(action, row_idx, episode_ends, start_offset=offset, length=pred.shape[0])
        diff = pred - label
        out[int(offset)] = {
            "mse_all": float(np.mean(diff**2)),
            "mse_pose": float(np.mean(diff[:, :6] ** 2)),
            "mse_gripper": float(np.mean(diff[:, 6:] ** 2)),
            "first_l2_all": float(np.linalg.norm(diff[0])),
            "first_l2_pose": float(np.linalg.norm(diff[0, :6])),
            "first_gripper_error": float(diff[0, 6]),
            "label_first_gripper": float(label[0, 6]),
        }
    best_offset = min(out, key=lambda key: out[key]["mse_all"])
    return out, int(best_offset)


def _flatten_offset_metrics(prefix: str, metrics: dict[int, dict[str, float]]) -> dict[str, float]:
    flat: dict[str, float] = {}
    for offset, values in metrics.items():
        for key, value in values.items():
            flat[f"{prefix}_offset_{offset}_{key}"] = value
    return flat


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _phase_or_selector_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["source"] == "selector":
            key = f"selector:{row['selector']}"
        elif row["source"] == "demo":
            key = f"demo:{row['phase']}"
        else:
            key = str(row["source"])
        groups.setdefault(key, []).append(row)
    return groups


def _write_channel_stats(path: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stat_rows: list[dict[str, Any]] = []
    for group, group_rows in _phase_or_selector_groups(rows).items():
        pred = np.asarray([row["pred_first_action"] for row in group_rows], dtype=float)
        label = np.asarray([row["label_t_action"] for row in group_rows], dtype=float)
        if pred.ndim != 2 or label.ndim != 2:
            continue
        for action_idx, name in enumerate(ACTION_NAMES):
            diff = pred[:, action_idx] - label[:, action_idx]
            stat_rows.append(
                {
                    "group": group,
                    "action_index": action_idx,
                    "action_name": name,
                    "count": int(pred.shape[0]),
                    "label_min": float(np.min(label[:, action_idx])),
                    "label_mean": float(np.mean(label[:, action_idx])),
                    "label_max": float(np.max(label[:, action_idx])),
                    "pred_min": float(np.min(pred[:, action_idx])),
                    "pred_mean": float(np.mean(pred[:, action_idx])),
                    "pred_max": float(np.max(pred[:, action_idx])),
                    "mae": float(np.mean(np.abs(diff))),
                    "mse": float(np.mean(diff**2)),
                    "sign_match_fraction": (
                        float(np.mean(np.sign(pred[:, action_idx]) == np.sign(label[:, action_idx])))
                        if action_idx == 6
                        else None
                    ),
                }
            )
    _write_csv(path, stat_rows)
    return stat_rows


def _plot_gripper_distributions(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    groups = _phase_or_selector_groups(rows)
    labels = list(groups.keys())
    x = np.arange(len(labels))
    fig, axes = plt.subplots(2, 1, figsize=(max(11.0, len(labels) * 0.75), 8.0), constrained_layout=True)
    pred_data = [np.asarray([r["pred_first_gripper"] for r in groups[label]], dtype=float) for label in labels]
    label_data = [np.asarray([r["label_t_gripper"] for r in groups[label]], dtype=float) for label in labels]

    axes[0].boxplot(label_data, positions=x - 0.18, widths=0.28, patch_artist=True)
    axes[0].boxplot(pred_data, positions=x + 0.18, widths=0.28, patch_artist=True)
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_title("First Returned Gripper: Label vs Official DP Prediction")
    axes[0].set_ylabel("-1 close / +1 open")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    axes[0].grid(True, alpha=0.25)
    axes[0].text(0.01, 0.95, "left boxes: labels; right boxes: predictions", transform=axes[0].transAxes, fontsize=8)

    sign_match = []
    for label in labels:
        pred = np.asarray([r["pred_first_gripper"] for r in groups[label]], dtype=float)
        target = np.asarray([r["label_t_gripper"] for r in groups[label]], dtype=float)
        sign_match.append(float(np.mean(np.sign(pred) == np.sign(target))))
    axes[1].bar(x, sign_match, color="tab:green")
    axes[1].set_ylim(0.0, 1.0)
    axes[1].set_title("Gripper Sign Match Fraction")
    axes[1].set_ylabel("fraction")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    axes[1].grid(True, alpha=0.25)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_per_channel_first_action(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pred = np.asarray([row["pred_first_action"] for row in rows], dtype=float)
    label = np.asarray([row["label_t_action"] for row in rows], dtype=float)
    fig, axes = plt.subplots(2, 4, figsize=(16.0, 7.0), constrained_layout=True)
    for idx, ax in enumerate(axes.flat[: len(ACTION_NAMES)]):
        ax.scatter(label[:, idx], pred[:, idx], s=18, alpha=0.7)
        lo = float(min(np.min(label[:, idx]), np.min(pred[:, idx])))
        hi = float(max(np.max(label[:, idx]), np.max(pred[:, idx])))
        if abs(hi - lo) < 1.0e-6:
            lo -= 1.0
            hi += 1.0
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=0.8)
        ax.axhline(0.0, color="gray", linewidth=0.5)
        ax.axvline(0.0, color="gray", linewidth=0.5)
        ax.set_title(f"a[{idx}] {ACTION_NAMES[idx]}")
        ax.set_xlabel("label")
        ax.set_ylabel("pred")
        ax.grid(True, alpha=0.25)
    axes.flat[-1].axis("off")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _normalizer_summary(policy: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    normalizer = getattr(policy, "normalizer", None)
    if normalizer is None:
        return {"available": False}
    summary["available"] = True
    try:
        action_norm = normalizer["action"]
        params = action_norm.params_dict
        summary["action_scale"] = params["scale"].detach().cpu().numpy().astype(float).tolist()
        summary["action_offset"] = params["offset"].detach().cpu().numpy().astype(float).tolist()
        input_stats = params["input_stats"]
        summary["action_input_min"] = input_stats["min"].detach().cpu().numpy().astype(float).tolist()
        summary["action_input_max"] = input_stats["max"].detach().cpu().numpy().astype(float).tolist()
        summary["action_input_mean"] = input_stats["mean"].detach().cpu().numpy().astype(float).tolist()
        summary["action_input_std"] = input_stats["std"].detach().cpu().numpy().astype(float).tolist()
    except Exception as exc:  # pragma: no cover - depends on official normalizer internals.
        summary["error"] = repr(exc)
    return summary


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = [row["sample"] for row in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(3, 1, figsize=(max(11.0, len(rows) * 0.55), 10.0), constrained_layout=True)
    axes[0].bar(x - 0.15, [row["returned_best_offset"] for row in rows], width=0.3, label="returned action best offset")
    axes[0].bar(x + 0.15, [row["full_best_offset"] for row in rows], width=0.3, label="full horizon best offset")
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_title("Best Label Offset By Sequence MSE")
    axes[0].set_ylabel("offset steps")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(x, [row["returned_offset_0_mse_all"] for row in rows], marker="o", label="returned vs a[t:t+8]")
    axes[1].plot(x, [row["returned_best_mse_all"] for row in rows], marker="o", label="returned best offset")
    axes[1].set_title("Returned Action Sequence MSE")
    axes[1].set_ylabel("MSE")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(x, [row["pred_first_gripper"] for row in rows], marker="o", label="pred first gripper")
    axes[2].plot(x, [row["label_t_gripper"] for row in rows], marker="o", label="label a[t] gripper")
    axes[2].plot(x, [row["label_t_plus_1_gripper"] for row in rows], marker="o", label="label a[t+1] gripper")
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_title("First-Step Gripper")
    axes[2].set_ylabel("-1 close / +1 open")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.25)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    dataset_path = Path(args.dataset).expanduser().resolve()
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    names = _phase_names(phase_ids)

    workspace = _load_workspace(checkpoint)
    policy, resolved_policy_source = _select_policy(workspace, str(args.policy_source))
    policy.num_inference_steps = int(args.num_inference_steps)
    policy.to(torch.device(args.device))
    policy.eval()
    n_obs_steps = int(policy.n_obs_steps)
    n_action_steps = int(policy.n_action_steps)
    horizon = int(policy.horizon)
    start_index = n_obs_steps - 1 if bool(getattr(policy, "oa_step_convention", False)) else n_obs_steps

    samples: list[dict[str, Any]] = []
    for label, row_idx in _episode_reference_rows(
        action, phase_ids, episode_ends, episode_index=int(args.episode_index)
    ):
        samples.append(
            {
                "sample": f"demo_{label}",
                "source": "demo",
                "selector": None,
                "row_idx": int(row_idx),
                "obs_seq": _obs_history_for_row(obs, int(row_idx), episode_ends, n_obs_steps),
                "trace_first_action": None,
                "nearest_distance": 0.0,
            }
        )
    for selector in args.row_selector:
        for row_idx in _selector_rows(
            obs,
            action,
            phase_ids,
            selector=str(selector),
            count=int(args.samples_per_selector),
        ):
            samples.append(
                {
                    "sample": f"selector_{selector}_{row_idx}",
                    "source": "selector",
                    "selector": str(selector),
                    "row_idx": int(row_idx),
                    "obs_seq": _obs_history_for_row(obs, int(row_idx), episode_ends, n_obs_steps),
                    "trace_first_action": None,
                    "nearest_distance": 0.0,
                }
            )
    for row_idx in args.row_index:
        samples.append(
            {
                "sample": f"demo_row_{row_idx}",
                "source": "demo",
                "selector": None,
                "row_idx": int(row_idx),
                "obs_seq": _obs_history_for_row(obs, int(row_idx), episode_ends, n_obs_steps),
                "trace_first_action": None,
                "nearest_distance": 0.0,
            }
        )
    for trace_path in args.trace:
        trace_name = Path(trace_path).parent.name
        for label, record in _live_trace_records(Path(trace_path), max_records=int(args.max_live_records_per_trace)):
            live_obs = np.asarray(record["lowdim_obs"], dtype=np.float32)
            nearest_idx, nearest_distance = _nearest_dataset_row(obs, live_obs)
            samples.append(
                {
                    "sample": f"{trace_name}:{label}",
                    "source": "live",
                    "selector": None,
                    "row_idx": int(nearest_idx),
                    "obs_seq": np.asarray(record["history_after_push"], dtype=np.float32),
                    "trace_first_action": np.asarray(record["first_action"], dtype=np.float32),
                    "nearest_distance": float(nearest_distance),
                    "trace_step": int(record["step"]),
                    "trace_policy_call_index": int(record["policy_call_index"]),
                }
            )

    rows: list[dict[str, Any]] = []
    offsets = [int(v) for v in args.offset]
    for sample_idx, sample in enumerate(samples):
        torch.manual_seed(int(args.seed) + sample_idx)
        obs_tensor = torch.as_tensor(sample["obs_seq"][None, ...], dtype=torch.float32, device=args.device)
        with torch.no_grad():
            result = policy.predict_action({"obs": obs_tensor})
        returned = result["action"][0].detach().cpu().numpy().astype(np.float32)
        full_pred = result["action_pred"][0].detach().cpu().numpy().astype(np.float32)
        row_idx = int(sample["row_idx"])
        ep_idx, ep_start, _ep_end = _episode_for_row(row_idx, episode_ends)
        local_idx = int(row_idx - ep_start)
        phase_id = int(phase_ids[row_idx])

        returned_metrics, returned_best_offset = _mse_by_offsets(
            returned, action, row_idx, episode_ends, offsets=offsets
        )
        full_metrics, full_best_offset = _mse_by_offsets(
            full_pred,
            action,
            row_idx - start_index,
            episode_ends,
            offsets=offsets,
        )
        label_t = _label_sequence(action, row_idx, episode_ends, start_offset=0, length=1)[0]
        label_t_plus_1 = _label_sequence(action, row_idx, episode_ends, start_offset=1, length=1)[0]
        record: dict[str, Any] = {
            "sample": sample["sample"],
            "source": sample["source"],
            "selector": sample.get("selector"),
            "row_idx": row_idx,
            "episode": ep_idx,
            "episode_step": local_idx,
            "phase": names[phase_id],
            "nearest_distance": float(sample["nearest_distance"]),
            "trace_step": sample.get("trace_step"),
            "trace_policy_call_index": sample.get("trace_policy_call_index"),
            "n_obs_steps": n_obs_steps,
            "n_action_steps": n_action_steps,
            "horizon": horizon,
            "policy_source": resolved_policy_source,
            "oa_step_convention": bool(getattr(policy, "oa_step_convention", False)),
            "official_return_start_index": start_index,
            "returned_best_offset": returned_best_offset,
            "full_best_offset": full_best_offset,
            "returned_best_mse_all": returned_metrics[returned_best_offset]["mse_all"],
            "full_best_mse_all": full_metrics[full_best_offset]["mse_all"],
            "pred_first_action": returned[0].astype(float).tolist(),
            "pred_first_gripper": float(returned[0, 6]),
            "label_t_action": label_t.astype(float).tolist(),
            "label_t_gripper": float(label_t[6]),
            "label_sign_group": "open_label" if float(label_t[6]) > 0.0 else "closed_label",
            "label_t_plus_1_action": label_t_plus_1.astype(float).tolist(),
            "label_t_plus_1_gripper": float(label_t_plus_1[6]),
            "obs_current_cube_minus_ee": sample["obs_seq"][-1, 14:17].astype(float).tolist(),
            "obs_current_gripper_width": float(sample["obs_seq"][-1, 20]),
        }
        if sample["trace_first_action"] is not None:
            trace_first = np.asarray(sample["trace_first_action"], dtype=np.float32)
            record["trace_first_action"] = trace_first.astype(float).tolist()
            record["trace_vs_requery_first_l2"] = float(np.linalg.norm(trace_first - returned[0]))
            record["trace_first_gripper"] = float(trace_first[6])
        record.update(_flatten_offset_metrics("returned", returned_metrics))
        record.update(_flatten_offset_metrics("full", full_metrics))
        rows.append(record)

    _write_csv(output_dir / "action_semantics_rows.csv", rows)
    channel_stats = _write_channel_stats(output_dir / "action_semantics_channel_stats.csv", rows)
    normalizer = _normalizer_summary(policy)
    open_rows = [row for row in rows if row["label_t_gripper"] > 0.0]
    closed_rows = [row for row in rows if row["label_t_gripper"] < 0.0]
    open_match = float(np.mean([row["pred_first_gripper"] > 0.0 for row in open_rows])) if open_rows else None
    closed_match = float(np.mean([row["pred_first_gripper"] < 0.0 for row in closed_rows])) if closed_rows else None
    gripper_gate_pass = bool(
        open_match is not None
        and closed_match is not None
        and open_match >= float(args.gripper_pass_fraction)
        and closed_match >= float(args.gripper_pass_fraction)
    )
    (output_dir / "action_semantics_summary.json").write_text(
        json.dumps(
            {
                "checkpoint": str(checkpoint),
                "dataset": str(dataset_path),
                "official_dp_source": str(args.diffusion_policy_root),
                "num_inference_steps": int(args.num_inference_steps),
                "requested_policy_source": str(args.policy_source),
                "resolved_policy_source": resolved_policy_source,
                "device": str(args.device),
                "seed": int(args.seed),
                "episode_index": int(args.episode_index),
                "offsets": offsets,
                "n_obs_steps": n_obs_steps,
                "n_action_steps": n_action_steps,
                "horizon": horizon,
                "oa_step_convention": bool(getattr(policy, "oa_step_convention", False)),
                "official_return_start_index": start_index,
                "action_dim_6_convention": "+1 open, -1 close",
                "normalizer": normalizer,
                "gripper_open_sign_match_fraction": open_match,
                "gripper_closed_sign_match_fraction": closed_match,
                "gripper_pass_fraction": float(args.gripper_pass_fraction),
                "gripper_gate_pass": gripper_gate_pass,
                "channel_stats": channel_stats,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _plot(rows, output_dir / "action_semantics_offsets.png")
    _plot_gripper_distributions(rows, output_dir / "gripper_label_vs_prediction.png")
    _plot_per_channel_first_action(rows, output_dir / "per_channel_first_action_scatter.png")
    report_lines = [
        "# DP Action Semantics Diagnostic",
        "",
        "No training or rollout was run. The script loaded the official Diffusion Policy checkpoint and compared predicted action sequences against dataset labels at multiple temporal offsets.",
        "",
        f"- Policy source queried: `{resolved_policy_source}` (requested `{args.policy_source}`)",
        f"- Official returned action start index: `{start_index}` (`oa_step_convention={bool(getattr(policy, 'oa_step_convention', False))}`)",
        f"- `n_obs_steps={n_obs_steps}`, `n_action_steps={n_action_steps}`, `horizon={horizon}`",
        f"- Episode sampled for exact demo windows: `{args.episode_index}`",
        "- DEXTRAH gripper convention: action dim 6 is `+1` open and `-1` close.",
        f"- Checkpoint action normalizer input dim 6 min/max: `{normalizer.get('action_input_min', [None] * 7)[6]}` / `{normalizer.get('action_input_max', [None] * 7)[6]}`",
        f"- Gripper sign match: open rows `{open_match}`, closed/lift rows `{closed_match}`, pass threshold `{args.gripper_pass_fraction}`.",
        f"- Gripper gate: `{'pass' if gripper_gate_pass else 'fail'}`.",
        "",
        "## Rows",
        "",
        "| sample | source | selector | phase | row | best returned offset | returned MSE@0 | returned best MSE | first pred grip | label a[t] grip | nearest dist |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['sample']} | {row['source']} | {row.get('selector')} | {row['phase']} | {row['row_idx']} | "
            f"{row['returned_best_offset']} | {row['returned_offset_0_mse_all']:.5f} | "
            f"{row['returned_best_mse_all']:.5f} | {row['pred_first_gripper']:.3f} | "
            f"{row['label_t_gripper']:.3f} | {row['nearest_distance']:.3f} |"
        )
    report_lines.extend(
        [
            "",
            "## Channel Summary",
            "",
            "| group | channel | label min/mean/max | pred min/mean/max | MAE | sign match |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    for stat in channel_stats:
        if stat["action_name"] != "gripper" and not bool(args.report_all_channels):
            continue
        report_lines.append(
            "| {group} | a[{idx}] {name} | {lmin:.3f}/{lmean:.3f}/{lmax:.3f} | "
            "{pmin:.3f}/{pmean:.3f}/{pmax:.3f} | {mae:.4f} | {sign} |".format(
                group=stat["group"],
                idx=stat["action_index"],
                name=stat["action_name"],
                lmin=stat["label_min"],
                lmean=stat["label_mean"],
                lmax=stat["label_max"],
                pmin=stat["pred_min"],
                pmean=stat["pred_mean"],
                pmax=stat["pred_max"],
                mae=stat["mae"],
                sign="" if stat["sign_match_fraction"] is None else f"{stat['sign_match_fraction']:.3f}",
            )
        )
    report_lines.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "- Returned best offset `0` means `policy.predict_action()['action'][0]` aligns best with dataset label `a[t]`, the intended eval convention.",
            "- Positive best offsets mean the policy output resembles future labels more than the current control label.",
            "- For live rows, the row index is the nearest training row under the same position/cube-relative features used by trace analysis, not a true time index.",
            "",
            "## Artifacts",
            "",
            f"- CSV: `{output_dir / 'action_semantics_rows.csv'}`",
            f"- Channel CSV: `{output_dir / 'action_semantics_channel_stats.csv'}`",
            f"- JSON: `{output_dir / 'action_semantics_summary.json'}`",
            f"- Plot: `{output_dir / 'action_semantics_offsets.png'}`",
            f"- Gripper plot: `{output_dir / 'gripper_label_vs_prediction.png'}`",
            f"- Per-channel plot: `{output_dir / 'per_channel_first_action_scatter.png'}`",
        ]
    )
    (output_dir / "action_semantics_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return {
        "output_dir": str(output_dir),
        "rows": len(rows),
        "plot": str(output_dir / "action_semantics_offsets.png"),
        "gripper_plot": str(output_dir / "gripper_label_vs_prediction.png"),
        "per_channel_plot": str(output_dir / "per_channel_first_action_scatter.png"),
        "report": str(output_dir / "action_semantics_report.md"),
        "csv": str(output_dir / "action_semantics_rows.csv"),
        "channel_csv": str(output_dir / "action_semantics_channel_stats.csv"),
        "gripper_gate_pass": gripper_gate_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--diffusion-policy-root", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--num-inference-steps", type=int, default=100)
    parser.add_argument("--policy-source", choices=["auto", "ema", "model"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--episode-index", type=int, default=29)
    parser.add_argument(
        "--row-selector",
        action="append",
        choices=["first", "gripper_open", "gripper_closed", "lift_high"],
        default=[],
        help="Add evenly spread dataset rows from this selector. Can be repeated.",
    )
    parser.add_argument("--samples-per-selector", type=int, default=24)
    parser.add_argument(
        "--gripper-pass-fraction",
        type=float,
        default=0.95,
        help="Required open/closed sign-match fraction for the offline gripper gate.",
    )
    parser.add_argument(
        "--report-all-channels",
        action="store_true",
        help="Include all channel stats in the markdown report instead of only gripper rows.",
    )
    parser.add_argument("--row-index", action="append", type=int, default=[])
    parser.add_argument("--trace", action="append", default=[])
    parser.add_argument("--max-live-records-per-trace", type=int, default=5)
    parser.add_argument("--offset", action="append", type=int, default=[-2, -1, 0, 1, 2, 4, 7])
    args = parser.parse_args()
    payload = diagnose(args)
    print("FRANKA_CUBE_DP_ACTION_SEMANTICS " + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
