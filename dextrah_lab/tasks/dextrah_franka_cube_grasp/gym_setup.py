"""Gym registration for the Franka cube-grasp task."""

from __future__ import annotations

import gymnasium as gym

from . import agents
from .franka_cube_grasp_env import DextrahFrankaCubeGraspEnv
from .franka_cube_grasp_env_cfg import DextrahFrankaCubeGraspEnvCfg
from .franka_cube_traj_tracking_env import DextrahFrankaCubeTrajTrackingEnv
from .franka_cube_traj_tracking_env_cfg import DextrahFrankaCubeTrajTrackingEnvCfg


gym.register(
    id="Dextrah-Franka-Cube-Grasp",
    entry_point="dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env:DextrahFrankaCubeGraspEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahFrankaCubeGraspEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_franka_cube_grasp_cfg.yaml",
    },
)


gym.register(
    id="Dextrah-Franka-Cube-Grasp-Traj-Tracking",
    entry_point=(
        "dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_traj_tracking_env:"
        "DextrahFrankaCubeTrajTrackingEnv"
    ),
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahFrankaCubeTrajTrackingEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_franka_cube_traj_tracking_cfg.yaml",
    },
)
