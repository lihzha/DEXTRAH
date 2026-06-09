#!/usr/bin/env python3
"""Render a DEXTRAH clutter-bin inspection scene in Isaac Sim.

Scene convention:
- World X is the robot/table short-axis direction.
- World Y is the table long-axis direction.
- The robot is placed at the origin on the +X side of the table, matching
  DEXTRAH's existing KUKA-Allegro setup where objects sit at negative X.
- Two square bins are centered at symmetric +/-Y offsets on the table.
- The left bin, from the robot side while looking toward -X, is the negative-Y
  bin and is densely packed with simple cuboid or sphere clutter.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import time
from pathlib import Path
from typing import Iterable

from isaaclab.app import AppLauncher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=Path("/tmp/dextrah_clutter_bin"))
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--video_seconds", type=float, default=4.0)
    parser.add_argument("--rt_subframes", type=int, default=16)
    parser.add_argument("--capture_video", action="store_true", help="Capture an overview PNG sequence for video encoding.")
    parser.add_argument("--sim_steps_per_frame", type=int, default=2)
    parser.add_argument("--settle_steps", type=int, default=300)
    parser.add_argument("--bin_l", type=float, default=0.48)
    parser.add_argument("--gripper_open_width", type=float, default=0.09)
    parser.add_argument(
        "--dynamic_clutter",
        dest="dynamic_clutter",
        action="store_true",
        default=True,
        help="Spawn clutter as PhysX rigid bodies. Enabled by default.",
    )
    parser.add_argument(
        "--static_clutter",
        dest="dynamic_clutter",
        action="store_false",
        help="Spawn clutter as fixed collision geometry instead of rigid bodies.",
    )
    parser.add_argument("--dynamic_sphere_grid", type=int, default=3)
    parser.add_argument("--dynamic_sphere_layers", type=int, default=2)
    parser.add_argument(
        "--dynamic_sphere_count",
        type=int,
        default=0,
        help="Optional target sphere count. When >0, layers are expanded to place at least this many spheres.",
    )
    parser.add_argument("--physics_device", default="cpu", help="PhysX device used by SimulationContext video capture.")
    parser.add_argument("--contact_offset", type=float, default=0.004)
    parser.add_argument("--rest_offset", type=float, default=0.0)
    parser.add_argument("--solver_position_iterations", type=int, default=12)
    parser.add_argument("--solver_velocity_iterations", type=int, default=2)
    parser.add_argument("--max_depenetration_velocity", type=float, default=3.0)
    parser.add_argument("--sphere_static_friction", type=float, default=1.2)
    parser.add_argument("--sphere_dynamic_friction", type=float, default=0.9)
    parser.add_argument("--sphere_linear_damping", type=float, default=0.12)
    parser.add_argument("--sphere_angular_damping", type=float, default=0.65)
    parser.add_argument("--sphere_sleep_threshold", type=float, default=0.03)
    parser.add_argument("--sphere_stabilization_threshold", type=float, default=0.01)
    parser.add_argument(
        "--clutter_shape",
        choices=("cube", "sphere"),
        default="sphere",
        help="Primitive used to fill the left bin. Size range is based on gripper open width.",
    )
    parser.add_argument(
        "--view",
        choices=("overview", "robot_side", "topdown", "filled_bin_close"),
        default="overview",
        help="Single inspection view to capture. The headless viewport capture exits Isaac after one image.",
    )
    AppLauncher.add_app_launcher_args(parser)
    return parser.parse_args()


args_cli = parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import omni.timeline  # noqa: E402
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


def _log(message: str) -> None:
    print(f"[clutter-bin] {message}", flush=True)


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
    rotate_xyz_deg: tuple[float, float, float] | None = None,
    collision: bool = True,
    dynamic: bool = False,
    density: float = 450.0,
) -> Usd.Prim:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    _set_xform(prim, center, size, rotate_xyz_deg=rotate_xyz_deg)
    _bind(prim, mat)
    if collision:
        UsdPhysics.CollisionAPI.Apply(prim)
        try:
            PhysxSchema.PhysxCollisionAPI.Apply(prim)
        except Exception:
            pass
    if dynamic:
        rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
        try:
            rb_api.CreateRigidBodyEnabledAttr(True)
            rb_api.CreateStartsAsleepAttr(False)
        except Exception:
            pass
        mass_api = UsdPhysics.MassAPI.Apply(prim)
        mass_api.CreateDensityAttr(float(density))
    return prim


def _add_sphere(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    diameter: float,
    mat: UsdShade.Material,
    *,
    collision: bool = True,
    dynamic: bool = False,
    density: float = 450.0,
) -> Usd.Prim:
    sphere = UsdGeom.Sphere.Define(stage, path)
    sphere.CreateRadiusAttr(float(diameter) / 2.0)
    prim = sphere.GetPrim()
    _set_xform(prim, center)
    _bind(prim, mat)
    if collision:
        UsdPhysics.CollisionAPI.Apply(prim)
        try:
            PhysxSchema.PhysxCollisionAPI.Apply(prim)
        except Exception:
            pass
    if dynamic:
        rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
        try:
            rb_api.CreateRigidBodyEnabledAttr(True)
            rb_api.CreateStartsAsleepAttr(False)
        except Exception:
            pass
        mass_api = UsdPhysics.MassAPI.Apply(prim)
        mass_api.CreateDensityAttr(float(density))
    return prim


def _add_physics_scene(stage: Usd.Stage) -> None:
    scene = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(9.81)
    try:
        PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
    except Exception:
        pass


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


def _create_bin(
    stage: Usd.Stage,
    root: str,
    center_xy: tuple[float, float],
    *,
    l: float,
    h: float,
    wall: float,
    bottom: float,
    table_top_z: float,
    mat: UsdShade.Material,
    edge_mat: UsdShade.Material,
) -> dict[str, float]:
    cx, cy = center_xy
    floor_z = table_top_z + bottom / 2.0
    wall_z = table_top_z + bottom + h / 2.0
    outer_l = l + 2.0 * wall

    _add_box(stage, f"{root}/floor", (cx, cy, floor_z), (outer_l, outer_l, bottom), mat)
    _add_box(stage, f"{root}/front_wall", (cx + l / 2.0 + wall / 2.0, cy, wall_z), (wall, outer_l, h), mat)
    _add_box(stage, f"{root}/back_wall", (cx - l / 2.0 - wall / 2.0, cy, wall_z), (wall, outer_l, h), mat)
    _add_box(stage, f"{root}/left_wall", (cx, cy - l / 2.0 - wall / 2.0, wall_z), (l, wall, h), mat)
    _add_box(stage, f"{root}/right_wall", (cx, cy + l / 2.0 + wall / 2.0, wall_z), (l, wall, h), mat)

    edge = wall * 0.55
    edge_z = table_top_z + bottom + h + edge / 2.0
    corner_z = table_top_z + (bottom + h) / 2.0
    half_outer = outer_l / 2.0
    _add_box(stage, f"{root}/rim_front", (cx + half_outer, cy, edge_z), (edge, outer_l, edge), edge_mat)
    _add_box(stage, f"{root}/rim_back", (cx - half_outer, cy, edge_z), (edge, outer_l, edge), edge_mat)
    _add_box(stage, f"{root}/rim_left", (cx, cy - half_outer, edge_z), (outer_l, edge, edge), edge_mat)
    _add_box(stage, f"{root}/rim_right", (cx, cy + half_outer, edge_z), (outer_l, edge, edge), edge_mat)
    for idx, sx in enumerate((-1.0, 1.0)):
        for sy in (-1.0, 1.0):
            _add_box(
                stage,
                f"{root}/corner_{idx}_{0 if sy < 0.0 else 1}",
                (cx + sx * half_outer, cy + sy * half_outer, corner_z),
                (edge, edge, bottom + h),
                edge_mat,
            )

    return {
        "center_x": cx,
        "center_y": cy,
        "inner_l": l,
        "inner_h": h,
        "outer_l": outer_l,
        "wall": wall,
        "bottom": bottom,
        "inner_floor_z": table_top_z + bottom,
        "inner_top_z": table_top_z + bottom + h,
    }


def _create_clutter(
    stage: Usd.Stage,
    *,
    bin_info: dict[str, float],
    gripper_width: float,
    seed: int,
    mats: list[UsdShade.Material],
    shape: str,
    dynamic: bool,
) -> list[dict[str, float]]:
    rng = random.Random(seed)
    min_side = 0.5 * gripper_width
    max_side = 1.5 * gripper_width
    usable = bin_info["inner_l"] - 0.028
    x_center = bin_info["center_x"]
    y_center = bin_info["center_y"]
    x_min = x_center - usable / 2.0
    y_min = y_center - usable / 2.0
    z_floor = bin_info["inner_floor_z"]
    z_limit = bin_info["inner_top_z"] - 0.018

    records: list[dict[str, float]] = []
    layer_idx = 0
    z_cursor = 0.0
    while z_floor + z_cursor + min_side <= z_limit:
        spacing = rng.triangular(min_side, max_side, 0.82 * gripper_width)
        remaining_z = z_limit - (z_floor + z_cursor)
        if remaining_z < min_side:
            break
        spacing = min(spacing, remaining_z)
        if spacing < min_side:
            break

        count_x = max(2, int(usable / spacing))
        count_y = max(2, int(usable / spacing))
        step_x = usable / count_x
        step_y = usable / count_y
        layer_fill = 1.0 if layer_idx < 2 else rng.uniform(0.86, 0.98)
        layer_jitter = 0.18 if layer_idx > 0 else 0.08

        for row_idx in range(count_y):
            for col_idx in range(count_x):
                if rng.random() > layer_fill:
                    continue
                side = spacing * rng.uniform(1.00, 1.16)
                side = max(min_side, min(max_side, side, remaining_z))
                x = x_min + (col_idx + 0.5) * step_x + rng.uniform(-layer_jitter, layer_jitter) * step_x
                y = y_min + (row_idx + 0.5) * step_y + rng.uniform(-layer_jitter, layer_jitter) * step_y
                half = side / 2.0
                x = max(x_center - usable / 2.0 + half, min(x_center + usable / 2.0 - half, x))
                y = max(y_center - usable / 2.0 + half, min(y_center + usable / 2.0 - half, y))
                z = z_floor + z_cursor + half
                if z + half > z_limit:
                    continue

                roll = rng.uniform(-2.0, 2.0) if layer_idx > 0 else 0.0
                pitch = rng.uniform(-2.0, 2.0) if layer_idx > 0 else 0.0
                yaw = rng.uniform(-8.0, 8.0)
                mat = mats[(row_idx + col_idx + layer_idx + rng.randrange(len(mats))) % len(mats)]
                path = f"/World/Clutter/left_bin_{shape}_{len(records):03d}"
                if shape == "sphere":
                    _add_sphere(
                        stage,
                        path,
                        (x, y, z),
                        side,
                        mat,
                        collision=True,
                        dynamic=dynamic,
                        density=380.0,
                    )
                else:
                    _add_box(
                        stage,
                        path,
                        (x, y, z),
                        (side, side, side),
                        mat,
                        rotate_xyz_deg=(roll, pitch, yaw),
                        collision=True,
                        dynamic=dynamic,
                        density=380.0,
                    )
                records.append(
                    {
                        "prim_path": path,
                        "shape": shape,
                        "x": x,
                        "y": y,
                        "z": z,
                        "side": side,
                        "diameter": side if shape == "sphere" else None,
                        "row": row_idx,
                        "col": col_idx,
                        "layer": layer_idx,
                        "roll_deg": roll,
                        "pitch_deg": pitch,
                        "yaw_deg": yaw,
                    }
                )

        z_cursor += spacing * rng.uniform(0.86, 0.96)
        layer_idx += 1

    return records


def _create_dynamic_sphere_clutter(
    *,
    bin_info: dict[str, float],
    gripper_width: float,
    seed: int,
    mat_colors: list[Color],
    grid_count: int,
    layer_count: int,
    target_count: int = 0,
) -> list[dict[str, float]]:
    rng = random.Random(seed)
    min_diameter = 0.5 * gripper_width
    max_diameter = 1.5 * gripper_width
    nominal_diameter = gripper_width
    usable = bin_info["inner_l"] - 0.038
    x_center = bin_info["center_x"]
    y_center = bin_info["center_y"]
    z_floor = bin_info["inner_floor_z"]

    grid_count = max(1, int(grid_count))
    layer_count = max(1, int(layer_count))
    target_count = max(0, int(target_count))
    if target_count > 0:
        layer_count = max(layer_count, math.ceil(target_count / float(grid_count * grid_count)))
    step_x = usable / grid_count
    step_y = usable / grid_count
    layer_step = 1.08 * nominal_diameter
    max_initial_diameter = 0.86 * min(step_x, step_y, layer_step)
    records: list[dict[str, float]] = []

    for layer_idx in range(layer_count):
        layer_offset_x = rng.uniform(-0.10, 0.10) * step_x
        layer_offset_y = rng.uniform(-0.10, 0.10) * step_y
        layer_fill = 1.0 if target_count > 0 else (1.0 if layer_idx == 0 else rng.uniform(0.90, 0.98))
        layer_cells = [(row_idx, col_idx) for row_idx in range(grid_count) for col_idx in range(grid_count)]
        rng.shuffle(layer_cells)

        for row_idx, col_idx in layer_cells:
            if target_count > 0 and len(records) >= target_count:
                break
            if rng.random() > layer_fill:
                continue
            diameter = rng.triangular(min_diameter, max_diameter, 0.90 * nominal_diameter)
            diameter = min(diameter, max_initial_diameter)
            diameter = max(min_diameter, diameter)
            radius = diameter / 2.0
            x = x_center - usable / 2.0 + (col_idx + rng.uniform(0.35, 0.65)) * step_x + layer_offset_x
            y = y_center - usable / 2.0 + (row_idx + rng.uniform(0.35, 0.65)) * step_y + layer_offset_y
            safe_margin = radius + 0.018
            x = max(x_center - usable / 2.0 + safe_margin, min(x_center + usable / 2.0 - safe_margin, x))
            y = max(y_center - usable / 2.0 + safe_margin, min(y_center + usable / 2.0 - safe_margin, y))
            z_boost = 0.030 + rng.uniform(0.0, 0.012)
            z = z_floor + radius + layer_idx * layer_step + z_boost

            mat_color = mat_colors[(row_idx + col_idx + layer_idx + rng.randrange(len(mat_colors))) % len(mat_colors)]
            path = f"/World/Clutter/left_bin_sphere_{len(records):03d}"
            sphere_cfg = sim_utils.SphereCfg(
                radius=radius,
                collision_props=sim_utils.CollisionPropertiesCfg(
                    collision_enabled=True,
                    contact_offset=float(args_cli.contact_offset),
                    rest_offset=float(args_cli.rest_offset),
                ),
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=False,
                    disable_gravity=False,
                    linear_damping=float(args_cli.sphere_linear_damping),
                    angular_damping=float(args_cli.sphere_angular_damping),
                    enable_gyroscopic_forces=True,
                    solver_position_iteration_count=int(args_cli.solver_position_iterations),
                    solver_velocity_iteration_count=int(args_cli.solver_velocity_iterations),
                    sleep_threshold=float(args_cli.sphere_sleep_threshold),
                    stabilization_threshold=float(args_cli.sphere_stabilization_threshold),
                    max_linear_velocity=1000.0,
                    max_angular_velocity=1000.0,
                    max_depenetration_velocity=float(args_cli.max_depenetration_velocity),
                ),
                mass_props=sim_utils.MassPropertiesCfg(density=380.0),
                physics_material=RigidBodyMaterialCfg(
                    static_friction=float(args_cli.sphere_static_friction),
                    dynamic_friction=float(args_cli.sphere_dynamic_friction),
                    restitution=0.0,
                    friction_combine_mode="max",
                    restitution_combine_mode="min",
                ),
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=mat_color, roughness=0.72),
            )
            sphere_cfg.func(path, sphere_cfg, translation=(x, y, z), orientation=(1.0, 0.0, 0.0, 0.0))
            records.append(
                {
                    "prim_path": path,
                    "shape": "sphere",
                    "x": x,
                    "y": y,
                    "z": z,
                    "side": diameter,
                    "diameter": diameter,
                    "row": row_idx,
                    "col": col_idx,
                    "layer": layer_idx,
                    "roll_deg": 0.0,
                    "pitch_deg": 0.0,
                    "yaw_deg": 0.0,
                }
            )
        if target_count > 0 and len(records) >= target_count:
            break

    return records


def _bake_clutter_transforms(stage: Usd.Stage, clutter: list[dict[str, float]]) -> None:
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    for record in clutter:
        path = record.get("prim_path")
        if not path:
            continue
        prim = stage.GetPrimAtPath(str(path))
        if not prim.IsValid():
            continue
        world_xform = xform_cache.GetLocalToWorldTransform(prim)
        translation = world_xform.ExtractTranslation()
        record["initial_x"] = record["x"]
        record["initial_y"] = record["y"]
        record["initial_z"] = record["z"]
        record["x"] = float(translation[0])
        record["y"] = float(translation[1])
        record["z"] = float(translation[2])
        record["settled_transform_baked"] = True

        xformable = UsdGeom.Xformable(prim)
        xformable.ClearXformOpOrder()
        xformable.AddTransformOp().Set(world_xform)


def _settle_scene(sim, stage: Usd.Stage, clutter: list[dict[str, float]], settle_steps: int) -> bool:
    if settle_steps <= 0:
        return False

    _log(f"settling dynamic scene for {settle_steps} physics steps")
    sim.reset()
    for _ in range(settle_steps):
        sim.step(render=False)
    sim.render()
    update_stage()
    _bake_clutter_transforms(stage, clutter)
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
    deadline = time.time() + 90.0
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
    UsdGeom.Xform.Define(stage, "/World/Bins")
    UsdGeom.Xform.Define(stage, "/World/Clutter")

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
    bin_mat = _material(
        stage,
        "/World/Looks/bin_solid_blue",
        (0.18, 0.43, 0.78),
        roughness=0.42,
    )
    bin_edge_mat = _material(stage, "/World/Looks/bin_edge_blue", (0.02, 0.13, 0.30), roughness=0.50)
    floor_mat = _material(stage, "/World/Looks/floor_gray", (0.28, 0.30, 0.31))
    clutter_colors: list[Color] = [
        (0.72, 0.22, 0.18),
        (0.92, 0.66, 0.18),
        (0.24, 0.58, 0.35),
        (0.78, 0.78, 0.70),
        (0.18, 0.42, 0.72),
    ]
    clutter_mats = [
        _material(stage, "/World/Looks/clutter_red", clutter_colors[0]),
        _material(stage, "/World/Looks/clutter_yellow", clutter_colors[1]),
        _material(stage, "/World/Looks/clutter_green", clutter_colors[2]),
        _material(stage, "/World/Looks/clutter_white", clutter_colors[3]),
        _material(stage, "/World/Looks/clutter_blue", clutter_colors[4]),
    ]

    bin_l = float(args_cli.bin_l)
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

    _log(f"referencing robot USD: {robot_usd}")
    _create_robot(stage, robot_usd)

    _log("creating table")
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

    left_bin = _create_bin(
        stage,
        "/World/Bins/left_filled",
        (bin_center_x, left_bin_y),
        l=bin_l,
        h=bin_h,
        wall=wall,
        bottom=bottom,
        table_top_z=table_top_z,
        mat=bin_mat,
        edge_mat=bin_edge_mat,
    )
    right_bin = _create_bin(
        stage,
        "/World/Bins/right_empty",
        (bin_center_x, right_bin_y),
        l=bin_l,
        h=bin_h,
        wall=wall,
        bottom=bottom,
        table_top_z=table_top_z,
        mat=bin_mat,
        edge_mat=bin_edge_mat,
    )
    dynamic_clutter = bool(args_cli.dynamic_clutter)
    if dynamic_clutter and str(args_cli.clutter_shape) != "sphere":
        raise ValueError(
            "Dynamic clutter is only supported for --clutter_shape sphere. "
            "Use --static_clutter for fixed cuboids, or omit --clutter_shape to use settled dynamic spheres."
        )
    if dynamic_clutter and str(args_cli.clutter_shape) == "sphere":
        clutter = _create_dynamic_sphere_clutter(
            bin_info=left_bin,
            gripper_width=float(args_cli.gripper_open_width),
            seed=int(args_cli.seed),
            mat_colors=clutter_colors,
            grid_count=int(args_cli.dynamic_sphere_grid),
            layer_count=int(args_cli.dynamic_sphere_layers),
            target_count=int(args_cli.dynamic_sphere_count),
        )
    else:
        clutter = _create_clutter(
            stage,
            bin_info=left_bin,
            gripper_width=float(args_cli.gripper_open_width),
            seed=int(args_cli.seed),
            mats=clutter_mats,
            shape=str(args_cli.clutter_shape),
            dynamic=dynamic_clutter,
        )
    _log(f"created {len(clutter)} clutter {args_cli.clutter_shape}s")

    _add_box(stage, "/World/Floor", (0.0, 0.0, -0.015), (3.2, 2.8, 0.03), floor_mat, collision=True)

    # Keep lighting simple and deterministic for inspection renders.
    dome = stage.DefinePrim("/World/DomeLight", "DomeLight")
    dome.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(650.0)
    dome.CreateAttribute("inputs:color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 0.98, 0.92))
    sun = stage.DefinePrim("/World/KeyLight", "DistantLight")
    sun.CreateAttribute("inputs:intensity", Sdf.ValueTypeNames.Float).Set(1500.0)
    sun.CreateAttribute("inputs:angle", Sdf.ValueTypeNames.Float).Set(0.35)
    _set_xform(sun, (0.0, 0.0, 0.0), rotate_xyz_deg=(-45.0, 0.0, 35.0))

    settle_steps = max(0, int(args_cli.settle_steps))
    settled_transforms_baked = _settle_scene(sim, stage, clutter, settle_steps)

    metadata = {
        "generated_at_unix": time.time(),
        "simulation_backend": "Isaac Sim / Isaac Lab / PhysX USD scene",
        "robot_usd": str(robot_usd),
        "axes": {
            "table_long_axis": "world_y",
            "table_short_axis": "world_x",
            "robot_base_origin": [0.0, 0.0, 0.0],
            "table_is_in_front_of_robot_at_negative_x": True,
        },
        "dimensions_m": {
            "bin_l": bin_l,
            "bin_h": bin_h,
            "bin_h_over_l": bin_h / bin_l,
            "bin_h_note": "Half of the original 1.5*l bin height.",
            "bin_gap_y": bin_gap,
            "wall_thickness": wall,
            "wall_collision_enabled": True,
            "rim_collision_enabled": True,
            "wall_visual_opacity": 1.0,
            "table_short_x": table_short_x,
            "table_long_y": table_long_y,
            "table_height": table_height,
            "gripper_open_width_reference": float(args_cli.gripper_open_width),
            "clutter_shape": str(args_cli.clutter_shape),
            "clutter_dynamic": dynamic_clutter,
            "dynamic_sphere_grid": int(args_cli.dynamic_sphere_grid),
            "dynamic_sphere_layers": int(args_cli.dynamic_sphere_layers),
            "dynamic_sphere_count_target": int(args_cli.dynamic_sphere_count),
            "settle_steps": settle_steps,
            "settled_transforms_baked_to_usd": settled_transforms_baked,
            "usd_exported_after_settle": True,
            "clutter_size_min": 0.5 * float(args_cli.gripper_open_width),
            "clutter_size_max": 1.5 * float(args_cli.gripper_open_width),
            "clutter_size_meaning": "cube side length or sphere diameter",
        },
        "simulation": {
            "simulation_context_created_before_scene_assets": True,
            "physics_device": str(args_cli.physics_device),
            "sim_dt": 1.0 / 60.0,
            "render_interval": 1,
            "default_static_friction": 1.0,
            "default_dynamic_friction": 1.0,
            "physx_bounce_threshold_velocity": 0.2,
            "dynamic_sphere_spawn_api": "Isaac Lab SphereCfg direct spawner",
        },
        "collision": {
            "contact_offset": float(args_cli.contact_offset),
            "rest_offset": float(args_cli.rest_offset),
            "solver_position_iterations": int(args_cli.solver_position_iterations),
            "solver_velocity_iterations": int(args_cli.solver_velocity_iterations),
            "max_depenetration_velocity": float(args_cli.max_depenetration_velocity),
            "sphere_static_friction": float(args_cli.sphere_static_friction),
            "sphere_dynamic_friction": float(args_cli.sphere_dynamic_friction),
            "sphere_linear_damping": float(args_cli.sphere_linear_damping),
            "sphere_angular_damping": float(args_cli.sphere_angular_damping),
            "sleep_threshold": float(args_cli.sphere_sleep_threshold),
            "stabilization_threshold": float(args_cli.sphere_stabilization_threshold),
            "density": 380.0,
        },
        "bins": {
            "left_filled": left_bin,
            "right_empty": right_bin,
            "symmetric_y_offsets": [left_bin_y, right_bin_y],
        },
        "clutter": {
            "count": len(clutter),
            "min_side": min(c["side"] for c in clutter),
            "max_side": max(c["side"] for c in clutter),
            "max_top_z": max(c["z"] + c["side"] / 2.0 for c in clutter),
            "bin_inner_top_z": left_bin["inner_top_z"],
            "records": clutter,
        },
        "checks": {
            "bin_height_is_0p75_l": abs(bin_h - 0.75 * bin_l) < 1.0e-9,
            "bins_symmetric_about_robot_x_axis": abs(left_bin_y + right_bin_y) < 1.0e-9,
            "robot_x_axis_parallel_table_short_axis": True,
            "bins_side_by_side_along_table_long_axis": True,
            "left_bin_is_negative_y_from_robot_view": True,
            "bin_wall_prims_have_collision_api": True,
            "bin_rim_prims_have_collision_api": True,
            "clutter_prim_collision_enabled": True,
            "clutter_rigid_body_enabled": dynamic_clutter,
            "dynamic_spheres_use_isaaclab_sphere_cfg": dynamic_clutter and str(args_cli.clutter_shape) == "sphere",
        },
    }
    _log("writing metadata")
    _write_metadata(output_dir / "scene_metadata.json", metadata)

    usd_path = output_dir / "clutter_bin_env.usda"
    _log(f"exporting USD: {usd_path}")
    stage.GetRootLayer().Export(str(usd_path))

    target = (bin_center_x, left_bin_y, table_top_z + 0.25)
    views = {
        "overview": ((0.22, left_bin_y - 0.70, 2.85), target),
        "robot_side": ((1.35, 0.0, 1.48), (table_center_x, 0.0, table_top_z + 0.28)),
        "topdown": ((table_center_x, 0.0, 2.65), (table_center_x, 0.0, table_top_z + 0.03)),
        "filled_bin_close": ((0.02, left_bin_y - 0.72, 1.55), (bin_center_x, left_bin_y, table_top_z + 0.34)),
    }
    name = str(args_cli.view)
    eye, look_at = views[name]
    expected_png = output_dir / f"{name}.png"
    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "view": name,
            "expected_png": str(expected_png),
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

    print(f"Wrote clutter-bin scene renders to {output_dir}")
    print(f"Clutter {args_cli.clutter_shape}s: {len(clutter)}")
    print(f"USD: {usd_path}")
    sim.clear_all_callbacks()
    sim.clear_instance()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
