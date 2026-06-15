"""Configuration for the bimanual YAM single-cube grasp task."""

from __future__ import annotations

from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg, RigidObjectCfg
from isaaclab.envs import DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import PhysxCfg, SimulationCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.utils import configclass


DEXTRAH_LAB_ROOT = Path(__file__).resolve().parents[2]
YAM_URDF_PATH = DEXTRAH_LAB_ROOT / "assets" / "yam" / "yam_urdf" / "bimanual_yam.urdf"
YAM_USD_DIR = DEXTRAH_LAB_ROOT / "assets" / "yam" / "yam_usd"

MOLMOACT2_REST_JOINT_POS = {
    # Matches MolmoAct2 BimanualYAM.keyframes["rest"].qpos by joint name.
    "left_joint1": 0.0,
    "left_joint2": 0.7853981633974483,
    "left_joint3": 1.5707963267948966,
    "left_joint4": 0.0,
    "left_joint5": 0.0,
    "left_joint6": 0.0,
    "left_left_finger": -0.02,
    "left_right_finger": -0.02,
    "right_joint1": 0.0,
    "right_joint2": 0.7853981633974483,
    "right_joint3": 1.5707963267948966,
    "right_joint4": 0.0,
    "right_joint5": 0.0,
    "right_joint6": 0.0,
    "right_left_finger": -0.02,
    "right_right_finger": -0.02,
}


def _bimanual_yam_robot_cfg(
    robot_base_pos: tuple[float, float, float],
    gripper_open_joint_pos: float,
) -> ArticulationCfg:
    return ArticulationCfg(
        prim_path="/World/envs/env_.*/Robot",
        spawn=sim_utils.UrdfFileCfg(
            asset_path=str(YAM_URDF_PATH),
            usd_dir=str(YAM_USD_DIR),
            usd_file_name="bimanual_yam.usd",
            fix_base=True,
            root_link_name="bimanual_base",
            merge_fixed_joints=False,
            force_usd_conversion=False,
            make_instanceable=False,
            self_collision=False,
            collision_from_visuals=False,
            replace_cylinders_with_capsules=True,
            joint_drive=None,
            activate_contact_sensors=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=True,
                max_depenetration_velocity=5.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=False,
                solver_position_iteration_count=12,
                solver_velocity_iteration_count=4,
                fix_root_link=True,
            ),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=robot_base_pos,
            rot=(1.0, 0.0, 0.0, 0.0),
            joint_pos=MOLMOACT2_REST_JOINT_POS,
            joint_vel={".*": 0.0},
        ),
        actuators={
            "left_shoulder": ImplicitActuatorCfg(
                joint_names_expr=["left_joint[1-3]"],
                effort_limit_sim=28.0,
                stiffness=80.0,
                damping=6.0,
            ),
            "left_wrist": ImplicitActuatorCfg(
                joint_names_expr=["left_joint[4-6]"],
                effort_limit_sim=12.0,
                stiffness=35.0,
                damping=3.0,
            ),
            "right_shoulder": ImplicitActuatorCfg(
                joint_names_expr=["right_joint[1-3]"],
                effort_limit_sim=28.0,
                stiffness=80.0,
                damping=6.0,
            ),
            "right_wrist": ImplicitActuatorCfg(
                joint_names_expr=["right_joint[4-6]"],
                effort_limit_sim=12.0,
                stiffness=35.0,
                damping=3.0,
            ),
            "left_gripper": ImplicitActuatorCfg(
                joint_names_expr=["left_(left|right)_finger"],
                effort_limit_sim=120.0,
                stiffness=4000.0,
                damping=80.0,
            ),
            "right_gripper": ImplicitActuatorCfg(
                joint_names_expr=["right_(left|right)_finger"],
                effort_limit_sim=120.0,
                stiffness=4000.0,
                damping=80.0,
            ),
        },
        soft_joint_pos_limit_factor=1.0,
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

    cube_size = 0.10
    cube_spawn_z = table_surface_z + cube_size / 2.0 + 0.005
    cube_lift_height = 0.14
    cube_success_lift_height = 0.10
    cube_success_xy_tol = 0.16
    cube_success_hand_dist = 0.18
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

    robot: ArticulationCfg = _bimanual_yam_robot_cfg(robot_base_pos, gripper_open_joint_pos)

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

    cube_static_friction = 1.8
    cube_dynamic_friction = 1.4
    cube_restitution = 0.0
    cube_density = 120.0
    cube_contact_offset = 0.004
    cube_rest_offset = 0.0
    cube_solver_position_iterations = 14
    cube_solver_velocity_iterations = 4
    cube_linear_damping = 0.08
    cube_angular_damping = 0.25
    cube_sleep_threshold = 0.02
    cube_stabilization_threshold = 0.01
    cube_max_depenetration_velocity = 3.0

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
