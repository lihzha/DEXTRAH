"""Reward helpers for the Franka star-kitting task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_franka_star_kitting_rewards(
    ee_to_star_dist: torch.Tensor,
    finger_center_to_star_dist: torch.Tensor,
    star_lift_height: torch.Tensor,
    goal_xy_error: torch.Tensor,
    goal_height_error: torch.Tensor,
    goal_yaw_error: torch.Tensor,
    has_lifted_star: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    approach_weight: float,
    approach_sharpness: float,
    grasp_weight: float,
    grasp_sharpness: float,
    lift_weight: float,
    transport_weight: float,
    transport_xy_sharpness: float,
    yaw_weight: float,
    yaw_sharpness: float,
    placement_weight: float,
    placement_height_sharpness: float,
    success_bonus_weight: float,
    action_penalty_weight: float,
):
    """Compute shaped rewards for pick-lift-transport-place behavior."""

    lift_denom = target_lift_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    near_star = torch.exp(-approach_sharpness * ee_to_star_dist)
    finger_near_star = torch.exp(-grasp_sharpness * finger_center_to_star_dist)
    lift_progress = torch.clamp(star_lift_height / lift_denom, 0.0, 1.0)
    lifted_gate = torch.clamp(lift_progress + has_lifted_star.float(), 0.0, 1.0)

    xy_align = torch.exp(-transport_xy_sharpness * goal_xy_error)
    yaw_align = torch.exp(-yaw_sharpness * goal_yaw_error)
    height_align = torch.exp(-placement_height_sharpness * goal_height_error)

    approach_reward = approach_weight * near_star
    grasp_reward = grasp_weight * finger_near_star * (0.25 + 0.75 * near_star)
    lift_reward = lift_weight * lift_progress * (0.25 + 0.75 * finger_near_star)
    transport_reward = transport_weight * xy_align * lifted_gate
    yaw_reward = yaw_weight * yaw_align * xy_align * lifted_gate
    placement_reward = placement_weight * xy_align * yaw_align * height_align * has_lifted_star.float()
    success_bonus = success_bonus_weight * in_success_region.float()
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        grasp_reward,
        lift_reward,
        transport_reward,
        yaw_reward,
        placement_reward,
        success_bonus,
        action_penalty,
    )

