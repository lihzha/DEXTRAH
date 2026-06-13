"""Generate contact-relabel specs for uniformly sampled Franka cube locations.

The default bounds match the Dextrah-Franka-Cube-Grasp reachable task support:
pickup center ``(-0.36, -0.12)`` with ``cube_spawn_xy_randomization=0.08``.
The output ``.env`` can be sourced before submitting
``cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh``.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_CENTER_X = -0.36
DEFAULT_CENTER_Y = -0.12
DEFAULT_HALF_WIDTH = 0.08
DEFAULT_EPISODE = 24
DEFAULT_EPISODE_STEP = 260


def _parse_int_list(raw: str) -> list[int]:
    values = [item.strip() for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError("Expected at least one integer")
    return [int(item) for item in values]


def _shell_assign(name: str, value: str) -> str:
    return f"{name}={shlex.quote(str(value))}"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260613)
    parser.add_argument("--seed_base", type=int, default=700000)
    parser.add_argument("--episodes", type=str, default=str(DEFAULT_EPISODE))
    parser.add_argument("--episode_steps", type=str, default=str(DEFAULT_EPISODE_STEP))
    parser.add_argument("--trajectory", type=str, default="")
    parser.add_argument("--joint_alpha", type=float, default=0.0)
    parser.add_argument("--center_x", type=float, default=DEFAULT_CENTER_X)
    parser.add_argument("--center_y", type=float, default=DEFAULT_CENTER_Y)
    parser.add_argument("--half_width_x", type=float, default=DEFAULT_HALF_WIDTH)
    parser.add_argument("--half_width_y", type=float, default=DEFAULT_HALF_WIDTH)
    parser.add_argument("--output_env", required=True, type=Path)
    parser.add_argument("--output_json", required=True, type=Path)
    parser.add_argument("--output_csv", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = int(args.count)
    if count <= 0:
        raise ValueError("--count must be positive")
    episodes = _parse_int_list(args.episodes)
    episode_steps = _parse_int_list(args.episode_steps)
    rng = np.random.default_rng(int(args.seed))
    x_min = float(args.center_x) - float(args.half_width_x)
    x_max = float(args.center_x) + float(args.half_width_x)
    y_min = float(args.center_y) - float(args.half_width_y)
    y_max = float(args.center_y) + float(args.half_width_y)
    xy = np.column_stack(
        (
            rng.uniform(x_min, x_max, size=count),
            rng.uniform(y_min, y_max, size=count),
        )
    ).astype(np.float32)

    specs: list[dict[str, Any]] = []
    for idx, (cube_x, cube_y) in enumerate(xy):
        episode = int(episodes[idx % len(episodes)])
        episode_step = int(episode_steps[idx % len(episode_steps)])
        rollout_seed = int(args.seed_base) + idx
        spec = f"{episode}:{episode_step}:{args.trajectory}:{float(args.joint_alpha):.6g}:{rollout_seed}:{cube_x:.6f}:{cube_y:.6f}"
        specs.append(
            {
                "index": idx,
                "spec": spec,
                "episode": episode,
                "episode_step": episode_step,
                "trajectory": str(args.trajectory),
                "joint_alpha": float(args.joint_alpha),
                "seed": rollout_seed,
                "cube_x": float(cube_x),
                "cube_y": float(cube_y),
            }
        )

    for path in (args.output_env, args.output_json, args.output_csv):
        path.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    env_lines = [
        "# Source with: set -a; source <this-file>; set +a",
        _shell_assign("SPEC_COUNT", str(count)),
    ]
    for row in specs:
        env_lines.append(_shell_assign(f"SPEC_{row['index']}", str(row["spec"])))
    args.output_env.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    summary = {
        "count": count,
        "seed": int(args.seed),
        "seed_base": int(args.seed_base),
        "support": {
            "center": [float(args.center_x), float(args.center_y)],
            "half_width": [float(args.half_width_x), float(args.half_width_y)],
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
        },
        "episodes": episodes,
        "episode_steps": episode_steps,
        "joint_alpha": float(args.joint_alpha),
        "trajectory": str(args.trajectory),
        "cube_xy_min": xy.min(axis=0).astype(float).tolist(),
        "cube_xy_max": xy.max(axis=0).astype(float).tolist(),
        "cube_xy_unique_rounded_1mm": int(np.unique(np.round(xy, 3), axis=0).shape[0]),
        "specs": specs,
    }
    args.output_json.write_text(json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with args.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(specs[0].keys()))
        writer.writeheader()
        writer.writerows(specs)

    print("FRANKA_CUBE_UNIFORM_RELABEL_SPECS " + json.dumps(_to_builtin(summary), sort_keys=True))


if __name__ == "__main__":
    main()
