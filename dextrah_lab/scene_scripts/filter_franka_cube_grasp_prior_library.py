#!/usr/bin/env python3
"""Filter a compact Franka cube GraspGenX reset-prior library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
    except Exception:
        np = None

    if isinstance(value, Path):
        return str(value)
    if np is not None and isinstance(value, np.ndarray):
        return value.tolist()
    if np is not None and isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _np_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _parse_indices(text: str) -> list[int]:
    indices: list[int] = []
    for item in text.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        indices.append(int(stripped, 0))
    if not indices:
        raise argparse.ArgumentTypeError("expected at least one comma-separated index")
    return indices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Input compact .npz grasp prior library.")
    parser.add_argument("--output", type=Path, required=True, help="Output compact .npz grasp prior library.")
    parser.add_argument(
        "--original_indices",
        type=_parse_indices,
        default=None,
        help="Comma-separated original GraspGenX indices to keep, e.g. 0,1,11,12.",
    )
    parser.add_argument(
        "--min_object_grasp_z",
        type=float,
        default=None,
        help="Keep grasps with object-local grasp z >= this value.",
    )
    parser.add_argument(
        "--max_object_grasp_z",
        type=float,
        default=None,
        help="Keep grasps with object-local grasp z <= this value.",
    )
    parser.add_argument("--filter_name", type=str, default="filtered_original_indices")
    parser.add_argument("--filter_criterion", type=str, default="manual original-index filter")
    parser.add_argument("--validation_source", type=str, default="")
    parser.add_argument("--fallback_original_index", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    import numpy as np

    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if source.suffix.lower() != ".npz":
        raise ValueError(f"Expected .npz source, got {source}")
    if not source.is_file():
        raise FileNotFoundError(source)

    with np.load(source, allow_pickle=False) as data:
        required = ("grasps_object", "confidence", "grasp_to_tool_transform", "metadata_json")
        missing = [key for key in required if key not in data.files]
        if missing:
            raise KeyError(f"Missing required compact-library keys in {source}: {missing}")

        grasps_object = np.asarray(data["grasps_object"], dtype=np.float32)
        confidence = np.asarray(data["confidence"], dtype=np.float32).reshape(-1)
        grasp_to_tool = np.asarray(data["grasp_to_tool_transform"], dtype=np.float32)
        metadata = json.loads(str(_np_scalar(data["metadata_json"])))
        cube_size_m = np.asarray(data["cube_size_m"], dtype=np.float32) if "cube_size_m" in data.files else None
        tool_frame = np.asarray(str(_np_scalar(data["tool_frame"]))) if "tool_frame" in data.files else None
        gripper_name = np.asarray(str(_np_scalar(data["gripper_name"]))) if "gripper_name" in data.files else None

    if grasps_object.ndim != 3 or tuple(grasps_object.shape[1:]) != (4, 4):
        raise ValueError(f"grasps_object must have shape (N, 4, 4), got {grasps_object.shape}")
    if confidence.shape[0] != grasps_object.shape[0]:
        raise ValueError(f"confidence length {confidence.shape[0]} does not match grasps {grasps_object.shape[0]}")

    source_original_indices = metadata.get("filter_original_indices")
    if source_original_indices is None:
        source_original_indices = list(range(grasps_object.shape[0]))
    source_original_indices = [int(index) for index in source_original_indices]
    if len(source_original_indices) != grasps_object.shape[0]:
        raise ValueError(
            "metadata filter_original_indices length must match grasps_object count, got "
            f"{len(source_original_indices)} vs {grasps_object.shape[0]}"
        )
    if len(set(source_original_indices)) != len(source_original_indices):
        raise ValueError(f"source original indices contain duplicates: {source_original_indices}")

    original_to_local = {original: local for local, original in enumerate(source_original_indices)}
    if args.original_indices is not None:
        requested = [int(index) for index in args.original_indices]
        if len(set(requested)) != len(requested):
            raise ValueError(f"requested original indices contain duplicates: {requested}")
        missing_requested = [index for index in requested if index not in original_to_local]
        if missing_requested:
            raise ValueError(
                f"Requested original indices not present in {source}: {missing_requested}; "
                f"available={source_original_indices}"
            )
        keep_local = [original_to_local[index] for index in requested]
    else:
        requested = list(source_original_indices)
        keep_local = list(range(grasps_object.shape[0]))

    object_grasp_z = grasps_object[:, 2, 3].astype(float)
    if args.min_object_grasp_z is not None:
        keep_local = [index for index in keep_local if object_grasp_z[index] >= float(args.min_object_grasp_z)]
    if args.max_object_grasp_z is not None:
        keep_local = [index for index in keep_local if object_grasp_z[index] <= float(args.max_object_grasp_z)]
    if args.original_indices is None and args.min_object_grasp_z is None and args.max_object_grasp_z is None:
        raise ValueError("Specify --original_indices and/or an object-grasp-z filter.")
    if not keep_local:
        raise ValueError(
            "Filter removed all grasps; "
            f"available original_indices={source_original_indices}, object_grasp_z={object_grasp_z.tolist()}"
        )
    requested = [source_original_indices[index] for index in keep_local]

    output_metadata = dict(metadata)
    output_metadata.update(
        {
            "filter_name": str(args.filter_name),
            "filter_criterion": str(args.filter_criterion),
            "filter_source_library": str(source),
            "filter_original_indices": requested,
            "filter_source_original_indices": source_original_indices,
            "filter_local_indices": keep_local,
            "num_grasps_filtered": int(len(keep_local)),
            "num_grasps_original": int(grasps_object.shape[0]),
        }
    )
    if args.min_object_grasp_z is not None or args.max_object_grasp_z is not None:
        output_metadata["filter_object_grasp_z_range_m"] = {
            "min": None if args.min_object_grasp_z is None else float(args.min_object_grasp_z),
            "max": None if args.max_object_grasp_z is None else float(args.max_object_grasp_z),
        }
        output_metadata["filter_source_object_grasp_z_m"] = [
            float(object_grasp_z[index]) for index in range(grasps_object.shape[0])
        ]
        output_metadata["filter_kept_object_grasp_z_m"] = [float(object_grasp_z[index]) for index in keep_local]
    if args.validation_source:
        output_metadata["filter_validation_source"] = str(args.validation_source)
    if args.fallback_original_index is not None:
        fallback = int(args.fallback_original_index)
        if fallback not in requested:
            raise ValueError(f"fallback_original_index={fallback} is not in requested indices {requested}")
        output_metadata["fallback_original_index"] = fallback

    output.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "grasps_object": grasps_object[keep_local],
        "confidence": confidence[keep_local],
        "grasp_to_tool_transform": grasp_to_tool,
        "metadata_json": np.asarray(json.dumps(_jsonable(output_metadata), sort_keys=True)),
    }
    if cube_size_m is not None:
        payload["cube_size_m"] = cube_size_m
    if tool_frame is not None:
        payload["tool_frame"] = tool_frame
    if gripper_name is not None:
        payload["gripper_name"] = gripper_name

    np.savez_compressed(output, **payload)
    summary = {
        "source": str(source),
        "output": str(output),
        "kept_original_indices": requested,
        "kept_local_indices": keep_local,
        "confidence": [float(confidence[index]) for index in keep_local],
        "metadata": output_metadata,
    }
    print("FRANKA_CUBE_GRASP_PRIOR_LIBRARY_FILTERED", json.dumps(_jsonable(summary), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
