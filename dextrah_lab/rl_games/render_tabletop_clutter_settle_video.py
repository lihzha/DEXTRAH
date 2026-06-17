"""Render reset-to-settle video evidence for tabletop clutter tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import traceback

from isaaclab.app import AppLauncher


DEFAULT_FRANKA_CAMERA_EYE = (-0.10, -1.05, 1.36)
DEFAULT_FRANKA_CAMERA_TARGET = (-0.62, 0.0, 0.78)
DEFAULT_YAM_CAMERA_EYE = (-0.52, -0.86, 0.72)
DEFAULT_YAM_CAMERA_TARGET = (-0.27, 0.0, 0.08)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Tabletop-Clutter-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default="artifacts/tabletop_clutter_settle")
parser.add_argument("--video_path", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--settle_steps", type=int, default=180)
parser.add_argument("--capture_interval", type=int, default=2)
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--video_seconds", type=float, default=None)
parser.add_argument("--render_warmup_frames", type=int, default=2)
parser.add_argument("--camera_eye", type=float, nargs=3, default=None)
parser.add_argument("--camera_target", type=float, nargs=3, default=None)
parser.add_argument("--object_asset_manifest_path", type=str, default=None)
parser.add_argument("--object_assets_dir", type=str, default=None)
parser.add_argument("--max_objects", type=int, default=None)
parser.add_argument("--object_asset_assignment", type=str, default=None)
parser.add_argument("--object_spawn_xy_randomization", type=float, default=None)
parser.add_argument("--object_spawn_yaw_randomization_deg", type=float, default=None)
parser.add_argument("--tabletop_clutter_asset_manifest_path", type=str, default=None)
parser.add_argument("--tabletop_clutter_assets_dir", type=str, default=None)
parser.add_argument("--tabletop_clutter_max_objects", type=int, default=None)
parser.add_argument("--tabletop_clutter_object_count", type=int, default=None)
parser.add_argument("--tabletop_clutter_asset_assignment", type=str, default=None)
parser.add_argument("--tabletop_clutter_spawn_xy_randomization", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_yaw_randomization_deg", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_z_jitter", type=float, default=None)
parser.add_argument("--tabletop_clutter_non_overlapping", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_placement_padding", type=float, default=None)
parser.add_argument("--tabletop_clutter_placement_attempts", type=int, default=None)
parser.add_argument("--tabletop_clutter_max_xy_radius", type=float, default=None)
parser.add_argument("--objaverse_textured_manifest_path", type=str, default=None)
parser.add_argument("--objaverse_textured_asset_dir", type=str, default=None)
parser.add_argument("--objaverse_textured_max_assets", type=int, default=None)
parser.add_argument("--objaverse_textured_mesh_source", type=str, default="auto", choices=["auto", "glb", "obj", "urdf_obj"])
parser.add_argument("--objaverse_textured_make_instanceable", action="store_true", default=False)
parser.add_argument("--objaverse_textured_force_conversion", action="store_true", default=False)
parser.add_argument("--objaverse_textured_collision_approximation", type=str, default="convexHull")
parser.add_argument("--disable_objaverse_textured_common_tabletop_priority", action="store_true", default=False)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
args_cli.enable_cameras = True
sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import imageio.v2 as imageio
import numpy as np
import torch

import isaaclab_tasks  # noqa: F401
import isaaclab.sim as sim_utils
from isaacsim.core.utils.extensions import enable_extension
from isaaclab.sim.converters import MeshConverter, MeshConverterCfg
from isaaclab.sim.schemas import schemas as sim_schemas
from isaaclab_tasks.utils import parse_env_cfg
from pxr import Usd, UsdPhysics

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401

if "YAM" in args_cli.task:
    import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup  # noqa: F401
    import dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.gym_setup  # noqa: F401


def _set_if_present(cfg, name: str, value) -> None:
    if value is not None and hasattr(cfg, name):
        setattr(cfg, name, value)


def _task_camera_defaults(task: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if "YAM" in task:
        return DEFAULT_YAM_CAMERA_EYE, DEFAULT_YAM_CAMERA_TARGET
    return DEFAULT_FRANKA_CAMERA_EYE, DEFAULT_FRANKA_CAMERA_TARGET


def _frame_array(frame) -> np.ndarray:
    if isinstance(frame, (list, tuple)):
        if not frame:
            raise RuntimeError("render() returned an empty frame list")
        frame = frame[0]
    frame = np.asarray(frame)
    if frame.ndim == 4:
        frame = frame[0]
    if frame.ndim != 3 or frame.shape[-1] not in (3, 4):
        raise RuntimeError(f"Unexpected render frame shape: {frame.shape}")
    if frame.shape[-1] == 4:
        frame = frame[:, :, :3]
    return frame.astype(np.uint8, copy=False)


def _capture_frame(env, frame_dir: Path, frame_idx: int) -> tuple[np.ndarray, str]:
    frame = _frame_array(env.render())
    frame_path = frame_dir / f"frame_{frame_idx:04d}.png"
    imageio.imwrite(frame_path, frame)
    return frame, str(frame_path)


def _tensor_list(value: torch.Tensor):
    return value.detach().float().cpu().tolist()


def _resolve_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


COMMON_TABLETOP_KEYWORDS = (
    "apple",
    "bag",
    "bagel",
    "bar",
    "bottle",
    "bowl",
    "box",
    "can",
    "candy",
    "container",
    "cup",
    "dish",
    "food",
    "fork",
    "fruit",
    "jar",
    "knife",
    "marker",
    "mug",
    "pen",
    "pepper",
    "plate",
    "remote",
    "scissors",
    "snack",
    "soap",
    "spoon",
    "sponge",
    "teapot",
    "toothbrush",
    "vase",
)
EXCLUDED_TABLETOP_KEYWORDS = ("animal", "building", "car", "chair", "person", "plant", "room", "statue", "tree", "vehicle")


def _collect_text(value: object, fragments: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        fragments.append(value)
    elif isinstance(value, (int, float, bool)):
        fragments.append(str(value))
    elif isinstance(value, dict):
        for nested_value in value.values():
            _collect_text(nested_value, fragments)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            _collect_text(nested_value, fragments)


def _record_text(record: dict[str, object]) -> str:
    fragments: list[str] = []
    for key in (
        "name",
        "title",
        "category",
        "categories",
        "class",
        "labels",
        "tags",
        "description",
        "object_name",
        "synset",
        "metadata",
        "annotations",
    ):
        _collect_text(record.get(key), fragments)
    if not fragments:
        fragments.append(str(record.get("uuid") or ""))
    return " ".join(fragments).lower()


def _record_xy_radius(record: dict[str, object]) -> float:
    if record.get("scaled_bounds_min") is not None and record.get("scaled_bounds_max") is not None:
        bounds_min = [float(v) for v in record["scaled_bounds_min"]]
        bounds_max = [float(v) for v in record["scaled_bounds_max"]]
        return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))
    if record.get("scaled_half_extents") is not None:
        half_extents = [float(v) for v in record["scaled_half_extents"]]
        return max(half_extents[0], half_extents[1])
    if record.get("bounds_min") is not None and record.get("bounds_max") is not None:
        scale = float(record.get("scale", 1.0))
        bounds_min = [scale * float(v) for v in record["bounds_min"]]
        bounds_max = [scale * float(v) for v in record["bounds_max"]]
        return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))
    if record.get("half_extents") is not None:
        scale = float(record.get("scale", 1.0))
        half_extents = [scale * float(v) for v in record["half_extents"]]
        return max(half_extents[0], half_extents[1])
    return 1.0


def _record_height(record: dict[str, object]) -> float:
    if record.get("scaled_bounds_min") is not None and record.get("scaled_bounds_max") is not None:
        return float(record["scaled_bounds_max"][2]) - float(record["scaled_bounds_min"][2])
    if record.get("scaled_half_extents") is not None:
        return 2.0 * float(record["scaled_half_extents"][2])
    if record.get("bounds_min") is not None and record.get("bounds_max") is not None:
        scale = float(record.get("scale", 1.0))
        return scale * (float(record["bounds_max"][2]) - float(record["bounds_min"][2]))
    if record.get("half_extents") is not None:
        return 2.0 * float(record.get("scale", 1.0)) * float(record["half_extents"][2])
    return 1.0


def _prioritize_tabletop_objaverse_records(records: list[object]) -> list[object]:
    def sort_key(item: tuple[int, object]) -> tuple[float, float, int]:
        index, record = item
        if not isinstance(record, dict):
            return (float("inf"), float("inf"), index)
        text = _record_text(record)
        common_hits = sum(1 for keyword in COMMON_TABLETOP_KEYWORDS if keyword in text)
        excluded_hits = sum(1 for keyword in EXCLUDED_TABLETOP_KEYWORDS if keyword in text)
        radius = _record_xy_radius(record)
        height = _record_height(record)
        score = 50.0 * common_hits - 75.0 * excluded_hits
        if radius <= 0.14:
            score += 10.0
        else:
            score -= 80.0 * (radius - 0.14)
        score -= 3.0 * abs(radius - 0.07)
        if height > 0.28:
            score -= 2.0 * (height - 0.28)
        return (-score, radius, index)

    return [record for _, record in sorted(enumerate(records), key=sort_key)]


def _first_existing_objaverse_mesh(record: dict[str, object], *, asset_root: Path, mesh_source: str) -> Path:
    candidates: list[Path] = []
    raw_object_path = record.get("raw_object_path")
    uuid = str(record.get("uuid") or record.get("name") or "")
    mesh_source = str(mesh_source or "auto")
    if uuid and mesh_source in ("auto", "glb"):
        candidates.append(asset_root / "raw_objaverse" / f"{uuid}.glb")
    if raw_object_path and mesh_source in ("auto", "obj"):
        candidates.append(_resolve_path(str(raw_object_path), base_dir=asset_root))
    if uuid and mesh_source in ("auto", "obj"):
        candidates.extend(
            [
                asset_root / "raw_objaverse" / f"{uuid}.obj",
            ]
        )
    if uuid and mesh_source in ("auto", "urdf_obj"):
        candidates.append(asset_root / "urdf" / uuid / "visual_model.obj")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not find raw Objaverse mesh for manifest record {uuid!r}")


def _prepare_textured_objaverse_manifest(
    *,
    manifest_path: Path,
    output_dir: Path,
    max_assets: int | None,
    mesh_source: str,
    make_instanceable: bool,
    force_conversion: bool,
    collision_approximation: str,
    prioritize_common_tabletop: bool,
) -> tuple[Path, dict[str, object]]:
    manifest_path = manifest_path.expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    object_records = payload.get("objects")
    if not isinstance(object_records, list) or not object_records:
        raise ValueError(f"Expected non-empty objects list in Objaverse manifest: {manifest_path}")

    asset_root_value = str(payload.get("asset_root") or ".")
    asset_root = _resolve_path(asset_root_value, base_dir=manifest_path.parent)
    if prioritize_common_tabletop:
        object_records = _prioritize_tabletop_objaverse_records(object_records)
    limit = len(object_records) if max_assets is None or int(max_assets) <= 0 else min(int(max_assets), len(object_records))
    output_dir.mkdir(parents=True, exist_ok=True)
    usd_root = output_dir / "USD"
    converted_records: list[dict[str, object]] = []
    converted_meshes: list[dict[str, object]] = []

    collision_approximation = str(collision_approximation)
    collision_props = sim_utils.CollisionPropertiesCfg(
        collision_enabled=collision_approximation != "none",
        contact_offset=0.004,
        rest_offset=0.0,
    )
    for record_idx, record in enumerate(object_records[:limit]):
        if not isinstance(record, dict):
            raise ValueError(f"Objaverse manifest record is not a mapping: {record!r}")
        uuid = str(record.get("uuid") or record.get("name") or f"object_{len(converted_records)}")
        mesh_path = _first_existing_objaverse_mesh(record, asset_root=asset_root, mesh_source=str(mesh_source))
        usd_dir = usd_root / uuid
        usd_path = usd_dir / f"{uuid}.usd"
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_conversion_start",
                    "idx": int(record_idx),
                    "uuid": uuid,
                    "mesh_path": str(mesh_path),
                    "mesh_size": int(mesh_path.stat().st_size),
                    "usd_path": str(usd_path),
                    "collision_approximation": collision_approximation,
                    "make_instanceable": bool(make_instanceable),
                }
            ),
            flush=True,
        )
        converted_usd_path: Path | None = None
        try:
            if mesh_path.suffix.lower() in (".glb", ".gltf"):
                converted_usd_path = _convert_glb_to_usd_direct(
                    mesh_path=mesh_path,
                    usd_path=usd_path,
                    collision_props=collision_props,
                    collision_approximation=collision_approximation,
                )
            else:
                converter_cfg = MeshConverterCfg(
                    asset_path=str(mesh_path),
                    usd_dir=str(usd_dir),
                    usd_file_name=usd_path.name,
                    force_usd_conversion=bool(force_conversion),
                    make_instanceable=bool(make_instanceable),
                    collision_props=collision_props,
                    collision_approximation=str(collision_approximation),
                )
                converter = MeshConverter(converter_cfg)
                converted_usd_path = Path(converter.usd_path)
        except BaseException as exc:
            print(
                json.dumps(
                    {
                        "event": "objaverse_textured_conversion_failed",
                        "idx": int(record_idx),
                        "uuid": uuid,
                        "mesh_path": str(mesh_path),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                ),
                flush=True,
            )
            raise
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_conversion_done",
                    "idx": int(record_idx),
                    "uuid": uuid,
                    "usd_path": str(converted_usd_path),
                }
            ),
            flush=True,
        )
        textured_record = dict(record)
        textured_record["usd_path"] = os.path.relpath(converted_usd_path, output_dir)
        textured_record["raw_object_path"] = str(mesh_path)
        textured_record["source_usd_path"] = str(record.get("usd_path") or "")
        converted_records.append(textured_record)
        converted_meshes.append(
            {
                "uuid": uuid,
                "mesh_path": str(mesh_path),
                "usd_path": str(converted_usd_path),
            }
        )

    textured_manifest = output_dir / "manifest.json"
    textured_payload = {
        "format": "dextrah_textured_objaverse_manifest_v1",
        "asset_root": ".",
        "source_manifest_path": str(manifest_path),
        "source_dataset": payload.get("source_dataset", "objaverse"),
        "selected_uuid_count": len(converted_records),
        "objects": converted_records,
        "conversion": {
            "converter": "isaaclab.sim.converters.MeshConverter",
            "collision_approximation": str(collision_approximation),
            "mesh_source": str(mesh_source),
            "make_instanceable": bool(make_instanceable),
            "force_usd_conversion": bool(force_conversion),
        },
    }
    textured_manifest.write_text(json.dumps(textured_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "source_manifest_path": str(manifest_path),
        "textured_manifest_path": str(textured_manifest),
        "asset_root": str(asset_root),
        "output_dir": str(output_dir),
        "num_objects": len(converted_records),
        "prioritize_common_tabletop": bool(prioritize_common_tabletop),
        "converted_meshes": converted_meshes,
    }
    return textured_manifest, summary


def _convert_glb_to_usd_direct(
    *,
    mesh_path: Path,
    usd_path: Path,
    collision_props: sim_utils.CollisionPropertiesCfg,
    collision_approximation: str,
) -> Path:
    usd_path.parent.mkdir(parents=True, exist_ok=True)
    enable_extension("omni.kit.asset_converter")
    import omni.kit.asset_converter

    converter_context = omni.kit.asset_converter.AssetConverterContext()
    converter_context.ignore_materials = False
    converter_context.ignore_animations = True
    converter_context.ignore_camera = True
    converter_context.ignore_light = True
    converter_context.merge_all_meshes = True
    converter_context.use_meter_as_world_unit = True
    converter_context.baking_scales = True
    converter_context.use_double_precision_to_usd_transform_op = True
    converter_task = omni.kit.asset_converter.get_instance().create_converter_task(
        str(mesh_path),
        str(usd_path),
        None,
        converter_context,
    )
    success = asyncio.get_event_loop().run_until_complete(converter_task.wait_until_finished())
    if not success:
        raise RuntimeError(
            f"Failed to convert {mesh_path} to USD. Error: {converter_task.get_error_message()}"
        )
    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"Failed to open converted USD: {usd_path}")
    if not stage.GetDefaultPrim().IsValid():
        root_prims = [prim for prim in stage.GetPseudoRoot().GetChildren() if prim.IsValid()]
        if not root_prims:
            raise RuntimeError(f"Converted USD has no root prims: {usd_path}")
        stage.SetDefaultPrim(root_prims[0])
    default_prim = stage.GetDefaultPrim()
    sim_schemas.define_rigid_body_properties(
        prim_path=default_prim.GetPath(),
        cfg=sim_utils.RigidBodyPropertiesCfg(rigid_body_enabled=True, kinematic_enabled=False, disable_gravity=False),
        stage=stage,
    )
    sim_schemas.define_mass_properties(
        prim_path=default_prim.GetPath(),
        cfg=sim_utils.MassPropertiesCfg(density=100.0),
        stage=stage,
    )
    if str(collision_approximation) != "none":
        for prim in stage.Traverse():
            if prim.GetTypeName() == "Mesh":
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
                mesh_collision_api.GetApproximationAttr().Set(str(collision_approximation))
                sim_schemas.define_collision_properties(
                    prim_path=prim.GetPath(),
                    cfg=collision_props,
                    stage=stage,
                )
    stage.Save()
    return usd_path


def _capture_steps_for_video(settle_steps: int, target_frame_count: int) -> tuple[int, set[int]]:
    if target_frame_count <= 1:
        return max(int(settle_steps), 0), set()
    settle_steps = max(int(settle_steps), target_frame_count - 1)
    raw_steps = [int(round(value)) for value in np.linspace(1, settle_steps, target_frame_count - 1)]
    steps: list[int] = []
    used: set[int] = set()
    for step in raw_steps:
        step = min(max(int(step), 1), settle_steps)
        if step not in used:
            steps.append(step)
            used.add(step)
    if len(steps) < target_frame_count - 1:
        for step in range(1, settle_steps + 1):
            if step not in used:
                steps.append(step)
                used.add(step)
            if len(steps) >= target_frame_count - 1:
                break
    return settle_steps, set(sorted(steps[: target_frame_count - 1]))


def _root_snapshot(task_env) -> dict[str, object]:
    env_origins = task_env.scene.env_origins
    snapshot: dict[str, object] = {
        "target_root_pos": _tensor_list(task_env._cube.data.root_pos_w - env_origins),
        "target_root_quat": _tensor_list(task_env._cube.data.root_quat_w),
    }
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    if clutter_objects:
        clutter_pos = []
        clutter_quat = []
        for clutter_object in clutter_objects:
            clutter_pos.append(_tensor_list(clutter_object.data.root_pos_w - env_origins))
            clutter_quat.append(_tensor_list(clutter_object.data.root_quat_w))
        snapshot["clutter_root_pos_by_slot"] = clutter_pos
        snapshot["clutter_root_quat_by_slot"] = clutter_quat
    return snapshot


def _initial_clearance_summary(task_env, snapshot: dict[str, object]) -> dict[str, object] | None:
    clutter_positions = snapshot.get("clutter_root_pos_by_slot")
    if not isinstance(clutter_positions, list) or not clutter_positions:
        return None
    target_positions = snapshot.get("target_root_pos")
    if not isinstance(target_positions, list):
        return None
    target_radii = getattr(task_env, "object_xy_radius", None)
    clutter_radii = getattr(task_env, "tabletop_clutter_xy_radius", None)
    if target_radii is None or clutter_radii is None:
        return None
    target_radii_list = target_radii.detach().float().cpu().tolist()
    clutter_radii_list = clutter_radii.detach().float().cpu().tolist()
    min_clearance = float("inf")
    overlaps: list[dict[str, object]] = []
    pair_count = 0
    for env_idx, target_pos in enumerate(target_positions):
        bodies: list[tuple[str, tuple[float, float], float]] = [
            ("target", (float(target_pos[0]), float(target_pos[1])), float(target_radii_list[env_idx]))
        ]
        for slot_idx, slot_positions in enumerate(clutter_positions):
            slot_pos = slot_positions[env_idx]
            bodies.append(
                (
                    f"clutter_{slot_idx:02d}",
                    (float(slot_pos[0]), float(slot_pos[1])),
                    float(clutter_radii_list[env_idx][slot_idx]),
                )
            )
        for left_idx in range(len(bodies)):
            for right_idx in range(left_idx + 1, len(bodies)):
                left_name, left_xy, left_radius = bodies[left_idx]
                right_name, right_xy, right_radius = bodies[right_idx]
                clearance = (
                    float(np.hypot(left_xy[0] - right_xy[0], left_xy[1] - right_xy[1]))
                    - left_radius
                    - right_radius
                )
                min_clearance = min(min_clearance, clearance)
                pair_count += 1
                if clearance < -1.0e-6:
                    overlaps.append(
                        {
                            "env": int(env_idx),
                            "a": left_name,
                            "b": right_name,
                            "clearance": float(clearance),
                        }
                    )
    return {
        "pair_count": int(pair_count),
        "overlap_count": len(overlaps),
        "min_clearance": None if not np.isfinite(min_clearance) else float(min_clearance),
        "overlaps": overlaps[:20],
    }


def _write_video(video_path: Path, frames: list[np.ndarray], fps: int) -> None:
    if not frames:
        raise RuntimeError("No frames captured for video")
    writer = imageio.get_writer(str(video_path), fps=int(fps), macro_block_size=1)
    try:
        for frame in frames:
            writer.append_data(frame)
    finally:
        writer.close()


def _step_physics_without_task_reset(task_env, hold_joint_pos: torch.Tensor | None) -> None:
    robot = getattr(task_env, "_robot", None)
    if robot is not None and hold_joint_pos is not None:
        robot.set_joint_position_target(hold_joint_pos)
    task_env.scene.write_data_to_sim()
    task_env.sim.step(render=False)
    task_env.scene.update(dt=task_env.sim.cfg.dt)


def main() -> None:
    output_dir = Path(args_cli.output_dir).expanduser().resolve()
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(args_cli.video_path).expanduser().resolve() if args_cli.video_path else output_dir / "settle.mp4"
    metrics_path = (
        Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    )

    objaverse_textured_summary = None
    if args_cli.objaverse_textured_manifest_path:
        textured_asset_dir = (
            Path(args_cli.objaverse_textured_asset_dir).expanduser().resolve()
            if args_cli.objaverse_textured_asset_dir
            else output_dir / "objaverse_textured_assets"
        )
        textured_manifest, objaverse_textured_summary = _prepare_textured_objaverse_manifest(
            manifest_path=Path(args_cli.objaverse_textured_manifest_path),
            output_dir=textured_asset_dir,
            max_assets=args_cli.objaverse_textured_max_assets,
            mesh_source=str(args_cli.objaverse_textured_mesh_source),
            make_instanceable=bool(args_cli.objaverse_textured_make_instanceable),
            force_conversion=bool(args_cli.objaverse_textured_force_conversion),
            collision_approximation=str(args_cli.objaverse_textured_collision_approximation),
            prioritize_common_tabletop=not bool(args_cli.disable_objaverse_textured_common_tabletop_priority),
        )
        args_cli.object_asset_manifest_path = str(textured_manifest)
        args_cli.tabletop_clutter_asset_manifest_path = str(textured_manifest)
        if args_cli.max_objects is None and args_cli.objaverse_textured_max_assets:
            args_cli.max_objects = int(args_cli.objaverse_textured_max_assets)
        if args_cli.tabletop_clutter_max_objects is None and args_cli.objaverse_textured_max_assets:
            args_cli.tabletop_clutter_max_objects = int(args_cli.objaverse_textured_max_assets)
        print(
            json.dumps(
                {
                    "event": "objaverse_textured_manifest_prepared",
                    "manifest_path": str(textured_manifest),
                    "num_objects": int(objaverse_textured_summary["num_objects"]),
                }
            ),
            flush=True,
        )

    torch.manual_seed(int(args_cli.seed))
    np.random.seed(int(args_cli.seed))
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    if hasattr(env_cfg, "seed"):
        env_cfg.seed = int(args_cli.seed)
    _set_if_present(env_cfg, "object_asset_manifest_path", args_cli.object_asset_manifest_path)
    _set_if_present(env_cfg, "object_assets_dir", args_cli.object_assets_dir)
    _set_if_present(env_cfg, "max_objects", args_cli.max_objects)
    _set_if_present(env_cfg, "object_asset_assignment", args_cli.object_asset_assignment)
    _set_if_present(env_cfg, "object_spawn_xy_randomization", args_cli.object_spawn_xy_randomization)
    _set_if_present(env_cfg, "object_spawn_yaw_randomization_deg", args_cli.object_spawn_yaw_randomization_deg)
    _set_if_present(env_cfg, "tabletop_clutter_asset_manifest_path", args_cli.tabletop_clutter_asset_manifest_path)
    _set_if_present(env_cfg, "tabletop_clutter_assets_dir", args_cli.tabletop_clutter_assets_dir)
    _set_if_present(env_cfg, "tabletop_clutter_max_objects", args_cli.tabletop_clutter_max_objects)
    _set_if_present(env_cfg, "tabletop_clutter_object_count", args_cli.tabletop_clutter_object_count)
    _set_if_present(env_cfg, "tabletop_clutter_asset_assignment", args_cli.tabletop_clutter_asset_assignment)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_xy_randomization", args_cli.tabletop_clutter_spawn_xy_randomization)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_yaw_randomization_deg", args_cli.tabletop_clutter_spawn_yaw_randomization_deg)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_z_jitter", args_cli.tabletop_clutter_spawn_z_jitter)
    _set_if_present(env_cfg, "tabletop_clutter_non_overlapping", args_cli.tabletop_clutter_non_overlapping)
    _set_if_present(env_cfg, "tabletop_clutter_placement_padding", args_cli.tabletop_clutter_placement_padding)
    _set_if_present(env_cfg, "tabletop_clutter_placement_attempts", args_cli.tabletop_clutter_placement_attempts)
    _set_if_present(env_cfg, "tabletop_clutter_max_xy_radius", args_cli.tabletop_clutter_max_xy_radius)
    _set_if_present(env_cfg, "object_reset_settle_steps", 0)

    print(
        json.dumps(
            {
                "event": "creating_env",
                "task": args_cli.task,
                "num_envs": int(args_cli.num_envs),
                "settle_steps": int(args_cli.settle_steps),
                "capture_interval": int(args_cli.capture_interval),
                "output_dir": str(output_dir),
            }
        ),
        flush=True,
    )
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = env.unwrapped
    eye_default, target_default = _task_camera_defaults(args_cli.task)
    eye = tuple(float(v) for v in (args_cli.camera_eye or eye_default))
    target = tuple(float(v) for v in (args_cli.camera_target or target_default))
    task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=task_env.cfg.viewer.cam_prim_path)

    print(json.dumps({"event": "reset_start"}), flush=True)
    env.reset(seed=int(args_cli.seed))
    print(json.dumps({"event": "reset_done"}), flush=True)
    for _ in range(max(int(args_cli.render_warmup_frames), 0)):
        task_env.sim.render()
        env.render()
    print(json.dumps({"event": "render_warmup_done"}), flush=True)

    frames: list[np.ndarray] = []
    frame_paths: list[str] = []
    frame, frame_path = _capture_frame(env, frame_dir, 0)
    frames.append(frame)
    frame_paths.append(frame_path)
    print(json.dumps({"event": "frame_captured", "frame_idx": 0, "path": frame_path}), flush=True)
    initial_snapshot = _root_snapshot(task_env)

    robot = getattr(task_env, "_robot", None)
    hold_joint_pos = robot.data.joint_pos.detach().clone() if robot is not None else None
    capture_interval = max(int(args_cli.capture_interval), 1)
    settle_steps = max(int(args_cli.settle_steps), 0)
    target_frame_count = None
    capture_step_set: set[int] | None = None
    if args_cli.video_seconds is not None:
        target_frame_count = max(int(round(float(args_cli.video_seconds) * int(args_cli.fps))), 1)
        settle_steps, capture_step_set = _capture_steps_for_video(settle_steps, target_frame_count)
        print(
            json.dumps(
                {
                    "event": "video_seconds_capture_plan",
                    "video_seconds": float(args_cli.video_seconds),
                    "fps": int(args_cli.fps),
                    "target_frame_count": int(target_frame_count),
                    "settle_steps": int(settle_steps),
                    "capture_steps": int(len(capture_step_set)),
                }
            ),
            flush=True,
        )
    frame_idx = 1
    for step_idx in range(1, settle_steps + 1):
        _step_physics_without_task_reset(task_env, hold_joint_pos)
        should_capture = (
            step_idx in capture_step_set
            if capture_step_set is not None
            else (step_idx % capture_interval == 0 or step_idx == settle_steps)
        )
        if should_capture:
            frame, frame_path = _capture_frame(env, frame_dir, frame_idx)
            frames.append(frame)
            frame_paths.append(frame_path)
            print(
                json.dumps({"event": "frame_captured", "frame_idx": int(frame_idx), "step_idx": int(step_idx)}),
                flush=True,
            )
            frame_idx += 1

    final_snapshot = _root_snapshot(task_env)
    initial_clearance_summary = _initial_clearance_summary(task_env, initial_snapshot)
    final_clearance_summary = _initial_clearance_summary(task_env, final_snapshot)
    _write_video(video_path, frames, int(args_cli.fps))
    print(json.dumps({"event": "video_written", "path": str(video_path), "frame_count": len(frames)}), flush=True)

    metrics = {
        "task": args_cli.task,
        "num_envs": int(task_env.num_envs),
        "seed": int(args_cli.seed),
        "settle_steps": int(settle_steps),
        "capture_interval": int(capture_interval),
        "fps": int(args_cli.fps),
        "video_seconds": None if args_cli.video_seconds is None else float(args_cli.video_seconds),
        "target_frame_count": target_frame_count,
        "camera_eye": [float(v) for v in eye],
        "camera_target": [float(v) for v in target],
        "video_path": str(video_path),
        "frame_paths": frame_paths,
        "frame_count": len(frame_paths),
        "objaverse_textured_assets": objaverse_textured_summary,
        "multi_object_asset_summary": task_env.multi_object_asset_summary()
        if hasattr(task_env, "multi_object_asset_summary")
        else None,
        "tabletop_clutter_summary": task_env.tabletop_clutter_summary()
        if hasattr(task_env, "tabletop_clutter_summary")
        else None,
        "initial_snapshot": initial_snapshot,
        "initial_clearance_summary": initial_clearance_summary,
        "final_snapshot": final_snapshot,
        "final_clearance_summary": final_clearance_summary,
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"video_path": str(video_path), "metrics_path": str(metrics_path)}, indent=2), flush=True)
    env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        traceback.print_exc()
        print(
            json.dumps(
                {
                    "event": "main_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            ),
            flush=True,
        )
        raise
    finally:
        simulation_app.close()
