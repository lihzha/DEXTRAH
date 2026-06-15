"""Reward helpers for the bimanual YAM cube-grasp task."""

from __future__ import annotations

import torch


@torch.jit.script
def compute_bimanual_yam_cube_grasp_rewards(
    left_hold_to_cube_dist: torch.Tensor,
    right_hold_to_cube_dist: torch.Tensor,
    left_gripper_width: torch.Tensor,
    right_gripper_width: torch.Tensor,
    cube_lift_height: torch.Tensor,
    cube_goal_height_error: torch.Tensor,
    cube_xy_error: torch.Tensor,
    finger_table_clearance: torch.Tensor,
    left_side_alignment: torch.Tensor,
    right_side_alignment: torch.Tensor,
    in_success_region: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
    max_gripper_width: float,
    table_clearance_margin: float,
    approach_weight: float,
    approach_sharpness: float,
    enclosure_weight: float,
    enclosure_sharpness: float,
    side_alignment_weight: float,
    lift_weight: float,
    height_tracking_weight: float,
    height_tracking_sharpness: float,
    xy_stability_weight: float,
    xy_stability_sharpness: float,
    success_bonus_weight: float,
    close_action_weight: float,
    lift_action_weight: float,
    descend_action_penalty_weight: float,
    table_clearance_penalty_weight: float,
    gripper_close_reg_weight: float,
    action_penalty_weight: float,
):
    """Compute a Franka-cube-style reward with bimanual side-contact shaping."""

    lift_denom = target_lift_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    mean_hold_to_cube_dist = 0.5 * (left_hold_to_cube_dist + right_hold_to_cube_dist)
    max_hold_to_cube_dist = torch.maximum(left_hold_to_cube_dist, right_hold_to_cube_dist)
    hold_distance_asymmetry = torch.abs(left_hold_to_cube_dist - right_hold_to_cube_dist)
    balance_gate = 1.0 - torch.clamp((hold_distance_asymmetry - 0.025) / 0.075, 0.0, 1.0)
    near_gate = torch.exp(-approach_sharpness * mean_hold_to_cube_dist)
    enclosure_gate = torch.exp(-enclosure_sharpness * max_hold_to_cube_dist)
    side_gate = torch.clamp(left_side_alignment, 0.0, 1.0) * torch.clamp(right_side_alignment, 0.0, 1.0)

    lift_progress = torch.clamp(cube_lift_height / lift_denom, 0.0, 1.0)
    height_tracking = torch.exp(-height_tracking_sharpness * cube_goal_height_error)
    xy_stability = torch.exp(-xy_stability_sharpness * cube_xy_error)

    width_denom = max_gripper_width
    if width_denom < 1.0e-6:
        width_denom = 1.0e-6
    left_open_fraction = torch.clamp(left_gripper_width / width_denom, 0.0, 1.0)
    right_open_fraction = torch.clamp(right_gripper_width / width_denom, 0.0, 1.0)
    closed_grippers = 0.5 * (
        torch.clamp((0.90 * max_gripper_width - left_gripper_width) / (0.65 * max_gripper_width), 0.0, 1.0)
        + torch.clamp((0.90 * max_gripper_width - right_gripper_width) / (0.65 * max_gripper_width), 0.0, 1.0)
    )

    table_clearance_denom = table_clearance_margin
    if table_clearance_denom < 1.0e-6:
        table_clearance_denom = 1.0e-6
    table_clearance_violation = torch.clamp(
        (table_clearance_margin - finger_table_clearance) / table_clearance_denom,
        0.0,
        1.0,
    )

    prelift_gate = 1.0 - lift_progress
    left_close_action = torch.clamp(-actions[:, 6], 0.0, 1.0)
    right_close_action = torch.clamp(-actions[:, 13], 0.0, 1.0)
    close_action = 0.5 * (left_close_action + right_close_action)
    lift_action = 0.5 * (torch.clamp(actions[:, 2], 0.0, 1.0) + torch.clamp(actions[:, 9], 0.0, 1.0))
    descend_action = 0.5 * (torch.clamp(-actions[:, 2], 0.0, 1.0) + torch.clamp(-actions[:, 9], 0.0, 1.0))
    bimanual_ready_gate = (
        torch.clamp((0.180 - max_hold_to_cube_dist) / 0.100, 0.0, 1.0)
        * (0.25 + 0.75 * balance_gate)
        * (0.20 + 0.80 * side_gate)
        * closed_grippers
        * xy_stability
    )

    approach_reward = approach_weight * near_gate
    enclosure_reward = enclosure_weight * enclosure_gate * (0.25 + 0.75 * side_gate)
    side_alignment_reward = side_alignment_weight * side_gate * near_gate
    lift_reward = lift_weight * lift_progress * (0.2 + 0.8 * near_gate) * (0.35 + 0.65 * side_gate)
    height_tracking_reward = height_tracking_weight * height_tracking * near_gate
    xy_stability_reward = xy_stability_weight * xy_stability
    success_bonus = success_bonus_weight * in_success_region.float()
    close_action_reward = close_action_weight * prelift_gate * bimanual_ready_gate * close_action
    lift_action_reward = lift_action_weight * prelift_gate * bimanual_ready_gate * lift_action
    descend_action_penalty = descend_action_penalty_weight * prelift_gate * bimanual_ready_gate * descend_action
    table_clearance_penalty = table_clearance_penalty_weight * table_clearance_violation * table_clearance_violation
    gripper_close_reg = gripper_close_reg_weight * 0.5 * (
        left_open_fraction * left_open_fraction + right_open_fraction * right_open_fraction
    )
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        enclosure_reward,
        side_alignment_reward,
        lift_reward,
        height_tracking_reward,
        xy_stability_reward,
        success_bonus,
        close_action_reward,
        lift_action_reward,
        descend_action_penalty,
        table_clearance_penalty,
        gripper_close_reg,
        action_penalty,
    )
