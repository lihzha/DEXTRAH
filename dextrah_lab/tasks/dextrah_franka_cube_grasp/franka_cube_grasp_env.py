"""DirectRLEnv for Franka single-cube grasp-and-lift."""

from __future__ import annotations

from collections.abc import Sequence
import json
import math
from pathlib import Path

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


def _yaw_quat_wxyz(yaw_rad: torch.Tensor) -> torch.Tensor:
    quat = torch.zeros(yaw_rad.shape[0], 4, device=yaw_rad.device)
    quat[:, 0] = torch.cos(0.5 * yaw_rad)
    quat[:, 3] = torch.sin(0.5 * yaw_rad)
    return quat


class DextrahFrankaCubeGraspEnv(DextrahFrankaStarKittingEnv):
    """Franka task: pick up the procedural cube used by the KUKA cube baseline."""

    cfg: DextrahFrankaCubeGraspEnvCfg

    def __init__(self, cfg: DextrahFrankaCubeGraspEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        self._ensure_cube_buffers()
        self._setup_grasp_prior_reset()

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
        if not hasattr(self, "cube_initial_pos"):
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
            self.finger_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.finger_table_clearance_violation = torch.zeros(self.num_envs, device=self.device)
        if not hasattr(self, "grasp_prior_reset_attempted"):
            self.grasp_prior_reset_attempted = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
            self.grasp_prior_reset_success = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
            self.grasp_prior_reset_farther = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
            self.grasp_prior_reset_sample_index = torch.full(
                (self.num_envs,), -1, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_pos_error = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_rot_error = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_exact_tool_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_pregrasp_tool_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_finger_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_finger_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_cube_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_cube_quat_w = torch.zeros(self.num_envs, 4, device=self.device)
            self.grasp_prior_reset_exact_tool_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_pregrasp_tool_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_exact_ee_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_target_ee_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_offset_dir_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_exact_tool_quat_w = torch.zeros(self.num_envs, 4, device=self.device)
            self.grasp_prior_reset_pregrasp_tool_quat_w = torch.zeros(self.num_envs, 4, device=self.device)
            self.grasp_prior_reset_exact_ee_quat_w = torch.zeros(self.num_envs, 4, device=self.device)
            self.grasp_prior_reset_target_ee_quat_w = torch.zeros(self.num_envs, 4, device=self.device)
            self.grasp_prior_reset_left_finger_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_right_finger_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_left_tip_proxy_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_right_tip_proxy_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_projected_exact_left_tip_proxy_pos = torch.zeros(
                self.num_envs, 3, device=self.device
            )
            self.grasp_prior_reset_projected_exact_right_tip_proxy_pos = torch.zeros(
                self.num_envs, 3, device=self.device
            )
            self.grasp_prior_reset_gripper_width = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_open_width_margin = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_offset_radial_dot = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_offset_radial_angle = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_exact_ee_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_pregrasp_ee_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_quality_reference_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_contact_reference_pos_w = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_contact_reference_pos_o = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_current_contact_reference_pos = torch.zeros(self.num_envs, 3, device=self.device)
            self.grasp_prior_reset_contact_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_center_gate_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_has_contact_location = torch.zeros(
                self.num_envs, dtype=torch.bool, device=self.device
            )
            self.grasp_prior_reset_candidate_topdown_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_candidate_center_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_candidate_width_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_candidate_table_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_candidate_valid_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_candidate_fallback_count = torch.zeros(
                self.num_envs, dtype=torch.long, device=self.device
            )
            self.grasp_prior_reset_projected_exact_finger_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_max_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_pregrasp_tip_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_quality_success = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        if not hasattr(self, "grasp_prior_action_warmstart_active"):
            action_dim = int(self.cfg.action_space)
            self.grasp_prior_action_warmstart_active = torch.zeros(
                self.num_envs, dtype=torch.bool, device=self.device
            )
            self.grasp_prior_action_warmstart_phase = torch.full(
                (self.num_envs,), -1, dtype=torch.long, device=self.device
            )
            self.grasp_prior_action_warmstart_policy_actions = torch.zeros(
                self.num_envs, action_dim, device=self.device
            )
            self.grasp_prior_action_warmstart_applied_actions = torch.zeros(
                self.num_envs, action_dim, device=self.device
            )
            self.grasp_prior_action_warmstart_policy_action_z = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_policy_gripper_action = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_applied_action_z = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_applied_gripper_action = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_action_delta_abs = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_exact_ee_error = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_close_width_target = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_warmstart_reference_finger_center_dist = torch.zeros(
                self.num_envs, device=self.device
            )
            self.grasp_prior_action_warmstart_close_latched = torch.zeros(
                self.num_envs, dtype=torch.bool, device=self.device
            )
            self.grasp_prior_action_warmstart_lift_latched = torch.zeros(
                self.num_envs, dtype=torch.bool, device=self.device
            )
        if not hasattr(self, "grasp_prior_action_prior_reward"):
            action_dim = int(self.cfg.action_space)
            self.grasp_prior_action_prior_active = torch.zeros(
                self.num_envs, dtype=torch.bool, device=self.device
            )
            self.grasp_prior_action_prior_phase = torch.full(
                (self.num_envs,), -1, dtype=torch.long, device=self.device
            )
            self.grasp_prior_action_prior_teacher_actions = torch.zeros(
                self.num_envs, action_dim, device=self.device
            )
            self.grasp_prior_action_prior_delta_abs = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_prior_reward = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_prior_teacher_action_z = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_prior_teacher_gripper_action = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_action_prior_exact_ee_error = torch.zeros(self.num_envs, device=self.device)

    def _setup_grasp_prior_reset(self) -> None:
        self._grasp_prior_reset_enabled = bool(self.cfg.grasp_prior_reset_enabled)
        self._grasp_prior_grasps_object: torch.Tensor | None = None
        self._grasp_prior_confidence: torch.Tensor | None = None
        self._grasp_prior_grasp_to_tool = torch.eye(4, device=self.device)
        self._grasp_prior_metadata: dict[str, object] = {}
        if not self._grasp_prior_reset_enabled:
            return

        library_path = Path(str(self.cfg.grasp_prior_library_path)).expanduser()
        if not library_path.is_file():
            raise FileNotFoundError(
                "grasp_prior_reset_enabled=True requires a compact grasp library at "
                f"grasp_prior_library_path, got {library_path}"
            )
        self._load_grasp_prior_library(library_path)

    @staticmethod
    def _json_npz_scalar(value) -> object:
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def _load_grasp_prior_library(self, path: Path) -> None:
        import numpy as np

        metadata: dict[str, object] = {}
        if path.suffix.lower() == ".npz":
            with np.load(path, allow_pickle=False) as data:
                if "metadata_json" in data.files:
                    metadata = json.loads(str(self._json_npz_scalar(data["metadata_json"])))
                for key in ("cube_size_m", "gripper_name", "tool_frame"):
                    if key in data.files:
                        metadata.setdefault(key, self._json_npz_scalar(data[key]))
                grasps_object = data["grasps_object"]
                confidence = data["confidence"] if "confidence" in data.files else None
                grasp_to_tool = (
                    data["grasp_to_tool_transform"]
                    if "grasp_to_tool_transform" in data.files
                    else np.eye(4, dtype=np.float32)
                )
        elif path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object in grasp prior library: {path}")
            metadata = dict(payload.get("metadata", {}))
            for key in ("cube_size_m", "gripper_name", "tool_frame"):
                if key in payload:
                    metadata.setdefault(key, payload[key])
            grasps_object = payload["grasps_object"]
            confidence = payload.get("confidence")
            grasp_to_tool = payload.get("grasp_to_tool_transform", np.eye(4, dtype=np.float32))
        else:
            raise ValueError(f"Unsupported grasp prior library extension for {path}; expected .npz or .json")

        grasps_tensor = torch.as_tensor(grasps_object, dtype=torch.float32, device=self.device)
        if grasps_tensor.ndim != 3 or tuple(grasps_tensor.shape[1:]) != (4, 4) or grasps_tensor.shape[0] == 0:
            raise ValueError(f"grasps_object must have shape (N, 4, 4), got {tuple(grasps_tensor.shape)}")
        if not torch.isfinite(grasps_tensor).all().item():
            raise ValueError(f"grasps_object contains NaN/Inf values: {path}")
        expected_bottom = torch.tensor((0.0, 0.0, 0.0, 1.0), device=self.device)
        if not torch.allclose(grasps_tensor[:, 3, :], expected_bottom.expand_as(grasps_tensor[:, 3, :]), atol=1.0e-4):
            raise ValueError(f"grasps_object transforms must have homogeneous bottom rows: {path}")

        grasp_to_tool_tensor = torch.as_tensor(grasp_to_tool, dtype=torch.float32, device=self.device)
        if tuple(grasp_to_tool_tensor.shape) != (4, 4):
            raise ValueError(
                f"grasp_to_tool_transform must have shape (4, 4), got {tuple(grasp_to_tool_tensor.shape)}"
            )
        if not torch.isfinite(grasp_to_tool_tensor).all().item():
            raise ValueError(f"grasp_to_tool_transform contains NaN/Inf values: {path}")

        cube_size_m = metadata.get("cube_size_m")
        if cube_size_m is not None and abs(float(cube_size_m) - float(self.cfg.cube_size)) > 1.0e-4:
            raise ValueError(
                f"Grasp prior cube_size_m={cube_size_m} does not match task cube_size={self.cfg.cube_size}"
            )
        tool_frame = str(metadata.get("tool_frame", "panda_hand"))
        if tool_frame != "panda_hand":
            raise ValueError(
                f"Variant 1 expects GraspGenX tool_frame='panda_hand' for DEXTRAH Franka, got {tool_frame!r}"
            )

        if confidence is None:
            confidence_tensor = torch.ones(grasps_tensor.shape[0], dtype=torch.float32, device=self.device)
        else:
            confidence_tensor = torch.as_tensor(confidence, dtype=torch.float32, device=self.device).flatten()
            if confidence_tensor.shape[0] != grasps_tensor.shape[0]:
                raise ValueError(
                    "confidence length must match grasps_object count, got "
                    f"{confidence_tensor.shape[0]} vs {grasps_tensor.shape[0]}"
                )

        self._grasp_prior_grasps_object = grasps_tensor.contiguous()
        self._grasp_prior_confidence = confidence_tensor.contiguous()
        self._grasp_prior_grasp_to_tool = grasp_to_tool_tensor.contiguous()
        self._grasp_prior_metadata = metadata

    def _grasp_prior_object_size(self, env_ids: torch.Tensor) -> torch.Tensor:
        return torch.full((env_ids.numel(),), float(self.cfg.cube_size), dtype=torch.float32, device=self.device)

    def _grasp_prior_required_open_width(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        return self._grasp_prior_object_size(env_ids)

    def _reset_grasp_prior_metrics(self, env_ids: torch.Tensor) -> None:
        self.grasp_prior_reset_attempted[env_ids] = False
        self.grasp_prior_reset_success[env_ids] = False
        self.grasp_prior_reset_farther[env_ids] = False
        self.grasp_prior_reset_sample_index[env_ids] = -1
        self.grasp_prior_reset_pos_error[env_ids] = 0.0
        self.grasp_prior_reset_rot_error[env_ids] = 0.0
        self.grasp_prior_reset_exact_tool_dist[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_tool_dist[env_ids] = 0.0
        self.grasp_prior_reset_finger_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_finger_table_clearance[env_ids] = 0.0
        self.grasp_prior_reset_cube_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_cube_quat_w[env_ids] = 0.0
        self.grasp_prior_reset_exact_tool_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_tool_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_exact_ee_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_target_ee_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_offset_dir_w[env_ids] = 0.0
        self.grasp_prior_reset_exact_tool_quat_w[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_tool_quat_w[env_ids] = 0.0
        self.grasp_prior_reset_exact_ee_quat_w[env_ids] = 0.0
        self.grasp_prior_reset_target_ee_quat_w[env_ids] = 0.0
        self.grasp_prior_reset_left_finger_pos[env_ids] = 0.0
        self.grasp_prior_reset_right_finger_pos[env_ids] = 0.0
        self.grasp_prior_reset_left_tip_proxy_pos[env_ids] = 0.0
        self.grasp_prior_reset_right_tip_proxy_pos[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_left_tip_proxy_pos[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_right_tip_proxy_pos[env_ids] = 0.0
        self.grasp_prior_reset_gripper_width[env_ids] = 0.0
        self.grasp_prior_reset_open_width_margin[env_ids] = 0.0
        self.grasp_prior_reset_offset_radial_dot[env_ids] = 0.0
        self.grasp_prior_reset_offset_radial_angle[env_ids] = 0.0
        self.grasp_prior_reset_exact_ee_dist[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_ee_dist[env_ids] = 0.0
        self.grasp_prior_reset_quality_reference_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_contact_reference_pos_w[env_ids] = 0.0
        self.grasp_prior_reset_contact_reference_pos_o[env_ids] = 0.0
        self.grasp_prior_current_contact_reference_pos[env_ids] = 0.0
        self.grasp_prior_reset_contact_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_center_gate_dist[env_ids] = 0.0
        self.grasp_prior_reset_has_contact_location[env_ids] = False
        self.grasp_prior_reset_candidate_topdown_count[env_ids] = 0
        self.grasp_prior_reset_candidate_center_count[env_ids] = 0
        self.grasp_prior_reset_candidate_width_count[env_ids] = 0
        self.grasp_prior_reset_candidate_table_count[env_ids] = 0
        self.grasp_prior_reset_candidate_valid_count[env_ids] = 0
        self.grasp_prior_reset_candidate_fallback_count[env_ids] = 0
        self.grasp_prior_reset_projected_exact_finger_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_max_dist[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_tip_table_clearance[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_table_clearance[env_ids] = 0.0
        self.grasp_prior_reset_quality_success[env_ids] = False
        if hasattr(self, "grasp_prior_action_warmstart_close_latched"):
            self.grasp_prior_action_warmstart_close_latched[env_ids] = False
        if hasattr(self, "grasp_prior_action_warmstart_lift_latched"):
            self.grasp_prior_action_warmstart_lift_latched[env_ids] = False
        if hasattr(self, "grasp_prior_action_warmstart_reference_finger_center_dist"):
            self.grasp_prior_action_warmstart_reference_finger_center_dist[env_ids] = 0.0

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

    def _compose_grasp_prior_targets(
        self,
        env_ids: torch.Tensor,
        cube_pos: torch.Tensor,
        cube_quat: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        if self._grasp_prior_grasps_object is None:
            raise RuntimeError("Grasp prior reset is enabled but no grasp library is loaded")

        num_ids = int(env_ids.numel())
        sample_indices = torch.randint(
            self._grasp_prior_grasps_object.shape[0],
            (num_ids,),
            device=self.device,
        )
        object_grasp_t = self._grasp_prior_grasps_object[sample_indices]
        world_object_t = torch.eye(4, device=self.device).repeat(num_ids, 1, 1)
        cube_pos_w = cube_pos + self.scene.env_origins[env_ids]
        world_object_t[:, :3, :3] = math_utils.matrix_from_quat(cube_quat)
        world_object_t[:, :3, 3] = cube_pos_w
        world_grasp_t = torch.bmm(world_object_t, object_grasp_t)
        world_tool_t = torch.bmm(
            world_grasp_t,
            self._grasp_prior_grasp_to_tool.unsqueeze(0).expand(num_ids, -1, -1),
        )

        exact_tool_pos_w = world_tool_t[:, :3, 3]
        tool_z_axis_w = world_tool_t[:, :3, 2]
        tool_z_axis_w = tool_z_axis_w / torch.clamp(torch.norm(tool_z_axis_w, dim=-1, keepdim=True), min=1.0e-6)
        pregrasp_offset = abs(float(self.cfg.grasp_prior_pregrasp_offset))
        plus_tool_pos_w = exact_tool_pos_w + pregrasp_offset * tool_z_axis_w
        minus_tool_pos_w = exact_tool_pos_w - pregrasp_offset * tool_z_axis_w
        exact_tool_dist = torch.norm(exact_tool_pos_w - cube_pos_w, dim=-1)
        plus_tool_dist = torch.norm(plus_tool_pos_w - cube_pos_w, dim=-1)
        minus_tool_dist = torch.norm(minus_tool_pos_w - cube_pos_w, dim=-1)
        use_plus = plus_tool_dist >= minus_tool_dist
        pregrasp_offset_dir_w = torch.where(use_plus.unsqueeze(-1), tool_z_axis_w, -tool_z_axis_w)
        pregrasp_tool_pos_w = exact_tool_pos_w + pregrasp_offset * pregrasp_offset_dir_w
        pregrasp_tool_dist = torch.where(use_plus, plus_tool_dist, minus_tool_dist)
        if pregrasp_offset <= 1.0e-6:
            pregrasp_farther = torch.ones_like(pregrasp_tool_dist, dtype=torch.bool)
        else:
            pregrasp_farther = pregrasp_tool_dist > exact_tool_dist

        tool_quat_w = math_utils.quat_from_matrix(world_tool_t[:, :3, :3])
        exact_ee_pos_w, exact_ee_quat_w = math_utils.combine_frame_transforms(
            exact_tool_pos_w,
            tool_quat_w,
            self.ee_offset_pos[env_ids],
            self.ee_offset_rot[env_ids],
        )
        target_ee_pos_w, target_ee_quat_w = math_utils.combine_frame_transforms(
            pregrasp_tool_pos_w,
            tool_quat_w,
            self.ee_offset_pos[env_ids],
            self.ee_offset_rot[env_ids],
        )
        root_pos_w = self._robot.data.root_pos_w[env_ids]
        root_quat_w = self._robot.data.root_quat_w[env_ids]
        target_ee_pos_b, target_ee_quat_b = math_utils.subtract_frame_transforms(
            root_pos_w,
            root_quat_w,
            target_ee_pos_w,
            target_ee_quat_w,
        )
        return {
            "sample_indices": sample_indices,
            "target_ee_pos_b": target_ee_pos_b,
            "target_ee_quat_b": target_ee_quat_b,
            "cube_pos_w": cube_pos_w,
            "cube_quat_w": cube_quat,
            "exact_tool_pos_w": exact_tool_pos_w,
            "exact_tool_quat_w": tool_quat_w,
            "pregrasp_tool_pos_w": pregrasp_tool_pos_w,
            "pregrasp_tool_quat_w": tool_quat_w,
            "exact_ee_pos_w": exact_ee_pos_w,
            "exact_ee_quat_w": exact_ee_quat_w,
            "target_ee_pos_w": target_ee_pos_w,
            "target_ee_quat_w": target_ee_quat_w,
            "pregrasp_offset_dir_w": pregrasp_offset_dir_w,
            "exact_tool_dist": exact_tool_dist,
            "pregrasp_tool_dist": pregrasp_tool_dist,
            "quality_reference_pos_w": cube_pos_w,
            "contact_reference_w": cube_pos_w,
            "contact_center_dist": torch.zeros(num_ids, dtype=torch.float32, device=self.device),
            "center_gate_dist": exact_tool_dist,
            "has_contact_location": torch.zeros(num_ids, dtype=torch.bool, device=self.device),
            "candidate_topdown_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "candidate_center_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "candidate_width_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "candidate_table_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "candidate_valid_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "candidate_fallback_count": torch.ones(num_ids, dtype=torch.long, device=self.device),
            "exact_ee_dist": torch.norm(exact_ee_pos_w - cube_pos_w, dim=-1),
            "pregrasp_ee_dist": torch.norm(target_ee_pos_w - cube_pos_w, dim=-1),
            "pregrasp_farther": pregrasp_farther,
        }

    def _solve_reset_ik(
        self,
        env_ids: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        target_ee_pos_b: torch.Tensor,
        target_ee_quat_b: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        solved_joint_pos = joint_pos.clone()
        solved_joint_pos[:, self.finger_joint_ids] = self._robot.data.default_joint_pos[env_ids][:, self.finger_joint_ids]
        arm_lower = self.robot_dof_lower_limits[self.arm_joint_ids]
        arm_upper = self.robot_dof_upper_limits[self.arm_joint_ids]
        damping = max(float(self.cfg.grasp_prior_reset_ik_damping), 1.0e-6)
        lambda_matrix = (damping**2) * torch.eye(6, device=self.device).unsqueeze(0)
        max_joint_step = float(self.cfg.grasp_prior_reset_ik_max_joint_step)
        pos_error_norm = torch.full((env_ids.numel(),), float("inf"), device=self.device)
        rot_error_norm = torch.full((env_ids.numel(),), float("inf"), device=self.device)
        success = torch.zeros(env_ids.numel(), dtype=torch.bool, device=self.device)

        for _ in range(max(int(self.cfg.grasp_prior_reset_ik_iterations), 1)):
            self._sync_reset_joint_state(env_ids, solved_joint_pos, joint_vel, update_buffers=False)
            ee_pos_b, ee_quat_b = self._compute_ee_frame_pose()
            ee_pos_b = ee_pos_b[env_ids]
            ee_quat_b = ee_quat_b[env_ids]
            pos_error, rot_error = math_utils.compute_pose_error(
                ee_pos_b,
                ee_quat_b,
                target_ee_pos_b,
                target_ee_quat_b,
                rot_error_type="axis_angle",
            )
            pos_error_norm = torch.norm(pos_error, dim=-1)
            rot_error_norm = torch.norm(rot_error, dim=-1)
            success = (
                (pos_error_norm <= float(self.cfg.grasp_prior_reset_ik_pos_tolerance))
                & (rot_error_norm <= float(self.cfg.grasp_prior_reset_ik_rot_tolerance))
            )
            if bool(success.all().item()):
                break

            jacobian = self._compute_ee_frame_jacobian()[env_ids]
            pose_error = torch.cat((pos_error, rot_error), dim=-1)
            jacobian_t = torch.transpose(jacobian, dim0=1, dim1=2)
            dls_rhs = torch.bmm(jacobian, jacobian_t) + lambda_matrix
            delta_joint_pos = torch.bmm(
                jacobian_t,
                torch.linalg.solve(dls_rhs, pose_error.unsqueeze(-1)),
            ).squeeze(-1)
            if max_joint_step > 0.0:
                delta_joint_pos = torch.clamp(delta_joint_pos, min=-max_joint_step, max=max_joint_step)
            current_arm_joint_pos = self._robot.data.joint_pos[env_ids][:, self.arm_joint_ids]
            solved_joint_pos[:, self.arm_joint_ids] = torch.clamp(
                current_arm_joint_pos + delta_joint_pos,
                arm_lower,
                arm_upper,
            )

        self._sync_reset_joint_state(env_ids, solved_joint_pos, joint_vel, update_buffers=False)
        ee_pos_b, ee_quat_b = self._compute_ee_frame_pose()
        pos_error, rot_error = math_utils.compute_pose_error(
            ee_pos_b[env_ids],
            ee_quat_b[env_ids],
            target_ee_pos_b,
            target_ee_quat_b,
            rot_error_type="axis_angle",
        )
        pos_error_norm = torch.norm(pos_error, dim=-1)
        rot_error_norm = torch.norm(rot_error, dim=-1)
        success = (
            (pos_error_norm <= float(self.cfg.grasp_prior_reset_ik_pos_tolerance))
            & (rot_error_norm <= float(self.cfg.grasp_prior_reset_ik_rot_tolerance))
        )
        return solved_joint_pos, success, pos_error_norm, rot_error_norm

    def _gripper_action_for_width(self, width: float) -> float:
        max_width = float(self.cfg.max_gripper_width)
        if max_width <= 1.0e-6:
            return -1.0
        value = 2.0 * float(width) / max_width - 1.0
        return max(-1.0, min(1.0, value))

    def _gripper_action_for_width_tensor(self, width: torch.Tensor) -> torch.Tensor:
        max_width = float(self.cfg.max_gripper_width)
        if max_width <= 1.0e-6:
            return torch.full_like(width, -1.0)
        return torch.clamp(2.0 * width / max_width - 1.0, min=-1.0, max=1.0)

    def _grasp_prior_close_width_targets(self) -> torch.Tensor:
        configured_width = torch.full(
            (self.num_envs,),
            float(self.cfg.grasp_prior_action_warmstart_close_width),
            dtype=torch.float32,
            device=self.device,
        )
        if bool(getattr(self.cfg, "grasp_prior_action_warmstart_use_prior_close_width", True)):
            sampled_width = torch.clamp(
                self.grasp_prior_reset_gripper_width - self.grasp_prior_reset_open_width_margin,
                min=0.0,
                max=float(self.cfg.max_gripper_width),
            )
            margin = max(float(getattr(self.cfg, "grasp_prior_action_warmstart_prior_close_width_margin", 0.003)), 0.0)
            prior_width = torch.clamp(sampled_width - margin, min=0.0, max=float(self.cfg.max_gripper_width))
            configured_width = torch.minimum(configured_width, prior_width)
        min_width = max(float(getattr(self.cfg, "grasp_prior_action_warmstart_min_close_width", 0.0)), 0.0)
        return torch.clamp(configured_width, min=min_width, max=float(self.cfg.max_gripper_width))

    def _grasp_prior_warmstart_close_action(self) -> torch.Tensor:
        return self._gripper_action_for_width_tensor(self._grasp_prior_close_width_targets())

    def _grasp_prior_exact_tracking_action(self, gripper_action: float | torch.Tensor) -> torch.Tensor:
        action = torch.zeros(self.num_envs, int(self.cfg.action_space), device=self.device)
        self._compute_intermediate_values(update_success_timer=False)
        current_ee_pos_b, current_ee_quat_b = self._compute_ee_frame_pose()
        exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
            self._robot.data.root_pos_w,
            self._robot.data.root_quat_w,
            self.grasp_prior_reset_exact_ee_pos_w,
            self.grasp_prior_reset_exact_ee_quat_w,
        )
        gain = float(self.cfg.grasp_prior_action_warmstart_gain)
        max_position_action = max(float(self.cfg.grasp_prior_action_warmstart_max_position_action), 0.0)
        pos_action = gain * (exact_ee_pos_b - current_ee_pos_b) / torch.clamp(self.action_scale[:3], min=1.0e-6)
        action[:, :3] = torch.clamp(pos_action, min=-max_position_action, max=max_position_action)
        if bool(self.cfg.grasp_prior_action_warmstart_track_orientation):
            _, rot_error_b = math_utils.compute_pose_error(
                current_ee_pos_b,
                current_ee_quat_b,
                exact_ee_pos_b,
                exact_ee_quat_b,
                rot_error_type="axis_angle",
            )
            rot_action = gain * rot_error_b / torch.clamp(self.action_scale[3:6], min=1.0e-6)
            action[:, 3:6] = torch.clamp(rot_action, min=-1.0, max=1.0)
        if isinstance(gripper_action, torch.Tensor):
            action[:, 6] = gripper_action.to(device=self.device)
        else:
            action[:, 6] = float(gripper_action)
        self.grasp_prior_action_warmstart_exact_ee_error[:] = torch.norm(
            exact_ee_pos_b - current_ee_pos_b, dim=-1
        )
        return action

    def _update_grasp_prior_action_warmstart_scalars(
        self,
        policy_actions: torch.Tensor,
        applied_actions: torch.Tensor,
    ) -> None:
        self.grasp_prior_action_warmstart_policy_action_z[:] = policy_actions[:, 2]
        self.grasp_prior_action_warmstart_policy_gripper_action[:] = policy_actions[:, 6]
        self.grasp_prior_action_warmstart_applied_action_z[:] = applied_actions[:, 2]
        self.grasp_prior_action_warmstart_applied_gripper_action[:] = applied_actions[:, 6]
        self.grasp_prior_action_warmstart_action_delta_abs[:] = torch.mean(
            torch.abs(applied_actions - policy_actions), dim=-1
        )

    def _grasp_prior_action_warmstart_phase_masks(
        self,
        active: torch.Tensor,
        step: torch.Tensor,
        approach_steps: int,
        close_steps: int,
        exact_ee_error: torch.Tensor,
        close_width: torch.Tensor,
        update_latches: bool,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        ready_to_close = step >= approach_steps
        close_max_ee_error = float(getattr(self.cfg, "grasp_prior_action_warmstart_close_max_ee_error", 0.0))
        if close_max_ee_error > 0.0:
            ready_to_close = ready_to_close & (exact_ee_error <= close_max_ee_error)
        close_latched = self.grasp_prior_action_warmstart_close_latched | ready_to_close
        if update_latches:
            self.grasp_prior_action_warmstart_close_latched[:] = torch.where(
                active,
                close_latched,
                self.grasp_prior_action_warmstart_close_latched,
            )
            close_latched = self.grasp_prior_action_warmstart_close_latched

        ready_to_lift = step >= approach_steps + close_steps
        lift_max_ee_error = float(getattr(self.cfg, "grasp_prior_action_warmstart_lift_max_ee_error", 0.0))
        if lift_max_ee_error > 0.0:
            ready_to_lift = ready_to_lift & (exact_ee_error <= lift_max_ee_error)

        lift_max_finger_dist = float(
            getattr(self.cfg, "grasp_prior_action_warmstart_lift_max_finger_center_dist", 0.0)
        )
        if lift_max_finger_dist > 0.0:
            reference_pos = self.grasp_prior_reset_quality_reference_pos_w - self.scene.env_origins
            missing_reference = torch.norm(reference_pos, dim=-1) < 1.0e-6
            reference_pos = torch.where(missing_reference.unsqueeze(-1), self.cube_pos, reference_pos)
            finger_center = 0.5 * (self.left_finger_pos + self.right_finger_pos)
            reference_finger_dist = torch.norm(finger_center - reference_pos, dim=-1)
            self.grasp_prior_action_warmstart_reference_finger_center_dist[:] = reference_finger_dist
            ready_to_lift = ready_to_lift & (reference_finger_dist <= lift_max_finger_dist)

        closed_width_margin = float(
            getattr(self.cfg, "grasp_prior_action_warmstart_lift_closed_width_margin", -1.0)
        )
        if closed_width_margin >= 0.0:
            ready_to_lift = ready_to_lift & (self.gripper_width <= close_width + closed_width_margin)

        close_ready = active & close_latched
        current_lift_ready = close_ready & ready_to_lift
        if bool(getattr(self.cfg, "grasp_prior_action_warmstart_require_current_lift_ready", False)):
            lift_latched = current_lift_ready
        else:
            lift_latched = self.grasp_prior_action_warmstart_lift_latched | current_lift_ready
        if update_latches:
            self.grasp_prior_action_warmstart_lift_latched[:] = torch.where(
                active,
                lift_latched,
                self.grasp_prior_action_warmstart_lift_latched,
            )
            lift_latched = self.grasp_prior_action_warmstart_lift_latched

        lift_ready = active & close_ready & lift_latched
        approach = active & ~close_ready
        close = close_ready & ~lift_ready
        lift = lift_ready
        return approach, close, lift

    def _apply_grasp_prior_action_warmstart(self, policy_actions: torch.Tensor) -> torch.Tensor:
        self._ensure_cube_buffers()
        policy_actions = policy_actions.clone().clamp(-1.0, 1.0)
        applied_actions = policy_actions.clone()
        self.grasp_prior_action_warmstart_policy_actions[:] = policy_actions
        self.grasp_prior_action_warmstart_phase[:] = -1
        self.grasp_prior_action_warmstart_active[:] = False
        self.grasp_prior_action_warmstart_exact_ee_error[:] = 0.0
        self.grasp_prior_action_warmstart_close_width_target[:] = 0.0
        self.grasp_prior_action_warmstart_reference_finger_center_dist[:] = 0.0

        if not bool(self.cfg.grasp_prior_action_warmstart_enabled):
            self.grasp_prior_action_warmstart_applied_actions[:] = applied_actions
            self._update_grasp_prior_action_warmstart_scalars(policy_actions, applied_actions)
            return applied_actions
        if not getattr(self, "_grasp_prior_reset_enabled", False):
            self.grasp_prior_action_warmstart_applied_actions[:] = applied_actions
            self._update_grasp_prior_action_warmstart_scalars(policy_actions, applied_actions)
            return applied_actions

        approach_steps = max(int(self.cfg.grasp_prior_action_warmstart_approach_steps), 0)
        close_steps = max(int(self.cfg.grasp_prior_action_warmstart_close_steps), 0)
        lift_steps = max(int(self.cfg.grasp_prior_action_warmstart_lift_steps), 0)
        total_steps = approach_steps + close_steps + lift_steps
        if total_steps <= 0:
            self.grasp_prior_action_warmstart_applied_actions[:] = applied_actions
            self._update_grasp_prior_action_warmstart_scalars(policy_actions, applied_actions)
            return applied_actions

        step = self.episode_length_buf.to(device=self.device)
        active = (
            (step < total_steps)
            & self.grasp_prior_reset_success
            & self.grasp_prior_reset_quality_success
        )
        if bool(active.any().item()):
            open_action = self._gripper_action_for_width(float(self.cfg.max_gripper_width))
            close_width = self._grasp_prior_close_width_targets()
            close_action = self._gripper_action_for_width_tensor(close_width)
            self.grasp_prior_action_warmstart_close_width_target[:] = close_width
            exact_open_action = self._grasp_prior_exact_tracking_action(open_action)
            exact_close_action = self._grasp_prior_exact_tracking_action(close_action)
            exact_ee_error = self.grasp_prior_action_warmstart_exact_ee_error.clone()
            lift_action = exact_close_action.clone()
            lift_action[:, 2] = float(self.cfg.grasp_prior_action_warmstart_lift_action_z)

            approach, close, lift = self._grasp_prior_action_warmstart_phase_masks(
                active,
                step,
                approach_steps,
                close_steps,
                exact_ee_error,
                close_width,
                True,
            )
            if bool(approach.any().item()):
                applied_actions[approach] = exact_open_action[approach]
                self.grasp_prior_action_warmstart_phase[approach] = 0
            if bool(close.any().item()):
                applied_actions[close] = exact_close_action[close]
                self.grasp_prior_action_warmstart_phase[close] = 1
            if bool(lift.any().item()):
                applied_actions[lift] = lift_action[lift]
                self.grasp_prior_action_warmstart_phase[lift] = 2
            self.grasp_prior_action_warmstart_active[:] = active

        self.grasp_prior_action_warmstart_applied_actions[:] = applied_actions
        self._update_grasp_prior_action_warmstart_scalars(policy_actions, applied_actions)
        return applied_actions

    def _grasp_prior_reference_actions(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        action_dim = int(self.cfg.action_space)
        teacher_actions = torch.zeros(self.num_envs, action_dim, device=self.device)
        active = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        phase = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        exact_ee_error = torch.zeros(self.num_envs, device=self.device)

        if not getattr(self, "_grasp_prior_reset_enabled", False):
            return teacher_actions, active, phase, exact_ee_error

        approach_steps = max(int(self.cfg.grasp_prior_action_warmstart_approach_steps), 0)
        close_steps = max(int(self.cfg.grasp_prior_action_warmstart_close_steps), 0)
        lift_steps = max(int(self.cfg.grasp_prior_action_warmstart_lift_steps), 0)
        total_steps = approach_steps + close_steps + lift_steps
        if total_steps <= 0:
            return teacher_actions, active, phase, exact_ee_error

        step = self.episode_length_buf.to(device=self.device)
        active = (
            (step < total_steps)
            & self.grasp_prior_reset_success
            & self.grasp_prior_reset_quality_success
        )
        if not bool(active.any().item()):
            return teacher_actions, active, phase, exact_ee_error

        open_action = self._gripper_action_for_width(float(self.cfg.max_gripper_width))
        close_width = self._grasp_prior_close_width_targets()
        close_action = self._gripper_action_for_width_tensor(close_width)
        self.grasp_prior_action_warmstart_close_width_target[:] = close_width
        exact_open_action = self._grasp_prior_exact_tracking_action(open_action)
        exact_ee_error = self.grasp_prior_action_warmstart_exact_ee_error.clone()
        exact_close_action = self._grasp_prior_exact_tracking_action(close_action)
        exact_ee_error = torch.maximum(exact_ee_error, self.grasp_prior_action_warmstart_exact_ee_error)
        lift_action = exact_close_action.clone()
        lift_action[:, 2] = float(self.cfg.grasp_prior_action_warmstart_lift_action_z)

        approach, close, lift = self._grasp_prior_action_warmstart_phase_masks(
            active,
            step,
            approach_steps,
            close_steps,
            exact_ee_error,
            close_width,
            False,
        )
        if bool(approach.any().item()):
            teacher_actions[approach] = exact_open_action[approach]
            phase[approach] = 0
        if bool(close.any().item()):
            teacher_actions[close] = exact_close_action[close]
            phase[close] = 1
        if bool(lift.any().item()):
            teacher_actions[lift] = lift_action[lift]
            phase[lift] = 2
        return teacher_actions, active, phase, exact_ee_error

    def compute_grasp_prior_reference_actions(self) -> torch.Tensor:
        """Return the current grasp-prior scripted action target for eval/BC."""
        teacher_actions, _, _, _ = self._grasp_prior_reference_actions()
        return teacher_actions.detach().clamp(-1.0, 1.0)

    def _compute_grasp_prior_action_prior_reward(self) -> torch.Tensor:
        self._ensure_cube_buffers()
        self.grasp_prior_action_prior_active[:] = False
        self.grasp_prior_action_prior_phase[:] = -1
        self.grasp_prior_action_prior_teacher_actions[:] = 0.0
        self.grasp_prior_action_prior_delta_abs[:] = 0.0
        self.grasp_prior_action_prior_reward[:] = 0.0
        self.grasp_prior_action_prior_teacher_action_z[:] = 0.0
        self.grasp_prior_action_prior_teacher_gripper_action[:] = 0.0
        self.grasp_prior_action_prior_exact_ee_error[:] = 0.0

        if not bool(self.cfg.grasp_prior_action_prior_reward_enabled):
            return self.grasp_prior_action_prior_reward
        if not getattr(self, "_grasp_prior_reset_enabled", False):
            return self.grasp_prior_action_prior_reward

        teacher_actions, active, phase, exact_ee_error = self._grasp_prior_reference_actions()
        self.grasp_prior_action_prior_active[:] = active
        self.grasp_prior_action_prior_phase[:] = phase
        self.grasp_prior_action_prior_teacher_actions[:] = teacher_actions
        self.grasp_prior_action_prior_teacher_action_z[:] = teacher_actions[:, 2]
        self.grasp_prior_action_prior_teacher_gripper_action[:] = teacher_actions[:, 6]
        self.grasp_prior_action_prior_exact_ee_error[:] = exact_ee_error

        policy_actions = self.actions
        if bool(self.cfg.grasp_prior_action_warmstart_enabled):
            policy_actions = self.grasp_prior_action_warmstart_policy_actions

        if bool(active.any().item()):
            delta_abs = torch.mean(torch.abs(policy_actions - teacher_actions), dim=-1)
            self.grasp_prior_action_prior_delta_abs[:] = delta_abs
            weight = max(float(self.cfg.grasp_prior_action_prior_reward_weight), 0.0)
            sharpness = max(float(self.cfg.grasp_prior_action_prior_reward_sharpness), 0.0)
            self.grasp_prior_action_prior_reward[:] = (
                weight
                * active.float()
                * torch.exp(-sharpness * delta_abs)
            )
        return self.grasp_prior_action_prior_reward

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        applied_actions = self._apply_grasp_prior_action_warmstart(actions)
        super()._pre_physics_step(applied_actions)

    def _grasp_prior_reset_extra_success_mask(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        return torch.ones(int(env_ids.numel()), dtype=torch.bool, device=self.device)

    def _grasp_prior_reset_extra_quality_mask(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        return torch.ones(int(env_ids.numel()), dtype=torch.bool, device=self.device)

    def _apply_grasp_prior_reset(
        self,
        env_ids: torch.Tensor,
        baseline_joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        cube_pos: torch.Tensor,
        cube_quat: torch.Tensor,
    ) -> None:
        targets = self._compose_grasp_prior_targets(env_ids, cube_pos, cube_quat)
        solved_joint_pos, ik_success, pos_error_norm, rot_error_norm = self._solve_reset_ik(
            env_ids,
            baseline_joint_pos,
            joint_vel,
            targets["target_ee_pos_b"],
            targets["target_ee_quat_b"],
        )
        self._compute_intermediate_values(env_ids)
        table_clearance_ok = self.finger_table_clearance[env_ids] >= float(
            self.cfg.finger_table_penetration_termination_margin
        )
        success = (
            ik_success
            & targets["pregrasp_farther"]
            & table_clearance_ok
            & self._grasp_prior_reset_extra_success_mask(env_ids, targets)
        )

        final_joint_pos = solved_joint_pos
        failed = ~success
        if bool(self.cfg.grasp_prior_fallback_to_default_on_ik_failure) and bool(failed.any().item()):
            final_joint_pos = solved_joint_pos.clone()
            final_joint_pos[failed] = baseline_joint_pos[failed]
            self._sync_reset_joint_state(env_ids, final_joint_pos, joint_vel, update_buffers=False)
            self._compute_intermediate_values(env_ids)

        self._sync_reset_joint_state(env_ids, final_joint_pos, joint_vel, update_buffers=True)
        self.grasp_prior_reset_attempted[env_ids] = True
        self.grasp_prior_reset_success[env_ids] = success
        self.grasp_prior_reset_farther[env_ids] = targets["pregrasp_farther"]
        self.grasp_prior_reset_sample_index[env_ids] = targets["sample_indices"]
        self.grasp_prior_reset_pos_error[env_ids] = pos_error_norm
        self.grasp_prior_reset_rot_error[env_ids] = rot_error_norm
        self.grasp_prior_reset_exact_tool_dist[env_ids] = targets["exact_tool_dist"]
        self.grasp_prior_reset_pregrasp_tool_dist[env_ids] = targets["pregrasp_tool_dist"]
        self.grasp_prior_reset_finger_center_dist[env_ids] = self.finger_center_to_cube_dist[env_ids]
        self.grasp_prior_reset_finger_table_clearance[env_ids] = self.finger_table_clearance[env_ids]
        self.grasp_prior_reset_cube_pos_w[env_ids] = targets["cube_pos_w"]
        self.grasp_prior_reset_cube_quat_w[env_ids] = targets["cube_quat_w"]
        self.grasp_prior_reset_exact_tool_pos_w[env_ids] = targets["exact_tool_pos_w"]
        self.grasp_prior_reset_pregrasp_tool_pos_w[env_ids] = targets["pregrasp_tool_pos_w"]
        self.grasp_prior_reset_exact_ee_pos_w[env_ids] = targets["exact_ee_pos_w"]
        self.grasp_prior_reset_target_ee_pos_w[env_ids] = targets["target_ee_pos_w"]
        self.grasp_prior_reset_offset_dir_w[env_ids] = targets["pregrasp_offset_dir_w"]
        self.grasp_prior_reset_exact_tool_quat_w[env_ids] = targets["exact_tool_quat_w"]
        self.grasp_prior_reset_pregrasp_tool_quat_w[env_ids] = targets["pregrasp_tool_quat_w"]
        self.grasp_prior_reset_exact_ee_quat_w[env_ids] = targets["exact_ee_quat_w"]
        self.grasp_prior_reset_target_ee_quat_w[env_ids] = targets["target_ee_quat_w"]
        self.grasp_prior_reset_left_finger_pos[env_ids] = self.left_finger_pos[env_ids]
        self.grasp_prior_reset_right_finger_pos[env_ids] = self.right_finger_pos[env_ids]
        self.grasp_prior_reset_gripper_width[env_ids] = self.gripper_width[env_ids]
        object_size = self._grasp_prior_object_size(env_ids)
        required_open_width = self._grasp_prior_required_open_width(env_ids, targets)
        self.grasp_prior_reset_open_width_margin[env_ids] = self.gripper_width[env_ids] - required_open_width
        quality_reference_pos_w = targets.get("quality_reference_pos_w", targets["cube_pos_w"])
        contact_reference_pos_w = targets.get("contact_reference_w", quality_reference_pos_w)
        self.grasp_prior_reset_quality_reference_pos_w[env_ids] = quality_reference_pos_w
        self.grasp_prior_reset_contact_reference_pos_w[env_ids] = contact_reference_pos_w
        self.grasp_prior_reset_contact_reference_pos_o[env_ids] = targets.get(
            "contact_reference_object",
            torch.zeros(int(env_ids.numel()), 3, dtype=torch.float32, device=self.device),
        )
        self.grasp_prior_current_contact_reference_pos[env_ids] = contact_reference_pos_w - self.scene.env_origins[
            env_ids
        ]
        self.grasp_prior_reset_contact_center_dist[env_ids] = targets.get(
            "contact_center_dist",
            torch.zeros_like(self.grasp_prior_reset_contact_center_dist[env_ids]),
        )
        self.grasp_prior_reset_center_gate_dist[env_ids] = targets.get("center_gate_dist", targets["exact_tool_dist"])
        self.grasp_prior_reset_has_contact_location[env_ids] = targets.get(
            "has_contact_location",
            torch.zeros(int(env_ids.numel()), dtype=torch.bool, device=self.device),
        )
        self.grasp_prior_reset_candidate_topdown_count[env_ids] = targets.get(
            "candidate_topdown_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_candidate_center_count[env_ids] = targets.get(
            "candidate_center_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_candidate_width_count[env_ids] = targets.get(
            "candidate_width_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_candidate_table_count[env_ids] = targets.get(
            "candidate_table_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_candidate_valid_count[env_ids] = targets.get(
            "candidate_valid_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_candidate_fallback_count[env_ids] = targets.get(
            "candidate_fallback_count",
            torch.zeros(int(env_ids.numel()), dtype=torch.long, device=self.device),
        )
        self.grasp_prior_reset_exact_ee_dist[env_ids] = torch.norm(
            targets["exact_ee_pos_w"] - quality_reference_pos_w,
            dim=-1,
        )
        self.grasp_prior_reset_pregrasp_ee_dist[env_ids] = torch.norm(
            targets["target_ee_pos_w"] - quality_reference_pos_w,
            dim=-1,
        )

        reference_to_exact = targets["exact_tool_pos_w"] - quality_reference_pos_w
        reference_to_exact = reference_to_exact / torch.clamp(
            torch.norm(reference_to_exact, dim=-1, keepdim=True),
            min=1.0e-6,
        )
        offset_dot = torch.sum(targets["pregrasp_offset_dir_w"] * reference_to_exact, dim=-1)
        self.grasp_prior_reset_offset_radial_dot[env_ids] = offset_dot
        self.grasp_prior_reset_offset_radial_angle[env_ids] = torch.acos(torch.clamp(offset_dot, -1.0, 1.0))
        require_offset_radial_quality = targets.get(
            "require_offset_radial_quality",
            torch.ones(int(env_ids.numel()), dtype=torch.bool, device=self.device),
        )

        pregrasp_offset = abs(float(self.cfg.grasp_prior_pregrasp_offset))
        body_finger_center = 0.5 * (self.left_finger_pos[env_ids] + self.right_finger_pos[env_ids])
        projected_exact_body_finger_center = body_finger_center - pregrasp_offset * targets["pregrasp_offset_dir_w"]
        quality_reference_pos_env = quality_reference_pos_w - self.scene.env_origins[env_ids]
        self.grasp_prior_reset_projected_exact_finger_center_dist[env_ids] = torch.norm(
            projected_exact_body_finger_center - quality_reference_pos_env, dim=-1
        )
        actual_finger_center_dist = self.grasp_prior_reset_projected_exact_finger_center_dist[env_ids]

        gripper_half_axis = 0.5 * (self.left_finger_pos[env_ids] - self.right_finger_pos[env_ids])
        pregrasp_ee_pos_env = targets["target_ee_pos_w"] - self.scene.env_origins[env_ids]
        exact_ee_pos_env = targets["exact_ee_pos_w"] - self.scene.env_origins[env_ids]
        left_tip_proxy = pregrasp_ee_pos_env + gripper_half_axis
        right_tip_proxy = pregrasp_ee_pos_env - gripper_half_axis
        exact_left_tip_proxy = exact_ee_pos_env + gripper_half_axis
        exact_right_tip_proxy = exact_ee_pos_env - gripper_half_axis
        self.grasp_prior_reset_left_tip_proxy_pos[env_ids] = left_tip_proxy
        self.grasp_prior_reset_right_tip_proxy_pos[env_ids] = right_tip_proxy
        self.grasp_prior_reset_projected_exact_left_tip_proxy_pos[env_ids] = exact_left_tip_proxy
        self.grasp_prior_reset_projected_exact_right_tip_proxy_pos[env_ids] = exact_right_tip_proxy
        exact_tip_center_dist = torch.norm(exact_ee_pos_env - quality_reference_pos_env, dim=-1)
        exact_left_tip_dist = torch.norm(exact_left_tip_proxy - quality_reference_pos_env, dim=-1)
        exact_right_tip_dist = torch.norm(exact_right_tip_proxy - quality_reference_pos_env, dim=-1)
        exact_tip_max_dist = torch.maximum(exact_left_tip_dist, exact_right_tip_dist)
        pregrasp_tip_table_clearance = torch.minimum(left_tip_proxy[:, 2], right_tip_proxy[:, 2]) - float(
            self.cfg.table_surface_z
        )
        exact_tip_table_clearance = torch.minimum(exact_left_tip_proxy[:, 2], exact_right_tip_proxy[:, 2]) - float(
            self.cfg.table_surface_z
        )
        self.grasp_prior_reset_projected_exact_tip_center_dist[env_ids] = exact_tip_center_dist
        self.grasp_prior_reset_projected_exact_tip_max_dist[env_ids] = exact_tip_max_dist
        self.grasp_prior_reset_pregrasp_tip_table_clearance[env_ids] = pregrasp_tip_table_clearance
        self.grasp_prior_reset_projected_exact_tip_table_clearance[env_ids] = exact_tip_table_clearance
        finger_center_limit = 1.25 * object_size
        tip_center_limit = 0.75 * object_size
        tip_max_limit = 1.25 * object_size
        finger_center_cap = float(getattr(self.cfg, "grasp_prior_reset_quality_max_finger_center_dist", 0.0))
        tip_center_cap = float(getattr(self.cfg, "grasp_prior_reset_quality_max_tip_center_dist", 0.0))
        tip_max_cap = float(getattr(self.cfg, "grasp_prior_reset_quality_max_tip_max_dist", 0.0))
        if finger_center_cap > 0.0:
            finger_center_limit = torch.minimum(
                finger_center_limit,
                torch.full_like(finger_center_limit, finger_center_cap),
            )
        if tip_center_cap > 0.0:
            tip_center_limit = torch.minimum(
                tip_center_limit,
                torch.full_like(tip_center_limit, tip_center_cap),
            )
        if tip_max_cap > 0.0:
            tip_max_limit = torch.minimum(
                tip_max_limit,
                torch.full_like(tip_max_limit, tip_max_cap),
            )
        self.grasp_prior_reset_quality_success[env_ids] = (
            success
            & (self.grasp_prior_reset_open_width_margin[env_ids] >= 0.0)
            & ((offset_dot > 0.25) | ~require_offset_radial_quality)
            & (actual_finger_center_dist <= finger_center_limit)
            & (exact_tip_center_dist <= tip_center_limit)
            & (exact_tip_max_dist <= tip_max_limit)
            & (pregrasp_tip_table_clearance >= float(self.cfg.finger_table_penetration_termination_margin))
            & (exact_tip_table_clearance >= float(self.cfg.finger_table_penetration_termination_margin))
            & self._grasp_prior_reset_extra_quality_mask(env_ids, targets)
        )

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
        finger_table_penetration_done = (
            (self.finger_table_clearance < float(self.cfg.finger_table_penetration_termination_margin))
            & (self.episode_length_buf > 2)
        )
        terminated = cube_out | success_done | prelift_drag_done | finger_table_penetration_done
        truncated = self.episode_length_buf >= self.max_episode_length - 1
        return terminated, truncated

    def _get_rewards(self) -> torch.Tensor:
        self._compute_intermediate_values(update_success_timer=True)
        reward_actions = self.actions
        if bool(getattr(self.cfg, "grasp_prior_action_warmstart_enabled", False)) and hasattr(
            self,
            "grasp_prior_action_warmstart_policy_actions",
        ):
            reward_actions = self.grasp_prior_action_warmstart_policy_actions
        (
            approach_reward,
            enclosure_reward,
            lift_reward,
            height_tracking_reward,
            xy_stability_reward,
            success_bonus,
            close_action_reward,
            lift_action_reward,
            descend_action_penalty,
            postlift_close_action_reward,
            postlift_open_action_penalty,
            postlift_lift_action_reward,
            postlift_descend_action_penalty,
            table_clearance_penalty,
            gripper_close_reg,
            action_penalty,
        ) = compute_franka_cube_grasp_rewards(
            self.left_finger_to_cube_dist,
            self.right_finger_to_cube_dist,
            self.gripper_width,
            self.cube_lift_height,
            self.cube_goal_height_error,
            self.cube_xy_error,
            self.finger_table_clearance,
            self.in_success_region,
            self.has_lifted_cube,
            reward_actions,
            float(self.cfg.cube_lift_height),
            float(self.cfg.max_gripper_width),
            float(self.cfg.finger_table_clearance_margin),
            float(self.cfg.cube_approach_weight),
            float(self.cfg.cube_approach_sharpness),
            float(self.cfg.cube_enclosure_weight),
            float(self.cfg.cube_enclosure_sharpness),
            float(self.cfg.cube_lift_weight),
            float(self.cfg.cube_height_tracking_weight),
            float(self.cfg.cube_height_tracking_sharpness),
            float(self.cfg.cube_xy_stability_weight),
            float(self.cfg.cube_xy_stability_sharpness),
            float(self.cfg.cube_success_bonus_weight),
            float(self.cfg.cube_close_action_weight),
            float(self.cfg.cube_lift_action_weight),
            float(self.cfg.cube_descend_action_penalty_weight),
            float(self.cfg.cube_postlift_action_gate_height),
            float(self.cfg.cube_postlift_close_action_weight),
            float(self.cfg.cube_postlift_open_action_penalty_weight),
            float(self.cfg.cube_postlift_lift_action_weight),
            float(self.cfg.cube_postlift_descend_action_penalty_weight),
            float(self.cfg.cube_table_clearance_penalty_weight),
            float(self.cfg.cube_gripper_close_reg_weight),
            float(self.cfg.cube_action_penalty_weight),
        )
        total_reward = (
            approach_reward
            + enclosure_reward
            + lift_reward
            + height_tracking_reward
            + xy_stability_reward
            + success_bonus
            + close_action_reward
            + lift_action_reward
            + descend_action_penalty
            + postlift_close_action_reward
            + postlift_open_action_penalty
            + postlift_lift_action_reward
            + postlift_descend_action_penalty
            + table_clearance_penalty
            + gripper_close_reg
            + action_penalty
        )
        action_prior_reward = self._compute_grasp_prior_action_prior_reward()
        total_reward = total_reward + action_prior_reward
        log_terms = {
            "cube_approach_reward": approach_reward.mean(),
            "cube_enclosure_reward": enclosure_reward.mean(),
            "cube_lift_reward": lift_reward.mean(),
            "cube_height_tracking_reward": height_tracking_reward.mean(),
            "cube_xy_stability_reward": xy_stability_reward.mean(),
            "cube_success_bonus": success_bonus.mean(),
            "cube_close_action_reward": close_action_reward.mean(),
            "cube_lift_action_reward": lift_action_reward.mean(),
            "cube_descend_action_penalty": descend_action_penalty.mean(),
            "cube_postlift_close_action_reward": postlift_close_action_reward.mean(),
            "cube_postlift_open_action_penalty": postlift_open_action_penalty.mean(),
            "cube_postlift_lift_action_reward": postlift_lift_action_reward.mean(),
            "cube_postlift_descend_action_penalty": postlift_descend_action_penalty.mean(),
            "cube_table_clearance_penalty": table_clearance_penalty.mean(),
            "cube_gripper_close_reg": gripper_close_reg.mean(),
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
            "cube_finger_table_clearance": self.finger_table_clearance.mean(),
            "cube_finger_table_clearance_violation": self.finger_table_clearance_violation.mean(),
            "cube_action_z": self.actions[:, 2].mean(),
            "cube_action_up": torch.clamp(self.actions[:, 2], 0.0, 1.0).mean(),
            "cube_action_down": torch.clamp(-self.actions[:, 2], 0.0, 1.0).mean(),
            "cube_gripper_action": self.actions[:, 6].mean(),
            "cube_gripper_close_action": torch.clamp(-self.actions[:, 6], 0.0, 1.0).mean(),
            "cube_reward_action_z": reward_actions[:, 2].mean(),
            "cube_reward_action_up": torch.clamp(reward_actions[:, 2], 0.0, 1.0).mean(),
            "cube_reward_action_down": torch.clamp(-reward_actions[:, 2], 0.0, 1.0).mean(),
            "cube_reward_gripper_action": reward_actions[:, 6].mean(),
            "cube_reward_gripper_close_action": torch.clamp(-reward_actions[:, 6], 0.0, 1.0).mean(),
        }
        if bool(self.cfg.grasp_prior_action_prior_reward_enabled):
            action_prior_phase = self.grasp_prior_action_prior_phase
            log_terms.update(
                {
                    "cube_action_prior_reward": action_prior_reward.mean(),
                    "cube_action_prior_active_rate": self.grasp_prior_action_prior_active.float().mean(),
                    "cube_action_prior_approach_rate": (action_prior_phase == 0).float().mean(),
                    "cube_action_prior_close_rate": (action_prior_phase == 1).float().mean(),
                    "cube_action_prior_lift_rate": (action_prior_phase == 2).float().mean(),
                    "cube_action_prior_delta_abs": self.grasp_prior_action_prior_delta_abs.mean(),
                    "cube_action_prior_teacher_z": self.grasp_prior_action_prior_teacher_action_z.mean(),
                    "cube_action_prior_teacher_gripper": self.grasp_prior_action_prior_teacher_gripper_action.mean(),
                    "cube_action_prior_exact_ee_error": self.grasp_prior_action_prior_exact_ee_error.mean(),
                    "cube_action_prior_close_width_target": self.grasp_prior_action_warmstart_close_width_target.mean(),
                }
            )
        if getattr(self, "_grasp_prior_reset_enabled", False):
            log_terms.update(
                {
                    "cube_grasp_prior_reset_attempt_rate": self.grasp_prior_reset_attempted.float().mean(),
                    "cube_grasp_prior_reset_success_rate": self.grasp_prior_reset_success.float().mean(),
                    "cube_grasp_prior_reset_farther_rate": self.grasp_prior_reset_farther.float().mean(),
                    "cube_grasp_prior_reset_pos_error": self.grasp_prior_reset_pos_error.mean(),
                    "cube_grasp_prior_reset_rot_error": self.grasp_prior_reset_rot_error.mean(),
                    "cube_grasp_prior_exact_tool_dist": self.grasp_prior_reset_exact_tool_dist.mean(),
                    "cube_grasp_prior_pregrasp_tool_dist": self.grasp_prior_reset_pregrasp_tool_dist.mean(),
                    "cube_grasp_prior_exact_ee_dist": self.grasp_prior_reset_exact_ee_dist.mean(),
                    "cube_grasp_prior_pregrasp_ee_dist": self.grasp_prior_reset_pregrasp_ee_dist.mean(),
                    "cube_grasp_prior_finger_center_dist": self.grasp_prior_reset_finger_center_dist.mean(),
                    "cube_grasp_prior_finger_table_clearance": self.grasp_prior_reset_finger_table_clearance.mean(),
                    "cube_grasp_prior_cube_quat_norm": torch.norm(
                        self.grasp_prior_reset_cube_quat_w,
                        dim=-1,
                    ).mean(),
                    "cube_grasp_prior_open_width_margin": self.grasp_prior_reset_open_width_margin.mean(),
                    "cube_grasp_prior_offset_radial_dot": self.grasp_prior_reset_offset_radial_dot.mean(),
                    "cube_grasp_prior_offset_radial_angle": self.grasp_prior_reset_offset_radial_angle.mean(),
                    "cube_grasp_prior_projected_exact_finger_center_dist": self.grasp_prior_reset_projected_exact_finger_center_dist.mean(),
                    "cube_grasp_prior_projected_exact_tip_center_dist": self.grasp_prior_reset_projected_exact_tip_center_dist.mean(),
                    "cube_grasp_prior_projected_exact_tip_max_dist": self.grasp_prior_reset_projected_exact_tip_max_dist.mean(),
                    "cube_grasp_prior_pregrasp_tip_table_clearance": self.grasp_prior_reset_pregrasp_tip_table_clearance.mean(),
                    "cube_grasp_prior_projected_exact_tip_table_clearance": self.grasp_prior_reset_projected_exact_tip_table_clearance.mean(),
                    "cube_grasp_prior_quality_success_rate": self.grasp_prior_reset_quality_success.float().mean(),
                    "cube_grasp_prior_candidate_topdown_count": self.grasp_prior_reset_candidate_topdown_count.float().mean(),
                    "cube_grasp_prior_candidate_center_count": self.grasp_prior_reset_candidate_center_count.float().mean(),
                    "cube_grasp_prior_candidate_width_count": self.grasp_prior_reset_candidate_width_count.float().mean(),
                    "cube_grasp_prior_candidate_table_count": self.grasp_prior_reset_candidate_table_count.float().mean(),
                    "cube_grasp_prior_candidate_valid_count": self.grasp_prior_reset_candidate_valid_count.float().mean(),
                    "cube_grasp_prior_candidate_fallback_count": self.grasp_prior_reset_candidate_fallback_count.float().mean(),
                }
            )
        if bool(self.cfg.grasp_prior_action_warmstart_enabled):
            phase = self.grasp_prior_action_warmstart_phase
            active = self.grasp_prior_action_warmstart_active
            active_count = active.float().sum()
            active_denom = torch.clamp(active_count, min=1.0)
            active_mask = active.float()
            lift = phase == 2
            lift_count = lift.float().sum()
            lift_denom = torch.clamp(lift_count, min=1.0)
            lift_mask = lift.float()
            log_terms.update(
                {
                    "cube_action_warmstart_active_rate": self.grasp_prior_action_warmstart_active.float().mean(),
                    "cube_action_warmstart_approach_rate": (phase == 0).float().mean(),
                    "cube_action_warmstart_close_rate": (phase == 1).float().mean(),
                    "cube_action_warmstart_lift_rate": (phase == 2).float().mean(),
                    "cube_action_warmstart_close_latched_rate": (
                        self.grasp_prior_action_warmstart_close_latched.float().mean()
                    ),
                    "cube_action_warmstart_lift_latched_rate": (
                        self.grasp_prior_action_warmstart_lift_latched.float().mean()
                    ),
                    "cube_action_warmstart_exact_ee_error": self.grasp_prior_action_warmstart_exact_ee_error.mean(),
                    "cube_action_warmstart_close_width_target": self.grasp_prior_action_warmstart_close_width_target.mean(),
                    "cube_action_warmstart_reference_finger_center_dist": (
                        self.grasp_prior_action_warmstart_reference_finger_center_dist.mean()
                    ),
                    "cube_action_warmstart_delta_abs": self.grasp_prior_action_warmstart_action_delta_abs.mean(),
                    "cube_policy_action_z": self.grasp_prior_action_warmstart_policy_action_z.mean(),
                    "cube_policy_gripper_action": self.grasp_prior_action_warmstart_policy_gripper_action.mean(),
                    "cube_applied_action_z": self.grasp_prior_action_warmstart_applied_action_z.mean(),
                    "cube_applied_gripper_action": self.grasp_prior_action_warmstart_applied_gripper_action.mean(),
                    "cube_action_warmstart_active_count": active_count,
                    "cube_action_warmstart_active_gripper_width": (self.gripper_width * active_mask).sum()
                    / active_denom,
                    "cube_action_warmstart_active_finger_center_dist": (
                        self.finger_center_to_cube_dist * active_mask
                    ).sum()
                    / active_denom,
                    "cube_action_warmstart_active_reference_finger_center_dist": (
                        self.grasp_prior_action_warmstart_reference_finger_center_dist * active_mask
                    ).sum()
                    / active_denom,
                    "cube_action_warmstart_active_lift_height": (self.cube_lift_height * active_mask).sum()
                    / active_denom,
                    "cube_action_warmstart_active_has_lifted_rate": (self.has_lifted_cube.float() * active_mask).sum()
                    / active_denom,
                    "cube_action_warmstart_active_success_rate": (self.in_success_region.float() * active_mask).sum()
                    / active_denom,
                    "cube_action_warmstart_active_exact_ee_error": (
                        self.grasp_prior_action_warmstart_exact_ee_error * active_mask
                    ).sum()
                    / active_denom,
                    "cube_action_warmstart_lift_count": lift_count,
                    "cube_action_warmstart_lift_gripper_width": (self.gripper_width * lift_mask).sum() / lift_denom,
                    "cube_action_warmstart_lift_finger_center_dist": (
                        self.finger_center_to_cube_dist * lift_mask
                    ).sum()
                    / lift_denom,
                    "cube_action_warmstart_lift_reference_finger_center_dist": (
                        self.grasp_prior_action_warmstart_reference_finger_center_dist * lift_mask
                    ).sum()
                    / lift_denom,
                    "cube_action_warmstart_lift_lift_height": (self.cube_lift_height * lift_mask).sum()
                    / lift_denom,
                    "cube_action_warmstart_lift_has_lifted_rate": (self.has_lifted_cube.float() * lift_mask).sum()
                    / lift_denom,
                    "cube_action_warmstart_lift_success_rate": (self.in_success_region.float() * lift_mask).sum()
                    / lift_denom,
                    "cube_action_warmstart_lift_exact_ee_error": (
                        self.grasp_prior_action_warmstart_exact_ee_error * lift_mask
                    ).sum()
                    / lift_denom,
                }
            )
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
        self._reset_grasp_prior_metrics(env_ids)

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
        if getattr(self, "_grasp_prior_reset_enabled", False):
            self._apply_grasp_prior_reset(env_ids, joint_pos, joint_vel, cube_pos, cube_quat)
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
        self.finger_table_clearance[env_ids] = torch.minimum(
            self.left_finger_pos[env_ids, 2],
            self.right_finger_pos[env_ids, 2],
        ) - float(self.cfg.table_surface_z)
        clearance_margin = float(self.cfg.finger_table_clearance_margin)
        if clearance_margin < 1.0e-6:
            clearance_margin = 1.0e-6
        self.finger_table_clearance_violation[env_ids] = torch.clamp(
            (float(self.cfg.finger_table_clearance_margin) - self.finger_table_clearance[env_ids])
            / clearance_margin,
            0.0,
            1.0,
        )
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
            & (self.hand_to_cube_mean_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
            & (self.finger_table_clearance[env_ids] >= float(self.cfg.finger_table_clearance_success_margin))
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
