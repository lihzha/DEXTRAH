"""Configuration for the Franka cube trajectory-tracking experiment variant."""

from __future__ import annotations

from isaaclab.utils import configclass

from .franka_cube_grasp_env_cfg import DextrahFrankaCubeGraspEnvCfg


@configclass
class DextrahFrankaCubeTrajTrackingEnvCfg(DextrahFrankaCubeGraspEnvCfg):
    """Reward-only task-space tracking variant for GraspGenX/cuRobo references."""

    trajectory_tracking_enabled = True
    trajectory_tracking_reference_path = ""

    # Keep the first variant reward-only.  Enabling reference observations is a
    # separate ablation because it changes the observation contract.
    trajectory_tracking_phase_observations = False

    # Reward terms.  The base cube reward is unchanged and these are additive.
    trajectory_tracking_position_weight = 1.5
    trajectory_tracking_position_sharpness = 18.0
    trajectory_tracking_orientation_weight = 0.15
    trajectory_tracking_orientation_sharpness = 6.0
    trajectory_tracking_gripper_weight = 0.20
    trajectory_tracking_gripper_sharpness = 45.0

    # Global training-step curriculum for fading the shaping term.  Set
    # end_weight equal to start_weight to keep it constant.
    trajectory_tracking_curriculum_steps = 200000
    trajectory_tracking_start_weight = 1.0
    trajectory_tracking_end_weight = 0.0

    # Safety/logging gates for transformed task-space targets.  By default the
    # curriculum tracks the reset-pose task-space reference instead of following
    # post-contact cube tumbles.
    trajectory_tracking_min_target_table_clearance = 0.025
    trajectory_tracking_follow_current_cube_pose = False
