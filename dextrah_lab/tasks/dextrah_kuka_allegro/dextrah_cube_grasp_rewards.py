# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from __future__ import annotations

import torch


@torch.jit.script
def compute_cube_grasp_rewards(
    hand_mean_dist: torch.Tensor,
    hand_max_dist: torch.Tensor,
    cube_lift_height: torch.Tensor,
    cube_goal_height_error: torch.Tensor,
    cube_xy_error: torch.Tensor,
    in_success_region: torch.Tensor,
    robot_finger_dof_pos: torch.Tensor,
    curled_q: torch.Tensor,
    actions: torch.Tensor,
    target_lift_height: float,
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
    finger_curl_reg_weight: float,
    action_penalty_weight: float,
):
    """Compute shaped single-cube grasp-lift rewards."""

    lift_denom = target_lift_height
    if lift_denom < 1.0e-6:
        lift_denom = 1.0e-6

    near_gate = torch.exp(-approach_sharpness * hand_mean_dist)
    enclosure_gate = torch.exp(-enclosure_sharpness * hand_max_dist)
    lift_progress = torch.clamp(cube_lift_height / lift_denom, 0.0, 1.0)

    approach_reward = approach_weight * near_gate
    enclosure_reward = enclosure_weight * enclosure_gate
    lift_reward = lift_weight * lift_progress * (0.2 + 0.8 * near_gate)
    height_tracking_reward = (
        height_tracking_weight
        * torch.exp(-height_tracking_sharpness * cube_goal_height_error)
        * near_gate
    )
    xy_stability_reward = xy_stability_weight * torch.exp(-xy_stability_sharpness * cube_xy_error)
    success_bonus = success_bonus_weight * in_success_region.float()

    finger_curl_dist = (robot_finger_dof_pos - curled_q).norm(p=2, dim=-1)
    finger_curl_reg = finger_curl_reg_weight * finger_curl_dist * finger_curl_dist
    action_penalty = action_penalty_weight * torch.sum(actions * actions, dim=-1)

    return (
        approach_reward,
        enclosure_reward,
        lift_reward,
        height_tracking_reward,
        xy_stability_reward,
        success_bonus,
        finger_curl_reg,
        action_penalty,
    )
