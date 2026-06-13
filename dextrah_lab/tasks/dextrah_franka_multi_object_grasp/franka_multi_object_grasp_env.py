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
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env import (
    DextrahFrankaCubeGraspEnv,
    _yaw_quat_wxyz,
)
from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env import (
    DextrahFrankaStarKittingEnv,
)

from .franka_multi_object_grasp_env_cfg import DextrahFrankaMultiObjectGraspEnvCfg


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
            self._object_grasp_priors[object_idx] = self._load_multi_object_prior(path, uuid=str(asset["uuid"]))

        has_prior_by_asset = torch.tensor(
            [1.0 if idx in self._object_grasp_priors else 0.0 for idx in range(self.num_unique_objects)],
            dtype=torch.float32,
            device=self.device,
        )
        self.object_has_grasp_prior[:] = has_prior_by_asset[self.object_asset_index]

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
        return {
            "grasps_object": grasps_tensor.contiguous(),
            "confidence": confidence_tensor.contiguous(),
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
        sample_indices = torch.full((num_ids,), -1, dtype=torch.long, device=self.device)
        object_grasp_t = torch.eye(4, device=self.device).repeat(num_ids, 1, 1)
        grasp_to_tool_t = torch.eye(4, device=self.device).repeat(num_ids, 1, 1)
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
            local_indices = torch.randint(grasps.shape[0], (count,), device=self.device)
            object_grasp_t[mask] = grasps[local_indices]
            sample_indices[mask] = local_indices
            grasp_to_tool = prior["grasp_to_tool"]
            if not isinstance(grasp_to_tool, torch.Tensor):
                raise RuntimeError("Internal grasp-to-tool tensor is invalid")
            grasp_to_tool_t[mask] = grasp_to_tool.unsqueeze(0).expand(count, -1, -1)

        world_object_t = torch.eye(4, device=self.device).repeat(num_ids, 1, 1)
        cube_pos_w = cube_pos + self.scene.env_origins[env_ids]
        world_object_t[:, :3, :3] = math_utils.matrix_from_quat(cube_quat)
        world_object_t[:, :3, 3] = cube_pos_w
        world_grasp_t = torch.bmm(world_object_t, object_grasp_t)
        world_tool_t = torch.bmm(world_grasp_t, grasp_to_tool_t)

        exact_tool_pos_w = world_tool_t[:, :3, 3]
        tool_z_axis_w = world_tool_t[:, :3, 2]
        tool_z_axis_w = tool_z_axis_w / torch.clamp(torch.norm(tool_z_axis_w, dim=-1, keepdim=True), min=1.0e-6)
        pregrasp_offset = abs(float(self.cfg.grasp_prior_pregrasp_offset))
        plus_tool_pos_w = exact_tool_pos_w + pregrasp_offset * tool_z_axis_w
        minus_tool_pos_w = exact_tool_pos_w - pregrasp_offset * tool_z_axis_w
        exact_tool_dist = torch.norm(exact_tool_pos_w - cube_pos_w, dim=-1)
        plus_tool_dist = torch.norm(plus_tool_pos_w - cube_pos_w, dim=-1)
        minus_tool_dist = torch.norm(minus_tool_pos_w - cube_pos_w, dim=-1)
        use_plus = plus_tool_dist >= minus_tool_dist
        pregrasp_tool_pos_w = torch.where(use_plus.unsqueeze(-1), plus_tool_pos_w, minus_tool_pos_w)
        pregrasp_tool_dist = torch.where(use_plus, plus_tool_dist, minus_tool_dist)
        pregrasp_farther = pregrasp_tool_dist > exact_tool_dist
        pregrasp_offset_dir_w = pregrasp_tool_pos_w - exact_tool_pos_w
        pregrasp_offset_dir_w = pregrasp_offset_dir_w / torch.clamp(
            torch.norm(pregrasp_offset_dir_w, dim=-1, keepdim=True),
            min=1.0e-6,
        )

        tool_quat_w = math_utils.quat_from_matrix(world_tool_t[:, :3, :3])
        exact_ee_pos_w, exact_ee_quat_w = math_utils.combine_frame_transforms(
            exact_tool_pos_w,
            tool_quat_w,
            self.ee_offset_pos[env_ids],
            self.ee_offset_rot[env_ids],
        )
        target_ee_pos_w, target_ee_quat_w = math_utils.combine_frame_transforms(
            pregrasp_tool_pos_w,
            tool_quat_w,
            self.ee_offset_pos[env_ids],
            self.ee_offset_rot[env_ids],
        )
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
            "cube_pos_w": cube_pos_w,
            "cube_quat_w": cube_quat,
            "exact_tool_pos_w": exact_tool_pos_w,
            "exact_tool_quat_w": tool_quat_w,
            "pregrasp_tool_pos_w": pregrasp_tool_pos_w,
            "pregrasp_tool_quat_w": tool_quat_w,
            "exact_ee_pos_w": exact_ee_pos_w,
            "exact_ee_quat_w": exact_ee_quat_w,
            "target_ee_pos_w": target_ee_pos_w,
            "target_ee_quat_w": target_ee_quat_w,
            "pregrasp_offset_dir_w": pregrasp_offset_dir_w,
            "exact_tool_dist": exact_tool_dist,
            "pregrasp_tool_dist": pregrasp_tool_dist,
            "exact_ee_dist": torch.norm(exact_ee_pos_w - cube_pos_w, dim=-1),
            "pregrasp_ee_dist": torch.norm(target_ee_pos_w - cube_pos_w, dim=-1),
            "pregrasp_farther": pregrasp_farther,
        }

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
            required_width[mask] = torch.where(torch.isfinite(sampled_width), sampled_width, required_width[mask])
        return torch.clamp(required_width, min=0.0)

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

        object_pos, object_quat = self._settle_reset_objects(env_ids, joint_pos, joint_vel)
        object_center_pos = self._object_center_pos_from_root(env_ids, object_pos, object_quat)
        self.cube_initial_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids, 2] = object_center_pos[:, 2] + float(self.cfg.cube_lift_height)
        self.has_lifted_cube[env_ids] = False
        self.in_success_region[env_ids] = False
        self.time_in_success_region[env_ids] = 0.0
        if getattr(self, "_grasp_prior_reset_enabled", False):
            self._apply_grasp_prior_reset(env_ids, joint_pos, joint_vel, object_pos, object_quat)
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
        self.ee_to_cube_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - center_pos, dim=-1)
        self.finger_center_to_cube_dist[env_ids] = torch.norm(finger_center - center_pos, dim=-1)
        self.left_finger_to_cube_dist[env_ids] = torch.norm(self.left_finger_pos[env_ids] - center_pos, dim=-1)
        self.right_finger_to_cube_dist[env_ids] = torch.norm(self.right_finger_pos[env_ids] - center_pos, dim=-1)
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

    def _get_observations(self) -> dict[str, torch.Tensor]:
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
