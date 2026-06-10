"""Configuration for the Franka single-cube grasp task."""

from __future__ import annotations

import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObjectCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.utils import configclass

from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env_cfg import (
    DextrahFrankaStarKittingEnvCfg,
)


FRANKA_TABLE_CENTER_Z = 0.72
FRANKA_TABLE_THICKNESS = 0.052
FRANKA_TABLE_SURFACE_Z = FRANKA_TABLE_CENTER_Z + 0.5 * FRANKA_TABLE_THICKNESS


@configclass
class DextrahFrankaCubeGraspEnvCfg(DextrahFrankaStarKittingEnvCfg):
    """State-based Franka pick-up task for the same procedural cube objective as Dextrah-Cube-Grasp."""

    # env
    observation_space = 72
    state_space = 72
    num_observations = observation_space
    num_states = state_space

    # cube pickup location uses the already validated Franka table workspace.
    pickup_x = -0.36
    pickup_y = -0.12
    cube_spawn_xy_randomization = 0.08

    # cube geometry and lift target match the KUKA/Allegro cube task.
    cube_size = 0.06
    cube_spawn_z = FRANKA_TABLE_SURFACE_Z + cube_size / 2.0 + 0.005
    cube_lift_height = 0.16
    cube_success_lift_height = 0.12
    cube_success_xy_tol = 0.08
    cube_success_hand_dist = 0.20
    target_lift_height = cube_lift_height
    lifted_success_height = cube_success_lift_height
    success_timeout = 0.20
    min_episode_steps_before_success = 40
    prelift_drag_termination_xy_error = 0.10

    # KUKA-cube-shaped reward weights for franka_cube_grasp_rewards.compute_franka_cube_grasp_rewards.
    # Robot-specific differences are handled in the reward inputs: two Franka
    # finger distances replace the DEXTRAH multi-finger hand distances, and the
    # parallel gripper width replaces the Allegro curl regularizer.
    cube_approach_weight = 2.0
    cube_approach_sharpness = 10.0
    cube_enclosure_weight = 1.0
    cube_enclosure_sharpness = 8.0
    cube_lift_weight = 10.0
    cube_height_tracking_weight = 3.0
    cube_height_tracking_sharpness = 18.0
    cube_xy_stability_weight = 1.0
    cube_xy_stability_sharpness = 12.0
    cube_success_bonus_weight = 15.0
    cube_gripper_close_reg_weight = -0.002
    cube_action_penalty_weight = -0.0005

    # explicit low-bounce cube contact setup, kept close to Dextrah-Cube-Grasp.
    cube_static_friction = 1.5
    cube_dynamic_friction = 1.2
    cube_restitution = 0.0
    cube_density = 500.0
    cube_contact_offset = 0.004
    cube_rest_offset = 0.0
    cube_solver_position_iterations = 12
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
