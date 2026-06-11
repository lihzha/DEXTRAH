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
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401


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
    for name in ("phase_triggered", "lift_triggered", "success_triggered", "contact_triggered"):
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
    trigger = phase_trigger | lift_trigger | success_trigger | contact_trigger
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


def _policy_actions(agent: BasePlayer | None, obs) -> torch.Tensor:
    if agent is None:
        raise ValueError("policy action source requires an RL-Games player.")
    obs_t = agent.obs_to_torch(obs)
    return agent.get_action(obs_t, is_deterministic=args_cli.deterministic)


def _actions_from_source(
    action_source: str,
    task_env,
    agent: BasePlayer | None,
    obs,
) -> tuple[torch.Tensor, dict[str, float | None]]:
    metrics: dict[str, float | None] = {}
    if action_source == "policy":
        raw_policy_actions = _policy_actions(agent, obs)
        _add_action_signal_metrics(metrics, "raw_policy_action", raw_policy_actions)
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
        raw_policy_actions = _policy_actions(agent, obs)
        reference_actions = _reference_delta_actions(task_env)
        alpha = max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
        mixed_actions = torch.clamp((1.0 - alpha) * raw_policy_actions + alpha * reference_actions, -1.0, 1.0)
        metrics["reference_mix_alpha"] = alpha
        _add_action_signal_metrics(metrics, "raw_policy_action", raw_policy_actions)
        _add_action_signal_metrics(metrics, "reference_delta_action", reference_actions)
        _add_action_signal_metrics(metrics, "mixed_action", mixed_actions)
        _add_action_delta_metrics(metrics, "policy_reference_action_error", raw_policy_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_reference_action_error", mixed_actions, reference_actions)
        _add_action_delta_metrics(metrics, "mixed_policy_action_error", mixed_actions, raw_policy_actions)
        return mixed_actions, metrics
    if action_source == "policy_reference_mix_hold":
        raw_policy_actions = _policy_actions(agent, obs)
        reference_actions = _reference_delta_actions(task_env)
        alpha = max(0.0, min(1.0, float(args_cli.reference_mix_alpha)))
        mixed_actions = torch.clamp((1.0 - alpha) * raw_policy_actions + alpha * reference_actions, -1.0, 1.0)
        metrics["reference_mix_alpha"] = alpha
        _add_action_signal_metrics(metrics, "raw_policy_action", raw_policy_actions)
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
        "trajectory_tracking_enabled",
        "trajectory_tracking_reference_path",
        "trajectory_tracking_reference_duration_s",
        "trajectory_tracking_phase_observations",
        "trajectory_tracking_close_action_weight",
        "trajectory_tracking_lift_action_weight",
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
    if task_env is not None and hasattr(task_env, "scene") and len(task_env.scene.env_origins) > 0:
        env_origin = task_env.scene.env_origins[0].detach().cpu().tolist()
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    print(f"[INFO] Eval video camera eye={eye} target={target}")

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
    else:
        env = gym_env

    step_metrics = []
    done_count = 0
    env_closed = False
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

        for step in range(args_cli.num_steps):
            if not simulation_app.is_running():
                break

            with torch.inference_mode():
                actions, action_source_metrics = _actions_from_source(args_cli.action_source, task_env, agent, obs)
                step_out = env.step(actions)
                if len(step_out) == 5:
                    obs, rewards, terminated, truncated, _ = step_out
                    dones = torch.logical_or(terminated, truncated)
                else:
                    obs, rewards, dones, _ = step_out

                if args_cli.action_source in POLICY_ACTION_SOURCES and isinstance(obs, dict):
                    obs = obs["obs"]

                success_rate = _env_metric(task_env, "in_success_region")
                reward_mean = _mean_float(rewards)
                task_metrics = _collect_task_metrics(task_env, actions)

                if isinstance(dones, torch.Tensor):
                    dones_bool = dones.bool()
                    done_count += int(dones_bool.sum().detach().cpu())
                    if agent is not None and agent.is_rnn and agent.states is not None and dones_bool.any():
                        for state in agent.states:
                            state[:, dones_bool, :] = 0.0
                    if args_cli.action_source in HOLD_ACTION_SOURCES and dones_bool.any():
                        _reset_hold_state(task_env, dones_bool)

                step_record = {
                    "step": step + 1,
                    "success_rate": success_rate,
                    "reward_mean": reward_mean,
                    **action_source_metrics,
                    **task_metrics,
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
    finally:
        env.close()
        env_closed = True

    success_values = [item["success_rate"] for item in step_metrics if item["success_rate"] is not None]
    reward_values = [item["reward_mean"] for item in step_metrics if item["reward_mean"] is not None]
    window = max(1, min(args_cli.success_window, len(success_values)))
    summary = {
        "task": args_cli.task,
        "checkpoint": resume_path,
        "action_source": args_cli.action_source,
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
        "hold_config": (
            {
                "hold_phase_start": float(args_cli.hold_phase_start),
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
        "done_count": done_count,
        "success_rate_mean": sum(success_values) / len(success_values) if success_values else None,
        "success_rate_final": success_values[-1] if success_values else None,
        "success_rate_last_window_mean": sum(success_values[-window:]) / window if success_values else None,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "video_enabled": args_cli.video,
        "video_folder": str(video_folder) if args_cli.video else None,
        "video_files": _latest_video_files(video_folder),
        "output_dir": str(output_dir),
        "env_closed": env_closed,
        "trajectory_tracking_reference": trajectory_tracking_reference,
        "trajectory_tracking_reference_path": getattr(env_cfg, "trajectory_tracking_reference_path", None),
        "env_config": _env_config_summary(env_cfg, task_env),
        "trace_csv_path": str(trace_csv_path),
        "trace_jsonl_path": str(trace_jsonl_path),
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
