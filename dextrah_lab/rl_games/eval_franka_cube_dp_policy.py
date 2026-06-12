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
parser.add_argument("--checkpoint", type=str, required=True, help="Official Diffusion Policy .ckpt path.")
parser.add_argument("--diffusion_policy_root", type=str, default=None, help="Path to real-stanford/diffusion_policy.")
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--num_steps", type=int, default=240)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--num_inference_steps", type=int, default=2)
parser.add_argument(
    "--num_action_samples",
    type=int,
    default=1,
    help=(
        "Number of stochastic DP action sequences to sample and average at each policy call. "
        "Values >1 reduce DDPM sampling noise for BC diagnostics."
    ),
)
parser.add_argument(
    "--action_chunk_steps",
    type=int,
    default=1,
    help="Number of predicted DP action steps to execute before replanning. Default 1 preserves first-action replanning.",
)
parser.add_argument("--clip_actions", type=float, default=1.0)
parser.add_argument("--success_window", type=int, default=80)
parser.add_argument(
    "--success_timeout_override",
    type=float,
    default=None,
    help=(
        "Optional eval-only override for env_cfg.success_timeout. "
        "Use a value larger than the rollout horizon to diagnose post-success hold "
        "without auto-resetting on the task's normal success timeout."
    ),
)
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
parser.add_argument(
    "--support_dataset",
    type=str,
    default=None,
    help="Optional converted lowdim NPZ dataset for per-step nearest-demo support tracing.",
)
parser.add_argument(
    "--support_trace_path",
    type=str,
    default=None,
    help="Optional JSON/CSV prefix for nearest-demo support trace. Defaults under output_dir when --support_dataset is set.",
)
parser.add_argument(
    "--phase_progress_dataset",
    type=str,
    default=None,
    help=(
        "Optional 25D phase/progress NPZ used as a dataset-backed runtime "
        "feature schedule. Required for phase/progress-conditioned checkpoints."
    ),
)
parser.add_argument(
    "--phase_progress_episode",
    type=int,
    default=0,
    help="Episode index inside --phase_progress_dataset used for runtime phase/progress features.",
)
parser.add_argument(
    "--phase_progress_start_step",
    type=int,
    default=0,
    help="Episode-local row used as phase/progress step zero.",
)
parser.add_argument(
    "--phase_progress_mode",
    choices=["dataset", "contact_gated"],
    default="dataset",
    help=(
        "Runtime phase/progress strategy. 'dataset' replays the stored episode "
        "clock. 'contact_gated' keeps align/open features until live lowdim "
        "state is near close/lift support in the phase/progress dataset."
    ),
)
parser.add_argument(
    "--phase_close_support_distance_threshold",
    type=float,
    default=0.55,
    help="Contact-gated mode: maximum scaled distance to close_hold support before close phase is allowed.",
)
parser.add_argument(
    "--phase_lift_support_distance_threshold",
    type=float,
    default=0.75,
    help="Contact-gated mode: maximum scaled distance to lift support before lift phase is allowed.",
)
parser.add_argument(
    "--phase_lift_gripper_width_threshold",
    type=float,
    default=0.025,
    help="Contact-gated mode: gripper width in meters below which lift phase is allowed.",
)
parser.add_argument(
    "--action_correction_mode",
    choices=["disabled", "nearest_label_align_pose", "nearest_label_full_action"],
    default="disabled",
    help=(
        "Eval-only diagnostic action correction. 'nearest_label_align_pose' "
        "replaces/blends pose dims 0:6 with the nearest align_open support "
        "dataset label while runtime phase is align_open; gripper is left as "
        "the DP output. 'nearest_label_full_action' replaces/blends all seven "
        "action dims with the nearest support label, coupling pose and gripper "
        "to the same relabel row. These modes are not trained policy results."
    ),
)
parser.add_argument(
    "--action_correction_blend",
    type=float,
    default=1.0,
    help="Blend factor for eval-only action correction pose dims. 1.0 fully uses the support label pose.",
)
parser.add_argument(
    "--demo_reset_dataset",
    type=str,
    default=None,
    help="Optional converted lowdim NPZ dataset used to overwrite reset cube pose from a selected demo row.",
)
parser.add_argument(
    "--demo_reset_episode",
    type=int,
    default=0,
    help="Episode index for --demo_reset_dataset. Default 0.",
)
parser.add_argument(
    "--demo_reset_step",
    type=int,
    default=0,
    help="Episode-local row for --demo_reset_dataset. Default 0 matches the padded-history train reset.",
)
parser.add_argument(
    "--demo_reset_source_trajectory_json",
    type=str,
    default=None,
    help=(
        "Optional raw source trajectory JSON whose joint_position frame should be "
        "written during demo reset. This is used to match contact-aware relabel "
        "rollout robot state; without it demo reset only overwrites cube state."
    ),
)
parser.add_argument(
    "--demo_reset_source_frame",
    type=int,
    default=None,
    help="Frame index inside --demo_reset_source_trajectory_json to use for robot joint reset.",
)
parser.add_argument(
    "--demo_reset_joint_blend_alpha",
    type=float,
    default=1.0,
    help=(
        "Eval-only diagnostic blend from the environment's normal post-reset "
        "Franka joint state (0.0) to the selected source trajectory joint state "
        "(1.0). Requires --demo_reset_source_trajectory_json."
    ),
)
parser.add_argument(
    "--demo_reset_cube_pos_blend_alpha",
    type=float,
    default=1.0,
    help=(
        "Eval-only diagnostic blend from the environment's normal post-reset "
        "cube position (0.0) to the selected demo cube position (1.0). Cube "
        "orientation is normalized linearly between the two quaternions."
    ),
)
parser.add_argument(
    "--demo_reset_replicate_env0_joint_blend",
    action="store_true",
    default=False,
    help=(
        "Eval-only diagnostic for batched exact-demo reset: after computing the "
        "normal/source joint blend for env0, copy that applied joint state to "
        "all envs. This avoids averaging over per-env random normal reset "
        "joints when NUM_ENVS > 1."
    ),
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
from dextrah_lab.offline_dp_bc.analyze_policy_trace import POSITION_FEATURE_IDX
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    ContactGatedPhaseProgressProvider,
    DatasetBackedPhaseProgressProvider,
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_LOWDIM_OBS_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    PHASE_PROGRESS_FEATURE_NAMES,
    LowdimObsHistory,
    extract_lowdim_obs_from_ppo_obs,
    predict_action_sequence_from_ppo_obs,
)
from dextrah_lab.offline_dp_bc.trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


DEFAULT_CAMERA_EYE = (-0.10, -0.78, 1.42)
DEFAULT_CAMERA_TARGET = (-0.41, -0.10, 0.82)
CONTACT_RELABEL_PHASE_ORDER = ("align_open", "close_hold", "lift")


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


def _policy_global_obs_dim(policy: Any) -> int | None:
    global_cond_dim = getattr(getattr(policy, "model", None), "global_cond_dim", None)
    if global_cond_dim is None:
        global_cond_dim = getattr(policy, "global_cond_dim", None)
    if global_cond_dim is None:
        return None
    n_obs_steps = int(getattr(policy, "n_obs_steps", 0))
    if n_obs_steps <= 0:
        return None
    if int(global_cond_dim) % n_obs_steps != 0:
        return None
    return int(global_cond_dim) // n_obs_steps


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


def _phase_names_for_npz(data: Any, phase_ids: np.ndarray, obs: np.ndarray | None = None) -> list[str]:
    """Decode phase ids for both original converted demos and relabel rollouts."""

    unique = set(int(v) for v in np.unique(phase_ids))
    data_files = set(getattr(data, "files", ()))
    has_phase_progress = (
        "phase_progress_features" in data_files
        or (obs is not None and int(obs.shape[-1]) > FRANKA_CUBE_LOWDIM_OBS_DIM)
    )
    if has_phase_progress and unique and unique.issubset({-1, 0, 1, 2}):
        return list(CONTACT_RELABEL_PHASE_ORDER)
    if "rollout_ids" in data_files and unique and unique.issubset({-1, 0, 1, 2}):
        return list(CONTACT_RELABEL_PHASE_ORDER)
    # trajectory_to_episode writes phase ids from sorted(set(phases)).
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _phase_name_from_id(phase_names: list[str], phase_id: int) -> str:
    if phase_names == list(CONTACT_RELABEL_PHASE_ORDER) and int(phase_id) < 0:
        phase_id = 0
    return str(phase_names[int(phase_id)])


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    episode_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    episode_idx = min(max(episode_idx, 0), int(episode_ends.shape[0] - 1))
    start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    end = int(episode_ends[episode_idx])
    return episode_idx, start, end


def _support_dataset_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = np.load(path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    feature_std = np.maximum(obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4).astype(np.float32)
    return {
        "path": str(path),
        "obs": obs,
        "action": action,
        "phase_ids": phase_ids,
        "episode_ends": episode_ends,
        "phase_names": _phase_names_for_npz(data, phase_ids, obs),
        "feature_std": feature_std,
    }


def _demo_reset_payload(
    path: Path | None,
    episode: int,
    episode_step: int,
    *,
    source_trajectory_json: Path | None = None,
    source_frame: int | None = None,
) -> dict[str, Any] | None:
    if path is None:
        return None
    data = np.load(path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if episode_ends.size == 0:
        raise ValueError(f"Demo reset dataset has no episodes: {path}")
    episode_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    episode_start = 0 if episode_idx == 0 else int(episode_ends[episode_idx - 1])
    episode_end = int(episode_ends[episode_idx])
    local_step = int(np.clip(int(episode_step), 0, max(0, episode_end - episode_start - 1)))
    row_idx = int(episode_start + local_step)
    phase_names = _phase_names_for_npz(data, phase_ids, obs)
    phase_id = int(phase_ids[row_idx])
    payload: dict[str, Any] = {
        "path": str(path),
        "obs": obs,
        "action": action,
        "phase_ids": phase_ids,
        "episode_ends": episode_ends,
        "phase_names": phase_names,
        "episode": episode_idx,
        "episode_start": episode_start,
        "episode_end": episode_end,
        "episode_step": local_step,
        "row": row_idx,
        "phase": _phase_name_from_id(phase_names, phase_id),
        "target_obs": obs[row_idx].copy(),
        "target_action": action[row_idx].copy(),
    }
    if source_trajectory_json is not None:
        source = json.loads(source_trajectory_json.read_text(encoding="utf-8"))
        frames = source.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"Source trajectory has no frames: {source_trajectory_json}")
        frame_idx = int(source_frame if source_frame is not None else local_step)
        frame_idx = int(np.clip(frame_idx, 0, len(frames) - 1))
        frame = frames[frame_idx]
        if not isinstance(frame, dict) or "joint_position" not in frame:
            raise ValueError(f"Source trajectory frame {frame_idx} has no joint_position: {source_trajectory_json}")
        raw_q = np.asarray(frame["joint_position"], dtype=np.float32)
        if raw_q.ndim != 1:
            raise ValueError(f"Source trajectory joint_position must be 1D, got {raw_q.shape}")
        payload.update(
            {
                "source_trajectory_json": str(source_trajectory_json),
                "source_frame": int(frame_idx),
                "source_joint_position": raw_q.copy(),
            }
        )
    return payload


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
        raise ValueError(
            f"Cannot map source joint_position dim {raw_q_tensor.shape[1]} to "
            f"{joint_pos.shape[1]} env joints ({arm_count} arm, {finger_count} fingers)"
        )
    return torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _reset_policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    policy_obs = obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict
    return policy_obs


def _apply_demo_reset(task_env: Any, demo_reset: dict[str, Any]) -> tuple[torch.Tensor, dict[str, Any]]:
    """Overwrite reset state from a converted demo row.

    By default this only writes cube pose/goal. If ``source_joint_position`` is
    present, the Franka articulation and controller targets are also reset to
    the raw source trajectory joint state used by the contact-aware relabeler.
    """

    env_ids = task_env._robot._ALL_INDICES
    env_ids = torch.as_tensor(env_ids, device=task_env.device, dtype=torch.long)
    num_ids = int(env_ids.numel())
    target_obs = np.asarray(demo_reset["target_obs"], dtype=np.float32)
    target_obs_base = target_obs[:FRANKA_CUBE_LOWDIM_OBS_DIM]
    joint_blend_alpha = float(np.clip(float(args_cli.demo_reset_joint_blend_alpha), 0.0, 1.0))
    cube_pos_blend_alpha = float(np.clip(float(args_cli.demo_reset_cube_pos_blend_alpha), 0.0, 1.0))
    normal_policy_obs = _reset_policy_obs_from_task_env(task_env)
    normal_lowdim = extract_lowdim_obs_from_ppo_obs(normal_policy_obs).detach().float().cpu().numpy()
    normal0 = normal_lowdim[0]
    robot_reset_summary: dict[str, Any] = {
        "source_joint_reset_available": "source_joint_position" in demo_reset,
        "source_trajectory_json": demo_reset.get("source_trajectory_json"),
        "source_frame": demo_reset.get("source_frame"),
        "joint_blend_alpha": joint_blend_alpha,
        "cube_pos_blend_alpha": cube_pos_blend_alpha,
        "normal_lowdim_before_reset_env0": normal0.astype(float).tolist(),
        "normal_cube_pos_before_reset_env0": normal0[7:10].astype(float).tolist(),
        "normal_cube_minus_ee_before_reset_env0": normal0[14:17].astype(float).tolist(),
        "normal_gripper_width_before_reset_env0": float(normal0[20]),
    }
    if "source_joint_position" in demo_reset:
        raw_q = np.asarray(demo_reset["source_joint_position"], dtype=np.float32)
        source_joint_pos = _map_source_joint_to_env(task_env, raw_q, env_ids)
        normal_joint_pos = task_env._robot.data.joint_pos[env_ids].detach().clone()
        joint_pos = normal_joint_pos + joint_blend_alpha * (source_joint_pos - normal_joint_pos)
        joint_pos = torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)
        if args_cli.demo_reset_replicate_env0_joint_blend and num_ids > 1:
            joint_pos[:] = joint_pos[0].unsqueeze(0)
        joint_vel = torch.zeros_like(joint_pos)
        task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
        task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        task_env.robot_dof_targets[env_ids] = joint_pos
        task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
        task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]
        robot_reset_summary.update(
            {
                "source_joint_position_raw_dim": int(raw_q.shape[0]),
                "normal_joint_position_env0": normal_joint_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
                "source_joint_position_env0": source_joint_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
                "applied_joint_position_env0": joint_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
                "replicate_env0_joint_blend": bool(args_cli.demo_reset_replicate_env0_joint_blend),
                "applied_joint_l2_from_source_env0": float(
                    torch.linalg.vector_norm((joint_pos[0] - source_joint_pos[0]).detach().float()).cpu()
                ),
                "applied_joint_l2_from_normal_env0": float(
                    torch.linalg.vector_norm((joint_pos[0] - normal_joint_pos[0]).detach().float()).cpu()
                ),
            }
        )

    source_cube_pos = torch.as_tensor(target_obs_base[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    source_cube_quat = torch.as_tensor(target_obs_base[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    normal_cube_pos = torch.as_tensor(normal_lowdim[:, 7:10], dtype=torch.float32, device=task_env.device)
    normal_cube_quat = torch.as_tensor(normal_lowdim[:, 10:14], dtype=torch.float32, device=task_env.device)
    target_cube_pos = normal_cube_pos + cube_pos_blend_alpha * (source_cube_pos - normal_cube_pos)
    quat_dot = torch.sum(normal_cube_quat * source_cube_quat, dim=1, keepdim=True)
    source_cube_quat = torch.where(quat_dot < 0.0, -source_cube_quat, source_cube_quat)
    target_cube_quat = normal_cube_quat + cube_pos_blend_alpha * (source_cube_quat - normal_cube_quat)
    target_cube_quat = torch.nn.functional.normalize(target_cube_quat, dim=1)
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
    diff_all = live_lowdim - target_obs_base.reshape(1, -1)
    if "applied_joint_position_env0" in robot_reset_summary:
        joint_after = task_env._robot.data.joint_pos[env_ids].detach().float().cpu().numpy()
        applied = np.asarray(robot_reset_summary["applied_joint_position_env0"], dtype=np.float32)
        robot_reset_summary["joint_linf_diff_after_write_env0"] = float(np.max(np.abs(joint_after[0] - applied)))
    summary = {
        "dataset": str(demo_reset["path"]),
        "episode": int(demo_reset["episode"]),
        "episode_step": int(demo_reset["episode_step"]),
        "row": int(demo_reset["row"]),
        "phase": str(demo_reset["phase"]),
        "joint_blend_alpha": joint_blend_alpha,
        "cube_pos_blend_alpha": cube_pos_blend_alpha,
        "target_cube_pos": target_obs_base[7:10].astype(float).tolist(),
        "target_cube_quat": target_obs_base[10:14].astype(float).tolist(),
        "target_cube_minus_ee": target_obs_base[14:17].astype(float).tolist(),
        "target_gripper_width": float(target_obs_base[20]),
        "applied_cube_pos_env0": target_cube_pos[0].detach().float().cpu().numpy().astype(float).tolist(),
        "applied_cube_quat_env0": target_cube_quat[0].detach().float().cpu().numpy().astype(float).tolist(),
        "live_lowdim_after_reset_env0": live0.astype(float).tolist(),
        "live_cube_pos_after_reset_env0": live0[7:10].astype(float).tolist(),
        "live_cube_minus_ee_after_reset_env0": live0[14:17].astype(float).tolist(),
        "lowdim_linf_diff_env0": float(np.max(np.abs(diff))),
        "lowdim_l2_diff_env0": float(np.linalg.norm(diff)),
        "cube_pos_l2_diff_env0": float(np.linalg.norm(diff[7:10])),
        "cube_minus_ee_l2_diff_env0": float(np.linalg.norm(diff[14:17])),
        "lowdim_l2_diff_max_all_envs": float(np.linalg.norm(diff_all, axis=1).max()),
        "cube_pos_l2_diff_max_all_envs": float(np.linalg.norm(diff_all[:, 7:10], axis=1).max()),
        "cube_minus_ee_l2_diff_max_all_envs": float(np.linalg.norm(diff_all[:, 14:17], axis=1).max()),
        "cube_pos_l2_from_demo_env0": float(np.linalg.norm(live0[7:10] - target_obs_base[7:10])),
        "cube_pos_l2_from_normal_env0": float(np.linalg.norm(live0[7:10] - normal0[7:10])),
        "cube_minus_ee_l2_from_demo_env0": float(np.linalg.norm(live0[14:17] - target_obs_base[14:17])),
        "cube_minus_ee_l2_from_normal_env0": float(np.linalg.norm(live0[14:17] - normal0[14:17])),
    }
    summary.update(robot_reset_summary)
    return policy_obs, summary


def _nearest_support_row(support: dict[str, Any], lowdim_obs: np.ndarray) -> tuple[int, float]:
    obs = support["obs"]
    feature_std = support["feature_std"]
    distances = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - lowdim_obs[POSITION_FEATURE_IDX]) / feature_std) ** 2).mean(axis=1))
    idx = int(np.argmin(distances))
    return idx, float(distances[idx])


def _nearest_support_row_for_phase(
    support: dict[str, Any],
    lowdim_obs: np.ndarray,
    phase_name: str,
) -> tuple[int, float]:
    obs = support["obs"]
    phase_ids = support["phase_ids"]
    feature_std = support["feature_std"]
    distances = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - lowdim_obs[POSITION_FEATURE_IDX]) / feature_std) ** 2).mean(axis=1))
    if support["phase_names"] == list(CONTACT_RELABEL_PHASE_ORDER) and phase_name == "align_open":
        mask = np.logical_or(phase_ids == 0, phase_ids < 0)
    else:
        try:
            phase_id = list(support["phase_names"]).index(str(phase_name))
            mask = phase_ids == phase_id
        except ValueError:
            mask = np.ones_like(phase_ids, dtype=bool)
    if np.any(mask):
        masked_distances = np.where(mask, distances, np.inf)
        idx = int(np.argmin(masked_distances))
    else:
        idx = int(np.argmin(distances))
    return idx, float(distances[idx])


def _runtime_phase_name(lowdim_obs: np.ndarray) -> str:
    if lowdim_obs.shape[0] < FRANKA_CUBE_LOWDIM_OBS_DIM + 3:
        return "unknown"
    phase_idx = int(np.argmax(lowdim_obs[21:24]))
    return ("align_open", "close_hold", "lift")[phase_idx]


def _apply_eval_action_correction(
    action_np: np.ndarray,
    *,
    lowdim_obs: np.ndarray,
    support: dict[str, Any] | None,
    mode: str,
    blend: float,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Apply opt-in eval-only action corrections for diagnostics."""

    mode = str(mode)
    blend = float(np.clip(float(blend), 0.0, 1.0))
    corrected = np.asarray(action_np, dtype=np.float32).copy()
    records: list[dict[str, Any]] = []
    if mode == "disabled":
        for env_idx in range(corrected.shape[0]):
            records.append({"mode": mode, "applied": False, "runtime_phase": _runtime_phase_name(lowdim_obs[env_idx])})
        return corrected, records
    if support is None:
        raise RuntimeError(f"action_correction_mode={mode} requires --support_dataset")

    for env_idx in range(corrected.shape[0]):
        runtime_phase = _runtime_phase_name(lowdim_obs[env_idx])
        original = corrected[env_idx].copy()
        record: dict[str, Any] = {
            "mode": mode,
            "applied": False,
            "runtime_phase": runtime_phase,
            "blend": blend,
            "original_action": original.astype(float).tolist(),
        }
        if mode == "nearest_label_align_pose" and runtime_phase == "align_open":
            nearest_idx, nearest_distance = _nearest_support_row_for_phase(support, lowdim_obs[env_idx], "align_open")
            label = np.asarray(support["action"][nearest_idx], dtype=np.float32)
            corrected[env_idx, :6] = (1.0 - blend) * corrected[env_idx, :6] + blend * label[:6]
            phase_id = int(support["phase_ids"][nearest_idx])
            record.update(
                {
                    "applied": True,
                    "nearest_demo_row": int(nearest_idx),
                    "nearest_demo_phase": _phase_name_from_id(support["phase_names"], phase_id),
                    "nearest_demo_distance": float(nearest_distance),
                    "label_action": label.astype(float).tolist(),
                    "pose_l2_before": float(np.linalg.norm(original[:6] - label[:6])),
                    "pose_l2_after": float(np.linalg.norm(corrected[env_idx, :6] - label[:6])),
                }
            )
        elif mode == "nearest_label_full_action":
            nearest_idx, nearest_distance = _nearest_support_row(support, lowdim_obs[env_idx])
            label = np.asarray(support["action"][nearest_idx], dtype=np.float32)
            corrected[env_idx, :] = (1.0 - blend) * corrected[env_idx, :] + blend * label
            phase_id = int(support["phase_ids"][nearest_idx])
            nearest_obs = np.asarray(support["obs"][nearest_idx], dtype=np.float32)
            record.update(
                {
                    "applied": True,
                    "nearest_demo_row": int(nearest_idx),
                    "nearest_demo_phase": _phase_name_from_id(support["phase_names"], phase_id),
                    "nearest_demo_distance": float(nearest_distance),
                    "nearest_demo_phase_progress": (
                        nearest_obs[21:25].astype(float).tolist() if nearest_obs.shape[0] >= 25 else None
                    ),
                    "label_action": label.astype(float).tolist(),
                    "pose_l2_before": float(np.linalg.norm(original[:6] - label[:6])),
                    "pose_l2_after": float(np.linalg.norm(corrected[env_idx, :6] - label[:6])),
                    "action_l2_before": float(np.linalg.norm(original - label)),
                    "action_l2_after": float(np.linalg.norm(corrected[env_idx] - label)),
                    "gripper_before": float(original[6]),
                    "gripper_after": float(corrected[env_idx, 6]),
                    "gripper_label": float(label[6]),
                }
            )
        record["corrected_action"] = corrected[env_idx].astype(float).tolist()
        records.append(record)
    return corrected, records


def _phase_min_distances(support: dict[str, Any], lowdim_obs: np.ndarray) -> dict[str, float]:
    obs = support["obs"]
    phase_ids = support["phase_ids"]
    feature_std = support["feature_std"]
    distances = np.sqrt((((obs[:, POSITION_FEATURE_IDX] - lowdim_obs[POSITION_FEATURE_IDX]) / feature_std) ** 2).mean(axis=1))
    out: dict[str, float] = {}
    for phase_id, phase_name in enumerate(support["phase_names"]):
        if support["phase_names"] == list(CONTACT_RELABEL_PHASE_ORDER) and phase_id == 0:
            mask = np.logical_or(phase_ids == phase_id, phase_ids < 0)
        else:
            mask = phase_ids == phase_id
        if np.any(mask):
            out[str(phase_name)] = float(np.min(distances[mask]))
    return out


def _history_step_payload(history: LowdimObsHistory, env_index: int) -> tuple[list[int], int]:
    steps = np.asarray(history._step_history[int(env_index)], dtype=np.int64)
    valid_steps = steps[steps >= 0]
    gap = int(valid_steps[-1] - valid_steps[-2]) if valid_steps.shape[0] >= 2 else 0
    return steps.astype(int).tolist(), gap


def _collect_support_record(
    *,
    support: dict[str, Any],
    step: int,
    env_index: int,
    lowdim_obs: np.ndarray,
    action: np.ndarray | None,
    reward_mean: float | None,
    task_metrics: dict[str, float | None],
    history: LowdimObsHistory,
    action_queue_len_after_pop: int,
    action_correction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nearest_idx, nearest_distance = _nearest_support_row(support, lowdim_obs)
    episode_idx, episode_start, _episode_end = _episode_for_row(nearest_idx, support["episode_ends"])
    phase_id = int(support["phase_ids"][nearest_idx])
    phase_name = _phase_name_from_id(support["phase_names"], phase_id)
    nearest_obs = support["obs"][nearest_idx]
    nearest_action = support["action"][nearest_idx]
    phase_distances = _phase_min_distances(support, lowdim_obs)
    history_steps, history_gap = _history_step_payload(history, env_index)
    live_cme = np.asarray(lowdim_obs[14:17], dtype=np.float32)
    nearest_cme = np.asarray(nearest_obs[14:17], dtype=np.float32)
    action = np.asarray(action, dtype=np.float32) if action is not None else np.full(FRANKA_CUBE_ACTION_DIM, np.nan, dtype=np.float32)
    record = {
        "step": int(step),
        "env_index": int(env_index),
        "nearest_demo_row": int(nearest_idx),
        "nearest_demo_episode": int(episode_idx),
        "nearest_demo_episode_step": int(nearest_idx - episode_start),
        "nearest_demo_phase": phase_name,
        "nearest_demo_distance": float(nearest_distance),
        "nearest_demo_action_gripper": float(nearest_action[6]),
        "nearest_demo_gripper_width": float(nearest_obs[20]),
        "live_phase_progress": (
            np.asarray(lowdim_obs[21:25], dtype=np.float32).astype(float).tolist()
            if lowdim_obs.shape[0] >= 25
            else None
        ),
        "nearest_demo_phase_progress": (
            np.asarray(nearest_obs[21:25], dtype=np.float32).astype(float).tolist()
            if nearest_obs.shape[0] >= 25
            else None
        ),
        "nearest_demo_cube_minus_ee": nearest_cme.astype(float).tolist(),
        "live_cube_minus_ee": live_cme.astype(float).tolist(),
        "live_to_nearest_demo_cube_minus_ee_norm": float(np.linalg.norm(live_cme - nearest_cme)),
        "live_ee_pos": np.asarray(lowdim_obs[0:3], dtype=np.float32).astype(float).tolist(),
        "live_cube_pos": np.asarray(lowdim_obs[7:10], dtype=np.float32).astype(float).tolist(),
        "live_gripper_width": float(lowdim_obs[20]),
        "ee_to_cube_dist": task_metrics.get("ee_to_cube_dist"),
        "finger_center_to_cube_dist": task_metrics.get("finger_center_to_cube_dist"),
        "cube_lift_height": task_metrics.get("cube_lift_height"),
        "reward_mean": reward_mean,
        "executed_action": action.astype(float).tolist(),
        "executed_gripper": float(action[6]),
        "history_steps": history_steps,
        "history_step_gap": int(history_gap),
        "action_queue_len_after_pop": int(action_queue_len_after_pop),
        "phase_min_distances": phase_distances,
    }
    if action_correction is not None:
        record["action_correction"] = action_correction
        record["action_correction_mode"] = action_correction.get("mode")
        record["action_correction_applied"] = bool(action_correction.get("applied", False))
        record["action_correction_runtime_phase"] = action_correction.get("runtime_phase")
        record["action_correction_nearest_demo_row"] = action_correction.get("nearest_demo_row")
        record["action_correction_nearest_demo_phase"] = action_correction.get("nearest_demo_phase")
        record["action_correction_nearest_demo_distance"] = action_correction.get("nearest_demo_distance")
        record["action_correction_pose_l2_before"] = action_correction.get("pose_l2_before")
        record["action_correction_pose_l2_after"] = action_correction.get("pose_l2_after")
        record["action_correction_action_l2_before"] = action_correction.get("action_l2_before")
        record["action_correction_action_l2_after"] = action_correction.get("action_l2_after")
        record["action_correction_gripper_before"] = action_correction.get("gripper_before")
        record["action_correction_gripper_after"] = action_correction.get("gripper_after")
        record["action_correction_gripper_label"] = action_correction.get("gripper_label")
    return record


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_eval_config(path: Path, *, checkpoint: Path, output_dir: Path, metrics_path: Path) -> None:
    config = {
        "args": _json_safe(vars(args_cli)),
        "checkpoint": str(checkpoint),
        "output_dir": str(output_dir),
        "metrics_path": str(metrics_path),
        "diffusion_policy_root": args_cli.diffusion_policy_root,
        "action_convention": "7D DEXTRAH relative EE pose plus gripper, +1 open / -1 close",
        "no_learning": True,
    }
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_support_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "step",
        "env_index",
        "nearest_demo_row",
        "nearest_demo_episode",
        "nearest_demo_episode_step",
        "nearest_demo_phase",
        "nearest_demo_distance",
        "nearest_demo_action_gripper",
        "nearest_demo_gripper_width",
        "live_phase_progress",
        "nearest_demo_phase_progress",
        "live_to_nearest_demo_cube_minus_ee_norm",
        "live_gripper_width",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "cube_lift_height",
        "reward_mean",
        "executed_gripper",
        "history_step_gap",
        "action_queue_len_after_pop",
        "live_cube_minus_ee",
        "nearest_demo_cube_minus_ee",
        "executed_action",
        "history_steps",
        "phase_min_distances",
        "action_correction_mode",
        "action_correction_applied",
        "action_correction_runtime_phase",
        "action_correction_nearest_demo_row",
        "action_correction_nearest_demo_phase",
        "action_correction_nearest_demo_distance",
        "action_correction_pose_l2_before",
        "action_correction_pose_l2_after",
        "action_correction_action_l2_before",
        "action_correction_action_l2_after",
        "action_correction_gripper_before",
        "action_correction_gripper_after",
        "action_correction_gripper_label",
        "action_correction",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            for key, value in list(row.items()):
                if isinstance(value, (list, dict)):
                    row[key] = json.dumps(_json_safe(value), sort_keys=True)
            writer.writerow(row)


def _lowdim_components(lowdim_obs: np.ndarray) -> dict[str, Any]:
    components = {
        "ee_pos": lowdim_obs[0:3].astype(float).tolist(),
        "ee_quat": lowdim_obs[3:7].astype(float).tolist(),
        "cube_pos": lowdim_obs[7:10].astype(float).tolist(),
        "cube_quat": lowdim_obs[10:14].astype(float).tolist(),
        "cube_minus_ee": lowdim_obs[14:17].astype(float).tolist(),
        "cube_goal_delta": lowdim_obs[17:20].astype(float).tolist(),
        "gripper_width": float(lowdim_obs[20]),
    }
    if lowdim_obs.shape[0] >= 25:
        components["phase_progress"] = {
            name: float(lowdim_obs[21 + idx]) for idx, name in enumerate(PHASE_PROGRESS_FEATURE_NAMES)
        }
    return components


def _trace_policy_call(
    *,
    trace_records: list[dict[str, Any]],
    max_calls: int,
    step: int,
    env_index: int,
    history: LowdimObsHistory,
    action_seq: np.ndarray,
    chunk_steps: int,
) -> None:
    if max_calls <= 0 or len(trace_records) >= max_calls:
        return
    env_index = min(max(0, int(env_index)), int(action_seq.shape[0]) - 1)
    lowdim_np = np.asarray(history._history[:, -1], dtype=np.float32)
    action_chunk = np.asarray(action_seq[env_index, :chunk_steps], dtype=np.float32)
    history_steps = getattr(history, "_step_history", None)
    if history_steps is not None:
        history_steps_env = np.asarray(history_steps[env_index], dtype=np.int64)
        valid_steps = history_steps_env[history_steps_env >= 0]
        history_step_gap = int(valid_steps[-1] - valid_steps[-2]) if valid_steps.shape[0] >= 2 else 0
        history_steps_payload = history_steps_env.astype(int).tolist()
    else:
        history_step_gap = None
        history_steps_payload = None
    trace_records.append(
        {
            "policy_call_index": len(trace_records),
            "step": int(step),
            "env_index": int(env_index),
            "lowdim_obs_dim": int(lowdim_np.shape[1]),
            "lowdim_obs": lowdim_np[env_index].astype(float).tolist(),
            "lowdim_components": _lowdim_components(lowdim_np[env_index]),
            "history_after_push": history._history[env_index].astype(float).tolist(),
            "history_steps_after_push": history_steps_payload,
            "history_step_gap": history_step_gap,
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
    support_dataset_path = Path(args_cli.support_dataset).expanduser().resolve() if args_cli.support_dataset else None
    phase_progress_dataset_path = (
        Path(args_cli.phase_progress_dataset).expanduser().resolve() if args_cli.phase_progress_dataset else None
    )
    support_trace_path = (
        Path(args_cli.support_trace_path).expanduser().resolve()
        if args_cli.support_trace_path
        else (output_dir / "support_trace.json" if support_dataset_path is not None else None)
    )
    support_trace_csv_path = support_trace_path.with_suffix(".csv") if support_trace_path is not None else None
    if support_trace_path is not None:
        support_trace_path.parent.mkdir(parents=True, exist_ok=True)
    demo_reset_dataset_path = (
        Path(args_cli.demo_reset_dataset).expanduser().resolve() if args_cli.demo_reset_dataset else None
    )
    demo_reset_source_trajectory_path = (
        Path(args_cli.demo_reset_source_trajectory_json).expanduser().resolve()
        if args_cli.demo_reset_source_trajectory_json
        else None
    )
    video_folder = Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"

    checkpoint = Path(args_cli.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if phase_progress_dataset_path is not None and not phase_progress_dataset_path.is_file():
        raise FileNotFoundError(phase_progress_dataset_path)
    if demo_reset_dataset_path is not None and not demo_reset_dataset_path.is_file():
        raise FileNotFoundError(demo_reset_dataset_path)
    if demo_reset_source_trajectory_path is not None and not demo_reset_source_trajectory_path.is_file():
        raise FileNotFoundError(demo_reset_source_trajectory_path)
    eval_config_path = output_dir / "eval_config.json"
    _write_eval_config(eval_config_path, checkpoint=checkpoint, output_dir=output_dir, metrics_path=metrics_path)
    _stage(
        "start",
        output_dir=str(output_dir),
        metrics_path=str(metrics_path),
        checkpoint=str(checkpoint),
        checkpoint_size=checkpoint.stat().st_size,
        eval_config_path=str(eval_config_path),
        num_envs=int(args_cli.num_envs),
        num_steps=int(args_cli.num_steps),
        debug_policy_trace_path=str(debug_trace_path) if debug_trace_path is not None else None,
        debug_policy_trace_max_calls=debug_trace_max_calls,
        support_dataset=str(support_dataset_path) if support_dataset_path is not None else None,
        support_trace_path=str(support_trace_path) if support_trace_path is not None else None,
        phase_progress_dataset=str(phase_progress_dataset_path) if phase_progress_dataset_path is not None else None,
        phase_progress_episode=int(args_cli.phase_progress_episode),
        phase_progress_start_step=int(args_cli.phase_progress_start_step),
        phase_progress_mode=str(args_cli.phase_progress_mode),
        num_action_samples=max(1, int(args_cli.num_action_samples)),
        phase_close_support_distance_threshold=float(args_cli.phase_close_support_distance_threshold),
        phase_lift_support_distance_threshold=float(args_cli.phase_lift_support_distance_threshold),
        phase_lift_gripper_width_threshold=float(args_cli.phase_lift_gripper_width_threshold),
        action_correction_mode=str(args_cli.action_correction_mode),
        action_correction_blend=float(args_cli.action_correction_blend),
        demo_reset_dataset=str(demo_reset_dataset_path) if demo_reset_dataset_path is not None else None,
        demo_reset_episode=int(args_cli.demo_reset_episode),
        demo_reset_step=int(args_cli.demo_reset_step),
        demo_reset_source_trajectory_json=(
            str(demo_reset_source_trajectory_path) if demo_reset_source_trajectory_path is not None else None
        ),
        demo_reset_source_frame=args_cli.demo_reset_source_frame,
        demo_reset_joint_blend_alpha=float(args_cli.demo_reset_joint_blend_alpha),
        demo_reset_cube_pos_blend_alpha=float(args_cli.demo_reset_cube_pos_blend_alpha),
    )
    support_dataset = _support_dataset_payload(support_dataset_path)
    if args_cli.action_correction_mode != "disabled" and support_dataset is None:
        raise RuntimeError("--action_correction_mode requires --support_dataset")
    if support_dataset is not None:
        _stage(
            "support_dataset_loaded",
            dataset=str(support_dataset_path),
            obs_shape=list(support_dataset["obs"].shape),
            action_shape=list(support_dataset["action"].shape),
        )
    phase_progress_provider = None
    if phase_progress_dataset_path is not None:
        if args_cli.phase_progress_mode == "dataset":
            phase_progress_provider = DatasetBackedPhaseProgressProvider.from_npz(
                phase_progress_dataset_path,
                episode_index=int(args_cli.phase_progress_episode),
                start_step=int(args_cli.phase_progress_start_step),
            )
        elif args_cli.phase_progress_mode == "contact_gated":
            phase_progress_provider = ContactGatedPhaseProgressProvider(
                dataset_path=phase_progress_dataset_path,
                episode_index=int(args_cli.phase_progress_episode),
                start_step=int(args_cli.phase_progress_start_step),
                close_support_distance_threshold=float(args_cli.phase_close_support_distance_threshold),
                lift_support_distance_threshold=float(args_cli.phase_lift_support_distance_threshold),
                lift_gripper_width_threshold=float(args_cli.phase_lift_gripper_width_threshold),
            )
        else:
            raise ValueError(f"Unsupported phase_progress_mode: {args_cli.phase_progress_mode}")
    if phase_progress_provider is not None:
        _stage("phase_progress_provider_loaded", **phase_progress_provider.summary())
    demo_reset = _demo_reset_payload(
        demo_reset_dataset_path,
        int(args_cli.demo_reset_episode),
        int(args_cli.demo_reset_step),
        source_trajectory_json=demo_reset_source_trajectory_path,
        source_frame=args_cli.demo_reset_source_frame,
    )
    if demo_reset is not None:
        _stage(
            "demo_reset_loaded",
            dataset=str(demo_reset_dataset_path),
            episode=int(demo_reset["episode"]),
            episode_step=int(demo_reset["episode_step"]),
            row=int(demo_reset["row"]),
            phase=str(demo_reset["phase"]),
            source_trajectory_json=demo_reset.get("source_trajectory_json"),
            source_frame=demo_reset.get("source_frame"),
            source_joint_reset_available="source_joint_position" in demo_reset,
            joint_blend_alpha=float(args_cli.demo_reset_joint_blend_alpha),
            cube_pos_blend_alpha=float(args_cli.demo_reset_cube_pos_blend_alpha),
        )

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    success_timeout_override = None
    if args_cli.success_timeout_override is not None:
        if not hasattr(env_cfg, "success_timeout"):
            raise AttributeError(
                f"Task config for {args_cli.task} does not expose success_timeout; "
                "cannot apply --success_timeout_override."
            )
        original_success_timeout = float(env_cfg.success_timeout)
        env_cfg.success_timeout = float(args_cli.success_timeout_override)
        success_timeout_override = {
            "original": original_success_timeout,
            "override": float(env_cfg.success_timeout),
        }
        _stage("success_timeout_override_applied", **success_timeout_override)
    _configure_eval_camera(env_cfg)
    _stage("env_cfg_ready", task=args_cli.task, device=str(args_cli.device), seed=int(args_cli.seed))

    workspace, policy = _load_policy(
        checkpoint,
        str(args_cli.device),
        int(args_cli.num_inference_steps),
        args_cli.diffusion_policy_root,
    )
    n_obs_steps = int(policy.n_obs_steps)
    expected_obs_dim = _policy_global_obs_dim(policy)
    if phase_progress_provider is None:
        if expected_obs_dim is not None and expected_obs_dim != FRANKA_CUBE_LOWDIM_OBS_DIM:
            raise RuntimeError(
                f"Checkpoint appears to expect obs_dim={expected_obs_dim}, but no --phase_progress_dataset was provided."
            )
        history_obs_dim = FRANKA_CUBE_LOWDIM_OBS_DIM
    else:
        history_obs_dim = int(phase_progress_provider.obs_dim)
        if expected_obs_dim is not None and expected_obs_dim != history_obs_dim:
            raise RuntimeError(
                f"Phase/progress provider produces obs_dim={history_obs_dim}, checkpoint expects {expected_obs_dim}."
            )

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

    history = LowdimObsHistory(num_envs=task_env.num_envs, n_obs_steps=n_obs_steps, obs_dim=history_obs_dim)
    requested_action_chunk_steps = max(1, int(args_cli.action_chunk_steps))
    action_queue = np.empty((task_env.num_envs, 0, FRANKA_CUBE_ACTION_DIM), dtype=np.float32)
    step_metrics: list[dict[str, float | int | None]] = []
    policy_trace_records: list[dict[str, Any]] = []
    support_trace_records: list[dict[str, Any]] = []
    action_min = np.full(FRANKA_CUBE_ACTION_DIM, np.inf, dtype=np.float64)
    action_max = np.full(FRANKA_CUBE_ACTION_DIM, -np.inf, dtype=np.float64)
    done_count = 0
    env_closed = False
    final_cube_pos_mean: list[float] | list[list[float]] | None = None
    final_gripper_width: float | None = None
    demo_reset_summary: dict[str, Any] | None = None
    try:
        _stage("env_reset_start")
        policy_obs = _policy_obs_from_reset(gym_env.reset())
        _stage("env_reset_done", policy_obs_shape=tuple(policy_obs.shape))
        if policy_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
            raise RuntimeError(f"Expected PPO obs dim {FRANKA_CUBE_PPO_OBS_DIM}, got {tuple(policy_obs.shape)}")
        if demo_reset is not None:
            _stage(
                "demo_reset_apply_start",
                episode=int(demo_reset["episode"]),
                episode_step=int(demo_reset["episode_step"]),
                row=int(demo_reset["row"]),
                phase=str(demo_reset["phase"]),
            )
            policy_obs, demo_reset_summary = _apply_demo_reset(task_env, demo_reset)
            _stage("demo_reset_apply_done", **demo_reset_summary)

        _stage("rollout_start", action_chunk_steps=requested_action_chunk_steps)
        for step in range(int(args_cli.num_steps)):
            if not simulation_app.is_running():
                _stage("simulation_app_stopped", step=step)
                break

            with torch.inference_mode():
                if action_queue.shape[1] == 0:
                    action_seq = predict_action_sequence_from_ppo_obs(
                        policy,
                        policy_obs,
                        history,
                        step=step,
                        phase_progress_provider=phase_progress_provider,
                        num_action_samples=max(1, int(args_cli.num_action_samples)),
                    )
                    if action_seq.ndim != 3 or action_seq.shape[0] != task_env.num_envs:
                        raise RuntimeError(f"Unexpected DP action sequence shape {action_seq.shape}")
                    chunk_steps = min(requested_action_chunk_steps, int(action_seq.shape[1]))
                    action_queue = np.asarray(action_seq[:, :chunk_steps], dtype=np.float32)
                    _trace_policy_call(
                        trace_records=policy_trace_records,
                        max_calls=debug_trace_max_calls,
                        step=step,
                        env_index=int(args_cli.debug_policy_trace_env_index),
                        history=history,
                        action_seq=action_seq,
                        chunk_steps=chunk_steps,
                    )
                action_np = action_queue[:, 0]
                action_queue = action_queue[:, 1:]
                action_correction_records = [
                    {"mode": str(args_cli.action_correction_mode), "applied": False, "runtime_phase": "unknown"}
                    for _ in range(task_env.num_envs)
                ]
                if args_cli.action_correction_mode != "disabled":
                    lowdim_before = extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()
                    if phase_progress_provider is not None:
                        lowdim_before = phase_progress_provider.augment_lowdim(lowdim_before, step=step)
                    action_np, action_correction_records = _apply_eval_action_correction(
                        action_np,
                        lowdim_obs=lowdim_before,
                        support=support_dataset,
                        mode=str(args_cli.action_correction_mode),
                        blend=float(args_cli.action_correction_blend),
                    )
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
                elif action_queue.shape[1] > 0:
                    lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs)
                    lowdim_np = lowdim.detach().float().cpu().numpy()
                    if phase_progress_provider is not None:
                        lowdim_np = phase_progress_provider.augment_lowdim(lowdim_np, step=step + 1)
                    history.push(lowdim_np, step=step + 1)

            reward_mean = _mean_float(rewards)
            task_metrics = _collect_task_metrics(task_env)
            if support_dataset is not None:
                lowdim_after = extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()
                if phase_progress_provider is not None:
                    lowdim_after = phase_progress_provider.augment_lowdim(lowdim_after, step=step + 1)
                env_index = min(max(0, int(args_cli.debug_policy_trace_env_index)), int(lowdim_after.shape[0]) - 1)
                support_trace_records.append(
                    _collect_support_record(
                        support=support_dataset,
                        step=step + 1,
                        env_index=env_index,
                        lowdim_obs=lowdim_after[env_index],
                        action=action_np[env_index],
                        reward_mean=reward_mean,
                        task_metrics=task_metrics,
                        history=history,
                        action_queue_len_after_pop=action_queue.shape[1],
                        action_correction=action_correction_records[env_index],
                    )
                )
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
        "phase_progress_provider": None if phase_progress_provider is None else phase_progress_provider.summary(),
        "action_chunk_steps": requested_action_chunk_steps,
        "num_action_samples": max(1, int(args_cli.num_action_samples)),
        "no_learning": True,
        "num_envs": task_num_envs,
        "num_steps_requested": int(args_cli.num_steps),
        "steps_completed": len(step_metrics),
        "done_count": done_count,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "final_success_rate": success_values[-1] if success_values else None,
        "window_success_rate": sum(success_values[-window:]) / window if success_values else None,
        "success_timeout_override": success_timeout_override,
        "action_min": action_min.astype(float).tolist(),
        "action_max": action_max.astype(float).tolist(),
        "step_metric_summary": _summarize_step_metrics(step_metrics),
        "final_cube_pos_mean": final_cube_pos_mean,
        "final_gripper_width": final_gripper_width,
        "output_dir": str(output_dir),
        "metrics_path": str(metrics_path),
        "eval_config_path": str(eval_config_path),
        "debug_policy_trace_path": str(debug_trace_path) if debug_trace_path is not None else None,
        "debug_policy_trace_records": len(policy_trace_records),
        "support_dataset": str(support_dataset_path) if support_dataset_path is not None else None,
        "action_correction_mode": str(args_cli.action_correction_mode),
        "action_correction_blend": float(args_cli.action_correction_blend),
        "support_trace_path": str(support_trace_path) if support_trace_path is not None else None,
        "support_trace_csv_path": str(support_trace_csv_path) if support_trace_csv_path is not None else None,
        "support_trace_records": len(support_trace_records),
        "demo_reset": demo_reset_summary,
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
    if support_trace_path is not None:
        support_summary = {
            "task": args_cli.task,
            "checkpoint": str(checkpoint),
            "dataset": str(support_dataset_path),
            "num_envs": task_num_envs,
            "num_steps_requested": int(args_cli.num_steps),
            "action_chunk_steps": requested_action_chunk_steps,
            "num_inference_steps": int(args_cli.num_inference_steps),
            "env_index": int(args_cli.debug_policy_trace_env_index),
            "records": len(support_trace_records),
            "first_negative_gripper_step": next(
                (int(record["step"]) for record in support_trace_records if float(record["executed_gripper"]) < 0.0),
                None,
            ),
            "first_hard_close_step": next(
                (int(record["step"]) for record in support_trace_records if float(record["executed_gripper"]) <= -0.9),
                None,
            ),
            "nearest_demo_distance_start": support_trace_records[0]["nearest_demo_distance"] if support_trace_records else None,
            "nearest_demo_distance_final": support_trace_records[-1]["nearest_demo_distance"] if support_trace_records else None,
            "nearest_demo_phase_counts": {
                phase: sum(1 for record in support_trace_records if record["nearest_demo_phase"] == phase)
                for phase in sorted({str(record["nearest_demo_phase"]) for record in support_trace_records})
            },
            "action_correction_mode": str(args_cli.action_correction_mode),
            "action_correction_blend": float(args_cli.action_correction_blend),
            "action_correction_applied_count": sum(
                1 for record in support_trace_records if bool(record.get("action_correction_applied", False))
            ),
        }
        support_trace_path.write_text(
            json.dumps(
                {"summary": _json_safe(support_summary), "records": _json_safe(support_trace_records)},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if support_trace_csv_path is not None:
            _write_support_csv(support_trace_csv_path, support_trace_records)
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
