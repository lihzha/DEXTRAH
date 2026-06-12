"""Validate runtime phase/progress feature parity against a generated 25D NPZ.

This check is intentionally offline. It verifies that the runtime provider used
by the Isaac eval bridge reproduces the exact four appended features in
``contact_relabel_set_phase_progress.npz`` before any closed-loop run can use a
phase/progress-conditioned checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .ppo_bridge import (
    DatasetBackedPhaseProgressProvider,
    FRANKA_CUBE_LOWDIM_OBS_DIM,
    FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM,
    PHASE_PROGRESS_FEATURE_NAMES,
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="Generated 25D phase/progress NPZ.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for report/JSON/CSV artifacts.")
    parser.add_argument(
        "--episode",
        type=int,
        action="append",
        default=None,
        help="Episode index to check. Repeatable. Default checks all episodes.",
    )
    parser.add_argument("--atol", type=float, default=1.0e-7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if obs.ndim != 2 or obs.shape[1] < FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM:
        raise ValueError(f"Expected generated obs shape (N,{FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM}), got {obs.shape}")
    if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(obs.shape[0]):
        raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")
    if "phase_progress_features" in data.files:
        feature_names = tuple(str(v) for v in np.asarray(data["phase_progress_features"]).tolist())
        if feature_names != PHASE_PROGRESS_FEATURE_NAMES:
            raise ValueError(f"Unexpected phase/progress feature names: {feature_names}")
    else:
        feature_names = PHASE_PROGRESS_FEATURE_NAMES

    episodes = list(range(int(episode_ends.size))) if args.episode is None else [int(v) for v in args.episode]
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    rows: list[dict[str, Any]] = []
    max_abs_error = 0.0
    checked_rows = 0
    for episode_idx in episodes:
        if episode_idx < 0 or episode_idx >= int(episode_ends.size):
            raise ValueError(f"Episode index out of range: {episode_idx}")
        start = int(starts[episode_idx])
        end = int(episode_ends[episode_idx])
        provider = DatasetBackedPhaseProgressProvider.from_npz(
            dataset_path,
            episode_index=episode_idx,
            start_step=0,
        )
        local_steps = np.arange(end - start, dtype=np.int64)
        actual = provider.features_for_step(local_steps, int(local_steps.shape[0]))
        expected = obs[start:end, FRANKA_CUBE_LOWDIM_OBS_DIM:FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM]
        abs_error = np.abs(actual - expected)
        episode_max = float(np.max(abs_error)) if abs_error.size else 0.0
        max_abs_error = max(max_abs_error, episode_max)
        checked_rows += int(local_steps.shape[0])
        for local_step, row_idx, expected_row, actual_row, error_row in zip(
            local_steps,
            range(start, end),
            expected,
            actual,
            abs_error,
        ):
            rows.append(
                {
                    "episode": int(episode_idx),
                    "local_step": int(local_step),
                    "row": int(row_idx),
                    "max_abs_error": float(np.max(error_row)),
                    **{
                        f"expected_{name}": float(expected_row[idx])
                        for idx, name in enumerate(feature_names)
                    },
                    **{
                        f"actual_{name}": float(actual_row[idx])
                        for idx, name in enumerate(feature_names)
                    },
                }
            )

    status = "pass" if max_abs_error <= float(args.atol) else "fail"
    csv_path = output_dir / "phase_progress_runtime_provider_parity.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else ["episode", "local_step", "row", "max_abs_error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "status": status,
        "dataset": str(dataset_path),
        "obs_shape": list(obs.shape),
        "episode_ends": episode_ends.astype(int).tolist(),
        "episodes_checked": episodes,
        "checked_rows": checked_rows,
        "feature_names": list(feature_names),
        "max_abs_error": max_abs_error,
        "atol": float(args.atol),
        "csv": str(csv_path),
        "scope": "offline parity gate for runtime phase/progress provider; no training or Isaac rollout",
    }
    summary_path = output_dir / "phase_progress_runtime_provider_parity.json"
    summary_path.write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_path = output_dir / "phase_progress_runtime_provider_parity.md"
    lines = [
        "# Phase/Progress Runtime Provider Parity",
        "",
        f"- status: `{status}`",
        f"- dataset: `{dataset_path}`",
        f"- obs shape: `{tuple(obs.shape)}`",
        f"- episode ends: `{episode_ends.astype(int).tolist()}`",
        f"- episodes checked: `{episodes}`",
        f"- checked rows: `{checked_rows}`",
        f"- feature names: `{list(feature_names)}`",
        f"- max abs error: `{max_abs_error:.9g}`",
        f"- tolerance: `{float(args.atol):.9g}`",
        f"- CSV: `{csv_path}`",
        "",
        "This is an offline gate only. A pass means the deterministic runtime",
        "provider reproduces the generated NPZ features for accepted relabel",
        "episodes; it does not prove closed-loop behavior.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "FRANKA_CUBE_PHASE_PROGRESS_PROVIDER_PARITY "
        + json.dumps({"status": status, "report": str(report_path), "summary": str(summary_path)}, sort_keys=True)
    )
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
