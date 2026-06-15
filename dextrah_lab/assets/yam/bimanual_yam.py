"""Bimanual YAM robot asset configuration."""

from __future__ import annotations

from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg


YAM_ASSET_DIR = Path(__file__).resolve().parent
BIMANUAL_YAM_MJCF_PATH = YAM_ASSET_DIR / "yam_mujoco" / "bimanual_yam_linear_flattened.xml"
BIMANUAL_YAM_URDF_PATH = YAM_ASSET_DIR / "yam_urdf" / "bimanual_yam.urdf"
BIMANUAL_YAM_USD_PATH = YAM_ASSET_DIR / "yam_usd" / "bimanual_yam.usd"

MOLMOACT2_REST_JOINT_POS = {
    # Matches MolmoAct2 BimanualYAM.keyframes["rest"].qpos by joint name.
    "left_joint1": 0.0,
    "left_joint2": 0.7853981633974483,
    "left_joint3": 1.5707963267948966,
    "left_joint4": 0.0,
    "left_joint5": 0.0,
    "left_joint6": 0.0,
    "left_left_finger": -0.02,
    "left_right_finger": -0.02,
    "right_joint1": 0.0,
    "right_joint2": 0.7853981633974483,
    "right_joint3": 1.5707963267948966,
    "right_joint4": 0.0,
    "right_joint5": 0.0,
    "right_joint6": 0.0,
    "right_left_finger": -0.02,
    "right_right_finger": -0.02,
}

BIMANUAL_YAM_CFG = ArticulationCfg(
    prim_path="{ENV_REGEX_NS}/Robot",
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(BIMANUAL_YAM_USD_PATH),
        activate_contact_sensors=False,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=True,
            retain_accelerations=True,
            linear_damping=0.0,
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=1000.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=12,
            solver_velocity_iteration_count=4,
            sleep_threshold=0.005,
            stabilization_threshold=0.0005,
            fix_root_link=True,
        ),
        joint_drive_props=sim_utils.JointDrivePropertiesCfg(drive_type="force"),
        copy_from_source=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.0),
        rot=(1.0, 0.0, 0.0, 0.0),
        joint_pos=MOLMOACT2_REST_JOINT_POS,
        joint_vel={".*": 0.0},
    ),
    actuators={
        "left_arm": ImplicitActuatorCfg(
            joint_names_expr=["left_joint[1-6]"],
            effort_limit_sim={
                "left_joint[1-3]": 28.0,
                "left_joint[4-6]": 10.0,
            },
            stiffness={
                "left_joint[1-3]": 40.0,
                "left_joint4": 20.0,
                "left_joint[5-6]": 10.0,
            },
            damping={
                "left_joint[1-3]": 2.5,
                "left_joint4": 0.5,
                "left_joint[5-6]": 1.0,
            },
        ),
        "right_arm": ImplicitActuatorCfg(
            joint_names_expr=["right_joint[1-6]"],
            effort_limit_sim={
                "right_joint[1-3]": 28.0,
                "right_joint[4-6]": 10.0,
            },
            stiffness={
                "right_joint[1-3]": 40.0,
                "right_joint4": 20.0,
                "right_joint[5-6]": 10.0,
            },
            damping={
                "right_joint[1-3]": 2.5,
                "right_joint4": 0.5,
                "right_joint[5-6]": 1.0,
            },
        ),
        "left_gripper": ImplicitActuatorCfg(
            joint_names_expr=["left_(left|right)_finger"],
            effort_limit_sim=40.0,
            stiffness=2000.0,
            damping=40.0,
        ),
        "right_gripper": ImplicitActuatorCfg(
            joint_names_expr=["right_(left|right)_finger"],
            effort_limit_sim=40.0,
            stiffness=2000.0,
            damping=40.0,
        ),
    },
    soft_joint_pos_limit_factor=1.0,
)
"""Configuration of the bimanual YAM robot."""
