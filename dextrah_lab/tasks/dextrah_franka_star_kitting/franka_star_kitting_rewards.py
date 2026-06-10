"""Reward helpers for the Franka star-kitting task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_franka_star_kitting_rewards(
    ee_to_star_dist: torch.Tensor,
    finger_center_to_star_dist: torch.Tensor,
    gripper_width: torch.Tensor,
    star_lift_height: torch.Tensor,
    star_initial_xy_error: torch.Tensor,
    goal_xy_error: torch.Tensor,
    goal_height_error: torch.Tensor,
    goal_yaw_error: torch.Tensor,
    has_lifted_star: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    max_gripper_width: float,
    approach_weight: float,
    approach_sharpness: float,
    finger_approach_weight: float,
    finger_approach_sharpness: float,
    grasp_weight: float,
    closed_grasp_weight: float,
    grasp_sharpness: float,
    lift_weight: float,
    lift_action_weight: float,
    close_near_weight: float,
    prelift_move_penalty_weight: float,
    close_far_penalty_weight: float,
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

    lift_reward_start_height = 0.004
    lift_denom = target_lift_height - lift_reward_start_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    near_star = torch.exp(-approach_sharpness * ee_to_star_dist)
    finger_approach = torch.exp(-finger_approach_sharpness * finger_center_to_star_dist)
    finger_near_star = torch.exp(-grasp_sharpness * finger_center_to_star_dist)
    finger_contact_gate = torch.clamp((0.095 - finger_center_to_star_dist) / 0.075, 0.0, 1.0)
    close_near_gate = torch.clamp((0.130 - finger_center_to_star_dist) / 0.085, 0.0, 1.0)
    lift_credit_gate = torch.clamp((0.140 - ee_to_star_dist) / 0.100, 0.0, 1.0)
    lift_progress = torch.clamp((star_lift_height - lift_reward_start_height) / lift_denom, 0.0, 1.0)
    lifted_gate = has_lifted_star.float()

    gripper_denom = 0.5 * max_gripper_width
    if gripper_denom < 1.0e-6:
        gripper_denom = 1.0e-6
    closed_gripper = torch.clamp((0.70 * max_gripper_width - gripper_width) / gripper_denom, 0.0, 1.0)
    close_near_ready = close_near_gate * (0.20 + 0.80 * near_star)
    grasp_ready = finger_contact_gate * (0.35 + 0.65 * finger_near_star) * (0.25 + 0.75 * near_star)
    prelift_gate = 1.0 - torch.clamp(lift_progress + has_lifted_star.float(), 0.0, 1.0)
    prelift_xy_motion = torch.clamp((star_initial_xy_error - 0.012) / 0.055, 0.0, 1.0)
    close_far_penalty_gate = torch.clamp(1.0 - finger_contact_gate, 0.0, 1.0)

    xy_align = torch.exp(-transport_xy_sharpness * goal_xy_error)
    yaw_align = torch.exp(-yaw_sharpness * goal_yaw_error)
    height_align = torch.exp(-placement_height_sharpness * goal_height_error)

    approach_reward = approach_weight * near_star
    finger_approach_reward = finger_approach_weight * finger_approach
    grasp_reward = grasp_weight * grasp_ready * (0.25 + 0.75 * closed_gripper)
    closed_grasp_reward = closed_grasp_weight * grasp_ready * closed_gripper
    lift_reward = lift_weight * lift_progress * (0.35 + 0.65 * lift_credit_gate) * (0.25 + 0.75 * closed_gripper)
    close_near_reward = close_near_weight * close_near_ready * closed_gripper
    lift_action_reward = (
        lift_action_weight * prelift_gate * close_near_ready * closed_gripper * torch.clamp(actions[:, 2], 0.0, 1.0)
    )
    transport_reward = transport_weight * xy_align * lifted_gate
    yaw_reward = yaw_weight * yaw_align * xy_align * lifted_gate
    placement_reward = placement_weight * xy_align * yaw_align * height_align * has_lifted_star.float()
    success_bonus = success_bonus_weight * in_success_region.float()
    prelift_move_penalty = prelift_move_penalty_weight * prelift_gate * prelift_xy_motion
    close_far_penalty = close_far_penalty_weight * closed_gripper * close_far_penalty_gate * (0.20 + 0.80 * near_star)
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        finger_approach_reward,
        grasp_reward,
        closed_grasp_reward,
        lift_reward,
        close_near_reward,
        lift_action_reward,
        transport_reward,
        yaw_reward,
        placement_reward,
        success_bonus,
        prelift_move_penalty,
        close_far_penalty,
        action_penalty,
    )
