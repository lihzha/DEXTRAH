"""Combine accepted Franka cube RGB relabel NPZs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _episode_lengths(episode_ends: np.ndarray) -> np.ndarray:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return (episode_ends - starts).astype(np.int64)


def _read_required(data: np.lib.npyio.NpzFile, key: str, source: Path) -> np.ndarray:
    if key not in data.files:
        raise KeyError(f"{source} is missing required key {key!r}")
    return np.asarray(data[key])


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = [p.expanduser().resolve() for p in args.input]
    output_path = args.output.expanduser().resolve()
    report_path = args.report.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    image_parts: list[np.ndarray] = []
    robot_state_parts: list[np.ndarray] = []
    action_parts: list[np.ndarray] = []
    phase_parts: list[np.ndarray] = []
    episode_lengths: list[int] = []
    rollout_ids: list[str] = []
    joint_alphas: list[float] = []
    cube_alphas: list[float] = []
    applied_cube_pos_parts: list[np.ndarray] = []
    normal_reset_cube_pos_parts: list[np.ndarray] = []
    source_cube_pos_parts: list[np.ndarray] = []
    source_rows: list[dict[str, Any]] = []
    camera_eye: np.ndarray | None = None
    camera_target: np.ndarray | None = None
    robot_state_names: np.ndarray | None = None

    for path in input_paths:
        data = np.load(path, allow_pickle=False)
        image = _read_required(data, "image", path).astype(np.uint8)
        robot_state = _read_required(data, "robot_state", path).astype(np.float32)
        action = _read_required(data, "action", path).astype(np.float32)
        episode_ends = _read_required(data, "episode_ends", path).astype(np.int64)
        phase_ids = _read_required(data, "phase_ids", path).astype(np.int32)
        if image.ndim != 4 or image.shape[-1] != 3:
            raise ValueError(f"{path}: expected image shape (N,H,W,3), got {image.shape}")
        if robot_state.shape != (image.shape[0], 8):
            raise ValueError(f"{path}: expected robot_state shape ({image.shape[0]},8), got {robot_state.shape}")
        if action.shape != (image.shape[0], 7):
            raise ValueError(f"{path}: expected action shape ({image.shape[0]},7), got {action.shape}")
        if phase_ids.shape != (image.shape[0],):
            raise ValueError(f"{path}: expected phase_ids shape ({image.shape[0]},), got {phase_ids.shape}")
        if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(image.shape[0]):
            raise ValueError(f"{path}: episode_ends must be cumulative exclusive ends ending at image length")

        lengths = _episode_lengths(episode_ends)
        n_episodes = int(lengths.shape[0])
        image_parts.append(image)
        robot_state_parts.append(robot_state)
        action_parts.append(action)
        phase_parts.append(phase_ids)
        episode_lengths.extend(int(v) for v in lengths.tolist())

        if "rollout_ids" in data.files:
            ids = np.asarray(data["rollout_ids"]).astype(str).reshape(-1)
            if ids.shape[0] != n_episodes:
                raise ValueError(f"{path}: rollout_ids has {ids.shape[0]} rows for {n_episodes} episodes")
            rollout_ids.extend(ids.tolist())
        else:
            rollout_ids.extend(f"{path.stem}_episode_{idx}" for idx in range(n_episodes))

        for key, target in [
            ("rollout_reset_joint_blend_alpha", joint_alphas),
            ("rollout_reset_cube_pos_blend_alpha", cube_alphas),
        ]:
            if key in data.files:
                values = np.asarray(data[key], dtype=np.float32).reshape(-1)
                if values.shape[0] != n_episodes:
                    raise ValueError(f"{path}: {key} has {values.shape[0]} rows for {n_episodes} episodes")
                target.extend(float(v) for v in values.tolist())
            else:
                target.extend(float("nan") for _ in range(n_episodes))

        for key, target in [
            ("rollout_applied_cube_pos", applied_cube_pos_parts),
            ("rollout_normal_reset_cube_pos", normal_reset_cube_pos_parts),
            ("rollout_source_cube_pos", source_cube_pos_parts),
        ]:
            if key in data.files:
                values = np.asarray(data[key], dtype=np.float32)
                if values.shape != (n_episodes, 3):
                    raise ValueError(f"{path}: {key} expected shape ({n_episodes},3), got {values.shape}")
                target.append(values)
            else:
                target.append(np.full((n_episodes, 3), np.nan, dtype=np.float32))

        if camera_eye is None and "camera_eye" in data.files:
            camera_eye = np.asarray(data["camera_eye"], dtype=np.float32)
        if camera_target is None and "camera_target" in data.files:
            camera_target = np.asarray(data["camera_target"], dtype=np.float32)
        if robot_state_names is None and "robot_state_names" in data.files:
            robot_state_names = np.asarray(data["robot_state_names"]).astype(str)
        source_rows.append(
            {
                "path": str(path),
                "image_shape": list(image.shape),
                "robot_state_shape": list(robot_state.shape),
                "action_shape": list(action.shape),
                "episode_lengths": lengths.astype(int).tolist(),
                "rollout_ids": rollout_ids[-n_episodes:],
            }
        )

    image_out = np.concatenate(image_parts, axis=0).astype(np.uint8)
    robot_state_out = np.concatenate(robot_state_parts, axis=0).astype(np.float32)
    action_out = np.concatenate(action_parts, axis=0).astype(np.float32)
    phase_out = np.concatenate(phase_parts, axis=0).astype(np.int32)
    episode_ends_out = np.cumsum(np.asarray(episode_lengths, dtype=np.int64))
    applied_cube_pos_out = np.concatenate(applied_cube_pos_parts, axis=0).astype(np.float32)
    normal_reset_cube_pos_out = np.concatenate(normal_reset_cube_pos_parts, axis=0).astype(np.float32)
    source_cube_pos_out = np.concatenate(source_cube_pos_parts, axis=0).astype(np.float32)

    np.savez_compressed(
        output_path,
        image=image_out,
        robot_state=robot_state_out,
        action=action_out,
        episode_ends=episode_ends_out,
        phase_ids=phase_out,
        rollout_ids=np.asarray(rollout_ids),
        rollout_reset_joint_blend_alpha=np.asarray(joint_alphas, dtype=np.float32),
        rollout_reset_cube_pos_blend_alpha=np.asarray(cube_alphas, dtype=np.float32),
        rollout_applied_cube_pos=applied_cube_pos_out,
        rollout_normal_reset_cube_pos=normal_reset_cube_pos_out,
        rollout_source_cube_pos=source_cube_pos_out,
        source_npzs=np.asarray([str(path) for path in input_paths]),
        camera_eye=np.asarray([] if camera_eye is None else camera_eye, dtype=np.float32),
        camera_target=np.asarray([] if camera_target is None else camera_target, dtype=np.float32),
        robot_state_names=np.asarray(
            [
                "ee_pos_x",
                "ee_pos_y",
                "ee_pos_z",
                "ee_quat_w",
                "ee_quat_x",
                "ee_quat_y",
                "ee_quat_z",
                "gripper_width",
            ]
            if robot_state_names is None
            else robot_state_names.astype(str).tolist()
        ),
    )

    unique_phase, phase_counts = np.unique(phase_out, return_counts=True)
    summary = {
        "inputs": source_rows,
        "output": str(output_path),
        "image_shape": list(image_out.shape),
        "robot_state_shape": list(robot_state_out.shape),
        "action_shape": list(action_out.shape),
        "episode_count": int(episode_ends_out.shape[0]),
        "episode_lengths": [int(v) for v in episode_lengths],
        "phase_counts": {str(int(k)): int(v) for k, v in zip(unique_phase, phase_counts)},
        "joint_reset_alpha_values": sorted({round(float(v), 6) for v in joint_alphas if np.isfinite(v)}),
        "cube_reset_alpha_values": sorted({round(float(v), 6) for v in cube_alphas if np.isfinite(v)}),
    }
    finite_applied = applied_cube_pos_out[np.isfinite(applied_cube_pos_out).all(axis=1)]
    if finite_applied.size:
        xy = finite_applied[:, :2]
        summary["applied_cube_xy_min"] = xy.min(axis=0).astype(float).tolist()
        summary["applied_cube_xy_max"] = xy.max(axis=0).astype(float).tolist()
        summary["applied_cube_xy_unique_rounded_1mm"] = int(np.unique(np.round(xy, 3), axis=0).shape[0])
    (report_path.parent / "combined_contact_relabel_rgb_summary.json").write_text(
        json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Combined Contact Relabel RGB Dataset",
        "",
        f"- output: `{output_path}`",
        f"- input count: `{len(input_paths)}`",
        f"- image/robot/action: `{tuple(image_out.shape)}` / `{tuple(robot_state_out.shape)}` / `{tuple(action_out.shape)}`",
        f"- episodes: `{int(episode_ends_out.shape[0])}`",
        f"- phase counts: `{summary['phase_counts']}`",
        f"- joint reset alpha values: `{summary['joint_reset_alpha_values']}`",
        f"- cube reset alpha values: `{summary['cube_reset_alpha_values']}`",
        f"- applied cube XY min/max: `{summary.get('applied_cube_xy_min')}` / `{summary.get('applied_cube_xy_max')}`",
        f"- unique applied cube XY rounded to 1mm: `{summary.get('applied_cube_xy_unique_rounded_1mm')}`",
        "",
        "## Inputs",
        "",
        "| input | episodes | rows | rollout ids |",
        "|---|---:|---:|---|",
    ]
    for row in source_rows:
        lines.append(
            f"| `{row['path']}` | `{len(row['episode_lengths'])}` | "
            f"`{row['image_shape'][0]}` | `{row['rollout_ids']}` |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FRANKA_CUBE_COMBINED_CONTACT_RELABEL_RGB " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
