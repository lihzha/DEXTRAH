#!/usr/bin/env python3
"""Create a reachable tabletop Objaverse manifest pool for YAM demo collection."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def _as_float_list(value: Any, length: int) -> list[float] | None:
    if not isinstance(value, list) or len(value) != length:
        return None
    try:
        values = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in values):
        return None
    return values


def _bounds(record: dict[str, Any]) -> tuple[list[float], list[float]] | None:
    bounds_min = _as_float_list(record.get("scaled_bounds_min"), 3)
    bounds_max = _as_float_list(record.get("scaled_bounds_max"), 3)
    if bounds_min is not None and bounds_max is not None:
        return bounds_min, bounds_max
    half_extents = _as_float_list(record.get("scaled_half_extents"), 3)
    if half_extents is not None:
        return [-v for v in half_extents], half_extents
    scale = record.get("scale", 1.0)
    try:
        scale_f = float(scale)
    except (TypeError, ValueError):
        return None
    raw_min = _as_float_list(record.get("bounds_min"), 3)
    raw_max = _as_float_list(record.get("bounds_max"), 3)
    if raw_min is not None and raw_max is not None:
        return [scale_f * v for v in raw_min], [scale_f * v for v in raw_max]
    raw_half = _as_float_list(record.get("half_extents"), 3)
    if raw_half is not None:
        half = [scale_f * v for v in raw_half]
        return [-v for v in half], half
    return None


def _xy_radius(bounds_min: list[float], bounds_max: list[float]) -> float:
    return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))


def _height(bounds_min: list[float], bounds_max: list[float]) -> float:
    return bounds_max[2] - bounds_min[2]


def _metadata_text(record: dict[str, Any]) -> str:
    fragments: list[str] = []
    for key in ("name", "title", "category", "categories", "labels", "tags", "description", "metadata", "uuid"):
        value = record.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            fragments.extend(str(item) for item in value)
        elif isinstance(value, dict):
            fragments.extend(str(item) for item in value.values())
        else:
            fragments.append(str(value))
    return " ".join(fragments).lower()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_manifest", type=Path, required=True)
    parser.add_argument("--output_manifest", type=Path, required=True)
    parser.add_argument("--max_assets", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--min_xy_radius", type=float, default=0.012)
    parser.add_argument("--max_xy_radius", type=float, default=0.075)
    parser.add_argument("--min_height", type=float, default=0.010)
    parser.add_argument("--max_height", type=float, default=0.160)
    parser.add_argument("--max_grasp_width_p95", type=float, default=0.145)
    parser.add_argument("--prefer_keywords", type=str, default="")
    parser.add_argument("--exclude_keywords", type=str, default="animal,building,car,chair,person,plant,room,statue,tree,vehicle")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    records = payload.get("objects")
    if not isinstance(records, list) or not records:
        raise ValueError(f"Expected non-empty objects list in {args.source_manifest}")
    source_asset_root = Path(str(payload.get("asset_root") or ".")).expanduser()
    if not source_asset_root.is_absolute():
        source_asset_root = (args.source_manifest.parent / source_asset_root).resolve()
    prefer_keywords = tuple(item.strip().lower() for item in args.prefer_keywords.split(",") if item.strip())
    exclude_keywords = tuple(item.strip().lower() for item in args.exclude_keywords.split(",") if item.strip())

    accepted: list[tuple[float, dict[str, Any]]] = []
    skipped: dict[str, int] = {
        "invalid_bounds": 0,
        "too_small": 0,
        "too_large": 0,
        "too_short": 0,
        "too_tall": 0,
        "too_wide_grasp": 0,
        "excluded_keyword": 0,
    }
    for record in records:
        if not isinstance(record, dict):
            continue
        bounds = _bounds(record)
        if bounds is None:
            skipped["invalid_bounds"] += 1
            continue
        bounds_min, bounds_max = bounds
        radius = _xy_radius(bounds_min, bounds_max)
        height = _height(bounds_min, bounds_max)
        if radius < float(args.min_xy_radius):
            skipped["too_small"] += 1
            continue
        if radius > float(args.max_xy_radius):
            skipped["too_large"] += 1
            continue
        if height < float(args.min_height):
            skipped["too_short"] += 1
            continue
        if height > float(args.max_height):
            skipped["too_tall"] += 1
            continue
        prior = record.get("grasp_prior") if isinstance(record.get("grasp_prior"), dict) else {}
        width_p95 = prior.get("grasp_width_p95")
        if width_p95 is not None:
            try:
                if float(width_p95) > float(args.max_grasp_width_p95):
                    skipped["too_wide_grasp"] += 1
                    continue
            except (TypeError, ValueError):
                pass
        text = _metadata_text(record)
        if any(keyword in text for keyword in exclude_keywords):
            skipped["excluded_keyword"] += 1
            continue
        prefer_hits = sum(1 for keyword in prefer_keywords if keyword in text)
        size_score = -abs(radius - 0.045) - 0.4 * abs(height - 0.060)
        score = 10.0 * prefer_hits + size_score
        normalized = dict(record)
        normalized["yam_collection_filter"] = {
            "xy_radius": radius,
            "height": height,
            "score": score,
        }
        accepted.append((score, normalized))

    rng = random.Random(int(args.seed))
    rng.shuffle(accepted)
    accepted.sort(key=lambda item: item[0], reverse=True)
    max_assets = int(args.max_assets)
    selected = [record for _, record in (accepted if max_assets <= 0 else accepted[:max_assets])]
    if not selected:
        raise ValueError(f"No records remain after filtering {args.source_manifest}; skipped={skipped}")

    output = dict(payload)
    output["format"] = "dextrah_yam_objaverse_collection_pool_v1"
    output["asset_root"] = str(source_asset_root)
    output["source_manifest_path"] = str(args.source_manifest)
    output["selected_uuid_count"] = len(selected)
    output["objects"] = selected
    output["yam_collection_filter"] = {
        "source_count": len(records),
        "selected_count": len(selected),
        "skipped": skipped,
        "seed": int(args.seed),
        "min_xy_radius": float(args.min_xy_radius),
        "max_xy_radius": float(args.max_xy_radius),
        "min_height": float(args.min_height),
        "max_height": float(args.max_height),
        "max_grasp_width_p95": float(args.max_grasp_width_p95),
        "prefer_keywords": list(prefer_keywords),
        "exclude_keywords": list(exclude_keywords),
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "event": "yam_objaverse_pool_manifest_written",
                "source_manifest": str(args.source_manifest),
                "output_manifest": str(args.output_manifest),
                "selected_count": len(selected),
                "skipped": skipped,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
