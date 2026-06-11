"""Render and measure Franka cube GraspGenX reset-prior geometry."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Franka-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--num_resets", type=int, default=3)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.08)
parser.add_argument("--grasp_prior_library_path", type=str, required=True)
parser.add_argument("--diagnostic_env_id", type=int, default=0)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.15, -1.05, 1.55))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.41, -0.08, 0.80))
parser.add_argument("--render_width", type=int, default=1280)
parser.add_argument("--render_height", type=int, default=720)
parser.add_argument("--video_fps", type=int, default=6)
parser.add_argument("--include_exact_close_check", action="store_true", default=False)
parser.add_argument("--exact_close_steps", type=int, default=80)
parser.add_argument("--exact_close_command_width", type=float, default=0.0)
parser.add_argument("--exact_close_approach_offset", type=float, default=0.0)
parser.add_argument("--exact_close_lateral_offset", type=float, default=0.0)
parser.add_argument("--render_all_resets", action="store_true", default=False)
parser.add_argument("--render_failed_exact_close", action="store_true", default=False)
parser.add_argument("--disable_fabric", action="store_true", default=False)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import numpy as np
import torch
from PIL import Image, ImageDraw

import isaaclab.sim as sim_utils
import isaaclab_tasks  # noqa: F401
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg
from isaaclab.utils import math as math_utils
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup  # noqa: F401
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup  # noqa: F401


def _as_float(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor | np.ndarray | list[float] | tuple[float, ...]) -> list[float]:
    if isinstance(value, torch.Tensor):
        flat = value.detach().float().cpu().flatten().tolist()
    elif isinstance(value, np.ndarray):
        flat = value.astype(float).flatten().tolist()
    else:
        flat = [float(v) for v in value]
    return [float(v) for v in flat]


def _finite_tree(value) -> bool:
    if isinstance(value, dict):
        return all(_finite_tree(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite_tree(v) for v in value)
    if isinstance(value, (int, bool)) or value is None or isinstance(value, str):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _quat_identity(device: str) -> torch.Tensor:
    return torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=device)


def _pos_in_root(task_env, env_id: int, pos_w: torch.Tensor) -> torch.Tensor:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    pos_b, _ = math_utils.subtract_frame_transforms(
        root_pos_w,
        root_quat_w,
        pos_w.unsqueeze(0),
        _quat_identity(task_env.device),
    )
    return pos_b[0]


def _world_from_env(task_env, env_id: int, pos_env: torch.Tensor) -> torch.Tensor:
    return pos_env + task_env.scene.env_origins[env_id]


def _mean_attr(task_env, name: str) -> float | None:
    if not hasattr(task_env, name):
        return None
    value = getattr(task_env, name)
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean_values(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.asarray(values, dtype=np.float64).mean())


def _contact_metrics(task_env, env_id: int) -> dict[str, object]:
    metrics: dict[str, object] = {"contact_available": False, "contact_flag": None}
    for asset_name in ("_cube", "_robot"):
        asset = getattr(task_env, asset_name, None)
        data = getattr(asset, "data", None)
        if data is None:
            continue
        label = asset_name.lstrip("_")
        for attr in ("net_contact_forces_w", "body_contact_forces_w", "contact_forces_w"):
            value = getattr(data, attr, None)
            if not isinstance(value, torch.Tensor):
                continue
            metrics["contact_available"] = True
            env_value = value[env_id] if value.ndim > 0 and value.shape[0] == task_env.num_envs else value
            force_norm = float(torch.norm(env_value.detach().float()).cpu())
            metrics[f"{label}_{attr}_norm"] = force_norm
            if metrics["contact_flag"] is None:
                metrics["contact_flag"] = force_norm > 1.0e-3
            else:
                metrics["contact_flag"] = bool(metrics["contact_flag"]) or force_norm > 1.0e-3
    return metrics


def _actual_tip_geometry(task_env, env_id: int) -> dict[str, object]:
    env_ids = torch.tensor([env_id], device=task_env.device, dtype=torch.long)
    task_env._compute_intermediate_values(env_ids)
    env_origin = task_env.scene.env_origins[env_id]
    cube_env = task_env.cube_pos[env_id]
    cube_w = cube_env + env_origin
    left_env = task_env.left_finger_pos[env_id]
    right_env = task_env.right_finger_pos[env_id]
    actual_ee_env = task_env.ee_pos[env_id]
    gripper_center_env = 0.5 * (left_env + right_env)
    gripper_half_axis = 0.5 * (left_env - right_env)
    left_tip_env = actual_ee_env + gripper_half_axis
    right_tip_env = actual_ee_env - gripper_half_axis
    tip_center_env = 0.5 * (left_tip_env + right_tip_env)
    left_tip_dist = torch.norm(left_tip_env - cube_env)
    right_tip_dist = torch.norm(right_tip_env - cube_env)
    tip_center_dist = torch.norm(tip_center_env - cube_env)
    tip_max_dist = torch.maximum(left_tip_dist, right_tip_dist)
    tip_table_clearance = torch.minimum(left_tip_env[2], right_tip_env[2]) - float(task_env.cfg.table_surface_z)
    return {
        "cube_pos_env": _tensor_list(cube_env),
        "cube_pos_w": _tensor_list(cube_w),
        "actual_ee_pos_env": _tensor_list(actual_ee_env),
        "actual_ee_pos_w": _tensor_list(actual_ee_env + env_origin),
        "left_finger_pos_env": _tensor_list(left_env),
        "right_finger_pos_env": _tensor_list(right_env),
        "left_finger_pos_w": _tensor_list(left_env + env_origin),
        "right_finger_pos_w": _tensor_list(right_env + env_origin),
        "gripper_center_pos_env": _tensor_list(gripper_center_env),
        "gripper_center_pos_w": _tensor_list(gripper_center_env + env_origin),
        "actual_left_tip_proxy_pos_env": _tensor_list(left_tip_env),
        "actual_right_tip_proxy_pos_env": _tensor_list(right_tip_env),
        "actual_left_tip_proxy_pos_w": _tensor_list(left_tip_env + env_origin),
        "actual_right_tip_proxy_pos_w": _tensor_list(right_tip_env + env_origin),
        "actual_tip_center_pos_env": _tensor_list(tip_center_env),
        "actual_tip_center_pos_w": _tensor_list(tip_center_env + env_origin),
        "relative_to_cube_env": {
            "left_finger": _tensor_list(left_env - cube_env),
            "right_finger": _tensor_list(right_env - cube_env),
            "gripper_center": _tensor_list(gripper_center_env - cube_env),
            "actual_ee": _tensor_list(actual_ee_env - cube_env),
            "actual_left_tip_proxy": _tensor_list(left_tip_env - cube_env),
            "actual_right_tip_proxy": _tensor_list(right_tip_env - cube_env),
            "actual_tip_center": _tensor_list(tip_center_env - cube_env),
        },
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "max_finger_to_cube_dist_m": _as_float(task_env.max_finger_to_cube_dist[env_id]),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "actual_left_tip_proxy_to_cube_dist_m": _as_float(left_tip_dist),
        "actual_right_tip_proxy_to_cube_dist_m": _as_float(right_tip_dist),
        "actual_tip_center_to_cube_dist_m": _as_float(tip_center_dist),
        "actual_tip_max_to_cube_dist_m": _as_float(tip_max_dist),
        "actual_tip_table_clearance_m": _as_float(tip_table_clearance),
    }


def _marker_cfg(path: str, color: tuple[float, float, float], radius: float) -> VisualizationMarkersCfg:
    return VisualizationMarkersCfg(
        prim_path=path,
        markers={
            "sphere": sim_utils.SphereCfg(
                radius=radius,
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=color),
            )
        },
    )


def _make_markers() -> dict[str, VisualizationMarkers]:
    return {
        "cube": VisualizationMarkers(_marker_cfg("/Visuals/GraspPriorResetDiag/CubeCenter", (0.0, 0.85, 1.0), 0.012)),
        "exact_tool": VisualizationMarkers(_marker_cfg("/Visuals/GraspPriorResetDiag/ExactTool", (0.0, 1.0, 0.15), 0.010)),
        "pregrasp_tool": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/PregraspTool", (1.0, 0.0, 0.85), 0.010)
        ),
        "exact_ee": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/ExactTcp", (0.0, 0.35, 1.0), 0.009)
        ),
        "pregrasp_ee": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/PregraspTcp", (1.0, 0.85, 0.0), 0.009)
        ),
        "close_target_ee": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/CloseTargetTcp", (1.0, 0.0, 0.0), 0.010)
        ),
        "left_finger": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/LeftFinger", (1.0, 0.15, 0.0), 0.008)
        ),
        "right_finger": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/RightFinger", (1.0, 0.55, 0.0), 0.008)
        ),
        "gripper_center": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/GripperCenter", (1.0, 1.0, 1.0), 0.007)
        ),
        "left_tip_proxy": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/LeftTipProxy", (0.0, 0.55, 1.0), 0.007)
        ),
        "right_tip_proxy": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/RightTipProxy", (0.0, 0.20, 1.0), 0.007)
        ),
        "exact_tip_proxy": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/ExactTipProxy", (0.1, 1.0, 0.75), 0.006)
        ),
        "offset": VisualizationMarkers(_marker_cfg("/Visuals/GraspPriorResetDiag/OffsetBeads", (1.0, 1.0, 0.0), 0.005)),
    }


def _visualize_markers(
    markers: dict[str, VisualizationMarkers],
    task_env,
    env_id: int,
    actual_geometry: dict[str, object] | None = None,
) -> None:
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_tool_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_tool_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    exact_ee_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    pregrasp_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    left_w = task_env.left_finger_pos[env_id] + env_origin
    right_w = task_env.right_finger_pos[env_id] + env_origin
    center_w = 0.5 * (left_w + right_w)
    if actual_geometry is not None:
        left_tip_w = torch.tensor(
            actual_geometry["actual_left_tip_proxy_pos_w"],
            dtype=torch.float32,
            device=task_env.device,
        )
        right_tip_w = torch.tensor(
            actual_geometry["actual_right_tip_proxy_pos_w"],
            dtype=torch.float32,
            device=task_env.device,
        )
        close_target_ee_w = torch.tensor(
            actual_geometry["target_ee_pos_w"],
            dtype=torch.float32,
            device=task_env.device,
        )
    else:
        left_tip_w = _world_from_env(task_env, env_id, task_env.grasp_prior_reset_left_tip_proxy_pos[env_id])
        right_tip_w = _world_from_env(task_env, env_id, task_env.grasp_prior_reset_right_tip_proxy_pos[env_id])
        close_target_ee_w = exact_ee_w
    exact_left_tip_w = _world_from_env(
        task_env, env_id, task_env.grasp_prior_reset_projected_exact_left_tip_proxy_pos[env_id]
    )
    exact_right_tip_w = _world_from_env(
        task_env, env_id, task_env.grasp_prior_reset_projected_exact_right_tip_proxy_pos[env_id]
    )
    offset_beads = torch.stack(
        (
            exact_tool_w + (pregrasp_tool_w - exact_tool_w) * 0.33,
            exact_tool_w + (pregrasp_tool_w - exact_tool_w) * 0.66,
            exact_ee_w + (pregrasp_ee_w - exact_ee_w) * 0.33,
            exact_ee_w + (pregrasp_ee_w - exact_ee_w) * 0.66,
        )
    )
    markers["cube"].visualize(cube_w.unsqueeze(0))
    markers["exact_tool"].visualize(exact_tool_w.unsqueeze(0))
    markers["pregrasp_tool"].visualize(pregrasp_tool_w.unsqueeze(0))
    markers["exact_ee"].visualize(exact_ee_w.unsqueeze(0))
    markers["pregrasp_ee"].visualize(pregrasp_ee_w.unsqueeze(0))
    markers["close_target_ee"].visualize(close_target_ee_w.unsqueeze(0))
    markers["left_finger"].visualize(left_w.unsqueeze(0))
    markers["right_finger"].visualize(right_w.unsqueeze(0))
    markers["gripper_center"].visualize(center_w.unsqueeze(0))
    markers["left_tip_proxy"].visualize(left_tip_w.unsqueeze(0))
    markers["right_tip_proxy"].visualize(right_tip_w.unsqueeze(0))
    markers["exact_tip_proxy"].visualize(torch.stack((exact_left_tip_w, exact_right_tip_w)))
    markers["offset"].visualize(offset_beads)


def _view_specs(base_eye: tuple[float, float, float], base_target: tuple[float, float, float]) -> list[dict[str, object]]:
    return [
        {"name": "first_oblique", "eye": base_eye, "target": base_target},
        {
            "name": "middle_top",
            "eye": (base_target[0] + 0.02, base_target[1] - 0.04, base_target[2] + 0.78),
            "target": base_target,
        },
        {
            "name": "last_side",
            "eye": (base_target[0] - 0.52, base_target[1] - 0.25, base_target[2] + 0.26),
            "target": base_target,
        },
    ]


def _set_camera(task_env, env_cfg, eye: tuple[float, float, float], target: tuple[float, float, float]) -> None:
    try:
        task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
    except Exception as exc:
        print(f"[WARN] Could not set reset diagnostic camera: {exc}", flush=True)


def _render_rgb(gym_env, task_env):
    for _ in range(6):
        task_env.sim.render()
    frame = None
    for _ in range(2):
        frame = gym_env.render()
    if isinstance(frame, list):
        frame = frame[0] if frame else None
    if frame is None:
        raise RuntimeError("gym_env.render() returned None for reset diagnostic frame")
    return np.asarray(frame)


def _overlay_frame(frame: np.ndarray, title: str, lines: list[str]) -> Image.Image:
    image = Image.fromarray(frame[..., :3].astype(np.uint8))
    draw = ImageDraw.Draw(image)
    margin = 12
    line_h = 17
    width = min(image.width - 2 * margin, 780)
    height = margin * 2 + line_h * (len(lines) + 2)
    draw.rectangle((margin, margin, margin + width, margin + height), fill=(0, 0, 0))
    draw.text((margin + 8, margin + 6), title, fill=(255, 255, 255))
    y = margin + 6 + line_h * 2
    for line in lines:
        draw.text((margin + 8, y), line, fill=(235, 235, 235))
        y += line_h
    return image


def _fmt_vec(values: list[float]) -> str:
    return "[" + ", ".join(f"{v:+.4f}" for v in values) + "]"


def _frame_lines(
    sample: dict[str, object],
    *,
    phase: str = "pregrasp",
    exact_close: dict[str, object] | None = None,
) -> list[str]:
    rel = sample["relative_to_cube_env"]
    if phase == "exact_close" and exact_close is not None:
        close_rel = exact_close["relative_to_cube_env"]
        contact_flag = exact_close.get("contact_flag")
        contact_text = "unavailable" if contact_flag is None else str(contact_flag)
        return [
            "PHASE 2: EXACT_GRASP_CLOSE_CHECK - scripted diagnostic, not the RL start state",
            "markers: cube cyan | panda_hand exact/pre magenta/green | TCP exact/pre blue/yellow | close target red | actual closed tip proxies blue/cyan",
            f"sample={sample['sample_index']} exact_ik={exact_close['exact_ik_success']} enclosure={exact_close['enclosure_success']} proxy_contact={exact_close['contact_proxy_success']}",
            f"close_cmd_width={exact_close['close_command_width_m']:.4f} observed_width={exact_close['observed_gripper_width_m']:.4f} contact_flag={contact_text}",
            f"target_offsets approach={exact_close['target_approach_offset_m']:+.4f} lateral={exact_close['target_lateral_offset_m']:+.4f}",
            f"cube_env={_fmt_vec(exact_close['cube_pos_env'])} cube_delta={exact_close['cube_pos_delta_m']:.4f} lift={exact_close['cube_lift_height_m']:.4f}",
            f"exact_pose_err pos={exact_close['exact_pos_error_m']:.4f} rot={exact_close['exact_rot_error_rad']:.4f} immediate_done={exact_close['immediate_done']}",
            f"TCP actual_rel={_fmt_vec(close_rel['actual_ee'])} tip_center_rel={_fmt_vec(close_rel['actual_tip_center'])}",
            f"tip_proxy rel L={_fmt_vec(close_rel['actual_left_tip_proxy'])} R={_fmt_vec(close_rel['actual_right_tip_proxy'])}",
            f"body_fingers rel L={_fmt_vec(close_rel['left_finger'])} R={_fmt_vec(close_rel['right_finger'])} center={_fmt_vec(close_rel['gripper_center'])}",
            f"tip dists center={exact_close['actual_tip_center_to_cube_dist_m']:.4f} max={exact_close['actual_tip_max_to_cube_dist_m']:.4f}",
            f"table_clearance tip={exact_close['actual_tip_table_clearance_m']:.4f} body={exact_close['finger_table_clearance_m']:.4f}",
            f"verdict={exact_close['verdict']} | pregrasp offset shown by yellow beads remains 0.03 m away from exact target",
        ]
    return [
        "PHASE 1: RESET_PREGRASP_RL_START - 3 cm offset, open gripper, policy starts here",
        "markers: cube cyan | panda_hand exact/pre magenta/green | TCP exact/pre blue/yellow | link origins orange | tip proxies blue/cyan",
        f"sample={sample['sample_index']} reset_success={sample['reset_success']} quality={sample['reset_grasp_quality_success']} immediate_done={sample['immediate_done']}",
        f"cube_env={_fmt_vec(sample['cube_pos_env'])} cube_w={_fmt_vec(sample['cube_pos_w'])}",
        f"panda_hand exact_rel={_fmt_vec(rel['exact_tool'])} pregrasp_rel={_fmt_vec(rel['pregrasp_tool'])}",
        f"TCP exact_rel={_fmt_vec(rel['exact_ee'])} pregrasp_rel={_fmt_vec(rel['target_ee'])} actual_rel={_fmt_vec(rel['actual_ee'])}",
        f"offset_dir_w={_fmt_vec(sample['pregrasp_offset_dir_w'])} offset_len={sample['pregrasp_offset_m']:.4f} radial_dot={sample['offset_radial_dot']:.4f}",
        f"body_fingers rel L={_fmt_vec(rel['left_finger'])} R={_fmt_vec(rel['right_finger'])} center={_fmt_vec(rel['gripper_center'])}",
        f"pregrasp_tip_proxy rel L={_fmt_vec(rel['left_tip_proxy'])} R={_fmt_vec(rel['right_tip_proxy'])}",
        f"exact_tip_proxy rel L={_fmt_vec(rel['projected_exact_left_tip_proxy'])} R={_fmt_vec(rel['projected_exact_right_tip_proxy'])}",
        f"width={sample['gripper_width_m']:.4f} cube={sample['cube_size_m']:.4f} margin={sample['open_width_margin_m']:.4f} body_table={sample['finger_table_clearance_m']:.4f}",
        f"tip_table pre={sample['pregrasp_tip_table_clearance_m']:.4f} exact={sample['projected_exact_tip_table_clearance_m']:.4f}",
        f"quality dists: exact_tcp_center={sample['projected_exact_tip_center_dist_m']:.4f} exact_tip_max={sample['projected_exact_tip_max_dist_m']:.4f} body_center_old={sample['projected_exact_finger_center_dist_m']:.4f}",
    ]


def _collect_sample(task_env, env_id: int, reset_index: int) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device))
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    exact_ee_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    target_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    left_env = task_env.left_finger_pos[env_id]
    right_env = task_env.right_finger_pos[env_id]
    left_tip_env = task_env.grasp_prior_reset_left_tip_proxy_pos[env_id]
    right_tip_env = task_env.grasp_prior_reset_right_tip_proxy_pos[env_id]
    projected_exact_left_tip_env = task_env.grasp_prior_reset_projected_exact_left_tip_proxy_pos[env_id]
    projected_exact_right_tip_env = task_env.grasp_prior_reset_projected_exact_right_tip_proxy_pos[env_id]
    cube_env = task_env.cube_pos[env_id]
    actual_ee_env = task_env.ee_pos[env_id]
    actual_ee_w = actual_ee_env + env_origin
    gripper_center_env = 0.5 * (left_env + right_env)
    exact_env = exact_w - env_origin
    pregrasp_env = pregrasp_w - env_origin
    exact_ee_env = exact_ee_w - env_origin
    target_ee_env = target_ee_w - env_origin
    pregrasp_offset = pregrasp_w - exact_w
    pregrasp_offset_m = torch.norm(pregrasp_offset)
    term, trunc = task_env._get_dones()
    immediate_done = bool((term[env_id] | trunc[env_id]).detach().cpu())
    sample_index = int(task_env.grasp_prior_reset_sample_index[env_id].detach().cpu())

    object_grasp_matrix = None
    if getattr(task_env, "_grasp_prior_grasps_object", None) is not None and sample_index >= 0:
        object_grasp_matrix = task_env._grasp_prior_grasps_object[sample_index].detach().cpu().tolist()

    sample = {
        "reset_index": int(reset_index),
        "env_id": int(env_id),
        "sample_index": sample_index,
        "reset_attempted": bool(task_env.grasp_prior_reset_attempted[env_id].detach().cpu()),
        "reset_success": bool(task_env.grasp_prior_reset_success[env_id].detach().cpu()),
        "reset_farther": bool(task_env.grasp_prior_reset_farther[env_id].detach().cpu()),
        "reset_grasp_quality_success": bool(task_env.grasp_prior_reset_quality_success[env_id].detach().cpu()),
        "immediate_done": immediate_done,
        "immediate_terminated": bool(term[env_id].detach().cpu()),
        "immediate_truncated": bool(trunc[env_id].detach().cpu()),
        "cube_size_m": float(task_env.cfg.cube_size),
        "cube_pos_env": _tensor_list(cube_env),
        "cube_pos_w": _tensor_list(cube_w),
        "cube_pos_root": _tensor_list(_pos_in_root(task_env, env_id, cube_w)),
        "cube_quat_w_wxyz": _tensor_list(task_env.cube_quat[env_id]),
        "exact_tool_pos_env": _tensor_list(exact_env),
        "exact_tool_pos_w": _tensor_list(exact_w),
        "exact_tool_pos_root": _tensor_list(_pos_in_root(task_env, env_id, exact_w)),
        "exact_tool_quat_w_wxyz": _tensor_list(task_env.grasp_prior_reset_exact_tool_quat_w[env_id]),
        "pregrasp_tool_pos_env": _tensor_list(pregrasp_env),
        "pregrasp_tool_pos_w": _tensor_list(pregrasp_w),
        "pregrasp_tool_pos_root": _tensor_list(_pos_in_root(task_env, env_id, pregrasp_w)),
        "pregrasp_tool_quat_w_wxyz": _tensor_list(task_env.grasp_prior_reset_pregrasp_tool_quat_w[env_id]),
        "exact_ee_pos_env": _tensor_list(exact_ee_env),
        "exact_ee_pos_w": _tensor_list(exact_ee_w),
        "exact_ee_pos_root": _tensor_list(_pos_in_root(task_env, env_id, exact_ee_w)),
        "exact_ee_quat_w_wxyz": _tensor_list(task_env.grasp_prior_reset_exact_ee_quat_w[env_id]),
        "target_ee_pos_env": _tensor_list(target_ee_env),
        "target_ee_pos_w": _tensor_list(target_ee_w),
        "target_ee_pos_root": _tensor_list(_pos_in_root(task_env, env_id, target_ee_w)),
        "target_ee_quat_w_wxyz": _tensor_list(task_env.grasp_prior_reset_target_ee_quat_w[env_id]),
        "actual_ee_pos_env": _tensor_list(actual_ee_env),
        "actual_ee_pos_w": _tensor_list(actual_ee_w),
        "actual_ee_pos_root": _tensor_list(_pos_in_root(task_env, env_id, actual_ee_w)),
        "left_finger_pos_env": _tensor_list(left_env),
        "right_finger_pos_env": _tensor_list(right_env),
        "left_finger_pos_w": _tensor_list(left_env + env_origin),
        "right_finger_pos_w": _tensor_list(right_env + env_origin),
        "gripper_center_pos_env": _tensor_list(gripper_center_env),
        "gripper_center_pos_w": _tensor_list(gripper_center_env + env_origin),
        "left_tip_proxy_pos_env": _tensor_list(left_tip_env),
        "right_tip_proxy_pos_env": _tensor_list(right_tip_env),
        "left_tip_proxy_pos_w": _tensor_list(left_tip_env + env_origin),
        "right_tip_proxy_pos_w": _tensor_list(right_tip_env + env_origin),
        "projected_exact_left_tip_proxy_pos_env": _tensor_list(projected_exact_left_tip_env),
        "projected_exact_right_tip_proxy_pos_env": _tensor_list(projected_exact_right_tip_env),
        "projected_exact_left_tip_proxy_pos_w": _tensor_list(projected_exact_left_tip_env + env_origin),
        "projected_exact_right_tip_proxy_pos_w": _tensor_list(projected_exact_right_tip_env + env_origin),
        "relative_to_cube_env": {
            "left_finger": _tensor_list(left_env - cube_env),
            "right_finger": _tensor_list(right_env - cube_env),
            "gripper_center": _tensor_list(gripper_center_env - cube_env),
            "exact_tool": _tensor_list(exact_env - cube_env),
            "pregrasp_tool": _tensor_list(pregrasp_env - cube_env),
            "exact_ee": _tensor_list(exact_ee_env - cube_env),
            "target_ee": _tensor_list(target_ee_env - cube_env),
            "actual_ee": _tensor_list(actual_ee_env - cube_env),
            "left_tip_proxy": _tensor_list(left_tip_env - cube_env),
            "right_tip_proxy": _tensor_list(right_tip_env - cube_env),
            "projected_exact_left_tip_proxy": _tensor_list(projected_exact_left_tip_env - cube_env),
            "projected_exact_right_tip_proxy": _tensor_list(projected_exact_right_tip_env - cube_env),
        },
        "pregrasp_offset_dir_w": _tensor_list(task_env.grasp_prior_reset_offset_dir_w[env_id]),
        "pregrasp_offset_m": float(pregrasp_offset_m.detach().cpu()),
        "exact_tool_dist_m": _as_float(task_env.grasp_prior_reset_exact_tool_dist[env_id]),
        "pregrasp_tool_dist_m": _as_float(task_env.grasp_prior_reset_pregrasp_tool_dist[env_id]),
        "exact_ee_dist_m": _as_float(task_env.grasp_prior_reset_exact_ee_dist[env_id]),
        "pregrasp_ee_dist_m": _as_float(task_env.grasp_prior_reset_pregrasp_ee_dist[env_id]),
        "pregrasp_minus_exact_tool_dist_m": _as_float(
            task_env.grasp_prior_reset_pregrasp_tool_dist[env_id]
            - task_env.grasp_prior_reset_exact_tool_dist[env_id]
        ),
        "pregrasp_minus_exact_ee_dist_m": _as_float(
            task_env.grasp_prior_reset_pregrasp_ee_dist[env_id] - task_env.grasp_prior_reset_exact_ee_dist[env_id]
        ),
        "reset_pos_error_m": _as_float(task_env.grasp_prior_reset_pos_error[env_id]),
        "reset_rot_error_rad": _as_float(task_env.grasp_prior_reset_rot_error[env_id]),
        "offset_radial_dot": _as_float(task_env.grasp_prior_reset_offset_radial_dot[env_id]),
        "offset_radial_angle_rad": _as_float(task_env.grasp_prior_reset_offset_radial_angle[env_id]),
        "offset_radial_angle_deg": math.degrees(_as_float(task_env.grasp_prior_reset_offset_radial_angle[env_id])),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "open_width_margin_m": _as_float(task_env.grasp_prior_reset_open_width_margin[env_id]),
        "gripper_width_fits_cube": bool(task_env.grasp_prior_reset_open_width_margin[env_id].detach().cpu() >= 0.0),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "max_finger_to_cube_dist_m": _as_float(task_env.max_finger_to_cube_dist[env_id]),
        "projected_exact_finger_center_dist_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_finger_center_dist[env_id]
        ),
        "projected_exact_tip_center_dist_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_tip_center_dist[env_id]
        ),
        "projected_exact_tip_max_dist_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_tip_max_dist[env_id]
        ),
        "pregrasp_tip_table_clearance_m": _as_float(
            task_env.grasp_prior_reset_pregrasp_tip_table_clearance[env_id]
        ),
        "projected_exact_tip_table_clearance_m": _as_float(
            task_env.grasp_prior_reset_projected_exact_tip_table_clearance[env_id]
        ),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "root_pos_w": _tensor_list(task_env._robot.data.root_pos_w[env_id]),
        "root_quat_w_wxyz": _tensor_list(task_env._robot.data.root_quat_w[env_id]),
        "object_grasp_matrix": object_grasp_matrix,
    }
    return sample


def _run_exact_close_check(
    task_env,
    env_id: int,
    *,
    close_steps: int,
    close_command_width: float,
    approach_offset: float,
    lateral_offset: float,
) -> dict[str, object]:
    env_ids = torch.tensor([env_id], dtype=torch.long, device=task_env.device)
    joint_pos = task_env._robot.data.joint_pos[env_ids].clone()
    joint_vel = torch.zeros_like(joint_pos)
    root_pos_w = task_env._robot.data.root_pos_w[env_ids]
    root_quat_w = task_env._robot.data.root_quat_w[env_ids]
    original_exact_ee_pos_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_ids]
    exact_ee_quat_w = task_env.grasp_prior_reset_exact_ee_quat_w[env_ids]
    approach_axis_w = task_env.grasp_prior_reset_offset_dir_w[env_ids]
    approach_axis_w = approach_axis_w / torch.clamp(torch.norm(approach_axis_w, dim=-1, keepdim=True), min=1.0e-6)
    left_tip_env = task_env.grasp_prior_reset_projected_exact_left_tip_proxy_pos[env_ids]
    right_tip_env = task_env.grasp_prior_reset_projected_exact_right_tip_proxy_pos[env_ids]
    lateral_axis_w = left_tip_env - right_tip_env
    lateral_axis_w = lateral_axis_w / torch.clamp(torch.norm(lateral_axis_w, dim=-1, keepdim=True), min=1.0e-6)
    target_ee_pos_w = (
        original_exact_ee_pos_w
        + float(approach_offset) * approach_axis_w
        + float(lateral_offset) * lateral_axis_w
    )
    target_ee_pos_b, target_ee_quat_b = math_utils.subtract_frame_transforms(
        root_pos_w,
        root_quat_w,
        target_ee_pos_w,
        exact_ee_quat_w,
    )
    exact_joint_pos, ik_success, pos_error_norm, rot_error_norm = task_env._solve_reset_ik(
        env_ids,
        joint_pos,
        joint_vel,
        target_ee_pos_b,
        target_ee_quat_b,
    )
    exact_joint_pos[:, task_env.finger_joint_ids] = task_env._robot.data.default_joint_pos[env_ids][
        :, task_env.finger_joint_ids
    ]
    task_env._sync_reset_joint_state(env_ids, exact_joint_pos, joint_vel, update_buffers=True)
    exact_open_geometry = _actual_tip_geometry(task_env, env_id)
    cube_before_close_env = task_env.cube_pos[env_id].detach().clone()

    close_width = max(float(close_command_width), 0.0)
    close_target_per_finger = min(0.5 * close_width, 0.04)
    close_joint_pos = exact_joint_pos.clone()
    close_joint_pos[:, task_env.finger_joint_ids] = close_target_per_finger
    task_env.robot_dof_targets[env_ids] = close_joint_pos
    task_env.arm_joint_pos_target[env_ids] = close_joint_pos[:, task_env.arm_joint_ids]
    task_env.finger_joint_pos_target[env_ids] = close_joint_pos[:, task_env.finger_joint_ids]
    for _ in range(max(int(close_steps), 0)):
        task_env._robot.set_joint_position_target(close_joint_pos, env_ids=env_ids)
        task_env.scene.write_data_to_sim()
        task_env.sim.step(render=False)
        task_env.scene.update(dt=task_env.sim.cfg.dt)
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values(env_ids)

    close_geometry = _actual_tip_geometry(task_env, env_id)
    term, trunc = task_env._get_dones()
    immediate_done = bool((term[env_id] | trunc[env_id]).detach().cpu())
    cube_after_close_env = task_env.cube_pos[env_id].detach().clone()
    cube_pos_delta = torch.norm(cube_after_close_env - cube_before_close_env)
    cube_size = float(task_env.cfg.cube_size)
    observed_width = float(close_geometry["gripper_width_m"])
    width_contact_proxy = (observed_width >= 0.75 * cube_size) and (observed_width <= float(task_env.cfg.max_gripper_width) + 0.01)
    tip_center_close = float(close_geometry["actual_tip_center_to_cube_dist_m"]) <= 0.80 * cube_size
    tip_max_close = float(close_geometry["actual_tip_max_to_cube_dist_m"]) <= 1.40 * cube_size
    table_clearance_ok = float(close_geometry["actual_tip_table_clearance_m"]) >= float(
        task_env.cfg.finger_table_penetration_termination_margin
    )
    contact_proxy_success = bool(width_contact_proxy and tip_center_close and tip_max_close)
    exact_ik_success = bool(ik_success[0].detach().cpu())
    enclosure_success = bool(
        exact_ik_success
        and contact_proxy_success
        and table_clearance_ok
        and not immediate_done
        and torch.isfinite(cube_pos_delta).item()
    )
    verdict = "PASS" if enclosure_success else "FAIL"
    contact = _contact_metrics(task_env, env_id)
    result = {
        "enabled": True,
        "exact_ik_success": exact_ik_success,
        "exact_pos_error_m": _as_float(pos_error_norm[0]),
        "exact_rot_error_rad": _as_float(rot_error_norm[0]),
        "target_approach_offset_m": float(approach_offset),
        "target_lateral_offset_m": float(lateral_offset),
        "target_approach_axis_w": _tensor_list(approach_axis_w[0]),
        "target_lateral_axis_w": _tensor_list(lateral_axis_w[0]),
        "original_exact_ee_pos_w": _tensor_list(original_exact_ee_pos_w[0]),
        "target_ee_pos_w": _tensor_list(target_ee_pos_w[0]),
        "target_ee_pos_env": _tensor_list(target_ee_pos_w[0] - task_env.scene.env_origins[env_id]),
        "target_ee_pos_root": _tensor_list(_pos_in_root(task_env, env_id, target_ee_pos_w[0])),
        "target_ee_quat_w_wxyz": _tensor_list(exact_ee_quat_w[0]),
        "close_steps": int(close_steps),
        "close_command_width_m": close_width,
        "close_target_per_finger_m": close_target_per_finger,
        "observed_gripper_width_m": observed_width,
        "width_contact_proxy": bool(width_contact_proxy),
        "tip_center_close_proxy": bool(tip_center_close),
        "tip_max_close_proxy": bool(tip_max_close),
        "table_clearance_ok": bool(table_clearance_ok),
        "contact_proxy_success": contact_proxy_success,
        "enclosure_success": enclosure_success,
        "verdict": verdict,
        "immediate_done": immediate_done,
        "immediate_terminated": bool(term[env_id].detach().cpu()),
        "immediate_truncated": bool(trunc[env_id].detach().cpu()),
        "cube_pos_before_close_env": _tensor_list(cube_before_close_env),
        "cube_pos_after_close_env": _tensor_list(cube_after_close_env),
        "cube_pos_delta_m": _as_float(cube_pos_delta),
        "cube_lift_height_m": _as_float(task_env.cube_lift_height[env_id]),
        "exact_open_geometry": exact_open_geometry,
        **close_geometry,
        **contact,
    }
    return result


def _write_csv(path: Path, samples: list[dict[str, object]]) -> None:
    exact_close_scalar_keys = [
        "enabled",
        "exact_ik_success",
        "exact_pos_error_m",
        "exact_rot_error_rad",
        "target_approach_offset_m",
        "target_lateral_offset_m",
        "close_steps",
        "close_command_width_m",
        "close_target_per_finger_m",
        "observed_gripper_width_m",
        "width_contact_proxy",
        "tip_center_close_proxy",
        "tip_max_close_proxy",
        "table_clearance_ok",
        "contact_proxy_success",
        "enclosure_success",
        "verdict",
        "immediate_done",
        "cube_pos_delta_m",
        "cube_lift_height_m",
        "actual_tip_center_to_cube_dist_m",
        "actual_tip_max_to_cube_dist_m",
        "actual_tip_table_clearance_m",
        "finger_table_clearance_m",
        "contact_available",
        "contact_flag",
    ]
    scalar_keys = [
        "reset_index",
        "env_id",
        "sample_index",
        "reset_attempted",
        "reset_success",
        "reset_farther",
        "reset_grasp_quality_success",
        "immediate_done",
        "reset_pos_error_m",
        "reset_rot_error_rad",
        "pregrasp_offset_m",
        "exact_tool_dist_m",
        "pregrasp_tool_dist_m",
        "pregrasp_minus_exact_tool_dist_m",
        "exact_ee_dist_m",
        "pregrasp_ee_dist_m",
        "pregrasp_minus_exact_ee_dist_m",
        "offset_radial_dot",
        "offset_radial_angle_deg",
        "gripper_width_m",
        "open_width_margin_m",
        "gripper_width_fits_cube",
        "finger_center_to_cube_dist_m",
        "left_finger_to_cube_dist_m",
        "right_finger_to_cube_dist_m",
        "max_finger_to_cube_dist_m",
        "projected_exact_finger_center_dist_m",
        "projected_exact_tip_center_dist_m",
        "projected_exact_tip_max_dist_m",
        "pregrasp_tip_table_clearance_m",
        "projected_exact_tip_table_clearance_m",
        "finger_table_clearance_m",
    ] + [f"exact_close_{key}" for key in exact_close_scalar_keys]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scalar_keys)
        writer.writeheader()
        for sample in samples:
            row = {key: sample.get(key) for key in scalar_keys}
            exact_close = sample.get("exact_close_check")
            if isinstance(exact_close, dict):
                for key in exact_close_scalar_keys:
                    row[f"exact_close_{key}"] = exact_close.get(key)
            writer.writerow(row)


def _write_video(frames: list[Path], video_path: Path, fps: int) -> bool:
    if not frames or shutil.which("ffmpeg") is None:
        return False
    list_path = video_path.with_suffix(".ffconcat")
    lines = ["ffconcat version 1.0\n"]
    duration = 1.0 / max(int(fps), 1)
    repeated = []
    for frame in frames:
        for _ in range(max(int(fps) * 2, 1)):
            repeated.append(frame)
    for frame in repeated:
        lines.append(f"file '{frame.resolve()}'\n")
        lines.append(f"duration {duration:.6f}\n")
    lines.append(f"file '{repeated[-1].resolve()}'\n")
    list_path.write_text("".join(lines), encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"[WARN] ffmpeg video encode failed: {result.stderr.strip()}", flush=True)
        return False
    return True


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_prior_diag_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "reset_geometry.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "reset_geometry.csv"
    video_path = output_dir / "reset_geometry.mp4"

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.sim.device = args_cli.device
    env_cfg.cube_spawn_xy_randomization = args_cli.cube_spawn_xy_randomization
    env_cfg.grasp_prior_reset_enabled = True
    env_cfg.grasp_prior_library_path = args_cli.grasp_prior_library_path
    if hasattr(env_cfg.viewer, "resolution"):
        env_cfg.viewer.resolution = (args_cli.render_width, args_cli.render_height)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    task_env = gym_env.unwrapped
    env_id = int(args_cli.diagnostic_env_id)
    if env_id < 0 or env_id >= task_env.num_envs:
        raise ValueError(f"--diagnostic_env_id must be in [0, {task_env.num_envs}), got {env_id}")
    markers = _make_markers()

    samples: list[dict[str, object]] = []
    rendered_frames: list[Path] = []
    env_closed = False
    try:
        view_specs = _view_specs(tuple(args_cli.camera_eye), tuple(args_cli.camera_target))
        for reset_index in range(max(int(args_cli.num_resets), 1)):
            reset_out = gym_env.reset(seed=args_cli.seed + reset_index)
            _ = reset_out[0] if isinstance(reset_out, tuple) else reset_out
            sample = _collect_sample(task_env, env_id, reset_index)
            samples.append(sample)
            print(
                "[RESET_DIAG] "
                f"reset={reset_index} sample={sample['sample_index']} "
                f"success={sample['reset_success']} quality={sample['reset_grasp_quality_success']} "
                f"width={sample['gripper_width_m']:.5f} margin={sample['open_width_margin_m']:.5f} "
                f"offset_dot={sample['offset_radial_dot']:.5f} "
                f"body_center={sample['projected_exact_finger_center_dist_m']:.5f} "
                f"tip_center={sample['projected_exact_tip_center_dist_m']:.5f} "
                f"tip_max={sample['projected_exact_tip_max_dist_m']:.5f} "
                f"immediate_done={sample['immediate_done']}",
                flush=True,
            )
            render_pregrasp = reset_index == 0 or bool(args_cli.render_all_resets)
            if render_pregrasp:
                _visualize_markers(markers, task_env, env_id)
                env_origin = task_env.scene.env_origins[env_id].detach().cpu().tolist()
                for view in view_specs:
                    eye = tuple(float(view["eye"][idx]) + float(env_origin[idx]) for idx in range(3))
                    target = tuple(float(view["target"][idx]) + float(env_origin[idx]) for idx in range(3))
                    _set_camera(task_env, env_cfg, eye, target)
                    frame = _render_rgb(gym_env, task_env)
                    title = (
                        f"Franka cube GGX reset/pregrasp RL start | reset {reset_index} | "
                        f"view {view['name']} | seed {args_cli.seed}"
                    )
                    image = _overlay_frame(frame, title, _frame_lines(sample, phase="pregrasp"))
                    frame_path = frames_dir / f"reset_{reset_index:03d}_phase1_pregrasp_{view['name']}.png"
                    image.save(frame_path)
                    rendered_frames.append(frame_path)
            if args_cli.include_exact_close_check:
                exact_close = _run_exact_close_check(
                    task_env,
                    env_id,
                    close_steps=args_cli.exact_close_steps,
                    close_command_width=args_cli.exact_close_command_width,
                    approach_offset=args_cli.exact_close_approach_offset,
                    lateral_offset=args_cli.exact_close_lateral_offset,
                )
                sample["exact_close_check"] = exact_close
                print(
                    "[EXACT_CLOSE_DIAG] "
                    f"reset={reset_index} sample={sample['sample_index']} "
                    f"ik={exact_close['exact_ik_success']} enclosure={exact_close['enclosure_success']} "
                    f"proxy_contact={exact_close['contact_proxy_success']} "
                    f"width={exact_close['observed_gripper_width_m']:.5f} "
                    f"cmd_width={exact_close['close_command_width_m']:.5f} "
                    f"tip_center={exact_close['actual_tip_center_to_cube_dist_m']:.5f} "
                    f"tip_max={exact_close['actual_tip_max_to_cube_dist_m']:.5f} "
                    f"tip_clearance={exact_close['actual_tip_table_clearance_m']:.5f} "
                    f"cube_delta={exact_close['cube_pos_delta_m']:.5f} "
                    f"immediate_done={exact_close['immediate_done']} verdict={exact_close['verdict']}",
                    flush=True,
                )
                render_exact_close = (
                    reset_index == 0
                    or bool(args_cli.render_all_resets)
                    or (bool(args_cli.render_failed_exact_close) and not bool(exact_close["enclosure_success"]))
                )
                if render_exact_close:
                    _visualize_markers(markers, task_env, env_id, actual_geometry=exact_close)
                    env_origin = task_env.scene.env_origins[env_id].detach().cpu().tolist()
                    for view in view_specs:
                        eye = tuple(float(view["eye"][idx]) + float(env_origin[idx]) for idx in range(3))
                        target = tuple(float(view["target"][idx]) + float(env_origin[idx]) for idx in range(3))
                        _set_camera(task_env, env_cfg, eye, target)
                        frame = _render_rgb(gym_env, task_env)
                        title = (
                            f"Franka cube GGX exact grasp close check | reset {reset_index} | "
                            f"view {view['name']} | seed {args_cli.seed}"
                        )
                        image = _overlay_frame(
                            frame,
                            title,
                            _frame_lines(sample, phase="exact_close", exact_close=exact_close),
                        )
                        frame_path = frames_dir / f"reset_{reset_index:03d}_phase2_exact_close_{view['name']}.png"
                        image.save(frame_path)
                        rendered_frames.append(frame_path)
    finally:
        gym_env.close()
        env_closed = True

    exact_checks = [
        sample["exact_close_check"]
        for sample in samples
        if isinstance(sample.get("exact_close_check"), dict)
    ]
    exact_close_enabled = bool(args_cli.include_exact_close_check)
    reset_gate_pass = bool(
        samples
        and all(bool(sample["reset_grasp_quality_success"]) for sample in samples)
        and all(not bool(sample["immediate_done"]) for sample in samples)
    )
    exact_close_gate_pass = bool(
        (not exact_close_enabled)
        or (
            exact_checks
            and len(exact_checks) == len(samples)
            and all(bool(check["enclosure_success"]) for check in exact_checks)
        )
    )
    summary = {
        "task": args_cli.task,
        "code_commit_env": os.environ.get("CODE_COMMIT", ""),
        "num_envs": int(args_cli.num_envs),
        "num_resets": len(samples),
        "seed": int(args_cli.seed),
        "diagnostic_env_id": env_id,
        "grasp_prior_library_path": args_cli.grasp_prior_library_path,
        "cube_spawn_xy_randomization": float(args_cli.cube_spawn_xy_randomization),
        "prior_enabled": True,
        "exact_close_check_enabled": exact_close_enabled,
        "exact_close_steps": int(args_cli.exact_close_steps),
        "exact_close_command_width_m": float(args_cli.exact_close_command_width),
        "exact_close_approach_offset_m": float(args_cli.exact_close_approach_offset),
        "exact_close_lateral_offset_m": float(args_cli.exact_close_lateral_offset),
        "render_all_resets": bool(args_cli.render_all_resets),
        "render_failed_exact_close": bool(args_cli.render_failed_exact_close),
        "pregrasp_reset_gate_pass": reset_gate_pass,
        "exact_close_gate_pass": exact_close_gate_pass,
        "rl_relaunch_gate_verdict": "PASS" if reset_gate_pass and exact_close_gate_pass else "FAIL",
        "attempt_rate": sum(1 for s in samples if s["reset_attempted"]) / len(samples) if samples else 0.0,
        "reset_success_rate": sum(1 for s in samples if s["reset_success"]) / len(samples) if samples else 0.0,
        "reset_quality_success_rate": sum(1 for s in samples if s["reset_grasp_quality_success"]) / len(samples)
        if samples
        else 0.0,
        "farther_rate": sum(1 for s in samples if s["reset_farther"]) / len(samples) if samples else 0.0,
        "immediate_done_rate": sum(1 for s in samples if s["immediate_done"]) / len(samples) if samples else 0.0,
        "all_scalars_finite": all(_finite_tree(sample) for sample in samples),
        "gripper_width_mean_m": _mean_attr(task_env, "grasp_prior_reset_gripper_width"),
        "open_width_margin_mean_m": _mean_attr(task_env, "grasp_prior_reset_open_width_margin"),
        "offset_radial_dot_mean": _mean_attr(task_env, "grasp_prior_reset_offset_radial_dot"),
        "projected_exact_finger_center_dist_mean_m": _mean_attr(
            task_env,
            "grasp_prior_reset_projected_exact_finger_center_dist",
        ),
        "projected_exact_tip_center_dist_mean_m": _mean_attr(
            task_env,
            "grasp_prior_reset_projected_exact_tip_center_dist",
        ),
        "projected_exact_tip_max_dist_mean_m": _mean_attr(
            task_env,
            "grasp_prior_reset_projected_exact_tip_max_dist",
        ),
        "pregrasp_tip_table_clearance_mean_m": _mean_attr(
            task_env,
            "grasp_prior_reset_pregrasp_tip_table_clearance",
        ),
        "projected_exact_tip_table_clearance_mean_m": _mean_attr(
            task_env,
            "grasp_prior_reset_projected_exact_tip_table_clearance",
        ),
        "exact_close_ik_success_rate": sum(1 for c in exact_checks if c["exact_ik_success"]) / len(exact_checks)
        if exact_checks
        else None,
        "exact_close_enclosure_success_rate": sum(1 for c in exact_checks if c["enclosure_success"])
        / len(exact_checks)
        if exact_checks
        else None,
        "exact_close_contact_proxy_success_rate": sum(1 for c in exact_checks if c["contact_proxy_success"])
        / len(exact_checks)
        if exact_checks
        else None,
        "exact_close_immediate_done_rate": sum(1 for c in exact_checks if c["immediate_done"]) / len(exact_checks)
        if exact_checks
        else None,
        "exact_close_observed_gripper_width_mean_m": _mean_values(
            [float(c["observed_gripper_width_m"]) for c in exact_checks]
        ),
        "exact_close_tip_center_dist_mean_m": _mean_values(
            [float(c["actual_tip_center_to_cube_dist_m"]) for c in exact_checks]
        ),
        "exact_close_tip_max_dist_mean_m": _mean_values(
            [float(c["actual_tip_max_to_cube_dist_m"]) for c in exact_checks]
        ),
        "exact_close_tip_table_clearance_mean_m": _mean_values(
            [float(c["actual_tip_table_clearance_m"]) for c in exact_checks]
        ),
        "exact_close_cube_pos_delta_mean_m": _mean_values([float(c["cube_pos_delta_m"]) for c in exact_checks]),
        "frame_paths": [str(path) for path in rendered_frames],
        "video_path": str(video_path) if video_path.exists() else None,
        "csv_path": str(csv_path),
        "metrics_path": str(metrics_path),
        "env_closed": env_closed,
        "notes": [
            "reset_success measures IK target tracking plus farther/table checks, not grasp-quality geometry",
            "reset_grasp_quality_success additionally requires open width >= cube size, offset away from cube, and a projected exact TCP/fingertip proxy near the cube",
            "panda_hand/tool and DEXTRAH TCP/EE are both reported because the task controls panda_hand plus ee_offset_pos",
            "body-origin finger distances are retained for reward consistency but are not used alone as grasp-quality geometry",
            "positions are reported in world, env-local, and robot-root frames where applicable",
            "exact_close_check, when enabled, is a diagnostic-only scripted move from pregrasp to exact pose followed by a close command; it is not part of the RL reset path",
        ],
    }
    payload = {
        "summary": summary,
        "samples": samples,
        "library_metadata": getattr(task_env, "_grasp_prior_metadata", {}),
        "grasp_to_tool_transform": getattr(task_env, "_grasp_prior_grasp_to_tool", torch.eye(4)).detach().cpu().tolist(),
    }
    _write_csv(csv_path, samples)
    video_written = _write_video(rendered_frames, video_path, args_cli.video_fps)
    payload["summary"]["video_path"] = str(video_path) if video_written else None
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[INFO] Wrote reset geometry metrics to {metrics_path}", flush=True)
    print(f"[INFO] Wrote reset geometry CSV to {csv_path}", flush=True)
    if video_written:
        print(f"[INFO] Wrote reset geometry video to {video_path}", flush=True)
    else:
        print("[WARN] Reset geometry video was not written; labeled PNG frames are available.", flush=True)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)

    if summary["attempt_rate"] < 1.0 or not summary["all_scalars_finite"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
