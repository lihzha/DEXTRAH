"""Create contact sheets and summary stats for YAM RGB policy datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", default=[], help="Path to a trajectory_dataset.npz file.")
    parser.add_argument(
        "--rgb-replay-jsonl",
        action="append",
        default=[],
        help="accepted_rgb_replays.jsonl file containing final_rgb_dataset paths.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-datasets", type=int, default=8)
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--thumb-size", type=int, default=192)
    parser.add_argument("--sheet-name", default="yam_rgb_scene_wrist_sheet.png")
    parser.add_argument("--report-name", default="yam_rgb_observation_report.json")
    return parser.parse_args()


def _load_datasets(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    for raw in args.dataset:
        paths.append(Path(raw).expanduser())
    for raw_jsonl in args.rgb_replay_jsonl:
        jsonl = Path(raw_jsonl).expanduser()
        if not jsonl.exists():
            raise FileNotFoundError(jsonl)
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            dataset = payload.get("final_rgb_dataset") or payload.get("dataset")
            if dataset:
                paths.append(Path(str(dataset)).expanduser())
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    if args.max_datasets > 0:
        unique = unique[: args.max_datasets]
    if not unique:
        raise ValueError("No datasets were provided.")
    return unique


def _as_rgb(array: np.ndarray) -> np.ndarray:
    if array.ndim != 4 or array.shape[-1] != 3:
        raise ValueError(f"Expected NHWC RGB array, got {array.shape}")
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    return array


def _metadata_from_npz(data: np.lib.npyio.NpzFile) -> dict[str, Any]:
    if "metadata_json" not in data.files:
        return {}
    raw = data["metadata_json"]
    try:
        text = str(raw.item() if raw.shape == () else raw.reshape(-1)[0])
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _frame_indices(count: int, requested: int) -> list[int]:
    if count <= 0:
        return []
    requested = max(int(requested), 1)
    return sorted({int(round(v)) for v in np.linspace(0, count - 1, num=min(requested, count))})


def _resize_rgb(frame: np.ndarray, thumb_size: int) -> Image.Image:
    image = Image.fromarray(frame, mode="RGB")
    image.thumbnail((thumb_size, thumb_size), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (thumb_size, thumb_size), (16, 16, 16))
    x = (thumb_size - image.width) // 2
    y = (thumb_size - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _stats(name: str, array: np.ndarray) -> dict[str, Any]:
    rgb = _as_rgb(array)
    flat = rgb.reshape(-1, 3).astype(np.float32)
    deltas = np.abs(np.diff(rgb.astype(np.int16), axis=0)).mean(axis=(1, 2, 3)) if rgb.shape[0] > 1 else np.asarray([])
    return {
        "name": name,
        "shape": list(rgb.shape),
        "dtype": str(rgb.dtype),
        "mean_rgb": [float(v) for v in flat.mean(axis=0)],
        "std_rgb": [float(v) for v in flat.std(axis=0)],
        "black_pixel_fraction": float(np.mean(np.all(rgb <= 3, axis=-1))),
        "white_pixel_fraction": float(np.mean(np.all(rgb >= 252, axis=-1))),
        "mean_abs_frame_delta": float(deltas.mean()) if deltas.size else 0.0,
        "p95_abs_frame_delta": float(np.percentile(deltas, 95)) if deltas.size else 0.0,
    }


def _draw_sheet(rows: list[dict[str, Any]], output_path: Path, *, frames: int, thumb_size: int) -> None:
    label_h = 34
    stream_label_w = 72
    row_gap = 12
    col_gap = 8
    cols = max(frames, 1)
    row_h = label_h + 2 * thumb_size + row_gap
    width = stream_label_w + cols * thumb_size + (cols - 1) * col_gap
    height = max(1, len(rows)) * row_h
    sheet = Image.new("RGB", (width, height), (245, 245, 242))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row_idx, row in enumerate(rows):
        y0 = row_idx * row_h
        title = f"{row_idx:02d} {row['path'].name} | n={row['frame_count']}"
        draw.text((4, y0 + 4), title[:140], fill=(20, 20, 20), font=font)
        draw.text((4, y0 + label_h + 4), "scene", fill=(20, 20, 20), font=font)
        draw.text((4, y0 + label_h + thumb_size + 4), "wrist", fill=(20, 20, 20), font=font)
        for col_idx, frame_idx in enumerate(row["indices"]):
            x = stream_label_w + col_idx * (thumb_size + col_gap)
            draw.text((x + 4, y0 + 4), str(frame_idx), fill=(50, 50, 50), font=font)
            sheet.paste(_resize_rgb(row["scene_rgb"][frame_idx], thumb_size), (x, y0 + label_h))
            sheet.paste(_resize_rgb(row["wrist_rgb"][frame_idx], thumb_size), (x, y0 + label_h + thumb_size))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "datasets": [],
        "sheet_path": str(output_dir / args.sheet_name),
    }
    for path in _load_datasets(args):
        if not path.exists():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=False) as data:
            scene_rgb = _as_rgb(data["scene_rgb"] if "scene_rgb" in data.files else data["rgb"])
            wrist_rgb = _as_rgb(data["wrist_rgb"])
            if scene_rgb.shape[0] != wrist_rgb.shape[0]:
                raise ValueError(f"{path}: scene/wrist frame count mismatch: {scene_rgb.shape} vs {wrist_rgb.shape}")
            indices = _frame_indices(scene_rgb.shape[0], args.frames)
            rows.append(
                {
                    "path": path,
                    "frame_count": int(scene_rgb.shape[0]),
                    "indices": indices,
                    "scene_rgb": scene_rgb,
                    "wrist_rgb": wrist_rgb,
                }
            )
            report["datasets"].append(
                {
                    "path": str(path),
                    "frame_count": int(scene_rgb.shape[0]),
                    "sampled_frame_indices": indices,
                    "metadata": _metadata_from_npz(data),
                    "scene_rgb": _stats("scene_rgb", scene_rgb),
                    "wrist_rgb": _stats("wrist_rgb", wrist_rgb),
                }
            )
    sheet_path = output_dir / args.sheet_name
    _draw_sheet(rows, sheet_path, frames=args.frames, thumb_size=args.thumb_size)
    report_path = output_dir / args.report_name
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sheet_path": str(sheet_path), "report_path": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
