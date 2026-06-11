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
parser.add_argument("--include_oracle_close_lift_check", action="store_true", default=False)
parser.add_argument("--oracle_approach_steps", type=int, default=16)
parser.add_argument("--oracle_close_steps", type=int, default=50)
parser.add_argument("--oracle_lift_steps", type=int, default=80)
parser.add_argument("--oracle_hold_steps", type=int, default=30)
parser.add_argument("--oracle_approach_distance", type=float, default=0.030)
parser.add_argument(
    "--oracle_approach_mode",
    choices=("fixed_direction", "proportional_exact"),
    default="fixed_direction",
)
parser.add_argument("--oracle_proportional_gain", type=float, default=1.0)
parser.add_argument("--oracle_max_position_action", type=float, default=1.0)
parser.add_argument("--oracle_track_orientation", action="store_true", default=False)
parser.add_argument("--oracle_close_width", type=float, default=0.055)
parser.add_argument("--oracle_lift_action_z", type=float, default=0.05)
parser.add_argument("--oracle_lift_success_height", type=float, default=0.020)
parser.add_argument("--oracle_render_interval", type=int, default=12)
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


def _gripper_action_for_width(width: float, max_width: float) -> float:
    if max_width <= 1.0e-6:
        return -1.0
    return float(np.clip(2.0 * float(width) / float(max_width) - 1.0, -1.0, 1.0))


def _ee_pose_b(task_env, env_id: int) -> tuple[torch.Tensor, torch.Tensor]:
    ee_pos_b, ee_quat_b = task_env._compute_ee_frame_pose()
    return ee_pos_b[env_id], ee_quat_b[env_id]


def _ee_pose_w_from_b(
    task_env,
    env_id: int,
    ee_pos_b: torch.Tensor,
    ee_quat_b: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    ee_pos_w, ee_quat_w = math_utils.combine_frame_transforms(
        root_pos_w,
        root_quat_w,
        ee_pos_b.unsqueeze(0),
        ee_quat_b.unsqueeze(0),
    )
    return ee_pos_w[0], ee_quat_w[0]


def _exact_ee_pose_b(task_env, env_id: int) -> tuple[torch.Tensor, torch.Tensor]:
    root_pos_w = task_env._robot.data.root_pos_w[env_id].unsqueeze(0)
    root_quat_w = task_env._robot.data.root_quat_w[env_id].unsqueeze(0)
    exact_ee_pos_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id].unsqueeze(0)
    exact_ee_quat_w = task_env.grasp_prior_reset_exact_ee_quat_w[env_id].unsqueeze(0)
    exact_ee_pos_b, exact_ee_quat_b = math_utils.subtract_frame_transforms(
        root_pos_w,
        root_quat_w,
        exact_ee_pos_w,
        exact_ee_quat_w,
    )
    return exact_ee_pos_b[0], exact_ee_quat_b[0]


def _bounded_exact_tracking_action(
    task_env,
    env_id: int,
    *,
    gripper_action: float,
) -> torch.Tensor:
    action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    current_ee_pos_b, current_ee_quat_b = _ee_pose_b(task_env, env_id)
    exact_ee_pos_b, exact_ee_quat_b = _exact_ee_pose_b(task_env, env_id)
    pos_error_b = exact_ee_pos_b - current_ee_pos_b
    gain = float(args_cli.oracle_proportional_gain)
    max_position_action = max(float(args_cli.oracle_max_position_action), 0.0)
    pos_action = gain * pos_error_b / torch.clamp(task_env.action_scale[:3], min=1.0e-6)
    action[env_id, 0:3] = torch.clamp(pos_action, min=-max_position_action, max=max_position_action)
    if bool(args_cli.oracle_track_orientation):
        _, rot_error_b = math_utils.compute_pose_error(
            current_ee_pos_b.unsqueeze(0),
            current_ee_quat_b.unsqueeze(0),
            exact_ee_pos_b.unsqueeze(0),
            exact_ee_quat_b.unsqueeze(0),
            rot_error_type="axis_angle",
        )
        rot_action = gain * rot_error_b[0] / torch.clamp(task_env.action_scale[3:6], min=1.0e-6)
        action[env_id, 3:6] = torch.clamp(rot_action, min=-1.0, max=1.0)
    action[:, 6] = gripper_action
    return action


def _action_tracking_before_step(task_env, env_id: int, action: torch.Tensor) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    env_origin = task_env.scene.env_origins[env_id]
    pre_ee_pos_b, pre_ee_quat_b = _ee_pose_b(task_env, env_id)
    pre_ee_pos_w, pre_ee_quat_w = _ee_pose_w_from_b(task_env, env_id, pre_ee_pos_b, pre_ee_quat_b)
    action_env = action[env_id].detach()
    command_delta_b = action_env[:6] * task_env.action_scale
    target_ee_pos_b, target_ee_quat_b = math_utils.apply_delta_pose(
        pre_ee_pos_b.unsqueeze(0),
        pre_ee_quat_b.unsqueeze(0),
        command_delta_b.unsqueeze(0),
    )
    target_ee_pos_w, target_ee_quat_w = _ee_pose_w_from_b(
        task_env,
        env_id,
        target_ee_pos_b[0],
        target_ee_quat_b[0],
    )
    exact_ee_pos_b, exact_ee_quat_b = _exact_ee_pose_b(task_env, env_id)
    exact_ee_pos_w = task_env.grasp_prior_reset_exact_ee_pos_w[env_id]
    pregrasp_ee_pos_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    return {
        "tracking_pre_ee_pos_b": pre_ee_pos_b.detach().clone(),
        "tracking_pre_ee_quat_b": pre_ee_quat_b.detach().clone(),
        "tracking_pre_ee_pos_w": pre_ee_pos_w.detach().clone(),
        "tracking_pre_ee_quat_w": pre_ee_quat_w.detach().clone(),
        "tracking_command_delta_b": command_delta_b.detach().clone(),
        "tracking_target_ee_pos_b": target_ee_pos_b[0].detach().clone(),
        "tracking_target_ee_quat_b": target_ee_quat_b[0].detach().clone(),
        "tracking_target_ee_pos_w": target_ee_pos_w.detach().clone(),
        "tracking_target_ee_quat_w": target_ee_quat_w.detach().clone(),
        "tracking_exact_ee_pos_b": exact_ee_pos_b.detach().clone(),
        "tracking_exact_ee_quat_b": exact_ee_quat_b.detach().clone(),
        "tracking_exact_ee_pos_w": exact_ee_pos_w.detach().clone(),
        "tracking_pregrasp_ee_pos_w": pregrasp_ee_pos_w.detach().clone(),
        "tracking_env_origin": env_origin.detach().clone(),
    }


def _finalize_action_tracking(
    task_env,
    env_id: int,
    before: dict[str, object],
) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    post_ee_pos_b, post_ee_quat_b = _ee_pose_b(task_env, env_id)
    post_ee_pos_w, post_ee_quat_w = _ee_pose_w_from_b(task_env, env_id, post_ee_pos_b, post_ee_quat_b)
    controller_pos_des_b = task_env.ik_controller.ee_pos_des[env_id].detach().clone()
    controller_quat_des_b = task_env.ik_controller.ee_quat_des[env_id].detach().clone()
    controller_pos_des_w, controller_quat_des_w = _ee_pose_w_from_b(
        task_env,
        env_id,
        controller_pos_des_b,
        controller_quat_des_b,
    )
    pre_ee_pos_b = before["tracking_pre_ee_pos_b"]
    pre_ee_pos_w = before["tracking_pre_ee_pos_w"]
    command_delta_b = before["tracking_command_delta_b"]
    target_ee_pos_b = before["tracking_target_ee_pos_b"]
    target_ee_pos_w = before["tracking_target_ee_pos_w"]
    exact_ee_pos_w = before["tracking_exact_ee_pos_w"]
    pregrasp_ee_pos_w = before["tracking_pregrasp_ee_pos_w"]
    env_origin = before["tracking_env_origin"]
    realized_delta_b = post_ee_pos_b - pre_ee_pos_b
    realized_delta_w = post_ee_pos_w - pre_ee_pos_w
    commanded_delta_norm = torch.norm(command_delta_b[:3])
    realized_delta_norm = torch.norm(realized_delta_b)
    return {
        "tracking_pre_ee_pos_b": _tensor_list(pre_ee_pos_b),
        "tracking_pre_ee_pos_env": _tensor_list(pre_ee_pos_w - env_origin),
        "tracking_pre_ee_pos_w": _tensor_list(pre_ee_pos_w),
        "tracking_post_ee_pos_b": _tensor_list(post_ee_pos_b),
        "tracking_post_ee_pos_env": _tensor_list(post_ee_pos_w - env_origin),
        "tracking_post_ee_pos_w": _tensor_list(post_ee_pos_w),
        "tracking_command_delta_b": _tensor_list(command_delta_b),
        "tracking_commanded_delta_norm_m": _as_float(commanded_delta_norm),
        "tracking_target_ee_pos_b": _tensor_list(target_ee_pos_b),
        "tracking_target_ee_pos_env": _tensor_list(target_ee_pos_w - env_origin),
        "tracking_target_ee_pos_w": _tensor_list(target_ee_pos_w),
        "tracking_controller_ee_pos_des_b": _tensor_list(controller_pos_des_b),
        "tracking_controller_ee_pos_des_env": _tensor_list(controller_pos_des_w - env_origin),
        "tracking_controller_ee_pos_des_w": _tensor_list(controller_pos_des_w),
        "tracking_realized_delta_b": _tensor_list(realized_delta_b),
        "tracking_realized_delta_w": _tensor_list(realized_delta_w),
        "tracking_realized_delta_norm_m": _as_float(realized_delta_norm),
        "tracking_realized_over_commanded": _as_float(
            realized_delta_norm / torch.clamp(commanded_delta_norm, min=1.0e-8)
        ),
        "tracking_target_minus_pre_ee_b": _tensor_list(target_ee_pos_b - pre_ee_pos_b),
        "tracking_post_minus_target_ee_b": _tensor_list(post_ee_pos_b - target_ee_pos_b),
        "tracking_post_to_command_target_dist_m": _as_float(torch.norm(post_ee_pos_b - target_ee_pos_b)),
        "tracking_pre_to_exact_ee_dist_m": _as_float(torch.norm(pre_ee_pos_w - exact_ee_pos_w)),
        "tracking_target_to_exact_ee_dist_m": _as_float(torch.norm(target_ee_pos_w - exact_ee_pos_w)),
        "tracking_post_to_exact_ee_dist_m": _as_float(torch.norm(post_ee_pos_w - exact_ee_pos_w)),
        "tracking_pre_to_pregrasp_ee_dist_m": _as_float(torch.norm(pre_ee_pos_w - pregrasp_ee_pos_w)),
        "tracking_post_to_pregrasp_ee_dist_m": _as_float(torch.norm(post_ee_pos_w - pregrasp_ee_pos_w)),
    }


def _mean_extra_value(value) -> float | None:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reward_log_terms(task_env) -> dict[str, float]:
    terms: dict[str, float] = {}
    extras = getattr(task_env, "extras", {})
    if not isinstance(extras, dict):
        return terms
    log_terms = extras.get("log", {})
    if isinstance(log_terms, dict):
        for key, value in log_terms.items():
            scalar = _mean_extra_value(value)
            if scalar is not None:
                terms[f"reward_term_{key}"] = scalar
    for key, value in extras.items():
        if key == "log":
            continue
        scalar = _mean_extra_value(value)
        if scalar is not None:
            terms[f"extra_{key}"] = scalar
    return terms


def _oracle_trace_record(
    task_env,
    env_id: int,
    *,
    reset_index: int,
    oracle_step: int,
    phase: str,
    phase_step: int,
    action: torch.Tensor,
    reward,
    terminated,
    truncated,
    action_tracking_before: dict[str, object] | None = None,
) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device), update_success_timer=False)
    geometry = _actual_tip_geometry(task_env, env_id)
    contact = _contact_metrics(task_env, env_id)
    env_origin = task_env.scene.env_origins[env_id]
    exact_ee_env = task_env.grasp_prior_reset_exact_ee_pos_w[env_id] - env_origin
    pregrasp_ee_env = task_env.grasp_prior_reset_target_ee_pos_w[env_id] - env_origin
    actual_ee_env = task_env.ee_pos[env_id]
    actual_to_exact = actual_ee_env - exact_ee_env
    actual_to_pregrasp = actual_ee_env - pregrasp_ee_env
    if isinstance(reward, torch.Tensor):
        reward_value = float(reward.detach().float().mean().cpu())
    else:
        reward_value = float(reward)
    if isinstance(terminated, torch.Tensor):
        terminated_flag = bool(terminated[env_id].detach().cpu())
    else:
        terminated_flag = bool(terminated)
    if isinstance(truncated, torch.Tensor):
        truncated_flag = bool(truncated[env_id].detach().cpu())
    else:
        truncated_flag = bool(truncated)
    action_env = action[env_id].detach().float().cpu()
    record: dict[str, object] = {
        "reset_index": int(reset_index),
        "env_id": int(env_id),
        "oracle_step": int(oracle_step),
        "phase": str(phase),
        "phase_step": int(phase_step),
        "reward": reward_value,
        "terminated": terminated_flag,
        "truncated": truncated_flag,
        "done": bool(terminated_flag or truncated_flag),
        "success_rate": _as_float(task_env.in_success_region[env_id]),
        "has_lifted_cube": _as_float(task_env.has_lifted_cube[env_id]),
        "cube_lift_height_m": _as_float(task_env.cube_lift_height[env_id]),
        "cube_xy_error_m": _as_float(task_env.cube_xy_error[env_id]),
        "cube_goal_height_error_m": _as_float(task_env.cube_goal_height_error[env_id]),
        "ee_to_cube_dist_m": _as_float(task_env.ee_to_cube_dist[env_id]),
        "finger_center_to_cube_dist_m": _as_float(task_env.finger_center_to_cube_dist[env_id]),
        "left_finger_to_cube_dist_m": _as_float(task_env.left_finger_to_cube_dist[env_id]),
        "right_finger_to_cube_dist_m": _as_float(task_env.right_finger_to_cube_dist[env_id]),
        "max_finger_to_cube_dist_m": _as_float(task_env.max_finger_to_cube_dist[env_id]),
        "finger_distance_asymmetry_m": _as_float(task_env.finger_distance_asymmetry[env_id]),
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "gripper_width_m": _as_float(task_env.gripper_width[env_id]),
        "action_x": float(action_env[0]),
        "action_y": float(action_env[1]),
        "action_z": float(action_env[2]),
        "action_roll": float(action_env[3]),
        "action_pitch": float(action_env[4]),
        "action_yaw": float(action_env[5]),
        "action_gripper": float(action_env[6]),
        "actual_ee_to_exact_ee_dist_m": _as_float(torch.norm(actual_to_exact)),
        "actual_ee_to_pregrasp_ee_dist_m": _as_float(torch.norm(actual_to_pregrasp)),
        "actual_ee_minus_exact_ee_env": _tensor_list(actual_to_exact),
        "actual_ee_minus_pregrasp_ee_env": _tensor_list(actual_to_pregrasp),
        "exact_ee_pos_env": _tensor_list(exact_ee_env),
        "pregrasp_ee_pos_env": _tensor_list(pregrasp_ee_env),
    }
    for key in (
        "actual_tip_center_to_cube_dist_m",
        "actual_tip_max_to_cube_dist_m",
        "actual_left_tip_proxy_to_cube_dist_m",
        "actual_right_tip_proxy_to_cube_dist_m",
        "actual_tip_table_clearance_m",
    ):
        record[key] = geometry[key]
    record["cube_pos_env"] = geometry["cube_pos_env"]
    record["actual_tip_center_pos_env"] = geometry["actual_tip_center_pos_env"]
    record["relative_to_cube_env"] = geometry["relative_to_cube_env"]
    if action_tracking_before is not None:
        record.update(_finalize_action_tracking(task_env, env_id, action_tracking_before))
    record.update(contact)
    record.update(_reward_log_terms(task_env))
    return record


def _oracle_frame_lines(sample: dict[str, object], record: dict[str, object], summary: dict[str, object]) -> list[str]:
    rel = record.get("relative_to_cube_env", {})
    tip_rel = rel.get("actual_tip_center", [0.0, 0.0, 0.0]) if isinstance(rel, dict) else [0.0, 0.0, 0.0]
    return [
        "PHASE 3: ORACLE_CLOSE_LIFT_FROM_RESET - debug-only scripted env.step rollout",
        "sequence: approach along reset offset -> light close -> small upward lift -> hold",
        f"reset={record['reset_index']} sample={sample['sample_index']} step={record['oracle_step']} phase={record['phase']} phase_step={record['phase_step']}",
        f"mode={summary.get('approach_mode', 'fixed_direction')} gain={summary.get('proportional_gain', 1.0):.2f} max_pos_action={summary.get('max_position_action', 1.0):.2f}",
        f"action xyz=({record['action_x']:+.3f},{record['action_y']:+.3f},{record['action_z']:+.3f}) gripper={record['action_gripper']:+.3f}",
        f"close_width_cmd={summary['close_width_command_m']:.4f} lift_gate={summary['lift_success_height_m']:.4f}",
        f"cube_env={_fmt_vec(record['cube_pos_env'])} lift={record['cube_lift_height_m']:.4f} xy={record['cube_xy_error_m']:.4f}",
        f"tip_center_rel={_fmt_vec(tip_rel)} tip_dist={record['actual_tip_center_to_cube_dist_m']:.4f} tip_max={record['actual_tip_max_to_cube_dist_m']:.4f}",
        f"actual_EE_to_exact={record['actual_ee_to_exact_ee_dist_m']:.4f} actual_EE_to_pregrasp={record['actual_ee_to_pregrasp_ee_dist_m']:.4f}",
        f"track post_to_exact={record.get('tracking_post_to_exact_ee_dist_m', 0.0):.4f} post_to_cmd_target={record.get('tracking_post_to_command_target_dist_m', 0.0):.4f} realized_delta={record.get('tracking_realized_delta_norm_m', 0.0):.4f}",
        f"ee={record['ee_to_cube_dist_m']:.4f} finger_center={record['finger_center_to_cube_dist_m']:.4f} width={record['gripper_width_m']:.4f}",
        f"table_clearance tip={record['actual_tip_table_clearance_m']:.4f} body={record['finger_table_clearance_m']:.4f}",
        f"reward={record['reward']:.4f} success={record['success_rate']:.1f} lifted_flag={record['has_lifted_cube']:.1f} done={record['done']}",
    ]


def _render_oracle_frame(
    gym_env,
    task_env,
    env_cfg,
    markers: dict[str, VisualizationMarkers],
    sample: dict[str, object],
    record: dict[str, object],
    oracle_summary: dict[str, object],
    *,
    frames_dir: Path,
    rendered_frames: list[Path],
    view_specs: list[dict[str, object]],
    key_frame: bool,
) -> None:
    actual_geometry = _actual_tip_geometry(task_env, int(record["env_id"]))
    actual_geometry["target_ee_pos_w"] = actual_geometry["actual_ee_pos_w"]
    _visualize_markers(markers, task_env, int(record["env_id"]), actual_geometry=actual_geometry)
    env_origin = task_env.scene.env_origins[int(record["env_id"])].detach().cpu().tolist()
    views = view_specs if key_frame else [view_specs[0]]
    for view in views:
        eye = tuple(float(view["eye"][idx]) + float(env_origin[idx]) for idx in range(3))
        target = tuple(float(view["target"][idx]) + float(env_origin[idx]) for idx in range(3))
        _set_camera(task_env, env_cfg, eye, target)
        frame = _render_rgb(gym_env, task_env)
        title = (
            f"Franka cube GGX oracle close/lift | reset {record['reset_index']} | "
            f"step {record['oracle_step']} | view {view['name']} | seed {args_cli.seed}"
        )
        image = _overlay_frame(frame, title, _oracle_frame_lines(sample, record, oracle_summary))
        frame_path = (
            frames_dir
            / f"reset_{int(record['reset_index']):03d}_phase3_oracle_step_{int(record['oracle_step']):04d}_{record['phase']}_{view['name']}.png"
        )
        image.save(frame_path)
        rendered_frames.append(frame_path)


def _run_oracle_close_lift_check(
    gym_env,
    task_env,
    env_cfg,
    markers: dict[str, VisualizationMarkers],
    sample: dict[str, object],
    env_id: int,
    *,
    frames_dir: Path,
    rendered_frames: list[Path],
    view_specs: list[dict[str, object]],
    render_this_reset: bool,
) -> dict[str, object]:
    env_ids = torch.tensor([env_id], dtype=torch.long, device=task_env.device)
    root_quat_w = task_env._robot.data.root_quat_w[env_ids]
    away_dir_w = task_env.grasp_prior_reset_offset_dir_w[env_ids]
    away_dir_w = away_dir_w / torch.clamp(torch.norm(away_dir_w, dim=-1, keepdim=True), min=1.0e-6)
    approach_dir_w = -away_dir_w
    approach_dir_b = math_utils.quat_apply_inverse(root_quat_w, approach_dir_w)
    approach_dir_b = approach_dir_b / torch.clamp(torch.norm(approach_dir_b, dim=-1, keepdim=True), min=1.0e-6)
    action_scale = task_env.action_scale.detach().clone()
    approach_mode = str(args_cli.oracle_approach_mode)
    approach_steps = max(int(args_cli.oracle_approach_steps), 0)
    close_steps = max(int(args_cli.oracle_close_steps), 0)
    lift_steps = max(int(args_cli.oracle_lift_steps), 0)
    hold_steps = max(int(args_cli.oracle_hold_steps), 0)
    per_step_distance = float(args_cli.oracle_approach_distance) / max(approach_steps, 1)
    approach_xyz_action = torch.clamp((approach_dir_b[0] * per_step_distance) / action_scale[:3], -1.0, 1.0)
    gripper_action = _gripper_action_for_width(float(args_cli.oracle_close_width), float(task_env.cfg.max_gripper_width))
    open_action = _gripper_action_for_width(float(task_env.cfg.max_gripper_width), float(task_env.cfg.max_gripper_width))

    base_action = torch.zeros(task_env.num_envs, int(task_env.cfg.action_space), device=task_env.device)
    phase_specs: list[tuple[str, int]] = []
    if approach_steps > 0:
        phase_specs.append(("approach_to_exact", approach_steps))
    if close_steps > 0:
        phase_specs.append(("light_close", close_steps))
    if lift_steps > 0:
        phase_specs.append(("lift", lift_steps))
    if hold_steps > 0:
        phase_specs.append(("hold", hold_steps))

    def action_for_phase(phase: str) -> torch.Tensor:
        if phase == "approach_to_exact":
            if approach_mode == "proportional_exact":
                return _bounded_exact_tracking_action(task_env, env_id, gripper_action=open_action)
            action = base_action.clone()
            action[:, 0:3] = approach_xyz_action
            action[:, 6] = open_action
            return action
        if phase == "light_close":
            if approach_mode == "proportional_exact":
                return _bounded_exact_tracking_action(task_env, env_id, gripper_action=gripper_action)
            action = base_action.clone()
            action[:, 6] = gripper_action
            return action
        if phase == "lift":
            action = base_action.clone()
            action[:, 2] = float(np.clip(args_cli.oracle_lift_action_z, -1.0, 1.0))
            action[:, 6] = gripper_action
            return action
        action = base_action.clone()
        action[:, 6] = gripper_action
        return action

    trace: list[dict[str, object]] = []
    done_seen = False
    oracle_step = 0
    total_planned = sum(steps for _, steps in phase_specs)
    key_steps = {1, max(1, approach_steps), max(1, approach_steps + close_steps), max(1, total_planned)}
    render_interval = max(int(args_cli.oracle_render_interval), 1)
    oracle_summary_seed = {
        "close_width_command_m": float(args_cli.oracle_close_width),
        "lift_success_height_m": float(args_cli.oracle_lift_success_height),
        "approach_mode": approach_mode,
        "proportional_gain": float(args_cli.oracle_proportional_gain),
        "max_position_action": float(args_cli.oracle_max_position_action),
    }
    for phase, steps in phase_specs:
        for phase_step in range(1, steps + 1):
            oracle_step += 1
            action = action_for_phase(phase)
            action_tracking_before = _action_tracking_before_step(task_env, env_id, action)
            step_out = gym_env.step(action)
            if len(step_out) == 5:
                _, reward, terminated, truncated, _ = step_out
            else:
                _, reward, dones, _ = step_out
                terminated = dones
                truncated = torch.zeros_like(dones) if isinstance(dones, torch.Tensor) else False
            record = _oracle_trace_record(
                task_env,
                env_id,
                reset_index=int(sample["reset_index"]),
                oracle_step=oracle_step,
                phase=phase,
                phase_step=phase_step,
                action=action,
                reward=reward,
                terminated=terminated,
                truncated=truncated,
                action_tracking_before=action_tracking_before,
            )
            trace.append(record)
            done_seen = done_seen or bool(record["done"])
            should_render = render_this_reset and (
                oracle_step in key_steps or oracle_step % render_interval == 0 or bool(record["done"])
            )
            if should_render:
                _render_oracle_frame(
                    gym_env,
                    task_env,
                    env_cfg,
                    markers,
                    sample,
                    record,
                    oracle_summary_seed,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_frames,
                    view_specs=view_specs,
                    key_frame=oracle_step in key_steps or bool(record["done"]),
                )
            if done_seen:
                break
        if done_seen:
            break

    lift_values = [float(item["cube_lift_height_m"]) for item in trace]
    success_values = [float(item["success_rate"]) for item in trace]
    tip_values = [float(item["actual_tip_center_to_cube_dist_m"]) for item in trace]
    width_values = [float(item["gripper_width_m"]) for item in trace]
    reward_values = [float(item["reward"]) for item in trace]
    post_to_exact_values = [
        float(item["tracking_post_to_exact_ee_dist_m"])
        for item in trace
        if item.get("tracking_post_to_exact_ee_dist_m") is not None
    ]
    post_to_target_values = [
        float(item["tracking_post_to_command_target_dist_m"])
        for item in trace
        if item.get("tracking_post_to_command_target_dist_m") is not None
    ]
    realized_delta_values = [
        float(item["tracking_realized_delta_norm_m"])
        for item in trace
        if item.get("tracking_realized_delta_norm_m") is not None
    ]
    commanded_delta_values = [
        float(item["tracking_commanded_delta_norm_m"])
        for item in trace
        if item.get("tracking_commanded_delta_norm_m") is not None
    ]
    realized_ratio_values = [
        float(item["tracking_realized_over_commanded"])
        for item in trace
        if item.get("tracking_realized_over_commanded") is not None
    ]
    max_lift = max(lift_values) if lift_values else 0.0
    final_record = trace[-1] if trace else None
    lift_gate = max_lift >= float(args_cli.oracle_lift_success_height)
    no_done = not any(bool(item["done"]) for item in trace)
    final_tip_close = bool(final_record and float(final_record["actual_tip_center_to_cube_dist_m"]) <= 1.0 * float(task_env.cfg.cube_size))
    oracle_success = bool(lift_gate and no_done and final_tip_close)
    result = {
        "enabled": True,
        "approach_steps": approach_steps,
        "close_steps": close_steps,
        "lift_steps": lift_steps,
        "hold_steps": hold_steps,
        "steps_completed": len(trace),
        "done_seen": bool(any(bool(item["done"]) for item in trace)),
        "terminated_seen": bool(any(bool(item["terminated"]) for item in trace)),
        "truncated_seen": bool(any(bool(item["truncated"]) for item in trace)),
        "approach_distance_command_m": float(args_cli.oracle_approach_distance),
        "approach_per_step_distance_m": per_step_distance,
        "approach_mode": approach_mode,
        "proportional_gain": float(args_cli.oracle_proportional_gain),
        "max_position_action": float(args_cli.oracle_max_position_action),
        "track_orientation": bool(args_cli.oracle_track_orientation),
        "approach_dir_w": _tensor_list(approach_dir_w[0]),
        "approach_dir_b": _tensor_list(approach_dir_b[0]),
        "approach_action_xyz": _tensor_list(approach_xyz_action),
        "close_width_command_m": float(args_cli.oracle_close_width),
        "close_gripper_action": gripper_action,
        "lift_action_z": float(args_cli.oracle_lift_action_z),
        "lift_success_height_m": float(args_cli.oracle_lift_success_height),
        "lift_gate_pass": bool(lift_gate),
        "final_tip_close_gate_pass": final_tip_close,
        "oracle_success": oracle_success,
        "verdict": "PASS" if oracle_success else "FAIL",
        "max_cube_lift_height_m": max_lift,
        "final_cube_lift_height_m": lift_values[-1] if lift_values else None,
        "max_success_rate": max(success_values) if success_values else 0.0,
        "final_success_rate": success_values[-1] if success_values else None,
        "min_tip_center_to_cube_dist_m": min(tip_values) if tip_values else None,
        "final_tip_center_to_cube_dist_m": tip_values[-1] if tip_values else None,
        "min_gripper_width_m": min(width_values) if width_values else None,
        "final_gripper_width_m": width_values[-1] if width_values else None,
        "min_post_to_exact_ee_dist_m": min(post_to_exact_values) if post_to_exact_values else None,
        "final_post_to_exact_ee_dist_m": post_to_exact_values[-1] if post_to_exact_values else None,
        "min_post_to_command_target_dist_m": min(post_to_target_values) if post_to_target_values else None,
        "mean_realized_delta_norm_m": _mean_values(realized_delta_values),
        "mean_commanded_delta_norm_m": _mean_values(commanded_delta_values),
        "mean_realized_over_commanded": _mean_values(realized_ratio_values),
        "reward_mean": _mean_values(reward_values),
        "reward_final": reward_values[-1] if reward_values else None,
        "trace": trace,
    }
    return result


def _json_safe_csv_value(value) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _write_oracle_trace_files(
    trace_records: list[dict[str, object]],
    *,
    trace_jsonl_path: Path,
    trace_csv_path: Path,
) -> None:
    trace_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_jsonl_path.open("w", encoding="utf-8") as f:
        for record in trace_records:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    trace_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for record in trace_records for key in record.keys()})
    if "oracle_step" in fieldnames:
        fieldnames.remove("oracle_step")
        fieldnames.insert(0, "oracle_step")
    if "reset_index" in fieldnames:
        fieldnames.remove("reset_index")
        fieldnames.insert(0, "reset_index")
    with trace_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in trace_records:
            writer.writerow({key: _json_safe_csv_value(record.get(key)) for key in fieldnames})


def _write_csv(path: Path, samples: list[dict[str, object]]) -> None:
    oracle_scalar_keys = [
        "enabled",
        "approach_steps",
        "close_steps",
        "lift_steps",
        "hold_steps",
        "steps_completed",
        "done_seen",
        "terminated_seen",
        "truncated_seen",
        "approach_mode",
        "approach_distance_command_m",
        "approach_per_step_distance_m",
        "proportional_gain",
        "max_position_action",
        "track_orientation",
        "close_width_command_m",
        "close_gripper_action",
        "lift_action_z",
        "lift_success_height_m",
        "lift_gate_pass",
        "final_tip_close_gate_pass",
        "oracle_success",
        "verdict",
        "max_cube_lift_height_m",
        "final_cube_lift_height_m",
        "max_success_rate",
        "final_success_rate",
        "min_tip_center_to_cube_dist_m",
        "final_tip_center_to_cube_dist_m",
        "min_gripper_width_m",
        "final_gripper_width_m",
        "min_post_to_exact_ee_dist_m",
        "final_post_to_exact_ee_dist_m",
        "min_post_to_command_target_dist_m",
        "mean_realized_delta_norm_m",
        "mean_commanded_delta_norm_m",
        "mean_realized_over_commanded",
        "reward_mean",
        "reward_final",
    ]
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
    ] + [f"exact_close_{key}" for key in exact_close_scalar_keys] + [
        f"oracle_{key}" for key in oracle_scalar_keys
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scalar_keys)
        writer.writeheader()
        for sample in samples:
            row = {key: sample.get(key) for key in scalar_keys}
            exact_close = sample.get("exact_close_check")
            if isinstance(exact_close, dict):
                for key in exact_close_scalar_keys:
                    row[f"exact_close_{key}"] = exact_close.get(key)
            oracle = sample.get("oracle_close_lift_check")
            if isinstance(oracle, dict):
                for key in oracle_scalar_keys:
                    row[f"oracle_{key}"] = oracle.get(key)
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
    if args_cli.include_exact_close_check and args_cli.include_oracle_close_lift_check:
        raise ValueError(
            "--include_exact_close_check and --include_oracle_close_lift_check are mutually exclusive because both "
            "checks intentionally mutate the same reset state."
        )

    output_dir = Path(args_cli.output_dir or datetime.now().strftime("franka_cube_prior_diag_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "reset_geometry.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "reset_geometry.csv"
    oracle_trace_jsonl_path = output_dir / "oracle_trace.jsonl"
    oracle_trace_csv_path = output_dir / "oracle_trace.csv"
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
    oracle_trace_records: list[dict[str, object]] = []
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
            if args_cli.include_oracle_close_lift_check:
                oracle_check = _run_oracle_close_lift_check(
                    gym_env,
                    task_env,
                    env_cfg,
                    markers,
                    sample,
                    env_id,
                    frames_dir=frames_dir,
                    rendered_frames=rendered_frames,
                    view_specs=view_specs,
                    render_this_reset=(reset_index == 0 or bool(args_cli.render_all_resets)),
                )
                sample["oracle_close_lift_check"] = oracle_check
                oracle_trace_records.extend(oracle_check["trace"])
                print(
                    "[ORACLE_CLOSE_LIFT_DIAG] "
                    f"reset={reset_index} sample={sample['sample_index']} "
                    f"verdict={oracle_check['verdict']} "
                    f"steps={oracle_check['steps_completed']} "
                    f"max_lift={oracle_check['max_cube_lift_height_m']:.5f} "
                    f"final_lift={oracle_check['final_cube_lift_height_m']:.5f} "
                    f"min_tip_center={oracle_check['min_tip_center_to_cube_dist_m']:.5f} "
                    f"final_width={oracle_check['final_gripper_width_m']:.5f} "
                    f"done={oracle_check['done_seen']}",
                    flush=True,
                )
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
    oracle_checks = [
        sample["oracle_close_lift_check"]
        for sample in samples
        if isinstance(sample.get("oracle_close_lift_check"), dict)
    ]
    exact_close_enabled = bool(args_cli.include_exact_close_check)
    oracle_enabled = bool(args_cli.include_oracle_close_lift_check)
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
    oracle_gate_pass = bool(
        (not oracle_enabled)
        or (
            oracle_checks
            and len(oracle_checks) == len(samples)
            and all(bool(check["oracle_success"]) for check in oracle_checks)
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
        "oracle_close_lift_check_enabled": oracle_enabled,
        "exact_close_steps": int(args_cli.exact_close_steps),
        "exact_close_command_width_m": float(args_cli.exact_close_command_width),
        "exact_close_approach_offset_m": float(args_cli.exact_close_approach_offset),
        "exact_close_lateral_offset_m": float(args_cli.exact_close_lateral_offset),
        "oracle_approach_steps": int(args_cli.oracle_approach_steps),
        "oracle_close_steps": int(args_cli.oracle_close_steps),
        "oracle_lift_steps": int(args_cli.oracle_lift_steps),
        "oracle_hold_steps": int(args_cli.oracle_hold_steps),
        "oracle_approach_mode": str(args_cli.oracle_approach_mode),
        "oracle_approach_distance_m": float(args_cli.oracle_approach_distance),
        "oracle_proportional_gain": float(args_cli.oracle_proportional_gain),
        "oracle_max_position_action": float(args_cli.oracle_max_position_action),
        "oracle_track_orientation": bool(args_cli.oracle_track_orientation),
        "oracle_close_width_m": float(args_cli.oracle_close_width),
        "oracle_lift_action_z": float(args_cli.oracle_lift_action_z),
        "oracle_lift_success_height_m": float(args_cli.oracle_lift_success_height),
        "oracle_render_interval": int(args_cli.oracle_render_interval),
        "render_all_resets": bool(args_cli.render_all_resets),
        "render_failed_exact_close": bool(args_cli.render_failed_exact_close),
        "pregrasp_reset_gate_pass": reset_gate_pass,
        "exact_close_gate_pass": exact_close_gate_pass,
        "oracle_close_lift_gate_pass": oracle_gate_pass,
        "rl_relaunch_gate_verdict": "PASS" if reset_gate_pass and exact_close_gate_pass and oracle_gate_pass else "FAIL",
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
        "oracle_success_rate": sum(1 for c in oracle_checks if c["oracle_success"]) / len(oracle_checks)
        if oracle_checks
        else None,
        "oracle_lift_gate_pass_rate": sum(1 for c in oracle_checks if c["lift_gate_pass"]) / len(oracle_checks)
        if oracle_checks
        else None,
        "oracle_done_seen_rate": sum(1 for c in oracle_checks if c["done_seen"]) / len(oracle_checks)
        if oracle_checks
        else None,
        "oracle_max_cube_lift_height_mean_m": _mean_values(
            [float(c["max_cube_lift_height_m"]) for c in oracle_checks]
        ),
        "oracle_final_cube_lift_height_mean_m": _mean_values(
            [float(c["final_cube_lift_height_m"]) for c in oracle_checks if c["final_cube_lift_height_m"] is not None]
        ),
        "oracle_min_tip_center_dist_mean_m": _mean_values(
            [float(c["min_tip_center_to_cube_dist_m"]) for c in oracle_checks if c["min_tip_center_to_cube_dist_m"] is not None]
        ),
        "oracle_final_gripper_width_mean_m": _mean_values(
            [float(c["final_gripper_width_m"]) for c in oracle_checks if c["final_gripper_width_m"] is not None]
        ),
        "oracle_min_post_to_exact_ee_dist_mean_m": _mean_values(
            [
                float(c["min_post_to_exact_ee_dist_m"])
                for c in oracle_checks
                if c["min_post_to_exact_ee_dist_m"] is not None
            ]
        ),
        "oracle_final_post_to_exact_ee_dist_mean_m": _mean_values(
            [
                float(c["final_post_to_exact_ee_dist_m"])
                for c in oracle_checks
                if c["final_post_to_exact_ee_dist_m"] is not None
            ]
        ),
        "oracle_min_post_to_command_target_dist_mean_m": _mean_values(
            [
                float(c["min_post_to_command_target_dist_m"])
                for c in oracle_checks
                if c["min_post_to_command_target_dist_m"] is not None
            ]
        ),
        "oracle_mean_realized_delta_norm_m": _mean_values(
            [
                float(c["mean_realized_delta_norm_m"])
                for c in oracle_checks
                if c["mean_realized_delta_norm_m"] is not None
            ]
        ),
        "oracle_mean_commanded_delta_norm_m": _mean_values(
            [
                float(c["mean_commanded_delta_norm_m"])
                for c in oracle_checks
                if c["mean_commanded_delta_norm_m"] is not None
            ]
        ),
        "oracle_mean_realized_over_commanded": _mean_values(
            [
                float(c["mean_realized_over_commanded"])
                for c in oracle_checks
                if c["mean_realized_over_commanded"] is not None
            ]
        ),
        "oracle_trace_jsonl_path": str(oracle_trace_jsonl_path) if oracle_trace_records else None,
        "oracle_trace_csv_path": str(oracle_trace_csv_path) if oracle_trace_records else None,
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
            "oracle_close_lift_check, when enabled, is a diagnostic-only scripted env.step rollout from the actual reset/pregrasp state; it does not change the RL task reset, observation, reward, or PPO path",
        ],
    }
    payload = {
        "summary": summary,
        "samples": samples,
        "library_metadata": getattr(task_env, "_grasp_prior_metadata", {}),
        "grasp_to_tool_transform": getattr(task_env, "_grasp_prior_grasp_to_tool", torch.eye(4)).detach().cpu().tolist(),
    }
    _write_csv(csv_path, samples)
    if oracle_trace_records:
        _write_oracle_trace_files(
            oracle_trace_records,
            trace_jsonl_path=oracle_trace_jsonl_path,
            trace_csv_path=oracle_trace_csv_path,
        )
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
