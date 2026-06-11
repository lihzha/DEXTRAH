#!/usr/bin/env python3
"""Export a compact GraspGenX object-local grasp library for the Franka cube task."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_graspgenx_root() -> Path:
    env = os.environ.get("GRASPGENX_ROOT") or os.environ.get("GRASPGENX_REPO")
    if env:
        return Path(env).expanduser().resolve()
    return (_repo_root().parent / "graspgenx").resolve()


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root() / "local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps.npz",
    )
    parser.add_argument("--graspgenx_root", type=Path, default=_default_graspgenx_root())
    parser.add_argument("--robot_config", type=Path, default=None)
    parser.add_argument("--cube_size", type=float, default=0.06)
    parser.add_argument("--pregrasp_offset", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num_sample_points", type=int, default=2000)
    parser.add_argument("--num_grasps", type=int, default=256)
    parser.add_argument("--topk", type=int, default=128)
    parser.add_argument("--grasp_threshold", type=float, default=-1.0)
    parser.add_argument("--planner", choices=("graspmoe", "diffusion", "topdown"), default="topdown")
    parser.add_argument("--moe_obb_density", choices=("sparse", "dense", "none"), default="dense")
    return parser.parse_args()


def _write_library(path: Path, payload: dict[str, Any]) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    if path.suffix.lower() != ".npz":
        raise ValueError(f"Unsupported output extension for {path}; expected .npz or .json")

    metadata = dict(payload["metadata"])
    np.savez_compressed(
        path,
        grasps_object=np.asarray(payload["grasps_object"], dtype=np.float32),
        confidence=np.asarray(payload["confidence"], dtype=np.float32),
        grasp_to_tool_transform=np.asarray(payload["grasp_to_tool_transform"], dtype=np.float32),
        metadata_json=np.asarray(json.dumps(_jsonable(metadata), sort_keys=True)),
        cube_size_m=np.asarray(float(metadata["cube_size_m"]), dtype=np.float32),
        tool_frame=np.asarray(str(metadata["tool_frame"])),
        gripper_name=np.asarray(str(metadata["gripper_name"])),
    )


def _load_yaml_without_path_expansion(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return payload


def main() -> None:
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("PYGLET_HEADLESS", "true")
    args = parse_args()

    import numpy as np
    import torch
    import trimesh

    graspgenx_root = args.graspgenx_root.expanduser().resolve()
    e2e_dir = graspgenx_root / "end2end"
    if not (e2e_dir / "e2e_grasp_demo.py").is_file():
        raise FileNotFoundError(f"Invalid GraspGenX end2end directory: {e2e_dir}")

    import sys

    for path in (str(graspgenx_root), str(e2e_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from e2e_grasp_demo import run_graspgen
    from robot_profiles import RobotProfile

    torch.manual_seed(int(args.seed))
    np.random.seed(int(args.seed))

    robot_config = args.robot_config
    if robot_config is None:
        robot_config = e2e_dir / "robots/franka_panda.yaml"
    robot_config = robot_config.expanduser().resolve()
    robot_cfg = _load_yaml_without_path_expansion(robot_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    if profile.tool_frame != "panda_hand":
        raise ValueError(f"Expected Franka profile tool_frame='panda_hand', got {profile.tool_frame!r}")

    cube_mesh = trimesh.creation.box(extents=(float(args.cube_size),) * 3)
    bundle = SimpleNamespace(
        object_mesh=cube_mesh,
        object_world_T=np.eye(4, dtype=np.float64),
    )
    grasps_object, confidence = run_graspgen(
        bundle,
        robot_cfg,
        num_sample_points=int(args.num_sample_points),
        num_grasps=int(args.num_grasps),
        topk=int(args.topk),
        seed=int(args.seed),
        grasp_threshold=float(args.grasp_threshold),
        planner=str(args.planner),
        moe_obb_density=str(args.moe_obb_density),
        obb_only=False,
    )
    if len(grasps_object) == 0:
        raise RuntimeError("GraspGenX returned zero grasps for the centered Franka cube")

    grasp_to_tool = np.asarray(profile.grasp_to_tool_transform, dtype=np.float32)
    tool_transforms = np.einsum("nij,jk->nik", grasps_object.astype(np.float32), grasp_to_tool)
    exact_tool_pos = tool_transforms[:, :3, 3]
    tool_z_axis = tool_transforms[:, :3, 2]
    tool_z_axis = tool_z_axis / np.maximum(np.linalg.norm(tool_z_axis, axis=-1, keepdims=True), 1.0e-6)
    plus_pos = exact_tool_pos + abs(float(args.pregrasp_offset)) * tool_z_axis
    minus_pos = exact_tool_pos - abs(float(args.pregrasp_offset)) * tool_z_axis
    exact_dist = np.linalg.norm(exact_tool_pos, axis=-1)
    plus_dist = np.linalg.norm(plus_pos, axis=-1)
    minus_dist = np.linalg.norm(minus_pos, axis=-1)
    pregrasp_dist = np.maximum(plus_dist, minus_dist)

    metadata = {
        "format": "dextrah_franka_cube_grasp_prior_v1",
        "object_frame": "centered cube root frame; origin at cube center; +Z up",
        "cube_size_m": float(args.cube_size),
        "gripper_name": profile.graspgen.gripper_name,
        "tool_frame": profile.tool_frame,
        "grasp_to_tool_transform_name": "T_grasp_tool",
        "robot_config": str(robot_config),
        "planner": str(args.planner),
        "moe_obb_density": str(args.moe_obb_density),
        "grasp_threshold": float(args.grasp_threshold),
        "num_sample_points": int(args.num_sample_points),
        "num_grasps_requested": int(args.num_grasps),
        "topk": int(args.topk),
        "seed": int(args.seed),
        "pregrasp_offset_m": float(args.pregrasp_offset),
        "pregrasp_farther_fraction": float(np.mean(pregrasp_dist > exact_dist)),
        "exact_tool_distance_min_m": float(np.min(exact_dist)),
        "exact_tool_distance_mean_m": float(np.mean(exact_dist)),
        "pregrasp_tool_distance_min_m": float(np.min(pregrasp_dist)),
        "pregrasp_tool_distance_mean_m": float(np.mean(pregrasp_dist)),
    }
    payload = {
        "metadata": metadata,
        "grasps_object": grasps_object.astype(np.float32),
        "confidence": confidence.astype(np.float32),
        "grasp_to_tool_transform": grasp_to_tool,
    }
    output = args.output.expanduser().resolve()
    _write_library(output, payload)

    summary = {
        "output": str(output),
        "num_grasps": int(len(grasps_object)),
        "confidence_min": float(np.min(confidence)),
        "confidence_max": float(np.max(confidence)),
        "metadata": metadata,
    }
    print("DEXTRAH_FRANKA_CUBE_GRASP_PRIOR_LIBRARY_EXPORTED", json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
