"""Aggregate contact-aware Franka cube rollout smokes into a gated relabel set.

This script does not run simulation or train a policy. It reads per-rollout
artifacts from ``contact_aware_franka_cube_rollout.py``, applies hard
acceptance filters, and exports only passing lowdim/action rows as a small NPZ
candidate for a later official Diffusion Policy smoke.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--set_dir", required=True, type=str)
parser.add_argument("--summary_glob", default="rollouts/*/contact_rollout_summary.json", type=str)
parser.add_argument("--min_lift", default=0.10, type=float)
parser.add_argument("--max_pose_clip_fraction", default=0.0, type=float)
parser.add_argument("--max_final_ee_to_cube", default=0.05, type=float)
parser.add_argument("--max_final_finger_to_cube", default=0.08, type=float)
parser.add_argument("--require_success_like", action="store_true", default=True)
parser.add_argument("--no_require_success_like", dest="require_success_like", action="store_false")
parser.add_argument("--output_prefix", default="contact_relabel_set", type=str)
args = parser.parse_args()


PHASE_IDS = {
    "align_open": 0,
    "close_hold": 1,
    "lift": 2,
}


def _literal_list(value: str, *, expected: int | None = None) -> list[float]:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, list):
        raise ValueError(f"Expected list literal, got {type(parsed).__name__}: {value[:80]}")
    if expected is not None and len(parsed) != expected:
        raise ValueError(f"Expected list length {expected}, got {len(parsed)}")
    return [float(v) for v in parsed]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _container_to_set_path(path_str: str, set_dir: Path) -> Path:
    path = Path(path_str)
    if path.exists():
        return path
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "results":
        try:
            idx = parts.index(set_dir.name)
        except ValueError:
            return path
        candidate = set_dir.joinpath(*parts[idx + 1 :])
        if candidate.exists():
            return candidate
    return path


def _gate_failures(payload: dict[str, Any], rows: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    steps = int(payload.get("steps", 0))
    if steps <= 0:
        failures.append("empty_rollout")
    if bool(args.require_success_like) and not bool(payload.get("success_like", False)):
        failures.append("success_like_false")
    if float(payload.get("max_cube_lift_height", -1.0)) < float(args.min_lift):
        failures.append("max_lift_below_threshold")
    if float(payload.get("final_cube_lift_height", -1.0)) < float(args.min_lift):
        failures.append("final_lift_below_threshold")
    if float(payload.get("max_pose_action_clip_fraction", 1.0)) > float(args.max_pose_clip_fraction) + 1.0e-9:
        failures.append("pose_action_clipped")
    if float(payload.get("final_ee_to_cube", 1.0e9)) > float(args.max_final_ee_to_cube):
        failures.append("final_ee_to_cube_too_large")
    if float(payload.get("final_finger_center_to_cube", 1.0e9)) > float(args.max_final_finger_to_cube):
        failures.append("final_finger_to_cube_too_large")
    skipped = int(payload.get("skipped_post_reset_local_step", -1))
    if skipped >= 0 and any(int(float(row.get("local_step", -1))) >= skipped for row in rows):
        failures.append("post_reset_row_detected")
    if rows and "lowdim_obs" not in rows[0]:
        failures.append("missing_lowdim_obs_for_relabel_export")
    return failures


def _report(summary: dict[str, Any], rollout_rows: list[dict[str, Any]], failure_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Franka Cube Contact-Aware Relabel Set Gate",
        "",
        "This bounded artifact aggregates live Isaac controller rollouts. It is a relabeling gate only; it does not train Diffusion Policy or RL.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Gate",
        "",
        f"- minimum final/max lift: `{args.min_lift:.4f}` m",
        f"- maximum pose-action clip fraction: `{args.max_pose_clip_fraction:.4f}`",
        f"- maximum final EE-to-cube: `{args.max_final_ee_to_cube:.4f}` m",
        f"- maximum final finger-center-to-cube: `{args.max_final_finger_to_cube:.4f}` m",
        "",
        "## Rollouts",
        "",
        "| rollout | pass | orientation | reset joint alpha | episode | step | final EE-cube | final finger-cube | final/max lift | max clip | failures | video |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rollout_rows:
        lines.append(
            f"| {row['rollout_id']} | {row['gate_pass']} | "
            f"{row.get('orientation_mode', '')} | "
            f"{float(row.get('reset_joint_blend_alpha', float('nan'))):.3f} | "
            f"{row['episode']} | {row['episode_step']} | "
            f"{float(row['final_ee_to_cube']):.4f} | {float(row['final_finger_center_to_cube']):.4f} | "
            f"{float(row['final_cube_lift_height']):.4f}/{float(row['max_cube_lift_height']):.4f} | "
            f"{float(row['max_pose_action_clip_fraction']):.3f} | {row['failure_reasons']} | `{row['video']}` |"
        )
    if failure_rows:
        lines.extend(["", "## Failures", ""])
        lines.extend(
            [
                "| rollout | reasons |",
                "|---|---|",
            ]
        )
        for row in failure_rows:
            lines.append(f"| {row['rollout_id']} | {row['failure_reasons']} |")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- summary JSON: `{summary['summary_json']}`",
            f"- rollout CSV: `{summary['rollout_csv']}`",
            f"- failure CSV: `{summary['failure_csv']}`",
            f"- accepted NPZ: `{summary['accepted_npz']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    set_dir = Path(args.set_dir).expanduser().resolve()
    summary_paths = sorted(set_dir.glob(args.summary_glob))
    if not summary_paths:
        raise FileNotFoundError(f"No rollout summaries matched {set_dir / args.summary_glob}")

    rollout_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    accepted_obs: list[list[float]] = []
    accepted_actions: list[list[float]] = []
    accepted_phase_ids: list[int] = []
    accepted_episode_ends: list[int] = []
    accepted_rollout_ids: list[str] = []
    accepted_rollout_reset_joint_blend_alpha: list[float] = []

    for summary_path in summary_paths:
        one_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        csv_path = _container_to_set_path(str(one_summary["csv"]), set_dir)
        if not csv_path.exists():
            sibling_csv = summary_path.parent / Path(str(one_summary["csv"])).name
            if sibling_csv.exists():
                csv_path = sibling_csv
        rows = _read_csv(csv_path)
        video = ""
        if one_summary.get("video_files"):
            video = str(one_summary["video_files"][0])
        for variant, payload in one_summary.get("variants", {}).items():
            rollout_id = f"{summary_path.parent.name}_{variant}"
            variant_rows = [row for row in rows if row.get("variant") == variant]
            failures = _gate_failures(payload, variant_rows)
            gate_pass = not failures
            reset_joint_blend_alpha = float(
                payload.get(
                    "reset_joint_blend_alpha",
                    one_summary.get("reset_joint_blend_alpha", float("nan")),
                )
            )
            orientation_mode = str(payload.get("orientation_mode", one_summary.get("orientation_mode", "")))
            rollout_row = {
                "rollout_id": rollout_id,
                "rollout_dir": str(summary_path.parent),
                "variant": variant,
                "orientation_mode": orientation_mode,
                "reset_joint_blend_alpha": reset_joint_blend_alpha,
                "reset_joint_l2_from_source": float(payload.get("reset_joint_l2_from_source", float("nan"))),
                "reset_joint_l2_from_normal": float(payload.get("reset_joint_l2_from_normal", float("nan"))),
                "reset_lowdim_l2_from_dataset": float(payload.get("reset_lowdim_l2_from_dataset", float("nan"))),
                "reset_cube_minus_ee_l2_from_dataset": float(
                    payload.get("reset_cube_minus_ee_l2_from_dataset", float("nan"))
                ),
                "episode": int(one_summary.get("episode", -1)),
                "episode_step": int(one_summary.get("episode_step", -1)),
                "steps": int(payload.get("steps", 0)),
                "gate_pass": gate_pass,
                "failure_reasons": ";".join(failures),
                "final_ee_to_cube": float(payload.get("final_ee_to_cube", float("nan"))),
                "final_finger_center_to_cube": float(payload.get("final_finger_center_to_cube", float("nan"))),
                "min_finger_center_to_cube": float(payload.get("min_finger_center_to_cube", float("nan"))),
                "final_cube_lift_height": float(payload.get("final_cube_lift_height", float("nan"))),
                "max_cube_lift_height": float(payload.get("max_cube_lift_height", float("nan"))),
                "final_gripper_width": float(payload.get("final_gripper_width", float("nan"))),
                "max_pose_action_clip_fraction": float(payload.get("max_pose_action_clip_fraction", float("nan"))),
                "terminated_next_step": bool(payload.get("terminated_next_step", False)),
                "truncated_next_step": bool(payload.get("truncated_next_step", False)),
                "skipped_post_reset_local_step": int(payload.get("skipped_post_reset_local_step", -1)),
                "video": video,
            }
            rollout_rows.append(rollout_row)
            if not gate_pass:
                failure_rows.append(rollout_row)
                continue
            rollout_start_count = len(accepted_obs)
            for row in variant_rows:
                accepted_obs.append(_literal_list(row["lowdim_obs"], expected=21))
                accepted_actions.append(_literal_list(row["executed_action"], expected=7))
                accepted_phase_ids.append(PHASE_IDS.get(row.get("phase", ""), -1))
            if len(accepted_obs) > rollout_start_count:
                accepted_episode_ends.append(len(accepted_obs))
                accepted_rollout_ids.append(rollout_id)
                accepted_rollout_reset_joint_blend_alpha.append(reset_joint_blend_alpha)

    output_prefix = args.output_prefix
    rollout_csv = set_dir / f"{output_prefix}_rollouts.csv"
    failure_csv = set_dir / f"{output_prefix}_failures.csv"
    summary_json = set_dir / f"{output_prefix}_summary.json"
    report_md = set_dir / f"{output_prefix}_report.md"
    accepted_npz = set_dir / f"{output_prefix}_accepted.npz"
    _write_csv(rollout_csv, rollout_rows)
    _write_csv(failure_csv, failure_rows)
    obs_arr = np.asarray(accepted_obs, dtype=np.float32).reshape((-1, 21))
    action_arr = np.asarray(accepted_actions, dtype=np.float32).reshape((-1, 7))
    phase_arr = np.asarray(accepted_phase_ids, dtype=np.int32)
    episode_ends_arr = np.asarray(accepted_episode_ends, dtype=np.int64)
    np.savez_compressed(
        accepted_npz,
        obs=obs_arr,
        action=action_arr,
        episode_ends=episode_ends_arr,
        phase_ids=phase_arr,
        rollout_ids=np.asarray(accepted_rollout_ids),
        rollout_reset_joint_blend_alpha=np.asarray(accepted_rollout_reset_joint_blend_alpha, dtype=np.float32),
    )
    all_pass = bool(rollout_rows) and not failure_rows
    verdict = (
        "PASS: all contact-aware rollouts satisfied the hard relabel gate; this only permits a tiny official-DP smoke proposal."
        if all_pass
        else "FAIL: at least one contact-aware rollout failed the hard relabel gate; do not train DP on this set."
    )
    summary = {
        "set_dir": str(set_dir),
        "summary_glob": args.summary_glob,
        "rollout_count": len(rollout_rows),
        "pass_count": len(rollout_rows) - len(failure_rows),
        "failure_count": len(failure_rows),
        "accepted_transition_count": int(obs_arr.shape[0]),
        "accepted_episode_count": int(episode_ends_arr.shape[0]),
        "gate": {
            "min_lift": float(args.min_lift),
            "max_pose_action_clip_fraction": float(args.max_pose_clip_fraction),
            "max_final_ee_to_cube": float(args.max_final_ee_to_cube),
            "max_final_finger_to_cube": float(args.max_final_finger_to_cube),
            "require_success_like": bool(args.require_success_like),
        },
        "verdict": verdict,
        "summary_json": str(summary_json),
        "rollout_csv": str(rollout_csv),
        "failure_csv": str(failure_csv),
        "report": str(report_md),
        "accepted_npz": str(accepted_npz),
        "rollouts": rollout_rows,
        "failures": failure_rows,
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(_report(summary, rollout_rows, failure_rows), encoding="utf-8")
    print(
        "FRANKA_CUBE_CONTACT_RELABEL_SET_DONE "
        + json.dumps(
            {
                "summary_json": str(summary_json),
                "report": str(report_md),
                "accepted_npz": str(accepted_npz),
                "verdict": verdict,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
