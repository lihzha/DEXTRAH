"""Build inspectable artifacts for Franka cube Diffusion Policy BC debugging.

The script reads existing official Diffusion Policy logs, checkpoint-smoke
logs, and fetched DEXTRAH/Isaac eval metrics. It does not launch training or
simulation; generated reports live in the external artifact namespace.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


AGENT_ID = "franka-cube-dp-bc-warmstart"
OFFICIAL_DP_REPO = "https://github.com/real-stanford/diffusion_policy"
OFFICIAL_DP_PAGE = "https://diffusion-policy.cs.columbia.edu/"
OFFICIAL_DP_COMMIT = "5ba07ac6661db573af695b419a7947ecb704690f"


@dataclass(frozen=True)
class TrainRun:
    key: str
    label: str
    log_relpath: str
    dataset_note: str
    checkpoint_note: str


@dataclass(frozen=True)
class EvalRun:
    key: str
    label: str
    metrics_relpath: str
    job_id: str
    checkpoint_note: str
    action_mode: str


TRAIN_RUNS = [
    TrainRun(
        key="approach_only_overfit2k",
        label="Approach-only overfit/debug",
        log_relpath="official_dp_debug/run_20260611_130917_curobo32_overfit2k/logs.json.txt",
        dataset_note="32 real cuRobo approach/pregrasp demonstrations",
        checkpoint_note="Approach/pregrasp only; cannot learn close/lift",
    ),
    TrainRun(
        key="full_pick_5epoch_503step",
        label="Full-pick/lift 5-epoch debug",
        log_relpath="official_dp_debug/run_20260611_131845_curobo32_full_pick_lift_debug/logs.json.txt",
        dataset_note="32 real cuRobo full-pick/lift demonstrations",
        checkpoint_note="503 global steps; undertrained but includes close/lift labels",
    ),
    TrainRun(
        key="full_pick_overfit2k",
        label="Full-pick/lift 25-epoch overfit2k",
        log_relpath="official_dp_debug/run_20260611_132410_curobo32_full_pick_lift_overfit2k/logs.json.txt",
        dataset_note="32 real cuRobo full-pick/lift demonstrations",
        checkpoint_note="2523 global steps; best current mechanics checkpoint",
    ),
]


EVAL_RUNS = [
    EvalRun(
        key="approach_only",
        label="Approach-only mechanics eval",
        metrics_relpath="cluster_evals/franka_cube_dp_eval_curobo8_smoke3_20260611_125635/metrics.json",
        job_id="1027713",
        checkpoint_note="approach/pregrasp checkpoint",
        action_mode="first-action replanning",
    ),
    EvalRun(
        key="full_pick_503_first_action",
        label="503-step full-pick first-action",
        metrics_relpath="cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558/metrics.json",
        job_id="1027722",
        checkpoint_note="full-pick/lift 5-epoch checkpoint",
        action_mode="first-action replanning",
    ),
    EvalRun(
        key="full_pick_503_chunk8",
        label="503-step full-pick chunk8",
        metrics_relpath="cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213/metrics.json",
        job_id="1027725",
        checkpoint_note="full-pick/lift 5-epoch checkpoint",
        action_mode="execute 8 predicted actions per policy call",
    ),
    EvalRun(
        key="full_pick_overfit2k_chunk8",
        label="Overfit2k full-pick chunk8",
        metrics_relpath=(
            "cluster_evals/"
            "franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_video_20260611_132637/"
            "metrics.json"
        ),
        job_id="1027727",
        checkpoint_note="full-pick/lift 25-epoch overfit2k checkpoint",
        action_mode="execute 8 predicted actions per policy call",
    ),
]


BRIDGE_SMOKE_LOGS = {
    "approach_only_first_open": "logs/official_dp_curobo32_overfit2k_checkpoint_smoke_100step.log",
    "full_pick_5epoch_first_open": "logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_first_warm_100step.log",
    "full_pick_5epoch_closed": "logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_closed_warm_100step.log",
    "full_pick_5epoch_lift_high": "logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_lift_high_warm_100step.log",
    "full_pick_overfit2k_first_open": "logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_first_warm_100step.log",
    "full_pick_overfit2k_closed": "logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_closed_warm_100step.log",
    "full_pick_overfit2k_lift_high": "logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_lift_high_warm_100step.log",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _last_with(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if key in row:
            return row
    return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summary_value(summary: dict[str, Any], metric: str, field: str) -> float | None:
    metric_summary = summary.get("step_metric_summary") or {}
    if metric in metric_summary and isinstance(metric_summary[metric], dict):
        return _safe_float(metric_summary[metric].get(field))
    return None


def _parse_smoke_payload(path: Path) -> dict[str, Any]:
    prefix = "FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED "
    payload = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                payload = json.loads(line[len(prefix) :])
    if payload is None:
        raise ValueError(f"No checkpoint-smoke payload in {path}")
    return payload


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _format_num(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    try:
        if digits == 0:
            return str(int(round(float(value))))
        return f"{float(value):.{digits}g}"
    except (TypeError, ValueError):
        return str(value)


def _plot_training(artifact_root: Path, out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train_summaries: list[dict[str, Any]] = []
    run_rows: dict[str, list[dict[str, Any]]] = {}

    for run in TRAIN_RUNS:
        path = artifact_root / run.log_relpath
        rows = _read_jsonl(path)
        run_rows[run.key] = rows
        final = rows[-1]
        val_row = _last_with(rows, "val_loss")
        mse_row = _last_with(rows, "train_action_mse_error")
        train_summaries.append(
            {
                "key": run.key,
                "label": run.label,
                "log_path": str(path),
                "dataset_note": run.dataset_note,
                "checkpoint_note": run.checkpoint_note,
                "rows": len(rows),
                "final_global_step": final.get("global_step"),
                "final_epoch": final.get("epoch"),
                "final_train_loss": _safe_float(final.get("train_loss")),
                "final_val_loss": _safe_float((val_row or {}).get("val_loss")),
                "final_train_action_mse_error": _safe_float(
                    (mse_row or {}).get("train_action_mse_error")
                ),
            }
        )

    full_pick = [r for r in TRAIN_RUNS if r.key in {"full_pick_5epoch_503step", "full_pick_overfit2k"}]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), constrained_layout=True)
    for run in full_pick:
        rows = run_rows[run.key]
        steps = np.asarray([r["global_step"] for r in rows if "train_loss" in r], dtype=float)
        losses = np.asarray([r["train_loss"] for r in rows if "train_loss" in r], dtype=float)
        axes[0].plot(steps, losses, linewidth=1.0, alpha=0.7, label=f"{run.label} train")
        val_steps = np.asarray([r["global_step"] for r in rows if "val_loss" in r], dtype=float)
        val_losses = np.asarray([r["val_loss"] for r in rows if "val_loss" in r], dtype=float)
        axes[1].plot(val_steps, val_losses, marker="o", linewidth=1.5, label=f"{run.label} val")
    axes[0].set_title("Train Loss")
    axes[1].set_title("Validation Loss")
    for ax in axes:
        ax.set_xlabel("global_step")
        ax.set_ylabel("loss")
        ax.set_yscale("log")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    loss_plot = out_dir / "full_pick_train_val_loss_5epoch_vs_25epoch.png"
    fig.savefig(loss_plot, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    for run in full_pick:
        rows = run_rows[run.key]
        mse_steps = np.asarray([r["global_step"] for r in rows if "train_action_mse_error" in r], dtype=float)
        mse_values = np.asarray([r["train_action_mse_error"] for r in rows if "train_action_mse_error" in r], dtype=float)
        ax.plot(mse_steps, mse_values, marker="o", linewidth=1.5, label=run.label)
    ax.set_title("Train Action MSE")
    ax.set_xlabel("global_step")
    ax.set_ylabel("MSE")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    mse_plot = out_dir / "full_pick_train_action_mse_5epoch_vs_25epoch.png"
    fig.savefig(mse_plot, dpi=180)
    plt.close(fig)

    return train_summaries


def _bridge_smoke_summaries(artifact_root: Path, out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for key, relpath in BRIDGE_SMOKE_LOGS.items():
        path = artifact_root / relpath
        payload = _parse_smoke_payload(path)
        selected_gripper = np.asarray(payload.get("selected_gripper_width", []), dtype=float)
        selected_ee_z = np.asarray(payload.get("selected_ee_z", []), dtype=float)
        bridge_min = np.asarray(payload["bridge_action_min"], dtype=float)
        bridge_max = np.asarray(payload["bridge_action_max"], dtype=float)
        direct_min = np.asarray(payload.get("direct_action_min", [np.nan] * 7), dtype=float)
        direct_max = np.asarray(payload.get("direct_action_max", [np.nan] * 7), dtype=float)
        direct_pose_values = np.concatenate((direct_min[:6], direct_max[:6]))
        direct_pose_absmax = (
            float(np.nanmax(np.abs(direct_pose_values))) if np.isfinite(direct_pose_values).any() else None
        )
        rows.append(
            {
                "key": key,
                "row_selector": payload.get("row_selector"),
                "log_path": str(path),
                "dataset_steps": payload.get("dataset_steps"),
                "selected_rows": payload.get("selected_row_indices"),
                "selected_gripper_mean": float(selected_gripper.mean()) if selected_gripper.size else None,
                "selected_ee_z_mean": float(selected_ee_z.mean()) if selected_ee_z.size else None,
                "bridge_gripper_action_min": float(bridge_min[6]),
                "bridge_gripper_action_max": float(bridge_max[6]),
                "direct_first_gripper_action_min": (
                    float(direct_min[6]) if np.isfinite(direct_min[6]) else None
                ),
                "direct_first_gripper_action_max": (
                    float(direct_max[6]) if np.isfinite(direct_max[6]) else None
                ),
                "bridge_pose_absmax": float(np.max(np.abs(np.concatenate((bridge_min[:6], bridge_max[:6]))))),
                "direct_pose_absmax": direct_pose_absmax,
            }
        )

    labels = [row["key"].replace("full_pick_", "fp_").replace("_", "\n") for row in rows]
    x = np.arange(len(rows), dtype=float)
    bridge_min = np.asarray([row["bridge_gripper_action_min"] for row in rows], dtype=float)
    bridge_max = np.asarray([row["bridge_gripper_action_max"] for row in rows], dtype=float)
    direct_min = np.asarray(
        [np.nan if row["direct_first_gripper_action_min"] is None else row["direct_first_gripper_action_min"] for row in rows],
        dtype=float,
    )
    direct_max = np.asarray(
        [np.nan if row["direct_first_gripper_action_max"] is None else row["direct_first_gripper_action_max"] for row in rows],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(13, 5.2), constrained_layout=True)
    width = 0.34
    ax.bar(x - width / 2, bridge_max - bridge_min, bottom=bridge_min, width=width, label="PPO bridge action[6] range")
    ax.bar(x + width / 2, direct_max - direct_min, bottom=direct_min, width=width, label="official DP direct first action[6] range")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, fontsize=8)
    ax.set_ylabel("gripper action")
    ax.set_title("Bridge Smoke Gripper Behavior")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(out_dir / "bridge_gripper_action_ranges.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4.8), constrained_layout=True)
    ax.bar(x - width / 2, [row["bridge_pose_absmax"] for row in rows], width=width, label="PPO bridge pose abs max")
    ax.bar(
        x + width / 2,
        [np.nan if row["direct_pose_absmax"] is None else row["direct_pose_absmax"] for row in rows],
        width=width,
        label="official DP direct pose abs max",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, fontsize=8)
    ax.set_ylabel("max abs action over pose dims")
    ax.set_title("Bridge Smoke Pose Action Ranges")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.savefig(out_dir / "bridge_pose_action_ranges.png", dpi=180)
    plt.close(fig)

    return rows


def _eval_summaries(artifact_root: Path, out_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    timeseries_rows: list[dict[str, Any]] = []
    video_bundle_path: Path | None = None

    metrics_by_run: dict[str, dict[str, Any]] = {}
    for run in EVAL_RUNS:
        metrics_path = artifact_root / run.metrics_relpath
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        steps = payload["steps"]
        summary = payload["summary"]
        metrics_by_run[run.key] = payload
        action_min = summary.get("action_min") or [None] * 7
        action_max = summary.get("action_max") or [None] * 7
        summary_rows.append(
            {
                "key": run.key,
                "label": run.label,
                "job_id": run.job_id,
                "metrics_path": str(metrics_path),
                "checkpoint_note": run.checkpoint_note,
                "action_mode": run.action_mode,
                "action_chunk_steps": summary.get("action_chunk_steps"),
                "steps_completed": summary.get("steps_completed"),
                "reward_mean": _safe_float(summary.get("reward_mean")),
                "reward_final": _safe_float(summary.get("reward_final")),
                "success_final": _safe_float(summary.get("final_success_rate")),
                "success_window": _safe_float(summary.get("window_success_rate")),
                "cube_lift_height_max": _summary_value(summary, "cube_lift_height", "max"),
                "cube_lift_height_final": _summary_value(summary, "cube_lift_height", "final"),
                "ee_to_cube_dist_initial": _safe_float(steps[0].get("ee_to_cube_dist")) if steps else None,
                "ee_to_cube_dist_final": _summary_value(summary, "ee_to_cube_dist", "final"),
                "finger_center_to_cube_dist_initial": _safe_float(steps[0].get("finger_center_to_cube_dist")) if steps else None,
                "finger_center_to_cube_dist_final": _summary_value(summary, "finger_center_to_cube_dist", "final"),
                "gripper_width_min": _summary_value(summary, "gripper_width", "min"),
                "gripper_width_final": _safe_float(summary.get("final_gripper_width")),
                "gripper_action_min": _safe_float(action_min[6]),
                "gripper_action_max": _safe_float(action_max[6]),
                "video_enabled": summary.get("video_enabled"),
                "video_files": summary.get("video_files"),
            }
        )
        for step in steps:
            row = {"eval_key": run.key, "eval_label": run.label}
            row.update(step)
            timeseries_rows.append(row)

        if run.key == "full_pick_overfit2k_chunk8":
            video_files = summary.get("video_files") or []
            if video_files:
                # The fetched path mirrors the remote result directory.
                remote_video_name = Path(video_files[0]).name
                local_video = metrics_path.parent / "videos" / remote_video_name
                if local_video.is_file():
                    video_out = out_dir.parent / "videos" / local_video.name
                    video_out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_video, video_out)
                    video_bundle_path = video_out

    fig, axes = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True)
    axes_flat = axes.flatten()
    metric_specs = [
        ("reward_mean", "Reward Mean"),
        ("gripper_width", "Gripper Width (m)"),
        ("ee_to_cube_dist", "EE to Cube Distance (m)"),
        ("finger_center_to_cube_dist", "Finger Center to Cube Distance (m)"),
        ("cube_lift_height", "Cube Lift Height (m)"),
    ]
    for ax, (metric, title) in zip(axes_flat, metric_specs):
        for run in EVAL_RUNS:
            steps = metrics_by_run[run.key]["steps"]
            xs = np.asarray([s["step"] for s in steps if metric in s], dtype=float)
            ys = np.asarray([s[metric] for s in steps if metric in s], dtype=float)
            if xs.size:
                ax.plot(xs, ys, linewidth=1.6, label=run.label)
        ax.set_title(title)
        ax.set_xlabel("env step")
        ax.grid(True, alpha=0.25)
    ax = axes_flat[-1]
    x = np.arange(len(summary_rows), dtype=float)
    width = 0.35
    ax.bar(x - width / 2, [r["gripper_action_min"] for r in summary_rows], width=width, label="action[6] min")
    ax.bar(x + width / 2, [r["gripper_action_max"] for r in summary_rows], width=width, label="action[6] max")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([r["label"].replace(" ", "\n") for r in summary_rows], fontsize=7)
    ax.set_title("Gripper Action Range")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    for ax in axes_flat[:-1]:
        ax.legend(fontsize=7)
    fig.savefig(out_dir / "eval_behavior_metrics.png", dpi=180)
    plt.close(fig)

    return summary_rows, timeseries_rows, video_bundle_path


def _markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(name for name, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(key, "n/a")) for _, key in columns) + " |")
    return "\n".join([header, sep] + body)


def _build_report(
    out_dir: Path,
    train_rows: list[dict[str, Any]],
    bridge_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    video_path: Path | None,
) -> str:
    comparison_rows = []
    train_by_key = {row["key"]: row for row in train_rows}
    eval_by_key = {row["key"]: row for row in eval_rows}

    def row(
        name: str,
        train_key: str,
        eval_key: str,
        data: str,
        decision: str,
    ) -> dict[str, str]:
        tr = train_by_key[train_key]
        ev = eval_by_key[eval_key]
        return {
            "path": name,
            "data": data,
            "train": (
                f"step {_format_num(tr['final_global_step'], 0)}, "
                f"train {_format_num(tr['final_train_loss'])}, "
                f"val {_format_num(tr['final_val_loss'])}, "
                f"mse {_format_num(tr['final_train_action_mse_error'])}"
            ),
            "eval": (
                f"job {ev['job_id']}, {ev['action_mode']}, "
                f"{_format_num(ev['steps_completed'], 0)} steps"
            ),
            "behavior": (
                f"reward final {_format_num(ev['reward_final'])}; "
                f"success {_format_num(ev['success_final'])}; "
                f"lift max {_format_num(ev['cube_lift_height_max'])}; "
                f"gripper width final {_format_num(ev['gripper_width_final'])}; "
                f"EE dist final {_format_num(ev['ee_to_cube_dist_final'])}"
            ),
            "decision": decision,
        }

    comparison_rows.append(
        row(
            "Approach-only",
            "approach_only_overfit2k",
            "approach_only",
            "approach/pregrasp only",
            "Mechanics evidence only; cannot warm-start close/lift.",
        )
    )
    comparison_rows.append(
        row(
            "503-step full-pick first-action",
            "full_pick_5epoch_503step",
            "full_pick_503_first_action",
            "full pick/lift cuRobo demos",
            "Partial late close but no lift; undertrained and unstable.",
        )
    )
    comparison_rows.append(
        row(
            "503-step full-pick chunk8",
            "full_pick_5epoch_503step",
            "full_pick_503_chunk8",
            "full pick/lift cuRobo demos",
            "Chunk mechanics passed but behavior stayed mostly open.",
        )
    )
    comparison_rows.append(
        row(
            "Overfit2k full-pick chunk8",
            "full_pick_overfit2k",
            "full_pick_overfit2k_chunk8",
            "full pick/lift cuRobo demos",
            "Best checkpoint locally, but closed-loop eval drifts away and never closes/lifts.",
        )
    )

    bridge_focus = [
        row
        for row in bridge_rows
        if row["key"]
        in {
            "full_pick_overfit2k_first_open",
            "full_pick_overfit2k_closed",
            "full_pick_overfit2k_lift_high",
        }
    ]
    bridge_focus_rows = [
        {
            "selector": row["row_selector"],
            "selected_gripper": _format_num(row["selected_gripper_mean"]),
            "selected_ee_z": _format_num(row["selected_ee_z_mean"]),
            "bridge_gripper": (
                f"{_format_num(row['bridge_gripper_action_min'])} to "
                f"{_format_num(row['bridge_gripper_action_max'])}"
            ),
            "pose_absmax": _format_num(row["bridge_pose_absmax"]),
        }
        for row in bridge_focus
    ]

    overfit_eval = eval_by_key["full_pick_overfit2k_chunk8"]
    text = f"""# Franka Cube Diffusion Policy BC Warm-Start Artifacts

Generated: `{datetime.now().isoformat(timespec="seconds")}`

Agent: `{AGENT_ID}`

Official Diffusion Policy source: `{OFFICIAL_DP_REPO}` from the project page
`{OFFICIAL_DP_PAGE}`, commit `{OFFICIAL_DP_COMMIT}`. The reports here use
checkpoints trained with the official low-dimensional workspace and then queried
through the DEXTRAH PPO-observation bridge.

## Bundle Contents

- `plots/full_pick_train_val_loss_5epoch_vs_25epoch.png`
- `plots/full_pick_train_action_mse_5epoch_vs_25epoch.png`
- `plots/bridge_gripper_action_ranges.png`
- `plots/bridge_pose_action_ranges.png`
- `plots/eval_behavior_metrics.png`
- `tables/train_summary.csv` and `.json`
- `tables/bridge_smokes_summary.csv` and `.json`
- `tables/eval_summary.csv` and `.json`
- `tables/eval_timeseries.csv`
- `videos/{video_path.name if video_path else "n/a"}`

## Checkpoint And Eval Comparison

{_markdown_table(
    comparison_rows,
    [
        ("Path", "path"),
        ("Data", "data"),
        ("Train", "train"),
        ("Eval", "eval"),
        ("Behavior", "behavior"),
        ("Decision", "decision"),
    ],
)}

## Overfit2k Bridge Smokes

The overfit2k checkpoint is state-dependent on demonstration-manifold inputs:
open/pregrasp rows produce positive gripper actions, and closed/lift rows
produce negative gripper actions.

{_markdown_table(
    bridge_focus_rows,
    [
        ("Selector", "selector"),
        ("Selected Gripper Width", "selected_gripper"),
        ("Selected EE z", "selected_ee_z"),
        ("Bridge Gripper Action", "bridge_gripper"),
        ("Bridge Pose Abs Max", "pose_absmax"),
    ],
)}

## Overfit2k Chunk8 Failure Analysis

Job `1027727` ran the best current checkpoint for `360` Isaac steps with
`action_chunk_steps=8`, `num_inference_steps=100`, and video enabled. The run
completed mechanically, but task behavior failed:

- final success rate `{_format_num(overfit_eval["success_final"])}` and cube
  lift max `{_format_num(overfit_eval["cube_lift_height_max"])}`.
- gripper width stayed open: min `{_format_num(overfit_eval["gripper_width_min"])}`
  m, final `{_format_num(overfit_eval["gripper_width_final"])}` m.
- the arm moved away from the cube: EE-to-cube distance went from
  `{_format_num(overfit_eval["ee_to_cube_dist_initial"])}` m to
  `{_format_num(overfit_eval["ee_to_cube_dist_final"])}` m; finger-center
  distance went from `{_format_num(overfit_eval["finger_center_to_cube_dist_initial"])}` m
  to `{_format_num(overfit_eval["finger_center_to_cube_dist_final"])}` m.
- reward decayed from its early peak to final `{_format_num(overfit_eval["reward_final"])}`.
- gripper action range was `{_format_num(overfit_eval["gripper_action_min"])}`
  to `{_format_num(overfit_eval["gripper_action_max"])}`, so the live rollout
  never entered the closed/lift action regime that the checkpoint produces for
  selected closed/lift dataset rows.

This makes the likely failure mode closed-loop observation/history mismatch and
distribution drift rather than an official-DP checkpoint load failure. The local
bridge smokes prove the checkpoint can output close/lift commands when fed
dataset closed/lift observations. In Isaac rollout, the initial approach bias
and chunked stale actions increase EE/finger distance; once the state drifts
away from the cuRobo demonstration manifold, the policy remains in open-gripper
approach behavior and never reaches the learned close/lift phase.

## Next Debug Step

The next bounded loop should log or export the exact low-dimensional observation
history seen by `eval_franka_cube_dp_policy.py`, compare it to nearest phases in
the converted dataset, and add a short diagnostic eval that records per-policy
call action chunks before physics execution. That will separate bridge channel
mismatch from ordinary covariate shift. A useful training-side follow-up is to
add recovery/noise augmentation or a goal-conditioned phase signal before any
larger BC/RL run.
"""
    report_path = out_dir / "report.md"
    report_path.write_text(text, encoding="utf-8")
    return str(report_path)


def build_bundle(artifact_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    tables_dir = output_dir / "tables"
    videos_dir = output_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    train_rows = _plot_training(artifact_root, plots_dir)
    bridge_rows = _bridge_smoke_summaries(artifact_root, plots_dir)
    eval_rows, timeseries_rows, video_path = _eval_summaries(artifact_root, plots_dir)

    _write_csv(
        tables_dir / "train_summary.csv",
        train_rows,
        [
            "key",
            "label",
            "log_path",
            "dataset_note",
            "checkpoint_note",
            "rows",
            "final_global_step",
            "final_epoch",
            "final_train_loss",
            "final_val_loss",
            "final_train_action_mse_error",
        ],
    )
    _write_json(tables_dir / "train_summary.json", train_rows)

    _write_csv(
        tables_dir / "bridge_smokes_summary.csv",
        bridge_rows,
        [
            "key",
            "row_selector",
            "log_path",
            "dataset_steps",
            "selected_rows",
            "selected_gripper_mean",
            "selected_ee_z_mean",
            "bridge_gripper_action_min",
            "bridge_gripper_action_max",
            "direct_first_gripper_action_min",
            "direct_first_gripper_action_max",
            "bridge_pose_absmax",
            "direct_pose_absmax",
        ],
    )
    _write_json(tables_dir / "bridge_smokes_summary.json", bridge_rows)

    _write_csv(
        tables_dir / "eval_summary.csv",
        eval_rows,
        [
            "key",
            "label",
            "job_id",
            "metrics_path",
            "checkpoint_note",
            "action_mode",
            "action_chunk_steps",
            "steps_completed",
            "reward_mean",
            "reward_final",
            "success_final",
            "success_window",
            "cube_lift_height_max",
            "cube_lift_height_final",
            "ee_to_cube_dist_initial",
            "ee_to_cube_dist_final",
            "finger_center_to_cube_dist_initial",
            "finger_center_to_cube_dist_final",
            "gripper_width_min",
            "gripper_width_final",
            "gripper_action_min",
            "gripper_action_max",
            "video_enabled",
            "video_files",
        ],
    )
    _write_json(tables_dir / "eval_summary.json", eval_rows)

    ts_fields = [
        "eval_key",
        "eval_label",
        "step",
        "reward_mean",
        "gripper_width",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "cube_lift_height",
        "has_lifted_cube",
        "in_success_region",
        "finger_table_clearance",
    ]
    _write_csv(tables_dir / "eval_timeseries.csv", timeseries_rows, ts_fields)

    report_path = _build_report(output_dir, train_rows, bridge_rows, eval_rows, video_path)

    manifest = {
        "agent_id": AGENT_ID,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "artifact_root": str(artifact_root),
        "output_dir": str(output_dir),
        "official_diffusion_policy": {
            "repo": OFFICIAL_DP_REPO,
            "project_page": OFFICIAL_DP_PAGE,
            "commit": OFFICIAL_DP_COMMIT,
        },
        "report": report_path,
        "plots": sorted(str(p) for p in plots_dir.glob("*.png")),
        "tables": sorted(str(p) for p in tables_dir.glob("*")),
        "video": str(video_path) if video_path else None,
        "train_runs": train_rows,
        "bridge_smokes": bridge_rows,
        "eval_runs": eval_rows,
    }
    _write_json(tables_dir / "artifact_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts"),
        help="Root containing official_dp_debug, logs, and fetched cluster_evals.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Bundle output directory. Defaults to artifact-root/reports/dp_bc_warmstart_artifacts_<timestamp>.",
    )
    args = parser.parse_args()

    artifact_root = args.artifact_root.expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else artifact_root / "reports" / f"dp_bc_warmstart_artifacts_{timestamp}"
    )
    manifest = build_bundle(artifact_root, output_dir)
    print("FRANKA_CUBE_DP_BC_ARTIFACT_BUNDLE " + json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
