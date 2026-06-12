"""Build inspectable artifacts from Franka cube validation smoke outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


VALIDATE_RE = re.compile(
    r"^\[VALIDATE\]\s+"
    r"step=(?P<step>\d+)\s+"
    r"reward=(?P<reward>[-+0-9.eE]+)\s+"
    r"ee_to_cube=(?P<ee_to_cube>[-+0-9.eE]+)\s+"
    r"finger_to_cube=(?P<finger_to_cube>[-+0-9.eE]+)\s+"
    r"gripper_width=(?P<gripper_width>[-+0-9.eE]+)\s+"
    r"finger_table_clearance=(?P<finger_table_clearance>[-+0-9.eE]+)\s+"
    r"lift=(?P<lift>[-+0-9.eE]+)\s+"
    r"xy_error=(?P<xy_error>[-+0-9.eE]+)\s+"
    r"success=(?P<success>[-+0-9.eE]+)"
)


def _fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if abs(value) >= 1.0:
            return f"{value:.4f}"
        return f"{value:.{digits}f}"
    return str(value)


def _parse_config(log_text: str) -> dict[str, str]:
    config: dict[str, str] = {}
    for line in log_text.splitlines():
        if "=" not in line or line.startswith("["):
            continue
        key, value = line.split("=", 1)
        if key.isupper() or key in {"validate_command", "container_host", "container_cuda_visible_devices"}:
            config[key.strip()] = value.strip()
    return config


def _parse_trace(log_text: str) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for line in log_text.splitlines():
        match = VALIDATE_RE.match(line)
        if not match:
            continue
        row: dict[str, float | int] = {"step": int(match.group("step"))}
        for key, value in match.groupdict().items():
            if key != "step":
                row[key] = float(value)
        rows.append(row)
    return rows


def _write_trace(rows: list[dict[str, float | int]], csv_path: Path, jsonl_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["step", "reward", "ee_to_cube", "finger_to_cube", "gripper_width", "finger_table_clearance", "lift", "xy_error", "success"]
    with csv_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    with jsonl_path.open("w") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, sort_keys=True) + "\n")


def _series(rows: list[dict[str, float | int]], key: str) -> list[float]:
    return [float(row.get(key, 0.0)) for row in rows]


def _draw_plot(rows: list[dict[str, float | int]], tracking: dict[str, object], output_path: Path) -> None:
    width, height = 1500, 1100
    margin_l, margin_r, margin_t = 95, 45, 85
    panel_h, panel_gap = 230, 80
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font_s = ImageFont.truetype("DejaVuSans.ttf", 13)
    except Exception:
        font = font_b = font_s = None

    draw.text((margin_l, 28), "Franka Cube Validation Smoke Trace", fill=(20, 20, 20), font=font_b)
    x0, x1 = margin_l, width - margin_r
    panels = [
        (
            "Reward / Success / Lift",
            [
                ("reward", "reward", (35, 110, 190), 4.0),
                ("lift", "lift", (55, 150, 75), 0.16),
                ("success", "success", (20, 80, 190), 1.0),
            ],
        ),
        (
            "Distances / Clearance",
            [
                ("EE-cube", "ee_to_cube", (225, 125, 35), 0.45),
                ("finger-cube", "finger_to_cube", (120, 80, 175), 0.45),
                ("finger clearance", "finger_table_clearance", (45, 145, 95), 0.36),
            ],
        ),
        (
            "Gripper / XY",
            [
                ("gripper width", "gripper_width", (40, 110, 170), 0.08),
                ("XY error", "xy_error", (210, 90, 40), 0.12),
            ],
        ),
    ]
    for idx, (title, specs) in enumerate(panels):
        y0 = margin_t + idx * (panel_h + panel_gap)
        y1 = y0 + panel_h
        draw.rectangle((x0, y0, x1, y1), outline=(214, 214, 214), width=2)
        draw.text((x0, y0 - 30), title, fill=(25, 25, 25), font=font)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y1 - frac * (y1 - y0)
            draw.line((x0, y, x1, y), fill=(238, 238, 238), width=1)
            draw.text((24, y - 8), f"{frac:.2f}", fill=(100, 100, 100), font=font_s)
        legend_x = x0 + 8
        for name, key, color, scale in specs:
            values = _series(rows, key)
            points = []
            for point_idx, value in enumerate(values):
                scaled = max(0.0, min(1.0, value / max(scale, 1.0e-8)))
                x = x0 + point_idx * (x1 - x0) / max(len(values) - 1, 1)
                y = y1 - scaled * (y1 - y0)
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=3)
            elif len(points) == 1:
                x, y = points[0]
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
            draw.rectangle((legend_x, y0 + 8, legend_x + 17, y0 + 20), fill=color)
            draw.text((legend_x + 23, y0 + 4), name, fill=(40, 40, 40), font=font_s)
            legend_x += 185

    y = margin_t + 3 * (panel_h + panel_gap) - 16
    draw.text((margin_l, y), "Action-Alignment Summary", fill=(25, 25, 25), font=font)
    summary_lines = [
        f"align reward mean: {_fmt(tracking.get('tracking_action_alignment_reward_mean'))}",
        f"align ceiling mean: {_fmt(tracking.get('tracking_action_alignment_reward_ceiling_mean'))}",
        f"align utilization mean: {_fmt(tracking.get('tracking_action_alignment_utilization_mean'))}",
        f"align error mean: {_fmt(tracking.get('tracking_action_alignment_error_mean'))}",
        f"reference close/up mean: {_fmt(tracking.get('tracking_reference_action_close_mean'))} / {_fmt(tracking.get('tracking_reference_action_up_mean'))}",
        f"target unsafe max: {_fmt(tracking.get('tracking_unsafe_target_rate_max'))}",
        f"target clearance min: {_fmt(tracking.get('tracking_target_table_clearance_min'))}",
    ]
    for line_idx, line in enumerate(summary_lines):
        draw.text((margin_l, y + 34 + 24 * line_idx), line, fill=(45, 45, 45), font=font_s)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _draw_no_video(output_path: Path, reason: str) -> None:
    image = Image.new("RGB", (1280, 720), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    try:
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        font = font_b = None
    draw.text((60, 70), "No Video Captured For This Smoke", fill=(20, 20, 20), font=font_b)
    wrapped = [
        reason,
        "The metrics/log bundle is still inspectable, but this run does not satisfy the updated visual artifact contract.",
        "A follow-up video-bearing bounded smoke/eval should be used before PPO scale-up.",
    ]
    y = 150
    for line in wrapped:
        draw.text((60, y), line, fill=(45, 45, 45), font=font)
        y += 46
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _discover_local_videos(metrics_path: Path) -> list[Path]:
    video_dir = metrics_path.parent / "videos"
    if not video_dir.exists():
        return []
    return sorted(video_dir.glob("*.mp4"))


def _video_metadata(video_path: Path) -> dict[str, object]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,nb_frames,r_frame_rate,duration",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams") or []
        return streams[0] if streams else {}
    except Exception as exc:
        return {"error": str(exc)}


def _draw_video_contact_sheet(video_path: Path, output_path: Path, run_name: str | None) -> dict[str, object]:
    metadata = _video_metadata(video_path)
    try:
        duration = float(metadata.get("duration", 0.0) or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    sample_times = [0.10, duration * 0.50 if duration > 0.0 else 1.0, max(duration - 0.10, 0.10)]
    labels = ["first usable", "middle", "last"]

    with tempfile.TemporaryDirectory() as tmpdir:
        frame_paths = []
        for idx, timestamp in enumerate(sample_times):
            frame_path = Path(tmpdir) / f"frame_{idx}.jpg"
            cmd = [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(frame_path),
            ]
            subprocess.run(cmd, check=False)
            if frame_path.exists():
                frame_paths.append(frame_path)
        frames = [Image.open(path).convert("RGB") for path in frame_paths]
        if not frames:
            _draw_no_video(output_path, f"Could not extract frames from {video_path}")
            return metadata

        thumb_w = 420
        thumb_h = int(frames[0].height * thumb_w / max(frames[0].width, 1))
        sheet_h = thumb_h + 120
        image = Image.new("RGB", (thumb_w * len(frames), sheet_h), "white")
        draw = ImageDraw.Draw(image)
        try:
            font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            font = ImageFont.truetype("DejaVuSans.ttf", 16)
        except Exception:
            font = font_b = None
        title = run_name or video_path.stem
        draw.text((18, 16), title, fill=(20, 20, 20), font=font_b)
        for idx, frame in enumerate(frames):
            thumb = frame.resize((thumb_w, thumb_h))
            x = idx * thumb_w
            y = 70
            image.paste(thumb, (x, y))
            label = labels[idx] if idx < len(labels) else f"sample {idx}"
            draw.text((x + 12, y + thumb_h + 12), f"{label} @ {sample_times[idx]:.2f}s", fill=(35, 35, 35), font=font)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text())
    log_text = args.log.read_text(errors="replace")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = _parse_trace(log_text)
    _write_trace(rows, output_dir / "validation_trace.csv", output_dir / "validation_trace.jsonl")

    config = _parse_config(log_text)
    tracking = metrics.get("rollout", {}).get("tracking", {})
    if not isinstance(tracking, dict):
        tracking = {}
    _draw_plot(rows, tracking, output_dir / "validation_trace_plot.png")
    video_files = _discover_local_videos(args.metrics)
    video_metadata = _video_metadata(video_files[0]) if video_files else {}
    contact_sheet_path = output_dir / "video_contact_sheet.png"
    if video_files:
        video_metadata = _draw_video_contact_sheet(video_files[0], contact_sheet_path, args.run_name or config.get("RUN_NAME"))
    else:
        contact_sheet_path = output_dir / "no_video_contact_sheet.png"
        _draw_no_video(
            contact_sheet_path,
            "No local MP4 was found next to metrics.json. Fetch the validation videos directory or relaunch with CAPTURE_VIDEO=True.",
        )

    summary = {
        "job_id": args.job_id,
        "commit": args.commit,
        "run_name": args.run_name or config.get("RUN_NAME"),
        "passed": bool(metrics.get("passed", False)),
        "task": metrics.get("task"),
        "steps_completed": metrics.get("rollout", {}).get("steps_completed"),
        "done_count": metrics.get("rollout", {}).get("done_count"),
        "early_done_count": metrics.get("rollout", {}).get("early_done_count"),
        "reward_mean": metrics.get("rollout", {}).get("reward_mean"),
        "reward_final": metrics.get("rollout", {}).get("reward_final"),
        "final_success_rate": metrics.get("rollout", {}).get("final_success_rate"),
        "max_mean_lift": metrics.get("rollout", {}).get("max_mean_lift"),
        "final_gripper_width": metrics.get("rollout", {}).get("final_gripper_width"),
        "tracking": tracking,
        "reference": metrics.get("tracking_reference"),
        "config": config,
        "trace_points": len(rows),
        "video_enabled": metrics.get("video_enabled"),
        "video_folder": metrics.get("video_folder"),
        "video_files": [str(path) for path in video_files],
        "video_metadata": video_metadata,
        "contact_sheet": str(contact_sheet_path),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (output_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")

    reference = metrics.get("tracking_reference", {})
    if not isinstance(reference, dict):
        reference = {}
    report = f"""# Franka Cube Validation Smoke Artifact

- job id: `{args.job_id}`
- run name: `{summary['run_name']}`
- commit: `{args.commit}`
- task: `{metrics.get('task')}`
- passed: `{metrics.get('passed')}`
- steps: `{summary['steps_completed']}`
- reward mean/final: {_fmt(summary['reward_mean'])} / {_fmt(summary['reward_final'])}
- done/early done: `{summary['done_count']}` / `{summary['early_done_count']}`
- success final: {_fmt(summary['final_success_rate'])}
- max mean lift: {_fmt(summary['max_mean_lift'])} m
- final gripper width: {_fmt(summary['final_gripper_width'])} m
- target unsafe max: {_fmt(tracking.get('tracking_unsafe_target_rate_max'))}
- target clearance min: {_fmt(tracking.get('tracking_target_table_clearance_min'))} m
- reference caveat: curobo_validated={reference.get('curobo_validated')}, source_tag={reference.get('source_tag')}
- visual artifact: `{video_files[0] if video_files else 'n/a'}`; contact sheet `{contact_sheet_path}`.
- video metadata: `{video_metadata}`

## Action Alignment

- alignment reward mean: {_fmt(tracking.get('tracking_action_alignment_reward_mean'))}
- alignment ceiling mean: {_fmt(tracking.get('tracking_action_alignment_reward_ceiling_mean'))}
- alignment utilization mean: {_fmt(tracking.get('tracking_action_alignment_utilization_mean'))}
- alignment error mean: {_fmt(tracking.get('tracking_action_alignment_error_mean'))}
- teacher-force alpha/active mean: {_fmt(tracking.get('tracking_teacher_force_alpha_mean'))} / {_fmt(tracking.get('tracking_teacher_force_active_mean'))}
- raw-policy/ref L2 mean: {_fmt(tracking.get('tracking_raw_policy_reference_action_error_l2_mean'))}
- applied/ref L2 mean: {_fmt(tracking.get('tracking_applied_reference_action_error_l2_mean'))}
- applied/policy L2 mean: {_fmt(tracking.get('tracking_applied_policy_action_error_l2_mean'))}
- raw policy close/up mean: {_fmt(tracking.get('tracking_raw_policy_action_close_mean'))} / {_fmt(tracking.get('tracking_raw_policy_action_up_mean'))}
- applied close/up mean: {_fmt(tracking.get('tracking_applied_action_close_mean'))} / {_fmt(tracking.get('tracking_applied_action_up_mean'))}
- policy close/up mean: {_fmt(tracking.get('tracking_action_close_mean'))} / {_fmt(tracking.get('tracking_action_up_mean'))}
- reference close/up mean: {_fmt(tracking.get('tracking_reference_action_close_mean'))} / {_fmt(tracking.get('tracking_reference_action_up_mean'))}

## Files

- metrics: `{args.metrics}`
- stdout log: `{args.log}`
- trace csv: `{output_dir / 'validation_trace.csv'}`
- trace jsonl: `{output_dir / 'validation_trace.jsonl'}`
- plot: `{output_dir / 'validation_trace_plot.png'}`
- contact sheet: `{contact_sheet_path}`
- videos: `{[str(path) for path in video_files]}`
- summary json: `{output_dir / 'summary.json'}`
- config json: `{output_dir / 'config.json'}`
"""
    (output_dir / "report.md").write_text(report)
    print(output_dir)
    print(output_dir / "report.md")
    print(output_dir / "validation_trace_plot.png")


if __name__ == "__main__":
    main()
