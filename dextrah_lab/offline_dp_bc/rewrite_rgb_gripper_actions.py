"""Rewrite RGB BC dataset gripper labels to the DEXTRAH action convention.

The Franka cube environment interprets the 7th action channel as a normalized
gripper target: ``+1`` opens and ``-1`` closes.  Some contact-relabel datasets
derive a loose close gap from cube size and therefore label close/lift phases
with a positive value.  This helper makes the phase-based convention explicit
for BC training without changing images, robot-state observations, episode
boundaries, or any metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    return value


def rewrite_dataset(
    *,
    input_path: Path,
    output_path: Path,
    report_path: Path,
    open_action: float,
    close_action: float,
    open_phases: set[int],
    close_phases: set[int],
) -> dict[str, Any]:
    data = np.load(input_path, allow_pickle=False)
    missing = sorted({"action", "phase_ids", "episode_ends"}.difference(data.files))
    if missing:
        raise KeyError(f"{input_path} missing required keys: {missing}")

    action = np.asarray(data["action"], dtype=np.float32).copy()
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if action.ndim != 2 or action.shape[1] != 7:
        raise ValueError(f"Expected action shape (N,7), got {action.shape}")
    if phase_ids.shape != (action.shape[0],):
        raise ValueError(f"Expected phase_ids shape ({action.shape[0]},), got {phase_ids.shape}")
    if episode_ends.ndim != 1 or int(episode_ends[-1]) != int(action.shape[0]):
        raise ValueError("episode_ends must be cumulative exclusive ends ending at action length")

    before_gripper = action[:, 6].copy()
    open_mask = np.isin(phase_ids, np.asarray(sorted(open_phases), dtype=np.int32))
    close_mask = np.isin(phase_ids, np.asarray(sorted(close_phases), dtype=np.int32))
    overlap = open_mask & close_mask
    if np.any(overlap):
        phases = sorted(int(v) for v in np.unique(phase_ids[overlap]))
        raise ValueError(f"open_phases and close_phases overlap in rows with phases {phases}")
    action[open_mask, 6] = float(open_action)
    action[close_mask, 6] = float(close_action)

    save_kwargs: dict[str, Any] = {key: np.asarray(data[key]) for key in data.files}
    save_kwargs["action"] = action
    save_kwargs["gripper_action_rewrite_source_npz"] = np.asarray(str(input_path))
    save_kwargs["gripper_action_rewrite_open_action"] = np.asarray(float(open_action), dtype=np.float32)
    save_kwargs["gripper_action_rewrite_close_action"] = np.asarray(float(close_action), dtype=np.float32)
    save_kwargs["gripper_action_rewrite_open_phases"] = np.asarray(sorted(open_phases), dtype=np.int32)
    save_kwargs["gripper_action_rewrite_close_phases"] = np.asarray(sorted(close_phases), dtype=np.int32)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **save_kwargs)

    phase_unique, phase_counts = np.unique(phase_ids, return_counts=True)
    before_unique, before_counts = np.unique(np.round(before_gripper, 6), return_counts=True)
    after_unique, after_counts = np.unique(np.round(action[:, 6], 6), return_counts=True)
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "rows": int(action.shape[0]),
        "episodes": int(episode_ends.shape[0]),
        "open_action": float(open_action),
        "close_action": float(close_action),
        "open_phases": sorted(int(v) for v in open_phases),
        "close_phases": sorted(int(v) for v in close_phases),
        "open_rows": int(np.count_nonzero(open_mask)),
        "close_rows": int(np.count_nonzero(close_mask)),
        "unchanged_rows": int(action.shape[0] - np.count_nonzero(open_mask | close_mask)),
        "phase_counts": {str(int(k)): int(v) for k, v in zip(phase_unique, phase_counts)},
        "gripper_before_counts": {f"{float(k):.6f}": int(v) for k, v in zip(before_unique, before_counts)},
        "gripper_after_counts": {f"{float(k):.6f}": int(v) for k, v in zip(after_unique, after_counts)},
        "action_min": np.min(action, axis=0).astype(float).tolist(),
        "action_max": np.max(action, axis=0).astype(float).tolist(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _parse_phase_list(values: list[int]) -> set[int]:
    return {int(v) for v in values}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--open-action", type=float, default=1.0)
    parser.add_argument("--close-action", type=float, default=-1.0)
    parser.add_argument("--open-phase", action="append", type=int, default=[0])
    parser.add_argument("--close-phase", action="append", type=int, default=[1, 2])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = rewrite_dataset(
        input_path=args.input.expanduser().resolve(),
        output_path=args.output.expanduser().resolve(),
        report_path=args.report.expanduser().resolve(),
        open_action=float(args.open_action),
        close_action=float(args.close_action),
        open_phases=_parse_phase_list(args.open_phase),
        close_phases=_parse_phase_list(args.close_phase),
    )
    print("FRANKA_CUBE_RGB_GRIPPER_ACTION_REWRITE " + json.dumps(_to_builtin(summary), sort_keys=True))


if __name__ == "__main__":
    main()
