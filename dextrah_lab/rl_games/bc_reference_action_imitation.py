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
    default="0,1,2,3,4,5,6",
    help="Comma-separated action dimensions used in the supervised loss.",
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
parser.add_argument("--seed", type=int, default=42, help="Random seed for env and supervised split.")
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


ACTION_LABELS = ("x", "y", "z", "rx", "ry", "rz", "gripper")


def _parse_loss_dims(raw: str, action_dim: int) -> list[int]:
    dims: list[int] = []
    for token in raw.split(","):
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


def _write_report(summary: dict[str, object], rows: list[dict[str, float | int | str]], path: Path) -> None:
    first = rows[0] if rows else {}
    last = rows[-1] if rows else {}
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
        f"- samples: `{summary.get('num_samples')}` train / `{summary.get('num_train')}` held-out / `{summary.get('num_val')}`",
        f"- observation dim: `{summary.get('obs_dim')}`, action dim: `{summary.get('action_dim')}`",
        f"- loss dims: `{summary.get('loss_dims')}`",
        f"- reference caveat: `curobo_validated={summary.get('curobo_validated')}`",
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
        "## Artifacts",
        "",
        f"- metrics: `{summary.get('metrics_path')}`",
        f"- curve CSV: `{summary.get('curve_csv_path')}`",
        f"- plot: `{summary.get('plot_path')}`",
        f"- dataset: `{summary.get('dataset_path')}`",
        "",
        "Next acceptance is not this loss alone: evaluate the output checkpoint at alpha `0.0`, `0.75`, and `1.0` with videos/action-semantics plots.",
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
    obs_records: list[torch.Tensor] = []
    reference_records: list[torch.Tensor] = []
    raw_records: list[torch.Tensor] = []
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

                obs_records.append(obs_t.detach().cpu())
                reference_records.append(reference_actions.detach().cpu())
                raw_records.append(raw_mus.detach().cpu())
                phase_records.append(getattr(task_env, "traj_phase_progress", torch.zeros(task_env.num_envs, device=task_env.device)).detach().cpu())
                lift_records.append(getattr(task_env, "cube_lift_height", torch.zeros(task_env.num_envs, device=task_env.device)).detach().cpu())
                success_records.append(getattr(task_env, "in_success_region", torch.zeros(task_env.num_envs, dtype=torch.bool, device=task_env.device)).detach().float().cpu())
                unsafe_records.append(getattr(task_env, "traj_target_safe_mask", torch.ones(task_env.num_envs, dtype=torch.bool, device=task_env.device)).detach().logical_not().float().cpu())

                step_out = env.step(reference_actions)
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

    obs_tensor = torch.cat(obs_records, dim=0).float()
    reference_tensor = torch.cat(reference_records, dim=0).float()
    raw_tensor = torch.cat(raw_records, dim=0).float()
    phase_tensor = torch.cat(phase_records, dim=0).float()
    lift_tensor = torch.cat(lift_records, dim=0).float()
    success_tensor = torch.cat(success_records, dim=0).float()
    unsafe_tensor = torch.cat(unsafe_records, dim=0).float()
    dataset = {
        "obs": obs_tensor,
        "reference_actions": reference_tensor,
        "raw_policy_actions_before": raw_tensor,
        "phase": phase_tensor,
        "cube_lift_height": lift_tensor,
        "success": success_tensor,
        "unsafe_target": unsafe_tensor,
        "loss_dims": torch.tensor(loss_dims, dtype=torch.long),
        "input_checkpoint": str(resume_path),
    }
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dataset, dataset_path)

    device = torch.device(rl_device)
    obs_tensor = obs_tensor.to(device)
    reference_tensor = reference_tensor.to(device)
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

    model = agent.model
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args_cli.learning_rate, weight_decay=args_cli.weight_decay)
    curve_rows: list[dict[str, float | int | str]] = []

    def evaluate_split(step: int) -> dict[str, float | int | str]:
        model.eval()
        with torch.no_grad():
            train_pred = _model_mus(model, obs_tensor[train_idx], action_dim, is_train=False).clamp(-1.0, 1.0)
            val_pred = _model_mus(model, obs_tensor[val_idx], action_dim, is_train=False).clamp(-1.0, 1.0)
        model.train()
        train_target = reference_tensor[train_idx]
        val_target = reference_tensor[val_idx]
        row: dict[str, float | int | str] = {"step": int(step)}
        row.update(_error_stats(train_pred, train_target, loss_dims, "train"))
        row.update(_error_stats(val_pred, val_target, loss_dims, "val"))
        return row

    curve_rows.append(evaluate_split(0))
    for step in range(1, args_cli.train_steps + 1):
        choice = train_idx[torch.randint(0, int(train_idx.numel()), (batch_size,), generator=generator, device=device)]
        pred = _model_mus(model, obs_tensor[choice], action_dim, is_train=True)
        target = reference_tensor[choice]
        loss = torch.mean(torch.square(pred[:, dims_t] - target[:, dims_t]))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        if step == args_cli.train_steps or step % max(1, args_cli.eval_interval) == 0:
            row = evaluate_split(step)
            row["last_batch_loss"] = float(loss.detach().cpu())
            curve_rows.append(row)
            print(json.dumps(row, sort_keys=True))

    ckpt = torch_ext.load_checkpoint(resume_path)
    ckpt["model"] = model.state_dict()
    if hasattr(model, "running_mean_std") and "running_mean_std" in ckpt:
        ckpt["running_mean_std"] = model.running_mean_std.state_dict()
    ckpt["bc_reference_action_imitation"] = {
        "input_checkpoint": str(resume_path),
        "num_samples": int(num_samples),
        "num_train": int(train_idx.numel()),
        "num_val": int(val_idx.numel()),
        "loss_dims": loss_dims,
        "train_steps": int(args_cli.train_steps),
        "learning_rate": float(args_cli.learning_rate),
        "dataset_path": str(dataset_path),
    }
    torch_ext.save_checkpoint(str(checkpoint_out), ckpt)

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
        "batch_size": int(batch_size),
        "learning_rate": float(args_cli.learning_rate),
        "validation_fraction": float(args_cli.validation_fraction),
        "curobo_validated": bool(reference_summary.get("curobo_validated", False)) if isinstance(reference_summary, dict) else False,
        "reference_summary": reference_summary,
        "dataset_reference_stats": _action_stats(reference_tensor.cpu(), "reference"),
        "dataset_raw_policy_before_stats": _action_stats(raw_tensor.cpu(), "raw_before"),
        "initial": curve_rows[0],
        "final": curve_rows[-1],
    }
    _write_csv(curve_rows, curve_csv_path)
    _draw_loss_plot(curve_rows, plot_path)
    metrics_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    _write_report(summary, curve_rows, report_path)
    print("[INFO] BC diagnostic summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
