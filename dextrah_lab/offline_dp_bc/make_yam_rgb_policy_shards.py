"""Build sharded YAM RGB pick-place policy datasets from replay NPZs.

The replay datasets contain validation/debug fields, including privileged object
state and phase labels.  This converter writes per-trajectory shards containing
only the policy inputs requested for sim2real training:

- scene_rgb and wrist_rgb uint8 images
- robot_state proprioception
- 7D relative EE + gripper actions
- episode_ends
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from .action_conversion import DextrahActionConvention, derive_relative_ee_actions
except ImportError:  # pragma: no cover - supports direct script execution.
    from action_conversion import DextrahActionConvention, derive_relative_ee_actions


YAM_ACTION_CONVENTION = DextrahActionConvention(
    position_scale=(0.055, 0.055, 0.045),
    rotation_scale=(0.22, 0.22, 0.25),
    world_to_action_quat_wxyz=(1.0, 0.0, 0.0, 0.0),
    max_gripper_width=0.17,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _source_rows(paths: list[Path], accepted_jsonl: list[Path]) -> list[dict[str, Any]]:
    rows = [{"dataset": str(path)} for path in paths]
    for jsonl in accepted_jsonl:
        for row in _read_jsonl(jsonl):
            if row.get("final_rgb_dataset"):
                row["dataset"] = row["final_rgb_dataset"]
            if row.get("dataset"):
                rows.append(row)
    if not rows:
        raise ValueError("No source datasets were provided")
    return rows


def _squeeze_env(arr: np.ndarray, *, key: str) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim >= 2 and arr.shape[1] == 1:
        return arr[:, 0]
    if arr.ndim >= 3 and arr.shape[0] > 0:
        raise ValueError(f"{key} must have a singleton env dimension or no env dimension, got {arr.shape}")
    return arr


def _frame_row_indices(step_idx: np.ndarray, rgb_step_idx: np.ndarray) -> np.ndarray:
    step_idx = np.asarray(step_idx, dtype=np.int64).reshape(-1)
    rgb_step_idx = np.asarray(rgb_step_idx, dtype=np.int64).reshape(-1)
    by_step = {int(step): idx for idx, step in enumerate(step_idx.tolist())}
    missing = [int(step) for step in rgb_step_idx.tolist() if int(step) not in by_step]
    if missing:
        raise ValueError(f"RGB step ids missing from state rows: {missing[:8]}")
    return np.asarray([by_step[int(step)] for step in rgb_step_idx.tolist()], dtype=np.int64)


def _rgb_array(data: np.lib.npyio.NpzFile, key: str, fallback: str | None = None) -> np.ndarray:
    actual = key if key in data.files else fallback
    if actual is None or actual not in data.files:
        raise KeyError(f"Replay dataset missing RGB key {key!r}")
    arr = np.asarray(data[actual], dtype=np.uint8)
    if arr.ndim != 4:
        raise ValueError(f"{actual} must be rank-4 RGB, got {arr.shape}")
    if arr.shape[-1] != 3:
        if arr.shape[1] == 3:
            arr = np.moveaxis(arr, 1, -1)
        else:
            raise ValueError(f"{actual} must be NHWC or NCHW RGB, got {arr.shape}")
    return arr


def _convert_one(row: dict[str, Any], output_dir: Path, index: int, *, compress: bool) -> dict[str, Any]:
    src = Path(str(row["dataset"])).expanduser()
    if not src.is_file():
        raise FileNotFoundError(src)
    with np.load(src, allow_pickle=False) as data:
        for key in ("step_idx", "rgb_step_idx", "robot_state", "tcp_pos", "tcp_quat", "gripper_width"):
            if key not in data.files:
                raise KeyError(f"{src} missing required key {key!r}")
        row_ids = _frame_row_indices(data["step_idx"], data["rgb_step_idx"])
        scene_rgb = _rgb_array(data, "scene_rgb", fallback="rgb")
        wrist_rgb = _rgb_array(data, "wrist_rgb")
        if scene_rgb.shape[0] != row_ids.shape[0] or wrist_rgb.shape[0] != row_ids.shape[0]:
            raise ValueError(
                f"{src}: RGB frame count mismatch: scene={scene_rgb.shape}, wrist={wrist_rgb.shape}, "
                f"rgb_step_idx={row_ids.shape}"
            )
        robot_state = _squeeze_env(np.asarray(data["robot_state"], dtype=np.float32), key="robot_state")[row_ids]
        tcp_pos = _squeeze_env(np.asarray(data["tcp_pos"], dtype=np.float32), key="tcp_pos")[row_ids]
        tcp_quat = _squeeze_env(np.asarray(data["tcp_quat"], dtype=np.float32), key="tcp_quat")[row_ids]
        gripper_width = _squeeze_env(np.asarray(data["gripper_width"], dtype=np.float32), key="gripper_width")[row_ids]
        gripper_width = gripper_width.reshape(-1)
        action = derive_relative_ee_actions(
            tcp_pos,
            tcp_quat,
            gripper_width=gripper_width,
            convention=YAM_ACTION_CONVENTION,
            terminal_action="repeat",
        )
        if robot_state.shape[0] != action.shape[0]:
            raise ValueError(f"{src}: robot/action length mismatch {robot_state.shape} vs {action.shape}")
        out = output_dir / f"yam_rgb_policy_{index:06d}.npz"
        metadata = {
            "source_dataset": str(src),
            "source_row": row,
            "policy_inputs": ["scene_rgb", "wrist_rgb", "robot_state"],
            "excluded_inputs": ["phase", "progress", "object_state", "bin_state", "target_state", "privileged_obs"],
            "action_convention": {
                "position_scale": list(YAM_ACTION_CONVENTION.position_scale),
                "rotation_scale": list(YAM_ACTION_CONVENTION.rotation_scale),
                "max_gripper_width": float(YAM_ACTION_CONVENTION.max_gripper_width),
            },
        }
        save_fn = np.savez_compressed if compress else np.savez
        save_fn(
            out,
            scene_rgb=scene_rgb,
            wrist_rgb=wrist_rgb,
            robot_state=robot_state.astype(np.float32, copy=False),
            action=action.astype(np.float32, copy=False),
            episode_ends=np.asarray([int(action.shape[0])], dtype=np.int64),
            metadata_json=np.asarray(json.dumps(metadata, indent=2, sort_keys=True)),
        )
    return {
        "path": str(out),
        "source_dataset": str(src),
        "num_steps": int(action.shape[0]),
        "scene_rgb_shape": list(scene_rgb.shape),
        "wrist_rgb_shape": list(wrist_rgb.shape),
        "robot_state_shape": list(robot_state.shape),
        "action_shape": list(action.shape),
        "compressed": bool(compress),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, action="append", default=[])
    parser.add_argument("--accepted_jsonl", type=Path, action="append", default=[])
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--no_compress",
        action="store_true",
        help="Write uncompressed NPZ shards. This is faster and often preferable on shared filesystems.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest.expanduser().resolve() if args.manifest else output_dir / "manifest.json"
    rows = _source_rows([p.expanduser() for p in args.dataset], [p.expanduser() for p in args.accepted_jsonl])

    shards = []
    compress = not bool(args.no_compress)
    for idx, row in enumerate(rows):
        shards.append(_convert_one(row, output_dir, idx, compress=compress))
    payload = {
        "format": "dextrah_yam_rgb_policy_sharded_v1",
        "num_shards": len(shards),
        "num_steps": int(sum(int(shard["num_steps"]) for shard in shards)),
        "image_keys": ["scene_rgb", "wrist_rgb"],
        "robot_state_key": "robot_state",
        "action_key": "action",
        "compressed": compress,
        "shards": shards,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "YAM_RGB_POLICY_SHARDS "
        + json.dumps(
            {
                "manifest": str(manifest_path),
                "num_shards": payload["num_shards"],
                "num_steps": payload["num_steps"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
