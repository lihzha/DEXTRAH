"""Bounded Franka cube teacher-forcing replay for DP BC debugging.

This script does not train. It resets the DEXTRAH Franka cube Isaac env,
extracts the same 21D lowdim observation used by the Diffusion Policy bridge,
finds the nearest row in a converted cuRobo dataset, compares the official DP
prediction against the dataset label, then executes a short action sequence in
the real env/controller. The output is meant to answer whether dataset labels
and predicted/executed actions produce the expected end-effector motion
direction under the real DEXTRAH controller.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", type=str, required=True, help="Converted lowdim NPZ dataset visible in container.")
parser.add_argument("--checkpoint", type=str, required=True, help="Official Diffusion Policy checkpoint.")
parser.add_argument("--diffusion_policy_root", type=str, default=None, help="Path to real-stanford/diffusion_policy.")
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--steps", type=int, default=8)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--num_inference_steps", type=int, default=100)
parser.add_argument(
    "--mode",
    action="append",
    default=[],
    choices=[
        "dataset_t",
        "dataset_t_plus_1",
        "dataset_t_plus_7",
        "dataset_open_t",
        "dataset_open_t_plus_1",
        "dataset_open_t_plus_7",
        "dp_replan",
    ],
    help="Replay mode. May be passed multiple times. Defaults to dataset_t and dp_replan.",
)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--print_interval", type=int, default=1)
parser.add_argument("--camera_eye", type=float, nargs=3, default=None)
parser.add_argument("--camera_target", type=float, nargs=3, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=80)
parser.add_argument("--video_name_prefix", type=str, default="franka-cube-dp-replay")
parser.add_argument(
    "--demo_reset_dataset",
    type=str,
    default=None,
    help="Optional converted lowdim NPZ dataset used to overwrite reset cube pose from a selected demo row.",
)
parser.add_argument("--demo_reset_episode", type=int, default=0)
parser.add_argument("--demo_reset_step", type=int, default=0)
parser.add_argument(
    "--dataset_start_row",
    type=int,
    default=-1,
    help="Optional global dataset row used as the start of replay labels. Overrides nearest-row selection.",
)
parser.add_argument(
    "--dataset_start_episode",
    type=int,
    default=-1,
    help="Optional episode index for replay label start. Ignored when --dataset_start_row is non-negative.",
)
parser.add_argument(
    "--dataset_start_step",
    type=int,
    default=0,
    help="Episode-local step for replay label start when --dataset_start_episode is set.",
)
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
from dextrah_lab.offline_dp_bc.action_conversion import normalized_action_to_world_delta
from dextrah_lab.offline_dp_bc.analyze_policy_trace import POSITION_FEATURE_IDX
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    LowdimObsHistory,
    extract_lowdim_obs_from_ppo_obs,
    predict_action_sequence_from_ppo_obs,
)
from dextrah_lab.offline_dp_bc.trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)


def _phase_names() -> list[str]:
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    ep_idx = min(max(ep_idx, 0), int(episode_ends.shape[0] - 1))
    start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    end = int(episode_ends[ep_idx])
    return ep_idx, start, end


def _row_for_episode_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> int:
    if episode_ends.size == 0:
        raise ValueError("dataset has no episodes")
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    local_step = int(np.clip(int(episode_step), 0, max(0, end - start - 1)))
    return int(start + local_step)


def _clipped_row(row_idx: int, episode_ends: np.ndarray) -> int:
    _ep, start, end = _episode_for_row(row_idx, episode_ends)
    return int(np.clip(int(row_idx), start, end - 1))


def _nearest_dataset_row(obs: np.ndarray, query_obs: np.ndarray) -> tuple[int, float]:
    std = np.maximum(obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4)
    dist = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - query_obs[POSITION_FEATURE_IDX]) / std) ** 2).mean(axis=1))
    idx = int(np.argmin(dist))
    return idx, float(dist[idx])


def _episode_step(row_idx: int, episode_ends: np.ndarray) -> int:
    _ep, start, _end = _episode_for_row(row_idx, episode_ends)
    return int(row_idx - start)


def _phase_name_for_row(phase_ids: np.ndarray, phase_names: list[str], row_idx: int) -> str:
    return str(phase_names[int(phase_ids[int(row_idx)])])


def _demo_reset_payload(path: Path | None, episode: int, episode_step: int) -> dict[str, Any] | None:
    if path is None:
        return None
    data = np.load(path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    row_idx = _row_for_episode_step(episode_ends, episode, episode_step)
    ep_idx, start, end = _episode_for_row(row_idx, episode_ends)
    phase_names = _phase_names()
    return {
        "path": str(path),
        "obs": obs,
        "action": action,
        "phase_ids": phase_ids,
        "episode_ends": episode_ends,
        "phase_names": phase_names,
        "episode": int(ep_idx),
        "episode_start": int(start),
        "episode_end": int(end),
        "episode_step": int(row_idx - start),
        "row": int(row_idx),
        "phase": _phase_name_for_row(phase_ids, phase_names, row_idx),
        "target_obs": obs[row_idx].copy(),
        "target_action": action[row_idx].copy(),
    }


def _policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _apply_demo_reset(task_env: Any, demo_reset: dict[str, Any]) -> tuple[torch.Tensor, dict[str, Any]]:
    """Overwrite cube pose/goal from a converted demo row.

    The converted lowdim dataset does not contain Franka joint states, so this
    diagnostic intentionally leaves the robot at the task reset state and
    reports the remaining lowdim mismatch after object reset.
    """

    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    num_ids = int(env_ids.numel())
    target_obs = np.asarray(demo_reset["target_obs"], dtype=np.float32)
    target_cube_pos = torch.as_tensor(target_obs[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    target_cube_quat = torch.as_tensor(target_obs[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    object_state = torch.zeros(num_ids, 13, device=task_env.device)
    object_state[:, 0:3] = target_cube_pos + task_env.scene.env_origins[env_ids]
    object_state[:, 3:7] = target_cube_quat
    task_env._cube.write_root_state_to_sim(object_state, env_ids=env_ids)

    task_env.cube_initial_pos[env_ids] = target_cube_pos
    task_env.cube_goal_pos[env_ids] = target_cube_pos
    task_env.cube_goal_pos[env_ids, 2] = target_cube_pos[:, 2] + float(task_env.cfg.cube_lift_height)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env.actions[env_ids] = 0.0
    task_env.ik_controller.reset(env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()

    policy_obs = _policy_obs_from_task_env(task_env)
    live_lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()
    live0 = live_lowdim[0]
    diff = live0 - target_obs
    summary = {
        "dataset": str(demo_reset["path"]),
        "episode": int(demo_reset["episode"]),
        "episode_step": int(demo_reset["episode_step"]),
        "row": int(demo_reset["row"]),
        "phase": str(demo_reset["phase"]),
        "target_cube_pos": target_obs[7:10].astype(float).tolist(),
        "target_cube_quat": target_obs[10:14].astype(float).tolist(),
        "target_cube_minus_ee": target_obs[14:17].astype(float).tolist(),
        "target_gripper_width": float(target_obs[20]),
        "target_action": np.asarray(demo_reset["target_action"], dtype=np.float32).astype(float).tolist(),
        "live_lowdim_after_reset_env0": live0.astype(float).tolist(),
        "live_cube_pos_after_reset_env0": live0[7:10].astype(float).tolist(),
        "live_cube_minus_ee_after_reset_env0": live0[14:17].astype(float).tolist(),
        "lowdim_linf_diff_env0": float(np.max(np.abs(diff))),
        "lowdim_l2_diff_env0": float(np.linalg.norm(diff)),
        "cube_pos_l2_diff_env0": float(np.linalg.norm(diff[7:10])),
        "cube_minus_ee_l2_diff_env0": float(np.linalg.norm(diff[14:17])),
        "exact_robot_joint_reset_available": False,
        "robot_reset_note": "converted lowdim NPZ has no Franka joint state; robot remains at task reset",
    }
    return policy_obs, summary


def _load_policy(checkpoint: Path, device: str, num_inference_steps: int, diffusion_policy_root: str | None):
    if diffusion_policy_root:
        root = str(Path(diffusion_policy_root).expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
    from diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace import (
        TrainDiffusionUnetLowdimWorkspace,
    )

    workspace = TrainDiffusionUnetLowdimWorkspace.create_from_checkpoint(str(checkpoint))
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    policy.num_inference_steps = int(num_inference_steps)
    policy.to(torch.device(device))
    policy.eval()
    return workspace, policy


def _policy_obs_from_reset(reset_out: Any) -> torch.Tensor:
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    return obs["policy"] if isinstance(obs, dict) else obs


def _policy_obs_from_step(step_out: Any) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, Any]:
    if len(step_out) == 5:
        obs, rewards, terminated, truncated, info = step_out
    else:
        obs, rewards, dones, info = step_out
        terminated = dones
        truncated = torch.zeros_like(dones, dtype=torch.bool)
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    return policy_obs, rewards, terminated, truncated, info


def _reset_env(gym_env: Any, seed: int) -> torch.Tensor:
    try:
        return _policy_obs_from_reset(gym_env.reset(seed=int(seed)))
    except TypeError:
        return _policy_obs_from_reset(gym_env.reset())


def _mean_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _env_metric(task_env: Any, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    return _mean_float(getattr(task_env, name))


def _env_metric_for_env(task_env: Any, name: str, env_idx: int) -> float | None:
    if not hasattr(task_env, name):
        return None
    value = getattr(task_env, name)
    if isinstance(value, torch.Tensor):
        return float(value.detach().flatten()[int(env_idx)].cpu())
    try:
        arr = np.asarray(value).reshape(-1)
        return float(arr[int(env_idx)])
    except Exception:
        return _mean_float(value)


def _configure_eval_camera(env_cfg: Any, task_env: Any | None = None) -> None:
    if args_cli.camera_eye is None and args_cli.camera_target is None and not args_cli.video:
        return
    if not hasattr(env_cfg, "viewer"):
        return
    eye = tuple(args_cli.camera_eye or DEFAULT_CAMERA_EYE)
    target = tuple(args_cli.camera_target or DEFAULT_CAMERA_TARGET)
    if task_env is not None and hasattr(task_env, "scene") and len(task_env.scene.env_origins) > 0:
        origin = task_env.scene.env_origins[0].detach().cpu().tolist()
        eye = tuple(float(eye[idx]) + origin[idx] for idx in range(3))
        target = tuple(float(target[idx]) + origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception:
            pass


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _latest_video_files(video_folder: Path) -> list[str]:
    if not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _safe_norm(value: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(value, dtype=np.float64)))


def _cosine(a: np.ndarray, b: np.ndarray) -> float | None:
    a_norm = _safe_norm(a)
    b_norm = _safe_norm(b)
    if a_norm < 1.0e-8 or b_norm < 1.0e-8:
        return None
    return float(np.dot(a, b) / (a_norm * b_norm))


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    modes = list(dict.fromkeys(str(row["mode"]) for row in rows))
    fig, axes = plt.subplots(5, 1, figsize=(13, 16), sharex=True, constrained_layout=True)
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode and int(row["env_index"]) == 0]
        x = [row["step"] for row in mode_rows]
        axes[0].plot(x, [row["ee_to_cube_after"] for row in mode_rows], label=f"{mode} ee")
        axes[0].plot(x, [row["finger_center_to_cube_dist_after"] for row in mode_rows], linestyle="--", label=f"{mode} finger")
        axes[1].plot(x, [row["live_cube_minus_ee_after_x"] for row in mode_rows], label=f"{mode} x")
        axes[1].plot(x, [row["live_cube_minus_ee_after_y"] for row in mode_rows], label=f"{mode} y")
        axes[1].plot(x, [row["live_cube_minus_ee_after_z"] for row in mode_rows], label=f"{mode} z")
        axes[2].plot(x, [row["gripper_width_after"] for row in mode_rows], label=f"{mode} width")
        axes[2].plot(x, [row["executed_gripper"] for row in mode_rows], linestyle="--", label=f"{mode} action")
        axes[3].plot(x, [row["nearest_live_distance"] for row in mode_rows], label=mode)
        axes[4].plot(x, [row["actual_vs_expected_xyz_cosine"] for row in mode_rows], label=mode)
        first_neg = next((row["step"] for row in mode_rows if row["executed_gripper"] < 0.0), None)
        if first_neg is not None:
            for ax in axes:
                ax.axvline(first_neg, color="tab:red", alpha=0.2, linestyle="--")
    axes[0].set_title("EE/Finger To Cube Distance After Step")
    axes[0].set_ylabel("m")
    axes[1].set_title("Live Cube Minus EE After Step")
    axes[1].set_ylabel("m")
    axes[2].set_title("Gripper Width And Executed Gripper Action")
    axes[2].set_ylabel("m / action")
    axes[3].set_title("Nearest Demo Distance")
    axes[3].set_ylabel("scaled distance")
    axes[4].set_title("Actual EE Delta vs Expected Action World Delta")
    axes[4].set_ylabel("cosine")
    axes[4].set_xlabel("replay step")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=6, ncol=2)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube DP Dataset-Action Replay",
        "",
        "This is a bounded Isaac controller replay. It does not train. Each mode resets the env, optionally applies a demo-conditioned cube reset, chooses either a fixed demo label window or the nearest converted cuRobo demo row, compares official-DP prediction against dataset labels, and executes a short sequence.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Reset / Label Selection",
        "",
        f"- Demo reset: `{summary['demo_reset']}`",
        f"- Dataset start: `{summary['dataset_start']}`",
        "",
        "## Mode Summary",
        "",
        "| mode | steps | nearest row | nearest phase | final EE-cube | final finger-cube | final cube-minus-EE | first close | first hard close | mean delta cosine |",
        "|---|---:|---:|---|---:|---:|---|---:|---:|---:|",
    ]
    for mode, payload in summary["modes"].items():
        lines.append(
            f"| {mode} | {payload['steps']} | {payload['initial_nearest_row']} | {payload['initial_nearest_phase']} | "
            f"{payload['final_ee_to_cube']:.4f} | {payload['final_finger_center_to_cube']:.4f} | "
            f"{payload['final_cube_minus_ee']} | {payload['first_executed_negative_step']} | "
            f"{payload['first_executed_hard_close_step']} | {payload['mean_actual_vs_expected_xyz_cosine']:.4f} |"
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
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_dp_replay_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args_cli.dataset).expanduser().resolve()
    checkpoint_path = Path(args_cli.checkpoint).expanduser().resolve()
    data = np.load(dataset_path, allow_pickle=False)
    dataset_obs = np.asarray(data["obs"], dtype=np.float32)
    dataset_action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    phase_names = _phase_names()
    demo_reset_dataset_path = (
        Path(args_cli.demo_reset_dataset).expanduser().resolve() if args_cli.demo_reset_dataset else None
    )
    if demo_reset_dataset_path is not None and not demo_reset_dataset_path.is_file():
        raise FileNotFoundError(demo_reset_dataset_path)
    demo_reset = _demo_reset_payload(
        demo_reset_dataset_path,
        int(args_cli.demo_reset_episode),
        int(args_cli.demo_reset_step),
    )
    dataset_start_row: int | None = None
    dataset_start_source = "nearest_live_row"
    if int(args_cli.dataset_start_row) >= 0:
        dataset_start_row = _clipped_row(int(args_cli.dataset_start_row), episode_ends)
        dataset_start_source = "global_row"
    elif int(args_cli.dataset_start_episode) >= 0:
        dataset_start_row = _row_for_episode_step(
            episode_ends,
            int(args_cli.dataset_start_episode),
            int(args_cli.dataset_start_step),
        )
        dataset_start_source = "episode_step"
    dataset_start_summary: dict[str, Any] | None = None
    if dataset_start_row is not None:
        dataset_start_episode, dataset_start_ep_start, _dataset_start_ep_end = _episode_for_row(
            dataset_start_row, episode_ends
        )
        dataset_start_summary = {
            "source": dataset_start_source,
            "row": int(dataset_start_row),
            "episode": int(dataset_start_episode),
            "episode_step": int(dataset_start_row - dataset_start_ep_start),
            "phase": _phase_name_for_row(phase_ids, phase_names, dataset_start_row),
            "cube_minus_ee": dataset_obs[dataset_start_row, 14:17].astype(float).tolist(),
            "gripper_width": float(dataset_obs[dataset_start_row, 20]),
            "action": dataset_action[dataset_start_row].astype(float).tolist(),
        }

    modes = args_cli.mode or ["dataset_t", "dp_replan"]
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    _configure_eval_camera(env_cfg)
    workspace, policy = _load_policy(
        checkpoint_path,
        str(args_cli.device),
        int(args_cli.num_inference_steps),
        args_cli.diffusion_policy_root,
    )

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    task_env = gym_env.unwrapped
    _configure_eval_camera(env_cfg, task_env)
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(output_dir / "videos"),
            step_trigger=lambda step: step == 0,
            video_length=int(args_cli.video_length),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )

    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    demo_reset_summary: dict[str, Any] | None = None
    try:
        for mode_index, mode in enumerate(modes):
            policy_obs = _reset_env(gym_env, seed=int(args_cli.seed))
            demo_reset_summary = None
            if demo_reset is not None:
                policy_obs, demo_reset_summary = _apply_demo_reset(task_env, demo_reset)
            if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
                raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")
            history = LowdimObsHistory(num_envs=task_env.num_envs, n_obs_steps=int(policy.n_obs_steps))
            nearest_rows: np.ndarray | None = None
            mode_distances: list[float] = []
            mode_cosines: list[float] = []
            mode_first: dict[str, Any] | None = None

            for step in range(int(args_cli.steps)):
                lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()
                if nearest_rows is None:
                    if dataset_start_row is None:
                        nearest_rows = np.asarray(
                            [
                                _nearest_dataset_row(dataset_obs, lowdim[env_idx])[0]
                                for env_idx in range(lowdim.shape[0])
                            ],
                            dtype=np.int64,
                        )
                    else:
                        nearest_rows = np.full(lowdim.shape[0], int(dataset_start_row), dtype=np.int64)
                nearest_distances = [
                    _nearest_dataset_row(dataset_obs, lowdim[env_idx])[1] for env_idx in range(lowdim.shape[0])
                ]
                live_nearest = [
                    _nearest_dataset_row(dataset_obs, lowdim[env_idx])[0] for env_idx in range(lowdim.shape[0])
                ]
                with torch.inference_mode():
                    dp_seq = predict_action_sequence_from_ppo_obs(policy, policy_obs, history, step=step)

                exec_actions = np.zeros((task_env.num_envs, FRANKA_CUBE_ACTION_DIM), dtype=np.float32)
                labels_t = np.zeros_like(exec_actions)
                labels_t1 = np.zeros_like(exec_actions)
                labels_t7 = np.zeros_like(exec_actions)
                for env_idx in range(task_env.num_envs):
                    base = int(nearest_rows[env_idx])
                    row_t = _clipped_row(base + step, episode_ends)
                    labels_t[env_idx] = dataset_action[row_t]
                    labels_t1[env_idx] = dataset_action[_clipped_row(row_t + 1, episode_ends)]
                    labels_t7[env_idx] = dataset_action[_clipped_row(row_t + 7, episode_ends)]
                    if mode == "dataset_t":
                        exec_actions[env_idx] = labels_t[env_idx]
                    elif mode == "dataset_t_plus_1":
                        exec_actions[env_idx] = labels_t1[env_idx]
                    elif mode == "dataset_t_plus_7":
                        exec_actions[env_idx] = labels_t7[env_idx]
                    elif mode == "dataset_open_t":
                        exec_actions[env_idx] = labels_t[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                    elif mode == "dataset_open_t_plus_1":
                        exec_actions[env_idx] = labels_t1[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                    elif mode == "dataset_open_t_plus_7":
                        exec_actions[env_idx] = labels_t7[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                    elif mode == "dp_replan":
                        exec_actions[env_idx] = dp_seq[env_idx, 0]
                    else:
                        raise ValueError(mode)

                clip = float(args_cli.clip_actions)
                if math.isfinite(clip) and clip > 0.0:
                    exec_actions = np.clip(exec_actions, -clip, clip)
                expected_world_delta = normalized_action_to_world_delta(exec_actions)
                before_lowdim = lowdim.copy()
                before_ee_to_cube = np.linalg.norm(before_lowdim[:, 14:17], axis=1)
                policy_obs_next, rewards, terminated, truncated, _info = _policy_obs_from_step(
                    gym_env.step(torch.as_tensor(exec_actions, dtype=torch.float32, device=task_env.device))
                )
                after_lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs_next).detach().float().cpu().numpy()
                after_ee_to_cube = np.linalg.norm(after_lowdim[:, 14:17], axis=1)
                actual_delta = after_lowdim[:, :3] - before_lowdim[:, :3]
                reward_np = rewards.detach().float().cpu().numpy()

                for env_idx in range(task_env.num_envs):
                    nearest_row = int(nearest_rows[env_idx])
                    live_nearest_row = int(live_nearest[env_idx])
                    current_row = _clipped_row(nearest_row + step, episode_ends)
                    phase = phase_names[int(phase_ids[current_row])]
                    live_nearest_phase = phase_names[int(phase_ids[live_nearest_row])]
                    cosine = _cosine(actual_delta[env_idx], expected_world_delta[env_idx, :3])
                    if cosine is not None:
                        mode_cosines.append(float(cosine))
                    mode_distances.append(float(after_ee_to_cube[env_idx]))
                    record = {
                        "mode": mode,
                        "mode_index": mode_index,
                        "step": step,
                        "env_index": env_idx,
                        "demo_reset_applied": demo_reset_summary is not None,
                        "fixed_dataset_start": dataset_start_row is not None,
                        "nearest_initial_row": nearest_row,
                        "dataset_row": current_row,
                        "dataset_episode": _episode_for_row(current_row, episode_ends)[0],
                        "dataset_episode_step": _episode_step(current_row, episode_ends),
                        "dataset_phase": phase,
                        "nearest_live_row": live_nearest_row,
                        "nearest_live_episode_step": _episode_step(live_nearest_row, episode_ends),
                        "nearest_live_phase": live_nearest_phase,
                        "nearest_live_distance": float(nearest_distances[env_idx]),
                        "live_minus_dataset_cube_minus_ee_norm": float(
                            np.linalg.norm(before_lowdim[env_idx, 14:17] - dataset_obs[current_row, 14:17])
                        ),
                        "live_minus_nearest_cube_minus_ee_norm": float(
                            np.linalg.norm(before_lowdim[env_idx, 14:17] - dataset_obs[live_nearest_row, 14:17])
                        ),
                        "ee_to_cube_before": float(before_ee_to_cube[env_idx]),
                        "ee_to_cube_after": float(after_ee_to_cube[env_idx]),
                        "finger_center_to_cube_dist_after": _env_metric_for_env(
                            task_env, "finger_center_to_cube_dist", env_idx
                        ),
                        "left_finger_to_cube_dist_after": _env_metric_for_env(
                            task_env, "left_finger_to_cube_dist", env_idx
                        ),
                        "right_finger_to_cube_dist_after": _env_metric_for_env(
                            task_env, "right_finger_to_cube_dist", env_idx
                        ),
                        "cube_lift_height_after": _env_metric_for_env(task_env, "cube_lift_height", env_idx),
                        "ee_to_cube_delta": float(after_ee_to_cube[env_idx] - before_ee_to_cube[env_idx]),
                        "live_cube_minus_ee_before_x": float(before_lowdim[env_idx, 14]),
                        "live_cube_minus_ee_before_y": float(before_lowdim[env_idx, 15]),
                        "live_cube_minus_ee_before_z": float(before_lowdim[env_idx, 16]),
                        "live_cube_minus_ee_after_x": float(after_lowdim[env_idx, 14]),
                        "live_cube_minus_ee_after_y": float(after_lowdim[env_idx, 15]),
                        "live_cube_minus_ee_after_z": float(after_lowdim[env_idx, 16]),
                        "dataset_cube_minus_ee_x": float(dataset_obs[current_row, 14]),
                        "dataset_cube_minus_ee_y": float(dataset_obs[current_row, 15]),
                        "dataset_cube_minus_ee_z": float(dataset_obs[current_row, 16]),
                        "nearest_live_cube_minus_ee_x": float(dataset_obs[live_nearest_row, 14]),
                        "nearest_live_cube_minus_ee_y": float(dataset_obs[live_nearest_row, 15]),
                        "nearest_live_cube_minus_ee_z": float(dataset_obs[live_nearest_row, 16]),
                        "gripper_width_before": float(before_lowdim[env_idx, 20]),
                        "gripper_width_after": float(after_lowdim[env_idx, 20]),
                        "reward": float(reward_np[env_idx]),
                        "label_t_action": labels_t[env_idx].astype(float).tolist(),
                        "label_t_plus_1_action": labels_t1[env_idx].astype(float).tolist(),
                        "label_t_plus_7_action": labels_t7[env_idx].astype(float).tolist(),
                        "dp_first_action": dp_seq[env_idx, 0].astype(float).tolist(),
                        "executed_action": exec_actions[env_idx].astype(float).tolist(),
                        "expected_world_delta_xyz": expected_world_delta[env_idx, :3].astype(float).tolist(),
                        "actual_world_delta_xyz": actual_delta[env_idx].astype(float).tolist(),
                        "actual_vs_expected_xyz_cosine": cosine,
                        "label_t_gripper": float(labels_t[env_idx, 6]),
                        "dp_first_gripper": float(dp_seq[env_idx, 0, 6]),
                        "executed_gripper": float(exec_actions[env_idx, 6]),
                    }
                    if mode_first is None and env_idx == 0:
                        mode_first = record
                    rows.append(record)

                if args_cli.print_interval > 0 and ((step + 1) % int(args_cli.print_interval) == 0 or step == 0):
                    print(
                        "REPLAY_STEP "
                        + json.dumps(
                            {
                                "mode": mode,
                                "step": step + 1,
                                "ee_to_cube_after_mean": float(np.mean(after_ee_to_cube)),
                                "reward_mean": float(np.mean(reward_np)),
                                "nearest_live_phase_env0": live_nearest_phase,
                                "nearest_live_distance_env0": float(nearest_distances[0]),
                                "exec_action_env0": exec_actions[0].astype(float).tolist(),
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                policy_obs = policy_obs_next
                dones = torch.logical_or(terminated, truncated)
                if dones.any():
                    break

            if mode_first is None:
                continue
            mode_rows = [row for row in rows if row["mode"] == mode]
            first_neg = next((row["step"] for row in mode_rows if row["executed_gripper"] < 0.0), None)
            first_hard = next((row["step"] for row in mode_rows if row["executed_gripper"] <= -0.9), None)
            first_label_neg = next((row["step"] for row in mode_rows if row["label_t_gripper"] < 0.0), None)
            first_label_hard = next((row["step"] for row in mode_rows if row["label_t_gripper"] <= -0.9), None)
            first_nearest_close = next(
                (row["step"] for row in mode_rows if row["nearest_live_phase"] == "close_fingers"), None
            )
            last_row = mode_rows[-1]
            summaries[mode] = {
                "steps": len(mode_rows),
                "initial_nearest_row": int(mode_first["nearest_initial_row"]),
                "initial_dataset_episode": int(mode_first["dataset_episode"]),
                "initial_dataset_episode_step": int(mode_first["dataset_episode_step"]),
                "initial_nearest_phase": str(mode_first["dataset_phase"]),
                "initial_nearest_live_distance": float(mode_first["nearest_live_distance"]),
                "initial_live_minus_dataset_cube_minus_ee_norm": float(
                    mode_first["live_minus_dataset_cube_minus_ee_norm"]
                ),
                "final_ee_to_cube": float(mode_distances[-1]) if mode_distances else float("nan"),
                "min_ee_to_cube": float(np.min(mode_distances)) if mode_distances else float("nan"),
                "final_finger_center_to_cube": float(last_row["finger_center_to_cube_dist_after"]),
                "min_finger_center_to_cube": float(
                    np.min([row["finger_center_to_cube_dist_after"] for row in mode_rows])
                ),
                "final_gripper_width": float(last_row["gripper_width_after"]),
                "final_cube_minus_ee": [
                    float(last_row["live_cube_minus_ee_after_x"]),
                    float(last_row["live_cube_minus_ee_after_y"]),
                    float(last_row["live_cube_minus_ee_after_z"]),
                ],
                "final_nearest_live_row": int(last_row["nearest_live_row"]),
                "final_nearest_live_phase": str(last_row["nearest_live_phase"]),
                "final_nearest_live_distance": float(last_row["nearest_live_distance"]),
                "first_executed_negative_step": first_neg,
                "first_executed_hard_close_step": first_hard,
                "first_label_negative_step": first_label_neg,
                "first_label_hard_close_step": first_label_hard,
                "first_nearest_close_phase_step": first_nearest_close,
                "mean_actual_vs_expected_xyz_cosine": float(np.mean(mode_cosines)) if mode_cosines else float("nan"),
                "first_dp_action": mode_first["dp_first_action"],
                "first_label_action": mode_first["label_t_action"],
                "first_executed_action": mode_first["executed_action"],
                "first_dp_gripper": float(mode_first["dp_first_gripper"]),
                "first_label_gripper": float(mode_first["label_t_gripper"]),
                "first_executed_gripper": float(mode_first["executed_gripper"]),
            }
    finally:
        gym_env.close()

    csv_path = output_dir / "replay_steps.csv"
    json_path = output_dir / "replay_summary.json"
    plot_path = output_dir / "replay_motion.png"
    report_path = output_dir / "replay_report.md"
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)
    bad_modes = [
        mode
        for mode, payload in summaries.items()
        if payload["mean_actual_vs_expected_xyz_cosine"] < 0.25 or not np.isfinite(payload["mean_actual_vs_expected_xyz_cosine"])
    ]
    verdict = (
        "Controller replay did not reliably follow the expected dataset action direction: " + ", ".join(bad_modes)
        if bad_modes
        else "Controller replay follows the expected dataset action direction at this reset; continue debugging policy/live-state semantics."
    )
    summary = {
        "dataset": str(dataset_path),
        "checkpoint": str(checkpoint_path),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "num_inference_steps": int(args_cli.num_inference_steps),
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "num_envs": int(args_cli.num_envs),
        "steps_requested": int(args_cli.steps),
        "modes": summaries,
        "demo_reset": demo_reset_summary,
        "dataset_start": dataset_start_summary
        or {"source": "nearest_live_row", "note": "first live observation selected label start independently per mode"},
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
        "FRANKA_CUBE_DP_DATASET_REPLAY_DONE "
        + json.dumps(
            {
                "output_dir": str(output_dir),
                "report": str(report_path),
                "csv": str(csv_path),
                "plot": str(plot_path),
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
        print(f"FRANKA_CUBE_DP_DATASET_REPLAY_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
