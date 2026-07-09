#!/usr/bin/env python3
"""Summarize and visualize randomization in a sharded YAM RGB dataset."""

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--grid-count", type=int, default=100)
    parser.add_argument("--grid-cols", type=int, default=10)
    parser.add_argument("--thumbnail-size", type=int, default=128)
    return parser.parse_args()


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_shard_path(manifest_path, shard_path):
    path = Path(shard_path)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path


def _host_results_path(path_text, results_root):
    if path_text.startswith("/results/"):
        return results_root / path_text[len("/results/") :]
    return Path(path_text)


def _basename(path_text):
    return Path(path_text).name if path_text else "<missing>"


def _recovery_enabled(metadata):
    recording = metadata.get("recording") or {}
    recovery_rows = recording.get("recovery") or []
    return any(bool(row.get("enabled", False)) for row in recovery_rows if isinstance(row, dict))


def _numeric_summary(values):
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"count": 0}
    return {
        "count": int(array.size),
        "min": float(np.min(array)),
        "p05": float(np.percentile(array, 5)),
        "median": float(np.median(array)),
        "mean": float(np.mean(array)),
        "p95": float(np.percentile(array, 95)),
        "max": float(np.max(array)),
    }


def _add_vector(numeric, prefix, values):
    if not isinstance(values, (list, tuple)):
        return
    for index, value in enumerate(values):
        numeric["{}_{}".format(prefix, "xyz"[index] if index < 3 else index)].append(float(value))


def _add_scalar(numeric, key, value):
    if value is not None:
        numeric[key].append(float(value))


def _as_rgb(frame):
    array = np.asarray(frame)
    if array.ndim != 3:
        raise ValueError("Expected rank-3 RGB frame, got {}".format(array.shape))
    if array.shape[0] in (3, 4) and array.shape[-1] not in (3, 4):
        array = np.transpose(array, (1, 2, 0))
    array = array[..., :3]
    if array.dtype != np.uint8:
        if np.max(array) <= 1.0:
            array = array * 255.0
        array = np.clip(array, 0.0, 255.0).astype(np.uint8)
    return array


def _resize_nearest(frame, size):
    frame = _as_rgb(frame)
    y_index = np.linspace(0, frame.shape[0] - 1, size).astype(np.int64)
    x_index = np.linspace(0, frame.shape[1] - 1, size).astype(np.int64)
    return frame[y_index[:, None], x_index[None, :]]


def _write_ppm(path, image):
    image = np.asarray(image, dtype=np.uint8)
    header = "P6\n{} {}\n255\n".format(image.shape[1], image.shape[0]).encode("ascii")
    path.write_bytes(header + image.tobytes(order="C"))


def _make_pair_grid(records, output_path, fraction, columns, thumbnail_size):
    rows = int(math.ceil(len(records) / float(columns)))
    divider = 2
    gutter = 4
    cell_width = thumbnail_size * 2 + divider
    cell_height = thumbnail_size
    grid = np.full(
        (rows * cell_height + (rows + 1) * gutter, columns * cell_width + (columns + 1) * gutter, 3),
        24,
        dtype=np.uint8,
    )
    for grid_index, record in enumerate(records):
        scene = np.load(record["shard_path"] / "scene_rgb.npy", mmap_mode="r", allow_pickle=False)
        wrist = np.load(record["shard_path"] / "wrist_rgb.npy", mmap_mode="r", allow_pickle=False)
        frame_index = int(round((min(len(scene), len(wrist)) - 1) * fraction))
        scene_frame = _resize_nearest(scene[frame_index], thumbnail_size)
        wrist_frame = _resize_nearest(wrist[frame_index], thumbnail_size)
        cell = np.full((cell_height, cell_width, 3), 235, dtype=np.uint8)
        cell[:, :thumbnail_size] = scene_frame
        cell[:, thumbnail_size + divider :] = wrist_frame
        row = grid_index // columns
        col = grid_index % columns
        y0 = gutter + row * (cell_height + gutter)
        x0 = gutter + col * (cell_width + gutter)
        grid[y0 : y0 + cell_height, x0 : x0 + cell_width] = cell
        record.setdefault("grid_frames", {})[str(fraction)] = frame_index
    _write_ppm(output_path, grid)


def _markdown_table(numeric, names):
    lines = ["| Variable | Min | Mean | Median | P95 | Max |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name in names:
        row = numeric.get(name, {"count": 0})
        if not row.get("count"):
            continue
        lines.append(
            "| `{}` | {:.5f} | {:.5f} | {:.5f} | {:.5f} | {:.5f} |".format(
                name, row["min"], row["mean"], row["median"], row["p95"], row["max"]
            )
        )
    return lines


def _counter_lines(title, counter):
    lines = ["### {}".format(title), "", "| Value | Count |", "| --- | ---: |"]
    for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append("| `{}` | {} |".format(value, count))
    lines.append("")
    return lines


def main():
    args = _parse_args()
    if args.grid_count < 1 or args.grid_cols < 1 or args.thumbnail_size < 8:
        raise ValueError("Grid count/columns must be positive and thumbnail size must be at least 8")

    manifest_path = args.manifest.resolve()
    manifest = _load_json(manifest_path)
    shards = manifest.get("shards", [])
    if not shards:
        raise ValueError("Empty manifest: {}".format(manifest_path))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    numeric = defaultdict(list)
    categorical = defaultdict(Counter)
    records = []
    missing_source_metadata = []
    missing_source_policy_metadata = []

    for manifest_index, shard in enumerate(shards):
        shard_path = _resolve_shard_path(manifest_path, shard["path"])
        metadata_path = shard_path / "metadata.json"
        metadata = _load_json(metadata_path)
        source_dataset = str(metadata.get("source_dataset", ""))
        source_metadata_path = Path(str(_host_results_path(source_dataset, args.results_root)) + ".metadata.json")
        if not source_metadata_path.is_file():
            missing_source_metadata.append(str(source_metadata_path))
            source_metadata = {}
        else:
            source_metadata = _load_json(source_metadata_path)

        source_policy_shard = str(
            metadata.get("source_policy_shard") or shard.get("source_policy_shard") or ""
        )
        source_policy_metadata_path = (
            _host_results_path(source_policy_shard, args.results_root) / "metadata.json"
            if source_policy_shard
            else None
        )
        if source_policy_metadata_path is None or not source_policy_metadata_path.is_file():
            source_policy_metadata = None
            missing_source_policy_metadata.append(
                str(source_policy_metadata_path) if source_policy_metadata_path is not None else "<missing>"
            )
        else:
            source_policy_metadata = _load_json(source_policy_metadata_path)

        visual = metadata.get("exact_visual_replay") or {}
        visual_paths = visual.get("paths") or {}
        recording = metadata.get("recording") or {}
        initial_states = metadata.get("recording_initial_states") or []
        initial_state = initial_states[0] if initial_states else {}
        scene_randomization = source_metadata.get("yam_policy_scene_randomization") or {}
        scene_camera = source_metadata.get("scene_camera") or {}
        goal_bin = scene_randomization.get("goal_bin") or {}
        lighting = scene_randomization.get("lighting") or {}
        background_walls = scene_randomization.get("background_walls") or {}
        material_randomization = visual.get("material_randomization") or {}
        object_material = material_randomization.get("object") or {}
        robot_material = material_randomization.get("robot") or {}

        table_texture = _basename((visual_paths.get("table_texture") or {}).get("selected"))
        dome_texture = _basename((visual_paths.get("dome_texture") or {}).get("selected"))
        background_texture = _basename((visual_paths.get("background_texture") or {}).get("selected"))
        categorical["table_textures"][table_texture] += 1
        categorical["dome_textures"][dome_texture] += 1
        categorical["background_textures"][background_texture] += 1
        categorical["split"][str(shard.get("split", "unknown"))] += 1
        categorical["rendering_mode"][str(recording.get("rendering_mode", "missing"))] += 1
        categorical["control_mode"][str(recording.get("control_mode", "missing"))] += 1
        categorical["background_walls_enabled"][str(bool(background_walls.get("enabled", False)))] += 1
        categorical["ground_texture_enabled"][str(bool(visual.get("ground_texture_enabled", False)))] += 1
        categorical["dynamic_replay"][str(bool(recording.get("dynamics_mode", False)))] += 1
        categorical["object_material_recorded"][str(bool(object_material))] += 1
        categorical["object_material_override_applied"][
            str(bool(object_material.get("override_applied", False)))
        ] += 1
        categorical["robot_material_recorded"][str(bool(robot_material))] += 1
        replay_gate = recording.get("replay_gate") or {}
        categorical["replay_gate_passed"][str(bool(replay_gate.get("passed", False)))] += 1
        categorical["exact_visual_resample"][str(bool(recording.get("exact_visual_resample", False)))] += 1
        recovery_enabled = _recovery_enabled(metadata)
        source_recovery_enabled = (
            _recovery_enabled(source_policy_metadata) if source_policy_metadata is not None else None
        )
        if source_recovery_enabled is None:
            recovery_provenance = "unknown_source"
        elif recovery_enabled and source_recovery_enabled:
            recovery_provenance = "inherited_recovery"
        elif recovery_enabled:
            recovery_provenance = "synthesized_recovery_from_nominal"
        elif source_recovery_enabled:
            recovery_provenance = "source_recovery_replayed_nominally"
        else:
            recovery_provenance = "nominal"
        categorical["recovery_data"][str(recovery_enabled)] += 1
        categorical["source_recovery_data"][str(source_recovery_enabled)] += 1
        categorical["recovery_provenance"][recovery_provenance] += 1
        categorical["source_policy_shards"][source_policy_shard or "<missing>"] += 1
        for controller_path in recording.get("episode_controller_paths") or []:
            categorical["controller_paths"][str(controller_path)] += 1

        _add_scalar(numeric, "trajectory_steps", shard.get("num_steps"))
        _add_scalar(numeric, "longest_stationary_tcp_steps", shard.get("longest_stationary_tcp_steps"))
        _add_vector(numeric, "camera_eye", visual.get("scene_eye") or scene_camera.get("eye"))
        _add_vector(numeric, "camera_target", visual.get("scene_target") or scene_camera.get("target"))
        _add_scalar(numeric, "camera_shared_y_jitter", visual.get("shared_y_jitter"))
        _add_vector(numeric, "object_initial", initial_state.get("cube_initial_pos"))
        _add_scalar(numeric, "bin_center_x", goal_bin.get("center_x"))
        _add_scalar(numeric, "bin_center_y", goal_bin.get("center_y"))
        _add_scalar(numeric, "bin_inner_size_x", goal_bin.get("inner_size_x"))
        _add_scalar(numeric, "bin_inner_size_y", goal_bin.get("inner_size_y"))
        _add_scalar(numeric, "bin_wall_height", goal_bin.get("wall_height"))
        _add_scalar(numeric, "dome_light_intensity", lighting.get("dome_light_intensity"))
        _add_scalar(numeric, "key_light_intensity", lighting.get("key_light_intensity"))
        _add_vector(numeric, "key_light_rotation", lighting.get("key_light_rotation_deg"))
        _add_scalar(numeric, "table_texture_tiling", visual.get("table_texture_tiling"))
        _add_scalar(numeric, "table_texture_roughness", visual.get("table_texture_roughness"))
        _add_scalar(numeric, "ground_texture_tiling", visual.get("background_texture_tiling"))
        _add_scalar(numeric, "ground_texture_roughness", visual.get("background_roughness"))
        _add_scalar(numeric, "bin_visual_roughness", visual.get("bin_visual_roughness"))
        _add_vector(numeric, "object_color", object_material.get("color"))
        _add_scalar(numeric, "object_metallic", object_material.get("metallic"))
        _add_scalar(numeric, "object_roughness", object_material.get("roughness"))
        _add_vector(numeric, "robot_color", robot_material.get("body_color"))
        _add_scalar(numeric, "robot_metallic", robot_material.get("metallic"))
        _add_scalar(numeric, "robot_roughness", robot_material.get("roughness"))

        records.append(
            {
                "manifest_index": manifest_index,
                "source_index": int(shard.get("source_index", manifest_index)),
                "split": str(shard.get("split", "unknown")),
                "target_uuid": str(shard.get("target_uuid", metadata.get("target_uuid", ""))),
                "num_steps": int(shard.get("num_steps", 0)),
                "shard_path": shard_path,
                "table_texture": table_texture,
                "dome_texture": dome_texture,
                "background_texture": background_texture,
                "recovery_data": recovery_enabled,
                "recovery_provenance": recovery_provenance,
                "source_policy_shard": source_policy_shard,
                "object_initial": initial_state.get("cube_initial_pos"),
                "goal_bin": goal_bin,
            }
        )

    numeric_summary = {key: _numeric_summary(values) for key, values in sorted(numeric.items())}
    categorical_json = {key: dict(sorted(counter.items())) for key, counter in sorted(categorical.items())}
    unique_targets = {record["target_uuid"] for record in records if record["target_uuid"]}
    train_targets = {record["target_uuid"] for record in records if record["split"] == "train"}
    val_targets = {record["target_uuid"] for record in records if record["split"] == "val"}
    recovery_count = categorical["recovery_data"].get("True", 0)
    table_texture_families = {Path(name).stem for name in categorical["table_textures"] if name != "<missing>"}
    dome_texture_families = {Path(name).stem for name in categorical["dome_textures"] if name != "<missing>"}
    background_texture_families = {
        Path(name).stem for name in categorical["background_textures"] if name != "<missing>"
    }
    table_dome_pairs = {
        (Path(record["table_texture"]).stem, Path(record["dome_texture"]).stem) for record in records
    }
    rendered_background_wall_count = categorical["background_walls_enabled"].get("True", 0)
    rendered_ground_texture_count = categorical["ground_texture_enabled"].get("True", 0)
    source_policy_counts = {
        path: count
        for path, count in categorical["source_policy_shards"].items()
        if path != "<missing>"
    }
    reused_source_policy_counts = {
        path: count for path, count in source_policy_counts.items() if count > 1
    }

    summary = {
        "manifest": str(manifest_path),
        "num_trajectories": len(records),
        "num_steps": int(sum(record["num_steps"] for record in records)),
        "num_train_trajectories": categorical["split"].get("train", 0),
        "num_val_trajectories": categorical["split"].get("val", 0),
        "unique_target_objects": len(unique_targets),
        "unique_train_target_objects": len(train_targets),
        "unique_val_target_objects": len(val_targets),
        "train_val_target_overlap": len(train_targets.intersection(val_targets)),
        "recovery_trajectories": recovery_count,
        "recovery_fraction": float(recovery_count / len(records)),
        "recovery_provenance": dict(sorted(categorical["recovery_provenance"].items())),
        "unique_source_policy_shards": len(source_policy_counts),
        "reused_source_policy_shards": len(reused_source_policy_counts),
        "rows_on_reused_source_policy_shards": int(sum(reused_source_policy_counts.values())),
        "max_source_policy_shard_reuse": int(max(source_policy_counts.values(), default=0)),
        "unique_table_textures": len(categorical["table_textures"]),
        "unique_table_texture_families": len(table_texture_families),
        "unique_dome_textures": len(categorical["dome_textures"]),
        "unique_dome_texture_families": len(dome_texture_families),
        "unique_background_textures": len(categorical["background_textures"]),
        "unique_background_texture_families": len(background_texture_families),
        "rendered_background_wall_trajectories": rendered_background_wall_count,
        "rendered_ground_texture_trajectories": rendered_ground_texture_count,
        "unique_table_dome_pairs": len(table_dome_pairs),
        "object_material_overrides_applied": categorical["object_material_override_applied"].get("True", 0),
        "robot_material_records": categorical["robot_material_recorded"].get("True", 0),
        "missing_source_metadata_count": len(missing_source_metadata),
        "missing_source_policy_metadata_count": len(missing_source_policy_metadata),
    }

    grid_count = min(args.grid_count, len(records))
    selected_indices = np.linspace(0, len(records) - 1, grid_count).round().astype(np.int64).tolist()
    selected_records = [dict(records[index]) for index in selected_indices]
    for grid_index, record in enumerate(selected_records):
        record["grid_row"] = grid_index // args.grid_cols
        record["grid_col"] = grid_index % args.grid_cols

    for name, fraction in (("initial", 0.0), ("midpoint", 0.5), ("final", 1.0)):
        _make_pair_grid(
            selected_records,
            args.output_dir / "randomization_grid_{}_scene_wrist.ppm".format(name),
            fraction,
            args.grid_cols,
            args.thumbnail_size,
        )

    for record in selected_records:
        record["shard_path"] = str(record["shard_path"])
    report_payload = {
        "summary": summary,
        "numeric": numeric_summary,
        "categorical": categorical_json,
        "grid": {
            "count": grid_count,
            "columns": args.grid_cols,
            "rows": int(math.ceil(grid_count / float(args.grid_cols))),
            "thumbnail_size": args.thumbnail_size,
            "cell_layout": "scene_rgb left, wrist_rgb right",
            "records": selected_records,
        },
        "missing_source_metadata": missing_source_metadata,
        "missing_source_policy_metadata": missing_source_policy_metadata,
    }
    (args.output_dir / "randomization_stats.json").write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if summary["rendered_ground_texture_trajectories"]:
        ground_texture_line = (
            "- Ground-texture trajectories rendered: `{}/{}` from `{}` selected floor texture families".format(
                summary["rendered_ground_texture_trajectories"],
                summary["num_trajectories"],
                summary["unique_background_texture_families"],
            )
        )
    else:
        ground_texture_line = (
            "- Ground-texture trajectories rendered: `0/{}`; `{}` selected background texture families are metadata-only".format(
                summary["num_trajectories"],
                summary["unique_background_texture_families"],
            )
        )

    lines = [
        "# YAM RGB Dataset Randomization Report",
        "",
        "## Dataset",
        "",
        "- Trajectories / control steps: `{}` / `{}`".format(summary["num_trajectories"], summary["num_steps"]),
        "- Train / validation trajectories: `{}` / `{}`".format(
            summary["num_train_trajectories"], summary["num_val_trajectories"]
        ),
        "- Unique target objects total/train/validation: `{}` / `{}` / `{}`".format(
            summary["unique_target_objects"],
            summary["unique_train_target_objects"],
            summary["unique_val_target_objects"],
        ),
        "- Train/validation target overlap: `{}`".format(summary["train_val_target_overlap"]),
        "- Recovery trajectories: `{}` (`{:.1%}`)".format(recovery_count, summary["recovery_fraction"]),
        "- Recovery provenance nominal/inherited/new/replayed-nominal: `{}` / `{}` / `{}` / `{}`".format(
            summary["recovery_provenance"].get("nominal", 0),
            summary["recovery_provenance"].get("inherited_recovery", 0),
            summary["recovery_provenance"].get("synthesized_recovery_from_nominal", 0),
            summary["recovery_provenance"].get("source_recovery_replayed_nominally", 0),
        ),
        "- Unique/reused source policy shards; rows on reused sources; maximum reuse: `{}` / `{}`; `{}`; `{}`".format(
            summary["unique_source_policy_shards"],
            summary["reused_source_policy_shards"],
            summary["rows_on_reused_source_policy_shards"],
            summary["max_source_policy_shard_reuse"],
        ),
        "- Unique rendered table / dome asset files: `{}` / `{}`".format(
            summary["unique_table_textures"], summary["unique_dome_textures"]
        ),
        "- Unique rendered table / dome texture families: `{}` / `{}`".format(
            summary["unique_table_texture_families"],
            summary["unique_dome_texture_families"],
        ),
        "- Background-wall trajectories rendered: `{}/{}`".format(
            summary["rendered_background_wall_trajectories"],
            summary["num_trajectories"],
        ),
        ground_texture_line,
        "- Unique selected table+dome family pairs: `{}`".format(summary["unique_table_dome_pairs"]),
        "- Object material overrides / robot material records: `{}` / `{}`".format(
            summary["object_material_overrides_applied"], summary["robot_material_records"]
        ),
        "- Missing source metadata: `{}`".format(summary["missing_source_metadata_count"]),
        "- Missing source-policy metadata: `{}`".format(
            summary["missing_source_policy_metadata_count"]
        ),
        "",
        "The 100-cell grids sample the frozen manifest uniformly. Each cell places `scene_rgb` on the left and `wrist_rgb` on the right. Cell metadata is in `randomization_stats.json`.",
        "",
        "### Initial Frames",
        "",
        "![Initial scene/wrist randomization grid](randomization_grid_initial_scene_wrist.png)",
        "",
        "### Midpoint Frames",
        "",
        "![Midpoint scene/wrist randomization grid](randomization_grid_midpoint_scene_wrist.png)",
        "",
        "### Final Frames",
        "",
        "![Final scene/wrist randomization grid](randomization_grid_final_scene_wrist.png)",
        "",
        "## Geometry And Camera",
        "",
    ]
    lines.extend(
        _markdown_table(
            numeric_summary,
            [
                "camera_eye_x", "camera_eye_y", "camera_eye_z",
                "camera_target_x", "camera_target_y", "camera_target_z",
                "object_initial_x", "object_initial_y", "object_initial_z",
                "bin_center_x", "bin_center_y", "bin_inner_size_x", "bin_inner_size_y", "bin_wall_height",
            ],
        )
    )
    lines.extend(["", "## Lighting, Materials, And Flow", ""])
    lines.extend(
        _markdown_table(
            numeric_summary,
            [
                "dome_light_intensity", "key_light_intensity",
                "key_light_rotation_x", "key_light_rotation_y", "key_light_rotation_z",
                "table_texture_tiling", "table_texture_roughness",
                "ground_texture_tiling", "ground_texture_roughness", "bin_visual_roughness",
                "object_metallic", "object_roughness", "robot_metallic", "robot_roughness",
                "trajectory_steps", "longest_stationary_tcp_steps",
            ],
        )
    )
    lines.append("")
    lines.extend(_counter_lines("Selected Table Textures", categorical["table_textures"]))
    lines.extend(_counter_lines("Selected Dome Textures", categorical["dome_textures"]))
    lines.extend(_counter_lines("Selected Ground Textures", categorical["background_textures"]))
    lines.extend(_counter_lines("Recovery Provenance", categorical["recovery_provenance"]))
    lines.extend(_counter_lines("Controller Paths", categorical["controller_paths"]))
    lines.extend(_counter_lines("Admission And Rendering Checks", Counter({
        "quality rendering": categorical["rendering_mode"].get("quality", 0),
        "dynamic replay": categorical["dynamic_replay"].get("True", 0),
        "replay gate passed": categorical["replay_gate_passed"].get("True", 0),
        "background walls disabled": categorical["background_walls_enabled"].get("False", 0),
        "ground texture enabled": categorical["ground_texture_enabled"].get("True", 0),
        "exact visual resample": categorical["exact_visual_resample"].get("True", 0),
    })))
    (args.output_dir / "randomization_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"event": "yam_rgb_randomization_report_written", "output_dir": str(args.output_dir), **summary}, sort_keys=True))


if __name__ == "__main__":
    main()
