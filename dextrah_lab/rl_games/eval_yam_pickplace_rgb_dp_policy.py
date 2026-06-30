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
parser.add_argument("--checkpoint", type=str, default="")
parser.add_argument("--diffusion_policy_root", type=str, default=None)
parser.add_argument("--task", type=str, default="Dextrah-Single-YAM-Single-Object-Policy-Grasp")
parser.add_argument("--control_mode", choices=("policy", "dataset_actions"), default="policy")
parser.add_argument("--dataset_action_pose_gain", type=float, default=1.0)
parser.add_argument("--dataset_action_translation_gain", type=float, default=None)
parser.add_argument("--dataset_action_rotation_gain", type=float, default=None)
parser.add_argument(
    "--exact_policy_shard",
    type=str,
    default="",
    help=(
        "Optional one-trajectory policy shard. Reconstructs its recorded object asset, bin, appearance, camera, "
        "and first robot/object dynamics state before every episode."
    ),
)
parser.add_argument("--exact_render_width", type=int, default=1024)
parser.add_argument("--exact_render_height", type=int, default=1024)
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


def _replay_random_color(rng: np.random.Generator, values: tuple[float, float]) -> tuple[float, float, float]:
    """Match the HSV-biased color sampler used by RGB data collection."""
    lo, hi = _range_pair(values, name="exact_material_value_range")
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
    return tuple(float(np.clip(channel + m, 0.0, 1.0)) for channel in rgb)


def _replay_jitter_color(
    rng: np.random.Generator,
    base: tuple[float, float, float],
    jitter: float,
) -> tuple[float, float, float]:
    return tuple(float(np.clip(channel + rng.uniform(-jitter, jitter), 0.05, 0.95)) for channel in base)


def _resolve_recorded_path(value: str | Path, *, parent: Path) -> Path:
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (parent / path).resolve()


def _policy_shard_array(shard: Path, key: str, *, mmap: bool = False) -> np.ndarray:
    if shard.is_dir():
        return np.load(shard / f"{key}.npy", mmap_mode="r" if mmap else None, allow_pickle=False)
    with np.load(shard, allow_pickle=False) as data:
        return np.asarray(data[key]).copy()


def _stable_scene_asset_record(asset: dict[str, Any]) -> dict[str, Any]:
    uuid = str(asset.get("uuid") or "")
    usd_path = str(asset.get("usd_path") or "")
    primitive_shape = str(asset.get("primitive_shape") or "")
    if not uuid or (not usd_path and not primitive_shape):
        raise ValueError("Exact stable scene target is missing a usable asset record")
    record: dict[str, Any] = {"uuid": uuid, "name": str(asset.get("name") or uuid)}
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


def _source_row(data: np.lib.npyio.NpzFile, key: str, row: int) -> np.ndarray:
    value = np.asarray(data[key])[int(row)]
    if value.ndim >= 2 and value.shape[0] == 1:
        value = value[0]
    elif value.ndim == 1:
        pass
    elif value.ndim >= 1 and value.shape[0] == 1:
        value = value[0]
    return np.asarray(value).copy()


def _load_exact_demo(shard: Path, output_dir: Path) -> dict[str, Any]:
    shard = shard.expanduser().resolve()
    if not shard.exists():
        raise FileNotFoundError(shard)
    if shard.is_dir():
        shard_metadata = json.loads((shard / "metadata.json").read_text(encoding="utf-8"))
    else:
        with np.load(shard, allow_pickle=False) as data:
            shard_metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
    source_dataset = _resolve_recorded_path(str(shard_metadata["source_dataset"]), parent=shard.parent)
    if not source_dataset.is_file():
        raise FileNotFoundError(source_dataset)
    trim = shard_metadata.get("trim") if isinstance(shard_metadata.get("trim"), dict) else {}
    policy_first_rgb_row = int(trim.get("start_row", 0))
    with np.load(source_dataset, allow_pickle=False) as source:
        source_metadata = json.loads(str(np.asarray(source["metadata_json"]).item()))
        rgb_step_idx = np.asarray(source["rgb_step_idx"], dtype=np.int64).reshape(-1)
        step_idx = np.asarray(source["step_idx"], dtype=np.int64).reshape(-1)
        if not 0 <= policy_first_rgb_row < int(rgb_step_idx.shape[0]):
            raise IndexError(f"Exact shard trim row {policy_first_rgb_row} is outside source RGB rows")
        source_step_id = int(rgb_step_idx[policy_first_rgb_row])
        matches = np.flatnonzero(step_idx == source_step_id)
        if matches.size != 1:
            raise ValueError(f"Expected one source state row for step {source_step_id}, got {matches.tolist()}")
        source_state_row = int(matches[0])
        initial_state = {
            "joint_position": _source_row(source, "actual_joint_position", source_state_row).astype(np.float32),
            "joint_velocity": _source_row(source, "actual_joint_velocity", source_state_row).astype(np.float32),
            "target_root_pos": _source_row(source, "target_root_pos", source_state_row).astype(np.float32),
            "target_root_quat": _source_row(source, "target_root_quat", source_state_row).astype(np.float32),
            "target_root_velocity": _source_row(source, "target_root_velocity", source_state_row).astype(np.float32),
        }
    stable_scene_path = _resolve_recorded_path(str(source_metadata["stable_scene_path"]), parent=source_dataset.parent)
    if not stable_scene_path.is_file():
        raise FileNotFoundError(stable_scene_path)
    stable_scene = json.loads(stable_scene_path.read_text(encoding="utf-8"))
    target = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else {}
    target_asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
    asset_record = _stable_scene_asset_record(target_asset)
    target_manifest = output_dir / "exact_target_asset_manifest.json"
    target_manifest.write_text(
        json.dumps({"asset_root": "/", "objects": [asset_record], "source": "exact_policy_shard"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    reference_robot_trajectory = np.asarray(
        _policy_shard_array(shard, "robot_state", mmap=True), dtype=np.float32
    ).copy()
    reference = {
        "scene_rgb": np.asarray(_policy_shard_array(shard, "scene_rgb", mmap=True)[0], dtype=np.uint8).copy(),
        "wrist_rgb": np.asarray(_policy_shard_array(shard, "wrist_rgb", mmap=True)[0], dtype=np.uint8).copy(),
        "robot_state": reference_robot_trajectory[0].copy(),
    }
    actions = np.asarray(_policy_shard_array(shard, "action", mmap=True), dtype=np.float32).copy()
    return {
        "shard": shard,
        "shard_metadata": shard_metadata,
        "source_dataset": source_dataset,
        "source_metadata": source_metadata,
        "stable_scene_path": stable_scene_path,
        "stable_scene": stable_scene,
        "target_manifest": target_manifest,
        "target_uuid": str(asset_record["uuid"]),
        "policy_first_rgb_row": policy_first_rgb_row,
        "source_state_row": source_state_row,
        "source_step_id": source_step_id,
        "initial_state": initial_state,
        "reference": reference,
        "reference_robot_trajectory": reference_robot_trajectory,
        "actions": actions,
    }


def _exact_demo_summary(exact_demo: dict[str, Any] | None) -> dict[str, Any] | None:
    if exact_demo is None:
        return None
    state = exact_demo["initial_state"]
    return {
        "enabled": True,
        "shard": str(exact_demo["shard"]),
        "source_dataset": str(exact_demo["source_dataset"]),
        "stable_scene_path": str(exact_demo["stable_scene_path"]),
        "target_manifest": str(exact_demo["target_manifest"]),
        "target_uuid": str(exact_demo["target_uuid"]),
        "policy_first_rgb_row": int(exact_demo["policy_first_rgb_row"]),
        "source_state_row": int(exact_demo["source_state_row"]),
        "source_step_id": int(exact_demo["source_step_id"]),
        "num_policy_actions": int(exact_demo["actions"].shape[0]),
        "joint_position": np.asarray(state["joint_position"]).astype(float).tolist(),
        "target_root_pos": np.asarray(state["target_root_pos"]).astype(float).tolist(),
        "target_root_quat": np.asarray(state["target_root_quat"]).astype(float).tolist(),
    }


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


def _max_abs_error(actual: Any, expected: Any) -> float:
    lhs = np.asarray(actual, dtype=np.float64)
    rhs = np.asarray(expected, dtype=np.float64)
    if lhs.shape != rhs.shape:
        return float("inf")
    return float(np.max(np.abs(lhs - rhs), initial=0.0))


def _replay_exact_visual_randomization(exact_demo: dict[str, Any]) -> dict[str, Any]:
    metadata = exact_demo["source_metadata"]
    scene = metadata.get("yam_policy_scene_randomization")
    camera = metadata.get("scene_camera")
    if not isinstance(scene, dict) or not isinstance(camera, dict):
        raise ValueError("Exact source metadata lacks scene randomization or camera records")
    materials = scene.get("materials") if isinstance(scene.get("materials"), dict) else {}
    table_texture = scene.get("tabletop_texture") if isinstance(scene.get("tabletop_texture"), dict) else {}
    background = scene.get("background_walls") if isinstance(scene.get("background_walls"), dict) else {}
    lighting = scene.get("lighting") if isinstance(scene.get("lighting"), dict) else {}

    rng = np.random.default_rng(int(metadata["seed"]) + 1009)
    for _ in range(5):
        rng.uniform(0.0, 1.0)
    table_color = _replay_random_color(rng, (0.32, 0.82))
    ground_color = _replay_random_color(rng, (0.32, 0.82))
    bin_floor_color = _replay_random_color(rng, (0.32, 0.82))
    x_wall_color = _replay_random_color(rng, (0.32, 0.82))
    y_wall_color = _replay_random_color(rng, (0.32, 0.82))
    table_material_roughness = float(rng.uniform(0.45, 0.92))
    surround_color = _replay_jitter_color(rng, table_color, 0.08)
    texture_patch_count = int(rng.integers(0, 1))
    if texture_patch_count != 0:
        raise RuntimeError("The exact-data replay expected zero procedural texture patches")
    background_color = _replay_random_color(rng, (0.32, 0.82))
    surround_roughness = float(rng.uniform(0.52, 0.95))
    table_texture_roughness = float(rng.uniform(0.60, 0.96))
    sampled_table_texture = _sample_texture_path(
        rng,
        str(table_texture.get("table_texture_dir") or ""),
        exts=SURFACE_TEXTURE_EXTS,
        include_tokens=("albedo", "diffuse", "diff", "basecolor", "color"),
        exclude_tokens=("normal", "orm", "rough", "metal", "height"),
    )
    table_texture_tiling = float(rng.uniform(1.4, 3.8))
    background_roughness = float(rng.uniform(0.58, 0.95))
    sampled_background_texture = _sample_texture_path(
        rng,
        str(background.get("background_texture_dir") or ""),
        exts=SURFACE_TEXTURE_EXTS,
        exclude_tokens=("normal", "orm", "rough", "metal", "height"),
    )
    background_texture_tiling = float(rng.uniform(1.0, 2.2))
    sampled_dome_texture = _sample_texture_path(
        rng,
        str(lighting.get("dome_light_texture_dir") or background.get("background_texture_dir") or ""),
        exts=DOME_TEXTURE_EXTS,
    )
    bin_visual_roughness = float(rng.uniform(0.45, 0.92))
    dome_light_intensity = float(rng.uniform(450.0, 1600.0))
    key_light_intensity = float(rng.uniform(250.0, 1400.0))
    key_light_rotation_deg = tuple(float(v) for v in rng.uniform((35.0, -8.0, -75.0), (72.0, 8.0, 35.0)))

    eye_jitter = tuple(float(v) for v in camera.get("eye_jitter", (0.018, 0.018, 0.018)))
    target_jitter = tuple(float(v) for v in camera.get("target_jitter", (0.012, 0.012, 0.012)))
    shared_y_radius = min(abs(eye_jitter[1]), abs(target_jitter[1]))
    shared_y_jitter = float(rng.uniform(-shared_y_radius, shared_y_radius))
    scene_eye = (
        DEFAULT_SCENE_CAMERA_EYE[0] + float(rng.uniform(-abs(eye_jitter[0]), abs(eye_jitter[0]))),
        DEFAULT_SCENE_CAMERA_EYE[1] + shared_y_jitter,
        DEFAULT_SCENE_CAMERA_EYE[2] + float(rng.uniform(-abs(eye_jitter[2]), abs(eye_jitter[2]))),
    )
    scene_target = (
        DEFAULT_SCENE_CAMERA_TARGET[0] + float(rng.uniform(-abs(target_jitter[0]), abs(target_jitter[0]))),
        DEFAULT_SCENE_CAMERA_TARGET[1] + shared_y_jitter,
        DEFAULT_SCENE_CAMERA_TARGET[2] + float(rng.uniform(-abs(target_jitter[2]), abs(target_jitter[2]))),
    )

    numeric_errors = {
        "table_color": _max_abs_error(table_color, materials.get("table_color")),
        "ground_color": _max_abs_error(ground_color, materials.get("ground_color")),
        "goal_bin_floor_color": _max_abs_error(bin_floor_color, materials.get("goal_bin_floor_color")),
        "goal_bin_x_wall_color": _max_abs_error(x_wall_color, materials.get("goal_bin_x_wall_color")),
        "goal_bin_y_wall_color": _max_abs_error(y_wall_color, materials.get("goal_bin_y_wall_color")),
        "tabletop_surround_color": _max_abs_error(surround_color, materials.get("tabletop_surround_color")),
        "table_texture_tiling": _max_abs_error(table_texture_tiling, table_texture.get("table_texture_tiling")),
        "background_texture_tiling": _max_abs_error(
            background_texture_tiling, background.get("background_texture_tiling")
        ),
        "dome_light_intensity": _max_abs_error(dome_light_intensity, lighting.get("dome_light_intensity")),
        "key_light_intensity": _max_abs_error(key_light_intensity, lighting.get("key_light_intensity")),
        "key_light_rotation_deg": _max_abs_error(key_light_rotation_deg, lighting.get("key_light_rotation_deg")),
        "scene_eye": _max_abs_error(scene_eye, camera.get("eye")),
        "scene_target": _max_abs_error(scene_target, camera.get("target")),
        "shared_y_jitter": _max_abs_error(shared_y_jitter, camera.get("shared_y_jitter")),
    }
    max_numeric_error = max(numeric_errors.values(), default=float("inf"))
    paths = {
        "table_texture": {
            "sampled": sampled_table_texture,
            "recorded": str(table_texture.get("table_texture_path") or ""),
        },
        "background_texture": {
            "sampled": sampled_background_texture,
            "recorded": str(background.get("background_texture_path") or ""),
        },
        "dome_texture": {
            "sampled": sampled_dome_texture,
            "recorded": str(lighting.get("dome_light_texture_path") or ""),
        },
    }
    paths_match = all(
        (not record["recorded"] and not record["sampled"])
        or Path(record["recorded"]).resolve() == Path(record["sampled"]).resolve()
        for record in paths.values()
    )
    if not math.isfinite(max_numeric_error) or max_numeric_error > 1.0e-6:
        raise RuntimeError(
            "Could not deterministically replay exact-demo visual RNG; "
            f"max recorded numeric error={max_numeric_error} errors={numeric_errors}"
        )
    return {
        "rng_seed": int(metadata["seed"]) + 1009,
        "max_recorded_numeric_error": max_numeric_error,
        "numeric_errors": numeric_errors,
        "sampled_paths_match_recorded": bool(paths_match),
        "paths": paths,
        "table_material_roughness": table_material_roughness,
        "tabletop_surround_roughness": surround_roughness,
        "table_texture_roughness": table_texture_roughness,
        "background_roughness": background_roughness,
        "bin_visual_roughness": bin_visual_roughness,
        "scene_eye": scene_eye,
        "scene_target": scene_target,
        "shared_y_jitter": shared_y_jitter,
        "background_color": background_color,
    }


def _apply_exact_demo_env_cfg(env_cfg: Any, exact_demo: dict[str, Any]) -> dict[str, Any]:
    metadata = exact_demo["source_metadata"]
    scene = metadata["yam_policy_scene_randomization"]
    materials = scene["materials"]
    surround = scene["tabletop_surround"]
    table_texture = scene["tabletop_texture"]
    background = scene["background_walls"]
    lighting = scene["lighting"]
    stable_scene = exact_demo["stable_scene"]
    bins = stable_scene.get("bins") if isinstance(stable_scene.get("bins"), dict) else {}
    goal = bins.get("goal") if isinstance(bins.get("goal"), dict) else None
    if goal is None:
        raise ValueError("Exact stable scene does not contain a goal bin")
    visual_replay = _replay_exact_visual_randomization(exact_demo)
    exact_demo["visual_replay"] = visual_replay

    env_cfg.object_asset_manifest_path = str(exact_demo["target_manifest"])
    env_cfg.max_objects = 1
    env_cfg.object_asset_assignment = "round_robin"
    env_cfg.object_validate_usd_bounds = False
    env_cfg.object_reset_settle_steps = 0
    env_cfg.arm_joint_reset_noise = 0.0
    initial_state = exact_demo["initial_state"]
    env_cfg.object_fixed_root_position = tuple(float(v) for v in initial_state["target_root_pos"])
    env_cfg.object_fixed_root_quat_wxyz = tuple(float(v) for v in initial_state["target_root_quat"])

    env_cfg.tabletop_goal_bin_enabled = True
    env_cfg.tabletop_source_bin_enabled = False
    env_cfg.tabletop_goal_bin_center_offset_x = float(goal["center_x"]) - float(env_cfg.table_center_x)
    env_cfg.tabletop_goal_bin_center_offset_y = float(goal["center_y"]) - float(env_cfg.table_center_y)
    for key in ("inner_size_x", "inner_size_y", "wall_thickness", "bottom_thickness", "wall_height"):
        if key in goal:
            setattr(env_cfg, f"tabletop_goal_bin_{key}", float(goal[key]))
    env_cfg.tabletop_goal_bin_clearance = float(goal.get("clearance", 0.08))
    env_cfg.tabletop_goal_bin_placement_clearance = float(goal.get("placement_clearance", 0.08))
    env_cfg.tabletop_goal_bin_success_xy_tol = min(
        0.12, 0.35 * min(float(goal["inner_size_x"]), float(goal["inner_size_y"]))
    )
    env_cfg.cube_success_xy_tol = env_cfg.tabletop_goal_bin_success_xy_tol
    if "goal_z" in goal:
        env_cfg.tabletop_goal_bin_goal_height = max(
            float(goal["goal_z"])
            - float(goal.get("table_surface_z", env_cfg.table_surface_z))
            - float(goal.get("bottom_thickness", env_cfg.tabletop_goal_bin_bottom_thickness)),
            0.0,
        )

    env_cfg.ground_plane_color = tuple(float(v) for v in materials["ground_color"])
    table_material = getattr(getattr(getattr(env_cfg, "table", None), "spawn", None), "visual_material", None)
    if table_material is not None:
        if hasattr(table_material, "diffuse_color"):
            table_material.diffuse_color = tuple(float(v) for v in materials["table_color"])
        if hasattr(table_material, "roughness"):
            table_material.roughness = float(visual_replay["table_material_roughness"])
    env_cfg.tabletop_goal_bin_floor_color = tuple(float(v) for v in materials["goal_bin_floor_color"])
    env_cfg.tabletop_goal_bin_x_wall_color = tuple(float(v) for v in materials["goal_bin_x_wall_color"])
    env_cfg.tabletop_goal_bin_y_wall_color = tuple(float(v) for v in materials["goal_bin_y_wall_color"])
    env_cfg.tabletop_goal_bin_visual_roughness = float(visual_replay["bin_visual_roughness"])
    env_cfg.dome_light_intensity = float(lighting["dome_light_intensity"])
    env_cfg.key_light_enabled = True
    env_cfg.key_light_intensity = float(lighting["key_light_intensity"])
    env_cfg.key_light_rotation_deg = tuple(float(v) for v in lighting["key_light_rotation_deg"])

    env_cfg.exact_tabletop_surround_enabled = bool(surround.get("enabled", False))
    env_cfg.exact_tabletop_surround_size = tuple(float(v) for v in surround.get("size", (1.04, 1.20)))
    env_cfg.exact_tabletop_surround_top_z_offset = float(surround.get("top_z_offset", -0.004))
    env_cfg.exact_tabletop_surround_thickness = float(surround.get("thickness", 0.006))
    env_cfg.exact_tabletop_surround_color = tuple(float(v) for v in materials["tabletop_surround_color"])
    env_cfg.exact_tabletop_surround_roughness = float(visual_replay["tabletop_surround_roughness"])
    env_cfg.exact_table_texture_enabled = bool(table_texture.get("enabled", False))
    env_cfg.exact_table_texture_path = str(table_texture.get("table_texture_path") or "")
    env_cfg.exact_table_texture_tiling = float(table_texture.get("table_texture_tiling", 2.4))
    env_cfg.exact_table_texture_roughness = float(visual_replay["table_texture_roughness"])
    env_cfg.exact_dome_texture_path = str(lighting.get("dome_light_texture_path") or "")
    env_cfg.exact_background_enabled = bool(background.get("enabled", False))
    if env_cfg.exact_background_enabled:
        raise ValueError("Exact-demo evaluator currently requires collection scenes without background walls")

    joint_names = [f"joint{i}" for i in range(1, 7)] + ["left_finger", "right_finger"]
    joint_position = np.asarray(initial_state["joint_position"], dtype=np.float32).reshape(-1)
    if joint_position.shape != (8,):
        raise ValueError(f"Expected exact YAM joint state with 8 values, got {joint_position.shape}")
    env_cfg.robot.init_state.joint_pos = {
        name: float(value) for name, value in zip(joint_names, joint_position, strict=True)
    }
    if hasattr(env_cfg, "viewer") and hasattr(env_cfg.viewer, "resolution"):
        env_cfg.viewer.resolution = (int(args_cli.exact_render_width), int(args_cli.exact_render_height))
    return {
        "enabled": True,
        "target_uuid": str(exact_demo["target_uuid"]),
        "goal_bin": {str(key): value for key, value in goal.items()},
        "visual_replay": visual_replay,
        "render_resolution": [int(args_cli.exact_render_width), int(args_cli.exact_render_height)],
    }


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


def _usd_solid_material(
    stage: Any,
    path: str,
    color: tuple[float, float, float],
    *,
    roughness: float,
) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _usd_add_box(
    stage: Any,
    path: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: UsdShade.Material,
) -> None:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*center))
    xformable.AddScaleOp().Set(Gf.Vec3f(*size))
    _usd_bind(prim, mat)


def _apply_exact_demo_appearance(task_env: Any, exact_demo: dict[str, Any]) -> dict[str, Any]:
    cfg = task_env.cfg
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("Missing USD stage while creating exact-demo appearance")
    env_origins = task_env.scene.env_origins.detach().float().cpu().numpy()
    size_xy = tuple(float(v) for v in cfg.exact_tabletop_surround_size)
    thickness = float(cfg.exact_tabletop_surround_thickness)
    top_z = float(cfg.table_surface_z) + float(cfg.exact_tabletop_surround_top_z_offset)
    center_z = top_z - 0.5 * thickness
    looks_root = "/World/Looks/YAMPolicyTabletopSurround"
    UsdGeom.Xform.Define(stage, looks_root)
    surround_mat = _usd_solid_material(
        stage,
        f"{looks_root}/surface",
        tuple(float(v) for v in cfg.exact_tabletop_surround_color),
        roughness=float(cfg.exact_tabletop_surround_roughness),
    )
    texture_path = str(cfg.exact_table_texture_path or "")
    texture_mat = None
    if texture_path:
        if not Path(texture_path).is_file():
            raise FileNotFoundError(texture_path)
        texture_mat = _usd_texture_material(
            stage,
            f"{looks_root}/table_texture",
            texture_path,
            roughness=float(cfg.exact_table_texture_roughness),
        )
    spawned: list[dict[str, Any]] = []
    texture_quads: list[dict[str, Any]] = []
    for env_id, origin in enumerate(env_origins):
        center = (
            float(origin[0]) + float(cfg.table_center_x),
            float(origin[1]) + float(cfg.table_center_y),
            float(origin[2]) + center_z,
        )
        if bool(cfg.exact_tabletop_surround_enabled):
            surround_path = f"/World/envs/env_{env_id}/YAMPolicyTabletopSurround"
            _usd_add_box(stage, surround_path, center, (size_xy[0], size_xy[1], thickness), surround_mat)
            spawned.append({"env_id": int(env_id), "path": surround_path, "center": [float(v) for v in center]})
        if bool(cfg.exact_table_texture_enabled) and texture_mat is not None:
            quad_center = (
                center[0],
                center[1],
                float(origin[2]) + float(cfg.table_surface_z) + 0.0008,
            )
            quad_path = f"/World/envs/env_{env_id}/YAMPolicyTabletopTexture/full_surface"
            tiling = float(cfg.exact_table_texture_tiling)
            uv_scale = (tiling, tiling * max(0.1, size_xy[1] / max(size_xy[0], 1.0e-6)))
            _usd_add_xy_quad(stage, quad_path, quad_center, size_xy, texture_mat, uv_scale=uv_scale)
            texture_quads.append(
                {
                    "env_id": int(env_id),
                    "path": quad_path,
                    "center": [float(v) for v in quad_center],
                    "size": [float(v) for v in size_xy],
                    "texture_path": texture_path,
                    "uv_scale": [float(v) for v in uv_scale],
                }
            )
    dome_texture_path = str(cfg.exact_dome_texture_path or "")
    dome_summary: dict[str, Any] = {"enabled": False}
    if dome_texture_path:
        if not Path(dome_texture_path).is_file():
            raise FileNotFoundError(dome_texture_path)
        light_prim = stage.GetPrimAtPath("/World/Light")
        if not light_prim.IsValid():
            raise RuntimeError("Exact-demo dome texture requested but /World/Light is missing")
        attr = light_prim.GetAttribute("inputs:texture:file")
        if not attr:
            attr = light_prim.CreateAttribute("inputs:texture:file", Sdf.ValueTypeNames.Asset)
        attr.Set(Sdf.AssetPath(dome_texture_path))
        dome_summary = {"enabled": True, "texture_path": dome_texture_path}
    task_env.sim.forward()
    return {
        "enabled": True,
        "size": [float(v) for v in size_xy],
        "top_z": float(top_z),
        "thickness": float(thickness),
        "spawned": spawned,
        "table_texture_quads": texture_quads,
        "dome_light_texture": dome_summary,
        "rng_replay": exact_demo["visual_replay"],
    }


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


def _validate_exact_target_asset(task_env: Any, exact_demo: dict[str, Any]) -> dict[str, Any]:
    active_assets = list(getattr(task_env, "_object_assets", []))
    active_indices = getattr(task_env, "object_asset_index", None)
    active_uuid = ""
    active_index = None
    if active_assets and active_indices is not None:
        active_index = int(active_indices[0].detach().cpu().item())
        active_uuid = str(active_assets[active_index].get("uuid") or "")
    expected_uuid = str(exact_demo["target_uuid"])
    if active_uuid != expected_uuid:
        raise RuntimeError(f"Exact target UUID mismatch: expected {expected_uuid}, active {active_uuid}")
    return {"expected_uuid": expected_uuid, "active_uuid": active_uuid, "active_index": active_index}


def _restore_exact_demo_state(task_env: Any, exact_demo: dict[str, Any]) -> dict[str, Any]:
    state = exact_demo["initial_state"]
    env_ids = torch.tensor([0], dtype=torch.long, device=task_env.device)
    joint_pos = torch.as_tensor(state["joint_position"], dtype=torch.float32, device=task_env.device).reshape(1, -1)
    joint_vel = torch.as_tensor(state["joint_velocity"], dtype=torch.float32, device=task_env.device).reshape(1, -1)
    if joint_pos.shape != (1, 8) or joint_vel.shape != (1, 8):
        raise ValueError(f"Expected exact joint state (1,8), got {joint_pos.shape}/{joint_vel.shape}")
    task_env._sync_reset_joint_state(env_ids, joint_pos, joint_vel, update_buffers=True)

    root_pos = torch.as_tensor(state["target_root_pos"], dtype=torch.float32, device=task_env.device).reshape(1, 3)
    root_quat = torch.as_tensor(state["target_root_quat"], dtype=torch.float32, device=task_env.device).reshape(1, 4)
    root_vel = torch.as_tensor(state["target_root_velocity"], dtype=torch.float32, device=task_env.device).reshape(1, 6)
    root_state = torch.zeros((1, 13), dtype=torch.float32, device=task_env.device)
    root_state[:, :3] = root_pos + task_env.scene.env_origins[env_ids]
    root_state[:, 3:7] = root_quat
    root_state[:, 7:13] = root_vel
    task_env._cube.write_root_state_to_sim(root_state, env_ids=env_ids)
    task_env._set_object_asset_root_pose(env_ids, root_pos, root_quat)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)

    object_center = task_env._object_center_pos_from_root(env_ids, root_pos, root_quat)
    task_env.cube_initial_pos[env_ids] = object_center
    task_env.cube_goal_pos[env_ids] = task_env._tabletop_goal_pos(env_ids, object_center)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env.cube_speed_done[env_ids] = False
    task_env.actions[env_ids] = 0.0
    task_env.ik_controller.reset(env_ids)
    if hasattr(task_env, "episode_length_buf"):
        task_env.episode_length_buf[env_ids] = 0
    task_env._compute_intermediate_values(env_ids)
    restored_robot = _robot_state(task_env)
    return {
        "source_state_row": int(exact_demo["source_state_row"]),
        "source_step_id": int(exact_demo["source_step_id"]),
        "joint_position_max_abs_error": _max_abs_error(restored_robot[:8], state["joint_position"]),
        "joint_velocity_max_abs_error": _max_abs_error(restored_robot[8:16], state["joint_velocity"]),
        "target_root_pos_max_abs_error": _max_abs_error(
            _tensor_numpy(task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids])[0],
            state["target_root_pos"],
        ),
        "target_root_quat_max_abs_error": _max_abs_error(
            _tensor_numpy(task_env._cube.data.root_quat_w[env_ids])[0], state["target_root_quat"]
        ),
        "restored_robot_state": restored_robot.astype(float).tolist(),
        "target_center_pos": _tensor_list(object_center[0]),
        "goal_pos": _tensor_list(task_env.cube_goal_pos[0]),
    }


def _array_error_metrics(actual: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    actual_f = np.asarray(actual, dtype=np.float32)
    expected_f = np.asarray(expected, dtype=np.float32)
    if actual_f.shape != expected_f.shape:
        return {"shape_match": False, "actual_shape": list(actual_f.shape), "expected_shape": list(expected_f.shape)}
    delta = actual_f - expected_f
    mse = float(np.mean(np.square(delta)))
    return {
        "shape_match": True,
        "shape": list(actual_f.shape),
        "mae": float(np.mean(np.abs(delta))),
        "rmse": float(math.sqrt(mse)),
        "max_abs": float(np.max(np.abs(delta), initial=0.0)),
        "psnr_db": None if mse <= 0.0 else float(20.0 * math.log10(255.0 / math.sqrt(mse))),
    }


def _save_exact_observation_comparison(
    output_dir: Path,
    live_obs: dict[str, np.ndarray],
    reference: dict[str, np.ndarray],
) -> str:
    from PIL import Image, ImageDraw, ImageFont

    scene_ref = np.asarray(reference["scene_rgb"], dtype=np.uint8)
    scene_live = np.asarray(live_obs["scene_rgb"], dtype=np.uint8)
    wrist_ref = np.asarray(reference["wrist_rgb"], dtype=np.uint8)
    wrist_live = np.asarray(live_obs["wrist_rgb"], dtype=np.uint8)
    arrays = (scene_ref, scene_live, wrist_ref, wrist_live)
    if len({array.shape for array in arrays}) != 1:
        raise ValueError(f"Cannot compare exact observation shapes: {[array.shape for array in arrays]}")
    height, width = scene_ref.shape[:2]
    header = 24
    canvas = Image.new("RGB", (3 * width, 2 * (height + header)), (16, 16, 16))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    rows = ((scene_ref, scene_live, "scene"), (wrist_ref, wrist_live, "wrist"))
    for row_idx, (ref, live, label) in enumerate(rows):
        y = row_idx * (height + header)
        diff = np.clip(np.abs(live.astype(np.int16) - ref.astype(np.int16)) * 4, 0, 255).astype(np.uint8)
        canvas.paste(Image.fromarray(ref, mode="RGB"), (0, y + header))
        canvas.paste(Image.fromarray(live, mode="RGB"), (width, y + header))
        canvas.paste(Image.fromarray(diff, mode="RGB"), (2 * width, y + header))
        draw.text((5, y + 6), f"{label} reference", fill=(240, 240, 235), font=font)
        draw.text((width + 5, y + 6), f"{label} exact-reset live", fill=(240, 240, 235), font=font)
        draw.text((2 * width + 5, y + 6), f"{label} |difference| x4", fill=(240, 240, 235), font=font)
    path = output_dir / "exact_observation_parity.png"
    canvas.save(path)
    return str(path)


def _audit_exact_observation(
    output_dir: Path,
    live_obs: dict[str, np.ndarray],
    exact_demo: dict[str, Any],
) -> dict[str, Any]:
    reference = exact_demo["reference"]
    return {
        "scene_rgb": _array_error_metrics(live_obs["scene_rgb"], reference["scene_rgb"]),
        "wrist_rgb": _array_error_metrics(live_obs["wrist_rgb"], reference["wrist_rgb"]),
        "robot_state": _array_error_metrics(live_obs["robot_state"], reference["robot_state"]),
        "comparison_image": _save_exact_observation_comparison(output_dir, live_obs, reference),
    }


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
    control_mode = str(args_cli.control_mode)
    checkpoint = Path(args_cli.checkpoint).expanduser().resolve() if str(args_cli.checkpoint).strip() else None
    if control_mode == "policy" and (checkpoint is None or not checkpoint.is_file()):
        raise FileNotFoundError(checkpoint or "--checkpoint is required for --control_mode=policy")
    exact_shard = Path(args_cli.exact_policy_shard) if str(args_cli.exact_policy_shard).strip() else None
    exact_demo = _load_exact_demo(exact_shard, output_dir) if exact_shard is not None else None
    if control_mode == "dataset_actions" and exact_demo is None:
        raise ValueError("--control_mode=dataset_actions requires --exact_policy_shard")
    if int(args_cli.num_episodes) < 1:
        raise ValueError("--num_episodes must be positive")

    rng = np.random.default_rng(int(args_cli.seed))
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
    if exact_demo is None:
        scene_eye, scene_target, scene_camera_jitter_summary = _jitter_scene_camera(rng)
        object_asset_summary = _apply_object_asset_overrides(env_cfg)
        randomization_summary = _apply_scene_randomization(env_cfg, rng)
        exact_config_summary = None
    else:
        exact_config_summary = _apply_exact_demo_env_cfg(env_cfg, exact_demo)
        scene_camera_record = exact_demo["source_metadata"]["scene_camera"]
        scene_eye = tuple(float(v) for v in scene_camera_record["eye"])
        scene_target = tuple(float(v) for v in scene_camera_record["target"])
        scene_camera_jitter_summary = {
            key: value for key, value in scene_camera_record.items() if key not in {"eye", "target"}
        }
        object_asset_summary = {
            "enabled": True,
            "exact_demo": True,
            "object_asset_manifest_path": str(exact_demo["target_manifest"]),
            "target_uuid": str(exact_demo["target_uuid"]),
        }
        randomization_summary = exact_demo["source_metadata"]["yam_policy_scene_randomization"]
        pose_summary = {
            "joint_pos": {
                name: float(value)
                for name, value in zip(
                    [f"joint{i}" for i in range(1, 7)] + ["left_finger", "right_finger"],
                    exact_demo["initial_state"]["joint_position"],
                    strict=True,
                )
            },
            "source": "exact_policy_shard",
        }
    _configure_camera(env_cfg, scene_eye, scene_target)

    _stage(
        "start",
        output_dir=str(output_dir),
        metrics_path=str(metrics_path),
        checkpoint=None if checkpoint is None else str(checkpoint),
        control_mode=control_mode,
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
        exact_demo=_exact_demo_summary(exact_demo),
        exact_config=exact_config_summary,
    )

    workspace = None
    policy = None
    if control_mode == "policy":
        assert checkpoint is not None
        workspace, policy = _load_policy(checkpoint, str(args_cli.device), args_cli.diffusion_policy_root)
        if int(policy.n_obs_steps) != 1:
            _stage("warning_policy_n_obs_steps_not_one", n_obs_steps=int(policy.n_obs_steps))

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = gym_env.unwrapped
    _configure_camera(env_cfg, scene_eye, scene_target, task_env)
    if exact_demo is None:
        appearance_summary = {
            "table_texture": _apply_eval_table_texture(task_env, rng),
            "dome_light_texture": _apply_eval_dome_light_texture(rng),
        }
        exact_asset_summary = None
    else:
        appearance_summary = _apply_exact_demo_appearance(task_env, exact_demo)
        exact_asset_summary = _validate_exact_target_asset(task_env, exact_demo)
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
    exact_reset_summaries: list[dict[str, Any]] = []
    exact_observation_parity: dict[str, Any] | None = None
    try:
        for episode in range(int(args_cli.num_episodes)):
            _policy_obs_from_reset(gym_env.reset(seed=int(args_cli.seed) + episode))
            exact_reset_summary = None
            if exact_demo is not None:
                exact_reset_summary = _restore_exact_demo_state(task_env, exact_demo)
                exact_reset_summaries.append(exact_reset_summary)
            obs = _capture_obs(gym_env, task_env, wrist_camera, scene_eye, scene_target)
            if exact_demo is not None and exact_observation_parity is None:
                exact_observation_parity = _audit_exact_observation(output_dir, obs, exact_demo)
                _stage("exact_observation_parity", **exact_observation_parity)
            current_obs = obs
            history = RgbRobotObsHistory(
                n_obs_steps=int(policy.n_obs_steps) if policy is not None else 1,
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
                if control_mode == "dataset_actions" and step >= int(exact_demo["actions"].shape[0]):
                    break
                task_env._compute_intermediate_values()
                pre_step_metrics = _collect_task_metrics(task_env)
                pre_step_object_pos = _tensor_list(task_env.cube_pos[0])
                new_policy_call = False
                if control_mode == "dataset_actions":
                    raw_action_np = np.asarray(exact_demo["actions"][step : step + 1], dtype=np.float32)
                    translation_gain = (
                        float(args_cli.dataset_action_pose_gain)
                        if args_cli.dataset_action_translation_gain is None
                        else float(args_cli.dataset_action_translation_gain)
                    )
                    rotation_gain = (
                        float(args_cli.dataset_action_pose_gain)
                        if args_cli.dataset_action_rotation_gain is None
                        else float(args_cli.dataset_action_rotation_gain)
                    )
                    raw_action_np[:, :3] *= translation_gain
                    raw_action_np[:, 3:6] *= rotation_gain
                elif action_queue.shape[1] == 0:
                    assert policy is not None
                    action_seq = _predict_action_sequence(policy, history, policy_call_idx)
                    policy_call_idx += 1
                    new_policy_call = True
                    if action_seq.ndim != 3 or action_seq.shape[0] != 1 or action_seq.shape[2] != 7:
                        raise RuntimeError(f"Unexpected RGB action sequence shape {action_seq.shape}")
                    chunk_steps = min(chunk_steps_requested, int(action_seq.shape[1]))
                    action_queue = np.asarray(action_seq[:, :chunk_steps], dtype=np.float32)
                    raw_action_np = action_queue[:, 0].copy()
                    action_queue = action_queue[:, 1:]
                else:
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

                if control_mode == "dataset_actions" and debug_interval <= 0:
                    next_obs = current_obs
                else:
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
                if control_mode == "dataset_actions":
                    live_robot_state = _robot_state(task_env)
                    reference_row = exact_demo["reference_robot_trajectory"][
                        min(step + 1, int(exact_demo["reference_robot_trajectory"].shape[0]) - 1)
                    ]
                    record["dataset_joint_position_l2_error"] = float(
                        np.linalg.norm(live_robot_state[:8] - reference_row[:8])
                    )
                    record["dataset_tcp_position_l2_error"] = float(
                        np.linalg.norm(live_robot_state[16:19] - reference_row[16:19])
                    )
                    for axis, live_value, reference_value in zip(
                        ("x", "y", "z"), live_robot_state[16:19], reference_row[16:19], strict=True
                    ):
                        record[f"dataset_live_tcp_{axis}"] = float(live_value)
                        record[f"dataset_reference_tcp_{axis}"] = float(reference_value)
                        record[f"dataset_tcp_{axis}_error"] = float(live_value - reference_value)
                    quat_dot = float(abs(np.dot(live_robot_state[19:23], reference_row[19:23])))
                    record["dataset_tcp_quat_angle_error"] = float(
                        2.0 * math.acos(float(np.clip(quat_dot, 0.0, 1.0)))
                    )
                    record["dataset_gripper_width_abs_error"] = float(
                        abs(float(live_robot_state[23]) - float(reference_row[23]))
                    )
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
                    "final_robot_state": _robot_state(task_env).astype(float).tolist(),
                    "exact_reset": exact_reset_summary,
                }
            )
    finally:
        gym_env.close()
        env_closed = True

    success_flags = [bool(item["success"]) for item in episode_summaries]
    reward_values = [float(item["reward_mean"]) for item in step_metrics if item.get("reward_mean") is not None]
    summary = {
        "task": str(args_cli.task),
        "control_mode": control_mode,
        "dataset_action_pose_gain": float(args_cli.dataset_action_pose_gain),
        "dataset_action_translation_gain": (
            float(args_cli.dataset_action_pose_gain)
            if args_cli.dataset_action_translation_gain is None
            else float(args_cli.dataset_action_translation_gain)
        ),
        "dataset_action_rotation_gain": (
            float(args_cli.dataset_action_pose_gain)
            if args_cli.dataset_action_rotation_gain is None
            else float(args_cli.dataset_action_rotation_gain)
        ),
        "checkpoint": None if checkpoint is None else str(checkpoint),
        "official_workspace": None if workspace is None else workspace.__class__.__name__,
        "policy_class": None if policy is None else policy.__class__.__name__,
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
        "exact_demo": _exact_demo_summary(exact_demo),
        "exact_config": exact_config_summary,
        "exact_asset": exact_asset_summary,
        "exact_resets": exact_reset_summaries,
        "exact_observation_parity": exact_observation_parity,
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
