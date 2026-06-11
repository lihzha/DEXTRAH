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
from typing import Any

import numpy as np


FRANKA_CUBE_PPO_OBS_DIM = 72
FRANKA_CUBE_LOWDIM_OBS_DIM = 21
FRANKA_CUBE_ACTION_DIM = 7


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
        self._filled = np.zeros(self.num_envs, dtype=np.int32)

    def reset(self, env_ids: np.ndarray | list[int] | None = None) -> None:
        if env_ids is None:
            self._history[...] = 0.0
            self._filled[...] = 0
        else:
            self._history[np.asarray(env_ids, dtype=np.int64)] = 0.0
            self._filled[np.asarray(env_ids, dtype=np.int64)] = 0

    def push(self, lowdim_obs: np.ndarray) -> np.ndarray:
        lowdim_obs = np.asarray(lowdim_obs, dtype=np.float32)
        if lowdim_obs.shape != (self.num_envs, self.obs_dim):
            raise ValueError(f"Expected lowdim obs {(self.num_envs, self.obs_dim)}, got {lowdim_obs.shape}")
        self._history[:, :-1] = self._history[:, 1:]
        self._history[:, -1] = lowdim_obs
        not_filled = self._filled < self.n_obs_steps
        if np.any(not_filled):
            self._history[not_filled] = lowdim_obs[not_filled, None, :]
        self._filled = np.minimum(self._filled + 1, self.n_obs_steps)
        return self._history.copy()


def predict_action_sequence_from_ppo_obs(policy: Any, ppo_obs: Any, history: LowdimObsHistory) -> Any:
    """Query an official lowdim DP policy for an action sequence.

    The returned sequence has shape ``(num_envs, n_action_steps, 7)`` in
    DEXTRAH's normalized relative-EE plus gripper convention. This is for
    evaluation wrappers and distillation data collection, not PPO checkpoint
    initialization.
    """

    lowdim = extract_lowdim_obs_from_ppo_obs(ppo_obs)
    obs_seq = history.push(_as_numpy(lowdim).astype(np.float32, copy=False))
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        raise ImportError("predict_action_from_ppo_obs requires torch and an official DP policy") from exc

    device = next(policy.parameters()).device
    obs_tensor = torch.as_tensor(obs_seq, dtype=torch.float32, device=device)
    with torch.no_grad():
        result = policy.predict_action({"obs": obs_tensor})
    action = result["action"]
    return action.detach().cpu().numpy()


def predict_action_from_ppo_obs(policy: Any, ppo_obs: Any, history: LowdimObsHistory) -> Any:
    """Query an official lowdim DP policy from a single-step 72D PPO obs.

    The returned action is the first denoised action step in DEXTRAH's 7D
    normalized controller convention. This preserves the original eval-wrapper
    behavior. Prefer ``predict_action_sequence_from_ppo_obs`` when a caller can
    execute Diffusion Policy action chunks.
    """

    return predict_action_sequence_from_ppo_obs(policy, ppo_obs, history)[:, 0]
