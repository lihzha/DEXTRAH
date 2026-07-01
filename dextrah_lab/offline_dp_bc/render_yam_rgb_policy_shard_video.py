"""Render stored scene and wrist observations from a YAM policy shard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--gap", type=int, default=8)
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required")
    shard = args.shard.expanduser().resolve()
    output = args.output.expanduser().resolve()
    scene = np.load(shard / "scene_rgb.npy", mmap_mode="r", allow_pickle=False)
    wrist = np.load(shard / "wrist_rgb.npy", mmap_mode="r", allow_pickle=False)
    if scene.shape != wrist.shape or scene.ndim != 4 or scene.shape[-1] != 3:
        raise ValueError(f"Expected matching NHWC RGB arrays, got {scene.shape}/{wrist.shape}")
    stride = max(1, int(args.stride))
    gap = max(0, int(args.gap))
    height = int(scene.shape[1])
    width = 2 * int(scene.shape[2]) + gap
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(max(1, int(args.fps))),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    separator = np.full((height, gap, 3), 245, dtype=np.uint8)
    frame_count = 0
    try:
        for index in range(0, int(scene.shape[0]), stride):
            frame = np.concatenate((np.asarray(scene[index]), separator, np.asarray(wrist[index])), axis=1)
            process.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
            frame_count += 1
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with status {return_code}")
    print(
        json.dumps(
            {
                "shard": str(shard),
                "output": str(output),
                "source_frames": int(scene.shape[0]),
                "video_frames": frame_count,
                "fps": max(1, int(args.fps)),
                "layout": "scene_rgb_left_wrist_rgb_right",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
