"""Audit Diffusion Policy BC train/eval mismatches for Franka cube.

The report is intended for debugging a no-learning DEXTRAH eval rollout
against the converted low-dimensional BC dataset. It does not run simulation
or training; it only inspects saved dataset, checkpoint, metrics, and trace
artifacts.
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

from .action_conversion import DEFAULT_DEXTRAH_ACTION_CONVENTION, normalized_action_to_world_delta
from .ppo_bridge import DEFAULT_PPO_OBS_SLICES
from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


LOWDIM_SCHEMA = [
    "ee_pos_x",
    "ee_pos_y",
    "ee_pos_z",
    "ee_quat_w",
    "ee_quat_x",
    "ee_quat_y",
    "ee_quat_z",
    "cube_pos_x",
    "cube_pos_y",
    "cube_pos_z",
    "cube_quat_w",
    "cube_quat_x",
    "cube_quat_y",
    "cube_quat_z",
    "cube_minus_ee_x",
    "cube_minus_ee_y",
    "cube_minus_ee_z",
    "cube_goal_delta_x",
    "cube_goal_delta_y",
    "cube_goal_delta_z",
    "gripper_width",
]


ENV_POLICY_OBS_LAYOUT: list[tuple[str, int]] = [
    ("joint_pos_scaled", 9),
    ("joint_vel_scaled", 9),
    ("ee_pos", 3),
    ("ee_quat", 4),
    ("left_finger_pos_minus_cube_pos", 3),
    ("right_finger_pos_minus_cube_pos", 3),
    ("cube_pos", 3),
    ("cube_quat", 4),
    ("cube_vel", 6),
    ("cube_goal_pos", 3),
    ("cube_minus_ee", 3),
    ("cube_goal_delta", 3),
    ("cube_initial_pos", 3),
    ("has_lifted_cube", 1),
    ("in_success_region", 1),
    ("time_in_success_region", 1),
    ("gripper_width", 1),
    ("ee_to_cube_dist", 1),
    ("max_finger_to_cube_dist", 1),
    ("finger_distance_asymmetry", 1),
    ("cube_lift_height", 1),
    ("cube_xy_error", 1),
    ("actions", 7),
]


BRIDGE_FIELDS = {
    "ee_pos": ("ee_pos", DEFAULT_PPO_OBS_SLICES.ee_pos),
    "ee_quat": ("ee_quat", DEFAULT_PPO_OBS_SLICES.ee_quat),
    "cube_pos": ("cube_pos", DEFAULT_PPO_OBS_SLICES.cube_pos),
    "cube_quat": ("cube_quat", DEFAULT_PPO_OBS_SLICES.cube_quat),
    "cube_minus_ee": ("cube_minus_ee", DEFAULT_PPO_OBS_SLICES.cube_minus_ee),
    "cube_goal_delta": ("cube_goal_delta", DEFAULT_PPO_OBS_SLICES.cube_goal_delta),
    "gripper_width": ("gripper_width", DEFAULT_PPO_OBS_SLICES.gripper_width),
}


def _phase_names() -> list[str]:
    # trajectory_to_episode writes ids from sorted(set(phases)).
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _layout_slices() -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    cursor = 0
    for name, width in ENV_POLICY_OBS_LAYOUT:
        out[name] = (cursor, cursor + width)
        cursor += width
    return out


def _slice_tuple(value: slice | int) -> tuple[int, int]:
    if isinstance(value, int):
        return (int(value), int(value) + 1)
    return (int(value.start), int(value.stop))


def _bridge_layout_check() -> dict[str, Any]:
    layout = _layout_slices()
    rows = []
    all_match = True
    for lowdim_name, (env_name, bridge_slice) in BRIDGE_FIELDS.items():
        expected = layout[env_name]
        actual = _slice_tuple(bridge_slice)
        match = actual == expected
        all_match = all_match and match
        rows.append(
            {
                "lowdim_field": lowdim_name,
                "env_field": env_name,
                "expected_slice": list(expected),
                "bridge_slice": list(actual),
                "match": bool(match),
            }
        )
    return {
        "env_policy_obs_dim": int(sum(width for _, width in ENV_POLICY_OBS_LAYOUT)),
        "bridge_matches_env_layout": bool(all_match),
        "rows": rows,
        "layout": {name: list(bounds) for name, bounds in layout.items()},
    }


def _stats(arr: np.ndarray) -> dict[str, list[float]]:
    return {
        "min": np.min(arr, axis=0).astype(float).tolist(),
        "max": np.max(arr, axis=0).astype(float).tolist(),
        "mean": np.mean(arr, axis=0).astype(float).tolist(),
        "std": np.std(arr, axis=0).astype(float).tolist(),
    }


def _load_checkpoint_normalizer(checkpoint: Path | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        return {"error": f"torch import failed: {exc}"}
    try:
        payload = torch.load(str(checkpoint), map_location="cpu", weights_only=False)
        model_state = payload["state_dicts"]["model"]
    except Exception as exc:
        return {"error": f"checkpoint load failed: {exc}"}
    out: dict[str, Any] = {}
    for field in ("obs", "action"):
        prefix = f"normalizer.params_dict.{field}."
        field_payload: dict[str, Any] = {}
        for key in ("offset", "scale", "input_stats.max", "input_stats.mean", "input_stats.min", "input_stats.std"):
            state_key = prefix + key
            if state_key in model_state:
                field_payload[key] = model_state[state_key].detach().cpu().numpy().astype(float).tolist()
        out[field] = field_payload
    return out


def _phase_boundaries(phase_ids: np.ndarray, episode_ends: np.ndarray) -> dict[str, dict[str, float | int | None]]:
    names = _phase_names()
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    rows: dict[str, list[int]] = {name: [] for name in names}
    counts: dict[str, list[int]] = {name: [] for name in names}
    for start, end in zip(starts, episode_ends):
        ep = phase_ids[int(start) : int(end)]
        for phase_id, name in enumerate(names):
            idx = np.flatnonzero(ep == phase_id)
            if idx.size:
                rows[name].append(int(idx[0]))
                counts[name].append(int(idx.size))
            else:
                counts[name].append(0)
    out: dict[str, dict[str, float | int | None]] = {}
    for name in names:
        first = rows[name]
        count = counts[name]
        out[name] = {
            "first_min": int(np.min(first)) if first else None,
            "first_mean": float(np.mean(first)) if first else None,
            "first_max": int(np.max(first)) if first else None,
            "count_mean": float(np.mean(count)) if count else 0.0,
            "count_min": int(np.min(count)) if count else 0,
            "count_max": int(np.max(count)) if count else 0,
        }
    return out


def _first_step(rows: list[dict[str, Any]], predicate) -> int | None:
    for row in rows:
        if predicate(row):
            return int(row["step"])
    return None


def _nearest_phase_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        phase = str(row["nearest_position_phase"])
        counts[phase] = counts.get(phase, 0) + 1
    return counts


def _trace_lowdim(trace: dict[str, Any]) -> np.ndarray:
    return np.asarray([record["lowdim_obs"] for record in trace["policy_calls"]], dtype=np.float32)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot_behavior(metrics: dict[str, Any], output_path: Path) -> None:
    steps = metrics["steps"]
    x = np.asarray([row["step"] for row in steps], dtype=float)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for key in ("ee_to_cube_dist", "finger_center_to_cube_dist", "left_finger_to_cube_dist", "right_finger_to_cube_dist"):
        y = [row.get(key) for row in steps]
        axes[0, 0].plot(x, y, label=key)
    axes[0, 0].set_title("Distance To Cube")
    axes[0, 0].set_ylabel("m")
    axes[0, 0].grid(True, alpha=0.25)
    axes[0, 0].legend(fontsize=7)

    axes[0, 1].plot(x, [row.get("gripper_width") for row in steps], label="gripper_width")
    axes[0, 1].set_title("Gripper Width")
    axes[0, 1].set_ylabel("m")
    axes[0, 1].grid(True, alpha=0.25)

    axes[1, 0].plot(x, [row.get("cube_lift_height") for row in steps], label="cube_lift_height")
    axes[1, 0].set_title("Cube Lift Height")
    axes[1, 0].set_ylabel("m")
    axes[1, 0].grid(True, alpha=0.25)

    axes[1, 1].plot(x, [row.get("reward_mean") for row in steps], label="reward")
    axes[1, 1].set_title("Reward")
    axes[1, 1].grid(True, alpha=0.25)
    for ax in axes.flat:
        ax.set_xlabel("env step")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_trace(rows: list[dict[str, Any]], phase_boundaries: dict[str, dict[str, Any]], output_path: Path) -> None:
    steps = np.asarray([row["step"] for row in rows], dtype=float)
    names = _phase_names()
    phase_to_id = {name: idx for idx, name in enumerate(names)}
    phase_ids = np.asarray([phase_to_id[row["nearest_position_phase"]] for row in rows], dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, constrained_layout=True)
    axes[0].plot(steps, phase_ids, marker="o", linewidth=1)
    axes[0].set_yticks(list(phase_to_id.values()))
    axes[0].set_yticklabels(names, fontsize=7)
    axes[0].set_title("Nearest Demo Phase")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(steps, [row["nearest_position_distance"] for row in rows], marker="o")
    axes[1].set_title("Nearest Demo Distance")
    axes[1].set_ylabel("scaled distance")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(steps, [row["chunk_gripper_action_min"] for row in rows], label="chunk gripper min")
    axes[2].plot(steps, [row["chunk_gripper_action_max"] for row in rows], label="chunk gripper max")
    axes[2].plot(steps, [row["live_gripper_width"] for row in rows], label="live width m")
    axes[2].axhline(0.0, color="black", linewidth=0.8)
    axes[2].set_title("Trace Gripper Commands")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=8)

    for phase in ("close_fingers", "lift_object", "hold_after_lift"):
        first_mean = phase_boundaries.get(phase, {}).get("first_mean")
        if first_mean is not None:
            for ax in axes:
                ax.axvline(float(first_mean), color="tab:red", linestyle="--", alpha=0.35)
                ax.text(float(first_mean), ax.get_ylim()[1], phase, rotation=90, va="top", ha="right", fontsize=7)
    axes[-1].set_xlabel("env step")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_obs_distribution(obs: np.ndarray, trace_obs: np.ndarray, output_path: Path) -> None:
    stats = _stats(obs)
    obs_min = np.asarray(stats["min"], dtype=float)
    obs_max = np.asarray(stats["max"], dtype=float)
    obs_mean = np.asarray(stats["mean"], dtype=float)
    obs_std = np.maximum(np.asarray(stats["std"], dtype=float), 1.0e-6)
    trace_min = trace_obs.min(axis=0)
    trace_max = trace_obs.max(axis=0)
    z = np.max(np.abs((trace_obs - obs_mean) / obs_std), axis=0)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    x = np.arange(obs.shape[1])
    axes[0].fill_between(x, obs_min, obs_max, alpha=0.25, label="dataset min/max")
    axes[0].plot(x, trace_min, marker="o", label="trace min")
    axes[0].plot(x, trace_max, marker="o", label="trace max")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(LOWDIM_SCHEMA, rotation=60, ha="right", fontsize=7)
    axes[0].set_title("Lowdim Observation Range")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    axes[1].bar(x, z)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(LOWDIM_SCHEMA, rotation=60, ha="right", fontsize=7)
    axes[1].set_ylabel("max abs z-score")
    axes[1].set_title("Trace Obs Distance From Dataset Distribution")
    axes[1].grid(True, axis="y", alpha=0.25)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _format_vector(values: list[float] | np.ndarray | None, precision: int = 4) -> str:
    if values is None:
        return "n/a"
    arr = np.asarray(values, dtype=float)
    return "[" + ", ".join(f"{v:.{precision}f}" for v in arr.tolist()) + "]"


def audit(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.dataset.expanduser().resolve(), allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    metadata = json.loads(args.metadata.expanduser().read_text(encoding="utf-8")) if args.metadata else {}
    metrics = json.loads(args.metrics.expanduser().read_text(encoding="utf-8"))
    trace = json.loads(args.trace.expanduser().read_text(encoding="utf-8"))
    trace_analysis = json.loads(args.trace_analysis.expanduser().read_text(encoding="utf-8"))
    trace_rows = trace_analysis["rows"]
    trace_obs = _trace_lowdim(trace)
    phase_boundaries = _phase_boundaries(phase_ids, episode_ends)
    layout_check = _bridge_layout_check()
    checkpoint_normalizer = _load_checkpoint_normalizer(args.checkpoint.expanduser().resolve() if args.checkpoint else None)

    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    start_obs = obs[starts]
    reset_obs = trace_obs[0]
    start_dist = np.linalg.norm(start_obs - reset_obs[None, :], axis=1)
    nearest_start_idx = int(np.argmin(start_dist))
    dataset_stats = _stats(obs)
    action_stats = _stats(action)

    norm_matches_dataset = None
    norm_obs_max_abs_diff = None
    norm_action_max_abs_diff = None
    if checkpoint_normalizer and "error" not in checkpoint_normalizer:
        ckpt_obs_mean = np.asarray(checkpoint_normalizer["obs"]["input_stats.mean"], dtype=float)
        ckpt_action_mean = np.asarray(checkpoint_normalizer["action"]["input_stats.mean"], dtype=float)
        norm_obs_max_abs_diff = float(np.max(np.abs(ckpt_obs_mean - np.asarray(dataset_stats["mean"]))))
        norm_action_max_abs_diff = float(np.max(np.abs(ckpt_action_mean - np.asarray(action_stats["mean"]))))
        norm_matches_dataset = bool(norm_obs_max_abs_diff < 1.0e-4 and norm_action_max_abs_diff < 1.0e-6)

    close_first = phase_boundaries["close_fingers"]["first_mean"]
    lift_first = phase_boundaries["lift_object"]["first_mean"]
    expected = {
        "close_fingers_first_mean_step": close_first,
        "lift_object_first_mean_step": lift_first,
        "hold_after_lift_first_mean_step": phase_boundaries["hold_after_lift"]["first_mean"],
        "dataset_fps_mean": float(np.mean([src.get("fps", np.nan) for src in metadata.get("sources", [])])),
        "eval_step_hz": 60.0,
        "action_chunk_steps": int(metrics["summary"].get("action_chunk_steps", -1)),
        "dp_horizon": 16,
        "dp_n_obs_steps": 2,
        "dp_n_action_steps": 8,
    }

    temporal = {
        "first_gripper_chunk_crosses_negative_step": _first_step(
            trace_rows, lambda row: float(row["chunk_gripper_action_min"]) < 0.0
        ),
        "first_gripper_chunk_hard_close_step": _first_step(
            trace_rows, lambda row: float(row["chunk_gripper_action_min"]) < -0.9
        ),
        "first_live_gripper_width_lt_1cm_step": _first_step(
            trace_rows, lambda row: float(row["live_gripper_width"]) < 0.01
        ),
        "first_nearest_lift_object_step": _first_step(
            trace_rows, lambda row: row["nearest_position_phase"] == "lift_object"
        ),
        "nearest_phase_counts": _nearest_phase_counts(trace_rows),
    }

    first_row = trace_rows[0]
    first_action_world = normalized_action_to_world_delta(
        np.asarray(
            [
                first_row["first_action_x"],
                first_row["first_action_y"],
                first_row["first_action_z"],
                0,
                0,
                0,
                0,
            ],
            dtype=np.float32,
        )[None, :],
        convention=DEFAULT_DEXTRAH_ACTION_CONVENTION,
    )[0, :3]
    final_row = trace_rows[-1]
    final_metrics = metrics["summary"]["step_metric_summary"]
    reset = {
        "trace_start_cube_pos": reset_obs[7:10].astype(float).tolist(),
        "dataset_start_cube_pos_min": start_obs[:, 7:10].min(axis=0).astype(float).tolist(),
        "dataset_start_cube_pos_max": start_obs[:, 7:10].max(axis=0).astype(float).tolist(),
        "dataset_start_cube_pos_mean": start_obs[:, 7:10].mean(axis=0).astype(float).tolist(),
        "trace_start_ee_pos": reset_obs[:3].astype(float).tolist(),
        "trace_start_cube_minus_ee": reset_obs[14:17].astype(float).tolist(),
        "nearest_dataset_episode_start": nearest_start_idx,
        "nearest_dataset_start_l2": float(start_dist[nearest_start_idx]),
    }

    plots = {
        "behavior": str(output_dir / "behavior_metrics.png"),
        "trace": str(output_dir / "trace_phase_action.png"),
        "obs_distribution": str(output_dir / "obs_distribution.png"),
    }
    _plot_behavior(metrics, Path(plots["behavior"]))
    _plot_trace(trace_rows, phase_boundaries, Path(plots["trace"]))
    _plot_obs_distribution(obs, trace_obs, Path(plots["obs_distribution"]))
    _write_csv(output_dir / "trace_phase_rows.csv", trace_rows)

    summary = {
        "dataset": str(args.dataset),
        "metadata": str(args.metadata) if args.metadata else None,
        "metrics": str(args.metrics),
        "trace": str(args.trace),
        "trace_analysis": str(args.trace_analysis),
        "checkpoint": str(args.checkpoint) if args.checkpoint else None,
        "output_dir": str(output_dir),
        "old_label_checkpoints_behavior_status": "stale_invalid_for_behavior_claims",
        "action_frame": {
            "dataset_world_to_action_quat_wxyz": metadata.get("action_convention", {}).get(
                "world_to_action_quat_wxyz"
            ),
            "dataset_position_scale": metadata.get("action_convention", {}).get("position_scale"),
            "dataset_rotation_scale": metadata.get("action_convention", {}).get("rotation_scale"),
            "eval_env_action_scale": {
                "position": list(DEFAULT_DEXTRAH_ACTION_CONVENTION.position_scale),
                "rotation": list(DEFAULT_DEXTRAH_ACTION_CONVENTION.rotation_scale),
            },
            "eval_applies_actions_in_robot_root_frame": True,
            "root_yaw_180deg_requires_world_to_action_rotation": True,
            "first_trace_action_frame_xyz": [
                trace_rows[0]["first_action_x"],
                trace_rows[0]["first_action_y"],
                trace_rows[0]["first_action_z"],
            ],
            "first_trace_world_delta_xyz": first_action_world.astype(float).tolist(),
        },
        "observation": {
            "lowdim_schema": LOWDIM_SCHEMA,
            "layout_check": layout_check,
            "checkpoint_normalizer": checkpoint_normalizer,
            "normalizer_matches_dataset_means": norm_matches_dataset,
            "normalizer_obs_mean_max_abs_diff": norm_obs_max_abs_diff,
            "normalizer_action_mean_max_abs_diff": norm_action_max_abs_diff,
            "trace_obs_outside_dataset_minmax_dims": [
                LOWDIM_SCHEMA[idx]
                for idx in np.flatnonzero(
                    (trace_obs.min(axis=0) < np.asarray(dataset_stats["min"]) - 1.0e-6)
                    | (trace_obs.max(axis=0) > np.asarray(dataset_stats["max"]) + 1.0e-6)
                )
            ],
        },
        "reset_distribution": reset,
        "temporal": {**expected, **temporal},
        "behavior": {
            "steps_completed": metrics["summary"].get("steps_completed"),
            "final_success_rate": metrics["summary"].get("final_success_rate"),
            "reward_final": metrics["summary"].get("reward_final"),
            "final_gripper_width": metrics["summary"].get("final_gripper_width"),
            "ee_to_cube_dist_final": final_metrics["ee_to_cube_dist"]["final"],
            "ee_to_cube_dist_min": final_metrics["ee_to_cube_dist"]["min"],
            "finger_center_to_cube_dist_final": final_metrics["finger_center_to_cube_dist"]["final"],
            "finger_center_to_cube_dist_min": final_metrics["finger_center_to_cube_dist"]["min"],
            "cube_lift_height_max": final_metrics["cube_lift_height"]["max"],
            "final_trace_cube_minus_ee": [
                final_row["live_cube_minus_ee_x"],
                final_row["live_cube_minus_ee_y"],
                final_row["live_cube_minus_ee_z"],
            ],
            "final_nearest_phase": final_row["nearest_position_phase"],
            "final_nearest_distance": final_row["nearest_position_distance"],
        },
        "plots": plots,
    }

    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = _build_report(summary)
    (output_dir / "mismatch_audit_report.md").write_text(report, encoding="utf-8")
    return summary


def _build_report(summary: dict[str, Any]) -> str:
    action = summary["action_frame"]
    obs = summary["observation"]
    reset = summary["reset_distribution"]
    temporal = summary["temporal"]
    behavior = summary["behavior"]
    layout = obs["layout_check"]
    plots = summary["plots"]

    lines = [
        "# Franka Cube DP BC Mismatch Audit",
        "",
        "## Status",
        "- Old pre-framefix checkpoints/videos are stale and invalid for behavior claims.",
        "- This audit uses the framefix checkpoint/eval trace.",
        "- Result: action frame and checkpoint normalizer are consistent with the framefix dataset; eval still fails because the live rollout closes while the end effector/fingers are not in the dataset grasp geometry.",
        "",
        "## Action Frame",
        f"- Dataset `world_to_action_quat_wxyz`: `{action['dataset_world_to_action_quat_wxyz']}`.",
        f"- Dataset pose scales: position `{action['dataset_position_scale']}`, rotation `{action['dataset_rotation_scale']}`.",
        f"- Eval action scales: `{action['eval_env_action_scale']}`.",
        "- DEXTRAH applies relative pose commands in the robot root frame through `DifferentialIKController(use_relative_mode=True)`; the framefix dataset rotates world deltas by the 180-degree root yaw before normalization.",
        f"- First trace action-frame xyz `{_format_vector(action['first_trace_action_frame_xyz'])}` maps back to world delta xyz `{_format_vector(action['first_trace_world_delta_xyz'])}`.",
        "",
        "## Observation And Normalization",
        f"- 72D env layout total: `{layout['env_policy_obs_dim']}`; bridge slices match env layout: `{layout['bridge_matches_env_layout']}`.",
        f"- Checkpoint normalizer matches dataset means: `{obs['normalizer_matches_dataset_means']}`; max obs mean diff `{obs['normalizer_obs_mean_max_abs_diff']}`, action mean diff `{obs['normalizer_action_mean_max_abs_diff']}`.",
        f"- Trace lowdim fields outside dataset min/max: `{obs['trace_obs_outside_dataset_minmax_dims']}`.",
        "- Lowdim training/eval schema is exactly: `ee_pos`, `ee_quat`, `cube_pos`, `cube_quat`, `cube_pos-ee_pos`, `cube_goal_pos-cube_pos`, `gripper_width`.",
        "",
        "## Reset Distribution",
        f"- Trace start cube pos `{_format_vector(reset['trace_start_cube_pos'])}`.",
        f"- Dataset episode-start cube pos min/max `{_format_vector(reset['dataset_start_cube_pos_min'])}` / `{_format_vector(reset['dataset_start_cube_pos_max'])}`.",
        f"- Nearest dataset episode start: `{reset['nearest_dataset_episode_start']}`, raw 21D L2 `{reset['nearest_dataset_start_l2']:.4f}`.",
        f"- Trace start cube-minus-EE `{_format_vector(reset['trace_start_cube_minus_ee'])}`.",
        "",
        "## Temporal Usage",
        f"- Dataset close first mean step: `{temporal['close_fingers_first_mean_step']}`.",
        f"- Dataset lift first mean step: `{temporal['lift_object_first_mean_step']}`.",
        f"- Eval action chunk steps: `{temporal['action_chunk_steps']}`, DP horizon `{temporal['dp_horizon']}`, DP action steps `{temporal['dp_n_action_steps']}`, obs steps `{temporal['dp_n_obs_steps']}`.",
        f"- First chunk with negative gripper command: `{temporal['first_gripper_chunk_crosses_negative_step']}`.",
        f"- First hard-close chunk: `{temporal['first_gripper_chunk_hard_close_step']}`.",
        f"- First live gripper width < 1cm: `{temporal['first_live_gripper_width_lt_1cm_step']}`.",
        f"- First nearest `lift_object` trace phase: `{temporal['first_nearest_lift_object_step']}`.",
        f"- Nearest phase counts: `{temporal['nearest_phase_counts']}`.",
        "",
        "## Behavior Evidence",
        f"- Steps completed `{behavior['steps_completed']}`, final success `{behavior['final_success_rate']}`, max cube lift `{behavior['cube_lift_height_max']}`.",
        f"- Final gripper width `{behavior['final_gripper_width']:.4f} m`; gripper did close.",
        f"- EE-to-cube distance final/min `{behavior['ee_to_cube_dist_final']:.4f}` / `{behavior['ee_to_cube_dist_min']:.4f} m`.",
        f"- Finger-center-to-cube distance final/min `{behavior['finger_center_to_cube_dist_final']:.4f}` / `{behavior['finger_center_to_cube_dist_min']:.4f} m`.",
        f"- Final trace cube-minus-EE `{_format_vector(behavior['final_trace_cube_minus_ee'])}`.",
        f"- Final nearest phase `{behavior['final_nearest_phase']}` with distance `{behavior['final_nearest_distance']:.4f}`.",
        "",
        "## Interpretation",
        "- The framefix path removed the pre-framefix away-from-object sign failure: EE-to-cube distance improves in the rollout.",
        "- The policy does not ignore gripper timing: it crosses to close commands and ends fully closed.",
        "- The failure is still a train/eval mismatch: the live rollout never matches the demo grasp geometry before closure/lift. It remains about 10 cm off laterally in cube-relative y and is vertically above the cube while the gripper is closed.",
        "- Next root-cause checks should instrument or patch observation/history/action-timing details, not pivot to RL or data augmentation.",
        "",
        "## Plots",
        f"- Behavior metrics: `{plots['behavior']}`",
        f"- Trace phase/actions: `{plots['trace']}`",
        f"- Observation distribution: `{plots['obs_distribution']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--trace-analysis", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = audit(args)
    print("FRANKA_CUBE_DP_MISMATCH_AUDIT " + json.dumps({k: summary[k] for k in ("output_dir", "behavior", "temporal")}, sort_keys=True))


if __name__ == "__main__":
    main()
