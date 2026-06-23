"""Configuration for the bimanual YAM single-cube grasp task."""

from __future__ import annotations

import math

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, RigidObjectCfg
from isaaclab.envs import DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import PhysxCfg, SimulationCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.utils import configclass

from dextrah_lab.assets.yam.bimanual_yam import (
    BIMANUAL_YAM_CFG,
    BIMANUAL_YAM_MJCF_PATH,
    BIMANUAL_YAM_USD_PATH,
    MOLMOACT2_BIMANUAL_ARM_Y_OFFSET,
    MOLMOACT2_BOX_ANCHOR_XY,
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_CAMERA_ORDER,
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_HOME_JOINT_POS,
    MOLMOACT2_LEFT_CAMERA_UID,
    MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_OBJECT_ANCHORS_XY,
    MOLMOACT2_NORM_TAG,
    MOLMOACT2_RIGHT_CAMERA_UID,
    MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY,
    MOLMOACT2_ROBOT_ROOT_POS,
    MOLMOACT2_REST_JOINT_POS,
    MOLMOACT2_TABLE_CENTER,
    MOLMOACT2_TABLE_SIZE,
    MOLMOACT2_TABLE_SURFACE_Z,
    MOLMOACT2_TOP_CAMERA_HFOV_DEG,
    MOLMOACT2_TOP_CAMERA_INTRINSIC,
    MOLMOACT2_TOP_CAMERA_LOCAL_POS,
    MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ,
    MOLMOACT2_TOP_CAMERA_PARENT_BODY,
    MOLMOACT2_TOP_CAMERA_UID,
    MOLMOACT2_TOP_CAMERA_VFOV_DEG,
    MOLMOACT2_WRIST_CAMERA_HFOV_DEG,
    MOLMOACT2_WRIST_CAMERA_INTRINSIC,
    MOLMOACT2_WRIST_CAMERA_LOCAL_POS,
    MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ,
    MOLMOACT2_WRIST_CAMERA_VFOV_DEG,
)

YAM_MJCF_PATH = BIMANUAL_YAM_MJCF_PATH
YAM_USD_PATH = BIMANUAL_YAM_USD_PATH

def _bimanual_yam_robot_cfg(
    robot_base_pos: tuple[float, float, float],
) -> ArticulationCfg:
    return BIMANUAL_YAM_CFG.copy().replace(prim_path="/World/envs/env_.*/Robot").replace(
        init_state=ArticulationCfg.InitialStateCfg(
            pos=robot_base_pos,
            rot=(1.0, 0.0, 0.0, 0.0),
            joint_pos=MOLMOACT2_HOME_JOINT_POS,
            joint_vel={".*": 0.0},
        ),
    )


@configclass
class DextrahBimanualYAMCubeGraspEnvCfg(DirectRLEnvCfg):
    """State-based bimanual YAM task: grasp one cube from left and right and lift it."""

    # env
    episode_length_s = 8.0
    decimation = 2
    sim_dt = 1.0 / 120.0
    action_space = 14
    observation_space = 97
    state_space = 97
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
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1024, env_spacing=3.0, replicate_physics=False)

    table_surface_z = MOLMOACT2_TABLE_SURFACE_Z
    table_thickness = MOLMOACT2_TABLE_SIZE[2]
    table_center_x = MOLMOACT2_TABLE_CENTER[0]
    table_center_y = MOLMOACT2_TABLE_CENTER[1]
    table_center_z = MOLMOACT2_TABLE_CENTER[2]
    table_size_x = MOLMOACT2_TABLE_SIZE[0]
    table_size_y = MOLMOACT2_TABLE_SIZE[1]

    robot_base_x = MOLMOACT2_ROBOT_ROOT_POS[0]
    robot_base_y = MOLMOACT2_ROBOT_ROOT_POS[1]
    robot_base_z = MOLMOACT2_ROBOT_ROOT_POS[2]
    robot_base_pos = (robot_base_x, robot_base_y, robot_base_z)
    robot_arm_y_offset = MOLMOACT2_BIMANUAL_ARM_Y_OFFSET
    reset_joint_pos = MOLMOACT2_HOME_JOINT_POS
    rest_joint_pos = MOLMOACT2_REST_JOINT_POS

    molmoact2_norm_tag = MOLMOACT2_NORM_TAG
    molmoact2_camera_order = MOLMOACT2_CAMERA_ORDER
    molmoact2_camera_width = MOLMOACT2_CAMERA_WIDTH
    molmoact2_camera_height = MOLMOACT2_CAMERA_HEIGHT
    molmoact2_top_camera_uid = MOLMOACT2_TOP_CAMERA_UID
    molmoact2_left_camera_uid = MOLMOACT2_LEFT_CAMERA_UID
    molmoact2_right_camera_uid = MOLMOACT2_RIGHT_CAMERA_UID
    molmoact2_top_camera_parent_body = MOLMOACT2_TOP_CAMERA_PARENT_BODY
    molmoact2_left_wrist_camera_parent_body = MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY
    molmoact2_right_wrist_camera_parent_body = MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY
    molmoact2_top_camera_local_pos = MOLMOACT2_TOP_CAMERA_LOCAL_POS
    molmoact2_top_camera_local_quat_wxyz = MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ
    molmoact2_wrist_camera_local_pos = MOLMOACT2_WRIST_CAMERA_LOCAL_POS
    molmoact2_wrist_camera_local_quat_wxyz = MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ
    molmoact2_top_camera_hfov_deg = MOLMOACT2_TOP_CAMERA_HFOV_DEG
    molmoact2_wrist_camera_hfov_deg = MOLMOACT2_WRIST_CAMERA_HFOV_DEG
    molmoact2_top_camera_vfov_deg = MOLMOACT2_TOP_CAMERA_VFOV_DEG
    molmoact2_wrist_camera_vfov_deg = MOLMOACT2_WRIST_CAMERA_VFOV_DEG
    molmoact2_top_camera_intrinsic = MOLMOACT2_TOP_CAMERA_INTRINSIC
    molmoact2_wrist_camera_intrinsic = MOLMOACT2_WRIST_CAMERA_INTRINSIC
    molmoact2_top_camera_eye = (
        robot_base_x + MOLMOACT2_TOP_CAMERA_LOCAL_POS[0],
        robot_base_y + MOLMOACT2_TOP_CAMERA_LOCAL_POS[1],
        robot_base_z + MOLMOACT2_TOP_CAMERA_LOCAL_POS[2],
    )
    _top_camera_y_rot = 2.0 * math.atan2(
        MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ[2],
        MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ[0],
    )
    molmoact2_top_camera_target = (
        molmoact2_top_camera_eye[0]
        + (molmoact2_top_camera_eye[2] - table_surface_z) / math.tan(_top_camera_y_rot),
        molmoact2_top_camera_eye[1],
        table_surface_z,
    )
    molmoact2_object_anchors_xy = MOLMOACT2_OBJECT_ANCHORS_XY
    molmoact2_box_anchor_xy = MOLMOACT2_BOX_ANCHOR_XY

    pickup_x = -0.30
    pickup_y = 0.0
    cube_spawn_xy_randomization = 0.015
    cube_spawn_yaw_randomization_deg = 0.0

    # The YAM linear fingers bottom out at roughly 10.8 cm separation in Isaac,
    # and their reachable pinch band sits around 13-14 cm above the table.
    # An 18 cm cube better matches the bimanual hand-center separation with less
    # interpenetration while keeping the reachable band on the side face.
    cube_size = 0.18
    cube_spawn_z = table_surface_z + cube_size / 2.0 + 0.005
    cube_lift_height = 0.08
    cube_success_lift_height = 0.04
    cube_success_xy_tol = 0.04
    cube_success_hand_dist = 0.18
    cube_success_max_linear_speed = 0.60
    cube_success_max_angular_speed = 8.0
    cube_speed_termination_linear = 1.00
    cube_speed_termination_angular = 10.0
    side_success_y_margin = 0.010
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
    # The controllable grasp point is the midpoint between the two linear
    # fingertips, which is offset from the upstream left_link_6/right_link_6.
    left_tcp_offset_pos = (0.0, 0.0, 0.0605)
    right_tcp_offset_pos = (0.0, 0.0, 0.0605)

    robot: ArticulationCfg = _bimanual_yam_robot_cfg(robot_base_pos)

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

    cube_static_friction = 1.6
    cube_dynamic_friction = 1.1
    cube_restitution = 0.0
    cube_density = 38.0
    cube_contact_offset = 0.002
    cube_rest_offset = 0.0
    cube_solver_position_iterations = 32
    cube_solver_velocity_iterations = 8
    cube_linear_damping = 0.20
    cube_angular_damping = 1.00
    cube_sleep_threshold = 0.02
    cube_stabilization_threshold = 0.01
    cube_max_depenetration_velocity = 1.0

    cube: RigidObjectCfg = RigidObjectCfg(
        prim_path="/World/envs/env_.*/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(cube_size, cube_size, cube_size),
            collision_props=sim_utils.CollisionPropertiesCfg(
                collision_enabled=True,
                contact_offset=cube_contact_offset,
                rest_offset=cube_rest_offset,
            ),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=False,
                disable_gravity=False,
                linear_damping=cube_linear_damping,
                angular_damping=cube_angular_damping,
                enable_gyroscopic_forces=True,
                solver_position_iteration_count=cube_solver_position_iterations,
                solver_velocity_iteration_count=cube_solver_velocity_iterations,
                sleep_threshold=cube_sleep_threshold,
                stabilization_threshold=cube_stabilization_threshold,
                max_linear_velocity=1000.0,
                max_angular_velocity=1000.0,
                max_depenetration_velocity=cube_max_depenetration_velocity,
            ),
            mass_props=sim_utils.MassPropertiesCfg(density=cube_density),
            physics_material=RigidBodyMaterialCfg(
                static_friction=cube_static_friction,
                dynamic_friction=cube_dynamic_friction,
                restitution=cube_restitution,
                friction_combine_mode="max",
                restitution_combine_mode="min",
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.10, 0.42, 0.86),
                roughness=0.65,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(pickup_x, pickup_y, cube_spawn_z),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )

    # reward weights
    cube_approach_weight = 2.0
    cube_approach_sharpness = 10.0
    cube_enclosure_weight = 1.2
    cube_enclosure_sharpness = 8.0
    cube_side_alignment_weight = 1.0
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

    # Optional bimanual scripted-action prior, modeled after the Franka cube
    # action-prior reward.  It never overrides the policy action; it only adds a
    # dense imitation-style reward and exposes reference actions for eval smokes.
    bimanual_action_prior_reward_enabled = False
    bimanual_action_prior_reward_weight = 2.0
    bimanual_action_prior_reward_sharpness = 2.0
    bimanual_reference_gain = 0.85
    bimanual_reference_max_action = 0.65
    bimanual_reference_lift_gain = 0.35
    bimanual_reference_lift_max_action = 0.45
    bimanual_reference_close_steps = 45
    bimanual_reference_standoff_steps = 120
    bimanual_reference_approach_steps = 140
    bimanual_reference_lift_steps = 55
    bimanual_reference_lift_height = 0.060
    bimanual_reference_left_rot_action = (0.0, 0.0, -0.5)
    bimanual_reference_right_rot_action = (0.0, 0.0, 0.5)
    bimanual_reference_contact_side_margin = 0.004
    bimanual_reference_standoff_side_margin = 0.080
    bimanual_reference_standoff_target_dist = 0.050
    bimanual_reference_cube_center_to_hold_z = 0.050
    bimanual_reference_min_hold_z = 0.125
    bimanual_reference_descent_max_action = 0.22
    bimanual_reference_descent_floor_margin = 0.015
    bimanual_reference_contact_dist = 0.180
    bimanual_reference_contact_trigger_dist = 0.166
    bimanual_reference_contact_target_dist = 0.045
    bimanual_reference_lift_squeeze_y = 0.0
    bimanual_reference_closed_width_fraction = 0.65
