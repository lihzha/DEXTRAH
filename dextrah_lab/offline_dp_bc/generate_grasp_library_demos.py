"""Generate geometric Franka cube approach demos from a GraspGenX grasp library.

This is a bounded bridge utility, not a replacement for cuRobo trajectory
exports. It consumes object-local GraspGenX grasps, samples DEXTRAH cube reset
poses, and interpolates approach-to-pregrasp EE waypoints in the same lowdim
schema used by the official Diffusion Policy adapter.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .action_conversion import DextrahActionConvention
from .trajectory_conversion import (
    DEFAULT_EE_OFFSET_POS,
    TrajectoryArrays,
    _quat_wxyz_from_matrix,
    trajectory_to_episode,
    write_demo_dataset,
)


FRANKA_CUBE_PICKUP_X = -0.36
FRANKA_CUBE_PICKUP_Y = -0.12
FRANKA_TABLE_SURFACE_Z = 0.72 + 0.5 * 0.052
FRANKA_CUBE_SIZE = 0.06
FRANKA_CUBE_SPAWN_Z = FRANKA_TABLE_SURFACE_Z + 0.5 * FRANKA_CUBE_SIZE + 0.005
FRANKA_CUBE_SPAWN_XY_RANDOMIZATION = 0.08


def _yaw_matrix(yaw_rad: float) -> np.ndarray:
    c = float(np.cos(yaw_rad))
    s = float(np.sin(yaw_rad))
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    return out


def _transform_from_pos_yaw(pos: np.ndarray, yaw_rad: float) -> np.ndarray:
    out = _yaw_matrix(yaw_rad)
    out[:3, 3] = np.asarray(pos, dtype=np.float64)
    return out


def _load_library(path: Path) -> dict[str, Any]:
    data = np.load(path, allow_pickle=False)
    required = ("grasps_object", "confidence", "grasp_to_tool_transform")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"{path} is missing required fields: {missing}")
    grasps_object = np.asarray(data["grasps_object"], dtype=np.float64)
    if grasps_object.ndim != 3 or grasps_object.shape[1:] != (4, 4):
        raise ValueError(f"grasps_object must have shape (N, 4, 4), got {grasps_object.shape}")
    confidence = np.asarray(data["confidence"], dtype=np.float64)
    if confidence.shape != (grasps_object.shape[0],):
        raise ValueError(f"confidence must have shape ({grasps_object.shape[0]},), got {confidence.shape}")
    metadata = {}
    if "metadata_json" in data:
        metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
    return {
        "grasps_object": grasps_object,
        "confidence": confidence,
        "grasp_to_tool_transform": np.asarray(data["grasp_to_tool_transform"], dtype=np.float64),
        "cube_size_m": float(np.asarray(data["cube_size_m"]).item()) if "cube_size_m" in data else FRANKA_CUBE_SIZE,
        "tool_frame": str(np.asarray(data["tool_frame"]).item()) if "tool_frame" in data else "panda_hand",
        "gripper_name": str(np.asarray(data["gripper_name"]).item()) if "gripper_name" in data else "franka_panda",
        "metadata": metadata,
    }


def _sample_grasp_indices(confidence: np.ndarray, *, num_episodes: int, top_k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if top_k <= 0 or top_k > confidence.shape[0]:
        top_k = confidence.shape[0]
    ranked = np.argsort(confidence)[::-1][:top_k]
    weights = np.clip(confidence[ranked], a_min=0.0, a_max=None)
    if np.sum(weights) <= 1.0e-9:
        weights = None
    else:
        weights = weights / np.sum(weights)
    return rng.choice(ranked, size=int(num_episodes), replace=True, p=weights).astype(np.int64)


def _episode_from_grasp(
    *,
    grasp_object: np.ndarray,
    grasp_to_tool: np.ndarray,
    cube_pos: np.ndarray,
    cube_yaw_rad: float,
    steps: int,
    hold_steps: int,
    approach_offset_m: float,
    pregrasp_offset_m: float,
    ee_offset_pos: tuple[float, float, float],
    max_gripper_width: float,
) -> tuple[TrajectoryArrays, dict[str, float]]:
    if steps < 2:
        raise ValueError("steps must be at least 2")
    if approach_offset_m <= pregrasp_offset_m:
        raise ValueError("approach_offset_m must be greater than pregrasp_offset_m")

    tool_to_ee = np.eye(4, dtype=np.float64)
    tool_to_ee[:3, 3] = np.asarray(ee_offset_pos, dtype=np.float64)
    object_to_ee = np.asarray(grasp_object, dtype=np.float64) @ np.asarray(grasp_to_tool, dtype=np.float64) @ tool_to_ee
    world_to_object = _transform_from_pos_yaw(cube_pos, cube_yaw_rad)
    world_to_ee_exact = world_to_object @ object_to_ee
    exact_pos = world_to_ee_exact[:3, 3]
    exact_quat = _quat_wxyz_from_matrix(world_to_ee_exact)

    direction = exact_pos - cube_pos
    norm = float(np.linalg.norm(direction))
    if norm < 1.0e-6:
        direction = -world_to_ee_exact[:3, 2]
        norm = float(np.linalg.norm(direction))
    approach_dir = direction / max(norm, 1.0e-6)

    start_pos = exact_pos + approach_dir * float(approach_offset_m)
    pregrasp_pos = exact_pos + approach_dir * float(pregrasp_offset_m)
    line_steps = int(steps)
    alphas = np.linspace(0.0, 1.0, line_steps, dtype=np.float64)
    ee_pos = (1.0 - alphas[:, None]) * start_pos[None, :] + alphas[:, None] * pregrasp_pos[None, :]
    if hold_steps > 0:
        ee_pos = np.concatenate([ee_pos, np.repeat(pregrasp_pos[None, :], int(hold_steps), axis=0)], axis=0)
    n = ee_pos.shape[0]

    ee_quat = np.repeat(exact_quat[None, :], n, axis=0)
    cube_pos_arr = np.repeat(np.asarray(cube_pos, dtype=np.float64)[None, :], n, axis=0)
    cube_quat = np.repeat(_quat_wxyz_from_matrix(world_to_object)[None, :], n, axis=0)
    phases = np.full(n, "go_to_pre_grasp_pose", dtype="<U64")
    if hold_steps > 0:
        phases[-int(hold_steps) :] = "hold_at_pre_grasp"
    gripper_width = np.full(n, float(max_gripper_width), dtype=np.float32)
    diagnostics = {
        "exact_ee_distance_m": float(np.linalg.norm(exact_pos - cube_pos)),
        "pregrasp_ee_distance_m": float(np.linalg.norm(pregrasp_pos - cube_pos)),
        "start_ee_distance_m": float(np.linalg.norm(start_pos - cube_pos)),
    }
    return (
        TrajectoryArrays(
            ee_pos=ee_pos.astype(np.float32),
            ee_quat_wxyz=ee_quat.astype(np.float32),
            cube_pos=cube_pos_arr.astype(np.float32),
            cube_quat_wxyz=cube_quat.astype(np.float32),
            phases=phases,
            gripper_width=gripper_width,
            fps=None,
            source_path=None,
        ),
        diagnostics,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grasp-library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num-episodes", type=int, default=16)
    parser.add_argument("--steps", type=int, default=24, help="Approach interpolation steps per episode")
    parser.add_argument("--hold-steps", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pickup-x", type=float, default=FRANKA_CUBE_PICKUP_X)
    parser.add_argument("--pickup-y", type=float, default=FRANKA_CUBE_PICKUP_Y)
    parser.add_argument("--cube-spawn-z", type=float, default=FRANKA_CUBE_SPAWN_Z)
    parser.add_argument("--cube-spawn-xy-randomization", type=float, default=FRANKA_CUBE_SPAWN_XY_RANDOMIZATION)
    parser.add_argument("--yaw-randomization-deg", type=float, default=0.0)
    parser.add_argument("--approach-offset-m", type=float, default=0.16)
    parser.add_argument("--pregrasp-offset-m", type=float, default=0.03)
    parser.add_argument("--cube-lift-height", type=float, default=0.16)
    parser.add_argument("--max-gripper-width", type=float, default=0.08)
    parser.add_argument(
        "--world-to-action-quat-wxyz",
        type=float,
        nargs=4,
        default=list(DextrahActionConvention().world_to_action_quat_wxyz),
        help="Rotate world-frame EE deltas into the controller action frame; Franka cube default is root yaw 180deg.",
    )
    parser.add_argument("--ee-offset-pos", type=float, nargs=3, default=list(DEFAULT_EE_OFFSET_POS))
    parser.add_argument("--no-clip-actions", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    library_path = args.grasp_library.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    library = _load_library(library_path)
    rng = np.random.default_rng(int(args.seed))
    selected_indices = _sample_grasp_indices(
        library["confidence"],
        num_episodes=int(args.num_episodes),
        top_k=int(args.top_k),
        seed=int(args.seed),
    )
    convention = DextrahActionConvention(
        world_to_action_quat_wxyz=tuple(float(v) for v in args.world_to_action_quat_wxyz),
        max_gripper_width=float(args.max_gripper_width),
        clip_actions=not bool(args.no_clip_actions),
    )

    episodes = []
    episode_meta = []
    for ep_idx, grasp_idx in enumerate(selected_indices):
        cube_xy = np.asarray([float(args.pickup_x), float(args.pickup_y)], dtype=np.float64)
        cube_xy += float(args.cube_spawn_xy_randomization) * rng.uniform(-1.0, 1.0, size=2)
        yaw = np.deg2rad(float(args.yaw_randomization_deg)) * rng.uniform(-1.0, 1.0)
        cube_pos = np.asarray([cube_xy[0], cube_xy[1], float(args.cube_spawn_z)], dtype=np.float64)
        trajectory, diagnostics = _episode_from_grasp(
            grasp_object=library["grasps_object"][int(grasp_idx)],
            grasp_to_tool=library["grasp_to_tool_transform"],
            cube_pos=cube_pos,
            cube_yaw_rad=float(yaw),
            steps=int(args.steps),
            hold_steps=int(args.hold_steps),
            approach_offset_m=float(args.approach_offset_m),
            pregrasp_offset_m=float(args.pregrasp_offset_m),
            ee_offset_pos=tuple(float(v) for v in args.ee_offset_pos),
            max_gripper_width=float(args.max_gripper_width),
        )
        episode = trajectory_to_episode(
            trajectory,
            convention=convention,
            cube_lift_height=float(args.cube_lift_height),
        )
        episodes.append(episode)
        episode_meta.append(
            {
                "episode": ep_idx,
                "grasp_index": int(grasp_idx),
                "grasp_confidence": float(library["confidence"][int(grasp_idx)]),
                "cube_pos": cube_pos.astype(float).tolist(),
                "cube_yaw_rad": float(yaw),
                **diagnostics,
                "pregrasp_farther_than_exact": bool(
                    diagnostics["pregrasp_ee_distance_m"] > diagnostics["exact_ee_distance_m"]
                ),
            }
        )

    metadata = {
        "source": "graspgenx_grasp_library_geometric_approach_to_dextrah_franka_cube_lowdim",
        "curobo_validated": False,
        "grasp_library": str(library_path),
        "gripper_name": library["gripper_name"],
        "tool_frame": library["tool_frame"],
        "cube_size_m": library["cube_size_m"],
        "library_metadata": library["metadata"],
        "selected_grasp_indices": selected_indices.astype(int).tolist(),
        "episode_metadata": episode_meta,
        "generator": {
            "seed": int(args.seed),
            "num_episodes": int(args.num_episodes),
            "steps": int(args.steps),
            "hold_steps": int(args.hold_steps),
            "top_k": int(args.top_k),
            "pickup_x": float(args.pickup_x),
            "pickup_y": float(args.pickup_y),
            "cube_spawn_z": float(args.cube_spawn_z),
            "cube_spawn_xy_randomization": float(args.cube_spawn_xy_randomization),
            "yaw_randomization_deg": float(args.yaw_randomization_deg),
            "approach_offset_m": float(args.approach_offset_m),
            "pregrasp_offset_m": float(args.pregrasp_offset_m),
            "ee_offset_pos": [float(v) for v in args.ee_offset_pos],
        },
        "action_convention": asdict(convention),
        "official_diffusion_policy_source": {
            "repo": "https://github.com/real-stanford/diffusion_policy",
            "project_page": "https://diffusion-policy.cs.columbia.edu/",
        },
        "notes": [
            "Geometric approach-to-pregrasp interpolation from GraspGenX grasps; not cuRobo-validated.",
            "Actions are DEXTRAH normalized relative EE deltas plus raw open gripper action.",
            "Use this for official-DP mechanics, validation split, and bridge smoke only until real cube cuRobo traces exist.",
        ],
    }
    summary = write_demo_dataset(episodes, output_path, metadata=metadata)
    compact = {
        "dataset_path": summary["dataset_path"],
        "num_episodes": summary["num_episodes"],
        "num_steps": summary["num_steps"],
        "obs_dim": summary["obs_dim"],
        "action_dim": summary["action_dim"],
        "curobo_validated": False,
        "all_pregrasps_farther": bool(all(item["pregrasp_farther_than_exact"] for item in episode_meta)),
    }
    print("FRANKA_CUBE_DP_BC_GRASP_LIBRARY_DEMOS " + json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    main()
