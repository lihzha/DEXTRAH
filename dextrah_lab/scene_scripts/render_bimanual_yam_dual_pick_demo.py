#!/usr/bin/env python3
"""Replay a synchronized bimanual YAM dual-pick trajectory in Isaac Lab."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


def _log(message: str) -> None:
    print(f"[bimanual-yam-dual-demo] {message}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=str, default="Dextrah-Bimanual-YAM-Cube-Grasp")
    parser.add_argument("--trajectory_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--render_stride", type=int, default=3)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--sim_steps_per_frame", type=int, default=1)
    parser.add_argument("--dynamic_replay", action="store_true")
    parser.add_argument("--settle_steps", type=int, default=60)
    parser.add_argument("--disable_fabric", action="store_true")
    parser.add_argument("--video_crf", type=int, default=18)
    parser.add_argument("--warmup_render_updates", type=int, default=6)
    parser.add_argument("--render_sync_updates", type=int, default=3)
    parser.add_argument("--force_camera_recompute", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--visual_motion_check", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fail_on_static_visual", action="store_true")
    parser.add_argument("--visual_motion_min_changed_pixels", type=int, default=2500)
    parser.add_argument("--visual_motion_diff_threshold", type=int, default=8)
    AppLauncher.add_app_launcher_args(parser)
    return parser


parser = _build_parser()
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


_log("importing runtime modules")
import gymnasium as gym  # noqa: E402
import imageio.v2 as imageio  # noqa: E402
import numpy as np  # noqa: E402
import omni.usd  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

_log("importing Isaac Lab modules")
import isaaclab.sim as sim_utils  # noqa: E402
import isaaclab_tasks  # noqa: F401,E402
from isaaclab.assets import RigidObject, RigidObjectCfg  # noqa: E402
from isaaclab.sensors.camera import Camera, CameraCfg  # noqa: E402
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

_log("importing DEXTRAH task and bimanual YAM constants")
import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup  # noqa: F401,E402
from dextrah_lab.assets.yam.bimanual_yam import (  # noqa: E402
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_TABLE_SURFACE_Z,
    MOLMOACT2_TOP_CAMERA_INTRINSIC,
    MOLMOACT2_TOP_CAMERA_LOCAL_POS,
    MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ,
    MOLMOACT2_TOP_CAMERA_PARENT_BODY,
    MOLMOACT2_WRIST_CAMERA_INTRINSIC,
    MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
    MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_vec(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1.0e-9:
        raise ValueError(f"Cannot normalize near-zero vector: {vec}")
    return vec / norm


def _quat_from_matrix(rot: np.ndarray) -> tuple[float, float, float, float]:
    trace = float(np.trace(rot))
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (rot[2, 1] - rot[1, 2]) / s
        qy = (rot[0, 2] - rot[2, 0]) / s
        qz = (rot[1, 0] - rot[0, 1]) / s
    else:
        idx = int(np.argmax(np.diag(rot)))
        if idx == 0:
            s = math.sqrt(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2]) * 2.0
            qw = (rot[2, 1] - rot[1, 2]) / s
            qx = 0.25 * s
            qy = (rot[0, 1] + rot[1, 0]) / s
            qz = (rot[0, 2] + rot[2, 0]) / s
        elif idx == 1:
            s = math.sqrt(1.0 + rot[1, 1] - rot[0, 0] - rot[2, 2]) * 2.0
            qw = (rot[0, 2] - rot[2, 0]) / s
            qx = (rot[0, 1] + rot[1, 0]) / s
            qy = 0.25 * s
            qz = (rot[1, 2] + rot[2, 1]) / s
        else:
            s = math.sqrt(1.0 + rot[2, 2] - rot[0, 0] - rot[1, 1]) * 2.0
            qw = (rot[1, 0] - rot[0, 1]) / s
            qx = (rot[0, 2] + rot[2, 0]) / s
            qy = (rot[1, 2] + rot[2, 1]) / s
            qz = 0.25 * s
    quat = np.asarray([qw, qx, qy, qz], dtype=np.float64)
    quat /= np.linalg.norm(quat)
    return tuple(float(x) for x in quat)


def _look_at_quat_world(
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    up: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> tuple[float, float, float, float]:
    eye_np = np.asarray(eye, dtype=np.float64)
    target_np = np.asarray(target, dtype=np.float64)
    forward = _normalize_vec(target_np - eye_np)
    up_hint = _normalize_vec(np.asarray(up, dtype=np.float64))
    right = np.cross(up_hint, forward)
    if np.linalg.norm(right) < 1.0e-6:
        right = np.cross(np.asarray([0.0, 1.0, 0.0], dtype=np.float64), forward)
    right = _normalize_vec(right)
    true_up = _normalize_vec(np.cross(forward, right))
    rot = np.column_stack([forward, right, true_up])
    return _quat_from_matrix(rot)


def _find_body_prim_path(stage: Any, body_name: str) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for prim in stage.Traverse():
        if prim.GetName() != body_name:
            continue
        path = str(prim.GetPath())
        if "/joints" in path or "/collisions" in path or "/visuals" in path:
            continue
        fallback.append(path)
        if "/World/envs/env_0/" in path:
            preferred.append(path)
    matches = preferred or fallback
    if not matches:
        raise RuntimeError(f"Could not find body prim named {body_name!r}")
    matches.sort(key=len)
    return matches[0]


def _spawn_from_intrinsic(intrinsic: tuple[float, ...]) -> sim_utils.PinholeCameraCfg:
    return sim_utils.PinholeCameraCfg.from_intrinsic_matrix(
        intrinsic_matrix=list(intrinsic),
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        focal_length=24.0,
        focus_distance=400.0,
        clipping_range=(0.01, 10.0),
    )


def _make_policy_camera(
    name: str,
    parent_path: str,
    pos: tuple[float, float, float],
    quat: tuple[float, float, float, float],
    intrinsic: tuple[float, ...],
) -> Camera:
    cfg = CameraCfg(
        prim_path=f"{parent_path}/{name}_dual_pick_sensor",
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=_spawn_from_intrinsic(intrinsic),
        offset=CameraCfg.OffsetCfg(pos=pos, rot=quat, convention="world"),
    )
    return Camera(cfg)


def _make_overview_camera() -> Camera:
    eye = (-0.46, -1.08, 0.22)
    target = (-0.30, 0.0, 0.16)
    cfg = CameraCfg(
        prim_path="/World/BimanualYamDualPickOverviewCamera",
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=16.0,
            horizontal_aperture=20.955,
            clipping_range=(0.01, 20.0),
        ),
        offset=CameraCfg.OffsetCfg(pos=eye, rot=_look_at_quat_world(eye, target), convention="world"),
    )
    return Camera(cfg)


def _initialize_camera_sensor(camera: Camera) -> None:
    if camera.is_initialized:
        camera.reset()
        return
    camera._initialize_impl()
    camera._is_initialized = True
    camera.reset()


def _initialize_cameras(cameras: dict[str, Camera]) -> None:
    for name, camera in cameras.items():
        _log(f"initializing camera sensor: {name}")
        _initialize_camera_sensor(camera)


def _flush_render_updates(count: int) -> None:
    for _ in range(max(0, int(count))):
        simulation_app.update()


def _sync_render_and_update_cameras(
    *,
    task_env: Any,
    cameras: dict[str, Camera],
    camera_dt: float,
    force_recompute: bool,
    render_sync_updates: int,
) -> dict[str, np.ndarray]:
    task_env.scene.write_data_to_sim()
    task_env.sim.render()
    _flush_render_updates(render_sync_updates)

    images: dict[str, np.ndarray] = {}
    for name, camera in cameras.items():
        camera.update(camera_dt, force_recompute=force_recompute)
        if force_recompute:
            camera.update(0.0, force_recompute=True)
        images[name] = _rgb_to_array(camera.data.output["rgb"])
    return images


def _warmup_cameras(task_env: Any, cameras: dict[str, Camera], sim_dt: float, updates: int) -> None:
    for _ in range(max(0, int(updates))):
        task_env.scene.write_data_to_sim()
        task_env.sim.render()
        _flush_render_updates(1)
        for camera in cameras.values():
            camera.update(sim_dt, force_recompute=True)


def _rgb_to_array(rgb_tensor: torch.Tensor) -> np.ndarray:
    rgb = rgb_tensor.detach().cpu().numpy()
    if rgb.ndim == 4:
        rgb = rgb[0]
    if rgb.shape[-1] > 3:
        rgb = rgb[..., :3]
    if rgb.dtype != np.uint8:
        if rgb.max(initial=0.0) <= 1.0:
            rgb = np.clip(rgb * 255.0, 0.0, 255.0)
        rgb = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    return np.ascontiguousarray(rgb)


def _draw_label(image: Image.Image, label: str) -> Image.Image:
    draw = ImageDraw.Draw(image)
    margin = 8
    box_h = 24
    text_bbox = draw.textbbox((0, 0), label)
    box_w = text_bbox[2] - text_bbox[0] + 2 * margin
    draw.rectangle((0, 0, box_w, box_h), fill=(0, 0, 0))
    draw.text((margin, 5), label, fill=(255, 255, 255))
    return image


def _make_composite(images: dict[str, np.ndarray]) -> np.ndarray:
    tiles = []
    for label in ("overview", "top_cam", "left_cam", "right_cam"):
        tile = Image.fromarray(images[label]).resize((MOLMOACT2_CAMERA_WIDTH, MOLMOACT2_CAMERA_HEIGHT))
        tiles.append(_draw_label(tile, label))
    composite = Image.new("RGB", (MOLMOACT2_CAMERA_WIDTH * 2, MOLMOACT2_CAMERA_HEIGHT * 2), (0, 0, 0))
    composite.paste(tiles[0], (0, 0))
    composite.paste(tiles[1], (MOLMOACT2_CAMERA_WIDTH, 0))
    composite.paste(tiles[2], (0, MOLMOACT2_CAMERA_HEIGHT))
    composite.paste(tiles[3], (MOLMOACT2_CAMERA_WIDTH, MOLMOACT2_CAMERA_HEIGHT))
    return np.asarray(composite)


def _save_png(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path)


def _write_video(path: Path, frames: list[np.ndarray], fps: int, crf: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        quality=None,
        output_params=["-crf", str(crf), "-pix_fmt", "yuv420p"],
        macro_block_size=1,
    )
    try:
        for frame in frames:
            writer.append_data(frame)
    finally:
        writer.close()


def _ffprobe(path: Path) -> dict[str, Any]:
    if shutil.which("ffprobe") is None:
        return {"available": False}
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,nb_frames,avg_frame_rate,duration",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return {
        "available": True,
        "returncode": proc.returncode,
        "stdout": json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else {},
        "stderr": proc.stderr,
    }


def _image_stats(array: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def _changed_pixels(
    first: np.ndarray,
    last: np.ndarray,
    *,
    box: tuple[int, int, int, int],
    threshold: int,
) -> int:
    x0, y0, x1, y1 = box
    first_crop = first[y0:y1, x0:x1, :3].astype(np.int16)
    last_crop = last[y0:y1, x0:x1, :3].astype(np.int16)
    delta = np.max(np.abs(first_crop - last_crop), axis=2)
    return int(np.count_nonzero(delta > int(threshold)))


def _visual_motion_diagnostics(
    video_frames: dict[str, list[np.ndarray]],
    *,
    min_changed_pixels: int,
    diff_threshold: int,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "checked": False,
        "passed": False,
        "min_changed_pixels": int(min_changed_pixels),
        "diff_threshold": int(diff_threshold),
    }
    top_frames = video_frames.get("top_cam", [])
    overview_frames = video_frames.get("overview", [])
    if len(top_frames) < 2:
        diagnostics["reason"] = "top_cam_has_fewer_than_two_frames"
        diagnostics["top_cam_frame_count"] = len(top_frames)
        return diagnostics

    top_height, top_width = top_frames[0].shape[:2]
    crop_boxes = {
        "top_left_arm_crop": (0, int(top_height * 0.35), int(top_width * 0.45), top_height),
        "top_right_arm_crop": (int(top_width * 0.55), int(top_height * 0.35), top_width, top_height),
        "top_center_workspace_crop": (
            int(top_width * 0.22),
            int(top_height * 0.25),
            int(top_width * 0.78),
            top_height,
        ),
    }
    changed_pixels = {
        name: _changed_pixels(top_frames[0], top_frames[-1], box=box, threshold=diff_threshold)
        for name, box in crop_boxes.items()
    }
    diagnostics.update(
        {
            "checked": True,
            "top_cam_frame_count": len(top_frames),
            "top_cam_shape": [int(top_height), int(top_width)],
            "crop_boxes_xyxy": {name: [int(v) for v in box] for name, box in crop_boxes.items()},
            "changed_pixels": changed_pixels,
            "min_arm_changed_pixels": int(
                min(changed_pixels["top_left_arm_crop"], changed_pixels["top_right_arm_crop"])
            ),
            "max_arm_changed_pixels": int(
                max(changed_pixels["top_left_arm_crop"], changed_pixels["top_right_arm_crop"])
            ),
            "max_changed_pixels": int(max(changed_pixels.values())),
        }
    )
    if len(overview_frames) >= 2:
        overview_height, overview_width = overview_frames[0].shape[:2]
        overview_box = (
            int(overview_width * 0.10),
            int(overview_height * 0.10),
            int(overview_width * 0.90),
            int(overview_height * 0.95),
        )
        diagnostics["overview_changed_pixels"] = _changed_pixels(
            overview_frames[0],
            overview_frames[-1],
            box=overview_box,
            threshold=diff_threshold,
        )
        diagnostics["overview_crop_box_xyxy"] = [int(v) for v in overview_box]
    diagnostics["passed"] = bool(int(diagnostics["min_arm_changed_pixels"]) >= int(min_changed_pixels))
    return diagnostics


def _root_state(device: torch.device, pos: list[float], quat_wxyz: list[float] | None = None) -> torch.Tensor:
    quat = quat_wxyz or [1.0, 0.0, 0.0, 0.0]
    state = torch.zeros((1, 13), dtype=torch.float32, device=device)
    state[0, 0:3] = torch.tensor(pos, dtype=torch.float32, device=device)
    state[0, 3:7] = torch.tensor(quat, dtype=torch.float32, device=device)
    return state


def _as_float_list(tensor: torch.Tensor) -> list[float]:
    return [float(v) for v in tensor.detach().cpu().tolist()]


def _joint_target_from_frame(
    *,
    robot: Any,
    planned_ids: list[int],
    frame: dict[str, Any],
) -> torch.Tensor:
    joint_pos = robot.data.default_joint_pos.clone()
    q = torch.tensor(frame["joint_position"], dtype=torch.float32, device=robot.device)
    joint_pos[:, planned_ids] = q.unsqueeze(0)
    return joint_pos


def _write_joint_target(robot: Any, joint_pos: torch.Tensor) -> None:
    robot.set_joint_position_target(joint_pos)
    robot.write_data_to_sim()


def _write_joint_state(robot: Any, joint_pos: torch.Tensor) -> None:
    joint_vel = torch.zeros_like(joint_pos)
    robot.write_joint_state_to_sim(joint_pos, joint_vel)
    _write_joint_target(robot, joint_pos)


def _step_dynamic_scene(task_env: Any, robot: Any, joint_pos: torch.Tensor, sim_dt: float, steps: int) -> None:
    for _ in range(max(1, int(steps))):
        _write_joint_target(robot, joint_pos)
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(sim_dt)


def _settle_dynamic_scene(task_env: Any, robot: Any, joint_pos: torch.Tensor, sim_dt: float, steps: int) -> None:
    for _ in range(max(0, int(steps))):
        _write_joint_target(robot, joint_pos)
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(sim_dt)


def _rigid_object_state_record(obj: RigidObject) -> dict[str, list[float]]:
    data = obj.data
    root_vel = getattr(data, "root_vel_w", None)
    if root_vel is not None:
        lin_vel = root_vel[0, 0:3]
        ang_vel = root_vel[0, 3:6]
    else:
        lin_vel = getattr(data, "root_lin_vel_w", torch.zeros((1, 3), device=obj.device))[0]
        ang_vel = getattr(data, "root_ang_vel_w", torch.zeros((1, 3), device=obj.device))[0]
    return {
        "position": _as_float_list(data.root_pos_w[0]),
        "quat_wxyz": _as_float_list(data.root_quat_w[0]),
        "linear_velocity": _as_float_list(lin_vel),
        "angular_velocity": _as_float_list(ang_vel),
    }


def _find_body_id(robot: Any, name: str) -> int:
    ids, names = robot.find_bodies(name)
    if len(ids) != 1:
        raise RuntimeError(f"Expected one body named {name!r}, got {names}")
    return int(ids[0])


def _body_position(robot: Any, body_id: int) -> np.ndarray:
    return robot.data.body_pos_w[0, body_id].detach().cpu().numpy().astype(np.float64)


def _finger_metrics(robot: Any, body_ids: dict[str, Any], side: str, object_position: list[float]) -> dict[str, Any]:
    finger_positions = [_body_position(robot, body_id) for body_id in body_ids[f"{side}_fingers"]]
    finger_center = 0.5 * (finger_positions[0] + finger_positions[1])
    object_np = np.asarray(object_position, dtype=np.float64)
    return {
        "link6_position": [float(v) for v in _body_position(robot, int(body_ids[f"{side}_link6"]))],
        "finger_positions": [[float(v) for v in pos] for pos in finger_positions],
        "finger_center_position": [float(v) for v in finger_center],
        "gripper_width": float(np.linalg.norm(finger_positions[0] - finger_positions[1])),
        "object_to_finger_center_distance": float(np.linalg.norm(object_np - finger_center)),
    }


def _summarize_object_trace(
    *,
    object_trace: list[dict[str, Any]],
    object_records: dict[str, Any],
    dynamic_replay: bool,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"dynamic_replay": bool(dynamic_replay)}
    for side in ("left", "right"):
        initial = [float(v) for v in object_records[side]["bimanual_center_world"]]
        actual_positions = [
            record[f"{side}_actual_position"]
            for record in object_trace
            if isinstance(record.get(f"{side}_actual_position"), list)
        ]
        if not actual_positions:
            continue
        initial_z = float(initial[2])
        max_z = max(float(pos[2]) for pos in actual_positions)
        final = [float(v) for v in actual_positions[-1]]
        xy_error = float(np.linalg.norm(np.asarray(final[:2], dtype=np.float64) - np.asarray(initial[:2], dtype=np.float64)))
        summary[side] = {
            "initial_position": initial,
            "final_position": final,
            "max_z": max_z,
            "max_lift": max_z - initial_z,
            "final_lift": float(final[2]) - initial_z,
            "final_xy_error": xy_error,
            "lifted_at_least_2cm": bool(max_z - initial_z >= 0.02),
        }
    return summary


def _object_position_for_frame(
    *,
    robot: Any,
    body_id: int,
    frame_idx: int,
    object_record: dict[str, Any],
) -> list[float]:
    attach_frame = int(object_record.get("attach_frame", 0))
    initial = [float(v) for v in object_record["bimanual_center_world"]]
    if frame_idx < attach_frame:
        return initial
    link_pos = robot.data.body_pos_w[0, body_id].detach().cpu().numpy()
    offset = np.asarray(object_record.get("tool_minus_object_center_world_at_grasp", [0.0, 0.0, 0.0]), dtype=np.float64)
    pos = np.asarray(link_pos, dtype=np.float64) - offset
    pos[2] = max(pos[2], MOLMOACT2_TABLE_SURFACE_Z + 0.5 * float(object_record["dims"][2]))
    return [float(v) for v in pos]


def _spawn_right_object(object_record: dict[str, Any], *, dynamic: bool) -> RigidObject:
    dims = tuple(float(v) for v in object_record["dims"])
    center = tuple(float(v) for v in object_record["bimanual_center_world"])
    rigid_props_kwargs: dict[str, Any] = {
        "rigid_body_enabled": True,
        "kinematic_enabled": not dynamic,
        "disable_gravity": not dynamic,
        "solver_position_iteration_count": 32 if dynamic else 16,
        "solver_velocity_iteration_count": 8 if dynamic else 4,
    }
    if dynamic:
        rigid_props_kwargs.update(
            {
                "linear_damping": 0.20,
                "angular_damping": 1.00,
                "enable_gyroscopic_forces": True,
                "sleep_threshold": 0.02,
                "stabilization_threshold": 0.01,
                "max_depenetration_velocity": 1.0,
            }
        )
    cfg = RigidObjectCfg(
        prim_path="/World/envs/env_0/RightObject",
        spawn=sim_utils.CuboidCfg(
            size=dims,
            collision_props=sim_utils.CollisionPropertiesCfg(collision_enabled=True, contact_offset=0.002),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(**rigid_props_kwargs),
            mass_props=sim_utils.MassPropertiesCfg(density=38.0 if dynamic else 40.0),
            physics_material=RigidBodyMaterialCfg(
                static_friction=1.6 if dynamic else 1.4,
                dynamic_friction=1.1,
                restitution=0.0,
                friction_combine_mode="max",
                restitution_combine_mode="min",
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.20, 0.78, 0.45), roughness=0.65),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=center, rot=(1.0, 0.0, 0.0, 0.0)),
    )
    return RigidObject(cfg)


def _configure_env_for_left_object(env_cfg: Any, left_record: dict[str, Any], *, dynamic: bool) -> None:
    dims = [float(v) for v in left_record["dims"]]
    center = [float(v) for v in left_record["bimanual_center_world"]]
    size = float(max(dims))
    env_cfg.cube_size = size
    env_cfg.pickup_x = float(center[0])
    env_cfg.pickup_y = float(center[1])
    env_cfg.cube_spawn_xy_randomization = 0.0
    env_cfg.cube_spawn_yaw_randomization_deg = 0.0
    env_cfg.cube_spawn_z = float(center[2])
    env_cfg.cube.spawn.size = tuple(dims)
    env_cfg.cube.init_state.pos = tuple(center)
    env_cfg.cube.spawn.rigid_props.kinematic_enabled = not dynamic
    env_cfg.cube.spawn.rigid_props.disable_gravity = not dynamic
    env_cfg.cube.spawn.visual_material = sim_utils.PreviewSurfaceCfg(
        diffuse_color=(0.14, 0.58, 0.96),
        roughness=0.65,
    )


def main() -> None:
    trajectory_path = args_cli.trajectory_path.expanduser().resolve()
    trajectory = _load_json(trajectory_path)
    if trajectory.get("format") != "dextrah_bimanual_yam_dual_pick_v1":
        raise ValueError(f"Expected dextrah_bimanual_yam_dual_pick_v1 trajectory: {trajectory_path}")
    frames = trajectory.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"Trajectory has no frames: {trajectory_path}")
    object_records = trajectory.get("object_records")
    if not isinstance(object_records, dict) or "left" not in object_records or "right" not in object_records:
        raise ValueError("Trajectory is missing left/right object_records")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args_cli.output_dir or Path("runs") / "bimanual_yam_dual_pick_demo" / timestamp
    output_dir = output_dir.resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"writing artifacts to {output_dir}")

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    dynamic_replay = bool(args_cli.dynamic_replay)
    _configure_env_for_left_object(env_cfg, object_records["left"], dynamic=dynamic_replay)

    _log("creating Gym environment")
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    task_env = env.unwrapped
    try:
        env.reset(seed=args_cli.seed)
        robot = task_env._robot
        left_object = task_env._cube
        right_object = _spawn_right_object(object_records["right"], dynamic=dynamic_replay)
        task_env.scene.rigid_objects["right_object"] = right_object

        task_env.sim.reset()
        env.reset(seed=args_cli.seed)
        right_object.write_root_state_to_sim(_root_state(right_object.device, object_records["right"]["bimanual_center_world"]))
        left_object.write_root_state_to_sim(_root_state(left_object.device, object_records["left"]["bimanual_center_world"]))

        joint_index = {name: idx for idx, name in enumerate(robot.joint_names)}
        planned_names = [str(v) for v in trajectory.get("joint_names", [])]
        missing = [name for name in planned_names if name not in joint_index]
        if missing:
            raise RuntimeError(f"Trajectory joint names missing from bimanual robot: {missing}")
        planned_ids = [joint_index[name] for name in planned_names]
        body_ids = {
            "left_link6": _find_body_id(robot, "left_link_6"),
            "right_link6": _find_body_id(robot, "right_link_6"),
            "left_fingers": [
                _find_body_id(robot, "left_link_left_finger"),
                _find_body_id(robot, "left_link_right_finger"),
            ],
            "right_fingers": [
                _find_body_id(robot, "right_link_left_finger"),
                _find_body_id(robot, "right_link_right_finger"),
            ],
        }

        sim_dt = float(task_env.cfg.sim.dt)
        render_stride = max(1, int(args_cli.render_stride))
        sim_steps_per_frame = max(1, int(args_cli.sim_steps_per_frame))
        video_frames: dict[str, list[np.ndarray]] = {name: [] for name in cameras}
        composite_frames: list[np.ndarray] = []
        sample_stats: dict[str, dict[str, dict[str, float]]] = {}
        object_trace: list[dict[str, Any]] = []

        initial_joint_pos = _joint_target_from_frame(robot=robot, planned_ids=planned_ids, frame=frames[0])
        _write_joint_state(robot, initial_joint_pos)
        right_object.write_root_state_to_sim(_root_state(right_object.device, object_records["right"]["bimanual_center_world"]))
        left_object.write_root_state_to_sim(_root_state(left_object.device, object_records["left"]["bimanual_center_world"]))
        task_env.scene.write_data_to_sim()
        task_env.sim.forward()
        task_env.scene.update(sim_dt)
        if dynamic_replay and int(args_cli.settle_steps) > 0:
            _log(f"settling dynamic replay for {int(args_cli.settle_steps)} sim steps")
            _settle_dynamic_scene(task_env, robot, initial_joint_pos, sim_dt, int(args_cli.settle_steps))

        stage = omni.usd.get_context().get_stage()
        base_path = _find_body_prim_path(stage, MOLMOACT2_TOP_CAMERA_PARENT_BODY)
        left_wrist_path = _find_body_prim_path(stage, MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY)
        right_wrist_path = _find_body_prim_path(stage, MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY)
        _log(f"camera parents: top={base_path}, left={left_wrist_path}, right={right_wrist_path}")

        cameras = {
            "overview": _make_overview_camera(),
            "top_cam": _make_policy_camera(
                "top_cam",
                base_path,
                MOLMOACT2_TOP_CAMERA_LOCAL_POS,
                MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ,
                MOLMOACT2_TOP_CAMERA_INTRINSIC,
            ),
            "left_cam": _make_policy_camera(
                "left_cam",
                left_wrist_path,
                MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
                MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
                MOLMOACT2_WRIST_CAMERA_INTRINSIC,
            ),
            "right_cam": _make_policy_camera(
                "right_cam",
                right_wrist_path,
                MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
                MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
                MOLMOACT2_WRIST_CAMERA_INTRINSIC,
            ),
        }
        _initialize_cameras(cameras)
        _warmup_cameras(task_env, cameras, sim_dt, int(args_cli.warmup_render_updates))

        source_indices = range(len(frames)) if dynamic_replay else range(0, len(frames), render_stride)
        for source_frame_idx in source_indices:
            frame = frames[source_frame_idx]
            joint_pos = _joint_target_from_frame(robot=robot, planned_ids=planned_ids, frame=frame)
            left_pos = _object_position_for_frame(
                robot=robot,
                body_id=int(body_ids["left_link6"]),
                frame_idx=source_frame_idx,
                object_record=object_records["left"],
            )
            right_pos = _object_position_for_frame(
                robot=robot,
                body_id=int(body_ids["right_link6"]),
                frame_idx=source_frame_idx,
                object_record=object_records["right"],
            )

            if dynamic_replay:
                _step_dynamic_scene(task_env, robot, joint_pos, sim_dt, sim_steps_per_frame)
                capture_frame = source_frame_idx % render_stride == 0 or source_frame_idx == len(frames) - 1
                camera_dt = sim_dt * sim_steps_per_frame
            else:
                _write_joint_state(robot, joint_pos)
                left_object.write_root_state_to_sim(_root_state(left_object.device, left_pos))
                right_object.write_root_state_to_sim(_root_state(right_object.device, right_pos))
                task_env.scene.write_data_to_sim()
                task_env.sim.forward()
                task_env.scene.update(sim_dt)
                capture_frame = True
                camera_dt = sim_dt
            if not capture_frame:
                continue

            frame_images = _sync_render_and_update_cameras(
                task_env=task_env,
                cameras=cameras,
                camera_dt=camera_dt,
                force_recompute=bool(args_cli.force_camera_recompute),
                render_sync_updates=int(args_cli.render_sync_updates),
            )
            task_env.scene.update(sim_dt)
            left_state = _rigid_object_state_record(left_object)
            right_state = _rigid_object_state_record(right_object)
            left_actual_pos = left_state["position"]
            right_actual_pos = right_state["position"]
            left_metrics = _finger_metrics(robot, body_ids, "left", left_actual_pos)
            right_metrics = _finger_metrics(robot, body_ids, "right", right_actual_pos)

            for name, rgb in frame_images.items():
                frame_images[name] = rgb
                video_frames[name].append(rgb)
                _save_png(frames_dir / name / f"{len(composite_frames):04d}.png", rgb)
            composite = _make_composite(frame_images)
            composite_frames.append(composite)
            _save_png(frames_dir / "composite" / f"{len(composite_frames) - 1:04d}.png", composite)
            object_trace.append(
                {
                    "render_frame": len(composite_frames) - 1,
                    "source_frame": source_frame_idx,
                    "left_position": left_pos,
                    "right_position": right_pos,
                    "left_reference_position": left_pos,
                    "right_reference_position": right_pos,
                    "left_actual_position": left_actual_pos,
                    "right_actual_position": right_actual_pos,
                    "left_actual_quat_wxyz": left_state["quat_wxyz"],
                    "right_actual_quat_wxyz": right_state["quat_wxyz"],
                    "left_actual_linear_velocity": left_state["linear_velocity"],
                    "right_actual_linear_velocity": right_state["linear_velocity"],
                    "left_actual_angular_velocity": left_state["angular_velocity"],
                    "right_actual_angular_velocity": right_state["angular_velocity"],
                    "left_finger_metrics": left_metrics,
                    "right_finger_metrics": right_metrics,
                    "actual_joint_position": _as_float_list(robot.data.joint_pos[0, planned_ids]),
                    "target_joint_position": [float(v) for v in frame["joint_position"]],
                    "left_phase": frame.get("left_phase"),
                    "right_phase": frame.get("right_phase"),
                }
            )
            if source_frame_idx in {0, len(frames) // 2, len(frames) - 1}:
                sample_stats[str(source_frame_idx)] = {name: _image_stats(image) for name, image in frame_images.items()}

        video_paths: dict[str, str] = {}
        for name, rgb_frames in video_frames.items():
            path = output_dir / f"{name}.mp4"
            _write_video(path, rgb_frames, args_cli.fps, args_cli.video_crf)
            video_paths[name] = str(path)
        composite_path = output_dir / "bimanual_yam_dual_pick_composite.mp4"
        _write_video(composite_path, composite_frames, args_cli.fps, args_cli.video_crf)
        video_paths["composite"] = str(composite_path)
        visual_motion = (
            _visual_motion_diagnostics(
                video_frames,
                min_changed_pixels=int(args_cli.visual_motion_min_changed_pixels),
                diff_threshold=int(args_cli.visual_motion_diff_threshold),
            )
            if bool(args_cli.visual_motion_check)
            else {"checked": False, "reason": "disabled"}
        )

        metadata = {
            "task": args_cli.task,
            "trajectory_path": str(trajectory_path),
            "trajectory_format": trajectory.get("format"),
            "trajectory_total_frames": len(frames),
            "render_stride": render_stride,
            "sim_steps_per_frame": sim_steps_per_frame,
            "settle_steps": int(args_cli.settle_steps),
            "rendered_frames": len(composite_frames),
            "fps": int(args_cli.fps),
            "joint_names": planned_names,
            "object_records": object_records,
            "object_pose_mode": (
                "dynamic_rigidbody_contact_replay" if dynamic_replay else "kinematic_follow_link6_after_arm_attach_frame"
            ),
            "dynamic_replay": dynamic_replay,
            "render_sync": {
                "warmup_render_updates": int(args_cli.warmup_render_updates),
                "render_sync_updates": int(args_cli.render_sync_updates),
                "force_camera_recompute": bool(args_cli.force_camera_recompute),
            },
            "dynamic_summary": _summarize_object_trace(
                object_trace=object_trace,
                object_records=object_records,
                dynamic_replay=dynamic_replay,
            ),
            "visual_motion_diagnostics": visual_motion,
            "object_trace": object_trace,
            "camera_parent_paths": {
                "top_cam": base_path,
                "left_cam": left_wrist_path,
                "right_cam": right_wrist_path,
            },
            "sample_stats": sample_stats,
            "videos": video_paths,
            "ffprobe": {name: _ffprobe(Path(path)) for name, path in video_paths.items()},
            "readiness": trajectory.get("readiness", {}),
        }
        _write_json(output_dir / "metadata.json", metadata)
        _log(f"composite video: {composite_path}")
        _log(f"metadata: {output_dir / 'metadata.json'}")
        if bool(args_cli.fail_on_static_visual) and bool(args_cli.visual_motion_check) and not bool(
            visual_motion.get("passed", False)
        ):
            raise RuntimeError(f"Visual motion check failed: {visual_motion}")
    finally:
        env.close()


if __name__ == "__main__":
    try:
        try:
            main()
        except BaseException as exc:
            _log(f"failed with {type(exc).__name__}: {exc!r}")
            traceback.print_exc()
            raise
    finally:
        simulation_app.close()
