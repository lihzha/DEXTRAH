"""Shared object-manifest and reset mechanics for robot-specific grasp envs."""

from __future__ import annotations

from collections.abc import Sequence
import json
import math
from pathlib import Path
import re
from typing import Any

import torch

import omni.usd
import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import RigidObject, RigidObjectCfg
from isaaclab.sim import schemas as sim_schemas
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.sim.utils import bind_physics_material, make_uninstanceable


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_repo_path(value: str | Path, *, base_dir: Path | None = None) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    if base_dir is not None:
        candidate = (base_dir / path).resolve()
        if candidate.exists():
            return candidate
    return (repo_root() / path).resolve()


def _safe_prim_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    if not token or token[0].isdigit():
        token = f"obj_{token}"
    return token


def _as_float_list(value: Any, length: int, default: Sequence[float]) -> list[float]:
    if value is None:
        return [float(v) for v in default]
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"Expected a list of {length} floats, got {value!r}")
    return [float(v) for v in value]


def _bounds_from_record(
    record: dict[str, object],
    *,
    scale: float,
    default_half_extents: Sequence[float],
) -> tuple[list[float], list[float]]:
    if record.get("scaled_bounds_min") is not None and record.get("scaled_bounds_max") is not None:
        return (
            _as_float_list(record.get("scaled_bounds_min"), 3, (-float(default_half_extents[0]),) * 3),
            _as_float_list(record.get("scaled_bounds_max"), 3, default_half_extents),
        )
    if record.get("bounds_min") is not None and record.get("bounds_max") is not None:
        bounds_min = _as_float_list(record.get("bounds_min"), 3, (-float(default_half_extents[0]),) * 3)
        bounds_max = _as_float_list(record.get("bounds_max"), 3, default_half_extents)
        return ([scale * v for v in bounds_min], [scale * v for v in bounds_max])
    if record.get("scaled_half_extents") is not None:
        half_extents = _as_float_list(record.get("scaled_half_extents"), 3, default_half_extents)
    elif record.get("half_extents") is not None:
        half_extents = [scale * v for v in _as_float_list(record.get("half_extents"), 3, default_half_extents)]
    else:
        half_extents = [float(v) for v in default_half_extents]
    return ([-v for v in half_extents], half_extents)


def _collect_record_text(value: object, fragments: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        fragments.append(value)
    elif isinstance(value, (int, float, bool)):
        fragments.append(str(value))
    elif isinstance(value, dict):
        for nested_value in value.values():
            _collect_record_text(nested_value, fragments)
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            _collect_record_text(nested_value, fragments)


def _record_metadata_text(record: dict[str, object], *, fallback: str) -> str:
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
        _collect_record_text(record.get(key), fragments)
    if not fragments:
        fragments.append(fallback)
    return " ".join(str(fragment) for fragment in fragments).lower()


def npz_scalar(value) -> object:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _yaw_quat_wxyz(yaw_rad: torch.Tensor) -> torch.Tensor:
    quat = torch.zeros(yaw_rad.shape[0], 4, device=yaw_rad.device)
    quat[:, 0] = torch.cos(0.5 * yaw_rad)
    quat[:, 3] = torch.sin(0.5 * yaw_rad)
    return quat


class MultiObjectGraspTaskMixin:
    """Mixin for envs that share the same GraspGen multi-object task."""

    def _load_asset_manifest(
        self,
        *,
        manifest_path_value: str,
        assets_dir_value: str,
        max_assets: int,
        require_scale: bool,
        default_half_extents: Sequence[float],
        default_grasp_size: float,
        default_scale: float,
        label: str,
    ) -> list[dict[str, object]]:
        manifest_path = str(manifest_path_value or "")
        object_assets_dir = resolve_repo_path(str(assets_dir_value), base_dir=repo_root())
        if not manifest_path:
            candidate = object_assets_dir / "manifest.json"
            manifest_path = str(candidate) if candidate.is_file() else ""

        assets: list[dict[str, object]] = []
        default_half_extents = tuple(float(v) for v in default_half_extents)
        if manifest_path:
            manifest = resolve_repo_path(manifest_path, base_dir=repo_root())
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            object_records = payload.get("objects")
            if not isinstance(object_records, list):
                raise ValueError(f"Expected manifest objects list in {manifest}")
            asset_root = payload.get("asset_root") or "."
            asset_root_path = resolve_repo_path(str(asset_root), base_dir=manifest.parent)
            for idx, record in enumerate(object_records):
                if not isinstance(record, dict):
                    raise ValueError(f"Object record {idx} in {manifest} is not a mapping")
                uuid = str(record.get("uuid") or record.get("name") or f"object_{idx}")
                usd_value = record.get("usd_path")
                if not usd_value:
                    raise ValueError(f"Object record {uuid} is missing usd_path")
                usd_path = resolve_repo_path(str(usd_value), base_dir=asset_root_path)
                if not usd_path.is_file():
                    raise FileNotFoundError(f"Missing USD asset for {uuid}: {usd_path}")
                scale = float(record.get("scale", default_scale))
                if bool(require_scale) and "scale" not in record:
                    raise ValueError(f"{label} record {uuid} does not include GraspGen object scale")
                bounds_min, bounds_max = _bounds_from_record(
                    record,
                    scale=scale,
                    default_half_extents=default_half_extents,
                )
                half_extents = [0.5 * (bounds_max[axis] - bounds_min[axis]) for axis in range(3)]
                center_offset = [0.5 * (bounds_max[axis] + bounds_min[axis]) for axis in range(3)]
                xy_radius = max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))
                grasp_prior_path = record.get("grasp_prior_path")
                resolved_prior = ""
                if grasp_prior_path:
                    resolved_prior = str(resolve_repo_path(str(grasp_prior_path), base_dir=asset_root_path))
                stable_pose_path = record.get("stable_pose_path")
                resolved_stable_pose = ""
                if stable_pose_path:
                    resolved_stable_pose = str(resolve_repo_path(str(stable_pose_path), base_dir=asset_root_path))
                raw_object_path = record.get("raw_object_path")
                resolved_raw_object = ""
                if raw_object_path:
                    resolved_raw_object = str(resolve_repo_path(str(raw_object_path), base_dir=asset_root_path))
                name = str(record.get("name") or record.get("title") or uuid)
                assets.append(
                    {
                        "uuid": uuid,
                        "name": name,
                        "metadata_text": _record_metadata_text(record, fallback=f"{name} {uuid}"),
                        "usd_path": str(usd_path),
                        "raw_object_path": resolved_raw_object,
                        "scale": scale,
                        "scaled_half_extents": half_extents,
                        "scaled_bounds_min": bounds_min,
                        "scaled_bounds_max": bounds_max,
                        "center_offset": center_offset,
                        "xy_radius": xy_radius,
                        "spawn_z_offset": -bounds_min[2],
                        "grasp_size": float(record.get("grasp_size", max(2.0 * max(half_extents), 0.02))),
                        "grasp_prior_path": resolved_prior,
                        "stable_pose_path": resolved_stable_pose,
                    }
                )
        else:
            usd_root = object_assets_dir / "USD"
            if not usd_root.is_dir():
                raise FileNotFoundError(
                    "Set env.object_asset_manifest_path or provide assets under "
                    f"{usd_root}"
                )
            for usd_path in sorted(usd_root.glob("*/*.usd")):
                uuid = usd_path.parent.name
                half_extents = list(default_half_extents)
                scale = float(default_scale)
                assets.append(
                    {
                        "uuid": uuid,
                        "name": uuid,
                        "metadata_text": uuid.lower(),
                        "usd_path": str(usd_path.resolve()),
                        "raw_object_path": "",
                        "scale": scale,
                        "scaled_half_extents": half_extents,
                        "scaled_bounds_min": [-v for v in half_extents],
                        "scaled_bounds_max": half_extents,
                        "center_offset": [0.0, 0.0, 0.0],
                        "xy_radius": max(half_extents[0], half_extents[1]),
                        "spawn_z_offset": half_extents[2],
                        "grasp_size": float(default_grasp_size),
                        "grasp_prior_path": "",
                        "stable_pose_path": "",
                    }
                )

        if max_assets > 0:
            assets = assets[: int(max_assets)]
        if not assets:
            raise ValueError(f"No {label} assets were found")
        return assets

    def _load_object_asset_manifest(self) -> list[dict[str, object]]:
        return self._load_asset_manifest(
            manifest_path_value=str(self.cfg.object_asset_manifest_path or ""),
            assets_dir_value=str(self.cfg.object_assets_dir),
            max_assets=int(self.cfg.max_objects),
            require_scale=bool(self.cfg.require_graspgen_scale),
            default_half_extents=tuple(float(v) for v in self.cfg.object_default_half_extents),
            default_grasp_size=float(self.cfg.object_default_grasp_size),
            default_scale=float(self.cfg.object_default_scale),
            label="multi-object",
        )

    def _setup_multi_object_task(self) -> None:
        self._object_assets = self._load_object_asset_manifest()
        self.num_unique_objects = len(self._object_assets)
        assignment = str(getattr(self.cfg, "object_asset_assignment", "round_robin")).lower()
        if assignment in ("round_robin", "round-robin", "cyclic"):
            self.object_asset_index = torch.remainder(
                torch.arange(self.num_envs, device=self.device),
                self.num_unique_objects,
            ).long()
        elif assignment in ("random", "uniform"):
            balanced_indices = torch.remainder(
                torch.arange(self.num_envs, device=self.device),
                self.num_unique_objects,
            ).long()
            self.object_asset_index = balanced_indices[torch.randperm(self.num_envs, device=self.device)]
        else:
            raise ValueError(
                "object_asset_assignment must be 'round_robin' or 'random', "
                f"got {self.cfg.object_asset_assignment!r}"
            )

        scale_by_asset = torch.tensor(
            [[float(asset["scale"])] for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        half_extents_by_asset = torch.tensor(
            [asset["scaled_half_extents"] for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        grasp_size_by_asset = torch.tensor(
            [float(asset["grasp_size"]) for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        bounds_min_by_asset = torch.tensor(
            [asset["scaled_bounds_min"] for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        bounds_max_by_asset = torch.tensor(
            [asset["scaled_bounds_max"] for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        center_offset_by_asset = torch.tensor(
            [asset["center_offset"] for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        xy_radius_by_asset = torch.tensor(
            [float(asset["xy_radius"]) for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        spawn_z_offset_by_asset = torch.tensor(
            [float(asset["spawn_z_offset"]) for asset in self._object_assets],
            dtype=torch.float32,
            device=self.device,
        )
        self.object_scale = scale_by_asset[self.object_asset_index]
        self.object_half_extents = half_extents_by_asset[self.object_asset_index]
        self.object_grasp_size = grasp_size_by_asset[self.object_asset_index]
        self.object_radius = torch.norm(self.object_half_extents, dim=-1)
        self.object_bounds_min = bounds_min_by_asset[self.object_asset_index]
        self.object_bounds_max = bounds_max_by_asset[self.object_asset_index]
        self.object_center_offset = center_offset_by_asset[self.object_asset_index]
        self.object_xy_radius = xy_radius_by_asset[self.object_asset_index]
        self.object_spawn_z_offset = spawn_z_offset_by_asset[self.object_asset_index]
        self.object_asset_id_fraction = self.object_asset_index.float() / max(float(self.num_unique_objects - 1), 1.0)
        self.object_has_grasp_prior = torch.zeros(self.num_envs, dtype=torch.float32, device=self.device)
        self._setup_stable_pose_resets()

    def _rank_tabletop_clutter_assets(self, assets: list[dict[str, object]]) -> list[dict[str, object]]:
        keywords = tuple(
            str(keyword).lower()
            for keyword in getattr(self.cfg, "tabletop_clutter_common_object_keywords", ())
            if str(keyword)
        )
        excluded_keywords = tuple(
            str(keyword).lower()
            for keyword in getattr(self.cfg, "tabletop_clutter_excluded_object_keywords", ())
            if str(keyword)
        )
        max_xy_radius = max(float(getattr(self.cfg, "tabletop_clutter_max_xy_radius", 0.0)), 0.0)

        def sort_key(asset: dict[str, object]) -> tuple[float, float, str]:
            text = str(asset.get("metadata_text") or asset.get("name") or asset.get("uuid") or "").lower()
            common_hits = sum(1 for keyword in keywords if keyword in text)
            excluded_hits = sum(1 for keyword in excluded_keywords if keyword in text)
            radius = float(asset["xy_radius"])
            bounds_min = asset["scaled_bounds_min"]
            bounds_max = asset["scaled_bounds_max"]
            height = (
                float(bounds_max[2]) - float(bounds_min[2])
                if isinstance(bounds_min, Sequence) and isinstance(bounds_max, Sequence)
                else 0.0
            )
            size_score = 0.0
            if max_xy_radius > 0.0:
                if radius <= max_xy_radius:
                    size_score += 10.0
                else:
                    size_score -= 80.0 * (radius - max_xy_radius)
            size_score -= 3.0 * abs(radius - 0.07)
            if height > 0.28:
                size_score -= 2.0 * (height - 0.28)
            score = 50.0 * common_hits - 75.0 * excluded_hits + size_score
            return (-score, radius, str(asset.get("uuid") or ""))

        return sorted(assets, key=sort_key)

    def _setup_tabletop_clutter_task(self) -> None:
        self.tabletop_clutter_object_count = max(int(getattr(self.cfg, "tabletop_clutter_object_count", 0)), 0)
        self._tabletop_clutter_enabled = bool(getattr(self.cfg, "tabletop_clutter_enabled", False)) and (
            self.tabletop_clutter_object_count > 0
        )
        self._tabletop_clutter_assets: list[dict[str, object]] = []
        self._tabletop_clutter_objects: list[RigidObject] = []
        self.tabletop_clutter_asset_index = torch.empty(
            (self.num_envs, 0),
            dtype=torch.long,
            device=self.device,
        )
        self.tabletop_clutter_initial_root_pos = torch.empty((self.num_envs, 0, 3), device=self.device)
        self.tabletop_clutter_initial_root_quat = torch.empty((self.num_envs, 0, 4), device=self.device)
        self.tabletop_clutter_placement_success = torch.empty((self.num_envs, 0), dtype=torch.bool, device=self.device)
        self.tabletop_clutter_placement_attempts = torch.empty((self.num_envs, 0), dtype=torch.long, device=self.device)
        self.tabletop_clutter_placement_min_clearance = torch.empty((self.num_envs,), device=self.device)
        if not self._tabletop_clutter_enabled:
            self.num_unique_tabletop_clutter_objects = 0
            return

        manifest_path = str(getattr(self.cfg, "tabletop_clutter_asset_manifest_path", "") or "")
        assets_dir = str(getattr(self.cfg, "tabletop_clutter_assets_dir", "") or "")
        if not manifest_path and not assets_dir:
            manifest_path = str(self.cfg.object_asset_manifest_path or "")
            assets_dir = str(self.cfg.object_assets_dir)
        max_assets = int(getattr(self.cfg, "tabletop_clutter_max_objects", 0))
        if max_assets <= 0:
            max_assets = int(getattr(self.cfg, "max_objects", 0))
        prioritize_common = bool(getattr(self.cfg, "tabletop_clutter_prioritize_common_objects", False))
        self._tabletop_clutter_assets = self._load_asset_manifest(
            manifest_path_value=manifest_path,
            assets_dir_value=assets_dir,
            max_assets=0 if prioritize_common else max_assets,
            require_scale=bool(getattr(self.cfg, "tabletop_clutter_require_graspgen_scale", False)),
            default_half_extents=tuple(float(v) for v in self.cfg.object_default_half_extents),
            default_grasp_size=float(self.cfg.object_default_grasp_size),
            default_scale=float(self.cfg.object_default_scale),
            label="tabletop clutter",
        )
        if prioritize_common:
            self._tabletop_clutter_assets = self._rank_tabletop_clutter_assets(self._tabletop_clutter_assets)
            if max_assets > 0:
                self._tabletop_clutter_assets = self._tabletop_clutter_assets[:max_assets]
            if not self._tabletop_clutter_assets:
                raise ValueError("No tabletop clutter assets were available after prioritization")
        self.num_unique_tabletop_clutter_objects = len(self._tabletop_clutter_assets)
        assignment = str(getattr(self.cfg, "tabletop_clutter_asset_assignment", "random")).lower()
        total_slots = self.num_envs * self.tabletop_clutter_object_count
        if assignment in ("round_robin", "round-robin", "cyclic"):
            index_flat = torch.remainder(
                torch.arange(total_slots, device=self.device),
                self.num_unique_tabletop_clutter_objects,
            ).long()
        elif assignment in ("random", "uniform"):
            index_flat = torch.randint(
                self.num_unique_tabletop_clutter_objects,
                (total_slots,),
                dtype=torch.long,
                device=self.device,
            )
        else:
            raise ValueError(
                "tabletop_clutter_asset_assignment must be 'round_robin' or 'random', "
                f"got {self.cfg.tabletop_clutter_asset_assignment!r}"
            )
        self.tabletop_clutter_asset_index = index_flat.view(self.num_envs, self.tabletop_clutter_object_count)
        xy_radius_by_asset = torch.tensor(
            [float(asset["xy_radius"]) for asset in self._tabletop_clutter_assets],
            dtype=torch.float32,
            device=self.device,
        )
        spawn_z_offset_by_asset = torch.tensor(
            [float(asset["spawn_z_offset"]) for asset in self._tabletop_clutter_assets],
            dtype=torch.float32,
            device=self.device,
        )
        self.tabletop_clutter_xy_radius = xy_radius_by_asset[self.tabletop_clutter_asset_index]
        self.tabletop_clutter_spawn_z_offset = spawn_z_offset_by_asset[self.tabletop_clutter_asset_index]
        denom = max(float(self.num_unique_tabletop_clutter_objects - 1), 1.0)
        self.tabletop_clutter_asset_id_fraction = self.tabletop_clutter_asset_index.float() / denom
        self.tabletop_clutter_initial_root_pos = torch.zeros(
            (self.num_envs, self.tabletop_clutter_object_count, 3),
            dtype=torch.float32,
            device=self.device,
        )
        self.tabletop_clutter_initial_root_quat = torch.zeros(
            (self.num_envs, self.tabletop_clutter_object_count, 4),
            dtype=torch.float32,
            device=self.device,
        )
        self.tabletop_clutter_initial_root_quat[:, :, 0] = 1.0
        self.tabletop_clutter_placement_success = torch.ones(
            (self.num_envs, self.tabletop_clutter_object_count),
            dtype=torch.bool,
            device=self.device,
        )
        self.tabletop_clutter_placement_attempts = torch.zeros(
            (self.num_envs, self.tabletop_clutter_object_count),
            dtype=torch.long,
            device=self.device,
        )
        self.tabletop_clutter_placement_min_clearance = torch.full(
            (self.num_envs,),
            float("inf"),
            dtype=torch.float32,
            device=self.device,
        )

    def _spawn_usd_rigid_object(self, prim_path: str, asset: dict[str, object]) -> None:
        scale = float(asset["scale"])
        object_cfg = RigidObjectCfg(
            prim_path=prim_path,
            spawn=sim_utils.UsdFileCfg(
                usd_path=str(asset["usd_path"]),
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=False,
                    disable_gravity=False,
                    linear_damping=float(self.cfg.object_linear_damping),
                    angular_damping=float(self.cfg.object_angular_damping),
                    enable_gyroscopic_forces=True,
                    solver_position_iteration_count=int(self.cfg.object_solver_position_iterations),
                    solver_velocity_iteration_count=int(self.cfg.object_solver_velocity_iterations),
                    sleep_threshold=float(self.cfg.object_sleep_threshold),
                    stabilization_threshold=float(self.cfg.object_stabilization_threshold),
                    max_linear_velocity=1000.0,
                    max_angular_velocity=1000.0,
                    max_depenetration_velocity=float(self.cfg.object_max_depenetration_velocity),
                ),
                mass_props=sim_utils.MassPropertiesCfg(density=float(self.cfg.object_density)),
                scale=(scale, scale, scale),
            ),
            init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, -10.0), rot=(1.0, 0.0, 0.0, 0.0)),
        )
        RigidObject(object_cfg)
        make_uninstanceable(prim_path)
        sim_schemas.modify_collision_properties(
            prim_path,
            sim_utils.CollisionPropertiesCfg(
                collision_enabled=True,
                contact_offset=float(self.cfg.object_contact_offset),
                rest_offset=float(self.cfg.object_rest_offset),
            ),
        )
        object_material_cfg = RigidBodyMaterialCfg(
            static_friction=float(self.cfg.object_static_friction),
            dynamic_friction=float(self.cfg.object_dynamic_friction),
            restitution=float(self.cfg.object_restitution),
            friction_combine_mode="max",
            restitution_combine_mode="min",
        )
        object_material_path = f"{prim_path}/physicsMaterial"
        object_material_cfg.func(object_material_path, object_material_cfg)
        bind_physics_material(prim_path, object_material_path)

    def _disable_base_link_articulation(self, prim_path: str) -> None:
        stage = omni.usd.get_context().get_stage()
        base_link_path = f"{prim_path}/baseLink"
        prim = stage.GetPrimAtPath(base_link_path)
        if prim.IsValid() and prim.HasAttribute("physxArticulation:articulationEnabled"):
            prim.GetAttribute("physxArticulation:articulationEnabled").Set(False)

    def _spawn_multi_object_assets(self) -> None:
        for env_id in range(self.num_envs):
            asset = self._object_assets[int(self.object_asset_index[env_id].item())]
            uuid = str(asset["uuid"])
            object_prim_name = f"object_{env_id}_{_safe_prim_token(uuid)}"
            prim_path = f"/World/envs/env_{env_id}/object/{object_prim_name}"
            self._spawn_usd_rigid_object(prim_path, asset)

        self._cube = RigidObject(RigidObjectCfg(prim_path="/World/envs/env_.*/object/.*", spawn=None))
        self.scene.rigid_objects["cube"] = self._cube
        self.scene.rigid_objects["object"] = self._cube

        for env_id in range(self.num_envs):
            asset = self._object_assets[int(self.object_asset_index[env_id].item())]
            object_prim_name = f"object_{env_id}_{_safe_prim_token(str(asset['uuid']))}"
            self._disable_base_link_articulation(f"/World/envs/env_{env_id}/object/{object_prim_name}")

    def _spawn_tabletop_clutter_assets(self) -> None:
        self._tabletop_clutter_objects = []
        if not getattr(self, "_tabletop_clutter_enabled", False):
            return

        for slot_idx in range(self.tabletop_clutter_object_count):
            for env_id in range(self.num_envs):
                asset = self._tabletop_clutter_assets[int(self.tabletop_clutter_asset_index[env_id, slot_idx].item())]
                uuid = str(asset["uuid"])
                prim_name = f"slot_{slot_idx:02d}_{env_id}_{_safe_prim_token(uuid)}"
                prim_path = f"/World/envs/env_{env_id}/tabletop_clutter/{prim_name}"
                self._spawn_usd_rigid_object(prim_path, asset)
                self._disable_base_link_articulation(prim_path)

            clutter_object = RigidObject(
                RigidObjectCfg(
                    prim_path=f"/World/envs/env_.*/tabletop_clutter/slot_{slot_idx:02d}_.*",
                    spawn=None,
                )
            )
            self._tabletop_clutter_objects.append(clutter_object)
            self.scene.rigid_objects[f"tabletop_clutter_{slot_idx:02d}"] = clutter_object

    def _setup_stable_pose_resets(self) -> None:
        self._object_stable_pose_enabled = bool(self.cfg.object_stable_pose_enabled)
        self._object_stable_poses: dict[int, dict[str, torch.Tensor | str]] = {}
        if not self._object_stable_pose_enabled:
            return

        cache_dir = str(self.cfg.object_stable_pose_cache_dir or "")
        for object_idx, asset in enumerate(self._object_assets):
            stable_pose_path = str(asset.get("stable_pose_path") or "")
            if not stable_pose_path and cache_dir:
                stable_pose_path = str(resolve_repo_path(Path(cache_dir) / f"{asset['uuid']}.npz", base_dir=repo_root()))
            if not stable_pose_path:
                if bool(self.cfg.object_stable_pose_allow_missing):
                    continue
                raise FileNotFoundError(f"Missing stable-pose cache path for object {asset['uuid']}")
            path = Path(stable_pose_path).expanduser()
            if not path.is_file():
                if bool(self.cfg.object_stable_pose_allow_missing):
                    continue
                raise FileNotFoundError(f"Missing stable-pose cache for object {asset['uuid']}: {path}")
            self._object_stable_poses[object_idx] = self._load_stable_pose_cache(path, uuid=str(asset["uuid"]))

    def _load_stable_pose_cache(self, path: Path, *, uuid: str) -> dict[str, torch.Tensor | str]:
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            if "rotations" in data.files and "root_z_offsets" in data.files:
                rotations = np.asarray(data["rotations"], dtype=np.float32)
                root_z_offsets = np.asarray(data["root_z_offsets"], dtype=np.float32).reshape(-1)
                transforms = None
            elif "transforms" in data.files:
                transforms = np.asarray(data["transforms"], dtype=np.float32)
                rotations = transforms[:, :3, :3]
                root_z_offsets = None
            else:
                raise ValueError(
                    f"Stable-pose cache for {uuid} is missing rotations/root_z_offsets or transforms: {path}"
                )
            probabilities = (
                np.asarray(data["probabilities"], dtype=np.float32).reshape(-1)
                if "probabilities" in data.files
                else np.ones((rotations.shape[0],), dtype=np.float32)
            )
            vertices = np.asarray(data["vertices"], dtype=np.float32) if "vertices" in data.files else None

        if rotations.ndim != 3 or tuple(rotations.shape[1:]) != (3, 3) or rotations.shape[0] == 0:
            raise ValueError(f"Stable-pose rotations must have shape (N, 3, 3), got {rotations.shape}: {path}")
        pose_count = min(max(int(self.cfg.object_stable_pose_count), 1), rotations.shape[0])
        rotations = rotations[:pose_count]
        probabilities = probabilities[:pose_count]
        if root_z_offsets is not None:
            root_z_offsets = root_z_offsets[:pose_count]
        elif vertices is not None and vertices.ndim == 2 and vertices.shape[1] == 3 and vertices.shape[0] > 0:
            rotated = np.einsum("nij,kj->nki", rotations, vertices)
            root_z_offsets = -rotated[:, :, 2].min(axis=1)
        else:
            root_z_offsets = transforms[:, 2, 3]
        return {
            "rotations": torch.as_tensor(rotations, dtype=torch.float32, device=self.device).contiguous(),
            "probabilities": torch.as_tensor(probabilities, dtype=torch.float32, device=self.device).contiguous(),
            "root_z_offsets": torch.as_tensor(root_z_offsets, dtype=torch.float32, device=self.device).contiguous(),
            "path": str(path),
        }

    def _sample_object_reset_pose(self, env_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        num_ids = int(env_ids.numel())
        yaw_randomization = math.radians(float(self.cfg.object_spawn_yaw_randomization_deg))
        if yaw_randomization > 0.0:
            yaw = yaw_randomization * (2.0 * torch.rand(num_ids, device=self.device) - 1.0)
            yaw_quat = _yaw_quat_wxyz(yaw)
        else:
            yaw_quat = torch.zeros(num_ids, 4, device=self.device)
            yaw_quat[:, 0] = 1.0

        if not getattr(self, "_object_stable_pose_enabled", False):
            return yaw_quat, self.object_spawn_z_offset[env_ids]

        object_indices = self.object_asset_index[env_ids]
        reset_rot = torch.empty((num_ids, 3, 3), dtype=torch.float32, device=self.device)
        root_z_offsets = torch.empty((num_ids,), dtype=torch.float32, device=self.device)
        for object_idx_tensor in torch.unique(object_indices):
            object_idx = int(object_idx_tensor.item())
            stable = self._object_stable_poses.get(object_idx)
            mask = object_indices == object_idx
            count = int(mask.sum().item())
            if stable is None:
                if bool(self.cfg.object_stable_pose_allow_missing):
                    reset_rot[mask] = math_utils.matrix_from_quat(yaw_quat[mask])
                    root_z_offsets[mask] = self.object_spawn_z_offset[env_ids[mask]]
                    continue
                raise RuntimeError(
                    f"Stable-pose reset requested for object without cache: {self._object_assets[object_idx]['uuid']}"
                )
            rotations = stable["rotations"]
            offsets = stable["root_z_offsets"]
            if not isinstance(rotations, torch.Tensor) or not isinstance(offsets, torch.Tensor):
                raise RuntimeError("Internal stable-pose cache tensor is invalid")
            if bool(self.cfg.object_stable_pose_randomize) and rotations.shape[0] > 1:
                ranks = torch.randint(rotations.shape[0], (count,), device=self.device)
            else:
                ranks = torch.zeros((count,), dtype=torch.long, device=self.device)
            reset_rot[mask] = rotations[ranks]
            root_z_offsets[mask] = offsets[ranks]

        yaw_rot = math_utils.matrix_from_quat(yaw_quat)
        object_quat = math_utils.quat_from_matrix(torch.bmm(yaw_rot, reset_rot))
        object_quat = object_quat / torch.clamp(torch.norm(object_quat, dim=-1, keepdim=True), min=1.0e-6)
        return object_quat, root_z_offsets

    def _sample_tabletop_clutter_quat(self, num_ids: int) -> torch.Tensor:
        yaw_randomization = math.radians(float(getattr(self.cfg, "tabletop_clutter_spawn_yaw_randomization_deg", 0.0)))
        if yaw_randomization > 0.0:
            yaw = yaw_randomization * (2.0 * torch.rand(num_ids, device=self.device) - 1.0)
            return _yaw_quat_wxyz(yaw)
        quat = torch.zeros(num_ids, 4, device=self.device)
        quat[:, 0] = 1.0
        return quat

    def _sample_tabletop_clutter_xy(self, env_ids: torch.Tensor, slot_idx: int) -> torch.Tensor:
        num_ids = int(env_ids.numel())
        xy_radius = self.tabletop_clutter_xy_radius[env_ids, slot_idx]
        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.table_center_x) + float(
            getattr(self.cfg, "tabletop_clutter_spawn_center_offset_x", 0.0)
        )
        spawn_xy[:, 1] = float(self.cfg.table_center_y) + float(
            getattr(self.cfg, "tabletop_clutter_spawn_center_offset_y", 0.0)
        )
        spawn_xy += float(getattr(self.cfg, "tabletop_clutter_spawn_xy_randomization", 0.0)) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x) + xy_radius
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x) - xy_radius
        min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y) + xy_radius
        max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y) - xy_radius
        spawn_xy[:, 0] = torch.minimum(torch.maximum(spawn_xy[:, 0], min_x), max_x)
        spawn_xy[:, 1] = torch.minimum(torch.maximum(spawn_xy[:, 1], min_y), max_y)
        return spawn_xy

    def _tabletop_clutter_xy_bounds(self, radius: float) -> tuple[float, float, float, float]:
        table_min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x) + radius
        table_max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x) - radius
        table_min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y) + radius
        table_max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y) - radius
        center_x = float(self.cfg.table_center_x) + float(
            getattr(self.cfg, "tabletop_clutter_spawn_center_offset_x", 0.0)
        )
        center_y = float(self.cfg.table_center_y) + float(
            getattr(self.cfg, "tabletop_clutter_spawn_center_offset_y", 0.0)
        )
        spawn_range = max(float(getattr(self.cfg, "tabletop_clutter_spawn_xy_randomization", 0.0)), 0.0)
        if spawn_range > 0.0:
            min_x = max(table_min_x, center_x - spawn_range)
            max_x = min(table_max_x, center_x + spawn_range)
            min_y = max(table_min_y, center_y - spawn_range)
            max_y = min(table_max_y, center_y + spawn_range)
        else:
            min_x, max_x, min_y, max_y = table_min_x, table_max_x, table_min_y, table_max_y
        if min_x > max_x:
            if table_min_x <= table_max_x:
                midpoint = max(min(center_x, table_max_x), table_min_x)
            else:
                midpoint = 0.5 * (table_min_x + table_max_x)
            min_x = max_x = midpoint
        if min_y > max_y:
            if table_min_y <= table_max_y:
                midpoint = max(min(center_y, table_max_y), table_min_y)
            else:
                midpoint = 0.5 * (table_min_y + table_max_y)
            min_y = max_y = midpoint
        return min_x, max_x, min_y, max_y

    def _tabletop_clearance(
        self,
        xy: tuple[float, float],
        radius: float,
        placed: list[tuple[tuple[float, float], float]],
    ) -> float:
        if not placed:
            return float("inf")
        return min(
            math.hypot(xy[0] - placed_xy[0], xy[1] - placed_xy[1]) - radius - placed_radius
            for placed_xy, placed_radius in placed
        )

    def _grid_tabletop_candidates(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        *,
        env_id: int,
        slot_idx: int,
    ) -> list[tuple[float, float]]:
        resolution = max(int(getattr(self.cfg, "tabletop_clutter_placement_grid_resolution", 21)), 2)
        xs = torch.linspace(min_x, max_x, resolution, device=self.device).detach().cpu().tolist()
        ys = torch.linspace(min_y, max_y, resolution, device=self.device).detach().cpu().tolist()
        center_x = 0.5 * (min_x + max_x)
        center_y = 0.5 * (min_y + max_y)
        offset = (env_id * 17 + slot_idx * 31) % max(resolution * resolution, 1)
        candidates = [(float(x), float(y)) for y in ys for x in xs]
        candidates.sort(key=lambda xy: abs(xy[0] - center_x) + abs(xy[1] - center_y))
        if candidates:
            offset = offset % len(candidates)
            candidates = candidates[offset:] + candidates[:offset]
        return candidates

    def _sample_tabletop_clutter_xy_non_overlapping(
        self,
        env_ids: torch.Tensor,
        target_root_pos: torch.Tensor | None,
    ) -> torch.Tensor:
        num_ids = int(env_ids.numel())
        positions = torch.zeros(num_ids, self.tabletop_clutter_object_count, 2, device=self.device)
        success = torch.ones(num_ids, self.tabletop_clutter_object_count, dtype=torch.bool, device=self.device)
        attempts_out = torch.zeros(num_ids, self.tabletop_clutter_object_count, dtype=torch.long, device=self.device)
        min_clearance_out = torch.full((num_ids,), float("inf"), dtype=torch.float32, device=self.device)
        padding = max(float(getattr(self.cfg, "tabletop_clutter_placement_padding", 0.0)), 0.0)
        max_attempts = max(int(getattr(self.cfg, "tabletop_clutter_placement_attempts", 128)), 1)
        random_values = torch.rand(
            (num_ids, self.tabletop_clutter_object_count, max_attempts, 2),
            device=self.device,
        )
        if target_root_pos is None and bool(
            getattr(self.cfg, "tabletop_clutter_include_target_object_in_placement", True)
        ):
            target_root_pos = self._cube.data.root_pos_w[env_ids] - self.scene.env_origins[env_ids]
        env_id_list = [int(env_id) for env_id in env_ids.detach().cpu().tolist()]
        for row_idx, env_id in enumerate(env_id_list):
            placed: list[tuple[tuple[float, float], float]] = []
            if target_root_pos is not None and bool(
                getattr(self.cfg, "tabletop_clutter_include_target_object_in_placement", True)
            ):
                target_xy = (
                    float(target_root_pos[row_idx, 0].detach().cpu().item()),
                    float(target_root_pos[row_idx, 1].detach().cpu().item()),
                )
                placed.append((target_xy, float(self.object_xy_radius[env_id].detach().cpu().item())))
            env_min_clearance = float("inf")
            for slot_idx in range(self.tabletop_clutter_object_count):
                radius = float(self.tabletop_clutter_xy_radius[env_id, slot_idx].detach().cpu().item())
                min_x, max_x, min_y, max_y = self._tabletop_clutter_xy_bounds(radius)
                chosen_xy: tuple[float, float] | None = None
                chosen_attempts = 0
                best_xy = (0.5 * (min_x + max_x), 0.5 * (min_y + max_y))
                best_clearance = -float("inf")
                for attempt_idx in range(max_attempts):
                    sample = random_values[row_idx, slot_idx, attempt_idx]
                    candidate_xy = (
                        min_x + (max_x - min_x) * float(sample[0].detach().cpu().item()),
                        min_y + (max_y - min_y) * float(sample[1].detach().cpu().item()),
                    )
                    clearance = self._tabletop_clearance(candidate_xy, radius, placed)
                    if clearance > best_clearance:
                        best_xy = candidate_xy
                        best_clearance = clearance
                    if clearance >= padding:
                        chosen_xy = candidate_xy
                        chosen_attempts = attempt_idx + 1
                        break
                if chosen_xy is None:
                    for candidate_idx, candidate_xy in enumerate(
                        self._grid_tabletop_candidates(
                            min_x,
                            max_x,
                            min_y,
                            max_y,
                            env_id=env_id,
                            slot_idx=slot_idx,
                        )
                    ):
                        clearance = self._tabletop_clearance(candidate_xy, radius, placed)
                        if clearance > best_clearance:
                            best_xy = candidate_xy
                            best_clearance = clearance
                        if clearance >= padding:
                            chosen_xy = candidate_xy
                            chosen_attempts = max_attempts + candidate_idx + 1
                            break
                if chosen_xy is None:
                    chosen_xy = best_xy
                    chosen_attempts = max_attempts
                    success[row_idx, slot_idx] = False
                final_clearance = self._tabletop_clearance(chosen_xy, radius, placed)
                if math.isfinite(final_clearance):
                    env_min_clearance = min(env_min_clearance, final_clearance)
                positions[row_idx, slot_idx, 0] = chosen_xy[0]
                positions[row_idx, slot_idx, 1] = chosen_xy[1]
                attempts_out[row_idx, slot_idx] = chosen_attempts
                placed.append((chosen_xy, radius))
            min_clearance_out[row_idx] = env_min_clearance if math.isfinite(env_min_clearance) else float("inf")

        self.tabletop_clutter_placement_success[env_ids] = success
        self.tabletop_clutter_placement_attempts[env_ids] = attempts_out
        self.tabletop_clutter_placement_min_clearance[env_ids] = min_clearance_out
        return positions

    def _reset_tabletop_clutter(self, env_ids: torch.Tensor, target_root_pos: torch.Tensor | None = None) -> None:
        if not getattr(self, "_tabletop_clutter_enabled", False):
            return
        num_ids = int(env_ids.numel())
        if num_ids <= 0:
            return
        z_jitter_range = max(float(getattr(self.cfg, "tabletop_clutter_spawn_z_jitter", 0.0)), 0.0)
        non_overlapping = bool(getattr(self.cfg, "tabletop_clutter_non_overlapping", False))
        clutter_xy = (
            self._sample_tabletop_clutter_xy_non_overlapping(env_ids, target_root_pos)
            if non_overlapping
            else None
        )
        for slot_idx, clutter_object in enumerate(self._tabletop_clutter_objects):
            object_pos = torch.zeros(num_ids, 3, device=self.device)
            if clutter_xy is not None:
                object_pos[:, 0:2] = clutter_xy[:, slot_idx, :]
            else:
                object_pos[:, 0:2] = self._sample_tabletop_clutter_xy(env_ids, slot_idx)
                self.tabletop_clutter_placement_success[env_ids, slot_idx] = True
                self.tabletop_clutter_placement_attempts[env_ids, slot_idx] = 1
                self.tabletop_clutter_placement_min_clearance[env_ids] = float("nan")
            z_jitter = z_jitter_range * torch.rand(num_ids, device=self.device)
            object_pos[:, 2] = (
                float(self.cfg.table_surface_z)
                + self.tabletop_clutter_spawn_z_offset[env_ids, slot_idx]
                + float(getattr(self.cfg, "tabletop_clutter_spawn_z_clearance", 0.0))
                + z_jitter
            )
            object_quat = self._sample_tabletop_clutter_quat(num_ids)
            object_state = torch.zeros(num_ids, 13, device=self.device)
            object_state[:, 0:3] = object_pos + self.scene.env_origins[env_ids]
            object_state[:, 3:7] = object_quat
            clutter_object.write_root_state_to_sim(object_state, env_ids=env_ids)
            self.tabletop_clutter_initial_root_pos[env_ids, slot_idx] = object_pos
            self.tabletop_clutter_initial_root_quat[env_ids, slot_idx] = object_quat

    def _zero_tabletop_clutter_velocity(self, env_ids: torch.Tensor) -> None:
        if not getattr(self, "_tabletop_clutter_enabled", False):
            return
        zero_vel = torch.zeros((int(env_ids.numel()), 6), dtype=torch.float32, device=self.device)
        for clutter_object in self._tabletop_clutter_objects:
            clutter_object.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)

    def _object_center_pos_from_root(
        self,
        env_ids: torch.Tensor,
        root_pos: torch.Tensor,
        root_quat: torch.Tensor,
    ) -> torch.Tensor:
        center_offset = self.object_center_offset[env_ids]
        rot_m = math_utils.matrix_from_quat(root_quat)
        return root_pos + torch.bmm(rot_m, center_offset.unsqueeze(-1)).squeeze(-1)

    def _settle_reset_objects(
        self,
        env_ids: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        settle_steps = max(int(self.cfg.object_reset_settle_steps), 0)
        if settle_steps <= 0:
            root_pos = self._cube.data.root_pos_w[env_ids] - self.scene.env_origins[env_ids]
            root_quat = self._cube.data.root_quat_w[env_ids]
            return root_pos, root_quat

        if bool(self.cfg.object_reset_settle_full_reset_only) and int(env_ids.numel()) != int(self.num_envs):
            raise RuntimeError(
                "object_reset_settle_steps > 0 is only safe for full-env resets. "
                "Partial RL resets need precomputed stable poses instead of in-reset simulation stepping."
            )

        sync_reset = getattr(self, "_sync_reset_joint_state", None)
        if callable(sync_reset):
            sync_reset(env_ids, joint_pos, joint_vel, update_buffers=True)
        else:
            self._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
            self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
            if hasattr(self, "robot_dof_targets"):
                self.robot_dof_targets[env_ids] = joint_pos
            self.scene.write_data_to_sim()
            self.sim.forward()
            self.scene.update(dt=0.0)
        for _ in range(settle_steps):
            self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
            self.scene.write_data_to_sim()
            self.sim.step(render=False)
            self.scene.update(dt=self.sim.cfg.dt)

        if bool(self.cfg.object_reset_zero_velocity_after_settle):
            zero_vel = torch.zeros((int(env_ids.numel()), 6), dtype=torch.float32, device=self.device)
            self._cube.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
            self._zero_tabletop_clutter_velocity(env_ids)
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

        root_pos = self._cube.data.root_pos_w[env_ids] - self.scene.env_origins[env_ids]
        root_quat = self._cube.data.root_quat_w[env_ids]
        return root_pos, root_quat

    def _multi_object_features(self) -> torch.Tensor:
        return torch.cat(
            (
                self.object_scale,
                self.object_half_extents,
                self.object_grasp_size.unsqueeze(-1),
                self.object_asset_id_fraction.unsqueeze(-1),
                self.object_has_grasp_prior.unsqueeze(-1),
                self.object_radius.unsqueeze(-1),
            ),
            dim=-1,
        )

    def _add_multi_object_log_terms(self, log_terms: dict[str, torch.Tensor], *, distance_term: torch.Tensor) -> None:
        num_objects = int(getattr(self, "num_unique_objects", 0))
        if num_objects <= 0 or num_objects > 16:
            return
        for object_idx in range(num_objects):
            object_mask_bool = self.object_asset_index == object_idx
            object_mask = object_mask_bool.float()
            denom = torch.clamp(object_mask.sum(), min=1.0)
            prefix = f"object_{object_idx}"
            log_terms[f"{prefix}_env_fraction"] = object_mask.mean()
            log_terms[f"{prefix}_success_rate"] = (self.in_success_region.float() * object_mask).sum() / denom
            log_terms[f"{prefix}_has_lifted_rate"] = (self.has_lifted_cube.float() * object_mask).sum() / denom
            log_terms[f"{prefix}_lift_height"] = (self.cube_lift_height * object_mask).sum() / denom
            log_terms[f"{prefix}_xy_error"] = (self.cube_xy_error * object_mask).sum() / denom
            log_terms[f"{prefix}_distance"] = (distance_term * object_mask).sum() / denom

    def multi_object_asset_summary(self) -> dict[str, object]:
        return {
            "num_unique_objects": self.num_unique_objects,
            "object_asset_assignment": str(getattr(self.cfg, "object_asset_assignment", "round_robin")),
            "object_asset_index_by_env": [int(v) for v in self.object_asset_index.detach().cpu().tolist()],
            "uuids": [str(asset["uuid"]) for asset in self._object_assets],
            "scales": [float(asset["scale"]) for asset in self._object_assets],
            "usd_paths": [str(asset["usd_path"]) for asset in self._object_assets],
            "grasp_prior_paths": [str(asset.get("grasp_prior_path") or "") for asset in self._object_assets],
        }

    def tabletop_clutter_summary(self) -> dict[str, object]:
        if not getattr(self, "_tabletop_clutter_enabled", False):
            return {
                "enabled": False,
                "object_count": 0,
                "num_unique_objects": 0,
            }
        asset_indices = self.tabletop_clutter_asset_index.detach().cpu().tolist()
        return {
            "enabled": True,
            "object_count": int(self.tabletop_clutter_object_count),
            "num_unique_objects": int(self.num_unique_tabletop_clutter_objects),
            "asset_assignment": str(getattr(self.cfg, "tabletop_clutter_asset_assignment", "random")),
            "asset_index_by_env_slot": [[int(v) for v in row] for row in asset_indices],
            "uuids": [str(asset["uuid"]) for asset in self._tabletop_clutter_assets],
            "names": [str(asset.get("name") or asset["uuid"]) for asset in self._tabletop_clutter_assets],
            "usd_paths": [str(asset["usd_path"]) for asset in self._tabletop_clutter_assets],
            "spawn_xy_randomization": float(getattr(self.cfg, "tabletop_clutter_spawn_xy_randomization", 0.0)),
            "spawn_yaw_randomization_deg": float(
                getattr(self.cfg, "tabletop_clutter_spawn_yaw_randomization_deg", 0.0)
            ),
            "spawn_z_jitter": float(getattr(self.cfg, "tabletop_clutter_spawn_z_jitter", 0.0)),
            "non_overlapping": bool(getattr(self.cfg, "tabletop_clutter_non_overlapping", False)),
            "placement_padding": float(getattr(self.cfg, "tabletop_clutter_placement_padding", 0.0)),
            "placement_success_by_env_slot": [
                [bool(v) for v in row]
                for row in self.tabletop_clutter_placement_success.detach().cpu().tolist()
            ],
            "placement_attempts_by_env_slot": [
                [int(v) for v in row]
                for row in self.tabletop_clutter_placement_attempts.detach().cpu().tolist()
            ],
            "placement_min_clearance_by_env": [
                float(v) for v in self.tabletop_clutter_placement_min_clearance.detach().cpu().tolist()
            ],
            "prioritize_common_objects": bool(
                getattr(self.cfg, "tabletop_clutter_prioritize_common_objects", False)
            ),
            "max_xy_radius": float(getattr(self.cfg, "tabletop_clutter_max_xy_radius", 0.0)),
        }
