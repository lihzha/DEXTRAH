"""Render reset-to-settle video evidence for tabletop clutter tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
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
parser.add_argument("--tabletop_clutter_spawn_z_clearance", type=float, default=None)
parser.add_argument("--tabletop_clutter_spawn_z_jitter", type=float, default=None)
parser.add_argument("--tabletop_clutter_require_graspgen_scale", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_enabled", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_cache_dir", type=str, default=None)
parser.add_argument("--tabletop_clutter_stable_pose_count", type=int, default=None)
parser.add_argument("--tabletop_clutter_non_overlapping", action=argparse.BooleanOptionalAction, default=None)
parser.add_argument("--tabletop_clutter_placement_padding", type=float, default=None)
parser.add_argument("--tabletop_clutter_placement_attempts", type=int, default=None)
parser.add_argument("--tabletop_clutter_max_xy_radius", type=float, default=None)
parser.add_argument("--tabletop_clutter_solver_position_iterations", type=int, default=None)
parser.add_argument("--tabletop_clutter_solver_velocity_iterations", type=int, default=None)
parser.add_argument("--tabletop_clutter_linear_damping", type=float, default=None)
parser.add_argument("--tabletop_clutter_angular_damping", type=float, default=None)
parser.add_argument("--tabletop_clutter_sleep_threshold", type=float, default=None)
parser.add_argument("--tabletop_clutter_stabilization_threshold", type=float, default=None)
parser.add_argument("--tabletop_clutter_max_depenetration_velocity", type=float, default=None)
parser.add_argument("--objaverse_textured_manifest_path", type=str, default=None)
parser.add_argument("--objaverse_textured_asset_dir", type=str, default=None)
parser.add_argument("--objaverse_textured_max_assets", type=int, default=None)
parser.add_argument("--objaverse_textured_mesh_source", type=str, default="auto", choices=["auto", "glb", "obj", "urdf_obj"])
parser.add_argument("--objaverse_textured_make_instanceable", action="store_true", default=False)
parser.add_argument("--objaverse_textured_force_conversion", action="store_true", default=False)
parser.add_argument("--objaverse_textured_collision_approximation", type=str, default="convexHull")
parser.add_argument("--objaverse_textured_require_graspgen_prior_scale", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--objaverse_textured_stable_pose_mesh_mode", type=str, default="convex_hull", choices=("convex_hull", "visual"))
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


def _npz_scalar(value) -> object:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _resolve_record_grasp_prior_path(record: dict[str, object], *, asset_root: Path) -> Path | None:
    candidates: list[Path] = []
    for key in ("grasp_prior_path", "source_grasp_prior_path"):
        value = record.get(key)
        if value:
            candidates.append(_resolve_path(str(value), base_dir=asset_root))
    prior = record.get("grasp_prior")
    if isinstance(prior, dict):
        for key in ("path", "grasp_prior_path", "prior_path"):
            value = prior.get(key)
            if value:
                candidates.append(_resolve_path(str(value), base_dir=asset_root))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0] if candidates else None


def _load_graspgen_object_scale_from_prior(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            if "object_scale" in data.files:
                scale = float(_npz_scalar(data["object_scale"]))
                if math.isfinite(scale) and scale > 0.0:
                    return scale
            if "metadata_json" in data.files:
                metadata = json.loads(str(_npz_scalar(data["metadata_json"])))
                if "object_scale" in metadata:
                    scale = float(metadata["object_scale"])
                    if math.isfinite(scale) and scale > 0.0:
                        return scale
    except Exception:
        return None
    return None


def _normalize_graspgen_record_scale(
    record: dict[str, object],
    *,
    asset_root: Path,
    require_prior_scale: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    uuid = str(record.get("uuid") or record.get("name") or "")
    prior_path = _resolve_record_grasp_prior_path(record, asset_root=asset_root)
    prior_scale = _load_graspgen_object_scale_from_prior(prior_path)
    record_has_scale = record.get("scale") is not None
    if prior_scale is not None:
        scale = float(prior_scale)
        scale_source = "grasp_prior.object_scale"
    elif require_prior_scale:
        raise ValueError(f"Could not read GraspGen object_scale for {uuid} from prior: {prior_path}")
    elif record_has_scale:
        scale = float(record["scale"])
        scale_source = "manifest.scale"
    else:
        scale = 1.0
        scale_source = "default"

    normalized = dict(record)
    normalized["scale"] = float(scale)
    normalized["scale_source"] = scale_source
    if prior_path is not None:
        normalized["grasp_prior_path"] = str(prior_path)
        prior = dict(normalized.get("grasp_prior") or {})
        prior["path"] = str(prior_path)
        prior["scale_source"] = scale_source
        normalized["grasp_prior"] = prior
    if "bounds_min" in normalized and "bounds_max" in normalized:
        bounds_min = [float(v) for v in normalized["bounds_min"]]
        bounds_max = [float(v) for v in normalized["bounds_max"]]
        scaled_bounds_min = [float(scale) * value for value in bounds_min]
        scaled_bounds_max = [float(scale) * value for value in bounds_max]
        normalized["scaled_bounds_min"] = scaled_bounds_min
        normalized["scaled_bounds_max"] = scaled_bounds_max
        normalized["scaled_half_extents"] = [
            0.5 * (scaled_bounds_max[axis] - scaled_bounds_min[axis]) for axis in range(3)
        ]
    summary = {
        "uuid": uuid,
        "scale": float(scale),
        "scale_source": scale_source,
        "grasp_prior_path": "" if prior_path is None else str(prior_path),
    }
    return normalized, summary


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


def _load_scaled_trimesh(mesh_path: Path, *, scale: float):
    import trimesh

    loaded = trimesh.load(mesh_path, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [geom for geom in loaded.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"Scene contains no meshes: {mesh_path}")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unsupported trimesh load result for {mesh_path}: {type(loaded).__name__}")
    mesh = mesh.copy()
    mesh.apply_scale(float(scale))
    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        raise ValueError(f"Mesh has no vertices/faces after scaling: {mesh_path}")
    return mesh


def _write_stable_pose_cache(
    *,
    uuid: str,
    mesh_path: Path,
    scale: float,
    cache_dir: Path,
    pose_count: int,
    mesh_mode: str,
) -> dict[str, object]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{uuid}.npz"
    pose_count = max(int(pose_count), 1)
    if cache_path.is_file():
        try:
            with np.load(cache_path, allow_pickle=False) as data:
                cached_scale = float(_npz_scalar(data["scale"])) if "scale" in data.files else None
                cached_pose_count = int(_npz_scalar(data["pose_count"])) if "pose_count" in data.files else 0
            if cached_scale is not None and abs(cached_scale - float(scale)) < 1.0e-8 and cached_pose_count >= pose_count:
                return {
                    "uuid": uuid,
                    "path": str(cache_path),
                    "scale": float(scale),
                    "pose_count": int(cached_pose_count),
                    "mesh_mode": str(mesh_mode),
                    "cached": True,
                }
        except Exception:
            pass

    mesh = _load_scaled_trimesh(mesh_path, scale=float(scale))
    if str(mesh_mode) == "visual":
        pose_mesh = mesh.copy()
    else:
        pose_mesh = mesh.convex_hull
        pose_mesh.merge_vertices()
        pose_mesh.remove_unreferenced_vertices()
    transforms, probabilities = pose_mesh.compute_stable_poses(sigma=0.0, n_samples=1, threshold=0.0)
    if len(transforms) == 0:
        raise RuntimeError(f"trimesh returned no stable poses for {uuid}")
    order = np.argsort(np.asarray(probabilities))[::-1]
    transforms = np.asarray(transforms, dtype=np.float64)[order]
    probabilities = np.asarray(probabilities, dtype=np.float64)[order]
    rotations = transforms[:, :3, :3]
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    root_z_offsets = []
    for rotation in rotations:
        rotated = vertices @ rotation.T
        root_z_offsets.append(-float(rotated[:, 2].min()))
    root_z_offsets = np.asarray(root_z_offsets, dtype=np.float64)
    np.savez_compressed(
        cache_path,
        uuid=np.asarray(uuid),
        scale=np.asarray(float(scale), dtype=np.float32),
        mesh_path=np.asarray(str(mesh_path)),
        stable_pose_mesh_mode=np.asarray(str(mesh_mode)),
        transforms=transforms,
        rotations=rotations,
        probabilities=probabilities,
        vertices=vertices,
        root_z_offsets=root_z_offsets,
        pose_count=np.asarray(min(pose_count, len(transforms)), dtype=np.int64),
    )
    return {
        "uuid": uuid,
        "path": str(cache_path),
        "scale": float(scale),
        "pose_count": int(min(pose_count, len(transforms))),
        "num_stable_poses": int(len(transforms)),
        "mesh_mode": str(mesh_mode),
        "visual_vertex_count": int(len(mesh.vertices)),
        "visual_face_count": int(len(mesh.faces)),
        "pose_vertex_count": int(len(pose_mesh.vertices)),
        "pose_face_count": int(len(pose_mesh.faces)),
        "cached": False,
    }


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
    require_graspgen_prior_scale: bool,
    max_xy_radius: float | None,
    stable_pose_cache_dir: Path | None,
    stable_pose_count: int,
    stable_pose_mesh_mode: str,
) -> tuple[Path, dict[str, object]]:
    manifest_path = manifest_path.expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    object_records = payload.get("objects")
    if not isinstance(object_records, list) or not object_records:
        raise ValueError(f"Expected non-empty objects list in Objaverse manifest: {manifest_path}")

    asset_root_value = str(payload.get("asset_root") or ".")
    asset_root = _resolve_path(asset_root_value, base_dir=manifest_path.parent)
    scale_summaries: list[dict[str, object]] = []
    normalized_records: list[dict[str, object]] = []
    for record in object_records:
        if not isinstance(record, dict):
            continue
        normalized, scale_summary = _normalize_graspgen_record_scale(
            record,
            asset_root=asset_root,
            require_prior_scale=bool(require_graspgen_prior_scale),
        )
        normalized_records.append(normalized)
        scale_summaries.append(scale_summary)
    object_records = normalized_records
    size_filtered_count = 0
    max_xy_radius_value = None if max_xy_radius is None else float(max_xy_radius)
    if max_xy_radius_value is not None and max_xy_radius_value > 0.0:
        before_count = len(object_records)
        object_records = [record for record in object_records if _record_xy_radius(record) <= max_xy_radius_value]
        size_filtered_count = before_count - len(object_records)
        if not object_records:
            raise ValueError(f"No Objaverse records remain after max_xy_radius={max_xy_radius_value} filtering")
    if prioritize_common_tabletop:
        object_records = _prioritize_tabletop_objaverse_records(object_records)
    limit = len(object_records) if max_assets is None or int(max_assets) <= 0 else min(int(max_assets), len(object_records))
    output_dir.mkdir(parents=True, exist_ok=True)
    usd_root = output_dir / "USD"
    converted_records: list[dict[str, object]] = []
    converted_meshes: list[dict[str, object]] = []
    stable_pose_summaries: list[dict[str, object]] = []

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
        if stable_pose_cache_dir is not None:
            stable_summary = _write_stable_pose_cache(
                uuid=uuid,
                mesh_path=mesh_path,
                scale=float(textured_record["scale"]),
                cache_dir=stable_pose_cache_dir,
                pose_count=int(stable_pose_count),
                mesh_mode=str(stable_pose_mesh_mode),
            )
            textured_record["stable_pose_path"] = str(stable_summary["path"])
            stable_pose_summaries.append(stable_summary)
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
        "require_graspgen_prior_scale": bool(require_graspgen_prior_scale),
        "max_xy_radius": max_xy_radius_value,
        "size_filtered_count": int(size_filtered_count),
        "scale_summaries": scale_summaries[:limit],
        "stable_pose_cache_dir": "" if stable_pose_cache_dir is None else str(stable_pose_cache_dir),
        "stable_pose_summaries": stable_pose_summaries,
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


def _speed_summary_from_root_vel(root_vel_w: torch.Tensor) -> dict[str, object]:
    root_vel_w = root_vel_w.detach().float()
    linear_speed = torch.linalg.norm(root_vel_w[:, 0:3], dim=-1)
    angular_speed = torch.linalg.norm(root_vel_w[:, 3:6], dim=-1)
    return {
        "linear_speed": _tensor_list(linear_speed),
        "angular_speed": _tensor_list(angular_speed),
        "max_linear_speed": float(linear_speed.max().detach().cpu().item()) if linear_speed.numel() else 0.0,
        "max_angular_speed": float(angular_speed.max().detach().cpu().item()) if angular_speed.numel() else 0.0,
    }


def _root_velocity_summary(task_env) -> dict[str, object]:
    summary: dict[str, object] = {}
    target_vel = getattr(task_env._cube.data, "root_vel_w", None)
    if isinstance(target_vel, torch.Tensor):
        summary["target"] = _speed_summary_from_root_vel(target_vel)
    clutter_objects = list(getattr(task_env, "_tabletop_clutter_objects", []))
    if clutter_objects:
        clutter = []
        max_linear = 0.0
        max_angular = 0.0
        for slot_idx, clutter_object in enumerate(clutter_objects):
            root_vel = getattr(clutter_object.data, "root_vel_w", None)
            if not isinstance(root_vel, torch.Tensor):
                continue
            slot_summary = _speed_summary_from_root_vel(root_vel)
            slot_summary["slot_idx"] = int(slot_idx)
            clutter.append(slot_summary)
            max_linear = max(max_linear, float(slot_summary["max_linear_speed"]))
            max_angular = max(max_angular, float(slot_summary["max_angular_speed"]))
        summary["clutter_by_slot"] = clutter
        summary["clutter_max_linear_speed"] = float(max_linear)
        summary["clutter_max_angular_speed"] = float(max_angular)
    return summary


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
        if args_cli.tabletop_clutter_object_count is None:
            args_cli.tabletop_clutter_object_count = 6
        if args_cli.tabletop_clutter_require_graspgen_scale is None:
            args_cli.tabletop_clutter_require_graspgen_scale = True
        if args_cli.tabletop_clutter_stable_pose_enabled is None:
            args_cli.tabletop_clutter_stable_pose_enabled = True
        if args_cli.tabletop_clutter_stable_pose_count is None:
            args_cli.tabletop_clutter_stable_pose_count = 1
        if args_cli.tabletop_clutter_spawn_z_clearance is None:
            args_cli.tabletop_clutter_spawn_z_clearance = 0.003
        if args_cli.tabletop_clutter_spawn_z_jitter is None:
            args_cli.tabletop_clutter_spawn_z_jitter = 0.0
        if args_cli.tabletop_clutter_solver_position_iterations is None:
            args_cli.tabletop_clutter_solver_position_iterations = 16
        if args_cli.tabletop_clutter_solver_velocity_iterations is None:
            args_cli.tabletop_clutter_solver_velocity_iterations = 6
        if args_cli.tabletop_clutter_linear_damping is None:
            args_cli.tabletop_clutter_linear_damping = 0.25
        if args_cli.tabletop_clutter_angular_damping is None:
            args_cli.tabletop_clutter_angular_damping = 1.25
        if args_cli.tabletop_clutter_sleep_threshold is None:
            args_cli.tabletop_clutter_sleep_threshold = 0.06
        if args_cli.tabletop_clutter_stabilization_threshold is None:
            args_cli.tabletop_clutter_stabilization_threshold = 0.03
        if args_cli.tabletop_clutter_max_depenetration_velocity is None:
            args_cli.tabletop_clutter_max_depenetration_velocity = 2.0
        stable_pose_cache_dir = None
        if bool(args_cli.tabletop_clutter_stable_pose_enabled):
            stable_pose_cache_dir = (
                Path(args_cli.tabletop_clutter_stable_pose_cache_dir).expanduser().resolve()
                if args_cli.tabletop_clutter_stable_pose_cache_dir
                else textured_asset_dir / "stable_pose_cache"
            )
            args_cli.tabletop_clutter_stable_pose_cache_dir = str(stable_pose_cache_dir)
        textured_manifest, objaverse_textured_summary = _prepare_textured_objaverse_manifest(
            manifest_path=Path(args_cli.objaverse_textured_manifest_path),
            output_dir=textured_asset_dir,
            max_assets=args_cli.objaverse_textured_max_assets,
            mesh_source=str(args_cli.objaverse_textured_mesh_source),
            make_instanceable=bool(args_cli.objaverse_textured_make_instanceable),
            force_conversion=bool(args_cli.objaverse_textured_force_conversion),
            collision_approximation=str(args_cli.objaverse_textured_collision_approximation),
            prioritize_common_tabletop=not bool(args_cli.disable_objaverse_textured_common_tabletop_priority),
            require_graspgen_prior_scale=bool(args_cli.objaverse_textured_require_graspgen_prior_scale),
            max_xy_radius=args_cli.tabletop_clutter_max_xy_radius,
            stable_pose_cache_dir=stable_pose_cache_dir,
            stable_pose_count=int(args_cli.tabletop_clutter_stable_pose_count),
            stable_pose_mesh_mode=str(args_cli.objaverse_textured_stable_pose_mesh_mode),
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
    _set_if_present(env_cfg, "tabletop_clutter_spawn_z_clearance", args_cli.tabletop_clutter_spawn_z_clearance)
    _set_if_present(env_cfg, "tabletop_clutter_spawn_z_jitter", args_cli.tabletop_clutter_spawn_z_jitter)
    _set_if_present(env_cfg, "tabletop_clutter_require_graspgen_scale", args_cli.tabletop_clutter_require_graspgen_scale)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_enabled", args_cli.tabletop_clutter_stable_pose_enabled)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_cache_dir", args_cli.tabletop_clutter_stable_pose_cache_dir)
    _set_if_present(env_cfg, "tabletop_clutter_stable_pose_count", args_cli.tabletop_clutter_stable_pose_count)
    _set_if_present(env_cfg, "tabletop_clutter_non_overlapping", args_cli.tabletop_clutter_non_overlapping)
    _set_if_present(env_cfg, "tabletop_clutter_placement_padding", args_cli.tabletop_clutter_placement_padding)
    _set_if_present(env_cfg, "tabletop_clutter_placement_attempts", args_cli.tabletop_clutter_placement_attempts)
    _set_if_present(env_cfg, "tabletop_clutter_max_xy_radius", args_cli.tabletop_clutter_max_xy_radius)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_solver_position_iterations",
        args_cli.tabletop_clutter_solver_position_iterations,
    )
    _set_if_present(
        env_cfg,
        "tabletop_clutter_solver_velocity_iterations",
        args_cli.tabletop_clutter_solver_velocity_iterations,
    )
    _set_if_present(env_cfg, "tabletop_clutter_linear_damping", args_cli.tabletop_clutter_linear_damping)
    _set_if_present(env_cfg, "tabletop_clutter_angular_damping", args_cli.tabletop_clutter_angular_damping)
    _set_if_present(env_cfg, "tabletop_clutter_sleep_threshold", args_cli.tabletop_clutter_sleep_threshold)
    _set_if_present(
        env_cfg,
        "tabletop_clutter_stabilization_threshold",
        args_cli.tabletop_clutter_stabilization_threshold,
    )
    _set_if_present(
        env_cfg,
        "tabletop_clutter_max_depenetration_velocity",
        args_cli.tabletop_clutter_max_depenetration_velocity,
    )
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
    initial_velocity_summary = _root_velocity_summary(task_env)

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
    final_velocity_summary = _root_velocity_summary(task_env)
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
        "initial_velocity_summary": initial_velocity_summary,
        "initial_clearance_summary": initial_clearance_summary,
        "final_snapshot": final_snapshot,
        "final_velocity_summary": final_velocity_summary,
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
