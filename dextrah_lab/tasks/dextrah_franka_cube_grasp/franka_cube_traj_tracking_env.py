"""Franka cube grasp task variant with task-space trajectory tracking rewards."""

from __future__ import annotations

from collections.abc import Sequence

import torch

import isaaclab.utils.math as math_utils

from .franka_cube_grasp_env import DextrahFrankaCubeGraspEnv
from .franka_cube_traj_tracking_env_cfg import DextrahFrankaCubeTrajTrackingEnvCfg
from .franka_cube_traj_tracking_reference import (
    build_template_reference,
    load_reference_payload,
    validate_reference_payload,
)


class DextrahFrankaCubeTrajTrackingEnv(DextrahFrankaCubeGraspEnv):
    """Reward-only tracking variant for compact GraspGenX/cuRobo references."""

    cfg: DextrahFrankaCubeTrajTrackingEnvCfg

    def __init__(self, cfg: DextrahFrankaCubeTrajTrackingEnvCfg, render_mode: str | None = None, **kwargs):
        if bool(getattr(cfg, "trajectory_tracking_phase_observations", False)):
            raise ValueError(
                "trajectory_tracking_phase_observations changes the observation space and is intentionally "
                "not enabled in the reward-only tracking variant."
            )
        self._trajectory_tracking_initialized = False
        super().__init__(cfg, render_mode, **kwargs)
        self._init_trajectory_tracking_reference()
        self._trajectory_tracking_initialized = True

    def _init_trajectory_tracking_reference(self) -> None:
        if not bool(self.cfg.trajectory_tracking_enabled):
            return

        reference_path = str(getattr(self.cfg, "trajectory_tracking_reference_path", "") or "")
        if reference_path:
            payload = load_reference_payload(reference_path)
            self._trajectory_tracking_reference_source = reference_path
        else:
            payload = build_template_reference(
                cube_size_m=float(self.cfg.cube_size),
                table_surface_z_m=float(self.cfg.table_surface_z),
                cube_spawn_z_m=float(self.cfg.cube_spawn_z),
                max_gripper_width_m=float(self.cfg.max_gripper_width),
            )
            self._trajectory_tracking_reference_source = "builtin_manual_template_pending_validation"
        self._trajectory_tracking_reference_payload = payload
        self._trajectory_tracking_reference_validation_records = validate_reference_payload(payload)

        waypoints = payload["waypoints"]
        times = [float(waypoint["time_s"]) for waypoint in waypoints]
        pos_object = [waypoint["ee_pos_object"] for waypoint in waypoints]
        quat_object = [waypoint["ee_quat_object_wxyz"] for waypoint in waypoints]
        gripper_width = [
            float(waypoint.get("gripper_width", float(self.cfg.max_gripper_width))) for waypoint in waypoints
        ]
        tracking_weight = [float(waypoint.get("tracking_weight", 1.0)) for waypoint in waypoints]

        self.traj_ref_times = torch.tensor(times, dtype=torch.float32, device=self.device)
        self.traj_ref_pos_object = torch.tensor(pos_object, dtype=torch.float32, device=self.device)
        self.traj_ref_quat_object = torch.tensor(quat_object, dtype=torch.float32, device=self.device)
        self.traj_ref_quat_object = self.traj_ref_quat_object / torch.clamp(
            torch.norm(self.traj_ref_quat_object, dim=-1, keepdim=True),
            min=1.0e-8,
        )
        self.traj_ref_gripper_width = torch.tensor(gripper_width, dtype=torch.float32, device=self.device)
        self.traj_ref_tracking_weight = torch.tensor(tracking_weight, dtype=torch.float32, device=self.device)
        self.traj_ref_duration = float(times[-1])

        self.traj_target_ee_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.traj_target_ee_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.traj_target_ee_quat[:, 0] = 1.0
        self.traj_target_gripper_width = torch.full(
            (self.num_envs,), float(self.cfg.max_gripper_width), device=self.device
        )
        self.traj_target_tracking_weight = torch.zeros(self.num_envs, device=self.device)
        self.traj_phase_progress = torch.zeros(self.num_envs, device=self.device)
        self.traj_target_table_clearance = torch.zeros(self.num_envs, device=self.device)

    def _reset_idx(self, env_ids: Sequence[int] | None):
        super()._reset_idx(env_ids)
        if bool(getattr(self, "_trajectory_tracking_initialized", False)) and bool(self.cfg.trajectory_tracking_enabled):
            if env_ids is None:
                env_ids_tensor = self._robot._ALL_INDICES
            else:
                env_ids_tensor = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
            self._update_trajectory_tracking_targets(env_ids_tensor)

    def _get_rewards(self) -> torch.Tensor:
        total_reward = super()._get_rewards()
        if bool(self.cfg.trajectory_tracking_enabled):
            total_reward = total_reward + self._compute_trajectory_tracking_reward()
        return total_reward

    def _compute_curriculum_scale(self) -> float:
        start_weight = float(self.cfg.trajectory_tracking_start_weight)
        end_weight = float(self.cfg.trajectory_tracking_end_weight)
        curriculum_steps = float(self.cfg.trajectory_tracking_curriculum_steps)
        if curriculum_steps <= 0.0:
            return start_weight
        global_step = float(getattr(self, "common_step_counter", 0))
        progress = min(max(global_step / curriculum_steps, 0.0), 1.0)
        return start_weight + progress * (end_weight - start_weight)

    def _update_trajectory_tracking_targets(self, env_ids: torch.Tensor | None = None) -> None:
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES

        episode_time = torch.clamp(
            self.episode_length_buf[env_ids].to(torch.float32) * self.dt,
            min=0.0,
            max=self.traj_ref_duration,
        )
        right = torch.bucketize(episode_time, self.traj_ref_times)
        right = torch.clamp(right, min=1, max=self.traj_ref_times.numel() - 1)
        left = right - 1
        t0 = self.traj_ref_times[left]
        t1 = self.traj_ref_times[right]
        alpha = torch.clamp((episode_time - t0) / torch.clamp(t1 - t0, min=1.0e-6), 0.0, 1.0).unsqueeze(-1)

        pos_object = (1.0 - alpha) * self.traj_ref_pos_object[left] + alpha * self.traj_ref_pos_object[right]
        quat_left = self.traj_ref_quat_object[left]
        quat_right = self.traj_ref_quat_object[right]
        quat_dot = torch.sum(quat_left * quat_right, dim=-1, keepdim=True)
        quat_right = torch.where(quat_dot < 0.0, -quat_right, quat_right)
        quat_object = (1.0 - alpha) * quat_left + alpha * quat_right
        quat_object = quat_object / torch.clamp(torch.norm(quat_object, dim=-1, keepdim=True), min=1.0e-8)

        gripper_width = (1.0 - alpha.squeeze(-1)) * self.traj_ref_gripper_width[left] + alpha.squeeze(
            -1
        ) * self.traj_ref_gripper_width[right]
        tracking_weight = (1.0 - alpha.squeeze(-1)) * self.traj_ref_tracking_weight[left] + alpha.squeeze(
            -1
        ) * self.traj_ref_tracking_weight[right]

        if bool(self.cfg.trajectory_tracking_follow_current_cube_pose):
            object_pos = self.cube_pos[env_ids]
            object_quat = self.cube_quat[env_ids]
        else:
            object_pos = self.cube_initial_pos[env_ids]
            object_quat = self.cube_quat[env_ids]
        target_pos, target_quat = math_utils.combine_frame_transforms(object_pos, object_quat, pos_object, quat_object)

        self.traj_target_ee_pos[env_ids] = target_pos
        self.traj_target_ee_quat[env_ids] = target_quat / torch.clamp(
            torch.norm(target_quat, dim=-1, keepdim=True),
            min=1.0e-8,
        )
        self.traj_target_gripper_width[env_ids] = gripper_width
        self.traj_target_tracking_weight[env_ids] = tracking_weight
        self.traj_phase_progress[env_ids] = episode_time / max(self.traj_ref_duration, 1.0e-6)
        self.traj_target_table_clearance[env_ids] = target_pos[:, 2] - float(self.cfg.table_surface_z)

    def _compute_trajectory_tracking_reward(self) -> torch.Tensor:
        self._update_trajectory_tracking_targets()
        curriculum_scale = self._compute_curriculum_scale()
        phase_weight = self.traj_target_tracking_weight * curriculum_scale

        position_error = torch.norm(self.ee_pos - self.traj_target_ee_pos, dim=-1)
        position_reward = (
            float(self.cfg.trajectory_tracking_position_weight)
            * phase_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_position_sharpness) * position_error)
        )

        ee_quat = self.ee_quat / torch.clamp(torch.norm(self.ee_quat, dim=-1, keepdim=True), min=1.0e-8)
        quat_alignment = torch.abs(torch.sum(ee_quat * self.traj_target_ee_quat, dim=-1)).clamp(0.0, 1.0)
        orientation_error = 1.0 - quat_alignment
        orientation_reward = (
            float(self.cfg.trajectory_tracking_orientation_weight)
            * phase_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_orientation_sharpness) * orientation_error)
        )

        gripper_error = torch.abs(self.gripper_width - self.traj_target_gripper_width)
        gripper_reward = (
            float(self.cfg.trajectory_tracking_gripper_weight)
            * phase_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_gripper_sharpness) * gripper_error)
        )

        tracking_reward = position_reward + orientation_reward + gripper_reward
        min_target_clearance = float(self.cfg.trajectory_tracking_min_target_table_clearance)
        unsafe_target = self.traj_target_table_clearance < min_target_clearance

        log_terms = self.extras.setdefault("log", {})
        log_terms.update(
            {
                "cube_traj_tracking_reward": tracking_reward.mean(),
                "cube_traj_tracking_position_reward": position_reward.mean(),
                "cube_traj_tracking_orientation_reward": orientation_reward.mean(),
                "cube_traj_tracking_gripper_reward": gripper_reward.mean(),
                "cube_traj_tracking_position_error": position_error.mean(),
                "cube_traj_tracking_orientation_error": orientation_error.mean(),
                "cube_traj_tracking_gripper_error": gripper_error.mean(),
                "cube_traj_tracking_phase_progress": self.traj_phase_progress.mean(),
                "cube_traj_tracking_curriculum_scale": torch.tensor(curriculum_scale, device=self.device),
                "cube_traj_tracking_target_table_clearance": self.traj_target_table_clearance.mean(),
                "cube_traj_tracking_unsafe_target_rate": unsafe_target.float().mean(),
            }
        )
        for key, value in log_terms.items():
            self.extras[key] = value
        return tracking_reward

    def trajectory_tracking_reference_summary(self) -> dict[str, object]:
        payload = getattr(self, "_trajectory_tracking_reference_payload", {})
        source = payload.get("source", {}) if isinstance(payload, dict) else {}
        tracking = payload.get("tracking", {}) if isinstance(payload, dict) else {}
        records = getattr(self, "_trajectory_tracking_reference_validation_records", [])
        failed_records = [record.get("name", "<unnamed>") for record in records if not bool(record.get("passed"))]
        return {
            "enabled": bool(self.cfg.trajectory_tracking_enabled),
            "source": getattr(self, "_trajectory_tracking_reference_source", None),
            "source_tag": source.get("tag") if isinstance(source, dict) else None,
            "planner": source.get("planner") if isinstance(source, dict) else None,
            "curobo_validated": bool(source.get("curobo_validated", False)) if isinstance(source, dict) else False,
            "graspgenx_source": bool(source.get("graspgenx_source", False)) if isinstance(source, dict) else False,
            "waypoint_count": int(self.traj_ref_times.numel()) if hasattr(self, "traj_ref_times") else 0,
            "duration_s": float(self.traj_ref_duration) if hasattr(self, "traj_ref_duration") else 0.0,
            "transform_policy": tracking.get("transform_policy") if isinstance(tracking, dict) else None,
            "joint_trajectory_policy": tracking.get("joint_trajectory_policy") if isinstance(tracking, dict) else None,
            "validation_passed": len(failed_records) == 0,
            "failed_validation_records": failed_records,
        }
