#!/usr/bin/env python3
"""Compose two single-YAM GraspGenX/cuRobo plans into a bimanual YAM demo.

This is a readiness/demo bridge for the MolmoAct2-style bimanual YAM asset.
It does not claim a native 16-DOF bimanual cuRobo model.  Instead, it plans
one collision-aware single-YAM pick-and-lift per arm in each arm's local
workspace, then pads and synchronizes the two 8-DOF plans into one 16-DOF
bimanual trajectory.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SINGLE_YAM_JOINT_NAMES = [
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
    "left_finger",
    "right_finger",
]
BIMANUAL_JOINT_NAMES = [
    "left_joint1",
    "left_joint2",
    "left_joint3",
    "left_joint4",
    "left_joint5",
    "left_joint6",
    "left_left_finger",
    "left_right_finger",
    "right_joint1",
    "right_joint2",
    "right_joint3",
    "right_joint4",
    "right_joint5",
    "right_joint6",
    "right_left_finger",
    "right_right_finger",
]
MOLMOACT2_ARM_Y_OFFSET = 0.31
MOLMOACT2_OBJECT_ANCHORS_XY = {
    "left": (-0.30, 0.22),
    "right": (-0.30, -0.22),
}
MOLMOACT2_HOME_ARM_QPOS = [0.0, 1.047, 1.047, 0.1, -0.1, 0.0]
MOLMOACT2_HOME_FINGER_QPOS = 0.0
TABLE_SURFACE_Z = 0.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_graspgenx_root() -> Path:
    env = os.environ.get("GRASPGENX_ROOT") or os.environ.get("GRASPGENX_REPO")
    if env:
        return Path(env).expanduser().resolve()
    worktree = _repo_root().parent / "graspgenx-yam-ggx-curobo"
    if worktree.is_dir():
        return worktree.resolve()
    return (_repo_root().parents[1] / "graspgenx").resolve()


def _default_curobo_root() -> Path | None:
    env = os.environ.get("GRASPGENX_CUROBO_DIR")
    if env:
        return Path(env).expanduser().resolve()
    candidate = _repo_root().parents[1] / "curobo"
    return candidate.resolve() if candidate.exists() else None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _matrix_from_pose_wxyz(pos: list[float], quat_wxyz: list[float]) -> list[list[float]]:
    w, x, y, z = [float(v) for v in quat_wxyz]
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm <= 0.0:
        w, x, y, z = 1.0, 0.0, 0.0, 0.0
    else:
        w, x, y, z = w / norm, x / norm, y / norm, z / norm
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return [
        [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy), float(pos[0])],
        [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx), float(pos[1])],
        [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy), float(pos[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _write_box_obj(path: Path, dims: tuple[float, float, float], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    hx, hy, hz = [0.5 * float(v) for v in dims]
    verts = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    faces = [
        (1, 2, 3),
        (1, 3, 4),
        (5, 8, 7),
        (5, 7, 6),
        (1, 5, 6),
        (1, 6, 2),
        (2, 6, 7),
        (2, 7, 3),
        (3, 7, 8),
        (3, 8, 4),
        (4, 8, 5),
        (4, 5, 1),
    ]
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# DEXTRAH generated {label} cuboid\n")
        for x, y, z in verts:
            f.write(f"v {x:.9f} {y:.9f} {z:.9f}\n")
        for face in faces:
            f.write("f " + " ".join(str(i) for i in face) + "\n")


def _arm_offset(arm: str) -> float:
    if arm == "left":
        return MOLMOACT2_ARM_Y_OFFSET
    if arm == "right":
        return -MOLMOACT2_ARM_Y_OFFSET
    raise ValueError(f"Unknown arm: {arm}")


def _actual_anchor(arm: str) -> tuple[float, float]:
    return MOLMOACT2_OBJECT_ANCHORS_XY[arm]


def _local_anchor_for_single_yam(arm: str) -> tuple[float, float]:
    x, y = _actual_anchor(arm)
    return float(x), float(y - _arm_offset(arm))


def _make_stable_scene(
    *,
    arm: str,
    output_dir: Path,
    object_dims: tuple[float, float, float],
) -> Path:
    local_x, local_y = _local_anchor_for_single_yam(arm)
    object_center = [local_x, local_y, TABLE_SURFACE_Z + 0.5 * float(object_dims[2])]
    quat = [1.0, 0.0, 0.0, 0.0]
    mesh_rel = Path("assets") / f"{arm}_target_box.obj"
    mesh_path = output_dir / mesh_rel
    _write_box_obj(mesh_path, object_dims, f"{arm} YAM target")
    bounds_min = [-0.5 * float(v) for v in object_dims]
    bounds_max = [0.5 * float(v) for v in object_dims]
    home_joint = [*MOLMOACT2_HOME_ARM_QPOS, MOLMOACT2_HOME_FINGER_QPOS, MOLMOACT2_HOME_FINGER_QPOS]
    payload = {
        "format": "dextrah_stable_scene_v1",
        "source": "generated_bimanual_yam_dual_pick_bridge",
        "arm": arm,
        "target": {
            "asset": {
                "asset_index": 0,
                "uuid": f"{arm}_box",
                "raw_object_path": str(mesh_path),
                "usd_spawn_scale": 1.0,
                "scaled_bounds_min": bounds_min,
                "scaled_bounds_max": bounds_max,
            },
            "mesh_copy": {
                "copy_rel": str(mesh_rel),
                "copy_path": str(mesh_path),
            },
            "root_position": object_center,
            "root_quat_wxyz": quat,
            "root_transform": _matrix_from_pose_wxyz(object_center, quat),
        },
        "clutter": [],
        "robot": {
            "joint_position": [home_joint],
            "joint_velocity": [[0.0 for _ in home_joint]],
            "arm_joint_position": [list(MOLMOACT2_HOME_ARM_QPOS)],
            "finger_joint_position": [[MOLMOACT2_HOME_FINGER_QPOS, MOLMOACT2_HOME_FINGER_QPOS]],
        },
    }
    stable_path = output_dir / f"{arm}_stable_scene.json"
    _write_json(stable_path, payload)
    return stable_path


def _run_single_arm_plan(args: argparse.Namespace, *, arm: str, output_dir: Path, stable_scene_path: Path) -> dict[str, Any]:
    arm_dir = output_dir / arm
    arm_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(args.python),
        str(args.planner_script.expanduser().resolve()),
        "--stable_scene_path",
        str(stable_scene_path),
        "--output_dir",
        str(arm_dir),
        "--run_name",
        f"{arm}_pick_lift",
        "--seed",
        str(int(args.seed) + (0 if arm == "left" else 1000)),
        "--num_grasps",
        str(int(args.num_grasps)),
        "--topk",
        str(int(args.topk)),
        "--max_plan_attempts",
        str(int(args.max_plan_attempts)),
        "--plan_task",
        "pick_and_lift",
        "--scripted_lift_mode",
        str(args.scripted_lift_mode),
        "--scripted_lift_height",
        str(float(args.scripted_lift_height)),
        "--scripted_lift_frames",
        str(int(args.scripted_lift_frames)),
        "--start_guard_frames",
        str(int(args.start_guard_frames)),
        "--no-include_goal_bin",
        "--no-include_default_clutter",
    ]
    if args.graspgenx_root is not None:
        cmd.extend(["--graspgenx_root", str(args.graspgenx_root.expanduser().resolve())])
    if args.curobo_root is not None:
        cmd.extend(["--curobo_root", str(args.curobo_root.expanduser().resolve())])
    log_path = arm_dir / "planner_stdout_stderr.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        print(json.dumps({"event": "single_arm_plan_start", "arm": arm, "cmd": cmd}), flush=True)
        result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, text=True, env=os.environ.copy(), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{arm} planner failed with return code {result.returncode}; see {log_path}")
    plan_dir = arm_dir / f"{arm}_pick_lift"
    plan_summary_path = plan_dir / "plan_summary.json"
    trajectory_path = plan_dir / "trajectory.json"
    if not trajectory_path.is_file():
        raise FileNotFoundError(f"Missing {arm} trajectory: {trajectory_path}")
    summary = _load_json(plan_summary_path) if plan_summary_path.is_file() else {}
    if summary.get("status") != "accepted":
        raise RuntimeError(f"{arm} plan was not accepted; see {plan_summary_path}")
    return {
        "arm": arm,
        "stable_scene_path": str(stable_scene_path),
        "plan_dir": str(plan_dir),
        "plan_summary_path": str(plan_summary_path),
        "trajectory_path": str(trajectory_path),
        "planner_log": str(log_path),
        "summary": summary,
        "trajectory": _load_json(trajectory_path),
    }


def _frame_at(frames: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    if not frames:
        raise ValueError("empty trajectory")
    return frames[min(idx, len(frames) - 1)]


def _joint_position(frame: dict[str, Any]) -> list[float]:
    joint = frame.get("joint_position")
    if not isinstance(joint, list) or len(joint) != len(SINGLE_YAM_JOINT_NAMES):
        raise ValueError("single-YAM frame is missing an 8-DOF joint_position")
    return [float(v) for v in joint]


def _first_attach_frame(frames: list[dict[str, Any]]) -> int:
    for idx, frame in enumerate(frames):
        phase = str(frame.get("phase", "")).lower()
        if "close" in phase or "lift" in phase:
            return idx
    return max(0, len(frames) // 2)


def _tool_minus_object_offset(record: dict[str, Any]) -> list[float]:
    summary = record.get("summary") if isinstance(record.get("summary"), dict) else {}
    scripted_lift = summary.get("scripted_lift") if isinstance(summary.get("scripted_lift"), dict) else {}
    offset = scripted_lift.get("tool_minus_object_center_world_at_grasp")
    if isinstance(offset, list) and len(offset) == 3:
        return [float(v) for v in offset]
    target = summary.get("target_center_world")
    traj = record.get("trajectory") if isinstance(record.get("trajectory"), dict) else {}
    annotations = traj.get("annotations") if isinstance(traj.get("annotations"), dict) else {}
    tool = annotations.get("target_tool_transform")
    if isinstance(target, list) and len(target) == 3 and isinstance(tool, list) and len(tool) >= 3:
        return [float(tool[i][3]) - float(target[i]) for i in range(3)]
    return [0.0, 0.0, 0.0]


def _compose(records: dict[str, dict[str, Any]], output_path: Path, object_dims: tuple[float, float, float]) -> dict[str, Any]:
    left_frames = records["left"]["trajectory"]["frames"]
    right_frames = records["right"]["trajectory"]["frames"]
    if not isinstance(left_frames, list) or not isinstance(right_frames, list) or not left_frames or not right_frames:
        raise ValueError("Both single-arm trajectories must contain frames")
    total = max(len(left_frames), len(right_frames))
    frames: list[dict[str, Any]] = []
    for idx in range(total):
        left_frame = _frame_at(left_frames, idx)
        right_frame = _frame_at(right_frames, idx)
        left_q = _joint_position(left_frame)
        right_q = _joint_position(right_frame)
        frames.append(
            {
                "frame_index": idx,
                "joint_names": list(BIMANUAL_JOINT_NAMES),
                "joint_position": [*left_q, *right_q],
                "left_joint_position": left_q,
                "right_joint_position": right_q,
                "left_source_frame": min(idx, len(left_frames) - 1),
                "right_source_frame": min(idx, len(right_frames) - 1),
                "left_phase": str(left_frame.get("phase", "")),
                "right_phase": str(right_frame.get("phase", "")),
            }
        )
    object_records: dict[str, Any] = {}
    for arm in ("left", "right"):
        local_x, local_y = _local_anchor_for_single_yam(arm)
        actual_x, actual_y = _actual_anchor(arm)
        object_records[arm] = {
            "object_id": f"{arm}_object",
            "arm": arm,
            "arm_y_offset": _arm_offset(arm),
            "single_yam_center_world": [local_x, local_y, TABLE_SURFACE_Z + 0.5 * float(object_dims[2])],
            "bimanual_center_world": [actual_x, actual_y, TABLE_SURFACE_Z + 0.5 * float(object_dims[2])],
            "dims": list(object_dims),
            "attach_frame": _first_attach_frame(records[arm]["trajectory"]["frames"]),
            "tool_minus_object_center_world_at_grasp": _tool_minus_object_offset(records[arm]),
            "source_trajectory": records[arm]["trajectory_path"],
            "plan_summary": records[arm]["plan_summary_path"],
        }
    fps = int(records["left"]["trajectory"].get("fps", 60))
    payload = {
        "format": "dextrah_bimanual_yam_dual_pick_v1",
        "source": "two_single_yam_graspgenx_curobo_plans",
        "composition_mode": "time_padded_simultaneous_left_right_replay",
        "fps": fps,
        "joint_names": list(BIMANUAL_JOINT_NAMES),
        "single_yam_joint_names": list(SINGLE_YAM_JOINT_NAMES),
        "total_frames": total,
        "object_records": object_records,
        "frames": frames,
        "arm_plan_records": {
            arm: {
                key: value
                for key, value in records[arm].items()
                if key not in {"trajectory", "summary"}
            }
            for arm in ("left", "right")
        },
        "readiness": {
            "native_bimanual_curobo_model": False,
            "single_yam_graspgenx_curobo_ready": True,
            "bimanual_demo_method": "compose two independent single-arm YAM cuRobo plans and replay them on the bimanual Isaac asset",
        },
    }
    _write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=_repo_root() / "local_results/bimanual_yam_dual_pick")
    parser.add_argument("--run_name", type=str, default="dual_pick_plan")
    parser.add_argument("--planner_script", type=Path, default=Path(__file__).with_name("plan_yam_graspgenx_curobo.py"))
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--graspgenx_root", type=Path, default=_default_graspgenx_root())
    parser.add_argument("--curobo_root", type=Path, default=_default_curobo_root())
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--object_dims", type=float, nargs=3, default=(0.08, 0.08, 0.08))
    parser.add_argument("--num_grasps", type=int, default=96)
    parser.add_argument("--topk", type=int, default=48)
    parser.add_argument("--max_plan_attempts", type=int, default=48)
    parser.add_argument("--scripted_lift_mode", choices=("fallback", "always", "never"), default="always")
    parser.add_argument("--scripted_lift_height", type=float, default=0.12)
    parser.add_argument("--scripted_lift_frames", type=int, default=180)
    parser.add_argument("--start_guard_frames", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = (args.output_dir.expanduser().resolve() / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    object_dims = tuple(float(v) for v in args.object_dims)
    records: dict[str, dict[str, Any]] = {}
    for arm in ("left", "right"):
        stable_scene_path = _make_stable_scene(arm=arm, output_dir=output_dir / "stable_scenes", object_dims=object_dims)
        records[arm] = _run_single_arm_plan(args, arm=arm, output_dir=output_dir / "single_arm_plans", stable_scene_path=stable_scene_path)
        print(
            json.dumps(
                {
                    "event": "single_arm_plan_done",
                    "arm": arm,
                    "trajectory_path": records[arm]["trajectory_path"],
                    "plan_summary_path": records[arm]["plan_summary_path"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
    combined_path = output_dir / "bimanual_trajectory.json"
    combined = _compose(records, combined_path, object_dims)
    metadata = {
        "status": "accepted",
        "output_dir": str(output_dir),
        "bimanual_trajectory": str(combined_path),
        "total_frames": combined["total_frames"],
        "fps": combined["fps"],
        "object_records": combined["object_records"],
        "readiness": combined["readiness"],
    }
    _write_json(output_dir / "metadata.json", metadata)
    print("DEXTRAH_BIMANUAL_YAM_DUAL_PICK_PLAN " + json.dumps(metadata, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
