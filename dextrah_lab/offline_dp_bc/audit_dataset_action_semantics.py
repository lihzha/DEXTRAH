"""Audit Franka cube lowdim dataset action semantics for replay debugging.

This offline diagnostic does not train or run Isaac. It inspects one converted
Diffusion Policy lowdim episode, optionally maps it back to the raw
GraspGenX/cuRobo ``trajectory.json``, and verifies that the labels behave as
one-step normalized relative-EE commands under the DEXTRAH action convention.
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

from .action_conversion import (
    apply_normalized_action_to_world_pose,
    axis_angle_from_quat_wxyz,
    quat_inv_wxyz,
    quat_mul_wxyz,
)
from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


def _phase_names() -> list[str]:
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _row_for_episode_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> int:
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    return int(start + np.clip(int(episode_step), 0, max(0, end - start - 1)))


def _episode_bounds(episode_ends: np.ndarray, episode: int) -> tuple[int, int]:
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    return int(start), int(episode_ends[episode_idx])


def _phase_ranges(phase_ids: np.ndarray, start: int, end: int) -> list[dict[str, Any]]:
    names = _phase_names()
    out: list[dict[str, Any]] = []
    ep = phase_ids[start:end]
    if ep.size == 0:
        return out
    run_start = 0
    for idx in range(1, int(ep.size) + 1):
        if idx == ep.size or ep[idx] != ep[run_start]:
            phase_id = int(ep[run_start])
            out.append(
                {
                    "phase": names[phase_id],
                    "episode_step_start": int(run_start),
                    "episode_step_end_exclusive": int(idx),
                    "count": int(idx - run_start),
                }
            )
            run_start = idx
    return out


def _load_source_frame(path: Path | None, episode_step: int) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"{path} does not contain a non-empty frames list")
    frame_idx = int(np.clip(int(episode_step), 0, len(frames) - 1))
    frame = frames[frame_idx]
    return {
        "path": str(path),
        "frame": int(frame_idx),
        "phase": str(frame.get("phase", "")),
        "joint_position": frame.get("joint_position"),
        "joint_position_dim": len(frame.get("joint_position", [])) if isinstance(frame.get("joint_position"), list) else 0,
        "total_frames": int(len(frames)),
        "top_level_keys": sorted(payload.keys()),
        "frame_keys": sorted(frame.keys()),
    }


def _quat_error(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    delta = quat_mul_wxyz(target, quat_inv_wxyz(pred))
    return np.linalg.norm(axis_angle_from_quat_wxyz(delta), axis=-1)


def _episode_rows(
    obs: np.ndarray,
    action: np.ndarray,
    phase_ids: np.ndarray,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    names = _phase_names()
    rows: list[dict[str, Any]] = []
    for global_row in range(start, end):
        episode_step = int(global_row - start)
        act = action[global_row]
        if global_row < end - 1:
            pred_pos, pred_quat = apply_normalized_action_to_world_pose(
                obs[global_row : global_row + 1, 0:3],
                obs[global_row : global_row + 1, 3:7],
                action[global_row : global_row + 1],
            )
            pos_err = float(np.linalg.norm(pred_pos[0] - obs[global_row + 1, 0:3]))
            rot_err = float(_quat_error(pred_quat, obs[global_row + 1 : global_row + 2, 3:7])[0])
            next_cube_minus_ee = obs[global_row + 1, 14:17]
        else:
            pos_err = float("nan")
            rot_err = float("nan")
            next_cube_minus_ee = obs[global_row, 14:17]
        rows.append(
            {
                "global_row": int(global_row),
                "episode_step": episode_step,
                "phase": names[int(phase_ids[global_row])],
                "ee_pos_x": float(obs[global_row, 0]),
                "ee_pos_y": float(obs[global_row, 1]),
                "ee_pos_z": float(obs[global_row, 2]),
                "cube_minus_ee_x": float(obs[global_row, 14]),
                "cube_minus_ee_y": float(obs[global_row, 15]),
                "cube_minus_ee_z": float(obs[global_row, 16]),
                "cube_minus_ee_norm": float(np.linalg.norm(obs[global_row, 14:17])),
                "next_cube_minus_ee_norm": float(np.linalg.norm(next_cube_minus_ee)),
                "gripper_width": float(obs[global_row, 20]),
                "action_dx": float(act[0]),
                "action_dy": float(act[1]),
                "action_dz": float(act[2]),
                "action_drx": float(act[3]),
                "action_dry": float(act[4]),
                "action_drz": float(act[5]),
                "action_gripper": float(act[6]),
                "pose_action_norm": float(np.linalg.norm(act[:6])),
                "xyz_action_norm": float(np.linalg.norm(act[:3])),
                "rot_action_norm": float(np.linalg.norm(act[3:6])),
                "pose_action_near_zero": bool(np.linalg.norm(act[:6]) < 1.0e-5),
                "pose_action_any_clipped": bool(np.any(np.abs(act[:6]) >= 0.999)),
                "one_step_pos_reconstruction_error": pos_err,
                "one_step_rot_reconstruction_error": rot_err,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    steps = np.asarray([row["episode_step"] for row in rows], dtype=float)
    fig, axes = plt.subplots(4, 1, figsize=(13, 13), sharex=True, constrained_layout=True)
    for key in ("action_dx", "action_dy", "action_dz"):
        axes[0].plot(steps, [row[key] for row in rows], label=key)
    axes[0].plot(steps, [row["action_gripper"] for row in rows], color="black", linestyle="--", label="gripper")
    axes[0].set_title("Normalized Action Components")
    axes[0].set_ylabel("action")
    axes[0].legend(ncol=4, fontsize=8)
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(steps, [row["cube_minus_ee_x"] for row in rows], label="x")
    axes[1].plot(steps, [row["cube_minus_ee_y"] for row in rows], label="y")
    axes[1].plot(steps, [row["cube_minus_ee_z"] for row in rows], label="z")
    axes[1].plot(steps, [row["cube_minus_ee_norm"] for row in rows], color="black", linestyle="--", label="norm")
    axes[1].set_title("Dataset Cube Minus EE")
    axes[1].set_ylabel("m")
    axes[1].legend(ncol=4, fontsize=8)
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(steps, [row["one_step_pos_reconstruction_error"] for row in rows], label="position")
    axes[2].plot(steps, [row["one_step_rot_reconstruction_error"] for row in rows], label="rotation")
    axes[2].set_title("Action t Reconstructs Dataset Pose t+1")
    axes[2].set_ylabel("m / rad")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.25)

    phase_to_y: dict[str, int] = {}
    y_values: list[int] = []
    for row in rows:
        phase_to_y.setdefault(row["phase"], len(phase_to_y))
        y_values.append(phase_to_y[row["phase"]])
    axes[3].step(steps, y_values, where="post")
    axes[3].set_yticks(list(phase_to_y.values()), list(phase_to_y.keys()), fontsize=7)
    axes[3].set_title("Phase")
    axes[3].set_xlabel("episode step")
    axes[3].grid(True, alpha=0.25)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = np.asarray([row[key] for row in rows if np.isfinite(float(row[key]))], dtype=np.float64)
    return float(values.mean()) if values.size else float("nan")


def _max(rows: list[dict[str, Any]], key: str) -> float:
    values = np.asarray([row[key] for row in rows if np.isfinite(float(row[key]))], dtype=np.float64)
    return float(values.max()) if values.size else float("nan")


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube DP Dataset Action Semantics Audit",
        "",
        "## Verdict",
        "",
        "- Dataset labels are normalized one-step relative end-effector delta-IK commands, not absolute poses.",
        "- The first selected action can be near zero when adjacent source waypoints are identical; replaying it from a different robot state will hold that different state.",
        "- Gripper labels are raw DEXTRAH commands: `+1` opens and `-1` closes.",
        "",
        "## Selection",
        "",
        f"- dataset: `{summary['dataset']}`",
        f"- metadata: `{summary.get('metadata_path')}`",
        f"- episode: `{summary['episode']}`",
        f"- rows: `{summary['episode_start']}` to `{summary['episode_end_exclusive']}`",
        f"- selected step: `{summary['selected_step']}` global row `{summary['selected_global_row']}`",
        f"- source frame: `{summary.get('source_frame')}`",
        "",
        "## Action Convention",
        "",
        f"- action schema: `{summary.get('action_schema')}`",
        f"- action convention: `{summary.get('action_convention')}`",
        "",
        "## Episode Stats",
        "",
        f"- pose action near-zero rate: `{summary['pose_action_near_zero_rate']:.4f}`",
        f"- pose action clipped rate: `{summary['pose_action_clipped_rate']:.4f}`",
        f"- one-step position reconstruction mean/max: `{summary['one_step_pos_reconstruction_error_mean']:.6g}` / `{summary['one_step_pos_reconstruction_error_max']:.6g}`",
        f"- one-step rotation reconstruction mean/max: `{summary['one_step_rot_reconstruction_error_mean']:.6g}` / `{summary['one_step_rot_reconstruction_error_max']:.6g}`",
        f"- first negative / hard-close action steps: `{summary['first_negative_gripper_step']}` / `{summary['first_hard_close_step']}`",
        "",
        "## Phase Ranges",
        "",
        "| phase | start | end excl | count |",
        "|---|---:|---:|---:|",
    ]
    for item in summary["phase_ranges"]:
        lines.append(
            f"| {item['phase']} | {item['episode_step_start']} | "
            f"{item['episode_step_end_exclusive']} | {item['count']} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- csv: `{summary['csv']}`",
            f"- json: `{summary['json']}`",
            f"- plot: `{summary['plot']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--episode", type=int, default=0)
    parser.add_argument("--selected_step", type=int, default=0)
    parser.add_argument("--source_trajectory_json", type=Path, default=None)
    parser.add_argument("--output_dir", required=True, type=Path)
    args = parser.parse_args()

    dataset_path = args.dataset.expanduser().resolve()
    metadata_path = args.metadata.expanduser().resolve() if args.metadata else dataset_path.with_suffix(dataset_path.suffix + ".metadata.json")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    start, end = _episode_bounds(episode_ends, int(args.episode))
    selected_global = _row_for_episode_step(episode_ends, int(args.episode), int(args.selected_step))
    rows = _episode_rows(obs, action, phase_ids, start, end)
    csv_path = output_dir / "dataset_action_semantics_rows.csv"
    json_path = output_dir / "dataset_action_semantics_summary.json"
    plot_path = output_dir / "dataset_action_semantics.png"
    report_path = output_dir / "dataset_action_semantics_report.md"
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)

    meta: dict[str, Any] = {}
    if metadata_path.is_file():
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    source = _load_source_frame(args.source_trajectory_json.expanduser().resolve() if args.source_trajectory_json else None, int(args.selected_step))
    first_negative = next((row["episode_step"] for row in rows if row["action_gripper"] < 0.0), None)
    first_hard = next((row["episode_step"] for row in rows if row["action_gripper"] <= -0.9), None)
    summary = {
        "dataset": str(dataset_path),
        "metadata_path": str(metadata_path) if metadata_path.is_file() else None,
        "episode": int(args.episode),
        "episode_start": int(start),
        "episode_end_exclusive": int(end),
        "selected_step": int(selected_global - start),
        "selected_global_row": int(selected_global),
        "selected_obs": obs[selected_global].astype(float).tolist(),
        "selected_action": action[selected_global].astype(float).tolist(),
        "selected_phase": _phase_names()[int(phase_ids[selected_global])],
        "source_frame": source,
        "action_schema": meta.get("action_schema"),
        "action_convention": meta.get("action_convention"),
        "source_metadata": (meta.get("sources") or [None] * (int(args.episode) + 1))[int(args.episode)]
        if len(meta.get("sources") or []) > int(args.episode)
        else None,
        "phase_ranges": _phase_ranges(phase_ids, start, end),
        "pose_action_near_zero_rate": float(np.mean([row["pose_action_near_zero"] for row in rows])),
        "pose_action_clipped_rate": float(np.mean([row["pose_action_any_clipped"] for row in rows])),
        "one_step_pos_reconstruction_error_mean": _mean(rows, "one_step_pos_reconstruction_error"),
        "one_step_pos_reconstruction_error_max": _max(rows, "one_step_pos_reconstruction_error"),
        "one_step_rot_reconstruction_error_mean": _mean(rows, "one_step_rot_reconstruction_error"),
        "one_step_rot_reconstruction_error_max": _max(rows, "one_step_rot_reconstruction_error"),
        "first_negative_gripper_step": first_negative,
        "first_hard_close_step": first_hard,
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "report": str(report_path),
    }
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_build_report(summary), encoding="utf-8")
    print(
        "FRANKA_CUBE_DP_DATASET_ACTION_SEMANTICS "
        + json.dumps({"output_dir": str(output_dir), "report": str(report_path), "plot": str(plot_path)}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
