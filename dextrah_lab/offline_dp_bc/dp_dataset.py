"""Official Diffusion Policy dataset adapter for DEXTRAH lowdim demos."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch

try:
    from diffusion_policy.common.normalize_util import array_to_stats, get_identity_normalizer_from_stat
    from diffusion_policy.dataset.base_dataset import BaseLowdimDataset
    from diffusion_policy.env_runner.base_lowdim_runner import BaseLowdimRunner
    from diffusion_policy.model.common.normalizer import LinearNormalizer, SingleFieldLinearNormalizer
except Exception:  # pragma: no cover - exercised in environments without official DP installed.
    BaseLowdimDataset = torch.utils.data.Dataset
    BaseLowdimRunner = object
    LinearNormalizer = None
    SingleFieldLinearNormalizer = None
    array_to_stats = None
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
        return {f"{self.metric_prefix}/mean_score": 0.0}
