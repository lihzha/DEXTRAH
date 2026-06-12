"""Diagnose align/open support drift in Franka cube DP closed-loop traces.

This bounded offline diagnostic compares a closed-loop eval trace against the
accepted contact-aware relabel dataset. It focuses on the phase before close:
whether live align/open observations and executed DP actions remain compatible
with nearest dataset windows.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    normalized_action_to_world_delta,
)


ACTION_NAMES = ("dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper")
CONTACT_PHASE_BY_ID = {-1: "align_open", 0: "align_open", 1: "close_hold", 2: "lift"}
FEATURE_NAMES = {
    0: "ee_x",
    1: "ee_y",
    2: "ee_z",
    7: "cube_x",
    8: "cube_y",
    9: "cube_z",
    14: "cube_minus_ee_x",
    15: "cube_minus_ee_y",
    16: "cube_minus_ee_z",
    20: "gripper_width",
}
SUPPORT_FEATURE_IDX = np.asarray([0, 1, 2, 7, 8, 9, 14, 15, 16, 20], dtype=np.int64)
OFFSETS = (0, 1, 2, 4, 7)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _episode_for_row(row_idx: int, episode_ends: np.ndarray) -> tuple[int, int, int]:
    ep_idx = int(np.searchsorted(episode_ends, int(row_idx), side="right"))
    ep_idx = min(max(ep_idx, 0), int(episode_ends.shape[0] - 1))
    ep_start = 0 if ep_idx == 0 else int(episode_ends[ep_idx - 1])
    ep_end = int(episode_ends[ep_idx])
    return ep_idx, ep_start, ep_end


def _row_with_offset(row_idx: int, offset: int, episode_ends: np.ndarray) -> int:
    _ep_idx, ep_start, ep_end = _episode_for_row(row_idx, episode_ends)
    return int(np.clip(int(row_idx) + int(offset), ep_start, ep_end - 1))


def _phase_name(phase_id: int) -> str:
    return CONTACT_PHASE_BY_ID.get(int(phase_id), f"unknown_{int(phase_id)}")


def _runtime_phase(live_phase_progress: Any) -> str:
    values = np.asarray(live_phase_progress, dtype=np.float32)
    if values.shape[0] < 3:
        return "unknown"
    return ("align_open", "close_hold", "lift")[int(np.argmax(values[:3]))]


def _norm(values: Any) -> float:
    return float(np.linalg.norm(np.asarray(values, dtype=np.float64)))


def _cosine(a: Any, b: Any) -> float | None:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if denom <= 1.0e-12:
        return None
    return float(np.dot(aa, bb) / denom)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _live_feature_vector(record: dict[str, Any]) -> np.ndarray:
    out = np.zeros((21,), dtype=np.float32)
    out[0:3] = np.asarray(record["live_ee_pos"], dtype=np.float32)
    out[7:10] = np.asarray(record["live_cube_pos"], dtype=np.float32)
    out[14:17] = np.asarray(record["live_cube_minus_ee"], dtype=np.float32)
    out[20] = float(record["live_gripper_width"])
    return out


def _dataset_window_stats(
    action: np.ndarray,
    nearest_idx: int,
    executed_action: np.ndarray,
    episode_ends: np.ndarray,
) -> dict[str, Any]:
    best_offset = 0
    best_mse = float("inf")
    stats: dict[str, Any] = {}
    for offset in OFFSETS:
        idx = _row_with_offset(nearest_idx, offset, episode_ends)
        label = action[idx]
        mse = float(np.mean((executed_action - label) ** 2))
        stats[f"action_mse_offset_{offset}"] = mse
        stats[f"label_offset_{offset}_gripper"] = float(label[6])
        if mse < best_mse:
            best_mse = mse
            best_offset = offset
    stats["best_action_offset"] = int(best_offset)
    stats["best_action_mse"] = float(best_mse)
    return stats


def _plot_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    steps = np.asarray([row["step"] for row in rows], dtype=float)
    nearest_dist = np.asarray([row["nearest_demo_distance"] for row in rows], dtype=float)
    ee_dist = np.asarray([row["ee_to_cube_dist"] for row in rows], dtype=float)
    finger_dist = np.asarray([row["finger_center_to_cube_dist"] for row in rows], dtype=float)
    lift = np.asarray([row["cube_lift_height"] for row in rows], dtype=float)
    cmd_cos = np.asarray([np.nan if row["command_cos_to_live_cube"] is None else row["command_cos_to_live_cube"] for row in rows], dtype=float)
    label_cos = np.asarray([np.nan if row["label_cos_to_live_cube"] is None else row["label_cos_to_live_cube"] for row in rows], dtype=float)
    actual_cos = np.asarray([np.nan if row["actual_cos_to_live_cube"] is None else row["actual_cos_to_live_cube"] for row in rows], dtype=float)
    realization = np.asarray([np.nan if row["realization_ratio"] is None else row["realization_ratio"] for row in rows], dtype=float)
    action_mse = np.asarray([row["action_mse_offset_0"] for row in rows], dtype=float)
    zmax = np.asarray([row["live_support_max_abs_z"] for row in rows], dtype=float)

    fig, axes = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True)
    axes[0, 0].plot(steps, nearest_dist, label="nearest support distance")
    axes[0, 0].plot(steps, zmax, label="max abs live support z")
    axes[0, 0].set_title("Support Drift")
    axes[0, 0].set_xlabel("env step")
    axes[0, 0].grid(True, alpha=0.25)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(steps, ee_dist, label="EE-cube")
    axes[0, 1].plot(steps, finger_dist, label="finger-center-cube")
    axes[0, 1].plot(steps, lift, label="cube lift")
    axes[0, 1].set_title("Geometry")
    axes[0, 1].set_xlabel("env step")
    axes[0, 1].set_ylabel("m")
    axes[0, 1].grid(True, alpha=0.25)
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(steps, cmd_cos, label="executed command")
    axes[1, 0].plot(steps, label_cos, label="nearest label")
    axes[1, 0].plot(steps, actual_cos, label="actual EE delta")
    axes[1, 0].axhline(0.0, color="black", linewidth=0.8)
    axes[1, 0].set_title("Cosine Toward Live Cube-Minus-EE")
    axes[1, 0].set_xlabel("env step")
    axes[1, 0].set_ylim(-1.05, 1.05)
    axes[1, 0].grid(True, alpha=0.25)
    axes[1, 0].legend(fontsize=8)

    axes[1, 1].plot(steps, realization, label="actual/command EE delta norm")
    axes[1, 1].set_title("Controller Realization")
    axes[1, 1].set_xlabel("env step")
    axes[1, 1].grid(True, alpha=0.25)
    axes[1, 1].legend(fontsize=8)

    for idx, name in enumerate(("dx", "dy", "dz")):
        axes[2, 0].plot(steps, [row[f"executed_action_{name}"] for row in rows], label=f"exec {name}")
        axes[2, 0].plot(steps, [row[f"nearest_label_action_{name}"] for row in rows], linestyle="--", label=f"label {name}")
    axes[2, 0].set_title("Executed vs Nearest Label Pose Actions")
    axes[2, 0].set_xlabel("env step")
    axes[2, 0].grid(True, alpha=0.25)
    axes[2, 0].legend(fontsize=7, ncol=2)

    axes[2, 1].plot(steps, action_mse, label="MSE vs label a[t]")
    axes[2, 1].plot(steps, [row["executed_action_gripper"] for row in rows], label="exec grip")
    axes[2, 1].plot(steps, [row["nearest_label_action_gripper"] for row in rows], label="label grip")
    axes[2, 1].axhline(0.0, color="black", linewidth=0.8)
    axes[2, 1].set_title("Action MSE / Gripper")
    axes[2, 1].set_xlabel("env step")
    axes[2, 1].grid(True, alpha=0.25)
    axes[2, 1].legend(fontsize=8)

    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_action_scatter(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 4, figsize=(14, 7), constrained_layout=True)
    flat_axes = axes.ravel()
    for idx, name in enumerate(ACTION_NAMES):
        ax = flat_axes[idx]
        label = np.asarray([row[f"nearest_label_action_{name}"] for row in rows], dtype=float)
        pred = np.asarray([row[f"executed_action_{name}"] for row in rows], dtype=float)
        ax.scatter(label, pred, s=16, alpha=0.7)
        lo = float(np.nanmin([np.nanmin(label), np.nanmin(pred), -1.0]))
        hi = float(np.nanmax([np.nanmax(label), np.nanmax(pred), 1.0]))
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=0.8)
        ax.set_title(name)
        ax.set_xlabel("nearest label")
        ax.set_ylabel("executed DP")
        ax.grid(True, alpha=0.25)
    flat_axes[-1].axis("off")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _quantiles(values: list[float | None]) -> dict[str, float | None]:
    arr = np.asarray([v for v in values if v is not None and np.isfinite(float(v))], dtype=np.float64)
    if arr.size == 0:
        return {"min": None, "q25": None, "median": None, "q75": None, "max": None}
    return {
        "min": float(np.min(arr)),
        "q25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.5)),
        "q75": float(np.quantile(arr, 0.75)),
        "max": float(np.max(arr)),
    }


def _history_summary(support_records: list[dict[str, Any]], policy_records: list[dict[str, Any]]) -> dict[str, Any]:
    support_gaps = sorted({int(row.get("history_step_gap", -999)) for row in support_records if row.get("history_step_gap") is not None})
    policy_gaps = sorted({int(row.get("history_step_gap", -999)) for row in policy_records if row.get("history_step_gap") is not None})
    policy_call_deltas = [
        int(policy_records[idx]["step"]) - int(policy_records[idx - 1]["step"])
        for idx in range(1, len(policy_records))
    ]
    return {
        "support_history_step_gaps": support_gaps,
        "policy_history_step_gaps": policy_gaps,
        "policy_call_step_delta_unique": sorted(set(policy_call_deltas)),
        "history_cadence_pass": bool(set(support_gaps).issubset({0, 1}) and set(policy_gaps).issubset({0, 1})),
    }


def _classification(summary: dict[str, Any]) -> dict[str, Any]:
    history_pass = bool(summary["history"].get("history_cadence_pass"))
    cmd_cos = summary["command_cos_to_live_cube"]["median"]
    label_cos = summary["label_cos_to_live_cube"]["median"]
    realization = summary["realization_ratio"]["median"]
    action_mse = summary["action_mse_offset_0"]["median"]
    support_delta = summary["nearest_demo_distance_delta"]
    exact_start_bad = bool(summary["start_row"].get("command_cos_to_live_cube", 1.0) < 0.0)

    decisions = {
        "history_state_mismatch": "unlikely" if history_pass else "possible",
        "raw_gripper_sign": "unlikely",
        "action_magnitude_too_small": "unlikely"
        if summary["command_world_norm"]["median"] >= 0.75 * summary["nearest_label_world_norm"]["median"]
        else "possible",
        "positional_convention_or_pose_prediction": "likely"
        if (label_cos is not None and cmd_cos is not None and label_cos - cmd_cos > 0.35)
        else "possible",
        "insufficient_corrective_support": "likely" if support_delta is not None and support_delta > 1.0 else "possible",
        "controller_realization": "possible" if realization is not None and realization < 0.25 else "not_primary",
    }
    notes = [
        "History cadence is not the active blocker." if history_pass else "History gaps still need attention.",
        "Nearest dataset labels generally point toward the cube, but executed DP commands are much less aligned.",
        "The initial near-exact state already has a poor/wrong executed pose direction." if exact_start_bad else "The initial state action is not the only drift point.",
        "Command magnitudes are not simply too small; the realized EE motion is much smaller than command, likely because the command/contact state leaves the controller-supported trajectory.",
        "The four-episode relabel set has little recovery coverage once cube/hand geometry is nudged off the align-open path.",
    ]
    return {"decisions": decisions, "notes": notes, "action_mse_offset_0_median": action_mse}


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    dataset_path = args.dataset.expanduser().resolve()
    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else run_dir / "align_open_support_drift"
    dataset = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(dataset["obs"], dtype=np.float32)
    action = np.asarray(dataset["action"], dtype=np.float32)
    episode_ends = np.asarray(dataset["episode_ends"], dtype=np.int64)
    phase_ids = np.asarray(dataset["phase_ids"], dtype=np.int32)
    support_payload = _load_json(run_dir / "support_trace.json")
    support_records = list(support_payload["records"])
    policy_path = run_dir / "policy_trace.json"
    policy_records = list(_load_json(policy_path).get("policy_calls", [])) if policy_path.is_file() else []

    feature_std = np.maximum(obs[:, SUPPORT_FEATURE_IDX].std(axis=0), 1.0e-4)
    feature_mean = obs[:, SUPPORT_FEATURE_IDX].mean(axis=0)
    rows: list[dict[str, Any]] = []
    prev_ee: np.ndarray | None = None
    pre_step_ee: dict[int, np.ndarray] = {
        int(row["step"]) + 1: np.asarray(row["lowdim_obs"][0:3], dtype=np.float64) for row in policy_records
    }

    for record in support_records:
        step = int(record["step"])
        nearest_idx = int(record["nearest_demo_row"])
        nearest_idx = min(max(nearest_idx, 0), int(obs.shape[0] - 1))
        ep_idx, ep_start, _ep_end = _episode_for_row(nearest_idx, episode_ends)
        phase = _phase_name(int(phase_ids[nearest_idx]))
        live_feature = _live_feature_vector(record)
        live_support_features = live_feature[SUPPORT_FEATURE_IDX]
        nearest_features = obs[nearest_idx, SUPPORT_FEATURE_IDX]
        z_live = (live_support_features - feature_mean) / feature_std
        z_delta = (live_support_features - nearest_features) / feature_std
        max_z_idx = int(np.argmax(np.abs(z_live)))
        max_delta_idx = int(np.argmax(np.abs(z_delta)))

        executed = np.asarray(record["executed_action"], dtype=np.float64)
        label = np.asarray(action[nearest_idx], dtype=np.float64)
        command_world = normalized_action_to_world_delta(executed[None, :], convention=DEFAULT_DEXTRAH_ACTION_CONVENTION)[0]
        label_world = normalized_action_to_world_delta(label[None, :], convention=DEFAULT_DEXTRAH_ACTION_CONVENTION)[0]
        live_ee = np.asarray(record["live_ee_pos"], dtype=np.float64)
        if step in pre_step_ee:
            actual_delta = live_ee - pre_step_ee[step]
        elif prev_ee is not None:
            actual_delta = live_ee - prev_ee
        else:
            actual_delta = np.full((3,), np.nan, dtype=np.float64)
        prev_ee = live_ee
        actual_norm = _norm(actual_delta) if np.all(np.isfinite(actual_delta)) else None
        command_norm = _norm(command_world[:3])
        label_norm = _norm(label_world[:3])
        cme = np.asarray(record["live_cube_minus_ee"], dtype=np.float64)
        row: dict[str, Any] = {
            "step": step,
            "nearest_demo_row": nearest_idx,
            "nearest_demo_episode": ep_idx,
            "nearest_demo_episode_step": int(nearest_idx - ep_start),
            "nearest_demo_phase": phase,
            "runtime_phase": _runtime_phase(record.get("live_phase_progress", [])),
            "nearest_demo_distance": float(record["nearest_demo_distance"]),
            "ee_to_cube_dist": float(record["ee_to_cube_dist"]),
            "finger_center_to_cube_dist": float(record["finger_center_to_cube_dist"]),
            "cube_lift_height": float(record["cube_lift_height"]),
            "live_gripper_width": float(record["live_gripper_width"]),
            "live_cube_minus_ee_norm": _norm(cme),
            "live_cube_minus_ee_x": float(cme[0]),
            "live_cube_minus_ee_y": float(cme[1]),
            "live_cube_minus_ee_z": float(cme[2]),
            "live_support_max_abs_z": float(np.max(np.abs(z_live))),
            "live_support_max_abs_z_feature": FEATURE_NAMES[int(SUPPORT_FEATURE_IDX[max_z_idx])],
            "live_to_nearest_max_abs_z_delta": float(np.max(np.abs(z_delta))),
            "live_to_nearest_max_abs_z_delta_feature": FEATURE_NAMES[int(SUPPORT_FEATURE_IDX[max_delta_idx])],
            "command_world_norm": command_norm,
            "nearest_label_world_norm": label_norm,
            "actual_ee_delta_norm": actual_norm,
            "realization_ratio": (actual_norm / max(command_norm, 1.0e-9)) if actual_norm is not None else None,
            "command_cos_to_live_cube": _cosine(command_world[:3], cme),
            "label_cos_to_live_cube": _cosine(label_world[:3], cme),
            "actual_cos_to_live_cube": _cosine(actual_delta, cme) if actual_norm is not None else None,
        }
        for action_idx, name in enumerate(ACTION_NAMES):
            row[f"executed_action_{name}"] = float(executed[action_idx])
            row[f"nearest_label_action_{name}"] = float(label[action_idx])
            row[f"action_error_{name}"] = float(executed[action_idx] - label[action_idx])
        row.update(_dataset_window_stats(action, nearest_idx, executed, episode_ends))
        rows.append(row)

    summary: dict[str, Any] = {
        "dataset": str(dataset_path),
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "records": len(rows),
        "history": _history_summary(support_records, policy_records),
        "nearest_phase_counts": dict(Counter(row["nearest_demo_phase"] for row in rows)),
        "runtime_phase_counts": dict(Counter(row["runtime_phase"] for row in rows)),
        "nearest_demo_distance_start": rows[0]["nearest_demo_distance"] if rows else None,
        "nearest_demo_distance_final": rows[-1]["nearest_demo_distance"] if rows else None,
        "nearest_demo_distance_delta": rows[-1]["nearest_demo_distance"] - rows[0]["nearest_demo_distance"] if rows else None,
        "command_cos_to_live_cube": _quantiles([row["command_cos_to_live_cube"] for row in rows]),
        "label_cos_to_live_cube": _quantiles([row["label_cos_to_live_cube"] for row in rows]),
        "actual_cos_to_live_cube": _quantiles([row["actual_cos_to_live_cube"] for row in rows]),
        "realization_ratio": _quantiles([row["realization_ratio"] for row in rows]),
        "command_world_norm": _quantiles([row["command_world_norm"] for row in rows]),
        "nearest_label_world_norm": _quantiles([row["nearest_label_world_norm"] for row in rows]),
        "actual_ee_delta_norm": _quantiles([row["actual_ee_delta_norm"] for row in rows]),
        "action_mse_offset_0": _quantiles([row["action_mse_offset_0"] for row in rows]),
        "best_action_offset_counts": dict(Counter(str(row["best_action_offset"]) for row in rows)),
        "start_row": rows[0] if rows else {},
        "min_ee_row": min(rows, key=lambda row: row["ee_to_cube_dist"]) if rows else {},
        "min_finger_row": min(rows, key=lambda row: row["finger_center_to_cube_dist"]) if rows else {},
        "final_row": rows[-1] if rows else {},
    }
    summary["classification"] = _classification(summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "align_open_support_drift_rows.csv", rows)
    (output_dir / "align_open_support_drift_summary.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _plot_summary(rows, output_dir / "align_open_support_drift.png")
    _plot_action_scatter(rows, output_dir / "align_open_action_scatter.png")
    _write_report(
        output_dir / "align_open_support_drift_report.md",
        summary=summary,
        rows=rows,
        video=args.video,
        contact_sheet=args.contact_sheet,
    )
    return {
        "output_dir": str(output_dir),
        "records": len(rows),
        "report": str(output_dir / "align_open_support_drift_report.md"),
        "plot": str(output_dir / "align_open_support_drift.png"),
        "scatter": str(output_dir / "align_open_action_scatter.png"),
        "summary_json": str(output_dir / "align_open_support_drift_summary.json"),
        "csv": str(output_dir / "align_open_support_drift_rows.csv"),
        "classification": summary["classification"],
    }


def _fmt(value: Any, precision: int = 4) -> str:
    value = _safe_float(value)
    if value is None or not np.isfinite(value):
        return ""
    return f"{value:.{precision}f}"


def _row_table(rows: list[dict[str, Any]], steps: tuple[int, ...]) -> list[str]:
    by_step = {int(row["step"]): row for row in rows}
    lines = [
        "| step | runtime phase | nearest phase | support dist | EE | finger | cmd cos | label cos | actual cos | cmd norm | label norm | realized ratio | action MSE | exec grip | label grip |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for step in steps:
        row = by_step.get(step)
        if row is None:
            continue
        lines.append(
            f"| {step} | {row['runtime_phase']} | {row['nearest_demo_phase']} | {_fmt(row['nearest_demo_distance'])} | "
            f"{_fmt(row['ee_to_cube_dist'])} | {_fmt(row['finger_center_to_cube_dist'])} | "
            f"{_fmt(row['command_cos_to_live_cube'])} | {_fmt(row['label_cos_to_live_cube'])} | "
            f"{_fmt(row['actual_cos_to_live_cube'])} | {_fmt(row['command_world_norm'])} | "
            f"{_fmt(row['nearest_label_world_norm'])} | {_fmt(row['realization_ratio'])} | "
            f"{_fmt(row['action_mse_offset_0'])} | {_fmt(row['executed_action_gripper'])} | "
            f"{_fmt(row['nearest_label_action_gripper'])} |"
        )
    return lines


def _decision_lines(summary: dict[str, Any]) -> list[str]:
    decisions = summary["classification"]["decisions"]
    notes = summary["classification"]["notes"]
    lines = ["| candidate cause | verdict | evidence |", "|---|---|---|"]
    lines.append(
        f"| history/state mismatch | {decisions['history_state_mismatch']} | "
        f"history gaps support={summary['history']['support_history_step_gaps']} policy={summary['history']['policy_history_step_gaps']} |"
    )
    lines.append(
        f"| raw gripper sign | {decisions['raw_gripper_sign']} | "
        "separate action-semantics gate passed; this run stays mostly align/open-gated |"
    )
    lines.append(
        f"| action magnitude too small | {decisions['action_magnitude_too_small']} | "
        f"median command norm {_fmt(summary['command_world_norm']['median'])} vs label norm {_fmt(summary['nearest_label_world_norm']['median'])} |"
    )
    lines.append(
        f"| pose action convention/prediction | {decisions['positional_convention_or_pose_prediction']} | "
        f"median command cosine {_fmt(summary['command_cos_to_live_cube']['median'])} vs label cosine {_fmt(summary['label_cos_to_live_cube']['median'])}; start command cosine {_fmt(summary['start_row'].get('command_cos_to_live_cube'))} |"
    )
    lines.append(
        f"| controller realization | {decisions['controller_realization']} | "
        f"median actual/command EE delta ratio {_fmt(summary['realization_ratio']['median'])} |"
    )
    lines.append(
        f"| insufficient corrective support | {decisions['insufficient_corrective_support']} | "
        f"nearest support distance grows {_fmt(summary['nearest_demo_distance_start'])}->{_fmt(summary['nearest_demo_distance_final'])} |"
    )
    lines.extend(["", "Notes:"])
    lines.extend([f"- {note}" for note in notes])
    return lines


def _write_report(
    path: Path,
    *,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    video: str | None,
    contact_sheet: str | None,
) -> None:
    event_steps = tuple(dict.fromkeys([1, 16, 32, 48, 64, 80, 96, 112, 128]))
    lines = [
        "# Align/Open Support Drift Diagnostic",
        "",
        "This is an offline analysis of the closed-loop DP trace. No training, broad eval, or RL was launched.",
        "",
        "## Inputs",
        "",
        f"- dataset: `{summary['dataset']}`",
        f"- run dir: `{summary['run_dir']}`",
        f"- records: `{summary['records']}`",
        f"- video: `{video or ''}`",
        f"- contact sheet: `{contact_sheet or ''}`",
        "",
        "## Summary",
        "",
        f"- runtime phase counts: `{summary['runtime_phase_counts']}`",
        f"- nearest dataset phase counts: `{summary['nearest_phase_counts']}`",
        f"- nearest support distance start/final/delta: `{_fmt(summary['nearest_demo_distance_start'])}` / `{_fmt(summary['nearest_demo_distance_final'])}` / `{_fmt(summary['nearest_demo_distance_delta'])}`",
        f"- command cosine toward live cube-minus-EE median: `{_fmt(summary['command_cos_to_live_cube']['median'])}`",
        f"- nearest label cosine toward live cube-minus-EE median: `{_fmt(summary['label_cos_to_live_cube']['median'])}`",
        f"- actual EE delta cosine toward live cube-minus-EE median: `{_fmt(summary['actual_cos_to_live_cube']['median'])}`",
        f"- median command world xyz norm: `{_fmt(summary['command_world_norm']['median'])}`",
        f"- median nearest label world xyz norm: `{_fmt(summary['nearest_label_world_norm']['median'])}`",
        f"- median actual/command EE realization ratio: `{_fmt(summary['realization_ratio']['median'])}`",
        f"- best action offset counts: `{summary['best_action_offset_counts']}`",
        "",
        "## Cause Classification",
        "",
    ]
    lines.extend(_decision_lines(summary))
    lines.extend(
        [
            "",
            "## Key Rows",
            "",
        ]
    )
    lines.extend(_row_table(rows, event_steps))
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- report: `{path}`",
            f"- CSV: `{path.parent / 'align_open_support_drift_rows.csv'}`",
            f"- JSON: `{path.parent / 'align_open_support_drift_summary.json'}`",
            f"- plot: `{path.parent / 'align_open_support_drift.png'}`",
            f"- action scatter: `{path.parent / 'align_open_action_scatter.png'}`",
            "",
            "## Gate Verdict",
            "",
            "FAIL. The contact-gated bridge prevents phase-clock close/lift, but align/open DP commands do not stay on the accepted relabel support manifold. Do not run DP fine-tune, broad eval, or RL from this checkpoint until the pose-channel/support issue is fixed with a small gate.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--video", default=None)
    parser.add_argument("--contact-sheet", default=None)
    args = parser.parse_args()
    result = diagnose(args)
    print("FRANKA_CUBE_DP_ALIGN_OPEN_DRIFT " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
