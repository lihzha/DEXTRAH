"""Summarize a small contact-aware support-expansion relabel dataset.

This is an offline artifact generator. It compares a candidate relabel NPZ
against a baseline accepted relabel NPZ, reports perturbation metadata from the
rollout gate, and writes inspectable JSON/CSV/PNG/Markdown outputs before any
official Diffusion Policy training is considered.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ACTION_NAMES = [
    "rel_ee_dx",
    "rel_ee_dy",
    "rel_ee_dz",
    "rel_ee_drot_x",
    "rel_ee_drot_y",
    "rel_ee_drot_z",
    "gripper_command",
]

PHASE_NAMES = {
    0: "align_open",
    1: "close_hold",
    2: "lift",
}

SUPPORT_FEATURE_INDICES = np.asarray(
    [0, 1, 2, 7, 8, 9, 14, 15, 16, 17, 18, 19, 20],
    dtype=np.int64,
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _fmt(value: Any, digits: int = 4) -> str:
    value = _safe_float(value)
    if value is None:
        return "nan"
    return f"{value:.{digits}f}"


def _load_json_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    path = path.expanduser().resolve()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _episode_slices(episode_ends: np.ndarray) -> list[slice]:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return [slice(int(start), int(end)) for start, end in zip(starts, episode_ends)]


def _nearest_support_distances(candidate_obs: np.ndarray, baseline_obs: np.ndarray) -> np.ndarray:
    base = baseline_obs[:, SUPPORT_FEATURE_INDICES].astype(np.float64)
    cand = candidate_obs[:, SUPPORT_FEATURE_INDICES].astype(np.float64)
    scale = np.std(base, axis=0)
    scale = np.where(scale < 1.0e-6, 1.0, scale)
    base_n = (base - np.mean(base, axis=0)) / scale
    cand_n = (cand - np.mean(base, axis=0)) / scale
    distances = np.empty(cand_n.shape[0], dtype=np.float64)
    chunk = 1024
    for start in range(0, cand_n.shape[0], chunk):
        end = min(start + chunk, cand_n.shape[0])
        diff = cand_n[start:end, None, :] - base_n[None, :, :]
        distances[start:end] = np.sqrt(np.sum(diff * diff, axis=-1)).min(axis=1)
    return distances


def _phase_counts(phase_ids: np.ndarray) -> dict[str, int]:
    if phase_ids.size == 0:
        return {}
    unique, counts = np.unique(phase_ids.astype(int), return_counts=True)
    return {PHASE_NAMES.get(int(phase), str(int(phase))): int(count) for phase, count in zip(unique, counts)}


def _action_stats(action: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, name in enumerate(ACTION_NAMES):
        col = action[:, idx].astype(np.float64)
        rows.append(
            {
                "channel": idx,
                "name": name,
                "min": float(np.min(col)),
                "p05": float(np.percentile(col, 5)),
                "mean": float(np.mean(col)),
                "p50": float(np.percentile(col, 50)),
                "p95": float(np.percentile(col, 95)),
                "max": float(np.max(col)),
                "std": float(np.std(col)),
            }
        )
    return rows


def _rollout_rows_from_summary(summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if summary is None:
        return []
    rows: list[dict[str, Any]] = []
    for row in summary.get("rollouts", []):
        rows.append(
            {
                "rollout_id": row.get("rollout_id", ""),
                "gate_pass": bool(row.get("gate_pass", False)),
                "reset_joint_blend_alpha": _safe_float(row.get("reset_joint_blend_alpha")),
                "steps": int(row.get("steps", 0) or 0),
                "final_ee_to_cube": _safe_float(row.get("final_ee_to_cube")),
                "final_finger_center_to_cube": _safe_float(row.get("final_finger_center_to_cube")),
                "final_cube_lift_height": _safe_float(row.get("final_cube_lift_height")),
                "max_cube_lift_height": _safe_float(row.get("max_cube_lift_height")),
                "final_gripper_width": _safe_float(row.get("final_gripper_width")),
                "max_pose_action_clip_fraction": _safe_float(row.get("max_pose_action_clip_fraction")),
                "reset_cube_minus_ee_l2_from_dataset": _safe_float(row.get("reset_cube_minus_ee_l2_from_dataset")),
                "failure_reasons": row.get("failure_reasons", ""),
                "video": row.get("video", ""),
            }
        )
    return rows


def _episode_rows(
    *,
    episode_ends: np.ndarray,
    rollout_ids: np.ndarray,
    rollout_alphas: np.ndarray,
    phase_ids: np.ndarray,
    distances: np.ndarray,
    action: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ep_idx, ep_slice in enumerate(_episode_slices(episode_ends)):
        phase_slice = phase_ids[ep_slice] if phase_ids.size else np.asarray([], dtype=np.int32)
        action_slice = action[ep_slice]
        dist_slice = distances[ep_slice]
        row = {
            "episode_index": ep_idx,
            "rollout_id": str(rollout_ids[ep_idx]) if ep_idx < rollout_ids.shape[0] else "",
            "reset_joint_blend_alpha": float(rollout_alphas[ep_idx]) if ep_idx < rollout_alphas.shape[0] else float("nan"),
            "start": int(ep_slice.start or 0),
            "end": int(ep_slice.stop or 0),
            "length": int((ep_slice.stop or 0) - (ep_slice.start or 0)),
            "nearest_support_min": float(np.min(dist_slice)),
            "nearest_support_p50": float(np.percentile(dist_slice, 50)),
            "nearest_support_p95": float(np.percentile(dist_slice, 95)),
            "nearest_support_max": float(np.max(dist_slice)),
            "phase_counts": json.dumps(_phase_counts(phase_slice), sort_keys=True),
        }
        for idx, name in enumerate(ACTION_NAMES):
            col = action_slice[:, idx].astype(np.float64)
            row[f"{name}_min"] = float(np.min(col))
            row[f"{name}_max"] = float(np.max(col))
            row[f"{name}_mean"] = float(np.mean(col))
        rows.append(row)
    return rows


def _plot(
    *,
    output_path: Path,
    episode_rows: list[dict[str, Any]],
    phase_ids: np.ndarray,
    action: np.ndarray,
    distances: np.ndarray,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.0), constrained_layout=True)
    labels = [row["rollout_id"] for row in episode_rows]
    x = np.arange(len(episode_rows))
    axes[0, 0].bar(x, [float(row["nearest_support_p50"]) for row in episode_rows], label="p50")
    axes[0, 0].scatter(x, [float(row["nearest_support_max"]) for row in episode_rows], color="tab:red", label="max")
    axes[0, 0].set_title("Nearest Baseline Support Distance By Rollout")
    axes[0, 0].set_ylabel("scaled distance")
    axes[0, 0].set_xticks(x, labels, rotation=35, ha="right")
    axes[0, 0].grid(True, axis="y", alpha=0.25)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].hist(distances, bins=32, color="tab:blue", alpha=0.75)
    axes[0, 1].set_title("Candidate Rows vs Baseline Support")
    axes[0, 1].set_xlabel("nearest support distance")
    axes[0, 1].set_ylabel("rows")
    axes[0, 1].grid(True, alpha=0.25)

    if phase_ids.size:
        phases = sorted(set(int(v) for v in phase_ids.tolist()))
        counts = [int(np.sum(phase_ids == phase)) for phase in phases]
        axes[1, 0].bar([PHASE_NAMES.get(phase, str(phase)) for phase in phases], counts)
    axes[1, 0].set_title("Phase Coverage")
    axes[1, 0].set_ylabel("rows")
    axes[1, 0].grid(True, axis="y", alpha=0.25)

    for idx, name in enumerate(("rel_ee_dx", "rel_ee_dy", "rel_ee_dz", "gripper_command")):
        action_idx = ACTION_NAMES.index(name)
        axes[1, 1].plot(action[:, action_idx], linewidth=0.8, label=name)
    axes[1, 1].set_title("Action Channels Over Candidate Dataset")
    axes[1, 1].set_xlabel("row")
    axes[1, 1].set_ylabel("action")
    axes[1, 1].grid(True, alpha=0.25)
    axes[1, 1].legend(fontsize=8)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _report(summary: dict[str, Any], episode_rows: list[dict[str, Any]], rollout_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Franka Cube Support-Expansion Relabel Dataset",
        "",
        "This offline artifact summarizes a bounded contact-aware support-expansion candidate before any official Diffusion Policy training.",
        "",
        "## Summary",
        "",
        f"- candidate dataset: `{summary['candidate_dataset']}`",
        f"- baseline dataset: `{summary['baseline_dataset']}`",
        f"- obs/action shape: `{summary['obs_shape']}` / `{summary['action_shape']}`",
        f"- episode ends: `{summary['episode_ends']}`",
        f"- phase counts: `{summary['phase_counts']}`",
        f"- nearest baseline support distance p50/p95/max: `{summary['nearest_support_p50']:.4f}` / `{summary['nearest_support_p95']:.4f}` / `{summary['nearest_support_max']:.4f}`",
        "",
        "## Rollout Gate Rows",
        "",
        "| rollout | pass | alpha | steps | final EE | final finger | final/max lift | clip | failures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rollout_rows:
        lines.append(
            f"| {row['rollout_id']} | {row['gate_pass']} | "
            f"{_fmt(row.get('reset_joint_blend_alpha'), 3)} | {row['steps']} | "
            f"{_fmt(row.get('final_ee_to_cube'))} | "
            f"{_fmt(row.get('final_finger_center_to_cube'))} | "
            f"{_fmt(row.get('final_cube_lift_height'))}/{_fmt(row.get('max_cube_lift_height'))} | "
            f"{_fmt(row.get('max_pose_action_clip_fraction'), 3)} | "
            f"{row.get('failure_reasons', '')} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Episodes",
            "",
            "| episode | rollout | alpha | rows | nearest p50 | nearest p95 | nearest max | phases |",
            "|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in episode_rows:
        lines.append(
            f"| {row['episode_index']} | {row['rollout_id']} | {row['reset_joint_blend_alpha']:.3f} | "
            f"{row['length']} | {row['nearest_support_p50']:.4f} | {row['nearest_support_p95']:.4f} | "
            f"{row['nearest_support_max']:.4f} | `{row['phase_counts']}` |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- summary JSON: `{summary['summary_json']}`",
            f"- episode CSV: `{summary['episode_csv']}`",
            f"- action stats CSV: `{summary['action_stats_csv']}`",
            f"- plot: `{summary['plot']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dataset", required=True, type=Path)
    parser.add_argument("--baseline-dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--rollout-summary-json", default=None, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = args.candidate_dataset.expanduser().resolve()
    baseline_path = args.baseline_dataset.expanduser().resolve()
    candidate = np.load(candidate_path, allow_pickle=False)
    baseline = np.load(baseline_path, allow_pickle=False)
    obs = np.asarray(candidate["obs"], dtype=np.float32)
    action = np.asarray(candidate["action"], dtype=np.float32)
    episode_ends = np.asarray(candidate["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(candidate["phase_ids"], dtype=np.int32) if "phase_ids" in candidate.files else np.asarray([], dtype=np.int32)
    rollout_ids = np.asarray(candidate["rollout_ids"]) if "rollout_ids" in candidate.files else np.asarray([], dtype=str)
    rollout_alphas = (
        np.asarray(candidate["rollout_reset_joint_blend_alpha"], dtype=np.float32)
        if "rollout_reset_joint_blend_alpha" in candidate.files
        else np.full((episode_ends.shape[0],), np.nan, dtype=np.float32)
    )
    baseline_obs = np.asarray(baseline["obs"], dtype=np.float32)
    distances = _nearest_support_distances(obs, baseline_obs)
    episode_rows = _episode_rows(
        episode_ends=episode_ends,
        rollout_ids=rollout_ids,
        rollout_alphas=rollout_alphas,
        phase_ids=phase_ids,
        distances=distances,
        action=action,
    )
    rollout_summary = _load_json_optional(args.rollout_summary_json)
    rollout_rows = _rollout_rows_from_summary(rollout_summary)
    action_rows = _action_stats(action)

    episode_csv = output_dir / "support_expansion_episodes.csv"
    action_stats_csv = output_dir / "support_expansion_action_stats.csv"
    summary_json = output_dir / "support_expansion_summary.json"
    report_md = output_dir / "support_expansion_report.md"
    plot_path = output_dir / "support_expansion_plot.png"
    _write_csv(episode_csv, episode_rows)
    _write_csv(action_stats_csv, action_rows)
    _plot(output_path=plot_path, episode_rows=episode_rows, phase_ids=phase_ids, action=action, distances=distances)

    summary = {
        "candidate_dataset": str(candidate_path),
        "baseline_dataset": str(baseline_path),
        "obs_shape": list(obs.shape),
        "action_shape": list(action.shape),
        "episode_ends": episode_ends.astype(int).tolist(),
        "rollout_ids": [str(v) for v in rollout_ids.tolist()],
        "rollout_reset_joint_blend_alpha": rollout_alphas.astype(float).tolist(),
        "phase_counts": _phase_counts(phase_ids),
        "nearest_support_min": float(np.min(distances)),
        "nearest_support_p50": float(np.percentile(distances, 50)),
        "nearest_support_p95": float(np.percentile(distances, 95)),
        "nearest_support_max": float(np.max(distances)),
        "summary_json": str(summary_json),
        "episode_csv": str(episode_csv),
        "action_stats_csv": str(action_stats_csv),
        "plot": str(plot_path),
        "report": str(report_md),
        "rollout_summary_json": str(args.rollout_summary_json) if args.rollout_summary_json else "",
        "rollouts": rollout_rows,
        "episodes": episode_rows,
        "action_stats": action_rows,
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(_report(summary, episode_rows, rollout_rows), encoding="utf-8")
    print(
        "FRANKA_CUBE_SUPPORT_EXPANSION_DATASET_REPORT_DONE "
        + json.dumps({"summary_json": str(summary_json), "report": str(report_md), "plot": str(plot_path)}, sort_keys=True),
        flush=True,
    )


if __name__ == "__main__":
    main()
