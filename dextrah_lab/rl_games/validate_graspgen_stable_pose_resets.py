"""Validate trimesh stable poses by placing GraspGen objects exactly in Isaac Lab."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import time

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Multi-Object-Grasp")
parser.add_argument("--object_asset_manifest_path", type=str, required=True)
parser.add_argument("--max_objects", type=int, default=4)
parser.add_argument("--object_uuids", type=str, default="")
parser.add_argument("--stable_pose_count", type=int, default=1)
parser.add_argument("--stable_pose_mesh_mode", type=str, default="convex_hull", choices=("convex_hull", "visual"))
parser.add_argument("--stable_pose_sigma", type=float, default=0.0)
parser.add_argument("--stable_pose_samples", type=int, default=1)
parser.add_argument("--stable_pose_threshold", type=float, default=0.0)
parser.add_argument("--settle_steps", type=int, default=240)
parser.add_argument("--settled_replay_steps", type=int, default=0)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--table_clearance", type=float, default=0.002)
parser.add_argument("--max_root_xy_drift", type=float, default=0.01)
parser.add_argument("--max_center_xy_drift", type=float, default=0.01)
parser.add_argument("--max_root_z_drift", type=float, default=0.02)
parser.add_argument("--max_angular_drift_deg", type=float, default=5.0)
parser.add_argument("--min_bottom_clearance", type=float, default=-0.005)
parser.add_argument("--max_final_speed", type=float, default=0.03)
parser.add_argument("--fail_on_task_done", action="store_true", default=False)
parser.add_argument("--render_frames", action="store_true", default=False)
parser.add_argument("--capture_interval", type=int, default=24)
parser.add_argument("--render_warmup_frames", type=int, default=2)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.render_frames:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch
import trimesh

import isaaclab_tasks  # noqa: F401
import isaaclab.utils.math as math_utils
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401


DEFAULT_CAMERA_EYE = (-0.14, -0.82, 1.35)
DEFAULT_CAMERA_TARGET = (-0.40, -0.06, 0.80)


def _resolve_manifest_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_selected_manifest(output_dir: Path) -> tuple[Path, list[dict[str, object]], Path]:
    manifest_path = Path(args_cli.object_asset_manifest_path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = payload.get("objects")
    if not isinstance(records, list):
        raise ValueError(f"Expected objects list in {manifest_path}")
    asset_root = _resolve_manifest_path(str(payload.get("asset_root") or "."), base_dir=manifest_path.parent)

    requested = [item.strip() for item in str(args_cli.object_uuids).split(",") if item.strip()]
    if requested:
        by_uuid = {str(record.get("uuid", "")): record for record in records if isinstance(record, dict)}
        missing = [uuid for uuid in requested if uuid not in by_uuid]
        if missing:
            raise ValueError(f"Requested UUIDs are not present in manifest: {missing}")
        selected = [dict(by_uuid[uuid]) for uuid in requested]
    else:
        limit = max(int(args_cli.max_objects), 1)
        selected = [dict(record) for record in records[:limit] if isinstance(record, dict)]
    if not selected:
        raise ValueError("No objects selected for stable-pose validation")

    filtered_payload = dict(payload)
    filtered_payload["asset_root"] = str(asset_root)
    filtered_payload["objects"] = selected
    filtered_manifest = output_dir / "selected_manifest.json"
    filtered_manifest.write_text(json.dumps(filtered_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return filtered_manifest, selected, asset_root


def _load_scaled_mesh(record: dict[str, object], asset_root: Path) -> trimesh.Trimesh:
    raw_value = record.get("raw_object_path")
    if not raw_value:
        raise ValueError(f"Object {record.get('uuid')} does not include raw_object_path")
    raw_path = _resolve_manifest_path(str(raw_value), base_dir=asset_root)
    if not raw_path.is_file():
        raise FileNotFoundError(f"Missing raw OBJ for {record.get('uuid')}: {raw_path}")
    loaded = trimesh.load(raw_path, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [geom for geom in loaded.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"Scene contains no meshes: {raw_path}")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unsupported trimesh load result for {raw_path}: {type(loaded).__name__}")
    mesh = mesh.copy()
    scale = float(record.get("scale", 1.0))
    mesh.apply_scale(scale)
    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        raise ValueError(f"Mesh has no vertices/faces after scaling: {raw_path}")
    return mesh


def _make_stable_pose_mesh(mesh: trimesh.Trimesh, *, uuid: str) -> trimesh.Trimesh:
    if args_cli.stable_pose_mesh_mode == "visual":
        return mesh.copy()

    start = time.perf_counter()
    pose_mesh = mesh.convex_hull
    pose_mesh.merge_vertices()
    pose_mesh.remove_unreferenced_vertices()
    elapsed = time.perf_counter() - start
    print(
        "[stable_pose] "
        f"uuid={uuid} convex_hull_vertices={len(pose_mesh.vertices)} "
        f"convex_hull_faces={len(pose_mesh.faces)} hull_seconds={elapsed:.3f}",
        flush=True,
    )
    if pose_mesh.vertices.size == 0 or pose_mesh.faces.size == 0:
        raise ValueError(f"Convex hull has no vertices/faces for {uuid}")
    return pose_mesh


def _matrix_to_quat_wxyz(matrix: np.ndarray, *, device: torch.device) -> torch.Tensor:
    rot = torch.as_tensor(matrix[:3, :3], dtype=torch.float32, device=device).unsqueeze(0)
    quat = math_utils.quat_from_matrix(rot)[0]
    return quat / torch.clamp(torch.norm(quat), min=1.0e-6)


def _compute_pose_cache(
    selected: list[dict[str, object]],
    asset_root: Path,
    output_dir: Path,
) -> tuple[list[dict[str, object]], list[torch.Tensor]]:
    cache_dir = output_dir / "stable_pose_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    all_pose_data: list[dict[str, object]] = []
    vertices_by_asset: list[torch.Tensor] = []
    pose_count = max(int(args_cli.stable_pose_count), 1)

    for record in selected:
        uuid = str(record.get("uuid") or "unknown")
        mesh = _load_scaled_mesh(record, asset_root)
        visual_vertex_count = int(len(mesh.vertices))
        visual_face_count = int(len(mesh.faces))
        print(
            "[stable_pose] "
            f"uuid={uuid} visual_vertices={visual_vertex_count} visual_faces={visual_face_count} "
            f"scale={float(record.get('scale', 1.0)):.10f} mode={args_cli.stable_pose_mesh_mode}",
            flush=True,
        )
        pose_mesh = _make_stable_pose_mesh(mesh, uuid=uuid)
        start = time.perf_counter()
        transforms, probabilities = pose_mesh.compute_stable_poses(
            sigma=float(args_cli.stable_pose_sigma),
            n_samples=max(int(args_cli.stable_pose_samples), 1),
            threshold=float(args_cli.stable_pose_threshold),
        )
        stable_pose_seconds = time.perf_counter() - start
        print(
            "[stable_pose] "
            f"uuid={uuid} stable_pose_count={len(transforms)} stable_pose_seconds={stable_pose_seconds:.3f}",
            flush=True,
        )
        if len(transforms) == 0:
            raise RuntimeError(f"trimesh returned no stable poses for {uuid}")
        order = np.argsort(np.asarray(probabilities))[::-1]
        transforms = np.asarray(transforms, dtype=np.float64)[order]
        probabilities = np.asarray(probabilities, dtype=np.float64)[order]
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        pose_records: list[dict[str, object]] = []
        for rank, transform in enumerate(transforms[:pose_count]):
            rot = transform[:3, :3]
            rotated = vertices @ rot.T
            bottom_z = float(rotated[:, 2].min())
            root_z_offset = -bottom_z
            pose_records.append(
                {
                    "rank": rank,
                    "probability": float(probabilities[rank]),
                    "transform": transform.tolist(),
                    "rotation": rot.tolist(),
                    "bottom_z_after_rotation": bottom_z,
                    "root_z_offset": root_z_offset,
                }
            )
        cache_path = cache_dir / f"{uuid}.npz"
        np.savez_compressed(
            cache_path,
            uuid=uuid,
            scale=float(record.get("scale", 1.0)),
            stable_pose_mesh_mode=args_cli.stable_pose_mesh_mode,
            transforms=transforms,
            probabilities=probabilities,
            vertices=vertices,
            pose_vertices=np.asarray(pose_mesh.vertices, dtype=np.float64),
            pose_faces=np.asarray(pose_mesh.faces, dtype=np.int64),
            pose_count=min(pose_count, len(transforms)),
        )
        all_pose_data.append(
            {
                "uuid": uuid,
                "scale": float(record.get("scale", 1.0)),
                "raw_object_path": str(_resolve_manifest_path(str(record.get("raw_object_path")), base_dir=asset_root)),
                "cache_path": str(cache_path),
                "stable_pose_mesh_mode": args_cli.stable_pose_mesh_mode,
                "visual_vertex_count": visual_vertex_count,
                "visual_face_count": visual_face_count,
                "pose_vertex_count": int(len(pose_mesh.vertices)),
                "pose_face_count": int(len(pose_mesh.faces)),
                "stable_pose_seconds": stable_pose_seconds,
                "num_stable_poses": int(len(transforms)),
                "tested_pose_count": int(len(pose_records)),
                "poses": pose_records,
                "bounds_min": vertices.min(axis=0).tolist(),
                "bounds_max": vertices.max(axis=0).tolist(),
            }
        )
        vertices_by_asset.append(torch.as_tensor(vertices, dtype=torch.float32))
    return all_pose_data, vertices_by_asset


def _configure_camera(task_env, env_id: int = 0) -> None:
    if not args_cli.render_frames:
        return
    origin = tuple(float(v) for v in task_env.scene.env_origins[env_id].detach().cpu())
    eye = tuple(DEFAULT_CAMERA_EYE[idx] + origin[idx] for idx in range(3))
    target = tuple(DEFAULT_CAMERA_TARGET[idx] + origin[idx] for idx in range(3))
    try:
        task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=task_env.cfg.viewer.cam_prim_path)
    except Exception as exc:
        print(f"[WARN] Could not set stable-pose camera: {exc}", flush=True)


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


def _capture_env_frames(env, task_env, frame_root: Path, frame_idx: int) -> dict[str, str]:
    if not args_cli.render_frames:
        return {}
    paths: dict[str, str] = {}
    for env_i in range(int(task_env.num_envs)):
        _configure_camera(task_env, env_id=env_i)
        frame = env.render()
        env_path = frame_root / f"env_{env_i:02d}" / f"frame_{frame_idx:04d}.png"
        paths[str(env_i)] = _save_frame(frame, env_path)
        if env_i == 0:
            _save_frame(frame, frame_root / f"frame_{frame_idx:04d}.png")
    return paths


def _zero_actions(task_env) -> torch.Tensor:
    return torch.zeros((task_env.num_envs, int(task_env.cfg.action_space)), device=task_env.device)


def _manual_step(task_env) -> torch.Tensor:
    task_env._pre_physics_step(_zero_actions(task_env))
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
    return torch.logical_or(terminated, truncated)


def _bottom_z_from_vertices(task_env, vertices_by_asset: list[torch.Tensor], env_ids: torch.Tensor) -> torch.Tensor:
    env_ids = env_ids.to(device=task_env.device, dtype=torch.long)
    root_pos = task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    root_quat = task_env._cube.data.root_quat_w[env_ids]
    rot_m = math_utils.matrix_from_quat(root_quat)
    object_indices = task_env.object_asset_index[env_ids]
    bottom = torch.empty(env_ids.numel(), dtype=torch.float32, device=task_env.device)
    for object_idx_tensor in torch.unique(object_indices):
        object_idx = int(object_idx_tensor.item())
        mask = object_indices == object_idx
        vertices = vertices_by_asset[object_idx].to(device=task_env.device)
        rotated = torch.einsum("nij,kj->nki", rot_m[mask], vertices)
        bottom[mask] = root_pos[mask, 2] + rotated[:, :, 2].min(dim=1).values
    return bottom


def _quat_angle_delta(initial_quat: torch.Tensor, current_quat: torch.Tensor) -> torch.Tensor:
    dot = torch.abs(torch.sum(initial_quat * current_quat, dim=-1))
    dot = torch.clamp(dot, -1.0, 1.0)
    return 2.0 * torch.acos(dot)


def _place_stable_pose_states(task_env, pose_data: list[dict[str, object]], vertices_by_asset: list[torch.Tensor]) -> dict[str, object]:
    env_ids = task_env._robot._ALL_INDICES
    num_assets = len(pose_data)
    object_indices = task_env.object_asset_index[env_ids].detach().cpu().numpy().astype(int)
    root_state = torch.zeros((task_env.num_envs, 13), dtype=torch.float32, device=task_env.device)
    pose_rank_by_env: list[int] = []
    pose_probability_by_env: list[float] = []
    object_uuid_by_env: list[str] = []
    object_asset_index_by_env: list[int] = []
    local_root_pos_by_env: list[list[float]] = []
    local_root_quat_by_env: list[list[float]] = []

    for env_i, object_idx in enumerate(object_indices):
        poses = pose_data[object_idx]["poses"]
        if not isinstance(poses, list) or not poses:
            raise RuntimeError(f"No stable poses available for object index {object_idx}")
        pose_rank = (env_i // num_assets) % len(poses)
        pose = poses[pose_rank]
        rot = np.asarray(pose["rotation"], dtype=np.float64)
        quat = _matrix_to_quat_wxyz(rot, device=task_env.device)
        vertices = vertices_by_asset[object_idx].to(device=task_env.device)
        rot_t = torch.as_tensor(rot, dtype=torch.float32, device=task_env.device)
        rotated = vertices @ rot_t.T
        bottom_z = float(rotated[:, 2].min().detach().cpu())
        local_root_pos = torch.tensor(
            [
                float(task_env.cfg.pickup_x),
                float(task_env.cfg.pickup_y),
                float(task_env.cfg.table_surface_z) + float(args_cli.table_clearance) - bottom_z,
            ],
            dtype=torch.float32,
            device=task_env.device,
        )
        root_state[env_i, 0:3] = local_root_pos + task_env.scene.env_origins[env_i]
        root_state[env_i, 3:7] = quat
        object_uuid_by_env.append(str(pose_data[object_idx]["uuid"]))
        object_asset_index_by_env.append(int(object_idx))
        pose_rank_by_env.append(int(pose_rank))
        pose_probability_by_env.append(float(pose["probability"]))
        local_root_pos_by_env.append(local_root_pos.detach().cpu().tolist())
        local_root_quat_by_env.append(quat.detach().cpu().tolist())

    task_env._cube.write_root_state_to_sim(root_state, env_ids=env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(env_ids)
    return {
        "object_uuid_by_env": object_uuid_by_env,
        "object_asset_index_by_env": object_asset_index_by_env,
        "pose_rank_by_env": pose_rank_by_env,
        "pose_probability_by_env": pose_probability_by_env,
        "initial_root_pos": local_root_pos_by_env,
        "initial_root_quat": local_root_quat_by_env,
    }


def _place_local_root_states(
    task_env,
    local_root_pos_by_env: list[list[float]],
    local_root_quat_by_env: list[list[float]],
) -> None:
    env_ids = task_env._robot._ALL_INDICES
    root_state = torch.zeros((task_env.num_envs, 13), dtype=torch.float32, device=task_env.device)
    local_pos = torch.as_tensor(local_root_pos_by_env, dtype=torch.float32, device=task_env.device)
    local_quat = torch.as_tensor(local_root_quat_by_env, dtype=torch.float32, device=task_env.device)
    root_state[:, 0:3] = local_pos + task_env.scene.env_origins[env_ids]
    root_state[:, 3:7] = local_quat
    task_env._cube.write_root_state_to_sim(root_state, env_ids=env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(env_ids)


def _run_stability_rollout(
    env,
    task_env,
    pose_data: list[dict[str, object]],
    vertices_by_asset: list[torch.Tensor],
    output_dir: Path,
    *,
    rollout_name: str,
    settle_steps: int,
    initial_local_root_pos: list[list[float]] | None = None,
    initial_local_root_quat: list[list[float]] | None = None,
    placement_template: dict[str, object] | None = None,
) -> dict[str, object]:
    env.reset()
    _configure_camera(task_env, env_id=0)
    if initial_local_root_pos is None or initial_local_root_quat is None:
        placement = _place_stable_pose_states(task_env, pose_data, vertices_by_asset)
        placement["source"] = "trimesh_stable_pose"
    else:
        _place_local_root_states(task_env, initial_local_root_pos, initial_local_root_quat)
        placement = dict(placement_template or {})
        placement["initial_root_pos"] = initial_local_root_pos
        placement["initial_root_quat"] = initial_local_root_quat
        placement["source"] = "settled_replay"
    for _ in range(max(int(args_cli.render_warmup_frames), 0)):
        if args_cli.render_frames:
            env.render()

    env_ids = task_env._robot._ALL_INDICES
    initial_root_pos = task_env._cube.data.root_pos_w[env_ids].detach().clone()
    initial_root_quat = task_env._cube.data.root_quat_w[env_ids].detach().clone()
    initial_center_pos = task_env.cube_pos.detach().clone()
    initial_bottom_z = _bottom_z_from_vertices(task_env, vertices_by_asset, env_ids).detach().clone()
    frame_root = output_dir / "frames"
    if rollout_name:
        frame_root = frame_root / rollout_name

    frame_records: list[dict[str, object]] = []
    if args_cli.render_frames:
        frame_records.append({"frame_index": 0, "paths_by_env": _capture_env_frames(env, task_env, frame_root, 0)})

    series: list[dict[str, object]] = []
    done_count = 0
    num_envs = int(env_ids.numel())
    root_xy_delta_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    center_xy_delta_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    root_z_delta_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    angular_delta_deg_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    bottom_clearance_min_by_env = torch.full((num_envs,), float("inf"), dtype=torch.float32, device=task_env.device)
    bottom_z_delta_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    object_speed_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    object_angular_speed_max_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    done_count_by_env = torch.zeros(num_envs, dtype=torch.long, device=task_env.device)
    final_object_speed_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    final_object_angular_speed_by_env = torch.zeros(num_envs, dtype=torch.float32, device=task_env.device)
    capture_interval = max(int(args_cli.capture_interval), 1)
    rollout_steps = max(int(settle_steps), 1)
    for step in range(rollout_steps):
        dones = _manual_step(task_env)
        done_count += int(dones.float().sum().detach().cpu())
        done_count_by_env += dones.to(dtype=torch.long)
        root_pos = task_env._cube.data.root_pos_w[env_ids]
        root_quat = task_env._cube.data.root_quat_w[env_ids]
        center_pos = task_env.cube_pos
        root_xy_delta = torch.norm(root_pos[:, :2] - initial_root_pos[:, :2], dim=-1)
        center_xy_delta = torch.norm(center_pos[:, :2] - initial_center_pos[:, :2], dim=-1)
        root_z_delta = torch.abs(root_pos[:, 2] - initial_root_pos[:, 2])
        angular_delta = _quat_angle_delta(initial_root_quat, root_quat)
        angular_delta_deg = torch.rad2deg(angular_delta)
        bottom_z = _bottom_z_from_vertices(task_env, vertices_by_asset, env_ids)
        bottom_clearance = bottom_z - float(task_env.cfg.table_surface_z)
        bottom_z_delta = torch.abs(bottom_z - initial_bottom_z)
        object_speed = torch.norm(task_env._cube.data.root_vel_w[env_ids, :3], dim=-1)
        object_angular_speed = torch.norm(task_env._cube.data.root_vel_w[env_ids, 3:], dim=-1)
        root_xy_delta_max_by_env = torch.maximum(root_xy_delta_max_by_env, root_xy_delta.detach())
        center_xy_delta_max_by_env = torch.maximum(center_xy_delta_max_by_env, center_xy_delta.detach())
        root_z_delta_max_by_env = torch.maximum(root_z_delta_max_by_env, root_z_delta.detach())
        angular_delta_deg_max_by_env = torch.maximum(angular_delta_deg_max_by_env, angular_delta_deg.detach())
        bottom_clearance_min_by_env = torch.minimum(bottom_clearance_min_by_env, bottom_clearance.detach())
        bottom_z_delta_max_by_env = torch.maximum(bottom_z_delta_max_by_env, bottom_z_delta.detach())
        object_speed_max_by_env = torch.maximum(object_speed_max_by_env, object_speed.detach())
        object_angular_speed_max_by_env = torch.maximum(object_angular_speed_max_by_env, object_angular_speed.detach())
        final_object_speed_by_env = object_speed.detach()
        final_object_angular_speed_by_env = object_angular_speed.detach()
        series.append(
            {
                "step": step + 1,
                "root_xy_delta_max": float(root_xy_delta.detach().max().cpu()),
                "center_xy_delta_max": float(center_xy_delta.detach().max().cpu()),
                "root_z_delta_max": float(root_z_delta.detach().max().cpu()),
                "angular_delta_deg_max": float(angular_delta_deg.detach().max().cpu()),
                "bottom_clearance_min": float(bottom_clearance.detach().min().cpu()),
                "bottom_z_delta_max": float(bottom_z_delta.detach().max().cpu()),
                "object_speed_max": float(object_speed.detach().max().cpu()),
                "object_angular_speed_max": float(object_angular_speed.detach().max().cpu()),
                "done_count": int(dones.float().sum().detach().cpu()),
            }
        )
        if args_cli.render_frames and ((step + 1) % capture_interval == 0 or step == rollout_steps - 1):
            frame_idx = len(frame_records)
            frame_records.append(
                {"frame_index": frame_idx, "paths_by_env": _capture_env_frames(env, task_env, frame_root, frame_idx)}
            )

    summary = {
        "samples": len(series),
        "root_xy_delta_max": max(float(item["root_xy_delta_max"]) for item in series),
        "center_xy_delta_max": max(float(item["center_xy_delta_max"]) for item in series),
        "root_z_delta_max": max(float(item["root_z_delta_max"]) for item in series),
        "angular_delta_deg_max": max(float(item["angular_delta_deg_max"]) for item in series),
        "bottom_clearance_min": min(float(item["bottom_clearance_min"]) for item in series),
        "bottom_z_delta_max": max(float(item["bottom_z_delta_max"]) for item in series),
        "object_speed_max": max(float(item["object_speed_max"]) for item in series),
        "object_angular_speed_max": max(float(item["object_angular_speed_max"]) for item in series),
        "final_object_speed_max": float(series[-1]["object_speed_max"]),
        "final_object_angular_speed_max": float(series[-1]["object_angular_speed_max"]),
        "done_count": done_count,
    }
    root_xy_list = root_xy_delta_max_by_env.detach().cpu().tolist()
    center_xy_list = center_xy_delta_max_by_env.detach().cpu().tolist()
    root_z_list = root_z_delta_max_by_env.detach().cpu().tolist()
    angular_list = angular_delta_deg_max_by_env.detach().cpu().tolist()
    bottom_clearance_list = bottom_clearance_min_by_env.detach().cpu().tolist()
    bottom_z_delta_list = bottom_z_delta_max_by_env.detach().cpu().tolist()
    speed_list = object_speed_max_by_env.detach().cpu().tolist()
    angular_speed_list = object_angular_speed_max_by_env.detach().cpu().tolist()
    final_speed_list = final_object_speed_by_env.detach().cpu().tolist()
    final_angular_speed_list = final_object_angular_speed_by_env.detach().cpu().tolist()
    done_count_list = done_count_by_env.detach().cpu().tolist()
    per_env: list[dict[str, object]] = []
    for env_i in range(num_envs):
        env_passed = (
            root_xy_list[env_i] <= float(args_cli.max_root_xy_drift)
            and center_xy_list[env_i] <= float(args_cli.max_center_xy_drift)
            and root_z_list[env_i] <= float(args_cli.max_root_z_drift)
            and angular_list[env_i] <= float(args_cli.max_angular_drift_deg)
            and bottom_clearance_list[env_i] >= float(args_cli.min_bottom_clearance)
            and final_speed_list[env_i] <= float(args_cli.max_final_speed)
            and (not args_cli.fail_on_task_done or int(done_count_list[env_i]) == 0)
        )
        per_env.append(
            {
                "env_id": env_i,
                "object_uuid": placement["object_uuid_by_env"][env_i],
                "object_asset_index": placement["object_asset_index_by_env"][env_i],
                "pose_rank": placement["pose_rank_by_env"][env_i],
                "pose_probability": placement["pose_probability_by_env"][env_i],
                "passed": bool(env_passed),
                "root_xy_delta_max": float(root_xy_list[env_i]),
                "center_xy_delta_max": float(center_xy_list[env_i]),
                "root_z_delta_max": float(root_z_list[env_i]),
                "angular_delta_deg_max": float(angular_list[env_i]),
                "bottom_clearance_min": float(bottom_clearance_list[env_i]),
                "bottom_z_delta_max": float(bottom_z_delta_list[env_i]),
                "object_speed_max": float(speed_list[env_i]),
                "object_angular_speed_max": float(angular_speed_list[env_i]),
                "final_object_speed": float(final_speed_list[env_i]),
                "final_object_angular_speed": float(final_angular_speed_list[env_i]),
                "task_done_count": int(done_count_list[env_i]),
            }
        )
    passed = all(bool(item["passed"]) for item in per_env)
    final_root_pos_local = (
        task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    ).detach().cpu().tolist()
    final_root_quat = task_env._cube.data.root_quat_w[env_ids].detach().cpu().tolist()
    return {
        "passed": bool(passed),
        "rollout_name": rollout_name or "stable_pose",
        "summary": summary,
        "per_env": per_env,
        "placement": placement,
        "final_root_pos": final_root_pos_local,
        "final_root_quat": final_root_quat,
        "frames": frame_records,
        "series_tail": series[-min(len(series), 10):],
        "thresholds": {
            "max_root_xy_drift": float(args_cli.max_root_xy_drift),
            "max_center_xy_drift": float(args_cli.max_center_xy_drift),
            "max_root_z_drift": float(args_cli.max_root_z_drift),
            "max_angular_drift_deg": float(args_cli.max_angular_drift_deg),
            "min_bottom_clearance": float(args_cli.min_bottom_clearance),
            "max_final_speed": float(args_cli.max_final_speed),
            "fail_on_task_done": bool(args_cli.fail_on_task_done),
        },
    }


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("graspgen_stable_pose_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    filtered_manifest, selected, asset_root = _load_selected_manifest(output_dir)
    pose_data, vertices_by_asset = _compute_pose_cache(selected, asset_root, output_dir)
    num_envs = len(selected) * max(int(args_cli.stable_pose_count), 1)

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    env_cfg.object_asset_manifest_path = str(filtered_manifest)
    env_cfg.max_objects = len(selected)
    env_cfg.object_spawn_xy_randomization = 0.0
    env_cfg.object_spawn_yaw_randomization_deg = 0.0
    env_cfg.object_reset_settle_steps = 0
    env_cfg.grasp_prior_reset_enabled = False
    env_cfg.grasp_prior_action_warmstart_enabled = False

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.render_frames else None)
    task_env = env.unwrapped
    _configure_camera(task_env, env_id=0)
    result = _run_stability_rollout(
        env,
        task_env,
        pose_data,
        vertices_by_asset,
        output_dir,
        rollout_name="stable_pose",
        settle_steps=int(args_cli.settle_steps),
    )
    settled_replay_result = None
    if int(args_cli.settled_replay_steps) > 0:
        settled_replay_result = _run_stability_rollout(
            env,
            task_env,
            pose_data,
            vertices_by_asset,
            output_dir,
            rollout_name="settled_replay",
            settle_steps=int(args_cli.settled_replay_steps),
            initial_local_root_pos=result["final_root_pos"],
            initial_local_root_quat=result["final_root_quat"],
            placement_template=result["placement"],
        )
    passed = bool(result["passed"]) if settled_replay_result is None else bool(settled_replay_result["passed"])
    payload = {
        "passed": passed,
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "num_envs": int(num_envs),
        "max_objects": int(len(selected)),
        "stable_pose_count": int(args_cli.stable_pose_count),
        "settle_steps": int(args_cli.settle_steps),
        "settled_replay_steps": int(args_cli.settled_replay_steps),
        "selected_manifest": str(filtered_manifest),
        "object_asset_manifest_path": str(args_cli.object_asset_manifest_path),
        "pose_data": pose_data,
        "result": result,
        "settled_replay_result": settled_replay_result,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] Wrote stable-pose metrics to {metrics_path}", flush=True)
    env.close()
    simulation_app.close()
    if not bool(payload["passed"]):
        raise SystemExit("Stable-pose placement validation failed")
    print("DEXTRAH_GRASPGEN_STABLE_POSE_VALIDATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
