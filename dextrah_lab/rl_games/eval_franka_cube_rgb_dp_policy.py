"""Evaluate an RGB Diffusion Policy checkpoint in the Franka cube env.

The policy observation is image + robot proprioception only. Low-dimensional
cube state may be used for an eval reset target, but it is not passed to the
policy.
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
parser.add_argument("--checkpoint", type=str, required=True)
parser.add_argument("--diffusion_policy_root", type=str, default=None)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--num_steps", type=int, default=320)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--num_inference_steps", type=int, default=100)
parser.add_argument("--num_action_samples", type=int, default=1)
parser.add_argument("--policy_sample_seed", type=int, default=None)
parser.add_argument("--action_chunk_steps", type=int, default=8)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument("--success_window", type=int, default=80)
parser.add_argument("--success_timeout_override", type=float, default=None)
parser.add_argument(
    "--stop_on_done",
    action="store_true",
    default=False,
    help="Stop the one-env trace on the first done instead of continuing after the Gymnasium auto-reset.",
)
parser.add_argument("--print_interval", type=int, default=20)
parser.add_argument("--image_height", type=int, default=96)
parser.add_argument("--image_width", type=int, default=96)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--demo_reset_dataset", type=str, default=None)
parser.add_argument("--demo_reset_episode", type=int, default=0)
parser.add_argument("--demo_reset_step", type=int, default=0)
parser.add_argument("--demo_reset_cube_pos_blend_alpha", type=float, default=1.0)
parser.add_argument(
    "--append_phase_progress",
    action="store_true",
    default=False,
    help="Append non-privileged contact phase one-hot plus episode progress to robot_state.",
)
parser.add_argument(
    "--phase_progress_dataset",
    type=str,
    default=None,
    help="RGB NPZ with phase_ids/episode_ends used as the runtime phase/progress schedule.",
)
parser.add_argument("--phase_progress_episode", type=int, default=0)
parser.add_argument("--phase_progress_start_step", type=int, default=0)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=320)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--video_name_prefix", type=str, default="franka-cube-rgb-dp-eval")
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.10, -0.78, 1.42))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.10, 0.82))
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

# RGB policy inference always needs camera rendering, even without recording.
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
    FRANKA_CUBE_LOWDIM_OBS_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    extract_lowdim_obs_from_ppo_obs,
)

ACTION_NAMES = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]


def _stage(name: str, **details: Any) -> None:
    print("RGB_DP_EVAL_STAGE " + json.dumps({"stage": name, **details}, sort_keys=True, default=str), flush=True)


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
    names = [
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
    return {name: _env_metric(task_env, name) for name in names if hasattr(task_env, name)}


def _json_metric_dict(metrics: dict[str, float | int | None]) -> dict[str, float | int | None]:
    out: dict[str, float | int | None] = {}
    for key, value in metrics.items():
        if value is None:
            out[key] = None
        elif isinstance(value, (int, np.integer)):
            out[key] = int(value)
        else:
            out[key] = float(value)
    return out


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


def _reset_policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _contact_phase_progress_features(phase_id: int, progress: float) -> np.ndarray:
    phase = int(phase_id)
    if phase < 0:
        phase = 0
    if phase not in (0, 1, 2):
        raise ValueError(f"Expected contact phase id in {{-1,0,1,2}}, got {phase_id}")
    out = np.zeros((4,), dtype=np.float32)
    out[phase] = 1.0
    out[3] = float(np.clip(float(progress), 0.0, 1.0))
    return out


class RgbPhaseProgressProvider:
    def __init__(self, path: Path, episode: int, start_step: int):
        self.path = path
        data = np.load(path, allow_pickle=False)
        if "phase_ids" not in data.files:
            raise KeyError(f"{path} missing phase_ids required for --append_phase_progress")
        if "episode_ends" not in data.files:
            raise KeyError(f"{path} missing episode_ends required for --append_phase_progress")
        self.phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
        self.episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
        if self.episode_ends.ndim != 1 or self.episode_ends.size == 0:
            raise ValueError(f"{path}: episode_ends must be nonempty 1D")
        if self.phase_ids.shape != (int(self.episode_ends[-1]),):
            raise ValueError(
                f"{path}: phase_ids shape {self.phase_ids.shape} does not match episode_ends[-1]={self.episode_ends[-1]}"
            )
        unique = set(int(v) for v in np.unique(self.phase_ids))
        if not unique.issubset({-1, 0, 1, 2}):
            raise ValueError(f"{path}: expected contact phase ids in {{-1,0,1,2}}, got {sorted(unique)}")
        self.episode = int(np.clip(int(episode), 0, int(self.episode_ends.size - 1)))
        self.episode_start = 0 if self.episode == 0 else int(self.episode_ends[self.episode - 1])
        self.episode_end = int(self.episode_ends[self.episode])
        self.episode_length = max(1, self.episode_end - self.episode_start)
        self.start_step = int(np.clip(int(start_step), 0, self.episode_length - 1))

    def feature_at(self, rollout_step: int) -> np.ndarray:
        local_step = min(self.start_step + int(rollout_step), self.episode_length - 1)
        row = self.episode_start + local_step
        denom = max(1, self.episode_length - 1)
        progress = float(local_step) / float(denom)
        return _contact_phase_progress_features(int(self.phase_ids[row]), progress)

    def summary(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "episode": int(self.episode),
            "episode_start": int(self.episode_start),
            "episode_end": int(self.episode_end),
            "episode_length": int(self.episode_length),
            "start_step": int(self.start_step),
            "feature_names": ["phase_align_open", "phase_close_hold", "phase_lift", "episode_progress"],
        }


def _robot_state_from_policy_obs(policy_obs: torch.Tensor, phase_features: np.ndarray | None = None) -> np.ndarray:
    lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs)
    lowdim_np = lowdim.detach().float().cpu().numpy()
    if lowdim_np.ndim != 2 or lowdim_np.shape[0] != 1:
        raise ValueError(f"RGB eval currently supports num_envs=1, got lowdim shape {lowdim_np.shape}")
    one = lowdim_np[0]
    robot_state = np.concatenate((one[:7], one[20:21]), axis=0).astype(np.float32)
    if phase_features is not None:
        robot_state = np.concatenate((robot_state, np.asarray(phase_features, dtype=np.float32)), axis=0)
    return robot_state.astype(np.float32)


def _resize_rgb_nearest(frame: np.ndarray, height: int, width: int) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[-1] < 3:
        raise ValueError(f"Expected RGB/RGBA frame with shape (H,W,3/4), got {frame.shape}")
    rgb = np.asarray(frame[..., :3])
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    h, w = rgb.shape[:2]
    side = min(h, w)
    y0 = max(0, (h - side) // 2)
    x0 = max(0, (w - side) // 2)
    crop = rgb[y0 : y0 + side, x0 : x0 + side]
    ys = np.linspace(0, side - 1, int(height)).astype(np.int64)
    xs = np.linspace(0, side - 1, int(width)).astype(np.int64)
    return crop[ys][:, xs].copy()


def _render_rgb_obs(gym_env: Any) -> np.ndarray:
    frame = gym_env.render()
    if isinstance(frame, list):
        if not frame:
            raise RuntimeError("gym_env.render() returned an empty frame list")
        frame = frame[-1]
    return _resize_rgb_nearest(np.asarray(frame), int(args_cli.image_height), int(args_cli.image_width))


class ImageRobotObsHistory:
    def __init__(self, n_obs_steps: int, height: int, width: int, robot_state_dim: int = 8):
        self.n_obs_steps = int(n_obs_steps)
        self.height = int(height)
        self.width = int(width)
        self.robot_state_dim = int(robot_state_dim)
        self.image = np.zeros((self.n_obs_steps, self.height, self.width, 3), dtype=np.uint8)
        self.robot_state = np.zeros((self.n_obs_steps, self.robot_state_dim), dtype=np.float32)
        self.initialized = False

    def reset(self, image: np.ndarray, robot_state: np.ndarray) -> None:
        if robot_state.shape != (self.robot_state_dim,):
            raise ValueError(f"Expected robot_state shape ({self.robot_state_dim},), got {robot_state.shape}")
        self.image[:] = image[None, ...]
        self.robot_state[:] = robot_state[None, ...]
        self.initialized = True

    def push(self, image: np.ndarray, robot_state: np.ndarray) -> None:
        if not self.initialized:
            self.reset(image, robot_state)
            return
        self.image[:-1] = self.image[1:]
        self.image[-1] = image
        self.robot_state[:-1] = self.robot_state[1:]
        self.robot_state[-1] = robot_state

    def as_policy_obs(self, device: torch.device) -> dict[str, torch.Tensor]:
        image = np.moveaxis(self.image.astype(np.float32) / 255.0, -1, 1)
        return {
            "image": torch.as_tensor(image[None], dtype=torch.float32, device=device),
            "robot_state": torch.as_tensor(self.robot_state[None], dtype=torch.float32, device=device),
        }


def _row_for_episode_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> tuple[int, int, int, int]:
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    local_step = int(np.clip(int(episode_step), 0, max(0, end - start - 1)))
    return int(start + local_step), episode_idx, start, end


def _load_demo_reset(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = np.load(path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    row, episode_idx, start, end = _row_for_episode_step(
        episode_ends,
        int(args_cli.demo_reset_episode),
        int(args_cli.demo_reset_step),
    )
    return {
        "path": str(path),
        "obs": obs,
        "episode_ends": episode_ends,
        "row": row,
        "episode": episode_idx,
        "episode_start": start,
        "episode_end": end,
        "episode_step": row - start,
        "target_obs": obs[row].copy(),
    }


def _apply_demo_cube_reset(task_env: Any, demo_reset: dict[str, Any]) -> tuple[torch.Tensor, dict[str, Any]]:
    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    num_ids = int(env_ids.numel())
    target_obs_base = np.asarray(demo_reset["target_obs"], dtype=np.float32)[:FRANKA_CUBE_LOWDIM_OBS_DIM]
    alpha = float(np.clip(float(args_cli.demo_reset_cube_pos_blend_alpha), 0.0, 1.0))

    normal_policy_obs = _reset_policy_obs_from_task_env(task_env)
    normal_lowdim = extract_lowdim_obs_from_ppo_obs(normal_policy_obs).detach().float().cpu().numpy()
    normal0 = normal_lowdim[0]
    source_cube_pos = torch.as_tensor(target_obs_base[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    source_cube_quat = torch.as_tensor(target_obs_base[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    normal_cube_pos = torch.as_tensor(normal_lowdim[:, 7:10], dtype=torch.float32, device=task_env.device)
    normal_cube_quat = torch.as_tensor(normal_lowdim[:, 10:14], dtype=torch.float32, device=task_env.device)
    target_cube_pos = normal_cube_pos + alpha * (source_cube_pos - normal_cube_pos)
    quat_dot = torch.sum(normal_cube_quat * source_cube_quat, dim=1, keepdim=True)
    source_cube_quat = torch.where(quat_dot < 0.0, -source_cube_quat, source_cube_quat)
    target_cube_quat = torch.nn.functional.normalize(normal_cube_quat + alpha * (source_cube_quat - normal_cube_quat), dim=1)

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

    policy_obs = _reset_policy_obs_from_task_env(task_env)
    live_lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()
    live0 = live_lowdim[0]
    diff = live0 - target_obs_base
    return policy_obs, {
        "dataset": str(demo_reset["path"]),
        "episode": int(demo_reset["episode"]),
        "episode_step": int(demo_reset["episode_step"]),
        "row": int(demo_reset["row"]),
        "cube_pos_blend_alpha": alpha,
        "normal_cube_pos_before_reset_env0": normal0[7:10].astype(float).tolist(),
        "target_cube_pos": target_obs_base[7:10].astype(float).tolist(),
        "target_cube_quat": target_obs_base[10:14].astype(float).tolist(),
        "applied_cube_pos_env0": target_cube_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
        "applied_cube_quat_env0": target_cube_quat[0].detach().float().cpu().numpy().astype(float).tolist(),
        "live_lowdim_after_reset_env0": live0.astype(float).tolist(),
        "lowdim_linf_diff_env0": float(np.max(np.abs(diff))),
        "cube_pos_l2_diff_env0": float(np.linalg.norm(diff[7:10])),
        "cube_pos_l2_from_normal_env0": float(np.linalg.norm(live0[7:10] - normal0[7:10])),
    }


def _configure_camera(env_cfg: Any, task_env: Any | None = None) -> None:
    if hasattr(env_cfg, "viewer"):
        env_cfg.viewer.eye = tuple(float(v) for v in args_cli.camera_eye)
        env_cfg.viewer.lookat = tuple(float(v) for v in args_cli.camera_target)
        env_cfg.viewer.origin_type = "world"
    if task_env is not None and hasattr(task_env, "sim") and hasattr(env_cfg, "viewer"):
        try:
            task_env.sim.set_camera_view(
                eye=tuple(float(v) for v in args_cli.camera_eye),
                target=tuple(float(v) for v in args_cli.camera_target),
                camera_prim_path=env_cfg.viewer.cam_prim_path,
            )
        except Exception as exc:
            print(f"[WARN] Could not set RGB eval camera: {exc}", flush=True)


def _latest_video_files(video_folder: Path | None) -> list[str]:
    if video_folder is None or not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _load_policy(checkpoint: Path, device: str, diffusion_policy_root: str | None):
    if diffusion_policy_root:
        root = str(Path(diffusion_policy_root).expanduser().resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
        _stage("official_dp_root_added", diffusion_policy_root=root)
    from diffusion_policy.workspace.train_diffusion_unet_image_workspace import TrainDiffusionUnetImageWorkspace

    _stage("official_dp_checkpoint_load_start", checkpoint=str(checkpoint))
    workspace = TrainDiffusionUnetImageWorkspace.create_from_checkpoint(str(checkpoint))
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    policy.num_inference_steps = int(args_cli.num_inference_steps)
    policy.to(torch.device(device))
    policy.eval()
    _stage(
        "official_dp_policy_ready",
        workspace=workspace.__class__.__name__,
        policy=policy.__class__.__name__,
        n_obs_steps=int(policy.n_obs_steps),
        num_inference_steps=int(policy.num_inference_steps),
        device=device,
    )
    return workspace, policy


def _predict_action_sequence(policy: Any, history: ImageRobotObsHistory, call_idx: int) -> np.ndarray:
    device = next(policy.parameters()).device
    sample_count = max(1, int(args_cli.num_action_samples))
    samples = []
    with torch.inference_mode():
        for sample_idx in range(sample_count):
            if args_cli.policy_sample_seed is not None:
                seed = int(args_cli.policy_sample_seed) + call_idx * sample_count + sample_idx
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
            result = policy.predict_action(history.as_policy_obs(device))
            samples.append(result["action"])
        action = samples[0] if len(samples) == 1 else torch.stack(samples, dim=0).mean(dim=0)
    return action.detach().cpu().numpy()


def main() -> None:
    if int(args_cli.num_envs) != 1:
        raise ValueError("RGB eval currently supports --num_envs 1")
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_rgb_dp_eval_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"
    checkpoint = Path(args_cli.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    demo_reset_path = Path(args_cli.demo_reset_dataset).expanduser().resolve() if args_cli.demo_reset_dataset else None
    if demo_reset_path is not None and not demo_reset_path.is_file():
        raise FileNotFoundError(demo_reset_path)
    demo_reset = _load_demo_reset(demo_reset_path)

    _stage(
        "start",
        output_dir=str(output_dir),
        metrics_path=str(metrics_path),
        checkpoint=str(checkpoint),
        demo_reset_dataset=str(demo_reset_path) if demo_reset_path else None,
        append_phase_progress=bool(args_cli.append_phase_progress),
        phase_progress_dataset=str(args_cli.phase_progress_dataset) if args_cli.phase_progress_dataset else None,
        phase_progress_episode=int(args_cli.phase_progress_episode),
        phase_progress_start_step=int(args_cli.phase_progress_start_step),
        num_action_samples=int(args_cli.num_action_samples),
        policy_sample_seed=args_cli.policy_sample_seed,
        action_chunk_steps=int(args_cli.action_chunk_steps),
        image_shape=[int(args_cli.image_height), int(args_cli.image_width), 3],
    )

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    success_timeout_override = None
    if args_cli.success_timeout_override is not None:
        original = float(env_cfg.success_timeout)
        env_cfg.success_timeout = float(args_cli.success_timeout_override)
        success_timeout_override = {"original": original, "override": float(env_cfg.success_timeout)}
    _configure_camera(env_cfg)

    workspace, policy = _load_policy(checkpoint, str(args_cli.device), args_cli.diffusion_policy_root)
    phase_provider = None
    if args_cli.append_phase_progress:
        if not args_cli.phase_progress_dataset:
            raise ValueError("--append_phase_progress requires --phase_progress_dataset")
        phase_path = Path(args_cli.phase_progress_dataset).expanduser().resolve()
        if not phase_path.is_file():
            raise FileNotFoundError(phase_path)
        phase_provider = RgbPhaseProgressProvider(
            phase_path,
            episode=int(args_cli.phase_progress_episode),
            start_step=int(args_cli.phase_progress_start_step),
        )
        _stage("phase_progress_provider_loaded", **phase_provider.summary())
    robot_state_dim = 8 + (4 if phase_provider is not None else 0)
    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = gym_env.unwrapped
    _configure_camera(env_cfg, task_env)
    if args_cli.video:
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(video_folder),
            step_trigger=lambda step: step == 0,
            video_length=min(int(args_cli.video_length), int(args_cli.num_steps)),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )

    step_metrics: list[dict[str, float | int | None]] = []
    action_trace: list[dict[str, Any]] = []
    action_min = np.full(7, np.inf, dtype=np.float64)
    action_max = np.full(7, -np.inf, dtype=np.float64)
    action_queue = np.empty((1, 0, 7), dtype=np.float32)
    action_queue_policy_call_idx = -1
    action_queue_step_offset = 0
    done_count = 0
    first_done: dict[str, Any] | None = None
    env_closed = False
    demo_reset_summary: dict[str, Any] | None = None
    final_cube_pos_mean = None
    final_gripper_width = None
    policy_call_idx = 0
    try:
        policy_obs = _policy_obs_from_reset(gym_env.reset())
        if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
            raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")
        if demo_reset is not None:
            policy_obs, demo_reset_summary = _apply_demo_cube_reset(task_env, demo_reset)
            _stage("demo_reset_apply_done", **demo_reset_summary)

        # Warm renderer once, then initialize the policy history from current state.
        _render_rgb_obs(gym_env)
        history = ImageRobotObsHistory(
            n_obs_steps=int(policy.n_obs_steps),
            height=int(args_cli.image_height),
            width=int(args_cli.image_width),
            robot_state_dim=robot_state_dim,
        )
        history.reset(
            _render_rgb_obs(gym_env),
            _robot_state_from_policy_obs(
                policy_obs,
                None if phase_provider is None else phase_provider.feature_at(0),
            ),
        )
        chunk_steps_requested = max(1, int(args_cli.action_chunk_steps))

        for step in range(int(args_cli.num_steps)):
            if not simulation_app.is_running():
                break
            pre_step_metrics = _collect_task_metrics(task_env)
            pre_step_cube_pos_mean = _tensor_list(task_env.cube_pos.mean(dim=0)) if hasattr(task_env, "cube_pos") else None
            new_policy_call = False
            if action_queue.shape[1] == 0:
                action_queue_policy_call_idx = policy_call_idx
                action_queue_step_offset = 0
                action_seq = _predict_action_sequence(policy, history, policy_call_idx)
                policy_call_idx += 1
                new_policy_call = True
                if action_seq.ndim != 3 or action_seq.shape[0] != 1:
                    raise RuntimeError(f"Unexpected RGB DP action sequence shape {action_seq.shape}")
                chunk_steps = min(chunk_steps_requested, int(action_seq.shape[1]))
                action_queue = np.asarray(action_seq[:, :chunk_steps], dtype=np.float32)
            raw_action_np = action_queue[:, 0].copy()
            queue_step_offset = int(action_queue_step_offset)
            action_np = raw_action_np.copy()
            action_queue = action_queue[:, 1:]
            action_queue_step_offset += 1
            clip = float(args_cli.clip_actions)
            if math.isfinite(clip) and clip > 0.0:
                action_np = np.clip(action_np, -clip, clip)
            action_min = np.minimum(action_min, action_np.min(axis=0))
            action_max = np.maximum(action_max, action_np.max(axis=0))
            action_trace.append(
                {
                    "step": step + 1,
                    "policy_call_index": int(action_queue_policy_call_idx),
                    "queue_step_offset": queue_step_offset,
                    "new_policy_call": bool(new_policy_call),
                    "raw_action": raw_action_np.reshape(-1).astype(float).tolist(),
                    "applied_action": action_np.reshape(-1).astype(float).tolist(),
                }
            )
            actions = torch.as_tensor(action_np, dtype=torch.float32, device=task_env.device)
            policy_obs, rewards, terminated, truncated, _ = _policy_obs_from_step(gym_env.step(actions))
            dones = torch.logical_or(terminated, truncated)
            done_now = bool(dones.any())
            if dones.any():
                done_count += int(torch.count_nonzero(dones).detach().cpu())
                action_queue = np.empty((1, 0, 7), dtype=np.float32)
                if first_done is None:
                    first_done = {
                        "step": int(step + 1),
                        "terminated": bool(terminated.detach().bool().any().cpu()),
                        "truncated": bool(truncated.detach().bool().any().cpu()),
                        "reward_mean": _mean_float(rewards),
                        "pre_step_metrics": _json_metric_dict(pre_step_metrics),
                        "pre_step_cube_pos_mean": pre_step_cube_pos_mean,
                        "previous_record": _json_metric_dict(step_metrics[-1]) if step_metrics else None,
                    }
                if args_cli.stop_on_done:
                    break

            next_image = _render_rgb_obs(gym_env)
            next_robot_state = _robot_state_from_policy_obs(
                policy_obs,
                None if phase_provider is None else phase_provider.feature_at(step + 1),
            )
            if dones.any():
                history.reset(next_image, next_robot_state)
            else:
                history.push(next_image, next_robot_state)

            reward_mean = _mean_float(rewards)
            task_metrics = _collect_task_metrics(task_env)
            record = {
                "step": step + 1,
                "reward_mean": reward_mean,
                "done": float(done_now),
                "terminated": float(bool(terminated.detach().bool().any().cpu())),
                "truncated": float(bool(truncated.detach().bool().any().cpu())),
                **task_metrics,
            }
            step_metrics.append(record)
            if args_cli.print_interval > 0 and ((step + 1) % int(args_cli.print_interval) == 0 or step == 0):
                print(
                    "[RGB_DP_EVAL] "
                    f"step={step + 1} reward_mean={reward_mean} "
                    f"success_rate={task_metrics.get('in_success_region')} "
                    f"cube_lift_height={task_metrics.get('cube_lift_height')} "
                    f"action_min={action_min.tolist()} action_max={action_max.tolist()}",
                    flush=True,
                )
        if first_done is not None and args_cli.stop_on_done:
            final_cube_pos_mean = first_done.get("pre_step_cube_pos_mean")
            final_gripper_width = first_done.get("pre_step_metrics", {}).get("gripper_width")
        else:
            final_cube_pos_mean = _tensor_list(task_env.cube_pos.mean(dim=0)) if hasattr(task_env, "cube_pos") else None
            final_gripper_width = _env_metric(task_env, "gripper_width")
    finally:
        gym_env.close()
        env_closed = True

    success_values = [item["in_success_region"] for item in step_metrics if item.get("in_success_region") is not None]
    reward_values = [item["reward_mean"] for item in step_metrics if item.get("reward_mean") is not None]
    window = max(1, min(int(args_cli.success_window), len(success_values)))
    summary = {
        "task": args_cli.task,
        "checkpoint": str(checkpoint),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "obs_schema": {
            "image": [3, int(args_cli.image_height), int(args_cli.image_width)],
            "robot_state": int(robot_state_dim),
        },
        "privileged_object_state_in_policy": False,
        "phase_progress_provider": None if phase_provider is None else phase_provider.summary(),
        "num_action_samples": int(args_cli.num_action_samples),
        "policy_sample_seed": args_cli.policy_sample_seed,
        "action_chunk_steps": max(1, int(args_cli.action_chunk_steps)),
        "num_envs": 1,
        "num_steps_requested": int(args_cli.num_steps),
        "steps_completed": len(step_metrics),
        "actions_completed": len(action_trace),
        "done_count": done_count,
        "stop_on_done": bool(args_cli.stop_on_done),
        "stopped_on_done": bool(first_done is not None and args_cli.stop_on_done),
        "stop_reason": "done" if first_done is not None and args_cli.stop_on_done else "num_steps",
        "first_done": first_done,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "final_success_rate": success_values[-1] if success_values else None,
        "window_success_rate": sum(success_values[-window:]) / window if success_values else None,
        "success_timeout_override": success_timeout_override,
        "action_names": ACTION_NAMES,
        "action_trace_format": {
            "raw_action": "Policy output before eval clipping, one 7D action for env0.",
            "applied_action": "Action after eval clipping, sent directly to the environment.",
            "policy_call_index": "Zero-based predict_action call that produced this action.",
            "queue_step_offset": "Index within the queued action chunk from that predict_action call.",
        },
        "action_min": action_min.astype(float).tolist(),
        "action_max": action_max.astype(float).tolist(),
        "step_metric_summary": _summarize_step_metrics(step_metrics),
        "final_cube_pos_mean": final_cube_pos_mean,
        "final_gripper_width": final_gripper_width,
        "demo_reset": demo_reset_summary,
        "video_enabled": bool(args_cli.video),
        "video_files": _latest_video_files(video_folder if args_cli.video else None),
        "env_closed": env_closed,
        "output_dir": str(output_dir),
        "metrics_path": str(metrics_path),
    }
    metrics_path.write_text(
        json.dumps({"summary": summary, "steps": step_metrics, "action_trace": action_trace}, indent=2, sort_keys=True)
        + "\n"
    )
    print("FRANKA_CUBE_RGB_DP_POLICY_EVAL_DONE " + json.dumps(summary, sort_keys=True, default=str), flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        print(f"FRANKA_CUBE_RGB_DP_POLICY_EVAL_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
