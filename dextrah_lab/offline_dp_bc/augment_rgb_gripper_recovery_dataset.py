"""Augment an RGB BC dataset with open-gripper recovery histories.

The RGB policy observes image plus 8-D robot state:
EE position, EE quaternion, and gripper width.  This helper duplicates full
episodes and overwrites only the gripper-width proprio feature during close and
lift phases.  The labels are unchanged, so the duplicated rows teach the policy
to command close/lift even if the closed-loop gripper failed to leave the open
state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


ROW_KEYS = {"image", "robot_state", "action", "phase_ids"}
EPISODE_KEYS = {
    "rollout_ids",
    "rollout_reset_joint_blend_alpha",
    "rollout_reset_cube_pos_blend_alpha",
    "rollout_applied_cube_pos",
    "rollout_normal_reset_cube_pos",
    "rollout_source_cube_pos",
}
GLOBAL_KEYS = {
    "source_npzs",
    "camera_eye",
    "camera_target",
    "robot_state_names",
    "filtered_source_npz",
    "filtered_source_episode_indices",
}


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    return value


def _episode_lengths(episode_ends: np.ndarray) -> np.ndarray:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return (episode_ends - starts).astype(np.int64)


def _augment_robot_state(
    robot_state: np.ndarray,
    phase_ids: np.ndarray,
    *,
    open_gripper_width: float,
    phases: set[int],
) -> np.ndarray:
    augmented = np.asarray(robot_state, dtype=np.float32).copy()
    mask = np.isin(phase_ids.astype(np.int32), np.asarray(sorted(phases), dtype=np.int32))
    augmented[mask, -1] = float(open_gripper_width)
    return augmented


def augment_dataset(
    *,
    input_path: Path,
    output_path: Path,
    report_path: Path,
    copies: int,
    open_gripper_width: float,
    phases: set[int],
) -> dict[str, Any]:
    data = np.load(input_path, allow_pickle=False)
    missing = sorted({"image", "robot_state", "action", "phase_ids", "episode_ends"}.difference(data.files))
    if missing:
        raise KeyError(f"{input_path} missing required keys: {missing}")

    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    total_rows = int(episode_ends[-1])
    episode_count = int(episode_ends.shape[0])
    robot_state = np.asarray(data["robot_state"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    if robot_state.ndim != 2 or robot_state.shape[1] != 8:
        raise ValueError(f"Expected robot_state shape (N,8), got {robot_state.shape}")
    if phase_ids.shape != (total_rows,):
        raise ValueError(f"Expected phase_ids shape ({total_rows},), got {phase_ids.shape}")

    save_kwargs: dict[str, Any] = {}
    row_blocks: dict[str, list[np.ndarray]] = {}
    episode_blocks: dict[str, list[np.ndarray]] = {}

    for key in data.files:
        if key == "episode_ends":
            continue
        value = np.asarray(data[key])
        if key in ROW_KEYS or value.shape[:1] == (total_rows,):
            row_blocks[key] = [value]
        elif key in EPISODE_KEYS or value.shape[:1] == (episode_count,):
            episode_blocks[key] = [value]
        elif key in GLOBAL_KEYS:
            save_kwargs[key] = value
        else:
            save_kwargs[key] = value

    augmented_robot = _augment_robot_state(
        robot_state,
        phase_ids,
        open_gripper_width=float(open_gripper_width),
        phases=phases,
    )
    augmented_rows = int(np.count_nonzero(np.isin(phase_ids, np.asarray(sorted(phases), dtype=np.int32))))
    for copy_idx in range(int(copies)):
        for key, blocks in row_blocks.items():
            if key == "robot_state":
                blocks.append(augmented_robot)
            else:
                blocks.append(np.asarray(data[key]))
        for key, blocks in episode_blocks.items():
            value = np.asarray(data[key])
            if key == "rollout_ids":
                value = np.asarray([f"{str(v)}_gripopen_aug{copy_idx}" for v in value.astype(str)])
            blocks.append(value)

    for key, blocks in row_blocks.items():
        save_kwargs[key] = np.concatenate(blocks, axis=0)
    for key, blocks in episode_blocks.items():
        save_kwargs[key] = np.concatenate(blocks, axis=0)

    lengths = _episode_lengths(episode_ends)
    output_lengths = np.tile(lengths, int(copies) + 1)
    output_episode_ends = np.cumsum(output_lengths.astype(np.int64))
    save_kwargs["episode_ends"] = output_episode_ends
    save_kwargs["gripper_recovery_source_npz"] = np.asarray(str(input_path))
    save_kwargs["gripper_recovery_copies"] = np.asarray(int(copies), dtype=np.int32)
    save_kwargs["gripper_recovery_open_width"] = np.asarray(float(open_gripper_width), dtype=np.float32)
    save_kwargs["gripper_recovery_phases"] = np.asarray(sorted(phases), dtype=np.int32)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **save_kwargs)

    phase_unique, phase_counts = np.unique(save_kwargs["phase_ids"], return_counts=True)
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "copies": int(copies),
        "input_rows": total_rows,
        "output_rows": int(output_episode_ends[-1]),
        "input_episodes": episode_count,
        "output_episodes": int(output_episode_ends.shape[0]),
        "augmented_rows_per_copy": augmented_rows,
        "open_gripper_width": float(open_gripper_width),
        "phases": sorted(int(v) for v in phases),
        "image_shape": list(np.asarray(save_kwargs["image"]).shape),
        "robot_state_shape": list(np.asarray(save_kwargs["robot_state"]).shape),
        "action_shape": list(np.asarray(save_kwargs["action"]).shape),
        "phase_counts": {str(int(k)): int(v) for k, v in zip(phase_unique, phase_counts)},
        "episode_lengths": output_lengths.astype(int).tolist(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--copies", type=int, default=1)
    parser.add_argument("--open-gripper-width", type=float, default=0.08)
    parser.add_argument(
        "--phase",
        action="append",
        type=int,
        default=[1, 2],
        help="Phase ids whose robot_state gripper width should be overwritten.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if int(args.copies) < 1:
        raise ValueError("--copies must be >= 1")
    summary = augment_dataset(
        input_path=args.input.expanduser().resolve(),
        output_path=args.output.expanduser().resolve(),
        report_path=args.report.expanduser().resolve(),
        copies=int(args.copies),
        open_gripper_width=float(args.open_gripper_width),
        phases={int(v) for v in args.phase},
    )
    print("FRANKA_CUBE_RGB_GRIPPER_RECOVERY_AUGMENT " + json.dumps(_to_builtin(summary), sort_keys=True))


if __name__ == "__main__":
    main()
