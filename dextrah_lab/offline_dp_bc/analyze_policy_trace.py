"""Analyze DEXTRAH Franka cube DP eval policy-call traces.

This compares live low-dimensional observations from
``eval_franka_cube_dp_policy.py --debug_policy_trace_*`` against a converted
demonstration dataset. It also reports how action-frame policy commands map
back to world-frame end-effector deltas under the DEXTRAH action convention.
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
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    normalized_action_to_world_delta,
)
from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


POSITION_FEATURE_IDX = np.asarray([0, 1, 2, 7, 8, 9, 14, 15, 16, 17, 18, 19, 20], dtype=np.int64)


def _phase_names() -> list[str]:
    # trajectory_to_episode used sorted(set(phases)) when writing phase_ids.
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _episode_local_index(global_idx: int, episode_ends: np.ndarray) -> tuple[int, int]:
    episode_idx = int(np.searchsorted(episode_ends, global_idx, side="right"))
    episode_start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    return episode_idx, int(global_idx - episode_start)


def _nearest_by_scaled_features(
    dataset_obs: np.ndarray,
    query_obs: np.ndarray,
    *,
    feature_idx: np.ndarray,
) -> tuple[int, float]:
    feature_std = np.maximum(dataset_obs[:, feature_idx].std(axis=0), 1.0e-4)
    distances = np.sqrt((((dataset_obs[:, feature_idx] - query_obs[feature_idx]) / feature_std) ** 2).mean(axis=1))
    idx = int(np.argmin(distances))
    return idx, float(distances[idx])


def _phase_min_distances(dataset_obs: np.ndarray, phase_ids: np.ndarray, query_obs: np.ndarray) -> dict[str, float]:
    names = _phase_names()
    feature_std = np.maximum(dataset_obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4)
    distances = np.sqrt(
        (((dataset_obs[:, POSITION_FEATURE_IDX] - query_obs[POSITION_FEATURE_IDX]) / feature_std) ** 2).mean(axis=1)
    )
    out: dict[str, float] = {}
    for phase_id, name in enumerate(names):
        mask = phase_ids == phase_id
        if np.any(mask):
            out[name] = float(np.min(distances[mask]))
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    steps = np.asarray([row["step"] for row in rows], dtype=float)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    axes[0, 0].plot(steps, [row["nearest_position_distance"] for row in rows], marker="o")
    axes[0, 0].set_title("Nearest Demo Distance")
    axes[0, 0].set_xlabel("env step")
    axes[0, 0].set_ylabel("scaled position/gripper distance")
    axes[0, 0].grid(True, alpha=0.25)

    axes[0, 1].plot(steps, [row["live_cube_minus_ee_x"] for row in rows], marker="o", label="x")
    axes[0, 1].plot(steps, [row["live_cube_minus_ee_y"] for row in rows], marker="o", label="y")
    axes[0, 1].plot(steps, [row["live_cube_minus_ee_z"] for row in rows], marker="o", label="z")
    axes[0, 1].set_title("Live Cube Minus EE")
    axes[0, 1].set_xlabel("env step")
    axes[0, 1].set_ylabel("m")
    axes[0, 1].grid(True, alpha=0.25)
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(steps, [row["first_action_x"] for row in rows], marker="o", label="label/action x")
    axes[1, 0].plot(steps, [row["first_action_y"] for row in rows], marker="o", label="label/action y")
    axes[1, 0].plot(steps, [row["env_world_delta_x"] for row in rows], marker="x", label="env world dx")
    axes[1, 0].plot(steps, [row["env_world_delta_y"] for row in rows], marker="x", label="env world dy")
    axes[1, 0].axhline(0.0, color="black", linewidth=0.8)
    axes[1, 0].set_title("Action Frame Sign")
    axes[1, 0].set_xlabel("env step")
    axes[1, 0].grid(True, alpha=0.25)
    axes[1, 0].legend(fontsize=8)

    axes[1, 1].plot(steps, [row["chunk_gripper_action_min"] for row in rows], marker="o", label="chunk min")
    axes[1, 1].plot(steps, [row["chunk_gripper_action_max"] for row in rows], marker="o", label="chunk max")
    axes[1, 1].plot(steps, [row["live_gripper_width"] for row in rows], marker="x", label="width m")
    axes[1, 1].axhline(0.0, color="black", linewidth=0.8)
    axes[1, 1].set_title("Open-Gripper Trace")
    axes[1, 1].set_xlabel("env step")
    axes[1, 1].grid(True, alpha=0.25)
    axes[1, 1].legend(fontsize=8)

    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _mean_vector(rows: list[dict[str, Any]], prefix: str) -> list[float] | None:
    if not rows:
        return None
    return [
        float(np.mean([row[f"{prefix}_{axis}"] for row in rows]))
        for axis in "xyz"
    ]


def _norm(values: list[float] | None) -> float | None:
    if values is None:
        return None
    return float(np.linalg.norm(np.asarray(values, dtype=np.float32)))


def _build_analysis(rows: list[dict[str, Any]], all_pregrasp: bool) -> str:
    if not rows:
        return "No policy trace records were available for analysis."

    nearest_delta = float(rows[-1]["nearest_position_distance"] - rows[0]["nearest_position_distance"])
    cube_minus_ee_start = [rows[0][f"live_cube_minus_ee_{axis}"] for axis in "xyz"]
    cube_minus_ee_end = [rows[-1][f"live_cube_minus_ee_{axis}"] for axis in "xyz"]
    cube_norm_start = _norm(cube_minus_ee_start)
    cube_norm_end = _norm(cube_minus_ee_end)
    gripper_min = min(row["chunk_gripper_action_min"] for row in rows)
    gripper_max = max(row["chunk_gripper_action_max"] for row in rows)
    mean_first = _mean_vector(rows, "first_action")
    mean_world = _mean_vector(rows, "env_world_delta")

    phase_msg = (
        "All traced states remain nearest to go_to_pre_grasp_pose"
        if all_pregrasp
        else "Traced states include non-pregrasp nearest-neighbor phases"
    )
    distance_msg = (
        f"nearest-demo distance increased by {nearest_delta:.3f}"
        if nearest_delta > 0.0
        else f"nearest-demo distance decreased by {abs(nearest_delta):.3f}"
    )
    cube_msg = (
        f"live cube-minus-EE norm changed {cube_norm_start:.3f}->{cube_norm_end:.3f} m"
        if cube_norm_start is not None and cube_norm_end is not None
        else "live cube-minus-EE norm unavailable"
    )
    if gripper_min > 0.5:
        gripper_msg = f"chunk gripper commands stayed open/positive [{gripper_min:.3f}, {gripper_max:.3f}]"
    elif gripper_max < -0.5:
        gripper_msg = f"chunk gripper commands stayed closed/negative [{gripper_min:.3f}, {gripper_max:.3f}]"
    else:
        gripper_msg = f"chunk gripper commands crossed neutral [{gripper_min:.3f}, {gripper_max:.3f}]"
    action_msg = (
        f"mean first action-frame xyz={mean_first} maps to mean world delta xyz={mean_world}"
        if mean_first is not None and mean_world is not None
        else "action-frame/world-delta means unavailable"
    )
    return f"{phase_msg}; {distance_msg}; {cube_msg}; {gripper_msg}; {action_msg}."


def analyze(dataset_path: Path, trace_path: Path, output_dir: Path) -> dict[str, Any]:
    dataset = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(dataset["obs"], dtype=np.float32)
    action = np.asarray(dataset["action"], dtype=np.float32)
    phase_ids = np.asarray(dataset["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(dataset["episode_ends"], dtype=np.int64)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    records = trace["policy_calls"]
    phase_names = _phase_names()

    rows: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        live_obs = np.asarray(record["lowdim_obs"], dtype=np.float32)
        nearest_idx, nearest_distance = _nearest_by_scaled_features(obs, live_obs, feature_idx=POSITION_FEATURE_IDX)
        episode_idx, episode_local_idx = _episode_local_index(nearest_idx, episode_ends)
        nearest_phase_id = int(phase_ids[nearest_idx])
        first_action = np.asarray(record["first_action"], dtype=np.float32)
        env_world_delta = normalized_action_to_world_delta(
            first_action[None, :], convention=DEFAULT_DEXTRAH_ACTION_CONVENTION
        )[0]
        label_world_delta = first_action[:6] * DEFAULT_DEXTRAH_ACTION_CONVENTION.pose_scale
        next_live_delta = [None, None, None]
        if idx + 1 < len(records):
            next_obs = np.asarray(records[idx + 1]["lowdim_obs"], dtype=np.float32)
            next_live_delta = (next_obs[:3] - live_obs[:3]).astype(float).tolist()

        row: dict[str, Any] = {
            "policy_call_index": int(record["policy_call_index"]),
            "step": int(record["step"]),
            "nearest_position_global_idx": nearest_idx,
            "nearest_position_episode": episode_idx,
            "nearest_position_episode_idx": episode_local_idx,
            "nearest_position_phase_id": nearest_phase_id,
            "nearest_position_phase": phase_names[nearest_phase_id],
            "nearest_position_distance": nearest_distance,
            "nearest_action_x": float(action[nearest_idx, 0]),
            "nearest_action_y": float(action[nearest_idx, 1]),
            "nearest_action_z": float(action[nearest_idx, 2]),
            "nearest_action_gripper": float(action[nearest_idx, 6]),
            "nearest_gripper_width": float(obs[nearest_idx, 20]),
            "live_gripper_width": float(live_obs[20]),
            "live_cube_minus_ee_x": float(live_obs[14]),
            "live_cube_minus_ee_y": float(live_obs[15]),
            "live_cube_minus_ee_z": float(live_obs[16]),
            "first_action_x": float(first_action[0]),
            "first_action_y": float(first_action[1]),
            "first_action_z": float(first_action[2]),
            "first_action_gripper": float(first_action[6]),
            "label_world_delta_x": float(label_world_delta[0]),
            "label_world_delta_y": float(label_world_delta[1]),
            "label_world_delta_z": float(label_world_delta[2]),
            "env_world_delta_x": float(env_world_delta[0]),
            "env_world_delta_y": float(env_world_delta[1]),
            "env_world_delta_z": float(env_world_delta[2]),
            "actual_next_ee_delta_x": next_live_delta[0],
            "actual_next_ee_delta_y": next_live_delta[1],
            "actual_next_ee_delta_z": next_live_delta[2],
            "chunk_gripper_action_min": float(record["chunk_gripper_action_min"]),
            "chunk_gripper_action_max": float(record["chunk_gripper_action_max"]),
            "phase_min_distances": _phase_min_distances(obs, phase_ids, live_obs),
        }
        rows.append(row)

    nearest_phases = [row["nearest_position_phase"] for row in rows]
    all_pregrasp = all(phase == "go_to_pre_grasp_pose" for phase in nearest_phases)
    live_cube_minus_ee_start = [rows[0][f"live_cube_minus_ee_{axis}"] for axis in "xyz"] if rows else None
    live_cube_minus_ee_end = [rows[-1][f"live_cube_minus_ee_{axis}"] for axis in "xyz"] if rows else None
    summary = {
        "dataset": str(dataset_path),
        "trace": str(trace_path),
        "output_dir": str(output_dir),
        "records": len(rows),
        "phase_names": phase_names,
        "nearest_phases": nearest_phases,
        "all_nearest_pregrasp": all_pregrasp,
        "nearest_distance_start": rows[0]["nearest_position_distance"] if rows else None,
        "nearest_distance_end": rows[-1]["nearest_position_distance"] if rows else None,
        "nearest_distance_delta": (
            float(rows[-1]["nearest_position_distance"] - rows[0]["nearest_position_distance"]) if rows else None
        ),
        "live_cube_minus_ee_start": live_cube_minus_ee_start,
        "live_cube_minus_ee_end": live_cube_minus_ee_end,
        "live_cube_minus_ee_norm_start": _norm(live_cube_minus_ee_start),
        "live_cube_minus_ee_norm_end": _norm(live_cube_minus_ee_end),
        "mean_first_action_xyz": _mean_vector(rows, "first_action"),
        "mean_env_world_delta_xyz": _mean_vector(rows, "env_world_delta"),
        "chunk_gripper_action_min": min(row["chunk_gripper_action_min"] for row in rows) if rows else None,
        "chunk_gripper_action_max": max(row["chunk_gripper_action_max"] for row in rows) if rows else None,
        "analysis": _build_analysis(rows, all_pregrasp),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "trace_phase_comparison.csv", rows)
    (output_dir / "trace_phase_comparison.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _plot(rows, output_dir / "trace_phase_comparison.png")
    return {"summary": summary, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(args.dataset.expanduser().resolve(), args.trace.expanduser().resolve(), args.output_dir.expanduser().resolve())
    print("FRANKA_CUBE_DP_TRACE_ANALYSIS " + json.dumps(payload["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
