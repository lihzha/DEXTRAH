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
        source_gripper_width = [
            float(waypoint.get("gripper_width", float(self.cfg.max_gripper_width))) for waypoint in waypoints
        ]
        min_target_gripper_width = max(
            0.0,
            float(getattr(self.cfg, "trajectory_tracking_min_target_gripper_width", 0.0) or 0.0),
        )
        max_target_gripper_width = float(self.cfg.max_gripper_width)
        if min_target_gripper_width > max_target_gripper_width:
            raise ValueError(
                "trajectory_tracking_min_target_gripper_width must not exceed max_gripper_width "
                f"({min_target_gripper_width} > {max_target_gripper_width})."
            )
        gripper_width = [
            min(max(width, min_target_gripper_width), max_target_gripper_width) for width in source_gripper_width
        ]
        tracking_weight = [float(waypoint.get("tracking_weight", 1.0)) for waypoint in waypoints]
        source_start_time = float(times[0])
        source_end_time = float(times[-1])
        source_duration = max(source_end_time - source_start_time, 0.0)
        runtime_duration_cfg = float(getattr(self.cfg, "trajectory_tracking_reference_duration_s", 0.0) or 0.0)
        if runtime_duration_cfg > 0.0 and source_duration > 1.0e-6:
            runtime_times = [
                (float(time_s) - source_start_time) / source_duration * runtime_duration_cfg for time_s in times
            ]
            retime_policy = "normalize_to_configured_runtime_duration"
        else:
            runtime_times = times
            retime_policy = "use_source_timestamps"

        self.traj_ref_source_start_time = source_start_time
        self.traj_ref_source_end_time = source_end_time
        self.traj_ref_source_duration = source_duration
        self.traj_ref_runtime_duration_cfg = runtime_duration_cfg
        self.traj_ref_retime_policy = retime_policy
        self.traj_ref_gripper_width_source_min = min(source_gripper_width)
        self.traj_ref_gripper_width_source_max = max(source_gripper_width)
        self.traj_ref_gripper_width_runtime_min = min(gripper_width)
        self.traj_ref_gripper_width_runtime_max = max(gripper_width)
        self.traj_ref_min_target_gripper_width = min_target_gripper_width
        self.traj_ref_gripper_schedule_policy = (
            "clamp_source_width_to_min_target_gripper_width"
            if min_target_gripper_width > 0.0
            else "use_source_gripper_width"
        )

        self.traj_ref_times = torch.tensor(runtime_times, dtype=torch.float32, device=self.device)
        self.traj_ref_pos_object = torch.tensor(pos_object, dtype=torch.float32, device=self.device)
        self.traj_ref_quat_object = torch.tensor(quat_object, dtype=torch.float32, device=self.device)
        self.traj_ref_quat_object = self.traj_ref_quat_object / torch.clamp(
            torch.norm(self.traj_ref_quat_object, dim=-1, keepdim=True),
            min=1.0e-8,
        )
        self.traj_ref_gripper_width = torch.tensor(gripper_width, dtype=torch.float32, device=self.device)
        self.traj_ref_tracking_weight = torch.tensor(tracking_weight, dtype=torch.float32, device=self.device)
        self.traj_ref_duration = float(runtime_times[-1])

        self.traj_target_ee_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.traj_target_ee_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.traj_target_ee_quat[:, 0] = 1.0
        self.traj_target_gripper_width = torch.full(
            (self.num_envs,), float(self.cfg.max_gripper_width), device=self.device
        )
        self.traj_target_tracking_weight = torch.zeros(self.num_envs, device=self.device)
        self.traj_phase_progress = torch.zeros(self.num_envs, device=self.device)
        self.traj_target_table_clearance = torch.zeros(self.num_envs, device=self.device)
        self.traj_effective_tracking_weight = torch.zeros(self.num_envs, device=self.device)
        self.traj_target_safe_mask = torch.ones(self.num_envs, dtype=torch.bool, device=self.device)
        self.traj_reference_object_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self.traj_reference_object_quat[:, 0] = 1.0
        if hasattr(self, "cube_quat"):
            self.traj_reference_object_quat[:] = self.cube_quat / torch.clamp(
                torch.norm(self.cube_quat, dim=-1, keepdim=True),
                min=1.0e-8,
            )

    def _reset_idx(self, env_ids: Sequence[int] | None):
        super()._reset_idx(env_ids)
        if bool(getattr(self, "_trajectory_tracking_initialized", False)) and bool(self.cfg.trajectory_tracking_enabled):
            if env_ids is None:
                env_ids_tensor = self._robot._ALL_INDICES
            else:
                env_ids_tensor = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
            reset_quat = self.cube_quat[env_ids_tensor]
            self.traj_reference_object_quat[env_ids_tensor] = reset_quat / torch.clamp(
                torch.norm(reset_quat, dim=-1, keepdim=True),
                min=1.0e-8,
            )
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
            object_quat = self.traj_reference_object_quat[env_ids]
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
        min_target_clearance = float(self.cfg.trajectory_tracking_min_target_table_clearance)
        unsafe_target = self.traj_target_table_clearance < min_target_clearance
        safe_target = ~unsafe_target
        effective_phase_weight = torch.where(safe_target, phase_weight, torch.zeros_like(phase_weight))
        self.traj_target_safe_mask[:] = safe_target
        self.traj_effective_tracking_weight[:] = effective_phase_weight

        reference_reweight_phase_start = float(
            getattr(self.cfg, "trajectory_tracking_reference_reweight_phase_start", 1.0)
        )
        late_reference_scale = float(getattr(self.cfg, "trajectory_tracking_reference_late_weight_scale", 1.0))
        reference_phase_gate = torch.clamp(
            (self.traj_phase_progress - reference_reweight_phase_start)
            / max(1.0 - reference_reweight_phase_start, 1.0e-6),
            0.0,
            1.0,
        )
        reference_reweight = 1.0 + reference_phase_gate * (late_reference_scale - 1.0)
        tracking_term_weight = effective_phase_weight * reference_reweight

        position_error = torch.norm(self.ee_pos - self.traj_target_ee_pos, dim=-1)
        position_reward = (
            float(self.cfg.trajectory_tracking_position_weight)
            * tracking_term_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_position_sharpness) * position_error)
        )

        ee_quat = self.ee_quat / torch.clamp(torch.norm(self.ee_quat, dim=-1, keepdim=True), min=1.0e-8)
        quat_alignment = torch.abs(torch.sum(ee_quat * self.traj_target_ee_quat, dim=-1)).clamp(0.0, 1.0)
        orientation_error = 1.0 - quat_alignment
        orientation_reward = (
            float(self.cfg.trajectory_tracking_orientation_weight)
            * tracking_term_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_orientation_sharpness) * orientation_error)
        )

        gripper_error = torch.abs(self.gripper_width - self.traj_target_gripper_width)
        gripper_reward = (
            float(self.cfg.trajectory_tracking_gripper_weight)
            * tracking_term_weight
            * torch.exp(-float(self.cfg.trajectory_tracking_gripper_sharpness) * gripper_error)
        )

        max_gripper_width = max(float(self.cfg.max_gripper_width), 1.0e-6)
        closed_width_span = max(
            max_gripper_width - float(getattr(self.cfg, "trajectory_tracking_min_target_gripper_width", 0.0) or 0.0),
            1.0e-6,
        )
        closed_target_gate = torch.clamp((max_gripper_width - self.traj_target_gripper_width) / closed_width_span, 0.0, 1.0)
        close_phase_start = float(getattr(self.cfg, "trajectory_tracking_close_action_phase_start", 0.0))
        close_phase_gate = torch.clamp(
            (self.traj_phase_progress - close_phase_start) / max(1.0 - close_phase_start, 1.0e-6),
            0.0,
            1.0,
        )
        lift_phase_start = float(getattr(self.cfg, "trajectory_tracking_lift_action_phase_start", 0.0))
        lift_phase_gate = torch.clamp(
            (self.traj_phase_progress - lift_phase_start) / max(1.0 - lift_phase_start, 1.0e-6),
            0.0,
            1.0,
        )
        contact_gate_distance = float(getattr(self.cfg, "trajectory_tracking_contact_gate_max_finger_dist", 0.14))
        contact_gate_width = max(float(getattr(self.cfg, "trajectory_tracking_contact_gate_width", 0.08)), 1.0e-6)
        contact_distance_gate = torch.clamp(
            (contact_gate_distance - self.max_finger_to_cube_dist) / contact_gate_width,
            0.0,
            1.0,
        )
        finger_balance_gate = 1.0 - torch.clamp((self.finger_distance_asymmetry - 0.025) / 0.075, 0.0, 1.0)
        contact_gate = contact_distance_gate * (0.25 + 0.75 * finger_balance_gate)
        close_action_signal = torch.clamp(-self.actions[:, 6], 0.0, 1.0)
        lift_action_signal = torch.clamp(self.actions[:, 2], 0.0, 1.0)
        close_action_reward_ceiling = (
            float(getattr(self.cfg, "trajectory_tracking_close_action_weight", 0.0))
            * effective_phase_weight
            * closed_target_gate
            * close_phase_gate
            * contact_gate
        )
        lift_action_reward_ceiling = (
            float(getattr(self.cfg, "trajectory_tracking_lift_action_weight", 0.0))
            * effective_phase_weight
            * closed_target_gate
            * lift_phase_gate
            * contact_gate
        )
        close_action_reward = close_action_reward_ceiling * close_action_signal
        lift_action_reward = lift_action_reward_ceiling * lift_action_signal
        close_action_utilization = torch.where(
            close_action_reward_ceiling > 1.0e-8,
            close_action_reward / torch.clamp(close_action_reward_ceiling, min=1.0e-8),
            torch.zeros_like(close_action_reward),
        )
        lift_action_utilization = torch.where(
            lift_action_reward_ceiling > 1.0e-8,
            lift_action_reward / torch.clamp(lift_action_reward_ceiling, min=1.0e-8),
            torch.zeros_like(lift_action_reward),
        )

        tracking_reward = position_reward + orientation_reward + gripper_reward + close_action_reward + lift_action_reward

        log_terms = self.extras.setdefault("log", {})
        log_terms.update(
            {
                "cube_traj_tracking_reward": tracking_reward.mean(),
                "cube_traj_tracking_position_reward": position_reward.mean(),
                "cube_traj_tracking_orientation_reward": orientation_reward.mean(),
                "cube_traj_tracking_gripper_reward": gripper_reward.mean(),
                "cube_traj_tracking_close_action_reward": close_action_reward.mean(),
                "cube_traj_tracking_lift_action_reward": lift_action_reward.mean(),
                "cube_traj_tracking_close_action_reward_ceiling": close_action_reward_ceiling.mean(),
                "cube_traj_tracking_lift_action_reward_ceiling": lift_action_reward_ceiling.mean(),
                "cube_traj_tracking_close_action_utilization": close_action_utilization.mean(),
                "cube_traj_tracking_lift_action_utilization": lift_action_utilization.mean(),
                "cube_traj_tracking_position_error": position_error.mean(),
                "cube_traj_tracking_orientation_error": orientation_error.mean(),
                "cube_traj_tracking_gripper_error": gripper_error.mean(),
                "cube_traj_tracking_closed_target_gate": closed_target_gate.mean(),
                "cube_traj_tracking_close_phase_gate": close_phase_gate.mean(),
                "cube_traj_tracking_lift_phase_gate": lift_phase_gate.mean(),
                "cube_traj_tracking_contact_gate": contact_gate.mean(),
                "cube_traj_tracking_contact_distance_gate": contact_distance_gate.mean(),
                "cube_traj_tracking_finger_balance_gate": finger_balance_gate.mean(),
                "cube_traj_tracking_action_close": close_action_signal.mean(),
                "cube_traj_tracking_action_up": lift_action_signal.mean(),
                "cube_traj_tracking_action_z": self.actions[:, 2].mean(),
                "cube_traj_tracking_gripper_action": self.actions[:, 6].mean(),
                "cube_traj_tracking_phase_progress": self.traj_phase_progress.mean(),
                "cube_traj_tracking_curriculum_scale": torch.tensor(curriculum_scale, device=self.device),
                "cube_traj_tracking_phase_weight": phase_weight.mean(),
                "cube_traj_tracking_effective_phase_weight": effective_phase_weight.mean(),
                "cube_traj_tracking_reference_reweight": reference_reweight.mean(),
                "cube_traj_tracking_tracking_term_weight": tracking_term_weight.mean(),
                "cube_traj_tracking_target_table_clearance": self.traj_target_table_clearance.mean(),
                "cube_traj_tracking_target_table_clearance_min": self.traj_target_table_clearance.min(),
                "cube_traj_tracking_safe_target_rate": safe_target.float().mean(),
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
        runtime_object_pose_policy = (
            "current_cube_pose" if bool(self.cfg.trajectory_tracking_follow_current_cube_pose) else "reset_cube_pose"
        )
        return {
            "enabled": bool(self.cfg.trajectory_tracking_enabled),
            "source": getattr(self, "_trajectory_tracking_reference_source", None),
            "source_tag": source.get("tag") if isinstance(source, dict) else None,
            "planner": source.get("planner") if isinstance(source, dict) else None,
            "curobo_validated": bool(source.get("curobo_validated", False)) if isinstance(source, dict) else False,
            "graspgenx_source": bool(source.get("graspgenx_source", False)) if isinstance(source, dict) else False,
            "waypoint_count": int(self.traj_ref_times.numel()) if hasattr(self, "traj_ref_times") else 0,
            "duration_s": float(self.traj_ref_duration) if hasattr(self, "traj_ref_duration") else 0.0,
            "runtime_duration_s": float(self.traj_ref_duration) if hasattr(self, "traj_ref_duration") else 0.0,
            "source_duration_s": float(getattr(self, "traj_ref_source_duration", 0.0)),
            "source_start_time_s": float(getattr(self, "traj_ref_source_start_time", 0.0)),
            "source_end_time_s": float(getattr(self, "traj_ref_source_end_time", 0.0)),
            "configured_runtime_duration_s": float(getattr(self, "traj_ref_runtime_duration_cfg", 0.0)),
            "runtime_retime_policy": getattr(self, "traj_ref_retime_policy", "uninitialized"),
            "source_gripper_width_min_m": float(getattr(self, "traj_ref_gripper_width_source_min", 0.0)),
            "source_gripper_width_max_m": float(getattr(self, "traj_ref_gripper_width_source_max", 0.0)),
            "runtime_gripper_width_min_m": float(getattr(self, "traj_ref_gripper_width_runtime_min", 0.0)),
            "runtime_gripper_width_max_m": float(getattr(self, "traj_ref_gripper_width_runtime_max", 0.0)),
            "min_target_gripper_width_m": float(getattr(self, "traj_ref_min_target_gripper_width", 0.0)),
            "gripper_schedule_policy": getattr(self, "traj_ref_gripper_schedule_policy", "uninitialized"),
            "transform_policy": tracking.get("transform_policy") if isinstance(tracking, dict) else None,
            "joint_trajectory_policy": tracking.get("joint_trajectory_policy") if isinstance(tracking, dict) else None,
            "runtime_object_pose_policy": runtime_object_pose_policy,
            "unsafe_target_reward_policy": "zero_tracking_weight_below_min_target_table_clearance",
            "min_target_table_clearance_m": float(self.cfg.trajectory_tracking_min_target_table_clearance),
            "validation_passed": len(failed_records) == 0,
            "failed_validation_records": failed_records,
        }
