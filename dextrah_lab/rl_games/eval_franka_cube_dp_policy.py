"""Evaluate a lowdim Diffusion Policy checkpoint in the Franka cube env.

This is a no-learning rollout wrapper. It loads an official
``real-stanford/diffusion_policy`` low-dimensional checkpoint, extracts the
compact 21D observation from DEXTRAH's 72D Franka cube observation, queries
the official lowdim policy, and steps the Isaac environment with the resulting
7D relative EE + gripper action. By default it replans every simulator step
for compatibility with the initial smoke path; ``--action_chunk_steps`` can
execute Diffusion Policy action chunks.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", type=str, required=True, help="Official Diffusion Policy .ckpt path.")
parser.add_argument("--diffusion_policy_root", type=str, default=None, help="Path to real-stanford/diffusion_policy.")
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--num_steps", type=int, default=240)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--num_inference_steps", type=int, default=2)
parser.add_argument(
    "--action_chunk_steps",
    type=int,
    default=1,
    help="Number of predicted DP action steps to execute before replanning. Default 1 preserves first-action replanning.",
)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument("--success_window", type=int, default=80)
parser.add_argument("--print_interval", type=int, default=20)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument(
    "--debug_policy_trace_path",
    type=str,
    default=None,
    help="Optional JSON path for lowdim observations and action chunks at policy-call boundaries.",
)
parser.add_argument(
    "--debug_policy_trace_max_calls",
    type=int,
    default=0,
    help="Maximum policy-call trace records to write. Default 0 disables tracing.",
)
parser.add_argument(
    "--debug_policy_trace_env_index",
    type=int,
    default=0,
    help="Environment index to record when --debug_policy_trace_max_calls is positive.",
)
parser.add_argument("--video", action="store_true", default=False, help="Record rollout video.")
parser.add_argument("--video_length", type=int, default=240)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--video_name_prefix", type=str, default="franka-cube-dp-eval")
parser.add_argument("--camera_eye", type=float, nargs=3, default=None)
parser.add_argument("--camera_target", type=float, nargs=3, default=None)
parser.add_argument(
    "--disable_fabric",
    action="store_true",
    default=False,
    help="Disable fabric and use USD I/O operations.",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    LowdimObsHistory,
    extract_lowdim_obs_from_ppo_obs,
    predict_action_sequence_from_ppo_obs,
)


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)


def _mean_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


def _env_metric(task_env: Any, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    return _mean_float(getattr(task_env, name))


def _collect_task_metrics(task_env: Any) -> dict[str, float | None]:
    metric_names = [
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "in_success_region",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "left_finger_to_cube_dist",
        "right_finger_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_distance_asymmetry",
        "gripper_width",
        "finger_table_clearance",
        "finger_table_clearance_violation",
    ]
    return {name: _env_metric(task_env, name) for name in metric_names if hasattr(task_env, name)}


def _stage(name: str, **details: Any) -> None:
    payload = {"stage": name, **details}
    print("DP_EVAL_STAGE " + json.dumps(payload, sort_keys=True, default=str), flush=True)


def _summarize_step_metrics(step_metrics: list[dict[str, float | int | None]]) -> dict[str, dict[str, float | int]]:
    summaries: dict[str, dict[str, float | int]] = {}
    for name in sorted({key for item in step_metrics for key in item.keys()} - {"step"}):
        records = [(item, float(item[name])) for item in step_metrics if item.get(name) is not None]
        if not records:
            continue
        values = [value for _, value in records]
        max_idx = max(range(len(values)), key=lambda idx: values[idx])
        min_idx = min(range(len(values)), key=lambda idx: values[idx])
        summaries[name] = {
            "final": values[-1],
            "max": values[max_idx],
            "max_step": int(records[max_idx][0]["step"]),
            "min": values[min_idx],
            "min_step": int(records[min_idx][0]["step"]),
            "mean": sum(values) / len(values),
        }
    return summaries


def _camera_tuple(values: list[float] | tuple[float, float, float] | None):
    if values is None:
        return None
    return tuple(float(v) for v in values)


def _configure_eval_camera(env_cfg: Any, task_env: Any | None = None) -> None:
    if args_cli.camera_eye is None and args_cli.camera_target is None and not args_cli.video:
        return
    if not hasattr(env_cfg, "viewer"):
        print("[WARN] Environment config has no viewer config; eval camera override skipped.", flush=True)
        return

    eye = _camera_tuple(args_cli.camera_eye) or DEFAULT_CAMERA_EYE
    target = _camera_tuple(args_cli.camera_target) or DEFAULT_CAMERA_TARGET
    if task_env is not None and hasattr(task_env, "scene") and len(task_env.scene.env_origins) > 0:
        env_origin = task_env.scene.env_origins[0].detach().cpu().tolist()
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    print(f"[INFO] DP eval camera eye={eye} target={target}", flush=True)

    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set active viewport camera: {exc}", flush=True)


def _load_policy(checkpoint: Path, device: str, num_inference_steps: int, diffusion_policy_root: str | None):
    if diffusion_policy_root:
        root = str(Path(diffusion_policy_root).expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
        _stage("official_dp_root_added", diffusion_policy_root=root)
    _stage("official_dp_import_start")
    from diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace import (
        TrainDiffusionUnetLowdimWorkspace,
    )

    _stage("official_dp_checkpoint_load_start", checkpoint=str(checkpoint))
    workspace = TrainDiffusionUnetLowdimWorkspace.create_from_checkpoint(str(checkpoint))
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    policy.num_inference_steps = int(num_inference_steps)
    _stage(
        "official_dp_checkpoint_loaded",
        workspace=workspace.__class__.__name__,
        policy=policy.__class__.__name__,
        n_obs_steps=int(policy.n_obs_steps),
        num_inference_steps=int(policy.num_inference_steps),
    )
    _stage("official_dp_policy_to_device_start", device=device)
    policy.to(torch.device(device))
    policy.eval()
    _stage("official_dp_policy_ready", device=device)
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


def _latest_video_files(video_folder: Path | None) -> list[str]:
    if video_folder is None or not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _lowdim_components(lowdim_obs: np.ndarray) -> dict[str, Any]:
    return {
        "ee_pos": lowdim_obs[0:3].astype(float).tolist(),
        "ee_quat": lowdim_obs[3:7].astype(float).tolist(),
        "cube_pos": lowdim_obs[7:10].astype(float).tolist(),
        "cube_quat": lowdim_obs[10:14].astype(float).tolist(),
        "cube_minus_ee": lowdim_obs[14:17].astype(float).tolist(),
        "cube_goal_delta": lowdim_obs[17:20].astype(float).tolist(),
        "gripper_width": float(lowdim_obs[20]),
    }


def _trace_policy_call(
    *,
    trace_records: list[dict[str, Any]],
    max_calls: int,
    step: int,
    env_index: int,
    policy_obs: torch.Tensor,
    history: LowdimObsHistory,
    action_seq: np.ndarray,
    chunk_steps: int,
) -> None:
    if max_calls <= 0 or len(trace_records) >= max_calls:
        return
    env_index = min(max(0, int(env_index)), int(action_seq.shape[0]) - 1)
    lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs)
    lowdim_np = lowdim.detach().float().cpu().numpy()
    action_chunk = np.asarray(action_seq[env_index, :chunk_steps], dtype=np.float32)
    trace_records.append(
        {
            "policy_call_index": len(trace_records),
            "step": int(step),
            "env_index": int(env_index),
            "lowdim_obs": lowdim_np[env_index].astype(float).tolist(),
            "lowdim_components": _lowdim_components(lowdim_np[env_index]),
            "history_after_push": history._history[env_index].astype(float).tolist(),
            "chunk_steps": int(chunk_steps),
            "action_sequence_shape": list(action_seq.shape),
            "action_chunk": action_chunk.astype(float).tolist(),
            "first_action": action_chunk[0].astype(float).tolist(),
            "chunk_gripper_action_min": float(action_chunk[:, 6].min()),
            "chunk_gripper_action_max": float(action_chunk[:, 6].max()),
            "chunk_pose_action_absmax": float(np.max(np.abs(action_chunk[:, :6]))),
        }
    )


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_dp_eval_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    debug_trace_max_calls = max(0, int(args_cli.debug_policy_trace_max_calls))
    debug_trace_path = (
        Path(args_cli.debug_policy_trace_path).expanduser().resolve()
        if args_cli.debug_policy_trace_path
        else (output_dir / "policy_trace.json" if debug_trace_max_calls > 0 else None)
    )
    if debug_trace_path is not None:
        debug_trace_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    checkpoint = Path(args_cli.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    _stage(
        "start",
        output_dir=str(output_dir),
        metrics_path=str(metrics_path),
        checkpoint=str(checkpoint),
        checkpoint_size=checkpoint.stat().st_size,
        num_envs=int(args_cli.num_envs),
        num_steps=int(args_cli.num_steps),
        debug_policy_trace_path=str(debug_trace_path) if debug_trace_path is not None else None,
        debug_policy_trace_max_calls=debug_trace_max_calls,
    )

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    _configure_eval_camera(env_cfg)
    _stage("env_cfg_ready", task=args_cli.task, device=str(args_cli.device), seed=int(args_cli.seed))

    workspace, policy = _load_policy(
        checkpoint,
        str(args_cli.device),
        int(args_cli.num_inference_steps),
        args_cli.diffusion_policy_root,
    )
    n_obs_steps = int(policy.n_obs_steps)

    _stage("gym_make_start", task=args_cli.task)
    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    task_env = gym_env.unwrapped
    _configure_eval_camera(env_cfg, task_env)
    task_num_envs = int(task_env.num_envs)
    _stage("gym_make_done", task=args_cli.task, task_env=task_env.__class__.__name__, num_envs=task_num_envs)

    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=min(args_cli.video_length, args_cli.num_steps),
            name_prefix=args_cli.video_name_prefix,
            disable_logger=True,
        )

    history = LowdimObsHistory(num_envs=task_env.num_envs, n_obs_steps=n_obs_steps)
    requested_action_chunk_steps = max(1, int(args_cli.action_chunk_steps))
    action_queue = np.empty((task_env.num_envs, 0, FRANKA_CUBE_ACTION_DIM), dtype=np.float32)
    step_metrics: list[dict[str, float | int | None]] = []
    policy_trace_records: list[dict[str, Any]] = []
    action_min = np.full(FRANKA_CUBE_ACTION_DIM, np.inf, dtype=np.float64)
    action_max = np.full(FRANKA_CUBE_ACTION_DIM, -np.inf, dtype=np.float64)
    done_count = 0
    env_closed = False
    final_cube_pos_mean: list[float] | list[list[float]] | None = None
    final_gripper_width: float | None = None
    try:
        _stage("env_reset_start")
        policy_obs = _policy_obs_from_reset(gym_env.reset())
        _stage("env_reset_done", policy_obs_shape=tuple(policy_obs.shape))
        if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
            raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")

        _stage("rollout_start", action_chunk_steps=requested_action_chunk_steps)
        for step in range(int(args_cli.num_steps)):
            if not simulation_app.is_running():
                _stage("simulation_app_stopped", step=step)
                break

            with torch.inference_mode():
                if action_queue.shape[1] == 0:
                    action_seq = predict_action_sequence_from_ppo_obs(policy, policy_obs, history)
                    if action_seq.ndim != 3 or action_seq.shape[0] != task_env.num_envs:
                        raise RuntimeError(f"Unexpected DP action sequence shape {action_seq.shape}")
                    chunk_steps = min(requested_action_chunk_steps, int(action_seq.shape[1]))
                    action_queue = np.asarray(action_seq[:, :chunk_steps], dtype=np.float32)
                    _trace_policy_call(
                        trace_records=policy_trace_records,
                        max_calls=debug_trace_max_calls,
                        step=step,
                        env_index=int(args_cli.debug_policy_trace_env_index),
                        policy_obs=policy_obs,
                        history=history,
                        action_seq=action_seq,
                        chunk_steps=chunk_steps,
                    )
                action_np = action_queue[:, 0]
                action_queue = action_queue[:, 1:]
                clip = float(args_cli.clip_actions)
                if math.isfinite(clip) and clip > 0.0:
                    action_np = np.clip(action_np, -clip, clip)
                action_min = np.minimum(action_min, action_np.min(axis=0))
                action_max = np.maximum(action_max, action_np.max(axis=0))
                actions = torch.as_tensor(action_np, dtype=torch.float32, device=task_env.device)
                policy_obs, rewards, terminated, truncated, _ = _policy_obs_from_step(gym_env.step(actions))
                dones = torch.logical_or(terminated, truncated)
                if dones.any():
                    done_env_ids = torch.nonzero(dones, as_tuple=False).view(-1).detach().cpu().numpy()
                    history.reset(done_env_ids)
                    action_queue = np.empty((task_env.num_envs, 0, FRANKA_CUBE_ACTION_DIM), dtype=np.float32)
                    done_count += int(done_env_ids.shape[0])

            reward_mean = _mean_float(rewards)
            task_metrics = _collect_task_metrics(task_env)
            step_record = {
                "step": step + 1,
                "reward_mean": reward_mean,
                **task_metrics,
            }
            step_metrics.append(step_record)
            if args_cli.print_interval > 0 and ((step + 1) % args_cli.print_interval == 0 or step == 0):
                print(
                    "[DP_EVAL] "
                    f"step={step + 1} reward_mean={reward_mean} "
                    f"success_rate={task_metrics.get('in_success_region')} "
                    f"cube_lift_height={task_metrics.get('cube_lift_height')} "
                    f"action_min={action_min.tolist()} action_max={action_max.tolist()}",
                    flush=True,
                )
        final_cube_pos_mean = _tensor_list(task_env.cube_pos.mean(dim=0)) if hasattr(task_env, "cube_pos") else None
        final_gripper_width = _env_metric(task_env, "gripper_width")
    finally:
        _stage("env_close_start")
        gym_env.close()
        env_closed = True
        _stage("env_close_done")

    success_values = [item["in_success_region"] for item in step_metrics if item.get("in_success_region") is not None]
    reward_values = [item["reward_mean"] for item in step_metrics if item.get("reward_mean") is not None]
    window = max(1, min(int(args_cli.success_window), len(success_values)))
    summary = {
        "task": args_cli.task,
        "checkpoint": str(checkpoint),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "ppo_bridge": "predict_action_sequence_from_ppo_obs",
        "action_chunk_steps": requested_action_chunk_steps,
        "no_learning": True,
        "num_envs": task_num_envs,
        "num_steps_requested": int(args_cli.num_steps),
        "steps_completed": len(step_metrics),
        "done_count": done_count,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "final_success_rate": success_values[-1] if success_values else None,
        "window_success_rate": sum(success_values[-window:]) / window if success_values else None,
        "action_min": action_min.astype(float).tolist(),
        "action_max": action_max.astype(float).tolist(),
        "step_metric_summary": _summarize_step_metrics(step_metrics),
        "final_cube_pos_mean": final_cube_pos_mean,
        "final_gripper_width": final_gripper_width,
        "output_dir": str(output_dir),
        "metrics_path": str(metrics_path),
        "debug_policy_trace_path": str(debug_trace_path) if debug_trace_path is not None else None,
        "debug_policy_trace_records": len(policy_trace_records),
        "video_enabled": bool(args_cli.video),
        "video_files": _latest_video_files(video_folder if args_cli.video else None),
        "env_closed": env_closed,
    }
    metrics_path.write_text(
        json.dumps({"summary": summary, "steps": step_metrics}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if debug_trace_path is not None:
        debug_trace_path.write_text(
            json.dumps(
                {
                    "summary": {
                        "task": args_cli.task,
                        "checkpoint": str(checkpoint),
                        "num_envs": task_num_envs,
                        "num_steps_requested": int(args_cli.num_steps),
                        "action_chunk_steps": requested_action_chunk_steps,
                        "num_inference_steps": int(args_cli.num_inference_steps),
                        "env_index": int(args_cli.debug_policy_trace_env_index),
                        "records": len(policy_trace_records),
                    },
                    "policy_calls": policy_trace_records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print("FRANKA_CUBE_DP_POLICY_EVAL_DONE " + json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"FRANKA_CUBE_DP_POLICY_EVAL_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
