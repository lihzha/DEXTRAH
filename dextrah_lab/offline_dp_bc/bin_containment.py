"""Geometry helpers for axis-aligned bin containment checks."""

from __future__ import annotations

import math
from collections.abc import Sequence


def projected_box_half_extents(
    half_extents_xyz: Sequence[float],
    quat_wxyz: Sequence[float],
) -> tuple[float, float, float]:
    """Project a centered, oriented box onto the world XYZ axes."""
    if len(half_extents_xyz) != 3:
        raise ValueError(f"Expected three half extents, got {len(half_extents_xyz)}")
    if len(quat_wxyz) != 4:
        raise ValueError(f"Expected a WXYZ quaternion, got {len(quat_wxyz)} values")

    half_x, half_y, half_z = (max(0.0, float(value)) for value in half_extents_xyz)
    w, x, y, z = (float(value) for value in quat_wxyz)
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise ValueError("Quaternion must have a finite, nonzero norm")
    w, x, y, z = (value / norm for value in (w, x, y, z))

    rotation = (
        (
            1.0 - 2.0 * (y * y + z * z),
            2.0 * (x * y - z * w),
            2.0 * (x * z + y * w),
        ),
        (
            2.0 * (x * y + z * w),
            1.0 - 2.0 * (x * x + z * z),
            2.0 * (y * z - x * w),
        ),
        (
            2.0 * (x * z - y * w),
            2.0 * (y * z + x * w),
            1.0 - 2.0 * (x * x + y * y),
        ),
    )
    local_half_extents = (half_x, half_y, half_z)
    return tuple(
        sum(
            abs(rotation[world_axis][local_axis]) * local_half_extents[local_axis]
            for local_axis in range(3)
        )
        for world_axis in range(3)
    )
