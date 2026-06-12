"""Audit Franka cube reset-prior policy actions against scripted candidates."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--num_resets", type=int, default=3)
parser.add_argument("--horizon_steps", type=int, default=40)
parser.add_argument(
    "--match_reset_state",
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Restore the exact same reset state for each candidate. Default uses fresh resets from the same prior distribution.",
)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--grasp_prior_library_path", type=str, required=True)
parser.add_argument(
    "--checkpoint",
    action="append",
    default=[],
    help="Policy checkpoint as label=/container/path/to/model.pth. May be repeated.",
)
parser.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--render", action="store_true", default=False)
parser.add_argument("--render_resets", type=int, default=1)
parser.add_argument("--render_interval", type=int, default=10)
parser.add_argument("--render_candidates", type=str, default="policy_ep10,policy_ep45,script_assisted_oracle_short")
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument("--oracle_proportional_gain", type=float, default=1.0)
parser.add_argument("--oracle_max_position_action", type=float, default=1.0)
parser.add_argument("--oracle_track_orientation", action="store_true", default=True)
parser.add_argument("--close_width", type=float, default=0.055)
parser.add_argument("--lift_action_z", type=float, default=0.15)
parser.add_argument("--assisted_approach_steps", type=int, default=20)
parser.add_argument("--assisted_close_steps", type=int, default=10)
parser.add_argument("--print_interval", type=int, default=10)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

if args_cli.render:
    args_cli.enable_cameras = True

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch
from PIL import Image, ImageDraw

from rl_games.common import env_configurations, vecenv
from rl_games.common.player import BasePlayer
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils import math as math_utils
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import isaaclab_tasks  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401


class DextrahAuditRlGamesVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_env_state(self):
        if hasattr(self.unwrapped, "get_env_state"):
            return self.unwrapped.get_env_state()
        return None

    def set_env_state(self, env_state):
        if hasattr(self.unwrapped, "set_env_state"):
            self.unwrapped.set_env_state(env_state)

    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


class DextrahAuditRlGamesGpuEnv(RlGamesGpuEnv):
    def get_env_state(self):
        if hasattr(self.env, "get_env_state"):
            return self.env.get_env_state()
        return None

    def set_env_state(self, env_state):
        if hasattr(self.env, "set_env_state"):
            self.env.set_env_state(env_state)

    def get_current_obs(self):
        if hasattr(self.env, "get_current_obs"):
            return self.env.get_current_obs()
        raise AttributeError("Wrapped environment does not expose get_current_obs")


def _as_float(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _maybe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return _as_float(value)
    except (TypeError, ValueError):
        return None


def _tensor_list(value: torch.Tensor | np.ndarray | list[float] | tuple[float, ...]) -> list[float]:
    if isinstance(value, torch.Tensor):
        flat = value.detach().float().cpu().flatten().tolist()
    elif isinstance(value, np.ndarray):
        flat = value.astype(float).flatten().tolist()
    else:
        flat = [float(v) for v in value]
    return [float(v) for v in flat]


def _mean_attr(task_env, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    return _maybe_float(getattr(task_env, name))


def _reward_log_terms(task_env) -> dict[str, float]:
    terms: dict[str, float] = {}
    extras = getattr(task_env, "extras", {})
    if not isinstance(extras, dict):
        return terms
    log_terms = extras.get("log", {})
    if isinstance(log_terms, dict):
        for key, value in log_terms.items():
            scalar = _maybe_float(value)
            if scalar is not None:
                terms[f"reward_term_{key}"] = scalar
    for key, value in extras.items():
        if key == "log":
            continue
        scalar = _maybe_float(value)
        if scalar is not None:
            terms[f"extra_{key}"] = scalar
    return terms


def _quat_identity(device: str) -> torch.Tensor:
    return torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=device)


def _pos_in_root(task_env, env_id: int, pos_w: torch.Tensor) -> torch.Tensor:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    pos_b, _ = math_utils.subtract_frame_transforms(
        root_pos_w,
        root_quat_w,
        pos_w.unsqueeze(0),
        _quat_identity(task_env.device),
    )
    return pos_b[0]


def _actual_tip_geometry(task_env, env_id: int) -> dict[str, object]:
    env_ids = torch.tensor([env_id], device=task_env.device, dtype=torch.long)
    task_env._compute_intermediate_values(env_ids, update_success_timer=False)
    env_origin = task_env.scene.env_origins[env_id]
    cube_env = task_env.cube_pos[env_id]
    cube_w = cube_env + env_origin
    left_env = task_env.left_finger_pos[env_id]
    right_env = task_env.right_finger_pos[env_id]
    actual_ee_env = task_env.ee_pos[env_id]
    gripper_center_env = 0.5 * (left_env + right_env)
    gripper_half_axis = 0.5 * (left_env - right_env)
    left_tip_env = actual_ee_env + gripper_half_axis
    right_tip_env = actual_ee_env - gripper_half_axis
    tip_center_env = 0.5 * (left_tip_env + right_tip_env)
    left_tip_dist = torch.norm(left_tip_env - cube_env)
    right_tip_dist = torch.norm(right_tip_env - cube_env)
    tip_center_dist = torch.norm(tip_center_env - cube_env)
    tip_max_dist = torch.maximum(left_tip_dist, right_tip_dist)
    tip_table_clearance = torch.minimum(left_tip_env[2], right_tip_env[2]) - float(task_env.cfg.table_surface_z)
    return {
        "cube_pos_env": _tensor_list(cube_env),
        "cube_pos_w": _tensor_list(cube_w),
        "actual_ee_pos_env": _tensor_list(actual_ee_env),
        "actual_ee_pos_w": _tensor_list(actual_ee_env + env_origin),
        "left_finger_pos_env": _tensor_list(left_env),
        "right_finger_pos_env": _tensor_list(right_env),
        "gripper_center_pos_env": _tensor_list(gripper_center_env),
        "actual_left_tip_proxy_pos_env": _tensor_list(left_tip_env),
        "actual_right_tip_proxy_pos_env": _tensor_list(right_tip_env),
        "actual_tip_center_pos_env": _tensor_list(tip_center_env),
        "relative_to_cube_env": {
            "left_finger": _tensor_list(left_env - cube_env),
            "right_finger": _tensor_list(right_env - cube_env),
            "gripper_center": _tensor_list(gripper_center_env - cube_env),
            "actual_ee": _tensor_list(actual_ee_env - cube_env),
            "actual_left_tip_proxy": _tensor_list(left_tip_env - cube_env),
            "actual_right_tip_proxy": _tensor_list(right_tip_env - cube_env),
            "actual_tip_center": _tensor_list(tip_center_env - cube_env),
        },
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "actual_tip_center_to_cube_dist_m": _as_float(tip_center_dist),
        "actual_tip_max_to_cube_dist_m": _as_float(tip_max_dist),
        "actual_left_tip_proxy_to_cube_dist_m": _as_float(left_tip_dist),
        "actual_right_tip_proxy_to_cube_dist_m": _as_float(right_tip_dist),
        "actual_tip_table_clearance_m": _as_float(tip_table_clearance),
    }


def _collect_reset_sample(task_env, env_id: int, reset_index: int) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    exact_ee_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    target_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    cube_env = task_env.cube_pos[env_id]
    actual_ee_env = task_env.ee_pos[env_id]
    left_env = task_env.left_finger_pos[env_id]
    right_env = task_env.right_finger_pos[env_id]
    gripper_center_env = 0.5 * (left_env + right_env)
    term, trunc = task_env._get_dones()
    immediate_done = bool((term[env_id] | trunc[env_id]).detach().cpu())
    sample_index = int(task_env.grasp_prior_reset_sample_index[env_id].detach().cpu())
    return {
        "reset_index": int(reset_index),
        "env_id": int(env_id),
        "sample_index": sample_index,
        "reset_attempted": bool(task_env.grasp_prior_reset_attempted[env_id].detach().cpu()),
        "reset_success": bool(task_env.grasp_prior_reset_success[env_id].detach().cpu()),
        "reset_farther": bool(task_env.grasp_prior_reset_farther[env_id].detach().cpu()),
        "reset_grasp_quality_success": bool(task_env.grasp_prior_reset_quality_success[env_id].detach().cpu()),
        "immediate_done": immediate_done,
        "immediate_terminated": bool(term[env_id].detach().cpu()),
        "immediate_truncated": bool(trunc[env_id].detach().cpu()),
        "cube_size_m": float(task_env.cfg.cube_size),
        "cube_pos_env": _tensor_list(cube_env),
        "cube_pos_w": _tensor_list(cube_w),
        "cube_pos_root": _tensor_list(_pos_in_root(task_env, env_id, cube_w)),
        "cube_quat_w_wxyz": _tensor_list(task_env.cube_quat[env_id]),
        "exact_tool_pos_env": _tensor_list(exact_w - env_origin),
        "exact_tool_pos_w": _tensor_list(exact_w),
        "pregrasp_tool_pos_env": _tensor_list(pregrasp_w - env_origin),
        "pregrasp_tool_pos_w": _tensor_list(pregrasp_w),
        "exact_ee_pos_env": _tensor_list(exact_ee_w - env_origin),
        "exact_ee_pos_w": _tensor_list(exact_ee_w),
        "target_ee_pos_env": _tensor_list(target_ee_w - env_origin),
        "target_ee_pos_w": _tensor_list(target_ee_w),
        "actual_ee_pos_env": _tensor_list(actual_ee_env),
        "left_finger_pos_env": _tensor_list(left_env),
        "right_finger_pos_env": _tensor_list(right_env),
        "gripper_center_pos_env": _tensor_list(gripper_center_env),
        "pregrasp_offset_dir_w": _tensor_list(task_env.grasp_prior_reset_offset_dir_w[env_id]),
        "pregrasp_offset_m": _as_float(torch.norm(pregrasp_w - exact_w)),
        "offset_radial_dot": _as_float(task_env.grasp_prior_reset_offset_radial_dot[env_id]),
        "reset_pos_error_m": _as_float(task_env.grasp_prior_reset_pos_error[env_id]),
        "reset_rot_error_rad": _as_float(task_env.grasp_prior_reset_rot_error[env_id]),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "open_width_margin_m": _as_float(task_env.grasp_prior_reset_open_width_margin[env_id]),
        "ee_to_cube_dist_m": _as_float(task_env.ee_to_cube_dist[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "projected_exact_tip_center_dist_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_tip_center_dist[env_id]
        ),
        "projected_exact_tip_max_dist_m": _as_float(task_env.grasp_prior_reset_projected_exact_tip_max_dist[env_id]),
        "pregrasp_tip_table_clearance_m": _as_float(task_env.grasp_prior_reset_pregrasp_tip_table_clearance[env_id]),
        "projected_exact_tip_table_clearance_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_tip_table_clearance[env_id]
        ),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
    }


def _snapshot_tensor(value):
    if isinstance(value, torch.Tensor):
        return value.detach().clone()
    return value


def _snapshot_task_tensor_names() -> tuple[str, ...]:
    return (
        "episode_length_buf",
        "reset_buf",
        "actions",
        "robot_dof_targets",
        "arm_joint_pos_target",
        "finger_joint_pos_target",
        "cube_initial_pos",
        "cube_goal_pos",
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "in_success_region",
        "time_in_success_region",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "left_finger_to_cube_dist",
        "right_finger_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_distance_asymmetry",
        "hand_to_cube_mean_dist",
        "hand_to_cube_max_dist",
        "gripper_width",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "cube_pos",
        "cube_quat",
        "cube_vel",
        "ee_pos",
        "ee_quat",
        "left_finger_pos",
        "right_finger_pos",
        "grasp_prior_reset_attempted",
        "grasp_prior_reset_success",
        "grasp_prior_reset_farther",
        "grasp_prior_reset_sample_index",
        "grasp_prior_reset_pos_error",
        "grasp_prior_reset_rot_error",
        "grasp_prior_reset_exact_tool_dist",
        "grasp_prior_reset_pregrasp_tool_dist",
        "grasp_prior_reset_finger_center_dist",
        "grasp_prior_reset_finger_table_clearance",
        "grasp_prior_reset_cube_pos_w",
        "grasp_prior_reset_exact_tool_pos_w",
        "grasp_prior_reset_pregrasp_tool_pos_w",
        "grasp_prior_reset_exact_ee_pos_w",
        "grasp_prior_reset_target_ee_pos_w",
        "grasp_prior_reset_offset_dir_w",
        "grasp_prior_reset_exact_tool_quat_w",
        "grasp_prior_reset_pregrasp_tool_quat_w",
        "grasp_prior_reset_exact_ee_quat_w",
        "grasp_prior_reset_target_ee_quat_w",
        "grasp_prior_reset_left_finger_pos",
        "grasp_prior_reset_right_finger_pos",
        "grasp_prior_reset_left_tip_proxy_pos",
        "grasp_prior_reset_right_tip_proxy_pos",
        "grasp_prior_reset_projected_exact_left_tip_proxy_pos",
        "grasp_prior_reset_projected_exact_right_tip_proxy_pos",
        "grasp_prior_reset_gripper_width",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_offset_radial_dot",
        "grasp_prior_reset_offset_radial_angle",
        "grasp_prior_reset_exact_ee_dist",
        "grasp_prior_reset_pregrasp_ee_dist",
        "grasp_prior_reset_projected_exact_finger_center_dist",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_pregrasp_tip_table_clearance",
        "grasp_prior_reset_projected_exact_tip_table_clearance",
        "grasp_prior_reset_quality_success",
    )


def _root_state_w(asset) -> torch.Tensor:
    return torch.cat((asset.data.root_pos_w, asset.data.root_quat_w, asset.data.root_vel_w), dim=-1)


def _snapshot_task_env_state(task_env) -> dict[str, object]:
    task_tensors = {}
    for name in _snapshot_task_tensor_names():
        if hasattr(task_env, name):
            task_tensors[name] = _snapshot_tensor(getattr(task_env, name))
    return {
        "version": 1,
        "num_envs": task_env.num_envs,
        "common_step_counter": int(getattr(task_env, "common_step_counter", 0)),
        "sim_step_counter": int(getattr(task_env, "_sim_step_counter", 0)),
        "task_tensors": task_tensors,
        "sim": {
            "robot_root_state": _snapshot_tensor(_root_state_w(task_env._robot)),
            "robot_joint_pos": _snapshot_tensor(task_env._robot.data.joint_pos),
            "robot_joint_vel": _snapshot_tensor(task_env._robot.data.joint_vel),
            "table_root_state": _snapshot_tensor(_root_state_w(task_env._table)),
            "cube_root_state": _snapshot_tensor(_root_state_w(task_env._cube)),
        },
    }


def _restore_task_env_state(task_env, env_state: dict[str, object]) -> None:
    if int(env_state.get("num_envs", task_env.num_envs)) != task_env.num_envs:
        raise ValueError(
            f"Cannot restore env state with num_envs={env_state.get('num_envs')} into num_envs={task_env.num_envs}"
        )
    task_env.common_step_counter = int(
        env_state.get("common_step_counter", getattr(task_env, "common_step_counter", 0))
    )
    if hasattr(task_env, "_sim_step_counter"):
        task_env._sim_step_counter = int(env_state.get("sim_step_counter", task_env._sim_step_counter))

    for name, value in env_state.get("task_tensors", {}).items():
        if isinstance(value, torch.Tensor):
            setattr(task_env, name, value.to(task_env.device).clone())

    sim_state = env_state.get("sim", {})
    if "robot_root_state" in sim_state:
        task_env._robot.write_root_state_to_sim(sim_state["robot_root_state"].to(task_env.device))
    if "robot_joint_pos" in sim_state and "robot_joint_vel" in sim_state:
        task_env._robot.write_joint_state_to_sim(
            sim_state["robot_joint_pos"].to(task_env.device),
            sim_state["robot_joint_vel"].to(task_env.device),
        )
    if "table_root_state" in sim_state:
        task_env._table.write_root_state_to_sim(sim_state["table_root_state"].to(task_env.device))
    if "cube_root_state" in sim_state:
        task_env._cube.write_root_state_to_sim(sim_state["cube_root_state"].to(task_env.device))

    task_env._robot.set_joint_position_target(task_env.arm_joint_pos_target, joint_ids=task_env.arm_joint_ids)
    task_env._robot.set_joint_position_target(task_env.finger_joint_pos_target, joint_ids=task_env.finger_joint_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(update_success_timer=False)


def _gripper_action_for_width(width: float, max_width: float) -> float:
    if max_width <= 1.0e-6:
        return -1.0
    return float(np.clip(2.0 * float(width) / float(max_width) - 1.0, -1.0, 1.0))


def _ee_pose_b(task_env, env_id: int) -> tuple[torch.Tensor, torch.Tensor]:
    ee_pos_b, ee_quat_b = task_env._compute_ee_frame_pose()
    return ee_pos_b[env_id], ee_quat_b[env_id]


def _ee_pose_w_from_b(
    task_env,
    env_id: int,
    ee_pos_b: torch.Tensor,
    ee_quat_b: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    ee_pos_w, ee_quat_w = math_utils.combine_frame_transforms(
        root_pos_w,
        root_quat_w,
        ee_pos_b.unsqueeze(0),
        ee_quat_b.unsqueeze(0),
    )
    return ee_pos_w[0], ee_quat_w[0]


def _exact_ee_pose_b(task_env, env_id: int) -> tuple[torch.Tensor, torch.Tensor]:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    exact_ee_pos_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id].unsqueeze(0)
    exact_ee_quat_w = task_env.grasp_prior_reset_exact_ee_quat_w[env_id].unsqueeze(0)
    exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
        root_pos_w,
        root_quat_w,
        exact_ee_pos_w,
        exact_ee_quat_w,
    )
    return exact_ee_pos_b[0], exact_ee_quat_b[0]


def _bounded_exact_tracking_action(task_env, env_id: int, *, gripper_action: float) -> torch.Tensor:
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    current_ee_pos_b, current_ee_quat_b = _ee_pose_b(task_env, env_id)
    exact_ee_pos_b, exact_ee_quat_b = _exact_ee_pose_b(task_env, env_id)
    pos_error_b = exact_ee_pos_b - current_ee_pos_b
    pos_action = float(args_cli.oracle_proportional_gain) * pos_error_b / torch.clamp(
        task_env.action_scale[:3], min=1.0e-6
    )
    max_position_action = max(float(args_cli.oracle_max_position_action), 0.0)
    action[env_id, 0:3] = torch.clamp(pos_action, min=-max_position_action, max=max_position_action)
    if bool(args_cli.oracle_track_orientation):
        _, rot_error_b = math_utils.compute_pose_error(
            current_ee_pos_b.unsqueeze(0),
            current_ee_quat_b.unsqueeze(0),
            exact_ee_pos_b.unsqueeze(0),
            exact_ee_quat_b.unsqueeze(0),
            rot_error_type="axis_angle",
        )
        rot_action = float(args_cli.oracle_proportional_gain) * rot_error_b[0] / torch.clamp(
            task_env.action_scale[3:6], min=1.0e-6
        )
        action[env_id, 3:6] = torch.clamp(rot_action, min=-1.0, max=1.0)
    action[:, 6] = gripper_action
    return action


def _action_tracking_before_step(task_env, env_id: int, action: torch.Tensor) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    pre_ee_pos_b, pre_ee_quat_b = _ee_pose_b(task_env, env_id)
    pre_ee_pos_w, pre_ee_quat_w = _ee_pose_w_from_b(task_env, env_id, pre_ee_pos_b, pre_ee_quat_b)
    action_env = action[env_id].detach()
    command_delta_b = action_env[:6] * task_env.action_scale
    target_ee_pos_b, target_ee_quat_b = math_utils.apply_delta_pose(
        pre_ee_pos_b.unsqueeze(0),
        pre_ee_quat_b.unsqueeze(0),
        command_delta_b.unsqueeze(0),
    )
    target_ee_pos_w, target_ee_quat_w = _ee_pose_w_from_b(task_env, env_id, target_ee_pos_b[0], target_ee_quat_b[0])
    exact_ee_pos_b, exact_ee_quat_b = _exact_ee_pose_b(task_env, env_id)
    return {
        "pre_ee_pos_b": pre_ee_pos_b.detach().clone(),
        "pre_ee_quat_b": pre_ee_quat_b.detach().clone(),
        "pre_ee_pos_w": pre_ee_pos_w.detach().clone(),
        "pre_ee_quat_w": pre_ee_quat_w.detach().clone(),
        "command_delta_b": command_delta_b.detach().clone(),
        "command_target_ee_pos_b": target_ee_pos_b[0].detach().clone(),
        "command_target_ee_quat_b": target_ee_quat_b[0].detach().clone(),
        "command_target_ee_pos_w": target_ee_pos_w.detach().clone(),
        "command_target_ee_quat_w": target_ee_quat_w.detach().clone(),
        "exact_ee_pos_b": exact_ee_pos_b.detach().clone(),
        "exact_ee_quat_b": exact_ee_quat_b.detach().clone(),
        "exact_ee_pos_w": task_env.grasp_prior_reset_exact_ee_pos_w[env_id].detach().clone(),
        "pregrasp_ee_pos_w": task_env.grasp_prior_reset_target_ee_pos_w[env_id].detach().clone(),
    }


def _finalize_action_tracking(task_env, env_id: int, before: dict[str, object]) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    post_ee_pos_b, post_ee_quat_b = _ee_pose_b(task_env, env_id)
    post_ee_pos_w, post_ee_quat_w = _ee_pose_w_from_b(task_env, env_id, post_ee_pos_b, post_ee_quat_b)
    controller_pos_des_b = task_env.ik_controller.ee_pos_des[env_id].detach().clone()
    controller_quat_des_b = task_env.ik_controller.ee_quat_des[env_id].detach().clone()
    controller_pos_des_w, controller_quat_des_w = _ee_pose_w_from_b(
        task_env,
        env_id,
        controller_pos_des_b,
        controller_quat_des_b,
    )
    _, post_to_exact_rot_b = math_utils.compute_pose_error(
        post_ee_pos_b.unsqueeze(0),
        post_ee_quat_b.unsqueeze(0),
        before["exact_ee_pos_b"].unsqueeze(0),
        before["exact_ee_quat_b"].unsqueeze(0),
        rot_error_type="axis_angle",
    )
    commanded = torch.norm(before["command_delta_b"][:3])
    realized = torch.norm(post_ee_pos_b - before["pre_ee_pos_b"])
    return {
        "tracking_pre_ee_pos_env": _tensor_list(before["pre_ee_pos_w"] - task_env.scene.env_origins[env_id]),
        "tracking_post_ee_pos_env": _tensor_list(post_ee_pos_w - task_env.scene.env_origins[env_id]),
        "tracking_command_delta_b": _tensor_list(before["command_delta_b"]),
        "tracking_command_target_ee_pos_env": _tensor_list(
            before["command_target_ee_pos_w"] - task_env.scene.env_origins[env_id]
        ),
        "tracking_controller_target_ee_pos_env": _tensor_list(controller_pos_des_w - task_env.scene.env_origins[env_id]),
        "tracking_commanded_delta_norm_m": _as_float(commanded),
        "tracking_realized_delta_norm_m": _as_float(realized),
        "tracking_realized_over_commanded": _as_float(realized / torch.clamp(commanded, min=1.0e-6)),
        "tracking_post_to_command_target_dist_m": _as_float(
            torch.norm(post_ee_pos_w - before["command_target_ee_pos_w"])
        ),
        "tracking_controller_to_command_target_dist_m": _as_float(
            torch.norm(controller_pos_des_w - before["command_target_ee_pos_w"])
        ),
        "tracking_post_to_exact_ee_dist_m": _as_float(torch.norm(post_ee_pos_w - before["exact_ee_pos_w"])),
        "tracking_post_to_exact_rot_error_rad": _as_float(torch.norm(post_to_exact_rot_b[0])),
        "tracking_controller_to_exact_ee_dist_m": _as_float(torch.norm(controller_pos_des_w - before["exact_ee_pos_w"])),
    }


def _contact_metrics(task_env, env_id: int) -> dict[str, object]:
    metrics: dict[str, object] = {"contact_available": False, "contact_flag": None}
    for asset_name in ("_cube", "_robot"):
        asset = getattr(task_env, asset_name, None)
        data = getattr(asset, "data", None)
        if data is None:
            continue
        label = asset_name.lstrip("_")
        for attr in ("net_contact_forces_w", "body_contact_forces_w", "contact_forces_w"):
            value = getattr(data, attr, None)
            if not isinstance(value, torch.Tensor):
                continue
            metrics["contact_available"] = True
            env_value = value[env_id] if value.ndim > 0 and value.shape[0] == task_env.num_envs else value
            force_norm = float(torch.norm(env_value.detach().float()).cpu())
            metrics[f"{label}_{attr}_norm"] = force_norm
            metrics["contact_flag"] = bool(metrics["contact_flag"]) or force_norm > 1.0e-3
    return metrics


def _action_metrics(action: torch.Tensor, env_id: int) -> dict[str, float]:
    values = action[env_id].detach().float().cpu().tolist()
    return {
        "action_x": float(values[0]),
        "action_y": float(values[1]),
        "action_z": float(values[2]),
        "action_roll": float(values[3]),
        "action_pitch": float(values[4]),
        "action_yaw": float(values[5]),
        "action_gripper": float(values[6]),
        "action_abs_mean": float(torch.mean(action.detach().float().abs()).cpu()),
        "action_max_abs": float(torch.max(action.detach().float().abs()).cpu()),
    }


def _step_record(
    task_env,
    env_id: int,
    *,
    reset_index: int,
    candidate: str,
    step: int,
    phase: str,
    action: torch.Tensor,
    reward,
    terminated,
    truncated,
    tracking_before: dict[str, object],
) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    geometry = _actual_tip_geometry(task_env, env_id)
    env_origin = task_env.scene.env_origins[env_id]
    exact_ee_env = task_env.grasp_prior_reset_exact_ee_pos_w[env_id] - env_origin
    pregrasp_ee_env = task_env.grasp_prior_reset_target_ee_pos_w[env_id] - env_origin
    actual_ee_env = task_env.ee_pos[env_id]
    if isinstance(reward, torch.Tensor):
        reward_value = _as_float(reward)
    else:
        reward_value = float(reward)
    if isinstance(terminated, torch.Tensor):
        terminated_flag = bool(terminated[env_id].detach().cpu())
    else:
        terminated_flag = bool(terminated)
    if isinstance(truncated, torch.Tensor):
        truncated_flag = bool(truncated[env_id].detach().cpu())
    else:
        truncated_flag = bool(truncated)
    record: dict[str, object] = {
        "reset_index": int(reset_index),
        "candidate": candidate,
        "step": int(step),
        "phase": phase,
        "sample_index": int(task_env.grasp_prior_reset_sample_index[env_id].detach().cpu()),
        "reward": reward_value,
        "terminated": terminated_flag,
        "truncated": truncated_flag,
        "done": bool(terminated_flag or truncated_flag),
        "success_rate": _as_float(task_env.in_success_region[env_id]),
        "has_lifted_cube": _as_float(task_env.has_lifted_cube[env_id]),
        "cube_lift_height_m": _as_float(task_env.cube_lift_height[env_id]),
        "cube_xy_error_m": _as_float(task_env.cube_xy_error[env_id]),
        "cube_goal_height_error_m": _as_float(task_env.cube_goal_height_error[env_id]),
        "ee_to_cube_dist_m": _as_float(task_env.ee_to_cube_dist[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "max_finger_to_cube_dist_m": _as_float(task_env.max_finger_to_cube_dist[env_id]),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "actual_ee_to_exact_ee_dist_m": _as_float(torch.norm(actual_ee_env - exact_ee_env)),
        "actual_ee_to_pregrasp_ee_dist_m": _as_float(torch.norm(actual_ee_env - pregrasp_ee_env)),
        "actual_ee_minus_exact_ee_env": _tensor_list(actual_ee_env - exact_ee_env),
        "actual_ee_minus_pregrasp_ee_env": _tensor_list(actual_ee_env - pregrasp_ee_env),
        "cube_pos_env": geometry["cube_pos_env"],
        "actual_tip_center_pos_env": geometry["actual_tip_center_pos_env"],
        "relative_to_cube_env": geometry["relative_to_cube_env"],
        "grasp_prior_reset_success": _as_float(task_env.grasp_prior_reset_success[env_id]),
        "grasp_prior_reset_quality_success": _as_float(task_env.grasp_prior_reset_quality_success[env_id]),
        **_action_metrics(action, env_id),
        **_contact_metrics(task_env, env_id),
        **_reward_log_terms(task_env),
        **_finalize_action_tracking(task_env, env_id, tracking_before),
    }
    for key in (
        "actual_tip_center_to_cube_dist_m",
        "actual_tip_max_to_cube_dist_m",
        "actual_left_tip_proxy_to_cube_dist_m",
        "actual_right_tip_proxy_to_cube_dist_m",
        "actual_tip_table_clearance_m",
    ):
        record[key] = geometry[key]
    return record


def _parse_checkpoints(values: list[str]) -> dict[str, str]:
    checkpoints: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected checkpoint as label=path, got {item!r}")
        label, path = item.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"Empty checkpoint label in {item!r}")
        checkpoints[f"policy_{label}"] = retrieve_file_path(path.strip())
    return checkpoints


def _create_player(agent_cfg: dict, env, label: str, checkpoint_path: str) -> BasePlayer:
    cfg = copy.deepcopy(agent_cfg)
    cfg["params"]["load_checkpoint"] = True
    cfg["params"]["load_path"] = checkpoint_path
    cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    print(f"[INFO] Loading {label}: {checkpoint_path}", flush=True)
    runner = Runner()
    runner.load(cfg)
    agent: BasePlayer = runner.create_player()
    agent.restore(checkpoint_path)
    agent.reset()
    return agent


def _obs_policy_tensor(obs):
    if isinstance(obs, tuple):
        obs = obs[0]
    if isinstance(obs, dict):
        obs = obs["obs"]
    return obs


def _scripted_action(task_env, env_id: int, candidate: str, step: int) -> tuple[torch.Tensor, str]:
    open_action = _gripper_action_for_width(float(task_env.cfg.max_gripper_width), float(task_env.cfg.max_gripper_width))
    close_action = _gripper_action_for_width(float(args_cli.close_width), float(task_env.cfg.max_gripper_width))
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    if candidate == "script_noop":
        return action, "noop"
    if candidate == "script_hold_open":
        action[:, 6] = open_action
        return action, "hold_open"
    if candidate == "script_approach_exact_open":
        return _bounded_exact_tracking_action(task_env, env_id, gripper_action=open_action), "approach_exact_open"
    if candidate == "script_close_light_pregrasp":
        action[:, 6] = close_action
        return action, "close_light_pregrasp"
    if candidate == "script_lift_closed":
        action[:, 2] = float(np.clip(args_cli.lift_action_z, -1.0, 1.0))
        action[:, 6] = close_action
        return action, "lift_closed"
    if candidate == "script_assisted_oracle_short":
        approach_steps = max(int(args_cli.assisted_approach_steps), 0)
        close_steps = max(int(args_cli.assisted_close_steps), 0)
        if step <= approach_steps:
            return _bounded_exact_tracking_action(task_env, env_id, gripper_action=open_action), "assisted_approach"
        if step <= approach_steps + close_steps:
            return _bounded_exact_tracking_action(task_env, env_id, gripper_action=close_action), "assisted_close"
        action[:, 2] = float(np.clip(args_cli.lift_action_z, -1.0, 1.0))
        action[:, 6] = close_action
        return action, "assisted_lift"
    raise ValueError(f"Unknown scripted candidate {candidate!r}")


def _render_rgb(gym_env, task_env):
    for _ in range(4):
        task_env.sim.render()
    frame = gym_env.render()
    if isinstance(frame, list):
        frame = frame[0] if frame else None
    if frame is None:
        raise RuntimeError("gym_env.render() returned None")
    return np.asarray(frame)


def _set_camera(task_env, env_cfg, env_id: int) -> None:
    env_origin = task_env.scene.env_origins[env_id].detach().cpu().tolist()
    eye = tuple(float(args_cli.camera_eye[idx]) + float(env_origin[idx]) for idx in range(3))
    target = tuple(float(args_cli.camera_target[idx]) + float(env_origin[idx]) for idx in range(3))
    if hasattr(env_cfg, "viewer"):
        env_cfg.viewer.eye = eye
        env_cfg.viewer.lookat = target
        env_cfg.viewer.origin_type = "world"
    try:
        task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
    except Exception as exc:
        print(f"[WARN] Could not set audit camera: {exc}", flush=True)


def _fmt_vec(values) -> str:
    return "[" + ", ".join(f"{float(v):+.3f}" for v in values) + "]"


def _overlay_frame(frame: np.ndarray, title: str, lines: list[str]) -> Image.Image:
    image = Image.fromarray(frame[..., :3].astype(np.uint8))
    draw = ImageDraw.Draw(image)
    margin = 10
    line_h = 16
    width = min(image.width - 2 * margin, 860)
    height = margin * 2 + line_h * (len(lines) + 2)
    draw.rectangle((margin, margin, margin + width, margin + height), fill=(0, 0, 0))
    draw.text((margin + 8, margin + 5), title, fill=(255, 255, 255))
    y = margin + 5 + line_h * 2
    for line in lines:
        draw.text((margin + 8, y), line, fill=(235, 235, 235))
        y += line_h
    return image


def _render_frame(
    gym_env,
    task_env,
    env_cfg,
    *,
    env_id: int,
    reset_index: int,
    candidate: str,
    step: int,
    phase: str,
    sample: dict[str, object],
    record: dict[str, object] | None,
    frames_dir: Path,
    rendered_frames: list[Path],
) -> None:
    _set_camera(task_env, env_cfg, env_id)
    frame = _render_rgb(gym_env, task_env)
    if record is None:
        lines = [
            "reset/pregrasp state before candidate action",
            f"sample={sample['sample_index']} reset_success={sample['reset_success']} quality={sample['reset_grasp_quality_success']}",
            f"cube={_fmt_vec(sample['cube_pos_env'])} exact_ee={_fmt_vec(sample['exact_ee_pos_env'])}",
            f"target/pregrasp_ee={_fmt_vec(sample['target_ee_pos_env'])} actual_ee={_fmt_vec(sample['actual_ee_pos_env'])}",
            f"ee_dist={sample['ee_to_cube_dist_m']:.4f} finger_dist={sample['finger_center_to_cube_dist_m']:.4f} width={sample['gripper_width_m']:.4f}",
            f"offset_len={sample['pregrasp_offset_m']:.4f} offset_dot={sample['offset_radial_dot']:.4f}",
        ]
    else:
        rel = record.get("relative_to_cube_env", {})
        lines = [
            f"phase={phase} sample={record['sample_index']} reward={record['reward']:.4f} done={record['done']}",
            f"action xyz=({record['action_x']:+.2f},{record['action_y']:+.2f},{record['action_z']:+.2f}) grip={record['action_gripper']:+.2f}",
            f"cube={_fmt_vec(record['cube_pos_env'])} lift={record['cube_lift_height_m']:.4f} xy={record['cube_xy_error_m']:.4f}",
            f"ee_dist={record['ee_to_cube_dist_m']:.4f} finger={record['finger_center_to_cube_dist_m']:.4f} tip={record['actual_tip_center_to_cube_dist_m']:.4f}",
            f"width={record['gripper_width_m']:.4f} table={record['finger_table_clearance_m']:.4f} contact={record.get('contact_flag')}",
            f"EE-to-exact={record['actual_ee_to_exact_ee_dist_m']:.4f} ctrl-to-exact={record['tracking_controller_to_exact_ee_dist_m']:.4f}",
            f"realized_delta={record['tracking_realized_delta_norm_m']:.4f} commanded={record['tracking_commanded_delta_norm_m']:.4f}",
            f"tip_rel={_fmt_vec(rel.get('actual_tip_center', [0, 0, 0]))}",
        ]
    title = f"Franka cube pass7 action audit | reset {reset_index} | {candidate} | step {step}"
    image = _overlay_frame(frame, title, lines)
    frame_path = frames_dir / f"reset_{reset_index:03d}_{candidate}_step_{step:03d}_{phase}.png"
    image.save(frame_path)
    rendered_frames.append(frame_path)


def _json_safe(value):
    if isinstance(value, torch.Tensor):
        return _tensor_list(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _csv_value(value):
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True)
    return value


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    for key in ("reset_index", "candidate", "step", "phase"):
        if key in fieldnames:
            fieldnames.remove(key)
            fieldnames.insert(0, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_json_safe(row), sort_keys=True) + "\n")


def _summarize_rollout(records: list[dict[str, object]], sample: dict[str, object], candidate: str) -> dict[str, object]:
    summary: dict[str, object] = {
        "reset_index": sample["reset_index"],
        "candidate": candidate,
        "sample_index": sample["sample_index"],
        "reset_success": sample["reset_success"],
        "reset_quality_success": sample["reset_grasp_quality_success"],
        "initial_ee_to_cube_dist_m": sample["ee_to_cube_dist_m"],
        "initial_finger_center_to_cube_dist_m": sample["finger_center_to_cube_dist_m"],
        "initial_gripper_width_m": sample["gripper_width_m"],
        "initial_projected_exact_tip_center_dist_m": sample["projected_exact_tip_center_dist_m"],
    }
    if not records:
        summary["steps_completed"] = 0
        return summary
    numeric_keys = [
        "reward",
        "cube_lift_height_m",
        "ee_to_cube_dist_m",
        "finger_center_to_cube_dist_m",
        "actual_tip_center_to_cube_dist_m",
        "actual_tip_max_to_cube_dist_m",
        "gripper_width_m",
        "actual_ee_to_exact_ee_dist_m",
        "tracking_post_to_exact_ee_dist_m",
        "action_x",
        "action_y",
        "action_z",
        "action_gripper",
    ]
    summary.update(
        {
            "steps_completed": len(records),
            "done_seen": any(bool(row["done"]) for row in records),
            "terminated_seen": any(bool(row["terminated"]) for row in records),
            "truncated_seen": any(bool(row["truncated"]) for row in records),
            "success_max": max(float(row["success_rate"]) for row in records),
            "lifted_max": max(float(row["has_lifted_cube"]) for row in records),
        }
    )
    for key in numeric_keys:
        values = [float(row[key]) for row in records if row.get(key) is not None]
        if not values:
            continue
        summary[f"{key}_first"] = values[0]
        summary[f"{key}_final"] = values[-1]
        summary[f"{key}_min"] = min(values)
        summary[f"{key}_max"] = max(values)
        summary[f"{key}_mean"] = float(np.mean(values))
        summary[f"{key}_delta_final_minus_first"] = values[-1] - values[0]
    reward_term_keys = sorted(key for key in records[0].keys() if key.startswith("reward_term_"))
    for key in reward_term_keys:
        values = [float(row[key]) for row in records if row.get(key) is not None]
        if len(values) >= 1:
            summary[f"{key}_first"] = values[0]
            summary[f"{key}_final"] = values[-1]
            summary[f"{key}_delta_final_minus_first"] = values[-1] - values[0]
    return summary


def _write_contact_sheet(frames: list[Path], output_path: Path, thumb_width: int = 480) -> None:
    if not frames:
        return
    images = []
    for path in frames:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue
        scale = thumb_width / max(image.width, 1)
        image = image.resize((thumb_width, max(1, int(image.height * scale))))
        images.append(image)
    if not images:
        return
    cols = min(3, len(images))
    rows = math.ceil(len(images) / cols)
    cell_h = max(image.height for image in images)
    sheet = Image.new("RGB", (cols * thumb_width, rows * cell_h), (20, 20, 20))
    for idx, image in enumerate(images):
        x = (idx % cols) * thumb_width
        y = (idx // cols) * cell_h
        sheet.paste(image, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def _write_trace_plot(rows: list[dict[str, object]], output_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[WARN] matplotlib unavailable; skipping trace plot: {exc}", flush=True)
        return
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidates = sorted({str(row["candidate"]) for row in rows})
    fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=True)
    metric_specs = [
        ("reward", "reward"),
        ("ee_to_cube_dist_m", "EE-cube dist m"),
        ("cube_lift_height_m", "cube lift m"),
        ("gripper_width_m", "gripper width m"),
    ]
    for ax, (key, label) in zip(axes, metric_specs, strict=True):
        for candidate in candidates:
            subset = [row for row in rows if row["candidate"] == candidate and row["reset_index"] == 0]
            if not subset or subset[0].get(key) is None:
                continue
            ax.plot([int(row["step"]) for row in subset], [float(row[key]) for row in subset], label=candidate)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("step")
    axes[0].legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _write_action_plot(rows: list[dict[str, object]], output_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[WARN] matplotlib unavailable; skipping action plot: {exc}", flush=True)
        return
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidates = sorted({str(row["candidate"]) for row in rows})
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    for ax, key in zip(axes, ("action_z", "action_gripper", "tracking_post_to_exact_ee_dist_m"), strict=True):
        for candidate in candidates:
            subset = [row for row in rows if row["candidate"] == candidate and row["reset_index"] == 0]
            if not subset or subset[0].get(key) is None:
                continue
            ax.plot([int(row["step"]) for row in subset], [float(row[key]) for row in subset], label=candidate)
        ax.set_ylabel(key)
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("step")
    axes[0].legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _write_report(
    path: Path,
    *,
    config: dict[str, object],
    checkpoints: dict[str, str],
    summaries: list[dict[str, object]],
    artifacts: dict[str, str],
) -> None:
    best_by_candidate: dict[str, dict[str, object]] = {}
    for row in summaries:
        candidate = str(row["candidate"])
        current = best_by_candidate.get(candidate)
        if current is None or float(row.get("reward_mean", -1.0e9)) > float(current.get("reward_mean", -1.0e9)):
            best_by_candidate[candidate] = row
    lines = [
        "# Franka Cube Pass7 Action/Reward Audit",
        "",
        "Diagnostic-only run. No PPO/A100 launch and no reward/reset/task semantic change.",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(config, indent=2, sort_keys=True),
        "```",
        "",
        "## Checkpoints",
        "",
    ]
    if checkpoints:
        for label, ckpt in checkpoints.items():
            lines.append(f"- `{label}`: `{ckpt}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Candidate Summary", ""])
    lines.append(
        "| Candidate | Reward mean | Final reward | Final EE dist | Final finger dist | Final width | Max lift | Action z mean | Grip mean | Done |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for candidate in sorted(best_by_candidate):
        row = best_by_candidate[candidate]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{candidate}`",
                    f"{float(row.get('reward_mean', 0.0)):.4f}",
                    f"{float(row.get('reward_final', 0.0)):.4f}",
                    f"{float(row.get('ee_to_cube_dist_m_final', 0.0)):.4f}",
                    f"{float(row.get('finger_center_to_cube_dist_m_final', 0.0)):.4f}",
                    f"{float(row.get('gripper_width_m_final', 0.0)):.4f}",
                    f"{float(row.get('cube_lift_height_m_max', 0.0)):.4f}",
                    f"{float(row.get('action_z_mean', 0.0)):.4f}",
                    f"{float(row.get('action_gripper_mean', 0.0)):.4f}",
                    str(bool(row.get("done_seen", False))),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Artifacts", ""])
    for name, artifact_path in artifacts.items():
        lines.append(f"- `{name}`: `{artifact_path}`")
    lines.extend(
        [
            "",
            "## Initial Interpretation",
            "",
            "- Compare policy rows against `script_noop`, `script_hold_open`, `script_approach_exact_open`, `script_close_light_pregrasp`, `script_lift_closed`, and `script_assisted_oracle_short`.",
            "- A concerning policy signature is positive/open gripper action plus positive z/away motion that reduces immediate reward or increases EE/finger distance relative to scripted alternatives.",
            "- Reward/action changes remain hypotheses only; this audit intentionally leaves the apple-to-apple task unchanged.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_rollout(
    env,
    gym_env,
    task_env,
    env_cfg,
    *,
    env_id: int,
    reset_index: int,
    candidate: str,
    sample: dict[str, object],
    player: BasePlayer | None,
    snapshot,
    frames_dir: Path,
    rendered_frames: list[Path],
    render_candidate: bool,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    _restore_task_env_state(task_env, snapshot)
    if player is not None:
        player.reset()
        obs = _obs_policy_tensor(env.get_current_obs())
        _ = player.get_batch_size(obs, 1)
        if player.is_rnn:
            player.init_rnn()
    else:
        obs = None
    records: list[dict[str, object]] = []
    if render_candidate:
        _render_frame(
            gym_env,
            task_env,
            env_cfg,
            env_id=env_id,
            reset_index=reset_index,
            candidate=candidate,
            step=0,
            phase="reset_pregrasp",
            sample=sample,
            record=None,
            frames_dir=frames_dir,
            rendered_frames=rendered_frames,
        )
    for step in range(1, max(int(args_cli.horizon_steps), 1) + 1):
        if not simulation_app.is_running():
            break
        with torch.inference_mode():
            if player is not None:
                obs_t = player.obs_to_torch(obs)
                action = player.get_action(obs_t, is_deterministic=bool(args_cli.deterministic))
                phase = "policy"
            else:
                action, phase = _scripted_action(task_env, env_id, candidate, step)
            tracking_before = _action_tracking_before_step(task_env, env_id, action)
            step_out = env.step(action)
            if len(step_out) == 5:
                obs, rewards, terminated, truncated, _ = step_out
                dones = torch.logical_or(terminated, truncated)
            else:
                obs, rewards, dones, _ = step_out
                terminated = dones
                truncated = torch.zeros_like(dones) if isinstance(dones, torch.Tensor) else False
            obs = _obs_policy_tensor(obs)
            record = _step_record(
                task_env,
                env_id,
                reset_index=reset_index,
                candidate=candidate,
                step=step,
                phase=phase,
                action=action,
                reward=rewards,
                terminated=terminated,
                truncated=truncated,
                tracking_before=tracking_before,
            )
            records.append(record)
            if render_candidate and (
                step == 1
                or step == int(args_cli.horizon_steps)
                or step % max(int(args_cli.render_interval), 1) == 0
                or bool(record["done"])
            ):
                _render_frame(
                    gym_env,
                    task_env,
                    env_cfg,
                    env_id=env_id,
                    reset_index=reset_index,
                    candidate=candidate,
                    step=step,
                    phase=phase,
                    sample=sample,
                    record=record,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_frames,
                )
            if bool(record["done"]):
                break
            if isinstance(dones, torch.Tensor) and player is not None and player.is_rnn and player.states is not None:
                dones_bool = dones.bool()
                if dones_bool.any():
                    for state in player.states:
                        state[:, dones_bool, :] = 0.0
    summary = _summarize_rollout(records, sample, candidate)
    return records, summary


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("action_audit_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    checkpoints = _parse_checkpoints(args_cli.checkpoint)
    env_cfg.scene.num_envs = int(args_cli.num_envs)
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = int(args_cli.seed)
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_library_path = str(args_cli.grasp_prior_library_path)
    env_cfg.cube_spawn_xy_randomization = float(args_cli.cube_spawn_xy_randomization)
    if hasattr(env_cfg, "use_cuda_graph"):
        env_cfg.use_cuda_graph = False
    agent_cfg["params"]["seed"] = int(args_cli.seed)

    print("[INFO] Action/reward audit config:")
    print_dict(
        {
            "task": args_cli.task,
            "num_envs": env_cfg.scene.num_envs,
            "num_resets": args_cli.num_resets,
            "horizon_steps": args_cli.horizon_steps,
            "match_reset_state": args_cli.match_reset_state,
            "seed": args_cli.seed,
            "cube_spawn_xy_randomization": args_cli.cube_spawn_xy_randomization,
            "grasp_prior_library_path": args_cli.grasp_prior_library_path,
            "checkpoints": checkpoints,
            "output_dir": str(output_dir),
        },
        nesting=4,
    )

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)
    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.render else None)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    _set_camera(task_env, env_cfg, 0)
    env = DextrahAuditRlGamesVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register(
        "DextrahAuditRlgWrapper",
        lambda config_name, num_actors, **kwargs: DextrahAuditRlGamesGpuEnv(config_name, num_actors, **kwargs),
    )
    env_configurations.register("rlgpu", {"vecenv_type": "DextrahAuditRlgWrapper", "env_creator": lambda **kwargs: env})

    players = {label: _create_player(agent_cfg, env, label, path) for label, path in checkpoints.items()}
    scripted_candidates = [
        "script_noop",
        "script_hold_open",
        "script_approach_exact_open",
        "script_close_light_pregrasp",
        "script_lift_closed",
        "script_assisted_oracle_short",
    ]
    all_candidates = list(players.keys()) + scripted_candidates
    render_candidates = {item.strip() for item in args_cli.render_candidates.split(",") if item.strip()}
    if "all" in render_candidates:
        render_candidates = set(all_candidates)

    reset_samples: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    rendered_frames: list[Path] = []

    env_id = 0
    if bool(args_cli.match_reset_state):
        env.reset()
        for reset_index in range(int(args_cli.num_resets)):
            if reset_index > 0:
                env.reset()
            sample = _collect_reset_sample(task_env, env_id, reset_index)
            sample["matched_reset_state"] = True
            reset_samples.append(sample)
            snapshot = _snapshot_task_env_state(task_env)
            print(
                "[AUDIT_RESET] "
                f"reset={reset_index} sample={sample['sample_index']} "
                f"reset_success={sample['reset_success']} quality={sample['reset_grasp_quality_success']} "
                f"ee={sample['ee_to_cube_dist_m']:.4f} finger={sample['finger_center_to_cube_dist_m']:.4f} "
                "matched_state=True",
                flush=True,
            )
            for candidate in all_candidates:
                player = players.get(candidate)
                render_candidate = (
                    bool(args_cli.render)
                    and reset_index < int(args_cli.render_resets)
                    and candidate in render_candidates
                )
                records, summary = _run_rollout(
                    env,
                    gym_env,
                    task_env,
                    env_cfg,
                    env_id=env_id,
                    reset_index=reset_index,
                    candidate=candidate,
                    sample=sample,
                    player=player,
                    snapshot=snapshot,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_frames,
                    render_candidate=render_candidate,
                )
                trace_rows.extend(records)
                summary_rows.append(summary)
                if args_cli.print_interval > 0:
                    print(
                        "[AUDIT_ROLLOUT] "
                        f"reset={reset_index} candidate={candidate} "
                        f"reward_mean={summary.get('reward_mean')} "
                        f"ee_final={summary.get('ee_to_cube_dist_m_final')} "
                        f"finger_final={summary.get('finger_center_to_cube_dist_m_final')} "
                        f"lift_max={summary.get('cube_lift_height_m_max')} "
                        f"done={summary.get('done_seen')}",
                        flush=True,
                    )
            _restore_task_env_state(task_env, snapshot)
    else:
        for reset_index in range(int(args_cli.num_resets)):
            for candidate in all_candidates:
                player = players.get(candidate)
                render_candidate = (
                    bool(args_cli.render)
                    and reset_index < int(args_cli.render_resets)
                    and candidate in render_candidates
                )
                env.reset()
                sample = _collect_reset_sample(task_env, env_id, reset_index)
                sample["candidate"] = candidate
                sample["matched_reset_state"] = False
                reset_samples.append(sample)
                snapshot = _snapshot_task_env_state(task_env)
                print(
                    "[AUDIT_RESET] "
                    f"reset={reset_index} candidate={candidate} sample={sample['sample_index']} "
                    f"reset_success={sample['reset_success']} quality={sample['reset_grasp_quality_success']} "
                    f"ee={sample['ee_to_cube_dist_m']:.4f} finger={sample['finger_center_to_cube_dist_m']:.4f} "
                    "matched_state=False",
                    flush=True,
                )
                records, summary = _run_rollout(
                    env,
                    gym_env,
                    task_env,
                    env_cfg,
                    env_id=env_id,
                    reset_index=reset_index,
                    candidate=candidate,
                    sample=sample,
                    player=player,
                    snapshot=snapshot,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_frames,
                    render_candidate=render_candidate,
                )
                trace_rows.extend(records)
                summary_rows.append(summary)
                if args_cli.print_interval > 0:
                    print(
                        "[AUDIT_ROLLOUT] "
                        f"reset={reset_index} candidate={candidate} "
                        f"reward_mean={summary.get('reward_mean')} "
                        f"ee_final={summary.get('ee_to_cube_dist_m_final')} "
                        f"finger_final={summary.get('finger_center_to_cube_dist_m_final')} "
                        f"lift_max={summary.get('cube_lift_height_m_max')} "
                        f"done={summary.get('done_seen')}",
                        flush=True,
                    )

    trace_jsonl = output_dir / "action_reward_trace.jsonl"
    trace_csv = output_dir / "action_reward_trace.csv"
    summary_csv = output_dir / "rollout_summary.csv"
    reset_csv = output_dir / "reset_samples.csv"
    _write_jsonl(trace_jsonl, trace_rows)
    _write_csv(trace_csv, trace_rows)
    _write_csv(summary_csv, summary_rows)
    _write_csv(reset_csv, reset_samples)
    trace_plot = output_dir / "action_reward_trace_plot.png"
    action_plot = output_dir / "action_tracking_plot.png"
    contact_sheet = output_dir / "action_audit_contact_sheet.jpg"
    _write_trace_plot(trace_rows, trace_plot)
    _write_action_plot(trace_rows, action_plot)
    _write_contact_sheet(rendered_frames, contact_sheet)

    artifacts = {
        "trace_jsonl": str(trace_jsonl),
        "trace_csv": str(trace_csv),
        "summary_csv": str(summary_csv),
        "reset_csv": str(reset_csv),
        "trace_plot": str(trace_plot),
        "action_plot": str(action_plot),
        "contact_sheet": str(contact_sheet),
        "frames_dir": str(frames_dir),
    }
    config = {
        "task": args_cli.task,
        "num_envs": int(args_cli.num_envs),
        "num_resets": int(args_cli.num_resets),
        "horizon_steps": int(args_cli.horizon_steps),
        "match_reset_state": bool(args_cli.match_reset_state),
        "seed": int(args_cli.seed),
        "cube_spawn_xy_randomization": float(args_cli.cube_spawn_xy_randomization),
        "grasp_prior_library_path": str(args_cli.grasp_prior_library_path),
        "close_width": float(args_cli.close_width),
        "lift_action_z": float(args_cli.lift_action_z),
        "oracle_proportional_gain": float(args_cli.oracle_proportional_gain),
        "oracle_max_position_action": float(args_cli.oracle_max_position_action),
        "oracle_track_orientation": bool(args_cli.oracle_track_orientation),
        "deterministic": bool(args_cli.deterministic),
    }
    report_path = output_dir / "REPORT.md"
    _write_report(report_path, config=config, checkpoints=checkpoints, summaries=summary_rows, artifacts=artifacts)
    artifacts["report"] = str(report_path)
    payload = {
        "config": config,
        "checkpoints": checkpoints,
        "reset_samples": reset_samples,
        "rollout_summaries": summary_rows,
        "artifacts": artifacts,
    }
    metrics_path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] Wrote audit metrics to {metrics_path}", flush=True)
    print(f"[INFO] Wrote audit report to {report_path}", flush=True)
    print("[INFO] Audit complete", flush=True)
    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
