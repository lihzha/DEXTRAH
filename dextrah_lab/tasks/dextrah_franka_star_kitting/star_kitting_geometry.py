"""Procedural USD geometry for the Franka star-kitting task."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade


Color = tuple[float, float, float]
Point2 = tuple[float, float]


@dataclass(frozen=True)
class StarKittingGeometryCfg:
    """Geometry parameters shared by training, eval, and validation."""

    star_outer_radius: float = 0.032
    star_inner_radius: float = 0.0145
    star_thickness: float = 0.045
    fixture_size_x: float = 0.18
    fixture_size_y: float = 0.18
    fixture_thickness: float = 0.060
    fixture_clearance: float = 0.006
    star_density: float = 220.0


def star_vertices(outer_radius: float, inner_radius: float, *, points: int = 5) -> list[Point2]:
    """Return a counter-clockwise 2-D star polygon centered at the origin."""

    vertices: list[Point2] = []
    for idx in range(points * 2):
        radius = outer_radius if idx % 2 == 0 else inner_radius
        angle = idx * math.pi / points
        vertices.append((radius * math.cos(angle), radius * math.sin(angle)))
    return vertices


def star_fits_franka_gripper(outer_radius: float, max_gripper_width: float, margin: float = 0.004) -> bool:
    """Conservative planar graspability check for the Panda parallel gripper."""

    return 2.0 * float(outer_radius) <= float(max_gripper_width) - float(margin)


def fixture_hole_radii(cfg: StarKittingGeometryCfg) -> tuple[float, float]:
    """Return the effective outer/inner radii of the star-shaped fixture hole."""

    return (
        cfg.star_outer_radius + cfg.fixture_clearance,
        cfg.star_inner_radius + 0.55 * cfg.fixture_clearance,
    )


def geometry_diagnostics(cfg: StarKittingGeometryCfg, *, max_gripper_width: float) -> dict[str, object]:
    """Return deterministic checks used by the environment validation gate."""

    hole_outer, hole_inner = fixture_hole_radii(cfg)
    star_fits_hole = (
        cfg.fixture_clearance > 0.0
        and hole_outer > cfg.star_outer_radius
        and hole_inner > cfg.star_inner_radius
        and 2.0 * hole_outer < cfg.fixture_size_x
        and 2.0 * hole_outer < cfg.fixture_size_y
        and cfg.star_thickness < cfg.fixture_thickness
    )
    return {
        "star_outer_radius": cfg.star_outer_radius,
        "star_inner_radius": cfg.star_inner_radius,
        "star_thickness": cfg.star_thickness,
        "fixture_size_x": cfg.fixture_size_x,
        "fixture_size_y": cfg.fixture_size_y,
        "fixture_thickness": cfg.fixture_thickness,
        "fixture_clearance": cfg.fixture_clearance,
        "hole_outer_radius": hole_outer,
        "hole_inner_radius": hole_inner,
        "max_gripper_width": max_gripper_width,
        "star_fits_franka_gripper": star_fits_franka_gripper(cfg.star_outer_radius, max_gripper_width),
        "star_fits_fixture_hole": star_fits_hole,
        "star_collision_model": "ten convex triangular-prism child colliders under one rigid body",
        "fixture_collision_model": "static triangle mesh with exact star-shaped through-hole",
    }


def _polygon_area(vertices: list[Point2]) -> float:
    area = 0.0
    for idx, p in enumerate(vertices):
        q = vertices[(idx + 1) % len(vertices)]
        area += p[0] * q[1] - q[0] * p[1]
    return 0.5 * area


def _set_xform(prim: Usd.Prim, translate: tuple[float, float, float], yaw_deg: float = 0.0) -> None:
    xformable = UsdGeom.Xformable(prim)
    xformable.ClearXformOpOrder()
    xformable.AddTranslateOp().Set(Gf.Vec3d(*[float(v) for v in translate]))
    if abs(float(yaw_deg)) > 1.0e-12:
        xformable.AddRotateXYZOp().Set(Gf.Vec3f(0.0, 0.0, float(yaw_deg)))


def material(stage: Usd.Stage, path: str, color: Color, roughness: float = 0.65) -> UsdShade.Material:
    """Create or return a preview-surface material."""

    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def _bind(prim: Usd.Prim, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def _apply_collision(prim: Usd.Prim, *, approximation: str) -> None:
    UsdPhysics.CollisionAPI.Apply(prim)
    mesh_collision_api_cls = getattr(UsdPhysics, "MeshCollisionAPI", None)
    if mesh_collision_api_cls is not None:
        mesh_collision_api = mesh_collision_api_cls.Apply(prim)
        mesh_collision_api.CreateApproximationAttr().Set(str(approximation))
    try:
        PhysxSchema.PhysxCollisionAPI.Apply(prim)
    except Exception:
        pass


def _make_rigid_body(prim: Usd.Prim, *, density: float) -> None:
    rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
    rb_api.CreateRigidBodyEnabledAttr(True)
    rb_api.CreateStartsAsleepAttr(False)
    mass_api = UsdPhysics.MassAPI.Apply(prim)
    mass_api.CreateDensityAttr(float(density))


def _add_mesh(
    stage: Usd.Stage,
    path: str,
    points: list[Gf.Vec3f],
    face_vertex_counts: list[int],
    face_vertex_indices: list[int],
    mat: UsdShade.Material,
    *,
    collision: bool,
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
    mesh.CreateExtentAttr([Gf.Vec3f(min(xs), min(ys), min(zs)), Gf.Vec3f(max(xs), max(ys), max(zs))])
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
    collision: bool,
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
    corners = [(half_x, half_y), (-half_x, half_y), (-half_x, -half_y), (half_x, -half_y)]
    result: list[tuple[float, Point2]] = []
    for corner in corners:
        base_angle = math.atan2(corner[1], corner[0])
        while base_angle <= angle_a:
            base_angle += 2.0 * math.pi
        if base_angle < angle_b - 1.0e-9:
            result.append((base_angle, corner))
    result.sort(key=lambda item: item[0])
    return [corner for _, corner in result]


def create_star_object(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    yaw_deg: float,
    cfg: StarKittingGeometryCfg,
    visual_mat: UsdShade.Material,
    collision_mat: UsdShade.Material,
) -> dict[str, object]:
    """Create the dynamic star body with visible star mesh and convex child colliders."""

    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    _set_xform(root, center, yaw_deg=float(yaw_deg))
    _make_rigid_body(root, density=cfg.star_density)

    vertices = star_vertices(cfg.star_outer_radius, cfg.star_inner_radius)
    _add_extruded_polygon_mesh(
        stage,
        f"{root_path}/visual",
        vertices,
        cfg.star_thickness,
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
            cfg.star_thickness,
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
        "outer_radius": cfg.star_outer_radius,
        "inner_radius": cfg.star_inner_radius,
        "thickness": cfg.star_thickness,
        "collision_pieces": len(vertices),
    }


def create_fixture(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    yaw_deg: float,
    cfg: StarKittingGeometryCfg,
    mat: UsdShade.Material,
) -> dict[str, object]:
    """Create a static rectangular fixture with an exact star-shaped through-hole."""

    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    _set_xform(root, center, yaw_deg=float(yaw_deg))
    hole_outer, hole_inner = fixture_hole_radii(cfg)
    hole_vertices = star_vertices(hole_outer, hole_inner)

    half_x = 0.5 * float(cfg.fixture_size_x)
    half_y = 0.5 * float(cfg.fixture_size_y)
    z0 = -0.5 * float(cfg.fixture_thickness)
    z1 = 0.5 * float(cfg.fixture_thickness)
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

    def add_cap_polygon(poly: list[Point2]) -> None:
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

    def add_side(p: Point2, q: Point2, *, inward: bool) -> None:
        if math.dist(p, q) <= 1.0e-9:
            return
        counts.append(4)
        if inward:
            indices.extend([point_idx(q, z0), point_idx(p, z0), point_idx(p, z1), point_idx(q, z1)])
        else:
            indices.extend([point_idx(p, z0), point_idx(q, z0), point_idx(q, z1), point_idx(p, z1)])

    n = len(hole_vertices)
    step = 2.0 * math.pi / n
    angles = [idx * step for idx in range(n + 1)]
    outer_points = [_ray_rectangle_intersection(angle, half_x, half_y) for angle in angles]
    for idx in range(n):
        hole_a = hole_vertices[idx]
        hole_b = hole_vertices[(idx + 1) % n]
        outer_a = outer_points[idx]
        outer_b = outer_points[idx + 1]
        outer_chain = [outer_a] + _rectangle_corners_between(angles[idx], angles[idx + 1], half_x, half_y) + [outer_b]
        add_cap_polygon([hole_a] + outer_chain + [hole_b])
        for p, q in zip(outer_chain, outer_chain[1:]):
            add_side(p, q, inward=False)
        add_side(hole_a, hole_b, inward=True)

    _add_mesh(
        stage,
        f"{root_path}/block_with_star_hole",
        points,
        counts,
        indices,
        mat,
        collision=True,
        approximation="none",
    )

    return {
        "prim_path": root_path,
        "center": list(center),
        "yaw_deg": float(yaw_deg),
        "size_x": cfg.fixture_size_x,
        "size_y": cfg.fixture_size_y,
        "thickness": cfg.fixture_thickness,
        "hole_outer_radius": hole_outer,
        "hole_inner_radius": hole_inner,
    }
