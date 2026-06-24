"""Convert accepted YAM pick-place trajectory datasets to RGB Diffusion Policy NPZ.

The YAM replay datasets are one NPZ per accepted trajectory. Each source NPZ
contains RGB observations plus replay-side controller telemetry. This converter
collates a JSONL manifest into the single NPZ layout consumed by the official
Diffusion Policy image dataset adapter:

- ``image``: uint8 RGB frames, optionally resized.
- ``robot_state``: non-privileged robot proprioception.
- ``action``: supervised action labels.
- ``episode_ends``: cumulative exclusive episode ends.

For the current YAM planner demos, the normal RL ``action`` field is zero
because replay directly drove joint targets. The default label is therefore the
recorded absolute ``command_joint_position``.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


ROBOT_STATE_SCHEMAS: dict[str, list[str]] = {
    "actual_joint_position": [f"actual_joint_{idx}" for idx in range(8)],
    "command_joint_position": [f"command_joint_{idx}" for idx in range(8)],
    "tcp_pose_width": [
        "tcp_pos_x",
        "tcp_pos_y",
        "tcp_pos_z",
        "tcp_quat_w",
        "tcp_quat_x",
        "tcp_quat_y",
        "tcp_quat_z",
        "gripper_width",
    ],
}

ACTION_SCHEMAS: dict[str, list[str]] = {
    "command_joint_position": [f"command_joint_{idx}" for idx in range(8)],
    "actual_joint_position": [f"actual_joint_{idx}" for idx in range(8)],
    "command_joint_delta": [f"command_joint_delta_{idx}" for idx in range(8)],
}


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


def _read_jsonl(path: Path, *, max_demos: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if max_demos is not None and len(rows) >= int(max_demos):
                break
    if not rows:
        raise ValueError(f"No manifest rows loaded from {path}")
    return rows


def _host_path(path: str | Path, *, results_root: Path, host_results_root: Path | None = None) -> Path:
    text = str(path)
    if text.startswith("/results/"):
        return results_root / text[len("/results/") :]
    if host_results_root is not None:
        host_text = str(host_results_root)
        if text == host_text:
            return results_root
        if text.startswith(host_text.rstrip("/") + "/"):
            return results_root / text[len(host_text.rstrip("/")) + 1 :]
    return Path(text)


def _npy_header_from_npz(npz_path: Path, key: str) -> dict[str, Any]:
    member_name = key if key.endswith(".npy") else f"{key}.npy"
    with zipfile.ZipFile(npz_path) as zf:
        with zf.open(member_name) as f:
            if f.read(6) != b"\x93NUMPY":
                raise ValueError(f"{npz_path}:{member_name} is not an NPY member")
            version = f.read(2)
            if version == b"\x01\x00":
                header_len = struct.unpack("<H", f.read(2))[0]
            else:
                header_len = struct.unpack("<I", f.read(4))[0]
            return ast.literal_eval(f.read(header_len).decode("latin1"))


def _source_length(row: dict[str, Any], *, results_root: Path, host_results_root: Path | None) -> int:
    meta_path = row.get("dataset_metadata")
    if meta_path:
        path = _host_path(meta_path, results_root=results_root, host_results_root=host_results_root)
        if path.is_file():
            meta = json.loads(path.read_text(encoding="utf-8"))
            if "demo_steps" in meta:
                return int(meta["demo_steps"])
    dataset = _host_path(row["dataset"], results_root=results_root, host_results_root=host_results_root)
    header = _npy_header_from_npz(dataset, "rgb")
    return int(header["shape"][0])


def _squeeze_env(array: np.ndarray, *, key: str, expected_last_dim: int | None = None) -> np.ndarray:
    arr = np.asarray(array)
    if arr.ndim >= 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    if expected_last_dim is not None and (arr.ndim != 2 or arr.shape[1] != expected_last_dim):
        raise ValueError(f"{key} expected shape (N,{expected_last_dim}), got {arr.shape}")
    return arr


def _resize_nearest_batch(rgb: np.ndarray, *, height: int, width: int) -> np.ndarray:
    if rgb.ndim != 4 or rgb.shape[-1] != 3:
        raise ValueError(f"rgb must be NHWC RGB, got {rgb.shape}")
    src_h = int(rgb.shape[1])
    src_w = int(rgb.shape[2])
    if src_h == int(height) and src_w == int(width):
        return rgb.astype(np.uint8, copy=False)
    y_idx = np.floor((np.arange(int(height), dtype=np.float64) + 0.5) * src_h / int(height)).astype(np.int64)
    x_idx = np.floor((np.arange(int(width), dtype=np.float64) + 0.5) * src_w / int(width)).astype(np.int64)
    y_idx = np.clip(y_idx, 0, src_h - 1)
    x_idx = np.clip(x_idx, 0, src_w - 1)
    return rgb[:, y_idx][:, :, x_idx, :].astype(np.uint8, copy=False)


def _coarse_phase_id(phase: str) -> int:
    leaf = str(phase).split("/")[-1]
    if leaf in {"go_to_pre_grasp_pose", "hold_at_pre_grasp", "go_from_pre_grasp_to_grasp_pose", "hold_at_grasp"}:
        return 0
    if leaf in {"close_fingers", "hold_after_close"}:
        return 1
    if leaf in {
        "lift_object",
        "hold_after_lift",
        "move_to_above_bin_scripted",
        "hold_above_bin",
        "open_fingers_to_drop",
        "hold_after_drop",
        "return_to_start_pose",
    }:
        return 2
    return -1


def _robot_state(data: np.lib.npyio.NpzFile, mode: str) -> np.ndarray:
    if mode in {"actual_joint_position", "command_joint_position"}:
        return _squeeze_env(data[mode], key=mode, expected_last_dim=8).astype(np.float32)
    if mode == "tcp_pose_width":
        tcp_pos = _squeeze_env(data["tcp_pos"], key="tcp_pos", expected_last_dim=3).astype(np.float32)
        tcp_quat = _squeeze_env(data["tcp_quat"], key="tcp_quat", expected_last_dim=4).astype(np.float32)
        width = np.asarray(data["gripper_width"], dtype=np.float32).reshape(-1, 1)
        return np.concatenate((tcp_pos, tcp_quat, width), axis=1).astype(np.float32)
    raise ValueError(f"Unsupported robot state mode {mode!r}")


def _action(data: np.lib.npyio.NpzFile, mode: str) -> np.ndarray:
    if mode in {"actual_joint_position", "command_joint_position"}:
        return _squeeze_env(data[mode], key=mode, expected_last_dim=8).astype(np.float32)
    if mode == "command_joint_delta":
        command = _squeeze_env(data["command_joint_position"], key="command_joint_position", expected_last_dim=8)
        current = _squeeze_env(data["actual_joint_position"], key="actual_joint_position", expected_last_dim=8)
        return (command - current).astype(np.float32)
    raise ValueError(f"Unsupported action mode {mode!r}")


def _stats(array: np.ndarray) -> dict[str, list[float]]:
    return {
        "min": np.nanmin(array, axis=0).astype(float).tolist(),
        "max": np.nanmax(array, axis=0).astype(float).tolist(),
        "mean": np.nanmean(array, axis=0).astype(float).tolist(),
        "std": np.nanstd(array, axis=0).astype(float).tolist(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--results-root", type=Path, default=Path("/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah"))
    parser.add_argument(
        "--host-results-root",
        type=Path,
        default=Path("/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah"),
        help="Host-side results prefix used in manifest paths; map it to --results-root.",
    )
    parser.add_argument("--max-demos", type=int, default=None)
    parser.add_argument("--image-height", type=int, default=96)
    parser.add_argument("--image-width", type=int, default=128)
    parser.add_argument(
        "--robot-state-mode",
        choices=tuple(ROBOT_STATE_SCHEMAS),
        default="actual_joint_position",
    )
    parser.add_argument("--action-mode", choices=tuple(ACTION_SCHEMAS), default="command_joint_position")
    parser.add_argument("--metadata-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = args.manifest.expanduser().resolve()
    output = args.output.expanduser().resolve()
    results_root = args.results_root.expanduser().resolve()
    host_results_root = args.host_results_root.expanduser().resolve() if args.host_results_root is not None else None
    rows = _read_jsonl(manifest, max_demos=args.max_demos)

    lengths = [_source_length(row, results_root=results_root, host_results_root=host_results_root) for row in rows]
    total = int(sum(lengths))
    if total <= 0:
        raise ValueError("No frames selected")
    image = np.empty((total, int(args.image_height), int(args.image_width), 3), dtype=np.uint8)
    robot_state = np.empty((total, 8), dtype=np.float32)
    action = np.empty((total, 8), dtype=np.float32)
    phase_ids = np.empty((total,), dtype=np.int32)
    source_step_idx = np.empty((total,), dtype=np.int64)
    source_frame_idx = np.empty((total,), dtype=np.int64)
    source_demo_index = np.empty((total,), dtype=np.int32)
    episode_ends = np.cumsum(np.asarray(lengths, dtype=np.int64))

    episode_metadata: list[dict[str, Any]] = []
    cursor = 0
    for demo_index, (row, expected_len) in enumerate(zip(rows, lengths)):
        dataset_path = _host_path(row["dataset"], results_root=results_root, host_results_root=host_results_root)
        with np.load(dataset_path, allow_pickle=False) as data:
            rgb = np.asarray(data["rgb"], dtype=np.uint8)
            n = int(rgb.shape[0])
            if n != int(expected_len):
                raise ValueError(f"{dataset_path}: expected {expected_len} frames from metadata, got {n}")
            end = cursor + n
            image[cursor:end] = _resize_nearest_batch(
                rgb,
                height=int(args.image_height),
                width=int(args.image_width),
            )
            robot = _robot_state(data, str(args.robot_state_mode))
            act = _action(data, str(args.action_mode))
            if robot.shape != (n, 8):
                raise ValueError(f"{dataset_path}: robot_state shape {robot.shape}, expected ({n},8)")
            if act.shape != (n, 8):
                raise ValueError(f"{dataset_path}: action shape {act.shape}, expected ({n},8)")
            if not np.isfinite(robot).all() or not np.isfinite(act).all():
                raise ValueError(f"{dataset_path}: non-finite robot/action values")
            robot_state[cursor:end] = robot
            action[cursor:end] = act
            phases = np.asarray(data["phase"]).astype(str).reshape(-1)
            if phases.shape[0] != n:
                raise ValueError(f"{dataset_path}: phase length {phases.shape[0]} != {n}")
            phase_ids[cursor:end] = np.asarray([_coarse_phase_id(v) for v in phases], dtype=np.int32)
            source_step_idx[cursor:end] = np.asarray(data["step_idx"], dtype=np.int64).reshape(-1)
            source_frame_idx[cursor:end] = np.asarray(data["source_frame_idx"], dtype=np.int64).reshape(-1)
            source_demo_index[cursor:end] = int(demo_index)
        episode_metadata.append(
            {
                "episode_index": int(demo_index),
                "seed": row.get("seed"),
                "objects_per_demo": row.get("objects_per_demo"),
                "dataset": str(dataset_path),
                "video": row.get("video"),
                "trajectory": row.get("trajectory"),
                "validation": row.get("validation"),
                "object_sequence": row.get("object_sequence", []),
                "start": int(cursor),
                "end": int(end),
                "length": int(n),
            }
        )
        cursor = end
        if (demo_index + 1) % 25 == 0 or demo_index + 1 == len(rows):
            print(
                json.dumps(
                    {
                        "event": "converted_progress",
                        "episodes": int(demo_index + 1),
                        "frames": int(cursor),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    if cursor != total:
        raise RuntimeError(f"Internal cursor mismatch: {cursor} != {total}")
    if np.allclose(action, 0.0):
        raise ValueError("Converted action labels are all zero; check action_mode")

    rollout_ids = np.asarray(
        [f"seed_{row.get('seed', idx)}_objects_{row.get('objects_per_demo', 'unknown')}" for idx, row in enumerate(rows)]
    )
    robot_state_names = np.asarray(ROBOT_STATE_SCHEMAS[str(args.robot_state_mode)])
    action_names = np.asarray(ACTION_SCHEMAS[str(args.action_mode)])
    metadata = {
        "source": "yam_pick_place_accepted_manifest_to_rgb_diffusion_policy_npz",
        "manifest": str(manifest),
        "output": str(output),
        "results_root": str(results_root),
        "host_results_root": None if host_results_root is None else str(host_results_root),
        "num_episodes": int(len(rows)),
        "num_steps": int(total),
        "image_shape": [int(v) for v in image.shape],
        "robot_state_shape": [int(v) for v in robot_state.shape],
        "action_shape": [int(v) for v in action.shape],
        "episode_length_min": int(min(lengths)),
        "episode_length_max": int(max(lengths)),
        "episode_length_mean": float(np.mean(lengths)),
        "robot_state_mode": str(args.robot_state_mode),
        "action_mode": str(args.action_mode),
        "robot_state_names": robot_state_names.astype(str).tolist(),
        "action_names": action_names.astype(str).tolist(),
        "phase_id_vocab": {
            "-1": "unknown",
            "0": "approach",
            "1": "grasp_close",
            "2": "lift_place_return",
        },
        "robot_state_stats": _stats(robot_state),
        "action_stats": _stats(action),
        "phase_counts": {
            str(int(k)): int(v)
            for k, v in zip(*np.unique(phase_ids, return_counts=True))
        },
        "episodes": episode_metadata,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        image=image,
        robot_state=robot_state,
        action=action,
        episode_ends=episode_ends,
        phase_ids=phase_ids,
        source_step_idx=source_step_idx,
        source_frame_idx=source_frame_idx,
        source_demo_index=source_demo_index,
        rollout_ids=rollout_ids,
        robot_state_names=robot_state_names,
        action_names=action_names,
        metadata_json=np.asarray(json.dumps(_to_builtin(metadata), indent=2, sort_keys=True)),
    )
    metadata_path = (
        args.metadata_output.expanduser().resolve()
        if args.metadata_output is not None
        else output.with_suffix(output.suffix + ".metadata.json")
    )
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(_to_builtin(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "YAM_RGB_DP_DATASET_CONVERTED "
        + json.dumps(
            {
                "output": str(output),
                "metadata": str(metadata_path),
                "num_episodes": int(len(rows)),
                "num_steps": int(total),
                "image_shape": [int(v) for v in image.shape],
                "robot_state_shape": [int(v) for v in robot_state.shape],
                "action_shape": [int(v) for v in action.shape],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
