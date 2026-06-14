"""Collect dynamically verified GraspGen prior indices for Franka multi-object RL."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Multi-Object-Grasp")
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_path", type=str, required=True)
parser.add_argument("--object_asset_manifest_path", type=str, required=True)
parser.add_argument("--max_objects", type=int, default=2)
parser.add_argument("--object_asset_assignment", type=str, default="round_robin")
parser.add_argument("--object_spawn_center_offset_x", type=float, default=0.05)
parser.add_argument("--object_spawn_center_offset_y", type=float, default=0.0)
parser.add_argument("--object_spawn_xy_randomization", type=float, default=0.10)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=180.0)
parser.add_argument("--object_stable_pose_enabled", action="store_true", default=False)
parser.add_argument("--object_stable_pose_cache_dir", type=str, default="")
parser.add_argument("--object_stable_pose_count", type=int, default=1)
parser.add_argument("--object_stable_pose_randomize", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--object_stable_pose_allow_missing", action="store_true", default=False)
parser.add_argument("--cycles", type=int, default=120)
parser.add_argument("--min_cycles", type=int, default=10)
parser.add_argument("--target_per_object", type=int, default=8)
parser.add_argument("--max_indices_per_object", type=int, default=128)
parser.add_argument("--score_steps", type=int, default=220)
parser.add_argument("--min_lift_height", type=float, default=0.10)
parser.add_argument("--max_xy_delta", type=float, default=0.15)
parser.add_argument("--max_finger_dist", type=float, default=0.25)
parser.add_argument("--max_done_count", type=int, default=0)
parser.add_argument("--require_success", action="store_true", default=False)
parser.add_argument("--grasp_reset_attempts", type=int, default=4)
parser.add_argument("--grasp_reset_require_topdown", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--grasp_reset_min_pregrasp_z", type=float, default=0.45)
parser.add_argument("--grasp_reset_candidate_count", type=int, default=2048)
parser.add_argument("--grasp_reset_max_center_distance_frac", type=float, default=0.35)
parser.add_argument("--grasp_reset_min_width", type=float, default=0.008)
parser.add_argument("--grasp_reset_ik_iterations", type=int, default=96)
parser.add_argument("--grasp_reset_ik_damping", type=float, default=0.035)
parser.add_argument("--grasp_reset_ik_max_joint_step", type=float, default=0.25)
parser.add_argument("--grasp_reset_ik_pos_tolerance", type=float, default=0.055)
parser.add_argument("--grasp_reset_ik_rot_tolerance", type=float, default=0.55)
parser.add_argument("--grasp_pregrasp_offset", type=float, default=0.03)
parser.add_argument("--grasp_warmstart_close_width", type=float, default=0.004)
parser.add_argument("--grasp_warmstart_use_prior_close_width", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--grasp_warmstart_prior_close_width_margin", type=float, default=0.003)
parser.add_argument("--grasp_warmstart_min_close_width", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_action_z", type=float, default=0.50)
parser.add_argument("--grasp_warmstart_approach_steps", type=int, default=4)
parser.add_argument("--grasp_warmstart_close_steps", type=int, default=40)
parser.add_argument("--grasp_warmstart_lift_steps", type=int, default=160)
parser.add_argument("--grasp_warmstart_gain", type=float, default=8.0)
parser.add_argument("--grasp_warmstart_max_position_action", type=float, default=1.0)
parser.add_argument("--grasp_warmstart_track_orientation", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--grasp_warmstart_close_max_ee_error", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_max_ee_error", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_max_finger_center_dist", type=float, default=0.0)
parser.add_argument("--grasp_warmstart_lift_closed_width_margin", type=float, default=-1.0)
parser.add_argument("--grasp_warmstart_require_current_lift_ready", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = False

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401


def _as_float(value: torch.Tensor) -> float:
    return float(value.detach().float().cpu())


def _make_env():
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = int(args_cli.seed)
    env_cfg.object_asset_manifest_path = str(Path(args_cli.object_asset_manifest_path).expanduser().resolve())
    env_cfg.max_objects = int(args_cli.max_objects)
    env_cfg.object_asset_assignment = str(args_cli.object_asset_assignment)
    env_cfg.object_spawn_center_offset_x = float(args_cli.object_spawn_center_offset_x)
    env_cfg.object_spawn_center_offset_y = float(args_cli.object_spawn_center_offset_y)
    env_cfg.object_spawn_xy_randomization = float(args_cli.object_spawn_xy_randomization)
    env_cfg.object_spawn_yaw_randomization_deg = float(args_cli.object_spawn_yaw_randomization_deg)
    env_cfg.object_stable_pose_enabled = bool(args_cli.object_stable_pose_enabled)
    env_cfg.object_stable_pose_cache_dir = str(args_cli.object_stable_pose_cache_dir)
    env_cfg.object_stable_pose_count = int(args_cli.object_stable_pose_count)
    env_cfg.object_stable_pose_randomize = bool(args_cli.object_stable_pose_randomize)
    env_cfg.object_stable_pose_allow_missing = bool(args_cli.object_stable_pose_allow_missing)
    env_cfg.object_reset_settle_steps = 0
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_allow_missing = False
    env_cfg.grasp_prior_reset_attempts = int(args_cli.grasp_reset_attempts)
    env_cfg.grasp_prior_reset_candidate_count = int(args_cli.grasp_reset_candidate_count)
    env_cfg.grasp_prior_reset_require_topdown = bool(args_cli.grasp_reset_require_topdown)
    env_cfg.grasp_prior_reset_min_pregrasp_z = float(args_cli.grasp_reset_min_pregrasp_z)
    env_cfg.grasp_prior_reset_max_center_distance_frac = float(args_cli.grasp_reset_max_center_distance_frac)
    env_cfg.grasp_prior_reset_min_width = float(args_cli.grasp_reset_min_width)
    env_cfg.grasp_prior_reset_ik_iterations = int(args_cli.grasp_reset_ik_iterations)
    env_cfg.grasp_prior_reset_ik_damping = float(args_cli.grasp_reset_ik_damping)
    env_cfg.grasp_prior_reset_ik_max_joint_step = float(args_cli.grasp_reset_ik_max_joint_step)
    env_cfg.grasp_prior_reset_ik_pos_tolerance = float(args_cli.grasp_reset_ik_pos_tolerance)
    env_cfg.grasp_prior_reset_ik_rot_tolerance = float(args_cli.grasp_reset_ik_rot_tolerance)
    env_cfg.grasp_prior_pregrasp_offset = float(args_cli.grasp_pregrasp_offset)
    env_cfg.grasp_prior_action_warmstart_enabled = True
    env_cfg.grasp_prior_action_warmstart_close_width = float(args_cli.grasp_warmstart_close_width)
    env_cfg.grasp_prior_action_warmstart_use_prior_close_width = bool(
        args_cli.grasp_warmstart_use_prior_close_width
    )
    env_cfg.grasp_prior_action_warmstart_prior_close_width_margin = float(
        args_cli.grasp_warmstart_prior_close_width_margin
    )
    env_cfg.grasp_prior_action_warmstart_min_close_width = float(args_cli.grasp_warmstart_min_close_width)
    env_cfg.grasp_prior_action_warmstart_lift_action_z = float(args_cli.grasp_warmstart_lift_action_z)
    env_cfg.grasp_prior_action_warmstart_approach_steps = int(args_cli.grasp_warmstart_approach_steps)
    env_cfg.grasp_prior_action_warmstart_close_steps = int(args_cli.grasp_warmstart_close_steps)
    env_cfg.grasp_prior_action_warmstart_lift_steps = int(args_cli.grasp_warmstart_lift_steps)
    env_cfg.grasp_prior_action_warmstart_gain = float(args_cli.grasp_warmstart_gain)
    env_cfg.grasp_prior_action_warmstart_max_position_action = float(args_cli.grasp_warmstart_max_position_action)
    env_cfg.grasp_prior_action_warmstart_track_orientation = bool(args_cli.grasp_warmstart_track_orientation)
    env_cfg.grasp_prior_action_warmstart_close_max_ee_error = float(
        args_cli.grasp_warmstart_close_max_ee_error
    )
    env_cfg.grasp_prior_action_warmstart_lift_max_ee_error = float(
        args_cli.grasp_warmstart_lift_max_ee_error
    )
    env_cfg.grasp_prior_action_warmstart_lift_max_finger_center_dist = float(
        args_cli.grasp_warmstart_lift_max_finger_center_dist
    )
    env_cfg.grasp_prior_action_warmstart_lift_closed_width_margin = float(
        args_cli.grasp_warmstart_lift_closed_width_margin
    )
    if args_cli.grasp_warmstart_require_current_lift_ready is not None:
        env_cfg.grasp_prior_action_warmstart_require_current_lift_ready = bool(
            args_cli.grasp_warmstart_require_current_lift_ready
        )
    env = gym.make(args_cli.task, cfg=env_cfg)
    return env, env.unwrapped


def _empty_object_records(task_env) -> dict[str, dict[str, Any]]:
    objects: dict[str, dict[str, Any]] = {}
    for object_idx, asset in enumerate(getattr(task_env, "_object_assets", [])):
        uuid = str(asset.get("uuid", object_idx))
        objects[uuid] = {
            "object_index": object_idx,
            "indices": [],
            "stats": {},
            "observed_reset_count": 0,
            "quality_reset_count": 0,
            "pass_count": 0,
        }
    return objects


def _sorted_indices(stats: dict[str, dict[str, Any]], max_indices: int) -> list[int]:
    keys = sorted(
        stats.keys(),
        key=lambda key: (
            -float(stats[key].get("max_lift_height", 0.0)),
            float(stats[key].get("min_max_finger_dist", 999.0)),
            int(key),
        ),
    )
    if max_indices > 0:
        keys = keys[:max_indices]
    return [int(key) for key in keys]


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _make_payload(task_env, objects: dict[str, dict[str, Any]], *, cycles_completed: int) -> dict[str, Any]:
    max_indices = int(args_cli.max_indices_per_object)
    for record in objects.values():
        stats = record.get("stats", {})
        if isinstance(stats, dict):
            record["indices"] = _sorted_indices(stats, max_indices)
    counts = {uuid: len(record["indices"]) for uuid, record in objects.items()}
    return {
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "task": args_cli.task,
            "num_envs": args_cli.num_envs,
            "seed": args_cli.seed,
            "cycles_requested": args_cli.cycles,
            "cycles_completed": cycles_completed,
            "target_per_object": args_cli.target_per_object,
            "max_indices_per_object": args_cli.max_indices_per_object,
            "thresholds": {
                "min_lift_height": args_cli.min_lift_height,
                "max_xy_delta": args_cli.max_xy_delta,
                "max_finger_dist": args_cli.max_finger_dist,
                "max_done_count": args_cli.max_done_count,
                "require_success": args_cli.require_success,
            },
            "config": {
                "object_asset_manifest_path": args_cli.object_asset_manifest_path,
                "max_objects": args_cli.max_objects,
                "object_asset_assignment": args_cli.object_asset_assignment,
                "object_spawn_center_offset_x": args_cli.object_spawn_center_offset_x,
                "object_spawn_center_offset_y": args_cli.object_spawn_center_offset_y,
                "object_spawn_xy_randomization": args_cli.object_spawn_xy_randomization,
                "object_spawn_yaw_randomization_deg": args_cli.object_spawn_yaw_randomization_deg,
                "object_stable_pose_enabled": args_cli.object_stable_pose_enabled,
                "object_stable_pose_cache_dir": args_cli.object_stable_pose_cache_dir,
                "object_stable_pose_count": args_cli.object_stable_pose_count,
                "object_stable_pose_randomize": args_cli.object_stable_pose_randomize,
                "grasp_reset_attempts": args_cli.grasp_reset_attempts,
                "grasp_reset_candidate_count": args_cli.grasp_reset_candidate_count,
                "grasp_reset_max_center_distance_frac": args_cli.grasp_reset_max_center_distance_frac,
                "grasp_pregrasp_offset": args_cli.grasp_pregrasp_offset,
                "score_steps": args_cli.score_steps,
                "warmstart_steps": {
                    "approach": args_cli.grasp_warmstart_approach_steps,
                    "close": args_cli.grasp_warmstart_close_steps,
                    "lift": args_cli.grasp_warmstart_lift_steps,
                },
                "grasp_warmstart_close_width": args_cli.grasp_warmstart_close_width,
                "grasp_warmstart_use_prior_close_width": args_cli.grasp_warmstart_use_prior_close_width,
                "grasp_warmstart_lift_action_z": args_cli.grasp_warmstart_lift_action_z,
                "grasp_warmstart_require_current_lift_ready": getattr(
                    task_env.cfg, "grasp_prior_action_warmstart_require_current_lift_ready", None
                ),
            },
            "asset_summary": task_env.multi_object_asset_summary()
            if hasattr(task_env, "multi_object_asset_summary")
            else {},
        },
        "summary": {
            "counts_by_uuid": counts,
            "all_targets_met": all(count >= int(args_cli.target_per_object) for count in counts.values()),
        },
        "objects": objects,
    }


def main() -> None:
    output_path = Path(args_cli.output_path).expanduser().resolve()
    env, task_env = _make_env()
    objects = _empty_object_records(task_env)
    device = task_env.device
    num_envs = int(task_env.num_envs)
    action_dim = int(task_env.cfg.action_space)
    actions = torch.zeros((num_envs, action_dim), device=device)
    cycles_completed = 0

    try:
        for cycle in range(max(int(args_cli.cycles), 1)):
            env.reset()
            sample_indices = task_env.grasp_prior_reset_sample_index.detach().clone()
            object_indices = task_env.object_asset_index.detach().clone()
            reset_success = task_env.grasp_prior_reset_success.detach().clone()
            quality_success = task_env.grasp_prior_reset_quality_success.detach().clone()
            initial_pos = task_env.cube_pos.detach().clone()
            max_lift = torch.zeros(num_envs, dtype=torch.float32, device=device)
            max_xy_delta = torch.zeros(num_envs, dtype=torch.float32, device=device)
            min_max_finger = torch.full((num_envs,), float("inf"), dtype=torch.float32, device=device)
            any_success = torch.zeros(num_envs, dtype=torch.bool, device=device)
            any_lifted = torch.zeros(num_envs, dtype=torch.bool, device=device)
            done_count = torch.zeros(num_envs, dtype=torch.long, device=device)

            for _ in range(max(int(args_cli.score_steps), 1)):
                active_before = done_count == 0
                _, _, terminated, truncated, _ = env.step(actions)
                done_step = torch.as_tensor(terminated, dtype=torch.bool, device=device) | torch.as_tensor(
                    truncated,
                    dtype=torch.bool,
                    device=device,
                )
                update_mask = active_before & ~done_step
                if bool(update_mask.any().item()):
                    max_lift[update_mask] = torch.maximum(max_lift[update_mask], task_env.cube_lift_height[update_mask])
                    xy_delta = torch.norm(task_env.cube_pos[:, :2] - initial_pos[:, :2], dim=-1)
                    max_xy_delta[update_mask] = torch.maximum(max_xy_delta[update_mask], xy_delta[update_mask])
                    min_max_finger[update_mask] = torch.minimum(
                        min_max_finger[update_mask],
                        task_env.max_finger_to_cube_dist[update_mask],
                    )
                    any_success[update_mask] |= task_env.in_success_region[update_mask]
                    any_lifted[update_mask] |= task_env.has_lifted_cube[update_mask]
                done_count += done_step.long()

            passes = (
                reset_success
                & quality_success
                & (max_lift >= float(args_cli.min_lift_height))
                & (max_xy_delta <= float(args_cli.max_xy_delta))
                & (min_max_finger <= float(args_cli.max_finger_dist))
                & (done_count <= int(args_cli.max_done_count))
            )
            if bool(args_cli.require_success):
                passes &= any_success

            object_indices_cpu = object_indices.cpu().tolist()
            sample_indices_cpu = sample_indices.cpu().tolist()
            passes_cpu = passes.cpu().tolist()
            quality_cpu = quality_success.cpu().tolist()
            reset_cpu = reset_success.cpu().tolist()
            max_lift_cpu = max_lift.cpu().tolist()
            max_xy_cpu = max_xy_delta.cpu().tolist()
            min_finger_cpu = min_max_finger.cpu().tolist()
            success_cpu = any_success.cpu().tolist()
            lifted_cpu = any_lifted.cpu().tolist()
            done_cpu = done_count.cpu().tolist()

            for env_id, object_idx in enumerate(object_indices_cpu):
                asset = task_env._object_assets[int(object_idx)]
                uuid = str(asset["uuid"])
                record = objects[uuid]
                record["observed_reset_count"] += 1
                if bool(quality_cpu[env_id]):
                    record["quality_reset_count"] += 1
                if not bool(passes_cpu[env_id]):
                    continue
                index = int(sample_indices_cpu[env_id])
                if index < 0:
                    continue
                record["pass_count"] += 1
                stats = record["stats"]
                key = str(index)
                candidate = {
                    "sample_index": index,
                    "object_index": int(object_idx),
                    "best_cycle": cycle,
                    "env_id": env_id,
                    "reset_success": bool(reset_cpu[env_id]),
                    "quality_success": bool(quality_cpu[env_id]),
                    "max_lift_height": float(max_lift_cpu[env_id]),
                    "max_xy_delta": float(max_xy_cpu[env_id]),
                    "min_max_finger_dist": float(min_finger_cpu[env_id]),
                    "has_lifted": bool(lifted_cpu[env_id]),
                    "success": bool(success_cpu[env_id]),
                    "done_count": int(done_cpu[env_id]),
                    "pass_observations": 1,
                }
                previous = stats.get(key)
                if previous is not None:
                    candidate["pass_observations"] = int(previous.get("pass_observations", 1)) + 1
                if previous is None or float(candidate["max_lift_height"]) > float(previous.get("max_lift_height", 0.0)):
                    stats[key] = candidate
                else:
                    previous["pass_observations"] = candidate["pass_observations"]

            cycles_completed = cycle + 1
            payload = _make_payload(task_env, objects, cycles_completed=cycles_completed)
            _write_payload(output_path, payload)
            counts = payload["summary"]["counts_by_uuid"]
            print(
                f"[INFO] cycle={cycles_completed}/{args_cli.cycles} "
                f"pass_envs={int(passes.sum().item())}/{num_envs} counts={counts}",
                flush=True,
            )
            if (
                cycles_completed >= int(args_cli.min_cycles)
                and all(count >= int(args_cli.target_per_object) for count in counts.values())
            ):
                break
    finally:
        payload = _make_payload(task_env, objects, cycles_completed=cycles_completed)
        _write_payload(output_path, payload)
        env.close()
        simulation_app.close()

    counts = payload["summary"]["counts_by_uuid"]
    missing = {uuid: count for uuid, count in counts.items() if count < int(args_cli.target_per_object)}
    if missing:
        raise SystemExit(f"Verified grasp collection did not reach target counts: {missing}")
    print(f"DEXTRAH_FRANKA_MULTI_OBJECT_VERIFIED_GRASPS_WRITTEN {output_path}", flush=True)


if __name__ == "__main__":
    main()
