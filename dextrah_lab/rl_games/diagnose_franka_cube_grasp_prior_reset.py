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
        "exact": VisualizationMarkers(_marker_cfg("/Visuals/GraspPriorResetDiag/ExactTool", (0.0, 1.0, 0.15), 0.010)),
        "pregrasp": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/PregraspTool", (1.0, 0.0, 0.85), 0.010)
        ),
        "target_ee": VisualizationMarkers(
            _marker_cfg("/Visuals/GraspPriorResetDiag/TargetEe", (1.0, 0.85, 0.0), 0.008)
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
        "offset": VisualizationMarkers(_marker_cfg("/Visuals/GraspPriorResetDiag/OffsetBeads", (1.0, 1.0, 0.0), 0.005)),
    }


def _visualize_markers(markers: dict[str, VisualizationMarkers], task_env, env_id: int) -> None:
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    target_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    left_w = task_env.left_finger_pos[env_id] + env_origin
    right_w = task_env.right_finger_pos[env_id] + env_origin
    center_w = 0.5 * (left_w + right_w)
    offset_beads = torch.stack(
        (
            exact_w + (pregrasp_w - exact_w) * 0.33,
            exact_w + (pregrasp_w - exact_w) * 0.66,
        )
    )
    markers["cube"].visualize(cube_w.unsqueeze(0))
    markers["exact"].visualize(exact_w.unsqueeze(0))
    markers["pregrasp"].visualize(pregrasp_w.unsqueeze(0))
    markers["target_ee"].visualize(target_ee_w.unsqueeze(0))
    markers["left_finger"].visualize(left_w.unsqueeze(0))
    markers["right_finger"].visualize(right_w.unsqueeze(0))
    markers["gripper_center"].visualize(center_w.unsqueeze(0))
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
    for _ in range(3):
        task_env.sim.render()
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


def _frame_lines(sample: dict[str, object]) -> list[str]:
    rel = sample["relative_to_cube_env"]
    return [
        "markers: cube cyan | exact grasp green | pregrasp magenta | target ee yellow | fingers orange/red | offset beads yellow",
        f"sample={sample['sample_index']} reset_success={sample['reset_success']} quality={sample['reset_grasp_quality_success']} immediate_done={sample['immediate_done']}",
        f"cube_env={_fmt_vec(sample['cube_pos_env'])} cube_w={_fmt_vec(sample['cube_pos_w'])}",
        f"exact_tool_env={_fmt_vec(sample['exact_tool_pos_env'])} pregrasp_tool_env={_fmt_vec(sample['pregrasp_tool_pos_env'])}",
        f"offset_dir_w={_fmt_vec(sample['pregrasp_offset_dir_w'])} offset_len={sample['pregrasp_offset_m']:.4f} radial_dot={sample['offset_radial_dot']:.4f}",
        f"left_rel_cube={_fmt_vec(rel['left_finger'])} right_rel_cube={_fmt_vec(rel['right_finger'])}",
        f"gripper_center_rel_cube={_fmt_vec(rel['gripper_center'])} width={sample['gripper_width_m']:.4f} cube={sample['cube_size_m']:.4f} margin={sample['open_width_margin_m']:.4f}",
        f"projected_exact_finger_center_dist={sample['projected_exact_finger_center_dist_m']:.4f} finger_table_clearance={sample['finger_table_clearance_m']:.4f}",
    ]


def _collect_sample(task_env, env_id: int, reset_index: int) -> dict[str, object]:
    task_env._compute_intermediate_values(torch.tensor([env_id], device=task_env.device))
    env_origin = task_env.scene.env_origins[env_id]
    cube_w = task_env.grasp_prior_reset_cube_pos_w[env_id]
    exact_w = task_env.grasp_prior_reset_exact_tool_pos_w[env_id]
    pregrasp_w = task_env.grasp_prior_reset_pregrasp_tool_pos_w[env_id]
    target_ee_w = task_env.grasp_prior_reset_target_ee_pos_w[env_id]
    left_env = task_env.left_finger_pos[env_id]
    right_env = task_env.right_finger_pos[env_id]
    cube_env = task_env.cube_pos[env_id]
    gripper_center_env = 0.5 * (left_env + right_env)
    exact_env = exact_w - env_origin
    pregrasp_env = pregrasp_w - env_origin
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
        "target_ee_pos_env": _tensor_list(target_ee_env),
        "target_ee_pos_w": _tensor_list(target_ee_w),
        "target_ee_pos_root": _tensor_list(_pos_in_root(task_env, env_id, target_ee_w)),
        "target_ee_quat_w_wxyz": _tensor_list(task_env.grasp_prior_reset_target_ee_quat_w[env_id]),
        "left_finger_pos_env": _tensor_list(left_env),
        "right_finger_pos_env": _tensor_list(right_env),
        "left_finger_pos_w": _tensor_list(left_env + env_origin),
        "right_finger_pos_w": _tensor_list(right_env + env_origin),
        "gripper_center_pos_env": _tensor_list(gripper_center_env),
        "gripper_center_pos_w": _tensor_list(gripper_center_env + env_origin),
        "relative_to_cube_env": {
            "left_finger": _tensor_list(left_env - cube_env),
            "right_finger": _tensor_list(right_env - cube_env),
            "gripper_center": _tensor_list(gripper_center_env - cube_env),
            "exact_tool": _tensor_list(exact_env - cube_env),
            "pregrasp_tool": _tensor_list(pregrasp_env - cube_env),
            "target_ee": _tensor_list(target_ee_env - cube_env),
        },
        "pregrasp_offset_dir_w": _tensor_list(task_env.grasp_prior_reset_offset_dir_w[env_id]),
        "pregrasp_offset_m": float(pregrasp_offset_m.detach().cpu()),
        "exact_tool_dist_m": _as_float(task_env.grasp_prior_reset_exact_tool_dist[env_id]),
        "pregrasp_tool_dist_m": _as_float(task_env.grasp_prior_reset_pregrasp_tool_dist[env_id]),
        "pregrasp_minus_exact_tool_dist_m": _as_float(
            task_env.grasp_prior_reset_pregrasp_tool_dist[env_id]
            - task_env.grasp_prior_reset_exact_tool_dist[env_id]
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
        "finger_table_clearance_m": _as_float(task_env.finger_table_clearance[env_id]),
        "root_pos_w": _tensor_list(task_env._robot.data.root_pos_w[env_id]),
        "root_quat_w_wxyz": _tensor_list(task_env._robot.data.root_quat_w[env_id]),
        "object_grasp_matrix": object_grasp_matrix,
    }
    return sample


def _write_csv(path: Path, samples: list[dict[str, object]]) -> None:
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
        "finger_table_clearance_m",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scalar_keys)
        writer.writeheader()
        for sample in samples:
            writer.writerow({key: sample.get(key) for key in scalar_keys})


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
                f"projected_center={sample['projected_exact_finger_center_dist_m']:.5f} "
                f"immediate_done={sample['immediate_done']}",
                flush=True,
            )
            if reset_index == 0:
                _visualize_markers(markers, task_env, env_id)
                env_origin = task_env.scene.env_origins[env_id].detach().cpu().tolist()
                for view in view_specs:
                    eye = tuple(float(view["eye"][idx]) + float(env_origin[idx]) for idx in range(3))
                    target = tuple(float(view["target"][idx]) + float(env_origin[idx]) for idx in range(3))
                    _set_camera(task_env, env_cfg, eye, target)
                    frame = _render_rgb(gym_env, task_env)
                    title = (
                        f"Franka cube GGX pregrasp reset diagnostic | reset {reset_index} | "
                        f"view {view['name']} | seed {args_cli.seed}"
                    )
                    image = _overlay_frame(frame, title, _frame_lines(sample))
                    frame_path = frames_dir / f"reset_{reset_index:03d}_{view['name']}.png"
                    image.save(frame_path)
                    rendered_frames.append(frame_path)
    finally:
        gym_env.close()
        env_closed = True

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
        "frame_paths": [str(path) for path in rendered_frames],
        "video_path": str(video_path) if video_path.exists() else None,
        "csv_path": str(csv_path),
        "metrics_path": str(metrics_path),
        "env_closed": env_closed,
        "notes": [
            "reset_success measures IK target tracking plus farther/table checks, not grasp-quality geometry",
            "reset_grasp_quality_success additionally requires open width >= cube size, offset away from cube, and projected exact finger center within one cube size",
            "positions are reported in world, env-local, and robot-root frames where applicable",
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
