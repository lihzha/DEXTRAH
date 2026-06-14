"""Render video evidence for the Franka GraspGen multi-object environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Multi-Object-Grasp")
parser.add_argument("--num_envs", type=int, default=4)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--object_asset_manifest_path", type=str, required=True)
parser.add_argument("--max_objects", type=int, default=4)
parser.add_argument("--object_asset_assignment", type=str, default="round_robin")
parser.add_argument("--object_spawn_center_offset_x", type=float, default=0.05)
parser.add_argument("--object_spawn_center_offset_y", type=float, default=0.0)
parser.add_argument("--object_spawn_xy_randomization", type=float, default=0.10)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=180.0)
parser.add_argument("--object_stable_pose_enabled", action="store_true", default=False)
parser.add_argument("--object_stable_pose_cache_dir", type=str, default="")
parser.add_argument("--object_stable_pose_count", type=int, default=1)
parser.add_argument("--object_stable_pose_randomize", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--object_stable_pose_allow_missing", action="store_true", default=False)
parser.add_argument("--render_warmup_frames", type=int, default=2)
parser.add_argument("--reset_cycles", type=int, default=3)
parser.add_argument("--settle_steps", type=int, default=72)
parser.add_argument("--perturb_steps", type=int, default=96)
parser.add_argument("--perturb_push_steps", type=int, default=10)
parser.add_argument("--perturb_linear_velocity", type=float, default=0.60)
parser.add_argument("--perturb_lateral_velocity", type=float, default=0.20)
parser.add_argument("--perturb_angular_velocity", type=float, default=4.0)
parser.add_argument("--grasp_steps", type=int, default=72)
parser.add_argument("--grasp_object_settle_steps", type=int, default=48)
parser.add_argument("--object_reset_settle_steps", type=int, default=120)
parser.add_argument("--grasp_warmstart_close_width", type=float, default=0.025)
parser.add_argument("--grasp_warmstart_use_prior_close_width", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--grasp_warmstart_prior_close_width_margin", type=float, default=0.003)
parser.add_argument("--grasp_warmstart_min_close_width", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_action_z", type=float, default=0.30)
parser.add_argument("--grasp_warmstart_approach_steps", type=int, default=0)
parser.add_argument("--grasp_warmstart_close_steps", type=int, default=0)
parser.add_argument("--grasp_warmstart_lift_steps", type=int, default=0)
parser.add_argument("--grasp_warmstart_gain", type=float, default=8.0)
parser.add_argument("--grasp_warmstart_max_position_action", type=float, default=1.0)
parser.add_argument("--grasp_warmstart_track_orientation", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--grasp_warmstart_close_max_ee_error", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_max_ee_error", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_max_finger_center_dist", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_closed_width_margin", type=float, default=-1.0)
parser.add_argument("--grasp_warmstart_require_current_lift_ready", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--capture_interval", type=int, default=2)
parser.add_argument("--grasp_reset_attempts", type=int, default=12)
parser.add_argument("--grasp_reset_require_topdown", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--grasp_reset_min_pregrasp_z", type=float, default=0.45)
parser.add_argument("--grasp_reset_candidate_count", type=int, default=16)
parser.add_argument("--grasp_reset_max_center_distance_frac", type=float, default=0.30)
parser.add_argument("--grasp_reset_min_width", type=float, default=0.008)
parser.add_argument("--grasp_prior_verified_indices_path", type=str, default="")
parser.add_argument("--grasp_reset_ik_iterations", type=int, default=None)
parser.add_argument("--grasp_reset_ik_damping", type=float, default=None)
parser.add_argument("--grasp_reset_ik_max_joint_step", type=float, default=None)
parser.add_argument("--grasp_reset_ik_pos_tolerance", type=float, default=None)
parser.add_argument("--grasp_reset_ik_rot_tolerance", type=float, default=None)
parser.add_argument("--grasp_pregrasp_offset", type=float, default=None)
parser.add_argument(
    "--grasp_contact_score_steps",
    type=int,
    default=60,
    help="Unrendered rollout steps for selecting the grasp-contact reset; set 0 to record the first quality reset.",
)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
import isaaclab.utils.math as math_utils
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401


DEFAULT_CAMERA_EYE = (-0.12, -0.90, 1.35)
DEFAULT_CAMERA_TARGET = (-0.40, -0.08, 0.80)


def _resolve_manifest_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _parse_obj_vertices(path: Path, *, scale: float, max_vertices: int = 4096) -> torch.Tensor:
    vertices: list[list[float]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("v "):
                continue
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            vertices.append([scale * float(parts[1]), scale * float(parts[2]), scale * float(parts[3])])
    if not vertices:
        raise ValueError(f"OBJ contains no vertices: {path}")
    stride = max(len(vertices) // max(int(max_vertices), 1), 1)
    return torch.as_tensor(vertices[::stride], dtype=torch.float32)


def _load_manifest_vertex_samples(manifest_path: str | Path, max_objects: int) -> dict[str, torch.Tensor]:
    manifest = Path(str(manifest_path)).expanduser().resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    asset_root = _resolve_manifest_path(str(payload.get("asset_root") or "."), base_dir=manifest.parent)
    records = payload.get("objects")
    if not isinstance(records, list):
        return {}
    if int(max_objects) > 0:
        records = records[: int(max_objects)]
    samples: dict[str, torch.Tensor] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        uuid = str(record.get("uuid") or "")
        raw_object_path = record.get("raw_object_path")
        if not uuid or not raw_object_path:
            continue
        path = _resolve_manifest_path(str(raw_object_path), base_dir=asset_root)
        if not path.is_file():
            continue
        samples[uuid] = _parse_obj_vertices(path, scale=float(record.get("scale", 1.0)))
    return samples


def _attach_validation_vertex_samples(task_env) -> None:
    try:
        samples_by_uuid = _load_manifest_vertex_samples(args_cli.object_asset_manifest_path, args_cli.max_objects)
    except Exception as exc:
        print(f"[WARN] Could not load mesh vertex samples for bottom-clearance checks: {exc}", flush=True)
        samples_by_uuid = {}
    task_env._validation_vertex_samples = [
        samples_by_uuid.get(str(asset.get("uuid", ""))) for asset in getattr(task_env, "_object_assets", [])
    ]


def _as_float(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


def _snapshot_tensor(value):
    if isinstance(value, torch.Tensor):
        return value.detach().clone()
    return value


def _root_state_w(asset) -> torch.Tensor:
    return torch.cat((asset.data.root_pos_w, asset.data.root_quat_w, asset.data.root_vel_w), dim=-1)


def _snapshot_task_tensor_names() -> tuple[str, ...]:
    return (
        "episode_length_buf",
        "reset_buf",
        "actions",
        "robot_dof_targets",
        "arm_joint_pos_target",
        "finger_joint_pos_target",
        "cube_initial_pos",
        "cube_goal_pos",
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "in_success_region",
        "time_in_success_region",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "left_finger_to_cube_dist",
        "right_finger_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_distance_asymmetry",
        "hand_to_cube_mean_dist",
        "hand_to_cube_max_dist",
        "gripper_width",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "cube_pos",
        "cube_quat",
        "cube_vel",
        "ee_pos",
        "ee_quat",
        "left_finger_pos",
        "right_finger_pos",
        "grasp_prior_reset_attempted",
        "grasp_prior_reset_success",
        "grasp_prior_reset_farther",
        "grasp_prior_reset_sample_index",
        "grasp_prior_reset_pos_error",
        "grasp_prior_reset_rot_error",
        "grasp_prior_reset_exact_tool_dist",
        "grasp_prior_reset_pregrasp_tool_dist",
        "grasp_prior_reset_finger_center_dist",
        "grasp_prior_reset_finger_table_clearance",
        "grasp_prior_reset_cube_pos_w",
        "grasp_prior_reset_cube_quat_w",
        "grasp_prior_reset_exact_tool_pos_w",
        "grasp_prior_reset_pregrasp_tool_pos_w",
        "grasp_prior_reset_exact_ee_pos_w",
        "grasp_prior_reset_target_ee_pos_w",
        "grasp_prior_reset_offset_dir_w",
        "grasp_prior_reset_exact_tool_quat_w",
        "grasp_prior_reset_pregrasp_tool_quat_w",
        "grasp_prior_reset_exact_ee_quat_w",
        "grasp_prior_reset_target_ee_quat_w",
        "grasp_prior_reset_left_finger_pos",
        "grasp_prior_reset_right_finger_pos",
        "grasp_prior_reset_left_tip_proxy_pos",
        "grasp_prior_reset_right_tip_proxy_pos",
        "grasp_prior_reset_projected_exact_left_tip_proxy_pos",
        "grasp_prior_reset_projected_exact_right_tip_proxy_pos",
        "grasp_prior_reset_gripper_width",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_offset_radial_dot",
        "grasp_prior_reset_offset_radial_angle",
        "grasp_prior_reset_exact_ee_dist",
        "grasp_prior_reset_pregrasp_ee_dist",
        "grasp_prior_reset_quality_reference_pos_w",
        "grasp_prior_reset_contact_reference_pos_w",
        "grasp_prior_reset_contact_center_dist",
        "grasp_prior_reset_center_gate_dist",
        "grasp_prior_reset_has_contact_location",
        "grasp_prior_reset_candidate_topdown_count",
        "grasp_prior_reset_candidate_contact_height_count",
        "grasp_prior_reset_candidate_center_count",
        "grasp_prior_reset_candidate_width_count",
        "grasp_prior_reset_candidate_table_count",
        "grasp_prior_reset_candidate_valid_count",
        "grasp_prior_reset_candidate_fallback_count",
        "grasp_prior_reset_projected_exact_finger_center_dist",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_pregrasp_tip_table_clearance",
        "grasp_prior_reset_projected_exact_tip_table_clearance",
        "grasp_prior_reset_quality_success",
        "grasp_prior_action_warmstart_active",
        "grasp_prior_action_warmstart_phase",
        "grasp_prior_action_warmstart_policy_actions",
        "grasp_prior_action_warmstart_applied_actions",
        "grasp_prior_action_warmstart_policy_action_z",
        "grasp_prior_action_warmstart_policy_gripper_action",
        "grasp_prior_action_warmstart_applied_action_z",
        "grasp_prior_action_warmstart_applied_gripper_action",
        "grasp_prior_action_warmstart_action_delta_abs",
        "grasp_prior_action_warmstart_exact_ee_error",
        "grasp_prior_action_warmstart_close_width_target",
        "grasp_prior_action_warmstart_reference_finger_center_dist",
        "grasp_prior_action_warmstart_close_latched",
        "grasp_prior_action_warmstart_lift_latched",
    )


def _snapshot_task_env_state(task_env) -> dict[str, object]:
    task_tensors = {}
    for name in _snapshot_task_tensor_names():
        if hasattr(task_env, name):
            task_tensors[name] = _snapshot_tensor(getattr(task_env, name))
    return {
        "version": 1,
        "num_envs": task_env.num_envs,
        "common_step_counter": int(getattr(task_env, "common_step_counter", 0)),
        "sim_step_counter": int(getattr(task_env, "_sim_step_counter", 0)),
        "task_tensors": task_tensors,
        "sim": {
            "robot_root_state": _snapshot_tensor(_root_state_w(task_env._robot)),
            "robot_joint_pos": _snapshot_tensor(task_env._robot.data.joint_pos),
            "robot_joint_vel": _snapshot_tensor(task_env._robot.data.joint_vel),
            "table_root_state": _snapshot_tensor(_root_state_w(task_env._table)),
            "cube_root_state": _snapshot_tensor(_root_state_w(task_env._cube)),
        },
    }


def _restore_task_env_state(task_env, env_state: dict[str, object]) -> None:
    if int(env_state.get("num_envs", task_env.num_envs)) != task_env.num_envs:
        raise ValueError(
            f"Cannot restore env state with num_envs={env_state.get('num_envs')} into num_envs={task_env.num_envs}"
        )
    task_env.common_step_counter = int(
        env_state.get("common_step_counter", getattr(task_env, "common_step_counter", 0))
    )
    if hasattr(task_env, "_sim_step_counter"):
        task_env._sim_step_counter = int(env_state.get("sim_step_counter", task_env._sim_step_counter))

    for name, value in env_state.get("task_tensors", {}).items():
        if isinstance(value, torch.Tensor):
            setattr(task_env, name, value.to(task_env.device).clone())

    sim_state = env_state.get("sim", {})
    if "robot_root_state" in sim_state:
        task_env._robot.write_root_state_to_sim(sim_state["robot_root_state"].to(task_env.device))
    if "robot_joint_pos" in sim_state and "robot_joint_vel" in sim_state:
        task_env._robot.write_joint_state_to_sim(
            sim_state["robot_joint_pos"].to(task_env.device),
            sim_state["robot_joint_vel"].to(task_env.device),
        )
    if "table_root_state" in sim_state:
        task_env._table.write_root_state_to_sim(sim_state["table_root_state"].to(task_env.device))
    if "cube_root_state" in sim_state:
        task_env._cube.write_root_state_to_sim(sim_state["cube_root_state"].to(task_env.device))

    task_env._robot.set_joint_position_target(task_env.arm_joint_pos_target, joint_ids=task_env.arm_joint_ids)
    task_env._robot.set_joint_position_target(task_env.finger_joint_pos_target, joint_ids=task_env.finger_joint_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(update_success_timer=False)


def _configure_camera(task_env, env_id: int = 0) -> None:
    origin = tuple(float(v) for v in task_env.scene.env_origins[env_id].detach().cpu())
    eye = tuple(DEFAULT_CAMERA_EYE[idx] + origin[idx] for idx in range(3))
    target = tuple(DEFAULT_CAMERA_TARGET[idx] + origin[idx] for idx in range(3))
    try:
        task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=task_env.cfg.viewer.cam_prim_path)
    except Exception as exc:
        print(f"[WARN] Could not set validation camera: {exc}", flush=True)


def _object_bottom_z_from_bounds(task_env, env_ids: torch.Tensor) -> torch.Tensor:
    root_pos = task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    root_quat = task_env._cube.data.root_quat_w[env_ids]
    bounds_min = task_env.object_bounds_min[env_ids]
    bounds_max = task_env.object_bounds_max[env_ids]
    corners = []
    for x_index in (0, 1):
        for y_index in (0, 1):
            for z_index in (0, 1):
                corners.append(
                    torch.stack(
                        (
                            bounds_min[:, 0] if x_index == 0 else bounds_max[:, 0],
                            bounds_min[:, 1] if y_index == 0 else bounds_max[:, 1],
                            bounds_min[:, 2] if z_index == 0 else bounds_max[:, 2],
                        ),
                        dim=-1,
                    )
                )
    corner_offsets = torch.stack(corners, dim=1)
    rotated_offsets = torch.einsum("nij,nkj->nki", math_utils.matrix_from_quat(root_quat), corner_offsets)
    return root_pos[:, 2] + rotated_offsets[:, :, 2].min(dim=1).values


def _object_bottom_z(task_env, env_ids: torch.Tensor) -> torch.Tensor:
    samples_by_asset = getattr(task_env, "_validation_vertex_samples", None)
    if not samples_by_asset:
        return _object_bottom_z_from_bounds(task_env, env_ids)

    env_ids = torch.as_tensor(env_ids, device=task_env.device, dtype=torch.long)
    root_pos = task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    root_quat = task_env._cube.data.root_quat_w[env_ids]
    rot_m = math_utils.matrix_from_quat(root_quat)
    object_indices = task_env.object_asset_index[env_ids]
    bottom = torch.empty(env_ids.numel(), dtype=torch.float32, device=task_env.device)
    for object_idx_tensor in torch.unique(object_indices):
        object_idx = int(object_idx_tensor.item())
        local_mask = object_indices == object_idx
        samples = samples_by_asset[object_idx] if object_idx < len(samples_by_asset) else None
        if samples is None:
            bottom[local_mask] = _object_bottom_z_from_bounds(task_env, env_ids[local_mask])
            continue
        vertices = samples.to(device=task_env.device)
        rotated = torch.einsum("nij,kj->nki", rot_m[local_mask], vertices)
        bottom[local_mask] = root_pos[local_mask, 2] + rotated[:, :, 2].min(dim=1).values
    return bottom


def _save_frame(frame, dst: Path) -> str:
    rgb = np.asarray(frame)
    if rgb.ndim == 3 and rgb.shape[-1] >= 3:
        rgb = rgb[..., :3]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        Image.fromarray(rgb).save(dst)
        return str(dst)
    except Exception:
        ppm_path = dst.with_suffix(".ppm")
        header = f"P6\n{rgb.shape[1]} {rgb.shape[0]}\n255\n".encode("ascii")
        ppm_path.write_bytes(header + rgb.tobytes())
        return str(ppm_path)


def _zero_actions(task_env) -> torch.Tensor:
    return torch.zeros((task_env.num_envs, int(task_env.cfg.action_space)), device=task_env.device)


def _step_env(env, task_env, actions: torch.Tensor | None = None):
    actions = _zero_actions(task_env) if actions is None else actions
    task_env._pre_physics_step(actions)
    for _ in range(int(task_env.cfg.decimation)):
        task_env._apply_action()
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(dt=task_env.sim.cfg.dt)
    task_env.episode_length_buf += 1
    if hasattr(task_env, "common_step_counter"):
        task_env.common_step_counter += 1
    task_env._compute_intermediate_values()
    terminated, truncated = task_env._get_dones()
    dones = torch.logical_or(terminated, truncated)
    return None, dones


def _capture(env, scenario_dir: Path, frame_idx: int) -> str:
    return _save_frame(env.render(), scenario_dir / "frames" / f"frame_{frame_idx:04d}.png")


def _warmup_render(env, task_env, frames: int) -> None:
    for _ in range(max(int(frames), 0)):
        _step_env(env, task_env)
        env.render()


def _warmup_render_static(env, frames: int) -> None:
    for _ in range(max(int(frames), 0)):
        env.render()


def _metrics_snapshot(
    task_env,
    dones: torch.Tensor | None = None,
    *,
    reference_pos: torch.Tensor | None = None,
    env_ids: torch.Tensor | None = None,
) -> dict[str, object]:
    if env_ids is None:
        env_ids = task_env._robot._ALL_INDICES
    bottom_z = _object_bottom_z(task_env, env_ids)
    if reference_pos is None:
        reference_pos = task_env.cube_initial_pos
    object_xy_delta = torch.norm(task_env.cube_pos[env_ids, :2] - reference_pos[env_ids, :2], dim=-1)
    object_speed = torch.norm(task_env.cube_vel[env_ids, :3], dim=-1)
    angular_speed = torch.norm(task_env.cube_vel[env_ids, 3:], dim=-1)
    done_count = int(dones[env_ids].float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0
    return {
        "bottom_z_min": float(bottom_z.detach().min().cpu()),
        "table_surface_z": float(task_env.cfg.table_surface_z),
        "bottom_clearance_min": float((bottom_z - float(task_env.cfg.table_surface_z)).detach().min().cpu()),
        "object_xy_delta_max": float(object_xy_delta.detach().max().cpu()),
        "object_speed_max": float(object_speed.detach().max().cpu()),
        "object_angular_speed_max": float(angular_speed.detach().max().cpu()),
        "object_center_z_min": float(task_env.cube_pos[env_ids, 2].detach().min().cpu()),
        "object_center_z_max": float(task_env.cube_pos[env_ids, 2].detach().max().cpu()),
        "finger_table_clearance_min": float(task_env.finger_table_clearance[env_ids].detach().min().cpu()),
        "finger_center_to_object_min": float(task_env.finger_center_to_cube_dist[env_ids].detach().min().cpu()),
        "max_finger_to_object_min": float(task_env.max_finger_to_cube_dist[env_ids].detach().min().cpu()),
        "gripper_width_min": float(task_env.gripper_width[env_ids].detach().min().cpu()),
        "gripper_width_max": float(task_env.gripper_width[env_ids].detach().max().cpu()),
        "episode_length_min": int(task_env.episode_length_buf[env_ids].detach().min().cpu()),
        "episode_length_max": int(task_env.episode_length_buf[env_ids].detach().max().cpu()),
        "done_count": done_count,
    }


def _selected_grasp_geometry_snapshot(task_env, env_id: int) -> dict[str, object]:
    env_ids = torch.tensor([env_id], device=task_env.device, dtype=torch.long)
    origin = task_env.scene.env_origins[env_id]
    hand_pos_w = task_env._robot.data.body_pos_w[env_id, task_env.ee_body_idx]
    hand_quat_w = task_env._robot.data.body_quat_w[env_id, task_env.ee_body_idx]
    exact_tool_pos_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_tool_pos_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    exact_ee_pos_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    target_ee_pos_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    left_finger_pos_w = task_env.left_finger_pos[env_id] + origin
    right_finger_pos_w = task_env.right_finger_pos[env_id] + origin
    object_root_pos_w = task_env._cube.data.root_pos_w[env_id]
    object_root_quat_w = task_env._cube.data.root_quat_w[env_id]
    object_idx = int(task_env.object_asset_index[env_id].detach().cpu())
    asset = task_env._object_assets[object_idx]
    return {
        "selected_asset_index": object_idx,
        "selected_asset_uuid": str(asset.get("uuid", "")),
        "selected_reset_sample_index": int(task_env.grasp_prior_reset_sample_index[env_id].detach().cpu()),
        "selected_reset_success": bool(task_env.grasp_prior_reset_success[env_id].detach().cpu()),
        "selected_quality_success": bool(task_env.grasp_prior_reset_quality_success[env_id].detach().cpu()),
        "selected_reset_pos_error": float(task_env.grasp_prior_reset_pos_error[env_id].detach().cpu()),
        "selected_reset_rot_error": float(task_env.grasp_prior_reset_rot_error[env_id].detach().cpu()),
        "selected_open_width_margin": float(task_env.grasp_prior_reset_open_width_margin[env_id].detach().cpu()),
        "selected_has_contact_location": bool(task_env.grasp_prior_reset_has_contact_location[env_id].detach().cpu()),
        "selected_contact_center_dist": float(task_env.grasp_prior_reset_contact_center_dist[env_id].detach().cpu()),
        "selected_center_gate_dist": float(task_env.grasp_prior_reset_center_gate_dist[env_id].detach().cpu()),
        "selected_candidate_topdown_count": int(
            task_env.grasp_prior_reset_candidate_topdown_count[env_id].detach().cpu()
        ),
        "selected_candidate_contact_height_count": int(
            task_env.grasp_prior_reset_candidate_contact_height_count[env_id].detach().cpu()
        ),
        "selected_candidate_center_count": int(
            task_env.grasp_prior_reset_candidate_center_count[env_id].detach().cpu()
        ),
        "selected_candidate_width_count": int(
            task_env.grasp_prior_reset_candidate_width_count[env_id].detach().cpu()
        ),
        "selected_candidate_table_count": int(
            task_env.grasp_prior_reset_candidate_table_count[env_id].detach().cpu()
        ),
        "selected_candidate_valid_count": int(
            task_env.grasp_prior_reset_candidate_valid_count[env_id].detach().cpu()
        ),
        "selected_candidate_fallback_count": int(
            task_env.grasp_prior_reset_candidate_fallback_count[env_id].detach().cpu()
        ),
        "object_root_pos": _tensor_list(object_root_pos_w - origin),
        "object_root_quat_wxyz": _tensor_list(object_root_quat_w),
        "object_center_pos": _tensor_list(task_env.cube_pos[env_id]),
        "quality_reference_pos": _tensor_list(task_env.grasp_prior_reset_quality_reference_pos_w[env_id] - origin),
        "contact_reference_pos": _tensor_list(task_env.grasp_prior_reset_contact_reference_pos_w[env_id] - origin),
        "hand_pos": _tensor_list(hand_pos_w - origin),
        "hand_quat_wxyz": _tensor_list(hand_quat_w),
        "ee_pos": _tensor_list(task_env.ee_pos[env_id]),
        "ee_quat_wxyz": _tensor_list(task_env.ee_quat[env_id]),
        "left_finger_pos": _tensor_list(task_env.left_finger_pos[env_id]),
        "right_finger_pos": _tensor_list(task_env.right_finger_pos[env_id]),
        "exact_tool_pos": _tensor_list(exact_tool_pos_w - origin),
        "pregrasp_tool_pos": _tensor_list(pregrasp_tool_pos_w - origin),
        "exact_ee_pos": _tensor_list(exact_ee_pos_w - origin),
        "target_ee_pos": _tensor_list(target_ee_pos_w - origin),
        "pregrasp_tool_to_hand_dist": float(torch.norm(pregrasp_tool_pos_w - hand_pos_w).detach().cpu()),
        "target_ee_to_ee_dist": float(torch.norm((target_ee_pos_w - origin) - task_env.ee_pos[env_id]).detach().cpu()),
        "exact_tool_to_finger_center_dist": float(
            torch.norm(exact_tool_pos_w - 0.5 * (left_finger_pos_w + right_finger_pos_w)).detach().cpu()
        ),
        "exact_ee_to_ee_dist": float(torch.norm((exact_ee_pos_w - origin) - task_env.ee_pos[env_id]).detach().cpu()),
        "object_size": float(task_env._grasp_prior_object_size(env_ids)[0].detach().cpu()),
    }


def _summarize_series(series: list[dict[str, object]]) -> dict[str, object]:
    keys = [
        "bottom_clearance_min",
        "object_xy_delta_max",
        "object_speed_max",
        "object_angular_speed_max",
        "object_center_z_max",
        "finger_table_clearance_min",
        "finger_center_to_object_min",
        "max_finger_to_object_min",
        "episode_length_max",
        "done_count",
    ]
    summary: dict[str, object] = {"samples": len(series)}
    for key in keys:
        values = [float(item[key]) for item in series if key in item]
        if not values:
            continue
        if key.endswith("_min") or key in ("bottom_clearance_min", "finger_table_clearance_min"):
            summary[key] = min(values)
        else:
            summary[key] = max(values)
    return summary


def _record_reset_settle(env, task_env, output_dir: Path) -> dict[str, object]:
    scenario_dir = output_dir / "reset_settle"
    frame_idx = 0
    series: list[dict[str, object]] = []
    artifact_paths: list[str] = []
    for cycle in range(max(int(args_cli.reset_cycles), 1)):
        env.reset()
        _configure_camera(task_env, env_id=0)
        _warmup_render(env, task_env, args_cli.render_warmup_frames)
        reference_pos = task_env.cube_pos.clone()
        for step in range(max(int(args_cli.settle_steps), 1)):
            _, dones = _step_env(env, task_env)
            if step % max(int(args_cli.capture_interval), 1) == 0:
                artifact_paths.append(_capture(env, scenario_dir, frame_idx))
                frame_idx += 1
            snap = _metrics_snapshot(task_env, dones, reference_pos=reference_pos)
            snap.update({"cycle": cycle, "step": step})
            series.append(snap)
    summary = _summarize_series(series)
    passed = (
        float(summary.get("bottom_clearance_min", -1.0)) >= -0.005
        and float(summary.get("object_xy_delta_max", 999.0)) <= 0.18
        and int(summary.get("done_count", 1)) == 0
    )
    return {"passed": passed, "summary": summary, "frames": artifact_paths}


def _record_perturbation(env, task_env, output_dir: Path) -> dict[str, object]:
    scenario_dir = output_dir / "perturbation"
    env.reset()
    _configure_camera(task_env, env_id=0)
    _warmup_render(env, task_env, args_cli.render_warmup_frames)
    reference_pos = task_env.cube_pos.clone()
    env_ids = task_env._robot._ALL_INDICES
    velocity = torch.zeros((task_env.num_envs, 6), device=task_env.device)
    signs = torch.where(torch.arange(task_env.num_envs, device=task_env.device) % 2 == 0, 1.0, -1.0)
    velocity[:, 0] = float(args_cli.perturb_linear_velocity) * signs
    velocity[:, 1] = float(args_cli.perturb_lateral_velocity) * torch.roll(signs, shifts=1)
    velocity[:, 5] = float(args_cli.perturb_angular_velocity) * signs
    task_env._cube.write_root_velocity_to_sim(velocity, env_ids=env_ids)
    task_env._compute_intermediate_values()

    frame_idx = 0
    series: list[dict[str, object]] = []
    artifact_paths: list[str] = []
    for step in range(max(int(args_cli.perturb_steps), 1)):
        if step < max(int(args_cli.perturb_push_steps), 1):
            task_env._cube.write_root_velocity_to_sim(velocity, env_ids=env_ids)
        _, dones = _step_env(env, task_env)
        if step % max(int(args_cli.capture_interval), 1) == 0:
            artifact_paths.append(_capture(env, scenario_dir, frame_idx))
            frame_idx += 1
        snap = _metrics_snapshot(task_env, dones, reference_pos=reference_pos)
        snap.update({"step": step})
        series.append(snap)
    summary = _summarize_series(series)
    passed = (
        float(summary.get("bottom_clearance_min", -1.0)) >= -0.01
        and float(summary.get("object_xy_delta_max", 0.0)) >= 0.01
        and float(summary.get("object_xy_delta_max", 999.0)) <= 0.35
        and float(summary.get("object_center_z_max", 999.0)) <= 1.20
    )
    return {"passed": passed, "summary": summary, "frames": artifact_paths}


def _refresh_object_references(task_env, env_ids: torch.Tensor) -> None:
    env_origins = task_env.scene.env_origins[env_ids]
    object_root_pos = task_env._cube.data.root_pos_w[env_ids] - env_origins
    object_root_quat = task_env._cube.data.root_quat_w[env_ids]
    center_pos = task_env._object_center_pos_from_root(env_ids, object_root_pos, object_root_quat)
    task_env.cube_initial_pos[env_ids] = center_pos
    task_env.cube_goal_pos[env_ids] = center_pos
    task_env.cube_goal_pos[env_ids, 2] = center_pos[:, 2] + float(task_env.cfg.cube_lift_height)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env._compute_intermediate_values(env_ids)


def _reset_settled_object_then_apply_grasp_prior(env, task_env) -> None:
    env_ids = task_env._robot._ALL_INDICES
    prior_enabled = bool(getattr(task_env, "_grasp_prior_reset_enabled", False))
    task_env._grasp_prior_reset_enabled = False
    env.reset()
    for _ in range(max(int(args_cli.grasp_object_settle_steps), 0)):
        _step_env(env, task_env)
    zero_vel = torch.zeros((task_env.num_envs, 6), device=task_env.device)
    task_env._cube.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    _refresh_object_references(task_env, env_ids)

    object_root_pos = task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    object_root_quat = task_env._cube.data.root_quat_w[env_ids]
    baseline_joint_pos = task_env._robot.data.default_joint_pos[env_ids].clone()
    joint_vel = torch.zeros_like(baseline_joint_pos)
    task_env._reset_grasp_prior_metrics(env_ids)
    task_env._grasp_prior_reset_enabled = prior_enabled
    task_env._apply_grasp_prior_reset(env_ids, baseline_joint_pos, joint_vel, object_root_pos, object_root_quat)
    max_attempts = max(int(args_cli.grasp_reset_attempts), 1)
    for _ in range(1, max_attempts):
        retry_mask = ~task_env.grasp_prior_reset_quality_success[env_ids]
        if not bool(retry_mask.any().item()):
            break
        retry_env_ids = env_ids[retry_mask]
        task_env._reset_grasp_prior_metrics(retry_env_ids)
        task_env._apply_grasp_prior_reset(
            retry_env_ids,
            baseline_joint_pos[retry_mask],
            joint_vel[retry_mask],
            object_root_pos[retry_mask],
            object_root_quat[retry_mask],
        )
    task_env.episode_length_buf[env_ids] = 0
    task_env.ik_controller.reset(env_ids)
    task_env._compute_intermediate_values(env_ids)


def _candidate_contact_envs(task_env) -> list[int]:
    min_pregrasp_z = float(args_cli.grasp_reset_min_pregrasp_z)
    quality = task_env.grasp_prior_reset_quality_success
    if bool(args_cli.grasp_reset_require_topdown):
        quality = quality & (task_env.grasp_prior_reset_offset_dir_w[:, 2] >= min_pregrasp_z)
    ordered: list[int] = []
    if not bool(quality.any().item()):
        return ordered
    env_ids = torch.nonzero(quality, as_tuple=False).flatten()
    z_values = task_env.grasp_prior_reset_offset_dir_w[env_ids, 2]
    order = torch.argsort(z_values, descending=True)
    ordered.extend(int(env_ids[index].item()) for index in order)
    return ordered


def _score_grasp_contact_result(result: dict[str, object]) -> float:
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    done_count = int(result.get("selected_done_count", 999))
    object_xy = float(summary.get("object_xy_delta_max", 999.0))
    bottom_clearance = float(summary.get("bottom_clearance_min", -999.0))
    finger_clearance = float(summary.get("finger_table_clearance_min", -999.0))
    finger_dist = float(result.get("selected_max_finger_dist_min", 999.0))
    lift_height = float(result.get("selected_lift_height_max", 0.0))
    pregrasp_z = float(result.get("selected_pregrasp_offset_dir_z", -999.0))
    phases = result.get("warmstart_phases", [])
    phase_bonus = 1.0 if isinstance(phases, list) and (1 in phases or 2 in phases) else 0.0
    return (
        (1000.0 if bool(result.get("passed", False)) else 0.0)
        + (250.0 if done_count == 0 else -50.0 * done_count)
        + 30.0 * phase_bonus
        + 10.0 * pregrasp_z
        + 500.0 * min(lift_height, 0.08)
        + 5.0 * min(finger_clearance, 0.10)
        + 5.0 * min(bottom_clearance, 0.02)
        - 150.0 * object_xy
        - 5.0 * finger_dist
    )


def _rollout_grasp_contact(
    env,
    task_env,
    *,
    selected_env: int,
    steps: int,
    scenario_dir: Path | None = None,
) -> dict[str, object]:
    frame_idx = 0
    series: list[dict[str, object]] = []
    artifact_paths: list[str] = []
    phase_values: list[int] = []
    active_values: list[bool] = []
    selected_done_count = 0
    reset_geometry = _selected_grasp_geometry_snapshot(task_env, selected_env)
    selected_env_ids = torch.tensor([selected_env], device=task_env.device, dtype=torch.long)
    if scenario_dir is not None:
        artifact_paths.append(_capture(env, scenario_dir, frame_idx))
        frame_idx += 1
    for step in range(max(int(steps), 1)):
        _, dones = _step_env(env, task_env)
        if hasattr(task_env, "grasp_prior_action_warmstart_phase"):
            phase_values.append(int(task_env.grasp_prior_action_warmstart_phase[selected_env].detach().cpu()))
            active_values.append(bool(task_env.grasp_prior_action_warmstart_active[selected_env].detach().cpu()))
        selected_done_count += int(dones[selected_env].detach().cpu())
        if scenario_dir is not None and step % max(int(args_cli.capture_interval), 1) == 0:
            artifact_paths.append(_capture(env, scenario_dir, frame_idx))
            frame_idx += 1
        snap = _metrics_snapshot(task_env, dones, env_ids=selected_env_ids)
        snap.update(
            {
                "step": step,
                "selected_env": selected_env,
                "selected_lift_height": float(task_env.cube_lift_height[selected_env].detach().cpu()),
                "selected_finger_center_dist": float(task_env.finger_center_to_cube_dist[selected_env].detach().cpu()),
                "selected_reference_finger_center_dist": float(
                    task_env.grasp_prior_action_warmstart_reference_finger_center_dist[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_reference_finger_center_dist")
                else 0.0,
                "selected_max_finger_dist": float(task_env.max_finger_to_cube_dist[selected_env].detach().cpu()),
                "selected_gripper_width": float(task_env.gripper_width[selected_env].detach().cpu()),
                "selected_warmstart_phase": int(
                    task_env.grasp_prior_action_warmstart_phase[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_phase")
                else -1,
                "selected_warmstart_close_latched": bool(
                    task_env.grasp_prior_action_warmstart_close_latched[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_close_latched")
                else False,
                "selected_warmstart_lift_latched": bool(
                    task_env.grasp_prior_action_warmstart_lift_latched[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_lift_latched")
                else False,
                "selected_warmstart_exact_ee_error": float(
                    task_env.grasp_prior_action_warmstart_exact_ee_error[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_exact_ee_error")
                else 0.0,
                "selected_warmstart_close_width_target": float(
                    task_env.grasp_prior_action_warmstart_close_width_target[selected_env].detach().cpu()
                )
                if hasattr(task_env, "grasp_prior_action_warmstart_close_width_target")
                else 0.0,
                "selected_episode_length": int(task_env.episode_length_buf[selected_env].detach().cpu()),
                "selected_reset_success": bool(task_env.grasp_prior_reset_success[selected_env].detach().cpu()),
                "selected_quality_success": bool(task_env.grasp_prior_reset_quality_success[selected_env].detach().cpu()),
                "selected_projected_tip_center_dist": float(
                    task_env.grasp_prior_reset_projected_exact_tip_center_dist[selected_env].detach().cpu()
                ),
                "selected_projected_tip_max_dist": float(
                    task_env.grasp_prior_reset_projected_exact_tip_max_dist[selected_env].detach().cpu()
                ),
                "selected_pregrasp_offset_dir_z": float(
                    task_env.grasp_prior_reset_offset_dir_w[selected_env, 2].detach().cpu()
                ),
                "selected_object_size": float(
                    task_env._grasp_prior_object_size(selected_env_ids)[0].detach().cpu()
                ),
            }
        )
        series.append(snap)

    summary = _summarize_series(series)
    selected_lift = max(float(item["selected_lift_height"]) for item in series)
    selected_max_finger = min(float(item["selected_max_finger_dist"]) for item in series)
    selected_reference_finger = min(float(item["selected_reference_finger_center_dist"]) for item in series)
    selected_width = min(float(item["selected_gripper_width"]) for item in series)
    selected_object_size = max(float(item["selected_object_size"]) for item in series)
    selected_tip_max = min(float(item["selected_projected_tip_max_dist"]) for item in series)
    selected_pregrasp_z = max(float(item["selected_pregrasp_offset_dir_z"]) for item in series)
    selected_object_xy_delta = float(summary.get("object_xy_delta_max", 999.0))
    max_contact_xy_delta = min(0.06, 0.75 * float(task_env.cfg.prelift_drag_termination_xy_error))
    min_lift_height = max(0.02, float(task_env.cfg.cube_success_lift_height))
    phases = sorted(set(phase_values))
    passed = (
        bool(task_env.grasp_prior_reset_quality_success[selected_env].detach().cpu())
        and selected_pregrasp_z >= float(args_cli.grasp_reset_min_pregrasp_z)
        and selected_lift >= min_lift_height
        and float(summary.get("bottom_clearance_min", -1.0)) >= -0.01
        and float(summary.get("finger_table_clearance_min", -1.0)) >= float(task_env.cfg.finger_table_penetration_termination_margin)
        and selected_done_count == 0
        and selected_object_xy_delta <= max_contact_xy_delta
        and (1 in phases or 2 in phases)
        and selected_tip_max <= 1.25 * selected_object_size
        and selected_width <= float(task_env.cfg.max_gripper_width)
    )
    return {
        "passed": passed,
        "summary": summary,
        "selected_env": selected_env,
        "selected_lift_height_max": selected_lift,
        "selected_max_finger_dist_min": selected_max_finger,
        "selected_reference_finger_center_dist_min": selected_reference_finger,
        "selected_gripper_width_min": selected_width,
        "selected_projected_tip_max_dist_min": selected_tip_max,
        "selected_pregrasp_offset_dir_z": selected_pregrasp_z,
        "selected_object_size": selected_object_size,
        "selected_object_xy_delta_max": selected_object_xy_delta,
        "selected_contact_xy_delta_threshold": max_contact_xy_delta,
        "selected_lift_height_threshold": min_lift_height,
        "selected_done_count": selected_done_count,
        "warmstart_phases": phases,
        "warmstart_active_count": sum(1 for item in active_values if item),
        "reset_geometry": reset_geometry,
        "frames": artifact_paths,
    }


def _select_scored_grasp_contact_state(env, task_env) -> tuple[int, dict[str, object]]:
    best_state: dict[str, object] | None = None
    best_result: dict[str, object] | None = None
    best_score = -float("inf")
    attempts = max(int(args_cli.grasp_reset_attempts), 1)
    warmstart_steps = (
        max(int(task_env.cfg.grasp_prior_action_warmstart_approach_steps), 0)
        + max(int(task_env.cfg.grasp_prior_action_warmstart_close_steps), 0)
        + max(int(task_env.cfg.grasp_prior_action_warmstart_lift_steps), 0)
    )
    requested_score_steps = int(args_cli.grasp_contact_score_steps)
    score_steps = 0 if requested_score_steps <= 0 else max(requested_score_steps, warmstart_steps, 1)

    for attempt in range(attempts):
        _reset_settled_object_then_apply_grasp_prior(env, task_env)
        candidate_envs = _candidate_contact_envs(task_env)
        if not candidate_envs:
            continue
        if score_steps <= 0:
            selected_env = int(candidate_envs[0])
            return selected_env, {
                "passed": False,
                "selection_attempt": attempt,
                "selection_candidates": candidate_envs,
                "selection_scoring": False,
                "selection_score_steps": 0,
                "selection_score": 0.0,
                "selected_env": selected_env,
            }
        reset_state = _snapshot_task_env_state(task_env)
        for selected_env in candidate_envs:
            _restore_task_env_state(task_env, reset_state)
            candidate_state = _snapshot_task_env_state(task_env)
            result = _rollout_grasp_contact(env, task_env, selected_env=selected_env, steps=score_steps)
            result["selection_attempt"] = attempt
            result["selection_score_steps"] = score_steps
            score = _score_grasp_contact_result(result)
            result["selection_score"] = score
            if score > best_score:
                best_score = score
                best_state = candidate_state
                best_result = result
            if bool(result.get("passed", False)):
                _restore_task_env_state(task_env, candidate_state)
                return selected_env, result
        _restore_task_env_state(task_env, reset_state)

    if best_state is None or best_result is None:
        _reset_settled_object_then_apply_grasp_prior(env, task_env)
        selected_env = 0
        return selected_env, {
            "passed": False,
            "selection_failure": "no_quality_candidate",
            "selection_score": best_score,
            "selected_env": selected_env,
        }

    _restore_task_env_state(task_env, best_state)
    return int(best_result["selected_env"]), best_result


def _record_grasp_contact(env, task_env, output_dir: Path) -> dict[str, object]:
    scenario_dir = output_dir / "grasp_contact"
    selected_env, probe_result = _select_scored_grasp_contact_state(env, task_env)
    _configure_camera(task_env, env_id=selected_env)
    _warmup_render_static(env, args_cli.render_warmup_frames)
    result = _rollout_grasp_contact(
        env,
        task_env,
        selected_env=selected_env,
        steps=max(int(args_cli.grasp_steps), 1),
        scenario_dir=scenario_dir,
    )
    result["selection_probe"] = {k: v for k, v in probe_result.items() if k != "frames"}
    return result


def _make_env(*, grasp_prior: bool):
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    env_cfg.object_asset_manifest_path = str(Path(args_cli.object_asset_manifest_path).expanduser().resolve())
    env_cfg.max_objects = int(args_cli.max_objects)
    env_cfg.object_asset_assignment = str(args_cli.object_asset_assignment)
    env_cfg.object_spawn_center_offset_x = float(args_cli.object_spawn_center_offset_x)
    env_cfg.object_spawn_center_offset_y = float(args_cli.object_spawn_center_offset_y)
    env_cfg.object_spawn_xy_randomization = float(args_cli.object_spawn_xy_randomization)
    env_cfg.object_spawn_yaw_randomization_deg = float(args_cli.object_spawn_yaw_randomization_deg)
    env_cfg.object_stable_pose_enabled = bool(args_cli.object_stable_pose_enabled)
    env_cfg.object_stable_pose_cache_dir = str(args_cli.object_stable_pose_cache_dir)
    env_cfg.object_stable_pose_count = int(args_cli.object_stable_pose_count)
    env_cfg.object_stable_pose_randomize = bool(args_cli.object_stable_pose_randomize)
    env_cfg.object_stable_pose_allow_missing = bool(args_cli.object_stable_pose_allow_missing)
    env_cfg.object_reset_settle_steps = int(args_cli.object_reset_settle_steps)
    env_cfg.object_reset_settle_full_reset_only = True
    env_cfg.grasp_prior_reset_enabled = bool(grasp_prior)
    env_cfg.grasp_prior_action_warmstart_enabled = bool(grasp_prior)
    env_cfg.grasp_prior_reset_attempts = int(args_cli.grasp_reset_attempts)
    env_cfg.grasp_prior_reset_candidate_count = int(args_cli.grasp_reset_candidate_count)
    env_cfg.grasp_prior_reset_require_topdown = bool(args_cli.grasp_reset_require_topdown)
    env_cfg.grasp_prior_reset_min_pregrasp_z = float(args_cli.grasp_reset_min_pregrasp_z)
    env_cfg.grasp_prior_reset_max_center_distance_frac = float(args_cli.grasp_reset_max_center_distance_frac)
    env_cfg.grasp_prior_reset_min_width = float(args_cli.grasp_reset_min_width)
    env_cfg.grasp_prior_verified_indices_path = str(args_cli.grasp_prior_verified_indices_path)
    if args_cli.grasp_reset_ik_iterations is not None:
        env_cfg.grasp_prior_reset_ik_iterations = int(args_cli.grasp_reset_ik_iterations)
    if args_cli.grasp_reset_ik_damping is not None:
        env_cfg.grasp_prior_reset_ik_damping = float(args_cli.grasp_reset_ik_damping)
    if args_cli.grasp_reset_ik_max_joint_step is not None:
        env_cfg.grasp_prior_reset_ik_max_joint_step = float(args_cli.grasp_reset_ik_max_joint_step)
    if args_cli.grasp_reset_ik_pos_tolerance is not None:
        env_cfg.grasp_prior_reset_ik_pos_tolerance = float(args_cli.grasp_reset_ik_pos_tolerance)
    if args_cli.grasp_reset_ik_rot_tolerance is not None:
        env_cfg.grasp_prior_reset_ik_rot_tolerance = float(args_cli.grasp_reset_ik_rot_tolerance)
    if args_cli.grasp_pregrasp_offset is not None:
        env_cfg.grasp_prior_pregrasp_offset = float(args_cli.grasp_pregrasp_offset)
    if grasp_prior:
        grasp_steps = max(int(args_cli.grasp_steps), 1)
        approach_steps = max(int(args_cli.grasp_warmstart_approach_steps), 0)
        close_steps = max(int(args_cli.grasp_warmstart_close_steps), 0)
        lift_steps = max(int(args_cli.grasp_warmstart_lift_steps), 0)
        if approach_steps + close_steps + lift_steps <= 0:
            approach_steps = min(20, max(grasp_steps // 3, 1))
            close_steps = min(20, max(grasp_steps // 3, 1))
            if approach_steps + close_steps >= grasp_steps:
                close_steps = max(grasp_steps - approach_steps - 1, 0)
            lift_steps = max(grasp_steps - approach_steps - close_steps, 1)
        env_cfg.grasp_prior_action_warmstart_close_width = float(args_cli.grasp_warmstart_close_width)
        env_cfg.grasp_prior_action_warmstart_use_prior_close_width = bool(
            args_cli.grasp_warmstart_use_prior_close_width
        )
        env_cfg.grasp_prior_action_warmstart_prior_close_width_margin = float(
            args_cli.grasp_warmstart_prior_close_width_margin
        )
        env_cfg.grasp_prior_action_warmstart_min_close_width = float(args_cli.grasp_warmstart_min_close_width)
        env_cfg.grasp_prior_action_warmstart_lift_action_z = float(args_cli.grasp_warmstart_lift_action_z)
        env_cfg.grasp_prior_action_warmstart_approach_steps = approach_steps
        env_cfg.grasp_prior_action_warmstart_close_steps = close_steps
        env_cfg.grasp_prior_action_warmstart_lift_steps = lift_steps
        env_cfg.grasp_prior_action_warmstart_gain = float(args_cli.grasp_warmstart_gain)
        env_cfg.grasp_prior_action_warmstart_max_position_action = float(args_cli.grasp_warmstart_max_position_action)
        env_cfg.grasp_prior_action_warmstart_track_orientation = bool(args_cli.grasp_warmstart_track_orientation)
        env_cfg.grasp_prior_action_warmstart_close_max_ee_error = float(
            args_cli.grasp_warmstart_close_max_ee_error
        )
        env_cfg.grasp_prior_action_warmstart_lift_max_ee_error = float(
            args_cli.grasp_warmstart_lift_max_ee_error
        )
        env_cfg.grasp_prior_action_warmstart_lift_max_finger_center_dist = float(
            args_cli.grasp_warmstart_lift_max_finger_center_dist
        )
        env_cfg.grasp_prior_action_warmstart_lift_closed_width_margin = float(
            args_cli.grasp_warmstart_lift_closed_width_margin
        )
        if args_cli.grasp_warmstart_require_current_lift_ready is not None:
            env_cfg.grasp_prior_action_warmstart_require_current_lift_ready = bool(
                args_cli.grasp_warmstart_require_current_lift_ready
            )
    env_cfg.grasp_prior_allow_missing = False
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = env.unwrapped
    _attach_validation_vertex_samples(task_env)
    _configure_camera(task_env, env_id=0)
    return env, task_env


def _set_grasp_prior_runtime_enabled(task_env, enabled: bool) -> bool:
    previous = bool(getattr(task_env, "_grasp_prior_reset_enabled", False))
    task_env._grasp_prior_reset_enabled = bool(enabled)
    return previous


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_multi_object_video_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "video_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    env, task_env = _make_env(grasp_prior=True)
    scenarios: dict[str, dict[str, object]] = {}
    prior_enabled = _set_grasp_prior_runtime_enabled(task_env, False)
    try:
        print("[INFO] Recording reset_settle with grasp-prior resets disabled", flush=True)
        scenarios["reset_settle"] = _record_reset_settle(env, task_env, output_dir)
        print("[INFO] Recording perturbation with grasp-prior resets disabled", flush=True)
        scenarios["perturbation"] = _record_perturbation(env, task_env, output_dir)
    finally:
        _set_grasp_prior_runtime_enabled(task_env, prior_enabled)

    _set_grasp_prior_runtime_enabled(task_env, True)
    print("[INFO] Recording grasp_contact with settled-object grasp-prior reset", flush=True)
    scenarios["grasp_contact"] = _record_grasp_contact(env, task_env, output_dir)
    resolved_env_cfg = task_env.cfg
    payload = {
        "passed": all(bool(item.get("passed", False)) for item in scenarios.values()),
        "scenarios": scenarios,
        "config": {
            "task": args_cli.task,
            "num_envs": args_cli.num_envs,
            "seed": args_cli.seed,
            "object_asset_manifest_path": str(args_cli.object_asset_manifest_path),
            "max_objects": args_cli.max_objects,
            "object_asset_assignment": str(args_cli.object_asset_assignment),
            "object_spawn_center_offset_x": args_cli.object_spawn_center_offset_x,
            "object_spawn_center_offset_y": args_cli.object_spawn_center_offset_y,
            "object_spawn_xy_randomization": args_cli.object_spawn_xy_randomization,
            "object_spawn_yaw_randomization_deg": args_cli.object_spawn_yaw_randomization_deg,
            "object_stable_pose_enabled": args_cli.object_stable_pose_enabled,
            "object_stable_pose_cache_dir": args_cli.object_stable_pose_cache_dir,
            "object_stable_pose_count": args_cli.object_stable_pose_count,
            "object_stable_pose_randomize": args_cli.object_stable_pose_randomize,
            "object_stable_pose_allow_missing": args_cli.object_stable_pose_allow_missing,
            "capture_interval": args_cli.capture_interval,
            "grasp_object_settle_steps": args_cli.grasp_object_settle_steps,
            "object_reset_settle_steps": args_cli.object_reset_settle_steps,
            "grasp_warmstart_close_width": args_cli.grasp_warmstart_close_width,
            "grasp_warmstart_use_prior_close_width": args_cli.grasp_warmstart_use_prior_close_width,
            "grasp_warmstart_prior_close_width_margin": args_cli.grasp_warmstart_prior_close_width_margin,
            "grasp_warmstart_min_close_width": args_cli.grasp_warmstart_min_close_width,
            "grasp_warmstart_lift_action_z": args_cli.grasp_warmstart_lift_action_z,
            "grasp_warmstart_approach_steps": args_cli.grasp_warmstart_approach_steps,
            "grasp_warmstart_close_steps": args_cli.grasp_warmstart_close_steps,
            "grasp_warmstart_lift_steps": args_cli.grasp_warmstart_lift_steps,
            "grasp_warmstart_gain": args_cli.grasp_warmstart_gain,
            "grasp_warmstart_max_position_action": args_cli.grasp_warmstart_max_position_action,
            "grasp_warmstart_track_orientation": args_cli.grasp_warmstart_track_orientation,
            "grasp_warmstart_close_max_ee_error": args_cli.grasp_warmstart_close_max_ee_error,
            "grasp_warmstart_lift_max_ee_error": args_cli.grasp_warmstart_lift_max_ee_error,
            "grasp_warmstart_lift_max_finger_center_dist": args_cli.grasp_warmstart_lift_max_finger_center_dist,
            "grasp_warmstart_lift_closed_width_margin": args_cli.grasp_warmstart_lift_closed_width_margin,
            "grasp_warmstart_require_current_lift_ready": getattr(
                resolved_env_cfg, "grasp_prior_action_warmstart_require_current_lift_ready", None
            ),
            "grasp_reset_require_topdown": args_cli.grasp_reset_require_topdown,
            "grasp_reset_min_pregrasp_z": args_cli.grasp_reset_min_pregrasp_z,
            "grasp_reset_min_contact_height_above_center": getattr(
                resolved_env_cfg, "grasp_prior_reset_min_contact_height_above_center", None
            ),
            "grasp_prior_verified_indices_path": args_cli.grasp_prior_verified_indices_path,
            "grasp_reset_ik_iterations": getattr(resolved_env_cfg, "grasp_prior_reset_ik_iterations", None),
            "grasp_reset_ik_damping": getattr(resolved_env_cfg, "grasp_prior_reset_ik_damping", None),
            "grasp_reset_ik_max_joint_step": getattr(resolved_env_cfg, "grasp_prior_reset_ik_max_joint_step", None),
            "grasp_reset_ik_pos_tolerance": getattr(resolved_env_cfg, "grasp_prior_reset_ik_pos_tolerance", None),
            "grasp_reset_ik_rot_tolerance": getattr(resolved_env_cfg, "grasp_prior_reset_ik_rot_tolerance", None),
            "grasp_pregrasp_offset": args_cli.grasp_pregrasp_offset,
            "grasp_contact_score_steps": args_cli.grasp_contact_score_steps,
            "perturb_push_steps": args_cli.perturb_push_steps,
            "perturb_linear_velocity": args_cli.perturb_linear_velocity,
            "perturb_lateral_velocity": args_cli.perturb_lateral_velocity,
            "perturb_angular_velocity": args_cli.perturb_angular_velocity,
        },
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] Wrote video metrics to {metrics_path}", flush=True)
    env.close()
    simulation_app.close()
    if not payload["passed"]:
        failed = [name for name, item in scenarios.items() if not bool(item.get("passed", False))]
        raise SystemExit(f"Video validation failed: {failed}")
    print("DEXTRAH_FRANKA_MULTI_OBJECT_VIDEO_VALIDATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
