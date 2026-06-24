#!/usr/bin/env python3
"""Plan YAM grasps with GraspGenX and cuRobo using DEXTRAH scene collisions.

This wrapper is intentionally DEXTRAH-owned: it mirrors the current
single-YAM tabletop-clutter task geometry and emits the exact cuRobo collision
scene used during planning.  It never replans rejected grasps in an empty
world for visualization.
"""

from __future__ import annotations

import argparse
import copy
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
YAM_GRIPPER_CENTER_LOCAL = [0.0, 0.0, 0.1098]
YAM_GRIPPER_CENTER_TOL = [0.045, 0.040, 0.036]
YAM_MAX_FALLBACK_GEOMETRY_COST = 0.75
YAM_MIN_LIFT_UP_DOT = 0.40
YAM_PREFERRED_LIFT_UP_DOT = 0.75
YAM_LIFT_ORIENTATION_WEIGHT = 0.25
YAM_MIN_TOOL_Z = 0.095


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


def _matrix_from_pose_xyzw(translation: list[float], quat_xyzw: list[float]) -> list[list[float]]:
    qx, qy, qz, qw = [float(v) for v in quat_xyzw]
    return _matrix_from_pose_wxyz(translation, [qw, qx, qy, qz])


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
    bounds_min_all = asset_summary.get("scaled_bounds_min") or []
    bounds_max_all = asset_summary.get("scaled_bounds_max") or []
    scale = float(scales[asset_idx]) if asset_idx < len(scales) else 1.0
    return {
        "metrics_path": str(metrics_path),
        "asset_index": asset_idx,
        "uuid": str(indexed("uuids", "") or ""),
        "usd_path": usd_path,
        "raw_object_path": raw_object_path,
        "scale": scale,
        "scaled_bounds_min": bounds_min_all[asset_idx] if asset_idx < len(bounds_min_all) else None,
        "scaled_bounds_max": bounds_max_all[asset_idx] if asset_idx < len(bounds_max_all) else None,
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
        "scaled_bounds_min": asset.get("scaled_bounds_min"),
        "scaled_bounds_max": asset.get("scaled_bounds_max"),
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
    candidate_values: list[object] = []
    raw_object_path = asset.get("raw_object_path")
    if raw_object_path:
        candidate_values.append(raw_object_path)
    usd_path = str(asset.get("usd_path") or "")
    if usd_path:
        candidate_values.append(_infer_raw_objaverse_path(usd_path))
    for value in candidate_values:
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


def _default_goal_bin_info() -> dict[str, float]:
    wall = 0.02
    bottom = 0.012
    inner_x = 0.36
    inner_y = 0.22
    wall_h = 0.12
    center_x = YAM_TABLE["center_x"] - 0.15
    center_y = YAM_TABLE["center_y"] + 0.42
    outer_x = inner_x + 2.0 * wall
    outer_y = inner_y + 2.0 * wall
    return {
        "center_x": center_x,
        "center_y": center_y,
        "inner_size_x": inner_x,
        "inner_size_y": inner_y,
        "outer_size_x": outer_x,
        "outer_size_y": outer_y,
        "wall_thickness": wall,
        "bottom_thickness": bottom,
        "wall_height": wall_h,
        "table_surface_z": YAM_TABLE["surface_z"],
        "floor_center_z": YAM_TABLE["surface_z"] + 0.5 * bottom,
        "inner_floor_z": YAM_TABLE["surface_z"] + bottom,
        "wall_center_z": YAM_TABLE["surface_z"] + bottom + 0.5 * wall_h,
        "inner_top_z": YAM_TABLE["surface_z"] + bottom + wall_h,
    }


def _stable_scene_bin_info(stable_scene: dict[str, Any] | None, key: str) -> dict[str, float] | None:
    if stable_scene is None:
        return None
    bins = stable_scene.get("bins") if isinstance(stable_scene.get("bins"), dict) else {}
    info = bins.get(key) if isinstance(bins, dict) else None
    if not isinstance(info, dict):
        return None
    required = (
        "center_x",
        "center_y",
        "inner_size_x",
        "inner_size_y",
        "outer_size_x",
        "outer_size_y",
        "wall_thickness",
        "bottom_thickness",
        "wall_height",
        "floor_center_z",
        "wall_center_z",
        "inner_top_z",
    )
    if any(name not in info for name in required):
        return None
    return {name: float(value) for name, value in info.items() if isinstance(value, (int, float))}


def _goal_bin_info(stable_scene: dict[str, Any] | None = None) -> dict[str, float]:
    return _stable_scene_bin_info(stable_scene, "goal") or _default_goal_bin_info()


def _bin_obstacles(info: dict[str, float], *, name_prefix: str) -> list[dict[str, Any]]:
    wall = float(info["wall_thickness"])
    inner_x = float(info["inner_size_x"])
    inner_y = float(info["inner_size_y"])
    outer_x = float(info["outer_size_x"])
    outer_y = float(info["outer_size_y"])
    wall_h = float(info["wall_height"])
    bottom = float(info["bottom_thickness"])
    center_x = float(info["center_x"])
    center_y = float(info["center_y"])
    floor_z = float(info["floor_center_z"])
    wall_z = float(info["wall_center_z"])

    def cuboid(name: str, xyz: list[float], dims: list[float]) -> dict[str, Any]:
        return {"name": name, "type": "cuboid", "dims": dims, "pose": [*xyz, 1.0, 0.0, 0.0, 0.0]}

    return [
        cuboid(f"{name_prefix}_floor", [center_x, center_y, floor_z], [outer_x, outer_y, bottom]),
        cuboid(
            f"{name_prefix}_x_pos_wall",
            [center_x + 0.5 * inner_x + 0.5 * wall, center_y, wall_z],
            [wall, outer_y, wall_h],
        ),
        cuboid(
            f"{name_prefix}_x_neg_wall",
            [center_x - 0.5 * inner_x - 0.5 * wall, center_y, wall_z],
            [wall, outer_y, wall_h],
        ),
        cuboid(
            f"{name_prefix}_y_pos_wall",
            [center_x, center_y + 0.5 * inner_y + 0.5 * wall, wall_z],
            [inner_x, wall, wall_h],
        ),
        cuboid(
            f"{name_prefix}_y_neg_wall",
            [center_x, center_y - 0.5 * inner_y - 0.5 * wall, wall_z],
            [inner_x, wall, wall_h],
        ),
    ]


def _goal_bin_obstacles(stable_scene: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return _bin_obstacles(_goal_bin_info(stable_scene), name_prefix="dextrah_goal_bin")


def _source_bin_obstacles(stable_scene: dict[str, Any] | None) -> list[dict[str, Any]]:
    source_info = _stable_scene_bin_info(stable_scene, "source")
    if source_info is None:
        return []
    return _bin_obstacles(source_info, name_prefix="dextrah_source_bin")


def _goal_bin_center(stable_scene: dict[str, Any] | None = None) -> list[float]:
    info = _goal_bin_info(stable_scene)
    # Expose the bin pose at the top rim center for trajectory helpers. The
    # actual collision model remains the five cuboids from _goal_bin_obstacles.
    return [float(info["center_x"]), float(info["center_y"]), float(info["inner_top_z"])]


def _minimum_jerk_ramp(start: Any, end: Any, n_frames: int) -> Any:
    import numpy as np

    n = max(int(n_frames), 1)
    start_arr = np.asarray(start, dtype=np.float32).reshape(1, -1)
    end_arr = np.asarray(end, dtype=np.float32).reshape(1, -1)
    alpha = np.linspace(0.0, 1.0, n, dtype=np.float32).reshape(-1, 1)
    blend = 10.0 * alpha**3 - 15.0 * alpha**4 + 6.0 * alpha**5
    return (start_arr + blend * (end_arr - start_arr)).astype(np.float32)


def _yam_fk_link_position(
    fk: Any,
    profile: Any,
    base_T: Any,
    q_arm: Any,
    link_name: str,
) -> tuple[Any, Any]:
    import numpy as np

    cfg = {name: float(value) for name, value in zip(profile.arm_joint_names, q_arm, strict=True)}
    T = fk.fk(cfg, base_T=base_T, link_names=[link_name])[link_name]
    return np.asarray(T[:3, 3], dtype=np.float64), T


def _solve_yam_scripted_bin_arm_pose(
    *,
    profile: Any,
    bundle: Any,
    q_start_arm: Any,
    target_link_position_world: Any,
) -> tuple[Any | None, dict[str, Any]]:
    import numpy as np
    from scipy.optimize import least_squares
    from trajectory_visualizer import URDFFK

    fk = URDFFK(profile.urdf_path, asset_root=profile.asset_root_path)
    q_start = np.asarray(q_start_arm, dtype=np.float64).reshape(-1)
    target = np.asarray(target_link_position_world, dtype=np.float64).reshape(3)
    if q_start.shape[0] != int(profile.n_arm):
        return None, {
            "enabled": True,
            "success": False,
            "reason": "bad_start_arm_shape",
            "shape": list(q_start.shape),
            "expected": int(profile.n_arm),
        }

    lower: list[float] = []
    upper: list[float] = []
    joint_map = {joint.name: joint for joint in fk._urdf.actuated_joints}
    for name, value in zip(profile.arm_joint_names, q_start, strict=True):
        joint = joint_map.get(name)
        limit = getattr(joint, "limit", None) if joint is not None else None
        lower.append(float(getattr(limit, "lower", value - 1.0)))
        upper.append(float(getattr(limit, "upper", value + 1.0)))
    lo = np.asarray(lower, dtype=np.float64)
    hi = np.asarray(upper, dtype=np.float64)
    q_start = np.clip(q_start, lo, hi)

    starts = [q_start]
    deterministic_offsets = [
        [0.10, 0.20, 0.20, 0.10, -0.05, 0.0],
        [0.20, 0.35, 0.30, 0.20, -0.10, 0.0],
        [0.35, 0.55, 0.55, 0.35, -0.15, 0.0],
        [-0.10, 0.20, 0.20, 0.10, -0.05, 0.0],
    ]
    for offset in deterministic_offsets:
        starts.append(np.clip(q_start + np.asarray(offset, dtype=np.float64), lo, hi))

    def _position(q: Any) -> Any:
        pos, _ = _yam_fk_link_position(fk, profile, bundle.robot_base_T, q, profile.tool_frame)
        return pos

    best: tuple[float, float, float, Any, Any] | None = None
    attempts: list[dict[str, Any]] = []
    for start in starts:
        def residual(q: Any) -> Any:
            pos = _position(q)
            return np.concatenate([(pos - target) * 8.0, (q - q_start) * 0.08])

        result = least_squares(
            residual,
            start,
            bounds=(lo, hi),
            max_nfev=180,
            xtol=1.0e-5,
            ftol=1.0e-5,
            gtol=1.0e-5,
        )
        q = np.asarray(result.x, dtype=np.float64)
        pos = _position(q)
        position_error = float(np.linalg.norm(pos - target))
        q_distance = float(np.linalg.norm(q - q_start))
        score = float(position_error + 0.015 * q_distance)
        attempts.append(
            {
                "start": start.tolist(),
                "q": q.tolist(),
                "position": pos.tolist(),
                "position_error": position_error,
                "q_distance": q_distance,
                "score": score,
                "success": bool(result.success),
                "status": int(result.status),
                "message": str(result.message),
            }
        )
        candidate = (score, position_error, q_distance, q, pos)
        if best is None or candidate[0] < best[0]:
            best = candidate

    if best is None:
        return None, {
            "enabled": True,
            "success": False,
            "reason": "no_ik_attempts",
            "target_link_position_world": target.tolist(),
            "attempts": attempts,
        }

    score, position_error, q_distance, q_best, pos_best = best
    ramp = _minimum_jerk_ramp(q_start, q_best, 121)
    ramp_positions = np.asarray([_position(q) for q in ramp], dtype=np.float64)
    summary = {
        "enabled": True,
        "success": bool(position_error <= 0.025),
        "target_link_position_world": target.tolist(),
        "solved_link_position_world": pos_best.tolist(),
        "position_error": position_error,
        "q_distance": q_distance,
        "score": score,
        "q_start_arm": q_start.tolist(),
        "q_target_arm": q_best.tolist(),
        "ramp_link_min_z": float(ramp_positions[:, 2].min()),
        "ramp_link_max_z": float(ramp_positions[:, 2].max()),
        "ramp_link_min_y": float(ramp_positions[:, 1].min()),
        "ramp_link_max_y": float(ramp_positions[:, 1].max()),
        "joint_limits_lower": lo.tolist(),
        "joint_limits_upper": hi.tolist(),
        "attempts": sorted(attempts, key=lambda item: float(item["score"]))[:3],
    }
    if not summary["success"]:
        return None, summary
    return q_best.astype(np.float32), summary


def _append_scripted_yam_bin_drop(
    *,
    joint_traj: Any,
    segments: list[tuple[str, int]],
    profile: Any,
    bundle: Any,
    target_center_world: Any | None,
    selected_tool_world: Any,
    bin_top_center_world: Any | None,
    move_frames: int,
    hold_frames: int,
    open_frames: int,
    drop_height_above_bin: float,
    drop_y_offset: float,
) -> tuple[Any, list[tuple[str, int]], dict[str, Any]]:
    import numpy as np

    traj = np.asarray(joint_traj, dtype=np.float32)
    if traj.ndim != 2 or traj.shape[0] == 0:
        return traj, segments, {"enabled": True, "success": False, "reason": "empty_trajectory"}
    if target_center_world is None:
        return traj, segments, {"enabled": True, "success": False, "reason": "missing_target_center_world"}

    n_arm = int(profile.n_arm)
    n_grip = int(profile.n_gripper)
    q_start_arm = traj[-1, :n_arm].astype(np.float32)
    finger_hold = traj[-1, n_arm : n_arm + n_grip].astype(np.float32)
    selected_tool = np.asarray(selected_tool_world, dtype=np.float64)
    target_center = np.asarray(target_center_world, dtype=np.float64).reshape(3)
    tool_center_offset = selected_tool[:3, 3] - target_center
    bin_top = np.asarray(
        _goal_bin_center() if bin_top_center_world is None else bin_top_center_world,
        dtype=np.float64,
    )
    desired_object_drop = np.asarray(
        [
            bin_top[0],
            bin_top[1] + float(drop_y_offset),
            max(bin_top[2] + 0.035, bin_top[2] + float(drop_height_above_bin) - float(tool_center_offset[2])),
        ],
        dtype=np.float64,
    )
    target_link_position = desired_object_drop + tool_center_offset
    target_link_position[2] = max(
        target_link_position[2],
        bin_top[2] + float(drop_height_above_bin),
    )

    q_bin, solve_summary = _solve_yam_scripted_bin_arm_pose(
        profile=profile,
        bundle=bundle,
        q_start_arm=q_start_arm,
        target_link_position_world=target_link_position,
    )
    summary: dict[str, Any] = {
        "enabled": True,
        "success": q_bin is not None,
        "drop_mode": "scripted_minimum_jerk_joint_space",
        "bin_top_center_world": bin_top.tolist(),
        "desired_object_drop_world": desired_object_drop.tolist(),
        "tool_minus_object_center_world_at_grasp": tool_center_offset.tolist(),
        "target_link_position_world": target_link_position.tolist(),
        "drop_y_offset": float(drop_y_offset),
        "drop_height_above_bin": float(drop_height_above_bin),
        "move_frames": int(move_frames),
        "hold_frames": int(hold_frames),
        "open_frames": int(open_frames),
        "solve": solve_summary,
    }
    if q_bin is None:
        return traj, segments, summary

    move_arm = _minimum_jerk_ramp(q_start_arm, q_bin, max(2, int(move_frames)))
    move_full = np.concatenate(
        [move_arm, np.tile(finger_hold.reshape(1, -1), (move_arm.shape[0], 1))],
        axis=1,
    ).astype(np.float32)
    chunks = [traj, move_full]
    new_segments = list(segments)
    new_segments.append(("move_to_above_bin_scripted", int(move_full.shape[0])))

    if int(hold_frames) > 0:
        hold = np.tile(move_full[-1], (int(hold_frames), 1)).astype(np.float32)
        chunks.append(hold)
        new_segments.append(("hold_above_bin", int(hold.shape[0])))

    if n_grip > 0:
        open_vals = np.asarray([profile.open_value(name) for name in profile.gripper_joint_names], dtype=np.float32)
        release_grip = _minimum_jerk_ramp(finger_hold, open_vals, max(1, int(open_frames)))
        release_arm = np.tile(move_full[-1, :n_arm], (release_grip.shape[0], 1)).astype(np.float32)
        release = np.concatenate([release_arm, release_grip], axis=1).astype(np.float32)
        chunks.append(release)
        new_segments.append(("open_fingers_to_drop", int(release.shape[0])))
        if int(hold_frames) > 0:
            post = np.tile(release[-1], (int(hold_frames), 1)).astype(np.float32)
            chunks.append(post)
            new_segments.append(("hold_after_drop", int(post.shape[0])))

    out = np.concatenate(chunks, axis=0).astype(np.float32)
    summary["total_frames_before"] = int(traj.shape[0])
    summary["total_frames_after"] = int(out.shape[0])
    summary["q_target_full"] = out[min(traj.shape[0] + move_full.shape[0] - 1, out.shape[0] - 1)].tolist()
    return out, new_segments, summary


def _apply_yam_planning_preclose_to_pick_segments(
    joint_traj: Any,
    segments: list[tuple[str, int]],
    *,
    profile: Any,
    planning_finger_joint_position: float | None,
) -> tuple[Any, dict[str, Any]]:
    import numpy as np

    if planning_finger_joint_position is None:
        return joint_traj, {"enabled": False, "reason": "planning_finger_not_set"}
    traj = np.asarray(joint_traj, dtype=np.float32).copy()
    n_arm = int(profile.n_arm)
    n_grip = int(profile.n_gripper)
    if traj.ndim != 2 or n_grip <= 0 or traj.shape[1] < n_arm + n_grip:
        return traj, {
            "enabled": True,
            "success": False,
            "reason": "trajectory_dimension_mismatch",
            "trajectory_shape": list(traj.shape),
            "n_arm": n_arm,
            "n_gripper": n_grip,
        }
    preclose = np.full((n_grip,), float(planning_finger_joint_position), dtype=np.float32)
    preclose_phases = {
        "go_to_pre_grasp_pose",
        "hold_at_pre_grasp",
        "go_from_pre_grasp_to_grasp_pose",
        "hold_at_grasp",
    }
    cursor = 0
    preclose_frames = 0
    close_frames = 0
    close_end: list[float] | None = None
    for phase, count in segments:
        count_i = max(int(count), 0)
        start = cursor
        end = min(cursor + count_i, traj.shape[0])
        cursor += count_i
        if end <= start:
            continue
        grip_slice = (slice(start, end), slice(n_arm, n_arm + n_grip))
        if str(phase) in preclose_phases:
            traj[grip_slice] = preclose.reshape(1, -1)
            preclose_frames += int(end - start)
        elif str(phase) == "close_fingers":
            close_end_values = traj[end - 1, n_arm : n_arm + n_grip].astype(np.float32)
            alpha = np.linspace(0.0, 1.0, end - start, dtype=np.float32).reshape(-1, 1)
            traj[grip_slice] = preclose.reshape(1, -1) + alpha * (
                close_end_values.reshape(1, -1) - preclose.reshape(1, -1)
            )
            close_frames += int(end - start)
            close_end = close_end_values.tolist()
    return traj, {
        "enabled": True,
        "success": True,
        "planning_finger_joint_position": float(planning_finger_joint_position),
        "preclose_frames": int(preclose_frames),
        "close_frames": int(close_frames),
        "close_end": close_end,
        "phases": sorted(preclose_phases),
    }


def _make_scripted_yam_vertical_lift(
    *,
    pregrasp_traj: Any,
    profile: Any,
    bundle: Any,
    target_center_world: Any | None,
    selected_tool_world: Any,
    lift_height: float,
    lift_frames: int,
) -> tuple[Any | None, dict[str, Any]]:
    import numpy as np

    traj = np.asarray(pregrasp_traj, dtype=np.float32)
    if traj.ndim != 2 or traj.shape[0] == 0:
        return None, {"enabled": True, "success": False, "reason": "empty_pregrasp_trajectory"}
    if target_center_world is None:
        return None, {"enabled": True, "success": False, "reason": "missing_target_center_world"}

    n_arm = int(profile.n_arm)
    q_start_arm = traj[-1, :n_arm].astype(np.float32)
    selected_tool = np.asarray(selected_tool_world, dtype=np.float64)
    target_center = np.asarray(target_center_world, dtype=np.float64).reshape(3)
    tool_center_offset = selected_tool[:3, 3] - target_center
    desired_object_lift = target_center + np.asarray([0.0, 0.0, float(lift_height)], dtype=np.float64)
    target_link_position = desired_object_lift + tool_center_offset
    target_link_position[2] = max(target_link_position[2], target_center[2] + float(lift_height))

    q_lift, solve_summary = _solve_yam_scripted_bin_arm_pose(
        profile=profile,
        bundle=bundle,
        q_start_arm=q_start_arm,
        target_link_position_world=target_link_position,
    )
    summary: dict[str, Any] = {
        "enabled": True,
        "success": q_lift is not None,
        "lift_mode": "scripted_minimum_jerk_joint_space",
        "lift_height": float(lift_height),
        "lift_frames": int(lift_frames),
        "target_center_world": target_center.tolist(),
        "desired_object_lift_world": desired_object_lift.tolist(),
        "tool_minus_object_center_world_at_grasp": tool_center_offset.tolist(),
        "target_link_position_world": target_link_position.tolist(),
        "q_start_arm": q_start_arm.tolist(),
        "solve": solve_summary,
    }
    if q_lift is None:
        return None, summary
    lift = _minimum_jerk_ramp(q_start_arm, q_lift.astype(np.float32), max(2, int(lift_frames))).astype(np.float32)
    summary["q_target_arm"] = q_lift.astype(np.float32).tolist()
    summary["total_frames"] = int(lift.shape[0])
    return lift, summary


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
    stable_scene = getattr(args, "stable_scene", None)
    if bool(args.include_goal_bin):
        obstacles.extend(_goal_bin_obstacles(stable_scene))
    if stable_scene is not None:
        obstacles.extend(_source_bin_obstacles(stable_scene))
        obstacles.extend(_stable_scene_clutter_obstacles(stable_scene, margin=float(args.clutter_margin)))
    elif args.metrics_path is not None:
        obstacles.extend(_metrics_clutter_obstacles(args.metrics_path.expanduser().resolve(), margin=float(args.clutter_margin)))
    elif bool(args.include_default_clutter):
        obstacles.extend(_default_clutter_obstacles())
    return obstacles


def _grasp_to_tool_matrix(robot_cfg: dict[str, Any]) -> Any:
    import numpy as np

    transform = robot_cfg.get("grasp_to_tool_transform") or {}
    translation = [float(v) for v in transform.get("translation", [0.0, 0.0, 0.0])]
    quat_xyzw = [float(v) for v in transform.get("quaternion_xyzw", [0.0, 0.0, 0.0, 1.0])]
    return np.asarray(_matrix_from_pose_xyzw(translation, quat_xyzw), dtype=float)


def _target_center_from_info(target_info: dict[str, Any] | None) -> Any | None:
    if target_info is None:
        return None
    bounds_min = target_info.get("scaled_bounds_min")
    bounds_max = target_info.get("scaled_bounds_max")
    root_transform = target_info.get("root_transform")
    if not isinstance(bounds_min, list) or not isinstance(bounds_max, list) or root_transform is None:
        return None
    import numpy as np

    bmin = np.asarray(bounds_min, dtype=float)
    bmax = np.asarray(bounds_max, dtype=float)
    if bmin.shape != (3,) or bmax.shape != (3,):
        return None
    local_center = 0.5 * (bmin + bmax)
    target_T = np.asarray(root_transform, dtype=float)
    center = target_T @ np.asarray([local_center[0], local_center[1], local_center[2], 1.0], dtype=float)
    return center[:3]


def _parse_int_set(value: str | None) -> set[int]:
    if value is None:
        return set()
    out: set[int] = set()
    for part in str(value).split(","):
        part = part.strip()
        if not part:
            continue
        out.add(int(part))
    return out


def _apply_grasp_original_index_exclusions(
    grasps_world: Any,
    conf: Any,
    grasp_filter_summary: dict[str, Any],
    exclude_original_indices: set[int],
) -> tuple[Any, Any, dict[str, Any]]:
    import numpy as np

    if not exclude_original_indices:
        return grasps_world, conf, grasp_filter_summary
    grasps_np = np.asarray(grasps_world)
    conf_np = np.asarray(conf)
    original_indices_raw = grasp_filter_summary.get("kept_original_indices")
    if isinstance(original_indices_raw, list) and len(original_indices_raw) == len(grasps_np):
        original_indices = [int(v) for v in original_indices_raw]
    else:
        original_indices = list(range(len(grasps_np)))
    keep_positions = [
        idx
        for idx, original_idx in enumerate(original_indices)
        if int(original_idx) not in exclude_original_indices
    ]
    summary = copy.deepcopy(grasp_filter_summary)
    summary["excluded_original_indices"] = sorted(int(v) for v in exclude_original_indices)
    summary["excluded_count"] = int(len(original_indices) - len(keep_positions))
    summary["input_count_before_exclusion"] = int(len(original_indices))
    summary["kept_count_before_exclusion"] = int(len(original_indices))
    summary["kept_count"] = int(len(keep_positions))
    if not keep_positions:
        raise RuntimeError(
            "All YAM grasp candidates were excluded by --exclude_grasp_original_indices"
        )

    def _subset_list(name: str) -> None:
        values = summary.get(name)
        if isinstance(values, list) and len(values) == len(original_indices):
            summary[name] = [values[i] for i in keep_positions]

    _subset_list("kept_original_indices")
    _subset_list("kept")
    _subset_list("planning_scores")
    summary["exclusion_applied"] = True
    return grasps_np[keep_positions].astype(np.float32), conf_np[keep_positions].astype(np.float32), summary


def _filter_yam_grasps_by_aperture(
    grasps_world: Any,
    conf: Any,
    *,
    robot_cfg: dict[str, Any],
    target_center_world: Any | None,
    min_keep: int,
    min_lift_up_dot: float,
    min_tool_z: float,
    allow_filter_fallback: bool,
    max_fallback_geometry_cost: float,
) -> tuple[Any, Any, dict[str, Any]]:
    import numpy as np

    if target_center_world is None or len(grasps_world) == 0:
        return grasps_world, conf, {
            "enabled": False,
            "reason": "missing_target_center_or_empty_grasps",
        }

    grasp_to_tool = _grasp_to_tool_matrix(robot_cfg)
    center_h = np.asarray([*np.asarray(target_center_world, dtype=float).reshape(3), 1.0], dtype=float)
    desired = np.asarray(YAM_GRIPPER_CENTER_LOCAL, dtype=float)
    tol = np.asarray(YAM_GRIPPER_CENTER_TOL, dtype=float)
    scored: list[dict[str, Any]] = []
    for idx, grasp in enumerate(np.asarray(grasps_world, dtype=float)):
        tool_T = grasp @ grasp_to_tool
        local_center = (np.linalg.inv(tool_T) @ center_h)[:3]
        normalized_error = (local_center - desired) / np.maximum(tol, 1.0e-6)
        cost = float(np.linalg.norm(normalized_error))
        inside = bool(np.all(np.abs(local_center - desired) <= tol))
        tool_z_w = tool_T[:3, 2]
        lift_up_dot = float(-tool_z_w[2])
        tool_z = float(tool_T[2, 3])
        lift_ok = bool(lift_up_dot >= float(min_lift_up_dot))
        height_ok = bool(tool_z >= float(min_tool_z))
        orientation_cost = abs(lift_up_dot - YAM_PREFERRED_LIFT_UP_DOT)
        ranking_cost = cost + YAM_LIFT_ORIENTATION_WEIGHT * orientation_cost
        scored.append(
            {
                "index": int(idx),
                "confidence": float(conf[idx]),
                "object_center_in_tool": local_center.tolist(),
                "geometry_cost": cost,
                "orientation_cost": orientation_cost,
                "ranking_cost": ranking_cost,
                "inside_aperture": inside,
                "tool_position_world": tool_T[:3, 3].tolist(),
                "tool_z_axis_world": tool_z_w.tolist(),
                "lift_up_dot": lift_up_dot,
                "tool_z": tool_z,
                "lift_ok": lift_ok,
                "height_ok": height_ok,
            }
        )

    def _ranked(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(entries, key=lambda entry: (entry["ranking_cost"], -float(entry["confidence"])))

    def _extend_unique(
        base: list[dict[str, Any]],
        additions: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        kept = list(base)
        seen = {int(entry["index"]) for entry in kept}
        for entry in additions:
            if len(kept) >= int(limit):
                break
            idx = int(entry["index"])
            if idx in seen:
                continue
            kept.append(entry)
            seen.add(idx)
        return kept

    inside = [entry for entry in scored if entry["inside_aperture"]]
    dynamic_ok = [
        entry
        for entry in inside
        if bool(entry["lift_ok"]) and bool(entry["height_ok"])
    ]
    if dynamic_ok:
        keep_entries = _ranked(dynamic_ok)
        reason = "inside_aperture_lift_up_and_height"
        if bool(allow_filter_fallback) and len(keep_entries) < int(min_keep):
            # A single strict grasp can be geometrically sound but unreachable
            # for cuRobo in clutter. Keep strict grasps first, then bounded
            # backups so planning can fail over without accepting far-off poses.
            keep_entries = _extend_unique(
                keep_entries,
                _ranked(inside),
                limit=max(1, int(min_keep)),
            )
            if len(keep_entries) < int(min_keep):
                fallback_entries = [
                    entry
                    for entry in _ranked(scored)
                    if float(entry["geometry_cost"]) <= float(max_fallback_geometry_cost)
                ]
                keep_entries = _extend_unique(
                    keep_entries,
                    fallback_entries,
                    limit=max(1, int(min_keep)),
                )
            if len(keep_entries) > len(dynamic_ok):
                reason = "inside_aperture_lift_up_and_height_with_backup_candidates"
    elif inside and bool(allow_filter_fallback):
        keep_entries = _ranked(inside)
        reason = "inside_aperture_without_lift_filter_fallback"
    elif bool(allow_filter_fallback):
        fallback_entries = [
            entry
            for entry in _ranked(scored)
            if float(entry["geometry_cost"]) <= float(max_fallback_geometry_cost)
        ]
        keep_entries = fallback_entries[: max(1, int(min_keep))]
        reason = "best_geometry_fallback"
    else:
        keep_entries = []
        reason = "no_grasp_satisfies_aperture_lift_and_height"

    if bool(allow_filter_fallback) and len(keep_entries) < max(1, int(min_keep)):
        selected = {entry["index"] for entry in keep_entries}
        needed = max(1, int(min_keep)) - len(keep_entries)
        fill_entries = [
            entry
            for entry in sorted(scored, key=lambda entry: entry["geometry_cost"])
            if entry["index"] not in selected
        ][:needed]
        if fill_entries:
            keep_entries = [*keep_entries, *fill_entries]
            reason = f"{reason}_min_keep_topup"

    keep_indices = [entry["index"] for entry in keep_entries]
    order = sorted(
        range(len(keep_indices)),
        key=lambda i: (keep_entries[i]["ranking_cost"], -float(conf[keep_indices[i]])),
    )
    keep_indices = [keep_indices[i] for i in order]
    keep_entries = [keep_entries[i] for i in order]
    for entry in keep_entries:
        # plan_to_grasp orders candidates by descending "confidence".
        # For YAM, GraspGenX confidence alone often picks fingertip-edge
        # grasps that are reachable but weak in dynamic sim, so pass a
        # geometry-derived planning score while preserving true GGX
        # confidence for reporting.
        entry["planning_score"] = float(1.0 / (1.0 + entry["ranking_cost"]) + 1.0e-4 * entry["confidence"])
    return (
        np.asarray(grasps_world)[keep_indices].astype(np.float32),
        np.asarray(conf)[keep_indices].astype(np.float32),
        {
            "enabled": True,
            "reason": reason,
            "target_center_world": np.asarray(target_center_world, dtype=float).tolist(),
            "desired_object_center_in_tool": desired.tolist(),
            "tolerance": tol.tolist(),
            "min_lift_up_dot": float(min_lift_up_dot),
            "preferred_lift_up_dot": float(YAM_PREFERRED_LIFT_UP_DOT),
            "lift_orientation_weight": float(YAM_LIFT_ORIENTATION_WEIGHT),
            "min_tool_z": float(min_tool_z),
            "allow_filter_fallback": bool(allow_filter_fallback),
            "max_fallback_geometry_cost": float(max_fallback_geometry_cost),
            "input_count": int(len(scored)),
            "kept_count": int(len(keep_indices)),
            "kept_original_indices": keep_indices,
            "kept": keep_entries,
            "planning_order": "yam_aperture_side_grasp_geometry_then_confidence",
            "planning_scores": [entry["planning_score"] for entry in keep_entries],
            "best_overall": _ranked(scored)[: min(8, len(scored))],
        },
    )


def _plan_yam_to_grasp_vertical_lift(
    planner: Any,
    robot_cfg: dict[str, Any],
    grasps_world: Any,
    conf: Any,
    *,
    max_attempts: int,
    seed: int,
    robot_base_T: Any,
    force_idx: int = -1,
    rank_by_confidence: bool = False,
    candidate_original_indices: list[int] | None = None,
) -> tuple[bool, Any, int, Any | None, Any | None]:
    """Plan a YAM grasp with vertical lift in robot/world coordinates.

    The stock GraspGenX helper lifts along tool ``z``. That is acceptable for
    Franka-style top grasps, but YAM-side grasps can have tool ``z`` tilted
    strongly sideways, which turns the lift into a sideways drag. Keep the
    approach in tool coordinates, but make the lift use robot/world +Z.
    """
    import numpy as np
    import torch
    import trimesh.transformations as tra
    from curobo.types import JointState
    from e2e_grasp_demo import matrix_to_xyz_quat_wxyz

    target_link = robot_cfg["curobo"]["tool_frame"]
    default_q = robot_cfg["curobo"]["default_joint_position"]
    q_start = JointState.from_position(
        torch.tensor([default_q], device="cuda", dtype=torch.float32),
        joint_names=planner.joint_names,
    )

    g2t = robot_cfg.get("grasp_to_tool_transform", {})
    tt = g2t.get("translation", [0, 0, 0])
    qq = g2t.get("quaternion_xyzw", [0, 0, 0, 1])
    t_offset = np.eye(4)
    t_offset[:3, 3] = tt
    if not (
        abs(qq[0]) < 1.0e-9
        and abs(qq[1]) < 1.0e-9
        and abs(qq[2]) < 1.0e-9
        and abs(qq[3] - 1.0) < 1.0e-9
    ):
        t_offset[:3, :3] = tra.quaternion_matrix([qq[3], qq[0], qq[1], qq[2]])[:3, :3]

    world_robot_inv = tra.inverse_matrix(robot_base_T)
    conf_np = np.asarray(conf, dtype=np.float32)
    order = np.argsort(-conf_np)
    if force_idx >= 0 and force_idx < len(grasps_world):
        try_idxs_list = [int(force_idx)]
    else:
        try_idxs_list = [int(i) for i in order[: max(1, int(max_attempts))]]

    def _grasp_pose_dict(idx_subset: list[int]) -> Any:
        positions: list[list[float]] = []
        quats: list[list[float]] = []
        for idx in idx_subset:
            target_robot = world_robot_inv @ np.asarray(grasps_world[idx], dtype=float) @ t_offset
            p, q = matrix_to_xyz_quat_wxyz(target_robot)
            positions.append(p)
            quats.append(q)
        pos_t = torch.tensor(positions, device="cuda", dtype=torch.float32).unsqueeze(0)
        quat_t = torch.tensor(quats, device="cuda", dtype=torch.float32).unsqueeze(0)
        from curobo_compat import grasp_goals

        return grasp_goals(target_link, pos_t, quat_t)

    def _try(
        grasp_poses: Any,
        approach_offset: float,
        plan_to_grasp_flag: bool,
        plan_to_lift_flag: bool,
        lift_offset: float,
    ) -> Any:
        return planner.plan_grasp(
            grasp_poses,
            q_start,
            grasp_approach_axis="z",
            grasp_approach_offset=approach_offset,
            grasp_approach_in_tool_frame=True,
            grasp_lift_axis="z",
            grasp_lift_offset=lift_offset,
            grasp_lift_in_tool_frame=False,
            plan_approach_to_grasp=plan_to_grasp_flag,
            plan_grasp_to_lift=plan_to_lift_flag,
            disable_collision_links=[target_link],
        )

    iterate_singletons = rank_by_confidence or (force_idx >= 0)
    outer_batches = [[i] for i in try_idxs_list] if iterate_singletons else [try_idxs_list]
    result = None
    kept_idxs: list[int] = []
    attempt_log: list[dict[str, Any]] = []
    for idx_subset in outer_batches:
        kept_idxs = idx_subset
        grasp_poses = _grasp_pose_dict(idx_subset)
        strategies = [
            (-0.15, True, True, 0.20, "vertical full (a=15, lift=20)"),
            (-0.15, True, True, 0.12, "vertical full (a=15, lift=12)"),
            (-0.10, True, True, 0.20, "vertical full (a=10, lift=20)"),
            (-0.10, True, True, 0.12, "vertical full (a=10, lift=12)"),
            (-0.07, True, True, 0.20, "vertical full (a=7, lift=20)"),
            (-0.07, True, True, 0.12, "vertical full (a=7, lift=12)"),
            (-0.10, True, False, 0.20, "approach+grasp"),
            (-0.05, False, False, 0.20, "short approach"),
        ]
        for approach_offset, plan_grasp_flag, plan_lift_flag, lift_offset, _label in strategies:
            try:
                result = _try(
                    grasp_poses,
                    approach_offset,
                    plan_grasp_flag,
                    plan_lift_flag,
                    lift_offset,
                )
            except Exception:
                attempt_log.append(
                    {
                        "candidate_indices": [int(i) for i in idx_subset],
                        "candidate_original_indices": [
                            int(candidate_original_indices[i])
                            for i in idx_subset
                            if candidate_original_indices is not None and 0 <= i < len(candidate_original_indices)
                        ],
                        "label": _label,
                        "exception": True,
                    }
                )
                continue
            success_flag = result.success is not None and bool(result.success.any())
            approach_field = getattr(result, "approach_success", None)
            grasp_field = getattr(result, "grasp_success", None)
            lift_field = getattr(result, "lift_success", None)
            approach_success = approach_field is not None and bool(approach_field.any())
            grasp_success = grasp_field is not None and bool(grasp_field.any())
            lift_success = lift_field is not None and bool(lift_field.any())
            attempt_log.append(
                {
                    "candidate_indices": [int(i) for i in idx_subset],
                    "candidate_original_indices": [
                        int(candidate_original_indices[i])
                        for i in idx_subset
                        if candidate_original_indices is not None and 0 <= i < len(candidate_original_indices)
                    ],
                    "label": _label,
                    "status": str(getattr(result, "status", "<no status>")),
                    "success": bool(success_flag),
                    "approach_success": bool(approach_success),
                    "grasp_success": bool(grasp_success),
                    "lift_success": bool(lift_success),
                    "approach_offset": float(approach_offset),
                    "lift_offset": float(lift_offset),
                    "plan_grasp": bool(plan_grasp_flag),
                    "plan_lift": bool(plan_lift_flag),
                }
            )
            if success_flag:
                break
            if (
                not plan_grasp_flag
                and result is not None
                and result.approach_success is not None
                and bool(result.approach_success.any())
            ):
                break
        else:
            continue
        break
    else:
        if result is not None:
            setattr(result, "_yam_attempt_log", attempt_log)
        return False, result, -1, None, None

    if result is None:
        return False, None, -1, None, None
    setattr(result, "_yam_attempt_log", attempt_log)
    has_approach = result.approach_success is not None and bool(result.approach_success.any())
    if not has_approach:
        return False, result, -1, None, None
    chosen_in_goalset = (
        int(result.goalset_index.view(-1)[0].item())
        if result.goalset_index is not None
        else -1
    )
    target_idx = kept_idxs[chosen_in_goalset] if 0 <= chosen_in_goalset < len(kept_idxs) else -1

    def _last_idx(x: Any) -> int | None:
        if x is None:
            return None
        try:
            return int(x.view(-1)[0].item())
        except Exception:
            try:
                return int(x)
            except Exception:
                return None

    def _traj_to_np(t: Any, last_tstep: Any = None) -> Any | None:
        if t is None:
            return None
        pos = t.position.detach().cpu().numpy()
        while pos.ndim > 2:
            pos = pos[0]
        pos = pos.astype(np.float32)
        li = _last_idx(last_tstep)
        if li is not None and 0 <= li < pos.shape[0] - 1:
            pos = pos[: li + 1]
        return pos

    pre_segments = []
    for traj, last_tstep in [
        (
            result.approach_interpolated_trajectory,
            getattr(result, "approach_interpolated_last_tstep", None),
        ),
        (
            result.grasp_interpolated_trajectory,
            getattr(result, "grasp_interpolated_last_tstep", None),
        ),
    ]:
        pos = _traj_to_np(traj, last_tstep)
        if pos is not None:
            pre_segments.append(pos)
    lift_np = _traj_to_np(
        result.lift_interpolated_trajectory,
        getattr(result, "lift_interpolated_last_tstep", None),
    )
    if not pre_segments:
        return False, result, target_idx, None, None
    result._segments = {
        "approach": pre_segments[0] if len(pre_segments) >= 1 else None,
        "grasp": pre_segments[1] if len(pre_segments) >= 2 else None,
        "lift": lift_np,
    }
    return True, result, target_idx, np.concatenate(pre_segments, axis=0), lift_np


def _make_robot_config(
    graspgenx_root: Path,
    run_dir: Path,
    *,
    start_arm_joint_position: list[float] | None = None,
    start_finger_joint_position: float | None = None,
    planning_finger_joint_position: float | None = None,
    grasp_to_tool_z: float = 0.04,
) -> Path:
    start_arm = list(start_arm_joint_position or DEXTRAH_YAM_ARM_START)
    start_finger = DEXTRAH_YAM_FINGER_OPEN if start_finger_joint_position is None else float(start_finger_joint_position)
    planning_finger = start_finger if planning_finger_joint_position is None else float(planning_finger_joint_position)
    src = graspgenx_root / "end2end/robots/yam_linear.yaml"
    cfg = _load_yaml(src)
    profile_open = {
        str(name): float(value)
        for name, value in (cfg.get("gripper_open") or {}).items()
    }
    if not profile_open:
        profile_open = {"left_finger": DEXTRAH_YAM_FINGER_OPEN, "right_finger": DEXTRAH_YAM_FINGER_OPEN}
    curobo_src = (src.parent / cfg["curobo"]["robot_config"]).resolve()
    curobo_cfg = _load_yaml(curobo_src)
    kinematics = curobo_cfg.setdefault("robot_cfg", {}).setdefault("kinematics", {})
    for key in ("urdf_path", "asset_root_path"):
        value = str(kinematics.get(key) or "")
        if value.startswith("/graspgenx/"):
            kinematics[key] = str(graspgenx_root / value.removeprefix("/graspgenx/"))
    cspace = kinematics.setdefault("cspace", {})
    # Keep cuRobo's locked gripper collision state at the settled DEXTRAH
    # start width. The dynamic replay still opens to the profile width before
    # approach, but planning with the fully-open finger collision can reject
    # otherwise valid grasp goals near the table/clutter.
    cspace["default_joint_position"] = [*start_arm, planning_finger, planning_finger]
    lock = curobo_cfg["robot_cfg"]["kinematics"].setdefault("lock_joints", {})
    lock["left_finger"] = planning_finger
    lock["right_finger"] = planning_finger
    curobo_out = run_dir / "configs/yam_linear_curobo_dextrah.yml"
    _write_yaml(curobo_out, curobo_cfg)

    cfg.setdefault("curobo", {})
    cfg["curobo"]["robot_config"] = str(curobo_out)
    cfg["curobo"]["tool_frame"] = "link_6"
    cfg["curobo"]["default_joint_position"] = list(start_arm)
    # The GraspGen-X YAM gripper frame sits near the front of the sweep
    # volume.  DEXTRAH/cuRobo control URDF link_6, whose fingertip collision
    # pads enclose objects roughly 4 cm deeper along local +Z for the enlarged
    # physical-contact variant. Keep this configurable for original-size
    # legacy scenes that were authored with the unshifted frame.
    cfg["grasp_to_tool_transform"] = {
        "translation": [0.0, 0.0, float(grasp_to_tool_z)],
        "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    cfg["robot_base_pose"] = {
        "translation": list(YAM_ROBOT_BASE),
        "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    cfg["gripper_open"] = profile_open
    cfg["dextrah_start_gripper_open"] = {"left_finger": start_finger, "right_finger": start_finger}
    cfg["dextrah_planning_gripper_open"] = {"left_finger": planning_finger, "right_finger": planning_finger}
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
    assets = [
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
    ]
    if bool(args.include_goal_bin):
        goal_info = _goal_bin_info(getattr(args, "stable_scene", None))
        wall = float(goal_info["wall_thickness"])
        bottom = float(goal_info["bottom_thickness"])
        inner_x = float(goal_info["inner_size_x"])
        inner_y = float(goal_info["inner_size_y"])
        wall_h = float(goal_info["wall_height"])
        assets.append(
            {
                "id": "bin",
                "type": "procedural_bin",
                "params": {
                    "width": inner_x + 2.0 * wall,
                    "depth": inner_y + 2.0 * wall,
                    "height": wall_h + bottom,
                    "thickness": wall,
                    "angle": 0.0,
                    "use_primitives": True,
                },
                "pose": {
                    "translation": _goal_bin_center(getattr(args, "stable_scene", None)),
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                # Keep the DEXTRAH-authored bin cuboids as the only cuRobo
                # collision source so the planner and Isaac replay share the
                # same floor/wall dimensions.
                "collision": "skip",
            }
        )

    cfg = {
        "name": "dextrah_single_yam_graspgenx_curobo",
        "assets": assets,
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
    parser.add_argument(
        "--rank_grasps_by_confidence",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Plan singleton grasps in confidence order. Disabled by default for "
            "YAM data generation so cuRobo can choose among a batched reachable "
            "goalset instead of failing on one awkward top-ranked grasp at a time."
        ),
    )
    parser.add_argument(
        "--plan_task",
        choices=("pick_and_lift", "pick_and_drop_in_bin"),
        default="pick_and_lift",
        help="Post-grasp trajectory builder. pick_and_drop_in_bin appends a bin-drop segment.",
    )
    parser.add_argument("--move_to_bin_frames", type=int, default=360)
    parser.add_argument("--drop_height_above_bin", type=float, default=0.18)
    parser.add_argument(
        "--scripted_place_fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="For YAM pick_and_drop_in_bin, append a DEXTRAH scripted drop if cuRobo transport fails.",
    )
    parser.add_argument(
        "--scripted_place_mode",
        choices=("fallback", "always", "never"),
        default="fallback",
        help="For YAM pick_and_drop_in_bin, control whether bin placement is scripted.",
    )
    parser.add_argument(
        "--scripted_lift_mode",
        choices=("fallback", "always", "never"),
        default="fallback",
        help="Use a scripted vertical lift for YAM after the cuRobo grasp segment.",
    )
    parser.add_argument("--scripted_lift_height", type=float, default=0.14)
    parser.add_argument("--scripted_lift_frames", type=int, default=240)
    parser.add_argument(
        "--scripted_bin_drop_y_offset",
        type=float,
        default=0.0,
        help="Object-center Y offset from the bin center for the scripted drop target.",
    )
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
    parser.add_argument("--filter_yam_grasps_by_aperture", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--yam_grasp_filter_min_keep", type=int, default=4)
    parser.add_argument("--yam_min_lift_up_dot", type=float, default=YAM_MIN_LIFT_UP_DOT)
    parser.add_argument("--yam_min_tool_z", type=float, default=YAM_MIN_TOOL_Z)
    parser.add_argument("--yam_allow_lift_filter_fallback", action="store_true")
    parser.add_argument("--yam_max_fallback_geometry_cost", type=float, default=YAM_MAX_FALLBACK_GEOMETRY_COST)
    parser.add_argument(
        "--yam_grasp_to_tool_z",
        type=float,
        default=0.04,
        help="Local +Z offset from the GraspGen-X grasp frame to DEXTRAH/cuRobo link_6.",
    )
    parser.add_argument(
        "--planning_finger_joint_position",
        type=float,
        default=None,
        help=(
            "Optional YAM finger joint value used for cuRobo locked-finger collision checking. "
            "The replay trajectory precloses to this value before arm motion."
        ),
    )
    parser.add_argument(
        "--exclude_grasp_original_indices",
        type=str,
        default="",
        help="Comma-separated GraspGen-X candidate indices to remove before cuRobo planning.",
    )
    parser.add_argument("--sim_fps", type=int, default=60)
    parser.add_argument("--start_guard_frames", type=int, default=60)
    parser.add_argument("--close_frames", type=int, default=60)
    parser.add_argument("--hold_frames", type=int, default=60)
    parser.add_argument("--hold_after_close_frames", type=int, default=120)
    return parser.parse_args()


def _annotate_trajectory_phases(
    path: Path,
    segments: list[tuple[str, int]],
    *,
    stable_scene: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    if not segments:
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    frames = payload.get("frames")
    if not isinstance(frames, list):
        return
    idx = 0
    normalized_segments: list[dict[str, Any]] = []
    for phase, count in segments:
        count_i = max(int(count), 0)
        if count_i <= 0:
            continue
        start = idx
        end = min(idx + count_i, len(frames))
        for frame in frames[start:end]:
            if isinstance(frame, dict):
                frame["phase"] = str(phase)
        normalized_segments.append({"phase": str(phase), "start": int(start), "count": int(end - start)})
        idx = end
        if idx >= len(frames):
            break
    if idx < len(frames):
        phase = str(segments[-1][0])
        for frame in frames[idx:]:
            if isinstance(frame, dict):
                frame["phase"] = phase
        normalized_segments.append({"phase": phase, "start": int(idx), "count": int(len(frames) - idx)})
    payload["segments"] = normalized_segments
    payload["phase_source"] = "dextrah_task_segments"
    object_sequence = _single_object_sequence_from_stable_scene(
        stable_scene,
        trajectory_path=path,
        frame_count=len(frames),
        segments=normalized_segments,
    )
    if object_sequence:
        payload["object_count"] = len(object_sequence)
        payload["object_sequence"] = object_sequence
    if extra_metadata:
        payload.update(_jsonable(extra_metadata))
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")


def _single_object_sequence_from_stable_scene(
    stable_scene: dict[str, Any] | None,
    *,
    trajectory_path: Path,
    frame_count: int,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(stable_scene, dict) or frame_count <= 0:
        return []
    selected = stable_scene.get("planner_selected_object") if isinstance(stable_scene.get("planner_selected_object"), dict) else {}
    target = stable_scene.get("target") if isinstance(stable_scene.get("target"), dict) else {}
    asset = target.get("asset") if isinstance(target.get("asset"), dict) else {}
    object_id = str(
        selected.get("object_id")
        or target.get("source_object_id")
        or target.get("object_id")
        or "target"
    )
    uuid = str(asset.get("uuid") or object_id)
    name = str(asset.get("name") or asset.get("metadata_text") or uuid)
    return [
        {
            "object_id": object_id,
            "source": "single_object_graspgenx_curobo",
            "slot_idx": target.get("slot_idx"),
            "uuid": uuid,
            "name": name,
            "asset": {
                "uuid": uuid,
                "name": str(asset.get("name") or ""),
                "metadata_text": str(asset.get("metadata_text") or ""),
                "usd_path": str(asset.get("usd_path") or ""),
                "raw_object_path": str(asset.get("raw_object_path") or ""),
                "grasp_prior_path": str(asset.get("grasp_prior_path") or ""),
                "scale": asset.get("scale"),
                "xy_radius": asset.get("xy_radius"),
                "scaled_half_extents": copy.deepcopy(asset.get("scaled_half_extents")),
            },
            "trajectory_path": str(trajectory_path),
            "start_frame": 0,
            "end_frame": int(frame_count - 1),
            "end_frame_exclusive": int(frame_count),
            "frame_count": int(frame_count),
            "pick_start_frame": 0,
            "placement_end_frame": int(frame_count - 1),
            "segments": copy.deepcopy(segments),
        }
    ]


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

    from e2e_grasp_demo import collision_world_to_curobo, export_trajectory, init_planner, run_graspgen
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
    target_center_world = _target_center_from_info(target_info)
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
        planning_finger_joint_position=args.planning_finger_joint_position,
        grasp_to_tool_z=float(args.yam_grasp_to_tool_z),
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
            "target_center_world": target_center_world,
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
        if "object" in bundle.vis_meshes:
            object_mesh, _old_object_T = bundle.vis_meshes["object"]
            bundle.vis_meshes["object"] = (object_mesh, metrics_target_T.copy())
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
            "target_center_world": target_center_world,
            "target_alignment": target_alignment,
            "collision_obstacles_world": [ob.__dict__ for ob in bundle.collision_world],
        },
    )

    if bool(args.filter_yam_grasps_by_aperture):
        grasps_world, conf, grasp_filter_summary = _filter_yam_grasps_by_aperture(
            grasps_world,
            conf,
            robot_cfg=robot_cfg,
            target_center_world=target_center_world,
            min_keep=int(args.yam_grasp_filter_min_keep),
            min_lift_up_dot=float(args.yam_min_lift_up_dot),
            min_tool_z=float(args.yam_min_tool_z),
            allow_filter_fallback=bool(args.yam_allow_lift_filter_fallback),
            max_fallback_geometry_cost=float(args.yam_max_fallback_geometry_cost),
        )
        if len(grasps_world) == 0:
            raise RuntimeError("YAM aperture filtering removed all grasps")
    else:
        grasp_filter_summary = {"enabled": False, "reason": "disabled"}
    exclude_original_indices = _parse_int_set(args.exclude_grasp_original_indices)
    grasps_world, conf, grasp_filter_summary = _apply_grasp_original_index_exclusions(
        grasps_world,
        conf,
        grasp_filter_summary,
        exclude_original_indices,
    )
    candidate_original_indices_raw = grasp_filter_summary.get("kept_original_indices")
    if isinstance(candidate_original_indices_raw, list) and len(candidate_original_indices_raw) == len(grasps_world):
        candidate_original_indices = [int(v) for v in candidate_original_indices_raw]
    else:
        candidate_original_indices = list(range(len(grasps_world)))

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
    actual_conf = np.asarray(conf, dtype=np.float32).copy()
    planning_conf = actual_conf
    if bool(grasp_filter_summary.get("enabled")):
        planning_scores = grasp_filter_summary.get("planning_scores")
        if isinstance(planning_scores, list) and len(planning_scores) == len(actual_conf):
            planning_conf = np.asarray(planning_scores, dtype=np.float32)
    success, result, target_idx, pregrasp_traj, lift_traj = _plan_yam_to_grasp_vertical_lift(
        planner,
        robot_cfg,
        grasps_world,
        planning_conf,
        max_attempts=int(args.max_plan_attempts),
        seed=int(args.seed),
        robot_base_T=bundle.robot_base_T,
        force_idx=-1,
        rank_by_confidence=bool(args.rank_grasps_by_confidence),
        candidate_original_indices=candidate_original_indices,
    )
    planner_status = str(getattr(result, "status", "<no result>")) if result is not None else "<no result>"
    planning_attempts = getattr(result, "_yam_attempt_log", None) if result is not None else None

    if target_idx < 0:
        target_idx = int(np.argmax(actual_conf))
    selected_grasp_original_index = (
        int(candidate_original_indices[target_idx])
        if 0 <= int(target_idx) < len(candidate_original_indices)
        else int(target_idx)
    )

    trajectory_json: Path | None = None
    trajectory_start_summary: dict[str, Any] | None = None
    scripted_lift_summary: dict[str, Any] = {"enabled": False, "reason": "not_requested"}
    scripted_place_summary: dict[str, Any] = {"enabled": False, "reason": "not_requested"}
    planning_preclose_summary: dict[str, Any] = {"enabled": False, "reason": "not_requested"}
    if bool(success) and pregrasp_traj is not None and len(pregrasp_traj) > 0:
        selected_tool_for_script = np.asarray(grasps_world[target_idx], dtype=float) @ _grasp_to_tool_matrix(robot_cfg)
        lift_missing = lift_traj is None or len(lift_traj) == 0
        use_scripted_lift = (
            str(args.scripted_lift_mode) == "always"
            or (str(args.scripted_lift_mode) == "fallback" and lift_missing)
        )
        if use_scripted_lift:
            scripted_lift_traj, scripted_lift_summary = _make_scripted_yam_vertical_lift(
                pregrasp_traj=pregrasp_traj,
                profile=profile,
                bundle=bundle,
                target_center_world=target_center_world,
                selected_tool_world=selected_tool_for_script,
                lift_height=float(args.scripted_lift_height),
                lift_frames=int(args.scripted_lift_frames),
            )
            scripted_lift_summary["mode"] = str(args.scripted_lift_mode)
            scripted_lift_summary["replaced_curobo_lift"] = bool(not lift_missing)
            if scripted_lift_traj is not None:
                lift_traj = scripted_lift_traj
        else:
            scripted_lift_summary = {
                "enabled": False,
                "mode": str(args.scripted_lift_mode),
                "reason": "curobo_lift_available" if not lift_missing else "disabled",
            }

    if bool(success) and pregrasp_traj is not None and len(pregrasp_traj) > 0 and lift_traj is not None and len(lift_traj) > 0:
        task_name = str(args.plan_task)
        if task_name == "pick_and_drop_in_bin" and str(args.scripted_place_mode) == "always":
            task_name = "pick_and_lift"
        task = get_task(task_name)
        if hasattr(task, "MOVE_TO_BIN_FRAMES"):
            task.MOVE_TO_BIN_FRAMES = max(2, int(args.move_to_bin_frames))
        if hasattr(task, "DROP_HEIGHT_ABOVE_BIN"):
            task.DROP_HEIGHT_ABOVE_BIN = float(args.drop_height_above_bin)
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
        task_segments = list(task_result.segments)
        joint_traj, planning_preclose_summary = _apply_yam_planning_preclose_to_pick_segments(
            joint_traj,
            task_segments,
            profile=profile,
            planning_finger_joint_position=args.planning_finger_joint_position,
        )
        has_task_bin_transport = any(str(name) == "move_to_above_bin" for name, _count in task_segments)
        if (
            str(args.plan_task) == "pick_and_drop_in_bin"
            and bool(args.scripted_place_fallback)
            and str(args.scripted_place_mode) != "never"
            and (str(args.scripted_place_mode) == "always" or not has_task_bin_transport)
        ):
            joint_traj, task_segments, scripted_place_summary = _append_scripted_yam_bin_drop(
                joint_traj=joint_traj,
                segments=task_segments,
                profile=profile,
                bundle=bundle,
                target_center_world=target_center_world,
                selected_tool_world=selected_tool_for_script,
                bin_top_center_world=_goal_bin_center(stable_scene),
                move_frames=int(args.move_to_bin_frames),
                hold_frames=int(args.hold_frames),
                open_frames=int(args.close_frames),
                drop_height_above_bin=float(args.drop_height_above_bin),
                drop_y_offset=float(args.scripted_bin_drop_y_offset),
            )
            scripted_place_summary["mode"] = str(args.scripted_place_mode)
        elif str(args.plan_task) == "pick_and_drop_in_bin":
            scripted_place_summary = {
                "enabled": bool(args.scripted_place_fallback),
                "success": False,
                "mode": str(args.scripted_place_mode),
                "reason": "task_already_added_bin_transport" if has_task_bin_transport else "disabled",
            }
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
                guard_frames = max(2, int(args.start_guard_frames))
                alpha = np.linspace(0.0, 1.0, guard_frames, dtype=np.float32)[:, None]
                start_ramp = (
                    expected_start[None, :]
                    + alpha * (joint_traj[0][None, :] - expected_start[None, :])
                ).astype(np.float32)
                tail = joint_traj[1:] if joint_traj.shape[0] > 1 else np.empty((0, joint_traj.shape[1]), dtype=np.float32)
                joint_traj = np.vstack([start_ramp, tail]).astype(np.float32)
                trajectory_start_summary["start_guard_frames"] = guard_frames
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
        _annotate_trajectory_phases(
            trajectory_json,
            task_segments,
            stable_scene=stable_scene,
            extra_metadata={
                "scripted_lift": scripted_lift_summary,
                "scripted_place": scripted_place_summary,
                "planning_preclose": planning_preclose_summary,
            },
        )

    overlay_json = run_dir / "grasp_pose_overlay.json"
    grasp_to_tool = _grasp_to_tool_matrix(robot_cfg)
    tool_grasps_world = [np.asarray(grasp, dtype=float) @ grasp_to_tool for grasp in grasps_world]
    selected_tool_world = tool_grasps_world[target_idx]
    overlay_payload = {
        "status": "accepted" if bool(success) else "rejected_or_failed",
        "planner_status": planner_status,
        "selected_grasp_index": int(target_idx),
        "selected_grasp_original_index": int(selected_grasp_original_index),
        "selected_grasp_confidence": float(actual_conf[target_idx]),
        "selected_grasp_planning_score": float(planning_conf[target_idx]),
        "selected_grasp_world": grasps_world[target_idx],
        "selected_tool_world": selected_tool_world,
        "annotations": {
            "all_grasps": grasps_world,
            "tool_grasps_world": tool_grasps_world,
            "target_grasp_transform": grasps_world[target_idx],
            "target_tool_transform": selected_tool_world,
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
            "target_center_world": None if target_center_world is None else target_center_world,
            "target_alignment": target_alignment,
            "grasp_filter": grasp_filter_summary,
            "grasp_to_tool_transform": robot_cfg.get("grasp_to_tool_transform"),
            "candidate_original_indices": candidate_original_indices,
            "excluded_grasp_original_indices": sorted(exclude_original_indices),
            "table": dict(YAM_TABLE),
        },
        "trajectory_start": trajectory_start_summary,
        "trajectory_json": None if trajectory_json is None else str(trajectory_json),
        "plan_task": str(args.plan_task),
        "rank_grasps_by_confidence": bool(args.rank_grasps_by_confidence),
        "move_to_bin_frames": int(args.move_to_bin_frames),
        "drop_height_above_bin": float(args.drop_height_above_bin),
        "scripted_lift": scripted_lift_summary,
        "scripted_place": scripted_place_summary,
        "planning_preclose": planning_preclose_summary,
        "planning_attempts": planning_attempts,
    }
    _write_json(overlay_json, overlay_payload)

    summary = PlanSummary(
        status="accepted" if bool(success) and trajectory_json is not None else "rejected_or_failed",
        run_name=run_name,
        curobo_collision_aware=True,
        selected_grasp_index=int(target_idx),
        selected_grasp_confidence=float(actual_conf[target_idx]),
        num_grasps=int(len(grasps_world)),
        trajectory_json=None if trajectory_json is None else str(trajectory_json),
        grasp_pose_overlay_json=str(overlay_json),
        collision_scene_model_json=str(collision_scene_model_json),
        planner_status=planner_status,
    )
    _write_json(
        run_dir / "plan_summary.json",
        {
            **asdict(summary),
            "success": bool(success),
            "selected_grasp_original_index": int(selected_grasp_original_index),
            "trajectory_start": trajectory_start_summary,
            "target_center_world": target_center_world,
            "plan_task": str(args.plan_task),
            "rank_grasps_by_confidence": bool(args.rank_grasps_by_confidence),
            "move_to_bin_frames": int(args.move_to_bin_frames),
            "drop_height_above_bin": float(args.drop_height_above_bin),
            "scripted_place": scripted_place_summary,
            "scripted_lift": scripted_lift_summary,
            "planning_preclose": planning_preclose_summary,
            "grasp_filter": grasp_filter_summary,
            "candidate_original_indices": candidate_original_indices,
            "excluded_grasp_original_indices": sorted(exclude_original_indices),
            "planning_attempts": planning_attempts,
        },
    )
    print("DEXTRAH_YAM_GRASPGENX_CUROBO_PLAN " + json.dumps(asdict(summary), sort_keys=True), flush=True)
    print(f"results={run_dir}", flush=True)


if __name__ == "__main__":
    main()
