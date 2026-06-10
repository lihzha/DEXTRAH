"""Gym registration for the Franka star-kitting task."""

from __future__ import annotations

import gymnasium as gym

from . import agents
from .franka_star_kitting_env import DextrahFrankaStarKittingEnv
from .franka_star_kitting_env_cfg import DextrahFrankaStarKittingEnvCfg


gym.register(
    id="Dextrah-Franka-Star-Kitting",
    entry_point="dextrah_lab.tasks.dextrah_franka_star_kitting.franka_star_kitting_env:DextrahFrankaStarKittingEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahFrankaStarKittingEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_franka_star_kitting_cfg.yaml",
    },
)

