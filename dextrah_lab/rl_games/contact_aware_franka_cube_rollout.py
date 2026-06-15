"""Bounded contact-aware Franka cube controller rollout smoke.

This script does not train. It probes whether a live Isaac controller rollout
can generate a physically plausible close/lift demonstration after raw
GraspGenX/cuRobo labels were shown to target an EE/TCP point that is not the
cube contact point. The controller targets measured finger-center geometry
instead of raw source EE waypoints and writes inspectable metrics/videos.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", required=True, type=str, help="Converted lowdim NPZ used for cube/source reset.")
parser.add_argument("--trajectory_json", required=True, type=str, help="Raw source trajectory JSON for joint reset.")
parser.add_argument("--output_dir", default=None, type=str)
parser.add_argument("--task", default="Dextrah-Franka-Cube-Grasp", type=str)
parser.add_argument("--episode", default=24, type=int)
parser.add_argument("--episode_step", default=260, type=int)
parser.add_argument("--seed", default=42, type=int)
parser.add_argument("--variant", action="append", default=[], help="Variant name or name:x,y,z offset in meters.")
parser.add_argument("--align_steps", default=80, type=int)
parser.add_argument("--contact_align_steps", default=0, type=int)
parser.add_argument(
    "--contact_align_reference",
    choices=("initial_cube", "live_cube"),
    default="initial_cube",
    help=(
        "Target anchor during the optional open-gripper contact-alignment phase. "
        "'initial_cube' preserves the original source/reset cube anchor; 'live_cube' "
        "tracks the measured cube pose before close/lift."
    ),
)
parser.add_argument(
    "--close_hold_reference",
    choices=("contact_anchor", "live_cube"),
    default="contact_anchor",
    help=(
        "Target anchor during gripper close/hold. 'contact_anchor' preserves the "
        "cube pose captured when the close gate fires. 'live_cube' tracks the "
        "measured cube pose while closing, then the last close pose is frozen "
        "for lift."
    ),
)
parser.add_argument(
    "--contact_align_threshold",
    default=0.06,
    type=float,
    help="Finger-center-to-cube threshold used for contact-alignment audit only.",
)
parser.add_argument(
    "--contact_gate_mode",
    choices=("center", "left_right"),
    default="center",
    help=(
        "Pre-close gate. 'center' preserves the previous finger-center distance gate. "
        "'left_right' additionally requires both finger distances and left/right balance."
    ),
)
parser.add_argument(
    "--finger_gate_max_distance",
    default=0.08,
    type=float,
    help="Maximum left/right finger-to-cube distance for --contact_gate_mode left_right.",
)
parser.add_argument(
    "--finger_gate_balance_threshold",
    default=0.02,
    type=float,
    help="Maximum absolute left-minus-right finger distance for --contact_gate_mode left_right.",
)
parser.add_argument(
    "--require_contact_gate",
    action="store_true",
    default=False,
    help="If set, do not fall back to close/hold when the contact-align step budget expires.",
)
parser.add_argument(
    "--lateral_centering_gain",
    default=0.0,
    type=float,
    help="Opt-in gain for live-cube lateral centering along the finger axis during contact-align.",
)
parser.add_argument(
    "--lateral_centering_limit",
    default=0.0,
    type=float,
    help="Maximum norm of the lateral centering correction in meters; <=0 disables limiting.",
)
parser.add_argument(
    "--lateral_search_amplitude",
    default=0.0,
    type=float,
    help="Optional sinusoidal search amplitude along the finger axis during contact-align.",
)
parser.add_argument(
    "--lateral_search_period",
    default=32,
    type=int,
    help="Period in env steps for --lateral_search_amplitude.",
)
parser.add_argument("--close_steps", default=80, type=int)
parser.add_argument(
    "--close_gripper_width",
    default=-1.0,
    type=float,
    help=(
        "Target gripper gap in meters during close/lift. Negative values use "
        "cube_size + --close_gripper_width_offset."
    ),
)
parser.add_argument(
    "--close_gripper_width_offset",
    default=-0.002,
    type=float,
    help="Auto close width offset from cube size in meters; default is a light 2 mm total squeeze.",
)
parser.add_argument(
    "--min_finger_cube_surface_margin",
    default=-0.006,
    type=float,
    help=(
        "Minimum allowed signed AABB margin for left/right finger body positions relative to the cube. "
        "Negative values mean the measured body point is inside the cube."
    ),
)
parser.add_argument("--lift_steps", default=120, type=int)
parser.add_argument("--lift_height", default=0.14, type=float)
parser.add_argument("--finger_gain", default=0.75, type=float)
parser.add_argument("--clip_actions", default=1.0, type=float)
parser.add_argument(
    "--pose_action_filter",
    choices=("clip", "scale"),
    default="clip",
    help=(
        "How to handle raw normalized pose commands that exceed the action limit. "
        "'clip' preserves the prior per-component saturation. 'scale' uniformly "
        "scales the 6D pose command under --pose_action_limit before the final "
        "physical clip, so action-limit artifacts are visible in audit fields."
    ),
)
parser.add_argument(
    "--pose_action_limit",
    default=1.0,
    type=float,
    help="Normalized pose-action magnitude used by --pose_action_filter scale.",
)
parser.add_argument(
    "--orientation_mode",
    choices=("live", "source"),
    default="live",
    help=(
        "Target EE orientation while translating the measured finger center. "
        "'live' preserves the current reset orientation; 'source' drives back to "
        "the selected source/dataset row orientation."
    ),
)
parser.add_argument(
    "--reset_joint_blend_alpha",
    default=1.0,
    type=float,
    help=(
        "Blend the post-task-reset robot joints toward the source trajectory joints before rollout. "
        "1.0 uses exact source joints; 0.0 leaves the task reset robot joints. Cube/object reset still "
        "uses the selected source row."
    ),
)
parser.add_argument(
    "--reset_cube_pos_blend_alpha",
    default=1.0,
    type=float,
    help=(
        "Blend the task-reset cube pose toward the selected source-row cube pose before rollout. "
        "1.0 preserves previous source-cube relabel behavior; 0.0 keeps the normal task-reset cube."
    ),
)
parser.add_argument(
    "--reset_cube_xy",
    type=float,
    nargs=2,
    default=None,
    help=(
        "Optional explicit task-frame cube XY reset. This overrides the XY produced by "
        "--reset_cube_pos_blend_alpha while preserving the selected reset orientation."
    ),
)
parser.add_argument(
    "--reset_cube_z",
    type=float,
    default=None,
    help="Optional explicit task-frame cube Z reset. Defaults to env cfg cube_spawn_z when --reset_cube_xy is set.",
)
parser.add_argument("--print_interval", default=40, type=int)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", default=280, type=int)
parser.add_argument("--video_name_prefix", default="franka-cube-contact-rollout", type=str)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument(
    "--save_rgb_obs",
    action="store_true",
    default=False,
    help="Save pre-action RGB frames and robot proprio for image-policy BC.",
)
parser.add_argument("--rgb_obs_height", default=96, type=int)
parser.add_argument("--rgb_obs_width", default=96, type=int)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video or args_cli.save_rgb_obs:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
from dextrah_lab.offline_dp_bc.action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    derive_relative_ee_actions,
    gripper_width_to_action,
)
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_PPO_OBS_DIM,
    extract_lowdim_obs_from_ppo_obs,
)


KNOWN_VARIANTS: dict[str, tuple[float, float, float]] = {
    "center": (0.0, 0.0, 0.0),
    "center_high15": (0.0, 0.0, 0.015),
    "center_high30": (0.0, 0.0, 0.030),
}


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    ep_idx = min(max(ep_idx, 0), int(episode_ends.shape[0] - 1))
    start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    end = int(episode_ends[ep_idx])
    return ep_idx, start, end


def _row_for_episode_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> int:
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    local_step = int(np.clip(int(episode_step), 0, max(0, end - start - 1)))
    return int(start + local_step)


def _parse_variant(spec: str) -> tuple[str, np.ndarray]:
    if ":" not in spec:
        if spec not in KNOWN_VARIANTS:
            raise ValueError(f"Unknown variant {spec!r}; use one of {sorted(KNOWN_VARIANTS)} or name:x,y,z")
        return spec, np.asarray(KNOWN_VARIANTS[spec], dtype=np.float32)
    name, raw = spec.split(":", 1)
    values = [float(v) for v in raw.split(",")]
    if len(values) != 3:
        raise ValueError(f"Variant offset must have three comma-separated values: {spec}")
    return name, np.asarray(values, dtype=np.float32)


def _policy_obs_from_reset(reset_out: Any) -> torch.Tensor:
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    return obs["policy"] if isinstance(obs, dict) else obs


def _policy_obs_from_step(step_out: Any) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    if len(step_out) == 5:
        obs, rewards, terminated, truncated, _info = step_out
    else:
        obs, rewards, dones, _info = step_out
        terminated = dones
        truncated = torch.zeros_like(dones, dtype=torch.bool)
    return obs["policy"] if isinstance(obs, dict) else obs, rewards, terminated, truncated


def _policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _lowdim_numpy_from_policy_obs(policy_obs: Any) -> np.ndarray:
    lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs)
    if hasattr(lowdim, "detach"):
        lowdim_np = lowdim.detach().float().cpu().numpy()
    else:
        lowdim_np = np.asarray(lowdim, dtype=np.float32)
    if lowdim_np.ndim == 1:
        return lowdim_np.astype(np.float32, copy=False)
    if lowdim_np.ndim == 2 and lowdim_np.shape[0] >= 1:
        return lowdim_np[0].astype(np.float32, copy=False)
    raise ValueError(f"Expected lowdim obs shape (21,) or (N, 21), got {lowdim_np.shape}")


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in str(value))


def _robot_state_from_lowdim(lowdim: np.ndarray) -> np.ndarray:
    """Non-privileged robot proprio: EE position, EE quaternion, gripper width."""

    return np.concatenate((lowdim[:7], lowdim[20:21]), axis=0).astype(np.float32)


def _resize_rgb_nearest(frame: np.ndarray, height: int, width: int) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[-1] < 3:
        raise ValueError(f"Expected RGB/RGBA frame with shape (H,W,3/4), got {frame.shape}")
    rgb = np.asarray(frame[..., :3])
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    h, w = rgb.shape[:2]
    side = min(h, w)
    y0 = max(0, (h - side) // 2)
    x0 = max(0, (w - side) // 2)
    crop = rgb[y0 : y0 + side, x0 : x0 + side]
    ys = np.linspace(0, side - 1, int(height)).astype(np.int64)
    xs = np.linspace(0, side - 1, int(width)).astype(np.int64)
    return crop[ys][:, xs].copy()


def _render_rgb_obs(gym_env: Any, height: int, width: int) -> np.ndarray:
    frame = gym_env.render()
    if isinstance(frame, list):
        if not frame:
            raise RuntimeError("gym_env.render() returned an empty frame list")
        frame = frame[-1]
    return _resize_rgb_nearest(np.asarray(frame), height=height, width=width)


def _map_source_joint_to_env(task_env: Any, raw_q: np.ndarray, env_ids: torch.Tensor) -> torch.Tensor:
    num_ids = int(env_ids.numel())
    raw_q_tensor = torch.as_tensor(raw_q, dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    joint_pos = task_env._robot.data.default_joint_pos[env_ids].clone()
    arm_count = len(task_env.arm_joint_ids)
    finger_count = len(task_env.finger_joint_ids)
    if raw_q_tensor.shape[1] == joint_pos.shape[1]:
        joint_pos[:] = raw_q_tensor
    elif raw_q_tensor.shape[1] == arm_count + finger_count:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + finger_count]
    elif raw_q_tensor.shape[1] == arm_count + 1:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + 1].repeat(1, finger_count)
    else:
        raise ValueError(f"Cannot map source joint dim {raw_q_tensor.shape[1]} to env joints {joint_pos.shape[1]}")
    return torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _reset_to_source(
    gym_env: Any,
    task_env: Any,
    *,
    dataset_obs: np.ndarray,
    episode_start: int,
    row_idx: int,
    raw_q: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    normal_policy_obs = _policy_obs_from_reset(gym_env.reset(seed=int(seed)))
    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    num_ids = int(env_ids.numel())
    normal_lowdim = _lowdim_numpy_from_policy_obs(normal_policy_obs)
    normal_joint_pos = task_env._robot.data.joint_pos[env_ids].clone()
    source_joint_pos = _map_source_joint_to_env(task_env, raw_q, env_ids)
    alpha = float(np.clip(float(args_cli.reset_joint_blend_alpha), 0.0, 1.0))
    cube_alpha = float(np.clip(float(args_cli.reset_cube_pos_blend_alpha), 0.0, 1.0))
    joint_pos = normal_joint_pos + alpha * (source_joint_pos - normal_joint_pos)
    joint_pos = torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)
    joint_vel = torch.zeros_like(joint_pos)
    task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    task_env.robot_dof_targets[env_ids] = joint_pos
    task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]

    target_obs = dataset_obs[row_idx]
    source_cube_pos = torch.as_tensor(target_obs[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    source_cube_quat = torch.as_tensor(target_obs[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    normal_cube_pos = torch.as_tensor(normal_lowdim[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    normal_cube_quat = torch.as_tensor(normal_lowdim[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    cube_pos = normal_cube_pos + cube_alpha * (source_cube_pos - normal_cube_pos)
    quat_dot = torch.sum(normal_cube_quat * source_cube_quat, dim=1, keepdim=True)
    source_cube_quat = torch.where(quat_dot < 0.0, -source_cube_quat, source_cube_quat)
    cube_quat = normal_cube_quat + cube_alpha * (source_cube_quat - normal_cube_quat)
    cube_quat = torch.nn.functional.normalize(cube_quat, dim=1)
    reset_cube_xy = getattr(args_cli, "reset_cube_xy", None)
    reset_cube_z = getattr(args_cli, "reset_cube_z", None)
    if reset_cube_xy is not None:
        xy = torch.as_tensor(reset_cube_xy, dtype=torch.float32, device=task_env.device).reshape(1, 2)
        cube_pos[:, 0:2] = xy.repeat(num_ids, 1)
        z_value = float(task_env.cfg.cube_spawn_z) if reset_cube_z is None else float(reset_cube_z)
        cube_pos[:, 2] = z_value
    object_state = torch.zeros(num_ids, 13, device=task_env.device)
    object_state[:, 0:3] = cube_pos + task_env.scene.env_origins[env_ids]
    object_state[:, 3:7] = cube_quat
    task_env._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
    task_env.cube_initial_pos[env_ids] = cube_pos
    task_env.cube_goal_pos[env_ids] = cube_pos
    task_env.cube_goal_pos[env_ids, 2] = cube_pos[:, 2] + float(task_env.cfg.cube_lift_height)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env.actions[env_ids] = 0.0
    task_env.ik_controller.reset(env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    reset_policy_obs = _policy_obs_from_task_env(task_env).detach().float().cpu().numpy()[0]
    reset_lowdim = _lowdim_numpy_from_policy_obs(reset_policy_obs[None])
    target_lowdim = np.asarray(dataset_obs[row_idx], dtype=np.float32)
    applied_joint_np = joint_pos.detach().float().cpu().numpy()[0]
    source_joint_np = source_joint_pos.detach().float().cpu().numpy()[0]
    normal_joint_np = normal_joint_pos.detach().float().cpu().numpy()[0]
    reset_summary = {
        "reset_joint_blend_alpha": alpha,
        "reset_cube_pos_blend_alpha": cube_alpha,
        "reset_joint_l2_from_source": float(np.linalg.norm(applied_joint_np - source_joint_np)),
        "reset_joint_linf_from_source": float(np.max(np.abs(applied_joint_np - source_joint_np))),
        "reset_joint_l2_from_normal": float(np.linalg.norm(applied_joint_np - normal_joint_np)),
        "reset_joint_linf_from_normal": float(np.max(np.abs(applied_joint_np - normal_joint_np))),
        "reset_lowdim_l2_from_dataset": float(np.linalg.norm(reset_lowdim - target_lowdim)),
        "reset_cube_minus_ee_l2_from_dataset": float(np.linalg.norm(reset_lowdim[14:17] - target_lowdim[14:17])),
        "reset_cube_pos_l2_from_dataset": float(np.linalg.norm(reset_lowdim[7:10] - target_lowdim[7:10])),
        "reset_cube_pos_l2_from_normal": float(np.linalg.norm(reset_lowdim[7:10] - normal_lowdim[7:10])),
        "reset_ee_pos_l2_from_dataset": float(np.linalg.norm(reset_lowdim[:3] - target_lowdim[:3])),
        "source_cube_pos": source_cube_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
        "normal_reset_cube_pos": normal_lowdim[7:10].astype(float).tolist(),
        "applied_cube_pos": cube_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
        "reset_cube_xy_override": (
            np.asarray(reset_cube_xy, dtype=np.float32).astype(float).tolist()
            if reset_cube_xy is not None
            else None
        ),
        "reset_cube_z_override": None if reset_cube_z is None else float(reset_cube_z),
        "source_joint_position": source_joint_np.astype(float).tolist(),
        "normal_reset_joint_position": normal_joint_np.astype(float).tolist(),
        "applied_joint_position": applied_joint_np.astype(float).tolist(),
    }
    return reset_policy_obs, reset_summary


def _finger_center(task_env: Any) -> np.ndarray:
    task_env._compute_intermediate_values()
    left = task_env.left_finger_pos.detach().float().cpu().numpy()[0]
    right = task_env.right_finger_pos.detach().float().cpu().numpy()[0]
    return 0.5 * (left + right)


def _axis_aligned_cube_signed_margin(points: np.ndarray, cube_pos: np.ndarray, cube_size: float) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32).reshape((-1, 3))
    center = np.asarray(cube_pos, dtype=np.float32).reshape((1, 3))
    half = 0.5 * float(cube_size)
    q = np.abs(points - center) - half
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=1)
    inside = np.minimum(np.max(q, axis=1), 0.0)
    return (outside + inside).astype(np.float32)


def _finger_geometry(task_env: Any, cube_pos: np.ndarray, *, cube_size: float) -> dict[str, Any]:
    task_env._compute_intermediate_values()
    left = task_env.left_finger_pos.detach().float().cpu().numpy()[0].astype(np.float32)
    right = task_env.right_finger_pos.detach().float().cpu().numpy()[0].astype(np.float32)
    center = 0.5 * (left + right)
    cube = np.asarray(cube_pos, dtype=np.float32)
    margins = _axis_aligned_cube_signed_margin(np.stack((left, right, center), axis=0), cube, float(cube_size))
    axis = left - right
    axis[2] = 0.0
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm < 1.0e-6:
        axis = np.asarray((1.0, 0.0, 0.0), dtype=np.float32)
    else:
        axis = (axis / axis_norm).astype(np.float32)
    lateral_signed = float(np.dot(cube - center, axis))
    left_dist = float(np.linalg.norm(left - cube))
    right_dist = float(np.linalg.norm(right - cube))
    return {
        "left": left,
        "right": right,
        "center": center,
        "axis": axis,
        "lateral_signed": lateral_signed,
        "left_dist": left_dist,
        "right_dist": right_dist,
        "balance_abs": float(abs(left_dist - right_dist)),
        "left_surface_margin": float(margins[0]),
        "right_surface_margin": float(margins[1]),
        "center_surface_margin": float(margins[2]),
        "surface_margin_min": float(min(margins[0], margins[1])),
    }


def _lateral_contact_adjust(geometry: dict[str, Any], contact_step: int) -> tuple[np.ndarray, dict[str, float | list[float]]]:
    axis = np.asarray(geometry["axis"], dtype=np.float32)
    correction = np.zeros(3, dtype=np.float32)
    gain = float(args_cli.lateral_centering_gain)
    if math.isfinite(gain) and gain != 0.0:
        correction += gain * float(geometry["lateral_signed"]) * axis
    amplitude = float(args_cli.lateral_search_amplitude)
    if math.isfinite(amplitude) and amplitude != 0.0:
        period = max(1, int(args_cli.lateral_search_period))
        phase = 2.0 * math.pi * (float(contact_step) / float(period))
        correction += float(amplitude * math.sin(phase)) * axis
    correction[2] = 0.0
    raw = correction.copy()
    limit = float(args_cli.lateral_centering_limit)
    norm = float(np.linalg.norm(correction))
    scale = 1.0
    if math.isfinite(limit) and limit > 0.0 and norm > limit:
        scale = float(limit / max(norm, 1.0e-12))
        correction *= scale
        norm = float(np.linalg.norm(correction))
    return correction.astype(np.float32), {
        "lateral_axis": axis.astype(float).tolist(),
        "lateral_signed_error": float(geometry["lateral_signed"]),
        "lateral_centering_raw": raw.astype(float).tolist(),
        "lateral_centering_correction": correction.astype(float).tolist(),
        "lateral_centering_norm": norm,
        "lateral_centering_scale": float(scale),
    }


def _contact_gate_ok(row: dict[str, Any]) -> bool:
    center_ok = float(row["finger_center_to_cube"]) <= float(args_cli.contact_align_threshold)
    surface_margin = row.get("finger_cube_surface_margin_min")
    surface_ok = True
    if surface_margin is not None:
        surface_ok = float(surface_margin) >= float(args_cli.min_finger_cube_surface_margin)
    if str(args_cli.contact_gate_mode) == "center":
        return bool(center_ok and surface_ok)
    left_ok = float(row["left_finger_to_cube"]) <= float(args_cli.finger_gate_max_distance)
    right_ok = float(row["right_finger_to_cube"]) <= float(args_cli.finger_gate_max_distance)
    balance_ok = float(row["finger_distance_balance_abs"]) <= float(args_cli.finger_gate_balance_threshold)
    return bool(center_ok and left_ok and right_ok and balance_ok and surface_ok)


def _close_gripper_target(cube_size: float) -> tuple[float, float]:
    if float(args_cli.close_gripper_width) >= 0.0:
        width = float(args_cli.close_gripper_width)
    else:
        width = float(cube_size) + float(args_cli.close_gripper_width_offset)
    max_width = float(DEFAULT_DEXTRAH_ACTION_CONVENTION.max_gripper_width)
    width = float(np.clip(width, 0.0, max_width))
    action = float(np.asarray(gripper_width_to_action(np.asarray(width, dtype=np.float32))).item())
    return width, action


def _action_to_finger_target(
    live_lowdim: np.ndarray,
    finger_center: np.ndarray,
    target_finger_center: np.ndarray,
    *,
    target_ee_quat: np.ndarray | None,
    gripper_action: float,
    gain: float,
    clip: float,
    pose_action_filter: str,
    pose_action_limit: float,
) -> tuple[np.ndarray, dict[str, float | str | list[float]]]:
    finger_error = np.asarray(target_finger_center, dtype=np.float32) - np.asarray(finger_center, dtype=np.float32)
    target_ee_pos = live_lowdim[:3] + float(gain) * finger_error
    ee_pos = np.stack((live_lowdim[:3], target_ee_pos), axis=0).astype(np.float32)
    target_quat = live_lowdim[3:7] if target_ee_quat is None else np.asarray(target_ee_quat, dtype=np.float32)
    ee_quat = np.stack((live_lowdim[3:7], target_quat), axis=0).astype(np.float32)
    grip = np.asarray([float(gripper_action), float(gripper_action)], dtype=np.float32)
    raw_convention = replace(DEFAULT_DEXTRAH_ACTION_CONVENTION, clip_actions=False)
    raw_action = derive_relative_ee_actions(
        ee_pos,
        ee_quat,
        gripper_action=grip,
        convention=raw_convention,
        terminal_action="drop",
    )[0].astype(np.float32)
    action = raw_action.copy()
    raw_pose = raw_action[:6].copy()
    raw_pose_max = float(np.max(np.abs(raw_pose))) if raw_pose.size else 0.0
    filter_scale = 1.0
    limit = float(pose_action_limit)
    if str(pose_action_filter) == "scale" and math.isfinite(limit) and limit > 0.0 and raw_pose_max > limit:
        filter_scale = float(limit / max(raw_pose_max, 1.0e-12))
        action[:6] = action[:6] * filter_scale
    filtered_pose_max = float(np.max(np.abs(action[:6]))) if action[:6].size else 0.0
    clip_value = float(clip)
    if math.isfinite(clip_value) and clip_value > 0:
        action = np.clip(action, -clip_value, clip_value)
    executed_pose_max = float(np.max(np.abs(action[:6]))) if action[:6].size else 0.0
    clip_threshold = clip_value if math.isfinite(clip_value) and clip_value > 0 else float("inf")
    audit = {
        "pose_action_filter": str(pose_action_filter),
        "pose_action_limit": float(limit),
        "raw_executed_action": raw_action.astype(float).tolist(),
        "raw_pose_action_max_abs": raw_pose_max,
        "filtered_pose_action_max_abs": filtered_pose_max,
        "executed_pose_action_max_abs": executed_pose_max,
        "pose_action_filter_scale": float(filter_scale),
        "raw_pose_action_would_clip_fraction": float(np.count_nonzero(np.abs(raw_pose) >= clip_threshold - 1.0e-6) / 6.0),
    }
    return action, audit


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    variants = list(dict.fromkeys(str(row["variant"]) for row in rows))
    fig, axes = plt.subplots(10, 1, figsize=(13, 28), sharex=True, constrained_layout=True)
    for variant in variants:
        vrows = [row for row in rows if row["variant"] == variant]
        x = [int(row["global_step"]) for row in vrows]
        axes[0].plot(x, [row["ee_to_cube"] for row in vrows], label=f"{variant} ee")
        axes[0].plot(x, [row["finger_center_to_cube"] for row in vrows], linestyle="--", label=f"{variant} finger")
        axes[1].plot(x, [row["cube_lift_height"] for row in vrows], label=variant)
        axes[2].plot(x, [row["gripper_width"] for row in vrows], label=f"{variant} width")
        axes[2].plot(x, [row["gripper_action"] for row in vrows], linestyle="--", label=f"{variant} action")
        axes[3].plot(x, [row["finger_error_norm"] for row in vrows], label=variant)
        axes[4].plot(x, [row["pose_action_clip_fraction"] for row in vrows], label=f"{variant} executed clip")
        axes[4].plot(
            x,
            [row.get("raw_pose_action_would_clip_fraction", 0.0) for row in vrows],
            linestyle="--",
            label=f"{variant} raw would clip",
        )
        axes[5].plot(x, [row.get("raw_pose_action_max_abs", 0.0) for row in vrows], label=f"{variant} raw")
        axes[5].plot(
            x,
            [row.get("executed_pose_action_max_abs", 0.0) for row in vrows],
            linestyle="--",
            label=f"{variant} executed",
        )
        axes[6].plot(x, [row.get("target_minus_cube_norm", 0.0) for row in vrows], label=variant)
        axes[7].plot(x, [row.get("left_finger_to_cube", 0.0) for row in vrows], label=f"{variant} left")
        axes[7].plot(x, [row.get("right_finger_to_cube", 0.0) for row in vrows], linestyle="--", label=f"{variant} right")
        axes[7].plot(x, [row.get("finger_distance_balance_abs", 0.0) for row in vrows], linestyle=":", label=f"{variant} balance")
        axes[8].plot(x, [row.get("finger_cube_surface_margin_min", 0.0) for row in vrows], label=f"{variant} min")
        axes[8].plot(
            x,
            [row.get("left_finger_cube_surface_margin", 0.0) for row in vrows],
            linestyle="--",
            label=f"{variant} left",
        )
        axes[8].plot(
            x,
            [row.get("right_finger_cube_surface_margin", 0.0) for row in vrows],
            linestyle=":",
            label=f"{variant} right",
        )
        axes[8].axhline(float(args_cli.min_finger_cube_surface_margin), color="k", linewidth=1.0, alpha=0.45)
        axes[9].plot(x, [row.get("lateral_centering_norm", 0.0) for row in vrows], label=f"{variant} correction")
        axes[9].plot(x, [row.get("lateral_signed_error", 0.0) for row in vrows], linestyle="--", label=f"{variant} signed")
    axes[0].set_title("EE/Finger-Center To Cube")
    axes[0].set_ylabel("m")
    axes[1].set_title("Cube Lift Height")
    axes[1].set_ylabel("m")
    axes[2].set_title("Gripper Width And Action")
    axes[2].set_ylabel("m / action")
    axes[3].set_title("Finger-Center Target Error")
    axes[3].set_ylabel("m")
    axes[4].set_title("Pose Action Clip Fraction")
    axes[4].set_ylabel("fraction")
    axes[5].set_title("Pose Action Max Abs")
    axes[5].set_ylabel("normalized")
    axes[6].set_title("Target Anchor Offset From Live Cube")
    axes[6].set_ylabel("m")
    axes[7].set_title("Left/Right Finger Geometry")
    axes[7].set_ylabel("m")
    axes[8].set_title("Finger Body Signed Margin To Cube AABB")
    axes[8].set_ylabel("m")
    axes[9].set_title("Lateral Centering")
    axes[9].set_ylabel("m")
    axes[9].set_xlabel("global step")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _latest_video_files(video_folder: Path) -> list[str]:
    if not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube Contact-Aware Rollout Smoke",
        "",
        "This bounded Isaac smoke does not train. It probes whether a live controller rollout that targets measured finger-center geometry can produce a stable close/lift trajectory before any DP BC work resumes.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Controller / Action Audit",
        "",
        f"- action convention: DEXTRAH 7D relative EE pose + gripper, position scale `{DEFAULT_DEXTRAH_ACTION_CONVENTION.position_scale}`, rotation scale `{DEFAULT_DEXTRAH_ACTION_CONVENTION.rotation_scale}`, gripper `+1=open/-1=close`",
        f"- pose action filter: `{summary['pose_action_filter']}`",
        f"- pose action limit: `{summary['pose_action_limit']:.4f}`",
        f"- final physical clip: `{summary['clip_actions']:.4f}`",
        f"- EE orientation mode: `{summary['orientation_mode']}`",
        f"- reset seed: `{summary['seed']}`",
        f"- gripper timing: align/open `{summary['align_steps']}` steps, contact-align/open `{summary['contact_align_steps']}` steps, close `{summary['close_steps']}` steps, lift `{summary['lift_steps']}` steps",
        f"- close gripper target: width `{summary['close_gripper_width_target']:.5f}` m, action `{summary['close_gripper_action_target']:.4f}`",
        f"- minimum finger/cube signed surface margin: `{summary['min_finger_cube_surface_margin']:.4f}` m",
        f"- contact-align reference: `{summary['contact_align_reference']}`",
        f"- close/hold reference: `{summary['close_hold_reference']}`",
        f"- contact-align threshold: `{summary['contact_align_threshold']:.4f}` m",
        f"- contact gate mode: `{summary['contact_gate_mode']}`",
        f"- require contact gate: `{summary['require_contact_gate']}`",
        f"- left/right finger gate: max distance `{summary['finger_gate_max_distance']:.4f}` m, balance `{summary['finger_gate_balance_threshold']:.4f}` m",
        f"- lateral centering: gain `{summary['lateral_centering_gain']:.4f}`, limit `{summary['lateral_centering_limit']:.4f}` m, search amplitude `{summary['lateral_search_amplitude']:.4f}` m, period `{summary['lateral_search_period']}`",
        "- contact-align behavior: when enabled, the rollout starts close/hold as soon as the threshold is reached and freezes the live contact anchor for close/lift.",
        "",
        "## Variant Summary",
        "",
        "| variant | orientation | filter | joint alpha | cube alpha | reset cube-minus-EE L2 | pre-close step | pre-close finger | pre-close margin | min margin | final margin | pre-close left/right/bal | pre-close EE | contact-ok | close start | trigger step | offset | steps | final EE-cube | min finger-cube | final finger-cube | max lift | final lift | final grip width | max clip | max raw | min scale | terminal next | skipped reset step | success-like |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for variant, payload in summary["variants"].items():
        lines.append(
            f"| {variant} | {payload['orientation_mode']} | {payload['pose_action_filter']} | "
            f"{payload['reset_joint_blend_alpha']:.3f} | {payload['reset_cube_pos_blend_alpha']:.3f} | "
            f"{payload['reset_cube_minus_ee_l2_from_dataset']:.5f} | "
            f"{payload['pre_close_local_step']} | "
            f"{payload['pre_close_finger_center_to_cube']:.4f} | "
            f"{payload['pre_close_finger_cube_surface_margin_min']:.4f} | "
            f"{payload['min_finger_cube_surface_margin']:.4f} | "
            f"{payload['final_finger_cube_surface_margin_min']:.4f} | "
            f"{payload['pre_close_left_finger_to_cube']:.4f}/{payload['pre_close_right_finger_to_cube']:.4f}/{payload['pre_close_finger_distance_balance_abs']:.4f} | "
            f"{payload['pre_close_ee_to_cube']:.4f} | "
            f"{payload['contact_align_success']} | {payload['close_start_local_step']} | "
            f"{payload['contact_align_trigger_step']} | {payload['offset']} | {payload['steps']} | "
            f"{payload['final_ee_to_cube']:.4f} | {payload['min_finger_center_to_cube']:.4f} | "
            f"{payload['final_finger_center_to_cube']:.4f} | {payload['max_cube_lift_height']:.4f} | "
            f"{payload['final_cube_lift_height']:.4f} | {payload['final_gripper_width']:.5f} | "
            f"{payload['max_pose_action_clip_fraction']:.3f} | {payload['max_raw_pose_action_max_abs']:.3f} | "
            f"{payload['min_pose_action_filter_scale']:.3f} | {payload['terminated_next_step']} | "
            f"{payload['skipped_post_reset_local_step']} | {payload['success_like']} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- CSV: `{summary['csv']}`",
            f"- JSON: `{summary['json']}`",
            f"- Plot: `{summary['plot']}`",
            f"- Videos: `{summary['video_files']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_contact_rollout_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args_cli.dataset).expanduser().resolve()
    trajectory_path = Path(args_cli.trajectory_json).expanduser().resolve()
    data = np.load(dataset_path, allow_pickle=False)
    dataset_obs = np.asarray(data["obs"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    row_idx = _row_for_episode_step(episode_ends, int(args_cli.episode), int(args_cli.episode_step))
    episode_idx, episode_start, _episode_end = _episode_for_row(row_idx, episode_ends)
    frames = json.loads(trajectory_path.read_text(encoding="utf-8"))["frames"]
    raw_q = np.asarray(frames[int(row_idx - episode_start)]["joint_position"], dtype=np.float32)
    source_ee_quat = np.asarray(dataset_obs[row_idx, 3:7], dtype=np.float32)
    variants = [_parse_variant(v) for v in (args_cli.variant or ["center", "center_high15", "center_high30"])]

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    if hasattr(env_cfg, "viewer"):
        env_cfg.viewer.eye = tuple(args_cli.camera_eye)
        env_cfg.viewer.lookat = tuple(args_cli.camera_target)
        env_cfg.viewer.origin_type = "world"
    gym_env = gym.make(
        args_cli.task,
        cfg=env_cfg,
        render_mode="rgb_array" if (args_cli.video or args_cli.save_rgb_obs) else None,
    )
    task_env = gym_env.unwrapped
    cube_size = float(getattr(task_env.cfg, "cube_size", 0.06))
    close_gripper_width_target, close_gripper_action_target = _close_gripper_target(cube_size)
    if hasattr(task_env, "sim") and hasattr(env_cfg, "viewer"):
        try:
            task_env.sim.set_camera_view(eye=tuple(args_cli.camera_eye), target=tuple(args_cli.camera_target))
        except Exception:
            pass
    steps_per_variant = int(
        args_cli.align_steps + args_cli.contact_align_steps + args_cli.close_steps + args_cli.lift_steps
    )
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(output_dir / "videos"),
            step_trigger=lambda step: step % max(1, steps_per_variant) == 0,
            video_length=int(args_cli.video_length),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )

    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    global_step = 0
    try:
        for variant_idx, (variant_name, offset) in enumerate(variants):
            policy_obs, reset_summary = _reset_to_source(
                gym_env,
                task_env,
                dataset_obs=dataset_obs,
                episode_start=episode_start,
                row_idx=row_idx,
                raw_q=raw_q,
                seed=int(args_cli.seed),
            )
            if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
                raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")
            initial_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0].copy()
            contact_anchor_cube_pos = initial_cube_pos.copy()
            align_end = int(args_cli.align_steps)
            contact_end = align_end + int(args_cli.contact_align_steps)
            close_start_step: int | None = None
            contact_align_trigger_step: int | None = None
            pre_close_row: dict[str, Any] | None = None
            contact_target_offset = offset.copy()
            rgb_images: list[np.ndarray] = []
            rgb_robot_states: list[np.ndarray] = []
            rgb_actions: list[np.ndarray] = []
            rgb_phase_ids: list[int] = []
            rgb_local_steps: list[int] = []
            if args_cli.save_rgb_obs:
                try:
                    _render_rgb_obs(gym_env, int(args_cli.rgb_obs_height), int(args_cli.rgb_obs_width))
                except Exception as exc:
                    print(f"[WARN] RGB warmup render failed: {exc}", flush=True)
            for local_step in range(steps_per_variant):
                if local_step < align_end:
                    phase = "align_open"
                    gripper = 1.0
                    lift_delta = np.zeros(3, dtype=np.float32)
                    target_reference = "initial_cube"
                    target_base = initial_cube_pos
                else:
                    if (
                        close_start_step is None
                        and local_step >= contact_end
                        and not bool(args_cli.require_contact_gate)
                    ):
                        close_start_step = int(local_step)
                    if close_start_step is None:
                        phase = "contact_align_open"
                        gripper = 1.0
                        lift_delta = np.zeros(3, dtype=np.float32)
                        target_reference = str(args_cli.contact_align_reference)
                        if args_cli.contact_align_reference == "live_cube":
                            task_env._compute_intermediate_values()
                            contact_anchor_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0].copy()
                        target_base = contact_anchor_cube_pos
                    elif local_step < close_start_step + int(args_cli.close_steps):
                        phase = "close_hold"
                        gripper = close_gripper_action_target
                        lift_delta = np.zeros(3, dtype=np.float32)
                        if args_cli.close_hold_reference == "live_cube":
                            task_env._compute_intermediate_values()
                            contact_anchor_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0].copy()
                        target_reference = str(args_cli.close_hold_reference)
                        target_base = contact_anchor_cube_pos
                    else:
                        phase = "lift"
                        gripper = close_gripper_action_target
                        frac = (local_step - (close_start_step + int(args_cli.close_steps)) + 1) / max(
                            1, int(args_cli.lift_steps)
                        )
                        lift_delta = np.asarray(
                            (0.0, 0.0, float(args_cli.lift_height) * min(1.0, frac)), dtype=np.float32
                        )
                        target_reference = "contact_anchor"
                        target_base = contact_anchor_cube_pos
                task_env._compute_intermediate_values()
                live_lowdim = _lowdim_numpy_from_policy_obs(policy_obs)
                rgb_frame = None
                if args_cli.save_rgb_obs:
                    rgb_frame = _render_rgb_obs(gym_env, int(args_cli.rgb_obs_height), int(args_cli.rgb_obs_width))
                cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0]
                finger_geom = _finger_geometry(task_env, cube_pos, cube_size=cube_size)
                finger_center = np.asarray(finger_geom["center"], dtype=np.float32)
                contact_step = max(0, local_step - align_end)
                lateral_adjust = np.zeros(3, dtype=np.float32)
                lateral_audit: dict[str, float | list[float]] = {
                    "lateral_axis": np.asarray(finger_geom["axis"], dtype=np.float32).astype(float).tolist(),
                    "lateral_signed_error": float(finger_geom["lateral_signed"]),
                    "lateral_centering_raw": [0.0, 0.0, 0.0],
                    "lateral_centering_correction": [0.0, 0.0, 0.0],
                    "lateral_centering_norm": 0.0,
                    "lateral_centering_scale": 1.0,
                }
                if phase == "contact_align_open":
                    lateral_adjust, lateral_audit = _lateral_contact_adjust(finger_geom, contact_step)
                    target_offset = (offset + lateral_adjust).astype(np.float32)
                elif phase in ("close_hold", "lift"):
                    target_offset = contact_target_offset.astype(np.float32)
                else:
                    target_offset = offset.astype(np.float32)
                target_finger = target_base + target_offset + lift_delta
                target_ee_quat = source_ee_quat if args_cli.orientation_mode == "source" else None
                action, action_audit = _action_to_finger_target(
                    live_lowdim,
                    finger_center,
                    target_finger,
                    target_ee_quat=target_ee_quat,
                    gripper_action=gripper,
                    gain=float(args_cli.finger_gain),
                    clip=float(args_cli.clip_actions),
                    pose_action_filter=str(args_cli.pose_action_filter),
                    pose_action_limit=float(args_cli.pose_action_limit),
                )
                clip_value = float(args_cli.clip_actions)
                if math.isfinite(clip_value) and clip_value > 0.0:
                    clip_hits = np.abs(action[:6]) >= (clip_value - 1.0e-6)
                else:
                    clip_hits = np.zeros_like(action[:6], dtype=bool)
                policy_obs, rewards, terminated, truncated = _policy_obs_from_step(
                    gym_env.step(torch.as_tensor(action[None], dtype=torch.float32, device=task_env.device))
                )
                after_lowdim = _lowdim_numpy_from_policy_obs(policy_obs)
                task_env._compute_intermediate_values()
                after_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0]
                after_finger_geom = _finger_geometry(task_env, after_cube_pos, cube_size=cube_size)
                terminated_flag = bool(terminated.detach().cpu().numpy()[0]) if hasattr(terminated, "detach") else bool(terminated[0])
                truncated_flag = bool(truncated.detach().cpu().numpy()[0]) if hasattr(truncated, "detach") else bool(truncated[0])
                done_flag = terminated_flag or truncated_flag
                if done_flag:
                    if rows and rows[-1].get("variant") == variant_name:
                        rows[-1]["terminated_next_step"] = terminated_flag
                        rows[-1]["truncated_next_step"] = truncated_flag
                        rows[-1]["terminal_reward_next"] = float(rewards.detach().float().cpu()[0])
                        rows[-1]["skipped_post_reset_local_step"] = int(local_step)
                        rows[-1]["skipped_post_reset_gripper_width"] = float(after_lowdim[20])
                        rows[-1]["skipped_post_reset_cube_lift_height"] = float(
                            task_env.cube_lift_height.detach().cpu()[0]
                        )
                    break
                row = {
                    "variant": variant_name,
                    "variant_index": variant_idx,
                    "offset": offset.astype(float).tolist(),
                    "global_step": global_step,
                    "local_step": local_step,
                    "phase": phase,
                    "episode": int(episode_idx),
                    "episode_step": int(row_idx - episode_start),
                    "source_row": int(row_idx),
                    "source_trajectory_json": str(trajectory_path),
                    "orientation_mode": str(args_cli.orientation_mode),
                    "reset_joint_blend_alpha": float(reset_summary["reset_joint_blend_alpha"]),
                    "reset_cube_pos_blend_alpha": float(reset_summary["reset_cube_pos_blend_alpha"]),
                    "reset_joint_l2_from_source": float(reset_summary["reset_joint_l2_from_source"]),
                    "reset_joint_l2_from_normal": float(reset_summary["reset_joint_l2_from_normal"]),
                    "reset_lowdim_l2_from_dataset": float(reset_summary["reset_lowdim_l2_from_dataset"]),
                    "reset_cube_minus_ee_l2_from_dataset": float(
                        reset_summary["reset_cube_minus_ee_l2_from_dataset"]
                    ),
                    "lowdim_obs": live_lowdim.astype(float).tolist(),
                    "target_finger_center": target_finger.astype(float).tolist(),
                    "target_reference": target_reference,
                    "contact_anchor_cube_pos": contact_anchor_cube_pos.astype(float).tolist(),
                    "target_offset": target_offset.astype(float).tolist(),
                    "target_minus_cube": (target_finger - cube_pos).astype(float).tolist(),
                    "target_minus_cube_norm": float(np.linalg.norm(target_finger - cube_pos)),
                    "contact_align_threshold": float(args_cli.contact_align_threshold),
                    "contact_align_triggered_close": False,
                    "contact_align_trigger_step": -1,
                    "close_start_local_step": (
                        int(close_start_step) if close_start_step is not None else -1
                    ),
                    "contact_gate_mode": str(args_cli.contact_gate_mode),
                    "require_contact_gate": bool(args_cli.require_contact_gate),
                    "finger_gate_max_distance": float(args_cli.finger_gate_max_distance),
                    "finger_gate_balance_threshold": float(args_cli.finger_gate_balance_threshold),
                    "cube_size": cube_size,
                    "close_gripper_width_target": close_gripper_width_target,
                    "close_gripper_action_target": close_gripper_action_target,
                    "min_finger_cube_surface_margin_threshold": float(args_cli.min_finger_cube_surface_margin),
                    "target_ee_quat": (
                        source_ee_quat.astype(float).tolist()
                        if args_cli.orientation_mode == "source"
                        else live_lowdim[3:7].astype(float).tolist()
                    ),
                    "finger_center": finger_center.astype(float).tolist(),
                    "left_finger": np.asarray(finger_geom["left"], dtype=np.float32).astype(float).tolist(),
                    "right_finger": np.asarray(finger_geom["right"], dtype=np.float32).astype(float).tolist(),
                    "finger_axis": np.asarray(finger_geom["axis"], dtype=np.float32).astype(float).tolist(),
                    "finger_error_norm": float(np.linalg.norm(target_finger - finger_center)),
                    "cube_pos": cube_pos.astype(float).tolist(),
                    "post_step_cube_pos": after_cube_pos.astype(float).tolist(),
                    "left_finger_cube_surface_margin": float(after_finger_geom["left_surface_margin"]),
                    "right_finger_cube_surface_margin": float(after_finger_geom["right_surface_margin"]),
                    "finger_center_cube_surface_margin": float(after_finger_geom["center_surface_margin"]),
                    "finger_cube_surface_margin_min": float(after_finger_geom["surface_margin_min"]),
                    "pre_action_left_finger_cube_surface_margin": float(finger_geom["left_surface_margin"]),
                    "pre_action_right_finger_cube_surface_margin": float(finger_geom["right_surface_margin"]),
                    "pre_action_finger_cube_surface_margin_min": float(finger_geom["surface_margin_min"]),
                    "ee_to_cube": float(task_env.ee_to_cube_dist.detach().cpu()[0]),
                    "finger_center_to_cube": float(task_env.finger_center_to_cube_dist.detach().cpu()[0]),
                    "left_finger_to_cube": float(task_env.left_finger_to_cube_dist.detach().cpu()[0]),
                    "right_finger_to_cube": float(task_env.right_finger_to_cube_dist.detach().cpu()[0]),
                    "finger_distance_balance_abs": float(
                        abs(
                            float(task_env.left_finger_to_cube_dist.detach().cpu()[0])
                            - float(task_env.right_finger_to_cube_dist.detach().cpu()[0])
                        )
                    ),
                    "cube_lift_height": float(task_env.cube_lift_height.detach().cpu()[0]),
                    "cube_xy_error": float(task_env.cube_xy_error.detach().cpu()[0]),
                    "gripper_width": float(after_lowdim[20]),
                    "gripper_action": float(action[6]),
                    "executed_action": action.astype(float).tolist(),
                    **lateral_audit,
                    **action_audit,
                    "pose_action_clip_fraction": float(np.count_nonzero(clip_hits) / 6.0),
                    "reward": float(rewards.detach().float().cpu()[0]),
                    "terminated_next_step": False,
                    "truncated_next_step": False,
                }
                if phase in ("align_open", "contact_align_open"):
                    pre_close_row = row
                if (
                    phase == "contact_align_open"
                    and close_start_step is None
                    and _contact_gate_ok(row)
                ):
                    task_env._compute_intermediate_values()
                    contact_anchor_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0].copy()
                    contact_target_offset = target_offset.copy()
                    contact_align_trigger_step = int(local_step)
                    close_start_step = int(local_step + 1)
                    row["contact_align_triggered_close"] = True
                    row["contact_align_trigger_step"] = int(contact_align_trigger_step)
                    row["close_start_local_step"] = int(close_start_step)
                rows.append(row)
                if args_cli.save_rgb_obs and rgb_frame is not None:
                    rgb_images.append(rgb_frame)
                    rgb_robot_states.append(_robot_state_from_lowdim(live_lowdim))
                    rgb_actions.append(action.astype(np.float32, copy=True))
                    rgb_phase_ids.append({"align_open": 0, "contact_align_open": 0, "close_hold": 1, "lift": 2}.get(phase, -1))
                    rgb_local_steps.append(int(local_step))
                if args_cli.print_interval > 0 and (
                    local_step == 0 or (local_step + 1) % int(args_cli.print_interval) == 0
                ):
                    print(
                        "CONTACT_ROLLOUT_STEP "
                        + json.dumps(
                            {
                                "variant": variant_name,
                                "local_step": local_step + 1,
                                "phase": phase,
                                "finger_center_to_cube": row["finger_center_to_cube"],
                                "left_finger_to_cube": row["left_finger_to_cube"],
                                "right_finger_to_cube": row["right_finger_to_cube"],
                                "finger_balance": row["finger_distance_balance_abs"],
                                "finger_cube_surface_margin_min": row["finger_cube_surface_margin_min"],
                                "cube_lift_height": row["cube_lift_height"],
                                "gripper_width": row["gripper_width"],
                                "clip_fraction": row["pose_action_clip_fraction"],
                                "contact_gate_ok": _contact_gate_ok(row),
                                "raw_pose_action_max_abs": row["raw_pose_action_max_abs"],
                                "pose_action_filter_scale": row["pose_action_filter_scale"],
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                global_step += 1
            vrows = [row for row in rows if row["variant"] == variant_name]
            last = vrows[-1]
            max_lift = float(max(row["cube_lift_height"] for row in vrows))
            final_lift = float(last["cube_lift_height"])
            min_finger = float(min(row["finger_center_to_cube"] for row in vrows))
            min_surface_margin = float(min(row["finger_cube_surface_margin_min"] for row in vrows))
            final_surface_margin = float(last["finger_cube_surface_margin_min"])
            surface_margin_ok = bool(min_surface_margin >= float(args_cli.min_finger_cube_surface_margin))
            pre_close_rows = [
                row for row in vrows if row["phase"] in ("align_open", "contact_align_open")
            ]
            pre_close = pre_close_row if pre_close_row is not None else (pre_close_rows[-1] if pre_close_rows else vrows[0])
            contact_align_success = bool(
                contact_align_trigger_step is not None
                or _contact_gate_ok(pre_close)
            )
            success_like = bool(
                max_lift >= float(task_env.cfg.cube_success_lift_height)
                and min_finger < 0.08
                and surface_margin_ok
            )
            rgb_npz = ""
            if args_cli.save_rgb_obs and rgb_images:
                rgb_npz_path = output_dir / f"rgb_obs_{_safe_name(variant_name)}.npz"
                np.savez_compressed(
                    rgb_npz_path,
                    image=np.stack(rgb_images, axis=0).astype(np.uint8),
                    robot_state=np.asarray(rgb_robot_states, dtype=np.float32),
                    action=np.asarray(rgb_actions, dtype=np.float32),
                    phase_ids=np.asarray(rgb_phase_ids, dtype=np.int32),
                    local_steps=np.asarray(rgb_local_steps, dtype=np.int64),
                    variant=np.asarray(str(variant_name)),
                    camera_eye=np.asarray(args_cli.camera_eye, dtype=np.float32),
                    camera_target=np.asarray(args_cli.camera_target, dtype=np.float32),
                    image_shape=np.asarray([int(args_cli.rgb_obs_height), int(args_cli.rgb_obs_width), 3], dtype=np.int32),
                    robot_state_names=np.asarray(
                        [
                            "ee_pos_x",
                            "ee_pos_y",
                            "ee_pos_z",
                            "ee_quat_w",
                            "ee_quat_x",
                            "ee_quat_y",
                            "ee_quat_z",
                            "gripper_width",
                        ]
                    ),
                )
                rgb_npz = str(rgb_npz_path)
            summaries[variant_name] = {
                "offset": offset.astype(float).tolist(),
                "orientation_mode": str(args_cli.orientation_mode),
                **reset_summary,
                "steps": len(vrows),
                "final_ee_to_cube": float(last["ee_to_cube"]),
                "min_finger_center_to_cube": min_finger,
                "final_finger_center_to_cube": float(last["finger_center_to_cube"]),
                "pre_close_local_step": int(pre_close["local_step"]),
                "pre_close_phase": str(pre_close["phase"]),
                "pre_close_ee_to_cube": float(pre_close["ee_to_cube"]),
                "pre_close_finger_center_to_cube": float(pre_close["finger_center_to_cube"]),
                "pre_close_left_finger_to_cube": float(pre_close["left_finger_to_cube"]),
                "pre_close_right_finger_to_cube": float(pre_close["right_finger_to_cube"]),
                "pre_close_finger_distance_balance_abs": float(pre_close["finger_distance_balance_abs"]),
                "pre_close_finger_cube_surface_margin_min": float(pre_close["finger_cube_surface_margin_min"]),
                "pre_close_left_finger_cube_surface_margin": float(pre_close["left_finger_cube_surface_margin"]),
                "pre_close_right_finger_cube_surface_margin": float(pre_close["right_finger_cube_surface_margin"]),
                "pre_close_finger_error_norm": float(pre_close["finger_error_norm"]),
                "pre_close_gripper_width": float(pre_close["gripper_width"]),
                "pre_close_target_reference": str(pre_close["target_reference"]),
                "pre_close_target_minus_cube_norm": float(pre_close["target_minus_cube_norm"]),
                "pre_close_target_offset": pre_close["target_offset"],
                "pre_close_lateral_centering_norm": float(pre_close["lateral_centering_norm"]),
                "pre_close_lateral_signed_error": float(pre_close["lateral_signed_error"]),
                "contact_align_success": contact_align_success,
                "contact_align_steps": int(args_cli.contact_align_steps),
                "contact_align_reference": str(args_cli.contact_align_reference),
                "close_hold_reference": str(args_cli.close_hold_reference),
                "contact_align_threshold": float(args_cli.contact_align_threshold),
                "contact_gate_mode": str(args_cli.contact_gate_mode),
                "require_contact_gate": bool(args_cli.require_contact_gate),
                "finger_gate_max_distance": float(args_cli.finger_gate_max_distance),
                "finger_gate_balance_threshold": float(args_cli.finger_gate_balance_threshold),
                "cube_size": cube_size,
                "close_gripper_width_target": close_gripper_width_target,
                "close_gripper_action_target": close_gripper_action_target,
                "min_finger_cube_surface_margin_threshold": float(args_cli.min_finger_cube_surface_margin),
                "contact_align_trigger_step": (
                    int(contact_align_trigger_step) if contact_align_trigger_step is not None else -1
                ),
                "close_start_local_step": (
                    int(close_start_step) if close_start_step is not None else -1
                ),
                "max_cube_lift_height": max_lift,
                "final_cube_lift_height": final_lift,
                "final_gripper_width": float(last["gripper_width"]),
                "min_finger_cube_surface_margin": min_surface_margin,
                "final_finger_cube_surface_margin_min": final_surface_margin,
                "surface_margin_ok": surface_margin_ok,
                "max_pose_action_clip_fraction": float(max(row["pose_action_clip_fraction"] for row in vrows)),
                "max_raw_pose_action_max_abs": float(max(row["raw_pose_action_max_abs"] for row in vrows)),
                "max_executed_pose_action_max_abs": float(
                    max(row["executed_pose_action_max_abs"] for row in vrows)
                ),
                "max_raw_pose_action_would_clip_fraction": float(
                    max(row["raw_pose_action_would_clip_fraction"] for row in vrows)
                ),
                "min_pose_action_filter_scale": float(min(row["pose_action_filter_scale"] for row in vrows)),
                "pose_action_filter": str(args_cli.pose_action_filter),
                "pose_action_limit": float(args_cli.pose_action_limit),
                "rgb_npz": rgb_npz,
                "terminated_next_step": bool(any(row.get("terminated_next_step", False) for row in vrows)),
                "truncated_next_step": bool(any(row.get("truncated_next_step", False) for row in vrows)),
                "skipped_post_reset_local_step": int(
                    max(
                        [row.get("skipped_post_reset_local_step", -1) for row in vrows],
                        default=-1,
                    )
                ),
                "success_like": success_like,
            }
    finally:
        gym_env.close()

    csv_path = output_dir / "contact_rollout_steps.csv"
    json_path = output_dir / "contact_rollout_summary.json"
    plot_path = output_dir / "contact_rollout_plot.png"
    report_path = output_dir / "contact_rollout_report.md"
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)
    any_success = any(payload["success_like"] for payload in summaries.values())
    verdict = (
        "At least one contact-aware rollout variant lifted the cube to the success threshold; inspect video before DP relabeling."
        if any_success
        else "No contact-aware rollout variant produced stable lift; controller-rollout relabeling needs more grasp/contact design before DP."
    )
    summary = {
        "dataset": str(dataset_path),
        "trajectory_json": str(trajectory_path),
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "episode": int(episode_idx),
        "episode_step": int(row_idx - episode_start),
        "align_steps": int(args_cli.align_steps),
        "contact_align_steps": int(args_cli.contact_align_steps),
        "contact_align_reference": str(args_cli.contact_align_reference),
        "close_hold_reference": str(args_cli.close_hold_reference),
        "contact_align_threshold": float(args_cli.contact_align_threshold),
        "contact_gate_mode": str(args_cli.contact_gate_mode),
        "require_contact_gate": bool(args_cli.require_contact_gate),
        "finger_gate_max_distance": float(args_cli.finger_gate_max_distance),
        "finger_gate_balance_threshold": float(args_cli.finger_gate_balance_threshold),
        "cube_size": cube_size,
        "close_gripper_width": float(args_cli.close_gripper_width),
        "close_gripper_width_offset": float(args_cli.close_gripper_width_offset),
        "close_gripper_width_target": close_gripper_width_target,
        "close_gripper_action_target": close_gripper_action_target,
        "min_finger_cube_surface_margin": float(args_cli.min_finger_cube_surface_margin),
        "lateral_centering_gain": float(args_cli.lateral_centering_gain),
        "lateral_centering_limit": float(args_cli.lateral_centering_limit),
        "lateral_search_amplitude": float(args_cli.lateral_search_amplitude),
        "lateral_search_period": int(args_cli.lateral_search_period),
        "close_steps": int(args_cli.close_steps),
        "lift_steps": int(args_cli.lift_steps),
        "lift_height": float(args_cli.lift_height),
        "finger_gain": float(args_cli.finger_gain),
        "clip_actions": float(args_cli.clip_actions),
        "pose_action_filter": str(args_cli.pose_action_filter),
        "pose_action_limit": float(args_cli.pose_action_limit),
        "orientation_mode": str(args_cli.orientation_mode),
        "reset_joint_blend_alpha": float(np.clip(float(args_cli.reset_joint_blend_alpha), 0.0, 1.0)),
        "reset_cube_pos_blend_alpha": float(np.clip(float(args_cli.reset_cube_pos_blend_alpha), 0.0, 1.0)),
        "reset_cube_xy": (
            np.asarray(args_cli.reset_cube_xy, dtype=np.float32).astype(float).tolist()
            if args_cli.reset_cube_xy is not None
            else None
        ),
        "reset_cube_z": None if args_cli.reset_cube_z is None else float(args_cli.reset_cube_z),
        "variants": summaries,
        "verdict": verdict,
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "report": str(report_path),
        "video_files": _latest_video_files(output_dir / "videos"),
        "save_rgb_obs": bool(args_cli.save_rgb_obs),
        "rgb_obs_shape": [int(args_cli.rgb_obs_height), int(args_cli.rgb_obs_width), 3],
    }
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_build_report(summary), encoding="utf-8")
    print(
        "FRANKA_CUBE_CONTACT_ROLLOUT_DONE "
        + json.dumps(
            {
                "output_dir": str(output_dir),
                "report": str(report_path),
                "summary_json": str(json_path),
                "verdict": verdict,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"FRANKA_CUBE_CONTACT_ROLLOUT_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
