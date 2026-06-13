"""Configuration for the Franka multi-object GraspGen pick-up task."""

from __future__ import annotations

from isaaclab.utils import configclass

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env_cfg import (
    DextrahFrankaCubeGraspEnvCfg,
)


@configclass
class DextrahFrankaMultiObjectGraspEnvCfg(DextrahFrankaCubeGraspEnvCfg):
    """State-based Franka pick-up task over a manifest of GraspGen objects."""

    observation_space = 80
    state_space = 80
    num_observations = observation_space
    num_states = state_space

    # Asset manifest produced by dextrah_lab/assets/prepare_graspgen_assets.py.
    # If empty, object_assets_dir is scanned for a manifest.json or USD/*/*.usd.
    object_asset_manifest_path = ""
    object_assets_dir = "dextrah_lab/assets/graspgen_objects"
    max_objects = 0
    # Object USD assets are instantiated during scene setup, so the asset
    # assignment is sampled once per vectorized env at construction time.
    # Reset-time pose randomization below still runs independently per env.
    object_asset_assignment = "round_robin"
    require_graspgen_scale = True

    # Object placement and physical properties.  The robot base remains at the
    # cube task's higher z, which avoids placing the Franka fingers under the
    # tabletop at reset.
    # Spawn objects around a table-center-relative workspace point instead of
    # the gripper pickup point.  The default center is +5 cm in table X with a
    # 10 cm half-width, giving edge offsets of (15, 0), (-5, 0), (5, 10),
    # and (5, -10) cm in the table frame.
    object_spawn_center_offset_x = 0.05
    object_spawn_center_offset_y = 0.0
    object_spawn_xy_randomization = 0.10
    object_spawn_yaw_randomization_deg = 180.0
    object_spawn_z_clearance = 0.006
    # Optional reset-time settling for rendered/debug validation.  This is
    # disabled by default because stepping the whole simulator inside a partial
    # vector-env reset would advance unrelated envs.  Use precomputed stable
    # poses before enabling this in large-scale RL training.
    object_reset_settle_steps = 0
    object_reset_zero_velocity_after_settle = True
    object_reset_settle_full_reset_only = True
    object_default_half_extents = (0.03, 0.03, 0.03)
    object_default_grasp_size = 0.06
    object_default_scale = 1.0
    object_density = 500.0
    object_solver_position_iterations = 12
    object_solver_velocity_iterations = 4
    object_linear_damping = 0.08
    object_angular_damping = 0.25
    object_sleep_threshold = 0.02
    object_stabilization_threshold = 0.01
    object_max_depenetration_velocity = 3.0

    # For multi-object training, per-object prior paths come from the manifest
    # or from grasp_prior_library_dir/<uuid>.npz.
    grasp_prior_library_dir = ""
    grasp_prior_allow_missing = False
