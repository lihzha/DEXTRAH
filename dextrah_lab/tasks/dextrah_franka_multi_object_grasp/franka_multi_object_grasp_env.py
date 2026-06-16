"""DirectRLEnv for Franka GraspGen multi-object pick-up."""

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
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.sensors import TiledCamera
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg
from isaaclab.sim.utils import bind_physics_material, make_uninstanceable
from isaaclab.sim import schemas as sim_schemas

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env import (
    DextrahFrankaCubeGraspEnv,
    _yaw_quat_wxyz,
)
from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env import (
    DextrahFrankaStarKittingEnv,
)

from .franka_multi_object_grasp_env_cfg import (
    DextrahFrankaMultiObjectGraspEnvCfg,
    DextrahFrankaMultiObjectRgbGraspEnvCfg,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _safe_prim_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    if not token or token[0].isdigit():
        token = f"obj_{token}"
    return token


def _resolve_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    return (_repo_root() / path).resolve()


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
        half_extents = [
            scale * v for v in _as_float_list(record.get("half_extents"), 3, default_half_extents)
        ]
    else:
        half_extents = [float(v) for v in default_half_extents]
    return ([-v for v in half_extents], half_extents)


def _npz_scalar(value) -> object:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class DextrahFrankaMultiObjectGraspEnv(DextrahFrankaCubeGraspEnv):
    """Franka task: pick up one of many GraspGen object assets per vectorized env."""

    cfg: DextrahFrankaMultiObjectGraspEnvCfg

    def _load_object_asset_manifest(self) -> list[dict[str, object]]:
        manifest_path = str(self.cfg.object_asset_manifest_path or "")
        object_assets_dir = _resolve_path(str(self.cfg.object_assets_dir), base_dir=_repo_root())
        if not manifest_path:
            candidate = object_assets_dir / "manifest.json"
            manifest_path = str(candidate) if candidate.is_file() else ""

        assets: list[dict[str, object]] = []
        default_half_extents = tuple(float(v) for v in self.cfg.object_default_half_extents)
        if manifest_path:
            manifest = _resolve_path(manifest_path, base_dir=_repo_root())
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            object_records = payload.get("objects")
            if not isinstance(object_records, list):
                raise ValueError(f"Expected manifest objects list in {manifest}")
            asset_root = payload.get("asset_root") or "."
            asset_root_path = _resolve_path(str(asset_root), base_dir=manifest.parent)
            for idx, record in enumerate(object_records):
                if not isinstance(record, dict):
                    raise ValueError(f"Object record {idx} in {manifest} is not a mapping")
                uuid = str(record.get("uuid") or record.get("name") or f"object_{idx}")
                usd_value = record.get("usd_path")
                if not usd_value:
                    raise ValueError(f"Object record {uuid} is missing usd_path")
                usd_path = _resolve_path(str(usd_value), base_dir=asset_root_path)
                if not usd_path.is_file():
                    raise FileNotFoundError(f"Missing USD asset for {uuid}: {usd_path}")
                scale = float(record.get("scale", self.cfg.object_default_scale))
                if bool(self.cfg.require_graspgen_scale) and "scale" not in record:
                    raise ValueError(f"Object record {uuid} does not include GraspGen object scale")
                bounds_min, bounds_max = _bounds_from_record(
                    record,
                    scale=scale,
                    default_half_extents=default_half_extents,
                )
                half_extents = [0.5 * (bounds_max[axis] - bounds_min[axis]) for axis in range(3)]
                center_offset = [0.5 * (bounds_max[axis] + bounds_min[axis]) for axis in range(3)]
                xy_radius = max(
                    abs(bounds_min[0]),
                    abs(bounds_max[0]),
                    abs(bounds_min[1]),
                    abs(bounds_max[1]),
                )
                grasp_prior_path = record.get("grasp_prior_path")
                resolved_prior = ""
                if grasp_prior_path:
                    resolved_prior = str(_resolve_path(str(grasp_prior_path), base_dir=asset_root_path))
                stable_pose_path = record.get("stable_pose_path")
                resolved_stable_pose = ""
                if stable_pose_path:
                    resolved_stable_pose = str(_resolve_path(str(stable_pose_path), base_dir=asset_root_path))
                raw_object_path = record.get("raw_object_path")
                resolved_raw_object = ""
                if raw_object_path:
                    resolved_raw_object = str(_resolve_path(str(raw_object_path), base_dir=asset_root_path))
                assets.append(
                    {
                        "uuid": uuid,
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
                scale = float(self.cfg.object_default_scale)
                assets.append(
                    {
                        "uuid": uuid,
                        "usd_path": str(usd_path.resolve()),
                        "raw_object_path": "",
                        "scale": scale,
                        "scaled_half_extents": half_extents,
                        "scaled_bounds_min": [-v for v in half_extents],
                        "scaled_bounds_max": half_extents,
                        "center_offset": [0.0, 0.0, 0.0],
                        "xy_radius": max(half_extents[0], half_extents[1]),
                        "spawn_z_offset": half_extents[2],
                        "grasp_size": float(self.cfg.object_default_grasp_size),
                        "grasp_prior_path": "",
                        "stable_pose_path": "",
                    }
                )

        max_objects = int(self.cfg.max_objects)
        if max_objects > 0:
            assets = assets[:max_objects]
        if not assets:
            raise ValueError("No multi-object GraspGen assets were found")
        return assets

    def _setup_scene(self):
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
        self.object_scale = scale_by_asset[self.object_asset_index]
        self.object_half_extents = half_extents_by_asset[self.object_asset_index]
        self.object_grasp_size = grasp_size_by_asset[self.object_asset_index]
        self.object_radius = torch.norm(self.object_half_extents, dim=-1)
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
        self.object_bounds_min = bounds_min_by_asset[self.object_asset_index]
        self.object_bounds_max = bounds_max_by_asset[self.object_asset_index]
        self.object_center_offset = center_offset_by_asset[self.object_asset_index]
        self.object_xy_radius = xy_radius_by_asset[self.object_asset_index]
        self.object_spawn_z_offset = spawn_z_offset_by_asset[self.object_asset_index]
        self.object_asset_id_fraction = self.object_asset_index.float() / max(float(self.num_unique_objects - 1), 1.0)
        self.object_has_grasp_prior = torch.zeros(self.num_envs, dtype=torch.float32, device=self.device)
        self._setup_stable_pose_resets()

        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        spawn_ground_plane(prim_path="/World/ground", cfg=GroundPlaneCfg())

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table

        for env_id in range(self.num_envs):
            asset = self._object_assets[int(self.object_asset_index[env_id].item())]
            uuid = str(asset["uuid"])
            object_prim_name = f"object_{env_id}_{_safe_prim_token(uuid)}"
            prim_path = f"/World/envs/env_{env_id}/object/{object_prim_name}"
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

        self._cube = RigidObject(RigidObjectCfg(prim_path="/World/envs/env_.*/object/.*", spawn=None))
        self.scene.rigid_objects["cube"] = self._cube
        self.scene.rigid_objects["object"] = self._cube

        stage = omni.usd.get_context().get_stage()
        for env_id in range(self.num_envs):
            asset = self._object_assets[int(self.object_asset_index[env_id].item())]
            object_prim_name = f"object_{env_id}_{_safe_prim_token(str(asset['uuid']))}"
            base_link_path = f"/World/envs/env_{env_id}/object/{object_prim_name}/baseLink"
            prim = stage.GetPrimAtPath(base_link_path)
            if prim.IsValid() and prim.HasAttribute("physxArticulation:articulationEnabled"):
                prim.GetAttribute("physxArticulation:articulationEnabled").Set(False)

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)
        if bool(getattr(self.cfg, "enable_rgb_observations", False)):
            self._tiled_camera = TiledCamera(self.cfg.tiled_camera)
            self.scene.sensors["tiled_camera"] = self._tiled_camera

    def _setup_stable_pose_resets(self) -> None:
        self._object_stable_pose_enabled = bool(self.cfg.object_stable_pose_enabled)
        self._object_stable_poses: dict[int, dict[str, torch.Tensor | str]] = {}
        if not self._object_stable_pose_enabled:
            return

        cache_dir = str(self.cfg.object_stable_pose_cache_dir or "")
        for object_idx, asset in enumerate(self._object_assets):
            stable_pose_path = str(asset.get("stable_pose_path") or "")
            if not stable_pose_path and cache_dir:
                stable_pose_path = str(_resolve_path(Path(cache_dir) / f"{asset['uuid']}.npz", base_dir=_repo_root()))
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

    def _setup_grasp_prior_reset(self) -> None:
        self._grasp_prior_reset_enabled = bool(self.cfg.grasp_prior_reset_enabled)
        self._grasp_prior_grasps_object = None
        self._grasp_prior_confidence = None
        self._grasp_prior_grasp_to_tool = torch.eye(4, device=self.device)
        self._grasp_prior_metadata = {}
        self._object_grasp_priors: dict[int, dict[str, object]] = {}
        if not self._grasp_prior_reset_enabled:
            return

        prior_dir = str(self.cfg.grasp_prior_library_dir or "")
        verified_indices_by_uuid = self._load_verified_grasp_indices(
            str(getattr(self.cfg, "grasp_prior_verified_indices_path", "") or "")
        )
        for object_idx, asset in enumerate(self._object_assets):
            prior_path = str(asset.get("grasp_prior_path") or "")
            if not prior_path and prior_dir:
                prior_path = str(_resolve_path(Path(prior_dir) / f"{asset['uuid']}.npz", base_dir=_repo_root()))
            if not prior_path:
                if bool(self.cfg.grasp_prior_allow_missing):
                    continue
                raise FileNotFoundError(f"Missing grasp prior path for object {asset['uuid']}")
            path = Path(prior_path).expanduser()
            if not path.is_file():
                if bool(self.cfg.grasp_prior_allow_missing):
                    continue
                raise FileNotFoundError(f"Missing grasp prior library for object {asset['uuid']}: {path}")
            uuid = str(asset["uuid"])
            prior = self._load_multi_object_prior(path, uuid=uuid)
            verified_indices = verified_indices_by_uuid.get(uuid)
            if verified_indices_by_uuid and verified_indices is None:
                raise ValueError(
                    f"Verified grasp cache {self.cfg.grasp_prior_verified_indices_path!r} "
                    f"has no indices for loaded object {uuid}"
                )
            if verified_indices is not None:
                grasps = prior["grasps_object"]
                if not isinstance(grasps, torch.Tensor):
                    raise RuntimeError("Internal grasp prior tensor is invalid")
                verified_tensor = torch.as_tensor(verified_indices, dtype=torch.long, device=self.device)
                verified_tensor = torch.unique(verified_tensor[(verified_tensor >= 0) & (verified_tensor < grasps.shape[0])])
                if verified_tensor.numel() == 0:
                    raise ValueError(
                        f"Verified grasp cache contains no valid indices for object {uuid} in {path}"
                    )
                prior["verified_indices"] = verified_tensor.contiguous()
                metadata = prior.get("metadata")
                if isinstance(metadata, dict):
                    metadata["verified_indices_count"] = int(verified_tensor.numel())
                    metadata["verified_indices_path"] = str(getattr(self.cfg, "grasp_prior_verified_indices_path", ""))
            self._object_grasp_priors[object_idx] = prior

        has_prior_by_asset = torch.tensor(
            [1.0 if idx in self._object_grasp_priors else 0.0 for idx in range(self.num_unique_objects)],
            dtype=torch.float32,
            device=self.device,
        )
        self.object_has_grasp_prior[:] = has_prior_by_asset[self.object_asset_index]

    def _load_verified_grasp_indices(self, path_value: str) -> dict[str, list[int]]:
        if not path_value:
            return {}
        path = _resolve_path(path_value, base_dir=_repo_root())
        if not path.is_file():
            raise FileNotFoundError(f"Missing verified grasp index cache: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_objects = payload.get("indices_by_uuid", payload.get("objects", payload)) if isinstance(payload, dict) else {}
        if not isinstance(raw_objects, dict):
            raise ValueError(f"Verified grasp index cache must contain an object mapping: {path}")

        verified: dict[str, list[int]] = {}
        for uuid, entry in raw_objects.items():
            indices = entry.get("indices") if isinstance(entry, dict) else entry
            if indices is None:
                continue
            if not isinstance(indices, list):
                raise ValueError(f"Verified indices for {uuid} must be a list in {path}")
            parsed = sorted({int(value) for value in indices if int(value) >= 0})
            if parsed:
                verified[str(uuid)] = parsed
        return verified

    def _load_multi_object_prior(self, path: Path, *, uuid: str) -> dict[str, object]:
        import numpy as np

        metadata: dict[str, object] = {}
        if path.suffix.lower() == ".npz":
            with np.load(path, allow_pickle=False) as data:
                if "metadata_json" in data.files:
                    metadata = json.loads(str(_npz_scalar(data["metadata_json"])))
                for key in ("object_uuid", "gripper_name", "tool_frame", "object_scale"):
                    if key in data.files:
                        metadata.setdefault(key, _npz_scalar(data[key]))
                grasps_object = data["grasps_object"]
                confidence = data["confidence"] if "confidence" in data.files else None
                contact_locations = data["contact_locations"] if "contact_locations" in data.files else None
                grasp_width = data["grasp_width"] if "grasp_width" in data.files else None
                grasp_to_tool = (
                    data["grasp_to_tool_transform"]
                    if "grasp_to_tool_transform" in data.files
                    else np.eye(4, dtype=np.float32)
                )
        elif path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = dict(payload.get("metadata", {}))
            grasps_object = payload["grasps_object"]
            confidence = payload.get("confidence")
            contact_locations = payload.get("contact_locations")
            grasp_width = payload.get("grasp_width")
            grasp_to_tool = payload.get("grasp_to_tool_transform", np.eye(4, dtype=np.float32))
        else:
            raise ValueError(f"Unsupported grasp prior extension for {path}; expected .npz or .json")

        grasps_tensor = torch.as_tensor(grasps_object, dtype=torch.float32, device=self.device)
        if grasps_tensor.ndim != 3 or tuple(grasps_tensor.shape[1:]) != (4, 4) or grasps_tensor.shape[0] == 0:
            raise ValueError(f"grasps_object must have shape (N, 4, 4), got {tuple(grasps_tensor.shape)}")
        expected_bottom = torch.tensor((0.0, 0.0, 0.0, 1.0), device=self.device)
        if not torch.allclose(grasps_tensor[:, 3, :], expected_bottom.expand_as(grasps_tensor[:, 3, :]), atol=1.0e-4):
            raise ValueError(f"grasps_object transforms must have homogeneous bottom rows: {path}")

        grasp_to_tool_tensor = torch.as_tensor(grasp_to_tool, dtype=torch.float32, device=self.device)
        if tuple(grasp_to_tool_tensor.shape) != (4, 4):
            raise ValueError(
                f"grasp_to_tool_transform must have shape (4, 4), got {tuple(grasp_to_tool_tensor.shape)}"
            )
        tool_frame = str(metadata.get("tool_frame", "panda_hand"))
        if tool_frame != "panda_hand":
            raise ValueError(f"Expected tool_frame='panda_hand' for Franka reset prior {uuid}, got {tool_frame!r}")
        if confidence is None:
            confidence_tensor = torch.ones(grasps_tensor.shape[0], dtype=torch.float32, device=self.device)
        else:
            confidence_tensor = torch.as_tensor(confidence, dtype=torch.float32, device=self.device).flatten()
            if confidence_tensor.shape[0] != grasps_tensor.shape[0]:
                raise ValueError("confidence length must match grasps_object count")
        grasp_width_tensor = None
        if grasp_width is not None:
            grasp_width_tensor = torch.as_tensor(grasp_width, dtype=torch.float32, device=self.device).flatten()
            if grasp_width_tensor.shape[0] != grasps_tensor.shape[0]:
                raise ValueError("grasp_width length must match grasps_object count")
        contact_locations_tensor = None
        if contact_locations is not None:
            contact_locations_tensor = torch.as_tensor(contact_locations, dtype=torch.float32, device=self.device)
            if contact_locations_tensor.ndim != 3 or contact_locations_tensor.shape[0] != grasps_tensor.shape[0]:
                raise ValueError("contact_locations must have shape (N, C, 3) and match grasps_object count")
            if contact_locations_tensor.shape[1] < 2 or contact_locations_tensor.shape[2] != 3:
                raise ValueError(
                    f"contact_locations must have shape (N, C>=2, 3), got {tuple(contact_locations_tensor.shape)}"
                )
        return {
            "grasps_object": grasps_tensor.contiguous(),
            "confidence": confidence_tensor.contiguous(),
            "contact_locations": None
            if contact_locations_tensor is None
            else contact_locations_tensor[:, :2, :].contiguous(),
            "grasp_width": None if grasp_width_tensor is None else grasp_width_tensor.contiguous(),
            "grasp_to_tool": grasp_to_tool_tensor.contiguous(),
            "metadata": metadata,
            "path": str(path),
        }

    def _compose_grasp_prior_targets(
        self,
        env_ids: torch.Tensor,
        cube_pos: torch.Tensor,
        cube_quat: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        num_ids = int(env_ids.numel())
        candidate_count = max(int(self.cfg.grasp_prior_reset_candidate_count), 1)
        candidate_sample_indices = torch.full(
            (num_ids, candidate_count),
            -1,
            dtype=torch.long,
            device=self.device,
        )
        object_grasp_t = torch.eye(4, device=self.device).repeat(num_ids, candidate_count, 1, 1)
        grasp_to_tool_t = torch.eye(4, device=self.device).repeat(num_ids, candidate_count, 1, 1)
        candidate_confidence = torch.ones((num_ids, candidate_count), dtype=torch.float32, device=self.device)
        candidate_required_width = self.object_grasp_size[env_ids].unsqueeze(1).expand(-1, candidate_count).clone()
        candidate_contact_locations = torch.zeros(
            (num_ids, candidate_count, 2, 3),
            dtype=torch.float32,
            device=self.device,
        )
        candidate_has_contact = torch.zeros((num_ids, candidate_count), dtype=torch.bool, device=self.device)
        object_indices = self.object_asset_index[env_ids]
        for object_idx_tensor in torch.unique(object_indices):
            object_idx = int(object_idx_tensor.item())
            prior = self._object_grasp_priors.get(object_idx)
            mask = object_indices == object_idx
            count = int(mask.sum().item())
            if prior is None:
                raise RuntimeError(f"Grasp prior reset requested for object without prior: {self._object_assets[object_idx]['uuid']}")
            grasps = prior["grasps_object"]
            if not isinstance(grasps, torch.Tensor):
                raise RuntimeError("Internal grasp prior tensor is invalid")
            verified_indices = prior.get("verified_indices")
            if isinstance(verified_indices, torch.Tensor) and verified_indices.numel() > 0:
                verified_choice = torch.randint(verified_indices.shape[0], (count, candidate_count), device=self.device)
                local_indices = verified_indices[verified_choice]
            else:
                local_indices = torch.randint(grasps.shape[0], (count, candidate_count), device=self.device)
            object_grasp_t[mask] = grasps[local_indices]
            candidate_sample_indices[mask] = local_indices
            confidence = prior["confidence"]
            if isinstance(confidence, torch.Tensor):
                candidate_confidence[mask] = confidence[local_indices]
            grasp_width = prior.get("grasp_width")
            if isinstance(grasp_width, torch.Tensor):
                sampled_width = grasp_width[local_indices]
                candidate_required_width[mask] = self._sanitize_grasp_prior_width(
                    sampled_width,
                    candidate_required_width[mask],
                )
            contact_locations = prior.get("contact_locations")
            if isinstance(contact_locations, torch.Tensor):
                sampled_contacts = contact_locations[local_indices]
                finite_contacts = torch.isfinite(sampled_contacts).all(dim=(-1, -2))
                candidate_contact_locations[mask] = sampled_contacts
                candidate_has_contact[mask] = finite_contacts
                sampled_contact_width = torch.norm(sampled_contacts[:, :, 0, :] - sampled_contacts[:, :, 1, :], dim=-1)
                candidate_required_width[mask] = torch.where(
                    finite_contacts & torch.isfinite(sampled_contact_width),
                    sampled_contact_width,
                    candidate_required_width[mask],
                )
            grasp_to_tool = prior["grasp_to_tool"]
            if not isinstance(grasp_to_tool, torch.Tensor):
                raise RuntimeError("Internal grasp-to-tool tensor is invalid")
            grasp_to_tool_t[mask] = grasp_to_tool.view(1, 1, 4, 4).expand(count, candidate_count, -1, -1)

        world_object_t = torch.eye(4, device=self.device).repeat(num_ids, 1, 1)
        object_root_pos_w = cube_pos + self.scene.env_origins[env_ids]
        object_center_pos = self._object_center_pos_from_root(env_ids, cube_pos, cube_quat)
        object_center_pos_w = object_center_pos + self.scene.env_origins[env_ids]
        world_object_t[:, :3, :3] = math_utils.matrix_from_quat(cube_quat)
        world_object_t[:, :3, 3] = object_root_pos_w
        flat_world_object_t = world_object_t.unsqueeze(1).expand(-1, candidate_count, -1, -1).reshape(-1, 4, 4)
        flat_object_grasp_t = object_grasp_t.reshape(-1, 4, 4)
        flat_grasp_to_tool_t = grasp_to_tool_t.reshape(-1, 4, 4)
        world_grasp_t = torch.bmm(flat_world_object_t, flat_object_grasp_t)
        world_tool_candidates = torch.bmm(world_grasp_t, flat_grasp_to_tool_t).reshape(
            num_ids,
            candidate_count,
            4,
            4,
        )
        flat_contact_locations = candidate_contact_locations.reshape(-1, 2, 3)
        flat_contact_points_w = torch.bmm(
            flat_world_object_t[:, :3, :3],
            flat_contact_locations.transpose(1, 2),
        ).transpose(1, 2)
        flat_contact_points_w = flat_contact_points_w + flat_world_object_t[:, None, :3, 3]
        candidate_contact_points_w = flat_contact_points_w.reshape(num_ids, candidate_count, 2, 3)
        candidate_contact_midpoint_w = candidate_contact_points_w.mean(dim=2)

        object_center_pos_w_candidates = object_center_pos_w.unsqueeze(1)
        object_center_offset_candidates = self.object_center_offset[env_ids].unsqueeze(1).expand(
            -1,
            candidate_count,
            -1,
        )
        candidate_contact_midpoint_o = candidate_contact_locations.mean(dim=2)
        candidate_contact_reference_o = torch.where(
            candidate_has_contact.unsqueeze(-1),
            candidate_contact_midpoint_o,
            object_center_offset_candidates,
        )
        candidate_contact_reference_w = torch.where(
            candidate_has_contact.unsqueeze(-1),
            candidate_contact_midpoint_w,
            object_center_pos_w_candidates,
        )
        candidate_exact_tool_pos_w = world_tool_candidates[:, :, :3, 3]
        candidate_tool_rot_w = world_tool_candidates[:, :, :3, :3]
        flat_candidate_tool_pos_w = candidate_exact_tool_pos_w.reshape(-1, 3)
        flat_candidate_tool_quat_w = math_utils.quat_from_matrix(candidate_tool_rot_w.reshape(-1, 3, 3))
        flat_ee_offset_pos = self.ee_offset_pos[env_ids].unsqueeze(1).expand(-1, candidate_count, -1).reshape(-1, 3)
        flat_ee_offset_rot = self.ee_offset_rot[env_ids].unsqueeze(1).expand(-1, candidate_count, -1).reshape(-1, 4)
        flat_raw_exact_ee_pos_w, flat_exact_ee_quat_w = math_utils.combine_frame_transforms(
            flat_candidate_tool_pos_w,
            flat_candidate_tool_quat_w,
            flat_ee_offset_pos,
            flat_ee_offset_rot,
        )
        candidate_raw_exact_ee_pos_w = flat_raw_exact_ee_pos_w.reshape(num_ids, candidate_count, 3)
        candidate_exact_ee_quat_w = flat_exact_ee_quat_w.reshape(num_ids, candidate_count, 4)
        candidate_exact_ee_rot_w = math_utils.matrix_from_quat(flat_exact_ee_quat_w).reshape(
            num_ids,
            candidate_count,
            3,
            3,
        )
        left_finger_offset_ee, right_finger_offset_ee = self._finger_offsets_from_ee(env_ids)
        # Contact locations are selection/quality references.  The reset pose
        # itself must remain the raw GraspGen panda_hand pose plus the DEXTRAH
        # EE/TCP offset; placing finger-link origins at contact points pushes
        # top-down grasps below the table.
        candidate_exact_ee_pos_w = candidate_raw_exact_ee_pos_w
        candidate_tool_z_axis_w = world_tool_candidates[:, :, :3, 2]
        candidate_tool_z_axis_w = candidate_tool_z_axis_w / torch.clamp(
            torch.norm(candidate_tool_z_axis_w, dim=-1, keepdim=True),
            min=1.0e-6,
        )
        pregrasp_offset = abs(float(self.cfg.grasp_prior_pregrasp_offset))
        plus_tool_pos_w = candidate_exact_tool_pos_w + pregrasp_offset * candidate_tool_z_axis_w
        minus_tool_pos_w = candidate_exact_tool_pos_w - pregrasp_offset * candidate_tool_z_axis_w
        candidate_exact_tool_dist = torch.norm(candidate_exact_tool_pos_w - object_center_pos_w_candidates, dim=-1)
        candidate_exact_ee_dist = torch.norm(candidate_exact_ee_pos_w - candidate_contact_reference_w, dim=-1)
        candidate_exact_reference_dist = torch.where(
            candidate_has_contact,
            candidate_exact_ee_dist,
            candidate_exact_tool_dist,
        )
        plus_tool_dist = torch.norm(plus_tool_pos_w - candidate_contact_reference_w, dim=-1)
        minus_tool_dist = torch.norm(minus_tool_pos_w - candidate_contact_reference_w, dim=-1)
        use_plus = plus_tool_dist >= minus_tool_dist
        if pregrasp_offset > 1.0e-6:
            plus_farther = plus_tool_dist > candidate_exact_reference_dist
            minus_farther = minus_tool_dist > candidate_exact_reference_dist
            has_farther = plus_farther | minus_farther
            plus_score = torch.where(plus_farther, plus_tool_pos_w[:, :, 2], plus_tool_pos_w[:, :, 2] - 10.0)
            minus_score = torch.where(minus_farther, minus_tool_pos_w[:, :, 2], minus_tool_pos_w[:, :, 2] - 10.0)
            use_plus = torch.where(has_farther, plus_score >= minus_score, use_plus)
        if bool(getattr(self.cfg, "grasp_prior_reset_require_downward_tool_z", False)):
            # GraspGen/Franka tool +Z is the approach axis. For tabletop top-side resets,
            # pregrasp must move opposite that axis, away from the object and table.
            use_plus = torch.zeros_like(use_plus)
        candidate_pregrasp_offset_dir_w = torch.where(
            use_plus.unsqueeze(-1),
            candidate_tool_z_axis_w,
            -candidate_tool_z_axis_w,
        )
        candidate_pregrasp_tool_pos_w = (
            candidate_exact_tool_pos_w + pregrasp_offset * candidate_pregrasp_offset_dir_w
        )
        candidate_pregrasp_ee_pos_w = (
            candidate_exact_ee_pos_w + pregrasp_offset * candidate_pregrasp_offset_dir_w
        )
        left_finger_offset_w = torch.einsum(
            "ncij,nj->nci",
            candidate_exact_ee_rot_w,
            left_finger_offset_ee,
        )
        right_finger_offset_w = torch.einsum(
            "ncij,nj->nci",
            candidate_exact_ee_rot_w,
            right_finger_offset_ee,
        )
        finger_half_axis_ee = 0.5 * (left_finger_offset_ee - right_finger_offset_ee)
        candidate_gripper_half_axis_w = torch.einsum(
            "ncij,nj->nci",
            candidate_exact_ee_rot_w,
            finger_half_axis_ee,
        )
        candidate_exact_left_finger_pos_w = candidate_exact_ee_pos_w + left_finger_offset_w
        candidate_exact_right_finger_pos_w = candidate_exact_ee_pos_w + right_finger_offset_w
        candidate_pregrasp_left_finger_pos_w = candidate_pregrasp_ee_pos_w + left_finger_offset_w
        candidate_pregrasp_right_finger_pos_w = candidate_pregrasp_ee_pos_w + right_finger_offset_w
        candidate_exact_left_tip_proxy_pos_w = candidate_exact_ee_pos_w + candidate_gripper_half_axis_w
        candidate_exact_right_tip_proxy_pos_w = candidate_exact_ee_pos_w - candidate_gripper_half_axis_w
        candidate_pregrasp_left_tip_proxy_pos_w = candidate_pregrasp_ee_pos_w + candidate_gripper_half_axis_w
        candidate_pregrasp_right_tip_proxy_pos_w = candidate_pregrasp_ee_pos_w - candidate_gripper_half_axis_w
        candidate_pregrasp_finger_table_clearance = torch.minimum(
            candidate_pregrasp_left_finger_pos_w[:, :, 2],
            candidate_pregrasp_right_finger_pos_w[:, :, 2],
        ) - float(self.cfg.table_surface_z)
        candidate_exact_finger_table_clearance = torch.minimum(
            candidate_exact_left_finger_pos_w[:, :, 2],
            candidate_exact_right_finger_pos_w[:, :, 2],
        ) - float(self.cfg.table_surface_z)
        candidate_pregrasp_tip_table_clearance = torch.minimum(
            candidate_pregrasp_left_tip_proxy_pos_w[:, :, 2],
            candidate_pregrasp_right_tip_proxy_pos_w[:, :, 2],
        ) - float(self.cfg.table_surface_z)
        candidate_projected_exact_tip_table_clearance = torch.minimum(
            candidate_exact_left_tip_proxy_pos_w[:, :, 2],
            candidate_exact_right_tip_proxy_pos_w[:, :, 2],
        ) - float(self.cfg.table_surface_z)
        candidate_pregrasp_tool_dist = torch.norm(candidate_pregrasp_tool_pos_w - candidate_contact_reference_w, dim=-1)
        candidate_pregrasp_ee_dist = torch.norm(candidate_pregrasp_ee_pos_w - candidate_contact_reference_w, dim=-1)
        if pregrasp_offset <= 1.0e-6:
            candidate_pregrasp_farther = torch.ones_like(candidate_pregrasp_tool_dist, dtype=torch.bool)
        else:
            candidate_pregrasp_farther = torch.where(
                candidate_has_contact,
                candidate_pregrasp_ee_dist > candidate_exact_reference_dist,
                candidate_pregrasp_tool_dist > candidate_exact_reference_dist,
            )

        pregrasp_z = candidate_pregrasp_offset_dir_w[:, :, 2]
        topdown_ok = pregrasp_z >= float(self.cfg.grasp_prior_reset_min_pregrasp_z)
        tool_downward_z = -candidate_tool_z_axis_w[:, :, 2]
        tool_down_ok = tool_downward_z >= float(getattr(self.cfg, "grasp_prior_reset_min_downward_tool_z", 0.0))
        min_contact_height = float(getattr(self.cfg, "grasp_prior_reset_min_contact_height_above_center", -math.inf))
        if bool(self.cfg.grasp_prior_reset_require_topdown) and math.isfinite(min_contact_height):
            contact_height_ok = (~candidate_has_contact) | (
                candidate_contact_reference_w[:, :, 2]
                >= object_center_pos_w_candidates[:, :, 2] + min_contact_height
            )
        else:
            contact_height_ok = torch.ones_like(topdown_ok, dtype=torch.bool)
        width_ok = (
            (candidate_required_width >= float(self.cfg.grasp_prior_reset_min_width))
            & (candidate_required_width <= float(self.cfg.max_gripper_width))
        )
        object_size = torch.clamp(self._grasp_prior_object_size(env_ids).unsqueeze(1), min=1.0e-4)
        candidate_contact_center_dist = torch.norm(
            candidate_contact_midpoint_w - object_center_pos_w_candidates,
            dim=-1,
        )
        candidate_center_gate_dist = torch.where(
            candidate_has_contact,
            candidate_contact_center_dist,
            candidate_exact_tool_dist,
        )
        normalized_center_dist = candidate_center_gate_dist / object_size
        normalized_tool_center_dist = candidate_exact_tool_dist / object_size
        center_ok = normalized_center_dist <= float(self.cfg.grasp_prior_reset_max_center_distance_frac)
        table_clearance_floor = max(float(self.cfg.finger_table_penetration_termination_margin), 0.0)
        table_floor_z = float(self.cfg.table_surface_z) + table_clearance_floor
        table_ok = (
            (candidate_pregrasp_finger_table_clearance >= table_clearance_floor)
            & (candidate_exact_finger_table_clearance >= table_clearance_floor)
            & (candidate_pregrasp_tip_table_clearance >= table_clearance_floor)
            & (candidate_projected_exact_tip_table_clearance >= table_clearance_floor)
            & (candidate_contact_reference_w[:, :, 2] >= table_floor_z)
        )
        valid = candidate_pregrasp_farther & width_ok & center_ok & table_ok
        if bool(self.cfg.grasp_prior_reset_require_topdown):
            valid = valid & topdown_ok & contact_height_ok
        if bool(getattr(self.cfg, "grasp_prior_reset_require_downward_tool_z", False)):
            valid = valid & tool_down_ok
        width_bonus = torch.clamp(candidate_required_width / max(float(self.cfg.max_gripper_width), 1.0e-6), 0.0, 1.0)
        score = candidate_confidence + pregrasp_z + tool_downward_z + 0.75 * width_bonus
        score = score - 6.0 * normalized_center_dist - normalized_tool_center_dist
        fallback_ok = candidate_pregrasp_farther & width_ok & table_ok
        if bool(self.cfg.grasp_prior_reset_require_topdown):
            fallback_ok = fallback_ok & topdown_ok & contact_height_ok
        if bool(getattr(self.cfg, "grasp_prior_reset_require_downward_tool_z", False)):
            fallback_ok = fallback_ok & tool_down_ok
        down_table_ok = tool_down_ok & table_ok
        down_table_width_ok = down_table_ok & width_ok
        down_table_width_center_ok = down_table_width_ok & center_ok
        down_table_width_center_contact_ok = down_table_width_center_ok & contact_height_ok
        down_table_width_center_contact_farther_ok = (
            down_table_width_center_contact_ok & candidate_pregrasp_farther
        )
        fallback_score = torch.where(fallback_ok, score, score - 1.0e5)
        scored = torch.where(valid, score, score - 1.0e6)
        has_valid = valid.any(dim=1, keepdim=True)
        has_fallback = fallback_ok.any(dim=1, keepdim=True)
        has_reset_candidate = (has_valid | has_fallback).squeeze(1)
        scored = torch.where(has_valid, scored, fallback_score)
        best_candidate = torch.argmax(scored, dim=1)
        row_ids = torch.arange(num_ids, dtype=torch.long, device=self.device)

        sample_indices = candidate_sample_indices[row_ids, best_candidate]
        exact_tool_pos_w = candidate_exact_tool_pos_w[row_ids, best_candidate]
        tool_z_axis_w = candidate_tool_z_axis_w[row_ids, best_candidate]
        tool_z_axis_w = tool_z_axis_w / torch.clamp(torch.norm(tool_z_axis_w, dim=-1, keepdim=True), min=1.0e-6)
        exact_tool_dist = candidate_exact_tool_dist[row_ids, best_candidate]
        exact_reference_dist = candidate_exact_reference_dist[row_ids, best_candidate]
        pregrasp_tool_pos_w = candidate_pregrasp_tool_pos_w[row_ids, best_candidate]
        exact_ee_pos_w = candidate_exact_ee_pos_w[row_ids, best_candidate]
        target_ee_pos_w = candidate_pregrasp_ee_pos_w[row_ids, best_candidate]
        pregrasp_tool_dist = torch.where(
            candidate_has_contact[row_ids, best_candidate],
            candidate_pregrasp_ee_dist[row_ids, best_candidate],
            candidate_pregrasp_tool_dist[row_ids, best_candidate],
        )
        pregrasp_farther = candidate_pregrasp_farther[row_ids, best_candidate]
        pregrasp_offset_dir_w = candidate_pregrasp_offset_dir_w[row_ids, best_candidate]
        contact_reference_w = candidate_contact_reference_w[row_ids, best_candidate]
        contact_reference_o = candidate_contact_reference_o[row_ids, best_candidate]
        contact_center_dist = candidate_contact_center_dist[row_ids, best_candidate]
        center_gate_dist = candidate_center_gate_dist[row_ids, best_candidate]
        has_contact_location = candidate_has_contact[row_ids, best_candidate]

        tool_quat_w = flat_candidate_tool_quat_w.reshape(num_ids, candidate_count, 4)[row_ids, best_candidate]
        exact_ee_quat_w = candidate_exact_ee_quat_w[row_ids, best_candidate]
        target_ee_quat_w = exact_ee_quat_w
        if bool((~has_reset_candidate).any().item()):
            no_candidate = ~has_reset_candidate
            env_origins = self.scene.env_origins[env_ids]
            safe_ee_pos_w = self.ee_pos[env_ids] + env_origins
            safe_ee_quat_w = self.ee_quat[env_ids]
            safe_tool_z_axis_w = torch.zeros_like(tool_z_axis_w)
            safe_tool_z_axis_w[:, 2] = -1.0
            safe_pregrasp_dir_w = torch.zeros_like(pregrasp_offset_dir_w)
            safe_pregrasp_dir_w[:, 2] = 1.0
            bad_dist = torch.full_like(exact_tool_dist, float("inf"))
            select_mask = no_candidate.unsqueeze(-1)
            sample_indices = torch.where(no_candidate, torch.full_like(sample_indices, -1), sample_indices)
            exact_tool_pos_w = torch.where(select_mask, safe_ee_pos_w, exact_tool_pos_w)
            pregrasp_tool_pos_w = torch.where(select_mask, safe_ee_pos_w, pregrasp_tool_pos_w)
            exact_ee_pos_w = torch.where(select_mask, safe_ee_pos_w, exact_ee_pos_w)
            target_ee_pos_w = torch.where(select_mask, safe_ee_pos_w, target_ee_pos_w)
            tool_z_axis_w = torch.where(select_mask, safe_tool_z_axis_w, tool_z_axis_w)
            pregrasp_offset_dir_w = torch.where(select_mask, safe_pregrasp_dir_w, pregrasp_offset_dir_w)
            tool_quat_w = torch.where(no_candidate.unsqueeze(-1), safe_ee_quat_w, tool_quat_w)
            exact_ee_quat_w = torch.where(no_candidate.unsqueeze(-1), safe_ee_quat_w, exact_ee_quat_w)
            target_ee_quat_w = exact_ee_quat_w
            exact_tool_dist = torch.where(no_candidate, bad_dist, exact_tool_dist)
            exact_reference_dist = torch.where(no_candidate, bad_dist, exact_reference_dist)
            pregrasp_tool_dist = torch.where(no_candidate, bad_dist, pregrasp_tool_dist)
            contact_center_dist = torch.where(no_candidate, bad_dist, contact_center_dist)
            center_gate_dist = torch.where(no_candidate, bad_dist, center_gate_dist)
            has_contact_location = has_contact_location & has_reset_candidate
            pregrasp_farther = pregrasp_farther & has_reset_candidate
        root_pos_w = self._robot.data.root_pos_w[env_ids]
        root_quat_w = self._robot.data.root_quat_w[env_ids]
        target_ee_pos_b, target_ee_quat_b = math_utils.subtract_frame_transforms(
            root_pos_w,
            root_quat_w,
            target_ee_pos_w,
            target_ee_quat_w,
        )
        return {
            "sample_indices": sample_indices,
            "target_ee_pos_b": target_ee_pos_b,
            "target_ee_quat_b": target_ee_quat_b,
            "cube_pos_w": object_center_pos_w,
            "cube_quat_w": cube_quat,
            "exact_tool_pos_w": exact_tool_pos_w,
            "exact_tool_quat_w": tool_quat_w,
            "pregrasp_tool_pos_w": pregrasp_tool_pos_w,
            "pregrasp_tool_quat_w": tool_quat_w,
            "exact_ee_pos_w": exact_ee_pos_w,
            "exact_ee_quat_w": exact_ee_quat_w,
            "target_ee_pos_w": target_ee_pos_w,
            "target_ee_quat_w": target_ee_quat_w,
            "tool_z_axis_w": tool_z_axis_w,
            "pregrasp_offset_dir_w": pregrasp_offset_dir_w,
            "exact_tool_dist": exact_tool_dist,
            "exact_reference_dist": exact_reference_dist,
            "pregrasp_tool_dist": pregrasp_tool_dist,
            "quality_reference_pos_w": contact_reference_w,
            "contact_reference_w": contact_reference_w,
            "contact_reference_object": contact_reference_o,
            "contact_center_dist": contact_center_dist,
            "center_gate_dist": center_gate_dist,
            "has_contact_location": has_contact_location,
            "candidate_topdown_count": topdown_ok.sum(dim=1),
            "candidate_tool_down_count": tool_down_ok.sum(dim=1),
            "candidate_contact_height_count": contact_height_ok.sum(dim=1),
            "candidate_center_count": center_ok.sum(dim=1),
            "candidate_width_count": width_ok.sum(dim=1),
            "candidate_table_count": table_ok.sum(dim=1),
            "candidate_down_table_count": down_table_ok.sum(dim=1),
            "candidate_down_table_width_count": down_table_width_ok.sum(dim=1),
            "candidate_down_table_width_center_count": down_table_width_center_ok.sum(dim=1),
            "candidate_down_table_width_center_contact_count": down_table_width_center_contact_ok.sum(dim=1),
            "candidate_down_table_width_center_contact_farther_count": (
                down_table_width_center_contact_farther_ok.sum(dim=1)
            ),
            "candidate_valid_count": valid.sum(dim=1),
            "candidate_fallback_count": fallback_ok.sum(dim=1),
            "candidate_select_success": has_reset_candidate,
            "pregrasp_finger_table_clearance": candidate_pregrasp_finger_table_clearance[row_ids, best_candidate],
            "exact_finger_table_clearance": candidate_exact_finger_table_clearance[row_ids, best_candidate],
            "pregrasp_tip_table_clearance": candidate_pregrasp_tip_table_clearance[row_ids, best_candidate],
            "projected_exact_tip_table_clearance": candidate_projected_exact_tip_table_clearance[
                row_ids, best_candidate
            ],
            "require_offset_radial_quality": ~has_contact_location,
            "exact_ee_dist": torch.norm(exact_ee_pos_w - contact_reference_w, dim=-1),
            "pregrasp_ee_dist": torch.norm(target_ee_pos_w - contact_reference_w, dim=-1),
            "pregrasp_farther": pregrasp_farther,
        }

    def _finger_offsets_from_ee(self, env_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self._compute_intermediate_values(env_ids)
        env_origins = self.scene.env_origins[env_ids]
        ee_pos_w = self.ee_pos[env_ids] + env_origins
        point_quat_w = torch.zeros((int(env_ids.numel()), 4), dtype=torch.float32, device=self.device)
        point_quat_w[:, 0] = 1.0
        left_offset_ee, _ = math_utils.subtract_frame_transforms(
            ee_pos_w,
            self.ee_quat[env_ids],
            self.left_finger_pos[env_ids] + env_origins,
            point_quat_w,
        )
        right_offset_ee, _ = math_utils.subtract_frame_transforms(
            ee_pos_w,
            self.ee_quat[env_ids],
            self.right_finger_pos[env_ids] + env_origins,
            point_quat_w,
        )
        return left_offset_ee, right_offset_ee

    def _finger_center_offset_from_ee(self, env_ids: torch.Tensor) -> torch.Tensor:
        left_offset_ee, right_offset_ee = self._finger_offsets_from_ee(env_ids)
        return 0.5 * (left_offset_ee + right_offset_ee)

    def _grasp_prior_reset_topdown_mask(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        mask = torch.ones(int(env_ids.numel()), dtype=torch.bool, device=self.device)
        if bool(self.cfg.grasp_prior_reset_require_topdown):
            mask = mask & (targets["pregrasp_offset_dir_w"][:, 2] >= float(self.cfg.grasp_prior_reset_min_pregrasp_z))
            min_contact_height = float(
                getattr(self.cfg, "grasp_prior_reset_min_contact_height_above_center", -math.inf)
            )
            if math.isfinite(min_contact_height):
                mask = mask & (
                    targets["contact_reference_w"][:, 2] >= targets["cube_pos_w"][:, 2] + min_contact_height
                )
        if bool(getattr(self.cfg, "grasp_prior_reset_require_downward_tool_z", False)):
            tool_z_axis_w = targets.get("tool_z_axis_w", targets["pregrasp_offset_dir_w"])
            mask = mask & (
                -tool_z_axis_w[:, 2] >= float(getattr(self.cfg, "grasp_prior_reset_min_downward_tool_z", 0.0))
            )
        object_size = torch.clamp(self._grasp_prior_object_size(env_ids), min=1.0e-4)
        center_dist = targets.get("center_gate_dist", targets["exact_tool_dist"])
        center_dist_ok = center_dist <= (
            float(self.cfg.grasp_prior_reset_max_center_distance_frac) * object_size
        )
        required_width = self._grasp_prior_required_open_width(env_ids, targets)
        width_ok = (
            (required_width >= float(self.cfg.grasp_prior_reset_min_width))
            & (required_width <= float(self.cfg.max_gripper_width))
        )
        table_clearance_floor = max(float(self.cfg.finger_table_penetration_termination_margin), 0.0)
        table_floor_z = float(self.cfg.table_surface_z) + table_clearance_floor
        table_ok = targets["contact_reference_w"][:, 2] >= table_floor_z
        if "pregrasp_finger_table_clearance" in targets and "exact_finger_table_clearance" in targets:
            table_ok = (
                table_ok
                & (targets["pregrasp_finger_table_clearance"] >= table_clearance_floor)
                & (targets["exact_finger_table_clearance"] >= table_clearance_floor)
            )
            if "pregrasp_tip_table_clearance" in targets and "projected_exact_tip_table_clearance" in targets:
                table_ok = (
                    table_ok
                    & (targets["pregrasp_tip_table_clearance"] >= table_clearance_floor)
                    & (targets["projected_exact_tip_table_clearance"] >= table_clearance_floor)
                )
        else:
            table_ok = table_ok & (targets["target_ee_pos_w"][:, 2] >= table_floor_z)
        return mask & center_dist_ok & width_ok & table_ok

    def _grasp_prior_reset_extra_success_mask(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        return self._grasp_prior_reset_topdown_mask(env_ids, targets)

    def _grasp_prior_reset_extra_quality_mask(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        return self._grasp_prior_reset_topdown_mask(env_ids, targets)

    def _grasp_prior_object_size(self, env_ids: torch.Tensor) -> torch.Tensor:
        return self.object_grasp_size[env_ids]

    def _grasp_prior_required_open_width(
        self,
        env_ids: torch.Tensor,
        targets: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        required_width = self.object_grasp_size[env_ids].clone()
        object_indices = self.object_asset_index[env_ids]
        sample_indices = targets["sample_indices"]
        for object_idx_tensor in torch.unique(object_indices):
            object_idx = int(object_idx_tensor.item())
            prior = self._object_grasp_priors.get(object_idx)
            if prior is None or prior.get("grasp_width") is None:
                continue
            grasp_width = prior["grasp_width"]
            if not isinstance(grasp_width, torch.Tensor):
                continue
            mask = object_indices == object_idx
            local_sample_indices = sample_indices[mask].clamp(min=0)
            sampled_width = grasp_width[local_sample_indices]
            required_width[mask] = self._sanitize_grasp_prior_width(sampled_width, required_width[mask])
        return torch.clamp(required_width, min=0.0)

    def _sanitize_grasp_prior_width(
        self,
        sampled_width: torch.Tensor,
        fallback_width: torch.Tensor,
    ) -> torch.Tensor:
        min_width = max(float(getattr(self.cfg, "grasp_prior_reset_min_width", 0.0)), 0.0)
        max_width = max(float(getattr(self.cfg, "max_gripper_width", 0.0)), min_width)
        plausible = torch.isfinite(sampled_width) & (sampled_width >= min_width) & (sampled_width <= max_width)
        return torch.where(plausible, sampled_width, fallback_width)

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

        self._sync_reset_joint_state(env_ids, joint_pos, joint_vel, update_buffers=True)
        for _ in range(settle_steps):
            self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
            self.scene.write_data_to_sim()
            self.sim.step(render=False)
            self.scene.update(dt=self.sim.cfg.dt)

        if bool(self.cfg.object_reset_zero_velocity_after_settle):
            zero_vel = torch.zeros((int(env_ids.numel()), 6), dtype=torch.float32, device=self.device)
            self._cube.write_root_velocity_to_sim(zero_vel, env_ids=env_ids)
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

        root_pos = self._cube.data.root_pos_w[env_ids] - self.scene.env_origins[env_ids]
        root_quat = self._cube.data.root_quat_w[env_ids]
        return root_pos, root_quat

    def _sample_and_write_object_reset_state(
        self,
        env_ids: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        num_ids = int(env_ids.numel())
        object_radius_xy = self.object_xy_radius[env_ids]
        spawn_xy = torch.zeros(num_ids, 2, device=self.device)
        spawn_xy[:, 0] = float(self.cfg.table_center_x) + float(self.cfg.object_spawn_center_offset_x)
        spawn_xy[:, 1] = float(self.cfg.table_center_y) + float(self.cfg.object_spawn_center_offset_y)
        spawn_xy += float(self.cfg.object_spawn_xy_randomization) * (
            2.0 * torch.rand(num_ids, 2, device=self.device) - 1.0
        )
        min_x = float(self.cfg.table_center_x - 0.5 * self.cfg.table_size_x) + object_radius_xy
        max_x = float(self.cfg.table_center_x + 0.5 * self.cfg.table_size_x) - object_radius_xy
        min_y = float(self.cfg.table_center_y - 0.5 * self.cfg.table_size_y) + object_radius_xy
        max_y = float(self.cfg.table_center_y + 0.5 * self.cfg.table_size_y) - object_radius_xy
        spawn_xy[:, 0] = torch.minimum(torch.maximum(spawn_xy[:, 0], min_x), max_x)
        spawn_xy[:, 1] = torch.minimum(torch.maximum(spawn_xy[:, 1], min_y), max_y)

        object_pos = torch.zeros(num_ids, 3, device=self.device)
        object_pos[:, 0:2] = spawn_xy
        object_quat, object_root_z_offset = self._sample_object_reset_pose(env_ids)
        object_pos[:, 2] = (
            float(self.cfg.table_surface_z)
            + object_root_z_offset
            + float(self.cfg.object_spawn_z_clearance)
        )
        object_state = torch.zeros(num_ids, 13, device=self.device)
        object_state[:, 0:3] = object_pos + self.scene.env_origins[env_ids]
        object_state[:, 3:7] = object_quat
        self._cube.write_root_state_to_sim(object_state, env_ids=env_ids)
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)

        return self._settle_reset_objects(env_ids, joint_pos, joint_vel)

    def _reset_idx(self, env_ids: Sequence[int] | None):
        self._ensure_cube_buffers()
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super(DextrahFrankaStarKittingEnv, self)._reset_idx(env_ids)
        self._reset_grasp_prior_metrics(env_ids)

        num_ids = len(env_ids)
        joint_pos = self._robot.data.default_joint_pos[env_ids].clone()
        joint_vel = torch.zeros_like(joint_pos)
        joint_noise = torch.zeros_like(joint_pos)
        arm_noise = float(self.cfg.arm_joint_reset_noise)
        if arm_noise > 0.0:
            joint_noise[:, self.arm_joint_ids] = arm_noise * (
                2.0 * torch.rand(num_ids, len(self.arm_joint_ids), device=self.device) - 1.0
            )
        joint_pos = torch.clamp(joint_pos + joint_noise, self.robot_dof_lower_limits, self.robot_dof_upper_limits)
        self._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
        self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        self.robot_dof_targets[env_ids] = joint_pos
        self.arm_joint_pos_target[env_ids] = joint_pos[:, self.arm_joint_ids]
        self.finger_joint_pos_target[env_ids] = joint_pos[:, self.finger_joint_ids]

        object_pos, object_quat = self._sample_and_write_object_reset_state(env_ids, joint_pos, joint_vel)
        object_center_pos = self._object_center_pos_from_root(env_ids, object_pos, object_quat)
        self.cube_initial_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids, 2] = object_center_pos[:, 2] + float(self.cfg.cube_lift_height)
        self.has_lifted_cube[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
        if getattr(self, "_grasp_prior_reset_enabled", False):
            self._apply_grasp_prior_reset(env_ids, joint_pos, joint_vel, object_pos, object_quat)
            max_attempts = max(int(getattr(self.cfg, "grasp_prior_reset_attempts", 1)), 1)
            for _ in range(1, max_attempts):
                retry_mask = ~self.grasp_prior_reset_quality_success[env_ids]
                if not bool(retry_mask.any().item()):
                    break
                retry_env_ids = env_ids[retry_mask]
                self._reset_grasp_prior_metrics(retry_env_ids)
                retry_object_pos, retry_object_quat = self._sample_and_write_object_reset_state(
                    retry_env_ids,
                    joint_pos[retry_mask],
                    joint_vel[retry_mask],
                )
                object_pos[retry_mask] = retry_object_pos
                object_quat[retry_mask] = retry_object_quat
                retry_object_center_pos = self._object_center_pos_from_root(
                    retry_env_ids,
                    retry_object_pos,
                    retry_object_quat,
                )
                self.cube_initial_pos[retry_env_ids] = retry_object_center_pos
                self.cube_goal_pos[retry_env_ids] = retry_object_center_pos
                self.cube_goal_pos[retry_env_ids, 2] = retry_object_center_pos[:, 2] + float(
                    self.cfg.cube_lift_height
                )
                self._apply_grasp_prior_reset(
                    retry_env_ids,
                    joint_pos[retry_mask],
                    joint_vel[retry_mask],
                    retry_object_pos,
                    retry_object_quat,
                )
        self.actions[env_ids] = 0.0
        self.ik_controller.reset(env_ids)

        self._compute_intermediate_values(env_ids)

    def _compute_intermediate_values(
        self,
        env_ids: torch.Tensor | None = None,
        *,
        update_success_timer: bool = False,
    ) -> None:
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        super()._compute_intermediate_values(env_ids, update_success_timer=False)

        env_origins = self.scene.env_origins[env_ids]
        root_pos = self._cube.data.root_pos_w[env_ids] - env_origins
        root_quat = self._cube.data.root_quat_w[env_ids]
        center_pos = self._object_center_pos_from_root(env_ids, root_pos, root_quat)
        self.cube_pos[env_ids] = center_pos

        finger_center = 0.5 * (self.left_finger_pos[env_ids] + self.right_finger_pos[env_ids])
        if hasattr(self, "grasp_prior_reset_contact_reference_pos_o"):
            reference_o = self.grasp_prior_reset_contact_reference_pos_o[env_ids]
            rot_m = math_utils.matrix_from_quat(root_quat)
            current_reference_pos = root_pos + torch.bmm(rot_m, reference_o.unsqueeze(-1)).squeeze(-1)
            use_contact_reference = (
                self.grasp_prior_reset_quality_success[env_ids]
                & self.grasp_prior_reset_has_contact_location[env_ids]
            )
            self.grasp_prior_current_contact_reference_pos[env_ids] = torch.where(
                use_contact_reference.unsqueeze(-1),
                current_reference_pos,
                center_pos,
            )

        self.ee_to_cube_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - center_pos, dim=-1)
        self.finger_center_to_cube_dist[env_ids] = torch.norm(finger_center - center_pos, dim=-1)
        self.left_finger_to_cube_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - center_pos,
            dim=-1,
        )
        self.right_finger_to_cube_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - center_pos,
            dim=-1,
        )
        self.max_finger_to_cube_dist[env_ids] = torch.maximum(
            self.left_finger_to_cube_dist[env_ids],
            self.right_finger_to_cube_dist[env_ids],
        )
        self.finger_distance_asymmetry[env_ids] = torch.abs(
            self.left_finger_to_cube_dist[env_ids] - self.right_finger_to_cube_dist[env_ids]
        )
        self.hand_to_cube_mean_dist[env_ids] = 0.5 * (
            self.left_finger_to_cube_dist[env_ids] + self.right_finger_to_cube_dist[env_ids]
        )
        self.hand_to_cube_max_dist[env_ids] = self.max_finger_to_cube_dist[env_ids]
        self.cube_lift_height[env_ids] = torch.clamp(
            center_pos[:, 2] - self.cube_initial_pos[env_ids, 2],
            min=0.0,
        )
        self.cube_xy_error[env_ids] = torch.norm(center_pos[:, :2] - self.cube_initial_pos[env_ids, :2], dim=-1)
        self.cube_goal_height_error[env_ids] = torch.abs(self.cube_goal_pos[env_ids, 2] - center_pos[:, 2])
        self.has_lifted_cube[env_ids] |= self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height)

        success = (
            (self.cube_lift_height[env_ids] >= float(self.cfg.cube_success_lift_height))
            & (self.cube_xy_error[env_ids] <= float(self.cfg.cube_success_xy_tol))
            & (self.hand_to_cube_mean_dist[env_ids] <= float(self.cfg.cube_success_hand_dist))
            & (self.finger_table_clearance[env_ids] >= float(self.cfg.finger_table_clearance_success_margin))
        )
        self.in_success_region[env_ids] = success
        if update_success_timer:
            self.time_in_success_region[env_ids] = torch.where(
                success,
                self.time_in_success_region[env_ids] + self.dt,
                torch.zeros_like(self.time_in_success_region[env_ids]),
            )
        else:
            self.time_in_success_region[env_ids] = torch.where(
                success,
                self.time_in_success_region[env_ids],
                torch.zeros_like(self.time_in_success_region[env_ids]),
            )

    def _get_robot_proprio_observations(self) -> torch.Tensor:
        self._compute_intermediate_values()
        joint_pos_scaled = (
            2.0
            * (self._robot.data.joint_pos - self.robot_dof_lower_limits)
            / (self.robot_dof_upper_limits - self.robot_dof_lower_limits)
            - 1.0
        )
        joint_vel_scaled = 0.12 * self._robot.data.joint_vel
        obs = torch.cat(
            (
                joint_pos_scaled,
                joint_vel_scaled,
                self.ee_pos,
                self.ee_quat,
                self.gripper_width.unsqueeze(-1),
                self.actions,
            ),
            dim=-1,
        )
        expected_dim = int(getattr(self.cfg, "rgb_robot_proprio_dim", obs.shape[-1]))
        if obs.shape[-1] != expected_dim:
            raise RuntimeError(f"RGB robot proprio dim mismatch: got {obs.shape[-1]}, expected {expected_dim}")
        return torch.clamp(obs, -5.0, 5.0)

    def _get_rgb_policy_observations(self) -> dict[str, torch.Tensor]:
        proprio = self._get_robot_proprio_observations()
        rgb = self._tiled_camera.data.output["rgb"].clone()[..., :3]
        rgb = rgb.permute((0, 3, 1, 2)).contiguous().to(dtype=torch.float32) / 255.0
        image_dim = int(getattr(self.cfg, "rgb_image_flat_dim", rgb.shape[1] * rgb.shape[2] * rgb.shape[3]))
        flat_rgb = rgb.flatten(start_dim=1)
        if flat_rgb.shape[-1] != image_dim:
            raise RuntimeError(f"RGB image flat dim mismatch: got {flat_rgb.shape[-1]}, expected {image_dim}")
        obs = torch.cat((proprio, flat_rgb), dim=-1)
        return {"policy": obs}

    def _get_observations(self) -> dict[str, torch.Tensor]:
        if bool(getattr(self.cfg, "enable_rgb_observations", False)):
            return self._get_rgb_policy_observations()

        base = super()._get_observations()
        obs = base["policy"]
        object_features = torch.cat(
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
        obs = torch.clamp(torch.cat((obs, object_features), dim=-1), -5.0, 5.0)
        return {"policy": obs, "critic": obs}

    def _get_rewards(self) -> torch.Tensor:
        rewards = super()._get_rewards()
        num_objects = int(getattr(self, "num_unique_objects", 0))
        if num_objects <= 0 or num_objects > 16 or "log" not in self.extras:
            return rewards

        log_terms = self.extras["log"]
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
            log_terms[f"{prefix}_finger_center_dist"] = (
                self.finger_center_to_cube_dist * object_mask
            ).sum() / denom
            if getattr(self, "_grasp_prior_reset_enabled", False):
                log_terms[f"{prefix}_grasp_prior_reset_success_rate"] = (
                    self.grasp_prior_reset_success.float() * object_mask
                ).sum() / denom
            if bool(getattr(self.cfg, "grasp_prior_action_warmstart_enabled", False)) and hasattr(
                self, "grasp_prior_action_warmstart_phase"
            ):
                lift_mask_bool = object_mask_bool & (self.grasp_prior_action_warmstart_phase == 2)
                lift_mask = lift_mask_bool.float()
                lift_denom = torch.clamp(lift_mask.sum(), min=1.0)
                log_terms[f"{prefix}_warmstart_lift_success_rate"] = (
                    self.in_success_region.float() * lift_mask
                ).sum() / lift_denom
                log_terms[f"{prefix}_warmstart_lift_lift_height"] = (
                    self.cube_lift_height * lift_mask
                ).sum() / lift_denom
                log_terms[f"{prefix}_warmstart_lift_gripper_width"] = (
                    self.gripper_width * lift_mask
                ).sum() / lift_denom
                log_terms[f"{prefix}_warmstart_lift_count"] = lift_mask.sum()
        return rewards

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


class DextrahFrankaMultiObjectRgbGraspEnv(DextrahFrankaMultiObjectGraspEnv):
    """RGB-observation variant of the Franka multi-object GraspGen task."""

    cfg: DextrahFrankaMultiObjectRgbGraspEnvCfg
