"""Gym registration for the Franka multi-object GraspGen task."""

from __future__ import annotations

import gymnasium as gym

from . import agents
from .franka_multi_object_grasp_env import DextrahFrankaMultiObjectGraspEnv
from .franka_multi_object_grasp_env_cfg import DextrahFrankaMultiObjectGraspEnvCfg


gym.register(
    id="Dextrah-Franka-Multi-Object-Grasp",
    entry_point=(
        "dextrah_lab.tasks.dextrah_franka_multi_object_grasp.franka_multi_object_grasp_env:"
        "DextrahFrankaMultiObjectGraspEnv"
    ),
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahFrankaMultiObjectGraspEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_franka_multi_object_grasp_cfg.yaml",
    },
)

