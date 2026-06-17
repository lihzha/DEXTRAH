"""DirectRLEnv for Franka GraspGen multi-object pick-up."""

from __future__ import annotations

from collections.abc import Sequence
import json
import math
import os
from pathlib import Path

import torch
import torch.nn.functional as F

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import Articulation, RigidObject
from isaaclab.sensors import TiledCamera
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane

from dextrah_lab.tasks.dextrah_multi_object_grasp.multi_object_grasp_task import (
    MultiObjectGraspTaskMixin,
    npz_scalar as _npz_scalar,
    repo_root as _repo_root,
    resolve_repo_path as _resolve_path,
)
from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env import (
    DextrahFrankaCubeGraspEnv,
)
from dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env import (
    DextrahFrankaStarKittingEnv,
)

from .franka_multi_object_grasp_env_cfg import (
    DextrahFrankaMultiObjectGraspEnvCfg,
    DextrahFrankaMultiObjectRgbGraspEnvCfg,
)


def _debug_reset_log(message: str) -> None:
    if os.environ.get("DEXTRAH_DEBUG_RESET", "").lower() in ("1", "true", "yes", "on"):
        print(f"[DEBUG][franka_multi_object_reset] {message}", flush=True)


def _count_object_assets_for_observations(cfg: DextrahFrankaMultiObjectGraspEnvCfg) -> int:
    """Count loaded target objects before DirectRLEnv allocates observation buffers."""

    object_assets_dir = _resolve_path(str(cfg.object_assets_dir), base_dir=_repo_root())
    manifest_path = str(cfg.object_asset_manifest_path or "")
    if not manifest_path:
        candidate = object_assets_dir / "manifest.json"
        manifest_path = str(candidate) if candidate.is_file() else ""

    if manifest_path:
        manifest = _resolve_path(manifest_path, base_dir=_repo_root())
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        object_records = payload.get("objects")
        if not isinstance(object_records, list):
            raise ValueError(f"Expected manifest objects list in {manifest}")
        count = len(object_records)
    else:
        count = len(sorted((object_assets_dir / "USD").glob("*/*.usd")))

    max_objects = int(getattr(cfg, "max_objects", 0))
    if max_objects > 0:
        count = min(count, max_objects)
    if count <= 0:
        raise ValueError("No multi-object GraspGen assets were found")
    return count


class DextrahFrankaMultiObjectGraspEnv(MultiObjectGraspTaskMixin, DextrahFrankaCubeGraspEnv):
    """Franka task: pick up one of many GraspGen object assets per vectorized env."""

    cfg: DextrahFrankaMultiObjectGraspEnvCfg

    def __init__(self, cfg: DextrahFrankaMultiObjectGraspEnvCfg, render_mode: str | None = None, **kwargs):
        if not bool(getattr(cfg, "enable_rgb_observations", False)):
            num_objects = _count_object_assets_for_observations(cfg)
            # Match the original DEXTRAH teacher's object conditioning: base
            # low-dimensional state plus one-hot object id and object scale.
            obs_dim = 72 + num_objects + 1
            cfg.observation_space = obs_dim
            cfg.state_space = obs_dim
            cfg.num_observations = obs_dim
            cfg.num_states = obs_dim
        super().__init__(cfg, render_mode, **kwargs)

    def _setup_scene(self):
        self._setup_multi_object_task()
        self.multi_object_idx_onehot = F.one_hot(
            self.object_asset_index,
            num_classes=self.num_unique_objects,
        ).to(dtype=torch.float32, device=self.device)
        self._setup_tabletop_clutter_task()

        self._robot = Articulation(self.cfg.robot)
        self._table = RigidObject(self.cfg.table)
        spawn_ground_plane(prim_path="/World/ground", cfg=GroundPlaneCfg())

        self.scene.clone_environments(copy_from_source=True)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=["/World/ground"])
        self.scene.articulations["robot"] = self._robot
        self.scene.rigid_objects["table"] = self._table
        self._spawn_multi_object_assets()
        self._spawn_tabletop_clutter_assets()
        self._spawn_tabletop_goal_bin()

        light_cfg = sim_utils.DomeLightCfg(intensity=1800.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)
        if bool(getattr(self.cfg, "enable_rgb_observations", False)):
            self._tiled_camera = TiledCamera(self.cfg.tiled_camera)
            self.scene.sensors["tiled_camera"] = self._tiled_camera

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
        allow_uncovered_verified = bool(getattr(self.cfg, "grasp_prior_verified_allow_uncovered", False))
        self._grasp_prior_verified_uncovered_uuids: list[str] = []
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
                if allow_uncovered_verified:
                    self._grasp_prior_verified_uncovered_uuids.append(uuid)
                else:
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
                    if allow_uncovered_verified:
                        self._grasp_prior_verified_uncovered_uuids.append(uuid)
                    else:
                        raise ValueError(
                            f"Verified grasp cache contains no valid indices for object {uuid} in {path}"
                        )
                else:
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
                    finite_contacts,
                    self._sanitize_grasp_prior_width(
                        sampled_contact_width,
                        candidate_required_width[mask],
                    ),
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

    def _reset_idx(self, env_ids: Sequence[int] | None):
        self._ensure_cube_buffers()
        if env_ids is None:
            env_ids = self._robot._ALL_INDICES
        env_ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        _debug_reset_log(f"start num_envs={int(env_ids.numel())}")
        super(DextrahFrankaStarKittingEnv, self)._reset_idx(env_ids)
        _debug_reset_log("after base reset")
        prior_metrics_active = (
            bool(getattr(self, "_grasp_prior_reset_enabled", False))
            or bool(getattr(self.cfg, "grasp_prior_action_warmstart_enabled", False))
            or bool(getattr(self.cfg, "grasp_prior_action_prior_reward_enabled", False))
        )
        if prior_metrics_active:
            _debug_reset_log("before grasp prior metric reset")
            self._reset_grasp_prior_metrics(env_ids)
            _debug_reset_log("after grasp prior metric reset")

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
        _debug_reset_log("after robot state reset")

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
        spawn_xy = self._move_xy_outside_tabletop_goal_bin(env_ids, spawn_xy, object_radius_xy)

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
        _debug_reset_log("after target object reset")
        self._reset_tabletop_clutter(env_ids, target_root_pos=object_pos)
        _debug_reset_log("after tabletop clutter reset")
        self.scene.write_data_to_sim()
        self.sim.forward()
        self.scene.update(dt=0.0)
        _debug_reset_log("after sim forward")

        object_pos, object_quat = self._settle_reset_objects(env_ids, joint_pos, joint_vel)
        _debug_reset_log("after reset settle")
        object_center_pos = self._object_center_pos_from_root(env_ids, object_pos, object_quat)
        self.cube_initial_pos[env_ids] = object_center_pos
        self.cube_goal_pos[env_ids] = self._tabletop_goal_pos(env_ids, object_center_pos)
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
                self._apply_grasp_prior_reset(
                    retry_env_ids,
                    joint_pos[retry_mask],
                    joint_vel[retry_mask],
                    object_pos[retry_mask],
                    object_quat[retry_mask],
                )
        self.actions[env_ids] = 0.0
        self.ik_controller.reset(env_ids)

        self._compute_intermediate_values(env_ids)
        _debug_reset_log("after intermediate values")

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
        if not hasattr(self, "multi_object_reward_reference_active"):
            self.multi_object_reward_reference_active = torch.zeros(
                self.num_envs,
                dtype=torch.bool,
                device=self.device,
            )
            self.multi_object_ee_to_object_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_finger_center_to_object_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_left_finger_to_object_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_right_finger_to_object_center_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_ee_to_grasp_reference_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_finger_center_to_grasp_reference_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_left_finger_to_grasp_reference_dist = torch.zeros(self.num_envs, device=self.device)
            self.multi_object_right_finger_to_grasp_reference_dist = torch.zeros(self.num_envs, device=self.device)

        self.multi_object_ee_to_object_center_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - center_pos, dim=-1)
        self.multi_object_finger_center_to_object_center_dist[env_ids] = torch.norm(finger_center - center_pos, dim=-1)
        self.multi_object_left_finger_to_object_center_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - center_pos,
            dim=-1,
        )
        self.multi_object_right_finger_to_object_center_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - center_pos,
            dim=-1,
        )

        distance_reference_pos = center_pos
        grasp_reference_pos = center_pos
        use_contact_reference = torch.zeros(int(env_ids.numel()), dtype=torch.bool, device=self.device)
        reward_use_contact_reference = bool(getattr(self.cfg, "grasp_prior_reward_use_contact_reference", False))
        if hasattr(self, "grasp_prior_reset_contact_reference_pos_o"):
            reference_o = self.grasp_prior_reset_contact_reference_pos_o[env_ids]
            rot_m = math_utils.matrix_from_quat(root_quat)
            current_reference_pos = root_pos + torch.bmm(rot_m, reference_o.unsqueeze(-1)).squeeze(-1)
            use_contact_reference = (
                self.grasp_prior_reset_quality_success[env_ids]
                & self.grasp_prior_reset_has_contact_location[env_ids]
            )
            grasp_reference_pos = torch.where(
                use_contact_reference.unsqueeze(-1),
                current_reference_pos,
                center_pos,
            )
            self.grasp_prior_current_contact_reference_pos[env_ids] = grasp_reference_pos
            if reward_use_contact_reference:
                distance_reference_pos = grasp_reference_pos

        self.multi_object_reward_reference_active[env_ids] = use_contact_reference & reward_use_contact_reference
        self.multi_object_ee_to_grasp_reference_dist[env_ids] = torch.norm(
            self.ee_pos[env_ids] - grasp_reference_pos,
            dim=-1,
        )
        self.multi_object_finger_center_to_grasp_reference_dist[env_ids] = torch.norm(
            finger_center - grasp_reference_pos,
            dim=-1,
        )
        self.multi_object_left_finger_to_grasp_reference_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - grasp_reference_pos,
            dim=-1,
        )
        self.multi_object_right_finger_to_grasp_reference_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - grasp_reference_pos,
            dim=-1,
        )

        self.ee_to_cube_dist[env_ids] = torch.norm(self.ee_pos[env_ids] - distance_reference_pos, dim=-1)
        self.finger_center_to_cube_dist[env_ids] = torch.norm(finger_center - distance_reference_pos, dim=-1)
        self.left_finger_to_cube_dist[env_ids] = torch.norm(
            self.left_finger_pos[env_ids] - distance_reference_pos,
            dim=-1,
        )
        self.right_finger_to_cube_dist[env_ids] = torch.norm(
            self.right_finger_pos[env_ids] - distance_reference_pos,
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
                self.multi_object_idx_onehot,
                self.object_scale,
            ),
            dim=-1,
        )
        obs = torch.clamp(torch.cat((obs, object_features), dim=-1), -5.0, 5.0)
        return {"policy": obs, "critic": obs}

    def _get_rewards(self) -> torch.Tensor:
        rewards = super()._get_rewards()
        num_objects = int(getattr(self, "num_unique_objects", 0))
        if num_objects <= 0 or "log" not in self.extras:
            return rewards

        log_terms = self.extras["log"]
        if hasattr(self, "multi_object_reward_reference_active"):
            log_terms["multi_object_reward_reference_active_rate"] = (
                self.multi_object_reward_reference_active.float().mean()
            )
            log_terms["multi_object_ee_to_object_center_dist"] = (
                self.multi_object_ee_to_object_center_dist.mean()
            )
            log_terms["multi_object_finger_center_to_object_center_dist"] = (
                self.multi_object_finger_center_to_object_center_dist.mean()
            )
            log_terms["multi_object_finger_center_to_grasp_reference_dist"] = (
                self.multi_object_finger_center_to_grasp_reference_dist.mean()
            )
            log_terms["multi_object_max_finger_to_grasp_reference_dist"] = torch.maximum(
                self.multi_object_left_finger_to_grasp_reference_dist,
                self.multi_object_right_finger_to_grasp_reference_dist,
            ).mean()
        if num_objects > 64:
            return rewards
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
            if hasattr(self, "multi_object_reward_reference_active"):
                log_terms[f"{prefix}_reward_reference_active_rate"] = (
                    self.multi_object_reward_reference_active.float() * object_mask
                ).sum() / denom
                log_terms[f"{prefix}_finger_center_to_object_center_dist"] = (
                    self.multi_object_finger_center_to_object_center_dist * object_mask
                ).sum() / denom
                log_terms[f"{prefix}_finger_center_to_grasp_reference_dist"] = (
                    self.multi_object_finger_center_to_grasp_reference_dist * object_mask
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

class DextrahFrankaMultiObjectRgbGraspEnv(DextrahFrankaMultiObjectGraspEnv):
    """RGB-observation variant of the Franka multi-object GraspGen task."""

    cfg: DextrahFrankaMultiObjectRgbGraspEnvCfg
