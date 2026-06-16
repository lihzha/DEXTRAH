"""DirectRLEnv for bimanual YAM single-cube grasp-and-lift."""

from __future__ import annotations

from collections.abc import Sequence
import math
import os
from pathlib import Path

import torch

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import Articulation, RigidObject
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.envs import DirectRLEnv
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from .bimanual_yam_cube_grasp_env_cfg import DextrahBimanualYAMCubeGraspEnvCfg, YAM_USD_PATH
from .bimanual_yam_cube_grasp_rewards import compute_bimanual_yam_cube_grasp_rewards


def _yaw_quat_wxyz(yaw_rad: torch.Tensor) -> torch.Tensor:
    quat = torch.zeros(yaw_rad.shape[0], 4, device=yaw_rad.device)
    quat[:, 0] = torch.cos(0.5 * yaw_rad)
    quat[:, 3] = torch.sin(0.5 * yaw_rad)
    return quat


def _sync_cube_spawn_cfg_from_scalars(cfg: DextrahBimanualYAMCubeGraspEnvCfg) -> None:
    """Apply scalar Hydra overrides to the nested cube spawner config."""

    for field_name, env_name in (
        ("cube_size", "CUBE_SIZE"),
        ("cube_density", "CUBE_DENSITY"),
        ("cube_static_friction", "CUBE_STATIC_FRICTION"),
        ("cube_dynamic_friction", "CUBE_DYNAMIC_FRICTION"),
    ):
        env_value = os.environ.get(env_name)
        if env_value:
            setattr(cfg, field_name, float(env_value))

    cube_size = float(cfg.cube_size)
    cfg.cube_spawn_z = float(cfg.table_surface_z) + 0.5 * cube_size + 0.005
    cfg.cube.spawn.size = (cube_size, cube_size, cube_size)
    cfg.cube.init_state.pos = (float(cfg.pickup_x), float(cfg.pickup_y), float(cfg.cube_spawn_z))
    cfg.cube.spawn.collision_props.contact_offset = float(cfg.cube_contact_offset)
    cfg.cube.spawn.collision_props.rest_offset = float(cfg.cube_rest_offset)
    cfg.cube.spawn.rigid_props.linear_damping = float(cfg.cube_linear_damping)
    cfg.cube.spawn.rigid_props.angular_damping = float(cfg.cube_angular_damping)
    cfg.cube.spawn.rigid_props.solver_position_iteration_count = int(cfg.cube_solver_position_iterations)
    cfg.cube.spawn.rigid_props.solver_velocity_iteration_count = int(cfg.cube_solver_velocity_iterations)
    cfg.cube.spawn.rigid_props.sleep_threshold = float(cfg.cube_sleep_threshold)
    cfg.cube.spawn.rigid_props.stabilization_threshold = float(cfg.cube_stabilization_threshold)
    cfg.cube.spawn.rigid_props.max_depenetration_velocity = float(cfg.cube_max_depenetration_velocity)
    cfg.cube.spawn.mass_props.density = float(cfg.cube_density)
    cfg.cube.spawn.physics_material.static_friction = float(cfg.cube_static_friction)
    cfg.cube.spawn.physics_material.dynamic_friction = float(cfg.cube_dynamic_friction)
    cfg.cube.spawn.physics_material.restitution = float(cfg.cube_restitution)


class DextrahBimanualYAMCubeGraspEnv(DirectRLEnv):
    """Bimanual YAM task: pick a cube with left and right arms and lift it."""

    cfg: DextrahBimanualYAMCubeGraspEnvCfg

    def __init__(self, cfg: DextrahBimanualYAMCubeGraspEnvCfg, render_mode: str | None = None, **kwargs):
        if not Path(YAM_USD_PATH).is_file():
            raise FileNotFoundError(
                "Bimanual YAM USD is missing. Prepare assets with "
                "`/isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless`. "
                f"Expected: {YAM_USD_PATH}"
            )
        _sync_cube_spawn_cfg_from_scalars(cfg)
        super().__init__(cfg, render_mode, **kwargs)

        self.dt = self.cfg.sim.dt * self.cfg.decimation
        self.robot_dof_lower_limits = self._robot.data.soft_joint_pos_limits[0, :, 0].to(self.device)
        self.robot_dof_upper_limits = self._robot.data.soft_joint_pos_limits[0, :, 1].to(self.device)
        self._sanitize_joint_limits()

        self.left_arm_joint_ids, self.left_arm_joint_names = self._find_joints("left_joint[1-6]", "left arm")
        self.right_arm_joint_ids, self.right_arm_joint_names = self._find_joints("right_joint[1-6]", "right arm")
        self.left_finger_joint_ids, self.left_finger_joint_names = self._find_joints(
            "left_(left|right)_finger", "left gripper"
        )
        self.right_finger_joint_ids, self.right_finger_joint_names = self._find_joints(
            "right_(left|right)_finger", "right gripper"
        )
        self.arm_joint_ids = self.left_arm_joint_ids + self.right_arm_joint_ids
        self.finger_joint_ids = self.left_finger_joint_ids + self.right_finger_joint_ids

        self.left_tcp_body_idx = self._find_one_body("left_link_6")
        self.right_tcp_body_idx = self._find_one_body("right_link_6")
        self.left_finger_body_ids = (
            self._find_one_body("left_link_left_finger"),
            self._find_one_body("left_link_right_finger"),
        )
        self.right_finger_body_ids = (
            self._find_one_body("right_link_left_finger"),
            self._find_one_body("right_link_right_finger"),
        )
        self.left_tcp_jacobi_idx = self.left_tcp_body_idx - 1 if self._robot.is_fixed_base else self.left_tcp_body_idx
        self.right_tcp_jacobi_idx = (
            self.right_tcp_body_idx - 1 if self._robot.is_fixed_base else self.right_tcp_body_idx
        )

        ik_cfg = DifferentialIKControllerCfg(command_type="pose", use_relative_mode=True, ik_method="dls")
        self.left_ik_controller = DifferentialIKController(ik_cfg, num_envs=self.num_envs, device=self.device)
        self.right_ik_controller = DifferentialIKController(ik_cfg, num_envs=self.num_envs, device=self.device)
        self.left_tcp_offset_pos = torch.tensor(self.cfg.left_tcp_offset_pos, device=self.device).repeat(
            self.num_envs, 1
        )
        self.right_tcp_offset_pos = torch.tensor(self.cfg.right_tcp_offset_pos, device=self.device).repeat(
            self.num_envs, 1
        )
        self.tcp_offset_rot = torch.tensor((1.0, 0.0, 0.0, 0.0), device=self.device).repeat(self.num_envs, 1)
        self.action_scale = torch.tensor(
            tuple(self.cfg.ik_position_action_scale) + tuple(self.cfg.ik_rotation_action_scale),
            device=self.device,
        )

        self.actions = torch.zeros(self.num_envs, self.cfg.action_space, device=self.device)
        self.left_arm_joint_pos_target = self._robot.data.default_joint_pos[:, self.left_arm_joint_ids].clone()
        self.right_arm_joint_pos_target = self._robot.data.default_joint_pos[:, self.right_arm_joint_ids].clone()
        self.left_finger_joint_pos_target = self._robot.data.default_joint_pos[:, self.left_finger_joint_ids].clone()
        self.right_finger_joint_pos_target = self._robot.data.default_joint_pos[:, self.right_finger_joint_ids].clone()
        self.robot_dof_targets = self._robot.data.default_joint_pos.clone()

        self._ensure_buffers()

    def _setup_scene(self):
        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        self._cube = RigidObject(self.cfg.cube)
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
        self.scene.rigid_objects["cube"] = self._cube

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)

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

        self.left_tcp_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.right_tcp_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.left_tcp_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.right_tcp_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.left_hold_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.right_hold_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.cube_vel = torch.zeros(self.num_envs, 6, device=self.device)
        self.cube_linear_speed = torch.zeros(self.num_envs, device=self.device)
        self.cube_angular_speed = torch.zeros(self.num_envs, device=self.device)
        self.cube_velocity_success_stable = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

        self.left_hold_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.right_hold_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.max_hold_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.hold_distance_asymmetry = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_center_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.left_gripper_width = torch.zeros(self.num_envs, device=self.device)
        self.right_gripper_width = torch.zeros(self.num_envs, device=self.device)
        self.mean_gripper_width = torch.zeros(self.num_envs, device=self.device)
        self.finger_table_clearance = torch.zeros(self.num_envs, device=self.device)
        self.finger_table_clearance_violation = torch.zeros(self.num_envs, device=self.device)
        self.left_side_alignment = torch.zeros(self.num_envs, device=self.device)
        self.right_side_alignment = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_side_success = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.bimanual_action_prior_active = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.bimanual_action_prior_phase = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        self.bimanual_action_prior_teacher_actions = torch.zeros(
            self.num_envs, int(self.cfg.action_space), device=self.device
        )
        self.bimanual_action_prior_delta_abs = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_delta_z_abs = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_reward = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_teacher_left_z = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_teacher_right_z = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_teacher_left_gripper = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_teacher_right_gripper = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_action_prior_hold_error = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_reference_start_left_hold = torch.zeros(self.num_envs, 3, device=self.device)
        self.bimanual_reference_start_right_hold = torch.zeros(self.num_envs, 3, device=self.device)
        self.bimanual_reference_lift_started = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.bimanual_reference_lift_start_step = torch.zeros(self.num_envs, device=self.device)
        self.bimanual_reference_lift_left_origin = torch.zeros(self.num_envs, 3, device=self.device)
        self.bimanual_reference_lift_right_origin = torch.zeros(self.num_envs, 3, device=self.device)

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = actions.clone().clamp(-1.0, 1.0)
        left_tcp_pos_b, left_tcp_quat_b = self._compute_tcp_frame_pose("left")
        right_tcp_pos_b, right_tcp_quat_b = self._compute_tcp_frame_pose("right")
        self.left_ik_controller.set_command(self.actions[:, :6] * self.action_scale, left_tcp_pos_b, left_tcp_quat_b)
        self.right_ik_controller.set_command(
            self.actions[:, 7:13] * self.action_scale,
            right_tcp_pos_b,
            right_tcp_quat_b,
        )
        self.left_finger_joint_pos_target[:] = self._gripper_targets_from_action(self.actions[:, 6])
        self.right_finger_joint_pos_target[:] = self._gripper_targets_from_action(self.actions[:, 13])

    def _apply_action(self) -> None:
        left_tcp_pos_b, left_tcp_quat_b = self._compute_tcp_frame_pose("left")
        right_tcp_pos_b, right_tcp_quat_b = self._compute_tcp_frame_pose("right")

        left_joint_pos = self._robot.data.joint_pos[:, self.left_arm_joint_ids]
        left_jacobian = self._compute_tcp_frame_jacobian("left")
        left_arm_target = self.left_ik_controller.compute(
            left_tcp_pos_b,
            left_tcp_quat_b,
            left_jacobian,
            left_joint_pos,
        )
        left_lower = self.robot_dof_lower_limits[self.left_arm_joint_ids]
        left_upper = self.robot_dof_upper_limits[self.left_arm_joint_ids]
        self.left_arm_joint_pos_target[:] = torch.clamp(left_arm_target, left_lower, left_upper)

        right_joint_pos = self._robot.data.joint_pos[:, self.right_arm_joint_ids]
        right_jacobian = self._compute_tcp_frame_jacobian("right")
        right_arm_target = self.right_ik_controller.compute(
            right_tcp_pos_b,
            right_tcp_quat_b,
            right_jacobian,
            right_joint_pos,
        )
        right_lower = self.robot_dof_lower_limits[self.right_arm_joint_ids]
        right_upper = self.robot_dof_upper_limits[self.right_arm_joint_ids]
        self.right_arm_joint_pos_target[:] = torch.clamp(right_arm_target, right_lower, right_upper)

        self._robot.set_joint_position_target(self.left_arm_joint_pos_target, joint_ids=self.left_arm_joint_ids)
        self._robot.set_joint_position_target(self.right_arm_joint_pos_target, joint_ids=self.right_arm_joint_ids)
        self._robot.set_joint_position_target(self.left_finger_joint_pos_target, joint_ids=self.left_finger_joint_ids)
        self._robot.set_joint_position_target(
            self.right_finger_joint_pos_target,
            joint_ids=self.right_finger_joint_ids,
        )

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
        finger_table_penetration_done = (
            (self.finger_table_clearance < float(self.cfg.finger_table_penetration_termination_margin))
            & (self.episode_length_buf > 2)
        )
        terminated = cube_out | success_done | prelift_drag_done | finger_table_penetration_done
        truncated = self.episode_length_buf >= self.max_episode_length - 1
        return terminated, truncated

    def _get_rewards(self) -> torch.Tensor:
        self._compute_intermediate_values(update_success_timer=True)
        (
            approach_reward,
            enclosure_reward,
            side_alignment_reward,
            lift_reward,
            height_tracking_reward,
            xy_stability_reward,
            success_bonus,
            close_action_reward,
            lift_action_reward,
            descend_action_penalty,
            table_clearance_penalty,
            gripper_close_reg,
            action_penalty,
        ) = compute_bimanual_yam_cube_grasp_rewards(
            self.left_hold_to_cube_dist,
            self.right_hold_to_cube_dist,
            self.left_gripper_width,
            self.right_gripper_width,
            self.cube_lift_height,
            self.cube_goal_height_error,
            self.cube_xy_error,
            self.finger_table_clearance,
            self.left_side_alignment,
            self.right_side_alignment,
            self.in_success_region,
            self.time_in_success_region >= float(self.cfg.success_timeout),
            self.actions,
            float(self.cfg.cube_lift_height),
            float(self.cfg.max_gripper_width),
            float(self.cfg.finger_table_clearance_margin),
            float(self.cfg.cube_approach_weight),
            float(self.cfg.cube_approach_sharpness),
            float(self.cfg.cube_enclosure_weight),
            float(self.cfg.cube_enclosure_sharpness),
            float(self.cfg.cube_side_alignment_weight),
            float(self.cfg.cube_lift_weight),
            float(self.cfg.cube_height_tracking_weight),
            float(self.cfg.cube_height_tracking_sharpness),
            float(self.cfg.cube_xy_stability_weight),
            float(self.cfg.cube_xy_stability_sharpness),
            float(self.cfg.cube_success_bonus_weight),
            float(self.cfg.cube_close_action_weight),
            float(self.cfg.cube_lift_action_weight),
            float(self.cfg.cube_descend_action_penalty_weight),
            float(self.cfg.cube_table_clearance_penalty_weight),
            float(self.cfg.cube_gripper_close_reg_weight),
            float(self.cfg.cube_action_penalty_weight),
        )
        total_reward = (
            approach_reward
            + enclosure_reward
            + side_alignment_reward
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
        )
        action_prior_reward = self._compute_bimanual_action_prior_reward()
        total_reward = total_reward + action_prior_reward
        log_terms = {
            "yam_cube_approach_reward": approach_reward.mean(),
            "yam_cube_enclosure_reward": enclosure_reward.mean(),
            "yam_cube_side_alignment_reward": side_alignment_reward.mean(),
            "yam_cube_lift_reward": lift_reward.mean(),
            "yam_cube_height_tracking_reward": height_tracking_reward.mean(),
            "yam_cube_xy_stability_reward": xy_stability_reward.mean(),
            "yam_cube_success_bonus": success_bonus.mean(),
            "yam_cube_close_action_reward": close_action_reward.mean(),
            "yam_cube_lift_action_reward": lift_action_reward.mean(),
            "yam_cube_descend_action_penalty": descend_action_penalty.mean(),
            "yam_cube_table_clearance_penalty": table_clearance_penalty.mean(),
            "yam_cube_gripper_close_reg": gripper_close_reg.mean(),
            "yam_cube_action_penalty": action_penalty.mean(),
            "yam_cube_lift_height": self.cube_lift_height.mean(),
            "yam_cube_xy_error": self.cube_xy_error.mean(),
            "yam_cube_goal_height_error": self.cube_goal_height_error.mean(),
            "yam_cube_success_rate": self.in_success_region.float().mean(),
            "yam_cube_stable_success_rate": (
                self.time_in_success_region >= float(self.cfg.success_timeout)
            ).float().mean(),
            "yam_cube_has_lifted_rate": self.has_lifted_cube.float().mean(),
            "yam_cube_linear_speed": self.cube_linear_speed.mean(),
            "yam_cube_angular_speed": self.cube_angular_speed.mean(),
            "yam_cube_velocity_success_stable_rate": self.cube_velocity_success_stable.float().mean(),
            "yam_cube_bimanual_side_success_rate": self.bimanual_side_success.float().mean(),
            "yam_cube_left_hold_to_cube_dist": self.left_hold_to_cube_dist.mean(),
            "yam_cube_right_hold_to_cube_dist": self.right_hold_to_cube_dist.mean(),
            "yam_cube_bimanual_center_to_cube_dist": self.bimanual_center_to_cube_dist.mean(),
            "yam_cube_max_hold_to_cube_dist": self.max_hold_to_cube_dist.mean(),
            "yam_cube_hold_distance_asymmetry": self.hold_distance_asymmetry.mean(),
            "yam_cube_left_gripper_width": self.left_gripper_width.mean(),
            "yam_cube_right_gripper_width": self.right_gripper_width.mean(),
            "yam_cube_finger_table_clearance": self.finger_table_clearance.mean(),
            "yam_cube_left_side_alignment": self.left_side_alignment.mean(),
            "yam_cube_right_side_alignment": self.right_side_alignment.mean(),
            "yam_cube_left_action_z": self.actions[:, 2].mean(),
            "yam_cube_right_action_z": self.actions[:, 9].mean(),
            "yam_cube_left_gripper_action": self.actions[:, 6].mean(),
            "yam_cube_right_gripper_action": self.actions[:, 13].mean(),
        }
        if bool(self.cfg.bimanual_action_prior_reward_enabled):
            action_prior_phase = self.bimanual_action_prior_phase
            log_terms.update(
                {
                    "yam_cube_action_prior_reward": action_prior_reward.mean(),
                    "yam_cube_action_prior_active_rate": self.bimanual_action_prior_active.float().mean(),
                    "yam_cube_action_prior_close_rate": (action_prior_phase == 0).float().mean(),
                    "yam_cube_action_prior_standoff_rate": (action_prior_phase == 1).float().mean(),
                    "yam_cube_action_prior_approach_rate": (action_prior_phase == 2).float().mean(),
                    "yam_cube_action_prior_lift_rate": (action_prior_phase == 3).float().mean(),
                    "yam_cube_action_prior_delta_abs": self.bimanual_action_prior_delta_abs.mean(),
                    "yam_cube_action_prior_delta_z_abs": self.bimanual_action_prior_delta_z_abs.mean(),
                    "yam_cube_action_prior_teacher_left_z": self.bimanual_action_prior_teacher_left_z.mean(),
                    "yam_cube_action_prior_teacher_right_z": self.bimanual_action_prior_teacher_right_z.mean(),
                    "yam_cube_action_prior_teacher_left_rot_z": (
                        self.bimanual_action_prior_teacher_actions[:, 5].mean()
                    ),
                    "yam_cube_action_prior_teacher_right_rot_z": (
                        self.bimanual_action_prior_teacher_actions[:, 12].mean()
                    ),
                    "yam_cube_action_prior_teacher_left_gripper": (
                        self.bimanual_action_prior_teacher_left_gripper.mean()
                    ),
                    "yam_cube_action_prior_teacher_right_gripper": (
                        self.bimanual_action_prior_teacher_right_gripper.mean()
                    ),
                    "yam_cube_action_prior_hold_error": self.bimanual_action_prior_hold_error.mean(),
                }
            )
        self.extras["log"] = log_terms
        for key, value in log_terms.items():
            self.extras[key] = value
        self.extras["in_success_region"] = self.in_success_region.float().mean()
        return total_reward

    def _actions_to_hold_targets(
        self,
        desired_left_hold: torch.Tensor,
        desired_right_hold: torch.Tensor,
        grip: float,
        *,
        gain: float,
        max_action: float,
    ) -> torch.Tensor:
        actions = torch.zeros(self.num_envs, int(self.cfg.action_space), device=self.device)
        pos_scale = torch.clamp(self.action_scale[:3], min=1.0e-6)
        actions[:, :3] = torch.clamp(
            gain * (desired_left_hold - self.left_hold_pos) / pos_scale,
            -float(max_action),
            float(max_action),
        )
        actions[:, 7:10] = torch.clamp(
            gain * (desired_right_hold - self.right_hold_pos) / pos_scale,
            -float(max_action),
            float(max_action),
        )
        actions[:, 6] = float(grip)
        actions[:, 13] = float(grip)
        return actions

    def _limit_reference_descent(
        self,
        actions: torch.Tensor,
        left_floor_z: torch.Tensor,
        right_floor_z: torch.Tensor,
    ) -> torch.Tensor:
        limited_actions = actions.clone()
        descent_max = max(float(self.cfg.bimanual_reference_descent_max_action), 0.0)
        floor_margin = max(float(self.cfg.bimanual_reference_descent_floor_margin), 0.0)
        if descent_max > 0.0:
            limited_actions[:, 2] = torch.clamp(limited_actions[:, 2], min=-descent_max)
            limited_actions[:, 9] = torch.clamp(limited_actions[:, 9], min=-descent_max)
        left_near_floor = self.left_hold_pos[:, 2] <= (left_floor_z + floor_margin)
        right_near_floor = self.right_hold_pos[:, 2] <= (right_floor_z + floor_margin)
        limited_actions[left_near_floor, 2] = torch.clamp(limited_actions[left_near_floor, 2], min=0.0)
        limited_actions[right_near_floor, 9] = torch.clamp(limited_actions[right_near_floor, 9], min=0.0)
        return limited_actions

    def _smooth_phase_alpha(self, start_step: int, phase_steps: int) -> torch.Tensor:
        if phase_steps <= 0:
            return torch.ones(self.num_envs, device=self.device)
        alpha = torch.clamp(
            (self.episode_length_buf.float() - float(start_step) + 1.0) / float(phase_steps),
            0.0,
            1.0,
        )
        return alpha * alpha * (3.0 - 2.0 * alpha)

    def _lerp_hold_target(self, start: torch.Tensor, end: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
        return start + alpha.unsqueeze(-1) * (end - start)

    def _bimanual_reference_actions(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        self._compute_intermediate_values()
        teacher_actions = torch.zeros(self.num_envs, int(self.cfg.action_space), device=self.device)
        active = ~self.in_success_region
        phase = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        hold_error = torch.zeros(self.num_envs, device=self.device)
        if not bool(active.any().item()):
            return teacher_actions, active, phase, hold_error

        cube_half_size = 0.5 * float(self.cfg.cube_size)
        side_offset = cube_half_size + float(self.cfg.bimanual_reference_contact_side_margin)
        reference_cube_pos = self.cube_initial_pos.clone()
        hold_z = torch.maximum(
            reference_cube_pos[:, 2] + float(self.cfg.bimanual_reference_cube_center_to_hold_z),
            torch.full_like(self.cube_initial_pos[:, 2], float(self.cfg.table_surface_z) + float(self.cfg.bimanual_reference_min_hold_z)),
        )
        contact_left_hold = reference_cube_pos.clone()
        contact_right_hold = reference_cube_pos.clone()
        contact_left_hold[:, 1] = reference_cube_pos[:, 1] + side_offset
        contact_right_hold[:, 1] = reference_cube_pos[:, 1] - side_offset
        contact_left_hold[:, 2] = hold_z
        contact_right_hold[:, 2] = hold_z
        standoff_side_offset = side_offset + float(self.cfg.bimanual_reference_standoff_side_margin)
        standoff_left_hold = contact_left_hold.clone()
        standoff_right_hold = contact_right_hold.clone()
        standoff_left_hold[:, 1] = reference_cube_pos[:, 1] + standoff_side_offset
        standoff_right_hold[:, 1] = reference_cube_pos[:, 1] - standoff_side_offset
        left_rot_action = torch.tensor(
            self.cfg.bimanual_reference_left_rot_action,
            dtype=teacher_actions.dtype,
            device=self.device,
        )
        right_rot_action = torch.tensor(
            self.cfg.bimanual_reference_right_rot_action,
            dtype=teacher_actions.dtype,
            device=self.device,
        )

        close_steps = max(int(self.cfg.bimanual_reference_close_steps), 0)
        standoff_steps = max(int(self.cfg.bimanual_reference_standoff_steps), 0)
        approach_steps = max(int(self.cfg.bimanual_reference_approach_steps), 0)
        standoff_start = close_steps
        approach_start = standoff_start + standoff_steps
        lift_start = approach_start + approach_steps
        episode_step = self.episode_length_buf

        contact_trigger = (
            active
            & (~self.bimanual_reference_lift_started)
            & (episode_step >= approach_start)
            & self.bimanual_side_success
            & (self.max_hold_to_cube_dist <= float(self.cfg.bimanual_reference_contact_trigger_dist))
        )
        fixed_lift_trigger = (
            active
            & (~self.bimanual_reference_lift_started)
            & (episode_step >= lift_start)
            & self.bimanual_side_success
            & (self.max_hold_to_cube_dist <= float(self.cfg.bimanual_reference_contact_trigger_dist))
        )
        new_lift = contact_trigger | fixed_lift_trigger
        if bool(new_lift.any().item()):
            self.bimanual_reference_lift_started[new_lift] = True
            self.bimanual_reference_lift_start_step[new_lift] = episode_step[new_lift].float()
            self.bimanual_reference_lift_left_origin[new_lift] = self.left_hold_pos[new_lift]
            self.bimanual_reference_lift_right_origin[new_lift] = self.right_hold_pos[new_lift]

        lift_mask = active & self.bimanual_reference_lift_started
        close_mask = active & (~lift_mask) & (episode_step < standoff_start)
        standoff_mask = active & (~lift_mask) & (episode_step >= standoff_start) & (episode_step < approach_start)
        approach_mask = active & (~lift_mask) & (episode_step >= approach_start)

        standoff_alpha = self._smooth_phase_alpha(standoff_start, standoff_steps)
        approach_alpha = self._smooth_phase_alpha(approach_start, approach_steps)
        lift_steps = max(int(self.cfg.bimanual_reference_lift_steps), 1)
        lift_alpha = torch.clamp(
            (episode_step.float() - self.bimanual_reference_lift_start_step + 1.0) / float(lift_steps),
            0.0,
            1.0,
        )
        lift_alpha = lift_alpha * lift_alpha * (3.0 - 2.0 * lift_alpha)
        desired_standoff_left = self._lerp_hold_target(
            self.bimanual_reference_start_left_hold,
            standoff_left_hold,
            standoff_alpha,
        )
        desired_standoff_right = self._lerp_hold_target(
            self.bimanual_reference_start_right_hold,
            standoff_right_hold,
            standoff_alpha,
        )
        desired_approach_left = self._lerp_hold_target(standoff_left_hold, contact_left_hold, approach_alpha)
        desired_approach_right = self._lerp_hold_target(standoff_right_hold, contact_right_hold, approach_alpha)
        desired_lift_left = self.bimanual_reference_lift_left_origin.clone()
        desired_lift_right = self.bimanual_reference_lift_right_origin.clone()
        desired_lift_left[:, 2] += lift_alpha * float(self.cfg.bimanual_reference_lift_height)
        desired_lift_right[:, 2] += lift_alpha * float(self.cfg.bimanual_reference_lift_height)
        squeeze_alpha = torch.clamp(2.0 * lift_alpha, 0.0, 1.0)
        desired_lift_left[:, 1] -= squeeze_alpha * float(self.cfg.bimanual_reference_lift_squeeze_y)
        desired_lift_right[:, 1] += squeeze_alpha * float(self.cfg.bimanual_reference_lift_squeeze_y)

        if bool(close_mask.any().item()):
            close_actions = self._actions_to_hold_targets(
                self.left_hold_pos,
                self.right_hold_pos,
                -1.0,
                gain=0.0,
                max_action=0.0,
            )
            teacher_actions[close_mask] = close_actions[close_mask]
            phase[close_mask] = 0
        if bool(standoff_mask.any().item()):
            standoff_actions = self._actions_to_hold_targets(
                desired_standoff_left,
                desired_standoff_right,
                -1.0,
                gain=float(self.cfg.bimanual_reference_gain),
                max_action=float(self.cfg.bimanual_reference_max_action),
            )
            standoff_actions = self._limit_reference_descent(
                standoff_actions,
                contact_left_hold[:, 2],
                contact_right_hold[:, 2],
            )
            standoff_actions[:, 3:6] = left_rot_action
            standoff_actions[:, 10:13] = right_rot_action
            teacher_actions[standoff_mask] = standoff_actions[standoff_mask]
            phase[standoff_mask] = 1
        if bool(approach_mask.any().item()):
            approach_actions = self._actions_to_hold_targets(
                desired_approach_left,
                desired_approach_right,
                -1.0,
                gain=float(self.cfg.bimanual_reference_gain),
                max_action=float(self.cfg.bimanual_reference_max_action),
            )
            approach_actions = self._limit_reference_descent(
                approach_actions,
                contact_left_hold[:, 2],
                contact_right_hold[:, 2],
            )
            approach_actions[:, 3:6] = left_rot_action
            approach_actions[:, 10:13] = right_rot_action
            teacher_actions[approach_mask] = approach_actions[approach_mask]
            phase[approach_mask] = 2
        if bool(lift_mask.any().item()):
            lift_actions = self._actions_to_hold_targets(
                desired_lift_left,
                desired_lift_right,
                -1.0,
                gain=float(self.cfg.bimanual_reference_lift_gain),
                max_action=float(self.cfg.bimanual_reference_lift_max_action),
            )
            lift_actions[:, 2] = torch.clamp(lift_actions[:, 2], min=0.0)
            lift_actions[:, 9] = torch.clamp(lift_actions[:, 9], min=0.0)
            teacher_actions[lift_mask] = lift_actions[lift_mask]
            phase[lift_mask] = 3

        desired_left = torch.where(standoff_mask.unsqueeze(-1), desired_standoff_left, desired_approach_left)
        desired_right = torch.where(standoff_mask.unsqueeze(-1), desired_standoff_right, desired_approach_right)
        desired_left = torch.where(lift_mask.unsqueeze(-1), desired_lift_left, desired_left)
        desired_right = torch.where(lift_mask.unsqueeze(-1), desired_lift_right, desired_right)
        desired_left = torch.where(close_mask.unsqueeze(-1), self.left_hold_pos, desired_left)
        desired_right = torch.where(close_mask.unsqueeze(-1), self.right_hold_pos, desired_right)
        hold_error[:] = torch.maximum(
            torch.norm(desired_left - self.left_hold_pos, dim=-1),
            torch.norm(desired_right - self.right_hold_pos, dim=-1),
        )
        return teacher_actions.clamp(-1.0, 1.0), active, phase, hold_error

    def compute_grasp_prior_reference_actions(self) -> torch.Tensor:
        """Return a bimanual scripted action target using the 14-D RL action interface."""
        teacher_actions, _, _, _ = self._bimanual_reference_actions()
        return teacher_actions.detach().clamp(-1.0, 1.0)

    def _compute_bimanual_action_prior_reward(self) -> torch.Tensor:
        self.bimanual_action_prior_active[:] = False
        self.bimanual_action_prior_phase[:] = -1
        self.bimanual_action_prior_teacher_actions[:] = 0.0
        self.bimanual_action_prior_delta_abs[:] = 0.0
        self.bimanual_action_prior_delta_z_abs[:] = 0.0
        self.bimanual_action_prior_reward[:] = 0.0
        self.bimanual_action_prior_teacher_left_z[:] = 0.0
        self.bimanual_action_prior_teacher_right_z[:] = 0.0
        self.bimanual_action_prior_teacher_left_gripper[:] = 0.0
        self.bimanual_action_prior_teacher_right_gripper[:] = 0.0
        self.bimanual_action_prior_hold_error[:] = 0.0

        if not bool(self.cfg.bimanual_action_prior_reward_enabled):
            return self.bimanual_action_prior_reward

        teacher_actions, active, phase, hold_error = self._bimanual_reference_actions()
        self.bimanual_action_prior_active[:] = active
        self.bimanual_action_prior_phase[:] = phase
        self.bimanual_action_prior_teacher_actions[:] = teacher_actions
        self.bimanual_action_prior_teacher_left_z[:] = teacher_actions[:, 2]
        self.bimanual_action_prior_teacher_right_z[:] = teacher_actions[:, 9]
        self.bimanual_action_prior_teacher_left_gripper[:] = teacher_actions[:, 6]
        self.bimanual_action_prior_teacher_right_gripper[:] = teacher_actions[:, 13]
        self.bimanual_action_prior_hold_error[:] = hold_error

        if bool(active.any().item()):
            action_delta = torch.abs(self.actions - teacher_actions)
            mean_delta_abs = torch.mean(action_delta, dim=-1)
            lift_z_delta_abs = 0.5 * (action_delta[:, 2] + action_delta[:, 9])
            lift_phase = phase == 3
            delta_abs = torch.where(
                lift_phase,
                0.20 * mean_delta_abs + 0.80 * lift_z_delta_abs,
                mean_delta_abs,
            )
            self.bimanual_action_prior_delta_abs[:] = delta_abs
            self.bimanual_action_prior_delta_z_abs[:] = torch.where(
                lift_phase,
                lift_z_delta_abs,
                torch.zeros_like(lift_z_delta_abs),
            )
            weight = max(float(self.cfg.bimanual_action_prior_reward_weight), 0.0)
            sharpness = max(float(self.cfg.bimanual_action_prior_reward_sharpness), 0.0)
            self.bimanual_action_prior_reward[:] = weight * active.float() * torch.exp(-sharpness * delta_abs)
        return self.bimanual_action_prior_reward

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
        self.left_arm_joint_pos_target[env_ids] = joint_pos[:, self.left_arm_joint_ids]
        self.right_arm_joint_pos_target[env_ids] = joint_pos[:, self.right_arm_joint_ids]
        self.left_finger_joint_pos_target[env_ids] = joint_pos[:, self.left_finger_joint_ids]
        self.right_finger_joint_pos_target[env_ids] = joint_pos[:, self.right_finger_joint_ids]

        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.pickup_x)
        spawn_xy[:, 1] = float(self.cfg.pickup_y)
        spawn_xy += float(self.cfg.cube_spawn_xy_randomization) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x + 0.5 * self.cfg.cube_size)
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x - 0.5 * self.cfg.cube_size)
        min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y + 0.5 * self.cfg.cube_size)
        max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y - 0.5 * self.cfg.cube_size)
        spawn_xy[:, 0] = torch.clamp(spawn_xy[:, 0], min=min_x, max=max_x)
        spawn_xy[:, 1] = torch.clamp(spawn_xy[:, 1], min=min_y, max=max_y)

        cube_pos = torch.zeros(num_ids, 3, device=self.device)
        cube_pos[:, 0:2] = spawn_xy
        cube_pos[:, 2] = float(self.cfg.cube_spawn_z)
        yaw_randomization = math.radians(float(self.cfg.cube_spawn_yaw_randomization_deg))
        if yaw_randomization > 0.0:
            yaw = yaw_randomization * (2.0 * torch.rand(num_ids, device=self.device) - 1.0)
            cube_quat = _yaw_quat_wxyz(yaw)
        else:
            cube_quat = torch.zeros(num_ids, 4, device=self.device)
            cube_quat[:, 0] = 1.0

        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = cube_pos + self.scene.env_origins[env_ids]
        object_state[:, 3:7] = cube_quat
        self._cube.write_root_state_to_sim(object_state, env_ids=env_ids)

        self.cube_initial_pos[env_ids] = cube_pos
        self.cube_goal_pos[env_ids] = cube_pos
        self.cube_goal_pos[env_ids, 2] = cube_pos[:, 2] + float(self.cfg.cube_lift_height)
        self.has_lifted_cube[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
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

    def _get_observations(self) -> dict[str, torch.Tensor]:
        self._compute_intermediate_values()
        joint_range = torch.clamp(self.robot_dof_upper_limits - self.robot_dof_lower_limits, min=1.0e-6)
        joint_pos_scaled = 2.0 * (self._robot.data.joint_pos - self.robot_dof_lower_limits) / joint_range - 1.0
        joint_vel_scaled = 0.12 * self._robot.data.joint_vel
        bimanual_center = 0.5 * (self.left_hold_pos + self.right_hold_pos)
        obs = torch.cat(
            (
                joint_pos_scaled,
                joint_vel_scaled,
                self.left_tcp_pos,
                self.left_tcp_quat,
                self.right_tcp_pos,
                self.right_tcp_quat,
                self.left_hold_pos - self.cube_pos,
                self.right_hold_pos - self.cube_pos,
                self.cube_pos,
                self.cube_quat,
                self.cube_vel,
                self.cube_goal_pos,
                self.cube_pos - bimanual_center,
                self.cube_goal_pos - self.cube_pos,
                self.has_lifted_cube.float().unsqueeze(-1),
                self.in_success_region.float().unsqueeze(-1),
                self.time_in_success_region.unsqueeze(-1),
                self.left_gripper_width.unsqueeze(-1),
                self.right_gripper_width.unsqueeze(-1),
                self.left_hold_to_cube_dist.unsqueeze(-1),
                self.right_hold_to_cube_dist.unsqueeze(-1),
                self.cube_lift_height.unsqueeze(-1),
                self.cube_xy_error.unsqueeze(-1),
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

        env_origins = self.scene.env_origins[env_ids]
        root_pos_w = self._robot.data.root_pos_w[env_ids]
        root_quat_w = self._robot.data.root_quat_w[env_ids]

        left_tcp_pos_b, left_tcp_quat_b = self._compute_tcp_frame_pose("left", env_ids)
        right_tcp_pos_b, right_tcp_quat_b = self._compute_tcp_frame_pose("right", env_ids)
        left_tcp_pos_w, left_tcp_quat_w = math_utils.combine_frame_transforms(
            root_pos_w,
            root_quat_w,
            left_tcp_pos_b,
            left_tcp_quat_b,
        )
        right_tcp_pos_w, right_tcp_quat_w = math_utils.combine_frame_transforms(
            root_pos_w,
            root_quat_w,
            right_tcp_pos_b,
            right_tcp_quat_b,
        )

        left_finger_a = self._robot.data.body_pos_w[env_ids, self.left_finger_body_ids[0]] - env_origins
        left_finger_b = self._robot.data.body_pos_w[env_ids, self.left_finger_body_ids[1]] - env_origins
        right_finger_a = self._robot.data.body_pos_w[env_ids, self.right_finger_body_ids[0]] - env_origins
        right_finger_b = self._robot.data.body_pos_w[env_ids, self.right_finger_body_ids[1]] - env_origins

        self.left_tcp_pos[env_ids] = left_tcp_pos_w - env_origins
        self.left_tcp_quat[env_ids] = left_tcp_quat_w
        self.right_tcp_pos[env_ids] = right_tcp_pos_w - env_origins
        self.right_tcp_quat[env_ids] = right_tcp_quat_w
        self.left_hold_pos[env_ids] = 0.5 * (left_finger_a + left_finger_b)
        self.right_hold_pos[env_ids] = 0.5 * (right_finger_a + right_finger_b)
        self.cube_pos[env_ids] = self._cube.data.root_pos_w[env_ids] - env_origins
        self.cube_quat[env_ids] = self._cube.data.root_quat_w[env_ids]
        self.cube_vel[env_ids] = self._cube.data.root_vel_w[env_ids]
        self.cube_linear_speed[env_ids] = torch.norm(self.cube_vel[env_ids, :3], dim=-1)
        self.cube_angular_speed[env_ids] = torch.norm(self.cube_vel[env_ids, 3:], dim=-1)

        self.left_gripper_width[env_ids] = torch.norm(left_finger_a - left_finger_b, dim=-1)
        self.right_gripper_width[env_ids] = torch.norm(right_finger_a - right_finger_b, dim=-1)
        self.mean_gripper_width[env_ids] = 0.5 * (
            self.left_gripper_width[env_ids] + self.right_gripper_width[env_ids]
        )
        self.left_hold_to_cube_dist[env_ids] = torch.norm(
            self.left_hold_pos[env_ids] - self.cube_pos[env_ids],
            dim=-1,
        )
        self.right_hold_to_cube_dist[env_ids] = torch.norm(
            self.right_hold_pos[env_ids] - self.cube_pos[env_ids],
            dim=-1,
        )
        self.max_hold_to_cube_dist[env_ids] = torch.maximum(
            self.left_hold_to_cube_dist[env_ids],
            self.right_hold_to_cube_dist[env_ids],
        )
        self.hold_distance_asymmetry[env_ids] = torch.abs(
            self.left_hold_to_cube_dist[env_ids] - self.right_hold_to_cube_dist[env_ids]
        )
        bimanual_center = 0.5 * (self.left_hold_pos[env_ids] + self.right_hold_pos[env_ids])
        self.bimanual_center_to_cube_dist[env_ids] = torch.norm(bimanual_center - self.cube_pos[env_ids], dim=-1)

        all_finger_z = torch.stack(
            (
                left_finger_a[:, 2],
                left_finger_b[:, 2],
                right_finger_a[:, 2],
                right_finger_b[:, 2],
            ),
            dim=-1,
        )
        self.finger_table_clearance[env_ids] = torch.min(all_finger_z, dim=-1).values - float(
            self.cfg.table_surface_z
        )
        clearance_margin = max(float(self.cfg.finger_table_clearance_margin), 1.0e-6)
        self.finger_table_clearance_violation[env_ids] = torch.clamp(
            (float(self.cfg.finger_table_clearance_margin) - self.finger_table_clearance[env_ids])
            / clearance_margin,
            0.0,
            1.0,
        )

        side_margin = float(self.cfg.side_success_y_margin)
        left_side_distance = self.left_hold_pos[env_ids, 1] - self.cube_pos[env_ids, 1]
        right_side_distance = self.cube_pos[env_ids, 1] - self.right_hold_pos[env_ids, 1]
        side_scale = max(0.5 * float(self.cfg.cube_size), 1.0e-6)
        self.left_side_alignment[env_ids] = torch.clamp((left_side_distance + side_margin) / side_scale, 0.0, 1.0)
        self.right_side_alignment[env_ids] = torch.clamp((right_side_distance + side_margin) / side_scale, 0.0, 1.0)
        self.bimanual_side_success[env_ids] = (
            (left_side_distance >= -side_margin)
            & (right_side_distance >= -side_margin)
            & (self.left_hold_to_cube_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
            & (self.right_hold_to_cube_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
        )

        self.cube_lift_height[env_ids] = torch.clamp(
            self.cube_pos[env_ids, 2] - self.cube_initial_pos[env_ids, 2],
            min=0.0,
        )
        self.cube_xy_error[env_ids] = torch.norm(
            self.cube_pos[env_ids, :2] - self.cube_initial_pos[env_ids, :2],
            dim=-1,
        )
        self.cube_goal_height_error[env_ids] = torch.abs(self.cube_goal_pos[env_ids, 2] - self.cube_pos[env_ids, 2])
        self.has_lifted_cube[env_ids] |= self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height)

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

    def _compute_tcp_frame_pose(
        self,
        arm: str,
        env_ids: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if env_ids is None:
            body_idx = self.left_tcp_body_idx if arm == "left" else self.right_tcp_body_idx
            offset_pos = self.left_tcp_offset_pos if arm == "left" else self.right_tcp_offset_pos
            hand_pos_w = self._robot.data.body_pos_w[:, body_idx]
            hand_quat_w = self._robot.data.body_quat_w[:, body_idx]
            root_pos_w = self._robot.data.root_pos_w
            root_quat_w = self._robot.data.root_quat_w
            offset_rot = self.tcp_offset_rot
        else:
            body_idx = self.left_tcp_body_idx if arm == "left" else self.right_tcp_body_idx
            offset_pos_all = self.left_tcp_offset_pos if arm == "left" else self.right_tcp_offset_pos
            offset_pos = offset_pos_all[env_ids]
            hand_pos_w = self._robot.data.body_pos_w[env_ids, body_idx]
            hand_quat_w = self._robot.data.body_quat_w[env_ids, body_idx]
            root_pos_w = self._robot.data.root_pos_w[env_ids]
            root_quat_w = self._robot.data.root_quat_w[env_ids]
            offset_rot = self.tcp_offset_rot[env_ids]
        tcp_pos_b, tcp_quat_b = math_utils.subtract_frame_transforms(
            root_pos_w,
            root_quat_w,
            hand_pos_w,
            hand_quat_w,
        )
        return math_utils.combine_frame_transforms(tcp_pos_b, tcp_quat_b, offset_pos, offset_rot)

    def _compute_tcp_frame_jacobian(self, arm: str) -> torch.Tensor:
        if arm == "left":
            jacobi_idx = self.left_tcp_jacobi_idx
            joint_ids = self.left_arm_joint_ids
            offset_pos = self.left_tcp_offset_pos
        else:
            jacobi_idx = self.right_tcp_jacobi_idx
            joint_ids = self.right_arm_joint_ids
            offset_pos = self.right_tcp_offset_pos
        jacobian = self._robot.root_physx_view.get_jacobians()[:, jacobi_idx, :, joint_ids]
        base_rot = self._robot.data.root_quat_w
        base_rot_matrix = math_utils.matrix_from_quat(math_utils.quat_inv(base_rot))
        jacobian[:, :3, :] = torch.bmm(base_rot_matrix, jacobian[:, :3, :])
        jacobian[:, 3:, :] = torch.bmm(base_rot_matrix, jacobian[:, 3:, :])
        jacobian[:, 0:3, :] += torch.bmm(-math_utils.skew_symmetric_matrix(offset_pos), jacobian[:, 3:, :])
        return jacobian

    def get_current_observations(self):
        return self._get_observations()
