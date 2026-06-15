"""Gym registration for the bimanual YAM cube-grasp task."""

from __future__ import annotations

import gymnasium as gym

from . import agents
from .bimanual_yam_cube_grasp_env import DextrahBimanualYAMCubeGraspEnv
from .bimanual_yam_cube_grasp_env_cfg import DextrahBimanualYAMCubeGraspEnvCfg


gym.register(
    id="Dextrah-Bimanual-YAM-Cube-Grasp",
    entry_point=(
        "dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.bimanual_yam_cube_grasp_env:"
        "DextrahBimanualYAMCubeGraspEnv"
    ),
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahBimanualYAMCubeGraspEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_bimanual_yam_cube_grasp_cfg.yaml",
    },
)
