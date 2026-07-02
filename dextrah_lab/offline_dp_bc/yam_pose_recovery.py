"""Pure helpers for choosing a recovery point in YAM demonstrations."""

from __future__ import annotations

from typing import Any

import numpy as np


DEFAULT_APPROACH_DISTANCE_M = 0.12


def select_pose_recovery_reference(
    *,
    phases: np.ndarray | None,
    actions: np.ndarray,
    robot_trajectory: np.ndarray,
    phase_pattern: str,
    phase_fraction: float,
    approach_distance_m: float = DEFAULT_APPROACH_DISTANCE_M,
) -> dict[str, Any]:
    """Select a pre-grasp recovery row from annotations or observable controls."""
    fraction = float(phase_fraction)
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("recovery phase fraction must lie in [0, 1]")

    if phases is not None:
        phase_array = np.asarray(phases, dtype=str).reshape(-1)
        matching = np.flatnonzero(np.char.find(phase_array, str(phase_pattern)) >= 0)
        if matching.size == 0:
            raise ValueError(f"Recovery phase pattern {phase_pattern!r} does not match any source phase")
        phase_offset = int(round(fraction * max(0, matching.size - 1)))
        reference_step = int(matching[phase_offset])
        return {
            "approach_distance_m": None,
            "approach_start_step": int(matching[0]),
            "approach_stop_step": int(matching[-1]),
            "close_start_step": None,
            "phase_name": str(phase_array[reference_step]),
            "reference_step_offset": reference_step,
            "selection_source": "phase_annotation",
        }

    action_array = np.asarray(actions)
    trajectory = np.asarray(robot_trajectory)
    if action_array.ndim != 2 or action_array.shape[0] < 1 or action_array.shape[1] < 7:
        raise ValueError(f"Expected recovery actions shaped [T, >=7], got {action_array.shape}")
    if trajectory.ndim != 2 or trajectory.shape[0] < 1 or trajectory.shape[1] < 19:
        raise ValueError(f"Expected robot trajectory shaped [T, >=19], got {trajectory.shape}")

    closing = np.flatnonzero(action_array[:, 6] < -0.5)
    if closing.size == 0:
        raise ValueError("Cannot infer recovery point: source actions contain no gripper-close transition")
    close_start = int(closing[0])
    close_state_index = min(close_start, int(trajectory.shape[0]) - 1)
    target_tcp = trajectory[close_state_index, 16:19].astype(np.float64)

    approach_stop = max(0, close_start - 1)
    approach_start = max(0, close_start - min(64, close_start))
    if close_start > 0:
        prior_count = min(close_start, int(trajectory.shape[0]), int(action_array.shape[0]))
        prior_tcp = trajectory[:prior_count, 16:19].astype(np.float64)
        distances = np.linalg.norm(prior_tcp - target_tcp[None, :], axis=1)
        eligible = (distances <= max(0.0, float(approach_distance_m))) & (
            action_array[:prior_count, 6] >= -0.5
        )
        eligible_indices = np.flatnonzero(eligible)
        if eligible_indices.size:
            approach_stop = int(eligible_indices[-1])
            approach_start = approach_stop
            while approach_start > 0 and bool(eligible[approach_start - 1]):
                approach_start -= 1

    reference_step = int(
        round(approach_start + fraction * max(0, approach_stop - approach_start))
    )
    reference_step = min(reference_step, int(action_array.shape[0]) - 1)
    return {
        "approach_distance_m": float(approach_distance_m),
        "approach_start_step": approach_start,
        "approach_stop_step": approach_stop,
        "close_start_step": close_start,
        "phase_name": "inferred/tcp_approach_before_gripper_close",
        "reference_step_offset": reference_step,
        "selection_source": "gripper_close_and_tcp_approach",
    }
