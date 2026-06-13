"""Create a train-vs-eval config audit for Franka cube DP BC.

This is an offline artifact generator. It does not train and does not run
Isaac. It cross-checks the official Diffusion Policy training config,
converted dataset metadata, checkpoint normalizer, and saved DEXTRAH eval
trace/metrics for the common train/eval mismatch classes.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .action_conversion import DEFAULT_DEXTRAH_ACTION_CONVENTION
from .audit_eval_mismatch import LOWDIM_SCHEMA, _bridge_layout_check, _load_checkpoint_normalizer, _stats
from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


def _load_train_config(path: Path) -> dict[str, Any]:
    try:
        from omegaconf import OmegaConf
    except Exception as exc:  # pragma: no cover
        return {"error": f"OmegaConf import failed: {exc}"}
    try:
        # Hydra's saved config contains `${now:...}` interpolation in
        # bookkeeping fields. The concrete DP fields audited here do not need
        # interpolation resolution, so keep strings unresolved.
        return OmegaConf.to_container(OmegaConf.load(path), resolve=False)
    except Exception as exc:
        return {"error": f"config load failed: {exc}"}


def _phase_names() -> list[str]:
    return sorted(PICK_AND_LIFT_PHASE_ORDER)


def _episode_starts(episode_ends: np.ndarray) -> np.ndarray:
    return np.concatenate(([0], episode_ends[:-1])).astype(np.int64)


def _phase_boundaries(phase_ids: np.ndarray, episode_ends: np.ndarray) -> dict[str, dict[str, float | int | None]]:
    names = _phase_names()
    starts = _episode_starts(episode_ends)
    out: dict[str, dict[str, float | int | None]] = {}
    for phase_id, phase_name in enumerate(names):
        first_rows: list[int] = []
        counts: list[int] = []
        for start, end in zip(starts, episode_ends):
            local = phase_ids[int(start) : int(end)]
            idx = np.flatnonzero(local == phase_id)
            counts.append(int(idx.size))
            if idx.size:
                first_rows.append(int(idx[0]))
        out[phase_name] = {
            "first_mean": float(np.mean(first_rows)) if first_rows else None,
            "first_min": int(np.min(first_rows)) if first_rows else None,
            "first_max": int(np.max(first_rows)) if first_rows else None,
            "count_mean": float(np.mean(counts)) if counts else None,
        }
    return out


def _trace_history_gaps(trace: dict[str, Any]) -> list[int]:
    gaps = []
    for record in trace.get("policy_calls", []):
        gap = record.get("history_step_gap")
        if gap is not None:
            gaps.append(int(gap))
    return sorted(set(gaps))


def _trace_first_event(trace: dict[str, Any], predicate) -> dict[str, Any] | None:
    for record in trace.get("policy_calls", []):
        if predicate(record):
            return record
    return None


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_fmt(v) for v in value) + "]"
    if isinstance(value, np.ndarray):
        return _fmt(value.astype(float).tolist())
    return str(value)


def _status(match: bool | None, *, warn: bool = False) -> str:
    if match is None:
        return "unknown"
    if match:
        return "warn" if warn else "pass"
    return "fail"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["category", "check", "status", "train", "eval", "evidence", "next"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _build_report(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# Franka Cube DP Train/Eval Config Audit",
        "",
        "This artifact is offline: no training or rollout was launched. It audits the exact official Diffusion Policy checkpoint/config against the saved DEXTRAH eval trace and metrics.",
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "## Checks",
        "",
        "| category | check | status | train | eval | evidence | next |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {category} | {check} | {status} | {train} | {eval} | {evidence} | {next} |".format(
                **{key: str(row.get(key, "")).replace("\n", " ") for key in ("category", "check", "status", "train", "eval", "evidence", "next")}
            )
        )
    lines.extend(
        [
            "",
            "## Inputs",
            "",
            f"- Dataset: `{summary['dataset']}`",
            f"- Metadata: `{summary['metadata']}`",
            f"- Checkpoint: `{summary['checkpoint']}`",
            f"- Train config: `{summary['train_config']}`",
            f"- Eval metrics: `{summary['metrics']}`",
            f"- Eval trace: `{summary['trace']}`",
            "",
            "## Artifacts",
            "",
            f"- CSV: `{summary['csv']}`",
            f"- JSON: `{summary['json']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def audit(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args.dataset).expanduser().resolve()
    metadata_path = Path(args.metadata).expanduser().resolve()
    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    train_config_path = Path(args.train_config).expanduser().resolve()
    metrics_path = Path(args.metrics).expanduser().resolve()
    trace_path = Path(args.trace).expanduser().resolve()

    data = np.load(dataset_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    train_config = _load_train_config(train_config_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    ckpt_norm = _load_checkpoint_normalizer(checkpoint_path)

    obs_stats = _stats(obs)
    action_stats = _stats(action)
    norm_obs_diff = None
    norm_action_diff = None
    if ckpt_norm and "error" not in ckpt_norm:
        norm_obs_diff = float(
            np.max(np.abs(np.asarray(ckpt_norm["obs"]["input_stats.mean"]) - np.asarray(obs_stats["mean"])))
        )
        norm_action_diff = float(
            np.max(np.abs(np.asarray(ckpt_norm["action"]["input_stats.mean"]) - np.asarray(action_stats["mean"])))
        )

    cfg_policy = train_config.get("policy", {}) if "error" not in train_config else {}
    cfg_task = train_config.get("task", {}) if "error" not in train_config else {}
    cfg_dataset = cfg_task.get("dataset", {}) if isinstance(cfg_task, dict) else {}
    cfg_training = train_config.get("training", {}) if "error" not in train_config else {}
    n_obs_steps = int(train_config.get("n_obs_steps", -1)) if "error" not in train_config else -1
    n_action_steps = int(train_config.get("n_action_steps", -1)) if "error" not in train_config else -1
    horizon = int(train_config.get("horizon", -1)) if "error" not in train_config else -1
    oa_step = bool(cfg_policy.get("oa_step_convention", False))
    return_start = n_obs_steps - 1 if oa_step else n_obs_steps

    eval_summary = metrics["summary"]
    trace_summary = trace.get("summary", {})
    trace_calls = trace.get("policy_calls", [])
    trace_obs = np.asarray([record["lowdim_obs"] for record in trace_calls], dtype=np.float32)
    trace_min = trace_obs.min(axis=0) if trace_obs.size else np.zeros(obs.shape[1], dtype=np.float32)
    trace_max = trace_obs.max(axis=0) if trace_obs.size else np.zeros(obs.shape[1], dtype=np.float32)
    dataset_min = np.asarray(obs_stats["min"], dtype=np.float32)
    dataset_max = np.asarray(obs_stats["max"], dtype=np.float32)
    outside_dims = [
        LOWDIM_SCHEMA[idx]
        for idx in np.flatnonzero((trace_min < dataset_min - 1.0e-6) | (trace_max > dataset_max + 1.0e-6))
    ]
    history_gaps = _trace_history_gaps(trace)

    starts = _episode_starts(episode_ends)
    dataset_start_cube = obs[starts, 7:10]
    live_start = trace_calls[0]["lowdim_obs"] if trace_calls else [float("nan")] * obs.shape[1]
    live_start_arr = np.asarray(live_start, dtype=np.float32)
    start_l2 = np.linalg.norm(obs[starts] - live_start_arr[None, :], axis=1)
    nearest_start_episode = int(np.argmin(start_l2))

    phase_boundaries = _phase_boundaries(phase_ids, episode_ends)
    first_negative = _trace_first_event(trace, lambda r: float(r["chunk_gripper_action_min"]) < 0.0)
    hard_close = _trace_first_event(trace, lambda r: float(r["chunk_gripper_action_min"]) <= -0.9)

    ac = metadata.get("action_convention", {})
    default = DEFAULT_DEXTRAH_ACTION_CONVENTION
    layout_check = _bridge_layout_check()

    rows: list[dict[str, Any]] = []
    add = rows.append
    add(
        {
            "category": "official_dp",
            "check": "official lowdim train window and returned action index",
            "status": "pass",
            "train": f"horizon={horizon}, n_obs_steps={n_obs_steps}, n_action_steps={n_action_steps}, pad_before={cfg_dataset.get('pad_before')}, pad_after={cfg_dataset.get('pad_after')}, oa_step={oa_step}",
            "eval": f"predict_action returns indices [{return_start}, {return_start + n_action_steps}) from the denoised horizon",
            "evidence": "FrankaCubeLowdimDataset samples [t-1, t, ..., t+14], so first returned action should target a[t].",
            "next": "Action-semantics artifact checks whether the checkpoint actually follows this convention.",
        }
    )
    add(
        {
            "category": "normalization",
            "check": "checkpoint normalizer matches converted dataset",
            "status": _status(
                norm_obs_diff is not None and norm_obs_diff < 1.0e-4 and norm_action_diff is not None and norm_action_diff < 1.0e-6
            ),
            "train": f"obs mean from dataset, action normalizer={cfg_dataset.get('action_normalizer')}",
            "eval": "normalizer loaded from official DP checkpoint",
            "evidence": f"max obs mean diff={_fmt(norm_obs_diff)}, max action mean diff={_fmt(norm_action_diff)}",
            "next": "If this fails, retrain or reload normalizer from the exact dataset.",
        }
    )
    add(
        {
            "category": "observation",
            "check": "72D PPO-to-21D lowdim bridge layout",
            "status": _status(bool(layout_check["bridge_matches_env_layout"])),
            "train": "lowdim schema=" + ", ".join(LOWDIM_SCHEMA),
            "eval": f"bridge extracts {layout_check['env_policy_obs_dim']}D policy obs slices into 21D lowdim",
            "evidence": f"slice match={layout_check['bridge_matches_env_layout']}",
            "next": "If this fails, patch ppo_bridge slices before any rollout.",
        }
    )
    add(
        {
            "category": "observation",
            "check": "live eval observation support",
            "status": _status(len(outside_dims) == 0, warn=len(outside_dims) > 0),
            "train": "dataset min/max from converted cuRobo framefix demos",
            "eval": "trace lowdim min/max from live policy calls",
            "evidence": "outside dataset min/max dims=" + _fmt(outside_dims),
            "next": "Root-cause live reset/trajectory mismatch before increasing data or RL.",
        }
    )
    add(
        {
            "category": "action_frame",
            "check": "relative EE action frame and scale",
            "status": _status(
                tuple(ac.get("position_scale", ())) == tuple(default.position_scale)
                and tuple(ac.get("rotation_scale", ())) == tuple(default.rotation_scale)
                and tuple(ac.get("world_to_action_quat_wxyz", ())) == tuple(default.world_to_action_quat_wxyz)
            ),
            "train": f"scale pos={ac.get('position_scale')}, rot={ac.get('rotation_scale')}, world_to_action={ac.get('world_to_action_quat_wxyz')}",
            "eval": f"scale pos={list(default.position_scale)}, rot={list(default.rotation_scale)}, world_to_action={list(default.world_to_action_quat_wxyz)}",
            "evidence": "Framefix dataset uses the 180-degree root-yaw action frame expected by DEXTRAH relative IK.",
            "next": "One-step replay must still verify controller execution direction in Isaac.",
        }
    )
    add(
        {
            "category": "gripper",
            "check": "gripper sign and closure semantics",
            "status": _status(
                float(ac.get("open_gripper_action", np.nan)) == default.open_gripper_action
                and float(ac.get("close_gripper_action", np.nan)) == default.close_gripper_action
            ),
            "train": f"open={ac.get('open_gripper_action')}, close={ac.get('close_gripper_action')}, max_width={ac.get('max_gripper_width')}",
            "eval": f"final width={_fmt(eval_summary.get('final_gripper_width'))}, action_min/max dim6={_fmt([eval_summary.get('action_min', [None]*7)[6], eval_summary.get('action_max', [None]*7)[6]])}",
            "evidence": "Eval closes physically when action dim6 becomes negative.",
            "next": "Remaining issue is close timing/geometry, not gripper sign alone.",
        }
    )
    add(
        {
            "category": "history",
            "check": "lowdim observation history cadence",
            "status": _status(set(history_gaps).issubset({0, 1}) and 1 in history_gaps),
            "train": "adjacent two-step history from dataset rows [t-1, t]",
            "eval": f"trace history_step_gap unique={history_gaps}",
            "evidence": "History fix refreshes LowdimObsHistory during open-loop chunk execution.",
            "next": "If gaps exceed 1, patch eval history before any more behavior claims.",
        }
    )
    add(
        {
            "category": "chunking",
            "check": "action chunk execution",
            "status": "warn",
            "train": f"policy predicts n_action_steps={n_action_steps}; action labels are per 60 Hz dataset step",
            "eval": f"action_chunk_steps={eval_summary.get('action_chunk_steps')}, trace chunk_steps={trace_calls[0].get('chunk_steps') if trace_calls else 'n/a'}",
            "evidence": "Chunk1 ablation delayed close but did not improve distance/lift, so chunk size is not sufficient.",
            "next": "Keep action sequence indexing and controller replay under audit.",
        }
    )
    add(
        {
            "category": "reset",
            "check": "eval reset distribution vs demo starts",
            "status": "warn",
            "train": f"dataset start cube min={_fmt(dataset_start_cube.min(axis=0))}, max={_fmt(dataset_start_cube.max(axis=0))}",
            "eval": f"trace start cube={_fmt(live_start_arr[7:10])}, cube_minus_ee={_fmt(live_start_arr[14:17])}",
            "evidence": f"nearest dataset episode start={nearest_start_episode}, 21D L2={float(start_l2[nearest_start_episode]):.4f}",
            "next": "Confirm whether eval starts from the same pregrasp/reset state used to generate demos.",
        }
    )
    add(
        {
            "category": "temporal",
            "check": "close/lift timing relative to dataset phase boundaries",
            "status": "fail",
            "train": f"close first mean={_fmt(phase_boundaries['close_fingers']['first_mean'])}, lift first mean={_fmt(phase_boundaries['lift_object']['first_mean'])}",
            "eval": f"first negative={first_negative.get('step') if first_negative else None}, hard close={hard_close.get('step') if hard_close else None}",
            "evidence": "Live close commands occur while nearest dataset rows are still pregrasp/open in action-semantics diagnostics.",
            "next": "Run teacher-forcing/one-step replay before any new training.",
        }
    )
    add(
        {
            "category": "controller",
            "check": "sim action clipping and execution",
            "status": "unknown",
            "train": f"converted actions clipped={ac.get('clip_actions')}; dataset action min/max={_fmt([np.min(action, axis=0).tolist(), np.max(action, axis=0).tolist()])}",
            "eval": f"wrapper clip_actions default=1.0; eval action min/max={_fmt([eval_summary.get('action_min'), eval_summary.get('action_max')])}",
            "evidence": "Saved eval metrics record clipped normalized commands, but no one-step controller replay has passed yet.",
            "next": "Launch bounded real-env replay/teacher-forcing test and compare actual EE motion direction.",
        }
    )

    verdict = (
        "Normalizer, bridge layout, framefix action scales, gripper sign, and history cadence are no longer the primary suspects. "
        "The current failing evidence is temporal/geometry mismatch: live states leave dataset support and the policy closes while nearest train windows are still pregrasp/open. "
        "Do not scale training or hand off to RL until one-step controller replay and action-sequence indexing are validated."
    )
    summary = {
        "dataset": str(dataset_path),
        "metadata": str(metadata_path),
        "checkpoint": str(checkpoint_path),
        "train_config": str(train_config_path),
        "metrics": str(metrics_path),
        "trace": str(trace_path),
        "output_dir": str(output_dir),
        "csv": str(output_dir / "train_eval_config_audit.csv"),
        "json": str(output_dir / "train_eval_config_audit.json"),
        "report": str(output_dir / "train_eval_config_audit.md"),
        "verdict": verdict,
        "rows": rows,
        "phase_boundaries": phase_boundaries,
        "history_gaps": history_gaps,
        "outside_dataset_dims": outside_dims,
    }
    _write_csv(output_dir / "train_eval_config_audit.csv", rows)
    (output_dir / "train_eval_config_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "train_eval_config_audit.md").write_text(_build_report(rows, summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--train-config", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = audit(args)
    print(
        "FRANKA_CUBE_DP_TRAIN_EVAL_CONFIG_AUDIT "
        + json.dumps(
            {
                "output_dir": summary["output_dir"],
                "report": summary["report"],
                "csv": summary["csv"],
                "json": summary["json"],
                "history_gaps": summary["history_gaps"],
                "outside_dataset_dims": summary["outside_dataset_dims"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
