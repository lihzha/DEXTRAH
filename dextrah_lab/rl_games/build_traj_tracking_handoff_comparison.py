"""Build a local handoff comparison report for Franka cube trajectory tracking.

This is an artifact-only utility: it reads already-fetched eval/BC outputs and
does not launch Isaac, Slurm, training, or rollout jobs.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class EvalCandidate:
    name: str
    job_id: str
    run: str
    alpha: str
    role: str
    decision: str
    visual_run: str | None = None
    camera_env: str | None = None


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = REPO_ROOT / "cluster_results" / "l401"

TM025_CHECKPOINT = (
    "/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/"
    "nn/bc_reference_action_imitation.pth"
)
REFERENCE_PATH = (
    "/results/trajectory_references/"
    "franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/"
    "compact_reference.json"
)
PURE_TEACHER_CHECKPOINT = (
    "/results/logs/rl_games/dextrah_franka_cube_traj_tracking/"
    "franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/"
    "nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth"
)
RESIDUAL_CHECKPOINT = (
    "/results/bc/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/"
    "nn/bc_reference_action_imitation.pth"
)


EVAL_CANDIDATES = [
    EvalCandidate(
        name="tm0.25 policy-only alpha0.0",
        job_id="1027988",
        run="franka_cube_traj_tracking_bc_dagger_tm025_select_a000_520_20260611_190200",
        visual_run="franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600",
        alpha="0.00",
        camera_env="0",
        role="policy-only lower-bound",
        decision="not usable for RL handoff: 0/4 success and no lift",
    ),
    EvalCandidate(
        name="tm0.25 teacher-assisted alpha0.5",
        job_id="1027989",
        run="franka_cube_traj_tracking_bc_dagger_tm025_select_a050_520_20260611_190200",
        visual_run="franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600",
        alpha="0.50",
        camera_env="0",
        role="lowest verified assisted success",
        decision="usable only as teacher-assisted trajectory-tracking curriculum evidence",
    ),
    EvalCandidate(
        name="tm0.25 teacher-assisted alpha0.75",
        job_id="1027990",
        run="franka_cube_traj_tracking_bc_dagger_tm025_select_a075_520_20260611_190200",
        visual_run="franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600",
        alpha="0.75",
        camera_env="0",
        role="assisted success",
        decision="usable only as teacher-assisted trajectory-tracking curriculum evidence",
    ),
    EvalCandidate(
        name="tm0.25 full teacher alpha1.0",
        job_id="1027991",
        run="franka_cube_traj_tracking_bc_dagger_tm025_select_a100_520_20260611_190200",
        visual_run="franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600",
        alpha="1.00",
        camera_env="1",
        role="full-teacher context",
        decision="reference/teacher ceiling; not learned policy-only behavior",
    ),
    EvalCandidate(
        name="pure reference/teacher-force alpha1.0 phase1.0",
        job_id="1027919",
        run="franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848",
        visual_run="franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848",
        alpha="1.00",
        camera_env="default",
        role="reference feasibility ceiling",
        decision="reference path viable; blocker is learned handoff, not transform/controller feasibility",
    ),
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def _metric(summary: dict[str, Any], key: str, field: str = "mean") -> float | None:
    record = summary.get("metric_summaries", {}).get(key, {})
    value = record.get(field) if isinstance(record, dict) else None
    return float(value) if isinstance(value, (int, float)) else None


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _md_link(label: str, path: Path, report_dir: Path) -> str:
    if not path.exists():
        return "missing"
    rel = path.relative_to(report_dir) if path.is_relative_to(report_dir) else Path("..") / path.relative_to(LOCAL_ROOT)
    return f"[{label}]({rel.as_posix()})"


def _eval_row(candidate: EvalCandidate) -> dict[str, Any]:
    metrics_path = LOCAL_ROOT / candidate.run / "metrics.json"
    payload = _read_json(metrics_path)
    summary = payload.get("summary", {})
    env_cfg = summary.get("env_config", {}) if isinstance(summary, dict) else {}
    num_envs = int(env_cfg.get("scene_num_envs") or len(summary.get("success_ever_by_env", [])) or 4)
    success_final = float(summary.get("success_rate_final", _metric(summary, "success_rate", "final") or 0.0))
    success_ever = float(summary.get("success_ever_rate", 0.0))
    target_unsafe = _metric(summary, "cube_traj_tracking_unsafe_target_rate", "max")
    target_clearance = _metric(summary, "cube_traj_tracking_target_table_clearance", "min")
    row = {
        "candidate": candidate.name,
        "job_id": candidate.job_id,
        "run": candidate.run,
        "role": candidate.role,
        "alpha": candidate.alpha,
        "camera_env": candidate.camera_env or "",
        "checkpoint": str(summary.get("checkpoint") or (PURE_TEACHER_CHECKPOINT if candidate.job_id == "1027919" else TM025_CHECKPOINT)),
        "reference_path": str(env_cfg.get("trajectory_tracking_reference_path") or REFERENCE_PATH),
        "curobo_validated": False,
        "num_envs": num_envs,
        "success_final_count": round(success_final * num_envs),
        "success_final_rate": success_final,
        "success_ever_count": int(summary.get("success_ever_count", round(success_ever * num_envs))),
        "success_ever_rate": success_ever,
        "lift_max_m": _metric(summary, "cube_lift_height", "max"),
        "lift_final_m": _metric(summary, "cube_lift_height", "final"),
        "target_unsafe_max": target_unsafe,
        "target_clearance_min_m": target_clearance,
        "ee_to_cube_final_m": _metric(summary, "ee_to_cube_dist", "final"),
        "finger_center_to_cube_final_m": _metric(summary, "finger_center_to_cube_dist", "final"),
        "raw_ref_l2_mean": _metric(summary, "cube_traj_tracking_raw_policy_reference_action_error_l2", "mean"),
        "applied_ref_l2_mean": _metric(summary, "cube_traj_tracking_applied_reference_action_error_l2", "mean"),
        "teacher_alpha_mean": _metric(summary, "cube_traj_tracking_teacher_force_alpha", "mean"),
        "teacher_alpha_final": _metric(summary, "cube_traj_tracking_teacher_force_alpha", "final"),
        "obs_dim": env_cfg.get("observation_space"),
        "action_dim": env_cfg.get("action_space"),
        "cube_spawn_xy_randomization": env_cfg.get("cube_spawn_xy_randomization"),
        "action_alignment_weight": env_cfg.get("trajectory_tracking_action_alignment_weight"),
        "close_action_weight": env_cfg.get("trajectory_tracking_close_action_weight"),
        "lift_action_weight": env_cfg.get("trajectory_tracking_lift_action_weight"),
        "reference_transform_policy": "transform_task_space_waypoints_by_cube_pose",
        "joint_trajectory_policy": "do_not_transform_joint_trajectories",
        "decision": candidate.decision,
        "metrics_path": str(metrics_path),
    }
    return row


def _artifact_paths(candidate: EvalCandidate, report_dir: Path) -> dict[str, str]:
    visual_run = candidate.visual_run or candidate.run
    artifact_dir = LOCAL_ROOT / f"{visual_run}_artifacts"
    run_dir = LOCAL_ROOT / visual_run
    videos = sorted((run_dir / "videos").glob("*.mp4"))
    return {
        "report": _md_link("report", artifact_dir / "report.md", report_dir),
        "trace_plot": _md_link("trace plot", artifact_dir / "trajectory_trace_plot.png", report_dir),
        "contact_sheet": _md_link("contact sheet", artifact_dir / "video_contact_sheet.png", report_dir),
        "usable_sheet": _md_link("usable sheet", artifact_dir / "usable_frame_contact_sheet.png", report_dir),
        "video": _md_link("video", videos[0], report_dir) if videos else "missing",
    }


def _load_residual_control() -> dict[str, Any]:
    run = "franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500"
    metrics_path = LOCAL_ROOT / run / "bc_metrics.json"
    metrics = _read_json(metrics_path)
    final = metrics.get("selected") or metrics.get("final", {})
    return {
        "candidate": "gated residual max1.5 alpha0.10 control",
        "job_id": "1028122",
        "run": run,
        "checkpoint": metrics.get("output_checkpoint") or RESIDUAL_CHECKPOINT,
        "input_checkpoint": metrics.get("input_checkpoint") or TM025_CHECKPOINT,
        "reference_path": (metrics.get("reference_summary") or {}).get("source") or REFERENCE_PATH,
        "curobo_validated": bool(metrics.get("curobo_validated", False)),
        "obs_dim": metrics.get("obs_dim"),
        "action_dim": metrics.get("action_dim"),
        "collection_action_source": metrics.get("collection_action_source"),
        "collection_teacher_alpha": metrics.get("collection_teacher_alpha"),
        "global_val_l2": final.get("val_l2"),
        "current_alpha010_val_l2": final.get("val_source_current_teacher_mix_alpha0p10_l2"),
        "tm025_rehearsal_val_l2": final.get("val_source_tm025_rehearsal_l2"),
        "current_alpha010_close_up_gripper": [
            final.get("val_source_current_teacher_mix_alpha0p10_close_abs"),
            final.get("val_source_current_teacher_mix_alpha0p10_up_abs"),
            final.get("val_source_current_teacher_mix_alpha0p10_gripper_abs"),
        ],
        "tm025_close_up_gripper": [
            final.get("val_source_tm025_rehearsal_close_abs"),
            final.get("val_source_tm025_rehearsal_up_abs"),
            final.get("val_source_tm025_rehearsal_gripper_abs"),
        ],
        "current_gate_mean": final.get("val_residual_gate_source_current_teacher_mix_alpha0p10_mean"),
        "tm025_gate_mean": final.get("val_residual_gate_source_tm025_rehearsal_mean"),
        "decision": "supervised gate failure; no rollout/video/PPO launched",
        "report": str(LOCAL_ROOT / run / "report.md"),
        "source_plot": str(LOCAL_ROOT / run / "bc_source_metric_plot.png"),
        "oracle_plot": str(LOCAL_ROOT / run / "oracle_residual_plot.png"),
    }


def _draw_plot(eval_rows: list[dict[str, Any]], residual: dict[str, Any], output: Path) -> None:
    width, height = 1200, 760
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = font_b = font_s = None
    draw.text((42, 28), "Trajectory-Tracking Handoff Comparison", fill=(20, 20, 20), font=font_b)
    chart_x, chart_y = 84, 110
    chart_w, chart_h = 980, 360
    draw.rectangle((chart_x, chart_y, chart_x + chart_w, chart_y + chart_h), outline=(180, 180, 180))
    for i in range(5):
        y = chart_y + chart_h - i * chart_h / 4
        draw.line((chart_x, y, chart_x + chart_w, y), fill=(225, 225, 225))
        draw.text((20, y - 9), f"{i/4:.2f}", fill=(70, 70, 70), font=font_s)
    labels = ["a0", "a0.5", "a0.75", "a1", "ref"]
    n = len(eval_rows)
    slot = chart_w / n
    for idx, (row, label) in enumerate(zip(eval_rows, labels, strict=False)):
        x0 = chart_x + idx * slot + 34
        bar_w = 50
        success = float(row.get("success_final_rate") or 0.0)
        lift = min(float(row.get("lift_max_m") or 0.0) / 0.20, 1.0)
        sy = chart_y + chart_h - success * chart_h
        ly = chart_y + chart_h - lift * chart_h
        draw.rectangle((x0, sy, x0 + bar_w, chart_y + chart_h), fill=(46, 125, 50))
        draw.rectangle((x0 + bar_w + 8, ly, x0 + 2 * bar_w + 8, chart_y + chart_h), fill=(33, 117, 180))
        draw.text((x0 - 4, chart_y + chart_h + 12), label, fill=(20, 20, 20), font=font)
        draw.text((x0 - 2, sy - 24), f"{row['success_final_count']}/{row['num_envs']}", fill=(46, 125, 50), font=font_s)
        draw.text((x0 + bar_w + 6, ly - 24), f"{float(row.get('lift_max_m') or 0):.3f}", fill=(33, 117, 180), font=font_s)
    draw.rectangle((84, 515, 104, 535), fill=(46, 125, 50))
    draw.text((114, 512), "final success rate", fill=(20, 20, 20), font=font)
    draw.rectangle((330, 515, 350, 535), fill=(33, 117, 180))
    draw.text((360, 512), "max lift, normalized to 0.20 m", fill=(20, 20, 20), font=font)
    draw.text((84, 580), "Residual negative/control:", fill=(20, 20, 20), font=font_b)
    draw.text(
        (84, 622),
        (
            f"tm0.25 L2={_fmt(residual.get('tm025_rehearsal_val_l2'))}, "
            f"current alpha0.10 L2={_fmt(residual.get('current_alpha010_val_l2'))}; "
            "supervised gate failed, so no rollout was launched."
        ),
        fill=(60, 60, 60),
        font=font,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def _write_csv(rows: list[dict[str, Any]], residual: dict[str, Any], output: Path) -> None:
    keys = [
        "candidate",
        "job_id",
        "role",
        "alpha",
        "num_envs",
        "success_final_count",
        "success_final_rate",
        "success_ever_count",
        "lift_max_m",
        "target_unsafe_max",
        "target_clearance_min_m",
        "ee_to_cube_final_m",
        "finger_center_to_cube_final_m",
        "raw_ref_l2_mean",
        "applied_ref_l2_mean",
        "teacher_alpha_mean",
        "checkpoint",
        "reference_path",
        "curobo_validated",
        "decision",
    ]
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in keys})
        writer.writerow(
            {
                "candidate": residual["candidate"],
                "job_id": residual["job_id"],
                "role": "supervised negative/control",
                "checkpoint": residual["checkpoint"],
                "reference_path": residual["reference_path"],
                "curobo_validated": residual["curobo_validated"],
                "decision": residual["decision"],
            }
        )


def _write_report(rows: list[dict[str, Any]], residual: dict[str, Any], report_dir: Path, plot_path: Path) -> None:
    old_video = LOCAL_ROOT / "franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318" / "videos" / "actionscale-rewinf-diag-video480-step-0.mp4"
    lines: list[str] = []
    lines.append("# Franka Cube Trajectory-Tracking Handoff Diagnostic")
    lines.append("")
    lines.append("This report is a local artifact-only comparison from already completed runs. No new training, PPO, or selector rollout was launched for this handoff diagnostic.")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append("- `tm0.25` remains the best Worker B checkpoint for teacher-assisted trajectory tracking: alpha `0.5`, `0.75`, and `1.0` each reach `3/4` final success with target unsafe max `0` and visually verified lifts.")
    lines.append("- Policy-only alpha `0.0` remains unusable for RL handoff: `0/4` success, max lift `0`, and the targeted video shows no lift.")
    lines.append("- The full teacher/reference-force path is viable: alpha `1.0`, phase end `1.0` reaches `3/4` final success and max lift `0.1444 m`; this rules out basic reference-transform/controller impossibility.")
    lines.append("- The latest gated residual checkpoint is a supervised negative/control only: it preserved tm0.25 but left current alpha `0.10` error too high, so it was not rolled out.")
    lines.append("- Do not scale PPO/RL from current B evidence. A usable RL path must first make policy-only or lower-teacher handoff work visually and metrically.")
    lines.append("")
    lines.append(f"Comparison plot: {_md_link('handoff_success_lift_plot.png', plot_path, report_dir)}")
    lines.append("")
    lines.append("## Candidate Metrics")
    lines.append("")
    lines.append("| Candidate | Job | Role | Alpha | Final success | Ever success | Max lift (m) | Target unsafe max | Clearance min (m) | EE/finger final (m) | Raw/ref L2 | Applied/ref L2 | Decision |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |")
    for row in rows:
        lines.append(
            "| {candidate} | {job_id} | {role} | {alpha} | {success_final_count}/{num_envs} | {success_ever_count}/{num_envs} | {lift_max} | {unsafe} | {clearance} | {ee}/{finger} | {raw_ref} | {applied_ref} | {decision} |".format(
                candidate=row["candidate"],
                job_id=row["job_id"],
                role=row["role"],
                alpha=row["alpha"],
                success_final_count=row["success_final_count"],
                num_envs=row["num_envs"],
                success_ever_count=row["success_ever_count"],
                lift_max=_fmt(row["lift_max_m"]),
                unsafe=_fmt(row["target_unsafe_max"]),
                clearance=_fmt(row["target_clearance_min_m"]),
                ee=_fmt(row["ee_to_cube_final_m"]),
                finger=_fmt(row["finger_center_to_cube_final_m"]),
                raw_ref=_fmt(row["raw_ref_l2_mean"]),
                applied_ref=_fmt(row["applied_ref_l2_mean"]),
                decision=row["decision"],
            )
        )
    lines.append("")
    lines.append("## Visual And Trace Artifacts")
    lines.append("")
    lines.append("| Candidate | Report | Trace plot | Contact sheet | Usable sheet | Video |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for candidate in EVAL_CANDIDATES:
        paths = _artifact_paths(candidate, report_dir)
        lines.append(
            f"| {candidate.name} | {paths['report']} | {paths['trace_plot']} | {paths['contact_sheet']} | {paths['usable_sheet']} | {paths['video']} |"
        )
    lines.append("")
    lines.append("Action-semantics comparison for the tm0.25 targeted visual bundle:")
    action_dir = LOCAL_ROOT / "franka_cube_traj_tracking_bc_dagger_tm025_visual_action_semantics_20260611_1906"
    lines.append(f"- {_md_link('action_semantics_report.md', action_dir / 'action_semantics_report.md', report_dir)}")
    lines.append(f"- {_md_link('action_semantics_plot.png', action_dir / 'action_semantics_plot.png', report_dir)}")
    lines.append("")
    lines.append("## Train/Eval Match Audit")
    lines.append("")
    lines.append("| Candidate | Checkpoint | Reference path | `curobo_validated` | Obs/action dim | Cube randomization | Teacher/mix settings | Reward/action terms | Consistency |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        visual = next((c.visual_run for c in EVAL_CANDIDATES if c.name == row["candidate"]), None)
        consistency = {}
        if visual:
            consistency = _read_json(LOCAL_ROOT / f"{visual}_artifacts" / "train_eval_consistency.json")
        status = "passed" if consistency.get("passed") is True else ("missing sidecar" if not consistency else consistency.get("status", "check"))
        terms = f"align={_fmt(row['action_alignment_weight'])}, close={_fmt(row['close_action_weight'])}, lift={_fmt(row['lift_action_weight'])}"
        mix = f"teacher_alpha_mean/final={_fmt(row['teacher_alpha_mean'])}/{_fmt(row['teacher_alpha_final'])}, eval alpha={row['alpha']}"
        lines.append(
            f"| {row['candidate']} | `{row['checkpoint']}` | `{row['reference_path']}` | `{row['curobo_validated']}` | {row['obs_dim']}/{row['action_dim']} | {row['cube_spawn_xy_randomization']} | {mix} | {terms} | {status} |"
        )
    lines.append("")
    lines.append("Reference configuration is still a compact GraspGenX/cuRobo-exported task-space reference with `curobo_validated=false`, `runtime_object_pose_policy=reset_cube_pose`, `transform_policy=transform_task_space_waypoints_by_cube_pose`, `joint_trajectory_policy=do_not_transform_joint_trajectories`, and target-unsafe tracking weight zeroed below the table-clearance threshold.")
    lines.append("")
    lines.append("## Gated Residual Negative/Control")
    lines.append("")
    lines.append("| Job | Checkpoint | tm0.25 val L2 | current alpha0.10 val L2 | global val L2 | close/up/gripper current | Decision |")
    lines.append("| ---: | --- | ---: | ---: | ---: | --- | --- |")
    current_cug = residual.get("current_alpha010_close_up_gripper") or []
    lines.append(
        f"| {residual['job_id']} | `{residual['checkpoint']}` | {_fmt(residual['tm025_rehearsal_val_l2'])} | {_fmt(residual['current_alpha010_val_l2'])} | {_fmt(residual['global_val_l2'])} | "
        f"{'/'.join(_fmt(v) for v in current_cug)} | {residual['decision']} |"
    )
    residual_dir = LOCAL_ROOT / str(residual["run"])
    lines.append("")
    lines.append(f"- Residual report: {_md_link('report.md', residual_dir / 'report.md', report_dir)}")
    lines.append(f"- Residual source plot: {_md_link('bc_source_metric_plot.png', residual_dir / 'bc_source_metric_plot.png', report_dir)}")
    lines.append(f"- Residual oracle plot: {_md_link('oracle_residual_plot.png', residual_dir / 'oracle_residual_plot.png', report_dir)}")
    lines.append("")
    lines.append("## Obsolete Failed Artifact")
    lines.append("")
    lines.append(f"- Job `1027753` / `actionscale-rewinf-diag-video480-step-0.mp4` is obsolete failed learned-policy evidence, not a current success or handoff candidate: {_md_link('old obsolete video', old_video, report_dir)}")
    lines.append("")
    lines.append("## Next Supervised-Only Direction")
    lines.append("")
    lines.append("- The useful handoff signal is the tm0.25 assisted manifold, not lower-teacher alpha0.10 states collected off a failing policy manifold.")
    lines.append("- The next bounded fix should stay supervised-only and preserve tm0.25 behavior while training on states sampled from the visually successful alpha0.5/0.75 rollouts, with explicit action/phase labels and a held-out policy-only probe before any selector rollout.")
    lines.append("- A safer formulation is a stage-conditioned handoff: keep reference/teacher assistance through approach/grasp, then train a small policy-only stabilization/hold head from successful hold states. This targets the observed failure directly instead of forcing one actor to cover both off-manifold alpha0.10 and tm0.25 states.")
    lines.append("")
    lines.append("## Machine-Readable Files")
    lines.append("")
    lines.append("- `summary.json`")
    lines.append("- `summary.csv`")
    lines.append("- `handoff_success_lift_plot.png`")
    (report_dir / "report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = args.output_dir or LOCAL_ROOT / f"franka_cube_traj_tracking_handoff_comparison_{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = [_eval_row(candidate) for candidate in EVAL_CANDIDATES]
    residual = _load_residual_control()
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(REPO_ROOT),
        "eval_candidates": rows,
        "residual_control": residual,
        "obsolete_failed_artifact": {
            "job_id": "1027753",
            "path": str(
                LOCAL_ROOT
                / "franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318"
                / "videos"
                / "actionscale-rewinf-diag-video480-step-0.mp4"
            ),
            "status": "obsolete_failed_diagnostic",
        },
    }
    (report_dir / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_csv(rows, residual, report_dir / "summary.csv")
    plot_path = report_dir / "handoff_success_lift_plot.png"
    _draw_plot(rows, residual, plot_path)
    _write_report(rows, residual, report_dir, plot_path)
    print(report_dir)


if __name__ == "__main__":
    main()
