"""Build inspectable trajectory-tracking eval artifacts from metrics and trace files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_train_env(path: Path | None) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        result: dict[str, object] = {}
        for line in path.read_text().splitlines():
            if ":" not in line or line.startswith(" "):
                continue
            key, raw_value = line.split(":", 1)
            value = raw_value.strip()
            if value.lower() in {"true", "false"}:
                result[key.strip()] = value.lower() == "true"
            else:
                try:
                    result[key.strip()] = float(value) if "." in value else int(value)
                except ValueError:
                    result[key.strip()] = value
        return result


def _series(steps: list[dict[str, object]], key: str) -> list[float]:
    values: list[float] = []
    for item in steps:
        value = item.get(key, 0.0)
        values.append(float(value) if isinstance(value, (int, float)) else 0.0)
    return values


def _summary(summary: dict[str, object], key: str, field: str = "mean") -> float | None:
    metric_summaries = summary.get("metric_summaries", {})
    if not isinstance(metric_summaries, dict):
        return None
    record = metric_summaries.get(key, {})
    if not isinstance(record, dict):
        return None
    value = record.get(field)
    return float(value) if isinstance(value, (int, float)) else None


def _window_metric(
    summary: dict[str, object],
    window_name: str,
    key: str,
    field: str = "mean",
) -> float | None:
    windows = summary.get("fixed_window_summaries", {})
    if not isinstance(windows, dict):
        return None
    window = windows.get(window_name, {})
    if not isinstance(window, dict):
        return None
    metrics = window.get("metric_summaries", {})
    if not isinstance(metrics, dict):
        return None
    record = metrics.get(key, {})
    if not isinstance(record, dict):
        return None
    value = record.get(field)
    return float(value) if isinstance(value, (int, float)) else None


def _fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if abs(value) >= 1.0:
            return f"{value:.4f}"
        return f"{value:.{digits}f}"
    return str(value)


def _draw_plot(steps: list[dict[str, object]], output_path: Path) -> None:
    width, height = 1500, 1730
    margin_l, margin_r, margin_t = 96, 42, 76
    panel_h, panel_gap = 245, 86
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = font_b = font_s = None

    draw.text((margin_l, 26), "Trajectory Tracking Diagnostic Trace", fill=(20, 20, 20), font=font_b)
    panels = [
        (
            "Phase / Target Safety",
            [
                ("phase", "cube_traj_tracking_phase_progress", (40, 90, 190), 1.0),
                ("target clearance", "cube_traj_tracking_target_table_clearance", (45, 145, 95), 0.36),
                ("unsafe rate", "cube_traj_tracking_unsafe_target_rate", (210, 40, 40), 1.0),
            ],
        ),
        (
            "Distances",
            [
                ("EE-target", "ee_to_traj_target_dist", (30, 120, 200), 0.45),
                ("EE-cube", "ee_to_cube_dist", (225, 125, 35), 0.45),
                ("finger-cube", "finger_center_to_cube_dist", (120, 80, 175), 0.45),
            ],
        ),
        (
            "Gripper / Gates / Rewards",
            [
                ("gripper width", "gripper_width", (40, 110, 170), 0.08),
                ("contact gate", "cube_traj_tracking_contact_gate", (60, 150, 70), 1.0),
                ("close reward", "cube_traj_tracking_close_action_reward", (210, 110, 45), 0.35),
                ("lift reward", "cube_traj_tracking_lift_action_reward", (150, 75, 170), 0.35),
                ("align reward", "cube_traj_tracking_action_alignment_reward", (40, 150, 150), 0.75),
            ],
        ),
        (
            "Lift / Success / Actions",
            [
                ("lift height", "cube_lift_height", (55, 150, 75), 0.16),
                ("success", "success_rate", (20, 80, 190), 1.0),
                ("close action", "cube_traj_tracking_action_close", (215, 95, 45), 1.0),
                ("up action", "cube_traj_tracking_action_up", (140, 70, 170), 1.0),
            ],
        ),
        (
            "Policy / Reference / Mixed Actions",
            [
                ("raw up", "raw_policy_action_up_mean", (35, 95, 190), 1.0),
                ("ref up", "reference_delta_action_up_mean", (45, 150, 95), 1.0),
                ("mixed up", "mixed_action_up_mean", (140, 70, 170), 1.0),
                ("raw close", "raw_policy_action_close_mean", (205, 95, 45), 1.0),
                ("ref close", "reference_delta_action_close_mean", (215, 150, 55), 1.0),
                ("mixed close", "mixed_action_close_mean", (40, 150, 150), 1.0),
            ],
        ),
    ]

    x0, x1 = margin_l, width - margin_r
    for panel_idx, (title, specs) in enumerate(panels):
        y0 = margin_t + panel_idx * (panel_h + panel_gap)
        y1 = y0 + panel_h
        draw.rectangle((x0, y0, x1, y1), outline=(214, 214, 214), width=2)
        draw.text((x0, y0 - 30), title, fill=(25, 25, 25), font=font)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y1 - frac * (y1 - y0)
            draw.line((x0, y, x1, y), fill=(238, 238, 238), width=1)
            draw.text((22, y - 8), f"{frac:.2f}", fill=(100, 100, 100), font=font_s)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = x0 + frac * (x1 - x0)
            draw.line((x, y0, x, y1), fill=(244, 244, 244), width=1)
        legend_x = x0 + 8
        for name, key, color, scale in specs:
            values = _series(steps, key)
            points = []
            for idx, value in enumerate(values):
                scaled = max(0.0, min(1.0, value / max(scale, 1.0e-8)))
                x = x0 + idx * (x1 - x0) / max(len(values) - 1, 1)
                y = y1 - scaled * (y1 - y0)
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=3)
            draw.rectangle((legend_x, y0 + 8, legend_x + 17, y0 + 20), fill=color)
            draw.text((legend_x + 23, y0 + 4), name, fill=(40, 40, 40), font=font_s)
            legend_x += 180
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _consistency(train_env: dict[str, object], eval_env: dict[str, object]) -> dict[str, object]:
    keys = [
        "observation_space",
        "state_space",
        "action_space",
        "cube_spawn_xy_randomization",
        "trajectory_tracking_reference_path",
        "trajectory_tracking_reference_duration_s",
        "trajectory_tracking_phase_observations",
        "trajectory_tracking_close_action_weight",
        "trajectory_tracking_lift_action_weight",
        "trajectory_tracking_contact_gate_max_finger_dist",
        "trajectory_tracking_contact_gate_width",
        "trajectory_tracking_reference_reweight_phase_start",
        "trajectory_tracking_reference_late_weight_scale",
        "trajectory_tracking_min_target_gripper_width",
        "trajectory_tracking_action_alignment_weight",
        "trajectory_tracking_action_alignment_phase_start",
        "trajectory_tracking_action_alignment_sharpness",
        "trajectory_tracking_action_alignment_use_contact_gate",
    ]
    rows = {}
    mismatches = []
    for key in keys:
        train_value = train_env.get(key)
        eval_value = eval_env.get(key)
        match = train_value == eval_value
        rows[key] = {"train": train_value, "eval": eval_value, "match": match}
        if not match:
            mismatches.append(key)
    return {"checks": rows, "mismatches": mismatches, "passed": len(mismatches) == 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--train-env-yaml", type=Path, default=None)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.metrics.read_text())
    summary = payload["summary"]
    steps = payload["steps"]
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_path = output_dir / "trajectory_trace_plot.png"
    _draw_plot(steps, plot_path)

    train_env = _load_train_env(args.train_env_yaml)
    eval_env = summary.get("env_config", {}) if isinstance(summary.get("env_config"), dict) else {}
    consistency = _consistency(train_env, eval_env)
    (output_dir / "train_eval_consistency.json").write_text(json.dumps(consistency, indent=2, sort_keys=True) + "\n")

    compact = {
        "action_source": summary.get("action_source"),
        "action_source_notes": summary.get("action_source_notes"),
        "reference_mix_alpha": summary.get("reference_mix_alpha"),
        "checkpoint": summary.get("checkpoint"),
        "done_count": summary.get("done_count"),
        "num_steps_completed": summary.get("num_steps_completed"),
        "reward_mean": summary.get("reward_mean"),
        "reward_final": summary.get("reward_final"),
        "success_rate_mean": summary.get("success_rate_mean"),
        "success_rate_final": summary.get("success_rate_final"),
        "cube_lift_height_max": _summary(summary, "cube_lift_height", "max"),
        "ee_to_cube_final": _summary(summary, "ee_to_cube_dist", "final"),
        "finger_center_to_cube_final": _summary(summary, "finger_center_to_cube_dist", "final"),
        "gripper_width_final": _summary(summary, "gripper_width", "final"),
        "target_unsafe_rate_max": _summary(summary, "cube_traj_tracking_unsafe_target_rate", "max"),
        "target_clearance_min": _summary(summary, "cube_traj_tracking_target_table_clearance", "min"),
        "contact_gate_mean": _summary(summary, "cube_traj_tracking_contact_gate", "mean"),
        "close_action_reward_mean": _summary(summary, "cube_traj_tracking_close_action_reward", "mean"),
        "lift_action_reward_mean": _summary(summary, "cube_traj_tracking_lift_action_reward", "mean"),
        "close_action_utilization_mean": _summary(summary, "cube_traj_tracking_close_action_utilization", "mean"),
        "lift_action_utilization_mean": _summary(summary, "cube_traj_tracking_lift_action_utilization", "mean"),
        "action_alignment_reward_mean": _summary(summary, "cube_traj_tracking_action_alignment_reward", "mean"),
        "action_alignment_reward_final": _summary(summary, "cube_traj_tracking_action_alignment_reward", "final"),
        "action_alignment_utilization_mean": _summary(
            summary, "cube_traj_tracking_action_alignment_utilization", "mean"
        ),
        "action_alignment_error_mean": _summary(summary, "cube_traj_tracking_action_alignment_error", "mean"),
        "reference_action_close_mean": _summary(summary, "cube_traj_tracking_reference_action_close", "mean"),
        "reference_action_up_mean": _summary(summary, "cube_traj_tracking_reference_action_up", "mean"),
        "raw_policy_action_close_mean": _summary(summary, "raw_policy_action_close_mean", "mean"),
        "raw_policy_action_up_mean": _summary(summary, "raw_policy_action_up_mean", "mean"),
        "raw_policy_action_gripper_mean": _summary(summary, "raw_policy_action_gripper_mean", "mean"),
        "raw_policy_action_z_mean": _summary(summary, "raw_policy_action_z_mean", "mean"),
        "reference_delta_action_close_mean": _summary(summary, "reference_delta_action_close_mean", "mean"),
        "reference_delta_action_up_mean": _summary(summary, "reference_delta_action_up_mean", "mean"),
        "reference_delta_action_gripper_mean": _summary(summary, "reference_delta_action_gripper_mean", "mean"),
        "reference_delta_action_z_mean": _summary(summary, "reference_delta_action_z_mean", "mean"),
        "mixed_action_close_mean": _summary(summary, "mixed_action_close_mean", "mean"),
        "mixed_action_up_mean": _summary(summary, "mixed_action_up_mean", "mean"),
        "mixed_action_gripper_mean": _summary(summary, "mixed_action_gripper_mean", "mean"),
        "mixed_action_z_mean": _summary(summary, "mixed_action_z_mean", "mean"),
        "policy_reference_action_error_l2_mean": _summary(summary, "policy_reference_action_error_l2_mean", "mean"),
        "policy_reference_action_error_close_abs_mean": _summary(
            summary, "policy_reference_action_error_close_abs_mean", "mean"
        ),
        "policy_reference_action_error_up_abs_mean": _summary(
            summary, "policy_reference_action_error_up_abs_mean", "mean"
        ),
        "mixed_reference_action_error_l2_mean": _summary(summary, "mixed_reference_action_error_l2_mean", "mean"),
        "mixed_reference_action_error_close_abs_mean": _summary(
            summary, "mixed_reference_action_error_close_abs_mean", "mean"
        ),
        "mixed_reference_action_error_up_abs_mean": _summary(
            summary, "mixed_reference_action_error_up_abs_mean", "mean"
        ),
        "fixed_windows": {
            window_name: {
                "reward_mean": _window_metric(summary, window_name, "reward_mean", "mean"),
                "reward_final": _window_metric(summary, window_name, "reward_mean", "final"),
                "ee_to_target_mean": _window_metric(summary, window_name, "ee_to_traj_target_dist", "mean"),
                "ee_to_cube_mean": _window_metric(summary, window_name, "ee_to_cube_dist", "mean"),
                "finger_center_to_cube_mean": _window_metric(
                    summary, window_name, "finger_center_to_cube_dist", "mean"
                ),
                "gripper_width_mean": _window_metric(summary, window_name, "gripper_width", "mean"),
                "close_utilization_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_close_action_utilization", "mean"
                ),
                "lift_utilization_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_lift_action_utilization", "mean"
                ),
                "action_alignment_reward_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_action_alignment_reward", "mean"
                ),
                "action_alignment_utilization_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_action_alignment_utilization", "mean"
                ),
                "action_alignment_error_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_action_alignment_error", "mean"
                ),
                "raw_policy_close_mean": _window_metric(summary, window_name, "raw_policy_action_close_mean", "mean"),
                "raw_policy_up_mean": _window_metric(summary, window_name, "raw_policy_action_up_mean", "mean"),
                "reference_close_mean": _window_metric(
                    summary, window_name, "reference_delta_action_close_mean", "mean"
                ),
                "reference_up_mean": _window_metric(summary, window_name, "reference_delta_action_up_mean", "mean"),
                "mixed_close_mean": _window_metric(summary, window_name, "mixed_action_close_mean", "mean"),
                "mixed_up_mean": _window_metric(summary, window_name, "mixed_action_up_mean", "mean"),
                "policy_reference_error_l2_mean": _window_metric(
                    summary, window_name, "policy_reference_action_error_l2_mean", "mean"
                ),
                "mixed_reference_error_l2_mean": _window_metric(
                    summary, window_name, "mixed_reference_action_error_l2_mean", "mean"
                ),
                "unsafe_target_rate_max": _window_metric(
                    summary, window_name, "cube_traj_tracking_unsafe_target_rate", "max"
                ),
                "target_clearance_min": _window_metric(
                    summary, window_name, "cube_traj_tracking_target_table_clearance", "min"
                ),
                "lift_height_max": _window_metric(summary, window_name, "cube_lift_height", "max"),
                "success_rate_mean": _window_metric(summary, window_name, "success_rate", "mean"),
            }
            for window_name in ("first", "middle", "last")
        },
        "reference_curobo_validated": summary.get("trajectory_tracking_reference", {}).get("curobo_validated"),
        "reference_source_tag": summary.get("trajectory_tracking_reference", {}).get("source_tag"),
        "trace_csv_path": summary.get("trace_csv_path"),
        "trace_jsonl_path": summary.get("trace_jsonl_path"),
        "video_files": summary.get("video_files"),
    }
    (output_dir / "summary.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n")

    window_rows = []
    for window_name in ("first", "middle", "last"):
        window = compact["fixed_windows"][window_name]
        window_rows.append(
            "| "
            + " | ".join(
                [
                    window_name,
                    _fmt(window["reward_mean"], 4),
                    _fmt(window["ee_to_target_mean"], 4),
                    _fmt(window["ee_to_cube_mean"], 4),
                    _fmt(window["finger_center_to_cube_mean"], 4),
                    _fmt(window["gripper_width_mean"], 4),
                    _fmt(window["close_utilization_mean"], 4),
                    _fmt(window["lift_utilization_mean"], 4),
                    f"{_fmt(window['raw_policy_close_mean'], 4)}/{_fmt(window['raw_policy_up_mean'], 4)}",
                    f"{_fmt(window['reference_close_mean'], 4)}/{_fmt(window['reference_up_mean'], 4)}",
                    f"{_fmt(window['mixed_close_mean'], 4)}/{_fmt(window['mixed_up_mean'], 4)}",
                    _fmt(window["policy_reference_error_l2_mean"], 4),
                    _fmt(window["mixed_reference_error_l2_mean"], 4),
                    _fmt(window["action_alignment_reward_mean"], 4),
                    _fmt(window["action_alignment_error_mean"], 4),
                    _fmt(window["target_clearance_min"], 4),
                    _fmt(window["lift_height_max"], 4),
                    _fmt(window["success_rate_mean"], 4),
                ]
            )
            + " |"
        )
    window_table = "\n".join(
        [
            "| Window | Reward | EE-target | EE-cube | Finger-cube | Grip width | Close util | Lift util | Raw close/up | Ref close/up | Mixed close/up | Policy-ref L2 | Mixed-ref L2 | Align reward | Align err | Target clearance min | Lift max | Success |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *window_rows,
        ]
    )

    report = f"""# Trajectory Tracking Diagnostic Artifact

- action source: `{summary.get('action_source')}` ({summary.get('action_source_notes')})
- reference mix alpha: {_fmt(summary.get('reference_mix_alpha'))}
- checkpoint: `{summary.get('checkpoint')}`
- steps: {summary.get('num_steps_completed')}/{summary.get('num_steps_requested')}
- reward mean/final: {_fmt(summary.get('reward_mean'))} / {_fmt(summary.get('reward_final'))}
- success mean/final: {_fmt(summary.get('success_rate_mean'))} / {_fmt(summary.get('success_rate_final'))}
- done count: {summary.get('done_count')}
- target unsafe max: {_fmt(compact['target_unsafe_rate_max'])}
- target clearance min: {_fmt(compact['target_clearance_min'])} m
- train/eval consistency passed: {consistency['passed']} mismatches={consistency['mismatches']}
- reference caveat: curobo_validated={compact['reference_curobo_validated']}, source_tag={compact['reference_source_tag']}

## Behavior

- cube lift max: {_fmt(compact['cube_lift_height_max'])} m
- EE-to-cube final: {_fmt(compact['ee_to_cube_final'])} m
- finger-center-to-cube final: {_fmt(compact['finger_center_to_cube_final'])} m
- gripper width final: {_fmt(compact['gripper_width_final'])} m
- contact gate mean: {_fmt(compact['contact_gate_mean'])}
- close/lift action reward mean: {_fmt(compact['close_action_reward_mean'])} / {_fmt(compact['lift_action_reward_mean'])}
- close/lift utilization mean: {_fmt(compact['close_action_utilization_mean'])} / {_fmt(compact['lift_action_utilization_mean'])}
- action-alignment reward mean/final: {_fmt(compact['action_alignment_reward_mean'])} / {_fmt(compact['action_alignment_reward_final'])}
- action-alignment utilization/error mean: {_fmt(compact['action_alignment_utilization_mean'])} / {_fmt(compact['action_alignment_error_mean'])}
- reference close/up action mean: {_fmt(compact['reference_action_close_mean'])} / {_fmt(compact['reference_action_up_mean'])}
- raw policy close/up mean: {_fmt(compact['raw_policy_action_close_mean'])} / {_fmt(compact['raw_policy_action_up_mean'])}
- reference-delta close/up mean: {_fmt(compact['reference_delta_action_close_mean'])} / {_fmt(compact['reference_delta_action_up_mean'])}
- mixed close/up mean: {_fmt(compact['mixed_action_close_mean'])} / {_fmt(compact['mixed_action_up_mean'])}
- policy-reference L2/close/up error mean: {_fmt(compact['policy_reference_action_error_l2_mean'])} / {_fmt(compact['policy_reference_action_error_close_abs_mean'])} / {_fmt(compact['policy_reference_action_error_up_abs_mean'])}
- mixed-reference L2/close/up error mean: {_fmt(compact['mixed_reference_action_error_l2_mean'])} / {_fmt(compact['mixed_reference_action_error_close_abs_mean'])} / {_fmt(compact['mixed_reference_action_error_up_abs_mean'])}

## Fixed-Window Rollout Metrics

{window_table}

## Files

- plot: `{plot_path}`
- summary_json: `{output_dir / 'summary.json'}`
- consistency_json: `{output_dir / 'train_eval_consistency.json'}`
- trace_csv: `{summary.get('trace_csv_path')}`
- trace_jsonl: `{summary.get('trace_jsonl_path')}`
- videos: `{summary.get('video_files')}`
"""
    (output_dir / "report.md").write_text(report)
    print(output_dir)
    print(plot_path)
    print(output_dir / "report.md")


if __name__ == "__main__":
    main()
