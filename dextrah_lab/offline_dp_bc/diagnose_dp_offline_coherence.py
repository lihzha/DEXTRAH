"""Exhaustive offline coherence gate for Franka cube Diffusion Policy BC.

This diagnostic does not train and does not run Isaac. It loads an official
lowdim Diffusion Policy checkpoint, queries it on every valid converted dataset
history, and compares the returned action sequence against dataset labels by
phase. It is meant to answer whether a checkpoint emits coherent coupled pose
and gripper commands before any closed-loop rollout or RL handoff.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .diagnose_dp_action_semantics import (
    ACTION_NAMES,
    CONTACT_RELABEL_PHASE_NAME_BY_ID,
    CONTACT_RELABEL_PHASE_ORDER,
    _episode_for_row,
    _label_sequence,
    _load_workspace,
    _obs_history_for_row,
    _phase_name_for_id,
    _phase_names,
    _select_policy,
)


def _safe_mean(values: list[float]) -> float | None:
    finite = [float(v) for v in values if math.isfinite(float(v))]
    if not finite:
        return None
    return float(np.mean(finite))


def _safe_median(values: list[float]) -> float | None:
    finite = [float(v) for v in values if math.isfinite(float(v))]
    if not finite:
        return None
    return float(np.median(finite))


def _safe_quantile(values: list[float], q: float) -> float | None:
    finite = [float(v) for v in values if math.isfinite(float(v))]
    if not finite:
        return None
    return float(np.quantile(finite, q))


def _pose_cosine(pred: np.ndarray, label: np.ndarray, eps: float = 1.0e-8) -> float:
    pred_norm = float(np.linalg.norm(pred))
    label_norm = float(np.linalg.norm(label))
    if pred_norm < eps or label_norm < eps:
        return float("nan")
    return float(np.dot(pred, label) / (pred_norm * label_norm))


def _norm_ratio(pred: np.ndarray, label: np.ndarray, eps: float = 1.0e-8) -> float:
    label_norm = float(np.linalg.norm(label))
    if label_norm < eps:
        return float("nan")
    return float(np.linalg.norm(pred) / label_norm)


def _phase_ids_to_names(phase_ids: np.ndarray, phase_names: list[str]) -> list[str]:
    names: list[str] = []
    for phase_id in phase_ids:
        names.append(_phase_name_for_id(int(phase_id), phase_names, phase_ids))
    return names


def _phase_order(phase_ids: np.ndarray, phase_names: list[str]) -> list[str]:
    unique = []
    for name in _phase_ids_to_names(phase_ids, phase_names):
        if name not in unique:
            unique.append(name)
    preferred = [name for name in CONTACT_RELABEL_PHASE_ORDER if name in unique]
    preferred.extend(name for name in unique if name not in preferred)
    return preferred


def _batch_rows(
    obs: np.ndarray,
    row_indices: np.ndarray,
    episode_ends: np.ndarray,
    n_obs_steps: int,
) -> np.ndarray:
    return np.stack(
        [_obs_history_for_row(obs, int(row_idx), episode_ends, n_obs_steps) for row_idx in row_indices],
        axis=0,
    ).astype(np.float32)


def _best_offset_metrics(
    pred: np.ndarray,
    action: np.ndarray,
    row_idx: int,
    episode_ends: np.ndarray,
    offsets: list[int],
) -> tuple[int, dict[str, float]]:
    best_offset = 0
    best: dict[str, float] | None = None
    for offset in offsets:
        label = _label_sequence(action, row_idx, episode_ends, start_offset=int(offset), length=pred.shape[0])
        diff = pred - label
        metrics = {
            "sequence_mse_all": float(np.mean(diff**2)),
            "sequence_mse_pose": float(np.mean(diff[:, :6] ** 2)),
            "sequence_mse_gripper": float(np.mean(diff[:, 6:] ** 2)),
        }
        if best is None or metrics["sequence_mse_all"] < best["sequence_mse_all"]:
            best_offset = int(offset)
            best = metrics
    if best is None:
        raise RuntimeError("No offsets were evaluated")
    return best_offset, best


def _summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "pass": False}

    per_channel_mae: list[float] = []
    per_channel_rmse: list[float] = []
    for action_idx in range(len(ACTION_NAMES)):
        errors = np.asarray([float(row[f"first_error_{ACTION_NAMES[action_idx]}"]) for row in rows], dtype=np.float64)
        per_channel_mae.append(float(np.mean(np.abs(errors))))
        per_channel_rmse.append(float(np.sqrt(np.mean(errors**2))))

    best_offsets = [int(row["best_offset"]) for row in rows]
    offset_counts = {str(offset): int(best_offsets.count(offset)) for offset in sorted(set(best_offsets))}
    count = len(rows)
    best_offset_zero_fraction = float(best_offsets.count(0) / count)
    gripper_sign_fraction = float(np.mean([bool(row["gripper_sign_match"]) for row in rows]))
    pose_cosines = [float(row["first_pose_cosine"]) for row in rows]
    xyz_cosines = [float(row["first_xyz_cosine"]) for row in rows]
    pose_norm_ratios = [float(row["first_pose_norm_ratio"]) for row in rows]
    xyz_norm_ratios = [float(row["first_xyz_norm_ratio"]) for row in rows]
    first_mse_all = [float(row["offset0_sequence_mse_all"]) for row in rows]
    first_mse_pose = [float(row["offset0_sequence_mse_pose"]) for row in rows]
    offset0_mse_all_mean = _safe_mean(first_mse_all)
    max_pose_first_mae = float(max(per_channel_mae[:6]))

    # These thresholds are deliberately coarse. The point is to prevent
    # closed-loop claims when the offline action direction is already wrong.
    # Offset argmin alone is not a reliable gate on smooth trajectories because
    # nearby labels can be nearly identical; low absolute error is acceptable.
    pose_cosine_mean = _safe_mean(pose_cosines)
    xyz_cosine_mean = _safe_mean(xyz_cosines)
    pose_norm_median = _safe_median(pose_norm_ratios)
    offset_or_absolute_error_pass = bool(
        best_offset_zero_fraction >= 0.50
        or (offset0_mse_all_mean is not None and offset0_mse_all_mean <= 0.035 and max_pose_first_mae <= 0.20)
    )
    coherent = bool(
        gripper_sign_fraction >= 0.90
        and offset_or_absolute_error_pass
        and pose_cosine_mean is not None
        and pose_cosine_mean >= 0.35
        and pose_norm_median is not None
        and 0.25 <= pose_norm_median <= 4.0
    )

    return {
        "count": count,
        "pass": coherent,
        "best_offset_counts": offset_counts,
        "best_offset_zero_fraction": best_offset_zero_fraction,
        "offset_or_absolute_error_pass": offset_or_absolute_error_pass,
        "gripper_sign_match_fraction": gripper_sign_fraction,
        "first_pose_cosine_mean": pose_cosine_mean,
        "first_pose_cosine_median": _safe_median(pose_cosines),
        "first_pose_cosine_p10": _safe_quantile(pose_cosines, 0.10),
        "first_xyz_cosine_mean": xyz_cosine_mean,
        "first_xyz_cosine_median": _safe_median(xyz_cosines),
        "first_pose_norm_ratio_mean": _safe_mean(pose_norm_ratios),
        "first_pose_norm_ratio_median": pose_norm_median,
        "first_xyz_norm_ratio_mean": _safe_mean(xyz_norm_ratios),
        "first_xyz_norm_ratio_median": _safe_median(xyz_norm_ratios),
        "offset0_sequence_mse_all_mean": offset0_mse_all_mean,
        "offset0_sequence_mse_pose_mean": _safe_mean(first_mse_pose),
        "max_pose_first_mae": max_pose_first_mae,
        "per_channel_first_mae": {name: per_channel_mae[idx] for idx, name in enumerate(ACTION_NAMES)},
        "per_channel_first_rmse": {name: per_channel_rmse[idx] for idx, name in enumerate(ACTION_NAMES)},
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_phase_csv(path: Path, summary: dict[str, Any], phase_order: list[str]) -> None:
    rows: list[dict[str, Any]] = []
    for phase in phase_order + ["all"]:
        item = summary["phase_summaries"].get(phase)
        if item is None:
            continue
        row = {
            "phase": phase,
            "pass": bool(item["pass"]),
            "count": int(item["count"]),
            "best_offset_zero_fraction": item.get("best_offset_zero_fraction"),
            "gripper_sign_match_fraction": item.get("gripper_sign_match_fraction"),
            "first_pose_cosine_mean": item.get("first_pose_cosine_mean"),
            "first_pose_cosine_median": item.get("first_pose_cosine_median"),
            "first_xyz_cosine_mean": item.get("first_xyz_cosine_mean"),
            "first_pose_norm_ratio_median": item.get("first_pose_norm_ratio_median"),
            "offset0_sequence_mse_all_mean": item.get("offset0_sequence_mse_all_mean"),
            "offset0_sequence_mse_pose_mean": item.get("offset0_sequence_mse_pose_mean"),
            "max_pose_first_mae": item.get("max_pose_first_mae"),
            "offset_or_absolute_error_pass": item.get("offset_or_absolute_error_pass"),
            "best_offset_counts": json.dumps(item.get("best_offset_counts", {}), sort_keys=True),
        }
        for name, value in item.get("per_channel_first_mae", {}).items():
            row[f"mae_{name}"] = value
        rows.append(row)
    _write_csv(path, rows)


def _markdown(summary: dict[str, Any], phase_order: list[str]) -> str:
    lines = [
        "# DP Offline Coherence Gate",
        "",
        "No training or simulator rollout was run. This gate queries the official Diffusion Policy checkpoint on dataset histories and compares predictions to offline labels.",
        "",
        "## Verdict",
        "",
        f"- overall: `{'pass' if summary['pass'] else 'fail'}`",
        f"- checkpoint: `{summary['checkpoint']}`",
        f"- dataset: `{summary['dataset']}`",
        f"- policy source: `{summary['policy_source']}`",
        f"- rows scored: `{summary['rows_scored']}`",
        "",
        "## Phase Summary",
        "",
        "| phase | pass | count | offset0 frac | grip sign | pose cos mean | pose norm median | MSE@0 all | MAE dx/dy/dz/grip | best offsets |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for phase in phase_order + ["all"]:
        item = summary["phase_summaries"].get(phase)
        if item is None:
            continue
        mae = item.get("per_channel_first_mae", {})
        mae_text = "/".join(
            "n/a" if mae.get(name) is None else f"{float(mae[name]):.3f}"
            for name in ("dx", "dy", "dz", "gripper")
        )
        lines.append(
            f"| {phase} | {'pass' if item['pass'] else 'fail'} | {item['count']} | "
            f"{float(item.get('best_offset_zero_fraction', 0.0)):.3f} | "
            f"{float(item.get('gripper_sign_match_fraction', 0.0)):.3f} | "
            f"{item.get('first_pose_cosine_mean') if item.get('first_pose_cosine_mean') is not None else 'n/a'} | "
            f"{item.get('first_pose_norm_ratio_median') if item.get('first_pose_norm_ratio_median') is not None else 'n/a'} | "
            f"{item.get('offset0_sequence_mse_all_mean') if item.get('offset0_sequence_mse_all_mean') is not None else 'n/a'} | "
            f"{mae_text} | `{item.get('best_offset_counts', {})}` |"
        )
    lines.extend(
        [
            "",
            "## Gate Thresholds",
            "",
            "- gripper sign fraction >= 0.90",
            "- best offset 0 fraction >= 0.50, or offset-0 sequence MSE <= 0.035 with max pose-channel first-action MAE <= 0.20",
            "- mean 6D pose direction cosine >= 0.35",
            "- median 6D pose norm ratio in [0.25, 4.0]",
            "",
            "## Artifacts",
            "",
            f"- rows CSV: `{summary['rows_csv']}`",
            f"- phase CSV: `{summary['phase_csv']}`",
            f"- JSON: `{summary['json']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    dataset_path = Path(args.dataset).expanduser().resolve()
    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.diffusion_policy_root:
        root = str(Path(args.diffusion_policy_root).expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    if obs.ndim != 2 or action.ndim != 2:
        raise ValueError(f"Expected rank-2 obs/action, got {obs.shape} and {action.shape}")
    if obs.shape[0] != action.shape[0] or action.shape[1] != 7:
        raise ValueError(f"Unexpected obs/action shapes: {obs.shape}, {action.shape}")
    if phase_ids.shape[0] != obs.shape[0]:
        raise ValueError(f"phase_ids length mismatch: {phase_ids.shape} vs {obs.shape}")

    workspace = _load_workspace(checkpoint_path)
    policy, resolved_policy_source = _select_policy(workspace, str(args.policy_source))
    policy.num_inference_steps = int(args.num_inference_steps)
    policy.to(torch.device(args.device))
    policy.eval()
    n_obs_steps = int(policy.n_obs_steps)
    n_action_steps = int(policy.n_action_steps)
    phase_names = _phase_names(phase_ids)
    row_indices = np.arange(obs.shape[0], dtype=np.int64)
    offsets = [int(v) for v in args.offset]

    rows: list[dict[str, Any]] = []
    for batch_start in range(0, row_indices.shape[0], int(args.batch_size)):
        batch_rows = row_indices[batch_start : batch_start + int(args.batch_size)]
        obs_batch = _batch_rows(obs, batch_rows, episode_ends, n_obs_steps)
        torch.manual_seed(int(args.seed) + int(batch_start))
        with torch.no_grad():
            obs_tensor = torch.as_tensor(obs_batch, dtype=torch.float32, device=args.device)
            result = policy.predict_action({"obs": obs_tensor})
        pred = result["action"].detach().cpu().numpy().astype(np.float32)
        if pred.shape != (batch_rows.shape[0], n_action_steps, 7):
            raise RuntimeError(f"Unexpected action shape {pred.shape}; expected {(batch_rows.shape[0], n_action_steps, 7)}")
        for local_idx, row_idx_np in enumerate(batch_rows):
            row_idx = int(row_idx_np)
            phase_id = int(phase_ids[row_idx])
            phase = _phase_name_for_id(phase_id, phase_names, phase_ids)
            ep_idx, ep_start, _ep_end = _episode_for_row(row_idx, episode_ends)
            label = _label_sequence(action, row_idx, episode_ends, start_offset=0, length=n_action_steps)
            first_pred = pred[local_idx, 0]
            first_label = label[0]
            diff_first = first_pred - first_label
            diff_seq = pred[local_idx] - label
            best_offset, best = _best_offset_metrics(pred[local_idx], action, row_idx, episode_ends, offsets)
            record: dict[str, Any] = {
                "row_idx": row_idx,
                "episode": int(ep_idx),
                "episode_step": int(row_idx - ep_start),
                "phase": phase,
                "phase_id": phase_id,
                "best_offset": int(best_offset),
                "best_sequence_mse_all": best["sequence_mse_all"],
                "best_sequence_mse_pose": best["sequence_mse_pose"],
                "best_sequence_mse_gripper": best["sequence_mse_gripper"],
                "offset0_sequence_mse_all": float(np.mean(diff_seq**2)),
                "offset0_sequence_mse_pose": float(np.mean(diff_seq[:, :6] ** 2)),
                "offset0_sequence_mse_gripper": float(np.mean(diff_seq[:, 6:] ** 2)),
                "first_pose_l2": float(np.linalg.norm(diff_first[:6])),
                "first_xyz_l2": float(np.linalg.norm(diff_first[:3])),
                "first_pose_cosine": _pose_cosine(first_pred[:6], first_label[:6]),
                "first_xyz_cosine": _pose_cosine(first_pred[:3], first_label[:3]),
                "first_pose_norm_ratio": _norm_ratio(first_pred[:6], first_label[:6]),
                "first_xyz_norm_ratio": _norm_ratio(first_pred[:3], first_label[:3]),
                "pred_first_gripper": float(first_pred[6]),
                "label_first_gripper": float(first_label[6]),
                "gripper_sign_match": bool(np.sign(first_pred[6]) == np.sign(first_label[6])),
                "obs_gripper_width": float(obs[row_idx, 20]) if obs.shape[1] > 20 else None,
            }
            for action_idx, name in enumerate(ACTION_NAMES):
                record[f"pred_first_{name}"] = float(first_pred[action_idx])
                record[f"label_first_{name}"] = float(first_label[action_idx])
                record[f"first_error_{name}"] = float(diff_first[action_idx])
            rows.append(record)

    phase_order = _phase_order(phase_ids, phase_names)
    phase_summaries = {phase: _summarize_group([row for row in rows if row["phase"] == phase]) for phase in phase_order}
    phase_summaries["all"] = _summarize_group(rows)
    overall_pass = bool(phase_summaries["all"]["pass"] and all(item["pass"] for item in phase_summaries.values()))

    rows_csv = output_dir / "offline_coherence_rows.csv"
    phase_csv = output_dir / "offline_coherence_phase_summary.csv"
    json_path = output_dir / "offline_coherence_summary.json"
    report_path = output_dir / "offline_coherence_report.md"
    summary = {
        "checkpoint": str(checkpoint_path),
        "dataset": str(dataset_path),
        "output_dir": str(output_dir),
        "policy_source": resolved_policy_source,
        "requested_policy_source": str(args.policy_source),
        "num_inference_steps": int(args.num_inference_steps),
        "device": str(args.device),
        "seed": int(args.seed),
        "obs_shape": list(obs.shape),
        "action_shape": list(action.shape),
        "episode_ends": episode_ends.astype(int).tolist(),
        "n_obs_steps": n_obs_steps,
        "n_action_steps": n_action_steps,
        "horizon": int(policy.horizon),
        "rows_scored": len(rows),
        "offsets": offsets,
        "pass": overall_pass,
        "phase_summaries": phase_summaries,
        "rows_csv": str(rows_csv),
        "phase_csv": str(phase_csv),
        "json": str(json_path),
        "report": str(report_path),
    }
    _write_csv(rows_csv, rows)
    _write_phase_csv(phase_csv, summary, phase_order)
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=True) + "\n", encoding="utf-8")
    report_path.write_text(_markdown(summary, phase_order), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--diffusion-policy-root", default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--num-inference-steps", type=int, default=100)
    parser.add_argument("--policy-source", choices=["auto", "ema", "model"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--offset", action="append", type=int, default=[-2, -1, 0, 1, 2, 4, 7])
    args = parser.parse_args()
    summary = diagnose(args)
    print(
        "FRANKA_CUBE_DP_OFFLINE_COHERENCE "
        + json.dumps(
            {
                "output_dir": summary["output_dir"],
                "report": summary["report"],
                "phase_csv": summary["phase_csv"],
                "rows_csv": summary["rows_csv"],
                "pass": summary["pass"],
                "rows_scored": summary["rows_scored"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
