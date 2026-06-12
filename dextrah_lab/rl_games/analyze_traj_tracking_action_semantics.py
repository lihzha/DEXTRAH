"""Compare trajectory-tracking action semantics across eval rollouts.

This is a local artifact helper.  It consumes one or more eval ``metrics.json``
files from ``eval_rollout.py`` and writes a compact report/CSV/plot focused on
raw-policy, reference, and applied action timing.  The goal is to make grasp
phase close/up/gripper mismatches visible instead of relying on a single L2
error number.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


WINDOWS = (
    ("approach", 0.00, 0.45),
    ("close", 0.45, 0.55),
    ("lift", 0.55, 0.80),
    ("hold", 0.80, 1.01),
)

ACTION_PREFIXES = ("env_raw_policy_action", "env_reference_action", "env_applied_action")
ACTION_LABELS = ("raw", "reference", "applied")


def _load_run(spec: str) -> dict[str, object]:
    if "=" in spec:
        label, path_raw = spec.split("=", 1)
    else:
        path_raw = spec
        label = Path(path_raw).parent.name
    path = Path(path_raw).expanduser()
    payload = json.loads(path.read_text())
    steps = payload.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"{path} does not contain a non-empty steps list")
    summary = payload.get("summary", {})
    return {"label": label, "path": path, "steps": steps, "summary": summary if isinstance(summary, dict) else {}}


def _float(row: dict[str, object], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _phase(row: dict[str, object], idx: int, total: int) -> float:
    value = row.get("traj_phase_progress", row.get("cube_traj_tracking_phase_progress"))
    if isinstance(value, (int, float)):
        return float(value)
    return idx / max(total - 1, 1)


def _rows_for_window(steps: list[dict[str, object]], lo: float, hi: float) -> list[dict[str, object]]:
    rows = [row for idx, row in enumerate(steps) if lo <= _phase(row, idx, len(steps)) < hi]
    return rows if rows else steps


def _mean(rows: Iterable[dict[str, object]], key: str) -> float | None:
    values = [_float(row, key, default=float("nan")) for row in rows]
    values = [value for value in values if value == value]
    if not values:
        return None
    return sum(values) / len(values)


def _max(rows: Iterable[dict[str, object]], key: str) -> float | None:
    values = [_float(row, key, default=float("nan")) for row in rows]
    values = [value for value in values if value == value]
    return max(values) if values else None


def _min(rows: Iterable[dict[str, object]], key: str) -> float | None:
    values = [_float(row, key, default=float("nan")) for row in rows]
    values = [value for value in values if value == value]
    return min(values) if values else None


def _last(rows: list[dict[str, object]], key: str) -> float | None:
    if not rows:
        return None
    value = rows[-1].get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if abs(value) >= 1.0:
            return f"{value:.{digits}f}"
        return f"{value:.6f}"
    return str(value)


def _summary_metric(summary: dict[str, object], key: str, field: str = "final") -> float | int | None:
    metrics = summary.get("metric_summaries")
    if not isinstance(metrics, dict):
        return None
    record = metrics.get(key)
    if not isinstance(record, dict):
        return None
    value = record.get(field)
    if isinstance(value, (int, float)):
        return value
    return None


def _window_summary(run: dict[str, object], window: tuple[str, float, float]) -> dict[str, object]:
    label, lo, hi = window
    steps = run["steps"]
    assert isinstance(steps, list)
    rows = _rows_for_window(steps, lo, hi)
    out: dict[str, object] = {
        "run": run["label"],
        "window": label,
        "phase_lo": lo,
        "phase_hi": hi,
        "step_start": int(rows[0].get("step", 0)),
        "step_end": int(rows[-1].get("step", 0)),
        "num_steps": len(rows),
        "success_mean": _mean(rows, "success_rate"),
        "success_final": _last(rows, "success_rate"),
        "success_max": _max(rows, "success_rate"),
        "lift_mean": _mean(rows, "cube_lift_height"),
        "lift_final": _last(rows, "cube_lift_height"),
        "lift_max": _max(rows, "cube_lift_height"),
        "ee_cube_mean": _mean(rows, "ee_to_cube_dist"),
        "ee_cube_final": _last(rows, "ee_to_cube_dist"),
        "finger_cube_mean": _mean(rows, "finger_center_to_cube_dist"),
        "finger_cube_final": _last(rows, "finger_center_to_cube_dist"),
        "gripper_width_mean": _mean(rows, "gripper_width"),
        "gripper_width_final": _last(rows, "gripper_width"),
        "target_unsafe_max": _max(rows, "cube_traj_tracking_unsafe_target_rate"),
        "target_clearance_min": _min(rows, "cube_traj_tracking_target_table_clearance"),
        "teacher_alpha_mean": _mean(rows, "cube_traj_tracking_teacher_force_alpha"),
        "raw_ref_l2_mean": _mean(rows, "env_raw_policy_reference_action_error_l2_mean"),
        "applied_ref_l2_mean": _mean(rows, "env_applied_reference_action_error_l2_mean"),
        "raw_ref_close_abs_mean": _mean(rows, "env_raw_policy_reference_action_error_close_abs_mean"),
        "raw_ref_up_abs_mean": _mean(rows, "env_raw_policy_reference_action_error_up_abs_mean"),
        "raw_ref_gripper_abs_mean": _mean(rows, "env_raw_policy_reference_action_error_gripper_abs_mean"),
        "applied_ref_close_abs_mean": _mean(rows, "env_applied_reference_action_error_close_abs_mean"),
        "applied_ref_up_abs_mean": _mean(rows, "env_applied_reference_action_error_up_abs_mean"),
        "applied_ref_gripper_abs_mean": _mean(rows, "env_applied_reference_action_error_gripper_abs_mean"),
    }
    for prefix, action_label in zip(ACTION_PREFIXES, ACTION_LABELS):
        out[f"{action_label}_up_mean"] = _mean(rows, f"{prefix}_up_mean")
        out[f"{action_label}_up_final"] = _last(rows, f"{prefix}_up_mean")
        out[f"{action_label}_close_mean"] = _mean(rows, f"{prefix}_close_mean")
        out[f"{action_label}_close_final"] = _last(rows, f"{prefix}_close_mean")
        out[f"{action_label}_gripper_mean"] = _mean(rows, f"{prefix}_gripper_mean")
        out[f"{action_label}_gripper_final"] = _last(rows, f"{prefix}_gripper_mean")
        for dim in range(7):
            out[f"{action_label}_dim{dim}_mean"] = _mean(rows, f"{prefix}_dim{dim}_mean")
            out[f"{action_label}_dim{dim}_final"] = _last(rows, f"{prefix}_dim{dim}_mean")
    return out


def _build_rows(runs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_window_summary(run, window) for run in runs for window in WINDOWS]


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _series(steps: list[dict[str, object]], key: str) -> list[float]:
    return [_float(row, key) for row in steps]


def _draw_series_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    steps: list[dict[str, object]],
    specs: list[tuple[str, str, tuple[int, int, int], float]],
    font,
    font_small,
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, outline=(220, 220, 220), width=1)
    draw.text((x0, y0 - 24), title, fill=(25, 25, 25), font=font)
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y1 - frac * (y1 - y0)
        draw.line((x0, y, x1, y), fill=(240, 240, 240), width=1)
    legend_x = x0 + 8
    for label, key, color, scale in specs:
        values = _series(steps, key)
        if not values:
            continue
        points = []
        for idx, value in enumerate(values):
            scaled = max(0.0, min(1.0, value / max(scale, 1.0e-9)))
            x = x0 + idx * (x1 - x0) / max(len(values) - 1, 1)
            y = y1 - scaled * (y1 - y0)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=2)
        draw.rectangle((legend_x, y0 + 6, legend_x + 13, y0 + 18), fill=color)
        draw.text((legend_x + 18, y0 + 2), label, fill=(35, 35, 35), font=font_small)
        legend_x += max(105, 10 + 7 * len(label))


def _draw_plot(runs: list[dict[str, object]], path: Path) -> None:
    width = 1580
    row_h = 690
    height = 72 + row_h * len(runs)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 13)
    except Exception:
        font_title = font = font_small = None
    draw.text((42, 22), "Trajectory Tracking Action Semantics", fill=(20, 20, 20), font=font_title)

    for ridx, run in enumerate(runs):
        steps = run["steps"]
        assert isinstance(steps, list)
        y = 82 + ridx * row_h
        draw.text((42, y - 34), str(run["label"]), fill=(20, 20, 20), font=font_title)
        panels = [
            (
                "Close / Gripper",
                [
                    ("raw close", "env_raw_policy_action_close_mean", (200, 90, 40), 1.0),
                    ("ref close", "env_reference_action_close_mean", (45, 150, 85), 1.0),
                    ("applied close", "env_applied_action_close_mean", (40, 100, 190), 1.0),
                    ("grip width", "gripper_width", (90, 90, 90), 0.08),
                ],
            ),
            (
                "Up / Lift",
                [
                    ("raw up", "env_raw_policy_action_up_mean", (200, 90, 40), 1.0),
                    ("ref up", "env_reference_action_up_mean", (45, 150, 85), 1.0),
                    ("applied up", "env_applied_action_up_mean", (40, 100, 190), 1.0),
                    ("lift", "cube_lift_height", (100, 70, 160), 0.16),
                    ("success", "success_rate", (20, 20, 20), 1.0),
                ],
            ),
            (
                "Action Error / Distance",
                [
                    ("raw-ref L2", "env_raw_policy_reference_action_error_l2_mean", (190, 50, 70), 2.0),
                    ("applied-ref L2", "env_applied_reference_action_error_l2_mean", (45, 130, 65), 2.0),
                    ("EE-cube", "ee_to_cube_dist", (215, 125, 35), 0.45),
                    ("finger-cube", "finger_center_to_cube_dist", (120, 80, 175), 0.45),
                ],
            ),
            (
                "Reference Components",
                [
                    ("ref x", "env_reference_action_dim0_mean", (55, 115, 190), 1.0),
                    ("ref y", "env_reference_action_dim1_mean", (215, 125, 35), 1.0),
                    ("ref z/up", "env_reference_action_up_mean", (45, 150, 85), 1.0),
                    ("ref grip", "env_reference_action_gripper_mean", (130, 70, 170), 1.0),
                    ("alpha", "cube_traj_tracking_teacher_force_alpha", (20, 20, 20), 1.0),
                ],
            ),
        ]
        for pidx, (title, specs) in enumerate(panels):
            px0 = 42 + pidx % 2 * 760
            py0 = y + (pidx // 2) * 315
            _draw_series_panel(
                draw,
                (px0, py0, px0 + 705, py0 + 240),
                title,
                steps,
                specs,
                font,
                font_small,
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _write_report(runs: list[dict[str, object]], rows: list[dict[str, object]], output_dir: Path) -> Path:
    report = output_dir / "action_semantics_report.md"
    lines = [
        "# Trajectory Tracking Action Semantics",
        "",
        "This report compares raw policy, reference, and applied actions by phase window.  It is intended to diagnose close/up/gripper timing, not to replace video inspection.",
        "",
        "## Runs",
        "",
    ]
    for run in runs:
        summary = run["summary"]
        assert isinstance(summary, dict)
        lines.append(f"- `{run['label']}`: `{run['path']}`")
        lines.append(
            f"  - success final/max/ever: `{_fmt(_summary_metric(summary, 'success_rate', 'final'))}` / "
            f"`{_fmt(_summary_metric(summary, 'success_rate', 'max'))}` / "
            f"`{_fmt(_summary_metric(summary, 'eval_success_ever_count', 'final'))}`"
        )
        lines.append(
            f"  - lift max: `{_fmt(_summary_metric(summary, 'cube_lift_height', 'max'))}` m; "
            f"target unsafe max: `{_fmt(_summary_metric(summary, 'cube_traj_tracking_unsafe_target_rate', 'max'))}`; "
            f"teacher alpha final: `{_fmt(_summary_metric(summary, 'cube_traj_tracking_teacher_force_alpha', 'final'))}`"
        )
    lines.extend(
        [
            "",
            "## Window Summary",
            "",
            "| Run | Window | Steps | Success final/max | Lift max | Raw close/up/grip | Ref close/up/grip | Applied close/up/grip | Raw-ref close/up/grip abs | Raw-ref L2 | Applied-ref L2 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        raw = f"{_fmt(row.get('raw_close_mean'))}/{_fmt(row.get('raw_up_mean'))}/{_fmt(row.get('raw_gripper_mean'))}"
        ref = f"{_fmt(row.get('reference_close_mean'))}/{_fmt(row.get('reference_up_mean'))}/{_fmt(row.get('reference_gripper_mean'))}"
        applied = f"{_fmt(row.get('applied_close_mean'))}/{_fmt(row.get('applied_up_mean'))}/{_fmt(row.get('applied_gripper_mean'))}"
        abs_err = (
            f"{_fmt(row.get('raw_ref_close_abs_mean'))}/"
            f"{_fmt(row.get('raw_ref_up_abs_mean'))}/"
            f"{_fmt(row.get('raw_ref_gripper_abs_mean'))}"
        )
        lines.append(
            f"| {row['run']} | {row['window']} | {row['step_start']}-{row['step_end']} | "
            f"{_fmt(row.get('success_final'))}/{_fmt(row.get('success_max'))} | "
            f"{_fmt(row.get('lift_max'))} | {raw} | {ref} | {applied} | {abs_err} | "
            f"{_fmt(row.get('raw_ref_l2_mean'))} | {_fmt(row.get('applied_ref_l2_mean'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Aids",
            "",
            "- A low L2 is not enough if close/up/gripper timing is weak or signs differ during the close/lift windows.",
            "- For teacher-forced runs, `applied` is what the env receives; `raw` is still the learned policy output being audited.",
            "- Target/reference caveat remains: the compact reference is `curobo_validated=false` unless the source report says otherwise.",
            "",
            "## Files",
            "",
            f"- CSV: `{output_dir / 'action_semantics_windows.csv'}`",
            f"- Plot: `{output_dir / 'action_semantics_plot.png'}`",
        ]
    )
    report.write_text("\n".join(lines) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="Run spec as LABEL=/path/to/metrics.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    runs = [_load_run(spec) for spec in args.run]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = _build_rows(runs)
    csv_path = args.output_dir / "action_semantics_windows.csv"
    plot_path = args.output_dir / "action_semantics_plot.png"
    _write_csv(rows, csv_path)
    _draw_plot(runs, plot_path)
    report_path = _write_report(runs, rows, args.output_dir)
    summary = {
        "runs": [str(run["path"]) for run in runs],
        "report": str(report_path),
        "csv": str(csv_path),
        "plot": str(plot_path),
    }
    (args.output_dir / "action_semantics_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(report_path)
    print(plot_path)
    print(csv_path)


if __name__ == "__main__":
    main()
