"""Configuration for the Franka star-kitting DirectRLEnv."""

from __future__ import annotations

import math

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, RigidObjectCfg
from isaaclab.envs import DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import PhysxCfg, SimulationCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.utils import configclass

from isaaclab_assets.robots.franka import FRANKA_PANDA_HIGH_PD_CFG


def _franka_star_robot_cfg(
    robot_base_z: float,
    robot_yaw_wxyz: tuple[float, float, float, float],
    finger_effort_limit: float,
    finger_stiffness: float,
    finger_damping: float,
) -> ArticulationCfg:
    robot_cfg = FRANKA_PANDA_HIGH_PD_CFG.copy().replace(prim_path="/World/envs/env_.*/Robot").replace(
        init_state=ArticulationCfg.InitialStateCfg(
            pos=(0.0, 0.0, robot_base_z),
            rot=robot_yaw_wxyz,
            joint_pos={
                "panda_joint1": 0.0,
                "panda_joint2": -0.68,
                "panda_joint3": 0.0,
                "panda_joint4": -2.45,
                "panda_joint5": 0.0,
                "panda_joint6": 2.28,
                "panda_joint7": 0.78,
                "panda_finger_joint.*": 0.04,
            },
            joint_vel={".*": 0.0},
        )
    )
    robot_cfg.actuators["panda_hand"].effort_limit_sim = float(finger_effort_limit)
    robot_cfg.actuators["panda_hand"].stiffness = float(finger_stiffness)
    robot_cfg.actuators["panda_hand"].damping = float(finger_damping)
    return robot_cfg


@configclass
class DextrahFrankaStarKittingEnvCfg(DirectRLEnvCfg):
    """State-based Franka pick-and-place kitting task for a star object."""

    # env
    episode_length_s = 10.0
    decimation = 2
    sim_dt = 1.0 / 120.0
    action_space = 7
    observation_space = 68
    state_space = 68
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
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=2048, env_spacing=2.2, replicate_physics=False)

    # table and kitting geometry
    table_center_x = -0.62
    table_center_y = 0.0
    table_center_z = 0.72
    table_size_x = 0.86
    table_size_y = 1.18
    table_thickness = 0.052
    table_surface_z = table_center_z + 0.5 * table_thickness

    pickup_x = -0.36
    pickup_y = -0.12
    fixture_x = -0.45
    fixture_y = 0.16
    fixture_yaw_deg = 18.0
    star_start_yaw_deg = -24.0
    star_spawn_xy_randomization = 0.0
    star_spawn_yaw_randomization_deg = 0.0
    star_reset_near_hand_probability = 0.0
    star_reset_near_hand_x = -0.360
    star_reset_near_hand_y = -0.120
    star_reset_near_hand_xy_noise = 0.020
    star_reset_near_hand_x_offset = 0.0
    star_reset_near_hand_y_offset = 0.0

    star_outer_radius = 0.032
    star_inner_radius = 0.0145
    star_thickness = 0.040
    fixture_size_x = 0.18
    fixture_size_y = 0.18
    fixture_thickness = 0.060
    fixture_clearance = 0.006
    star_density = 260.0

    # Franka geometry/control
    max_gripper_width = 0.08
    arm_joint_reset_noise = 0.035
    robot_base_z = 0.20
    robot_yaw_wxyz = (0.0, 0.0, 0.0, 1.0)  # 180 deg about z; points arm toward negative X table.
    ee_offset_pos = (0.0, 0.0, 0.1034)
    ik_position_action_scale = (0.060, 0.060, 0.045)
    ik_rotation_action_scale = (0.25, 0.25, 0.30)
    finger_effort_limit = 1000.0
    finger_stiffness = 4000.0
    finger_damping = 400.0

    robot: ArticulationCfg = _franka_star_robot_cfg(
        robot_base_z,
        robot_yaw_wxyz,
        finger_effort_limit,
        finger_stiffness,
        finger_damping,
    )

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

    # task success
    target_lift_height = 0.080
    lifted_success_height = 0.055
    placement_xy_tol = 0.025
    placement_yaw_tol = math.radians(10.0)
    placement_height_tol = 0.025
    success_timeout = 0.20
    out_of_bounds_margin = 0.18
    min_episode_steps_before_success = 50

    # rewards
    approach_weight = 3.0
    approach_sharpness = 9.0
    finger_approach_weight = 9.0
    finger_approach_sharpness = 14.0
    grasp_pose_weight = 10.0
    both_fingers_near_weight = 14.0
    lift_ready_weight = 36.0
    grasp_weight = 2.0
    closed_grasp_weight = 26.0
    grasp_sharpness = 18.0
    lift_weight = 260.0
    descend_action_weight = 10.0
    lift_action_weight = 44.0
    close_near_weight = 6.0
    close_action_weight = 14.0
    prelift_move_penalty_weight = -34.0
    close_far_penalty_weight = -14.0
    open_near_penalty_weight = -10.0
    ungrasped_lift_penalty_weight = -12.0
    transport_weight = 6.0
    transport_xy_sharpness = 18.0
    yaw_weight = 3.0
    yaw_sharpness = 4.5
    placement_weight = 12.0
    placement_height_sharpness = 18.0
    success_bonus_weight = 80.0
    action_penalty_weight = -0.002
