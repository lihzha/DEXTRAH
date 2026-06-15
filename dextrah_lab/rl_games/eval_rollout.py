# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Evaluate an RL-Games checkpoint and optionally record a rollout video."""

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Evaluate an RL-Games checkpoint.")
parser.add_argument("--video", action="store_true", default=False, help="Record a rollout video.")
parser.add_argument("--video_length", type=int, default=600, help="Length of the recorded video in steps.")
parser.add_argument("--video_folder", type=str, default=None, help="Directory for rollout videos.")
parser.add_argument("--video_name_prefix", type=str, default="cube-grasp-eval", help="Prefix for rollout video files.")
parser.add_argument("--camera_eye", type=float, nargs=3, default=None, help="Viewport camera eye for video eval.")
parser.add_argument("--camera_target", type=float, nargs=3, default=None, help="Viewport camera target for video eval.")
parser.add_argument(
    "--camera_env_index",
    type=int,
    default=0,
    help="Vectorized environment index whose origin is used to offset the eval video camera.",
)
parser.add_argument("--num_steps", type=int, default=600, help="Number of policy steps to run.")
parser.add_argument("--success_window", type=int, default=100, help="Trailing window for final success-rate average.")
parser.add_argument("--print_interval", type=int, default=20, help="Print metrics every N steps.")
parser.add_argument("--output_dir", type=str, default=None, help="Directory for eval outputs.")
parser.add_argument("--metrics_path", type=str, default=None, help="Path to write metrics JSON.")
parser.add_argument("--trace_csv_path", type=str, default=None, help="Path to write per-step trace CSV.")
parser.add_argument("--trace_jsonl_path", type=str, default=None, help="Path to write per-step trace JSONL.")
parser.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True, help="Use deterministic actions.")
parser.add_argument(
    "--action_source",
    choices=(
        "policy",
        "zero",
        "reference_delta",
        "policy_reference_mix",
        "reference_delta_hold",
        "policy_reference_mix_hold",
    ),
    default="policy",
    help=(
        "Action source for rollout. 'policy' loads an RL-Games checkpoint. "
        "'reference_delta' maps the trajectory target position/gripper schedule "
        "into the existing Franka delta-IK action interface. "
        "'policy_reference_mix' loads a policy checkpoint and blends its action "
        "toward the reference_delta action. '*_hold' variants follow the source "
        "until a contact/lift/success/phase trigger, then hold a lifted target "
        "with a closed gripper."
    ),
)
parser.add_argument(
    "--reference_mix_alpha",
    type=float,
    default=0.0,
    help="For policy_reference_mix* action sources, fraction of reference_delta action in the pre-hold action.",
)
parser.add_argument(
    "--reference_mix_gripper_alpha",
    type=float,
    default=None,
    help=(
        "Optional eval-only override for action dim6 under policy_reference_mix* action sources. "
        "When unset, the gripper dimension uses --reference_mix_alpha like every other action dimension."
    ),
)
parser.add_argument(
    "--reference_mix_z_alpha",
    type=float,
    default=None,
    help=(
        "Optional eval-only override for action dim2 under policy_reference_mix* action sources. "
        "When unset, the z/lift dimension uses --reference_mix_alpha like every other action dimension."
    ),
)
parser.add_argument(
    "--hold_trigger_mode",
    choices=("any", "contact_after_phase_or_lift_success", "lift_success_only"),
    default="any",
    help=(
        "For *_hold action sources, choose how hold activation combines triggers. "
        "'any' preserves legacy phase OR lift OR success OR contact behavior. "
        "'contact_after_phase_or_lift_success' prevents phase-only/free-space hold by requiring "
        "late contact, actual lift, or success. 'lift_success_only' ignores phase/contact triggers."
    ),
)
parser.add_argument(
    "--hold_phase_start",
    type=float,
    default=0.42,
    help="For *_hold action sources, force terminal hold once trajectory phase progress reaches this value.",
)
parser.add_argument(
    "--hold_trigger_lift_height",
    type=float,
    default=0.02,
    help="For *_hold action sources, enter hold when cube lift height reaches this many meters.",
)
parser.add_argument(
    "--hold_contact_max_finger_dist",
    type=float,
    default=0.16,
    help="For *_hold action sources, enter hold when max finger-to-cube distance is below this value.",
)
parser.add_argument(
    "--hold_lift_height",
    type=float,
    default=0.10,
    help="For *_hold action sources, hold target z is cube z at trigger plus this many meters.",
)
parser.add_argument(
    "--hold_target_policy",
    choices=("cube_trigger_plus_lift", "cube_current_plus_trigger_ee_offset"),
    default="cube_trigger_plus_lift",
    help=(
        "For *_hold action sources, target policy after hold trigger. "
        "'cube_trigger_plus_lift' preserves the previous static cube-position target. "
        "'cube_current_plus_trigger_ee_offset' stores the trigger-frame EE-minus-cube "
        "offset and tracks cube_current + offset + hold_lift_height*z."
    ),
)
parser.add_argument(
    "--hold_gripper_action",
    type=float,
    default=-1.0,
    help="For *_hold action sources, gripper command after hold trigger.",
)
parser.add_argument(
    "--suppress_success_termination",
    action=argparse.BooleanOptionalAction,
    default=False,
    help=(
        "Eval-only diagnostic: mask success_done termination so the rollout continues after first success. "
        "Other termination reasons remain active, and metrics still record when success_done would have fired."
    ),
)
parser.add_argument(
    "--summary_window",
    type=int,
    default=120,
    help="Fixed window size in steps for episode-independent first/middle/last metric summaries.",
)
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment.")
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
parser.add_argument("--num_envs", type=int, default=None, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--checkpoint", type=str, default=None, help="Path to model checkpoint.")
parser.add_argument(
    "--use_last_checkpoint",
    action="store_true",
    help="When no checkpoint is provided, use the last saved model instead of the best saved model.",
)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

if args_cli.video:
    args_cli.enable_cameras = True

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

from rl_games.algos_torch import torch_ext
from rl_games.common import env_configurations, vecenv
from rl_games.common.player import BasePlayer
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict
import isaaclab.utils.math as math_utils

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import get_checkpoint_path, parse_env_cfg
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401

from residual_action_adapter import build_residual_adapter_from_metadata


POLICY_ACTION_SOURCES = ("policy", "policy_reference_mix", "policy_reference_mix_hold")
MIX_ACTION_SOURCES = ("policy_reference_mix", "policy_reference_mix_hold")
HOLD_ACTION_SOURCES = ("reference_delta_hold", "policy_reference_mix_hold")


def _mean_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tensor_stat_float(value, stat: str) -> float | None:
    if not isinstance(value, torch.Tensor):
        return None
    tensor = value.detach().float()
    if tensor.numel() == 0:
        return None
    if stat == "min":
        result = tensor.min()
    elif stat == "max":
        result = tensor.max()
    else:
        result = tensor.mean()
    return float(result.cpu())


def _env_metric(task_env, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    return _mean_float(getattr(task_env, name))


def _tensor_values(value, expected_len: int | None = None) -> list[float] | None:
    if not isinstance(value, torch.Tensor):
        return None
    values = value.detach().float().flatten().cpu().tolist()
    if expected_len is not None and len(values) != expected_len:
        return None
    return [float(item) for item in values]


def _env_metric_values(task_env, name: str, expected_len: int | None = None) -> list[float] | None:
    if not hasattr(task_env, name):
        return None
    return _tensor_values(getattr(task_env, name), expected_len=expected_len)


def _add_vector_metrics(metrics: dict[str, float | None], prefix: str, value, labels: tuple[str, ...]) -> None:
    if not isinstance(value, torch.Tensor) or value.numel() == 0:
        return
    tensor = value.detach().float()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    if tensor.shape[-1] < len(labels):
        return
    mean_values = tensor[..., : len(labels)].reshape(-1, len(labels)).mean(dim=0).cpu().tolist()
    first_values = tensor.reshape(-1, tensor.shape[-1])[0, : len(labels)].cpu().tolist()
    for idx, label in enumerate(labels):
        metrics[f"{prefix}_{label}_mean"] = float(mean_values[idx])
        metrics[f"{prefix}_{label}_env0"] = float(first_values[idx])


def _add_action_signal_metrics(metrics: dict[str, float | None], prefix: str, actions: torch.Tensor | None) -> None:
    if not isinstance(actions, torch.Tensor):
        return
    action_tensor = actions.detach().float()
    if action_tensor.ndim < 2 or action_tensor.numel() == 0:
        return
    dim_count = action_tensor.shape[-1]
    for dim in range(min(dim_count, 7)):
        metrics[f"{prefix}_dim{dim}_mean"] = _mean_float(action_tensor[:, dim])
    if dim_count >= 3:
        metrics[f"{prefix}_z_mean"] = _mean_float(action_tensor[:, 2])
        metrics[f"{prefix}_up_mean"] = _mean_float(torch.clamp(action_tensor[:, 2], 0.0, 1.0))
    if dim_count >= 7:
        metrics[f"{prefix}_gripper_mean"] = _mean_float(action_tensor[:, 6])
        metrics[f"{prefix}_close_mean"] = _mean_float(torch.clamp(-action_tensor[:, 6], 0.0, 1.0))


def _add_action_delta_metrics(
    metrics: dict[str, float | None],
    prefix: str,
    lhs: torch.Tensor | None,
    rhs: torch.Tensor | None,
) -> None:
    if not isinstance(lhs, torch.Tensor) or not isinstance(rhs, torch.Tensor):
        return
    lhs_tensor = lhs.detach().float()
    rhs_tensor = rhs.detach().float()
    if lhs_tensor.shape != rhs_tensor.shape or lhs_tensor.ndim < 2 or lhs_tensor.numel() == 0:
        return
    delta = lhs_tensor - rhs_tensor
    metrics[f"{prefix}_mse_mean"] = _mean_float(torch.mean(torch.square(delta), dim=-1))
    metrics[f"{prefix}_l2_mean"] = _mean_float(torch.norm(delta, dim=-1))
    if lhs_tensor.shape[-1] >= 3:
        metrics[f"{prefix}_z_abs_mean"] = _mean_float(torch.abs(delta[:, 2]))
        lhs_up = torch.clamp(lhs_tensor[:, 2], 0.0, 1.0)
        rhs_up = torch.clamp(rhs_tensor[:, 2], 0.0, 1.0)
        metrics[f"{prefix}_up_abs_mean"] = _mean_float(torch.abs(lhs_up - rhs_up))
    if lhs_tensor.shape[-1] >= 7:
        metrics[f"{prefix}_gripper_abs_mean"] = _mean_float(torch.abs(delta[:, 6]))
        lhs_close = torch.clamp(-lhs_tensor[:, 6], 0.0, 1.0)
        rhs_close = torch.clamp(-rhs_tensor[:, 6], 0.0, 1.0)
        metrics[f"{prefix}_close_abs_mean"] = _mean_float(torch.abs(lhs_close - rhs_close))


def _collect_task_metrics(task_env, actions: torch.Tensor | None = None) -> dict[str, float | None]:
    metric_names = [
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "left_finger_to_cube_dist",
        "right_finger_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_distance_asymmetry",
        "hand_to_cube_mean_dist",
        "hand_to_cube_max_dist",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "grasp_prior_reset_attempted",
        "grasp_prior_reset_success",
        "grasp_prior_reset_farther",
        "grasp_prior_reset_pos_error",
        "grasp_prior_reset_rot_error",
        "grasp_prior_reset_exact_tool_dist",
        "grasp_prior_reset_pregrasp_tool_dist",
        "grasp_prior_reset_exact_ee_dist",
        "grasp_prior_reset_pregrasp_ee_dist",
        "grasp_prior_reset_finger_center_dist",
        "grasp_prior_reset_finger_table_clearance",
        "grasp_prior_reset_gripper_width",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_offset_radial_dot",
        "grasp_prior_reset_offset_radial_angle",
        "grasp_prior_reset_projected_exact_finger_center_dist",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_pregrasp_tip_table_clearance",
        "grasp_prior_reset_projected_exact_tip_table_clearance",
        "grasp_prior_reset_quality_success",
        "grasp_prior_reset_candidate_tool_down_count",
        "grasp_prior_reset_candidate_table_count",
        "grasp_prior_action_warmstart_active",
        "grasp_prior_action_warmstart_phase",
        "grasp_prior_action_warmstart_policy_action_z",
        "grasp_prior_action_warmstart_policy_gripper_action",
        "grasp_prior_action_warmstart_applied_action_z",
        "grasp_prior_action_warmstart_applied_gripper_action",
        "grasp_prior_action_warmstart_action_delta_abs",
        "grasp_prior_action_warmstart_exact_ee_error",
        "grasp_prior_action_prior_active",
        "grasp_prior_action_prior_phase",
        "grasp_prior_action_prior_delta_abs",
        "grasp_prior_action_prior_reward",
        "grasp_prior_action_prior_teacher_action_z",
        "grasp_prior_action_prior_teacher_gripper_action",
        "grasp_prior_action_prior_exact_ee_error",
        "star_lift_height",
        "star_initial_xy_error",
        "goal_xy_error",
        "goal_height_error",
        "goal_yaw_error",
        "has_lifted_star",
        "ee_to_star_dist",
        "finger_center_to_star_dist",
        "left_finger_to_star_dist",
        "right_finger_to_star_dist",
        "max_finger_to_star_dist",
        "finger_distance_asymmetry",
        "gripper_width",
        "traj_phase_progress",
        "traj_target_table_clearance",
        "traj_target_gripper_width",
    ]
    stat_metric_names = {
        "cube_lift_height",
        "cube_xy_error",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "gripper_width",
        "traj_target_table_clearance",
        "traj_target_gripper_width",
    }
    metrics = {}
    for name in metric_names:
        if not hasattr(task_env, name):
            continue
        value = getattr(task_env, name)
        metrics[name] = _mean_float(value)
        if name in stat_metric_names:
            metrics[f"{name}_min"] = _tensor_stat_float(value, "min")
            metrics[f"{name}_max"] = _tensor_stat_float(value, "max")
    log_terms = getattr(task_env, "extras", {}).get("log", {})
    if isinstance(log_terms, dict):
        for name, value in log_terms.items():
            if isinstance(name, str) and name.startswith("cube_traj_tracking_"):
                mean_value = _mean_float(value)
                if mean_value is not None:
                    metrics[name] = mean_value
    _add_vector_metrics(metrics, "ee_pos", getattr(task_env, "ee_pos", None), ("x", "y", "z"))
    _add_vector_metrics(metrics, "cube_pos", getattr(task_env, "cube_pos", None), ("x", "y", "z"))
    _add_vector_metrics(
        metrics,
        "grasp_prior_reset_offset_dir",
        getattr(task_env, "grasp_prior_reset_offset_dir_w", None),
        ("x", "y", "z"),
    )
    tool_z_axis = getattr(task_env, "grasp_prior_reset_tool_z_axis_w", None)
    _add_vector_metrics(metrics, "grasp_prior_reset_tool_z_axis", tool_z_axis, ("x", "y", "z"))
    if tool_z_axis is not None:
        metrics["grasp_prior_reset_tool_downward_z"] = _mean_float(-tool_z_axis[:, 2])
        metrics["grasp_prior_reset_tool_downward_z_min"] = _tensor_stat_float(-tool_z_axis[:, 2], "min")
        metrics["grasp_prior_reset_tool_downward_z_max"] = _tensor_stat_float(-tool_z_axis[:, 2], "max")
    _add_vector_metrics(metrics, "traj_target_ee_pos", getattr(task_env, "traj_target_ee_pos", None), ("x", "y", "z"))
    _add_vector_metrics(metrics, "ee_quat", getattr(task_env, "ee_quat", None), ("w", "x", "y", "z"))
    _add_vector_metrics(
        metrics,
        "traj_target_ee_quat",
        getattr(task_env, "traj_target_ee_quat", None),
        ("w", "x", "y", "z"),
    )
    if hasattr(task_env, "ee_pos") and hasattr(task_env, "traj_target_ee_pos"):
        ee_to_target = torch.norm(task_env.ee_pos - task_env.traj_target_ee_pos, dim=-1)
        metrics["ee_to_traj_target_dist"] = _mean_float(ee_to_target)
        metrics["ee_to_traj_target_dist_min"] = _tensor_stat_float(ee_to_target, "min")
        metrics["ee_to_traj_target_dist_max"] = _tensor_stat_float(ee_to_target, "max")
    if isinstance(actions, torch.Tensor):
        _add_action_signal_metrics(metrics, "applied_action", actions)
        action_tensor = actions.detach().float()
        if action_tensor.ndim >= 2 and action_tensor.shape[-1] >= 7:
            # Backward-compatible names from earlier eval artifacts; for mixed
            # rollouts these describe the action actually applied to the env.
            metrics["policy_action_z_mean"] = metrics.get("applied_action_z_mean")
            metrics["policy_action_gripper_mean"] = metrics.get("applied_action_gripper_mean")
            metrics["policy_action_close_mean"] = metrics.get("applied_action_close_mean")
            metrics["policy_action_up_mean"] = metrics.get("applied_action_up_mean")
    raw_policy_actions = getattr(task_env, "traj_raw_policy_actions", None)
    reference_actions = getattr(task_env, "traj_reference_actions", None)
    env_applied_actions = getattr(task_env, "traj_applied_actions", None)
    _add_action_signal_metrics(metrics, "env_raw_policy_action", raw_policy_actions)
    _add_action_signal_metrics(metrics, "env_reference_action", reference_actions)
    _add_action_signal_metrics(metrics, "env_applied_action", env_applied_actions)
    _add_action_delta_metrics(metrics, "env_raw_policy_reference_action_error", raw_policy_actions, reference_actions)
    _add_action_delta_metrics(metrics, "env_applied_reference_action_error", env_applied_actions, reference_actions)
    _add_action_delta_metrics(metrics, "env_applied_policy_action_error", env_applied_actions, raw_policy_actions)
    return metrics


def _zero_actions(task_env) -> torch.Tensor:
    return torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)


def _reference_delta_actions(task_env) -> torch.Tensor:
    """Track the current task-space reference using the env's delta-IK action convention.

    This is deliberately not joint replay.  The compact reference is transformed
    into runtime task-space targets by the environment; this helper converts the
    current target position and gripper width into the 7-D relative action used
    by the Franka task.  Orientation is left to the existing IK/controller state
    for this cheap feasibility smoke.
    """

    if hasattr(task_env, "compute_grasp_prior_reference_actions"):
        return task_env.compute_grasp_prior_reference_actions()
    if not hasattr(task_env, "traj_target_ee_pos"):
        raise ValueError("reference_delta action source requires a trajectory-tracking task environment.")
    if hasattr(task_env, "compute_reference_delta_actions"):
        return task_env.compute_reference_delta_actions()
    if hasattr(task_env, "_compute_intermediate_values"):
        task_env._compute_intermediate_values()
    if hasattr(task_env, "_update_trajectory_tracking_targets"):
        task_env._update_trajectory_tracking_targets()

    ee_pos_b, _ = task_env._compute_ee_frame_pose()
    target_pos_local = task_env.traj_target_ee_pos
    target_pos_w = target_pos_local + task_env.scene.env_origins
    target_pos_b, _ = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        target_pos_w,
        task_env._robot.data.root_quat_w,
    )

    actions = _zero_actions(task_env)
    position_scale = torch.clamp(task_env.action_scale[:3], min=1.0e-6)
    actions[:, :3] = torch.clamp((target_pos_b - ee_pos_b) / position_scale, -1.0, 1.0)
    if actions.shape[-1] >= 7 and hasattr(task_env, "traj_target_gripper_width"):
        max_width = max(float(task_env.cfg.max_gripper_width), 1.0e-6)
        actions[:, 6] = torch.clamp(2.0 * task_env.traj_target_gripper_width / max_width - 1.0, -1.0, 1.0)
    return actions


def _delta_actions_to_local_targets(
    task_env,
    target_pos_local: torch.Tensor,
    gripper_action: float,
) -> torch.Tensor:
    """Convert local env-frame task-space targets into the Franka delta-IK action convention."""

    if hasattr(task_env, "_compute_intermediate_values"):
        task_env._compute_intermediate_values()

    ee_pos_b, _ = task_env._compute_ee_frame_pose()
    target_pos_w = target_pos_local + task_env.scene.env_origins
    target_pos_b, _ = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        target_pos_w,
        task_env._robot.data.root_quat_w,
    )

    actions = _zero_actions(task_env)
    position_scale = torch.clamp(task_env.action_scale[:3], min=1.0e-6)
    actions[:, :3] = torch.clamp((target_pos_b - ee_pos_b) / position_scale, -1.0, 1.0)
    if actions.shape[-1] >= 7:
        actions[:, 6] = torch.clamp(
            torch.full((task_env.num_envs,), float(gripper_action), device=task_env.device),
            -1.0,
            1.0,
        )
    return actions


def _env_tensor(task_env, name: str, default: float = 0.0) -> torch.Tensor:
    value = getattr(task_env, name, None)
    if isinstance(value, torch.Tensor):
        tensor = value.detach().float()
        if tensor.ndim == 0:
            return tensor.reshape(1).expand(task_env.num_envs).to(device=task_env.device)
        return tensor.reshape(task_env.num_envs, -1)[:, 0].to(device=task_env.device)
    return torch.full((task_env.num_envs,), float(default), device=task_env.device)


def _env_bool_tensor(task_env, name: str, default: bool = False) -> torch.Tensor:
    value = getattr(task_env, name, None)
    if isinstance(value, torch.Tensor):
        tensor = value.detach()
        if tensor.ndim == 0:
            return tensor.bool().reshape(1).expand(task_env.num_envs).to(device=task_env.device)
        return tensor.reshape(task_env.num_envs, -1)[:, 0].bool().to(device=task_env.device)
    return torch.full((task_env.num_envs,), bool(default), dtype=torch.bool, device=task_env.device)


def _step_tensor_summary(values: torch.Tensor) -> dict[str, float | int | None]:
    if not isinstance(values, torch.Tensor):
        return {"count": 0, "mean": None, "min": None, "max": None}
    valid = values.detach().float()
    valid = valid[valid >= 0.0]
    if valid.numel() == 0:
        return {"count": 0, "mean": None, "min": None, "max": None}
    return {
        "count": int(valid.numel()),
        "mean": float(valid.mean().cpu()),
        "min": float(valid.min().cpu()),
        "max": float(valid.max().cpu()),
    }


def _tensor_bool_list(values: torch.Tensor) -> list[bool]:
    if not isinstance(values, torch.Tensor):
        return []
    return [bool(v) for v in values.detach().bool().cpu().tolist()]


def _tensor_float_list(values: torch.Tensor) -> list[float]:
    if not isinstance(values, torch.Tensor):
        return []
    return [float(v) for v in values.detach().float().cpu().tolist()]


def _done_reason_snapshot(task_env, success_timeout_override: float | None = None) -> dict[str, torch.Tensor]:
    """Snapshot likely termination reasons before env.step may auto-reset done envs."""

    if hasattr(task_env, "_compute_intermediate_values"):
        task_env._compute_intermediate_values()

    false = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    if not hasattr(task_env, "cube_pos"):
        return {
            "success_region": _env_bool_tensor(task_env, "in_success_region"),
            "success_done": false,
            "cube_out": false,
            "prelift_drag": false,
            "finger_table_penetration": false,
            "truncated": false,
        }

    cfg = getattr(task_env, "cfg", None)
    if cfg is None:
        return {
            "success_region": _env_bool_tensor(task_env, "in_success_region"),
            "success_done": false,
            "cube_out": false,
            "prelift_drag": false,
            "finger_table_penetration": false,
            "truncated": false,
        }

    cube_pos = getattr(task_env, "cube_pos")
    lower_x = float(getattr(cfg, "table_center_x", 0.0)) - 0.5 * float(getattr(cfg, "table_size_x", 0.0)) - float(
        getattr(cfg, "out_of_bounds_margin", 0.0)
    )
    upper_x = float(getattr(cfg, "table_center_x", 0.0)) + 0.5 * float(getattr(cfg, "table_size_x", 0.0)) + float(
        getattr(cfg, "out_of_bounds_margin", 0.0)
    )
    lower_y = -0.5 * float(getattr(cfg, "table_size_y", 0.0)) - float(getattr(cfg, "out_of_bounds_margin", 0.0))
    upper_y = 0.5 * float(getattr(cfg, "table_size_y", 0.0)) + float(getattr(cfg, "out_of_bounds_margin", 0.0))
    cube_out = (
        (cube_pos[:, 0] < lower_x)
        | (cube_pos[:, 0] > upper_x)
        | (cube_pos[:, 1] < lower_y)
        | (cube_pos[:, 1] > upper_y)
        | (cube_pos[:, 2] < float(getattr(cfg, "table_surface_z", 0.0)) - 0.08)
    )
    episode_length = _env_tensor(task_env, "episode_length_buf")
    success_region = _env_bool_tensor(task_env, "in_success_region")
    success_timeout = (
        float(success_timeout_override)
        if success_timeout_override is not None
        else float(getattr(cfg, "success_timeout", math.inf))
    )
    success_done = (
        (_env_tensor(task_env, "time_in_success_region") >= success_timeout)
        & (episode_length >= int(getattr(cfg, "min_episode_steps_before_success", 0)))
    )
    prelift_drag = (
        (~_env_bool_tensor(task_env, "has_lifted_cube"))
        & (_env_tensor(task_env, "cube_xy_error") >= float(getattr(cfg, "prelift_drag_termination_xy_error", math.inf)))
        & (episode_length > 2)
    )
    finger_table_penetration = (
        _env_tensor(task_env, "finger_table_clearance", default=math.inf)
        < float(getattr(cfg, "finger_table_penetration_termination_margin", -math.inf))
    ) & (episode_length > 2)
    truncated = episode_length >= int(getattr(task_env, "max_episode_length", math.inf)) - 1
    return {
        "success_region": success_region,
        "success_done": success_done,
        "cube_out": cube_out,
        "prelift_drag": prelift_drag,
        "finger_table_penetration": finger_table_penetration,
        "truncated": truncated,
    }


def _install_success_termination_suppression(task_env) -> bool:
    """Mask success termination for eval-only stability diagnostics."""

    original_get_dones = getattr(task_env, "_get_dones", None)
    cfg = getattr(task_env, "cfg", None)
    if original_get_dones is None or cfg is None or not hasattr(cfg, "success_timeout"):
        return False

    original_success_timeout = float(getattr(cfg, "success_timeout"))
    setattr(task_env, "_eval_original_success_timeout", original_success_timeout)
    setattr(task_env, "_eval_suppress_success_termination", True)
    setattr(task_env, "_eval_original_get_dones", original_get_dones)

    def _get_dones_without_success():
        terminated, truncated = original_get_dones()
        reasons = _done_reason_snapshot(task_env, success_timeout_override=original_success_timeout)
        return terminated & (~reasons["success_done"]), truncated

    setattr(task_env, "_get_dones", _get_dones_without_success)
    return True


def _ensure_hold_state(task_env) -> dict[str, torch.Tensor]:
    state = getattr(task_env, "_eval_terminal_hold_state", None)
    if (
        not isinstance(state, dict)
        or state.get("active", torch.empty(0, device=task_env.device)).shape[0] != task_env.num_envs
    ):
        state = {
            "active": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "target_pos_local": torch.zeros(task_env.num_envs, 3, device=task_env.device),
            "trigger_ee_cube_offset_local": torch.zeros(task_env.num_envs, 3, device=task_env.device),
            "trigger_step": torch.full((task_env.num_envs,), -1.0, device=task_env.device),
            "phase_triggered": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "lift_triggered": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "success_triggered": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "contact_triggered": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "contact_after_phase_triggered": torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device),
            "call_count": torch.zeros((), device=task_env.device),
        }
        setattr(task_env, "_eval_terminal_hold_state", state)
    return state


def _reset_hold_state(task_env, env_mask: torch.Tensor) -> None:
    state = getattr(task_env, "_eval_terminal_hold_state", None)
    if not isinstance(state, dict):
        return
    mask = env_mask.to(device=task_env.device, dtype=torch.bool).reshape(-1)
    if mask.numel() != task_env.num_envs or not bool(mask.any()):
        return
    state["active"][mask] = False
    state["target_pos_local"][mask] = 0.0
    state["trigger_ee_cube_offset_local"][mask] = 0.0
    state["trigger_step"][mask] = -1.0
    for name in (
        "phase_triggered",
        "lift_triggered",
        "success_triggered",
        "contact_triggered",
        "contact_after_phase_triggered",
    ):
        state[name][mask] = False


def _hold_actions_from_source(task_env, base_actions: torch.Tensor) -> tuple[torch.Tensor, dict[str, float | None]]:
    """Apply terminal hold to a pre-hold reference/mixed action stream."""

    if not hasattr(task_env, "cube_pos"):
        raise ValueError("terminal hold action sources require cube task metrics.")
    if hasattr(task_env, "_compute_intermediate_values"):
        task_env._compute_intermediate_values()

    state = _ensure_hold_state(task_env)
    state["call_count"] += 1.0

    phase = _env_tensor(task_env, "traj_phase_progress")
    lift_height = _env_tensor(task_env, "cube_lift_height")
    success = _env_tensor(task_env, "in_success_region")
    max_finger_dist = _env_tensor(task_env, "max_finger_to_cube_dist", default=math.inf)

    phase_trigger = phase >= float(args_cli.hold_phase_start)
    lift_trigger = lift_height >= float(args_cli.hold_trigger_lift_height)
    success_trigger = success >= 0.5
    contact_trigger = max_finger_dist <= float(args_cli.hold_contact_max_finger_dist)
    contact_after_phase_trigger = phase_trigger & contact_trigger
    if args_cli.hold_trigger_mode == "any":
        trigger = phase_trigger | lift_trigger | success_trigger | contact_trigger
    elif args_cli.hold_trigger_mode == "contact_after_phase_or_lift_success":
        trigger = contact_after_phase_trigger | lift_trigger | success_trigger
    elif args_cli.hold_trigger_mode == "lift_success_only":
        trigger = lift_trigger | success_trigger
    else:
        raise ValueError(f"Unsupported hold_trigger_mode: {args_cli.hold_trigger_mode}")
    new_hold = (~state["active"]) & trigger

    cube_pos = getattr(task_env, "cube_pos").detach().clone()
    ee_pos = getattr(task_env, "ee_pos", cube_pos).detach().clone()
    if bool(new_hold.any()):
        trigger_offset = ee_pos - cube_pos
        state["trigger_ee_cube_offset_local"][new_hold] = trigger_offset[new_hold]
        target_pos = cube_pos.clone()
        target_pos[:, 2] = torch.maximum(
            cube_pos[:, 2] + float(args_cli.hold_lift_height),
            ee_pos[:, 2],
        )
        state["target_pos_local"][new_hold] = target_pos[new_hold]
        state["trigger_step"][new_hold] = state["call_count"]
        state["phase_triggered"] |= new_hold & phase_trigger
        state["lift_triggered"] |= new_hold & lift_trigger
        state["success_triggered"] |= new_hold & success_trigger
        state["contact_triggered"] |= new_hold & contact_trigger
        state["contact_after_phase_triggered"] |= new_hold & contact_after_phase_trigger
        state["active"] |= new_hold

    target_pos_local = state["target_pos_local"]
    if args_cli.hold_target_policy == "cube_current_plus_trigger_ee_offset":
        dynamic_target_pos = cube_pos + state["trigger_ee_cube_offset_local"]
        dynamic_target_pos[:, 2] = dynamic_target_pos[:, 2] + float(args_cli.hold_lift_height)
        target_pos_local = torch.where(state["active"].unsqueeze(-1), dynamic_target_pos, target_pos_local)
        state["target_pos_local"][state["active"]] = target_pos_local[state["active"]]

    hold_actions = _delta_actions_to_local_targets(
        task_env,
        target_pos_local,
        gripper_action=float(args_cli.hold_gripper_action),
    )
    active = state["active"].unsqueeze(-1)
    applied_actions = torch.where(active, hold_actions, base_actions)

    metrics: dict[str, float | None] = {
        "hold_trigger_mode_id": (
            1.0
            if args_cli.hold_trigger_mode == "contact_after_phase_or_lift_success"
            else 2.0
            if args_cli.hold_trigger_mode == "lift_success_only"
            else 0.0
        ),
        "hold_phase_start": float(args_cli.hold_phase_start),
        "hold_trigger_lift_height": float(args_cli.hold_trigger_lift_height),
        "hold_contact_max_finger_dist": float(args_cli.hold_contact_max_finger_dist),
        "hold_lift_height": float(args_cli.hold_lift_height),
        "hold_gripper_action": float(args_cli.hold_gripper_action),
        "hold_target_policy_id": 1.0 if args_cli.hold_target_policy == "cube_current_plus_trigger_ee_offset" else 0.0,
        "hold_active_rate": _mean_float(state["active"].float()),
        "hold_new_trigger_rate": _mean_float(new_hold.float()),
        "hold_phase_trigger_rate": _mean_float(state["phase_triggered"].float()),
        "hold_lift_trigger_rate": _mean_float(state["lift_triggered"].float()),
        "hold_success_trigger_rate": _mean_float(state["success_triggered"].float()),
        "hold_contact_trigger_rate": _mean_float(state["contact_triggered"].float()),
        "hold_contact_after_phase_trigger_rate": _mean_float(state["contact_after_phase_triggered"].float()),
    }
    triggered_steps = state["trigger_step"][state["trigger_step"] >= 0.0]
    if triggered_steps.numel() > 0:
        metrics["hold_trigger_step_mean"] = _mean_float(triggered_steps)
        metrics["hold_trigger_step_min"] = _tensor_stat_float(triggered_steps, "min")
        metrics["hold_trigger_step_max"] = _tensor_stat_float(triggered_steps, "max")
    _add_vector_metrics(metrics, "hold_target_pos", state["target_pos_local"], ("x", "y", "z"))
    _add_vector_metrics(
        metrics,
        "hold_trigger_ee_cube_offset",
        state["trigger_ee_cube_offset_local"],
        ("x", "y", "z"),
    )
    _add_action_signal_metrics(metrics, "hold_action", hold_actions)
    _add_action_signal_metrics(metrics, "hold_applied_action", applied_actions)
    _add_action_delta_metrics(metrics, "hold_reference_action_error", hold_actions, base_actions)
    _add_action_delta_metrics(metrics, "applied_reference_action_error", applied_actions, base_actions)
    return applied_actions, metrics


def _policy_obs_tensor(agent: BasePlayer, obs) -> torch.Tensor:
    obs_t = agent.obs_to_torch(obs)
    if isinstance(obs_t, dict):
        if "obs" in obs_t:
            obs_t = obs_t["obs"]
        elif "policy" in obs_t:
            obs_t = obs_t["policy"]
        else:
            raise TypeError(f"Unsupported policy observation dict keys: {sorted(obs_t.keys())}")
    if not isinstance(obs_t, torch.Tensor):
        obs_t = torch.as_tensor(obs_t, device=agent.device, dtype=torch.float32)
    return obs_t.detach().float()


def _residual_context_tensor(
    residual_adapter,
    task_env,
    *,
    device: torch.device,
    batch_size: int,
    teacher_alpha: float,
) -> torch.Tensor | None:
    context_dim = int(getattr(residual_adapter, "context_dim", 0))
    if context_dim <= 0:
        return None
    features = list(getattr(residual_adapter, "context_features", ()) or ())
    if len(features) != context_dim:
        raise ValueError(f"Residual adapter context metadata mismatch: dim={context_dim}, features={features}")
    values = []
    for feature in features:
        if feature == "phase":
            phase = getattr(task_env, "traj_phase_progress", torch.zeros(batch_size, device=device))
            values.append(phase.to(device=device, dtype=torch.float32).view(-1, 1).clamp(0.0, 1.0))
        elif feature == "teacher_alpha":
            values.append(torch.full((batch_size, 1), float(teacher_alpha), dtype=torch.float32, device=device))
        else:
            raise ValueError(f"Unsupported residual context feature {feature!r}")
    return torch.cat(values, dim=-1)


def _policy_action_components(
    agent: BasePlayer | None,
    task_env,
    obs,
    *,
    teacher_alpha: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None, torch.Tensor | None]:
    if agent is None:
        raise ValueError("policy action source requires an RL-Games player.")
    obs_t = agent.obs_to_torch(obs)
    base_action = agent.get_action(obs_t, is_deterministic=args_cli.deterministic).detach().float()
    residual_adapter = getattr(agent, "_bc_residual_action_adapter", None)
    if residual_adapter is None:
        return base_action, base_action, None, None
    obs_tensor = _policy_obs_tensor(agent, obs)
    residual_context = _residual_context_tensor(
        residual_adapter,
        task_env,
        device=base_action.device,
        batch_size=obs_tensor.shape[0],
        teacher_alpha=teacher_alpha,
    )
    residual = residual_adapter(obs_tensor, residual_context).detach().float().to(device=base_action.device)
    residual_gate = None
    if hasattr(residual_adapter, "gate_values"):
        residual_gate = residual_adapter.gate_values(obs_tensor, residual_context).detach().float().to(device=base_action.device)
    final_action = torch.clamp(base_action + residual, -1.0, 1.0)
    return final_action, base_action, residual, residual_gate


def _add_policy_component_metrics(
    metrics: dict[str, float | None],
    final_actions: torch.Tensor,
    base_actions: torch.Tensor,
    residual_actions: torch.Tensor | None,
    residual_gate: torch.Tensor | None,
) -> None:
    _add_action_signal_metrics(metrics, "raw_policy_action", final_actions)
    if residual_actions is None:
        return
    metrics["residual_adapter_enabled"] = 1.0
    _add_action_signal_metrics(metrics, "base_policy_action", base_actions)
    _add_action_signal_metrics(metrics, "residual_policy_action", residual_actions)
    _add_action_delta_metrics(metrics, "residual_final_base_action_error", final_actions, base_actions)
    if isinstance(residual_gate, torch.Tensor):
        metrics["residual_gate_mean"] = _mean_float(residual_gate)
        metrics["residual_gate_min"] = _tensor_stat_float(residual_gate, "min")
        metrics["residual_gate_max"] = _tensor_stat_float(residual_gate, "max")


def _reference_mix_override_alpha(value: float | None, default_alpha: float) -> float:
    if value is None:
        return default_alpha
    return max(0.0, min(1.0, float(value)))


def _mix_policy_reference_actions(
    raw_policy_actions: torch.Tensor,
    reference_actions: torch.Tensor,
    *,
    alpha: float,
    z_alpha: float,
    gripper_alpha: float,
) -> torch.Tensor:
    mixed_actions = torch.clamp((1.0 - alpha) * raw_policy_actions + alpha * reference_actions, -1.0, 1.0)
    if mixed_actions.shape[-1] >= 3 and z_alpha != alpha:
        mixed_actions[:, 2] = torch.clamp(
            (1.0 - z_alpha) * raw_policy_actions[:, 2] + z_alpha * reference_actions[:, 2],
            -1.0,
            1.0,
        )
    if mixed_actions.shape[-1] >= 7 and gripper_alpha != alpha:
        mixed_actions[:, 6] = torch.clamp(
            (1.0 - gripper_alpha) * raw_policy_actions[:, 6] + gripper_alpha * reference_actions[:, 6],
            -1.0,
            1.0,
        )
    return mixed_actions


def _actions_from_source(
    action_source: str,
    task_env,
    agent: BasePlayer | None,
    obs,
) -> tuple[torch.Tensor, dict[str, float | None]]:
    metrics: dict[str, float | None] = {}
    if action_source == "policy":
        raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate = _policy_action_components(
            agent,
            task_env,
            obs,
            teacher_alpha=float(args_cli.reference_mix_alpha),
        )
        _add_policy_component_metrics(metrics, raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate)
        return raw_policy_actions, metrics
    if action_source == "zero":
        actions = _zero_actions(task_env)
        return actions, metrics
    if action_source == "reference_delta":
        reference_actions = _reference_delta_actions(task_env)
        _add_action_signal_metrics(metrics, "reference_delta_action", reference_actions)
        return reference_actions, metrics
    if action_source == "reference_delta_hold":
        reference_actions = _reference_delta_actions(task_env)
        _add_action_signal_metrics(metrics, "reference_delta_action", reference_actions)
        applied_actions, hold_metrics = _hold_actions_from_source(task_env, reference_actions)
        metrics.update(hold_metrics)
        return applied_actions, metrics
    if action_source == "policy_reference_mix":
        reference_actions = _reference_delta_actions(task_env)
        alpha = max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
        z_alpha = _reference_mix_override_alpha(args_cli.reference_mix_z_alpha, alpha)
        gripper_alpha = _reference_mix_override_alpha(args_cli.reference_mix_gripper_alpha, alpha)
        raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate = _policy_action_components(
            agent,
            task_env,
            obs,
            teacher_alpha=alpha,
        )
        mixed_actions = _mix_policy_reference_actions(
            raw_policy_actions,
            reference_actions,
            alpha=alpha,
            z_alpha=z_alpha,
            gripper_alpha=gripper_alpha,
        )
        metrics["reference_mix_alpha"] = alpha
        metrics["reference_mix_z_alpha"] = z_alpha
        metrics["reference_mix_gripper_alpha"] = gripper_alpha
        _add_policy_component_metrics(metrics, raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate)
        _add_action_signal_metrics(metrics, "reference_delta_action", reference_actions)
        _add_action_signal_metrics(metrics, "mixed_action", mixed_actions)
        _add_action_delta_metrics(metrics, "policy_reference_action_error", raw_policy_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_reference_action_error", mixed_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_policy_action_error", mixed_actions, raw_policy_actions)
        return mixed_actions, metrics
    if action_source == "policy_reference_mix_hold":
        reference_actions = _reference_delta_actions(task_env)
        alpha = max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
        z_alpha = _reference_mix_override_alpha(args_cli.reference_mix_z_alpha, alpha)
        gripper_alpha = _reference_mix_override_alpha(args_cli.reference_mix_gripper_alpha, alpha)
        raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate = _policy_action_components(
            agent,
            task_env,
            obs,
            teacher_alpha=alpha,
        )
        mixed_actions = _mix_policy_reference_actions(
            raw_policy_actions,
            reference_actions,
            alpha=alpha,
            z_alpha=z_alpha,
            gripper_alpha=gripper_alpha,
        )
        metrics["reference_mix_alpha"] = alpha
        metrics["reference_mix_z_alpha"] = z_alpha
        metrics["reference_mix_gripper_alpha"] = gripper_alpha
        _add_policy_component_metrics(metrics, raw_policy_actions, base_policy_actions, residual_policy_actions, residual_gate)
        _add_action_signal_metrics(metrics, "reference_delta_action", reference_actions)
        _add_action_signal_metrics(metrics, "mixed_action", mixed_actions)
        _add_action_delta_metrics(metrics, "policy_reference_action_error", raw_policy_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_reference_action_error", mixed_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_policy_action_error", mixed_actions, raw_policy_actions)
        applied_actions, hold_metrics = _hold_actions_from_source(task_env, mixed_actions)
        metrics.update(hold_metrics)
        return applied_actions, metrics
    raise ValueError(f"Unsupported action source: {action_source}")


def _trajectory_tracking_reference_summary(task_env) -> dict | None:
    if not hasattr(task_env, "trajectory_tracking_reference_summary"):
        return None
    try:
        return task_env.trajectory_tracking_reference_summary()
    except Exception as exc:
        return {"error": str(exc)}


def _collect_episode_probe_metrics(task_env, num_envs: int) -> dict[str, list[float]]:
    metric_sources = {
        "success_rate": "in_success_region",
        "time_in_success_region": "time_in_success_region",
        "cube_lift_height": "cube_lift_height",
        "has_lifted_cube": "has_lifted_cube",
        "ee_to_cube_dist": "ee_to_cube_dist",
        "finger_center_to_cube_dist": "finger_center_to_cube_dist",
        "gripper_width": "gripper_width",
    }
    metrics: dict[str, list[float]] = {}
    for output_name, source_name in metric_sources.items():
        values = _env_metric_values(task_env, source_name, expected_len=num_envs)
        if values is not None:
            metrics[output_name] = values
    return metrics


def _empty_episode_stats(start_step: int) -> dict[str, float | int | None]:
    return {
        "start_step": int(start_step),
        "max_success_rate": None,
        "max_time_in_success_region": None,
        "max_cube_lift_height": None,
        "max_has_lifted_cube": None,
        "min_ee_to_cube_dist": None,
        "min_finger_center_to_cube_dist": None,
        "min_gripper_width": None,
    }


def _update_episode_stats(
    stats: dict[str, float | int | None], probe_metrics: dict[str, list[float]], env_idx: int
) -> None:
    max_fields = {
        "success_rate": "max_success_rate",
        "time_in_success_region": "max_time_in_success_region",
        "cube_lift_height": "max_cube_lift_height",
        "has_lifted_cube": "max_has_lifted_cube",
    }
    min_fields = {
        "ee_to_cube_dist": "min_ee_to_cube_dist",
        "finger_center_to_cube_dist": "min_finger_center_to_cube_dist",
        "gripper_width": "min_gripper_width",
    }
    for source_name, stat_name in max_fields.items():
        values = probe_metrics.get(source_name)
        if values is None:
            continue
        value = values[env_idx]
        current = stats.get(stat_name)
        stats[stat_name] = value if current is None else max(float(current), value)
    for source_name, stat_name in min_fields.items():
        values = probe_metrics.get(source_name)
        if values is None:
            continue
        value = values[env_idx]
        current = stats.get(stat_name)
        stats[stat_name] = value if current is None else min(float(current), value)


def _episode_metric_value(probe_metrics: dict[str, list[float]], metric_name: str, env_idx: int) -> float | None:
    values = probe_metrics.get(metric_name)
    if values is None:
        return None
    return float(values[env_idx])


def _finish_episode_outcome(
    *,
    env_idx: int,
    episode_id: int,
    terminal_step: int,
    stats: dict[str, float | int | None],
    terminal_probe_metrics: dict[str, list[float]],
    terminal_source: str = "pre_done_state",
) -> dict[str, float | int | bool | None]:
    terminal_success = _episode_metric_value(terminal_probe_metrics, "success_rate", env_idx)
    terminal_success_time = _episode_metric_value(terminal_probe_metrics, "time_in_success_region", env_idx)
    terminal_lift = _episode_metric_value(terminal_probe_metrics, "cube_lift_height", env_idx)
    terminal_has_lifted = _episode_metric_value(terminal_probe_metrics, "has_lifted_cube", env_idx)
    max_success = stats.get("max_success_rate")
    max_lifted = stats.get("max_has_lifted_cube")
    return {
        "env_idx": int(env_idx),
        "episode_id": int(episode_id),
        "start_step": int(stats["start_step"]) if stats.get("start_step") is not None else None,
        "terminal_step": int(terminal_step),
        "terminal_source": terminal_source,
        "terminal_success_rate": terminal_success,
        "terminal_time_in_success_region": terminal_success_time,
        "terminal_cube_lift_height": terminal_lift,
        "terminal_has_lifted_cube": terminal_has_lifted,
        "terminal_ee_to_cube_dist": _episode_metric_value(terminal_probe_metrics, "ee_to_cube_dist", env_idx),
        "terminal_finger_center_to_cube_dist": _episode_metric_value(
            terminal_probe_metrics, "finger_center_to_cube_dist", env_idx
        ),
        "terminal_gripper_width": _episode_metric_value(terminal_probe_metrics, "gripper_width", env_idx),
        **{key: value for key, value in stats.items() if key != "start_step"},
        "success": bool(max_success is not None and float(max_success) >= 0.5),
        "lifted": bool(max_lifted is not None and float(max_lifted) >= 0.5),
    }


def _collect_action_metrics(actions: torch.Tensor) -> dict[str, float | None]:
    if not isinstance(actions, torch.Tensor):
        return {}
    action_cpu = actions.detach().float().cpu()
    flat = action_cpu.flatten()
    metrics: dict[str, float | None] = {
        "action_mean": float(flat.mean()),
        "action_abs_mean": float(flat.abs().mean()),
        "action_min": float(flat.min()),
        "action_max": float(flat.max()),
    }
    if action_cpu.ndim >= 2 and action_cpu.shape[0] > 0:
        first = action_cpu[0]
        for idx, value in enumerate(first.tolist()):
            metrics[f"action_env0_{idx}"] = float(value)
        if first.numel() > 6:
            metrics["gripper_action_env0"] = float(first[6])
    return metrics


def _summarize_step_metrics(step_metrics: list[dict[str, float | int | None]]) -> dict[str, dict[str, float | int]]:
    summaries: dict[str, dict[str, float | int]] = {}
    for name in sorted({key for item in step_metrics for key in item.keys()} - {"step"}):
        records = [(item, float(item[name])) for item in step_metrics if item.get(name) is not None]
        if not records:
            continue
        float_values = [value for _, value in records]
        max_idx = max(range(len(float_values)), key=lambda idx: float_values[idx])
        min_idx = min(range(len(float_values)), key=lambda idx: float_values[idx])
        summaries[name] = {
            "final": float_values[-1],
            "max": float_values[max_idx],
            "max_step": int(records[max_idx][0]["step"]),
            "min": float_values[min_idx],
            "min_step": int(records[min_idx][0]["step"]),
            "mean": sum(float_values) / len(float_values),
        }
    return summaries


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _first_done_step(step_metrics: list[dict[str, float | int | None]]) -> int | None:
    for item in step_metrics:
        done_count = item.get("done_count_step")
        if done_count is not None and int(done_count) > 0:
            return int(item["step"])
    return None


def _summarize_episode_outcomes(
    outcomes: list[dict[str, float | int | bool | None]],
    *,
    success_hold_time_threshold: float | None = None,
) -> dict[str, float | int | None]:
    if not outcomes:
        return {
            "count": 0,
            "success_rate": None,
            "terminal_success_rate": None,
            "lifted_rate": None,
            "success_hold_time_threshold": success_hold_time_threshold,
            "success_hold_rate": None,
            "max_lift_mean": None,
            "max_lift_min": None,
            "max_lift_max": None,
            "max_time_in_success_region_mean": None,
            "max_time_in_success_region_max": None,
            "terminal_success_rate_mean": None,
            "terminal_time_in_success_region_mean": None,
            "terminal_lift_mean": None,
        }
    success_values = [1.0 if outcome.get("success") else 0.0 for outcome in outcomes]
    terminal_success_values = [
        1.0 if float(outcome["terminal_success_rate"]) >= 0.5 else 0.0
        for outcome in outcomes
        if outcome.get("terminal_success_rate") is not None
    ]
    lifted_values = [1.0 if outcome.get("lifted") else 0.0 for outcome in outcomes]
    success_hold_values = [
        1.0 if float(outcome["max_time_in_success_region"]) >= float(success_hold_time_threshold) else 0.0
        for outcome in outcomes
        if success_hold_time_threshold is not None and outcome.get("max_time_in_success_region") is not None
    ]
    max_lifts = [
        float(outcome["max_cube_lift_height"])
        for outcome in outcomes
        if outcome.get("max_cube_lift_height") is not None
    ]
    max_success_times = [
        float(outcome["max_time_in_success_region"])
        for outcome in outcomes
        if outcome.get("max_time_in_success_region") is not None
    ]
    terminal_success = [
        float(outcome["terminal_success_rate"])
        for outcome in outcomes
        if outcome.get("terminal_success_rate") is not None
    ]
    terminal_success_times = [
        float(outcome["terminal_time_in_success_region"])
        for outcome in outcomes
        if outcome.get("terminal_time_in_success_region") is not None
    ]
    terminal_lifts = [
        float(outcome["terminal_cube_lift_height"])
        for outcome in outcomes
        if outcome.get("terminal_cube_lift_height") is not None
    ]
    return {
        "count": len(outcomes),
        "success_rate": _mean(success_values),
        "terminal_success_rate": _mean(terminal_success_values),
        "lifted_rate": _mean(lifted_values),
        "success_hold_time_threshold": success_hold_time_threshold,
        "success_hold_rate": _mean(success_hold_values),
        "max_lift_mean": _mean(max_lifts),
        "max_lift_min": min(max_lifts) if max_lifts else None,
        "max_lift_max": max(max_lifts) if max_lifts else None,
        "max_time_in_success_region_mean": _mean(max_success_times),
        "max_time_in_success_region_max": max(max_success_times) if max_success_times else None,
        "terminal_success_rate_mean": _mean(terminal_success),
        "terminal_time_in_success_region_mean": _mean(terminal_success_times),
        "terminal_lift_mean": _mean(terminal_lifts),
    }


def _filter_first_attempt_outcomes(
    completed_outcomes: list[dict[str, float | int | bool | None]],
    horizon_outcomes: list[dict[str, float | int | bool | None]],
    num_envs: int,
) -> list[dict[str, float | int | bool | None]]:
    """Return exactly one initial-attempt outcome per env when available."""
    by_env: dict[int, dict[str, float | int | bool | None]] = {}
    for outcome in horizon_outcomes:
        if int(outcome.get("episode_id", -1)) == 0:
            by_env[int(outcome["env_idx"])] = outcome
    for outcome in completed_outcomes:
        if int(outcome.get("episode_id", -1)) == 0:
            by_env[int(outcome["env_idx"])] = outcome
    return [by_env[env_idx] for env_idx in range(num_envs) if env_idx in by_env]


def _write_trace_artifacts(
    step_metrics: list[dict[str, float | int | None]],
    trace_csv_path: Path,
    trace_jsonl_path: Path,
) -> None:
    trace_csv_path.parent.mkdir(parents=True, exist_ok=True)
    trace_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for item in step_metrics for key in item.keys()})
    with trace_csv_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in step_metrics:
            writer.writerow(item)
    with trace_jsonl_path.open("w") as jsonl_file:
        for item in step_metrics:
            jsonl_file.write(json.dumps(item, sort_keys=True) + "\n")


def _fixed_window_summaries(
    step_metrics: list[dict[str, float | int | None]],
    window_size: int,
) -> dict[str, dict[str, object]]:
    if not step_metrics:
        return {}
    count = len(step_metrics)
    size = max(1, min(int(window_size), count))
    spans = {
        "first": (0, size),
        "middle": (max((count - size) // 2, 0), max((count - size) // 2, 0) + size),
        "last": (count - size, count),
    }
    summaries: dict[str, dict[str, object]] = {}
    for name, (start, end) in spans.items():
        rows = step_metrics[start:end]
        summaries[name] = {
            "start_step": int(rows[0]["step"]),
            "end_step": int(rows[-1]["step"]),
            "num_steps": len(rows),
            "metric_summaries": _summarize_step_metrics(rows),
        }
    return summaries


def _env_config_summary(env_cfg, task_env) -> dict[str, object]:
    cfg = getattr(task_env, "cfg", env_cfg)
    keys = [
        "observation_space",
        "num_observations",
        "state_space",
        "num_states",
        "action_space",
        "num_actions",
        "cube_spawn_xy_randomization",
        "cube_approach_weight",
        "cube_enclosure_weight",
        "cube_lift_weight",
        "cube_height_tracking_weight",
        "cube_xy_stability_weight",
        "cube_success_bonus_weight",
        "cube_close_action_weight",
        "cube_lift_action_weight",
        "cube_descend_action_penalty_weight",
        "cube_table_clearance_penalty_weight",
        "cube_gripper_close_reg_weight",
        "cube_action_penalty_weight",
        "trajectory_tracking_enabled",
        "trajectory_tracking_reference_path",
        "trajectory_tracking_reference_duration_s",
        "trajectory_tracking_phase_observations",
        "trajectory_tracking_position_weight",
        "trajectory_tracking_position_sharpness",
        "trajectory_tracking_orientation_weight",
        "trajectory_tracking_orientation_sharpness",
        "trajectory_tracking_gripper_weight",
        "trajectory_tracking_gripper_sharpness",
        "trajectory_tracking_close_action_weight",
        "trajectory_tracking_lift_action_weight",
        "trajectory_tracking_start_weight",
        "trajectory_tracking_end_weight",
        "trajectory_tracking_contact_gate_max_finger_dist",
        "trajectory_tracking_contact_gate_width",
        "trajectory_tracking_reference_reweight_phase_start",
        "trajectory_tracking_reference_late_weight_scale",
        "trajectory_tracking_min_target_gripper_width",
        "trajectory_tracking_action_alignment_weight",
        "trajectory_tracking_action_alignment_phase_start",
        "trajectory_tracking_action_alignment_sharpness",
        "trajectory_tracking_action_alignment_use_contact_gate",
        "trajectory_tracking_action_alignment_include_xy",
        "trajectory_tracking_action_alignment_include_z",
        "trajectory_tracking_action_alignment_include_gripper",
        "trajectory_tracking_teacher_force_enabled",
        "trajectory_tracking_teacher_force_alpha_start",
        "trajectory_tracking_teacher_force_alpha_end",
        "trajectory_tracking_teacher_force_phase_end",
        "trajectory_tracking_teacher_force_anneal_steps",
        "trajectory_tracking_action_alignment_compare_raw_policy",
        "trajectory_tracking_min_target_table_clearance",
        "trajectory_tracking_follow_current_cube_pose",
    ]
    summary = {
        "scene_num_envs": int(getattr(env_cfg.scene, "num_envs", 0)),
        "seed": getattr(env_cfg, "seed", None),
        "sim_device": getattr(env_cfg.sim, "device", None),
        "physics_dt": float(getattr(env_cfg.sim, "dt", 0.0)),
        "env_dt": float(getattr(cfg, "decimation", 1)) * float(getattr(env_cfg.sim, "dt", 0.0)),
        "episode_length_s": float(getattr(cfg, "episode_length_s", 0.0)),
    }
    for key in keys:
        if hasattr(cfg, key):
            value = getattr(cfg, key)
            if isinstance(value, (str, bool, int, float)) or value is None:
                summary[key] = value
    return summary


def _checkpoint_path(agent_cfg: dict) -> str:
    log_root_path = os.path.abspath(os.path.join("logs", "rl_games", agent_cfg["params"]["config"]["name"]))
    print(f"[INFO] Loading experiment from directory: {log_root_path}")
    if args_cli.checkpoint is not None:
        return retrieve_file_path(args_cli.checkpoint)

    run_dir = agent_cfg["params"]["config"].get("full_experiment_name", ".*")
    checkpoint_file = ".*" if args_cli.use_last_checkpoint else f"{agent_cfg['params']['config']['name']}.pth"
    return get_checkpoint_path(log_root_path, run_dir, checkpoint_file, other_dirs=["nn"])


def _latest_video_files(video_folder: Path | None) -> list[str]:
    if video_folder is None or not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _write_trace_files(
    step_metrics: list[dict[str, float | int | None]],
    *,
    trace_jsonl_path: Path,
    trace_csv_path: Path,
) -> None:
    trace_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_jsonl_path.open("w", encoding="utf-8") as f:
        for record in step_metrics:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    trace_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for record in step_metrics for key in record.keys()})
    if "step" in fieldnames:
        fieldnames.remove("step")
        fieldnames.insert(0, "step")
    with trace_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in step_metrics:
            writer.writerow(record)


def _camera_tuple(values: list[float] | tuple[float, float, float] | None):
    if values is None:
        return None
    return tuple(float(v) for v in values)


def _configure_eval_camera(env_cfg, task_env=None) -> None:
    if args_cli.camera_eye is None and args_cli.camera_target is None:
        return
    if not hasattr(env_cfg, "viewer"):
        print("[WARN] Environment config has no viewer config; eval camera override skipped.")
        return

    eye = _camera_tuple(args_cli.camera_eye) or tuple(env_cfg.viewer.eye)
    target = _camera_tuple(args_cli.camera_target) or tuple(env_cfg.viewer.lookat)
    camera_env_index = max(0, int(args_cli.camera_env_index))
    if task_env is not None and hasattr(task_env, "scene") and len(task_env.scene.env_origins) > 0:
        origin_count = len(task_env.scene.env_origins)
        if camera_env_index >= origin_count:
            print(
                f"[WARN] Requested camera_env_index={camera_env_index}, "
                f"but only {origin_count} env origins exist; using env0."
            )
            camera_env_index = 0
        env_origin = task_env.scene.env_origins[camera_env_index].detach().cpu().tolist()
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    print(f"[INFO] Eval video camera_env_index={camera_env_index} eye={eye} target={target}")

    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set active viewport camera: {exc}")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    """Run checkpoint evaluation."""

    output_dir = Path(args_cli.output_dir or datetime.now().strftime("eval_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    trace_csv_path = (
        Path(args_cli.trace_csv_path).expanduser().resolve()
        if args_cli.trace_csv_path
        else output_dir / "trace.csv"
    )
    trace_jsonl_path = (
        Path(args_cli.trace_jsonl_path).expanduser().resolve()
        if args_cli.trace_jsonl_path
        else output_dir / "trace.jsonl"
    )
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    env_cfg.scene.num_envs = args_cli.num_envs if args_cli.num_envs is not None else env_cfg.scene.num_envs
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    if args_cli.seed is not None:
        env_cfg.seed = args_cli.seed
        agent_cfg["params"]["seed"] = args_cli.seed
    _configure_eval_camera(env_cfg)

    resume_path = None
    if args_cli.action_source in POLICY_ACTION_SOURCES:
        resume_path = _checkpoint_path(agent_cfg)
        agent_cfg["params"]["load_checkpoint"] = True
        agent_cfg["params"]["load_path"] = resume_path
        print(f"[INFO]: Loading model checkpoint from: {agent_cfg['params']['load_path']}")
    elif args_cli.checkpoint:
        resume_path = retrieve_file_path(args_cli.checkpoint)
        print(f"[INFO]: Non-policy action source will not restore checkpoint: {resume_path}")

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    success_termination_suppression_installed = False
    if args_cli.suppress_success_termination:
        success_termination_suppression_installed = _install_success_termination_suppression(task_env)
        if success_termination_suppression_installed:
            print("[INFO] Eval-only success termination suppression is active.")
        else:
            print("[WARN] Requested success termination suppression, but this env does not expose success_timeout.")
    trajectory_tracking_reference = _trajectory_tracking_reference_summary(task_env)
    _configure_eval_camera(env_cfg, task_env)

    if args_cli.video:
        video_kwargs = {
            "video_folder": str(video_folder),
            "step_trigger": lambda step: step == 0,
            "video_length": min(args_cli.video_length, args_cli.num_steps),
            "name_prefix": args_cli.video_name_prefix,
            "disable_logger": True,
        }
        print("[INFO] Recording rollout video.")
        print_dict(video_kwargs, nesting=4)
        gym_env = gym.wrappers.RecordVideo(gym_env, **video_kwargs)

    agent: BasePlayer | None = None
    residual_adapter_summary: dict[str, object] | None = None
    if args_cli.action_source in POLICY_ACTION_SOURCES:
        rl_device = agent_cfg["params"]["config"]["device"]
        clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
        clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)
        env = RlGamesVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

        vecenv.register(
            "IsaacRlgWrapper", lambda config_name, num_actors, **kwargs: RlGamesGpuEnv(config_name, num_actors, **kwargs)
        )
        env_configurations.register("rlgpu", {"vecenv_type": "IsaacRlgWrapper", "env_creator": lambda **kwargs: env})

        agent_cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
        runner = Runner()
        runner.load(agent_cfg)
        agent = runner.create_player()
        agent.restore(resume_path)
        agent.reset()
        ckpt = torch_ext.load_checkpoint(resume_path)
        residual_metadata = ckpt.get("bc_residual_action_adapter") if isinstance(ckpt, dict) else None
        if isinstance(residual_metadata, dict):
            residual_adapter = build_residual_adapter_from_metadata(residual_metadata).to(device=agent.device)
            residual_adapter.eval()
            setattr(agent, "_bc_residual_action_adapter", residual_adapter)
            residual_adapter_summary = {
                key: value
                for key, value in residual_metadata.items()
                if key != "state_dict"
            }
            print("[INFO] Loaded BC residual action adapter:")
            print(json.dumps(residual_adapter_summary, indent=2, sort_keys=True))
    else:
        env = gym_env

    step_metrics = []
    done_count = 0
    success_ever_env = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    first_success_step = torch.full((task_env.num_envs,), -1.0, device=task_env.device)
    last_success_step = torch.full((task_env.num_envs,), -1.0, device=task_env.device)
    done_ever_env = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    first_done_step = torch.full((task_env.num_envs,), -1.0, device=task_env.device)
    done_after_success_env = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    suppressed_success_done_ever_env = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    first_suppressed_success_done_step = torch.full((task_env.num_envs,), -1.0, device=task_env.device)
    final_success_env = torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)
    final_lift_height_env = torch.zeros(task_env.num_envs, device=task_env.device)
    max_lift_height_env = torch.zeros(task_env.num_envs, device=task_env.device)
    done_reason_counts = {
        "success_done": 0,
        "cube_out": 0,
        "prelift_drag": 0,
        "finger_table_penetration": 0,
        "truncated": 0,
        "done_after_success_unclassified": 0,
        "unclassified": 0,
    }
    done_events: list[dict[str, object]] = []
    env_closed = False
    num_envs = 0
    horizon_episode_outcomes: list[dict[str, float | int | bool | None]] = []
    try:
        obs = env.reset()
        if isinstance(obs, tuple):
            obs = obs[0]
        if args_cli.action_source in POLICY_ACTION_SOURCES and isinstance(obs, dict):
            obs = obs["obs"]
        if agent is not None:
            _ = agent.get_batch_size(obs, 1)
            if agent.is_rnn:
                agent.init_rnn()

        num_envs = int(env.unwrapped.num_envs)
        episode_ids = [0 for _ in range(num_envs)]
        episode_stats = [_empty_episode_stats(start_step=1) for _ in range(num_envs)]
        completed_episode_outcomes: list[dict[str, float | int | bool | None]] = []

        for step in range(args_cli.num_steps):
            if not simulation_app.is_running():
                break

            with torch.inference_mode():
                pre_step_episode_probe_metrics = _collect_episode_probe_metrics(task_env, num_envs)
                for env_idx in range(num_envs):
                    _update_episode_stats(episode_stats[env_idx], pre_step_episode_probe_metrics, env_idx)

                actions, action_source_metrics = _actions_from_source(args_cli.action_source, task_env, agent, obs)
                pre_step_done_reasons = _done_reason_snapshot(task_env)
                step_out = env.step(actions)
                if len(step_out) == 5:
                    obs, rewards, terminated, truncated, _ = step_out
                    dones = torch.logical_or(terminated, truncated)
                else:
                    obs, rewards, dones, _ = step_out
                    terminated = None
                    truncated = None

                if args_cli.action_source in POLICY_ACTION_SOURCES and isinstance(obs, dict):
                    obs = obs["obs"]

                success_tensor = _env_bool_tensor(task_env, "in_success_region")
                reward_mean = _mean_float(rewards)
                task_metrics = _collect_task_metrics(task_env, actions)
                post_step_episode_probe_metrics = _collect_episode_probe_metrics(task_env, num_envs)
                action_metrics = _collect_action_metrics(actions)

                step_done_count = 0
                done_env_indices: set[int] = set()
                dones_bool = None
                if isinstance(dones, torch.Tensor):
                    dones_bool = dones.bool()
                    step_done_count = int(dones_bool.sum().detach().cpu())
                    done_count += step_done_count
                    success_tensor = success_tensor | (dones_bool & pre_step_done_reasons["success_region"])
                    success_tensor = success_tensor | (dones_bool & pre_step_done_reasons["success_done"])
                    if agent is not None and agent.is_rnn and agent.states is not None and dones_bool.any():
                        for state in agent.states:
                            state[:, dones_bool, :] = 0.0
                    for env_idx in torch.nonzero(dones_bool.flatten(), as_tuple=False).flatten().detach().cpu().tolist():
                        done_env_indices.add(int(env_idx))
                        completed_episode_outcomes.append(
                            _finish_episode_outcome(
                                env_idx=int(env_idx),
                                episode_id=episode_ids[int(env_idx)],
                                terminal_step=step + 1,
                                stats=episode_stats[int(env_idx)],
                                terminal_probe_metrics=pre_step_episode_probe_metrics,
                            )
                        )
                        episode_ids[int(env_idx)] += 1
                        episode_stats[int(env_idx)] = _empty_episode_stats(start_step=step + 2)
                elif dones is not None:
                    step_done_count = int(bool(dones))
                    done_count += step_done_count
                    if step_done_count > 0:
                        done_env_indices.add(0)
                        completed_episode_outcomes.append(
                            _finish_episode_outcome(
                                env_idx=0,
                                episode_id=episode_ids[0],
                                terminal_step=step + 1,
                                stats=episode_stats[0],
                                terminal_probe_metrics=pre_step_episode_probe_metrics,
                            )
                        )
                        episode_ids[0] += 1
                        episode_stats[0] = _empty_episode_stats(start_step=step + 2)

                for env_idx in range(num_envs):
                    if env_idx not in done_env_indices:
                        _update_episode_stats(episode_stats[env_idx], post_step_episode_probe_metrics, env_idx)
                lift_height_tensor = _env_tensor(task_env, "cube_lift_height")
                final_success_env = success_tensor.detach().clone()
                final_lift_height_env = lift_height_tensor.detach().clone()
                max_lift_height_env = torch.maximum(max_lift_height_env, lift_height_tensor)
                suppressed_success_done = None
                if args_cli.suppress_success_termination:
                    suppressed_success_done = pre_step_done_reasons["success_done"]
                    new_suppressed_success_done = suppressed_success_done & (~suppressed_success_done_ever_env)
                    if bool(new_suppressed_success_done.any()):
                        first_suppressed_success_done_step[new_suppressed_success_done] = float(step + 1)
                    suppressed_success_done_ever_env |= suppressed_success_done
                new_success = success_tensor & (~success_ever_env)
                if bool(new_success.any()):
                    first_success_step[new_success] = float(step + 1)
                if bool(success_tensor.any()):
                    last_success_step[success_tensor] = float(step + 1)
                success_ever_env |= success_tensor

                if dones_bool is not None and bool(dones_bool.any()):
                    new_done = dones_bool & (~done_ever_env)
                    if bool(new_done.any()):
                        first_done_step[new_done] = float(step + 1)
                    done_after_success_env |= dones_bool & success_ever_env
                    reason_names = ("success_done", "cube_out", "prelift_drag", "finger_table_penetration", "truncated")
                    classified = torch.zeros_like(dones_bool)
                    for reason_name in reason_names:
                        reason_mask = dones_bool & pre_step_done_reasons[reason_name]
                        done_reason_counts[reason_name] += int(reason_mask.sum().detach().cpu())
                        classified |= reason_mask
                    after_success_unclassified = dones_bool & (~classified) & success_ever_env
                    done_reason_counts["done_after_success_unclassified"] += int(
                        after_success_unclassified.sum().detach().cpu()
                    )
                    classified |= after_success_unclassified
                    done_reason_counts["unclassified"] += int((dones_bool & (~classified)).sum().detach().cpu())
                    for env_id in torch.nonzero(new_done, as_tuple=False).flatten().detach().cpu().tolist():
                        first_success_value = float(first_success_step[env_id].detach().cpu())
                        last_success_value = float(last_success_step[env_id].detach().cpu())
                        reasons = [
                            name
                            for name in reason_names
                            if bool(pre_step_done_reasons[name][env_id].detach().cpu())
                        ]
                        if not reasons and bool(success_ever_env[env_id].detach().cpu()):
                            reasons = ["done_after_success_unclassified"]
                        elif not reasons:
                            reasons = ["unclassified"]
                        done_events.append(
                            {
                                "env_id": int(env_id),
                                "first_done_step": int(step + 1),
                                "first_success_step": int(first_success_value) if first_success_value >= 0 else None,
                                "last_success_step": int(last_success_value) if last_success_value >= 0 else None,
                                "success_ever_before_done": bool(success_ever_env[env_id].detach().cpu()),
                                "reason_source": "pre_step_snapshot_before_auto_reset",
                                "reasons": reasons,
                            }
                        )
                    done_ever_env |= dones_bool
                    if args_cli.action_source in HOLD_ACTION_SOURCES:
                        _reset_hold_state(task_env, dones_bool)

                success_rate = _mean_float(success_tensor.float())
                done_step_rate = _mean_float(dones_bool.float()) if isinstance(dones_bool, torch.Tensor) else None
                terminated_rate = _mean_float(terminated.bool().float()) if isinstance(terminated, torch.Tensor) else None
                truncated_rate = _mean_float(truncated.bool().float()) if isinstance(truncated, torch.Tensor) else None
                eval_event_metrics = {
                    "eval_success_ever_rate": _mean_float(success_ever_env.float()),
                    "eval_success_ever_count": int(success_ever_env.sum().detach().cpu()),
                    "eval_first_success_step_mean": _step_tensor_summary(first_success_step)["mean"],
                    "eval_last_success_step_mean": _step_tensor_summary(last_success_step)["mean"],
                    "eval_done_rate": done_step_rate,
                    "eval_done_count_step": (
                        step_done_count if isinstance(dones_bool, torch.Tensor) else 0
                    ),
                    "eval_done_count_cumulative": done_count,
                    "eval_done_ever_rate": _mean_float(done_ever_env.float()),
                    "eval_done_ever_count": int(done_ever_env.sum().detach().cpu()),
                    "eval_done_after_success_rate": _mean_float(done_after_success_env.float()),
                    "eval_terminated_rate": terminated_rate,
                    "eval_truncated_rate": truncated_rate,
                    "eval_suppressed_success_done_rate": (
                        _mean_float(suppressed_success_done.float())
                        if isinstance(suppressed_success_done, torch.Tensor)
                        else None
                    ),
                    "eval_suppressed_success_done_count": int(
                        suppressed_success_done_ever_env.sum().detach().cpu()
                    ),
                    "eval_first_suppressed_success_done_step_mean": _step_tensor_summary(
                        first_suppressed_success_done_step
                    )["mean"],
                }
                if isinstance(dones_bool, torch.Tensor):
                    for reason_name, reason_tensor in pre_step_done_reasons.items():
                        if reason_name == "success_region":
                            continue
                        eval_event_metrics[f"eval_done_{reason_name}_rate"] = _mean_float(
                            (dones_bool & reason_tensor).float()
                        )

                step_record = {
                    "step": step + 1,
                    "done_any_step": int(step_done_count > 0),
                    "done_count_step": step_done_count,
                    "done_count_cumulative": done_count,
                    "success_rate": success_rate,
                    "reward_mean": reward_mean,
                    **eval_event_metrics,
                    **action_source_metrics,
                    **task_metrics,
                    **action_metrics,
                }
                step_metrics.append(step_record)

                if args_cli.print_interval > 0 and ((step + 1) % args_cli.print_interval == 0 or step == 0):
                    print(
                        "[EVAL] "
                        f"step={step + 1} "
                        f"success_rate={success_rate} "
                        f"reward_mean={reward_mean} "
                        f"task_metrics={task_metrics}"
                    )

        if num_envs > 0:
            horizon_probe_metrics = _collect_episode_probe_metrics(task_env, num_envs)
            horizon_step = len(step_metrics)
            for env_idx in range(num_envs):
                _update_episode_stats(episode_stats[env_idx], horizon_probe_metrics, env_idx)
                if int(episode_stats[env_idx].get("start_step") or 0) <= max(1, horizon_step):
                    horizon_episode_outcomes.append(
                        _finish_episode_outcome(
                            env_idx=env_idx,
                            episode_id=episode_ids[env_idx],
                            terminal_step=horizon_step,
                            stats=episode_stats[env_idx],
                            terminal_probe_metrics=horizon_probe_metrics,
                            terminal_source="horizon_end_state",
                        )
                    )
    finally:
        env.close()
        env_closed = True

    success_values = [item["success_rate"] for item in step_metrics if item["success_rate"] is not None]
    reward_values = [item["reward_mean"] for item in step_metrics if item["reward_mean"] is not None]
    window = max(1, min(args_cli.success_window, len(success_values)))
    first_done_step_any = _first_done_step(step_metrics)
    first_episode_metrics = [
        item for item in step_metrics if first_done_step_any is None or int(item["step"]) <= first_done_step_any
    ]
    first_episode_success_values = [
        item["success_rate"] for item in first_episode_metrics if item["success_rate"] is not None
    ]
    first_episode_reward_values = [
        item["reward_mean"] for item in first_episode_metrics if item["reward_mean"] is not None
    ]
    success_occupancy_mean = _mean(success_values)
    success_occupancy_last_window_mean = _mean(success_values[-window:]) if success_values else None
    reward_mean = _mean(reward_values)
    reward_final = reward_values[-1] if reward_values else None
    success_hold_time_threshold = None
    if hasattr(task_env, "cfg") and hasattr(task_env.cfg, "success_timeout"):
        success_hold_time_threshold = float(task_env.cfg.success_timeout)
    completed_episode_summary = _summarize_episode_outcomes(
        completed_episode_outcomes,
        success_hold_time_threshold=success_hold_time_threshold,
    )
    horizon_episode_summary = _summarize_episode_outcomes(
        horizon_episode_outcomes,
        success_hold_time_threshold=success_hold_time_threshold,
    )
    first_attempt_outcomes = _filter_first_attempt_outcomes(
        completed_episode_outcomes,
        horizon_episode_outcomes,
        num_envs,
    )
    first_attempt_summary = _summarize_episode_outcomes(
        first_attempt_outcomes,
        success_hold_time_threshold=success_hold_time_threshold,
    )
    eval_success_rate = first_attempt_summary["success_rate"]
    eval_success_rate_source = "first_attempt_success_rate"
    first_success_summary = _step_tensor_summary(first_success_step)
    last_success_summary = _step_tensor_summary(last_success_step)
    first_done_summary = _step_tensor_summary(first_done_step)
    first_suppressed_success_done_summary = _step_tensor_summary(first_suppressed_success_done_step)
    summary = {
        "task": args_cli.task,
        "checkpoint": resume_path,
        "action_source": args_cli.action_source,
        "residual_adapter": residual_adapter_summary,
        "action_source_notes": (
            "rl_games_policy"
            if args_cli.action_source == "policy"
            else (
                "position_only_delta_ik_from_runtime_task_space_reference_plus_gripper_schedule"
                if args_cli.action_source == "reference_delta"
                else (
                    "position_only_delta_ik_reference_delta_until_terminal_hold_target_plus_closed_gripper"
                    if args_cli.action_source == "reference_delta_hold"
                    else (
                    "rl_games_policy_blended_with_position_only_delta_ik_reference_delta_plus_gripper_schedule"
                    if args_cli.action_source == "policy_reference_mix"
                    else (
                        "rl_games_policy_blended_with_reference_delta_until_terminal_hold_target_plus_closed_gripper"
                        if args_cli.action_source == "policy_reference_mix_hold"
                        else "zero_actions"
                    )
                    )
                )
            )
        ),
        "reference_mix_alpha": (
            max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
            if args_cli.action_source in MIX_ACTION_SOURCES
            else None
        ),
        "reference_mix_gripper_alpha": (
            (
                max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
                if args_cli.reference_mix_gripper_alpha is None
                else max(0.0, min(1.0, float(args_cli.reference_mix_gripper_alpha)))
            )
            if args_cli.action_source in MIX_ACTION_SOURCES
            else None
        ),
        "reference_mix_z_alpha": (
            (
                max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
                if args_cli.reference_mix_z_alpha is None
                else max(0.0, min(1.0, float(args_cli.reference_mix_z_alpha)))
            )
            if args_cli.action_source in MIX_ACTION_SOURCES
            else None
        ),
        "reference_mix_z_alpha_override": (
            args_cli.reference_mix_z_alpha is not None
            if args_cli.action_source in MIX_ACTION_SOURCES
            else None
        ),
        "reference_mix_gripper_alpha_override": (
            args_cli.reference_mix_gripper_alpha is not None
            if args_cli.action_source in MIX_ACTION_SOURCES
            else None
        ),
        "hold_config": (
            {
                "hold_phase_start": float(args_cli.hold_phase_start),
                "hold_trigger_mode": args_cli.hold_trigger_mode,
                "hold_trigger_lift_height": float(args_cli.hold_trigger_lift_height),
                "hold_contact_max_finger_dist": float(args_cli.hold_contact_max_finger_dist),
                "hold_lift_height": float(args_cli.hold_lift_height),
                "hold_gripper_action": float(args_cli.hold_gripper_action),
                "target_policy": args_cli.hold_target_policy,
            }
            if args_cli.action_source in HOLD_ACTION_SOURCES
            else None
        ),
        "num_envs": env_cfg.scene.num_envs,
        "num_steps_requested": args_cli.num_steps,
        "num_steps_completed": len(step_metrics),
        "deterministic": args_cli.deterministic,
        "camera_env_index": int(args_cli.camera_env_index),
        "suppress_success_termination": bool(args_cli.suppress_success_termination),
        "success_termination_suppression_installed": bool(success_termination_suppression_installed),
        "done_count": done_count,
        "success_rate_mean": success_occupancy_mean,
        "success_rate_final": success_values[-1] if success_values else None,
        "success_rate_max": max(success_values) if success_values else None,
        "success_rate_last_window_mean": success_occupancy_last_window_mean,
        "success_occupancy_mean": success_occupancy_mean,
        "success_occupancy_last_window_mean": success_occupancy_last_window_mean,
        "success_rate_definition": (
            "Per-step mean in_success_region occupancy diagnostic. Use eval_success_rate for "
            "the first-attempt episode success metric."
        ),
        "eval_success_rate": eval_success_rate,
        "eval_success_rate_source": eval_success_rate_source,
        "eval_success_hold_rate": first_attempt_summary["success_hold_rate"],
        "eval_success_rate_definition": (
            "Success rate over each env's first evaluation attempt, where an attempt is successful "
            "if its per-env max in_success_region is >= 0.5. Completed attempts use the pre-reset "
            "terminal state; unfinished first attempts use horizon-end state. "
            "success_occupancy_* fields are per-step in_success_region occupancy and may show reset artifacts."
        ),
        "reward_mean": reward_mean,
        "reward_final": reward_final,
        "success_ever_count": int(success_ever_env.sum().detach().cpu()),
        "success_ever_rate": _mean_float(success_ever_env.float()),
        "success_ever_by_env": _tensor_bool_list(success_ever_env),
        "success_final_by_env": _tensor_bool_list(final_success_env),
        "first_success_step": first_success_summary,
        "first_success_step_by_env": _tensor_float_list(first_success_step),
        "last_success_step": last_success_summary,
        "last_success_step_by_env": _tensor_float_list(last_success_step),
        "cube_lift_height_final_by_env": _tensor_float_list(final_lift_height_env),
        "cube_lift_height_max_by_env": _tensor_float_list(max_lift_height_env),
        "done_ever_count": int(done_ever_env.sum().detach().cpu()),
        "done_ever_rate": _mean_float(done_ever_env.float()),
        "done_ever_by_env": _tensor_bool_list(done_ever_env),
        "first_done_step": first_done_summary,
        "first_done_step_by_env": _tensor_float_list(first_done_step),
        "done_after_success_count": int(done_after_success_env.sum().detach().cpu()),
        "done_after_success_rate": _mean_float(done_after_success_env.float()),
        "suppressed_success_done_count": int(suppressed_success_done_ever_env.sum().detach().cpu()),
        "suppressed_success_done_rate": _mean_float(suppressed_success_done_ever_env.float()),
        "first_suppressed_success_done_step": first_suppressed_success_done_summary,
        "done_reason_counts": done_reason_counts,
        "done_events": done_events,
        "video_enabled": args_cli.video,
        "video_folder": str(video_folder) if args_cli.video else None,
        "video_files": _latest_video_files(video_folder),
        "trace_jsonl_path": str(trace_jsonl_path),
        "trace_csv_path": str(trace_csv_path),
        "output_dir": str(output_dir),
        "env_closed": env_closed,
        "first_done_step_any": first_done_step_any,
        "first_episode_num_steps": len(first_episode_metrics),
        "first_episode_success_rate_final": first_episode_success_values[-1]
        if first_episode_success_values
        else None,
        "first_episode_success_rate_max": max(first_episode_success_values)
        if first_episode_success_values
        else None,
        "first_episode_success_rate_mean": _mean(first_episode_success_values),
        "first_episode_reward_final": first_episode_reward_values[-1]
        if first_episode_reward_values
        else None,
        "first_episode_reward_mean": _mean(first_episode_reward_values),
        "first_episode_metric_summaries": _summarize_step_metrics(first_episode_metrics),
        "completed_episode_count": completed_episode_summary["count"],
        "completed_episode_success_rate": completed_episode_summary["success_rate"],
        "completed_episode_success_hold_rate": completed_episode_summary["success_hold_rate"],
        "completed_episode_summary": completed_episode_summary,
        "horizon_episode_count": horizon_episode_summary["count"],
        "horizon_episode_summary": horizon_episode_summary,
        "horizon_episode_outcomes": horizon_episode_outcomes,
        "first_attempt_count": first_attempt_summary["count"],
        "first_attempt_count_expected": num_envs,
        "first_attempt_success_rate": first_attempt_summary["success_rate"],
        "first_attempt_success_hold_rate": first_attempt_summary["success_hold_rate"],
        "first_attempt_terminal_success_rate": first_attempt_summary["terminal_success_rate"],
        "first_attempt_summary": first_attempt_summary,
        "first_attempt_outcomes": first_attempt_outcomes,
        "episode_outcomes": completed_episode_outcomes,
        "trajectory_tracking_reference": trajectory_tracking_reference,
        "trajectory_tracking_reference_path": getattr(env_cfg, "trajectory_tracking_reference_path", None),
        "env_config": _env_config_summary(env_cfg, task_env),
        "metric_summaries": _summarize_step_metrics(step_metrics),
        "fixed_window_summaries": _fixed_window_summaries(step_metrics, args_cli.summary_window),
    }
    payload = {"summary": summary, "steps": step_metrics}
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_trace_artifacts(step_metrics, trace_csv_path, trace_jsonl_path)
    print(f"[INFO] Wrote metrics to {metrics_path}")
    print(f"[INFO] Wrote trace CSV to {trace_csv_path}")
    print(f"[INFO] Wrote trace JSONL to {trace_jsonl_path}")
    print("[INFO] Eval summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
