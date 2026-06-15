"""Configuration for the bimanual YAM single-cube grasp task."""

from __future__ import annotations

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
    MOLMOACT2_REST_JOINT_POS,
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
            joint_pos=MOLMOACT2_REST_JOINT_POS,
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
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1024, env_spacing=1.8, replicate_physics=False)

    # MolmoAct2 YAM-relative layout. Their ManiSkill task places the YAM base
    # at (-0.65, 0, 0.01), the box at (-0.15, 0), and objects near x=-0.30
    # with left/right split on +Y/-Y.
    robot_base_x = -0.65
    robot_base_y = 0.0
    robot_base_z = 0.01
    robot_base_pos = (robot_base_x, robot_base_y, robot_base_z)
    table_surface_z = 0.0
    table_thickness = 0.052
    table_center_x = -0.27
    table_center_y = 0.0
    table_center_z = table_surface_z - 0.5 * table_thickness
    table_size_x = 0.74
    table_size_y = 0.74

    pickup_x = -0.30
    pickup_y = 0.0
    cube_spawn_xy_randomization = 0.015
    cube_spawn_yaw_randomization_deg = 0.0

    # The YAM linear fingers bottom out at roughly 10.8 cm separation in Isaac,
    # and their reachable pinch band sits around 13-14 cm above the table.
    # A 16 cm cube is wide enough to pinch and tall enough for that reachable
    # band to contact the side face instead of lifting above the object.
    cube_size = 0.16
    cube_spawn_z = table_surface_z + cube_size / 2.0 + 0.005
    cube_lift_height = 0.08
    cube_success_lift_height = 0.04
    cube_success_xy_tol = 0.16
    cube_success_hand_dist = 0.18
    cube_success_max_linear_speed = 0.60
    cube_success_max_angular_speed = 8.0
    side_success_y_margin = 0.010
    success_timeout = 0.10
    min_episode_steps_before_success = 30
    prelift_drag_termination_xy_error = 0.18
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
    cube_density = 80.0
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

    # Optional bimanual scripted-action prior, modeled after the Franka cube
    # action-prior reward.  It never overrides the policy action; it only adds a
    # dense imitation-style reward and exposes reference actions for eval smokes.
    bimanual_action_prior_reward_enabled = False
    bimanual_action_prior_reward_weight = 2.0
    bimanual_action_prior_reward_sharpness = 2.0
    bimanual_reference_gain = 1.35
    bimanual_reference_max_action = 1.0
    bimanual_reference_lift_gain = 0.35
    bimanual_reference_lift_max_action = 0.45
    bimanual_reference_contact_side_margin = 0.004
    bimanual_reference_cube_center_to_hold_z = 0.055
    bimanual_reference_min_hold_z = 0.130
    bimanual_reference_contact_dist = 0.180
    bimanual_reference_contact_target_dist = 0.045
    bimanual_reference_closed_width_fraction = 0.65
