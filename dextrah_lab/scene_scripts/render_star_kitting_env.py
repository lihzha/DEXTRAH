#!/usr/bin/env python3
"""Render a DEXTRAH star-kitting scene in Isaac Sim.

Scene convention:
- World X is the robot/table short-axis direction.
- World Y is the table long-axis direction.
- The robot is placed at the origin on the +X side of the table, matching
  DEXTRAH's KUKA-Allegro setup where table objects sit at negative X.
- A star-shaped object starts on the negative-Y side of the table.
- A rectangular fixture with a matching star-shaped through-hole sits on the
  positive-Y side of the table. The task is to pick the star and insert it into
  the fixture.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET

from isaaclab.app import AppLauncher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=Path("/tmp/dextrah_star_kitting"))
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument(
        "--scene",
        choices=("star_kitting", "single_cube", "cube_motion"),
        default="star_kitting",
        help=(
            "Scene to render. single_cube renders a static cube task. "
            "cube_motion is kept as a legacy alias and only moves the cube with --animate_cube."
        ),
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--video_seconds", type=float, default=3.0)
    parser.add_argument("--capture_video", action="store_true", help="Capture an overview PNG sequence.")
    parser.add_argument("--sim_steps_per_frame", type=int, default=2)
    parser.add_argument(
        "--physics_dt",
        type=float,
        default=1.0 / 60.0,
        help="PhysX simulation timestep in seconds.",
    )
    parser.add_argument("--settle_steps", type=int, default=30)
    parser.add_argument("--physics_device", default="cpu", help="PhysX device used by SimulationContext.")
    parser.add_argument(
        "--robot",
        choices=("graspgenx_franka", "kuka_allegro"),
        default="graspgenx_franka",
        help="Robot asset to render in the kitting scene.",
    )
    parser.add_argument(
        "--graspgenx_root",
        type=Path,
        default=None,
        help="GraspGenX repo root used to load end2end/robots/franka_panda.yaml.",
    )
    parser.add_argument(
        "--curobo_assets_root",
        type=Path,
        default=None,
        help="cuRobo content/assets root used by GraspGenX's ${CUROBO_ASSETS} token.",
    )
    parser.add_argument(
        "--franka_urdf",
        type=Path,
        default=None,
        help="Override the Franka URDF path after loading the GraspGenX config.",
    )
    parser.add_argument(
        "--franka_render_mode",
        choices=("static_urdf_obj_meshes", "articulation_usd"),
        default=None,
        help="Render GraspGenX Franka as static URDF OBJ meshes or an Isaac Lab articulation.",
    )
    parser.add_argument(
        "--franka_usd",
        default=None,
        help="Override the actuated Franka USD/URI used to spawn the Isaac Lab articulation.",
    )
    parser.add_argument(
        "--franka_scene_yaw_deg",
        type=float,
        default=180.0,
        help="Yaw applied to the GraspGenX Franka base pose so the arm faces the DEXTRAH table.",
    )
    parser.add_argument(
        "--franka_base_z_offset",
        type=float,
        default=0.2,
        help="Vertical offset added to the GraspGenX Franka base pose.",
    )
    parser.add_argument(
        "--franka_motion",
        choices=("hold", "all_directions", "trajectory"),
        default="hold",
        help="Actuated Franka motion program. all_directions commands a deterministic arm sweep.",
    )
    parser.add_argument(
        "--franka_motion_scale",
        type=float,
        default=1.0,
        help="Scale for the actuated Franka all_directions joint target sweep.",
    )
    parser.add_argument(
        "--franka_trajectory_json",
        type=Path,
        default=None,
        help="GraspGenX/cuRobo trajectory.json used when --franka_motion trajectory.",
    )
    parser.add_argument(
        "--franka_trajectory_playback",
        choices=("target", "state"),
        default="target",
        help=(
            "Trajectory playback mode. target sends joint targets through the articulation controller; "
            "state writes exact joint states for kinematic demo replay."
        ),
    )
    parser.add_argument(
        "--franka_trajectory_object_id",
        type=str,
        default="object",
        help="Object id in trajectory frames whose pose should drive the DEXTRAH star.",
    )
    parser.add_argument(
        "--franka_trajectory_object_mode",
        choices=("trajectory", "physics"),
        default="trajectory",
        help=(
            "trajectory replays object_poses from trajectory.json; physics leaves the star under "
            "PhysX control so Franka contacts must move it dynamically."
        ),
    )
    parser.add_argument(
        "--franka_contact_proxy_mode",
        choices=("kinematic", "articulation", "off"),
        default="articulation",
        help=(
            "Contact fallback for the referenced Franka USD. kinematic adds hidden PhysX boxes that "
            "follow the finger body poses; articulation only authors hidden child colliders."
        ),
    )
    parser.add_argument(
        "--show_contact_debug",
        action="store_true",
        default=False,
        help="Show debug collision geometry for contact diagnosis.",
    )
    parser.add_argument(
        "--show_franka_contact_proxies",
        action="store_true",
        default=False,
        help="Show Franka finger contact proxy boxes even when --show_contact_debug is not set.",
    )
    parser.add_argument(
        "--show_star_collision",
        action="store_true",
        default=False,
        help="Show star convex collision pieces even when --show_contact_debug is not set.",
    )
    parser.add_argument(
        "--contact_debug_opacity",
        type=float,
        default=0.38,
        help="Preview opacity for visible contact-debug geometry.",
    )
    parser.add_argument(
        "--franka_contact_proxy_center",
        type=float,
        nargs=3,
        default=(0.0, 0.0, 0.030),
        metavar=("X", "Y", "Z"),
        help="Local center of the Franka finger proxy box, in meters.",
    )
    parser.add_argument(
        "--franka_contact_proxy_size",
        type=float,
        nargs=3,
        default=(0.020, 0.012, 0.050),
        metavar=("X", "Y", "Z"),
        help="Local size of the Franka finger proxy box, in meters.",
    )
    parser.add_argument(
        "--franka_contact_proxy_contact_offset",
        type=float,
        default=None,
        help="Optional PhysX contact offset for Franka finger proxy colliders.",
    )
    parser.add_argument(
        "--star_collision_contact_offset",
        type=float,
        default=None,
        help="Optional PhysX contact offset for star collision pieces.",
    )
    parser.add_argument(
        "--collision_rest_offset",
        type=float,
        default=None,
        help="Optional PhysX rest offset applied to debugged star/proxy contact colliders.",
    )
    parser.add_argument(
        "--franka_max_depenetration_velocity",
        type=float,
        default=5.0,
        help="Maximum depenetration velocity for Franka articulation rigid bodies.",
    )
    parser.add_argument(
        "--franka_solver_position_iterations",
        type=int,
        default=8,
        help="Franka articulation solver position iteration count.",
    )
    parser.add_argument(
        "--franka_solver_velocity_iterations",
        type=int,
        default=0,
        help="Franka articulation solver velocity iteration count.",
    )
    parser.add_argument(
        "--star_max_depenetration_velocity",
        type=float,
        default=None,
        help="Optional maximum depenetration velocity for the dynamic star rigid body.",
    )
    parser.add_argument(
        "--star_solver_position_iterations",
        type=int,
        default=None,
        help="Optional solver position iteration count for the dynamic star rigid body.",
    )
    parser.add_argument(
        "--star_solver_velocity_iterations",
        type=int,
        default=None,
        help="Optional solver velocity iteration count for the dynamic star rigid body.",
    )
    parser.add_argument(
        "--franka_grasp_constraint_mode",
        choices=("off", "attach_on_close"),
        default="off",
        help=(
            "Debug-only grasp assist. Leave this off for faithful physics renders where failures remain failures."
        ),
    )
    parser.add_argument(
        "--franka_grasp_constraint_close_threshold",
        type=float,
        default=0.012,
        help="Maximum actual finger joint opening, in meters, before attach_on_close may create the grasp constraint.",
    )
    parser.add_argument(
        "--franka_grasp_constraint_xy_threshold",
        type=float,
        default=0.050,
        help="Maximum XY distance between finger midpoint and star center before attach_on_close may fire.",
    )
    parser.add_argument(
        "--franka_grasp_constraint_z_threshold",
        type=float,
        default=0.080,
        help="Maximum vertical offset between finger midpoint and star center before attach_on_close may fire.",
    )
    parser.add_argument("--star_outer_radius", type=float, default=0.032)
    parser.add_argument("--star_inner_radius", type=float, default=0.0145)
    parser.add_argument("--star_thickness", type=float, default=0.040)
    parser.add_argument(
        "--show_grasp_candidates",
        action="store_true",
        default=False,
        help="Render GraspGenX candidate frames from trajectory annotations without changing the plan.",
    )
    parser.add_argument(
        "--max_grasp_candidates",
        type=int,
        default=24,
        help=(
            "Maximum number of grasp candidates to visualize when --show_grasp_candidates is set. "
            "Use a value at least as large as the source count to show every candidate."
        ),
    )
    parser.add_argument(
        "--grasp_candidate_axis_length",
        type=float,
        default=0.045,
        help="Axis triad length, in meters, for visualized grasp candidates.",
    )
    parser.add_argument(
        "--grasp_candidate_axis_thickness",
        type=float,
        default=0.004,
        help="Axis triad thickness, in meters, for visualized grasp candidates.",
    )
    parser.add_argument("--fixture_size_x", type=float, default=0.18)
    parser.add_argument("--fixture_size_y", type=float, default=0.18)
    parser.add_argument("--fixture_thickness", type=float, default=0.060)
    parser.add_argument("--fixture_clearance", type=float, default=0.006)
    parser.add_argument("--star_start_yaw_deg", type=float, default=-24.0)
    parser.add_argument("--fixture_yaw_deg", type=float, default=18.0)
    parser.add_argument("--cube_size", type=float, default=0.06)
    parser.add_argument("--cube_start_x", type=float, default=-0.55)
    parser.add_argument("--cube_start_y", type=float, default=0.10)
    parser.add_argument("--cube_forward_travel", type=float, default=-0.14)
    parser.add_argument("--cube_lateral_disturbance", type=float, default=0.08)
    parser.add_argument("--cube_vertical_disturbance", type=float, default=0.035)
    parser.add_argument("--cube_yaw_disturbance_deg", type=float, default=55.0)
    parser.add_argument(
        "--animate_cube",
        action="store_true",
        default=False,
        help="Opt into the legacy keyframed cube disturbance visualization.",
    )
    parser.add_argument(
        "--dynamic_star",
        dest="dynamic_star",
        action="store_true",
        default=True,
        help="Spawn the star as a rigid body. Enabled by default.",
    )
    parser.add_argument(
        "--static_star",
        dest="dynamic_star",
        action="store_false",
        help="Keep the star fixed for inspection renders.",
    )
    parser.add_argument(
        "--view",
        choices=("overview", "robot_side", "topdown", "pickup_close", "fixture_close"),
        default="overview",
    )
    AppLauncher.add_app_launcher_args(parser)
    return parser.parse_args()


args_cli = parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import omni.usd  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
import torch  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg  # noqa: E402
from isaaclab.assets.articulation import ArticulationCfg  # noqa: E402
from isaaclab.sensors.camera import TiledCamera, TiledCameraCfg  # noqa: E402
from isaaclab.sim import PhysxCfg, SimulationCfg  # noqa: E402
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg  # noqa: E402
from isaaclab.utils.assets import ISAACLAB_NUCLEUS_DIR  # noqa: E402
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

try:
    from isaacsim.core.utils.stage import create_new_stage, update_stage
except Exception:  # Isaac Sim 4.x fallback namespace
    from omni.isaac.core.utils.stage import create_new_stage, update_stage  # type: ignore


Color = tuple[float, float, float]
Point2 = tuple[float, float]


@dataclass(frozen=True)
class RobotSpec:
    name: str
    usd_path: Path | str | None
    source: str
    base_translation: tuple[float, float, float]
    base_quaternion_xyzw: tuple[float, float, float, float]
    render_mode: str
    source_config: Path | None = None
    urdf_path: Path | None = None
    asset_root_path: Path | None = None
    default_joint_position: list[float] | None = None
    joint_names: list[str] | None = None
    joint_positions: dict[str, float] | None = None
    source_base_translation: tuple[float, float, float] | None = None
    source_base_quaternion_xyzw: tuple[float, float, float, float] | None = None
    scene_yaw_deg: float | None = None
    base_z_offset: float = 0.0
    actuator_config: dict[str, dict[str, object]] | None = None


@dataclass(frozen=True)
class UrdfMesh:
    filename: Path
    origin_xyz: tuple[float, float, float]
    origin_rpy: tuple[float, float, float]


@dataclass(frozen=True)
class UrdfJoint:
    name: str
    joint_type: str
    parent: str
    child: str
    origin_xyz: tuple[float, float, float]
    origin_rpy: tuple[float, float, float]
    axis: tuple[float, float, float]


def _log(message: str) -> None:
    print(f"[star-kitting] {message}", flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_git_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(128).startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def _set_xform(
    prim: Usd.Prim,
    translate: Iterable[float],
    scale: Iterable[float] | None = None,
    rotate_xyz_deg: Iterable[float] | None = None,
    rotate_quat_xyzw: Iterable[float] | None = None,
) -> None:
    if rotate_xyz_deg is not None and rotate_quat_xyzw is not None:
        raise ValueError("Use either rotate_xyz_deg or rotate_quat_xyzw, not both")
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in translate]))
    if rotate_xyz_deg is not None:
        xformable.AddRotateXYZOp().Set(Gf.Vec3f(*[float(v) for v in rotate_xyz_deg]))
    if rotate_quat_xyzw is not None:
        qx, qy, qz, qw = [float(v) for v in rotate_quat_xyzw]
        xformable.AddOrientOp().Set(Gf.Quatf(qw, qx, qy, qz))
    if scale is not None:
        xformable.AddScaleOp().Set(Gf.Vec3f(*[float(v) for v in scale]))


def _material(
    stage: Usd.Stage,
    path: str,
    color: Color,
    roughness: float = 0.72,
    opacity: float = 1.0,
) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    if opacity < 1.0:
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _bind(prim: Usd.Prim, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def _set_schema_float_attr(api: object, prim: Usd.Prim, method_name: str, attr_name: str, value: float | None) -> None:
    if value is None:
        return
    try:
        method = getattr(api, method_name)
        method().Set(float(value))
        return
    except Exception:
        pass
    try:
        prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float).Set(float(value))
    except Exception:
        pass


def _set_schema_int_attr(api: object, prim: Usd.Prim, method_name: str, attr_name: str, value: int | None) -> None:
    if value is None:
        return
    try:
        method = getattr(api, method_name)
        method().Set(int(value))
        return
    except Exception:
        pass
    try:
        prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Int).Set(int(value))
    except Exception:
        pass


def _add_box(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: UsdShade.Material,
    *,
    collision: bool = True,
    visible: bool = True,
    contact_offset: float | None = None,
    rest_offset: float | None = None,
) -> Usd.Prim:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    _set_xform(prim, center, size)
    _bind(prim, mat)
    if not visible:
        UsdGeom.Imageable(prim).MakeInvisible()
    if collision:
        _apply_collision(prim, approximation="box", contact_offset=contact_offset, rest_offset=rest_offset)
    return prim


def _as_matrix4(value: object) -> list[list[float]] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    matrix: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != 4:
            return None
        try:
            matrix.append([float(v) for v in row])
        except (TypeError, ValueError):
            return None
    return matrix


def _transform_distance(a: list[list[float]], b: list[list[float]]) -> float:
    return math.sqrt(sum((float(a[r][c]) - float(b[r][c])) ** 2 for r in range(4) for c in range(4)))


def _select_grasp_candidate_indices(
    grasps: list[list[list[float]]],
    target_grasp: list[list[float]] | None,
    max_count: int,
) -> list[int]:
    budget = max(0, int(max_count))
    if not grasps or budget <= 0:
        return []
    selected: list[int] = []
    target_idx = None
    if target_grasp is not None:
        distances = [_transform_distance(grasp, target_grasp) for grasp in grasps]
        target_idx = int(min(range(len(distances)), key=distances.__getitem__))
        selected.append(target_idx)

    if budget >= len(grasps):
        return selected + [idx for idx in range(len(grasps)) if idx not in selected]

    remaining_budget = max(0, budget - len(selected))
    if remaining_budget <= 0:
        return selected
    if remaining_budget == 1:
        candidates = [0]
    else:
        candidates = [
            int(round(float(idx) * float(len(grasps) - 1) / float(remaining_budget - 1)))
            for idx in range(remaining_budget)
        ]
    for idx in candidates:
        if idx not in selected:
            selected.append(idx)
    if len(selected) < budget:
        for idx in range(len(grasps)):
            if idx not in selected:
                selected.append(idx)
                if len(selected) >= budget:
                    break
    return selected[:budget]


def _grasp_orientation_label(transform: list[list[float]]) -> str:
    z_axis_z = float(transform[2][2])
    if z_axis_z <= -0.8:
        return "top_down"
    if z_axis_z >= 0.8:
        return "bottom_up"
    if abs(z_axis_z) <= 0.5:
        return "side_or_oblique"
    return "steep_oblique"


def _add_local_axis_box(
    stage: Usd.Stage,
    path: str,
    axis: str,
    length: float,
    thickness: float,
    mat: UsdShade.Material,
) -> None:
    half = 0.5 * float(length)
    t = float(thickness)
    if axis == "x":
        center = (half, 0.0, 0.0)
        size = (float(length), t, t)
    elif axis == "y":
        center = (0.0, half, 0.0)
        size = (t, float(length), t)
    elif axis == "z":
        center = (0.0, 0.0, half)
        size = (t, t, float(length))
    else:
        raise ValueError(f"Unsupported axis: {axis}")
    _add_box(stage, path, center, size, mat, collision=False, visible=True)


def _add_grasp_candidate_markers(
    stage: Usd.Stage,
    trajectory: dict[str, object] | None,
    *,
    max_count: int,
    axis_length: float,
    axis_thickness: float,
    x_mat: UsdShade.Material,
    y_mat: UsdShade.Material,
    z_mat: UsdShade.Material,
    target_mat: UsdShade.Material,
) -> dict[str, object]:
    if trajectory is None:
        return {"enabled": False, "reason": "missing_trajectory"}
    annotations = trajectory.get("annotations")
    if not isinstance(annotations, dict):
        return {"enabled": False, "reason": "missing_annotations"}
    raw_grasps = annotations.get("all_grasps")
    if not isinstance(raw_grasps, list):
        return {"enabled": False, "reason": "missing_all_grasps"}
    grasps = [matrix for item in raw_grasps if (matrix := _as_matrix4(item)) is not None]
    target_grasp = _as_matrix4(annotations.get("target_grasp_transform"))
    if not grasps:
        return {"enabled": False, "reason": "empty_all_grasps"}

    source_counts_by_label: dict[str, int] = {}
    for grasp in grasps:
        label = _grasp_orientation_label(grasp)
        source_counts_by_label[label] = source_counts_by_label.get(label, 0) + 1

    root_path = "/World/GraspCandidates"
    UsdGeom.Xform.Define(stage, root_path)
    selected_indices = _select_grasp_candidate_indices(grasps, target_grasp, max_count)
    target_idx = None
    if target_grasp is not None:
        distances = [_transform_distance(grasp, target_grasp) for grasp in grasps]
        target_idx = int(min(range(len(distances)), key=distances.__getitem__))
        if target_idx not in selected_indices:
            selected_indices = [target_idx] + selected_indices[:-1]

    markers: list[dict[str, object]] = []
    for marker_idx, grasp_idx in enumerate(selected_indices):
        transform = grasps[grasp_idx]
        marker_root_path = f"{root_path}/g_{marker_idx:03d}_src_{grasp_idx:03d}"
        root = UsdGeom.Xform.Define(stage, marker_root_path).GetPrim()
        pos = (float(transform[0][3]), float(transform[1][3]), float(transform[2][3]))
        quat = _quat_xyzw_from_matrix(transform)
        _set_xform(root, pos, rotate_quat_xyzw=quat)
        is_target = target_idx is not None and grasp_idx == target_idx
        length = float(axis_length) * (1.35 if is_target else 1.0)
        thickness = float(axis_thickness) * (1.45 if is_target else 1.0)
        _add_local_axis_box(stage, f"{marker_root_path}/x_axis", "x", length, thickness, x_mat)
        _add_local_axis_box(stage, f"{marker_root_path}/y_axis", "y", length, thickness, y_mat)
        _add_local_axis_box(stage, f"{marker_root_path}/z_axis", "z", length, thickness, z_mat)
        if is_target:
            _add_box(
                stage,
                f"{marker_root_path}/target_center",
                (0.0, 0.0, 0.0),
                (thickness * 2.5, thickness * 2.5, thickness * 2.5),
                target_mat,
                collision=False,
                visible=True,
            )
        markers.append(
            {
                "marker_path": marker_root_path,
                "source_index": int(grasp_idx),
                "is_target": bool(is_target),
                "position_w": [float(pos[0]), float(pos[1]), float(pos[2])],
                "z_axis_z": float(transform[2][2]),
                "orientation_label": _grasp_orientation_label(transform),
            }
        )

    counts_by_label: dict[str, int] = {}
    for marker in markers:
        label = str(marker["orientation_label"])
        counts_by_label[label] = counts_by_label.get(label, 0) + 1
    return {
        "enabled": True,
        "root_path": root_path,
        "source_count": len(grasps),
        "source_counts_by_orientation_label": source_counts_by_label,
        "visualized_count": len(markers),
        "target_source_index": target_idx,
        "selection": "target plus evenly sampled candidates, or all source candidates when max_count covers them; no planning filter",
        "counts_by_orientation_label": counts_by_label,
        "markers": markers,
    }


def _apply_collision(
    prim: Usd.Prim,
    *,
    approximation: str = "none",
    contact_offset: float | None = None,
    rest_offset: float | None = None,
) -> None:
    UsdPhysics.CollisionAPI.Apply(prim)
    mesh_collision_api_cls = getattr(UsdPhysics, "MeshCollisionAPI", None)
    if mesh_collision_api_cls is not None:
        try:
            mesh_collision_api = mesh_collision_api_cls.Apply(prim)
            mesh_collision_api.CreateApproximationAttr().Set(str(approximation))
        except Exception:
            pass
    try:
        physx_api = PhysxSchema.PhysxCollisionAPI.Apply(prim)
        _set_schema_float_attr(
            physx_api,
            prim,
            "CreateContactOffsetAttr",
            "physxCollision:contactOffset",
            contact_offset,
        )
        _set_schema_float_attr(
            physx_api,
            prim,
            "CreateRestOffsetAttr",
            "physxCollision:restOffset",
            rest_offset,
        )
    except Exception:
        pass


def _make_rigid_body(
    prim: Usd.Prim,
    *,
    density: float,
    max_depenetration_velocity: float | None = None,
    solver_position_iterations: int | None = None,
    solver_velocity_iterations: int | None = None,
) -> None:
    rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
    try:
        rb_api.CreateRigidBodyEnabledAttr(True)
        rb_api.CreateStartsAsleepAttr(False)
    except Exception:
        pass
    if (
        max_depenetration_velocity is not None
        or solver_position_iterations is not None
        or solver_velocity_iterations is not None
    ):
        try:
            physx_rb_api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
            _set_schema_float_attr(
                physx_rb_api,
                prim,
                "CreateMaxDepenetrationVelocityAttr",
                "physxRigidBody:maxDepenetrationVelocity",
                max_depenetration_velocity,
            )
            _set_schema_int_attr(
                physx_rb_api,
                prim,
                "CreateSolverPositionIterationCountAttr",
                "physxRigidBody:solverPositionIterationCount",
                solver_position_iterations,
            )
            _set_schema_int_attr(
                physx_rb_api,
                prim,
                "CreateSolverVelocityIterationCountAttr",
                "physxRigidBody:solverVelocityIterationCount",
                solver_velocity_iterations,
            )
        except Exception:
            pass
    mass_api = UsdPhysics.MassAPI.Apply(prim)
    mass_api.CreateDensityAttr(float(density))


def _create_sim_context():
    _log(f"creating SimulationContext on physics_device={args_cli.physics_device}")
    physx_cfg_kwargs: dict[str, object] = {
        "bounce_threshold_velocity": 0.2,
        "gpu_max_rigid_patch_count": 4 * 5 * 2**15,
    }
    if int(args_cli.franka_solver_velocity_iterations) > 0:
        physx_cfg_kwargs["min_velocity_iteration_count"] = max(
            0,
            int(args_cli.franka_solver_velocity_iterations),
        )
    sim_cfg = SimulationCfg(
        dt=float(args_cli.physics_dt),
        render_interval=1,
        device=str(args_cli.physics_device),
        physics_prim_path="/World/physicsScene",
        physics_material=RigidBodyMaterialCfg(static_friction=1.0, dynamic_friction=1.0),
        physx=PhysxCfg(**physx_cfg_kwargs),
    )
    return sim_utils.SimulationContext(sim_cfg)


def _path_from_arg_or_env(
    arg_value: Path | None,
    env_names: Iterable[str],
    candidates: Iterable[Path],
    *,
    required_file: Path | None = None,
) -> Path | None:
    paths: list[Path] = []
    if arg_value is not None:
        paths.append(arg_value)
    for env_name in env_names:
        value = os.environ.get(env_name)
        if value:
            paths.append(Path(value))
    paths.extend(candidates)

    for path in paths:
        expanded = path.expanduser()
        if required_file is None:
            if expanded.exists():
                return expanded.resolve()
        elif (expanded / required_file).is_file():
            return expanded.resolve()
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            f"PyYAML is required to load GraspGenX robot config {path}. "
            "Install PyYAML in the Isaac Lab environment or pass a pre-resolved --franka_urdf."
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in GraspGenX robot config: {path}")
    return data


def _resolve_graspgenx_root() -> Path:
    root = _path_from_arg_or_env(
        args_cli.graspgenx_root,
        ("GRASPGENX_ROOT", "GRASPGENX_REPO"),
        (
            Path("/graspgenx"),
            _repo_root().parent / "graspgenx",
        ),
        required_file=Path("end2end/robots/franka_panda.yaml"),
    )
    if root is None:
        raise FileNotFoundError(
            "Could not find GraspGenX root containing end2end/robots/franka_panda.yaml. "
            "Pass --graspgenx_root or set GRASPGENX_ROOT."
        )
    return root


def _resolve_curobo_assets_root(graspgenx_root: Path) -> Path:
    candidates = [
        Path("/curobo_assets"),
        Path("/curobo/curobo/content/assets"),
        graspgenx_root / "ext/curobo/curobo/content/assets",
        _repo_root().parent / "curobo/curobo/content/assets",
    ]
    override = os.environ.get("GRASPGENX_CUROBO_DIR")
    if override:
        candidates.insert(0, Path(override) / "curobo/content/assets")
    root = _path_from_arg_or_env(
        args_cli.curobo_assets_root,
        ("CUROBO_ASSETS_ROOT", "CUROBO_ASSETS"),
        candidates,
        required_file=Path("robot/franka_description/franka_panda.urdf"),
    )
    if root is None:
        raise FileNotFoundError(
            "Could not find cuRobo assets root containing robot/franka_description/franka_panda.urdf. "
            "Pass --curobo_assets_root or set CUROBO_ASSETS_ROOT."
        )
    return root


def _expand_graspgenx_path(value: str | Path, *, graspgenx_root: Path, curobo_assets_root: Path) -> Path:
    raw = str(value)
    expanded = (
        raw.replace("${CUROBO_ASSETS}", str(curobo_assets_root))
        .replace("${REPO}", str(graspgenx_root))
        .replace("${E2E}", str(graspgenx_root / "end2end"))
    )
    path = Path(expanded).expanduser()
    if not path.is_absolute():
        path = graspgenx_root / path
    return path.resolve()


def _as_float_tuple(value: Any, *, length: int, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{field_name} must be a sequence of {length} numbers")
    return tuple(float(v) for v in value)


Matrix4 = list[list[float]]


def _mat_identity() -> Matrix4:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_mul(a: Matrix4, b: Matrix4) -> Matrix4:
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _mat_translation(xyz: Iterable[float]) -> Matrix4:
    m = _mat_identity()
    x, y, z = [float(v) for v in xyz]
    m[0][3] = x
    m[1][3] = y
    m[2][3] = z
    return m


def _mat_rot_x(angle: float) -> Matrix4:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_rot_y(angle: float) -> Matrix4:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_rot_z(angle: float) -> Matrix4:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_from_xyz_rpy(xyz: Iterable[float], rpy: Iterable[float]) -> Matrix4:
    roll, pitch, yaw = [float(v) for v in rpy]
    rotation = _mat_mul(_mat_mul(_mat_rot_z(yaw), _mat_rot_y(pitch)), _mat_rot_x(roll))
    return _mat_mul(_mat_translation(xyz), rotation)


def _mat_from_quat_xyzw(quat_xyzw: Iterable[float]) -> Matrix4:
    x, y, z, w = [float(v) for v in quat_xyzw]
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm <= 1.0e-12:
        return _mat_identity()
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w), 0.0],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w), 0.0],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y), 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _normalize_quat_xyzw(quat_xyzw: Iterable[float]) -> tuple[float, float, float, float]:
    x, y, z, w = [float(v) for v in quat_xyzw]
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm <= 1.0e-12:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / norm, y / norm, z / norm, w / norm)


def _quat_xyzw_mul(
    lhs: Iterable[float],
    rhs: Iterable[float],
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = _normalize_quat_xyzw(lhs)
    bx, by, bz, bw = _normalize_quat_xyzw(rhs)
    return _normalize_quat_xyzw(
        (
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        )
    )


def _yaw_quat_xyzw(yaw_deg: float) -> tuple[float, float, float, float]:
    half = 0.5 * math.radians(float(yaw_deg))
    return (0.0, 0.0, math.sin(half), math.cos(half))


def _quat_xyzw_to_wxyz(quat_xyzw: Iterable[float]) -> tuple[float, float, float, float]:
    x, y, z, w = _normalize_quat_xyzw(quat_xyzw)
    return (w, x, y, z)


def _quat_wxyz_to_xyzw(quat_wxyz: Iterable[float]) -> tuple[float, float, float, float]:
    w, x, y, z = [float(v) for v in quat_wxyz]
    return _normalize_quat_xyzw((x, y, z, w))


def _mat_axis_angle(axis: Iterable[float], angle: float) -> Matrix4:
    ax, ay, az = [float(v) for v in axis]
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if norm <= 1.0e-12:
        return _mat_identity()
    ax, ay, az = ax / norm, ay / norm, az / norm
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    return [
        [t * ax * ax + c, t * ax * ay - s * az, t * ax * az + s * ay, 0.0],
        [t * ax * ay + s * az, t * ay * ay + c, t * ay * az - s * ax, 0.0],
        [t * ax * az - s * ay, t * ay * az + s * ax, t * az * az + c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_apply_point(m: Matrix4, p: Iterable[float]) -> tuple[float, float, float]:
    x, y, z = [float(v) for v in p]
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
    )


def _mat_apply_vector(m: Matrix4, v: Iterable[float]) -> tuple[float, float, float]:
    x, y, z = [float(value) for value in v]
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z,
    )


def _joint_motion_matrix(joint: UrdfJoint, joint_positions: dict[str, float]) -> Matrix4:
    q = float(joint_positions.get(joint.name, 0.0))
    if joint.joint_type in ("revolute", "continuous"):
        return _mat_axis_angle(joint.axis, q)
    if joint.joint_type == "prismatic":
        return _mat_translation(tuple(q * float(v) for v in joint.axis))
    return _mat_identity()


def _parse_float_attr(element: ET.Element | None, attr: str, default: str) -> tuple[float, float, float]:
    value = default if element is None else element.attrib.get(attr, default)
    parts = [float(v) for v in value.split()]
    if len(parts) != 3:
        raise ValueError(f"Expected 3 floats for URDF {attr}, got {value!r}")
    return (parts[0], parts[1], parts[2])


def _parse_urdf_robot(urdf_path: Path) -> tuple[dict[str, list[UrdfMesh]], list[UrdfJoint]]:
    tree = ET.parse(urdf_path)
    root = tree.getroot()
    asset_root = urdf_path.parent

    link_meshes: dict[str, list[UrdfMesh]] = {}
    for link in root.findall("link"):
        link_name = link.attrib["name"]
        meshes: list[UrdfMesh] = []
        for collision in link.findall("collision"):
            mesh_element = collision.find("geometry/mesh")
            if mesh_element is None or "filename" not in mesh_element.attrib:
                continue
            origin = collision.find("origin")
            meshes.append(
                UrdfMesh(
                    filename=(asset_root / mesh_element.attrib["filename"]).resolve(),
                    origin_xyz=_parse_float_attr(origin, "xyz", "0 0 0"),
                    origin_rpy=_parse_float_attr(origin, "rpy", "0 0 0"),
                )
            )
        if meshes:
            link_meshes[link_name] = meshes

    joints: list[UrdfJoint] = []
    for joint in root.findall("joint"):
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is None or child is None:
            continue
        origin = joint.find("origin")
        axis = joint.find("axis")
        joints.append(
            UrdfJoint(
                name=joint.attrib["name"],
                joint_type=joint.attrib.get("type", "fixed"),
                parent=parent.attrib["link"],
                child=child.attrib["link"],
                origin_xyz=_parse_float_attr(origin, "xyz", "0 0 0"),
                origin_rpy=_parse_float_attr(origin, "rpy", "0 0 0"),
                axis=_parse_float_attr(axis, "xyz", "0 0 1"),
            )
        )
    return link_meshes, joints


def _compute_link_transforms(joints: list[UrdfJoint], robot: RobotSpec) -> dict[str, Matrix4]:
    children = {joint.child for joint in joints}
    parents = {joint.parent for joint in joints}
    roots = sorted(parents - children)
    root_link = roots[0] if roots else "base_link"
    base = _mat_mul(_mat_translation(robot.base_translation), _mat_from_quat_xyzw(robot.base_quaternion_xyzw))
    transforms: dict[str, Matrix4] = {root_link: base}
    pending = list(joints)
    while pending:
        next_pending: list[UrdfJoint] = []
        progressed = False
        for joint in pending:
            parent_transform = transforms.get(joint.parent)
            if parent_transform is None:
                next_pending.append(joint)
                continue
            joint_origin = _mat_from_xyz_rpy(joint.origin_xyz, joint.origin_rpy)
            child_transform = _mat_mul(
                _mat_mul(parent_transform, joint_origin),
                _joint_motion_matrix(joint, robot.joint_positions or {}),
            )
            transforms[joint.child] = child_transform
            progressed = True
        if not progressed:
            unresolved = ", ".join(joint.name for joint in next_pending)
            raise RuntimeError(f"Could not resolve URDF joint chain: {unresolved}")
        pending = next_pending
    return transforms


def _load_obj_mesh(path: Path) -> tuple[list[tuple[float, float, float]], list[int], list[int]]:
    vertices: list[tuple[float, float, float]] = []
    face_counts: list[int] = []
    face_indices: list[int] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z, *_ = line.split()
                vertices.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                refs = line.split()[1:]
                if len(refs) < 3:
                    continue
                face_counts.append(len(refs))
                for ref in refs:
                    idx = int(ref.split("/")[0])
                    if idx < 0:
                        idx = len(vertices) + idx + 1
                    face_indices.append(idx - 1)
    if not vertices or not face_counts:
        raise ValueError(f"OBJ mesh has no vertices/faces: {path}")
    return vertices, face_counts, face_indices


def _add_obj_mesh(
    stage: Usd.Stage,
    path: str,
    obj_path: Path,
    transform: Matrix4,
    mat: UsdShade.Material,
) -> Usd.Prim:
    vertices, face_counts, face_indices = _load_obj_mesh(obj_path)
    points = [Gf.Vec3f(*_mat_apply_point(transform, vertex)) for vertex in vertices]
    prim = _add_mesh(
        stage,
        path,
        points,
        face_counts,
        face_indices,
        mat,
        collision=False,
        visible=True,
    )
    return prim


def _resolve_graspgenx_franka_robot(output_dir: Path) -> RobotSpec:
    _ = output_dir
    _log("resolving GraspGenX Franka robot config")
    graspgenx_root = _resolve_graspgenx_root()
    _log(f"resolved GraspGenX root: {graspgenx_root}")
    cfg_path = graspgenx_root / "end2end/robots/franka_panda.yaml"
    cfg = _load_yaml(cfg_path)
    _log(f"loaded GraspGenX Franka config: {cfg_path}")
    curobo_assets_root = _resolve_curobo_assets_root(graspgenx_root)
    _log(f"resolved cuRobo assets root: {curobo_assets_root}")

    urdf_path = args_cli.franka_urdf.expanduser().resolve() if args_cli.franka_urdf else None
    if urdf_path is None:
        urdf_path = _expand_graspgenx_path(
            str(cfg["urdf_path"]),
            graspgenx_root=graspgenx_root,
            curobo_assets_root=curobo_assets_root,
        )
    asset_root = _expand_graspgenx_path(
        str(cfg.get("asset_root_path", urdf_path.parent)),
        graspgenx_root=graspgenx_root,
        curobo_assets_root=curobo_assets_root,
    )

    base_pose = cfg.get("robot_base_pose", {})
    source_base_translation = _as_float_tuple(
        base_pose.get("translation", [0.0, 0.0, 0.0]),
        length=3,
        field_name="robot_base_pose.translation",
    )
    franka_base_z_offset = float(args_cli.franka_base_z_offset)
    base_translation = (
        float(source_base_translation[0]),
        float(source_base_translation[1]),
        float(source_base_translation[2]) + franka_base_z_offset,
    )
    base_quat = _as_float_tuple(
        base_pose.get("quaternion_xyzw", [0.0, 0.0, 0.0, 1.0]),
        length=4,
        field_name="robot_base_pose.quaternion_xyzw",
    )

    curobo_cfg = cfg.get("curobo", {})
    default_joint_position = None
    if isinstance(curobo_cfg, dict) and "default_joint_position" in curobo_cfg:
        default_joint_position = [float(v) for v in curobo_cfg["default_joint_position"]]
    arm_joint_names = [
        "panda_joint1",
        "panda_joint2",
        "panda_joint3",
        "panda_joint4",
        "panda_joint5",
        "panda_joint6",
        "panda_joint7",
    ]
    finger_joint_names = ["panda_finger_joint1", "panda_finger_joint2"]
    joint_names = arm_joint_names + finger_joint_names
    joint_positions = dict(zip(arm_joint_names, default_joint_position or [0.0] * len(arm_joint_names)))
    joint_positions["panda_finger_joint1"] = 0.04
    joint_positions["panda_finger_joint2"] = 0.04

    render_mode = str(
        args_cli.franka_render_mode
        or ("static_urdf_obj_meshes" if args_cli.scene == "cube_motion" else "articulation_usd")
    )
    if render_mode == "static_urdf_obj_meshes":
        return RobotSpec(
            name="graspgenx_franka_panda",
            usd_path=None,
            source="GraspGenX end2end/robots/franka_panda.yaml",
            source_config=cfg_path,
            urdf_path=urdf_path,
            asset_root_path=asset_root,
            base_translation=base_translation,  # type: ignore[arg-type]
            base_quaternion_xyzw=base_quat,  # type: ignore[arg-type]
            render_mode=render_mode,
            default_joint_position=default_joint_position,
            joint_names=joint_names,
            joint_positions=joint_positions,
            source_base_translation=source_base_translation,  # type: ignore[arg-type]
            source_base_quaternion_xyzw=base_quat,  # type: ignore[arg-type]
            base_z_offset=franka_base_z_offset,
        )

    scene_yaw_deg = float(args_cli.franka_scene_yaw_deg)
    scene_base_quat = _quat_xyzw_mul(_yaw_quat_xyzw(scene_yaw_deg), base_quat)
    dynamic_cfg = cfg.get("dynamic", {})
    if not isinstance(dynamic_cfg, dict):
        dynamic_cfg = {}
    arm_kp = float(dynamic_cfg.get("arm_kp", 2000.0))
    arm_kd = float(dynamic_cfg.get("arm_kd", 100.0))
    finger_kp = float(dynamic_cfg.get("finger_kp", 4000.0))
    finger_kd = float(dynamic_cfg.get("finger_kd", 400.0))
    finger_effort_limit = float(dynamic_cfg.get("finger_effort_limit", 1000.0))
    actuator_config: dict[str, dict[str, object]] = {
        "panda_shoulder": {
            "joint_names_expr": ["panda_joint[1-4]"],
            "effort_limit_sim": 87.0,
            "stiffness": arm_kp,
            "damping": arm_kd,
        },
        "panda_forearm": {
            "joint_names_expr": ["panda_joint[5-7]"],
            "effort_limit_sim": 12.0,
            "stiffness": arm_kp,
            "damping": arm_kd,
        },
        "panda_hand": {
            "joint_names_expr": ["panda_finger_joint.*"],
            "effort_limit_sim": finger_effort_limit,
            "stiffness": finger_kp,
            "damping": finger_kd,
        },
    }
    franka_usd = (
        str(args_cli.franka_usd).strip()
        if args_cli.franka_usd is not None and str(args_cli.franka_usd).strip()
        else os.environ.get("FRANKA_USD", "").strip()
    )
    if not franka_usd:
        franka_usd = f"{ISAACLAB_NUCLEUS_DIR}/Robots/FrankaEmika/panda_instanceable.usd"

    return RobotSpec(
        name="graspgenx_franka_panda",
        usd_path=franka_usd,
        source="GraspGenX end2end/robots/franka_panda.yaml with Isaac Lab actuated Franka USD",
        source_config=cfg_path,
        urdf_path=urdf_path,
        asset_root_path=asset_root,
        base_translation=base_translation,  # type: ignore[arg-type]
        base_quaternion_xyzw=scene_base_quat,
        render_mode=render_mode,
        default_joint_position=default_joint_position,
        joint_names=joint_names,
        joint_positions=joint_positions,
        source_base_translation=source_base_translation,  # type: ignore[arg-type]
        source_base_quaternion_xyzw=base_quat,  # type: ignore[arg-type]
        scene_yaw_deg=scene_yaw_deg,
        base_z_offset=franka_base_z_offset,
        actuator_config=actuator_config,
    )


def _resolve_kuka_allegro_robot() -> RobotSpec:
    robot_usd = _repo_root() / "dextrah_lab/assets/kuka_allegro/kuka_allegro_colored.usd"
    if not robot_usd.exists():
        raise FileNotFoundError(f"Robot USD is missing: {robot_usd}")
    if _is_git_lfs_pointer(robot_usd):
        raise RuntimeError(
            f"Robot USD is a Git LFS pointer, not a materialized USD asset: {robot_usd}. "
            "Run `git lfs pull` before rendering."
        )
    return RobotSpec(
        name="kuka_allegro",
        usd_path=robot_usd,
        source="DEXTRAH dextrah_lab/assets/kuka_allegro/kuka_allegro_colored.usd",
        base_translation=(0.0, 0.0, 0.0),
        base_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
        render_mode="usd_reference",
    )


def _resolve_robot(output_dir: Path) -> RobotSpec:
    if args_cli.robot == "graspgenx_franka":
        return _resolve_graspgenx_franka_robot(output_dir)
    if args_cli.robot == "kuka_allegro":
        return _resolve_kuka_allegro_robot()
    raise ValueError(f"Unsupported robot: {args_cli.robot}")


def _safe_prim_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)


def _create_static_urdf_robot(stage: Usd.Stage, robot: RobotSpec) -> None:
    if robot.urdf_path is None:
        raise ValueError("Static URDF robot is missing urdf_path")
    _log(f"authoring static robot meshes from URDF: {robot.urdf_path}")
    link_meshes, joints = _parse_urdf_robot(robot.urdf_path)
    link_transforms = _compute_link_transforms(joints, robot)

    UsdGeom.Xform.Define(stage, "/World/Robot/Links")
    body_mat = _material(stage, "/World/Looks/franka_body_white", (0.82, 0.83, 0.80), roughness=0.58)
    joint_mat = _material(stage, "/World/Looks/franka_joint_dark", (0.18, 0.19, 0.20), roughness=0.62)
    finger_mat = _material(stage, "/World/Looks/franka_finger_gray", (0.34, 0.35, 0.35), roughness=0.64)

    mesh_count = 0
    for link_name in sorted(link_meshes):
        link_transform = link_transforms.get(link_name)
        if link_transform is None:
            _log(f"skipping URDF link without resolved transform: {link_name}")
            continue
        for mesh_idx, mesh in enumerate(link_meshes[link_name]):
            if not mesh.filename.is_file():
                raise FileNotFoundError(f"URDF mesh is missing: {mesh.filename}")
            mesh_transform = _mat_mul(link_transform, _mat_from_xyz_rpy(mesh.origin_xyz, mesh.origin_rpy))
            if "finger" in link_name:
                mat = finger_mat
            elif "hand" in link_name or link_name.endswith("7"):
                mat = joint_mat
            else:
                mat = body_mat
            _add_obj_mesh(
                stage,
                f"/World/Robot/Links/{_safe_prim_name(link_name)}_{mesh_idx}",
                mesh.filename,
                mesh_transform,
                mat,
            )
            mesh_count += 1
    if mesh_count == 0:
        raise RuntimeError(f"No renderable OBJ meshes found in URDF: {robot.urdf_path}")
    _log(f"authored {mesh_count} static Franka mesh prims")


def _franka_actuator_cfg(robot: RobotSpec) -> dict[str, ImplicitActuatorCfg]:
    actuator_config = robot.actuator_config or {}

    def implicit_cfg(name: str) -> ImplicitActuatorCfg:
        cfg = actuator_config[name]
        return ImplicitActuatorCfg(
            joint_names_expr=list(cfg["joint_names_expr"]),  # type: ignore[arg-type]
            effort_limit_sim=float(cfg["effort_limit_sim"]),
            stiffness=float(cfg["stiffness"]),
            damping=float(cfg["damping"]),
        )

    return {
        "panda_shoulder": implicit_cfg("panda_shoulder"),
        "panda_forearm": implicit_cfg("panda_forearm"),
        "panda_hand": implicit_cfg("panda_hand"),
    }


def _create_franka_articulation(robot: RobotSpec) -> Articulation:
    if robot.usd_path is None:
        raise ValueError("Franka articulation is missing usd_path")
    _log(f"spawning actuated Franka articulation from USD: {robot.usd_path}")
    franka_cfg = ArticulationCfg(
        prim_path="/World/Robot",
        spawn=sim_utils.UsdFileCfg(
            usd_path=str(robot.usd_path),
            activate_contact_sensors=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=True,
                retain_accelerations=True,
                linear_damping=0.0,
                angular_damping=0.0,
                max_depenetration_velocity=float(args_cli.franka_max_depenetration_velocity),
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=max(1, int(args_cli.franka_solver_position_iterations)),
                solver_velocity_iteration_count=max(0, int(args_cli.franka_solver_velocity_iterations)),
                sleep_threshold=0.005,
                stabilization_threshold=0.0005,
                fix_root_link=True,
            ),
            joint_drive_props=sim_utils.JointDrivePropertiesCfg(drive_type="force"),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=robot.base_translation,
            rot=_quat_xyzw_to_wxyz(robot.base_quaternion_xyzw),
            joint_pos=robot.joint_positions or {".*": 0.0},
            joint_vel={".*": 0.0},
        ),
        actuators=_franka_actuator_cfg(robot),
        soft_joint_pos_limit_factor=1.0,
    )
    return Articulation(franka_cfg)


def _create_robot(stage: Usd.Stage, robot: RobotSpec) -> Articulation | None:
    if robot.render_mode == "articulation_usd":
        return _create_franka_articulation(robot)

    robot_prim = UsdGeom.Xform.Define(stage, "/World/Robot").GetPrim()
    if robot.render_mode == "usd_reference":
        if robot.usd_path is None:
            raise ValueError("USD reference robot is missing usd_path")
        robot_prim.GetReferences().AddReference(str(robot.usd_path))
        _set_xform(
            robot_prim,
            robot.base_translation,
            rotate_quat_xyzw=robot.base_quaternion_xyzw,
        )
        return None

    if robot.render_mode == "static_urdf_obj_meshes":
        if robot.urdf_path is None:
            raise ValueError("Static URDF robot is missing urdf_path")
        _set_xform(robot_prim, (0.0, 0.0, 0.0))
        _create_static_urdf_robot(stage, robot)
        return None

    raise ValueError(f"Unsupported robot render mode: {robot.render_mode}")


def _add_franka_finger_collision_proxies(
    stage: Usd.Stage,
    mat: UsdShade.Material,
    *,
    visible: bool,
    local_center: tuple[float, float, float],
    local_size: tuple[float, float, float],
    contact_offset: float | None,
    rest_offset: float | None,
) -> dict[str, object]:
    """Add minimal fingertip colliders when the referenced Franka USD is visual-only."""

    created: list[str] = []
    missing: list[str] = []
    for link_name in ("panda_leftfinger", "panda_rightfinger"):
        link_path = f"/World/Robot/{link_name}"
        link_prim = stage.GetPrimAtPath(link_path)
        if not link_prim.IsValid():
            missing.append(link_path)
            continue
        proxy_path = f"{link_path}/dextrah_contact_proxy"
        _add_box(
            stage,
            proxy_path,
            center=local_center,
            size=local_size,
            mat=mat,
            collision=True,
            visible=visible,
            contact_offset=contact_offset,
            rest_offset=rest_offset,
        )
        created.append(proxy_path)
    return {
        "created": created,
        "missing_links": missing,
        "count": len(created),
        "shape": "box per Franka finger link",
        "visible": bool(visible),
        "local_center": [float(v) for v in local_center],
        "local_size": [float(v) for v in local_size],
        "contact_offset": None if contact_offset is None else float(contact_offset),
        "rest_offset": None if rest_offset is None else float(rest_offset),
    }


def _add_franka_contact_debug_visual_overlays(
    stage: Usd.Stage,
    mat: UsdShade.Material,
    *,
    visible: bool,
    local_center: tuple[float, float, float],
    local_size: tuple[float, float, float],
) -> dict[str, object]:
    root_path = "/World/ContactDebug/FrankaFingerProxies"
    UsdGeom.Xform.Define(stage, "/World/ContactDebug")
    UsdGeom.Xform.Define(stage, root_path)
    followers: dict[str, dict[str, object]] = {}
    created: list[str] = []
    for link_name, suffix in (("panda_leftfinger", "leftfinger"), ("panda_rightfinger", "rightfinger")):
        path = f"{root_path}/{suffix}"
        prim = _add_box(
            stage,
            path,
            center=(0.0, 0.0, -10.0),
            size=local_size,
            mat=mat,
            collision=False,
            visible=visible,
        )
        try:
            UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(False)
        except Exception:
            pass
        followers[link_name] = {
            "path": path,
            "local_center": [float(v) for v in local_center],
            "local_size": [float(v) for v in local_size],
        }
        created.append(path)
    return {
        "enabled": bool(visible),
        "root_path": root_path,
        "created": created if visible else [],
        "count": len(created) if visible else 0,
        "followers": followers if visible else {},
        "shape": "visual-only box follower per Franka finger body",
        "local_center": [float(v) for v in local_center],
        "local_size": [float(v) for v in local_size],
    }


def _update_franka_contact_debug_visual_overlays(
    stage: Usd.Stage,
    robot: Articulation | None,
    overlay_record: dict[str, object] | None,
) -> None:
    if robot is None or not overlay_record or not bool(overlay_record.get("enabled")):
        return
    followers = overlay_record.get("followers")
    if not isinstance(followers, dict):
        return
    body_poses = _robot_body_pose_records(robot)
    updated = False
    for body_name, info in followers.items():
        if not isinstance(info, dict):
            continue
        path = info.get("path")
        pose = body_poses.get(str(body_name))
        if not isinstance(path, str) or not isinstance(pose, dict):
            continue
        pos = pose.get("position_w")
        quat_wxyz = pose.get("quaternion_wxyz")
        local_center = info.get("local_center", [0.0, 0.0, 0.030])
        local_size = info.get("local_size", [0.020, 0.012, 0.050])
        if not isinstance(pos, list) or not isinstance(quat_wxyz, list):
            continue
        prim = stage.GetPrimAtPath(path)
        if not prim.IsValid():
            continue
        quat_xyzw = _quat_wxyz_to_xyzw(quat_wxyz)
        rot = _mat_from_quat_xyzw(quat_xyzw)
        offset = _mat_apply_vector(rot, local_center)
        center = tuple(float(pos[idx]) + float(offset[idx]) for idx in range(3))
        _set_xform(prim, center, scale=local_size, rotate_quat_xyzw=quat_xyzw)
        updated = True
    if updated:
        update_stage()


def _make_kinematic_body(prim: Usd.Prim) -> None:
    rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
    rb_api.CreateRigidBodyEnabledAttr(True)
    rb_api.CreateKinematicEnabledAttr(True)
    try:
        rb_api.CreateStartsAsleepAttr(False)
    except Exception:
        pass
    try:
        physx_api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        physx_api.CreateDisableGravityAttr(True)
    except Exception:
        pass


def _add_franka_kinematic_contact_proxies(
    stage: Usd.Stage,
    mat: UsdShade.Material,
    *,
    visible: bool,
    local_center: tuple[float, float, float],
    local_size: tuple[float, float, float],
    contact_offset: float | None,
    rest_offset: float | None,
) -> dict[str, object]:
    _ = stage, mat
    root_path = "/World/FrankaContactProxies"
    followers: dict[str, dict[str, object]] = {}
    created: list[str] = []
    for link_name, suffix in (("panda_leftfinger", "leftfinger"), ("panda_rightfinger", "rightfinger")):
        proxy_path = f"{root_path}/{suffix}"
        proxy_cfg = RigidObjectCfg(
            prim_path=proxy_path,
            spawn=sim_utils.CuboidCfg(
                size=local_size,
                visible=visible,
                collision_props=sim_utils.CollisionPropertiesCfg(
                    contact_offset=contact_offset,
                    rest_offset=rest_offset,
                ),
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=True,
                    disable_gravity=True,
                ),
                mass_props=sim_utils.MassPropertiesCfg(mass=0.05),
                physics_material=RigidBodyMaterialCfg(static_friction=1.2, dynamic_friction=1.2),
            ),
            init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, -10.0)),
        )
        proxy_object = RigidObject(proxy_cfg)
        followers[link_name] = {
            "path": proxy_path,
            "local_center": list(local_center),
            "local_size": list(local_size),
            "object": proxy_object,
        }
        created.append(proxy_path)
    return {
        "mode": "kinematic",
        "root_path": root_path,
        "created": created,
        "count": len(created),
        "followers": followers,
        "shape": "kinematic box per Franka finger body",
        "visible": bool(visible),
        "local_center": list(local_center),
        "local_size": list(local_size),
        "contact_offset": None if contact_offset is None else float(contact_offset),
        "rest_offset": None if rest_offset is None else float(rest_offset),
    }


def _update_franka_kinematic_contact_proxies(
    stage: Usd.Stage,
    robot: Articulation | None,
    proxy_record: dict[str, object] | None,
) -> None:
    if robot is None or not proxy_record:
        return
    followers = proxy_record.get("followers")
    if not isinstance(followers, dict):
        return
    body_poses = _robot_body_pose_records(robot)
    updated = False
    for body_name, info in followers.items():
        if not isinstance(info, dict):
            continue
        path = info.get("path")
        pose = body_poses.get(str(body_name))
        if not isinstance(path, str) or not isinstance(pose, dict):
            continue
        pos = pose.get("position_w")
        quat_wxyz = pose.get("quaternion_wxyz")
        if not isinstance(pos, list) or not isinstance(quat_wxyz, list):
            continue
        prim = stage.GetPrimAtPath(path)
        proxy_object = info.get("object")
        local_center = info.get("local_center", [0.0, 0.0, 0.030])
        local_size = info.get("local_size", [0.020, 0.012, 0.050])
        quat_xyzw = _quat_wxyz_to_xyzw(quat_wxyz)
        rot = _mat_from_quat_xyzw(quat_xyzw)
        offset = _mat_apply_vector(rot, local_center)
        center = tuple(float(pos[idx]) + float(offset[idx]) for idx in range(3))
        if isinstance(proxy_object, RigidObject):
            root_pose = torch.tensor(
                [[center[0], center[1], center[2], float(quat_wxyz[0]), float(quat_wxyz[1]), float(quat_wxyz[2]), float(quat_wxyz[3])]],
                dtype=torch.float32,
                device=proxy_object.device,
            )
            proxy_object.write_root_pose_to_sim(root_pose)
            updated = True
        elif prim.IsValid():
            _set_xform(prim, center, scale=local_size, rotate_quat_xyzw=quat_xyzw)
            updated = True
    if updated:
        pass


def _contact_proxy_metadata(value):
    if isinstance(value, dict):
        return {str(k): _contact_proxy_metadata(v) for k, v in value.items() if str(k) != "object"}
    if isinstance(value, list):
        return [_contact_proxy_metadata(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _robot_metadata(robot: RobotSpec) -> dict[str, object]:
    return {
        "name": robot.name,
        "source": robot.source,
        "render_mode": robot.render_mode,
        "source_config": str(robot.source_config) if robot.source_config else None,
        "usd_path": str(robot.usd_path) if robot.usd_path else None,
        "urdf_path": str(robot.urdf_path) if robot.urdf_path else None,
        "asset_root_path": str(robot.asset_root_path) if robot.asset_root_path else None,
        "base_translation": list(robot.base_translation),
        "base_quaternion_xyzw": list(robot.base_quaternion_xyzw),
        "source_base_translation": list(robot.source_base_translation) if robot.source_base_translation else None,
        "source_base_quaternion_xyzw": (
            list(robot.source_base_quaternion_xyzw) if robot.source_base_quaternion_xyzw else None
        ),
        "scene_yaw_deg": robot.scene_yaw_deg,
        "base_z_offset": robot.base_z_offset,
        "joint_names": robot.joint_names,
        "default_joint_position": robot.default_joint_position,
        "joint_positions": robot.joint_positions,
        "actuator_config": robot.actuator_config,
    }


def _star_vertices(
    outer_radius: float,
    inner_radius: float,
    *,
    points: int = 5,
    phase_rad: float = 0.0,
) -> list[Point2]:
    vertices: list[Point2] = []
    for idx in range(points * 2):
        radius = outer_radius if idx % 2 == 0 else inner_radius
        angle = phase_rad + idx * math.pi / points
        vertices.append((radius * math.cos(angle), radius * math.sin(angle)))
    return vertices


def _polygon_area(vertices: list[Point2]) -> float:
    area = 0.0
    for idx, p in enumerate(vertices):
        q = vertices[(idx + 1) % len(vertices)]
        area += p[0] * q[1] - q[0] * p[1]
    return 0.5 * area


def _add_mesh(
    stage: Usd.Stage,
    path: str,
    points: list[Gf.Vec3f],
    face_vertex_counts: list[int],
    face_vertex_indices: list[int],
    mat: UsdShade.Material,
    *,
    collision: bool = False,
    approximation: str = "none",
    visible: bool = True,
    contact_offset: float | None = None,
    rest_offset: float | None = None,
) -> Usd.Prim:
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(face_vertex_counts)
    mesh.CreateFaceVertexIndicesAttr(face_vertex_indices)
    mesh.CreateSubdivisionSchemeAttr("none")
    mesh.CreateDoubleSidedAttr(True)
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    zs = [float(p[2]) for p in points]
    mesh.CreateExtentAttr(
        [
            Gf.Vec3f(min(xs), min(ys), min(zs)),
            Gf.Vec3f(max(xs), max(ys), max(zs)),
        ]
    )
    prim = mesh.GetPrim()
    _bind(prim, mat)
    if not visible:
        UsdGeom.Imageable(prim).MakeInvisible()
    if collision:
        _apply_collision(prim, approximation=approximation, contact_offset=contact_offset, rest_offset=rest_offset)
    return prim


def _extruded_polygon_mesh_data(
    vertices: list[Point2],
    thickness: float,
    *,
    fan_center: Point2 | None,
) -> tuple[list[Gf.Vec3f], list[int], list[int]]:
    if len(vertices) < 3:
        raise ValueError("Need at least three vertices for an extruded polygon")
    if _polygon_area(vertices) < 0.0:
        vertices = list(reversed(vertices))

    z0 = -0.5 * float(thickness)
    z1 = 0.5 * float(thickness)
    n = len(vertices)
    points = [Gf.Vec3f(x, y, z0) for x, y in vertices] + [Gf.Vec3f(x, y, z1) for x, y in vertices]
    counts: list[int] = []
    indices: list[int] = []

    if fan_center is None:
        for idx in range(1, n - 1):
            counts.append(3)
            indices.extend([n, n + idx, n + idx + 1])
        for idx in range(1, n - 1):
            counts.append(3)
            indices.extend([0, idx + 1, idx])
    else:
        bottom_center_idx = len(points)
        top_center_idx = bottom_center_idx + 1
        points.append(Gf.Vec3f(fan_center[0], fan_center[1], z0))
        points.append(Gf.Vec3f(fan_center[0], fan_center[1], z1))
        for idx in range(n):
            nxt = (idx + 1) % n
            counts.append(3)
            indices.extend([top_center_idx, n + idx, n + nxt])
        for idx in range(n):
            nxt = (idx + 1) % n
            counts.append(3)
            indices.extend([bottom_center_idx, nxt, idx])

    for idx in range(n):
        nxt = (idx + 1) % n
        counts.append(4)
        indices.extend([idx, nxt, n + nxt, n + idx])

    return points, counts, indices


def _add_extruded_polygon_mesh(
    stage: Usd.Stage,
    path: str,
    vertices: list[Point2],
    thickness: float,
    mat: UsdShade.Material,
    *,
    fan_center: Point2 | None,
    collision: bool = False,
    approximation: str = "none",
    visible: bool = True,
    contact_offset: float | None = None,
    rest_offset: float | None = None,
) -> Usd.Prim:
    points, counts, indices = _extruded_polygon_mesh_data(vertices, thickness, fan_center=fan_center)
    return _add_mesh(
        stage,
        path,
        points,
        counts,
        indices,
        mat,
        collision=collision,
        approximation=approximation,
        visible=visible,
        contact_offset=contact_offset,
        rest_offset=rest_offset,
    )


def _ray_rectangle_intersection(angle: float, half_x: float, half_y: float) -> Point2:
    dx = math.cos(angle)
    dy = math.sin(angle)
    candidates: list[float] = []
    if abs(dx) > 1.0e-9:
        candidates.append(half_x / abs(dx))
    if abs(dy) > 1.0e-9:
        candidates.append(half_y / abs(dy))
    t = min(candidates)
    return (dx * t, dy * t)


def _rectangle_corners_between(angle_a: float, angle_b: float, half_x: float, half_y: float) -> list[Point2]:
    corners = [
        (half_x, half_y),
        (-half_x, half_y),
        (-half_x, -half_y),
        (half_x, -half_y),
    ]
    result: list[tuple[float, Point2]] = []
    for corner in corners:
        base_angle = math.atan2(corner[1], corner[0])
        while base_angle <= angle_a:
            base_angle += 2.0 * math.pi
        if base_angle < angle_b - 1.0e-9:
            result.append((base_angle, corner))
    result.sort(key=lambda item: item[0])
    return [corner for _, corner in result]


def _add_fixture_mesh(
    stage: Usd.Stage,
    path: str,
    *,
    size_x: float,
    size_y: float,
    thickness: float,
    hole_vertices: list[Point2],
    mat: UsdShade.Material,
    collision: bool = True,
) -> Usd.Prim:
    half_x = 0.5 * float(size_x)
    half_y = 0.5 * float(size_y)
    if max(abs(x) for x, _ in hole_vertices) >= half_x or max(abs(y) for _, y in hole_vertices) >= half_y:
        raise ValueError("Star hole must fit inside fixture rectangle")

    # The fixture top/bottom are triangulated as radial cells from the star hole
    # out to the enclosing rectangle. This gives an exact through-hole without
    # requiring a CAD or triangulation dependency at runtime.
    z0 = -0.5 * float(thickness)
    z1 = 0.5 * float(thickness)
    points: list[Gf.Vec3f] = []
    point_indices: dict[tuple[float, float, float], int] = {}
    counts: list[int] = []
    indices: list[int] = []

    def point_idx(point: Point2, z: float) -> int:
        key = (round(float(point[0]), 10), round(float(point[1]), 10), round(float(z), 10))
        if key not in point_indices:
            point_indices[key] = len(points)
            points.append(Gf.Vec3f(float(point[0]), float(point[1]), float(z)))
        return point_indices[key]

    def add_top_polygon(poly: list[Point2]) -> None:
        if len(poly) < 3:
            return
        if _polygon_area(poly) < 0.0:
            poly = list(reversed(poly))
        top_indices = [point_idx(p, z1) for p in poly]
        bottom_indices = [point_idx(p, z0) for p in poly]
        for idx in range(1, len(poly) - 1):
            counts.append(3)
            indices.extend([top_indices[0], top_indices[idx], top_indices[idx + 1]])
        for idx in range(1, len(poly) - 1):
            counts.append(3)
            indices.extend([bottom_indices[0], bottom_indices[idx + 1], bottom_indices[idx]])

    def add_outer_side(p: Point2, q: Point2) -> None:
        if math.dist(p, q) <= 1.0e-9:
            return
        counts.append(4)
        indices.extend([point_idx(p, z0), point_idx(q, z0), point_idx(q, z1), point_idx(p, z1)])

    def add_inner_side(p: Point2, q: Point2) -> None:
        if math.dist(p, q) <= 1.0e-9:
            return
        counts.append(4)
        indices.extend([point_idx(q, z0), point_idx(p, z0), point_idx(p, z1), point_idx(q, z1)])

    n = len(hole_vertices)
    step = 2.0 * math.pi / n
    angles = [idx * step for idx in range(n + 1)]
    outer_points = [_ray_rectangle_intersection(angle, half_x, half_y) for angle in angles]

    for idx in range(n):
        hole_a = hole_vertices[idx]
        hole_b = hole_vertices[(idx + 1) % n]
        outer_a = outer_points[idx]
        outer_b = outer_points[idx + 1]
        corners = _rectangle_corners_between(angles[idx], angles[idx + 1], half_x, half_y)
        outer_chain = [outer_a] + corners + [outer_b]
        cell = [hole_a] + outer_chain + [hole_b]
        add_top_polygon(cell)
        for p, q in zip(outer_chain, outer_chain[1:]):
            add_outer_side(p, q)
        add_inner_side(hole_a, hole_b)

    return _add_mesh(
        stage,
        path,
        points,
        counts,
        indices,
        mat,
        collision=collision,
        approximation="none",
        visible=True,
    )


def _create_star_object(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    yaw_deg: float,
    outer_radius: float,
    inner_radius: float,
    thickness: float,
    visual_mat: UsdShade.Material,
    collision_mat: UsdShade.Material,
    dynamic: bool,
    visual_visible: bool,
    collision_visible: bool,
    collision_contact_offset: float | None,
    collision_rest_offset: float | None,
    max_depenetration_velocity: float | None,
    solver_position_iterations: int | None,
    solver_velocity_iterations: int | None,
) -> dict[str, object]:
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    _set_xform(root, center, rotate_xyz_deg=(0.0, 0.0, float(yaw_deg)))
    if dynamic:
        _make_rigid_body(
            root,
            density=520.0,
            max_depenetration_velocity=max_depenetration_velocity,
            solver_position_iterations=solver_position_iterations,
            solver_velocity_iterations=solver_velocity_iterations,
        )

    vertices = _star_vertices(outer_radius, inner_radius)
    _add_extruded_polygon_mesh(
        stage,
        f"{root_path}/visual",
        vertices,
        thickness,
        visual_mat,
        fan_center=(0.0, 0.0),
        collision=False,
        visible=visual_visible,
    )

    for idx in range(len(vertices)):
        tri = [(0.0, 0.0), vertices[idx], vertices[(idx + 1) % len(vertices)]]
        _add_extruded_polygon_mesh(
            stage,
            f"{root_path}/collision_{idx:02d}",
            tri,
            thickness,
            collision_mat,
            fan_center=None,
            collision=True,
            approximation="convexHull",
            visible=collision_visible,
            contact_offset=collision_contact_offset,
            rest_offset=collision_rest_offset,
        )

    return {
        "prim_path": root_path,
        "center": list(center),
        "yaw_deg": float(yaw_deg),
        "outer_radius": float(outer_radius),
        "inner_radius": float(inner_radius),
        "thickness": float(thickness),
        "dynamic": bool(dynamic),
        "visual_visible": bool(visual_visible),
        "collision_pieces": len(vertices),
        "collision_model": "ten convex triangular-prism child colliders under one rigid body",
        "collision_visible": bool(collision_visible),
        "collision_debug_visuals": 0,
        "collision_debug_visual_margin": 0.0,
        "collision_contact_offset": None if collision_contact_offset is None else float(collision_contact_offset),
        "collision_rest_offset": None if collision_rest_offset is None else float(collision_rest_offset),
        "max_depenetration_velocity": None
        if max_depenetration_velocity is None
        else float(max_depenetration_velocity),
        "solver_position_iterations": None
        if solver_position_iterations is None
        else int(solver_position_iterations),
        "solver_velocity_iterations": None
        if solver_velocity_iterations is None
        else int(solver_velocity_iterations),
    }


def _create_fixture(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    yaw_deg: float,
    size_x: float,
    size_y: float,
    thickness: float,
    star_outer_radius: float,
    star_inner_radius: float,
    clearance: float,
    mat: UsdShade.Material,
) -> dict[str, object]:
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    _set_xform(root, center, rotate_xyz_deg=(0.0, 0.0, float(yaw_deg)))
    hole_vertices = _star_vertices(star_outer_radius + clearance, star_inner_radius + 0.55 * clearance)
    _add_fixture_mesh(
        stage,
        f"{root_path}/block_with_star_hole",
        size_x=size_x,
        size_y=size_y,
        thickness=thickness,
        hole_vertices=hole_vertices,
        mat=mat,
        collision=True,
    )
    return {
        "prim_path": root_path,
        "center": list(center),
        "yaw_deg": float(yaw_deg),
        "size_x": float(size_x),
        "size_y": float(size_y),
        "thickness": float(thickness),
        "hole_outer_radius": float(star_outer_radius + clearance),
        "hole_inner_radius": float(star_inner_radius + 0.55 * clearance),
        "clearance": float(clearance),
        "collision_model": "static triangle mesh matching the star through-hole",
    }


def _create_cube_object(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    size: float,
    mat: UsdShade.Material,
    animate: bool = False,
) -> dict[str, object]:
    prim = _add_box(stage, root_path, center, (size, size, size), mat, collision=True)
    return {
        "prim_path": root_path,
        "center": list(center),
        "size": float(size),
        "dynamic": False,
        "motion_source": "deterministic keyframed disturbance trajectory" if animate else "static task cube",
    }


def _create_table(
    stage: Usd.Stage,
    *,
    table_mat: UsdShade.Material,
    leg_mat: UsdShade.Material,
    table_center_x: float,
    table_short_x: float,
    table_long_y: float,
    table_height: float,
    table_top_thick: float,
) -> dict[str, float]:
    _add_box(
        stage,
        "/World/Table/top",
        (table_center_x, 0.0, table_height),
        (table_short_x, table_long_y, table_top_thick),
        table_mat,
    )
    leg_xs = [table_center_x - table_short_x / 2.0 + 0.08, table_center_x + table_short_x / 2.0 - 0.08]
    leg_ys = [-table_long_y / 2.0 + 0.08, table_long_y / 2.0 - 0.08]
    leg_idx = 0
    for lx in leg_xs:
        for ly in leg_ys:
            _add_box(
                stage,
                f"/World/Table/leg_{leg_idx}",
                (lx, ly, table_height / 2.0),
                (0.05, 0.05, table_height),
                leg_mat,
            )
            leg_idx += 1
    return {
        "center_x": float(table_center_x),
        "short_x": float(table_short_x),
        "long_y": float(table_long_y),
        "height": float(table_height),
        "top_thickness": float(table_top_thick),
        "surface_z": float(table_height + table_top_thick / 2.0),
    }


def _bake_root_transform(stage: Usd.Stage, prim_path: str, record: dict[str, object]) -> None:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    world_xform = xform_cache.GetLocalToWorldTransform(prim)
    translation = world_xform.ExtractTranslation()
    record["initial_center"] = record["center"]
    record["center"] = [float(translation[0]), float(translation[1]), float(translation[2])]
    record["settled_transform_baked"] = True
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTransformOp().Set(world_xform)


def _reset_robot_articulation(robot: Articulation | None) -> None:
    if robot is None:
        return
    root_state = robot.data.default_root_state.clone()
    robot.write_root_pose_to_sim(root_state[:, :7])
    robot.write_root_velocity_to_sim(root_state[:, 7:])
    joint_pos = robot.data.default_joint_pos.clone()
    joint_vel = robot.data.default_joint_vel.clone()
    robot.write_joint_state_to_sim(joint_pos, joint_vel)
    robot.set_joint_position_target(joint_pos)
    robot.write_data_to_sim()
    robot.reset()


def _franka_motion_envelope(phase: float) -> float:
    t = max(0.0, min(1.0, float(phase)))
    return _smoothstep(min(1.0, t / 0.12)) * _smoothstep(min(1.0, (1.0 - t) / 0.12))


def _franka_all_directions_target(robot: Articulation, phase: float):
    target = robot.data.default_joint_pos.clone()
    joint_indices = {name: idx for idx, name in enumerate(robot.joint_names)}
    scale = max(0.0, min(1.5, float(args_cli.franka_motion_scale)))
    t = max(0.0, min(1.0, float(phase)))
    tau = 2.0 * math.pi * t
    envelope = _franka_motion_envelope(t)
    offsets = {
        "panda_joint1": 0.46 * math.sin(tau),
        "panda_joint2": 0.26 * math.sin(tau + 0.5 * math.pi),
        "panda_joint3": 0.34 * math.sin(2.0 * tau + 0.35),
        "panda_joint4": 0.30 * math.sin(tau + math.pi),
        "panda_joint5": 0.38 * math.sin(1.5 * tau + 0.80),
        "panda_joint6": 0.24 * math.sin(tau - 0.65),
        "panda_joint7": 0.64 * math.sin(2.0 * tau + 1.20),
    }
    for joint_name, offset in offsets.items():
        joint_idx = joint_indices.get(joint_name)
        if joint_idx is not None:
            target[:, joint_idx] = target[:, joint_idx] + float(scale * envelope * offset)

    finger_opening = 0.025 + 0.015 * (0.5 + 0.5 * math.sin(2.0 * tau + 0.30))
    for joint_name in ("panda_finger_joint1", "panda_finger_joint2"):
        joint_idx = joint_indices.get(joint_name)
        if joint_idx is not None:
            target[:, joint_idx] = float(finger_opening)
    return target


_TRAJECTORY_CACHE: dict[str, object] | None = None


def _load_franka_trajectory() -> dict[str, object] | None:
    global _TRAJECTORY_CACHE
    if args_cli.franka_trajectory_json is None:
        return None
    if _TRAJECTORY_CACHE is None:
        path = args_cli.franka_trajectory_json.expanduser().resolve()
        _log(f"loading Franka trajectory JSON: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        frames = data.get("frames")
        if not isinstance(frames, list) or len(frames) == 0:
            raise ValueError(f"Trajectory JSON has no frames: {path}")
        _TRAJECTORY_CACHE = data
    return _TRAJECTORY_CACHE


def _trajectory_frame_index(trajectory: dict[str, object], frame_idx: float, frame_count: int) -> int:
    frames = trajectory.get("frames")
    if not isinstance(frames, list) or len(frames) == 0:
        return 0
    if frame_count <= 1:
        return 0
    alpha = max(0.0, min(1.0, float(frame_idx) / float(frame_count - 1)))
    return min(len(frames) - 1, max(0, int(round(alpha * float(len(frames) - 1)))))


def _trajectory_frame(trajectory: dict[str, object], frame_idx: float, frame_count: int) -> dict[str, object]:
    frames = trajectory.get("frames")
    if not isinstance(frames, list) or len(frames) == 0:
        raise ValueError("Trajectory JSON has no frames")
    item = frames[_trajectory_frame_index(trajectory, frame_idx, frame_count)]
    if not isinstance(item, dict):
        raise ValueError("Trajectory frame is not a mapping")
    return item


def _franka_trajectory_target(robot: Articulation, frame_idx: float, frame_count: int):
    trajectory = _load_franka_trajectory()
    if trajectory is None:
        raise ValueError("--franka_motion trajectory requires --franka_trajectory_json")
    frame = _trajectory_frame(trajectory, frame_idx, frame_count)
    joint_position = frame.get("joint_position")
    if not isinstance(joint_position, list) or len(joint_position) < 7:
        raise ValueError("Trajectory frame is missing a Franka joint_position vector")

    target = robot.data.default_joint_pos.clone()
    joint_indices = {name: idx for idx, name in enumerate(robot.joint_names)}
    arm_names = [
        "panda_joint1",
        "panda_joint2",
        "panda_joint3",
        "panda_joint4",
        "panda_joint5",
        "panda_joint6",
        "panda_joint7",
    ]
    for src_idx, joint_name in enumerate(arm_names):
        joint_idx = joint_indices.get(joint_name)
        if joint_idx is not None:
            target[:, joint_idx] = float(joint_position[src_idx])

    if len(joint_position) >= 8:
        finger_1 = float(joint_position[7])
        finger_2 = float(joint_position[8]) if len(joint_position) >= 9 else finger_1
        for joint_name, value in (
            ("panda_finger_joint1", finger_1),
            ("panda_finger_joint2", finger_2),
        ):
            joint_idx = joint_indices.get(joint_name)
            if joint_idx is not None:
                target[:, joint_idx] = value
    return target


def _robot_articulation_target(
    robot: Articulation | None,
    phase: float,
    frame_idx: int = 0,
    frame_count: int = 1,
):
    if robot is None:
        return None
    if args_cli.franka_motion == "all_directions":
        return _franka_all_directions_target(robot, phase)
    if args_cli.franka_motion == "trajectory":
        return _franka_trajectory_target(robot, frame_idx, frame_count)
    return robot.data.default_joint_pos.clone()


def _quat_xyzw_from_matrix(m: list[list[float]]) -> tuple[float, float, float, float]:
    trace = float(m[0][0]) + float(m[1][1]) + float(m[2][2])
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (float(m[2][1]) - float(m[1][2])) / s
        qy = (float(m[0][2]) - float(m[2][0])) / s
        qz = (float(m[1][0]) - float(m[0][1])) / s
    elif float(m[0][0]) > float(m[1][1]) and float(m[0][0]) > float(m[2][2]):
        s = math.sqrt(1.0 + float(m[0][0]) - float(m[1][1]) - float(m[2][2])) * 2.0
        qw = (float(m[2][1]) - float(m[1][2])) / s
        qx = 0.25 * s
        qy = (float(m[0][1]) + float(m[1][0])) / s
        qz = (float(m[0][2]) + float(m[2][0])) / s
    elif float(m[1][1]) > float(m[2][2]):
        s = math.sqrt(1.0 + float(m[1][1]) - float(m[0][0]) - float(m[2][2])) * 2.0
        qw = (float(m[0][2]) - float(m[2][0])) / s
        qx = (float(m[0][1]) + float(m[1][0])) / s
        qy = 0.25 * s
        qz = (float(m[1][2]) + float(m[2][1])) / s
    else:
        s = math.sqrt(1.0 + float(m[2][2]) - float(m[0][0]) - float(m[1][1])) * 2.0
        qw = (float(m[1][0]) - float(m[0][1])) / s
        qx = (float(m[0][2]) + float(m[2][0])) / s
        qy = (float(m[1][2]) + float(m[2][1])) / s
        qz = 0.25 * s
    return _normalize_quat_xyzw((qx, qy, qz, qw))


def _object_pose_from_trajectory_frame(
    trajectory: dict[str, object],
    frame_idx: float,
    frame_count: int,
    object_id: str,
) -> list[list[float]] | None:
    frame = _trajectory_frame(trajectory, frame_idx, frame_count)
    object_poses = frame.get("object_poses")
    if isinstance(object_poses, dict):
        pose = object_poses.get(object_id)
        if pose is None and object_id == "object":
            objects = trajectory.get("objects")
            if isinstance(objects, list) and objects:
                first = objects[0]
                if isinstance(first, dict):
                    pose = object_poses.get(str(first.get("id", "")))
        if isinstance(pose, list):
            return pose
    parts = frame.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("name") in (object_id, "object"):
                pose = part.get("transform")
                if isinstance(pose, list):
                    return pose
    return None


def _apply_trajectory_object_pose(
    stage: Usd.Stage,
    prim_path: str,
    trajectory: dict[str, object] | None,
    frame_idx: float,
    frame_count: int,
    object_id: str,
) -> None:
    if trajectory is None:
        return
    pose = _object_pose_from_trajectory_frame(trajectory, frame_idx, frame_count, object_id)
    if pose is None:
        return
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return
    translate = (float(pose[0][3]), float(pose[1][3]), float(pose[2][3]))
    quat_xyzw = _quat_xyzw_from_matrix(pose)
    _set_xform(prim, translate, rotate_quat_xyzw=quat_xyzw)
    update_stage()


def _object_motion_record(
    stage: Usd.Stage,
    prim_path: str,
    frame_idx: int,
    frame_count: int,
) -> dict[str, object] | None:
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return None
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    world_xform = xform_cache.GetLocalToWorldTransform(prim)
    translation = world_xform.ExtractTranslation()
    return {
        "frame": int(frame_idx),
        "t": 0.0 if frame_count <= 1 else float(frame_idx) / float(frame_count - 1),
        "prim_path": str(prim_path),
        "position_w": [float(translation[0]), float(translation[1]), float(translation[2])],
        "world_transform": [[float(world_xform[row][col]) for col in range(4)] for row in range(4)],
    }


def _rigid_object_motion_record(
    rigid_object: RigidObject | None,
    prim_path: str,
    frame_idx: int,
    frame_count: int,
) -> dict[str, object] | None:
    if rigid_object is None:
        return None
    try:
        pose = rigid_object.data.root_pose_w[0].detach().cpu().tolist()
        vel = rigid_object.data.root_vel_w[0].detach().cpu().tolist()
    except Exception:
        return None
    return {
        "frame": int(frame_idx),
        "t": 0.0 if frame_count <= 1 else float(frame_idx) / float(frame_count - 1),
        "prim_path": str(prim_path),
        "position_w": [float(v) for v in pose[:3]],
        "quaternion_wxyz": [float(v) for v in pose[3:7]],
        "linear_velocity_w": [float(v) for v in vel[:3]],
        "angular_velocity_w": [float(v) for v in vel[3:]],
        "source": "physx_rigid_object",
    }


def _robot_body_pose_records(robot: Articulation | None) -> dict[str, dict[str, object]]:
    if robot is None:
        return {}
    records: dict[str, dict[str, object]] = {}
    body_names = list(robot.body_names)
    wanted = ("panda_hand", "panda_leftfinger", "panda_rightfinger", "panda_link7")
    for body_name in wanted:
        if body_name not in body_names:
            continue
        body_idx = body_names.index(body_name)
        try:
            pos = robot.data.body_pos_w[0, body_idx].detach().cpu().tolist()
            quat = robot.data.body_quat_w[0, body_idx].detach().cpu().tolist()
        except Exception:
            records[body_name] = {"body_name": body_name}
            continue
        records[body_name] = {
            "body_name": body_name,
            "position_w": [float(v) for v in pos],
            "quaternion_wxyz": [float(v) for v in quat],
        }
    return records


def _robot_end_effector_record(robot: Articulation | None) -> dict[str, object] | None:
    if robot is None:
        return None
    body_names = list(robot.body_names)
    for body_name in ("panda_hand", "panda_link8", "panda_leftfinger", "panda_rightfinger", "panda_link7"):
        if body_name not in body_names:
            continue
        body_idx = body_names.index(body_name)
        try:
            pos = robot.data.body_pos_w[0, body_idx].detach().cpu().tolist()
            quat = robot.data.body_quat_w[0, body_idx].detach().cpu().tolist()
        except Exception:
            return {"body_name": body_name}
        return {
            "body_name": body_name,
            "position_w": [float(v) for v in pos],
            "quaternion_wxyz": [float(v) for v in quat],
        }
    return None


def _robot_motion_record(robot: Articulation | None, frame_idx: int, frame_count: int, target) -> dict[str, object] | None:
    if robot is None or target is None:
        return None
    values = target[0].detach().cpu().tolist()
    joint_targets = {name: float(values[idx]) for idx, name in enumerate(robot.joint_names)}
    actual_pos = robot.data.joint_pos[0].detach().cpu().tolist()
    actual_vel = robot.data.joint_vel[0].detach().cpu().tolist()
    return {
        "frame": int(frame_idx),
        "t": 0.0 if frame_count <= 1 else float(frame_idx) / float(frame_count - 1),
        "motion": str(args_cli.franka_motion),
        "joint_targets": joint_targets,
        "joint_positions_actual": {name: float(actual_pos[idx]) for idx, name in enumerate(robot.joint_names)},
        "joint_velocities_actual": {name: float(actual_vel[idx]) for idx, name in enumerate(robot.joint_names)},
        "end_effector": _robot_end_effector_record(robot),
        "body_poses": _robot_body_pose_records(robot),
    }


def _joint_value(robot: Articulation | None, joint_name: str) -> float | None:
    if robot is None or joint_name not in robot.joint_names:
        return None
    joint_idx = list(robot.joint_names).index(joint_name)
    try:
        return float(robot.data.joint_pos[0, joint_idx].detach().cpu().item())
    except Exception:
        return None


def _finger_midpoint_w(robot: Articulation | None) -> list[float] | None:
    body_poses = _robot_body_pose_records(robot)
    left = body_poses.get("panda_leftfinger", {}).get("position_w")
    right = body_poses.get("panda_rightfinger", {}).get("position_w")
    if not isinstance(left, list) or not isinstance(right, list):
        return None
    return [0.5 * (float(left[idx]) + float(right[idx])) for idx in range(3)]


def _quat_wxyz_normalize(quat_wxyz: Iterable[float]) -> tuple[float, float, float, float]:
    w, x, y, z = [float(v) for v in quat_wxyz]
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm <= 1.0e-12:
        return (1.0, 0.0, 0.0, 0.0)
    return (w / norm, x / norm, y / norm, z / norm)


def _quat_wxyz_inverse(quat_wxyz: Iterable[float]) -> tuple[float, float, float, float]:
    w, x, y, z = _quat_wxyz_normalize(quat_wxyz)
    return (w, -x, -y, -z)


def _quat_wxyz_mul(
    lhs: Iterable[float],
    rhs: Iterable[float],
) -> tuple[float, float, float, float]:
    aw, ax, ay, az = _quat_wxyz_normalize(lhs)
    bw, bx, by, bz = _quat_wxyz_normalize(rhs)
    return _quat_wxyz_normalize(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        )
    )


def _quat_wxyz_rotate_vector(
    quat_wxyz: Iterable[float],
    vec: Iterable[float],
) -> tuple[float, float, float]:
    w, x, y, z = _quat_wxyz_normalize(quat_wxyz)
    vx, vy, vz = [float(v) for v in vec]
    uv = (
        y * vz - z * vy,
        z * vx - x * vz,
        x * vy - y * vx,
    )
    uuv = (
        y * uv[2] - z * uv[1],
        z * uv[0] - x * uv[2],
        x * uv[1] - y * uv[0],
    )
    return (
        vx + 2.0 * (w * uv[0] + uuv[0]),
        vy + 2.0 * (w * uv[1] + uuv[1]),
        vz + 2.0 * (w * uv[2] + uuv[2]),
    )


def _update_kinematic_grasp_weld(
    *,
    robot: Articulation | None,
    star_rigid_object: RigidObject | None,
    state: dict[str, object],
) -> None:
    if robot is None or star_rigid_object is None:
        return
    rel_pos = state.get("relative_position_body0")
    rel_quat = state.get("relative_quaternion_body0_object")
    if not isinstance(rel_pos, list) or not isinstance(rel_quat, list):
        return
    hand_pose = _robot_body_pose_records(robot).get("panda_hand", {})
    hand_pos = hand_pose.get("position_w")
    hand_quat = hand_pose.get("quaternion_wxyz")
    if not isinstance(hand_pos, list) or not isinstance(hand_quat, list):
        return
    hand_quat_wxyz = _quat_wxyz_normalize(hand_quat)
    offset_w = _quat_wxyz_rotate_vector(hand_quat_wxyz, rel_pos)
    object_pos = [float(hand_pos[idx]) + float(offset_w[idx]) for idx in range(3)]
    object_quat = _quat_wxyz_mul(hand_quat_wxyz, rel_quat)
    root_pose = torch.tensor(
        [[object_pos[0], object_pos[1], object_pos[2], object_quat[0], object_quat[1], object_quat[2], object_quat[3]]],
        dtype=torch.float32,
        device=star_rigid_object.device,
    )
    star_rigid_object.write_root_pose_to_sim(root_pose)
    try:
        root_vel = torch.zeros((1, 6), dtype=torch.float32, device=star_rigid_object.device)
        star_rigid_object.write_root_velocity_to_sim(root_vel)
    except Exception:
        pass
    star_rigid_object.update(1.0 / 60.0)


def _maybe_attach_franka_grasp_constraint(
    *,
    stage: Usd.Stage,
    robot: Articulation | None,
    star_rigid_object: RigidObject | None,
    star_prim_path: str,
    state: dict[str, object] | None,
    frame_idx: int,
    substep_idx: int,
) -> None:
    if state is None:
        return
    if bool(state.get("attached")):
        _update_kinematic_grasp_weld(robot=robot, star_rigid_object=star_rigid_object, state=state)
        return
    if bool(state.get("failed")):
        return
    if str(state.get("mode")) != "attach_on_close":
        return
    if robot is None or star_rigid_object is None:
        state["failed"] = True
        state["failure_reason"] = "missing_robot_or_star_rigid_object"
        return

    finger_values = [
        _joint_value(robot, "panda_finger_joint1"),
        _joint_value(robot, "panda_finger_joint2"),
    ]
    if any(value is None for value in finger_values):
        state["last_check"] = {"reason": "missing_finger_joint_values"}
        return
    max_finger_opening = max(float(value) for value in finger_values if value is not None)
    close_threshold = float(state["close_threshold"])
    if max_finger_opening > close_threshold:
        state["last_check"] = {
            "reason": "fingers_open",
            "max_finger_opening": max_finger_opening,
            "close_threshold": close_threshold,
        }
        return

    finger_midpoint = _finger_midpoint_w(robot)
    object_record = _rigid_object_motion_record(star_rigid_object, star_prim_path, frame_idx, 1)
    object_pos = object_record.get("position_w") if object_record is not None else None
    object_quat = object_record.get("quaternion_wxyz") if object_record is not None else None
    if not isinstance(finger_midpoint, list) or not isinstance(object_pos, list):
        state["last_check"] = {"reason": "missing_pose"}
        return
    dx = float(finger_midpoint[0]) - float(object_pos[0])
    dy = float(finger_midpoint[1]) - float(object_pos[1])
    dz = float(finger_midpoint[2]) - float(object_pos[2])
    xy_distance = math.sqrt(dx * dx + dy * dy)
    z_distance = abs(dz)
    xy_threshold = float(state["xy_threshold"])
    z_threshold = float(state["z_threshold"])
    state["last_check"] = {
        "reason": "near_object" if xy_distance <= xy_threshold and z_distance <= z_threshold else "too_far",
        "frame": int(frame_idx),
        "substep": int(substep_idx),
        "max_finger_opening": max_finger_opening,
        "finger_midpoint_w": [float(v) for v in finger_midpoint],
        "object_position_w": [float(v) for v in object_pos],
        "xy_distance": xy_distance,
        "z_distance": z_distance,
        "xy_threshold": xy_threshold,
        "z_threshold": z_threshold,
    }
    if xy_distance > xy_threshold or z_distance > z_threshold:
        return

    hand_pose = _robot_body_pose_records(robot).get("panda_hand", {})
    hand_pos = hand_pose.get("position_w")
    hand_quat = hand_pose.get("quaternion_wxyz")
    if not isinstance(hand_pos, list) or not isinstance(hand_quat, list) or not isinstance(object_quat, list):
        state["last_check"] = {
            **dict(state["last_check"]),
            "reason": "missing_pose_for_constraint",
        }
        return

    hand_quat_wxyz = _quat_wxyz_normalize(hand_quat)
    object_quat_wxyz = _quat_wxyz_normalize(object_quat)
    hand_inv = _quat_wxyz_inverse(hand_quat_wxyz)
    relative_pos = _quat_wxyz_rotate_vector(
        hand_inv,
        (
            float(object_pos[0]) - float(hand_pos[0]),
            float(object_pos[1]) - float(hand_pos[1]),
            float(object_pos[2]) - float(hand_pos[2]),
        ),
    )
    relative_quat = _quat_wxyz_mul(hand_inv, object_quat_wxyz)

    state["attached"] = True
    state["attach_frame"] = int(frame_idx)
    state["attach_substep"] = int(substep_idx)
    state["body0"] = "/World/Robot/panda_hand"
    state["body1"] = str(star_prim_path)
    state["constraint_method"] = "kinematic_pose_weld"
    state["relative_position_body0"] = [float(v) for v in relative_pos]
    state["relative_quaternion_body0_object"] = [float(v) for v in relative_quat]
    state["attach_metrics"] = dict(state["last_check"])
    _update_kinematic_grasp_weld(robot=robot, star_rigid_object=star_rigid_object, state=state)
    _log(f"attached Franka grasp weld at frame {frame_idx}, substep {substep_idx}")


def _write_robot_articulation_targets(robot: Articulation | None, joint_pos_target=None) -> None:
    if robot is None:
        return
    if joint_pos_target is None:
        joint_pos_target = robot.data.default_joint_pos
    robot.set_joint_position_target(joint_pos_target)
    robot.write_data_to_sim()


def _write_robot_articulation_state(robot: Articulation | None, joint_pos=None) -> None:
    if robot is None:
        return
    if joint_pos is None:
        joint_pos = robot.data.default_joint_pos
    joint_vel = robot.data.default_joint_vel.clone()
    joint_vel.zero_()
    robot.write_joint_state_to_sim(joint_pos, joint_vel)
    robot.set_joint_position_target(joint_pos)
    robot.write_data_to_sim()


def _update_robot_articulation(robot: Articulation | None, dt: float) -> None:
    if robot is None:
        return
    robot.update(dt)


def _robot_runtime_metadata(robot: Articulation | None) -> dict[str, object]:
    if robot is None:
        return {"articulation_initialized": False}
    return {
        "articulation_initialized": True,
        "is_fixed_base": bool(robot.is_fixed_base),
        "num_joints": int(robot.num_joints),
        "num_bodies": int(robot.num_bodies),
        "joint_names_sim": list(robot.joint_names),
        "body_names_sim": list(robot.body_names),
        "actuator_group_names": list(robot.actuators.keys()),
    }


def _stage_collision_summary(stage: Usd.Stage, root_path: str) -> dict[str, object]:
    counts_by_child: dict[str, int] = {}
    examples: list[dict[str, object]] = []
    prefix = str(root_path).rstrip("/")
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        if not path.startswith(prefix):
            continue
        schemas = [str(item) for item in prim.GetAppliedSchemas()]
        if "PhysicsCollisionAPI" not in schemas and "PhysicsMeshCollisionAPI" not in schemas:
            continue
        rel = path[len(prefix) :].lstrip("/")
        child = rel.split("/", 1)[0] if rel else prim.GetName()
        counts_by_child[child] = counts_by_child.get(child, 0) + 1
        if len(examples) < 32:
            examples.append({"path": path, "schemas": schemas})
    return {
        "root_path": prefix,
        "num_collision_prims": int(sum(counts_by_child.values())),
        "counts_by_child": counts_by_child,
        "examples": examples,
    }


def _settle_scene(
    sim,
    stage: Usd.Stage,
    star_record: dict[str, object],
    settle_steps: int,
    robot_articulation: Articulation | None,
    star_rigid_object: RigidObject | None = None,
    contact_proxy_followers: dict[str, object] | None = None,
    contact_debug_overlays: dict[str, object] | None = None,
) -> bool:
    _log("resetting SimulationContext for scene initialization")
    sim.reset()
    _reset_robot_articulation(robot_articulation)
    if star_rigid_object is not None:
        star_rigid_object.update(float(sim.cfg.dt))
    _update_franka_kinematic_contact_proxies(stage, robot_articulation, contact_proxy_followers)
    if settle_steps <= 0 or not bool(star_record.get("dynamic")):
        _update_franka_contact_debug_visual_overlays(stage, robot_articulation, contact_debug_overlays)
        sim.render()
        update_stage()
        return False
    _log(f"settling dynamic star for {settle_steps} physics steps")
    for _ in range(settle_steps):
        _write_robot_articulation_targets(robot_articulation)
        _update_franka_kinematic_contact_proxies(stage, robot_articulation, contact_proxy_followers)
        sim.step(render=False)
        _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
        if star_rigid_object is not None:
            star_rigid_object.update(float(sim.cfg.dt))
    _update_franka_contact_debug_visual_overlays(stage, robot_articulation, contact_debug_overlays)
    sim.render()
    update_stage()
    _bake_root_transform(stage, str(star_record["prim_path"]), star_record)
    return True


def _write_metadata(path: Path, metadata: dict) -> None:
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def _normalize_vec(vec: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1.0e-12:
        raise ValueError(f"Cannot normalize near-zero vector: {vec}")
    return (vec[0] / norm, vec[1] / norm, vec[2] / norm)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _quat_from_matrix(
    x_axis: tuple[float, float, float],
    y_axis: tuple[float, float, float],
    z_axis: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    m00, m01, m02 = x_axis[0], y_axis[0], z_axis[0]
    m10, m11, m12 = x_axis[1], y_axis[1], z_axis[1]
    m20, m21, m22 = x_axis[2], y_axis[2], z_axis[2]
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        return (0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s)
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return ((m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s)
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return ((m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s)
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
    return ((m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s)


def _look_at_quat_world(
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    # Isaac Lab's "world" camera convention uses +X forward and +Z up.
    forward = _normalize_vec((target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]))
    up_ref = (0.0, 0.0, 1.0)
    if abs(sum(forward[i] * up_ref[i] for i in range(3))) > 0.985:
        up_ref = (0.0, 1.0, 0.0)
    y_axis = _normalize_vec(_cross(up_ref, forward))
    z_axis = _normalize_vec(_cross(forward, y_axis))
    return _quat_from_matrix(forward, y_axis, z_axis)


def _save_rgb_tensor(path: Path, rgb_tensor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = rgb_tensor.detach().cpu().numpy()
    try:
        from PIL import Image

        Image.fromarray(rgb).save(path)
    except Exception:
        from torchvision.utils import save_image
        import torch

        image = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        save_image(image, str(path))


def _set_view(eye: tuple[float, float, float], target: tuple[float, float, float]):
    try:
        from isaacsim.core.utils.viewports import set_camera_view
    except Exception:
        from omni.isaac.core.utils.viewports import set_camera_view  # type: ignore
    from omni.kit.viewport.utility import get_active_viewport

    try:
        set_camera_view(eye=list(eye), target=list(target))
    except TypeError:
        set_camera_view(list(eye), list(target))

    viewport = get_active_viewport()
    if viewport is None:
        raise RuntimeError("No active viewport available for capture")
    return viewport


def _capture_viewport_png(viewport, dst: Path, *, deadline_seconds: float = 90.0) -> Path:
    from omni.kit.viewport.utility import capture_viewport_to_file, next_viewport_frame_async

    dst.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(1):
        simulation_app.update()

    async def _wait_for_capture() -> None:
        await next_viewport_frame_async(viewport, n_frames=4)
        capture = capture_viewport_to_file(viewport, file_path=str(dst))
        await capture.wait_for_result(completion_frames=12)

    loop = asyncio.get_event_loop()
    task = loop.create_task(_wait_for_capture())
    deadline = time.time() + float(deadline_seconds)
    while not task.done() and time.time() < deadline:
        simulation_app.update()
        loop.run_until_complete(asyncio.sleep(0.0))
    if not task.done():
        task.cancel()
        loop.run_until_complete(asyncio.sleep(0.0))
        raise TimeoutError(f"Timed out while capturing viewport image {dst}")
    task.result()

    if not dst.exists():
        raise RuntimeError(f"Viewport capture did not write {dst}")

    return dst


def _capture_view(
    name: str,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    output_dir: Path,
) -> Path:
    viewport = _set_view(eye, target)
    return _capture_viewport_png(viewport, output_dir / f"{name}.png")


def _capture_overview_video(
    *,
    sim,
    robot_articulation: Articulation | None,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    output_dir: Path,
    fps: int,
    seconds: float,
    sim_steps_per_frame: int,
    frame_callback=None,
    robot_motion_trace: list[dict[str, object]] | None = None,
    object_motion_trace: list[dict[str, object]] | None = None,
    object_stage: Usd.Stage | None = None,
    object_prim_path: str | None = None,
    object_rigid_object: RigidObject | None = None,
    contact_proxy_followers: dict[str, object] | None = None,
    contact_debug_overlays: dict[str, object] | None = None,
    grasp_constraint_state: dict[str, object] | None = None,
) -> list[str]:
    frame_count = max(2, int(round(float(fps) * float(seconds))))
    frames_dir = output_dir / "frames"
    frames: list[str] = []

    quat_wxyz = _look_at_quat_world(eye, target)
    camera_cfg = TiledCameraCfg(
        prim_path="/World/OverviewCamera",
        offset=TiledCameraCfg.OffsetCfg(pos=eye, rot=quat_wxyz, convention="world"),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=20.0,
            focus_distance=400.0,
            horizontal_aperture=20.955,
            clipping_range=(0.05, 5.0),
        ),
        width=int(args_cli.width),
        height=int(args_cli.height),
        update_period=0,
    )
    _log("creating overview TiledCamera")
    camera = TiledCamera(camera_cfg)
    _log("resetting SimulationContext")
    sim.reset()
    _reset_robot_articulation(robot_articulation)
    if object_rigid_object is not None:
        object_rigid_object.update(float(sim.cfg.dt))
    _update_franka_kinematic_contact_proxies(object_stage or omni.usd.get_context().get_stage(), robot_articulation, contact_proxy_followers)

    _log(f"capturing overview video frames with TiledCamera: {frame_count} frames")
    for frame_idx in range(frame_count):
        step_count = 1 if frame_idx == 0 else max(1, int(sim_steps_per_frame))
        last_robot_target = None
        for substep_idx in range(step_count):
            substep = 0.0 if step_count <= 1 else float(substep_idx) / float(step_count)
            phase = min(1.0, (float(frame_idx) + substep) / max(float(frame_count - 1), 1.0))
            last_robot_target = _robot_articulation_target(
                robot_articulation,
                phase,
                frame_idx=float(frame_idx) + substep,
                frame_count=frame_count,
            )
            if args_cli.franka_motion == "trajectory" and args_cli.franka_trajectory_playback == "state":
                _write_robot_articulation_state(robot_articulation, last_robot_target)
                _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
                _update_franka_kinematic_contact_proxies(
                    object_stage or omni.usd.get_context().get_stage(),
                    robot_articulation,
                    contact_proxy_followers,
                )
                sim.step(render=False)
                _write_robot_articulation_state(robot_articulation, last_robot_target)
                _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
                if object_rigid_object is not None:
                    object_rigid_object.update(float(sim.cfg.dt))
                if object_stage is not None and object_prim_path is not None:
                    _maybe_attach_franka_grasp_constraint(
                        stage=object_stage,
                        robot=robot_articulation,
                        star_rigid_object=object_rigid_object,
                        star_prim_path=object_prim_path,
                        state=grasp_constraint_state,
                        frame_idx=frame_idx,
                        substep_idx=substep_idx,
                    )
            else:
                _write_robot_articulation_targets(robot_articulation, last_robot_target)
                _update_franka_kinematic_contact_proxies(
                    object_stage or omni.usd.get_context().get_stage(),
                    robot_articulation,
                    contact_proxy_followers,
                )
                sim.step(render=False)
                _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
                if object_rigid_object is not None:
                    object_rigid_object.update(float(sim.cfg.dt))
                if object_stage is not None and object_prim_path is not None:
                    _maybe_attach_franka_grasp_constraint(
                        stage=object_stage,
                        robot=robot_articulation,
                        star_rigid_object=object_rigid_object,
                        star_prim_path=object_prim_path,
                        state=grasp_constraint_state,
                        frame_idx=frame_idx,
                        substep_idx=substep_idx,
                    )
        if frame_callback is not None:
            frame_callback(frame_idx, frame_count)
        if robot_motion_trace is not None:
            motion_record = _robot_motion_record(robot_articulation, frame_idx, frame_count, last_robot_target)
            if motion_record is not None:
                robot_motion_trace.append(motion_record)
        _update_franka_contact_debug_visual_overlays(
            object_stage or omni.usd.get_context().get_stage(),
            robot_articulation,
            contact_debug_overlays,
        )
        sim.render()
        camera.update(float(sim.cfg.dt) * step_count)
        if object_motion_trace is not None and object_stage is not None and object_prim_path is not None:
            object_record = _rigid_object_motion_record(
                object_rigid_object,
                object_prim_path,
                frame_idx,
                frame_count,
            ) or _object_motion_record(object_stage, object_prim_path, frame_idx, frame_count)
            if object_record is not None:
                object_motion_trace.append(object_record)
        dst = frames_dir / f"overview_{frame_idx:04d}.png"
        _log(f"capturing overview frame {frame_idx + 1}/{frame_count}")
        _save_rgb_tensor(dst, camera.data.output["rgb"][0])
        frames.append(str(dst))

    del camera
    return frames


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


def _disturbance_pulse(t: float, center: float, width: float) -> float:
    x = (float(t) - float(center)) / max(float(width), 1.0e-6)
    return math.exp(-0.5 * x * x)


def _cube_motion_state(frame_idx: int, frame_count: int, surface_z: float) -> dict[str, object]:
    t = 0.0 if frame_count <= 1 else float(frame_idx) / float(frame_count - 1)
    travel = _smoothstep(t)

    kick_0 = _disturbance_pulse(t, 0.23, 0.045)
    kick_1 = _disturbance_pulse(t, 0.52, 0.060)
    kick_2 = _disturbance_pulse(t, 0.77, 0.050)
    lateral = float(args_cli.cube_lateral_disturbance) * (0.75 * kick_0 - 1.0 * kick_1 + 0.55 * kick_2)
    lift = float(args_cli.cube_vertical_disturbance) * (0.35 * kick_0 + 1.0 * kick_1 + 0.45 * kick_2)
    yaw = float(args_cli.cube_yaw_disturbance_deg) * (0.25 * travel + 0.45 * kick_0 - 0.55 * kick_1 + 0.35 * kick_2)
    pitch = 11.0 * kick_1 - 5.0 * kick_2
    roll = -7.0 * kick_0 + 6.0 * kick_2

    size = float(args_cli.cube_size)
    center = (
        float(args_cli.cube_start_x) + float(args_cli.cube_forward_travel) * travel,
        float(args_cli.cube_start_y) + lateral,
        float(surface_z) + 0.5 * size + 0.001 + lift,
    )
    return {
        "frame": int(frame_idx),
        "t": t,
        "center": [float(v) for v in center],
        "roll_pitch_yaw_deg": [float(roll), float(pitch), float(yaw)],
        "disturbance_pulses": [float(kick_0), float(kick_1), float(kick_2)],
    }


def _cube_static_state(frame_idx: int, frame_count: int, cube_center: tuple[float, float, float]) -> dict[str, object]:
    return {
        "frame": int(frame_idx),
        "t": 0.0 if frame_count <= 1 else float(frame_idx) / float(frame_count - 1),
        "center": [float(v) for v in cube_center],
        "roll_pitch_yaw_deg": [0.0, 0.0, 0.0],
        "disturbance_pulses": [],
    }


def _apply_cube_motion(stage: Usd.Stage, cube_path: str, state: dict[str, object]) -> None:
    prim = stage.GetPrimAtPath(cube_path)
    if not prim.IsValid():
        raise RuntimeError(f"Cube prim is missing: {cube_path}")
    center = state["center"]
    rpy = state["roll_pitch_yaw_deg"]
    _set_xform(
        prim,
        (float(center[0]), float(center[1]), float(center[2])),
        (float(args_cli.cube_size), float(args_cli.cube_size), float(args_cli.cube_size)),
        rotate_xyz_deg=(float(rpy[0]), float(rpy[1]), float(rpy[2])),
    )
    update_stage()


def _render_cube_motion_scene(
    *,
    output_dir: Path,
    stage: Usd.Stage,
    sim,
    robot_articulation: Articulation | None,
    robot_spec: RobotSpec,
    table: dict[str, float],
    floor_mat: UsdShade.Material,
    cube_mat: UsdShade.Material,
) -> None:
    surface_z = table["surface_z"]
    table_center_x = table["center_x"]
    animate_cube = bool(args_cli.animate_cube)
    cube_path = "/World/CubeTask/Cube"
    cube_center = (
        float(args_cli.cube_start_x),
        float(args_cli.cube_start_y),
        float(surface_z) + 0.5 * float(args_cli.cube_size) + 0.001,
    )

    UsdGeom.Xform.Define(stage, "/World/CubeTask")
    _log("creating animated cube object" if animate_cube else "creating static cube object")
    cube = _create_cube_object(
        stage,
        root_path=cube_path,
        center=cube_center,
        size=float(args_cli.cube_size),
        mat=cube_mat,
        animate=animate_cube,
    )
    _add_box(stage, "/World/Floor", (0.0, 0.0, -0.015), (3.2, 2.8, 0.03), floor_mat, collision=True)

    dome = stage.DefinePrim("/World/DomeLight", "DomeLight")
    dome.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(650.0)
    dome.CreateAttribute("inputs:color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 0.98, 0.92))
    sun = stage.DefinePrim("/World/KeyLight", "DistantLight")
    sun.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1500.0)
    sun.CreateAttribute("inputs:angle", Sdf.ValueTypeNames.Float).Set(0.35)
    _set_xform(sun, (0.0, 0.0, 0.0), rotate_xyz_deg=(-45.0, 0.0, 35.0))

    _log("resetting SimulationContext for cube-motion initialization")
    sim.reset()
    _reset_robot_articulation(robot_articulation)
    sim.render()
    update_stage()

    trajectory: list[dict[str, object]] = []
    robot_motion_trace: list[dict[str, object]] = []

    def frame_callback(frame_idx: int, frame_count: int) -> None:
        if animate_cube:
            state = _cube_motion_state(frame_idx, frame_count, surface_z)
            _apply_cube_motion(stage, cube_path, state)
        else:
            state = _cube_static_state(frame_idx, frame_count, cube_center)
        trajectory.append(state)

    metadata = {
        "generated_at_unix": time.time(),
        "task": "single_cube_motion" if animate_cube else "single_cube_static",
        "task_description": (
            "GraspGenX Franka rendered in the single-cube scene; the cube is static unless "
            "legacy cube animation is explicitly enabled, and the Franka can be held or driven by actuator targets."
        ),
        "simulation_backend": "Isaac Sim / Isaac Lab / PhysX USD scene",
        "robot": _robot_metadata(robot_spec),
        "robot_runtime": _robot_runtime_metadata(robot_articulation),
        "robot_motion": {
            "mode": str(args_cli.franka_motion),
            "scale": float(args_cli.franka_motion_scale),
            "commanded": bool(robot_articulation is not None and args_cli.franka_motion != "hold"),
            "description": "all_directions commands a deterministic joint-space sweep that moves the hand laterally, vertically, and forward/back.",
        },
        "axes": {
            "table_long_axis": "world_y",
            "table_short_axis": "world_x",
            "robot_base_origin": list(robot_spec.base_translation),
            "table_is_in_front_of_robot_at_negative_x": True,
        },
        "dimensions_m": {
            "table_short_x": table["short_x"],
            "table_long_y": table["long_y"],
            "table_height": table["height"],
            "table_surface_z": surface_z,
            "cube_size": float(args_cli.cube_size),
            "cube_forward_travel": float(args_cli.cube_forward_travel),
            "cube_lateral_disturbance": float(args_cli.cube_lateral_disturbance),
            "cube_vertical_disturbance": float(args_cli.cube_vertical_disturbance),
        },
        "objects": {
            "cube": cube,
            "disturbances": [
                {"center_t": 0.23, "description": "positive lateral slide with small bounce"},
                {"center_t": 0.52, "description": "negative lateral shove with main vertical hop"},
                {"center_t": 0.77, "description": "settling correction shove"},
            ]
            if animate_cube
            else [],
        },
        "simulation": {
            "physics_device": str(args_cli.physics_device),
            "sim_dt": 1.0 / 60.0,
            "render_interval": 1,
            "cube_motion_is_keyframed": animate_cube,
        },
        "checks": {
            "robot_selected": robot_spec.name,
            "uses_graspgenx_franka": robot_spec.name == "graspgenx_franka_panda",
            "franka_is_static": robot_spec.render_mode == "static_urdf_obj_meshes",
            "franka_is_articulation": robot_spec.render_mode == "articulation_usd",
            "franka_has_actuators": bool(robot_spec.actuator_config),
            "franka_motion_commanded": bool(robot_articulation is not None and args_cli.franka_motion != "hold"),
            "cube_moves": animate_cube,
        },
    }
    _write_metadata(output_dir / "scene_metadata.json", metadata)

    usd_path = output_dir / ("franka_cube_motion_env.usda" if animate_cube else "franka_single_cube_env.usda")
    _log(f"exporting USD: {usd_path}")
    stage.GetRootLayer().Export(str(usd_path))

    table_target = (float(args_cli.cube_start_x) - 0.05, float(args_cli.cube_start_y), surface_z + 0.12)
    views = {
        "overview": ((1.28, -0.72, 1.42), table_target),
        "robot_side": ((1.20, 0.06, 1.32), (float(args_cli.cube_start_x), float(args_cli.cube_start_y), surface_z + 0.12)),
        "topdown": ((table_center_x, float(args_cli.cube_start_y), 2.05), (table_center_x, float(args_cli.cube_start_y), surface_z + 0.02)),
        "pickup_close": ((0.05, float(args_cli.cube_start_y) - 0.46, 1.16), (float(args_cli.cube_start_x), float(args_cli.cube_start_y), surface_z + 0.08)),
        "fixture_close": ((0.05, float(args_cli.cube_start_y) - 0.46, 1.16), (float(args_cli.cube_start_x), float(args_cli.cube_start_y), surface_z + 0.08)),
    }
    name = str(args_cli.view)
    eye, look_at = views[name]
    if bool(args_cli.capture_video):
        if name != "overview":
            raise ValueError("--capture_video is currently overview-only")
        frame_paths = _capture_overview_video(
            sim=sim,
            robot_articulation=robot_articulation,
            eye=eye,
            target=look_at,
            output_dir=output_dir,
            fps=int(args_cli.fps),
            seconds=float(args_cli.video_seconds),
            sim_steps_per_frame=int(args_cli.sim_steps_per_frame),
            frame_callback=frame_callback,
            robot_motion_trace=robot_motion_trace,
        )
        rendered = {"overview_frames": frame_paths}
    else:
        frame_callback(0, 1)
        _log(f"capturing view: {name}")
        rendered = {name: str(_capture_view(name, eye, look_at, output_dir))}

    _write_metadata(output_dir / "trajectory.json", {"cube_trajectory": trajectory})
    robot_motion_path = output_dir / "robot_motion_trajectory.json"
    _write_metadata(
        robot_motion_path,
        {
            "motion": str(args_cli.franka_motion),
            "scale": float(args_cli.franka_motion_scale),
            "robot_motion_trajectory": robot_motion_trace,
        },
    )
    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "trajectory": str(output_dir / "trajectory.json"),
            "robot_motion_trajectory": str(robot_motion_path),
            "renders": rendered,
            "fps": int(args_cli.fps),
            "video_seconds": float(args_cli.video_seconds),
            "sim_steps_per_frame": int(args_cli.sim_steps_per_frame),
        },
    )

    print(f"Wrote Franka single-cube scene renders to {output_dir}")
    print(f"Cube trajectory frames: {len(trajectory)}")
    print(f"USD: {usd_path}")


def main() -> None:
    output_dir = args_cli.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"output_dir={output_dir}")
    if float(args_cli.physics_dt) <= 0.0:
        raise ValueError("--physics_dt must be positive")
    if int(args_cli.franka_solver_position_iterations) <= 0:
        raise ValueError("--franka_solver_position_iterations must be positive")
    if int(args_cli.franka_solver_velocity_iterations) < 0:
        raise ValueError("--franka_solver_velocity_iterations must be non-negative")
    proxy_center = tuple(float(v) for v in args_cli.franka_contact_proxy_center)
    proxy_size = tuple(float(v) for v in args_cli.franka_contact_proxy_size)
    if any(v <= 0.0 for v in proxy_size):
        raise ValueError("--franka_contact_proxy_size entries must be positive")
    contact_debug_opacity = max(0.0, min(1.0, float(args_cli.contact_debug_opacity)))
    contact_debug_enabled = bool(args_cli.show_contact_debug)
    show_franka_contact_proxies = contact_debug_enabled or bool(args_cli.show_franka_contact_proxies)
    show_star_collision = contact_debug_enabled or bool(args_cli.show_star_collision)
    collision_rest_offset = (
        None if args_cli.collision_rest_offset is None else float(args_cli.collision_rest_offset)
    )
    franka_proxy_contact_offset = (
        None
        if args_cli.franka_contact_proxy_contact_offset is None
        else float(args_cli.franka_contact_proxy_contact_offset)
    )
    star_collision_contact_offset = (
        None if args_cli.star_collision_contact_offset is None else float(args_cli.star_collision_contact_offset)
    )

    _log("resolving robot")
    robot_spec = _resolve_robot(output_dir)
    _log(f"resolved robot: {robot_spec.name} render_mode={robot_spec.render_mode}")
    _log("loading trajectory if requested")
    trajectory_data = _load_franka_trajectory() if args_cli.franka_motion == "trajectory" else None
    if isinstance(trajectory_data, dict):
        _log(f"loaded trajectory frames: {len(trajectory_data.get('frames', []))}")

    _log("creating USD stage")
    create_new_stage()
    update_stage()
    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    UsdGeom.Xform.Define(stage, "/World")
    sim = _create_sim_context()
    UsdGeom.Xform.Define(stage, "/World/Table")
    UsdGeom.Xform.Define(stage, "/World/Kitting")
    UsdGeom.Xform.Define(stage, "/World/Looks")

    _log("creating materials")
    table_mat = _material(stage, "/World/Looks/table_matte", (0.54, 0.50, 0.44))
    leg_mat = _material(stage, "/World/Looks/table_dark", (0.20, 0.22, 0.24))
    floor_mat = _material(stage, "/World/Looks/floor_gray", (0.28, 0.30, 0.31))
    star_mat = _material(
        stage,
        "/World/Looks/star_yellow",
        (0.95, 0.70, 0.16),
        roughness=0.55,
        opacity=0.45 if show_star_collision else 1.0,
    )
    cube_mat = _material(stage, "/World/Looks/cube_blue", (0.10, 0.42, 0.86), roughness=0.62)
    collision_mat = _material(stage, "/World/Looks/collision_hidden", (0.95, 0.70, 0.16), roughness=0.55)
    proxy_debug_mat = _material(
        stage,
        "/World/Looks/contact_proxy_debug_red",
        (1.0, 0.08, 0.04),
        roughness=0.45,
        opacity=contact_debug_opacity,
    )
    star_collision_debug_mat = _material(
        stage,
        "/World/Looks/star_collision_debug_cyan",
        (0.05, 0.82, 1.0),
        roughness=0.45,
        opacity=contact_debug_opacity,
    )
    fixture_mat = _material(stage, "/World/Looks/fixture_graphite", (0.16, 0.18, 0.19), roughness=0.47)
    grasp_x_mat = _material(stage, "/World/Looks/grasp_axis_x", (0.86, 0.10, 0.10), roughness=0.45)
    grasp_y_mat = _material(stage, "/World/Looks/grasp_axis_y", (0.12, 0.62, 0.18), roughness=0.45)
    grasp_z_mat = _material(stage, "/World/Looks/grasp_axis_z", (0.12, 0.28, 0.92), roughness=0.45)
    grasp_target_mat = _material(stage, "/World/Looks/grasp_target_white", (1.0, 0.95, 0.70), roughness=0.35)

    # Match the current clutter-bin scene table and robot convention.
    table_height = 0.72
    table_top_thick = 0.052
    table_center_x = -0.72
    table_short_x = 0.90
    table_long_y = 1.32
    pickup_y = -0.26
    fixture_y = 0.26

    if robot_spec.usd_path is not None:
        _log(f"referencing robot USD: {robot_spec.usd_path}")
    else:
        _log(f"creating robot with render_mode={robot_spec.render_mode}")
    robot_articulation = _create_robot(stage, robot_spec)
    franka_articulation_contact_proxies: dict[str, object] = {"created": [], "missing_links": [], "count": 0}
    franka_kinematic_contact_proxies: dict[str, object] | None = None
    if robot_spec.name == "graspgenx_franka_panda" and robot_spec.render_mode == "articulation_usd":
        if str(args_cli.franka_contact_proxy_mode) in ("articulation", "kinematic"):
            franka_articulation_contact_proxies = _add_franka_finger_collision_proxies(
                stage,
                collision_mat,
                visible=False,
                local_center=proxy_center,
                local_size=proxy_size,
                contact_offset=franka_proxy_contact_offset,
                rest_offset=collision_rest_offset,
            )
        if str(args_cli.franka_contact_proxy_mode) == "kinematic":
            franka_kinematic_contact_proxies = _add_franka_kinematic_contact_proxies(
                stage,
                collision_mat,
                visible=False,
                local_center=proxy_center,
                local_size=proxy_size,
                contact_offset=franka_proxy_contact_offset,
                rest_offset=collision_rest_offset,
            )
        update_stage()
    franka_contact_proxies: dict[str, object] = {
        "mode": str(args_cli.franka_contact_proxy_mode),
        "articulation_child": franka_articulation_contact_proxies,
        "kinematic_followers": franka_kinematic_contact_proxies,
    }
    franka_contact_debug_visual_overlays = _add_franka_contact_debug_visual_overlays(
        stage,
        proxy_debug_mat,
        visible=show_franka_contact_proxies,
        local_center=proxy_center,
        local_size=proxy_size,
    )
    if args_cli.franka_motion == "trajectory" and robot_articulation is None:
        raise ValueError("--franka_motion trajectory requires --franka_render_mode articulation_usd")
    if (
        args_cli.scene == "star_kitting"
        and args_cli.franka_motion == "trajectory"
        and args_cli.franka_trajectory_object_mode == "physics"
        and args_cli.franka_trajectory_playback != "target"
    ):
        raise ValueError(
            "--franka_trajectory_object_mode physics requires --franka_trajectory_playback target "
            "so the robot is driven through the articulation controller instead of kinematic state writes."
        )
    if (
        args_cli.scene == "star_kitting"
        and args_cli.franka_motion == "trajectory"
        and args_cli.franka_trajectory_object_mode == "physics"
        and not bool(args_cli.dynamic_star)
    ):
        raise ValueError("--franka_trajectory_object_mode physics requires --dynamic_star")
    if str(args_cli.franka_grasp_constraint_mode) == "attach_on_close" and not bool(args_cli.dynamic_star):
        raise ValueError("--franka_grasp_constraint_mode attach_on_close requires --dynamic_star")
    if (
        str(args_cli.franka_grasp_constraint_mode) == "attach_on_close"
        and args_cli.franka_motion == "trajectory"
        and args_cli.franka_trajectory_object_mode != "physics"
    ):
        raise ValueError("--franka_grasp_constraint_mode attach_on_close requires --franka_trajectory_object_mode physics")

    _log("creating table")
    table = _create_table(
        stage,
        table_mat=table_mat,
        leg_mat=leg_mat,
        table_center_x=table_center_x,
        table_short_x=table_short_x,
        table_long_y=table_long_y,
        table_height=table_height,
        table_top_thick=table_top_thick,
    )
    surface_z = table["surface_z"]

    if args_cli.scene in ("single_cube", "cube_motion"):
        _render_cube_motion_scene(
            output_dir=output_dir,
            stage=stage,
            sim=sim,
            robot_articulation=robot_articulation,
            robot_spec=robot_spec,
            table=table,
            floor_mat=floor_mat,
            cube_mat=cube_mat,
        )
        sim.clear_all_callbacks()
        sim.clear_instance()
        return

    star_outer_radius = float(args_cli.star_outer_radius)
    star_inner_radius = float(args_cli.star_inner_radius)
    star_thickness = float(args_cli.star_thickness)
    fixture_size_x = float(args_cli.fixture_size_x)
    fixture_size_y = float(args_cli.fixture_size_y)
    fixture_thickness = float(args_cli.fixture_thickness)
    fixture_clearance = float(args_cli.fixture_clearance)
    if not (0.0 < star_inner_radius < star_outer_radius):
        raise ValueError("--star_inner_radius must be positive and smaller than --star_outer_radius")
    if fixture_clearance < 0.0:
        raise ValueError("--fixture_clearance must be non-negative")

    star_center = (table_center_x, pickup_y, surface_z + star_thickness / 2.0 + 0.001)
    fixture_center = (table_center_x, fixture_y, surface_z + fixture_thickness / 2.0)

    _log("creating star object")
    star = _create_star_object(
        stage,
        root_path="/World/Kitting/StarObject",
        center=star_center,
        yaw_deg=float(args_cli.star_start_yaw_deg),
        outer_radius=star_outer_radius,
        inner_radius=star_inner_radius,
        thickness=star_thickness,
        visual_mat=star_mat,
        collision_mat=star_collision_debug_mat if show_star_collision else collision_mat,
        dynamic=bool(args_cli.dynamic_star),
        visual_visible=True,
        collision_visible=show_star_collision,
        collision_contact_offset=star_collision_contact_offset,
        collision_rest_offset=collision_rest_offset,
        max_depenetration_velocity=(
            None
            if args_cli.star_max_depenetration_velocity is None
            else float(args_cli.star_max_depenetration_velocity)
        ),
        solver_position_iterations=(
            None
            if args_cli.star_solver_position_iterations is None
            else int(args_cli.star_solver_position_iterations)
        ),
        solver_velocity_iterations=(
            None
            if args_cli.star_solver_velocity_iterations is None
            else int(args_cli.star_solver_velocity_iterations)
        ),
    )
    star_rigid_object = (
        RigidObject(RigidObjectCfg(prim_path=str(star["prim_path"]))) if bool(star.get("dynamic")) else None
    )

    _log("creating fixture")
    fixture = _create_fixture(
        stage,
        root_path="/World/Kitting/Fixture",
        center=fixture_center,
        yaw_deg=float(args_cli.fixture_yaw_deg),
        size_x=fixture_size_x,
        size_y=fixture_size_y,
        thickness=fixture_thickness,
        star_outer_radius=star_outer_radius,
        star_inner_radius=star_inner_radius,
        clearance=fixture_clearance,
        mat=fixture_mat,
    )

    _add_box(stage, "/World/Floor", (0.0, 0.0, -0.015), (3.2, 2.8, 0.03), floor_mat, collision=True)

    dome = stage.DefinePrim("/World/DomeLight", "DomeLight")
    dome.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(650.0)
    dome.CreateAttribute("inputs:color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 0.98, 0.92))
    sun = stage.DefinePrim("/World/KeyLight", "DistantLight")
    sun.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1500.0)
    sun.CreateAttribute("inputs:angle", Sdf.ValueTypeNames.Float).Set(0.35)
    _set_xform(sun, (0.0, 0.0, 0.0), rotate_xyz_deg=(-45.0, 0.0, 35.0))
    grasp_candidate_markers = (
        _add_grasp_candidate_markers(
            stage,
            trajectory_data,
            max_count=max(0, int(args_cli.max_grasp_candidates)),
            axis_length=float(args_cli.grasp_candidate_axis_length),
            axis_thickness=float(args_cli.grasp_candidate_axis_thickness),
            x_mat=grasp_x_mat,
            y_mat=grasp_y_mat,
            z_mat=grasp_z_mat,
            target_mat=grasp_target_mat,
        )
        if bool(args_cli.show_grasp_candidates)
        else {"enabled": False, "reason": "disabled"}
    )

    settle_steps = max(0, int(args_cli.settle_steps))
    settled_transform_baked = _settle_scene(
        sim,
        stage,
        star,
        settle_steps,
        robot_articulation,
        star_rigid_object=star_rigid_object,
        contact_proxy_followers=franka_kinematic_contact_proxies,
        contact_debug_overlays=franka_contact_debug_visual_overlays,
    )
    trajectory_drives_star = (
        trajectory_data is not None and str(args_cli.franka_trajectory_object_mode) == "trajectory"
    )
    robot_collision_summary = _stage_collision_summary(stage, "/World/Robot")

    goal_pose = {
        "position": [
            float(fixture_center[0]),
            float(fixture_center[1]),
            float(surface_z + star_thickness / 2.0 + 0.001),
        ],
        "yaw_deg": float(args_cli.fixture_yaw_deg),
        "description": "Place the star centroid in the fixture hole and align yaw with the fixture slot.",
    }
    grasp_constraint_state: dict[str, object] = {
        "mode": str(args_cli.franka_grasp_constraint_mode),
        "attached": False,
        "failed": False,
        "close_threshold": float(args_cli.franka_grasp_constraint_close_threshold),
        "xy_threshold": float(args_cli.franka_grasp_constraint_xy_threshold),
        "z_threshold": float(args_cli.franka_grasp_constraint_z_threshold),
        "requires_dynamic_star": True,
        "requires_target_playback": True,
    }
    contact_debug_metadata = {
        "show_contact_debug": contact_debug_enabled,
        "show_franka_contact_proxies": show_franka_contact_proxies,
        "show_star_collision": show_star_collision,
        "opacity": contact_debug_opacity,
        "franka_contact_proxy_center": [float(v) for v in proxy_center],
        "franka_contact_proxy_size": [float(v) for v in proxy_size],
        "franka_contact_proxy_contact_offset": franka_proxy_contact_offset,
        "star_collision_contact_offset": star_collision_contact_offset,
        "collision_rest_offset": collision_rest_offset,
        "franka_visual_overlays": _contact_proxy_metadata(franka_contact_debug_visual_overlays),
    }
    metadata = {
        "generated_at_unix": time.time(),
        "task": "star_kitting",
        "task_description": "Pick the star-shaped object and place it into the matching star-shaped fixture.",
        "simulation_backend": "Isaac Sim / Isaac Lab / PhysX USD scene",
        "robot": _robot_metadata(robot_spec),
        "robot_runtime": _robot_runtime_metadata(robot_articulation),
        "robot_collision_summary": robot_collision_summary,
        "franka_contact_proxies": _contact_proxy_metadata(franka_contact_proxies),
        "franka_grasp_constraint": _contact_proxy_metadata(grasp_constraint_state),
        "contact_debug": contact_debug_metadata,
        "grasp_candidate_markers": grasp_candidate_markers,
        "robot_usd": str(robot_spec.usd_path) if robot_spec.usd_path else None,
        "robot_motion": {
            "mode": str(args_cli.franka_motion),
            "scale": float(args_cli.franka_motion_scale),
            "trajectory_playback": str(args_cli.franka_trajectory_playback),
            "trajectory_json": str(args_cli.franka_trajectory_json.expanduser().resolve())
            if args_cli.franka_trajectory_json is not None
            else None,
            "trajectory_frames": len(trajectory_data.get("frames", []))
            if isinstance(trajectory_data, dict) and isinstance(trajectory_data.get("frames"), list)
            else 0,
            "trajectory_object_id": str(args_cli.franka_trajectory_object_id),
            "trajectory_object_mode": str(args_cli.franka_trajectory_object_mode),
        },
        "axes": {
            "table_long_axis": "world_y",
            "table_short_axis": "world_x",
            "robot_base_origin": list(robot_spec.base_translation),
            "table_is_in_front_of_robot_at_negative_x": True,
        },
        "dimensions_m": {
            "table_short_x": table_short_x,
            "table_long_y": table_long_y,
            "table_height": table_height,
            "table_surface_z": surface_z,
            "star_outer_radius": star_outer_radius,
            "star_inner_radius": star_inner_radius,
            "star_thickness": star_thickness,
            "fixture_size_x": fixture_size_x,
            "fixture_size_y": fixture_size_y,
            "fixture_thickness": fixture_thickness,
            "fixture_clearance": fixture_clearance,
            "settle_steps": settle_steps,
            "settled_transform_baked_to_usd": settled_transform_baked,
        },
        "objects": {
            "star": star,
            "fixture": fixture,
            "goal_pose": goal_pose,
        },
        "simulation": {
            "simulation_context_created_before_scene_assets": True,
            "physics_device": str(args_cli.physics_device),
            "sim_dt": float(args_cli.physics_dt),
            "render_interval": 1,
            "default_static_friction": 1.0,
            "default_dynamic_friction": 1.0,
            "physx_bounce_threshold_velocity": 0.2,
            "physx_min_velocity_iteration_count": (
                max(0, int(args_cli.franka_solver_velocity_iterations))
                if int(args_cli.franka_solver_velocity_iterations) > 0
                else None
            ),
            "franka_max_depenetration_velocity": float(args_cli.franka_max_depenetration_velocity),
            "franka_solver_position_iterations": max(1, int(args_cli.franka_solver_position_iterations)),
            "franka_solver_velocity_iterations": max(0, int(args_cli.franka_solver_velocity_iterations)),
        },
        "checks": {
            "robot_selected": robot_spec.name,
            "uses_graspgenx_franka": robot_spec.name == "graspgenx_franka_panda",
            "franka_is_articulation": robot_spec.render_mode == "articulation_usd",
            "franka_has_actuators": bool(robot_spec.actuator_config),
            "franka_collision_prim_count": int(robot_collision_summary["num_collision_prims"]),
            "franka_trajectory_playback": args_cli.franka_motion == "trajectory",
            "franka_trajectory_state_playback": (
                args_cli.franka_motion == "trajectory" and args_cli.franka_trajectory_playback == "state"
            ),
            "franka_trajectory_object_replay": trajectory_drives_star,
            "franka_trajectory_physics_object": (
                args_cli.franka_motion == "trajectory" and args_cli.franka_trajectory_object_mode == "physics"
            ),
            "franka_trajectory_has_frames": bool(
                isinstance(trajectory_data, dict)
                and isinstance(trajectory_data.get("frames"), list)
                and len(trajectory_data.get("frames", [])) > 0
            ),
            "franka_scene_yaw_points_arm_toward_table": abs(((float(robot_spec.scene_yaw_deg or 0.0) % 360.0) - 180.0)) < 1.0e-6,
            "same_table_convention_as_clutter_bin_scene": True,
            "star_has_convex_child_colliders": True,
            "fixture_is_rectangular_block_with_star_through_hole": True,
            "goal_yaw_matches_fixture_yaw": abs(goal_pose["yaw_deg"] - float(args_cli.fixture_yaw_deg)) < 1.0e-9,
            "star_starts_on_negative_y_side": pickup_y < 0.0,
            "fixture_starts_on_positive_y_side": fixture_y > 0.0,
        },
    }
    _log("writing metadata")
    _write_metadata(output_dir / "scene_metadata.json", metadata)

    if trajectory_drives_star:
        _apply_trajectory_object_pose(
            stage,
            str(star["prim_path"]),
            trajectory_data,
            0,
            1,
            str(args_cli.franka_trajectory_object_id),
        )

    usd_path = output_dir / "star_kitting_env.usda"
    _log(f"exporting USD: {usd_path}")
    stage.GetRootLayer().Export(str(usd_path))

    table_target = (table_center_x, 0.0, surface_z + 0.13)
    views = {
        "overview": ((0.45, -0.92, 2.10), (-0.50, 0.0, surface_z + 0.12)),
        "robot_side": ((1.35, 0.0, 1.42), (table_center_x, 0.0, surface_z + 0.18)),
        "topdown": ((table_center_x, 0.0, 2.10), (table_center_x, 0.0, surface_z + 0.02)),
        "pickup_close": ((0.08, pickup_y - 0.47, 1.25), (table_center_x, pickup_y, surface_z + 0.08)),
        "fixture_close": ((0.08, fixture_y - 0.47, 1.25), (table_center_x, fixture_y, surface_z + 0.08)),
    }
    name = str(args_cli.view)
    eye, look_at = views[name]
    robot_motion_trace: list[dict[str, object]] = []
    star_motion_trace: list[dict[str, object]] = []

    def trajectory_frame_callback(frame_idx: int, frame_count: int) -> None:
        if not trajectory_drives_star:
            return
        _apply_trajectory_object_pose(
            stage,
            str(star["prim_path"]),
            trajectory_data,
            frame_idx,
            frame_count,
            str(args_cli.franka_trajectory_object_id),
        )

    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "view": name,
            "capture_video": bool(args_cli.capture_video),
            "franka_motion": str(args_cli.franka_motion),
            "franka_trajectory_playback": str(args_cli.franka_trajectory_playback),
            "franka_trajectory_object_mode": str(args_cli.franka_trajectory_object_mode),
            "show_grasp_candidates": bool(args_cli.show_grasp_candidates),
            "grasp_candidate_markers": grasp_candidate_markers,
            "contact_debug": contact_debug_metadata,
            "franka_trajectory_json": str(args_cli.franka_trajectory_json.expanduser().resolve())
            if args_cli.franka_trajectory_json is not None
            else None,
        },
    )
    if bool(args_cli.capture_video):
        if name != "overview":
            raise ValueError("--capture_video is currently overview-only")
        frame_paths = _capture_overview_video(
            sim=sim,
            robot_articulation=robot_articulation,
            eye=eye,
            target=look_at,
            output_dir=output_dir,
            fps=int(args_cli.fps),
            seconds=float(args_cli.video_seconds),
            sim_steps_per_frame=int(args_cli.sim_steps_per_frame),
            frame_callback=trajectory_frame_callback if trajectory_data is not None else None,
            robot_motion_trace=robot_motion_trace,
            object_motion_trace=star_motion_trace,
            object_stage=stage,
            object_prim_path=str(star["prim_path"]),
            object_rigid_object=star_rigid_object,
            contact_proxy_followers=franka_kinematic_contact_proxies,
            contact_debug_overlays=franka_contact_debug_visual_overlays,
            grasp_constraint_state=grasp_constraint_state,
        )
        rendered = {"overview_frames": frame_paths}
    else:
        if trajectory_data is not None:
            trajectory_frame_callback(0, 1)
        object_record = _rigid_object_motion_record(
            star_rigid_object,
            str(star["prim_path"]),
            0,
            1,
        ) or _object_motion_record(stage, str(star["prim_path"]), 0, 1)
        if object_record is not None:
            star_motion_trace.append(object_record)
        _log(f"capturing view: {name}")
        rendered = {name: str(_capture_view(name, eye, look_at, output_dir))}

    star_motion_path = output_dir / "star_motion_trajectory.json"
    _write_metadata(
        star_motion_path,
        {
            "object_mode": str(args_cli.franka_trajectory_object_mode),
            "object_replay_enabled": bool(trajectory_drives_star),
            "franka_grasp_constraint": _contact_proxy_metadata(grasp_constraint_state),
            "star_motion_trajectory": star_motion_trace,
        },
    )
    robot_motion_path = output_dir / "robot_motion_trajectory.json"
    _write_metadata(
        robot_motion_path,
        {
            "motion": str(args_cli.franka_motion),
            "trajectory_playback": str(args_cli.franka_trajectory_playback),
            "franka_grasp_constraint": _contact_proxy_metadata(grasp_constraint_state),
            "robot_motion_trajectory": robot_motion_trace,
        },
    )

    _log("writing render manifest")
    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "renders": rendered,
            "fps": int(args_cli.fps),
            "video_seconds": float(args_cli.video_seconds),
            "sim_steps_per_frame": int(args_cli.sim_steps_per_frame),
            "franka_motion": str(args_cli.franka_motion),
            "franka_trajectory_playback": str(args_cli.franka_trajectory_playback),
            "franka_trajectory_object_mode": str(args_cli.franka_trajectory_object_mode),
            "franka_trajectory_json": str(args_cli.franka_trajectory_json.expanduser().resolve())
            if args_cli.franka_trajectory_json is not None
            else None,
            "show_grasp_candidates": bool(args_cli.show_grasp_candidates),
            "grasp_candidate_markers": grasp_candidate_markers,
            "contact_debug": contact_debug_metadata,
            "franka_grasp_constraint": _contact_proxy_metadata(grasp_constraint_state),
            "star_motion_trajectory": str(star_motion_path),
            "robot_motion_trajectory": str(robot_motion_path),
        },
    )

    print(f"Wrote star-kitting scene renders to {output_dir}")
    print(f"Star dynamic: {bool(args_cli.dynamic_star)}")
    print(f"USD: {usd_path}")
    sim.clear_all_callbacks()
    sim.clear_instance()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
