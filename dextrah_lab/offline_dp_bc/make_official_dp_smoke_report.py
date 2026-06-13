"""Summarize a bounded official Diffusion Policy smoke run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CHECKPOINT_PREFIX = "FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED "


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _read_prefixed_payload(path: Path, prefix: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return json.loads(line[len(prefix) :])
    return None


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _action_range_row(name: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {"selector": name, "status": "missing"}
    return {
        "selector": name,
        "status": "pass",
        "direct_action_shape": payload["direct_action_shape"],
        "bridge_action_shape": payload["bridge_action_shape"],
        "direct_min": payload["direct_action_min"],
        "direct_max": payload["direct_action_max"],
        "bridge_min": payload["bridge_action_min"],
        "bridge_max": payload["bridge_action_max"],
        "selected_rows": payload["selected_row_indices"],
        "selected_gripper_width": payload["selected_gripper_width"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--official-dp-dir", required=True, type=Path)
    parser.add_argument("--official-dp-commit", required=True)
    parser.add_argument("--official-dp-remote", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    train_dir = run_dir / "official_dp_train"
    dataset_summary_path = run_dir / "dataset_summary.json"
    dataset_summary = json.loads(dataset_summary_path.read_text(encoding="utf-8"))
    train_logs = _read_json_lines(train_dir / "logs.json.txt")
    train_final = train_logs[-1] if train_logs else {}
    first_payload = _read_prefixed_payload(run_dir / "logs" / "checkpoint_action_range_first.log", CHECKPOINT_PREFIX)
    closed_payload = _read_prefixed_payload(run_dir / "logs" / "checkpoint_action_range_closed.log", CHECKPOINT_PREFIX)
    summary = {
        "run_dir": str(run_dir),
        "official_diffusion_policy": {
            "source_dir": str(args.official_dp_dir.expanduser().resolve()),
            "commit": str(args.official_dp_commit),
            "remote": str(args.official_dp_remote),
        },
        "dataset": {
            "path": dataset_summary["dataset_path"],
            "obs_shape": dataset_summary["obs_shape"],
            "action_shape": dataset_summary["action_shape"],
            "episode_ends": dataset_summary["episode_ends"],
            "train_samples": dataset_summary["train_samples"],
            "val_samples": dataset_summary["val_samples"],
            "action_abs_max": dataset_summary["action_abs_max"],
            "action_clip_fraction_abs_ge_1": dataset_summary["action_clip_fraction_abs_ge_1"],
            "pose_action_abs_max": dataset_summary["pose_action_abs_max"],
            "pose_action_clip_fraction_abs_ge_1": dataset_summary["pose_action_clip_fraction_abs_ge_1"],
            "gripper_exact_bound_fraction": dataset_summary["gripper_exact_bound_fraction"],
        },
        "training": {
            "train_dir": str(train_dir),
            "resolved_config": str(train_dir / ".hydra" / "config.yaml"),
            "overrides": str(train_dir / ".hydra" / "overrides.yaml"),
            "stdout_log": str(run_dir / "logs" / "official_dp_tiny_train.log"),
            "metrics_log": str(train_dir / "logs.json.txt"),
            "latest_checkpoint": str(train_dir / "checkpoints" / "latest.ckpt"),
            "final_metrics": train_final,
        },
        "checkpoint_action_range": [
            _action_range_row("first", first_payload),
            _action_range_row("gripper_closed", closed_payload),
        ],
        "verdict": "pass" if train_final and first_payload and closed_payload else "incomplete",
        "scope": "tiny official-DP mechanics smoke only; not a BC readiness or closed-loop behavior claim",
    }
    summary_path = run_dir / "official_dp_smoke_summary.json"
    report_path = run_dir / "official_dp_smoke_report.md"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Official Diffusion Policy Contact-Relabel Smoke",
        "",
        f"- verdict: `{summary['verdict']}`",
        f"- scope: {summary['scope']}",
        f"- run dir: `{run_dir}`",
        f"- official DP source: `{args.official_dp_dir.expanduser().resolve()}`",
        f"- official DP commit: `{args.official_dp_commit}`",
        f"- official DP remote: `{args.official_dp_remote}`",
        "",
        "## Dataset",
        "",
        f"- dataset: `{dataset_summary['dataset_path']}`",
        f"- obs shape: `{dataset_summary['obs_shape']}`",
        f"- action shape: `{dataset_summary['action_shape']}`",
        f"- episode ends: `{dataset_summary['episode_ends']}`",
        f"- train/val samples: `{dataset_summary['train_samples']}` / `{dataset_summary['val_samples']}`",
        f"- action abs max: `{_fmt(dataset_summary['action_abs_max'])}`",
        f"- exact-bound action fraction: `{_fmt(dataset_summary['action_clip_fraction_abs_ge_1'])}`",
        f"- pose action abs max: `{_fmt(dataset_summary['pose_action_abs_max'])}`",
        f"- pose exact-bound fraction: `{_fmt(dataset_summary['pose_action_clip_fraction_abs_ge_1'])}`",
        f"- gripper exact-bound fraction: `{_fmt(dataset_summary['gripper_exact_bound_fraction'])}`",
        "",
        "## Tiny Train",
        "",
        f"- resolved config: `{train_dir / '.hydra' / 'config.yaml'}`",
        f"- overrides: `{train_dir / '.hydra' / 'overrides.yaml'}`",
        f"- stdout log: `{run_dir / 'logs' / 'official_dp_tiny_train.log'}`",
        f"- metrics log: `{train_dir / 'logs.json.txt'}`",
        f"- checkpoint: `{train_dir / 'checkpoints' / 'latest.ckpt'}`",
        "",
        "|metric|value|",
        "|---|---|",
    ]
    for key in ["global_step", "epoch", "lr", "train_loss", "val_loss", "train_action_mse_error", "test/mean_score"]:
        if key in train_final:
            lines.append(f"|{key}|{_fmt(train_final[key])}|")
    lines.extend(
        [
            "",
            "## Predicted Action Range Sanity",
            "",
            "This uses the one-step debug checkpoint only. Bound-touching here is a mechanics/range signal, not a behavior claim.",
            "",
            "|selector|direct shape|bridge shape|direct min|direct max|bridge min|bridge max|selected rows|",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in summary["checkpoint_action_range"]:
        if row["status"] != "pass":
            lines.append(f"|{row['selector']}|missing|missing|missing|missing|missing|missing|missing|")
            continue
        lines.append(
            "|"
            + "|".join(
                [
                    row["selector"],
                    str(row["direct_action_shape"]),
                    str(row["bridge_action_shape"]),
                    str(row["direct_min"]),
                    str(row["direct_max"]),
                    str(row["bridge_min"]),
                    str(row["bridge_max"]),
                    str(row["selected_rows"]),
                ]
            )
            + "|"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- dataset report: `{run_dir / 'dataset_report.md'}`",
            f"- dataset summary JSON: `{dataset_summary_path}`",
            f"- action range CSV: `{run_dir / 'action_range.csv'}`",
            f"- observation range CSV: `{run_dir / 'obs_range.csv'}`",
            f"- train log: `{run_dir / 'logs' / 'official_dp_tiny_train.log'}`",
            f"- checkpoint smoke logs: `{run_dir / 'logs'}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FRANKA_CUBE_OFFICIAL_DP_SMOKE_REPORT " + json.dumps({"verdict": summary["verdict"], "report": str(report_path)}))


if __name__ == "__main__":
    main()
