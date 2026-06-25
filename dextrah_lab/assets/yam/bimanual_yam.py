"""Bimanual YAM robot asset configuration."""

from __future__ import annotations

import math
from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg


YAM_ASSET_DIR = Path(__file__).resolve().parent
BIMANUAL_YAM_MJCF_PATH = YAM_ASSET_DIR / "yam_mujoco" / "bimanual_yam_linear_flattened.xml"
BIMANUAL_YAM_URDF_PATH = YAM_ASSET_DIR / "yam_urdf" / "bimanual_yam.urdf"
BIMANUAL_YAM_USD_PATH = YAM_ASSET_DIR / "yam_mjcf_usd" / "bimanual_yam_linear_flattened.usd"
SINGLE_YAM_MJCF_PATH = YAM_ASSET_DIR / "yam_mujoco" / "yam_linear.xml"
SINGLE_YAM_URDF_PATH = YAM_ASSET_DIR / "yam_urdf" / "yam.urdf"
SINGLE_YAM_USD_PATH = YAM_ASSET_DIR / "yam_mjcf_usd" / "yam_linear.usd"

MOLMOACT2_CAMERA_WIDTH = 640
MOLMOACT2_CAMERA_HEIGHT = 360
MOLMOACT2_TOP_CAMERA_HFOV_DEG = 69.4
MOLMOACT2_WRIST_CAMERA_HFOV_DEG = 87.0
MOLMOACT2_TOP_CAMERA_UID = "top_cam"
MOLMOACT2_LEFT_CAMERA_UID = "left_cam"
MOLMOACT2_RIGHT_CAMERA_UID = "right_cam"
MOLMOACT2_CAMERA_ORDER = (
    MOLMOACT2_TOP_CAMERA_UID,
    MOLMOACT2_LEFT_CAMERA_UID,
    MOLMOACT2_RIGHT_CAMERA_UID,
)
MOLMOACT2_NORM_TAG = "yam_dual_molmoact2"

MOLMOACT2_TOP_CAMERA_PARENT_BODY = "bimanual_base"
MOLMOACT2_TOP_CAMERA_LOCAL_POS = (0.15, 0.0, 0.8)
MOLMOACT2_TOP_CAMERA_LOCAL_QUAT_WXYZ = (0.7660444431189782, 0.0, 0.6427876096865391, 0.0)
MOLMOACT2_LEFT_WRIST_CAMERA_PARENT_BODY = "left_link_6"
MOLMOACT2_RIGHT_WRIST_CAMERA_PARENT_BODY = "right_link_6"
MOLMOACT2_WRIST_CAMERA_LOCAL_POS = (0.0, 0.09, 0.06)
MOLMOACT2_WRIST_CAMERA_LOCAL_QUAT_WXYZ = (
    0.612372429196013,
    -0.35355339154618404,
    -0.3535533966987049,
    -0.612372438120441,
)
MOLMOACT2_CAMERA_BODY_MASS = 0.001
MOLMOACT2_CAMERA_BODY_DIAGINERTIA = (1.0e-6, 1.0e-6, 1.0e-6)

MOLMOACT2_BIMANUAL_ARM_Y_OFFSET = 0.31
MOLMOACT2_ROBOT_ROOT_POS = (-0.65, 0.0, 0.01)
MOLMOACT2_ROBOT_ROOT_QUAT_WXYZ = (1.0, 0.0, 0.0, 0.0)
MOLMOACT2_TABLE_SIZE = (1.209, 2.418, 0.9196429)
MOLMOACT2_TABLE_CENTER = (-0.12, 0.0, -0.5 * MOLMOACT2_TABLE_SIZE[2])
MOLMOACT2_TABLE_SURFACE_Z = 0.0
MOLMOACT2_OBJECT_ANCHORS_XY = ((-0.30, 0.22), (-0.30, -0.22))
MOLMOACT2_BOX_ANCHOR_XY = (-0.15, 0.0)


def _intrinsic_from_hfov(width: int, height: int, hfov_deg: float) -> tuple[float, float, float, float, float, float, float, float, float]:
    focal = (0.5 * float(width)) / math.tan(0.5 * math.radians(float(hfov_deg)))
    return (focal, 0.0, 0.5 * float(width), 0.0, focal, 0.5 * float(height), 0.0, 0.0, 1.0)


def _vfov_from_hfov(width: int, height: int, hfov_deg: float) -> float:
    return math.degrees(
        2.0 * math.atan((float(height) / float(width)) * math.tan(0.5 * math.radians(float(hfov_deg))))
    )


MOLMOACT2_TOP_CAMERA_INTRINSIC = _intrinsic_from_hfov(
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_TOP_CAMERA_HFOV_DEG,
)
MOLMOACT2_WRIST_CAMERA_INTRINSIC = _intrinsic_from_hfov(
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_WRIST_CAMERA_HFOV_DEG,
)
MOLMOACT2_TOP_CAMERA_VFOV_DEG = _vfov_from_hfov(
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_TOP_CAMERA_HFOV_DEG,
)
MOLMOACT2_WRIST_CAMERA_VFOV_DEG = _vfov_from_hfov(
    MOLMOACT2_CAMERA_WIDTH,
    MOLMOACT2_CAMERA_HEIGHT,
    MOLMOACT2_WRIST_CAMERA_HFOV_DEG,
)

MOLMOACT2_REST_JOINT_POS = {
    # Matches the MolmoAct2 ManiSkill BimanualYAM rest keyframe by joint name.
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

MOLMOACT2_HOME_JOINT_POS = {
    # Matches the original bimanual_yam.xml keyframe named "home".
    "left_joint1": 0.0,
    "left_joint2": 1.047,
    "left_joint3": 1.047,
    "left_joint4": 0.1,
    "left_joint5": -0.1,
    "left_joint6": 0.0,
    "left_left_finger": 0.0,
    "left_right_finger": 0.0,
    "right_joint1": 0.0,
    "right_joint2": 1.047,
    "right_joint3": 1.047,
    "right_joint4": 0.1,
    "right_joint5": -0.1,
    "right_joint6": 0.0,
    "right_left_finger": 0.0,
    "right_right_finger": 0.0,
}

MOLMOACT2_SINGLE_REST_JOINT_POS = {
    "joint1": 0.0,
    "joint2": 0.7853981633974483,
    "joint3": 1.5707963267948966,
    "joint4": 0.0,
    "joint5": 0.0,
    "joint6": 0.0,
    "left_finger": -0.02,
    "right_finger": -0.02,
}

MOLMOACT2_SINGLE_HOME_JOINT_POS = {
    # Matches yam_linear.xml keyframe named "home" for the gripper-down reset pose.
    "joint1": 0.0,
    "joint2": 1.047,
    "joint3": 1.047,
    "joint4": 0.0,
    "joint5": 0.0,
    "joint6": 0.0,
    "left_finger": 0.0,
    "right_finger": 0.0,
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
        joint_pos=MOLMOACT2_HOME_JOINT_POS,
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

SINGLE_YAM_CFG = ArticulationCfg(
    prim_path="{ENV_REGEX_NS}/Robot",
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(SINGLE_YAM_USD_PATH),
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
        joint_pos=MOLMOACT2_SINGLE_HOME_JOINT_POS,
        joint_vel={".*": 0.0},
    ),
    actuators={
        "arm": ImplicitActuatorCfg(
            joint_names_expr=["joint[1-6]"],
            effort_limit_sim={
                "joint[1-3]": 56.0,
                "joint[4-6]": 20.0,
            },
            stiffness={
                "joint[1-3]": 80.0,
                "joint4": 40.0,
                "joint[5-6]": 20.0,
            },
            damping={
                "joint[1-3]": 12.5,
                "joint4": 2.5,
                "joint[5-6]": 5.0,
            },
        ),
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=["(left|right)_finger"],
            effort_limit_sim=20.0,
            stiffness=1000.0,
            damping=160.0,
        ),
    },
    soft_joint_pos_limit_factor=1.0,
)
"""Configuration of the bimanual YAM robot."""
