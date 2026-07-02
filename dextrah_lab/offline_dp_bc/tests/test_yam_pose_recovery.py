from __future__ import annotations

import numpy as np
import pytest

from dextrah_lab.offline_dp_bc.yam_pose_recovery import select_pose_recovery_reference


def _inputs() -> tuple[np.ndarray, np.ndarray]:
    actions = np.zeros((10, 7), dtype=np.float32)
    actions[:, 6] = 1.0
    actions[8:, 6] = -1.0
    trajectory = np.zeros((11, 24), dtype=np.float32)
    trajectory[:9, 16] = np.asarray((0.20, 0.16, 0.11, 0.09, 0.07, 0.05, 0.03, 0.01, 0.0))
    return actions, trajectory


def test_uses_phase_annotations_when_available() -> None:
    actions, trajectory = _inputs()
    phases = np.asarray(("idle", "target/grasp", "target/grasp", "done"))

    selected = select_pose_recovery_reference(
        phases=phases,
        actions=actions,
        robot_trajectory=trajectory,
        phase_pattern="target/grasp",
        phase_fraction=1.0,
    )

    assert selected["reference_step_offset"] == 2
    assert selected["selection_source"] == "phase_annotation"
    assert selected["phase_name"] == "target/grasp"


def test_infers_pregrasp_window_without_phase_features() -> None:
    actions, trajectory = _inputs()

    selected = select_pose_recovery_reference(
        phases=None,
        actions=actions,
        robot_trajectory=trajectory,
        phase_pattern="unused",
        phase_fraction=0.5,
    )

    assert selected["close_start_step"] == 8
    assert selected["approach_start_step"] == 2
    assert selected["approach_stop_step"] == 7
    assert selected["reference_step_offset"] == 4
    assert selected["selection_source"] == "gripper_close_and_tcp_approach"


def test_inference_requires_a_close_command() -> None:
    actions, trajectory = _inputs()
    actions[:, 6] = 1.0

    with pytest.raises(ValueError, match="no gripper-close transition"):
        select_pose_recovery_reference(
            phases=None,
            actions=actions,
            robot_trajectory=trajectory,
            phase_pattern="unused",
            phase_fraction=0.5,
        )


def test_rejects_invalid_fraction() -> None:
    actions, trajectory = _inputs()

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        select_pose_recovery_reference(
            phases=None,
            actions=actions,
            robot_trajectory=trajectory,
            phase_pattern="unused",
            phase_fraction=1.1,
        )
