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
    choices=["dataset_t", "dataset_t_plus_1", "dataset_t_plus_7", "dp_replan"],
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


def _clipped_row(row_idx: int, episode_ends: np.ndarray) -> int:
    _ep, start, end = _episode_for_row(row_idx, episode_ends)
    return int(np.clip(int(row_idx), start, end - 1))


def _nearest_dataset_row(obs: np.ndarray, query_obs: np.ndarray) -> tuple[int, float]:
    std = np.maximum(obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4)
    dist = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - query_obs[POSITION_FEATURE_IDX]) / std) ** 2).mean(axis=1))
    idx = int(np.argmin(dist))
    return idx, float(dist[idx])


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
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, constrained_layout=True)
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode and int(row["env_index"]) == 0]
        x = [row["step"] for row in mode_rows]
        axes[0].plot(x, [row["ee_to_cube_after"] for row in mode_rows], marker="o", label=mode)
        axes[1].plot(x, [row["gripper_width_after"] for row in mode_rows], marker="o", label=mode)
        axes[2].plot(x, [row["actual_vs_expected_xyz_cosine"] for row in mode_rows], marker="o", label=mode)
    axes[0].set_title("EE To Cube Distance After Step")
    axes[0].set_ylabel("m")
    axes[1].set_title("Gripper Width After Step")
    axes[1].set_ylabel("m")
    axes[2].set_title("Actual EE Delta vs Expected Action World Delta")
    axes[2].set_ylabel("cosine")
    axes[2].set_xlabel("replay step")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube DP Dataset-Action Replay",
        "",
        "This is a bounded Isaac controller replay. It does not train. Each mode resets the env, finds the nearest converted cuRobo demo row to the live lowdim observation, compares official-DP prediction against dataset labels, and executes a short sequence.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Mode Summary",
        "",
        "| mode | steps | nearest row | nearest phase | final EE-cube | min EE-cube | mean delta cosine | first DP grip | first label grip |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for mode, payload in summary["modes"].items():
        lines.append(
            f"| {mode} | {payload['steps']} | {payload['initial_nearest_row']} | {payload['initial_nearest_phase']} | "
            f"{payload['final_ee_to_cube']:.4f} | {payload['min_ee_to_cube']:.4f} | "
            f"{payload['mean_actual_vs_expected_xyz_cosine']:.4f} | {payload['first_dp_gripper']:.3f} | "
            f"{payload['first_label_gripper']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- CSV: `{summary['csv']}`",
            f"- JSON: `{summary['json']}`",
            f"- Plot: `{summary['plot']}`",
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
    try:
        for mode_index, mode in enumerate(modes):
            policy_obs = _reset_env(gym_env, seed=int(args_cli.seed))
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
                    nearest_rows = np.asarray(
                        [_nearest_dataset_row(dataset_obs, lowdim[env_idx])[0] for env_idx in range(lowdim.shape[0])],
                        dtype=np.int64,
                    )
                nearest_distances = [
                    _nearest_dataset_row(dataset_obs, lowdim[env_idx])[1] for env_idx in range(lowdim.shape[0])
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
                    current_row = _clipped_row(nearest_row + step, episode_ends)
                    phase = phase_names[int(phase_ids[current_row])]
                    cosine = _cosine(actual_delta[env_idx], expected_world_delta[env_idx, :3])
                    if cosine is not None:
                        mode_cosines.append(float(cosine))
                    mode_distances.append(float(after_ee_to_cube[env_idx]))
                    record = {
                        "mode": mode,
                        "mode_index": mode_index,
                        "step": step,
                        "env_index": env_idx,
                        "nearest_initial_row": nearest_row,
                        "dataset_row": current_row,
                        "dataset_phase": phase,
                        "nearest_live_distance": float(nearest_distances[env_idx]),
                        "ee_to_cube_before": float(before_ee_to_cube[env_idx]),
                        "ee_to_cube_after": float(after_ee_to_cube[env_idx]),
                        "ee_to_cube_delta": float(after_ee_to_cube[env_idx] - before_ee_to_cube[env_idx]),
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
            summaries[mode] = {
                "steps": len([row for row in rows if row["mode"] == mode]),
                "initial_nearest_row": int(mode_first["nearest_initial_row"]),
                "initial_nearest_phase": str(mode_first["dataset_phase"]),
                "initial_nearest_live_distance": float(mode_first["nearest_live_distance"]),
                "final_ee_to_cube": float(mode_distances[-1]) if mode_distances else float("nan"),
                "min_ee_to_cube": float(np.min(mode_distances)) if mode_distances else float("nan"),
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
        "verdict": verdict,
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "report": str(report_path),
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
