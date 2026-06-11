#!/usr/bin/env python3
"""Plan a DEXTRAH Franka star grasp with GraspGenX and cuRobo.

This script is intentionally DEXTRAH-owned, but it reuses the GraspGenX
``end2end`` pipeline:

1. Generate a small Franka-graspable star mesh matching the DEXTRAH kitting
   task geometry.
2. Build a DEXTRAH-coordinate tabletop scene for GraspGenX and cuRobo.
3. Run GraspGenX grasp inference.
4. Run cuRobo approach/grasp/lift planning.
5. Export ``trajectory.json`` with either Newton dynamic playback or a
   kinematic attached-object fallback.

The exported trajectory can be rendered by
``render_star_kitting_env.py --franka_motion trajectory``.
"""

from __future__ import annotations

import argparse
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
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")


def _star_vertices(outer_radius: float, inner_radius: float, *, points: int = 5) -> list[tuple[float, float]]:
    vertices: list[tuple[float, float]] = []
    for idx in range(points * 2):
        radius = outer_radius if idx % 2 == 0 else inner_radius
        angle = idx * math.pi / points
        vertices.append((radius * math.cos(angle), radius * math.sin(angle)))
    return vertices


def _write_star_obj(path: Path, outer_radius: float, inner_radius: float, thickness: float) -> dict[str, Any]:
    """Write a centered extruded star OBJ and return geometry metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    verts_2d = _star_vertices(outer_radius, inner_radius)
    z0 = -0.5 * float(thickness)
    z1 = 0.5 * float(thickness)
    verts = [(x, y, z0) for x, y in verts_2d] + [(x, y, z1) for x, y in verts_2d]
    bottom_center_idx = len(verts) + 1
    top_center_idx = len(verts) + 2
    verts.append((0.0, 0.0, z0))
    verts.append((0.0, 0.0, z1))

    faces: list[tuple[int, ...]] = []
    n = len(verts_2d)
    for idx in range(n):
        nxt = (idx + 1) % n
        bottom_a = idx + 1
        bottom_b = nxt + 1
        top_a = n + idx + 1
        top_b = n + nxt + 1
        faces.append((top_center_idx, top_a, top_b))
        faces.append((bottom_center_idx, bottom_b, bottom_a))
        faces.append((bottom_a, bottom_b, top_b, top_a))

    with path.open("w", encoding="utf-8") as f:
        f.write("# DEXTRAH generated Franka-kitting star mesh\n")
        for x, y, z in verts:
            f.write(f"v {x:.9f} {y:.9f} {z:.9f}\n")
        for face in faces:
            f.write("f " + " ".join(str(i) for i in face) + "\n")

    return {
        "mesh": str(path),
        "outer_radius": float(outer_radius),
        "inner_radius": float(inner_radius),
        "thickness": float(thickness),
        "vertices": len(verts),
        "faces": len(faces),
    }


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


def _make_robot_config(graspgenx_root: Path, run_dir: Path, robot_base_z: float, robot_yaw_deg: float) -> Path:
    src = graspgenx_root / "end2end/robots/franka_panda.yaml"
    cfg = _load_yaml(src)
    cfg["robot_base_pose"] = {
        "translation": [0.0, 0.0, float(robot_base_z)],
        "quaternion_xyzw": _yaw_quat_xyzw(robot_yaw_deg),
    }
    out = run_dir / "configs/franka_panda_dextrah.yaml"
    _write_yaml(out, cfg)
    return out


def _make_env_config(args: argparse.Namespace, run_dir: Path, star_mesh: Path) -> Path:
    surface_z = float(args.table_height) + 0.5 * float(args.table_top_thickness)
    star_base_z = surface_z + float(args.object_surface_offset)
    star_center_z = star_base_z + 0.5 * float(args.star_thickness)
    fixture_center_z = surface_z + 0.5 * float(args.fixture_thickness)

    # The procedural table is visual-only here. Exact cuRobo cuboids below
    # define the tabletop and fixture collision in DEXTRAH coordinates.
    cfg: dict[str, Any] = {
        "name": "dextrah_franka_star_kitting_pick",
        "assets": [
            {
                "id": "table",
                "type": "procedural_table",
                "params": {
                    "width": float(args.table_short_x),
                    "depth": float(args.table_long_y),
                    "height": float(args.table_height),
                    "thickness": float(args.table_top_thickness),
                    "leg_thickness": 0.05,
                },
                "pose": {
                    "translation": [float(args.table_center_x), 0.0, 0.0],
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                "support_label": "table_top",
                "collision": "skip",
            }
        ],
        "object_slot": {
            "world_position": [float(args.table_center_x), float(args.pickup_y), star_base_z],
            "mesh_scale": 1.0,
            "randomize": {"yaw_range_deg": [float(args.star_start_yaw_deg), float(args.star_start_yaw_deg)]},
        },
        "extra_collision": [
            {
                "name": "dextrah_tabletop",
                "type": "cuboid",
                "dims": [
                    float(args.table_short_x),
                    float(args.table_long_y),
                    float(args.table_top_thickness),
                ],
                "pose": [
                    float(args.table_center_x),
                    0.0,
                    float(args.table_height),
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "name": "dextrah_fixture_block",
                "type": "cuboid",
                "dims": [
                    float(args.fixture_size_x),
                    float(args.fixture_size_y),
                    float(args.fixture_thickness),
                ],
                "pose": [
                    float(args.table_center_x),
                    float(args.fixture_y),
                    fixture_center_z,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                ],
            },
        ],
        "visual": {
            "show_ground_grid": True,
            "background_color": [0.95, 0.95, 0.95],
            "camera": {
                "eye": [0.45, -0.92, 2.10],
                "target": [float(args.table_center_x), 0.0, surface_z + 0.12],
            },
        },
    }
    # GraspGenX build_scene receives mesh_file separately, but keeping it in
    # the generated YAML helps the run directory remain self-describing.
    cfg["object_slot"]["mesh_file_hint"] = str(star_mesh)
    cfg["dextrah_geometry"] = {
        "table_surface_z": surface_z,
        "star_center": [float(args.table_center_x), float(args.pickup_y), star_center_z],
        "fixture_center": [float(args.table_center_x), float(args.fixture_y), fixture_center_z],
        "fixture_yaw_deg": float(args.fixture_yaw_deg),
    }
    out = run_dir / "configs/dextrah_franka_star_kitting_pick.yaml"
    _write_yaml(out, cfg)
    return out


@dataclass
class PlanSummary:
    status: str
    run_name: str
    playback_mode: str
    trajectory_json: str
    selected_grasp_index: int
    selected_grasp_confidence: float
    num_grasps: int
    plan_segments: dict[str, int]
    task_segments: dict[str, int]


def _joint_cfg_from_row(profile: Any, joint_row: Any) -> dict[str, float]:
    n_arm = int(profile.n_arm)
    cfg: dict[str, float] = {}
    for name, value in zip(profile.arm_joint_names, joint_row[:n_arm]):
        cfg[name] = float(value)
    for idx, name in enumerate(profile.gripper_joint_names):
        col = n_arm + idx
        cfg[name] = (
            float(joint_row[col])
            if col < len(joint_row)
            else profile.open_value(name)
        )
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
        profile.grasp_to_tool_transform, dtype=float
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
            object_T = (
                np.asarray(link_poses[profile.tool_frame], dtype=float)
                @ object_in_tool_T
            )
        frame.setdefault("object_poses", {})["object"] = object_T.tolist()

    payload.setdefault("dextrah", {})
    payload["dextrah"]["object_pose_mode"] = "kinematic_attached_to_tool"
    payload["dextrah"]["object_pose_object_id"] = "object"
    payload["dextrah"]["attachment_start_frame"] = int(attach_start)
    trajectory_json.write_text(json.dumps(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, default=_repo_root() / "local_results/graspgenx_franka_star")
    parser.add_argument("--run_name", type=str, default=None)
    parser.add_argument("--graspgenx_root", type=Path, default=_default_graspgenx_root())
    parser.add_argument("--curobo_root", type=Path, default=_default_curobo_root())
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num_grasps", type=int, default=200)
    parser.add_argument("--topk", type=int, default=80)
    parser.add_argument("--grasp_threshold", type=float, default=0.7)
    parser.add_argument("--grasp_planner", choices=("graspmoe", "diffusion", "topdown"), default="graspmoe")
    parser.add_argument("--moe_obb_density", choices=("sparse", "dense", "none"), default="dense")
    parser.add_argument("--max_plan_attempts", type=int, default=80)
    parser.add_argument("--rank_grasps_by_confidence", action="store_true")
    parser.add_argument("--sim_fps", type=int, default=60)
    parser.add_argument("--sim_dt", type=float, default=0.001)
    parser.add_argument(
        "--playback_mode",
        choices=("dynamic", "kinematic"),
        default="dynamic",
        help=(
            "dynamic replays the plan in Newton; kinematic exports planned "
            "joints and attaches the object after close."
        ),
    )
    parser.add_argument("--settle_frames", type=int, default=30)
    parser.add_argument("--object_mass", type=float, default=0.05)
    parser.add_argument("--object_mu", type=float, default=10.0)
    parser.add_argument("--finger_mu", type=float, default=3.0)
    parser.add_argument("--hold_frames", type=int, default=60)
    parser.add_argument("--hold_after_close_frames", type=int, default=90)
    parser.add_argument("--close_frames", type=int, default=30)
    parser.add_argument("--star_outer_radius", type=float, default=0.032)
    parser.add_argument("--star_inner_radius", type=float, default=0.0145)
    parser.add_argument("--star_thickness", type=float, default=0.040)
    parser.add_argument("--star_start_yaw_deg", type=float, default=-24.0)
    parser.add_argument("--fixture_yaw_deg", type=float, default=18.0)
    parser.add_argument("--fixture_size_x", type=float, default=0.18)
    parser.add_argument("--fixture_size_y", type=float, default=0.18)
    parser.add_argument("--fixture_thickness", type=float, default=0.060)
    parser.add_argument("--fixture_clearance", type=float, default=0.006)
    parser.add_argument("--table_center_x", type=float, default=-0.72)
    parser.add_argument("--table_short_x", type=float, default=0.90)
    parser.add_argument("--table_long_y", type=float, default=1.32)
    parser.add_argument("--table_height", type=float, default=0.72)
    parser.add_argument("--table_top_thickness", type=float, default=0.052)
    parser.add_argument("--pickup_y", type=float, default=-0.26)
    parser.add_argument("--fixture_y", type=float, default=0.26)
    parser.add_argument("--object_surface_offset", type=float, default=0.001)
    parser.add_argument("--robot_base_z", type=float, default=0.50)
    parser.add_argument("--robot_yaw_deg", type=float, default=180.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_name = args.run_name or time.strftime("franka_star_ggx_curobo_%Y%m%d_%H%M%S")
    run_dir = (args.output_dir.expanduser().resolve() / run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    graspgenx_root = args.graspgenx_root.expanduser().resolve()
    if not (graspgenx_root / "end2end/e2e_grasp_demo.py").is_file():
        raise FileNotFoundError(f"Invalid GraspGenX root: {graspgenx_root}")
    if args.curobo_root is not None:
        curobo_root = args.curobo_root.expanduser().resolve()
        os.environ.setdefault("GRASPGENX_CUROBO_DIR", str(curobo_root))
    os.environ.setdefault("GRASPGENX_ROOT", str(graspgenx_root))
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    os.environ.setdefault("PYGLET_HEADLESS", "true")

    e2e_dir = graspgenx_root / "end2end"
    for path in (str(graspgenx_root), str(e2e_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)

    import numpy as np
    import torch

    from e2e_grasp_demo import collision_world_to_curobo, init_planner, plan_to_grasp, run_graspgen
    from robot_profiles import RobotProfile
    from scene_builder import build_scene, load_yaml
    from tasks import get_task

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    star_mesh = run_dir / "assets/star_object.obj"
    mesh_metadata = _write_star_obj(
        star_mesh,
        outer_radius=float(args.star_outer_radius),
        inner_radius=float(args.star_inner_radius),
        thickness=float(args.star_thickness),
    )
    robot_config = _make_robot_config(graspgenx_root, run_dir, args.robot_base_z, args.robot_yaw_deg)
    env_config = _make_env_config(args, run_dir, star_mesh)

    robot_cfg = load_yaml(robot_config)
    env_cfg = load_yaml(env_config)
    profile = RobotProfile.from_yaml(robot_cfg)
    bundle = build_scene(env_cfg, robot_cfg, str(star_mesh), seed=args.seed)

    _write_json(
        run_dir / "run_config.json",
        {
            "args": vars(args),
            "mesh": mesh_metadata,
            "robot_config": str(robot_config),
            "env_config": str(env_config),
            "robot_profile": profile.NAME,
            "object_world_T": bundle.object_world_T,
            "robot_base_T": bundle.robot_base_T,
            "collision_obstacles": [ob.__dict__ for ob in bundle.collision_world],
        },
    )

    grasps_world, conf = run_graspgen(
        bundle,
        robot_cfg,
        num_sample_points=2000,
        num_grasps=int(args.num_grasps),
        topk=int(args.topk),
        seed=int(args.seed),
        grasp_threshold=float(args.grasp_threshold),
        planner=str(args.grasp_planner),
        moe_obb_density=str(args.moe_obb_density),
        obb_only=False,
    )
    if len(grasps_world) == 0:
        raise RuntimeError("GraspGenX returned zero grasps for the DEXTRAH star")

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
    if not success or target_idx < 0 or pregrasp_traj is None:
        raise RuntimeError("cuRobo failed to plan a DEXTRAH star grasp")
    if lift_traj is None or lift_traj.shape[0] == 0:
        raise RuntimeError("cuRobo returned no lift segment for the DEXTRAH star")

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
    camera_eye = list(camera.get("eye", [0.45, -0.92, 2.10]))
    camera_target = list(
        camera.get("target", [float(args.table_center_x), 0.0, 0.866])
    )
    if args.playback_mode == "dynamic":
        from dynamic_playback import simulate_and_export

        simulate_and_export(
            bundle=bundle,
            profile=profile,
            joint_traj=task_result.joint_traj,
            out_path=trajectory_json,
            grasps_world=grasps_world,
            target_idx=target_idx,
            camera_eye=camera_eye,
            camera_target=camera_target,
            sim_fps=int(args.sim_fps),
            sim_dt=float(args.sim_dt),
            settle_frames=int(args.settle_frames),
            object_mass=float(args.object_mass),
            object_mu=float(args.object_mu),
            finger_mu=float(args.finger_mu),
        )
    else:
        from e2e_grasp_demo import export_trajectory
        from trajectory_visualizer import URDFFK

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
    task_segments = {name: int(count) for name, count in task_result.segments}
    summary = PlanSummary(
        status="passed",
        run_name=run_name,
        playback_mode=str(args.playback_mode),
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
            "trajectory_frames": int(json.loads(trajectory_json.read_text()).get("total_frames", 0)),
        },
    )
    print("DEXTRAH_GRASPGENX_CUROBO_PLAN_PASSED", json.dumps(asdict(summary), sort_keys=True), flush=True)
    print(f"results={run_dir}", flush=True)


if __name__ == "__main__":
    main()
