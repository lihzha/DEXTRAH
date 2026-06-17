"""Gym registration for the single YAM multi-object GraspGen task."""

from __future__ import annotations

import gymnasium as gym

from . import agents
from .single_yam_multi_object_grasp_env import DextrahSingleYAMMultiObjectGraspEnv
from .single_yam_multi_object_grasp_env_cfg import (
    DextrahSingleYAMMultiObjectGraspEnvCfg,
    DextrahSingleYAMTabletopClutterGraspEnvCfg,
)


gym.register(
    id="Dextrah-Single-YAM-Multi-Object-Grasp",
    entry_point=(
        "dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.single_yam_multi_object_grasp_env:"
        "DextrahSingleYAMMultiObjectGraspEnv"
    ),
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahSingleYAMMultiObjectGraspEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_single_yam_multi_object_grasp_cfg.yaml",
    },
)


gym.register(
    id="Dextrah-Single-YAM-Tabletop-Clutter-Grasp",
    entry_point=(
        "dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.single_yam_multi_object_grasp_env:"
        "DextrahSingleYAMMultiObjectGraspEnv"
    ),
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": DextrahSingleYAMTabletopClutterGraspEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_ppo_single_yam_multi_object_grasp_cfg.yaml",
    },
)
