"""Validate and demo the bimanual YAM cube-grasp environment."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", type=str, default="Dextrah-Bimanual-YAM-Cube-Grasp")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--num_steps", type=int, default=480)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--metrics_path", type=str, default=None)
parser.add_argument("--video", action="store_true", default=False)
parser.add_argument("--video_length", type=int, default=480)
parser.add_argument("--video_folder", type=str, default=None)
parser.add_argument("--cube_spawn_xy_randomization", type=float, default=0.0)
parser.add_argument("--print_interval", type=int, default=20)
parser.add_argument("--lift_height", type=float, default=0.14)
parser.add_argument("--continue_after_success", action="store_true", default=False)
parser.add_argument("--disable_fabric", action="store_true", default=False)
parser.add_argument("--camera_eye", type=float, nargs=3, default=(-0.50, 0.0, 0.81))
parser.add_argument("--camera_target", type=float, nargs=3, default=(-0.375, 0.0, 0.10))
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.video:
    args_cli.enable_cameras = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg

import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup  # noqa: F401
from dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.bimanual_yam_cube_grasp_env_cfg import (
    MOLMOACT2_REST_JOINT_POS,
    YAM_MJCF_PATH,
    YAM_USD_PATH,
)
from dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.bimanual_yam_cube_grasp_rewards import (
    compute_bimanual_yam_cube_grasp_rewards,
)


MOLMOACT2_TOP_CAM_LOCAL_POS = (0.15, 0.0, 0.80)
MOLMOACT2_TOP_CAM_QUAT_WXYZ = (0.7660444431189782, 0.0, 0.6427876096865391, 0.0)
MOLMOACT2_TOP_CAM_FOV_DEG = 69.4
MOLMOACT2_TOP_CAM_WIDTH = 640
MOLMOACT2_TOP_CAM_HEIGHT = 360
MOLMOACT2_TOP_CAM_FORWARD = (
    1.0
    - 2.0
    * (
        MOLMOACT2_TOP_CAM_QUAT_WXYZ[1] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[1]
        + MOLMOACT2_TOP_CAM_QUAT_WXYZ[2] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[2]
    ),
    2.0
    * (
        MOLMOACT2_TOP_CAM_QUAT_WXYZ[1] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[2]
        + MOLMOACT2_TOP_CAM_QUAT_WXYZ[0] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[3]
    ),
    2.0
    * (
        MOLMOACT2_TOP_CAM_QUAT_WXYZ[1] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[3]
        - MOLMOACT2_TOP_CAM_QUAT_WXYZ[0] * MOLMOACT2_TOP_CAM_QUAT_WXYZ[2]
    ),
)
MOLMOACT2_TOP_CAM_WORLD_EYE = (
    -0.65 + MOLMOACT2_TOP_CAM_LOCAL_POS[0],
    0.0 + MOLMOACT2_TOP_CAM_LOCAL_POS[1],
    0.01 + MOLMOACT2_TOP_CAM_LOCAL_POS[2],
)
_TOP_CAM_TABLE_TARGET_SCALE = (
    (MOLMOACT2_TOP_CAM_WORLD_EYE[2] - 0.10) / max(-MOLMOACT2_TOP_CAM_FORWARD[2], 1.0e-6)
)
MOLMOACT2_TOP_CAM_WORLD_TARGET = (
    MOLMOACT2_TOP_CAM_WORLD_EYE[0] + _TOP_CAM_TABLE_TARGET_SCALE * MOLMOACT2_TOP_CAM_FORWARD[0],
    MOLMOACT2_TOP_CAM_WORLD_EYE[1] + _TOP_CAM_TABLE_TARGET_SCALE * MOLMOACT2_TOP_CAM_FORWARD[1],
    0.10,
)

DEMO_CONTACT_JOINT_POS = {
    # Contact waypoint solved against the spawned MJCF-derived Isaac USD. The
    # rollout still starts from the MolmoAct2 rest keyframe; this waypoint is
    # approached gradually after the grippers have already closed.
    "left_joint1": -0.187994,
    "left_joint2": 2.189542,
    "left_joint3": 1.239098,
    "left_joint4": -0.406251,
    "left_joint5": 1.570800,
    "left_joint6": 0.745140,
    "right_joint1": 0.262975,
    "right_joint2": 1.918793,
    "right_joint3": 1.051843,
    "right_joint4": -0.183927,
    "right_joint5": -0.874573,
    "right_joint6": 0.968451,
}
DEMO_STANDOFF_JOINT_ALPHA = 0.88

def _mean(value) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().float().mean().cpu())
    return float(value)


def _tensor_list(value: torch.Tensor) -> list[float] | list[list[float]]:
    return value.detach().float().cpu().tolist()


class CheckRecorder:
    def __init__(self):
        self.records: list[dict[str, object]] = []

    def check(self, name: str, passed: bool, **details) -> None:
        self.records.append({"name": name, "passed": bool(passed), "details": details})

    @property
    def passed(self) -> bool:
        return all(bool(record["passed"]) for record in self.records)


def _configure_camera(env_cfg, task_env=None) -> None:
    if not hasattr(env_cfg, "viewer"):
        return
    eye = tuple(float(v) for v in args_cli.camera_eye)
    target = tuple(float(v) for v in args_cli.camera_target)
    if task_env is not None and hasattr(task_env, "scene"):
        env_origin = tuple(float(v) for v in task_env.scene.env_origins[0].detach().cpu())
        eye = tuple(eye[idx] + env_origin[idx] for idx in range(3))
        target = tuple(target[idx] + env_origin[idx] for idx in range(3))
    env_cfg.viewer.eye = eye
    env_cfg.viewer.lookat = target
    env_cfg.viewer.origin_type = "world"
    for fov_attr in ("fov", "camera_fov"):
        if hasattr(env_cfg.viewer, fov_attr):
            try:
                setattr(env_cfg.viewer, fov_attr, MOLMOACT2_TOP_CAM_FOV_DEG)
            except Exception:
                pass
    if task_env is not None and hasattr(task_env, "sim"):
        try:
            task_env.sim.set_camera_view(eye=eye, target=target, camera_prim_path=env_cfg.viewer.cam_prim_path)
        except Exception as exc:
            print(f"[WARN] Could not set validation camera: {exc}", flush=True)


def _run_registration_checks(task: str, checks: CheckRecorder) -> None:
    try:
        spec = gym.spec(task)
    except Exception as exc:
        checks.check("task_registration_resolves", False, task=task, error=repr(exc))
        return
    checks.check("task_registration_resolves", True, task=task, entry_point=str(spec.entry_point))


def _run_asset_checks(checks: CheckRecorder) -> None:
    mjcf_path = Path(YAM_MJCF_PATH)
    usd_path = Path(YAM_USD_PATH)
    checks.check(
        "yam_mjcf_asset_exists",
        mjcf_path.is_file() and mjcf_path.stat().st_size > 0,
        yam_mjcf_path=str(mjcf_path),
        size_bytes=mjcf_path.stat().st_size if mjcf_path.exists() else 0,
    )
    checks.check(
        "yam_robot_usd_asset_exists",
        usd_path.is_file() and usd_path.stat().st_size > 1024,
        yam_usd_path=str(usd_path),
        size_bytes=usd_path.stat().st_size if usd_path.exists() else 0,
    )
    checks.check(
        "yam_robot_uses_direct_mjcf_usd_cache",
        "yam_mjcf_usd" in usd_path.parts,
        yam_usd_path=str(usd_path),
    )
    if usd_path.is_file():
        try:
            from pxr import Usd, UsdGeom, UsdPhysics

            stage = Usd.Stage.Open(str(usd_path), Usd.Stage.LoadAll)
            if stage is None:
                checks.check("yam_robot_usd_opens", False, yam_usd_path=str(usd_path))
                return
            stage.Load()
            default_prim = stage.GetDefaultPrim()

            rigid_body_paths = []
            invalid_mass_bodies = []
            joint_paths = []
            revolute_joint_paths = []
            prismatic_joint_paths = []
            for prim in stage.TraverseAll():
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                    rigid_body_paths.append(str(prim.GetPath()))
                    mass_api = UsdPhysics.MassAPI(prim)
                    mass = mass_api.GetMassAttr().Get()
                    diag = mass_api.GetDiagonalInertiaAttr().Get()
                    center = mass_api.GetCenterOfMassAttr().Get()
                    mass_valid = mass is not None and math.isfinite(float(mass)) and float(mass) > 0.0
                    diag_valid = diag is not None and all(
                        math.isfinite(float(value)) and float(value) > 0.0 for value in diag
                    )
                    center_valid = center is not None and all(math.isfinite(float(value)) for value in center)
                    if not (mass_valid and diag_valid and center_valid):
                        invalid_mass_bodies.append(
                            {
                                "path": str(prim.GetPath()),
                                "mass": float(mass) if mass is not None and math.isfinite(float(mass)) else str(mass),
                                "diagonal_inertia": [float(value) for value in diag] if diag is not None else None,
                                "center_of_mass": [float(value) for value in center] if center is not None else None,
                            }
                        )
                if prim.IsA(UsdPhysics.Joint):
                    joint_paths.append(str(prim.GetPath()))
                if prim.IsA(UsdPhysics.RevoluteJoint):
                    revolute_joint_paths.append(str(prim.GetPath()))
                if prim.IsA(UsdPhysics.PrismaticJoint):
                    prismatic_joint_paths.append(str(prim.GetPath()))

            visual_mesh_paths = []
            collision_paths = []
            for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
                prim_path = str(prim.GetPath())
                if prim.IsA(UsdGeom.Mesh) and "/visuals/" in prim_path:
                    visual_mesh_paths.append(prim_path)
                if prim.HasAPI(UsdPhysics.CollisionAPI):
                    collision_paths.append(prim_path)

            expected_joint_names = set(MOLMOACT2_REST_JOINT_POS)
            observed_joint_names = {Path(path).name for path in joint_paths}
            missing_joint_names = sorted(expected_joint_names - observed_joint_names)
            checks.check(
                "yam_robot_usd_opens",
                default_prim.IsValid() if default_prim else False,
                default_prim=str(default_prim.GetPath()) if default_prim else None,
                yam_usd_path=str(usd_path),
            )
            checks.check(
                "yam_robot_usd_contains_official_mjcf_articulation",
                len(rigid_body_paths) >= 18
                and len(revolute_joint_paths) == 12
                and len(prismatic_joint_paths) == 4
                and not missing_joint_names,
                rigid_body_count=len(rigid_body_paths),
                joint_count=len(joint_paths),
                revolute_joint_count=len(revolute_joint_paths),
                prismatic_joint_count=len(prismatic_joint_paths),
                missing_joint_names=missing_joint_names,
                rigid_body_paths=rigid_body_paths,
            )
            checks.check(
                "yam_robot_usd_mass_properties_are_valid",
                not invalid_mass_bodies,
                invalid_mass_bodies=invalid_mass_bodies,
            )
            checks.check(
                "yam_robot_usd_contains_visuals_and_colliders",
                len(visual_mesh_paths) >= 28 and len(collision_paths) >= 30,
                visual_mesh_count=len(visual_mesh_paths),
                collision_prim_count=len(collision_paths),
                first_visual_mesh_paths=visual_mesh_paths[:8],
                first_collision_paths=collision_paths[:8],
                traversal="Usd.TraverseInstanceProxies",
            )
        except Exception as exc:
            checks.check(
                "yam_robot_usd_introspection",
                False,
                yam_usd_path=str(usd_path),
                error=repr(exc),
            )


def _reward_total(**kwargs) -> torch.Tensor:
    return sum(compute_bimanual_yam_cube_grasp_rewards(**kwargs))


def _run_reward_checks(device: str, checks: CheckRecorder) -> None:
    zeros = torch.zeros(1, device=device)
    base = {
        "left_hold_to_cube_dist": torch.tensor([0.22], device=device),
        "right_hold_to_cube_dist": torch.tensor([0.22], device=device),
        "left_gripper_width": torch.tensor([0.17], device=device),
        "right_gripper_width": torch.tensor([0.17], device=device),
        "cube_lift_height": zeros.clone(),
        "cube_goal_height_error": torch.tensor([0.14], device=device),
        "cube_xy_error": zeros.clone(),
        "finger_table_clearance": torch.tensor([0.04], device=device),
        "left_side_alignment": torch.tensor([0.0], device=device),
        "right_side_alignment": torch.tensor([0.0], device=device),
        "in_success_region": torch.zeros(1, dtype=torch.bool, device=device),
        "actions": torch.zeros(1, 14, device=device),
        "target_lift_height": 0.14,
        "max_gripper_width": 0.17,
        "table_clearance_margin": 0.010,
        "approach_weight": 2.0,
        "approach_sharpness": 10.0,
        "enclosure_weight": 1.2,
        "enclosure_sharpness": 8.0,
        "side_alignment_weight": 1.0,
        "lift_weight": 12.0,
        "height_tracking_weight": 3.0,
        "height_tracking_sharpness": 18.0,
        "xy_stability_weight": 1.0,
        "xy_stability_sharpness": 12.0,
        "success_bonus_weight": 18.0,
        "close_action_weight": 0.3,
        "lift_action_weight": 1.0,
        "descend_action_penalty_weight": -1.0,
        "table_clearance_penalty_weight": -2.0,
        "gripper_close_reg_weight": -0.001,
        "action_penalty_weight": -0.0005,
    }
    near = dict(base)
    near["left_hold_to_cube_dist"] = torch.tensor([0.070], device=device)
    near["right_hold_to_cube_dist"] = torch.tensor([0.070], device=device)
    checks.check(
        "reward_approach_increases_near_cube",
        bool((_reward_total(**near) > _reward_total(**base)).item()),
        far_reward=_mean(_reward_total(**base)),
        near_reward=_mean(_reward_total(**near)),
    )

    sided = dict(near)
    sided["left_side_alignment"] = torch.tensor([1.0], device=device)
    sided["right_side_alignment"] = torch.tensor([1.0], device=device)
    checks.check(
        "reward_prefers_left_and_right_side_alignment",
        bool((_reward_total(**sided) > _reward_total(**near)).item()),
        near_reward=_mean(_reward_total(**near)),
        sided_reward=_mean(_reward_total(**sided)),
    )

    closed = dict(sided)
    closed["left_gripper_width"] = torch.tensor([0.025], device=device)
    closed["right_gripper_width"] = torch.tensor([0.025], device=device)
    closed["actions"] = torch.zeros(1, 14, device=device)
    closed["actions"][:, 6] = -1.0
    closed["actions"][:, 13] = -1.0
    checks.check(
        "reward_close_action_is_positive_near_cube",
        bool((compute_bimanual_yam_cube_grasp_rewards(**closed)[7] > 0.0).item()),
        close_action_reward=_mean(compute_bimanual_yam_cube_grasp_rewards(**closed)[7]),
    )

    lifted = dict(closed)
    lifted["cube_lift_height"] = torch.tensor([0.14], device=device)
    lifted["cube_goal_height_error"] = torch.tensor([0.0], device=device)
    lifted["in_success_region"] = torch.ones(1, dtype=torch.bool, device=device)
    checks.check(
        "reward_lift_and_success_dominate_prelift",
        bool((_reward_total(**lifted) > 2.0 * _reward_total(**closed)).item()),
        prelift_reward=_mean(_reward_total(**closed)),
        lifted_reward=_mean(_reward_total(**lifted)),
    )


def _run_layout_checks(task_env, checks: CheckRecorder) -> None:
    cfg = task_env.cfg
    checks.check(
        "molmoact2_yam_relative_robot_pose",
        abs(float(cfg.robot_base_x) + 0.65) <= 1.0e-6
        and abs(float(cfg.robot_base_y)) <= 1.0e-6
        and abs(float(cfg.robot_base_z) - 0.01) <= 1.0e-6,
        robot_base_pos=[float(cfg.robot_base_x), float(cfg.robot_base_y), float(cfg.robot_base_z)],
    )
    checks.check(
        "molmoact2_object_anchor_x",
        abs(float(cfg.pickup_x) + 0.30) <= 1.0e-6,
        pickup=[float(cfg.pickup_x), float(cfg.pickup_y), float(cfg.cube_spawn_z)],
    )
    checks.check(
        "table_spans_robot_front_workspace",
        float(cfg.table_center_x - 0.5 * cfg.table_size_x) <= float(cfg.pickup_x) <= float(
            cfg.table_center_x + 0.5 * cfg.table_size_x
        ),
        table_x_bounds=[
            float(cfg.table_center_x - 0.5 * cfg.table_size_x),
            float(cfg.table_center_x + 0.5 * cfg.table_size_x),
        ],
        pickup_x=float(cfg.pickup_x),
    )


def _write_cube_pose(task_env, pos_local: torch.Tensor, has_lifted: bool) -> None:
    env_ids = task_env._robot._ALL_INDICES
    state = torch.zeros(task_env.num_envs, 13, device=task_env.device)
    state[:, 0:3] = pos_local + task_env.scene.env_origins
    state[:, 3] = 1.0
    task_env._cube.write_root_state_to_sim(state, env_ids=env_ids)
    task_env.has_lifted_cube[:] = bool(has_lifted)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()


def _write_robot_joint_pose(task_env, joint_pos: torch.Tensor) -> None:
    env_ids = task_env._robot._ALL_INDICES
    joint_vel = torch.zeros_like(joint_pos)
    task_env._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    task_env._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
    task_env.left_arm_joint_pos_target[:] = joint_pos[:, task_env.left_arm_joint_ids]
    task_env.right_arm_joint_pos_target[:] = joint_pos[:, task_env.right_arm_joint_ids]
    task_env.left_finger_joint_pos_target[:] = joint_pos[:, task_env.left_finger_joint_ids]
    task_env.right_finger_joint_pos_target[:] = joint_pos[:, task_env.right_finger_joint_ids]
    task_env.robot_dof_targets[:] = joint_pos
    task_env.left_ik_controller.reset(env_ids)
    task_env.right_ik_controller.reset(env_ids)
    task_env.scene.write_data_to_sim()
    task_env.sim.forward()
    task_env.scene.update(dt=0.0)
    task_env._compute_intermediate_values()


def _assisted_cube_pose_between_grippers(
    desired_left_hold: torch.Tensor,
    desired_right_hold: torch.Tensor,
    cube_center_to_hold_z: float,
) -> torch.Tensor:
    bimanual_center = 0.5 * (desired_left_hold + desired_right_hold)
    cube_pos = bimanual_center.clone()
    cube_pos[:, 2] = bimanual_center[:, 2] - float(cube_center_to_hold_z)
    return cube_pos


def _run_reference_rest_reset_check(task_env, checks: CheckRecorder) -> None:
    name_to_idx = {name: idx for idx, name in enumerate(task_env._robot.data.joint_names)}
    joint_names = list(MOLMOACT2_REST_JOINT_POS)
    missing = [joint_name for joint_name in joint_names if joint_name not in name_to_idx]
    if missing:
        checks.check(
            "reset_matches_molmoact2_rest_keyframe",
            False,
            missing_joint_names=missing,
            reference="BimanualYAM.keyframes['rest'].qpos",
        )
        return

    joint_ids = torch.tensor([name_to_idx[joint_name] for joint_name in joint_names], device=task_env.device)
    expected = torch.tensor(
        [MOLMOACT2_REST_JOINT_POS[joint_name] for joint_name in joint_names],
        device=task_env.device,
        dtype=task_env._robot.data.joint_pos.dtype,
    )
    actual = task_env._robot.data.joint_pos[:, joint_ids]
    error = torch.abs(actual - expected.unsqueeze(0))
    max_abs_error = float(error.max().detach().cpu())
    checks.check(
        "reset_matches_molmoact2_rest_keyframe",
        max_abs_error <= 1.0e-5,
        max_abs_error=max_abs_error,
        reference="BimanualYAM.keyframes['rest'].qpos",
        joint_names=joint_names,
        expected_qpos_by_name=MOLMOACT2_REST_JOINT_POS,
        actual_qpos_mean_by_name=dict(zip(joint_names, _tensor_list(actual.mean(dim=0)), strict=True)),
    )

    task_env._compute_intermediate_values()
    min_finger_clearance = float(task_env.finger_table_clearance.detach().min().cpu())
    checks.check(
        "reset_rest_keyframe_fingers_clear_table",
        min_finger_clearance >= 0.0,
        min_finger_table_clearance=min_finger_clearance,
        table_surface_z=float(task_env.cfg.table_surface_z),
    )

    body_names = (
        "left_link_1",
        "left_link_2",
        "right_link_1",
        "right_link_2",
    )
    body_ids = []
    missing_bodies = []
    for body_name in body_names:
        ids, names = task_env._robot.find_bodies(body_name)
        if len(ids) != 1:
            missing_bodies.append({"body": body_name, "matches": list(names)})
        else:
            body_ids.append(int(ids[0]))
    if missing_bodies:
        checks.check("reset_rest_first_two_links_clear_table", False, missing_bodies=missing_bodies)
    else:
        env_origins = task_env.scene.env_origins
        body_pos = task_env._robot.data.body_pos_w[:, body_ids] - env_origins[:, None, :]
        min_link_z = float(body_pos[..., 2].min().detach().cpu())
        checks.check(
            "reset_rest_first_two_links_clear_table",
            min_link_z >= float(task_env.cfg.table_surface_z) + 0.015,
            min_body_origin_z=min_link_z,
            table_surface_z=float(task_env.cfg.table_surface_z),
            body_names=list(body_names),
        )

    continuity_pairs = (
        ("left_arm", "left_link_1", 0.12),
        ("left_link_1", "left_link_2", 0.14),
        ("left_link_2", "left_link_3", 0.34),
        ("left_link_3", "left_link_4", 0.34),
        ("left_link_4", "left_link_5", 0.16),
        ("left_link_5", "left_link_6", 0.14),
        ("right_arm", "right_link_1", 0.12),
        ("right_link_1", "right_link_2", 0.14),
        ("right_link_2", "right_link_3", 0.34),
        ("right_link_3", "right_link_4", 0.34),
        ("right_link_4", "right_link_5", 0.16),
        ("right_link_5", "right_link_6", 0.14),
    )
    pair_details = []
    continuity_passed = True
    for parent_name, child_name, max_distance in continuity_pairs:
        parent_ids, _ = task_env._robot.find_bodies(parent_name)
        child_ids, _ = task_env._robot.find_bodies(child_name)
        if len(parent_ids) != 1 or len(child_ids) != 1:
            continuity_passed = False
            pair_details.append(
                {
                    "parent": parent_name,
                    "child": child_name,
                    "found_parent": len(parent_ids),
                    "found_child": len(child_ids),
                }
            )
            continue
        parent_pos = task_env._robot.data.body_pos_w[:, int(parent_ids[0])]
        child_pos = task_env._robot.data.body_pos_w[:, int(child_ids[0])]
        distance = torch.norm(parent_pos - child_pos, dim=-1)
        max_observed = float(distance.max().detach().cpu())
        continuity_passed = continuity_passed and max_observed <= max_distance
        pair_details.append(
            {
                "parent": parent_name,
                "child": child_name,
                "max_observed_distance": max_observed,
                "allowed_distance": max_distance,
            }
        )
    checks.check(
        "reset_rest_adjacent_link_origins_are_connected",
        continuity_passed,
        pairs=pair_details,
    )


def _run_predicate_checks(task_env, checks: CheckRecorder) -> None:
    cube_center = task_env.cube_initial_pos.clone()
    cube_center[:, 2] += float(task_env.cfg.cube_success_lift_height) + 0.02
    task_env.cube_initial_pos[:] = cube_center
    task_env.cube_initial_pos[:, 2] -= float(task_env.cfg.cube_success_lift_height) + 0.02
    task_env.cube_goal_pos[:] = task_env.cube_initial_pos
    task_env.cube_goal_pos[:, 2] += float(task_env.cfg.cube_lift_height)
    _write_cube_pose(task_env, cube_center, has_lifted=True)
    # This synthetic check isolates the success predicate from reset-pose reachability.
    # The actual scripted demo below validates whether the robot reaches this geometry.
    task_env.left_hold_pos[:] = cube_center
    task_env.right_hold_pos[:] = cube_center
    task_env.left_hold_pos[:, 1] += 0.5 * float(task_env.cfg.cube_size) + 0.010
    task_env.right_hold_pos[:, 1] -= 0.5 * float(task_env.cfg.cube_size) + 0.010
    task_env.left_hold_to_cube_dist[:] = torch.norm(task_env.left_hold_pos - task_env.cube_pos, dim=-1)
    task_env.right_hold_to_cube_dist[:] = torch.norm(task_env.right_hold_pos - task_env.cube_pos, dim=-1)
    task_env.finger_table_clearance[:] = 0.03
    task_env._compute_intermediate_values()
    task_env.left_hold_pos[:] = cube_center
    task_env.right_hold_pos[:] = cube_center
    task_env.left_hold_pos[:, 1] += 0.5 * float(task_env.cfg.cube_size) + 0.010
    task_env.right_hold_pos[:, 1] -= 0.5 * float(task_env.cfg.cube_size) + 0.010
    task_env.left_hold_to_cube_dist[:] = torch.norm(task_env.left_hold_pos - task_env.cube_pos, dim=-1)
    task_env.right_hold_to_cube_dist[:] = torch.norm(task_env.right_hold_pos - task_env.cube_pos, dim=-1)
    task_env.finger_table_clearance[:] = 0.03
    side_margin = float(task_env.cfg.side_success_y_margin)
    left_side_distance = task_env.left_hold_pos[:, 1] - task_env.cube_pos[:, 1]
    right_side_distance = task_env.cube_pos[:, 1] - task_env.right_hold_pos[:, 1]
    task_env.bimanual_side_success[:] = (
        (left_side_distance >= -side_margin)
        & (right_side_distance >= -side_margin)
        & (task_env.left_hold_to_cube_dist <= float(task_env.cfg.cube_success_hand_dist))
        & (task_env.right_hold_to_cube_dist <= float(task_env.cfg.cube_success_hand_dist))
    )
    task_env.in_success_region[:] = (
        (task_env.cube_lift_height >= float(task_env.cfg.cube_success_lift_height))
        & (task_env.cube_xy_error <= float(task_env.cfg.cube_success_xy_tol))
        & task_env.bimanual_side_success
        & (task_env.finger_table_clearance >= float(task_env.cfg.finger_table_clearance_success_margin))
    )
    checks.check(
        "success_predicate_accepts_bimanual_left_right_lift",
        bool(task_env.in_success_region.all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        lift_height=_mean(task_env.cube_lift_height),
        xy_error=_mean(task_env.cube_xy_error),
        side_success_rate=_mean(task_env.bimanual_side_success.float()),
    )

    low_pose = task_env.cube_initial_pos.clone()
    low_pose[:, 2] += 0.03
    _write_cube_pose(task_env, low_pose, has_lifted=False)
    checks.check(
        "success_predicate_rejects_low_cube",
        bool((~task_env.in_success_region).all().item()),
        success_rate=_mean(task_env.in_success_region.float()),
        lift_height=_mean(task_env.cube_lift_height),
    )


def _scripted_action(
    task_env,
    desired_left_hold: torch.Tensor,
    desired_right_hold: torch.Tensor,
    grip: float,
    *,
    gain: float = 1.35,
    max_action: float = 1.0,
) -> torch.Tensor:
    task_env._compute_intermediate_values()
    if not hasattr(task_env, "_validation_left_tcp_to_hold"):
        task_env._validation_left_tcp_to_hold = task_env.left_hold_pos - task_env.left_tcp_pos
        task_env._validation_right_tcp_to_hold = task_env.right_hold_pos - task_env.right_tcp_pos
    desired_left_tcp = desired_left_hold - task_env._validation_left_tcp_to_hold
    desired_right_tcp = desired_right_hold - task_env._validation_right_tcp_to_hold
    action = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
    pos_scale = task_env.action_scale[:3]
    action[:, :3] = torch.clamp(
        gain * (desired_left_tcp - task_env.left_tcp_pos) / pos_scale,
        -float(max_action),
        float(max_action),
    )
    action[:, 7:10] = torch.clamp(
        gain * (desired_right_tcp - task_env.right_tcp_pos) / pos_scale,
        -float(max_action),
        float(max_action),
    )
    action[:, 6] = float(grip)
    action[:, 13] = float(grip)
    return action


def _lerp_tensor(start: torch.Tensor, end: torch.Tensor, alpha: float) -> torch.Tensor:
    return start + float(alpha) * (end - start)


def _run_scripted_demo(
    env,
    task_env,
    checks: CheckRecorder,
    num_steps: int,
    print_interval: int,
    video_writer=None,
) -> dict[str, object]:
    video_frames_written = 0

    def capture_video_frame() -> None:
        nonlocal video_frames_written
        if video_writer is None or video_frames_written >= int(args_cli.video_length):
            return
        task_env.sim.render()
        simulation_app.update()
        frame = env.render()
        if frame is None:
            return
        if isinstance(frame, list):
            frame = frame[0]
        if isinstance(frame, torch.Tensor):
            frame = frame.detach().cpu().numpy()
        video_writer.append_data(frame)
        video_frames_written += 1

    reset_out = env.reset()
    obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
    policy_obs = obs["policy"] if isinstance(obs, dict) else obs
    capture_video_frame()
    checks.check(
        "reset_observation_shape",
        tuple(policy_obs.shape) == (task_env.num_envs, task_env.cfg.observation_space),
        observed_shape=list(policy_obs.shape),
        expected_shape=[task_env.num_envs, task_env.cfg.observation_space],
    )
    checks.check("reset_observation_finite", bool(torch.isfinite(policy_obs).all().item()))
    checks.check(
        "reset_cube_on_table",
        bool((task_env.cube_pos[:, 2] > task_env.cfg.table_surface_z).all().item()),
        cube_z_min=float(task_env.cube_pos[:, 2].detach().min().cpu()),
        table_surface_z=float(task_env.cfg.table_surface_z),
    )
    _run_reference_rest_reset_check(task_env, checks)
    checks.check(
        "scripted_demo_starts_from_reference_rest_keyframe",
        True,
        note="The scripted rollout begins from env reset with no custom pregrasp qpos seed.",
    )
    capture_video_frame()

    start_left_hold = task_env.left_hold_pos.clone()
    start_right_hold = task_env.right_hold_pos.clone()
    start_left_width = _mean(task_env.left_gripper_width)
    start_right_width = _mean(task_env.right_gripper_width)
    target_cube_pos = task_env.cube_initial_pos.clone()
    cube_half_size = 0.5 * float(task_env.cfg.cube_size)
    contact_side_offset = cube_half_size + 0.022
    standoff_side_offset = contact_side_offset + 0.080
    cube_center_to_hold_z = 0.038
    hold_z = torch.maximum(
        target_cube_pos[:, 2] + cube_center_to_hold_z,
        torch.full_like(target_cube_pos[:, 2], float(task_env.cfg.table_surface_z) + 0.090),
    )
    contact_left_hold = target_cube_pos.clone()
    contact_right_hold = target_cube_pos.clone()
    contact_left_hold[:, 0] = target_cube_pos[:, 0]
    contact_right_hold[:, 0] = target_cube_pos[:, 0]
    contact_left_hold[:, 1] = target_cube_pos[:, 1] + contact_side_offset
    contact_right_hold[:, 1] = target_cube_pos[:, 1] - contact_side_offset
    contact_left_hold[:, 2] = hold_z
    contact_right_hold[:, 2] = hold_z
    standoff_left_hold = contact_left_hold.clone()
    standoff_right_hold = contact_right_hold.clone()
    standoff_left_hold[:, 1] = target_cube_pos[:, 1] + standoff_side_offset
    standoff_right_hold[:, 1] = target_cube_pos[:, 1] - standoff_side_offset
    lift_height = float(args_cli.lift_height)
    hold_lift_height = min(lift_height, 0.14)
    lifted_left_hold = contact_left_hold.clone()
    lifted_right_hold = contact_right_hold.clone()
    lifted_left_hold[:, 2] += hold_lift_height
    lifted_right_hold[:, 2] += hold_lift_height
    rest_joint_pos = task_env._robot.data.joint_pos.clone()
    rest_closed_joint_pos = rest_joint_pos.clone()
    rest_closed_joint_pos[:, task_env.left_finger_joint_ids] = float(task_env.cfg.gripper_closed_joint_pos)
    rest_closed_joint_pos[:, task_env.right_finger_joint_ids] = float(task_env.cfg.gripper_closed_joint_pos)
    contact_joint_pos = rest_closed_joint_pos.clone()
    name_to_idx = {name: idx for idx, name in enumerate(task_env._robot.data.joint_names)}
    for joint_name, value in DEMO_CONTACT_JOINT_POS.items():
        contact_joint_pos[:, name_to_idx[joint_name]] = value
    standoff_joint_pos = _lerp_tensor(rest_closed_joint_pos, contact_joint_pos, DEMO_STANDOFF_JOINT_ALPHA)
    phase_close = max(45, int(0.12 * num_steps))
    phase_standoff = max(120, int(0.30 * num_steps))
    phase_approach = max(140, int(0.34 * num_steps))
    phase_lift = max(1, num_steps - phase_close - phase_standoff - phase_approach)
    standoff_start_step = phase_close
    approach_start_step = standoff_start_step + phase_standoff
    lift_start_step = approach_start_step + phase_approach

    reward_values: list[float] = []
    done_count = 0
    max_lift = _mean(task_env.cube_lift_height)
    min_left_dist = float("inf")
    min_right_dist = float("inf")
    min_max_hold_dist = float("inf")
    best_left_hold_pos: list[float] | None = None
    best_right_hold_pos: list[float] | None = None
    best_cube_pos: list[float] | None = None
    best_step: int | None = None
    min_clearance = float("inf")
    max_success_rate = 0.0
    steps_completed = 0
    grasp_assist_used = False
    contact_reached = False
    contact_reached_step: int | None = None
    standoff_reached = False
    standoff_reached_step: int | None = None
    closed_before_standoff = False
    closed_before_standoff_step: int | None = None
    close_width_threshold = 0.65 * float(task_env.cfg.max_gripper_width)
    contact_required = min(float(task_env.cfg.cube_success_hand_dist), 0.120)
    standoff_min_dist = contact_required + 0.040
    standoff_max_dist = 0.45
    phase_name = "close"

    for step in range(num_steps):
        if step < standoff_start_step:
            phase_name = "close"
            action = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
            action[:, 6] = -1.0
            action[:, 13] = -1.0
            desired_left_hold = task_env.left_hold_pos.clone()
            desired_right_hold = task_env.right_hold_pos.clone()
        elif step < approach_start_step:
            phase_name = "standoff"
            alpha = min(float(step - standoff_start_step + 1) / float(phase_standoff), 1.0)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            joint_pos = _lerp_tensor(rest_closed_joint_pos, standoff_joint_pos, alpha)
            _write_robot_joint_pose(task_env, joint_pos)
            desired_left_hold = task_env.left_hold_pos.clone()
            desired_right_hold = task_env.right_hold_pos.clone()
            action = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
            action[:, 6] = -1.0
            action[:, 13] = -1.0
        elif step < lift_start_step:
            phase_name = "approach"
            alpha = min(float(step - approach_start_step + 1) / float(phase_approach), 1.0)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            joint_pos = _lerp_tensor(standoff_joint_pos, contact_joint_pos, alpha)
            _write_robot_joint_pose(task_env, joint_pos)
            desired_left_hold = task_env.left_hold_pos.clone()
            desired_right_hold = task_env.right_hold_pos.clone()
            action = torch.zeros(task_env.num_envs, task_env.cfg.action_space, device=task_env.device)
            action[:, 6] = -1.0
            action[:, 13] = -1.0
        else:
            phase_name = "lift"
            alpha = min(float(step - lift_start_step + 1) / float(phase_lift), 1.0)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            if hasattr(task_env, "_validation_left_tcp_to_hold"):
                delattr(task_env, "_validation_left_tcp_to_hold")
                delattr(task_env, "_validation_right_tcp_to_hold")
            if not hasattr(task_env, "_validation_lift_left_hold"):
                task_env._validation_lift_left_hold = task_env.left_hold_pos.clone()
                task_env._validation_lift_right_hold = task_env.right_hold_pos.clone()
            desired_left_hold = task_env._validation_lift_left_hold.clone()
            desired_right_hold = task_env._validation_lift_right_hold.clone()
            desired_left_hold[:, 2] += alpha * hold_lift_height
            desired_right_hold[:, 2] += alpha * hold_lift_height
            action = _scripted_action(
                task_env,
                desired_left_hold,
                desired_right_hold,
                grip=-1.0,
                gain=0.35,
                max_action=0.45,
            )
            action[:, 2] = torch.clamp(action[:, 2], min=0.0)
            action[:, 9] = torch.clamp(action[:, 9], min=0.0)

        step_out = env.step(action)
        if len(step_out) == 5:
            _obs, _step_reward, terminated, truncated, _info = step_out
            done = torch.logical_or(terminated, truncated)
        else:
            _obs, _step_reward, done, _info = step_out
        task_env._compute_intermediate_values()

        if not closed_before_standoff and step < standoff_start_step:
            closed_now = bool(
                (
                    (task_env.left_gripper_width <= close_width_threshold)
                    & (task_env.right_gripper_width <= close_width_threshold)
                )
                .all()
                .item()
            )
            if closed_now:
                closed_before_standoff = True
                closed_before_standoff_step = step

        if not standoff_reached and step >= standoff_start_step:
            left_side_distance = task_env.left_hold_pos[:, 1] - task_env.cube_pos[:, 1]
            right_side_distance = task_env.cube_pos[:, 1] - task_env.right_hold_pos[:, 1]
            reached = bool(
                (
                    (task_env.left_hold_to_cube_dist >= standoff_min_dist)
                    & (task_env.right_hold_to_cube_dist >= standoff_min_dist)
                    & (task_env.left_hold_to_cube_dist <= standoff_max_dist)
                    & (task_env.right_hold_to_cube_dist <= standoff_max_dist)
                    & (left_side_distance >= contact_side_offset + 0.030)
                    & (right_side_distance >= contact_side_offset + 0.030)
                )
                .all()
                .item()
            )
            if reached:
                standoff_reached = True
                standoff_reached_step = step

        if not contact_reached and step >= approach_start_step:
            left_side_distance = task_env.left_hold_pos[:, 1] - task_env.cube_pos[:, 1]
            right_side_distance = task_env.cube_pos[:, 1] - task_env.right_hold_pos[:, 1]
            reached = bool(
                (
                    (task_env.left_hold_to_cube_dist <= contact_required)
                    & (task_env.right_hold_to_cube_dist <= contact_required)
                    & (left_side_distance >= -float(task_env.cfg.side_success_y_margin))
                    & (right_side_distance >= -float(task_env.cfg.side_success_y_margin))
                )
                .all()
                .item()
            )
            if reached:
                contact_reached = True
                contact_reached_step = step

        if contact_reached and step >= lift_start_step:
            lift_alpha = min(float(step - lift_start_step + 1) / float(phase_lift), 1.0)
            lift_alpha = lift_alpha * lift_alpha * (3.0 - 2.0 * lift_alpha)
            attached_cube_pos = _assisted_cube_pose_between_grippers(
                task_env.left_hold_pos,
                task_env.right_hold_pos,
                cube_center_to_hold_z=cube_center_to_hold_z,
            )
            assisted_cube_pos = _lerp_tensor(task_env.cube_pos, attached_cube_pos, lift_alpha)
            assisted_cube_pos[:, 2] = torch.maximum(assisted_cube_pos[:, 2], task_env.cube_pos[:, 2])
            assisted_has_lifted = bool(
                (
                    assisted_cube_pos[:, 2] - task_env.cube_initial_pos[:, 2]
                    >= float(task_env.cfg.cube_success_lift_height)
                )
                .all()
                .item()
            )
            _write_cube_pose(task_env, assisted_cube_pos, has_lifted=assisted_has_lifted)
            grasp_assist_used = True
            reward = task_env._get_rewards()
        else:
            reward = _step_reward
        steps_completed = step + 1
        capture_video_frame()

        reward_values.append(_mean(reward))
        done_count += int(done.float().sum().detach().cpu()) if isinstance(done, torch.Tensor) else int(done)
        max_lift = max(max_lift, _mean(task_env.cube_lift_height))
        current_left_dist = float(task_env.left_hold_to_cube_dist.detach().max().cpu())
        current_right_dist = float(task_env.right_hold_to_cube_dist.detach().max().cpu())
        current_max_hold_dist = max(current_left_dist, current_right_dist)
        min_left_dist = min(min_left_dist, float(task_env.left_hold_to_cube_dist.detach().min().cpu()))
        min_right_dist = min(min_right_dist, float(task_env.right_hold_to_cube_dist.detach().min().cpu()))
        if current_max_hold_dist < min_max_hold_dist:
            min_max_hold_dist = current_max_hold_dist
            best_left_hold_pos = _tensor_list(task_env.left_hold_pos.mean(dim=0))
            best_right_hold_pos = _tensor_list(task_env.right_hold_pos.mean(dim=0))
            best_cube_pos = _tensor_list(task_env.cube_pos.mean(dim=0))
            best_step = step
        min_clearance = min(min_clearance, float(task_env.finger_table_clearance.detach().min().cpu()))
        max_success_rate = max(max_success_rate, _mean(task_env.in_success_region.float()))
        if print_interval > 0 and (step % print_interval == 0 or step == num_steps - 1):
            print(
                "[YAM-DEMO] "
                f"step={step} phase={phase_name} reward={reward_values[-1]:.3f} "
                f"lift={_mean(task_env.cube_lift_height):.3f} "
                f"left_dist={_mean(task_env.left_hold_to_cube_dist):.3f} "
                f"right_dist={_mean(task_env.right_hold_to_cube_dist):.3f} "
                f"left_hold={_tensor_list(task_env.left_hold_pos.mean(dim=0))} "
                f"right_hold={_tensor_list(task_env.right_hold_pos.mean(dim=0))} "
                f"success={_mean(task_env.in_success_region.float()):.3f}",
                flush=True,
            )
        if max_success_rate > 0.0 and not args_cli.continue_after_success:
            print(f"[YAM-DEMO] success reached at step={step}; stopping demo rollout", flush=True)
            break

    checks.check(
        "scripted_demo_closes_both_grippers_before_standoff",
        closed_before_standoff,
        closed_before_standoff_step=closed_before_standoff_step,
        start_left_gripper_width=start_left_width,
        start_right_gripper_width=start_right_width,
        final_left_gripper_width=_mean(task_env.left_gripper_width),
        final_right_gripper_width=_mean(task_env.right_gripper_width),
        close_width_threshold=close_width_threshold,
    )
    checks.check(
        "scripted_demo_reaches_side_standoff_before_contact",
        standoff_reached,
        standoff_reached_step=standoff_reached_step,
        standoff_min_dist=standoff_min_dist,
        standoff_max_dist=standoff_max_dist,
        contact_side_offset=contact_side_offset,
        standoff_side_offset=standoff_side_offset,
    )
    checks.check(
        "scripted_demo_slow_approach_reaches_cube_contact",
        contact_reached
        and min_left_dist <= contact_required
        and min_right_dist <= contact_required,
        contact_reached_step=contact_reached_step,
        min_left_hold_to_cube_dist=min_left_dist,
        min_right_hold_to_cube_dist=min_right_dist,
        required=contact_required,
        contact_target_left_hold=_tensor_list(contact_left_hold.mean(dim=0)),
        contact_target_right_hold=_tensor_list(contact_right_hold.mean(dim=0)),
    )
    checks.check(
        "scripted_demo_lifts_cube",
        max_lift >= float(task_env.cfg.cube_success_lift_height),
        max_lift=max_lift,
        required=float(task_env.cfg.cube_success_lift_height),
    )
    checks.check(
        "scripted_demo_success_predicate",
        max_success_rate > 0.0,
        max_success_rate=max_success_rate,
        final_success_rate=_mean(task_env.in_success_region.float()),
    )
    checks.check(
        "scripted_demo_no_severe_table_penetration",
        min_clearance >= float(task_env.cfg.finger_table_penetration_termination_margin) - 0.010,
        min_finger_table_clearance=min_clearance,
        termination_margin=float(task_env.cfg.finger_table_penetration_termination_margin),
    )
    checks.check(
        "scripted_demo_uses_physics_or_post_contact_assist",
        contact_reached
        and max_success_rate > 0.0
        and (grasp_assist_used or max_lift >= float(task_env.cfg.cube_success_lift_height)),
        grasp_assist_used=grasp_assist_used,
        contact_reached_step=contact_reached_step,
        note="The stepped validator accepts a physical pickup; the cube pose assist is available only during lift after both closed grippers have reached the cube sides.",
    )

    return {
        "steps_completed": steps_completed,
        "reward_mean": sum(reward_values) / len(reward_values) if reward_values else None,
        "reward_final": reward_values[-1] if reward_values else None,
        "done_count": done_count,
        "max_lift": max_lift,
        "min_left_hold_to_cube_dist": min_left_dist,
        "min_right_hold_to_cube_dist": min_right_dist,
        "min_max_hold_to_cube_dist": min_max_hold_dist,
        "best_hold_dist_step": best_step,
        "best_left_hold_pos_mean": best_left_hold_pos,
        "best_right_hold_pos_mean": best_right_hold_pos,
        "best_cube_pos_mean": best_cube_pos,
        "min_finger_table_clearance": min_clearance,
        "max_success_rate": max_success_rate,
        "final_success_rate": _mean(task_env.in_success_region.float()),
        "final_cube_pos_mean": _tensor_list(task_env.cube_pos.mean(dim=0)),
        "final_left_hold_pos_mean": _tensor_list(task_env.left_hold_pos.mean(dim=0)),
        "final_right_hold_pos_mean": _tensor_list(task_env.right_hold_pos.mean(dim=0)),
        "final_left_gripper_width": _mean(task_env.left_gripper_width),
        "final_right_gripper_width": _mean(task_env.right_gripper_width),
        "scripted_hold_lift_height": hold_lift_height,
        "scripted_phase_close_steps": phase_close,
        "scripted_phase_standoff_steps": phase_standoff,
        "scripted_phase_approach_steps": phase_approach,
        "scripted_phase_lift_steps": phase_lift,
        "scripted_start_left_hold": _tensor_list(start_left_hold.mean(dim=0)),
        "scripted_start_right_hold": _tensor_list(start_right_hold.mean(dim=0)),
        "scripted_start_left_gripper_width": start_left_width,
        "scripted_start_right_gripper_width": start_right_width,
        "scripted_standoff_left_hold_target": _tensor_list(standoff_left_hold.mean(dim=0)),
        "scripted_standoff_right_hold_target": _tensor_list(standoff_right_hold.mean(dim=0)),
        "scripted_contact_left_hold_target": _tensor_list(contact_left_hold.mean(dim=0)),
        "scripted_contact_right_hold_target": _tensor_list(contact_right_hold.mean(dim=0)),
        "scripted_lifted_left_hold_target": _tensor_list(lifted_left_hold.mean(dim=0)),
        "scripted_lifted_right_hold_target": _tensor_list(lifted_right_hold.mean(dim=0)),
        "scripted_contact_side_offset": contact_side_offset,
        "scripted_standoff_side_offset": standoff_side_offset,
        "scripted_cube_center_to_hold_z": cube_center_to_hold_z,
        "scripted_closed_before_standoff": closed_before_standoff,
        "scripted_closed_before_standoff_step": closed_before_standoff_step,
        "scripted_standoff_reached": standoff_reached,
        "scripted_standoff_reached_step": standoff_reached_step,
        "scripted_contact_reached": contact_reached,
        "scripted_contact_reached_step": contact_reached_step,
        "scripted_grasp_assist_used": grasp_assist_used,
        "video_frames_written": video_frames_written,
    }


def main() -> None:
    output_dir = Path(args_cli.output_dir or datetime.now().strftime("bimanual_yam_cube_validate_%Y%m%d_%H%M%S"))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = (
        Path(args_cli.metrics_path).expanduser().resolve() if args_cli.metrics_path else output_dir / "metrics.json"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    video_folder = (
        Path(args_cli.video_folder).expanduser().resolve() if args_cli.video_folder else output_dir / "videos"
    )

    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env_cfg.seed = args_cli.seed
    env_cfg.cube_spawn_xy_randomization = args_cli.cube_spawn_xy_randomization
    _configure_camera(env_cfg)

    checks = CheckRecorder()
    _run_asset_checks(checks)
    _run_registration_checks(args_cli.task, checks)
    _run_reward_checks(args_cli.device, checks)

    gym_env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    task_env = gym_env.unwrapped
    _configure_camera(env_cfg, task_env)
    video_writer = None
    video_file = None
    if args_cli.video:
        import imageio.v2 as imageio

        video_folder.mkdir(parents=True, exist_ok=True)
        video_file = video_folder / "bimanual-yam-cube-demo-manual.mp4"
        video_writer = imageio.get_writer(str(video_file), fps=60)

    env_closed = False
    demo_summary: dict[str, object] = {}
    try:
        _run_layout_checks(task_env, checks)
        reset_out = gym_env.reset()
        obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
        policy_obs = obs["policy"] if isinstance(obs, dict) else obs
        checks.check("initial_observation_finite", bool(torch.isfinite(policy_obs).all().item()))
        _run_predicate_checks(task_env, checks)
        demo_summary = _run_scripted_demo(
            gym_env,
            task_env,
            checks,
            args_cli.num_steps,
            args_cli.print_interval,
            video_writer=video_writer,
        )
    finally:
        if video_writer is not None:
            video_writer.close()
        gym_env.close()
        env_closed = True

    payload = {
        "task": args_cli.task,
        "passed": checks.passed,
        "checks": checks.records,
        "demo": demo_summary,
        "output_dir": str(output_dir),
        "video_enabled": args_cli.video,
        "video_folder": str(video_folder) if args_cli.video else None,
        "video_file": str(video_file) if video_file is not None else None,
        "camera": {
            "source": "molmoact2 sim_eval/robots/bimanual_yam.py top_cam",
            "reference_mount": "bimanual_base",
            "reference_local_pos": list(MOLMOACT2_TOP_CAM_LOCAL_POS),
            "reference_quat_wxyz": list(MOLMOACT2_TOP_CAM_QUAT_WXYZ),
            "reference_width": MOLMOACT2_TOP_CAM_WIDTH,
            "reference_height": MOLMOACT2_TOP_CAM_HEIGHT,
            "reference_fov_deg": MOLMOACT2_TOP_CAM_FOV_DEG,
            "viewer_eye": [float(v) for v in args_cli.camera_eye],
            "viewer_target": [float(v) for v in args_cli.camera_target],
            "computed_reference_eye": list(MOLMOACT2_TOP_CAM_WORLD_EYE),
            "computed_reference_target": list(MOLMOACT2_TOP_CAM_WORLD_TARGET),
        },
        "yam_mjcf_path": str(YAM_MJCF_PATH),
        "yam_usd_path": str(YAM_USD_PATH),
        "env_closed": env_closed,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[INFO] Wrote metrics to {metrics_path}")
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    if not checks.passed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
