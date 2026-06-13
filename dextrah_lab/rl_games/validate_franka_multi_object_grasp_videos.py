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
parser.add_argument("--object_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=180.0)
parser.add_argument("--render_warmup_frames", type=int, default=2)
parser.add_argument("--reset_cycles", type=int, default=3)
parser.add_argument("--settle_steps", type=int, default=72)
parser.add_argument("--perturb_steps", type=int, default=96)
parser.add_argument("--grasp_steps", type=int, default=72)
parser.add_argument("--capture_interval", type=int, default=2)
parser.add_argument("--grasp_reset_attempts", type=int, default=12)
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


def _as_float(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


def _configure_camera(task_env, env_id: int = 0) -> None:
    origin = tuple(float(v) for v in task_env.scene.env_origins[env_id].detach().cpu())
    eye = tuple(DEFAULT_CAMERA_EYE[idx] + origin[idx] for idx in range(3))
    target = tuple(DEFAULT_CAMERA_TARGET[idx] + origin[idx] for idx in range(3))
    try:
        task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=task_env.cfg.viewer.cam_prim_path)
    except Exception as exc:
        print(f"[WARN] Could not set validation camera: {exc}", flush=True)


def _object_bottom_z(task_env, env_ids: torch.Tensor) -> torch.Tensor:
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
    out = env.step(actions)
    task_env._compute_intermediate_values()
    terminated, truncated = task_env._get_dones()
    dones = torch.logical_or(terminated, truncated)
    return out, dones


def _capture(env, scenario_dir: Path, frame_idx: int) -> str:
    return _save_frame(env.render(), scenario_dir / "frames" / f"frame_{frame_idx:04d}.png")


def _warmup_render(env, task_env, frames: int) -> None:
    for _ in range(max(int(frames), 0)):
        _step_env(env, task_env)
        env.render()


def _metrics_snapshot(task_env, dones: torch.Tensor | None = None) -> dict[str, object]:
    env_ids = task_env._robot._ALL_INDICES
    bottom_z = _object_bottom_z(task_env, env_ids)
    object_xy_delta = torch.norm(task_env.cube_pos[:, :2] - task_env.cube_initial_pos[:, :2], dim=-1)
    object_speed = torch.norm(task_env.cube_vel[:, :3], dim=-1)
    angular_speed = torch.norm(task_env.cube_vel[:, 3:], dim=-1)
    return {
        "bottom_z_min": float(bottom_z.detach().min().cpu()),
        "table_surface_z": float(task_env.cfg.table_surface_z),
        "bottom_clearance_min": float((bottom_z - float(task_env.cfg.table_surface_z)).detach().min().cpu()),
        "object_xy_delta_max": float(object_xy_delta.detach().max().cpu()),
        "object_speed_max": float(object_speed.detach().max().cpu()),
        "object_angular_speed_max": float(angular_speed.detach().max().cpu()),
        "object_center_z_min": float(task_env.cube_pos[:, 2].detach().min().cpu()),
        "object_center_z_max": float(task_env.cube_pos[:, 2].detach().max().cpu()),
        "finger_table_clearance_min": float(task_env.finger_table_clearance.detach().min().cpu()),
        "finger_center_to_object_min": float(task_env.finger_center_to_cube_dist.detach().min().cpu()),
        "max_finger_to_object_min": float(task_env.max_finger_to_cube_dist.detach().min().cpu()),
        "gripper_width_min": float(task_env.gripper_width.detach().min().cpu()),
        "gripper_width_max": float(task_env.gripper_width.detach().max().cpu()),
        "done_count": int(dones.float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0,
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
        for step in range(max(int(args_cli.settle_steps), 1)):
            _, dones = _step_env(env, task_env)
            if step % max(int(args_cli.capture_interval), 1) == 0:
                artifact_paths.append(_capture(env, scenario_dir, frame_idx))
                frame_idx += 1
            snap = _metrics_snapshot(task_env, dones)
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
    env_ids = task_env._robot._ALL_INDICES
    velocity = torch.zeros((task_env.num_envs, 6), device=task_env.device)
    signs = torch.where(torch.arange(task_env.num_envs, device=task_env.device) % 2 == 0, 1.0, -1.0)
    velocity[:, 0] = 0.28 * signs
    velocity[:, 1] = 0.10 * torch.roll(signs, shifts=1)
    velocity[:, 5] = 3.0 * signs
    task_env._cube.write_root_velocity_to_sim(velocity, env_ids=env_ids)
    task_env._compute_intermediate_values()

    frame_idx = 0
    series: list[dict[str, object]] = []
    artifact_paths: list[str] = []
    for step in range(max(int(args_cli.perturb_steps), 1)):
        _, dones = _step_env(env, task_env)
        if step % max(int(args_cli.capture_interval), 1) == 0:
            artifact_paths.append(_capture(env, scenario_dir, frame_idx))
            frame_idx += 1
        snap = _metrics_snapshot(task_env, dones)
        snap.update({"step": step})
        series.append(snap)
    summary = _summarize_series(series)
    passed = (
        float(summary.get("bottom_clearance_min", -1.0)) >= -0.01
        and float(summary.get("object_xy_delta_max", 0.0)) >= 0.01
        and float(summary.get("object_xy_delta_max", 999.0)) <= 0.35
        and float(summary.get("object_center_z_max", 999.0)) <= 1.20
        and int(summary.get("done_count", 1)) == 0
    )
    return {"passed": passed, "summary": summary, "frames": artifact_paths}


def _reset_until_quality_grasp(env, task_env) -> int:
    selected_env = 0
    for _ in range(max(int(args_cli.grasp_reset_attempts), 1)):
        env.reset()
        task_env._compute_intermediate_values()
        quality = task_env.grasp_prior_reset_quality_success
        if bool(quality.any().item()):
            selected_env = int(torch.nonzero(quality, as_tuple=False)[0].item())
            break
    return selected_env


def _record_grasp_contact(env, task_env, output_dir: Path) -> dict[str, object]:
    scenario_dir = output_dir / "grasp_contact"
    selected_env = _reset_until_quality_grasp(env, task_env)
    _configure_camera(task_env, env_id=selected_env)
    _warmup_render(env, task_env, args_cli.render_warmup_frames)
    frame_idx = 0
    series: list[dict[str, object]] = []
    artifact_paths: list[str] = []
    phase_values: list[int] = []
    for step in range(max(int(args_cli.grasp_steps), 1)):
        _, dones = _step_env(env, task_env)
        if hasattr(task_env, "grasp_prior_action_warmstart_phase"):
            phase_values.append(int(task_env.grasp_prior_action_warmstart_phase[selected_env].detach().cpu()))
        if step % max(int(args_cli.capture_interval), 1) == 0:
            artifact_paths.append(_capture(env, scenario_dir, frame_idx))
            frame_idx += 1
        snap = _metrics_snapshot(task_env, dones)
        snap.update(
            {
                "step": step,
                "selected_env": selected_env,
                "selected_lift_height": float(task_env.cube_lift_height[selected_env].detach().cpu()),
                "selected_finger_center_dist": float(task_env.finger_center_to_cube_dist[selected_env].detach().cpu()),
                "selected_max_finger_dist": float(task_env.max_finger_to_cube_dist[selected_env].detach().cpu()),
                "selected_gripper_width": float(task_env.gripper_width[selected_env].detach().cpu()),
            }
        )
        series.append(snap)
    summary = _summarize_series(series)
    selected_lift = max(float(item["selected_lift_height"]) for item in series)
    selected_max_finger = min(float(item["selected_max_finger_dist"]) for item in series)
    selected_width = min(float(item["selected_gripper_width"]) for item in series)
    passed = (
        bool(task_env.grasp_prior_reset_quality_success[selected_env].detach().cpu())
        and float(summary.get("bottom_clearance_min", -1.0)) >= -0.01
        and float(summary.get("finger_table_clearance_min", -1.0)) >= float(task_env.cfg.finger_table_penetration_termination_margin)
        and selected_max_finger <= 0.12
        and selected_width <= float(task_env.cfg.max_gripper_width)
        and int(summary.get("done_count", 1)) == 0
    )
    return {
        "passed": passed,
        "summary": summary,
        "selected_env": selected_env,
        "selected_lift_height_max": selected_lift,
        "selected_max_finger_dist_min": selected_max_finger,
        "selected_gripper_width_min": selected_width,
        "warmstart_phases": sorted(set(phase_values)),
        "frames": artifact_paths,
    }


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_multi_object_video_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "video_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    env_cfg.object_asset_manifest_path = str(Path(args_cli.object_asset_manifest_path).expanduser().resolve())
    env_cfg.max_objects = int(args_cli.max_objects)
    env_cfg.object_spawn_xy_randomization = float(args_cli.object_spawn_xy_randomization)
    env_cfg.object_spawn_yaw_randomization_deg = float(args_cli.object_spawn_yaw_randomization_deg)
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_action_warmstart_enabled = True
    env_cfg.grasp_prior_action_warmstart_close_width = 0.035
    env_cfg.grasp_prior_action_warmstart_lift_action_z = 0.30
    env_cfg.grasp_prior_action_warmstart_approach_steps = min(20, max(args_cli.grasp_steps // 3, 1))
    env_cfg.grasp_prior_action_warmstart_close_steps = min(20, max(args_cli.grasp_steps // 3, 1))
    env_cfg.grasp_prior_action_warmstart_lift_steps = max(args_cli.grasp_steps - 2 * (args_cli.grasp_steps // 3), 1)
    env_cfg.grasp_prior_allow_missing = False

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = env.unwrapped
    _configure_camera(task_env, env_id=0)

    scenarios = {
        "reset_settle": _record_reset_settle(env, task_env, output_dir),
        "perturbation": _record_perturbation(env, task_env, output_dir),
        "grasp_contact": _record_grasp_contact(env, task_env, output_dir),
    }
    payload = {
        "passed": all(bool(item.get("passed", False)) for item in scenarios.values()),
        "scenarios": scenarios,
        "config": {
            "task": args_cli.task,
            "num_envs": args_cli.num_envs,
            "seed": args_cli.seed,
            "object_asset_manifest_path": str(args_cli.object_asset_manifest_path),
            "max_objects": args_cli.max_objects,
            "capture_interval": args_cli.capture_interval,
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
