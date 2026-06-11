"""Load an official Diffusion Policy checkpoint and query the PPO bridge.

This is intentionally bounded: it constructs the official workspace from a
saved one-step/debug checkpoint, reads a small converted dataset sample, and
runs one inference call through the lowdim-to-PPO-to-lowdim bridge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .dp_dataset import dataset_statistics
from .ppo_bridge import (
    FRANKA_CUBE_ACTION_DIM,
    FRANKA_CUBE_LOWDIM_OBS_DIM,
    FRANKA_CUBE_PPO_OBS_DIM,
    LowdimObsHistory,
    embed_lowdim_obs_in_ppo_obs,
    predict_action_from_ppo_obs,
)


def _load_workspace(checkpoint: Path) -> Any:
    try:
        from diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace import (
            TrainDiffusionUnetLowdimWorkspace,
        )
    except Exception as exc:  # pragma: no cover - exercised without official DP installed.
        raise ImportError(
            "Official diffusion_policy is not importable. Add the official "
            "real-stanford/diffusion_policy checkout to PYTHONPATH."
        ) from exc

    return TrainDiffusionUnetLowdimWorkspace.create_from_checkpoint(str(checkpoint))


def _dataset_lowdim_window(dataset_path: Path, batch_size: int, n_obs_steps: int) -> np.ndarray:
    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    if obs.ndim != 2 or obs.shape[1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
        raise ValueError(f"Expected obs shape (N, {FRANKA_CUBE_LOWDIM_OBS_DIM}), got {obs.shape}")
    if obs.shape[0] < 1:
        raise ValueError("Dataset has no observations")
    base = obs[: min(batch_size, obs.shape[0])]
    if base.shape[0] < batch_size:
        base = np.repeat(base[-1:], batch_size, axis=0)
    return np.repeat(base[:, None, :], n_obs_steps, axis=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, help="Official DP .ckpt path")
    parser.add_argument("--dataset", required=True, help="Converted Franka cube lowdim NPZ")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-inference-steps", type=int, default=2)
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    dataset_path = Path(args.dataset).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)

    workspace = _load_workspace(checkpoint)
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    policy.num_inference_steps = int(args.num_inference_steps)
    policy.to(torch.device(args.device))
    policy.eval()

    n_obs_steps = int(policy.n_obs_steps)
    lowdim_seq = _dataset_lowdim_window(dataset_path, int(args.batch_size), n_obs_steps)
    ppo_obs = embed_lowdim_obs_in_ppo_obs(lowdim_seq[:, -1])
    roundtrip = np.asarray(ppo_obs[..., 18:21])
    history = LowdimObsHistory(num_envs=lowdim_seq.shape[0], n_obs_steps=n_obs_steps)

    with torch.no_grad():
        direct = policy.predict_action({"obs": torch.as_tensor(lowdim_seq, dtype=torch.float32, device=args.device)})
        bridge_action = predict_action_from_ppo_obs(policy, ppo_obs, history)

    direct_action = direct["action"].detach().cpu().numpy()
    if direct_action.shape[-1] != FRANKA_CUBE_ACTION_DIM:
        raise RuntimeError(f"Official policy produced action shape {direct_action.shape}")
    if bridge_action.shape != (lowdim_seq.shape[0], FRANKA_CUBE_ACTION_DIM):
        raise RuntimeError(f"Bridge action shape mismatch: {bridge_action.shape}")
    if not np.isfinite(direct_action).all() or not np.isfinite(bridge_action).all():
        raise RuntimeError("Official policy produced non-finite actions")

    stats = dataset_statistics(dataset_path)
    payload = {
        "checkpoint": str(checkpoint),
        "dataset": str(dataset_path),
        "dataset_steps": int(stats["num_steps"]),
        "dataset_episodes": int(stats["num_episodes"]),
        "ppo_obs_shape": list(ppo_obs.shape),
        "lowdim_seq_shape": list(lowdim_seq.shape),
        "direct_action_shape": list(direct_action.shape),
        "bridge_action_shape": list(bridge_action.shape),
        "bridge_action_min": np.min(bridge_action, axis=0).astype(float).tolist(),
        "bridge_action_max": np.max(bridge_action, axis=0).astype(float).tolist(),
        "roundtrip_ee_pos": roundtrip[0].astype(float).tolist(),
        "num_inference_steps": int(policy.num_inference_steps),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "ppo_bridge": "eval_wrapper_or_distillation_only_not_rl_games_weight_init",
        "ppo_obs_dim": FRANKA_CUBE_PPO_OBS_DIM,
    }
    print("FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED " + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
