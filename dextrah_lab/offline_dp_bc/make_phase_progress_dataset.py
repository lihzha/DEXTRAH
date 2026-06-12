"""Append contact phase/progress features to a Franka cube lowdim NPZ.

This adapter keeps the original 21D Franka cube lowdim state intact and appends
four scalar features:

- contact phase one-hot: align/open, close/hold, lift
- episode progress in [0, 1]

The resulting 25D dataset matches the runtime phase/progress providers in
``ppo_bridge.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .trajectory_conversion import PICK_AND_LIFT_PHASE_ORDER


CONTACT_PHASES = {
    "align_open": 0,
    "close_hold": 1,
    "lift": 2,
}

PICK_LIFT_TO_CONTACT_PHASE = {
    "go_to_pre_grasp_pose": CONTACT_PHASES["align_open"],
    "hold_at_pre_grasp": CONTACT_PHASES["align_open"],
    "go_from_pre_grasp_to_grasp_pose": CONTACT_PHASES["align_open"],
    "hold_at_grasp": CONTACT_PHASES["align_open"],
    "close_fingers": CONTACT_PHASES["close_hold"],
    "hold_after_close": CONTACT_PHASES["close_hold"],
    "lift_object": CONTACT_PHASES["lift"],
    "hold_after_lift": CONTACT_PHASES["lift"],
}


def _to_builtin(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _to_builtin(value.item())
        return [_to_builtin(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    return value


def _is_contact_relabel_phase_ids(raw_phase_ids: np.ndarray) -> bool:
    unique = set(int(v) for v in np.unique(raw_phase_ids))
    return bool(unique) and unique.issubset({-1, 0, 1, 2})


def _is_pick_lift_phase_ids(raw_phase_ids: np.ndarray) -> bool:
    unique = set(int(v) for v in np.unique(raw_phase_ids))
    return bool(unique) and unique.issubset(set(range(len(PICK_AND_LIFT_PHASE_ORDER))))


def _contact_relabel_phase_ids(raw_phase_ids: np.ndarray) -> np.ndarray:
    phase_ids = np.asarray(raw_phase_ids, dtype=np.int32)
    unique = set(int(v) for v in np.unique(phase_ids))
    if not unique.issubset({-1, 0, 1, 2}):
        raise ValueError(
            "Phase/progress augmentation is only defined for contact relabel "
            f"phase ids in {{-1,0,1,2}}, got {sorted(unique)}"
        )
    out = phase_ids.copy()
    out[out < 0] = CONTACT_PHASES["align_open"]
    return out


def _pick_lift_phase_ids_to_contact(raw_phase_ids: np.ndarray) -> np.ndarray:
    """Collapse sorted full-pick/lift phase IDs to three runtime phases."""

    phase_ids = np.asarray(raw_phase_ids, dtype=np.int32)
    sorted_phase_names = sorted(PICK_AND_LIFT_PHASE_ORDER)
    unique = set(int(v) for v in np.unique(phase_ids))
    if not unique.issubset(set(range(len(sorted_phase_names)))):
        raise ValueError(
            "Full pick/lift phase collapse expects phase ids in "
            f"[0,{len(sorted_phase_names)}), got {sorted(unique)}"
        )
    out = np.empty_like(phase_ids, dtype=np.int32)
    for phase_id, phase_name in enumerate(sorted_phase_names):
        out[phase_ids == phase_id] = PICK_LIFT_TO_CONTACT_PHASE[phase_name]
    return out


def _contact_phase_ids(raw_phase_ids: np.ndarray, mode: str) -> tuple[np.ndarray, str]:
    phase_ids = np.asarray(raw_phase_ids, dtype=np.int32)
    if mode == "auto":
        if _is_contact_relabel_phase_ids(phase_ids):
            mode = "contact_relabel"
        elif _is_pick_lift_phase_ids(phase_ids):
            mode = "pick_lift_to_contact"
        else:
            unique = sorted(int(v) for v in np.unique(phase_ids))
            raise ValueError(f"Could not infer phase id schema from unique ids {unique}")
    if mode == "contact_relabel":
        return _contact_relabel_phase_ids(phase_ids), mode
    if mode == "pick_lift_to_contact":
        return _pick_lift_phase_ids_to_contact(phase_ids), mode
    raise ValueError(f"Unsupported --phase-mode {mode!r}")


def _episode_progress(episode_ends: np.ndarray, n_rows: int) -> np.ndarray:
    starts = np.concatenate(([0], episode_ends[:-1])).astype(np.int64)
    progress = np.zeros((n_rows,), dtype=np.float32)
    for start, end in zip(starts, episode_ends):
        length = int(end - start)
        if length <= 1:
            progress[int(start) : int(end)] = 0.0
        else:
            progress[int(start) : int(end)] = np.linspace(0.0, 1.0, length, dtype=np.float32)
    return progress


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--phase-mode",
        choices=("auto", "contact_relabel", "pick_lift_to_contact"),
        default="auto",
        help=(
            "How to interpret input phase_ids before collapsing to "
            "align_open/close_hold/lift."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    report_path = args.report.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    data = np.load(input_path, allow_pickle=False)
    obs = np.asarray(data["obs"], dtype=np.float32)
    action = np.asarray(data["action"], dtype=np.float32)
    episode_ends = np.asarray(data["episode_ends"], dtype=np.int64)
    raw_phase_ids = np.asarray(data["phase_ids"], dtype=np.int32)
    phase_ids, resolved_phase_mode = _contact_phase_ids(raw_phase_ids, str(args.phase_mode))
    if obs.ndim != 2 or obs.shape[1] != 21:
        raise ValueError(f"Expected base obs shape (N,21), got {obs.shape}")
    if action.ndim != 2 or action.shape[1] != 7:
        raise ValueError(f"Expected action shape (N,7), got {action.shape}")
    if episode_ends.ndim != 1 or episode_ends[-1] != obs.shape[0]:
        raise ValueError("episode_ends must be cumulative exclusive ends ending at obs length")

    one_hot = np.eye(3, dtype=np.float32)[phase_ids]
    progress = _episode_progress(episode_ends, int(obs.shape[0]))[:, None]
    augmented_obs = np.concatenate((obs, one_hot, progress), axis=1).astype(np.float32)

    save_kwargs: dict[str, Any] = {
        "obs": augmented_obs,
        "action": action,
        "episode_ends": episode_ends,
        "phase_ids": phase_ids,
        "source_phase_ids": raw_phase_ids,
        "phase_progress_features": np.asarray(
            ["phase_align_open", "phase_close_hold", "phase_lift", "episode_progress"]
        ),
        "source_npz": np.asarray(str(input_path)),
        "source_phase_mode": np.asarray(resolved_phase_mode),
    }
    for key in (
        "rollout_ids",
        "rollout_reset_joint_blend_alpha",
        "rollout_reset_cube_pos_blend_alpha",
    ):
        if key in data.files:
            save_kwargs[key] = data[key]
    np.savez_compressed(output_path, **save_kwargs)

    unique, counts = np.unique(phase_ids, return_counts=True)
    raw_unique, raw_counts = np.unique(raw_phase_ids, return_counts=True)
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "phase_mode": resolved_phase_mode,
        "obs_shape_before": list(obs.shape),
        "obs_shape_after": list(augmented_obs.shape),
        "action_shape": list(action.shape),
        "episode_ends": episode_ends.astype(int).tolist(),
        "appended_features": save_kwargs["phase_progress_features"].tolist(),
        "phase_counts": {str(int(k)): int(v) for k, v in zip(unique, counts)},
        "source_phase_counts": {str(int(k)): int(v) for k, v in zip(raw_unique, raw_counts)},
        "progress_min": float(np.min(progress)),
        "progress_max": float(np.max(progress)),
        "scope": "25D official-DP dataset; runtime eval needs the matching phase/progress provider",
    }
    (report_path.parent / "phase_progress_dataset_summary.json").write_text(
        json.dumps(_to_builtin(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Phase/Progress Lowdim Dataset",
        "",
        f"- input: `{input_path}`",
        f"- output: `{output_path}`",
        f"- phase mode: `{resolved_phase_mode}`",
        f"- obs before/after: `{tuple(obs.shape)}` -> `{tuple(augmented_obs.shape)}`",
        f"- action shape: `{tuple(action.shape)}`",
        f"- episode ends: `{episode_ends.astype(int).tolist()}`",
        f"- appended features: `{summary['appended_features']}`",
        f"- phase counts: `{summary['phase_counts']}`",
        f"- source phase counts: `{summary['source_phase_counts']}`",
        f"- scope: {summary['scope']}",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("FRANKA_CUBE_PHASE_PROGRESS_DATASET " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
