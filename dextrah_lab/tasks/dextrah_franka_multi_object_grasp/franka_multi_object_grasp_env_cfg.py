"""Configuration for the Franka multi-object GraspGen pick-up task."""

from __future__ import annotations

import isaaclab.sim as sim_utils
from isaaclab.sensors import TiledCameraCfg
from isaaclab.utils import configclass

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env_cfg import (
    DextrahFrankaCubeGraspEnvCfg,
)

FRANKA_MULTI_OBJECT_RGB_PROPRIO_DIM = 33
FRANKA_MULTI_OBJECT_RGB_IMAGE_HEIGHT = 240
FRANKA_MULTI_OBJECT_RGB_IMAGE_WIDTH = 320
FRANKA_MULTI_OBJECT_RGB_IMAGE_CHANNELS = 3
FRANKA_MULTI_OBJECT_RGB_OBSERVATION_SPACE = (
    FRANKA_MULTI_OBJECT_RGB_PROPRIO_DIM
    + FRANKA_MULTI_OBJECT_RGB_IMAGE_CHANNELS
    * FRANKA_MULTI_OBJECT_RGB_IMAGE_HEIGHT
    * FRANKA_MULTI_OBJECT_RGB_IMAGE_WIDTH
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
    object_stable_pose_enabled = False
    object_stable_pose_cache_dir = ""
    object_stable_pose_count = 1
    object_stable_pose_randomize = True
    object_stable_pose_allow_missing = False
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
    object_static_friction = 1.5
    object_dynamic_friction = 1.2
    object_restitution = 0.0
    object_contact_offset = 0.004
    object_rest_offset = 0.0
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
    # Optional JSON cache of dynamically verified grasp prior sample indices.
    # When set, reset sampling is restricted to indices that lifted in sim for
    # the matching object UUID.
    grasp_prior_verified_indices_path = ""
    grasp_prior_allow_missing = False
    # Multi-object priors include side/top approaches that need more pregrasp
    # clearance than the cube default. Table safety is enforced by the top-side
    # and projected finger-clearance reset gates below.
    grasp_prior_pregrasp_offset = 0.08
    grasp_prior_reset_attempts = 1
    grasp_prior_reset_candidate_count = 16
    grasp_prior_reset_require_topdown = True
    # Require both a top-side pregrasp displacement and a downward GraspGen
    # tool z-axis.  The pregrasp displacement alone can be above the object even
    # when the gripper approach axis points upward from below the table.
    grasp_prior_reset_min_pregrasp_z = 0.45
    grasp_prior_reset_require_downward_tool_z = True
    grasp_prior_reset_min_downward_tool_z = 0.45
    # Reject contact-based priors whose contact/reference midpoint is below
    # the current object center in world z.  This prevents underside grasps
    # even when the pregrasp offset is forced to approach from above.
    grasp_prior_reset_min_contact_height_above_center = 0.0
    grasp_prior_reset_max_center_distance_frac = 0.50
    grasp_prior_reset_min_width = 0.008
    grasp_prior_reset_ik_iterations = 64
    grasp_prior_reset_ik_damping = 0.035
    grasp_prior_reset_ik_max_joint_step = 0.25
    grasp_prior_reset_ik_pos_tolerance = 0.055
    grasp_prior_reset_ik_rot_tolerance = 0.55
    # Long, thin objects can have a large grasp-size extent.  Keep reset
    # quality tied to the actual projected gripper/contact alignment instead
    # of allowing object-length-scaled distances.
    grasp_prior_reset_quality_max_finger_center_dist = 0.08
    grasp_prior_reset_quality_max_tip_center_dist = 0.08
    grasp_prior_reset_quality_max_tip_max_dist = 0.10
    # Multi-object priors often target thin/elongated objects. Close fully and
    # lift long enough for reset-video verification instead of inheriting the
    # short single-cube warmstart.
    grasp_prior_action_warmstart_approach_steps = 20
    grasp_prior_action_warmstart_close_steps = 28
    grasp_prior_action_warmstart_lift_steps = 80
    grasp_prior_action_warmstart_close_width = 0.0
    grasp_prior_action_warmstart_use_prior_close_width = False
    grasp_prior_action_warmstart_lift_action_z = 1.0
    grasp_prior_action_warmstart_require_current_lift_ready = True

    # Optional online RGB observation path used by the RGB PPO task below.
    enable_rgb_observations = False
    rgb_robot_proprio_dim = FRANKA_MULTI_OBJECT_RGB_PROPRIO_DIM
    rgb_image_height = FRANKA_MULTI_OBJECT_RGB_IMAGE_HEIGHT
    rgb_image_width = FRANKA_MULTI_OBJECT_RGB_IMAGE_WIDTH
    rgb_image_channels = FRANKA_MULTI_OBJECT_RGB_IMAGE_CHANNELS
    rgb_image_flat_dim = (
        FRANKA_MULTI_OBJECT_RGB_IMAGE_CHANNELS
        * FRANKA_MULTI_OBJECT_RGB_IMAGE_HEIGHT
        * FRANKA_MULTI_OBJECT_RGB_IMAGE_WIDTH
    )

    # Workspace-facing Franka view derived from the validation rollout camera.
    # Isaac Lab's world camera convention uses +X forward and +Z up.
    rgb_camera_pos = (-0.10, -0.78, 1.42)
    rgb_camera_rot = (0.51027146, -0.27909221, 0.17949265, 0.79341853)
    rgb_camera_horizontal_aperture = 21.02
    rgb_camera_focal_length = 23.59
    tiled_camera: TiledCameraCfg = TiledCameraCfg(
        prim_path="/World/envs/env_.*/Camera",
        offset=TiledCameraCfg.OffsetCfg(pos=rgb_camera_pos, rot=rgb_camera_rot, convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=rgb_camera_focal_length,
            focus_distance=400.0,
            horizontal_aperture=rgb_camera_horizontal_aperture,
            clipping_range=(0.01, 2.0),
        ),
        width=rgb_image_width,
        height=rgb_image_height,
    )


@configclass
class DextrahFrankaMultiObjectRgbGraspEnvCfg(DextrahFrankaMultiObjectGraspEnvCfg):
    """RGB-observation Franka pick-up task over GraspGen objects."""

    enable_rgb_observations = True
    observation_space = FRANKA_MULTI_OBJECT_RGB_OBSERVATION_SPACE
    state_space = 0
    num_observations = observation_space
    num_states = state_space
