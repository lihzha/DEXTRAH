#!/usr/bin/env python3
"""Plan a sequential YAM pick-and-drop trajectory for every object in a stable scene."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _localize_container_path(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith("/code/"):
        return str(_repo_root() / value[len("/code/") :])
    return value


def _localize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    localized = copy.deepcopy(asset)
    for key in ("raw_object_path", "source_raw_object_path", "mesh_path", "usd_path"):
        if key in localized:
            localized[key] = _localize_container_path(localized[key])
    return localized


def _matrix_from_pose_wxyz(pos: list[float], quat_wxyz: list[float]) -> list[list[float]]:
    import math

    w, x, y, z = [float(v) for v in quat_wxyz]
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm <= 0.0:
        w, x, y, z = 1.0, 0.0, 0.0, 0.0
    else:
        w, x, y, z = w / norm, x / norm, y / norm, z / norm
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return [
        [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy), float(pos[0])],
        [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx), float(pos[1])],
        [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy), float(pos[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _target_to_object(target: dict[str, Any]) -> dict[str, Any]:
    asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
    pos = [float(v) for v in target["root_position"]]
    quat = [float(v) for v in target["root_quat_wxyz"]]
    return {
        "object_id": "target",
        "source": "target",
        "slot_idx": None,
        "asset": _localize_asset(asset),
        "root_position": pos,
        "root_quat_wxyz": quat,
        "root_transform": copy.deepcopy(target.get("root_transform") or _matrix_from_pose_wxyz(pos, quat)),
        "mesh_copy": copy.deepcopy(target.get("mesh_copy") or {}),
    }


def _clutter_to_object(entry: dict[str, Any]) -> dict[str, Any]:
    asset = entry.get("asset") if isinstance(entry.get("asset"), dict) else {}
    pos = [float(v) for v in entry["root_position"]]
    quat = [float(v) for v in entry["root_quat_wxyz"]]
    slot_idx = int(entry.get("slot_idx", 0))
    return {
        "object_id": f"clutter_{slot_idx:02d}",
        "source": "clutter",
        "slot_idx": slot_idx,
        "asset": _localize_asset(asset),
        "root_position": pos,
        "root_quat_wxyz": quat,
        "root_transform": copy.deepcopy(entry.get("root_transform") or _matrix_from_pose_wxyz(pos, quat)),
    }


def _stable_scene_objects(stable_scene: dict[str, Any]) -> list[dict[str, Any]]:
    target = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else None
    if target is None:
        raise ValueError("stable_scene is missing target")
    objects = [_target_to_object(target)]
    clutter = stable_scene.get("clutter") if isinstance(stable_scene.get("clutter"), list) else []
    for entry in clutter:
        if isinstance(entry, dict):
            objects.append(_clutter_to_object(entry))
    return objects


def _object_as_target(obj: dict[str, Any]) -> dict[str, Any]:
    target = {
        "asset": copy.deepcopy(obj["asset"]),
        "root_position": copy.deepcopy(obj["root_position"]),
        "root_quat_wxyz": copy.deepcopy(obj["root_quat_wxyz"]),
        "root_transform": copy.deepcopy(obj["root_transform"]),
    }
    if obj.get("mesh_copy"):
        target["mesh_copy"] = copy.deepcopy(obj["mesh_copy"])
    return target


def _object_as_clutter(obj: dict[str, Any], slot_idx: int) -> dict[str, Any]:
    return {
        "slot_idx": int(slot_idx),
        "asset": copy.deepcopy(obj["asset"]),
        "root_position": copy.deepcopy(obj["root_position"]),
        "root_quat_wxyz": copy.deepcopy(obj["root_quat_wxyz"]),
        "root_transform": copy.deepcopy(obj["root_transform"]),
        "source_object_id": str(obj["object_id"]),
    }


def _set_robot_start(scene: dict[str, Any], joint_position: list[float]) -> None:
    robot = scene.setdefault("robot", {})
    joint = [float(v) for v in joint_position]
    robot["joint_position"] = [joint]
    robot["joint_velocity"] = [[0.0 for _ in joint]]
    robot["arm_joint_position"] = [joint[:6]]
    robot["finger_joint_position"] = [joint[6:]]


def _planning_scene_for_object(
    base_scene: dict[str, Any],
    objects: list[dict[str, Any]],
    selected_idx: int,
    *,
    start_joint_position: list[float] | None,
    completed_indices: set[int] | None = None,
) -> dict[str, Any]:
    scene = copy.deepcopy(base_scene)
    selected = objects[selected_idx]
    completed = set(completed_indices or set())
    obstacles = [obj for idx, obj in enumerate(objects) if idx != selected_idx and idx not in completed]
    scene["target"] = _object_as_target(selected)
    scene["clutter"] = [_object_as_clutter(obj, slot_idx) for slot_idx, obj in enumerate(obstacles)]
    snapshots = scene.setdefault("snapshots", {})
    stable = snapshots.setdefault("stable", {})
    stable["target_root_pos"] = [copy.deepcopy(selected["root_position"])]
    stable["target_root_quat"] = [copy.deepcopy(selected["root_quat_wxyz"])]
    stable["clutter_root_pos_by_slot"] = [[copy.deepcopy(obj["root_position"])] for obj in obstacles]
    stable["clutter_root_quat_by_slot"] = [[copy.deepcopy(obj["root_quat_wxyz"])] for obj in obstacles]
    if start_joint_position is not None:
        _set_robot_start(scene, start_joint_position)
    scene["planner_selected_object"] = {
        "object_id": selected["object_id"],
        "source": selected["source"],
        "slot_idx": selected["slot_idx"],
        "completed_object_ids": [str(objects[idx]["object_id"]) for idx in sorted(completed)],
        "obstacle_object_ids": [obj["object_id"] for obj in obstacles],
    }
    return scene


def _parse_order(order: str | None, objects: list[dict[str, Any]], max_objects: int | None) -> list[int]:
    if not order:
        indices = list(range(len(objects)))
    else:
        by_id = {str(obj["object_id"]): idx for idx, obj in enumerate(objects)}
        by_id["target"] = 0
        for idx, obj in enumerate(objects):
            if obj["source"] == "clutter":
                by_id[f"clutter:{obj['slot_idx']}"] = idx
                by_id[f"clutter_{int(obj['slot_idx']):02d}"] = idx
        indices = []
        for token in (part.strip() for part in order.split(",")):
            if not token:
                continue
            if token.isdigit():
                idx = int(token)
            elif token in by_id:
                idx = by_id[token]
            else:
                raise ValueError(f"Unknown object order token {token!r}; valid ids: {sorted(by_id)}")
            if idx < 0 or idx >= len(objects):
                raise ValueError(f"Object order index out of range: {idx}")
            indices.append(idx)
    if max_objects is not None:
        indices = indices[: int(max_objects)]
    return indices


def _trajectory_last_joint(path: Path) -> list[float]:
    payload = _load_json(path)
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"Trajectory has no frames: {path}")
    joint = frames[-1].get("joint_position") if isinstance(frames[-1], dict) else None
    if not isinstance(joint, list):
        raise ValueError(f"Last trajectory frame has no joint_position: {path}")
    return [float(v) for v in joint]


def _stable_start_joint(stable_scene: dict[str, Any]) -> list[float]:
    robot = stable_scene.get("robot") if isinstance(stable_scene.get("robot"), dict) else {}
    joint = robot.get("joint_position")
    if isinstance(joint, list) and joint:
        values = joint[0] if isinstance(joint[0], list) else joint
        if isinstance(values, list) and values:
            return [float(v) for v in values]
    arm = robot.get("arm_joint_position")
    fingers = robot.get("finger_joint_position")
    if isinstance(arm, list) and arm and isinstance(fingers, list) and fingers:
        arm_values = arm[0] if isinstance(arm[0], list) else arm
        finger_values = fingers[0] if isinstance(fingers[0], list) else fingers
        if isinstance(arm_values, list) and isinstance(finger_values, list):
            return [float(v) for v in [*arm_values, *finger_values]]
    raise ValueError("Stable scene is missing robot start joint_position")


def _minimum_jerk(alpha: float) -> float:
    a = max(0.0, min(1.0, float(alpha)))
    return 10.0 * a**3 - 15.0 * a**4 + 6.0 * a**5


def _append_return_to_start(path: Path, target_joint: list[float], frame_count: int) -> None:
    if int(frame_count) <= 0:
        return
    payload = _load_json(path)
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"Trajectory has no frames: {path}")
    start_joint = frames[-1].get("joint_position") if isinstance(frames[-1], dict) else None
    if not isinstance(start_joint, list):
        raise ValueError(f"Last trajectory frame has no joint_position: {path}")
    start = [float(v) for v in start_joint]
    target = [float(v) for v in target_joint]
    if len(start) != len(target):
        raise ValueError(f"Return-to-start joint length mismatch: {len(start)} != {len(target)}")
    parts = copy.deepcopy(frames[-1].get("parts")) if isinstance(frames[-1], dict) else None
    segment_start = len(frames)
    for idx in range(1, int(frame_count) + 1):
        blend = _minimum_jerk(idx / float(frame_count))
        joint = [float(s + blend * (t - s)) for s, t in zip(start, target, strict=True)]
        frame = {"phase": "return_to_start_pose", "joint_position": joint}
        if parts is not None:
            frame["parts"] = copy.deepcopy(parts)
        frames.append(frame)
    segments = payload.setdefault("segments", [])
    if isinstance(segments, list):
        segments.append({"phase": "return_to_start_pose", "start": int(segment_start), "count": int(frame_count)})
    payload["total_frames"] = int(len(frames))
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")


def _placement_end_relative(payload: dict[str, Any], default: int) -> int:
    placement_end = int(default)
    segments = payload.get("segments")
    if not isinstance(segments, list):
        return placement_end
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        phase = str(segment.get("phase") or "")
        if phase == "return_to_start_pose":
            continue
        start = int(segment.get("start", 0))
        count = int(segment.get("count", 0))
        if count > 0:
            placement_end = max(placement_end, start + count - 1)
    return placement_end


def _combine_trajectories(
    trajectory_paths: list[Path],
    object_records: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    combined_frames: list[dict[str, Any]] = []
    combined_segments: list[dict[str, Any]] = []
    per_object: list[dict[str, Any]] = []
    first_payload: dict[str, Any] | None = None
    all_grasps: list[Any] = []
    selected_grasps: list[Any] = []

    for object_idx, (path, record) in enumerate(zip(trajectory_paths, object_records, strict=True)):
        payload = _load_json(path)
        if first_payload is None:
            first_payload = payload
        frames = payload.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"Trajectory has no frames: {path}")
        start = len(combined_frames)
        for frame in frames:
            frame_out = copy.deepcopy(frame)
            phase = str(frame_out.get("phase") or "unknown")
            frame_out["phase"] = f"{record['object_id']}/{phase}"
            frame_out["object_id"] = str(record["object_id"])
            frame_out["object_sequence_index"] = int(object_idx)
            combined_frames.append(frame_out)
        for segment in payload.get("segments") or []:
            if not isinstance(segment, dict):
                continue
            combined_segments.append(
                {
                    "phase": f"{record['object_id']}/{segment.get('phase', 'unknown')}",
                    "start": int(start + int(segment.get("start", 0))),
                    "count": int(segment.get("count", 0)),
                    "object_id": str(record["object_id"]),
                    "object_sequence_index": int(object_idx),
                }
            )
        annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
        raw_grasps = annotations.get("tool_grasps_world") or annotations.get("all_grasps")
        if isinstance(raw_grasps, list):
            all_grasps.extend(raw_grasps)
        target_grasp = annotations.get("target_tool_transform") or annotations.get("target_grasp_transform")
        if target_grasp is not None:
            selected_grasps.append(target_grasp)
        asset = record.get("asset") if isinstance(record.get("asset"), dict) else {}
        object_segments = [
            segment
            for segment in combined_segments
            if str(segment.get("object_id")) == str(record["object_id"])
            and int(segment.get("object_sequence_index", -1)) == int(object_idx)
        ]
        placement_end_relative = _placement_end_relative(payload, len(frames) - 1)
        per_object.append(
            {
                "object_id": str(record["object_id"]),
                "source": str(record["source"]),
                "slot_idx": record["slot_idx"],
                "uuid": str(asset.get("uuid") or ""),
                "name": str(asset.get("name") or asset.get("metadata_text") or asset.get("uuid") or record["object_id"]),
                "asset": {
                    "uuid": str(asset.get("uuid") or ""),
                    "name": str(asset.get("name") or ""),
                    "metadata_text": str(asset.get("metadata_text") or ""),
                    "usd_path": str(asset.get("usd_path") or ""),
                    "raw_object_path": str(asset.get("raw_object_path") or ""),
                    "grasp_prior_path": str(asset.get("grasp_prior_path") or ""),
                    "scale": asset.get("scale"),
                    "xy_radius": asset.get("xy_radius"),
                    "scaled_half_extents": copy.deepcopy(asset.get("scaled_half_extents")),
                },
                "trajectory_path": str(path),
                "start_frame": int(start),
                "end_frame": int(start + len(frames) - 1),
                "end_frame_exclusive": int(start + len(frames)),
                "frame_count": int(len(frames)),
                "pick_start_frame": int(start),
                "placement_end_frame": int(start + placement_end_relative),
                "segments": object_segments,
            }
        )

    if first_payload is None:
        raise ValueError("No trajectories to combine")
    combined = {
        "fps": int(first_payload.get("fps", 60)),
        "total_frames": int(len(combined_frames)),
        "base_dir": str(output_path.parent),
        "camera": copy.deepcopy(first_payload.get("camera") or {}),
        "static": copy.deepcopy(first_payload.get("static") or {}),
        "annotations": {
            "tool_grasps_world": all_grasps or selected_grasps,
            "target_tool_transform": selected_grasps[0] if selected_grasps else None,
            "selected_tool_transforms_by_object": selected_grasps,
        },
        "frames": combined_frames,
        "segments": combined_segments,
        "phase_source": "stitched_multi_object_dextrah_task_segments",
        "object_count": int(len(per_object)),
        "object_sequence": per_object,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_jsonable(combined), indent=2) + "\n", encoding="utf-8")
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable_scene_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--run_name", type=str, default=None)
    parser.add_argument("--planner_script", type=Path, default=Path(__file__).with_name("plan_yam_graspgenx_curobo.py"))
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--graspgenx_root", type=Path, default=None)
    parser.add_argument("--curobo_root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--object_order", type=str, default=None)
    parser.add_argument("--max_objects", type=int, default=None)
    parser.add_argument("--num_grasps", type=int, default=64)
    parser.add_argument("--topk", type=int, default=32)
    parser.add_argument("--max_plan_attempts", type=int, default=32)
    parser.add_argument("--move_to_bin_frames", type=int, default=360)
    parser.add_argument("--drop_height_above_bin", type=float, default=0.18)
    parser.add_argument("--scripted_bin_drop_y_offset", type=float, default=0.0)
    parser.add_argument("--scripted_bin_drop_y_offset_after_first", type=float, default=None)
    parser.add_argument("--scripted_place_mode", choices=("fallback", "always", "never"), default="fallback")
    parser.add_argument("--scripted_lift_mode", choices=("fallback", "always", "never"), default="always")
    parser.add_argument("--scripted_lift_height", type=float, default=0.14)
    parser.add_argument("--scripted_lift_frames", type=int, default=240)
    parser.add_argument("--start_guard_frames", type=int, default=60)
    parser.add_argument("--return_to_start_frames", type=int, default=240)
    parser.add_argument("--strict_object_order", action="store_true")
    parser.add_argument("--yam_grasp_filter_min_keep", type=int, default=None)
    parser.add_argument("--yam_allow_lift_filter_fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stable_scene = _load_json(args.stable_scene_path.expanduser().resolve())
    if stable_scene.get("format") != "dextrah_stable_scene_v1":
        raise ValueError(f"Expected dextrah_stable_scene_v1 payload in {args.stable_scene_path}")
    objects = _stable_scene_objects(stable_scene)
    order = _parse_order(args.object_order, objects, args.max_objects)
    if not order:
        raise ValueError("Object order is empty")

    current_joint: list[float] | None = None
    trajectory_paths: list[Path] = []
    object_records: list[dict[str, Any]] = []
    object_summaries: list[dict[str, Any]] = []
    completed_indices: set[int] = set()
    planning_failures: list[dict[str, Any]] = []
    start_joint = _stable_start_joint(stable_scene)
    env = os.environ.copy()

    remaining = list(order)
    sequence_idx = 0
    while remaining:
        candidates = [remaining[0]] if bool(args.strict_object_order) else list(remaining)
        step_failures: list[dict[str, Any]] = []
        planned = False
        for candidate_rank, object_idx in enumerate(candidates):
            obj = objects[object_idx]
            object_id = str(obj["object_id"])
            object_dir = output_dir / f"{sequence_idx:02d}_{candidate_rank:02d}_{object_id}"
            object_dir.mkdir(parents=True, exist_ok=True)
            planning_scene = _planning_scene_for_object(
                stable_scene,
                objects,
                object_idx,
                start_joint_position=current_joint,
                completed_indices=completed_indices,
            )
            planning_scene_path = object_dir / "planning_scene.json"
            planning_scene_path.write_text(json.dumps(_jsonable(planning_scene), indent=2) + "\n", encoding="utf-8")
            drop_y_offset = float(args.scripted_bin_drop_y_offset)
            if sequence_idx > 0 and args.scripted_bin_drop_y_offset_after_first is not None:
                drop_y_offset = float(args.scripted_bin_drop_y_offset_after_first)
            run_name = args.run_name or f"yam_multi_{sequence_idx:02d}_{candidate_rank:02d}_{object_id}"
            cmd = [
                str(args.python),
                str(args.planner_script.expanduser().resolve()),
                "--stable_scene_path",
                str(planning_scene_path),
                "--output_dir",
                str(object_dir),
                "--run_name",
                run_name,
                "--seed",
                str(int(args.seed) + sequence_idx * 100 + candidate_rank),
                "--num_grasps",
                str(int(args.num_grasps)),
                "--topk",
                str(int(args.topk)),
                "--max_plan_attempts",
                str(int(args.max_plan_attempts)),
                "--plan_task",
                "pick_and_drop_in_bin",
                "--scripted_place_fallback",
                "--move_to_bin_frames",
                str(int(args.move_to_bin_frames)),
                "--drop_height_above_bin",
                str(float(args.drop_height_above_bin)),
                "--scripted_lift_mode",
                str(args.scripted_lift_mode),
                "--scripted_lift_height",
                str(float(args.scripted_lift_height)),
                "--scripted_lift_frames",
                str(int(args.scripted_lift_frames)),
                "--scripted_bin_drop_y_offset",
                str(float(drop_y_offset)),
                "--scripted_place_mode",
                str(args.scripted_place_mode),
                "--start_guard_frames",
                str(int(args.start_guard_frames)),
            ]
            if args.yam_grasp_filter_min_keep is not None:
                cmd.extend(["--yam_grasp_filter_min_keep", str(int(args.yam_grasp_filter_min_keep))])
            if bool(args.yam_allow_lift_filter_fallback):
                cmd.append("--yam_allow_lift_filter_fallback")
            if args.graspgenx_root is not None:
                cmd.extend(["--graspgenx_root", str(args.graspgenx_root.expanduser().resolve())])
            if args.curobo_root is not None:
                cmd.extend(["--curobo_root", str(args.curobo_root.expanduser().resolve())])
            log_path = object_dir / "planner_stdout_stderr.log"
            print(
                json.dumps(
                    {
                        "event": "planning_object_start",
                        "object_id": object_id,
                        "sequence_idx": sequence_idx,
                        "candidate_rank": candidate_rank,
                        "remaining_object_ids": [str(objects[idx]["object_id"]) for idx in remaining],
                        "cmd": cmd,
                    }
                ),
                flush=True,
            )
            with log_path.open("w", encoding="utf-8") as log_file:
                result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, text=True, env=env, check=False)
            plan_dir = object_dir / run_name
            trajectory_path = plan_dir / "trajectory.json"
            plan_summary_path = plan_dir / "plan_summary.json"
            plan_summary = _load_json(plan_summary_path) if plan_summary_path.is_file() else {}
            failure_reason: str | None = None
            if result.returncode != 0:
                failure_reason = f"planner_returncode_{result.returncode}"
            elif not trajectory_path.is_file():
                failure_reason = "trajectory_missing"
            elif plan_summary.get("status") not in (None, "accepted"):
                failure_reason = f"planner_status_{plan_summary.get('status')}"
            if failure_reason is not None:
                failure = {
                    "object_id": object_id,
                    "source": obj["source"],
                    "slot_idx": obj["slot_idx"],
                    "sequence_idx": sequence_idx,
                    "candidate_rank": candidate_rank,
                    "reason": failure_reason,
                    "planning_scene_path": str(planning_scene_path),
                    "plan_dir": str(plan_dir),
                    "plan_summary_path": str(plan_summary_path),
                    "log_path": str(log_path),
                    "planner_status": plan_summary.get("planner_status"),
                    "num_grasps": plan_summary.get("num_grasps"),
                }
                step_failures.append(failure)
                planning_failures.append(failure)
                print(json.dumps({"event": "planning_object_rejected", **failure}), flush=True)
                continue

            if len(remaining) > 1:
                _append_return_to_start(trajectory_path, start_joint, int(args.return_to_start_frames))
                current_joint = list(start_joint)
            else:
                current_joint = _trajectory_last_joint(trajectory_path)
            trajectory_paths.append(trajectory_path)
            object_records.append(obj)
            completed_indices.add(object_idx)
            remaining.remove(object_idx)
            object_summaries.append(
                {
                    "object_id": object_id,
                    "source": obj["source"],
                    "slot_idx": obj["slot_idx"],
                    "sequence_idx": sequence_idx,
                    "candidate_rank": candidate_rank,
                    "planning_scene_path": str(planning_scene_path),
                    "plan_dir": str(plan_dir),
                    "trajectory_path": str(trajectory_path),
                    "plan_summary_path": str(plan_summary_path),
                    "selected_grasp_confidence": plan_summary.get("selected_grasp_confidence"),
                    "scripted_place": plan_summary.get("diagnostics", {}).get("scripted_place")
                    if isinstance(plan_summary.get("diagnostics"), dict)
                    else None,
                }
            )
            print(
                json.dumps(
                    {
                        "event": "planning_object_done",
                        "object_id": object_id,
                        "sequence_idx": sequence_idx,
                        "candidate_rank": candidate_rank,
                        "trajectory_path": str(trajectory_path),
                        "last_joint_position": current_joint,
                    }
                ),
                flush=True,
            )
            sequence_idx += 1
            planned = True
            break
        if not planned:
            failure_path = output_dir / "planning_failures.json"
            failure_path.write_text(json.dumps(_jsonable(planning_failures), indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(
                "No remaining object could be planned at sequence "
                f"{sequence_idx}; failures written to {failure_path}; step_failures={step_failures}"
            )

    combined_path = output_dir / "trajectory.json"
    combined = _combine_trajectories(trajectory_paths, object_records, combined_path)
    overlay_path = output_dir / "grasp_pose_overlay.json"
    overlay_path.write_text(
        json.dumps(
            {
                "status": "accepted",
                "tool_grasps_world": combined["annotations"].get("tool_grasps_world") or [],
                "selected_tool_world": combined["annotations"].get("target_tool_transform"),
                "selected_tool_transforms_by_object": combined["annotations"].get("selected_tool_transforms_by_object") or [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": "accepted",
        "stable_scene_path": str(args.stable_scene_path.expanduser().resolve()),
        "output_dir": str(output_dir),
        "trajectory_json": str(combined_path),
        "grasp_pose_overlay": str(overlay_path),
        "object_order": [objects[idx]["object_id"] for idx in order],
        "planned_object_order": [record["object_id"] for record in object_records],
        "objects": object_summaries,
        "planning_failures": planning_failures,
        "total_frames": int(combined["total_frames"]),
        "fps": int(combined["fps"]),
    }
    (output_dir / "multi_plan_summary.json").write_text(json.dumps(_jsonable(summary), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"event": "multi_plan_complete", **summary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
