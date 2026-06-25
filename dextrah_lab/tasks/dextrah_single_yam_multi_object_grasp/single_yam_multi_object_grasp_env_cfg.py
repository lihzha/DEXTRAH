"""Configuration for the true single-arm YAM multi-object grasp task."""

from __future__ import annotations

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, RigidObjectCfg
from isaaclab.envs import DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import PhysxCfg, SimulationCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.utils import configclass

from dextrah_lab.assets.yam.bimanual_yam import MOLMOACT2_SINGLE_HOME_JOINT_POS, SINGLE_YAM_CFG
from dextrah_lab.tasks.dextrah_multi_object_grasp.multi_object_grasp_cfg import (
    GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT,
    GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH,
    MULTI_OBJECT_FEATURE_DIM,
    MultiObjectGraspTaskCfg,
)


SINGLE_YAM_BASE_OBSERVATION_SPACE = 62


def _single_yam_robot_cfg(robot_base_pos: tuple[float, float, float]) -> ArticulationCfg:
    return SINGLE_YAM_CFG.copy().replace(prim_path="/World/envs/env_.*/Robot").replace(
        init_state=ArticulationCfg.InitialStateCfg(
            pos=robot_base_pos,
            rot=(1.0, 0.0, 0.0, 0.0),
            joint_pos=MOLMOACT2_SINGLE_HOME_JOINT_POS,
            joint_vel={".*": 0.0},
        ),
    )


@configclass
class DextrahSingleYAMMultiObjectGraspEnvCfg(MultiObjectGraspTaskCfg, DirectRLEnvCfg):
    """State-based multi-object grasp task controlled by one single-arm YAM articulation."""

    # env
    episode_length_s = 8.0
    decimation = 2
    sim_dt = 1.0 / 120.0
    action_space = 7
    observation_space = SINGLE_YAM_BASE_OBSERVATION_SPACE + MULTI_OBJECT_FEATURE_DIM
    state_space = observation_space
    num_actions = action_space
    num_observations = observation_space
    num_states = state_space
    use_cuda_graph = False

    # simulation
    sim: SimulationCfg = SimulationCfg(
        dt=sim_dt,
        render_interval=decimation,
        physics_material=RigidBodyMaterialCfg(
            static_friction=1.2,
            dynamic_friction=1.0,
            restitution=0.0,
            friction_combine_mode="max",
            restitution_combine_mode="min",
        ),
        physx=PhysxCfg(
            bounce_threshold_velocity=0.2,
            gpu_max_rigid_patch_count=4 * 5 * 2**15,
        ),
    )
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1024, env_spacing=1.8, replicate_physics=False)

    # Render-scene appearance used by the training environment viewer.
    ground_plane_size = (6.0, 6.0)
    ground_plane_color = (0.03, 0.03, 0.03)
    ground_plane_z = -0.08
    dome_light_intensity = 1800.0
    dome_light_exposure = 0.0
    dome_light_color = (0.75, 0.75, 0.75)
    key_light_enabled = False
    key_light_intensity = 0.0
    key_light_exposure = 0.0
    key_light_color = (0.95, 0.95, 0.92)
    key_light_angle = 0.8
    key_light_rotation_deg = (50.0, 0.0, -35.0)

    # YAM-relative layout. The single arm is mounted on the near table edge and
    # shifted onto the table-right half, matching the real camera/robot setup.
    robot_base_x = -0.65
    robot_base_y = -0.25
    robot_base_z = 0.01
    robot_base_pos = (robot_base_x, robot_base_y, robot_base_z)
    table_surface_z = 0.0
    table_thickness = 0.052
    table_center_x = -0.12
    table_center_y = 0.0
    table_center_z = table_surface_z - 0.5 * table_thickness
    table_size_x = 1.04
    table_size_y = 1.20

    pickup_x = -0.30
    pickup_y = -0.18

    # Success and reset behavior for the target object.
    cube_lift_height = 0.08
    cube_success_lift_height = 0.04
    cube_success_xy_tol = 0.04
    cube_success_hand_dist = 0.12
    cube_success_max_linear_speed = 0.60
    cube_success_max_angular_speed = 8.0
    cube_speed_termination_linear = 1.00
    cube_speed_termination_angular = 10.0
    success_timeout = 0.10
    min_episode_steps_before_success = 30
    prelift_drag_termination_xy_error = 0.04
    cube_out_max_z = table_surface_z + 0.35
    finger_table_clearance_margin = 0.010
    finger_table_penetration_termination_margin = -0.008
    finger_table_clearance_success_margin = -0.004
    out_of_bounds_margin = 0.18

    # YAM geometry/control
    max_gripper_width = 0.17
    gripper_open_joint_pos = -0.0475
    gripper_closed_joint_pos = 0.0
    arm_joint_reset_noise = 0.0
    ik_position_action_scale = (0.055, 0.055, 0.045)
    ik_rotation_action_scale = (0.22, 0.22, 0.25)
    tcp_offset_pos = (0.0, 0.0, 0.0605)

    robot: ArticulationCfg = _single_yam_robot_cfg(robot_base_pos)

    table: RigidObjectCfg = RigidObjectCfg(
        prim_path="/World/envs/env_.*/Table",
        spawn=sim_utils.CuboidCfg(
            size=(table_size_x, table_size_y, table_thickness),
            collision_props=sim_utils.CollisionPropertiesCfg(collision_enabled=True, contact_offset=0.004),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=True,
                disable_gravity=True,
            ),
            physics_material=RigidBodyMaterialCfg(
                static_friction=1.4,
                dynamic_friction=1.1,
                restitution=0.0,
                friction_combine_mode="max",
                restitution_combine_mode="min",
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.50, 0.47, 0.41), roughness=0.72),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(table_center_x, table_center_y, table_center_z),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )

    # Center multi-object resets around the YAM pickup site.
    object_spawn_center_offset_x = pickup_x - table_center_x
    object_spawn_center_offset_y = pickup_y - table_center_y
    object_spawn_xy_randomization = 0.08
    # Optional per-axis jitter overrides.  When left as None, the legacy square
    # object_spawn_xy_randomization is used for both axes.
    object_spawn_x_randomization = None
    object_spawn_y_randomization = None
    object_spawn_yaw_randomization_deg = 180.0
    object_stable_pose_enabled = False
    object_reset_settle_steps = 0
    object_default_half_extents = (0.04, 0.04, 0.04)
    object_default_grasp_size = 0.08
    object_density = 120.0
    object_static_friction = 1.6
    object_dynamic_friction = 1.1
    object_solver_position_iterations = 24
    object_solver_velocity_iterations = 6
    object_linear_damping = 0.12
    object_angular_damping = 0.65
    object_max_depenetration_velocity = 2.0

    # reward weights
    cube_approach_weight = 2.0
    cube_approach_sharpness = 10.0
    cube_lift_weight = 12.0
    cube_height_tracking_weight = 3.0
    cube_height_tracking_sharpness = 18.0
    cube_xy_stability_weight = 1.0
    cube_xy_stability_sharpness = 12.0
    cube_success_bonus_weight = 18.0
    cube_close_action_weight = 0.3
    cube_lift_action_weight = 1.0
    cube_descend_action_penalty_weight = -1.0
    cube_table_clearance_penalty_weight = -2.0
    cube_gripper_close_reg_weight = -0.001
    cube_action_penalty_weight = -0.0005
    cube_velocity_penalty_weight = -2.0


@configclass
class DextrahSingleYAMTabletopClutterGraspEnvCfg(DextrahSingleYAMMultiObjectGraspEnvCfg):
    """Single-arm YAM multi-object grasp task with extra randomly sampled tabletop clutter."""

    # Generated by dextrah_lab/assets/prepare_graspgen_assets.py from the
    # Objaverse-backed GraspGen dataset. The loader requires object_scale from
    # each record's grasp prior instead of silently using manifest/default scale.
    object_asset_manifest_path = GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH
    object_assets_dir = GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT
    max_objects = 0
    object_asset_assignment = "random"
    require_graspgen_scale = True
    object_validate_usd_bounds = True

    tabletop_clutter_enabled = True
    tabletop_clutter_object_count = 6
    tabletop_clutter_asset_manifest_path = GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH
    tabletop_clutter_assets_dir = GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT
    tabletop_clutter_max_objects = 0
    tabletop_clutter_asset_assignment = "random"
    tabletop_clutter_require_graspgen_scale = True
    tabletop_clutter_validate_usd_bounds = True
    tabletop_clutter_spawn_center_offset_x = -0.18
    tabletop_clutter_spawn_center_offset_y = -0.14
    tabletop_clutter_spawn_xy_randomization = 0.38
    tabletop_clutter_spawn_yaw_randomization_deg = 180.0
    tabletop_clutter_spawn_z_clearance = 0.006
    tabletop_clutter_spawn_z_jitter = 0.0
    tabletop_clutter_placement_attempts = 512
    tabletop_clutter_placement_grid_resolution = 35

    tabletop_goal_bin_enabled = True
    tabletop_goal_bin_center_offset_x = -0.15
    tabletop_goal_bin_center_offset_y = 0.42
    tabletop_goal_bin_inner_size_x = 0.36
    tabletop_goal_bin_inner_size_y = 0.22
    tabletop_goal_bin_wall_thickness = 0.02
    tabletop_goal_bin_bottom_thickness = 0.012
    tabletop_goal_bin_wall_height = 0.12
    tabletop_goal_bin_clearance = 0.10
    tabletop_goal_bin_placement_clearance = 0.16
    tabletop_goal_bin_goal_height = 0.06
    tabletop_goal_bin_success_xy_tol = 0.08
    cube_success_xy_tol = tabletop_goal_bin_success_xy_tol


@configclass
class DextrahSingleYAMSingleObjectPolicyGraspEnvCfg(DextrahSingleYAMMultiObjectGraspEnvCfg):
    """Single-object YAM tabletop policy scene with one target object and one goal bin."""

    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1, env_spacing=1.8, replicate_physics=False)
    episode_length_s = 12.0

    # Production policy data uses the Objaverse-backed GraspGen pool. Local
    # smoke renders can override these to repo-local primitive manifests.
    object_asset_manifest_path = GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH
    object_assets_dir = GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT
    max_objects = 0
    object_asset_assignment = "random"
    require_graspgen_scale = True
    object_validate_usd_bounds = True
    object_spawn_xy_randomization = 0.0
    object_spawn_x_randomization = 0.045
    object_spawn_y_randomization = 0.045
    object_spawn_yaw_randomization_deg = 180.0
    object_spawn_z_clearance = 0.006
    object_reset_settle_steps = 100
    object_reset_zero_velocity_after_settle = True

    tabletop_clutter_enabled = False
    tabletop_clutter_object_count = 0
    tabletop_source_bin_enabled = False

    tabletop_goal_bin_enabled = True
    tabletop_goal_bin_center_offset_x = -0.10
    tabletop_goal_bin_center_offset_y = 0.20
    tabletop_goal_bin_inner_size_x = 0.28
    tabletop_goal_bin_inner_size_y = 0.22
    tabletop_goal_bin_wall_thickness = 0.02
    tabletop_goal_bin_bottom_thickness = 0.012
    tabletop_goal_bin_wall_height = 0.12
    tabletop_goal_bin_clearance = 0.08
    tabletop_goal_bin_placement_clearance = 0.08
    tabletop_goal_bin_goal_height = 0.06
    tabletop_goal_bin_success_xy_tol = 0.12
    cube_success_xy_tol = tabletop_goal_bin_success_xy_tol


@configclass
class DextrahSingleYAMTwoBinPrimitiveGraspEnvCfg(DextrahSingleYAMMultiObjectGraspEnvCfg):
    """Single-arm YAM source-to-destination bin demo with fixed primitive objects."""

    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1, env_spacing=1.8, replicate_physics=False)
    episode_length_s = 12.0

    object_asset_manifest_path = "dextrah_lab/assets/primitives/yam_two_bin_primitives_manifest.json"
    object_assets_dir = "dextrah_lab/assets/primitives"
    max_objects = 1
    object_asset_assignment = "round_robin"
    require_graspgen_scale = False
    object_validate_usd_bounds = False
    object_spawn_xy_randomization = 0.0
    object_spawn_yaw_randomization_deg = 0.0
    object_spawn_z_clearance = 0.0
    object_fixed_root_position = (-0.420, -0.225, 0.052)
    object_fixed_root_quat_wxyz = (0.991445, 0.0, 0.0, 0.130526)
    object_reset_settle_steps = 72
    object_reset_zero_velocity_after_settle = True
    object_density = 180.0
    object_static_friction = 1.8
    object_dynamic_friction = 1.2
    object_linear_damping = 0.16
    object_angular_damping = 0.75
    object_max_depenetration_velocity = 1.5

    tabletop_source_bin_enabled = True
    tabletop_source_bin_center_offset_x = -0.18
    tabletop_source_bin_center_offset_y = -0.22
    tabletop_source_bin_inner_size_x = 0.36
    tabletop_source_bin_inner_size_y = 0.28
    tabletop_source_bin_wall_thickness = 0.02
    tabletop_source_bin_bottom_thickness = 0.012
    tabletop_source_bin_wall_height = 0.12
    tabletop_source_bin_floor_color = (0.19, 0.17, 0.13)
    tabletop_source_bin_x_wall_color = (0.58, 0.42, 0.19)
    tabletop_source_bin_y_wall_color = (0.47, 0.34, 0.15)
    tabletop_source_bin_visual_roughness = 0.74

    tabletop_goal_bin_enabled = True
    tabletop_goal_bin_center_offset_x = -0.18
    tabletop_goal_bin_center_offset_y = 0.22
    tabletop_goal_bin_inner_size_x = 0.36
    tabletop_goal_bin_inner_size_y = 0.28
    tabletop_goal_bin_wall_thickness = 0.02
    tabletop_goal_bin_bottom_thickness = 0.012
    tabletop_goal_bin_wall_height = 0.12
    tabletop_goal_bin_clearance = 0.06
    tabletop_goal_bin_placement_clearance = 0.04
    tabletop_goal_bin_goal_height = 0.06
    tabletop_goal_bin_success_xy_tol = 0.10
    tabletop_goal_bin_floor_color = (0.13, 0.16, 0.18)
    tabletop_goal_bin_x_wall_color = (0.14, 0.43, 0.61)
    tabletop_goal_bin_y_wall_color = (0.11, 0.34, 0.52)
    tabletop_goal_bin_visual_roughness = 0.70
    cube_success_xy_tol = tabletop_goal_bin_success_xy_tol

    tabletop_clutter_enabled = True
    tabletop_clutter_object_count = 5
    tabletop_clutter_asset_manifest_path = object_asset_manifest_path
    tabletop_clutter_assets_dir = object_assets_dir
    tabletop_clutter_max_objects = 5
    tabletop_clutter_asset_assignment = "round_robin"
    tabletop_clutter_require_graspgen_scale = False
    tabletop_clutter_validate_usd_bounds = False
    tabletop_clutter_spawn_xy_randomization = 0.0
    tabletop_clutter_spawn_yaw_randomization_deg = 0.0
    tabletop_clutter_spawn_z_clearance = 0.0
    tabletop_clutter_spawn_z_jitter = 0.0
    tabletop_clutter_non_overlapping = False
    tabletop_clutter_kinematic_enabled = True
    tabletop_clutter_disable_gravity = True
    tabletop_clutter_density = 160.0
    tabletop_clutter_static_friction = 1.8
    tabletop_clutter_dynamic_friction = 1.2
    tabletop_clutter_fixed_layout_enabled = True
    tabletop_clutter_fixed_layout = (
        {"root_position": (-0.300, -0.300, 0.052), "yaw_deg": -8.0},
        {"root_position": (-0.410, -0.295, 0.074), "yaw_deg": 22.0},
        {"root_position": (-0.225, -0.210, 0.052), "yaw_deg": 0.0},
        {"root_position": (-0.405, -0.145, 0.067), "yaw_deg": -30.0},
        {"root_position": (-0.300, -0.215, 0.125), "yaw_deg": 0.0},
    )
