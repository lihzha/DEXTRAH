"""DirectRLEnv for one bimanual YAM robot on the shared multi-object grasp task."""

from __future__ import annotations

from collections.abc import Sequence

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from dextrah_lab.tasks.dextrah_multi_object_grasp.multi_object_grasp_task import MultiObjectGraspTaskMixin
from dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.bimanual_yam_cube_grasp_env import (
    DextrahBimanualYAMCubeGraspEnv,
)

from .single_yam_multi_object_grasp_env_cfg import DextrahSingleYAMMultiObjectGraspEnvCfg


class DextrahSingleYAMMultiObjectGraspEnv(MultiObjectGraspTaskMixin, DextrahBimanualYAMCubeGraspEnv):
    """YAM task: pick up one of many GraspGen object assets per vectorized env."""

    cfg: DextrahSingleYAMMultiObjectGraspEnvCfg

    def _setup_scene(self):
        self._setup_multi_object_task()
        self._setup_tabletop_clutter_task()

        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        spawn_ground_plane(
            prim_path="/World/ground",
            cfg=GroundPlaneCfg(size=(6.0, 6.0), color=(0.03, 0.03, 0.03)),
            translation=(0.0, 0.0, -0.08),
        )

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table
        self._spawn_multi_object_assets()
        self._spawn_tabletop_clutter_assets()

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)

    def _sync_reset_joint_state(
        self,
        env_ids: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        *,
        update_buffers: bool,
    ) -> None:
        self._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
        self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        if update_buffers:
            self.robot_dof_targets[env_ids] = joint_pos
            self.left_arm_joint_pos_target[env_ids] = joint_pos[:, self.left_arm_joint_ids]
            self.right_arm_joint_pos_target[env_ids] = joint_pos[:, self.right_arm_joint_ids]
            self.left_finger_joint_pos_target[env_ids] = joint_pos[:, self.left_finger_joint_ids]
            self.right_finger_joint_pos_target[env_ids] = joint_pos[:, self.right_finger_joint_ids]
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

    def _reset_idx(self, env_ids: Sequence[int] | None):
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super(DextrahBimanualYAMCubeGraspEnv, self)._reset_idx(env_ids)

        num_ids = len(env_ids)
        joint_pos = self._robot.data.default_joint_pos[env_ids].clone()
        joint_vel = torch.zeros_like(joint_pos)
        joint_noise = torch.zeros_like(joint_pos)
        arm_noise = float(self.cfg.arm_joint_reset_noise)
        if arm_noise > 0.0:
            joint_noise[:, self.arm_joint_ids] = arm_noise * (
                2.0 * torch.rand(num_ids, len(self.arm_joint_ids), device=self.device) - 1.0
            )
        joint_pos = torch.clamp(joint_pos + joint_noise, self.robot_dof_lower_limits, self.robot_dof_upper_limits)
        self._sync_reset_joint_state(env_ids, joint_pos, joint_vel, update_buffers=True)

        object_radius_xy = self.object_xy_radius[env_ids]
        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.table_center_x) + float(self.cfg.object_spawn_center_offset_x)
        spawn_xy[:, 1] = float(self.cfg.table_center_y) + float(self.cfg.object_spawn_center_offset_y)
        spawn_xy += float(self.cfg.object_spawn_xy_randomization) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x) + object_radius_xy
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x) - object_radius_xy
        min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y) + object_radius_xy
        max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y) - object_radius_xy
        spawn_xy[:, 0] = torch.minimum(torch.maximum(spawn_xy[:, 0], min_x), max_x)
        spawn_xy[:, 1] = torch.minimum(torch.maximum(spawn_xy[:, 1], min_y), max_y)

        object_pos = torch.zeros(num_ids, 3, device=self.device)
        object_pos[:, 0:2] = spawn_xy
        object_quat, object_root_z_offset = self._sample_object_reset_pose(env_ids)
        object_pos[:, 2] = (
            float(self.cfg.table_surface_z)
            + object_root_z_offset
            + float(self.cfg.object_spawn_z_clearance)
        )
        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = object_pos + self.scene.env_origins[env_ids]
        object_state[:, 3:7] = object_quat
        self._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
        self._reset_tabletop_clutter(env_ids, target_root_pos=object_pos)
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

        object_pos, object_quat = self._settle_reset_objects(env_ids, joint_pos, joint_vel)
        object_center_pos = self._object_center_pos_from_root(env_ids, object_pos, object_quat)
        self.cube_initial_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids, 2] = object_center_pos[:, 2] + float(self.cfg.cube_lift_height)
        self.has_lifted_cube[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
        self.cube_speed_done[env_ids] = False
        self.actions[env_ids] = 0.0
        self.left_ik_controller.reset(env_ids)
        self.right_ik_controller.reset(env_ids)

        self._compute_intermediate_values(env_ids)
        self.bimanual_reference_start_left_hold[env_ids] = self.left_hold_pos[env_ids]
        self.bimanual_reference_start_right_hold[env_ids] = self.right_hold_pos[env_ids]
        self.bimanual_reference_lift_started[env_ids] = False
        self.bimanual_reference_lift_start_step[env_ids] = 0.0
        self.bimanual_reference_lift_left_origin[env_ids] = self.left_hold_pos[env_ids]
        self.bimanual_reference_lift_right_origin[env_ids] = self.right_hold_pos[env_ids]

    def _compute_intermediate_values(
        self,
        env_ids: torch.Tensor | None = None,
        *,
        update_success_timer: bool = False,
    ) -> None:
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super()._compute_intermediate_values(env_ids, update_success_timer=False)

        env_origins = self.scene.env_origins[env_ids]
        root_pos = self._cube.data.root_pos_w[env_ids] - env_origins
        root_quat = self._cube.data.root_quat_w[env_ids]
        center_pos = self._object_center_pos_from_root(env_ids, root_pos, root_quat)
        self.cube_pos[env_ids] = center_pos
        self.cube_lift_height[env_ids] = torch.clamp(
            center_pos[:, 2] - self.cube_initial_pos[env_ids, 2],
            min=0.0,
        )
        self.cube_xy_error[env_ids] = torch.norm(center_pos[:, :2] - self.cube_initial_pos[env_ids, :2], dim=-1)
        self.cube_goal_height_error[env_ids] = torch.abs(self.cube_goal_pos[env_ids, 2] - center_pos[:, 2])
        self.has_lifted_cube[env_ids] |= self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height)

        self.left_hold_to_cube_dist[env_ids] = torch.norm(self.left_hold_pos[env_ids] - center_pos, dim=-1)
        self.right_hold_to_cube_dist[env_ids] = torch.norm(self.right_hold_pos[env_ids] - center_pos, dim=-1)
        self.max_hold_to_cube_dist[env_ids] = torch.maximum(
            self.left_hold_to_cube_dist[env_ids],
            self.right_hold_to_cube_dist[env_ids],
        )
        self.hold_distance_asymmetry[env_ids] = torch.abs(
            self.left_hold_to_cube_dist[env_ids] - self.right_hold_to_cube_dist[env_ids]
        )
        bimanual_center = 0.5 * (self.left_hold_pos[env_ids] + self.right_hold_pos[env_ids])
        self.bimanual_center_to_cube_dist[env_ids] = torch.norm(bimanual_center - center_pos, dim=-1)

        side_margin = float(self.cfg.side_success_y_margin)
        left_side_distance = self.left_hold_pos[env_ids, 1] - center_pos[:, 1]
        right_side_distance = center_pos[:, 1] - self.right_hold_pos[env_ids, 1]
        side_scale = torch.clamp(0.5 * self.object_grasp_size[env_ids], min=1.0e-6)
        self.left_side_alignment[env_ids] = torch.clamp((left_side_distance + side_margin) / side_scale, 0.0, 1.0)
        self.right_side_alignment[env_ids] = torch.clamp((right_side_distance + side_margin) / side_scale, 0.0, 1.0)
        self.bimanual_side_success[env_ids] = (
            (left_side_distance >= -side_margin)
            & (right_side_distance >= -side_margin)
            & (self.left_hold_to_cube_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
            & (self.right_hold_to_cube_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
        )

        success = (
            (self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height))
            & (self.cube_xy_error[env_ids] <= float(self.cfg.cube_success_xy_tol))
            & self.bimanual_side_success[env_ids]
            & (self.finger_table_clearance[env_ids] >= float(self.cfg.finger_table_clearance_success_margin))
            & (self.cube_linear_speed[env_ids] <= float(self.cfg.cube_success_max_linear_speed))
            & (self.cube_angular_speed[env_ids] <= float(self.cfg.cube_success_max_angular_speed))
        )
        self.cube_velocity_success_stable[env_ids] = (
            (self.cube_linear_speed[env_ids] <= float(self.cfg.cube_success_max_linear_speed))
            & (self.cube_angular_speed[env_ids] <= float(self.cfg.cube_success_max_angular_speed))
        )
        self.in_success_region[env_ids] = success
        if update_success_timer:
            self.time_in_success_region[env_ids] = torch.where(
                success,
                self.time_in_success_region[env_ids] + self.dt,
                torch.zeros_like(self.time_in_success_region[env_ids]),
            )
        else:
            self.time_in_success_region[env_ids] = torch.where(
                success,
                self.time_in_success_region[env_ids],
                torch.zeros_like(self.time_in_success_region[env_ids]),
            )

    def _get_observations(self) -> dict[str, torch.Tensor]:
        base = super()._get_observations()
        obs = torch.clamp(torch.cat((base["policy"], self._multi_object_features()), dim=-1), -5.0, 5.0)
        return {"policy": obs, "critic": obs}

    def _get_rewards(self) -> torch.Tensor:
        rewards = super()._get_rewards()
        if "log" in self.extras:
            self._add_multi_object_log_terms(self.extras["log"], distance_term=self.bimanual_center_to_cube_dist)
        return rewards

    def get_current_observations(self):
        return self._get_observations()
