#!/usr/bin/env python3
"""Render a RoboLab USD scene through DEXTRAH's Isaac Lab renderer.

The default output is a constant-speed 360 degree orbit video. The camera stays
above the scene and continuously looks at the detected table center. If no table
prim can be detected, the orbit target falls back to the referenced scene's
bounding-box center.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

from isaaclab.app import AppLauncher


def _float3(value: str) -> tuple[float, float, float]:
    parts = [float(v) for v in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("expected comma-separated x,y,z")
    return (parts[0], parts[1], parts[2])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", default="banana_bowl.usda", help="RoboLab scene filename, relative path, or absolute USD path.")
    parser.add_argument("--robolab_root", type=Path, default=None, help="Optional RoboLab checkout/package root.")
    parser.add_argument("--robolab_scene_dir", type=Path, default=None, help="Optional directory containing RoboLab scenes.")
    parser.add_argument("--output_dir", type=Path, default=Path("/tmp/dextrah_robolab_scene"))
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--video_seconds", type=float, default=6.0)
    parser.add_argument("--sim_steps_per_frame", type=int, default=1)
    parser.add_argument("--sim_dt", type=float, default=1.0 / 120.0)
    parser.add_argument("--settle_steps", type=int, default=12)
    parser.add_argument("--warmup_frames", type=int, default=8)
    parser.add_argument("--rt_subframes", type=int, default=4)
    parser.add_argument("--physics_device", default="cuda:0")
    parser.add_argument("--scene_translation", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--scene_rotation_deg", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--scene_scale", type=float, default=1.0)
    parser.add_argument("--orbit_radius", type=float, default=None, help="Camera orbit radius in meters. Defaults from scene bounds.")
    parser.add_argument("--orbit_elevation_deg", type=float, default=45.0, help="Camera elevation above the horizontal orbit plane.")
    parser.add_argument("--orbit_height", type=float, default=None, help="Optional direct camera height above target z.")
    parser.add_argument("--orbit_start_deg", type=float, default=35.0)
    parser.add_argument("--orbit_target", type=_float3, default=None, help="Optional explicit target x,y,z.")
    parser.add_argument("--target_z_offset", type=float, default=0.05, help="Added to detected table-top target z.")
    parser.add_argument(
        "--target_source",
        choices=("table", "scene_bbox", "origin", "custom"),
        default="table",
        help="How to pick the orbit look-at target when --orbit_target is not set.",
    )
    parser.add_argument("--camera_focal_length", type=float, default=22.0)
    parser.add_argument("--horizontal_aperture", type=float, default=20.955)
    parser.add_argument(
        "--capture_backend",
        choices=("sensor", "viewport", "tiled"),
        default="sensor",
        help="Sensor capture avoids SimulationContext.reset/render stalls on imported static USD scenes.",
    )
    parser.add_argument("--dome_intensity", type=float, default=750.0)
    parser.add_argument("--sun_intensity", type=float, default=1800.0)
    parser.add_argument("--randomize_lighting", action="store_true")
    parser.add_argument("--robot", choices=("none", "kuka_allegro"), default="none")
    parser.add_argument("--robot_translation", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--robot_rotation_deg", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--encode_video", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--export_usd", action=argparse.BooleanOptionalAction, default=True)
    AppLauncher.add_app_launcher_args(parser)
    return parser.parse_args()


args_cli = parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import omni.usd  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.sensors.camera import TiledCamera, TiledCameraCfg  # noqa: E402
from isaaclab.sim import PhysxCfg, SimulationCfg  # noqa: E402
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg  # noqa: E402
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics  # noqa: E402

try:
    from isaacsim.core.utils.stage import create_new_stage, update_stage
except Exception:
    from omni.isaac.core.utils.stage import create_new_stage, update_stage  # type: ignore

from dextrah_lab.robolab_bridge import resolve_robolab_scene  # noqa: E402


def _log(message: str) -> None:
    print(f"[robolab-render] {message}", flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_git_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(128).startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _set_xform(
    prim: Usd.Prim,
    translate: Iterable[float],
    scale: Iterable[float] | None = None,
    rotate_xyz_deg: Iterable[float] | None = None,
) -> None:
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in translate]))
    if rotate_xyz_deg is not None:
        xformable.AddRotateXYZOp().Set(Gf.Vec3f(*[float(v) for v in rotate_xyz_deg]))
    if scale is not None:
        xformable.AddScaleOp().Set(Gf.Vec3f(*[float(v) for v in scale]))


def _create_sim_context():
    _log(f"creating SimulationContext on physics_device={args_cli.physics_device}")
    sim_cfg = SimulationCfg(
        dt=float(args_cli.sim_dt),
        render_interval=1,
        device=str(args_cli.physics_device),
        physics_prim_path="/World/physicsScene",
        physics_material=RigidBodyMaterialCfg(static_friction=1.0, dynamic_friction=1.0),
        physx=PhysxCfg(
            bounce_threshold_velocity=0.2,
            gpu_max_rigid_patch_count=4 * 5 * 2**15,
        ),
    )
    return sim_utils.SimulationContext(sim_cfg)


def _add_physics_scene(stage: Usd.Stage) -> None:
    scene = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(9.81)


def _add_lighting(stage: Usd.Stage, *, rng: random.Random) -> dict[str, float]:
    dome_intensity = float(args_cli.dome_intensity)
    sun_intensity = float(args_cli.sun_intensity)
    sun_angle = 35.0
    sun_yaw = -35.0
    if args_cli.randomize_lighting:
        dome_intensity *= rng.uniform(0.75, 1.25)
        sun_intensity *= rng.uniform(0.65, 1.35)
        sun_angle += rng.uniform(-10.0, 10.0)
        sun_yaw += rng.uniform(-45.0, 45.0)

    dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
    dome.CreateIntensityAttr(dome_intensity)
    dome.CreateExposureAttr(0.0)

    sun = UsdLux.DistantLight.Define(stage, "/World/SunLight")
    sun.CreateIntensityAttr(sun_intensity)
    sun.CreateAngleAttr(0.35)
    _set_xform(sun.GetPrim(), (0.0, 0.0, 0.0), rotate_xyz_deg=(sun_angle, 0.0, sun_yaw))
    return {
        "dome_intensity": dome_intensity,
        "sun_intensity": sun_intensity,
        "sun_angle_deg": sun_angle,
        "sun_yaw_deg": sun_yaw,
    }


def _create_robot(stage: Usd.Stage) -> str | None:
    if args_cli.robot == "none":
        return None
    robot_usd = _repo_root() / "dextrah_lab/assets/kuka_allegro/kuka_allegro_colored.usd"
    if not robot_usd.exists():
        raise FileNotFoundError(f"Robot USD is missing: {robot_usd}")
    if _is_git_lfs_pointer(robot_usd):
        raise RuntimeError(f"Robot USD is still a Git LFS pointer, run git lfs pull: {robot_usd}")
    robot = UsdGeom.Xform.Define(stage, "/World/Robot").GetPrim()
    robot.GetReferences().AddReference(str(robot_usd))
    _set_xform(robot, args_cli.robot_translation, rotate_xyz_deg=args_cli.robot_rotation_deg)
    return str(robot_usd)


def _reference_robolab_scene(stage: Usd.Stage, scene_path: Path) -> Usd.Prim:
    scene_root = UsdGeom.Xform.Define(stage, "/World/RoboLabScene").GetPrim()
    scene_root.GetReferences().AddReference(str(scene_path))
    scale = float(args_cli.scene_scale)
    _set_xform(
        scene_root,
        args_cli.scene_translation,
        scale=(scale, scale, scale),
        rotate_xyz_deg=args_cli.scene_rotation_deg,
    )
    return scene_root


def _range_to_dict(range3d: Gf.Range3d) -> dict[str, Any]:
    min_v = range3d.GetMin()
    max_v = range3d.GetMax()
    center = range3d.GetMidpoint()
    size = max_v - min_v
    return {
        "min": [float(min_v[0]), float(min_v[1]), float(min_v[2])],
        "max": [float(max_v[0]), float(max_v[1]), float(max_v[2])],
        "center": [float(center[0]), float(center[1]), float(center[2])],
        "size": [float(size[0]), float(size[1]), float(size[2])],
    }


def _compute_bbox(stage: Usd.Stage, prim: Usd.Prim) -> Gf.Range3d:
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy])
    bbox = cache.ComputeWorldBound(prim).ComputeAlignedBox()
    if bbox.IsEmpty():
        raise RuntimeError(f"Could not compute non-empty bounds for {prim.GetPath()}")
    return bbox


def _find_table_bbox(stage: Usd.Stage, scene_root: Usd.Prim) -> Gf.Range3d | None:
    table_prims: list[Usd.Prim] = []
    for prim in Usd.PrimRange(scene_root):
        path_text = str(prim.GetPath()).lower()
        name_text = prim.GetName().lower()
        if ("table" in path_text or name_text in {"workbench", "counter", "countertop", "desk"}) and prim.IsA(
            UsdGeom.Imageable
        ):
            table_prims.append(prim)

    if not table_prims:
        return None

    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy])
    merged = Gf.Range3d()
    used = 0
    for prim in table_prims:
        bbox = cache.ComputeWorldBound(prim).ComputeAlignedBox()
        if not bbox.IsEmpty():
            merged.UnionWith(bbox)
            used += 1
    if used == 0 or merged.IsEmpty():
        return None
    return merged


def _target_from_bounds(stage: Usd.Stage, scene_root: Usd.Prim, scene_bbox: Gf.Range3d) -> tuple[tuple[float, float, float], str, dict[str, Any] | None]:
    if args_cli.orbit_target is not None:
        return tuple(args_cli.orbit_target), "custom", None
    if args_cli.target_source == "custom":
        raise ValueError("--target_source custom requires --orbit_target x,y,z")
    if args_cli.target_source == "origin":
        return (0.0, 0.0, 0.0), "origin", None
    if args_cli.target_source == "scene_bbox":
        center = scene_bbox.GetMidpoint()
        return (float(center[0]), float(center[1]), float(center[2])), "scene_bbox", _range_to_dict(scene_bbox)

    table_bbox = _find_table_bbox(stage, scene_root)
    if table_bbox is not None:
        center = table_bbox.GetMidpoint()
        max_v = table_bbox.GetMax()
        target = (float(center[0]), float(center[1]), float(max_v[2] + float(args_cli.target_z_offset)))
        return target, "table", _range_to_dict(table_bbox)

    center = scene_bbox.GetMidpoint()
    return (float(center[0]), float(center[1]), float(center[2])), "scene_bbox_fallback", _range_to_dict(scene_bbox)


def _orbit_radius_and_height(scene_bbox: Gf.Range3d, target: tuple[float, float, float]) -> tuple[float, float]:
    size = scene_bbox.GetSize()
    xy_extent = max(float(size[0]), float(size[1]), 0.75)
    radius = float(args_cli.orbit_radius) if args_cli.orbit_radius is not None else max(1.0, xy_extent * 1.35)
    if args_cli.orbit_height is not None:
        height = float(args_cli.orbit_height)
    else:
        elevation = math.radians(float(args_cli.orbit_elevation_deg))
        height = radius * math.tan(elevation)
    height = max(0.25, height)
    return radius, height


def _normalize_vec(vec: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1.0e-12:
        raise ValueError(f"Cannot normalize near-zero vector: {vec}")
    return (vec[0] / norm, vec[1] / norm, vec[2] / norm)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _quat_from_matrix(
    x_axis: tuple[float, float, float],
    y_axis: tuple[float, float, float],
    z_axis: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    m00, m01, m02 = x_axis[0], y_axis[0], z_axis[0]
    m10, m11, m12 = x_axis[1], y_axis[1], z_axis[1]
    m20, m21, m22 = x_axis[2], y_axis[2], z_axis[2]
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        return (0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s)
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return ((m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s)
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return ((m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s)
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
    return ((m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s)


def _look_at_quat_world(
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    # Isaac Lab's "world" camera convention uses +X forward and +Z up.
    forward = _normalize_vec((target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]))
    up_ref = (0.0, 0.0, 1.0)
    if abs(sum(forward[i] * up_ref[i] for i in range(3))) > 0.985:
        up_ref = (0.0, 1.0, 0.0)
    y_axis = _normalize_vec(_cross(up_ref, forward))
    z_axis = _normalize_vec(_cross(forward, y_axis))
    return _quat_from_matrix(forward, y_axis, z_axis)


def _get_or_add_xform_op(
    xformable: UsdGeom.Xformable,
    op_name: str,
    add_fn,
) -> UsdGeom.XformOp:
    attr = xformable.GetPrim().GetAttribute(f"xformOp:{op_name}")
    if attr.IsValid():
        return UsdGeom.XformOp(attr)
    return add_fn()


def _set_camera_pose(
    camera_prim: Usd.Prim,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    quat = _look_at_quat_world(eye, target)
    xformable = UsdGeom.Xformable(camera_prim)
    translate_op = _get_or_add_xform_op(
        xformable,
        "translate",
        lambda: xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble),
    )
    orient_op = _get_or_add_xform_op(
        xformable,
        "orient",
        lambda: xformable.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble),
    )
    if translate_op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
        translate_op.Set(Gf.Vec3f(float(eye[0]), float(eye[1]), float(eye[2])))
    else:
        translate_op.Set(Gf.Vec3d(float(eye[0]), float(eye[1]), float(eye[2])))
    if orient_op.GetPrecision() == UsdGeom.XformOp.PrecisionFloat:
        orient_op.Set(Gf.Quatf(float(quat[0]), Gf.Vec3f(float(quat[1]), float(quat[2]), float(quat[3]))))
    else:
        orient_op.Set(Gf.Quatd(float(quat[0]), Gf.Vec3d(float(quat[1]), float(quat[2]), float(quat[3]))))
    xformable.SetXformOpOrder([translate_op, orient_op])
    return quat


def _initialize_tiled_camera_sensor(camera: TiledCamera) -> None:
    if camera.is_initialized:
        camera.reset()
        return
    _log("initializing orbit TiledCamera sensor without SimulationContext reset")
    camera._initialize_impl()
    camera._is_initialized = True
    camera.reset()


def _set_sensor_camera_view(
    camera: TiledCamera,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    import torch

    eyes = torch.tensor([eye], dtype=torch.float32, device=camera.device)
    targets = torch.tensor([target], dtype=torch.float32, device=camera.device)
    camera.set_world_poses_from_view(eyes=eyes, targets=targets)
    return _look_at_quat_world(eye, target)


def _save_rgb_tensor(path: Path, rgb_tensor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = rgb_tensor.detach().cpu().numpy()
    try:
        from PIL import Image

        Image.fromarray(rgb).save(path)
    except Exception:
        from torchvision.utils import save_image
        import torch

        image = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        save_image(image, str(path))


def _set_view(eye: tuple[float, float, float], target: tuple[float, float, float]):
    try:
        from isaacsim.core.utils.viewports import set_camera_view
    except Exception:
        from omni.isaac.core.utils.viewports import set_camera_view  # type: ignore
    from omni.kit.viewport.utility import get_active_viewport

    try:
        set_camera_view(eye=list(eye), target=list(target))
    except TypeError:
        set_camera_view(list(eye), list(target))

    viewport = get_active_viewport()
    if viewport is None:
        raise RuntimeError("No active viewport available for capture")
    return viewport


def _capture_viewport_png(viewport, dst: Path, *, deadline_seconds: float = 120.0) -> Path:
    from omni.kit.viewport.utility import capture_viewport_to_file, next_viewport_frame_async

    dst.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        simulation_app.update()

    async def _wait_for_capture() -> None:
        await next_viewport_frame_async(viewport, n_frames=max(1, int(args_cli.rt_subframes)))
        capture = capture_viewport_to_file(viewport, file_path=str(dst))
        await capture.wait_for_result(completion_frames=max(8, int(args_cli.rt_subframes)))

    loop = asyncio.get_event_loop()
    task = loop.create_task(_wait_for_capture())
    deadline = time.time() + float(deadline_seconds)
    while not task.done() and time.time() < deadline:
        simulation_app.update()
        loop.run_until_complete(asyncio.sleep(0.0))
    if not task.done():
        task.cancel()
        loop.run_until_complete(asyncio.sleep(0.0))
        raise TimeoutError(f"Timed out while capturing viewport image {dst}")
    task.result()

    if not dst.exists():
        raise RuntimeError(f"Viewport capture did not write {dst}")

    return dst


def _encode_video(frames_dir: Path, video_path: Path, fps: int) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return {"status": "skipped", "reason": "ffmpeg_not_found", "path": str(video_path)}
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(int(fps)),
        "-i",
        str(frames_dir / "orbit_%04d.png"),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(video_path),
    ]
    _log("encoding orbit video with ffmpeg")
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    result = {
        "status": "passed" if proc.returncode == 0 and video_path.exists() else "failed",
        "returncode": proc.returncode,
        "cmd": cmd,
        "path": str(video_path),
    }
    if proc.stdout:
        result["stdout"] = proc.stdout
    if proc.stderr:
        result["stderr"] = proc.stderr
    return result


def _capture_orbit_viewport(
    *,
    target: tuple[float, float, float],
    radius: float,
    height: float,
    output_dir: Path,
) -> tuple[list[str], dict[str, Any]]:
    frame_count = max(2, int(round(float(args_cli.fps) * float(args_cli.video_seconds))))
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("orbit_*.png"):
        stale.unlink()

    frames: list[str] = []
    poses: list[dict[str, Any]] = []
    start = math.radians(float(args_cli.orbit_start_deg))

    _log(f"capturing orbit frames with viewport backend: {frame_count} frames at {args_cli.fps} fps")
    for frame_idx in range(frame_count):
        theta = start + (2.0 * math.pi * frame_idx / frame_count)
        eye = (
            target[0] + radius * math.cos(theta),
            target[1] + radius * math.sin(theta),
            target[2] + height,
        )
        quat = _look_at_quat_world(eye, target)
        viewport = _set_view(eye, target)
        dst = frames_dir / f"orbit_{frame_idx:04d}.png"
        _log(f"capturing orbit frame {frame_idx + 1}/{frame_count}")
        _capture_viewport_png(viewport, dst)
        frames.append(str(dst))
        poses.append(
            {
                "frame": frame_idx,
                "theta_deg": math.degrees(theta),
                "eye": [float(v) for v in eye],
                "target": [float(v) for v in target],
                "quat_wxyz": [float(v) for v in quat],
            }
        )

    return frames, {"frame_count": frame_count, "frames_dir": str(frames_dir), "camera_poses": poses}


def _capture_orbit_sensor(
    *,
    target: tuple[float, float, float],
    radius: float,
    height: float,
    scene_bbox: Gf.Range3d,
    output_dir: Path,
) -> tuple[list[str], dict[str, Any]]:
    frame_count = max(2, int(round(float(args_cli.fps) * float(args_cli.video_seconds))))
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("orbit_*.png"):
        stale.unlink()

    start = math.radians(float(args_cli.orbit_start_deg))
    first_eye = (
        target[0] + radius * math.cos(start),
        target[1] + radius * math.sin(start),
        target[2] + height,
    )
    first_quat = _look_at_quat_world(first_eye, target)
    scene_size = scene_bbox.GetSize()
    scene_extent = max(float(scene_size[0]), float(scene_size[1]), float(scene_size[2]))
    clipping_far = max(10.0, 4.0 * max(radius, height, scene_extent))
    camera_cfg = TiledCameraCfg(
        prim_path="/World/OrbitCamera",
        offset=TiledCameraCfg.OffsetCfg(pos=first_eye, rot=first_quat, convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=float(args_cli.camera_focal_length),
            focus_distance=400.0,
            horizontal_aperture=float(args_cli.horizontal_aperture),
            clipping_range=(0.03, float(clipping_far)),
        ),
        width=int(args_cli.width),
        height=int(args_cli.height),
        update_period=0,
    )

    _log("creating orbit TiledCamera for no-reset sensor capture")
    camera = TiledCamera(camera_cfg)
    for _ in range(max(2, int(args_cli.rt_subframes))):
        simulation_app.update()
    _initialize_tiled_camera_sensor(camera)

    camera_prim = omni.usd.get_context().get_stage().GetPrimAtPath("/World/OrbitCamera")
    if not camera_prim.IsValid():
        raise RuntimeError("Orbit camera prim was not created")

    frames: list[str] = []
    poses: list[dict[str, Any]] = []
    _log(f"capturing orbit frames with sensor backend: {frame_count} frames at {args_cli.fps} fps")
    for frame_idx in range(frame_count):
        theta = start + (2.0 * math.pi * frame_idx / frame_count)
        eye = (
            target[0] + radius * math.cos(theta),
            target[1] + radius * math.sin(theta),
            target[2] + height,
        )
        quat = _set_sensor_camera_view(camera, eye, target)
        for _ in range(max(2, int(args_cli.rt_subframes))):
            simulation_app.update()
        camera.update(0.0, force_recompute=True)
        dst = frames_dir / f"orbit_{frame_idx:04d}.png"
        _log(f"capturing orbit frame {frame_idx + 1}/{frame_count}")
        _save_rgb_tensor(dst, camera.data.output["rgb"][0])
        frames.append(str(dst))
        poses.append(
            {
                "frame": frame_idx,
                "theta_deg": math.degrees(theta),
                "eye": [float(v) for v in eye],
                "target": [float(v) for v in target],
                "quat_wxyz": [float(v) for v in quat],
            }
        )

    del camera
    return frames, {"frame_count": frame_count, "frames_dir": str(frames_dir), "camera_poses": poses}


def _capture_orbit_video(
    *,
    sim,
    target: tuple[float, float, float],
    radius: float,
    height: float,
    scene_bbox: Gf.Range3d,
    output_dir: Path,
) -> tuple[list[str], dict[str, Any]]:
    frame_count = max(2, int(round(float(args_cli.fps) * float(args_cli.video_seconds))))
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("orbit_*.png"):
        stale.unlink()

    start = math.radians(float(args_cli.orbit_start_deg))
    first_eye = (
        target[0] + radius * math.cos(start),
        target[1] + radius * math.sin(start),
        target[2] + height,
    )
    first_quat = _look_at_quat_world(first_eye, target)
    scene_size = scene_bbox.GetSize()
    scene_extent = max(float(scene_size[0]), float(scene_size[1]), float(scene_size[2]))
    clipping_far = max(10.0, 4.0 * max(radius, height, scene_extent))
    camera_cfg = TiledCameraCfg(
        prim_path="/World/OrbitCamera",
        offset=TiledCameraCfg.OffsetCfg(pos=first_eye, rot=first_quat, convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=float(args_cli.camera_focal_length),
            focus_distance=400.0,
            horizontal_aperture=float(args_cli.horizontal_aperture),
            clipping_range=(0.03, float(clipping_far)),
        ),
        width=int(args_cli.width),
        height=int(args_cli.height),
        update_period=0,
    )

    _log("creating orbit TiledCamera")
    camera = TiledCamera(camera_cfg)
    _log("resetting SimulationContext after camera creation")
    sim.reset()

    for _ in range(max(0, int(args_cli.settle_steps))):
        sim.step(render=False)
    for _ in range(max(0, int(args_cli.warmup_frames))):
        sim.render()
        camera.update(float(sim.cfg.dt))

    camera_prim = omni.usd.get_context().get_stage().GetPrimAtPath("/World/OrbitCamera")
    if not camera_prim.IsValid():
        raise RuntimeError("Orbit camera prim was not created")

    frames: list[str] = []
    poses: list[dict[str, Any]] = []
    _log(f"capturing orbit frames: {frame_count} frames at {args_cli.fps} fps")
    for frame_idx in range(frame_count):
        theta = start + (2.0 * math.pi * frame_idx / frame_count)
        eye = (
            target[0] + radius * math.cos(theta),
            target[1] + radius * math.sin(theta),
            target[2] + height,
        )
        quat = _set_camera_pose(camera_prim, eye, target)
        for _ in range(max(0, int(args_cli.sim_steps_per_frame))):
            sim.step(render=False)
        for _ in range(max(1, int(args_cli.rt_subframes))):
            sim.render()
        camera.update(float(sim.cfg.dt) * max(1, int(args_cli.sim_steps_per_frame)))
        dst = frames_dir / f"orbit_{frame_idx:04d}.png"
        _log(f"capturing orbit frame {frame_idx + 1}/{frame_count}")
        _save_rgb_tensor(dst, camera.data.output["rgb"][0])
        frames.append(str(dst))
        poses.append(
            {
                "frame": frame_idx,
                "theta_deg": math.degrees(theta),
                "eye": [float(v) for v in eye],
                "target": [float(v) for v in target],
                "quat_wxyz": [float(v) for v in quat],
            }
        )

    del camera
    return frames, {"frame_count": frame_count, "frames_dir": str(frames_dir), "camera_poses": poses}


def main() -> None:
    output_dir = args_cli.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"output_dir={output_dir}")

    resolved_scene = resolve_robolab_scene(
        args_cli.scene,
        robolab_root=args_cli.robolab_root,
        scene_dir=args_cli.robolab_scene_dir,
    )
    _log(f"resolved RoboLab scene: {resolved_scene.scene_path} ({resolved_scene.source})")

    rng = random.Random(int(args_cli.seed))
    _log("creating USD stage")
    create_new_stage()
    update_stage()
    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.Xform.Define(stage, "/World")
    _add_physics_scene(stage)
    sim = _create_sim_context()

    scene_root = _reference_robolab_scene(stage, resolved_scene.scene_path)
    robot_usd = _create_robot(stage)
    lighting = _add_lighting(stage, rng=rng)
    update_stage()

    scene_bbox = _compute_bbox(stage, scene_root)
    target, target_source, target_bbox = _target_from_bounds(stage, scene_root, scene_bbox)
    radius, height = _orbit_radius_and_height(scene_bbox, target)
    _log(
        "orbit target="
        f"{target} source={target_source} radius={radius:.3f} height={height:.3f}"
    )

    if args_cli.capture_backend == "tiled":
        frame_paths, orbit_result = _capture_orbit_video(
            sim=sim,
            target=target,
            radius=radius,
            height=height,
            scene_bbox=scene_bbox,
            output_dir=output_dir,
        )
    elif args_cli.capture_backend == "sensor":
        frame_paths, orbit_result = _capture_orbit_sensor(
            target=target,
            radius=radius,
            height=height,
            scene_bbox=scene_bbox,
            output_dir=output_dir,
        )
    else:
        frame_paths, orbit_result = _capture_orbit_viewport(
            target=target,
            radius=radius,
            height=height,
            output_dir=output_dir,
        )

    video_result: dict[str, Any] | None = None
    if args_cli.encode_video:
        video_result = _encode_video(output_dir / "frames", output_dir / "orbit.mp4", int(args_cli.fps))

    if args_cli.export_usd:
        usd_path = output_dir / "robolab_scene_in_dextrah.usda"
        stage.GetRootLayer().Export(str(usd_path))
        _log(f"exported USD stage: {usd_path}")
    else:
        usd_path = None

    metadata = {
        "scene_request": str(args_cli.scene),
        "scene_path": str(resolved_scene.scene_path),
        "scene_source": resolved_scene.source,
        "robolab_scene_dir": str(resolved_scene.scene_dir) if resolved_scene.scene_dir else None,
        "output_dir": str(output_dir),
        "seed": int(args_cli.seed),
        "render": {
            "width": int(args_cli.width),
            "height": int(args_cli.height),
            "fps": int(args_cli.fps),
            "video_seconds": float(args_cli.video_seconds),
            "frame_count": len(frame_paths),
            "capture_backend": str(args_cli.capture_backend),
            "encode_video": bool(args_cli.encode_video),
            "video": video_result,
        },
        "simulation": {
            "sim_dt": float(args_cli.sim_dt),
            "physics_device": str(args_cli.physics_device),
            "settle_steps": int(args_cli.settle_steps),
            "sim_steps_per_frame": int(args_cli.sim_steps_per_frame),
        },
        "scene_transform": {
            "translation": [float(v) for v in args_cli.scene_translation],
            "rotation_deg": [float(v) for v in args_cli.scene_rotation_deg],
            "scale": float(args_cli.scene_scale),
        },
        "scene_bbox": _range_to_dict(scene_bbox),
        "target_source": target_source,
        "target_bbox": target_bbox,
        "orbit": {
            "target": [float(v) for v in target],
            "radius": float(radius),
            "height": float(height),
            "elevation_deg": float(args_cli.orbit_elevation_deg),
            "start_deg": float(args_cli.orbit_start_deg),
        },
        "lighting": lighting,
        "robot": {
            "mode": str(args_cli.robot),
            "usd": robot_usd,
            "translation": [float(v) for v in args_cli.robot_translation],
            "rotation_deg": [float(v) for v in args_cli.robot_rotation_deg],
        },
        "frames": frame_paths,
        "orbit_capture": orbit_result,
        "usd_export": str(usd_path) if usd_path else None,
    }
    _write_json(output_dir / "render_manifest.json", metadata)
    _write_json(output_dir / "camera_poses.json", {"poses": orbit_result["camera_poses"]})
    _log(f"wrote manifest: {output_dir / 'render_manifest.json'}")
    if video_result is not None:
        _log(f"video encode status: {video_result.get('status')} path={video_result.get('path')}")

    simulation_app.close()


if __name__ == "__main__":
    main()
