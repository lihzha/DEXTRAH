"""Summarize exact-scene closed-loop YAM RGB policy evaluations."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _metric(summary: dict[str, Any], name: str, field: str) -> float | None:
    value = (summary.get("step_metric_summary") or {}).get(name, {}).get(field)
    return None if value is None else float(value)


def _mean(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    return None if not finite else sum(finite) / len(finite)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix_dir", type=Path, required=True)
    parser.add_argument("--results_root", type=Path, required=True)
    parser.add_argument("--require_complete", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    matrix_dir = args.matrix_dir.expanduser().resolve()
    results_root = args.results_root.expanduser().resolve()
    matrix_path = matrix_dir / "eval_matrix.tsv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        entries = list(csv.DictReader(handle, delimiter="\t"))
    rows = []
    missing = []
    for entry in entries:
        metrics_path = results_root / "evals" / entry["run_name"] / "metrics.json"
        if not metrics_path.is_file():
            missing.append(str(metrics_path))
            continue
        summary = json.loads(metrics_path.read_text(encoding="utf-8")).get("summary", {})
        episodes = summary.get("episodes") or []
        success = bool(episodes and episodes[0].get("success"))
        site_visibility = summary.get("robot_debug_site_visibility") or {}
        rows.append(
            {
                **entry,
                "metrics_path": str(metrics_path),
                "success": success,
                "episode_success_rate": summary.get("episode_success_rate"),
                "steps_completed": summary.get("steps_completed"),
                "max_lift_height": _metric(summary, "cube_lift_height", "max"),
                "min_hold_to_cube_dist": _metric(summary, "hold_to_cube_dist", "min"),
                "final_bin_drop_success": _metric(summary, "bin_drop_success", "final"),
                "hidden_debug_sites": int(site_visibility.get("hidden_count") or 0),
                "video_files": summary.get("video_files") or [],
            }
        )
    if missing and bool(args.require_complete):
        raise SystemExit(f"Missing {len(missing)} matrix metrics; first: {missing[0]}")

    split_summaries = {}
    for split in ("train", "val"):
        split_rows = [row for row in rows if row["split"] == split]
        split_summaries[split] = {
            "count": len(split_rows),
            "success_count": sum(bool(row["success"]) for row in split_rows),
            "success_rate": None
            if not split_rows
            else sum(bool(row["success"]) for row in split_rows) / len(split_rows),
            "mean_max_lift_height": _mean([row["max_lift_height"] for row in split_rows]),
            "mean_min_hold_to_cube_dist": _mean([row["min_hold_to_cube_dist"] for row in split_rows]),
        }
    val = split_summaries["val"]
    train = split_summaries["train"]
    selection_score = (
        100.0 * float(val["success_rate"] or 0.0)
        + 10.0 * float(train["success_rate"] or 0.0)
        + float(val["mean_max_lift_height"] or 0.0)
        - float(val["mean_min_hold_to_cube_dist"] or 0.0)
    )
    payload = {
        "matrix_dir": str(matrix_dir),
        "entry_count": len(entries),
        "completed_count": len(rows),
        "missing": missing,
        "splits": split_summaries,
        "selection_score": selection_score,
        "selection_priority": "heldout_success_then_train_success_then_lift_and_distance",
        "rows": rows,
    }
    summary_path = matrix_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = matrix_dir / "summary.csv"
    fieldnames = [
        "matrix_index",
        "split",
        "source_index",
        "success",
        "max_lift_height",
        "min_hold_to_cube_dist",
        "final_bin_drop_success",
        "steps_completed",
        "hidden_debug_sites",
        "metrics_path",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    print(json.dumps({"summary": str(summary_path), "selection_score": selection_score}, sort_keys=True))


if __name__ == "__main__":
    main()
