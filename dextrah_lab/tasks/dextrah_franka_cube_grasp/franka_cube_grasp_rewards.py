"""Reward helpers for the Franka single-cube grasp task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_franka_cube_grasp_rewards(
    ee_to_cube_dist: torch.Tensor,
    finger_center_to_cube_dist: torch.Tensor,
    left_finger_to_cube_dist: torch.Tensor,
    right_finger_to_cube_dist: torch.Tensor,
    gripper_width: torch.Tensor,
    cube_lift_height: torch.Tensor,
    cube_xy_error: torch.Tensor,
    cube_goal_height_error: torch.Tensor,
    has_lifted_cube: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    max_gripper_width: float,
    approach_weight: float,
    approach_sharpness: float,
    finger_approach_weight: float,
    finger_approach_sharpness: float,
    grasp_ready_weight: float,
    closed_grasp_weight: float,
    lift_weight: float,
    height_tracking_weight: float,
    height_tracking_sharpness: float,
    xy_stability_weight: float,
    xy_stability_sharpness: float,
    close_action_weight: float,
    lift_action_weight: float,
    success_bonus_weight: float,
    prelift_move_penalty_weight: float,
    close_far_penalty_weight: float,
    open_near_penalty_weight: float,
    ungrasped_lift_penalty_weight: float,
    action_penalty_weight: float,
):
    """Compute shaped rewards for Franka cube pickup.

    The no-lift terms are intentionally modest. Real object height is the
    dominant reward so this task can expose whether Franka can learn the same
    pickup objective as the KUKA/Allegro cube task.
    """

    lift_reward_start_height = 0.001
    lift_denom = target_lift_height - lift_reward_start_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    max_finger_to_cube_dist = torch.maximum(left_finger_to_cube_dist, right_finger_to_cube_dist)
    finger_distance_asymmetry = torch.abs(left_finger_to_cube_dist - right_finger_to_cube_dist)
    finger_balance_gate = 1.0 - torch.clamp((finger_distance_asymmetry - 0.020) / 0.070, 0.0, 1.0)
    near_cube = torch.exp(-approach_sharpness * ee_to_cube_dist)
    finger_approach = torch.exp(-finger_approach_sharpness * max_finger_to_cube_dist) * (
        0.30 + 0.70 * finger_balance_gate
    )
    tight_finger_gate = torch.clamp((0.125 - max_finger_to_cube_dist) / 0.075, 0.0, 1.0) * finger_balance_gate
    tight_center_gate = torch.clamp((0.115 - finger_center_to_cube_dist) / 0.065, 0.0, 1.0)
    tight_ee_gate = torch.clamp((0.150 - ee_to_cube_dist) / 0.090, 0.0, 1.0)
    grasp_ready_gate = tight_finger_gate * tight_center_gate * tight_ee_gate

    gripper_denom = 0.5 * max_gripper_width
    if gripper_denom < 1.0e-6:
        gripper_denom = 1.0e-6
    closed_gripper = torch.clamp((0.90 * max_gripper_width - gripper_width) / (1.30 * gripper_denom), 0.0, 1.0)

    lift_progress = torch.clamp((cube_lift_height - lift_reward_start_height) / lift_denom, 0.0, 1.0)
    prelift_gate = 1.0 - torch.clamp(lift_progress + has_lifted_cube.float(), 0.0, 1.0)
    lifted_gate = has_lifted_cube.float()
    xy_stability = torch.exp(-xy_stability_sharpness * cube_xy_error)
    height_tracking = torch.exp(-height_tracking_sharpness * cube_goal_height_error)
    lift_credit_gate = 0.35 + 0.65 * grasp_ready_gate
    closed_credit_gate = 0.25 + 0.75 * closed_gripper
    lift_action_progress_gate = 0.15 + 0.85 * torch.clamp(cube_lift_height / 0.020, 0.0, 1.0)

    close_near_gate = torch.clamp((0.180 - max_finger_to_cube_dist) / 0.120, 0.0, 1.0) * (
        0.25 + 0.75 * finger_balance_gate
    )
    close_far_gate = torch.clamp((max_finger_to_cube_dist - 0.140) / 0.080, 0.0, 1.0)
    open_near_gate = torch.maximum(close_near_gate, grasp_ready_gate)
    prelift_xy_motion = torch.clamp((cube_xy_error - 0.015) / 0.065, 0.0, 1.0)

    approach_reward = approach_weight * (0.70 + 0.30 * xy_stability) * near_cube
    finger_approach_reward = finger_approach_weight * (0.70 + 0.30 * xy_stability) * finger_approach
    grasp_ready_reward = grasp_ready_weight * prelift_gate * grasp_ready_gate
    closed_grasp_reward = closed_grasp_weight * prelift_gate * grasp_ready_gate * closed_gripper
    lift_reward = lift_weight * lift_progress * lift_credit_gate * closed_credit_gate * xy_stability
    height_tracking_reward = (
        height_tracking_weight
        * height_tracking
        * xy_stability
        * torch.clamp(lift_progress + lifted_gate, 0.0, 1.0)
    )
    xy_stability_reward = xy_stability_weight * xy_stability * torch.clamp(lift_progress + lifted_gate, 0.0, 1.0)
    close_action_reward = (
        close_action_weight
        * prelift_gate
        * close_near_gate
        * torch.clamp(-actions[:, 6], 0.0, 1.0)
    )
    lift_action_reward = (
        lift_action_weight
        * prelift_gate
        * grasp_ready_gate
        * closed_gripper
        * lift_action_progress_gate
        * torch.clamp(actions[:, 2], 0.0, 1.0)
    )
    success_bonus = success_bonus_weight * in_success_region.float()
    prelift_move_penalty = prelift_move_penalty_weight * prelift_gate * prelift_xy_motion
    close_far_penalty = close_far_penalty_weight * closed_gripper * close_far_gate
    open_near_penalty = open_near_penalty_weight * prelift_gate * open_near_gate * torch.clamp(actions[:, 6], 0.0, 1.0)
    ungrasped_lift_penalty = (
        ungrasped_lift_penalty_weight
        * prelift_gate
        * open_near_gate
        * (1.0 - closed_gripper)
        * torch.clamp(actions[:, 2], 0.0, 1.0)
    )
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        finger_approach_reward,
        grasp_ready_reward,
        closed_grasp_reward,
        lift_reward,
        height_tracking_reward,
        xy_stability_reward,
        close_action_reward,
        lift_action_reward,
        success_bonus,
        prelift_move_penalty,
        close_far_penalty,
        open_near_penalty,
        ungrasped_lift_penalty,
        action_penalty,
    )

