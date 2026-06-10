"""DirectRLEnv for Franka single-cube grasp-and-lift."""

from __future__ import annotations

from collections.abc import Sequence

import torch

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import Articulation, RigidObject
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env import (
    DextrahFrankaStarKittingEnv,
)

from .franka_cube_grasp_env_cfg import DextrahFrankaCubeGraspEnvCfg
from .franka_cube_grasp_rewards import compute_franka_cube_grasp_rewards


class DextrahFrankaCubeGraspEnv(DextrahFrankaStarKittingEnv):
    """Franka task: pick up the procedural cube used by the KUKA cube baseline."""

    cfg: DextrahFrankaCubeGraspEnvCfg

    def __init__(self, cfg: DextrahFrankaCubeGraspEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        self._ensure_cube_buffers()

    def _setup_scene(self):
        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        self._cube = RigidObject(self.cfg.cube)
        spawn_ground_plane(prim_path="/World/ground", cfg=GroundPlaneCfg())

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table
        self.scene.rigid_objects["cube"] = self._cube

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)

    def _ensure_cube_buffers(self) -> None:
        if hasattr(self, "cube_initial_pos"):
            return
        self.cube_initial_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_goal_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.cube_lift_height = torch.zeros(self.num_envs, device=self.device)
        self.cube_xy_error = torch.zeros(self.num_envs, device=self.device)
        self.cube_goal_height_error = torch.zeros(self.num_envs, device=self.device)
        self.has_lifted_cube = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.in_success_region = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.time_in_success_region = torch.zeros(self.num_envs, device=self.device)
        self.ee_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.finger_center_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.left_finger_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.right_finger_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.max_finger_to_cube_dist = torch.zeros(self.num_envs, device=self.device)
        self.finger_distance_asymmetry = torch.zeros(self.num_envs, device=self.device)
        self.hand_to_cube_mean_dist = torch.zeros(self.num_envs, device=self.device)
        self.hand_to_cube_max_dist = torch.zeros(self.num_envs, device=self.device)
        self.gripper_width = torch.zeros(self.num_envs, device=self.device)

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        self._compute_intermediate_values()
        lower_x = self.cfg.table_center_x - 0.5 * self.cfg.table_size_x - self.cfg.out_of_bounds_margin
        upper_x = self.cfg.table_center_x + 0.5 * self.cfg.table_size_x + self.cfg.out_of_bounds_margin
        lower_y = -0.5 * self.cfg.table_size_y - self.cfg.out_of_bounds_margin
        upper_y = 0.5 * self.cfg.table_size_y + self.cfg.out_of_bounds_margin
        cube_out = (
            (self.cube_pos[:, 0] < lower_x)
            | (self.cube_pos[:, 0] > upper_x)
            | (self.cube_pos[:, 1] < lower_y)
            | (self.cube_pos[:, 1] > upper_y)
            | (self.cube_pos[:, 2] < self.cfg.table_surface_z - 0.08)
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
        terminated = cube_out | success_done | prelift_drag_done
        truncated = self.episode_length_buf >= self.max_episode_length - 1
        return terminated, truncated

    def _get_rewards(self) -> torch.Tensor:
        self._compute_intermediate_values(update_success_timer=True)
        (
            approach_reward,
            finger_approach_reward,
            grasp_ready_reward,
            closed_grasp_reward,
            lift_reward,
            height_tracking_reward,
            xy_stability_reward,
            close_action_reward,
            lift_action_reward,
            success_bonus,
            prelift_move_penalty,
            close_far_penalty,
            open_near_penalty,
            ungrasped_lift_penalty,
            action_penalty,
        ) = compute_franka_cube_grasp_rewards(
            self.ee_to_cube_dist,
            self.finger_center_to_cube_dist,
            self.left_finger_to_cube_dist,
            self.right_finger_to_cube_dist,
            self.gripper_width,
            self.cube_lift_height,
            self.cube_xy_error,
            self.cube_goal_height_error,
            self.has_lifted_cube,
            self.in_success_region,
            self.actions,
            float(self.cfg.cube_lift_height),
            float(self.cfg.max_gripper_width),
            float(self.cfg.cube_approach_weight),
            float(self.cfg.cube_approach_sharpness),
            float(self.cfg.cube_finger_approach_weight),
            float(self.cfg.cube_finger_approach_sharpness),
            float(self.cfg.cube_grasp_ready_weight),
            float(self.cfg.cube_closed_grasp_weight),
            float(self.cfg.cube_lift_weight),
            float(self.cfg.cube_height_tracking_weight),
            float(self.cfg.cube_height_tracking_sharpness),
            float(self.cfg.cube_xy_stability_weight),
            float(self.cfg.cube_xy_stability_sharpness),
            float(self.cfg.cube_close_action_weight),
            float(self.cfg.cube_lift_action_weight),
            float(self.cfg.cube_success_bonus_weight),
            float(self.cfg.cube_prelift_move_penalty_weight),
            float(self.cfg.cube_close_far_penalty_weight),
            float(self.cfg.cube_open_near_penalty_weight),
            float(self.cfg.cube_ungrasped_lift_penalty_weight),
            float(self.cfg.cube_action_penalty_weight),
        )
        total_reward = (
            approach_reward
            + finger_approach_reward
            + grasp_ready_reward
            + closed_grasp_reward
            + lift_reward
            + height_tracking_reward
            + xy_stability_reward
            + close_action_reward
            + lift_action_reward
            + success_bonus
            + prelift_move_penalty
            + close_far_penalty
            + open_near_penalty
            + ungrasped_lift_penalty
            + action_penalty
        )
        log_terms = {
            "cube_approach_reward": approach_reward.mean(),
            "cube_finger_approach_reward": finger_approach_reward.mean(),
            "cube_grasp_ready_reward": grasp_ready_reward.mean(),
            "cube_closed_grasp_reward": closed_grasp_reward.mean(),
            "cube_lift_reward": lift_reward.mean(),
            "cube_height_tracking_reward": height_tracking_reward.mean(),
            "cube_xy_stability_reward": xy_stability_reward.mean(),
            "cube_close_action_reward": close_action_reward.mean(),
            "cube_lift_action_reward": lift_action_reward.mean(),
            "cube_success_bonus": success_bonus.mean(),
            "cube_prelift_move_penalty": prelift_move_penalty.mean(),
            "cube_close_far_penalty": close_far_penalty.mean(),
            "cube_open_near_penalty": open_near_penalty.mean(),
            "cube_ungrasped_lift_penalty": ungrasped_lift_penalty.mean(),
            "cube_action_penalty": action_penalty.mean(),
            "cube_lift_height": self.cube_lift_height.mean(),
            "cube_xy_error": self.cube_xy_error.mean(),
            "cube_goal_height_error": self.cube_goal_height_error.mean(),
            "cube_success_rate": self.in_success_region.float().mean(),
            "cube_has_lifted_rate": self.has_lifted_cube.float().mean(),
            "cube_gripper_width": self.gripper_width.mean(),
            "cube_ee_to_cube_dist": self.ee_to_cube_dist.mean(),
            "cube_finger_center_to_cube_dist": self.finger_center_to_cube_dist.mean(),
            "cube_left_finger_to_cube_dist": self.left_finger_to_cube_dist.mean(),
            "cube_right_finger_to_cube_dist": self.right_finger_to_cube_dist.mean(),
            "cube_max_finger_to_cube_dist": self.max_finger_to_cube_dist.mean(),
            "cube_finger_distance_asymmetry": self.finger_distance_asymmetry.mean(),
            "cube_action_z": self.actions[:, 2].mean(),
            "cube_action_up": torch.clamp(self.actions[:, 2], 0.0, 1.0).mean(),
            "cube_action_down": torch.clamp(-self.actions[:, 2], 0.0, 1.0).mean(),
            "cube_gripper_action": self.actions[:, 6].mean(),
            "cube_gripper_close_action": torch.clamp(-self.actions[:, 6], 0.0, 1.0).mean(),
        }
        self.extras["log"] = log_terms
        for key, value in log_terms.items():
            self.extras[key] = value
        self.extras["in_success_region"] = self.in_success_region.float().mean()
        return total_reward

    def _reset_idx(self, env_ids: Sequence[int] | None):
        self._ensure_cube_buffers()
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super(DextrahFrankaStarKittingEnv, self)._reset_idx(env_ids)

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
        spawn_xy += float(self.cfg.cube_spawn_xy_randomization) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x + 0.5 * self.cfg.cube_size)
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x - 0.5 * self.cfg.cube_size)
        min_y = float(-0.5 * self.cfg.table_size_y + 0.5 * self.cfg.cube_size)
        max_y = float(0.5 * self.cfg.table_size_y - 0.5 * self.cfg.cube_size)
        spawn_xy[:, 0] = torch.clamp(spawn_xy[:, 0], min=min_x, max=max_x)
        spawn_xy[:, 1] = torch.clamp(spawn_xy[:, 1], min=min_y, max=max_y)

        cube_pos = torch.zeros(num_ids, 3, device=self.device)
        cube_pos[:, 0:2] = spawn_xy
        cube_pos[:, 2] = float(self.cfg.cube_spawn_z)
        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = cube_pos + self.scene.env_origins[env_ids]
        object_state[:, 3] = 1.0
        self._cube.write_root_state_to_sim(object_state, env_ids=env_ids)

        self.cube_initial_pos[env_ids] = cube_pos
        self.cube_goal_pos[env_ids] = cube_pos
        self.cube_goal_pos[env_ids, 2] = cube_pos[:, 2] + float(self.cfg.cube_lift_height)
        self.has_lifted_cube[env_ids] = False
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
        obs = torch.cat(
            (
                joint_pos_scaled,
                joint_vel_scaled,
                self.ee_pos,
                self.ee_quat,
                self.left_finger_pos - self.cube_pos,
                self.right_finger_pos - self.cube_pos,
                self.cube_pos,
                self.cube_quat,
                self.cube_vel,
                self.cube_goal_pos,
                self.cube_pos - self.ee_pos,
                self.cube_goal_pos - self.cube_pos,
                self.cube_initial_pos,
                self.has_lifted_cube.float().unsqueeze(-1),
                self.in_success_region.float().unsqueeze(-1),
                self.time_in_success_region.unsqueeze(-1),
                self.gripper_width.unsqueeze(-1),
                self.ee_to_cube_dist.unsqueeze(-1),
                self.max_finger_to_cube_dist.unsqueeze(-1),
                self.finger_distance_asymmetry.unsqueeze(-1),
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
        self._ensure_cube_buffers()
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
            self.cube_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.cube_quat = torch.zeros(self.num_envs, 4, device=self.device)
            self.cube_vel = torch.zeros(self.num_envs, 6, device=self.device)

        self.ee_pos[env_ids] = ee_pos_w - env_origins
        self.ee_quat[env_ids] = ee_quat_w
        self.left_finger_pos[env_ids] = self._robot.data.body_pos_w[env_ids, self.left_finger_body_idx] - env_origins
        self.right_finger_pos[env_ids] = self._robot.data.body_pos_w[env_ids, self.right_finger_body_idx] - env_origins
        self.cube_pos[env_ids] = self._cube.data.root_pos_w[env_ids] - env_origins
        self.cube_quat[env_ids] = self._cube.data.root_quat_w[env_ids]
        self.cube_vel[env_ids] = self._cube.data.root_vel_w[env_ids]

        finger_center = 0.5 * (self.left_finger_pos[env_ids] + self.right_finger_pos[env_ids])
        self.gripper_width[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - self.right_finger_pos[env_ids], dim=-1
        )
        self.ee_to_cube_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - self.cube_pos[env_ids], dim=-1)
        self.finger_center_to_cube_dist[env_ids] = torch.norm(finger_center - self.cube_pos[env_ids], dim=-1)
        self.left_finger_to_cube_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - self.cube_pos[env_ids], dim=-1
        )
        self.right_finger_to_cube_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - self.cube_pos[env_ids], dim=-1
        )
        self.max_finger_to_cube_dist[env_ids] = torch.maximum(
            self.left_finger_to_cube_dist[env_ids], self.right_finger_to_cube_dist[env_ids]
        )
        self.finger_distance_asymmetry[env_ids] = torch.abs(
            self.left_finger_to_cube_dist[env_ids] - self.right_finger_to_cube_dist[env_ids]
        )
        self.hand_to_cube_mean_dist[env_ids] = 0.5 * (
            self.left_finger_to_cube_dist[env_ids] + self.right_finger_to_cube_dist[env_ids]
        )
        self.hand_to_cube_max_dist[env_ids] = self.max_finger_to_cube_dist[env_ids]
        self.cube_lift_height[env_ids] = torch.clamp(
            self.cube_pos[env_ids, 2] - self.cube_initial_pos[env_ids, 2], min=0.0
        )
        self.cube_xy_error[env_ids] = torch.norm(
            self.cube_pos[env_ids, :2] - self.cube_initial_pos[env_ids, :2], dim=-1
        )
        self.cube_goal_height_error[env_ids] = torch.abs(self.cube_goal_pos[env_ids, 2] - self.cube_pos[env_ids, 2])
        self.has_lifted_cube[env_ids] |= self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height)

        success = (
            (self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height))
            & (self.cube_xy_error[env_ids] <= float(self.cfg.cube_success_xy_tol))
            & (self.hand_to_cube_max_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
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

