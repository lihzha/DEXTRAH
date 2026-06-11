#!/usr/bin/env python3
"""Plan DEXTRAH Franka cube trajectories with GraspGenX and cuRobo.

This DEXTRAH-owned wrapper reuses the official GraspGenX ``end2end``
implementation to produce real cuRobo-validated trajectory exports for the
Franka cube BC warm-start path.

The default geometry mirrors ``DextrahFrankaCubeGraspEnvCfg``:

* table center ``(-0.62, 0.0, 0.72)`` with a 52 mm top;
* 60 mm cube at ``(-0.36, -0.12)`` and 5 mm initial table clearance;
* Franka base at ``(0, 0, 0.27)`` with DEXTRAH's 180 degree Z yaw.

The output ``trajectory.json`` is suitable for
``dextrah_lab.offline_dp_bc.trajectory_conversion`` with GraspGenX FK.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_graspgenx_root() -> Path:
    env = os.environ.get("GRASPGENX_ROOT") or os.environ.get("GRASPGENX_REPO")
    if env:
        return Path(env).expanduser().resolve()
    return (_repo_root().parent / "graspgenx").resolve()


def _default_curobo_root() -> Path | None:
    env = os.environ.get("GRASPGENX_CUROBO_DIR")
    if env:
        return Path(env).expanduser().resolve()
    candidate = _repo_root().parent / "curobo"
    return candidate.resolve() if candidate.exists() else None


def _yaw_quat_xyzw(yaw_deg: float) -> list[float]:
    half = 0.5 * math.radians(float(yaw_deg))
    return [0.0, 0.0, math.sin(half), math.cos(half)]


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
        import torch
    except Exception:
        np = None
        torch = None

    if isinstance(value, Path):
        return str(value)
    if np is not None and isinstance(value, np.ndarray):
        return value.tolist()
    if np is not None and isinstance(value, np.generic):
        return value.item()
    if torch is not None and torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


def _require_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"Missing {label}: {path}")


def _latest_pth(path: Path) -> Path:
    candidates = sorted(path.glob("epoch_*.pth")) or sorted(path.glob("*.pth"))
    if not candidates:
        raise FileNotFoundError(f"No .pth checkpoints found in {path}")
    return candidates[-1]


def _write_cube_obj(path: Path, cube_size: float) -> dict[str, Any]:
    """Write a centered cube mesh with exact meter units."""

    path.parent.mkdir(parents=True, exist_ok=True)
    h = 0.5 * float(cube_size)
    verts = [
        (-h, -h, -h),
        (h, -h, -h),
        (h, h, -h),
        (-h, h, -h),
        (-h, -h, h),
        (h, -h, h),
        (h, h, h),
        (-h, h, h),
    ]
    faces = [
        (1, 2, 3),
        (1, 3, 4),
        (5, 8, 7),
        (5, 7, 6),
        (1, 5, 6),
        (1, 6, 2),
        (2, 6, 7),
        (2, 7, 3),
        (3, 7, 8),
        (3, 8, 4),
        (4, 8, 5),
        (4, 5, 1),
    ]
    with path.open("w", encoding="utf-8") as f:
        f.write("# DEXTRAH generated Franka cube mesh\n")
        for x, y, z in verts:
            f.write(f"v {x:.9f} {y:.9f} {z:.9f}\n")
        for face in faces:
            f.write("f " + " ".join(str(i) for i in face) + "\n")
    return {
        "mesh": str(path),
        "cube_size_m": float(cube_size),
        "vertices": len(verts),
        "faces": len(faces),
    }


def _make_robot_config(
    graspgenx_root: Path,
    run_dir: Path,
    *,
    robot_base_z: float,
    robot_yaw_deg: float,
) -> Path:
    src = graspgenx_root / "end2end/robots/franka_panda.yaml"
    cfg = _load_yaml(src)
    cfg["robot_base_pose"] = {
        "translation": [0.0, 0.0, float(robot_base_z)],
        "quaternion_xyzw": _yaw_quat_xyzw(robot_yaw_deg),
    }
    cfg.setdefault("curobo", {})
    cfg["curobo"]["default_joint_position"] = [
        0.0,
        -0.68,
        0.0,
        -2.45,
        0.0,
        2.28,
        0.78,
    ]
    out = run_dir / "configs/franka_panda_dextrah_cube.yaml"
    _write_yaml(out, cfg)
    return out


def _make_env_config(args: argparse.Namespace, run_dir: Path, cube_mesh: Path) -> Path:
    surface_z = float(args.table_center_z) + 0.5 * float(args.table_thickness)
    cube_base_z = surface_z + float(args.object_surface_offset)
    cube_center_z = cube_base_z + 0.5 * float(args.cube_size)

    cfg: dict[str, Any] = {
        "name": "dextrah_franka_cube_grasp",
        "assets": [
            {
                "id": "table",
                "type": "procedural_table",
                "params": {
                    "width": float(args.table_size_x),
                    "depth": float(args.table_size_y),
                    "height": float(args.table_center_z),
                    "thickness": float(args.table_thickness),
                    "leg_thickness": 0.05,
                },
                "pose": {
                    "translation": [
                        float(args.table_center_x),
                        float(args.table_center_y),
                        0.0,
                    ],
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                "support_label": "table_top",
                "collision": "skip",
            }
        ],
        "robot_base_pose": {
            "translation": [0.0, 0.0, float(args.robot_base_z)],
            "quaternion_xyzw": _yaw_quat_xyzw(float(args.robot_yaw_deg)),
        },
        "object_slot": {
            "world_position": [float(args.cube_x), float(args.cube_y), cube_base_z],
            "mesh_scale": 1.0,
            "mesh_file_hint": str(cube_mesh),
            "randomize": {
                "yaw_range_deg": [
                    float(args.cube_yaw_deg),
                    float(args.cube_yaw_deg),
                ]
            },
        },
        "extra_collision": [
            {
                "name": "dextrah_tabletop",
                "type": "cuboid",
                "dims": [
                    float(args.table_size_x),
                    float(args.table_size_y),
                    float(args.table_thickness),
                ],
                "pose": [
                    float(args.table_center_x),
                    float(args.table_center_y),
                    float(args.table_center_z),
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                ],
            }
        ],
        "visual": {
            "show_ground_grid": True,
            "background_color": [0.95, 0.95, 0.95],
            "camera": {
                "eye": [0.30, -0.82, 1.55],
                "target": [float(args.cube_x), float(args.cube_y), surface_z + 0.12],
            },
        },
        "dextrah_geometry": {
            "source_env_cfg": "DextrahFrankaCubeGraspEnvCfg",
            "table_surface_z": surface_z,
            "cube_base_z": cube_base_z,
            "cube_center": [float(args.cube_x), float(args.cube_y), cube_center_z],
            "cube_spawn_z_expected": surface_z + 0.5 * float(args.cube_size) + float(args.object_surface_offset),
        },
    }
    out = run_dir / "configs/dextrah_franka_cube_grasp.yaml"
    _write_yaml(out, cfg)
    return out


def _joint_cfg_from_row(profile: Any, joint_row: Any) -> dict[str, float]:
    n_arm = int(profile.n_arm)
    cfg: dict[str, float] = {}
    for name, value in zip(profile.arm_joint_names, joint_row[:n_arm]):
        cfg[name] = float(value)
    for idx, name in enumerate(profile.gripper_joint_names):
        col = n_arm + idx
        cfg[name] = float(joint_row[col]) if col < len(joint_row) else profile.open_value(name)
    return cfg


def _attachment_start_frame(segments: list[tuple[str, int]]) -> int:
    frame = 0
    for name, count in segments:
        if name in {"hold_after_close", "lift_object", "hold_after_lift"}:
            return frame
        frame += int(count)
    return frame


def _augment_kinematic_object_poses(
    trajectory_json: Path,
    *,
    fk: Any,
    profile: Any,
    bundle: Any,
    joint_traj: Any,
    segments: list[tuple[str, int]],
    grasp_world_T: Any,
) -> None:
    import numpy as np
    import trimesh.transformations as tra

    payload = json.loads(trajectory_json.read_text(encoding="utf-8"))
    frames = payload.get("frames", [])
    if not isinstance(frames, list):
        raise ValueError(f"Expected list of frames in {trajectory_json}")

    object_initial_T = np.asarray(bundle.object_world_T, dtype=float)
    tool_at_grasp_T = np.asarray(grasp_world_T, dtype=float) @ np.asarray(
        profile.grasp_to_tool_transform,
        dtype=float,
    )
    object_in_tool_T = tra.inverse_matrix(tool_at_grasp_T) @ object_initial_T
    attach_start = _attachment_start_frame(segments)

    for idx, frame in enumerate(frames):
        if idx < attach_start or idx >= len(joint_traj):
            object_T = object_initial_T
        else:
            cfg = _joint_cfg_from_row(profile, joint_traj[idx])
            link_poses = fk.fk(
                cfg,
                base_T=bundle.robot_base_T,
                link_names=[profile.tool_frame],
            )
            object_T = np.asarray(link_poses[profile.tool_frame], dtype=float) @ object_in_tool_T
        frame.setdefault("object_poses", {})["object"] = object_T.tolist()

    payload.setdefault("dextrah", {})
    payload["dextrah"]["object_pose_mode"] = "kinematic_attached_to_tool"
    payload["dextrah"]["object_pose_object_id"] = "object"
    payload["dextrah"]["attachment_start_frame"] = int(attach_start)
    trajectory_json.write_text(json.dumps(payload), encoding="utf-8")


def _validate_environment() -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("torch.cuda.is_available() is false")

    curobo = importlib.import_module("curobo")
    from curobo.content import get_assets_path
    from curobo.motion_planner import MotionPlannerCfg  # noqa: F401
    from graspgenx import get_checkpoints_version_dir, get_gripper_descriptions_assets

    ckpt_dir = Path(get_checkpoints_version_dir()).resolve()
    gen_dir = ckpt_dir / "gen"
    dis_dir = ckpt_dir / "dis"
    _require_dir(gen_dir, "GraspGenX generator checkpoint dir")
    _require_dir(dis_dir, "GraspGenX discriminator checkpoint dir")
    _require_file(gen_dir / "config.yaml", "GraspGenX generator config")
    _require_file(dis_dir / "config.yaml", "GraspGenX discriminator config")
    gen_pth = _latest_pth(gen_dir)
    dis_pth = _latest_pth(dis_dir)

    gripper_assets = Path(get_gripper_descriptions_assets()).resolve()
    _require_dir(gripper_assets / "franka_panda", "franka_panda gripper assets")

    curobo_assets = Path(get_assets_path()).resolve()
    _require_file(
        curobo_assets / "robot/franka_description/franka_panda.urdf",
        "cuRobo Franka URDF",
    )
    _require_file(
        curobo_assets.parent / "configs/robot/franka.yml",
        "cuRobo Franka robot config",
    )

    return {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_device_name": torch.cuda.get_device_name(0),
        "curobo_module": getattr(curobo, "__file__", ""),
        "curobo_assets": str(curobo_assets),
        "graspgenx_checkpoint_dir": str(ckpt_dir),
        "gen_checkpoint": str(gen_pth),
        "dis_checkpoint": str(dis_pth),
        "gripper_assets": str(gripper_assets),
        "env": {
            "GRASPGENX_CHECKPOINT_DIR": os.environ.get("GRASPGENX_CHECKPOINT_DIR", ""),
            "GRASPGENX_GRIPPER_CFG_DIR": os.environ.get("GRASPGENX_GRIPPER_CFG_DIR", ""),
            "GRASPGENX_CUROBO_DIR": os.environ.get("GRASPGENX_CUROBO_DIR", ""),
        },
    }


@dataclass
class PlanSummary:
    status: str
    source: str
    curobo_validated: bool
    run_name: str
    trajectory_json: str
    selected_grasp_index: int
    selected_grasp_confidence: float
    num_grasps: int
    plan_segments: dict[str, int]
    task_segments: dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=_repo_root() / "local_results/graspgenx_franka_cube")
    parser.add_argument("--run_name", type=str, default=None)
    parser.add_argument("--graspgenx_root", type=Path, default=_default_graspgenx_root())
    parser.add_argument("--curobo_root", type=Path, default=_default_curobo_root())
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num_sample_points", type=int, default=2000)
    parser.add_argument("--num_grasps", type=int, default=200)
    parser.add_argument("--topk", type=int, default=80)
    parser.add_argument("--grasp_threshold", type=float, default=0.7)
    parser.add_argument("--grasp_planner", choices=("graspmoe", "diffusion", "topdown"), default="graspmoe")
    parser.add_argument("--moe_obb_density", choices=("sparse", "dense", "none"), default="dense")
    parser.add_argument("--max_plan_attempts", type=int, default=80)
    parser.add_argument("--rank_grasps_by_confidence", action="store_true")
    parser.add_argument("--sim_fps", type=int, default=60)
    parser.add_argument("--hold_frames", type=int, default=60)
    parser.add_argument("--hold_after_close_frames", type=int, default=90)
    parser.add_argument("--close_frames", type=int, default=30)
    parser.add_argument("--cube_size", type=float, default=0.06)
    parser.add_argument("--cube_x", type=float, default=-0.36)
    parser.add_argument("--cube_y", type=float, default=-0.12)
    parser.add_argument("--cube_yaw_deg", type=float, default=0.0)
    parser.add_argument("--object_surface_offset", type=float, default=0.005)
    parser.add_argument("--table_center_x", type=float, default=-0.62)
    parser.add_argument("--table_center_y", type=float, default=0.0)
    parser.add_argument("--table_center_z", type=float, default=0.72)
    parser.add_argument("--table_size_x", type=float, default=0.86)
    parser.add_argument("--table_size_y", type=float, default=1.18)
    parser.add_argument("--table_thickness", type=float, default=0.052)
    parser.add_argument("--robot_base_z", type=float, default=0.27)
    parser.add_argument("--robot_yaw_deg", type=float, default=180.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_name = args.run_name or time.strftime("franka_cube_ggx_curobo_%Y%m%d_%H%M%S")
    run_dir = (args.output_dir.expanduser().resolve() / run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    graspgenx_root = args.graspgenx_root.expanduser().resolve()
    if not (graspgenx_root / "end2end/e2e_grasp_demo.py").is_file():
        raise FileNotFoundError(f"Invalid GraspGenX root: {graspgenx_root}")

    if args.curobo_root is not None:
        curobo_root = args.curobo_root.expanduser().resolve()
        os.environ.setdefault("GRASPGENX_CUROBO_DIR", str(curobo_root))
        if str(curobo_root) not in sys.path:
            sys.path.insert(0, str(curobo_root))
    os.environ.setdefault("GRASPGENX_ROOT", str(graspgenx_root))
    if (graspgenx_root / "ext/graspgenx_checkpoints").is_dir():
        os.environ.setdefault("GRASPGENX_CHECKPOINT_DIR", str(graspgenx_root / "ext/graspgenx_checkpoints"))
    if (graspgenx_root / "ext/gripper_descriptions").is_dir():
        os.environ.setdefault("GRASPGENX_GRIPPER_CFG_DIR", str(graspgenx_root / "ext/gripper_descriptions"))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("PYGLET_HEADLESS", "true")

    e2e_dir = graspgenx_root / "end2end"
    for path in (str(graspgenx_root), str(e2e_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)

    import numpy as np
    import torch

    from e2e_grasp_demo import collision_world_to_curobo, export_trajectory, init_planner, plan_to_grasp, run_graspgen
    from robot_profiles import RobotProfile
    from scene_builder import build_scene, load_yaml
    from tasks import get_task
    from trajectory_visualizer import URDFFK

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    env_info = _validate_environment()
    _write_json(run_dir / "environment.json", env_info)

    cube_mesh = run_dir / "assets/cube_60mm.obj"
    mesh_metadata = _write_cube_obj(cube_mesh, float(args.cube_size))
    robot_config = _make_robot_config(
        graspgenx_root,
        run_dir,
        robot_base_z=float(args.robot_base_z),
        robot_yaw_deg=float(args.robot_yaw_deg),
    )
    env_config = _make_env_config(args, run_dir, cube_mesh)

    robot_cfg = load_yaml(robot_config)
    env_cfg = load_yaml(env_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    bundle = build_scene(env_cfg, robot_cfg, str(cube_mesh), seed=args.seed)
    object_extents = np.asarray(bundle.object_mesh.extents, dtype=np.float64)
    if not np.allclose(object_extents, float(args.cube_size), atol=2e-4, rtol=1e-3):
        raise RuntimeError(
            "Generated scene is not the requested cube size: "
            f"extents={object_extents.tolist()} cube_size={args.cube_size}"
        )

    _write_json(
        run_dir / "run_config.json",
        {
            "args": vars(args),
            "mesh": mesh_metadata,
            "robot_config": str(robot_config),
            "env_config": str(env_config),
            "robot_profile": profile.NAME,
            "object_world_T": bundle.object_world_T,
            "object_extents_m": object_extents,
            "robot_base_T": bundle.robot_base_T,
            "collision_obstacles": [ob.__dict__ for ob in bundle.collision_world],
            "dextrah_action_scales": {
                "position": [0.060, 0.060, 0.045],
                "rotation": [0.25, 0.25, 0.30],
                "gripper": "raw -1 close / +1 open",
            },
        },
    )

    grasps_world, conf = run_graspgen(
        bundle,
        robot_cfg,
        num_sample_points=int(args.num_sample_points),
        num_grasps=int(args.num_grasps),
        topk=int(args.topk),
        seed=int(args.seed),
        grasp_threshold=float(args.grasp_threshold),
        planner=str(args.grasp_planner),
        moe_obb_density=str(args.moe_obb_density),
        obb_only=False,
    )
    if len(grasps_world) == 0:
        raise RuntimeError("GraspGenX returned zero grasps for the DEXTRAH cube")

    scene_model = collision_world_to_curobo(bundle.collision_world, bundle.robot_base_T)
    planner = init_planner(
        robot_config,
        robot_cfg,
        scene_model,
        max_goalset=max(int(args.max_plan_attempts), len(grasps_world), 1),
    )
    success, result, target_idx, pregrasp_traj, lift_traj = plan_to_grasp(
        planner,
        robot_cfg,
        grasps_world,
        conf,
        max_attempts=int(args.max_plan_attempts),
        seed=int(args.seed),
        robot_base_T=bundle.robot_base_T,
        force_idx=-1,
        rank_by_confidence=bool(args.rank_grasps_by_confidence),
    )
    if not success or target_idx < 0 or pregrasp_traj is None or len(pregrasp_traj) == 0:
        raise RuntimeError("cuRobo failed to plan an approach/grasp trajectory for the DEXTRAH cube")
    if lift_traj is None or len(lift_traj) == 0:
        raise RuntimeError("cuRobo returned no lift segment for the DEXTRAH cube")

    task = get_task("pick_and_lift")
    task_result = task.plan_actions(
        planner=planner,
        bundle=bundle,
        profile=profile,
        grasps_world=grasps_world,
        conf=conf,
        target_idx=target_idx,
        pregrasp_traj=pregrasp_traj,
        lift_traj=lift_traj,
        env_cfg=env_cfg,
        close_frames=int(args.close_frames),
        hold_frames=int(args.hold_frames),
        hold_after_close_frames=int(args.hold_after_close_frames),
        playback_mode="dynamic",
        result=result,
    )

    trajectory_json = run_dir / "trajectory.json"
    camera = (env_cfg.get("visual") or {}).get("camera", {})
    camera_eye = list(camera.get("eye", [0.30, -0.82, 1.55]))
    camera_target = list(camera.get("target", [float(args.cube_x), float(args.cube_y), 0.866]))
    fk = URDFFK(profile.urdf_path, asset_root=profile.asset_root_path)
    export_trajectory(
        bundle=bundle,
        fk=fk,
        profile=profile,
        joint_traj=task_result.joint_traj,
        grasps_world=grasps_world,
        target_idx=target_idx,
        camera_eye=camera_eye,
        camera_target=camera_target,
        output_path=trajectory_json,
        fps=int(args.sim_fps),
    )
    _augment_kinematic_object_poses(
        trajectory_json,
        fk=fk,
        profile=profile,
        bundle=bundle,
        joint_traj=task_result.joint_traj,
        segments=task_result.segments,
        grasp_world_T=grasps_world[target_idx],
    )

    plan_segments_src = getattr(result, "_segments", {}) if result is not None else {}
    plan_segments = {
        "approach": int(plan_segments_src.get("approach").shape[0])
        if plan_segments_src.get("approach") is not None
        else 0,
        "grasp": int(plan_segments_src.get("grasp").shape[0])
        if plan_segments_src.get("grasp") is not None
        else 0,
        "lift": int(lift_traj.shape[0]),
    }
    if plan_segments["approach"] <= 0 or plan_segments["grasp"] <= 0 or plan_segments["lift"] <= 0:
        raise RuntimeError(f"Invalid cuRobo segment lengths: {plan_segments}")
    task_segments = {name: int(count) for name, count in task_result.segments}
    summary = PlanSummary(
        status="passed",
        source="graspgenx_curobo",
        curobo_validated=True,
        run_name=run_name,
        trajectory_json=str(trajectory_json),
        selected_grasp_index=int(target_idx),
        selected_grasp_confidence=float(conf[target_idx]),
        num_grasps=int(len(grasps_world)),
        plan_segments=plan_segments,
        task_segments=task_segments,
    )
    _write_json(
        run_dir / "plan_summary.json",
        {
            **asdict(summary),
            "selected_grasp_world": grasps_world[target_idx],
            "confidence_min": float(np.min(conf)),
            "confidence_max": float(np.max(conf)),
            "pregrasp_traj_shape": list(pregrasp_traj.shape),
            "lift_traj_shape": list(lift_traj.shape),
            "trajectory_frames": int(json.loads(trajectory_json.read_text(encoding="utf-8")).get("total_frames", 0)),
        },
    )
    print(
        "DEXTRAH_CUBE_GRASPGENX_CUROBO_PLAN_PASSED "
        + json.dumps(asdict(summary), sort_keys=True),
        flush=True,
    )
    print(f"results={run_dir}", flush=True)


if __name__ == "__main__":
    main()
