"""Validate controller-native YAM RGB shards and build nested curricula."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import numpy as np


SOURCE_PATTERN = re.compile(r"source_(\d+)$")
REQUIRED_ARRAYS = ("scene_rgb", "wrist_rgb", "robot_state", "action", "episode_ends")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", default=(10, 50, 100, 500))
    parser.add_argument("--expected_count", type=int, default=500)
    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _source_index(shard: Path) -> int:
    for parent in shard.parents:
        match = SOURCE_PATTERN.fullmatch(parent.name)
        if match:
            return int(match.group(1))
    raise ValueError(f"Cannot infer source index from {shard}")


def _validate_shard(shard: Path) -> tuple[dict[str, Any] | None, str | None]:
    metadata_path = shard / "metadata.json"
    if not metadata_path.is_file():
        return None, "missing_metadata"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid_metadata:{exc}"
    recording = metadata.get("recording") if isinstance(metadata.get("recording"), dict) else {}
    gate = recording.get("replay_gate") if isinstance(recording.get("replay_gate"), dict) else {}
    if not bool(gate.get("enabled")) or not bool(gate.get("passed")):
        return None, "replay_gate_not_passed"
    episode_success = recording.get("episode_success")
    if not isinstance(episode_success, list) or not episode_success or not all(bool(v) for v in episode_success):
        return None, "recording_success_not_passed"
    if not bool(recording.get("dynamics_mode")):
        return None, "not_dynamics_mode"
    if not bool(recording.get("exact_reset")):
        return None, "not_exact_reset"
    if str(recording.get("rendering_mode") or "") != "quality":
        return None, "not_quality_rendering"
    site_visibility = recording.get("robot_debug_site_visibility")
    if not isinstance(site_visibility, dict) or int(site_visibility.get("hidden_count") or 0) < 2:
        return None, "robot_debug_sites_not_hidden"
    target_uuid = str(metadata.get("target_uuid") or "")
    if not target_uuid:
        return None, "missing_target_uuid"
    missing = [name for name in REQUIRED_ARRAYS if not (shard / f"{name}.npy").is_file()]
    if missing:
        return None, "missing_arrays:" + ",".join(missing)
    try:
        arrays = {
            name: np.load(shard / f"{name}.npy", mmap_mode="r", allow_pickle=False)
            for name in REQUIRED_ARRAYS
        }
        action = arrays["action"]
        robot_state = arrays["robot_state"]
        scene_rgb = arrays["scene_rgb"]
        wrist_rgb = arrays["wrist_rgb"]
        episode_ends = arrays["episode_ends"]
        row_count = int(action.shape[0])
        if action.ndim != 2 or action.shape[1] != 7 or row_count < 1:
            return None, f"invalid_action_shape:{action.shape}"
        if robot_state.shape != (row_count, 24):
            return None, f"invalid_robot_state_shape:{robot_state.shape}"
        for name, value in (("scene_rgb", scene_rgb), ("wrist_rgb", wrist_rgb)):
            if value.ndim != 4 or value.shape[0] != row_count or value.shape[-1] != 3:
                return None, f"invalid_{name}_shape:{value.shape}"
            sample_ids = sorted({0, row_count // 2, row_count - 1})
            for sample_id in sample_ids:
                frame = np.asarray(value[sample_id])
                if not np.isfinite(frame).all() or float(frame.mean()) <= 1.0:
                    return None, f"blank_or_invalid_{name}:{sample_id}"
        if episode_ends.ndim != 1 or int(episode_ends[-1]) != row_count:
            return None, f"invalid_episode_ends:{episode_ends.shape}"
        if not np.isfinite(action).all() or not np.isfinite(robot_state).all():
            return None, "nonfinite_lowdim_array"
    except (OSError, ValueError) as exc:
        return None, f"array_validation_failed:{exc}"
    return {
        "source_index": _source_index(shard),
        "path": shard.resolve(),
        "source_dataset": str(metadata.get("source_dataset") or ""),
        "source_policy_shard": str(metadata.get("source_policy_shard") or recording.get("source_policy_shard") or ""),
        "target_uuid": target_uuid,
        "num_steps": row_count,
        "scene_rgb_shape": list(scene_rgb.shape),
        "wrist_rgb_shape": list(wrist_rgb.shape),
        "robot_state_shape": list(robot_state.shape),
        "action_shape": list(action.shape),
        "compressed": False,
        "storage": "npy_dir",
    }, None


def _round_robin_groups(records: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["target_uuid"])].append(record)
    group_names = list(grouped)
    rng.shuffle(group_names)
    queues: list[deque[dict[str, Any]]] = []
    for name in group_names:
        rows = grouped[name]
        rng.shuffle(rows)
        queues.append(deque(rows))
    output: list[dict[str, Any]] = []
    while queues:
        next_queues = []
        for queue in queues:
            output.append(queue.popleft())
            if queue:
                next_queues.append(queue)
        queues = next_queues
    return output


def _object_disjoint_order(
    records: list[dict[str, Any]], val_ratio: float, seed: int
) -> tuple[list[dict[str, Any]], set[str]]:
    if not 0.0 < val_ratio < 1.0:
        raise ValueError("val_ratio must be strictly between zero and one")
    rng = random.Random(seed)
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[str(record["target_uuid"])] += 1
    object_ids = list(counts)
    if len(object_ids) < 2:
        raise ValueError("Object-disjoint validation requires at least two target UUIDs")
    rng.shuffle(object_ids)
    target_val_rows = max(1, round(len(records) * val_ratio))
    val_ids: set[str] = set()
    val_rows = 0
    for object_id in object_ids:
        candidate_rows = val_rows + counts[object_id]
        if not val_ids or abs(candidate_rows - target_val_rows) <= abs(val_rows - target_val_rows):
            val_ids.add(object_id)
            val_rows = candidate_rows
        if val_rows >= target_val_rows:
            break
    if len(val_ids) == len(object_ids):
        val_ids.remove(max(val_ids, key=lambda item: counts[item]))

    train = _round_robin_groups([r for r in records if r["target_uuid"] not in val_ids], rng)
    val = _round_robin_groups([r for r in records if r["target_uuid"] in val_ids], rng)
    train_queue = deque(train)
    val_queue = deque(val)
    ordered: list[dict[str, Any]] = []
    train_per_val = max(1, round((1.0 - val_ratio) / val_ratio))
    while train_queue or val_queue:
        for _ in range(train_per_val):
            if train_queue:
                ordered.append(train_queue.popleft())
        if val_queue:
            ordered.append(val_queue.popleft())
        if not train_queue:
            ordered.extend(val_queue)
            val_queue.clear()
        elif not val_queue:
            ordered.extend(train_queue)
            train_queue.clear()
    return ordered, val_ids


def _manifest_row(record: dict[str, Any], output_dir: Path, val_ids: set[str]) -> dict[str, Any]:
    row = {key: value for key, value in record.items() if key != "path"}
    row["path"] = os.path.relpath(record["path"], output_dir)
    row["split"] = "val" if str(record["target_uuid"]) in val_ids else "train"
    return row


def main() -> None:
    args = _parser().parse_args()
    records_root = args.records_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(records_root.glob("source_*/policy_dataset/yam_rgb_policy_*"))
    accepted = []
    rejected = []
    seen_sources: set[int] = set()
    for shard in candidates:
        record, reason = _validate_shard(shard)
        if record is None:
            rejected.append({"path": str(shard), "reason": reason})
            continue
        source_index = int(record["source_index"])
        if source_index in seen_sources:
            rejected.append({"path": str(shard), "reason": f"duplicate_source_index:{source_index}"})
            continue
        seen_sources.add(source_index)
        accepted.append(record)
    audit = {
        "records_root": str(records_root),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "rejected": rejected,
    }
    (output_dir / "validation_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if len(accepted) != int(args.expected_count):
        raise SystemExit(
            f"Expected {args.expected_count} replay-gated shards, found {len(accepted)}; "
            f"see {output_dir / 'validation_audit.json'}"
        )
    ordered, val_ids = _object_disjoint_order(accepted, float(args.val_ratio), int(args.seed))
    sizes = sorted(set(int(size) for size in args.sizes))
    if not sizes or sizes[0] < 1 or sizes[-1] > len(ordered):
        raise ValueError(f"Invalid curriculum sizes {sizes} for {len(ordered)} records")

    curriculum_rows = []
    for size in sizes:
        rows = [_manifest_row(record, output_dir, val_ids) for record in ordered[:size]]
        train_count = sum(row["split"] == "train" for row in rows)
        val_count = size - train_count
        if train_count < 1 or val_count < 1:
            raise ValueError(f"Curriculum size {size} lacks train or validation rows: {train_count}/{val_count}")
        manifest = {
            "format": "dextrah_yam_rgb_policy_sharded_v1",
            "label_semantics": "exact_clipped_pose_controller_commands",
            "recording_gate": "exact_reset_action_only_dynamics_replay",
            "num_shards": size,
            "num_steps": int(sum(int(row["num_steps"]) for row in rows)),
            "num_train_shards": train_count,
            "num_val_shards": val_count,
            "object_disjoint_split": True,
            "image_keys": ["scene_rgb", "wrist_rgb"],
            "robot_state_key": "robot_state",
            "action_key": "action",
            "gripper_label_source": "executed_controller_command",
            "compressed": False,
            "storage": "npy_dir",
            "shards": rows,
        }
        manifest_path = output_dir / f"manifest_{size:04d}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        curriculum_rows.append(
            {
                "size": size,
                "manifest": str(manifest_path),
                "num_steps": manifest["num_steps"],
                "num_train_shards": train_count,
                "num_val_shards": val_count,
                "train_source_policy_shards": [
                    row["source_policy_shard"] for row in rows if row["split"] == "train"
                ],
                "val_source_policy_shards": [
                    row["source_policy_shard"] for row in rows if row["split"] == "val"
                ],
            }
        )
    curriculum = {
        "format": "dextrah_yam_controller_native_curriculum_v1",
        "seed": int(args.seed),
        "val_ratio": float(args.val_ratio),
        "accepted_count": len(accepted),
        "val_target_uuids": sorted(val_ids),
        "stages": curriculum_rows,
    }
    curriculum_path = output_dir / "curriculum.json"
    curriculum_path.write_text(json.dumps(curriculum, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "curriculum": str(curriculum_path),
                "accepted_count": len(accepted),
                "sizes": sizes,
                "validation_object_count": len(val_ids),
                "finite": bool(math.isfinite(float(args.val_ratio))),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
