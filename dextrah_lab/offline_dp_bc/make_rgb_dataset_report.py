"""Create validation, coverage, and visualization artifacts for RGB BC datasets."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    return value


def _episode_bounds(episode_ends: np.ndarray) -> list[tuple[int, int]]:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return [(int(start), int(end)) for start, end in zip(starts, episode_ends)]


def _validate(data: np.lib.npyio.NpzFile, *, expected_robot_state_dim: int) -> list[str]:
    errors: list[str] = []
    for key in ("image", "robot_state", "action", "episode_ends"):
        if key not in data.files:
            errors.append(f"missing key {key!r}")
    if errors:
        return errors
    image = np.asarray(data["image"])
    robot_state = np.asarray(data["robot_state"])
    action = np.asarray(data["action"])
    episode_ends = np.asarray(data["episode_ends"])
    if image.ndim != 4 or image.shape[-1] != 3:
        errors.append(f"image must be (N,H,W,3), got {image.shape}")
    if image.dtype != np.uint8:
        errors.append(f"image dtype must be uint8, got {image.dtype}")
    if robot_state.shape != (image.shape[0], int(expected_robot_state_dim)):
        errors.append(
            f"robot_state must be ({image.shape[0]},{expected_robot_state_dim}), got {robot_state.shape}"
        )
    if action.shape != (image.shape[0], 7):
        errors.append(f"action must be ({image.shape[0]},7), got {action.shape}")
    if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(image.shape[0]):
        errors.append("episode_ends must be 1D cumulative exclusive and end at image length")
    for key in ("rollout_ids", "rollout_reset_joint_blend_alpha", "rollout_reset_cube_pos_blend_alpha"):
        if key in data.files:
            values = np.asarray(data[key]).reshape(-1)
            if "episode_ends" in data.files and values.shape[0] != int(np.asarray(data["episode_ends"]).shape[0]):
                errors.append(f"{key} must have one row per episode, got {values.shape[0]}")
    if "rollout_applied_cube_pos" in data.files:
        cube_pos = np.asarray(data["rollout_applied_cube_pos"])
        if "episode_ends" in data.files and cube_pos.shape != (int(np.asarray(data["episode_ends"]).shape[0]), 3):
            errors.append(f"rollout_applied_cube_pos must be (episodes,3), got {cube_pos.shape}")
    return errors


def _nearest_neighbor_stats(xy: np.ndarray) -> dict[str, float | None]:
    if xy.shape[0] < 2:
        return {"min": None, "p10": None, "median": None, "mean": None}
    diff = xy[:, None, :] - xy[None, :, :]
    dist = np.linalg.norm(diff, axis=-1)
    np.fill_diagonal(dist, np.inf)
    nn = np.min(dist, axis=1)
    return {
        "min": float(np.min(nn)),
        "p10": float(np.percentile(nn, 10.0)),
        "median": float(np.median(nn)),
        "mean": float(np.mean(nn)),
    }


def _upscale(frame: np.ndarray, scale: int) -> np.ndarray:
    if scale <= 1:
        return frame
    return np.repeat(np.repeat(frame, int(scale), axis=0), int(scale), axis=1)


def _write_episode_video(
    *,
    image: np.ndarray,
    bounds: list[tuple[int, int]],
    episode_ids: list[int],
    output_path: Path,
    fps: int,
    scale: int,
) -> None:
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - depends on runtime image stack.
        raise RuntimeError("imageio is required for --video-output") from exc

    clips = [image[start:end] for start, end in (bounds[idx] for idx in episode_ids)]
    max_len = max(int(clip.shape[0]) for clip in clips)
    separator = np.full((image.shape[1] * scale, max(2, scale * 2), 3), 255, dtype=np.uint8)
    frames: list[np.ndarray] = []
    for t in range(max_len):
        panels = []
        for clip in clips:
            frame = clip[min(t, int(clip.shape[0]) - 1)]
            panels.append(_upscale(frame, scale))
        row = panels[0]
        for panel in panels[1:]:
            row = np.concatenate((row, separator, panel), axis=1)
        frames.append(row)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        imageio.mimsave(output_path, frames, fps=int(fps), macro_block_size=1)
        return
    except Exception:
        if shutil.which("ffmpeg") is None:
            raise
    with tempfile.TemporaryDirectory(prefix="rgb_dataset_video_") as tmpdir:
        frame_dir = Path(tmpdir)
        for idx, frame in enumerate(frames):
            imageio.imwrite(frame_dir / f"frame_{idx:06d}.png", frame)
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(int(fps)),
            "-i",
            str(frame_dir / "frame_%06d.png"),
            "-vf",
            "format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-robot-state-dim", type=int, default=8)
    parser.add_argument("--video-output", type=Path, default=None)
    parser.add_argument("--video-episodes", type=int, default=3)
    parser.add_argument("--video-seed", type=int, default=42)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--scale", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(dataset_path, allow_pickle=False)
    validation_errors = _validate(data, expected_robot_state_dim=int(args.expected_robot_state_dim))
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    image = np.asarray(data["image"], dtype=np.uint8)
    robot_state = np.asarray(data["robot_state"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    bounds = _episode_bounds(episode_ends)
    episode_lengths = np.asarray([end - start for start, end in bounds], dtype=np.int64)
    rollout_ids = (
        np.asarray(data["rollout_ids"]).astype(str).reshape(-1).tolist()
        if "rollout_ids" in data.files
        else [f"episode_{idx}" for idx in range(len(bounds))]
    )
    cube_pos = (
        np.asarray(data["rollout_applied_cube_pos"], dtype=np.float32)
        if "rollout_applied_cube_pos" in data.files
        else np.full((len(bounds), 3), np.nan, dtype=np.float32)
    )
    finite_cube = cube_pos[np.isfinite(cube_pos).all(axis=1)]
    cube_xy = finite_cube[:, :2] if finite_cube.size else np.zeros((0, 2), dtype=np.float32)
    unique_rollouts = len(set(rollout_ids))

    rng = np.random.default_rng(int(args.video_seed))
    video_episode_count = min(int(args.video_episodes), len(bounds))
    video_episode_ids = sorted(rng.choice(len(bounds), size=video_episode_count, replace=False).astype(int).tolist())
    video_path = args.video_output.expanduser().resolve() if args.video_output else output_dir / "rgb_dataset_three_episodes.mp4"
    _write_episode_video(
        image=image,
        bounds=bounds,
        episode_ids=video_episode_ids,
        output_path=video_path,
        fps=int(args.fps),
        scale=int(args.scale),
    )

    episode_rows: list[dict[str, Any]] = []
    for idx, (start, end) in enumerate(bounds):
        episode_rows.append(
            {
                "episode": idx,
                "rollout_id": rollout_ids[idx],
                "start": start,
                "end": end,
                "length": end - start,
                "cube_x": float(cube_pos[idx, 0]),
                "cube_y": float(cube_pos[idx, 1]),
                "cube_z": float(cube_pos[idx, 2]),
            }
        )
    episode_csv = output_dir / "rgb_dataset_episodes.csv"
    with episode_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(episode_rows[0].keys()))
        writer.writeheader()
        writer.writerows(episode_rows)

    summary = {
        "dataset": str(dataset_path),
        "npz_keys": sorted(data.files),
        "image_shape": list(image.shape),
        "robot_state_shape": list(robot_state.shape),
        "action_shape": list(action.shape),
        "episode_count": len(bounds),
        "transition_count": int(image.shape[0]),
        "episode_length_min": int(np.min(episode_lengths)),
        "episode_length_max": int(np.max(episode_lengths)),
        "episode_length_mean": float(np.mean(episode_lengths)),
        "rollout_id_count": len(rollout_ids),
        "unique_rollout_id_count": unique_rollouts,
        "duplicate_rollout_id_count": len(rollout_ids) - unique_rollouts,
        "image_min": int(np.min(image)),
        "image_max": int(np.max(image)),
        "robot_state_min": np.min(robot_state, axis=0).astype(float).tolist(),
        "robot_state_max": np.max(robot_state, axis=0).astype(float).tolist(),
        "action_min": np.min(action, axis=0).astype(float).tolist(),
        "action_max": np.max(action, axis=0).astype(float).tolist(),
        "cube_xy_min": cube_xy.min(axis=0).astype(float).tolist() if cube_xy.size else None,
        "cube_xy_max": cube_xy.max(axis=0).astype(float).tolist() if cube_xy.size else None,
        "cube_xy_unique_rounded_1mm": int(np.unique(np.round(cube_xy, 3), axis=0).shape[0]) if cube_xy.size else 0,
        "cube_xy_nearest_neighbor_m": _nearest_neighbor_stats(cube_xy),
        "video_episode_ids": video_episode_ids,
        "video": str(video_path),
        "episode_csv": str(episode_csv),
    }
    summary_json = output_dir / "rgb_dataset_summary.json"
    report_md = output_dir / "rgb_dataset_report.md"
    summary_json.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Franka Cube RGB Dataset Report",
                "",
                f"- dataset: `{dataset_path}`",
                f"- image/robot/action: `{tuple(image.shape)}` / `{tuple(robot_state.shape)}` / `{tuple(action.shape)}`",
                f"- episodes/transitions: `{len(bounds)}` / `{int(image.shape[0])}`",
                f"- duplicate rollout ids: `{summary['duplicate_rollout_id_count']}`",
                f"- cube XY min/max: `{summary['cube_xy_min']}` / `{summary['cube_xy_max']}`",
                f"- unique cube XY rounded to 1mm: `{summary['cube_xy_unique_rounded_1mm']}`",
                f"- cube XY nearest-neighbor meters: `{summary['cube_xy_nearest_neighbor_m']}`",
                f"- image min/max: `{summary['image_min']}` / `{summary['image_max']}`",
                f"- video: `{video_path}`",
                f"- episode CSV: `{episode_csv}`",
                f"- summary JSON: `{summary_json}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        "FRANKA_CUBE_RGB_DATASET_REPORT "
        + json.dumps({"report": str(report_md), "summary": str(summary_json), "video": str(video_path)}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
