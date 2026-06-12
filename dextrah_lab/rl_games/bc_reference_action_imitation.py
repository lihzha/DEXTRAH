"""Tiny supervised action-imitation diagnostic for Franka cube trajectory tracking.

This script is intentionally diagnostic-only.  It collects policy observations
from the trajectory-tracking task while stepping the existing reference_delta
controller, then overfits the loaded RL-Games actor to the reference actions.
The output checkpoint keeps the same 72-D observation / 7-D action
parameterization so it can be evaluated with ``eval_rollout.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Supervised reference-action imitation diagnostic.")
parser.add_argument("--num_envs", type=int, default=8, help="Number of environments used for reference rollout.")
parser.add_argument("--collection_steps", type=int, default=520, help="Number of reference rollout steps to collect.")
parser.add_argument("--train_steps", type=int, default=400, help="Number of supervised optimization steps.")
parser.add_argument("--batch_size", type=int, default=1024, help="Supervised minibatch size.")
parser.add_argument("--learning_rate", type=float, default=1.0e-4, help="Adam learning rate for the actor overfit.")
parser.add_argument("--weight_decay", type=float, default=0.0, help="AdamW-style weight decay for the actor overfit.")
parser.add_argument("--validation_fraction", type=float, default=0.20, help="Held-out dataset fraction.")
parser.add_argument(
    "--loss_dims",
    type=str,
    default="all",
    help="Action dimensions used in the supervised loss: 'all' or comma/colon/space-separated indices.",
)
parser.add_argument("--eval_interval", type=int, default=25, help="How often to log train/validation losses.")
parser.add_argument("--output_dir", type=str, default=None, help="Directory for BC diagnostic artifacts.")
parser.add_argument("--checkpoint", type=str, required=True, help="Input RL-Games checkpoint.")
parser.add_argument(
    "--bc_checkpoint_path",
    type=str,
    default=None,
    help="Path to write the BC-updated RL-Games checkpoint. Defaults under output_dir/nn.",
)
parser.add_argument("--dataset_path", type=str, default=None, help="Path to write the collected tensor dataset.")
parser.add_argument(
    "--rehearsal_dataset_paths",
    type=str,
    default="",
    help="Comma/colon-separated reference_action_dataset.pt files to concatenate with the fresh collection.",
)
parser.add_argument(
    "--rehearsal_dataset_names",
    type=str,
    default="",
    help="Optional comma/colon-separated source names matching --rehearsal_dataset_paths.",
)
parser.add_argument(
    "--source_batch_mode",
    choices=("random", "balanced"),
    default="random",
    help="Supervised batch sampling mode. 'balanced' draws from each dataset source every minibatch.",
)
parser.add_argument(
    "--source_loss_weights",
    type=str,
    default="",
    help="Optional comma-separated source weights, e.g. current_teacher_mix_alpha0p10=1,tm025_rehearsal=3.",
)
parser.add_argument(
    "--best_score_weights",
    type=str,
    default="",
    help=(
        "Optional comma-separated validation metric weights used to choose the saved checkpoint, "
        "e.g. val_source_current_teacher_mix_alpha0p10_l2=1,val_source_tm025_rehearsal_l2=3. "
        "Defaults to val_l2=1."
    ),
)
parser.add_argument(
    "--early_stop_patience",
    type=int,
    default=0,
    help="Stop after this many eval intervals without best-score improvement. 0 disables early stopping.",
)
parser.add_argument(
    "--distill_sources",
    type=str,
    default="",
    help=(
        "Optional comma/colon-separated source names/slugs/ids to regularize toward the frozen initial actor. "
        "Disabled when empty."
    ),
)
parser.add_argument(
    "--distill_loss_weight",
    type=float,
    default=0.0,
    help="MSE weight for frozen-initial-actor distillation on --distill_sources.",
)
parser.add_argument(
    "--distill_dims",
    type=str,
    default="",
    help="Action dimensions used for distillation. Defaults to --loss_dims when empty.",
)
parser.add_argument(
    "--residual_adapter_enabled",
    type=lambda value: str(value).strip().lower() in ("1", "true", "yes", "on"),
    default=False,
    help="Train a zero-initialized residual adapter on top of the frozen input actor instead of updating actor weights.",
)
parser.add_argument("--residual_hidden_dim", type=int, default=64, help="Hidden width for residual adapter; 0 uses linear.")
parser.add_argument(
    "--residual_max_action",
    type=float,
    default=0.5,
    help="Maximum absolute residual action before final action clipping.",
)
parser.add_argument(
    "--residual_preserve_sources",
    type=str,
    default="",
    help="Source names/slugs/ids where residual output is penalized toward zero.",
)
parser.add_argument(
    "--residual_preserve_weight",
    type=float,
    default=0.0,
    help="MSE weight for residual-to-zero preservation on --residual_preserve_sources.",
)
parser.add_argument(
    "--residual_l2_weight",
    type=float,
    default=0.0,
    help="Global residual magnitude MSE penalty.",
)
parser.add_argument(
    "--residual_gate_enabled",
    type=lambda value: str(value).strip().lower() in ("1", "true", "yes", "on"),
    default=False,
    help="Enable an observation-conditioned scalar gate multiplying the residual adapter output.",
)
parser.add_argument(
    "--residual_gate_hidden_dim",
    type=int,
    default=-1,
    help="Hidden width for residual gate; -1 reuses --residual_hidden_dim and 0 uses linear.",
)
parser.add_argument(
    "--residual_gate_bias_init",
    type=float,
    default=0.0,
    help="Initial bias for the residual gate sigmoid. 0.0 starts at gate=0.5.",
)
parser.add_argument(
    "--source_probe_steps",
    type=int,
    default=200,
    help="Tiny linear source-classifier probe steps for obs separability; 0 disables.",
)
parser.add_argument("--source_probe_lr", type=float, default=1.0e-2, help="Learning rate for the source probe.")
parser.add_argument("--seed", type=int, default=42, help="Random seed for env and supervised split.")
parser.add_argument(
    "--collection_action_source",
    choices=("reference_delta", "policy", "teacher_mix"),
    default="reference_delta",
    help=(
        "Action source used to step the rollout while collecting observations. "
        "Labels are always compute_reference_delta_actions()."
    ),
)
parser.add_argument(
    "--collection_teacher_alpha",
    type=float,
    default=0.5,
    help="Reference blend used when --collection_action_source=teacher_mix.",
)
parser.add_argument("--task", type=str, default=None, help="Gym task name.")
parser.add_argument("--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O.")
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

from rl_games.algos_torch import torch_ext
from rl_games.common import env_configurations, vecenv
from rl_games.common.player import BasePlayer
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config

import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401

from residual_action_adapter import ResidualActionAdapter


ACTION_LABELS = ("x", "y", "z", "rx", "ry", "rz", "gripper")


def _split_list(raw: str) -> list[str]:
    values: list[str] = []
    for token in raw.replace(":", ",").replace(";", ",").split(","):
        token = token.strip()
        if token:
            values.append(token)
    return values


def _source_slug(raw: str) -> str:
    chars = []
    for char in raw.lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_") or "source"


def _parse_float_map(raw: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    raw = raw.replace("__COMMA__", ",")
    if not raw.strip():
        return weights
    for token in raw.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Expected key=value in weight map entry: {token!r}")
        key, value = token.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty key in weight map entry: {token!r}")
        weight = float(value)
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError(f"Weight for {key!r} must be finite and non-negative, got {weight}")
        weights[key] = weight
    return weights


def _resolve_source_weights(raw: str, source_names: list[str], source_slugs: list[str]) -> list[float]:
    parsed = _parse_float_map(raw)
    if not parsed:
        return [1.0 for _ in source_slugs]
    source_keys: dict[str, int] = {}
    for idx, (name, slug) in enumerate(zip(source_names, source_slugs, strict=True)):
        source_keys[name] = idx
        source_keys[slug] = idx
        source_keys[str(idx)] = idx
    weights = [1.0 for _ in source_slugs]
    for key, value in parsed.items():
        if key not in source_keys:
            raise ValueError(f"Unknown source weight key {key!r}; valid keys include {sorted(source_keys)}")
        weights[source_keys[key]] = value
    return weights


def _resolve_source_ids(raw: str, source_names: list[str], source_slugs: list[str]) -> list[int]:
    values = _split_list(raw)
    if not values:
        return []
    if any(value in ("*", "all") for value in values):
        return list(range(len(source_slugs)))
    source_keys: dict[str, int] = {}
    for idx, (name, slug) in enumerate(zip(source_names, source_slugs, strict=True)):
        source_keys[name] = idx
        source_keys[slug] = idx
        source_keys[str(idx)] = idx
    source_ids: list[int] = []
    for value in values:
        if value not in source_keys:
            raise ValueError(f"Unknown source selector {value!r}; valid keys include {sorted(source_keys)}")
        source_id = source_keys[value]
        if source_id not in source_ids:
            source_ids.append(source_id)
    return source_ids


def _score_row(row: dict[str, float | int | str], weights: dict[str, float]) -> float:
    score = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        if key not in row:
            raise KeyError(f"Best-score metric {key!r} not found in row. Available keys include {sorted(row)[:20]}...")
        value = row[key]
        if not isinstance(value, (float, int)):
            raise TypeError(f"Best-score metric {key!r} must be numeric, got {type(value).__name__}")
        score += weight * float(value)
        total_weight += weight
    if total_weight <= 0.0:
        raise ValueError("--best_score_weights must include at least one positive weight")
    return score / total_weight


def _parse_loss_dims(raw: str, action_dim: int) -> list[int]:
    if raw.strip().lower() in ("all", "*"):
        return list(range(action_dim))
    dims: list[int] = []
    normalized = raw.replace(":", ",").replace(";", ",").replace(" ", ",")
    for token in normalized.split(","):
        token = token.strip()
        if not token:
            continue
        dim = int(token)
        if dim < 0 or dim >= action_dim:
            raise ValueError(f"loss dim {dim} outside action dimension {action_dim}")
        dims.append(dim)
    if not dims:
        raise ValueError("--loss_dims must include at least one dimension")
    return sorted(set(dims))


def _obs_tensor(agent: BasePlayer, obs) -> torch.Tensor:
    obs_t = agent.obs_to_torch(obs)
    if isinstance(obs_t, dict):
        if "obs" in obs_t:
            obs_t = obs_t["obs"]
        elif "policy" in obs_t:
            obs_t = obs_t["policy"]
        else:
            raise TypeError(f"Unsupported observation dict keys for BC diagnostic: {sorted(obs_t.keys())}")
    if not isinstance(obs_t, torch.Tensor):
        obs_t = torch.as_tensor(obs_t, device=agent.device, dtype=torch.float32)
    return obs_t.detach().float()


def _model_mus(model: torch.nn.Module, obs_batch: torch.Tensor, action_dim: int, *, is_train: bool) -> torch.Tensor:
    prev_actions = torch.zeros(obs_batch.shape[0], action_dim, dtype=obs_batch.dtype, device=obs_batch.device)
    batch = {
        "is_train": is_train,
        "obs": obs_batch,
        "prev_actions": prev_actions,
    }
    output = model(batch)
    if "mus" not in output:
        raise KeyError(f"RL-Games model output lacks 'mus'; keys={sorted(output.keys())}")
    return output["mus"]


def _reference_delta_actions(task_env) -> torch.Tensor:
    if not hasattr(task_env, "compute_reference_delta_actions"):
        raise ValueError("BC diagnostic requires trajectory task env.compute_reference_delta_actions().")
    return task_env.compute_reference_delta_actions().detach().clamp(-1.0, 1.0)


def _mean_float(tensor: torch.Tensor) -> float:
    return float(tensor.detach().float().mean().cpu())


def _action_stats(actions: torch.Tensor, prefix: str) -> dict[str, float]:
    out: dict[str, float] = {}
    actions = actions.detach().float()
    for dim in range(min(actions.shape[-1], len(ACTION_LABELS))):
        out[f"{prefix}_{ACTION_LABELS[dim]}_mean"] = _mean_float(actions[:, dim])
        out[f"{prefix}_{ACTION_LABELS[dim]}_std"] = float(actions[:, dim].std(unbiased=False).cpu())
    if actions.shape[-1] >= 3:
        out[f"{prefix}_up_mean"] = _mean_float(torch.clamp(actions[:, 2], 0.0, 1.0))
    if actions.shape[-1] >= 7:
        out[f"{prefix}_close_mean"] = _mean_float(torch.clamp(-actions[:, 6], 0.0, 1.0))
    return out


def _error_stats(pred: torch.Tensor, target: torch.Tensor, dims: list[int], prefix: str) -> dict[str, float]:
    pred = pred.detach().float()
    target = target.detach().float()
    delta = pred[:, dims] - target[:, dims]
    out = {
        f"{prefix}_mse": _mean_float(torch.mean(torch.square(delta), dim=-1)),
        f"{prefix}_l2": _mean_float(torch.norm(delta, dim=-1)),
    }
    labels = [ACTION_LABELS[dim] if dim < len(ACTION_LABELS) else f"dim{dim}" for dim in dims]
    for local_idx, label in enumerate(labels):
        out[f"{prefix}_{label}_abs"] = _mean_float(torch.abs(delta[:, local_idx]))
    if 2 in dims:
        out[f"{prefix}_up_abs"] = _mean_float(
            torch.abs(torch.clamp(pred[:, 2], 0.0, 1.0) - torch.clamp(target[:, 2], 0.0, 1.0))
        )
    if 6 in dims:
        out[f"{prefix}_close_abs"] = _mean_float(
            torch.abs(torch.clamp(-pred[:, 6], 0.0, 1.0) - torch.clamp(-target[:, 6], 0.0, 1.0))
        )
        out[f"{prefix}_gripper_abs"] = _mean_float(torch.abs(pred[:, 6] - target[:, 6]))
    return out


def _quantile_float(values: torch.Tensor, q: float) -> float:
    values = values.detach().float().reshape(-1)
    values = values[torch.isfinite(values)]
    if int(values.numel()) == 0:
        return float("nan")
    return float(torch.quantile(values, float(q), interpolation="linear").cpu())


def _source_subset(values: torch.Tensor, source_ids: torch.Tensor, source_id: int, indices: torch.Tensor) -> torch.Tensor:
    local_source_ids = source_ids[indices]
    mask = local_source_ids == int(source_id)
    if not bool(mask.any()):
        return values[indices][:0]
    return values[indices][mask]


def _oracle_residual_stats(
    *,
    base_actions: torch.Tensor,
    target_actions: torch.Tensor,
    source_ids: torch.Tensor,
    train_idx: torch.Tensor,
    val_idx: torch.Tensor,
    source_names: list[str],
    source_slugs: list[str],
    dims: list[int],
    residual_max_action: float,
) -> dict[str, object]:
    oracle = target_actions.detach().float() - base_actions.detach().float()
    max_action = float(residual_max_action)
    clipped_oracle = torch.clamp(oracle, -max_action, max_action) if max_action >= 0.0 else oracle
    clipped_pred = torch.clamp(base_actions.detach().float() + clipped_oracle, -1.0, 1.0)
    dims_t = torch.tensor(dims, dtype=torch.long, device=oracle.device)
    split_indices = {"train": train_idx, "val": val_idx}
    source_rows: list[dict[str, object]] = []
    dim_rows: list[dict[str, object]] = []
    for source_id, (source_name, source_slug) in enumerate(zip(source_names, source_slugs, strict=True)):
        for split, indices in split_indices.items():
            residual_subset = _source_subset(oracle, source_ids, source_id, indices)
            base_subset = _source_subset(base_actions, source_ids, source_id, indices)
            target_subset = _source_subset(target_actions, source_ids, source_id, indices)
            clipped_pred_subset = _source_subset(clipped_pred, source_ids, source_id, indices)
            if int(residual_subset.numel()) == 0:
                continue
            residual_dims = residual_subset[:, dims_t]
            abs_residual_dims = torch.abs(residual_dims)
            residual_l2 = torch.norm(residual_dims, dim=-1)
            clipped_error_l2 = torch.norm(
                clipped_pred_subset[:, dims_t] - target_subset[:, dims_t],
                dim=-1,
            )
            source_rows.append(
                {
                    "source": source_name,
                    "slug": source_slug,
                    "split": split,
                    "count": int(residual_subset.shape[0]),
                    "oracle_l2_mean": _mean_float(residual_l2),
                    "oracle_l2_p50": _quantile_float(residual_l2, 0.50),
                    "oracle_l2_p75": _quantile_float(residual_l2, 0.75),
                    "oracle_l2_p90": _quantile_float(residual_l2, 0.90),
                    "oracle_l2_p95": _quantile_float(residual_l2, 0.95),
                    "oracle_l2_p99": _quantile_float(residual_l2, 0.99),
                    "oracle_l2_max": float(torch.max(residual_l2).detach().cpu()),
                    "oracle_abs_mean": _mean_float(abs_residual_dims),
                    "clip_dim_rate": _mean_float((abs_residual_dims > max_action).float()) if max_action >= 0.0 else 0.0,
                    "clip_sample_rate": _mean_float((torch.max(abs_residual_dims, dim=-1).values > max_action).float())
                    if max_action >= 0.0
                    else 0.0,
                    "clipped_achievable_l2_mean": _mean_float(clipped_error_l2),
                    "base_l2_mean": _mean_float(torch.norm(base_subset[:, dims_t] - target_subset[:, dims_t], dim=-1)),
                    "residual_max_action": max_action,
                }
            )
            for dim in dims:
                label = ACTION_LABELS[dim] if dim < len(ACTION_LABELS) else f"dim{dim}"
                values = residual_subset[:, dim]
                abs_values = torch.abs(values)
                dim_rows.append(
                    {
                        "source": source_name,
                        "slug": source_slug,
                        "split": split,
                        "dim": int(dim),
                        "label": label,
                        "count": int(values.shape[0]),
                        "mean": _mean_float(values),
                        "std": float(values.std(unbiased=False).detach().cpu()),
                        "abs_mean": _mean_float(abs_values),
                        "abs_p50": _quantile_float(abs_values, 0.50),
                        "abs_p75": _quantile_float(abs_values, 0.75),
                        "abs_p90": _quantile_float(abs_values, 0.90),
                        "abs_p95": _quantile_float(abs_values, 0.95),
                        "abs_p99": _quantile_float(abs_values, 0.99),
                        "abs_max": float(torch.max(abs_values).detach().cpu()),
                        "clip_rate": _mean_float((abs_values > max_action).float()) if max_action >= 0.0 else 0.0,
                    }
                )
    return {
        "definition": "reference_action - frozen_base_action",
        "residual_max_action": max_action,
        "source_rows": source_rows,
        "dim_rows": dim_rows,
    }


def _run_source_probe(
    *,
    obs: torch.Tensor,
    source_ids: torch.Tensor,
    train_idx: torch.Tensor,
    val_idx: torch.Tensor,
    num_sources: int,
    steps: int,
    learning_rate: float,
    batch_size: int,
    generator: torch.Generator,
) -> dict[str, object]:
    if steps <= 0 or num_sources < 2:
        return {"enabled": False, "reason": "disabled_or_single_source"}
    probe = torch.nn.Linear(obs.shape[-1], num_sources, device=obs.device)
    optimizer = torch.optim.AdamW(probe.parameters(), lr=float(learning_rate))
    train_batch_size = max(1, min(int(batch_size), int(train_idx.numel())))
    for _ in range(int(steps)):
        choice = train_idx[torch.randint(0, int(train_idx.numel()), (train_batch_size,), generator=generator, device=obs.device)]
        logits = probe(obs[choice].detach())
        loss = torch.nn.functional.cross_entropy(logits, source_ids[choice].long())
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        train_logits = probe(obs[train_idx].detach())
        val_logits = probe(obs[val_idx].detach())
        train_pred = torch.argmax(train_logits, dim=-1)
        val_pred = torch.argmax(val_logits, dim=-1)
        train_target = source_ids[train_idx].long()
        val_target = source_ids[val_idx].long()
        train_counts = torch.bincount(train_target, minlength=num_sources).float()
        val_counts = torch.bincount(val_target, minlength=num_sources).float()
        train_baseline = float((torch.max(train_counts) / train_counts.sum().clamp_min(1.0)).detach().cpu())
        val_baseline = float((torch.max(val_counts) / val_counts.sum().clamp_min(1.0)).detach().cpu())
        train_accuracy = _mean_float((train_pred == train_target).float())
        val_accuracy = _mean_float((val_pred == val_target).float())
        train_loss = float(torch.nn.functional.cross_entropy(train_logits, train_target).detach().cpu())
        val_loss = float(torch.nn.functional.cross_entropy(val_logits, val_target).detach().cpu())
    return {
        "enabled": True,
        "steps": int(steps),
        "learning_rate": float(learning_rate),
        "train_accuracy": train_accuracy,
        "val_accuracy": val_accuracy,
        "train_baseline_accuracy": train_baseline,
        "val_baseline_accuracy": val_baseline,
        "train_loss": train_loss,
        "val_loss": val_loss,
        "num_sources": int(num_sources),
    }


def _write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _draw_loss_plot(rows: list[dict[str, float | int | str]], path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1320, 780
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 12)
    except Exception:
        font_title = font = font_small = None
    draw.text((42, 26), "Reference Action BC Diagnostic", fill=(20, 20, 20), font=font_title)
    panels = [
        ("MSE", "train_mse", "val_mse", 0, 92, 620, 342),
        ("L2", "train_l2", "val_l2", 700, 92, 1278, 342),
        ("Up abs error", "train_up_abs", "val_up_abs", 0, 432, 620, 682),
        ("Close abs error", "train_close_abs", "val_close_abs", 700, 432, 1278, 682),
    ]
    for title, train_key, val_key, x0, y0, x1, y1 in panels:
        x0 += 42
        x1 += 0
        draw.rectangle((x0, y0, x1, y1), outline=(220, 220, 220), width=1)
        draw.text((x0, y0 - 24), title, fill=(20, 20, 20), font=font)
        values = []
        for row in rows:
            for key in (train_key, val_key):
                value = row.get(key)
                if isinstance(value, (float, int)):
                    values.append(float(value))
        max_value = max(values) if values else 1.0
        max_value = max(max_value, 1.0e-6)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y1 - frac * (y1 - y0)
            draw.line((x0, y, x1, y), fill=(240, 240, 240), width=1)
        for key, label, color in (
            (train_key, "train", (210, 95, 45)),
            (val_key, "val", (45, 120, 195)),
        ):
            points = []
            for idx, row in enumerate(rows):
                value = row.get(key)
                if not isinstance(value, (float, int)):
                    continue
                x = x0 + idx * (x1 - x0) / max(len(rows) - 1, 1)
                y = y1 - max(0.0, min(1.0, float(value) / max_value)) * (y1 - y0)
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=color, width=3)
            draw.rectangle((x0 + 8 + (0 if label == "train" else 82), y0 + 8, x0 + 22 + (0 if label == "train" else 82), y0 + 22), fill=color)
            draw.text((x0 + 28 + (0 if label == "train" else 82), y0 + 5), label, fill=(35, 35, 35), font=font_small)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _draw_source_metric_plot(rows: list[dict[str, float | int | str]], path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1320, 720
    margin_left, margin_right = 96, 42
    margin_top, margin_bottom = 92, 96
    plot_x0, plot_y0 = margin_left, margin_top
    plot_x1, plot_y1 = width - margin_right, height - margin_bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 12)
    except Exception:
        font_title = font = font_small = None
    draw.text((42, 26), "BC Source Validation Metrics", fill=(20, 20, 20), font=font_title)

    all_keys = sorted({key for row in rows for key in row})
    metric_keys = ["val_l2", "selection_score"]
    metric_keys.extend(
        key
        for key in all_keys
        if (key.startswith("val_source_") and key.endswith("_l2"))
        or (key.startswith("val_distill_source_") and key.endswith("_l2"))
        or (key.startswith("val_residual_source_") and key.endswith("_l2"))
        or (key.startswith("val_preserve_source_") and key.endswith("_l2"))
        or (key.startswith("val_gate_source_") and key.endswith("_mean"))
    )
    metric_keys = [key for idx, key in enumerate(metric_keys) if key in all_keys and key not in metric_keys[:idx]]
    if not metric_keys:
        metric_keys = ["val_l2"] if "val_l2" in all_keys else []

    values = [
        float(row[key])
        for row in rows
        for key in metric_keys
        if isinstance(row.get(key), (float, int))
    ]
    max_value = max(values) if values else 1.0
    max_value = max(max_value, 1.0e-6)
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = plot_y1 - frac * (plot_y1 - plot_y0)
        draw.line((plot_x0, y, plot_x1, y), fill=(235, 235, 235), width=1)
        draw.text((34, y - 8), f"{frac * max_value:.3f}", fill=(80, 80, 80), font=font_small)
    draw.rectangle((plot_x0, plot_y0, plot_x1, plot_y1), outline=(205, 205, 205), width=1)

    palette = [
        (45, 120, 195),
        (210, 95, 45),
        (60, 155, 105),
        (145, 95, 180),
        (205, 145, 45),
        (65, 155, 170),
        (180, 70, 115),
        (110, 110, 110),
    ]
    legend_x, legend_y = plot_x0, plot_y1 + 22
    for idx, key in enumerate(metric_keys[:8]):
        color = palette[idx % len(palette)]
        points = []
        for row_idx, row in enumerate(rows):
            value = row.get(key)
            if not isinstance(value, (float, int)):
                continue
            x = plot_x0 + row_idx * (plot_x1 - plot_x0) / max(len(rows) - 1, 1)
            y = plot_y1 - max(0.0, min(1.0, float(value) / max_value)) * (plot_y1 - plot_y0)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        elif len(points) == 1:
            x, y = points[0]
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
        lx = legend_x + (idx % 4) * 300
        ly = legend_y + (idx // 4) * 24
        draw.rectangle((lx, ly, lx + 14, ly + 14), fill=color)
        draw.text((lx + 20, ly - 2), key[:38], fill=(35, 35, 35), font=font_small)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _draw_oracle_residual_plot(oracle_stats: dict[str, object], path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    dim_rows = oracle_stats.get("dim_rows", [])
    source_rows = oracle_stats.get("source_rows", [])
    if not isinstance(dim_rows, list):
        dim_rows = []
    if not isinstance(source_rows, list):
        source_rows = []
    val_dim_rows = [row for row in dim_rows if isinstance(row, dict) and row.get("split") == "val"]
    val_source_rows = [row for row in source_rows if isinstance(row, dict) and row.get("split") == "val"]

    width, height = 1320, 780
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 11)
    except Exception:
        font_title = font = font_small = None

    draw.text((42, 26), "Oracle Required Residuals (validation split)", fill=(20, 20, 20), font=font_title)
    max_action = float(oracle_stats.get("residual_max_action", 0.0) or 0.0)
    labels = [ACTION_LABELS[idx] if idx < len(ACTION_LABELS) else f"dim{idx}" for idx in range(7)]
    sources = []
    for row in val_dim_rows:
        source = row.get("source")
        if isinstance(source, str) and source not in sources:
            sources.append(source)
    palette = [(45, 120, 195), (210, 95, 45), (60, 155, 105), (145, 95, 180)]
    x0, y0, x1, y1 = 72, 108, 1264, 438
    draw.rectangle((x0, y0, x1, y1), outline=(210, 210, 210), width=1)
    max_value = max(
        [float(row.get("abs_p95", 0.0) or 0.0) for row in val_dim_rows] + [max_action, 1.0e-6]
    )
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y1 - frac * (y1 - y0)
        draw.line((x0, y, x1, y), fill=(238, 238, 238), width=1)
        draw.text((24, y - 8), f"{frac * max_value:.2f}", fill=(80, 80, 80), font=font_small)
    if max_action > 0:
        y = y1 - min(1.0, max_action / max_value) * (y1 - y0)
        draw.line((x0, y, x1, y), fill=(200, 35, 35), width=2)
        draw.text((x1 - 150, y - 18), f"max={max_action:.2f}", fill=(160, 35, 35), font=font_small)
    group_width = (x1 - x0) / max(len(labels), 1)
    bar_width = group_width / max(len(sources) + 1, 2)
    for dim, label in enumerate(labels):
        cx = x0 + dim * group_width
        draw.text((cx + 8, y1 + 8), label, fill=(35, 35, 35), font=font_small)
        for source_idx, source in enumerate(sources):
            row = next(
                (
                    item
                    for item in val_dim_rows
                    if isinstance(item, dict) and item.get("source") == source and int(item.get("dim", -1)) == dim
                ),
                None,
            )
            if row is None:
                continue
            value = float(row.get("abs_p95", 0.0) or 0.0)
            bx0 = cx + 8 + source_idx * bar_width
            bx1 = bx0 + max(4, bar_width - 4)
            by0 = y1 - min(1.0, value / max_value) * (y1 - y0)
            draw.rectangle((bx0, by0, bx1, y1), fill=palette[source_idx % len(palette)])
    for idx, source in enumerate(sources[:4]):
        lx = x0 + idx * 280
        ly = y1 + 42
        draw.rectangle((lx, ly, lx + 14, ly + 14), fill=palette[idx % len(palette)])
        draw.text((lx + 20, ly - 2), f"{source[:28]} p95 abs", fill=(35, 35, 35), font=font_small)

    table_y = 528
    draw.text((72, table_y - 32), "Validation source summary", fill=(20, 20, 20), font=font)
    header = "source                         l2_mean  l2_p95  clip_dim  clip_sample  clipped_l2"
    draw.text((72, table_y), header, fill=(45, 45, 45), font=font_small)
    for row_idx, row in enumerate(val_source_rows[:8]):
        y = table_y + 24 + row_idx * 24
        source = str(row.get("source", "n/a"))[:28]
        text = (
            f"{source:<28} "
            f"{float(row.get('oracle_l2_mean', float('nan'))):>7.3f} "
            f"{float(row.get('oracle_l2_p95', float('nan'))):>7.3f} "
            f"{float(row.get('clip_dim_rate', float('nan'))):>8.3f} "
            f"{float(row.get('clip_sample_rate', float('nan'))):>11.3f} "
            f"{float(row.get('clipped_achievable_l2_mean', float('nan'))):>10.3f}"
        )
        draw.text((72, y), text, fill=(35, 35, 35), font=font_small)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _write_report(summary: dict[str, object], rows: list[dict[str, float | int | str]], path: Path) -> None:
    first = rows[0] if rows else {}
    last = rows[-1] if rows else {}
    selected = summary.get("selected", last)
    if not isinstance(selected, dict):
        selected = last
    source_rows = summary.get("dataset_sources", [])
    source_lines = [
        "| source | samples | collection action | teacher alpha | source path |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    if isinstance(source_rows, list):
        for source in source_rows:
            if isinstance(source, dict):
                source_lines.append(
                    "| {name} | {samples} | {action_source} | {teacher_alpha} | `{path}` |".format(
                        name=source.get("name", "n/a"),
                        samples=source.get("num_samples", "n/a"),
                        action_source=source.get("collection_action_source", "n/a"),
                        teacher_alpha=source.get("collection_teacher_alpha", "n/a"),
                        path=source.get("path", "n/a"),
                    )
                )
    source_metric_lines = [
        "| source | split | initial mse | final mse | initial l2 | final l2 | initial up abs | final up abs | initial close abs | final close abs |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    distill_metric_lines = [
        "| source | split | initial distill mse | final distill mse | initial distill l2 | final distill l2 | initial up abs | final up abs | initial close abs | final close abs |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    base_metric_lines = [
        "| source | split | base mse | base l2 | base up abs | base close abs |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    residual_metric_lines = [
        "| source | split | initial residual l2 | final residual l2 | initial preserve l2 | final preserve l2 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    gate_metric_lines = [
        "| source | split | initial gate mean | final gate mean | initial gate min | final gate min | initial gate max | final gate max |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    oracle_stats = summary.get("oracle_residual_stats", {})
    oracle_source_lines = [
        "| source | split | count | oracle L2 mean | L2 p95 | L2 p99 | clip dim rate | clip sample rate | clipped achievable L2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    oracle_dim_lines = [
        "| source | split | dim | abs mean | abs p50 | abs p90 | abs p95 | abs p99 | abs max | clip rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(oracle_stats, dict):
        oracle_source_rows = oracle_stats.get("source_rows", [])
        if isinstance(oracle_source_rows, list):
            for row in oracle_source_rows:
                if not isinstance(row, dict):
                    continue
                oracle_source_lines.append(
                    f"| {row.get('source', 'n/a')} | {row.get('split', 'n/a')} | {row.get('count', 'n/a')} | "
                    f"{row.get('oracle_l2_mean', 'n/a')} | {row.get('oracle_l2_p95', 'n/a')} | "
                    f"{row.get('oracle_l2_p99', 'n/a')} | {row.get('clip_dim_rate', 'n/a')} | "
                    f"{row.get('clip_sample_rate', 'n/a')} | {row.get('clipped_achievable_l2_mean', 'n/a')} |"
                )
        dim_rows = oracle_stats.get("dim_rows", [])
        if isinstance(dim_rows, list):
            for row in dim_rows:
                if not isinstance(row, dict):
                    continue
                oracle_dim_lines.append(
                    f"| {row.get('source', 'n/a')} | {row.get('split', 'n/a')} | {row.get('label', row.get('dim', 'n/a'))} | "
                    f"{row.get('abs_mean', 'n/a')} | {row.get('abs_p50', 'n/a')} | {row.get('abs_p90', 'n/a')} | "
                    f"{row.get('abs_p95', 'n/a')} | {row.get('abs_p99', 'n/a')} | {row.get('abs_max', 'n/a')} | "
                    f"{row.get('clip_rate', 'n/a')} |"
                )
    source_probe = summary.get("source_probe", {})
    if isinstance(source_probe, dict) and source_probe.get("enabled"):
        source_probe_lines = [
            "| probe | steps | train acc | val acc | train baseline | val baseline | train loss | val loss |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            (
                f"| linear obs source classifier | {source_probe.get('steps', 'n/a')} | "
                f"{source_probe.get('train_accuracy', 'n/a')} | {source_probe.get('val_accuracy', 'n/a')} | "
                f"{source_probe.get('train_baseline_accuracy', 'n/a')} | {source_probe.get('val_baseline_accuracy', 'n/a')} | "
                f"{source_probe.get('train_loss', 'n/a')} | {source_probe.get('val_loss', 'n/a')} |"
            ),
        ]
    else:
        source_probe_lines = [f"- source probe: `{source_probe}`"]
    if isinstance(source_rows, list):
        for source in source_rows:
            if not isinstance(source, dict):
                continue
            slug = source.get("slug")
            name = source.get("name", "n/a")
            if not isinstance(slug, str):
                continue
            for split in ("train", "val"):
                prefix = f"{split}_source_{slug}"
                source_metric_lines.append(
                    f"| {name} | {split} | "
                    f"{first.get(prefix + '_mse', 'n/a')} | {last.get(prefix + '_mse', 'n/a')} | "
                    f"{first.get(prefix + '_l2', 'n/a')} | {last.get(prefix + '_l2', 'n/a')} | "
                    f"{first.get(prefix + '_up_abs', 'n/a')} | {last.get(prefix + '_up_abs', 'n/a')} | "
                    f"{first.get(prefix + '_close_abs', 'n/a')} | {last.get(prefix + '_close_abs', 'n/a')} |"
                )
                distill_prefix = f"{split}_distill_source_{slug}"
                if distill_prefix + "_mse" in first or distill_prefix + "_mse" in last:
                    distill_metric_lines.append(
                        f"| {name} | {split} | "
                        f"{first.get(distill_prefix + '_mse', 'n/a')} | {last.get(distill_prefix + '_mse', 'n/a')} | "
                        f"{first.get(distill_prefix + '_l2', 'n/a')} | {last.get(distill_prefix + '_l2', 'n/a')} | "
                        f"{first.get(distill_prefix + '_up_abs', 'n/a')} | {last.get(distill_prefix + '_up_abs', 'n/a')} | "
                        f"{first.get(distill_prefix + '_close_abs', 'n/a')} | {last.get(distill_prefix + '_close_abs', 'n/a')} |"
                    )
                base_prefix = f"{split}_base_source_{slug}"
                if base_prefix + "_mse" in last:
                    base_metric_lines.append(
                        f"| {name} | {split} | "
                        f"{last.get(base_prefix + '_mse', 'n/a')} | {last.get(base_prefix + '_l2', 'n/a')} | "
                        f"{last.get(base_prefix + '_up_abs', 'n/a')} | {last.get(base_prefix + '_close_abs', 'n/a')} |"
                    )
                residual_prefix = f"{split}_residual_source_{slug}"
                preserve_prefix = f"{split}_preserve_source_{slug}"
                if residual_prefix + "_l2" in first or residual_prefix + "_l2" in last:
                    residual_metric_lines.append(
                        f"| {name} | {split} | "
                        f"{first.get(residual_prefix + '_l2', 'n/a')} | {last.get(residual_prefix + '_l2', 'n/a')} | "
                        f"{first.get(preserve_prefix + '_l2', 'n/a')} | {last.get(preserve_prefix + '_l2', 'n/a')} |"
                    )
                gate_prefix = f"{split}_gate_source_{slug}"
                if gate_prefix + "_mean" in first or gate_prefix + "_mean" in last:
                    gate_metric_lines.append(
                        f"| {name} | {split} | "
                        f"{first.get(gate_prefix + '_mean', 'n/a')} | {last.get(gate_prefix + '_mean', 'n/a')} | "
                        f"{first.get(gate_prefix + '_min', 'n/a')} | {last.get(gate_prefix + '_min', 'n/a')} | "
                        f"{first.get(gate_prefix + '_max', 'n/a')} | {last.get(gate_prefix + '_max', 'n/a')} |"
                    )
    if "train_distill_mse" in first or "val_distill_mse" in first:
        distill_metric_lines.extend(
            [
                "",
                "| aggregate | split | initial distill mse | final distill mse | initial distill l2 | final distill l2 | initial up abs | final up abs | initial close abs | final close abs |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                (
                    f"| selected sources | train | {first.get('train_distill_mse', 'n/a')} | {last.get('train_distill_mse', 'n/a')} | "
                    f"{first.get('train_distill_l2', 'n/a')} | {last.get('train_distill_l2', 'n/a')} | "
                    f"{first.get('train_distill_up_abs', 'n/a')} | {last.get('train_distill_up_abs', 'n/a')} | "
                    f"{first.get('train_distill_close_abs', 'n/a')} | {last.get('train_distill_close_abs', 'n/a')} |"
                ),
                (
                    f"| selected sources | val | {first.get('val_distill_mse', 'n/a')} | {last.get('val_distill_mse', 'n/a')} | "
                    f"{first.get('val_distill_l2', 'n/a')} | {last.get('val_distill_l2', 'n/a')} | "
                    f"{first.get('val_distill_up_abs', 'n/a')} | {last.get('val_distill_up_abs', 'n/a')} | "
                    f"{first.get('val_distill_close_abs', 'n/a')} | {last.get('val_distill_close_abs', 'n/a')} |"
                ),
            ]
        )
    lines = [
        "# Reference Action BC Diagnostic",
        "",
        "This is a bounded supervised action-imitation diagnostic, not PPO scale-up.",
        "",
        "## Setup",
        "",
        f"- task: `{summary.get('task')}`",
        f"- input checkpoint: `{summary.get('input_checkpoint')}`",
        f"- output checkpoint: `{summary.get('output_checkpoint')}`",
        f"- collection action source: `{summary.get('collection_action_source')}`",
        f"- collection teacher alpha: `{summary.get('collection_teacher_alpha')}`",
        f"- samples: `{summary.get('num_samples')}` total / `{summary.get('num_train')}` train / `{summary.get('num_val')}` held-out",
        f"- observation dim: `{summary.get('obs_dim')}`, action dim: `{summary.get('action_dim')}`",
        f"- loss dims: `{summary.get('loss_dims')}`",
        f"- source batch mode: `{summary.get('source_batch_mode')}`",
        f"- source loss weights: `{summary.get('source_loss_weights')}`",
        f"- best score weights: `{summary.get('best_score_weights')}`",
        f"- distillation target: `{summary.get('distill_target')}`",
        f"- distillation sources: `{summary.get('distill_sources')}`",
        f"- distillation dims: `{summary.get('distill_dims')}`",
        f"- distillation loss weight: `{summary.get('distill_loss_weight')}`",
        f"- residual adapter enabled: `{summary.get('residual_adapter_enabled')}`",
        f"- residual hidden dim / max action: `{summary.get('residual_hidden_dim')}` / `{summary.get('residual_max_action')}`",
        f"- residual gate enabled / hidden dim / bias init: `{summary.get('residual_gate_enabled')}` / `{summary.get('residual_gate_hidden_dim')}` / `{summary.get('residual_gate_bias_init')}`",
        f"- residual preserve sources: `{summary.get('residual_preserve_sources')}`",
        f"- residual preserve/l2 weights: `{summary.get('residual_preserve_weight')}` / `{summary.get('residual_l2_weight')}`",
        f"- selected step/score: `{summary.get('selected_step')}` / `{summary.get('selected_score')}`",
        f"- early stop triggered: `{summary.get('early_stop_triggered')}`",
        f"- reference caveat: `curobo_validated={summary.get('curobo_validated')}`",
        "",
        "## Dataset Sources",
        "",
        *source_lines,
        "",
        "## Loss",
        "",
        "| split | initial mse | final mse | initial l2 | final l2 | initial up abs | final up abs | initial close abs | final close abs |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| train | {first.get('train_mse', 'n/a')} | {last.get('train_mse', 'n/a')} | "
            f"{first.get('train_l2', 'n/a')} | {last.get('train_l2', 'n/a')} | "
            f"{first.get('train_up_abs', 'n/a')} | {last.get('train_up_abs', 'n/a')} | "
            f"{first.get('train_close_abs', 'n/a')} | {last.get('train_close_abs', 'n/a')} |"
        ),
        (
            f"| val | {first.get('val_mse', 'n/a')} | {last.get('val_mse', 'n/a')} | "
            f"{first.get('val_l2', 'n/a')} | {last.get('val_l2', 'n/a')} | "
            f"{first.get('val_up_abs', 'n/a')} | {last.get('val_up_abs', 'n/a')} | "
            f"{first.get('val_close_abs', 'n/a')} | {last.get('val_close_abs', 'n/a')} |"
        ),
        "",
        "## Selected Checkpoint",
        "",
        "| split | selected mse | selected l2 | selected up abs | selected close abs |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| train | {selected.get('train_mse', 'n/a')} | {selected.get('train_l2', 'n/a')} | "
            f"{selected.get('train_up_abs', 'n/a')} | {selected.get('train_close_abs', 'n/a')} |"
        ),
        (
            f"| val | {selected.get('val_mse', 'n/a')} | {selected.get('val_l2', 'n/a')} | "
            f"{selected.get('val_up_abs', 'n/a')} | {selected.get('val_close_abs', 'n/a')} |"
        ),
        "",
        "## Per-Source Loss",
        "",
        *source_metric_lines,
        "",
        "## Distillation Metrics",
        "",
        *distill_metric_lines,
        "",
        "## Residual Adapter Metrics",
        "",
        "Base metrics are the frozen input actor against reference labels. Residual metrics are final-minus-base action magnitude; preserve metrics are final action error to the frozen base on preservation sources.",
        "",
        "### Frozen Base Label Error",
        "",
        *base_metric_lines,
        "",
        "### Residual Magnitude / Base Preservation",
        "",
        *residual_metric_lines,
        "",
        "### Residual Gate",
        "",
        *gate_metric_lines,
        "",
        "## Oracle Required Residuals",
        "",
        "Oracle residual is `reference_action - frozen_base_action` before residual clipping. The clipped-achievable L2 column shows the remaining label error if only `RESIDUAL_MAX_ACTION` clipping limited the oracle residual.",
        "",
        "### Source Summary",
        "",
        *oracle_source_lines,
        "",
        "### Per-Dimension Absolute Residual Percentiles",
        "",
        *oracle_dim_lines,
        "",
        "## Source Separability Probe",
        "",
        *source_probe_lines,
        "",
        "## Artifacts",
        "",
        f"- metrics: `{summary.get('metrics_path')}`",
        f"- curve CSV: `{summary.get('curve_csv_path')}`",
        f"- plot: `{summary.get('plot_path')}`",
        f"- source metric plot: `{summary.get('source_plot_path')}`",
        f"- oracle residual plot: `{summary.get('oracle_plot_path')}`",
        f"- oracle source CSV: `{summary.get('oracle_source_csv_path')}`",
        f"- oracle dim CSV: `{summary.get('oracle_dim_csv_path')}`",
        f"- dataset: `{summary.get('dataset_path')}`",
        "",
        "Next acceptance is not this loss alone: evaluate selector alphas `0.0`, `0.25`, `0.5`, `0.75`, and `1.0` with metrics first, then videos/action-semantics plots only if selector behavior improves.",
    ]
    path.write_text("\n".join(lines) + "\n")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    random.seed(args_cli.seed)
    torch.manual_seed(args_cli.seed)

    output_dir = Path(args_cli.output_dir or datetime.now().strftime("bc_ref_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args_cli.dataset_path).expanduser().resolve() if args_cli.dataset_path else output_dir / "reference_action_dataset.pt"
    checkpoint_out = (
        Path(args_cli.bc_checkpoint_path).expanduser().resolve()
        if args_cli.bc_checkpoint_path
        else output_dir / "nn" / "bc_reference_action_imitation.pth"
    )
    checkpoint_out.parent.mkdir(parents=True, exist_ok=True)
    curve_csv_path = output_dir / "bc_loss_curve.csv"
    metrics_path = output_dir / "bc_metrics.json"
    plot_path = output_dir / "bc_loss_plot.png"
    source_plot_path = output_dir / "bc_source_metric_plot.png"
    oracle_plot_path = output_dir / "oracle_residual_plot.png"
    oracle_source_csv_path = output_dir / "oracle_residual_source.csv"
    oracle_dim_csv_path = output_dir / "oracle_residual_dim.csv"
    report_path = output_dir / "report.md"

    env_cfg.scene.num_envs = args_cli.num_envs if args_cli.num_envs is not None else env_cfg.scene.num_envs
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = args_cli.seed
    agent_cfg["params"]["seed"] = args_cli.seed

    resume_path = retrieve_file_path(args_cli.checkpoint)
    agent_cfg["params"]["load_checkpoint"] = True
    agent_cfg["params"]["load_path"] = resume_path

    gym_env = gym.make(args_cli.task, cfg=env_cfg)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)
    env = RlGamesVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register("IsaacRlgWrapper", lambda config_name, num_actors, **kwargs: RlGamesGpuEnv(config_name, num_actors, **kwargs))
    env_configurations.register("rlgpu", {"vecenv_type": "IsaacRlgWrapper", "env_creator": lambda **kwargs: env})

    agent_cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    runner = Runner()
    runner.load(agent_cfg)
    agent = runner.create_player()
    agent.restore(resume_path)
    agent.reset()
    if agent.is_rnn:
        raise NotImplementedError("BC reference-action diagnostic currently supports feed-forward policies only.")

    action_dim = int(getattr(task_env.cfg, "action_space", 0))
    loss_dims = _parse_loss_dims(args_cli.loss_dims, action_dim)
    collection_teacher_alpha = min(max(float(args_cli.collection_teacher_alpha), 0.0), 1.0)
    rehearsal_paths = _split_list(args_cli.rehearsal_dataset_paths)
    rehearsal_names = _split_list(args_cli.rehearsal_dataset_names)
    if rehearsal_names and len(rehearsal_names) != len(rehearsal_paths):
        raise ValueError(
            "--rehearsal_dataset_names must be empty or have the same number of entries as --rehearsal_dataset_paths"
        )
    obs_records: list[torch.Tensor] = []
    reference_records: list[torch.Tensor] = []
    raw_records: list[torch.Tensor] = []
    applied_records: list[torch.Tensor] = []
    phase_records: list[torch.Tensor] = []
    lift_records: list[torch.Tensor] = []
    success_records: list[torch.Tensor] = []
    unsafe_records: list[torch.Tensor] = []

    try:
        obs = env.reset()
        if isinstance(obs, tuple):
            obs = obs[0]
        if isinstance(obs, dict) and "obs" in obs:
            obs = obs["obs"]

        for step in range(args_cli.collection_steps):
            if not simulation_app.is_running():
                break
            with torch.no_grad():
                obs_t = _obs_tensor(agent, obs)
                raw_mus = _model_mus(agent.model, obs_t, action_dim, is_train=False).detach().clamp(-1.0, 1.0)
                reference_actions = _reference_delta_actions(task_env)
                if args_cli.collection_action_source == "reference_delta":
                    applied_actions = reference_actions
                elif args_cli.collection_action_source == "policy":
                    applied_actions = raw_mus
                else:
                    applied_actions = torch.clamp(
                        (1.0 - collection_teacher_alpha) * raw_mus
                        + collection_teacher_alpha * reference_actions,
                        -1.0,
                        1.0,
                    )

                obs_records.append(obs_t.detach().cpu())
                reference_records.append(reference_actions.detach().cpu())
                raw_records.append(raw_mus.detach().cpu())
                applied_records.append(applied_actions.detach().cpu())
                phase_records.append(getattr(task_env, "traj_phase_progress", torch.zeros(task_env.num_envs, device=task_env.device)).detach().cpu())
                lift_records.append(getattr(task_env, "cube_lift_height", torch.zeros(task_env.num_envs, device=task_env.device)).detach().cpu())
                success_records.append(getattr(task_env, "in_success_region", torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)).detach().float().cpu())
                unsafe_records.append(getattr(task_env, "traj_target_safe_mask", torch.ones(task_env.num_envs, dtype=torch.bool, device=task_env.device)).detach().logical_not().float().cpu())

                step_out = env.step(applied_actions)
                if len(step_out) == 5:
                    obs, _, dones, truncated, _ = step_out
                    dones = torch.logical_or(dones, truncated)
                else:
                    obs, _, dones, _ = step_out
                if isinstance(obs, dict) and "obs" in obs:
                    obs = obs["obs"]
                if isinstance(dones, torch.Tensor) and bool(dones.any()) and agent.is_rnn and agent.states is not None:
                    for state in agent.states:
                        state[:, dones.bool(), :] = 0.0
    finally:
        env.close()

    current_source_name = f"current_{args_cli.collection_action_source}_alpha{collection_teacher_alpha:.2f}".replace(".", "p")
    obs_tensors = [torch.cat(obs_records, dim=0).float()]
    reference_tensors = [torch.cat(reference_records, dim=0).float()]
    raw_tensors = [torch.cat(raw_records, dim=0).float()]
    applied_tensors = [torch.cat(applied_records, dim=0).float()]
    phase_tensors = [torch.cat(phase_records, dim=0).float()]
    lift_tensors = [torch.cat(lift_records, dim=0).float()]
    success_tensors = [torch.cat(success_records, dim=0).float()]
    unsafe_tensors = [torch.cat(unsafe_records, dim=0).float()]
    source_names = [current_source_name]
    source_slugs = [_source_slug(current_source_name)]
    source_ids = [torch.zeros(obs_tensors[0].shape[0], dtype=torch.long)]
    source_metadata: list[dict[str, object]] = [
        {
            "id": 0,
            "name": current_source_name,
            "slug": source_slugs[0],
            "path": "fresh_collection",
            "num_samples": int(obs_tensors[0].shape[0]),
            "collection_action_source": args_cli.collection_action_source,
            "collection_teacher_alpha": collection_teacher_alpha,
        }
    ]

    for dataset_idx, rehearsal_path_raw in enumerate(rehearsal_paths, start=1):
        rehearsal_path = Path(rehearsal_path_raw).expanduser()
        loaded = torch.load(rehearsal_path, map_location="cpu")
        if not isinstance(loaded, dict):
            raise TypeError(f"Rehearsal dataset {rehearsal_path} is not a dict.")
        if "obs" not in loaded or "reference_actions" not in loaded:
            raise KeyError(f"Rehearsal dataset {rehearsal_path} must include 'obs' and 'reference_actions'.")
        obs_loaded = loaded["obs"].detach().float().cpu()
        reference_loaded = loaded["reference_actions"].detach().float().cpu()
        if obs_loaded.ndim != 2 or reference_loaded.ndim != 2:
            raise ValueError(f"Rehearsal dataset {rehearsal_path} tensors must be 2-D.")
        if obs_loaded.shape[0] != reference_loaded.shape[0]:
            raise ValueError(f"Rehearsal dataset {rehearsal_path} obs/reference sample counts differ.")
        if obs_loaded.shape[-1] != obs_tensors[0].shape[-1]:
            raise ValueError(
                f"Rehearsal dataset {rehearsal_path} obs dim {obs_loaded.shape[-1]} "
                f"does not match fresh obs dim {obs_tensors[0].shape[-1]}."
            )
        if reference_loaded.shape[-1] != reference_tensors[0].shape[-1]:
            raise ValueError(
                f"Rehearsal dataset {rehearsal_path} action dim {reference_loaded.shape[-1]} "
                f"does not match fresh action dim {reference_tensors[0].shape[-1]}."
            )
        source_name = rehearsal_names[dataset_idx - 1] if rehearsal_names else f"rehearsal_{dataset_idx}"
        source_slug = _source_slug(source_name)
        while source_slug in source_slugs:
            source_slug = f"{source_slug}_{dataset_idx}"
        obs_tensors.append(obs_loaded)
        reference_tensors.append(reference_loaded)
        raw_tensors.append(
            loaded.get("raw_policy_actions_before", torch.full_like(reference_loaded, float("nan"))).detach().float().cpu()
        )
        applied_tensors.append(
            loaded.get("applied_collection_actions", torch.full_like(reference_loaded, float("nan"))).detach().float().cpu()
        )
        phase_tensors.append(loaded.get("phase", torch.full((obs_loaded.shape[0],), float("nan"))).detach().float().cpu())
        lift_tensors.append(
            loaded.get("cube_lift_height", torch.full((obs_loaded.shape[0],), float("nan"))).detach().float().cpu()
        )
        success_tensors.append(loaded.get("success", torch.full((obs_loaded.shape[0],), float("nan"))).detach().float().cpu())
        unsafe_tensors.append(
            loaded.get("unsafe_target", torch.full((obs_loaded.shape[0],), float("nan"))).detach().float().cpu()
        )
        source_names.append(source_name)
        source_slugs.append(source_slug)
        source_ids.append(torch.full((obs_loaded.shape[0],), dataset_idx, dtype=torch.long))
        source_metadata.append(
            {
                "id": dataset_idx,
                "name": source_name,
                "slug": source_slug,
                "path": str(rehearsal_path),
                "num_samples": int(obs_loaded.shape[0]),
                "collection_action_source": loaded.get("collection_action_source", "unknown"),
                "collection_teacher_alpha": loaded.get("collection_teacher_alpha", "unknown"),
                "input_checkpoint": loaded.get("input_checkpoint", "unknown"),
            }
        )

    obs_tensor = torch.cat(obs_tensors, dim=0).float()
    reference_tensor = torch.cat(reference_tensors, dim=0).float()
    raw_tensor = torch.cat(raw_tensors, dim=0).float()
    applied_tensor = torch.cat(applied_tensors, dim=0).float()
    phase_tensor = torch.cat(phase_tensors, dim=0).float()
    lift_tensor = torch.cat(lift_tensors, dim=0).float()
    success_tensor = torch.cat(success_tensors, dim=0).float()
    unsafe_tensor = torch.cat(unsafe_tensors, dim=0).float()
    source_id_tensor = torch.cat(source_ids, dim=0)
    dataset = {
        "obs": obs_tensor,
        "reference_actions": reference_tensor,
        "raw_policy_actions_before": raw_tensor,
        "applied_collection_actions": applied_tensor,
        "phase": phase_tensor,
        "cube_lift_height": lift_tensor,
        "success": success_tensor,
        "unsafe_target": unsafe_tensor,
        "source_ids": source_id_tensor,
        "source_names": source_names,
        "source_metadata": source_metadata,
        "loss_dims": torch.tensor(loss_dims, dtype=torch.long),
        "input_checkpoint": str(resume_path),
        "collection_action_source": args_cli.collection_action_source,
        "collection_teacher_alpha": collection_teacher_alpha,
    }
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dataset, dataset_path)

    device = torch.device(rl_device)
    obs_tensor = obs_tensor.to(device)
    reference_tensor = reference_tensor.to(device)
    source_id_tensor = source_id_tensor.to(device)
    num_samples = obs_tensor.shape[0]
    if num_samples < 2:
        raise RuntimeError("BC dataset collection produced fewer than two samples.")
    generator = torch.Generator(device=device)
    generator.manual_seed(args_cli.seed)
    perm = torch.randperm(num_samples, generator=generator, device=device)
    val_count = max(1, min(num_samples - 1, int(round(num_samples * args_cli.validation_fraction))))
    val_idx = perm[:val_count]
    train_idx = perm[val_count:]
    batch_size = max(1, min(args_cli.batch_size, int(train_idx.numel())))
    dims_t = torch.tensor(loss_dims, dtype=torch.long, device=device)
    train_idx_by_source = [train_idx[source_id_tensor[train_idx] == source_id] for source_id in range(len(source_slugs))]
    active_train_sources = [source_id for source_id, indices in enumerate(train_idx_by_source) if int(indices.numel()) > 0]
    if args_cli.source_batch_mode == "balanced" and not active_train_sources:
        raise RuntimeError("Balanced source batching requested but no train source indices are available.")
    source_loss_weights = _resolve_source_weights(args_cli.source_loss_weights, source_names, source_slugs)
    source_loss_weights_t = torch.tensor(source_loss_weights, dtype=torch.float32, device=device)
    best_score_weights = _parse_float_map(args_cli.best_score_weights) or {"val_l2": 1.0}
    if args_cli.distill_loss_weight < 0.0 or not math.isfinite(args_cli.distill_loss_weight):
        raise ValueError(f"--distill_loss_weight must be finite and non-negative, got {args_cli.distill_loss_weight}")
    distill_source_ids = _resolve_source_ids(args_cli.distill_sources, source_names, source_slugs)
    distill_source_names = [source_names[source_id] for source_id in distill_source_ids]
    distill_source_slugs = [source_slugs[source_id] for source_id in distill_source_ids]
    if args_cli.distill_loss_weight > 0.0 and not distill_source_ids:
        raise ValueError("--distill_loss_weight > 0 requires at least one --distill_sources entry")
    distill_dims = _parse_loss_dims(args_cli.distill_dims, action_dim) if args_cli.distill_dims.strip() else list(loss_dims)
    distill_dims_t = torch.tensor(distill_dims, dtype=torch.long, device=device)
    distill_enabled = args_cli.distill_loss_weight > 0.0 and bool(distill_source_ids)
    residual_adapter_enabled = bool(args_cli.residual_adapter_enabled)
    if args_cli.residual_hidden_dim < 0:
        raise ValueError(f"--residual_hidden_dim must be non-negative, got {args_cli.residual_hidden_dim}")
    if args_cli.residual_max_action < 0.0 or not math.isfinite(args_cli.residual_max_action):
        raise ValueError(f"--residual_max_action must be finite and non-negative, got {args_cli.residual_max_action}")
    if args_cli.residual_preserve_weight < 0.0 or not math.isfinite(args_cli.residual_preserve_weight):
        raise ValueError(
            f"--residual_preserve_weight must be finite and non-negative, got {args_cli.residual_preserve_weight}"
        )
    if args_cli.residual_l2_weight < 0.0 or not math.isfinite(args_cli.residual_l2_weight):
        raise ValueError(f"--residual_l2_weight must be finite and non-negative, got {args_cli.residual_l2_weight}")
    if args_cli.residual_gate_enabled and not residual_adapter_enabled:
        raise ValueError("--residual_gate_enabled requires --residual_adapter_enabled")
    if args_cli.residual_gate_hidden_dim < -1:
        raise ValueError(f"--residual_gate_hidden_dim must be -1 or non-negative, got {args_cli.residual_gate_hidden_dim}")
    residual_gate_hidden_dim = (
        int(args_cli.residual_hidden_dim)
        if int(args_cli.residual_gate_hidden_dim) < 0
        else int(args_cli.residual_gate_hidden_dim)
    )
    if not math.isfinite(float(args_cli.residual_gate_bias_init)):
        raise ValueError(f"--residual_gate_bias_init must be finite, got {args_cli.residual_gate_bias_init}")
    if args_cli.source_probe_steps < 0:
        raise ValueError(f"--source_probe_steps must be non-negative, got {args_cli.source_probe_steps}")
    if args_cli.source_probe_steps > 0 and (args_cli.source_probe_lr <= 0.0 or not math.isfinite(args_cli.source_probe_lr)):
        raise ValueError(f"--source_probe_lr must be positive and finite, got {args_cli.source_probe_lr}")
    residual_preserve_source_ids = _resolve_source_ids(args_cli.residual_preserve_sources, source_names, source_slugs)
    residual_preserve_source_names = [source_names[source_id] for source_id in residual_preserve_source_ids]
    residual_preserve_source_slugs = [source_slugs[source_id] for source_id in residual_preserve_source_ids]
    if residual_adapter_enabled and args_cli.residual_preserve_weight > 0.0 and not residual_preserve_source_ids:
        raise ValueError("--residual_preserve_weight > 0 requires --residual_preserve_sources")

    model = agent.model
    model.eval()
    with torch.no_grad():
        initial_action_tensor = _model_mus(model, obs_tensor, action_dim, is_train=False).detach().clamp(-1.0, 1.0)
    oracle_residual_stats = _oracle_residual_stats(
        base_actions=initial_action_tensor,
        target_actions=reference_tensor,
        source_ids=source_id_tensor,
        train_idx=train_idx,
        val_idx=val_idx,
        source_names=source_names,
        source_slugs=source_slugs,
        dims=loss_dims,
        residual_max_action=float(args_cli.residual_max_action),
    )
    probe_generator = torch.Generator(device=device)
    probe_generator.manual_seed(args_cli.seed + 1009)
    source_probe_summary = _run_source_probe(
        obs=obs_tensor,
        source_ids=source_id_tensor,
        train_idx=train_idx,
        val_idx=val_idx,
        num_sources=len(source_slugs),
        steps=int(args_cli.source_probe_steps),
        learning_rate=float(args_cli.source_probe_lr),
        batch_size=batch_size,
        generator=probe_generator,
    )
    print(
        json.dumps(
            {
                "oracle_residual_source_rows": oracle_residual_stats.get("source_rows", []),
                "source_probe": source_probe_summary,
            },
            sort_keys=True,
        )
    )
    distill_target_tensor: torch.Tensor | None = None
    if distill_enabled:
        distill_target_tensor = initial_action_tensor
        print(
            json.dumps(
                {
                    "distill_target": "input_checkpoint_initial_actor",
                    "distill_sources": distill_source_names,
                    "distill_source_ids": distill_source_ids,
                    "distill_dims": distill_dims,
                    "distill_loss_weight": float(args_cli.distill_loss_weight),
                },
                sort_keys=True,
            )
        )
    base_action_tensor: torch.Tensor | None = None
    residual_adapter: ResidualActionAdapter | None = None
    if residual_adapter_enabled:
        model.eval()
        for param in model.parameters():
            param.requires_grad_(False)
        base_action_tensor = initial_action_tensor
        residual_adapter = ResidualActionAdapter(
            obs_dim=int(obs_tensor.shape[-1]),
            action_dim=action_dim,
            hidden_dim=int(args_cli.residual_hidden_dim),
            max_action=float(args_cli.residual_max_action),
            gate_enabled=bool(args_cli.residual_gate_enabled),
            gate_hidden_dim=int(residual_gate_hidden_dim),
            gate_bias_init=float(args_cli.residual_gate_bias_init),
        ).to(device=device)
        print(
            json.dumps(
                {
                    "residual_adapter_enabled": True,
                    "residual_hidden_dim": int(args_cli.residual_hidden_dim),
                    "residual_max_action": float(args_cli.residual_max_action),
                    "residual_gate_enabled": bool(args_cli.residual_gate_enabled),
                    "residual_gate_hidden_dim": int(residual_gate_hidden_dim),
                    "residual_gate_bias_init": float(args_cli.residual_gate_bias_init),
                    "residual_preserve_sources": residual_preserve_source_names,
                    "residual_preserve_source_ids": residual_preserve_source_ids,
                    "residual_preserve_weight": float(args_cli.residual_preserve_weight),
                    "residual_l2_weight": float(args_cli.residual_l2_weight),
                },
                sort_keys=True,
            )
        )
    model.train()
    if residual_adapter_enabled and residual_adapter is not None:
        model.eval()
        residual_adapter.train()
        optimizer = torch.optim.AdamW(
            residual_adapter.parameters(),
            lr=args_cli.learning_rate,
            weight_decay=args_cli.weight_decay,
        )
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=args_cli.learning_rate, weight_decay=args_cli.weight_decay)
    curve_rows: list[dict[str, float | int | str]] = []

    def source_subset_mask(batch_sources: torch.Tensor, selected_source_ids: list[int]) -> torch.Tensor:
        mask = torch.zeros(batch_sources.shape, dtype=torch.bool, device=batch_sources.device)
        for source_id in selected_source_ids:
            mask = torch.logical_or(mask, batch_sources == int(source_id))
        return mask

    def predict_actions(
        indices: torch.Tensor, *, is_train: bool
    ) -> tuple[torch.Tensor, torch.Tensor | None, torch.Tensor | None, torch.Tensor | None]:
        if residual_adapter_enabled:
            if residual_adapter is None or base_action_tensor is None:
                raise RuntimeError("Residual adapter mode is enabled but adapter/base actions are missing.")
            base = base_action_tensor[indices]
            obs_subset = obs_tensor[indices]
            residual = residual_adapter(obs_subset)
            gate = residual_adapter.gate_values(obs_subset) if bool(args_cli.residual_gate_enabled) else None
            return torch.clamp(base + residual, -1.0, 1.0), base, residual, gate
        pred = _model_mus(model, obs_tensor[indices], action_dim, is_train=is_train).clamp(-1.0, 1.0)
        return pred, None, None, None

    def evaluate_split(step: int) -> dict[str, float | int | str]:
        model.eval()
        if residual_adapter is not None:
            residual_adapter.eval()
        with torch.no_grad():
            train_pred, train_base, train_residual, train_gate = predict_actions(train_idx, is_train=False)
            val_pred, val_base, val_residual, val_gate = predict_actions(val_idx, is_train=False)
        if residual_adapter is not None:
            residual_adapter.train()
        elif not residual_adapter_enabled:
            model.train()
        train_target = reference_tensor[train_idx]
        val_target = reference_tensor[val_idx]
        row: dict[str, float | int | str] = {"step": int(step)}
        row.update(_error_stats(train_pred, train_target, loss_dims, "train"))
        row.update(_error_stats(val_pred, val_target, loss_dims, "val"))
        if residual_adapter_enabled and train_base is not None and val_base is not None:
            row.update(_error_stats(train_base, train_target, loss_dims, "train_base"))
            row.update(_error_stats(val_base, val_target, loss_dims, "val_base"))
        if residual_adapter_enabled and train_residual is not None and val_residual is not None:
            train_zero = torch.zeros_like(train_residual)
            val_zero = torch.zeros_like(val_residual)
            row.update(_error_stats(train_residual, train_zero, loss_dims, "train_residual"))
            row.update(_error_stats(val_residual, val_zero, loss_dims, "val_residual"))
        if residual_adapter_enabled and train_gate is not None and val_gate is not None:
            row["train_gate_mean"] = _mean_float(train_gate)
            row["train_gate_min"] = float(torch.min(train_gate).detach().cpu())
            row["train_gate_max"] = float(torch.max(train_gate).detach().cpu())
            row["val_gate_mean"] = _mean_float(val_gate)
            row["val_gate_min"] = float(torch.min(val_gate).detach().cpu())
            row["val_gate_max"] = float(torch.max(val_gate).detach().cpu())
        train_sources = source_id_tensor[train_idx]
        val_sources = source_id_tensor[val_idx]
        for source_id, source_slug in enumerate(source_slugs):
            train_mask = train_sources == source_id
            if bool(train_mask.any()):
                row.update(
                    _error_stats(
                        train_pred[train_mask],
                        train_target[train_mask],
                        loss_dims,
                        f"train_source_{source_slug}",
                    )
                )
                row[f"train_source_{source_slug}_count"] = int(train_mask.sum().detach().cpu())
                if residual_adapter_enabled and train_base is not None and train_residual is not None:
                    row.update(
                        _error_stats(
                            train_base[train_mask],
                            train_target[train_mask],
                            loss_dims,
                            f"train_base_source_{source_slug}",
                        )
                    )
                    row.update(
                        _error_stats(
                            train_residual[train_mask],
                            torch.zeros_like(train_residual[train_mask]),
                            loss_dims,
                            f"train_residual_source_{source_slug}",
                        )
                    )
                    if train_gate is not None:
                        gate_subset = train_gate[train_mask]
                        row[f"train_gate_source_{source_slug}_mean"] = _mean_float(gate_subset)
                        row[f"train_gate_source_{source_slug}_min"] = float(torch.min(gate_subset).detach().cpu())
                        row[f"train_gate_source_{source_slug}_max"] = float(torch.max(gate_subset).detach().cpu())
            val_mask = val_sources == source_id
            if bool(val_mask.any()):
                row.update(
                    _error_stats(
                        val_pred[val_mask],
                        val_target[val_mask],
                        loss_dims,
                        f"val_source_{source_slug}",
                    )
                )
                row[f"val_source_{source_slug}_count"] = int(val_mask.sum().detach().cpu())
                if residual_adapter_enabled and val_base is not None and val_residual is not None:
                    row.update(
                        _error_stats(
                            val_base[val_mask],
                            val_target[val_mask],
                            loss_dims,
                            f"val_base_source_{source_slug}",
                        )
                    )
                    row.update(
                        _error_stats(
                            val_residual[val_mask],
                            torch.zeros_like(val_residual[val_mask]),
                            loss_dims,
                            f"val_residual_source_{source_slug}",
                        )
                    )
                    if val_gate is not None:
                        gate_subset = val_gate[val_mask]
                        row[f"val_gate_source_{source_slug}_mean"] = _mean_float(gate_subset)
                        row[f"val_gate_source_{source_slug}_min"] = float(torch.min(gate_subset).detach().cpu())
                        row[f"val_gate_source_{source_slug}_max"] = float(torch.max(gate_subset).detach().cpu())
        if residual_adapter_enabled and train_base is not None and val_base is not None:
            train_preserve_mask = source_subset_mask(train_sources, residual_preserve_source_ids)
            val_preserve_mask = source_subset_mask(val_sources, residual_preserve_source_ids)
            if bool(train_preserve_mask.any()):
                row.update(
                    _error_stats(
                        train_pred[train_preserve_mask],
                        train_base[train_preserve_mask],
                        loss_dims,
                        "train_preserve",
                    )
                )
                row["train_preserve_count"] = int(train_preserve_mask.sum().detach().cpu())
            if bool(val_preserve_mask.any()):
                row.update(
                    _error_stats(
                        val_pred[val_preserve_mask],
                        val_base[val_preserve_mask],
                        loss_dims,
                        "val_preserve",
                    )
                )
                row["val_preserve_count"] = int(val_preserve_mask.sum().detach().cpu())
            for source_id in residual_preserve_source_ids:
                source_slug = source_slugs[source_id]
                train_mask = train_sources == source_id
                if bool(train_mask.any()):
                    row.update(
                        _error_stats(
                            train_pred[train_mask],
                            train_base[train_mask],
                            loss_dims,
                            f"train_preserve_source_{source_slug}",
                        )
                    )
                    row[f"train_preserve_source_{source_slug}_count"] = int(train_mask.sum().detach().cpu())
                val_mask = val_sources == source_id
                if bool(val_mask.any()):
                    row.update(
                        _error_stats(
                            val_pred[val_mask],
                            val_base[val_mask],
                            loss_dims,
                            f"val_preserve_source_{source_slug}",
                        )
                    )
                    row[f"val_preserve_source_{source_slug}_count"] = int(val_mask.sum().detach().cpu())
        if distill_enabled and distill_target_tensor is not None:
            train_distill_target = distill_target_tensor[train_idx]
            val_distill_target = distill_target_tensor[val_idx]
            train_distill_mask = source_subset_mask(train_sources, distill_source_ids)
            val_distill_mask = source_subset_mask(val_sources, distill_source_ids)
            if bool(train_distill_mask.any()):
                row.update(
                    _error_stats(
                        train_pred[train_distill_mask],
                        train_distill_target[train_distill_mask],
                        distill_dims,
                        "train_distill",
                    )
                )
                row["train_distill_count"] = int(train_distill_mask.sum().detach().cpu())
            if bool(val_distill_mask.any()):
                row.update(
                    _error_stats(
                        val_pred[val_distill_mask],
                        val_distill_target[val_distill_mask],
                        distill_dims,
                        "val_distill",
                    )
                )
                row["val_distill_count"] = int(val_distill_mask.sum().detach().cpu())
            for source_id in distill_source_ids:
                source_slug = source_slugs[source_id]
                train_mask = train_sources == source_id
                if bool(train_mask.any()):
                    row.update(
                        _error_stats(
                            train_pred[train_mask],
                            train_distill_target[train_mask],
                            distill_dims,
                            f"train_distill_source_{source_slug}",
                        )
                    )
                    row[f"train_distill_source_{source_slug}_count"] = int(train_mask.sum().detach().cpu())
                val_mask = val_sources == source_id
                if bool(val_mask.any()):
                    row.update(
                        _error_stats(
                            val_pred[val_mask],
                            val_distill_target[val_mask],
                            distill_dims,
                            f"val_distill_source_{source_slug}",
                        )
                    )
                    row[f"val_distill_source_{source_slug}_count"] = int(val_mask.sum().detach().cpu())
        row["selection_score"] = _score_row(row, best_score_weights)
        return row

    def sample_train_batch() -> torch.Tensor:
        if args_cli.source_batch_mode == "random":
            return train_idx[torch.randint(0, int(train_idx.numel()), (batch_size,), generator=generator, device=device)]
        per_source = max(1, batch_size // max(1, len(active_train_sources)))
        remainder = max(0, batch_size - per_source * len(active_train_sources))
        choices = []
        for source_pos, source_id in enumerate(active_train_sources):
            count = per_source + (1 if source_pos < remainder else 0)
            indices = train_idx_by_source[source_id]
            local = torch.randint(0, int(indices.numel()), (count,), generator=generator, device=device)
            choices.append(indices[local])
        choice = torch.cat(choices, dim=0)
        if int(choice.numel()) > batch_size:
            choice = choice[:batch_size]
        shuffle = torch.randperm(int(choice.numel()), generator=generator, device=device)
        return choice[shuffle]

    def weighted_source_loss(pred: torch.Tensor, target: torch.Tensor, batch_sources: torch.Tensor) -> torch.Tensor:
        per_sample_loss = torch.mean(torch.square(pred[:, dims_t] - target[:, dims_t]), dim=-1)
        weighted_losses = []
        weights_used = []
        for source_id in torch.unique(batch_sources).detach().cpu().tolist():
            source_id_int = int(source_id)
            mask = batch_sources == source_id_int
            if bool(mask.any()):
                weight = source_loss_weights_t[source_id_int]
                if float(weight.detach().cpu()) > 0.0:
                    weighted_losses.append(weight * per_sample_loss[mask].mean())
                    weights_used.append(weight)
        if not weighted_losses:
            return per_sample_loss.mean()
        return torch.stack(weighted_losses).sum() / torch.stack(weights_used).sum().clamp_min(1.0e-8)

    def residual_preservation_loss(residual: torch.Tensor | None, batch_sources: torch.Tensor) -> torch.Tensor:
        if not residual_adapter_enabled or residual is None or args_cli.residual_preserve_weight <= 0.0:
            return torch.zeros((), dtype=reference_tensor.dtype, device=device)
        mask = source_subset_mask(batch_sources, residual_preserve_source_ids)
        if not bool(mask.any()):
            return torch.zeros((), dtype=reference_tensor.dtype, device=device)
        return torch.mean(torch.square(residual[mask][:, dims_t]))

    def residual_l2_loss(residual: torch.Tensor | None) -> torch.Tensor:
        if not residual_adapter_enabled or residual is None or args_cli.residual_l2_weight <= 0.0:
            return torch.zeros((), dtype=reference_tensor.dtype, device=device)
        return torch.mean(torch.square(residual[:, dims_t]))

    def distillation_loss(pred: torch.Tensor, batch_indices: torch.Tensor) -> torch.Tensor:
        if not distill_enabled or distill_target_tensor is None:
            return pred.sum() * 0.0
        batch_sources = source_id_tensor[batch_indices]
        mask = source_subset_mask(batch_sources, distill_source_ids)
        if not bool(mask.any()):
            return pred.sum() * 0.0
        target = distill_target_tensor[batch_indices]
        return torch.mean(torch.square(pred[mask][:, distill_dims_t] - target[mask][:, distill_dims_t]))

    curve_rows.append(evaluate_split(0))
    best_row = dict(curve_rows[0])
    best_score = float(best_row["selection_score"])
    best_step = 0
    if residual_adapter_enabled and residual_adapter is not None:
        best_state = {key: value.detach().cpu().clone() for key, value in residual_adapter.state_dict().items()}
    else:
        best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    evals_without_improvement = 0
    early_stop_triggered = False
    actual_train_steps = 0
    for step in range(1, args_cli.train_steps + 1):
        actual_train_steps = step
        choice = sample_train_batch()
        pred, _, residual, _ = predict_actions(choice, is_train=True)
        target = reference_tensor[choice]
        label_loss = weighted_source_loss(pred, target, source_id_tensor[choice])
        distill_loss = distillation_loss(pred, choice)
        residual_preserve_loss = residual_preservation_loss(residual, source_id_tensor[choice])
        residual_magnitude_loss = residual_l2_loss(residual)
        loss = (
            label_loss
            + float(args_cli.distill_loss_weight) * distill_loss
            + float(args_cli.residual_preserve_weight) * residual_preserve_loss
            + float(args_cli.residual_l2_weight) * residual_magnitude_loss
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_params = residual_adapter.parameters() if residual_adapter_enabled and residual_adapter is not None else model.parameters()
        torch.nn.utils.clip_grad_norm_(grad_params, max_norm=1.0)
        optimizer.step()
        if step == args_cli.train_steps or step % max(1, args_cli.eval_interval) == 0:
            row = evaluate_split(step)
            row["last_batch_loss"] = float(loss.detach().cpu())
            row["last_batch_label_loss"] = float(label_loss.detach().cpu())
            row["last_batch_distill_loss"] = float(distill_loss.detach().cpu())
            row["last_batch_residual_preserve_loss"] = float(residual_preserve_loss.detach().cpu())
            row["last_batch_residual_l2_loss"] = float(residual_magnitude_loss.detach().cpu())
            curve_rows.append(row)
            score = float(row["selection_score"])
            if score < best_score:
                best_score = score
                best_step = step
                best_row = dict(row)
                if residual_adapter_enabled and residual_adapter is not None:
                    best_state = {
                        key: value.detach().cpu().clone() for key, value in residual_adapter.state_dict().items()
                    }
                else:
                    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                evals_without_improvement = 0
            else:
                evals_without_improvement += 1
            print(json.dumps(row, sort_keys=True))
            if args_cli.early_stop_patience > 0 and evals_without_improvement >= args_cli.early_stop_patience:
                early_stop_triggered = True
                print(
                    json.dumps(
                        {
                            "early_stop_triggered": True,
                            "step": int(step),
                            "best_step": int(best_step),
                            "best_score": best_score,
                            "evals_without_improvement": int(evals_without_improvement),
                        },
                        sort_keys=True,
                    )
                )
                break

    if residual_adapter_enabled and residual_adapter is not None:
        residual_adapter.load_state_dict(best_state)
    else:
        model.load_state_dict(best_state)
    ckpt = torch_ext.load_checkpoint(resume_path)
    ckpt["model"] = model.state_dict()
    if residual_adapter_enabled and residual_adapter is not None:
        adapter_metadata = residual_adapter.metadata()
        adapter_metadata.update(
            {
                "state_dict": {
                    key: value.detach().cpu().clone() for key, value in residual_adapter.state_dict().items()
                },
                "base_checkpoint": str(resume_path),
                "preserve_sources": residual_preserve_source_names,
                "preserve_source_ids": residual_preserve_source_ids,
                "preserve_source_slugs": residual_preserve_source_slugs,
                "preserve_weight": float(args_cli.residual_preserve_weight),
                "residual_l2_weight": float(args_cli.residual_l2_weight),
                "gate_enabled": bool(args_cli.residual_gate_enabled),
                "gate_hidden_dim": int(residual_gate_hidden_dim),
                "gate_bias_init": float(args_cli.residual_gate_bias_init),
                "train_sources": source_names,
                "selected_step": int(best_step),
                "selected_score": best_score,
            }
        )
        ckpt["bc_residual_action_adapter"] = adapter_metadata
    if hasattr(model, "running_mean_std") and "running_mean_std" in ckpt:
        ckpt["running_mean_std"] = model.running_mean_std.state_dict()
    ckpt["bc_reference_action_imitation"] = {
        "input_checkpoint": str(resume_path),
        "num_samples": int(num_samples),
        "num_train": int(train_idx.numel()),
        "num_val": int(val_idx.numel()),
        "loss_dims": loss_dims,
        "train_steps": int(args_cli.train_steps),
        "actual_train_steps": int(actual_train_steps),
        "learning_rate": float(args_cli.learning_rate),
        "dataset_path": str(dataset_path),
        "source_batch_mode": args_cli.source_batch_mode,
        "source_loss_weights": source_loss_weights,
        "best_score_weights": best_score_weights,
        "distill_target": "input_checkpoint_initial_actor" if distill_enabled else "disabled",
        "distill_sources": distill_source_names,
        "distill_source_ids": distill_source_ids,
        "distill_dims": distill_dims,
        "distill_loss_weight": float(args_cli.distill_loss_weight),
        "residual_adapter_enabled": bool(residual_adapter_enabled),
        "residual_hidden_dim": int(args_cli.residual_hidden_dim),
        "residual_max_action": float(args_cli.residual_max_action),
        "residual_gate_enabled": bool(args_cli.residual_gate_enabled),
        "residual_gate_hidden_dim": int(residual_gate_hidden_dim),
        "residual_gate_bias_init": float(args_cli.residual_gate_bias_init),
        "residual_preserve_sources": residual_preserve_source_names,
        "residual_preserve_source_ids": residual_preserve_source_ids,
        "residual_preserve_weight": float(args_cli.residual_preserve_weight),
        "residual_l2_weight": float(args_cli.residual_l2_weight),
        "best_step": int(best_step),
        "best_score": best_score,
    }
    torch.save(ckpt, checkpoint_out)

    reference_summary = (
        task_env.trajectory_tracking_reference_summary()
        if hasattr(task_env, "trajectory_tracking_reference_summary")
        else {}
    )
    summary: dict[str, object] = {
        "task": args_cli.task,
        "input_checkpoint": str(resume_path),
        "output_checkpoint": str(checkpoint_out),
        "dataset_path": str(dataset_path),
        "metrics_path": str(metrics_path),
        "curve_csv_path": str(curve_csv_path),
        "plot_path": str(plot_path),
        "source_plot_path": str(source_plot_path),
        "oracle_plot_path": str(oracle_plot_path),
        "oracle_source_csv_path": str(oracle_source_csv_path),
        "oracle_dim_csv_path": str(oracle_dim_csv_path),
        "report_path": str(report_path),
        "num_samples": int(num_samples),
        "num_train": int(train_idx.numel()),
        "num_val": int(val_idx.numel()),
        "obs_dim": int(obs_tensor.shape[-1]),
        "action_dim": int(action_dim),
        "loss_dims": loss_dims,
        "collection_steps": int(args_cli.collection_steps),
        "num_envs": int(args_cli.num_envs),
        "train_steps": int(args_cli.train_steps),
        "actual_train_steps": int(actual_train_steps),
        "batch_size": int(batch_size),
        "learning_rate": float(args_cli.learning_rate),
        "validation_fraction": float(args_cli.validation_fraction),
        "collection_action_source": args_cli.collection_action_source,
        "collection_teacher_alpha": collection_teacher_alpha,
        "rehearsal_dataset_paths": rehearsal_paths,
        "dataset_sources": source_metadata,
        "source_batch_mode": args_cli.source_batch_mode,
        "source_loss_weights": dict(zip(source_slugs, source_loss_weights, strict=True)),
        "best_score_weights": best_score_weights,
        "distill_target": "input_checkpoint_initial_actor" if distill_enabled else "disabled",
        "distill_sources": distill_source_names,
        "distill_source_ids": distill_source_ids,
        "distill_source_slugs": distill_source_slugs,
        "distill_dims": distill_dims,
        "distill_loss_weight": float(args_cli.distill_loss_weight),
        "residual_adapter_enabled": bool(residual_adapter_enabled),
        "residual_hidden_dim": int(args_cli.residual_hidden_dim),
        "residual_max_action": float(args_cli.residual_max_action),
        "residual_gate_enabled": bool(args_cli.residual_gate_enabled),
        "residual_gate_hidden_dim": int(residual_gate_hidden_dim),
        "residual_gate_bias_init": float(args_cli.residual_gate_bias_init),
        "residual_preserve_sources": residual_preserve_source_names,
        "residual_preserve_source_ids": residual_preserve_source_ids,
        "residual_preserve_source_slugs": residual_preserve_source_slugs,
        "residual_preserve_weight": float(args_cli.residual_preserve_weight),
        "residual_l2_weight": float(args_cli.residual_l2_weight),
        "oracle_residual_stats": oracle_residual_stats,
        "source_probe": source_probe_summary,
        "selected": best_row,
        "selected_step": int(best_step),
        "selected_score": best_score,
        "early_stop_triggered": bool(early_stop_triggered),
        "curobo_validated": bool(reference_summary.get("curobo_validated", False)) if isinstance(reference_summary, dict) else False,
        "reference_summary": reference_summary,
        "dataset_reference_stats": _action_stats(reference_tensor.cpu(), "reference"),
        "dataset_raw_policy_before_stats": _action_stats(raw_tensor.cpu(), "raw_before"),
        "dataset_applied_collection_stats": _action_stats(applied_tensor.cpu(), "applied_collection"),
        "initial": curve_rows[0],
        "final": curve_rows[-1],
    }
    _write_csv(curve_rows, curve_csv_path)
    oracle_source_rows = oracle_residual_stats.get("source_rows", [])
    if isinstance(oracle_source_rows, list):
        _write_csv(oracle_source_rows, oracle_source_csv_path)
    oracle_dim_rows = oracle_residual_stats.get("dim_rows", [])
    if isinstance(oracle_dim_rows, list):
        _write_csv(oracle_dim_rows, oracle_dim_csv_path)
    _draw_loss_plot(curve_rows, plot_path)
    _draw_source_metric_plot(curve_rows, source_plot_path)
    _draw_oracle_residual_plot(oracle_residual_stats, oracle_plot_path)
    metrics_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    _write_report(summary, curve_rows, report_path)
    print("[INFO] BC diagnostic summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
