#!/usr/bin/env python3
"""Plan YAM grasps with GraspGenX and cuRobo using DEXTRAH scene collisions.

This wrapper is intentionally DEXTRAH-owned: it mirrors the current
single-YAM tabletop-clutter task geometry and emits the exact cuRobo collision
scene used during planning.  It never replans rejected grasps in an empty
world for visualization.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEXTRAH_YAM_ARM_START = [
    0.0,
    0.7853981633974483,
    1.5707963267948966,
    0.0,
    0.0,
    0.0,
]
DEXTRAH_YAM_FINGER_OPEN = -0.02

YAM_TABLE = {
    "surface_z": 0.0,
    "thickness": 0.052,
    "center_x": -0.12,
    "center_y": 0.0,
    "size_x": 1.04,
    "size_y": 1.20,
}
YAM_TABLE["center_z"] = YAM_TABLE["surface_z"] - 0.5 * YAM_TABLE["thickness"]
YAM_ROBOT_BASE = [-0.65, 0.0, 0.01]
YAM_TARGET_XY = [-0.30, 0.0]
YAM_TARGET_DIMS = [0.08, 0.08, 0.08]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_graspgenx_root() -> Path:
    env = os.environ.get("GRASPGENX_ROOT") or os.environ.get("GRASPGENX_REPO")
    if env:
        return Path(env).expanduser().resolve()
    worktree_candidate = _repo_root().parent / "graspgenx-yam-ggx-curobo"
    if worktree_candidate.is_dir():
        return worktree_candidate.resolve()
    repo_candidate = _repo_root().parents[1] / "graspgenx"
    return repo_candidate.resolve()


def _default_curobo_root() -> Path | None:
    env = os.environ.get("GRASPGENX_CUROBO_DIR")
    if env:
        return Path(env).expanduser().resolve()
    candidate = _repo_root().parents[1] / "curobo"
    return candidate.resolve() if candidate.exists() else None


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
        import torch
    except Exception:
        np = None
        torch = None
    if isinstance(value, Path):
        return str(value)
    if np is not None and isinstance(value, np.ndarray):
        return value.tolist()
    if np is not None and isinstance(value, np.generic):
        return value.item()
    if torch is not None and torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def _write_box_obj(path: Path, dims: list[float], *, label: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    hx, hy, hz = [0.5 * float(v) for v in dims]
    verts = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    faces = [
        (1, 2, 3),
        (1, 3, 4),
        (5, 8, 7),
        (5, 7, 6),
        (1, 5, 6),
        (1, 6, 2),
        (2, 6, 7),
        (2, 7, 3),
        (3, 7, 8),
        (3, 8, 4),
        (4, 8, 5),
        (4, 5, 1),
    ]
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# DEXTRAH generated {label} cuboid\n")
        for x, y, z in verts:
            f.write(f"v {x:.9f} {y:.9f} {z:.9f}\n")
        for face in faces:
            f.write("f " + " ".join(str(i) for i in face) + "\n")
    return {"path": str(path), "dims": [float(v) for v in dims], "vertices": len(verts), "faces": len(faces)}


def _quat_wxyz_to_matrix(q: list[float]) -> list[list[float]]:
    qw, qx, qy, qz = [float(v) for v in q]
    n = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if n <= 0.0:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    qw, qx, qy, qz = qw / n, qx / n, qy / n, qz / n
    return [
        [1.0 - 2.0 * (qy * qy + qz * qz), 2.0 * (qx * qy - qz * qw), 2.0 * (qx * qz + qy * qw)],
        [2.0 * (qx * qy + qz * qw), 1.0 - 2.0 * (qx * qx + qz * qz), 2.0 * (qy * qz - qx * qw)],
        [2.0 * (qx * qz - qy * qw), 2.0 * (qy * qz + qx * qw), 1.0 - 2.0 * (qx * qx + qy * qy)],
    ]


def _rotate_vec(rot: list[list[float]], vec: list[float]) -> list[float]:
    return [
        float(rot[row][0] * vec[0] + rot[row][1] * vec[1] + rot[row][2] * vec[2])
        for row in range(3)
    ]


def _matrix_from_pose_wxyz(translation: list[float], quat_wxyz: list[float]) -> list[list[float]]:
    rot = _quat_wxyz_to_matrix(quat_wxyz)
    return [
        [rot[0][0], rot[0][1], rot[0][2], float(translation[0])],
        [rot[1][0], rot[1][1], rot[1][2], float(translation[1])],
        [rot[2][0], rot[2][1], rot[2][2], float(translation[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _infer_raw_objaverse_path(usd_path: str) -> str:
    path = Path(str(usd_path))
    uuid = path.stem
    parts = list(path.parts)
    try:
        usd_idx = parts.index("USD")
    except ValueError:
        return str(path.with_suffix(".obj"))
    return str(Path(*parts[:usd_idx], "raw_objaverse", f"{uuid}.obj"))


def _metrics_target_info(metrics_path: Path | None) -> dict[str, Any] | None:
    if metrics_path is None:
        return None
    metrics = json.loads(metrics_path.expanduser().read_text(encoding="utf-8"))
    snapshot = metrics.get("initial_snapshot") or {}
    target_positions = snapshot.get("target_root_pos") or []
    target_quats = snapshot.get("target_root_quat") or []
    if not target_positions or not target_quats:
        return None
    target_pos = [float(v) for v in target_positions[0]]
    target_quat = [float(v) for v in target_quats[0]]

    asset_summary = metrics.get("multi_object_asset_summary") or {}
    indices = asset_summary.get("object_asset_index_by_env") or []
    asset_idx = int(indices[0]) if indices else 0

    def indexed(name: str, default: Any = None) -> Any:
        values = asset_summary.get(name) or []
        if asset_idx < len(values):
            return values[asset_idx]
        return default

    usd_path = str(indexed("usd_paths", "") or "")
    raw_paths = asset_summary.get("raw_object_paths") or []
    raw_object_path = str(raw_paths[asset_idx]) if asset_idx < len(raw_paths) and raw_paths[asset_idx] else ""
    if not raw_object_path and usd_path:
        raw_object_path = _infer_raw_objaverse_path(usd_path)

    scales = asset_summary.get("usd_spawn_scales") or asset_summary.get("scales") or []
    scale = float(scales[asset_idx]) if asset_idx < len(scales) else 1.0
    return {
        "metrics_path": str(metrics_path),
        "asset_index": asset_idx,
        "uuid": str(indexed("uuids", "") or ""),
        "usd_path": usd_path,
        "raw_object_path": raw_object_path,
        "scale": scale,
        "root_position": target_pos,
        "root_quat_wxyz": target_quat,
        "root_transform": _matrix_from_pose_wxyz(target_pos, target_quat),
    }


def _load_stable_scene(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("format") != "dextrah_stable_scene_v1":
        raise ValueError(f"Expected dextrah_stable_scene_v1 payload in {path}")
    payload["_path"] = str(path.expanduser().resolve())
    return payload


def _stable_scene_target_info(stable_scene: dict[str, Any] | None) -> dict[str, Any] | None:
    if stable_scene is None:
        return None
    target = stable_scene.get("target") or {}
    asset = target.get("asset") or {}
    root_pos = target.get("root_position")
    root_quat = target.get("root_quat_wxyz")
    if not isinstance(root_pos, list) or not isinstance(root_quat, list):
        return None
    scale = float(asset.get("usd_spawn_scale", asset.get("scale", 1.0)) or 1.0)
    return {
        "stable_scene_path": str(stable_scene.get("_path", "")),
        "source": "stable_scene",
        "asset_index": int(asset.get("asset_index", 0) or 0),
        "uuid": str(asset.get("uuid") or ""),
        "usd_path": str(asset.get("usd_path") or ""),
        "raw_object_path": str(asset.get("raw_object_path") or ""),
        "scale": scale,
        "root_position": [float(v) for v in root_pos],
        "root_quat_wxyz": [float(v) for v in root_quat],
        "root_transform": _matrix_from_pose_wxyz([float(v) for v in root_pos], [float(v) for v in root_quat]),
    }


def _stable_scene_target_mesh_path(stable_scene: dict[str, Any] | None) -> Path | None:
    if stable_scene is None:
        return None
    stable_scene_path = Path(str(stable_scene.get("_path", ""))).expanduser()
    base_dir = stable_scene_path.parent if stable_scene_path else Path.cwd()
    target = stable_scene.get("target") or {}
    mesh_copy = target.get("mesh_copy") if isinstance(target.get("mesh_copy"), dict) else {}
    rel = mesh_copy.get("copy_rel")
    if rel:
        candidate = (base_dir / str(rel)).resolve()
        if candidate.is_file():
            return candidate
    copy_path = mesh_copy.get("copy_path")
    if copy_path:
        candidate = Path(str(copy_path)).expanduser()
        if not candidate.is_absolute():
            candidate = (base_dir / candidate).resolve()
        if candidate.is_file():
            return candidate
    asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
    for value in (asset.get("raw_object_path"), _infer_raw_objaverse_path(str(asset.get("usd_path") or ""))):
        if not value:
            continue
        candidate = Path(str(value)).expanduser()
        if candidate.is_file():
            return candidate.resolve()
    return None


def _stable_scene_robot_start(stable_scene: dict[str, Any] | None) -> tuple[list[float] | None, float | None]:
    if stable_scene is None:
        return None, None
    robot = stable_scene.get("robot") if isinstance(stable_scene.get("robot"), dict) else {}
    arm = robot.get("arm_joint_position")
    if not isinstance(arm, list) or not arm:
        return None, None
    start_arm = [float(v) for v in arm[0]]
    finger_value: float | None = None
    fingers = robot.get("finger_joint_position")
    if isinstance(fingers, list) and fingers and fingers[0]:
        finger_value = float(sum(float(v) for v in fingers[0]) / float(len(fingers[0])))
    return start_arm, finger_value


def _goal_bin_obstacles() -> list[dict[str, Any]]:
    wall = 0.02
    bottom = 0.012
    inner_x = 0.36
    inner_y = 0.22
    wall_h = 0.12
    center_x = YAM_TABLE["center_x"] - 0.15
    center_y = YAM_TABLE["center_y"] + 0.42
    outer_x = inner_x + 2.0 * wall
    outer_y = inner_y + 2.0 * wall
    floor_z = YAM_TABLE["surface_z"] + 0.5 * bottom
    wall_z = YAM_TABLE["surface_z"] + bottom + 0.5 * wall_h

    def cuboid(name: str, xyz: list[float], dims: list[float]) -> dict[str, Any]:
        return {"name": name, "type": "cuboid", "dims": dims, "pose": [*xyz, 1.0, 0.0, 0.0, 0.0]}

    return [
        cuboid("dextrah_goal_bin_floor", [center_x, center_y, floor_z], [outer_x, outer_y, bottom]),
        cuboid(
            "dextrah_goal_bin_x_pos_wall",
            [center_x + 0.5 * inner_x + 0.5 * wall, center_y, wall_z],
            [wall, outer_y, wall_h],
        ),
        cuboid(
            "dextrah_goal_bin_x_neg_wall",
            [center_x - 0.5 * inner_x - 0.5 * wall, center_y, wall_z],
            [wall, outer_y, wall_h],
        ),
        cuboid(
            "dextrah_goal_bin_y_pos_wall",
            [center_x, center_y + 0.5 * inner_y + 0.5 * wall, wall_z],
            [inner_x, wall, wall_h],
        ),
        cuboid(
            "dextrah_goal_bin_y_neg_wall",
            [center_x, center_y - 0.5 * inner_y - 0.5 * wall, wall_z],
            [inner_x, wall, wall_h],
        ),
    ]


def _default_clutter_obstacles() -> list[dict[str, Any]]:
    half_extents = [
        [0.040, 0.030, 0.030],
        [0.035, 0.035, 0.055],
        [0.030, 0.045, 0.025],
        [0.050, 0.025, 0.045],
    ]
    centers_xy = [
        [-0.12, -0.19],
        [-0.09, 0.17],
        [-0.44, -0.12],
        [0.08, -0.06],
    ]
    obstacles = []
    for idx, (xy, half) in enumerate(zip(centers_xy, half_extents, strict=True)):
        center = [float(xy[0]), float(xy[1]), YAM_TABLE["surface_z"] + float(half[2])]
        dims = [2.0 * float(v) for v in half]
        obstacles.append(
            {
                "name": f"dextrah_default_clutter_{idx:02d}",
                "type": "cuboid",
                "dims": dims,
                "pose": [*center, 1.0, 0.0, 0.0, 0.0],
            }
        )
    return obstacles


def _metrics_clutter_obstacles(metrics_path: Path, *, margin: float) -> list[dict[str, Any]]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    clutter = metrics.get("tabletop_clutter_summary") or {}
    snapshot = metrics.get("initial_snapshot") or {}
    indices_by_slot = (clutter.get("asset_index_by_env_slot") or [[]])[0]
    positions_by_slot = snapshot.get("clutter_root_pos_by_slot") or []
    quats_by_slot = snapshot.get("clutter_root_quat_by_slot") or []
    bounds_min_all = clutter.get("scaled_bounds_min") or []
    bounds_max_all = clutter.get("scaled_bounds_max") or []
    obstacles: list[dict[str, Any]] = []
    for slot_idx, asset_idx in enumerate(indices_by_slot):
        if slot_idx >= len(positions_by_slot) or slot_idx >= len(quats_by_slot):
            continue
        if int(asset_idx) >= len(bounds_min_all) or int(asset_idx) >= len(bounds_max_all):
            continue
        slot_positions = positions_by_slot[slot_idx]
        slot_quats = quats_by_slot[slot_idx]
        if not slot_positions or not slot_quats:
            continue
        root_pos = [float(v) for v in slot_positions[0]]
        root_quat = [float(v) for v in slot_quats[0]]
        bounds_min = [float(v) for v in bounds_min_all[int(asset_idx)]]
        bounds_max = [float(v) for v in bounds_max_all[int(asset_idx)]]
        local_center = [0.5 * (bounds_min[axis] + bounds_max[axis]) for axis in range(3)]
        dims = [max(bounds_max[axis] - bounds_min[axis] + 2.0 * float(margin), 0.005) for axis in range(3)]
        rot = _quat_wxyz_to_matrix(root_quat)
        center_offset = _rotate_vec(rot, local_center)
        center = [root_pos[axis] + center_offset[axis] for axis in range(3)]
        obstacles.append(
            {
                "name": f"dextrah_metrics_clutter_{slot_idx:02d}",
                "type": "cuboid",
                "dims": dims,
                "pose": [*center, *root_quat],
                "source_asset_index": int(asset_idx),
            }
        )
    return obstacles


def _stable_scene_clutter_obstacles(stable_scene: dict[str, Any], *, margin: float) -> list[dict[str, Any]]:
    obstacles: list[dict[str, Any]] = []
    for entry in stable_scene.get("clutter") or []:
        if not isinstance(entry, dict):
            continue
        asset = entry.get("asset") if isinstance(entry.get("asset"), dict) else {}
        bounds_min = asset.get("scaled_bounds_min")
        bounds_max = asset.get("scaled_bounds_max")
        root_pos = entry.get("root_position")
        root_quat = entry.get("root_quat_wxyz")
        if not all(isinstance(value, list) for value in (bounds_min, bounds_max, root_pos, root_quat)):
            continue
        bounds_min_f = [float(v) for v in bounds_min]
        bounds_max_f = [float(v) for v in bounds_max]
        root_pos_f = [float(v) for v in root_pos]
        root_quat_f = [float(v) for v in root_quat]
        local_center = [0.5 * (bounds_min_f[axis] + bounds_max_f[axis]) for axis in range(3)]
        dims = [max(bounds_max_f[axis] - bounds_min_f[axis] + 2.0 * float(margin), 0.005) for axis in range(3)]
        rot = _quat_wxyz_to_matrix(root_quat_f)
        center_offset = _rotate_vec(rot, local_center)
        center = [root_pos_f[axis] + center_offset[axis] for axis in range(3)]
        obstacles.append(
            {
                "name": f"dextrah_stable_clutter_{int(entry.get('slot_idx', len(obstacles))):02d}",
                "type": "cuboid",
                "dims": dims,
                "pose": [*center, *root_quat_f],
                "source_asset_index": int(asset.get("asset_index", -1) or -1),
                "uuid": str(asset.get("uuid") or ""),
            }
        )
    return obstacles


def _scene_collision(args: argparse.Namespace) -> list[dict[str, Any]]:
    table = {
        "name": "dextrah_tabletop",
        "type": "cuboid",
        "dims": [YAM_TABLE["size_x"], YAM_TABLE["size_y"], YAM_TABLE["thickness"]],
        "pose": [
            YAM_TABLE["center_x"],
            YAM_TABLE["center_y"],
            YAM_TABLE["center_z"],
            1.0,
            0.0,
            0.0,
            0.0,
        ],
    }
    obstacles = [table]
    if bool(args.include_goal_bin):
        obstacles.extend(_goal_bin_obstacles())
    if getattr(args, "stable_scene", None) is not None:
        obstacles.extend(_stable_scene_clutter_obstacles(args.stable_scene, margin=float(args.clutter_margin)))
    elif args.metrics_path is not None:
        obstacles.extend(_metrics_clutter_obstacles(args.metrics_path.expanduser().resolve(), margin=float(args.clutter_margin)))
    elif bool(args.include_default_clutter):
        obstacles.extend(_default_clutter_obstacles())
    return obstacles


def _make_robot_config(
    graspgenx_root: Path,
    run_dir: Path,
    *,
    start_arm_joint_position: list[float] | None = None,
    start_finger_joint_position: float | None = None,
) -> Path:
    start_arm = list(start_arm_joint_position or DEXTRAH_YAM_ARM_START)
    finger_open = DEXTRAH_YAM_FINGER_OPEN if start_finger_joint_position is None else float(start_finger_joint_position)
    src = graspgenx_root / "end2end/robots/yam_linear.yaml"
    cfg = _load_yaml(src)
    curobo_src = (src.parent / cfg["curobo"]["robot_config"]).resolve()
    curobo_cfg = _load_yaml(curobo_src)
    cspace = curobo_cfg.setdefault("robot_cfg", {}).setdefault("kinematics", {}).setdefault("cspace", {})
    cspace["default_joint_position"] = [*start_arm, finger_open, finger_open]
    lock = curobo_cfg["robot_cfg"]["kinematics"].setdefault("lock_joints", {})
    lock["left_finger"] = finger_open
    lock["right_finger"] = finger_open
    curobo_out = run_dir / "configs/yam_linear_curobo_dextrah.yml"
    _write_yaml(curobo_out, curobo_cfg)

    cfg.setdefault("curobo", {})
    cfg["curobo"]["robot_config"] = str(curobo_out)
    cfg["curobo"]["default_joint_position"] = list(start_arm)
    cfg["robot_base_pose"] = {
        "translation": list(YAM_ROBOT_BASE),
        "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    cfg["gripper_open"] = {"left_finger": finger_open, "right_finger": finger_open}
    out = run_dir / "configs/yam_linear_dextrah.yaml"
    _write_yaml(out, cfg)
    return out


def _make_env_config(
    args: argparse.Namespace,
    run_dir: Path,
    target_mesh: Path,
    table_mesh: Path,
    *,
    target_mesh_scale: float,
    target_info: dict[str, Any] | None,
) -> Path:
    target_dims = [float(v) for v in args.target_dims]
    if target_info is not None and bool(args.use_metrics_target_pose):
        target_x = float(target_info["root_position"][0])
        target_y = float(target_info["root_position"][1])
        target_base_z = float(target_info["root_position"][2])
        target_quat_xyzw = [
            float(target_info["root_quat_wxyz"][1]),
            float(target_info["root_quat_wxyz"][2]),
            float(target_info["root_quat_wxyz"][3]),
            float(target_info["root_quat_wxyz"][0]),
        ]
    else:
        target_x = float(args.target_x)
        target_y = float(args.target_y)
        target_base_z = YAM_TABLE["surface_z"] + float(args.object_surface_offset)
        target_quat_xyzw = [0.0, 0.0, 0.0, 1.0]
    collision = _scene_collision(args)
    cfg = {
        "name": "dextrah_single_yam_graspgenx_curobo",
        "assets": [
            {
                "id": "table",
                "type": "mesh_asset",
                "params": {"mesh_file": str(table_mesh), "scale": 1.0},
                "pose": {
                    "translation": [YAM_TABLE["center_x"], YAM_TABLE["center_y"], YAM_TABLE["center_z"]],
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                "support_label": "table_top",
                "collision": "skip",
            }
        ],
        "robot_base_pose": {
            "translation": list(YAM_ROBOT_BASE),
            "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
        "object_slot": {
            "world_position": [target_x, target_y, target_base_z],
            "mesh_scale": float(target_mesh_scale),
            "mesh_file_hint": str(target_mesh),
            "randomize": {"yaw_range_deg": [float(args.target_yaw_deg), float(args.target_yaw_deg)]},
            "root_quaternion_xyzw_hint": target_quat_xyzw,
        },
        "extra_collision": collision,
        "visual": {
            "show_ground_grid": True,
            "background_color": [0.95, 0.95, 0.95],
            "camera": {
                "eye": [-0.52, -0.86, 0.72],
                "target": [target_x, target_y, 0.08],
            },
        },
        "dextrah_geometry": {
            "source_env_cfg": "DextrahSingleYAMTabletopClutterGraspEnvCfg",
            "robot_base": list(YAM_ROBOT_BASE),
            "robot_start_arm_joint_position": list(DEXTRAH_YAM_ARM_START),
            "robot_start_finger_joint_position": DEXTRAH_YAM_FINGER_OPEN,
            "table": dict(YAM_TABLE),
            "target_dims": target_dims,
            "target_base_z": target_base_z,
            "target_mesh": str(target_mesh),
            "target_mesh_scale": float(target_mesh_scale),
            "target_metrics": target_info,
            "metrics_path": None if args.metrics_path is None else str(args.metrics_path),
        },
    }
    out = run_dir / "configs/dextrah_single_yam_graspgenx_curobo.yaml"
    _write_yaml(out, cfg)
    return out


def _validate_runtime(graspgenx_root: Path) -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("torch.cuda.is_available() is false")
    curobo = importlib.import_module("curobo")
    from graspgenx import get_checkpoints_version_dir

    checkpoint_dir = Path(get_checkpoints_version_dir()).resolve()
    if not (checkpoint_dir / "gen/config.yaml").is_file() or not (checkpoint_dir / "dis/config.yaml").is_file():
        raise FileNotFoundError(f"Missing GraspGenX checkpoints under {checkpoint_dir}")
    yam_gripper_assets = graspgenx_root / "end2end/curobo_assets/yam_gripper_assets/x_grippers/yam_linear"
    for name in ("coll_mesh.obj", "vis_mesh.obj"):
        path = yam_gripper_assets / name
        if not path.is_file() or path.stat().st_size < 128:
            raise FileNotFoundError(f"Missing YAM GraspGenX gripper asset: {path}")
    return {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_device_name": torch.cuda.get_device_name(0),
        "curobo_module": getattr(curobo, "__file__", ""),
        "graspgenx_root": str(graspgenx_root),
        "graspgenx_checkpoint_dir": str(checkpoint_dir),
        "yam_gripper_assets": str(yam_gripper_assets),
        "env": {
            "GRASPGENX_ROOT": os.environ.get("GRASPGENX_ROOT", ""),
            "GRASPGENX_CUROBO_DIR": os.environ.get("GRASPGENX_CUROBO_DIR", ""),
            "GRASPGENX_CHECKPOINT_DIR": os.environ.get("GRASPGENX_CHECKPOINT_DIR", ""),
            "GRASPGENX_GRIPPER_CFG_DIR": os.environ.get("GRASPGENX_GRIPPER_CFG_DIR", ""),
        },
    }


@dataclass
class PlanSummary:
    status: str
    run_name: str
    curobo_collision_aware: bool
    selected_grasp_index: int
    selected_grasp_confidence: float
    num_grasps: int
    trajectory_json: str | None
    grasp_pose_overlay_json: str
    collision_scene_model_json: str
    planner_status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=_repo_root() / "local_results/yam_graspgenx_curobo")
    parser.add_argument("--run_name", type=str, default=None)
    parser.add_argument("--graspgenx_root", type=Path, default=_default_graspgenx_root())
    parser.add_argument("--curobo_root", type=Path, default=_default_curobo_root())
    parser.add_argument("--metrics_path", type=Path, default=None, help="Optional DEXTRAH render metrics.json for sampled clutter proxies.")
    parser.add_argument("--stable_scene_path", type=Path, default=None, help="Optional DEXTRAH stable_scene.json captured after simulation settle.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num_sample_points", type=int, default=2000)
    parser.add_argument("--num_grasps", type=int, default=64)
    parser.add_argument("--topk", type=int, default=32)
    parser.add_argument("--grasp_threshold", type=float, default=-1.0)
    parser.add_argument("--grasp_planner", choices=("graspmoe", "diffusion", "topdown"), default="graspmoe")
    parser.add_argument("--moe_obb_density", choices=("sparse", "dense", "none"), default="dense")
    parser.add_argument("--max_plan_attempts", type=int, default=32)
    parser.add_argument("--rank_grasps_by_confidence", action="store_true", default=True)
    parser.add_argument("--target_x", type=float, default=YAM_TARGET_XY[0])
    parser.add_argument("--target_y", type=float, default=YAM_TARGET_XY[1])
    parser.add_argument("--target_yaw_deg", type=float, default=0.0)
    parser.add_argument("--target_dims", type=float, nargs=3, default=YAM_TARGET_DIMS)
    parser.add_argument("--target_mesh_path", type=Path, default=None)
    parser.add_argument("--target_mesh_scale", type=float, default=None)
    parser.add_argument("--use_metrics_target_pose", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--align_grasps_to_metrics_target", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--object_surface_offset", type=float, default=0.006)
    parser.add_argument("--include_goal_bin", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include_default_clutter", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--clutter_margin", type=float, default=0.006)
    parser.add_argument("--sim_fps", type=int, default=60)
    parser.add_argument("--close_frames", type=int, default=30)
    parser.add_argument("--hold_frames", type=int, default=45)
    parser.add_argument("--hold_after_close_frames", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_name = args.run_name or time.strftime("yam_ggx_curobo_%Y%m%d_%H%M%S")
    run_dir = (args.output_dir.expanduser().resolve() / run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    graspgenx_root = args.graspgenx_root.expanduser().resolve()
    if not (graspgenx_root / "end2end/e2e_grasp_demo.py").is_file():
        raise FileNotFoundError(f"Invalid GraspGenX root: {graspgenx_root}")
    os.environ.setdefault("GRASPGENX_ROOT", str(graspgenx_root))
    if (graspgenx_root / "ext/graspgenx_checkpoints").is_dir():
        os.environ.setdefault("GRASPGENX_CHECKPOINT_DIR", str(graspgenx_root / "ext/graspgenx_checkpoints"))
    if (graspgenx_root / "ext/gripper_descriptions").is_dir():
        os.environ.setdefault("GRASPGENX_GRIPPER_CFG_DIR", str(graspgenx_root / "ext/gripper_descriptions"))
    if args.curobo_root is not None:
        curobo_root = args.curobo_root.expanduser().resolve()
        os.environ.setdefault("GRASPGENX_CUROBO_DIR", str(curobo_root))
        if str(curobo_root) not in sys.path:
            sys.path.insert(0, str(curobo_root))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("PYGLET_HEADLESS", "true")
    for path in (str(graspgenx_root), str(graspgenx_root / "end2end")):
        if path not in sys.path:
            sys.path.insert(0, path)

    import numpy as np
    import torch

    from e2e_grasp_demo import collision_world_to_curobo, export_trajectory, init_planner, plan_to_grasp, run_graspgen
    from robot_profiles import RobotProfile
    from scene_builder import build_scene, load_yaml
    from tasks import get_task
    from trajectory_visualizer import URDFFK

    torch.manual_seed(int(args.seed))
    np.random.seed(int(args.seed))

    env_info = _validate_runtime(graspgenx_root)
    _write_json(run_dir / "environment.json", env_info)

    stable_scene = _load_stable_scene(args.stable_scene_path)
    args.stable_scene = stable_scene
    stable_target_info = _stable_scene_target_info(stable_scene)
    target_info = stable_target_info or _metrics_target_info(args.metrics_path)
    stable_target_mesh = _stable_scene_target_mesh_path(stable_scene)
    stable_start_arm_q, stable_start_finger_q = _stable_scene_robot_start(stable_scene)
    target_mesh_source = "target_mesh_path" if args.target_mesh_path is not None else "stable_scene" if stable_target_mesh is not None else "generated_box"
    target_mesh = (
        args.target_mesh_path.expanduser().resolve()
        if args.target_mesh_path is not None
        else stable_target_mesh
        if stable_target_mesh is not None
        else run_dir / "assets/yam_target_cuboid.obj"
    )
    table_mesh = run_dir / "assets/dextrah_tabletop.obj"
    if target_mesh_source == "generated_box":
        target_mesh_meta = _write_box_obj(target_mesh, [float(v) for v in args.target_dims], label="YAM target")
    elif not target_mesh.is_file():
        raise FileNotFoundError(f"Missing target mesh: {target_mesh}")
    else:
        target_mesh_meta = {
            "path": str(target_mesh),
            "source": target_mesh_source,
            "target_info": target_info,
        }
    if args.target_mesh_scale is not None:
        target_mesh_scale = float(args.target_mesh_scale)
    elif target_info is not None and target_mesh_source in {"target_mesh_path", "stable_scene"}:
        target_mesh_scale = float(target_info.get("scale", 1.0))
    else:
        target_mesh_scale = 1.0
    table_mesh_meta = _write_box_obj(
        table_mesh,
        [YAM_TABLE["size_x"], YAM_TABLE["size_y"], YAM_TABLE["thickness"]],
        label="DEXTRAH tabletop",
    )
    robot_config = _make_robot_config(
        graspgenx_root,
        run_dir,
        start_arm_joint_position=stable_start_arm_q,
        start_finger_joint_position=stable_start_finger_q,
    )
    env_config = _make_env_config(
        args,
        run_dir,
        target_mesh,
        table_mesh,
        target_mesh_scale=target_mesh_scale,
        target_info=target_info,
    )

    robot_cfg = load_yaml(robot_config)
    env_cfg = load_yaml(env_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    bundle = build_scene(env_cfg, robot_cfg, str(target_mesh), seed=int(args.seed))

    _write_json(
        run_dir / "run_config.json",
        {
            "args": vars(args),
            "stable_scene": stable_scene,
            "stable_start_arm_joint_position": stable_start_arm_q,
            "stable_start_finger_joint_position": stable_start_finger_q,
            "robot_config": str(robot_config),
            "env_config": str(env_config),
            "target_mesh": target_mesh_meta,
            "table_mesh": table_mesh_meta,
            "robot_profile": profile.NAME,
            "robot_base_T": bundle.robot_base_T,
            "object_world_T": bundle.object_world_T,
            "collision_obstacles_world": [ob.__dict__ for ob in bundle.collision_world],
        },
    )

    grasps_world, conf = run_graspgen(
        bundle=bundle,
        robot_cfg=robot_cfg,
        num_sample_points=int(args.num_sample_points),
        num_grasps=int(args.num_grasps),
        topk=int(args.topk),
        seed=int(args.seed),
        grasp_threshold=float(args.grasp_threshold),
        planner=str(args.grasp_planner),
        moe_obb_density=str(args.moe_obb_density),
        obb_only=False,
    )
    if len(grasps_world) == 0:
        raise RuntimeError("GraspGenX returned zero YAM grasps")
    target_alignment: dict[str, Any] | None = None
    if (
        target_info is not None
        and bool(args.align_grasps_to_metrics_target)
        and target_mesh_source in {"target_mesh_path", "stable_scene"}
    ):
        metrics_target_T = np.asarray(target_info["root_transform"], dtype=float)
        source_target_T = np.asarray(bundle.object_world_T, dtype=float)
        source_to_metrics = metrics_target_T @ np.linalg.inv(source_target_T)
        grasps_world = [source_to_metrics @ np.asarray(grasp, dtype=float) for grasp in grasps_world]
        bundle.object_world_T = metrics_target_T
        if bundle.objects:
            bundle.objects[0].world_T = metrics_target_T.copy()
        target_alignment = {
            "enabled": True,
            "source_target_transform": source_target_T,
            "metrics_target_transform": metrics_target_T,
            "source_to_metrics_transform": source_to_metrics,
            "target_info": target_info,
        }
    else:
        target_alignment = {
            "enabled": False,
            "reason": "missing target transform or external target mesh",
            "target_info": target_info,
        }

    scene_model = collision_world_to_curobo(bundle.collision_world, bundle.robot_base_T)
    collision_scene_model_json = run_dir / "collision_scene_model.json"
    _write_json(collision_scene_model_json, scene_model)
    cuboids = scene_model.get("cuboid", {})
    required = {"dextrah_tabletop"}
    if bool(args.include_goal_bin):
        required.add("dextrah_goal_bin_floor")
    missing = sorted(required - set(cuboids))
    if missing:
        raise RuntimeError(f"cuRobo scene model is missing required cuboids: {missing}")

    planner = init_planner(
        robot_config,
        robot_cfg,
        scene_model,
        max_goalset=max(int(args.max_plan_attempts), len(grasps_world), 1),
    )
    success, result, target_idx, pregrasp_traj, lift_traj = plan_to_grasp(
        planner,
        robot_cfg,
        grasps_world,
        conf,
        max_attempts=int(args.max_plan_attempts),
        seed=int(args.seed),
        robot_base_T=bundle.robot_base_T,
        force_idx=-1,
        rank_by_confidence=bool(args.rank_grasps_by_confidence),
    )
    planner_status = str(getattr(result, "status", "<no result>")) if result is not None else "<no result>"

    if target_idx < 0:
        target_idx = int(np.argmax(conf))

    trajectory_json: Path | None = None
    trajectory_start_summary: dict[str, Any] | None = None
    if bool(success) and pregrasp_traj is not None and len(pregrasp_traj) > 0 and lift_traj is not None and len(lift_traj) > 0:
        task = get_task("pick_and_lift")
        task_result = task.plan_actions(
            planner=planner,
            bundle=bundle,
            profile=profile,
            grasps_world=grasps_world,
            conf=conf,
            target_idx=int(target_idx),
            pregrasp_traj=pregrasp_traj,
            lift_traj=lift_traj,
            env_cfg=env_cfg,
            close_frames=int(args.close_frames),
            hold_frames=int(args.hold_frames),
            hold_after_close_frames=int(args.hold_after_close_frames),
            playback_mode="dynamic",
            result=result,
        )
        joint_traj = np.asarray(task_result.joint_traj, dtype=np.float32)
        expected_start_arm = np.asarray(robot_cfg["curobo"]["default_joint_position"], dtype=np.float32)
        expected_start_grip = np.asarray(
            [
                stable_start_finger_q
                if stable_start_finger_q is not None
                else profile.open_value(name)
                for name in profile.gripper_joint_names
            ],
            dtype=np.float32,
        )
        expected_start = np.concatenate([expected_start_arm, expected_start_grip], axis=0)
        if joint_traj.shape[1] == expected_start.shape[0]:
            start_delta = joint_traj[0] - expected_start
            max_abs_start_delta = float(np.max(np.abs(start_delta)))
            trajectory_start_summary = {
                "expected_start": expected_start,
                "first_planned": joint_traj[0],
                "max_abs_delta_before_guard": max_abs_start_delta,
                "prepended_settled_start": bool(max_abs_start_delta > 1.0e-4),
            }
            if max_abs_start_delta > 1.0e-4:
                joint_traj = np.vstack([expected_start[None, :], joint_traj]).astype(np.float32)
        else:
            trajectory_start_summary = {
                "expected_start": expected_start,
                "first_planned": joint_traj[0] if joint_traj.shape[0] else [],
                "reason": "dimension_mismatch",
                "trajectory_dim": int(joint_traj.shape[1]),
                "expected_dim": int(expected_start.shape[0]),
            }
        trajectory_json = run_dir / "trajectory.json"
        camera = (env_cfg.get("visual") or {}).get("camera", {})
        fk = URDFFK(profile.urdf_path, asset_root=profile.asset_root_path)
        export_trajectory(
            bundle=bundle,
            fk=fk,
            profile=profile,
            joint_traj=joint_traj,
            grasps_world=grasps_world,
            target_idx=int(target_idx),
            camera_eye=list(camera.get("eye", [-0.52, -0.86, 0.72])),
            camera_target=list(camera.get("target", [float(args.target_x), float(args.target_y), 0.08])),
            output_path=trajectory_json,
            fps=int(args.sim_fps),
        )

    overlay_json = run_dir / "grasp_pose_overlay.json"
    overlay_payload = {
        "status": "accepted" if bool(success) else "rejected_or_failed",
        "planner_status": planner_status,
        "selected_grasp_index": int(target_idx),
        "selected_grasp_confidence": float(conf[target_idx]),
        "selected_grasp_world": grasps_world[target_idx],
        "annotations": {
            "all_grasps": grasps_world,
            "target_grasp_transform": grasps_world[target_idx],
        },
        "collision_scene_model": scene_model,
        "world_scene": {
            "robot_base": list(YAM_ROBOT_BASE),
            "target_xyz": (
                [float(v) for v in target_info["root_position"]]
                if target_info is not None
                else [
                    float(args.target_x),
                    float(args.target_y),
                    YAM_TABLE["surface_z"] + float(args.object_surface_offset),
                ]
            ),
            "target_dims": [float(v) for v in args.target_dims],
            "target_mesh": str(target_mesh),
            "target_mesh_scale": float(target_mesh_scale),
            "target_alignment": target_alignment,
            "table": dict(YAM_TABLE),
        },
        "trajectory_start": trajectory_start_summary,
        "trajectory_json": None if trajectory_json is None else str(trajectory_json),
    }
    _write_json(overlay_json, overlay_payload)

    summary = PlanSummary(
        status="accepted" if bool(success) and trajectory_json is not None else "rejected_or_failed",
        run_name=run_name,
        curobo_collision_aware=True,
        selected_grasp_index=int(target_idx),
        selected_grasp_confidence=float(conf[target_idx]),
        num_grasps=int(len(grasps_world)),
        trajectory_json=None if trajectory_json is None else str(trajectory_json),
        grasp_pose_overlay_json=str(overlay_json),
        collision_scene_model_json=str(collision_scene_model_json),
        planner_status=planner_status,
    )
    _write_json(
        run_dir / "plan_summary.json",
        {**asdict(summary), "success": bool(success), "trajectory_start": trajectory_start_summary},
    )
    print("DEXTRAH_YAM_GRASPGENX_CUROBO_PLAN " + json.dumps(asdict(summary), sort_keys=True), flush=True)
    print(f"results={run_dir}", flush=True)


if __name__ == "__main__":
    main()
