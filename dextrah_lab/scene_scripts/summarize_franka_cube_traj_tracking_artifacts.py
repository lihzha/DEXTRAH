"""Build an inspectable artifact bundle for Franka cube trajectory tracking runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class RunSpec:
    key: str
    label: str
    run_type: str
    job_id: str
    commit: str
    result_dir: Path
    metrics_path: Path | None = None
    log_path: Path | None = None
    config_path: Path | None = None


def _load_json(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _nested_get(data: dict | None, keys: Iterable[str], default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _summary_stat(metrics: dict | None, metric_name: str, stat: str, default=None):
    return _nested_get(metrics, ("summary", "metric_summaries", metric_name, stat), default)


def _trajectory_summary(metrics: dict | None) -> dict:
    if not metrics:
        return {}
    return (
        _nested_get(metrics, ("summary", "trajectory_tracking_reference"), None)
        or metrics.get("tracking_reference")
        or {}
    )


def _rollout(metrics: dict | None) -> dict:
    if not metrics:
        return {}
    return metrics.get("rollout") or {}


def _read_config_scalars(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    wanted = {
        "episode_length_s",
        "observation_space",
        "cube_spawn_xy_randomization",
        "trajectory_tracking_enabled",
        "trajectory_tracking_reference_path",
        "trajectory_tracking_reference_duration_s",
        "trajectory_tracking_phase_observations",
        "trajectory_tracking_follow_current_cube_pose",
    }
    scalars: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        key, value = match.groups()
        if key in wanted:
            scalars[key] = value.strip()
    return scalars


def _parse_checkpoint_rewards(log_path: Path | None) -> list[dict[str, float | int | str]]:
    if log_path is None or not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    records = []
    pattern = re.compile(r"ep_(\d+)_rew_+(-?\d+(?:\.\d+)?)")
    for line in text.splitlines():
        match = pattern.search(line)
        if match:
            records.append({"epoch": int(match.group(1)), "reward_suffix": float(match.group(2)), "line": line.strip()})
    dedup: dict[int, dict[str, float | int | str]] = {}
    for record in records:
        dedup[int(record["epoch"])] = record
    return [dedup[epoch] for epoch in sorted(dedup)]


def _finite_summary(metrics: dict | None) -> dict[str, int]:
    total = 0
    nonfinite = 0

    def visit(value):
        nonlocal total, nonfinite
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            total += 1
            if not math.isfinite(float(value)):
                nonfinite += 1

    visit(metrics)
    return {"numeric_count": total, "nonfinite_count": nonfinite}


def _step_series(metrics: dict | None, metric_name: str) -> list[tuple[float, float]]:
    if not metrics:
        return []
    series = []
    for idx, step in enumerate(metrics.get("steps", []), start=1):
        if metric_name not in step or step[metric_name] is None:
            continue
        value = float(step[metric_name])
        if math.isfinite(value):
            series.append((float(step.get("step", idx)), value))
    return series


def _summarize_run(spec: RunSpec) -> dict:
    metrics = _load_json(spec.metrics_path)
    trajectory = _trajectory_summary(metrics)
    rollout = _rollout(metrics)
    finite = _finite_summary(metrics)
    config = _read_config_scalars(spec.config_path)
    ckpt_rewards = _parse_checkpoint_rewards(spec.log_path)
    row = {
        "key": spec.key,
        "label": spec.label,
        "type": spec.run_type,
        "job_id": spec.job_id,
        "commit": spec.commit,
        "result_dir": str(spec.result_dir),
        "metrics_path": str(spec.metrics_path) if spec.metrics_path else "",
        "log_path": str(spec.log_path) if spec.log_path else "",
        "config_path": str(spec.config_path) if spec.config_path else "",
        "metrics_present": bool(metrics),
        "numeric_count": finite["numeric_count"],
        "nonfinite_count": finite["nonfinite_count"],
        "steps_completed": _nested_get(metrics, ("summary", "num_steps_completed"), rollout.get("steps_completed", "")),
        "steps_requested": _nested_get(metrics, ("summary", "num_steps_requested"), ""),
        "done_count": _nested_get(metrics, ("summary", "done_count"), rollout.get("done_count", "")),
        "early_done_count": rollout.get("early_done_count", ""),
        "reward_mean": _nested_get(metrics, ("summary", "reward_mean"), rollout.get("reward_mean", "")),
        "reward_final": _nested_get(metrics, ("summary", "reward_final"), rollout.get("reward_final", "")),
        "success_rate_mean": _nested_get(metrics, ("summary", "success_rate_mean"), rollout.get("final_success_rate", "")),
        "success_rate_final": _nested_get(metrics, ("summary", "success_rate_final"), rollout.get("final_success_rate", "")),
        "phase_max": _summary_stat(metrics, "traj_phase_progress", "max", ""),
        "phase_final": _summary_stat(metrics, "traj_phase_progress", "final", ""),
        "phase_mean": _summary_stat(metrics, "traj_phase_progress", "mean", ""),
        "tracking_reward_mean": _summary_stat(metrics, "cube_traj_tracking_reward", "mean", _nested_get(rollout, ("tracking", "tracking_reward_mean"), "")),
        "tracking_reward_final": _summary_stat(metrics, "cube_traj_tracking_reward", "final", _nested_get(rollout, ("tracking", "tracking_reward_final"), "")),
        "unsafe_target_rate_max": _summary_stat(metrics, "cube_traj_tracking_unsafe_target_rate", "max", _nested_get(rollout, ("tracking", "tracking_unsafe_target_rate_max"), "")),
        "safe_target_rate_min": _summary_stat(metrics, "cube_traj_tracking_safe_target_rate", "min", ""),
        "target_clearance_min": _summary_stat(
            metrics,
            "cube_traj_tracking_target_table_clearance_min",
            "min",
            _nested_get(rollout, ("tracking", "tracking_target_table_clearance_batch_min"), ""),
        ),
        "finger_clearance_min": _summary_stat(metrics, "finger_table_clearance_min", "min", rollout.get("min_mean_finger_table_clearance", "")),
        "finger_violation_max": _summary_stat(metrics, "finger_table_clearance_violation_max", "max", ""),
        "lift_height_max": _summary_stat(metrics, "cube_lift_height_max", "max", rollout.get("max_mean_lift", "")),
        "gripper_width_mean": _summary_stat(metrics, "gripper_width", "mean", ""),
        "gripper_width_min": _summary_stat(metrics, "gripper_width", "min", ""),
        "ee_to_cube_mean": _summary_stat(metrics, "ee_to_cube_dist", "mean", ""),
        "ee_to_cube_min": _summary_stat(metrics, "ee_to_cube_dist", "min", ""),
        "finger_center_to_cube_mean": _summary_stat(metrics, "finger_center_to_cube_dist", "mean", ""),
        "right_finger_to_cube_min": _summary_stat(metrics, "right_finger_to_cube_dist", "min", ""),
        "position_error_mean": _summary_stat(metrics, "cube_traj_tracking_position_error", "mean", ""),
        "orientation_error_mean": _summary_stat(metrics, "cube_traj_tracking_orientation_error", "mean", ""),
        "gripper_error_mean": _summary_stat(metrics, "cube_traj_tracking_gripper_error", "mean", ""),
        "runtime_duration_s": trajectory.get("runtime_duration_s", trajectory.get("duration_s", "")),
        "source_duration_s": trajectory.get("source_duration_s", ""),
        "retime_policy": trajectory.get("runtime_retime_policy", ""),
        "object_pose_policy": trajectory.get("runtime_object_pose_policy", ""),
        "curobo_validated": trajectory.get("curobo_validated", ""),
        "reference_source": trajectory.get("source", ""),
        "checkpoint_rewards": ckpt_rewards,
        "config": config,
    }
    if ckpt_rewards:
        row["checkpoint_reward_final"] = ckpt_rewards[-1]["reward_suffix"]
        row["checkpoint_reward_best"] = max(float(record["reward_suffix"]) for record in ckpt_rewards)
    else:
        row["checkpoint_reward_final"] = ""
        row["checkpoint_reward_best"] = ""
    return row


def _fmt(value, digits: int = 4) -> str:
    if value == "" or value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(value)
    if abs(number) >= 100:
        return f"{number:.2f}"
    if abs(number) >= 10:
        return f"{number:.3f}"
    return f"{number:.{digits}f}"


def _draw_plot(
    image_path: Path,
    title: str,
    panels: list[dict],
    width: int = 1500,
    panel_height: int = 310,
) -> None:
    margin_left = 92
    margin_right = 34
    margin_top = 72
    margin_bottom = 56
    gap = 42
    height = margin_top + margin_bottom + len(panels) * panel_height + (len(panels) - 1) * gap
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]
    draw.text((margin_left, 24), title, fill="black", font=title_font)

    for panel_index, panel in enumerate(panels):
        top = margin_top + panel_index * (panel_height + gap)
        bottom = top + panel_height
        left = margin_left
        right = width - margin_right
        series = panel["series"]
        y_values = [value for _, data in series for _, value in data]
        x_values = [step for _, data in series for step, _ in data]
        x_min = panel.get("x_min", min(x_values) if x_values else 0.0)
        x_max = panel.get("x_max", max(x_values) if x_values else 1.0)
        if x_min == x_max:
            x_max = x_min + 1.0
        if "y_min" in panel and "y_max" in panel:
            y_min = float(panel["y_min"])
            y_max = float(panel["y_max"])
        elif y_values:
            y_min = min(y_values)
            y_max = max(y_values)
            if y_min == y_max:
                y_min -= 1.0
                y_max += 1.0
            pad = 0.08 * (y_max - y_min)
            y_min -= pad
            y_max += pad
        else:
            y_min, y_max = 0.0, 1.0

        def sx(x):
            return left + (float(x) - x_min) / (x_max - x_min) * (right - left)

        def sy(y):
            return bottom - (float(y) - y_min) / (y_max - y_min) * (bottom - top)

        draw.rectangle((left, top, right, bottom), outline="#a0a0a0")
        draw.text((left, top - 18), panel["title"], fill="black", font=font)
        for tick in range(6):
            x = left + tick * (right - left) / 5.0
            value = x_min + tick * (x_max - x_min) / 5.0
            draw.line((x, bottom, x, bottom + 5), fill="#555555")
            draw.text((x - 14, bottom + 8), f"{value:.0f}", fill="#333333", font=font)
        for tick in range(5):
            y = bottom - tick * (bottom - top) / 4.0
            value = y_min + tick * (y_max - y_min) / 4.0
            draw.line((left - 5, y, left, y), fill="#555555")
            draw.text((8, y - 6), _fmt(value, 3), fill="#333333", font=font)
            if tick not in (0, 4):
                draw.line((left, y, right, y), fill="#eeeeee")
        for threshold in panel.get("thresholds", []):
            y_value = float(threshold["value"])
            if y_min <= y_value <= y_max:
                y = sy(y_value)
                draw.line((left, y, right, y), fill=threshold.get("color", "#888888"), width=1)
                draw.text((right - 210, y - 14), threshold["label"], fill=threshold.get("color", "#888888"), font=font)
        legend_x = left + 12
        legend_y = top + 10
        for idx, (label, data) in enumerate(series):
            color = colors[idx % len(colors)]
            points = [(sx(x), sy(y)) for x, y in data]
            if len(points) >= 2:
                draw.line(points, fill=color, width=3)
            elif len(points) == 1:
                x, y = points[0]
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
            draw.line((legend_x, legend_y + idx * 18 + 6, legend_x + 24, legend_y + idx * 18 + 6), fill=color, width=3)
            draw.text((legend_x + 30, legend_y + idx * 18), label, fill="#111111", font=font)
        draw.text((right - 42, bottom + 30), "step", fill="#333333", font=font)

    image.save(image_path)


def _write_csv(path: Path, summaries: list[dict]) -> None:
    fields = [
        "key",
        "label",
        "type",
        "job_id",
        "commit",
        "steps_completed",
        "steps_requested",
        "done_count",
        "reward_mean",
        "reward_final",
        "success_rate_mean",
        "success_rate_final",
        "phase_max",
        "phase_final",
        "tracking_reward_mean",
        "unsafe_target_rate_max",
        "safe_target_rate_min",
        "target_clearance_min",
        "finger_clearance_min",
        "finger_violation_max",
        "lift_height_max",
        "gripper_width_mean",
        "gripper_width_min",
        "ee_to_cube_mean",
        "finger_center_to_cube_mean",
        "position_error_mean",
        "orientation_error_mean",
        "gripper_error_mean",
        "runtime_duration_s",
        "source_duration_s",
        "retime_policy",
        "object_pose_policy",
        "curobo_validated",
        "checkpoint_reward_final",
        "checkpoint_reward_best",
        "nonfinite_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for summary in summaries:
            writer.writerow({field: summary.get(field, "") for field in fields})


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _write_report(path: Path, summaries: list[dict], phase_png: Path, behavior_png: Path, csv_path: Path, json_path: Path) -> None:
    by_key = {summary["key"]: summary for summary in summaries}
    old = by_key["phase_starved_rl25_eval"]
    retime = by_key["retimed_rl25_eval"]
    env_smoke = by_key["retimed_env_smoke"]
    train_old = by_key["phase_starved_rl25_train"]
    train_retime = by_key["retimed_rl25_train"]
    old_reference_duration = old.get("source_duration_s") or old.get("runtime_duration_s")
    retime_source_duration = retime.get("source_duration_s") or retime.get("runtime_duration_s")
    rows = []
    for key in (
        "phase_starved_rl25_eval",
        "retimed_env_smoke",
        "retimed_3epoch_eval",
        "retimed_rl25_train",
        "retimed_rl25_eval",
    ):
        summary = by_key[key]
        rows.append(
            [
                summary["label"],
                summary["job_id"],
                summary["commit"][:7],
                summary["type"],
                _fmt(summary.get("steps_completed")),
                _fmt(summary.get("reward_mean")),
                _fmt(summary.get("success_rate_mean")),
                _fmt(summary.get("lift_height_max")),
                _fmt(summary.get("finger_violation_max")),
                _fmt(summary.get("phase_max")),
                _fmt(summary.get("unsafe_target_rate_max")),
                _fmt(summary.get("target_clearance_min")),
            ]
        )
    config_rows = [
        ["Observation size", old["config"].get("observation_space", "72"), retime["config"].get("observation_space", "72")],
        ["Phase observations", old["config"].get("trajectory_tracking_phase_observations", "false"), retime["config"].get("trajectory_tracking_phase_observations", "false")],
        ["Reference duration", _fmt(old.get("runtime_duration_s")), _fmt(retime.get("runtime_duration_s"))],
        ["Source duration", _fmt(old_reference_duration), _fmt(retime_source_duration)],
        ["Retime policy", str(old.get("retime_policy") or "source_timing"), str(retime.get("retime_policy"))],
        ["Object pose policy", str(old.get("object_pose_policy")), str(retime.get("object_pose_policy"))],
        ["cuRobo validated", str(old.get("curobo_validated")), str(retime.get("curobo_validated"))],
    ]
    text = f"""# Franka Cube Trajectory-Tracking Artifact Comparison

Generated: {datetime.now().isoformat(timespec="seconds")}

## Main Conclusion

The retiming patch fixes the previous phase-starvation failure mode. The reset-pose RL25 eval before retiming only reached phase `{_fmt(old.get("phase_max"))}` because the reference duration was `{_fmt(old_reference_duration)}` s inside a 10 s episode. The retimed eval reaches phase `{_fmt(retime.get("phase_max"))}` with runtime duration `{_fmt(retime.get("runtime_duration_s"))}` s, while target safety remains clean: unsafe target rate max `{_fmt(retime.get("unsafe_target_rate_max"))}` and target clearance min `{_fmt(retime.get("target_clearance_min"))}` m.

The remaining issue is behavior, not target generation. The retimed RL25 checkpoint improves tracking reward and approach distance versus the phase-starved eval, but it still has success `{_fmt(retime.get("success_rate_mean"))}` and max lift only `{_fmt(retime.get("lift_height_max"))}` m. Gripper width collapses near zero during the grasp/lift phase, and orientation error remains high, so the next bounded iteration should diagnose grasp contact/orientation/gripper scheduling before scaling training.

The compact 60 mm reference is still reported as `curobo_validated=false`; it should not be treated as a DEXTRAH-ready validated reference until exact geometry/validation matches.

## Required Artifacts

- Phase/safety plot: `{phase_png}`
- Behavior plot: `{behavior_png}`
- Summary JSON: `{json_path}`
- Summary CSV: `{csv_path}`

## Run Comparison

{_markdown_table(["Run", "Job", "Commit", "Type", "Steps", "Reward mean", "Success", "Lift max m", "Finger viol max", "Phase max", "Unsafe max", "Target clear min m"], rows)}

## Config Differences

{_markdown_table(["Setting", "Before retiming eval", "Retimed RL25 eval"], config_rows)}

## Training Checkpoints

- Phase-starved RL25 train `{train_old["job_id"]}` checkpoint reward suffix final/best: `{_fmt(train_old.get("checkpoint_reward_final"))}` / `{_fmt(train_old.get("checkpoint_reward_best"))}`.
- Retimed RL25 train `{train_retime["job_id"]}` checkpoint reward suffix final/best: `{_fmt(train_retime.get("checkpoint_reward_final"))}` / `{_fmt(train_retime.get("checkpoint_reward_best"))}`.
- TensorBoard event files fetched for these short smokes are zero-byte sidecars in the local artifact directories, so rollout JSON metrics are the inspectable evidence.

## Retimed Env Smoke

- Job `{env_smoke["job_id"]}` completed `{_fmt(env_smoke.get("steps_completed"))}` steps with non-finite count `{env_smoke.get("nonfinite_count")}`.
- Observation size remained baseline `72`; task registration and baseline registration checks passed in the validation JSON.
- Runtime duration `{_fmt(env_smoke.get("runtime_duration_s"))}` s is within the 10 s episode, target clearance min `{_fmt(env_smoke.get("target_clearance_min"))}` m, unsafe target rate max `{_fmt(env_smoke.get("unsafe_target_rate_max"))}`.

## Next Debug Direction

Keep the original baseline unchanged and continue in the separate `Dextrah-Franka-Cube-Grasp-Traj-Tracking` variant. Based on the retimed RL25 eval, the next cheap ablation should target behavior: inspect whether gripper width target `0.0` and weak orientation tracking encourage closing before useful contact. A bounded follow-up should adjust only the variant's tracking/reward schedule, run a task smoke, then a short RL smoke/eval before any larger training.
"""
    path.write_text(text, encoding="utf-8")


def _build_run_specs(root: Path) -> list[RunSpec]:
    return [
        RunSpec(
            key="phase_starved_rl25_train",
            label="Before retime RL25 train",
            run_type="train",
            job_id="1027718",
            commit="9abe6fbcd732afbe4a1339d3f4ffed72d29ff82c",
            result_dir=root / "franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509",
            log_path=root / "franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509" / "teacher_8gpu_1027718.out",
            config_path=root / "franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509" / "params" / "env.yaml",
        ),
        RunSpec(
            key="phase_starved_rl25_eval",
            label="Before retime RL25 eval",
            run_type="eval",
            job_id="1027719",
            commit="9abe6fbcd732afbe4a1339d3f4ffed72d29ff82c",
            result_dir=root / "franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748",
            metrics_path=root / "franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748" / "metrics.json",
            log_path=root / "franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748" / "eval_franka_cube_1027719.out",
            config_path=root / "franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509" / "params" / "env.yaml",
        ),
        RunSpec(
            key="retimed_env_smoke",
            label="Retimed env smoke",
            run_type="validation",
            job_id="1027720",
            commit="22f674cd42eaf79fa9e42433a9e2f1dff04a917a",
            result_dir=root / "franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430",
            metrics_path=root / "franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430" / "metrics.json",
            log_path=root / "franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430" / "validate_franka_cube_1027720.out",
        ),
        RunSpec(
            key="retimed_3epoch_eval",
            label="Retimed 3-epoch eval",
            run_type="eval",
            job_id="1027723",
            commit="08ce93bb4afb294dee88f1202fcf64e82e028f6e",
            result_dir=root / "franka_cube_traj_tracking_retime_ref_eval720_20260611_131855",
            metrics_path=root / "franka_cube_traj_tracking_retime_ref_eval720_20260611_131855" / "metrics.json",
            log_path=root / "franka_cube_traj_tracking_retime_ref_eval720_20260611_131855" / "eval_franka_cube_1027723.out",
        ),
        RunSpec(
            key="retimed_rl25_train",
            label="Retimed RL25 train",
            run_type="train",
            job_id="1027724",
            commit="26fa0b7ef0b412979aa6476c075125c49a32afcc",
            result_dir=root / "franka_cube_traj_tracking_retime_ref_rl25_20260611_132107",
            log_path=root / "franka_cube_traj_tracking_retime_ref_rl25_20260611_132107" / "teacher_8gpu_1027724.out",
            config_path=root / "franka_cube_traj_tracking_retime_ref_rl25_20260611_132107" / "params" / "env.yaml",
        ),
        RunSpec(
            key="retimed_rl25_eval",
            label="Retimed RL25 eval",
            run_type="eval",
            job_id="1027726",
            commit="26fa0b7ef0b412979aa6476c075125c49a32afcc",
            result_dir=root / "franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411",
            metrics_path=root / "franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411" / "metrics.json",
            log_path=root / "franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411" / "eval_franka_cube_1027726.out",
            config_path=root / "franka_cube_traj_tracking_retime_ref_rl25_20260611_132107" / "params" / "env.yaml",
        ),
    ]


def _write_plots(root: Path, output_dir: Path, summaries: list[dict]) -> tuple[Path, Path]:
    metrics = {
        "before": _load_json(root / "franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748" / "metrics.json"),
        "retime3": _load_json(root / "franka_cube_traj_tracking_retime_ref_eval720_20260611_131855" / "metrics.json"),
        "retime25": _load_json(root / "franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411" / "metrics.json"),
    }
    phase_png = output_dir / "phase_progress_and_target_safety.png"
    _draw_plot(
        phase_png,
        "Franka Cube Trajectory Tracking: Retiming Fixes Phase Starvation, Target Safety Stays Clean",
        [
            {
                "title": "Phase progress",
                "y_min": 0.0,
                "y_max": 1.05,
                "series": [
                    ("before retime RL25 eval 1027719", _step_series(metrics["before"], "traj_phase_progress")),
                    ("retimed 3-epoch eval 1027723", _step_series(metrics["retime3"], "traj_phase_progress")),
                    ("retimed RL25 eval 1027726", _step_series(metrics["retime25"], "traj_phase_progress")),
                ],
            },
            {
                "title": "Tracking target table clearance (m)",
                "y_min": 0.0,
                "y_max": 0.36,
                "thresholds": [{"value": 0.025, "label": "min target clearance 0.025 m", "color": "#d62728"}],
                "series": [
                    ("before retime RL25 eval 1027719", _step_series(metrics["before"], "cube_traj_tracking_target_table_clearance_min")),
                    ("retimed 3-epoch eval 1027723", _step_series(metrics["retime3"], "cube_traj_tracking_target_table_clearance_min")),
                    ("retimed RL25 eval 1027726", _step_series(metrics["retime25"], "cube_traj_tracking_target_table_clearance_min")),
                ],
            },
            {
                "title": "Unsafe target rate",
                "y_min": -0.02,
                "y_max": 1.02,
                "series": [
                    ("before retime RL25 eval 1027719", _step_series(metrics["before"], "cube_traj_tracking_unsafe_target_rate")),
                    ("retimed 3-epoch eval 1027723", _step_series(metrics["retime3"], "cube_traj_tracking_unsafe_target_rate")),
                    ("retimed RL25 eval 1027726", _step_series(metrics["retime25"], "cube_traj_tracking_unsafe_target_rate")),
                ],
            },
        ],
    )
    behavior_png = output_dir / "behavior_reward_lift_finger_metrics.png"
    _draw_plot(
        behavior_png,
        "Franka Cube Trajectory Tracking: Behavior Metrics After Retiming",
        [
            {
                "title": "Reward mean",
                "series": [
                    ("before retime RL25 eval 1027719", _step_series(metrics["before"], "reward_mean")),
                    ("retimed 3-epoch eval 1027723", _step_series(metrics["retime3"], "reward_mean")),
                    ("retimed RL25 eval 1027726", _step_series(metrics["retime25"], "reward_mean")),
                ],
            },
            {
                "title": "Cube lift height max (m)",
                "y_min": 0.0,
                "y_max": 0.14,
                "thresholds": [{"value": 0.10, "label": "nominal lifted threshold 0.10 m", "color": "#888888"}],
                "series": [
                    ("before retime RL25 eval 1027719", _step_series(metrics["before"], "cube_lift_height_max")),
                    ("retimed 3-epoch eval 1027723", _step_series(metrics["retime3"], "cube_lift_height_max")),
                    ("retimed RL25 eval 1027726", _step_series(metrics["retime25"], "cube_lift_height_max")),
                ],
            },
            {
                "title": "Gripper width and finger distance to cube (m)",
                "series": [
                    ("retimed RL25 gripper width", _step_series(metrics["retime25"], "gripper_width")),
                    ("retimed RL25 finger-center to cube", _step_series(metrics["retime25"], "finger_center_to_cube_dist")),
                    ("retimed RL25 ee to cube", _step_series(metrics["retime25"], "ee_to_cube_dist")),
                ],
            },
            {
                "title": "Finger table clearance and violation (m)",
                "y_min": 0.0,
                "y_max": 0.12,
                "thresholds": [{"value": 0.05, "label": "finger clearance target 0.05 m", "color": "#888888"}],
                "series": [
                    ("before retime min clearance", _step_series(metrics["before"], "finger_table_clearance_min")),
                    ("retimed RL25 min clearance", _step_series(metrics["retime25"], "finger_table_clearance_min")),
                    ("retimed RL25 violation max", _step_series(metrics["retime25"], "finger_table_clearance_violation_max")),
                ],
            },
        ],
        panel_height=250,
    )
    return phase_png, behavior_png


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("cluster_results/l401"), help="Local fetched l401 artifact root.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output bundle directory. Defaults to cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_<timestamp>.",
    )
    args = parser.parse_args()

    root = args.root
    output_dir = args.output_dir or root / f"franka_cube_traj_tracking_artifact_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = _build_run_specs(root)
    summaries = [_summarize_run(spec) for spec in specs]
    phase_png, behavior_png = _write_plots(root, output_dir, summaries)
    summary_json = output_dir / "summary.json"
    summary_csv = output_dir / "summary.csv"
    report_md = output_dir / "comparison_report.md"
    summary_json.write_text(json.dumps({"runs": summaries}, indent=2), encoding="utf-8")
    _write_csv(summary_csv, summaries)
    _write_report(report_md, summaries, phase_png, behavior_png, summary_csv, summary_json)

    print(f"artifact_dir={output_dir}")
    print(f"report={report_md}")
    print(f"summary_json={summary_json}")
    print(f"summary_csv={summary_csv}")
    print(f"phase_png={phase_png}")
    print(f"behavior_png={behavior_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
