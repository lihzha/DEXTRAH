"""DirectRLEnv for one single-arm YAM robot on the shared multi-object grasp task."""

from __future__ import annotations

from collections.abc import Sequence
import math
from pathlib import Path

import torch

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import Articulation, RigidObject
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.envs import DirectRLEnv
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from dextrah_lab.assets.yam.bimanual_yam import SINGLE_YAM_USD_PATH
from dextrah_lab.tasks.dextrah_multi_object_grasp.multi_object_grasp_task import MultiObjectGraspTaskMixin

from .single_yam_multi_object_grasp_env_cfg import DextrahSingleYAMMultiObjectGraspEnvCfg


class DextrahSingleYAMMultiObjectGraspEnv(MultiObjectGraspTaskMixin, DirectRLEnv):
    """YAM task: pick up one GraspGen object with one single-arm YAM articulation."""

    cfg: DextrahSingleYAMMultiObjectGraspEnvCfg

    def __init__(self, cfg: DextrahSingleYAMMultiObjectGraspEnvCfg, render_mode: str | None = None, **kwargs):
        if not Path(SINGLE_YAM_USD_PATH).is_file():
            raise FileNotFoundError(
                "Single-arm YAM USD is missing. Prepare assets with "
                "`/isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py "
                "--headless --converter mjcf --robot single`. "
                f"Expected: {SINGLE_YAM_USD_PATH}"
            )
        super().__init__(cfg, render_mode, **kwargs)

        self.dt = self.cfg.sim.dt * self.cfg.decimation
        self.robot_dof_lower_limits = self._robot.data.soft_joint_pos_limits[0, :, 0].to(self.device)
        self.robot_dof_upper_limits = self._robot.data.soft_joint_pos_limits[0, :, 1].to(self.device)
        self._sanitize_joint_limits()

        self.arm_joint_ids, self.arm_joint_names = self._find_joints("joint[1-6]", "arm")
        self.finger_joint_ids, self.finger_joint_names = self._find_joints("(left|right)_finger", "gripper")
        self.tcp_body_idx = self._find_one_body("link_6")
        self.finger_body_ids = (
            self._find_one_body("link_left_finger"),
            self._find_one_body("link_right_finger"),
        )
        self.tcp_jacobi_idx = self.tcp_body_idx - 1 if self._robot.is_fixed_base else self.tcp_body_idx

        ik_cfg = DifferentialIKControllerCfg(command_type="pose", use_relative_mode=True, ik_method="dls")
        self.ik_controller = DifferentialIKController(ik_cfg, num_envs=self.num_envs, device=self.device)
        self.tcp_offset_pos = torch.tensor(self.cfg.tcp_offset_pos, device=self.device).repeat(self.num_envs, 1)
        self.tcp_offset_rot = torch.tensor((1.0, 0.0, 0.0, 0.0), device=self.device).repeat(self.num_envs, 1)
        self.action_scale = torch.tensor(
            tuple(self.cfg.ik_position_action_scale) + tuple(self.cfg.ik_rotation_action_scale),
            device=self.device,
        )

        self.actions = torch.zeros(self.num_envs, self.cfg.action_space, device=self.device)
        self.arm_joint_pos_target = self._robot.data.default_joint_pos[:, self.arm_joint_ids].clone()
        self.finger_joint_pos_target = self._robot.data.default_joint_pos[:, self.finger_joint_ids].clone()
        self.robot_dof_targets = self._robot.data.default_joint_pos.clone()

        self._ensure_buffers()

    def _setup_scene(self):
        self._setup_multi_object_task()
        self._setup_tabletop_clutter_task()

        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        spawn_ground_plane(
            prim_path="/World/ground",
            cfg=GroundPlaneCfg(size=tuple(self.cfg.ground_plane_size), color=self.cfg.ground_plane_color),
            translation=(0.0, 0.0, float(self.cfg.ground_plane_z)),
        )

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table
        self._spawn_multi_object_assets()
        self._spawn_tabletop_clutter_assets()
        self._spawn_tabletop_source_bin()
        self._spawn_tabletop_goal_bin()

        light_cfg = sim_utils.DomeLightCfg(
            intensity=float(self.cfg.dome_light_intensity),
            exposure=float(self.cfg.dome_light_exposure),
            color=tuple(float(v) for v in self.cfg.dome_light_color),
        )
        light_cfg.func("/World/Light", light_cfg)
        if bool(getattr(self.cfg, "key_light_enabled", False)):
            key_light_cfg = sim_utils.DistantLightCfg(
                intensity=float(self.cfg.key_light_intensity),
                exposure=float(self.cfg.key_light_exposure),
                color=tuple(float(v) for v in self.cfg.key_light_color),
                angle=float(self.cfg.key_light_angle),
            )
            key_light_rotation = torch.tensor(
                [[math.radians(float(v)) for v in self.cfg.key_light_rotation_deg]],
                dtype=torch.float32,
            )
            key_light_quat = math_utils.quat_from_euler_xyz(
                key_light_rotation[:, 0],
                key_light_rotation[:, 1],
                key_light_rotation[:, 2],
            )[0]
            key_light_cfg.func("/World/KeyLight", key_light_cfg, orientation=tuple(float(v) for v in key_light_quat))

    def _sanitize_joint_limits(self) -> None:
        default_pos = self._robot.data.default_joint_pos[0]
        finite_lower = torch.isfinite(self.robot_dof_lower_limits)
        finite_upper = torch.isfinite(self.robot_dof_upper_limits)
        invalid = (~finite_lower) | (~finite_upper) | (self.robot_dof_upper_limits <= self.robot_dof_lower_limits)
        if bool(invalid.any().item()):
            self.robot_dof_lower_limits = torch.where(invalid, default_pos - 2.0, self.robot_dof_lower_limits)
            self.robot_dof_upper_limits = torch.where(invalid, default_pos + 2.0, self.robot_dof_upper_limits)

    def _find_joints(self, pattern: str, label: str) -> tuple[list[int], list[str]]:
        ids, names = self._robot.find_joints(pattern)
        if len(ids) == 0:
            raise ValueError(f"Could not find {label} joints with pattern {pattern!r}")
        return list(ids), list(names)

    def _find_one_body(self, name: str) -> int:
        ids, names = self._robot.find_bodies(name)
        if len(ids) != 1:
            raise ValueError(f"Expected exactly one body named {name!r}, got {names}")
        return int(ids[0])

    def _ensure_buffers(self) -> None:
        self.cube_initial_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_goal_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_lift_height = torch.zeros(self.num_envs, device=self.device)
        self.cube_xy_error = torch.zeros(self.num_envs, device=self.device)
        self.cube_goal_height_error = torch.zeros(self.num_envs, device=self.device)
        self.has_lifted_cube = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.in_success_region = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.time_in_success_region = torch.zeros(self.num_envs, device=self.device)

        self.tcp_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.tcp_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.hold_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.cube_vel = torch.zeros(self.num_envs, 6, device=self.device)
        self.cube_linear_speed = torch.zeros(self.num_envs, device=self.device)
        self.cube_angular_speed = torch.zeros(self.num_envs, device=self.device)
        self.cube_velocity_success_stable = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.cube_speed_done = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.last_cube_speed_done = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

        self.gripper_width = torch.zeros(self.num_envs, device=self.device)
        self.hold_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.grasp_success = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.finger_table_clearance = torch.zeros(self.num_envs, device=self.device)
        self.finger_table_clearance_violation = torch.zeros(self.num_envs, device=self.device)

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
            self.arm_joint_pos_target[env_ids] = joint_pos[:, self.arm_joint_ids]
            self.finger_joint_pos_target[env_ids] = joint_pos[:, self.finger_joint_ids]
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = actions.clone().clamp(-1.0, 1.0)
        tcp_pos_b, tcp_quat_b = self._compute_tcp_frame_pose()
        self.ik_controller.set_command(self.actions[:, :6] * self.action_scale, tcp_pos_b, tcp_quat_b)
        self.finger_joint_pos_target[:] = self._gripper_targets_from_action(self.actions[:, 6])

    def _apply_action(self) -> None:
        tcp_pos_b, tcp_quat_b = self._compute_tcp_frame_pose()
        joint_pos = self._robot.data.joint_pos[:, self.arm_joint_ids]
        jacobian = self._compute_tcp_frame_jacobian()
        arm_target = self.ik_controller.compute(tcp_pos_b, tcp_quat_b, jacobian, joint_pos)
        lower = self.robot_dof_lower_limits[self.arm_joint_ids]
        upper = self.robot_dof_upper_limits[self.arm_joint_ids]
        self.arm_joint_pos_target[:] = torch.clamp(arm_target, lower, upper)

        self._robot.set_joint_position_target(self.arm_joint_pos_target, joint_ids=self.arm_joint_ids)
        self._robot.set_joint_position_target(self.finger_joint_pos_target, joint_ids=self.finger_joint_ids)

    def _gripper_targets_from_action(self, gripper_action: torch.Tensor) -> torch.Tensor:
        open_pos = float(self.cfg.gripper_open_joint_pos)
        closed_pos = float(self.cfg.gripper_closed_joint_pos)
        alpha = 0.5 * (gripper_action + 1.0)
        target = closed_pos + alpha * (open_pos - closed_pos)
        return target.unsqueeze(-1).repeat(1, 2)

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        self._compute_intermediate_values()
        lower_x = self.cfg.table_center_x - 0.5 * self.cfg.table_size_x - self.cfg.out_of_bounds_margin
        upper_x = self.cfg.table_center_x + 0.5 * self.cfg.table_size_x + self.cfg.out_of_bounds_margin
        lower_y = self.cfg.table_center_y - 0.5 * self.cfg.table_size_y - self.cfg.out_of_bounds_margin
        upper_y = self.cfg.table_center_y + 0.5 * self.cfg.table_size_y + self.cfg.out_of_bounds_margin
        cube_out = (
            (self.cube_pos[:, 0] < lower_x)
            | (self.cube_pos[:, 0] > upper_x)
            | (self.cube_pos[:, 1] < lower_y)
            | (self.cube_pos[:, 1] > upper_y)
            | (self.cube_pos[:, 2] < self.cfg.table_surface_z - 0.08)
            | (self.cube_pos[:, 2] > float(self.cfg.cube_out_max_z))
        )
        success_done = (
            (self.time_in_success_region >= self.cfg.success_timeout)
            & (self.episode_length_buf >= int(self.cfg.min_episode_steps_before_success))
        )
        prelift_drag_done = (
            (~self.has_lifted_cube)
            & (self.cube_xy_error >= float(self.cfg.prelift_drag_termination_xy_error))
            & (self.episode_length_buf > 2)
        )
        cube_speed_done = (
            (
                (self.cube_linear_speed > float(self.cfg.cube_speed_termination_linear))
                | (self.cube_angular_speed > float(self.cfg.cube_speed_termination_angular))
            )
            & (self.episode_length_buf > 2)
        )
        self.cube_speed_done[:] = cube_speed_done
        self.last_cube_speed_done[:] = cube_speed_done
        finger_table_penetration_done = (
            (self.finger_table_clearance < float(self.cfg.finger_table_penetration_termination_margin))
            & (self.episode_length_buf > 2)
        )
        terminated = cube_out | success_done | prelift_drag_done | cube_speed_done | finger_table_penetration_done
        truncated = self.episode_length_buf >= self.max_episode_length - 1
        return terminated, truncated

    def _get_rewards(self) -> torch.Tensor:
        self._compute_intermediate_values(update_success_timer=True)
        approach_reward = float(self.cfg.cube_approach_weight) * torch.exp(
            -float(self.cfg.cube_approach_sharpness) * self.hold_to_cube_dist
        )
        lift_reward = float(self.cfg.cube_lift_weight) * torch.clamp(
            self.cube_lift_height / max(float(self.cfg.cube_lift_height), 1.0e-6),
            0.0,
            1.0,
        )
        height_tracking_reward = float(self.cfg.cube_height_tracking_weight) * torch.exp(
            -float(self.cfg.cube_height_tracking_sharpness) * self.cube_goal_height_error
        )
        xy_stability_reward = float(self.cfg.cube_xy_stability_weight) * torch.exp(
            -float(self.cfg.cube_xy_stability_sharpness) * self.cube_xy_error
        )
        success_bonus = float(self.cfg.cube_success_bonus_weight) * self.in_success_region.float()
        close_action = 0.5 * (1.0 - self.actions[:, 6])
        close_action_reward = float(self.cfg.cube_close_action_weight) * close_action
        lift_action_reward = float(self.cfg.cube_lift_action_weight) * torch.clamp(self.actions[:, 2], min=0.0)
        descend_action_penalty = float(self.cfg.cube_descend_action_penalty_weight) * torch.clamp(
            -self.actions[:, 2],
            min=0.0,
        )
        clearance_margin = max(float(self.cfg.finger_table_clearance_margin), 1.0e-6)
        table_clearance_penalty = float(self.cfg.cube_table_clearance_penalty_weight) * torch.clamp(
            (float(self.cfg.finger_table_clearance_margin) - self.finger_table_clearance) / clearance_margin,
            0.0,
            1.0,
        )
        gripper_close_reg = float(self.cfg.cube_gripper_close_reg_weight) * close_action.square()
        action_penalty = float(self.cfg.cube_action_penalty_weight) * torch.sum(self.actions.square(), dim=-1)
        linear_speed_limit = max(float(self.cfg.cube_success_max_linear_speed), 1.0e-6)
        angular_speed_limit = max(float(self.cfg.cube_success_max_angular_speed), 1.0e-6)
        linear_speed_violation = torch.clamp((self.cube_linear_speed - linear_speed_limit) / linear_speed_limit, min=0.0)
        angular_speed_violation = torch.clamp(
            (self.cube_angular_speed - angular_speed_limit) / angular_speed_limit,
            min=0.0,
        )
        cube_velocity_penalty = float(self.cfg.cube_velocity_penalty_weight) * (
            linear_speed_violation.square() + angular_speed_violation.square()
        )
        total_reward = (
            approach_reward
            + lift_reward
            + height_tracking_reward
            + xy_stability_reward
            + success_bonus
            + close_action_reward
            + lift_action_reward
            + descend_action_penalty
            + table_clearance_penalty
            + gripper_close_reg
            + action_penalty
            + cube_velocity_penalty
        )
        log_terms = {
            "yam_single_approach_reward": approach_reward.mean(),
            "yam_single_lift_reward": lift_reward.mean(),
            "yam_single_height_tracking_reward": height_tracking_reward.mean(),
            "yam_single_xy_stability_reward": xy_stability_reward.mean(),
            "yam_single_success_bonus": success_bonus.mean(),
            "yam_single_close_action_reward": close_action_reward.mean(),
            "yam_single_lift_action_reward": lift_action_reward.mean(),
            "yam_single_descend_action_penalty": descend_action_penalty.mean(),
            "yam_single_table_clearance_penalty": table_clearance_penalty.mean(),
            "yam_single_gripper_close_reg": gripper_close_reg.mean(),
            "yam_single_action_penalty": action_penalty.mean(),
            "yam_single_velocity_penalty": cube_velocity_penalty.mean(),
            "yam_single_lift_height": self.cube_lift_height.mean(),
            "yam_single_xy_error": self.cube_xy_error.mean(),
            "yam_single_goal_height_error": self.cube_goal_height_error.mean(),
            "yam_single_success_rate": self.in_success_region.float().mean(),
            "yam_single_stable_success_rate": (
                self.time_in_success_region >= float(self.cfg.success_timeout)
            ).float().mean(),
            "yam_single_has_lifted_rate": self.has_lifted_cube.float().mean(),
            "yam_single_linear_speed": self.cube_linear_speed.mean(),
            "yam_single_angular_speed": self.cube_angular_speed.mean(),
            "yam_single_velocity_success_stable_rate": self.cube_velocity_success_stable.float().mean(),
            "yam_single_speed_done_rate": self.cube_speed_done.float().mean(),
            "yam_single_hold_to_cube_dist": self.hold_to_cube_dist.mean(),
            "yam_single_gripper_width": self.gripper_width.mean(),
            "yam_single_finger_table_clearance": self.finger_table_clearance.mean(),
            "yam_single_grasp_success_rate": self.grasp_success.float().mean(),
            "yam_single_action_z": self.actions[:, 2].mean(),
            "yam_single_gripper_action": self.actions[:, 6].mean(),
        }
        self._add_multi_object_log_terms(log_terms, distance_term=self.hold_to_cube_dist)
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
        self._sync_reset_joint_state(env_ids, joint_pos, joint_vel, update_buffers=True)

        object_radius_xy = self.object_xy_radius[env_ids]
        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.table_center_x) + float(self.cfg.object_spawn_center_offset_x)
        spawn_xy[:, 1] = float(self.cfg.table_center_y) + float(self.cfg.object_spawn_center_offset_y)
        spawn_randomization = max(float(self.cfg.object_spawn_xy_randomization), 0.0)
        spawn_x_randomization = getattr(self.cfg, "object_spawn_x_randomization", None)
        spawn_y_randomization = getattr(self.cfg, "object_spawn_y_randomization", None)
        spawn_ranges = torch.tensor(
            [
                spawn_randomization if spawn_x_randomization is None else max(float(spawn_x_randomization), 0.0),
                spawn_randomization if spawn_y_randomization is None else max(float(spawn_y_randomization), 0.0),
            ],
            dtype=torch.float32,
            device=self.device,
        )
        spawn_xy += (2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0) * spawn_ranges.unsqueeze(0)
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x) + object_radius_xy
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x) - object_radius_xy
        min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y) + object_radius_xy
        max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y) - object_radius_xy
        spawn_xy[:, 0] = torch.minimum(torch.maximum(spawn_xy[:, 0], min_x), max_x)
        spawn_xy[:, 1] = torch.minimum(torch.maximum(spawn_xy[:, 1], min_y), max_y)
        spawn_xy = self._move_xy_outside_tabletop_goal_bin(env_ids, spawn_xy, object_radius_xy)

        object_pos = torch.zeros(num_ids, 3, device=self.device)
        object_pos[:, 0:2] = spawn_xy
        object_quat, object_root_z_offset = self._sample_object_reset_pose(env_ids)
        object_pos[:, 2] = (
            float(self.cfg.table_surface_z)
            + object_root_z_offset
            + float(self.cfg.object_spawn_z_clearance)
        )
        fixed_root_position = getattr(self.cfg, "object_fixed_root_position", None)
        if fixed_root_position is not None:
            object_pos[:] = torch.as_tensor(
                tuple(float(v) for v in fixed_root_position),
                dtype=torch.float32,
                device=self.device,
            ).unsqueeze(0)
        fixed_root_quat = getattr(self.cfg, "object_fixed_root_quat_wxyz", None)
        if fixed_root_quat is not None:
            fixed_quat = torch.as_tensor(
                tuple(float(v) for v in fixed_root_quat),
                dtype=torch.float32,
                device=self.device,
            )
            fixed_quat = fixed_quat / torch.clamp(torch.norm(fixed_quat), min=1.0e-6)
            object_quat[:] = fixed_quat.unsqueeze(0)
        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = object_pos + self.scene.env_origins[env_ids]
        object_state[:, 3:7] = object_quat
        self._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
        self._set_object_asset_root_pose(env_ids, object_pos, object_quat)
        self._reset_tabletop_clutter(env_ids, target_root_pos=object_pos)
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

        object_pos, object_quat = self._settle_reset_objects(env_ids, joint_pos, joint_vel)
        object_center_pos = self._object_center_pos_from_root(env_ids, object_pos, object_quat)
        self.cube_initial_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids] = self._tabletop_goal_pos(env_ids, object_center_pos)
        self.has_lifted_cube[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
        self.cube_speed_done[env_ids] = False
        self.actions[env_ids] = 0.0
        self.ik_controller.reset(env_ids)

        self._compute_intermediate_values(env_ids)

    def _get_observations(self) -> dict[str, torch.Tensor]:
        self._compute_intermediate_values()
        joint_range = torch.clamp(self.robot_dof_upper_limits - self.robot_dof_lower_limits, min=1.0e-6)
        joint_pos_scaled = 2.0 * (self._robot.data.joint_pos - self.robot_dof_lower_limits) / joint_range - 1.0
        joint_vel_scaled = 0.12 * self._robot.data.joint_vel
        base_obs = torch.cat(
            (
                joint_pos_scaled,
                joint_vel_scaled,
                self.tcp_pos,
                self.tcp_quat,
                self.hold_pos - self.cube_pos,
                self.cube_pos,
                self.cube_quat,
                self.cube_vel,
                self.cube_goal_pos,
                self.cube_pos - self.hold_pos,
                self.cube_goal_pos - self.cube_pos,
                self.has_lifted_cube.float().unsqueeze(-1),
                self.in_success_region.float().unsqueeze(-1),
                self.time_in_success_region.unsqueeze(-1),
                self.gripper_width.unsqueeze(-1),
                self.hold_to_cube_dist.unsqueeze(-1),
                self.cube_lift_height.unsqueeze(-1),
                self.cube_xy_error.unsqueeze(-1),
                self.actions,
            ),
            dim=-1,
        )
        obs = torch.clamp(torch.cat((base_obs, self._multi_object_features()), dim=-1), -5.0, 5.0)
        return {"policy": obs, "critic": obs}

    def _compute_intermediate_values(
        self,
        env_ids: torch.Tensor | None = None,
        *,
        update_success_timer: bool = False,
    ) -> None:
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)

        env_origins = self.scene.env_origins[env_ids]
        root_pos_w = self._robot.data.root_pos_w[env_ids]
        root_quat_w = self._robot.data.root_quat_w[env_ids]

        tcp_pos_b, tcp_quat_b = self._compute_tcp_frame_pose(env_ids)
        tcp_pos_w, tcp_quat_w = math_utils.combine_frame_transforms(root_pos_w, root_quat_w, tcp_pos_b, tcp_quat_b)

        finger_a = self._robot.data.body_pos_w[env_ids, self.finger_body_ids[0]] - env_origins
        finger_b = self._robot.data.body_pos_w[env_ids, self.finger_body_ids[1]] - env_origins

        root_pos = self._cube.data.root_pos_w[env_ids] - env_origins
        root_quat = self._cube.data.root_quat_w[env_ids]
        center_pos = self._object_center_pos_from_root(env_ids, root_pos, root_quat)
        self.tcp_pos[env_ids] = tcp_pos_w - env_origins
        self.tcp_quat[env_ids] = tcp_quat_w
        self.hold_pos[env_ids] = 0.5 * (finger_a + finger_b)
        self.cube_pos[env_ids] = center_pos
        self.cube_quat[env_ids] = root_quat
        self.cube_vel[env_ids] = self._cube.data.root_vel_w[env_ids]
        self.cube_linear_speed[env_ids] = torch.norm(self.cube_vel[env_ids, :3], dim=-1)
        self.cube_angular_speed[env_ids] = torch.norm(self.cube_vel[env_ids, 3:], dim=-1)

        self.gripper_width[env_ids] = torch.norm(finger_a - finger_b, dim=-1)
        self.hold_to_cube_dist[env_ids] = torch.norm(self.hold_pos[env_ids] - center_pos, dim=-1)
        self.finger_table_clearance[env_ids] = torch.minimum(finger_a[:, 2], finger_b[:, 2]) - float(
            self.cfg.table_surface_z
        )
        clearance_margin = max(float(self.cfg.finger_table_clearance_margin), 1.0e-6)
        self.finger_table_clearance_violation[env_ids] = torch.clamp(
            (float(self.cfg.finger_table_clearance_margin) - self.finger_table_clearance[env_ids])
            / clearance_margin,
            0.0,
            1.0,
        )

        self.cube_lift_height[env_ids] = torch.clamp(
            center_pos[:, 2] - self.cube_initial_pos[env_ids, 2],
            min=0.0,
        )
        self.has_lifted_cube[env_ids] |= self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height)
        initial_xy_error = torch.norm(center_pos[:, :2] - self.cube_initial_pos[env_ids, :2], dim=-1)
        goal_xy_error = torch.norm(center_pos[:, :2] - self.cube_goal_pos[env_ids, :2], dim=-1)
        if bool(getattr(self.cfg, "tabletop_goal_bin_enabled", False)):
            self.cube_xy_error[env_ids] = torch.where(self.has_lifted_cube[env_ids], goal_xy_error, initial_xy_error)
        else:
            self.cube_xy_error[env_ids] = initial_xy_error
        self.cube_goal_height_error[env_ids] = torch.abs(self.cube_goal_pos[env_ids, 2] - center_pos[:, 2])
        self.grasp_success[env_ids] = self.hold_to_cube_dist[env_ids] <= float(self.cfg.cube_success_hand_dist)

        success = (
            (self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height))
            & (self.cube_xy_error[env_ids] <= float(self.cfg.cube_success_xy_tol))
            & self.grasp_success[env_ids]
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

    def _compute_tcp_frame_pose(self, env_ids: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        if env_ids is None:
            offset_pos = self.tcp_offset_pos
            hand_pos_w = self._robot.data.body_pos_w[:, self.tcp_body_idx]
            hand_quat_w = self._robot.data.body_quat_w[:, self.tcp_body_idx]
            root_pos_w = self._robot.data.root_pos_w
            root_quat_w = self._robot.data.root_quat_w
            offset_rot = self.tcp_offset_rot
        else:
            offset_pos = self.tcp_offset_pos[env_ids]
            hand_pos_w = self._robot.data.body_pos_w[env_ids, self.tcp_body_idx]
            hand_quat_w = self._robot.data.body_quat_w[env_ids, self.tcp_body_idx]
            root_pos_w = self._robot.data.root_pos_w[env_ids]
            root_quat_w = self._robot.data.root_quat_w[env_ids]
            offset_rot = self.tcp_offset_rot[env_ids]
        tcp_pos_b, tcp_quat_b = math_utils.subtract_frame_transforms(root_pos_w, root_quat_w, hand_pos_w, hand_quat_w)
        return math_utils.combine_frame_transforms(tcp_pos_b, tcp_quat_b, offset_pos, offset_rot)

    def _compute_tcp_frame_jacobian(self) -> torch.Tensor:
        jacobian = self._robot.root_physx_view.get_jacobians()[:, self.tcp_jacobi_idx, :, self.arm_joint_ids]
        base_rot = self._robot.data.root_quat_w
        base_rot_matrix = math_utils.matrix_from_quat(math_utils.quat_inv(base_rot))
        jacobian[:, :3, :] = torch.bmm(base_rot_matrix, jacobian[:, :3, :])
        jacobian[:, 3:, :] = torch.bmm(base_rot_matrix, jacobian[:, 3:, :])
        jacobian[:, 0:3, :] += torch.bmm(-math_utils.skew_symmetric_matrix(self.tcp_offset_pos), jacobian[:, 3:, :])
        return jacobian

    def compute_grasp_prior_reference_actions(self) -> torch.Tensor:
        return torch.zeros(self.num_envs, int(self.cfg.action_space), device=self.device)

    def get_current_observations(self):
        return self._get_observations()
