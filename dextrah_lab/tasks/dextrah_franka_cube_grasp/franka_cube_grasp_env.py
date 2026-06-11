"""DirectRLEnv for Franka single-cube grasp-and-lift."""

from __future__ import annotations

from collections.abc import Sequence
import json
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
            self.grasp_prior_reset_projected_exact_finger_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_max_dist = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_pregrasp_tip_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_projected_exact_tip_table_clearance = torch.zeros(self.num_envs, device=self.device)
            self.grasp_prior_reset_quality_success = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

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
        self.grasp_prior_reset_projected_exact_finger_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_center_dist[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_max_dist[env_ids] = 0.0
        self.grasp_prior_reset_pregrasp_tip_table_clearance[env_ids] = 0.0
        self.grasp_prior_reset_projected_exact_tip_table_clearance[env_ids] = 0.0
        self.grasp_prior_reset_quality_success[env_ids] = False

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

    def _compose_grasp_prior_targets(self, env_ids: torch.Tensor, cube_pos: torch.Tensor) -> dict[str, torch.Tensor]:
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
        pregrasp_tool_pos_w = torch.where(use_plus.unsqueeze(-1), plus_tool_pos_w, minus_tool_pos_w)
        pregrasp_tool_dist = torch.where(use_plus, plus_tool_dist, minus_tool_dist)
        pregrasp_farther = pregrasp_tool_dist > exact_tool_dist
        pregrasp_offset_dir_w = pregrasp_tool_pos_w - exact_tool_pos_w
        pregrasp_offset_dir_w = pregrasp_offset_dir_w / torch.clamp(
            torch.norm(pregrasp_offset_dir_w, dim=-1, keepdim=True),
            min=1.0e-6,
        )

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

    def _apply_grasp_prior_reset(
        self,
        env_ids: torch.Tensor,
        baseline_joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        cube_pos: torch.Tensor,
    ) -> None:
        targets = self._compose_grasp_prior_targets(env_ids, cube_pos)
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
        success = ik_success & targets["pregrasp_farther"] & table_clearance_ok

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
        self.grasp_prior_reset_open_width_margin[env_ids] = self.gripper_width[env_ids] - float(self.cfg.cube_size)
        self.grasp_prior_reset_exact_ee_dist[env_ids] = targets["exact_ee_dist"]
        self.grasp_prior_reset_pregrasp_ee_dist[env_ids] = targets["pregrasp_ee_dist"]

        cube_to_exact = targets["exact_ee_pos_w"] - targets["cube_pos_w"]
        cube_to_exact = cube_to_exact / torch.clamp(torch.norm(cube_to_exact, dim=-1, keepdim=True), min=1.0e-6)
        offset_dot = torch.sum(targets["pregrasp_offset_dir_w"] * cube_to_exact, dim=-1)
        self.grasp_prior_reset_offset_radial_dot[env_ids] = offset_dot
        self.grasp_prior_reset_offset_radial_angle[env_ids] = torch.acos(torch.clamp(offset_dot, -1.0, 1.0))

        pregrasp_offset = abs(float(self.cfg.grasp_prior_pregrasp_offset))
        body_finger_center = 0.5 * (self.left_finger_pos[env_ids] + self.right_finger_pos[env_ids])
        projected_exact_body_finger_center = body_finger_center - pregrasp_offset * targets["pregrasp_offset_dir_w"]
        cube_pos_env = targets["cube_pos_w"] - self.scene.env_origins[env_ids]
        self.grasp_prior_reset_projected_exact_finger_center_dist[env_ids] = torch.norm(
            projected_exact_body_finger_center - cube_pos_env, dim=-1
        )

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
        exact_tip_center_dist = torch.norm(exact_ee_pos_env - cube_pos_env, dim=-1)
        exact_left_tip_dist = torch.norm(exact_left_tip_proxy - cube_pos_env, dim=-1)
        exact_right_tip_dist = torch.norm(exact_right_tip_proxy - cube_pos_env, dim=-1)
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
        self.grasp_prior_reset_quality_success[env_ids] = (
            success
            & (self.grasp_prior_reset_open_width_margin[env_ids] >= 0.0)
            & (offset_dot > 0.25)
            & (exact_tip_center_dist <= 0.75 * float(self.cfg.cube_size))
            & (exact_tip_max_dist <= 1.25 * float(self.cfg.cube_size))
            & (pregrasp_tip_table_clearance >= float(self.cfg.finger_table_penetration_termination_margin))
            & (exact_tip_table_clearance >= float(self.cfg.finger_table_penetration_termination_margin))
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
            self.actions,
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
            + table_clearance_penalty
            + gripper_close_reg
            + action_penalty
        )
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
        }
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
                    "cube_grasp_prior_open_width_margin": self.grasp_prior_reset_open_width_margin.mean(),
                    "cube_grasp_prior_offset_radial_dot": self.grasp_prior_reset_offset_radial_dot.mean(),
                    "cube_grasp_prior_offset_radial_angle": self.grasp_prior_reset_offset_radial_angle.mean(),
                    "cube_grasp_prior_projected_exact_finger_center_dist": self.grasp_prior_reset_projected_exact_finger_center_dist.mean(),
                    "cube_grasp_prior_projected_exact_tip_center_dist": self.grasp_prior_reset_projected_exact_tip_center_dist.mean(),
                    "cube_grasp_prior_projected_exact_tip_max_dist": self.grasp_prior_reset_projected_exact_tip_max_dist.mean(),
                    "cube_grasp_prior_pregrasp_tip_table_clearance": self.grasp_prior_reset_pregrasp_tip_table_clearance.mean(),
                    "cube_grasp_prior_projected_exact_tip_table_clearance": self.grasp_prior_reset_projected_exact_tip_table_clearance.mean(),
                    "cube_grasp_prior_quality_success_rate": self.grasp_prior_reset_quality_success.float().mean(),
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
        if getattr(self, "_grasp_prior_reset_enabled", False):
            self._apply_grasp_prior_reset(env_ids, joint_pos, joint_vel, cube_pos)
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
