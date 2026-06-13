"""Audit Franka cube source target frames against the live Isaac controller.

This script does not train. It answers whether converted cuRobo lowdim target
rows describe the same control point/frame that the DEXTRAH Isaac env controls.
For selected episode-local rows, it compares:

* converted dataset lowdim EE target,
* env FK recomputed from the raw source joint state,
* one-step controller commands from the live task EE frame to dataset/FK
  targets.
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
parser.add_argument("--dataset", required=True, type=str, help="Converted lowdim NPZ dataset.")
parser.add_argument("--trajectory_json", required=True, type=str, help="Raw source trajectory JSON for the episode.")
parser.add_argument("--output_dir", default=None, type=str)
parser.add_argument("--task", default="Dextrah-Franka-Cube-Grasp", type=str)
parser.add_argument("--episode", default=24, type=int)
parser.add_argument(
    "--episode_step",
    action="append",
    type=int,
    default=[],
    help="Episode-local rows to audit. Defaults to close/lift sentinel rows.",
)
parser.add_argument("--seed", default=42, type=int)
parser.add_argument("--replay_csv", default=None, type=str, help="Optional replay_steps.csv to merge context.")
parser.add_argument("--reference_video", default=None, type=str)
parser.add_argument("--reference_contact_sheet", default=None, type=str)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

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
from dextrah_lab.offline_dp_bc.ppo_bridge import (
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    extract_lowdim_obs_from_ppo_obs,
)
from dextrah_lab.offline_dp_bc.trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


PHASE_NAMES = sorted(PICK_AND_LIFT_PHASE_ORDER)


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


def _phase_name(phase_ids: np.ndarray, row_idx: int) -> str:
    return PHASE_NAMES[int(phase_ids[int(row_idx)])]


def _policy_obs_from_task_env(task_env: Any) -> torch.Tensor:
    task_env._compute_intermediate_values()
    obs_dict = task_env._get_observations()
    return obs_dict["policy"] if isinstance(obs_dict, dict) else obs_dict


def _policy_obs_from_reset(reset_out: Any) -> torch.Tensor:
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    return obs["policy"] if isinstance(obs, dict) else obs


def _policy_obs_from_step(step_out: Any) -> torch.Tensor:
    obs = step_out[0]
    return obs["policy"] if isinstance(obs, dict) else obs


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
            f"Cannot map source joint dim {raw_q_tensor.shape[1]} to env joints "
            f"({joint_pos.shape[1]} total, {arm_count} arm, {finger_count} fingers)"
        )
    return torch.clamp(joint_pos, task_env.robot_dof_lower_limits, task_env.robot_dof_upper_limits)


def _apply_source_state(
    gym_env: Any,
    task_env: Any,
    *,
    target_obs: np.ndarray,
    initial_cube_pos: np.ndarray,
    raw_joint_position: np.ndarray,
    seed: int,
) -> np.ndarray:
    _policy_obs_from_reset(gym_env.reset(seed=int(seed)))
    env_ids = torch.as_tensor(task_env._robot._ALL_INDICES, device=task_env.device, dtype=torch.long)
    joint_pos = _map_source_joint_to_env(task_env, raw_joint_position, env_ids)
    joint_vel = torch.zeros_like(joint_pos)
    task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    task_env.robot_dof_targets[env_ids] = joint_pos
    task_env.arm_joint_pos_target[env_ids] = joint_pos[:, task_env.arm_joint_ids]
    task_env.finger_joint_pos_target[env_ids] = joint_pos[:, task_env.finger_joint_ids]

    num_ids = int(env_ids.numel())
    cube_pos = torch.as_tensor(target_obs[7:10], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    cube_quat = torch.as_tensor(target_obs[10:14], dtype=torch.float32, device=task_env.device).repeat(num_ids, 1)
    object_state = torch.zeros(num_ids, 13, device=task_env.device)
    object_state[:, 0:3] = cube_pos + task_env.scene.env_origins[env_ids]
    object_state[:, 3:7] = cube_quat
    task_env._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
    task_env.cube_initial_pos[env_ids] = torch.as_tensor(
        initial_cube_pos, dtype=torch.float32, device=task_env.device
    ).repeat(num_ids, 1)
    task_env.cube_goal_pos[env_ids] = cube_pos
    task_env.cube_goal_pos[env_ids, 2] = cube_pos[:, 2] + float(task_env.cfg.cube_lift_height)
    task_env.has_lifted_cube[env_ids] = False
    task_env.in_success_region[env_ids] = False
    task_env.time_in_success_region[env_ids] = 0.0
    task_env.actions[env_ids] = 0.0
    task_env.ik_controller.reset(env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    policy_obs = _policy_obs_from_task_env(task_env)
    return extract_lowdim_obs_from_ppo_obs(policy_obs).detach().float().cpu().numpy()[0]


def _normalized_action_to_target(live_lowdim: np.ndarray, target_lowdim: np.ndarray, gripper_action: float) -> np.ndarray:
    ee_pos = np.stack((live_lowdim[:3], target_lowdim[:3]), axis=0).astype(np.float32)
    ee_quat = np.stack((live_lowdim[3:7], target_lowdim[3:7]), axis=0).astype(np.float32)
    grip = np.asarray([float(gripper_action), float(gripper_action)], dtype=np.float32)
    return derive_relative_ee_actions(
        ee_pos,
        ee_quat,
        gripper_action=grip,
        convention=DEFAULT_DEXTRAH_ACTION_CONVENTION,
        terminal_action="drop",
    )[0].astype(np.float32)


def _safe_norm(value: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(value, dtype=np.float64)))


def _cosine(a: np.ndarray, b: np.ndarray) -> float | None:
    an = _safe_norm(a)
    bn = _safe_norm(b)
    if an < 1.0e-8 or bn < 1.0e-8:
        return None
    return float(np.dot(a, b) / (an * bn))


def _ratio(actual: float, expected: float) -> float | None:
    if abs(expected) < 1.0e-8:
        return None
    return float(actual / expected)


def _quat_error_rad(a: np.ndarray, b: np.ndarray) -> float:
    return _safe_norm(axis_angle_from_quat_wxyz(quat_mul_wxyz(a, quat_inv_wxyz(b))))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_replay_context(path: Path | None) -> dict[int, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    out: dict[int, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                target_step = int(row.get("tracking_target_episode_step", -1))
            except ValueError:
                continue
            if target_step >= 0 and target_step not in out:
                out[target_step] = row
    return out


def _plot_state(rows: list[dict[str, Any]], output_path: Path) -> None:
    state_rows = [r for r in rows if r["record_type"] == "state"]
    if not state_rows:
        return
    x = [int(r["episode_step"]) for r in state_rows]
    fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=True, constrained_layout=True)
    axes[0].plot(x, [r["dataset_vs_fk_ee_pos_l2"] for r in state_rows], marker="o", label="dataset EE vs env FK EE")
    axes[0].plot(x, [r["dataset_vs_fk_cube_minus_ee_l2"] for r in state_rows], marker="o", label="cube-minus-EE")
    axes[1].plot(x, [r["fk_ee_to_cube"] for r in state_rows], marker="o", label="FK EE-cube")
    axes[1].plot(x, [r["fk_finger_center_to_cube"] for r in state_rows], marker="o", label="FK finger-center-cube")
    axes[1].plot(x, [r["fk_left_finger_to_cube"] for r in state_rows], linestyle=":", label="left finger")
    axes[1].plot(x, [r["fk_right_finger_to_cube"] for r in state_rows], linestyle=":", label="right finger")
    axes[2].plot(x, [r["dataset_gripper_action"] for r in state_rows], marker="o", label="dataset gripper action")
    axes[2].plot(x, [r["fk_gripper_width"] for r in state_rows], marker="o", label="FK gripper width")
    axes[3].plot(x, [r.get("replay_ee_to_cube_after", np.nan) for r in state_rows], marker="o", label="1027893 EE-cube")
    axes[3].plot(
        x,
        [r.get("replay_finger_center_to_cube_after", np.nan) for r in state_rows],
        marker="o",
        label="1027893 finger-center-cube",
    )
    axes[0].set_ylabel("m/rad")
    axes[1].set_ylabel("m")
    axes[2].set_ylabel("action / m")
    axes[3].set_ylabel("m")
    axes[3].set_xlabel("episode-local source row")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_step(rows: list[dict[str, Any]], output_path: Path) -> None:
    step_rows = [r for r in rows if r["record_type"] == "one_step"]
    if not step_rows:
        return
    variants = list(dict.fromkeys(r["variant"] for r in step_rows))
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True, constrained_layout=True)
    for variant in variants:
        var_rows = [r for r in step_rows if r["variant"] == variant]
        x = [int(r["episode_step"]) for r in var_rows]
        axes[0].plot(x, [r["target_error_after"] for r in var_rows], marker="o", label=variant)
        axes[1].plot(x, [r["actual_vs_expected_xyz_cosine"] for r in var_rows], marker="o", label=variant)
        axes[2].plot(x, [r["xyz_realization_ratio"] for r in var_rows], marker="o", label=variant)
    axes[0].set_ylabel("target err m")
    axes[1].set_ylabel("cosine")
    axes[2].set_ylabel("actual/expected")
    axes[2].set_xlabel("episode-local source row")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _build_report(summary: dict[str, Any], state_rows: list[dict[str, Any]], step_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Franka Cube Target-Frame Audit",
        "",
        "This bounded Isaac audit compares converted lowdim targets against env FK from the same source joints and one-step controller commands from the live task EE frame. It does not train.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## State Target Table",
        "",
        "| step | phase | dataset-vs-FK EE | dataset-vs-FK quat | FK EE-cube | FK finger-cube | FK L/R finger-cube | grip action | replay EE/finger |",
        "|---:|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in state_rows:
        lines.append(
            f"| {row['episode_step']} | {row['phase']} | {row['dataset_vs_fk_ee_pos_l2']:.5f} | "
            f"{row['dataset_vs_fk_ee_quat_rad']:.5f} | {row['fk_ee_to_cube']:.5f} | "
            f"{row['fk_finger_center_to_cube']:.5f} | "
            f"{row['fk_left_finger_to_cube']:.5f}/{row['fk_right_finger_to_cube']:.5f} | "
            f"{row['dataset_gripper_action']:.3f} | "
            f"{row.get('replay_ee_to_cube_after', float('nan')):.5f}/"
            f"{row.get('replay_finger_center_to_cube_after', float('nan')):.5f} |"
        )
    lines.extend(
        [
            "",
            "## One-Step Command Table",
            "",
            "| step | phase | variant | target row | action xyz | target err after | cosine | ratio | clip frac | finger-cube after |",
            "|---:|---|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in step_rows:
        lines.append(
            f"| {row['episode_step']} | {row['phase']} | {row['variant']} | {row['target_episode_step']} | "
            f"{row['executed_action_xyz']} | {row['target_error_after']:.5f} | "
            f"{row['actual_vs_expected_xyz_cosine'] if row['actual_vs_expected_xyz_cosine'] is not None else 'None'} | "
            f"{row['xyz_realization_ratio'] if row['xyz_realization_ratio'] is not None else 'None'} | "
            f"{row['pose_action_clip_fraction']:.3f} | {row['finger_center_to_cube_after']:.5f} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- State CSV: `{summary['state_csv']}`",
            f"- One-step CSV: `{summary['one_step_csv']}`",
            f"- Summary JSON: `{summary['summary_json']}`",
            f"- State plot: `{summary['state_plot']}`",
            f"- One-step plot: `{summary['one_step_plot']}`",
            f"- Reference video: `{summary.get('reference_video')}`",
            f"- Reference contact sheet: `{summary.get('reference_contact_sheet')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_target_frame_audit_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = Path(args_cli.dataset).expanduser().resolve()
    trajectory_path = Path(args_cli.trajectory_json).expanduser().resolve()
    replay_csv = Path(args_cli.replay_csv).expanduser().resolve() if args_cli.replay_csv else None
    data = np.load(dataset_path, allow_pickle=False)
    dataset_obs = np.asarray(data["obs"], dtype=np.float32)
    dataset_action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_idx, ep_start, ep_end = _episode_for_row(
        _row_for_episode_step(episode_ends, int(args_cli.episode), 0),
        episode_ends,
    )
    episode_steps = args_cli.episode_step or [260, 282, 297, 310, 312, 402, 450, 487]
    episode_steps = sorted({int(np.clip(s, 0, ep_end - ep_start - 2)) for s in episode_steps})

    payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
    frames = payload["frames"]
    if len(frames) < ep_end - ep_start:
        raise ValueError(f"trajectory has {len(frames)} frames but episode has {ep_end - ep_start} rows")

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=1,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode=None)
    task_env = gym_env.unwrapped
    action_scale_np = task_env.action_scale.detach().float().cpu().numpy()
    root_quat_np = task_env._robot.data.root_quat_w[0].detach().float().cpu().numpy()
    initial_cube_pos = dataset_obs[ep_start, 7:10].astype(np.float32)
    replay_context = _read_replay_context(replay_csv)

    fk_obs_by_step: dict[int, np.ndarray] = {}
    state_rows: list[dict[str, Any]] = []
    all_steps_for_fk = sorted(set(episode_steps + [min(s + 1, ep_end - ep_start - 1) for s in episode_steps]))
    try:
        for episode_step in all_steps_for_fk:
            row_idx = ep_start + int(episode_step)
            raw_q = np.asarray(frames[int(episode_step)]["joint_position"], dtype=np.float32)
            fk_lowdim = _apply_source_state(
                gym_env,
                task_env,
                target_obs=dataset_obs[row_idx],
                initial_cube_pos=initial_cube_pos,
                raw_joint_position=raw_q,
                seed=int(args_cli.seed),
            )
            fk_obs_by_step[int(episode_step)] = fk_lowdim
            if episode_step not in episode_steps:
                continue
            dataset_lowdim = dataset_obs[row_idx]
            replay_row = replay_context.get(int(episode_step), {})
            state_row = {
                "record_type": "state",
                "episode": int(episode_idx),
                "episode_step": int(episode_step),
                "row": int(row_idx),
                "phase": _phase_name(phase_ids, row_idx),
                "dataset_vs_fk_ee_pos_l2": _safe_norm(dataset_lowdim[:3] - fk_lowdim[:3]),
                "dataset_vs_fk_ee_quat_rad": _quat_error_rad(dataset_lowdim[3:7], fk_lowdim[3:7]),
                "dataset_vs_fk_cube_minus_ee_l2": _safe_norm(dataset_lowdim[14:17] - fk_lowdim[14:17]),
                "dataset_gripper_width": float(dataset_lowdim[20]),
                "dataset_gripper_action": float(dataset_action[row_idx, 6]),
                "fk_ee_to_cube": _safe_norm(fk_lowdim[14:17]),
                "fk_finger_center_to_cube": float(task_env.finger_center_to_cube_dist.detach().cpu()[0]),
                "fk_left_finger_to_cube": float(task_env.left_finger_to_cube_dist.detach().cpu()[0]),
                "fk_right_finger_to_cube": float(task_env.right_finger_to_cube_dist.detach().cpu()[0]),
                "fk_gripper_width": float(fk_lowdim[20]),
                "fk_cube_lift_height": float(task_env.cube_lift_height.detach().cpu()[0]),
                "replay_ee_to_cube_after": float(replay_row["ee_to_cube_after"]) if replay_row else float("nan"),
                "replay_finger_center_to_cube_after": (
                    float(replay_row["finger_center_to_cube_dist_after"]) if replay_row else float("nan")
                ),
                "replay_gripper_width_after": float(replay_row["gripper_width_after"]) if replay_row else float("nan"),
                "replay_cube_lift_height_after": (
                    float(replay_row["cube_lift_height_after"]) if replay_row else float("nan")
                ),
            }
            state_rows.append(state_row)

        step_rows: list[dict[str, Any]] = []
        for episode_step in episode_steps:
            row_idx = ep_start + int(episode_step)
            target_step = min(int(episode_step) + 1, ep_end - ep_start - 1)
            target_row = ep_start + target_step
            variants = {
                "dataset_label": dataset_action[row_idx].astype(np.float32),
                "source_lowdim_residual": None,
                "source_joint_fk_residual": None,
            }
            for variant in variants:
                raw_q = np.asarray(frames[int(episode_step)]["joint_position"], dtype=np.float32)
                before_lowdim = _apply_source_state(
                    gym_env,
                    task_env,
                    target_obs=dataset_obs[row_idx],
                    initial_cube_pos=initial_cube_pos,
                    raw_joint_position=raw_q,
                    seed=int(args_cli.seed),
                )
                if variant == "source_lowdim_residual":
                    action = _normalized_action_to_target(
                        before_lowdim,
                        dataset_obs[target_row],
                        gripper_action=float(dataset_action[target_row, 6]),
                    )
                    target_lowdim = dataset_obs[target_row]
                elif variant == "source_joint_fk_residual":
                    action = _normalized_action_to_target(
                        before_lowdim,
                        fk_obs_by_step[target_step],
                        gripper_action=float(dataset_action[target_row, 6]),
                    )
                    target_lowdim = fk_obs_by_step[target_step]
                else:
                    action = variants[variant].copy()
                    target_pos, target_quat = apply_normalized_action_to_world_pose(
                        before_lowdim[None, :3],
                        before_lowdim[None, 3:7],
                        action[None],
                    )
                    target_lowdim = before_lowdim.copy()
                    target_lowdim[:3] = target_pos[0]
                    target_lowdim[3:7] = target_quat[0]
                clip_hits = np.abs(action[:6]) >= (1.0 - 1.0e-6)
                expected_world_delta = normalized_action_to_world_delta(action[None])[0]
                policy_obs_next = _policy_obs_from_step(
                    gym_env.step(torch.as_tensor(action[None], dtype=torch.float32, device=task_env.device))
                )
                after_lowdim = extract_lowdim_obs_from_ppo_obs(policy_obs_next).detach().float().cpu().numpy()[0]
                actual_delta = after_lowdim[:3] - before_lowdim[:3]
                expected_norm = _safe_norm(expected_world_delta[:3])
                actual_norm = _safe_norm(actual_delta)
                target_error_after = _safe_norm(after_lowdim[:3] - target_lowdim[:3])
                step_rows.append(
                    {
                        "record_type": "one_step",
                        "episode": int(episode_idx),
                        "episode_step": int(episode_step),
                        "row": int(row_idx),
                        "phase": _phase_name(phase_ids, row_idx),
                        "variant": variant,
                        "target_episode_step": int(target_step),
                        "target_row": int(target_row),
                        "target_phase": _phase_name(phase_ids, target_row),
                        "executed_action": action.astype(float).tolist(),
                        "executed_action_xyz": action[:3].astype(float).tolist(),
                        "pose_action_clip_fraction": float(np.count_nonzero(clip_hits) / 6.0),
                        "expected_xyz_delta_norm": expected_norm,
                        "actual_xyz_delta_norm": actual_norm,
                        "xyz_realization_ratio": _ratio(actual_norm, expected_norm),
                        "actual_vs_expected_xyz_cosine": _cosine(actual_delta, expected_world_delta[:3]),
                        "target_error_after": target_error_after,
                        "ee_to_cube_after": _safe_norm(after_lowdim[14:17]),
                        "finger_center_to_cube_after": float(task_env.finger_center_to_cube_dist.detach().cpu()[0]),
                        "gripper_width_after": float(after_lowdim[20]),
                        "cube_lift_height_after": float(task_env.cube_lift_height.detach().cpu()[0]),
                        "action_scale": action_scale_np.astype(float).tolist(),
                        "robot_root_quat_wxyz": root_quat_np.astype(float).tolist(),
                    }
                )
    finally:
        gym_env.close()

    state_csv = output_dir / "target_frame_state_rows.csv"
    one_step_csv = output_dir / "target_frame_one_step.csv"
    summary_json = output_dir / "target_frame_summary.json"
    report_path = output_dir / "target_frame_report.md"
    state_plot = output_dir / "target_frame_state_plot.png"
    one_step_plot = output_dir / "target_frame_one_step_plot.png"
    _write_csv(state_csv, state_rows)
    _write_csv(one_step_csv, step_rows)
    _plot_state(state_rows, state_plot)
    _plot_step(step_rows, one_step_plot)

    max_dataset_fk_ee = max((row["dataset_vs_fk_ee_pos_l2"] for row in state_rows), default=float("nan"))
    min_fk_finger = min((row["fk_finger_center_to_cube"] for row in state_rows), default=float("nan"))
    best_target_error = min((row["target_error_after"] for row in step_rows), default=float("nan"))
    verdict = (
        "Converted lowdim EE targets match env FK from source joints, but the controlled EE/TCP remains far from "
        "finger-center contact geometry; raw cuRobo labels need controller/contact-aware relabeling before DP."
        if max_dataset_fk_ee < 0.005 and min_fk_finger > 0.04
        else (
            "Converted lowdim targets disagree with env FK from source joints; fix frame/FK conversion before DP."
            if max_dataset_fk_ee >= 0.005
            else "Target-frame audit inconclusive; inspect one-step command table and video."
        )
    )
    summary = {
        "dataset": str(dataset_path),
        "trajectory_json": str(trajectory_path),
        "episode": int(episode_idx),
        "episode_steps": episode_steps,
        "task": args_cli.task,
        "seed": int(args_cli.seed),
        "max_dataset_vs_fk_ee_pos_l2": float(max_dataset_fk_ee),
        "min_fk_finger_center_to_cube": float(min_fk_finger),
        "best_one_step_target_error_after": float(best_target_error),
        "verdict": verdict,
        "state_csv": str(state_csv),
        "one_step_csv": str(one_step_csv),
        "summary_json": str(summary_json),
        "report": str(report_path),
        "state_plot": str(state_plot),
        "one_step_plot": str(one_step_plot),
        "reference_video": args_cli.reference_video,
        "reference_contact_sheet": args_cli.reference_contact_sheet,
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_build_report(summary, state_rows, step_rows), encoding="utf-8")
    print(
        "FRANKA_CUBE_TARGET_FRAME_AUDIT_DONE "
        + json.dumps(
            {
                "output_dir": str(output_dir),
                "report": str(report_path),
                "summary_json": str(summary_json),
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
        print(f"FRANKA_CUBE_TARGET_FRAME_AUDIT_FAILED {exc.__class__.__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        simulation_app.close()
