# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Evaluate an RL-Games checkpoint and optionally record a rollout video."""

import argparse
import csv
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
parser.add_argument("--trace_jsonl_path", type=str, default=None, help="Path to write per-step metrics JSONL.")
parser.add_argument("--trace_csv_path", type=str, default=None, help="Path to write per-step metrics CSV.")
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
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
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


def _tensor_values(value, expected_len: int | None = None) -> list[float] | None:
    if not isinstance(value, torch.Tensor):
        return None
    values = value.detach().float().flatten().cpu().tolist()
    if expected_len is not None and len(values) != expected_len:
        return None
    return [float(item) for item in values]


def _env_metric_values(task_env, name: str, expected_len: int | None = None) -> list[float] | None:
    if not hasattr(task_env, name):
        return None
    return _tensor_values(getattr(task_env, name), expected_len=expected_len)


def _collect_task_metrics(task_env) -> dict[str, float | None]:
    metric_names = [
        "cube_lift_height",
        "cube_xy_error",
        "cube_goal_height_error",
        "has_lifted_cube",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "left_finger_to_cube_dist",
        "right_finger_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_distance_asymmetry",
        "hand_to_cube_mean_dist",
        "hand_to_cube_max_dist",
        "finger_table_clearance",
        "finger_table_clearance_violation",
        "grasp_prior_reset_attempted",
        "grasp_prior_reset_success",
        "grasp_prior_reset_farther",
        "grasp_prior_reset_pos_error",
        "grasp_prior_reset_rot_error",
        "grasp_prior_reset_exact_tool_dist",
        "grasp_prior_reset_pregrasp_tool_dist",
        "grasp_prior_reset_exact_ee_dist",
        "grasp_prior_reset_pregrasp_ee_dist",
        "grasp_prior_reset_finger_center_dist",
        "grasp_prior_reset_finger_table_clearance",
        "grasp_prior_reset_gripper_width",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_offset_radial_dot",
        "grasp_prior_reset_offset_radial_angle",
        "grasp_prior_reset_projected_exact_finger_center_dist",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_pregrasp_tip_table_clearance",
        "grasp_prior_reset_projected_exact_tip_table_clearance",
        "grasp_prior_reset_quality_success",
        "grasp_prior_action_warmstart_active",
        "grasp_prior_action_warmstart_phase",
        "grasp_prior_action_warmstart_policy_action_z",
        "grasp_prior_action_warmstart_policy_gripper_action",
        "grasp_prior_action_warmstart_applied_action_z",
        "grasp_prior_action_warmstart_applied_gripper_action",
        "grasp_prior_action_warmstart_action_delta_abs",
        "grasp_prior_action_warmstart_exact_ee_error",
        "star_lift_height",
        "star_initial_xy_error",
        "goal_xy_error",
        "goal_height_error",
        "goal_yaw_error",
        "has_lifted_star",
        "ee_to_star_dist",
        "finger_center_to_star_dist",
        "left_finger_to_star_dist",
        "right_finger_to_star_dist",
        "max_finger_to_star_dist",
        "finger_distance_asymmetry",
        "gripper_width",
    ]
    return {name: _env_metric(task_env, name) for name in metric_names if hasattr(task_env, name)}


def _collect_episode_probe_metrics(task_env, num_envs: int) -> dict[str, list[float]]:
    metric_sources = {
        "success_rate": "in_success_region",
        "cube_lift_height": "cube_lift_height",
        "has_lifted_cube": "has_lifted_cube",
        "ee_to_cube_dist": "ee_to_cube_dist",
        "finger_center_to_cube_dist": "finger_center_to_cube_dist",
        "gripper_width": "gripper_width",
    }
    metrics: dict[str, list[float]] = {}
    for output_name, source_name in metric_sources.items():
        values = _env_metric_values(task_env, source_name, expected_len=num_envs)
        if values is not None:
            metrics[output_name] = values
    return metrics


def _empty_episode_stats(start_step: int) -> dict[str, float | int | None]:
    return {
        "start_step": int(start_step),
        "max_success_rate": None,
        "max_cube_lift_height": None,
        "max_has_lifted_cube": None,
        "min_ee_to_cube_dist": None,
        "min_finger_center_to_cube_dist": None,
        "min_gripper_width": None,
    }


def _update_episode_stats(
    stats: dict[str, float | int | None], probe_metrics: dict[str, list[float]], env_idx: int
) -> None:
    max_fields = {
        "success_rate": "max_success_rate",
        "cube_lift_height": "max_cube_lift_height",
        "has_lifted_cube": "max_has_lifted_cube",
    }
    min_fields = {
        "ee_to_cube_dist": "min_ee_to_cube_dist",
        "finger_center_to_cube_dist": "min_finger_center_to_cube_dist",
        "gripper_width": "min_gripper_width",
    }
    for source_name, stat_name in max_fields.items():
        values = probe_metrics.get(source_name)
        if values is None:
            continue
        value = values[env_idx]
        current = stats.get(stat_name)
        stats[stat_name] = value if current is None else max(float(current), value)
    for source_name, stat_name in min_fields.items():
        values = probe_metrics.get(source_name)
        if values is None:
            continue
        value = values[env_idx]
        current = stats.get(stat_name)
        stats[stat_name] = value if current is None else min(float(current), value)


def _episode_metric_value(probe_metrics: dict[str, list[float]], metric_name: str, env_idx: int) -> float | None:
    values = probe_metrics.get(metric_name)
    if values is None:
        return None
    return float(values[env_idx])


def _finish_episode_outcome(
    *,
    env_idx: int,
    episode_id: int,
    terminal_step: int,
    stats: dict[str, float | int | None],
    terminal_probe_metrics: dict[str, list[float]],
) -> dict[str, float | int | bool | None]:
    terminal_success = _episode_metric_value(terminal_probe_metrics, "success_rate", env_idx)
    terminal_lift = _episode_metric_value(terminal_probe_metrics, "cube_lift_height", env_idx)
    terminal_has_lifted = _episode_metric_value(terminal_probe_metrics, "has_lifted_cube", env_idx)
    max_success = stats.get("max_success_rate")
    max_lifted = stats.get("max_has_lifted_cube")
    return {
        "env_idx": int(env_idx),
        "episode_id": int(episode_id),
        "start_step": int(stats["start_step"]) if stats.get("start_step") is not None else None,
        "terminal_step": int(terminal_step),
        "terminal_source": "pre_done_state",
        "terminal_success_rate": terminal_success,
        "terminal_cube_lift_height": terminal_lift,
        "terminal_has_lifted_cube": terminal_has_lifted,
        "terminal_ee_to_cube_dist": _episode_metric_value(terminal_probe_metrics, "ee_to_cube_dist", env_idx),
        "terminal_finger_center_to_cube_dist": _episode_metric_value(
            terminal_probe_metrics, "finger_center_to_cube_dist", env_idx
        ),
        "terminal_gripper_width": _episode_metric_value(terminal_probe_metrics, "gripper_width", env_idx),
        **{key: value for key, value in stats.items() if key != "start_step"},
        "success": bool(max_success is not None and float(max_success) >= 0.5),
        "lifted": bool(max_lifted is not None and float(max_lifted) >= 0.5),
    }


def _collect_action_metrics(actions: torch.Tensor) -> dict[str, float | None]:
    if not isinstance(actions, torch.Tensor):
        return {}
    action_cpu = actions.detach().float().cpu()
    flat = action_cpu.flatten()
    metrics: dict[str, float | None] = {
        "action_mean": float(flat.mean()),
        "action_abs_mean": float(flat.abs().mean()),
        "action_min": float(flat.min()),
        "action_max": float(flat.max()),
    }
    if action_cpu.ndim >= 2 and action_cpu.shape[0] > 0:
        first = action_cpu[0]
        for idx, value in enumerate(first.tolist()):
            metrics[f"action_env0_{idx}"] = float(value)
        if first.numel() > 6:
            metrics["gripper_action_env0"] = float(first[6])
    return metrics


def _summarize_step_metrics(step_metrics: list[dict[str, float | int | None]]) -> dict[str, dict[str, float | int]]:
    summaries: dict[str, dict[str, float | int]] = {}
    for name in sorted({key for item in step_metrics for key in item.keys()} - {"step"}):
        records = [(item, float(item[name])) for item in step_metrics if item.get(name) is not None]
        if not records:
            continue
        float_values = [value for _, value in records]
        max_idx = max(range(len(float_values)), key=lambda idx: float_values[idx])
        min_idx = min(range(len(float_values)), key=lambda idx: float_values[idx])
        summaries[name] = {
            "final": float_values[-1],
            "max": float_values[max_idx],
            "max_step": int(records[max_idx][0]["step"]),
            "min": float_values[min_idx],
            "min_step": int(records[min_idx][0]["step"]),
            "mean": sum(float_values) / len(float_values),
        }
    return summaries


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _first_done_step(step_metrics: list[dict[str, float | int | None]]) -> int | None:
    for item in step_metrics:
        done_count = item.get("done_count_step")
        if done_count is not None and int(done_count) > 0:
            return int(item["step"])
    return None


def _summarize_episode_outcomes(outcomes: list[dict[str, float | int | bool | None]]) -> dict[str, float | int | None]:
    if not outcomes:
        return {
            "count": 0,
            "success_rate": None,
            "lifted_rate": None,
            "max_lift_mean": None,
            "max_lift_min": None,
            "max_lift_max": None,
            "terminal_success_rate_mean": None,
            "terminal_lift_mean": None,
        }
    success_values = [1.0 if outcome.get("success") else 0.0 for outcome in outcomes]
    lifted_values = [1.0 if outcome.get("lifted") else 0.0 for outcome in outcomes]
    max_lifts = [
        float(outcome["max_cube_lift_height"])
        for outcome in outcomes
        if outcome.get("max_cube_lift_height") is not None
    ]
    terminal_success = [
        float(outcome["terminal_success_rate"])
        for outcome in outcomes
        if outcome.get("terminal_success_rate") is not None
    ]
    terminal_lifts = [
        float(outcome["terminal_cube_lift_height"])
        for outcome in outcomes
        if outcome.get("terminal_cube_lift_height") is not None
    ]
    return {
        "count": len(outcomes),
        "success_rate": _mean(success_values),
        "lifted_rate": _mean(lifted_values),
        "max_lift_mean": _mean(max_lifts),
        "max_lift_min": min(max_lifts) if max_lifts else None,
        "max_lift_max": max(max_lifts) if max_lifts else None,
        "terminal_success_rate_mean": _mean(terminal_success),
        "terminal_lift_mean": _mean(terminal_lifts),
    }


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


def _write_trace_files(
    step_metrics: list[dict[str, float | int | None]],
    *,
    trace_jsonl_path: Path,
    trace_csv_path: Path,
) -> None:
    trace_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_jsonl_path.open("w", encoding="utf-8") as f:
        for record in step_metrics:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    trace_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for record in step_metrics for key in record.keys()})
    if "step" in fieldnames:
        fieldnames.remove("step")
        fieldnames.insert(0, "step")
    with trace_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in step_metrics:
            writer.writerow(record)


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
    if task_env is not None and hasattr(task_env, "scene") and len(task_env.scene.env_origins) > 0:
        env_origin = task_env.scene.env_origins[0].detach().cpu().tolist()
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
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
    trace_jsonl_path = (
        Path(args_cli.trace_jsonl_path).expanduser().resolve()
        if args_cli.trace_jsonl_path
        else output_dir / "trace.jsonl"
    )
    trace_csv_path = (
        Path(args_cli.trace_csv_path).expanduser().resolve()
        if args_cli.trace_csv_path
        else output_dir / "trace.csv"
    )
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

        num_envs = int(env.unwrapped.num_envs)
        episode_ids = [0 for _ in range(num_envs)]
        episode_stats = [_empty_episode_stats(start_step=1) for _ in range(num_envs)]
        completed_episode_outcomes: list[dict[str, float | int | bool | None]] = []

        for step in range(args_cli.num_steps):
            if not simulation_app.is_running():
                break

            with torch.inference_mode():
                pre_step_episode_probe_metrics = _collect_episode_probe_metrics(task_env, num_envs)
                for env_idx in range(num_envs):
                    _update_episode_stats(episode_stats[env_idx], pre_step_episode_probe_metrics, env_idx)

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
                action_metrics = _collect_action_metrics(actions)

                step_done_count = 0
                if isinstance(dones, torch.Tensor):
                    dones_bool = dones.bool()
                    step_done_count = int(dones_bool.sum().detach().cpu())
                    done_count += step_done_count
                    for env_idx in torch.nonzero(dones_bool.flatten(), as_tuple=False).flatten().detach().cpu().tolist():
                        completed_episode_outcomes.append(
                            _finish_episode_outcome(
                                env_idx=int(env_idx),
                                episode_id=episode_ids[int(env_idx)],
                                terminal_step=step + 1,
                                stats=episode_stats[int(env_idx)],
                                terminal_probe_metrics=pre_step_episode_probe_metrics,
                            )
                        )
                        episode_ids[int(env_idx)] += 1
                        episode_stats[int(env_idx)] = _empty_episode_stats(start_step=step + 2)
                    if agent.is_rnn and agent.states is not None and dones_bool.any():
                        for state in agent.states:
                            state[:, dones_bool, :] = 0.0
                elif dones is not None:
                    step_done_count = int(bool(dones))
                    done_count += step_done_count
                    if step_done_count > 0:
                        completed_episode_outcomes.append(
                            _finish_episode_outcome(
                                env_idx=0,
                                episode_id=episode_ids[0],
                                terminal_step=step + 1,
                                stats=episode_stats[0],
                                terminal_probe_metrics=pre_step_episode_probe_metrics,
                            )
                        )
                        episode_ids[0] += 1
                        episode_stats[0] = _empty_episode_stats(start_step=step + 2)

                step_record = {
                    "step": step + 1,
                    "done_any_step": int(step_done_count > 0),
                    "done_count_step": step_done_count,
                    "done_count_cumulative": done_count,
                    "success_rate": success_rate,
                    "reward_mean": reward_mean,
                    **task_metrics,
                    **action_metrics,
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
    first_done_step = _first_done_step(step_metrics)
    first_episode_metrics = [
        item for item in step_metrics if first_done_step is None or int(item["step"]) <= first_done_step
    ]
    first_episode_success_values = [
        item["success_rate"] for item in first_episode_metrics if item["success_rate"] is not None
    ]
    first_episode_reward_values = [
        item["reward_mean"] for item in first_episode_metrics if item["reward_mean"] is not None
    ]
    completed_episode_summary = _summarize_episode_outcomes(completed_episode_outcomes)
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
        "trace_jsonl_path": str(trace_jsonl_path),
        "trace_csv_path": str(trace_csv_path),
        "output_dir": str(output_dir),
        "env_closed": env_closed,
        "first_done_step": first_done_step,
        "first_episode_num_steps": len(first_episode_metrics),
        "first_episode_success_rate_final": first_episode_success_values[-1]
        if first_episode_success_values
        else None,
        "first_episode_success_rate_max": max(first_episode_success_values)
        if first_episode_success_values
        else None,
        "first_episode_success_rate_mean": _mean(first_episode_success_values),
        "first_episode_reward_final": first_episode_reward_values[-1]
        if first_episode_reward_values
        else None,
        "first_episode_reward_mean": _mean(first_episode_reward_values),
        "first_episode_metric_summaries": _summarize_step_metrics(first_episode_metrics),
        "completed_episode_count": completed_episode_summary["count"],
        "completed_episode_summary": completed_episode_summary,
        "episode_outcomes": completed_episode_outcomes,
        "metric_summaries": _summarize_step_metrics(step_metrics),
    }
    payload = {"summary": summary, "steps": step_metrics}
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_trace_files(step_metrics, trace_jsonl_path=trace_jsonl_path, trace_csv_path=trace_csv_path)
    print(f"[INFO] Wrote metrics to {metrics_path}")
    print(f"[INFO] Wrote trace JSONL to {trace_jsonl_path}")
    print(f"[INFO] Wrote trace CSV to {trace_csv_path}")
    print("[INFO] Eval summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
