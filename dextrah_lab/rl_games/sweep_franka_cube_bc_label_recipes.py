"""Sweep closed-loop Franka cube label recipes from pass7 reset priors.

This is a diagnostic-only script. It does not alter the RL task, reward,
termination, PPO config, or reset defaults. It searches for a corrective label
recipe that actually clamps and lifts under the same pass7 reset-prior
distribution before any new BC/RL run is considered.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import traceback
from dataclasses import dataclass
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
parser.add_argument("--success_lift_height", type=float, default=0.01)
parser.add_argument("--oracle_gain", type=float, default=8.0)
parser.add_argument("--oracle_max_position_action", type=float, default=1.0)
parser.add_argument("--track_orientation", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--render", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--render_resets", type=int, default=1)
parser.add_argument("--render_interval", type=int, default=10)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument(
    "--recipe",
    action="append",
    default=None,
    help=(
        "Override recipes as name:close=<width|action>,approach=N,close_steps=N,lift=N,lift_z=Z,"
        "offset_z=M. Offsets are diagnostic-only robot-root-frame target offsets."
    ),
)
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

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils import math as math_utils
from isaaclab.utils.dict import print_dict
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesVecEnvWrapper

import isaaclab_tasks  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401


ACTION_NAMES = ("x", "y", "z", "roll", "pitch", "yaw", "gripper")


@dataclass(frozen=True)
class Recipe:
    name: str
    close_width: float | None
    close_action: float | None
    approach_steps: int
    close_steps: int
    lift_steps: int
    lift_action_z: float
    track_exact_during_lift: bool = True
    target_offset_root: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def close_action_value(self, max_gripper_width: float) -> float:
        if self.close_action is not None:
            return float(np.clip(self.close_action, -1.0, 1.0))
        if self.close_width is None:
            raise ValueError(f"Recipe {self.name!r} has neither close_width nor close_action")
        return _gripper_action_for_width(self.close_width, max_gripper_width)

    def close_label(self) -> str:
        if self.close_action is not None:
            return f"action={self.close_action:+.3f}"
        return f"width={self.close_width:.3f}"

    def target_offset_label(self) -> str:
        ox, oy, oz = self.target_offset_root
        return f"offset_root=({ox:+.3f},{oy:+.3f},{oz:+.3f})"


class SweepVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


def _default_recipes() -> list[Recipe]:
    return [
        Recipe("baseline_w055_z015", close_width=0.055, close_action=None, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("w050_z015", close_width=0.050, close_action=None, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("w045_z015", close_width=0.045, close_action=None, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("w035_z015", close_width=0.035, close_action=None, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("w035_close24_z015", close_width=0.035, close_action=None, approach_steps=16, close_steps=24, lift_steps=16, lift_action_z=0.15),
        Recipe("w035_z030", close_width=0.035, close_action=None, approach_steps=16, close_steps=12, lift_steps=16, lift_action_z=0.30),
        Recipe("act_neg025_z015", close_width=None, close_action=-0.25, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("act_neg050_z015", close_width=None, close_action=-0.50, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("act_neg100_z015", close_width=None, close_action=-1.00, approach_steps=16, close_steps=12, lift_steps=12, lift_action_z=0.15),
        Recipe("act_neg050_close24_z030", close_width=None, close_action=-0.50, approach_steps=16, close_steps=24, lift_steps=16, lift_action_z=0.30),
    ]


def _parse_recipe(text: str) -> Recipe:
    if ":" not in text:
        raise ValueError(f"Recipe must be name:key=value,... got {text!r}")
    name, spec = text.split(":", 1)
    values: dict[str, str] = {}
    for item in spec.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise ValueError(f"Recipe item must be key=value, got {item!r}")
        key, value = item.split("=", 1)
        values[key.strip()] = value.strip()
    close_width: float | None = None
    close_action: float | None = None
    close_value = values.get("close", values.get("close_width", ""))
    if close_value.startswith("action:"):
        close_action = float(close_value.split(":", 1)[1])
    elif "close_action" in values:
        close_action = float(values["close_action"])
    elif close_value:
        close_width = float(close_value)
    elif "width" in values:
        close_width = float(values["width"])
    else:
        close_width = 0.055
    offset_x = float(values.get("offset_x", values.get("target_offset_x", 0.0)))
    offset_y = float(values.get("offset_y", values.get("target_offset_y", 0.0)))
    offset_z = float(values.get("offset_z", values.get("target_offset_z", 0.0)))
    return Recipe(
        name=name.strip(),
        close_width=close_width,
        close_action=close_action,
        approach_steps=int(values.get("approach", values.get("approach_steps", 16))),
        close_steps=int(values.get("close_steps", values.get("settle", 12))),
        lift_steps=int(values.get("lift", values.get("lift_steps", 12))),
        lift_action_z=float(values.get("lift_z", values.get("lift_action_z", 0.15))),
        track_exact_during_lift=values.get("track_exact_during_lift", "true").lower() not in ("0", "false", "no"),
        target_offset_root=(offset_x, offset_y, offset_z),
    )


def _recipes() -> list[Recipe]:
    if args_cli.recipe:
        return [_parse_recipe(text) for text in args_cli.recipe]
    return _default_recipes()


def _json_safe(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return float(value.detach().float().cpu())
        return value.detach().float().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    for key in reversed(["recipe_name", "reset_index", "step", "phase"]):
        if key in fieldnames:
            fieldnames.remove(key)
            fieldnames.insert(0, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True)
    return value


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_json_safe(row), sort_keys=True) + "\n")


def _write_exception_artifact(output_dir: Path, exc: BaseException) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = traceback.format_exc()
    (output_dir / "ERROR.md").write_text(
        "# Label Recipe Sweep Error\n\n"
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


def _phase_for_step(recipe: Recipe, step_index_zero_based: int) -> str:
    if step_index_zero_based < int(recipe.approach_steps):
        return "approach"
    if step_index_zero_based < int(recipe.approach_steps) + int(recipe.close_steps):
        return "close"
    return "lift"


def _quat_identity(device: str) -> torch.Tensor:
    return torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=device)


def _pos_in_root(task_env, env_id: int, pos_w: torch.Tensor) -> torch.Tensor:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    pos_b, _ = math_utils.subtract_frame_transforms(root_pos_w, root_quat_w, pos_w.unsqueeze(0), _quat_identity(task_env.device))
    return pos_b[0]


def _compute_exact_tracking_action(task_env, gripper_action: float, target_offset_root: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> torch.Tensor:
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    task_env._compute_intermediate_values(update_success_timer=False)
    current_ee_pos_b, current_ee_quat_b = task_env._compute_ee_frame_pose()
    exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        task_env.grasp_prior_reset_exact_ee_pos_w,
        task_env.grasp_prior_reset_exact_ee_quat_w,
    )
    offset_b = torch.tensor(target_offset_root, dtype=exact_ee_pos_b.dtype, device=task_env.device).view(1, 3)
    exact_ee_pos_b = exact_ee_pos_b + offset_b
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


def _reference_action(task_env, recipe: Recipe, phase: str) -> torch.Tensor:
    open_action = _gripper_action_for_width(float(task_env.cfg.max_gripper_width), float(task_env.cfg.max_gripper_width))
    close_action = recipe.close_action_value(float(task_env.cfg.max_gripper_width))
    if phase == "approach":
        return _compute_exact_tracking_action(task_env, open_action, recipe.target_offset_root)
    if phase == "close":
        return _compute_exact_tracking_action(task_env, close_action, recipe.target_offset_root)
    if phase == "lift":
        if recipe.track_exact_during_lift:
            action = _compute_exact_tracking_action(task_env, close_action, recipe.target_offset_root)
        else:
            action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
            action[:, 6] = close_action
        action[:, 2] = float(np.clip(recipe.lift_action_z, -1.0, 1.0))
        return action.clamp(-1.0, 1.0)
    raise ValueError(f"Unknown phase {phase!r}")


def _root_state_w(asset) -> torch.Tensor:
    return torch.cat((asset.data.root_pos_w, asset.data.root_quat_w, asset.data.root_vel_w), dim=-1)


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
            value = getattr(task_env, name)
            task_tensors[name] = value.detach().clone() if isinstance(value, torch.Tensor) else value
    return {
        "version": 1,
        "num_envs": task_env.num_envs,
        "common_step_counter": int(getattr(task_env, "common_step_counter", 0)),
        "sim_step_counter": int(getattr(task_env, "_sim_step_counter", 0)),
        "task_tensors": task_tensors,
        "sim": {
            "robot_root_state": _root_state_w(task_env._robot).detach().clone(),
            "robot_joint_pos": task_env._robot.data.joint_pos.detach().clone(),
            "robot_joint_vel": task_env._robot.data.joint_vel.detach().clone(),
            "table_root_state": _root_state_w(task_env._table).detach().clone(),
            "cube_root_state": _root_state_w(task_env._cube).detach().clone(),
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
    task_env._robot.write_root_state_to_sim(sim_state["robot_root_state"].to(task_env.device))
    task_env._robot.write_joint_state_to_sim(
        sim_state["robot_joint_pos"].to(task_env.device),
        sim_state["robot_joint_vel"].to(task_env.device),
    )
    task_env._table.write_root_state_to_sim(sim_state["table_root_state"].to(task_env.device))
    task_env._cube.write_root_state_to_sim(sim_state["cube_root_state"].to(task_env.device))
    task_env._robot.set_joint_position_target(task_env.arm_joint_pos_target, joint_ids=task_env.arm_joint_ids)
    task_env._robot.set_joint_position_target(task_env.finger_joint_pos_target, joint_ids=task_env.finger_joint_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(update_success_timer=False)


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
        print(f"[WARN] Could not set sweep camera: {exc}", flush=True)


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
    width = min(image.width - 2 * margin, 1040)
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


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


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


def _step_metrics(task_env, env_id: int, *, recipe: Recipe, reset_index: int, step: int, phase: str, action: torch.Tensor, reward: Any, terminated: Any, truncated: Any) -> dict[str, Any]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    reward_value = _as_float(reward[env_id] if isinstance(reward, torch.Tensor) and reward.ndim > 0 else reward)
    terminated_flag = bool(terminated[env_id].detach().cpu()) if isinstance(terminated, torch.Tensor) else bool(terminated)
    truncated_flag = bool(truncated[env_id].detach().cpu()) if isinstance(truncated, torch.Tensor) else bool(truncated)
    action_env = action[env_id].detach().float()
    clip_fraction = float(torch.mean((torch.abs(action_env) >= 0.999).float()).cpu())
    record = {
        "recipe_name": recipe.name,
        "reset_index": int(reset_index),
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
        "action_clip_fraction": clip_fraction,
    }
    record.update(_contact_metrics(task_env, env_id))
    return record


def _summarize_trace(rows: list[dict[str, Any]], sample: dict[str, Any], recipe: Recipe, close_action: float, max_width: float) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "recipe_name": recipe.name,
        "reset_index": sample["reset_index"],
        "sample_index": sample["sample_index"],
        "close_setting": recipe.close_label(),
        "close_action": float(close_action),
        "close_target_width_m": float(recipe.close_width) if recipe.close_width is not None else float(0.5 * (close_action + 1.0) * max_width),
        "approach_steps": int(recipe.approach_steps),
        "close_steps": int(recipe.close_steps),
        "lift_steps": int(recipe.lift_steps),
        "lift_action_z": float(recipe.lift_action_z),
        "track_exact_during_lift": bool(recipe.track_exact_during_lift),
        "target_offset_root_x_m": float(recipe.target_offset_root[0]),
        "target_offset_root_y_m": float(recipe.target_offset_root[1]),
        "target_offset_root_z_m": float(recipe.target_offset_root[2]),
        "target_offset_root_norm_m": float(math.sqrt(sum(float(v) ** 2 for v in recipe.target_offset_root))),
        "reset_success": sample["reset_success"],
        "reset_quality_success": sample["reset_quality_success"],
        "immediate_done": sample["immediate_done"],
        "initial_ee_to_cube_dist_m": sample["ee_to_cube_dist_m"],
        "initial_finger_center_to_cube_dist_m": sample["finger_center_to_cube_dist_m"],
        "initial_gripper_width_m": sample["gripper_width_m"],
        "steps_completed": len(rows),
    }
    if not rows:
        summary["label_recipe_pass"] = False
        return summary
    for key in (
        "reward",
        "cube_lift_height_m",
        "ee_to_cube_dist_m",
        "finger_center_to_cube_dist_m",
        "max_finger_to_cube_dist_m",
        "gripper_width_m",
        "finger_table_clearance_m",
        "action_z",
        "action_gripper",
        "action_clip_fraction",
    ):
        values = [float(row[key]) for row in rows if row.get(key) is not None and str(row.get(key)) != ""]
        if values:
            summary[f"{key}_first"] = values[0]
            summary[f"{key}_final"] = values[-1]
            summary[f"{key}_min"] = min(values)
            summary[f"{key}_max"] = max(values)
            summary[f"{key}_mean"] = float(np.mean(values))
    lift_gate = max(float(row["cube_lift_height_m"]) for row in rows) >= float(args_cli.success_lift_height)
    plausible_contact = (
        summary.get("gripper_width_m_min", 1.0) <= float(getattr(args_cli, "cube_size_for_proxy", 0.060))
        and summary.get("finger_center_to_cube_dist_m_min", 1.0) <= 0.070
    )
    no_bad_done = not any(bool(row["terminated"]) for row in rows)
    no_table_pathology = summary.get("finger_table_clearance_m_min", 1.0) >= -0.002
    summary.update(
        {
            "success_max": max(float(row["success_rate"]) for row in rows),
            "lifted_max": max(float(row["has_lifted_cube"]) for row in rows),
            "done_seen": any(bool(row["done"]) for row in rows),
            "terminated_seen": any(bool(row["terminated"]) for row in rows),
            "truncated_seen": any(bool(row["truncated"]) for row in rows),
            "contact_seen": any(bool(row.get("contact_flag")) for row in rows if row.get("contact_flag") is not None),
            "contact_proxy_success": bool(plausible_contact),
            "lift_gate_pass": bool(lift_gate),
            "no_table_pathology": bool(no_table_pathology),
            "no_bad_done": bool(no_bad_done),
            "label_recipe_pass": bool(lift_gate and plausible_contact and no_table_pathology and no_bad_done),
        }
    )
    return summary


def _render_frame(gym_env, task_env, env_cfg, *, env_id: int, recipe: Recipe, reset_index: int, step: int, phase: str, sample: dict[str, Any], record: dict[str, Any] | None, frames_dir: Path, rendered_frames: list[Path]) -> None:
    if not bool(args_cli.render):
        return
    _set_camera(task_env, env_cfg, env_id)
    frame = _render_rgb(gym_env, task_env)
    if record is None:
        lines = [
            "reset/pregrasp before label action",
            f"recipe={recipe.name} {recipe.close_label()} lift_z={recipe.lift_action_z:+.2f}",
            recipe.target_offset_label(),
            f"sample={sample['sample_index']} reset={sample['reset_success']} quality={sample['reset_quality_success']}",
            f"cube={_fmt_vec(sample['cube_pos_env'])} exact_ee={_fmt_vec(sample['exact_ee_pos_env'])}",
            f"pregrasp_ee={_fmt_vec(sample['pregrasp_ee_pos_env'])}",
            f"ee={sample['ee_to_cube_dist_m']:.4f} finger={sample['finger_center_to_cube_dist_m']:.4f} width={sample['gripper_width_m']:.4f}",
        ]
    else:
        lines = [
            f"phase={phase} reward={record['reward']:.3f} done={record['done']} contact={record.get('contact_flag')}",
            recipe.target_offset_label(),
            f"action xyz=({record['action_x']:+.2f},{record['action_y']:+.2f},{record['action_z']:+.2f}) grip={record['action_gripper']:+.2f}",
            f"lift={record['cube_lift_height_m']:.4f} success={record['success_rate']:.1f} lifted={record['has_lifted_cube']:.1f}",
            f"ee={record['ee_to_cube_dist_m']:.4f} finger={record['finger_center_to_cube_dist_m']:.4f} maxfinger={record['max_finger_to_cube_dist_m']:.4f}",
            f"width={record['gripper_width_m']:.4f} table={record['finger_table_clearance_m']:.4f} clipfrac={record['action_clip_fraction']:.2f}",
        ]
    image = _overlay_frame(frame, f"Label recipe sweep | {recipe.name} | reset {reset_index} | step {step}", lines)
    frame_path = frames_dir / f"{_safe_name(recipe.name)}_reset_{reset_index:03d}_step_{step:03d}_{phase}.png"
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
    metrics = [
        ("gripper_width_m", "gripper width m"),
        ("cube_lift_height_m", "lift m"),
        ("finger_center_to_cube_dist_m", "finger-cube m"),
        ("action_z", "action z"),
        ("action_gripper", "gripper act"),
    ]
    recipes = sorted({str(row["recipe_name"]) for row in rows})
    palette = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22"]
    colors = {name: palette[idx % len(palette)] for idx, name in enumerate(recipes)}
    font = _font(12)
    font_b = _font(14, bold=True)
    font_t = _font(20, bold=True)
    W, H = 1600, 1100
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.text((28, 18), "Pass7 label recipe sweep traces (reset 0)", fill="#111827", font=font_t)
    panel_w = 740
    panel_h = 285
    for idx, (metric, title) in enumerate(metrics):
        x0 = 28 + (idx % 2) * (panel_w + 42)
        y0 = 70 + (idx // 2) * (panel_h + 36)
        x1, y1 = x0 + panel_w, y0 + panel_h
        draw.rectangle((x0, y0, x1, y1), outline="#c9ccd1")
        draw.text((x0 + 8, y0 + 6), title, fill="#111827", font=font_b)
        px0, py0, px1, py1 = x0 + 58, y0 + 34, x1 - 18, y1 - 42
        values = [
            float(row[metric])
            for row in rows
            if int(row["reset_index"]) == 0 and metric in row and row.get(metric) is not None
        ]
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
            draw.text((x0 + 3, y - 7), f"{val:.3g}", fill="#4b5563", font=font)
        for recipe_name in recipes:
            subset = [
                row
                for row in rows
                if row["recipe_name"] == recipe_name and int(row["reset_index"]) == 0 and metric in row
            ]
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
                draw.line(pts, fill=colors[recipe_name], width=2)
        if idx == len(metrics) - 1:
            legend_y = y1 - 34
            for ridx, recipe_name in enumerate(recipes[:10]):
                lx = px0 + (ridx % 2) * 310
                ly = legend_y - (ridx // 2) * 18
                draw.line((lx, ly, lx + 18, ly), fill=colors[recipe_name], width=3)
                draw.text((lx + 23, ly - 8), recipe_name[:34], fill="#111827", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def _aggregate_recipe_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_recipe: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_recipe.setdefault(str(row["recipe_name"]), []).append(row)
    aggregate: list[dict[str, Any]] = []
    for recipe_name, subset in by_recipe.items():
        aggregate.append(
            {
                "recipe_name": recipe_name,
                "resets": len(subset),
                "pass_rate": float(np.mean([1.0 if bool(row.get("label_recipe_pass")) else 0.0 for row in subset])),
                "lift_gate_pass_rate": float(np.mean([1.0 if bool(row.get("lift_gate_pass")) else 0.0 for row in subset])),
                "contact_proxy_success_rate": float(np.mean([1.0 if bool(row.get("contact_proxy_success")) else 0.0 for row in subset])),
                "max_lift_mean_m": float(np.mean([float(row.get("cube_lift_height_m_max", 0.0)) for row in subset])),
                "max_lift_max_m": float(np.max([float(row.get("cube_lift_height_m_max", 0.0)) for row in subset])),
                "final_lift_mean_m": float(np.mean([float(row.get("cube_lift_height_m_final", 0.0)) for row in subset])),
                "min_gripper_width_mean_m": float(np.mean([float(row.get("gripper_width_m_min", math.nan)) for row in subset])),
                "final_gripper_width_mean_m": float(np.mean([float(row.get("gripper_width_m_final", math.nan)) for row in subset])),
                "min_finger_center_mean_m": float(np.mean([float(row.get("finger_center_to_cube_dist_m_min", math.nan)) for row in subset])),
                "final_finger_center_mean_m": float(np.mean([float(row.get("finger_center_to_cube_dist_m_final", math.nan)) for row in subset])),
                "terminated_rate": float(np.mean([1.0 if bool(row.get("terminated_seen")) else 0.0 for row in subset])),
                "max_action_clip_fraction": float(np.max([float(row.get("action_clip_fraction_max", 0.0)) for row in subset])),
                "close_action": float(subset[0].get("close_action", math.nan)),
                "close_target_width_m": float(subset[0].get("close_target_width_m", math.nan)),
                "lift_action_z": float(subset[0].get("lift_action_z", math.nan)),
                "target_offset_root_x_m": float(subset[0].get("target_offset_root_x_m", math.nan)),
                "target_offset_root_y_m": float(subset[0].get("target_offset_root_y_m", math.nan)),
                "target_offset_root_z_m": float(subset[0].get("target_offset_root_z_m", math.nan)),
                "target_offset_root_norm_m": float(subset[0].get("target_offset_root_norm_m", math.nan)),
                "close_steps": int(subset[0].get("close_steps", 0)),
                "lift_steps": int(subset[0].get("lift_steps", 0)),
            }
        )
    aggregate.sort(key=lambda row: (-float(row["pass_rate"]), -float(row["max_lift_max_m"]), float(row["min_finger_center_mean_m"])))
    return aggregate


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    agg = payload["recipe_aggregate"]
    first_pass = payload.get("first_passing_recipe")
    lines = [
        "# Pass7 Corrective Label Recipe Sweep",
        "",
        "Diagnostic-only run. No training, reward, reset, or PPO changes.",
        "",
        "## Verdict",
        "",
        f"- corrected label recipe found: `{bool(first_pass)}`",
        f"- first passing recipe: `{first_pass or 'none'}`",
        f"- root recommendation: `{payload.get('recommendation')}`",
        "",
        "## Aggregate Recipe Table",
        "",
        "| recipe | pass rate | lift pass | contact proxy | max lift max m | min width mean m | final finger mean m | close action | target width m | offset root z m |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in agg:
        lines.append(
            f"| `{row['recipe_name']}` | {float(row['pass_rate']):.3f} | {float(row['lift_gate_pass_rate']):.3f} | "
            f"{float(row['contact_proxy_success_rate']):.3f} | {float(row['max_lift_max_m']):.4f} | "
            f"{float(row['min_gripper_width_mean_m']):.4f} | {float(row['final_finger_center_mean_m']):.4f} | "
            f"{float(row['close_action']):+.3f} | {float(row['close_target_width_m']):.4f} | "
            f"{float(row.get('target_offset_root_z_m', 0.0)):+.4f} |"
        )
    lines.extend(["", "## Key Artifacts", ""])
    for name, artifact_path in payload["key_artifacts"].items():
        lines.append(f"- `{name}`: `{artifact_path}`")
    lines.extend(["", "## Notes", ""])
    lines.append("- `contact_proxy_success` is a diagnostic proxy based on realized gripper width and finger-center distance; actual lift remains the hard gate.")
    lines.append("- Direct negative gripper actions are tested because this Franka action convention maps `-1` to fully closed and `+1` to open.")
    lines.append("- Non-zero `offset_root_*` fields are diagnostic-only target offsets applied to the scripted oracle action target, not to the reset prior itself.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("label_recipe_sweep_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    recipes = _recipes()

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
        "success_lift_height": float(args_cli.success_lift_height),
        "oracle_gain": float(args_cli.oracle_gain),
        "oracle_max_position_action": float(args_cli.oracle_max_position_action),
        "track_orientation": bool(args_cli.track_orientation),
        "render": bool(args_cli.render),
        "recipes": [recipe.__dict__ for recipe in recipes],
        "output_dir": str(output_dir),
    }
    print("[INFO] Label recipe sweep config:")
    print_dict(config, nesting=4)

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if bool(args_cli.render) else None)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    _set_camera(task_env, env_cfg, 0)
    env = SweepVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)
    env_id = 0

    setattr(args_cli, "cube_size_for_proxy", float(task_env.cfg.cube_size))
    reset_samples: list[dict[str, Any]] = []
    reset_snapshots: list[dict[str, Any]] = []
    for reset_index in range(int(args_cli.num_resets)):
        env.reset()
        sample = _collect_reset_sample(task_env, env_id, reset_index)
        reset_samples.append(sample)
        reset_snapshots.append(_snapshot_task_env_state(task_env))
        print(
            "[LABEL_SWEEP_RESET] "
            f"reset={reset_index} sample={sample['sample_index']} success={sample['reset_success']} "
            f"quality={sample['reset_quality_success']} ee={sample['ee_to_cube_dist_m']:.4f} "
            f"finger={sample['finger_center_to_cube_dist_m']:.4f}",
            flush=True,
        )

    trace_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    rendered_by_recipe: dict[str, list[Path]] = {recipe.name: [] for recipe in recipes}
    max_width = float(task_env.cfg.max_gripper_width)

    for recipe in recipes:
        close_action = recipe.close_action_value(max_width)
        total_steps = int(recipe.approach_steps) + int(recipe.close_steps) + int(recipe.lift_steps)
        for reset_index, (sample, snapshot) in enumerate(zip(reset_samples, reset_snapshots, strict=True)):
            _restore_task_env_state(task_env, snapshot)
            obs = _obs_policy_tensor(env.get_current_obs())
            del obs
            recipe_rows: list[dict[str, Any]] = []
            render_this = bool(args_cli.render) and reset_index < int(args_cli.render_resets)
            if render_this:
                _render_frame(
                    gym_env,
                    task_env,
                    env_cfg,
                    env_id=env_id,
                    recipe=recipe,
                    reset_index=reset_index,
                    step=0,
                    phase="reset_pregrasp",
                    sample=sample,
                    record=None,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_by_recipe[recipe.name],
                )
            for step_idx in range(total_steps):
                if not simulation_app.is_running():
                    break
                phase = _phase_for_step(recipe, step_idx)
                action = _reference_action(task_env, recipe, phase)
                step_out = env.step(action)
                if len(step_out) == 5:
                    _, rewards, terminated, truncated, _ = step_out
                else:
                    _, rewards, dones, _ = step_out
                    terminated = dones
                    truncated = torch.zeros_like(dones) if isinstance(dones, torch.Tensor) else False
                record = _step_metrics(
                    task_env,
                    env_id,
                    recipe=recipe,
                    reset_index=reset_index,
                    step=step_idx + 1,
                    phase=phase,
                    action=action,
                    reward=rewards,
                    terminated=terminated,
                    truncated=truncated,
                )
                recipe_rows.append(record)
                if render_this and (
                    step_idx == 0
                    or step_idx + 1 == total_steps
                    or (step_idx + 1) % max(int(args_cli.render_interval), 1) == 0
                    or step_idx + 1 in (recipe.approach_steps, recipe.approach_steps + recipe.close_steps)
                    or bool(record["done"])
                ):
                    _render_frame(
                        gym_env,
                        task_env,
                        env_cfg,
                        env_id=env_id,
                        recipe=recipe,
                        reset_index=reset_index,
                        step=step_idx + 1,
                        phase=phase,
                        sample=sample,
                        record=record,
                        frames_dir=frames_dir,
                        rendered_frames=rendered_by_recipe[recipe.name],
                    )
                if bool(record["done"]):
                    break
            trace_rows.extend(recipe_rows)
            summary = _summarize_trace(recipe_rows, sample, recipe, close_action, max_width)
            summary_rows.append(summary)
            print(
                "[LABEL_SWEEP_RECIPE] "
                f"recipe={recipe.name} reset={reset_index} pass={summary.get('label_recipe_pass')} "
                f"lift_max={summary.get('cube_lift_height_m_max', 0.0):.4f} "
                f"width_min={summary.get('gripper_width_m_min', math.nan):.4f} "
                f"finger_min={summary.get('finger_center_to_cube_dist_m_min', math.nan):.4f} "
                f"terminated={summary.get('terminated_seen')}",
                flush=True,
            )

    recipe_aggregate = _aggregate_recipe_summaries(summary_rows)
    first_pass = next((row["recipe_name"] for row in recipe_aggregate if float(row["pass_rate"]) >= 1.0), None)
    if first_pass is None:
        first_pass = next((row["recipe_name"] for row in recipe_aggregate if float(row["pass_rate"]) > 0.0), None)
    recommendation = (
        "generate supervised labels from the first passing recipe, then run a supervised-only gate"
        if first_pass
        else "no corrected label recipe found; continue control/close-force diagnostics before BC/RL"
    )

    artifacts: dict[str, str] = {
        "reset_samples": str(output_dir / "reset_samples.json"),
        "recipe_summary_csv": str(output_dir / "recipe_summary.csv"),
        "recipe_aggregate_csv": str(output_dir / "recipe_aggregate.csv"),
        "rollout_trace_csv": str(output_dir / "rollout_trace.csv"),
        "rollout_trace_jsonl": str(output_dir / "rollout_trace.jsonl"),
        "trace_plot": str(output_dir / "trace_plot.png"),
    }
    _write_json(output_dir / "reset_samples.json", {"resets": reset_samples})
    _write_csv(output_dir / "recipe_summary.csv", summary_rows)
    _write_csv(output_dir / "recipe_aggregate.csv", recipe_aggregate)
    _write_csv(output_dir / "rollout_trace.csv", trace_rows)
    _write_jsonl(output_dir / "rollout_trace.jsonl", trace_rows)
    _draw_trace_plot(trace_rows, output_dir / "trace_plot.png")

    for recipe_name, frames in rendered_by_recipe.items():
        if frames:
            sheet_path = output_dir / f"{_safe_name(recipe_name)}_contact_sheet.jpg"
            _write_contact_sheet(frames, sheet_path)
            artifacts[f"{recipe_name}_contact_sheet"] = str(sheet_path)

    key_artifacts = {
        "report": str(output_dir / "REPORT.md"),
        "trace_plot": str(output_dir / "trace_plot.png"),
        "recipe_summary_csv": str(output_dir / "recipe_summary.csv"),
        "recipe_aggregate_csv": str(output_dir / "recipe_aggregate.csv"),
    }
    baseline_sheet = output_dir / "baseline_w055_z015_contact_sheet.jpg"
    if baseline_sheet.exists():
        key_artifacts["baseline_contact_sheet"] = str(baseline_sheet)
    if first_pass:
        pass_sheet = output_dir / f"{_safe_name(first_pass)}_contact_sheet.jpg"
        if pass_sheet.exists():
            key_artifacts["first_pass_contact_sheet"] = str(pass_sheet)
    representative_failure = next((row["recipe_name"] for row in recipe_aggregate if float(row["pass_rate"]) == 0.0), None)
    if representative_failure:
        fail_sheet = output_dir / f"{_safe_name(representative_failure)}_contact_sheet.jpg"
        if fail_sheet.exists():
            key_artifacts["representative_failure_contact_sheet"] = str(fail_sheet)

    payload = {
        "config": config,
        "reset_samples": reset_samples,
        "recipe_summaries": summary_rows,
        "recipe_aggregate": recipe_aggregate,
        "first_passing_recipe": first_pass,
        "recommendation": recommendation,
        "artifacts": artifacts,
        "key_artifacts": key_artifacts,
    }
    report_path = output_dir / "REPORT.md"
    artifacts["report"] = str(report_path)
    payload["artifacts"] = artifacts
    payload["key_artifacts"] = key_artifacts
    _write_report(report_path, payload)
    _write_json(metrics_path, payload)
    _write_json(output_dir / "summary.json", payload)
    print("[INFO] Label recipe sweep summary:")
    print(json.dumps(_json_safe({"first_passing_recipe": first_pass, "recipe_aggregate": recipe_aggregate}), indent=2, sort_keys=True))

    env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        output_dir_arg = args_cli.output_dir or datetime.now().strftime("label_recipe_sweep_error_%Y%m%d_%H%M%S")
        _write_exception_artifact(Path(output_dir_arg).expanduser().resolve(), exc)
        raise
    finally:
        simulation_app.close()
