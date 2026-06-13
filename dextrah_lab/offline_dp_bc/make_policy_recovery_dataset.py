"""Build a policy-recovery BC dataset from failed closed-loop traces.

The closed-loop one-demo DP fit can memorize the accepted demo offline but miss
the cube after small contact errors. This tool converts those failed live states
into supervised recovery examples by pairing each traced lowdim observation with
an oracle action derived from the matching demo timestep.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from .action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    apply_normalized_action_to_world_pose,
    derive_relative_ee_actions,
)


RESIDUAL_TARGET_ACTION_CONVENTION = replace(DEFAULT_DEXTRAH_ACTION_CONVENTION, clip_actions=False)
POSITION_FEATURE_IDX = np.asarray([0, 1, 2, 7, 8, 9, 14, 15, 16, 17, 18, 19, 20], dtype=np.int64)


def _episode_bounds(episode_ends: np.ndarray, episode: int) -> tuple[int, int]:
    if episode_ends.size == 0:
        raise ValueError("dataset has no episodes")
    ep_idx = int(np.clip(int(episode), 0, int(episode_ends.size - 1)))
    start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    end = int(episode_ends[ep_idx])
    return start, end


def _row_for_step(episode_ends: np.ndarray, episode: int, episode_step: int) -> tuple[int, int, int]:
    start, end = _episode_bounds(episode_ends, episode)
    local = int(np.clip(int(episode_step), 0, max(0, end - start - 1)))
    return int(start + local), int(start), int(end)


def _episode_start_for_row(episode_ends: np.ndarray, row_idx: int) -> int:
    episode = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    if episode <= 0:
        return 0
    return int(episode_ends[episode - 1])


def _nearest_row_by_scaled_features(base_obs: np.ndarray, live_obs: np.ndarray) -> tuple[int, float]:
    feature_std = np.maximum(base_obs[:, POSITION_FEATURE_IDX].std(axis=0), 1.0e-4).astype(np.float32)
    delta = (base_obs[:, POSITION_FEATURE_IDX] - live_obs[POSITION_FEATURE_IDX]) / feature_std
    distances = np.sqrt(np.mean(delta * delta, axis=1))
    idx = int(np.argmin(distances))
    return idx, float(distances[idx])


def _phase_from_obs_or_demo(live_obs: np.ndarray, phase_ids: np.ndarray, row_idx: int) -> int:
    if live_obs.shape[0] >= 24:
        return int(np.argmax(live_obs[21:24]))
    return int(phase_ids[row_idx]) if phase_ids.size else 0


def _first_close_row(base_action: np.ndarray, episode_ends: np.ndarray, episode: int) -> tuple[int, int]:
    start, end = _episode_bounds(episode_ends, episode)
    close_locals = np.flatnonzero(base_action[start:end, 6] < 0.0)
    if close_locals.size == 0:
        return int(end - 1), int(end - start - 1)
    local = int(close_locals[0])
    return int(start + local), local


def _target_action_from_live_state(
    live_obs: np.ndarray,
    demo_obs: np.ndarray,
    demo_action: np.ndarray,
    *,
    clip_actions: float | None,
) -> np.ndarray:
    target_pos, target_quat = apply_normalized_action_to_world_pose(
        demo_obs[None, :3],
        demo_obs[None, 3:7],
        demo_action[None],
        convention=DEFAULT_DEXTRAH_ACTION_CONVENTION,
    )
    ee_pos = np.stack((live_obs[:3], target_pos[0]), axis=0).astype(np.float32)
    ee_quat = np.stack((live_obs[3:7], target_quat[0]), axis=0).astype(np.float32)
    gripper = np.asarray([float(demo_action[6]), float(demo_action[6])], dtype=np.float32)
    action = derive_relative_ee_actions(
        ee_pos,
        ee_quat,
        gripper_action=gripper,
        convention=RESIDUAL_TARGET_ACTION_CONVENTION,
        terminal_action="drop",
    )[0].astype(np.float32, copy=False)
    if clip_actions is not None and np.isfinite(float(clip_actions)) and float(clip_actions) > 0.0:
        clip = float(clip_actions)
        action[:6] = np.clip(action[:6], -clip, clip)
        action[6] = np.clip(action[6], -1.0, 1.0)
    return action


def _load_policy_trace(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("policy_calls", [])
    if not isinstance(records, list):
        raise ValueError(f"{path}: policy_calls must be a list")
    return records


def build_policy_recovery_dataset(
    *,
    base_dataset: Path,
    trace_paths: list[Path],
    output_path: Path,
    demo_episode: int,
    demo_start_step: int,
    original_copies: int,
    clip_actions: float | None,
    label_mode: str,
    contact_gate_cme_norm: float,
    min_trace_step: int | None,
    max_trace_step: int | None,
) -> dict[str, Any]:
    data = np.load(base_dataset, allow_pickle=False)
    base_obs = np.asarray(data["obs"], dtype=np.float32)
    base_action = np.asarray(data["action"], dtype=np.float32)
    base_episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    phase_ids = (
        np.asarray(data["phase_ids"], dtype=np.int32)
        if "phase_ids" in data.files
        else np.zeros(base_obs.shape[0], dtype=np.int32)
    )
    if base_obs.ndim != 2 or base_action.ndim != 2 or base_obs.shape[0] != base_action.shape[0]:
        raise ValueError(f"Bad base obs/action shapes: {base_obs.shape} vs {base_action.shape}")
    if base_action.shape[1] != 7:
        raise ValueError(f"Expected 7D base actions, got {base_action.shape[1]}")
    valid_label_modes = {
        "residual_to_demo_target",
        "dataset_step_action",
        "residual_to_nearest_demo_target",
        "residual_to_nearest_pose_timed_gripper",
        "residual_to_timed_contact_gated_gripper",
        "nearest_dataset_step_action",
    }
    if label_mode not in valid_label_modes:
        raise ValueError(f"Unsupported label_mode {label_mode!r}")

    out_obs: list[np.ndarray] = []
    out_action: list[np.ndarray] = []
    out_phase: list[np.ndarray] = []
    episode_lengths: list[int] = []
    rollout_ids: list[str] = []
    source_trace_paths: list[str] = []
    source_trace_steps: list[np.ndarray] = []
    source_demo_rows: list[np.ndarray] = []
    source_demo_steps: list[np.ndarray] = []
    source_label_modes: list[str] = []

    base_start, base_end = _episode_bounds(base_episode_ends, demo_episode)
    first_close_row, first_close_local = _first_close_row(base_action, base_episode_ends, demo_episode)
    preclose_row = max(base_start, first_close_row - 1)
    base_slice = slice(base_start, base_end)
    for copy_idx in range(max(0, int(original_copies))):
        out_obs.append(base_obs[base_slice].astype(np.float32, copy=True))
        out_action.append(base_action[base_slice].astype(np.float32, copy=True))
        out_phase.append(phase_ids[base_slice].astype(np.int32, copy=True))
        episode_lengths.append(int(base_end - base_start))
        rollout_ids.append(f"demo_episode_{int(demo_episode)}__original_{copy_idx:03d}")
        source_trace_paths.append(str(base_dataset))
        source_trace_steps.append(np.arange(base_end - base_start, dtype=np.int32))
        source_demo_rows.append(np.arange(base_start, base_end, dtype=np.int32))
        source_demo_steps.append(np.arange(base_end - base_start, dtype=np.int32))
        source_label_modes.append("original")

    recovery_summaries: list[dict[str, Any]] = []
    for trace_idx, trace_path in enumerate(trace_paths):
        records = _load_policy_trace(trace_path)
        rec_obs: list[np.ndarray] = []
        rec_action: list[np.ndarray] = []
        rec_phase: list[int] = []
        rec_trace_steps: list[int] = []
        rec_demo_rows: list[int] = []
        rec_demo_steps: list[int] = []
        skipped = 0
        skipped_by_step_filter = 0
        for record in records:
            if "lowdim_obs" not in record:
                skipped += 1
                continue
            live_obs = np.asarray(record["lowdim_obs"], dtype=np.float32)
            if live_obs.ndim != 1:
                skipped += 1
                continue
            if live_obs.shape[0] != base_obs.shape[1]:
                raise ValueError(
                    f"{trace_path}: live obs dim {live_obs.shape[0]} does not match base obs dim {base_obs.shape[1]}"
                )
            rollout_step = int(record.get("step", len(rec_obs)))
            if min_trace_step is not None and rollout_step < int(min_trace_step):
                skipped_by_step_filter += 1
                continue
            if max_trace_step is not None and rollout_step > int(max_trace_step):
                skipped_by_step_filter += 1
                continue
            time_demo_row, time_demo_start, time_demo_end = _row_for_step(
                base_episode_ends,
                int(demo_episode),
                int(demo_start_step) + rollout_step,
            )
            nearest_demo_row, nearest_distance = _nearest_row_by_scaled_features(base_obs, live_obs)
            if label_mode in {
                "nearest_dataset_step_action",
                "residual_to_nearest_demo_target",
                "residual_to_nearest_pose_timed_gripper",
            }:
                demo_row = nearest_demo_row
                demo_start = _episode_start_for_row(base_episode_ends, demo_row)
            elif label_mode == "residual_to_timed_contact_gated_gripper":
                live_cme_norm = float(np.linalg.norm(live_obs[14:17]))
                use_preclose_target = (
                    rollout_step >= first_close_local
                    and live_cme_norm > float(contact_gate_cme_norm)
                )
                demo_row = preclose_row if use_preclose_target else time_demo_row
                demo_start = time_demo_start
            else:
                demo_row = time_demo_row
                demo_start = time_demo_start
            if label_mode in {"dataset_step_action", "nearest_dataset_step_action"}:
                label = base_action[demo_row].astype(np.float32, copy=True)
            else:
                label = _target_action_from_live_state(
                    live_obs,
                    base_obs[demo_row],
                    base_action[demo_row],
                    clip_actions=clip_actions,
                )
                if label_mode == "residual_to_nearest_pose_timed_gripper":
                    label[6] = base_action[time_demo_row, 6]
                elif label_mode == "residual_to_timed_contact_gated_gripper":
                    live_cme_norm = float(np.linalg.norm(live_obs[14:17]))
                    if rollout_step >= first_close_local and live_cme_norm > float(contact_gate_cme_norm):
                        label[6] = DEFAULT_DEXTRAH_ACTION_CONVENTION.open_gripper_action
                    else:
                        label[6] = base_action[time_demo_row, 6]
            rec_obs.append(live_obs.astype(np.float32, copy=True))
            rec_action.append(label.astype(np.float32, copy=True))
            rec_phase.append(_phase_from_obs_or_demo(live_obs, phase_ids, demo_row))
            rec_trace_steps.append(rollout_step)
            rec_demo_rows.append(demo_row)
            rec_demo_steps.append(int(demo_row - demo_start))
            _ = time_demo_end
        if not rec_obs:
            raise ValueError(f"{trace_path}: no usable lowdim_obs records")
        obs_i = np.stack(rec_obs, axis=0).astype(np.float32)
        action_i = np.stack(rec_action, axis=0).astype(np.float32)
        phase_i = np.asarray(rec_phase, dtype=np.int32)
        out_obs.append(obs_i)
        out_action.append(action_i)
        out_phase.append(phase_i)
        episode_lengths.append(int(obs_i.shape[0]))
        rollout_id = f"{trace_path.parent.name}__recovery_{trace_idx:03d}"
        rollout_ids.append(rollout_id)
        source_trace_paths.append(str(trace_path))
        source_trace_steps.append(np.asarray(rec_trace_steps, dtype=np.int32))
        source_demo_rows.append(np.asarray(rec_demo_rows, dtype=np.int32))
        source_demo_steps.append(np.asarray(rec_demo_steps, dtype=np.int32))
        source_label_modes.append(label_mode)
        recovery_summaries.append(
            {
                "trace_path": str(trace_path),
                "rollout_id": rollout_id,
                "records": int(obs_i.shape[0]),
                "skipped": int(skipped),
                "skipped_by_step_filter": int(skipped_by_step_filter),
                "trace_step_min": int(np.min(rec_trace_steps)),
                "trace_step_max": int(np.max(rec_trace_steps)),
                "demo_row_min": int(np.min(rec_demo_rows)),
                "demo_row_max": int(np.max(rec_demo_rows)),
                "action_absmax": float(np.max(np.abs(action_i[:, :6]))),
                "nearest_distance_mean": float(
                    np.mean(
                        [
                            _nearest_row_by_scaled_features(base_obs, obs_row)[1]
                            for obs_row in obs_i
                        ]
                    )
                ),
            }
        )

    obs_out = np.concatenate(out_obs, axis=0).astype(np.float32)
    action_out = np.concatenate(out_action, axis=0).astype(np.float32)
    phase_out = np.concatenate(out_phase, axis=0).astype(np.int32)
    episode_ends_out = np.cumsum(np.asarray(episode_lengths, dtype=np.int64))

    max_trace_len = max(arr.shape[0] for arr in source_trace_steps)
    trace_step_arr = np.full((len(source_trace_steps), max_trace_len), -1, dtype=np.int32)
    demo_row_arr = np.full_like(trace_step_arr, -1)
    demo_step_arr = np.full_like(trace_step_arr, -1)
    for idx, (steps, rows, demo_steps) in enumerate(zip(source_trace_steps, source_demo_rows, source_demo_steps)):
        trace_step_arr[idx, : steps.shape[0]] = steps
        demo_row_arr[idx, : rows.shape[0]] = rows
        demo_step_arr[idx, : demo_steps.shape[0]] = demo_steps

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        obs=obs_out,
        action=action_out,
        episode_ends=episode_ends_out,
        phase_ids=phase_out,
        rollout_ids=np.asarray(rollout_ids),
        recovery_source_trace_paths=np.asarray(source_trace_paths),
        recovery_source_trace_steps=trace_step_arr,
        recovery_demo_rows=demo_row_arr,
        recovery_demo_episode_steps=demo_step_arr,
        recovery_label_modes=np.asarray(source_label_modes),
        recovery_base_dataset=np.asarray(str(base_dataset)),
        recovery_clip_actions=np.asarray(-1.0 if clip_actions is None else float(clip_actions), dtype=np.float32),
    )

    action_abs = np.abs(action_out[:, :6])
    summary = {
        "base_dataset": str(base_dataset),
        "trace_paths": [str(path) for path in trace_paths],
        "output_path": str(output_path),
        "demo_episode": int(demo_episode),
        "demo_start_step": int(demo_start_step),
        "original_copies": int(original_copies),
        "label_mode": label_mode,
        "clip_actions": None if clip_actions is None else float(clip_actions),
        "contact_gate_cme_norm": float(contact_gate_cme_norm),
        "min_trace_step": None if min_trace_step is None else int(min_trace_step),
        "max_trace_step": None if max_trace_step is None else int(max_trace_step),
        "first_close_demo_row": int(first_close_row),
        "first_close_demo_step": int(first_close_local),
        "preclose_demo_row": int(preclose_row),
        "output_steps": int(obs_out.shape[0]),
        "output_episodes": int(episode_ends_out.shape[0]),
        "episode_lengths": [int(v) for v in episode_lengths],
        "obs_dim": int(obs_out.shape[1]),
        "action_absmax": float(action_abs.max()) if action_abs.size else 0.0,
        "pose_clip_fraction": float((action_abs >= 1.0 - 1.0e-6).mean()) if action_abs.size else 0.0,
        "recoveries": recovery_summaries,
        "action_convention": asdict(DEFAULT_DEXTRAH_ACTION_CONVENTION),
        "residual_target_action_convention": asdict(RESIDUAL_TARGET_ACTION_CONVENTION),
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base_dataset", required=True, type=Path)
    parser.add_argument("--policy_trace", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--demo_episode", type=int, default=0)
    parser.add_argument("--demo_start_step", type=int, default=0)
    parser.add_argument("--original_copies", type=int, default=4)
    parser.add_argument("--clip_actions", type=float, default=1.0)
    parser.add_argument(
        "--label_mode",
        choices=[
            "residual_to_demo_target",
            "dataset_step_action",
            "residual_to_nearest_demo_target",
            "residual_to_nearest_pose_timed_gripper",
            "residual_to_timed_contact_gated_gripper",
            "nearest_dataset_step_action",
        ],
        default="residual_to_demo_target",
    )
    parser.add_argument(
        "--contact_gate_cme_norm",
        type=float,
        default=0.04,
        help=(
            "For residual_to_timed_contact_gated_gripper, keep/reopen the gripper and "
            "use the pre-close pose target until ||cube_minus_ee|| is below this value."
        ),
    )
    parser.add_argument(
        "--min_trace_step",
        type=int,
        default=None,
        help="Optional inclusive minimum rollout step to keep from each failed policy trace.",
    )
    parser.add_argument(
        "--max_trace_step",
        type=int,
        default=None,
        help="Optional inclusive maximum rollout step to keep from each failed policy trace.",
    )
    args = parser.parse_args()
    summary = build_policy_recovery_dataset(
        base_dataset=args.base_dataset.expanduser().resolve(),
        trace_paths=[path.expanduser().resolve() for path in args.policy_trace],
        output_path=args.output.expanduser().resolve(),
        demo_episode=int(args.demo_episode),
        demo_start_step=int(args.demo_start_step),
        original_copies=max(0, int(args.original_copies)),
        clip_actions=None if float(args.clip_actions) <= 0.0 else float(args.clip_actions),
        label_mode=str(args.label_mode),
        contact_gate_cme_norm=float(args.contact_gate_cme_norm),
        min_trace_step=args.min_trace_step,
        max_trace_step=args.max_trace_step,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
