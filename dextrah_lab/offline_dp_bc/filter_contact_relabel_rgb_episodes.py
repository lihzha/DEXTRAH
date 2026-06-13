"""Filter an accepted Franka cube RGB relabel NPZ by episode.

The script keeps full episodes and preserves row-level and episode-level
metadata. It can select explicit episode indices, or select episodes whose
first-frame cube centroid is near one of the provided target centroids.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


ROW_KEYS = {"image", "robot_state", "action", "phase_ids"}
EPISODE_KEYS = {"rollout_ids", "rollout_reset_joint_blend_alpha", "rollout_reset_cube_pos_blend_alpha"}
GLOBAL_KEYS = {"source_npzs", "camera_eye", "camera_target", "robot_state_names"}


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    return value


def _episode_bounds(episode_ends: np.ndarray) -> list[tuple[int, int]]:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    return [(int(start), int(end)) for start, end in zip(starts, episode_ends)]


def _parse_centroid(raw: str) -> tuple[float, float]:
    parts = [float(v) for v in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected centroid as cx,cy, got {raw!r}")
    return float(parts[0]), float(parts[1])


def _load_centroid_rows(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a top-level rows list")
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        episode = int(row["episode"])
        out[episode] = row
    return out


def _select_by_centroid(
    *,
    centroid_rows: dict[int, dict[str, Any]],
    targets: list[tuple[float, float]],
    radius: float,
    max_episodes: int | None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for episode, row in centroid_rows.items():
        if "cx" not in row or "cy" not in row:
            continue
        cx = float(row["cx"])
        cy = float(row["cy"])
        distances = [float(np.hypot(cx - tx, cy - ty)) for tx, ty in targets]
        nearest = float(min(distances)) if distances else float("inf")
        if nearest <= float(radius):
            selected.append(
                {
                    "episode": int(episode),
                    "cx": cx,
                    "cy": cy,
                    "nearest_target_distance": nearest,
                    "nearest_target_index": int(np.argmin(distances)),
                }
            )
    selected.sort(key=lambda row: (float(row["nearest_target_distance"]), int(row["episode"])))
    if max_episodes is not None and int(max_episodes) > 0:
        selected = selected[: int(max_episodes)]
    return selected


def filter_dataset(
    *,
    input_path: Path,
    output_path: Path,
    report_path: Path,
    episodes: list[int],
) -> dict[str, Any]:
    data = np.load(input_path, allow_pickle=False)
    required = ROW_KEYS | {"episode_ends"}
    missing = sorted(required.difference(data.files))
    if missing:
        raise KeyError(f"{input_path} is missing required keys: {missing}")

    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    bounds = _episode_bounds(episode_ends)
    if not episodes:
        raise ValueError("No episodes selected")
    for episode in episodes:
        if episode < 0 or episode >= len(bounds):
            raise IndexError(f"Episode {episode} is outside [0, {len(bounds)})")

    row_indices = [np.arange(bounds[episode][0], bounds[episode][1], dtype=np.int64) for episode in episodes]
    row_index = np.concatenate(row_indices, axis=0)
    episode_lengths = [int(bounds[episode][1] - bounds[episode][0]) for episode in episodes]
    output_episode_ends = np.cumsum(np.asarray(episode_lengths, dtype=np.int64))

    save_kwargs: dict[str, Any] = {}
    total_rows = int(episode_ends[-1])
    episode_count = int(episode_ends.shape[0])
    selected_arr = np.asarray(episodes, dtype=np.int32)

    for key in data.files:
        if key == "episode_ends":
            continue
        value = np.asarray(data[key])
        if key in ROW_KEYS or (value.shape[:1] == (total_rows,)):
            save_kwargs[key] = value[row_index]
        elif key in EPISODE_KEYS or (value.shape[:1] == (episode_count,)):
            save_kwargs[key] = value[selected_arr]
        elif key in GLOBAL_KEYS:
            save_kwargs[key] = value
        else:
            save_kwargs[key] = value

    save_kwargs["episode_ends"] = output_episode_ends
    save_kwargs["filtered_source_npz"] = np.asarray(str(input_path))
    save_kwargs["filtered_source_episode_indices"] = selected_arr

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **save_kwargs)

    phase_counts: dict[str, int] = {}
    if "phase_ids" in save_kwargs:
        unique, counts = np.unique(np.asarray(save_kwargs["phase_ids"], dtype=np.int32), return_counts=True)
        phase_counts = {str(int(k)): int(v) for k, v in zip(unique, counts)}
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "selected_episodes": [int(v) for v in episodes],
        "episode_count": int(len(episodes)),
        "episode_lengths": episode_lengths,
        "row_count": int(row_index.shape[0]),
        "image_shape": list(np.asarray(save_kwargs["image"]).shape),
        "robot_state_shape": list(np.asarray(save_kwargs["robot_state"]).shape),
        "action_shape": list(np.asarray(save_kwargs["action"]).shape),
        "phase_counts": phase_counts,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--episode", action="append", type=int, default=[])
    parser.add_argument("--centroids-json", type=Path, default=None)
    parser.add_argument("--target-centroid", action="append", default=[])
    parser.add_argument("--radius", type=float, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected: list[dict[str, Any]] = [{"episode": int(v), "selection": "explicit"} for v in args.episode]
    if args.centroids_json is not None:
        if args.radius is None:
            raise ValueError("--radius is required when using --centroids-json")
        targets = [_parse_centroid(raw) for raw in args.target_centroid]
        if not targets:
            raise ValueError("At least one --target-centroid is required when using --centroids-json")
        selected.extend(
            _select_by_centroid(
                centroid_rows=_load_centroid_rows(args.centroids_json.expanduser().resolve()),
                targets=targets,
                radius=float(args.radius),
                max_episodes=args.max_episodes,
            )
        )

    episodes = sorted({int(row["episode"]) for row in selected})
    summary = filter_dataset(
        input_path=args.input.expanduser().resolve(),
        output_path=args.output.expanduser().resolve(),
        report_path=args.report.expanduser().resolve(),
        episodes=episodes,
    )
    summary["selection"] = selected
    args.report.expanduser().resolve().write_text(
        json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("FRANKA_CUBE_FILTERED_CONTACT_RELABEL_RGB " + json.dumps(_to_builtin(summary), sort_keys=True))


if __name__ == "__main__":
    main()
