"""Diagnostic BC warm-start for Franka cube pass7 first-contact actions.

This script is intentionally diagnostic-only. It samples valid GraspGenX pass7
reset states, labels RL-Games observations with assisted reference actions, and
fine-tunes a copied checkpoint actor with supervised MSE. It does not change the
environment, reward, reset, termination, or PPO configuration.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--num_resets", type=int, default=16)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--grasp_prior_library_path", type=str, required=True)
parser.add_argument("--init_checkpoint", type=str, required=True)
parser.add_argument("--train_epochs", type=int, default=40)
parser.add_argument("--batch_size", type=int, default=2048)
parser.add_argument("--learning_rate", type=float, default=1.0e-3)
parser.add_argument("--train_scope", choices=("mu", "actor", "all"), default="mu")
parser.add_argument("--validation_fraction", type=float, default=0.25)
parser.add_argument("--phase_balance_loss", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--lift_phase_loss_weight", type=float, default=1.0)
parser.add_argument("--lift_z_mse_weight", type=float, default=1.0)
parser.add_argument("--lift_z_sign_loss_weight", type=float, default=0.0)
parser.add_argument("--approach_steps", type=int, default=16)
parser.add_argument("--close_steps", type=int, default=12)
parser.add_argument("--lift_steps", type=int, default=12)
parser.add_argument("--close_width", type=float, default=0.055)
parser.add_argument("--lift_action_z", type=float, default=0.15)
parser.add_argument("--oracle_gain", type=float, default=8.0)
parser.add_argument("--oracle_max_position_action", type=float, default=1.0)
parser.add_argument("--track_orientation", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--gate_val_mse", type=float, default=0.04)
parser.add_argument("--gate_gripper_sign", type=float, default=0.95)
parser.add_argument("--gate_lift_z_sign", type=float, default=0.90)
parser.add_argument("--save_bc_checkpoint", action=argparse.BooleanOptionalAction, default=True)
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
from isaaclab.utils import math as math_utils
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict
from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

import isaaclab_tasks  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401


ACTION_NAMES = ("x", "y", "z", "roll", "pitch", "yaw", "gripper")


class DextrahBcVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


class DextrahBcGpuEnv(RlGamesGpuEnv):
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    leading = ["split", "phase", "action_dim", "action_name", "reset_index", "env_id", "step"]
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


def _write_exception_artifact(output_dir: Path, exc: BaseException) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = traceback.format_exc()
    (output_dir / "ERROR.md").write_text(
        "# BC Pass7 Diagnostic Error\n\n"
        f"- error_type: `{type(exc).__name__}`\n"
        f"- error: `{exc}`\n\n"
        "```text\n"
        f"{trace}"
        "```\n",
        encoding="utf-8",
    )
    _write_json(output_dir / "error.json", {"error_type": type(exc).__name__, "error": str(exc), "traceback": trace})


def _tensor_stats(values: torch.Tensor | np.ndarray) -> dict[str, float]:
    arr = values.detach().float().cpu().numpy() if isinstance(values, torch.Tensor) else np.asarray(values, dtype=float)
    arr = arr.reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"mean": math.nan, "std": math.nan, "min": math.nan, "max": math.nan, "p50": math.nan, "p95": math.nan}
    return {
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite)),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "p50": float(np.percentile(finite, 50)),
        "p95": float(np.percentile(finite, 95)),
    }


def _obs_policy_tensor(obs):
    if isinstance(obs, tuple):
        obs = obs[0]
    if isinstance(obs, dict):
        obs = obs["obs"]
    return obs


def _gripper_action_for_width(width: float, max_width: float) -> float:
    if max_width <= 1.0e-6:
        return -1.0
    return float(np.clip(2.0 * float(width) / float(max_width) - 1.0, -1.0, 1.0))


def _exact_tracking_action(task_env, gripper_action: float) -> torch.Tensor:
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    task_env._compute_intermediate_values(update_success_timer=False)
    current_ee_pos_b, current_ee_quat_b = task_env._compute_ee_frame_pose()
    exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
        task_env._robot.data.root_pos_w,
        task_env._robot.data.root_quat_w,
        task_env.grasp_prior_reset_exact_ee_pos_w,
        task_env.grasp_prior_reset_exact_ee_quat_w,
    )
    pos_action = float(args_cli.oracle_gain) * (exact_ee_pos_b - current_ee_pos_b) / torch.clamp(
        task_env.action_scale[:3], min=1.0e-6
    )
    max_position_action = max(float(args_cli.oracle_max_position_action), 0.0)
    action[:, :3] = torch.clamp(pos_action, min=-max_position_action, max=max_position_action)
    if bool(args_cli.track_orientation):
        _, rot_error_b = math_utils.compute_pose_error(
            current_ee_pos_b,
            current_ee_quat_b,
            exact_ee_pos_b,
            exact_ee_quat_b,
            rot_error_type="axis_angle",
        )
        rot_action = float(args_cli.oracle_gain) * rot_error_b / torch.clamp(task_env.action_scale[3:6], min=1.0e-6)
        action[:, 3:6] = torch.clamp(rot_action, min=-1.0, max=1.0)
    action[:, 6] = float(gripper_action)
    return action


def _reference_action(task_env, phase: str) -> torch.Tensor:
    open_action = _gripper_action_for_width(float(task_env.cfg.max_gripper_width), float(task_env.cfg.max_gripper_width))
    close_action = _gripper_action_for_width(float(args_cli.close_width), float(task_env.cfg.max_gripper_width))
    if phase == "approach":
        return _exact_tracking_action(task_env, open_action)
    if phase == "close":
        return _exact_tracking_action(task_env, close_action)
    if phase == "lift":
        action = _exact_tracking_action(task_env, close_action)
        action[:, 2] = float(np.clip(args_cli.lift_action_z, -1.0, 1.0))
        return action
    raise ValueError(f"Unknown phase {phase!r}")


def _phase_for_step(step: int) -> str:
    if step < int(args_cli.approach_steps):
        return "approach"
    if step < int(args_cli.approach_steps) + int(args_cli.close_steps):
        return "close"
    return "lift"


def _create_player(agent_cfg: dict, env, checkpoint_path: str) -> BasePlayer:
    cfg = copy.deepcopy(agent_cfg)
    cfg["params"]["load_checkpoint"] = True
    cfg["params"]["load_path"] = checkpoint_path
    cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    runner = Runner()
    runner.load(cfg)
    player: BasePlayer = runner.create_player()
    player.restore(checkpoint_path)
    player.reset()
    return player


def _prepare_player(player: BasePlayer, obs: torch.Tensor, *, obs_is_preprocessed: bool = False) -> torch.Tensor:
    player.reset()
    obs_t = obs if obs_is_preprocessed else player.obs_to_torch(obs)
    _ = player.get_batch_size(obs_t, 1)
    if player.is_rnn:
        player.init_rnn()
    return obs_t


def _forward_mu(player: BasePlayer, obs: torch.Tensor) -> torch.Tensor:
    input_dict: dict[str, Any] = {"is_train": False, "prev_actions": None, "obs": obs}
    if getattr(player, "is_rnn", False):
        input_dict["rnn_states"] = getattr(player, "states", None)
    out = player.model(input_dict)
    if not isinstance(out, dict):
        raise RuntimeError(f"Expected model dict output, got {type(out).__name__}")
    for key in ("mus", "mu", "actions"):
        value = out.get(key)
        if isinstance(value, torch.Tensor):
            return torch.clamp(value, -1.0, 1.0)
    raise RuntimeError(f"Model output has no mus/mu/actions tensor; keys={sorted(out.keys())}")


def _select_trainable_params(model: torch.nn.Module, scope: str) -> tuple[list[torch.nn.Parameter], list[str]]:
    for param in model.parameters():
        param.requires_grad_(False)
    selected: list[tuple[str, torch.nn.Parameter]] = []
    for name, param in model.named_parameters():
        lower = name.lower()
        if scope == "all":
            selected.append((name, param))
        elif scope == "actor":
            if "critic" not in lower and "value" not in lower and "sigma" not in lower:
                selected.append((name, param))
        elif scope == "mu":
            if "mu" in lower and "sigma" not in lower:
                selected.append((name, param))
    if not selected and scope != "all":
        print(f"[WARN] No parameters selected for scope={scope}; falling back to all parameters.", flush=True)
        return _select_trainable_params(model, "all")
    for _, param in selected:
        param.requires_grad_(True)
    return [param for _, param in selected], [name for name, _ in selected]


def _split_indices(reset_ids: torch.Tensor, validation_fraction: float) -> tuple[torch.Tensor, torch.Tensor]:
    unique_resets = torch.unique(reset_ids.detach().cpu()).tolist()
    unique_resets = [int(v) for v in unique_resets]
    if len(unique_resets) <= 1:
        indices = torch.arange(reset_ids.numel(), device=reset_ids.device)
        split = max(1, int(0.8 * indices.numel()))
        return indices[:split], indices[split:]
    val_count = max(1, int(round(len(unique_resets) * float(validation_fraction))))
    val_resets = set(unique_resets[-val_count:])
    val_mask = torch.tensor([int(v.item()) in val_resets for v in reset_ids], device=reset_ids.device)
    all_indices = torch.arange(reset_ids.numel(), device=reset_ids.device)
    return all_indices[~val_mask], all_indices[val_mask]


def _bc_loss(pred: torch.Tensor, target: torch.Tensor, phase_ids: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
    mse = (pred - target).square()
    sample_loss = mse.mean(dim=1)
    lift_mask = phase_ids == 2
    if float(args_cli.lift_z_mse_weight) != 1.0 and bool(lift_mask.any()):
        weighted_mse = mse.clone()
        weighted_mse[lift_mask, 2] = weighted_mse[lift_mask, 2] * float(args_cli.lift_z_mse_weight)
        sample_loss = weighted_mse.mean(dim=1)
    if float(args_cli.lift_phase_loss_weight) != 1.0 and bool(lift_mask.any()):
        sample_loss = sample_loss.clone()
        sample_loss[lift_mask] = sample_loss[lift_mask] * float(args_cli.lift_phase_loss_weight)
    if bool(args_cli.phase_balance_loss):
        weights = torch.ones_like(sample_loss)
        active_phases = torch.unique(phase_ids)
        for phase_id in active_phases:
            mask = phase_ids == phase_id
            if bool(mask.any()):
                weights[mask] = float(phase_ids.numel()) / (float(active_phases.numel()) * float(mask.sum()))
        sample_loss = sample_loss * weights
    loss = sample_loss.mean()
    lift_z_sign_loss = torch.zeros((), device=pred.device, dtype=pred.dtype)
    if float(args_cli.lift_z_sign_loss_weight) > 0.0 and bool(lift_mask.any()):
        target_sign = torch.sign(target[lift_mask, 2])
        active = target_sign.abs() > 1.0e-6
        if bool(active.any()):
            margin = pred[lift_mask, 2][active] * target_sign[active]
            lift_z_sign_loss = torch.nn.functional.softplus(-margin / 0.05).mean()
            loss = loss + float(args_cli.lift_z_sign_loss_weight) * lift_z_sign_loss
    diagnostics = {
        "base_mse": float(torch.mean((pred - target).square()).detach()),
        "weighted_mse_term": float(sample_loss.mean().detach()),
        "lift_z_sign_loss": float(lift_z_sign_loss.detach()),
        "total_loss": float(loss.detach()),
    }
    return loss, diagnostics


def _prediction_metrics(
    pred: torch.Tensor,
    target: torch.Tensor,
    phase_ids: torch.Tensor,
    *,
    split: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pred = pred.detach().float().cpu()
    target = target.detach().float().cpu()
    phase_ids_cpu = phase_ids.detach().long().cpu()
    err = pred - target
    summary: dict[str, Any] = {
        f"{split}_mse": float(torch.mean(err.square())),
        f"{split}_mae": float(torch.mean(err.abs())),
        f"{split}_max_abs_error": float(torch.max(err.abs())),
        f"{split}_gripper_sign_accuracy": float(((pred[:, 6] >= 0.0) == (target[:, 6] >= 0.0)).float().mean()),
        f"{split}_z_sign_accuracy": float(((pred[:, 2] >= 0.0) == (target[:, 2] >= 0.0)).float().mean()),
    }
    lift_mask = phase_ids_cpu == 2
    if bool(lift_mask.any()):
        summary[f"{split}_lift_z_sign_accuracy"] = float(
            ((pred[lift_mask, 2] >= 0.0) == (target[lift_mask, 2] >= 0.0)).float().mean()
        )
        summary[f"{split}_lift_z_mae"] = float(torch.mean((pred[lift_mask, 2] - target[lift_mask, 2]).abs()))
        summary[f"{split}_lift_z_negative_rate"] = float((pred[lift_mask, 2] < 0.0).float().mean())
    rows: list[dict[str, Any]] = []
    phase_names = {0: "approach", 1: "close", 2: "lift"}
    for phase_id, phase_name in phase_names.items():
        mask = phase_ids_cpu == phase_id
        if not bool(mask.any()):
            continue
        z_sign_accuracy = float(((pred[mask, 2] >= 0.0) == (target[mask, 2] >= 0.0)).float().mean())
        summary[f"{split}_{phase_name}_z_sign_accuracy"] = z_sign_accuracy
        summary[f"{split}_{phase_name}_z_negative_rate"] = float((pred[mask, 2] < 0.0).float().mean())
        summary[f"{split}_{phase_name}_z_mae"] = float(torch.mean((pred[mask, 2] - target[mask, 2]).abs()))
        for dim, name in enumerate(ACTION_NAMES):
            dim_err = err[mask, dim]
            rows.append(
                {
                    "split": split,
                    "phase": phase_name,
                    "action_dim": dim,
                    "action_name": name,
                    "target_mean": float(target[mask, dim].mean()),
                    "pred_mean": float(pred[mask, dim].mean()),
                    "mse": float(torch.mean(dim_err.square())),
                    "mae": float(torch.mean(dim_err.abs())),
                    "sign_accuracy": float(((pred[mask, dim] >= 0.0) == (target[mask, dim] >= 0.0)).float().mean()),
                    **{f"target_{k}": v for k, v in _tensor_stats(target[mask, dim]).items()},
                    **{f"pred_{k}": v for k, v in _tensor_stats(pred[mask, dim]).items()},
                }
            )
    return summary, rows


def _write_plots(output_dir: Path, losses: list[dict[str, float]], metric_rows: list[dict[str, Any]]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[WARN] matplotlib unavailable; skipping plots: {exc}", flush=True)
        return artifacts
    if losses:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot([row["epoch"] for row in losses], [row["train_loss"] for row in losses], label="train")
        ax.plot([row["epoch"] for row in losses], [row["val_loss"] for row in losses], label="val")
        ax.set_xlabel("BC epoch")
        ax.set_ylabel("MSE")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        path = output_dir / "bc_loss_curves.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["bc_loss_curves"] = str(path)
    if metric_rows:
        phases = ["approach", "close", "lift"]
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        axes = axes.ravel()
        for dim, name in enumerate(ACTION_NAMES):
            ax = axes[dim]
            xs = np.arange(len(phases))
            width = 0.35
            target = []
            pred = []
            for phase in phases:
                row = next(
                    (
                        item
                        for item in metric_rows
                        if item.get("split") == "val" and item.get("phase") == phase and int(item.get("action_dim")) == dim
                    ),
                    None,
                )
                target.append(float(row["target_mean"]) if row else math.nan)
                pred.append(float(row["pred_mean"]) if row else math.nan)
            ax.bar(xs - width / 2.0, target, width, label="target")
            ax.bar(xs + width / 2.0, pred, width, label="pred")
            ax.set_title(name)
            ax.set_xticks(xs)
            ax.set_xticklabels(phases, rotation=30)
            ax.set_ylim(-1.05, 1.05)
            ax.grid(True, alpha=0.2)
        axes[-1].axis("off")
        axes[0].legend()
        fig.suptitle("Validation action means by phase")
        fig.tight_layout()
        path = output_dir / "bc_action_phase_means.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["bc_action_phase_means"] = str(path)
        fig, ax = plt.subplots(figsize=(7, 4))
        sign_rows = [
            item
            for item in metric_rows
            if item.get("split") in {"initial_val", "val"} and int(item.get("action_dim")) == 2
        ]
        x_labels = []
        heights = []
        for split in ["initial_val", "val"]:
            for phase in phases:
                row = next((item for item in sign_rows if item.get("split") == split and item.get("phase") == phase), None)
                x_labels.append(f"{split}\n{phase}")
                heights.append(float(row["sign_accuracy"]) if row else math.nan)
        ax.bar(np.arange(len(heights)), heights)
        ax.axhline(float(args_cli.gate_lift_z_sign), color="tab:red", linestyle="--", linewidth=1, label="lift gate")
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("z sign accuracy")
        ax.set_xticks(np.arange(len(heights)))
        ax.set_xticklabels(x_labels, rotation=30, ha="right")
        ax.grid(True, axis="y", alpha=0.2)
        ax.legend(loc="lower right")
        fig.tight_layout()
        path = output_dir / "bc_z_sign_accuracy.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        artifacts["bc_z_sign_accuracy"] = str(path)
    return artifacts


def _save_bc_checkpoint(init_checkpoint: str, player: BasePlayer, output_path: Path) -> None:
    try:
        state = torch.load(init_checkpoint, map_location="cpu", weights_only=False)
    except TypeError:
        state = torch.load(init_checkpoint, map_location="cpu")
    if not isinstance(state, dict):
        raise RuntimeError(f"Expected dict checkpoint, got {type(state).__name__}")
    state = copy.deepcopy(state)
    state["model"] = {key: value.detach().cpu() for key, value in player.model.state_dict().items()}
    state["dextrah_bc_diagnostic"] = {
        "source_checkpoint": init_checkpoint,
        "train_scope": args_cli.train_scope,
        "train_epochs": int(args_cli.train_epochs),
        "learning_rate": float(args_cli.learning_rate),
        "phase_balance_loss": bool(args_cli.phase_balance_loss),
        "lift_phase_loss_weight": float(args_cli.lift_phase_loss_weight),
        "lift_z_mse_weight": float(args_cli.lift_z_mse_weight),
        "lift_z_sign_loss_weight": float(args_cli.lift_z_sign_loss_weight),
        "note": "Diagnostic BC first-contact action warm-start; non-apple-to-apple.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, output_path)


def _loadability_check(agent_cfg: dict, env, checkpoint_path: str, obs: torch.Tensor, target: torch.Tensor) -> dict[str, Any]:
    player = _create_player(agent_cfg, env, checkpoint_path)
    obs_t = _prepare_player(player, obs, obs_is_preprocessed=True)
    with torch.inference_mode():
        pred = _forward_mu(player, obs_t)
    return {
        "checkpoint": checkpoint_path,
        "mse": float(torch.mean((pred - target).square())),
        "mae": float(torch.mean((pred - target).abs())),
        "pred_action_mean": _json_safe(pred.mean(dim=0)),
        "target_action_mean": _json_safe(target.mean(dim=0)),
    }


def _write_report(
    path: Path,
    *,
    config: dict[str, Any],
    dataset_summary: dict[str, Any],
    train_summary: dict[str, Any],
    gate: dict[str, Any],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Pass7 BC First-Contact Diagnostic",
        "",
        "Diagnostic-only run. This does not change the apple-to-apple task defaults and does not launch PPO/A100.",
        "",
        "## Verdict",
        "",
        f"- supervised gate: `{'PASS' if gate.get('pass') else 'FAIL'}`",
        f"- validation MSE: `{train_summary.get('val_mse')}`",
        f"- validation MAE: `{train_summary.get('val_mae')}`",
        f"- gripper sign accuracy: `{train_summary.get('val_gripper_sign_accuracy')}`",
        f"- lift z sign accuracy: `{train_summary.get('val_lift_z_sign_accuracy')}`",
        f"- lift z negative prediction rate: `{train_summary.get('val_lift_z_negative_rate')}`",
        f"- validation z sign accuracy: `{train_summary.get('val_z_sign_accuracy')}`",
        f"- saved BC checkpoint: `{train_summary.get('bc_checkpoint_path')}`",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(_json_safe(config), indent=2, sort_keys=True),
        "```",
        "",
        "## Dataset",
        "",
        "```json",
        json.dumps(_json_safe(dataset_summary), indent=2, sort_keys=True),
        "```",
        "",
        "## Training Summary",
        "",
        "```json",
        json.dumps(_json_safe(train_summary), indent=2, sort_keys=True),
        "```",
        "",
        "## Gate",
        "",
        "```json",
        json.dumps(_json_safe(gate), indent=2, sort_keys=True),
        "```",
        "",
        "## Artifacts",
        "",
    ]
    for name, artifact_path in artifacts.items():
        lines.append(f"- `{name}`: `{artifact_path}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg, agent_cfg: dict):
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("bc_pass7_%Y%m%d_%H%M%S")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    init_checkpoint = retrieve_file_path(args_cli.init_checkpoint)

    env_cfg.scene.num_envs = int(args_cli.num_envs)
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = int(args_cli.seed)
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_library_path = str(args_cli.grasp_prior_library_path)
    env_cfg.cube_spawn_xy_randomization = float(args_cli.cube_spawn_xy_randomization)
    if hasattr(env_cfg, "use_cuda_graph"):
        env_cfg.use_cuda_graph = False
    agent_cfg["params"]["seed"] = int(args_cli.seed)

    config = {
        "task": args_cli.task,
        "num_envs": int(args_cli.num_envs),
        "num_resets": int(args_cli.num_resets),
        "seed": int(args_cli.seed),
        "cube_spawn_xy_randomization": float(args_cli.cube_spawn_xy_randomization),
        "grasp_prior_library_path": str(args_cli.grasp_prior_library_path),
        "init_checkpoint": init_checkpoint,
        "approach_steps": int(args_cli.approach_steps),
        "close_steps": int(args_cli.close_steps),
        "lift_steps": int(args_cli.lift_steps),
        "close_width": float(args_cli.close_width),
        "lift_action_z": float(args_cli.lift_action_z),
        "oracle_gain": float(args_cli.oracle_gain),
        "oracle_max_position_action": float(args_cli.oracle_max_position_action),
        "track_orientation": bool(args_cli.track_orientation),
        "train_epochs": int(args_cli.train_epochs),
        "batch_size": int(args_cli.batch_size),
        "learning_rate": float(args_cli.learning_rate),
        "train_scope": str(args_cli.train_scope),
        "validation_fraction": float(args_cli.validation_fraction),
        "phase_balance_loss": bool(args_cli.phase_balance_loss),
        "lift_phase_loss_weight": float(args_cli.lift_phase_loss_weight),
        "lift_z_mse_weight": float(args_cli.lift_z_mse_weight),
        "lift_z_sign_loss_weight": float(args_cli.lift_z_sign_loss_weight),
        "output_dir": str(output_dir),
    }
    print("[INFO] BC pass7 diagnostic config:")
    print_dict(config, nesting=4)

    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    gym_env = gym.make(args_cli.task, cfg=env_cfg)
    if isinstance(gym_env.unwrapped, DirectMARLEnv):
        gym_env = multi_agent_to_single_agent(gym_env)
    task_env = gym_env.unwrapped
    env = DextrahBcVecEnvWrapper(gym_env, rl_device, clip_obs, clip_actions)

    vecenv.register(
        "DextrahBcWrapper",
        lambda config_name, num_actors, **kwargs: DextrahBcGpuEnv(config_name, num_actors, **kwargs),
    )
    env_configurations.register("rlgpu", {"vecenv_type": "DextrahBcWrapper", "env_creator": lambda **kwargs: env})

    player = _create_player(agent_cfg, env, init_checkpoint)
    player.model.train()

    total_steps = int(args_cli.approach_steps) + int(args_cli.close_steps) + int(args_cli.lift_steps)
    if total_steps <= 0:
        raise ValueError("At least one phase step is required.")

    obs_batches: list[torch.Tensor] = []
    action_batches: list[torch.Tensor] = []
    phase_batches: list[torch.Tensor] = []
    reset_batches: list[torch.Tensor] = []
    sample_batches: list[torch.Tensor] = []
    valid_counts: list[int] = []
    reset_rows: list[dict[str, Any]] = []

    for reset_index in range(int(args_cli.num_resets)):
        obs = _obs_policy_tensor(env.reset())
        valid = (task_env.grasp_prior_reset_success & task_env.grasp_prior_reset_quality_success).detach().clone()
        if not bool(valid.any()):
            raise RuntimeError(f"No valid pass7 resets in reset batch {reset_index}")
        valid_counts.append(int(valid.sum().detach().cpu()))
        reset_rows.append(
            {
                "reset_index": reset_index,
                "valid_count": int(valid.sum().detach().cpu()),
                "reset_success_mean": float(task_env.grasp_prior_reset_success.float().mean().detach().cpu()),
                "reset_quality_mean": float(task_env.grasp_prior_reset_quality_success.float().mean().detach().cpu()),
                "ee_to_cube_mean": float(task_env.ee_to_cube_dist.float().mean().detach().cpu()),
                "finger_center_to_cube_mean": float(task_env.finger_center_to_cube_dist.float().mean().detach().cpu()),
                "gripper_width_mean": float(task_env.gripper_width.float().mean().detach().cpu()),
                "sample_indices": _json_safe(task_env.grasp_prior_reset_sample_index.detach().cpu()),
            }
        )
        for step in range(total_steps):
            phase = _phase_for_step(step)
            reference = _reference_action(task_env, phase).clamp(-1.0, 1.0)
            obs_tensor = _obs_policy_tensor(obs).detach().clone()
            obs_batches.append(obs_tensor[valid].detach().clone())
            action_batches.append(reference[valid].detach().clone())
            phase_id = {"approach": 0, "close": 1, "lift": 2}[phase]
            phase_batches.append(torch.full((int(valid.sum()),), phase_id, dtype=torch.long, device=task_env.device))
            reset_batches.append(torch.full((int(valid.sum()),), reset_index, dtype=torch.long, device=task_env.device))
            sample_batches.append(task_env.grasp_prior_reset_sample_index[valid].detach().clone())
            step_out = env.step(reference)
            obs = step_out[0]

    obs_all = torch.cat(obs_batches, dim=0)
    obs_all = player.obs_to_torch(obs_all)
    action_all = torch.cat(action_batches, dim=0).clamp(-1.0, 1.0)
    phase_all = torch.cat(phase_batches, dim=0)
    reset_all = torch.cat(reset_batches, dim=0)
    sample_all = torch.cat(sample_batches, dim=0)
    train_idx, val_idx = _split_indices(reset_all, float(args_cli.validation_fraction))
    if train_idx.numel() == 0 or val_idx.numel() == 0:
        raise RuntimeError(f"Bad train/val split: train={train_idx.numel()} val={val_idx.numel()}")

    dataset_path = output_dir / "bc_dataset.pt"
    torch.save(
        {
            "obs": obs_all.detach().cpu(),
            "actions": action_all.detach().cpu(),
            "phase_ids": phase_all.detach().cpu(),
            "reset_ids": reset_all.detach().cpu(),
            "sample_indices": sample_all.detach().cpu(),
            "config": config,
        },
        dataset_path,
    )

    dataset_summary = {
        "num_samples": int(obs_all.shape[0]),
        "obs_dim": int(obs_all.shape[-1]),
        "action_dim": int(action_all.shape[-1]),
        "train_samples": int(train_idx.numel()),
        "val_samples": int(val_idx.numel()),
        "valid_counts_per_reset": valid_counts,
        "phase_counts": {
            "approach": int((phase_all == 0).sum().detach().cpu()),
            "close": int((phase_all == 1).sum().detach().cpu()),
            "lift": int((phase_all == 2).sum().detach().cpu()),
        },
        "sample_histogram": {str(int(k)): int(v) for k, v in zip(*torch.unique(sample_all.detach().cpu(), return_counts=True), strict=True)},
        "obs_stats": _tensor_stats(obs_all),
        "action_stats": _tensor_stats(action_all),
        "reset_rows": reset_rows,
        "dataset_path": str(dataset_path),
    }
    _write_json(output_dir / "dataset_summary.json", dataset_summary)

    with torch.inference_mode():
        initial_pred_val = _forward_mu(player, _prepare_player(player, obs_all[val_idx], obs_is_preprocessed=True))
    initial_summary, initial_rows = _prediction_metrics(initial_pred_val, action_all[val_idx], phase_all[val_idx], split="initial_val")

    trainable_params, trainable_names = _select_trainable_params(player.model, str(args_cli.train_scope))
    optimizer = torch.optim.Adam(trainable_params, lr=float(args_cli.learning_rate))
    losses: list[dict[str, float]] = []
    batch_size = max(1, int(args_cli.batch_size))
    for epoch in range(1, int(args_cli.train_epochs) + 1):
        player.model.train()
        perm = train_idx[torch.randperm(train_idx.numel(), device=train_idx.device)]
        total_loss = 0.0
        total_count = 0
        for start in range(0, int(perm.numel()), batch_size):
            batch_idx = perm[start : start + batch_size]
            pred = _forward_mu(player, obs_all[batch_idx])
            loss, train_loss_diag = _bc_loss(pred, action_all[batch_idx], phase_all[batch_idx])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
            optimizer.step()
            total_loss += float(loss.detach()) * int(batch_idx.numel())
            total_count += int(batch_idx.numel())
        player.model.eval()
        with torch.inference_mode():
            val_pred = _forward_mu(player, obs_all[val_idx])
            val_loss_tensor, val_loss_diag = _bc_loss(val_pred, action_all[val_idx], phase_all[val_idx])
            val_loss = float(val_loss_tensor)
        losses.append(
            {
                "epoch": float(epoch),
                "train_loss": total_loss / max(total_count, 1),
                "val_loss": val_loss,
                "train_base_mse_last_batch": train_loss_diag["base_mse"],
                "train_lift_z_sign_loss_last_batch": train_loss_diag["lift_z_sign_loss"],
                "val_base_mse": val_loss_diag["base_mse"],
                "val_lift_z_sign_loss": val_loss_diag["lift_z_sign_loss"],
            }
        )

    player.model.eval()
    with torch.inference_mode():
        pred_train = _forward_mu(player, obs_all[train_idx])
        pred_val = _forward_mu(player, obs_all[val_idx])
    train_summary, train_rows = _prediction_metrics(pred_train, action_all[train_idx], phase_all[train_idx], split="train")
    val_summary, val_rows = _prediction_metrics(pred_val, action_all[val_idx], phase_all[val_idx], split="val")
    metric_rows = initial_rows + train_rows + val_rows
    train_summary.update(initial_summary)
    train_summary.update(val_summary)
    train_summary["trainable_param_count"] = int(sum(param.numel() for param in trainable_params))
    train_summary["trainable_names"] = trainable_names
    train_summary["loss_history"] = losses

    bc_checkpoint_path = output_dir / "bc_pass7_action_warmstart.pth"
    loadability: dict[str, Any] | None = None
    saved_checkpoint = None
    if bool(args_cli.save_bc_checkpoint):
        _save_bc_checkpoint(init_checkpoint, player, bc_checkpoint_path)
        saved_checkpoint = str(bc_checkpoint_path)
        loadability = _loadability_check(agent_cfg, env, str(bc_checkpoint_path), obs_all[val_idx], action_all[val_idx])
    train_summary["bc_checkpoint_path"] = saved_checkpoint
    train_summary["loadability_check"] = loadability

    gate = {
        "val_mse_threshold": float(args_cli.gate_val_mse),
        "gripper_sign_threshold": float(args_cli.gate_gripper_sign),
        "lift_z_sign_threshold": float(args_cli.gate_lift_z_sign),
        "val_mse": train_summary.get("val_mse"),
        "val_gripper_sign_accuracy": train_summary.get("val_gripper_sign_accuracy"),
        "val_lift_z_sign_accuracy": train_summary.get("val_lift_z_sign_accuracy"),
        "checkpoint_loadable": loadability is not None and math.isfinite(float(loadability["mse"])),
    }
    gate["pass"] = bool(
        float(gate["val_mse"]) <= float(gate["val_mse_threshold"])
        and float(gate["val_gripper_sign_accuracy"]) >= float(gate["gripper_sign_threshold"])
        and float(gate["val_lift_z_sign_accuracy"]) >= float(gate["lift_z_sign_threshold"])
        and bool(gate["checkpoint_loadable"])
    )
    train_summary["gate"] = gate

    _write_csv(output_dir / "bc_action_metrics.csv", metric_rows)
    with (output_dir / "bc_loss_history.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = sorted({key for row in losses for key in row.keys()})
        for key in reversed(["epoch", "train_loss", "val_loss"]):
            if key in fieldnames:
                fieldnames.remove(key)
                fieldnames.insert(0, key)
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(losses)
    artifacts = _write_plots(output_dir, losses, metric_rows)
    artifacts.update(
        {
            "dataset_summary": str(output_dir / "dataset_summary.json"),
            "bc_action_metrics": str(output_dir / "bc_action_metrics.csv"),
            "bc_loss_history": str(output_dir / "bc_loss_history.csv"),
            "dataset": str(dataset_path),
        }
    )
    if saved_checkpoint is not None:
        artifacts["bc_checkpoint"] = saved_checkpoint

    report_path = output_dir / "REPORT.md"
    _write_report(
        report_path,
        config=config,
        dataset_summary=dataset_summary,
        train_summary=train_summary,
        gate=gate,
        artifacts=artifacts,
    )
    artifacts["report"] = str(report_path)

    payload = {
        "config": config,
        "dataset_summary": dataset_summary,
        "train_summary": train_summary,
        "gate": gate,
        "artifacts": artifacts,
    }
    _write_json(metrics_path, payload)
    _write_json(output_dir / "train_metrics.json", payload)
    print("[INFO] BC diagnostic summary:")
    print(json.dumps(_json_safe({"gate": gate, "train_summary": train_summary, "artifacts": artifacts}), indent=2, sort_keys=True))

    env.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        output_dir_arg = args_cli.output_dir or datetime.now().strftime("bc_pass7_error_%Y%m%d_%H%M%S")
        _write_exception_artifact(Path(output_dir_arg).expanduser().resolve(), exc)
        raise
    finally:
        simulation_app.close()
