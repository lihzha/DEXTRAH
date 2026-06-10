# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Evaluate an RL-Games checkpoint and optionally record a rollout video."""

import argparse
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Evaluate an RL-Games checkpoint.")
parser.add_argument("--video", action="store_true", default=False, help="Record a rollout video.")
parser.add_argument("--video_length", type=int, default=600, help="Length of the recorded video in steps.")
parser.add_argument("--video_folder", type=str, default=None, help="Directory for rollout videos.")
parser.add_argument("--video_name_prefix", type=str, default="cube-grasp-eval", help="Prefix for rollout video files.")
parser.add_argument("--camera_eye", type=float, nargs=3, default=None, help="Viewport camera eye for video eval.")
parser.add_argument("--camera_target", type=float, nargs=3, default=None, help="Viewport camera target for video eval.")
parser.add_argument("--num_steps", type=int, default=600, help="Number of policy steps to run.")
parser.add_argument("--success_window", type=int, default=100, help="Trailing window for final success-rate average.")
parser.add_argument("--print_interval", type=int, default=20, help="Print metrics every N steps.")
parser.add_argument("--output_dir", type=str, default=None, help="Directory for eval outputs.")
parser.add_argument("--metrics_path", type=str, default=None, help="Path to write metrics JSON.")
parser.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True, help="Use deterministic actions.")
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment.")
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
parser.add_argument("--num_envs", type=int, default=None, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--checkpoint", type=str, default=None, help="Path to model checkpoint.")
parser.add_argument(
    "--use_last_checkpoint",
    action="store_true",
    help="When no checkpoint is provided, use the last saved model instead of the best saved model.",
)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

if args_cli.video:
    args_cli.enable_cameras = True

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

from rl_games.common import env_configurations, vecenv
from rl_games.common.player import BasePlayer
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import get_checkpoint_path, parse_env_cfg
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401


def _mean_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _env_metric(task_env, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    return _mean_float(getattr(task_env, name))


def _collect_task_metrics(task_env) -> dict[str, float | None]:
    metric_names = [
        "cube_lift_height",
        "cube_xy_error",
        "hand_to_cube_mean_dist",
        "star_lift_height",
        "goal_xy_error",
        "goal_height_error",
        "goal_yaw_error",
        "ee_to_star_dist",
        "finger_center_to_star_dist",
        "gripper_width",
    ]
    return {name: _env_metric(task_env, name) for name in metric_names if hasattr(task_env, name)}


def _checkpoint_path(agent_cfg: dict) -> str:
    log_root_path = os.path.abspath(os.path.join("logs", "rl_games", agent_cfg["params"]["config"]["name"]))
    print(f"[INFO] Loading experiment from directory: {log_root_path}")
    if args_cli.checkpoint is not None:
        return retrieve_file_path(args_cli.checkpoint)

    run_dir = agent_cfg["params"]["config"].get("full_experiment_name", ".*")
    checkpoint_file = ".*" if args_cli.use_last_checkpoint else f"{agent_cfg['params']['config']['name']}.pth"
    return get_checkpoint_path(log_root_path, run_dir, checkpoint_file, other_dirs=["nn"])


def _latest_video_files(video_folder: Path | None) -> list[str]:
    if video_folder is None or not video_folder.exists():
        return []
    return [str(path) for path in sorted(video_folder.glob("*.mp4"))]


def _camera_tuple(values: list[float] | tuple[float, float, float] | None):
    if values is None:
        return None
    return tuple(float(v) for v in values)


def _configure_eval_camera(env_cfg, task_env=None) -> None:
    if args_cli.camera_eye is None and args_cli.camera_target is None:
        return
    if not hasattr(env_cfg, "viewer"):
        print("[WARN] Environment config has no viewer config; eval camera override skipped.")
        return

    eye = _camera_tuple(args_cli.camera_eye) or tuple(env_cfg.viewer.eye)
    target = _camera_tuple(args_cli.camera_target) or tuple(env_cfg.viewer.lookat)
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    print(f"[INFO] Eval video camera eye={eye} target={target}")

    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set active viewport camera: {exc}")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    """Run checkpoint evaluation."""

    output_dir = Path(args_cli.output_dir or datetime.now().strftime("eval_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    env_cfg.scene.num_envs = args_cli.num_envs if args_cli.num_envs is not None else env_cfg.scene.num_envs
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    if args_cli.seed is not None:
        env_cfg.seed = args_cli.seed
        agent_cfg["params"]["seed"] = args_cli.seed
    _configure_eval_camera(env_cfg)

    resume_path = _checkpoint_path(agent_cfg)
    agent_cfg["params"]["load_checkpoint"] = True
    agent_cfg["params"]["load_path"] = resume_path
    print(f"[INFO]: Loading model checkpoint from: {agent_cfg['params']['load_path']}")

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    _configure_eval_camera(env_cfg, task_env)

    if args_cli.video:
        video_kwargs = {
            "video_folder": str(video_folder),
            "step_trigger": lambda step: step == 0,
            "video_length": min(args_cli.video_length, args_cli.num_steps),
            "name_prefix": args_cli.video_name_prefix,
            "disable_logger": True,
        }
        print("[INFO] Recording rollout video.")
        print_dict(video_kwargs, nesting=4)
        gym_env = gym.wrappers.RecordVideo(gym_env, **video_kwargs)

    env = RlGamesVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register(
        "IsaacRlgWrapper", lambda config_name, num_actors, **kwargs: RlGamesGpuEnv(config_name, num_actors, **kwargs)
    )
    env_configurations.register("rlgpu", {"vecenv_type": "IsaacRlgWrapper", "env_creator": lambda **kwargs: env})

    agent_cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    runner = Runner()
    runner.load(agent_cfg)
    agent: BasePlayer = runner.create_player()
    agent.restore(resume_path)
    agent.reset()

    step_metrics = []
    done_count = 0
    env_closed = False
    try:
        obs = env.reset()
        if isinstance(obs, tuple):
            obs = obs[0]
        if isinstance(obs, dict):
            obs = obs["obs"]
        _ = agent.get_batch_size(obs, 1)
        if agent.is_rnn:
            agent.init_rnn()

        for step in range(args_cli.num_steps):
            if not simulation_app.is_running():
                break

            with torch.inference_mode():
                obs = agent.obs_to_torch(obs)
                actions = agent.get_action(obs, is_deterministic=args_cli.deterministic)
                step_out = env.step(actions)
                if len(step_out) == 5:
                    obs, rewards, terminated, truncated, _ = step_out
                    dones = torch.logical_or(terminated, truncated)
                else:
                    obs, rewards, dones, _ = step_out

                if isinstance(obs, dict):
                    obs = obs["obs"]

                success_rate = _env_metric(task_env, "in_success_region")
                reward_mean = _mean_float(rewards)
                task_metrics = _collect_task_metrics(task_env)

                if isinstance(dones, torch.Tensor):
                    dones_bool = dones.bool()
                    done_count += int(dones_bool.sum().detach().cpu())
                    if agent.is_rnn and agent.states is not None and dones_bool.any():
                        for state in agent.states:
                            state[:, dones_bool, :] = 0.0

                step_record = {
                    "step": step + 1,
                    "success_rate": success_rate,
                    "reward_mean": reward_mean,
                    **task_metrics,
                }
                step_metrics.append(step_record)

                if args_cli.print_interval > 0 and ((step + 1) % args_cli.print_interval == 0 or step == 0):
                    print(
                        "[EVAL] "
                        f"step={step + 1} "
                        f"success_rate={success_rate} "
                        f"reward_mean={reward_mean} "
                        f"task_metrics={task_metrics}"
                    )
    finally:
        env.close()
        env_closed = True

    success_values = [item["success_rate"] for item in step_metrics if item["success_rate"] is not None]
    reward_values = [item["reward_mean"] for item in step_metrics if item["reward_mean"] is not None]
    window = max(1, min(args_cli.success_window, len(success_values)))
    summary = {
        "task": args_cli.task,
        "checkpoint": resume_path,
        "num_envs": env_cfg.scene.num_envs,
        "num_steps_requested": args_cli.num_steps,
        "num_steps_completed": len(step_metrics),
        "deterministic": args_cli.deterministic,
        "done_count": done_count,
        "success_rate_mean": sum(success_values) / len(success_values) if success_values else None,
        "success_rate_final": success_values[-1] if success_values else None,
        "success_rate_last_window_mean": sum(success_values[-window:]) / window if success_values else None,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "video_enabled": args_cli.video,
        "video_folder": str(video_folder) if args_cli.video else None,
        "video_files": _latest_video_files(video_folder),
        "output_dir": str(output_dir),
        "env_closed": env_closed,
    }
    payload = {"summary": summary, "steps": step_metrics}
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[INFO] Wrote metrics to {metrics_path}")
    print("[INFO] Eval summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
