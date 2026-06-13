"""Summarize a bounded official Diffusion Policy pretrain run."""

from __future__ import annotations

import argparse
import csv
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
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "row",
        "global_step",
        "epoch",
        "lr",
        "train_loss",
        "val_loss",
        "train_action_mse_error",
        "test/mean_score",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(rows):
            writer.writerow({key: row.get(key, "") for key in fieldnames} | {"row": idx})


def _plot_loss(path: Path, rows: list[dict[str, Any]]) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - depends on local env.
        return f"matplotlib unavailable: {exc}"

    if not rows:
        return "no log rows"

    def series(key: str) -> tuple[list[int], list[float]]:
        xs: list[int] = []
        ys: list[float] = []
        for row in rows:
            if key in row:
                xs.append(int(row.get("global_step", len(xs))))
                ys.append(float(row[key]))
        return xs, ys

    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    for ax, key, ylabel in [
        (axes[0], "train_loss", "train loss"),
        (axes[1], "val_loss", "val loss"),
        (axes[2], "train_action_mse_error", "action MSE"),
    ]:
        xs, ys = series(key)
        if xs:
            ax.plot(xs, ys, marker="o", linewidth=1.5)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("global step")
    fig.suptitle("Official DP Contact-Aware Debug Pretrain")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return None


def _epoch_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if "val_loss" in row or "train_action_mse_error" in row]


def _loss_verdict(epoch_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(epoch_rows) < 2:
        return {"status": "incomplete", "reason": "fewer than two epoch summary rows"}
    initial = float(epoch_rows[0]["train_loss"])
    final = float(epoch_rows[-1]["train_loss"])
    val_initial = float(epoch_rows[0].get("val_loss", float("nan")))
    val_final = float(epoch_rows[-1].get("val_loss", float("nan")))
    return {
        "status": "pass" if final < initial else "fail",
        "initial_train_loss": initial,
        "final_train_loss": final,
        "train_loss_delta": final - initial,
        "train_loss_ratio": final / initial if initial != 0 else None,
        "initial_val_loss": val_initial,
        "final_val_loss": val_final,
        "val_loss_delta": val_final - val_initial,
        "val_loss_ratio": val_final / val_initial if val_initial != 0 else None,
    }


def _action_range_rows(log_dir: Path, selectors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selector in selectors:
        payload = _read_prefixed_payload(log_dir / f"checkpoint_action_range_{selector}.log", CHECKPOINT_PREFIX)
        if payload is None:
            rows.append({"selector": selector, "status": "missing"})
            continue
        direct_chunk_min = payload.get("direct_action_chunk_min")
        direct_chunk_max = payload.get("direct_action_chunk_max")
        bridge_min = payload.get("bridge_action_min")
        bridge_max = payload.get("bridge_action_max")
        label_min = payload.get("label_action_min")
        label_max = payload.get("label_action_max")
        pose_touches_bounds = False
        if direct_chunk_min is not None and direct_chunk_max is not None:
            pose_touches_bounds = pose_touches_bounds or min(direct_chunk_min[:6]) <= -0.99
            pose_touches_bounds = pose_touches_bounds or max(direct_chunk_max[:6]) >= 0.99
        if bridge_min is not None and bridge_max is not None:
            pose_touches_bounds = pose_touches_bounds or min(bridge_min[:6]) <= -0.99
            pose_touches_bounds = pose_touches_bounds or max(bridge_max[:6]) >= 0.99
        gripper_sign_status = "unknown"
        if label_min is not None and label_max is not None:
            label_gripper_min = float(label_min[-1])
            label_gripper_max = float(label_max[-1])
            direct_gripper_min = float(payload["direct_action_min"][-1])
            direct_gripper_max = float(payload["direct_action_max"][-1])
            bridge_gripper_min = None if bridge_min is None else float(bridge_min[-1])
            bridge_gripper_max = None if bridge_max is None else float(bridge_max[-1])
            if label_gripper_min > 0.0 and label_gripper_max > 0.0:
                bridge_ok = True if bridge_gripper_min is None else bridge_gripper_min > 0.0
                gripper_sign_status = "pass" if direct_gripper_min > 0.0 and bridge_ok else "needs_review"
            elif label_gripper_min < 0.0 and label_gripper_max < 0.0:
                bridge_ok = True if bridge_gripper_max is None else bridge_gripper_max < 0.0
                gripper_sign_status = "pass" if direct_gripper_max < 0.0 and bridge_ok else "needs_review"
            else:
                gripper_sign_status = "mixed_label"
        range_status = "needs_review" if pose_touches_bounds or gripper_sign_status == "needs_review" else "pass"
        rows.append(
            {
                "selector": selector,
                "status": "pass",
                "range_status": range_status,
                "pose_touches_normalized_bounds": pose_touches_bounds,
                "gripper_sign_status": gripper_sign_status,
                "selected_rows": payload["selected_row_indices"],
                "selected_ee_z": payload["selected_ee_z"],
                "selected_gripper_width": payload["selected_gripper_width"],
                "direct_action_shape": payload["direct_action_shape"],
                "bridge_action_shape": payload["bridge_action_shape"],
                "direct_only": payload.get("direct_only", False),
                "label_action_shape": payload.get("label_action_shape"),
                "direct_min": payload["direct_action_min"],
                "direct_max": payload["direct_action_max"],
                "direct_chunk_min": direct_chunk_min,
                "direct_chunk_max": direct_chunk_max,
                "bridge_min": bridge_min,
                "bridge_max": bridge_max,
                "label_min": label_min,
                "label_max": label_max,
                "label_chunk_min": payload.get("label_action_chunk_min"),
                "label_chunk_max": payload.get("label_action_chunk_max"),
                "num_inference_steps": payload["num_inference_steps"],
            }
        )
    return rows


def _markdown_epoch_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "|epoch|global_step|lr|train_loss|val_loss|train_action_mse_error|",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "|"
            + "|".join(
                [
                    _fmt(row.get("epoch")),
                    _fmt(row.get("global_step")),
                    _fmt(row.get("lr")),
                    _fmt(row.get("train_loss")),
                    _fmt(row.get("val_loss")),
                    _fmt(row.get("train_action_mse_error")),
                ]
            )
            + "|"
        )
    return "\n".join(lines)


def _markdown_action_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "|selector|status|range status|gripper sign|rows|label first min/max|direct first min/max|bridge first min/max|label chunk min/max|direct chunk min/max|",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "|"
            + "|".join(
                [
                    str(row["selector"]),
                    str(row["status"]),
                    str(row.get("range_status", "")),
                    str(row.get("gripper_sign_status", "")),
                    str(row.get("selected_rows", "")),
                    f"{row.get('label_min', '')} / {row.get('label_max', '')}",
                    f"{row.get('direct_min', '')} / {row.get('direct_max', '')}",
                    f"{row.get('bridge_min', '')} / {row.get('bridge_max', '')}",
                    f"{row.get('label_chunk_min', '')} / {row.get('label_chunk_max', '')}",
                    f"{row.get('direct_chunk_min', '')} / {row.get('direct_chunk_max', '')}",
                ]
            )
            + "|"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--official-dp-dir", required=True, type=Path)
    parser.add_argument("--official-dp-commit", required=True)
    parser.add_argument("--official-dp-remote", required=True)
    parser.add_argument("--selectors", default="first,gripper_closed,lift_high")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    train_dir = run_dir / "official_dp_train"
    log_dir = run_dir / "logs"
    dataset_summary_path = run_dir / "dataset_summary.json"
    dataset_summary = json.loads(dataset_summary_path.read_text(encoding="utf-8"))
    rows = _read_json_lines(train_dir / "logs.json.txt")
    epochs = _epoch_rows(rows)
    loss_verdict = _loss_verdict(epochs)
    selectors = [part.strip() for part in args.selectors.split(",") if part.strip()]
    action_rows = _action_range_rows(log_dir, selectors)

    loss_csv = run_dir / "loss_history.csv"
    plot_path = run_dir / "loss_curves.png"
    plot_error = _plot_loss(plot_path, rows)
    _write_csv(loss_csv, rows)

    final_metrics = epochs[-1] if epochs else (rows[-1] if rows else {})
    action_range_status = "pass" if all(row["status"] == "pass" for row in action_rows) else "incomplete"
    action_range_semantics = "pass" if all(row.get("range_status") == "pass" for row in action_rows) else "needs_review"
    verdict = (
        "pass"
        if loss_verdict["status"] == "pass" and action_range_status == "pass" and action_range_semantics == "pass"
        else "needs_review"
    )
    summary = {
        "verdict": verdict,
        "scope": "bounded official-DP contact-aware debug pretrain; not closed-loop BC readiness",
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
            "action_normalizer": dataset_summary.get("action_normalizer", "unknown"),
            "pose_action_abs_max": dataset_summary["pose_action_abs_max"],
            "pose_action_clip_fraction_abs_ge_1": dataset_summary["pose_action_clip_fraction_abs_ge_1"],
            "gripper_exact_bound_fraction": dataset_summary["gripper_exact_bound_fraction"],
        },
        "loss": loss_verdict,
        "action_range_status": action_range_status,
        "action_range_semantics": action_range_semantics,
        "final_metrics": final_metrics,
        "action_range": action_rows,
        "artifacts": {
            "resolved_config": str(train_dir / ".hydra" / "config.yaml"),
            "overrides": str(train_dir / ".hydra" / "overrides.yaml"),
            "train_stdout": str(log_dir / "official_dp_debug_pretrain.log"),
            "metrics_log": str(train_dir / "logs.json.txt"),
            "loss_csv": str(loss_csv),
            "loss_plot": str(plot_path) if plot_error is None else None,
            "loss_plot_error": plot_error,
            "checkpoint": str(train_dir / "checkpoints" / "latest.ckpt"),
        },
    }
    summary_path = run_dir / "official_dp_pretrain_summary.json"
    report_path = run_dir / "official_dp_pretrain_report.md"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Official DP Contact-Aware Debug Pretrain",
        "",
        f"- verdict: `{verdict}`",
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
        f"- action normalizer: `{dataset_summary.get('action_normalizer', 'unknown')}`",
        f"- pose action abs max: `{_fmt(dataset_summary['pose_action_abs_max'])}`",
        f"- pose exact-bound fraction: `{_fmt(dataset_summary['pose_action_clip_fraction_abs_ge_1'])}`",
        f"- gripper exact-bound fraction: `{_fmt(dataset_summary['gripper_exact_bound_fraction'])}`",
        "",
        "## Loss Curve",
        "",
        f"- loss status: `{loss_verdict['status']}`",
        f"- initial/final train loss: `{_fmt(loss_verdict.get('initial_train_loss'))}` / `{_fmt(loss_verdict.get('final_train_loss'))}`",
        f"- initial/final val loss: `{_fmt(loss_verdict.get('initial_val_loss'))}` / `{_fmt(loss_verdict.get('final_val_loss'))}`",
        f"- loss CSV: `{loss_csv}`",
        f"- loss plot: `{plot_path if plot_error is None else plot_error}`",
        "",
        _markdown_epoch_table(epochs),
        "",
        "## Checkpoint Action Range",
        "",
        f"- action range status: `{action_range_status}`",
        f"- action range semantics: `{action_range_semantics}`",
        "",
        "Finite ranges here are a checkpoint sanity gate, not a closed-loop behavior claim. Pose-channel bound-touching is flagged for review even if all outputs are finite.",
        "",
        _markdown_action_table(action_rows),
        "",
        "## Artifacts",
        "",
        f"- resolved config: `{train_dir / '.hydra' / 'config.yaml'}`",
        f"- overrides: `{train_dir / '.hydra' / 'overrides.yaml'}`",
        f"- stdout log: `{log_dir / 'official_dp_debug_pretrain.log'}`",
        f"- metrics log: `{train_dir / 'logs.json.txt'}`",
        f"- checkpoint: `{train_dir / 'checkpoints' / 'latest.ckpt'}`",
        f"- summary JSON: `{summary_path}`",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FRANKA_CUBE_OFFICIAL_DP_PRETRAIN_REPORT " + json.dumps({"verdict": verdict, "report": str(report_path)}))


if __name__ == "__main__":
    main()
