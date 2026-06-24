"""Official Diffusion Policy dataset adapter for DEXTRAH lowdim demos."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

try:
    from diffusion_policy.common.normalize_util import (
        array_to_stats,
        get_identity_normalizer_from_stat,
        get_image_range_normalizer,
    )
    from diffusion_policy.dataset.base_dataset import BaseImageDataset, BaseLowdimDataset
    from diffusion_policy.env_runner.base_image_runner import BaseImageRunner
    from diffusion_policy.env_runner.base_lowdim_runner import BaseLowdimRunner
    from diffusion_policy.model.common.normalizer import LinearNormalizer, SingleFieldLinearNormalizer
except Exception:  # pragma: no cover - exercised in environments without official DP installed.
    BaseImageDataset = torch.utils.data.Dataset
    BaseLowdimDataset = torch.utils.data.Dataset
    BaseImageRunner = object
    BaseLowdimRunner = object
    LinearNormalizer = None
    SingleFieldLinearNormalizer = None
    array_to_stats = None
    get_image_range_normalizer = None
    get_identity_normalizer_from_stat = None


def dataset_statistics(dataset_path: str | Path) -> dict[str, Any]:
    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    return {
        "dataset_path": str(dataset_path),
        "num_steps": int(obs.shape[0]),
        "num_episodes": int(episode_ends.shape[0]),
        "obs_shape": list(obs.shape),
        "action_shape": list(action.shape),
        "obs_min": np.min(obs, axis=0).astype(float).tolist(),
        "obs_max": np.max(obs, axis=0).astype(float).tolist(),
        "action_min": np.min(action, axis=0).astype(float).tolist(),
        "action_max": np.max(action, axis=0).astype(float).tolist(),
    }


def _create_limits_clamp_constant_action_normalizer(
    action: np.ndarray,
    *,
    range_eps: float = 1.0e-4,
):
    """Create a limits normalizer that keeps near-constant action dims near their mean.

    Official ``SingleFieldLinearNormalizer`` maps near-constant dimensions with
    unit scale. That is fine for observations, but for Diffusion Policy actions
    it lets sampled normalized noise unnormalize to large controller commands in
    dimensions whose labels are effectively zero. This variant keeps ordinary
    dimensions identical to limits normalization and maps clipped normalized
    samples in near-constant dimensions back to ``mean +/- range_eps / 2``.
    """

    stat = array_to_stats(action)
    input_min = stat["min"].astype(np.float32, copy=True)
    input_max = stat["max"].astype(np.float32, copy=True)
    input_mean = stat["mean"].astype(np.float32, copy=True)
    input_range = input_max - input_min
    small_range = input_range < float(range_eps)
    effective_range = input_range.copy()
    effective_range[small_range] = float(range_eps)
    scale = (2.0 / effective_range).astype(np.float32)
    offset = (-1.0 - scale * input_min).astype(np.float32)
    offset[small_range] = (-scale[small_range] * input_mean[small_range]).astype(np.float32)
    return SingleFieldLinearNormalizer.create_manual(
        scale=scale,
        offset=offset,
        input_stats_dict=stat,
    )


def _contact_phase_progress_features(
    phase_ids: np.ndarray,
    episode_ends: np.ndarray,
    n_rows: int,
) -> np.ndarray:
    phase_ids = np.asarray(phase_ids, dtype=np.int32)
    if phase_ids.shape != (int(n_rows),):
        raise ValueError(f"phase_ids must have shape ({n_rows},), got {phase_ids.shape}")
    unique = set(int(v) for v in np.unique(phase_ids))
    if not unique.issubset({-1, 0, 1, 2}):
        raise ValueError(
            "RGB phase/progress augmentation expects contact relabel phase ids "
            f"in {{-1,0,1,2}}, got {sorted(unique)}"
        )
    contact_phase = phase_ids.copy()
    contact_phase[contact_phase < 0] = 0
    one_hot = np.eye(3, dtype=np.float32)[contact_phase]

    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    progress = np.zeros((int(n_rows),), dtype=np.float32)
    for start, end in zip(starts, episode_ends):
        start_i = int(start)
        end_i = int(end)
        length = end_i - start_i
        if length <= 1:
            progress[start_i:end_i] = 0.0
        else:
            progress[start_i:end_i] = np.linspace(0.0, 1.0, length, dtype=np.float32)
    return np.concatenate((one_hot, progress[:, None]), axis=1).astype(np.float32)


def _linear_normalizer_from_checkpoint(checkpoint_path: str | Path):
    """Load the policy normalizer state from an official DP checkpoint."""

    if LinearNormalizer is None:
        raise ImportError("diffusion_policy is not installed; cannot load checkpoint normalizer")
    import dill

    path = Path(checkpoint_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = torch.load(path.open("rb"), pickle_module=dill, map_location="cpu")
    try:
        model_state = payload["state_dicts"]["model"]
    except KeyError as exc:
        raise KeyError(f"{path} does not look like an official DP workspace checkpoint") from exc
    normalizer_state = {
        key[len("normalizer.") :]: value
        for key, value in model_state.items()
        if key.startswith("normalizer.")
    }
    if not normalizer_state:
        raise KeyError(f"{path} does not contain model normalizer state")
    normalizer = LinearNormalizer()
    normalizer.load_state_dict(normalizer_state)
    return normalizer


class FrankaCubeLowdimDataset(BaseLowdimDataset):
    """NPZ-backed low-dimensional dataset for official Diffusion Policy.

    The NPZ layout is produced by
    ``dextrah_lab.offline_dp_bc.trajectory_conversion``:

    - ``obs``: ``(N, obs_dim)`` compact Franka cube observations.
    - ``action``: ``(N, 7)`` normalized DEXTRAH relative EE plus gripper actions.
    - ``episode_ends``: cumulative exclusive episode ends.
    """

    def __init__(
        self,
        dataset_path: str,
        horizon: int = 16,
        pad_before: int = 1,
        pad_after: int = 7,
        seed: int = 42,
        val_ratio: float = 0.0,
        max_train_episodes: int | None = None,
        split: str = "train",
        action_normalizer: str = "identity",
    ):
        super().__init__()
        self.dataset_path = str(dataset_path)
        self.horizon = int(horizon)
        self.pad_before = int(pad_before)
        self.pad_after = int(pad_after)
        self.seed = int(seed)
        self.val_ratio = float(val_ratio)
        self.max_train_episodes = max_train_episodes
        self.split = str(split)
        self.action_normalizer = str(action_normalizer)

        data = np.load(self.dataset_path, allow_pickle=False)
        self.obs = np.asarray(data["obs"], dtype=np.float32)
        self.action = np.asarray(data["action"], dtype=np.float32)
        self.episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
        if self.obs.ndim != 2:
            raise ValueError(f"obs must be rank 2, got {self.obs.shape}")
        if self.action.ndim != 2:
            raise ValueError(f"action must be rank 2, got {self.action.shape}")
        if self.obs.shape[0] != self.action.shape[0]:
            raise ValueError(f"obs/action length mismatch: {self.obs.shape} vs {self.action.shape}")
        if self.action.shape[1] != 7:
            raise ValueError(f"Expected DEXTRAH 7D actions, got {self.action.shape[1]}")
        if self.episode_ends.ndim != 1 or self.episode_ends[-1] != self.obs.shape[0]:
            raise ValueError("episode_ends must be 1D cumulative exclusive ends ending at N")

        self.episode_starts = np.concatenate(([0], self.episode_ends[:-1])).astype(np.int64)
        self.train_episode_mask = self._make_train_episode_mask()
        self.indices = self._build_indices(self.split)

    def _make_train_episode_mask(self) -> np.ndarray:
        n_eps = int(self.episode_ends.shape[0])
        rng = np.random.default_rng(self.seed)
        if self.val_ratio <= 0.0 or n_eps == 1:
            train_mask = np.ones(n_eps, dtype=bool)
        else:
            val_mask = rng.random(n_eps) < min(max(self.val_ratio, 0.0), 1.0)
            if np.all(val_mask):
                val_mask[rng.integers(0, n_eps)] = False
            if not np.any(val_mask):
                val_mask[rng.integers(0, n_eps)] = True
            train_mask = ~val_mask
        if self.max_train_episodes is not None and int(self.max_train_episodes) < int(train_mask.sum()):
            train_ids = np.nonzero(train_mask)[0]
            keep = rng.choice(train_ids, size=int(self.max_train_episodes), replace=False)
            new_mask = np.zeros_like(train_mask)
            new_mask[keep] = True
            train_mask = new_mask
        return train_mask

    def _build_indices(self, split: str) -> list[tuple[int, int, int]]:
        if split not in {"train", "val", "all"}:
            raise ValueError(f"Unsupported split {split!r}")
        indices: list[tuple[int, int, int]] = []
        for ep_idx, (start, end) in enumerate(zip(self.episode_starts, self.episode_ends)):
            if split == "train" and not self.train_episode_mask[ep_idx]:
                continue
            if split == "val" and self.train_episode_mask[ep_idx]:
                continue
            for t in range(int(start), int(end)):
                indices.append((int(start), int(end), int(t)))
        return indices

    def get_validation_dataset(self):
        val_set = copy.copy(self)
        val_set.split = "val"
        val_set.indices = self._build_indices("val")
        return val_set

    def get_normalizer(self, **kwargs):
        if LinearNormalizer is None or SingleFieldLinearNormalizer is None:
            raise ImportError(
                "diffusion_policy is not installed; install real-stanford/diffusion_policy "
                "to use get_normalizer in the official workspace."
            )
        normalizer = LinearNormalizer()
        normalizer["obs"] = SingleFieldLinearNormalizer.create_fit(
            self.obs,
            last_n_dims=1,
            mode=kwargs.get("obs_mode", "limits"),
            output_max=1.0,
            output_min=-1.0,
        )
        if self.action_normalizer == "identity":
            stat = array_to_stats(self.action)
            normalizer["action"] = get_identity_normalizer_from_stat(stat)
        elif self.action_normalizer == "limits":
            normalizer["action"] = SingleFieldLinearNormalizer.create_fit(
                self.action,
                last_n_dims=1,
                mode="limits",
                output_max=1.0,
                output_min=-1.0,
            )
        elif self.action_normalizer == "limits_clamp_constant":
            normalizer["action"] = _create_limits_clamp_constant_action_normalizer(self.action)
        else:
            raise ValueError(f"Unsupported action_normalizer {self.action_normalizer!r}")
        return normalizer

    def get_all_actions(self) -> torch.Tensor:
        return torch.from_numpy(self.action)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        ep_start, ep_end, center = self.indices[idx]
        seq_start = center - self.pad_before
        frame_ids = np.arange(seq_start, seq_start + self.horizon, dtype=np.int64)
        frame_ids = np.clip(frame_ids, ep_start, ep_end - 1)
        return {
            "obs": torch.from_numpy(self.obs[frame_ids]),
            "action": torch.from_numpy(self.action[frame_ids]),
        }


class FrankaCubeRgbDataset(BaseImageDataset):
    """NPZ-backed RGB + robot-proprio dataset for official image Diffusion Policy.

    Policy observations intentionally exclude cube/object low-dimensional state.
    Required NPZ keys:

    - ``image`` or ``rgb``: ``(N,H,W,3)`` or ``(N,3,H,W)`` uint8 RGB frames.
    - ``robot_state``: ``(N,D)`` non-privileged robot proprioception.
    - ``action``: ``(N,7)`` normalized DEXTRAH relative EE plus gripper actions.
    - ``episode_ends``: cumulative exclusive episode ends.
    """

    def __init__(
        self,
        dataset_path: str,
        horizon: int = 16,
        pad_before: int = 1,
        pad_after: int = 7,
        seed: int = 42,
        val_ratio: float = 0.0,
        max_train_episodes: int | None = None,
        split: str = "train",
        action_normalizer: str = "identity",
        image_key: str = "image",
        robot_state_key: str = "robot_state",
        obs_image_name: str = "image",
        obs_robot_state_name: str = "robot_state",
        append_phase_progress: bool = False,
        phase_key: str = "phase_ids",
        normalizer_checkpoint: str | None = None,
        distill_mask_mode: str = "none",
        distill_mask_tolerance: float = 1.0e-6,
    ):
        super().__init__()
        self.dataset_path = str(dataset_path)
        self.horizon = int(horizon)
        self.pad_before = int(pad_before)
        self.pad_after = int(pad_after)
        self.seed = int(seed)
        self.val_ratio = float(val_ratio)
        self.max_train_episodes = max_train_episodes
        self.split = str(split)
        self.action_normalizer = str(action_normalizer)
        self.image_key = str(image_key)
        self.robot_state_key = str(robot_state_key)
        self.obs_image_name = str(obs_image_name)
        self.obs_robot_state_name = str(obs_robot_state_name)
        self.append_phase_progress = bool(append_phase_progress)
        self.phase_key = str(phase_key)
        self.normalizer_checkpoint = None if normalizer_checkpoint in (None, "") else str(normalizer_checkpoint)
        self.distill_mask_mode = str(distill_mask_mode)
        self.distill_mask_tolerance = float(distill_mask_tolerance)

        data = np.load(self.dataset_path, allow_pickle=False)
        actual_image_key = self.image_key if self.image_key in data.files else "rgb"
        if actual_image_key not in data.files:
            raise KeyError(f"{self.dataset_path} missing image key {self.image_key!r} or 'rgb'")
        if self.robot_state_key not in data.files:
            raise KeyError(f"{self.dataset_path} missing robot_state key {self.robot_state_key!r}")
        self.image = np.asarray(data[actual_image_key])
        self.robot_state = np.asarray(data[self.robot_state_key], dtype=np.float32)
        self.action = np.asarray(data["action"], dtype=np.float32)
        self.episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)

        if self.image.ndim != 4:
            raise ValueError(f"image must be rank 4, got {self.image.shape}")
        if self.image.shape[-1] == 3:
            self.image_layout = "nhwc"
            self.image_shape_chw = (3, int(self.image.shape[1]), int(self.image.shape[2]))
        elif self.image.shape[1] == 3:
            self.image_layout = "nchw"
            self.image_shape_chw = (3, int(self.image.shape[2]), int(self.image.shape[3]))
        else:
            raise ValueError(f"image must be NHWC or NCHW RGB, got {self.image.shape}")
        if self.robot_state.ndim != 2:
            raise ValueError(f"robot_state must be rank 2, got {self.robot_state.shape}")
        if self.action.ndim != 2 or self.action.shape[1] != 7:
            raise ValueError(f"Expected DEXTRAH 7D actions, got {self.action.shape}")
        n = int(self.image.shape[0])
        if self.robot_state.shape[0] != n or self.action.shape[0] != n:
            raise ValueError(
                f"image/robot_state/action length mismatch: {self.image.shape}, "
                f"{self.robot_state.shape}, {self.action.shape}"
            )
        if self.episode_ends.ndim != 1 or self.episode_ends.size == 0 or int(self.episode_ends[-1]) != n:
            raise ValueError("episode_ends must be 1D cumulative exclusive ends ending at N")
        if self.append_phase_progress:
            if self.phase_key not in data.files:
                raise KeyError(
                    f"{self.dataset_path} missing {self.phase_key!r}; "
                    "required when append_phase_progress=true"
                )
            phase_features = _contact_phase_progress_features(data[self.phase_key], self.episode_ends, n)
            self.robot_state = np.concatenate((self.robot_state, phase_features), axis=1).astype(np.float32)

        self.episode_starts = np.concatenate(([0], self.episode_ends[:-1])).astype(np.int64)
        self.row_distill_mask = self._make_row_distill_mask(data, n)
        self.train_episode_mask = self._make_train_episode_mask()
        self.indices = self._build_indices(self.split)

    def _make_row_distill_mask(self, data: np.lib.npyio.NpzFile, n_rows: int) -> np.ndarray | None:
        mode = self.distill_mask_mode
        if mode in {"", "none", "off", "false"}:
            return None
        if mode == "all":
            return np.ones((int(n_rows),), dtype=np.float32)
        if mode != "normal_reset":
            raise ValueError(
                "distill_mask_mode must be one of 'none', 'all', or 'normal_reset', "
                f"got {mode!r}"
            )
        required = ["rollout_reset_joint_blend_alpha", "rollout_reset_cube_pos_blend_alpha"]
        missing = [key for key in required if key not in data.files]
        if missing:
            raise KeyError(
                f"{self.dataset_path} missing {missing}; required for distill_mask_mode='normal_reset'"
            )
        joint_alpha = np.asarray(data["rollout_reset_joint_blend_alpha"], dtype=np.float32).reshape(-1)
        cube_alpha = np.asarray(data["rollout_reset_cube_pos_blend_alpha"], dtype=np.float32).reshape(-1)
        n_eps = int(self.episode_ends.shape[0])
        if joint_alpha.shape[0] != n_eps or cube_alpha.shape[0] != n_eps:
            raise ValueError(
                "reset alpha metadata must have one row per episode: "
                f"joint={joint_alpha.shape}, cube={cube_alpha.shape}, episodes={n_eps}"
            )
        tol = float(self.distill_mask_tolerance)
        episode_mask = (
            np.isfinite(joint_alpha)
            & np.isfinite(cube_alpha)
            & (np.abs(joint_alpha) <= tol)
            & (np.abs(cube_alpha) <= tol)
        )
        row_mask = np.zeros((int(n_rows),), dtype=np.float32)
        for keep, start, end in zip(episode_mask, self.episode_starts, self.episode_ends):
            if bool(keep):
                row_mask[int(start) : int(end)] = 1.0
        return row_mask

    def _make_train_episode_mask(self) -> np.ndarray:
        n_eps = int(self.episode_ends.shape[0])
        rng = np.random.default_rng(self.seed)
        if self.val_ratio <= 0.0 or n_eps == 1:
            train_mask = np.ones(n_eps, dtype=bool)
        else:
            val_count = min(max(1, round(n_eps * min(max(self.val_ratio, 0.0), 1.0))), n_eps - 1)
            val_ids = rng.choice(n_eps, size=val_count, replace=False)
            train_mask = np.ones(n_eps, dtype=bool)
            train_mask[val_ids] = False
        if self.max_train_episodes is not None and int(self.max_train_episodes) < int(train_mask.sum()):
            train_ids = np.nonzero(train_mask)[0]
            keep = rng.choice(train_ids, size=int(self.max_train_episodes), replace=False)
            new_mask = np.zeros_like(train_mask)
            new_mask[keep] = True
            train_mask = new_mask
        return train_mask

    def _build_indices(self, split: str) -> list[tuple[int, int, int]]:
        if split not in {"train", "val", "all"}:
            raise ValueError(f"Unsupported split {split!r}")
        indices: list[tuple[int, int, int]] = []
        for ep_idx, (start, end) in enumerate(zip(self.episode_starts, self.episode_ends)):
            if split == "train" and not self.train_episode_mask[ep_idx]:
                continue
            if split == "val" and self.train_episode_mask[ep_idx]:
                continue
            for t in range(int(start), int(end)):
                indices.append((int(start), int(end), int(t)))
        return indices

    def get_validation_dataset(self):
        val_set = copy.copy(self)
        val_set.split = "val"
        val_set.indices = self._build_indices("val")
        return val_set

    def get_normalizer(self, **kwargs):
        if LinearNormalizer is None or SingleFieldLinearNormalizer is None or get_image_range_normalizer is None:
            raise ImportError(
                "diffusion_policy is not installed; install real-stanford/diffusion_policy "
                "to use get_normalizer in the official workspace."
            )
        if self.normalizer_checkpoint is not None:
            normalizer = _linear_normalizer_from_checkpoint(self.normalizer_checkpoint)
            expected = {self.obs_image_name, self.obs_robot_state_name, "action"}
            missing = expected.difference(normalizer.params_dict.keys())
            if missing:
                raise KeyError(
                    f"Normalizer checkpoint {self.normalizer_checkpoint} is missing fields {sorted(missing)}"
                )
            robot_scale = normalizer.params_dict[self.obs_robot_state_name]["scale"]
            action_scale = normalizer.params_dict["action"]["scale"]
            if int(robot_scale.numel()) != int(self.robot_state.shape[1]):
                raise ValueError(
                    f"Reference normalizer robot_state dim {robot_scale.numel()} "
                    f"does not match dataset dim {self.robot_state.shape[1]}"
                )
            if int(action_scale.numel()) != int(self.action.shape[1]):
                raise ValueError(
                    f"Reference normalizer action dim {action_scale.numel()} "
                    f"does not match dataset dim {self.action.shape[1]}"
                )
            return normalizer
        normalizer = LinearNormalizer()
        normalizer[self.obs_image_name] = get_image_range_normalizer()
        normalizer[self.obs_robot_state_name] = SingleFieldLinearNormalizer.create_fit(
            self.robot_state,
            last_n_dims=1,
            mode=kwargs.get("robot_state_mode", "limits"),
            output_max=1.0,
            output_min=-1.0,
        )
        if self.action_normalizer == "identity":
            stat = array_to_stats(self.action)
            normalizer["action"] = get_identity_normalizer_from_stat(stat)
        elif self.action_normalizer == "limits":
            normalizer["action"] = SingleFieldLinearNormalizer.create_fit(
                self.action,
                last_n_dims=1,
                mode="limits",
                output_max=1.0,
                output_min=-1.0,
            )
        elif self.action_normalizer == "limits_clamp_constant":
            normalizer["action"] = _create_limits_clamp_constant_action_normalizer(self.action)
        else:
            raise ValueError(f"Unsupported action_normalizer {self.action_normalizer!r}")
        return normalizer

    def get_all_actions(self) -> torch.Tensor:
        return torch.from_numpy(self.action)

    def __len__(self) -> int:
        return len(self.indices)

    def _image_chw_float(self, frame_ids: np.ndarray) -> np.ndarray:
        image = self.image[frame_ids]
        if self.image_layout == "nhwc":
            image = np.moveaxis(image, -1, 1)
        image = image.astype(np.float32, copy=False)
        if image.max(initial=0.0) > 1.0:
            image = image / 255.0
        return image

    def __getitem__(self, idx: int) -> dict[str, Any]:
        ep_start, ep_end, center = self.indices[idx]
        seq_start = center - self.pad_before
        frame_ids = np.arange(seq_start, seq_start + self.horizon, dtype=np.int64)
        frame_ids = np.clip(frame_ids, ep_start, ep_end - 1)
        sample = {
            "obs": {
                self.obs_image_name: torch.from_numpy(self._image_chw_float(frame_ids)),
                self.obs_robot_state_name: torch.from_numpy(self.robot_state[frame_ids]),
            },
            "action": torch.from_numpy(self.action[frame_ids]),
        }
        if self.row_distill_mask is not None:
            sample["distill_mask"] = torch.from_numpy(self.row_distill_mask[frame_ids])
        return sample


class YamRgbShardedDataset(BaseImageDataset):
    """Manifest-backed two-camera YAM RGB dataset for image Diffusion Policy.

    The manifest is produced by ``make_yam_rgb_policy_shards.py``.  Each shard
    is one episode with only non-privileged policy fields:
    ``scene_rgb``, ``wrist_rgb``, ``robot_state``, ``action``, and
    ``episode_ends``.
    """

    def __init__(
        self,
        manifest_path: str,
        horizon: int = 16,
        pad_before: int = 0,
        pad_after: int = 15,
        seed: int = 42,
        val_ratio: float = 0.0,
        max_train_episodes: int | None = None,
        split: str = "train",
        action_normalizer: str = "limits_clamp_constant",
        image_keys: list[str] | tuple[str, ...] = ("scene_rgb", "wrist_rgb"),
        robot_state_key: str = "robot_state",
        obs_robot_state_name: str = "robot_state",
        normalizer_checkpoint: str | None = None,
    ):
        super().__init__()
        self.manifest_path = str(manifest_path)
        self.horizon = int(horizon)
        self.pad_before = int(pad_before)
        self.pad_after = int(pad_after)
        self.seed = int(seed)
        self.val_ratio = float(val_ratio)
        self.max_train_episodes = max_train_episodes
        self.split = str(split)
        self.action_normalizer = str(action_normalizer)
        self.image_keys = tuple(str(k) for k in image_keys)
        self.robot_state_key = str(robot_state_key)
        self.obs_robot_state_name = str(obs_robot_state_name)
        self.normalizer_checkpoint = None if normalizer_checkpoint in (None, "") else str(normalizer_checkpoint)
        if not self.image_keys:
            raise ValueError("image_keys must not be empty")

        manifest_file = Path(self.manifest_path).expanduser().resolve()
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
        raw_shards = payload.get("shards")
        if not isinstance(raw_shards, list) or not raw_shards:
            raise ValueError(f"{manifest_file} has no shards")
        self.shard_paths = [
            (Path(str(row["path"])) if Path(str(row["path"])).is_absolute() else manifest_file.parent / str(row["path"]))
            for row in raw_shards
        ]
        self.shard_paths = [path.expanduser().resolve() for path in self.shard_paths]
        for path in self.shard_paths:
            if not path.is_file():
                raise FileNotFoundError(path)

        self._shard_lengths: list[int] = []
        robot_parts: list[np.ndarray] = []
        action_parts: list[np.ndarray] = []
        for path in self.shard_paths:
            with np.load(path, allow_pickle=False) as data:
                robot = np.asarray(data[self.robot_state_key], dtype=np.float32)
                action = np.asarray(data["action"], dtype=np.float32)
                if robot.ndim != 2:
                    raise ValueError(f"{path}: robot_state must be rank 2, got {robot.shape}")
                if action.ndim != 2 or action.shape[1] != 7:
                    raise ValueError(f"{path}: action must be (N,7), got {action.shape}")
                if robot.shape[0] != action.shape[0]:
                    raise ValueError(f"{path}: robot/action length mismatch {robot.shape} vs {action.shape}")
                for key in self.image_keys:
                    image = np.asarray(data[key])
                    if image.ndim != 4:
                        raise ValueError(f"{path}: {key} must be rank 4, got {image.shape}")
                    if image.shape[0] != action.shape[0]:
                        raise ValueError(f"{path}: {key} length {image.shape[0]} != action length {action.shape[0]}")
                self._shard_lengths.append(int(action.shape[0]))
                robot_parts.append(robot)
                action_parts.append(action)
        self.robot_state = np.concatenate(robot_parts, axis=0).astype(np.float32, copy=False)
        self.action = np.concatenate(action_parts, axis=0).astype(np.float32, copy=False)
        self.episode_ends = np.cumsum(np.asarray(self._shard_lengths, dtype=np.int64))
        self.episode_starts = np.concatenate(([0], self.episode_ends[:-1])).astype(np.int64)
        self.train_episode_mask = self._make_train_episode_mask()
        self.indices = self._build_indices(self.split)
        self._cache_shard_idx: int | None = None
        self._cache_data: dict[str, np.ndarray] | None = None

    def _make_train_episode_mask(self) -> np.ndarray:
        n_eps = int(len(self.shard_paths))
        rng = np.random.default_rng(self.seed)
        if self.val_ratio <= 0.0 or n_eps == 1:
            train_mask = np.ones(n_eps, dtype=bool)
        else:
            val_count = min(max(1, round(n_eps * min(max(self.val_ratio, 0.0), 1.0))), n_eps - 1)
            val_ids = rng.choice(n_eps, size=val_count, replace=False)
            train_mask = np.ones(n_eps, dtype=bool)
            train_mask[val_ids] = False
        if self.max_train_episodes is not None and int(self.max_train_episodes) < int(train_mask.sum()):
            train_ids = np.nonzero(train_mask)[0]
            keep = rng.choice(train_ids, size=int(self.max_train_episodes), replace=False)
            new_mask = np.zeros_like(train_mask)
            new_mask[keep] = True
            train_mask = new_mask
        return train_mask

    def _build_indices(self, split: str) -> list[tuple[int, int]]:
        if split not in {"train", "val", "all"}:
            raise ValueError(f"Unsupported split {split!r}")
        indices: list[tuple[int, int]] = []
        for ep_idx, length in enumerate(self._shard_lengths):
            if split == "train" and not self.train_episode_mask[ep_idx]:
                continue
            if split == "val" and self.train_episode_mask[ep_idx]:
                continue
            for local_t in range(int(length)):
                indices.append((int(ep_idx), int(local_t)))
        return indices

    def get_validation_dataset(self):
        val_set = copy.copy(self)
        val_set.split = "val"
        val_set.indices = self._build_indices("val")
        val_set._cache_shard_idx = None
        val_set._cache_data = None
        return val_set

    def get_normalizer(self, **kwargs):
        if LinearNormalizer is None or SingleFieldLinearNormalizer is None or get_image_range_normalizer is None:
            raise ImportError(
                "diffusion_policy is not installed; install real-stanford/diffusion_policy "
                "to use get_normalizer in the official workspace."
            )
        if self.normalizer_checkpoint is not None:
            normalizer = _linear_normalizer_from_checkpoint(self.normalizer_checkpoint)
            expected = set(self.image_keys).union({self.obs_robot_state_name, "action"})
            missing = expected.difference(normalizer.params_dict.keys())
            if missing:
                raise KeyError(
                    f"Normalizer checkpoint {self.normalizer_checkpoint} is missing fields {sorted(missing)}"
                )
            robot_scale = normalizer.params_dict[self.obs_robot_state_name]["scale"]
            action_scale = normalizer.params_dict["action"]["scale"]
            if int(robot_scale.numel()) != int(self.robot_state.shape[1]):
                raise ValueError(
                    f"Reference normalizer robot_state dim {robot_scale.numel()} "
                    f"does not match dataset dim {self.robot_state.shape[1]}"
                )
            if int(action_scale.numel()) != int(self.action.shape[1]):
                raise ValueError(
                    f"Reference normalizer action dim {action_scale.numel()} "
                    f"does not match dataset dim {self.action.shape[1]}"
                )
            return normalizer
        normalizer = LinearNormalizer()
        for key in self.image_keys:
            normalizer[key] = get_image_range_normalizer()
        normalizer[self.obs_robot_state_name] = SingleFieldLinearNormalizer.create_fit(
            self.robot_state,
            last_n_dims=1,
            mode=kwargs.get("robot_state_mode", "limits"),
            output_max=1.0,
            output_min=-1.0,
        )
        if self.action_normalizer == "identity":
            stat = array_to_stats(self.action)
            normalizer["action"] = get_identity_normalizer_from_stat(stat)
        elif self.action_normalizer == "limits":
            normalizer["action"] = SingleFieldLinearNormalizer.create_fit(
                self.action,
                last_n_dims=1,
                mode="limits",
                output_max=1.0,
                output_min=-1.0,
            )
        elif self.action_normalizer == "limits_clamp_constant":
            normalizer["action"] = _create_limits_clamp_constant_action_normalizer(self.action)
        else:
            raise ValueError(f"Unsupported action_normalizer {self.action_normalizer!r}")
        return normalizer

    def get_all_actions(self) -> torch.Tensor:
        return torch.from_numpy(self.action)

    def __len__(self) -> int:
        return len(self.indices)

    def _load_shard(self, shard_idx: int) -> dict[str, np.ndarray]:
        if self._cache_shard_idx == int(shard_idx) and self._cache_data is not None:
            return self._cache_data
        path = self.shard_paths[int(shard_idx)]
        with np.load(path, allow_pickle=False) as data:
            loaded = {
                key: np.asarray(data[key])
                for key in (*self.image_keys, self.robot_state_key, "action")
            }
        self._cache_shard_idx = int(shard_idx)
        self._cache_data = loaded
        return loaded

    @staticmethod
    def _image_chw_float(image: np.ndarray, frame_ids: np.ndarray) -> np.ndarray:
        frames = np.asarray(image[frame_ids])
        if frames.ndim != 4:
            raise ValueError(f"image frames must be rank 4, got {frames.shape}")
        if frames.shape[-1] == 3:
            frames = np.moveaxis(frames, -1, 1)
        elif frames.shape[1] != 3:
            raise ValueError(f"image must be NHWC or NCHW RGB, got {frames.shape}")
        frames = frames.astype(np.float32, copy=False)
        if frames.max(initial=0.0) > 1.0:
            frames = frames / 255.0
        return frames

    def __getitem__(self, idx: int) -> dict[str, Any]:
        shard_idx, center = self.indices[idx]
        length = int(self._shard_lengths[shard_idx])
        seq_start = int(center) - self.pad_before
        frame_ids = np.arange(seq_start, seq_start + self.horizon, dtype=np.int64)
        frame_ids = np.clip(frame_ids, 0, length - 1)
        shard = self._load_shard(shard_idx)
        obs = {
            key: torch.from_numpy(self._image_chw_float(shard[key], frame_ids))
            for key in self.image_keys
        }
        obs[self.obs_robot_state_name] = torch.from_numpy(
            np.asarray(shard[self.robot_state_key], dtype=np.float32)[frame_ids]
        )
        return {
            "obs": obs,
            "action": torch.from_numpy(np.asarray(shard["action"], dtype=np.float32)[frame_ids]),
        }


class NoopLowdimRunner(BaseLowdimRunner):
    """Offline-BC env runner for official Diffusion Policy training.

    This avoids simulator rollouts during BC while still satisfying the
    official workspace contract. It returns the monitor key used by the
    official low-dimensional configs after slash-to-underscore sanitization.
    """

    def __init__(self, output_dir=None, metric_prefix: str = "test", **_: Any):
        if BaseLowdimRunner is object:
            self.output_dir = output_dir
        else:
            super().__init__(output_dir=output_dir)
        self.metric_prefix = metric_prefix

    def run(self, policy) -> dict[str, float]:
        return {
            f"{self.metric_prefix}/mean_score": 0.0,
            f"{self.metric_prefix}_mean_score": 0.0,
        }


class NoopImageRunner(BaseImageRunner):
    """Offline-BC env runner for official image Diffusion Policy training."""

    def __init__(self, output_dir=None, metric_prefix: str = "test", **_: Any):
        if BaseImageRunner is object:
            self.output_dir = output_dir
        else:
            super().__init__(output_dir=output_dir)
        self.metric_prefix = metric_prefix

    def run(self, policy) -> dict[str, float]:
        return {
            f"{self.metric_prefix}/mean_score": 0.0,
            f"{self.metric_prefix}_mean_score": 0.0,
        }
