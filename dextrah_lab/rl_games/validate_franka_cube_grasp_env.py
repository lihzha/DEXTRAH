"""Validate the Franka cube-grasp environment before launching RL training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=8)
parser.add_argument("--num_steps", type=int, default=120)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=120)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
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

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_rewards import (
    compute_franka_cube_grasp_rewards,
)


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)


def _mean(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


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


class CheckRecorder:
    def __init__(self):
        self.records: list[dict[str, object]] = []

    def check(self, name: str, passed: bool, **details) -> None:
        self.records.append({"name": name, "passed": bool(passed), "details": details})

    @property
    def passed(self) -> bool:
        return all(bool(record["passed"]) for record in self.records)


def _reward_total(**kwargs) -> torch.Tensor:
    return sum(compute_franka_cube_grasp_rewards(**kwargs))


def _run_reward_checks(device: str, checks: CheckRecorder) -> None:
    zeros = torch.zeros(1, device=device)
    base = {
        "ee_to_cube_dist": torch.tensor([0.25], device=device),
        "finger_center_to_cube_dist": torch.tensor([0.22], device=device),
        "left_finger_to_cube_dist": torch.tensor([0.22], device=device),
        "right_finger_to_cube_dist": torch.tensor([0.22], device=device),
        "gripper_width": torch.tensor([0.08], device=device),
        "cube_lift_height": zeros.clone(),
        "cube_xy_error": zeros.clone(),
        "cube_goal_height_error": torch.tensor([0.16], device=device),
        "has_lifted_cube": torch.zeros(1, dtype=torch.bool, device=device),
        "in_success_region": torch.zeros(1, dtype=torch.bool, device=device),
        "actions": torch.zeros(1, 7, device=device),
        "target_lift_height": 0.16,
        "success_hand_dist": 0.20,
        "max_gripper_width": 0.08,
        "approach_weight": 2.0,
        "approach_sharpness": 9.0,
        "finger_approach_weight": 5.0,
        "finger_approach_sharpness": 12.0,
        "grasp_ready_weight": 4.0,
        "closed_grasp_weight": 3.0,
        "lift_weight": 180.0,
        "height_tracking_weight": 24.0,
        "height_tracking_sharpness": 18.0,
        "xy_stability_weight": 5.0,
        "xy_stability_sharpness": 14.0,
        "close_action_weight": 1.5,
        "lift_action_weight": 2.0,
        "success_bonus_weight": 80.0,
        "prelift_move_penalty_weight": -35.0,
        "close_far_penalty_weight": -8.0,
        "open_near_penalty_weight": -5.0,
        "ungrasped_lift_penalty_weight": -8.0,
        "action_penalty_weight": -0.002,
    }

    near = dict(base)
    near["ee_to_cube_dist"] = torch.tensor([0.050], device=device)
    checks.check(
        "reward_approach_increases_near_cube",
        bool((_reward_total(**near) > _reward_total(**base)).item()),
        far_reward=_mean(_reward_total(**base)),
        near_reward=_mean(_reward_total(**near)),
    )

    finger_near = dict(near)
    finger_near["finger_center_to_cube_dist"] = torch.tensor([0.055], device=device)
    finger_near["left_finger_to_cube_dist"] = torch.tensor([0.075], device=device)
    finger_near["right_finger_to_cube_dist"] = torch.tensor([0.075], device=device)
    checks.check(
        "reward_finger_approach_increases_near_cube",
        bool((_reward_total(**finger_near) > _reward_total(**near)).item()),
        near_reward=_mean(_reward_total(**near)),
        finger_near_reward=_mean(_reward_total(**finger_near)),
    )

    closed_near = dict(finger_near)
    closed_near["gripper_width"] = torch.tensor([0.024], device=device)
    closed_near["actions"] = torch.tensor([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_close_near_exceeds_open_near",
        bool((_reward_total(**closed_near) > _reward_total(**finger_near)).item()),
        open_reward=_mean(_reward_total(**finger_near)),
        closed_reward=_mean(_reward_total(**closed_near)),
    )

    lifted = dict(closed_near)
    lifted["cube_lift_height"] = torch.tensor([0.16], device=device)
    lifted["cube_goal_height_error"] = torch.tensor([0.0], device=device)
    lifted["has_lifted_cube"] = torch.ones(1, dtype=torch.bool, device=device)
    checks.check(
        "reward_actual_lift_dominates_no_lift_grasp",
        bool((_reward_total(**lifted) > 10.0 * _reward_total(**closed_near)).item()),
        no_lift_reward=_mean(_reward_total(**closed_near)),
        lifted_reward=_mean(_reward_total(**lifted)),
    )

    lift_intent = dict(closed_near)
    lift_intent["actions"] = torch.tensor([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_lift_intent_without_lift_is_capped",
        bool((_reward_total(**lift_intent) < 0.15 * _reward_total(**lifted)).item()),
        lift_intent_reward=_mean(_reward_total(**lift_intent)),
        lifted_reward=_mean(_reward_total(**lifted)),
        lifted_fraction_cap=0.15,
    )

    dragged = dict(closed_near)
    dragged["cube_xy_error"] = torch.tensor([0.090], device=device)
    checks.check(
        "reward_penalizes_prelift_dragging",
        bool((_reward_total(**dragged) < _reward_total(**closed_near)).item()),
        stable_reward=_mean(_reward_total(**closed_near)),
        dragged_reward=_mean(_reward_total(**dragged)),
    )

    success = dict(lifted)
    success["in_success_region"] = torch.ones(1, dtype=torch.bool, device=device)
    checks.check(
        "reward_success_bonus_increases",
        bool((_reward_total(**success) > _reward_total(**lifted)).item()),
        lifted_reward=_mean(_reward_total(**lifted)),
        success_reward=_mean(_reward_total(**success)),
    )

    closed_far = dict(base)
    closed_far["gripper_width"] = torch.tensor([0.0], device=device)
    checks.check(
        "reward_penalizes_closing_far_from_cube",
        bool((_reward_total(**closed_far) < _reward_total(**base)).item()),
        open_far_reward=_mean(_reward_total(**base)),
        closed_far_reward=_mean(_reward_total(**closed_far)),
    )


def _write_cube_pose(task_env, pos_local: torch.Tensor, has_lifted: bool) -> None:
    env_ids = task_env._robot._ALL_INDICES
    state = torch.zeros(task_env.num_envs, 13, device=task_env.device)
    state[:, 0:3] = pos_local + task_env.scene.env_origins
    state[:, 3] = 1.0
    task_env._cube.write_root_state_to_sim(state, env_ids=env_ids)
    task_env.has_lifted_cube[:] = bool(has_lifted)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()


def _run_predicate_checks(task_env, checks: CheckRecorder) -> None:
    finger_center = 0.5 * (task_env.left_finger_pos + task_env.right_finger_pos)
    synthetic_initial = finger_center.clone()
    synthetic_initial[:, 2] = float(task_env.cfg.cube_spawn_z)
    task_env.cube_initial_pos[:] = synthetic_initial
    task_env.cube_goal_pos[:] = synthetic_initial
    task_env.cube_goal_pos[:, 2] = synthetic_initial[:, 2] + float(task_env.cfg.cube_lift_height)

    success_pose = synthetic_initial.clone()
    success_pose[:, 2] += float(task_env.cfg.cube_success_lift_height) + 0.01
    _write_cube_pose(task_env, success_pose, has_lifted=True)
    task_env.actions[:] = 0.0
    task_env.actions[:, 2] = 1.0
    task_env.actions[:, 6] = -1.0
    checks.check(
        "success_predicate_accepts_lifted_cube_near_gripper",
        bool(task_env.in_success_region.all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        lift_height=_mean(task_env.cube_lift_height),
        xy_error=_mean(task_env.cube_xy_error),
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
    )
    closed_width = torch.full_like(task_env.gripper_width, 0.024)
    zero_lift = torch.zeros_like(task_env.cube_lift_height)
    prelift_goal_height_error = torch.full_like(task_env.cube_goal_height_error, float(task_env.cfg.cube_lift_height))
    prelift_false = torch.zeros_like(task_env.has_lifted_cube)
    prelift_actions = task_env.actions.clone()
    prelift_actions[:, 2] = 0.0
    prelift_actions[:, 6] = -1.0
    prelift_rewards = compute_franka_cube_grasp_rewards(
        task_env.ee_to_cube_dist,
        task_env.finger_center_to_cube_dist,
        task_env.left_finger_to_cube_dist,
        task_env.right_finger_to_cube_dist,
        closed_width,
        zero_lift,
        task_env.cube_xy_error,
        prelift_goal_height_error,
        prelift_false,
        prelift_false,
        prelift_actions,
        float(task_env.cfg.cube_lift_height),
        float(task_env.cfg.cube_success_hand_dist),
        float(task_env.cfg.max_gripper_width),
        float(task_env.cfg.cube_approach_weight),
        float(task_env.cfg.cube_approach_sharpness),
        float(task_env.cfg.cube_finger_approach_weight),
        float(task_env.cfg.cube_finger_approach_sharpness),
        float(task_env.cfg.cube_grasp_ready_weight),
        float(task_env.cfg.cube_closed_grasp_weight),
        float(task_env.cfg.cube_lift_weight),
        float(task_env.cfg.cube_height_tracking_weight),
        float(task_env.cfg.cube_height_tracking_sharpness),
        float(task_env.cfg.cube_xy_stability_weight),
        float(task_env.cfg.cube_xy_stability_sharpness),
        float(task_env.cfg.cube_close_action_weight),
        float(task_env.cfg.cube_lift_action_weight),
        float(task_env.cfg.cube_success_bonus_weight),
        float(task_env.cfg.cube_prelift_move_penalty_weight),
        float(task_env.cfg.cube_close_far_penalty_weight),
        float(task_env.cfg.cube_open_near_penalty_weight),
        float(task_env.cfg.cube_ungrasped_lift_penalty_weight),
        float(task_env.cfg.cube_action_penalty_weight),
    )
    grasp_ready_reward = prelift_rewards[2]
    closed_grasp_reward = prelift_rewards[3]
    close_action_reward = prelift_rewards[7]
    close_far_penalty = prelift_rewards[11]
    grasp_ready_value = _mean(grasp_ready_reward)
    closed_grasp_value = _mean(closed_grasp_reward)
    close_action_value = _mean(close_action_reward)
    close_far_penalty_value = _mean(close_far_penalty)
    checks.check(
        "reward_accepts_success_geometry_for_prelift_grasp",
        (
            grasp_ready_value > 0.05
            and closed_grasp_value > 0.01
            and close_action_value >= 0.0
            and close_far_penalty_value > -0.5
        ),
        grasp_ready_reward=grasp_ready_value,
        closed_grasp_reward=closed_grasp_value,
        close_action_reward=close_action_value,
        close_far_penalty=close_far_penalty_value,
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
        finger_center_dist=_mean(task_env.finger_center_to_cube_dist),
        ee_to_cube_dist=_mean(task_env.ee_to_cube_dist),
    )

    lifted_rewards = compute_franka_cube_grasp_rewards(
        task_env.ee_to_cube_dist,
        task_env.finger_center_to_cube_dist,
        task_env.left_finger_to_cube_dist,
        task_env.right_finger_to_cube_dist,
        closed_width,
        task_env.cube_lift_height,
        task_env.cube_xy_error,
        task_env.cube_goal_height_error,
        task_env.has_lifted_cube,
        task_env.in_success_region,
        task_env.actions,
        float(task_env.cfg.cube_lift_height),
        float(task_env.cfg.cube_success_hand_dist),
        float(task_env.cfg.max_gripper_width),
        float(task_env.cfg.cube_approach_weight),
        float(task_env.cfg.cube_approach_sharpness),
        float(task_env.cfg.cube_finger_approach_weight),
        float(task_env.cfg.cube_finger_approach_sharpness),
        float(task_env.cfg.cube_grasp_ready_weight),
        float(task_env.cfg.cube_closed_grasp_weight),
        float(task_env.cfg.cube_lift_weight),
        float(task_env.cfg.cube_height_tracking_weight),
        float(task_env.cfg.cube_height_tracking_sharpness),
        float(task_env.cfg.cube_xy_stability_weight),
        float(task_env.cfg.cube_xy_stability_sharpness),
        float(task_env.cfg.cube_close_action_weight),
        float(task_env.cfg.cube_lift_action_weight),
        float(task_env.cfg.cube_success_bonus_weight),
        float(task_env.cfg.cube_prelift_move_penalty_weight),
        float(task_env.cfg.cube_close_far_penalty_weight),
        float(task_env.cfg.cube_open_near_penalty_weight),
        float(task_env.cfg.cube_ungrasped_lift_penalty_weight),
        float(task_env.cfg.cube_action_penalty_weight),
    )
    lift_reward = lifted_rewards[4]
    lift_action_reward = lifted_rewards[8]
    success_bonus = lifted_rewards[9]
    close_far_penalty = lifted_rewards[11]
    lift_value = _mean(lift_reward)
    lift_action_value = _mean(lift_action_reward)
    success_bonus_value = _mean(success_bonus)
    close_far_penalty_value = _mean(close_far_penalty)
    checks.check(
        "reward_accepts_success_geometry_for_lift",
        (
            lift_value > 20.0
            and lift_action_value >= 0.0
            and success_bonus_value > 0.0
            and close_far_penalty_value > -0.5
        ),
        lift_reward=lift_value,
        lift_action_reward=lift_action_value,
        success_bonus=success_bonus_value,
        close_far_penalty=close_far_penalty_value,
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
        finger_center_dist=_mean(task_env.finger_center_to_cube_dist),
        ee_to_cube_dist=_mean(task_env.ee_to_cube_dist),
    )
    task_env.actions[:] = 0.0

    low_pose = synthetic_initial.clone()
    low_pose[:, 2] += 0.03
    _write_cube_pose(task_env, low_pose, has_lifted=False)
    checks.check(
        "success_predicate_rejects_low_cube",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        lift_height=_mean(task_env.cube_lift_height),
    )

    wrong_xy = success_pose.clone()
    wrong_xy[:, 1] += 0.16
    _write_cube_pose(task_env, wrong_xy, has_lifted=True)
    checks.check(
        "success_predicate_rejects_wrong_xy",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        xy_error=_mean(task_env.cube_xy_error),
    )


def _run_short_rollout(env, task_env, checks: CheckRecorder, num_steps: int, print_interval: int) -> dict[str, object]:
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
        "reset_cube_on_table",
        bool((task_env.cube_pos[:, 2] > task_env.cfg.table_surface_z).all().item()),
        cube_z_min=float(task_env.cube_pos[:, 2].detach().min().cpu()),
        table_surface_z=float(task_env.cfg.table_surface_z),
    )

    reward_values: list[float] = []
    done_count = 0
    max_lift = _mean(task_env.cube_lift_height)
    max_xy_error = _mean(task_env.cube_xy_error)
    for step in range(num_steps):
        actions = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
        if step > num_steps // 3:
            actions[:, 6] = -0.5
        if step > 2 * num_steps // 3:
            actions[:, 2] = 0.5
        step_out = env.step(actions)
        if len(step_out) == 5:
            obs, rewards, terminated, truncated, _ = step_out
            dones = torch.logical_or(terminated, truncated)
        else:
            obs, rewards, dones, _ = step_out
        policy_obs = obs["policy"] if isinstance(obs, dict) else obs
        reward_values.append(_mean(rewards))
        done_count += int(dones.float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0
        max_lift = max(max_lift, _mean(task_env.cube_lift_height))
        max_xy_error = max(max_xy_error, _mean(task_env.cube_xy_error))

        if not bool(torch.isfinite(policy_obs).all().item()):
            checks.check("rollout_observation_finite", False, step=step)
            break
        if not bool(torch.isfinite(rewards).all().item()):
            checks.check("rollout_reward_finite", False, step=step)
            break
        if print_interval > 0 and ((step + 1) % print_interval == 0 or step == 0):
            print(
                "[VALIDATE] "
                f"step={step + 1} reward={reward_values[-1]:.4f} "
                f"ee_to_cube={_mean(task_env.ee_to_cube_dist):.4f} "
                f"finger_to_cube={_mean(task_env.finger_center_to_cube_dist):.4f} "
                f"gripper_width={_mean(task_env.gripper_width):.4f} "
                f"lift={_mean(task_env.cube_lift_height):.4f} "
                f"xy_error={_mean(task_env.cube_xy_error):.4f} "
                f"success={_mean(task_env.in_success_region.float()):.4f}",
                flush=True,
            )

    checks.check(
        "rollout_observation_reward_finite",
        len(reward_values) == num_steps,
        completed_steps=len(reward_values),
        requested_steps=num_steps,
    )
    checks.check(
        "rollout_cube_stays_in_workspace",
        bool((task_env.cube_pos[:, 2] > task_env.cfg.table_surface_z - 0.08).all().item()),
        cube_z_min=float(task_env.cube_pos[:, 2].detach().min().cpu()),
        done_count=done_count,
    )
    return {
        "steps_completed": len(reward_values),
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "done_count": done_count,
        "max_mean_lift": max_lift,
        "max_mean_xy_error": max_xy_error,
        "final_cube_pos_mean": _tensor_list(task_env.cube_pos.mean(dim=0)),
        "final_gripper_width": _mean(task_env.gripper_width),
        "final_success_rate": _mean(task_env.in_success_region.float()),
    }


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    env_cfg.cube_spawn_xy_randomization = args_cli.cube_spawn_xy_randomization
    _configure_validation_camera(env_cfg)

    checks = CheckRecorder()
    _run_reward_checks(args_cli.device, checks)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    task_env = gym_env.unwrapped
    _configure_validation_camera(env_cfg, task_env)
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=min(args_cli.video_length, args_cli.num_steps),
            name_prefix="franka-cube-validate",
            disable_logger=True,
        )

    rollout_summary: dict[str, object] = {}
    env_closed = False
    try:
        reset_out = gym_env.reset()
        obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
        policy_obs = obs["policy"] if isinstance(obs, dict) else obs
        checks.check(
            "initial_observation_shape",
            tuple(policy_obs.shape) == (task_env.num_envs, task_env.cfg.observation_space),
            observed_shape=list(policy_obs.shape),
            expected_shape=[task_env.num_envs, task_env.cfg.observation_space],
        )
        _run_predicate_checks(task_env, checks)
        rollout_summary = _run_short_rollout(gym_env, task_env, checks, args_cli.num_steps, args_cli.print_interval)
    finally:
        gym_env.close()
        env_closed = True

    payload = {
        "task": args_cli.task,
        "passed": checks.passed,
        "checks": checks.records,
        "rollout": rollout_summary,
        "output_dir": str(output_dir),
        "video_enabled": args_cli.video,
        "video_folder": str(video_folder) if args_cli.video else None,
        "env_closed": env_closed,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[INFO] Wrote metrics to {metrics_path}")
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    if not checks.passed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
