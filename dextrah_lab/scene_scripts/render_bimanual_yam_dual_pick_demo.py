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
    parser.add_argument("--disable_fabric", action="store_true")
    parser.add_argument("--video_crf", type=int, default=18)
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
    eye = (-1.22, -0.98, 0.78)
    target = (-0.30, 0.0, 0.16)
    cfg = CameraCfg(
        prim_path="/World/BimanualYamDualPickOverviewCamera",
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=20.0,
            horizontal_aperture=20.955,
            clipping_range=(0.01, 20.0),
        ),
        offset=CameraCfg.OffsetCfg(pos=eye, rot=_look_at_quat_world(eye, target), convention="world"),
    )
    return Camera(cfg)


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


def _root_state(device: torch.device, pos: list[float], quat_wxyz: list[float] | None = None) -> torch.Tensor:
    quat = quat_wxyz or [1.0, 0.0, 0.0, 0.0]
    state = torch.zeros((1, 13), dtype=torch.float32, device=device)
    state[0, 0:3] = torch.tensor(pos, dtype=torch.float32, device=device)
    state[0, 3:7] = torch.tensor(quat, dtype=torch.float32, device=device)
    return state


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


def _spawn_right_object(object_record: dict[str, Any]) -> RigidObject:
    dims = tuple(float(v) for v in object_record["dims"])
    center = tuple(float(v) for v in object_record["bimanual_center_world"])
    cfg = RigidObjectCfg(
        prim_path="/World/envs/env_0/RightObject",
        spawn=sim_utils.CuboidCfg(
            size=dims,
            collision_props=sim_utils.CollisionPropertiesCfg(collision_enabled=True, contact_offset=0.002),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=True,
                disable_gravity=True,
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=4,
            ),
            mass_props=sim_utils.MassPropertiesCfg(density=40.0),
            physics_material=RigidBodyMaterialCfg(static_friction=1.4, dynamic_friction=1.1, restitution=0.0),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.20, 0.78, 0.45), roughness=0.65),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=center, rot=(1.0, 0.0, 0.0, 0.0)),
    )
    return RigidObject(cfg)


def _configure_env_for_left_object(env_cfg: Any, left_record: dict[str, Any]) -> None:
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
    env_cfg.cube.spawn.rigid_props.kinematic_enabled = True
    env_cfg.cube.spawn.rigid_props.disable_gravity = True
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
    _configure_env_for_left_object(env_cfg, object_records["left"])

    _log("creating Gym environment")
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    task_env = env.unwrapped
    try:
        env.reset(seed=args_cli.seed)
        robot = task_env._robot
        left_object = task_env._cube
        right_object = _spawn_right_object(object_records["right"])
        task_env.scene.rigid_objects["right_object"] = right_object

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
        left_body_id = int(robot.find_bodies("left_link_6")[0][0])
        right_body_id = int(robot.find_bodies("right_link_6")[0][0])

        dt = float(getattr(task_env, "step_dt", task_env.cfg.sim.dt))
        render_stride = max(1, int(args_cli.render_stride))
        video_frames: dict[str, list[np.ndarray]] = {name: [] for name in cameras}
        composite_frames: list[np.ndarray] = []
        sample_stats: dict[str, dict[str, dict[str, float]]] = {}
        object_trace: list[dict[str, Any]] = []

        for source_frame_idx in range(0, len(frames), render_stride):
            frame = frames[source_frame_idx]
            joint_pos = robot.data.default_joint_pos.clone()
            joint_vel = torch.zeros_like(joint_pos)
            q = torch.tensor(frame["joint_position"], dtype=torch.float32, device=robot.device)
            joint_pos[:, planned_ids] = q.unsqueeze(0)
            robot.write_joint_state_to_sim(joint_pos, joint_vel)
            robot.set_joint_position_target(joint_pos)
            robot.write_data_to_sim()
            robot.update(dt)

            left_pos = _object_position_for_frame(
                robot=robot,
                body_id=left_body_id,
                frame_idx=source_frame_idx,
                object_record=object_records["left"],
            )
            right_pos = _object_position_for_frame(
                robot=robot,
                body_id=right_body_id,
                frame_idx=source_frame_idx,
                object_record=object_records["right"],
            )
            left_object.write_root_state_to_sim(_root_state(left_object.device, left_pos))
            right_object.write_root_state_to_sim(_root_state(right_object.device, right_pos))
            left_object.update(dt)
            right_object.update(dt)

            for _ in range(max(1, int(args_cli.sim_steps_per_frame))):
                task_env.sim.step(render=False)
            task_env.sim.render()
            robot.update(dt)
            left_object.update(dt)
            right_object.update(dt)

            frame_images: dict[str, np.ndarray] = {}
            for name, camera in cameras.items():
                camera.update(dt)
                rgb = _rgb_to_array(camera.data.output["rgb"])
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

        metadata = {
            "task": args_cli.task,
            "trajectory_path": str(trajectory_path),
            "trajectory_format": trajectory.get("format"),
            "trajectory_total_frames": len(frames),
            "render_stride": render_stride,
            "rendered_frames": len(composite_frames),
            "fps": int(args_cli.fps),
            "joint_names": planned_names,
            "object_records": object_records,
            "object_pose_mode": "kinematic_follow_link6_after_arm_attach_frame",
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
