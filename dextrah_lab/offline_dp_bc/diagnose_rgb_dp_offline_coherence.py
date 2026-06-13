"""Offline action-coherence diagnostic for Franka cube RGB Diffusion Policy BC.

This script does not run Isaac. It loads an official image Diffusion Policy
checkpoint, queries selected RGB/proprio histories from an NPZ dataset, and
compares the returned action sequence against the dataset labels using the same
two-frame history convention as the closed-loop RGB evaluator.
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

from dextrah_lab.offline_dp_bc.dp_dataset import _contact_phase_progress_features

ACTION_NAMES = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]
PHASE_NAME_BY_ID = {
    0: "align_open",
    1: "close_hold",
    2: "lift",
}


def _episode_for_row(row: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, row, side="right"))
    ep_start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    ep_end = int(episode_ends[ep_idx])
    return ep_idx, ep_start, ep_end


def _phase_name(phase_ids: np.ndarray | None, row: int) -> str:
    if phase_ids is None:
        return "unknown"
    return PHASE_NAME_BY_ID.get(int(phase_ids[row]), str(int(phase_ids[row])))


def _image_history(image: np.ndarray, frame_ids: np.ndarray) -> np.ndarray:
    frames = image[frame_ids]
    if frames.shape[-1] == 3:
        frames = np.moveaxis(frames, -1, 1)
    frames = frames.astype(np.float32, copy=False)
    if frames.max(initial=0.0) > 1.0:
        frames = frames / 255.0
    return frames


def _history_for_row(
    image: np.ndarray,
    robot_state: np.ndarray,
    row: int,
    episode_ends: np.ndarray,
    n_obs_steps: int,
) -> dict[str, np.ndarray]:
    _ep_idx, ep_start, ep_end = _episode_for_row(row, episode_ends)
    frame_ids = np.arange(row - (n_obs_steps - 1), row + 1, dtype=np.int64)
    frame_ids = np.clip(frame_ids, ep_start, ep_end - 1)
    return {
        "image": _image_history(image, frame_ids),
        "robot_state": robot_state[frame_ids].astype(np.float32, copy=False),
    }


def _label_for_row(action: np.ndarray, row: int, episode_ends: np.ndarray, length: int) -> np.ndarray:
    _ep_idx, _ep_start, ep_end = _episode_for_row(row, episode_ends)
    frame_ids = np.arange(row, row + length, dtype=np.int64)
    frame_ids = np.clip(frame_ids, row, ep_end - 1)
    return action[frame_ids].astype(np.float32, copy=False)


def _select_rows(args: argparse.Namespace, episode_ends: np.ndarray, n_rows: int) -> list[int]:
    selected: list[int] = []
    selected.extend(int(row) for row in args.row)
    for ep_idx in args.episode:
        ep_idx = int(ep_idx)
        if ep_idx < 0 or ep_idx >= int(episode_ends.shape[0]):
            raise ValueError(f"Episode {ep_idx} is out of range for {episode_ends.shape[0]} episodes")
        ep_start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
        ep_end = int(episode_ends[ep_idx])
        for step in args.episode_step:
            row = ep_start + int(step)
            if row < ep_end:
                selected.append(row)
    if args.random_rows > 0:
        rng = np.random.default_rng(int(args.seed))
        selected.extend(rng.choice(np.arange(n_rows, dtype=np.int64), size=int(args.random_rows), replace=False).tolist())
    rows = sorted({int(row) for row in selected})
    for row in rows:
        if row < 0 or row >= n_rows:
            raise ValueError(f"Row {row} out of range [0, {n_rows})")
    return rows


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


def _pose_cosine(a: np.ndarray, b: np.ndarray, eps: float = 1.0e-8) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm < eps or b_norm < eps:
        return float("nan")
    return float(np.dot(a, b) / (a_norm * b_norm))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    first_mse = np.asarray([float(row["first_mse_all"]) for row in rows], dtype=np.float64)
    seq_mse = np.asarray([float(row["sequence_mse_all"]) for row in rows], dtype=np.float64)
    pose_cos = np.asarray([float(row["first_pose_cosine"]) for row in rows], dtype=np.float64)
    grip_matches = np.asarray([bool(row["gripper_sign_match"]) for row in rows], dtype=bool)
    out: dict[str, Any] = {
        "count": len(rows),
        "first_mse_all_mean": float(np.mean(first_mse)),
        "first_mse_all_median": float(np.median(first_mse)),
        "sequence_mse_all_mean": float(np.mean(seq_mse)),
        "sequence_mse_all_median": float(np.median(seq_mse)),
        "gripper_sign_match_fraction": float(np.mean(grip_matches)),
    }
    finite_cos = pose_cos[np.isfinite(pose_cos)]
    out["first_pose_cosine_mean"] = float(np.mean(finite_cos)) if finite_cos.size else None
    for action_idx, name in enumerate(ACTION_NAMES):
        errors = np.asarray([float(row[f"first_error_{name}"]) for row in rows], dtype=np.float64)
        out[f"first_mae_{name}"] = float(np.mean(np.abs(errors)))
        out[f"first_bias_{name}"] = float(np.mean(errors))
    return out


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    dataset = Path(args.dataset).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if not dataset.is_file():
        raise FileNotFoundError(dataset)

    data = np.load(dataset, allow_pickle=False)
    image_key = "image" if "image" in data.files else "rgb"
    image = np.asarray(data[image_key])
    robot_state = np.asarray(data["robot_state"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32) if "phase_ids" in data.files else None
    rollout_ids = np.asarray(data["rollout_ids"]).astype(str) if "rollout_ids" in data.files else None
    if image.shape[0] != robot_state.shape[0] or image.shape[0] != action.shape[0]:
        raise ValueError(f"Length mismatch: image {image.shape}, robot_state {robot_state.shape}, action {action.shape}")
    if args.append_phase_progress:
        if phase_ids is None:
            raise KeyError(f"{dataset} missing phase_ids required for --append-phase-progress")
        phase_features = _contact_phase_progress_features(phase_ids, episode_ends, int(robot_state.shape[0]))
        robot_state = np.concatenate((robot_state, phase_features), axis=1).astype(np.float32)

    workspace, policy, resolved_policy = _load_policy(
        checkpoint,
        str(args.device),
        Path(args.diffusion_policy_root) if args.diffusion_policy_root else None,
        str(args.policy_source),
    )
    policy.num_inference_steps = int(args.num_inference_steps)
    n_obs_steps = int(policy.n_obs_steps)
    n_action_steps = int(policy.n_action_steps)
    rows = _select_rows(args, episode_ends, int(action.shape[0]))

    records: list[dict[str, Any]] = []
    for batch_start in range(0, len(rows), int(args.batch_size)):
        batch_rows = rows[batch_start : batch_start + int(args.batch_size)]
        histories = [_history_for_row(image, robot_state, row, episode_ends, n_obs_steps) for row in batch_rows]
        image_batch = np.stack([item["image"] for item in histories], axis=0)
        robot_batch = np.stack([item["robot_state"] for item in histories], axis=0)
        torch.manual_seed(int(args.seed) + batch_start)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(args.seed) + batch_start)
        with torch.inference_mode():
            result = policy.predict_action(
                {
                    "image": torch.as_tensor(image_batch, dtype=torch.float32, device=args.device),
                    "robot_state": torch.as_tensor(robot_batch, dtype=torch.float32, device=args.device),
                }
            )
        pred_batch = result["action"].detach().cpu().numpy().astype(np.float32)
        for local_idx, row in enumerate(batch_rows):
            label = _label_for_row(action, row, episode_ends, n_action_steps)
            pred = pred_batch[local_idx]
            diff = pred - label
            ep_idx, ep_start, ep_end = _episode_for_row(row, episode_ends)
            record: dict[str, Any] = {
                "row": int(row),
                "episode": int(ep_idx),
                "episode_step": int(row - ep_start),
                "episode_length": int(ep_end - ep_start),
                "phase": _phase_name(phase_ids, row),
                "rollout_id": "" if rollout_ids is None else str(rollout_ids[ep_idx]),
                "sequence_mse_all": float(np.mean(diff**2)),
                "sequence_mse_pose": float(np.mean(diff[:, :6] ** 2)),
                "sequence_mse_gripper": float(np.mean(diff[:, 6:] ** 2)),
                "first_mse_all": float(np.mean(diff[0] ** 2)),
                "first_mse_pose": float(np.mean(diff[0, :6] ** 2)),
                "first_mse_gripper": float(np.mean(diff[0, 6:] ** 2)),
                "first_pose_cosine": _pose_cosine(pred[0, :6], label[0, :6]),
                "first_xyz_cosine": _pose_cosine(pred[0, :3], label[0, :3]),
                "gripper_sign_match": bool(np.sign(pred[0, 6]) == np.sign(label[0, 6])),
                "obs_gripper_width": float(robot_state[row, -1]),
            }
            for action_idx, name in enumerate(ACTION_NAMES):
                record[f"pred_first_{name}"] = float(pred[0, action_idx])
                record[f"label_first_{name}"] = float(label[0, action_idx])
                record[f"first_error_{name}"] = float(diff[0, action_idx])
            records.append(record)

    by_phase = {phase: _summary([row for row in records if row["phase"] == phase]) for phase in sorted({r["phase"] for r in records})}
    payload = {
        "checkpoint": str(checkpoint),
        "dataset": str(dataset),
        "image_shape": list(image.shape),
        "robot_state_shape": list(robot_state.shape),
        "action_shape": list(action.shape),
        "episode_count": int(episode_ends.shape[0]),
        "policy_source": resolved_policy,
        "workspace_class": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "n_obs_steps": n_obs_steps,
        "n_action_steps": n_action_steps,
        "horizon": int(policy.horizon),
        "num_inference_steps": int(policy.num_inference_steps),
        "rows": records,
        "summary": _summary(records),
        "summary_by_phase": by_phase,
    }
    rows_csv = output_dir / "rgb_offline_coherence_rows.csv"
    json_path = output_dir / "rgb_offline_coherence_summary.json"
    report_path = output_dir / "rgb_offline_coherence_report.md"
    _write_csv(rows_csv, records)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=True) + "\n", encoding="utf-8")
    lines = [
        "# RGB DP Offline Coherence",
        "",
        f"- checkpoint: `{checkpoint}`",
        f"- dataset: `{dataset}`",
        f"- policy: `{payload['policy_class']}` from `{resolved_policy}`",
        f"- rows scored: `{len(records)}`",
        f"- summary: `{json.dumps(payload['summary'], sort_keys=True, allow_nan=True)}`",
        "",
        "| row | ep | step | phase | seq mse | first mse | grip ok | first pred | first label |",
        "|---:|---:|---:|---|---:|---:|---:|---|---|",
    ]
    for row in records:
        pred = [row[f"pred_first_{name}"] for name in ACTION_NAMES]
        label = [row[f"label_first_{name}"] for name in ACTION_NAMES]
        pred_s = ", ".join(f"{float(v):.3f}" for v in pred)
        label_s = ", ".join(f"{float(v):.3f}" for v in label)
        lines.append(
            f"| {row['row']} | {row['episode']} | {row['episode_step']} | {row['phase']} | "
            f"{float(row['sequence_mse_all']):.5f} | {float(row['first_mse_all']):.5f} | "
            f"{int(bool(row['gripper_sign_match']))} | `{pred_s}` | `{label_s}` |"
        )
    lines.extend(["", "## Artifacts", "", f"- rows CSV: `{rows_csv}`", f"- JSON: `{json_path}`"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--diffusion-policy-root", default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--num-inference-steps", type=int, default=100)
    parser.add_argument("--policy-source", choices=["auto", "ema", "model"], default="auto")
    parser.add_argument(
        "--append-phase-progress",
        action="store_true",
        default=False,
        help="Append contact phase one-hot plus episode progress to raw 8D robot_state before scoring.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--row", action="append", type=int, default=[])
    parser.add_argument("--episode", action="append", type=int, default=[])
    parser.add_argument("--episode-step", action="append", type=int, default=[0, 20, 40, 60, 80, 120, 160])
    parser.add_argument("--random-rows", type=int, default=0)
    args = parser.parse_args()
    result = diagnose(args)
    print(json.dumps({"summary": result["summary"], "summary_by_phase": result["summary_by_phase"]}, sort_keys=True, allow_nan=True))


if __name__ == "__main__":
    main()
