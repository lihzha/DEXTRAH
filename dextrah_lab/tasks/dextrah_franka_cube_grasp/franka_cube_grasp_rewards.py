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
    finger_table_clearance: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    max_gripper_width: float,
    table_clearance_margin: float,
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
    close_action_weight: float,
    lift_action_weight: float,
    descend_action_penalty_weight: float,
    postlift_action_gate_height: float,
    postlift_close_action_weight: float,
    postlift_open_action_penalty_weight: float,
    postlift_lift_action_weight: float,
    postlift_descend_action_penalty_weight: float,
    table_clearance_penalty_weight: float,
    gripper_close_reg_weight: float,
    action_penalty_weight: float,
):
    """Compute KUKA-cube-shaped rewards plus gated Franka gripper action shaping."""

    lift_denom = target_lift_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    mean_finger_to_cube_dist = 0.5 * (left_finger_to_cube_dist + right_finger_to_cube_dist)
    max_finger_to_cube_dist = torch.maximum(left_finger_to_cube_dist, right_finger_to_cube_dist)
    finger_distance_asymmetry = torch.abs(left_finger_to_cube_dist - right_finger_to_cube_dist)
    finger_balance_gate = 1.0 - torch.clamp((finger_distance_asymmetry - 0.025) / 0.075, 0.0, 1.0)
    near_gate = torch.exp(-approach_sharpness * mean_finger_to_cube_dist)
    enclosure_gate = torch.exp(-enclosure_sharpness * max_finger_to_cube_dist)
    lift_progress = torch.clamp(cube_lift_height / lift_denom, 0.0, 1.0)
    height_tracking = torch.exp(-height_tracking_sharpness * cube_goal_height_error)
    xy_stability = torch.exp(-xy_stability_sharpness * cube_xy_error)
    gripper_width_denom = max_gripper_width
    if gripper_width_denom < 1.0e-6:
        gripper_width_denom = 1.0e-6
    gripper_open_fraction = torch.clamp(gripper_width / gripper_width_denom, 0.0, 1.0)
    closed_gripper = torch.clamp((0.90 * max_gripper_width - gripper_width) / (0.65 * max_gripper_width), 0.0, 1.0)
    prelift_gate = 1.0 - lift_progress
    near_enclosure_gate = (
        torch.clamp((0.180 - max_finger_to_cube_dist) / 0.100, 0.0, 1.0)
        * (0.25 + 0.75 * finger_balance_gate)
    )
    lift_ready_gate = near_enclosure_gate * closed_gripper * xy_stability
    table_clearance_denom = table_clearance_margin
    if table_clearance_denom < 1.0e-6:
        table_clearance_denom = 1.0e-6
    table_clearance_violation = torch.clamp(
        (table_clearance_margin - finger_table_clearance) / table_clearance_denom,
        0.0,
        1.0,
    )

    approach_reward = approach_weight * near_gate
    enclosure_reward = enclosure_weight * enclosure_gate
    lift_reward = lift_weight * lift_progress * (0.2 + 0.8 * near_gate)
    height_tracking_reward = height_tracking_weight * height_tracking * near_gate
    xy_stability_reward = xy_stability_weight * xy_stability
    success_bonus = success_bonus_weight * in_success_region.float()
    close_action_reward = close_action_weight * prelift_gate * near_enclosure_gate * torch.clamp(-actions[:, 6], 0.0, 1.0)
    lift_action_reward = lift_action_weight * prelift_gate * lift_ready_gate * torch.clamp(actions[:, 2], 0.0, 1.0)
    descend_action_penalty = (
        descend_action_penalty_weight * prelift_gate * lift_ready_gate * torch.clamp(-actions[:, 2], 0.0, 1.0)
    )
    postlift_gate_denom = postlift_action_gate_height
    if postlift_gate_denom < 1.0e-6:
        postlift_gate_denom = lift_denom
    postlift_gate = torch.clamp(cube_lift_height / postlift_gate_denom, 0.0, 1.0)
    postlift_close_action_reward = postlift_close_action_weight * postlift_gate * torch.clamp(-actions[:, 6], 0.0, 1.0)
    postlift_open_action_penalty = postlift_open_action_penalty_weight * postlift_gate * torch.clamp(actions[:, 6], 0.0, 1.0)
    postlift_lift_action_reward = postlift_lift_action_weight * postlift_gate * torch.clamp(actions[:, 2], 0.0, 1.0)
    postlift_descend_action_penalty = (
        postlift_descend_action_penalty_weight * postlift_gate * torch.clamp(-actions[:, 2], 0.0, 1.0)
    )
    table_clearance_penalty = table_clearance_penalty_weight * table_clearance_violation * table_clearance_violation
    gripper_close_reg = gripper_close_reg_weight * gripper_open_fraction * gripper_open_fraction
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        enclosure_reward,
        lift_reward,
        height_tracking_reward,
        xy_stability_reward,
        success_bonus,
        close_action_reward,
        lift_action_reward,
        descend_action_penalty,
        postlift_close_action_reward,
        postlift_open_action_penalty,
        postlift_lift_action_reward,
        postlift_descend_action_penalty,
        table_clearance_penalty,
        gripper_close_reg,
        action_penalty,
    )
