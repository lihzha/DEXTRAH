# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.nn.functional as F

import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObject, RigidObjectCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg

from .dextrah_cube_grasp_env_cfg import DextrahCubeGraspEnvCfg
from .dextrah_cube_grasp_rewards import compute_cube_grasp_rewards
from .dextrah_kuka_allegro_env import DextrahKukaAllegroEnv


class DextrahCubeGraspEnv(DextrahKukaAllegroEnv):
    """Single procedural cube grasp-and-lift task using the DextrAH controller."""

    cfg: DextrahCubeGraspEnvCfg

    def __init__(self, cfg: DextrahCubeGraspEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        self._ensure_cube_task_buffers()
        self.object_goal[:, 0] = self.cfg.x_center
        self.object_goal[:, 1] = self.cfg.y_center
        self.object_goal[:, 2] = self.cfg.cube_spawn_z + self.cfg.cube_lift_height

    def _ensure_cube_task_buffers(self) -> None:
        if hasattr(self, "cube_initial_pos"):
            return
        self.cube_initial_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_initial_pos[:, 0] = self.cfg.x_center
        self.cube_initial_pos[:, 1] = self.cfg.y_center
        self.cube_initial_pos[:, 2] = self.cfg.cube_spawn_z
        self.cube_lift_height = torch.zeros(self.num_envs, device=self.device)
        self.cube_xy_error = torch.zeros(self.num_envs, device=self.device)
        self.cube_goal_height_error = torch.zeros(self.num_envs, device=self.device)
        self.hand_to_cube_mean_dist = torch.zeros(self.num_envs, device=self.device)
        self.hand_to_cube_max_dist = torch.zeros(self.num_envs, device=self.device)

    def _setup_policy_params(self):
        self.num_unique_objects = 1
        self.cfg.num_student_observations = 159
        self.cfg.num_teacher_observations = 168
        self.cfg.num_observations = self.cfg.num_teacher_observations
        self.cfg.num_states = 215
        self.cfg.state_space = self.cfg.num_states
        self.cfg.observation_space = self.cfg.num_observations
        self.cfg.action_space = self.cfg.num_actions

    def _setup_objects(self):
        self.num_unique_objects = 1
        self.multi_object_idx = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.multi_object_idx_onehot = F.one_hot(self.multi_object_idx, num_classes=1).float()
        self.object_scale = torch.ones(self.num_envs, 1, device=self.device)
        self.total_object_scales = self.object_scale.clone()
        self.device_index = self.object_scale.device.index or 0
        self.object_mat_prims = []
        self.arm_mat_prims = []

        cube_spawn_cfg = sim_utils.CuboidCfg(
            size=(self.cfg.cube_size, self.cfg.cube_size, self.cfg.cube_size),
            collision_props=sim_utils.CollisionPropertiesCfg(
                collision_enabled=True,
                contact_offset=self.cfg.cube_contact_offset,
                rest_offset=self.cfg.cube_rest_offset,
            ),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=False,
                disable_gravity=False,
                linear_damping=self.cfg.cube_linear_damping,
                angular_damping=self.cfg.cube_angular_damping,
                enable_gyroscopic_forces=True,
                solver_position_iteration_count=self.cfg.cube_solver_position_iterations,
                solver_velocity_iteration_count=self.cfg.cube_solver_velocity_iterations,
                sleep_threshold=self.cfg.cube_sleep_threshold,
                stabilization_threshold=self.cfg.cube_stabilization_threshold,
                max_linear_velocity=1000.0,
                max_angular_velocity=1000.0,
                max_depenetration_velocity=self.cfg.cube_max_depenetration_velocity,
            ),
            mass_props=sim_utils.MassPropertiesCfg(density=self.cfg.cube_density),
            physics_material=RigidBodyMaterialCfg(
                static_friction=self.cfg.cube_static_friction,
                dynamic_friction=self.cfg.cube_dynamic_friction,
                restitution=self.cfg.cube_restitution,
                friction_combine_mode="max",
                restitution_combine_mode="min",
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.10, 0.42, 0.86),
                roughness=0.65,
            ),
        )

        for env_id in range(self.num_envs):
            prim_path = f"/World/envs/env_{env_id}/object/cube"
            object_cfg = RigidObjectCfg(
                prim_path=prim_path,
                spawn=cube_spawn_cfg,
                init_state=RigidObjectCfg.InitialStateCfg(
                    pos=(self.cfg.x_center, self.cfg.y_center, self.cfg.cube_spawn_z),
                    rot=(1.0, 0.0, 0.0, 0.0),
                ),
            )
            RigidObject(object_cfg)

        self.object = RigidObject(RigidObjectCfg(prim_path="/World/envs/env_.*/object/.*", spawn=None))
        self.scene.rigid_objects["object"] = self.object

    def _reset_idx(self, env_ids: Sequence[int] | None):
        if env_ids is None:
            env_ids = self.robot._ALL_INDICES
        super()._reset_idx(env_ids)
        self._ensure_cube_task_buffers()

        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        num_ids = env_ids.shape[0]
        object_xy = self.object_pos[env_ids, :2].clone()

        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:2] = object_xy + self.scene.env_origins[env_ids, 0:2]
        object_state[:, 2] = self.cfg.cube_spawn_z + self.scene.env_origins[env_ids, 2]
        object_state[:, 3] = 1.0
        self.object.write_root_state_to_sim(object_state, env_ids)

        self.cube_initial_pos[env_ids, :2] = object_xy
        self.cube_initial_pos[env_ids, 2] = self.cfg.cube_spawn_z
        self.object_goal[env_ids, :2] = object_xy
        self.object_goal[env_ids, 2] = self.cfg.cube_spawn_z + self.cfg.cube_lift_height

        self._compute_intermediate_values()
        self.compute_intermediate_reward_values()

    def compute_intermediate_reward_values(self):
        self._ensure_cube_task_buffers()

        self.object_to_object_goal_pos_error = torch.norm(self.object_pos - self.object_goal, dim=-1)
        self.object_vertical_error = torch.abs(self.object_goal[:, 2] - self.object_pos[:, 2])

        self.cube_lift_height = torch.clamp(self.object_pos[:, 2] - self.cube_initial_pos[:, 2], min=0.0)
        self.cube_goal_height_error = torch.abs(self.object_goal[:, 2] - self.object_pos[:, 2])
        self.cube_xy_error = torch.norm(self.object_pos[:, :2] - self.cube_initial_pos[:, :2], dim=-1)

        hand_dist = torch.norm(self.hand_pos - self.object_pos[:, None, :], dim=-1)
        self.hand_to_cube_mean_dist = hand_dist.mean(dim=-1)
        self.hand_to_cube_max_dist = hand_dist.max(dim=-1).values
        self.hand_to_object_pos_error = self.hand_to_cube_mean_dist

        self.in_success_region = (
            (self.cube_lift_height >= self.cfg.cube_success_lift_height)
            & (self.cube_xy_error <= self.cfg.cube_success_xy_tol)
            & (self.hand_to_cube_mean_dist <= self.cfg.cube_success_hand_dist)
        )
        self.time_in_success_region = torch.where(
            self.in_success_region,
            self.time_in_success_region + self.cfg.sim.dt * self.cfg.decimation,
            0.0,
        )

    def _named_checkpoint_tensors(self):
        return super()._named_checkpoint_tensors() + (
            "cube_initial_pos",
            "cube_lift_height",
            "cube_xy_error",
            "cube_goal_height_error",
            "hand_to_cube_mean_dist",
            "hand_to_cube_max_dist",
        )

    def _get_rewards(self) -> torch.Tensor:
        self.compute_intermediate_reward_values()

        (
            approach_reward,
            enclosure_reward,
            lift_reward,
            height_tracking_reward,
            xy_stability_reward,
            success_bonus,
            finger_curl_reg,
            action_penalty,
        ) = compute_cube_grasp_rewards(
            self.hand_to_cube_mean_dist,
            self.hand_to_cube_max_dist,
            self.cube_lift_height,
            self.cube_goal_height_error,
            self.cube_xy_error,
            self.in_success_region,
            self.robot_dof_pos[:, 7:],
            self.curled_q,
            self.actions,
            self.cfg.cube_lift_height,
            self.cfg.cube_approach_weight,
            self.cfg.cube_approach_sharpness,
            self.cfg.cube_enclosure_weight,
            self.cfg.cube_enclosure_sharpness,
            self.cfg.cube_lift_weight,
            self.cfg.cube_height_tracking_weight,
            self.cfg.cube_height_tracking_sharpness,
            self.cfg.cube_xy_stability_weight,
            self.cfg.cube_xy_stability_sharpness,
            self.cfg.cube_success_bonus_weight,
            self.cfg.cube_finger_curl_reg_weight,
            self.cfg.cube_action_penalty_weight,
        )

        self.extras["cube_approach_reward"] = approach_reward.mean()
        self.extras["cube_enclosure_reward"] = enclosure_reward.mean()
        self.extras["cube_lift_reward"] = lift_reward.mean()
        self.extras["cube_height_tracking_reward"] = height_tracking_reward.mean()
        self.extras["cube_xy_stability_reward"] = xy_stability_reward.mean()
        self.extras["cube_success_bonus"] = success_bonus.mean()
        self.extras["cube_finger_curl_reg"] = finger_curl_reg.mean()
        self.extras["cube_action_penalty"] = action_penalty.mean()
        self.extras["cube_lift_height"] = self.cube_lift_height.mean()
        self.extras["cube_xy_error"] = self.cube_xy_error.mean()
        self.extras["cube_success_rate"] = self.in_success_region.float().mean()
        self.extras["num_adr_increases"] = self.dextrah_adr.num_increments()
        self.extras["in_success_region"] = self.in_success_region.float().mean()

        return (
            approach_reward
            + enclosure_reward
            + lift_reward
            + height_tracking_reward
            + xy_stability_reward
            + success_bonus
            + finger_curl_reg
            + action_penalty
        )
