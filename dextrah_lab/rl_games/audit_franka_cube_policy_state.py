"""Audit Franka cube reset-prior checkpoint actions and observation state.

This is diagnostic-only instrumentation for the GraspGenX pass7 reset-prior
branch. It does not step PPO training or modify the task; it samples valid reset
states, records checkpoint actor outputs, and compares them to training JSONL
action trends.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--num_resets", type=int, default=3)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--grasp_prior_library_path", type=str, required=True)
parser.add_argument("--training_jsonl_path", type=str, default=None)
parser.add_argument(
    "--checkpoint",
    action="append",
    default=[],
    help="Policy checkpoint as label=/container/path/to/model.pth. May be repeated.",
)
parser.add_argument("--stochastic_samples", type=int, default=16)
parser.add_argument("--histogram_bins", type=int, default=41)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch

from rl_games.common import env_configurations, vecenv
from rl_games.common.player import BasePlayer
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import isaaclab_tasks  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401


ACTION_NAMES = ("x", "y", "z", "roll", "pitch", "yaw", "gripper")
TRAINING_KEYS = (
    "cube_action_z",
    "cube_action_up",
    "cube_action_down",
    "cube_gripper_action",
    "cube_gripper_close_action",
    "cube_gripper_width",
    "cube_ee_to_cube_dist",
    "cube_finger_center_to_cube_dist",
    "cube_approach_reward",
    "cube_enclosure_reward",
    "cube_lift_action_reward",
    "cube_lift_reward",
    "cube_success_rate",
    "cube_has_lifted_rate",
    "cube_grasp_prior_reset_success_rate",
    "cube_grasp_prior_quality_success_rate",
)


class DextrahStateAuditVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


class DextrahStateAuditGpuEnv(RlGamesGpuEnv):
    def get_current_obs(self):
        if hasattr(self.env, "get_current_obs"):
            return self.env.get_current_obs()
        raise AttributeError("Wrapped environment does not expose get_current_obs")


def _json_safe(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return float(value.detach().cpu())
        return value.detach().float().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    leading = ["checkpoint", "source", "mode", "reset_index", "env_id", "dim", "action_dim", "key", "epoch"]
    for key in reversed(leading):
        if key in fieldnames:
            fieldnames.remove(key)
            fieldnames.insert(0, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _tensor_stats(values: torch.Tensor | np.ndarray) -> dict[str, float]:
    arr = values.detach().float().cpu().numpy() if isinstance(values, torch.Tensor) else np.asarray(values, dtype=float)
    arr = arr.reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"mean": math.nan, "std": math.nan, "min": math.nan, "max": math.nan, "p05": math.nan, "p50": math.nan, "p95": math.nan}
    return {
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite)),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "p05": float(np.percentile(finite, 5)),
        "p50": float(np.percentile(finite, 50)),
        "p95": float(np.percentile(finite, 95)),
    }


def _dim_summary(
    tensor: torch.Tensor,
    *,
    source: str,
    reset_index: int | str,
    checkpoint: str | None = None,
    mode: str | None = None,
    key: str | None = None,
) -> list[dict[str, Any]]:
    tensor = tensor.detach().float().cpu()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    rows: list[dict[str, Any]] = []
    for dim in range(tensor.shape[-1]):
        stats = _tensor_stats(tensor[..., dim])
        rows.append(
            {
                "checkpoint": checkpoint,
                "mode": mode,
                "source": source,
                "key": key,
                "reset_index": reset_index,
                "dim": dim,
                **stats,
            }
        )
    return rows


def _action_summary_rows(
    tensor: torch.Tensor,
    *,
    checkpoint: str,
    mode: str,
    reset_index: int | str,
    source: str,
) -> list[dict[str, Any]]:
    tensor = tensor.detach().float().cpu()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    rows: list[dict[str, Any]] = []
    for dim in range(tensor.shape[-1]):
        stats = _tensor_stats(tensor[..., dim])
        rows.append(
            {
                "checkpoint": checkpoint,
                "mode": mode,
                "reset_index": reset_index,
                "source": source,
                "action_dim": dim,
                "action_name": ACTION_NAMES[dim] if dim < len(ACTION_NAMES) else f"dim{dim}",
                "sat_frac_abs_ge_0p95": float((tensor[..., dim].abs() >= 0.95).float().mean()),
                "open_positive_or_up_positive": bool(dim in (2, 6)),
                **stats,
            }
        )
    return rows


def _sample_action_rows(
    tensor: torch.Tensor,
    *,
    checkpoint: str,
    mode: str,
    reset_index: int,
    source: str,
    max_envs: int = 8,
) -> list[dict[str, Any]]:
    tensor = tensor.detach().float().cpu()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    rows: list[dict[str, Any]] = []
    for env_id in range(min(max_envs, tensor.shape[0])):
        row = {
            "checkpoint": checkpoint,
            "mode": mode,
            "reset_index": int(reset_index),
            "source": source,
            "env_id": env_id,
        }
        for dim in range(tensor.shape[-1]):
            name = ACTION_NAMES[dim] if dim < len(ACTION_NAMES) else f"dim{dim}"
            row[f"action_{name}"] = float(tensor[env_id, dim])
        rows.append(row)
    return rows


def _parse_checkpoints(values: list[str]) -> dict[str, str]:
    checkpoints: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected checkpoint as label=path, got {item!r}")
        label, path = item.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"Empty checkpoint label in {item!r}")
        checkpoints[label] = retrieve_file_path(path.strip())
    return checkpoints


def _create_player(agent_cfg: dict, env, label: str, checkpoint_path: str) -> BasePlayer:
    cfg = copy.deepcopy(agent_cfg)
    cfg["params"]["load_checkpoint"] = True
    cfg["params"]["load_path"] = checkpoint_path
    cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    print(f"[INFO] Loading {label}: {checkpoint_path}", flush=True)
    runner = Runner()
    runner.load(cfg)
    player: BasePlayer = runner.create_player()
    player.restore(checkpoint_path)
    player.reset()
    return player


def _obs_policy_tensor(obs):
    if isinstance(obs, tuple):
        obs = obs[0]
    if isinstance(obs, dict):
        obs = obs["obs"]
    return obs


def _prepare_player(player: BasePlayer, obs: torch.Tensor) -> torch.Tensor:
    player.reset()
    obs_t = player.obs_to_torch(obs)
    _ = player.get_batch_size(obs_t, 1)
    if player.is_rnn:
        player.init_rnn()
    return obs_t


def _raw_model_outputs(player: BasePlayer, obs_t: torch.Tensor) -> tuple[dict[str, torch.Tensor], str | None]:
    input_dict: dict[str, Any] = {"is_train": False, "prev_actions": None, "obs": obs_t}
    if getattr(player, "is_rnn", False):
        input_dict["rnn_states"] = getattr(player, "states", None)
    try:
        out = player.model(input_dict)
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    tensor_out: dict[str, torch.Tensor] = {}
    if isinstance(out, dict):
        for key, value in out.items():
            if isinstance(value, torch.Tensor):
                tensor_out[key] = value.detach().clone()
    return tensor_out, None


def _flatten_checkpoint_tensors(value: Any, prefix: str = "") -> dict[str, torch.Tensor]:
    out: dict[str, torch.Tensor] = {}
    if isinstance(value, torch.Tensor):
        out[prefix] = value.detach().cpu()
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_checkpoint_tensors(item, child))
    elif isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            child = f"{prefix}.{idx}" if prefix else str(idx)
            out.update(_flatten_checkpoint_tensors(item, child))
    return out


def _checkpoint_tensor_summary(label: str, checkpoint_path: str, obs_dim: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, torch.Tensor]]]:
    state = torch.load(checkpoint_path, map_location="cpu")
    tensors = _flatten_checkpoint_tensors(state)
    interesting_rows: list[dict[str, Any]] = []
    rms_pairs: list[dict[str, torch.Tensor]] = []
    for key, tensor in tensors.items():
        lower = key.lower()
        if not any(token in lower for token in ("running", "rms", "mean", "std", "var", "sigma")):
            continue
        row = {
            "checkpoint": label,
            "key": key,
            "shape": list(tensor.shape),
            "numel": int(tensor.numel()),
            **_tensor_stats(tensor.float()),
        }
        interesting_rows.append(row)
    for key, mean in tensors.items():
        lower = key.lower()
        if mean.ndim != 1 or mean.numel() != obs_dim:
            continue
        if not (lower.endswith("running_mean") or lower.endswith("moving_mean") or "running_mean" in lower):
            continue
        candidate_var_keys = [
            key.replace("running_mean", "running_var"),
            key.replace("running_mean", "running_std"),
            key.replace("moving_mean", "moving_var"),
            key.replace("mean", "var"),
            key.replace("mean", "std"),
        ]
        for var_key in candidate_var_keys:
            var = tensors.get(var_key)
            if isinstance(var, torch.Tensor) and var.shape == mean.shape:
                rms_pairs.append({"mean_key": key, "var_key": var_key, "mean": mean.float(), "var_or_std": var.float()})
                break
    summary = {
        "checkpoint": label,
        "path": checkpoint_path,
        "top_level_keys": list(state.keys()) if isinstance(state, dict) else [],
        "num_tensors": len(tensors),
        "interesting_tensor_count": len(interesting_rows),
        "obs_rms_pair_count": len(rms_pairs),
        "obs_rms_pairs": [{"mean_key": p["mean_key"], "var_key": p["var_key"]} for p in rms_pairs],
    }
    return summary, interesting_rows, rms_pairs


def _reset_sample_summary(task_env, reset_index: int) -> dict[str, Any]:
    sample_index = getattr(task_env, "grasp_prior_reset_sample_index", None)
    sample_hist: dict[int, int] = {}
    if isinstance(sample_index, torch.Tensor):
        unique, counts = torch.unique(sample_index.detach().cpu(), return_counts=True)
        sample_hist = {int(k): int(v) for k, v in zip(unique.tolist(), counts.tolist(), strict=True)}
    fields = {
        "reset_index": reset_index,
        "sample_histogram": sample_hist,
    }
    for name in (
        "grasp_prior_reset_attempted",
        "grasp_prior_reset_success",
        "grasp_prior_reset_quality_success",
        "grasp_prior_reset_farther",
        "grasp_prior_reset_pos_error",
        "grasp_prior_reset_rot_error",
        "grasp_prior_reset_projected_exact_tip_center_dist",
        "grasp_prior_reset_projected_exact_tip_max_dist",
        "grasp_prior_reset_open_width_margin",
        "grasp_prior_reset_pregrasp_tip_table_clearance",
        "ee_to_cube_dist",
        "finger_center_to_cube_dist",
        "gripper_width",
    ):
        if hasattr(task_env, name):
            value = getattr(task_env, name)
            if isinstance(value, torch.Tensor):
                fields[f"{name}_mean"] = float(value.detach().float().mean().cpu())
                fields[f"{name}_min"] = float(value.detach().float().min().cpu())
                fields[f"{name}_max"] = float(value.detach().float().max().cpu())
    return fields


def _read_training_jsonl(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    training_path = retrieve_file_path(path)
    rows: list[dict[str, Any]] = []
    with Path(training_path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            payload = json.loads(line)
            scalars = payload.get("scalars", {})
            row: dict[str, Any] = {
                "epoch": payload.get("epoch"),
                "frame": payload.get("frame"),
                "wall_time": payload.get("wall_time"),
            }
            for key in TRAINING_KEYS:
                if key in scalars:
                    row[key] = scalars[key]
            rows.append(row)
    return rows


def _write_plots(
    output_dir: Path,
    *,
    action_rows: list[dict[str, Any]],
    zscore_rows: list[dict[str, Any]],
    training_rows: list[dict[str, Any]],
) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[WARN] matplotlib unavailable; skipping plots: {exc}", flush=True)
        return artifacts

    if action_rows:
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        axes = axes.ravel()
        for dim in range(len(ACTION_NAMES)):
            ax = axes[dim]
            for label in sorted({row["checkpoint"] for row in action_rows}):
                values = [
                    float(row["value"])
                    for row in action_rows
                    if row["checkpoint"] == label and row["mode"] == "deterministic" and int(row["action_dim"]) == dim
                ]
                if values:
                    ax.hist(values, bins=int(args_cli.histogram_bins), alpha=0.45, label=label, range=(-1.0, 1.0))
            ax.set_title(ACTION_NAMES[dim])
            ax.set_xlim(-1.05, 1.05)
            ax.grid(True, alpha=0.2)
        axes[-1].axis("off")
        axes[0].legend(fontsize=8)
        fig.suptitle("Deterministic reset action histograms by dimension")
        fig.tight_layout()
        path = output_dir / "action_histograms.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["action_histograms"] = str(path)

    if zscore_rows:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label in sorted({row["checkpoint"] for row in zscore_rows}):
            values = [float(row["z_abs_p95"]) for row in zscore_rows if row["checkpoint"] == label]
            if values:
                ax.hist(values, bins=30, alpha=0.45, label=label)
        ax.set_xlabel("per-dim abs z p95 for reset observations")
        ax.set_ylabel("observation dimensions")
        ax.grid(True, alpha=0.25)
        ax.legend()
        path = output_dir / "observation_zscore_histograms.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["observation_zscore_histograms"] = str(path)

    if training_rows:
        fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
        epochs = [int(row["epoch"]) for row in training_rows if row.get("epoch") is not None]
        for key in ("cube_action_z", "cube_gripper_action", "cube_action_up", "cube_action_down"):
            vals = [float(row.get(key, math.nan)) for row in training_rows]
            axes[0].plot(epochs, vals, label=key)
        for key in ("cube_ee_to_cube_dist", "cube_finger_center_to_cube_dist", "cube_gripper_width"):
            vals = [float(row.get(key, math.nan)) for row in training_rows]
            axes[1].plot(epochs, vals, label=key)
        for key in ("cube_approach_reward", "cube_enclosure_reward", "cube_lift_action_reward", "cube_lift_reward"):
            vals = [float(row.get(key, math.nan)) for row in training_rows]
            axes[2].plot(epochs, vals, label=key)
        axes[0].set_ylabel("action")
        axes[1].set_ylabel("m")
        axes[2].set_ylabel("reward term")
        axes[2].set_xlabel("epoch")
        for ax in axes:
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=8)
        fig.tight_layout()
        path = output_dir / "training_action_trends.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["training_action_trends"] = str(path)
    return artifacts


def _write_report(
    path: Path,
    *,
    config: dict[str, Any],
    checkpoint_summaries: dict[str, Any],
    action_summary_rows: list[dict[str, Any]],
    zscore_rows: list[dict[str, Any]],
    training_rows: list[dict[str, Any]],
    reset_rows: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> None:
    det_rows = [row for row in action_summary_rows if row.get("mode") == "deterministic"]
    latest_training = training_rows[-1] if training_rows else {}
    lines = [
        "# Franka Cube Pass7 Policy State Audit",
        "",
        "Diagnostic-only run. No PPO/A100 launch and no task/reward/action semantic change.",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(_json_safe(config), indent=2, sort_keys=True),
        "```",
        "",
        "## Action Sign And Scale",
        "",
        "- Action dimensions are `[x, y, z, roll, pitch, yaw, gripper]`.",
        "- The Franka task clamps actions to `[-1, 1]`.",
        "- Positive `action_z` is upward IK motion; `+1.0` maps to the configured z scale.",
        "- Gripper action `-1` closes, `+1` opens; `+1.0` maps to full open width.",
        "",
        "## Deterministic Reset Actions",
        "",
        "| Checkpoint | x | y | z | roll | pitch | yaw | gripper | z sat | grip sat |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    by_ckpt: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in det_rows:
        by_ckpt[str(row["checkpoint"])][int(row["action_dim"])] = row
    for label in sorted(by_ckpt):
        dims = by_ckpt[label]
        means = [float(dims[idx]["mean"]) if idx in dims else math.nan for idx in range(7)]
        z_sat = float(dims[2].get("sat_frac_abs_ge_0p95", math.nan)) if 2 in dims else math.nan
        grip_sat = float(dims[6].get("sat_frac_abs_ge_0p95", math.nan)) if 6 in dims else math.nan
        lines.append(
            "| "
            + " | ".join(
                [f"`{label}`"] + [f"{v:.3f}" for v in means] + [f"{z_sat:.3f}", f"{grip_sat:.3f}"]
            )
            + " |"
        )
    lines.extend(["", "## Observation RMS / Z-Score", ""])
    if zscore_rows:
        lines.append("| Checkpoint | RMS pair | max abs-z p95 | dims abs-z p95 > 3 | dims abs-z p95 > 5 |")
        lines.append("| --- | --- | ---: | ---: | ---: |")
        by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in zscore_rows:
            by_pair[(str(row["checkpoint"]), str(row["rms_pair"]))].append(row)
        for (label, pair), rows in sorted(by_pair.items()):
            max_p95 = max(float(row["z_abs_p95"]) for row in rows)
            gt3 = sum(float(row["z_abs_p95"]) > 3.0 for row in rows)
            gt5 = sum(float(row["z_abs_p95"]) > 5.0 for row in rows)
            lines.append(f"| `{label}` | `{pair}` | {max_p95:.3f} | {gt3} | {gt5} |")
    else:
        lines.append("- No observation-shaped RMS pair was found in the checkpoints, or RMS extraction failed.")
    lines.extend(["", "## Training-Side Action Trend", ""])
    if latest_training:
        lines.append(
            "- Latest JSONL epoch "
            f"`{latest_training.get('epoch')}`: cube_action_z=`{float(latest_training.get('cube_action_z', math.nan)):.3f}`, "
            f"cube_gripper_action=`{float(latest_training.get('cube_gripper_action', math.nan)):.3f}`, "
            f"EE distance=`{float(latest_training.get('cube_ee_to_cube_dist', math.nan)):.3f}`, "
            f"finger distance=`{float(latest_training.get('cube_finger_center_to_cube_dist', math.nan)):.3f}`."
        )
    else:
        lines.append("- No training JSONL provided or readable.")
    lines.extend(["", "## Reset Health", ""])
    if reset_rows:
        reset_success = np.mean([float(row.get("grasp_prior_reset_success_mean", 0.0)) for row in reset_rows])
        quality = np.mean([float(row.get("grasp_prior_reset_quality_success_mean", 0.0)) for row in reset_rows])
        lines.append(f"- Mean reset success across sampled batches: `{reset_success:.3f}`; reset quality: `{quality:.3f}`.")
    lines.extend(["", "## Checkpoint State Summary", ""])
    for label, summary in checkpoint_summaries.items():
        lines.append(
            f"- `{label}`: obs_rms_pair_count=`{summary.get('obs_rms_pair_count')}`, "
            f"interesting_tensor_count=`{summary.get('interesting_tensor_count')}`, path=`{summary.get('path')}`"
        )
    lines.extend(["", "## Artifacts", ""])
    for name, artifact_path in artifacts.items():
        lines.append(f"- `{name}`: `{artifact_path}`")
    lines.extend(["", "## Verdict", ""])
    if "ep45" in by_ckpt and 2 in by_ckpt["ep45"] and 6 in by_ckpt["ep45"]:
        z_mean = float(by_ckpt["ep45"][2]["mean"])
        g_mean = float(by_ckpt["ep45"][6]["mean"])
        if z_mean > 0.5 and g_mean > 0.5:
            lines.append(
                "- The ep45 actor itself outputs the open/up bias at reset in deterministic mode. "
                "This matches the training JSONL trend and is not caused by the rollout renderer or post-reset stepping logic."
            )
        else:
            lines.append(
                "- Ep45 deterministic reset actions are not strongly open/up in this diagnostic; investigate rollout-time state drift or stochastic/action-scaling effects next."
            )
    else:
        lines.append("- Could not derive an ep45 deterministic reset-action verdict from the output tables.")
    lines.append(
        "- No A100/PPO scale-up is justified from this diagnostic alone; the next experiment should be a bounded diagnostic-only action prior/curriculum or policy-distribution intervention if the reset-state actor bias is confirmed."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("policy_state_audit_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"

    checkpoints = _parse_checkpoints(args_cli.checkpoint)
    if not checkpoints:
        raise ValueError("At least one --checkpoint label=path is required.")

    env_cfg.scene.num_envs = int(args_cli.num_envs)
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = int(args_cli.seed)
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_library_path = str(args_cli.grasp_prior_library_path)
    env_cfg.cube_spawn_xy_randomization = float(args_cli.cube_spawn_xy_randomization)
    if hasattr(env_cfg, "use_cuda_graph"):
        env_cfg.use_cuda_graph = False
    agent_cfg["params"]["seed"] = int(args_cli.seed)

    print("[INFO] Policy state audit config:")
    print_dict(
        {
            "task": args_cli.task,
            "num_envs": env_cfg.scene.num_envs,
            "num_resets": args_cli.num_resets,
            "seed": args_cli.seed,
            "cube_spawn_xy_randomization": args_cli.cube_spawn_xy_randomization,
            "grasp_prior_library_path": args_cli.grasp_prior_library_path,
            "training_jsonl_path": args_cli.training_jsonl_path,
            "checkpoints": checkpoints,
            "output_dir": str(output_dir),
        },
        nesting=4,
    )

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    gym_env = gym.make(args_cli.task, cfg=env_cfg)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    env = DextrahStateAuditVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register(
        "DextrahPolicyStateAuditWrapper",
        lambda config_name, num_actors, **kwargs: DextrahStateAuditGpuEnv(config_name, num_actors, **kwargs),
    )
    env_configurations.register("rlgpu", {"vecenv_type": "DextrahPolicyStateAuditWrapper", "env_creator": lambda **kwargs: env})

    players = {label: _create_player(agent_cfg, env, label, path) for label, path in checkpoints.items()}

    processed_obs_batches: list[torch.Tensor] = []
    raw_obs_batches: list[torch.Tensor] = []
    reset_rows: list[dict[str, Any]] = []
    observation_rows: list[dict[str, Any]] = []
    action_summary: list[dict[str, Any]] = []
    action_samples: list[dict[str, Any]] = []
    action_values_for_hist: list[dict[str, Any]] = []
    actor_output_summary: list[dict[str, Any]] = []
    actor_output_samples: list[dict[str, Any]] = []

    for reset_index in range(int(args_cli.num_resets)):
        obs = env.reset()
        obs = _obs_policy_tensor(obs)
        raw_obs = task_env._get_observations()["policy"]
        processed_obs_batches.append(obs.detach().clone())
        raw_obs_batches.append(raw_obs.detach().clone())
        reset_rows.append(_reset_sample_summary(task_env, reset_index))
        observation_rows.extend(_dim_summary(obs, source="rlgames_processed_obs", reset_index=reset_index))
        observation_rows.extend(_dim_summary(raw_obs, source="task_policy_obs", reset_index=reset_index))

        for label, player in players.items():
            obs_t = _prepare_player(player, obs)
            with torch.inference_mode():
                deterministic_actions = player.get_action(obs_t, is_deterministic=True).detach().clone()
            action_summary.extend(
                _action_summary_rows(
                    deterministic_actions,
                    checkpoint=label,
                    mode="deterministic",
                    reset_index=reset_index,
                    source="player_get_action",
                )
            )
            action_samples.extend(
                _sample_action_rows(
                    deterministic_actions,
                    checkpoint=label,
                    mode="deterministic",
                    reset_index=reset_index,
                    source="player_get_action",
                )
            )
            for env_id in range(deterministic_actions.shape[0]):
                for dim in range(deterministic_actions.shape[-1]):
                    action_values_for_hist.append(
                        {
                            "checkpoint": label,
                            "mode": "deterministic",
                            "reset_index": reset_index,
                            "env_id": env_id,
                            "action_dim": dim,
                            "value": float(deterministic_actions[env_id, dim].detach().cpu()),
                        }
                    )

            stochastic_actions = []
            for sample_idx in range(max(int(args_cli.stochastic_samples), 0)):
                obs_t = _prepare_player(player, obs)
                with torch.inference_mode():
                    action = player.get_action(obs_t, is_deterministic=False).detach().clone()
                stochastic_actions.append(action)
                if sample_idx < 2:
                    action_samples.extend(
                        _sample_action_rows(
                            action,
                            checkpoint=label,
                            mode=f"stochastic_sample_{sample_idx}",
                            reset_index=reset_index,
                            source="player_get_action",
                        )
                    )
            if stochastic_actions:
                stacked = torch.stack(stochastic_actions, dim=0).reshape(-1, stochastic_actions[0].shape[-1])
                action_summary.extend(
                    _action_summary_rows(
                        stacked,
                        checkpoint=label,
                        mode="stochastic",
                        reset_index=reset_index,
                        source=f"{len(stochastic_actions)}x_player_get_action",
                    )
                )

            obs_t = _prepare_player(player, obs)
            raw_outputs, model_error = _raw_model_outputs(player, obs_t)
            if model_error is not None:
                actor_output_summary.append(
                    {
                        "checkpoint": label,
                        "reset_index": reset_index,
                        "key": "model_error",
                        "error": model_error,
                    }
                )
            for key, value in raw_outputs.items():
                if value.ndim >= 2 and value.shape[-1] <= 128:
                    actor_output_summary.extend(
                        _dim_summary(value, source="player_model_raw_output", reset_index=reset_index, checkpoint=label, key=key)
                    )
                    if value.shape[-1] == len(ACTION_NAMES):
                        actor_output_samples.extend(
                            _sample_action_rows(
                                value,
                                checkpoint=label,
                                mode=f"raw_model_{key}",
                                reset_index=reset_index,
                                source="player_model",
                            )
                        )
                else:
                    actor_output_summary.append(
                        {
                            "checkpoint": label,
                            "reset_index": reset_index,
                            "key": key,
                            "shape": list(value.shape),
                            **_tensor_stats(value),
                        }
                    )

    all_processed_obs = torch.cat(processed_obs_batches, dim=0)
    all_raw_obs = torch.cat(raw_obs_batches, dim=0)
    obs_dim = int(all_processed_obs.shape[-1])
    observation_rows.extend(_dim_summary(all_processed_obs, source="rlgames_processed_obs_all", reset_index="all"))
    observation_rows.extend(_dim_summary(all_raw_obs, source="task_policy_obs_all", reset_index="all"))

    checkpoint_summaries: dict[str, Any] = {}
    checkpoint_tensor_rows: list[dict[str, Any]] = []
    zscore_rows: list[dict[str, Any]] = []
    for label, path in checkpoints.items():
        summary, tensor_rows, rms_pairs = _checkpoint_tensor_summary(label, path, obs_dim)
        checkpoint_summaries[label] = summary
        checkpoint_tensor_rows.extend(tensor_rows)
        for pair in rms_pairs:
            mean = pair["mean"].to(all_processed_obs.device)
            var_or_std = torch.clamp(pair["var_or_std"].to(all_processed_obs.device), min=1.0e-8)
            # RL-Games stores running_var for RunningMeanStd. If this was a std tensor,
            # taking sqrt again is conservative and will show in the report as a pair name.
            z = (all_processed_obs - mean) / torch.sqrt(var_or_std + 1.0e-5)
            for dim in range(obs_dim):
                values = z[:, dim].detach().float().cpu().numpy()
                finite = values[np.isfinite(values)]
                row = {
                    "checkpoint": label,
                    "rms_pair": f"{pair['mean_key']} / {pair['var_key']}",
                    "dim": dim,
                    "z_mean": float(np.mean(finite)) if finite.size else math.nan,
                    "z_std": float(np.std(finite)) if finite.size else math.nan,
                    "z_min": float(np.min(finite)) if finite.size else math.nan,
                    "z_max": float(np.max(finite)) if finite.size else math.nan,
                    "z_abs_p95": float(np.percentile(np.abs(finite), 95)) if finite.size else math.nan,
                    "z_abs_max": float(np.max(np.abs(finite))) if finite.size else math.nan,
                }
                zscore_rows.append(row)

    training_rows = _read_training_jsonl(args_cli.training_jsonl_path)

    artifacts = {
        "reset_observation_dim_summary_csv": str(output_dir / "reset_observation_dim_summary.csv"),
        "observation_zscore_summary_csv": str(output_dir / "observation_zscore_summary.csv"),
        "policy_action_dim_summary_csv": str(output_dir / "policy_action_dim_summary.csv"),
        "policy_action_samples_csv": str(output_dir / "policy_action_samples.csv"),
        "actor_output_dim_summary_csv": str(output_dir / "actor_output_dim_summary.csv"),
        "actor_output_samples_csv": str(output_dir / "actor_output_samples.csv"),
        "checkpoint_tensor_summary_csv": str(output_dir / "checkpoint_tensor_summary.csv"),
        "training_action_epoch_summary_csv": str(output_dir / "training_action_epoch_summary.csv"),
        "reset_batch_summary_csv": str(output_dir / "reset_batch_summary.csv"),
        "checkpoint_state_summary_json": str(output_dir / "checkpoint_state_summary.json"),
    }
    plot_artifacts = _write_plots(
        output_dir,
        action_rows=action_values_for_hist,
        zscore_rows=zscore_rows,
        training_rows=training_rows,
    )
    artifacts.update(plot_artifacts)

    _write_csv(output_dir / "reset_observation_dim_summary.csv", observation_rows)
    _write_csv(output_dir / "observation_zscore_summary.csv", zscore_rows)
    _write_csv(output_dir / "policy_action_dim_summary.csv", action_summary)
    _write_csv(output_dir / "policy_action_samples.csv", action_samples)
    _write_csv(output_dir / "actor_output_dim_summary.csv", actor_output_summary)
    _write_csv(output_dir / "actor_output_samples.csv", actor_output_samples)
    _write_csv(output_dir / "checkpoint_tensor_summary.csv", checkpoint_tensor_rows)
    _write_csv(output_dir / "training_action_epoch_summary.csv", training_rows)
    _write_csv(output_dir / "reset_batch_summary.csv", reset_rows)
    _write_json(output_dir / "checkpoint_state_summary.json", checkpoint_summaries)

    config = {
        "task": args_cli.task,
        "num_envs": int(args_cli.num_envs),
        "num_resets": int(args_cli.num_resets),
        "seed": int(args_cli.seed),
        "cube_spawn_xy_randomization": float(args_cli.cube_spawn_xy_randomization),
        "grasp_prior_library_path": str(args_cli.grasp_prior_library_path),
        "training_jsonl_path": args_cli.training_jsonl_path,
        "checkpoints": checkpoints,
        "stochastic_samples": int(args_cli.stochastic_samples),
        "clip_observations": float(clip_obs),
        "clip_actions": float(clip_actions),
        "action_scale": _json_safe(getattr(task_env, "action_scale", torch.empty(0))),
        "max_gripper_width": float(getattr(task_env.cfg, "max_gripper_width", math.nan)),
        "action_semantics": {
            "action_z_positive": "upward IK delta",
            "action_gripper_negative": "close",
            "action_gripper_positive": "open",
        },
    }
    report_path = output_dir / "REPORT.md"
    artifacts["report"] = str(report_path)
    _write_report(
        report_path,
        config=config,
        checkpoint_summaries=checkpoint_summaries,
        action_summary_rows=action_summary,
        zscore_rows=zscore_rows,
        training_rows=training_rows,
        reset_rows=reset_rows,
        artifacts=artifacts,
    )

    payload = {
        "config": config,
        "checkpoint_summaries": checkpoint_summaries,
        "reset_batch_summary": reset_rows,
        "policy_action_dim_summary": action_summary,
        "observation_zscore_summary": zscore_rows,
        "training_action_epoch_summary": training_rows,
        "artifacts": artifacts,
    }
    _write_json(metrics_path, payload)
    print(f"[INFO] Wrote policy state metrics to {metrics_path}", flush=True)
    print(f"[INFO] Wrote policy state report to {report_path}", flush=True)
    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
