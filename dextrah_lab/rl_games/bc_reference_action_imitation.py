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
        "## Per-Source Loss",
        "",
        *source_metric_lines,
        "",
        "## Artifacts",
        "",
        f"- metrics: `{summary.get('metrics_path')}`",
        f"- curve CSV: `{summary.get('curve_csv_path')}`",
        f"- plot: `{summary.get('plot_path')}`",
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
        "collection_action_source": args_cli.collection_action_source,
        "collection_teacher_alpha": collection_teacher_alpha,
        "rehearsal_dataset_paths": rehearsal_paths,
        "dataset_sources": source_metadata,
        "curobo_validated": bool(reference_summary.get("curobo_validated", False)) if isinstance(reference_summary, dict) else False,
        "reference_summary": reference_summary,
        "dataset_reference_stats": _action_stats(reference_tensor.cpu(), "reference"),
        "dataset_raw_policy_before_stats": _action_stats(raw_tensor.cpu(), "raw_before"),
        "dataset_applied_collection_stats": _action_stats(applied_tensor.cpu(), "applied_collection"),
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
