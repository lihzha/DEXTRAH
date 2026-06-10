# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from __future__ import annotations

import copy

import isaaclab.envs.mdp as mdp
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.utils import configclass

from .dextrah_kuka_allegro_env_cfg import DextrahKukaAllegroEnvCfg, EventCfg


@configclass
class CubeGraspEventCfg(EventCfg):
    """Reset randomization for the state-based single-cube task."""

    robot_physics_material = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
            "static_friction_range": (1.2, 1.2),
            "dynamic_friction_range": (1.0, 1.0),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 250,
        },
    )

    object_physics_material = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("object", body_names=".*"),
            "static_friction_range": (1.5, 1.5),
            "dynamic_friction_range": (1.2, 1.2),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 250,
        },
    )

    object_scale_mass = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("object"),
            "mass_distribution_params": (1.0, 1.0),
            "operation": "scale",
            "distribution": "uniform",
        },
    )


@configclass
class DextrahCubeGraspEnvCfg(DextrahKukaAllegroEnvCfg):
    """State-based single-cube grasp and lift task."""

    # This task is intentionally state based; camera distillation is not used.
    distillation = False
    obs_type = "cube_state"
    simulate_stereo = False

    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=4096, env_spacing=2.0, replicate_physics=False)

    # The object is a single procedural cube, not an object-set USD asset.
    objects_dir = "single_cube"
    valid_objects_dir = ["single_cube"]
    deactivate_object_scaling = True

    # Object spawn randomization: 8 cm by 8 cm in XY.
    x_center = -0.55
    y_center = 0.10
    cube_spawn_xy_randomization = 0.08

    # Workspace used for out-of-reach termination. This is intentionally wider
    # than the reset randomization range.
    x_width = 0.50
    y_width = 0.50

    # Cube geometry and lift target.
    cube_size = 0.06
    table_top_z = 0.25
    cube_spawn_z = table_top_z + cube_size / 2.0 + 0.005
    cube_lift_height = 0.16
    cube_success_lift_height = 0.12
    cube_success_xy_tol = 0.08
    cube_success_hand_dist = 0.16
    object_goal_tol = 0.08

    # Keep the task focused on grasping/lifting before adding ADR.
    enable_adr = False
    starting_adr_increments = 0
    success_for_adr = 0.8
    max_pose_angle = 45.0

    # Reward weights for dextrah_cube_grasp_rewards.compute_cube_grasp_rewards.
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
    cube_finger_curl_reg_weight = -0.002
    cube_action_penalty_weight = -0.0005

    # Explicit low-bounce cube contact setup.
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

    events: CubeGraspEventCfg = CubeGraspEventCfg()

    adr_custom_cfg_dict = copy.deepcopy(DextrahKukaAllegroEnvCfg.adr_custom_cfg_dict)
    adr_custom_cfg_dict["object_spawn"]["x_width_spawn"] = (
        cube_spawn_xy_randomization,
        cube_spawn_xy_randomization,
    )
    adr_custom_cfg_dict["object_spawn"]["y_width_spawn"] = (
        cube_spawn_xy_randomization,
        cube_spawn_xy_randomization,
    )
    adr_custom_cfg_dict["object_spawn"]["rotation"] = (0.0, 0.0)
    adr_custom_cfg_dict["object_wrench"]["max_linear_accel"] = (0.0, 0.0)
    adr_custom_cfg_dict["object_state_noise"]["object_pos_noise"] = (0.0, 0.0)
    adr_custom_cfg_dict["object_state_noise"]["object_pos_bias"] = (0.0, 0.0)
    adr_custom_cfg_dict["object_state_noise"]["object_rot_noise"] = (0.0, 0.0)
    adr_custom_cfg_dict["object_state_noise"]["object_rot_bias"] = (0.0, 0.0)
    adr_custom_cfg_dict["robot_state_noise"]["robot_joint_pos_noise"] = (0.0, 0.0)
    adr_custom_cfg_dict["robot_state_noise"]["robot_joint_pos_bias"] = (0.0, 0.0)
    adr_custom_cfg_dict["robot_state_noise"]["robot_joint_vel_noise"] = (0.0, 0.0)
    adr_custom_cfg_dict["robot_state_noise"]["robot_joint_vel_bias"] = (0.0, 0.0)
    adr_custom_cfg_dict["robot_spawn"]["joint_pos_noise"] = (0.0, 0.05)
    adr_custom_cfg_dict["robot_spawn"]["joint_vel_noise"] = (0.0, 0.1)
    adr_custom_cfg_dict["observation_annealing"]["coefficient"] = (1.0, 1.0)
