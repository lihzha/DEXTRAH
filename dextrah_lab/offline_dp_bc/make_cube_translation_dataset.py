"""Translate Franka cube lowdim trajectories across cube start poses.

This is a geometry-preserving augmentation for closed-loop BC debugging.  It
duplicates each input episode at target cube positions by translating the
absolute EE position and cube position together.  The cube-minus-EE features,
goal delta, quaternions, phase/progress features, and relative EE action labels
are left unchanged, so the policy sees broader absolute reset coverage without
changing the demonstrated local grasp geometry.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .action_conversion import DEFAULT_DEXTRAH_ACTION_CONVENTION


def _episode_slices(episode_ends: np.ndarray) -> list[slice]:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return [slice(int(start), int(end)) for start, end in zip(starts, episode_ends)]


def _as_str_array(values: list[str]) -> np.ndarray:
    max_len = max((len(v) for v in values), default=1)
    return np.asarray(values, dtype=f"<U{max_len}")


def _episode_start_cube_positions(path: Path) -> np.ndarray:
    data = np.load(path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if obs.ndim != 2 or obs.shape[1] < 10:
        raise ValueError(f"{path}: expected obs shape (N, >=10), got {obs.shape}")
    if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(obs.shape[0]):
        raise ValueError(f"{path}: bad episode_ends")
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return obs[starts, 7:10].astype(np.float32, copy=True)


def _dedupe_positions(positions: np.ndarray, *, decimals: int = 5) -> np.ndarray:
    if positions.size == 0:
        return positions.reshape(0, 3).astype(np.float32)
    rounded = np.round(np.asarray(positions, dtype=np.float32).reshape(-1, 3), int(decimals))
    _unique, keep = np.unique(rounded, axis=0, return_index=True)
    keep_sorted = np.sort(keep)
    return np.asarray(positions, dtype=np.float32).reshape(-1, 3)[keep_sorted].astype(np.float32, copy=True)


def _target_positions_from_args(args: argparse.Namespace) -> np.ndarray:
    parts: list[np.ndarray] = []
    for raw in args.target_cube_pos or []:
        values = [float(v) for v in raw.split(",")]
        if len(values) != 3:
            raise ValueError(f"--target_cube_pos must be x,y,z, got {raw!r}")
        parts.append(np.asarray(values, dtype=np.float32)[None, :])
    for source in args.target_cube_positions_from or []:
        parts.append(_episode_start_cube_positions(source.expanduser().resolve()))
    if args.grid_x is not None or args.grid_y is not None:
        if args.grid_x is None or args.grid_y is None:
            raise ValueError("--grid_x and --grid_y must be provided together")
        z = float(args.grid_z)
        grid = [[float(x), float(y), z] for x in args.grid_x for y in args.grid_y]
        parts.append(np.asarray(grid, dtype=np.float32))
    if args.random_count > 0:
        rng = np.random.default_rng(int(args.seed))
        x = rng.uniform(float(args.random_x_range[0]), float(args.random_x_range[1]), int(args.random_count))
        y = rng.uniform(float(args.random_y_range[0]), float(args.random_y_range[1]), int(args.random_count))
        z = np.full_like(x, float(args.grid_z), dtype=np.float64)
        parts.append(np.stack((x, y, z), axis=1).astype(np.float32))
    if not parts:
        raise ValueError("Provide --target_cube_pos, --target_cube_positions_from, --grid_x/--grid_y, or --random_count")
    return _dedupe_positions(np.concatenate(parts, axis=0), decimals=int(args.dedupe_decimals))


def build_cube_translation_dataset(
    *,
    input_path: Path,
    output_path: Path,
    target_cube_positions: np.ndarray,
    include_original: bool,
    max_targets: int | None,
) -> dict[str, Any]:
    data = np.load(input_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if obs.ndim != 2 or obs.shape[1] not in (21, 25):
        raise ValueError(f"Expected obs shape (N, 21|25), got {obs.shape}")
    if action.ndim != 2 or action.shape != (obs.shape[0], 7):
        raise ValueError(f"Expected action shape ({obs.shape[0]}, 7), got {action.shape}")
    if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(obs.shape[0]):
        raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")

    targets = _dedupe_positions(target_cube_positions)
    if max_targets is not None and int(max_targets) > 0:
        targets = targets[: int(max_targets)]
    ep_slices = _episode_slices(episode_ends)
    input_rollout_ids = (
        [str(v) for v in np.asarray(data["rollout_ids"]).tolist()] if "rollout_ids" in data.files else []
    )

    obs_parts: list[np.ndarray] = []
    action_parts: list[np.ndarray] = []
    phase_parts: list[np.ndarray] = []
    source_phase_parts: list[np.ndarray] = []
    rollout_ids: list[str] = []
    episode_lengths: list[int] = []
    source_episode_ids: list[int] = []
    source_cube_positions: list[np.ndarray] = []
    target_positions_out: list[np.ndarray] = []

    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32) if "phase_ids" in data.files else None
    source_phase_ids = np.asarray(data["source_phase_ids"], dtype=np.int32) if "source_phase_ids" in data.files else None

    def append_episode(ep_idx: int, ep_slice: slice, target_cube: np.ndarray, tag: str) -> None:
        ep_obs = obs[ep_slice].astype(np.float32, copy=True)
        ep_action = action[ep_slice].astype(np.float32, copy=True)
        source_cube = ep_obs[0, 7:10].astype(np.float32, copy=True)
        delta = np.asarray(target_cube, dtype=np.float32) - source_cube
        translated_obs = ep_obs.copy()
        translated_obs[:, 0:3] = ep_obs[:, 0:3] + delta[None, :]
        translated_obs[:, 7:10] = ep_obs[:, 7:10] + delta[None, :]
        translated_obs[:, 14:17] = translated_obs[:, 7:10] - translated_obs[:, 0:3]
        obs_parts.append(translated_obs.astype(np.float32, copy=False))
        action_parts.append(ep_action)
        if phase_ids is not None:
            phase_parts.append(phase_ids[ep_slice].astype(np.int32, copy=True))
        if source_phase_ids is not None:
            source_phase_parts.append(source_phase_ids[ep_slice].astype(np.int32, copy=True))
        base_id = input_rollout_ids[ep_idx] if ep_idx < len(input_rollout_ids) else f"episode_{ep_idx}"
        rollout_ids.append(f"{base_id}__cube_{tag}")
        episode_lengths.append(int(translated_obs.shape[0]))
        source_episode_ids.append(int(ep_idx))
        source_cube_positions.append(source_cube)
        target_positions_out.append(np.asarray(target_cube, dtype=np.float32).copy())

    for ep_idx, ep_slice in enumerate(ep_slices):
        source_cube = obs[ep_slice][0, 7:10].astype(np.float32, copy=True)
        if include_original:
            append_episode(ep_idx, ep_slice, source_cube, "original")
        for target_idx, target_cube in enumerate(targets):
            append_episode(ep_idx, ep_slice, target_cube, f"target_{target_idx:03d}")

    obs_out = np.concatenate(obs_parts, axis=0).astype(np.float32)
    action_out = np.concatenate(action_parts, axis=0).astype(np.float32)
    episode_ends_out = np.cumsum(np.asarray(episode_lengths, dtype=np.int64))
    save_kwargs: dict[str, Any] = {
        "obs": obs_out,
        "action": action_out,
        "episode_ends": episode_ends_out,
        "rollout_ids": _as_str_array(rollout_ids),
        "cube_translation_source_npz": np.asarray(str(input_path)),
        "cube_translation_target_positions": np.asarray(targets, dtype=np.float32),
        "cube_translation_source_episode": np.asarray(source_episode_ids, dtype=np.int32),
        "cube_translation_source_cube_pos": np.asarray(source_cube_positions, dtype=np.float32),
        "cube_translation_target_cube_pos": np.asarray(target_positions_out, dtype=np.float32),
    }
    if phase_parts:
        save_kwargs["phase_ids"] = np.concatenate(phase_parts, axis=0).astype(np.int32)
    if source_phase_parts:
        save_kwargs["source_phase_ids"] = np.concatenate(source_phase_parts, axis=0).astype(np.int32)
    for key in ("phase_progress_features", "source_npz", "source_phase_mode"):
        if key in data.files:
            save_kwargs[key] = data[key]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **save_kwargs)

    starts = np.concatenate(([0], episode_ends_out[:-1])).astype(np.int64)
    start_cubes = obs_out[starts, 7:10]
    action_abs = np.abs(action_out[:, :6])
    phase_counts: dict[str, int] = {}
    if "phase_ids" in save_kwargs:
        unique, counts = np.unique(save_kwargs["phase_ids"], return_counts=True)
        phase_counts = {str(int(k)): int(v) for k, v in zip(unique, counts)}
    summary = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_steps": int(obs.shape[0]),
        "input_episodes": int(episode_ends.shape[0]),
        "output_steps": int(obs_out.shape[0]),
        "output_episodes": int(episode_ends_out.shape[0]),
        "obs_dim": int(obs_out.shape[1]),
        "include_original": bool(include_original),
        "target_count": int(targets.shape[0]),
        "target_positions": targets.astype(float).tolist(),
        "cube_start_min": np.min(start_cubes, axis=0).astype(float).tolist(),
        "cube_start_max": np.max(start_cubes, axis=0).astype(float).tolist(),
        "phase_counts": phase_counts,
        "action_absmax": float(action_abs.max()) if action_abs.size else 0.0,
        "pose_clip_fraction": float((action_abs >= 1.0 - 1.0e-6).mean()) if action_abs.size else 0.0,
        "action_convention": asdict(DEFAULT_DEXTRAH_ACTION_CONVENTION),
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target_cube_pos", action="append", default=[])
    parser.add_argument("--target_cube_positions_from", action="append", default=[], type=Path)
    parser.add_argument("--grid_x", nargs="*", type=float, default=None)
    parser.add_argument("--grid_y", nargs="*", type=float, default=None)
    parser.add_argument("--grid_z", type=float, default=0.781)
    parser.add_argument("--random_count", type=int, default=0)
    parser.add_argument("--random_x_range", nargs=2, type=float, default=(-0.44, -0.28))
    parser.add_argument("--random_y_range", nargs=2, type=float, default=(-0.20, -0.04))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dedupe_decimals", type=int, default=5)
    parser.add_argument("--max_targets", type=int, default=None)
    parser.add_argument("--include_original", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = _target_positions_from_args(args)
    summary = build_cube_translation_dataset(
        input_path=args.input.expanduser().resolve(),
        output_path=args.output.expanduser().resolve(),
        target_cube_positions=targets,
        include_original=bool(args.include_original),
        max_targets=args.max_targets,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
