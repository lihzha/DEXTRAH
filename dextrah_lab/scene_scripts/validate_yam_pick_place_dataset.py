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


def _metadata_from_arrays(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    raw = arrays.get("metadata_json")
    if raw is None:
        return {}
    try:
        text = str(raw.item() if getattr(raw, "shape", ()) == () else raw.reshape(-1)[0])
    except Exception:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _object_sequence_checks(
    metadata: dict[str, Any],
    *,
    expected_objects: int,
    frame_count: int,
) -> dict[str, Any]:
    sequence = metadata.get("trajectory_object_sequence")
    if not isinstance(sequence, list):
        sequence = []
    uuids = [
        str(item.get("uuid") or "")
        for item in sequence
        if isinstance(item, dict) and str(item.get("uuid") or "")
    ]
    frame_ranges_valid = True
    for item in sequence:
        if not isinstance(item, dict):
            frame_ranges_valid = False
            continue
        try:
            start = int(item.get("start_frame"))
            end = int(item.get("end_frame"))
            end_exclusive = int(item.get("end_frame_exclusive", end + 1))
            count = int(item.get("frame_count", end_exclusive - start))
        except (TypeError, ValueError):
            frame_ranges_valid = False
            continue
        frame_ranges_valid = frame_ranges_valid and (
            0 <= start <= end < end_exclusive <= frame_count and count == end_exclusive - start
        )
    return {
        "sequence": sequence,
        "checks": {
            "object_sequence_present": bool(sequence),
            "object_sequence_count": len(sequence) == int(expected_objects),
            "object_sequence_frame_ranges": bool(frame_ranges_valid),
            "object_sequence_unique_uuids": len(uuids) == len(set(uuids)),
        },
    }


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


def _as_scalar_series(value: np.ndarray) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim == 0:
        return arr.reshape(1)
    if arr.ndim == 1:
        return arr
    return arr.reshape(arr.shape[0], -1)[:, 0]


def _decode_phase_array(value: np.ndarray) -> np.ndarray:
    phases = []
    for item in _as_scalar_series(value):
        if isinstance(item, bytes):
            phases.append(item.decode("utf-8", errors="replace"))
        elif isinstance(item, np.bytes_):
            phases.append(bytes(item).decode("utf-8", errors="replace"))
        else:
            phases.append(str(item))
    return np.asarray(phases, dtype="<U128")


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


def _goal_bin_validation_info(stable_scene: dict[str, Any], args: argparse.Namespace) -> dict[str, float]:
    bins = stable_scene.get("bins") if isinstance(stable_scene.get("bins"), dict) else {}
    goal = bins.get("goal") if isinstance(bins.get("goal"), dict) else {}
    if not goal:
        summary = stable_scene.get("tabletop_clutter_summary")
        summary = summary if isinstance(summary, dict) else {}
        legacy_goal = summary.get("goal_bin") if isinstance(summary.get("goal_bin"), dict) else {}
        goal = legacy_goal
    return {
        "center_x": float(goal.get("center_x", args.bin_center_x)),
        "center_y": float(goal.get("center_y", args.bin_center_y)),
        "inner_size_x": float(goal.get("inner_size_x", args.bin_inner_size_x)),
        "inner_size_y": float(goal.get("inner_size_y", args.bin_inner_size_y)),
        "source": "stable_scene" if goal else "args",
    }


def _object_metrics(
    object_id: str,
    pos: np.ndarray,
    stable_scene: dict[str, Any],
    args: argparse.Namespace,
    goal_bin: dict[str, float],
) -> dict[str, Any]:
    initial = np.asarray(pos[0], dtype=np.float64)
    final = np.asarray(pos[-1], dtype=np.float64)
    z_values = np.asarray(pos[:, 2], dtype=np.float64)
    radius = _object_radius_from_stable(stable_scene, object_id)
    inside = _inside_bin(
        final[:2],
        center_x=float(goal_bin["center_x"]),
        center_y=float(goal_bin["center_y"]),
        inner_size_x=float(goal_bin["inner_size_x"]),
        inner_size_y=float(goal_bin["inner_size_y"]),
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
        "goal_bin": dict(goal_bin),
        "passes_lift_delta": bool(lift_delta >= float(args.min_lift_delta)),
        "passes_final_z": bool(final[2] >= float(args.min_final_z)),
    }


def _scripted_transport_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    demo = metrics.get("single_yam_rejected_path_demo")
    if not isinstance(demo, dict):
        return {}
    transport = demo.get("scripted_target_transport")
    return transport if isinstance(transport, dict) else {}


def _contact_proxy_metrics(arrays: dict[str, np.ndarray], args: argparse.Namespace) -> dict[str, Any]:
    required = [
        "tcp_pos",
        "target_object_center_pos",
        "target_root_pos",
        "gripper_width",
        "command_joint_position",
        "phase",
    ]
    missing = [key for key in required if key not in arrays]
    base: dict[str, Any] = {
        "required_keys": required,
        "missing_keys": missing,
        "passes": False,
        "near_tcp_object": False,
        "gripper_close_commanded": False,
        "object_lifted_while_close_commanded": False,
    }
    if missing:
        return base

    try:
        tcp_pos = _as_pos(arrays["tcp_pos"]).astype(np.float64)
        target_center = _as_pos(arrays["target_object_center_pos"]).astype(np.float64)
        target_root = _as_pos(arrays["target_root_pos"]).astype(np.float64)
        gripper_width = _as_scalar_series(arrays["gripper_width"]).astype(np.float64)
        command = np.asarray(arrays["command_joint_position"], dtype=np.float64)
        if command.ndim == 3:
            command = command[:, 0, :]
        elif command.ndim != 2:
            raise ValueError(f"Expected command_joint_position to have 2 or 3 dimensions, got {command.shape}")
        actual = None
        if "actual_joint_position" in arrays:
            actual = np.asarray(arrays["actual_joint_position"], dtype=np.float64)
            if actual.ndim == 3:
                actual = actual[:, 0, :]
            elif actual.ndim != 2:
                actual = None
        phases = _decode_phase_array(arrays["phase"])
    except (TypeError, ValueError) as exc:
        base["error"] = str(exc)
        return base

    sample_count = min(
        tcp_pos.shape[0],
        target_center.shape[0],
        target_root.shape[0],
        gripper_width.shape[0],
        command.shape[0],
        phases.shape[0],
    )
    if actual is not None:
        sample_count = min(sample_count, actual.shape[0])
    if sample_count <= 0:
        base["sample_count"] = 0
        return base
    tcp_pos = tcp_pos[:sample_count]
    target_center = target_center[:sample_count]
    target_root = target_root[:sample_count]
    gripper_width = gripper_width[:sample_count]
    command = command[:sample_count]
    actual = None if actual is None else actual[:sample_count]
    phases = phases[:sample_count]

    near_grasp_phase_names = (
        "hold_at_grasp",
        "close_fingers",
        "hold_after_close",
        "lift_object",
        "hold_after_lift",
        "move_to_above_bin_scripted",
        "hold_above_bin",
    )
    close_command_phase_names = (
        "close_fingers",
        "hold_after_close",
        "lift_object",
        "hold_after_lift",
        "move_to_above_bin_scripted",
        "hold_above_bin",
    )
    near_mask = np.isin(phases, near_grasp_phase_names)
    close_command_mask = np.isin(phases, close_command_phase_names)
    if not bool(near_mask.any()):
        near_mask = np.ones(sample_count, dtype=bool)
    if not bool(close_command_mask.any()):
        close_command_mask = near_mask

    tcp_object_distance = np.linalg.norm(tcp_pos - target_center, axis=1)
    open_window = min(30, sample_count)
    open_width = float(np.nanmedian(gripper_width[:open_window])) if open_window else math.nan
    min_closed_width = float(np.nanmin(gripper_width[close_command_mask]))
    close_delta = float(open_width - min_closed_width)
    finger_command = command[:, -2:] if command.shape[1] >= 2 else command
    finger_command_mean = np.nanmean(finger_command, axis=1)
    open_command = float(np.nanmin(finger_command_mean[near_mask]))
    max_close_command = float(np.nanmax(finger_command_mean[close_command_mask]))
    command_close_delta = float(max_close_command - open_command)
    max_close_finger_error = None
    if actual is not None and actual.shape == command.shape and actual.shape[1] >= 2:
        finger_error = np.abs(actual[:, -2:] - command[:, -2:])
        max_close_finger_error = float(np.nanmax(finger_error[close_command_mask]))
    initial_z = float(target_root[0, 2])
    max_closed_lift_z = float(np.nanmax(target_root[close_command_mask, 2]))
    closed_lift_delta = float(max_closed_lift_z - initial_z)
    min_tcp_object_dist = float(np.nanmin(tcp_object_distance[near_mask]))
    min_tcp_object_dist_step = int(np.flatnonzero(near_mask)[int(np.nanargmin(tcp_object_distance[near_mask]))])

    near_tcp_object = min_tcp_object_dist <= float(args.max_contact_proxy_tcp_object_dist)
    gripper_close_commanded = command_close_delta >= float(args.min_contact_proxy_gripper_close_delta)
    object_lifted_while_close_commanded = closed_lift_delta >= float(args.min_contact_proxy_lift_delta)
    base.update(
        {
            "sample_count": int(sample_count),
            "near_grasp_phases": list(near_grasp_phase_names),
            "close_command_phases": list(close_command_phase_names),
            "min_tcp_object_dist": min_tcp_object_dist,
            "min_tcp_object_dist_step": min_tcp_object_dist_step,
            "max_contact_proxy_tcp_object_dist": float(args.max_contact_proxy_tcp_object_dist),
            "initial_target_z": initial_z,
            "max_close_command_target_z": max_closed_lift_z,
            "close_command_lift_delta": closed_lift_delta,
            "min_contact_proxy_lift_delta": float(args.min_contact_proxy_lift_delta),
            "open_gripper_width": open_width,
            "min_close_command_gripper_width": min_closed_width,
            "gripper_width_close_delta": close_delta,
            "open_finger_command": open_command,
            "max_close_finger_command": max_close_command,
            "finger_command_close_delta": command_close_delta,
            "max_close_finger_tracking_error": max_close_finger_error,
            "min_contact_proxy_gripper_close_delta": float(args.min_contact_proxy_gripper_close_delta),
            "near_tcp_object": bool(near_tcp_object),
            "gripper_close_commanded": bool(gripper_close_commanded),
            "object_lifted_while_close_commanded": bool(object_lifted_while_close_commanded),
            "passes": bool(near_tcp_object and gripper_close_commanded and object_lifted_while_close_commanded),
        }
    )
    return base


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
    parser.add_argument("--max_joint_error_abs", type=float, default=0.25)
    parser.add_argument("--max_joint_error_l2", type=float, default=0.35)
    parser.add_argument("--min_rgb_std", type=float, default=2.0)
    parser.add_argument("--bin_center_x", type=float, default=-0.27)
    parser.add_argument("--bin_center_y", type=float, default=0.42)
    parser.add_argument("--bin_inner_size_x", type=float, default=0.36)
    parser.add_argument("--bin_inner_size_y", type=float, default=0.22)
    parser.add_argument("--bin_margin", type=float, default=-0.015)
    parser.add_argument("--require_contact_proxy", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow_extra_clutter_slots", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--allow_scripted_target_transport", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max_contact_proxy_tcp_object_dist", type=float, default=0.12)
    parser.add_argument("--min_contact_proxy_gripper_close_delta", type=float, default=0.03)
    parser.add_argument("--min_contact_proxy_lift_delta", type=float, default=0.035)
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
    metadata = _metadata_from_arrays(arrays)

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
    expected_objects = int(args.expected_objects) if args.expected_objects is not None else None
    clutter_slot_count = 0
    if "clutter_root_pos" in arrays:
        clutter_array = arrays["clutter_root_pos"]
        clutter_slot_count = int(clutter_array.shape[1]) if clutter_array.ndim >= 3 else 0
    goal_bin = _goal_bin_validation_info(stable_scene, args)
    object_results: list[dict[str, Any]] = []
    if not missing:
        object_results.append(_object_metrics("target", _as_pos(arrays["target_root_pos"]), stable_scene, args, goal_bin))
        if "clutter_root_pos" in arrays:
            clutter = arrays["clutter_root_pos"]
            clutter_count = int(clutter.shape[1]) if clutter.ndim >= 3 else 0
            stable_clutter = stable_scene.get("clutter") if isinstance(stable_scene.get("clutter"), list) else []
            if expected_objects is not None:
                clutter_limit = max(0, expected_objects - 1)
            elif stable_clutter:
                clutter_limit = len(stable_clutter)
            else:
                clutter_limit = clutter_count
            for slot_idx in range(min(clutter_count, clutter_limit)):
                object_results.append(
                    _object_metrics(
                        f"clutter_{slot_idx:02d}",
                        _clutter_pos(clutter, slot_idx),
                        stable_scene,
                        args,
                        goal_bin,
                    )
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
    scripted_transport = _scripted_transport_metrics(metrics)
    scripted_transport_enabled = bool(scripted_transport.get("enabled", False))
    contact_proxy = _contact_proxy_metrics(arrays, args)

    expected_objects = expected_objects if expected_objects is not None else len(object_results)
    expected_clutter_count = max(0, expected_objects - 1)
    state_steps = int(arrays["step_idx"].shape[0]) if "step_idx" in arrays else 0
    try:
        source_frame_count = int(metadata.get("trajectory_total_frames") or 0)
    except (TypeError, ValueError):
        source_frame_count = 0
    if source_frame_count <= 0:
        source_frame_count = state_steps
    sequence_summary = _object_sequence_checks(
        metadata,
        expected_objects=expected_objects,
        frame_count=source_frame_count,
    )
    checks = {
        "required_keys_present": not missing,
        "expected_object_count": len(object_results) == expected_objects,
        "clutter_slot_count_matches_expected": bool(
            args.allow_extra_clutter_slots or clutter_slot_count == expected_clutter_count
        ),
        **sequence_summary["checks"],
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
        "scripted_target_transport_disabled": bool(args.allow_scripted_target_transport or not scripted_transport_enabled),
        "contact_proxy": bool((not args.require_contact_proxy) or contact_proxy.get("passes", False)),
    }
    status = "accepted" if all(bool(value) for value in checks.values()) else "rejected"
    summary = {
        "status": status,
        "dataset_path": str(args.dataset_path),
        "metrics_path": None if args.metrics_path is None else str(args.metrics_path),
        "stable_scene_path": None if stable_scene_path is None else str(stable_scene_path),
        "checks": checks,
        "missing_keys": missing,
        "goal_bin": goal_bin,
        "objects": object_results,
        "dataset": {
            "keys": sorted(arrays.keys()),
            "state_steps": state_steps if state_steps > 0 else None,
            "rgb_shape": list(rgb.shape),
            "expected_clutter_count": expected_clutter_count,
            "clutter_slot_count": clutter_slot_count,
            "done_sum": int(done.sum()) if done.size else 0,
            "terminated_sum": int(terminated.sum()) if terminated.size else 0,
            "truncated_sum": int(truncated.sum()) if truncated.size else 0,
        },
        "metadata": {
            "present": bool(metadata),
            "task": metadata.get("task"),
            "trajectory_path": metadata.get("trajectory_path"),
            "trajectory_total_frames": metadata.get("trajectory_total_frames"),
            "trajectory_object_count": metadata.get("trajectory_object_count"),
            "trajectory_object_sequence": sequence_summary["sequence"],
            "trajectory_segments": metadata.get("trajectory_segments"),
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
        "scripted_target_transport": scripted_transport,
        "contact_proxy": contact_proxy,
        "robot_debug_site_visibility": metrics.get("robot_debug_site_visibility"),
    }
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"event": "yam_dataset_validation", "status": status, "output_path": str(args.output_path)}))
    raise SystemExit(0 if status == "accepted" else 1)


if __name__ == "__main__":
    main()
