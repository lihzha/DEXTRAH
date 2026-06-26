"""Offline action-coherence diagnostic for YAM two-camera RGB Diffusion Policy.

This script does not run Isaac. It loads an official image Diffusion Policy
checkpoint, queries selected observations directly from the sharded YAM RGB
policy dataset, and compares returned actions against the shard labels.
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

ACTION_NAMES = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]
IMAGE_KEYS = ("scene_rgb", "wrist_rgb")


def _path_maps(raw: list[str]) -> list[tuple[str, str]]:
    maps: list[tuple[str, str]] = []
    for item in raw:
        if "=" not in item:
            raise ValueError(f"--path-map must be SRC=DST, got {item!r}")
        src, dst = item.split("=", 1)
        maps.append((src.rstrip("/"), dst.rstrip("/")))
    return maps


def _resolve_path(path: str, *, parent: Path, maps: list[tuple[str, str]]) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = parent / raw
    raw_s = str(raw)
    for src, dst in maps:
        if raw_s == src or raw_s.startswith(src + "/"):
            return Path(dst + raw_s[len(src) :]).expanduser().resolve()
    return raw.expanduser().resolve()


def _load_manifest(path: Path, maps: list[tuple[str, str]]) -> tuple[dict[str, Any], list[Path], list[int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("shards")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path} has no shards")
    shard_paths: list[Path] = []
    lengths: list[int] = []
    for row in rows:
        shard_paths.append(_resolve_path(str(row["path"]), parent=path.parent, maps=maps))
        lengths.append(int(row["num_steps"]))
    return payload, shard_paths, lengths


def _load_shard(path: Path) -> dict[str, np.ndarray]:
    if path.is_dir():
        out = {key: np.load(path / f"{key}.npy", mmap_mode="r", allow_pickle=False) for key in IMAGE_KEYS}
        out["robot_state"] = np.load(path / "robot_state.npy", mmap_mode="r", allow_pickle=False)
        out["action"] = np.load(path / "action.npy", mmap_mode="r", allow_pickle=False)
        return out
    if path.is_file():
        with np.load(path, allow_pickle=False) as data:
            return {key: np.asarray(data[key]) for key in (*IMAGE_KEYS, "robot_state", "action")}
    raise FileNotFoundError(path)


def _episode_for_global_row(row: int, lengths: list[int]) -> tuple[int, int]:
    cursor = 0
    for shard_idx, length in enumerate(lengths):
        end = cursor + int(length)
        if cursor <= row < end:
            return shard_idx, row - cursor
        cursor = end
    raise ValueError(f"Global row {row} out of range [0, {cursor})")


def _select_rows(args: argparse.Namespace, lengths: list[int]) -> list[tuple[int, int]]:
    selected: list[tuple[int, int]] = []
    selected.extend(_episode_for_global_row(int(row), lengths) for row in args.row)
    for shard_idx in args.shard:
        if shard_idx < 0 or shard_idx >= len(lengths):
            raise ValueError(f"Shard {shard_idx} is out of range for {len(lengths)} shards")
        for step in args.shard_step:
            step = int(step)
            if 0 <= step < int(lengths[shard_idx]):
                selected.append((int(shard_idx), step))
    if args.random_rows > 0:
        rng = np.random.default_rng(int(args.seed))
        total = int(sum(lengths))
        for row in rng.choice(np.arange(total, dtype=np.int64), size=int(args.random_rows), replace=False):
            selected.append(_episode_for_global_row(int(row), lengths))
    return sorted(set(selected))


def _image_history(image: np.ndarray, frame_ids: np.ndarray) -> np.ndarray:
    frames = np.asarray(image[frame_ids])
    if frames.shape[-1] == 3:
        frames = np.moveaxis(frames, -1, 1)
    elif frames.shape[1] != 3:
        raise ValueError(f"Expected NHWC or NCHW RGB, got {frames.shape}")
    frames = frames.astype(np.float32, copy=False)
    if frames.max(initial=0.0) > 1.0:
        frames = frames / 255.0
    return frames


def _history_for_row(shard: dict[str, np.ndarray], local_row: int, n_obs_steps: int) -> dict[str, np.ndarray]:
    length = int(shard["action"].shape[0])
    frame_ids = np.arange(local_row - (n_obs_steps - 1), local_row + 1, dtype=np.int64)
    frame_ids = np.clip(frame_ids, 0, length - 1)
    return {
        "scene_rgb": _image_history(shard["scene_rgb"], frame_ids),
        "wrist_rgb": _image_history(shard["wrist_rgb"], frame_ids),
        "robot_state": np.asarray(shard["robot_state"], dtype=np.float32)[frame_ids],
    }


def _label_for_row(shard: dict[str, np.ndarray], local_row: int, length: int) -> np.ndarray:
    action = np.asarray(shard["action"], dtype=np.float32)
    frame_ids = np.arange(local_row, local_row + int(length), dtype=np.int64)
    frame_ids = np.clip(frame_ids, local_row, int(action.shape[0]) - 1)
    return action[frame_ids].astype(np.float32, copy=False)


def _load_policy(checkpoint: Path, device: str, diffusion_policy_root: Path | None, policy_source: str):
    if diffusion_policy_root is not None:
        root = str(diffusion_policy_root.expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
    from diffusion_policy.workspace.train_diffusion_unet_image_workspace import TrainDiffusionUnetImageWorkspace

    workspace = TrainDiffusionUnetImageWorkspace.create_from_checkpoint(str(checkpoint))
    if policy_source == "ema":
        policy = workspace.ema_model
        resolved = "ema"
    elif policy_source == "model":
        policy = workspace.model
        resolved = "model"
    elif getattr(workspace, "ema_model", None) is not None:
        policy = workspace.ema_model
        resolved = "ema"
    else:
        policy = workspace.model
        resolved = "model"
    if policy is None:
        raise RuntimeError(f"Requested policy source {policy_source!r} is unavailable")
    policy.to(torch.device(device))
    policy.eval()
    return workspace, policy, resolved


def _cosine(a: np.ndarray, b: np.ndarray, eps: float = 1.0e-8) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm < eps or b_norm < eps:
        return float("nan")
    return float(np.dot(a, b) / (a_norm * b_norm))


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    out: dict[str, Any] = {"count": len(rows)}
    for key in (
        "first_mse_all",
        "first_mse_pose",
        "sequence_mse_all",
        "pred_first_pose_l2",
        "label_first_pose_l2",
        "pred_first_xyz_l2",
        "label_first_xyz_l2",
    ):
        values = np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        out[f"{key}_mean"] = float(np.mean(values))
        out[f"{key}_median"] = float(np.median(values))
    pred_pose = out["pred_first_pose_l2_mean"]
    label_pose = out["label_first_pose_l2_mean"]
    out["pose_l2_ratio_mean"] = float(pred_pose / label_pose) if label_pose > 0.0 else None
    pred_xyz = out["pred_first_xyz_l2_mean"]
    label_xyz = out["label_first_xyz_l2_mean"]
    out["xyz_l2_ratio_mean"] = float(pred_xyz / label_xyz) if label_xyz > 0.0 else None
    signs = np.asarray([bool(row["gripper_sign_match"]) for row in rows], dtype=bool)
    out["gripper_sign_match_fraction"] = float(np.mean(signs))
    for key in ("first_pose_cosine", "first_xyz_cosine"):
        values = np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        finite = values[np.isfinite(values)]
        out[f"{key}_mean"] = float(np.mean(finite)) if finite.size else None
    for action_idx, name in enumerate(ACTION_NAMES):
        pred = np.asarray([float(row[f"pred_first_{name}"]) for row in rows], dtype=np.float64)
        label = np.asarray([float(row[f"label_first_{name}"]) for row in rows], dtype=np.float64)
        out[f"pred_first_{name}_mean"] = float(np.mean(pred))
        out[f"label_first_{name}_mean"] = float(np.mean(label))
        out[f"first_mae_{name}"] = float(np.mean(np.abs(pred - label)))
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    manifest = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if not manifest.is_file():
        raise FileNotFoundError(manifest)

    maps = _path_maps(args.path_map)
    manifest_payload, shard_paths, lengths = _load_manifest(manifest, maps)
    workspace, policy, resolved_policy = _load_policy(
        checkpoint,
        str(args.device),
        Path(args.diffusion_policy_root) if args.diffusion_policy_root else None,
        str(args.policy_source),
    )
    policy.num_inference_steps = int(args.num_inference_steps)
    n_obs_steps = int(policy.n_obs_steps)
    n_action_steps = int(policy.n_action_steps)
    selected = _select_rows(args, lengths)
    if not selected:
        raise ValueError("No rows selected")

    records: list[dict[str, Any]] = []
    shard_cache: dict[int, dict[str, np.ndarray]] = {}
    for batch_start in range(0, len(selected), int(args.batch_size)):
        batch_rows = selected[batch_start : batch_start + int(args.batch_size)]
        histories: list[dict[str, np.ndarray]] = []
        labels: list[np.ndarray] = []
        for shard_idx, local_row in batch_rows:
            if shard_idx not in shard_cache:
                shard_cache[shard_idx] = _load_shard(shard_paths[shard_idx])
            shard = shard_cache[shard_idx]
            histories.append(_history_for_row(shard, local_row, n_obs_steps))
            labels.append(_label_for_row(shard, local_row, n_action_steps))
        obs = {
            "scene_rgb": np.stack([item["scene_rgb"] for item in histories], axis=0),
            "wrist_rgb": np.stack([item["wrist_rgb"] for item in histories], axis=0),
            "robot_state": np.stack([item["robot_state"] for item in histories], axis=0),
        }
        torch.manual_seed(int(args.seed) + batch_start)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(args.seed) + batch_start)
        with torch.inference_mode():
            result = policy.predict_action(
                {
                    key: torch.as_tensor(value, dtype=torch.float32, device=args.device)
                    for key, value in obs.items()
                }
            )
        pred_batch = result["action"].detach().cpu().numpy().astype(np.float32)
        for local_idx, (shard_idx, local_row) in enumerate(batch_rows):
            pred = pred_batch[local_idx]
            label = labels[local_idx]
            diff = pred - label
            first_pred = pred[0]
            first_label = label[0]
            global_row = int(sum(lengths[:shard_idx]) + local_row)
            record: dict[str, Any] = {
                "global_row": global_row,
                "shard": int(shard_idx),
                "shard_step": int(local_row),
                "shard_length": int(lengths[shard_idx]),
                "label_gripper_regime": "close" if float(first_label[6]) < 0.0 else "open",
                "sequence_mse_all": float(np.mean(diff**2)),
                "sequence_mse_pose": float(np.mean(diff[:, :6] ** 2)),
                "sequence_mse_gripper": float(np.mean(diff[:, 6:] ** 2)),
                "first_mse_all": float(np.mean(diff[0] ** 2)),
                "first_mse_pose": float(np.mean(diff[0, :6] ** 2)),
                "first_mse_gripper": float(np.mean(diff[0, 6:] ** 2)),
                "first_pose_cosine": _cosine(first_pred[:6], first_label[:6]),
                "first_xyz_cosine": _cosine(first_pred[:3], first_label[:3]),
                "pred_first_pose_l2": float(np.linalg.norm(first_pred[:6])),
                "label_first_pose_l2": float(np.linalg.norm(first_label[:6])),
                "pred_first_xyz_l2": float(np.linalg.norm(first_pred[:3])),
                "label_first_xyz_l2": float(np.linalg.norm(first_label[:3])),
                "gripper_sign_match": bool(np.sign(first_pred[6]) == np.sign(first_label[6])),
                "obs_gripper_width": float(histories[local_idx]["robot_state"][-1, -1]),
            }
            for action_idx, name in enumerate(ACTION_NAMES):
                record[f"pred_first_{name}"] = float(first_pred[action_idx])
                record[f"label_first_{name}"] = float(first_label[action_idx])
                record[f"first_error_{name}"] = float(first_pred[action_idx] - first_label[action_idx])
            records.append(record)

    by_regime = {
        regime: _summary([row for row in records if row["label_gripper_regime"] == regime])
        for regime in sorted({str(row["label_gripper_regime"]) for row in records})
    }
    payload = {
        "checkpoint": str(checkpoint),
        "manifest": str(manifest),
        "manifest_format": manifest_payload.get("format"),
        "num_shards": int(len(lengths)),
        "num_steps": int(sum(lengths)),
        "selected_rows": int(len(records)),
        "policy_source": resolved_policy,
        "workspace_class": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "n_obs_steps": n_obs_steps,
        "n_action_steps": n_action_steps,
        "horizon": int(policy.horizon),
        "num_inference_steps": int(policy.num_inference_steps),
        "rows": records,
        "summary": _summary(records),
        "summary_by_gripper_regime": by_regime,
    }
    rows_csv = output_dir / "yam_rgb_offline_coherence_rows.csv"
    json_path = output_dir / "yam_rgb_offline_coherence_summary.json"
    report_path = output_dir / "yam_rgb_offline_coherence_report.md"
    _write_csv(rows_csv, records)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=True) + "\n", encoding="utf-8")

    lines = [
        "# YAM RGB DP Offline Coherence",
        "",
        f"- checkpoint: `{checkpoint}`",
        f"- manifest: `{manifest}`",
        f"- policy: `{payload['policy_class']}` from `{resolved_policy}`",
        f"- rows scored: `{len(records)}`",
        f"- summary: `{json.dumps(payload['summary'], sort_keys=True, allow_nan=True)}`",
        "",
        "| shard | step | regime | seq mse | first mse | pose ratio | grip ok | first pred | first label |",
        "|---:|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in records:
        pred = [row[f"pred_first_{name}"] for name in ACTION_NAMES]
        label = [row[f"label_first_{name}"] for name in ACTION_NAMES]
        pred_s = ", ".join(f"{float(v):.3f}" for v in pred)
        label_s = ", ".join(f"{float(v):.3f}" for v in label)
        label_l2 = float(row["label_first_pose_l2"])
        pose_ratio = float(row["pred_first_pose_l2"]) / label_l2 if label_l2 > 0.0 else math.nan
        lines.append(
            f"| {row['shard']} | {row['shard_step']} | {row['label_gripper_regime']} | "
            f"{float(row['sequence_mse_all']):.5f} | {float(row['first_mse_all']):.5f} | "
            f"{pose_ratio:.3f} | {int(bool(row['gripper_sign_match']))} | "
            f"`{pred_s}` | `{label_s}` |"
        )
    lines.extend(["", "## Artifacts", "", f"- rows CSV: `{rows_csv}`", f"- JSON: `{json_path}`"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--diffusion-policy-root", default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--num-inference-steps", type=int, default=100)
    parser.add_argument("--policy-source", choices=["auto", "ema", "model"], default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--row", action="append", type=int, default=[])
    parser.add_argument("--shard", action="append", type=int, default=[0, 1, 37, 123, 250, 399])
    parser.add_argument("--shard-step", action="append", type=int, default=[0, 64, 128, 216, 251, 493, 775, 824])
    parser.add_argument("--random-rows", type=int, default=0)
    parser.add_argument("--path-map", action="append", default=[])
    args = parser.parse_args()
    result = diagnose(args)
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "summary_by_gripper_regime": result["summary_by_gripper_regime"],
                "output_dir": str(Path(args.output_dir).expanduser().resolve()),
            },
            sort_keys=True,
            allow_nan=True,
        )
    )


if __name__ == "__main__":
    main()
