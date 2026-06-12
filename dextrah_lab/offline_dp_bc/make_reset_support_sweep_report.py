"""Summarize reset-support perturbation sweeps for Franka cube DP evals.

This offline artifact generator reads fetched ``eval_franka_cube_dp_policy.py``
run directories, compares reset perturbation settings, and writes an
inspectable CSV/JSON/PNG/Markdown bundle. It does not run Isaac or train.
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


OFFICIAL_DP_REPO = "https://github.com/real-stanford/diffusion_policy"
OFFICIAL_DP_COMMIT = "5ba07ac6661db573af695b419a7947ecb704690f"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_metrics(run_dir: Path) -> dict[str, Any]:
    metrics_path = run_dir / "metrics.json"
    payload = _load_json(metrics_path)
    return payload.get("summary", payload)


def _float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    value = _float(value)
    return None if not np.isfinite(value) else float(value)


def _metric(summary: dict[str, Any], name: str, stat: str) -> float | None:
    item = summary.get("step_metric_summary", {}).get(name, {})
    if not isinstance(item, dict):
        return None
    return _safe_float(item.get(stat))


def _read_support_rows(run_dir: Path, summary: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    support_csv = summary.get("support_trace_csv_path")
    if support_csv:
        candidates.append(Path(str(support_csv)))
    candidates.append(run_dir / "support_trace.csv")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _row_float(row: dict[str, Any], key: str) -> float:
    return _float(row.get(key))


def _support_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "support_distance_start": None,
            "support_distance_min": None,
            "support_distance_final": None,
            "nearest_phase_final": None,
            "first_negative_gripper_step": None,
            "first_hard_close_step": None,
        }
    distances = np.asarray([_row_float(row, "nearest_demo_distance") for row in rows], dtype=np.float64)
    finite = distances[np.isfinite(distances)]
    first_negative = next((row for row in rows if _row_float(row, "executed_gripper") < 0.0), None)
    first_hard = next((row for row in rows if _row_float(row, "executed_gripper") <= -0.9), None)
    return {
        "support_distance_start": _safe_float(rows[0].get("nearest_demo_distance")),
        "support_distance_min": float(np.min(finite)) if finite.size else None,
        "support_distance_final": _safe_float(rows[-1].get("nearest_demo_distance")),
        "nearest_phase_final": rows[-1].get("nearest_demo_phase"),
        "first_negative_gripper_step": int(float(first_negative["step"])) if first_negative is not None else None,
        "first_hard_close_step": int(float(first_hard["step"])) if first_hard is not None else None,
    }


def _failure_reason(row: dict[str, Any]) -> str:
    final_success = _float(row.get("final_success_rate"), 0.0)
    window_success = _float(row.get("window_success_rate"), 0.0)
    max_lift = _float(row.get("max_lift_m"), 0.0)
    final_lift = _float(row.get("final_lift_m"), 0.0)
    min_ee = _float(row.get("min_ee_to_cube_m"), float("inf"))
    min_finger = _float(row.get("min_finger_center_to_cube_m"), float("inf"))
    final_gripper = _float(row.get("final_gripper_width_m"), float("inf"))
    support_final = _float(row.get("support_distance_final"), 0.0)
    if final_success >= 0.5 and window_success >= 0.5:
        return "durable_success"
    if max_lift >= 0.12 and final_lift < 0.12:
        return "transient_success_or_drop"
    if min_ee > 0.08 and min_finger > 0.06:
        return "never_reaches_contact_geometry"
    if final_gripper > 0.035 and max_lift < 0.12:
        return "insufficient_gripper_closure_or_lift"
    if support_final > 5.0:
        return "outside_demo_support"
    return "no_success"


def _entry_setting(entry: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    demo_reset = summary.get("demo_reset") or {}
    return {
        "joint_blend_alpha": entry.get("joint_blend_alpha", demo_reset.get("joint_blend_alpha")),
        "cube_pos_blend_alpha": entry.get("cube_pos_blend_alpha", demo_reset.get("cube_pos_blend_alpha")),
        "setting": entry.get("setting", ""),
    }


def _summarize_run(entry: dict[str, Any]) -> dict[str, Any]:
    run_dir = Path(entry["run_dir"]).expanduser().resolve()
    summary = _load_metrics(run_dir)
    support_rows = _read_support_rows(run_dir, summary)
    support = _support_stats(support_rows)
    setting = _entry_setting(entry, summary)
    row: dict[str, Any] = {
        "label": entry.get("label", run_dir.name),
        "job_id": entry.get("job_id", ""),
        "run_dir": str(run_dir),
        "setting": setting["setting"],
        "joint_blend_alpha": _safe_float(setting["joint_blend_alpha"]),
        "cube_pos_blend_alpha": _safe_float(setting["cube_pos_blend_alpha"]),
        "steps_completed": int(summary.get("steps_completed", 0) or 0),
        "done_count": int(summary.get("done_count", 0) or 0),
        "final_success_rate": _safe_float(summary.get("final_success_rate")),
        "window_success_rate": _safe_float(summary.get("window_success_rate")),
        "max_lift_m": _metric(summary, "cube_lift_height", "max"),
        "max_lift_step": _metric(summary, "cube_lift_height", "max_step"),
        "final_lift_m": _metric(summary, "cube_lift_height", "final"),
        "min_ee_to_cube_m": _metric(summary, "ee_to_cube_dist", "min"),
        "final_ee_to_cube_m": _metric(summary, "ee_to_cube_dist", "final"),
        "min_finger_center_to_cube_m": _metric(summary, "finger_center_to_cube_dist", "min"),
        "final_finger_center_to_cube_m": _metric(summary, "finger_center_to_cube_dist", "final"),
        "final_gripper_width_m": summary.get("final_gripper_width"),
        "video_files": summary.get("video_files", []),
        "report_url": entry.get("report_url", ""),
        "video_url": entry.get("video_url", ""),
        "contact_sheet_url": entry.get("contact_sheet_url", ""),
        **support,
    }
    row["failure_reason"] = _failure_reason(row)
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5), constrained_layout=True)
    labels = [str(row["label"]) for row in rows]
    x = np.arange(len(rows))
    max_lift = [_float(row.get("max_lift_m"), 0.0) for row in rows]
    final_lift = [_float(row.get("final_lift_m"), 0.0) for row in rows]
    final_support = [_float(row.get("support_distance_final"), np.nan) for row in rows]
    support_min = [_float(row.get("support_distance_min"), np.nan) for row in rows]
    success = [_float(row.get("window_success_rate"), 0.0) for row in rows]
    final_ee = [_float(row.get("final_ee_to_cube_m"), np.nan) for row in rows]
    final_finger = [_float(row.get("final_finger_center_to_cube_m"), np.nan) for row in rows]

    axes[0, 0].bar(x - 0.18, max_lift, width=0.36, label="max lift")
    axes[0, 0].bar(x + 0.18, final_lift, width=0.36, label="final lift")
    axes[0, 0].axhline(0.12, color="tab:red", linestyle="--", linewidth=1.0, label="success lift threshold")
    axes[0, 0].set_ylabel("lift (m)")
    axes[0, 0].set_title("Lift By Reset Setting")
    axes[0, 0].set_xticks(x, labels, rotation=35, ha="right")
    axes[0, 0].grid(True, axis="y", alpha=0.25)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(x, final_support, marker="o", label="final support distance")
    axes[0, 1].plot(x, support_min, marker="o", label="min support distance")
    axes[0, 1].set_ylabel("scaled nearest-demo distance")
    axes[0, 1].set_title("Nearest-Demo Support")
    axes[0, 1].set_xticks(x, labels, rotation=35, ha="right")
    axes[0, 1].grid(True, alpha=0.25)
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].scatter(final_support, max_lift, c=success, cmap="viridis", s=80, edgecolor="black")
    for row, support, lift in zip(rows, final_support, max_lift):
        if np.isfinite(support) and np.isfinite(lift):
            axes[1, 0].annotate(str(row["label"]), (support, lift), fontsize=7, xytext=(4, 4), textcoords="offset points")
    axes[1, 0].axhline(0.12, color="tab:red", linestyle="--", linewidth=1.0)
    axes[1, 0].set_xlabel("final support distance")
    axes[1, 0].set_ylabel("max lift (m)")
    axes[1, 0].set_title("Support Distance vs Lift")
    axes[1, 0].grid(True, alpha=0.25)

    axes[1, 1].plot(x, final_ee, marker="o", label="final EE-cube")
    axes[1, 1].plot(x, final_finger, marker="o", label="final finger-cube")
    axes[1, 1].set_ylabel("distance (m)")
    axes[1, 1].set_title("Final Contact Geometry")
    axes[1, 1].set_xticks(x, labels, rotation=35, ha="right")
    axes[1, 1].grid(True, alpha=0.25)
    axes[1, 1].legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    try:
        return f"{float(value):.{digits}g}"
    except (TypeError, ValueError):
        return str(value)


def _write_report(path: Path, rows: list[dict[str, Any]], plot_name: str, manifest: dict[str, Any]) -> None:
    durable = [row for row in rows if row["failure_reason"] == "durable_success"]
    failures = [row for row in rows if row["failure_reason"] != "durable_success"]
    verdict = (
        "PASS only inside measured reset support; no broad normal-reset readiness."
        if durable and failures
        else "No durable success in this sweep."
        if not durable
        else "All measured settings durable; expand perturbation coverage before scale-up."
    )
    lines = [
        "# Franka Cube DP Reset Support Sweep",
        "",
        f"- Official Diffusion Policy source: `{OFFICIAL_DP_REPO}`",
        f"- Official Diffusion Policy commit: `{OFFICIAL_DP_COMMIT}`",
        f"- Sweep manifest: `{manifest.get('manifest_path', '')}`",
        f"- Verdict: **{verdict}**",
        "",
        "This is a bounded evaluation artifact only. It does not authorize DP BC, RL, or broad closed-loop scale-up.",
        "",
        f"![support sweep]({plot_name})",
        "",
        "## Summary Table",
        "",
        "| Label | Joint Blend | Cube Blend | Window Success | Max Lift | Final Lift | Final EE | Final Finger | Final Support | Final Phase | Reason |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {label} | {joint} | {cube} | {ws} | {max_lift} | {final_lift} | {ee} | {finger} | {support} | {phase} | {reason} |".format(
                label=row["label"],
                joint=_fmt(row.get("joint_blend_alpha")),
                cube=_fmt(row.get("cube_pos_blend_alpha")),
                ws=_fmt(row.get("window_success_rate")),
                max_lift=_fmt(row.get("max_lift_m")),
                final_lift=_fmt(row.get("final_lift_m")),
                ee=_fmt(row.get("final_ee_to_cube_m")),
                finger=_fmt(row.get("final_finger_center_to_cube_m")),
                support=_fmt(row.get("support_distance_final")),
                phase=row.get("nearest_phase_final") or "n/a",
                reason=row["failure_reason"],
            )
        )
    lines.extend(["", "## Artifact Links", ""])
    for row in rows:
        lines.append(f"### {row['label']}")
        lines.append(f"- job_id: `{row.get('job_id', '')}`")
        lines.append(f"- run_dir: `{row.get('run_dir', '')}`")
        if row.get("report_url"):
            lines.append(f"- per-run report: {row['report_url']}")
        if row.get("video_url"):
            lines.append(f"- video: {row['video_url']}")
        if row.get("contact_sheet_url"):
            lines.append(f"- contact sheet: {row['contact_sheet_url']}")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- Matched source-joint success combined with normal-reset failure points to reset/support coverage unless blended runs fail while staying close to demo support.",
            "- If failure appears at high joint-blend alpha with low support distance, inspect observation normalization and reset write semantics again.",
            "- Action chunking is not the primary hypothesis here because the same checkpoint already passes the matched source-joint no-reset hold gate with `ACTION_CHUNK_STEPS=1`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="JSON file containing a `runs` list.")
    parser.add_argument("--output_dir", required=True, help="Directory for report artifacts.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_json(manifest_path)
    if isinstance(manifest, list):
        manifest = {"runs": manifest}
    manifest["manifest_path"] = str(manifest_path)
    rows = [_summarize_run(entry) for entry in manifest.get("runs", [])]
    rows.sort(key=lambda row: (-1.0 if row.get("joint_blend_alpha") is None else -float(row["joint_blend_alpha"]), row["label"]))

    json_path = output_dir / "reset_support_sweep_summary.json"
    csv_path = output_dir / "reset_support_sweep_table.csv"
    plot_path = output_dir / "reset_support_sweep_plot.png"
    report_path = output_dir / "reset_support_sweep_report.md"

    json_path.write_text(json.dumps({"runs": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(csv_path, rows)
    _plot(rows, plot_path)
    _write_report(report_path, rows, plot_path.name, manifest)

    print(json.dumps({"summary_json": str(json_path), "table_csv": str(csv_path), "plot": str(plot_path), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
