#!/usr/bin/env python3
"""Create or validate compact Franka cube trajectory-tracking references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


if str(_repo_root()) not in sys.path:
    sys.path.insert(0, str(_repo_root()))

from dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_traj_tracking_reference import (  # noqa: E402
    build_template_reference,
    read_reference_payload,
    validate_reference_payload,
    write_reference_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None, help="Existing compact reference JSON to validate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root()
        / "local_results/franka_cube_traj_tracking/franka-cube-traj-tracking/reference_template.json",
        help="Output compact reference JSON path when generating a template.",
    )
    parser.add_argument("--summary", type=Path, default=None, help="Optional validation summary JSON path.")
    parser.add_argument("--validate-only", action="store_true", help="Validate without writing a generated template.")
    parser.add_argument("--cube-size", type=float, default=0.06)
    parser.add_argument("--table-surface-z", type=float, default=0.746)
    parser.add_argument("--cube-spawn-z", type=float, default=None)
    parser.add_argument("--max-gripper-width", type=float, default=0.08)
    parser.add_argument("--source-tag", type=str, default="manual_template_pending_graspgenx_curobo_export")
    parser.add_argument(
        "--mark-curobo-validated",
        action="store_true",
        help="Mark the generated reference as cuRobo-validated. Use only for real validated exports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input is not None:
        payload = read_reference_payload(args.input)
        output_path = None
    else:
        payload = build_template_reference(
            cube_size_m=float(args.cube_size),
            table_surface_z_m=float(args.table_surface_z),
            cube_spawn_z_m=args.cube_spawn_z,
            max_gripper_width_m=float(args.max_gripper_width),
            source_tag=str(args.source_tag),
            curobo_validated=bool(args.mark_curobo_validated),
        )
        output_path = args.output.expanduser().resolve()
        if not args.validate_only:
            write_reference_payload(output_path, payload)

    records = validate_reference_payload(payload)
    passed = all(bool(record["passed"]) for record in records)
    summary = {
        "passed": passed,
        "input": str(args.input.expanduser().resolve()) if args.input is not None else None,
        "output": str(output_path) if output_path is not None and not args.validate_only else None,
        "waypoint_count": len(payload.get("waypoints", [])) if isinstance(payload.get("waypoints"), list) else 0,
        "curobo_validated": bool((payload.get("source") or {}).get("curobo_validated"))
        if isinstance(payload.get("source"), dict)
        else False,
        "records": records,
    }
    if args.summary is not None:
        summary_path = args.summary.expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
