#!/usr/bin/env python3
"""Convert a GraspGenX Franka trajectory JSON into a compact DEXTRAH reference.

The GraspGenX trajectory input may contain joint positions. The output never
stores joint arrays: it stores object-local DEXTRAH EE poses, phase labels, and
an optional gripper-width schedule for runtime task-space tracking.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


if str(_repo_root()) not in sys.path:
    sys.path.insert(0, str(_repo_root()))

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_traj_tracking_reference import (  # noqa: E402
    SCHEMA_NAME,
    SCHEMA_VERSION,
    validate_reference_payload,
    write_reference_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", type=Path, required=True, help="GraspGenX trajectory.json input.")
    parser.add_argument("--output", type=Path, required=True, help="Compact DEXTRAH reference JSON output.")
    parser.add_argument("--summary", type=Path, default=None, help="Optional converter/validation summary JSON.")
    parser.add_argument(
        "--graspgenx-root",
        type=Path,
        default=Path("/home/lzha/code/graspgenx"),
        help="GraspGenX checkout containing end2end/trajectory_visualizer.py.",
    )
    parser.add_argument(
        "--robot-config",
        type=Path,
        default=None,
        help="GraspGenX Franka robot YAML. Defaults to <graspgenx-root>/end2end/robots/franka_panda.yaml.",
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=None,
        help="Optional GraspGenX validation.json used to prove cuRobo validation.",
    )
    parser.add_argument(
        "--mark-curobo-validated",
        action="store_true",
        help="Set source.curobo_validated=true only if --validation-json passed.",
    )
    parser.add_argument(
        "--object-key",
        type=str,
        default="",
        help="Static object key in trajectory JSON. Auto-detects object/cube/box when omitted.",
    )
    parser.add_argument("--tool-frame", type=str, default="panda_hand")
    parser.add_argument(
        "--dextrah-ee-offset",
        type=float,
        nargs=3,
        default=(0.0, 0.0, 0.1034),
        help="Local offset from GraspGenX tool frame to the DEXTRAH EE frame.",
    )
    parser.add_argument("--cube-size", type=float, default=0.06)
    parser.add_argument("--table-surface-z", type=float, default=0.746)
    parser.add_argument("--cube-spawn-z", type=float, default=None)
    parser.add_argument("--max-gripper-width", type=float, default=0.08)
    parser.add_argument("--max-waypoints", type=int, default=9)
    parser.add_argument("--fps", type=float, default=None, help="Override trajectory fps for time_s fields.")
    parser.add_argument("--source-tag", type=str, default="graspgenx_curobo_trajectory_export")
    return parser.parse_args()


def _load_graspgenx_helpers(graspgenx_root: Path):
    end2end_dir = graspgenx_root.expanduser().resolve() / "end2end"
    if not end2end_dir.is_dir():
        raise FileNotFoundError(f"Missing GraspGenX end2end directory: {end2end_dir}")
    if str(end2end_dir) not in sys.path:
        sys.path.insert(0, str(end2end_dir))
    from robot_profiles import RobotProfile  # type: ignore
    from scene_builder import load_yaml  # type: ignore
    from trajectory_visualizer import URDFFK  # type: ignore

    return RobotProfile, URDFFK, load_yaml


def _matrix4(value: Any, *, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (4, 4):
        raise ValueError(f"{name} must be a 4x4 matrix")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _quat_wxyz_from_matrix(matrix: np.ndarray) -> list[float]:
    rot = np.asarray(matrix[:3, :3], dtype=np.float64)
    trace = float(np.trace(rot))
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (rot[2, 1] - rot[1, 2]) / s
        qy = (rot[0, 2] - rot[2, 0]) / s
        qz = (rot[1, 0] - rot[0, 1]) / s
    else:
        diag = np.diag(rot)
        if diag[0] > diag[1] and diag[0] > diag[2]:
            s = math.sqrt(max(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2], 1.0e-12)) * 2.0
            qw = (rot[2, 1] - rot[1, 2]) / s
            qx = 0.25 * s
            qy = (rot[0, 1] + rot[1, 0]) / s
            qz = (rot[0, 2] + rot[2, 0]) / s
        elif diag[1] > diag[2]:
            s = math.sqrt(max(1.0 + rot[1, 1] - rot[0, 0] - rot[2, 2], 1.0e-12)) * 2.0
            qw = (rot[0, 2] - rot[2, 0]) / s
            qx = (rot[0, 1] + rot[1, 0]) / s
            qy = 0.25 * s
            qz = (rot[1, 2] + rot[2, 1]) / s
        else:
            s = math.sqrt(max(1.0 + rot[2, 2] - rot[0, 0] - rot[1, 1], 1.0e-12)) * 2.0
            qw = (rot[1, 0] - rot[0, 1]) / s
            qx = (rot[0, 2] + rot[2, 0]) / s
            qy = (rot[1, 2] + rot[2, 1]) / s
            qz = 0.25 * s
    quat = np.asarray([qw, qx, qy, qz], dtype=np.float64)
    quat /= max(float(np.linalg.norm(quat)), 1.0e-12)
    return [float(item) for item in quat]


def _select_object_transform(trajectory: dict[str, Any], object_key: str) -> tuple[str, np.ndarray]:
    static = trajectory.get("static")
    if not isinstance(static, dict):
        raise ValueError("trajectory JSON is missing a static object map")

    def transform_for(key: str) -> np.ndarray | None:
        item = static.get(key)
        if isinstance(item, dict) and "transform" in item:
            return _matrix4(item["transform"], name=f"static[{key!r}].transform")
        return None

    if object_key:
        transform = transform_for(object_key)
        if transform is None:
            raise KeyError(f"Object key {object_key!r} has no transform in trajectory static map")
        return object_key, transform

    preferred = ("object", "object_0", "cube", "box", "target", "manipulation_object")
    for key in preferred:
        transform = transform_for(key)
        if transform is not None:
            return key, transform

    for key in sorted(static):
        lower = key.lower()
        if any(skip in lower for skip in ("table", "ground", "robot", "bin", "fixture")):
            continue
        transform = transform_for(key)
        if transform is not None:
            return key, transform
    raise ValueError(f"Could not auto-detect object transform from static keys: {sorted(static)}")


def _selected_indices(num_frames: int, max_waypoints: int) -> list[int]:
    if num_frames < 2:
        raise ValueError("Need at least two trajectory frames")
    max_waypoints = max(2, int(max_waypoints))
    if num_frames <= max_waypoints:
        return list(range(num_frames))
    raw = [round(i * (num_frames - 1) / (max_waypoints - 1)) for i in range(max_waypoints)]
    return sorted(set(int(idx) for idx in raw))


def _phase_and_weight(progress: float) -> tuple[str, float]:
    if progress < 0.35:
        return "approach", 0.45
    if progress < 0.55:
        return "pregrasp", 0.75
    if progress < 0.68:
        return "grasp", 1.0
    if progress < 0.80:
        return "close", 1.0
    return "lift", 0.70


def _validated_source(validation_json: Path | None, *, cube_size_m: float, require_validated: bool) -> tuple[bool, dict[str, Any]]:
    if validation_json is None:
        if require_validated:
            raise ValueError("--mark-curobo-validated requires --validation-json")
        return False, {}

    payload = json.loads(validation_json.expanduser().read_text(encoding="utf-8"))
    status_passed = payload.get("status") == "passed"
    segments = payload.get("plan_segments") if isinstance(payload.get("plan_segments"), dict) else {}
    segment_lengths = {name: int(segments.get(name, 0) or 0) for name in ("approach", "grasp", "lift")}
    segments_passed = all(value > 0 for value in segment_lengths.values())
    extents = np.asarray(payload.get("object_extents_m", []), dtype=np.float64)
    extents_match = bool(extents.shape == (3,) and np.allclose(extents, cube_size_m, atol=2.0e-3, rtol=0.05))
    passed = bool(status_passed and segments_passed and extents_match)
    details = {
        "validation_json": str(validation_json.expanduser().resolve()),
        "status": payload.get("status"),
        "plan_segments": segment_lengths,
        "object_extents_m": extents.tolist() if extents.shape == (3,) else payload.get("object_extents_m"),
        "object_extents_match_cube_size": extents_match,
        "selected_grasp_index": payload.get("selected_grasp_index"),
        "selected_grasp_confidence": payload.get("selected_grasp_confidence"),
    }
    if require_validated and not passed:
        raise ValueError(f"Validation JSON is not sufficient to mark cuRobo validated: {details}")
    return passed if require_validated else False, details


def _build_joint_cfg(profile, actuated_names: list[str], joint_position: Any) -> dict[str, float]:
    values = np.asarray(joint_position, dtype=np.float64).reshape(-1)
    if values.size < profile.n_arm:
        raise ValueError(f"joint_position has {values.size} columns, expected at least {profile.n_arm}")
    cfg = {name: 0.0 for name in actuated_names}
    for col, name in enumerate(profile.arm_joint_names):
        cfg[name] = float(values[col])
    for gripper_col, name in enumerate(profile.gripper_joint_names):
        col = profile.n_arm + gripper_col
        cfg[name] = float(values[col]) if col < values.size else float(profile.open_value(name))
    return cfg


def main() -> None:
    args = parse_args()
    global np
    import numpy as np

    graspgenx_root = args.graspgenx_root.expanduser().resolve()
    robot_config = args.robot_config or (graspgenx_root / "end2end/robots/franka_panda.yaml")
    RobotProfile, URDFFK, load_yaml = _load_graspgenx_helpers(graspgenx_root)

    trajectory_path = args.trajectory.expanduser().resolve()
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    frames = trajectory.get("frames")
    if not isinstance(frames, list) or len(frames) < 2:
        raise ValueError(f"{trajectory_path} has no usable frames")

    robot_cfg = load_yaml(robot_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    fk = URDFFK(profile.urdf_path, asset_root=profile.asset_root_path)
    if args.tool_frame not in fk.link_names():
        raise ValueError(f"Tool frame {args.tool_frame!r} is not in URDF links")
    actuated_names = fk.actuated_joint_names()

    object_key, world_object = _select_object_transform(trajectory, args.object_key)
    object_world_inv = np.linalg.inv(world_object)
    tool_to_dextrah_ee = np.eye(4, dtype=np.float64)
    tool_to_dextrah_ee[:3, 3] = np.asarray(args.dextrah_ee_offset, dtype=np.float64)

    fps = float(args.fps if args.fps is not None else trajectory.get("fps", 30.0))
    if not math.isfinite(fps) or fps <= 0.0:
        raise ValueError(f"Invalid fps: {fps}")

    cube_spawn_z = (
        float(args.cube_spawn_z)
        if args.cube_spawn_z is not None
        else float(args.table_surface_z + 0.5 * args.cube_size + 0.005)
    )
    curobo_validated, validation_details = _validated_source(
        args.validation_json,
        cube_size_m=float(args.cube_size),
        require_validated=bool(args.mark_curobo_validated),
    )

    waypoints: list[dict[str, Any]] = []
    for frame_idx in _selected_indices(len(frames), args.max_waypoints):
        frame = frames[frame_idx]
        if not isinstance(frame, dict) or "joint_position" not in frame:
            raise ValueError(f"Frame {frame_idx} is missing joint_position")
        cfg = _build_joint_cfg(profile, actuated_names, frame["joint_position"])
        world_tool = fk.fk(cfg, base_T=profile.robot_base_T, link_names=[args.tool_frame])[args.tool_frame]
        world_ee = world_tool @ tool_to_dextrah_ee
        object_ee = object_world_inv @ world_ee
        progress = float(frame_idx) / float(max(len(frames) - 1, 1))
        phase, tracking_weight = _phase_and_weight(progress)
        gripper_value = float(cfg.get(profile.gripper_joint_names[0], profile.open_value(profile.gripper_joint_names[0])))
        gripper_width = max(0.0, min(float(args.max_gripper_width), 2.0 * gripper_value))
        waypoints.append(
            {
                "phase": phase,
                "time_s": float(frame_idx / fps),
                "ee_pos_object": [float(v) for v in object_ee[:3, 3]],
                "ee_quat_object_wxyz": _quat_wxyz_from_matrix(object_ee),
                "gripper_width": gripper_width,
                "tracking_weight": tracking_weight,
            }
        )

    source_notes = (
        "Converted from GraspGenX trajectory JSON. Output stores task-space waypoints only; "
        "joint positions remain offline validation input and are not stored in this reference."
    )
    if not curobo_validated:
        source_notes += " This reference is not marked cuRobo validated."

    payload = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "description": "Compact object-local task-space reference converted from a GraspGenX Franka trajectory.",
        "cube_size_m": float(args.cube_size),
        "table_surface_z_m": float(args.table_surface_z),
        "cube_spawn_z_m": cube_spawn_z,
        "reference_frame": "cube_object_frame",
        "target_frame": "dextrah_ee_frame",
        "tool_frame": f"{args.tool_frame}_plus_dextrah_ee_offset",
        "source": {
            "tag": str(args.source_tag),
            "planner": "graspgenx_curobo_trajectory_json",
            "graspgenx_source": True,
            "curobo_validated": bool(curobo_validated),
            "trajectory_json": str(trajectory_path),
            "object_key": object_key,
            "validation": validation_details,
            "notes": source_notes,
        },
        "tracking": {
            "mode": "reward_only",
            "phase_reference_observations": False,
            "transform_policy": "transform_task_space_waypoints_by_cube_pose",
            "joint_trajectory_policy": "do_not_transform_joint_trajectories",
        },
        "validation": {
            "min_ee_table_clearance_m": 0.025,
            "min_cube_aabb_clearance_m": 0.0,
            "requires_curobo_collision_validation_before_training": not bool(curobo_validated),
        },
        "waypoints": waypoints,
    }

    records = validate_reference_payload(payload)
    passed = all(bool(record["passed"]) for record in records)
    write_reference_payload(args.output, payload)
    summary = {
        "passed": passed,
        "trajectory": str(trajectory_path),
        "output": str(args.output.expanduser().resolve()),
        "waypoint_count": len(waypoints),
        "object_key": object_key,
        "curobo_validated": bool(curobo_validated),
        "records": records,
    }
    if args.summary is not None:
        summary_path = args.summary.expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
