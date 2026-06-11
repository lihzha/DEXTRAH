"""Reward helpers for the Franka star-kitting task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_franka_star_kitting_rewards(
    ee_to_star_dist: torch.Tensor,
    finger_center_to_star_dist: torch.Tensor,
    left_finger_to_star_dist: torch.Tensor,
    right_finger_to_star_dist: torch.Tensor,
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
    grasp_pose_weight: float,
    both_fingers_near_weight: float,
    lift_ready_weight: float,
    grasp_weight: float,
    closed_grasp_weight: float,
    grasp_sharpness: float,
    lift_weight: float,
    descend_action_weight: float,
    lift_action_weight: float,
    close_near_weight: float,
    close_action_weight: float,
    prelift_move_penalty_weight: float,
    prelift_stall_penalty_weight: float,
    close_far_penalty_weight: float,
    open_near_penalty_weight: float,
    ungrasped_lift_penalty_weight: float,
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

    lift_reward_start_height = 0.001
    lift_denom = target_lift_height - lift_reward_start_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    near_star = torch.exp(-approach_sharpness * ee_to_star_dist)
    max_finger_to_star_dist = torch.maximum(left_finger_to_star_dist, right_finger_to_star_dist)
    finger_distance_asymmetry = torch.abs(left_finger_to_star_dist - right_finger_to_star_dist)
    finger_balance_gate = 1.0 - torch.clamp((finger_distance_asymmetry - 0.020) / 0.065, 0.0, 1.0)
    finger_approach = torch.exp(-finger_approach_sharpness * max_finger_to_star_dist) * (
        0.35 + 0.65 * finger_balance_gate
    )
    finger_near_star = torch.exp(-grasp_sharpness * max_finger_to_star_dist) * (
        0.25 + 0.75 * finger_balance_gate
    )
    ee_grasp_pose = torch.exp(-45.0 * ee_to_star_dist)
    finger_contact_gate = torch.clamp((0.128 - max_finger_to_star_dist) / 0.070, 0.0, 1.0) * finger_balance_gate
    close_near_gate = (
        torch.clamp((0.172 - max_finger_to_star_dist) / 0.120, 0.0, 1.0)
        * (0.20 + 0.80 * finger_balance_gate)
    )
    left_finger_gate = torch.clamp((0.155 - left_finger_to_star_dist) / 0.085, 0.0, 1.0)
    right_finger_gate = torch.clamp((0.155 - right_finger_to_star_dist) / 0.085, 0.0, 1.0)
    both_fingers_near_gate = (
        torch.clamp((0.162 - max_finger_to_star_dist) / 0.085, 0.0, 1.0) * finger_balance_gate
    )
    tight_both_fingers_gate = (
        torch.clamp((0.136 - max_finger_to_star_dist) / 0.056, 0.0, 1.0) * finger_balance_gate
    )
    tight_finger_center_gate = torch.clamp((0.126 - finger_center_to_star_dist) / 0.036, 0.0, 1.0)
    tight_ee_gate = torch.clamp((0.125 - ee_to_star_dist) / 0.055, 0.0, 1.0)
    lift_ready_gate = tight_ee_gate * tight_finger_center_gate * tight_both_fingers_gate
    pregrasp_ee_gate = torch.clamp((0.158 - ee_to_star_dist) / 0.070, 0.0, 1.0)
    pregrasp_center_gate = torch.clamp((0.135 - finger_center_to_star_dist) / 0.060, 0.0, 1.0)
    pregrasp_close_gate = pregrasp_ee_gate * torch.maximum(
        pregrasp_center_gate * (0.20 + 0.80 * both_fingers_near_gate),
        0.65 * both_fingers_near_gate,
    )
    contact_close_gate = (
        torch.clamp((0.110 - ee_to_star_dist) / 0.055, 0.0, 1.0)
        * torch.clamp((0.112 - max_finger_to_star_dist) / 0.050, 0.0, 1.0)
        * finger_balance_gate
    )
    lift_credit_gate = (
        torch.clamp((0.142 - ee_to_star_dist) / 0.100, 0.0, 1.0)
        * (0.20 + 0.80 * tight_both_fingers_gate)
    )
    lift_progress = torch.clamp((star_lift_height - lift_reward_start_height) / lift_denom, 0.0, 1.0)
    lifted_gate = has_lifted_star.float()

    gripper_denom = 0.5 * max_gripper_width
    if gripper_denom < 1.0e-6:
        gripper_denom = 1.0e-6
    closed_gripper = torch.clamp((0.90 * max_gripper_width - gripper_width) / (1.30 * gripper_denom), 0.0, 1.0)
    close_near_ready = torch.maximum(close_near_gate * (0.10 + 0.90 * near_star), pregrasp_close_gate)
    grasp_pose_ready = ee_grasp_pose * (0.25 + 0.75 * finger_contact_gate)
    contact_ready = torch.maximum(grasp_pose_ready, contact_close_gate)
    grasp_ready = torch.maximum(contact_ready * (0.20 + 0.80 * finger_near_star), lift_ready_gate)
    prelift_gate = 1.0 - torch.clamp(lift_progress + has_lifted_star.float(), 0.0, 1.0)
    prelift_xy_motion = torch.clamp((star_initial_xy_error - 0.012) / 0.045, 0.0, 1.0)
    asymmetry_drag_gate = torch.clamp((finger_distance_asymmetry - 0.030) / 0.070, 0.0, 1.0)
    prelift_stability_gate = 1.0 - torch.clamp((star_initial_xy_error - 0.022) / 0.035, 0.0, 1.0)
    stable_or_lifted_gate = torch.maximum(prelift_stability_gate, lifted_gate)
    lift_action_progress_gate = 0.15 + 0.85 * torch.clamp(star_lift_height / 0.020, 0.0, 1.0)
    no_lift_progress_gate = 1.0 - torch.clamp(star_lift_height / 0.020, 0.0, 1.0)
    close_far_penalty_gate = torch.clamp((max_finger_to_star_dist - 0.128) / 0.064, 0.0, 1.0)
    descend_gate = (
        torch.clamp((0.205 - ee_to_star_dist) / 0.130, 0.0, 1.0)
        * torch.clamp((max_finger_to_star_dist - 0.112) / 0.082, 0.0, 1.0)
        * (1.0 - closed_gripper)
    )
    close_action_gate = 0.25 * pregrasp_close_gate + 0.75 * lift_ready_gate
    closed_near_ready = 0.10 * close_near_ready + 0.90 * lift_ready_gate

    xy_align = torch.exp(-transport_xy_sharpness * goal_xy_error)
    yaw_align = torch.exp(-yaw_sharpness * goal_yaw_error)
    height_align = torch.exp(-placement_height_sharpness * goal_height_error)

    approach_reward = approach_weight * stable_or_lifted_gate * near_star
    finger_approach_reward = finger_approach_weight * stable_or_lifted_gate * finger_approach
    grasp_pose_reward = grasp_pose_weight * prelift_stability_gate * (0.35 * contact_ready + 0.65 * lift_ready_gate)
    both_fingers_near_reward = both_fingers_near_weight * prelift_stability_gate * tight_ee_gate * both_fingers_near_gate
    lift_ready_reward = lift_ready_weight * stable_or_lifted_gate * lift_ready_gate * closed_gripper
    grasp_reward = grasp_weight * stable_or_lifted_gate * grasp_ready * (0.25 + 0.75 * closed_gripper)
    closed_grasp_reward = closed_grasp_weight * stable_or_lifted_gate * grasp_ready * closed_gripper
    lift_reward = (
        lift_weight
        * stable_or_lifted_gate
        * lift_progress
        * (0.35 + 0.65 * lift_credit_gate)
        * (0.25 + 0.75 * closed_gripper)
    )
    close_near_reward = close_near_weight * prelift_stability_gate * closed_near_ready * closed_gripper
    close_action_reward = (
        close_action_weight
        * prelift_gate
        * prelift_stability_gate
        * close_action_gate
        * torch.clamp(-actions[:, 6], 0.0, 1.0)
    )
    descend_action_reward = (
        descend_action_weight
        * prelift_gate
        * prelift_stability_gate
        * descend_gate
        * torch.clamp(-actions[:, 2], 0.0, 1.0)
    )
    lift_action_reward = (
        lift_action_weight
        * prelift_gate
        * prelift_stability_gate
        * lift_ready_gate
        * closed_gripper
        * lift_action_progress_gate
        * torch.clamp(actions[:, 2], 0.0, 1.0)
    )
    transport_reward = transport_weight * xy_align * lifted_gate
    yaw_reward = yaw_weight * yaw_align * xy_align * lifted_gate
    placement_reward = placement_weight * xy_align * yaw_align * height_align * has_lifted_star.float()
    success_bonus = success_bonus_weight * in_success_region.float()
    prelift_move_penalty = (
        prelift_move_penalty_weight
        * prelift_gate
        * prelift_xy_motion
        * (0.75 + 0.75 * asymmetry_drag_gate)
    )
    prelift_stall_penalty = (
        prelift_stall_penalty_weight
        * prelift_gate
        * prelift_stability_gate
        * lift_ready_gate
        * closed_gripper
        * no_lift_progress_gate
    )
    close_far_penalty = close_far_penalty_weight * closed_gripper * close_far_penalty_gate * (0.35 + 0.65 * near_star)
    one_finger_near_gate = torch.maximum(left_finger_gate, right_finger_gate)
    opening_or_lifting_near_gate = torch.maximum(pregrasp_close_gate, tight_ee_gate * one_finger_near_gate)
    open_near_penalty = (
        open_near_penalty_weight
        * prelift_gate
        * prelift_stability_gate
        * opening_or_lifting_near_gate
        * torch.clamp(actions[:, 6], 0.0, 1.0)
    )
    ungrasped_lift_penalty = (
        ungrasped_lift_penalty_weight
        * prelift_gate
        * prelift_stability_gate
        * opening_or_lifting_near_gate
        * (1.0 - closed_gripper)
        * torch.clamp(actions[:, 2], 0.0, 1.0)
    )
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        finger_approach_reward,
        grasp_pose_reward,
        both_fingers_near_reward,
        lift_ready_reward,
        grasp_reward,
        closed_grasp_reward,
        lift_reward,
        close_near_reward,
        close_action_reward,
        descend_action_reward,
        lift_action_reward,
        transport_reward,
        yaw_reward,
        placement_reward,
        success_bonus,
        prelift_move_penalty,
        prelift_stall_penalty,
        close_far_penalty,
        open_near_penalty,
        ungrasped_lift_penalty,
        action_penalty,
    )
