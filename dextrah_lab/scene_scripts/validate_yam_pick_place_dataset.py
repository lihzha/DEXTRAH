#!/usr/bin/env python3
"""Validate a recorded YAM pick-all-into-bin trajectory dataset."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _finite_summary(array: np.ndarray) -> dict[str, Any]:
    finite = np.isfinite(array)
    if not bool(finite.all()):
        return {"finite": False, "nan_count": int(np.isnan(array).sum()), "inf_count": int(np.isinf(array).sum())}
    return {"finite": True, "nan_count": 0, "inf_count": 0}


def _as_pos(value: np.ndarray) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim == 3:
        return arr[:, 0, :]
    if arr.ndim == 2:
        return arr
    raise ValueError(f"Expected position array with 2 or 3 dims, got {arr.shape}")


def _clutter_pos(value: np.ndarray, slot_idx: int) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim == 4:
        return arr[:, slot_idx, 0, :]
    if arr.ndim == 3:
        return arr[:, slot_idx, :]
    raise ValueError(f"Expected clutter position array with 3 or 4 dims, got {arr.shape}")


def _object_radius_from_stable(stable_scene: dict[str, Any], object_id: str) -> float:
    if object_id == "target":
        source = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else {}
    else:
        slot_idx = int(object_id.rsplit("_", 1)[-1])
        clutter = stable_scene.get("clutter") if isinstance(stable_scene.get("clutter"), list) else []
        source = clutter[slot_idx] if slot_idx < len(clutter) and isinstance(clutter[slot_idx], dict) else {}
    asset = source.get("asset") if isinstance(source.get("asset"), dict) else {}
    radius = asset.get("xy_radius")
    if radius is not None:
        try:
            return float(radius)
        except (TypeError, ValueError):
            pass
    half_extents = asset.get("scaled_half_extents")
    if isinstance(half_extents, list) and len(half_extents) >= 2:
        return max(float(half_extents[0]), float(half_extents[1]))
    return 0.0


def _inside_bin(
    xy: np.ndarray,
    *,
    center_x: float,
    center_y: float,
    inner_size_x: float,
    inner_size_y: float,
    radius: float,
    margin: float,
) -> bool:
    half_x = 0.5 * inner_size_x - max(radius, 0.0) - margin
    half_y = 0.5 * inner_size_y - max(radius, 0.0) - margin
    # If a large object cannot fit by radius, fall back to center-in-bin. This
    # keeps validation useful for irregular Objaverse bounds while still using
    # the stricter check for ordinary tabletop objects.
    if half_x <= 0.0:
        half_x = 0.5 * inner_size_x - margin
    if half_y <= 0.0:
        half_y = 0.5 * inner_size_y - margin
    return abs(float(xy[0]) - center_x) <= half_x and abs(float(xy[1]) - center_y) <= half_y


def _object_metrics(
    object_id: str,
    pos: np.ndarray,
    stable_scene: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    initial = np.asarray(pos[0], dtype=np.float64)
    final = np.asarray(pos[-1], dtype=np.float64)
    z_values = np.asarray(pos[:, 2], dtype=np.float64)
    radius = _object_radius_from_stable(stable_scene, object_id)
    inside = _inside_bin(
        final[:2],
        center_x=float(args.bin_center_x),
        center_y=float(args.bin_center_y),
        inner_size_x=float(args.bin_inner_size_x),
        inner_size_y=float(args.bin_inner_size_y),
        radius=radius,
        margin=float(args.bin_margin),
    )
    lift_delta = float(np.nanmax(z_values) - initial[2])
    return {
        "object_id": object_id,
        "radius": float(radius),
        "initial_pos": initial.tolist(),
        "final_pos": final.tolist(),
        "max_z": float(np.nanmax(z_values)),
        "lift_delta": lift_delta,
        "inside_bin": bool(inside),
        "passes_lift_delta": bool(lift_delta >= float(args.min_lift_delta)),
        "passes_final_z": bool(final[2] >= float(args.min_final_z)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset_path", type=Path, required=True)
    parser.add_argument("--metrics_path", type=Path, default=None)
    parser.add_argument("--stable_scene_path", type=Path, default=None)
    parser.add_argument("--output_path", type=Path, required=True)
    parser.add_argument("--expected_objects", type=int, default=None)
    parser.add_argument("--min_lift_delta", type=float, default=0.06)
    parser.add_argument("--min_final_z", type=float, default=-0.005)
    parser.add_argument("--min_finger_table_clearance", type=float, default=0.015)
    parser.add_argument("--max_joint_error_abs", type=float, default=0.15)
    parser.add_argument("--max_joint_error_l2", type=float, default=0.35)
    parser.add_argument("--min_rgb_std", type=float, default=2.0)
    parser.add_argument("--bin_center_x", type=float, default=-0.27)
    parser.add_argument("--bin_center_y", type=float, default=0.42)
    parser.add_argument("--bin_inner_size_x", type=float, default=0.36)
    parser.add_argument("--bin_inner_size_y", type=float, default=0.22)
    parser.add_argument("--bin_margin", type=float, default=-0.015)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = _load_json(args.metrics_path)
    stable_scene_path = args.stable_scene_path
    if stable_scene_path is None:
        stable_scene_info = metrics.get("stable_scene") if isinstance(metrics.get("stable_scene"), dict) else {}
        stable_value = stable_scene_info.get("input_path") or stable_scene_info.get("path")
        if stable_value:
            stable_scene_path = Path(str(stable_value))
    stable_scene = _load_json(stable_scene_path) if stable_scene_path and stable_scene_path.is_file() else {}

    with np.load(args.dataset_path, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}

    required_keys = [
        "target_root_pos",
        "finger_table_clearance",
        "command_joint_position",
        "actual_joint_position",
        "rgb",
        "done",
        "terminated",
        "truncated",
    ]
    missing = [key for key in required_keys if key not in arrays]
    object_results: list[dict[str, Any]] = []
    if not missing:
        object_results.append(_object_metrics("target", _as_pos(arrays["target_root_pos"]), stable_scene, args))
        if "clutter_root_pos" in arrays:
            clutter = arrays["clutter_root_pos"]
            clutter_count = int(clutter.shape[1]) if clutter.ndim >= 3 else 0
            for slot_idx in range(clutter_count):
                object_results.append(
                    _object_metrics(f"clutter_{slot_idx:02d}", _clutter_pos(clutter, slot_idx), stable_scene, args)
                )

    command = np.asarray(arrays.get("command_joint_position", np.empty((0,))), dtype=np.float64)
    actual = np.asarray(arrays.get("actual_joint_position", np.empty((0,))), dtype=np.float64)
    joint_error = actual - command if command.shape == actual.shape and command.size else np.empty((0,))
    joint_error_abs = np.abs(joint_error) if joint_error.size else np.empty((0,))
    joint_error_l2 = np.linalg.norm(joint_error.reshape(joint_error.shape[0], -1), axis=1) if joint_error.size else np.empty((0,))
    finger_clearance = np.asarray(arrays.get("finger_table_clearance", np.empty((0,))), dtype=np.float64)
    rgb = np.asarray(arrays.get("rgb", np.empty((0,))), dtype=np.uint8)
    done = np.asarray(arrays.get("done", np.empty((0,))), dtype=bool)
    terminated = np.asarray(arrays.get("terminated", np.empty((0,))), dtype=bool)
    truncated = np.asarray(arrays.get("truncated", np.empty((0,))), dtype=bool)

    expected_objects = int(args.expected_objects) if args.expected_objects is not None else len(object_results)
    checks = {
        "required_keys_present": not missing,
        "expected_object_count": len(object_results) == expected_objects,
        "all_objects_inside_bin": bool(object_results) and all(bool(item["inside_bin"]) for item in object_results),
        "all_objects_lifted": bool(object_results) and all(bool(item["passes_lift_delta"]) for item in object_results),
        "all_final_z_valid": bool(object_results) and all(bool(item["passes_final_z"]) for item in object_results),
        "finger_table_clearance": bool(finger_clearance.size)
        and float(np.nanmin(finger_clearance)) >= float(args.min_finger_table_clearance),
        "joint_error_abs": bool(joint_error_abs.size)
        and float(np.nanmax(joint_error_abs)) <= float(args.max_joint_error_abs),
        "joint_error_l2": bool(joint_error_l2.size)
        and float(np.nanmax(joint_error_l2)) <= float(args.max_joint_error_l2),
        "rgb_present": rgb.ndim == 4 and rgb.shape[-1] == 3 and rgb.shape[0] > 0,
        "rgb_nonblank": bool(rgb.size) and float(np.std(rgb.astype(np.float32))) >= float(args.min_rgb_std),
        "done_once_or_more": bool(done.size) and int(done.sum()) >= 1 and bool(done[-1].all()),
        "terminated_once_or_more": bool(terminated.size) and int(terminated.sum()) >= 1 and bool(terminated[-1].all()),
        "not_truncated_final": bool(truncated.size) and not bool(truncated[-1].any()),
        "finite_command_joint_position": _finite_summary(command).get("finite", False),
        "finite_actual_joint_position": _finite_summary(actual).get("finite", False),
        "finite_finger_table_clearance": _finite_summary(finger_clearance).get("finite", False),
    }
    status = "accepted" if all(bool(value) for value in checks.values()) else "rejected"
    summary = {
        "status": status,
        "dataset_path": str(args.dataset_path),
        "metrics_path": None if args.metrics_path is None else str(args.metrics_path),
        "stable_scene_path": None if stable_scene_path is None else str(stable_scene_path),
        "checks": checks,
        "missing_keys": missing,
        "objects": object_results,
        "dataset": {
            "keys": sorted(arrays.keys()),
            "state_steps": int(arrays["step_idx"].shape[0]) if "step_idx" in arrays else None,
            "rgb_shape": list(rgb.shape),
            "done_sum": int(done.sum()) if done.size else 0,
            "terminated_sum": int(terminated.sum()) if terminated.size else 0,
            "truncated_sum": int(truncated.sum()) if truncated.size else 0,
        },
        "finger_table_clearance": {
            "min": None if not finger_clearance.size else float(np.nanmin(finger_clearance)),
            "mean": None if not finger_clearance.size else float(np.nanmean(finger_clearance)),
            "last100_min": None if finger_clearance.shape[0] < 100 else float(np.nanmin(finger_clearance[-100:])),
        },
        "joint_tracking": {
            "max_abs": None if not joint_error_abs.size else float(np.nanmax(joint_error_abs)),
            "mean_abs": None if not joint_error_abs.size else float(np.nanmean(joint_error_abs)),
            "max_l2": None if not joint_error_l2.size else float(np.nanmax(joint_error_l2)),
            "mean_l2": None if not joint_error_l2.size else float(np.nanmean(joint_error_l2)),
            "last100_max_abs": None if joint_error_abs.shape[0] < 100 else float(np.nanmax(joint_error_abs[-100:])),
        },
        "rgb": {
            "std": None if not rgb.size else float(np.std(rgb.astype(np.float32))),
            "mean": None if not rgb.size else float(np.mean(rgb.astype(np.float32))),
        },
        "robot_debug_site_visibility": metrics.get("robot_debug_site_visibility"),
    }
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"event": "yam_dataset_validation", "status": status, "output_path": str(args.output_path)}))
    raise SystemExit(0 if status == "accepted" else 1)


if __name__ == "__main__":
    main()
