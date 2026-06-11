"""Convert GraspGenX/cuRobo Franka cube trajectories to lowdim BC demos."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    DextrahActionConvention,
    derive_relative_ee_actions,
    gripper_width_to_action,
    normalize_quat_wxyz,
    quat_from_axis_angle_wxyz,
)


DEFAULT_EE_OFFSET_POS = (0.0, 0.0, 0.1034)

PHASE_PRESETS: dict[str, tuple[str, ...] | None] = {
    "approach_pregrasp": ("go_to_pre_grasp_pose", "hold_at_pre_grasp"),
    "approach_grasp": (
        "go_to_pre_grasp_pose",
        "hold_at_pre_grasp",
        "go_from_pre_grasp_to_grasp_pose",
        "hold_at_grasp",
    ),
    "full_pick_lift": (
        "go_to_pre_grasp_pose",
        "hold_at_pre_grasp",
        "go_from_pre_grasp_to_grasp_pose",
        "hold_at_grasp",
        "close_fingers",
        "hold_after_close",
        "lift_object",
        "hold_after_lift",
    ),
    "all": None,
}

COMPACT_OBS_SCHEMA = (
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
)


@dataclass
class TrajectoryArrays:
    ee_pos: np.ndarray
    ee_quat_wxyz: np.ndarray
    cube_pos: np.ndarray
    cube_quat_wxyz: np.ndarray
    phases: np.ndarray
    gripper_width: np.ndarray | None = None
    gripper_action: np.ndarray | None = None
    fps: float | None = None
    source_path: str | None = None


def _stats(array: np.ndarray) -> dict[str, list[float]]:
    return {
        "min": np.min(array, axis=0).astype(float).tolist(),
        "max": np.max(array, axis=0).astype(float).tolist(),
        "mean": np.mean(array, axis=0).astype(float).tolist(),
        "std": np.std(array, axis=0).astype(float).tolist(),
    }


def _matrix_from_xyzw(translation: Sequence[float], quat_xyzw: Sequence[float]) -> np.ndarray:
    x, y, z, w = [float(v) for v in quat_xyzw]
    quat = normalize_quat_wxyz(np.asarray([w, x, y, z], dtype=np.float64))
    w, x, y, z = quat
    rot = np.array(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = rot
    out[:3, 3] = np.asarray(translation, dtype=np.float64)
    return out


def _quat_wxyz_from_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    trace = np.trace(matrix[:3, :3])
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        quat = np.array(
            [
                0.25 * s,
                (matrix[2, 1] - matrix[1, 2]) / s,
                (matrix[0, 2] - matrix[2, 0]) / s,
                (matrix[1, 0] - matrix[0, 1]) / s,
            ],
            dtype=np.float64,
        )
    else:
        diag = np.diag(matrix[:3, :3])
        idx = int(np.argmax(diag))
        if idx == 0:
            s = np.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2.0
            quat = np.array(
                [
                    (matrix[2, 1] - matrix[1, 2]) / s,
                    0.25 * s,
                    (matrix[0, 1] + matrix[1, 0]) / s,
                    (matrix[0, 2] + matrix[2, 0]) / s,
                ],
                dtype=np.float64,
            )
        elif idx == 1:
            s = np.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2.0
            quat = np.array(
                [
                    (matrix[0, 2] - matrix[2, 0]) / s,
                    (matrix[0, 1] + matrix[1, 0]) / s,
                    0.25 * s,
                    (matrix[1, 2] + matrix[2, 1]) / s,
                ],
                dtype=np.float64,
            )
        else:
            s = np.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2.0
            quat = np.array(
                [
                    (matrix[1, 0] - matrix[0, 1]) / s,
                    (matrix[0, 2] + matrix[2, 0]) / s,
                    (matrix[1, 2] + matrix[2, 1]) / s,
                    0.25 * s,
                ],
                dtype=np.float64,
            )
    return normalize_quat_wxyz(quat)


def _pose_from_matrix(matrix: Any) -> tuple[np.ndarray, np.ndarray]:
    mat = np.asarray(matrix, dtype=np.float64)
    if mat.shape != (4, 4):
        raise ValueError(f"Expected 4x4 transform, got {mat.shape}")
    return mat[:3, 3].copy(), _quat_wxyz_from_matrix(mat)


def _expand_phase_labels(frames: list[dict[str, Any]], plan_summary: Path | None) -> np.ndarray:
    phases = np.asarray([str(frame.get("phase", "plan")) for frame in frames], dtype="<U64")
    if len(set(phases.tolist())) > 1:
        return phases
    summary_path = plan_summary
    if summary_path is None and frames:
        summary_path = None
    if summary_path is not None and summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        task_segments = summary.get("task_segments", {})
        expanded: list[str] = []
        if isinstance(task_segments, dict):
            for name, count in task_segments.items():
                expanded.extend([str(name)] * int(count))
        if expanded:
            if len(expanded) < len(frames):
                expanded.extend([expanded[-1]] * (len(frames) - len(expanded)))
            return np.asarray(expanded[: len(frames)], dtype="<U64")
    return phases


def _load_robot_profile(graspgenx_root: Path, robot_config: Path):
    e2e_dir = graspgenx_root / "end2end"
    for path in (str(graspgenx_root), str(e2e_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from robot_profiles import RobotProfile
    from scene_builder import load_yaml
    from trajectory_visualizer import URDFFK

    robot_cfg = load_yaml(robot_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    fk = URDFFK(profile.urdf_path, asset_root=profile.asset_root_path)
    return profile, fk


def _compute_ee_from_fk(
    frames: list[dict[str, Any]],
    *,
    graspgenx_root: Path,
    robot_config: Path,
    run_config: Path | None,
    ee_offset_pos: Sequence[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    profile, fk = _load_robot_profile(graspgenx_root, robot_config)
    robot_base_T = np.asarray(profile.robot_base_T, dtype=np.float64)
    if run_config is not None and run_config.is_file():
        payload = json.loads(run_config.read_text(encoding="utf-8"))
        if "robot_base_T" in payload:
            robot_base_T = np.asarray(payload["robot_base_T"], dtype=np.float64)

    ee_offset = np.eye(4, dtype=np.float64)
    ee_offset[:3, 3] = np.asarray(ee_offset_pos, dtype=np.float64)

    ee_pos = []
    ee_quat = []
    gripper_width = []
    for frame in frames:
        q = np.asarray(frame.get("joint_position"), dtype=np.float64)
        if q.ndim != 1 or q.shape[0] < profile.n_arm:
            raise ValueError("FK conversion requires each frame to contain joint_position with arm joints")
        cfg = {}
        for name, value in zip(profile.arm_joint_names, q[: profile.n_arm]):
            cfg[name] = float(value)
        for idx, name in enumerate(profile.gripper_joint_names):
            col = profile.n_arm + idx
            cfg[name] = float(q[col]) if col < q.shape[0] else profile.open_value(name)
        link_pose = fk.fk(cfg, base_T=robot_base_T, link_names=[profile.tool_frame])[profile.tool_frame]
        ee_pose = np.asarray(link_pose, dtype=np.float64) @ ee_offset
        pos, quat = _pose_from_matrix(ee_pose)
        ee_pos.append(pos)
        ee_quat.append(quat)
        if q.shape[0] >= profile.n_arm + 2:
            gripper_width.append(float(q[profile.n_arm]) + float(q[profile.n_arm + 1]))
        elif q.shape[0] >= profile.n_arm + 1:
            gripper_width.append(2.0 * float(q[profile.n_arm]))

    width = np.asarray(gripper_width, dtype=np.float32) if gripper_width else None
    return np.asarray(ee_pos, dtype=np.float32), np.asarray(ee_quat, dtype=np.float32), width


def load_task_space_npz(path: Path) -> TrajectoryArrays:
    data = np.load(path, allow_pickle=False)
    ee_pos = np.asarray(data["ee_pos"], dtype=np.float32)
    ee_quat = np.asarray(data["ee_quat_wxyz"] if "ee_quat_wxyz" in data else data["ee_quat"], dtype=np.float32)
    cube_pos = np.asarray(data["cube_pos"], dtype=np.float32)
    if "cube_quat_wxyz" in data:
        cube_quat = np.asarray(data["cube_quat_wxyz"], dtype=np.float32)
    else:
        cube_quat = np.zeros((ee_pos.shape[0], 4), dtype=np.float32)
        cube_quat[:, 0] = 1.0
    phases = (
        np.asarray(data["phase"]).astype("<U64")
        if "phase" in data
        else np.full(ee_pos.shape[0], "plan", dtype="<U64")
    )
    gripper_width = np.asarray(data["gripper_width"], dtype=np.float32) if "gripper_width" in data else None
    gripper_action = np.asarray(data["gripper_action"], dtype=np.float32) if "gripper_action" in data else None
    fps = float(np.asarray(data["fps"]).item()) if "fps" in data else None
    return TrajectoryArrays(
        ee_pos=ee_pos,
        ee_quat_wxyz=ee_quat,
        cube_pos=cube_pos,
        cube_quat_wxyz=cube_quat,
        phases=phases,
        gripper_width=gripper_width,
        gripper_action=gripper_action,
        fps=fps,
        source_path=str(path),
    )


def load_graspgenx_trajectory_json(
    path: Path,
    *,
    graspgenx_root: Path | None = None,
    robot_config: Path | None = None,
    run_config: Path | None = None,
    plan_summary: Path | None = None,
    ee_offset_pos: Sequence[float] = DEFAULT_EE_OFFSET_POS,
) -> TrajectoryArrays:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"{path} does not contain a non-empty frames list")
    if plan_summary is None:
        sibling = path.parent / "plan_summary.json"
        plan_summary = sibling if sibling.is_file() else None
    if run_config is None:
        sibling = path.parent / "run_config.json"
        run_config = sibling if sibling.is_file() else None

    phases = _expand_phase_labels(frames, plan_summary)

    ee_pos = []
    ee_quat = []
    explicit_ee = True
    for frame in frames:
        if "ee_pose" in frame:
            pos, quat = _pose_from_matrix(frame["ee_pose"])
        elif "ee_pos" in frame and ("ee_quat_wxyz" in frame or "ee_quat" in frame):
            pos = np.asarray(frame["ee_pos"], dtype=np.float64)
            quat = np.asarray(frame.get("ee_quat_wxyz", frame.get("ee_quat")), dtype=np.float64)
        else:
            explicit_ee = False
            break
        ee_pos.append(pos)
        ee_quat.append(quat)
    gripper_width = None
    if explicit_ee:
        ee_pos_arr = np.asarray(ee_pos, dtype=np.float32)
        ee_quat_arr = np.asarray(ee_quat, dtype=np.float32)
    elif graspgenx_root is not None and robot_config is not None:
        ee_pos_arr, ee_quat_arr, gripper_width = _compute_ee_from_fk(
            frames,
            graspgenx_root=graspgenx_root,
            robot_config=robot_config,
            run_config=run_config,
            ee_offset_pos=ee_offset_pos,
        )
    else:
        raise ValueError(
            "trajectory JSON lacks explicit EE poses. Provide --graspgenx-root and --robot-config "
            "so FK can compute panda_hand plus the DEXTRAH EE offset."
        )

    cube_pos = []
    cube_quat = []
    for frame in frames:
        object_poses = frame.get("object_poses") or {}
        object_pose = object_poses.get("object")
        if object_pose is None and object_poses:
            object_pose = next(iter(object_poses.values()))
        if object_pose is None:
            static = payload.get("static") or {}
            object_static = static.get("object") or next(iter(static.values()), None)
            object_pose = object_static.get("transform") if isinstance(object_static, dict) else None
        if object_pose is None:
            raise ValueError(f"Could not find object pose in {path}")
        pos, quat = _pose_from_matrix(object_pose)
        cube_pos.append(pos)
        cube_quat.append(quat)

    fps = float(payload["fps"]) if "fps" in payload else None
    return TrajectoryArrays(
        ee_pos=ee_pos_arr,
        ee_quat_wxyz=ee_quat_arr,
        cube_pos=np.asarray(cube_pos, dtype=np.float32),
        cube_quat_wxyz=np.asarray(cube_quat, dtype=np.float32),
        phases=phases,
        gripper_width=gripper_width,
        fps=fps,
        source_path=str(path),
    )


def compact_observation(
    trajectory: TrajectoryArrays,
    *,
    cube_lift_height: float = 0.16,
    default_gripper_width: float = DEFAULT_DEXTRAH_ACTION_CONVENTION.max_gripper_width,
) -> np.ndarray:
    n = trajectory.ee_pos.shape[0]
    cube_goal_pos = trajectory.cube_pos.copy()
    cube_goal_pos[:, 2] = trajectory.cube_pos[0, 2] + float(cube_lift_height)
    if trajectory.gripper_width is None:
        gripper_width = np.full((n, 1), float(default_gripper_width), dtype=np.float32)
    else:
        gripper_width = np.asarray(trajectory.gripper_width, dtype=np.float32).reshape(n, 1)
    obs = np.concatenate(
        (
            trajectory.ee_pos,
            normalize_quat_wxyz(trajectory.ee_quat_wxyz).astype(np.float32),
            trajectory.cube_pos,
            normalize_quat_wxyz(trajectory.cube_quat_wxyz).astype(np.float32),
            trajectory.cube_pos - trajectory.ee_pos,
            cube_goal_pos - trajectory.cube_pos,
            gripper_width,
        ),
        axis=-1,
    )
    if obs.shape[1] != len(COMPACT_OBS_SCHEMA):
        raise RuntimeError(f"Compact obs schema mismatch: got {obs.shape[1]}, expected {len(COMPACT_OBS_SCHEMA)}")
    return obs.astype(np.float32)


def select_phases(trajectory: TrajectoryArrays, phase_names: Sequence[str] | None) -> TrajectoryArrays:
    if phase_names is None:
        return trajectory
    phase_set = set(phase_names)
    mask = np.asarray([phase in phase_set for phase in trajectory.phases], dtype=bool)
    if not np.any(mask):
        raise ValueError(f"No frames matched requested phases {sorted(phase_set)} in {trajectory.source_path}")
    idx = np.nonzero(mask)[0]
    # Keep contiguous blocks only. A Diffusion Policy episode should not jump
    # across omitted close/lift phases.
    if np.any(np.diff(idx) != 1):
        raise ValueError(
            f"Selected phases are not contiguous in {trajectory.source_path}; choose a broader phase_set."
        )
    width = trajectory.gripper_width[idx] if trajectory.gripper_width is not None else None
    grip = trajectory.gripper_action[idx] if trajectory.gripper_action is not None else None
    return TrajectoryArrays(
        ee_pos=trajectory.ee_pos[idx],
        ee_quat_wxyz=trajectory.ee_quat_wxyz[idx],
        cube_pos=trajectory.cube_pos[idx],
        cube_quat_wxyz=trajectory.cube_quat_wxyz[idx],
        phases=trajectory.phases[idx],
        gripper_width=width,
        gripper_action=grip,
        fps=trajectory.fps,
        source_path=trajectory.source_path,
    )


def trajectory_to_episode(
    trajectory: TrajectoryArrays,
    *,
    convention: DextrahActionConvention = DEFAULT_DEXTRAH_ACTION_CONVENTION,
    cube_lift_height: float = 0.16,
) -> dict[str, np.ndarray]:
    if trajectory.ee_pos.shape[0] < 2:
        raise ValueError(f"Trajectory {trajectory.source_path} has fewer than two selected frames")
    obs = compact_observation(
        trajectory,
        cube_lift_height=cube_lift_height,
        default_gripper_width=convention.max_gripper_width,
    )
    action = derive_relative_ee_actions(
        trajectory.ee_pos,
        trajectory.ee_quat_wxyz,
        gripper_action=trajectory.gripper_action,
        gripper_width=trajectory.gripper_width,
        phases=trajectory.phases,
        convention=convention,
    )
    if obs.shape[0] != action.shape[0]:
        raise RuntimeError(f"obs/action length mismatch: {obs.shape} vs {action.shape}")
    phase_vocab = {name: idx for idx, name in enumerate(sorted(set(trajectory.phases.tolist())))}
    phase_ids = np.asarray([phase_vocab[p] for p in trajectory.phases], dtype=np.int32)
    return {"obs": obs, "action": action, "phase_ids": phase_ids}


def write_demo_dataset(
    episodes: Sequence[dict[str, np.ndarray]],
    output_path: Path,
    *,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if not episodes:
        raise ValueError("No episodes to write")
    obs = np.concatenate([ep["obs"] for ep in episodes], axis=0).astype(np.float32)
    action = np.concatenate([ep["action"] for ep in episodes], axis=0).astype(np.float32)
    phase_ids = np.concatenate([ep["phase_ids"] for ep in episodes], axis=0).astype(np.int32)
    ends = np.cumsum([ep["obs"].shape[0] for ep in episodes]).astype(np.int64)
    if obs.shape[0] != action.shape[0]:
        raise RuntimeError(f"obs/action length mismatch: {obs.shape} vs {action.shape}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        obs=obs,
        action=action,
        episode_ends=ends,
        phase_ids=phase_ids,
    )
    summary = {
        **metadata,
        "dataset_path": str(output_path),
        "num_episodes": len(episodes),
        "num_steps": int(obs.shape[0]),
        "obs_dim": int(obs.shape[1]),
        "action_dim": int(action.shape[1]),
        "obs_schema": list(COMPACT_OBS_SCHEMA),
        "action_schema": [
            "rel_ee_dx_scaled",
            "rel_ee_dy_scaled",
            "rel_ee_dz_scaled",
            "rel_ee_drx_scaled",
            "rel_ee_dry_scaled",
            "rel_ee_drz_scaled",
            "gripper_raw_open_positive",
        ],
        "obs_stats": _stats(obs),
        "action_stats": _stats(action),
    }
    meta_path = output_path.with_suffix(output_path.suffix + ".metadata.json")
    meta_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _load_input(path: Path, args: argparse.Namespace) -> TrajectoryArrays:
    suffix = path.suffix.lower()
    if args.input_format == "npz" or (args.input_format == "auto" and suffix == ".npz"):
        return load_task_space_npz(path)
    if args.input_format == "json" or (args.input_format == "auto" and suffix == ".json"):
        return load_graspgenx_trajectory_json(
            path,
            graspgenx_root=args.graspgenx_root,
            robot_config=args.robot_config,
            run_config=args.run_config,
            plan_summary=args.plan_summary,
            ee_offset_pos=args.ee_offset_pos,
        )
    raise ValueError(f"Cannot infer input format for {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+", help="Trajectory JSON or task-space NPZ files")
    parser.add_argument("--output", type=Path, required=True, help="Output dataset .npz")
    parser.add_argument("--input-format", choices=("auto", "json", "npz"), default="auto")
    parser.add_argument("--phase-set", choices=tuple(PHASE_PRESETS), default="approach_pregrasp")
    parser.add_argument("--phase", action="append", default=None, help="Explicit phase label to include")
    parser.add_argument("--graspgenx-root", type=Path, default=None)
    parser.add_argument("--robot-config", type=Path, default=None)
    parser.add_argument("--run-config", type=Path, default=None)
    parser.add_argument("--plan-summary", type=Path, default=None)
    parser.add_argument("--cube-lift-height", type=float, default=0.16)
    parser.add_argument("--max-gripper-width", type=float, default=0.08)
    parser.add_argument("--ee-offset-pos", type=float, nargs=3, default=list(DEFAULT_EE_OFFSET_POS))
    parser.add_argument("--no-clip-actions", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    convention = DextrahActionConvention(
        max_gripper_width=float(args.max_gripper_width),
        clip_actions=not bool(args.no_clip_actions),
    )
    selected_phases = tuple(args.phase) if args.phase else PHASE_PRESETS[args.phase_set]
    episodes = []
    sources = []
    for path in args.inputs:
        traj = _load_input(path.expanduser().resolve(), args)
        selected = select_phases(traj, selected_phases)
        episodes.append(trajectory_to_episode(selected, convention=convention, cube_lift_height=args.cube_lift_height))
        sources.append(
            {
                "path": str(path),
                "frames_in": int(traj.ee_pos.shape[0]),
                "frames_selected": int(selected.ee_pos.shape[0]),
                "fps": selected.fps,
                "phases_selected": sorted(set(selected.phases.tolist())),
            }
        )
    metadata = {
        "source": "graspgenx_curobo_to_dextrah_franka_cube_lowdim",
        "phase_set": args.phase_set,
        "selected_phases": list(selected_phases) if selected_phases is not None else None,
        "action_convention": asdict(convention),
        "official_diffusion_policy_source": {
            "repo": "https://github.com/real-stanford/diffusion_policy",
            "project_page": "https://diffusion-policy.cs.columbia.edu/",
        },
        "sources": sources,
        "notes": [
            "Actions are DEXTRAH normalized relative EE deltas plus raw gripper action.",
            "Compact observations are for a Diffusion Policy wrapper/distillation path, not direct PPO weight loading.",
        ],
    }
    summary = write_demo_dataset(episodes, args.output.expanduser().resolve(), metadata=metadata)
    print("FRANKA_CUBE_DP_BC_CONVERTED " + json.dumps({k: summary[k] for k in ("dataset_path", "num_episodes", "num_steps", "obs_dim", "action_dim")}, sort_keys=True))


if __name__ == "__main__":
    main()
