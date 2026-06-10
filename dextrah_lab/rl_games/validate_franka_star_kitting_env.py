# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in to this material, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this material and related documentation without an express
# license agreement from NVIDIA CORPORATION or its affiliates is strictly
# prohibited.

"""Validate the Franka star-kitting environment before launching RL training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Star-Kitting")
parser.add_argument("--num_envs", type=int, default=8)
parser.add_argument("--num_steps", type=int, default=180)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=180)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--camera_eye", type=float, nargs=3, default=None, help="Viewport camera eye for validation video.")
parser.add_argument(
    "--camera_target", type=float, nargs=3, default=None, help="Viewport camera target for validation video."
)
parser.add_argument("--print_interval", type=int, default=30)
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

import isaaclab.utils.math as math_utils
import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_rewards import (
    compute_franka_star_kitting_rewards,
)


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, 0.05, 0.77)


def _mean(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _mean_vec(value: torch.Tensor) -> list[float]:
    return [float(v) for v in value.detach().float().mean(dim=0).cpu()]


def _camera_tuple(values: list[float] | tuple[float, float, float] | None):
    if values is None:
        return None
    return tuple(float(v) for v in values)


def _configure_validation_camera(env_cfg, task_env=None) -> None:
    if not args_cli.video and args_cli.camera_eye is None and args_cli.camera_target is None:
        return
    if not hasattr(env_cfg, "viewer"):
        print("[WARN] Environment config has no viewer config; validation camera override skipped.", flush=True)
        return

    eye = _camera_tuple(args_cli.camera_eye) or DEFAULT_CAMERA_EYE
    target = _camera_tuple(args_cli.camera_target) or DEFAULT_CAMERA_TARGET
    if task_env is not None and hasattr(task_env, "scene"):
        env_origin = tuple(float(v) for v in task_env.scene.env_origins[0].detach().cpu())
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    print(f"[INFO] Validation video camera eye={eye} target={target}", flush=True)

    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set active validation camera: {exc}", flush=True)


def _yaw_quat_wxyz(yaw: torch.Tensor) -> torch.Tensor:
    quat = torch.zeros(yaw.shape[0], 4, device=yaw.device)
    quat[:, 0] = torch.cos(0.5 * yaw)
    quat[:, 3] = torch.sin(0.5 * yaw)
    return quat


class CheckRecorder:
    def __init__(self):
        self.records: list[dict[str, object]] = []

    def check(self, name: str, passed: bool, **details) -> None:
        self.records.append({"name": name, "passed": bool(passed), "details": details})

    @property
    def passed(self) -> bool:
        return all(bool(record["passed"]) for record in self.records)


def _reward_total(**kwargs) -> torch.Tensor:
    terms = compute_franka_star_kitting_rewards(**kwargs)
    return sum(terms)


def _run_reward_checks(device: str, checks: CheckRecorder) -> None:
    zeros = torch.zeros(1, device=device)
    ones = torch.ones(1, device=device)
    base = {
        "ee_to_star_dist": torch.tensor([0.18], device=device),
        "finger_center_to_star_dist": torch.tensor([0.18], device=device),
        "gripper_width": torch.tensor([0.08], device=device),
        "star_lift_height": zeros.clone(),
        "star_initial_xy_error": zeros.clone(),
        "goal_xy_error": torch.tensor([0.22], device=device),
        "goal_height_error": torch.tensor([0.12], device=device),
        "goal_yaw_error": torch.tensor([1.2], device=device),
        "has_lifted_star": torch.zeros(1, dtype=torch.bool, device=device),
        "in_success_region": torch.zeros(1, dtype=torch.bool, device=device),
        "actions": torch.zeros(1, 7, device=device),
        "target_lift_height": 0.08,
        "max_gripper_width": 0.08,
        "approach_weight": 2.0,
        "approach_sharpness": 9.0,
        "grasp_weight": 1.5,
        "closed_grasp_weight": 4.0,
        "grasp_sharpness": 18.0,
        "lift_weight": 16.0,
        "prelift_move_penalty_weight": -2.0,
        "close_far_penalty_weight": -1.5,
        "transport_weight": 5.0,
        "transport_xy_sharpness": 18.0,
        "yaw_weight": 3.0,
        "yaw_sharpness": 4.5,
        "placement_weight": 8.0,
        "placement_height_sharpness": 18.0,
        "success_bonus_weight": 40.0,
        "action_penalty_weight": -0.002,
    }

    near = dict(base)
    near["ee_to_star_dist"] = torch.tensor([0.025], device=device)
    checks.check(
        "reward_approach_increases_near_star",
        bool((_reward_total(**near) > _reward_total(**base)).item()),
        far_reward=_mean(_reward_total(**base)),
        near_reward=_mean(_reward_total(**near)),
    )

    lifted = dict(near)
    lifted["finger_center_to_star_dist"] = torch.tensor([0.018], device=device)
    lifted["gripper_width"] = torch.tensor([0.018], device=device)
    lifted["star_lift_height"] = torch.tensor([0.08], device=device)
    checks.check(
        "reward_lift_increases_after_grasp",
        bool((_reward_total(**lifted) > _reward_total(**near)).item()),
        near_reward=_mean(_reward_total(**near)),
        lifted_reward=_mean(_reward_total(**lifted)),
    )

    transported = dict(lifted)
    transported["has_lifted_star"] = torch.ones(1, dtype=torch.bool, device=device)
    transported["goal_xy_error"] = torch.tensor([0.015], device=device)
    checks.check(
        "reward_transport_increases_near_fixture",
        bool((_reward_total(**transported) > _reward_total(**lifted)).item()),
        lifted_reward=_mean(_reward_total(**lifted)),
        transported_reward=_mean(_reward_total(**transported)),
    )

    yaw_aligned = dict(transported)
    yaw_aligned["goal_yaw_error"] = torch.tensor([0.03], device=device)
    checks.check(
        "reward_yaw_alignment_increases",
        bool((_reward_total(**yaw_aligned) > _reward_total(**transported)).item()),
        misaligned_reward=_mean(_reward_total(**transported)),
        aligned_reward=_mean(_reward_total(**yaw_aligned)),
    )

    placed = dict(yaw_aligned)
    placed["goal_height_error"] = torch.tensor([0.005], device=device)
    placed["in_success_region"] = torch.ones(1, dtype=torch.bool, device=device)
    checks.check(
        "reward_success_bonus_increases",
        bool((_reward_total(**placed) > _reward_total(**yaw_aligned)).item()),
        aligned_reward=_mean(_reward_total(**yaw_aligned)),
        placed_reward=_mean(_reward_total(**placed)),
    )

    action_penalized = dict(placed)
    action_penalized["actions"] = ones.repeat(1, 7)
    checks.check(
        "reward_action_penalty_decreases_large_actions",
        bool((_reward_total(**action_penalized) < _reward_total(**placed)).item()),
        placed_reward=_mean(_reward_total(**placed)),
        action_penalized_reward=_mean(_reward_total(**action_penalized)),
    )

    dragged = dict(near)
    dragged["star_initial_xy_error"] = torch.tensor([0.10], device=device)
    checks.check(
        "reward_penalizes_prelift_dragging",
        bool((_reward_total(**dragged) < _reward_total(**near)).item()),
        near_reward=_mean(_reward_total(**near)),
        dragged_reward=_mean(_reward_total(**dragged)),
    )

    closed_far = dict(base)
    closed_far["gripper_width"] = torch.tensor([0.0], device=device)
    checks.check(
        "reward_penalizes_closing_far_from_star",
        bool((_reward_total(**closed_far) < _reward_total(**base)).item()),
        open_far_reward=_mean(_reward_total(**base)),
        closed_far_reward=_mean(_reward_total(**closed_far)),
    )


def _write_star_pose(task_env, pos_local: torch.Tensor, yaw: torch.Tensor, has_lifted: bool) -> None:
    env_ids = task_env._robot._ALL_INDICES
    state = torch.zeros(task_env.num_envs, 13, device=task_env.device)
    state[:, 0:3] = pos_local + task_env.scene.env_origins
    state[:, 3:7] = _yaw_quat_wxyz(yaw)
    task_env._star.write_root_state_to_sim(state, env_ids=env_ids)
    task_env.has_lifted_star[:] = bool(has_lifted)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()


def _run_predicate_checks(task_env, checks: CheckRecorder) -> None:
    goal = task_env.star_goal_pos.clone()
    goal_yaw = task_env.star_goal_yaw.clone()
    _write_star_pose(task_env, goal, goal_yaw, has_lifted=True)
    checks.check(
        "success_predicate_accepts_lifted_star_at_goal",
        bool(task_env.in_success_region.all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        xy_error=_mean(task_env.goal_xy_error),
        height_error=_mean(task_env.goal_height_error),
        yaw_error=_mean(task_env.goal_yaw_error),
    )

    _write_star_pose(task_env, goal, goal_yaw + 0.75, has_lifted=True)
    checks.check(
        "success_predicate_rejects_wrong_yaw",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        yaw_error=_mean(task_env.goal_yaw_error),
    )

    wrong_xy = goal.clone()
    wrong_xy[:, 1] += 0.08
    _write_star_pose(task_env, wrong_xy, goal_yaw, has_lifted=True)
    checks.check(
        "success_predicate_rejects_wrong_xy",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        xy_error=_mean(task_env.goal_xy_error),
    )

    _write_star_pose(task_env, goal, goal_yaw, has_lifted=False)
    checks.check(
        "success_predicate_requires_prior_lift",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
    )


def _target_actions_to_world_position(task_env, target_pos_local: torch.Tensor, gripper_command: float) -> torch.Tensor:
    ee_pos_b, _ = task_env._compute_ee_frame_pose()
    target_pos_w = target_pos_local + task_env.scene.env_origins
    target_pos_b, _ = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        target_pos_w,
        task_env._robot.data.root_quat_w,
    )
    action = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
    action[:, :3] = torch.clamp((target_pos_b - ee_pos_b) / task_env.action_scale[:3], -1.0, 1.0)
    action[:, 6] = float(gripper_command)
    return action


def _scripted_target(task_env, step: int, num_steps: int) -> tuple[torch.Tensor, float]:
    star = task_env.star_pos.detach()
    goal = task_env.star_goal_pos.detach()
    z_above_star = star[:, 2] + 0.12
    z_grasp = star[:, 2] + 0.024
    z_lift = star[:, 2] + 0.17
    z_place = goal[:, 2] + 0.045
    phase = float(step) / max(float(num_steps - 1), 1.0)

    target = torch.zeros_like(star)
    if phase < 0.34:
        target[:, 0:2] = star[:, 0:2]
        target[:, 2] = z_above_star
        gripper = 1.0
    elif phase < 0.58:
        target[:, 0:2] = star[:, 0:2]
        target[:, 2] = z_grasp
        gripper = 1.0
    elif phase < 0.74:
        target[:, 0:2] = star[:, 0:2]
        target[:, 2] = z_grasp
        gripper = -1.0
    elif phase < 0.86:
        target[:, 0:2] = star[:, 0:2]
        target[:, 2] = z_lift
        gripper = -1.0
    elif phase < 0.94:
        target[:, 0:2] = goal[:, 0:2]
        target[:, 2] = z_lift
        gripper = -1.0
    elif phase < 0.98:
        target[:, 0:2] = goal[:, 0:2]
        target[:, 2] = z_place
        gripper = -1.0
    else:
        target[:, 0:2] = goal[:, 0:2]
        target[:, 2] = z_place
        gripper = 1.0
    return target, gripper


def _run_scripted_rollout(env, task_env, checks: CheckRecorder, num_steps: int, print_interval: int) -> dict[str, object]:
    obs_out = env.reset()
    obs = obs_out[0] if isinstance(obs_out, tuple) else obs_out
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    checks.check(
        "reset_observation_shape",
        tuple(policy_obs.shape) == (task_env.num_envs, task_env.cfg.observation_space),
        observed_shape=list(policy_obs.shape),
        expected_shape=[task_env.num_envs, task_env.cfg.observation_space],
    )
    checks.check("reset_observation_finite", bool(torch.isfinite(policy_obs).all().item()))
    checks.check(
        "reset_star_on_pickup_side",
        bool((task_env.star_pos[:, 1] < 0.0).all().item()),
        star_y_mean=_mean(task_env.star_pos[:, 1]),
    )
    checks.check(
        "fixture_goal_on_placement_side",
        bool((task_env.star_goal_pos[:, 1] > 0.0).all().item()),
        goal_y_mean=_mean(task_env.star_goal_pos[:, 1]),
    )

    initial_ee = task_env.ee_pos.clone()
    initial_ee_star = _mean(task_env.ee_to_star_dist)
    initial_finger_star = _mean(task_env.finger_center_to_star_dist)
    min_ee_star = _mean(task_env.ee_to_star_dist)
    min_finger_star = _mean(task_env.finger_center_to_star_dist)
    max_star_height = _mean(task_env.star_lift_height)
    reward_values: list[float] = []
    done_count = 0
    for step in range(num_steps):
        target, gripper = _scripted_target(task_env, step, num_steps)
        actions = _target_actions_to_world_position(task_env, target, gripper)
        step_out = env.step(actions)
        if len(step_out) == 5:
            obs, rewards, terminated, truncated, _ = step_out
            dones = torch.logical_or(terminated, truncated)
        else:
            obs, rewards, dones, _ = step_out
        if isinstance(obs, dict):
            policy_obs = obs["policy"]
        else:
            policy_obs = obs
        reward_values.append(_mean(rewards))
        done_count += int(dones.float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0
        min_ee_star = min(min_ee_star, _mean(task_env.ee_to_star_dist))
        min_finger_star = min(min_finger_star, _mean(task_env.finger_center_to_star_dist))
        max_star_height = max(max_star_height, _mean(task_env.star_lift_height))

        if not bool(torch.isfinite(policy_obs).all().item()):
            checks.check("scripted_rollout_observation_finite", False, step=step)
            break
        if not bool(torch.isfinite(rewards).all().item()):
            checks.check("scripted_rollout_reward_finite", False, step=step)
            break
        if print_interval > 0 and ((step + 1) % print_interval == 0 or step == 0):
            print(
                "[VALIDATE] "
                f"step={step + 1} reward={reward_values[-1]:.4f} "
                f"ee_to_star={_mean(task_env.ee_to_star_dist):.4f} "
                f"finger_to_star={_mean(task_env.finger_center_to_star_dist):.4f} "
                f"gripper_width={_mean(task_env.gripper_width):.4f} "
                f"lift={_mean(task_env.star_lift_height):.4f} "
                f"success={_mean(task_env.in_success_region.float()):.4f}",
                flush=True,
            )

    ee_motion = torch.norm(task_env.ee_pos - initial_ee, dim=-1)
    checks.check(
        "scripted_rollout_observation_reward_finite",
        len(reward_values) == num_steps,
        completed_steps=len(reward_values),
        requested_steps=num_steps,
    )
    checks.check(
        "scripted_rollout_moves_end_effector",
        _mean(ee_motion) > 0.03,
        mean_ee_motion=_mean(ee_motion),
    )
    checks.check(
        "scripted_rollout_approaches_star",
        min_ee_star < 0.11 and (initial_ee_star < 0.12 or min_ee_star < initial_ee_star - 0.05),
        initial_ee_to_star=initial_ee_star,
        min_ee_to_star=min_ee_star,
        improvement=initial_ee_star - min_ee_star,
    )
    checks.check(
        "scripted_rollout_fingers_approach_star",
        min_finger_star < 0.085
        and (initial_finger_star < 0.085 or min_finger_star < initial_finger_star - 0.05),
        initial_finger_to_star=initial_finger_star,
        min_finger_to_star=min_finger_star,
        improvement=initial_finger_star - min_finger_star,
    )
    checks.check(
        "scripted_rollout_star_stays_in_workspace",
        bool((task_env.star_pos[:, 2] > task_env.cfg.table_surface_z - 0.08).all().item()),
        star_z_min=float(task_env.star_pos[:, 2].detach().min().cpu()),
        done_count=done_count,
    )

    return {
        "steps_completed": len(reward_values),
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "min_ee_to_star": min_ee_star,
        "initial_ee_to_star": initial_ee_star,
        "min_finger_to_star": min_finger_star,
        "initial_finger_to_star": initial_finger_star,
        "max_star_lift_height": max_star_height,
        "final_success_rate": _mean(task_env.in_success_region.float()),
        "final_ee_pos_mean": _mean_vec(task_env.ee_pos),
        "final_star_pos_mean": _mean_vec(task_env.star_pos),
        "final_goal_pos_mean": _mean_vec(task_env.star_goal_pos),
        "final_gripper_width": _mean(task_env.gripper_width),
        "done_count": done_count,
    }


def main() -> bool:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_star_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    _configure_validation_camera(env_cfg)

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    if args_cli.video:
        env = gym.wrappers.RecordVideo(
            env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=min(args_cli.video_length, args_cli.num_steps),
            name_prefix="franka-star-kitting-validation",
            disable_logger=True,
        )
    task_env = env.unwrapped
    _configure_validation_camera(env_cfg, task_env)
    checks = CheckRecorder()

    checks.check(
        "geometry_star_fits_gripper",
        bool(task_env.geometry_diagnostics["star_fits_franka_gripper"]),
        **task_env.geometry_diagnostics,
    )
    checks.check(
        "geometry_star_fits_fixture",
        bool(task_env.geometry_diagnostics["star_fits_fixture_hole"]),
        **task_env.geometry_diagnostics,
    )

    _run_reward_checks(task_env.device, checks)
    reset_out = env.reset()
    _ = reset_out
    _run_predicate_checks(task_env, checks)
    rollout = _run_scripted_rollout(env, task_env, checks, args_cli.num_steps, args_cli.print_interval)

    payload = {
        "task": args_cli.task,
        "num_envs": args_cli.num_envs,
        "num_steps": args_cli.num_steps,
        "seed": args_cli.seed,
        "passed": checks.passed,
        "checks": checks.records,
        "rollout": rollout,
        "video_enabled": bool(args_cli.video),
        "video_folder": str(video_folder) if args_cli.video else None,
        "output_dir": str(output_dir),
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    failed = not checks.passed
    env.close()
    return not failed


if __name__ == "__main__":
    exit_code = 0
    try:
        exit_code = 0 if main() else 1
    finally:
        simulation_app.close()
    raise SystemExit(exit_code)
