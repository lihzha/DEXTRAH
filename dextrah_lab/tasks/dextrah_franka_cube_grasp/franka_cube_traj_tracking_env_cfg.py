"""Configuration for the Franka cube trajectory-tracking experiment variant."""

from __future__ import annotations

from isaaclab.utils import configclass

from .franka_cube_grasp_env_cfg import DextrahFrankaCubeGraspEnvCfg


@configclass
class DextrahFrankaCubeTrajTrackingEnvCfg(DextrahFrankaCubeGraspEnvCfg):
    """Reward-only task-space tracking variant for GraspGenX/cuRobo references."""

    trajectory_tracking_enabled = True
    trajectory_tracking_reference_path = ""
    # Normalize compact reference timestamps to this runtime horizon.  The
    # original GraspGenX/cuRobo export can be much longer than the 10 s DEXTRAH
    # episode; source timing is still reported in the runtime summary.
    trajectory_tracking_reference_duration_s = 8.0

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
    # Phase-gated proximity/contact shaping for the tracking variant.  These
    # action bonuses are intentionally separate from the baseline cube reward.
    # The gate is broad enough to provide a learning signal before hard contact.
    # Diagnostic scale: the previous relaxed-gate smoke produced nonzero but
    # negligible close/lift terms (~1e-3).  Keep this variant separate from the
    # baseline while testing whether action incentives can overcome reference
    # attraction during close/lift phases.
    trajectory_tracking_close_action_weight = 2.5
    trajectory_tracking_close_action_phase_start = 0.45
    trajectory_tracking_lift_action_weight = 4.0
    trajectory_tracking_lift_action_phase_start = 0.55
    trajectory_tracking_contact_gate_max_finger_dist = 0.30
    trajectory_tracking_contact_gate_width = 0.18
    # Reduce task-space position/orientation/gripper tracking after grasp phase
    # so the diagnostic can test whether late reference attraction pulls the
    # hand away from the cube.  Action bonuses continue to use the unscaled
    # safe phase weight.
    trajectory_tracking_reference_reweight_phase_start = 0.55
    trajectory_tracking_reference_late_weight_scale = 0.35
    # GraspGenX exports use zero as a close command.  In this DEXTRAH task the
    # tracked value is measured fingertip-body separation, so clamp close-phase
    # targets to the contact-width scale used by the cube reward checks.
    trajectory_tracking_min_target_gripper_width = 0.024

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
