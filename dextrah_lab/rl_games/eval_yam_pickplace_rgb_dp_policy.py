"""Evaluate a two-camera RGB Diffusion Policy checkpoint on single-YAM pick-place.

The policy receives only scene RGB, wrist RGB, and robot proprioception.  The
task state is used for evaluation metrics only; object/bin/phase/progress state
is never passed to the policy.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


DEFAULT_SCENE_CAMERA_EYE = (-0.50, 0.04, 0.68)
DEFAULT_SCENE_CAMERA_TARGET = (-0.25, 0.04, 0.03)
DEFAULT_YAM_ARM_QPOS = (0.0, 1.0, 1.0, -1.5, 0.0, 0.0)
ACTION_NAMES = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]
SURFACE_TEXTURE_EXTS = (".jpg", ".jpeg", ".png")
DOME_TEXTURE_EXTS = (".hdr", ".exr", ".jpg", ".jpeg", ".png")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", type=str, required=True)
parser.add_argument("--diffusion_policy_root", type=str, default=None)
parser.add_argument("--task", type=str, default="Dextrah-Single-YAM-Single-Object-Policy-Grasp")
parser.add_argument("--num_episodes", type=int, default=20)
parser.add_argument("--num_steps", type=int, default=720)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--num_inference_steps", type=int, default=100)
parser.add_argument("--num_action_samples", type=int, default=1)
parser.add_argument("--policy_sample_seed", type=int, default=None)
parser.add_argument("--action_chunk_steps", type=int, default=8)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument("--stop_on_done", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--print_interval", type=int, default=20)
parser.add_argument("--image_height", type=int, default=256)
parser.add_argument("--image_width", type=int, default=256)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=720)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--video_name_prefix", type=str, default="yam-pickplace-rgb-dp-eval")
parser.add_argument("--camera_eye", type=float, nargs=3, default=DEFAULT_SCENE_CAMERA_EYE)
parser.add_argument("--camera_target", type=float, nargs=3, default=DEFAULT_SCENE_CAMERA_TARGET)
parser.add_argument("--scene_camera_eye_jitter", type=float, nargs=3, default=(0.018, 0.018, 0.018))
parser.add_argument("--scene_camera_target_jitter", type=float, nargs=3, default=(0.012, 0.012, 0.012))
parser.add_argument("--yam_policy_scene_randomization", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--yam_policy_object_x_range", type=float, nargs=2, default=(-0.34, -0.22))
parser.add_argument("--yam_policy_object_y_range", type=float, nargs=2, default=(-0.16, -0.04))
parser.add_argument("--yam_policy_bin_x_range", type=float, nargs=2, default=(-0.32, -0.12))
parser.add_argument("--yam_policy_bin_y_range", type=float, nargs=2, default=(0.10, 0.26))
parser.add_argument("--yam_policy_bin_inner_size_x_range", type=float, nargs=2, default=(0.22, 0.32))
parser.add_argument("--yam_policy_bin_inner_size_y_range", type=float, nargs=2, default=(0.16, 0.24))
parser.add_argument("--yam_policy_bin_wall_height_range", type=float, nargs=2, default=(0.08, 0.14))
parser.add_argument("--yam_policy_dome_light_intensity_range", type=float, nargs=2, default=(450.0, 1600.0))
parser.add_argument("--yam_policy_key_light_intensity_range", type=float, nargs=2, default=(250.0, 1400.0))
parser.add_argument("--yam_policy_material_value_range", type=float, nargs=2, default=(0.32, 0.82))
parser.add_argument("--yam_policy_table_texture_dir", type=str, default="")
parser.add_argument("--yam_policy_table_texture_tiling_range", type=float, nargs=2, default=(1.4, 3.8))
parser.add_argument("--yam_policy_dome_light_texture_dir", type=str, default="")
parser.add_argument("--yam_policy_object_asset_manifest_path", type=str, default="")
parser.add_argument("--yam_policy_object_assets_dir", type=str, default="")
parser.add_argument("--yam_policy_max_objects", type=int, default=0)
parser.add_argument("--yam_policy_object_validate_usd_bounds", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--yam_default_arm_qpos", type=float, nargs=6, default=DEFAULT_YAM_ARM_QPOS)
parser.add_argument("--yam_default_finger_qpos", type=float, default=-0.0475)
parser.add_argument("--yam_gripper_stiffness_scale", type=float, default=2.0)
parser.add_argument("--yam_gripper_damping_scale", type=float, default=0.25)
parser.add_argument("--yam_gripper_effort_scale", type=float, default=5.0)
parser.add_argument("--debug_obs_interval", type=int, default=0)
parser.add_argument("--debug_obs_max_frames", type=int, default=120)
parser.add_argument("--scene_rgb_capture_attempts", type=int, default=6)
parser.add_argument("--scene_rgb_black_mean_threshold", type=float, default=3.0)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch

import isaaclab.sim as sim_utils
import isaaclab_tasks  # noqa: F401
import omni.usd
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab_tasks.utils import parse_env_cfg
from pxr import Gf, Sdf, UsdGeom, UsdShade

import dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.gym_setup  # noqa: F401
from dextrah_lab.assets.yam.bimanual_yam import (
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_WRIST_CAMERA_INTRINSIC,
    MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
    MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
)


def _stage(name: str, **details: Any) -> None:
    print("YAM_RGB_DP_EVAL_STAGE " + json.dumps({"stage": name, **details}, sort_keys=True, default=str), flush=True)


def _tensor_numpy(value: torch.Tensor, dtype=np.float32) -> np.ndarray:
    return value.detach().cpu().numpy().astype(dtype, copy=False)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


def _mean_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _range_pair(values: tuple[float, float] | list[float], *, name: str) -> tuple[float, float]:
    lo, hi = float(values[0]), float(values[1])
    if not math.isfinite(lo) or not math.isfinite(hi) or hi < lo:
        raise ValueError(f"Invalid {name}: {values}")
    return lo, hi


def _rng_uniform(rng: np.random.Generator, values: tuple[float, float] | list[float], *, name: str) -> float:
    lo, hi = _range_pair(values, name=name)
    return float(rng.uniform(lo, hi))


def _random_color(rng: np.random.Generator, values: tuple[float, float] | list[float]) -> tuple[float, float, float]:
    lo, hi = _range_pair(values, name="yam_policy_material_value_range")
    return tuple(float(v) for v in rng.uniform(lo, hi, size=3))


def _scale_gain_value(value: Any, scale: float) -> Any:
    if isinstance(value, dict):
        return {key: _scale_gain_value(item, scale) for key, item in value.items()}
    if value is None:
        return None
    return float(value) * float(scale)


def _jsonable_gain_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable_gain_value(item) for key, item in value.items()}
    if value is None:
        return None
    return float(value)


def _apply_yam_actuator_gain_scales(env_cfg: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "enabled": False,
        "actuator_name": "gripper",
        "stiffness_scale": float(args_cli.yam_gripper_stiffness_scale),
        "damping_scale": float(args_cli.yam_gripper_damping_scale),
        "effort_scale": float(args_cli.yam_gripper_effort_scale),
    }
    actuators = getattr(getattr(env_cfg, "robot", None), "actuators", None)
    if not isinstance(actuators, dict) or "gripper" not in actuators:
        summary["reason"] = "missing_yam_gripper_actuator"
        return summary
    actuator = actuators["gripper"]
    summary["before"] = {
        "stiffness": _jsonable_gain_value(getattr(actuator, "stiffness", None)),
        "damping": _jsonable_gain_value(getattr(actuator, "damping", None)),
        "effort_limit_sim": _jsonable_gain_value(getattr(actuator, "effort_limit_sim", None)),
    }
    actuator.stiffness = _scale_gain_value(actuator.stiffness, float(args_cli.yam_gripper_stiffness_scale))
    actuator.damping = _scale_gain_value(actuator.damping, float(args_cli.yam_gripper_damping_scale))
    actuator.effort_limit_sim = _scale_gain_value(actuator.effort_limit_sim, float(args_cli.yam_gripper_effort_scale))
    summary["after"] = {
        "stiffness": _jsonable_gain_value(getattr(actuator, "stiffness", None)),
        "damping": _jsonable_gain_value(getattr(actuator, "damping", None)),
        "effort_limit_sim": _jsonable_gain_value(getattr(actuator, "effort_limit_sim", None)),
    }
    summary["enabled"] = True
    return summary


def _apply_yam_default_pose(env_cfg: Any) -> dict[str, Any]:
    joint_names = [f"joint{i}" for i in range(1, 7)]
    joint_pos = {name: float(value) for name, value in zip(joint_names, args_cli.yam_default_arm_qpos, strict=True)}
    joint_pos["left_finger"] = float(args_cli.yam_default_finger_qpos)
    joint_pos["right_finger"] = float(args_cli.yam_default_finger_qpos)
    robot_cfg = getattr(env_cfg, "robot", None)
    init_state = getattr(robot_cfg, "init_state", None)
    if init_state is not None:
        init_state.joint_pos = dict(joint_pos)
    return {"joint_pos": joint_pos}


def _apply_eval_episode_length(env_cfg: Any) -> dict[str, Any]:
    sim_dt = float(getattr(getattr(env_cfg, "sim", None), "dt", getattr(env_cfg, "sim_dt", 1.0 / 120.0)))
    decimation = int(getattr(env_cfg, "decimation", 1))
    env_dt = sim_dt * float(decimation)
    requested_steps = max(1, int(args_cli.num_steps))
    # Isaac Lab truncates at max_episode_length - 1, so leave a small step margin.
    required_episode_length_s = float(requested_steps + 2) * env_dt
    before = float(getattr(env_cfg, "episode_length_s", 0.0) or 0.0)
    after = max(before, required_episode_length_s)
    env_cfg.episode_length_s = float(after)
    return {
        "enabled": bool(after > before + 1e-9),
        "before_s": before,
        "after_s": float(after),
        "env_dt": float(env_dt),
        "decimation": int(decimation),
        "sim_dt": float(sim_dt),
        "requested_steps": int(requested_steps),
        "required_episode_length_s": float(required_episode_length_s),
    }


def _apply_object_asset_overrides(env_cfg: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {"enabled": False}
    manifest_path = str(args_cli.yam_policy_object_asset_manifest_path or "").strip()
    assets_dir = str(args_cli.yam_policy_object_assets_dir or "").strip()
    max_objects = int(args_cli.yam_policy_max_objects)
    validate_bounds = args_cli.yam_policy_object_validate_usd_bounds
    if manifest_path:
        env_cfg.object_asset_manifest_path = manifest_path
        summary["object_asset_manifest_path"] = manifest_path
        summary["enabled"] = True
    if assets_dir:
        env_cfg.object_assets_dir = assets_dir
        summary["object_assets_dir"] = assets_dir
        summary["enabled"] = True
    if max_objects > 0:
        env_cfg.max_objects = max_objects
        summary["max_objects"] = int(max_objects)
        summary["enabled"] = True
    if validate_bounds is not None:
        env_cfg.object_validate_usd_bounds = bool(validate_bounds)
        summary["object_validate_usd_bounds"] = bool(validate_bounds)
        summary["enabled"] = True
    return summary


def _apply_scene_randomization(env_cfg: Any, rng: np.random.Generator) -> dict[str, Any]:
    if not bool(args_cli.yam_policy_scene_randomization):
        return {"enabled": False}
    object_x_range = _range_pair(args_cli.yam_policy_object_x_range, name="yam_policy_object_x_range")
    object_y_range = _range_pair(args_cli.yam_policy_object_y_range, name="yam_policy_object_y_range")
    object_center_x = 0.5 * (object_x_range[0] + object_x_range[1])
    object_center_y = 0.5 * (object_y_range[0] + object_y_range[1])
    bin_x = _rng_uniform(rng, args_cli.yam_policy_bin_x_range, name="yam_policy_bin_x_range")
    bin_y = _rng_uniform(rng, args_cli.yam_policy_bin_y_range, name="yam_policy_bin_y_range")
    bin_inner_x = _rng_uniform(rng, args_cli.yam_policy_bin_inner_size_x_range, name="yam_policy_bin_inner_size_x_range")
    bin_inner_y = _rng_uniform(rng, args_cli.yam_policy_bin_inner_size_y_range, name="yam_policy_bin_inner_size_y_range")
    bin_wall_height = _rng_uniform(rng, args_cli.yam_policy_bin_wall_height_range, name="yam_policy_bin_wall_height_range")

    env_cfg.object_spawn_center_offset_x = object_center_x - float(env_cfg.table_center_x)
    env_cfg.object_spawn_center_offset_y = object_center_y - float(env_cfg.table_center_y)
    env_cfg.object_spawn_x_randomization = 0.5 * abs(object_x_range[1] - object_x_range[0])
    env_cfg.object_spawn_y_randomization = 0.5 * abs(object_y_range[1] - object_y_range[0])
    env_cfg.object_spawn_xy_randomization = 0.0
    env_cfg.tabletop_goal_bin_enabled = True
    env_cfg.tabletop_source_bin_enabled = False
    env_cfg.tabletop_goal_bin_center_offset_x = bin_x - float(env_cfg.table_center_x)
    env_cfg.tabletop_goal_bin_center_offset_y = bin_y - float(env_cfg.table_center_y)
    env_cfg.tabletop_goal_bin_inner_size_x = bin_inner_x
    env_cfg.tabletop_goal_bin_inner_size_y = bin_inner_y
    env_cfg.tabletop_goal_bin_wall_height = bin_wall_height
    env_cfg.tabletop_goal_bin_clearance = 0.08
    env_cfg.tabletop_goal_bin_placement_clearance = 0.08
    env_cfg.tabletop_goal_bin_success_xy_tol = min(0.12, 0.35 * min(bin_inner_x, bin_inner_y))
    env_cfg.cube_success_xy_tol = env_cfg.tabletop_goal_bin_success_xy_tol

    table_color = _random_color(rng, args_cli.yam_policy_material_value_range)
    ground_color = _random_color(rng, args_cli.yam_policy_material_value_range)
    bin_floor_color = _random_color(rng, args_cli.yam_policy_material_value_range)
    x_wall_color = _random_color(rng, args_cli.yam_policy_material_value_range)
    y_wall_color = _random_color(rng, args_cli.yam_policy_material_value_range)
    env_cfg.ground_plane_color = ground_color
    table_spawn = getattr(getattr(env_cfg, "table", None), "spawn", None)
    table_material = getattr(table_spawn, "visual_material", None)
    if table_material is not None and hasattr(table_material, "diffuse_color"):
        table_material.diffuse_color = tuple(float(v) for v in table_color)
        if hasattr(table_material, "roughness"):
            table_material.roughness = float(rng.uniform(0.45, 0.92))
    env_cfg.tabletop_goal_bin_floor_color = bin_floor_color
    env_cfg.tabletop_goal_bin_x_wall_color = x_wall_color
    env_cfg.tabletop_goal_bin_y_wall_color = y_wall_color
    env_cfg.tabletop_goal_bin_visual_roughness = float(rng.uniform(0.45, 0.92))
    env_cfg.dome_light_intensity = _rng_uniform(
        rng,
        args_cli.yam_policy_dome_light_intensity_range,
        name="yam_policy_dome_light_intensity_range",
    )
    env_cfg.key_light_enabled = True
    env_cfg.key_light_intensity = _rng_uniform(
        rng,
        args_cli.yam_policy_key_light_intensity_range,
        name="yam_policy_key_light_intensity_range",
    )
    env_cfg.key_light_rotation_deg = tuple(float(v) for v in rng.uniform((35.0, -8.0, -75.0), (72.0, 8.0, 35.0)))
    summary = {
        "enabled": True,
        "object_region": {
            "center_x": float(object_center_x),
            "center_y": float(object_center_y),
            "x_range": [float(v) for v in object_x_range],
            "y_range": [float(v) for v in object_y_range],
        },
        "goal_bin": {
            "center_x": float(bin_x),
            "center_y": float(bin_y),
            "inner_size_x": float(bin_inner_x),
            "inner_size_y": float(bin_inner_y),
            "wall_height": float(bin_wall_height),
        },
        "materials": {
            "table_color": [float(v) for v in table_color],
            "ground_color": [float(v) for v in ground_color],
            "goal_bin_floor_color": [float(v) for v in bin_floor_color],
            "goal_bin_x_wall_color": [float(v) for v in x_wall_color],
            "goal_bin_y_wall_color": [float(v) for v in y_wall_color],
        },
        "lighting": {
            "dome_light_intensity": float(env_cfg.dome_light_intensity),
            "key_light_intensity": float(env_cfg.key_light_intensity),
            "key_light_rotation_deg": [float(v) for v in env_cfg.key_light_rotation_deg],
        },
    }
    env_cfg.yam_policy_scene_randomization_summary = summary
    return summary


def _texture_candidates(
    raw_roots: str | None,
    *,
    exts: tuple[str, ...],
    include_tokens: tuple[str, ...] = (),
    exclude_tokens: tuple[str, ...] = (),
) -> list[Path]:
    if not raw_roots:
        return []
    allowed_exts = {item.lower() for item in exts}
    candidates: list[Path] = []
    for raw_root in str(raw_roots).split(os.pathsep):
        if not raw_root.strip():
            continue
        root = Path(raw_root).expanduser()
        if root.is_file() and root.suffix.lower() in allowed_exts:
            candidates.append(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in allowed_exts:
                    continue
                name = path.name.lower()
                if include_tokens and not any(token in name for token in include_tokens):
                    continue
                if exclude_tokens and any(token in name for token in exclude_tokens):
                    continue
                candidates.append(path)
    return sorted({path.resolve() for path in candidates})


def _sample_texture_path(
    rng: np.random.Generator,
    raw_roots: str | None,
    *,
    exts: tuple[str, ...],
    include_tokens: tuple[str, ...] = (),
    exclude_tokens: tuple[str, ...] = (),
) -> str:
    candidates = _texture_candidates(
        raw_roots,
        exts=exts,
        include_tokens=include_tokens,
        exclude_tokens=exclude_tokens,
    )
    if not candidates:
        return ""
    return str(candidates[int(rng.integers(0, len(candidates)))])


def _usd_texture_material(stage: Any, path: str, texture_file: str, *, roughness: float) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
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
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _usd_bind(prim: Any, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def _usd_add_xy_quad(
    stage: Any,
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
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in points])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateExtentAttr(
        [
            Gf.Vec3f(*(min(point[axis] for point in points) for axis in range(3))),
            Gf.Vec3f(*(max(point[axis] for point in points) for axis in range(3))),
        ]
    )
    st = UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar(
        "st",
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.faceVarying,
    )
    st.Set([Gf.Vec2f(0.0, 0.0), Gf.Vec2f(ux, 0.0), Gf.Vec2f(ux, uy), Gf.Vec2f(0.0, uy)])
    _usd_bind(mesh.GetPrim(), mat)


def _apply_eval_table_texture(task_env: Any, rng: np.random.Generator) -> dict[str, Any]:
    texture_path = _sample_texture_path(
        rng,
        args_cli.yam_policy_table_texture_dir,
        exts=SURFACE_TEXTURE_EXTS,
        include_tokens=("albedo", "diffuse", "diff", "basecolor", "color"),
        exclude_tokens=("normal", "orm", "rough", "metal", "height"),
    )
    if not texture_path:
        return {"enabled": False, "texture_dir": str(args_cli.yam_policy_table_texture_dir or "")}
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"enabled": False, "texture_path": texture_path, "reason": "missing_usd_stage"}
    tiling_range = _range_pair(args_cli.yam_policy_table_texture_tiling_range, name="yam_policy_table_texture_tiling_range")
    tiling = float(rng.uniform(tiling_range[0], tiling_range[1]))
    roughness = float(rng.uniform(0.60, 0.96))
    cfg = task_env.cfg
    looks_root = "/World/Looks/YAMPolicyEvalTexture"
    UsdGeom.Xform.Define(stage, looks_root)
    mat = _usd_texture_material(stage, f"{looks_root}/table_texture", texture_path, roughness=roughness)
    env_origins = task_env.scene.env_origins.detach().float().cpu().numpy()
    size_xy = (float(cfg.table_size_x), float(cfg.table_size_y))
    records: list[dict[str, Any]] = []
    for env_id, origin in enumerate(env_origins):
        center = (
            float(origin[0]) + float(cfg.table_center_x),
            float(origin[1]) + float(cfg.table_center_y),
            float(origin[2]) + float(cfg.table_surface_z) + 0.0008,
        )
        uv_scale = (tiling, tiling * max(0.1, size_xy[1] / max(size_xy[0], 1.0e-6)))
        path = f"/World/envs/env_{env_id}/YAMPolicyEvalTableTexture/full_surface"
        _usd_add_xy_quad(stage, path, center, size_xy, mat, uv_scale=uv_scale)
        records.append(
            {
                "env_id": int(env_id),
                "path": path,
                "center": [float(v) for v in center],
                "size": [float(v) for v in size_xy],
                "uv_scale": [float(v) for v in uv_scale],
            }
        )
    task_env.sim.forward()
    return {
        "enabled": True,
        "texture_dir": str(args_cli.yam_policy_table_texture_dir or ""),
        "texture_path": texture_path,
        "tiling": tiling,
        "roughness": roughness,
        "quads": records,
    }


def _apply_eval_dome_light_texture(rng: np.random.Generator) -> dict[str, Any]:
    texture_path = _sample_texture_path(
        rng,
        args_cli.yam_policy_dome_light_texture_dir,
        exts=DOME_TEXTURE_EXTS,
    )
    if not texture_path:
        return {"enabled": False, "texture_dir": str(args_cli.yam_policy_dome_light_texture_dir or "")}
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"enabled": False, "texture_path": texture_path, "reason": "missing_usd_stage"}
    light_prim = stage.GetPrimAtPath("/World/Light")
    if not light_prim.IsValid():
        return {"enabled": False, "texture_path": texture_path, "reason": "missing_world_light"}
    attr = light_prim.GetAttribute("inputs:texture:file")
    if not attr:
        attr = light_prim.CreateAttribute("inputs:texture:file", Sdf.ValueTypeNames.Asset)
    attr.Set(Sdf.AssetPath(texture_path))
    return {
        "enabled": True,
        "texture_dir": str(args_cli.yam_policy_dome_light_texture_dir or ""),
        "texture_path": texture_path,
    }


def _jitter_vec(
    rng: np.random.Generator,
    base: tuple[float, float, float] | list[float],
    jitter: tuple[float, float, float] | list[float],
) -> tuple[float, float, float]:
    return tuple(float(b + rng.uniform(-abs(j), abs(j))) for b, j in zip(base, jitter, strict=True))


def _jitter_scene_camera(
    rng: np.random.Generator,
) -> tuple[tuple[float, float, float], tuple[float, float, float], dict[str, Any]]:
    eye = tuple(float(v) for v in args_cli.camera_eye)
    target = tuple(float(v) for v in args_cli.camera_target)
    preserve_x_axis_projection = (
        abs(float(eye[1]) - float(target[1])) < 1.0e-6
        and abs(float(DEFAULT_SCENE_CAMERA_EYE[1]) - float(DEFAULT_SCENE_CAMERA_TARGET[1])) < 1.0e-6
    )
    if preserve_x_axis_projection:
        eye_jitter = tuple(float(v) for v in args_cli.scene_camera_eye_jitter)
        target_jitter = tuple(float(v) for v in args_cli.scene_camera_target_jitter)
        shared_y_radius = min(abs(eye_jitter[1]), abs(target_jitter[1]))
        shared_y_jitter = float(rng.uniform(-shared_y_radius, shared_y_radius))
        eye = (
            float(eye[0]) + float(rng.uniform(-abs(eye_jitter[0]), abs(eye_jitter[0]))),
            float(eye[1]) + shared_y_jitter,
            float(eye[2]) + float(rng.uniform(-abs(eye_jitter[2]), abs(eye_jitter[2]))),
        )
        target = (
            float(target[0]) + float(rng.uniform(-abs(target_jitter[0]), abs(target_jitter[0]))),
            float(target[1]) + shared_y_jitter,
            float(target[2]) + float(rng.uniform(-abs(target_jitter[2]), abs(target_jitter[2]))),
        )
        summary = {
            "eye_jitter": [float(v) for v in args_cli.scene_camera_eye_jitter],
            "target_jitter": [float(v) for v in args_cli.scene_camera_target_jitter],
            "xy_projection_axis": "x",
            "shared_y_jitter": shared_y_jitter,
        }
    else:
        eye = _jitter_vec(rng, eye, args_cli.scene_camera_eye_jitter)
        target = _jitter_vec(rng, target, args_cli.scene_camera_target_jitter)
        summary = {
            "eye_jitter": [float(v) for v in args_cli.scene_camera_eye_jitter],
            "target_jitter": [float(v) for v in args_cli.scene_camera_target_jitter],
            "xy_projection_axis": "free",
            "shared_y_jitter": None,
        }
    return eye, target, summary


def _configure_camera(env_cfg: Any, scene_eye: tuple[float, float, float], scene_target: tuple[float, float, float], task_env: Any | None = None) -> None:
    if hasattr(env_cfg, "viewer"):
        env_cfg.viewer.eye = tuple(float(v) for v in scene_eye)
        env_cfg.viewer.lookat = tuple(float(v) for v in scene_target)
        env_cfg.viewer.origin_type = "world"
    if task_env is not None and hasattr(task_env, "sim") and hasattr(env_cfg, "viewer"):
        task_env.sim.set_camera_view(
            eye=tuple(float(v) for v in scene_eye),
            target=tuple(float(v) for v in scene_target),
            camera_prim_path=env_cfg.viewer.cam_prim_path,
        )


def _frame_array(frame: Any) -> np.ndarray:
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


def _resize_rgb_nearest(frame: np.ndarray, height: int, width: int) -> np.ndarray:
    height = max(int(height), 1)
    width = max(int(width), 1)
    rgb = np.asarray(frame[..., :3])
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    if rgb.shape[0] == height and rgb.shape[1] == width:
        return rgb.copy()
    y_idx = np.linspace(0, rgb.shape[0] - 1, height).round().astype(np.int64)
    x_idx = np.linspace(0, rgb.shape[1] - 1, width).round().astype(np.int64)
    return rgb[y_idx[:, None], x_idx[None, :], :].copy()


def _render_scene_frame(gym_env: Any, task_env: Any) -> np.ndarray:
    # Prefer the unwrapped env so observation capture is independent of the
    # video wrapper's bookkeeping.
    for renderer in (task_env, gym_env):
        render_fn = getattr(renderer, "render", None)
        if render_fn is None:
            continue
        frame = render_fn()
        if frame is not None:
            return _frame_array(frame)
    raise RuntimeError("No scene renderer produced an RGB frame")


def _capture_scene_rgb(
    gym_env: Any,
    task_env: Any,
    scene_eye: tuple[float, float, float],
    scene_target: tuple[float, float, float],
) -> np.ndarray:
    attempts = max(1, int(args_cli.scene_rgb_capture_attempts))
    threshold = float(args_cli.scene_rgb_black_mean_threshold)
    last_frame: np.ndarray | None = None
    last_mean = 0.0
    for attempt in range(attempts):
        task_env.sim.set_camera_view(
            eye=scene_eye,
            target=scene_target,
            camera_prim_path=task_env.cfg.viewer.cam_prim_path,
        )
        task_env.sim.render()
        frame = _render_scene_frame(gym_env, task_env)
        last_frame = frame
        last_mean = float(np.asarray(frame[..., :3], dtype=np.float32).mean())
        if threshold <= 0.0 or last_mean >= threshold:
            if attempt > 0:
                _stage("scene_rgb_capture_recovered", attempt=attempt + 1, mean=last_mean)
            break
        _stage("scene_rgb_capture_retry", attempt=attempt + 1, mean=last_mean)
        task_env.sim.render()
    if last_frame is None:
        raise RuntimeError("Scene RGB capture failed without returning a frame")
    if threshold > 0.0 and last_mean < threshold:
        _stage("scene_rgb_capture_black_after_retries", attempts=attempts, mean=last_mean)
    return _resize_rgb_nearest(
        last_frame,
        int(args_cli.image_height),
        int(args_cli.image_width),
    )


def _save_debug_obs_frame(
    output_dir: Path,
    obs: dict[str, np.ndarray],
    *,
    episode: int,
    step: int,
    action: np.ndarray | None,
    paths: list[str],
) -> None:
    if len(paths) >= max(0, int(args_cli.debug_obs_max_frames)):
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        _stage("debug_obs_disabled", reason=f"pil_import_failed:{exc.__class__.__name__}")
        args_cli.debug_obs_interval = 0
        return
    scene = np.asarray(obs["scene_rgb"], dtype=np.uint8)
    wrist = np.asarray(obs["wrist_rgb"], dtype=np.uint8)
    if scene.shape != wrist.shape:
        return
    frame_h, frame_w = scene.shape[:2]
    header_h = 28
    canvas = Image.new("RGB", (frame_w * 2, frame_h + header_h), (18, 18, 18))
    canvas.paste(Image.fromarray(scene, mode="RGB"), (0, header_h))
    canvas.paste(Image.fromarray(wrist, mode="RGB"), (frame_w, header_h))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    label = f"ep={episode} step={step}"
    if action is not None:
        flat = np.asarray(action, dtype=np.float32).reshape(-1)
        label += " action=[" + ", ".join(f"{v:+.3f}" for v in flat[:7]) + "]"
    draw.text((6, 7), label, fill=(238, 238, 232), font=font)
    draw.text((max(2, frame_w // 2 - 38), frame_h + header_h - 15), "scene", fill=(238, 238, 232), font=font)
    draw.text((frame_w + max(2, frame_w // 2 - 34), frame_h + header_h - 15), "wrist", fill=(238, 238, 232), font=font)
    debug_dir = output_dir / "debug_obs"
    debug_dir.mkdir(parents=True, exist_ok=True)
    path = debug_dir / f"obs_ep{episode:03d}_step{step:04d}.png"
    canvas.save(path)
    paths.append(str(path))


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


def _spawn_d405_from_intrinsic() -> sim_utils.PinholeCameraCfg:
    return sim_utils.PinholeCameraCfg.from_intrinsic_matrix(
        intrinsic_matrix=list(MOLMOACT2_WRIST_CAMERA_INTRINSIC),
        width=MOLMOACT2_CAMERA_WIDTH,
        height=MOLMOACT2_CAMERA_HEIGHT,
        focal_length=24.0,
        focus_distance=400.0,
        clipping_range=(0.01, 10.0),
    )


def _make_single_yam_wrist_camera(task_env: Any) -> tuple[Camera, dict[str, Any]]:
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


def _robot_state(task_env: Any) -> np.ndarray:
    robot = task_env._robot
    actual_joint_position = _tensor_numpy(robot.data.joint_pos)
    actual_joint_velocity = _tensor_numpy(robot.data.joint_vel)
    task_env._compute_intermediate_values()
    tcp_pos = _tensor_numpy(task_env.tcp_pos)
    tcp_quat = _tensor_numpy(task_env.tcp_quat)
    gripper_width = _tensor_numpy(task_env.gripper_width).reshape((actual_joint_position.shape[0], -1))
    robot_state = np.concatenate(
        (actual_joint_position, actual_joint_velocity, tcp_pos, tcp_quat, gripper_width),
        axis=1,
    ).astype(np.float32, copy=False)
    if robot_state.shape != (1, 24):
        raise ValueError(f"Expected one-env 24D YAM robot_state, got {robot_state.shape}")
    return robot_state[0].copy()


def _capture_obs(
    gym_env: Any,
    task_env: Any,
    wrist_camera: Camera,
    scene_eye: tuple[float, float, float],
    scene_target: tuple[float, float, float],
) -> dict[str, np.ndarray]:
    scene_rgb = _capture_scene_rgb(gym_env, task_env, scene_eye, scene_target)
    task_env.scene.write_data_to_sim()
    task_env.sim.render()
    wrist_camera.update(float(task_env.dt), force_recompute=True)
    wrist_camera.update(0.0, force_recompute=True)
    wrist_rgb = _resize_rgb_nearest(
        _camera_rgb_array(wrist_camera.data.output["rgb"]),
        int(args_cli.image_height),
        int(args_cli.image_width),
    )
    task_env.sim.set_camera_view(
        eye=scene_eye,
        target=scene_target,
        camera_prim_path=task_env.cfg.viewer.cam_prim_path,
    )
    return {"scene_rgb": scene_rgb, "wrist_rgb": wrist_rgb, "robot_state": _robot_state(task_env)}


class RgbRobotObsHistory:
    def __init__(self, n_obs_steps: int, height: int, width: int, robot_state_dim: int = 24):
        self.n_obs_steps = int(n_obs_steps)
        self.height = int(height)
        self.width = int(width)
        self.robot_state_dim = int(robot_state_dim)
        self.scene_rgb = np.zeros((self.n_obs_steps, self.height, self.width, 3), dtype=np.uint8)
        self.wrist_rgb = np.zeros((self.n_obs_steps, self.height, self.width, 3), dtype=np.uint8)
        self.robot_state = np.zeros((self.n_obs_steps, self.robot_state_dim), dtype=np.float32)
        self.initialized = False

    def reset(self, obs: dict[str, np.ndarray]) -> None:
        robot_state = np.asarray(obs["robot_state"], dtype=np.float32)
        if robot_state.shape != (self.robot_state_dim,):
            raise ValueError(f"Expected robot_state shape ({self.robot_state_dim},), got {robot_state.shape}")
        self.scene_rgb[:] = np.asarray(obs["scene_rgb"], dtype=np.uint8)[None, ...]
        self.wrist_rgb[:] = np.asarray(obs["wrist_rgb"], dtype=np.uint8)[None, ...]
        self.robot_state[:] = robot_state[None, ...]
        self.initialized = True

    def push(self, obs: dict[str, np.ndarray]) -> None:
        if not self.initialized:
            self.reset(obs)
            return
        self.scene_rgb[:-1] = self.scene_rgb[1:]
        self.wrist_rgb[:-1] = self.wrist_rgb[1:]
        self.robot_state[:-1] = self.robot_state[1:]
        self.scene_rgb[-1] = np.asarray(obs["scene_rgb"], dtype=np.uint8)
        self.wrist_rgb[-1] = np.asarray(obs["wrist_rgb"], dtype=np.uint8)
        self.robot_state[-1] = np.asarray(obs["robot_state"], dtype=np.float32)

    def as_policy_obs(self, device: torch.device) -> dict[str, torch.Tensor]:
        scene = np.moveaxis(self.scene_rgb.astype(np.float32) / 255.0, -1, 1)
        wrist = np.moveaxis(self.wrist_rgb.astype(np.float32) / 255.0, -1, 1)
        return {
            "scene_rgb": torch.as_tensor(scene[None], dtype=torch.float32, device=device),
            "wrist_rgb": torch.as_tensor(wrist[None], dtype=torch.float32, device=device),
            "robot_state": torch.as_tensor(self.robot_state[None], dtype=torch.float32, device=device),
        }


def _collect_task_metrics(task_env: Any) -> dict[str, float | None]:
    names = [
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "in_success_region",
        "time_in_success_region",
        "hold_to_cube_dist",
        "gripper_width",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "cube_linear_speed",
        "cube_angular_speed",
        "grasp_success",
    ]
    return {name: _mean_float(getattr(task_env, name)) for name in names if hasattr(task_env, name)}


def _summarize_step_metrics(step_metrics: list[dict[str, float | int | None]]) -> dict[str, dict[str, float | int]]:
    summaries: dict[str, dict[str, float | int]] = {}
    for name in sorted({key for item in step_metrics for key in item.keys()} - {"episode", "step"}):
        records = [(item, float(item[name])) for item in step_metrics if item.get(name) is not None]
        if not records:
            continue
        values = [value for _, value in records]
        max_idx = max(range(len(values)), key=lambda idx: values[idx])
        min_idx = min(range(len(values)), key=lambda idx: values[idx])
        summaries[name] = {
            "final": values[-1],
            "max": values[max_idx],
            "max_step": int(records[max_idx][0]["step"]),
            "min": values[min_idx],
            "min_step": int(records[min_idx][0]["step"]),
            "mean": sum(values) / len(values),
        }
    return summaries


def _latest_video_files(video_folder: Path | None) -> list[str]:
    if video_folder is None or not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _load_policy(checkpoint: Path, device: str, diffusion_policy_root: str | None):
    if diffusion_policy_root:
        root = str(Path(diffusion_policy_root).expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
        _stage("official_dp_root_added", diffusion_policy_root=root)
    from diffusion_policy.workspace.train_diffusion_unet_image_workspace import TrainDiffusionUnetImageWorkspace

    _stage("official_dp_checkpoint_load_start", checkpoint=str(checkpoint))
    workspace = TrainDiffusionUnetImageWorkspace.create_from_checkpoint(str(checkpoint))
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    policy.num_inference_steps = int(args_cli.num_inference_steps)
    policy.to(torch.device(device))
    policy.eval()
    _stage(
        "official_dp_policy_ready",
        workspace=workspace.__class__.__name__,
        policy=policy.__class__.__name__,
        n_obs_steps=int(policy.n_obs_steps),
        num_inference_steps=int(policy.num_inference_steps),
        device=device,
    )
    return workspace, policy


def _predict_action_sequence(policy: Any, history: RgbRobotObsHistory, call_idx: int) -> np.ndarray:
    device = next(policy.parameters()).device
    sample_count = max(1, int(args_cli.num_action_samples))
    samples = []
    with torch.inference_mode():
        for sample_idx in range(sample_count):
            if args_cli.policy_sample_seed is not None:
                seed = int(args_cli.policy_sample_seed) + call_idx * sample_count + sample_idx
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
            result = policy.predict_action(history.as_policy_obs(device))
            samples.append(result["action"])
        action = samples[0] if len(samples) == 1 else torch.stack(samples, dim=0).mean(dim=0)
    return action.detach().cpu().numpy()


def _policy_obs_from_reset(reset_out: Any) -> torch.Tensor:
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    return obs["policy"] if isinstance(obs, dict) else obs


def _policy_obs_from_step(step_out: Any) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, Any]:
    if len(step_out) == 5:
        obs, rewards, terminated, truncated, info = step_out
    else:
        obs, rewards, dones, info = step_out
        terminated = dones
        truncated = torch.zeros_like(dones, dtype=torch.bool)
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    return policy_obs, rewards, terminated, truncated, info


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("yam_pickplace_rgb_dp_eval_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"
    checkpoint = Path(args_cli.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if int(args_cli.num_episodes) < 1:
        raise ValueError("--num_episodes must be positive")

    rng = np.random.default_rng(int(args_cli.seed))
    scene_eye, scene_target, scene_camera_jitter_summary = _jitter_scene_camera(rng)
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    episode_length_summary = _apply_eval_episode_length(env_cfg)
    pose_summary = _apply_yam_default_pose(env_cfg)
    gain_summary = _apply_yam_actuator_gain_scales(env_cfg)
    object_asset_summary = _apply_object_asset_overrides(env_cfg)
    randomization_summary = _apply_scene_randomization(env_cfg, rng)
    _configure_camera(env_cfg, scene_eye, scene_target)

    _stage(
        "start",
        output_dir=str(output_dir),
        metrics_path=str(metrics_path),
        checkpoint=str(checkpoint),
        task=str(args_cli.task),
        seed=int(args_cli.seed),
        num_episodes=int(args_cli.num_episodes),
        num_steps=int(args_cli.num_steps),
        scene_camera={"eye": [float(v) for v in scene_eye], "target": [float(v) for v in scene_target]},
        scene_camera_jitter=scene_camera_jitter_summary,
        image_shape=[int(args_cli.image_height), int(args_cli.image_width), 3],
        episode_length=episode_length_summary,
        robot_default_pose=pose_summary,
        gripper_gain_scales=gain_summary,
        object_asset_overrides=object_asset_summary,
        scene_randomization=randomization_summary,
    )

    workspace, policy = _load_policy(checkpoint, str(args_cli.device), args_cli.diffusion_policy_root)
    if int(policy.n_obs_steps) != 1:
        _stage("warning_policy_n_obs_steps_not_one", n_obs_steps=int(policy.n_obs_steps))

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = gym_env.unwrapped
    _configure_camera(env_cfg, scene_eye, scene_target, task_env)
    appearance_summary = {
        "table_texture": _apply_eval_table_texture(task_env, rng),
        "dome_light_texture": _apply_eval_dome_light_texture(rng),
    }
    _stage("appearance_ready", appearance=appearance_summary)
    wrist_camera, wrist_camera_summary = _make_single_yam_wrist_camera(task_env)
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=min(int(args_cli.video_length), int(args_cli.num_steps) * int(args_cli.num_episodes)),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )

    step_metrics: list[dict[str, float | int | None]] = []
    episode_summaries: list[dict[str, Any]] = []
    action_trace: list[dict[str, Any]] = []
    action_min = np.full(7, np.inf, dtype=np.float64)
    action_max = np.full(7, -np.inf, dtype=np.float64)
    policy_call_idx = 0
    env_closed = False
    debug_obs_paths: list[str] = []
    try:
        for episode in range(int(args_cli.num_episodes)):
            _policy_obs_from_reset(gym_env.reset(seed=int(args_cli.seed) + episode))
            obs = _capture_obs(gym_env, task_env, wrist_camera, scene_eye, scene_target)
            current_obs = obs
            history = RgbRobotObsHistory(
                n_obs_steps=int(policy.n_obs_steps),
                height=int(args_cli.image_height),
                width=int(args_cli.image_width),
                robot_state_dim=24,
            )
            history.reset(obs)
            if int(args_cli.debug_obs_interval) > 0:
                _save_debug_obs_frame(output_dir, current_obs, episode=episode, step=0, action=None, paths=debug_obs_paths)
            action_queue = np.empty((1, 0, 7), dtype=np.float32)
            done_count = 0
            first_done: dict[str, Any] | None = None
            episode_records: list[dict[str, float | int | None]] = []
            chunk_steps_requested = max(1, int(args_cli.action_chunk_steps))
            debug_interval = max(0, int(args_cli.debug_obs_interval))
            for step in range(int(args_cli.num_steps)):
                if not simulation_app.is_running():
                    break
                task_env._compute_intermediate_values()
                pre_step_metrics = _collect_task_metrics(task_env)
                pre_step_object_pos = _tensor_list(task_env.cube_pos[0])
                new_policy_call = False
                if action_queue.shape[1] == 0:
                    action_seq = _predict_action_sequence(policy, history, policy_call_idx)
                    policy_call_idx += 1
                    new_policy_call = True
                    if action_seq.ndim != 3 or action_seq.shape[0] != 1 or action_seq.shape[2] != 7:
                        raise RuntimeError(f"Unexpected RGB action sequence shape {action_seq.shape}")
                    chunk_steps = min(chunk_steps_requested, int(action_seq.shape[1]))
                    action_queue = np.asarray(action_seq[:, :chunk_steps], dtype=np.float32)
                raw_action_np = action_queue[:, 0].copy()
                action_queue = action_queue[:, 1:]
                action_np = raw_action_np.copy()
                clip = float(args_cli.clip_actions)
                if math.isfinite(clip) and clip > 0.0:
                    action_np = np.clip(action_np, -clip, clip)
                if debug_interval > 0 and (step == 0 or (step + 1) % debug_interval == 0):
                    _save_debug_obs_frame(
                        output_dir,
                        current_obs,
                        episode=episode,
                        step=step + 1,
                        action=action_np,
                        paths=debug_obs_paths,
                    )
                action_min = np.minimum(action_min, action_np.min(axis=0))
                action_max = np.maximum(action_max, action_np.max(axis=0))
                action_trace.append(
                    {
                        "episode": int(episode),
                        "step": int(step + 1),
                        "new_policy_call": bool(new_policy_call),
                        "raw_action": raw_action_np.reshape(-1).astype(float).tolist(),
                        "applied_action": action_np.reshape(-1).astype(float).tolist(),
                    }
                )
                actions = torch.as_tensor(action_np, dtype=torch.float32, device=task_env.device)
                _, rewards, terminated, truncated, _ = _policy_obs_from_step(gym_env.step(actions))
                dones = torch.logical_or(terminated, truncated)
                done_now = bool(dones.any())
                if done_now:
                    done_count += int(torch.count_nonzero(dones).detach().cpu())
                    action_queue = np.empty((1, 0, 7), dtype=np.float32)
                    if first_done is None:
                        first_done = {
                            "step": int(step + 1),
                            "terminated": bool(terminated.detach().bool().any().cpu()),
                            "truncated": bool(truncated.detach().bool().any().cpu()),
                            "reward_mean": _mean_float(rewards),
                            "pre_step_metrics": pre_step_metrics,
                            "pre_step_object_pos": pre_step_object_pos,
                        }

                next_obs = _capture_obs(gym_env, task_env, wrist_camera, scene_eye, scene_target)
                if done_now:
                    history.reset(next_obs)
                else:
                    history.push(next_obs)
                current_obs = next_obs
                task_metrics = _collect_task_metrics(task_env)
                record: dict[str, float | int | None] = {
                    "episode": int(episode),
                    "step": int(step + 1),
                    "reward_mean": _mean_float(rewards),
                    "done": float(done_now),
                    "terminated": float(bool(terminated.detach().bool().any().cpu())),
                    "truncated": float(bool(truncated.detach().bool().any().cpu())),
                    **task_metrics,
                }
                step_metrics.append(record)
                episode_records.append(record)
                if args_cli.print_interval > 0 and ((step + 1) % int(args_cli.print_interval) == 0 or step == 0):
                    print(
                        "[YAM_RGB_DP_EVAL] "
                        f"episode={episode} step={step + 1} reward_mean={record['reward_mean']} "
                        f"success={task_metrics.get('in_success_region')} "
                        f"lift={task_metrics.get('cube_lift_height')} "
                        f"xy_error={task_metrics.get('cube_xy_error')} "
                        f"action_min={action_min.tolist()} action_max={action_max.tolist()}",
                        flush=True,
                    )
                if done_now and bool(args_cli.stop_on_done):
                    break
            success_values = [float(item["in_success_region"]) for item in episode_records if item.get("in_success_region") is not None]
            lift_values = [float(item["cube_lift_height"]) for item in episode_records if item.get("cube_lift_height") is not None]
            if first_done is not None:
                done_metrics = first_done.get("pre_step_metrics") or {}
                if done_metrics.get("in_success_region") is not None:
                    success_values.append(float(done_metrics["in_success_region"]))
                if done_metrics.get("cube_lift_height") is not None:
                    lift_values.append(float(done_metrics["cube_lift_height"]))
            episode_summaries.append(
                {
                    "episode": int(episode),
                    "steps_completed": int(len(episode_records)),
                    "done_count": int(done_count),
                    "first_done": first_done,
                    "success": bool(success_values and max(success_values) >= 0.5),
                    "final_success": None if not success_values else float(success_values[-1]),
                    "max_success": None if not success_values else float(max(success_values)),
                    "max_lift_height": None if not lift_values else float(max(lift_values)),
                    "final_object_pos": _tensor_list(task_env.cube_pos[0]) if hasattr(task_env, "cube_pos") else None,
                    "final_goal_pos": _tensor_list(task_env.cube_goal_pos[0]) if hasattr(task_env, "cube_goal_pos") else None,
                    "final_gripper_width": _mean_float(getattr(task_env, "gripper_width", None)),
                }
            )
    finally:
        gym_env.close()
        env_closed = True

    success_flags = [bool(item["success"]) for item in episode_summaries]
    reward_values = [float(item["reward_mean"]) for item in step_metrics if item.get("reward_mean") is not None]
    summary = {
        "task": str(args_cli.task),
        "checkpoint": str(checkpoint),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "obs_schema": {
            "scene_rgb": [3, int(args_cli.image_height), int(args_cli.image_width)],
            "wrist_rgb": [3, int(args_cli.image_height), int(args_cli.image_width)],
            "robot_state": 24,
        },
        "privileged_object_state_in_policy": False,
        "phase_progress_in_policy": False,
        "wrist_camera": wrist_camera_summary,
        "scene_camera": {"eye": [float(v) for v in scene_eye], "target": [float(v) for v in scene_target]},
        "scene_camera_jitter": scene_camera_jitter_summary,
        "object_asset_overrides": object_asset_summary,
        "scene_randomization": randomization_summary,
        "appearance": appearance_summary,
        "episode_length": episode_length_summary,
        "robot_default_pose": pose_summary,
        "gripper_gain_scales": gain_summary,
        "num_episodes_requested": int(args_cli.num_episodes),
        "num_steps_requested": int(args_cli.num_steps),
        "action_chunk_steps": int(args_cli.action_chunk_steps),
        "num_inference_steps": int(args_cli.num_inference_steps),
        "num_action_samples": int(args_cli.num_action_samples),
        "episode_success_rate": sum(success_flags) / len(success_flags) if success_flags else None,
        "episodes_completed": int(len(episode_summaries)),
        "steps_completed": int(len(step_metrics)),
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "action_names": ACTION_NAMES,
        "action_min": action_min.astype(float).tolist(),
        "action_max": action_max.astype(float).tolist(),
        "step_metric_summary": _summarize_step_metrics(step_metrics),
        "episodes": episode_summaries,
        "video_enabled": bool(args_cli.video),
        "video_files": _latest_video_files(video_folder if args_cli.video else None),
        "debug_obs_files": debug_obs_paths,
        "env_closed": env_closed,
        "output_dir": str(output_dir),
        "metrics_path": str(metrics_path),
    }
    metrics_path.write_text(
        json.dumps({"summary": summary, "steps": step_metrics, "action_trace": action_trace}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print("YAM_RGB_DP_POLICY_EVAL_DONE " + json.dumps(summary, sort_keys=True, default=str), flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"YAM_RGB_DP_POLICY_EVAL_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
