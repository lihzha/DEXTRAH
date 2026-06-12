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


def _episode_starts(episode_ends: np.ndarray) -> np.ndarray:
    if episode_ends.ndim != 1:
        raise ValueError(f"episode_ends must be rank 1, got {episode_ends.shape}")
    return np.concatenate(([0], episode_ends[:-1])).astype(np.int64)


def _history_indices_for_row(
    row_idx: int,
    *,
    episode_starts: np.ndarray,
    episode_ends: np.ndarray,
    n_obs_steps: int,
) -> np.ndarray:
    ep_idx = int(np.searchsorted(episode_ends, row_idx, side="right"))
    if ep_idx >= episode_ends.shape[0]:
        ep_idx = int(episode_ends.shape[0] - 1)
    ep_start = int(episode_starts[ep_idx])
    ep_end = int(episode_ends[ep_idx])
    row_idx = min(max(int(row_idx), ep_start), ep_end - 1)
    frame_ids = np.arange(row_idx - n_obs_steps + 1, row_idx + 1, dtype=np.int64)
    return np.clip(frame_ids, ep_start, ep_end - 1)


def _future_indices_for_row(
    row_idx: int,
    *,
    episode_ends: np.ndarray,
    n_action_steps: int,
) -> np.ndarray:
    ep_idx = int(np.searchsorted(episode_ends, row_idx, side="right"))
    if ep_idx >= episode_ends.shape[0]:
        ep_idx = int(episode_ends.shape[0] - 1)
    ep_end = int(episode_ends[ep_idx])
    row_idx = min(int(row_idx), ep_end - 1)
    frame_ids = np.arange(row_idx, row_idx + n_action_steps, dtype=np.int64)
    return np.clip(frame_ids, row_idx, ep_end - 1)


def _select_rows(
    obs: np.ndarray,
    episode_ends: np.ndarray,
    *,
    batch_size: int,
    row_selector: str,
    row_index: int | None,
) -> np.ndarray:
    n_rows = int(obs.shape[0])
    if row_index is not None:
        if row_index < 0 or row_index >= n_rows:
            raise ValueError(f"--row-index must be in [0, {n_rows}), got {row_index}")
        base = np.arange(row_index, min(row_index + batch_size, n_rows), dtype=np.int64)
    elif row_selector == "first":
        base = np.arange(min(batch_size, n_rows), dtype=np.int64)
    elif row_selector == "gripper_open":
        base = np.argsort(-obs[:, -1], kind="stable")[:batch_size].astype(np.int64)
    elif row_selector == "gripper_closed":
        base = np.argsort(obs[:, -1], kind="stable")[:batch_size].astype(np.int64)
    elif row_selector == "lift_high":
        closed = obs[:, -1] <= (float(np.min(obs[:, -1])) + 1.0e-6)
        if np.any(closed):
            candidate = np.nonzero(closed)[0]
            order = np.argsort(-obs[candidate, 2], kind="stable")
            base = candidate[order[:batch_size]].astype(np.int64)
        else:
            base = np.argsort(-obs[:, 2], kind="stable")[:batch_size].astype(np.int64)
    else:
        raise ValueError(f"Unsupported row selector {row_selector!r}")

    if base.shape[0] == 0:
        raise ValueError("No rows selected")
    if base.shape[0] < batch_size:
        base = np.concatenate((base, np.repeat(base[-1:], batch_size - base.shape[0])))
    if np.any(base >= episode_ends[-1]):
        raise ValueError("Selected row outside dataset")
    return base.astype(np.int64)


def _dataset_lowdim_window(
    dataset_path: Path,
    batch_size: int,
    n_obs_steps: int,
    n_action_steps: int,
    *,
    row_selector: str,
    row_index: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    if obs.ndim != 2 or obs.shape[1] != FRANKA_CUBE_LOWDIM_OBS_DIM:
        raise ValueError(f"Expected obs shape (N, {FRANKA_CUBE_LOWDIM_OBS_DIM}), got {obs.shape}")
    if action.ndim != 2 or action.shape[1] != FRANKA_CUBE_ACTION_DIM:
        raise ValueError(f"Expected action shape (N, {FRANKA_CUBE_ACTION_DIM}), got {action.shape}")
    if obs.shape[0] != action.shape[0]:
        raise ValueError(f"obs/action length mismatch: {obs.shape[0]} vs {action.shape[0]}")
    if obs.shape[0] < 1:
        raise ValueError("Dataset has no observations")
    if episode_ends.ndim != 1 or episode_ends[-1] != obs.shape[0]:
        raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")
    row_indices = _select_rows(
        obs,
        episode_ends,
        batch_size=batch_size,
        row_selector=row_selector,
        row_index=row_index,
    )
    starts = _episode_starts(episode_ends)
    windows = [
        obs[
            _history_indices_for_row(
                int(row_idx),
                episode_starts=starts,
                episode_ends=episode_ends,
                n_obs_steps=n_obs_steps,
            )
        ]
        for row_idx in row_indices
    ]
    action_windows = [
        action[
            _future_indices_for_row(
                int(row_idx),
                episode_ends=episode_ends,
                n_action_steps=n_action_steps,
            )
        ]
        for row_idx in row_indices
    ]
    return np.stack(windows, axis=0).astype(np.float32), np.stack(action_windows, axis=0).astype(np.float32), row_indices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, help="Official DP .ckpt path")
    parser.add_argument("--dataset", required=True, help="Converted Franka cube lowdim NPZ")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--num-inference-steps", type=int, default=2)
    parser.add_argument(
        "--row-selector",
        choices=("first", "gripper_open", "gripper_closed", "lift_high"),
        default="first",
        help="Dataset rows used to build the lowdim observation window.",
    )
    parser.add_argument("--row-index", type=int, default=None, help="Explicit dataset row start index")
    parser.add_argument(
        "--warm-history-from-dataset",
        action="store_true",
        help="Prime the PPO bridge history with the selected dataset window before querying the final row.",
    )
    parser.add_argument(
        "--policy-source",
        choices=("auto", "ema", "raw"),
        default="auto",
        help="Which checkpoint policy to query. auto prefers EMA when present, matching prior behavior.",
    )
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    dataset_path = Path(args.dataset).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)

    workspace = _load_workspace(checkpoint)
    if args.policy_source == "raw":
        policy = workspace.model
        policy_source = "raw"
    elif args.policy_source == "ema":
        policy = getattr(workspace, "ema_model", None)
        if policy is None:
            raise RuntimeError("Checkpoint has no ema_model")
        policy_source = "ema"
    else:
        policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
        policy_source = "ema" if getattr(workspace, "ema_model", None) is not None else "raw"
    policy.num_inference_steps = int(args.num_inference_steps)
    policy.to(torch.device(args.device))
    policy.eval()

    n_obs_steps = int(policy.n_obs_steps)
    n_action_steps = int(policy.n_action_steps)
    lowdim_seq, label_action_seq, row_indices = _dataset_lowdim_window(
        dataset_path,
        int(args.batch_size),
        n_obs_steps,
        n_action_steps,
        row_selector=str(args.row_selector),
        row_index=args.row_index,
    )
    ppo_obs = embed_lowdim_obs_in_ppo_obs(lowdim_seq[:, -1])
    roundtrip = np.asarray(ppo_obs[..., 18:21])
    history = LowdimObsHistory(num_envs=lowdim_seq.shape[0], n_obs_steps=n_obs_steps)
    if args.warm_history_from_dataset:
        for obs_t in range(max(0, n_obs_steps - 1)):
            history.push(lowdim_seq[:, obs_t])

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
        "row_selector": str(args.row_selector),
        "row_index": None if args.row_index is None else int(args.row_index),
        "selected_row_indices": row_indices.astype(int).tolist(),
        "selected_ee_z": lowdim_seq[:, -1, 2].astype(float).tolist(),
        "selected_gripper_width": lowdim_seq[:, -1, -1].astype(float).tolist(),
        "direct_action_shape": list(direct_action.shape),
        "direct_action_min": np.min(direct_action[:, 0], axis=0).astype(float).tolist(),
        "direct_action_max": np.max(direct_action[:, 0], axis=0).astype(float).tolist(),
        "direct_action_chunk_min": np.min(direct_action.reshape(-1, direct_action.shape[-1]), axis=0).astype(float).tolist(),
        "direct_action_chunk_max": np.max(direct_action.reshape(-1, direct_action.shape[-1]), axis=0).astype(float).tolist(),
        "bridge_action_shape": list(bridge_action.shape),
        "bridge_action_min": np.min(bridge_action, axis=0).astype(float).tolist(),
        "bridge_action_max": np.max(bridge_action, axis=0).astype(float).tolist(),
        "label_action_shape": list(label_action_seq.shape),
        "label_action_min": np.min(label_action_seq[:, 0], axis=0).astype(float).tolist(),
        "label_action_max": np.max(label_action_seq[:, 0], axis=0).astype(float).tolist(),
        "label_action_chunk_min": np.min(label_action_seq.reshape(-1, label_action_seq.shape[-1]), axis=0).astype(float).tolist(),
        "label_action_chunk_max": np.max(label_action_seq.reshape(-1, label_action_seq.shape[-1]), axis=0).astype(float).tolist(),
        "selected_label_dz_first": label_action_seq[:, 0, 2].astype(float).tolist(),
        "selected_label_gripper_first": label_action_seq[:, 0, -1].astype(float).tolist(),
        "roundtrip_ee_pos": roundtrip[0].astype(float).tolist(),
        "num_inference_steps": int(policy.num_inference_steps),
        "warm_history_from_dataset": bool(args.warm_history_from_dataset),
        "official_workspace": workspace.__class__.__name__,
        "policy_class": policy.__class__.__name__,
        "policy_source": policy_source,
        "ppo_bridge": "eval_wrapper_or_distillation_only_not_rl_games_weight_init",
        "ppo_obs_dim": FRANKA_CUBE_PPO_OBS_DIM,
    }
    print("FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED " + json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
