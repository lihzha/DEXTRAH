"""Diagnose live-vs-demo Franka cube geometry for DP eval traces.

This script is a narrow follow-up to ``audit_eval_mismatch``. It compares a
saved no-learning eval trace against the converted demonstration dataset at the
policy-call boundaries, with emphasis on cube-relative grasp geometry, gripper
commands, and the observation-history cadence used by chunked evaluation.
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

from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


def _phase_names() -> list[str]:
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _episode_starts(episode_ends: np.ndarray) -> np.ndarray:
    return np.concatenate(([0], episode_ends[:-1])).astype(np.int64)


def _episode_local_index(global_idx: int, episode_ends: np.ndarray) -> tuple[int, int]:
    episode_idx = int(np.searchsorted(episode_ends, global_idx, side="right"))
    starts = _episode_starts(episode_ends)
    return episode_idx, int(global_idx - starts[episode_idx])


def _norm(values: np.ndarray | list[float]) -> float:
    return float(np.linalg.norm(np.asarray(values, dtype=np.float64)))


def _vec(values: np.ndarray | list[float]) -> list[float]:
    return np.asarray(values, dtype=np.float64).astype(float).tolist()


def _mean_std(rows: list[np.ndarray]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    arr = np.stack(rows, axis=0).astype(np.float64)
    return {
        "count": int(arr.shape[0]),
        "mean": _vec(arr.mean(axis=0)),
        "std": _vec(arr.std(axis=0)),
        "min": _vec(arr.min(axis=0)),
        "max": _vec(arr.max(axis=0)),
    }


def _phase_boundaries(phase_ids: np.ndarray, episode_ends: np.ndarray) -> dict[str, dict[str, float | int | None]]:
    names = _phase_names()
    starts = _episode_starts(episode_ends)
    out: dict[str, dict[str, float | int | None]] = {}
    for phase_id, phase_name in enumerate(names):
        firsts: list[int] = []
        counts: list[int] = []
        for start, end in zip(starts, episode_ends):
            ep = phase_ids[int(start) : int(end)]
            idx = np.flatnonzero(ep == phase_id)
            counts.append(int(idx.size))
            if idx.size:
                firsts.append(int(idx[0]))
        out[phase_name] = {
            "first_min": int(np.min(firsts)) if firsts else None,
            "first_mean": float(np.mean(firsts)) if firsts else None,
            "first_max": int(np.max(firsts)) if firsts else None,
            "count_mean": float(np.mean(counts)) if counts else 0.0,
        }
    return out


def _first_global_by_mask(mask: np.ndarray, start: int, end: int) -> int | None:
    idx = np.flatnonzero(mask[int(start) : int(end)])
    if idx.size == 0:
        return None
    return int(start + idx[0])


def _episode_reference_indices(
    action: np.ndarray,
    phase_ids: np.ndarray,
    episode_ends: np.ndarray,
) -> list[dict[str, int | None]]:
    names = _phase_names()
    phase_to_id = {name: idx for idx, name in enumerate(names)}
    starts = _episode_starts(episode_ends)
    refs: list[dict[str, int | None]] = []
    for start, end in zip(starts, episode_ends):
        ep_ref = {
            "episode_start": int(start),
            "first_pregrasp": _first_global_by_mask(phase_ids == phase_to_id["go_to_pre_grasp_pose"], start, end),
            "first_close_phase": _first_global_by_mask(phase_ids == phase_to_id["close_fingers"], start, end),
            "first_negative_gripper": _first_global_by_mask(action[:, 6] < 0.0, start, end),
            "first_hard_close": _first_global_by_mask(action[:, 6] <= -0.9, start, end),
            "first_lift_phase": _first_global_by_mask(phase_ids == phase_to_id["lift_object"], start, end),
        }
        refs.append(ep_ref)
    return refs


def _reference_stats(obs: np.ndarray, action: np.ndarray, refs: list[dict[str, int | None]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("episode_start", "first_pregrasp", "first_close_phase", "first_negative_gripper", "first_hard_close", "first_lift_phase"):
        indices = [int(row[key]) for row in refs if row[key] is not None]
        out[key] = {
            "global_indices": indices,
            "cube_minus_ee": _mean_std([obs[idx, 14:17] for idx in indices]),
            "gripper_width": _mean_std([obs[idx, 20:21] for idx in indices]),
            "action_gripper": _mean_std([action[idx, 6:7] for idx in indices]),
        }
    return out


def _trace_history_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    step_deltas = [
        int(records[idx]["step"]) - int(records[idx - 1]["step"])
        for idx in range(1, len(records))
    ]
    history_slot_gaps: list[int] = []
    for idx, record in enumerate(records):
        step_0, step_1 = _history_step_pair(records, idx)
        history_slot_gaps.append(int(step_1 - step_0))
    first_history = np.asarray(records[0]["history_after_push"], dtype=np.float32)
    first_obs = np.asarray(records[0]["lowdim_obs"], dtype=np.float32)
    first_duplicate_diff = float(np.max(np.abs(first_history - first_obs[None, :])))
    previous_call_history_diffs: list[float] = []
    current_history_diffs: list[float] = []
    for idx in range(1, len(records)):
        hist = np.asarray(records[idx]["history_after_push"], dtype=np.float32)
        prev_obs = np.asarray(records[idx - 1]["lowdim_obs"], dtype=np.float32)
        cur_obs = np.asarray(records[idx]["lowdim_obs"], dtype=np.float32)
        previous_call_history_diffs.append(float(np.max(np.abs(hist[-2] - prev_obs))))
        current_history_diffs.append(float(np.max(np.abs(hist[-1] - cur_obs))))
    return {
        "training_obs_history_step_delta": 1,
        "eval_policy_call_step_deltas": step_deltas,
        "eval_policy_call_step_delta_unique": sorted(set(step_deltas)),
        "eval_policy_call_step_delta_mean": float(np.mean(step_deltas)) if step_deltas else 0.0,
        "history_slot_step_gaps": history_slot_gaps,
        "history_slot_step_gap_unique": sorted(set(history_slot_gaps)),
        "history_slot_step_gap_mean": float(np.mean(history_slot_gaps)) if history_slot_gaps else 0.0,
        "history_cadence_mismatch": bool(history_slot_gaps and max(history_slot_gaps) > 1),
        "first_history_duplicates_reset_obs": bool(first_duplicate_diff < 1.0e-6),
        "first_history_duplicate_max_abs_diff": first_duplicate_diff,
        "history_prev_slot_matches_previous_policy_call_max_abs_diff": (
            float(np.max(previous_call_history_diffs)) if previous_call_history_diffs else 0.0
        ),
        "history_current_slot_matches_current_obs_max_abs_diff": (
            float(np.max(current_history_diffs)) if current_history_diffs else 0.0
        ),
    }


def _history_step_pair(records: list[dict[str, Any]], idx: int) -> tuple[int, int]:
    recorded_steps = records[idx].get("history_steps_after_push")
    if recorded_steps is not None:
        valid_steps = [int(step) for step in recorded_steps if int(step) >= 0]
        if len(valid_steps) >= 2:
            return valid_steps[-2], valid_steps[-1]
        if len(valid_steps) == 1:
            return valid_steps[0], valid_steps[0]
    current_step = int(records[idx]["step"])
    if idx == 0:
        return current_step, current_step
    return int(records[idx - 1]["step"]), current_step


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], summary: dict[str, Any], output_path: Path) -> None:
    steps = np.asarray([row["step"] for row in rows], dtype=float)
    fig, axes = plt.subplots(4, 1, figsize=(13, 13), sharex=True, constrained_layout=True)

    for axis_name, color in zip(("x", "y", "z"), ("tab:blue", "tab:orange", "tab:green")):
        axes[0].plot(steps, [row[f"live_cube_minus_ee_{axis_name}"] for row in rows], color=color, label=f"live {axis_name}")
        axes[0].plot(
            steps,
            [row[f"nearest_demo_cube_minus_ee_{axis_name}"] for row in rows],
            color=color,
            linestyle="--",
            alpha=0.75,
            label=f"nearest demo {axis_name}",
        )
    axes[0].set_title("Live vs Nearest-Demo Cube Minus EE")
    axes[0].set_ylabel("m")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(ncol=3, fontsize=8)

    axes[1].plot(steps, [row["live_to_nearest_demo_cube_minus_ee_norm"] for row in rows], label="to nearest demo")
    axes[1].plot(steps, [row["live_to_demo_first_close_mean_norm"] for row in rows], label="to demo first close mean")
    axes[1].plot(steps, [row["live_to_demo_first_hard_close_mean_norm"] for row in rows], label="to demo hard close mean")
    axes[1].set_title("Cube-Minus-EE Distance To Demo References")
    axes[1].set_ylabel("m")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)

    axes[2].plot(steps, [row["live_gripper_width"] for row in rows], label="live width")
    axes[2].plot(steps, [row["nearest_demo_gripper_width"] for row in rows], linestyle="--", label="nearest demo width")
    axes[2].set_title("Gripper Width")
    axes[2].set_ylabel("m")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=8)

    axes[3].plot(steps, [row["chunk_gripper_action_min"] for row in rows], label="chunk action min")
    axes[3].plot(steps, [row["chunk_gripper_action_max"] for row in rows], label="chunk action max")
    axes[3].plot(steps, [row["nearest_demo_action_gripper"] for row in rows], linestyle="--", label="nearest demo action")
    axes[3].axhline(0.0, color="black", linewidth=0.8)
    axes[3].set_title("Gripper Commands")
    axes[3].set_ylabel("normalized")
    axes[3].grid(True, alpha=0.25)
    axes[3].legend(fontsize=8)

    temporal = summary["temporal"]
    for label, value, color in (
        ("live first close", temporal.get("first_live_negative_gripper_step"), "tab:red"),
        ("live hard close", temporal.get("first_live_hard_close_step"), "tab:purple"),
        ("demo close mean", temporal.get("dataset_first_close_phase_mean_step"), "tab:red"),
        ("demo lift mean", temporal.get("dataset_first_lift_phase_mean_step"), "tab:brown"),
    ):
        if value is None:
            continue
        for ax in axes:
            ax.axvline(float(value), color=color, linestyle="--", alpha=0.25)
        axes[0].text(float(value), axes[0].get_ylim()[1], label, rotation=90, va="top", ha="right", fontsize=7)

    axes[-1].set_xlabel("env step")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _build_report(summary: dict[str, Any], plot_path: Path, csv_path: Path) -> str:
    history = summary["history"]
    temporal = summary["temporal"]
    close = summary["live_at_first_negative_gripper"]
    hard = summary["live_at_first_hard_close"]
    lines = [
        "# Franka Cube DP Live-vs-Demo Geometry Diagnostic",
        "",
        "## Main Finding",
        f"- History cadence mismatch: `{history['history_cadence_mismatch']}`. Training uses adjacent obs history step delta `1`; recorded history slot gaps are `{history['history_slot_step_gap_unique']}` env steps.",
        f"- Policy-call deltas are `{history['eval_policy_call_step_delta_unique']}` env steps; with chunked eval this may remain larger than `1`, but the history slots should be adjacent after the fix.",
        f"- First history duplicates reset obs: `{history['first_history_duplicates_reset_obs']}` with max abs diff `{history['first_history_duplicate_max_abs_diff']}`.",
        "- If `history_cadence_mismatch=True`, the chunked eval is conditioning the official DP policy on observations spaced by one action chunk, not the adjacent observations used by training.",
        "",
        "## Close Geometry",
        f"- Dataset first close phase mean step: `{temporal['dataset_first_close_phase_mean_step']}`.",
        f"- Dataset first hard-close mean step: `{temporal['dataset_first_hard_close_mean_step']}`.",
        f"- Live first negative gripper step: `{temporal['first_live_negative_gripper_step']}`.",
        f"- Live first hard-close step: `{temporal['first_live_hard_close_step']}`.",
    ]
    if close:
        lines.extend(
            [
                f"- At live first negative gripper, live cube-minus-EE is `{close['live_cube_minus_ee']}`.",
                f"- Distance to nearest demo cube-minus-EE: `{close['live_to_nearest_demo_cube_minus_ee_norm']:.4f} m`; to demo first-close mean: `{close['live_to_demo_first_close_mean_norm']:.4f} m`.",
            ]
        )
    if hard:
        lines.extend(
            [
                f"- At live hard close, live cube-minus-EE is `{hard['live_cube_minus_ee']}`.",
                f"- Distance to nearest demo cube-minus-EE: `{hard['live_to_nearest_demo_cube_minus_ee_norm']:.4f} m`; to demo hard-close mean: `{hard['live_to_demo_first_hard_close_mean_norm']:.4f} m`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Decision",
            "- Concrete mismatch found: update the eval wrapper so `LowdimObsHistory` is refreshed every env step even when action chunks are executed open-loop. Then relaunch a bounded no-video trace before any larger BC/RL work.",
            "",
            "## Artifacts",
            f"- Plot: `{plot_path}`",
            f"- CSV: `{csv_path}`",
            f"- Summary JSON: `{summary['output_dir']}/geometry_diagnosis_summary.json`",
            "",
        ]
    )
    return "\n".join(lines)


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.dataset.expanduser().resolve(), allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    trace = json.loads(args.trace.expanduser().read_text(encoding="utf-8"))
    trace_analysis = json.loads(args.trace_analysis.expanduser().read_text(encoding="utf-8"))
    records = trace["policy_calls"]
    analysis_rows = trace_analysis["rows"]
    if len(records) != len(analysis_rows):
        raise ValueError(f"Trace records ({len(records)}) and analysis rows ({len(analysis_rows)}) differ")

    refs = _episode_reference_indices(action, phase_ids, episode_ends)
    ref_stats = _reference_stats(obs, action, refs)
    close_mean = np.asarray(ref_stats["first_close_phase"]["cube_minus_ee"]["mean"], dtype=np.float64)
    hard_mean = np.asarray(ref_stats["first_hard_close"]["cube_minus_ee"]["mean"], dtype=np.float64)

    rows: list[dict[str, Any]] = []
    for record, analysis_row in zip(records, analysis_rows):
        record_idx = int(record["policy_call_index"])
        live_obs = np.asarray(record["lowdim_obs"], dtype=np.float32)
        nearest_idx = int(analysis_row["nearest_position_global_idx"])
        nearest_episode = int(analysis_row["nearest_position_episode"])
        nearest_ep_ref = refs[nearest_episode]
        nearest_close_idx = nearest_ep_ref["first_close_phase"]
        nearest_hard_idx = nearest_ep_ref["first_hard_close"]
        live_cme = live_obs[14:17].astype(np.float64)
        nearest_cme = obs[nearest_idx, 14:17].astype(np.float64)
        nearest_close_cme = obs[int(nearest_close_idx), 14:17].astype(np.float64) if nearest_close_idx is not None else np.full(3, np.nan)
        nearest_hard_cme = obs[int(nearest_hard_idx), 14:17].astype(np.float64) if nearest_hard_idx is not None else np.full(3, np.nan)
        history_step_0, history_step_1 = _history_step_pair(records, record_idx)
        row: dict[str, Any] = {
            "policy_call_index": record_idx,
            "step": int(record["step"]),
            "history_obs_step_0": history_step_0,
            "history_obs_step_1": history_step_1,
            "history_step_gap": int(history_step_1 - history_step_0),
            "nearest_position_phase": str(analysis_row["nearest_position_phase"]),
            "nearest_position_episode": nearest_episode,
            "nearest_position_episode_idx": int(analysis_row["nearest_position_episode_idx"]),
            "nearest_position_distance": float(analysis_row["nearest_position_distance"]),
            "nearest_position_global_idx": nearest_idx,
            "live_gripper_width": float(live_obs[20]),
            "nearest_demo_gripper_width": float(obs[nearest_idx, 20]),
            "nearest_demo_action_gripper": float(action[nearest_idx, 6]),
            "chunk_gripper_action_min": float(record["chunk_gripper_action_min"]),
            "chunk_gripper_action_max": float(record["chunk_gripper_action_max"]),
            "first_action_gripper": float(record["first_action"][6]),
            "live_cube_minus_ee": _vec(live_cme),
            "nearest_demo_cube_minus_ee": _vec(nearest_cme),
            "nearest_episode_first_close_cube_minus_ee": _vec(nearest_close_cme),
            "nearest_episode_first_hard_close_cube_minus_ee": _vec(nearest_hard_cme),
            "live_to_nearest_demo_cube_minus_ee_norm": _norm(live_cme - nearest_cme),
            "live_to_nearest_episode_first_close_cube_minus_ee_norm": _norm(live_cme - nearest_close_cme),
            "live_to_nearest_episode_first_hard_close_cube_minus_ee_norm": _norm(live_cme - nearest_hard_cme),
            "live_to_demo_first_close_mean_norm": _norm(live_cme - close_mean),
            "live_to_demo_first_hard_close_mean_norm": _norm(live_cme - hard_mean),
        }
        for axis, idx in zip(("x", "y", "z"), range(3)):
            row[f"live_cube_minus_ee_{axis}"] = float(live_cme[idx])
            row[f"nearest_demo_cube_minus_ee_{axis}"] = float(nearest_cme[idx])
            row[f"nearest_episode_first_close_cube_minus_ee_{axis}"] = float(nearest_close_cme[idx])
            row[f"nearest_episode_first_hard_close_cube_minus_ee_{axis}"] = float(nearest_hard_cme[idx])
            row[f"live_minus_nearest_demo_cube_minus_ee_{axis}"] = float(live_cme[idx] - nearest_cme[idx])
        rows.append(row)

    first_negative = next((row for row in rows if row["chunk_gripper_action_min"] < 0.0), None)
    first_hard = next((row for row in rows if row["chunk_gripper_action_min"] <= -0.9), None)
    phase_bounds = _phase_boundaries(phase_ids, episode_ends)
    hard_local_steps = []
    for ref in refs:
        if ref["first_hard_close"] is None:
            continue
        _, local_idx = _episode_local_index(int(ref["first_hard_close"]), episode_ends)
        hard_local_steps.append(local_idx)

    summary: dict[str, Any] = {
        "dataset": str(args.dataset),
        "trace": str(args.trace),
        "trace_analysis": str(args.trace_analysis),
        "output_dir": str(output_dir),
        "records": len(rows),
        "history": _trace_history_summary(records),
        "temporal": {
            "dataset_first_close_phase_mean_step": phase_bounds["close_fingers"]["first_mean"],
            "dataset_first_lift_phase_mean_step": phase_bounds["lift_object"]["first_mean"],
            "dataset_first_hard_close_mean_step": float(np.mean(hard_local_steps)) if hard_local_steps else None,
            "dataset_first_hard_close_min_step": int(np.min(hard_local_steps)) if hard_local_steps else None,
            "dataset_first_hard_close_max_step": int(np.max(hard_local_steps)) if hard_local_steps else None,
            "first_live_negative_gripper_step": int(first_negative["step"]) if first_negative else None,
            "first_live_hard_close_step": int(first_hard["step"]) if first_hard else None,
        },
        "reference_stats": ref_stats,
        "live_at_first_negative_gripper": first_negative,
        "live_at_first_hard_close": first_hard,
    }

    csv_path = output_dir / "live_vs_nearest_demo_geometry.csv"
    plot_path = output_dir / "live_vs_nearest_demo_geometry.png"
    _write_csv(csv_path, rows)
    _plot(rows, summary, plot_path)
    summary_path = output_dir / "geometry_diagnosis_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = _build_report(summary, plot_path, csv_path)
    (output_dir / "geometry_diagnosis_report.md").write_text(report, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--trace-analysis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = diagnose(args)
    print(
        "FRANKA_CUBE_DP_LIVE_DEMO_GEOMETRY "
        + json.dumps(
            {
                "output_dir": summary["output_dir"],
                "history": summary["history"],
                "temporal": summary["temporal"],
                "live_at_first_hard_close": summary["live_at_first_hard_close"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
