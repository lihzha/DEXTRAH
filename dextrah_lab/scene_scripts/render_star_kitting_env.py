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
        choices=("star_kitting", "cube_motion"),
        default="star_kitting",
        help="Scene to render. cube_motion keeps the Franka static and moves a single disturbed cube.",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--video_seconds", type=float, default=3.0)
    parser.add_argument("--capture_video", action="store_true", help="Capture an overview PNG sequence.")
    parser.add_argument("--sim_steps_per_frame", type=int, default=2)
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
        default="static_urdf_obj_meshes",
        help="Render GraspGenX Franka as static URDF OBJ meshes, or opt into an Isaac Lab articulation.",
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
    parser.add_argument("--star_outer_radius", type=float, default=0.092)
    parser.add_argument("--star_inner_radius", type=float, default=0.042)
    parser.add_argument("--star_thickness", type=float, default=0.034)
    parser.add_argument("--fixture_size_x", type=float, default=0.33)
    parser.add_argument("--fixture_size_y", type=float, default=0.33)
    parser.add_argument("--fixture_thickness", type=float, default=0.052)
    parser.add_argument("--fixture_clearance", type=float, default=0.012)
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
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation  # noqa: E402
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
    graspgenx_root = _resolve_graspgenx_root()
    cfg_path = graspgenx_root / "end2end/robots/franka_panda.yaml"
    cfg = _load_yaml(cfg_path)
    curobo_assets_root = _resolve_curobo_assets_root(graspgenx_root)

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
    base_translation = _as_float_tuple(
        base_pose.get("translation", [0.0, 0.0, 0.0]),
        length=3,
        field_name="robot_base_pose.translation",
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

    render_mode = str(args_cli.franka_render_mode)
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
        source_base_translation=base_translation,  # type: ignore[arg-type]
        source_base_quaternion_xyzw=base_quat,  # type: ignore[arg-type]
        scene_yaw_deg=scene_yaw_deg,
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
                max_depenetration_velocity=5.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=8,
                solver_velocity_iteration_count=0,
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


def _create_cube_object(
    stage: Usd.Stage,
    *,
    root_path: str,
    center: tuple[float, float, float],
    size: float,
    mat: UsdShade.Material,
) -> dict[str, object]:
    prim = _add_box(stage, root_path, center, (size, size, size), mat, collision=True)
    return {
        "prim_path": root_path,
        "center": list(center),
        "size": float(size),
        "dynamic": False,
        "motion_source": "deterministic keyframed disturbance trajectory",
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


def _write_robot_articulation_targets(robot: Articulation | None) -> None:
    if robot is None:
        return
    robot.set_joint_position_target(robot.data.default_joint_pos)
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


def _settle_scene(
    sim,
    stage: Usd.Stage,
    star_record: dict[str, object],
    settle_steps: int,
    robot_articulation: Articulation | None,
) -> bool:
    _log("resetting SimulationContext for scene initialization")
    sim.reset()
    _reset_robot_articulation(robot_articulation)
    if settle_steps <= 0 or not bool(star_record.get("dynamic")):
        sim.render()
        update_stage()
        return False
    _log(f"settling dynamic star for {settle_steps} physics steps")
    for _ in range(settle_steps):
        _write_robot_articulation_targets(robot_articulation)
        sim.step(render=False)
        _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
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

    _log(f"capturing overview video frames with TiledCamera: {frame_count} frames")
    for frame_idx in range(frame_count):
        step_count = 1 if frame_idx == 0 else max(1, int(sim_steps_per_frame))
        for _ in range(step_count):
            _write_robot_articulation_targets(robot_articulation)
            sim.step(render=False)
            _update_robot_articulation(robot_articulation, float(sim.cfg.dt))
        if frame_callback is not None:
            frame_callback(frame_idx, frame_count)
        sim.render()
        camera.update(float(sim.cfg.dt) * step_count)
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
    cube_path = "/World/CubeTask/Cube"
    cube_center = (
        float(args_cli.cube_start_x),
        float(args_cli.cube_start_y),
        float(surface_z) + 0.5 * float(args_cli.cube_size) + 0.001,
    )

    UsdGeom.Xform.Define(stage, "/World/CubeTask")
    _log("creating disturbed cube object")
    cube = _create_cube_object(
        stage,
        root_path=cube_path,
        center=cube_center,
        size=float(args_cli.cube_size),
        mat=cube_mat,
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

    def frame_callback(frame_idx: int, frame_count: int) -> None:
        state = _cube_motion_state(frame_idx, frame_count, surface_z)
        _apply_cube_motion(stage, cube_path, state)
        trajectory.append(state)

    metadata = {
        "generated_at_unix": time.time(),
        "task": "single_cube_motion",
        "task_description": "Static GraspGenX Franka rendered with one cube moved by deterministic disturbance kicks.",
        "simulation_backend": "Isaac Sim / Isaac Lab / PhysX USD scene",
        "robot": _robot_metadata(robot_spec),
        "robot_runtime": _robot_runtime_metadata(robot_articulation),
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
            ],
        },
        "simulation": {
            "physics_device": str(args_cli.physics_device),
            "sim_dt": 1.0 / 60.0,
            "render_interval": 1,
            "cube_motion_is_keyframed": True,
        },
        "checks": {
            "robot_selected": robot_spec.name,
            "uses_graspgenx_franka": robot_spec.name == "graspgenx_franka_panda",
            "franka_is_static": robot_spec.render_mode == "static_urdf_obj_meshes",
            "franka_is_articulation": robot_spec.render_mode == "articulation_usd",
            "franka_has_actuators": bool(robot_spec.actuator_config),
            "cube_moves": True,
        },
    }
    _write_metadata(output_dir / "scene_metadata.json", metadata)

    usd_path = output_dir / "franka_cube_motion_env.usda"
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
        )
        rendered = {"overview_frames": frame_paths}
    else:
        frame_callback(0, 1)
        _log(f"capturing view: {name}")
        rendered = {name: str(_capture_view(name, eye, look_at, output_dir))}

    _write_metadata(output_dir / "trajectory.json", {"cube_trajectory": trajectory})
    _write_metadata(
        output_dir / "render_manifest.json",
        {
            "usd": str(usd_path),
            "metadata": str(output_dir / "scene_metadata.json"),
            "trajectory": str(output_dir / "trajectory.json"),
            "renders": rendered,
            "fps": int(args_cli.fps),
            "video_seconds": float(args_cli.video_seconds),
            "sim_steps_per_frame": int(args_cli.sim_steps_per_frame),
        },
    )

    print(f"Wrote Franka cube-motion scene renders to {output_dir}")
    print(f"Cube trajectory frames: {len(trajectory)}")
    print(f"USD: {usd_path}")


def main() -> None:
    output_dir = args_cli.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"output_dir={output_dir}")

    robot_spec = _resolve_robot(output_dir)

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
    star_mat = _material(stage, "/World/Looks/star_yellow", (0.95, 0.70, 0.16), roughness=0.55)
    cube_mat = _material(stage, "/World/Looks/cube_blue", (0.10, 0.42, 0.86), roughness=0.62)
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

    if robot_spec.usd_path is not None:
        _log(f"referencing robot USD: {robot_spec.usd_path}")
    else:
        _log(f"creating robot with render_mode={robot_spec.render_mode}")
    robot_articulation = _create_robot(stage, robot_spec)

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

    if args_cli.scene == "cube_motion":
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
    settled_transform_baked = _settle_scene(sim, stage, star, settle_steps, robot_articulation)

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
        "robot": _robot_metadata(robot_spec),
        "robot_runtime": _robot_runtime_metadata(robot_articulation),
        "robot_usd": str(robot_spec.usd_path) if robot_spec.usd_path else None,
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
            "sim_dt": 1.0 / 60.0,
            "render_interval": 1,
            "default_static_friction": 1.0,
            "default_dynamic_friction": 1.0,
            "physx_bounce_threshold_velocity": 0.2,
        },
        "checks": {
            "robot_selected": robot_spec.name,
            "uses_graspgenx_franka": robot_spec.name == "graspgenx_franka_panda",
            "franka_is_articulation": robot_spec.render_mode == "articulation_usd",
            "franka_has_actuators": bool(robot_spec.actuator_config),
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
            robot_articulation=robot_articulation,
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
