"""Audit Franka cube pass7 BC label semantics in closed loop.

This script is diagnostic-only. It does not modify the RL task, reward,
termination, PPO config, or reset defaults. It answers three bounded questions:

1. Do the same reference actions used as BC labels grasp/lift when executed
   from the pass7 reset distribution?
2. Does an exact replay of the recorded label actions reproduce that behavior?
3. On the same live observations, how far is a BC policy checkpoint from the
   reference label actions?
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--num_resets", type=int, default=2)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--grasp_prior_library_path", type=str, required=True)
parser.add_argument("--policy_checkpoint", type=str, default="")
parser.add_argument("--policy_label", type=str, default="bc_policy")
parser.add_argument("--approach_steps", type=int, default=16)
parser.add_argument("--close_steps", type=int, default=12)
parser.add_argument("--lift_steps", type=int, default=12)
parser.add_argument("--close_width", type=float, default=0.055)
parser.add_argument("--lift_action_z", type=float, default=0.15)
parser.add_argument("--oracle_gain", type=float, default=8.0)
parser.add_argument("--oracle_max_position_action", type=float, default=1.0)
parser.add_argument("--track_orientation", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--render", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--render_resets", type=int, default=1)
parser.add_argument("--render_interval", type=int, default=10)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument("--success_lift_height", type=float, default=0.01)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

if bool(args_cli.render):
    args_cli.enable_cameras = True

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

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


ACTION_NAMES = ("x", "y", "z", "roll", "pitch", "yaw", "gripper")


class DextrahLabelVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


class DextrahLabelGpuEnv(RlGamesGpuEnv):
    def get_current_obs(self):
        if hasattr(self.env, "get_current_obs"):
            return self.env.get_current_obs()
        raise AttributeError("Wrapped environment does not expose get_current_obs")


def _json_safe(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return float(value.detach().float().cpu())
        return value.detach().float().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    for key in reversed(["reset_index", "mode", "step", "phase", "action_dim", "action_name"]):
        if key in fieldnames:
            fieldnames.remove(key)
            fieldnames.insert(0, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_json_safe(row), sort_keys=True) + "\n")


def _write_exception_artifact(output_dir: Path, exc: BaseException) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = traceback.format_exc()
    (output_dir / "ERROR.md").write_text(
        "# BC Label Semantics Audit Error\n\n"
        f"- error_type: `{type(exc).__name__}`\n"
        f"- error: `{exc}`\n\n"
        "```text\n"
        f"{trace}"
        "```\n",
        encoding="utf-8",
    )
    _write_json(output_dir / "error.json", {"error_type": type(exc).__name__, "error": str(exc), "traceback": trace})


def _tensor_list(value: torch.Tensor | np.ndarray | list[float] | tuple[float, ...]) -> list[float]:
    if isinstance(value, torch.Tensor):
        flat = value.detach().float().cpu().flatten().tolist()
    elif isinstance(value, np.ndarray):
        flat = value.astype(float).flatten().tolist()
    else:
        flat = [float(v) for v in value]
    return [float(v) for v in flat]


def _as_float(value: Any) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return _as_float(value)
    except (TypeError, ValueError):
        return None


def _obs_policy_tensor(obs: Any) -> torch.Tensor:
    if isinstance(obs, tuple):
        obs = obs[0]
    if isinstance(obs, dict):
        obs = obs["obs"]
    return obs


def _gripper_action_for_width(width: float, max_width: float) -> float:
    if max_width <= 1.0e-6:
        return -1.0
    return float(np.clip(2.0 * float(width) / float(max_width) - 1.0, -1.0, 1.0))


def _phase_for_step(step_index_zero_based: int) -> str:
    if step_index_zero_based < int(args_cli.approach_steps):
        return "approach"
    if step_index_zero_based < int(args_cli.approach_steps) + int(args_cli.close_steps):
        return "close"
    return "lift"


def _quat_identity(device: str) -> torch.Tensor:
    return torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=device)


def _pos_in_root(task_env, env_id: int, pos_w: torch.Tensor) -> torch.Tensor:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    pos_b, _ = math_utils.subtract_frame_transforms(root_pos_w, root_quat_w, pos_w.unsqueeze(0), _quat_identity(task_env.device))
    return pos_b[0]


def _compute_exact_tracking_action(task_env, gripper_action: float) -> torch.Tensor:
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    task_env._compute_intermediate_values(update_success_timer=False)
    current_ee_pos_b, current_ee_quat_b = task_env._compute_ee_frame_pose()
    exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        task_env.grasp_prior_reset_exact_ee_pos_w,
        task_env.grasp_prior_reset_exact_ee_quat_w,
    )
    pos_action = float(args_cli.oracle_gain) * (exact_ee_pos_b - current_ee_pos_b) / torch.clamp(
        task_env.action_scale[:3], min=1.0e-6
    )
    max_position_action = max(float(args_cli.oracle_max_position_action), 0.0)
    action[:, :3] = torch.clamp(pos_action, min=-max_position_action, max=max_position_action)
    if bool(args_cli.track_orientation):
        _, rot_error_b = math_utils.compute_pose_error(
            current_ee_pos_b,
            current_ee_quat_b,
            exact_ee_pos_b,
            exact_ee_quat_b,
            rot_error_type="axis_angle",
        )
        rot_action = float(args_cli.oracle_gain) * rot_error_b / torch.clamp(task_env.action_scale[3:6], min=1.0e-6)
        action[:, 3:6] = torch.clamp(rot_action, min=-1.0, max=1.0)
    action[:, 6] = float(gripper_action)
    return action.clamp(-1.0, 1.0)


def _reference_action(task_env, phase: str) -> torch.Tensor:
    open_action = _gripper_action_for_width(float(task_env.cfg.max_gripper_width), float(task_env.cfg.max_gripper_width))
    close_action = _gripper_action_for_width(float(args_cli.close_width), float(task_env.cfg.max_gripper_width))
    if phase == "approach":
        return _compute_exact_tracking_action(task_env, open_action)
    if phase == "close":
        return _compute_exact_tracking_action(task_env, close_action)
    if phase == "lift":
        action = _compute_exact_tracking_action(task_env, close_action)
        action[:, 2] = float(np.clip(args_cli.lift_action_z, -1.0, 1.0))
        return action.clamp(-1.0, 1.0)
    raise ValueError(f"Unknown phase {phase!r}")


def _root_state_w(asset) -> torch.Tensor:
    return torch.cat((asset.data.root_pos_w, asset.data.root_quat_w, asset.data.root_vel_w), dim=-1)


def _snapshot_tensor(value: Any) -> Any:
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
        "grasp_prior_reset_gripper_width",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_offset_radial_dot",
        "grasp_prior_reset_offset_radial_angle",
        "grasp_prior_reset_exact_ee_dist",
        "grasp_prior_reset_pregrasp_ee_dist",
        "grasp_prior_reset_projected_exact_finger_center_dist",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_quality_success",
    )


def _snapshot_task_env_state(task_env) -> dict[str, Any]:
    task_tensors: dict[str, Any] = {}
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


def _restore_task_env_state(task_env, env_state: dict[str, Any]) -> None:
    if int(env_state.get("num_envs", task_env.num_envs)) != task_env.num_envs:
        raise ValueError(f"Cannot restore num_envs={env_state.get('num_envs')} into num_envs={task_env.num_envs}")
    task_env.common_step_counter = int(env_state.get("common_step_counter", getattr(task_env, "common_step_counter", 0)))
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


def _create_player(agent_cfg: dict, env, checkpoint_path: str) -> BasePlayer:
    cfg = copy.deepcopy(agent_cfg)
    cfg["params"]["load_checkpoint"] = True
    cfg["params"]["load_path"] = checkpoint_path
    cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    runner = Runner()
    runner.load(cfg)
    player: BasePlayer = runner.create_player()
    player.restore(checkpoint_path)
    player.reset()
    return player


def _prepare_player_for_obs(player: BasePlayer, obs: torch.Tensor) -> torch.Tensor:
    obs_t = player.obs_to_torch(obs)
    _ = player.get_batch_size(obs_t, 1)
    if player.is_rnn and getattr(player, "states", None) is None:
        player.init_rnn()
    return obs_t


def _policy_action(player: BasePlayer | None, obs: torch.Tensor) -> torch.Tensor | None:
    if player is None:
        return None
    obs_t = _prepare_player_for_obs(player, obs)
    with torch.inference_mode():
        action = player.get_action(obs_t, is_deterministic=True)
    return action.clamp(-1.0, 1.0)


def _set_camera(task_env, env_cfg, env_id: int) -> None:
    if not bool(args_cli.render):
        return
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


def _render_rgb(gym_env, task_env) -> np.ndarray:
    for _ in range(4):
        task_env.sim.render()
    frame = gym_env.render()
    if isinstance(frame, list):
        frame = frame[0] if frame else None
    if frame is None:
        raise RuntimeError("gym_env.render() returned None")
    return np.asarray(frame)


def _font(size: int, *, bold: bool = False):
    try:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
    except Exception:
        return ImageFont.load_default()


def _overlay_frame(frame: np.ndarray, title: str, lines: list[str]) -> Image.Image:
    image = Image.fromarray(frame[..., :3].astype(np.uint8))
    draw = ImageDraw.Draw(image)
    font = _font(14)
    title_font = _font(16, bold=True)
    margin = 10
    line_h = 17
    width = min(image.width - 2 * margin, 940)
    height = margin * 2 + line_h * (len(lines) + 2)
    draw.rectangle((margin, margin, margin + width, margin + height), fill=(0, 0, 0))
    draw.text((margin + 8, margin + 5), title, fill=(255, 255, 255), font=title_font)
    y = margin + 5 + line_h * 2
    for line in lines:
        draw.text((margin + 8, y), line, fill=(235, 235, 235), font=font)
        y += line_h
    return image


def _fmt_vec(values: Any) -> str:
    return "[" + ", ".join(f"{float(v):+.3f}" for v in values) + "]"


def _collect_reset_sample(task_env, env_id: int, reset_index: int) -> dict[str, Any]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_ee_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    pregrasp_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    exact_tool_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_tool_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    term, trunc = task_env._get_dones()
    return {
        "reset_index": int(reset_index),
        "env_id": int(env_id),
        "sample_index": int(task_env.grasp_prior_reset_sample_index[env_id].detach().cpu()),
        "reset_success": bool(task_env.grasp_prior_reset_success[env_id].detach().cpu()),
        "reset_quality_success": bool(task_env.grasp_prior_reset_quality_success[env_id].detach().cpu()),
        "immediate_done": bool((term[env_id] | trunc[env_id]).detach().cpu()),
        "cube_pos_env": _tensor_list(task_env.cube_pos[env_id]),
        "cube_pos_w": _tensor_list(cube_w),
        "cube_pos_root": _tensor_list(_pos_in_root(task_env, env_id, cube_w)),
        "exact_ee_pos_env": _tensor_list(exact_ee_w - env_origin),
        "pregrasp_ee_pos_env": _tensor_list(pregrasp_ee_w - env_origin),
        "exact_tool_pos_env": _tensor_list(exact_tool_w - env_origin),
        "pregrasp_tool_pos_env": _tensor_list(pregrasp_tool_w - env_origin),
        "ee_to_cube_dist_m": _as_float(task_env.ee_to_cube_dist[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "projected_exact_tip_center_dist_m": _as_float(task_env.grasp_prior_reset_projected_exact_tip_center_dist[env_id]),
        "projected_exact_tip_max_dist_m": _as_float(task_env.grasp_prior_reset_projected_exact_tip_max_dist[env_id]),
        "open_width_margin_m": _as_float(task_env.grasp_prior_reset_open_width_margin[env_id]),
        "offset_radial_dot": _as_float(task_env.grasp_prior_reset_offset_radial_dot[env_id]),
        "reset_pos_error_m": _as_float(task_env.grasp_prior_reset_pos_error[env_id]),
        "reset_rot_error_rad": _as_float(task_env.grasp_prior_reset_rot_error[env_id]),
    }


def _contact_metrics(task_env, env_id: int) -> dict[str, Any]:
    metrics: dict[str, Any] = {"contact_available": False, "contact_flag": None}
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


def _step_metrics(task_env, env_id: int, *, reset_index: int, mode: str, step: int, phase: str, action: torch.Tensor, reward: Any, terminated: Any, truncated: Any) -> dict[str, Any]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    if isinstance(reward, torch.Tensor):
        reward_value = _as_float(reward[env_id] if reward.ndim > 0 else reward)
    else:
        reward_value = float(reward)
    terminated_flag = bool(terminated[env_id].detach().cpu()) if isinstance(terminated, torch.Tensor) else bool(terminated)
    truncated_flag = bool(truncated[env_id].detach().cpu()) if isinstance(truncated, torch.Tensor) else bool(truncated)
    action_env = action[env_id].detach().float()
    record = {
        "reset_index": int(reset_index),
        "mode": mode,
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
        "ee_to_cube_dist_m": _as_float(task_env.ee_to_cube_dist[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "max_finger_to_cube_dist_m": _as_float(task_env.max_finger_to_cube_dist[env_id]),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "finger_table_clearance_violation": _as_float(task_env.finger_table_clearance_violation[env_id]),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "cube_pos_env": _tensor_list(task_env.cube_pos[env_id]),
        "ee_pos_env": _tensor_list(task_env.ee_pos[env_id]),
        "action_x": float(action_env[0].cpu()),
        "action_y": float(action_env[1].cpu()),
        "action_z": float(action_env[2].cpu()),
        "action_roll": float(action_env[3].cpu()),
        "action_pitch": float(action_env[4].cpu()),
        "action_yaw": float(action_env[5].cpu()),
        "action_gripper": float(action_env[6].cpu()),
        "action_abs_mean": float(torch.mean(action_env.abs()).cpu()),
        "action_max_abs": float(torch.max(action_env.abs()).cpu()),
        "grasp_prior_reset_success": _as_float(task_env.grasp_prior_reset_success[env_id]),
        "grasp_prior_reset_quality_success": _as_float(task_env.grasp_prior_reset_quality_success[env_id]),
    }
    record.update(_contact_metrics(task_env, env_id))
    return record


def _summarize_trace(rows: list[dict[str, Any]], sample: dict[str, Any], mode: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "mode": mode,
        "reset_index": sample["reset_index"],
        "sample_index": sample["sample_index"],
        "reset_success": sample["reset_success"],
        "reset_quality_success": sample["reset_quality_success"],
        "initial_ee_to_cube_dist_m": sample["ee_to_cube_dist_m"],
        "initial_finger_center_to_cube_dist_m": sample["finger_center_to_cube_dist_m"],
        "initial_gripper_width_m": sample["gripper_width_m"],
        "steps_completed": len(rows),
    }
    if not rows:
        return summary
    summary.update(
        {
            "success_max": max(float(row["success_rate"]) for row in rows),
            "lifted_max": max(float(row["has_lifted_cube"]) for row in rows),
            "done_seen": any(bool(row["done"]) for row in rows),
            "contact_seen": any(bool(row.get("contact_flag")) for row in rows if row.get("contact_flag") is not None),
            "lift_gate_pass": max(float(row["cube_lift_height_m"]) for row in rows) >= float(args_cli.success_lift_height),
        }
    )
    for key in (
        "reward",
        "cube_lift_height_m",
        "ee_to_cube_dist_m",
        "finger_center_to_cube_dist_m",
        "max_finger_to_cube_dist_m",
        "gripper_width_m",
        "action_z",
        "action_gripper",
    ):
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        if values:
            summary[f"{key}_first"] = values[0]
            summary[f"{key}_final"] = values[-1]
            summary[f"{key}_min"] = min(values)
            summary[f"{key}_max"] = max(values)
            summary[f"{key}_mean"] = float(np.mean(values))
    return summary


def _record_action_comparison(
    rows: list[dict[str, Any]],
    *,
    reset_index: int,
    step: int,
    phase: str,
    label_action: torch.Tensor,
    policy_action: torch.Tensor | None,
    obs: torch.Tensor,
) -> None:
    label_values = label_action[0].detach().float().cpu().tolist()
    policy_values = [math.nan] * len(label_values)
    if policy_action is not None:
        policy_values = policy_action[0].detach().float().cpu().tolist()
    obs0 = obs[0].detach().float()
    obs_abs = obs0.abs()
    obs_stats = {
        "obs_abs_mean": float(obs_abs.mean().cpu()),
        "obs_abs_max": float(obs_abs.max().cpu()),
        "obs_min": float(obs0.min().cpu()),
        "obs_max": float(obs0.max().cpu()),
    }
    for dim, name in enumerate(ACTION_NAMES):
        label = float(label_values[dim])
        policy = float(policy_values[dim])
        rows.append(
            {
                "reset_index": int(reset_index),
                "step": int(step),
                "phase": phase,
                "action_dim": dim,
                "action_name": name,
                "label_action": label,
                "policy_action": policy,
                "policy_minus_label": policy - label if math.isfinite(policy) else math.nan,
                "abs_error": abs(policy - label) if math.isfinite(policy) else math.nan,
                "same_sign": (policy >= 0.0) == (label >= 0.0) if math.isfinite(policy) else None,
                **obs_stats,
            }
        )


def _render_frame(gym_env, task_env, env_cfg, *, env_id: int, mode: str, reset_index: int, step: int, phase: str, sample: dict[str, Any], record: dict[str, Any] | None, frames_dir: Path, rendered_frames: list[Path]) -> None:
    if not bool(args_cli.render):
        return
    _set_camera(task_env, env_cfg, env_id)
    frame = _render_rgb(gym_env, task_env)
    if record is None:
        lines = [
            "reset/pregrasp before action",
            f"sample={sample['sample_index']} reset={sample['reset_success']} quality={sample['reset_quality_success']}",
            f"cube={_fmt_vec(sample['cube_pos_env'])} exact_ee={_fmt_vec(sample['exact_ee_pos_env'])}",
            f"pregrasp_ee={_fmt_vec(sample['pregrasp_ee_pos_env'])}",
            f"ee_dist={sample['ee_to_cube_dist_m']:.4f} finger={sample['finger_center_to_cube_dist_m']:.4f} width={sample['gripper_width_m']:.4f}",
        ]
    else:
        lines = [
            f"phase={phase} reward={record['reward']:.3f} done={record['done']} contact={record.get('contact_flag')}",
            f"action xyz=({record['action_x']:+.2f},{record['action_y']:+.2f},{record['action_z']:+.2f}) grip={record['action_gripper']:+.2f}",
            f"lift={record['cube_lift_height_m']:.4f} success={record['success_rate']:.1f} lifted={record['has_lifted_cube']:.1f}",
            f"ee={record['ee_to_cube_dist_m']:.4f} finger={record['finger_center_to_cube_dist_m']:.4f} maxfinger={record['max_finger_to_cube_dist_m']:.4f}",
            f"width={record['gripper_width_m']:.4f} table={record['finger_table_clearance_m']:.4f}",
        ]
    image = _overlay_frame(frame, f"BC label semantics | {mode} | reset {reset_index} | step {step}", lines)
    frame_path = frames_dir / f"reset_{reset_index:03d}_{mode}_step_{step:03d}_{phase}.png"
    image.save(frame_path)
    rendered_frames.append(frame_path)


def _write_contact_sheet(frames: list[Path], output_path: Path, thumb_width: int = 480) -> None:
    if not frames:
        return
    images: list[Image.Image] = []
    for path in frames:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue
        scale = thumb_width / max(image.width, 1)
        images.append(image.resize((thumb_width, max(1, int(image.height * scale)))))
    if not images:
        return
    cols = min(3, len(images))
    rows = math.ceil(len(images) / cols)
    cell_h = max(image.height for image in images)
    sheet = Image.new("RGB", (cols * thumb_width, rows * cell_h), (20, 20, 20))
    for idx, image in enumerate(images):
        sheet.paste(image, ((idx % cols) * thumb_width, (idx // cols) * cell_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def _draw_trace_plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    modes = sorted({str(row["mode"]) for row in rows})
    metrics = [
        ("ee_to_cube_dist_m", "EE-cube m"),
        ("finger_center_to_cube_dist_m", "finger-cube m"),
        ("cube_lift_height_m", "lift m"),
        ("action_z", "action z"),
        ("action_gripper", "gripper act"),
    ]
    colors = {"closed_loop_label": "#1f77b4", "recorded_label_replay": "#2ca02c", "policy_replay": "#d62728"}
    try:
        font = _font(12)
        font_b = _font(14, bold=True)
        font_t = _font(20, bold=True)
    except Exception:
        font = font_b = font_t = ImageFont.load_default()
    W, H = 1500, 1050
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.text((28, 18), "BC label semantics trace plot", fill="#111827", font=font_t)
    panel_w = 700
    panel_h = 290
    for idx, (metric, title) in enumerate(metrics):
        x0 = 28 + (idx % 2) * (panel_w + 40)
        y0 = 70 + (idx // 2) * (panel_h + 34)
        x1, y1 = x0 + panel_w, y0 + panel_h
        draw.rectangle((x0, y0, x1, y1), outline="#c9ccd1")
        draw.text((x0 + 8, y0 + 6), title, fill="#111827", font=font_b)
        px0, py0, px1, py1 = x0 + 56, y0 + 34, x1 - 18, y1 - 36
        values = [float(row[metric]) for row in rows if metric in row and row.get(metric) is not None]
        if not values:
            continue
        lo, hi = min(values), max(values)
        if abs(hi - lo) < 1.0e-9:
            lo -= 1.0
            hi += 1.0
        else:
            pad = 0.08 * (hi - lo)
            lo -= pad
            hi += pad
        draw.line((px0, py1, px1, py1), fill="#6b7280")
        draw.line((px0, py0, px0, py1), fill="#6b7280")
        for i in range(5):
            y = py1 - (py1 - py0) * i / 4
            val = lo + (hi - lo) * i / 4
            draw.line((px0, y, px1, y), fill="#edf0f5")
            draw.text((x0 + 4, y - 7), f"{val:.3g}", fill="#4b5563", font=font)
        for mode_idx, mode in enumerate(modes):
            subset = [row for row in rows if row["mode"] == mode and int(row["reset_index"]) == 0]
            if not subset:
                continue
            xs = [int(row["step"]) for row in subset]
            vs = [float(row[metric]) for row in subset]
            xlo, xhi = min(xs), max(xs)
            pts = []
            for xval, v in zip(xs, vs, strict=True):
                x = px0 + (px1 - px0) * (xval - xlo) / max(xhi - xlo, 1)
                y = py1 - (py1 - py0) * (v - lo) / max(hi - lo, 1.0e-9)
                pts.append((x, y))
            if len(pts) >= 2:
                draw.line(pts, fill=colors.get(mode, "#111827"), width=3)
            lx = px0 + 150 * mode_idx
            ly = y1 - 22
            draw.line((lx, ly, lx + 20, ly), fill=colors.get(mode, "#111827"), width=3)
            draw.text((lx + 26, ly - 8), mode.replace("_", " "), fill="#111827", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def _summarize_action_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if not rows:
        return summary
    finite_rows = [row for row in rows if row.get("policy_action") is not None and math.isfinite(float(row["policy_action"]))]
    if not finite_rows:
        return {"policy_checkpoint_loaded": False}
    summary["policy_checkpoint_loaded"] = True
    summary["mean_abs_error"] = float(np.mean([float(row["abs_error"]) for row in finite_rows]))
    summary["max_abs_error"] = float(np.max([float(row["abs_error"]) for row in finite_rows]))
    summary["same_sign_rate"] = float(np.mean([1.0 if bool(row["same_sign"]) else 0.0 for row in finite_rows]))
    phase_dim: list[dict[str, Any]] = []
    for phase in ("approach", "close", "lift"):
        for dim, name in enumerate(ACTION_NAMES):
            subset = [row for row in finite_rows if row["phase"] == phase and int(row["action_dim"]) == dim]
            if not subset:
                continue
            phase_dim.append(
                {
                    "phase": phase,
                    "action_dim": dim,
                    "action_name": name,
                    "label_mean": float(np.mean([float(row["label_action"]) for row in subset])),
                    "policy_mean": float(np.mean([float(row["policy_action"]) for row in subset])),
                    "mae": float(np.mean([float(row["abs_error"]) for row in subset])),
                    "same_sign_rate": float(np.mean([1.0 if bool(row["same_sign"]) else 0.0 for row in subset])),
                }
            )
    summary["by_phase_dim"] = phase_dim
    return summary


def _run_mode(
    env,
    gym_env,
    task_env,
    env_cfg,
    *,
    env_id: int,
    reset_index: int,
    mode: str,
    sample: dict[str, Any],
    snapshot: dict[str, Any],
    actions: list[torch.Tensor] | None,
    player: BasePlayer | None,
    frames_dir: Path,
    rendered_frames: list[Path],
) -> tuple[list[dict[str, Any]], list[torch.Tensor]]:
    _restore_task_env_state(task_env, snapshot)
    if player is not None:
        player.reset()
    obs = _obs_policy_tensor(env.get_current_obs())
    records: list[dict[str, Any]] = []
    recorded_actions: list[torch.Tensor] = []
    render_this_reset = bool(args_cli.render) and reset_index < int(args_cli.render_resets)
    if render_this_reset:
        _render_frame(
            gym_env,
            task_env,
            env_cfg,
            env_id=env_id,
            mode=mode,
            reset_index=reset_index,
            step=0,
            phase="reset_pregrasp",
            sample=sample,
            record=None,
            frames_dir=frames_dir,
            rendered_frames=rendered_frames,
        )
    total_steps = int(args_cli.approach_steps) + int(args_cli.close_steps) + int(args_cli.lift_steps)
    for step_idx in range(total_steps):
        if not simulation_app.is_running():
            break
        phase = _phase_for_step(step_idx)
        if mode == "closed_loop_label":
            action = _reference_action(task_env, phase)
            recorded_actions.append(action.detach().clone())
        elif mode == "recorded_label_replay":
            if actions is None:
                raise ValueError("recorded_label_replay requires actions")
            action = actions[step_idx].to(task_env.device).clone()
        elif mode == "policy_replay":
            policy_action = _policy_action(player, obs) if player is not None else None
            if policy_action is None:
                raise ValueError("policy_replay requires a policy checkpoint")
            action = policy_action
        else:
            raise ValueError(f"Unknown mode {mode!r}")
        step_out = env.step(action)
        if len(step_out) == 5:
            obs, rewards, terminated, truncated, _ = step_out
        else:
            obs, rewards, dones, _ = step_out
            terminated = dones
            truncated = torch.zeros_like(dones) if isinstance(dones, torch.Tensor) else False
        obs = _obs_policy_tensor(obs)
        record = _step_metrics(
            task_env,
            env_id,
            reset_index=reset_index,
            mode=mode,
            step=step_idx + 1,
            phase=phase,
            action=action,
            reward=rewards,
            terminated=terminated,
            truncated=truncated,
        )
        records.append(record)
        if render_this_reset and (
            step_idx == 0
            or step_idx + 1 == total_steps
            or (step_idx + 1) % max(int(args_cli.render_interval), 1) == 0
            or bool(record["done"])
        ):
            _render_frame(
                gym_env,
                task_env,
                env_cfg,
                env_id=env_id,
                mode=mode,
                reset_index=reset_index,
                step=step_idx + 1,
                phase=phase,
                sample=sample,
                record=record,
                frames_dir=frames_dir,
                rendered_frames=rendered_frames,
            )
        if bool(record["done"]):
            break
    return records, recorded_actions


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    summaries = payload["rollout_summaries"]
    action_summary = payload["action_comparison_summary"]
    by_mode: dict[str, list[dict[str, Any]]] = {}
    for row in summaries:
        by_mode.setdefault(str(row["mode"]), []).append(row)
    def mode_rate(mode: str, key: str) -> float:
        rows = by_mode.get(mode, [])
        if not rows:
            return math.nan
        return float(np.mean([1.0 if bool(row.get(key)) else 0.0 for row in rows]))
    lines = [
        "# BC Label Semantics Audit",
        "",
        "Diagnostic-only run. No task/reward/reset/PPO semantic changes.",
        "",
        "## Verdict",
        "",
        f"- closed-loop label lift gate pass rate: `{mode_rate('closed_loop_label', 'lift_gate_pass')}`",
        f"- recorded label replay lift gate pass rate: `{mode_rate('recorded_label_replay', 'lift_gate_pass')}`",
        f"- policy replay lift gate pass rate: `{mode_rate('policy_replay', 'lift_gate_pass')}`",
        f"- policy-vs-label mean abs error: `{action_summary.get('mean_abs_error')}`",
        f"- policy-vs-label same sign rate: `{action_summary.get('same_sign_rate')}`",
        "",
        "Interpretation: see `summary.json` for the machine-readable root-cause category.",
        "",
        "## Rollout Summary",
        "",
        "| mode | resets | lift pass rate | success max mean | max lift mean | final EE dist mean | final finger dist mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in sorted(by_mode):
        rows = by_mode[mode]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{mode}`",
                    str(len(rows)),
                    f"{mode_rate(mode, 'lift_gate_pass'):.3f}",
                    f"{np.mean([float(row.get('success_max', 0.0)) for row in rows]):.3f}",
                    f"{np.mean([float(row.get('cube_lift_height_m_max', 0.0)) for row in rows]):.4f}",
                    f"{np.mean([float(row.get('ee_to_cube_dist_m_final', math.nan)) for row in rows]):.4f}",
                    f"{np.mean([float(row.get('finger_center_to_cube_dist_m_final', math.nan)) for row in rows]):.4f}",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Policy-vs-Label By Phase/Dim", ""])
    lines.append("| phase | dim | label mean | policy mean | MAE | same sign |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for row in action_summary.get("by_phase_dim", []):
        lines.append(
            f"| `{row['phase']}` | `{row['action_name']}` | {float(row['label_mean']):.3f} | "
            f"{float(row['policy_mean']):.3f} | {float(row['mae']):.3f} | {float(row['same_sign_rate']):.3f} |"
        )
    lines.extend(["", "## Artifacts", ""])
    for name, artifact_path in payload["artifacts"].items():
        lines.append(f"- `{name}`: `{artifact_path}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("bc_label_semantics_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    policy_checkpoint = retrieve_file_path(args_cli.policy_checkpoint) if args_cli.policy_checkpoint else ""
    env_cfg.scene.num_envs = int(args_cli.num_envs)
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = int(args_cli.seed)
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_library_path = str(args_cli.grasp_prior_library_path)
    env_cfg.cube_spawn_xy_randomization = float(args_cli.cube_spawn_xy_randomization)
    if hasattr(env_cfg, "use_cuda_graph"):
        env_cfg.use_cuda_graph = False
    agent_cfg["params"]["seed"] = int(args_cli.seed)

    config = {
        "task": args_cli.task,
        "num_envs": int(args_cli.num_envs),
        "num_resets": int(args_cli.num_resets),
        "seed": int(args_cli.seed),
        "cube_spawn_xy_randomization": float(args_cli.cube_spawn_xy_randomization),
        "grasp_prior_library_path": str(args_cli.grasp_prior_library_path),
        "policy_checkpoint": policy_checkpoint,
        "approach_steps": int(args_cli.approach_steps),
        "close_steps": int(args_cli.close_steps),
        "lift_steps": int(args_cli.lift_steps),
        "close_width": float(args_cli.close_width),
        "lift_action_z": float(args_cli.lift_action_z),
        "oracle_gain": float(args_cli.oracle_gain),
        "oracle_max_position_action": float(args_cli.oracle_max_position_action),
        "track_orientation": bool(args_cli.track_orientation),
        "render": bool(args_cli.render),
        "output_dir": str(output_dir),
    }
    print("[INFO] BC label semantics audit config:")
    print_dict(config, nesting=4)

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if bool(args_cli.render) else None)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    _set_camera(task_env, env_cfg, 0)
    env = DextrahLabelVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register(
        "DextrahBcLabelWrapper",
        lambda config_name, num_actors, **kwargs: DextrahLabelGpuEnv(config_name, num_actors, **kwargs),
    )
    env_configurations.register("rlgpu", {"vecenv_type": "DextrahBcLabelWrapper", "env_creator": lambda **kwargs: env})

    player = _create_player(agent_cfg, env, policy_checkpoint) if policy_checkpoint else None
    if player is not None:
        player.model.eval()

    env_id = 0
    reset_samples: list[dict[str, Any]] = []
    action_comparison_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    rollout_summaries: list[dict[str, Any]] = []
    rendered_by_mode: dict[str, list[Path]] = {"closed_loop_label": [], "recorded_label_replay": [], "policy_replay": []}

    for reset_index in range(int(args_cli.num_resets)):
        env.reset()
        sample = _collect_reset_sample(task_env, env_id, reset_index)
        reset_samples.append(sample)
        snapshot = _snapshot_task_env_state(task_env)
        print(
            "[LABEL_AUDIT_RESET] "
            f"reset={reset_index} sample={sample['sample_index']} success={sample['reset_success']} "
            f"quality={sample['reset_quality_success']} ee={sample['ee_to_cube_dist_m']:.4f} "
            f"finger={sample['finger_center_to_cube_dist_m']:.4f}",
            flush=True,
        )

        _restore_task_env_state(task_env, snapshot)
        if player is not None:
            player.reset()
        obs = _obs_policy_tensor(env.get_current_obs())
        recorded_actions: list[torch.Tensor] = []
        closed_loop_records: list[dict[str, Any]] = []
        render_this_reset = bool(args_cli.render) and reset_index < int(args_cli.render_resets)
        if render_this_reset:
            _render_frame(
                gym_env,
                task_env,
                env_cfg,
                env_id=env_id,
                mode="closed_loop_label",
                reset_index=reset_index,
                step=0,
                phase="reset_pregrasp",
                sample=sample,
                record=None,
                frames_dir=frames_dir,
                rendered_frames=rendered_by_mode["closed_loop_label"],
            )
        total_steps = int(args_cli.approach_steps) + int(args_cli.close_steps) + int(args_cli.lift_steps)
        for step_idx in range(total_steps):
            phase = _phase_for_step(step_idx)
            label_action = _reference_action(task_env, phase)
            policy_action = _policy_action(player, obs) if player is not None else None
            _record_action_comparison(
                action_comparison_rows,
                reset_index=reset_index,
                step=step_idx + 1,
                phase=phase,
                label_action=label_action,
                policy_action=policy_action,
                obs=obs,
            )
            recorded_actions.append(label_action.detach().clone())
            step_out = env.step(label_action)
            if len(step_out) == 5:
                obs, rewards, terminated, truncated, _ = step_out
            else:
                obs, rewards, dones, _ = step_out
                terminated = dones
                truncated = torch.zeros_like(dones) if isinstance(dones, torch.Tensor) else False
            obs = _obs_policy_tensor(obs)
            record = _step_metrics(
                task_env,
                env_id,
                reset_index=reset_index,
                mode="closed_loop_label",
                step=step_idx + 1,
                phase=phase,
                action=label_action,
                reward=rewards,
                terminated=terminated,
                truncated=truncated,
            )
            closed_loop_records.append(record)
            if render_this_reset and (
                step_idx == 0
                or step_idx + 1 == total_steps
                or (step_idx + 1) % max(int(args_cli.render_interval), 1) == 0
                or bool(record["done"])
            ):
                _render_frame(
                    gym_env,
                    task_env,
                    env_cfg,
                    env_id=env_id,
                    mode="closed_loop_label",
                    reset_index=reset_index,
                    step=step_idx + 1,
                    phase=phase,
                    sample=sample,
                    record=record,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_by_mode["closed_loop_label"],
                )
            if bool(record["done"]):
                break
        trace_rows.extend(closed_loop_records)
        rollout_summaries.append(_summarize_trace(closed_loop_records, sample, "closed_loop_label"))

        for mode in ("recorded_label_replay", "policy_replay"):
            if mode == "policy_replay" and player is None:
                continue
            frames = rendered_by_mode[mode]
            records, _ = _run_mode(
                env,
                gym_env,
                task_env,
                env_cfg,
                env_id=env_id,
                reset_index=reset_index,
                mode=mode,
                sample=sample,
                snapshot=snapshot,
                actions=recorded_actions,
                player=player,
                frames_dir=frames_dir,
                rendered_frames=frames,
            )
            trace_rows.extend(records)
            rollout_summaries.append(_summarize_trace(records, sample, mode))
            print(
                "[LABEL_AUDIT_ROLLOUT] "
                f"reset={reset_index} mode={mode} steps={len(records)} "
                f"lift_max={max([float(r['cube_lift_height_m']) for r in records], default=0.0):.4f} "
                f"success_max={max([float(r['success_rate']) for r in records], default=0.0):.1f}",
                flush=True,
            )

    action_summary = _summarize_action_comparison(action_comparison_rows)
    by_mode = {mode: [row for row in rollout_summaries if row["mode"] == mode] for mode in sorted({row["mode"] for row in rollout_summaries})}

    def pass_rate(mode: str) -> float:
        rows = by_mode.get(mode, [])
        if not rows:
            return math.nan
        return float(np.mean([1.0 if bool(row.get("lift_gate_pass")) else 0.0 for row in rows]))

    closed_loop_rate = pass_rate("closed_loop_label")
    replay_rate = pass_rate("recorded_label_replay")
    policy_rate = pass_rate("policy_replay")
    if math.isfinite(closed_loop_rate) and closed_loop_rate < 0.5:
        root_cause = "label_semantics_or_reference_control_failure"
    elif math.isfinite(replay_rate) and replay_rate < 0.5:
        root_cause = "labels_need_closed_loop_correction_or_replay_state_mismatch"
    elif action_summary.get("policy_checkpoint_loaded") and float(action_summary.get("mean_abs_error", 0.0)) > 0.25:
        root_cause = "policy_label_mismatch_or_normalization_fitting_failure"
    elif math.isfinite(policy_rate) and policy_rate < 0.5:
        root_cause = "policy_closed_loop_compounding_despite_small_one_step_error"
    else:
        root_cause = "inconclusive_or_pass"

    artifacts: dict[str, str] = {
        "reset_samples": str(output_dir / "reset_samples.json"),
        "action_comparison_csv": str(output_dir / "action_comparison.csv"),
        "action_comparison_jsonl": str(output_dir / "action_comparison.jsonl"),
        "rollout_trace_csv": str(output_dir / "rollout_trace.csv"),
        "rollout_trace_jsonl": str(output_dir / "rollout_trace.jsonl"),
        "rollout_summary_csv": str(output_dir / "rollout_summary.csv"),
        "trace_plot": str(output_dir / "trace_plot.png"),
    }
    _write_json(output_dir / "reset_samples.json", {"resets": reset_samples})
    _write_csv(output_dir / "action_comparison.csv", action_comparison_rows)
    _write_jsonl(output_dir / "action_comparison.jsonl", action_comparison_rows)
    _write_csv(output_dir / "rollout_trace.csv", trace_rows)
    _write_jsonl(output_dir / "rollout_trace.jsonl", trace_rows)
    _write_csv(output_dir / "rollout_summary.csv", rollout_summaries)
    for mode, frames in rendered_by_mode.items():
        if frames:
            sheet_path = output_dir / f"{mode}_contact_sheet.jpg"
            _write_contact_sheet(frames, sheet_path)
            artifacts[f"{mode}_contact_sheet"] = str(sheet_path)
    _draw_trace_plot(trace_rows, output_dir / "trace_plot.png")

    payload = {
        "config": config,
        "reset_samples": reset_samples,
        "rollout_summaries": rollout_summaries,
        "action_comparison_summary": action_summary,
        "root_cause_category": root_cause,
        "rates": {
            "closed_loop_label_lift_gate_pass_rate": closed_loop_rate,
            "recorded_label_replay_lift_gate_pass_rate": replay_rate,
            "policy_replay_lift_gate_pass_rate": policy_rate,
        },
        "artifacts": artifacts,
    }
    report_path = output_dir / "REPORT.md"
    artifacts["report"] = str(report_path)
    payload["artifacts"] = artifacts
    _write_report(report_path, payload)
    _write_json(metrics_path, payload)
    _write_json(output_dir / "summary.json", payload)
    print("[INFO] BC label semantics summary:")
    print(json.dumps(_json_safe({"root_cause_category": root_cause, "rates": payload["rates"], "action_summary": action_summary}), indent=2, sort_keys=True))

    env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        output_dir_arg = args_cli.output_dir or datetime.now().strftime("bc_label_semantics_error_%Y%m%d_%H%M%S")
        _write_exception_artifact(Path(output_dir_arg).expanduser().resolve(), exc)
        raise
    finally:
        simulation_app.close()
