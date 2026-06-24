"""Render reset-to-settle video evidence for tabletop clutter tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import sys
import traceback

from isaaclab.app import AppLauncher


DEFAULT_FRANKA_CAMERA_EYE = (-0.10, -1.05, 1.36)
DEFAULT_FRANKA_CAMERA_TARGET = (-0.62, 0.0, 0.78)
DEFAULT_YAM_CAMERA_EYE = (-0.58, -0.12, 0.74)
DEFAULT_YAM_CAMERA_TARGET = (-0.26, -0.28, 0.00)
DEFAULT_TASK = "Dextrah-Single-YAM-Single-Object-Policy-Grasp"
SURFACE_TEXTURE_EXTS = (".png", ".jpg", ".jpeg")
DOME_TEXTURE_EXTS = (".hdr", ".exr")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default=DEFAULT_TASK)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default="artifacts/tabletop_clutter_settle")
parser.add_argument("--video_path", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--settle_steps", type=int, default=180)
parser.add_argument("--capture_interval", type=int, default=2)
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--video_seconds", type=float, default=None)
parser.add_argument(
    "--demo_mode",
    type=str,
    default="settle",
    choices=("settle", "single_yam_rejected_path", "single_yam_trajectory"),
)
parser.add_argument("--demo_steps", type=int, default=180)
parser.add_argument("--demo_high_hold_z", type=float, default=0.16)
parser.add_argument("--demo_low_hold_z", type=float, default=-0.02)
parser.add_argument("--demo_trajectory_path", type=str, default=None)
parser.add_argument(
    "--demo_trajectory_source",
    type=str,
    default="auto",
    choices=("auto", "graspgenx_replay", "dextrah_table_rejection", "none"),
)
parser.add_argument(
    "--demo_trajectory_replay_mode",
    type=str,
    default="kinematic",
    choices=("kinematic", "dynamic"),
)
parser.add_argument(
    "--demo_trajectory_timing_mode",
    type=str,
    default="realtime",
    choices=("stretch", "realtime"),
    help=(
        "stretch maps all trajectory frames over --demo_steps. realtime respects "
        "the trajectory fps at the Isaac control timestep and holds the final "
        "frame after the source trajectory ends."
    ),
)
parser.add_argument("--demo_trajectory_velocity_targets", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--demo_trajectory_velocity_target_scale", type=float, default=1.0)
parser.add_argument(
    "--scripted_target_transport",
    action=argparse.BooleanOptionalAction,
    default=False,
    help="During trajectory replay, carry the target with the gripper through lift/place phases and release it over the bin.",
)
parser.add_argument("--demo_start_blend_steps", type=int, default=36)
parser.add_argument("--stable_scene_path", type=str, default=None)
parser.add_argument(
    "--stable_scene_output_path",
    type=str,
    default=None,
    help="Optional path for writing the final settled/replayed stable scene even when --stable_scene_path is an input.",
)
parser.add_argument("--record_trajectory_dataset", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--trajectory_dataset_path", type=str, default=None)
parser.add_argument("--record_rgb_width", type=int, default=160)
parser.add_argument("--record_rgb_height", type=int, default=120)
parser.add_argument("--record_rgb_interval", type=int, default=1)
parser.add_argument("--demo_table_rejection_target_fraction", type=float, default=0.82)
parser.add_argument("--render_warmup_frames", type=int, default=2)
parser.add_argument("--render_width", type=int, default=None)
parser.add_argument("--render_height", type=int, default=None)
parser.add_argument("--freeze_object_roots_for_video", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--repeat_initial_frame_for_video", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--visual_object_overlay", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--visual_object_overlay_z_offset", type=float, default=0.0)
parser.add_argument(
    "--hide_robot_debug_sites",
    action=argparse.BooleanOptionalAction,
    default=True,
    help="Hide visible MuJoCo robot site prims, such as YAM tcp_site/grasp_site, from rendered RGB.",
)
parser.add_argument("--grasp_pose_overlay_path", type=str, default=None)
parser.add_argument("--grasp_pose_overlay_max_count", type=int, default=8)
parser.add_argument("--grasp_pose_overlay_axis_length", type=float, default=0.075)
parser.add_argument("--grasp_pose_overlay_axis_thickness", type=float, default=0.007)
parser.add_argument("--dome_light_intensity", type=float, default=None)
parser.add_argument("--dome_light_exposure", type=float, default=None)
parser.add_argument("--key_light_enabled", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--key_light_intensity", type=float, default=None)
parser.add_argument("--key_light_exposure", type=float, default=None)
parser.add_argument("--camera_eye", type=float, nargs=3, default=None)
parser.add_argument("--camera_target", type=float, nargs=3, default=None)
parser.add_argument(
    "--yam_policy_scene_randomization",
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Randomize the single-YAM one-object policy scene layout and visual conditions before env creation.",
)
parser.add_argument("--yam_policy_object_x_range", type=float, nargs=2, default=(-0.42, -0.22))
parser.add_argument("--yam_policy_object_y_range", type=float, nargs=2, default=(-0.42, -0.18))
parser.add_argument("--yam_policy_bin_x_range", type=float, nargs=2, default=(-0.34, -0.10))
parser.add_argument("--yam_policy_bin_y_range", type=float, nargs=2, default=(0.20, 0.46))
parser.add_argument("--yam_policy_bin_inner_size_x_range", type=float, nargs=2, default=(0.28, 0.42))
parser.add_argument("--yam_policy_bin_inner_size_y_range", type=float, nargs=2, default=(0.20, 0.34))
parser.add_argument("--yam_policy_bin_wall_height_range", type=float, nargs=2, default=(0.08, 0.16))
parser.add_argument("--yam_policy_scene_camera_eye_jitter", type=float, nargs=3, default=(0.04, 0.04, 0.04))
parser.add_argument("--yam_policy_scene_camera_target_jitter", type=float, nargs=3, default=(0.03, 0.03, 0.02))
parser.add_argument("--yam_policy_dome_light_intensity_range", type=float, nargs=2, default=(450.0, 1600.0))
parser.add_argument("--yam_policy_key_light_intensity_range", type=float, nargs=2, default=(250.0, 1400.0))
parser.add_argument("--yam_policy_material_value_range", type=float, nargs=2, default=(0.32, 0.82))
parser.add_argument("--yam_policy_tabletop_surround", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--yam_policy_tabletop_surround_size", type=float, nargs=2, default=(1.04, 1.20))
parser.add_argument("--yam_policy_tabletop_surround_top_z_offset", type=float, default=-0.004)
parser.add_argument("--yam_policy_tabletop_surround_thickness", type=float, default=0.006)
parser.add_argument("--yam_policy_tabletop_surround_color_jitter", type=float, default=0.08)
parser.add_argument("--yam_policy_tabletop_texture", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--yam_policy_tabletop_texture_patch_count_range", type=int, nargs=2, default=(0, 0))
parser.add_argument("--yam_policy_tabletop_texture_color_jitter", type=float, default=0.16)
parser.add_argument("--yam_policy_table_texture_dir", type=str, default=None)
parser.add_argument("--yam_policy_table_texture_tiling_range", type=float, nargs=2, default=(1.4, 3.8))
parser.add_argument("--yam_policy_background_walls", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--yam_policy_background_wall_distance", type=float, default=1.28)
parser.add_argument("--yam_policy_background_wall_height", type=float, default=0.72)
parser.add_argument("--yam_policy_background_wall_thickness", type=float, default=0.025)
parser.add_argument("--yam_policy_background_texture_dir", type=str, default=None)
parser.add_argument("--yam_policy_background_texture_tiling_range", type=float, nargs=2, default=(1.0, 2.2))
parser.add_argument("--yam_policy_dome_light_texture_dir", type=str, default=None)
parser.add_argument("--record_multicam_rgb", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--record_scene_rgb", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--record_wrist_rgb", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument(
    "--wrist_camera_mode",
    type=str,
    default="sensor",
    choices=("sensor", "viewer"),
    help="Use an IsaacLab Camera sensor on YAM link_6 or the legacy TCP-relative viewer camera for wrist RGB.",
)
parser.add_argument("--wrist_camera_pos_offset", type=float, nargs=3, default=(0.035, 0.0, 0.085))
parser.add_argument("--wrist_camera_forward", type=float, nargs=3, default=(0.16, 0.0, -0.10))
parser.add_argument("--yam_arm_stiffness_scale", type=float, default=None)
parser.add_argument("--yam_arm_damping_scale", type=float, default=None)
parser.add_argument("--yam_arm_effort_scale", type=float, default=None)
parser.add_argument("--yam_gripper_stiffness_scale", type=float, default=None)
parser.add_argument("--yam_gripper_damping_scale", type=float, default=None)
parser.add_argument("--yam_gripper_effort_scale", type=float, default=None)
parser.add_argument("--object_asset_manifest_path", type=str, default=None)
parser.add_argument("--object_assets_dir", type=str, default=None)
parser.add_argument("--max_objects", type=int, default=None)
parser.add_argument("--object_asset_assignment", type=str, default=None)
parser.add_argument("--object_validate_usd_bounds", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--object_usd_bounds_max_ratio", type=float, default=None)
parser.add_argument("--object_usd_bounds_max_dimension", type=float, default=None)
parser.add_argument("--require_graspgen_scale", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--object_spawn_xy_randomization", type=float, default=None)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=None)
parser.add_argument("--object_spawn_z_clearance", type=float, default=None)
parser.add_argument("--object_kinematic_enabled", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--object_disable_gravity", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--object_solver_position_iterations", type=int, default=None)
parser.add_argument("--object_solver_velocity_iterations", type=int, default=None)
parser.add_argument("--object_linear_damping", type=float, default=None)
parser.add_argument("--object_angular_damping", type=float, default=None)
parser.add_argument("--object_sleep_threshold", type=float, default=None)
parser.add_argument("--object_stabilization_threshold", type=float, default=None)
parser.add_argument("--object_max_linear_velocity", type=float, default=None)
parser.add_argument("--object_max_angular_velocity", type=float, default=None)
parser.add_argument("--object_max_depenetration_velocity", type=float, default=None)
parser.add_argument("--tabletop_clutter_asset_manifest_path", type=str, default=None)
parser.add_argument("--tabletop_clutter_assets_dir", type=str, default=None)
parser.add_argument("--tabletop_clutter_max_objects", type=int, default=None)
parser.add_argument("--tabletop_clutter_object_count", type=int, default=None)
parser.add_argument("--tabletop_clutter_asset_assignment", type=str, default=None)
parser.add_argument("--tabletop_clutter_validate_usd_bounds", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_usd_bounds_max_ratio", type=float, default=None)
parser.add_argument("--tabletop_clutter_usd_bounds_max_dimension", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_xy_randomization", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_yaw_randomization_deg", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_z_clearance", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_z_jitter", type=float, default=None)
parser.add_argument("--tabletop_clutter_require_graspgen_scale", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_enabled", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_cache_dir", type=str, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_count", type=int, default=None)
parser.add_argument("--tabletop_clutter_non_overlapping", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_placement_padding", type=float, default=None)
parser.add_argument("--tabletop_clutter_placement_attempts", type=int, default=None)
parser.add_argument("--tabletop_clutter_max_xy_radius", type=float, default=None)
parser.add_argument("--tabletop_clutter_solver_position_iterations", type=int, default=None)
parser.add_argument("--tabletop_clutter_solver_velocity_iterations", type=int, default=None)
parser.add_argument("--tabletop_clutter_kinematic_enabled", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_disable_gravity", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_linear_damping", type=float, default=None)
parser.add_argument("--tabletop_clutter_angular_damping", type=float, default=None)
parser.add_argument("--tabletop_clutter_sleep_threshold", type=float, default=None)
parser.add_argument("--tabletop_clutter_stabilization_threshold", type=float, default=None)
parser.add_argument("--tabletop_clutter_max_linear_velocity", type=float, default=None)
parser.add_argument("--tabletop_clutter_max_angular_velocity", type=float, default=None)
parser.add_argument("--tabletop_clutter_max_depenetration_velocity", type=float, default=None)
parser.add_argument("--objaverse_textured_manifest_path", type=str, default=None)
parser.add_argument("--objaverse_textured_asset_dir", type=str, default=None)
parser.add_argument("--objaverse_textured_max_assets", type=int, default=None)
parser.add_argument("--objaverse_textured_mesh_source", type=str, default="auto", choices=["auto", "glb", "obj", "urdf_obj"])
parser.add_argument("--objaverse_textured_make_instanceable", action="store_true", default=False)
parser.add_argument("--objaverse_textured_force_conversion", action="store_true", default=False)
parser.add_argument("--objaverse_textured_collision_approximation", type=str, default="convexHull")
parser.add_argument("--objaverse_textured_require_graspgen_prior_scale", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--objaverse_textured_stable_pose_mesh_mode", type=str, default="convex_hull", choices=("convex_hull", "visual"))
parser.add_argument("--disable_objaverse_textured_common_tabletop_priority", action="store_true", default=False)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
args_cli.enable_cameras = True
sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import imageio.v2 as imageio
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
import isaaclab.sim as sim_utils
from isaacsim.core.utils.extensions import enable_extension
from isaaclab.sim.converters import MeshConverter, MeshConverterCfg
from isaaclab.sim.schemas import schemas as sim_schemas
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab_tasks.utils import parse_env_cfg
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401

if "YAM" in args_cli.task:
    from dextrah_lab.assets.yam.bimanual_yam import (
        MOLMOACT2_CAMERA_HEIGHT,
        MOLMOACT2_CAMERA_WIDTH,
        MOLMOACT2_WRIST_CAMERA_INTRINSIC,
        MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
        MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
    )

    import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup  # noqa: F401
    import dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.gym_setup  # noqa: F401


def _set_if_present(cfg, name: str, value) -> None:
    if value is not None and hasattr(cfg, name):
        setattr(cfg, name, value)


def _scale_gain_value(value, scale: float):
    if isinstance(value, dict):
        return {k: _scale_gain_value(v, scale) for k, v in value.items()}
    if value is None:
        return None
    return float(value) * float(scale)


def _jsonable_gain_value(value):
    if isinstance(value, dict):
        return {str(k): _jsonable_gain_value(v) for k, v in value.items()}
    if value is None:
        return None
    return float(value)


def _apply_yam_actuator_gain_scales(
    env_cfg,
    *,
    actuator_name: str,
    stiffness_scale,
    damping_scale,
    effort_scale,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "enabled": False,
        "actuator_name": str(actuator_name),
        "stiffness_scale": None if stiffness_scale is None else float(stiffness_scale),
        "damping_scale": None if damping_scale is None else float(damping_scale),
        "effort_scale": None if effort_scale is None else float(effort_scale),
        "before": None,
        "after": None,
    }
    if stiffness_scale is None and damping_scale is None and effort_scale is None:
        return summary
    robot_cfg = getattr(env_cfg, "robot", None)
    actuators = getattr(robot_cfg, "actuators", None)
    if not isinstance(actuators, dict) or actuator_name not in actuators:
        summary["reason"] = f"missing_yam_{actuator_name}_actuator"
        return summary
    actuator = actuators[actuator_name]
    before = {
        "stiffness": _jsonable_gain_value(getattr(actuator, "stiffness", None)),
        "damping": _jsonable_gain_value(getattr(actuator, "damping", None)),
        "effort_limit_sim": _jsonable_gain_value(getattr(actuator, "effort_limit_sim", None)),
    }
    if stiffness_scale is not None:
        actuator.stiffness = _scale_gain_value(actuator.stiffness, float(stiffness_scale))
    if damping_scale is not None:
        actuator.damping = _scale_gain_value(actuator.damping, float(damping_scale))
    if effort_scale is not None:
        actuator.effort_limit_sim = _scale_gain_value(actuator.effort_limit_sim, float(effort_scale))
    after = {
        "stiffness": _jsonable_gain_value(getattr(actuator, "stiffness", None)),
        "damping": _jsonable_gain_value(getattr(actuator, "damping", None)),
        "effort_limit_sim": _jsonable_gain_value(getattr(actuator, "effort_limit_sim", None)),
    }
    summary.update({"enabled": True, "before": before, "after": after})
    return summary


def _task_camera_defaults(task: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if "YAM" in task:
        return DEFAULT_YAM_CAMERA_EYE, DEFAULT_YAM_CAMERA_TARGET
    return DEFAULT_FRANKA_CAMERA_EYE, DEFAULT_FRANKA_CAMERA_TARGET


def _frame_array(frame) -> np.ndarray:
    if isinstance(frame, (list, tuple)):
        if not frame:
            raise RuntimeError("render() returned an empty frame list")
        frame = frame[0]
    frame = np.asarray(frame)
    if frame.ndim == 4:
        frame = frame[0]
    if frame.ndim != 3 or frame.shape[-1] not in (3, 4):
        raise RuntimeError(f"Unexpected render frame shape: {frame.shape}")
    if frame.shape[-1] == 4:
        frame = frame[:, :, :3]
    return frame.astype(np.uint8, copy=False)


def _capture_frame(env, frame_dir: Path, frame_idx: int) -> tuple[np.ndarray, str]:
    frame = _frame_array(env.render())
    frame_path = frame_dir / f"frame_{frame_idx:04d}.png"
    imageio.imwrite(frame_path, frame)
    return frame, str(frame_path)


def _camera_rgb_array(rgb_tensor: torch.Tensor) -> np.ndarray:
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


def _find_body_prim_path(stage, body_name: str) -> str:
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


def _spawn_d405_from_intrinsic() -> sim_utils.PinholeCameraCfg:
    return sim_utils.PinholeCameraCfg.from_intrinsic_matrix(
        intrinsic_matrix=list(MOLMOACT2_WRIST_CAMERA_INTRINSIC),
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        focal_length=24.0,
        focus_distance=400.0,
        clipping_range=(0.01, 10.0),
    )


def _make_single_yam_wrist_camera(task_env) -> tuple[Camera, dict[str, object]]:
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("Cannot create wrist camera without a USD stage")
    parent_path = _find_body_prim_path(stage, "link_6")
    cfg = CameraCfg(
        prim_path=f"{parent_path}/wrist_d405_policy_sensor",
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        data_types=["rgb"],
        update_period=0.0,
        spawn=_spawn_d405_from_intrinsic(),
        offset=CameraCfg.OffsetCfg(
            pos=MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
            rot=MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
            convention="world",
        ),
    )
    camera = Camera(cfg)
    if camera.is_initialized:
        camera.reset()
    else:
        camera._initialize_impl()
        camera._is_initialized = True
        camera.reset()
    task_env.sim.render()
    camera.update(0.0, force_recompute=True)
    return camera, {
        "enabled": True,
        "mode": "sensor",
        "parent_path": parent_path,
        "prim_path": cfg.prim_path,
        "width": int(MOLMOACT2_CAMERA_WIDTH),
        "height": int(MOLMOACT2_CAMERA_HEIGHT),
        "local_pos": [float(v) for v in MOLMOACT2_WRIST_CAMERA_LOCAL_POS],
        "local_quat_wxyz": [float(v) for v in MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ],
        "intrinsic_row_major": [float(v) for v in MOLMOACT2_WRIST_CAMERA_INTRINSIC],
    }


def _resize_rgb_nearest(frame: np.ndarray, height: int, width: int) -> np.ndarray:
    height = max(int(height), 1)
    width = max(int(width), 1)
    frame = np.asarray(frame)
    if frame.shape[0] == height and frame.shape[1] == width:
        return frame.astype(np.uint8, copy=False)
    y_idx = np.linspace(0, frame.shape[0] - 1, height).round().astype(np.int64)
    x_idx = np.linspace(0, frame.shape[1] - 1, width).round().astype(np.int64)
    return frame[y_idx[:, None], x_idx[None, :], :].astype(np.uint8, copy=False)


def _tensor_numpy(value: torch.Tensor, dtype=np.float32) -> np.ndarray:
    return value.detach().cpu().numpy().astype(dtype, copy=False)


def _tensor_list(value: torch.Tensor):
    return value.detach().float().cpu().tolist()


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, torch.Tensor):
        return value.detach().float().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _hide_robot_debug_site_prims(*, site_names: tuple[str, ...] = ("tcp_site", "grasp_site")) -> dict[str, object]:
    stage = omni.usd.get_context().get_stage()
    summary: dict[str, object] = {
        "enabled": True,
        "site_names": list(site_names),
        "hidden_count": 0,
        "hidden_paths": [],
    }
    if stage is None:
        summary["reason"] = "missing_stage"
        return summary

    hidden_paths: list[str] = []
    site_name_set = set(site_names)
    for prim in stage.Traverse():
        if prim.GetName() not in site_name_set:
            continue
        imageable = UsdGeom.Imageable(prim)
        if not imageable:
            continue
        imageable.MakeInvisible()
        hidden_paths.append(str(prim.GetPath()))

    summary["hidden_count"] = len(hidden_paths)
    summary["hidden_paths"] = hidden_paths
    return summary


def _quat_wxyz_to_matrix(q: list[float]) -> np.ndarray:
    qw, qx, qy, qz = [float(v) for v in q]
    n = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if n <= 0.0:
        return np.eye(3, dtype=np.float64)
    qw, qx, qy, qz = qw / n, qx / n, qy / n, qz / n
    return np.asarray(
        [
            [1.0 - 2.0 * (qy * qy + qz * qz), 2.0 * (qx * qy - qz * qw), 2.0 * (qx * qz + qy * qw)],
            [2.0 * (qx * qy + qz * qw), 1.0 - 2.0 * (qx * qx + qz * qz), 2.0 * (qy * qz - qx * qw)],
            [2.0 * (qx * qz - qy * qw), 2.0 * (qy * qz + qx * qw), 1.0 - 2.0 * (qx * qx + qy * qy)],
        ],
        dtype=np.float64,
    )


def _matrix_from_pose_wxyz(pos: list[float], quat_wxyz: list[float]) -> list[list[float]]:
    mat = np.eye(4, dtype=np.float64)
    mat[:3, :3] = _quat_wxyz_to_matrix(quat_wxyz)
    mat[:3, 3] = np.asarray(pos, dtype=np.float64)
    return mat.tolist()


def _range_pair(values, *, name: str) -> tuple[float, float]:
    if values is None or len(values) != 2:
        raise ValueError(f"{name} must contain exactly two values")
    lo, hi = (float(values[0]), float(values[1]))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _rng_uniform(rng: np.random.Generator, values, *, name: str) -> float:
    lo, hi = _range_pair(values, name=name)
    return float(rng.uniform(lo, hi))


def _rng_vec_jitter(rng: np.random.Generator, base: tuple[float, float, float], jitter) -> tuple[float, float, float]:
    jitter_arr = np.asarray(tuple(float(v) for v in jitter), dtype=np.float64)
    if jitter_arr.shape != (3,):
        raise ValueError(f"Expected 3D jitter, got {jitter}")
    delta = rng.uniform(-jitter_arr, jitter_arr)
    return tuple(float(v) for v in np.asarray(base, dtype=np.float64) + delta)


def _random_color(rng: np.random.Generator, value_range) -> tuple[float, float, float]:
    lo, hi = _range_pair(value_range, name="material_value_range")
    hue = float(rng.uniform(0.0, 1.0))
    sat = float(rng.uniform(0.12, 0.42))
    val = float(rng.uniform(lo, hi))
    chroma = val * sat
    x = chroma * (1.0 - abs((hue * 6.0) % 2.0 - 1.0))
    m = val - chroma
    sector = int(hue * 6.0) % 6
    rgb = (
        (chroma, x, 0.0),
        (x, chroma, 0.0),
        (0.0, chroma, x),
        (0.0, x, chroma),
        (x, 0.0, chroma),
        (chroma, 0.0, x),
    )[sector]
    return tuple(float(max(0.0, min(1.0, c + m))) for c in rgb)


def _jitter_color(
    rng: np.random.Generator,
    base: tuple[float, float, float],
    jitter: float,
    *,
    min_value: float = 0.05,
    max_value: float = 0.95,
) -> tuple[float, float, float]:
    jitter = max(float(jitter), 0.0)
    return tuple(float(np.clip(float(channel) + rng.uniform(-jitter, jitter), min_value, max_value)) for channel in base)


def _set_preview_surface_color(material, color: tuple[float, float, float], roughness: float | None = None) -> bool:
    if material is None:
        return False
    changed = False
    if hasattr(material, "diffuse_color"):
        material.diffuse_color = tuple(float(v) for v in color)
        changed = True
    if roughness is not None and hasattr(material, "roughness"):
        material.roughness = float(roughness)
        changed = True
    return changed


def _texture_candidates(
    roots: str | None,
    *,
    exts: tuple[str, ...],
    include_tokens: tuple[str, ...] = (),
    exclude_tokens: tuple[str, ...] = (),
) -> list[str]:
    if roots is None or not str(roots).strip():
        return []
    candidates: list[str] = []
    for raw_root in str(roots).split(os.pathsep):
        raw_root = raw_root.strip()
        if not raw_root:
            continue
        root = Path(raw_root).expanduser()
        if not root.is_absolute():
            root = (Path(__file__).resolve().parents[2] / root).resolve()
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            name = path.name.lower()
            suffix = path.suffix.lower()
            if suffix not in exts:
                continue
            if include_tokens and not any(token in name for token in include_tokens):
                continue
            if exclude_tokens and any(token in name for token in exclude_tokens):
                continue
            candidates.append(str(path))
    return sorted(dict.fromkeys(candidates))


def _sample_texture_path(
    rng: np.random.Generator,
    roots: str | None,
    *,
    exts: tuple[str, ...],
    include_tokens: tuple[str, ...] = (),
    exclude_tokens: tuple[str, ...] = (),
) -> str:
    candidates = _texture_candidates(
        roots,
        exts=exts,
        include_tokens=include_tokens,
        exclude_tokens=exclude_tokens,
    )
    if not candidates:
        return ""
    return candidates[int(rng.integers(0, len(candidates)))]


def _apply_stable_scene_bins_to_env_cfg(env_cfg, stable_scene: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(stable_scene, dict):
        return {"enabled": False}
    bins = stable_scene.get("bins") if isinstance(stable_scene.get("bins"), dict) else {}
    summary: dict[str, object] = {"enabled": True, "bins": {}}
    for bin_name, prefix in (("goal", "tabletop_goal_bin"), ("source", "tabletop_source_bin")):
        info = bins.get(bin_name) if isinstance(bins.get(bin_name), dict) else None
        if info is None:
            continue
        setattr(env_cfg, f"{prefix}_enabled", True)
        setattr(env_cfg, f"{prefix}_center_offset_x", float(info["center_x"]) - float(env_cfg.table_center_x))
        setattr(env_cfg, f"{prefix}_center_offset_y", float(info["center_y"]) - float(env_cfg.table_center_y))
        for key in ("inner_size_x", "inner_size_y", "wall_thickness", "bottom_thickness", "wall_height"):
            if key in info:
                setattr(env_cfg, f"{prefix}_{key}", float(info[key]))
        if "clearance" in info:
            setattr(env_cfg, f"{prefix}_clearance", float(info["clearance"]))
        if bin_name == "goal" and "placement_clearance" in info:
            setattr(env_cfg, f"{prefix}_placement_clearance", float(info["placement_clearance"]))
        if "goal_z" in info:
            goal_height = float(info["goal_z"]) - float(info.get("table_surface_z", env_cfg.table_surface_z)) - float(
                info.get("bottom_thickness", getattr(env_cfg, f"{prefix}_bottom_thickness", 0.012))
            )
            setattr(env_cfg, f"{prefix}_goal_height", max(goal_height, 0.0))
        summary["bins"][bin_name] = {str(k): _jsonable(v) for k, v in info.items()}
    return summary


def _update_yam_policy_randomization_with_restored_bins(env_cfg, stable_scene_bin_restore: dict[str, object]) -> None:
    if not bool(stable_scene_bin_restore.get("enabled")):
        return
    current_summary = getattr(env_cfg, "yam_policy_scene_randomization_summary", {"enabled": False})
    if not isinstance(current_summary, dict):
        return
    bins = stable_scene_bin_restore.get("bins") if isinstance(stable_scene_bin_restore.get("bins"), dict) else {}
    if not bins:
        return
    restored_summary = dict(current_summary)
    for bin_name, summary_key in (("goal", "goal_bin"), ("source", "source_bin")):
        info = bins.get(bin_name) if isinstance(bins.get(bin_name), dict) else None
        if info is None:
            continue
        previous_key = f"pre_restore_{summary_key}"
        if summary_key in restored_summary and previous_key not in restored_summary:
            restored_summary[previous_key] = restored_summary[summary_key]
        restored_summary[summary_key] = {
            key: float(info[key])
            for key in ("center_x", "center_y", "inner_size_x", "inner_size_y", "wall_height")
            if key in info
        }
    restored_summary["stable_scene_bin_restore"] = stable_scene_bin_restore
    restored_summary["bin_source"] = "stable_scene_restore"
    setattr(env_cfg, "yam_policy_scene_randomization_summary", restored_summary)


def _apply_yam_policy_scene_randomization(env_cfg, args, rng: np.random.Generator) -> dict[str, object]:
    if not bool(args.yam_policy_scene_randomization):
        return {"enabled": False}
    object_x_range = _range_pair(args.yam_policy_object_x_range, name="yam_policy_object_x_range")
    object_y_range = _range_pair(args.yam_policy_object_y_range, name="yam_policy_object_y_range")
    object_center_x = 0.5 * (object_x_range[0] + object_x_range[1])
    object_center_y = 0.5 * (object_y_range[0] + object_y_range[1])
    bin_x = _rng_uniform(rng, args.yam_policy_bin_x_range, name="yam_policy_bin_x_range")
    bin_y = _rng_uniform(rng, args.yam_policy_bin_y_range, name="yam_policy_bin_y_range")
    bin_inner_x = _rng_uniform(rng, args.yam_policy_bin_inner_size_x_range, name="yam_policy_bin_inner_size_x_range")
    bin_inner_y = _rng_uniform(rng, args.yam_policy_bin_inner_size_y_range, name="yam_policy_bin_inner_size_y_range")
    bin_wall_height = _rng_uniform(rng, args.yam_policy_bin_wall_height_range, name="yam_policy_bin_wall_height_range")

    setattr(env_cfg, "object_spawn_center_offset_x", object_center_x - float(env_cfg.table_center_x))
    setattr(env_cfg, "object_spawn_center_offset_y", object_center_y - float(env_cfg.table_center_y))
    setattr(env_cfg, "object_spawn_x_randomization", 0.5 * abs(object_x_range[1] - object_x_range[0]))
    setattr(env_cfg, "object_spawn_y_randomization", 0.5 * abs(object_y_range[1] - object_y_range[0]))
    setattr(env_cfg, "object_spawn_xy_randomization", 0.0)
    setattr(env_cfg, "tabletop_goal_bin_enabled", True)
    setattr(env_cfg, "tabletop_goal_bin_center_offset_x", bin_x - float(env_cfg.table_center_x))
    setattr(env_cfg, "tabletop_goal_bin_center_offset_y", bin_y - float(env_cfg.table_center_y))
    setattr(env_cfg, "tabletop_goal_bin_inner_size_x", bin_inner_x)
    setattr(env_cfg, "tabletop_goal_bin_inner_size_y", bin_inner_y)
    setattr(env_cfg, "tabletop_goal_bin_wall_height", bin_wall_height)
    setattr(env_cfg, "tabletop_goal_bin_clearance", 0.08)
    setattr(env_cfg, "tabletop_goal_bin_placement_clearance", 0.08)
    setattr(env_cfg, "tabletop_goal_bin_success_xy_tol", min(0.12, 0.35 * min(bin_inner_x, bin_inner_y)))
    setattr(env_cfg, "cube_success_xy_tol", getattr(env_cfg, "tabletop_goal_bin_success_xy_tol"))
    setattr(env_cfg, "tabletop_source_bin_enabled", False)

    table_color = _random_color(rng, args.yam_policy_material_value_range)
    ground_color = _random_color(rng, args.yam_policy_material_value_range)
    bin_floor_color = _random_color(rng, args.yam_policy_material_value_range)
    x_wall_color = _random_color(rng, args.yam_policy_material_value_range)
    y_wall_color = _random_color(rng, args.yam_policy_material_value_range)
    setattr(env_cfg, "ground_plane_color", ground_color)
    table_material_changed = False
    table_cfg = getattr(env_cfg, "table", None)
    table_spawn = getattr(table_cfg, "spawn", None)
    if table_spawn is not None:
        table_material_changed = _set_preview_surface_color(
            getattr(table_spawn, "visual_material", None),
            table_color,
            roughness=float(rng.uniform(0.45, 0.92)),
        )
    surround_size = tuple(float(v) for v in args.yam_policy_tabletop_surround_size)
    surround_color = _jitter_color(rng, table_color, args.yam_policy_tabletop_surround_color_jitter)
    texture_count_range = tuple(int(v) for v in args.yam_policy_tabletop_texture_patch_count_range)
    if texture_count_range[1] < texture_count_range[0]:
        raise ValueError(f"Invalid yam_policy_tabletop_texture_patch_count_range: {texture_count_range}")
    texture_patch_count = int(rng.integers(texture_count_range[0], texture_count_range[1] + 1))
    texture_patches: list[dict[str, object]] = []
    if bool(args.yam_policy_tabletop_texture):
        for _patch_idx in range(texture_patch_count):
            along_x = bool(rng.integers(0, 2))
            long_dim = float(rng.uniform(0.35, 0.95))
            short_dim = float(rng.uniform(0.018, 0.075))
            size_x = long_dim if along_x else short_dim
            size_y = short_dim if along_x else long_dim
            margin = 0.08
            max_x = max(0.01, 0.5 * surround_size[0] - margin - 0.5 * size_x)
            max_y = max(0.01, 0.5 * surround_size[1] - margin - 0.5 * size_y)
            texture_patches.append(
                {
                    "center_offset": [float(rng.uniform(-max_x, max_x)), float(rng.uniform(-max_y, max_y))],
                    "size": [size_x, size_y],
                    "color": [float(v) for v in _jitter_color(rng, table_color, args.yam_policy_tabletop_texture_color_jitter)],
                }
            )
    background_wall_color = _random_color(rng, args.yam_policy_material_value_range)
    setattr(env_cfg, "yam_policy_tabletop_surround_enabled", bool(args.yam_policy_tabletop_surround))
    setattr(env_cfg, "yam_policy_tabletop_surround_size", surround_size)
    setattr(env_cfg, "yam_policy_tabletop_surround_top_z_offset", float(args.yam_policy_tabletop_surround_top_z_offset))
    setattr(env_cfg, "yam_policy_tabletop_surround_thickness", float(args.yam_policy_tabletop_surround_thickness))
    setattr(env_cfg, "yam_policy_tabletop_surround_color", surround_color)
    setattr(env_cfg, "yam_policy_tabletop_surround_roughness", float(rng.uniform(0.52, 0.95)))
    setattr(env_cfg, "yam_policy_tabletop_texture_enabled", bool(args.yam_policy_tabletop_texture))
    setattr(env_cfg, "yam_policy_tabletop_texture_patches", texture_patches)
    setattr(env_cfg, "yam_policy_tabletop_texture_roughness", float(rng.uniform(0.60, 0.96)))
    table_texture_path = _sample_texture_path(
        rng,
        args.yam_policy_table_texture_dir,
        exts=SURFACE_TEXTURE_EXTS,
        include_tokens=("albedo", "diffuse", "diff", "basecolor", "color"),
        exclude_tokens=("normal", "orm", "rough", "metal", "height"),
    )
    table_texture_tiling_range = _range_pair(
        args.yam_policy_table_texture_tiling_range,
        name="yam_policy_table_texture_tiling_range",
    )
    table_texture_tiling = float(rng.uniform(table_texture_tiling_range[0], table_texture_tiling_range[1]))
    setattr(env_cfg, "yam_policy_table_texture_path", table_texture_path)
    setattr(env_cfg, "yam_policy_table_texture_tiling", table_texture_tiling)
    setattr(env_cfg, "yam_policy_background_walls_enabled", bool(args.yam_policy_background_walls))
    setattr(env_cfg, "yam_policy_background_wall_distance", float(args.yam_policy_background_wall_distance))
    setattr(env_cfg, "yam_policy_background_wall_height", float(args.yam_policy_background_wall_height))
    setattr(env_cfg, "yam_policy_background_wall_thickness", float(args.yam_policy_background_wall_thickness))
    setattr(env_cfg, "yam_policy_background_wall_color", background_wall_color)
    setattr(env_cfg, "yam_policy_background_wall_roughness", float(rng.uniform(0.58, 0.95)))
    background_texture_path = _sample_texture_path(
        rng,
        args.yam_policy_background_texture_dir,
        exts=SURFACE_TEXTURE_EXTS,
        exclude_tokens=("normal", "orm", "rough", "metal", "height"),
    )
    background_texture_tiling_range = _range_pair(
        args.yam_policy_background_texture_tiling_range,
        name="yam_policy_background_texture_tiling_range",
    )
    background_texture_tiling = float(rng.uniform(background_texture_tiling_range[0], background_texture_tiling_range[1]))
    dome_texture_roots = args.yam_policy_dome_light_texture_dir or args.yam_policy_background_texture_dir
    dome_texture_path = _sample_texture_path(rng, dome_texture_roots, exts=DOME_TEXTURE_EXTS)
    setattr(env_cfg, "yam_policy_background_texture_path", background_texture_path)
    setattr(env_cfg, "yam_policy_background_texture_tiling", background_texture_tiling)
    setattr(env_cfg, "yam_policy_dome_light_texture_path", dome_texture_path)
    setattr(env_cfg, "tabletop_goal_bin_floor_color", bin_floor_color)
    setattr(env_cfg, "tabletop_goal_bin_x_wall_color", x_wall_color)
    setattr(env_cfg, "tabletop_goal_bin_y_wall_color", y_wall_color)
    setattr(env_cfg, "tabletop_goal_bin_visual_roughness", float(rng.uniform(0.45, 0.92)))

    dome_light = _rng_uniform(rng, args.yam_policy_dome_light_intensity_range, name="yam_policy_dome_light_intensity_range")
    key_light = _rng_uniform(rng, args.yam_policy_key_light_intensity_range, name="yam_policy_key_light_intensity_range")
    setattr(env_cfg, "dome_light_intensity", dome_light)
    setattr(env_cfg, "key_light_enabled", True)
    setattr(env_cfg, "key_light_intensity", key_light)
    setattr(env_cfg, "key_light_rotation_deg", tuple(float(v) for v in rng.uniform((35.0, -8.0, -75.0), (72.0, 8.0, 35.0))))

    summary = {
        "enabled": True,
        "coordinate_convention": {
            "x": "YAM forward toward table",
            "positive_y": "robot-left/table-left",
            "negative_y": "robot-right/table-right",
        },
        "object_region": {
            "center_x": object_center_x,
            "center_y": object_center_y,
            "x_range": [float(v) for v in args.yam_policy_object_x_range],
            "y_range": [float(v) for v in args.yam_policy_object_y_range],
        },
        "goal_bin": {
            "center_x": bin_x,
            "center_y": bin_y,
            "inner_size_x": bin_inner_x,
            "inner_size_y": bin_inner_y,
            "wall_height": bin_wall_height,
        },
        "materials": {
            "table_color": table_color,
            "table_material_changed": bool(table_material_changed),
            "ground_color": ground_color,
            "goal_bin_floor_color": bin_floor_color,
            "goal_bin_x_wall_color": x_wall_color,
            "goal_bin_y_wall_color": y_wall_color,
            "tabletop_surround_color": surround_color,
        },
        "tabletop_surround": {
            "enabled": bool(args.yam_policy_tabletop_surround),
            "size": [float(v) for v in args.yam_policy_tabletop_surround_size],
            "top_z_offset": float(args.yam_policy_tabletop_surround_top_z_offset),
            "thickness": float(args.yam_policy_tabletop_surround_thickness),
        },
        "tabletop_texture": {
            "enabled": bool(args.yam_policy_tabletop_texture),
            "patch_count": len(texture_patches),
            "patches": texture_patches,
            "table_texture_dir": args.yam_policy_table_texture_dir,
            "table_texture_path": table_texture_path or None,
            "table_texture_tiling": table_texture_tiling,
        },
        "background_walls": {
            "enabled": bool(args.yam_policy_background_walls),
            "distance": float(args.yam_policy_background_wall_distance),
            "height": float(args.yam_policy_background_wall_height),
            "thickness": float(args.yam_policy_background_wall_thickness),
            "color": [float(v) for v in background_wall_color],
            "background_texture_dir": args.yam_policy_background_texture_dir,
            "background_texture_path": background_texture_path or None,
            "background_texture_tiling": background_texture_tiling,
        },
        "lighting": {
            "dome_light_intensity": dome_light,
            "dome_light_texture_dir": dome_texture_roots,
            "dome_light_texture_path": dome_texture_path or None,
            "key_light_intensity": key_light,
            "key_light_rotation_deg": [float(v) for v in getattr(env_cfg, "key_light_rotation_deg", ())],
        },
    }
    setattr(env_cfg, "yam_policy_scene_randomization_summary", summary)
    return summary


def _resolve_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _npz_scalar(value) -> object:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _resolve_record_grasp_prior_path(record: dict[str, object], *, asset_root: Path) -> Path | None:
    candidates: list[Path] = []
    for key in ("grasp_prior_path", "source_grasp_prior_path"):
        value = record.get(key)
        if value:
            candidates.append(_resolve_path(str(value), base_dir=asset_root))
    prior = record.get("grasp_prior")
    if isinstance(prior, dict):
        for key in ("path", "grasp_prior_path", "prior_path"):
            value = prior.get(key)
            if value:
                candidates.append(_resolve_path(str(value), base_dir=asset_root))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0] if candidates else None


def _load_graspgen_object_scale_from_prior(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            if "object_scale" in data.files:
                scale = float(_npz_scalar(data["object_scale"]))
                if math.isfinite(scale) and scale > 0.0:
                    return scale
            if "metadata_json" in data.files:
                metadata = json.loads(str(_npz_scalar(data["metadata_json"])))
                if "object_scale" in metadata:
                    scale = float(metadata["object_scale"])
                    if math.isfinite(scale) and scale > 0.0:
                        return scale
    except Exception:
        return None
    return None


def _normalize_graspgen_record_scale(
    record: dict[str, object],
    *,
    asset_root: Path,
    require_prior_scale: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    uuid = str(record.get("uuid") or record.get("name") or "")
    prior_path = _resolve_record_grasp_prior_path(record, asset_root=asset_root)
    prior_scale = _load_graspgen_object_scale_from_prior(prior_path)
    record_has_scale = record.get("scale") is not None
    if prior_scale is not None:
        scale = float(prior_scale)
        scale_source = "grasp_prior.object_scale"
    elif require_prior_scale:
        raise ValueError(f"Could not read GraspGen object_scale for {uuid} from prior: {prior_path}")
    elif record_has_scale:
        scale = float(record["scale"])
        scale_source = "manifest.scale"
    else:
        scale = 1.0
        scale_source = "default"

    normalized = dict(record)
    normalized["scale"] = float(scale)
    normalized["scale_source"] = scale_source
    if prior_path is not None:
        normalized["grasp_prior_path"] = str(prior_path)
        prior = dict(normalized.get("grasp_prior") or {})
        prior["path"] = str(prior_path)
        prior["scale_source"] = scale_source
        normalized["grasp_prior"] = prior
    if "bounds_min" in normalized and "bounds_max" in normalized:
        bounds_min = [float(v) for v in normalized["bounds_min"]]
        bounds_max = [float(v) for v in normalized["bounds_max"]]
        scaled_bounds_min = [float(scale) * value for value in bounds_min]
        scaled_bounds_max = [float(scale) * value for value in bounds_max]
        normalized["scaled_bounds_min"] = scaled_bounds_min
        normalized["scaled_bounds_max"] = scaled_bounds_max
        normalized["scaled_half_extents"] = [
            0.5 * (scaled_bounds_max[axis] - scaled_bounds_min[axis]) for axis in range(3)
        ]
    summary = {
        "uuid": uuid,
        "scale": float(scale),
        "scale_source": scale_source,
        "grasp_prior_path": "" if prior_path is None else str(prior_path),
    }
    return normalized, summary


COMMON_TABLETOP_KEYWORDS = (
    "apple",
    "bag",
    "bagel",
    "bar",
    "bottle",
    "bowl",
    "box",
    "can",
    "candy",
    "container",
    "cup",
    "dish",
    "food",
    "fork",
    "fruit",
    "jar",
    "knife",
    "marker",
    "mug",
    "pen",
    "pepper",
    "plate",
    "remote",
    "scissors",
    "snack",
    "soap",
    "spoon",
    "sponge",
    "teapot",
    "toothbrush",
    "vase",
)
EXCLUDED_TABLETOP_KEYWORDS = ("animal", "building", "car", "chair", "person", "plant", "room", "statue", "tree", "vehicle")


def _collect_text(value: object, fragments: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        fragments.append(value)
    elif isinstance(value, (int, float, bool)):
        fragments.append(str(value))
    elif isinstance(value, dict):
        for nested_value in value.values():
            _collect_text(nested_value, fragments)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            _collect_text(nested_value, fragments)


def _record_text(record: dict[str, object]) -> str:
    fragments: list[str] = []
    for key in (
        "name",
        "title",
        "category",
        "categories",
        "class",
        "labels",
        "tags",
        "description",
        "object_name",
        "synset",
        "metadata",
        "annotations",
    ):
        _collect_text(record.get(key), fragments)
    if not fragments:
        fragments.append(str(record.get("uuid") or ""))
    return " ".join(fragments).lower()


def _record_xy_radius(record: dict[str, object]) -> float:
    if record.get("scaled_bounds_min") is not None and record.get("scaled_bounds_max") is not None:
        bounds_min = [float(v) for v in record["scaled_bounds_min"]]
        bounds_max = [float(v) for v in record["scaled_bounds_max"]]
        return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))
    if record.get("scaled_half_extents") is not None:
        half_extents = [float(v) for v in record["scaled_half_extents"]]
        return max(half_extents[0], half_extents[1])
    if record.get("bounds_min") is not None and record.get("bounds_max") is not None:
        scale = float(record.get("scale", 1.0))
        bounds_min = [scale * float(v) for v in record["bounds_min"]]
        bounds_max = [scale * float(v) for v in record["bounds_max"]]
        return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))
    if record.get("half_extents") is not None:
        scale = float(record.get("scale", 1.0))
        half_extents = [scale * float(v) for v in record["half_extents"]]
        return max(half_extents[0], half_extents[1])
    return 1.0


def _record_height(record: dict[str, object]) -> float:
    if record.get("scaled_bounds_min") is not None and record.get("scaled_bounds_max") is not None:
        return float(record["scaled_bounds_max"][2]) - float(record["scaled_bounds_min"][2])
    if record.get("scaled_half_extents") is not None:
        return 2.0 * float(record["scaled_half_extents"][2])
    if record.get("bounds_min") is not None and record.get("bounds_max") is not None:
        scale = float(record.get("scale", 1.0))
        return scale * (float(record["bounds_max"][2]) - float(record["bounds_min"][2]))
    if record.get("half_extents") is not None:
        return 2.0 * float(record.get("scale", 1.0)) * float(record["half_extents"][2])
    return 1.0


def _prioritize_tabletop_objaverse_records(records: list[object]) -> list[object]:
    def sort_key(item: tuple[int, object]) -> tuple[float, float, int]:
        index, record = item
        if not isinstance(record, dict):
            return (float("inf"), float("inf"), index)
        text = _record_text(record)
        common_hits = sum(1 for keyword in COMMON_TABLETOP_KEYWORDS if keyword in text)
        excluded_hits = sum(1 for keyword in EXCLUDED_TABLETOP_KEYWORDS if keyword in text)
        radius = _record_xy_radius(record)
        height = _record_height(record)
        score = 50.0 * common_hits - 75.0 * excluded_hits
        if radius <= 0.14:
            score += 10.0
        else:
            score -= 80.0 * (radius - 0.14)
        score -= 3.0 * abs(radius - 0.07)
        if height > 0.28:
            score -= 2.0 * (height - 0.28)
        return (-score, radius, index)

    return [record for _, record in sorted(enumerate(records), key=sort_key)]


def _first_existing_objaverse_mesh(record: dict[str, object], *, asset_root: Path, mesh_source: str) -> Path:
    candidates: list[Path] = []
    raw_object_path = record.get("raw_object_path")
    uuid = str(record.get("uuid") or record.get("name") or "")
    mesh_source = str(mesh_source or "auto")
    if uuid and mesh_source in ("auto", "glb"):
        candidates.append(asset_root / "raw_objaverse" / f"{uuid}.glb")
    if raw_object_path and mesh_source in ("auto", "obj"):
        candidates.append(_resolve_path(str(raw_object_path), base_dir=asset_root))
    if uuid and mesh_source in ("auto", "obj"):
        candidates.extend(
            [
                asset_root / "raw_objaverse" / f"{uuid}.obj",
            ]
        )
    if uuid and mesh_source in ("auto", "urdf_obj"):
        candidates.append(asset_root / "urdf" / uuid / "visual_model.obj")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not find raw Objaverse mesh for manifest record {uuid!r}")


def _load_scaled_trimesh(mesh_path: Path, *, scale: float):
    import trimesh

    loaded = trimesh.load(mesh_path, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [geom for geom in loaded.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"Scene contains no meshes: {mesh_path}")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unsupported trimesh load result for {mesh_path}: {type(loaded).__name__}")
    mesh = mesh.copy()
    mesh.apply_scale(float(scale))
    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        raise ValueError(f"Mesh has no vertices/faces after scaling: {mesh_path}")
    return mesh


def _write_stable_pose_cache(
    *,
    uuid: str,
    mesh_path: Path,
    scale: float,
    cache_dir: Path,
    pose_count: int,
    mesh_mode: str,
) -> dict[str, object]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{uuid}.npz"
    pose_count = max(int(pose_count), 1)
    if cache_path.is_file():
        try:
            with np.load(cache_path, allow_pickle=False) as data:
                cached_scale = float(_npz_scalar(data["scale"])) if "scale" in data.files else None
                cached_pose_count = int(_npz_scalar(data["pose_count"])) if "pose_count" in data.files else 0
            if cached_scale is not None and abs(cached_scale - float(scale)) < 1.0e-8 and cached_pose_count >= pose_count:
                return {
                    "uuid": uuid,
                    "path": str(cache_path),
                    "scale": float(scale),
                    "pose_count": int(cached_pose_count),
                    "mesh_mode": str(mesh_mode),
                    "cached": True,
                }
        except Exception:
            pass

    mesh = _load_scaled_trimesh(mesh_path, scale=float(scale))
    if str(mesh_mode) == "visual":
        pose_mesh = mesh.copy()
    else:
        pose_mesh = mesh.convex_hull
        pose_mesh.merge_vertices()
        pose_mesh.remove_unreferenced_vertices()
    transforms, probabilities = pose_mesh.compute_stable_poses(sigma=0.0, n_samples=1, threshold=0.0)
    if len(transforms) == 0:
        raise RuntimeError(f"trimesh returned no stable poses for {uuid}")
    order = np.argsort(np.asarray(probabilities))[::-1]
    transforms = np.asarray(transforms, dtype=np.float64)[order]
    probabilities = np.asarray(probabilities, dtype=np.float64)[order]
    rotations = transforms[:, :3, :3]
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    root_z_offsets = []
    for rotation in rotations:
        rotated = vertices @ rotation.T
        root_z_offsets.append(-float(rotated[:, 2].min()))
    root_z_offsets = np.asarray(root_z_offsets, dtype=np.float64)
    np.savez_compressed(
        cache_path,
        uuid=np.asarray(uuid),
        scale=np.asarray(float(scale), dtype=np.float32),
        mesh_path=np.asarray(str(mesh_path)),
        stable_pose_mesh_mode=np.asarray(str(mesh_mode)),
        transforms=transforms,
        rotations=rotations,
        probabilities=probabilities,
        vertices=vertices,
        root_z_offsets=root_z_offsets,
        pose_count=np.asarray(min(pose_count, len(transforms)), dtype=np.int64),
    )
    return {
        "uuid": uuid,
        "path": str(cache_path),
        "scale": float(scale),
        "pose_count": int(min(pose_count, len(transforms))),
        "num_stable_poses": int(len(transforms)),
        "mesh_mode": str(mesh_mode),
        "visual_vertex_count": int(len(mesh.vertices)),
        "visual_face_count": int(len(mesh.faces)),
        "pose_vertex_count": int(len(pose_mesh.vertices)),
        "pose_face_count": int(len(pose_mesh.faces)),
        "cached": False,
    }


def _prepare_textured_objaverse_manifest(
    *,
    manifest_path: Path,
    output_dir: Path,
    max_assets: int | None,
    mesh_source: str,
    make_instanceable: bool,
    force_conversion: bool,
    collision_approximation: str,
    prioritize_common_tabletop: bool,
    require_graspgen_prior_scale: bool,
    max_xy_radius: float | None,
    stable_pose_cache_dir: Path | None,
    stable_pose_count: int,
    stable_pose_mesh_mode: str,
) -> tuple[Path, dict[str, object]]:
    manifest_path = manifest_path.expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    object_records = payload.get("objects")
    if not isinstance(object_records, list) or not object_records:
        raise ValueError(f"Expected non-empty objects list in Objaverse manifest: {manifest_path}")

    asset_root_value = str(payload.get("asset_root") or ".")
    asset_root = _resolve_path(asset_root_value, base_dir=manifest_path.parent)
    scale_summaries: list[dict[str, object]] = []
    normalized_records: list[dict[str, object]] = []
    for record in object_records:
        if not isinstance(record, dict):
            continue
        normalized, scale_summary = _normalize_graspgen_record_scale(
            record,
            asset_root=asset_root,
            require_prior_scale=bool(require_graspgen_prior_scale),
        )
        normalized_records.append(normalized)
        scale_summaries.append(scale_summary)
    object_records = normalized_records
    size_filtered_count = 0
    max_xy_radius_value = None if max_xy_radius is None else float(max_xy_radius)
    if max_xy_radius_value is not None and max_xy_radius_value > 0.0:
        before_count = len(object_records)
        object_records = [record for record in object_records if _record_xy_radius(record) <= max_xy_radius_value]
        size_filtered_count = before_count - len(object_records)
        if not object_records:
            raise ValueError(f"No Objaverse records remain after max_xy_radius={max_xy_radius_value} filtering")
    if prioritize_common_tabletop:
        object_records = _prioritize_tabletop_objaverse_records(object_records)
    limit = len(object_records) if max_assets is None or int(max_assets) <= 0 else min(int(max_assets), len(object_records))
    output_dir.mkdir(parents=True, exist_ok=True)
    usd_root = output_dir / "USD"
    converted_records: list[dict[str, object]] = []
    converted_meshes: list[dict[str, object]] = []
    stable_pose_summaries: list[dict[str, object]] = []

    collision_approximation = str(collision_approximation)
    collision_props = sim_utils.CollisionPropertiesCfg(
        collision_enabled=collision_approximation != "none",
        contact_offset=0.004,
        rest_offset=0.0,
    )
    for record_idx, record in enumerate(object_records[:limit]):
        if not isinstance(record, dict):
            raise ValueError(f"Objaverse manifest record is not a mapping: {record!r}")
        uuid = str(record.get("uuid") or record.get("name") or f"object_{len(converted_records)}")
        mesh_path = _first_existing_objaverse_mesh(record, asset_root=asset_root, mesh_source=str(mesh_source))
        usd_dir = usd_root / uuid
        usd_path = usd_dir / f"{uuid}.usd"
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_conversion_start",
                    "idx": int(record_idx),
                    "uuid": uuid,
                    "mesh_path": str(mesh_path),
                    "mesh_size": int(mesh_path.stat().st_size),
                    "usd_path": str(usd_path),
                    "collision_approximation": collision_approximation,
                    "make_instanceable": bool(make_instanceable),
                }
            ),
            flush=True,
        )
        converted_usd_path: Path | None = None
        try:
            if mesh_path.suffix.lower() in (".glb", ".gltf"):
                converted_usd_path = _convert_glb_to_usd_direct(
                    mesh_path=mesh_path,
                    usd_path=usd_path,
                    collision_props=collision_props,
                    collision_approximation=collision_approximation,
                )
            else:
                converter_cfg = MeshConverterCfg(
                    asset_path=str(mesh_path),
                    usd_dir=str(usd_dir),
                    usd_file_name=usd_path.name,
                    force_usd_conversion=bool(force_conversion),
                    make_instanceable=bool(make_instanceable),
                    collision_props=collision_props,
                    collision_approximation=str(collision_approximation),
                )
                converter = MeshConverter(converter_cfg)
                converted_usd_path = Path(converter.usd_path)
        except BaseException as exc:
            print(
                json.dumps(
                    {
                        "event": "objaverse_textured_conversion_failed",
                        "idx": int(record_idx),
                        "uuid": uuid,
                        "mesh_path": str(mesh_path),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                ),
                flush=True,
            )
            raise
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_conversion_done",
                    "idx": int(record_idx),
                    "uuid": uuid,
                    "usd_path": str(converted_usd_path),
                }
            ),
            flush=True,
        )
        textured_record = dict(record)
        textured_record["usd_path"] = os.path.relpath(converted_usd_path, output_dir)
        textured_record["raw_object_path"] = str(mesh_path)
        textured_record["source_usd_path"] = str(record.get("usd_path") or "")
        if stable_pose_cache_dir is not None:
            stable_summary = _write_stable_pose_cache(
                uuid=uuid,
                mesh_path=mesh_path,
                scale=float(textured_record["scale"]),
                cache_dir=stable_pose_cache_dir,
                pose_count=int(stable_pose_count),
                mesh_mode=str(stable_pose_mesh_mode),
            )
            textured_record["stable_pose_path"] = str(stable_summary["path"])
            stable_pose_summaries.append(stable_summary)
        converted_records.append(textured_record)
        converted_meshes.append(
            {
                "uuid": uuid,
                "mesh_path": str(mesh_path),
                "usd_path": str(converted_usd_path),
            }
        )

    textured_manifest = output_dir / "manifest.json"
    textured_payload = {
        "format": "dextrah_textured_objaverse_manifest_v1",
        "asset_root": ".",
        "source_manifest_path": str(manifest_path),
        "source_dataset": payload.get("source_dataset", "objaverse"),
        "selected_uuid_count": len(converted_records),
        "objects": converted_records,
        "conversion": {
            "converter": "isaaclab.sim.converters.MeshConverter",
            "collision_approximation": str(collision_approximation),
            "mesh_source": str(mesh_source),
            "make_instanceable": bool(make_instanceable),
            "force_usd_conversion": bool(force_conversion),
        },
    }
    textured_manifest.write_text(json.dumps(textured_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "source_manifest_path": str(manifest_path),
        "textured_manifest_path": str(textured_manifest),
        "asset_root": str(asset_root),
        "output_dir": str(output_dir),
        "num_objects": len(converted_records),
        "prioritize_common_tabletop": bool(prioritize_common_tabletop),
        "require_graspgen_prior_scale": bool(require_graspgen_prior_scale),
        "max_xy_radius": max_xy_radius_value,
        "size_filtered_count": int(size_filtered_count),
        "scale_summaries": scale_summaries[:limit],
        "stable_pose_cache_dir": "" if stable_pose_cache_dir is None else str(stable_pose_cache_dir),
        "stable_pose_summaries": stable_pose_summaries,
        "converted_meshes": converted_meshes,
    }
    return textured_manifest, summary


def _convert_glb_to_usd_direct(
    *,
    mesh_path: Path,
    usd_path: Path,
    collision_props: sim_utils.CollisionPropertiesCfg,
    collision_approximation: str,
) -> Path:
    usd_path.parent.mkdir(parents=True, exist_ok=True)
    enable_extension("omni.kit.asset_converter")
    import omni.kit.asset_converter

    converter_context = omni.kit.asset_converter.AssetConverterContext()
    converter_context.ignore_materials = False
    converter_context.ignore_animations = True
    converter_context.ignore_camera = True
    converter_context.ignore_light = True
    converter_context.merge_all_meshes = True
    converter_context.use_meter_as_world_unit = True
    converter_context.baking_scales = True
    converter_context.use_double_precision_to_usd_transform_op = True
    converter_task = omni.kit.asset_converter.get_instance().create_converter_task(
        str(mesh_path),
        str(usd_path),
        None,
        converter_context,
    )
    success = asyncio.get_event_loop().run_until_complete(converter_task.wait_until_finished())
    if not success:
        raise RuntimeError(
            f"Failed to convert {mesh_path} to USD. Error: {converter_task.get_error_message()}"
        )
    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"Failed to open converted USD: {usd_path}")
    if not stage.GetDefaultPrim().IsValid():
        root_prims = [prim for prim in stage.GetPseudoRoot().GetChildren() if prim.IsValid()]
        if not root_prims:
            raise RuntimeError(f"Converted USD has no root prims: {usd_path}")
        stage.SetDefaultPrim(root_prims[0])
    default_prim = stage.GetDefaultPrim()
    sim_schemas.define_rigid_body_properties(
        prim_path=default_prim.GetPath(),
        cfg=sim_utils.RigidBodyPropertiesCfg(rigid_body_enabled=True, kinematic_enabled=False, disable_gravity=False),
        stage=stage,
    )
    sim_schemas.define_mass_properties(
        prim_path=default_prim.GetPath(),
        cfg=sim_utils.MassPropertiesCfg(density=100.0),
        stage=stage,
    )
    if str(collision_approximation) != "none":
        for prim in stage.Traverse():
            if prim.GetTypeName() == "Mesh":
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
                mesh_collision_api.GetApproximationAttr().Set(str(collision_approximation))
                sim_schemas.define_collision_properties(
                    prim_path=prim.GetPath(),
                    cfg=collision_props,
                    stage=stage,
                )
    stage.Save()
    return usd_path


def _capture_steps_for_video(settle_steps: int, target_frame_count: int) -> tuple[int, set[int]]:
    if target_frame_count <= 1:
        return max(int(settle_steps), 0), set()
    settle_steps = max(int(settle_steps), target_frame_count - 1)
    raw_steps = [int(round(value)) for value in np.linspace(1, settle_steps, target_frame_count - 1)]
    steps: list[int] = []
    used: set[int] = set()
    for step in raw_steps:
        step = min(max(int(step), 1), settle_steps)
        if step not in used:
            steps.append(step)
            used.add(step)
    if len(steps) < target_frame_count - 1:
        for step in range(1, settle_steps + 1):
            if step not in used:
                steps.append(step)
                used.add(step)
            if len(steps) >= target_frame_count - 1:
                break
    return settle_steps, set(sorted(steps[: target_frame_count - 1]))


def _root_snapshot(task_env) -> dict[str, object]:
    env_origins = task_env.scene.env_origins
    snapshot: dict[str, object] = {
        "target_root_pos": _tensor_list(task_env._cube.data.root_pos_w - env_origins),
        "target_root_quat": _tensor_list(task_env._cube.data.root_quat_w),
    }
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    if clutter_objects:
        clutter_pos = []
        clutter_quat = []
        for clutter_object in clutter_objects:
            clutter_pos.append(_tensor_list(clutter_object.data.root_pos_w - env_origins))
            clutter_quat.append(_tensor_list(clutter_object.data.root_quat_w))
        snapshot["clutter_root_pos_by_slot"] = clutter_pos
        snapshot["clutter_root_quat_by_slot"] = clutter_quat
    return snapshot


def _infer_raw_objaverse_path(path: str) -> str:
    value = Path(str(path))
    uuid = value.stem
    parts = list(value.parts)
    try:
        usd_idx = parts.index("USD")
    except ValueError:
        return str(value.with_suffix(".obj"))
    return str(Path(*parts[:usd_idx], "raw_objaverse", f"{uuid}.obj"))


def _copy_asset_mesh(output_dir: Path, asset: dict[str, object], label: str) -> dict[str, object]:
    candidates: list[Path] = []
    for key in ("raw_object_path", "source_raw_object_path", "mesh_path"):
        value = asset.get(key)
        if value:
            candidates.append(Path(str(value)).expanduser())
    usd_path = str(asset.get("usd_path") or "")
    if usd_path:
        candidates.append(Path(_infer_raw_objaverse_path(usd_path)).expanduser())
    existing = [path for path in candidates if path.is_file()]
    summary: dict[str, object] = {
        "label": label,
        "source_candidates": [str(path) for path in candidates],
        "copied": False,
    }
    if not existing:
        return summary
    source = existing[0].resolve()
    asset_dir = output_dir / "stable_scene_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix or ".obj"
    uuid = str(asset.get("uuid") or source.stem or label)
    dest = asset_dir / f"{label}_{uuid}{suffix}"
    if source.resolve() != dest.resolve():
        shutil.copy2(source, dest)
    summary.update(
        {
            "copied": True,
            "source_path": str(source),
            "copy_path": str(dest),
            "copy_rel": os.path.relpath(dest, output_dir),
            "copy_size": int(dest.stat().st_size),
        }
    )
    return summary


def _asset_record_for_env(task_env, env_id: int) -> dict[str, object]:
    assets = list(getattr(task_env, "_object_assets", []))
    indices = getattr(task_env, "object_asset_index", None)
    if not assets or indices is None:
        return {}
    return dict(assets[int(indices[env_id].item())])


def _clutter_asset_record_for_slot(task_env, env_id: int, slot_idx: int) -> dict[str, object]:
    assets = list(getattr(task_env, "_tabletop_clutter_assets", []))
    indices = getattr(task_env, "tabletop_clutter_asset_index", None)
    if not assets or indices is None:
        return {}
    return dict(assets[int(indices[env_id, slot_idx].item())])


def _robot_state_snapshot(task_env) -> dict[str, object]:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        return {"enabled": False}
    joint_names = list(getattr(robot.data, "joint_names", []))
    joint_pos = robot.data.joint_pos.detach().float().cpu()
    joint_vel = robot.data.joint_vel.detach().float().cpu()
    arm_joint_ids = list(getattr(task_env, "arm_joint_ids", []))
    finger_joint_ids = list(getattr(task_env, "finger_joint_ids", []))
    return {
        "enabled": True,
        "joint_names": joint_names,
        "joint_position": joint_pos.tolist(),
        "joint_velocity": joint_vel.tolist(),
        "arm_joint_ids": [int(v) for v in arm_joint_ids],
        "finger_joint_ids": [int(v) for v in finger_joint_ids],
        "arm_joint_names": [joint_names[int(i)] for i in arm_joint_ids if int(i) < len(joint_names)],
        "finger_joint_names": [joint_names[int(i)] for i in finger_joint_ids if int(i) < len(joint_names)],
        "arm_joint_position": joint_pos[:, arm_joint_ids].tolist() if arm_joint_ids else [],
        "finger_joint_position": joint_pos[:, finger_joint_ids].tolist() if finger_joint_ids else [],
    }


def _stable_scene_payload(
    task_env,
    *,
    output_dir: Path,
    task: str,
    seed: int,
    settle_steps: int,
    initial_snapshot: dict[str, object],
    stable_snapshot: dict[str, object],
    initial_velocity_summary: dict[str, object],
    stable_velocity_summary: dict[str, object],
    initial_clearance_summary: dict[str, object] | None,
    stable_clearance_summary: dict[str, object] | None,
) -> dict[str, object]:
    env_id = 0
    target_pos = [float(v) for v in stable_snapshot["target_root_pos"][env_id]]
    target_quat = [float(v) for v in stable_snapshot["target_root_quat"][env_id]]
    target_asset = _asset_record_for_env(task_env, env_id)
    target_mesh_copy = _copy_asset_mesh(output_dir, target_asset, "target") if target_asset else {}

    clutter_entries: list[dict[str, object]] = []
    clutter_positions = stable_snapshot.get("clutter_root_pos_by_slot")
    clutter_quats = stable_snapshot.get("clutter_root_quat_by_slot")
    if isinstance(clutter_positions, list) and isinstance(clutter_quats, list):
        for slot_idx, (slot_positions, slot_quats) in enumerate(zip(clutter_positions, clutter_quats, strict=False)):
            if env_id >= len(slot_positions) or env_id >= len(slot_quats):
                continue
            asset = _clutter_asset_record_for_slot(task_env, env_id, slot_idx)
            root_pos = [float(v) for v in slot_positions[env_id]]
            root_quat = [float(v) for v in slot_quats[env_id]]
            clutter_entries.append(
                {
                    "slot_idx": int(slot_idx),
                    "asset": _jsonable(asset),
                    "root_position": root_pos,
                    "root_quat_wxyz": root_quat,
                    "root_transform": _matrix_from_pose_wxyz(root_pos, root_quat),
                }
            )
    bins: dict[str, object] = {}
    for key, method_name in (
        ("source", "_tabletop_source_bin_info"),
        ("goal", "_tabletop_goal_bin_info"),
    ):
        method = getattr(task_env, method_name, None)
        if not callable(method):
            continue
        info = method()
        if info is not None:
            bins[key] = _jsonable(info)

    return {
        "format": "dextrah_stable_scene_v1",
        "task": task,
        "seed": int(seed),
        "settle_steps": int(settle_steps),
        "env_id": int(env_id),
        "sim_dt": float(task_env.sim.cfg.dt),
        "robot": _robot_state_snapshot(task_env),
        "target": {
            "asset": _jsonable(target_asset),
            "mesh_copy": target_mesh_copy,
            "root_position": target_pos,
            "root_quat_wxyz": target_quat,
            "root_transform": _matrix_from_pose_wxyz(target_pos, target_quat),
        },
        "clutter": clutter_entries,
        "bins": bins,
        "snapshots": {
            "initial": initial_snapshot,
            "stable": stable_snapshot,
        },
        "velocity_summary": {
            "initial": initial_velocity_summary,
            "stable": stable_velocity_summary,
        },
        "clearance_summary": {
            "initial": initial_clearance_summary,
            "stable": stable_clearance_summary,
        },
        "yam_policy_scene_randomization": _jsonable(
            getattr(task_env.cfg, "yam_policy_scene_randomization_summary", {"enabled": False})
        ),
        "multi_object_asset_summary": task_env.multi_object_asset_summary()
        if hasattr(task_env, "multi_object_asset_summary")
        else None,
        "tabletop_clutter_summary": task_env.tabletop_clutter_summary()
        if hasattr(task_env, "tabletop_clutter_summary")
        else None,
    }


def _load_stable_scene(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("format") != "dextrah_stable_scene_v1":
        raise ValueError(f"Expected dextrah_stable_scene_v1 payload in {path}")
    return payload


def _stable_scene_asset_record(asset: dict[str, object]) -> dict[str, object] | None:
    uuid = str(asset.get("uuid") or "")
    usd_path = str(asset.get("usd_path") or "")
    primitive_shape = str(asset.get("primitive_shape") or "")
    if not uuid or (not usd_path and not primitive_shape):
        return None

    record: dict[str, object] = {
        "uuid": uuid,
        "name": str(asset.get("name") or uuid),
    }
    if usd_path:
        record["usd_path"] = usd_path
    for key in (
        "metadata_text",
        "raw_object_path",
        "primitive_shape",
        "primitive_radius",
        "primitive_size",
        "primitive_color",
        "scale",
        "usd_spawn_scale",
        "usd_root_scale",
        "scaled_half_extents",
        "scaled_bounds_min",
        "scaled_bounds_max",
        "grasp_size",
        "grasp_prior_path",
        "stable_pose_path",
    ):
        value = asset.get(key)
        if value not in (None, ""):
            record[key] = value
    return record


def _write_stable_scene_asset_manifest(
    records: list[dict[str, object]],
    output_dir: Path,
    *,
    filename: str,
    source: str,
) -> Path | None:
    if not records:
        return None
    manifest = {
        "asset_root": "/",
        "objects": records,
        "source": source,
    }
    manifest_path = output_dir / filename
    manifest_path.write_text(json.dumps(_jsonable(manifest), indent=2), encoding="utf-8")
    return manifest_path


def _stable_scene_asset_manifests(stable_scene: dict[str, object], output_dir: Path) -> dict[str, object]:
    target = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else {}
    target_asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
    target_record = _stable_scene_asset_record(target_asset)

    clutter_records: list[dict[str, object]] = []
    clutter = stable_scene.get("clutter") if isinstance(stable_scene.get("clutter"), list) else []
    for entry in clutter:
        if not isinstance(entry, dict):
            continue
        asset = entry.get("asset") if isinstance(entry.get("asset"), dict) else {}
        record = _stable_scene_asset_record(asset)
        if record is not None:
            clutter_records.append(record)

    target_manifest_path = (
        _write_stable_scene_asset_manifest(
            [target_record],
            output_dir,
            filename="stable_scene_target_manifest.json",
            source="stable_scene_target",
        )
        if target_record is not None
        else None
    )
    clutter_manifest_path = _write_stable_scene_asset_manifest(
        clutter_records,
        output_dir,
        filename="stable_scene_clutter_manifest.json",
        source="stable_scene_clutter",
    )
    return {
        "target_manifest_path": target_manifest_path,
        "target_uuid": "" if target_record is None else str(target_record.get("uuid") or ""),
        "clutter_manifest_path": clutter_manifest_path,
        "clutter_uuids": [str(record.get("uuid") or "") for record in clutter_records],
    }


def _restore_robot_state_from_stable_scene(task_env, stable_scene: dict[str, object]) -> dict[str, object]:
    robot = getattr(task_env, "_robot", None)
    robot_payload = stable_scene.get("robot") if isinstance(stable_scene.get("robot"), dict) else {}
    if robot is None or not robot_payload:
        return {"enabled": False, "reason": "missing_robot_or_payload"}
    joint_positions = robot_payload.get("joint_position")
    if not isinstance(joint_positions, list) or not joint_positions:
        return {"enabled": False, "reason": "missing_joint_position"}
    q = torch.as_tensor(joint_positions, dtype=robot.data.joint_pos.dtype, device=task_env.device)
    if q.ndim != 2:
        return {"enabled": False, "reason": "bad_joint_position_shape", "shape": list(q.shape)}
    if q.shape[0] == 1 and int(task_env.num_envs) > 1:
        q = q.repeat(int(task_env.num_envs), 1)
    if q.shape != robot.data.joint_pos.shape:
        return {
            "enabled": False,
            "reason": "joint_position_shape_mismatch",
            "payload_shape": list(q.shape),
            "env_shape": list(robot.data.joint_pos.shape),
        }
    env_ids = robot._ALL_INDICES
    q = torch.clamp(q, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)
    qd = torch.zeros_like(q)
    robot.write_joint_state_to_sim(q, qd, env_ids=env_ids)
    robot.set_joint_position_target(q, env_ids=env_ids)
    if hasattr(task_env, "robot_dof_targets"):
        task_env.robot_dof_targets[env_ids] = q
    if hasattr(task_env, "arm_joint_pos_target"):
        task_env.arm_joint_pos_target[env_ids] = q[:, task_env.arm_joint_ids]
    if hasattr(task_env, "finger_joint_pos_target"):
        task_env.finger_joint_pos_target[env_ids] = q[:, task_env.finger_joint_ids]
    return {"enabled": True, "joint_position": _tensor_list(q)}


def _restore_stable_scene(task_env, stable_scene: dict[str, object]) -> dict[str, object]:
    snapshots = stable_scene.get("snapshots") if isinstance(stable_scene.get("snapshots"), dict) else {}
    stable_snapshot = snapshots.get("stable") if isinstance(snapshots.get("stable"), dict) else None
    if stable_snapshot is None:
        return {"enabled": False, "reason": "missing_stable_snapshot"}
    _restore_root_snapshot(task_env, stable_snapshot)
    robot_restore = _restore_robot_state_from_stable_scene(task_env, stable_scene)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()
    return {"enabled": True, "robot": robot_restore}


def _restore_root_snapshot(task_env, snapshot: dict[str, object]) -> None:
    env_ids = torch.arange(int(task_env.num_envs), dtype=torch.long, device=task_env.device)
    env_origins = task_env.scene.env_origins

    def _pose_from_lists(pos_list: object, quat_list: object) -> tuple[torch.Tensor, torch.Tensor]:
        pos = torch.as_tensor(pos_list, dtype=torch.float32, device=task_env.device)
        quat = torch.as_tensor(quat_list, dtype=torch.float32, device=task_env.device)
        if pos.ndim != 2 or quat.ndim != 2:
            raise ValueError("Root snapshot entries must have shape (num_envs, dims)")
        return pos, quat

    def _state_from_pose(pos: torch.Tensor, quat: torch.Tensor) -> torch.Tensor:
        state = torch.zeros((pos.shape[0], 13), dtype=torch.float32, device=task_env.device)
        state[:, 0:3] = pos + env_origins[env_ids]
        state[:, 3:7] = quat
        return state

    zero_vel = torch.zeros((int(task_env.num_envs), 6), dtype=torch.float32, device=task_env.device)
    target_pos, target_quat = _pose_from_lists(snapshot["target_root_pos"], snapshot["target_root_quat"])
    target_state = _state_from_pose(target_pos, target_quat)
    task_env._cube.write_root_state_to_sim(target_state, env_ids=env_ids)
    task_env._cube.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
    sync_target_roots = getattr(task_env, "_set_object_asset_root_pose", None)
    if callable(sync_target_roots):
        sync_target_roots(env_ids, target_pos, target_quat)

    clutter_positions = snapshot.get("clutter_root_pos_by_slot")
    clutter_quats = snapshot.get("clutter_root_quat_by_slot")
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    sync_clutter_roots = getattr(task_env, "_set_tabletop_clutter_asset_root_pose", None)
    if isinstance(clutter_positions, list) and isinstance(clutter_quats, list):
        for slot_idx, (clutter_object, slot_pos, slot_quat) in enumerate(
            zip(clutter_objects, clutter_positions, clutter_quats, strict=False)
        ):
            slot_pos_tensor, slot_quat_tensor = _pose_from_lists(slot_pos, slot_quat)
            slot_state = _state_from_pose(slot_pos_tensor, slot_quat_tensor)
            clutter_object.write_root_state_to_sim(slot_state, env_ids=env_ids)
            clutter_object.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
            if callable(sync_clutter_roots):
                sync_clutter_roots(env_ids, slot_idx, slot_pos_tensor, slot_quat_tensor)

    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    if callable(sync_target_roots):
        sync_target_roots(env_ids, target_pos, target_quat)
    if callable(sync_clutter_roots) and isinstance(clutter_positions, list) and isinstance(clutter_quats, list):
        for slot_idx, (slot_pos, slot_quat) in enumerate(zip(clutter_positions, clutter_quats, strict=False)):
            slot_pos_tensor, slot_quat_tensor = _pose_from_lists(slot_pos, slot_quat)
            sync_clutter_roots(env_ids, slot_idx, slot_pos_tensor, slot_quat_tensor)


def _set_target_root_pose_env(task_env, pos_env: torch.Tensor, quat_wxyz: torch.Tensor) -> None:
    env_ids = torch.arange(int(task_env.num_envs), dtype=torch.long, device=task_env.device)
    env_origins = task_env.scene.env_origins
    pos = torch.as_tensor(pos_env, dtype=torch.float32, device=task_env.device)
    quat = torch.as_tensor(quat_wxyz, dtype=torch.float32, device=task_env.device)
    if pos.ndim == 1:
        pos = pos.unsqueeze(0)
    if quat.ndim == 1:
        quat = quat.unsqueeze(0)
    state = torch.zeros((int(task_env.num_envs), 13), dtype=torch.float32, device=task_env.device)
    state[:, 0:3] = pos + env_origins[env_ids]
    state[:, 3:7] = quat
    zero_vel = torch.zeros((int(task_env.num_envs), 6), dtype=torch.float32, device=task_env.device)
    task_env._cube.write_root_state_to_sim(state, env_ids=env_ids)
    task_env._cube.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
    sync_target_roots = getattr(task_env, "_set_object_asset_root_pose", None)
    if callable(sync_target_roots):
        sync_target_roots(env_ids, pos, quat)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()


def _spawn_visual_object_overlay(task_env, snapshot: dict[str, object], *, z_offset: float = 0.0) -> list[dict[str, object]]:
    env_origins = task_env.scene.env_origins.detach().float().cpu().numpy()
    spawned: list[dict[str, object]] = []

    def _spawn(path: str, asset: dict[str, object], pos, quat, env_id: int, label: str) -> None:
        world_pos = np.asarray(pos, dtype=np.float64) + env_origins[env_id]
        world_pos[2] += float(z_offset)
        world_quat = tuple(float(v) for v in quat)
        scale = float(asset["scale"])
        cfg = sim_utils.UsdFileCfg(
            usd_path=str(asset["usd_path"]),
            scale=(scale, scale, scale),
        )
        cfg.func(path, cfg, translation=tuple(float(v) for v in world_pos), orientation=world_quat)
        spawned.append(
            {
                "label": label,
                "env_id": int(env_id),
                "path": path,
                "uuid": str(asset.get("uuid") or ""),
                "usd_path": str(asset["usd_path"]),
                "scale": scale,
                "translation": [float(v) for v in world_pos],
                "orientation": [float(v) for v in world_quat],
            }
        )

    target_pos = snapshot.get("target_root_pos")
    target_quat = snapshot.get("target_root_quat")
    object_assets = list(getattr(task_env, "_object_assets", []))
    if isinstance(target_pos, list) and isinstance(target_quat, list) and object_assets:
        object_indices = getattr(task_env, "object_asset_index", None)
        for env_id, (pos, quat) in enumerate(zip(target_pos, target_quat, strict=False)):
            asset_idx = int(object_indices[env_id].item()) if object_indices is not None else 0
            asset = object_assets[asset_idx]
            _spawn(f"/World/VisualObjectOverlay/env_{env_id}/target", asset, pos, quat, env_id, "target")

    clutter_positions = snapshot.get("clutter_root_pos_by_slot")
    clutter_quats = snapshot.get("clutter_root_quat_by_slot")
    clutter_assets = list(getattr(task_env, "_tabletop_clutter_assets", []))
    clutter_indices = getattr(task_env, "tabletop_clutter_asset_index", None)
    if isinstance(clutter_positions, list) and isinstance(clutter_quats, list) and clutter_assets:
        for slot_idx, (slot_pos, slot_quat) in enumerate(zip(clutter_positions, clutter_quats, strict=False)):
            for env_id, (pos, quat) in enumerate(zip(slot_pos, slot_quat, strict=False)):
                asset_idx = int(clutter_indices[env_id, slot_idx].item()) if clutter_indices is not None else 0
                asset = clutter_assets[asset_idx]
                _spawn(
                    f"/World/VisualObjectOverlay/env_{env_id}/clutter_{slot_idx:02d}",
                    asset,
                    pos,
                    quat,
                    env_id,
                    f"clutter_{slot_idx:02d}",
                )

    task_env.sim.forward()
    return spawned


def _as_matrix4(value: object) -> np.ndarray | None:
    try:
        arr = np.asarray(value, dtype=np.float64)
    except Exception:
        return None
    if arr.shape != (4, 4) or not np.isfinite(arr).all():
        return None
    return arr


def _matrix_to_quat_xyzw(matrix: np.ndarray) -> tuple[float, float, float, float]:
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
            s = math.sqrt(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2]) * 2.0
            qw = (rot[2, 1] - rot[1, 2]) / s
            qx = 0.25 * s
            qy = (rot[0, 1] + rot[1, 0]) / s
            qz = (rot[0, 2] + rot[2, 0]) / s
        elif diag[1] > diag[2]:
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
    quat = np.asarray([qx, qy, qz, qw], dtype=np.float64)
    norm = float(np.linalg.norm(quat))
    if norm > 0.0:
        quat /= norm
    return tuple(float(v) for v in quat)


def _usd_set_xform(
    prim: Usd.Prim,
    translate: tuple[float, float, float],
    *,
    rotate_quat_xyzw: tuple[float, float, float, float] | None = None,
    scale: tuple[float, float, float] | None = None,
) -> None:
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in translate]))
    if rotate_quat_xyzw is not None:
        qx, qy, qz, qw = [float(v) for v in rotate_quat_xyzw]
        xformable.AddOrientOp().Set(Gf.Quatf(qw, qx, qy, qz))
    if scale is not None:
        xformable.AddScaleOp().Set(Gf.Vec3f(*[float(v) for v in scale]))


def _usd_material(
    stage: Usd.Stage,
    path: str,
    color: tuple[float, float, float],
    *,
    roughness: float = 0.42,
    texture_file: str | None = None,
) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    if texture_file:
        st_reader = UsdShade.Shader.Define(stage, f"{path}/PrimvarReader_st")
        st_reader.CreateIdAttr("UsdPrimvarReader_float2")
        st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
        st_reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
        texture = UsdShade.Shader.Define(stage, f"{path}/DiffuseTexture")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(str(texture_file)))
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_reader.ConnectableAPI(), "result")
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(texture.ConnectableAPI(), "rgb")
    else:
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _usd_bind(prim: Usd.Prim, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def _usd_add_box(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: UsdShade.Material,
) -> None:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    _usd_set_xform(prim, center, scale=size)
    _usd_bind(prim, mat)


def _usd_add_quad(
    stage: Usd.Stage,
    path: str,
    points: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
    uvs: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]],
    mat: UsdShade.Material,
) -> None:
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*[float(v) for v in point]) for point in points])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateDoubleSidedAttr(True)
    min_pt = tuple(min(float(point[axis]) for point in points) for axis in range(3))
    max_pt = tuple(max(float(point[axis]) for point in points) for axis in range(3))
    mesh.CreateExtentAttr([Gf.Vec3f(*min_pt), Gf.Vec3f(*max_pt)])
    st = UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar(
        "st",
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying,
    )
    st.Set([Gf.Vec2f(*[float(v) for v in uv]) for uv in uvs])
    _usd_bind(mesh.GetPrim(), mat)


def _usd_add_xy_quad(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    size_xy: tuple[float, float],
    mat: UsdShade.Material,
    *,
    uv_scale: tuple[float, float],
) -> None:
    cx, cy, cz = (float(v) for v in center)
    sx, sy = (float(v) for v in size_xy)
    ux, uy = (float(v) for v in uv_scale)
    points = (
        (cx - 0.5 * sx, cy - 0.5 * sy, cz),
        (cx + 0.5 * sx, cy - 0.5 * sy, cz),
        (cx + 0.5 * sx, cy + 0.5 * sy, cz),
        (cx - 0.5 * sx, cy + 0.5 * sy, cz),
    )
    _usd_add_quad(stage, path, points, ((0.0, 0.0), (ux, 0.0), (ux, uy), (0.0, uy)), mat)


def _apply_yam_policy_dome_light_texture(stage: Usd.Stage, cfg) -> dict[str, object]:
    texture_path = str(getattr(cfg, "yam_policy_dome_light_texture_path", "") or "")
    if not texture_path:
        return {"enabled": False}
    light_prim = stage.GetPrimAtPath("/World/Light")
    if not light_prim.IsValid():
        return {"enabled": False, "texture_path": texture_path, "reason": "missing_world_light"}
    attr = light_prim.GetAttribute("inputs:texture:file")
    if not attr:
        attr = light_prim.CreateAttribute("inputs:texture:file", Sdf.ValueTypeNames.Asset)
    attr.Set(Sdf.AssetPath(texture_path))
    return {"enabled": True, "texture_path": texture_path}


def _spawn_yam_policy_tabletop_surround(task_env) -> dict[str, object]:
    cfg = task_env.cfg
    surround_enabled = bool(getattr(cfg, "yam_policy_tabletop_surround_enabled", False))
    texture_enabled = bool(getattr(cfg, "yam_policy_tabletop_texture_enabled", False))
    walls_enabled = bool(getattr(cfg, "yam_policy_background_walls_enabled", False))
    dome_texture_requested = bool(str(getattr(cfg, "yam_policy_dome_light_texture_path", "") or ""))
    if not (surround_enabled or texture_enabled or walls_enabled or dome_texture_requested):
        return {"enabled": False}
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"enabled": False, "reason": "missing_usd_stage"}
    dome_light_texture = _apply_yam_policy_dome_light_texture(stage, cfg)
    env_origins = task_env.scene.env_origins.detach().float().cpu().numpy()
    size_xy = tuple(float(v) for v in getattr(cfg, "yam_policy_tabletop_surround_size", (1.04, 1.20)))
    if len(size_xy) != 2:
        return {"enabled": False, "reason": "invalid_size", "size": list(size_xy)}
    thickness = float(getattr(cfg, "yam_policy_tabletop_surround_thickness", 0.006))
    top_z = float(cfg.table_surface_z) + float(getattr(cfg, "yam_policy_tabletop_surround_top_z_offset", -0.004))
    center_z = top_z - 0.5 * thickness
    color = tuple(float(v) for v in getattr(cfg, "yam_policy_tabletop_surround_color", (0.48, 0.48, 0.45)))
    roughness = float(getattr(cfg, "yam_policy_tabletop_surround_roughness", 0.72))
    table_texture_path = str(getattr(cfg, "yam_policy_table_texture_path", "") or "")
    table_texture_tiling = float(getattr(cfg, "yam_policy_table_texture_tiling", 2.4))
    looks_root = "/World/Looks/YAMPolicyTabletopSurround"
    UsdGeom.Xform.Define(stage, looks_root)
    surround_mat = _usd_material(stage, f"{looks_root}/surface", color, roughness=roughness)
    table_texture_mat = None
    if table_texture_path:
        table_texture_mat = _usd_material(
            stage,
            f"{looks_root}/table_texture",
            color,
            roughness=float(getattr(cfg, "yam_policy_tabletop_texture_roughness", roughness)),
            texture_file=table_texture_path,
        )
    spawned: list[dict[str, object]] = []
    table_texture_quads: list[dict[str, object]] = []
    if surround_enabled:
        for env_id, origin in enumerate(env_origins):
            center = (
                float(origin[0]) + float(cfg.table_center_x),
                float(origin[1]) + float(cfg.table_center_y),
                float(origin[2]) + center_z,
            )
            path = f"/World/envs/env_{env_id}/YAMPolicyTabletopSurround"
            _usd_add_box(stage, path, center, (size_xy[0], size_xy[1], thickness), surround_mat)
            spawned.append({"env_id": int(env_id), "path": path, "center": [float(v) for v in center]})
            if table_texture_mat is not None:
                quad_center = (center[0], center[1], float(origin[2]) + float(cfg.table_surface_z) + 0.0008)
                quad_path = f"/World/envs/env_{env_id}/YAMPolicyTabletopTexture/full_surface"
                uv_scale = (
                    table_texture_tiling,
                    table_texture_tiling * max(0.1, size_xy[1] / max(size_xy[0], 1e-6)),
                )
                _usd_add_xy_quad(stage, quad_path, quad_center, size_xy, table_texture_mat, uv_scale=uv_scale)
                table_texture_quads.append(
                    {
                        "env_id": int(env_id),
                        "path": quad_path,
                        "center": [float(v) for v in quad_center],
                        "size": [float(v) for v in size_xy],
                        "texture_path": table_texture_path,
                        "uv_scale": [float(v) for v in uv_scale],
                    }
                )

    texture_patches: list[dict[str, object]] = []
    if texture_enabled:
        patches = list(getattr(cfg, "yam_policy_tabletop_texture_patches", []))
        patch_thickness = 0.001
        patch_center_z = float(cfg.table_surface_z) + 0.0005
        texture_roughness = float(getattr(cfg, "yam_policy_tabletop_texture_roughness", 0.78))
        for patch_idx, patch in enumerate(patches):
            if not isinstance(patch, dict):
                continue
            patch_size = patch.get("size", (0.25, 0.04))
            patch_offset = patch.get("center_offset", (0.0, 0.0))
            if len(patch_size) != 2 or len(patch_offset) != 2:
                continue
            patch_color = tuple(float(v) for v in patch.get("color", color))
            patch_mat = _usd_material(stage, f"{looks_root}/texture_{patch_idx:02d}", patch_color, roughness=texture_roughness)
            for env_id, origin in enumerate(env_origins):
                center = (
                    float(origin[0]) + float(cfg.table_center_x) + float(patch_offset[0]),
                    float(origin[1]) + float(cfg.table_center_y) + float(patch_offset[1]),
                    float(origin[2]) + patch_center_z,
                )
                path = f"/World/envs/env_{env_id}/YAMPolicyTabletopTexture/patch_{patch_idx:02d}"
                _usd_add_box(
                    stage,
                    path,
                    center,
                    (float(patch_size[0]), float(patch_size[1]), patch_thickness),
                    patch_mat,
                )
            texture_patches.append(
                {
                    "patch_idx": int(patch_idx),
                    "center_offset": [float(v) for v in patch_offset],
                    "size": [float(v) for v in patch_size],
                    "color": [float(v) for v in patch_color],
                }
            )

    background_walls: list[dict[str, object]] = []
    if walls_enabled:
        wall_distance = float(getattr(cfg, "yam_policy_background_wall_distance", 1.28))
        wall_height = float(getattr(cfg, "yam_policy_background_wall_height", 0.72))
        wall_thickness = float(getattr(cfg, "yam_policy_background_wall_thickness", 0.025))
        wall_color = tuple(float(v) for v in getattr(cfg, "yam_policy_background_wall_color", (0.55, 0.56, 0.54)))
        wall_roughness = float(getattr(cfg, "yam_policy_background_wall_roughness", 0.80))
        wall_mat = _usd_material(stage, f"{looks_root}/background_wall", wall_color, roughness=wall_roughness)
        background_texture_path = str(getattr(cfg, "yam_policy_background_texture_path", "") or "")
        background_texture_tiling = float(getattr(cfg, "yam_policy_background_texture_tiling", 1.4))
        wall_texture_mat = None
        if background_texture_path:
            wall_texture_mat = _usd_material(
                stage,
                f"{looks_root}/background_wall_texture",
                wall_color,
                roughness=wall_roughness,
                texture_file=background_texture_path,
            )
        wall_center_z = float(cfg.table_surface_z) + 0.5 * wall_height
        wall_specs = (
            ("back_y", (0.0, wall_distance, wall_center_z), (2.0 * wall_distance, wall_thickness, wall_height)),
            ("left_x", (-wall_distance, 0.0, wall_center_z), (wall_thickness, 2.0 * wall_distance, wall_height)),
            ("right_x", (wall_distance, 0.0, wall_center_z), (wall_thickness, 2.0 * wall_distance, wall_height)),
        )
        for env_id, origin in enumerate(env_origins):
            for wall_name, wall_offset, wall_size in wall_specs:
                center = (
                    float(origin[0]) + float(cfg.table_center_x) + float(wall_offset[0]),
                    float(origin[1]) + float(cfg.table_center_y) + float(wall_offset[1]),
                    float(origin[2]) + float(wall_offset[2]),
                )
                path = f"/World/envs/env_{env_id}/YAMPolicyBackground/{wall_name}"
                _usd_add_box(stage, path, center, wall_size, wall_mat)
                texture_path = ""
                texture_quad_path = ""
                if wall_texture_mat is not None:
                    base_z = float(origin[2]) + float(cfg.table_surface_z)
                    if wall_name == "back_y":
                        y = center[1] - 0.5 * wall_thickness - 0.001
                        points = (
                            (center[0] - wall_distance, y, base_z),
                            (center[0] + wall_distance, y, base_z),
                            (center[0] + wall_distance, y, base_z + wall_height),
                            (center[0] - wall_distance, y, base_z + wall_height),
                        )
                    else:
                        sign = -1.0 if wall_name == "left_x" else 1.0
                        x = center[0] - sign * (0.5 * wall_thickness + 0.001)
                        points = (
                            (x, center[1] - wall_distance, base_z),
                            (x, center[1] + wall_distance, base_z),
                            (x, center[1] + wall_distance, base_z + wall_height),
                            (x, center[1] - wall_distance, base_z + wall_height),
                        )
                    texture_quad_path = f"{path}/texture_face"
                    _usd_add_quad(
                        stage,
                        texture_quad_path,
                        points,
                        (
                            (0.0, 0.0),
                            (background_texture_tiling, 0.0),
                            (background_texture_tiling, background_texture_tiling),
                            (0.0, background_texture_tiling),
                        ),
                        wall_texture_mat,
                    )
                    texture_path = background_texture_path
                background_walls.append(
                    {
                        "env_id": int(env_id),
                        "name": wall_name,
                        "path": path,
                        "center": [float(v) for v in center],
                        "size": [float(v) for v in wall_size],
                        "texture_path": texture_path or None,
                        "texture_quad_path": texture_quad_path or None,
                    }
                )
    task_env.sim.forward()
    return {
        "enabled": True,
        "surround_enabled": surround_enabled,
        "texture_enabled": texture_enabled,
        "background_walls_enabled": walls_enabled,
        "size": [float(v) for v in size_xy],
        "top_z": float(top_z),
        "thickness": float(thickness),
        "color": [float(v) for v in color],
        "roughness": roughness,
        "dome_light_texture": dome_light_texture,
        "spawned": spawned,
        "table_texture_quads": table_texture_quads,
        "texture_patches": texture_patches,
        "background_walls": background_walls,
    }


def _grasp_overlay_candidates(payload: dict[str, object], max_count: int) -> tuple[list[np.ndarray], int | None]:
    annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
    raw_grasps = (
        annotations.get("tool_grasps_world")
        or payload.get("tool_grasps_world")
        or annotations.get("all_grasps")
        or payload.get("all_grasps")
        or payload.get("grasps_world")
        or []
    )
    grasps = [matrix for item in raw_grasps if (matrix := _as_matrix4(item)) is not None]
    target = _as_matrix4(payload.get("selected_tool_world"))
    if target is None:
        target = _as_matrix4(annotations.get("target_tool_transform"))
    if target is None:
        target = _as_matrix4(payload.get("selected_grasp_world"))
    if target is None:
        target = _as_matrix4(annotations.get("target_grasp_transform"))
    if target is None:
        target = _as_matrix4(payload.get("target_grasp_transform"))
    target_idx: int | None = None
    if target is not None and grasps:
        distances = [float(np.linalg.norm(g[:3, 3] - target[:3, 3])) for g in grasps]
        target_idx = int(min(range(len(distances)), key=distances.__getitem__))
    elif target is not None:
        grasps = [target]
        target_idx = 0

    if not grasps:
        return [], None
    budget = max(int(max_count), 1)
    selected: list[int] = []
    if target_idx is not None:
        selected.append(target_idx)
    remaining = max(0, budget - len(selected))
    if remaining > 0:
        candidates = (
            [0]
            if remaining == 1
            else [
                int(round(float(idx) * float(len(grasps) - 1) / float(remaining - 1)))
                for idx in range(remaining)
            ]
        )
        for idx in candidates:
            if idx not in selected:
                selected.append(idx)
    for idx in range(len(grasps)):
        if len(selected) >= budget:
            break
        if idx not in selected:
            selected.append(idx)
    selected = selected[:budget]
    target_marker_idx = selected.index(target_idx) if target_idx in selected else None
    return [grasps[idx] for idx in selected], target_marker_idx


def _spawn_grasp_pose_overlay(
    overlay_path: Path | None,
    *,
    max_count: int,
    axis_length: float,
    axis_thickness: float,
) -> dict[str, object]:
    if overlay_path is None:
        return {"enabled": False, "reason": "missing_path"}
    if not overlay_path.is_file():
        return {"enabled": False, "reason": "path_not_found", "path": str(overlay_path)}
    payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"enabled": False, "reason": "payload_not_mapping", "path": str(overlay_path)}
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"enabled": False, "reason": "missing_usd_stage", "path": str(overlay_path)}

    grasps, target_marker_idx = _grasp_overlay_candidates(payload, max_count)
    if not grasps:
        return {"enabled": False, "reason": "no_valid_grasp_matrices", "path": str(overlay_path)}

    root_path = "/World/GraspPoseOverlay"
    looks_root = "/World/Looks/GraspPoseOverlay"
    UsdGeom.Xform.Define(stage, root_path)
    UsdGeom.Xform.Define(stage, looks_root)
    x_mat = _usd_material(stage, f"{looks_root}/axis_x_red", (0.88, 0.08, 0.06))
    y_mat = _usd_material(stage, f"{looks_root}/axis_y_green", (0.08, 0.62, 0.18))
    z_mat = _usd_material(stage, f"{looks_root}/axis_z_blue", (0.10, 0.25, 0.92))
    center_mat = _usd_material(stage, f"{looks_root}/selected_center", (1.0, 0.95, 0.70))

    markers: list[dict[str, object]] = []
    for marker_idx, transform in enumerate(grasps):
        is_selected = target_marker_idx is not None and marker_idx == target_marker_idx
        marker_path = f"{root_path}/g_{marker_idx:03d}"
        marker_root = UsdGeom.Xform.Define(stage, marker_path).GetPrim()
        position = tuple(float(v) for v in transform[:3, 3])
        quat = _matrix_to_quat_xyzw(transform)
        _usd_set_xform(marker_root, position, rotate_quat_xyzw=quat)
        length = float(axis_length) * (1.35 if is_selected else 1.0)
        thickness = float(axis_thickness) * (1.35 if is_selected else 1.0)
        half = 0.5 * length
        _usd_add_box(stage, f"{marker_path}/x_axis", (half, 0.0, 0.0), (length, thickness, thickness), x_mat)
        _usd_add_box(stage, f"{marker_path}/y_axis", (0.0, half, 0.0), (thickness, length, thickness), y_mat)
        _usd_add_box(stage, f"{marker_path}/z_axis", (0.0, 0.0, half), (thickness, thickness, length), z_mat)
        if is_selected:
            _usd_add_box(
                stage,
                f"{marker_path}/selected_center",
                (0.0, 0.0, 0.0),
                (2.5 * thickness, 2.5 * thickness, 2.5 * thickness),
                center_mat,
            )
        markers.append(
            {
                "path": marker_path,
                "is_selected": bool(is_selected),
                "position_w": [float(v) for v in position],
                "axis_z_w": [float(v) for v in transform[:3, 2]],
            }
        )
    return {
        "enabled": True,
        "path": str(overlay_path),
        "root_path": root_path,
        "visualized_count": len(markers),
        "selected_marker_index": target_marker_idx,
        "axis_length": float(axis_length),
        "axis_thickness": float(axis_thickness),
        "markers": markers,
    }


def _initial_clearance_summary(task_env, snapshot: dict[str, object]) -> dict[str, object] | None:
    clutter_positions = snapshot.get("clutter_root_pos_by_slot")
    if not isinstance(clutter_positions, list) or not clutter_positions:
        return None
    target_positions = snapshot.get("target_root_pos")
    if not isinstance(target_positions, list):
        return None
    target_radii = getattr(task_env, "object_xy_radius", None)
    clutter_radii = getattr(task_env, "tabletop_clutter_xy_radius", None)
    if target_radii is None or clutter_radii is None:
        return None
    target_radii_list = target_radii.detach().float().cpu().tolist()
    clutter_radii_list = clutter_radii.detach().float().cpu().tolist()
    min_clearance = float("inf")
    min_bin_clearance = float("inf")
    overlaps: list[dict[str, object]] = []
    bin_clearance_violations: list[dict[str, object]] = []
    pair_count = 0
    bin_pair_count = 0
    bin_clearance_required = float(getattr(task_env.cfg, "tabletop_goal_bin_clearance", 0.0))
    bin_clearance_fn = getattr(task_env, "_tabletop_goal_bin_clearance", None)
    for env_idx, target_pos in enumerate(target_positions):
        bodies: list[tuple[str, tuple[float, float], float]] = [
            ("target", (float(target_pos[0]), float(target_pos[1])), float(target_radii_list[env_idx]))
        ]
        for slot_idx, slot_positions in enumerate(clutter_positions):
            slot_pos = slot_positions[env_idx]
            bodies.append(
                (
                    f"clutter_{slot_idx:02d}",
                    (float(slot_pos[0]), float(slot_pos[1])),
                    float(clutter_radii_list[env_idx][slot_idx]),
                )
            )
        for left_idx in range(len(bodies)):
            for right_idx in range(left_idx + 1, len(bodies)):
                left_name, left_xy, left_radius = bodies[left_idx]
                right_name, right_xy, right_radius = bodies[right_idx]
                clearance = (
                    float(np.hypot(left_xy[0] - right_xy[0], left_xy[1] - right_xy[1]))
                    - left_radius
                    - right_radius
                )
                min_clearance = min(min_clearance, clearance)
                pair_count += 1
                if clearance < -1.0e-6:
                    overlaps.append(
                        {
                            "env": int(env_idx),
                            "a": left_name,
                            "b": right_name,
                            "clearance": float(clearance),
                        }
                    )
        if callable(bin_clearance_fn) and bool(getattr(task_env.cfg, "tabletop_goal_bin_enabled", False)):
            for body_name, body_xy, body_radius in bodies:
                clearance = float(bin_clearance_fn(body_xy, body_radius))
                min_bin_clearance = min(min_bin_clearance, clearance)
                bin_pair_count += 1
                if clearance < bin_clearance_required - 1.0e-6:
                    bin_clearance_violations.append(
                        {
                            "env": int(env_idx),
                            "body": body_name,
                            "clearance": float(clearance),
                            "required_clearance": float(bin_clearance_required),
                        }
                    )
    return {
        "pair_count": int(pair_count),
        "overlap_count": len(overlaps),
        "min_clearance": None if not np.isfinite(min_clearance) else float(min_clearance),
        "overlaps": overlaps[:20],
        "bin_pair_count": int(bin_pair_count),
        "bin_clearance_required": float(bin_clearance_required),
        "min_bin_clearance": None if not np.isfinite(min_bin_clearance) else float(min_bin_clearance),
        "bin_clearance_violation_count": len(bin_clearance_violations),
        "bin_clearance_violations": bin_clearance_violations[:20],
    }


def _speed_summary_from_root_vel(root_vel_w: torch.Tensor) -> dict[str, object]:
    root_vel_w = root_vel_w.detach().float()
    linear_speed = torch.linalg.norm(root_vel_w[:, 0:3], dim=-1)
    angular_speed = torch.linalg.norm(root_vel_w[:, 3:6], dim=-1)
    return {
        "linear_speed": _tensor_list(linear_speed),
        "angular_speed": _tensor_list(angular_speed),
        "max_linear_speed": float(linear_speed.max().detach().cpu().item()) if linear_speed.numel() else 0.0,
        "max_angular_speed": float(angular_speed.max().detach().cpu().item()) if angular_speed.numel() else 0.0,
    }


def _root_velocity_summary(task_env) -> dict[str, object]:
    summary: dict[str, object] = {}
    target_vel = getattr(task_env._cube.data, "root_vel_w", None)
    if isinstance(target_vel, torch.Tensor):
        summary["target"] = _speed_summary_from_root_vel(target_vel)
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    if clutter_objects:
        clutter = []
        max_linear = 0.0
        max_angular = 0.0
        for slot_idx, clutter_object in enumerate(clutter_objects):
            root_vel = getattr(clutter_object.data, "root_vel_w", None)
            if not isinstance(root_vel, torch.Tensor):
                continue
            slot_summary = _speed_summary_from_root_vel(root_vel)
            slot_summary["slot_idx"] = int(slot_idx)
            clutter.append(slot_summary)
            max_linear = max(max_linear, float(slot_summary["max_linear_speed"]))
            max_angular = max(max_angular, float(slot_summary["max_angular_speed"]))
        summary["clutter_by_slot"] = clutter
        summary["clutter_max_linear_speed"] = float(max_linear)
        summary["clutter_max_angular_speed"] = float(max_angular)
    return summary


def _write_video(video_path: Path, frames: list[np.ndarray], fps: int) -> None:
    if not frames:
        raise RuntimeError("No frames captured for video")
    writer = imageio.get_writer(str(video_path), fps=int(fps), macro_block_size=1)
    try:
        for frame in frames:
            writer.append_data(frame)
    finally:
        writer.close()


def _step_physics_without_task_reset(task_env, hold_joint_pos: torch.Tensor | None) -> None:
    robot = getattr(task_env, "_robot", None)
    if robot is not None and hold_joint_pos is not None:
        robot.set_joint_position_target(hold_joint_pos)
    task_env.scene.write_data_to_sim()
    task_env.sim.step(render=False)
    task_env.scene.update(dt=task_env.sim.cfg.dt)


def _manual_action_step(task_env, actions: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    task_env._pre_physics_step(actions)
    for _ in range(int(task_env.cfg.decimation)):
        task_env._apply_action()
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(dt=task_env.sim.cfg.dt)
    task_env.episode_length_buf += 1
    if hasattr(task_env, "common_step_counter"):
        task_env.common_step_counter += 1
    task_env._compute_intermediate_values()
    return task_env._get_dones()


def _default_yam_rejected_trajectory_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "yam" / "rejected_nominal_trajectory_compact.json"


def _load_demo_trajectory(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"Expected non-empty frames list in demo trajectory: {path}")
    joint_positions: list[np.ndarray] = []
    phases: list[str] = []
    for frame_idx, frame in enumerate(frames):
        if not isinstance(frame, dict) or "joint_position" not in frame:
            raise ValueError(f"Trajectory frame {frame_idx} has no joint_position: {path}")
        q = np.asarray(frame["joint_position"], dtype=np.float32)
        if q.ndim != 1:
            raise ValueError(f"Trajectory frame {frame_idx} joint_position must be 1-D, got {q.shape}")
        joint_positions.append(q)
        phases.append(str(frame.get("phase") or "plan"))
    return {
        "path": str(path),
        "fps": payload.get("fps"),
        "total_frames": int(payload.get("total_frames") or len(joint_positions)),
        "joint_names": payload.get("joint_names"),
        "segments": payload.get("segments"),
        "object_count": payload.get("object_count"),
        "object_sequence": payload.get("object_sequence"),
        "tabletop_rejected": payload.get("tabletop_rejected"),
        "tabletop_status": payload.get("tabletop_status"),
        "nominal_status": payload.get("nominal_status"),
        "candidate_idx": payload.get("candidate_idx"),
        "candidate_confidence": payload.get("candidate_confidence"),
        "scripted_place": payload.get("scripted_place"),
        "joint_positions": joint_positions,
        "phases": phases,
    }


def _trajectory_source_fps(trajectory: dict[str, object]) -> float:
    try:
        fps = float(trajectory.get("fps") or 0.0)
    except (TypeError, ValueError):
        fps = 0.0
    if not math.isfinite(fps) or fps <= 0.0:
        return 30.0
    return fps


def _env_control_dt(task_env) -> float:
    sim_dt = float(getattr(task_env.sim.cfg, "dt", 0.0))
    decimation = max(int(getattr(task_env.cfg, "decimation", 1)), 1)
    if not math.isfinite(sim_dt) or sim_dt <= 0.0:
        return 1.0 / 60.0
    return sim_dt * float(decimation)


def _trajectory_realtime_step_count(
    task_env,
    trajectory: dict[str, object],
    *,
    start_blend_steps: int,
) -> int:
    source_joint_positions = trajectory["joint_positions"]
    if not isinstance(source_joint_positions, list) or not source_joint_positions:
        return 0
    fps = _trajectory_source_fps(trajectory)
    control_dt = _env_control_dt(task_env)
    source_duration = float(max(len(source_joint_positions) - 1, 0)) / fps
    replay_steps = int(math.ceil(source_duration / control_dt)) + 1
    return max(1, int(start_blend_steps) + replay_steps)


def _map_source_joint_to_env(task_env, raw_q: np.ndarray | torch.Tensor) -> torch.Tensor:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        raise AttributeError("single_yam_rejected_path trajectory replay requires a robot articulation")
    raw = torch.as_tensor(raw_q, dtype=robot.data.joint_pos.dtype, device=task_env.device).view(1, -1)
    raw = raw.repeat(task_env.num_envs, 1)
    joint_pos = robot.data.default_joint_pos.clone()
    arm_count = len(getattr(task_env, "arm_joint_ids", []))
    finger_count = len(getattr(task_env, "finger_joint_ids", []))
    if raw.shape[1] == joint_pos.shape[1]:
        joint_pos[:] = raw
    elif raw.shape[1] == arm_count + finger_count:
        joint_pos[:, task_env.arm_joint_ids] = raw[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw[:, arm_count : arm_count + finger_count]
    elif raw.shape[1] == arm_count + 1:
        joint_pos[:, task_env.arm_joint_ids] = raw[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw[:, arm_count : arm_count + 1].repeat(1, finger_count)
    else:
        raise ValueError(
            f"Cannot map trajectory joint_position dim {raw.shape[1]} to "
            f"{joint_pos.shape[1]} env joints ({arm_count} arm, {finger_count} fingers)"
        )
    return torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _map_source_joint_velocity_to_env(task_env, raw_qd: np.ndarray | torch.Tensor) -> torch.Tensor:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        raise AttributeError("single_yam_rejected_path trajectory replay requires a robot articulation")
    raw = torch.as_tensor(raw_qd, dtype=robot.data.joint_vel.dtype, device=task_env.device).view(1, -1)
    raw = raw.repeat(task_env.num_envs, 1)
    joint_vel = torch.zeros_like(robot.data.joint_vel)
    arm_count = len(getattr(task_env, "arm_joint_ids", []))
    finger_count = len(getattr(task_env, "finger_joint_ids", []))
    if raw.shape[1] == joint_vel.shape[1]:
        joint_vel[:] = raw
    elif raw.shape[1] == arm_count + finger_count:
        joint_vel[:, task_env.arm_joint_ids] = raw[:, :arm_count]
        joint_vel[:, task_env.finger_joint_ids] = raw[:, arm_count : arm_count + finger_count]
    elif raw.shape[1] == arm_count + 1:
        joint_vel[:, task_env.arm_joint_ids] = raw[:, :arm_count]
        joint_vel[:, task_env.finger_joint_ids] = raw[:, arm_count : arm_count + 1].repeat(1, finger_count)
    else:
        raise ValueError(
            f"Cannot map trajectory joint velocity dim {raw.shape[1]} to "
            f"{joint_vel.shape[1]} env joints ({arm_count} arm, {finger_count} fingers)"
        )
    return joint_vel


def _apply_kinematic_joint_position(task_env, joint_pos: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        raise AttributeError("single_yam_rejected_path trajectory replay requires a robot articulation")
    env_ids = robot._ALL_INDICES
    joint_vel = torch.zeros_like(joint_pos)
    robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    if hasattr(task_env, "robot_dof_targets"):
        task_env.robot_dof_targets[env_ids] = joint_pos
    if hasattr(task_env, "arm_joint_pos_target"):
        task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    if hasattr(task_env, "finger_joint_pos_target"):
        task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env.episode_length_buf += 1
    if hasattr(task_env, "common_step_counter"):
        task_env.common_step_counter += 1
    task_env._compute_intermediate_values()
    return task_env._get_dones()


def _apply_dynamic_joint_position_target(
    task_env,
    joint_pos: torch.Tensor,
    joint_vel: torch.Tensor | None = None,
    *,
    velocity_target_scale: float = 1.0,
) -> tuple[torch.Tensor, torch.Tensor]:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        raise AttributeError("single_yam_rejected_path trajectory replay requires a robot articulation")
    env_ids = robot._ALL_INDICES
    velocity_target = None
    if joint_vel is not None and hasattr(robot, "set_joint_velocity_target"):
        velocity_target = float(velocity_target_scale) * joint_vel
    if hasattr(task_env, "robot_dof_targets"):
        task_env.robot_dof_targets[env_ids] = joint_pos
    if hasattr(task_env, "arm_joint_pos_target"):
        task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    if hasattr(task_env, "finger_joint_pos_target"):
        task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]
    for _ in range(int(task_env.cfg.decimation)):
        robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        if velocity_target is not None:
            robot.set_joint_velocity_target(velocity_target, env_ids=env_ids)
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(dt=task_env.sim.cfg.dt)
    task_env.episode_length_buf += 1
    if hasattr(task_env, "common_step_counter"):
        task_env.common_step_counter += 1
    task_env._compute_intermediate_values()
    return task_env._get_dones()


def _single_yam_rejected_trajectory_joint_position(
    task_env,
    trajectory: dict[str, object],
    step_idx: int,
    total_steps: int,
    *,
    start_joint_pos: torch.Tensor,
    start_blend_steps: int,
    timing_mode: str,
) -> tuple[torch.Tensor, torch.Tensor, str, int, dict[str, object]]:
    source_joint_positions = trajectory["joint_positions"]
    source_phases = trajectory["phases"]
    if not isinstance(source_joint_positions, list) or not source_joint_positions:
        raise ValueError("Trajectory has no source joint positions")
    total_steps = max(int(total_steps), 1)
    start_blend_steps = max(min(int(start_blend_steps), total_steps - 1), 0)
    first_source_joint_pos = _map_source_joint_to_env(task_env, source_joint_positions[0])
    if start_blend_steps > 0 and step_idx <= start_blend_steps:
        alpha = float(step_idx) / float(start_blend_steps)
        joint_pos = start_joint_pos + alpha * (first_source_joint_pos - start_joint_pos)
        control_dt = _env_control_dt(task_env)
        blend_velocity = (first_source_joint_pos - start_joint_pos) / max(float(start_blend_steps) * control_dt, 1.0e-9)
        return (
            joint_pos,
            blend_velocity,
            "blend_from_dextrah_start",
            0,
            {
                "trajectory_timing_mode": str(timing_mode),
                "trajectory_source_time_s": 0.0,
                "trajectory_source_frame_float": 0.0,
                "trajectory_source_frame_alpha": float(alpha),
                "joint_target_velocity": _tensor_list(blend_velocity),
            },
        )

    if str(timing_mode) == "realtime":
        fps = _trajectory_source_fps(trajectory)
        control_dt = _env_control_dt(task_env)
        replay_step = max(int(step_idx) - int(start_blend_steps) - 1, 0)
        source_time = float(replay_step) * control_dt
        source_frame_float = min(source_time * fps, float(len(source_joint_positions) - 1))
        lo = int(math.floor(source_frame_float))
        hi = min(lo + 1, len(source_joint_positions) - 1)
        alpha = float(source_frame_float - lo)
        lo_q = np.asarray(source_joint_positions[lo], dtype=np.float32)
        hi_q = np.asarray(source_joint_positions[hi], dtype=np.float32)
        raw_q = lo_q + alpha * (hi_q - lo_q)
        raw_qd = (hi_q - lo_q) * fps if hi > lo else np.zeros_like(raw_q)
        joint_pos = _map_source_joint_to_env(task_env, raw_q)
        joint_vel = _map_source_joint_velocity_to_env(task_env, raw_qd)
        phase_idx = min(int(round(source_frame_float)), len(source_joint_positions) - 1)
        phase = str(source_phases[phase_idx]) if isinstance(source_phases, list) else "trajectory"
        return (
            joint_pos,
            joint_vel,
            phase,
            phase_idx,
            {
                "trajectory_timing_mode": "realtime",
                "trajectory_source_time_s": float(min(source_time, float(len(source_joint_positions) - 1) / fps)),
                "trajectory_source_frame_float": float(source_frame_float),
                "trajectory_source_frame_alpha": float(alpha),
                "joint_target_velocity": _tensor_list(joint_vel),
            },
        )

    source_span = max(total_steps - start_blend_steps, 1)
    source_alpha = float(step_idx - start_blend_steps - 1) / float(max(source_span - 1, 1))
    source_idx = int(round(source_alpha * (len(source_joint_positions) - 1)))
    source_idx = max(0, min(source_idx, len(source_joint_positions) - 1))
    joint_pos = _map_source_joint_to_env(task_env, source_joint_positions[source_idx])
    joint_vel = torch.zeros_like(joint_pos)
    phase = str(source_phases[source_idx]) if isinstance(source_phases, list) else "trajectory"
    return (
        joint_pos,
        joint_vel,
        phase,
        source_idx,
        {
            "trajectory_timing_mode": "stretch",
            "trajectory_source_time_s": float(source_idx) / _trajectory_source_fps(trajectory),
            "trajectory_source_frame_float": float(source_idx),
            "trajectory_source_frame_alpha": 0.0,
            "joint_target_velocity": _tensor_list(joint_vel),
        },
    )


DEXTRAH_TABLE_REJECTION_TARGET_ARM_Q = (
    -0.1004,
    3.5656,
    1.9488,
    0.1869,
    -0.0467,
    -1.1129,
)


def _dextrah_table_rejection_full_target_joint_pos(task_env) -> torch.Tensor:
    robot = getattr(task_env, "_robot", None)
    if robot is None:
        raise AttributeError("dextrah_table_rejection trajectory requires a robot articulation")
    arm_joint_ids = list(getattr(task_env, "arm_joint_ids", []))
    finger_joint_ids = list(getattr(task_env, "finger_joint_ids", []))
    if len(arm_joint_ids) != len(DEXTRAH_TABLE_REJECTION_TARGET_ARM_Q):
        raise ValueError(
            "dextrah_table_rejection expects the six-joint single-YAM arm, "
            f"got {len(arm_joint_ids)} arm joints"
        )
    target = robot.data.default_joint_pos.clone()
    target_arm = torch.as_tensor(
        DEXTRAH_TABLE_REJECTION_TARGET_ARM_Q,
        dtype=target.dtype,
        device=task_env.device,
    ).view(1, -1)
    target[:, arm_joint_ids] = target_arm.repeat(task_env.num_envs, 1)
    if finger_joint_ids:
        target[:, finger_joint_ids] = float(getattr(task_env.cfg, "gripper_closed_joint_pos", 0.0))
    return torch.clamp(target, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _single_yam_dextrah_table_rejection_joint_position(
    task_env,
    step_idx: int,
    total_steps: int,
    *,
    start_joint_pos: torch.Tensor,
    target_fraction: float,
) -> tuple[torch.Tensor, str, torch.Tensor]:
    full_target = _dextrah_table_rejection_full_target_joint_pos(task_env)
    target_fraction = max(0.0, min(float(target_fraction), 1.0))
    target_joint_pos = start_joint_pos + target_fraction * (full_target - start_joint_pos)
    total_steps = max(int(total_steps), 1)
    approach_steps = max(int(round(0.78 * total_steps)), 1)
    if step_idx <= approach_steps:
        alpha = float(step_idx) / float(approach_steps)
        alpha = alpha * alpha * (3.0 - 2.0 * alpha)
        phase = "dextrah_current_scene_rejected_approach"
    else:
        alpha = 1.0
        phase = "dextrah_current_scene_rejected_hold"
    joint_pos = start_joint_pos + alpha * (target_joint_pos - start_joint_pos)
    return joint_pos, phase, target_joint_pos


def _single_yam_rejected_path_action(
    task_env,
    step_idx: int,
    total_steps: int,
    *,
    high_hold_z: float,
    low_hold_z: float,
) -> tuple[torch.Tensor, str, torch.Tensor]:
    if not all(hasattr(task_env, name) for name in ("tcp_pos", "hold_pos", "cube_pos")):
        raise AttributeError("single_yam_rejected_path demo requires the single-YAM task state buffers")
    task_env._compute_intermediate_values()
    actions = torch.zeros((task_env.num_envs, int(task_env.cfg.action_space)), device=task_env.device)
    position_scale = torch.as_tensor(task_env.cfg.ik_position_action_scale, device=task_env.device)

    total_steps = max(int(total_steps), 1)
    approach_end = max(int(round(0.32 * total_steps)), 1)
    descend_end = max(int(round(0.72 * total_steps)), approach_end + 1)
    table_z = float(task_env.cfg.table_surface_z)
    target_hold = task_env.hold_pos.detach().clone()
    target_hold[:, 0] = float(getattr(task_env.cfg, "pickup_x", task_env.cfg.table_center_x))
    target_hold[:, 1] = float(getattr(task_env.cfg, "pickup_y", task_env.cfg.table_center_y))
    if step_idx <= approach_end:
        phase = "high_side_approach"
        target_hold[:, 0] -= 0.10
        target_hold[:, 2] = table_z + float(high_hold_z)
        gripper_action = 1.0
    elif step_idx <= descend_end:
        phase = "low_clearance_rejected_approach"
        alpha = float(step_idx - approach_end) / float(max(descend_end - approach_end, 1))
        side_offset = -0.10 * (1.0 - alpha)
        target_hold[:, 0] += side_offset
        target_hold[:, 2] = table_z + (1.0 - alpha) * float(high_hold_z) + alpha * float(low_hold_z)
        gripper_action = 1.0
    else:
        phase = "rejected_pose_hold"
        target_hold[:, 2] = table_z + float(low_hold_z)
        gripper_action = -1.0

    hold_error = target_hold - task_env.hold_pos.detach()
    actions[:, :3] = torch.clamp(hold_error / torch.clamp(position_scale, min=1.0e-6), -1.0, 1.0)
    actions[:, 6] = float(gripper_action)
    return actions, phase, target_hold


def _single_yam_rejected_path_row(
    task_env,
    *,
    step_idx: int,
    phase: str,
    target_hold: torch.Tensor,
    actions: torch.Tensor,
    terminated: torch.Tensor,
    truncated: torch.Tensor,
    joint_position: torch.Tensor | None = None,
    source_frame_idx: int | None = None,
    trajectory_timing: dict[str, object] | None = None,
    trajectory_path: str | None = None,
) -> dict[str, object]:
    done = torch.logical_or(terminated, truncated)
    penetration_margin = float(getattr(task_env.cfg, "finger_table_penetration_termination_margin", -0.008))
    clearance = task_env.finger_table_clearance.detach()
    row = {
        "step": int(step_idx),
        "phase": phase,
        "target_hold_pos": _tensor_list(target_hold),
        "action": _tensor_list(actions),
        "tcp_pos": _tensor_list(task_env.tcp_pos),
        "hold_pos": _tensor_list(task_env.hold_pos),
        "target_object_pos": _tensor_list(task_env.cube_pos),
        "target_object_quat": _tensor_list(task_env.cube_quat),
        "target_object_velocity": _tensor_list(task_env.cube_vel),
        "gripper_width": _tensor_list(task_env.gripper_width),
        "finger_table_clearance": _tensor_list(clearance),
        "finger_table_penetration_margin": penetration_margin,
        "finger_table_penetration_rejected": _tensor_list(clearance < penetration_margin),
        "terminated": _tensor_list(terminated),
        "truncated": _tensor_list(truncated),
        "done": _tensor_list(done),
        "cube_linear_speed": _tensor_list(task_env.cube_linear_speed),
        "cube_angular_speed": _tensor_list(task_env.cube_angular_speed),
    }
    if joint_position is not None:
        row["joint_position"] = _tensor_list(joint_position)
        robot = getattr(task_env, "_robot", None)
        if robot is not None:
            actual_pos = robot.data.joint_pos.detach()
            actual_vel = robot.data.joint_vel.detach()
            tracking_error = actual_pos - joint_position
            row["actual_joint_position"] = _tensor_list(actual_pos)
            row["actual_joint_velocity"] = _tensor_list(actual_vel)
            row["joint_tracking_error"] = _tensor_list(tracking_error)
            row["joint_tracking_error_max_abs"] = float(torch.max(torch.abs(tracking_error)).detach().cpu().item())
    if source_frame_idx is not None:
        row["source_frame_idx"] = int(source_frame_idx)
    if trajectory_timing is not None:
        row.update(trajectory_timing)
    if trajectory_path is not None:
        row["trajectory_path"] = str(trajectory_path)
    return row


def _clutter_root_state(task_env, attr: str, dim: int) -> np.ndarray:
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    values: list[np.ndarray] = []
    env_origins = getattr(task_env.scene, "env_origins", None)
    for clutter_object in clutter_objects:
        tensor = getattr(getattr(clutter_object, "data", None), attr, None)
        if not isinstance(tensor, torch.Tensor):
            continue
        if attr == "root_pos_w" and isinstance(env_origins, torch.Tensor):
            tensor = tensor - env_origins
        values.append(_tensor_numpy(tensor))
    if not values:
        return np.zeros((0, int(task_env.num_envs), int(dim)), dtype=np.float32)
    return np.stack(values, axis=0).astype(np.float32, copy=False)


def _demo_dataset_sample(
    task_env,
    *,
    step_idx: int,
    phase: str,
    actions: torch.Tensor,
    terminated: torch.Tensor,
    truncated: torch.Tensor,
    dataset_terminated: torch.Tensor | None,
    dataset_truncated: torch.Tensor | None,
    joint_position: torch.Tensor | None,
    joint_velocity: torch.Tensor | None,
    source_frame_idx: int | None,
) -> dict[str, np.ndarray | str | int]:
    robot = getattr(task_env, "_robot", None)
    env_origins = task_env.scene.env_origins
    target_root_pos = task_env._cube.data.root_pos_w - env_origins
    observations = task_env._get_observations()
    raw_done = torch.logical_or(terminated, truncated)
    if dataset_terminated is None:
        dataset_terminated = terminated
    if dataset_truncated is None:
        dataset_truncated = truncated
    done = torch.logical_or(dataset_terminated, dataset_truncated)
    if robot is not None:
        actual_joint_position = _tensor_numpy(robot.data.joint_pos)
        actual_joint_velocity = _tensor_numpy(robot.data.joint_vel)
        command_shape = robot.data.joint_pos.shape
    else:
        actual_joint_position = np.zeros((int(task_env.num_envs), 0), dtype=np.float32)
        actual_joint_velocity = np.zeros((int(task_env.num_envs), 0), dtype=np.float32)
        command_shape = (int(task_env.num_envs), 0)
    if joint_position is None:
        command_joint_position = np.full(command_shape, np.nan, dtype=np.float32)
    else:
        command_joint_position = _tensor_numpy(joint_position)
    if joint_velocity is None:
        command_joint_velocity = np.full(command_shape, np.nan, dtype=np.float32)
    else:
        command_joint_velocity = _tensor_numpy(joint_velocity)
    tcp_pos = _tensor_numpy(task_env.tcp_pos)
    tcp_quat = _tensor_numpy(task_env.tcp_quat)
    gripper_width = _tensor_numpy(task_env.gripper_width)
    robot_state = np.concatenate(
        (
            actual_joint_position,
            actual_joint_velocity,
            tcp_pos,
            tcp_quat,
            gripper_width.reshape((gripper_width.shape[0], -1)),
        ),
        axis=1,
    ).astype(np.float32, copy=False)
    return {
        "step_idx": int(step_idx),
        "phase": str(phase),
        "source_frame_idx": -1 if source_frame_idx is None else int(source_frame_idx),
        "action": _tensor_numpy(actions),
        "command_joint_position": command_joint_position,
        "command_joint_velocity": command_joint_velocity,
        "actual_joint_position": actual_joint_position,
        "actual_joint_velocity": actual_joint_velocity,
        "policy_obs": _tensor_numpy(observations["policy"]),
        "critic_obs": _tensor_numpy(observations["critic"]),
        "tcp_pos": tcp_pos,
        "tcp_quat": tcp_quat,
        "hold_pos": _tensor_numpy(task_env.hold_pos),
        "target_object_center_pos": _tensor_numpy(task_env.cube_pos),
        "target_object_quat": _tensor_numpy(task_env.cube_quat),
        "target_object_velocity": _tensor_numpy(task_env.cube_vel),
        "target_root_pos": _tensor_numpy(target_root_pos),
        "target_root_quat": _tensor_numpy(task_env._cube.data.root_quat_w),
        "target_root_velocity": _tensor_numpy(task_env._cube.data.root_vel_w),
        "clutter_root_pos": _clutter_root_state(task_env, "root_pos_w", 3),
        "clutter_root_quat": _clutter_root_state(task_env, "root_quat_w", 4),
        "clutter_root_velocity": _clutter_root_state(task_env, "root_vel_w", 6),
        "gripper_width": gripper_width,
        "robot_state": robot_state,
        "finger_table_clearance": _tensor_numpy(task_env.finger_table_clearance),
        "raw_task_terminated": _tensor_numpy(terminated, dtype=np.bool_),
        "raw_task_truncated": _tensor_numpy(truncated, dtype=np.bool_),
        "raw_task_done": _tensor_numpy(raw_done, dtype=np.bool_),
        "terminated": _tensor_numpy(dataset_terminated, dtype=np.bool_),
        "truncated": _tensor_numpy(dataset_truncated, dtype=np.bool_),
        "done": _tensor_numpy(done, dtype=np.bool_),
    }


def _append_demo_dataset_sample(dataset: dict[str, list[object]], sample: dict[str, object]) -> None:
    for key, value in sample.items():
        dataset.setdefault(key, []).append(value)


def _write_demo_dataset_npz(
    path: Path,
    *,
    dataset: dict[str, list[object]],
    rgb_frames: list[np.ndarray],
    rgb_step_idx: list[int],
    rgb_streams: dict[str, list[np.ndarray]] | None = None,
    metadata: dict[str, object],
) -> dict[str, object]:
    arrays: dict[str, np.ndarray] = {}
    for key, values in dataset.items():
        if key == "phase":
            arrays[key] = np.asarray(values, dtype="<U96")
        elif key in ("step_idx", "source_frame_idx"):
            arrays[key] = np.asarray(values, dtype=np.int64)
        else:
            arrays[key] = np.asarray(values)
    arrays["rgb"] = np.asarray(rgb_frames, dtype=np.uint8)
    arrays["rgb_step_idx"] = np.asarray(rgb_step_idx, dtype=np.int64)
    stream_counts: dict[str, int] = {}
    for key, frames in (rgb_streams or {}).items():
        arrays[key] = np.asarray(frames, dtype=np.uint8)
        stream_counts[key] = int(len(frames))
    arrays["metadata_json"] = np.asarray(json.dumps(_jsonable(metadata), indent=2))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    metadata_path = path.with_suffix(path.suffix + ".metadata.json")
    metadata_path.write_text(json.dumps(_jsonable(metadata), indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "metadata_path": str(metadata_path),
        "state_steps": int(len(dataset.get("step_idx", []))),
        "rgb_frames": int(len(rgb_frames)),
        "rgb_streams": stream_counts,
        "keys": sorted(arrays.keys()),
    }


def _wrist_camera_eye_target(task_env, args) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    tcp_pos = task_env.tcp_pos[0].detach().cpu().numpy().astype(np.float64)
    tcp_quat = task_env.tcp_quat[0].detach().cpu().numpy().astype(np.float64)
    rot = _quat_wxyz_to_matrix(tcp_quat.tolist())
    pos_offset = np.asarray(tuple(float(v) for v in args.wrist_camera_pos_offset), dtype=np.float64)
    forward = np.asarray(tuple(float(v) for v in args.wrist_camera_forward), dtype=np.float64)
    eye = tcp_pos + rot @ pos_offset
    target = eye + rot @ forward
    return tuple(float(v) for v in eye), tuple(float(v) for v in target)


def _capture_policy_rgb_streams(
    env,
    task_env,
    args,
    *,
    scene_eye: tuple[float, float, float],
    scene_target: tuple[float, float, float],
    wrist_camera: Camera | None = None,
    camera_dt: float = 0.0,
) -> dict[str, np.ndarray]:
    frames: dict[str, np.ndarray] = {}
    if bool(args.record_scene_rgb):
        task_env.sim.set_camera_view(
            eye=scene_eye,
            target=scene_target,
            camera_prim_path=task_env.cfg.viewer.cam_prim_path,
        )
        task_env.sim.render()
        frames["scene_rgb"] = _resize_rgb_nearest(
            _frame_array(env.render()),
            int(args.record_rgb_height),
            int(args.record_rgb_width),
        ).copy()
    if bool(args.record_wrist_rgb):
        if wrist_camera is not None:
            task_env.scene.write_data_to_sim()
            task_env.sim.render()
            wrist_camera.update(float(camera_dt), force_recompute=True)
            wrist_camera.update(0.0, force_recompute=True)
            wrist_rgb = _camera_rgb_array(wrist_camera.data.output["rgb"])
        else:
            wrist_eye, wrist_target = _wrist_camera_eye_target(task_env, args)
            task_env.sim.set_camera_view(
                eye=wrist_eye,
                target=wrist_target,
                camera_prim_path=task_env.cfg.viewer.cam_prim_path,
            )
            task_env.sim.render()
            wrist_rgb = _frame_array(env.render())
        frames["wrist_rgb"] = _resize_rgb_nearest(
            wrist_rgb,
            int(args.record_rgb_height),
            int(args.record_rgb_width),
        ).copy()
    task_env.sim.set_camera_view(
        eye=scene_eye,
        target=scene_target,
        camera_prim_path=task_env.cfg.viewer.cam_prim_path,
    )
    return frames


def _row_max_abs_summary(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            arr = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if arr.size == 0:
            continue
        finite = np.abs(arr[np.isfinite(arr)])
        if finite.size:
            values.append(float(np.max(finite)))
    if not values:
        return {"count": 0, "max_abs": None, "mean_abs": None}
    return {
        "count": int(len(values)),
        "max_abs": float(max(values)),
        "mean_abs": float(sum(values) / len(values)),
    }


def _row_scalar_summary(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            scalar = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(scalar):
            values.append(abs(scalar))
    if not values:
        return {"count": 0, "max_abs": None, "mean_abs": None}
    return {
        "count": int(len(values)),
        "max_abs": float(max(values)),
        "mean_abs": float(sum(values) / len(values)),
    }


def main() -> None:
    output_dir = Path(args_cli.output_dir).expanduser().resolve()
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(args_cli.video_path).expanduser().resolve() if args_cli.video_path else output_dir / "settle.mp4"
    metrics_path = (
        Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    )
    stable_scene_path = (
        Path(args_cli.stable_scene_path).expanduser().resolve()
        if args_cli.stable_scene_path
        else output_dir / "stable_scene.json"
    )
    trajectory_dataset_path = (
        Path(args_cli.trajectory_dataset_path).expanduser().resolve()
        if args_cli.trajectory_dataset_path
        else output_dir / "trajectory_dataset.npz"
    )
    stable_scene_input_path = stable_scene_path if stable_scene_path.is_file() else None
    stable_scene_input = _load_stable_scene(stable_scene_input_path)
    single_yam_demo_enabled = args_cli.demo_mode in ("single_yam_rejected_path", "single_yam_trajectory")

    objaverse_textured_summary = None
    if args_cli.objaverse_textured_manifest_path:
        textured_asset_dir = (
            Path(args_cli.objaverse_textured_asset_dir).expanduser().resolve()
            if args_cli.objaverse_textured_asset_dir
            else output_dir / "objaverse_textured_assets"
        )
        if args_cli.tabletop_clutter_object_count is None:
            args_cli.tabletop_clutter_object_count = 6
        if args_cli.tabletop_clutter_require_graspgen_scale is None:
            args_cli.tabletop_clutter_require_graspgen_scale = True
        if args_cli.tabletop_clutter_stable_pose_enabled is None:
            args_cli.tabletop_clutter_stable_pose_enabled = True
        if args_cli.tabletop_clutter_stable_pose_count is None:
            args_cli.tabletop_clutter_stable_pose_count = 1
        if args_cli.tabletop_clutter_spawn_z_clearance is None:
            args_cli.tabletop_clutter_spawn_z_clearance = 0.003
        if args_cli.tabletop_clutter_spawn_z_jitter is None:
            args_cli.tabletop_clutter_spawn_z_jitter = 0.0
        if args_cli.tabletop_clutter_solver_position_iterations is None:
            args_cli.tabletop_clutter_solver_position_iterations = 16
        if args_cli.tabletop_clutter_solver_velocity_iterations is None:
            args_cli.tabletop_clutter_solver_velocity_iterations = 6
        if args_cli.tabletop_clutter_linear_damping is None:
            args_cli.tabletop_clutter_linear_damping = 0.25
        if args_cli.tabletop_clutter_angular_damping is None:
            args_cli.tabletop_clutter_angular_damping = 1.25
        if args_cli.tabletop_clutter_sleep_threshold is None:
            args_cli.tabletop_clutter_sleep_threshold = 0.06
        if args_cli.tabletop_clutter_stabilization_threshold is None:
            args_cli.tabletop_clutter_stabilization_threshold = 0.03
        if args_cli.tabletop_clutter_max_depenetration_velocity is None:
            args_cli.tabletop_clutter_max_depenetration_velocity = 2.0
        stable_pose_cache_dir = None
        if bool(args_cli.tabletop_clutter_stable_pose_enabled):
            stable_pose_cache_dir = (
                Path(args_cli.tabletop_clutter_stable_pose_cache_dir).expanduser().resolve()
                if args_cli.tabletop_clutter_stable_pose_cache_dir
                else textured_asset_dir / "stable_pose_cache"
            )
            args_cli.tabletop_clutter_stable_pose_cache_dir = str(stable_pose_cache_dir)
        textured_manifest, objaverse_textured_summary = _prepare_textured_objaverse_manifest(
            manifest_path=Path(args_cli.objaverse_textured_manifest_path),
            output_dir=textured_asset_dir,
            max_assets=args_cli.objaverse_textured_max_assets,
            mesh_source=str(args_cli.objaverse_textured_mesh_source),
            make_instanceable=bool(args_cli.objaverse_textured_make_instanceable),
            force_conversion=bool(args_cli.objaverse_textured_force_conversion),
            collision_approximation=str(args_cli.objaverse_textured_collision_approximation),
            prioritize_common_tabletop=not bool(args_cli.disable_objaverse_textured_common_tabletop_priority),
            require_graspgen_prior_scale=bool(args_cli.objaverse_textured_require_graspgen_prior_scale),
            max_xy_radius=args_cli.tabletop_clutter_max_xy_radius,
            stable_pose_cache_dir=stable_pose_cache_dir,
            stable_pose_count=int(args_cli.tabletop_clutter_stable_pose_count),
            stable_pose_mesh_mode=str(args_cli.objaverse_textured_stable_pose_mesh_mode),
        )
        args_cli.object_asset_manifest_path = str(textured_manifest)
        args_cli.tabletop_clutter_asset_manifest_path = str(textured_manifest)
        if args_cli.max_objects is None and args_cli.objaverse_textured_max_assets:
            args_cli.max_objects = int(args_cli.objaverse_textured_max_assets)
        if args_cli.tabletop_clutter_max_objects is None and args_cli.objaverse_textured_max_assets:
            args_cli.tabletop_clutter_max_objects = int(args_cli.objaverse_textured_max_assets)
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_manifest_prepared",
                    "manifest_path": str(textured_manifest),
                    "num_objects": int(objaverse_textured_summary["num_objects"]),
                }
            ),
            flush=True,
        )

    if stable_scene_input is not None:
        stable_scene_manifests = _stable_scene_asset_manifests(stable_scene_input, output_dir)
        target_manifest_path = stable_scene_manifests.get("target_manifest_path")
        if target_manifest_path is not None:
            args_cli.object_asset_manifest_path = str(target_manifest_path)
            args_cli.max_objects = 1
            args_cli.object_asset_assignment = "round_robin"
            if args_cli.object_validate_usd_bounds is None:
                args_cli.object_validate_usd_bounds = False
            print(
                json.dumps(
                    {
                        "event": "stable_scene_target_manifest_prepared",
                        "manifest_path": str(target_manifest_path),
                        "uuid": str(stable_scene_manifests.get("target_uuid") or ""),
                    }
                ),
                flush=True,
            )
        clutter_manifest_path = stable_scene_manifests.get("clutter_manifest_path")
        clutter_uuids = [
            str(uuid)
            for uuid in stable_scene_manifests.get("clutter_uuids", [])
            if str(uuid)
        ]
        if clutter_manifest_path is not None:
            args_cli.tabletop_clutter_asset_manifest_path = str(clutter_manifest_path)
            args_cli.tabletop_clutter_object_count = len(clutter_uuids)
            args_cli.tabletop_clutter_max_objects = len(clutter_uuids)
            args_cli.tabletop_clutter_asset_assignment = "round_robin"
            if args_cli.tabletop_clutter_validate_usd_bounds is None:
                args_cli.tabletop_clutter_validate_usd_bounds = False
            print(
                json.dumps(
                    {
                        "event": "stable_scene_clutter_manifest_prepared",
                        "manifest_path": str(clutter_manifest_path),
                        "uuids": clutter_uuids,
                    }
                ),
                flush=True,
            )

    torch.manual_seed(int(args_cli.seed))
    np.random.seed(int(args_cli.seed))
    randomization_rng = np.random.default_rng(int(args_cli.seed) + 1009)
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    if hasattr(env_cfg, "seed"):
        env_cfg.seed = int(args_cli.seed)
    _set_if_present(env_cfg, "dome_light_intensity", args_cli.dome_light_intensity)
    _set_if_present(env_cfg, "dome_light_exposure", args_cli.dome_light_exposure)
    _set_if_present(env_cfg, "key_light_enabled", args_cli.key_light_enabled)
    _set_if_present(env_cfg, "key_light_intensity", args_cli.key_light_intensity)
    _set_if_present(env_cfg, "key_light_exposure", args_cli.key_light_exposure)
    yam_arm_control_gains = _apply_yam_actuator_gain_scales(
        env_cfg,
        actuator_name="arm",
        stiffness_scale=args_cli.yam_arm_stiffness_scale,
        damping_scale=args_cli.yam_arm_damping_scale,
        effort_scale=args_cli.yam_arm_effort_scale,
    )
    yam_gripper_control_gains = _apply_yam_actuator_gain_scales(
        env_cfg,
        actuator_name="gripper",
        stiffness_scale=args_cli.yam_gripper_stiffness_scale,
        damping_scale=args_cli.yam_gripper_damping_scale,
        effort_scale=args_cli.yam_gripper_effort_scale,
    )
    if bool(yam_arm_control_gains.get("enabled")):
        print(json.dumps({"event": "yam_arm_control_gains", **yam_arm_control_gains}), flush=True)
    if bool(yam_gripper_control_gains.get("enabled")):
        print(json.dumps({"event": "yam_gripper_control_gains", **yam_gripper_control_gains}), flush=True)
    yam_policy_randomization = _apply_yam_policy_scene_randomization(env_cfg, args_cli, randomization_rng)
    _set_if_present(env_cfg, "object_asset_manifest_path", args_cli.object_asset_manifest_path)
    _set_if_present(env_cfg, "object_assets_dir", args_cli.object_assets_dir)
    _set_if_present(env_cfg, "max_objects", args_cli.max_objects)
    _set_if_present(env_cfg, "object_asset_assignment", args_cli.object_asset_assignment)
    _set_if_present(env_cfg, "object_validate_usd_bounds", args_cli.object_validate_usd_bounds)
    _set_if_present(env_cfg, "object_usd_bounds_max_ratio", args_cli.object_usd_bounds_max_ratio)
    _set_if_present(env_cfg, "object_usd_bounds_max_dimension", args_cli.object_usd_bounds_max_dimension)
    _set_if_present(env_cfg, "require_graspgen_scale", args_cli.require_graspgen_scale)
    _set_if_present(env_cfg, "object_spawn_xy_randomization", args_cli.object_spawn_xy_randomization)
    _set_if_present(env_cfg, "object_spawn_yaw_randomization_deg", args_cli.object_spawn_yaw_randomization_deg)
    _set_if_present(env_cfg, "object_spawn_z_clearance", args_cli.object_spawn_z_clearance)
    _set_if_present(env_cfg, "object_kinematic_enabled", args_cli.object_kinematic_enabled)
    _set_if_present(env_cfg, "object_disable_gravity", args_cli.object_disable_gravity)
    _set_if_present(env_cfg, "object_solver_position_iterations", args_cli.object_solver_position_iterations)
    _set_if_present(env_cfg, "object_solver_velocity_iterations", args_cli.object_solver_velocity_iterations)
    _set_if_present(env_cfg, "object_linear_damping", args_cli.object_linear_damping)
    _set_if_present(env_cfg, "object_angular_damping", args_cli.object_angular_damping)
    _set_if_present(env_cfg, "object_sleep_threshold", args_cli.object_sleep_threshold)
    _set_if_present(env_cfg, "object_stabilization_threshold", args_cli.object_stabilization_threshold)
    _set_if_present(env_cfg, "object_max_linear_velocity", args_cli.object_max_linear_velocity)
    _set_if_present(env_cfg, "object_max_angular_velocity", args_cli.object_max_angular_velocity)
    _set_if_present(env_cfg, "object_max_depenetration_velocity", args_cli.object_max_depenetration_velocity)
    _set_if_present(env_cfg, "tabletop_clutter_asset_manifest_path", args_cli.tabletop_clutter_asset_manifest_path)
    _set_if_present(env_cfg, "tabletop_clutter_assets_dir", args_cli.tabletop_clutter_assets_dir)
    _set_if_present(env_cfg, "tabletop_clutter_max_objects", args_cli.tabletop_clutter_max_objects)
    _set_if_present(env_cfg, "tabletop_clutter_object_count", args_cli.tabletop_clutter_object_count)
    _set_if_present(env_cfg, "tabletop_clutter_asset_assignment", args_cli.tabletop_clutter_asset_assignment)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_validate_usd_bounds",
        args_cli.tabletop_clutter_validate_usd_bounds,
    )
    _set_if_present(
        env_cfg,
        "tabletop_clutter_usd_bounds_max_ratio",
        args_cli.tabletop_clutter_usd_bounds_max_ratio,
    )
    _set_if_present(
        env_cfg,
        "tabletop_clutter_usd_bounds_max_dimension",
        args_cli.tabletop_clutter_usd_bounds_max_dimension,
    )
    _set_if_present(env_cfg, "tabletop_clutter_spawn_xy_randomization", args_cli.tabletop_clutter_spawn_xy_randomization)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_yaw_randomization_deg", args_cli.tabletop_clutter_spawn_yaw_randomization_deg)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_z_clearance", args_cli.tabletop_clutter_spawn_z_clearance)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_z_jitter", args_cli.tabletop_clutter_spawn_z_jitter)
    _set_if_present(env_cfg, "tabletop_clutter_require_graspgen_scale", args_cli.tabletop_clutter_require_graspgen_scale)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_enabled", args_cli.tabletop_clutter_stable_pose_enabled)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_cache_dir", args_cli.tabletop_clutter_stable_pose_cache_dir)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_count", args_cli.tabletop_clutter_stable_pose_count)
    _set_if_present(env_cfg, "tabletop_clutter_non_overlapping", args_cli.tabletop_clutter_non_overlapping)
    _set_if_present(env_cfg, "tabletop_clutter_placement_padding", args_cli.tabletop_clutter_placement_padding)
    _set_if_present(env_cfg, "tabletop_clutter_placement_attempts", args_cli.tabletop_clutter_placement_attempts)
    _set_if_present(env_cfg, "tabletop_clutter_max_xy_radius", args_cli.tabletop_clutter_max_xy_radius)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_solver_position_iterations",
        args_cli.tabletop_clutter_solver_position_iterations,
    )
    _set_if_present(
        env_cfg,
        "tabletop_clutter_solver_velocity_iterations",
        args_cli.tabletop_clutter_solver_velocity_iterations,
    )
    _set_if_present(env_cfg, "tabletop_clutter_kinematic_enabled", args_cli.tabletop_clutter_kinematic_enabled)
    _set_if_present(env_cfg, "tabletop_clutter_disable_gravity", args_cli.tabletop_clutter_disable_gravity)
    _set_if_present(env_cfg, "tabletop_clutter_linear_damping", args_cli.tabletop_clutter_linear_damping)
    _set_if_present(env_cfg, "tabletop_clutter_angular_damping", args_cli.tabletop_clutter_angular_damping)
    _set_if_present(env_cfg, "tabletop_clutter_sleep_threshold", args_cli.tabletop_clutter_sleep_threshold)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_stabilization_threshold",
        args_cli.tabletop_clutter_stabilization_threshold,
    )
    _set_if_present(env_cfg, "tabletop_clutter_max_linear_velocity", args_cli.tabletop_clutter_max_linear_velocity)
    _set_if_present(env_cfg, "tabletop_clutter_max_angular_velocity", args_cli.tabletop_clutter_max_angular_velocity)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_max_depenetration_velocity",
        args_cli.tabletop_clutter_max_depenetration_velocity,
    )
    if stable_scene_input is not None and single_yam_demo_enabled:
        _set_if_present(env_cfg, "tabletop_clutter_prioritize_common_objects", False)
    stable_scene_bin_restore = _apply_stable_scene_bins_to_env_cfg(env_cfg, stable_scene_input)
    if bool(stable_scene_bin_restore.get("enabled")):
        _update_yam_policy_randomization_with_restored_bins(env_cfg, stable_scene_bin_restore)
        print(json.dumps({"event": "stable_scene_bins_applied", **stable_scene_bin_restore}), flush=True)
    _set_if_present(env_cfg, "object_reset_settle_steps", 0)

    render_resolution = None
    if hasattr(env_cfg, "viewer") and hasattr(env_cfg.viewer, "resolution"):
        default_width, default_height = (int(v) for v in env_cfg.viewer.resolution)
        if args_cli.render_width is not None or args_cli.render_height is not None:
            render_width = default_width if args_cli.render_width is None else int(args_cli.render_width)
            render_height = default_height if args_cli.render_height is None else int(args_cli.render_height)
            if render_width <= 0 or render_height <= 0:
                raise ValueError(f"Render resolution must be positive, got {render_width}x{render_height}")
            env_cfg.viewer.resolution = (render_width, render_height)
        render_resolution = [int(v) for v in env_cfg.viewer.resolution]
    elif args_cli.render_width is not None or args_cli.render_height is not None:
        raise AttributeError("The parsed env config does not expose viewer.resolution")

    print(
        json.dumps(
            {
                "event": "creating_env",
                "task": args_cli.task,
                "num_envs": int(args_cli.num_envs),
                "settle_steps": int(args_cli.settle_steps),
                "capture_interval": int(args_cli.capture_interval),
                "render_resolution": render_resolution,
                "output_dir": str(output_dir),
                "yam_policy_scene_randomization": getattr(
                    env_cfg,
                    "yam_policy_scene_randomization_summary",
                    yam_policy_randomization,
                ),
            }
        ),
        flush=True,
    )
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = env.unwrapped
    yam_policy_tabletop_surround_summary = _spawn_yam_policy_tabletop_surround(task_env)
    if yam_policy_tabletop_surround_summary.get("enabled"):
        print(
            json.dumps({"event": "yam_policy_tabletop_surround_spawned", **yam_policy_tabletop_surround_summary}),
            flush=True,
        )
    if stable_scene_input is not None:
        target = stable_scene_input.get("target") if isinstance(stable_scene_input.get("target"), dict) else {}
        asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
        expected_uuid = str(asset.get("uuid") or "")
        active_assets = list(getattr(task_env, "_object_assets", []))
        active_indices = getattr(task_env, "object_asset_index", None)
        active_uuid = ""
        if active_assets and active_indices is not None:
            active_idx = int(active_indices[0].detach().cpu().item())
            active_uuid = str(active_assets[active_idx].get("uuid") or "")
        if expected_uuid and active_uuid and active_uuid != expected_uuid:
            raise RuntimeError(
                f"Stable-scene target UUID mismatch: expected {expected_uuid}, active environment has {active_uuid}"
            )
        print(
            json.dumps(
                {
                    "event": "stable_scene_target_asset_active",
                    "expected_uuid": expected_uuid,
                    "active_uuid": active_uuid,
                }
            ),
            flush=True,
        )
        expected_clutter_uuids = []
        stable_clutter = stable_scene_input.get("clutter") if isinstance(stable_scene_input.get("clutter"), list) else []
        for entry in stable_clutter:
            if not isinstance(entry, dict):
                continue
            clutter_asset = entry.get("asset") if isinstance(entry.get("asset"), dict) else {}
            expected_clutter_uuids.append(str(clutter_asset.get("uuid") or ""))
        active_clutter_uuids: list[str] = []
        clutter_assets = list(getattr(task_env, "_tabletop_clutter_assets", []))
        clutter_indices = getattr(task_env, "tabletop_clutter_asset_index", None)
        if clutter_assets and clutter_indices is not None:
            for slot_idx in range(min(len(expected_clutter_uuids), int(clutter_indices.shape[1]))):
                active_idx = int(clutter_indices[0, slot_idx].detach().cpu().item())
                active_clutter_uuids.append(str(clutter_assets[active_idx].get("uuid") or ""))
        for slot_idx, expected_uuid in enumerate(expected_clutter_uuids):
            if not expected_uuid:
                continue
            active_uuid = active_clutter_uuids[slot_idx] if slot_idx < len(active_clutter_uuids) else ""
            if active_uuid and active_uuid != expected_uuid:
                raise RuntimeError(
                    "Stable-scene clutter UUID mismatch at slot "
                    f"{slot_idx}: expected {expected_uuid}, active environment has {active_uuid}"
                )
        print(
            json.dumps(
                {
                    "event": "stable_scene_clutter_assets_active",
                    "expected_uuids": expected_clutter_uuids,
                    "active_uuids": active_clutter_uuids,
                }
            ),
            flush=True,
        )
    eye_default, target_default = _task_camera_defaults(args_cli.task)
    eye = tuple(float(v) for v in (args_cli.camera_eye or eye_default))
    target = tuple(float(v) for v in (args_cli.camera_target or target_default))
    scene_camera_summary: dict[str, object] = {
        "randomized": False,
        "eye": [float(v) for v in eye],
        "target": [float(v) for v in target],
    }
    if bool(args_cli.yam_policy_scene_randomization) and args_cli.camera_eye is None and args_cli.camera_target is None:
        eye = _rng_vec_jitter(randomization_rng, eye, args_cli.yam_policy_scene_camera_eye_jitter)
        target = _rng_vec_jitter(randomization_rng, target, args_cli.yam_policy_scene_camera_target_jitter)
        scene_camera_summary = {
            "randomized": True,
            "eye": [float(v) for v in eye],
            "target": [float(v) for v in target],
            "eye_jitter": [float(v) for v in args_cli.yam_policy_scene_camera_eye_jitter],
            "target_jitter": [float(v) for v in args_cli.yam_policy_scene_camera_target_jitter],
        }
    task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=task_env.cfg.viewer.cam_prim_path)

    print(json.dumps({"event": "reset_start"}), flush=True)
    env.reset(seed=int(args_cli.seed))
    print(json.dumps({"event": "reset_done"}), flush=True)
    robot_debug_site_visibility_summary = {"enabled": False}
    if bool(args_cli.hide_robot_debug_sites):
        robot_debug_site_visibility_summary = _hide_robot_debug_site_prims()
        task_env.sim.forward()
        print(
            json.dumps(
                {
                    "event": "robot_debug_sites_hidden",
                    "hidden_count": robot_debug_site_visibility_summary.get("hidden_count", 0),
                    "hidden_paths": robot_debug_site_visibility_summary.get("hidden_paths", []),
                }
            ),
            flush=True,
        )
    for _ in range(max(int(args_cli.render_warmup_frames), 0)):
        task_env.sim.render()
        env.render()
    print(json.dumps({"event": "render_warmup_done"}), flush=True)
    stable_scene_restore_summary = {"enabled": False}
    if stable_scene_input is not None:
        stable_scene_restore_summary = _restore_stable_scene(task_env, stable_scene_input)
        for _ in range(max(int(args_cli.render_warmup_frames), 1)):
            task_env.sim.render()
            env.render()
        print(
            json.dumps(
                {
                    "event": "stable_scene_restored",
                    "path": str(stable_scene_input_path),
                    "summary": stable_scene_restore_summary,
                }
            ),
            flush=True,
        )

    wrist_camera: Camera | None = None
    wrist_camera_summary: dict[str, object] = {
        "enabled": False,
        "mode": str(args_cli.wrist_camera_mode),
    }
    if (
        bool(args_cli.record_multicam_rgb)
        and bool(args_cli.record_wrist_rgb)
        and str(args_cli.wrist_camera_mode) == "sensor"
    ):
        try:
            wrist_camera, wrist_camera_summary = _make_single_yam_wrist_camera(task_env)
        except Exception as exc:
            wrist_camera = None
            wrist_camera_summary = {
                "enabled": False,
                "mode": "viewer_fallback",
                "reason": f"{type(exc).__name__}: {exc}",
            }
        for _ in range(max(int(args_cli.render_warmup_frames), 1)):
            task_env.scene.write_data_to_sim()
            task_env.sim.render()
            if wrist_camera is not None:
                wrist_camera.update(float(_env_control_dt(task_env)), force_recompute=True)
        print(json.dumps({"event": "wrist_camera_prepared", **wrist_camera_summary}), flush=True)

    frames: list[np.ndarray] = []
    frame_paths: list[str] = []
    initial_snapshot = _root_snapshot(task_env)
    initial_velocity_summary = _root_velocity_summary(task_env)
    if bool(args_cli.freeze_object_roots_for_video):
        _restore_root_snapshot(task_env, initial_snapshot)
    visual_object_overlay_summary: list[dict[str, object]] = []
    if bool(args_cli.visual_object_overlay):
        visual_object_overlay_summary = _spawn_visual_object_overlay(
            task_env,
            initial_snapshot,
            z_offset=float(args_cli.visual_object_overlay_z_offset),
        )
        for _ in range(max(int(args_cli.render_warmup_frames), 1)):
            task_env.sim.render()
            env.render()
        print(
            json.dumps(
                {
                    "event": "visual_object_overlay_spawned",
                    "count": len(visual_object_overlay_summary),
                    "z_offset": float(args_cli.visual_object_overlay_z_offset),
                }
            ),
            flush=True,
        )
    grasp_pose_overlay_path = (
        Path(args_cli.grasp_pose_overlay_path).expanduser().resolve()
        if args_cli.grasp_pose_overlay_path
        else None
    )
    grasp_pose_overlay_summary = _spawn_grasp_pose_overlay(
        grasp_pose_overlay_path,
        max_count=max(1, int(args_cli.grasp_pose_overlay_max_count)),
        axis_length=float(args_cli.grasp_pose_overlay_axis_length),
        axis_thickness=float(args_cli.grasp_pose_overlay_axis_thickness),
    )
    if grasp_pose_overlay_summary.get("enabled"):
        for _ in range(max(int(args_cli.render_warmup_frames), 1)):
            task_env.sim.render()
            env.render()
        print(
            json.dumps(
                {
                    "event": "grasp_pose_overlay_spawned",
                    "path": grasp_pose_overlay_summary.get("path"),
                    "count": grasp_pose_overlay_summary.get("visualized_count"),
                    "selected_marker_index": grasp_pose_overlay_summary.get("selected_marker_index"),
                }
            ),
            flush=True,
        )
    elif grasp_pose_overlay_path is not None:
        print(
            json.dumps(
                {
                    "event": "grasp_pose_overlay_skipped",
                    "path": str(grasp_pose_overlay_path),
                    "reason": grasp_pose_overlay_summary.get("reason"),
                }
            ),
            flush=True,
        )
    frame, frame_path = _capture_frame(env, frame_dir, 0)
    frames.append(frame)
    frame_paths.append(frame_path)
    print(json.dumps({"event": "frame_captured", "frame_idx": 0, "path": frame_path}), flush=True)

    robot = getattr(task_env, "_robot", None)
    hold_joint_pos = robot.data.joint_pos.detach().clone() if robot is not None else None
    capture_interval = max(int(args_cli.capture_interval), 1)
    settle_steps = max(int(args_cli.settle_steps), 0)
    demo_steps = max(int(args_cli.demo_steps), 0)
    demo_step_rows: list[dict[str, object]] = []
    first_rejected_step: int | None = None
    first_done_step: int | None = None
    record_trajectory_dataset = bool(args_cli.record_trajectory_dataset) and single_yam_demo_enabled
    trajectory_dataset: dict[str, list[object]] = {}
    trajectory_rgb_frames: list[np.ndarray] = []
    trajectory_rgb_step_idx: list[int] = []
    trajectory_rgb_streams: dict[str, list[np.ndarray]] = {}
    demo_trajectory: dict[str, object] | None = None
    demo_trajectory_path: Path | None = None
    demo_trajectory_start_error: dict[str, object] | None = None
    demo_trajectory_timing_summary: dict[str, object] | None = None
    demo_start_joint_pos = None
    demo_table_rejection_target_joint_pos = None
    scripted_transport_desired_drop_env = None
    scripted_transport_drop_segment: tuple[int, int] | None = None
    if single_yam_demo_enabled:
        if robot is not None:
            demo_start_joint_pos = robot.data.joint_pos.detach().clone()
        trajectory_source = str(args_cli.demo_trajectory_source)
        should_load_trajectory = trajectory_source in ("auto", "graspgenx_replay")
        if should_load_trajectory:
            if args_cli.demo_trajectory_path:
                demo_trajectory_path = Path(args_cli.demo_trajectory_path).expanduser().resolve()
            else:
                default_trajectory_path = _default_yam_rejected_trajectory_path()
                if default_trajectory_path.is_file():
                    demo_trajectory_path = default_trajectory_path
            if trajectory_source == "graspgenx_replay" and demo_trajectory_path is None:
                raise FileNotFoundError("graspgenx_replay requested but no demo trajectory path was found")
        if demo_trajectory_path is not None and should_load_trajectory:
            demo_trajectory = _load_demo_trajectory(demo_trajectory_path)
            if robot is None:
                raise AttributeError("single_yam_rejected_path trajectory replay requires a robot articulation")
            first_source_joint_pos = _map_source_joint_to_env(task_env, demo_trajectory["joint_positions"][0])
            if demo_start_joint_pos is not None:
                start_delta = first_source_joint_pos - demo_start_joint_pos
                demo_trajectory_start_error = {
                    "max_abs": float(torch.max(torch.abs(start_delta)).detach().cpu().item()),
                    "l2": float(torch.linalg.norm(start_delta).detach().cpu().item()),
                    "first_source_joint_position": _tensor_list(first_source_joint_pos),
                    "replay_start_joint_position": _tensor_list(demo_start_joint_pos),
                }
            if str(args_cli.demo_trajectory_timing_mode) == "realtime":
                requested_demo_steps = int(demo_steps)
                source_fps = _trajectory_source_fps(demo_trajectory)
                source_frames = int(len(demo_trajectory["joint_positions"]))
                source_duration_s = float(max(source_frames - 1, 0)) / source_fps
                min_replay_steps = _trajectory_realtime_step_count(
                    task_env,
                    demo_trajectory,
                    start_blend_steps=int(args_cli.demo_start_blend_steps),
                )
                demo_steps = max(int(demo_steps), int(min_replay_steps))
                demo_trajectory_timing_summary = {
                    "mode": "realtime",
                    "source_fps": float(source_fps),
                    "source_frames": int(source_frames),
                    "source_duration_s": float(source_duration_s),
                    "env_control_dt_s": float(_env_control_dt(task_env)),
                    "requested_demo_steps": int(requested_demo_steps),
                    "min_replay_steps": int(min_replay_steps),
                    "final_demo_steps": int(demo_steps),
                }
            else:
                demo_trajectory_timing_summary = {
                    "mode": "stretch",
                    "requested_demo_steps": int(demo_steps),
                    "source_fps": float(_trajectory_source_fps(demo_trajectory)),
                    "source_frames": int(len(demo_trajectory["joint_positions"])),
                }
            scripted_place = demo_trajectory.get("scripted_place")
            if isinstance(scripted_place, dict):
                desired_drop = scripted_place.get("desired_object_drop_world")
                if isinstance(desired_drop, (list, tuple)) and len(desired_drop) == 3:
                    drop_world = torch.as_tensor(
                        desired_drop,
                        dtype=task_env.tcp_pos.dtype,
                        device=task_env.device,
                    ).view(1, 3)
                    scripted_transport_desired_drop_env = drop_world.repeat(task_env.num_envs, 1) - task_env.scene.env_origins
                segments = demo_trajectory.get("segments")
                if isinstance(segments, list):
                    for segment in segments:
                        if not isinstance(segment, dict):
                            continue
                        if str(segment.get("phase") or "") != "move_to_above_bin_scripted":
                            continue
                        start = int(segment.get("start") or 0)
                        count = max(int(segment.get("count") or 0), 1)
                        scripted_transport_drop_segment = (start, count)
                        break
            print(
                json.dumps(
                    {
                        "event": "demo_trajectory_loaded",
                        "source": trajectory_source,
                        "path": str(demo_trajectory_path),
                        "source_frames": int(len(demo_trajectory["joint_positions"])),
                        "source_fps": demo_trajectory.get("fps"),
                        "tabletop_rejected": demo_trajectory.get("tabletop_rejected"),
                        "tabletop_status": demo_trajectory.get("tabletop_status"),
                        "nominal_status": demo_trajectory.get("nominal_status"),
                        "replay_mode": str(args_cli.demo_trajectory_replay_mode),
                        "timing_mode": str(args_cli.demo_trajectory_timing_mode),
                        "start_blend_steps": int(args_cli.demo_start_blend_steps),
                        "start_error": demo_trajectory_start_error,
                        "timing": demo_trajectory_timing_summary,
                    }
                ),
                flush=True,
            )
        elif trajectory_source == "dextrah_table_rejection":
            if robot is None or demo_start_joint_pos is None:
                raise AttributeError("dextrah_table_rejection requires a robot articulation")
            demo_table_rejection_target_joint_pos = _dextrah_table_rejection_full_target_joint_pos(task_env)
            print(
                json.dumps(
                    {
                        "event": "demo_dextrah_table_rejection_target_loaded",
                        "source": trajectory_source,
                        "target_fraction": float(args_cli.demo_table_rejection_target_fraction),
                        "full_target_joint_position": _tensor_list(demo_table_rejection_target_joint_pos),
                    }
                ),
                flush=True,
            )
    planned_steps = settle_steps if args_cli.demo_mode == "settle" else demo_steps
    target_frame_count = None
    capture_step_set: set[int] | None = None
    if args_cli.video_seconds is not None:
        target_frame_count = max(int(round(float(args_cli.video_seconds) * int(args_cli.fps))), 1)
        planned_steps, capture_step_set = _capture_steps_for_video(planned_steps, target_frame_count)
        if args_cli.demo_mode == "settle":
            settle_steps = planned_steps
        else:
            demo_steps = planned_steps
        print(
            json.dumps(
                {
                    "event": "video_seconds_capture_plan",
                    "demo_mode": args_cli.demo_mode,
                    "video_seconds": float(args_cli.video_seconds),
                    "fps": int(args_cli.fps),
                    "target_frame_count": int(target_frame_count),
                    "planned_steps": int(planned_steps),
                    "capture_steps": int(len(capture_step_set)),
                }
            ),
            flush=True,
        )
    frame_idx = 1
    scripted_transport_enabled = False
    scripted_transport_started_step = None
    scripted_transport_released_step = None
    scripted_transport_place_start_pos = None
    if bool(args_cli.repeat_initial_frame_for_video):
        if target_frame_count is None:
            raise ValueError("--repeat_initial_frame_for_video requires --video_seconds")
        for frame_idx in range(1, int(target_frame_count)):
            repeat_frame = frames[0].copy()
            frame_path = str(frame_dir / f"frame_{frame_idx:04d}.png")
            imageio.imwrite(frame_path, repeat_frame)
            frames.append(repeat_frame)
            frame_paths.append(frame_path)
        settle_steps = 0
        demo_steps = 0
        print(
            json.dumps(
                {
                    "event": "initial_frame_repeated",
                    "frame_count": len(frames),
                    "video_seconds": float(args_cli.video_seconds),
                    "fps": int(args_cli.fps),
                }
            ),
            flush=True,
        )
    elif single_yam_demo_enabled:
        scripted_transport_enabled = bool(args_cli.scripted_target_transport)
        scripted_transport_offset = None
        scripted_transport_quat = None
        for step_idx in range(1, demo_steps + 1):
            joint_position = None
            joint_velocity = None
            source_frame_idx = None
            trajectory_timing = None
            if demo_trajectory is not None:
                joint_position, joint_velocity, phase, source_frame_idx, trajectory_timing = (
                    _single_yam_rejected_trajectory_joint_position(
                        task_env,
                        demo_trajectory,
                        step_idx,
                        demo_steps,
                        start_joint_pos=demo_start_joint_pos,
                        start_blend_steps=int(args_cli.demo_start_blend_steps),
                        timing_mode=str(args_cli.demo_trajectory_timing_mode),
                    )
                )
                if args_cli.demo_trajectory_replay_mode == "dynamic":
                    velocity_target = joint_velocity if bool(args_cli.demo_trajectory_velocity_targets) else None
                    terminated, truncated = _apply_dynamic_joint_position_target(
                        task_env,
                        joint_position,
                        velocity_target,
                        velocity_target_scale=float(args_cli.demo_trajectory_velocity_target_scale),
                    )
                else:
                    terminated, truncated = _apply_kinematic_joint_position(task_env, joint_position)
                actions = torch.zeros((task_env.num_envs, int(task_env.cfg.action_space)), device=task_env.device)
                target_hold = task_env.hold_pos.detach().clone()
            elif args_cli.demo_trajectory_source == "dextrah_table_rejection":
                if demo_start_joint_pos is None:
                    raise AttributeError("dextrah_table_rejection requires a captured start joint position")
                joint_position, phase, demo_table_rejection_target_joint_pos = (
                    _single_yam_dextrah_table_rejection_joint_position(
                        task_env,
                        step_idx,
                        demo_steps,
                        start_joint_pos=demo_start_joint_pos,
                        target_fraction=float(args_cli.demo_table_rejection_target_fraction),
                    )
                )
                terminated, truncated = _apply_kinematic_joint_position(task_env, joint_position)
                actions = torch.zeros((task_env.num_envs, int(task_env.cfg.action_space)), device=task_env.device)
                target_hold = task_env.hold_pos.detach().clone()
            else:
                actions, phase, target_hold = _single_yam_rejected_path_action(
                    task_env,
                    step_idx,
                    demo_steps,
                    high_hold_z=float(args_cli.demo_high_hold_z),
                    low_hold_z=float(args_cli.demo_low_hold_z),
                )
                terminated, truncated = _manual_action_step(task_env, actions)
            if scripted_transport_enabled:
                phase_text = str(phase)
                carry_tokens = (
                    "lift_object",
                    "hold_after_lift",
                    "move_to_above_bin_scripted",
                    "hold_above_bin",
                )
                if scripted_transport_desired_drop_env is not None:
                    carry_tokens = (*carry_tokens, "open_fingers_to_drop")
                carry_target = any(
                    token in phase_text
                    for token in carry_tokens
                )
                if carry_target:
                    if scripted_transport_offset is None:
                        target_pos_env = task_env._cube.data.root_pos_w - task_env.scene.env_origins
                        scripted_transport_offset = (target_pos_env - task_env.tcp_pos).detach().clone()
                        scripted_transport_quat = task_env._cube.data.root_quat_w.detach().clone()
                        scripted_transport_started_step = int(step_idx)
                    target_pos_env = task_env.tcp_pos + scripted_transport_offset
                    if scripted_transport_desired_drop_env is not None:
                        if "move_to_above_bin_scripted" in phase_text:
                            if scripted_transport_place_start_pos is None:
                                scripted_transport_place_start_pos = target_pos_env.detach().clone()
                            if scripted_transport_drop_segment is not None:
                                segment_start, segment_count = scripted_transport_drop_segment
                                alpha = float(source_frame_idx - segment_start) / float(max(segment_count - 1, 1))
                                alpha = max(0.0, min(1.0, alpha))
                            else:
                                alpha = 0.0
                            target_pos_env = (
                                scripted_transport_place_start_pos
                                + float(alpha) * (scripted_transport_desired_drop_env - scripted_transport_place_start_pos)
                            )
                        elif any(token in phase_text for token in ("hold_above_bin", "open_fingers_to_drop")):
                            target_pos_env = scripted_transport_desired_drop_env
                    _set_target_root_pose_env(task_env, target_pos_env, scripted_transport_quat)
                release_tokens = ("hold_after_drop",) if scripted_transport_desired_drop_env is not None else (
                    "open_fingers_to_drop",
                    "hold_after_drop",
                )
                if scripted_transport_offset is not None and scripted_transport_released_step is None and any(
                    token in phase_text for token in release_tokens
                ):
                    scripted_transport_released_step = int(step_idx)
            row = _single_yam_rejected_path_row(
                task_env,
                step_idx=step_idx,
                phase=phase,
                target_hold=target_hold,
                actions=actions,
                terminated=terminated,
                truncated=truncated,
                joint_position=joint_position,
                source_frame_idx=source_frame_idx,
                trajectory_timing=trajectory_timing,
                trajectory_path=None if demo_trajectory_path is None else str(demo_trajectory_path),
            )
            demo_step_rows.append(row)
            if record_trajectory_dataset:
                dataset_terminated = None
                dataset_truncated = None
                if demo_trajectory is not None:
                    dataset_terminated = torch.zeros_like(terminated, dtype=torch.bool)
                    dataset_truncated = torch.zeros_like(truncated, dtype=torch.bool)
                    if step_idx >= demo_steps:
                        dataset_terminated[:] = True
                sample = _demo_dataset_sample(
                    task_env,
                    step_idx=step_idx,
                    phase=phase,
                    actions=actions,
                    terminated=terminated,
                    truncated=truncated,
                    dataset_terminated=dataset_terminated,
                    dataset_truncated=dataset_truncated,
                    joint_position=joint_position,
                    joint_velocity=joint_velocity,
                    source_frame_idx=source_frame_idx,
                )
                _append_demo_dataset_sample(trajectory_dataset, sample)
                record_rgb_interval = max(int(args_cli.record_rgb_interval), 1)
                if step_idx == 1 or step_idx == demo_steps or step_idx % record_rgb_interval == 0:
                    if bool(args_cli.record_multicam_rgb):
                        rgb_views = _capture_policy_rgb_streams(
                            env,
                            task_env,
                            args_cli,
                            scene_eye=eye,
                            scene_target=target,
                            wrist_camera=wrist_camera,
                            camera_dt=_env_control_dt(task_env),
                        )
                        for view_key, view_rgb in rgb_views.items():
                            trajectory_rgb_streams.setdefault(view_key, []).append(view_rgb.copy())
                        rgb = rgb_views.get("scene_rgb")
                        if rgb is None:
                            if not rgb_views:
                                raise ValueError("--record_multicam_rgb requires at least one enabled RGB stream")
                            rgb = next(iter(rgb_views.values()))
                    else:
                        rgb = _resize_rgb_nearest(
                            _frame_array(env.render()),
                            int(args_cli.record_rgb_height),
                            int(args_cli.record_rgb_width),
                        )
                    trajectory_rgb_frames.append(rgb.copy())
                    trajectory_rgb_step_idx.append(int(step_idx))
            rejected = torch.as_tensor(
                task_env.finger_table_clearance
                < float(getattr(task_env.cfg, "finger_table_penetration_termination_margin", -0.008)),
                device=task_env.device,
            )
            done = torch.logical_or(terminated, truncated)
            if first_rejected_step is None and bool(rejected.any().detach().cpu().item()):
                first_rejected_step = int(step_idx)
                print(
                    json.dumps(
                        {
                            "event": "rejected_path_detected",
                            "step_idx": int(step_idx),
                            "finger_table_clearance": _tensor_list(task_env.finger_table_clearance),
                        }
                    ),
                    flush=True,
                )
            if first_done_step is None and bool(done.any().detach().cpu().item()):
                first_done_step = int(step_idx)
            should_capture = (
                step_idx in capture_step_set
                if capture_step_set is not None
                else (step_idx % capture_interval == 0 or step_idx == demo_steps)
            )
            if should_capture:
                frame, frame_path = _capture_frame(env, frame_dir, frame_idx)
                frames.append(frame)
                frame_paths.append(frame_path)
                print(
                    json.dumps(
                        {
                            "event": "frame_captured",
                            "frame_idx": int(frame_idx),
                            "step_idx": int(step_idx),
                            "phase": phase,
                        }
                    ),
                    flush=True,
                )
                frame_idx += 1
    else:
        for step_idx in range(1, settle_steps + 1):
            _step_physics_without_task_reset(task_env, hold_joint_pos)
            if bool(args_cli.freeze_object_roots_for_video):
                _restore_root_snapshot(task_env, initial_snapshot)
            should_capture = (
                step_idx in capture_step_set
                if capture_step_set is not None
                else (step_idx % capture_interval == 0 or step_idx == settle_steps)
            )
            if should_capture:
                frame, frame_path = _capture_frame(env, frame_dir, frame_idx)
                frames.append(frame)
                frame_paths.append(frame_path)
                print(
                    json.dumps({"event": "frame_captured", "frame_idx": int(frame_idx), "step_idx": int(step_idx)}),
                    flush=True,
                )
                frame_idx += 1

    if bool(args_cli.freeze_object_roots_for_video):
        _restore_root_snapshot(task_env, initial_snapshot)
    final_snapshot = _root_snapshot(task_env)
    final_velocity_summary = _root_velocity_summary(task_env)
    initial_clearance_summary = _initial_clearance_summary(task_env, initial_snapshot)
    final_clearance_summary = _initial_clearance_summary(task_env, final_snapshot)
    stable_scene_written = False
    stable_scene_output_path = (
        Path(args_cli.stable_scene_output_path).expanduser().resolve()
        if args_cli.stable_scene_output_path
        else None
    )
    if stable_scene_input is None or stable_scene_output_path is not None:
        stable_scene = _stable_scene_payload(
            task_env,
            output_dir=(stable_scene_output_path or stable_scene_path).parent,
            task=str(args_cli.task),
            seed=int(args_cli.seed),
            settle_steps=int(settle_steps if args_cli.demo_mode == "settle" else 0),
            initial_snapshot=initial_snapshot,
            stable_snapshot=final_snapshot,
            initial_velocity_summary=initial_velocity_summary,
            stable_velocity_summary=final_velocity_summary,
            initial_clearance_summary=initial_clearance_summary,
            stable_clearance_summary=final_clearance_summary,
        )
        stable_write_path = stable_scene_output_path or stable_scene_path
        stable_write_path.parent.mkdir(parents=True, exist_ok=True)
        stable_write_path.write_text(json.dumps(_jsonable(stable_scene), indent=2), encoding="utf-8")
        stable_scene_written = True
        print(
            json.dumps(
                {
                    "event": "stable_scene_written",
                    "path": str(stable_write_path),
                    "settle_steps": int(settle_steps if args_cli.demo_mode == "settle" else 0),
                }
            ),
            flush=True,
        )
    _write_video(video_path, frames, int(args_cli.fps))
    print(json.dumps({"event": "video_written", "path": str(video_path), "frame_count": len(frames)}), flush=True)
    trajectory_dataset_summary: dict[str, object] = {
        "enabled": bool(record_trajectory_dataset),
        "requested": bool(args_cli.record_trajectory_dataset),
        "path": str(trajectory_dataset_path),
        "record_rgb_width": int(args_cli.record_rgb_width),
        "record_rgb_height": int(args_cli.record_rgb_height),
        "record_rgb_interval": int(args_cli.record_rgb_interval),
        "reason": None if record_trajectory_dataset else "not_requested_or_not_single_yam_trajectory",
    }
    if record_trajectory_dataset:
        trajectory_dataset_summary = _write_demo_dataset_npz(
            trajectory_dataset_path,
            dataset=trajectory_dataset,
            rgb_frames=trajectory_rgb_frames,
            rgb_step_idx=trajectory_rgb_step_idx,
            rgb_streams=trajectory_rgb_streams,
            metadata={
                "task": str(args_cli.task),
                "seed": int(args_cli.seed),
                "demo_mode": str(args_cli.demo_mode),
                "trajectory_source": str(args_cli.demo_trajectory_source),
                "trajectory_path": None if demo_trajectory_path is None else str(demo_trajectory_path),
                "stable_scene_path": str(stable_scene_path),
                "video_path": str(video_path),
                "fps": int(args_cli.fps),
                "control_dt_s": float(_env_control_dt(task_env)),
                "demo_steps": int(demo_steps),
                "source_timing": demo_trajectory_timing_summary,
                "trajectory_total_frames": None if demo_trajectory is None else demo_trajectory.get("total_frames"),
                "trajectory_segments": None if demo_trajectory is None else demo_trajectory.get("segments"),
                "trajectory_object_count": None if demo_trajectory is None else demo_trajectory.get("object_count"),
                "trajectory_object_sequence": None if demo_trajectory is None else demo_trajectory.get("object_sequence"),
                "yam_policy_scene_randomization": getattr(
                    task_env.cfg,
                    "yam_policy_scene_randomization_summary",
                    {"enabled": False},
                ),
                "scene_camera": scene_camera_summary,
                "record_multicam_rgb": {
                    "enabled": bool(args_cli.record_multicam_rgb),
                    "scene_rgb": bool(args_cli.record_scene_rgb),
                    "wrist_rgb": bool(args_cli.record_wrist_rgb),
                    "wrist_camera_model": "single_yam_link6_d405_sensor"
                    if wrist_camera is not None
                    else "virtual_tcp_relative_d405_view",
                    "wrist_camera_mode": str(args_cli.wrist_camera_mode),
                    "wrist_camera_sensor": wrist_camera_summary,
                    "wrist_camera_pos_offset": [float(v) for v in args_cli.wrist_camera_pos_offset],
                    "wrist_camera_forward": [float(v) for v in args_cli.wrist_camera_forward],
                },
            },
        )
        trajectory_dataset_summary.update(
            {
                "enabled": True,
                "requested": True,
                "record_rgb_width": int(args_cli.record_rgb_width),
                "record_rgb_height": int(args_cli.record_rgb_height),
                "record_rgb_interval": int(args_cli.record_rgb_interval),
                "reason": None,
            }
        )
        print(json.dumps({"event": "trajectory_dataset_written", **trajectory_dataset_summary}), flush=True)

    metrics = {
        "task": args_cli.task,
        "num_envs": int(task_env.num_envs),
        "seed": int(args_cli.seed),
        "demo_mode": args_cli.demo_mode,
        "settle_steps": int(settle_steps),
        "demo_steps": int(demo_steps),
        "capture_interval": int(capture_interval),
        "fps": int(args_cli.fps),
        "video_seconds": None if args_cli.video_seconds is None else float(args_cli.video_seconds),
        "target_frame_count": target_frame_count,
        "single_yam_rejected_path_demo": {
            "enabled": bool(single_yam_demo_enabled),
            "high_hold_z": float(args_cli.demo_high_hold_z),
            "low_hold_z": float(args_cli.demo_low_hold_z),
            "trajectory_source": str(args_cli.demo_trajectory_source),
            "trajectory_replay_mode": str(args_cli.demo_trajectory_replay_mode),
            "trajectory_timing_mode": str(args_cli.demo_trajectory_timing_mode),
            "trajectory_velocity_targets": bool(args_cli.demo_trajectory_velocity_targets),
            "trajectory_velocity_target_scale": float(args_cli.demo_trajectory_velocity_target_scale),
            "scripted_target_transport": {
                "enabled": bool(scripted_transport_enabled),
                "started_step": scripted_transport_started_step,
                "released_step": scripted_transport_released_step,
                "desired_drop_env": None
                if scripted_transport_desired_drop_env is None
                else _tensor_list(scripted_transport_desired_drop_env),
                "drop_segment": None
                if scripted_transport_drop_segment is None
                else {
                    "start": int(scripted_transport_drop_segment[0]),
                    "count": int(scripted_transport_drop_segment[1]),
                },
            },
            "trajectory_replay_enabled": demo_trajectory is not None,
            "trajectory_path": None if demo_trajectory_path is None else str(demo_trajectory_path),
            "trajectory_source_frames": None
            if demo_trajectory is None
            else int(len(demo_trajectory["joint_positions"])),
            "trajectory_source_fps": None if demo_trajectory is None else demo_trajectory.get("fps"),
            "trajectory_timing": demo_trajectory_timing_summary,
            "trajectory_tabletop_rejected": None
            if demo_trajectory is None
            else demo_trajectory.get("tabletop_rejected"),
            "trajectory_tabletop_status": None if demo_trajectory is None else demo_trajectory.get("tabletop_status"),
            "trajectory_nominal_status": None if demo_trajectory is None else demo_trajectory.get("nominal_status"),
            "trajectory_segments": None if demo_trajectory is None else demo_trajectory.get("segments"),
            "start_blend_steps": int(args_cli.demo_start_blend_steps),
            "trajectory_start_error": demo_trajectory_start_error,
            "table_rejection_target_fraction": float(args_cli.demo_table_rejection_target_fraction),
            "table_rejection_target_joint_position": None
            if demo_table_rejection_target_joint_pos is None
            else _tensor_list(demo_table_rejection_target_joint_pos),
            "first_rejected_step": first_rejected_step,
            "first_done_step": first_done_step,
            "step_count": len(demo_step_rows),
            "joint_target_velocity_summary": _row_max_abs_summary(demo_step_rows, "joint_target_velocity"),
            "actual_joint_velocity_summary": _row_max_abs_summary(demo_step_rows, "actual_joint_velocity"),
            "joint_tracking_error_summary": _row_scalar_summary(demo_step_rows, "joint_tracking_error_max_abs"),
            "step_rows": demo_step_rows,
        },
        "trajectory_dataset": trajectory_dataset_summary,
        "camera_eye": [float(v) for v in eye],
        "camera_target": [float(v) for v in target],
        "scene_camera": scene_camera_summary,
        "yam_policy_tabletop_surround": yam_policy_tabletop_surround_summary,
        "app_rendering_mode": getattr(args_cli, "rendering_mode", None),
        "yam_policy_scene_randomization": getattr(
            task_env.cfg,
            "yam_policy_scene_randomization_summary",
            {"enabled": False},
        ),
        "yam_arm_control_gains": yam_arm_control_gains,
        "yam_gripper_control_gains": yam_gripper_control_gains,
        "render_resolution": [int(v) for v in task_env.cfg.viewer.resolution]
        if hasattr(task_env.cfg, "viewer")
        else render_resolution,
        "training_env_render_scene": {
            "ground_plane_size": [float(v) for v in getattr(task_env.cfg, "ground_plane_size", ())],
            "ground_plane_color": None
            if getattr(task_env.cfg, "ground_plane_color", None) is None
            else [float(v) for v in getattr(task_env.cfg, "ground_plane_color")],
            "ground_plane_z": float(getattr(task_env.cfg, "ground_plane_z", 0.0)),
            "ground_plane_thickness": float(getattr(task_env.cfg, "ground_plane_thickness", 0.0)),
            "ground_grid_enabled": bool(getattr(task_env.cfg, "ground_grid_enabled", False)),
            "ground_grid_spacing": float(getattr(task_env.cfg, "ground_grid_spacing", 0.0)),
            "ground_grid_line_width": float(getattr(task_env.cfg, "ground_grid_line_width", 0.0)),
            "ground_grid_line_height": float(getattr(task_env.cfg, "ground_grid_line_height", 0.0)),
            "ground_grid_color": [float(v) for v in getattr(task_env.cfg, "ground_grid_color", ())],
            "dome_light_intensity": float(getattr(task_env.cfg, "dome_light_intensity", 0.0)),
            "dome_light_exposure": float(getattr(task_env.cfg, "dome_light_exposure", 0.0)),
            "dome_light_color": [float(v) for v in getattr(task_env.cfg, "dome_light_color", ())],
            "key_light_enabled": bool(getattr(task_env.cfg, "key_light_enabled", False)),
            "key_light_intensity": float(getattr(task_env.cfg, "key_light_intensity", 0.0)),
            "key_light_exposure": float(getattr(task_env.cfg, "key_light_exposure", 0.0)),
            "key_light_color": [float(v) for v in getattr(task_env.cfg, "key_light_color", ())],
            "key_light_angle": float(getattr(task_env.cfg, "key_light_angle", 0.0)),
            "key_light_rotation_deg": [float(v) for v in getattr(task_env.cfg, "key_light_rotation_deg", ())],
            "table_visual_diffuse_color": [
                float(v)
                for v in getattr(
                    getattr(getattr(task_env.cfg.table, "spawn", None), "visual_material", None),
                    "diffuse_color",
                    (),
                )
            ],
            "tabletop_goal_bin_floor_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_goal_bin_floor_color", ())
            ],
            "tabletop_goal_bin_x_wall_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_goal_bin_x_wall_color", ())
            ],
            "tabletop_goal_bin_y_wall_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_goal_bin_y_wall_color", ())
            ],
            "tabletop_goal_bin_visual_roughness": float(
                getattr(task_env.cfg, "tabletop_goal_bin_visual_roughness", 0.0)
            ),
            "tabletop_source_bin_floor_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_source_bin_floor_color", ())
            ],
            "tabletop_source_bin_x_wall_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_source_bin_x_wall_color", ())
            ],
            "tabletop_source_bin_y_wall_color": [
                float(v) for v in getattr(task_env.cfg, "tabletop_source_bin_y_wall_color", ())
            ],
            "tabletop_source_bin_visual_roughness": float(
                getattr(task_env.cfg, "tabletop_source_bin_visual_roughness", 0.0)
            ),
        },
        "freeze_object_roots_for_video": bool(args_cli.freeze_object_roots_for_video),
        "repeat_initial_frame_for_video": bool(args_cli.repeat_initial_frame_for_video),
        "robot_debug_site_visibility": robot_debug_site_visibility_summary,
        "visual_object_overlay": {
            "enabled": bool(args_cli.visual_object_overlay),
            "z_offset": float(args_cli.visual_object_overlay_z_offset),
            "objects": visual_object_overlay_summary,
        },
        "grasp_pose_overlay": grasp_pose_overlay_summary,
        "stable_scene": {
            "path": str(stable_scene_path),
            "input_path": None if stable_scene_input_path is None else str(stable_scene_input_path),
            "input_loaded": stable_scene_input is not None,
            "restore": stable_scene_restore_summary,
            "written": bool(stable_scene_written),
        },
        "video_path": str(video_path),
        "frame_paths": frame_paths,
        "frame_count": len(frame_paths),
        "asset_manifest_paths": {
            "object": args_cli.object_asset_manifest_path,
            "tabletop_clutter": args_cli.tabletop_clutter_asset_manifest_path,
        },
        "asset_config": {
            "object_asset_manifest_path": str(getattr(task_env.cfg, "object_asset_manifest_path", "")),
            "object_assets_dir": str(getattr(task_env.cfg, "object_assets_dir", "")),
            "require_graspgen_scale": bool(getattr(task_env.cfg, "require_graspgen_scale", False)),
            "tabletop_clutter_asset_manifest_path": str(
                getattr(task_env.cfg, "tabletop_clutter_asset_manifest_path", "")
            ),
            "tabletop_clutter_assets_dir": str(getattr(task_env.cfg, "tabletop_clutter_assets_dir", "")),
            "tabletop_clutter_require_graspgen_scale": bool(
                getattr(task_env.cfg, "tabletop_clutter_require_graspgen_scale", False)
            ),
        },
        "objaverse_textured_assets": objaverse_textured_summary,
        "multi_object_asset_summary": task_env.multi_object_asset_summary()
        if hasattr(task_env, "multi_object_asset_summary")
        else None,
        "tabletop_clutter_summary": task_env.tabletop_clutter_summary()
        if hasattr(task_env, "tabletop_clutter_summary")
        else None,
        "initial_snapshot": initial_snapshot,
        "initial_velocity_summary": initial_velocity_summary,
        "initial_clearance_summary": initial_clearance_summary,
        "final_snapshot": final_snapshot,
        "final_velocity_summary": final_velocity_summary,
        "final_clearance_summary": final_clearance_summary,
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"video_path": str(video_path), "metrics_path": str(metrics_path)}, indent=2), flush=True)
    env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        traceback.print_exc()
        print(
            json.dumps(
                {
                    "event": "main_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            ),
            flush=True,
        )
        raise
    finally:
        simulation_app.close()
