"""Build inspectable trajectory-tracking eval artifacts from metrics and trace files."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
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


def _load_train_bc_metrics(path: Path | None) -> dict[str, object]:
    """Load comparable train/eval metadata from a BC diagnostic report.

    BC diagnostics do not write the full Hydra train environment YAML that PPO
    runs have.  They do record the checkpoint, dims, collection policy, and
    compact trajectory reference metadata, which is enough to turn an otherwise
    opaque `train_config_unavailable` into a partial audit with explicit gaps.
    """

    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text())
    reference = data.get("reference_summary", {})
    reference = reference if isinstance(reference, dict) else {}
    result: dict[str, object] = {
        "__source": "bc_metrics",
        "__bc_metrics_path": str(path),
        "__bc_task": data.get("task"),
        "__bc_input_checkpoint": data.get("input_checkpoint"),
        "__bc_output_checkpoint": data.get("output_checkpoint"),
        "__bc_collection_action_source": data.get("collection_action_source"),
        "__bc_collection_teacher_alphas": data.get("collection_teacher_alphas")
        or data.get("collection_teacher_alpha"),
        "__bc_residual_adapter_enabled": data.get("residual_adapter_enabled"),
        "__bc_residual_context_features": data.get("residual_context_features"),
        "__bc_curobo_validated": data.get("curobo_validated"),
        "__bc_reference_summary": reference,
    }
    obs_dim = data.get("obs_dim")
    action_dim = data.get("action_dim")
    if isinstance(obs_dim, (int, float)):
        result["observation_space"] = int(obs_dim)
        result["state_space"] = int(obs_dim)
    if isinstance(action_dim, (int, float)):
        result["action_space"] = int(action_dim)
    if reference.get("source") is not None:
        result["trajectory_tracking_reference_path"] = reference.get("source")
    duration = reference.get("configured_runtime_duration_s") or reference.get("runtime_duration_s")
    if duration is not None:
        result["trajectory_tracking_reference_duration_s"] = duration
    min_gripper_width = reference.get("min_target_gripper_width_m")
    if min_gripper_width is not None:
        result["trajectory_tracking_min_target_gripper_width"] = min_gripper_width
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


def _local_video_files(metrics_path: Path, summary: dict[str, object]) -> list[Path]:
    """Resolve eval videos after a remote `/results` run has been fetched locally."""

    candidates: list[Path] = []
    for raw_path in summary.get("video_files") or []:
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        if path.exists():
            candidates.append(path)
            continue
        fetched = metrics_path.parent / "videos" / path.name
        if fetched.exists():
            candidates.append(fetched)
    for path in sorted((metrics_path.parent / "videos").glob("*.mp4")):
        if path not in candidates:
            candidates.append(path)
    return candidates


def _local_sidecar_file(metrics_path: Path, remote_path: object, default_name: str) -> Path | None:
    if isinstance(remote_path, str):
        path = Path(remote_path)
        if path.exists():
            return path
        fetched = metrics_path.parent / path.name
        if fetched.exists():
            return fetched
    fetched = metrics_path.parent / default_name
    return fetched if fetched.exists() else None


def _video_metadata(video_path: Path) -> dict[str, object]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,nb_frames,duration,r_frame_rate",
                "-of",
                "json",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        streams = payload.get("streams", [])
        return streams[0] if streams else {}
    except Exception as exc:
        return {"error": str(exc)}


def _frame_count(metadata: dict[str, object]) -> int:
    nb_frames = metadata.get("nb_frames")
    try:
        if nb_frames not in (None, "N/A"):
            return int(nb_frames)
    except (TypeError, ValueError):
        pass
    try:
        duration = float(metadata.get("duration") or 0.0)
        rate_raw = str(metadata.get("r_frame_rate") or "0/1")
        num, den = rate_raw.split("/", 1)
        rate = float(num) / max(float(den), 1.0)
        return int(round(duration * rate))
    except Exception:
        return 0


def _draw_video_contact_sheet(video_path: Path, output_path: Path, run_name: str | None) -> dict[str, object]:
    metadata = _video_metadata(video_path)
    frame_count = _frame_count(metadata)
    if frame_count <= 0:
        raise RuntimeError(f"Could not determine frame count for {video_path}")
    frame_indices = sorted({0, frame_count // 3, (2 * frame_count) // 3, frame_count - 1})

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp_dir = Path(tmp_raw)
        selector = "+".join(f"eq(n\\,{idx})" for idx in frame_indices)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-vf",
                f"select='{selector}'",
                "-vsync",
                "0",
                str(tmp_dir / "frame_%03d.jpg"),
            ],
            check=True,
        )
        frame_paths = sorted(tmp_dir.glob("frame_*.jpg"))
        if not frame_paths:
            raise RuntimeError(f"No frames extracted from {video_path}")

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 18)
            font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 21)
        except Exception:
            font = font_b = None

        thumb_w = 360
        thumbs = []
        for idx, frame_path in enumerate(frame_paths):
            image = Image.open(frame_path).convert("RGB")
            scale = thumb_w / image.width
            thumb_h = int(round(image.height * scale))
            image = image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            thumbs.append((image, frame_indices[min(idx, len(frame_indices) - 1)]))

        label_h = 58
        width = thumb_w * len(thumbs)
        height = max(image.height for image, _ in thumbs) + label_h
        sheet = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(sheet)
        title = run_name or video_path.parent.parent.name
        draw.text((12, 8), title, fill=(20, 20, 20), font=font_b)
        for col, (image, frame_idx) in enumerate(thumbs):
            x = col * thumb_w
            sheet.paste(image, (x, label_h))
            draw.text((x + 12, 34), f"frame {frame_idx}/{frame_count - 1}", fill=(40, 40, 40), font=font)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output_path)

    metadata["frame_count_resolved"] = frame_count
    metadata["contact_sheet_frames"] = frame_indices
    return metadata


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
                ("hold active", "hold_active_rate", (120, 70, 170), 1.0),
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
                ("hold close", "hold_applied_action_close_mean", (80, 80, 80), 1.0),
                ("teacher alpha", "cube_traj_tracking_teacher_force_alpha", (20, 20, 20), 1.0),
                ("raw-ref L2", "cube_traj_tracking_raw_policy_reference_action_error_l2", (200, 40, 85), 2.2),
                ("applied-ref L2", "cube_traj_tracking_applied_reference_action_error_l2", (70, 125, 60), 2.2),
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


def _consistency(
    train_env: dict[str, object],
    eval_env: dict[str, object],
    summary: dict[str, object],
) -> dict[str, object]:
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
        "trajectory_tracking_teacher_force_enabled",
        "trajectory_tracking_teacher_force_alpha_start",
        "trajectory_tracking_teacher_force_alpha_end",
        "trajectory_tracking_teacher_force_phase_end",
        "trajectory_tracking_teacher_force_anneal_steps",
        "trajectory_tracking_action_alignment_compare_raw_policy",
    ]
    rows = {}
    mismatches = []
    missing_train_keys = []
    missing_eval_keys = []
    unverified_train_keys = []
    expected_env_override_keys = set(_expected_env_override_keys(summary, eval_env))
    train_source = train_env.get("__source") if train_env else None
    if not train_env:
        for key in keys:
            eval_value = eval_env.get(key)
            rows[key] = {
                "train": None,
                "eval": eval_value,
                "match": None,
                "status": "train_config_unavailable",
            }
            if eval_value is not None:
                missing_train_keys.append(key)
        return {
            "checks": rows,
            "mismatches": [],
            "missing_train_keys": missing_train_keys,
            "missing_eval_keys": missing_eval_keys,
            "unverified_train_keys": unverified_train_keys,
            "expected_eval_overrides": _expected_eval_overrides(summary),
            "passed": None,
            "status": "train_config_unavailable",
            "train_source": None,
        }
    extra_checks: dict[str, dict[str, object]] = {}
    for key in keys:
        train_value = train_env.get(key)
        eval_value = eval_env.get(key)
        if train_source == "bc_metrics" and train_value is None and eval_value is not None:
            status = "bc_metadata_unavailable"
            match = None
            unverified_train_keys.append(key)
        elif train_value is None and eval_value is not None:
            status = "missing_train_key"
            match = None
            missing_train_keys.append(key)
        elif eval_value is None and train_value is not None:
            status = "missing_eval_key"
            match = None
            missing_eval_keys.append(key)
        else:
            match = train_value == eval_value
            if match:
                status = "match"
            elif key in expected_env_override_keys:
                status = "expected_eval_override"
                match = None
            else:
                status = "mismatch"
        if not match:
            if status == "mismatch":
                mismatches.append(key)
        rows[key] = {"train": train_value, "eval": eval_value, "match": match, "status": status}
    if train_source == "bc_metrics":
        reference = train_env.get("__bc_reference_summary", {})
        reference = reference if isinstance(reference, dict) else {}
        eval_reference = summary.get("trajectory_tracking_reference", {})
        eval_reference = eval_reference if isinstance(eval_reference, dict) else {}
        extra_specs = {
            "task": (train_env.get("__bc_task"), summary.get("task")),
            "checkpoint": (train_env.get("__bc_output_checkpoint"), summary.get("checkpoint")),
            "reference_curobo_validated": (
                reference.get("curobo_validated"),
                eval_reference.get("curobo_validated"),
            ),
            "reference_validation_passed": (
                reference.get("validation_passed"),
                eval_reference.get("validation_passed"),
            ),
            "reference_transform_policy": (
                reference.get("transform_policy"),
                eval_reference.get("transform_policy"),
            ),
            "reference_joint_trajectory_policy": (
                reference.get("joint_trajectory_policy"),
                eval_reference.get("joint_trajectory_policy"),
            ),
            "reference_gripper_schedule_policy": (
                reference.get("gripper_schedule_policy"),
                eval_reference.get("gripper_schedule_policy"),
            ),
            "reference_runtime_object_pose_policy": (
                reference.get("runtime_object_pose_policy"),
                eval_reference.get("runtime_object_pose_policy"),
            ),
            "reference_source_tag": (
                reference.get("source_tag"),
                eval_reference.get("source_tag"),
            ),
        }
        for key, (train_value, eval_value) in extra_specs.items():
            if isinstance(train_value, float) or isinstance(eval_value, float):
                try:
                    match = abs(float(train_value) - float(eval_value)) <= 1e-9
                except (TypeError, ValueError):
                    match = False
            else:
                match = train_value == eval_value
            status = "match" if match else "mismatch"
            if not match:
                mismatches.append(key)
            extra_checks[key] = {
                "train": train_value,
                "eval": eval_value,
                "match": match,
                "status": status,
            }
    passed = len(mismatches) == 0 and len(missing_train_keys) == 0 and len(missing_eval_keys) == 0
    if train_source == "bc_metrics":
        status = "bc_metadata_partial_pass" if passed else "bc_metadata_partial_failed"
    else:
        status = "passed" if passed else "failed"
    return {
        "checks": rows,
        "extra_checks": extra_checks,
        "mismatches": mismatches,
        "missing_train_keys": missing_train_keys,
        "missing_eval_keys": missing_eval_keys,
        "unverified_train_keys": unverified_train_keys,
        "bc_metadata": {
            "metrics_path": train_env.get("__bc_metrics_path"),
            "collection_action_source": train_env.get("__bc_collection_action_source"),
            "collection_teacher_alphas": train_env.get("__bc_collection_teacher_alphas"),
            "input_checkpoint": train_env.get("__bc_input_checkpoint"),
            "output_checkpoint": train_env.get("__bc_output_checkpoint"),
            "residual_adapter_enabled": train_env.get("__bc_residual_adapter_enabled"),
            "residual_context_features": train_env.get("__bc_residual_context_features"),
            "curobo_validated": train_env.get("__bc_curobo_validated"),
        }
        if train_source == "bc_metrics"
        else {},
        "expected_eval_overrides": _expected_eval_overrides(summary),
        "expected_env_override_keys": sorted(expected_env_override_keys),
        "passed": passed,
        "status": status,
        "train_source": train_source or "train_env_yaml",
    }


def _expected_eval_overrides(summary: dict[str, object]) -> dict[str, object]:
    """Fields intentionally controlled by an eval diagnostic, not train/eval env parity."""

    keys = [
        "action_source",
        "action_source_notes",
        "reference_mix_alpha",
        "reference_mix_gripper_alpha",
        "reference_mix_gripper_alpha_override",
        "reference_mix_z_alpha",
        "reference_mix_z_alpha_override",
        "hold_config",
        "checkpoint",
        "num_envs",
        "num_steps_requested",
        "deterministic",
        "suppress_success_termination",
        "success_termination_suppression_installed",
        "video_enabled",
        "video_folder",
    ]
    return {key: summary.get(key) for key in keys if summary.get(key) is not None}


def _expected_env_override_keys(summary: dict[str, object], eval_env: dict[str, object]) -> list[str]:
    """Env config fields intentionally changed for a fixed diagnostic eval."""

    expected: list[str] = []
    if bool(eval_env.get("trajectory_tracking_teacher_force_enabled")):
        expected.extend(
            [
                "trajectory_tracking_teacher_force_alpha_start",
                "trajectory_tracking_teacher_force_alpha_end",
                "trajectory_tracking_teacher_force_phase_end",
                "trajectory_tracking_teacher_force_anneal_steps",
            ]
        )
    if summary.get("reference_mix_alpha") is not None:
        expected.append("reference_mix_alpha")
    if summary.get("reference_mix_gripper_alpha") is not None:
        expected.append("reference_mix_gripper_alpha")
    if summary.get("reference_mix_z_alpha") is not None:
        expected.append("reference_mix_z_alpha")
    return expected


def _step_summary_value(summary: dict[str, object], key: str, field: str) -> float | None:
    record = summary.get(key)
    if not isinstance(record, dict):
        return None
    value = record.get(field)
    return float(value) if isinstance(value, (int, float)) else None


def _write_success_diagnostics(
    output_dir: Path,
    compact: dict[str, object],
    summary: dict[str, object],
    steps: list[dict[str, object]],
) -> tuple[Path, Path, Path]:
    diagnostics = {
        "action_source": compact.get("action_source"),
        "reference_mix_alpha": compact.get("reference_mix_alpha"),
        "reference_mix_gripper_alpha": compact.get("reference_mix_gripper_alpha"),
        "reference_mix_gripper_alpha_override": compact.get("reference_mix_gripper_alpha_override"),
        "reference_mix_z_alpha": compact.get("reference_mix_z_alpha"),
        "reference_mix_z_alpha_override": compact.get("reference_mix_z_alpha_override"),
        "hold_config": compact.get("hold_config"),
        "suppress_success_termination": compact.get("suppress_success_termination"),
        "success_termination_suppression_installed": compact.get("success_termination_suppression_installed"),
        "num_steps_completed": compact.get("num_steps_completed"),
        "done_count": compact.get("done_count"),
        "done_ever_count": compact.get("done_ever_count"),
        "done_after_success_count": compact.get("done_after_success_count"),
        "done_reason_counts": compact.get("done_reason_counts"),
        "done_events": compact.get("done_events"),
        "success_ever_count": compact.get("success_ever_count"),
        "success_ever_rate": compact.get("success_ever_rate"),
        "success_rate_mean": compact.get("success_rate_mean"),
        "success_rate_final": compact.get("success_rate_final"),
        "success_rate_max": compact.get("success_rate_max"),
        "first_success_step": compact.get("first_success_step"),
        "last_success_step": compact.get("last_success_step"),
        "first_done_step": compact.get("first_done_step"),
        "suppressed_success_done_count": compact.get("suppressed_success_done_count"),
        "suppressed_success_done_rate": compact.get("suppressed_success_done_rate"),
        "first_suppressed_success_done_step": compact.get("first_suppressed_success_done_step"),
        "cube_lift_height_max": compact.get("cube_lift_height_max"),
        "ee_to_cube_final": compact.get("ee_to_cube_final"),
        "finger_center_to_cube_final": compact.get("finger_center_to_cube_final"),
        "target_unsafe_rate_max": compact.get("target_unsafe_rate_max"),
        "target_clearance_min": compact.get("target_clearance_min"),
        "hold_trigger_step_mean": compact.get("hold_trigger_step_mean"),
        "hold_lift_trigger_rate_mean": compact.get("hold_lift_trigger_rate_mean"),
        "hold_success_trigger_rate_mean": compact.get("hold_success_trigger_rate_mean"),
        "hold_contact_trigger_rate_mean": compact.get("hold_contact_trigger_rate_mean"),
        "reference_curobo_validated": compact.get("reference_curobo_validated"),
        "reference_source_tag": compact.get("reference_source_tag"),
    }
    diagnostics_json_path = output_dir / "success_diagnostics.json"
    diagnostics_json_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")

    diagnostics_csv_path = output_dir / "success_diagnostics.csv"
    with diagnostics_csv_path.open("w", newline="") as csv_file:
        fieldnames = sorted(diagnostics)
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                for key, value in diagnostics.items()
            }
        )

    focus_candidates = [
        _step_summary_value(summary, "first_success_step", "min"),
        _step_summary_value(summary, "last_success_step", "max"),
        _step_summary_value(summary, "first_done_step", "max"),
        _step_summary_value(summary, "first_suppressed_success_done_step", "min"),
        compact.get("hold_trigger_step_mean"),
    ]
    focus_steps = [int(round(value)) for value in focus_candidates if isinstance(value, (int, float))]
    if focus_steps:
        start_step = max(1, min(focus_steps) - 80)
        end_step = min(len(steps), max(focus_steps) + 80)
    else:
        start_step = 1
        end_step = min(len(steps), 160)
    columns = [
        "step",
        "success_rate",
        "eval_success_ever_count",
        "eval_success_ever_rate",
        "eval_done_count_step",
        "eval_done_count_cumulative",
        "eval_done_after_success_rate",
        "eval_done_success_done_rate",
        "eval_suppressed_success_done_rate",
        "eval_suppressed_success_done_count",
        "cube_lift_height",
        "cube_lift_height_max",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "max_finger_to_cube_dist",
        "finger_table_clearance",
        "gripper_width",
        "hold_active_rate",
        "hold_new_trigger_rate",
        "hold_trigger_step_mean",
        "hold_lift_trigger_rate",
        "hold_success_trigger_rate",
        "hold_contact_trigger_rate",
        "cube_traj_tracking_action_close",
        "cube_traj_tracking_action_up",
        "cube_traj_tracking_gripper_action",
        "cube_traj_tracking_teacher_force_alpha",
        "cube_traj_tracking_teacher_force_active_rate",
        "cube_traj_tracking_raw_policy_reference_action_error_l2",
        "cube_traj_tracking_applied_reference_action_error_l2",
        "cube_traj_tracking_applied_policy_action_error_l2",
        "cube_traj_tracking_raw_policy_action_close",
        "cube_traj_tracking_raw_policy_action_up",
        "cube_traj_tracking_applied_action_close",
        "cube_traj_tracking_applied_action_up",
        "cube_traj_tracking_close_action_reward",
        "cube_traj_tracking_lift_action_reward",
        "cube_traj_tracking_target_table_clearance",
        "cube_traj_tracking_unsafe_target_rate",
        "traj_phase_progress",
    ]
    window_trace_path = output_dir / "success_window_trace.csv"
    with window_trace_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for row in steps[start_step - 1 : end_step]:
            writer.writerow({key: row.get(key) for key in columns})
    return diagnostics_json_path, diagnostics_csv_path, window_trace_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--train-env-yaml", type=Path, default=None)
    parser.add_argument("--train-bc-metrics", type=Path, default=None)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.metrics.read_text())
    summary = payload["summary"]
    steps = payload["steps"]
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_path = output_dir / "trajectory_trace_plot.png"
    _draw_plot(steps, plot_path)
    video_files = _local_video_files(args.metrics, summary)
    contact_sheet_path: Path | None = None
    video_metadata: dict[str, object] = {}
    if video_files:
        contact_sheet_path = output_dir / "video_contact_sheet.png"
        try:
            video_metadata = _draw_video_contact_sheet(video_files[0], contact_sheet_path, output_dir.name)
        except Exception as exc:
            video_metadata = {"error": str(exc), "video": str(video_files[0])}

    train_env = _load_train_env(args.train_env_yaml)
    train_bc_env = _load_train_bc_metrics(args.train_bc_metrics)
    if train_bc_env:
        for key, value in train_bc_env.items():
            train_env.setdefault(key, value)
    eval_env = summary.get("env_config", {}) if isinstance(summary.get("env_config"), dict) else {}
    consistency = _consistency(train_env, eval_env, summary)
    (output_dir / "train_eval_consistency.json").write_text(json.dumps(consistency, indent=2, sort_keys=True) + "\n")

    compact = {
        "action_source": summary.get("action_source"),
        "action_source_notes": summary.get("action_source_notes"),
        "reference_mix_alpha": summary.get("reference_mix_alpha"),
        "reference_mix_gripper_alpha": summary.get("reference_mix_gripper_alpha"),
        "reference_mix_gripper_alpha_override": summary.get("reference_mix_gripper_alpha_override"),
        "reference_mix_z_alpha": summary.get("reference_mix_z_alpha"),
        "reference_mix_z_alpha_override": summary.get("reference_mix_z_alpha_override"),
        "hold_config": summary.get("hold_config"),
        "hold_target_policy": (
            summary.get("hold_config", {}).get("target_policy")
            if isinstance(summary.get("hold_config"), dict)
            else None
        ),
        "hold_trigger_mode": (
            summary.get("hold_config", {}).get("hold_trigger_mode")
            if isinstance(summary.get("hold_config"), dict)
            else None
        ),
        "checkpoint": summary.get("checkpoint"),
        "done_count": summary.get("done_count"),
        "num_steps_completed": summary.get("num_steps_completed"),
        "reward_mean": summary.get("reward_mean"),
        "reward_final": summary.get("reward_final"),
        "success_rate_mean": summary.get("success_rate_mean"),
        "success_rate_final": summary.get("success_rate_final"),
        "success_rate_max": summary.get("success_rate_max") or _summary(summary, "success_rate", "max"),
        "success_ever_rate": summary.get("success_ever_rate"),
        "success_ever_count": summary.get("success_ever_count"),
        "first_success_step": summary.get("first_success_step"),
        "last_success_step": summary.get("last_success_step"),
        "done_ever_rate": summary.get("done_ever_rate"),
        "done_ever_count": summary.get("done_ever_count"),
        "first_done_step": summary.get("first_done_step"),
        "done_after_success_rate": summary.get("done_after_success_rate"),
        "done_after_success_count": summary.get("done_after_success_count"),
        "suppressed_success_done_rate": summary.get("suppressed_success_done_rate"),
        "suppressed_success_done_count": summary.get("suppressed_success_done_count"),
        "first_suppressed_success_done_step": summary.get("first_suppressed_success_done_step"),
        "done_reason_counts": summary.get("done_reason_counts"),
        "done_events": summary.get("done_events"),
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
        "teacher_force_alpha_mean": _summary(summary, "cube_traj_tracking_teacher_force_alpha", "mean"),
        "teacher_force_alpha_final": _summary(summary, "cube_traj_tracking_teacher_force_alpha", "final"),
        "teacher_force_phase_end": eval_env.get("trajectory_tracking_teacher_force_phase_end"),
        "teacher_force_configured_alpha_start": eval_env.get("trajectory_tracking_teacher_force_alpha_start"),
        "teacher_force_configured_alpha_end": eval_env.get("trajectory_tracking_teacher_force_alpha_end"),
        "teacher_force_active_rate_mean": _summary(
            summary, "cube_traj_tracking_teacher_force_active_rate", "mean"
        ),
        "teacher_force_active_rate_final": _summary(
            summary, "cube_traj_tracking_teacher_force_active_rate", "final"
        ),
        "raw_policy_reference_action_error_l2_mean": _summary(
            summary, "cube_traj_tracking_raw_policy_reference_action_error_l2", "mean"
        ),
        "raw_policy_reference_action_error_l2_final": _summary(
            summary, "cube_traj_tracking_raw_policy_reference_action_error_l2", "final"
        ),
        "env_applied_reference_action_error_l2_mean": _summary(
            summary, "cube_traj_tracking_applied_reference_action_error_l2", "mean"
        ),
        "env_applied_policy_action_error_l2_mean": _summary(
            summary, "cube_traj_tracking_applied_policy_action_error_l2", "mean"
        ),
        "env_raw_policy_action_close_mean": _summary(summary, "cube_traj_tracking_raw_policy_action_close", "mean"),
        "env_raw_policy_action_up_mean": _summary(summary, "cube_traj_tracking_raw_policy_action_up", "mean"),
        "env_applied_action_close_mean": _summary(summary, "cube_traj_tracking_applied_action_close", "mean"),
        "env_applied_action_up_mean": _summary(summary, "cube_traj_tracking_applied_action_up", "mean"),
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
        "hold_active_rate_mean": _summary(summary, "hold_active_rate", "mean"),
        "hold_active_rate_final": _summary(summary, "hold_active_rate", "final"),
        "hold_new_trigger_rate_max": _summary(summary, "hold_new_trigger_rate", "max"),
        "hold_trigger_step_mean": _summary(summary, "hold_trigger_step_mean", "mean"),
        "hold_trigger_mode_id_mean": _summary(summary, "hold_trigger_mode_id", "mean"),
        "hold_phase_trigger_rate_mean": _summary(summary, "hold_phase_trigger_rate", "mean"),
        "hold_lift_trigger_rate_mean": _summary(summary, "hold_lift_trigger_rate", "mean"),
        "hold_success_trigger_rate_mean": _summary(summary, "hold_success_trigger_rate", "mean"),
        "hold_contact_trigger_rate_mean": _summary(summary, "hold_contact_trigger_rate", "mean"),
        "hold_contact_after_phase_trigger_rate_mean": _summary(
            summary, "hold_contact_after_phase_trigger_rate", "mean"
        ),
        "hold_target_pos_z_final": _summary(summary, "hold_target_pos_z_mean", "final"),
        "hold_target_policy_id_mean": _summary(summary, "hold_target_policy_id", "mean"),
        "hold_trigger_ee_cube_offset_x_final": _summary(summary, "hold_trigger_ee_cube_offset_x_mean", "final"),
        "hold_trigger_ee_cube_offset_y_final": _summary(summary, "hold_trigger_ee_cube_offset_y_mean", "final"),
        "hold_trigger_ee_cube_offset_z_final": _summary(summary, "hold_trigger_ee_cube_offset_z_mean", "final"),
        "hold_action_close_mean": _summary(summary, "hold_action_close_mean", "mean"),
        "hold_action_up_mean": _summary(summary, "hold_action_up_mean", "mean"),
        "hold_applied_action_close_mean": _summary(summary, "hold_applied_action_close_mean", "mean"),
        "hold_applied_action_up_mean": _summary(summary, "hold_applied_action_up_mean", "mean"),
        "applied_reference_action_error_l2_mean": _summary(
            summary, "applied_reference_action_error_l2_mean", "mean"
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
                "teacher_force_alpha_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_teacher_force_alpha", "mean"
                ),
                "teacher_force_active_rate": _window_metric(
                    summary, window_name, "cube_traj_tracking_teacher_force_active_rate", "mean"
                ),
                "env_raw_policy_reference_error_l2_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_raw_policy_reference_action_error_l2", "mean"
                ),
                "env_applied_reference_error_l2_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_applied_reference_action_error_l2", "mean"
                ),
                "env_applied_policy_error_l2_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_applied_policy_action_error_l2", "mean"
                ),
                "env_raw_policy_close_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_raw_policy_action_close", "mean"
                ),
                "env_raw_policy_up_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_raw_policy_action_up", "mean"
                ),
                "env_applied_close_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_applied_action_close", "mean"
                ),
                "env_applied_up_mean": _window_metric(
                    summary, window_name, "cube_traj_tracking_applied_action_up", "mean"
                ),
                "raw_policy_close_mean": _window_metric(summary, window_name, "raw_policy_action_close_mean", "mean"),
                "raw_policy_up_mean": _window_metric(summary, window_name, "raw_policy_action_up_mean", "mean"),
                "reference_close_mean": _window_metric(
                    summary, window_name, "reference_delta_action_close_mean", "mean"
                ),
                "reference_up_mean": _window_metric(summary, window_name, "reference_delta_action_up_mean", "mean"),
                "mixed_close_mean": _window_metric(summary, window_name, "mixed_action_close_mean", "mean"),
                "mixed_up_mean": _window_metric(summary, window_name, "mixed_action_up_mean", "mean"),
                "hold_active_rate": _window_metric(summary, window_name, "hold_active_rate", "mean"),
                "hold_applied_close_mean": _window_metric(
                    summary, window_name, "hold_applied_action_close_mean", "mean"
                ),
                "hold_applied_up_mean": _window_metric(
                    summary, window_name, "hold_applied_action_up_mean", "mean"
                ),
                "applied_reference_error_l2_mean": _window_metric(
                    summary, window_name, "applied_reference_action_error_l2_mean", "mean"
                ),
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
        "suppress_success_termination": summary.get("suppress_success_termination"),
        "success_termination_suppression_installed": summary.get("success_termination_suppression_installed"),
        "trace_csv_path": summary.get("trace_csv_path"),
        "trace_jsonl_path": summary.get("trace_jsonl_path"),
        "local_trace_csv_path": str(
            _local_sidecar_file(args.metrics, summary.get("trace_csv_path"), "trace.csv") or ""
        ),
        "local_trace_jsonl_path": str(
            _local_sidecar_file(args.metrics, summary.get("trace_jsonl_path"), "trace.jsonl") or ""
        ),
        "video_files": [str(path) for path in video_files],
        "video_contact_sheet": str(contact_sheet_path) if contact_sheet_path else None,
        "video_metadata": video_metadata,
    }
    diagnostics_json_path, diagnostics_csv_path, window_trace_path = _write_success_diagnostics(
        output_dir, compact, summary, steps
    )
    (output_dir / "summary.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n")
    csv_path = output_dir / "summary.csv"
    with csv_path.open("w", newline="") as csv_file:
        fieldnames = sorted(key for key in compact if key != "fixed_windows")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                for key, value in compact.items()
                if key != "fixed_windows"
            }
        )

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
                    f"{_fmt(window['hold_active_rate'], 4)}",
                    f"{_fmt(window['hold_applied_close_mean'], 4)}/{_fmt(window['hold_applied_up_mean'], 4)}",
                    _fmt(window["teacher_force_alpha_mean"], 4),
                    _fmt(window["env_raw_policy_reference_error_l2_mean"], 4),
                    _fmt(window["env_applied_reference_error_l2_mean"], 4),
                    _fmt(window["env_applied_policy_error_l2_mean"], 4),
                    f"{_fmt(window['env_raw_policy_close_mean'], 4)}/{_fmt(window['env_raw_policy_up_mean'], 4)}",
                    f"{_fmt(window['env_applied_close_mean'], 4)}/{_fmt(window['env_applied_up_mean'], 4)}",
                    _fmt(window["policy_reference_error_l2_mean"], 4),
                    _fmt(window["mixed_reference_error_l2_mean"], 4),
                    _fmt(window["applied_reference_error_l2_mean"], 4),
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
            "| Window | Reward | EE-target | EE-cube | Finger-cube | Grip width | Close util | Lift util | Raw close/up | Ref close/up | Mixed close/up | Hold active | Hold applied close/up | Teacher alpha | Env raw-ref L2 | Env applied-ref L2 | Env applied-policy L2 | Env raw close/up | Env applied close/up | Policy-ref L2 | Mixed-ref L2 | Applied-ref L2 | Align reward | Align err | Target clearance min | Lift max | Success |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *window_rows,
        ]
    )

    report = f"""# Trajectory Tracking Diagnostic Artifact

- action source: `{summary.get('action_source')}` ({summary.get('action_source_notes')})
- reference mix alpha: {_fmt(summary.get('reference_mix_alpha'))}
- reference mix z alpha: {_fmt(summary.get('reference_mix_z_alpha'))} (override={summary.get('reference_mix_z_alpha_override')})
- reference mix gripper alpha: {_fmt(summary.get('reference_mix_gripper_alpha'))} (override={summary.get('reference_mix_gripper_alpha_override')})
- hold config: `{summary.get('hold_config')}`
- suppress success termination: `{summary.get('suppress_success_termination')}` (installed={summary.get('success_termination_suppression_installed')})
- checkpoint: `{summary.get('checkpoint')}`
- steps: {summary.get('num_steps_completed')}/{summary.get('num_steps_requested')}
- reward mean/final: {_fmt(summary.get('reward_mean'))} / {_fmt(summary.get('reward_final'))}
- success mean/final/max: {_fmt(summary.get('success_rate_mean'))} / {_fmt(summary.get('success_rate_final'))} / {_fmt(compact['success_rate_max'])}
- success ever count/rate: {compact['success_ever_count']} / {_fmt(compact['success_ever_rate'])}
- done count: {summary.get('done_count')} (done ever count/rate: {compact['done_ever_count']} / {_fmt(compact['done_ever_rate'])})
- target unsafe max: {_fmt(compact['target_unsafe_rate_max'])}
- target clearance min: {_fmt(compact['target_clearance_min'])} m
- train/eval consistency status: {consistency['status']} real_mismatches={consistency['mismatches']} missing_train_keys={consistency['missing_train_keys']} missing_eval_keys={consistency['missing_eval_keys']}
- train/eval consistency source: {consistency['train_source']} unverified_train_keys={consistency.get('unverified_train_keys', [])}
- expected eval-only overrides: `{consistency['expected_eval_overrides']}`
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
- teacher-force alpha mean/final/active mean: {_fmt(compact['teacher_force_alpha_mean'])} / {_fmt(compact['teacher_force_alpha_final'])} / {_fmt(compact['teacher_force_active_rate_mean'])}
- teacher-force configured alpha start/end and phase_end: {_fmt(compact['teacher_force_configured_alpha_start'])} / {_fmt(compact['teacher_force_configured_alpha_end'])} / {_fmt(compact['teacher_force_phase_end'])}
- teacher-force alpha note: reported alpha is the applied blend coefficient after phase gating. The configured alpha is only used while `traj_phase_progress <= phase_end`; after that it is zero. If environments reset during a no-reset/suppressed-success diagnostic, their phase restarts and they can contribute nonzero final alpha.
- env raw-policy/ref L2 mean/final: {_fmt(compact['raw_policy_reference_action_error_l2_mean'])} / {_fmt(compact['raw_policy_reference_action_error_l2_final'])}
- env applied/ref L2 mean: {_fmt(compact['env_applied_reference_action_error_l2_mean'])}
- env applied/raw-policy L2 mean: {_fmt(compact['env_applied_policy_action_error_l2_mean'])}
- env raw-policy close/up mean: {_fmt(compact['env_raw_policy_action_close_mean'])} / {_fmt(compact['env_raw_policy_action_up_mean'])}
- env applied close/up mean: {_fmt(compact['env_applied_action_close_mean'])} / {_fmt(compact['env_applied_action_up_mean'])}
- reference close/up action mean: {_fmt(compact['reference_action_close_mean'])} / {_fmt(compact['reference_action_up_mean'])}
- raw policy close/up mean: {_fmt(compact['raw_policy_action_close_mean'])} / {_fmt(compact['raw_policy_action_up_mean'])}
- reference-delta close/up mean: {_fmt(compact['reference_delta_action_close_mean'])} / {_fmt(compact['reference_delta_action_up_mean'])}
- mixed close/up mean: {_fmt(compact['mixed_action_close_mean'])} / {_fmt(compact['mixed_action_up_mean'])}
- policy-reference L2/close/up error mean: {_fmt(compact['policy_reference_action_error_l2_mean'])} / {_fmt(compact['policy_reference_action_error_close_abs_mean'])} / {_fmt(compact['policy_reference_action_error_up_abs_mean'])}
- mixed-reference L2/close/up error mean: {_fmt(compact['mixed_reference_action_error_l2_mean'])} / {_fmt(compact['mixed_reference_action_error_close_abs_mean'])} / {_fmt(compact['mixed_reference_action_error_up_abs_mean'])}

## Terminal Hold

- hold active mean/final: {_fmt(compact['hold_active_rate_mean'])} / {_fmt(compact['hold_active_rate_final'])}
- hold new-trigger max: {_fmt(compact['hold_new_trigger_rate_max'])}
- hold trigger step mean: {_fmt(compact['hold_trigger_step_mean'])}
- hold trigger mode: `{compact['hold_trigger_mode']}` (id mean {_fmt(compact['hold_trigger_mode_id_mean'])})
- phase/lift/success/contact/contact-after-phase trigger rates: {_fmt(compact['hold_phase_trigger_rate_mean'])} / {_fmt(compact['hold_lift_trigger_rate_mean'])} / {_fmt(compact['hold_success_trigger_rate_mean'])} / {_fmt(compact['hold_contact_trigger_rate_mean'])} / {_fmt(compact['hold_contact_after_phase_trigger_rate_mean'])}
- hold target policy: `{compact['hold_target_policy']}` (id mean {_fmt(compact['hold_target_policy_id_mean'])})
- hold target z final: {_fmt(compact['hold_target_pos_z_final'])} m
- trigger EE-cube offset final x/y/z: {_fmt(compact['hold_trigger_ee_cube_offset_x_final'])} / {_fmt(compact['hold_trigger_ee_cube_offset_y_final'])} / {_fmt(compact['hold_trigger_ee_cube_offset_z_final'])} m
- hold action close/up mean: {_fmt(compact['hold_action_close_mean'])} / {_fmt(compact['hold_action_up_mean'])}
- hold-applied action close/up mean: {_fmt(compact['hold_applied_action_close_mean'])} / {_fmt(compact['hold_applied_action_up_mean'])}
- applied-reference action L2 mean: {_fmt(compact['applied_reference_action_error_l2_mean'])}

## Done Semantics

- first success step summary: `{compact['first_success_step']}`
- last success step summary: `{compact['last_success_step']}`
- first done step summary: `{compact['first_done_step']}`
- done-after-success count/rate: {compact['done_after_success_count']} / {_fmt(compact['done_after_success_rate'])}
- suppressed success-done count/rate: {compact['suppressed_success_done_count']} / {_fmt(compact['suppressed_success_done_rate'])}
- first suppressed success-done step summary: `{compact['first_suppressed_success_done_step']}`
- done reason counts: `{compact['done_reason_counts']}`
- done events: `{compact['done_events']}`

## Fixed-Window Rollout Metrics

{window_table}

## Files

- plot: `{plot_path}`
- video_contact_sheet: `{contact_sheet_path}`
- summary_json: `{output_dir / 'summary.json'}`
- summary_csv: `{csv_path}`
- success_diagnostics_json: `{diagnostics_json_path}`
- success_diagnostics_csv: `{diagnostics_csv_path}`
- success_window_trace_csv: `{window_trace_path}`
- consistency_json: `{output_dir / 'train_eval_consistency.json'}`
- trace_csv: `{summary.get('trace_csv_path')}`
- trace_jsonl: `{summary.get('trace_jsonl_path')}`
- local_trace_csv: `{compact['local_trace_csv_path']}`
- local_trace_jsonl: `{compact['local_trace_jsonl_path']}`
- videos: `{[str(path) for path in video_files]}`
- video_metadata: `{video_metadata}`
"""
    (output_dir / "report.md").write_text(report)
    print(output_dir)
    print(plot_path)
    print(output_dir / "report.md")


if __name__ == "__main__":
    main()
