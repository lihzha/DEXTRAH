"""Build inspectable closed-loop support-drift reports for Franka cube DP evals.

This is an offline artifact generator. It reads a fetched
``eval_franka_cube_dp_policy.py`` run directory containing metrics and support
traces, then writes a markdown report, machine-readable summary, key-row CSV,
and PNG plot. It does not launch Isaac, train, or evaluate a policy.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


OFFICIAL_DP_REPO = "https://github.com/real-stanford/diffusion_policy"
OFFICIAL_DP_COMMIT = "5ba07ac6661db573af695b419a7947ecb704690f"


def _fmt(value: Any, digits: int = 4) -> str:
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


def _float(row: dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _int(row: dict[str, Any], key: str, default: int = -1) -> int:
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def _parse_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(v) for v in value]
    if value is None or value == "":
        return []
    parsed = ast.literal_eval(str(value))
    return [float(v) for v in parsed]


def _read_support_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row["step"] = _int(row, "step")
            row["nearest_demo_episode"] = _int(row, "nearest_demo_episode")
            row["nearest_demo_episode_step"] = _int(row, "nearest_demo_episode_step")
            row["nearest_demo_distance"] = _float(row, "nearest_demo_distance")
            row["live_gripper_width"] = _float(row, "live_gripper_width")
            row["ee_to_cube_dist"] = _float(row, "ee_to_cube_dist")
            row["finger_center_to_cube_dist"] = _float(row, "finger_center_to_cube_dist")
            row["cube_lift_height"] = _float(row, "cube_lift_height")
            row["reward_mean"] = _float(row, "reward_mean")
            row["executed_gripper"] = _float(row, "executed_gripper")
            row["history_step_gap"] = _int(row, "history_step_gap")
            row["live_cube_minus_ee_vec"] = _parse_list(row.get("live_cube_minus_ee"))
            row["nearest_demo_cube_minus_ee_vec"] = _parse_list(row.get("nearest_demo_cube_minus_ee"))
            row["executed_action_vec"] = _parse_list(row.get("executed_action"))
            rows.append(row)
    return rows


def _load_metrics(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "summary" in payload:
        return payload["summary"]
    return payload


def _first_row(rows: list[dict[str, Any]], predicate) -> dict[str, Any] | None:
    for row in rows:
        if predicate(row):
            return row
    return None


def _min_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    finite = [row for row in rows if np.isfinite(_float(row, key))]
    if not finite:
        return None
    return min(finite, key=lambda row: _float(row, key))


def _last_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[-1] if rows else None


def _vec_columns(rows: list[dict[str, Any]], key: str, idx: int) -> list[float]:
    out = []
    for row in rows:
        vec = row.get(key) or []
        out.append(float(vec[idx]) if len(vec) > idx else float("nan"))
    return out


def _event_rows(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any] | None]] = [
        ("start", rows[0] if rows else None),
        ("first_negative_gripper", _first_row(rows, lambda row: _float(row, "executed_gripper") < 0.0)),
        ("first_hard_close", _first_row(rows, lambda row: _float(row, "executed_gripper") <= -0.9)),
        ("first_width_lt_1cm", _first_row(rows, lambda row: _float(row, "live_gripper_width") < 0.01)),
        ("min_ee_to_cube", _min_row(rows, "ee_to_cube_dist")),
        ("min_finger_center_to_cube", _min_row(rows, "finger_center_to_cube_dist")),
        ("final", _last_row(rows)),
    ]
    deduped: list[tuple[str, dict[str, Any]]] = []
    seen_steps: set[tuple[str, int]] = set()
    for name, row in events:
        if row is None:
            continue
        key = (name, _int(row, "step"))
        if key not in seen_steps:
            deduped.append((name, row))
            seen_steps.add(key)
    return deduped


def _row_summary(name: str, row: dict[str, Any]) -> dict[str, Any]:
    live = row.get("live_cube_minus_ee_vec") or []
    nearest = row.get("nearest_demo_cube_minus_ee_vec") or []
    return {
        "event": name,
        "step": _int(row, "step"),
        "nearest_phase": row.get("nearest_demo_phase", ""),
        "nearest_episode": _int(row, "nearest_demo_episode"),
        "nearest_episode_step": _int(row, "nearest_demo_episode_step"),
        "nearest_distance": _float(row, "nearest_demo_distance"),
        "live_cube_minus_ee_x": live[0] if len(live) > 0 else None,
        "live_cube_minus_ee_y": live[1] if len(live) > 1 else None,
        "live_cube_minus_ee_z": live[2] if len(live) > 2 else None,
        "nearest_cube_minus_ee_x": nearest[0] if len(nearest) > 0 else None,
        "nearest_cube_minus_ee_y": nearest[1] if len(nearest) > 1 else None,
        "nearest_cube_minus_ee_z": nearest[2] if len(nearest) > 2 else None,
        "ee_to_cube_dist": _float(row, "ee_to_cube_dist"),
        "finger_center_to_cube_dist": _float(row, "finger_center_to_cube_dist"),
        "gripper_width": _float(row, "live_gripper_width"),
        "executed_gripper": _float(row, "executed_gripper"),
        "cube_lift_height": _float(row, "cube_lift_height"),
        "history_step_gap": _int(row, "history_step_gap"),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], output_path: Path) -> None:
    steps = np.asarray([_int(row, "step") for row in rows], dtype=float)
    fig, axes = plt.subplots(4, 1, figsize=(13.5, 13.0), sharex=True, constrained_layout=True)

    axes[0].plot(steps, [_float(row, "nearest_demo_distance") for row in rows], label="nearest-demo distance")
    axes[0].set_ylabel("scaled distance")
    axes[0].set_title("Closed-Loop Support Drift")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    axes[1].plot(steps, [_float(row, "ee_to_cube_dist") for row in rows], label="EE to cube")
    axes[1].plot(steps, [_float(row, "finger_center_to_cube_dist") for row in rows], label="finger-center to cube")
    axes[1].plot(steps, [_float(row, "cube_lift_height") for row in rows], label="cube lift")
    axes[1].set_ylabel("m")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)

    axes[2].plot(steps, [_float(row, "live_gripper_width") for row in rows], label="live width")
    axes[2].plot(steps, [_float(row, "executed_gripper") for row in rows], label="executed gripper action")
    axes[2].axhline(0.0, color="black", linewidth=0.8)
    axes[2].axhline(-0.9, color="tab:red", linewidth=0.8, linestyle="--")
    axes[2].set_ylabel("m / action")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=8)

    for axis_name, color, idx in zip(("x", "y", "z"), ("tab:blue", "tab:orange", "tab:green"), range(3)):
        axes[3].plot(steps, _vec_columns(rows, "live_cube_minus_ee_vec", idx), color=color, label=f"live {axis_name}")
        axes[3].plot(
            steps,
            _vec_columns(rows, "nearest_demo_cube_minus_ee_vec", idx),
            color=color,
            linestyle="--",
            alpha=0.7,
            label=f"nearest {axis_name}",
        )
    axes[3].set_xlabel("env step")
    axes[3].set_ylabel("cube - EE (m)")
    axes[3].grid(True, alpha=0.25)
    axes[3].legend(ncol=3, fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_actions(rows: list[dict[str, Any]], output_path: Path) -> None:
    steps = np.asarray([_int(row, "step") for row in rows], dtype=float)
    action = np.full((len(rows), 7), np.nan, dtype=float)
    for idx, row in enumerate(rows):
        vec = row.get("executed_action_vec") or []
        if len(vec) >= 7:
            action[idx] = np.asarray(vec[:7], dtype=float)
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 8.0), sharex=True, constrained_layout=True)
    labels = ("dx", "dy", "dz", "droll", "dpitch", "dyaw")
    for idx, label in enumerate(labels):
        axes[0].plot(steps, action[:, idx], label=label)
    axes[0].set_title("Executed Pose Action Components")
    axes[0].set_ylabel("normalized action")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(ncol=3, fontsize=8)

    axes[1].plot(steps, action[:, 6], label="gripper action")
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].axhline(-0.9, color="tab:red", linewidth=0.8, linestyle="--")
    axes[1].axhline(0.9, color="tab:green", linewidth=0.8, linestyle="--")
    axes[1].set_title("Executed Gripper Action")
    axes[1].set_xlabel("env step")
    axes[1].set_ylabel("-1 close / +1 open")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _compact_summary(metrics: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    phase_counts = Counter(str(row.get("nearest_demo_phase", "")) for row in rows)
    events = [_row_summary(name, row) for name, row in _event_rows(rows)]
    first = rows[0] if rows else {}
    final = rows[-1] if rows else {}
    support_delta = _float(final, "nearest_demo_distance") - _float(first, "nearest_demo_distance")
    return {
        "steps": len(rows),
        "metrics": {
            "reward_mean": metrics.get("reward_mean"),
            "reward_final": metrics.get("reward_final"),
            "final_success_rate": metrics.get("final_success_rate"),
            "window_success_rate": metrics.get("window_success_rate"),
            "done_count": metrics.get("done_count"),
            "success_timeout_override": metrics.get("success_timeout_override"),
            "final_gripper_width": metrics.get("final_gripper_width"),
            "debug_policy_trace_records": metrics.get("debug_policy_trace_records"),
            "support_trace_records": metrics.get("support_trace_records"),
        },
        "distance_summary": {
            "ee_to_cube_min": _float(_min_row(rows, "ee_to_cube_dist") or {}, "ee_to_cube_dist"),
            "ee_to_cube_final": _float(final, "ee_to_cube_dist"),
            "finger_center_to_cube_min": _float(_min_row(rows, "finger_center_to_cube_dist") or {}, "finger_center_to_cube_dist"),
            "finger_center_to_cube_final": _float(final, "finger_center_to_cube_dist"),
            "cube_lift_max": max((_float(row, "cube_lift_height") for row in rows), default=None),
            "cube_lift_final": _float(final, "cube_lift_height"),
            "support_distance_start": _float(first, "nearest_demo_distance"),
            "support_distance_final": _float(final, "nearest_demo_distance"),
            "support_distance_delta": support_delta,
        },
        "phase_counts": dict(phase_counts),
        "history_gap_unique": sorted({_int(row, "history_step_gap") for row in rows}),
        "events": events,
    }


def _baseline_summary(run_dir: Path | None) -> dict[str, Any] | None:
    if run_dir is None:
        return None
    metrics_path = run_dir / "metrics.json"
    support_path = run_dir / "support_trace.csv"
    if not metrics_path.is_file() or not support_path.is_file():
        return None
    return _compact_summary(_load_metrics(metrics_path), _read_support_csv(support_path))


def _verdict_and_note(
    metrics: dict[str, Any],
    distances: dict[str, Any],
    demo_reset: dict[str, Any],
) -> tuple[str, str]:
    success_timeout_override = metrics.get("success_timeout_override")
    final_success = _float(metrics, "final_success_rate")
    window_success = _float(metrics, "window_success_rate")
    done_count = _float(metrics, "done_count")
    matched_noreset_pass = (
        final_success >= 1.0
        and window_success >= 1.0
        and done_count == 0.0
        and distances["cube_lift_final"] >= 0.12
        and success_timeout_override is not None
        and bool(demo_reset.get("source_joint_reset_available"))
    )
    failed_drift = (
        final_success < 0.5
        and window_success < 0.5
        and distances["cube_lift_final"] < 0.12
        and (
            distances["finger_center_to_cube_final"] > 0.06
            or distances["ee_to_cube_final"] > 0.08
            or distances["support_distance_final"] > 5.0
        )
    )
    if matched_noreset_pass:
        verdict = (
            "PASS (bounded): exact source-joint matched reset with success-timeout override "
            "retains and lifts the cube through the rollout horizon."
        )
        diagnostic_note = (
            "This is a no-learning diagnostic under exact source-joint matched reset with "
            "an eval-only success-timeout override. It clears the narrow hold-retention "
            "question for this setup, but it is not normal-reset generalization and is not "
            "BC/RL scale-up readiness evidence."
        )
    elif failed_drift:
        verdict = "FAIL: closed-loop policy still leaves demonstration support and closes away from the cube."
        diagnostic_note = (
            "This is a no-learning diagnostic. It must not be used as BC/RL scale-up evidence "
            "while the video shows the hand closing away from the cube."
        )
    else:
        verdict = "INCONCLUSIVE: inspect video and support trace before using this checkpoint."
        diagnostic_note = (
            "This is a no-learning diagnostic. Do not use it as BC/RL scale-up evidence until "
            "the visual behavior, reset condition, and support traces are explicitly validated."
        )
    return verdict, diagnostic_note


def _build_report(args: argparse.Namespace, summary: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    metrics = summary["metrics"]
    distances = summary["distance_summary"]
    demo_reset = summary.get("demo_reset") or {}
    verdict = str(summary.get("verdict", "INCONCLUSIVE: inspect video and support trace before using this checkpoint."))
    diagnostic_note = str(
        summary.get(
            "diagnostic_note",
            "This is a no-learning diagnostic. Do not use it as BC/RL scale-up evidence until "
            "the visual behavior, reset condition, and support traces are explicitly validated.",
        )
    )
    lines = [
        "# Franka Cube DP Closed-Loop Support Report",
        "",
        f"Run: `{args.run_name}`",
        f"Job: `{args.job_id}`",
        f"Implementation commit: `{args.commit}`",
        f"Official Diffusion Policy: `{OFFICIAL_DP_REPO}` @ `{args.official_dp_commit}`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        diagnostic_note,
        "",
        "## Key Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| steps | {_fmt(summary['steps'], 0)} |",
        f"| reward mean/final | {_fmt(metrics.get('reward_mean'))} / {_fmt(metrics.get('reward_final'))} |",
        f"| success/window success | {_fmt(metrics.get('final_success_rate'))} / {_fmt(metrics.get('window_success_rate'))} |",
        f"| done count | {_fmt(metrics.get('done_count'), 0)} |",
        f"| success timeout override | {metrics.get('success_timeout_override') or 'n/a'} |",
        f"| EE-to-cube min/final | {_fmt(distances['ee_to_cube_min'])} / {_fmt(distances['ee_to_cube_final'])} m |",
        f"| finger-center-to-cube min/final | {_fmt(distances['finger_center_to_cube_min'])} / {_fmt(distances['finger_center_to_cube_final'])} m |",
        f"| cube lift max/final | {_fmt(distances['cube_lift_max'])} / {_fmt(distances['cube_lift_final'])} m |",
        f"| final gripper width | {_fmt(metrics.get('final_gripper_width'))} m |",
        f"| nearest-demo distance start/final/delta | {_fmt(distances['support_distance_start'])} / {_fmt(distances['support_distance_final'])} / {_fmt(distances['support_distance_delta'])} |",
        f"| history gap unique | {summary['history_gap_unique']} |",
        "",
        "## Demo Reset",
        "",
    ]
    if demo_reset:
        lines.extend(
            [
                f"- episode/step/phase: `{demo_reset.get('episode')}` / `{demo_reset.get('episode_step')}` / `{demo_reset.get('phase')}`",
                f"- row: `{demo_reset.get('row')}`",
                f"- source joint reset available: `{demo_reset.get('source_joint_reset_available')}`",
                f"- source trajectory/frame: `{demo_reset.get('source_trajectory_json')}` / `{demo_reset.get('source_frame')}`",
                f"- joint write Linf diff: `{_fmt(demo_reset.get('joint_linf_diff_after_write_env0'))}`",
                f"- cube position L2 diff after reset: `{_fmt(demo_reset.get('cube_pos_l2_diff_env0'))}`",
                f"- cube-minus-EE L2 diff after reset: `{_fmt(demo_reset.get('cube_minus_ee_l2_diff_env0'))}`",
                f"- lowdim L2/Linf diff after reset: `{_fmt(demo_reset.get('lowdim_l2_diff_env0'))}` / `{_fmt(demo_reset.get('lowdim_linf_diff_env0'))}`",
            ]
        )
    else:
        lines.append("- No demo reset block found in metrics.")
    lines.extend(
        [
            "",
            "## Nearest-Demo Phases",
            "",
            "| phase | count |",
            "|---|---:|",
        ]
    )
    for phase, count in sorted(summary["phase_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {phase} | {count} |")
    lines.extend(
        [
            "",
            "## Event Rows",
            "",
            "| event | step | nearest phase | nearest ep/step | support dist | live cube-minus-EE | EE dist | finger dist | width | gripper action |",
            "|---|---:|---|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for event in summary["events"]:
        live_vec = [
            event.get("live_cube_minus_ee_x"),
            event.get("live_cube_minus_ee_y"),
            event.get("live_cube_minus_ee_z"),
        ]
        lines.append(
            "| {event} | {step} | {phase} | {ep}/{ep_step} | {dist} | {vec} | {ee} | {finger} | {width} | {grip} |".format(
                event=event["event"],
                step=event["step"],
                phase=event["nearest_phase"],
                ep=event["nearest_episode"],
                ep_step=event["nearest_episode_step"],
                dist=_fmt(event["nearest_distance"]),
                vec="[" + ", ".join(_fmt(v) for v in live_vec) + "]",
                ee=_fmt(event["ee_to_cube_dist"]),
                finger=_fmt(event["finger_center_to_cube_dist"]),
                width=_fmt(event["gripper_width"]),
                grip=_fmt(event["executed_gripper"]),
            )
        )
    if baseline is not None:
        bdist = baseline["distance_summary"]
        lines.extend(
            [
                "",
                "## Baseline Comparison",
                "",
                f"Baseline label: `{args.baseline_label}`",
                "",
                "| run | EE min/final | finger min/final | support start/final/delta | lift max | phases |",
                "|---|---:|---:|---:|---:|---|",
                (
                    f"| baseline | {_fmt(bdist['ee_to_cube_min'])}/{_fmt(bdist['ee_to_cube_final'])} | "
                    f"{_fmt(bdist['finger_center_to_cube_min'])}/{_fmt(bdist['finger_center_to_cube_final'])} | "
                    f"{_fmt(bdist['support_distance_start'])}/{_fmt(bdist['support_distance_final'])}/{_fmt(bdist['support_distance_delta'])} | "
                    f"{_fmt(bdist['cube_lift_max'])} | {baseline['phase_counts']} |"
                ),
                (
                    f"| current | {_fmt(distances['ee_to_cube_min'])}/{_fmt(distances['ee_to_cube_final'])} | "
                    f"{_fmt(distances['finger_center_to_cube_min'])}/{_fmt(distances['finger_center_to_cube_final'])} | "
                    f"{_fmt(distances['support_distance_start'])}/{_fmt(distances['support_distance_final'])}/{_fmt(distances['support_distance_delta'])} | "
                    f"{_fmt(distances['cube_lift_max'])} | {summary['phase_counts']} |"
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Run directory: `{args.run_dir}`",
            f"- Metrics: `{Path(args.run_dir) / 'metrics.json'}`",
            f"- Support trace CSV: `{Path(args.run_dir) / 'support_trace.csv'}`",
            f"- Policy trace: `{Path(args.run_dir) / 'policy_trace.json'}`",
            f"- Plot: `{summary['plot']}`",
            f"- Action plot: `{summary['action_plot']}`",
            f"- Key rows CSV: `{summary['key_rows_csv']}`",
            f"- Summary JSON: `{summary['summary_json']}`",
            f"- Eval config: `{Path(args.run_dir) / 'eval_config.json'}`",
            f"- Video: `{summary.get('video') or 'n/a'}`",
            f"- Contact sheet: `{summary.get('contact_sheet') or 'n/a'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = _load_metrics(run_dir / "metrics.json")
    rows = _read_support_csv(run_dir / "support_trace.csv")
    summary = _compact_summary(metrics, rows)
    summary.update(
        {
            "run_name": args.run_name,
            "job_id": args.job_id,
            "commit": args.commit,
            "official_dp_commit": args.official_dp_commit,
            "run_dir": str(run_dir),
            "demo_reset": metrics.get("demo_reset"),
            "video": str(next((run_dir / "videos").glob("*.mp4"), "")) if (run_dir / "videos").is_dir() else "",
        }
    )
    verdict, diagnostic_note = _verdict_and_note(
        summary["metrics"],
        summary["distance_summary"],
        summary.get("demo_reset") or {},
    )
    summary["verdict"] = verdict
    summary["diagnostic_note"] = diagnostic_note
    key_rows = [_row_summary(name, row) for name, row in _event_rows(rows)]
    key_rows_csv = out_dir / "closed_loop_support_key_rows.csv"
    plot_path = out_dir / "closed_loop_support_trace.png"
    action_plot_path = out_dir / "closed_loop_action_components.png"
    summary_json = out_dir / "closed_loop_support_summary.json"
    report_path = out_dir / "closed_loop_support_report.md"
    _write_csv(key_rows_csv, key_rows)
    _plot(rows, plot_path)
    _plot_actions(rows, action_plot_path)
    contact_sheet = out_dir / "closed_loop_contact_sheet.jpg"
    if args.contact_sheet:
        contact_sheet = Path(args.contact_sheet).expanduser().resolve()
    summary["key_rows_csv"] = str(key_rows_csv)
    summary["plot"] = str(plot_path)
    summary["action_plot"] = str(action_plot_path)
    summary["summary_json"] = str(summary_json)
    summary["report"] = str(report_path)
    summary["contact_sheet"] = str(contact_sheet if contact_sheet.exists() else "")
    baseline = _baseline_summary(Path(args.baseline_run_dir).expanduser().resolve() if args.baseline_run_dir else None)
    report = _build_report(args, summary, baseline)
    report_path.write_text(report, encoding="utf-8")
    summary["baseline"] = baseline
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--run_name", required=True)
    parser.add_argument("--job_id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--official_dp_commit", default=OFFICIAL_DP_COMMIT)
    parser.add_argument("--baseline_run_dir", default="")
    parser.add_argument("--baseline_label", default="baseline")
    parser.add_argument("--contact_sheet", default="")
    return parser.parse_args()


def main() -> None:
    summary = build_report(_parse_args())
    print(
        "FRANKA_CUBE_DP_CLOSED_LOOP_SUPPORT_REPORT "
        + json.dumps(
            {
                "report": summary["report"],
                "plot": summary["plot"],
                "action_plot": summary["action_plot"],
                "summary_json": summary["summary_json"],
                "key_rows_csv": summary["key_rows_csv"],
                "verdict": summary.get("verdict", "inspect"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
