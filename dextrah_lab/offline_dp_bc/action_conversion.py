"""DEXTRAH Franka relative end-effector action conversion.

The Franka cube task uses Isaac Lab's DifferentialIKController with
``command_type="pose"`` and ``use_relative_mode=True``. Its six pose command
dimensions are position deltas in meters plus axis-angle rotation deltas in
radians. The DEXTRAH policy action normalizes those deltas by fixed controller
scales, then appends the raw gripper command where ``-1`` closes and ``+1``
opens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class DextrahActionConvention:
    """Relative EE action convention used by DEXTRAH Franka cube PPO."""

    position_scale: tuple[float, float, float] = (0.060, 0.060, 0.045)
    rotation_scale: tuple[float, float, float] = (0.25, 0.25, 0.30)
    world_to_action_quat_wxyz: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    max_gripper_width: float = 0.08
    open_gripper_action: float = 1.0
    close_gripper_action: float = -1.0
    clip_actions: bool = True

    @property
    def pose_scale(self) -> np.ndarray:
        return np.asarray(self.position_scale + self.rotation_scale, dtype=np.float32)


DEFAULT_DEXTRAH_ACTION_CONVENTION = DextrahActionConvention()


def normalize_quat_wxyz(quat: np.ndarray, eps: float = 1.0e-12) -> np.ndarray:
    quat = np.asarray(quat, dtype=np.float64)
    norm = np.linalg.norm(quat, axis=-1, keepdims=True)
    norm = np.maximum(norm, eps)
    return quat / norm


def quat_conjugate_wxyz(quat: np.ndarray) -> np.ndarray:
    quat = np.asarray(quat, dtype=np.float64)
    out = quat.copy()
    out[..., 1:] *= -1.0
    return out


def quat_mul_wxyz(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    q1 = np.asarray(q1, dtype=np.float64)
    q2 = np.asarray(q2, dtype=np.float64)
    w1, x1, y1, z1 = np.moveaxis(q1, -1, 0)
    w2, x2, y2, z2 = np.moveaxis(q2, -1, 0)
    out = np.stack(
        (
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ),
        axis=-1,
    )
    return normalize_quat_wxyz(out)


def quat_inv_wxyz(quat: np.ndarray, eps: float = 1.0e-12) -> np.ndarray:
    quat = np.asarray(quat, dtype=np.float64)
    denom = np.sum(quat * quat, axis=-1, keepdims=True)
    return quat_conjugate_wxyz(quat) / np.maximum(denom, eps)


def axis_angle_from_quat_wxyz(quat: np.ndarray, eps: float = 1.0e-6) -> np.ndarray:
    """Match Isaac Lab's ``axis_angle_from_quat`` sign and Taylor behavior."""

    quat = normalize_quat_wxyz(quat)
    quat = quat * (1.0 - 2.0 * (quat[..., 0:1] < 0.0))
    mag = np.linalg.norm(quat[..., 1:], axis=-1)
    half_angle = np.arctan2(mag, quat[..., 0])
    angle = 2.0 * half_angle
    denom = np.where(
        np.abs(angle) > eps,
        np.sin(half_angle) / np.maximum(angle, eps),
        0.5 - angle * angle / 48.0,
    )
    return quat[..., 1:4] / denom[..., None]


def quat_from_axis_angle_wxyz(axis_angle: np.ndarray, eps: float = 1.0e-12) -> np.ndarray:
    axis_angle = np.asarray(axis_angle, dtype=np.float64)
    angle = np.linalg.norm(axis_angle, axis=-1, keepdims=True)
    axis = axis_angle / np.maximum(angle, eps)
    half = 0.5 * angle
    quat = np.concatenate((np.cos(half), axis * np.sin(half)), axis=-1)
    identity = np.zeros_like(quat)
    identity[..., 0] = 1.0
    return normalize_quat_wxyz(np.where(angle > eps, quat, identity))


def rotate_vectors_wxyz(quat: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Rotate 3D vectors by a WXYZ quaternion with NumPy broadcasting."""

    vectors = np.asarray(vectors, dtype=np.float64)
    quat = normalize_quat_wxyz(np.asarray(quat, dtype=np.float64))
    quat_vec = quat[..., 1:4]
    w = quat[..., 0:1]
    uv = np.cross(quat_vec, vectors, axis=-1)
    uuv = np.cross(quat_vec, uv, axis=-1)
    return vectors + 2.0 * (w * uv + uuv)


def apply_delta_pose(
    source_pos: np.ndarray,
    source_quat_wxyz: np.ndarray,
    delta_pose: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Numpy equivalent of Isaac Lab ``apply_delta_pose`` for validation."""

    source_pos = np.asarray(source_pos, dtype=np.float64)
    source_quat_wxyz = normalize_quat_wxyz(source_quat_wxyz)
    delta_pose = np.asarray(delta_pose, dtype=np.float64)
    target_pos = source_pos + delta_pose[..., :3]
    delta_quat = quat_from_axis_angle_wxyz(delta_pose[..., 3:6])
    target_quat = quat_mul_wxyz(delta_quat, source_quat_wxyz)
    return target_pos, target_quat


def normalized_action_to_world_delta(
    action: np.ndarray,
    *,
    convention: DextrahActionConvention = DEFAULT_DEXTRAH_ACTION_CONVENTION,
) -> np.ndarray:
    """Convert normalized action-frame pose commands back to world deltas."""

    action = np.asarray(action, dtype=np.float64)
    raw_delta = action[..., :6] * convention.pose_scale
    action_to_world_quat = quat_inv_wxyz(np.asarray(convention.world_to_action_quat_wxyz, dtype=np.float64))
    pos_delta_world = rotate_vectors_wxyz(action_to_world_quat, raw_delta[..., :3])
    rot_delta_world = rotate_vectors_wxyz(action_to_world_quat, raw_delta[..., 3:6])
    return np.concatenate((pos_delta_world, rot_delta_world), axis=-1).astype(np.float32)


def apply_normalized_action_to_world_pose(
    source_pos: np.ndarray,
    source_quat_wxyz: np.ndarray,
    action: np.ndarray,
    *,
    convention: DextrahActionConvention = DEFAULT_DEXTRAH_ACTION_CONVENTION,
) -> tuple[np.ndarray, np.ndarray]:
    """Replay a normalized DEXTRAH action against world-frame EE poses."""

    world_delta = normalized_action_to_world_delta(action, convention=convention)
    return apply_delta_pose(source_pos, source_quat_wxyz, world_delta)


def gripper_width_to_action(
    gripper_width: np.ndarray,
    *,
    max_gripper_width: float = DEFAULT_DEXTRAH_ACTION_CONVENTION.max_gripper_width,
) -> np.ndarray:
    """Map a target gripper gap in meters to DEXTRAH raw gripper action."""

    width = np.asarray(gripper_width, dtype=np.float32)
    denom = max(float(max_gripper_width), 1.0e-6)
    return np.clip(2.0 * width / denom - 1.0, -1.0, 1.0)


def phase_gripper_actions(
    phases: Sequence[str],
    *,
    convention: DextrahActionConvention = DEFAULT_DEXTRAH_ACTION_CONVENTION,
    close_phase_names: Iterable[str] = ("close_fingers", "hold_after_close", "lift_object", "hold_after_lift"),
) -> np.ndarray:
    """Infer open/close gripper actions from GraspGenX/cuRobo phase labels."""

    close_names = set(close_phase_names)
    actions = np.full(len(phases), convention.open_gripper_action, dtype=np.float32)
    for idx, phase in enumerate(phases):
        if str(phase) in close_names:
            actions[idx] = convention.close_gripper_action
    return actions


def derive_relative_ee_actions(
    ee_pos: np.ndarray,
    ee_quat_wxyz: np.ndarray,
    *,
    gripper_action: np.ndarray | None = None,
    gripper_width: np.ndarray | None = None,
    phases: Sequence[str] | None = None,
    convention: DextrahActionConvention = DEFAULT_DEXTRAH_ACTION_CONVENTION,
    terminal_action: str = "repeat",
) -> np.ndarray:
    """Derive normalized 7D DEXTRAH actions from task-space EE waypoints.

    For timestep ``t``, the first six dimensions are the normalized relative
    command that moves from waypoint ``t`` to ``t + 1`` using Isaac Lab's
    delta-pose convention:

    ``target_pos = current_pos + delta_pos``
    ``target_quat = quat_from_axis_angle(delta_rot) * current_quat``

    The final action uses an explicit ``gripper_action`` when supplied, maps
    ``gripper_width`` when supplied, or falls back to phase-derived open/close
    labels. The default terminal action repeats the previous command so
    observations and actions keep the same length.

    DEXTRAH Franka observations are recorded in the environment/world frame,
    while Isaac's differential IK controller receives relative commands in the
    robot root frame. ``world_to_action_quat_wxyz`` rotates translation and
    axis-angle deltas into that controller frame before normalization. The
    default is the Franka cube root's 180 degree yaw about world z.
    """

    ee_pos = np.asarray(ee_pos, dtype=np.float64)
    ee_quat_wxyz = normalize_quat_wxyz(ee_quat_wxyz)
    if ee_pos.ndim != 2 or ee_pos.shape[1] != 3:
        raise ValueError(f"ee_pos must have shape (T, 3), got {ee_pos.shape}")
    if ee_quat_wxyz.shape != (ee_pos.shape[0], 4):
        raise ValueError(f"ee_quat_wxyz must have shape (T, 4), got {ee_quat_wxyz.shape}")
    if ee_pos.shape[0] < 2:
        raise ValueError("Need at least two EE waypoints to derive relative actions")

    pos_delta = ee_pos[1:] - ee_pos[:-1]
    quat_delta = quat_mul_wxyz(ee_quat_wxyz[1:], quat_inv_wxyz(ee_quat_wxyz[:-1]))
    rot_delta = axis_angle_from_quat_wxyz(quat_delta)
    world_to_action_quat = np.asarray(convention.world_to_action_quat_wxyz, dtype=np.float64)
    pos_delta = rotate_vectors_wxyz(world_to_action_quat, pos_delta)
    rot_delta = rotate_vectors_wxyz(world_to_action_quat, rot_delta)
    pose_delta = np.concatenate((pos_delta, rot_delta), axis=-1).astype(np.float32)
    normalized_pose = pose_delta / convention.pose_scale[None, :]

    if terminal_action == "repeat":
        last_pose = normalized_pose[-1:]
    elif terminal_action == "zero":
        last_pose = np.zeros((1, 6), dtype=np.float32)
    elif terminal_action == "drop":
        last_pose = np.empty((0, 6), dtype=np.float32)
    else:
        raise ValueError(f"Unsupported terminal_action {terminal_action!r}")
    normalized_pose = np.concatenate((normalized_pose, last_pose), axis=0)

    if gripper_action is not None:
        grip = np.asarray(gripper_action, dtype=np.float32)
    elif gripper_width is not None:
        grip = gripper_width_to_action(gripper_width, max_gripper_width=convention.max_gripper_width)
    elif phases is not None:
        grip = phase_gripper_actions(phases, convention=convention)
    else:
        grip = np.full(ee_pos.shape[0], convention.open_gripper_action, dtype=np.float32)

    if terminal_action == "drop":
        grip = grip[:-1]
    if grip.shape != (normalized_pose.shape[0],):
        raise ValueError(f"gripper action must have shape ({normalized_pose.shape[0]},), got {grip.shape}")

    action = np.concatenate((normalized_pose, grip[:, None]), axis=-1).astype(np.float32)
    if convention.clip_actions:
        action = np.clip(action, -1.0, 1.0)
    return action
