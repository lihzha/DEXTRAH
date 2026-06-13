"""Validate the Franka GraspGen multi-object grasp environment before RL training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Multi-Object-Grasp")
parser.add_argument("--num_envs", type=int, default=8)
parser.add_argument("--num_steps", type=int, default=120)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=120)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--render_check", action="store_true", default=False)
parser.add_argument("--render_check_frames", type=int, default=2)
parser.add_argument("--object_asset_manifest_path", type=str, default=None)
parser.add_argument("--object_assets_dir", type=str, default=None)
parser.add_argument("--max_objects", type=int, default=None)
parser.add_argument("--object_spawn_xy_randomization", type=float, default=None)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=None)
parser.add_argument("--enable_grasp_prior_reset", action="store_true", default=False)
parser.add_argument("--grasp_prior_library_dir", type=str, default=None)
parser.add_argument("--grasp_prior_allow_missing", action="store_true", default=False)
parser.add_argument("--grasp_prior_reset_cycles", type=int, default=4)
parser.add_argument("--print_interval", type=int, default=30)
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video or args_cli.render_check:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
import isaaclab.utils.math as math_utils
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)


def _mean(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


class CheckRecorder:
    def __init__(self):
        self.records: list[dict[str, object]] = []

    def check(self, name: str, passed: bool, **details) -> None:
        self.records.append({"name": name, "passed": bool(passed), "details": details})

    @property
    def passed(self) -> bool:
        return all(bool(record["passed"]) for record in self.records)


def _run_registration_checks(task: str, checks: CheckRecorder) -> None:
    registered: dict[str, str] = {}
    for task_id in ("Dextrah-Franka-Cube-Grasp", task):
        try:
            spec = gym.spec(task_id)
            registered[task_id] = str(spec.entry_point)
        except Exception as exc:
            checks.check("task_registration_resolves", False, task=task_id, error=repr(exc))
            return
    checks.check(
        "task_registration_resolves",
        True,
        baseline_entry_point=registered["Dextrah-Franka-Cube-Grasp"],
        requested_entry_point=registered[task],
    )


def _configure_validation_camera(env_cfg, task_env=None) -> None:
    if not (args_cli.video or args_cli.render_check) or not hasattr(env_cfg, "viewer"):
        return
    eye = tuple(DEFAULT_CAMERA_EYE)
    target = tuple(DEFAULT_CAMERA_TARGET)
    if task_env is not None and hasattr(task_env, "scene"):
        env_origin = tuple(float(v) for v in task_env.scene.env_origins[0].detach().cpu())
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set validation camera: {exc}", flush=True)


def _run_asset_checks(task_env, checks: CheckRecorder) -> dict[str, object]:
    summary = task_env.multi_object_asset_summary()
    num_unique = int(summary["num_unique_objects"])
    scales = torch.as_tensor(summary["scales"], dtype=torch.float32)
    usd_paths = [Path(path) for path in summary["usd_paths"]]
    used_asset_count = int(torch.unique(task_env.object_asset_index).numel())
    expected_used = min(task_env.num_envs, num_unique)
    checks.check(
        "multi_object_asset_count",
        num_unique >= 2 and used_asset_count == expected_used,
        num_unique_objects=num_unique,
        used_asset_count=used_asset_count,
        expected_used_asset_count=expected_used,
        uuids=summary["uuids"][:16],
    )
    checks.check(
        "multi_object_usd_paths_exist",
        all(path.is_file() for path in usd_paths),
        missing=[str(path) for path in usd_paths if not path.is_file()][:8],
    )
    checks.check(
        "multi_object_scales_finite_positive",
        bool(torch.isfinite(scales).all().item()) and bool((scales > 0.0).all().item()),
        scale_min=float(scales.min().item()) if scales.numel() else None,
        scale_max=float(scales.max().item()) if scales.numel() else None,
    )
    checks.check(
        "multi_object_geometry_finite_positive",
        bool(torch.isfinite(task_env.object_half_extents).all().item())
        and bool((task_env.object_half_extents > 0.0).all().item())
        and bool(torch.isfinite(task_env.object_bounds_min).all().item())
        and bool(torch.isfinite(task_env.object_bounds_max).all().item()),
        half_extent_min=float(task_env.object_half_extents.detach().min().cpu()),
        half_extent_max=float(task_env.object_half_extents.detach().max().cpu()),
        xy_radius_max=float(task_env.object_xy_radius.detach().max().cpu()),
        spawn_z_offset_min=float(task_env.object_spawn_z_offset.detach().min().cpu()),
    )
    return summary


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


def _run_reset_checks(env, task_env, checks: CheckRecorder) -> dict[str, object]:
    obs_out = env.reset()
    obs = obs_out[0] if isinstance(obs_out, tuple) else obs_out
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    checks.check(
        "reset_observation_shape",
        tuple(policy_obs.shape) == (task_env.num_envs, task_env.cfg.observation_space),
        observed_shape=list(policy_obs.shape),
        expected_shape=[task_env.num_envs, task_env.cfg.observation_space],
    )
    checks.check("reset_observation_finite", bool(torch.isfinite(policy_obs).all().item()))

    env_ids = task_env._robot._ALL_INDICES
    root_pos = task_env._cube.data.root_pos_w[env_ids] - task_env.scene.env_origins[env_ids]
    expected_root_z = (
        float(task_env.cfg.table_surface_z)
        + task_env.object_spawn_z_offset[env_ids]
        + float(task_env.cfg.object_spawn_z_clearance)
    )
    bottom_z = _object_bottom_z(task_env, env_ids)
    root_z_error = torch.abs(root_pos[:, 2] - expected_root_z)
    checks.check(
        "reset_object_bottom_on_table",
        bool((bottom_z >= float(task_env.cfg.table_surface_z) - 1.0e-4).all().item())
        and float(root_z_error.max().detach().cpu()) <= 1.0e-3,
        bottom_z_min=float(bottom_z.detach().min().cpu()),
        table_surface_z=float(task_env.cfg.table_surface_z),
        root_z_error_max=float(root_z_error.detach().max().cpu()),
        object_spawn_z_clearance=float(task_env.cfg.object_spawn_z_clearance),
    )
    checks.check(
        "reset_object_center_finite",
        bool(torch.isfinite(task_env.cube_pos).all().item()),
        center_z_min=float(task_env.cube_pos[:, 2].detach().min().cpu()),
        center_z_max=float(task_env.cube_pos[:, 2].detach().max().cpu()),
    )
    checks.check(
        "reset_fingers_clear_table",
        bool((task_env.finger_table_clearance >= float(task_env.cfg.finger_table_penetration_termination_margin)).all().item()),
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
        finger_table_clearance_mean=_mean(task_env.finger_table_clearance),
        penetration_margin=float(task_env.cfg.finger_table_penetration_termination_margin),
        success_margin=float(task_env.cfg.finger_table_clearance_margin),
    )
    robot_base_z = float(getattr(task_env.cfg, "robot_base_z", 0.0))
    checks.check(
        "franka_base_z_not_low",
        robot_base_z >= 0.27
        and float(task_env.finger_table_clearance.detach().min().cpu())
        >= float(task_env.cfg.finger_table_penetration_termination_margin),
        robot_base_z=robot_base_z,
        observed_cube_task_baseline_z=0.27,
        finger_table_clearance_min=float(task_env.finger_table_clearance.detach().min().cpu()),
    )
    return {
        "obs_shape": list(policy_obs.shape),
        "root_z_error_max": float(root_z_error.detach().max().cpu()),
        "bottom_z_min": float(bottom_z.detach().min().cpu()),
        "finger_table_clearance_min": float(task_env.finger_table_clearance.detach().min().cpu()),
    }


def _run_grasp_prior_reset_checks(env, task_env, checks: CheckRecorder, reset_cycles: int) -> dict[str, object]:
    if not bool(getattr(task_env.cfg, "grasp_prior_reset_enabled", False)):
        return {"enabled": False}

    cycles = max(int(reset_cycles), 1)
    cycle_summaries: list[dict[str, object]] = []
    immediate_done_count = 0
    for cycle_idx in range(cycles):
        obs_out = env.reset()
        obs = obs_out[0] if isinstance(obs_out, tuple) else obs_out
        policy_obs = obs["policy"] if isinstance(obs, dict) else obs
        task_env._compute_intermediate_values()
        terminated, truncated = task_env._get_dones()
        dones = torch.logical_or(terminated, truncated)
        immediate_done_count += int(dones.float().sum().detach().cpu())
        cycle_summaries.append(
            {
                "cycle": cycle_idx,
                "obs_finite": bool(torch.isfinite(policy_obs).all().item()),
                "attempt_rate": _mean(task_env.grasp_prior_reset_attempted.float()),
                "success_rate": _mean(task_env.grasp_prior_reset_success.float()),
                "quality_success_rate": _mean(task_env.grasp_prior_reset_quality_success.float()),
                "farther_rate": _mean(task_env.grasp_prior_reset_farther.float()),
                "pos_error_mean": _mean(task_env.grasp_prior_reset_pos_error),
                "rot_error_mean": _mean(task_env.grasp_prior_reset_rot_error),
                "open_width_margin_finite": bool(torch.isfinite(task_env.grasp_prior_reset_open_width_margin).all().item()),
                "open_width_margin_min": float(task_env.grasp_prior_reset_open_width_margin.detach().min().cpu()),
                "finger_table_clearance_min": float(task_env.finger_table_clearance.detach().min().cpu()),
                "immediate_done_count": int(dones.float().sum().detach().cpu()),
            }
        )

    attempt_rates = [float(item["attempt_rate"]) for item in cycle_summaries]
    success_rates = [float(item["success_rate"]) for item in cycle_summaries]
    farther_rates = [float(item["farther_rate"]) for item in cycle_summaries]
    clearance_mins = [float(item["finger_table_clearance_min"]) for item in cycle_summaries]
    checks.check("grasp_prior_reset_observation_finite", all(bool(item["obs_finite"]) for item in cycle_summaries))
    checks.check(
        "grasp_prior_reset_open_width_margin_finite",
        all(bool(item["open_width_margin_finite"]) for item in cycle_summaries),
        per_cycle_open_width_margin_min=[float(item["open_width_margin_min"]) for item in cycle_summaries],
    )
    checks.check("grasp_prior_reset_attempted_all_envs", min(attempt_rates) >= 1.0, min_attempt_rate=min(attempt_rates))
    checks.check(
        "grasp_prior_reset_success_rate",
        sum(success_rates) / len(success_rates) >= 0.25,
        mean_success_rate=sum(success_rates) / len(success_rates),
        per_cycle_success_rate=success_rates,
    )
    checks.check(
        "grasp_prior_reset_pregrasp_farther_from_object",
        min(farther_rates) >= 1.0,
        min_farther_rate=min(farther_rates),
    )
    checks.check(
        "grasp_prior_reset_no_table_penetration",
        min(clearance_mins) >= float(task_env.cfg.finger_table_penetration_termination_margin),
        min_finger_table_clearance=min(clearance_mins),
        penetration_margin=float(task_env.cfg.finger_table_penetration_termination_margin),
    )
    checks.check(
        "grasp_prior_reset_no_immediate_done_spike",
        immediate_done_count == 0,
        immediate_done_count=immediate_done_count,
        cycles=cycles,
        num_envs=task_env.num_envs,
    )
    return {
        "enabled": True,
        "cycles": cycles,
        "immediate_done_count": immediate_done_count,
        "mean_success_rate": sum(success_rates) / len(success_rates),
        "cycles_detail": cycle_summaries,
    }


def _run_short_rollout(env, task_env, checks: CheckRecorder, num_steps: int, print_interval: int) -> dict[str, object]:
    obs_out = env.reset()
    obs = obs_out[0] if isinstance(obs_out, tuple) else obs_out
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    checks.check("rollout_initial_obs_finite", bool(torch.isfinite(policy_obs).all().item()))

    reward_values: list[float] = []
    done_count = 0
    early_done_count = 0
    min_finger_table_clearance = _mean(task_env.finger_table_clearance)
    min_object_bottom_z = float("inf")
    for step in range(num_steps):
        actions = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
        if step > num_steps // 3:
            actions[:, 6] = -0.5
        if step > 2 * num_steps // 3:
            actions[:, 2] = 0.4
        step_out = env.step(actions)
        if len(step_out) == 5:
            obs, rewards, terminated, truncated, _ = step_out
            dones = torch.logical_or(terminated, truncated)
        else:
            obs, rewards, dones, _ = step_out
        policy_obs = obs["policy"] if isinstance(obs, dict) else obs
        reward_values.append(_mean(rewards))
        step_done_count = int(dones.float().sum().detach().cpu()) if isinstance(dones, torch.Tensor) else 0
        done_count += step_done_count
        if step < min(5, num_steps):
            early_done_count += step_done_count
        min_finger_table_clearance = min(min_finger_table_clearance, _mean(task_env.finger_table_clearance))
        bottom_z = _object_bottom_z(task_env, task_env._robot._ALL_INDICES)
        min_object_bottom_z = min(min_object_bottom_z, float(bottom_z.detach().min().cpu()))
        if not bool(torch.isfinite(policy_obs).all().item()):
            checks.check("rollout_observation_finite", False, step=step)
            break
        if not bool(torch.isfinite(rewards).all().item()):
            checks.check("rollout_reward_finite", False, step=step)
            break
        if print_interval > 0 and ((step + 1) % print_interval == 0 or step == 0):
            print(
                "[VALIDATE_MULTI_OBJECT] "
                f"step={step + 1} reward={reward_values[-1]:.4f} "
                f"object={_mean(task_env.object_asset_id_fraction):.4f} "
                f"ee_to_object={_mean(task_env.ee_to_cube_dist):.4f} "
                f"finger_to_object={_mean(task_env.finger_center_to_cube_dist):.4f} "
                f"finger_table_clearance={_mean(task_env.finger_table_clearance):.4f} "
                f"lift={_mean(task_env.cube_lift_height):.4f} "
                f"success={_mean(task_env.in_success_region.float()):.4f}",
                flush=True,
            )

    checks.check(
        "rollout_observation_reward_finite",
        len(reward_values) == num_steps,
        completed_steps=len(reward_values),
        requested_steps=num_steps,
    )
    checks.check(
        "rollout_no_immediate_termination_spike",
        early_done_count == 0,
        early_done_count=early_done_count,
        early_window_steps=min(5, num_steps),
        total_done_count=done_count,
    )
    checks.check(
        "rollout_object_stays_in_workspace",
        bool((task_env.cube_pos[:, 2] > task_env.cfg.table_surface_z - 0.08).all().item()),
        object_center_z_min=float(task_env.cube_pos[:, 2].detach().min().cpu()),
        object_bottom_z_min=min_object_bottom_z,
        done_count=done_count,
    )
    return {
        "steps_completed": len(reward_values),
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "done_count": done_count,
        "early_done_count": early_done_count,
        "min_mean_finger_table_clearance": min_finger_table_clearance,
        "min_object_bottom_z": min_object_bottom_z,
        "final_object_center_pos_mean": _tensor_list(task_env.cube_pos.mean(dim=0)),
        "final_success_rate": _mean(task_env.in_success_region.float()),
    }


def _write_rgb_artifact(frame, path: Path) -> str:
    import numpy as np

    rgb = np.asarray(frame)
    if rgb.ndim == 3 and rgb.shape[-1] >= 3:
        rgb = rgb[..., :3]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        png_path = path.with_suffix(".png")
        Image.fromarray(rgb).save(png_path)
        return str(png_path)
    except Exception:
        ppm_path = path.with_suffix(".ppm")
        header = f"P6\n{rgb.shape[1]} {rgb.shape[0]}\n255\n".encode("ascii")
        ppm_path.write_bytes(header + rgb.tobytes())
        return str(ppm_path)


def _run_render_checks(env, task_env, checks: CheckRecorder, output_dir: Path, num_frames: int) -> dict[str, object]:
    import numpy as np

    frame_summaries: list[dict[str, object]] = []
    num_frames = max(int(num_frames), 1)
    for frame_idx in range(num_frames):
        if frame_idx > 0:
            actions = torch.zeros((task_env.num_envs, task_env.cfg.action_space), device=task_env.device)
            env.step(actions)
        frame_arr = np.asarray(env.render())
        finite = bool(np.isfinite(frame_arr).all())
        nonempty = frame_arr.ndim == 3 and frame_arr.shape[0] >= 32 and frame_arr.shape[1] >= 32 and frame_arr.shape[2] >= 3
        dynamic_range = float(frame_arr[..., :3].max() - frame_arr[..., :3].min()) if nonempty else 0.0
        mean_value = float(frame_arr[..., :3].mean()) if nonempty else 0.0
        artifact = None
        if finite and nonempty:
            artifact = _write_rgb_artifact(frame_arr, output_dir / "render_check" / f"frame_{frame_idx:04d}.png")
        frame_summaries.append(
            {
                "frame_index": frame_idx,
                "shape": list(frame_arr.shape),
                "finite": finite,
                "dynamic_range": dynamic_range,
                "mean_value": mean_value,
                "artifact": artifact,
            }
        )

    checks.check(
        "render_check_frames_nonblank",
        all(
            bool(item["finite"])
            and len(item["shape"]) == 3
            and item["shape"][0] >= 32
            and item["shape"][1] >= 32
            and item["shape"][2] >= 3
            and float(item["dynamic_range"]) >= 5.0
            and float(item["mean_value"]) >= 1.0
            for item in frame_summaries
        ),
        frames=frame_summaries,
    )
    return {"enabled": True, "frames": frame_summaries}


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_multi_object_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    if args_cli.object_asset_manifest_path:
        env_cfg.object_asset_manifest_path = str(Path(args_cli.object_asset_manifest_path).expanduser().resolve())
    if args_cli.object_assets_dir:
        env_cfg.object_assets_dir = str(Path(args_cli.object_assets_dir).expanduser().resolve())
    if args_cli.max_objects is not None:
        env_cfg.max_objects = int(args_cli.max_objects)
    if args_cli.object_spawn_xy_randomization is not None:
        env_cfg.object_spawn_xy_randomization = float(args_cli.object_spawn_xy_randomization)
    if args_cli.object_spawn_yaw_randomization_deg is not None:
        env_cfg.object_spawn_yaw_randomization_deg = float(args_cli.object_spawn_yaw_randomization_deg)
    if args_cli.enable_grasp_prior_reset:
        env_cfg.grasp_prior_reset_enabled = True
        if args_cli.grasp_prior_library_dir:
            env_cfg.grasp_prior_library_dir = str(Path(args_cli.grasp_prior_library_dir).expanduser().resolve())
    env_cfg.grasp_prior_allow_missing = bool(args_cli.grasp_prior_allow_missing)
    _configure_validation_camera(env_cfg)

    checks = CheckRecorder()
    _run_registration_checks(args_cli.task, checks)
    needs_rgb_render = bool(args_cli.video or args_cli.render_check)
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if needs_rgb_render else None)
    if args_cli.video:
        env = gym.wrappers.RecordVideo(
            env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=args_cli.video_length,
            disable_logger=True,
        )
    task_env = env.unwrapped
    _configure_validation_camera(env_cfg, task_env=task_env)

    asset_summary = _run_asset_checks(task_env, checks)
    reset_summary = _run_reset_checks(env, task_env, checks)
    render_summary = (
        _run_render_checks(env, task_env, checks, output_dir, args_cli.render_check_frames)
        if args_cli.render_check
        else {"enabled": False}
    )
    grasp_prior_summary = _run_grasp_prior_reset_checks(
        env,
        task_env,
        checks,
        reset_cycles=args_cli.grasp_prior_reset_cycles,
    )
    rollout_summary = _run_short_rollout(env, task_env, checks, args_cli.num_steps, args_cli.print_interval)

    payload = {
        "passed": checks.passed,
        "checks": checks.records,
        "task": args_cli.task,
        "num_envs": args_cli.num_envs,
        "num_steps": args_cli.num_steps,
        "seed": args_cli.seed,
        "asset_summary": asset_summary,
        "reset_summary": reset_summary,
        "render_summary": render_summary,
        "grasp_prior_reset_summary": grasp_prior_summary,
        "rollout_summary": rollout_summary,
        "config": {
            "object_asset_manifest_path": str(getattr(task_env.cfg, "object_asset_manifest_path", "")),
            "object_assets_dir": str(getattr(task_env.cfg, "object_assets_dir", "")),
            "max_objects": int(getattr(task_env.cfg, "max_objects", 0)),
            "object_spawn_xy_randomization": float(task_env.cfg.object_spawn_xy_randomization),
            "object_spawn_yaw_randomization_deg": float(task_env.cfg.object_spawn_yaw_randomization_deg),
            "grasp_prior_reset_enabled": bool(task_env.cfg.grasp_prior_reset_enabled),
            "grasp_prior_library_dir": str(getattr(task_env.cfg, "grasp_prior_library_dir", "")),
            "robot_base_z": float(getattr(task_env.cfg, "robot_base_z", 0.0)),
        },
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] Wrote metrics to {metrics_path}", flush=True)
    env.close()
    simulation_app.close()
    if not checks.passed:
        failed = [record["name"] for record in checks.records if not bool(record["passed"])]
        raise SystemExit(f"Validation failed: {failed}")
    print("DEXTRAH_FRANKA_MULTI_OBJECT_ENV_VALIDATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
