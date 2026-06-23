"""Compose two rendered videos into one side-by-side MP4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=Path, nargs="+", required=True)
    parser.add_argument("--right", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--left_label", type=str, default="default scene camera")
    parser.add_argument("--right_label", type=str, default="top-down camera")
    parser.add_argument("--fps", type=float, default=0.0)
    parser.add_argument("--label_height", type=int, default=32)
    return parser.parse_args()


def _to_rgb(frame: np.ndarray) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    if arr.shape[-1] == 4:
        arr = arr[:, :, :3]
    return np.asarray(arr, dtype=np.uint8)


def _pad_to(frame: np.ndarray, height: int, width: int) -> np.ndarray:
    out = np.zeros((height, width, 3), dtype=np.uint8)
    h = min(height, frame.shape[0])
    w = min(width, frame.shape[1])
    out[:h, :w] = frame[:h, :w]
    return out


def _resize_to_height(frame: np.ndarray, height: int) -> np.ndarray:
    if int(frame.shape[0]) == int(height):
        return frame
    width = max(1, int(round(float(frame.shape[1]) * float(height) / float(frame.shape[0]))))
    try:
        from PIL import Image

        image = Image.fromarray(frame)
        return np.asarray(image.resize((width, int(height)), Image.Resampling.BILINEAR), dtype=np.uint8)
    except Exception:
        y_idx = np.linspace(0, frame.shape[0] - 1, int(height)).round().astype(np.int64)
        x_idx = np.linspace(0, frame.shape[1] - 1, width).round().astype(np.int64)
        return frame[y_idx][:, x_idx]


def _label_bar(width: int, height: int, left_label: str, right_label: str, split_x: int) -> np.ndarray:
    bar = np.zeros((height, width, 3), dtype=np.uint8)
    bar[:] = (18, 20, 22)
    try:
        from PIL import Image, ImageDraw, ImageFont

        image = Image.fromarray(bar)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 18)
        except Exception:
            font = ImageFont.load_default()
        draw.text((12, max((height - 18) // 2, 2)), left_label, fill=(236, 238, 240), font=font)
        draw.text((split_x + 12, max((height - 18) // 2, 2)), right_label, fill=(236, 238, 240), font=font)
        return np.asarray(image, dtype=np.uint8)
    except Exception:
        return bar


def main() -> None:
    args = _parse_args()
    if len(args.left) != len(args.right):
        raise ValueError(f"Expected equal numbers of left/right videos, got {len(args.left)} and {len(args.right)}")
    for path in [*args.left, *args.right]:
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    left_probe = imageio.get_reader(str(args.left[0]))
    left_meta = left_probe.get_meta_data()
    left_probe.close()
    fps = float(args.fps) if float(args.fps) > 0.0 else float(left_meta.get("fps") or 30.0)
    writer = imageio.get_writer(str(args.output), fps=fps, codec="libx264", quality=8)
    frame_count = 0
    try:
        for left_path, right_path in zip(args.left, args.right, strict=True):
            left_reader = imageio.get_reader(str(left_path))
            right_reader = imageio.get_reader(str(right_path))
            try:
                for left_frame, right_frame in zip(left_reader, right_reader, strict=False):
                    left = _to_rgb(left_frame)
                    right = _to_rgb(right_frame)
                    height = max(left.shape[0], right.shape[0])
                    left = _resize_to_height(left, height)
                    right = _resize_to_height(right, height)
                    left_width = left.shape[1]
                    combined = np.concatenate([left, right], axis=1)
                    label_height = max(int(args.label_height), 0)
                    if label_height > 0:
                        labels = _label_bar(
                            combined.shape[1],
                            label_height,
                            str(args.left_label),
                            str(args.right_label),
                            left_width,
                        )
                        combined = np.concatenate([labels, combined], axis=0)
                    writer.append_data(combined)
                    frame_count += 1
            finally:
                left_reader.close()
                right_reader.close()
    finally:
        writer.close()
    print(
        json.dumps(
            {
            "event": "two_view_video_written",
            "output": str(args.output),
            "frame_count": frame_count,
            "fps": fps,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
