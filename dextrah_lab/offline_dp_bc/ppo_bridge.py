"""Bridge helpers from Franka cube PPO observations to lowdim DP observations.

This module is intentionally small. A Diffusion Policy checkpoint cannot be
loaded directly into the current rl_games PPO actor because the architectures
and observation histories differ. The bridge here supports two safer paths:

1. Evaluate a trained lowdim DP policy in the Franka cube env by extracting the
   compact observation fields from the existing 72D PPO observation and keeping
   the two-step observation history expected by the DP config.
2. Distill DP actions into a PPO-compatible actor by using this same extractor
   to query the DP teacher while training a separate 72D-observation student.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


FRANKA_CUBE_PPO_OBS_DIM = 72
FRANKA_CUBE_LOWDIM_OBS_DIM = 21
FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM = 25
FRANKA_CUBE_ACTION_DIM = 7
PHASE_PROGRESS_FEATURE_NAMES = (
    "phase_align_open",
    "phase_close_hold",
    "phase_lift",
    "episode_progress",
)
PHASE_PROGRESS_FEATURE_DIM = len(PHASE_PROGRESS_FEATURE_NAMES)
PHASE_PROGRESS_SUPPORT_FEATURE_IDX = np.asarray(
    [0, 1, 2, 7, 8, 9, 14, 15, 16, 17, 18, 19, 20],
    dtype=np.int64,
)
CONTACT_PHASE_NAME_BY_ID = {
    0: "align_open",
    1: "close_hold",
    2: "lift",
}


@dataclass(frozen=True)
class FrankaCubePpoObsSlices:
    ee_pos: slice = field(default_factory=lambda: slice(18, 21))
    ee_quat: slice = field(default_factory=lambda: slice(21, 25))
    cube_pos: slice = field(default_factory=lambda: slice(31, 34))
    cube_quat: slice = field(default_factory=lambda: slice(34, 38))
    cube_minus_ee: slice = field(default_factory=lambda: slice(47, 50))
    cube_goal_delta: slice = field(default_factory=lambda: slice(50, 53))
    gripper_width: int = 59


DEFAULT_PPO_OBS_SLICES = FrankaCubePpoObsSlices()


def _is_torch_tensor(value: Any) -> bool:
    return hasattr(value, "detach") and hasattr(value, "reshape") and value.__class__.__module__.startswith("torch")


def _as_numpy(value: Any) -> np.ndarray:
    if _is_torch_tensor(value):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def extract_lowdim_obs_from_ppo_obs(
    ppo_obs: Any,
    *,
    slices: FrankaCubePpoObsSlices = DEFAULT_PPO_OBS_SLICES,
) -> Any:
    """Extract the 21D DP lowdim observation from DEXTRAH's 72D PPO obs.

    Supports NumPy arrays and torch tensors with shape ``(..., 72)``. The
    returned type matches the input type.
    """

    if ppo_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
        raise ValueError(f"Expected last dim {FRANKA_CUBE_PPO_OBS_DIM}, got {ppo_obs.shape[-1]}")
    parts = [
        ppo_obs[..., slices.ee_pos],
        ppo_obs[..., slices.ee_quat],
        ppo_obs[..., slices.cube_pos],
        ppo_obs[..., slices.cube_quat],
        ppo_obs[..., slices.cube_minus_ee],
        ppo_obs[..., slices.cube_goal_delta],
        ppo_obs[..., slices.gripper_width : slices.gripper_width + 1],
    ]
    if _is_torch_tensor(ppo_obs):
        import torch

        out = torch.cat(parts, dim=-1)
    else:
        out = np.concatenate(parts, axis=-1)
    if out.shape[-1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
        raise RuntimeError(f"Lowdim extraction produced {out.shape[-1]} dims")
    return out


def embed_lowdim_obs_in_ppo_obs(
    lowdim_obs: Any,
    *,
    base_ppo_obs: Any | None = None,
    slices: FrankaCubePpoObsSlices = DEFAULT_PPO_OBS_SLICES,
) -> Any:
    """Place a 21D lowdim obs into the matching slots of a 72D PPO obs.

    This is a smoke-test and distillation helper. Fields not present in the
    lowdim schema, such as joint state and reward-shaping scalars, are left as
    zeros or copied from ``base_ppo_obs``.
    """

    if lowdim_obs.shape[-1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
        raise ValueError(f"Expected lowdim dim {FRANKA_CUBE_LOWDIM_OBS_DIM}, got {lowdim_obs.shape[-1]}")
    if base_ppo_obs is None:
        shape = lowdim_obs.shape[:-1] + (FRANKA_CUBE_PPO_OBS_DIM,)
        if _is_torch_tensor(lowdim_obs):
            import torch

            ppo_obs = torch.zeros(shape, dtype=lowdim_obs.dtype, device=lowdim_obs.device)
        else:
            ppo_obs = np.zeros(shape, dtype=np.asarray(lowdim_obs).dtype)
    else:
        ppo_obs = base_ppo_obs.clone() if _is_torch_tensor(base_ppo_obs) else np.array(base_ppo_obs, copy=True)
        if ppo_obs.shape[-1] != FRANKA_CUBE_PPO_OBS_DIM:
            raise ValueError(f"Expected base PPO dim {FRANKA_CUBE_PPO_OBS_DIM}, got {ppo_obs.shape[-1]}")

    cursor = 0
    ppo_obs[..., slices.ee_pos] = lowdim_obs[..., cursor : cursor + 3]
    cursor += 3
    ppo_obs[..., slices.ee_quat] = lowdim_obs[..., cursor : cursor + 4]
    cursor += 4
    ppo_obs[..., slices.cube_pos] = lowdim_obs[..., cursor : cursor + 3]
    cursor += 3
    ppo_obs[..., slices.cube_quat] = lowdim_obs[..., cursor : cursor + 4]
    cursor += 4
    ppo_obs[..., slices.cube_minus_ee] = lowdim_obs[..., cursor : cursor + 3]
    cursor += 3
    ppo_obs[..., slices.cube_goal_delta] = lowdim_obs[..., cursor : cursor + 3]
    cursor += 3
    ppo_obs[..., slices.gripper_width : slices.gripper_width + 1] = lowdim_obs[..., cursor : cursor + 1]
    return ppo_obs


class LowdimObsHistory:
    """Fixed-length lowdim observation history for DP policy inference."""

    def __init__(self, num_envs: int, n_obs_steps: int = 2, obs_dim: int = FRANKA_CUBE_LOWDIM_OBS_DIM):
        self.num_envs = int(num_envs)
        self.n_obs_steps = int(n_obs_steps)
        self.obs_dim = int(obs_dim)
        self._history = np.zeros((self.num_envs, self.n_obs_steps, self.obs_dim), dtype=np.float32)
        self._step_history = np.full((self.num_envs, self.n_obs_steps), -1, dtype=np.int64)
        self._filled = np.zeros(self.num_envs, dtype=np.int32)

    def reset(self, env_ids: np.ndarray | list[int] | None = None) -> None:
        if env_ids is None:
            self._history[...] = 0.0
            self._step_history[...] = -1
            self._filled[...] = 0
        else:
            env_ids_arr = np.asarray(env_ids, dtype=np.int64)
            self._history[env_ids_arr] = 0.0
            self._step_history[env_ids_arr] = -1
            self._filled[env_ids_arr] = 0

    def push(self, lowdim_obs: np.ndarray, *, step: int | np.ndarray | None = None) -> np.ndarray:
        lowdim_obs = np.asarray(lowdim_obs, dtype=np.float32)
        if lowdim_obs.shape != (self.num_envs, self.obs_dim):
            raise ValueError(f"Expected lowdim obs {(self.num_envs, self.obs_dim)}, got {lowdim_obs.shape}")
        if step is None:
            step_values = self._step_history[:, -1].copy()
        elif np.isscalar(step):
            step_values = np.full(self.num_envs, int(step), dtype=np.int64)
        else:
            step_values = np.asarray(step, dtype=np.int64)
            if step_values.shape != (self.num_envs,):
                raise ValueError(f"Expected step shape {(self.num_envs,)}, got {step_values.shape}")
        self._history[:, :-1] = self._history[:, 1:]
        self._history[:, -1] = lowdim_obs
        self._step_history[:, :-1] = self._step_history[:, 1:]
        self._step_history[:, -1] = step_values
        not_filled = self._filled < self.n_obs_steps
        if np.any(not_filled):
            self._history[not_filled] = lowdim_obs[not_filled, None, :]
            self._step_history[not_filled] = step_values[not_filled, None]
        self._filled = np.minimum(self._filled + 1, self.n_obs_steps)
        return self._history.copy()


@dataclass(frozen=True)
class DatasetBackedPhaseProgressProvider:
    """Append offline phase/progress features from a generated 25D NPZ.

    This is a narrow bridge for the phase/progress diagnostic checkpoint. It
    uses an accepted relabel episode's stored feature columns as a deterministic
    runtime schedule. It does not infer task phase from arbitrary live state.
    """

    dataset_path: str
    episode_index: int
    episode_start: int
    episode_end: int
    start_step: int
    features: np.ndarray
    feature_names: tuple[str, ...] = PHASE_PROGRESS_FEATURE_NAMES

    @classmethod
    def from_npz(cls, path: str | Path, *, episode_index: int = 0, start_step: int = 0) -> "DatasetBackedPhaseProgressProvider":
        dataset_path = Path(path).expanduser().resolve()
        data = np.load(dataset_path, allow_pickle=False)
        obs = np.asarray(data["obs"], dtype=np.float32)
        episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
        if obs.ndim != 2 or obs.shape[1] < FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM:
            raise ValueError(
                f"Expected phase/progress obs shape (N,{FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM}) or wider, got {obs.shape}"
            )
        if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(obs.shape[0]):
            raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")
        episode_index = int(episode_index)
        if episode_index < 0 or episode_index >= int(episode_ends.size):
            raise ValueError(f"episode_index must be in [0,{episode_ends.size}), got {episode_index}")
        episode_start = 0 if episode_index == 0 else int(episode_ends[episode_index - 1])
        episode_end = int(episode_ends[episode_index])
        start_step = int(start_step)
        if start_step < 0 or start_step >= episode_end - episode_start:
            raise ValueError(
                f"start_step must be in [0,{episode_end - episode_start}), got {start_step}"
            )
        if "phase_progress_features" in data.files:
            names = tuple(str(v) for v in np.asarray(data["phase_progress_features"]).tolist())
            if names != PHASE_PROGRESS_FEATURE_NAMES:
                raise ValueError(f"Unexpected phase/progress feature names: {names}")
        else:
            names = PHASE_PROGRESS_FEATURE_NAMES
        features = obs[:, FRANKA_CUBE_LOWDIM_OBS_DIM:FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM].astype(np.float32, copy=True)
        return cls(
            dataset_path=str(dataset_path),
            episode_index=episode_index,
            episode_start=episode_start,
            episode_end=episode_end,
            start_step=start_step,
            features=features,
            feature_names=names,
        )

    @property
    def obs_dim(self) -> int:
        return FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM

    def row_indices_for_step(self, step: int | np.ndarray, num_envs: int) -> np.ndarray:
        if np.isscalar(step) or step is None:
            step_values = np.full(num_envs, 0 if step is None else int(step), dtype=np.int64)
        else:
            step_values = np.asarray(step, dtype=np.int64)
            if step_values.shape != (num_envs,):
                raise ValueError(f"Expected step shape {(num_envs,)}, got {step_values.shape}")
        rows = int(self.episode_start + self.start_step) + step_values
        return np.clip(rows, int(self.episode_start), int(self.episode_end) - 1).astype(np.int64)

    def features_for_step(self, step: int | np.ndarray, num_envs: int) -> np.ndarray:
        return self.features[self.row_indices_for_step(step, num_envs)].astype(np.float32, copy=True)

    def augment_lowdim(self, lowdim_obs: np.ndarray, *, step: int | np.ndarray | None = None) -> np.ndarray:
        lowdim_obs = np.asarray(lowdim_obs, dtype=np.float32)
        if lowdim_obs.ndim != 2 or lowdim_obs.shape[1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
            raise ValueError(f"Expected lowdim obs (N,{FRANKA_CUBE_LOWDIM_OBS_DIM}), got {lowdim_obs.shape}")
        features = self.features_for_step(0 if step is None else step, int(lowdim_obs.shape[0]))
        return np.concatenate((lowdim_obs, features), axis=1).astype(np.float32)

    def summary(self) -> dict[str, Any]:
        return {
            "mode": "dataset",
            "dataset_path": self.dataset_path,
            "episode_index": int(self.episode_index),
            "episode_start": int(self.episode_start),
            "episode_end": int(self.episode_end),
            "start_step": int(self.start_step),
            "feature_names": list(self.feature_names),
            "obs_dim": int(self.obs_dim),
        }


class ContactGatedPhaseProgressProvider:
    """Dataset-backed phase/progress provider with live-geometry gating.

    The generated 25D dataset uses a deterministic episode clock. That is
    useful offline but unsafe in closed loop: the policy can see close/lift
    features before the live EE/cube state reaches close/lift support. This
    provider keeps the dataset progress schedule but only allows close/lift
    one-hot phases when the current 21D lowdim state is near that phase's
    support in the selected relabel dataset episode.
    """

    def __init__(
        self,
        *,
        dataset_path: str | Path,
        episode_index: int = 0,
        start_step: int = 0,
        close_support_distance_threshold: float = 0.55,
        lift_support_distance_threshold: float = 0.75,
        lift_gripper_width_threshold: float = 0.025,
    ) -> None:
        dataset_path = Path(dataset_path).expanduser().resolve()
        data = np.load(dataset_path, allow_pickle=False)
        obs = np.asarray(data["obs"], dtype=np.float32)
        episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
        phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
        if obs.ndim != 2 or obs.shape[1] < FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM:
            raise ValueError(
                f"Expected phase/progress obs shape (N,{FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM}) or wider, got {obs.shape}"
            )
        unique = set(int(v) for v in np.unique(phase_ids))
        if not unique.issubset({0, 1, 2}):
            raise ValueError(f"Contact-gated provider expects phase ids in {{0,1,2}}, got {sorted(unique)}")
        if episode_ends.ndim != 1 or episode_ends.size == 0 or int(episode_ends[-1]) != int(obs.shape[0]):
            raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")
        episode_index = int(episode_index)
        if episode_index < 0 or episode_index >= int(episode_ends.size):
            raise ValueError(f"episode_index must be in [0,{episode_ends.size}), got {episode_index}")
        episode_start = 0 if episode_index == 0 else int(episode_ends[episode_index - 1])
        episode_end = int(episode_ends[episode_index])
        start_step = int(start_step)
        if start_step < 0 or start_step >= episode_end - episode_start:
            raise ValueError(f"start_step must be in [0,{episode_end - episode_start}), got {start_step}")
        if "phase_progress_features" in data.files:
            names = tuple(str(v) for v in np.asarray(data["phase_progress_features"]).tolist())
            if names != PHASE_PROGRESS_FEATURE_NAMES:
                raise ValueError(f"Unexpected phase/progress feature names: {names}")
        else:
            names = PHASE_PROGRESS_FEATURE_NAMES

        self.dataset_path = str(dataset_path)
        self.episode_index = episode_index
        self.episode_start = episode_start
        self.episode_end = episode_end
        self.start_step = start_step
        self.feature_names = names
        self.base_obs = obs[:, :FRANKA_CUBE_LOWDIM_OBS_DIM].astype(np.float32, copy=True)
        self.features = obs[:, FRANKA_CUBE_LOWDIM_OBS_DIM:FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM].astype(
            np.float32, copy=True
        )
        self.phase_ids = phase_ids.astype(np.int32, copy=True)
        self.close_support_distance_threshold = float(close_support_distance_threshold)
        self.lift_support_distance_threshold = float(lift_support_distance_threshold)
        self.lift_gripper_width_threshold = float(lift_gripper_width_threshold)

        episode_rows = np.arange(episode_start, episode_end, dtype=np.int64)
        support = self.base_obs[episode_rows][:, PHASE_PROGRESS_SUPPORT_FEATURE_IDX]
        self._episode_rows = episode_rows
        self._support_std = np.maximum(support.std(axis=0), 1.0e-4).astype(np.float32)
        self._phase_bounds: dict[int, tuple[int, int]] = {}
        for phase_id in (0, 1, 2):
            phase_rows = episode_rows[self.phase_ids[episode_rows] == phase_id]
            if phase_rows.size:
                self._phase_bounds[phase_id] = (int(phase_rows[0]), int(phase_rows[-1]) + 1)

    @property
    def obs_dim(self) -> int:
        return FRANKA_CUBE_PHASE_PROGRESS_OBS_DIM

    def row_indices_for_step(self, step: int | np.ndarray, num_envs: int) -> np.ndarray:
        if np.isscalar(step) or step is None:
            step_values = np.full(num_envs, 0 if step is None else int(step), dtype=np.int64)
        else:
            step_values = np.asarray(step, dtype=np.int64)
            if step_values.shape != (num_envs,):
                raise ValueError(f"Expected step shape {(num_envs,)}, got {step_values.shape}")
        rows = int(self.episode_start + self.start_step) + step_values
        return np.clip(rows, int(self.episode_start), int(self.episode_end) - 1).astype(np.int64)

    def _phase_min_distances(self, lowdim_obs: np.ndarray) -> np.ndarray:
        query = lowdim_obs[PHASE_PROGRESS_SUPPORT_FEATURE_IDX].astype(np.float32)
        distances = np.sqrt((((self.base_obs[:, PHASE_PROGRESS_SUPPORT_FEATURE_IDX] - query) / self._support_std) ** 2).mean(axis=1))
        out = np.full(3, np.inf, dtype=np.float32)
        for phase_id in (0, 1, 2):
            rows = self._episode_rows[self.phase_ids[self._episode_rows] == phase_id]
            if rows.size:
                out[phase_id] = float(np.min(distances[rows]))
        return out

    def _features_for_phase(self, phase_id: int, schedule_row: int) -> np.ndarray:
        start, end = self._phase_bounds.get(int(phase_id), (self.episode_start, self.episode_end))
        progress_row = int(np.clip(schedule_row, start, end - 1))
        feature = np.zeros(PHASE_PROGRESS_FEATURE_DIM, dtype=np.float32)
        feature[int(phase_id)] = 1.0
        feature[3] = float(self.features[progress_row, 3])
        return feature

    def augment_lowdim(self, lowdim_obs: np.ndarray, *, step: int | np.ndarray | None = None) -> np.ndarray:
        lowdim_obs = np.asarray(lowdim_obs, dtype=np.float32)
        if lowdim_obs.ndim != 2 or lowdim_obs.shape[1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
            raise ValueError(f"Expected lowdim obs (N,{FRANKA_CUBE_LOWDIM_OBS_DIM}), got {lowdim_obs.shape}")
        rows = self.row_indices_for_step(0 if step is None else step, int(lowdim_obs.shape[0]))
        features = np.zeros((lowdim_obs.shape[0], PHASE_PROGRESS_FEATURE_DIM), dtype=np.float32)
        for env_idx, schedule_row in enumerate(rows):
            schedule_phase = int(np.argmax(self.features[int(schedule_row), :3]))
            phase_distances = self._phase_min_distances(lowdim_obs[env_idx])
            close_allowed = bool(phase_distances[1] <= self.close_support_distance_threshold)
            lift_allowed = bool(
                close_allowed
                and schedule_phase >= 2
                and phase_distances[2] <= self.lift_support_distance_threshold
                and float(lowdim_obs[env_idx, 20]) <= self.lift_gripper_width_threshold
            )
            if schedule_phase >= 2 and lift_allowed:
                chosen_phase = 2
            elif schedule_phase >= 1 and close_allowed:
                chosen_phase = 1
            else:
                chosen_phase = 0
            features[env_idx] = self._features_for_phase(chosen_phase, int(schedule_row))
        return np.concatenate((lowdim_obs, features), axis=1).astype(np.float32)

    def summary(self) -> dict[str, Any]:
        return {
            "mode": "contact_gated",
            "dataset_path": self.dataset_path,
            "episode_index": int(self.episode_index),
            "episode_start": int(self.episode_start),
            "episode_end": int(self.episode_end),
            "start_step": int(self.start_step),
            "feature_names": list(self.feature_names),
            "obs_dim": int(self.obs_dim),
            "close_support_distance_threshold": float(self.close_support_distance_threshold),
            "lift_support_distance_threshold": float(self.lift_support_distance_threshold),
            "lift_gripper_width_threshold": float(self.lift_gripper_width_threshold),
            "phase_bounds": {
                CONTACT_PHASE_NAME_BY_ID[int(k)]: [int(v[0]), int(v[1])] for k, v in self._phase_bounds.items()
            },
        }


def predict_action_sequence_from_ppo_obs(
    policy: Any,
    ppo_obs: Any,
    history: LowdimObsHistory,
    *,
    step: int | np.ndarray | None = None,
    phase_progress_provider: DatasetBackedPhaseProgressProvider | ContactGatedPhaseProgressProvider | None = None,
    num_action_samples: int = 1,
    gripper_sample_aggregation: str = "mean",
    gripper_close_threshold: float = 0.5,
    gripper_vote_threshold: float = 0.5,
) -> Any:
    """Query an official lowdim DP policy for an action sequence.

    The returned sequence has shape ``(num_envs, n_action_steps, 7)`` in
    DEXTRAH's normalized relative-EE plus gripper convention. This is for
    evaluation wrappers and distillation data collection, not PPO checkpoint
    initialization.
    """

    lowdim = extract_lowdim_obs_from_ppo_obs(ppo_obs)
    lowdim_np = _as_numpy(lowdim).astype(np.float32, copy=False)
    if phase_progress_provider is not None:
        lowdim_np = phase_progress_provider.augment_lowdim(lowdim_np, step=step)
    obs_seq = history.push(lowdim_np, step=step)
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        raise ImportError("predict_action_from_ppo_obs requires torch and an official DP policy") from exc

    device = next(policy.parameters()).device
    obs_tensor = torch.as_tensor(obs_seq, dtype=torch.float32, device=device)
    sample_count = max(1, int(num_action_samples))
    gripper_mode = str(gripper_sample_aggregation)
    if gripper_mode not in {"mean", "binary_vote"}:
        raise ValueError(f"Unsupported gripper_sample_aggregation {gripper_mode!r}")
    close_threshold = float(gripper_close_threshold)
    vote_threshold = float(gripper_vote_threshold)
    if not 0.0 <= vote_threshold <= 1.0:
        raise ValueError(f"gripper_vote_threshold must be in [0, 1], got {vote_threshold}")
    with torch.no_grad():
        if sample_count == 1 and gripper_mode == "mean":
            result = policy.predict_action({"obs": obs_tensor})
            action = result["action"]
        else:
            samples = []
            for _ in range(sample_count):
                result = policy.predict_action({"obs": obs_tensor})
                samples.append(result["action"])
            stacked = torch.stack(samples, dim=0)
            action = stacked.mean(dim=0)
            if gripper_mode == "binary_vote":
                close_votes = stacked[..., 6] < close_threshold
                close_fraction = close_votes.to(dtype=action.dtype).mean(dim=0)
                action[..., 6] = torch.where(
                    close_fraction >= vote_threshold,
                    torch.full_like(action[..., 6], -1.0),
                    torch.full_like(action[..., 6], 1.0),
                )
    return action.detach().cpu().numpy()


def predict_action_from_ppo_obs(
    policy: Any,
    ppo_obs: Any,
    history: LowdimObsHistory,
    *,
    step: int | np.ndarray | None = None,
    phase_progress_provider: DatasetBackedPhaseProgressProvider | ContactGatedPhaseProgressProvider | None = None,
    num_action_samples: int = 1,
    gripper_sample_aggregation: str = "mean",
    gripper_close_threshold: float = 0.5,
    gripper_vote_threshold: float = 0.5,
) -> Any:
    """Query an official lowdim DP policy from a single-step 72D PPO obs.

    The returned action is the first denoised action step in DEXTRAH's 7D
    normalized controller convention. This preserves the original eval-wrapper
    behavior. Prefer ``predict_action_sequence_from_ppo_obs`` when a caller can
    execute Diffusion Policy action chunks.
    """

    return predict_action_sequence_from_ppo_obs(
        policy,
        ppo_obs,
        history,
        step=step,
        phase_progress_provider=phase_progress_provider,
        num_action_samples=num_action_samples,
        gripper_sample_aggregation=gripper_sample_aggregation,
        gripper_close_threshold=gripper_close_threshold,
        gripper_vote_threshold=gripper_vote_threshold,
    )[:, 0]
