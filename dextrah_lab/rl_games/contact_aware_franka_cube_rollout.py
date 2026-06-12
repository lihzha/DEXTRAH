"""Bounded contact-aware Franka cube controller rollout smoke.

This script does not train. It probes whether a live Isaac controller rollout
can generate a physically plausible close/lift demonstration after raw
GraspGenX/cuRobo labels were shown to target an EE/TCP point that is not the
cube contact point. The controller targets measured finger-center geometry
instead of raw source EE waypoints and writes inspectable metrics/videos.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", required=True, type=str, help="Converted lowdim NPZ used for cube/source reset.")
parser.add_argument("--trajectory_json", required=True, type=str, help="Raw source trajectory JSON for joint reset.")
parser.add_argument("--output_dir", default=None, type=str)
parser.add_argument("--task", default="Dextrah-Franka-Cube-Grasp", type=str)
parser.add_argument("--episode", default=24, type=int)
parser.add_argument("--episode_step", default=260, type=int)
parser.add_argument("--seed", default=42, type=int)
parser.add_argument("--variant", action="append", default=[], help="Variant name or name:x,y,z offset in meters.")
parser.add_argument("--align_steps", default=80, type=int)
parser.add_argument("--close_steps", default=80, type=int)
parser.add_argument("--lift_steps", default=120, type=int)
parser.add_argument("--lift_height", default=0.14, type=float)
parser.add_argument("--finger_gain", default=0.75, type=float)
parser.add_argument("--clip_actions", default=1.0, type=float)
parser.add_argument("--print_interval", default=40, type=int)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", default=280, type=int)
parser.add_argument("--video_name_prefix", default="franka-cube-contact-rollout", type=str)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
from dextrah_lab.offline_dp_bc.action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    derive_relative_ee_actions,
)
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_PPO_OBS_DIM,
    extract_lowdim_obs_from_ppo_obs,
)


KNOWN_VARIANTS: dict[str, tuple[float, float, float]] = {
    "center": (0.0, 0.0, 0.0),
    "center_high15": (0.0, 0.0, 0.015),
    "center_high30": (0.0, 0.0, 0.030),
}


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    ep_idx = min(max(ep_idx, 0), int(episode_ends.shape[0] - 1))
    start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    end = int(episode_ends[ep_idx])
    return ep_idx, start, end


def _row_for_episode_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> int:
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    local_step = int(np.clip(int(episode_step), 0, max(0, end - start - 1)))
    return int(start + local_step)


def _parse_variant(spec: str) -> tuple[str, np.ndarray]:
    if ":" not in spec:
        if spec not in KNOWN_VARIANTS:
            raise ValueError(f"Unknown variant {spec!r}; use one of {sorted(KNOWN_VARIANTS)} or name:x,y,z")
        return spec, np.asarray(KNOWN_VARIANTS[spec], dtype=np.float32)
    name, raw = spec.split(":", 1)
    values = [float(v) for v in raw.split(",")]
    if len(values) != 3:
        raise ValueError(f"Variant offset must have three comma-separated values: {spec}")
    return name, np.asarray(values, dtype=np.float32)


def _policy_obs_from_reset(reset_out: Any) -> torch.Tensor:
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    return obs["policy"] if isinstance(obs, dict) else obs


def _policy_obs_from_step(step_out: Any) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    if len(step_out) == 5:
        obs, rewards, terminated, truncated, _info = step_out
    else:
        obs, rewards, dones, _info = step_out
        terminated = dones
        truncated = torch.zeros_like(dones, dtype=torch.bool)
    return obs["policy"] if isinstance(obs, dict) else obs, rewards, terminated, truncated


def _policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _lowdim_numpy_from_policy_obs(policy_obs: Any) -> np.ndarray:
    lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs)
    if hasattr(lowdim, "detach"):
        lowdim_np = lowdim.detach().float().cpu().numpy()
    else:
        lowdim_np = np.asarray(lowdim, dtype=np.float32)
    if lowdim_np.ndim == 1:
        return lowdim_np.astype(np.float32, copy=False)
    if lowdim_np.ndim == 2 and lowdim_np.shape[0] >= 1:
        return lowdim_np[0].astype(np.float32, copy=False)
    raise ValueError(f"Expected lowdim obs shape (21,) or (N, 21), got {lowdim_np.shape}")


def _map_source_joint_to_env(task_env: Any, raw_q: np.ndarray, env_ids: torch.Tensor) -> torch.Tensor:
    num_ids = int(env_ids.numel())
    raw_q_tensor = torch.as_tensor(raw_q, dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    joint_pos = task_env._robot.data.default_joint_pos[env_ids].clone()
    arm_count = len(task_env.arm_joint_ids)
    finger_count = len(task_env.finger_joint_ids)
    if raw_q_tensor.shape[1] == joint_pos.shape[1]:
        joint_pos[:] = raw_q_tensor
    elif raw_q_tensor.shape[1] == arm_count + finger_count:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + finger_count]
    elif raw_q_tensor.shape[1] == arm_count + 1:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + 1].repeat(1, finger_count)
    else:
        raise ValueError(f"Cannot map source joint dim {raw_q_tensor.shape[1]} to env joints {joint_pos.shape[1]}")
    return torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _reset_to_source(
    gym_env: Any,
    task_env: Any,
    *,
    dataset_obs: np.ndarray,
    episode_start: int,
    row_idx: int,
    raw_q: np.ndarray,
    seed: int,
) -> np.ndarray:
    _policy_obs_from_reset(gym_env.reset(seed=int(seed)))
    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    joint_pos = _map_source_joint_to_env(task_env, raw_q, env_ids)
    joint_vel = torch.zeros_like(joint_pos)
    task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    task_env.robot_dof_targets[env_ids] = joint_pos
    task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]

    num_ids = int(env_ids.numel())
    target_obs = dataset_obs[row_idx]
    cube_pos = torch.as_tensor(target_obs[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    cube_quat = torch.as_tensor(target_obs[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    object_state = torch.zeros(num_ids, 13, device=task_env.device)
    object_state[:, 0:3] = cube_pos + task_env.scene.env_origins[env_ids]
    object_state[:, 3:7] = cube_quat
    task_env._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
    initial_cube = torch.as_tensor(
        dataset_obs[episode_start, 7:10], dtype=torch.float32, device=task_env.device
    ).repeat(num_ids, 1)
    task_env.cube_initial_pos[env_ids] = initial_cube
    task_env.cube_goal_pos[env_ids] = cube_pos
    task_env.cube_goal_pos[env_ids, 2] = cube_pos[:, 2] + float(task_env.cfg.cube_lift_height)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env.actions[env_ids] = 0.0
    task_env.ik_controller.reset(env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    return _policy_obs_from_task_env(task_env).detach().float().cpu().numpy()[0]


def _finger_center(task_env: Any) -> np.ndarray:
    task_env._compute_intermediate_values()
    left = task_env.left_finger_pos.detach().float().cpu().numpy()[0]
    right = task_env.right_finger_pos.detach().float().cpu().numpy()[0]
    return 0.5 * (left + right)


def _action_to_finger_target(
    live_lowdim: np.ndarray,
    finger_center: np.ndarray,
    target_finger_center: np.ndarray,
    *,
    gripper_action: float,
    gain: float,
    clip: float,
) -> np.ndarray:
    finger_error = np.asarray(target_finger_center, dtype=np.float32) - np.asarray(finger_center, dtype=np.float32)
    target_ee_pos = live_lowdim[:3] + float(gain) * finger_error
    ee_pos = np.stack((live_lowdim[:3], target_ee_pos), axis=0).astype(np.float32)
    ee_quat = np.stack((live_lowdim[3:7], live_lowdim[3:7]), axis=0).astype(np.float32)
    grip = np.asarray([float(gripper_action), float(gripper_action)], dtype=np.float32)
    action = derive_relative_ee_actions(
        ee_pos,
        ee_quat,
        gripper_action=grip,
        convention=DEFAULT_DEXTRAH_ACTION_CONVENTION,
        terminal_action="drop",
    )[0].astype(np.float32)
    if math.isfinite(float(clip)) and float(clip) > 0:
        action = np.clip(action, -float(clip), float(clip))
    return action


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    variants = list(dict.fromkeys(str(row["variant"]) for row in rows))
    fig, axes = plt.subplots(5, 1, figsize=(13, 16), sharex=True, constrained_layout=True)
    for variant in variants:
        vrows = [row for row in rows if row["variant"] == variant]
        x = [int(row["global_step"]) for row in vrows]
        axes[0].plot(x, [row["ee_to_cube"] for row in vrows], label=f"{variant} ee")
        axes[0].plot(x, [row["finger_center_to_cube"] for row in vrows], linestyle="--", label=f"{variant} finger")
        axes[1].plot(x, [row["cube_lift_height"] for row in vrows], label=variant)
        axes[2].plot(x, [row["gripper_width"] for row in vrows], label=f"{variant} width")
        axes[2].plot(x, [row["gripper_action"] for row in vrows], linestyle="--", label=f"{variant} action")
        axes[3].plot(x, [row["finger_error_norm"] for row in vrows], label=variant)
        axes[4].plot(x, [row["pose_action_clip_fraction"] for row in vrows], label=variant)
    axes[0].set_title("EE/Finger-Center To Cube")
    axes[0].set_ylabel("m")
    axes[1].set_title("Cube Lift Height")
    axes[1].set_ylabel("m")
    axes[2].set_title("Gripper Width And Action")
    axes[2].set_ylabel("m / action")
    axes[3].set_title("Finger-Center Target Error")
    axes[3].set_ylabel("m")
    axes[4].set_title("Pose Action Clip Fraction")
    axes[4].set_ylabel("fraction")
    axes[4].set_xlabel("global step")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _latest_video_files(video_folder: Path) -> list[str]:
    if not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube Contact-Aware Rollout Smoke",
        "",
        "This bounded Isaac smoke does not train. It probes whether a live controller rollout that targets measured finger-center geometry can produce a stable close/lift trajectory before any DP BC work resumes.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Variant Summary",
        "",
        "| variant | offset | steps | final EE-cube | min finger-cube | final finger-cube | max lift | final lift | final grip width | max clip | terminal next | skipped reset step | success-like |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for variant, payload in summary["variants"].items():
        lines.append(
            f"| {variant} | {payload['offset']} | {payload['steps']} | "
            f"{payload['final_ee_to_cube']:.4f} | {payload['min_finger_center_to_cube']:.4f} | "
            f"{payload['final_finger_center_to_cube']:.4f} | {payload['max_cube_lift_height']:.4f} | "
            f"{payload['final_cube_lift_height']:.4f} | {payload['final_gripper_width']:.5f} | "
            f"{payload['max_pose_action_clip_fraction']:.3f} | {payload['terminated_next_step']} | "
            f"{payload['skipped_post_reset_local_step']} | {payload['success_like']} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- CSV: `{summary['csv']}`",
            f"- JSON: `{summary['json']}`",
            f"- Plot: `{summary['plot']}`",
            f"- Videos: `{summary['video_files']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_contact_rollout_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args_cli.dataset).expanduser().resolve()
    trajectory_path = Path(args_cli.trajectory_json).expanduser().resolve()
    data = np.load(dataset_path, allow_pickle=False)
    dataset_obs = np.asarray(data["obs"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    row_idx = _row_for_episode_step(episode_ends, int(args_cli.episode), int(args_cli.episode_step))
    episode_idx, episode_start, _episode_end = _episode_for_row(row_idx, episode_ends)
    frames = json.loads(trajectory_path.read_text(encoding="utf-8"))["frames"]
    raw_q = np.asarray(frames[int(row_idx - episode_start)]["joint_position"], dtype=np.float32)
    variants = [_parse_variant(v) for v in (args_cli.variant or ["center", "center_high15", "center_high30"])]

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    if hasattr(env_cfg, "viewer"):
        env_cfg.viewer.eye = tuple(args_cli.camera_eye)
        env_cfg.viewer.lookat = tuple(args_cli.camera_target)
        env_cfg.viewer.origin_type = "world"
    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    task_env = gym_env.unwrapped
    if hasattr(task_env, "sim") and hasattr(env_cfg, "viewer"):
        try:
            task_env.sim.set_camera_view(eye=tuple(args_cli.camera_eye), target=tuple(args_cli.camera_target))
        except Exception:
            pass
    steps_per_variant = int(args_cli.align_steps + args_cli.close_steps + args_cli.lift_steps)
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(output_dir / "videos"),
            step_trigger=lambda step: step % max(1, steps_per_variant) == 0,
            video_length=int(args_cli.video_length),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )

    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    global_step = 0
    try:
        for variant_idx, (variant_name, offset) in enumerate(variants):
            policy_obs = _reset_to_source(
                gym_env,
                task_env,
                dataset_obs=dataset_obs,
                episode_start=episode_start,
                row_idx=row_idx,
                raw_q=raw_q,
                seed=int(args_cli.seed),
            )
            if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
                raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")
            initial_cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0].copy()
            for local_step in range(steps_per_variant):
                if local_step < int(args_cli.align_steps):
                    phase = "align_open"
                    gripper = 1.0
                    lift_delta = np.zeros(3, dtype=np.float32)
                elif local_step < int(args_cli.align_steps + args_cli.close_steps):
                    phase = "close_hold"
                    gripper = -1.0
                    lift_delta = np.zeros(3, dtype=np.float32)
                else:
                    phase = "lift"
                    gripper = -1.0
                    frac = (local_step - int(args_cli.align_steps + args_cli.close_steps) + 1) / max(1, int(args_cli.lift_steps))
                    lift_delta = np.asarray((0.0, 0.0, float(args_cli.lift_height) * min(1.0, frac)), dtype=np.float32)
                task_env._compute_intermediate_values()
                live_lowdim = _lowdim_numpy_from_policy_obs(policy_obs)
                finger_center = _finger_center(task_env)
                cube_pos = task_env.cube_pos.detach().float().cpu().numpy()[0]
                target_finger = initial_cube_pos + offset + lift_delta
                action = _action_to_finger_target(
                    live_lowdim,
                    finger_center,
                    target_finger,
                    gripper_action=gripper,
                    gain=float(args_cli.finger_gain),
                    clip=float(args_cli.clip_actions),
                )
                clip_hits = np.abs(action[:6]) >= (float(args_cli.clip_actions) - 1.0e-6)
                policy_obs, rewards, terminated, truncated = _policy_obs_from_step(
                    gym_env.step(torch.as_tensor(action[None], dtype=torch.float32, device=task_env.device))
                )
                after_lowdim = _lowdim_numpy_from_policy_obs(policy_obs)
                task_env._compute_intermediate_values()
                terminated_flag = bool(terminated.detach().cpu().numpy()[0]) if hasattr(terminated, "detach") else bool(terminated[0])
                truncated_flag = bool(truncated.detach().cpu().numpy()[0]) if hasattr(truncated, "detach") else bool(truncated[0])
                done_flag = terminated_flag or truncated_flag
                if done_flag:
                    if rows and rows[-1].get("variant") == variant_name:
                        rows[-1]["terminated_next_step"] = terminated_flag
                        rows[-1]["truncated_next_step"] = truncated_flag
                        rows[-1]["terminal_reward_next"] = float(rewards.detach().float().cpu()[0])
                        rows[-1]["skipped_post_reset_local_step"] = int(local_step)
                        rows[-1]["skipped_post_reset_gripper_width"] = float(after_lowdim[20])
                        rows[-1]["skipped_post_reset_cube_lift_height"] = float(
                            task_env.cube_lift_height.detach().cpu()[0]
                        )
                    break
                row = {
                    "variant": variant_name,
                    "variant_index": variant_idx,
                    "offset": offset.astype(float).tolist(),
                    "global_step": global_step,
                    "local_step": local_step,
                    "phase": phase,
                    "episode": int(episode_idx),
                    "episode_step": int(row_idx - episode_start),
                    "target_finger_center": target_finger.astype(float).tolist(),
                    "finger_center": finger_center.astype(float).tolist(),
                    "finger_error_norm": float(np.linalg.norm(target_finger - finger_center)),
                    "cube_pos": cube_pos.astype(float).tolist(),
                    "ee_to_cube": float(task_env.ee_to_cube_dist.detach().cpu()[0]),
                    "finger_center_to_cube": float(task_env.finger_center_to_cube_dist.detach().cpu()[0]),
                    "left_finger_to_cube": float(task_env.left_finger_to_cube_dist.detach().cpu()[0]),
                    "right_finger_to_cube": float(task_env.right_finger_to_cube_dist.detach().cpu()[0]),
                    "cube_lift_height": float(task_env.cube_lift_height.detach().cpu()[0]),
                    "cube_xy_error": float(task_env.cube_xy_error.detach().cpu()[0]),
                    "gripper_width": float(after_lowdim[20]),
                    "gripper_action": float(action[6]),
                    "executed_action": action.astype(float).tolist(),
                    "pose_action_clip_fraction": float(np.count_nonzero(clip_hits) / 6.0),
                    "reward": float(rewards.detach().float().cpu()[0]),
                    "terminated_next_step": False,
                    "truncated_next_step": False,
                }
                rows.append(row)
                if args_cli.print_interval > 0 and (
                    local_step == 0 or (local_step + 1) % int(args_cli.print_interval) == 0
                ):
                    print(
                        "CONTACT_ROLLOUT_STEP "
                        + json.dumps(
                            {
                                "variant": variant_name,
                                "local_step": local_step + 1,
                                "phase": phase,
                                "finger_center_to_cube": row["finger_center_to_cube"],
                                "cube_lift_height": row["cube_lift_height"],
                                "gripper_width": row["gripper_width"],
                                "clip_fraction": row["pose_action_clip_fraction"],
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                global_step += 1
            vrows = [row for row in rows if row["variant"] == variant_name]
            last = vrows[-1]
            max_lift = float(max(row["cube_lift_height"] for row in vrows))
            final_lift = float(last["cube_lift_height"])
            min_finger = float(min(row["finger_center_to_cube"] for row in vrows))
            success_like = bool(max_lift >= float(task_env.cfg.cube_success_lift_height) and min_finger < 0.08)
            summaries[variant_name] = {
                "offset": offset.astype(float).tolist(),
                "steps": len(vrows),
                "final_ee_to_cube": float(last["ee_to_cube"]),
                "min_finger_center_to_cube": min_finger,
                "final_finger_center_to_cube": float(last["finger_center_to_cube"]),
                "max_cube_lift_height": max_lift,
                "final_cube_lift_height": final_lift,
                "final_gripper_width": float(last["gripper_width"]),
                "max_pose_action_clip_fraction": float(max(row["pose_action_clip_fraction"] for row in vrows)),
                "terminated_next_step": bool(any(row.get("terminated_next_step", False) for row in vrows)),
                "truncated_next_step": bool(any(row.get("truncated_next_step", False) for row in vrows)),
                "skipped_post_reset_local_step": int(
                    max(
                        [row.get("skipped_post_reset_local_step", -1) for row in vrows],
                        default=-1,
                    )
                ),
                "success_like": success_like,
            }
    finally:
        gym_env.close()

    csv_path = output_dir / "contact_rollout_steps.csv"
    json_path = output_dir / "contact_rollout_summary.json"
    plot_path = output_dir / "contact_rollout_plot.png"
    report_path = output_dir / "contact_rollout_report.md"
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)
    any_success = any(payload["success_like"] for payload in summaries.values())
    verdict = (
        "At least one contact-aware rollout variant lifted the cube to the success threshold; inspect video before DP relabeling."
        if any_success
        else "No contact-aware rollout variant produced stable lift; controller-rollout relabeling needs more grasp/contact design before DP."
    )
    summary = {
        "dataset": str(dataset_path),
        "trajectory_json": str(trajectory_path),
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "episode": int(episode_idx),
        "episode_step": int(row_idx - episode_start),
        "align_steps": int(args_cli.align_steps),
        "close_steps": int(args_cli.close_steps),
        "lift_steps": int(args_cli.lift_steps),
        "lift_height": float(args_cli.lift_height),
        "finger_gain": float(args_cli.finger_gain),
        "clip_actions": float(args_cli.clip_actions),
        "variants": summaries,
        "verdict": verdict,
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "report": str(report_path),
        "video_files": _latest_video_files(output_dir / "videos"),
    }
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_build_report(summary), encoding="utf-8")
    print(
        "FRANKA_CUBE_CONTACT_ROLLOUT_DONE "
        + json.dumps(
            {
                "output_dir": str(output_dir),
                "report": str(report_path),
                "summary_json": str(json_path),
                "verdict": verdict,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"FRANKA_CUBE_CONTACT_ROLLOUT_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
