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
import time
from pathlib import Path
from typing import Iterable

from isaaclab.app import AppLauncher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=Path("/tmp/dextrah_star_kitting"))
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--video_seconds", type=float, default=3.0)
    parser.add_argument("--capture_video", action="store_true", help="Capture an overview PNG sequence.")
    parser.add_argument("--sim_steps_per_frame", type=int, default=2)
    parser.add_argument("--settle_steps", type=int, default=30)
    parser.add_argument("--physics_device", default="cpu", help="PhysX device used by SimulationContext.")
    parser.add_argument("--star_outer_radius", type=float, default=0.092)
    parser.add_argument("--star_inner_radius", type=float, default=0.042)
    parser.add_argument("--star_thickness", type=float, default=0.034)
    parser.add_argument("--fixture_size_x", type=float, default=0.33)
    parser.add_argument("--fixture_size_y", type=float, default=0.33)
    parser.add_argument("--fixture_thickness", type=float, default=0.052)
    parser.add_argument("--fixture_clearance", type=float, default=0.012)
    parser.add_argument("--star_start_yaw_deg", type=float, default=-24.0)
    parser.add_argument("--fixture_yaw_deg", type=float, default=18.0)
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
from isaaclab.sensors.camera import TiledCamera, TiledCameraCfg  # noqa: E402
from isaaclab.sim import PhysxCfg, SimulationCfg  # noqa: E402
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg  # noqa: E402
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

try:
    from isaacsim.core.utils.stage import create_new_stage, update_stage
except Exception:  # Isaac Sim 4.x fallback namespace
    from omni.isaac.core.utils.stage import create_new_stage, update_stage  # type: ignore


Color = tuple[float, float, float]
Point2 = tuple[float, float]


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
) -> None:
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in translate]))
    if rotate_xyz_deg is not None:
        xformable.AddRotateXYZOp().Set(Gf.Vec3f(*[float(v) for v in rotate_xyz_deg]))
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


def _add_box(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: UsdShade.Material,
    *,
    collision: bool = True,
) -> Usd.Prim:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    _set_xform(prim, center, size)
    _bind(prim, mat)
    if collision:
        _apply_collision(prim, approximation="box")
    return prim


def _apply_collision(prim: Usd.Prim, *, approximation: str = "none") -> None:
    UsdPhysics.CollisionAPI.Apply(prim)
    mesh_collision_api_cls = getattr(UsdPhysics, "MeshCollisionAPI", None)
    if mesh_collision_api_cls is not None:
        try:
            mesh_collision_api = mesh_collision_api_cls.Apply(prim)
            mesh_collision_api.CreateApproximationAttr().Set(str(approximation))
        except Exception:
            pass
    try:
        PhysxSchema.PhysxCollisionAPI.Apply(prim)
    except Exception:
        pass


def _make_rigid_body(prim: Usd.Prim, *, density: float) -> None:
    rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
    try:
        rb_api.CreateRigidBodyEnabledAttr(True)
        rb_api.CreateStartsAsleepAttr(False)
    except Exception:
        pass
    mass_api = UsdPhysics.MassAPI.Apply(prim)
    mass_api.CreateDensityAttr(float(density))


def _create_sim_context():
    _log(f"creating SimulationContext on physics_device={args_cli.physics_device}")
    sim_cfg = SimulationCfg(
        dt=1.0 / 60.0,
        render_interval=1,
        device=str(args_cli.physics_device),
        physics_prim_path="/World/physicsScene",
        physics_material=RigidBodyMaterialCfg(static_friction=1.0, dynamic_friction=1.0),
        physx=PhysxCfg(
            bounce_threshold_velocity=0.2,
            gpu_max_rigid_patch_count=4 * 5 * 2**15,
        ),
    )
    return sim_utils.SimulationContext(sim_cfg)


def _create_robot(stage: Usd.Stage, robot_usd: Path) -> None:
    robot = UsdGeom.Xform.Define(stage, "/World/Robot").GetPrim()
    robot.GetReferences().AddReference(str(robot_usd))
    _set_xform(robot, (0.0, 0.0, 0.0), rotate_xyz_deg=(0.0, 0.0, 0.0))


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
        _apply_collision(prim, approximation=approximation)
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
) -> dict[str, object]:
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    _set_xform(root, center, rotate_xyz_deg=(0.0, 0.0, float(yaw_deg)))
    if dynamic:
        _make_rigid_body(root, density=520.0)

    vertices = _star_vertices(outer_radius, inner_radius)
    _add_extruded_polygon_mesh(
        stage,
        f"{root_path}/visual",
        vertices,
        thickness,
        visual_mat,
        fan_center=(0.0, 0.0),
        collision=False,
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
            visible=False,
        )

    return {
        "prim_path": root_path,
        "center": list(center),
        "yaw_deg": float(yaw_deg),
        "outer_radius": float(outer_radius),
        "inner_radius": float(inner_radius),
        "thickness": float(thickness),
        "dynamic": bool(dynamic),
        "collision_pieces": len(vertices),
        "collision_model": "ten convex triangular-prism child colliders under one rigid body",
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


def _settle_scene(sim, stage: Usd.Stage, star_record: dict[str, object], settle_steps: int) -> bool:
    if settle_steps <= 0 or not bool(star_record.get("dynamic")):
        return False
    _log(f"settling dynamic star for {settle_steps} physics steps")
    sim.reset()
    for _ in range(settle_steps):
        sim.step(render=False)
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
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    output_dir: Path,
    fps: int,
    seconds: float,
    sim_steps_per_frame: int,
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

    _log(f"capturing overview video frames with TiledCamera: {frame_count} frames")
    for frame_idx in range(frame_count):
        step_count = 1 if frame_idx == 0 else max(1, int(sim_steps_per_frame))
        for _ in range(step_count):
            sim.step(render=False)
        sim.render()
        camera.update(float(sim.cfg.dt) * step_count)
        dst = frames_dir / f"overview_{frame_idx:04d}.png"
        _log(f"capturing overview frame {frame_idx + 1}/{frame_count}")
        _save_rgb_tensor(dst, camera.data.output["rgb"][0])
        frames.append(str(dst))

    del camera
    return frames


def main() -> None:
    output_dir = args_cli.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"output_dir={output_dir}")

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

    robot_usd = _repo_root() / "dextrah_lab/assets/kuka_allegro/kuka_allegro_colored.usd"
    if not robot_usd.exists():
        raise FileNotFoundError(f"Robot USD is missing: {robot_usd}")
    if _is_git_lfs_pointer(robot_usd):
        raise RuntimeError(
            f"Robot USD is a Git LFS pointer, not a materialized USD asset: {robot_usd}. "
            "Run `git lfs pull` before rendering."
        )

    _log("creating materials")
    table_mat = _material(stage, "/World/Looks/table_matte", (0.54, 0.50, 0.44))
    leg_mat = _material(stage, "/World/Looks/table_dark", (0.20, 0.22, 0.24))
    floor_mat = _material(stage, "/World/Looks/floor_gray", (0.28, 0.30, 0.31))
    star_mat = _material(stage, "/World/Looks/star_yellow", (0.95, 0.70, 0.16), roughness=0.55)
    collision_mat = _material(stage, "/World/Looks/collision_hidden", (0.95, 0.70, 0.16), roughness=0.55)
    fixture_mat = _material(stage, "/World/Looks/fixture_graphite", (0.16, 0.18, 0.19), roughness=0.47)

    # Match the current clutter-bin scene table and robot convention.
    table_height = 0.72
    table_top_thick = 0.052
    table_center_x = -0.72
    table_short_x = 0.90
    table_long_y = 1.32
    pickup_y = -0.26
    fixture_y = 0.26

    _log(f"referencing robot USD: {robot_usd}")
    _create_robot(stage, robot_usd)

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
        collision_mat=collision_mat,
        dynamic=bool(args_cli.dynamic_star),
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

    settle_steps = max(0, int(args_cli.settle_steps))
    settled_transform_baked = _settle_scene(sim, stage, star, settle_steps)

    goal_pose = {
        "position": [
            float(fixture_center[0]),
            float(fixture_center[1]),
            float(surface_z + star_thickness / 2.0 + 0.001),
        ],
        "yaw_deg": float(args_cli.fixture_yaw_deg),
        "description": "Place the star centroid in the fixture hole and align yaw with the fixture slot.",
    }
    metadata = {
        "generated_at_unix": time.time(),
        "task": "star_kitting",
        "task_description": "Pick the star-shaped object and place it into the matching star-shaped fixture.",
        "simulation_backend": "Isaac Sim / Isaac Lab / PhysX USD scene",
        "robot_usd": str(robot_usd),
        "axes": {
            "table_long_axis": "world_y",
            "table_short_axis": "world_x",
            "robot_base_origin": [0.0, 0.0, 0.0],
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
            "sim_dt": 1.0 / 60.0,
            "render_interval": 1,
            "default_static_friction": 1.0,
            "default_dynamic_friction": 1.0,
            "physx_bounce_threshold_velocity": 0.2,
        },
        "checks": {
            "same_robot_as_clutter_bin_scene": True,
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

    usd_path = output_dir / "star_kitting_env.usda"
    _log(f"exporting USD: {usd_path}")
    stage.GetRootLayer().Export(str(usd_path))

    table_target = (table_center_x, 0.0, surface_z + 0.13)
    views = {
        "overview": ((0.25, -0.76, 2.45), table_target),
        "robot_side": ((1.35, 0.0, 1.42), (table_center_x, 0.0, surface_z + 0.18)),
        "topdown": ((table_center_x, 0.0, 2.10), (table_center_x, 0.0, surface_z + 0.02)),
        "pickup_close": ((0.08, pickup_y - 0.47, 1.25), (table_center_x, pickup_y, surface_z + 0.08)),
        "fixture_close": ((0.08, fixture_y - 0.47, 1.25), (table_center_x, fixture_y, surface_z + 0.08)),
    }
    name = str(args_cli.view)
    eye, look_at = views[name]
    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "view": name,
            "capture_video": bool(args_cli.capture_video),
        },
    )
    if bool(args_cli.capture_video):
        if name != "overview":
            raise ValueError("--capture_video is currently overview-only")
        frame_paths = _capture_overview_video(
            sim=sim,
            eye=eye,
            target=look_at,
            output_dir=output_dir,
            fps=int(args_cli.fps),
            seconds=float(args_cli.video_seconds),
            sim_steps_per_frame=int(args_cli.sim_steps_per_frame),
        )
        rendered = {"overview_frames": frame_paths}
    else:
        _log(f"capturing view: {name}")
        rendered = {name: str(_capture_view(name, eye, look_at, output_dir))}

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
