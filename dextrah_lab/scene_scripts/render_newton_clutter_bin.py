#!/usr/bin/env python3
"""Render the DEXTRAH clutter-bin sphere drop with Newton and OpenGL.

This is a lightweight counterpart to ``render_clutter_bin_env.py``: it keeps
the same DEXTRAH table/bin dimensions, but uses Newton for rigid-body physics
and pyrender's EGL/OpenGL path for MP4 frames.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

# Match the GraspGenX end2end renderer: select EGL before importing pyrender.
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("PYGLET_HEADLESS", "true")

import newton
import numpy as np
import pyrender
import trimesh
import trimesh.transformations as tra
import warp as wp
from PIL import Image


LOG = logging.getLogger("dextrah-newton-bin")


@dataclass(frozen=True)
class ShapeParams:
    mu: float
    ke: float
    kd: float
    kf: float
    gap: float | None = None
    margin: float | None = None


@dataclass
class SphereSpec:
    object_id: str
    body_idx: int
    radius: float
    mass: float
    color: tuple[float, float, float, float]
    initial_position: tuple[float, float, float]
    layer: int
    row: int
    col: int


@dataclass
class SceneDims:
    bin_l: float
    bin_h: float
    bin_gap: float
    wall: float
    bottom: float
    table_height: float
    table_top_thick: float
    table_top_z: float
    table_short_x: float
    table_long_y: float
    table_center_x: float
    bin_center_x: float
    left_bin_y: float
    right_bin_y: float
    inner_floor_z: float
    inner_top_z: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=Path("/tmp/dextrah_newton_clutter_bin"))
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--video_seconds", type=float, default=5.0)
    parser.add_argument("--physics_dt", type=float, default=0.002)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--bin_l", type=float, default=0.48)
    parser.add_argument("--gripper_open_width", type=float, default=0.09)
    parser.add_argument(
        "--sphere_count",
        type=int,
        default=27,
        help="Number of falling spheres. Keep <=27 for SolverMuJoCo contact bitmask compatibility.",
    )
    parser.add_argument("--sphere_grid", type=int, default=4)
    parser.add_argument("--drop_height", type=float, default=0.34)
    parser.add_argument("--solver_iterations", type=int, default=80)
    parser.add_argument("--solver_ls_iterations", type=int, default=40)
    parser.add_argument("--solver_impratio", type=float, default=1000.0)
    parser.add_argument("--collide_substeps", type=int, default=4)
    parser.add_argument("--contact_max", type=int, default=262144)
    parser.add_argument("--sphere_mu", type=float, default=1.2)
    parser.add_argument("--static_mu", type=float, default=1.4)
    parser.add_argument("--contact_ke", type=float, default=5.0e4)
    parser.add_argument("--contact_kd", type=float, default=5.0e2)
    parser.add_argument("--contact_kf", type=float, default=1.0e3)
    parser.add_argument("--free_joint_armature", type=float, default=0.002)
    parser.add_argument("--no_encode", action="store_true", help="Write frames/metadata but skip MP4 encoding.")
    parser.add_argument("--camera_eye", type=float, nargs=3, default=None)
    parser.add_argument("--camera_target", type=float, nargs=3, default=None)
    return parser.parse_args()


def _normalize(v: np.ndarray, eps: float = 1.0e-12) -> np.ndarray:
    norm = float(np.linalg.norm(v))
    if norm < eps:
        return v
    return v / norm


def camera_pose_from_lookat(
    eye: Iterable[float],
    target: Iterable[float],
    up: Iterable[float] = (0.0, 0.0, 1.0),
) -> np.ndarray:
    eye_np = np.asarray(list(eye), dtype=float)
    target_np = np.asarray(list(target), dtype=float)
    up_np = np.asarray(list(up), dtype=float)

    z_axis = _normalize(eye_np - target_np)
    x_axis = _normalize(np.cross(up_np, z_axis))
    if np.linalg.norm(x_axis) < 1.0e-8:
        alt_up = np.array([0.0, 1.0, 0.0]) if abs(up_np[2]) > 0.9 else np.array([0.0, 0.0, 1.0])
        x_axis = _normalize(np.cross(alt_up, z_axis))
    y_axis = np.cross(z_axis, x_axis)

    pose = np.eye(4)
    pose[:3, 0] = x_axis
    pose[:3, 1] = y_axis
    pose[:3, 2] = z_axis
    pose[:3, 3] = eye_np
    return pose


def _wp_transform(center: tuple[float, float, float]) -> wp.transform:
    return wp.transform(
        wp.vec3(float(center[0]), float(center[1]), float(center[2])),
        wp.quat(0.0, 0.0, 0.0, 1.0),
    )


def _shape_cfg(params: ShapeParams):
    kwargs = {
        "is_hydroelastic": False,
        "ke": float(params.ke),
        "kd": float(params.kd),
        "kf": float(params.kf),
        "mu": float(params.mu),
    }
    if params.gap is not None:
        kwargs["gap"] = float(params.gap)
    if params.margin is not None:
        kwargs["margin"] = float(params.margin)
    return newton.ModelBuilder.ShapeConfig(**kwargs)


def _add_static_box(
    builder,
    *,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    params: ShapeParams,
    label: str,
) -> None:
    hx, hy, hz = (float(v) / 2.0 for v in size)
    try:
        builder.add_shape_box(
            body=-1,
            xform=_wp_transform(center),
            hx=hx,
            hy=hy,
            hz=hz,
            cfg=_shape_cfg(params),
            label=label,
        )
    except TypeError:
        builder.add_shape_box(
            body=-1,
            pos=center,
            rot=wp.quat(0.0, 0.0, 0.0, 1.0),
            hx=hx,
            hy=hy,
            hz=hz,
            density=0.0,
            ke=params.ke,
            kd=params.kd,
            kf=params.kf,
            mu=params.mu,
        )


def _add_dynamic_sphere(
    builder,
    *,
    center: tuple[float, float, float],
    radius: float,
    mass: float,
    params: ShapeParams,
    armature: float,
    label: str,
) -> int:
    xform = _wp_transform(center)
    try:
        body_idx = builder.add_body(xform=xform, mass=float(mass), label=label)
    except TypeError:
        body_idx = builder.add_body(origin=xform, m=float(mass))
        builder.add_joint_free(child=body_idx)
        joint_idx = builder.joint_count - 1
        q_start = int(builder.joint_q_start[joint_idx])
        builder.joint_q[q_start + 0] = center[0]
        builder.joint_q[q_start + 1] = center[1]
        builder.joint_q[q_start + 2] = center[2]
        builder.joint_q[q_start + 3] = 0.0
        builder.joint_q[q_start + 4] = 0.0
        builder.joint_q[q_start + 5] = 0.0
        builder.joint_q[q_start + 6] = 1.0

    joint_idx = builder.joint_count - 1
    if joint_idx >= 0 and hasattr(builder, "joint_qd_start") and hasattr(builder, "joint_armature"):
        qd_start = int(builder.joint_qd_start[joint_idx])
        for qd_idx in range(qd_start, len(builder.joint_armature)):
            builder.joint_armature[qd_idx] = float(armature)

    try:
        builder.add_shape_sphere(
            body=body_idx,
            xform=wp.transform_identity(),
            radius=float(radius),
            cfg=_shape_cfg(params),
            label=label,
        )
    except TypeError:
        builder.add_shape_sphere(
            body=body_idx,
            pos=(0.0, 0.0, 0.0),
            rot=wp.quat(0.0, 0.0, 0.0, 1.0),
            radius=float(radius),
            density=0.0,
            ke=params.ke,
            kd=params.kd,
            kf=params.kf,
            mu=params.mu,
        )
    return int(body_idx)


def _scene_dims(bin_l: float) -> SceneDims:
    bin_h = 0.75 * bin_l
    bin_gap = 0.08
    wall = 0.025
    bottom = 0.025
    table_height = 0.72
    table_top_thick = 0.052
    table_top_z = table_height + table_top_thick / 2.0
    table_short_x = bin_l + 0.42
    table_long_y = 2.0 * bin_l + bin_gap + 0.28
    table_center_x = -0.72
    bin_center_x = table_center_x
    bin_center_offset_y = bin_l / 2.0 + bin_gap / 2.0
    left_bin_y = -bin_center_offset_y
    right_bin_y = bin_center_offset_y
    return SceneDims(
        bin_l=bin_l,
        bin_h=bin_h,
        bin_gap=bin_gap,
        wall=wall,
        bottom=bottom,
        table_height=table_height,
        table_top_thick=table_top_thick,
        table_top_z=table_top_z,
        table_short_x=table_short_x,
        table_long_y=table_long_y,
        table_center_x=table_center_x,
        bin_center_x=bin_center_x,
        left_bin_y=left_bin_y,
        right_bin_y=right_bin_y,
        inner_floor_z=table_top_z + bottom,
        inner_top_z=table_top_z + bottom + bin_h,
    )


def _box_mesh(center: tuple[float, float, float], size: tuple[float, float, float]) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(center)
    return mesh


def _static_items(dims: SceneDims) -> list[dict]:
    items: list[dict] = []

    def add_box(name: str, center, size, color) -> None:
        items.append({"name": name, "mesh": _box_mesh(center, size), "color": color, "center": center, "size": size})

    table_color = (0.54, 0.50, 0.44, 1.0)
    leg_color = (0.20, 0.22, 0.24, 1.0)
    bin_color = (0.18, 0.43, 0.78, 1.0)
    bin_edge_color = (0.02, 0.13, 0.30, 1.0)
    floor_color = (0.32, 0.33, 0.34, 1.0)

    add_box(
        "table_top",
        (dims.table_center_x, 0.0, dims.table_height),
        (dims.table_short_x, dims.table_long_y, dims.table_top_thick),
        table_color,
    )
    leg_xs = [
        dims.table_center_x - dims.table_short_x / 2.0 + 0.08,
        dims.table_center_x + dims.table_short_x / 2.0 - 0.08,
    ]
    leg_ys = [-dims.table_long_y / 2.0 + 0.08, dims.table_long_y / 2.0 - 0.08]
    leg_idx = 0
    for lx in leg_xs:
        for ly in leg_ys:
            add_box(f"table_leg_{leg_idx}", (lx, ly, dims.table_height / 2.0), (0.05, 0.05, dims.table_height), leg_color)
            leg_idx += 1

    def add_bin(prefix: str, cx: float, cy: float) -> None:
        floor_z = dims.table_top_z + dims.bottom / 2.0
        wall_z = dims.table_top_z + dims.bottom + dims.bin_h / 2.0
        outer_l = dims.bin_l + 2.0 * dims.wall
        add_box(f"{prefix}_floor", (cx, cy, floor_z), (outer_l, outer_l, dims.bottom), bin_color)
        add_box(
            f"{prefix}_front_wall",
            (cx + dims.bin_l / 2.0 + dims.wall / 2.0, cy, wall_z),
            (dims.wall, outer_l, dims.bin_h),
            bin_color,
        )
        add_box(
            f"{prefix}_back_wall",
            (cx - dims.bin_l / 2.0 - dims.wall / 2.0, cy, wall_z),
            (dims.wall, outer_l, dims.bin_h),
            bin_color,
        )
        add_box(
            f"{prefix}_left_wall",
            (cx, cy - dims.bin_l / 2.0 - dims.wall / 2.0, wall_z),
            (dims.bin_l, dims.wall, dims.bin_h),
            bin_color,
        )
        add_box(
            f"{prefix}_right_wall",
            (cx, cy + dims.bin_l / 2.0 + dims.wall / 2.0, wall_z),
            (dims.bin_l, dims.wall, dims.bin_h),
            bin_color,
        )

        edge = dims.wall * 0.55
        edge_z = dims.table_top_z + dims.bottom + dims.bin_h + edge / 2.0
        half_outer = outer_l / 2.0
        add_box(f"{prefix}_rim_front", (cx + half_outer, cy, edge_z), (edge, outer_l, edge), bin_edge_color)
        add_box(f"{prefix}_rim_back", (cx - half_outer, cy, edge_z), (edge, outer_l, edge), bin_edge_color)
        add_box(f"{prefix}_rim_left", (cx, cy - half_outer, edge_z), (outer_l, edge, edge), bin_edge_color)
        add_box(f"{prefix}_rim_right", (cx, cy + half_outer, edge_z), (outer_l, edge, edge), bin_edge_color)

    add_bin("left_bin", dims.bin_center_x, dims.left_bin_y)
    add_bin("right_bin", dims.bin_center_x, dims.right_bin_y)
    add_box("floor", (0.0, 0.0, -0.015), (3.2, 2.8, 0.03), floor_color)
    return items


def _add_static_collision(builder, dims: SceneDims, params: ShapeParams) -> None:
    def add_box(label: str, center, size) -> None:
        _add_static_box(builder, center=center, size=size, params=params, label=label)

    add_box(
        "table_top",
        (dims.table_center_x, 0.0, dims.table_height),
        (dims.table_short_x, dims.table_long_y, dims.table_top_thick),
    )
    outer_l = dims.bin_l + 2.0 * dims.wall
    for prefix, cy in (("left_bin", dims.left_bin_y), ("right_bin", dims.right_bin_y)):
        cx = dims.bin_center_x
        floor_z = dims.table_top_z + dims.bottom / 2.0
        wall_z = dims.table_top_z + dims.bottom + dims.bin_h / 2.0
        add_box(f"{prefix}_floor", (cx, cy, floor_z), (outer_l, outer_l, dims.bottom))
        add_box(
            f"{prefix}_front_wall",
            (cx + dims.bin_l / 2.0 + dims.wall / 2.0, cy, wall_z),
            (dims.wall, outer_l, dims.bin_h),
        )
        add_box(
            f"{prefix}_back_wall",
            (cx - dims.bin_l / 2.0 - dims.wall / 2.0, cy, wall_z),
            (dims.wall, outer_l, dims.bin_h),
        )
        add_box(
            f"{prefix}_left_wall",
            (cx, cy - dims.bin_l / 2.0 - dims.wall / 2.0, wall_z),
            (dims.bin_l, dims.wall, dims.bin_h),
        )
        add_box(
            f"{prefix}_right_wall",
            (cx, cy + dims.bin_l / 2.0 + dims.wall / 2.0, wall_z),
            (dims.bin_l, dims.wall, dims.bin_h),
        )


def _sphere_specs(
    *,
    rng: np.random.Generator,
    dims: SceneDims,
    count: int,
    grid_count: int,
    gripper_width: float,
    drop_height: float,
) -> list[dict]:
    count = max(1, int(count))
    grid_count = max(1, int(grid_count))
    layer_count = int(math.ceil(count / float(grid_count * grid_count)))
    usable = dims.bin_l - 0.050
    step_x = usable / grid_count
    step_y = usable / grid_count
    nominal = float(gripper_width)
    layer_step = 1.16 * nominal
    max_diameter = min(1.20 * nominal, 0.82 * min(step_x, step_y, layer_step))
    min_diameter = min(0.58 * nominal, 0.75 * max_diameter)
    mode_diameter = min(max_diameter, max(min_diameter, 0.88 * nominal))
    colors = [
        (0.72, 0.22, 0.18, 1.0),
        (0.92, 0.66, 0.18, 1.0),
        (0.24, 0.58, 0.35, 1.0),
        (0.78, 0.78, 0.70, 1.0),
        (0.18, 0.42, 0.72, 1.0),
        (0.55, 0.30, 0.68, 1.0),
    ]

    specs: list[dict] = []
    for layer_idx in range(layer_count):
        cells = [(row_idx, col_idx) for row_idx in range(grid_count) for col_idx in range(grid_count)]
        rng.shuffle(cells)
        layer_jitter_x = rng.uniform(-0.10, 0.10) * step_x
        layer_jitter_y = rng.uniform(-0.10, 0.10) * step_y
        for row_idx, col_idx in cells:
            if len(specs) >= count:
                break
            diameter = float(rng.triangular(min_diameter, mode_diameter, max_diameter))
            radius = diameter / 2.0
            safe = radius + 0.018
            x = dims.bin_center_x - usable / 2.0 + (col_idx + rng.uniform(0.35, 0.65)) * step_x + layer_jitter_x
            y = dims.left_bin_y - usable / 2.0 + (row_idx + rng.uniform(0.35, 0.65)) * step_y + layer_jitter_y
            x = max(dims.bin_center_x - usable / 2.0 + safe, min(dims.bin_center_x + usable / 2.0 - safe, x))
            y = max(dims.left_bin_y - usable / 2.0 + safe, min(dims.left_bin_y + usable / 2.0 - safe, y))
            z = dims.inner_top_z + drop_height + radius + layer_idx * layer_step + rng.uniform(0.0, 0.025)
            density = 380.0
            mass = density * (4.0 / 3.0) * math.pi * radius**3
            specs.append(
                {
                    "object_id": f"sphere_{len(specs):03d}",
                    "radius": radius,
                    "mass": mass,
                    "color": colors[(row_idx + col_idx + layer_idx + len(specs)) % len(colors)],
                    "initial_position": (float(x), float(y), float(z)),
                    "layer": layer_idx,
                    "row": row_idx,
                    "col": col_idx,
                }
            )
    return specs


def _transform_to_matrix(transform_xyzw: np.ndarray) -> np.ndarray:
    arr = np.asarray(transform_xyzw, dtype=float).reshape(-1)
    matrix = np.eye(4)
    matrix[:3, :3] = tra.quaternion_matrix([arr[6], arr[3], arr[4], arr[5]])[:3, :3]
    matrix[:3, 3] = arr[:3]
    return matrix


def _add_mesh(scene: pyrender.Scene, mesh: trimesh.Trimesh, color: tuple[float, float, float, float], pose: np.ndarray) -> None:
    material = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=np.asarray(color, dtype=float),
        metallicFactor=0.08,
        roughnessFactor=0.62,
    )
    scene.add(pyrender.Mesh.from_trimesh(mesh, material=material, smooth=False), pose=pose)


def _render_frame(
    renderer: pyrender.OffscreenRenderer,
    *,
    static_items: list[dict],
    sphere_meshes: dict[str, trimesh.Trimesh],
    sphere_specs: list[SphereSpec],
    body_q: np.ndarray,
    width: int,
    height: int,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> np.ndarray:
    scene = pyrender.Scene(
        ambient_light=np.array([0.38, 0.38, 0.38, 1.0]),
        bg_color=np.array([0.94, 0.95, 0.96, 1.0]),
    )
    identity = np.eye(4)
    for item in static_items:
        _add_mesh(scene, item["mesh"], item["color"], identity)

    for spec in sphere_specs:
        pose = _transform_to_matrix(body_q[spec.body_idx])
        _add_mesh(scene, sphere_meshes[spec.object_id], spec.color, pose)

    aspect = float(width) / float(height)
    cam = pyrender.PerspectiveCamera(yfov=math.radians(45.0), aspectRatio=aspect)
    cam_pose = camera_pose_from_lookat(eye, target)
    scene.add(cam, pose=cam_pose)
    scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=4.5), pose=cam_pose)
    fill_pose = camera_pose_from_lookat((eye[0] - 1.0, eye[1] + 1.0, eye[2]), target)
    scene.add(pyrender.DirectionalLight(color=[0.85, 0.88, 1.0], intensity=1.8), pose=fill_pose)

    color, _depth = renderer.render(scene)
    return color


def _encode_video(frames_dir: Path, output_mp4: Path, fps: int) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        LOG.warning("ffmpeg not found; leaving PNG frames unencoded")
        return False
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(int(fps)),
        "-i",
        str(frames_dir / "overview_%04d.png"),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_mp4),
    ]
    LOG.info("encoding MP4: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        LOG.warning("ffmpeg failed: %s", result.stderr.strip())
        return False
    return output_mp4.exists()


def _module_version(name: str) -> str:
    try:
        module = __import__(name)
        return str(getattr(module, "__version__", "unknown"))
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [NEWTON-BIN] %(message)s")
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("output_dir=%s", output_dir)
    LOG.info("PYOPENGL_PLATFORM=%s", os.environ.get("PYOPENGL_PLATFORM"))
    try:
        wp.set_device(str(args.device))
    except Exception as exc:  # noqa: BLE001
        LOG.warning("wp.set_device(%s) failed; continuing with default device: %s", args.device, exc)

    dims = _scene_dims(float(args.bin_l))
    rng = np.random.default_rng(int(args.seed))
    static_items = _static_items(dims)
    static_params = ShapeParams(mu=args.static_mu, ke=args.contact_ke, kd=args.contact_kd, kf=args.contact_kf)
    sphere_params = ShapeParams(mu=args.sphere_mu, ke=args.contact_ke, kd=args.contact_kd, kf=args.contact_kf)

    LOG.info("building Newton model")
    builder = newton.ModelBuilder(gravity=-9.81)
    newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
    builder.default_shape_cfg = _shape_cfg(static_params)
    _add_static_collision(builder, dims, static_params)

    sphere_specs_raw = _sphere_specs(
        rng=rng,
        dims=dims,
        count=int(args.sphere_count),
        grid_count=int(args.sphere_grid),
        gripper_width=float(args.gripper_open_width),
        drop_height=float(args.drop_height),
    )
    sphere_specs: list[SphereSpec] = []
    for raw in sphere_specs_raw:
        body_idx = _add_dynamic_sphere(
            builder,
            center=raw["initial_position"],
            radius=raw["radius"],
            mass=raw["mass"],
            params=sphere_params,
            armature=float(args.free_joint_armature),
            label=raw["object_id"],
        )
        sphere_specs.append(SphereSpec(body_idx=body_idx, **raw))

    try:
        model = builder.finalize(device=str(args.device))
    except TypeError:
        model = builder.finalize()
    LOG.info("Newton model: bodies=%d joints=%d shapes=%d device=%s", model.body_count, model.joint_count, model.shape_count, model.device)

    states = [model.state(), model.state()]
    newton.eval_fk(model, model.joint_q, model.joint_qd, states[0])
    solver = newton.solvers.SolverMuJoCo(
        model,
        use_mujoco_contacts=False,
        solver="newton",
        integrator="implicitfast",
        cone="elliptic",
        iterations=int(args.solver_iterations),
        ls_iterations=int(args.solver_ls_iterations),
        impratio=float(args.solver_impratio),
        njmax=int(args.contact_max),
        nconmax=int(args.contact_max),
    )
    collision_pipeline = newton.CollisionPipeline(model, reduce_contacts=True, broad_phase="explicit")
    contacts = newton.Contacts(rigid_contact_max=int(args.contact_max), soft_contact_max=0, device=model.device)
    control = model.control()

    fps = max(1, int(args.fps))
    total_frames = max(2, int(round(float(args.video_seconds) * fps)))
    sim_substeps = max(1, int(round(1.0 / (fps * float(args.physics_dt)))))
    effective_dt = 1.0 / (fps * sim_substeps)
    collide_substeps = max(1, int(args.collide_substeps))
    LOG.info(
        "simulating %d frames at %d fps, %d Newton substeps/frame, effective_dt=%.6f",
        total_frames,
        fps,
        sim_substeps,
        effective_dt,
    )

    eye = tuple(args.camera_eye) if args.camera_eye is not None else (0.18, dims.left_bin_y - 0.86, 2.55)
    target = tuple(args.camera_target) if args.camera_target is not None else (dims.bin_center_x, dims.left_bin_y, dims.table_top_z + 0.30)
    sphere_meshes = {
        spec.object_id: trimesh.creation.uv_sphere(radius=spec.radius, count=[16, 16])
        for spec in sphere_specs
    }

    trajectory: dict = {
        "fps": fps,
        "physics_dt": effective_dt,
        "frames": [],
    }
    renderer = pyrender.OffscreenRenderer(int(args.width), int(args.height))
    try:
        for frame_idx in range(total_frames):
            if frame_idx > 0:
                for substep in range(sim_substeps):
                    states[0].clear_forces()
                    if substep % collide_substeps == 0:
                        collision_pipeline.collide(states[0], contacts)
                    solver.step(states[0], states[1], control, contacts, effective_dt)
                    states[0], states[1] = states[1], states[0]

            body_q = states[0].body_q.numpy()
            if np.any(np.isnan(body_q)):
                raise RuntimeError(f"NaN detected in Newton body_q at frame {frame_idx}")

            color = _render_frame(
                renderer,
                static_items=static_items,
                sphere_meshes=sphere_meshes,
                sphere_specs=sphere_specs,
                body_q=body_q,
                width=int(args.width),
                height=int(args.height),
                eye=eye,
                target=target,
            )
            frame_path = frames_dir / f"overview_{frame_idx:04d}.png"
            Image.fromarray(color).save(frame_path)
            if frame_idx % max(1, total_frames // 10) == 0:
                LOG.info("wrote frame %d/%d", frame_idx + 1, total_frames)

            trajectory["frames"].append(
                {
                    "frame": frame_idx,
                    "time": frame_idx / float(fps),
                    "spheres": [
                        {
                            "id": spec.object_id,
                            "position": body_q[spec.body_idx, :3].astype(float).tolist(),
                            "quat_xyzw": body_q[spec.body_idx, 3:7].astype(float).tolist(),
                        }
                        for spec in sphere_specs
                    ],
                }
            )
    finally:
        renderer.delete()

    (output_dir / "trajectory.json").write_text(json.dumps(trajectory, indent=2) + "\n")
    metadata = {
        "generated_at_unix": time.time(),
        "backend": f"Newton physics + pyrender OpenGL ({os.environ.get('PYOPENGL_PLATFORM', 'default')})",
        "package_versions": {
            "newton": _module_version("newton"),
            "warp": _module_version("warp"),
            "pyrender": _module_version("pyrender"),
            "trimesh": _module_version("trimesh"),
        },
        "args": vars(args) | {"output_dir": str(output_dir)},
        "dimensions_m": asdict(dims),
        "camera": {"eye": list(eye), "target": list(target), "up": [0.0, 0.0, 1.0]},
        "simulation": {
            "model_device": str(model.device),
            "solver": "newton.solvers.SolverMuJoCo",
            "solver_backend": "newton",
            "integrator": "implicitfast",
            "frames": total_frames,
            "fps": fps,
            "sim_substeps_per_frame": sim_substeps,
            "effective_dt": effective_dt,
            "collide_substeps": collide_substeps,
            "contact_max": int(args.contact_max),
        },
        "spheres": [asdict(spec) for spec in sphere_specs],
        "static_items": [
            {"name": item["name"], "center": item["center"], "size": item["size"]}
            for item in static_items
            if "center" in item
        ],
    }
    (output_dir / "scene_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    mp4_path = output_dir / "overview.mp4"
    encoded = False if args.no_encode else _encode_video(frames_dir, mp4_path, fps)
    manifest = {
        "frames_dir": str(frames_dir),
        "frame_pattern": str(frames_dir / "overview_%04d.png"),
        "frame_count": total_frames,
        "mp4": str(mp4_path) if encoded else None,
        "encoded": encoded,
        "metadata": str(output_dir / "scene_metadata.json"),
        "trajectory": str(output_dir / "trajectory.json"),
    }
    (output_dir / "render_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    LOG.info("done; frames=%s mp4=%s", frames_dir, mp4_path if encoded else "not encoded")


if __name__ == "__main__":
    main()
