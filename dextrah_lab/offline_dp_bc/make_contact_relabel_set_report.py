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
    "contact_align_open": 0,
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


def _payload_vec3(payload: dict[str, Any], key: str) -> list[float]:
    value = payload.get(key)
    if value is None:
        return [float("nan"), float("nan"), float("nan")]
    arr = np.asarray(value, dtype=np.float32).reshape(-1)
    if arr.shape[0] != 3:
        raise ValueError(f"Expected {key} length 3, got {value}")
    return [float(v) for v in arr.tolist()]


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
        "| rollout | pass | orientation | filter | contact ref | pre-close finger | pre-close EE | contact-ok | reset joint alpha | reset cube alpha | episode | step | final EE-cube | final finger-cube | final/max lift | max clip | max raw | min scale | failures | video |",
        "|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rollout_rows:
        lines.append(
            f"| {row['rollout_id']} | {row['gate_pass']} | "
            f"{row.get('orientation_mode', '')} | "
            f"{row.get('pose_action_filter', '')} | "
            f"{row.get('contact_align_reference', '')} | "
            f"{float(row.get('pre_close_finger_center_to_cube', float('nan'))):.4f} | "
            f"{float(row.get('pre_close_ee_to_cube', float('nan'))):.4f} | "
            f"{row.get('contact_align_success', '')} | "
            f"{float(row.get('reset_joint_blend_alpha', float('nan'))):.3f} | "
            f"{float(row.get('reset_cube_pos_blend_alpha', float('nan'))):.3f} | "
            f"{row['episode']} | {row['episode_step']} | "
            f"{float(row['final_ee_to_cube']):.4f} | {float(row['final_finger_center_to_cube']):.4f} | "
            f"{float(row['final_cube_lift_height']):.4f}/{float(row['max_cube_lift_height']):.4f} | "
            f"{float(row['max_pose_action_clip_fraction']):.3f} | "
            f"{float(row.get('max_raw_pose_action_max_abs', float('nan'))):.3f} | "
            f"{float(row.get('min_pose_action_filter_scale', float('nan'))):.3f} | "
            f"{row['failure_reasons']} | `{row['video']}` |"
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
            f"- accepted RGB NPZ: `{summary.get('accepted_rgb_npz', '')}`",
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
    accepted_rollout_reset_cube_pos_blend_alpha: list[float] = []
    accepted_rollout_applied_cube_pos: list[list[float]] = []
    accepted_rollout_normal_reset_cube_pos: list[list[float]] = []
    accepted_rollout_source_cube_pos: list[list[float]] = []
    accepted_images: list[np.ndarray] = []
    accepted_robot_states: list[np.ndarray] = []
    accepted_rgb_actions: list[np.ndarray] = []
    accepted_rgb_phase_ids: list[np.ndarray] = []
    accepted_rgb_episode_ends: list[int] = []
    accepted_rgb_rollout_ids: list[str] = []
    accepted_rgb_rollout_reset_joint_blend_alpha: list[float] = []
    accepted_rgb_rollout_reset_cube_pos_blend_alpha: list[float] = []
    accepted_rgb_rollout_applied_cube_pos: list[list[float]] = []
    accepted_rgb_rollout_normal_reset_cube_pos: list[list[float]] = []
    accepted_rgb_rollout_source_cube_pos: list[list[float]] = []
    rgb_camera_eye: np.ndarray | None = None
    rgb_camera_target: np.ndarray | None = None
    rgb_robot_state_names: np.ndarray | None = None

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
            reset_cube_pos_blend_alpha = float(
                payload.get(
                    "reset_cube_pos_blend_alpha",
                    one_summary.get("reset_cube_pos_blend_alpha", 1.0),
                )
            )
            orientation_mode = str(payload.get("orientation_mode", one_summary.get("orientation_mode", "")))
            pose_action_filter = str(payload.get("pose_action_filter", one_summary.get("pose_action_filter", "")))
            applied_cube_pos = _payload_vec3(payload, "applied_cube_pos")
            normal_reset_cube_pos = _payload_vec3(payload, "normal_reset_cube_pos")
            source_cube_pos = _payload_vec3(payload, "source_cube_pos")
            rollout_row = {
                "rollout_id": rollout_id,
                "rollout_dir": str(summary_path.parent),
                "variant": variant,
                "orientation_mode": orientation_mode,
                "pose_action_filter": pose_action_filter,
                "pose_action_limit": float(payload.get("pose_action_limit", one_summary.get("pose_action_limit", float("nan")))),
                "contact_align_steps": int(payload.get("contact_align_steps", one_summary.get("contact_align_steps", 0))),
                "contact_align_reference": str(
                    payload.get("contact_align_reference", one_summary.get("contact_align_reference", ""))
                ),
                "contact_align_threshold": float(
                    payload.get("contact_align_threshold", one_summary.get("contact_align_threshold", float("nan")))
                ),
                "contact_align_success": bool(payload.get("contact_align_success", False)),
                "pre_close_local_step": int(payload.get("pre_close_local_step", -1)),
                "pre_close_phase": str(payload.get("pre_close_phase", "")),
                "pre_close_ee_to_cube": float(payload.get("pre_close_ee_to_cube", float("nan"))),
                "pre_close_finger_center_to_cube": float(
                    payload.get("pre_close_finger_center_to_cube", float("nan"))
                ),
                "pre_close_finger_error_norm": float(payload.get("pre_close_finger_error_norm", float("nan"))),
                "pre_close_target_reference": str(payload.get("pre_close_target_reference", "")),
                "pre_close_target_minus_cube_norm": float(
                    payload.get("pre_close_target_minus_cube_norm", float("nan"))
                ),
                "reset_joint_blend_alpha": reset_joint_blend_alpha,
                "reset_cube_pos_blend_alpha": reset_cube_pos_blend_alpha,
                "reset_joint_l2_from_source": float(payload.get("reset_joint_l2_from_source", float("nan"))),
                "reset_joint_l2_from_normal": float(payload.get("reset_joint_l2_from_normal", float("nan"))),
                "reset_lowdim_l2_from_dataset": float(payload.get("reset_lowdim_l2_from_dataset", float("nan"))),
                "reset_cube_minus_ee_l2_from_dataset": float(
                    payload.get("reset_cube_minus_ee_l2_from_dataset", float("nan"))
                ),
                "applied_cube_pos": applied_cube_pos,
                "normal_reset_cube_pos": normal_reset_cube_pos,
                "source_cube_pos": source_cube_pos,
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
                "max_raw_pose_action_max_abs": float(payload.get("max_raw_pose_action_max_abs", float("nan"))),
                "max_executed_pose_action_max_abs": float(
                    payload.get("max_executed_pose_action_max_abs", float("nan"))
                ),
                "max_raw_pose_action_would_clip_fraction": float(
                    payload.get("max_raw_pose_action_would_clip_fraction", float("nan"))
                ),
                "min_pose_action_filter_scale": float(payload.get("min_pose_action_filter_scale", float("nan"))),
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
                accepted_rollout_reset_cube_pos_blend_alpha.append(reset_cube_pos_blend_alpha)
                accepted_rollout_applied_cube_pos.append(applied_cube_pos)
                accepted_rollout_normal_reset_cube_pos.append(normal_reset_cube_pos)
                accepted_rollout_source_cube_pos.append(source_cube_pos)

            rgb_npz_raw = str(payload.get("rgb_npz", ""))
            if rgb_npz_raw:
                rgb_npz_path = _container_to_set_path(rgb_npz_raw, set_dir)
                if not rgb_npz_path.exists():
                    sibling_rgb = summary_path.parent / Path(rgb_npz_raw).name
                    if sibling_rgb.exists():
                        rgb_npz_path = sibling_rgb
                if not rgb_npz_path.exists():
                    raise FileNotFoundError(f"Accepted rollout {rollout_id} references missing RGB NPZ: {rgb_npz_raw}")
                rgb_data = np.load(rgb_npz_path, allow_pickle=False)
                image = np.asarray(rgb_data["image"], dtype=np.uint8)
                robot_state = np.asarray(rgb_data["robot_state"], dtype=np.float32)
                rgb_action = np.asarray(rgb_data["action"], dtype=np.float32)
                rgb_phase = np.asarray(rgb_data["phase_ids"], dtype=np.int32)
                if image.ndim != 4 or image.shape[-1] != 3:
                    raise ValueError(f"{rgb_npz_path}: expected image shape (N,H,W,3), got {image.shape}")
                if robot_state.shape != (image.shape[0], 8):
                    raise ValueError(f"{rgb_npz_path}: expected robot_state ({image.shape[0]},8), got {robot_state.shape}")
                if rgb_action.shape != (image.shape[0], 7):
                    raise ValueError(f"{rgb_npz_path}: expected action ({image.shape[0]},7), got {rgb_action.shape}")
                if rgb_phase.shape != (image.shape[0],):
                    raise ValueError(f"{rgb_npz_path}: expected phase_ids ({image.shape[0]},), got {rgb_phase.shape}")
                if image.shape[0] != len(variant_rows):
                    raise ValueError(
                        f"{rgb_npz_path}: RGB rows {image.shape[0]} do not match CSV rows {len(variant_rows)}"
                    )
                accepted_images.append(image)
                accepted_robot_states.append(robot_state)
                accepted_rgb_actions.append(rgb_action)
                accepted_rgb_phase_ids.append(rgb_phase)
                next_end = int(image.shape[0]) if not accepted_rgb_episode_ends else int(accepted_rgb_episode_ends[-1] + image.shape[0])
                accepted_rgb_episode_ends.append(next_end)
                accepted_rgb_rollout_ids.append(rollout_id)
                accepted_rgb_rollout_reset_joint_blend_alpha.append(reset_joint_blend_alpha)
                accepted_rgb_rollout_reset_cube_pos_blend_alpha.append(reset_cube_pos_blend_alpha)
                accepted_rgb_rollout_applied_cube_pos.append(applied_cube_pos)
                accepted_rgb_rollout_normal_reset_cube_pos.append(normal_reset_cube_pos)
                accepted_rgb_rollout_source_cube_pos.append(source_cube_pos)
                if "camera_eye" in rgb_data.files:
                    current_eye = np.asarray(rgb_data["camera_eye"], dtype=np.float32)
                    if rgb_camera_eye is None:
                        rgb_camera_eye = current_eye
                if "camera_target" in rgb_data.files:
                    current_target = np.asarray(rgb_data["camera_target"], dtype=np.float32)
                    if rgb_camera_target is None:
                        rgb_camera_target = current_target
                if "robot_state_names" in rgb_data.files and rgb_robot_state_names is None:
                    rgb_robot_state_names = np.asarray(rgb_data["robot_state_names"]).astype(str)

    output_prefix = args.output_prefix
    rollout_csv = set_dir / f"{output_prefix}_rollouts.csv"
    failure_csv = set_dir / f"{output_prefix}_failures.csv"
    summary_json = set_dir / f"{output_prefix}_summary.json"
    report_md = set_dir / f"{output_prefix}_report.md"
    accepted_npz = set_dir / f"{output_prefix}_accepted.npz"
    accepted_rgb_npz = set_dir / f"{output_prefix}_accepted_rgb.npz"
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
        rollout_reset_cube_pos_blend_alpha=np.asarray(accepted_rollout_reset_cube_pos_blend_alpha, dtype=np.float32),
        rollout_applied_cube_pos=np.asarray(accepted_rollout_applied_cube_pos, dtype=np.float32).reshape((-1, 3)),
        rollout_normal_reset_cube_pos=np.asarray(accepted_rollout_normal_reset_cube_pos, dtype=np.float32).reshape((-1, 3)),
        rollout_source_cube_pos=np.asarray(accepted_rollout_source_cube_pos, dtype=np.float32).reshape((-1, 3)),
    )
    rgb_transition_count = 0
    rgb_episode_count = 0
    if accepted_images:
        image_arr = np.concatenate(accepted_images, axis=0).astype(np.uint8)
        robot_state_arr = np.concatenate(accepted_robot_states, axis=0).astype(np.float32)
        rgb_action_arr = np.concatenate(accepted_rgb_actions, axis=0).astype(np.float32)
        rgb_phase_arr = np.concatenate(accepted_rgb_phase_ids, axis=0).astype(np.int32)
        rgb_episode_ends_arr = np.asarray(accepted_rgb_episode_ends, dtype=np.int64)
        rgb_transition_count = int(image_arr.shape[0])
        rgb_episode_count = int(rgb_episode_ends_arr.shape[0])
        np.savez_compressed(
            accepted_rgb_npz,
            image=image_arr,
            robot_state=robot_state_arr,
            action=rgb_action_arr,
            episode_ends=rgb_episode_ends_arr,
            phase_ids=rgb_phase_arr,
            rollout_ids=np.asarray(accepted_rgb_rollout_ids),
            rollout_reset_joint_blend_alpha=np.asarray(
                accepted_rgb_rollout_reset_joint_blend_alpha, dtype=np.float32
            ),
            rollout_reset_cube_pos_blend_alpha=np.asarray(
                accepted_rgb_rollout_reset_cube_pos_blend_alpha, dtype=np.float32
            ),
            rollout_applied_cube_pos=np.asarray(
                accepted_rgb_rollout_applied_cube_pos, dtype=np.float32
            ).reshape((-1, 3)),
            rollout_normal_reset_cube_pos=np.asarray(
                accepted_rgb_rollout_normal_reset_cube_pos, dtype=np.float32
            ).reshape((-1, 3)),
            rollout_source_cube_pos=np.asarray(
                accepted_rgb_rollout_source_cube_pos, dtype=np.float32
            ).reshape((-1, 3)),
            camera_eye=np.asarray([] if rgb_camera_eye is None else rgb_camera_eye, dtype=np.float32),
            camera_target=np.asarray([] if rgb_camera_target is None else rgb_camera_target, dtype=np.float32),
            robot_state_names=np.asarray(
                [
                    "ee_pos_x",
                    "ee_pos_y",
                    "ee_pos_z",
                    "ee_quat_w",
                    "ee_quat_x",
                    "ee_quat_y",
                    "ee_quat_z",
                    "gripper_width",
                ]
                if rgb_robot_state_names is None
                else rgb_robot_state_names.astype(str).tolist()
            ),
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
        "accepted_rgb_transition_count": rgb_transition_count,
        "accepted_rgb_episode_count": rgb_episode_count,
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
        "accepted_rgb_npz": str(accepted_rgb_npz) if accepted_images else "",
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
