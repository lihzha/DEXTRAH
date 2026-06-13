"""Create inspectable reports for Franka cube lowdim DP datasets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .dp_dataset import FrankaCubeLowdimDataset


OBS_FIELD_NAMES = [
    "ee_pos_x",
    "ee_pos_y",
    "ee_pos_z",
    "ee_quat_w",
    "ee_quat_x",
    "ee_quat_y",
    "ee_quat_z",
    "cube_pos_x",
    "cube_pos_y",
    "cube_pos_z",
    "cube_quat_w",
    "cube_quat_x",
    "cube_quat_y",
    "cube_quat_z",
    "cube_minus_ee_x",
    "cube_minus_ee_y",
    "cube_minus_ee_z",
    "cube_goal_delta_x",
    "cube_goal_delta_y",
    "cube_goal_delta_z",
    "gripper_width",
]

ACTION_FIELD_NAMES = [
    "rel_ee_dx",
    "rel_ee_dy",
    "rel_ee_dz",
    "rel_ee_drot_x",
    "rel_ee_drot_y",
    "rel_ee_drot_z",
    "gripper_command",
]


def _field_names(base_names: list[str], dim: int, prefix: str) -> list[str]:
    if dim <= len(base_names):
        return base_names[:dim]
    return base_names + [f"{prefix}_{idx}" for idx in range(len(base_names), dim)]


def _to_builtin(value: Any) -> Any:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _to_builtin(value.item())
        return [_to_builtin(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    return value


def _vector_stats(values: np.ndarray, names: list[str]) -> list[dict[str, Any]]:
    rows = []
    for idx, name in enumerate(names):
        col = values[:, idx].astype(np.float64)
        rows.append(
            {
                "index": idx,
                "name": name,
                "min": float(np.min(col)),
                "max": float(np.max(col)),
                "mean": float(np.mean(col)),
                "std": float(np.std(col)),
                "p01": float(np.percentile(col, 1.0)),
                "p50": float(np.percentile(col, 50.0)),
                "p99": float(np.percentile(col, 99.0)),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _normalizer_summary(dataset: FrankaCubeLowdimDataset) -> dict[str, Any]:
    normalizer = dataset.get_normalizer()
    state = normalizer.state_dict()
    summary: dict[str, Any] = {
        "class": normalizer.__class__.__name__,
        "fields": {},
    }
    for key, value in state.items():
        arr = np.asarray(_to_builtin(value), dtype=np.float64)
        summary["fields"][key] = {
            "shape": list(arr.shape),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "values": arr.astype(float).tolist(),
        }
    return summary


def _phase_summary(data: np.lib.npyio.NpzFile) -> dict[str, Any]:
    if "phase_ids" not in data.files:
        return {"available": False}
    phase_ids = np.asarray(data["phase_ids"])
    unique, counts = np.unique(phase_ids, return_counts=True)
    return {
        "available": True,
        "counts": {str(_to_builtin(k)): int(v) for k, v in zip(unique, counts)},
    }


def _validate_expected(
    *,
    obs: np.ndarray,
    action: np.ndarray,
    episode_ends: np.ndarray,
    expected_obs_dim: int,
    expected_action_dim: int,
    expected_episode_ends: list[int] | None,
) -> list[str]:
    errors: list[str] = []
    if obs.ndim != 2 or obs.shape[1] != expected_obs_dim:
        errors.append(f"expected obs (*, {expected_obs_dim}), got {tuple(obs.shape)}")
    if action.ndim != 2 or action.shape[1] != expected_action_dim:
        errors.append(f"expected action (*, {expected_action_dim}), got {tuple(action.shape)}")
    if obs.shape[0] != action.shape[0]:
        errors.append(f"obs/action row mismatch: {obs.shape[0]} vs {action.shape[0]}")
    if episode_ends.ndim != 1 or episode_ends.shape[0] == 0 or episode_ends[-1] != obs.shape[0]:
        errors.append("episode_ends must be 1D cumulative exclusive ends ending at obs length")
    if expected_episode_ends is not None and episode_ends.astype(int).tolist() != expected_episode_ends:
        errors.append(
            f"expected episode_ends {expected_episode_ends}, got {episode_ends.astype(int).tolist()}"
        )
    return errors


def _markdown_table(rows: list[dict[str, Any]], columns: list[str], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit is not None else rows
    lines = [
        "|" + "|".join(columns) + "|",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for row in selected:
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("|" + "|".join(values) + "|")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--horizon", type=int, default=16)
    parser.add_argument("--pad-before", type=int, default=1)
    parser.add_argument("--pad-after", type=int, default=7)
    parser.add_argument("--val-ratio", type=float, default=0.25)
    parser.add_argument(
        "--action-normalizer",
        choices=("identity", "limits", "limits_clamp_constant"),
        default="identity",
    )
    parser.add_argument("--expected-obs-dim", type=int, default=21)
    parser.add_argument("--expected-action-dim", type=int, default=7)
    parser.add_argument(
        "--expected-episode-ends",
        default="282,563,844,1126",
        help="Comma-separated expected cumulative episode ends, or empty to skip.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    episode_starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    episode_lengths = (episode_ends - episode_starts).astype(int).tolist()
    expected_episode_ends = (
        [int(v) for v in str(args.expected_episode_ends).split(",") if v.strip()]
        if str(args.expected_episode_ends).strip()
        else None
    )

    validation_errors = _validate_expected(
        obs=obs,
        action=action,
        episode_ends=episode_ends,
        expected_obs_dim=int(args.expected_obs_dim),
        expected_action_dim=int(args.expected_action_dim),
        expected_episode_ends=expected_episode_ends,
    )
    dataset = FrankaCubeLowdimDataset(
        str(dataset_path),
        horizon=int(args.horizon),
        pad_before=int(args.pad_before),
        pad_after=int(args.pad_after),
        val_ratio=float(args.val_ratio),
        action_normalizer=str(args.action_normalizer),
    )
    val_dataset = dataset.get_validation_dataset()
    sample = dataset[0]
    obs_base_names = OBS_FIELD_NAMES
    if obs.shape[1] > len(OBS_FIELD_NAMES) and "phase_progress_features" in data.files:
        obs_base_names = OBS_FIELD_NAMES + [str(v) for v in np.asarray(data["phase_progress_features"]).tolist()]
    obs_names = _field_names(obs_base_names, int(obs.shape[1]), "obs_extra")
    action_names = _field_names(ACTION_FIELD_NAMES, int(action.shape[1]), "action_extra")
    obs_stats = _vector_stats(obs, obs_names)
    action_stats = _vector_stats(action, action_names)
    normalizer = _normalizer_summary(dataset)

    summary = {
        "dataset_path": str(dataset_path),
        "npz_keys": sorted(data.files),
        "obs_shape": list(obs.shape),
        "action_shape": list(action.shape),
        "episode_ends": episode_ends.astype(int).tolist(),
        "episode_lengths": episode_lengths,
        "num_episodes": int(episode_ends.shape[0]),
        "train_samples": int(len(dataset)),
        "val_samples": int(len(val_dataset)),
        "horizon": int(args.horizon),
        "pad_before": int(args.pad_before),
        "pad_after": int(args.pad_after),
        "val_ratio": float(args.val_ratio),
        "action_normalizer": str(args.action_normalizer),
        "sample_obs_shape": list(sample["obs"].shape),
        "sample_action_shape": list(sample["action"].shape),
        "validation_errors": validation_errors,
        "official_diffusion_policy_dataset_base": dataset.__class__.__mro__[1].__module__,
        "action_abs_max": float(np.max(np.abs(action))),
        "action_clip_fraction_abs_ge_1": float(np.mean(np.abs(action) >= 1.0)),
        "pose_action_abs_max": float(np.max(np.abs(action[:, :6]))),
        "pose_action_clip_fraction_abs_ge_1": float(np.mean(np.abs(action[:, :6]) >= 1.0)),
        "gripper_exact_bound_fraction": float(np.mean(np.abs(action[:, -1]) >= 1.0)),
        "gripper_command_min": float(np.min(action[:, -1])),
        "gripper_command_max": float(np.max(action[:, -1])),
        "phase_summary": _phase_summary(data),
        "normalizer": normalizer,
    }

    summary_path = output_dir / "dataset_summary.json"
    obs_csv = output_dir / "obs_range.csv"
    action_csv = output_dir / "action_range.csv"
    report_path = output_dir / "dataset_report.md"
    summary_path.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(obs_csv, obs_stats)
    _write_csv(action_csv, action_stats)

    verdict = "PASS" if not validation_errors else "FAIL"
    lines = [
        "# Franka Cube Lowdim DP Dataset Report",
        "",
        f"- verdict: `{verdict}`",
        f"- dataset: `{dataset_path}`",
        f"- obs shape: `{tuple(obs.shape)}`",
        f"- action shape: `{tuple(action.shape)}`",
        f"- episode ends: `{episode_ends.astype(int).tolist()}`",
        f"- episode lengths: `{episode_lengths}`",
        f"- train/val samples: `{len(dataset)}` / `{len(val_dataset)}`",
        f"- action normalizer: `{args.action_normalizer}`",
        f"- official DP dataset base: `{summary['official_diffusion_policy_dataset_base']}`",
        f"- action abs max: `{summary['action_abs_max']:.6g}`",
        f"- action clip fraction abs>=1: `{summary['action_clip_fraction_abs_ge_1']:.6g}`",
        f"- pose action abs max: `{summary['pose_action_abs_max']:.6g}`",
        f"- pose action clip fraction abs>=1: `{summary['pose_action_clip_fraction_abs_ge_1']:.6g}`",
        f"- gripper exact-bound fraction: `{summary['gripper_exact_bound_fraction']:.6g}`",
        f"- gripper command range: `{summary['gripper_command_min']:.6g}` to `{summary['gripper_command_max']:.6g}`",
        "",
        "## Validation",
        "",
    ]
    if validation_errors:
        lines.extend(f"- {err}" for err in validation_errors)
    else:
        lines.append("- Shapes and expected episode ends match the contact-aware relabel smoke target.")
    lines.extend(
        [
            "",
            "## Action Range",
            "",
            _markdown_table(
                action_stats,
                ["index", "name", "min", "max", "mean", "std", "p01", "p50", "p99"],
            ),
            "",
            "## Observation Range",
            "",
            _markdown_table(
                obs_stats,
                ["index", "name", "min", "max", "mean", "std", "p01", "p50", "p99"],
            ),
            "",
            "## Normalizer",
            "",
            "- obs normalizer: official `LinearNormalizer` limits fit.",
            f"- action normalizer: `{args.action_normalizer}`.",
            f"- normalizer fields: `{sorted(normalizer['fields'].keys())}`",
            "",
            "## Output Files",
            "",
            f"- JSON summary: `{summary_path}`",
            f"- obs range CSV: `{obs_csv}`",
            f"- action range CSV: `{action_csv}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FRANKA_CUBE_LOWDIM_DATASET_REPORT " + json.dumps({"verdict": verdict, "report": str(report_path)}))
    if validation_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
