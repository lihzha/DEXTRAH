#!/usr/bin/env python3
"""Run a closed-loop YAM two-bin pick-and-place demo until the source bin is clear."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")


def _minimum_jerk_ramp(start: np.ndarray, end: np.ndarray, n_frames: int) -> np.ndarray:
    n_frames = max(int(n_frames), 2)
    alpha = np.linspace(0.0, 1.0, n_frames, dtype=np.float32).reshape(-1, 1)
    blend = alpha**3 * (10.0 - 15.0 * alpha + 6.0 * alpha**2)
    return (start.reshape(1, -1) + blend * (end.reshape(1, -1) - start.reshape(1, -1))).astype(np.float32)


def _matrix_from_pose_wxyz(pos: list[float], quat_wxyz: list[float]) -> list[list[float]]:
    import math

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


def _normalize_pose(pos: Any, quat: Any) -> tuple[list[float], list[float], list[list[float]]]:
    pos_out = [float(v) for v in pos]
    quat_out = [float(v) for v in quat]
    return pos_out, quat_out, _matrix_from_pose_wxyz(pos_out, quat_out)


def _target_to_object(target: dict[str, Any]) -> dict[str, Any]:
    pos, quat, transform = _normalize_pose(target["root_position"], target["root_quat_wxyz"])
    obj = {
        "object_id": "target",
        "asset": copy.deepcopy(target.get("asset") if isinstance(target.get("asset"), dict) else {}),
        "root_position": pos,
        "root_quat_wxyz": quat,
        "root_transform": copy.deepcopy(target.get("root_transform") or transform),
        "initial_object_id": "target",
    }
    mesh_copy = target.get("mesh_copy") if isinstance(target.get("mesh_copy"), dict) else {}
    if mesh_copy:
        obj["mesh_copy"] = copy.deepcopy(mesh_copy)
    return obj


def _clutter_to_object(entry: dict[str, Any]) -> dict[str, Any]:
    slot_idx = int(entry.get("slot_idx", 0))
    object_id = str(entry.get("source_object_id") or entry.get("object_id") or f"clutter_{slot_idx:02d}")
    pos, quat, transform = _normalize_pose(entry["root_position"], entry["root_quat_wxyz"])
    return {
        "object_id": object_id,
        "asset": copy.deepcopy(entry.get("asset") if isinstance(entry.get("asset"), dict) else {}),
        "root_position": pos,
        "root_quat_wxyz": quat,
        "root_transform": copy.deepcopy(entry.get("root_transform") or transform),
        "initial_object_id": object_id,
    }


def _objects_from_scene(stable_scene: dict[str, Any]) -> list[dict[str, Any]]:
    target = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else None
    if target is None:
        raise ValueError("stable scene is missing target")
    objects = [_target_to_object(target)]
    for entry in stable_scene.get("clutter") or []:
        if isinstance(entry, dict):
            objects.append(_clutter_to_object(entry))
    return objects


def _object_as_target(obj: dict[str, Any]) -> dict[str, Any]:
    target = {
        "asset": copy.deepcopy(obj["asset"]),
        "root_position": copy.deepcopy(obj["root_position"]),
        "root_quat_wxyz": copy.deepcopy(obj["root_quat_wxyz"]),
        "root_transform": copy.deepcopy(obj["root_transform"]),
    }
    if obj.get("mesh_copy"):
        target["mesh_copy"] = copy.deepcopy(obj["mesh_copy"])
    return target


def _object_as_clutter(obj: dict[str, Any], slot_idx: int) -> dict[str, Any]:
    return {
        "slot_idx": int(slot_idx),
        "source_object_id": str(obj["object_id"]),
        "asset": copy.deepcopy(obj["asset"]),
        "root_position": copy.deepcopy(obj["root_position"]),
        "root_quat_wxyz": copy.deepcopy(obj["root_quat_wxyz"]),
        "root_transform": copy.deepcopy(obj["root_transform"]),
    }


def _set_robot_start(scene: dict[str, Any], joint_position: list[float]) -> None:
    joint = [float(v) for v in joint_position]
    robot = scene.setdefault("robot", {})
    robot["joint_position"] = [joint]
    robot["joint_velocity"] = [[0.0 for _ in joint]]
    robot["arm_joint_position"] = [joint[:6]]
    robot["finger_joint_position"] = [joint[6:]]


def _robot_joint_from_scene(scene: dict[str, Any]) -> list[float] | None:
    robot = scene.get("robot") if isinstance(scene.get("robot"), dict) else {}
    joint_position = robot.get("joint_position") if isinstance(robot.get("joint_position"), list) else []
    if not joint_position:
        return None
    first = joint_position[0]
    if not isinstance(first, list):
        return None
    return [float(v) for v in first]


def _home_joint_from_scene(stable_scene: dict[str, Any]) -> list[float]:
    joint = _robot_joint_from_scene(stable_scene)
    if joint is not None:
        return joint
    arm = [0.0, 0.7853981852531433, 1.5707963705062866, 0.0, 0.0, 0.0]
    fingers = [-0.019999999552965164, -0.019999999552965164]
    return [*arm, *fingers]


def _append_return_home_to_trajectory(
    trajectory_path: Path,
    *,
    home_joint: list[float],
    return_frames: int,
    hold_frames: int,
    output_path: Path,
) -> tuple[Path, dict[str, Any]]:
    payload = _load_json(trajectory_path)
    frames = payload.get("frames") if isinstance(payload.get("frames"), list) else []
    if not frames:
        raise ValueError(f"Trajectory has no frames: {trajectory_path}")
    last_joint = np.asarray(frames[-1].get("joint_position"), dtype=np.float32)
    home = np.asarray(home_joint, dtype=np.float32)
    if last_joint.ndim != 1 or home.ndim != 1 or last_joint.shape != home.shape:
        raise ValueError(
            f"Cannot append return-home segment: last joint shape {last_joint.shape}, home shape {home.shape}"
        )
    return_count = max(int(return_frames), 0)
    hold_count = max(int(hold_frames), 0)
    appended = 0
    start_idx = len(frames)
    new_segments: list[dict[str, Any]] = []
    if return_count > 0:
        ramp = _minimum_jerk_ramp(last_joint, home, return_count)
        for joint in ramp:
            frames.append({"phase": "return_home_scripted", "joint_position": joint.tolist()})
        new_segments.append({"phase": "return_home_scripted", "start": int(start_idx), "count": int(return_count)})
        appended += return_count
    if hold_count > 0:
        hold_start = len(frames)
        for _ in range(hold_count):
            frames.append({"phase": "hold_home_after_return", "joint_position": home.tolist()})
        new_segments.append({"phase": "hold_home_after_return", "start": int(hold_start), "count": int(hold_count)})
        appended += hold_count
    segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
    payload["segments"] = [*segments, *new_segments]
    payload["frames"] = frames
    payload["total_frames"] = len(frames)
    payload["continuous_return_home"] = {
        "enabled": appended > 0,
        "source_trajectory_path": str(trajectory_path),
        "output_trajectory_path": str(output_path),
        "return_frames": int(return_count),
        "hold_frames": int(hold_count),
        "appended_frames": int(appended),
        "home_joint": home.tolist(),
        "start_joint": last_joint.tolist(),
        "max_abs_start_to_home": float(np.max(np.abs(last_joint - home))) if last_joint.size else 0.0,
    }
    _write_json(output_path, payload)
    return output_path, payload["continuous_return_home"]


def _scene_for_object(
    base_scene: dict[str, Any],
    objects: list[dict[str, Any]],
    selected_id: str,
    *,
    current_joint: list[float] | None,
    iteration: int,
) -> dict[str, Any]:
    selected = next(obj for obj in objects if str(obj["object_id"]) == str(selected_id))
    obstacles = [obj for obj in objects if str(obj["object_id"]) != str(selected_id)]
    scene = copy.deepcopy(base_scene)
    scene["target"] = _object_as_target(selected)
    scene["clutter"] = [_object_as_clutter(obj, slot_idx) for slot_idx, obj in enumerate(obstacles)]
    snapshots = scene.setdefault("snapshots", {})
    stable = {
        "target_root_pos": [copy.deepcopy(selected["root_position"])],
        "target_root_quat": [copy.deepcopy(selected["root_quat_wxyz"])],
        "clutter_root_pos_by_slot": [[copy.deepcopy(obj["root_position"])] for obj in obstacles],
        "clutter_root_quat_by_slot": [[copy.deepcopy(obj["root_quat_wxyz"])] for obj in obstacles],
    }
    snapshots["initial"] = copy.deepcopy(stable)
    snapshots["stable"] = stable
    if current_joint is not None:
        _set_robot_start(scene, current_joint)
    scene["planner_selected_object"] = {
        "object_id": str(selected["object_id"]),
        "iteration": int(iteration),
        "obstacle_object_ids": [str(obj["object_id"]) for obj in obstacles],
    }
    return scene


def _bin_info(stable_scene: dict[str, Any], key: str) -> dict[str, float]:
    bins = stable_scene.get("bins") if isinstance(stable_scene.get("bins"), dict) else {}
    info = bins.get(key) if isinstance(bins.get(key), dict) else {}
    if not info:
        raise ValueError(f"stable scene is missing bins.{key}")
    return {
        "center_x": float(info["center_x"]),
        "center_y": float(info["center_y"]),
        "inner_size_x": float(info["inner_size_x"]),
        "inner_size_y": float(info["inner_size_y"]),
    }


def _inside_bin_center(pos: list[float], bin_info: dict[str, float], *, margin: float) -> bool:
    return (
        abs(float(pos[0]) - float(bin_info["center_x"])) <= 0.5 * float(bin_info["inner_size_x"]) + float(margin)
        and abs(float(pos[1]) - float(bin_info["center_y"])) <= 0.5 * float(bin_info["inner_size_y"]) + float(margin)
    )


def _shape_priority(obj: dict[str, Any]) -> int:
    asset = obj.get("asset") if isinstance(obj.get("asset"), dict) else {}
    shape = str(asset.get("primitive_shape") or asset.get("uuid") or "").lower()
    return 1 if "sphere" in shape else 0


def _source_edge_clearance(pos: list[float], source_bin: dict[str, float]) -> float:
    dx = abs(float(pos[0]) - float(source_bin["center_x"]))
    dy = abs(float(pos[1]) - float(source_bin["center_y"]))
    return min(0.5 * float(source_bin["inner_size_x"]) - dx, 0.5 * float(source_bin["inner_size_y"]) - dy)


def _layer_priority(pos: list[float]) -> int:
    return 0 if float(pos[2]) >= 0.065 else 1


def _select_next_source_object(
    objects: list[dict[str, Any]],
    source_bin: dict[str, float],
    margin: float,
    *,
    exclude_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    excluded = exclude_ids or set()
    candidates = [
        obj
        for obj in objects
        if str(obj["object_id"]) not in excluded
        and _inside_bin_center(obj["root_position"], source_bin, margin=margin)
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda obj: (
            _layer_priority(obj["root_position"]),
            -float(obj["root_position"][2]),
            _shape_priority(obj),
            -_source_edge_clearance(obj["root_position"], source_bin),
            -float(obj["root_position"][1] - float(source_bin["center_y"])),
            str(obj["object_id"]),
        ),
    )[0]


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _unique_floats(values: list[float], *, ndigits: int = 6) -> list[float]:
    out: list[float] = []
    seen: set[float] = set()
    for value in values:
        rounded = round(float(value), ndigits)
        if rounded in seen:
            continue
        seen.add(rounded)
        out.append(float(value))
    return out


def _planning_finger_options(args: argparse.Namespace, base_finger_joint: float) -> list[float | None]:
    explicit = _parse_float_list(str(args.planner_finger_joint_positions))
    if explicit:
        return [float(v) for v in _unique_floats(explicit)]
    offsets = _parse_float_list(str(args.planner_finger_preclose_offsets))
    if not offsets:
        return [None]
    base = float(base_finger_joint)
    return [float(v) for v in _unique_floats([min(0.0, base + float(offset)) for offset in offsets])]


def _append_pythonpath(env: dict[str, str], paths: list[Path | None]) -> None:
    existing = env.get("PYTHONPATH", "")
    values = [str(path) for path in paths if path is not None]
    if existing:
        values.append(existing)
    env["PYTHONPATH"] = ":".join(values)


def _run_logged(cmd: list[str], log_path: Path, *, env: dict[str, str], cwd: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(json.dumps({"event": "command_start", "cmd": cmd}) + "\n")
        log_file.flush()
        result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(cwd), check=False)
        log_file.write(json.dumps({"event": "command_done", "returncode": int(result.returncode)}) + "\n")
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with code {result.returncode}; see {log_path}")


def _planner_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    if args.graspgenx_root is not None:
        env.setdefault("GRASPGENX_ROOT", str(args.graspgenx_root.expanduser().resolve()))
        checkpoint_dir = args.graspgenx_root.expanduser().resolve() / "ext/graspgenx_checkpoints"
        gripper_dir = args.graspgenx_root.expanduser().resolve() / "ext/gripper_descriptions"
        if checkpoint_dir.is_dir():
            env.setdefault("GRASPGENX_CHECKPOINT_DIR", str(checkpoint_dir))
        if gripper_dir.is_dir():
            env.setdefault("GRASPGENX_GRIPPER_CFG_DIR", str(gripper_dir))
    if args.curobo_root is not None:
        env.setdefault("GRASPGENX_CUROBO_DIR", str(args.curobo_root.expanduser().resolve()))
    _append_pythonpath(
        env,
        [
            _repo_root(),
            args.graspgenx_root.expanduser().resolve() if args.graspgenx_root is not None else None,
            args.graspgenx_root.expanduser().resolve() / "end2end" if args.graspgenx_root is not None else None,
            args.curobo_root.expanduser().resolve() if args.curobo_root is not None else None,
        ],
    )
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("WANDB_MODE", "offline")
    return env


def _isaac_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    _append_pythonpath(env, [_repo_root(), args.fabrics_root.expanduser().resolve() if args.fabrics_root else None])
    env.update(
        {
            "OMNI_KIT_ACCEPT_EULA": "YES",
            "ISAACSIM_ACCEPT_EULA": "YES",
            "ACCEPT_EULA": "Y",
            "PRIVACY_CONSENT": "Y",
            "WANDB_MODE": "offline",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CUDA_VISIBLE_DEVICES": str(args.cuda_visible_devices),
            "NVIDIA_VISIBLE_DEVICES": str(args.cuda_visible_devices),
        }
    )
    return env


def _plan_iteration(
    args: argparse.Namespace,
    scene_path: Path,
    iteration_dir: Path,
    iteration: int,
    *,
    drop_y_offset: float,
    attempt_number: int,
    planning_finger_joint_position: float | None,
    excluded_grasp_original_indices: set[int],
) -> dict[str, Any]:
    plan_output_dir = iteration_dir / "plan"
    run_name = "pick_drop"
    cmd = [
        str(args.planner_python.expanduser()),
        str(args.planner_script.expanduser().resolve()),
        "--stable_scene_path",
        str(scene_path),
        "--output_dir",
        str(plan_output_dir),
        "--run_name",
        run_name,
        "--seed",
        str(int(args.seed) + int(iteration)),
        "--num_grasps",
        str(int(args.num_grasps)),
        "--topk",
        str(int(args.topk)),
        "--max_plan_attempts",
        str(int(args.max_plan_attempts)),
        "--plan_task",
        "pick_and_drop_in_bin",
        "--scripted_place_fallback",
        "--move_to_bin_frames",
        str(int(args.move_to_bin_frames)),
        "--drop_height_above_bin",
        str(float(args.drop_height_above_bin)),
        "--scripted_bin_drop_y_offset",
        str(float(drop_y_offset)),
        "--scripted_place_mode",
        str(args.scripted_place_mode),
        "--scripted_lift_mode",
        str(args.scripted_lift_mode),
        "--scripted_lift_height",
        str(float(args.scripted_lift_height)),
        "--scripted_lift_frames",
        str(int(args.scripted_lift_frames)),
        "--start_guard_frames",
        str(int(args.start_guard_frames)),
        "--clutter_margin",
        str(float(args.planner_clutter_margin)),
        "--yam_grasp_filter_min_keep",
        str(int(args.yam_grasp_filter_min_keep)),
        "--yam_grasp_to_tool_z",
        str(float(args.planner_yam_grasp_to_tool_z)),
    ]
    if planning_finger_joint_position is not None:
        cmd.extend(["--planning_finger_joint_position", str(float(planning_finger_joint_position))])
    if excluded_grasp_original_indices:
        cmd.extend(
            [
                "--exclude_grasp_original_indices",
                ",".join(str(int(v)) for v in sorted(excluded_grasp_original_indices)),
            ]
        )
    if bool(args.yam_allow_lift_filter_fallback):
        cmd.append("--yam_allow_lift_filter_fallback")
    if args.graspgenx_root is not None:
        cmd.extend(["--graspgenx_root", str(args.graspgenx_root.expanduser().resolve())])
    if args.curobo_root is not None:
        cmd.extend(["--curobo_root", str(args.curobo_root.expanduser().resolve())])
    _run_logged(cmd, iteration_dir / "planner.log", env=_planner_env(args), cwd=_repo_root())
    run_dir = plan_output_dir / run_name
    trajectory_path = run_dir / "trajectory.json"
    plan_summary_path = run_dir / "plan_summary.json"
    if not trajectory_path.is_file():
        raise FileNotFoundError(trajectory_path)
    plan_summary = _load_json(plan_summary_path) if plan_summary_path.is_file() else {}
    if plan_summary.get("status") not in (None, "accepted"):
        raise RuntimeError(f"Planner status was not accepted for {scene_path}: {plan_summary.get('status')}")
    return {
        "plan_output_dir": str(plan_output_dir),
        "run_dir": str(run_dir),
        "trajectory_path": str(trajectory_path),
        "plan_summary_path": str(plan_summary_path),
        "selected_grasp_confidence": plan_summary.get("selected_grasp_confidence"),
        "selected_grasp_index": plan_summary.get("selected_grasp_index"),
        "selected_grasp_original_index": plan_summary.get("selected_grasp_original_index"),
        "planning_preclose": plan_summary.get("planning_preclose"),
        "excluded_grasp_original_indices": sorted(int(v) for v in excluded_grasp_original_indices),
        "attempt_number": int(attempt_number),
        "planning_finger_joint_position": None
        if planning_finger_joint_position is None
        else float(planning_finger_joint_position),
        "scripted_bin_drop_y_offset": float(drop_y_offset),
    }


def _render_iteration(
    args: argparse.Namespace,
    *,
    scene_path: Path,
    trajectory_path: Path,
    output_dir: Path,
    video_name: str,
    camera_eye: tuple[float, float, float] | None,
    camera_target: tuple[float, float, float] | None,
    record_dataset: bool,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / video_name
    metrics_path = output_dir / "metrics.json"
    cmd = [
        str(args.isaac_python.expanduser()),
        str(args.render_script.expanduser().resolve()),
        "--headless",
        "--task",
        str(args.task),
        "--num_envs",
        "1",
        "--seed",
        str(int(args.seed)),
        "--output_dir",
        str(output_dir),
        "--video_path",
        str(video_path),
        "--metrics_path",
        str(metrics_path),
        "--settle_steps",
        str(int(args.restore_settle_steps)),
        "--demo_mode",
        "single_yam_trajectory",
        "--demo_steps",
        str(int(args.demo_steps)),
        "--demo_trajectory_path",
        str(trajectory_path),
        "--demo_trajectory_source",
        "graspgenx_replay",
        "--demo_trajectory_replay_mode",
        str(args.demo_trajectory_replay_mode),
        "--demo_trajectory_timing_mode",
        str(args.demo_trajectory_timing_mode),
        "--demo_trajectory_velocity_targets",
        "--stable_scene_path",
        str(scene_path),
        "--capture_interval",
        str(int(args.capture_interval)),
        "--fps",
        str(int(round(float(args.fps)))),
        "--render_width",
        str(int(args.render_width)),
        "--render_height",
        str(int(args.render_height)),
    ]
    if bool(args.scripted_target_transport):
        cmd.append("--scripted_target_transport")
    dataset_path = output_dir / "trajectory_dataset.npz"
    if record_dataset:
        cmd.extend(
            [
                "--record_trajectory_dataset",
                "--trajectory_dataset_path",
                str(dataset_path),
                "--record_rgb_width",
                str(int(args.record_rgb_width)),
                "--record_rgb_height",
                str(int(args.record_rgb_height)),
                "--record_rgb_interval",
                str(int(args.record_rgb_interval)),
            ]
        )
    if camera_eye is not None:
        cmd.extend(["--camera_eye", *(str(float(v)) for v in camera_eye)])
    if camera_target is not None:
        cmd.extend(["--camera_target", *(str(float(v)) for v in camera_target)])
    _run_logged(cmd, output_dir / "render.log", env=_isaac_env(args), cwd=_repo_root())
    return {
        "video_path": str(video_path),
        "metrics_path": str(metrics_path),
        "dataset_path": str(dataset_path) if record_dataset else "",
    }


def _refresh_scene_after_settle(args: argparse.Namespace, scene_path: Path, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_scene_path = output_dir / "stable_scene_raw.json"
    video_path = output_dir / "settle_refresh.mp4"
    metrics_path = output_dir / "metrics.json"
    cmd = [
        str(args.isaac_python.expanduser()),
        str(args.render_script.expanduser().resolve()),
        "--headless",
        "--task",
        str(args.task),
        "--num_envs",
        "1",
        "--seed",
        str(int(args.seed)),
        "--output_dir",
        str(output_dir),
        "--video_path",
        str(video_path),
        "--metrics_path",
        str(metrics_path),
        "--settle_steps",
        str(int(args.refresh_settle_steps)),
        "--demo_mode",
        "settle",
        "--demo_steps",
        "0",
        "--stable_scene_path",
        str(scene_path),
        "--stable_scene_output_path",
        str(raw_scene_path),
        "--capture_interval",
        str(max(int(args.refresh_settle_steps), 1)),
        "--fps",
        str(int(round(float(args.fps)))),
        "--render_width",
        str(int(args.refresh_render_width)),
        "--render_height",
        str(int(args.refresh_render_height)),
    ]
    _run_logged(cmd, output_dir / "render.log", env=_isaac_env(args), cwd=_repo_root())
    return {
        "raw_scene_path": str(raw_scene_path),
        "video_path": str(video_path),
        "metrics_path": str(metrics_path),
    }


def _scene_with_preserved_object_ids(
    raw_scene: dict[str, Any],
    input_scene: dict[str, Any],
    selected_id: str,
) -> dict[str, Any]:
    scene = copy.deepcopy(raw_scene)
    if isinstance(scene.get("target"), dict):
        scene["target"]["source_object_id"] = str(selected_id)
    input_clutter = input_scene.get("clutter") if isinstance(input_scene.get("clutter"), list) else []
    output_clutter = scene.get("clutter") if isinstance(scene.get("clutter"), list) else []
    for slot_idx, entry in enumerate(output_clutter):
        if not isinstance(entry, dict):
            continue
        source_id = None
        if slot_idx < len(input_clutter) and isinstance(input_clutter[slot_idx], dict):
            source_id = input_clutter[slot_idx].get("source_object_id")
        entry["source_object_id"] = str(source_id or f"clutter_{slot_idx:02d}")
    scene["planner_selected_object"] = copy.deepcopy(input_scene.get("planner_selected_object") or {})
    scene["planner_selected_object"]["object_id"] = str(selected_id)
    scene["planner_selected_object"]["settled_refresh"] = True
    return scene


def _update_objects_from_stable_scene(
    objects: list[dict[str, Any]],
    selected_id: str,
    scene: dict[str, Any],
) -> list[dict[str, Any]]:
    by_id = {str(obj["object_id"]): copy.deepcopy(obj) for obj in objects}
    target = scene.get("target") if isinstance(scene.get("target"), dict) else {}
    if selected_id in by_id and target:
        pos, quat, transform = _normalize_pose(target["root_position"], target["root_quat_wxyz"])
        by_id[selected_id]["root_position"] = pos
        by_id[selected_id]["root_quat_wxyz"] = quat
        by_id[selected_id]["root_transform"] = transform
    for slot_idx, entry in enumerate(scene.get("clutter") or []):
        if not isinstance(entry, dict):
            continue
        object_id = str(entry.get("source_object_id") or f"clutter_{slot_idx:02d}")
        if object_id not in by_id:
            continue
        pos, quat, transform = _normalize_pose(entry["root_position"], entry["root_quat_wxyz"])
        by_id[object_id]["root_position"] = pos
        by_id[object_id]["root_quat_wxyz"] = quat
        by_id[object_id]["root_transform"] = transform
    return [by_id[str(obj["object_id"])] for obj in objects]


def _validate_iteration(args: argparse.Namespace, dataset_path: Path, metrics_path: Path, scene_path: Path, output_path: Path) -> dict[str, Any]:
    cmd = [
        str(args.validator_python.expanduser()),
        str(args.validator_script.expanduser().resolve()),
        "--dataset_path",
        str(dataset_path),
        "--metrics_path",
        str(metrics_path),
        "--stable_scene_path",
        str(scene_path),
        "--output_path",
        str(output_path),
        "--expected_objects",
        "1",
    ]
    log_path = output_path.with_suffix(".log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(json.dumps({"event": "command_start", "cmd": cmd}) + "\n")
        log_file.flush()
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=_planner_env(args),
            cwd=str(_repo_root()),
            check=False,
        )
        log_file.write(json.dumps({"event": "command_done", "returncode": int(result.returncode)}) + "\n")
    if output_path.is_file():
        validation = _load_json(output_path)
        validation["validator_returncode"] = int(result.returncode)
        return validation
    raise RuntimeError(f"Validation command failed with code {result.returncode}; see {log_path}")


def _pose_from_dataset_array(array: np.ndarray) -> list[float]:
    arr = np.asarray(array)
    while arr.ndim > 1:
        arr = arr[0]
    return [float(v) for v in arr.tolist()]


def _update_objects_from_dataset(
    objects: list[dict[str, Any]],
    selected_id: str,
    planning_scene: dict[str, Any],
    dataset_path: Path,
) -> tuple[list[dict[str, Any]], list[float], dict[str, Any]]:
    by_id = {str(obj["object_id"]): copy.deepcopy(obj) for obj in objects}
    with np.load(dataset_path, allow_pickle=False) as data:
        target_pos = _pose_from_dataset_array(data["target_root_pos"][-1])
        target_quat = _pose_from_dataset_array(data["target_root_quat"][-1])
        by_id[str(selected_id)]["root_position"] = target_pos
        by_id[str(selected_id)]["root_quat_wxyz"] = target_quat
        by_id[str(selected_id)]["root_transform"] = _matrix_from_pose_wxyz(target_pos, target_quat)

        clutter_pos = np.asarray(data["clutter_root_pos"][-1])
        clutter_quat = np.asarray(data["clutter_root_quat"][-1])
        clutter_entries = planning_scene.get("clutter") if isinstance(planning_scene.get("clutter"), list) else []
        for slot_idx, entry in enumerate(clutter_entries):
            object_id = str(entry.get("source_object_id") or f"clutter_{slot_idx:02d}")
            if object_id not in by_id or slot_idx >= clutter_pos.shape[0]:
                continue
            pos = _pose_from_dataset_array(clutter_pos[slot_idx])
            quat = _pose_from_dataset_array(clutter_quat[slot_idx])
            by_id[object_id]["root_position"] = pos
            by_id[object_id]["root_quat_wxyz"] = quat
            by_id[object_id]["root_transform"] = _matrix_from_pose_wxyz(pos, quat)

        actual_joint = np.asarray(data["actual_joint_position"][-1])
        current_joint = _pose_from_dataset_array(actual_joint)
        z_values = np.asarray(data["target_root_pos"])
        initial_z = float(np.asarray(data["target_root_pos"][0]).reshape(-1, 3)[0, 2])
        max_z = float(z_values.reshape(z_values.shape[0], -1, 3)[:, 0, 2].max())

    updated = [by_id[str(obj["object_id"])] for obj in objects]
    motion = {
        "selected_object_id": str(selected_id),
        "final_position": by_id[str(selected_id)]["root_position"],
        "max_z": max_z,
        "lift_delta": max_z - initial_z,
    }
    return updated, current_joint, motion


def _joint_delta_summary(a: list[float] | None, b: list[float] | None) -> dict[str, Any]:
    if a is None or b is None:
        return {"enabled": False, "reason": "missing_joint"}
    arr_a = np.asarray(a, dtype=np.float32)
    arr_b = np.asarray(b, dtype=np.float32)
    if arr_a.shape != arr_b.shape:
        return {"enabled": False, "reason": "shape_mismatch", "shape_a": list(arr_a.shape), "shape_b": list(arr_b.shape)}
    delta = arr_b - arr_a
    return {
        "enabled": True,
        "max_abs": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "l2": float(np.linalg.norm(delta)) if delta.size else 0.0,
    }


def _compose_final_video(args: argparse.Namespace, left_videos: list[Path], right_videos: list[Path], output_path: Path) -> None:
    cmd = [
        str(args.compose_python.expanduser()),
        str(args.compose_script.expanduser().resolve()),
        "--left",
        *(str(path) for path in left_videos),
        "--right",
        *(str(path) for path in right_videos),
        "--output",
        str(output_path),
        "--fps",
        str(float(args.fps)),
        "--left_label",
        str(args.left_label),
        "--right_label",
        str(args.right_label),
    ]
    _run_logged(cmd, output_path.with_suffix(".compose.log"), env=_isaac_env(args), cwd=_repo_root())


def _final_validation(
    *,
    objects: list[dict[str, Any]],
    source_bin: dict[str, float],
    goal_bin: dict[str, float],
    picked_ids: list[str],
    margin: float,
    min_lift_delta: float,
    iteration_records: list[dict[str, Any]],
) -> dict[str, Any]:
    object_rows = []
    for obj in objects:
        pos = obj["root_position"]
        object_rows.append(
            {
                "object_id": str(obj["object_id"]),
                "asset_uuid": str(obj.get("asset", {}).get("uuid") or ""),
                "final_position": copy.deepcopy(pos),
                "inside_source_bin": _inside_bin_center(pos, source_bin, margin=margin),
                "inside_goal_bin": _inside_bin_center(pos, goal_bin, margin=margin),
            }
        )
    picked_set = set(picked_ids)
    checks = {
        "all_objects_picked_once": len(picked_set) == len(objects),
        "all_final_inside_goal_bin": all(row["inside_goal_bin"] for row in object_rows),
        "source_bin_clear": not any(row["inside_source_bin"] for row in object_rows),
        "all_iteration_lifts_valid": all(
            float(record.get("motion", {}).get("lift_delta", 0.0)) >= float(min_lift_delta)
            for record in iteration_records
        ),
    }
    return {
        "status": "accepted" if all(checks.values()) else "rejected",
        "checks": checks,
        "picked_object_ids": picked_ids,
        "objects": object_rows,
    }


def parse_args() -> argparse.Namespace:
    repo = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial_stable_scene_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--task", type=str, default="Dextrah-Single-YAM-Two-Bin-Primitive-Grasp")
    parser.add_argument("--seed", type=int, default=62022)
    parser.add_argument("--planner_script", type=Path, default=repo / "dextrah_lab/scene_scripts/plan_yam_graspgenx_curobo.py")
    parser.add_argument("--render_script", type=Path, default=repo / "dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py")
    parser.add_argument("--validator_script", type=Path, default=repo / "dextrah_lab/scene_scripts/validate_yam_pick_place_dataset.py")
    parser.add_argument("--compose_script", type=Path, default=repo / "dextrah_lab/scene_scripts/compose_two_view_video.py")
    parser.add_argument("--planner_python", type=Path, default=Path(sys.executable))
    parser.add_argument("--validator_python", type=Path, default=Path(sys.executable))
    parser.add_argument("--isaac_python", type=Path, default=Path("/home/lzha/code/.venvs/dextrah-isaaclab/bin/python"))
    parser.add_argument("--compose_python", type=Path, default=Path("/home/lzha/code/.venvs/dextrah-isaaclab/bin/python"))
    parser.add_argument("--graspgenx_root", type=Path, default=None)
    parser.add_argument("--curobo_root", type=Path, default=None)
    parser.add_argument("--fabrics_root", type=Path, default=Path("/home/lzha/code/FABRICS/src"))
    parser.add_argument("--cuda_visible_devices", type=str, default="0")
    parser.add_argument("--num_grasps", type=int, default=160)
    parser.add_argument("--topk", type=int, default=80)
    parser.add_argument("--max_plan_attempts", type=int, default=80)
    parser.add_argument("--yam_allow_lift_filter_fallback", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--yam_grasp_filter_min_keep", type=int, default=8)
    parser.add_argument(
        "--planner_yam_grasp_to_tool_z",
        type=float,
        default=0.04,
        help="Forwarded to plan_yam_graspgenx_curobo.py --yam_grasp_to_tool_z.",
    )
    parser.add_argument("--planner_clutter_margin", type=float, default=-0.025)
    parser.add_argument(
        "--planner_finger_preclose_offsets",
        type=str,
        default="0.0,0.008,0.016,0.024,0.032,0.040",
        help=(
            "Comma-separated offsets added to the current start finger joint for adaptive "
            "cuRobo planning collision states. Values are clamped at 0.0."
        ),
    )
    parser.add_argument(
        "--planner_finger_joint_positions",
        type=str,
        default="",
        help="Explicit comma-separated planning finger joint values; overrides preclose offsets when set.",
    )
    parser.add_argument("--max_attempts_per_object", type=int, default=8)
    parser.add_argument("--max_no_progress_passes", type=int, default=2)
    parser.add_argument("--max_picks", type=int, default=None)
    parser.add_argument("--allow_partial", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--reset_robot_home_between_picks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reset the YAM to the stable-scene start pose between picks while preserving updated object poses.",
    )
    parser.add_argument(
        "--continuous_episode",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Avoid per-iteration settle refreshes and preserve replay-updated object poses. "
            "Pairs with scripted return-home so the next pick starts from the prior episode state."
        ),
    )
    parser.add_argument(
        "--append_return_home_between_picks",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Append a scripted joint-space return-to-home segment to each rendered trajectory.",
    )
    parser.add_argument("--return_home_frames", type=int, default=180)
    parser.add_argument("--return_home_hold_frames", type=int, default=60)
    parser.add_argument("--source_margin", type=float, default=0.01)
    parser.add_argument("--goal_margin", type=float, default=0.01)
    parser.add_argument("--min_lift_delta", type=float, default=0.04)
    parser.add_argument("--move_to_bin_frames", type=int, default=300)
    parser.add_argument("--drop_height_above_bin", type=float, default=0.18)
    parser.add_argument("--scripted_bin_drop_y_offset", type=float, default=0.0)
    parser.add_argument(
        "--scripted_bin_drop_y_offsets",
        type=str,
        default="-0.075,-0.045,-0.015,0.015,0.045,0.075",
        help="Comma-separated y offsets cycled across picks to spread drops inside the goal bin.",
    )
    parser.add_argument("--scripted_place_mode", choices=("fallback", "always", "never"), default="always")
    parser.add_argument("--scripted_lift_mode", choices=("fallback", "always", "never"), default="always")
    parser.add_argument("--scripted_lift_height", type=float, default=0.14)
    parser.add_argument("--scripted_lift_frames", type=int, default=220)
    parser.add_argument("--start_guard_frames", type=int, default=60)
    parser.add_argument("--restore_settle_steps", type=int, default=180)
    parser.add_argument("--refresh_settle_steps", type=int, default=120)
    parser.add_argument("--refresh_render_width", type=int, default=320)
    parser.add_argument("--refresh_render_height", type=int, default=240)
    parser.add_argument("--demo_steps", type=int, default=1500)
    parser.add_argument("--demo_trajectory_replay_mode", choices=("dynamic", "kinematic"), default="dynamic")
    parser.add_argument("--demo_trajectory_timing_mode", choices=("realtime", "stretch"), default="realtime")
    parser.add_argument("--scripted_target_transport", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--capture_interval", type=int, default=4)
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--render_width", type=int, default=640)
    parser.add_argument("--render_height", type=int, default=480)
    parser.add_argument("--record_rgb_width", type=int, default=160)
    parser.add_argument("--record_rgb_height", type=int, default=120)
    parser.add_argument("--record_rgb_interval", type=int, default=1)
    parser.add_argument("--topdown_camera_eye", type=float, nargs=3, default=(-0.30, 0.0, 1.08))
    parser.add_argument("--topdown_camera_target", type=float, nargs=3, default=(-0.30, 0.0, 0.02))
    parser.add_argument("--left_label", type=str, default="default scene camera")
    parser.add_argument("--right_label", type=str, default="top-down camera")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stable_scene = _load_json(args.initial_stable_scene_path.expanduser().resolve())
    if stable_scene.get("format") != "dextrah_stable_scene_v1":
        raise ValueError(f"Expected dextrah_stable_scene_v1 payload in {args.initial_stable_scene_path}")
    source_bin = _bin_info(stable_scene, "source")
    goal_bin = _bin_info(stable_scene, "goal")
    objects = _objects_from_scene(stable_scene)
    home_joint = _home_joint_from_scene(stable_scene)
    if bool(args.continuous_episode):
        args.reset_robot_home_between_picks = False
        args.append_return_home_between_picks = True
    current_joint: list[float] | None = None
    picked_ids: list[str] = []
    failed_ids: set[str] = set()
    iteration_records: list[dict[str, Any]] = []
    default_videos: list[Path] = []
    topdown_videos: list[Path] = []
    drop_y_offsets = _parse_float_list(str(args.scripted_bin_drop_y_offsets))
    if not drop_y_offsets:
        drop_y_offsets = [float(args.scripted_bin_drop_y_offset)]

    _write_json(output_dir / "initial_objects.json", {"objects": objects, "source_bin": source_bin, "goal_bin": goal_bin})

    iteration = 0
    planning_skip_ids: set[str] = set()
    attempt_counts: dict[str, int] = {}
    candidate_exclusions: dict[str, set[int]] = {}
    no_progress_passes = 0
    while True:
        if args.max_picks is not None and iteration >= int(args.max_picks):
            break
        selected = _select_next_source_object(
            objects,
            source_bin,
            margin=float(args.source_margin),
            exclude_ids=planning_skip_ids | failed_ids,
        )
        if selected is None:
            if planning_skip_ids:
                skipped = sorted(planning_skip_ids)
                no_progress_passes += 1
                exhausted = no_progress_passes >= max(1, int(args.max_no_progress_passes))
                _write_json(
                    output_dir / f"planning_pass_exhausted_{no_progress_passes:02d}.json",
                    {
                        "iteration": int(iteration),
                        "skipped_object_ids": skipped,
                        "no_progress_passes": int(no_progress_passes),
                        "max_no_progress_passes": int(args.max_no_progress_passes),
                        "exhausted": bool(exhausted),
                    },
                )
                print(
                    json.dumps(
                        {
                            "event": "planning_pass_exhausted",
                            "iteration": iteration,
                            "skipped_object_ids": skipped,
                            "no_progress_passes": no_progress_passes,
                            "exhausted": exhausted,
                        }
                    ),
                    flush=True,
                )
                if exhausted:
                    failed_ids.update(skipped)
                    if not bool(args.allow_partial):
                        raise RuntimeError(
                            f"No remaining source-bin object planned successfully after "
                            f"{no_progress_passes} no-progress pass(es): {skipped}"
                        )
                    break
                planning_skip_ids.clear()
                continue
            if not bool(args.allow_partial):
                remaining = [
                    str(obj["object_id"])
                    for obj in objects
                    if _inside_bin_center(obj["root_position"], source_bin, margin=float(args.source_margin))
                    and str(obj["object_id"]) not in failed_ids
                ]
                if remaining:
                    raise RuntimeError(
                        f"No remaining source-bin object planned successfully at iteration {iteration}: {remaining}"
                    )
            break
        selected_id = str(selected["object_id"])
        iteration_dir = output_dir / f"iter_{iteration:02d}_{selected_id}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        previous_final_joint = None if current_joint is None else [float(v) for v in current_joint]
        planning_scene = _scene_for_object(
            stable_scene,
            objects,
            selected_id,
            current_joint=current_joint,
            iteration=iteration,
        )
        pre_scene_path = iteration_dir / "planning_scene_pre_settle.json"
        _write_json(pre_scene_path, planning_scene)
        print(json.dumps({"event": "iteration_start", "iteration": iteration, "object_id": selected_id}), flush=True)

        if bool(args.continuous_episode):
            refresh_info = {
                "enabled": False,
                "reason": "continuous_episode_preserves_dataset_poses",
                "raw_scene_path": "",
                "video_path": "",
                "metrics_path": "",
            }
        else:
            refresh_info = _refresh_scene_after_settle(args, pre_scene_path, iteration_dir / "settle_refresh")
            refreshed_scene_raw = _load_json(Path(refresh_info["raw_scene_path"]))
            planning_scene = _scene_with_preserved_object_ids(refreshed_scene_raw, planning_scene, selected_id)
            # A failed candidate plan should not become a physical state update.
            # Promote object poses only after a validated replay dataset.
        scene_path = iteration_dir / "planning_scene.json"
        _write_json(scene_path, planning_scene)
        planning_start_joint = _robot_joint_from_scene(planning_scene) or home_joint
        attempt_number = int(attempt_counts.get(selected_id, 0)) + 1
        attempt_counts[selected_id] = attempt_number
        base_finger_joint = float(planning_start_joint[-1]) if planning_start_joint else float(home_joint[-1])
        finger_options = _planning_finger_options(args, base_finger_joint)
        planning_finger_joint_position = finger_options[(attempt_number - 1) % len(finger_options)]
        excluded_grasp_original_indices = set(candidate_exclusions.get(selected_id, set()))

        drop_y_offset = float(drop_y_offsets[iteration % len(drop_y_offsets)])
        try:
            plan_info = _plan_iteration(
                args,
                scene_path,
                iteration_dir,
                iteration,
                drop_y_offset=drop_y_offset,
                attempt_number=attempt_number,
                planning_finger_joint_position=planning_finger_joint_position,
                excluded_grasp_original_indices=excluded_grasp_original_indices,
            )
        except Exception as exc:
            planning_skip_ids.add(selected_id)
            terminal_failed = attempt_number >= max(1, int(args.max_attempts_per_object))
            if terminal_failed:
                failed_ids.add(selected_id)
            failure = {
                "iteration": int(iteration),
                "object_id": selected_id,
                "status": "planning_failed",
                "attempt_number": int(attempt_number),
                "max_attempts_per_object": int(args.max_attempts_per_object),
                "terminal_failed": bool(terminal_failed),
                "planning_finger_joint_position": None
                if planning_finger_joint_position is None
                else float(planning_finger_joint_position),
                "excluded_grasp_original_indices": sorted(int(v) for v in excluded_grasp_original_indices),
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "scene_path": str(scene_path),
                "skip_ids_for_iteration": sorted(planning_skip_ids),
                "failed_object_ids": sorted(failed_ids),
            }
            _write_json(iteration_dir / "planning_failure.json", failure)
            iteration_records.append(failure)
            print(json.dumps({"event": "iteration_plan_failed", **failure}), flush=True)
            iteration += 1
            continue
        planner_trajectory_path = Path(plan_info["trajectory_path"])
        trajectory_path = planner_trajectory_path
        return_home_info: dict[str, Any] = {"enabled": False}
        if bool(args.append_return_home_between_picks):
            trajectory_path, return_home_info = _append_return_home_to_trajectory(
                planner_trajectory_path,
                home_joint=home_joint,
                return_frames=int(args.return_home_frames),
                hold_frames=int(args.return_home_hold_frames),
                output_path=iteration_dir / "trajectory_with_return_home.json",
            )
            plan_info["planner_trajectory_path"] = str(planner_trajectory_path)
            plan_info["trajectory_path"] = str(trajectory_path)
            plan_info["return_home"] = return_home_info
        default_info = _render_iteration(
            args,
            scene_path=scene_path,
            trajectory_path=trajectory_path,
            output_dir=iteration_dir / "default_view",
            video_name="default_view.mp4",
            camera_eye=None,
            camera_target=None,
            record_dataset=True,
        )
        validation_path = iteration_dir / "validation_metrics.json"
        validation = _validate_iteration(
            args,
            Path(default_info["dataset_path"]),
            Path(default_info["metrics_path"]),
            scene_path,
            validation_path,
        )
        objects, replay_final_joint, motion = _update_objects_from_dataset(
            objects,
            selected_id,
            planning_scene,
            Path(default_info["dataset_path"]),
        )
        current_joint = None if bool(args.reset_robot_home_between_picks) else replay_final_joint
        continuity = {
            "continuous_episode": bool(args.continuous_episode),
            "reset_robot_home_between_picks": bool(args.reset_robot_home_between_picks),
            "planning_start_joint": planning_start_joint,
            "previous_replay_final_joint": previous_final_joint,
            "replay_final_joint": replay_final_joint,
            "home_joint": home_joint,
            "planning_start_from_previous_final": _joint_delta_summary(previous_final_joint, planning_start_joint),
            "final_to_home": _joint_delta_summary(replay_final_joint, home_joint),
            "return_home": return_home_info,
        }
        validation_status = str(validation.get("status") or "unknown")
        if validation_status != "accepted":
            selected_original = plan_info.get("selected_grasp_original_index")
            if selected_original is not None:
                candidate_exclusions.setdefault(selected_id, set()).add(int(selected_original))
            planning_skip_ids.add(selected_id)
            terminal_failed = attempt_number >= max(1, int(args.max_attempts_per_object))
            if terminal_failed:
                failed_ids.add(selected_id)
        else:
            terminal_failed = False
        topdown_info = _render_iteration(
            args,
            scene_path=scene_path,
            trajectory_path=trajectory_path,
            output_dir=iteration_dir / "topdown_view",
            video_name="topdown_view.mp4",
            camera_eye=tuple(float(v) for v in args.topdown_camera_eye),
            camera_target=tuple(float(v) for v in args.topdown_camera_target),
            record_dataset=False,
        )
        if validation_status == "accepted":
            picked_ids.append(selected_id)
            no_progress_passes = 0
        default_videos.append(Path(default_info["video_path"]))
        topdown_videos.append(Path(topdown_info["video_path"]))
        record = {
            "iteration": int(iteration),
            "object_id": selected_id,
            "status": "accepted" if validation_status == "accepted" else "validation_failed",
            "pre_settle_scene_path": str(pre_scene_path),
            "settle_refresh": refresh_info,
            "scene_path": str(scene_path),
            "plan": plan_info,
            "default_replay": default_info,
            "topdown_replay": topdown_info,
            "validation_path": str(validation_path),
            "validation_status": validation_status,
            "motion": motion,
            "continuity": continuity,
            "retry_policy": {
                "attempt_number": int(attempt_number),
                "max_attempts_per_object": int(args.max_attempts_per_object),
                "terminal_failed": bool(terminal_failed),
                "planning_finger_options": finger_options,
                "planning_finger_joint_position": None
                if planning_finger_joint_position is None
                else float(planning_finger_joint_position),
                "excluded_grasp_original_indices_before_plan": sorted(int(v) for v in excluded_grasp_original_indices),
                "excluded_grasp_original_indices_after_validation": sorted(
                    int(v) for v in candidate_exclusions.get(selected_id, set())
                ),
            },
        }
        iteration_records.append(record)
        _write_json(iteration_dir / "iteration_summary.json", record)
        _write_json(output_dir / f"objects_after_iter_{iteration:02d}.json", {"objects": objects})
        event_name = "iteration_done" if validation_status == "accepted" else "iteration_validation_failed"
        print(
            json.dumps(
                {
                    "event": event_name,
                    "iteration": iteration,
                    "object_id": selected_id,
                    "validation_status": validation_status,
                    "motion": motion,
                }
            ),
            flush=True,
        )
        iteration += 1
        if validation_status == "accepted":
            planning_skip_ids.clear()

    final_validation = _final_validation(
        objects=objects,
        source_bin=source_bin,
        goal_bin=goal_bin,
        picked_ids=picked_ids,
        margin=float(args.goal_margin),
        min_lift_delta=float(args.min_lift_delta),
        iteration_records=iteration_records,
    )
    picked_set = set(picked_ids)
    unpicked_ids = {str(obj["object_id"]) for obj in objects if str(obj["object_id"]) not in picked_set}
    source_remaining_ids = {
        str(obj["object_id"])
        for obj in objects
        if _inside_bin_center(obj["root_position"], source_bin, margin=float(args.source_margin))
    }
    final_failed_ids = sorted(set(failed_ids) | unpicked_ids)
    final_validation["failed_object_ids"] = final_failed_ids
    final_validation["failed_object_count"] = int(len(final_failed_ids))
    final_validation["terminal_failed_object_ids"] = sorted(failed_ids)
    final_validation["source_remaining_object_ids"] = sorted(source_remaining_ids)
    final_validation["attempt_counts"] = {key: int(value) for key, value in sorted(attempt_counts.items())}
    final_validation["candidate_exclusions"] = {
        key: sorted(int(v) for v in value) for key, value in sorted(candidate_exclusions.items())
    }
    if args.allow_partial and final_validation["status"] == "rejected":
        final_validation["status"] = "partial"
        final_validation["allow_partial"] = True
    _write_json(output_dir / "iterative_validation.json", final_validation)

    composed_video = output_dir / "yam_two_bin_iterative_two_view.mp4"
    if default_videos and topdown_videos:
        _compose_final_video(args, default_videos, topdown_videos, composed_video)

    summary = {
        "status": final_validation["status"],
        "initial_stable_scene_path": str(args.initial_stable_scene_path.expanduser().resolve()),
        "output_dir": str(output_dir),
        "composed_video": str(composed_video) if composed_video.is_file() else "",
        "iterations": iteration_records,
        "final_validation_path": str(output_dir / "iterative_validation.json"),
        "final_objects": objects,
        "picked_object_ids": picked_ids,
        "failed_object_ids": final_failed_ids,
        "terminal_failed_object_ids": sorted(failed_ids),
        "source_remaining_object_ids": sorted(source_remaining_ids),
        "attempt_counts": {key: int(value) for key, value in sorted(attempt_counts.items())},
        "candidate_exclusions": {
            key: sorted(int(v) for v in value) for key, value in sorted(candidate_exclusions.items())
        },
        "default_videos": [str(path) for path in default_videos],
        "topdown_videos": [str(path) for path in topdown_videos],
    }
    _write_json(output_dir / "iterative_demo_summary.json", summary)
    print(json.dumps({"event": "iterative_demo_complete", "status": summary["status"], "summary": summary}, indent=2), flush=True)
    if summary["status"] not in {"accepted", "partial"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
