# Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in to this material, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this material and related documentation without an express
# license agreement from NVIDIA CORPORATION or its affiliates is strictly
# prohibited.

"""DirectRLEnv for Franka star-object kitting."""

from __future__ import annotations

from collections.abc import Sequence
import math

import torch

import omni.usd
import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.envs import DirectRLEnv
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane
from pxr import UsdGeom

from .franka_star_kitting_env_cfg import DextrahFrankaStarKittingEnvCfg
from .franka_star_kitting_rewards import compute_franka_star_kitting_rewards
from .star_kitting_geometry import (
    StarKittingGeometryCfg,
    create_fixture,
    create_star_object,
    geometry_diagnostics,
    material,
)


def _yaw_quat_wxyz(yaw_rad: torch.Tensor) -> torch.Tensor:
    quat = torch.zeros(yaw_rad.shape[0], 4, device=yaw_rad.device)
    quat[:, 0] = torch.cos(0.5 * yaw_rad)
    quat[:, 3] = torch.sin(0.5 * yaw_rad)
    return quat


def _yaw_from_quat_wxyz(quat: torch.Tensor) -> torch.Tensor:
    w = quat[:, 0]
    x = quat[:, 1]
    y = quat[:, 2]
    z = quat[:, 3]
    return torch.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def _wrap_to_pi(angle: torch.Tensor) -> torch.Tensor:
    return torch.atan2(torch.sin(angle), torch.cos(angle))


class DextrahFrankaStarKittingEnv(DirectRLEnv):
    """Franka task: pick a star object and place it into a matching fixture."""

    cfg: DextrahFrankaStarKittingEnvCfg

    def __init__(self, cfg: DextrahFrankaStarKittingEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)

        self.dt = self.cfg.sim.dt * self.cfg.decimation
        self.robot_dof_lower_limits = self._robot.data.soft_joint_pos_limits[0, :, 0].to(self.device)
        self.robot_dof_upper_limits = self._robot.data.soft_joint_pos_limits[0, :, 1].to(self.device)

        self.arm_joint_ids, self.arm_joint_names = self._robot.find_joints("panda_joint.*")
        self.finger_joint_ids, self.finger_joint_names = self._robot.find_joints("panda_finger_joint.*")
        body_ids, body_names = self._robot.find_bodies("panda_hand")
        if len(body_ids) != 1:
            raise ValueError(f"Expected exactly one panda_hand body, got {body_names}")
        self.ee_body_idx = int(body_ids[0])
        self.ee_jacobi_idx = self.ee_body_idx - 1 if self._robot.is_fixed_base else self.ee_body_idx
        self.left_finger_body_idx = int(self._robot.find_bodies("panda_leftfinger")[0][0])
        self.right_finger_body_idx = int(self._robot.find_bodies("panda_rightfinger")[0][0])

        ik_cfg = DifferentialIKControllerCfg(command_type="pose", use_relative_mode=True, ik_method="dls")
        self.ik_controller = DifferentialIKController(ik_cfg, num_envs=self.num_envs, device=self.device)
        self.ee_offset_pos = torch.tensor(self.cfg.ee_offset_pos, device=self.device).repeat(self.num_envs, 1)
        self.ee_offset_rot = torch.tensor((1.0, 0.0, 0.0, 0.0), device=self.device).repeat(self.num_envs, 1)
        self.action_scale = torch.tensor(
            tuple(self.cfg.ik_position_action_scale) + tuple(self.cfg.ik_rotation_action_scale),
            device=self.device,
        )

        self.actions = torch.zeros(self.num_envs, self.cfg.action_space, device=self.device)
        self.arm_joint_pos_target = self._robot.data.default_joint_pos[:, self.arm_joint_ids].clone()
        self.finger_joint_pos_target = self._robot.data.default_joint_pos[:, self.finger_joint_ids].clone()
        self.robot_dof_targets = self._robot.data.default_joint_pos.clone()

        self.geometry_cfg = self._geometry_cfg()
        self.geometry_diagnostics = geometry_diagnostics(
            self.geometry_cfg, max_gripper_width=float(self.cfg.max_gripper_width)
        )

        self.star_initial_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.star_goal_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.star_goal_yaw = torch.zeros(self.num_envs, device=self.device)
        self.star_lift_height = torch.zeros(self.num_envs, device=self.device)
        self.has_lifted_star = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.in_success_region = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.time_in_success_region = torch.zeros(self.num_envs, device=self.device)

        self.ee_to_star_dist = torch.zeros(self.num_envs, device=self.device)
        self.finger_center_to_star_dist = torch.zeros(self.num_envs, device=self.device)
        self.left_finger_to_star_dist = torch.zeros(self.num_envs, device=self.device)
        self.right_finger_to_star_dist = torch.zeros(self.num_envs, device=self.device)
        self.max_finger_to_star_dist = torch.zeros(self.num_envs, device=self.device)
        self.finger_distance_asymmetry = torch.zeros(self.num_envs, device=self.device)
        self.star_initial_xy_error = torch.zeros(self.num_envs, device=self.device)
        self.goal_xy_error = torch.zeros(self.num_envs, device=self.device)
        self.goal_height_error = torch.zeros(self.num_envs, device=self.device)
        self.goal_yaw_error = torch.zeros(self.num_envs, device=self.device)
        self.gripper_width = torch.zeros(self.num_envs, device=self.device)

    def _geometry_cfg(self) -> StarKittingGeometryCfg:
        return StarKittingGeometryCfg(
            star_outer_radius=float(self.cfg.star_outer_radius),
            star_inner_radius=float(self.cfg.star_inner_radius),
            star_thickness=float(self.cfg.star_thickness),
            fixture_size_x=float(self.cfg.fixture_size_x),
            fixture_size_y=float(self.cfg.fixture_size_y),
            fixture_thickness=float(self.cfg.fixture_thickness),
            fixture_clearance=float(self.cfg.fixture_clearance),
            star_density=float(self.cfg.star_density),
        )

    def _setup_scene(self):
        diagnostics = geometry_diagnostics(
            self._geometry_cfg(), max_gripper_width=float(self.cfg.max_gripper_width)
        )
        if not bool(diagnostics["star_fits_franka_gripper"]):
            raise ValueError(f"Star is too large for the Franka gripper: {diagnostics}")
        if not bool(diagnostics["star_fits_fixture_hole"]):
            raise ValueError(f"Star and fixture geometry is invalid: {diagnostics}")

        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        spawn_ground_plane(prim_path="/World/ground", cfg=GroundPlaneCfg())

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table

        stage = omni.usd.get_context().get_stage()
        UsdGeom.Xform.Define(stage, "/World/Looks")
        star_mat = material(stage, "/World/Looks/star_yellow", (0.95, 0.70, 0.16), roughness=0.55)
        collision_mat = material(stage, "/World/Looks/star_collision_hidden", (0.95, 0.70, 0.16), roughness=0.55)
        fixture_mat = material(stage, "/World/Looks/fixture_graphite", (0.16, 0.18, 0.19), roughness=0.47)

        geometry_cfg = self._geometry_cfg()
        star_center = self._nominal_star_center()
        fixture_center = self._nominal_fixture_center()
        for env_id in range(self.scene.cfg.num_envs):
            root = f"/World/envs/env_{env_id}/StarKitting"
            UsdGeom.Xform.Define(stage, root)
            create_star_object(
                stage,
                root_path=f"{root}/StarObject",
                center=star_center,
                yaw_deg=float(self.cfg.star_start_yaw_deg),
                cfg=geometry_cfg,
                visual_mat=star_mat,
                collision_mat=collision_mat,
            )
            create_fixture(
                stage,
                root_path=f"{root}/Fixture",
                center=fixture_center,
                yaw_deg=float(self.cfg.fixture_yaw_deg),
                cfg=geometry_cfg,
                mat=fixture_mat,
            )

        self._star = RigidObject(RigidObjectCfg(prim_path="/World/envs/env_.*/StarKitting/StarObject", spawn=None))
        self.scene.rigid_objects["star"] = self._star

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)

    def _nominal_star_center(self) -> tuple[float, float, float]:
        return (
            float(self.cfg.pickup_x),
            float(self.cfg.pickup_y),
            float(self.cfg.table_surface_z + 0.5 * self.cfg.star_thickness + 0.002),
        )

    def _nominal_fixture_center(self) -> tuple[float, float, float]:
        return (
            float(self.cfg.fixture_x),
            float(self.cfg.fixture_y),
            float(self.cfg.table_surface_z + 0.5 * self.cfg.fixture_thickness),
        )

    def _goal_center_z(self) -> float:
        return float(self.cfg.table_surface_z + 0.5 * self.cfg.star_thickness + 0.002)

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = actions.clone().clamp(-1.0, 1.0)
        ee_pos_b, ee_quat_b = self._compute_ee_frame_pose()
        ik_command = self.actions[:, :6] * self.action_scale
        self.ik_controller.set_command(ik_command, ee_pos_b, ee_quat_b)

        # Raw gripper action: -1 closes, +1 opens.
        target_width = 0.5 * (self.actions[:, 6] + 1.0) * float(self.cfg.max_gripper_width)
        target_per_finger = torch.clamp(0.5 * target_width, min=0.0, max=0.04)
        self.finger_joint_pos_target[:, 0] = target_per_finger
        self.finger_joint_pos_target[:, 1] = target_per_finger

    def _apply_action(self) -> None:
        ee_pos_b, ee_quat_b = self._compute_ee_frame_pose()
        joint_pos = self._robot.data.joint_pos[:, self.arm_joint_ids]
        jacobian = self._compute_ee_frame_jacobian()
        arm_target = self.ik_controller.compute(ee_pos_b, ee_quat_b, jacobian, joint_pos)
        arm_lower = self.robot_dof_lower_limits[self.arm_joint_ids]
        arm_upper = self.robot_dof_upper_limits[self.arm_joint_ids]
        self.arm_joint_pos_target[:] = torch.clamp(arm_target, arm_lower, arm_upper)
        self._robot.set_joint_position_target(self.arm_joint_pos_target, joint_ids=self.arm_joint_ids)
        self._robot.set_joint_position_target(self.finger_joint_pos_target, joint_ids=self.finger_joint_ids)

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        self._compute_intermediate_values()
        lower_x = self.cfg.pickup_x - 0.5 * self.cfg.table_size_x - self.cfg.out_of_bounds_margin
        upper_x = self.cfg.pickup_x + 0.5 * self.cfg.table_size_x + self.cfg.out_of_bounds_margin
        lower_y = -0.5 * self.cfg.table_size_y - self.cfg.out_of_bounds_margin
        upper_y = 0.5 * self.cfg.table_size_y + self.cfg.out_of_bounds_margin
        star_out = (
            (self.star_pos[:, 0] < lower_x)
            | (self.star_pos[:, 0] > upper_x)
            | (self.star_pos[:, 1] < lower_y)
            | (self.star_pos[:, 1] > upper_y)
            | (self.star_pos[:, 2] < self.cfg.table_surface_z - 0.08)
        )
        success_done = (
            (self.time_in_success_region >= self.cfg.success_timeout)
            & (self.episode_length_buf >= int(self.cfg.min_episode_steps_before_success))
        )
        terminated = star_out | success_done
        truncated = self.episode_length_buf >= self.max_episode_length - 1
        return terminated, truncated

    def _get_rewards(self) -> torch.Tensor:
        self._compute_intermediate_values(update_success_timer=True)
        (
            approach_reward,
            finger_approach_reward,
            grasp_pose_reward,
            both_fingers_near_reward,
            lift_ready_reward,
            grasp_reward,
            closed_grasp_reward,
            lift_reward,
            close_near_reward,
            close_action_reward,
            descend_action_reward,
            lift_action_reward,
            transport_reward,
            yaw_reward,
            placement_reward,
            success_bonus,
            prelift_move_penalty,
            close_far_penalty,
            open_near_penalty,
            ungrasped_lift_penalty,
            action_penalty,
        ) = compute_franka_star_kitting_rewards(
            self.ee_to_star_dist,
            self.finger_center_to_star_dist,
            self.left_finger_to_star_dist,
            self.right_finger_to_star_dist,
            self.gripper_width,
            self.star_lift_height,
            self.star_initial_xy_error,
            self.goal_xy_error,
            self.goal_height_error,
            self.goal_yaw_error,
            self.has_lifted_star,
            self.in_success_region,
            self.actions,
            float(self.cfg.target_lift_height),
            float(self.cfg.max_gripper_width),
            float(self.cfg.approach_weight),
            float(self.cfg.approach_sharpness),
            float(self.cfg.finger_approach_weight),
            float(self.cfg.finger_approach_sharpness),
            float(self.cfg.grasp_pose_weight),
            float(self.cfg.both_fingers_near_weight),
            float(self.cfg.lift_ready_weight),
            float(self.cfg.grasp_weight),
            float(self.cfg.closed_grasp_weight),
            float(self.cfg.grasp_sharpness),
            float(self.cfg.lift_weight),
            float(self.cfg.descend_action_weight),
            float(self.cfg.lift_action_weight),
            float(self.cfg.close_near_weight),
            float(self.cfg.close_action_weight),
            float(self.cfg.prelift_move_penalty_weight),
            float(self.cfg.close_far_penalty_weight),
            float(self.cfg.open_near_penalty_weight),
            float(self.cfg.ungrasped_lift_penalty_weight),
            float(self.cfg.transport_weight),
            float(self.cfg.transport_xy_sharpness),
            float(self.cfg.yaw_weight),
            float(self.cfg.yaw_sharpness),
            float(self.cfg.placement_weight),
            float(self.cfg.placement_height_sharpness),
            float(self.cfg.success_bonus_weight),
            float(self.cfg.action_penalty_weight),
        )
        total_reward = (
            approach_reward
            + finger_approach_reward
            + grasp_pose_reward
            + both_fingers_near_reward
            + lift_ready_reward
            + grasp_reward
            + closed_grasp_reward
            + lift_reward
            + close_near_reward
            + close_action_reward
            + descend_action_reward
            + lift_action_reward
            + transport_reward
            + yaw_reward
            + placement_reward
            + success_bonus
            + prelift_move_penalty
            + close_far_penalty
            + open_near_penalty
            + ungrasped_lift_penalty
            + action_penalty
        )
        log_terms = {
            "star_approach_reward": approach_reward.mean(),
            "star_finger_approach_reward": finger_approach_reward.mean(),
            "star_grasp_pose_reward": grasp_pose_reward.mean(),
            "star_both_fingers_near_reward": both_fingers_near_reward.mean(),
            "star_lift_ready_reward": lift_ready_reward.mean(),
            "star_grasp_reward": grasp_reward.mean(),
            "star_closed_grasp_reward": closed_grasp_reward.mean(),
            "star_lift_reward": lift_reward.mean(),
            "star_close_near_reward": close_near_reward.mean(),
            "star_close_action_reward": close_action_reward.mean(),
            "star_descend_action_reward": descend_action_reward.mean(),
            "star_lift_action_reward": lift_action_reward.mean(),
            "star_transport_reward": transport_reward.mean(),
            "star_yaw_reward": yaw_reward.mean(),
            "star_placement_reward": placement_reward.mean(),
            "star_success_bonus": success_bonus.mean(),
            "star_prelift_move_penalty": prelift_move_penalty.mean(),
            "star_close_far_penalty": close_far_penalty.mean(),
            "star_open_near_penalty": open_near_penalty.mean(),
            "star_ungrasped_lift_penalty": ungrasped_lift_penalty.mean(),
            "star_action_penalty": action_penalty.mean(),
            "star_lift_height": self.star_lift_height.mean(),
            "star_initial_xy_error": self.star_initial_xy_error.mean(),
            "star_goal_xy_error": self.goal_xy_error.mean(),
            "star_goal_height_error": self.goal_height_error.mean(),
            "star_goal_yaw_error": self.goal_yaw_error.mean(),
            "star_success_rate": self.in_success_region.float().mean(),
            "star_has_lifted_rate": self.has_lifted_star.float().mean(),
            "star_gripper_width": self.gripper_width.mean(),
            "star_ee_to_star_dist": self.ee_to_star_dist.mean(),
            "star_finger_center_to_star_dist": self.finger_center_to_star_dist.mean(),
            "star_left_finger_to_star_dist": self.left_finger_to_star_dist.mean(),
            "star_right_finger_to_star_dist": self.right_finger_to_star_dist.mean(),
            "star_max_finger_to_star_dist": self.max_finger_to_star_dist.mean(),
            "star_finger_distance_asymmetry": self.finger_distance_asymmetry.mean(),
            "star_action_z": self.actions[:, 2].mean(),
            "star_action_up": torch.clamp(self.actions[:, 2], 0.0, 1.0).mean(),
            "star_action_down": torch.clamp(-self.actions[:, 2], 0.0, 1.0).mean(),
            "star_gripper_action": self.actions[:, 6].mean(),
            "star_gripper_close_action": torch.clamp(-self.actions[:, 6], 0.0, 1.0).mean(),
        }
        self.extras["log"] = log_terms
        for key, value in log_terms.items():
            self.extras[key] = value
        self.extras["in_success_region"] = self.in_success_region.float().mean()
        return total_reward

    def _reset_idx(self, env_ids: Sequence[int] | None):
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super()._reset_idx(env_ids)

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
        self._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
        self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        self.robot_dof_targets[env_ids] = joint_pos
        self.arm_joint_pos_target[env_ids] = joint_pos[:, self.arm_joint_ids]
        self.finger_joint_pos_target[env_ids] = joint_pos[:, self.finger_joint_ids]

        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.pickup_x)
        spawn_xy[:, 1] = float(self.cfg.pickup_y)
        spawn_xy += float(self.cfg.star_spawn_xy_randomization) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        near_hand_probability = float(self.cfg.star_reset_near_hand_probability)
        if near_hand_probability > 0.0:
            near_hand_mask = torch.rand(num_ids, device=self.device) < min(max(near_hand_probability, 0.0), 1.0)
            near_hand_count = int(near_hand_mask.sum().item())
            if near_hand_count > 0:
                near_hand_xy = torch.zeros(near_hand_count, 2, device=self.device)
                near_hand_xy[:, 0] = float(self.cfg.star_reset_near_hand_x) + float(
                    self.cfg.star_reset_near_hand_x_offset
                )
                near_hand_xy[:, 1] = float(self.cfg.star_reset_near_hand_y) + float(
                    self.cfg.star_reset_near_hand_y_offset
                )
                near_hand_noise = float(self.cfg.star_reset_near_hand_xy_noise)
                if near_hand_noise > 0.0:
                    near_hand_xy += near_hand_noise * (
                        2.0 * torch.rand(near_hand_count, 2, device=self.device) - 1.0
                    )
                min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x + self.cfg.star_outer_radius)
                max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x - self.cfg.star_outer_radius)
                min_y = float(-0.5 * self.cfg.table_size_y + self.cfg.star_outer_radius)
                max_y = float(0.5 * self.cfg.table_size_y - self.cfg.star_outer_radius)
                near_hand_xy[:, 0] = torch.clamp(near_hand_xy[:, 0], min=min_x, max=max_x)
                near_hand_xy[:, 1] = torch.clamp(near_hand_xy[:, 1], min=min_y, max=max_y)
                spawn_xy[near_hand_mask] = near_hand_xy
        yaw_base = math.radians(float(self.cfg.star_start_yaw_deg))
        yaw_noise = math.radians(float(self.cfg.star_spawn_yaw_randomization_deg)) * (
            2.0 * torch.rand(num_ids, device=self.device) - 1.0
        )
        yaw = yaw_base + yaw_noise
        star_pos = torch.zeros(num_ids, 3, device=self.device)
        star_pos[:, 0:2] = spawn_xy
        star_pos[:, 2] = self._goal_center_z()
        star_quat = _yaw_quat_wxyz(yaw)

        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = star_pos + self.scene.env_origins[env_ids]
        object_state[:, 3:7] = star_quat
        self._star.write_root_state_to_sim(object_state, env_ids=env_ids)

        self.star_initial_pos[env_ids] = star_pos
        self.star_goal_pos[env_ids, 0] = float(self.cfg.fixture_x)
        self.star_goal_pos[env_ids, 1] = float(self.cfg.fixture_y)
        self.star_goal_pos[env_ids, 2] = self._goal_center_z()
        self.star_goal_yaw[env_ids] = math.radians(float(self.cfg.fixture_yaw_deg))
        self.has_lifted_star[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
        self.actions[env_ids] = 0.0
        self.ik_controller.reset(env_ids)

        self._compute_intermediate_values(env_ids)

    def _get_observations(self) -> dict[str, torch.Tensor]:
        self._compute_intermediate_values()
        joint_pos_scaled = (
            2.0
            * (self._robot.data.joint_pos - self.robot_dof_lower_limits)
            / (self.robot_dof_upper_limits - self.robot_dof_lower_limits)
            - 1.0
        )
        joint_vel_scaled = 0.12 * self._robot.data.joint_vel
        yaw_error = _wrap_to_pi(self.star_goal_yaw - self.star_yaw)
        obs = torch.cat(
            (
                joint_pos_scaled,
                joint_vel_scaled,
                self.ee_pos,
                self.ee_quat,
                self.left_finger_pos - self.star_pos,
                self.right_finger_pos - self.star_pos,
                self.star_pos,
                self.star_quat,
                self.star_vel,
                self.star_goal_pos,
                torch.sin(self.star_goal_yaw).unsqueeze(-1),
                torch.cos(self.star_goal_yaw).unsqueeze(-1),
                self.star_pos - self.ee_pos,
                self.star_goal_pos - self.star_pos,
                torch.sin(yaw_error).unsqueeze(-1),
                torch.cos(yaw_error).unsqueeze(-1),
                self.has_lifted_star.float().unsqueeze(-1),
                self.in_success_region.float().unsqueeze(-1),
                self.time_in_success_region.unsqueeze(-1),
                self.gripper_width.unsqueeze(-1),
                self.actions,
            ),
            dim=-1,
        )
        obs = torch.clamp(obs, -5.0, 5.0)
        return {"policy": obs, "critic": obs}

    def _compute_intermediate_values(
        self,
        env_ids: torch.Tensor | None = None,
        *,
        update_success_timer: bool = False,
    ) -> None:
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        hand_pos_w = self._robot.data.body_pos_w[env_ids, self.ee_body_idx]
        hand_quat_w = self._robot.data.body_quat_w[env_ids, self.ee_body_idx]
        root_pos_w = self._robot.data.root_pos_w[env_ids]
        root_quat_w = self._robot.data.root_quat_w[env_ids]
        ee_pos_b, ee_quat_b = math_utils.subtract_frame_transforms(root_pos_w, root_quat_w, hand_pos_w, hand_quat_w)
        ee_pos_b, ee_quat_b = math_utils.combine_frame_transforms(
            ee_pos_b,
            ee_quat_b,
            self.ee_offset_pos[env_ids],
            self.ee_offset_rot[env_ids],
        )
        ee_pos_w, ee_quat_w = math_utils.combine_frame_transforms(root_pos_w, root_quat_w, ee_pos_b, ee_quat_b)

        env_origins = self.scene.env_origins[env_ids]
        if not hasattr(self, "ee_pos"):
            self.ee_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.ee_quat = torch.zeros(self.num_envs, 4, device=self.device)
            self.left_finger_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.right_finger_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.star_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.star_quat = torch.zeros(self.num_envs, 4, device=self.device)
            self.star_vel = torch.zeros(self.num_envs, 6, device=self.device)
            self.star_yaw = torch.zeros(self.num_envs, device=self.device)

        self.ee_pos[env_ids] = ee_pos_w - env_origins
        self.ee_quat[env_ids] = ee_quat_w
        self.left_finger_pos[env_ids] = self._robot.data.body_pos_w[env_ids, self.left_finger_body_idx] - env_origins
        self.right_finger_pos[env_ids] = self._robot.data.body_pos_w[env_ids, self.right_finger_body_idx] - env_origins
        self.star_pos[env_ids] = self._star.data.root_pos_w[env_ids] - env_origins
        self.star_quat[env_ids] = self._star.data.root_quat_w[env_ids]
        self.star_vel[env_ids] = self._star.data.root_vel_w[env_ids]
        self.star_yaw[env_ids] = _yaw_from_quat_wxyz(self.star_quat[env_ids])

        finger_center = 0.5 * (self.left_finger_pos[env_ids] + self.right_finger_pos[env_ids])
        self.gripper_width[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - self.right_finger_pos[env_ids], dim=-1
        )
        self.ee_to_star_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - self.star_pos[env_ids], dim=-1)
        self.finger_center_to_star_dist[env_ids] = torch.norm(finger_center - self.star_pos[env_ids], dim=-1)
        self.left_finger_to_star_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - self.star_pos[env_ids], dim=-1
        )
        self.right_finger_to_star_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - self.star_pos[env_ids], dim=-1
        )
        self.max_finger_to_star_dist[env_ids] = torch.maximum(
            self.left_finger_to_star_dist[env_ids], self.right_finger_to_star_dist[env_ids]
        )
        self.finger_distance_asymmetry[env_ids] = torch.abs(
            self.left_finger_to_star_dist[env_ids] - self.right_finger_to_star_dist[env_ids]
        )
        self.star_lift_height[env_ids] = torch.clamp(
            self.star_pos[env_ids, 2] - self.star_initial_pos[env_ids, 2], min=0.0
        )
        self.star_initial_xy_error[env_ids] = torch.norm(
            self.star_pos[env_ids, :2] - self.star_initial_pos[env_ids, :2], dim=-1
        )
        self.has_lifted_star[env_ids] |= self.star_lift_height[env_ids] >= float(self.cfg.lifted_success_height)
        self.goal_xy_error[env_ids] = torch.norm(
            self.star_pos[env_ids, :2] - self.star_goal_pos[env_ids, :2], dim=-1
        )
        self.goal_height_error[env_ids] = torch.abs(self.star_pos[env_ids, 2] - self.star_goal_pos[env_ids, 2])
        self.goal_yaw_error[env_ids] = torch.abs(_wrap_to_pi(self.star_goal_yaw[env_ids] - self.star_yaw[env_ids]))

        success = (
            self.has_lifted_star[env_ids]
            & (self.goal_xy_error[env_ids] <= float(self.cfg.placement_xy_tol))
            & (self.goal_height_error[env_ids] <= float(self.cfg.placement_height_tol))
            & (self.goal_yaw_error[env_ids] <= float(self.cfg.placement_yaw_tol))
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

    def _compute_ee_frame_pose(self) -> tuple[torch.Tensor, torch.Tensor]:
        hand_pos_w = self._robot.data.body_pos_w[:, self.ee_body_idx]
        hand_quat_w = self._robot.data.body_quat_w[:, self.ee_body_idx]
        root_pos_w = self._robot.data.root_pos_w
        root_quat_w = self._robot.data.root_quat_w
        ee_pos_b, ee_quat_b = math_utils.subtract_frame_transforms(root_pos_w, root_quat_w, hand_pos_w, hand_quat_w)
        return math_utils.combine_frame_transforms(ee_pos_b, ee_quat_b, self.ee_offset_pos, self.ee_offset_rot)

    def _compute_ee_frame_jacobian(self) -> torch.Tensor:
        jacobian = self._robot.root_physx_view.get_jacobians()[:, self.ee_jacobi_idx, :, self.arm_joint_ids]
        base_rot = self._robot.data.root_quat_w
        base_rot_matrix = math_utils.matrix_from_quat(math_utils.quat_inv(base_rot))
        jacobian[:, :3, :] = torch.bmm(base_rot_matrix, jacobian[:, :3, :])
        jacobian[:, 3:, :] = torch.bmm(base_rot_matrix, jacobian[:, 3:, :])
        jacobian[:, 0:3, :] += torch.bmm(-math_utils.skew_symmetric_matrix(self.ee_offset_pos), jacobian[:, 3:, :])
        return jacobian

    def get_current_observations(self):
        return self._get_observations()
