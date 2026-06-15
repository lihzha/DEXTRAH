"""Render all RGB dataset episodes as a tiled grid video."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np


def _episode_bounds(episode_ends: np.ndarray) -> list[tuple[int, int]]:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return [(int(start), int(end)) for start, end in zip(starts, episode_ends)]


def _upscale(frame: np.ndarray, scale: int) -> np.ndarray:
    if scale <= 1:
        return frame
    return np.repeat(np.repeat(frame, int(scale), axis=0), int(scale), axis=1)


def _parse_episode_indices(value: str, episode_count: int) -> list[int]:
    text = str(value).strip()
    if not text or text.lower() == "all":
        return list(range(episode_count))
    indices = [int(part) for part in text.split(",") if part.strip()]
    for idx in indices:
        if idx < 0 or idx >= episode_count:
            raise ValueError(f"episode index {idx} outside [0, {episode_count})")
    return indices


def _tile_frame(
    clips: list[np.ndarray],
    *,
    frame_index: int,
    rows: int,
    cols: int,
    scale: int,
    gap: int,
    background: int,
) -> np.ndarray:
    h, w = clips[0].shape[1:3]
    cell_h = h * int(scale)
    cell_w = w * int(scale)
    out_h = rows * cell_h + max(0, rows - 1) * int(gap)
    out_w = cols * cell_w + max(0, cols - 1) * int(gap)
    canvas = np.full((out_h, out_w, 3), int(background), dtype=np.uint8)
    for ep_idx, clip in enumerate(clips):
        row = ep_idx // cols
        col = ep_idx % cols
        if row >= rows:
            break
        t = min(int(frame_index), int(clip.shape[0]) - 1)
        y0 = row * (cell_h + int(gap))
        x0 = col * (cell_w + int(gap))
        canvas[y0 : y0 + cell_h, x0 : x0 + cell_w] = _upscale(clip[t], int(scale))
    return canvas


def _write_video(frames: list[np.ndarray], output: Path, fps: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("imageio is required to write the grid video") from exc

    try:
        imageio.mimsave(output, frames, fps=int(fps), macro_block_size=1)
        return
    except Exception:
        if shutil.which("ffmpeg") is None:
            raise

    with tempfile.TemporaryDirectory(prefix="rgb_episode_grid_") as tmpdir:
        frame_dir = Path(tmpdir)
        for idx, frame in enumerate(frames):
            imageio.imwrite(frame_dir / f"frame_{idx:06d}.png", frame)
        subprocess.run(
            [
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
                str(output),
            ],
            check=True,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--episodes", default="all", help="Comma-separated episode indices, or 'all'.")
    parser.add_argument("--cols", type=int, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--gap", type=int, default=2)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--background", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with np.load(args.dataset, allow_pickle=True) as data:
        image = np.asarray(data["image"])
        episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
        if image.ndim != 4 or image.shape[-1] != 3 or image.dtype != np.uint8:
            raise ValueError(f"image must be uint8 (N,H,W,3), got {image.shape} {image.dtype}")
        if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(image.shape[0]):
            raise ValueError("episode_ends must be cumulative exclusive ends ending at image length")
        bounds = _episode_bounds(episode_ends)
        episode_indices = _parse_episode_indices(str(args.episodes), len(bounds))
        clips = [image[start:end] for start, end in (bounds[idx] for idx in episode_indices)]

    if not clips:
        raise ValueError("no episodes selected")
    cols = max(1, int(args.cols))
    rows = int(math.ceil(len(clips) / cols))
    stride = max(1, int(args.stride))
    max_len = max(int(clip.shape[0]) for clip in clips)
    frames = [
        _tile_frame(
            clips,
            frame_index=t,
            rows=rows,
            cols=cols,
            scale=int(args.scale),
            gap=int(args.gap),
            background=int(args.background),
        )
        for t in range(0, max_len, stride)
    ]
    _write_video(frames, args.output, int(args.fps))
    print(
        "FRANKA_CUBE_RGB_EPISODE_GRID "
        f"dataset={args.dataset} output={args.output} episodes={len(clips)} "
        f"frames={len(frames)} rows={rows} cols={cols}"
    )


if __name__ == "__main__":
    main()
