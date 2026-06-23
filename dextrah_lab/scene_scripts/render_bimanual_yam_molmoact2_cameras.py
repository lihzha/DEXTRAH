#!/usr/bin/env python3
"""Render the bimanual YAM MolmoAct2 camera setup in Isaac Lab.

The script creates one overview camera plus the three MolmoAct2 policy cameras:
top_cam, left_cam, and right_cam.  Policy camera intrinsics and mount poses are
pulled from the shared bimanual YAM asset constants so this is a direct render
check of the environment configuration.
"""

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
    print(f"[bimanual-yam-viz] {message}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=str, default="Dextrah-Bimanual-YAM-Cube-Grasp")
    parser.add_argument("--num_envs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_dir", type=Path, default=None)
    parser.add_argument("--frames", type=int, default=48)
    parser.add_argument("--fps", type=int, default=12)
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

_log("importing Isaac Lab camera/task modules")
import isaaclab.sim as sim_utils  # noqa: E402
import isaaclab_tasks  # noqa: F401,E402
from isaaclab.sensors.camera import Camera, CameraCfg  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

_log("importing DEXTRAH task and MolmoAct2 constants")
import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup  # noqa: F401,E402
from dextrah_lab.assets.yam.bimanual_yam import (  # noqa: E402
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_CAMERA_ORDER,
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_TOP_CAMERA_INTRINSIC,
    MOLMOACT2_TOP_CAMERA_LOCAL_POS,
    MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ,
    MOLMOACT2_TOP_CAMERA_PARENT_BODY,
    MOLMOACT2_TOP_CAMERA_VFOV_DEG,
    MOLMOACT2_WRIST_CAMERA_INTRINSIC,
    MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
    MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
    MOLMOACT2_WRIST_CAMERA_VFOV_DEG,
)


def _normalize_vec(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:
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
    """Return a world-convention camera quaternion (+X forward, +Z up)."""

    eye_np = np.asarray(eye, dtype=np.float64)
    target_np = np.asarray(target, dtype=np.float64)
    forward = _normalize_vec(target_np - eye_np)
    up_hint = _normalize_vec(np.asarray(up, dtype=np.float64))
    right = np.cross(up_hint, forward)
    if np.linalg.norm(right) < 1e-6:
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
    prim_path = f"{parent_path}/{name}_render_sensor"
    cfg = CameraCfg(
        prim_path=prim_path,
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=_spawn_from_intrinsic(intrinsic),
        offset=CameraCfg.OffsetCfg(pos=pos, rot=quat, convention="opengl"),
    )
    return Camera(cfg)


def _make_overview_camera() -> Camera:
    eye = (-1.25, -0.95, 0.78)
    target = (-0.36, 0.0, 0.18)
    quat = _look_at_quat_world(eye, target)
    cfg = CameraCfg(
        prim_path="/World/BimanualYamOverviewCamera",
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=20.0,
            horizontal_aperture=20.955,
            clipping_range=(0.01, 20.0),
        ),
        offset=CameraCfg.OffsetCfg(pos=eye, rot=quat, convention="world"),
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


def _save_png(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path)


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


def _intrinsic_matrix(camera: Camera) -> list[float]:
    matrix = camera.data.intrinsic_matrices[0].detach().cpu().numpy()
    return [float(x) for x in matrix.reshape(-1)]


def _max_abs_err(actual: list[float], expected: tuple[float, ...]) -> float:
    return float(np.max(np.abs(np.asarray(actual, dtype=np.float64) - np.asarray(expected, dtype=np.float64))))


def _image_stats(array: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


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


def main() -> None:
    if args_cli.num_envs != 1:
        raise ValueError("This visualization script expects --num_envs 1 so camera paths are unambiguous.")
    if args_cli.frames <= 0:
        raise ValueError("--frames must be positive")
    if args_cli.fps <= 0:
        raise ValueError("--fps must be positive")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args_cli.output_dir or Path("runs") / "bimanual_yam_molmoact2_camera_viz" / timestamp
    output_dir = output_dir.resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"writing artifacts to {output_dir}")

    _log("parsing environment config")
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    _log("creating Gym environment")
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    task_env = env.unwrapped

    try:
        _log("resetting environment")
        env.reset(seed=args_cli.seed)
        stage = omni.usd.get_context().get_stage()
        base_path = _find_body_prim_path(stage, MOLMOACT2_TOP_CAMERA_PARENT_BODY)
        left_wrist_path = _find_body_prim_path(stage, MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY)
        right_wrist_path = _find_body_prim_path(stage, MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY)
        _log(f"camera parents: top={base_path}, left={left_wrist_path}, right={right_wrist_path}")

        _log("creating camera sensors")
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

        _log("resetting simulation after camera creation")
        task_env.sim.reset()
        env.reset(seed=args_cli.seed)
        zero_action = torch.zeros((1, task_env.cfg.action_space), device=task_env.device)
        dt = float(getattr(task_env, "step_dt", task_env.cfg.sim.dt))

        for _ in range(4):
            task_env.sim.render()
            for camera in cameras.values():
                camera.update(dt)

        actual_intrinsics = {
            "top_cam": _intrinsic_matrix(cameras["top_cam"]),
            "left_cam": _intrinsic_matrix(cameras["left_cam"]),
            "right_cam": _intrinsic_matrix(cameras["right_cam"]),
        }
        intrinsic_errors = {
            "top_cam": _max_abs_err(actual_intrinsics["top_cam"], MOLMOACT2_TOP_CAMERA_INTRINSIC),
            "left_cam": _max_abs_err(actual_intrinsics["left_cam"], MOLMOACT2_WRIST_CAMERA_INTRINSIC),
            "right_cam": _max_abs_err(actual_intrinsics["right_cam"], MOLMOACT2_WRIST_CAMERA_INTRINSIC),
        }
        if max(intrinsic_errors.values()) > 1e-3:
            raise RuntimeError(f"Camera intrinsic mismatch: {intrinsic_errors}")

        videos: dict[str, list[np.ndarray]] = {name: [] for name in cameras}
        composite_frames: list[np.ndarray] = []
        sample_stats: dict[str, dict[str, dict[str, float]]] = {}

        for frame_idx in range(args_cli.frames):
            if frame_idx > 0:
                for _ in range(max(1, args_cli.sim_steps_per_frame)):
                    env.step(zero_action)
            task_env.sim.render()
            frame_images: dict[str, np.ndarray] = {}
            for name, camera in cameras.items():
                camera.update(dt)
                rgb = _rgb_to_array(camera.data.output["rgb"])
                frame_images[name] = rgb
                videos[name].append(rgb)
                _save_png(frames_dir / name / f"{frame_idx:04d}.png", rgb)
            composite = _make_composite(frame_images)
            composite_frames.append(composite)
            _save_png(frames_dir / "composite" / f"{frame_idx:04d}.png", composite)

            if frame_idx in {0, args_cli.frames // 2, args_cli.frames - 1}:
                sample_stats[str(frame_idx)] = {name: _image_stats(image) for name, image in frame_images.items()}

        video_paths: dict[str, str] = {}
        for name, frames in videos.items():
            video_path = output_dir / f"{name}.mp4"
            _write_video(video_path, frames, args_cli.fps, args_cli.video_crf)
            video_paths[name] = str(video_path)
        composite_path = output_dir / "bimanual_yam_molmoact2_cameras_composite.mp4"
        _write_video(composite_path, composite_frames, args_cli.fps, args_cli.video_crf)
        video_paths["composite"] = str(composite_path)

        metadata = {
            "task": args_cli.task,
            "frames": args_cli.frames,
            "fps": args_cli.fps,
            "camera_order": list(MOLMOACT2_CAMERA_ORDER),
            "resolution": [MOLMOACT2_CAMERA_WIDTH, MOLMOACT2_CAMERA_HEIGHT],
            "reference": {
                "top_cam": {
                    "parent_body": MOLMOACT2_TOP_CAMERA_PARENT_BODY,
                    "local_pos": list(MOLMOACT2_TOP_CAMERA_LOCAL_POS),
                    "local_quat_wxyz": list(MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ),
                    "convention": "opengl",
                    "vfov_deg": MOLMOACT2_TOP_CAMERA_VFOV_DEG,
                    "intrinsic_row_major": list(MOLMOACT2_TOP_CAMERA_INTRINSIC),
                },
                "left_cam": {
                    "parent_body": MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY,
                    "local_pos": list(MOLMOACT2_WRIST_CAMERA_LOCAL_POS),
                    "local_quat_wxyz": list(MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ),
                    "convention": "opengl",
                    "vfov_deg": MOLMOACT2_WRIST_CAMERA_VFOV_DEG,
                    "intrinsic_row_major": list(MOLMOACT2_WRIST_CAMERA_INTRINSIC),
                },
                "right_cam": {
                    "parent_body": MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY,
                    "local_pos": list(MOLMOACT2_WRIST_CAMERA_LOCAL_POS),
                    "local_quat_wxyz": list(MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ),
                    "convention": "opengl",
                    "vfov_deg": MOLMOACT2_WRIST_CAMERA_VFOV_DEG,
                    "intrinsic_row_major": list(MOLMOACT2_WRIST_CAMERA_INTRINSIC),
                },
            },
            "resolved_parent_paths": {
                "top_cam": base_path,
                "left_cam": left_wrist_path,
                "right_cam": right_wrist_path,
            },
            "actual_intrinsics_row_major": actual_intrinsics,
            "intrinsic_max_abs_error": intrinsic_errors,
            "sample_stats": sample_stats,
            "videos": video_paths,
            "ffprobe": {name: _ffprobe(Path(path)) for name, path in video_paths.items()},
        }
        with (output_dir / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
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
