"""Compact task-space references for Franka cube trajectory tracking.

The format intentionally stores object-local end-effector targets and gripper
widths, not robot joint trajectories.  Randomized object poses should transform
these task-space waypoints first; IK and collision validation belong in offline
reference generation or bounded reset/validation tooling.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


SCHEMA_NAME = "dextrah.franka_cube_traj_tracking_reference"
SCHEMA_VERSION = 1


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _float_list(value: object, *, length: int, name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{name} must be a list of {length} numbers")
    out: list[float] = []
    for idx, item in enumerate(value):
        if not _is_finite_number(item):
            raise ValueError(f"{name}[{idx}] must be finite")
        out.append(float(item))
    return out


def _normalized_quat_wxyz(value: object, *, name: str) -> list[float]:
    quat = _float_list(value, length=4, name=name)
    norm = math.sqrt(sum(component * component for component in quat))
    if norm < 1.0e-8:
        raise ValueError(f"{name} has near-zero norm")
    return [component / norm for component in quat]


def _check(records: list[dict[str, object]], name: str, passed: bool, **details: object) -> None:
    records.append({"name": name, "passed": bool(passed), "details": details})


def build_template_reference(
    *,
    cube_size_m: float = 0.06,
    table_surface_z_m: float = 0.746,
    cube_spawn_z_m: float | None = None,
    max_gripper_width_m: float = 0.08,
    source_tag: str = "manual_template_pending_graspgenx_curobo_export",
    curobo_validated: bool = False,
) -> dict[str, Any]:
    """Build a small task-space reference scaffold for the Franka cube task.

    This is a documented scaffold, not a substitute for a validated
    GraspGenX/cuRobo library.  The waypoints approach the cube from the robot
    side in the cube object frame and then lift while keeping a close gripper
    schedule.
    """

    cube_size_m = float(cube_size_m)
    table_surface_z_m = float(table_surface_z_m)
    if cube_spawn_z_m is None:
        cube_spawn_z_m = table_surface_z_m + 0.5 * cube_size_m + 0.005
    max_gripper_width_m = float(max_gripper_width_m)

    # Approximate DEXTRAH EE-frame orientation for a side approach from the
    # robot-facing +X side.  Replace with planner-exported tool orientation for
    # any actual experiment run.
    side_approach_quat_wxyz = [0.0, 0.0, 1.0, 0.0]

    waypoints = [
        {
            "phase": "approach",
            "time_s": 0.00,
            "ee_pos_object": [0.180, 0.000, 0.140],
            "ee_quat_object_wxyz": side_approach_quat_wxyz,
            "gripper_width": max_gripper_width_m,
            "tracking_weight": 0.30,
        },
        {
            "phase": "pregrasp",
            "time_s": 0.65,
            "ee_pos_object": [0.105, 0.000, 0.075],
            "ee_quat_object_wxyz": side_approach_quat_wxyz,
            "gripper_width": max_gripper_width_m,
            "tracking_weight": 0.65,
        },
        {
            "phase": "grasp",
            "time_s": 1.15,
            "ee_pos_object": [0.055, 0.000, 0.025],
            "ee_quat_object_wxyz": side_approach_quat_wxyz,
            "gripper_width": max_gripper_width_m,
            "tracking_weight": 1.00,
        },
        {
            "phase": "close",
            "time_s": 1.55,
            "ee_pos_object": [0.055, 0.000, 0.025],
            "ee_quat_object_wxyz": side_approach_quat_wxyz,
            "gripper_width": 0.025,
            "tracking_weight": 1.00,
        },
        {
            "phase": "lift",
            "time_s": 2.20,
            "ee_pos_object": [0.055, 0.000, 0.165],
            "ee_quat_object_wxyz": side_approach_quat_wxyz,
            "gripper_width": 0.025,
            "tracking_weight": 0.55,
        },
    ]

    return {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "description": "Compact object-local task-space reference for Franka cube trajectory tracking.",
        "cube_size_m": cube_size_m,
        "table_surface_z_m": table_surface_z_m,
        "cube_spawn_z_m": float(cube_spawn_z_m),
        "reference_frame": "cube_object_frame",
        "target_frame": "dextrah_ee_frame",
        "tool_frame": "panda_hand_plus_ee_offset",
        "source": {
            "tag": str(source_tag),
            "planner": "manual_template",
            "graspgenx_source": False,
            "curobo_validated": bool(curobo_validated),
            "notes": (
                "Use this scaffold for wiring and validation only. Replace it "
                "with GraspGenX/cuRobo-exported, collision-validated waypoints "
                "before training claims."
            ),
        },
        "tracking": {
            "mode": "reward_only",
            "phase_reference_observations": False,
            "transform_policy": "transform_task_space_waypoints_by_cube_pose",
            "joint_trajectory_policy": "do_not_transform_joint_trajectories",
        },
        "validation": {
            "min_ee_table_clearance_m": 0.025,
            "min_cube_aabb_clearance_m": 0.0,
            "requires_curobo_collision_validation_before_training": True,
        },
        "waypoints": waypoints,
    }


def read_reference_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def write_reference_payload(path: str | Path, payload: dict[str, Any]) -> None:
    out_path = Path(path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_reference_payload(payload: dict[str, Any]) -> list[dict[str, object]]:
    """Return pass/fail diagnostics for a compact reference payload."""

    records: list[dict[str, object]] = []
    _check(records, "schema_name", payload.get("schema") == SCHEMA_NAME, schema=payload.get("schema"))
    _check(
        records,
        "schema_version",
        payload.get("schema_version") == SCHEMA_VERSION,
        schema_version=payload.get("schema_version"),
    )

    waypoints = payload.get("waypoints")
    _check(records, "waypoints_list", isinstance(waypoints, list) and len(waypoints) >= 2)
    if not isinstance(waypoints, list):
        return records

    cube_size = float(payload.get("cube_size_m", 0.06))
    cube_half_extent = 0.5 * cube_size
    table_surface_z = float(payload.get("table_surface_z_m", 0.746))
    cube_spawn_z = float(payload.get("cube_spawn_z_m", table_surface_z + cube_half_extent + 0.005))
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    min_table_clearance = float(validation.get("min_ee_table_clearance_m", 0.025))
    min_cube_clearance = float(validation.get("min_cube_aabb_clearance_m", 0.0))
    max_gripper_width = 0.08

    times: list[float] = []
    min_world_z = math.inf
    min_table_margin = math.inf
    min_cube_aabb_clearance = math.inf
    waypoint_errors: list[str] = []
    phase_names: list[str] = []

    for idx, raw_waypoint in enumerate(waypoints):
        if not isinstance(raw_waypoint, dict):
            waypoint_errors.append(f"waypoint {idx} is not an object")
            continue
        phase = raw_waypoint.get("phase")
        if not isinstance(phase, str) or not phase:
            waypoint_errors.append(f"waypoint {idx} has invalid phase")
        else:
            phase_names.append(phase)
        if not _is_finite_number(raw_waypoint.get("time_s")):
            waypoint_errors.append(f"waypoint {idx} has invalid time_s")
            continue
        time_s = float(raw_waypoint["time_s"])
        times.append(time_s)
        try:
            pos = _float_list(raw_waypoint.get("ee_pos_object"), length=3, name=f"waypoints[{idx}].ee_pos_object")
            _normalized_quat_wxyz(
                raw_waypoint.get("ee_quat_object_wxyz"),
                name=f"waypoints[{idx}].ee_quat_object_wxyz",
            )
        except ValueError as exc:
            waypoint_errors.append(str(exc))
            continue
        if "gripper_width" in raw_waypoint and raw_waypoint["gripper_width"] is not None:
            gripper_width = raw_waypoint["gripper_width"]
            if not _is_finite_number(gripper_width) or not (0.0 <= float(gripper_width) <= max_gripper_width):
                waypoint_errors.append(f"waypoint {idx} gripper_width must be in [0, {max_gripper_width}]")
        if "tracking_weight" in raw_waypoint:
            tracking_weight = raw_waypoint["tracking_weight"]
            if not _is_finite_number(tracking_weight) or float(tracking_weight) < 0.0:
                waypoint_errors.append(f"waypoint {idx} tracking_weight must be non-negative")

        world_z = cube_spawn_z + pos[2]
        table_margin = world_z - table_surface_z
        min_world_z = min(min_world_z, world_z)
        min_table_margin = min(min_table_margin, table_margin)

        outside = [
            max(abs(pos[0]) - cube_half_extent, 0.0),
            max(abs(pos[1]) - cube_half_extent, 0.0),
            max(abs(pos[2]) - cube_half_extent, 0.0),
        ]
        if outside == [0.0, 0.0, 0.0]:
            clearance = -min(cube_half_extent - abs(axis) for axis in pos)
        else:
            clearance = math.sqrt(sum(component * component for component in outside))
        min_cube_aabb_clearance = min(min_cube_aabb_clearance, clearance)

    monotonic_times = len(times) == len(waypoints) and all(next_t > cur_t for cur_t, next_t in zip(times, times[1:]))
    _check(records, "waypoints_valid", len(waypoint_errors) == 0, errors=waypoint_errors[:12])
    _check(records, "time_strictly_increasing", monotonic_times, times=times)
    _check(records, "phase_labels_present", len(phase_names) == len(waypoints), phases=phase_names)
    _check(
        records,
        "approx_ee_table_clearance",
        min_table_margin >= min_table_clearance,
        min_world_z=min_world_z,
        table_surface_z=table_surface_z,
        min_table_margin=min_table_margin,
        required_margin=min_table_clearance,
    )
    _check(
        records,
        "target_outside_cube_aabb",
        min_cube_aabb_clearance >= min_cube_clearance,
        min_cube_aabb_clearance=min_cube_aabb_clearance,
        required_clearance=min_cube_clearance,
    )

    forbidden_keys = ("joint_position", "joint_positions", "joint_trajectory", "joint_trajectories")
    present_forbidden = [key for key in forbidden_keys if key in payload]
    for idx, raw_waypoint in enumerate(waypoints):
        if isinstance(raw_waypoint, dict):
            present_forbidden.extend(f"waypoints[{idx}].{key}" for key in forbidden_keys if key in raw_waypoint)
    _check(records, "no_joint_trajectory_arrays", len(present_forbidden) == 0, present_forbidden=present_forbidden)

    tracking = payload.get("tracking") if isinstance(payload.get("tracking"), dict) else {}
    _check(
        records,
        "task_space_transform_policy",
        tracking.get("transform_policy") == "transform_task_space_waypoints_by_cube_pose",
        transform_policy=tracking.get("transform_policy"),
    )
    _check(
        records,
        "joint_transform_policy",
        tracking.get("joint_trajectory_policy") == "do_not_transform_joint_trajectories",
        joint_trajectory_policy=tracking.get("joint_trajectory_policy"),
    )
    return records


def assert_reference_payload_valid(payload: dict[str, Any]) -> None:
    records = validate_reference_payload(payload)
    failed = [record for record in records if not bool(record["passed"])]
    if failed:
        names = ", ".join(str(record["name"]) for record in failed)
        raise ValueError(f"Invalid Franka cube trajectory tracking reference: {names}")


def load_reference_payload(path: str | Path) -> dict[str, Any]:
    payload = read_reference_payload(path)
    assert_reference_payload_valid(payload)
    return payload
