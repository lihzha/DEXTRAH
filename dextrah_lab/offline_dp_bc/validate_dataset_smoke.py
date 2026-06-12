"""Bounded local smoke for Franka cube Diffusion Policy BC data."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np

from .action_conversion import (
    DEFAULT_DEXTRAH_ACTION_CONVENTION,
    apply_normalized_action_to_world_pose,
    quat_from_axis_angle_wxyz,
)
from .dp_dataset import FrankaCubeLowdimDataset, dataset_statistics
from .trajectory_conversion import TrajectoryArrays, trajectory_to_episode, write_demo_dataset


def _make_synthetic_episode(num_frames: int, yaw_delta: float) -> TrajectoryArrays:
    alpha = np.linspace(0.0, 1.0, num_frames, dtype=np.float32)
    ee_pos = np.stack(
        (
            -0.25 - 0.08 * alpha,
            -0.12 * np.ones_like(alpha),
            0.92 - 0.08 * alpha,
        ),
        axis=-1,
    )
    ee_quat = quat_from_axis_angle_wxyz(
        np.stack((np.zeros_like(alpha), np.zeros_like(alpha), yaw_delta * alpha), axis=-1)
    ).astype(np.float32)
    cube_pos = np.tile(np.asarray([-0.36, -0.12, 0.781], dtype=np.float32), (num_frames, 1))
    cube_quat = np.zeros((num_frames, 4), dtype=np.float32)
    cube_quat[:, 0] = 1.0
    phases = np.asarray(["go_to_pre_grasp_pose"] * num_frames, dtype="<U64")
    gripper_width = np.full(num_frames, 0.08, dtype=np.float32)
    return TrajectoryArrays(
        ee_pos=ee_pos,
        ee_quat_wxyz=ee_quat,
        cube_pos=cube_pos,
        cube_quat_wxyz=cube_quat,
        phases=phases,
        gripper_width=gripper_width,
        fps=60.0,
        source_path="synthetic",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=None, help="Existing dataset .npz to validate")
    parser.add_argument("--synthetic-output", type=Path, default=None, help="Where to write synthetic smoke data")
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--pad-before", type=int, default=1)
    parser.add_argument("--pad-after", type=int, default=3)
    parser.add_argument("--expected-obs-dim", type=int, default=21)
    parser.add_argument(
        "--action-normalizer",
        choices=("identity", "limits", "limits_clamp_constant"),
        default="identity",
    )
    parser.add_argument("--val-ratio", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset is None:
        output = args.synthetic_output
        if output is None:
            output = Path(tempfile.gettempdir()) / "franka_cube_dp_bc_synthetic_smoke.npz"
        episodes = [
            trajectory_to_episode(_make_synthetic_episode(18, 0.10)),
            trajectory_to_episode(_make_synthetic_episode(20, -0.08)),
        ]
        metadata = {
            "source": "synthetic_smoke",
            "action_convention": DEFAULT_DEXTRAH_ACTION_CONVENTION.__dict__,
        }
        write_demo_dataset(episodes, output, metadata=metadata)
        dataset_path = output
    else:
        dataset_path = args.dataset

    dataset = FrankaCubeLowdimDataset(
        str(dataset_path),
        horizon=args.horizon,
        pad_before=args.pad_before,
        pad_after=args.pad_after,
        val_ratio=float(args.val_ratio),
        action_normalizer=str(args.action_normalizer),
    )
    if len(dataset) == 0:
        raise RuntimeError("Dataset has zero train samples")
    sample = dataset[0]
    obs = sample["obs"].numpy()
    action = sample["action"].numpy()
    if obs.shape != (args.horizon, int(args.expected_obs_dim)):
        raise RuntimeError(f"Unexpected obs sample shape {obs.shape}")
    if action.shape != (args.horizon, 7):
        raise RuntimeError(f"Unexpected action sample shape {action.shape}")
    if not np.all(np.isfinite(obs)) or not np.all(np.isfinite(action)):
        raise RuntimeError("Sample contains non-finite values")
    if np.max(np.abs(action)) > 1.0001:
        raise RuntimeError("Action sample exceeds normalized DEXTRAH action bounds")

    replay_idx = min(max(int(args.pad_before), 0), args.horizon - 2)
    next_pos, _next_quat = apply_normalized_action_to_world_pose(
        obs[replay_idx : replay_idx + 1, :3],
        obs[replay_idx : replay_idx + 1, 3:7],
        action[replay_idx : replay_idx + 1],
        convention=DEFAULT_DEXTRAH_ACTION_CONVENTION,
    )
    replay_error = float(np.linalg.norm(next_pos[0] - obs[replay_idx + 1, :3]))
    stats = dataset_statistics(dataset_path)
    result = {
        "dataset": str(dataset_path),
        "num_train_samples": len(dataset),
        "sample_obs_shape": list(obs.shape),
        "sample_action_shape": list(action.shape),
        "obs_dim": stats["obs_shape"][1],
        "action_dim": stats["action_shape"][1],
        "first_step_position_replay_error": replay_error,
        "official_diffusion_policy_imported": dataset.__class__.__mro__[1].__module__.startswith("diffusion_policy"),
    }
    print("FRANKA_CUBE_DP_BC_SMOKE_PASSED " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
