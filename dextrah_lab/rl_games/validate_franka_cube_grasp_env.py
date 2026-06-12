"""Validate the Franka cube-grasp environment before launching RL training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


REWARD_WEIGHT_FIELDS = (
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
    "trajectory_tracking_position_weight",
    "trajectory_tracking_orientation_weight",
    "trajectory_tracking_gripper_weight",
    "trajectory_tracking_close_action_weight",
    "trajectory_tracking_lift_action_weight",
    "trajectory_tracking_start_weight",
    "trajectory_tracking_end_weight",
)

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
parser.add_argument(
    "--trajectory_tracking_reference_path",
    type=str,
    default=None,
    help="Optional compact task-space reference JSON for the trajectory-tracking task variant.",
)
parser.add_argument("--trajectory_tracking_action_alignment_weight", type=float, default=None)
parser.add_argument("--trajectory_tracking_action_alignment_phase_start", type=float, default=None)
parser.add_argument("--trajectory_tracking_action_alignment_sharpness", type=float, default=None)
parser.add_argument("--trajectory_tracking_action_alignment_use_contact_gate", type=str, default=None)
parser.add_argument("--trajectory_tracking_teacher_force_enabled", type=str, default=None)
parser.add_argument("--trajectory_tracking_teacher_force_alpha_start", type=float, default=None)
parser.add_argument("--trajectory_tracking_teacher_force_alpha_end", type=float, default=None)
parser.add_argument("--trajectory_tracking_teacher_force_phase_end", type=float, default=None)
parser.add_argument("--trajectory_tracking_teacher_force_anneal_steps", type=float, default=None)
parser.add_argument("--trajectory_tracking_action_alignment_compare_raw_policy", type=str, default=None)
parser.add_argument("--camera_eye", type=float, nargs=3, default=None, help="Viewport camera eye for validation video.")
parser.add_argument(
    "--camera_target", type=float, nargs=3, default=None, help="Viewport camera target for validation video."
)
parser.add_argument("--print_interval", type=int, default=30)
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
for reward_weight_field in REWARD_WEIGHT_FIELDS:
    parser.add_argument(f"--{reward_weight_field}", type=float, default=None)
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
from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_traj_tracking_reference import (
    build_template_reference,
    validate_reference_payload,
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


def _optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Expected boolean string, got {value!r}")


def _collect_reward_weights(env_cfg) -> dict[str, float]:
    return {
        name: float(getattr(env_cfg, name))
        for name in REWARD_WEIGHT_FIELDS
        if hasattr(env_cfg, name)
    }


def _apply_optional_float_overrides(env_cfg, overrides: dict[str, float | None]) -> None:
    for name, value in overrides.items():
        if value is None:
            continue
        if not hasattr(env_cfg, name):
            raise ValueError(f"--{name} was provided for a task config without {name}")
        setattr(env_cfg, name, float(value))


def _run_reward_weight_config_checks(env_cfg, checks: CheckRecorder) -> None:
    reward_weights = _collect_reward_weights(env_cfg)
    checks.check(
        "reward_weight_config_finite",
        all(torch.isfinite(torch.tensor(value)).item() for value in reward_weights.values()),
        reward_weights=reward_weights,
    )


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
        "left_finger_to_cube_dist": torch.tensor([0.22], device=device),
        "right_finger_to_cube_dist": torch.tensor([0.22], device=device),
        "gripper_width": torch.tensor([0.08], device=device),
        "cube_lift_height": zeros.clone(),
        "cube_goal_height_error": torch.tensor([0.16], device=device),
        "cube_xy_error": zeros.clone(),
        "finger_table_clearance": torch.tensor([0.04], device=device),
        "in_success_region": torch.zeros(1, dtype=torch.bool, device=device),
        "actions": torch.zeros(1, 7, device=device),
        "target_lift_height": 0.16,
        "max_gripper_width": 0.08,
        "table_clearance_margin": 0.025,
        "approach_weight": 2.0,
        "approach_sharpness": 10.0,
        "enclosure_weight": 1.0,
        "enclosure_sharpness": 8.0,
        "lift_weight": 10.0,
        "height_tracking_weight": 3.0,
        "height_tracking_sharpness": 18.0,
        "xy_stability_weight": 1.0,
        "xy_stability_sharpness": 12.0,
        "success_bonus_weight": 15.0,
        "close_action_weight": 0.3,
        "lift_action_weight": 1.0,
        "descend_action_penalty_weight": -1.0,
        "table_clearance_penalty_weight": -3.0,
        "gripper_close_reg_weight": -0.002,
        "action_penalty_weight": -0.0005,
    }

    near = dict(base)
    near["left_finger_to_cube_dist"] = torch.tensor([0.075], device=device)
    near["right_finger_to_cube_dist"] = torch.tensor([0.075], device=device)
    checks.check(
        "reward_approach_increases_near_cube",
        bool((_reward_total(**near) > _reward_total(**base)).item()),
        far_reward=_mean(_reward_total(**base)),
        near_reward=_mean(_reward_total(**near)),
    )

    balanced_near = dict(near)
    imbalanced_near = dict(near)
    imbalanced_near["right_finger_to_cube_dist"] = torch.tensor([0.16], device=device)
    checks.check(
        "reward_enclosure_prefers_both_fingers_near",
        bool((_reward_total(**balanced_near) > _reward_total(**imbalanced_near)).item()),
        balanced_reward=_mean(_reward_total(**balanced_near)),
        imbalanced_reward=_mean(_reward_total(**imbalanced_near)),
    )

    closed_near = dict(balanced_near)
    closed_near["gripper_width"] = torch.tensor([0.024], device=device)
    closed_near["actions"] = torch.tensor([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_close_near_exceeds_open_near",
        bool((_reward_total(**closed_near) > _reward_total(**balanced_near)).item()),
        open_reward=_mean(_reward_total(**balanced_near)),
        closed_reward=_mean(_reward_total(**closed_near)),
    )

    lifted = dict(closed_near)
    lifted["cube_lift_height"] = torch.tensor([0.16], device=device)
    lifted["cube_goal_height_error"] = torch.tensor([0.0], device=device)
    checks.check(
        "reward_actual_lift_dominates_no_lift_grasp",
        bool((_reward_total(**lifted) > 3.0 * _reward_total(**closed_near)).item()),
        no_lift_reward=_mean(_reward_total(**closed_near)),
        lifted_reward=_mean(_reward_total(**lifted)),
        lifted_ratio_floor=3.0,
    )

    lift_intent = dict(closed_near)
    lift_intent["actions"] = torch.tensor([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_lift_intent_without_lift_is_capped",
        bool((_reward_total(**lift_intent) < 0.45 * _reward_total(**lifted)).item()),
        lift_intent_reward=_mean(_reward_total(**lift_intent)),
        lifted_reward=_mean(_reward_total(**lifted)),
        lifted_fraction_cap=0.45,
    )

    descend_intent = dict(closed_near)
    descend_intent["actions"] = torch.tensor([[0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_penalizes_descend_when_lift_ready",
        bool((_reward_total(**descend_intent) < _reward_total(**closed_near)).item()),
        closed_reward=_mean(_reward_total(**closed_near)),
        descend_reward=_mean(_reward_total(**descend_intent)),
    )

    lift_far = dict(base)
    lift_far["gripper_width"] = torch.tensor([0.024], device=device)
    lift_far["actions"] = torch.tensor([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0]], device=device)
    checks.check(
        "reward_lift_action_is_near_gated",
        bool((_reward_total(**lift_intent) > _reward_total(**lift_far)).item()),
        near_lift_intent_reward=_mean(_reward_total(**lift_intent)),
        far_lift_intent_reward=_mean(_reward_total(**lift_far)),
    )

    table_low = dict(closed_near)
    table_low["finger_table_clearance"] = torch.tensor([0.0], device=device)
    checks.check(
        "reward_penalizes_low_finger_table_clearance",
        bool((_reward_total(**table_low) < _reward_total(**closed_near)).item()),
        safe_reward=_mean(_reward_total(**closed_near)),
        low_clearance_reward=_mean(_reward_total(**table_low)),
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
        "reward_closed_gripper_regularizer_prefers_closed",
        bool((_reward_total(**closed_far) > _reward_total(**base)).item()),
        open_far_reward=_mean(_reward_total(**base)),
        closed_far_reward=_mean(_reward_total(**closed_far)),
    )


def _run_registration_checks(task: str, checks: CheckRecorder) -> None:
    registered: dict[str, str] = {}
    for task_id in ("Dextrah-Franka-Cube-Grasp", task):
        try:
            spec = gym.spec(task_id)
            registered[task_id] = str(spec.entry_point)
        except Exception as exc:
            checks.check("task_registration_resolves", False, task=task_id, error=repr(exc))
            return
    checks.check(
        "task_registration_resolves",
        True,
        baseline_entry_point=registered["Dextrah-Franka-Cube-Grasp"],
        requested_entry_point=registered[task],
    )


def _run_reference_loader_checks(checks: CheckRecorder) -> None:
    payload = build_template_reference()
    records = validate_reference_payload(payload)
    checks.check(
        "trajectory_reference_template_valid",
        all(bool(record["passed"]) for record in records),
        curobo_validated=bool(payload["source"]["curobo_validated"]),
        waypoint_count=len(payload["waypoints"]),
        failed=[record["name"] for record in records if not bool(record["passed"])],
    )

    bad_payload = build_template_reference()
    bad_payload["waypoints"][0]["joint_position"] = [0.0]
    bad_records = validate_reference_payload(bad_payload)
    bad_failed = [record["name"] for record in bad_records if not bool(record["passed"])]
    checks.check(
        "trajectory_reference_rejects_joint_arrays",
        "no_joint_trajectory_arrays" in bad_failed,
        failed=bad_failed,
    )


def _run_tracking_config_checks(env_cfg, task: str, checks: CheckRecorder) -> None:
    tracking_enabled = bool(getattr(env_cfg, "trajectory_tracking_enabled", False))
    if not tracking_enabled:
        checks.check(
            "trajectory_tracking_clean_rl_config",
            "Traj-Tracking" not in task,
            task=task,
            trajectory_tracking_enabled=tracking_enabled,
        )
        return

    reference_path = str(getattr(env_cfg, "trajectory_tracking_reference_path", "") or "")
    action_alignment_weight = float(getattr(env_cfg, "trajectory_tracking_action_alignment_weight", 0.0))
    teacher_force_enabled = bool(getattr(env_cfg, "trajectory_tracking_teacher_force_enabled", False))
    start_weight = float(getattr(env_cfg, "trajectory_tracking_start_weight", 1.0))
    end_weight = float(getattr(env_cfg, "trajectory_tracking_end_weight", start_weight))
    phase_observations = bool(getattr(env_cfg, "trajectory_tracking_phase_observations", False))
    checks.check(
        "trajectory_tracking_reference_path_configured",
        bool(reference_path),
        task=task,
        trajectory_tracking_reference_path=reference_path,
    )
    checks.check(
        "trajectory_tracking_clean_rl_config",
        action_alignment_weight == 0.0
        and not teacher_force_enabled
        and abs(start_weight - end_weight) <= 1.0e-9
        and not phase_observations,
        action_alignment_weight=action_alignment_weight,
        teacher_force_enabled=teacher_force_enabled,
        start_weight=start_weight,
        end_weight=end_weight,
        phase_observations=phase_observations,
    )


def _run_tracking_reset_checks(task_env, checks: CheckRecorder) -> dict[str, object]:
    if not bool(getattr(task_env.cfg, "trajectory_tracking_enabled", False)):
        return {"enabled": False}

    summary = (
        task_env.trajectory_tracking_reference_summary()
        if hasattr(task_env, "trajectory_tracking_reference_summary")
        else {"enabled": True, "summary_missing": True}
    )
    checks.check(
        "trajectory_tracking_reference_runtime_summary",
        bool(summary.get("enabled"))
        and int(summary.get("waypoint_count", 0)) >= 2
        and summary.get("transform_policy") == "transform_task_space_waypoints_by_cube_pose"
        and summary.get("joint_trajectory_policy") == "do_not_transform_joint_trajectories",
        **summary,
    )
    checks.check(
        "trajectory_tracking_template_marked_unvalidated",
        summary.get("curobo_validated") is False,
        **summary,
    )
    runtime_duration_s = float(summary.get("runtime_duration_s", summary.get("duration_s", 0.0)) or 0.0)
    episode_length_s = float(
        getattr(task_env.cfg, "episode_length_s", 0.0)
        or (float(getattr(task_env, "max_episode_length", 0)) * float(getattr(task_env, "dt", 0.0)))
    )
    checks.check(
        "trajectory_tracking_runtime_duration_within_episode",
        runtime_duration_s > 0.0 and (episode_length_s <= 0.0 or runtime_duration_s <= episode_length_s),
        runtime_duration_s=runtime_duration_s,
        source_duration_s=float(summary.get("source_duration_s", 0.0) or 0.0),
        configured_runtime_duration_s=float(summary.get("configured_runtime_duration_s", 0.0) or 0.0),
        runtime_retime_policy=summary.get("runtime_retime_policy"),
        episode_length_s=episode_length_s,
    )
    configured_min_gripper_width = float(summary.get("min_target_gripper_width_m", 0.0) or 0.0)
    runtime_min_gripper_width = float(summary.get("runtime_gripper_width_min_m", 0.0) or 0.0)
    checks.check(
        "trajectory_tracking_gripper_width_policy",
        runtime_min_gripper_width + 1.0e-6 >= configured_min_gripper_width,
        runtime_gripper_width_min_m=runtime_min_gripper_width,
        runtime_gripper_width_max_m=float(summary.get("runtime_gripper_width_max_m", 0.0) or 0.0),
        source_gripper_width_min_m=float(summary.get("source_gripper_width_min_m", 0.0) or 0.0),
        source_gripper_width_max_m=float(summary.get("source_gripper_width_max_m", 0.0) or 0.0),
        min_target_gripper_width_m=configured_min_gripper_width,
        gripper_schedule_policy=summary.get("gripper_schedule_policy"),
    )

    if hasattr(task_env, "_update_trajectory_tracking_targets"):
        task_env._update_trajectory_tracking_targets()
    target_tensors = {
        "traj_target_ee_pos": getattr(task_env, "traj_target_ee_pos", None),
        "traj_target_ee_quat": getattr(task_env, "traj_target_ee_quat", None),
        "traj_target_gripper_width": getattr(task_env, "traj_target_gripper_width", None),
        "traj_target_tracking_weight": getattr(task_env, "traj_target_tracking_weight", None),
        "traj_target_table_clearance": getattr(task_env, "traj_target_table_clearance", None),
    }
    finite_targets = all(value is not None and torch.isfinite(value).all().item() for value in target_tensors.values())
    min_clearance = float(target_tensors["traj_target_table_clearance"].detach().min().cpu())
    checks.check(
        "trajectory_tracking_targets_finite",
        bool(finite_targets),
        min_target_table_clearance=min_clearance,
        required_margin=float(task_env.cfg.trajectory_tracking_min_target_table_clearance),
    )
    checks.check(
        "trajectory_tracking_targets_clear_table",
        min_clearance >= float(task_env.cfg.trajectory_tracking_min_target_table_clearance),
        min_target_table_clearance=min_clearance,
        required_margin=float(task_env.cfg.trajectory_tracking_min_target_table_clearance),
    )
    return summary


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
        finger_table_clearance=_mean(task_env.finger_table_clearance),
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
    )
    closed_width = torch.full_like(task_env.gripper_width, 0.024)
    prelift_actions = task_env.actions.clone()
    prelift_actions[:, 2] = 0.0
    prelift_actions[:, 6] = -1.0
    prelift_rewards = compute_franka_cube_grasp_rewards(
        task_env.left_finger_to_cube_dist,
        task_env.right_finger_to_cube_dist,
        closed_width,
        torch.zeros_like(task_env.cube_lift_height),
        torch.full_like(task_env.cube_goal_height_error, float(task_env.cfg.cube_lift_height)),
        task_env.cube_xy_error,
        task_env.finger_table_clearance,
        torch.zeros_like(task_env.in_success_region),
        prelift_actions,
        float(task_env.cfg.cube_lift_height),
        float(task_env.cfg.max_gripper_width),
        float(task_env.cfg.finger_table_clearance_margin),
        float(task_env.cfg.cube_approach_weight),
        float(task_env.cfg.cube_approach_sharpness),
        float(task_env.cfg.cube_enclosure_weight),
        float(task_env.cfg.cube_enclosure_sharpness),
        float(task_env.cfg.cube_lift_weight),
        float(task_env.cfg.cube_height_tracking_weight),
        float(task_env.cfg.cube_height_tracking_sharpness),
        float(task_env.cfg.cube_xy_stability_weight),
        float(task_env.cfg.cube_xy_stability_sharpness),
        float(task_env.cfg.cube_success_bonus_weight),
        float(task_env.cfg.cube_close_action_weight),
        float(task_env.cfg.cube_lift_action_weight),
        float(task_env.cfg.cube_descend_action_penalty_weight),
        float(task_env.cfg.cube_table_clearance_penalty_weight),
        float(task_env.cfg.cube_gripper_close_reg_weight),
        float(task_env.cfg.cube_action_penalty_weight),
    )
    approach_reward = prelift_rewards[0]
    enclosure_reward = prelift_rewards[1]
    close_action_reward = prelift_rewards[6]
    table_clearance_penalty = prelift_rewards[9]
    gripper_close_reg = prelift_rewards[10]
    approach_value = _mean(approach_reward)
    enclosure_value = _mean(enclosure_reward)
    close_action_value = _mean(close_action_reward)
    table_clearance_penalty_value = _mean(table_clearance_penalty)
    gripper_close_reg_value = _mean(gripper_close_reg)
    approach_required = float(getattr(task_env.cfg, "cube_approach_weight", 0.0)) > 0.0
    enclosure_required = float(getattr(task_env.cfg, "cube_enclosure_weight", 0.0)) > 0.0
    checks.check(
        "reward_accepts_success_geometry_for_prelift_enclosure",
        (
            (not approach_required or approach_value > 0.10)
            and (not enclosure_required or enclosure_value > 0.10)
            and close_action_value >= 0.0
            and table_clearance_penalty_value >= -0.001
            and gripper_close_reg_value > -0.001
        ),
        approach_reward=approach_value,
        enclosure_reward=enclosure_value,
        close_action_reward=close_action_value,
        table_clearance_penalty=table_clearance_penalty_value,
        gripper_close_reg=gripper_close_reg_value,
        finger_table_clearance=_mean(task_env.finger_table_clearance),
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
        finger_center_dist=_mean(task_env.finger_center_to_cube_dist),
        ee_to_cube_dist=_mean(task_env.ee_to_cube_dist),
        cube_approach_weight=float(getattr(task_env.cfg, "cube_approach_weight", 0.0)),
        cube_enclosure_weight=float(getattr(task_env.cfg, "cube_enclosure_weight", 0.0)),
    )

    lifted_rewards = compute_franka_cube_grasp_rewards(
        task_env.left_finger_to_cube_dist,
        task_env.right_finger_to_cube_dist,
        closed_width,
        task_env.cube_lift_height,
        task_env.cube_goal_height_error,
        task_env.cube_xy_error,
        task_env.finger_table_clearance,
        task_env.in_success_region,
        task_env.actions,
        float(task_env.cfg.cube_lift_height),
        float(task_env.cfg.max_gripper_width),
        float(task_env.cfg.finger_table_clearance_margin),
        float(task_env.cfg.cube_approach_weight),
        float(task_env.cfg.cube_approach_sharpness),
        float(task_env.cfg.cube_enclosure_weight),
        float(task_env.cfg.cube_enclosure_sharpness),
        float(task_env.cfg.cube_lift_weight),
        float(task_env.cfg.cube_height_tracking_weight),
        float(task_env.cfg.cube_height_tracking_sharpness),
        float(task_env.cfg.cube_xy_stability_weight),
        float(task_env.cfg.cube_xy_stability_sharpness),
        float(task_env.cfg.cube_success_bonus_weight),
        float(task_env.cfg.cube_close_action_weight),
        float(task_env.cfg.cube_lift_action_weight),
        float(task_env.cfg.cube_descend_action_penalty_weight),
        float(task_env.cfg.cube_table_clearance_penalty_weight),
        float(task_env.cfg.cube_gripper_close_reg_weight),
        float(task_env.cfg.cube_action_penalty_weight),
    )
    lift_reward = lifted_rewards[2]
    success_bonus = lifted_rewards[5]
    lift_action_reward = lifted_rewards[7]
    lift_value = _mean(lift_reward)
    success_bonus_value = _mean(success_bonus)
    lift_action_value = _mean(lift_action_reward)
    lift_required = float(getattr(task_env.cfg, "cube_lift_weight", 0.0)) > 0.0
    success_required = float(getattr(task_env.cfg, "cube_success_bonus_weight", 0.0)) > 0.0
    checks.check(
        "reward_accepts_success_geometry_for_lift",
        (
            (not lift_required or lift_value > 1.0)
            and (not success_required or success_bonus_value > 0.0)
            and lift_action_value >= 0.0
        ),
        lift_reward=lift_value,
        success_bonus=success_bonus_value,
        lift_action_reward=lift_action_value,
        finger_table_clearance=_mean(task_env.finger_table_clearance),
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
        hand_mean_dist=_mean(task_env.hand_to_cube_mean_dist),
        hand_max_dist=_mean(task_env.hand_to_cube_max_dist),
        finger_center_dist=_mean(task_env.finger_center_to_cube_dist),
        ee_to_cube_dist=_mean(task_env.ee_to_cube_dist),
        cube_lift_weight=float(getattr(task_env.cfg, "cube_lift_weight", 0.0)),
        cube_success_bonus_weight=float(getattr(task_env.cfg, "cube_success_bonus_weight", 0.0)),
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
    checks.check(
        "reset_fingers_clear_table",
        bool((task_env.finger_table_clearance >= float(task_env.cfg.finger_table_clearance_margin)).all().item()),
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
        finger_table_clearance_mean=_mean(task_env.finger_table_clearance),
        required_margin=float(task_env.cfg.finger_table_clearance_margin),
    )

    reward_values: list[float] = []
    done_count = 0
    early_done_count = 0
    max_lift = _mean(task_env.cube_lift_height)
    max_xy_error = _mean(task_env.cube_xy_error)
    min_finger_table_clearance = _mean(task_env.finger_table_clearance)
    tracking_enabled = bool(getattr(task_env.cfg, "trajectory_tracking_enabled", False))
    tracking_log_keys = (
        "cube_traj_tracking_reward",
        "cube_traj_tracking_position_error",
        "cube_traj_tracking_orientation_error",
        "cube_traj_tracking_gripper_error",
        "cube_traj_tracking_close_action_reward",
        "cube_traj_tracking_lift_action_reward",
        "cube_traj_tracking_close_action_reward_ceiling",
        "cube_traj_tracking_lift_action_reward_ceiling",
        "cube_traj_tracking_close_action_utilization",
        "cube_traj_tracking_lift_action_utilization",
        "cube_traj_tracking_action_alignment_reward",
        "cube_traj_tracking_action_alignment_reward_ceiling",
        "cube_traj_tracking_action_alignment_utilization",
        "cube_traj_tracking_action_alignment_error",
        "cube_traj_tracking_action_alignment_mse",
        "cube_traj_tracking_action_alignment_phase_gate",
        "cube_traj_tracking_action_alignment_contact_gate",
        "cube_traj_tracking_teacher_force_alpha",
        "cube_traj_tracking_teacher_force_active_rate",
        "cube_traj_tracking_raw_policy_reference_action_error_l2",
        "cube_traj_tracking_applied_reference_action_error_l2",
        "cube_traj_tracking_applied_policy_action_error_l2",
        "cube_traj_tracking_raw_policy_action_close",
        "cube_traj_tracking_raw_policy_action_up",
        "cube_traj_tracking_raw_policy_action_z",
        "cube_traj_tracking_raw_policy_gripper_action",
        "cube_traj_tracking_applied_action_close",
        "cube_traj_tracking_applied_action_up",
        "cube_traj_tracking_applied_action_z",
        "cube_traj_tracking_applied_gripper_action",
        "cube_traj_tracking_closed_target_gate",
        "cube_traj_tracking_close_phase_gate",
        "cube_traj_tracking_lift_phase_gate",
        "cube_traj_tracking_contact_gate",
        "cube_traj_tracking_contact_distance_gate",
        "cube_traj_tracking_finger_balance_gate",
        "cube_traj_tracking_action_close",
        "cube_traj_tracking_action_up",
        "cube_traj_tracking_action_z",
        "cube_traj_tracking_gripper_action",
        "cube_traj_tracking_reference_action_close",
        "cube_traj_tracking_reference_action_up",
        "cube_traj_tracking_reference_action_z",
        "cube_traj_tracking_reference_gripper_action",
        "cube_traj_tracking_effective_phase_weight",
        "cube_traj_tracking_reference_reweight",
        "cube_traj_tracking_tracking_term_weight",
        "cube_traj_tracking_phase_progress",
        "cube_traj_tracking_curriculum_scale",
        "cube_traj_tracking_target_table_clearance",
        "cube_traj_tracking_target_table_clearance_min",
        "cube_traj_tracking_safe_target_rate",
        "cube_traj_tracking_unsafe_target_rate",
    )
    tracking_log_seen = {key: False for key in tracking_log_keys}
    tracking_log_finite = True
    tracking_reward_values: list[float] = []
    tracking_unsafe_values: list[float] = []
    tracking_clearance_values: list[float] = []
    tracking_clearance_min_values: list[float] = []
    tracking_effective_weight_values: list[float] = []
    tracking_close_action_reward_values: list[float] = []
    tracking_lift_action_reward_values: list[float] = []
    tracking_close_action_reward_ceiling_values: list[float] = []
    tracking_lift_action_reward_ceiling_values: list[float] = []
    tracking_close_action_utilization_values: list[float] = []
    tracking_lift_action_utilization_values: list[float] = []
    tracking_action_alignment_reward_values: list[float] = []
    tracking_action_alignment_reward_ceiling_values: list[float] = []
    tracking_action_alignment_utilization_values: list[float] = []
    tracking_action_alignment_error_values: list[float] = []
    tracking_action_alignment_phase_gate_values: list[float] = []
    tracking_action_alignment_contact_gate_values: list[float] = []
    tracking_teacher_force_alpha_values: list[float] = []
    tracking_teacher_force_active_values: list[float] = []
    tracking_raw_policy_reference_error_values: list[float] = []
    tracking_applied_reference_error_values: list[float] = []
    tracking_applied_policy_error_values: list[float] = []
    tracking_raw_policy_action_close_values: list[float] = []
    tracking_raw_policy_action_up_values: list[float] = []
    tracking_applied_action_close_values: list[float] = []
    tracking_applied_action_up_values: list[float] = []
    tracking_contact_gate_values: list[float] = []
    tracking_contact_distance_gate_values: list[float] = []
    tracking_finger_balance_gate_values: list[float] = []
    tracking_reference_reweight_values: list[float] = []
    tracking_term_weight_values: list[float] = []
    tracking_phase_progress_values: list[float] = []
    tracking_curriculum_scale_values: list[float] = []
    tracking_action_close_values: list[float] = []
    tracking_action_up_values: list[float] = []
    tracking_reference_action_close_values: list[float] = []
    tracking_reference_action_up_values: list[float] = []
    tracking_close_phase_gate_values: list[float] = []
    tracking_lift_phase_gate_values: list[float] = []
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
        step_done_count = int(dones.float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0
        done_count += step_done_count
        if step < min(5, num_steps):
            early_done_count += step_done_count
        max_lift = max(max_lift, _mean(task_env.cube_lift_height))
        max_xy_error = max(max_xy_error, _mean(task_env.cube_xy_error))
        min_finger_table_clearance = min(min_finger_table_clearance, _mean(task_env.finger_table_clearance))
        if tracking_enabled:
            log_terms = task_env.extras.get("log", {})
            for key in tracking_log_keys:
                value = log_terms.get(key)
                if value is None:
                    continue
                tracking_log_seen[key] = True
                if isinstance(value, torch.Tensor):
                    tracking_log_finite = tracking_log_finite and bool(torch.isfinite(value).all().item())
                if key == "cube_traj_tracking_reward":
                    tracking_reward_values.append(_mean(value))
                elif key == "cube_traj_tracking_unsafe_target_rate":
                    tracking_unsafe_values.append(_mean(value))
                elif key == "cube_traj_tracking_target_table_clearance":
                    tracking_clearance_values.append(_mean(value))
                elif key == "cube_traj_tracking_target_table_clearance_min":
                    tracking_clearance_min_values.append(_mean(value))
                elif key == "cube_traj_tracking_effective_phase_weight":
                    tracking_effective_weight_values.append(_mean(value))
                elif key == "cube_traj_tracking_close_action_reward":
                    tracking_close_action_reward_values.append(_mean(value))
                elif key == "cube_traj_tracking_lift_action_reward":
                    tracking_lift_action_reward_values.append(_mean(value))
                elif key == "cube_traj_tracking_close_action_reward_ceiling":
                    tracking_close_action_reward_ceiling_values.append(_mean(value))
                elif key == "cube_traj_tracking_lift_action_reward_ceiling":
                    tracking_lift_action_reward_ceiling_values.append(_mean(value))
                elif key == "cube_traj_tracking_close_action_utilization":
                    tracking_close_action_utilization_values.append(_mean(value))
                elif key == "cube_traj_tracking_lift_action_utilization":
                    tracking_lift_action_utilization_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_reward":
                    tracking_action_alignment_reward_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_reward_ceiling":
                    tracking_action_alignment_reward_ceiling_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_utilization":
                    tracking_action_alignment_utilization_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_error":
                    tracking_action_alignment_error_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_phase_gate":
                    tracking_action_alignment_phase_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_alignment_contact_gate":
                    tracking_action_alignment_contact_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_teacher_force_alpha":
                    tracking_teacher_force_alpha_values.append(_mean(value))
                elif key == "cube_traj_tracking_teacher_force_active_rate":
                    tracking_teacher_force_active_values.append(_mean(value))
                elif key == "cube_traj_tracking_raw_policy_reference_action_error_l2":
                    tracking_raw_policy_reference_error_values.append(_mean(value))
                elif key == "cube_traj_tracking_applied_reference_action_error_l2":
                    tracking_applied_reference_error_values.append(_mean(value))
                elif key == "cube_traj_tracking_applied_policy_action_error_l2":
                    tracking_applied_policy_error_values.append(_mean(value))
                elif key == "cube_traj_tracking_raw_policy_action_close":
                    tracking_raw_policy_action_close_values.append(_mean(value))
                elif key == "cube_traj_tracking_raw_policy_action_up":
                    tracking_raw_policy_action_up_values.append(_mean(value))
                elif key == "cube_traj_tracking_applied_action_close":
                    tracking_applied_action_close_values.append(_mean(value))
                elif key == "cube_traj_tracking_applied_action_up":
                    tracking_applied_action_up_values.append(_mean(value))
                elif key == "cube_traj_tracking_contact_gate":
                    tracking_contact_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_contact_distance_gate":
                    tracking_contact_distance_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_finger_balance_gate":
                    tracking_finger_balance_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_reference_reweight":
                    tracking_reference_reweight_values.append(_mean(value))
                elif key == "cube_traj_tracking_tracking_term_weight":
                    tracking_term_weight_values.append(_mean(value))
                elif key == "cube_traj_tracking_phase_progress":
                    tracking_phase_progress_values.append(_mean(value))
                elif key == "cube_traj_tracking_curriculum_scale":
                    tracking_curriculum_scale_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_close":
                    tracking_action_close_values.append(_mean(value))
                elif key == "cube_traj_tracking_action_up":
                    tracking_action_up_values.append(_mean(value))
                elif key == "cube_traj_tracking_reference_action_close":
                    tracking_reference_action_close_values.append(_mean(value))
                elif key == "cube_traj_tracking_reference_action_up":
                    tracking_reference_action_up_values.append(_mean(value))
                elif key == "cube_traj_tracking_close_phase_gate":
                    tracking_close_phase_gate_values.append(_mean(value))
                elif key == "cube_traj_tracking_lift_phase_gate":
                    tracking_lift_phase_gate_values.append(_mean(value))

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
                f"finger_table_clearance={_mean(task_env.finger_table_clearance):.4f} "
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
    checks.check(
        "rollout_no_immediate_termination_spike",
        early_done_count == 0,
        early_done_count=early_done_count,
        early_window_steps=min(5, num_steps),
        total_done_count=done_count,
    )
    tracking_summary: dict[str, object] = {"enabled": tracking_enabled}
    if tracking_enabled:
        missing_tracking_logs = [key for key, seen in tracking_log_seen.items() if not seen]
        tracking_summary = {
            "enabled": True,
            "missing_logs": missing_tracking_logs,
            "tracking_reward_mean": sum(tracking_reward_values) / len(tracking_reward_values)
            if tracking_reward_values
            else None,
            "tracking_reward_final": tracking_reward_values[-1] if tracking_reward_values else None,
            "tracking_unsafe_target_rate_max": max(tracking_unsafe_values) if tracking_unsafe_values else None,
            "tracking_target_table_clearance_min": min(tracking_clearance_values) if tracking_clearance_values else None,
            "tracking_target_table_clearance_batch_min": min(tracking_clearance_min_values)
            if tracking_clearance_min_values
            else None,
            "tracking_effective_phase_weight_mean": sum(tracking_effective_weight_values)
            / len(tracking_effective_weight_values)
            if tracking_effective_weight_values
            else None,
            "tracking_close_action_reward_mean": sum(tracking_close_action_reward_values)
            / len(tracking_close_action_reward_values)
            if tracking_close_action_reward_values
            else None,
            "tracking_lift_action_reward_mean": sum(tracking_lift_action_reward_values)
            / len(tracking_lift_action_reward_values)
            if tracking_lift_action_reward_values
            else None,
            "tracking_close_action_reward_ceiling_mean": sum(tracking_close_action_reward_ceiling_values)
            / len(tracking_close_action_reward_ceiling_values)
            if tracking_close_action_reward_ceiling_values
            else None,
            "tracking_lift_action_reward_ceiling_mean": sum(tracking_lift_action_reward_ceiling_values)
            / len(tracking_lift_action_reward_ceiling_values)
            if tracking_lift_action_reward_ceiling_values
            else None,
            "tracking_close_action_utilization_mean": sum(tracking_close_action_utilization_values)
            / len(tracking_close_action_utilization_values)
            if tracking_close_action_utilization_values
            else None,
            "tracking_lift_action_utilization_mean": sum(tracking_lift_action_utilization_values)
            / len(tracking_lift_action_utilization_values)
            if tracking_lift_action_utilization_values
            else None,
            "tracking_action_alignment_reward_mean": sum(tracking_action_alignment_reward_values)
            / len(tracking_action_alignment_reward_values)
            if tracking_action_alignment_reward_values
            else None,
            "tracking_action_alignment_reward_ceiling_mean": sum(tracking_action_alignment_reward_ceiling_values)
            / len(tracking_action_alignment_reward_ceiling_values)
            if tracking_action_alignment_reward_ceiling_values
            else None,
            "tracking_action_alignment_utilization_mean": sum(tracking_action_alignment_utilization_values)
            / len(tracking_action_alignment_utilization_values)
            if tracking_action_alignment_utilization_values
            else None,
            "tracking_action_alignment_error_mean": sum(tracking_action_alignment_error_values)
            / len(tracking_action_alignment_error_values)
            if tracking_action_alignment_error_values
            else None,
            "tracking_action_alignment_phase_gate_final": tracking_action_alignment_phase_gate_values[-1]
            if tracking_action_alignment_phase_gate_values
            else None,
            "tracking_action_alignment_contact_gate_mean": sum(tracking_action_alignment_contact_gate_values)
            / len(tracking_action_alignment_contact_gate_values)
            if tracking_action_alignment_contact_gate_values
            else None,
            "tracking_teacher_force_alpha_mean": sum(tracking_teacher_force_alpha_values)
            / len(tracking_teacher_force_alpha_values)
            if tracking_teacher_force_alpha_values
            else None,
            "tracking_teacher_force_active_mean": sum(tracking_teacher_force_active_values)
            / len(tracking_teacher_force_active_values)
            if tracking_teacher_force_active_values
            else None,
            "tracking_raw_policy_reference_action_error_l2_mean": sum(tracking_raw_policy_reference_error_values)
            / len(tracking_raw_policy_reference_error_values)
            if tracking_raw_policy_reference_error_values
            else None,
            "tracking_applied_reference_action_error_l2_mean": sum(tracking_applied_reference_error_values)
            / len(tracking_applied_reference_error_values)
            if tracking_applied_reference_error_values
            else None,
            "tracking_applied_policy_action_error_l2_mean": sum(tracking_applied_policy_error_values)
            / len(tracking_applied_policy_error_values)
            if tracking_applied_policy_error_values
            else None,
            "tracking_raw_policy_action_close_mean": sum(tracking_raw_policy_action_close_values)
            / len(tracking_raw_policy_action_close_values)
            if tracking_raw_policy_action_close_values
            else None,
            "tracking_raw_policy_action_up_mean": sum(tracking_raw_policy_action_up_values)
            / len(tracking_raw_policy_action_up_values)
            if tracking_raw_policy_action_up_values
            else None,
            "tracking_applied_action_close_mean": sum(tracking_applied_action_close_values)
            / len(tracking_applied_action_close_values)
            if tracking_applied_action_close_values
            else None,
            "tracking_applied_action_up_mean": sum(tracking_applied_action_up_values)
            / len(tracking_applied_action_up_values)
            if tracking_applied_action_up_values
            else None,
            "tracking_contact_gate_mean": sum(tracking_contact_gate_values) / len(tracking_contact_gate_values)
            if tracking_contact_gate_values
            else None,
            "tracking_contact_distance_gate_mean": sum(tracking_contact_distance_gate_values)
            / len(tracking_contact_distance_gate_values)
            if tracking_contact_distance_gate_values
            else None,
            "tracking_finger_balance_gate_mean": sum(tracking_finger_balance_gate_values)
            / len(tracking_finger_balance_gate_values)
            if tracking_finger_balance_gate_values
            else None,
            "tracking_reference_reweight_mean": sum(tracking_reference_reweight_values)
            / len(tracking_reference_reweight_values)
            if tracking_reference_reweight_values
            else None,
            "tracking_term_weight_mean": sum(tracking_term_weight_values) / len(tracking_term_weight_values)
            if tracking_term_weight_values
            else None,
            "tracking_phase_progress_final": tracking_phase_progress_values[-1]
            if tracking_phase_progress_values
            else None,
            "tracking_phase_progress_max": max(tracking_phase_progress_values) if tracking_phase_progress_values else None,
            "tracking_curriculum_scale_min": min(tracking_curriculum_scale_values)
            if tracking_curriculum_scale_values
            else None,
            "tracking_curriculum_scale_max": max(tracking_curriculum_scale_values)
            if tracking_curriculum_scale_values
            else None,
            "tracking_action_close_mean": sum(tracking_action_close_values) / len(tracking_action_close_values)
            if tracking_action_close_values
            else None,
            "tracking_action_up_mean": sum(tracking_action_up_values) / len(tracking_action_up_values)
            if tracking_action_up_values
            else None,
            "tracking_reference_action_close_mean": sum(tracking_reference_action_close_values)
            / len(tracking_reference_action_close_values)
            if tracking_reference_action_close_values
            else None,
            "tracking_reference_action_up_mean": sum(tracking_reference_action_up_values)
            / len(tracking_reference_action_up_values)
            if tracking_reference_action_up_values
            else None,
            "tracking_close_phase_gate_final": tracking_close_phase_gate_values[-1]
            if tracking_close_phase_gate_values
            else None,
            "tracking_lift_phase_gate_final": tracking_lift_phase_gate_values[-1]
            if tracking_lift_phase_gate_values
            else None,
        }
        checks.check(
            "trajectory_tracking_logs_present_and_finite",
            len(missing_tracking_logs) == 0 and tracking_log_finite,
            **tracking_summary,
        )
        checks.check(
            "trajectory_tracking_runtime_targets_safe",
            bool(tracking_unsafe_values) and max(tracking_unsafe_values) <= 0.0,
            **tracking_summary,
        )
        reference_duration_s = float(getattr(task_env, "traj_ref_duration", 0.0) or 0.0)
        rollout_duration_s = float(num_steps) * float(getattr(task_env, "dt", 0.0) or 0.0)
        should_reach_reference_end = reference_duration_s > 0.0 and rollout_duration_s + 1.0e-6 >= reference_duration_s
        phase_reached_end = bool(tracking_phase_progress_values) and max(tracking_phase_progress_values) >= 0.99
        checks.check(
            "trajectory_tracking_phase_reaches_reference_end",
            (not should_reach_reference_end) or phase_reached_end,
            reference_duration_s=reference_duration_s,
            rollout_duration_s=rollout_duration_s,
            should_reach_reference_end=should_reach_reference_end,
            **tracking_summary,
        )
        checks.check(
            "trajectory_tracking_action_alignment_disabled",
            bool(tracking_action_alignment_reward_ceiling_values)
            and max(tracking_action_alignment_reward_ceiling_values) <= 0.0,
            **tracking_summary,
        )
        checks.check(
            "trajectory_tracking_teacher_force_disabled",
            bool(tracking_teacher_force_active_values)
            and max(tracking_teacher_force_active_values) <= 0.0
            and bool(tracking_teacher_force_alpha_values)
            and max(tracking_teacher_force_alpha_values) <= 0.0,
            **tracking_summary,
        )
        checks.check(
            "trajectory_tracking_curriculum_constant",
            bool(tracking_curriculum_scale_values)
            and max(tracking_curriculum_scale_values) == min(tracking_curriculum_scale_values),
            **tracking_summary,
        )
    return {
        "steps_completed": len(reward_values),
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "done_count": done_count,
        "early_done_count": early_done_count,
        "max_mean_lift": max_lift,
        "max_mean_xy_error": max_xy_error,
        "min_mean_finger_table_clearance": min_finger_table_clearance,
        "final_cube_pos_mean": _tensor_list(task_env.cube_pos.mean(dim=0)),
        "final_gripper_width": _mean(task_env.gripper_width),
        "final_success_rate": _mean(task_env.in_success_region.float()),
        "tracking": tracking_summary,
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
    if args_cli.trajectory_tracking_reference_path:
        if not hasattr(env_cfg, "trajectory_tracking_reference_path"):
            raise ValueError(
                "--trajectory_tracking_reference_path was provided for a task config "
                "without trajectory_tracking_reference_path"
            )
        env_cfg.trajectory_tracking_reference_path = str(
            Path(args_cli.trajectory_tracking_reference_path).expanduser().resolve()
        )
    trajectory_overrides = {
        "trajectory_tracking_action_alignment_weight": args_cli.trajectory_tracking_action_alignment_weight,
        "trajectory_tracking_action_alignment_phase_start": args_cli.trajectory_tracking_action_alignment_phase_start,
        "trajectory_tracking_action_alignment_sharpness": args_cli.trajectory_tracking_action_alignment_sharpness,
        "trajectory_tracking_teacher_force_alpha_start": args_cli.trajectory_tracking_teacher_force_alpha_start,
        "trajectory_tracking_teacher_force_alpha_end": args_cli.trajectory_tracking_teacher_force_alpha_end,
        "trajectory_tracking_teacher_force_phase_end": args_cli.trajectory_tracking_teacher_force_phase_end,
        "trajectory_tracking_teacher_force_anneal_steps": args_cli.trajectory_tracking_teacher_force_anneal_steps,
    }
    for name, value in trajectory_overrides.items():
        if value is not None:
            if not hasattr(env_cfg, name):
                raise ValueError(f"--{name} was provided for a task config without {name}")
            setattr(env_cfg, name, float(value))
    _apply_optional_float_overrides(
        env_cfg,
        {name: getattr(args_cli, name) for name in REWARD_WEIGHT_FIELDS},
    )
    use_contact_gate = _optional_bool(args_cli.trajectory_tracking_action_alignment_use_contact_gate)
    if use_contact_gate is not None:
        if not hasattr(env_cfg, "trajectory_tracking_action_alignment_use_contact_gate"):
            raise ValueError(
                "--trajectory_tracking_action_alignment_use_contact_gate was provided for a task config "
                "without trajectory_tracking_action_alignment_use_contact_gate"
            )
        env_cfg.trajectory_tracking_action_alignment_use_contact_gate = bool(use_contact_gate)
    teacher_force_enabled = _optional_bool(args_cli.trajectory_tracking_teacher_force_enabled)
    if teacher_force_enabled is not None:
        if not hasattr(env_cfg, "trajectory_tracking_teacher_force_enabled"):
            raise ValueError(
                "--trajectory_tracking_teacher_force_enabled was provided for a task config "
                "without trajectory_tracking_teacher_force_enabled"
            )
        env_cfg.trajectory_tracking_teacher_force_enabled = bool(teacher_force_enabled)
    compare_raw_policy = _optional_bool(args_cli.trajectory_tracking_action_alignment_compare_raw_policy)
    if compare_raw_policy is not None:
        if not hasattr(env_cfg, "trajectory_tracking_action_alignment_compare_raw_policy"):
            raise ValueError(
                "--trajectory_tracking_action_alignment_compare_raw_policy was provided for a task config "
                "without trajectory_tracking_action_alignment_compare_raw_policy"
            )
        env_cfg.trajectory_tracking_action_alignment_compare_raw_policy = bool(compare_raw_policy)
    _configure_validation_camera(env_cfg)

    checks = CheckRecorder()
    _run_registration_checks(args_cli.task, checks)
    _run_reference_loader_checks(checks)
    _run_reward_checks(args_cli.device, checks)
    _run_reward_weight_config_checks(env_cfg, checks)
    _run_tracking_config_checks(env_cfg, args_cli.task, checks)

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
        tracking_reference_summary = _run_tracking_reset_checks(task_env, checks)
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
        "trajectory_tracking_reference_path": getattr(env_cfg, "trajectory_tracking_reference_path", None),
        "reward_weights": _collect_reward_weights(env_cfg),
        "tracking_reference": tracking_reference_summary,
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
