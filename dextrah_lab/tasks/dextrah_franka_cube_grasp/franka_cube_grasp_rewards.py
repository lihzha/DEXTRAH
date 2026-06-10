"""Reward helpers for the Franka single-cube grasp task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_franka_cube_grasp_rewards(
    left_finger_to_cube_dist: torch.Tensor,
    right_finger_to_cube_dist: torch.Tensor,
    gripper_width: torch.Tensor,
    cube_lift_height: torch.Tensor,
    cube_goal_height_error: torch.Tensor,
    cube_xy_error: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    max_gripper_width: float,
    approach_weight: float,
    approach_sharpness: float,
    enclosure_weight: float,
    enclosure_sharpness: float,
    lift_weight: float,
    height_tracking_weight: float,
    height_tracking_sharpness: float,
    xy_stability_weight: float,
    xy_stability_sharpness: float,
    success_bonus_weight: float,
    gripper_close_reg_weight: float,
    action_penalty_weight: float,
):
    """Compute KUKA-cube-shaped rewards for Franka cube pickup."""

    lift_denom = target_lift_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    mean_finger_to_cube_dist = 0.5 * (left_finger_to_cube_dist + right_finger_to_cube_dist)
    max_finger_to_cube_dist = torch.maximum(left_finger_to_cube_dist, right_finger_to_cube_dist)
    near_gate = torch.exp(-approach_sharpness * mean_finger_to_cube_dist)
    enclosure_gate = torch.exp(-enclosure_sharpness * max_finger_to_cube_dist)
    lift_progress = torch.clamp(cube_lift_height / lift_denom, 0.0, 1.0)
    height_tracking = torch.exp(-height_tracking_sharpness * cube_goal_height_error)
    xy_stability = torch.exp(-xy_stability_sharpness * cube_xy_error)
    gripper_width_denom = max_gripper_width
    if gripper_width_denom < 1.0e-6:
        gripper_width_denom = 1.0e-6
    gripper_open_fraction = torch.clamp(gripper_width / gripper_width_denom, 0.0, 1.0)

    approach_reward = approach_weight * near_gate
    enclosure_reward = enclosure_weight * enclosure_gate
    lift_reward = lift_weight * lift_progress * (0.2 + 0.8 * near_gate)
    height_tracking_reward = height_tracking_weight * height_tracking * near_gate
    xy_stability_reward = xy_stability_weight * xy_stability
    success_bonus = success_bonus_weight * in_success_region.float()
    gripper_close_reg = gripper_close_reg_weight * gripper_open_fraction * gripper_open_fraction
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        enclosure_reward,
        lift_reward,
        height_tracking_reward,
        xy_stability_reward,
        success_bonus,
        gripper_close_reg,
        action_penalty,
    )
