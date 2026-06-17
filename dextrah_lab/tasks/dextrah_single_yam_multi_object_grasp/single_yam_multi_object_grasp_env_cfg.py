"""Configuration for the single-YAM GraspGen multi-object grasp task."""

from __future__ import annotations

from isaaclab.utils import configclass

from dextrah_lab.tasks.dextrah_multi_object_grasp.multi_object_grasp_cfg import (
    MULTI_OBJECT_FEATURE_DIM,
    MultiObjectGraspTaskCfg,
)
from dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.bimanual_yam_cube_grasp_env_cfg import (
    DextrahBimanualYAMCubeGraspEnvCfg,
)


BIMANUAL_YAM_BASE_OBSERVATION_SPACE = getattr(
    DextrahBimanualYAMCubeGraspEnvCfg,
    "observation_space",
    getattr(DextrahBimanualYAMCubeGraspEnvCfg, "num_observations", 97),
)
BIMANUAL_YAM_TABLE_CENTER_X = getattr(DextrahBimanualYAMCubeGraspEnvCfg, "table_center_x", -0.27)
BIMANUAL_YAM_TABLE_CENTER_Y = getattr(DextrahBimanualYAMCubeGraspEnvCfg, "table_center_y", 0.0)
BIMANUAL_YAM_PICKUP_X = getattr(DextrahBimanualYAMCubeGraspEnvCfg, "pickup_x", -0.30)
BIMANUAL_YAM_PICKUP_Y = getattr(DextrahBimanualYAMCubeGraspEnvCfg, "pickup_y", 0.0)


@configclass
class DextrahSingleYAMMultiObjectGraspEnvCfg(MultiObjectGraspTaskCfg, DextrahBimanualYAMCubeGraspEnvCfg):
    """State-based multi-object grasp task controlled by one bimanual YAM articulation."""

    observation_space = BIMANUAL_YAM_BASE_OBSERVATION_SPACE + MULTI_OBJECT_FEATURE_DIM
    state_space = observation_space
    num_observations = observation_space
    num_states = state_space

    # Center multi-object resets around the existing YAM pickup site.
    object_spawn_center_offset_x = BIMANUAL_YAM_PICKUP_X - BIMANUAL_YAM_TABLE_CENTER_X
    object_spawn_center_offset_y = BIMANUAL_YAM_PICKUP_Y - BIMANUAL_YAM_TABLE_CENTER_Y
    object_spawn_xy_randomization = 0.08
    object_spawn_yaw_randomization_deg = 180.0

    # Keep the default YAM object-reset behavior conservative until per-object
    # stable poses are available for all assets.
    object_stable_pose_enabled = False
    object_reset_settle_steps = 0

    # The object manifest supplies per-asset extents.  These defaults only
    # apply when scanning a raw USD directory without manifest metadata.
    object_default_half_extents = (0.04, 0.04, 0.04)
    object_default_grasp_size = 0.08

    # Larger objects and the YAM linear fingers need lower mass than the Franka
    # defaults to avoid harsh contact impulses during early environment smokes.
    object_density = 120.0
    object_static_friction = 1.6
    object_dynamic_friction = 1.1
    object_solver_position_iterations = 24
    object_solver_velocity_iterations = 6
    object_linear_damping = 0.12
    object_angular_damping = 0.65
    object_max_depenetration_velocity = 2.0


@configclass
class DextrahSingleYAMTabletopClutterGraspEnvCfg(DextrahSingleYAMMultiObjectGraspEnvCfg):
    """Single-YAM multi-object grasp task with extra randomly sampled tabletop clutter."""

    object_assets_dir = "dextrah_lab/assets/visdex_objects"
    max_objects = 96
    object_asset_assignment = "random"
    require_graspgen_scale = False

    tabletop_clutter_enabled = True
    tabletop_clutter_object_count = 6
    tabletop_clutter_assets_dir = "dextrah_lab/assets/visdex_objects"
    tabletop_clutter_max_objects = 96
    tabletop_clutter_asset_assignment = "random"
    tabletop_clutter_require_graspgen_scale = False
    tabletop_clutter_spawn_center_offset_x = 0.0
    tabletop_clutter_spawn_center_offset_y = 0.0
    tabletop_clutter_spawn_xy_randomization = 0.22
    tabletop_clutter_spawn_yaw_randomization_deg = 180.0
    tabletop_clutter_spawn_z_clearance = 0.006
    tabletop_clutter_spawn_z_jitter = 0.0
