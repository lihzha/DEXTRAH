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
from dataclasses import asdict, replace
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
        "dataset_target_t_plus_1",
        "dataset_target_t_plus_7",
        "controller_target_hold",
        "dp_replan",
    ],
    help="Replay mode. May be passed multiple times. Defaults to dataset_t and dp_replan.",
)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument(
    "--pose_action_multiplier",
    type=float,
    default=1.0,
    help=(
        "Replay-only multiplier applied to the first six pose action dimensions before clipping. "
        "Use only for controller-realization diagnostics; do not use this to claim BC policy quality."
    ),
)
parser.add_argument(
    "--action_repeat",
    type=int,
    default=1,
    help=(
        "Replay-only repeat count. The same selected action is executed for this many env steps before "
        "advancing the dataset/policy action index. This is diagnostic and changes temporal semantics."
    ),
)
parser.add_argument(
    "--controller_target_lookahead",
    type=int,
    default=1,
    help="Replay-only target row lookahead for controller_target_hold mode.",
)
parser.add_argument(
    "--controller_target_tolerance",
    type=float,
    default=0.015,
    help="EE-position tolerance in meters before controller_target_hold advances to the next target row.",
)
parser.add_argument(
    "--controller_target_max_hold",
    type=int,
    default=16,
    help="Maximum env steps to hold one target row before controller_target_hold advances.",
)
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
parser.add_argument(
    "--demo_reset_trajectory_json",
    type=str,
    default=None,
    help=(
        "Optional raw GraspGenX/cuRobo trajectory.json for the selected demo episode. "
        "When present, the selected frame's joint_position is also written into the Franka env."
    ),
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
from dextrah_lab.offline_dp_bc.action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    apply_normalized_action_to_world_pose,
    axis_angle_from_quat_wxyz,
    derive_relative_ee_actions,
    normalized_action_to_world_delta,
    quat_inv_wxyz,
    quat_mul_wxyz,
)
from dextrah_lab.offline_dp_bc.analyze_policy_trace import POSITION_FEATURE_IDX
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    LowdimObsHistory,
    extract_lowdim_obs_from_ppo_obs,
    predict_action_sequence_from_ppo_obs,
)
from dextrah_lab.offline_dp_bc.trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER
from dextrah_lab.offline_dp_bc.trajectory_conversion import write_demo_dataset


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)
RESIDUAL_TARGET_ACTION_CONVENTION = replace(DEFAULT_DEXTRAH_ACTION_CONVENTION, clip_actions=False)


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


def _trajectory_joint_payload(path: Path | None, episode_step: int) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"{path} does not contain a non-empty frames list")
    frame_idx = int(np.clip(int(episode_step), 0, len(frames) - 1))
    frame = frames[frame_idx]
    if "joint_position" not in frame:
        raise ValueError(f"{path} frame {frame_idx} has no joint_position")
    q = np.asarray(frame["joint_position"], dtype=np.float32)
    if q.ndim != 1:
        raise ValueError(f"{path} frame {frame_idx} joint_position must be 1D, got {q.shape}")
    return {
        "path": str(path),
        "frame": int(frame_idx),
        "phase": str(frame.get("phase", "")),
        "joint_position": q,
        "raw_joint_dim": int(q.shape[0]),
        "total_frames": int(len(frames)),
    }


def _demo_reset_payload(
    path: Path | None,
    episode: int,
    episode_step: int,
    *,
    trajectory_json: Path | None = None,
) -> dict[str, Any] | None:
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
        "source_trajectory": _trajectory_joint_payload(trajectory_json, int(row_idx - start)),
    }


def _policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _reset_robot_from_source_trajectory(
    task_env: Any,
    env_ids: torch.Tensor,
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    if source is None:
        return {
            "exact_robot_joint_reset_available": False,
            "robot_reset_note": "converted lowdim NPZ has no Franka joint state; robot remains at task reset",
        }

    num_ids = int(env_ids.numel())
    raw_q = np.asarray(source["joint_position"], dtype=np.float32)
    raw_q_tensor = torch.as_tensor(raw_q, dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    joint_pos = task_env._robot.data.default_joint_pos[env_ids].clone()
    joint_vel = torch.zeros_like(joint_pos)
    arm_count = len(task_env.arm_joint_ids)
    finger_count = len(task_env.finger_joint_ids)

    if raw_q_tensor.shape[1] == joint_pos.shape[1]:
        joint_pos[:] = raw_q_tensor
        mapping = "full_articulation"
    elif raw_q_tensor.shape[1] == arm_count + finger_count:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + finger_count]
        mapping = "arm_plus_two_fingers"
    elif raw_q_tensor.shape[1] == arm_count + 1:
        joint_pos[:, task_env.arm_joint_ids] = raw_q_tensor[:, :arm_count]
        joint_pos[:, task_env.finger_joint_ids] = raw_q_tensor[:, arm_count : arm_count + 1].repeat(1, finger_count)
        mapping = "arm_plus_single_finger_repeated"
    else:
        raise ValueError(
            f"Cannot map trajectory joint_position dim {raw_q_tensor.shape[1]} to "
            f"{joint_pos.shape[1]} env joints ({arm_count} arm, {finger_count} fingers)"
        )

    joint_pos = torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)
    task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    task_env.robot_dof_targets[env_ids] = joint_pos
    task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]

    return {
        "exact_robot_joint_reset_available": True,
        "robot_reset_note": "raw trajectory joint_position applied to Franka articulation",
        "source_trajectory_json": str(source["path"]),
        "source_trajectory_frame": int(source["frame"]),
        "source_trajectory_phase": str(source.get("phase", "")),
        "source_trajectory_total_frames": int(source["total_frames"]),
        "source_joint_position_raw": raw_q.astype(float).tolist(),
        "source_joint_position_raw_dim": int(source["raw_joint_dim"]),
        "source_joint_mapping": mapping,
        "applied_joint_position_env0": joint_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
    }


def _apply_demo_reset(task_env: Any, demo_reset: dict[str, Any]) -> tuple[torch.Tensor, dict[str, Any]]:
    """Overwrite cube pose/goal and, when available, Franka joint state from a demo row."""

    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    num_ids = int(env_ids.numel())
    target_obs = np.asarray(demo_reset["target_obs"], dtype=np.float32)
    robot_reset_summary = _reset_robot_from_source_trajectory(
        task_env,
        env_ids,
        demo_reset.get("source_trajectory"),
    )
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
    joint_after = task_env._robot.data.joint_pos[env_ids].detach().float().cpu().numpy()
    if robot_reset_summary["exact_robot_joint_reset_available"]:
        applied = np.asarray(robot_reset_summary["applied_joint_position_env0"], dtype=np.float32)
        joint_diff = joint_after[0] - applied
        joint_linf_diff = float(np.max(np.abs(joint_diff)))
        joint_l2_diff = float(np.linalg.norm(joint_diff))
    else:
        joint_linf_diff = None
        joint_l2_diff = None
    summary = {
        "dataset": str(demo_reset["path"]),
        "episode": int(demo_reset["episode"]),
        "episode_step": int(demo_reset["episode_step"]),
        "row": int(demo_reset["row"]),
        "phase": str(demo_reset["phase"]),
        "target_cube_pos": target_obs[7:10].astype(float).tolist(),
        "target_cube_quat": target_obs[10:14].astype(float).tolist(),
        "target_cube_minus_ee": target_obs[14:17].astype(float).tolist(),
        "target_ee_pos": target_obs[0:3].astype(float).tolist(),
        "target_ee_quat": target_obs[3:7].astype(float).tolist(),
        "target_gripper_width": float(target_obs[20]),
        "target_action": np.asarray(demo_reset["target_action"], dtype=np.float32).astype(float).tolist(),
        "live_lowdim_after_reset_env0": live0.astype(float).tolist(),
        "live_ee_pos_after_reset_env0": live0[0:3].astype(float).tolist(),
        "live_ee_quat_after_reset_env0": live0[3:7].astype(float).tolist(),
        "live_cube_pos_after_reset_env0": live0[7:10].astype(float).tolist(),
        "live_cube_minus_ee_after_reset_env0": live0[14:17].astype(float).tolist(),
        "lowdim_linf_diff_env0": float(np.max(np.abs(diff))),
        "lowdim_l2_diff_env0": float(np.linalg.norm(diff)),
        "cube_pos_l2_diff_env0": float(np.linalg.norm(diff[7:10])),
        "cube_minus_ee_l2_diff_env0": float(np.linalg.norm(diff[14:17])),
        "ee_pos_l2_diff_env0": float(np.linalg.norm(diff[0:3])),
        "joint_position_after_reset_env0": joint_after[0].astype(float).tolist(),
        "joint_linf_diff_after_write_env0": joint_linf_diff,
        "joint_l2_diff_after_write_env0": joint_l2_diff,
        **robot_reset_summary,
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


def _ratio(actual: float, expected: float) -> float | None:
    if not math.isfinite(expected) or abs(expected) < 1.0e-8:
        return None
    return float(actual / expected)


def _normalized_action_to_dataset_target(
    live_lowdim: np.ndarray,
    target_lowdim: np.ndarray,
    *,
    gripper_action: float,
) -> np.ndarray:
    """Compute a live-state residual action toward a dataset target row.

    This is a replay-only diagnostic. Converted BC labels are deltas between
    adjacent source waypoints. Here we instead ask what DEXTRAH action would
    target a selected source waypoint from the live controller state at the
    current env step.
    """

    ee_pos = np.stack(
        (
            np.asarray(live_lowdim[:3], dtype=np.float32),
            np.asarray(target_lowdim[:3], dtype=np.float32),
        ),
        axis=0,
    )
    ee_quat = np.stack(
        (
            np.asarray(live_lowdim[3:7], dtype=np.float32),
            np.asarray(target_lowdim[3:7], dtype=np.float32),
        ),
        axis=0,
    )
    grip = np.asarray([float(gripper_action), float(gripper_action)], dtype=np.float32)
    return derive_relative_ee_actions(
        ee_pos,
        ee_quat,
        gripper_action=grip,
        convention=RESIDUAL_TARGET_ACTION_CONVENTION,
        terminal_action="drop",
    )[0].astype(np.float32, copy=False)


def _finite_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            value_f = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value_f):
            values.append(value_f)
    return values


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


def _plot_action_audit(rows: list[dict[str, Any]], output_path: Path) -> None:
    if not rows:
        return
    modes = list(dict.fromkeys(str(row["mode"]) for row in rows))
    fig, axes = plt.subplots(5, 1, figsize=(13, 16), sharex=True, constrained_layout=True)
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode and int(row["env_index"]) == 0]
        x = [row["step"] for row in mode_rows]
        axes[0].plot(x, [row["expected_xyz_delta_norm"] for row in mode_rows], label=f"{mode} expected")
        axes[0].plot(x, [row["actual_xyz_delta_norm"] for row in mode_rows], linestyle="--", label=f"{mode} actual")
        axes[1].plot(x, [row["xyz_realization_ratio"] for row in mode_rows], label=mode)
        axes[2].plot(x, [row["xyz_target_error_norm"] for row in mode_rows], label=f"{mode} target")
        axes[2].plot(
            x,
            [row["actual_vs_dataset_next_ee_pos_norm"] for row in mode_rows],
            linestyle="--",
            label=f"{mode} dataset-next",
        )
        tracking_after = [row.get("tracking_target_error_after") for row in mode_rows]
        if any(value is not None for value in tracking_after):
            axes[2].plot(
                x,
                [float(value) if value is not None else np.nan for value in tracking_after],
                linestyle=":",
                label=f"{mode} residual-target",
            )
        axes[3].plot(x, [row["expected_rot_delta_norm"] for row in mode_rows], label=f"{mode} expected")
        axes[3].plot(x, [row["actual_rot_delta_norm"] for row in mode_rows], linestyle="--", label=f"{mode} actual")
        axes[4].plot(x, [row["gripper_width_after"] for row in mode_rows], label=f"{mode} width")
        axes[4].plot(x, [row["target_gripper_width_from_action"] for row in mode_rows], linestyle="--", label=f"{mode} target")
    axes[0].set_title("Expected vs Realized EE Translation Delta")
    axes[0].set_ylabel("m / env step")
    axes[1].set_title("Translation Realization Ratio")
    axes[1].set_ylabel("actual / expected")
    axes[1].axhline(1.0, color="black", alpha=0.25, linewidth=1.0)
    axes[2].set_title("Actual EE Target Error")
    axes[2].set_ylabel("m")
    axes[3].set_title("Expected vs Realized EE Rotation Delta")
    axes[3].set_ylabel("rad / env step")
    axes[4].set_title("Gripper Width Target From Action")
    axes[4].set_ylabel("m")
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
        "This is a bounded Isaac controller replay. It does not train. Each mode resets the env, optionally applies a demo-conditioned cube reset, chooses either a fixed demo label window or the nearest converted cuRobo demo row, compares official-DP prediction against dataset labels, and executes a short sequence. `dataset_target_*` modes are replay-only residual-target diagnostics that recompute a live-state action toward a selected source waypoint. `controller_target_hold` is a replay-only absolute-pose-to-relative receding-target diagnostic that holds each source target until the live controller reaches it or times out.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Reset / Label Selection",
        "",
        f"- Demo reset: `{summary['demo_reset']}`",
        f"- Dataset start: `{summary['dataset_start']}`",
        f"- Pose action multiplier: `{summary.get('pose_action_multiplier')}`",
        f"- Action repeat: `{summary.get('action_repeat')}`",
        f"- Controller target settings: `{summary.get('controller_target_settings')}`",
        f"- Action audit: `{summary.get('action_audit')}`",
        "",
        "## Mode Summary",
        "",
        "| mode | steps | nearest row | nearest phase | final EE-cube | final finger-cube | final cube-minus-EE | first close | first hard close | target close | target lift | mean cosine | median xyz ratio | mean target err | mean residual target before | mean residual target after | mean clip frac | max clip frac |",
        "|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, payload in summary["modes"].items():
        lines.append(
            f"| {mode} | {payload['steps']} | {payload['initial_nearest_row']} | {payload['initial_nearest_phase']} | "
            f"{payload['final_ee_to_cube']:.4f} | {payload['final_finger_center_to_cube']:.4f} | "
            f"{payload['final_cube_minus_ee']} | {payload['first_executed_negative_step']} | "
            f"{payload['first_executed_hard_close_step']} | "
            f"{payload.get('first_tracking_target_close_phase_step')} | "
            f"{payload.get('first_tracking_target_lift_phase_step')} | "
            f"{payload['mean_actual_vs_expected_xyz_cosine']:.4f} | "
            f"{payload.get('median_xyz_realization_ratio', float('nan')):.4f} | "
            f"{payload.get('mean_xyz_target_error_norm', float('nan')):.5f} | "
            f"{payload.get('mean_tracking_target_error_before', float('nan')):.5f} | "
            f"{payload.get('mean_tracking_target_error_after', float('nan')):.5f} | "
            f"{payload.get('mean_pose_action_clip_fraction', float('nan')):.3f} | "
            f"{payload.get('max_pose_action_clip_fraction', float('nan')):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- CSV: `{summary['csv']}`",
            f"- JSON: `{summary['json']}`",
            f"- Plot: `{summary['plot']}`",
            f"- Action audit plot: `{summary.get('action_audit_plot')}`",
            f"- Videos: `{summary['video_files']}`",
            f"- Controller rollout datasets: `{summary.get('controller_rollout_datasets', [])}`",
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
    demo_reset_trajectory_path = (
        Path(args_cli.demo_reset_trajectory_json).expanduser().resolve()
        if args_cli.demo_reset_trajectory_json
        else None
    )
    if demo_reset_dataset_path is not None and not demo_reset_dataset_path.is_file():
        raise FileNotFoundError(demo_reset_dataset_path)
    if demo_reset_trajectory_path is not None and not demo_reset_trajectory_path.is_file():
        raise FileNotFoundError(demo_reset_trajectory_path)
    demo_reset = _demo_reset_payload(
        demo_reset_dataset_path,
        int(args_cli.demo_reset_episode),
        int(args_cli.demo_reset_step),
        trajectory_json=demo_reset_trajectory_path,
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
    action_repeat = max(1, int(args_cli.action_repeat))
    pose_action_multiplier = float(args_cli.pose_action_multiplier)
    controller_target_lookahead = max(0, int(args_cli.controller_target_lookahead))
    controller_target_tolerance = max(0.0, float(args_cli.controller_target_tolerance))
    controller_target_max_hold = max(1, int(args_cli.controller_target_max_hold))
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
        video_period = max(1, int(args_cli.video_length))
        gym_env = gym.wrappers.RecordVideo(
            gym_env,
            video_folder=str(output_dir / "videos"),
            step_trigger=lambda step: step % video_period == 0,
            video_length=int(args_cli.video_length),
            name_prefix=str(args_cli.video_name_prefix),
            disable_logger=True,
        )
    action_scale_np = task_env.action_scale.detach().float().cpu().numpy()
    root_quat_wxyz_np = task_env._robot.data.root_quat_w[0].detach().float().cpu().numpy()
    action_audit_summary = {
        "controller": "IsaacLab DifferentialIKController(command_type=pose, use_relative_mode=True, ik_method=dls)",
        "action_space": int(task_env.cfg.action_space),
        "env_decimation": int(task_env.cfg.decimation),
        "sim_dt": float(task_env.cfg.sim.dt),
        "env_dt": float(task_env.dt),
        "task_action_scale": action_scale_np.astype(float).tolist(),
        "conversion_pose_scale": DEFAULT_DEXTRAH_ACTION_CONVENTION.pose_scale.astype(float).tolist(),
        "conversion_world_to_action_quat_wxyz": list(DEFAULT_DEXTRAH_ACTION_CONVENTION.world_to_action_quat_wxyz),
        "robot_root_quat_wxyz_env0": root_quat_wxyz_np.astype(float).tolist(),
        "gripper_convention": "-1 closes, +1 opens; target_width=0.5*(action+1)*max_gripper_width",
        "max_gripper_width": float(task_env.cfg.max_gripper_width),
        "video_step_trigger": "global_step % video_length == 0",
        "pose_action_multiplier": pose_action_multiplier,
        "action_repeat": action_repeat,
        "repeat_semantics": "selected dataset/policy action index advances every action_repeat env steps",
        "controller_target_hold_semantics": (
            "recompute normalized relative action from live EE pose to a held source dataset target row; "
            "advance target after tolerance hit or max hold timeout"
        ),
    }
    controller_target_settings = {
        "lookahead_rows": controller_target_lookahead,
        "tolerance_m": controller_target_tolerance,
        "max_hold_env_steps": controller_target_max_hold,
    }

    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    controller_rollout_datasets: list[dict[str, Any]] = []
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
            held_dp_action: np.ndarray | None = None
            controller_target_rows: np.ndarray | None = None
            controller_target_holds: np.ndarray | None = None
            controller_rollout_obs: list[np.ndarray] = []
            controller_rollout_actions: list[np.ndarray] = []
            controller_rollout_phase_ids: list[int] = []
            controller_rollout_target_rows: list[int] = []

            for step in range(int(args_cli.steps)):
                action_index = int(step // action_repeat)
                repeat_index = int(step % action_repeat)
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
                if mode == "controller_target_hold" and controller_target_rows is None:
                    controller_target_rows = np.asarray(
                        [
                            _clipped_row(int(base) + controller_target_lookahead, episode_ends)
                            for base in nearest_rows
                        ],
                        dtype=np.int64,
                    )
                    controller_target_holds = np.zeros(lowdim.shape[0], dtype=np.int64)
                nearest_distances = [
                    _nearest_dataset_row(dataset_obs, lowdim[env_idx])[1] for env_idx in range(lowdim.shape[0])
                ]
                live_nearest = [
                    _nearest_dataset_row(dataset_obs, lowdim[env_idx])[0] for env_idx in range(lowdim.shape[0])
                ]
                with torch.inference_mode():
                    if repeat_index == 0 or held_dp_action is None:
                        dp_seq = predict_action_sequence_from_ppo_obs(policy, policy_obs, history, step=step)
                        held_dp_action = dp_seq[:, 0].copy()
                    else:
                        history.push(lowdim.astype(np.float32, copy=False), step=step)
                        dp_seq = np.repeat(held_dp_action[:, None, :], repeats=1, axis=1)

                exec_actions = np.zeros((task_env.num_envs, FRANKA_CUBE_ACTION_DIM), dtype=np.float32)
                labels_t = np.zeros_like(exec_actions)
                labels_t1 = np.zeros_like(exec_actions)
                labels_t7 = np.zeros_like(exec_actions)
                exec_label_rows = np.full(task_env.num_envs, -1, dtype=np.int64)
                exec_label_offsets = np.full(task_env.num_envs, -1, dtype=np.int64)
                tracking_target_rows = np.full(task_env.num_envs, -1, dtype=np.int64)
                tracking_target_offsets = np.full(task_env.num_envs, -1, dtype=np.int64)
                controller_target_rows_after = np.full(task_env.num_envs, -1, dtype=np.int64)
                controller_target_holds_before = np.full(task_env.num_envs, -1, dtype=np.int64)
                controller_target_holds_after = np.full(task_env.num_envs, -1, dtype=np.int64)
                controller_target_advanced = np.zeros(task_env.num_envs, dtype=bool)
                controller_target_advance_reasons: list[str] = [""] * task_env.num_envs
                exec_action_sources: list[str] = ["unknown"] * task_env.num_envs
                for env_idx in range(task_env.num_envs):
                    base = int(nearest_rows[env_idx])
                    row_t = _clipped_row(base + action_index, episode_ends)
                    row_t1 = _clipped_row(row_t + 1, episode_ends)
                    row_t7 = _clipped_row(row_t + 7, episode_ends)
                    labels_t[env_idx] = dataset_action[row_t]
                    labels_t1[env_idx] = dataset_action[row_t1]
                    labels_t7[env_idx] = dataset_action[row_t7]
                    if mode == "dataset_t":
                        exec_actions[env_idx] = labels_t[env_idx]
                        exec_label_rows[env_idx] = row_t
                        exec_label_offsets[env_idx] = 0
                        exec_action_sources[env_idx] = "dataset_t"
                    elif mode == "dataset_t_plus_1":
                        exec_actions[env_idx] = labels_t1[env_idx]
                        exec_label_rows[env_idx] = row_t1
                        exec_label_offsets[env_idx] = 1
                        exec_action_sources[env_idx] = "dataset_t_plus_1"
                    elif mode == "dataset_t_plus_7":
                        exec_actions[env_idx] = labels_t7[env_idx]
                        exec_label_rows[env_idx] = row_t7
                        exec_label_offsets[env_idx] = 7
                        exec_action_sources[env_idx] = "dataset_t_plus_7"
                    elif mode == "dataset_open_t":
                        exec_actions[env_idx] = labels_t[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                        exec_label_rows[env_idx] = row_t
                        exec_label_offsets[env_idx] = 0
                        exec_action_sources[env_idx] = "dataset_open_t"
                    elif mode == "dataset_open_t_plus_1":
                        exec_actions[env_idx] = labels_t1[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                        exec_label_rows[env_idx] = row_t1
                        exec_label_offsets[env_idx] = 1
                        exec_action_sources[env_idx] = "dataset_open_t_plus_1"
                    elif mode == "dataset_open_t_plus_7":
                        exec_actions[env_idx] = labels_t7[env_idx]
                        exec_actions[env_idx, 6] = 1.0
                        exec_label_rows[env_idx] = row_t7
                        exec_label_offsets[env_idx] = 7
                        exec_action_sources[env_idx] = "dataset_open_t_plus_7"
                    elif mode == "dataset_target_t_plus_1":
                        exec_actions[env_idx] = _normalized_action_to_dataset_target(
                            lowdim[env_idx],
                            dataset_obs[row_t1],
                            gripper_action=float(dataset_action[row_t1, 6]),
                        )
                        exec_label_rows[env_idx] = row_t1
                        exec_label_offsets[env_idx] = 1
                        tracking_target_rows[env_idx] = row_t1
                        tracking_target_offsets[env_idx] = 1
                        exec_action_sources[env_idx] = "dataset_target_t_plus_1"
                    elif mode == "dataset_target_t_plus_7":
                        exec_actions[env_idx] = _normalized_action_to_dataset_target(
                            lowdim[env_idx],
                            dataset_obs[row_t7],
                            gripper_action=float(dataset_action[row_t7, 6]),
                        )
                        exec_label_rows[env_idx] = row_t7
                        exec_label_offsets[env_idx] = 7
                        tracking_target_rows[env_idx] = row_t7
                        tracking_target_offsets[env_idx] = 7
                        exec_action_sources[env_idx] = "dataset_target_t_plus_7"
                    elif mode == "controller_target_hold":
                        if controller_target_rows is None or controller_target_holds is None:
                            raise RuntimeError("controller_target_hold state was not initialized")
                        target_row = int(controller_target_rows[env_idx])
                        exec_actions[env_idx] = _normalized_action_to_dataset_target(
                            lowdim[env_idx],
                            dataset_obs[target_row],
                            gripper_action=float(dataset_action[target_row, 6]),
                        )
                        exec_label_rows[env_idx] = target_row
                        exec_label_offsets[env_idx] = int(target_row - row_t)
                        tracking_target_rows[env_idx] = target_row
                        tracking_target_offsets[env_idx] = int(target_row - row_t)
                        controller_target_holds_before[env_idx] = int(controller_target_holds[env_idx])
                        exec_action_sources[env_idx] = "controller_target_hold"
                    elif mode == "dp_replan":
                        exec_actions[env_idx] = dp_seq[env_idx, 0]
                        exec_action_sources[env_idx] = "dp_replan_first_action"
                    else:
                        raise ValueError(mode)

                raw_exec_actions = exec_actions.copy()
                if pose_action_multiplier != 1.0:
                    exec_actions[:, :6] = exec_actions[:, :6] * pose_action_multiplier
                clip = float(args_cli.clip_actions)
                if math.isfinite(clip) and clip > 0.0:
                    exec_actions = np.clip(exec_actions, -clip, clip)
                clip_hits = np.abs(exec_actions[:, :6]) >= (clip - 1.0e-6) if math.isfinite(clip) and clip > 0.0 else np.zeros_like(exec_actions[:, :6], dtype=bool)
                expected_world_delta = normalized_action_to_world_delta(exec_actions)
                before_lowdim = lowdim.copy()
                before_ee_to_cube = np.linalg.norm(before_lowdim[:, 14:17], axis=1)
                expected_target_pos, expected_target_quat = apply_normalized_action_to_world_pose(
                    before_lowdim[:, :3],
                    before_lowdim[:, 3:7],
                    exec_actions,
                )
                target_gripper_width = np.clip(
                    0.5 * (exec_actions[:, 6] + 1.0) * float(task_env.cfg.max_gripper_width),
                    0.0,
                    float(task_env.cfg.max_gripper_width),
                )
                policy_obs_next, rewards, terminated, truncated, _info = _policy_obs_from_step(
                    gym_env.step(torch.as_tensor(exec_actions, dtype=torch.float32, device=task_env.device))
                )
                after_lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs_next).detach().float().cpu().numpy()
                after_ee_to_cube = np.linalg.norm(after_lowdim[:, 14:17], axis=1)
                actual_delta = after_lowdim[:, :3] - before_lowdim[:, :3]
                actual_quat_delta = quat_mul_wxyz(after_lowdim[:, 3:7], quat_inv_wxyz(before_lowdim[:, 3:7]))
                actual_rot_delta = axis_angle_from_quat_wxyz(actual_quat_delta)
                reward_np = rewards.detach().float().cpu().numpy()

                for env_idx in range(task_env.num_envs):
                    nearest_row = int(nearest_rows[env_idx])
                    live_nearest_row = int(live_nearest[env_idx])
                    current_row = _clipped_row(nearest_row + step, episode_ends)
                    phase = phase_names[int(phase_ids[current_row])]
                    live_nearest_phase = phase_names[int(phase_ids[live_nearest_row])]
                    cosine = _cosine(actual_delta[env_idx], expected_world_delta[env_idx, :3])
                    rot_cosine = _cosine(actual_rot_delta[env_idx], expected_world_delta[env_idx, 3:6])
                    expected_xyz_norm = _safe_norm(expected_world_delta[env_idx, :3])
                    actual_xyz_norm = _safe_norm(actual_delta[env_idx])
                    expected_rot_norm = _safe_norm(expected_world_delta[env_idx, 3:6])
                    actual_rot_norm = _safe_norm(actual_rot_delta[env_idx])
                    xyz_target_error_norm = _safe_norm(after_lowdim[env_idx, :3] - expected_target_pos[env_idx])
                    quat_target_error = quat_mul_wxyz(after_lowdim[env_idx, 3:7], quat_inv_wxyz(expected_target_quat[env_idx]))
                    quat_target_error_norm = _safe_norm(axis_angle_from_quat_wxyz(quat_target_error))
                    label_row = int(exec_label_rows[env_idx])
                    if label_row >= 0:
                        label_next_row = _clipped_row(label_row + 1, episode_ends)
                        label_delta_xyz = dataset_obs[label_next_row, :3] - dataset_obs[label_row, :3]
                        label_delta_quat = quat_mul_wxyz(
                            dataset_obs[label_next_row, 3:7],
                            quat_inv_wxyz(dataset_obs[label_row, 3:7]),
                        )
                        label_delta_rot = axis_angle_from_quat_wxyz(label_delta_quat)
                        expected_vs_dataset_delta_norm = _safe_norm(expected_world_delta[env_idx, :3] - label_delta_xyz)
                        expected_vs_dataset_rot_norm = _safe_norm(expected_world_delta[env_idx, 3:6] - label_delta_rot)
                        expected_target_vs_dataset_next_ee_pos_norm = _safe_norm(
                            expected_target_pos[env_idx] - dataset_obs[label_next_row, :3]
                        )
                        actual_vs_dataset_next_ee_pos_norm = _safe_norm(
                            after_lowdim[env_idx, :3] - dataset_obs[label_next_row, :3]
                        )
                        dataset_label_delta_xyz = label_delta_xyz.astype(float).tolist()
                        dataset_label_delta_rot = label_delta_rot.astype(float).tolist()
                        executed_label_phase = _phase_name_for_row(phase_ids, phase_names, label_row)
                        executed_label_episode_step = _episode_step(label_row, episode_ends)
                    else:
                        label_next_row = -1
                        expected_vs_dataset_delta_norm = None
                        expected_vs_dataset_rot_norm = None
                        expected_target_vs_dataset_next_ee_pos_norm = None
                        actual_vs_dataset_next_ee_pos_norm = None
                        dataset_label_delta_xyz = None
                        dataset_label_delta_rot = None
                        executed_label_phase = ""
                        executed_label_episode_step = -1
                    tracking_target_row = int(tracking_target_rows[env_idx])
                    if tracking_target_row >= 0:
                        tracking_target_phase = _phase_name_for_row(phase_ids, phase_names, tracking_target_row)
                        tracking_target_episode_step = _episode_step(tracking_target_row, episode_ends)
                        tracking_target_error_before = _safe_norm(
                            before_lowdim[env_idx, :3] - dataset_obs[tracking_target_row, :3]
                        )
                        tracking_target_error_after = _safe_norm(
                            after_lowdim[env_idx, :3] - dataset_obs[tracking_target_row, :3]
                        )
                        tracking_target_cube_minus_ee_error_after = _safe_norm(
                            after_lowdim[env_idx, 14:17] - dataset_obs[tracking_target_row, 14:17]
                        )
                        tracking_target_ee_pos = dataset_obs[tracking_target_row, :3].astype(float).tolist()
                        tracking_target_cube_minus_ee = dataset_obs[tracking_target_row, 14:17].astype(float).tolist()
                    else:
                        tracking_target_phase = ""
                        tracking_target_episode_step = -1
                        tracking_target_error_before = None
                        tracking_target_error_after = None
                        tracking_target_cube_minus_ee_error_after = None
                        tracking_target_ee_pos = None
                        tracking_target_cube_minus_ee = None
                    if mode == "controller_target_hold" and controller_target_rows is not None and controller_target_holds is not None:
                        hold_before = int(controller_target_holds_before[env_idx])
                        target_error_for_advance = (
                            float(tracking_target_error_after)
                            if tracking_target_error_after is not None
                            else float("inf")
                        )
                        reason = ""
                        should_advance = False
                        if target_error_for_advance <= controller_target_tolerance:
                            reason = "tolerance"
                            should_advance = True
                        elif hold_before + 1 >= controller_target_max_hold:
                            reason = "max_hold"
                            should_advance = True
                        target_row_for_advance = int(controller_target_rows[env_idx])
                        _target_ep, _target_start, target_end = _episode_for_row(target_row_for_advance, episode_ends)
                        if should_advance and target_row_for_advance < target_end - 1:
                            controller_target_rows[env_idx] = int(target_row_for_advance + 1)
                            controller_target_holds[env_idx] = 0
                            controller_target_advanced[env_idx] = True
                            controller_target_advance_reasons[env_idx] = reason
                        else:
                            controller_target_holds[env_idx] = hold_before + 1
                            controller_target_advance_reasons[env_idx] = reason if should_advance else ""
                        controller_target_rows_after[env_idx] = int(controller_target_rows[env_idx])
                        controller_target_holds_after[env_idx] = int(controller_target_holds[env_idx])
                        if env_idx == 0:
                            controller_rollout_obs.append(before_lowdim[env_idx].astype(np.float32, copy=True))
                            controller_rollout_actions.append(exec_actions[env_idx].astype(np.float32, copy=True))
                            controller_rollout_phase_ids.append(
                                int(phase_ids[tracking_target_row]) if tracking_target_row >= 0 else int(phase_ids[current_row])
                            )
                            controller_rollout_target_rows.append(int(tracking_target_row))
                    if cosine is not None:
                        mode_cosines.append(float(cosine))
                    mode_distances.append(float(after_ee_to_cube[env_idx]))
                    record = {
                        "mode": mode,
                        "mode_index": mode_index,
                        "step": step,
                        "action_index": action_index,
                        "repeat_index": repeat_index,
                        "action_repeat": action_repeat,
                        "env_index": env_idx,
                        "demo_reset_applied": demo_reset_summary is not None,
                        "fixed_dataset_start": dataset_start_row is not None,
                        "nearest_initial_row": nearest_row,
                        "dataset_row": current_row,
                        "dataset_episode": _episode_for_row(current_row, episode_ends)[0],
                        "dataset_episode_step": _episode_step(current_row, episode_ends),
                        "dataset_phase": phase,
                        "executed_action_source": exec_action_sources[env_idx],
                        "executed_label_row": label_row,
                        "executed_label_offset": int(exec_label_offsets[env_idx]),
                        "executed_label_episode_step": int(executed_label_episode_step),
                        "executed_label_next_row": int(label_next_row),
                        "executed_label_phase": executed_label_phase,
                        "tracking_target_row": tracking_target_row,
                        "tracking_target_offset": int(tracking_target_offsets[env_idx]),
                        "tracking_target_episode_step": int(tracking_target_episode_step),
                        "tracking_target_phase": tracking_target_phase,
                        "tracking_target_error_before": tracking_target_error_before,
                        "tracking_target_error_after": tracking_target_error_after,
                        "tracking_target_cube_minus_ee_error_after": tracking_target_cube_minus_ee_error_after,
                        "tracking_target_ee_pos": tracking_target_ee_pos,
                        "tracking_target_cube_minus_ee": tracking_target_cube_minus_ee,
                        "controller_target_row_after": int(controller_target_rows_after[env_idx]),
                        "controller_target_hold_before": int(controller_target_holds_before[env_idx]),
                        "controller_target_hold_after": int(controller_target_holds_after[env_idx]),
                        "controller_target_advanced": bool(controller_target_advanced[env_idx]),
                        "controller_target_advance_reason": controller_target_advance_reasons[env_idx],
                        "controller_target_lookahead": controller_target_lookahead,
                        "controller_target_tolerance": controller_target_tolerance,
                        "controller_target_max_hold": controller_target_max_hold,
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
                        "raw_executed_action_before_multiplier": raw_exec_actions[env_idx].astype(float).tolist(),
                        "executed_action": exec_actions[env_idx].astype(float).tolist(),
                        "pose_action_multiplier": pose_action_multiplier,
                        "pose_action_clip_count": int(np.count_nonzero(clip_hits[env_idx])),
                        "pose_action_clip_fraction": float(np.count_nonzero(clip_hits[env_idx]) / 6.0),
                        "action_scale": action_scale_np.astype(float).tolist(),
                        "action_frame_robot_root_quat_wxyz": root_quat_wxyz_np.astype(float).tolist(),
                        "expected_world_delta_xyz": expected_world_delta[env_idx, :3].astype(float).tolist(),
                        "expected_world_delta_rot": expected_world_delta[env_idx, 3:6].astype(float).tolist(),
                        "expected_target_ee_pos": np.asarray(expected_target_pos[env_idx]).astype(float).tolist(),
                        "expected_target_ee_quat": np.asarray(expected_target_quat[env_idx]).astype(float).tolist(),
                        "actual_world_delta_xyz": actual_delta[env_idx].astype(float).tolist(),
                        "actual_world_delta_rot": np.asarray(actual_rot_delta[env_idx]).astype(float).tolist(),
                        "actual_vs_expected_xyz_cosine": cosine,
                        "actual_vs_expected_rot_cosine": rot_cosine,
                        "expected_xyz_delta_norm": expected_xyz_norm,
                        "actual_xyz_delta_norm": actual_xyz_norm,
                        "xyz_realization_ratio": _ratio(actual_xyz_norm, expected_xyz_norm),
                        "xyz_target_error_norm": xyz_target_error_norm,
                        "expected_rot_delta_norm": expected_rot_norm,
                        "actual_rot_delta_norm": actual_rot_norm,
                        "rot_realization_ratio": _ratio(actual_rot_norm, expected_rot_norm),
                        "rot_target_error_norm": quat_target_error_norm,
                        "dataset_label_delta_xyz": dataset_label_delta_xyz,
                        "dataset_label_delta_rot": dataset_label_delta_rot,
                        "expected_vs_dataset_delta_norm": expected_vs_dataset_delta_norm,
                        "expected_vs_dataset_rot_norm": expected_vs_dataset_rot_norm,
                        "expected_target_vs_dataset_next_ee_pos_norm": expected_target_vs_dataset_next_ee_pos_norm,
                        "actual_vs_dataset_next_ee_pos_norm": actual_vs_dataset_next_ee_pos_norm,
                        "label_t_gripper": float(labels_t[env_idx, 6]),
                        "dp_first_gripper": float(dp_seq[env_idx, 0, 6]),
                        "executed_gripper": float(exec_actions[env_idx, 6]),
                        "target_gripper_width_from_action": float(target_gripper_width[env_idx]),
                        "gripper_width_target_error_after": float(
                            after_lowdim[env_idx, 20] - target_gripper_width[env_idx]
                        ),
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
                                "pose_action_multiplier": pose_action_multiplier,
                                "action_repeat": action_repeat,
                                "action_index": action_index,
                                "repeat_index": repeat_index,
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
            first_target_close = next(
                (row["step"] for row in mode_rows if row.get("tracking_target_phase") == "close_fingers"), None
            )
            first_target_lift = next(
                (row["step"] for row in mode_rows if row.get("tracking_target_phase") == "lift_object"), None
            )
            last_row = mode_rows[-1]
            xyz_ratios = _finite_values(mode_rows, "xyz_realization_ratio")
            rot_ratios = _finite_values(mode_rows, "rot_realization_ratio")
            xyz_target_errors = _finite_values(mode_rows, "xyz_target_error_norm")
            dataset_next_errors = _finite_values(mode_rows, "actual_vs_dataset_next_ee_pos_norm")
            tracking_target_errors_before = _finite_values(mode_rows, "tracking_target_error_before")
            tracking_target_errors_after = _finite_values(mode_rows, "tracking_target_error_after")
            tracking_target_cme_errors_after = _finite_values(
                mode_rows, "tracking_target_cube_minus_ee_error_after"
            )
            gripper_width_errors = _finite_values(mode_rows, "gripper_width_target_error_after")
            pose_clip_fractions = _finite_values(mode_rows, "pose_action_clip_fraction")
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
                "first_tracking_target_close_phase_step": first_target_close,
                "first_tracking_target_lift_phase_step": first_target_lift,
                "mean_actual_vs_expected_xyz_cosine": float(np.mean(mode_cosines)) if mode_cosines else float("nan"),
                "mean_xyz_realization_ratio": float(np.mean(xyz_ratios)) if xyz_ratios else float("nan"),
                "median_xyz_realization_ratio": float(np.median(xyz_ratios)) if xyz_ratios else float("nan"),
                "mean_rot_realization_ratio": float(np.mean(rot_ratios)) if rot_ratios else float("nan"),
                "median_rot_realization_ratio": float(np.median(rot_ratios)) if rot_ratios else float("nan"),
                "mean_xyz_target_error_norm": float(np.mean(xyz_target_errors)) if xyz_target_errors else float("nan"),
                "median_xyz_target_error_norm": float(np.median(xyz_target_errors)) if xyz_target_errors else float("nan"),
                "mean_actual_vs_dataset_next_ee_pos_norm": (
                    float(np.mean(dataset_next_errors)) if dataset_next_errors else float("nan")
                ),
                "median_actual_vs_dataset_next_ee_pos_norm": (
                    float(np.median(dataset_next_errors)) if dataset_next_errors else float("nan")
                ),
                "mean_tracking_target_error_before": (
                    float(np.mean(tracking_target_errors_before)) if tracking_target_errors_before else float("nan")
                ),
                "median_tracking_target_error_before": (
                    float(np.median(tracking_target_errors_before)) if tracking_target_errors_before else float("nan")
                ),
                "mean_tracking_target_error_after": (
                    float(np.mean(tracking_target_errors_after)) if tracking_target_errors_after else float("nan")
                ),
                "median_tracking_target_error_after": (
                    float(np.median(tracking_target_errors_after)) if tracking_target_errors_after else float("nan")
                ),
                "mean_tracking_target_cube_minus_ee_error_after": (
                    float(np.mean(tracking_target_cme_errors_after))
                    if tracking_target_cme_errors_after
                    else float("nan")
                ),
                "mean_gripper_width_target_error_after": (
                    float(np.mean(gripper_width_errors)) if gripper_width_errors else float("nan")
                ),
                "max_pose_action_clip_fraction": (
                    float(np.max(pose_clip_fractions)) if pose_clip_fractions else float("nan")
                ),
                "mean_pose_action_clip_fraction": (
                    float(np.mean(pose_clip_fractions)) if pose_clip_fractions else float("nan")
                ),
                "first_dp_action": mode_first["dp_first_action"],
                "first_label_action": mode_first["label_t_action"],
                "first_executed_action": mode_first["executed_action"],
                "first_dp_gripper": float(mode_first["dp_first_gripper"]),
                "first_label_gripper": float(mode_first["label_t_gripper"]),
                "first_executed_gripper": float(mode_first["executed_gripper"]),
            }
            if mode == "controller_target_hold" and controller_rollout_obs:
                rollout_path = output_dir / "controller_target_hold_lowdim_rollout.npz"
                rollout_episode = {
                    "obs": np.stack(controller_rollout_obs, axis=0).astype(np.float32),
                    "action": np.stack(controller_rollout_actions, axis=0).astype(np.float32),
                    "phase_ids": np.asarray(controller_rollout_phase_ids, dtype=np.int32),
                }
                rollout_metadata = {
                    "source": "dextrah_controller_rollout_teacher_from_curobo_waypoints",
                    "curobo_validated_source": True,
                    "source_dataset": str(dataset_path),
                    "source_checkpoint_for_audit_only": str(checkpoint_path),
                    "source_demo_reset": demo_reset_summary,
                    "source_dataset_start": dataset_start_summary,
                    "source_phase_names": phase_names,
                    "source_target_rows_env0": [int(row) for row in controller_rollout_target_rows],
                    "controller_target_settings": controller_target_settings,
                    "action_convention": asdict(DEFAULT_DEXTRAH_ACTION_CONVENTION),
                    "notes": [
                        "Replay-only artifact generated by executing live residual actions in the DEXTRAH Isaac env.",
                        "This is not a BC readiness claim; inspect tracking, clipping, and support metrics before training.",
                    ],
                }
                rollout_summary = write_demo_dataset([rollout_episode], rollout_path, metadata=rollout_metadata)
                controller_rollout_datasets.append(
                    {
                        "mode": mode,
                        "dataset_path": str(rollout_path),
                        "metadata_path": str(rollout_path.with_suffix(rollout_path.suffix + ".metadata.json")),
                        "num_steps": int(rollout_summary["num_steps"]),
                        "target_row_first": int(controller_rollout_target_rows[0]),
                        "target_row_last": int(controller_rollout_target_rows[-1]),
                    }
                )
    finally:
        gym_env.close()

    csv_path = output_dir / "replay_steps.csv"
    json_path = output_dir / "replay_summary.json"
    plot_path = output_dir / "replay_motion.png"
    action_plot_path = output_dir / "action_realization_audit.png"
    report_path = output_dir / "replay_report.md"
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)
    _plot_action_audit(rows, action_plot_path)
    bad_modes = [
        mode
        for mode, payload in summaries.items()
        if payload["mean_actual_vs_expected_xyz_cosine"] < 0.25 or not np.isfinite(payload["mean_actual_vs_expected_xyz_cosine"])
    ]
    underrealized_modes = [
        mode
        for mode, payload in summaries.items()
        if (
            mode.startswith("dataset")
            and math.isfinite(payload.get("median_xyz_realization_ratio", float("nan")))
            and payload["median_xyz_realization_ratio"] < 0.50
        )
    ]
    verdict = (
        "Controller replay did not reliably follow the expected dataset action direction: " + ", ".join(bad_modes)
        if bad_modes
        else (
            "Controller follows the expected dataset action direction but under-realizes one-step action magnitude: "
            + ", ".join(underrealized_modes)
            if underrealized_modes
            else "Controller replay follows the expected dataset action direction and magnitude at this reset; continue debugging policy/live-state semantics."
        )
    )
    summary = {
        "dataset": str(dataset_path),
        "checkpoint": str(checkpoint_path),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "num_inference_steps": int(args_cli.num_inference_steps),
        "pose_action_multiplier": pose_action_multiplier,
        "action_repeat": action_repeat,
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "num_envs": int(args_cli.num_envs),
        "steps_requested": int(args_cli.steps),
        "modes": summaries,
        "demo_reset": demo_reset_summary,
        "action_audit": action_audit_summary,
        "controller_target_settings": controller_target_settings,
        "controller_rollout_datasets": controller_rollout_datasets,
        "dataset_start": dataset_start_summary
        or {"source": "nearest_live_row", "note": "first live observation selected label start independently per mode"},
        "verdict": verdict,
        "csv": str(csv_path),
        "json": str(json_path),
        "plot": str(plot_path),
        "action_audit_plot": str(action_plot_path),
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
