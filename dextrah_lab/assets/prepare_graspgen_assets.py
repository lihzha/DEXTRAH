#!/usr/bin/env python3
"""Prepare a DEXTRAH GraspGen object subset for Franka multi-object RL."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any
import urllib.request


HF_BASE_URL = "https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GraspGen/resolve/main"
DEFAULT_SPLIT_URL = f"{HF_BASE_URL}/splits/robotiq_2f_140/train.txt"
DEFAULT_GRASP_INDEX_URL = f"{HF_BASE_URL}/grasp_data/franka_panda/uuid_index.json"
DEFAULT_DOWNLOADER_URL = "https://raw.githubusercontent.com/NVlabs/GraspGen/main/scripts/download_objects.py"
NO_HOME_ENV_KEYS = (
    "HOME",
    "XDG_CACHE_HOME",
    "HF_HOME",
    "HUGGINGFACE_HUB_CACHE",
    "OBJAVERSE_HOME",
    "OBJAVERSE_CACHE_DIR",
    "TMPDIR",
    "PIP_CACHE_DIR",
    "TORCH_HOME",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
    except Exception:
        np = None

    if isinstance(value, Path):
        return str(value)
    if np is not None and isinstance(value, np.ndarray):
        return value.tolist()
    if np is not None and isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _download(url: str, path: Path, *, overwrite: bool = False) -> Path:
    path = path.expanduser().resolve()
    if path.is_file() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    print(f"[DOWNLOAD] {url} -> {path}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, tmp_path.open("wb") as f:
        shutil.copyfileobj(response, f)
    tmp_path.replace(path)
    return path


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _under_home(path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)
    return str(resolved) == "/home" or str(resolved).startswith("/home/")


def _assert_no_home_download_paths(output_dir: Path) -> None:
    if not _enabled(os.environ.get("DEXTRAH_ENFORCE_NO_HOME_DOWNLOADS")):
        return

    checks: list[tuple[str, Path]] = [
        ("output_dir", output_dir),
        ("Path.home", Path.home()),
        ("tempfile.gettempdir", Path(tempfile.gettempdir())),
    ]
    for key in NO_HOME_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            checks.append((key, Path(value)))

    bad: list[str] = []
    for label, path in checks:
        resolved = path.expanduser().resolve(strict=False)
        print(f"[NO_HOME_DOWNLOAD_CHECK] {label}={resolved}", flush=True)
        if _under_home(resolved):
            bad.append(f"{label}={resolved}")
    if bad:
        raise RuntimeError(
            "Refusing to prepare GraspGen assets with /home download/cache paths: "
            + ", ".join(bad)
        )


def _read_uuid_lines(path_or_url: str, cache_path: Path | None = None) -> list[str]:
    if path_or_url.startswith(("http://", "https://")):
        if cache_path is None:
            fd, name = tempfile.mkstemp(prefix="graspgen_split_", suffix=".txt")
            os.close(fd)
            cache_path = Path(name)
        path = _download(path_or_url, cache_path)
    else:
        path = Path(path_or_url).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"UUID list not found: {path}")
    uuids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return list(dict.fromkeys(uuids))


def _load_json(path_or_url: str, cache_path: Path | None = None) -> Any:
    if path_or_url.startswith(("http://", "https://")):
        if cache_path is None:
            fd, name = tempfile.mkstemp(prefix="graspgen_", suffix=".json")
            os.close(fd)
            cache_path = Path(name)
        path = _download(path_or_url, cache_path)
        return json.loads(path.read_text(encoding="utf-8"))
    path = Path(path_or_url).expanduser().resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def _select_uuids(
    split_uuids: list[str],
    grasp_index: dict[str, int],
    *,
    limit: int,
    explicit_uuids: list[str],
    prefer_single_shard: bool,
) -> list[str]:
    if explicit_uuids:
        missing = [uuid for uuid in explicit_uuids if uuid not in grasp_index]
        if missing:
            raise ValueError(f"{len(missing)} explicit UUIDs are missing from the Franka grasp index: {missing[:8]}")
        return explicit_uuids[:limit] if limit > 0 else explicit_uuids

    candidates = [uuid for uuid in split_uuids if uuid in grasp_index]
    if not candidates:
        raise ValueError("No split UUIDs are present in the Franka grasp index")
    if limit <= 0 or limit >= len(candidates):
        return candidates
    if not prefer_single_shard:
        return candidates[:limit]

    counts: dict[int, int] = {}
    for uuid in candidates:
        shard_id = int(grasp_index[uuid])
        counts[shard_id] = counts.get(shard_id, 0) + 1
    ordered_shards = sorted(counts, key=lambda shard: (-counts[shard], shard))
    selected: list[str] = []
    for shard_id in ordered_shards:
        for uuid in candidates:
            if int(grasp_index[uuid]) == shard_id and uuid not in selected:
                selected.append(uuid)
                if len(selected) >= limit:
                    return selected
    return selected


def _run_graspgen_downloader(
    *,
    downloader_path: Path,
    uuid_list_path: Path,
    output_dir: Path,
    simplify: bool,
    unused_cpu_count: int,
) -> None:
    cmd = [
        sys.executable,
        str(downloader_path),
        "--uuid_list",
        str(uuid_list_path),
        "--output_dir",
        str(output_dir),
        "--unused_cpu_count",
        str(unused_cpu_count),
    ]
    if simplify:
        cmd.append("--simplify")
    print("[OBJECT_DOWNLOAD]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def _load_object_mapping(raw_object_dir: Path, *, simplify: bool) -> dict[str, Path]:
    mapping_path = raw_object_dir / ("map_uuid_to_path_simplified.json" if simplify else "map_uuid_to_path.json")
    mapping: dict[str, Path] = {}
    if mapping_path.is_file():
        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        for uuid, rel_path in payload.items():
            base = raw_object_dir / ("simplified" if simplify else "")
            mapping[str(uuid)] = (base / str(rel_path)).resolve()

    fallback_exts = (".obj", ".OBJ")
    for obj_path in raw_object_dir.rglob("*"):
        if obj_path.suffix not in fallback_exts:
            continue
        for uuid in list(mapping.keys()):
            if uuid in obj_path.name and not mapping[uuid].is_file():
                mapping[uuid] = obj_path.resolve()
    return mapping


def _find_object_path(uuid: str, raw_object_dir: Path, mapping: dict[str, Path]) -> Path:
    mapped = mapping.get(uuid)
    if mapped is not None and mapped.is_file():
        return mapped
    matches = sorted(path for path in raw_object_dir.rglob(f"*{uuid}*.obj") if path.is_file())
    if len(matches) == 1:
        return matches[0].resolve()
    if len(matches) > 1:
        raise ValueError(f"Multiple OBJ files match UUID {uuid}: {matches}")
    raise FileNotFoundError(f"No downloaded OBJ found for UUID {uuid} under {raw_object_dir}")


def _parse_obj_bounds(path: Path) -> tuple[list[float], list[float]]:
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("v "):
                continue
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            xyz = [float(parts[1]), float(parts[2]), float(parts[3])]
            for axis in range(3):
                mins[axis] = min(mins[axis], xyz[axis])
                maxs[axis] = max(maxs[axis], xyz[axis])
            count += 1
    if count <= 0:
        raise ValueError(f"OBJ contains no vertices: {path}")
    return mins, maxs


def _copy_obj_dependencies(src_obj: Path, dst_dir: Path) -> None:
    copied = {src_obj.resolve()}
    mtl_files: list[Path] = []
    with src_obj.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("mtllib "):
                continue
            rel = line.strip().split(maxsplit=1)[1]
            mtl_path = (src_obj.parent / rel).resolve()
            if mtl_path.is_file() and mtl_path not in copied:
                shutil.copy2(mtl_path, dst_dir / mtl_path.name)
                copied.add(mtl_path)
                mtl_files.append(mtl_path)
    for mtl_path in mtl_files:
        with mtl_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 2 or not parts[0].lower().startswith("map_"):
                    continue
                texture_path = (mtl_path.parent / parts[-1]).resolve()
                if texture_path.is_file() and texture_path not in copied:
                    shutil.copy2(texture_path, dst_dir / texture_path.name)
                    copied.add(texture_path)


def _write_urdf(uuid: str, object_path: Path, urdf_dir: Path, *, overwrite: bool) -> tuple[Path, list[float], list[float]]:
    object_dir = urdf_dir / uuid
    object_dir.mkdir(parents=True, exist_ok=True)
    visual_path = object_dir / "visual_model.obj"
    collision_path = object_dir / "collision_model_vhacd.obj"
    if overwrite or not visual_path.is_file():
        shutil.copy2(object_path, visual_path)
    if overwrite or not collision_path.is_file():
        shutil.copy2(object_path, collision_path)
    _copy_obj_dependencies(object_path, object_dir)
    urdf_path = object_dir / "model.urdf"
    urdf = f"""<?xml version='1.0'?>
<robot name="object_{uuid}">
    <static>false</static>
    <link name="baseLink">
        <inertial>
            <mass value="0.1"/>
            <inertia ixx="1e-4" ixy="0." ixz="0." iyy="1e-4" iyz="0." izz="1e-4"/>
        </inertial>
        <collision name="collision">
            <geometry>
                <mesh filename="collision_model_vhacd.obj"/>
            </geometry>
        </collision>
        <visual name="visual">
            <geometry>
                <mesh filename="visual_model.obj"/>
            </geometry>
        </visual>
    </link>
</robot>
"""
    if overwrite or not urdf_path.is_file():
        urdf_path.write_text(urdf, encoding="utf-8")
    bounds_min, bounds_max = _parse_obj_bounds(object_path)
    return urdf_path, bounds_min, bounds_max


def _extract_payload(payload: dict[str, Any], uuid: str) -> dict[str, Any]:
    import numpy as np

    obj = payload.get("object", {})
    grasps = payload.get("grasps", {})
    transforms = np.asarray(grasps.get("transforms"), dtype=np.float32)
    if transforms.ndim != 3 or tuple(transforms.shape[1:]) != (4, 4):
        raise ValueError(f"{uuid}: expected grasps.transforms with shape (N, 4, 4), got {transforms.shape}")
    keep = np.ones((transforms.shape[0],), dtype=bool)
    object_in_gripper = grasps.get("object_in_gripper")
    if object_in_gripper is not None:
        object_in_gripper_arr = np.asarray(object_in_gripper, dtype=bool).reshape(-1)
        if object_in_gripper_arr.shape[0] == transforms.shape[0] and object_in_gripper_arr.any():
            keep = object_in_gripper_arr
    transforms = transforms[keep]
    if transforms.shape[0] == 0:
        raise ValueError(f"{uuid}: no valid grasp transforms after object_in_gripper filtering")

    confidence = np.ones((transforms.shape[0],), dtype=np.float32)
    contact_locations = None
    raw_contact_locations = grasps.get("contact_locations")
    grasp_width = None
    if raw_contact_locations is not None:
        contacts = np.asarray(raw_contact_locations, dtype=np.float32)
        if contacts.ndim == 3 and contacts.shape[0] == keep.shape[0] and contacts.shape[1] >= 2:
            contacts = contacts[keep]
            grasp_width = np.linalg.norm(contacts[:, 0, :] - contacts[:, 1, :], axis=-1).astype(np.float32)
            finite_width = np.isfinite(grasp_width)
            if finite_width.any():
                transforms = transforms[finite_width]
                confidence = confidence[finite_width]
                contacts = contacts[finite_width]
                grasp_width = grasp_width[finite_width]
                contact_locations = contacts
            else:
                grasp_width = None

    scale = float(obj["scale"])
    object_file = str(obj.get("file", ""))
    metadata = {
        "format": "dextrah_franka_multi_object_grasp_prior_v1",
        "source_dataset": "nvidia/PhysicalAI-Robotics-GraspGen",
        "source_gripper": "franka_panda",
        "object_uuid": uuid,
        "object_file": object_file,
        "object_scale": scale,
        "tool_frame": "panda_hand",
        "gripper_name": "franka_panda",
        "grasp_transform_name": "T_object_panda_hand",
        "grasp_to_tool_transform_name": "identity_dataset_panda_hand",
        "object_in_gripper_filter_kept": int(transforms.shape[0]),
        "object_in_gripper_filter_total": int(keep.shape[0]),
        "has_contact_locations": contact_locations is not None,
        "contact_location_count": 0 if contact_locations is None else int(contact_locations.shape[0]),
    }
    return {
        "scale": scale,
        "object_file": object_file,
        "grasps_object": transforms,
        "confidence": confidence,
        "contact_locations": contact_locations,
        "grasp_width": grasp_width,
        "grasp_to_tool_transform": np.eye(4, dtype=np.float32),
        "metadata": metadata,
    }


def _write_prior_npz(path: Path, uuid: str, extracted: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = extracted["metadata"]
    grasp_width = extracted["grasp_width"]
    contact_locations = extracted["contact_locations"]
    save_kwargs = {
        "grasps_object": np.asarray(extracted["grasps_object"], dtype=np.float32),
        "confidence": np.asarray(extracted["confidence"], dtype=np.float32),
        "grasp_to_tool_transform": np.asarray(extracted["grasp_to_tool_transform"], dtype=np.float32),
        "metadata_json": np.asarray(json.dumps(_jsonable(metadata), sort_keys=True)),
        "object_uuid": np.asarray(uuid),
        "object_scale": np.asarray(float(extracted["scale"]), dtype=np.float32),
        "tool_frame": np.asarray("panda_hand"),
        "gripper_name": np.asarray("franka_panda"),
    }
    if contact_locations is not None:
        save_kwargs["contact_locations"] = np.asarray(contact_locations, dtype=np.float32)
    if grasp_width is not None:
        save_kwargs["grasp_width"] = np.asarray(grasp_width, dtype=np.float32)
    np.savez_compressed(path, **save_kwargs)
    summary = {
        "path": str(path),
        "scale": float(extracted["scale"]),
        "num_grasps": int(save_kwargs["grasps_object"].shape[0]),
        "has_contact_locations": contact_locations is not None,
        "grasp_width_mean": None if grasp_width is None else float(np.mean(grasp_width)),
        "grasp_width_p95": None if grasp_width is None else float(np.percentile(grasp_width, 95)),
    }
    return summary


def _extract_grasp_priors(
    *,
    selected_uuids: list[str],
    grasp_index: dict[str, int],
    cache_dir: Path,
    prior_dir: Path,
    overwrite: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    target_by_shard: dict[int, set[str]] = {}
    for uuid in selected_uuids:
        target_by_shard.setdefault(int(grasp_index[uuid]), set()).add(uuid)

    summaries: dict[str, dict[str, Any]] = {}
    extracted_by_uuid: dict[str, dict[str, Any]] = {}
    for shard_id, shard_uuids in sorted(target_by_shard.items()):
        shard_path = _download(
            f"{HF_BASE_URL}/grasp_data/franka_panda/shard_{shard_id:03d}.tar",
            cache_dir / "grasp_data" / "franka_panda" / f"shard_{shard_id:03d}.tar",
        )
        remaining = set(shard_uuids)
        print(f"[GRASP_SHARD] shard={shard_id:03d} targets={len(remaining)}", flush=True)
        with tarfile.open(shard_path, "r") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                basename = Path(member.name).name
                if not basename.endswith(".grasps.json"):
                    continue
                uuid = basename[: -len(".grasps.json")]
                if uuid not in remaining:
                    continue
                file_obj = tar.extractfile(member)
                if file_obj is None:
                    continue
                payload = json.loads(file_obj.read().decode("utf-8"))
                extracted = _extract_payload(payload, uuid)
                prior_path = prior_dir / f"{uuid}.npz"
                if overwrite or not prior_path.is_file():
                    summaries[uuid] = _write_prior_npz(prior_path, uuid, extracted)
                else:
                    summaries[uuid] = {"path": str(prior_path), "scale": float(extracted["scale"]), "existing": True}
                extracted_by_uuid[uuid] = extracted
                remaining.remove(uuid)
                if not remaining:
                    break
        if remaining:
            raise FileNotFoundError(f"Shard {shard_id:03d} did not contain grasp JSON for: {sorted(remaining)[:8]}")
    return extracted_by_uuid, summaries


def _load_scale_from_prior(path: Path) -> float | None:
    if not path.is_file():
        return None
    try:
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            if "object_scale" in data.files:
                value = data["object_scale"]
                return float(value.item() if hasattr(value, "item") else value)
            if "metadata_json" in data.files:
                metadata = json.loads(str(data["metadata_json"].item()))
                if "object_scale" in metadata:
                    return float(metadata["object_scale"])
    except Exception:
        return None
    return None


def _write_manifest(
    output_dir: Path,
    objects: list[dict[str, Any]],
    selected_uuids: list[str],
    skipped_objects: list[dict[str, Any]],
    args,
) -> Path:
    manifest_path = output_dir / "manifest.json"
    payload = {
        "format": "dextrah_graspgen_object_manifest_v1",
        "asset_root": ".",
        "source_dataset": "nvidia/PhysicalAI-Robotics-GraspGen",
        "object_split_url": args.split_url,
        "object_split_gripper": "robotiq_2f_140",
        "grasp_prior_gripper": "franka_panda",
        "selected_uuid_count": len(selected_uuids),
        "skipped_object_count": len(skipped_objects),
        "skipped_objects": skipped_objects,
        "objects": objects,
        "conversion": {
            "urdf_dir": "urdf",
            "usd_dir": "USD",
            "command": "python dextrah_lab/assets/batch_convert_urdf.py "
            f"{output_dir / 'urdf'} {output_dir / 'USD'} --headless --manifest {manifest_path}",
        },
    }
    manifest_path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=_repo_root() / "dextrah_lab/assets/graspgen_objects")
    parser.add_argument("--split_url", type=str, default=DEFAULT_SPLIT_URL)
    parser.add_argument("--uuid_list", type=str, default=None, help="Local UUID text file; overrides --split_url.")
    parser.add_argument("--uuids", type=str, nargs="*", default=None, help="Explicit UUIDs to prepare.")
    parser.add_argument("--limit", type=int, default=16, help="Number of objects to prepare; <=0 means all.")
    parser.add_argument("--prefer_single_shard", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--grasp_index_url", type=str, default=DEFAULT_GRASP_INDEX_URL)
    parser.add_argument("--downloader_url", type=str, default=DEFAULT_DOWNLOADER_URL)
    parser.add_argument("--skip_object_download", action="store_true", default=False)
    parser.add_argument("--skip_grasp_extract", action="store_true", default=False)
    parser.add_argument("--simplify", action="store_true", default=False)
    parser.add_argument("--unused_cpu_count", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument(
        "--min_scaled_half_extent",
        type=float,
        default=1.0e-6,
        help="Skip objects whose GraspGen-scaled half extent is non-finite or not larger than this value.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    _assert_no_home_download_paths(output_dir)
    cache_dir = output_dir / "cache"
    raw_object_dir = output_dir / "raw_objaverse"
    urdf_dir = output_dir / "urdf"
    usd_dir = output_dir / "USD"
    prior_dir = output_dir / "grasp_priors"
    split_dir = output_dir / "splits"
    for path in (cache_dir, raw_object_dir, urdf_dir, usd_dir, prior_dir, split_dir):
        path.mkdir(parents=True, exist_ok=True)

    uuid_source = args.uuid_list or args.split_url
    split_uuids = _read_uuid_lines(uuid_source, cache_dir / "robotiq_2f_140_train.txt")
    grasp_index = _load_json(args.grasp_index_url, cache_dir / "franka_panda_uuid_index.json")
    selected_uuids = _select_uuids(
        split_uuids,
        {str(key): int(value) for key, value in grasp_index.items()},
        limit=int(args.limit),
        explicit_uuids=list(args.uuids or []),
        prefer_single_shard=bool(args.prefer_single_shard),
    )
    selected_uuid_path = split_dir / "selected_uuids.txt"
    selected_uuid_path.write_text("\n".join(selected_uuids) + "\n", encoding="utf-8")
    print(f"[UUIDS] selected={len(selected_uuids)} list={selected_uuid_path}", flush=True)

    if not args.skip_object_download:
        downloader_path = _download(args.downloader_url, cache_dir / "download_objects.py", overwrite=args.overwrite)
        _run_graspgen_downloader(
            downloader_path=downloader_path,
            uuid_list_path=selected_uuid_path,
            output_dir=raw_object_dir,
            simplify=bool(args.simplify),
            unused_cpu_count=int(args.unused_cpu_count),
        )

    extracted_by_uuid: dict[str, dict[str, Any]] = {}
    prior_summaries: dict[str, dict[str, Any]] = {}
    if not args.skip_grasp_extract:
        extracted_by_uuid, prior_summaries = _extract_grasp_priors(
            selected_uuids=selected_uuids,
            grasp_index={str(key): int(value) for key, value in grasp_index.items()},
            cache_dir=cache_dir,
            prior_dir=prior_dir,
            overwrite=bool(args.overwrite),
        )

    object_mapping = _load_object_mapping(raw_object_dir, simplify=bool(args.simplify))
    manifest_objects: list[dict[str, Any]] = []
    skipped_objects: list[dict[str, Any]] = []
    min_scaled_half_extent = float(args.min_scaled_half_extent)
    for uuid in selected_uuids:
        object_path = _find_object_path(uuid, raw_object_dir, object_mapping)
        urdf_path, bounds_min, bounds_max = _write_urdf(uuid, object_path, urdf_dir, overwrite=bool(args.overwrite))
        prior_path = prior_dir / f"{uuid}.npz"
        scale = None
        if uuid in extracted_by_uuid:
            scale = float(extracted_by_uuid[uuid]["scale"])
        if scale is None:
            scale = _load_scale_from_prior(prior_path)
        if scale is None:
            raise ValueError(f"Could not determine GraspGen object scale for {uuid}; run without --skip_grasp_extract")

        scaled_bounds_min = [float(scale) * value for value in bounds_min]
        scaled_bounds_max = [float(scale) * value for value in bounds_max]
        half_extents = [0.5 * (bounds_max[axis] - bounds_min[axis]) for axis in range(3)]
        scaled_half_extents = [float(scale) * value for value in half_extents]
        if (
            not math.isfinite(float(scale))
            or float(scale) <= 0.0
            or any(
                (not math.isfinite(float(value))) or float(value) <= min_scaled_half_extent
                for value in scaled_half_extents
            )
        ):
            skipped = {
                "uuid": uuid,
                "reason": "invalid_scaled_half_extents",
                "scale": float(scale),
                "bounds_min": bounds_min,
                "bounds_max": bounds_max,
                "scaled_half_extents": scaled_half_extents,
                "min_scaled_half_extent": min_scaled_half_extent,
                "raw_object_path": os.path.relpath(object_path, output_dir),
                "urdf_path": os.path.relpath(urdf_path, output_dir),
                "grasp_prior_path": os.path.relpath(prior_path, output_dir),
            }
            skipped_objects.append(skipped)
            print("DEXTRAH_GRASPGEN_ASSET_SKIPPED", json.dumps(_jsonable(skipped), sort_keys=True), flush=True)
            continue
        grasp_size = max(2.0 * max(scaled_half_extents), 0.02)
        manifest_objects.append(
            {
                "uuid": uuid,
                "scale": float(scale),
                "raw_object_path": os.path.relpath(object_path, output_dir),
                "urdf_path": os.path.relpath(urdf_path, output_dir),
                "usd_path": f"USD/{uuid}/{uuid}.usd",
                "grasp_prior_path": os.path.relpath(prior_path, output_dir),
                "bounds_min": bounds_min,
                "bounds_max": bounds_max,
                "scaled_bounds_min": scaled_bounds_min,
                "scaled_bounds_max": scaled_bounds_max,
                "half_extents": half_extents,
                "scaled_half_extents": scaled_half_extents,
                "grasp_size": grasp_size,
                "grasp_prior": prior_summaries.get(uuid, {"path": str(prior_path)}),
            }
        )

    manifest_path = _write_manifest(output_dir, manifest_objects, selected_uuids, skipped_objects, args)
    missing_usd = [item["usd_path"] for item in manifest_objects if not (output_dir / item["usd_path"]).is_file()]
    summary = {
        "manifest_path": str(manifest_path),
        "selected_uuid_path": str(selected_uuid_path),
        "raw_object_dir": str(raw_object_dir),
        "urdf_dir": str(urdf_dir),
        "usd_dir": str(usd_dir),
        "prior_dir": str(prior_dir),
        "num_objects": len(manifest_objects),
        "skipped_object_count": len(skipped_objects),
        "min_scaled_half_extent": min_scaled_half_extent,
        "missing_usd_count": len(missing_usd),
        "missing_usd_examples": missing_usd[:8],
    }
    print("DEXTRAH_GRASPGEN_ASSETS_PREPARED", json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
