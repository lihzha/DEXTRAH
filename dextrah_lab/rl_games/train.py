# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script to train RL agent with RL-Games."""

"""Launch Isaac Sim Simulator first."""

import argparse
import sys

from isaaclab.app import AppLauncher

# add argparse arguments
parser = argparse.ArgumentParser(description="Train an RL agent with RL-Games.")
parser.add_argument("--video", action="store_true", default=False, help="Record videos during training.")
parser.add_argument("--video_length", type=int, default=200, help="Length of the recorded video (in steps).")
parser.add_argument("--video_interval", type=int, default=2000, help="Interval between video recordings (in steps).")
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
parser.add_argument("--num_envs", type=int, default=None, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")
parser.add_argument(
    "--distributed", action="store_true", default=False, help="Run training with multiple GPUs or nodes."
)
parser.add_argument("--checkpoint", type=str, default=None, help="Path to model checkpoint.")
parser.add_argument("--sigma", type=str, default=None, help="The policy's initial standard deviation.")
parser.add_argument("--max_iterations", type=int, default=None, help="RL Policy training iterations.")
parser.add_argument("--auto_resume", action="store_true", default=False, help="Resume from the newest checkpoint.")
parser.add_argument("--no_auto_resume", action="store_true", default=False, help="Disable Slurm auto-resume.")

# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli, hydra_args = parser.parse_known_args()
# always enable cameras to record video
if args_cli.video:
    args_cli.enable_cameras = True
if args_cli.task and "RGB" in args_cli.task:
    args_cli.enable_cameras = True

# clear out sys.argv for Hydra
sys.argv = [sys.argv[0]] + hydra_args

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import glob
import math
import os
import re
from datetime import datetime

from rl_games.common import env_configurations, vecenv
from rl_games.common.algo_observer import IsaacAlgoObserver
from rl_games.algos_torch import model_builder
from rl_games.torch_runner import Runner

from a2c_rgb_resnet import A2CRgbResnetBuilder

from isaaclab.utils.dict import print_dict
from isaaclab.utils.io import dump_pickle, dump_yaml

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import load_cfg_from_registry, parse_env_cfg
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper

#import dextrah_lab.tasks.shadow_hand.gym_setup
import dextrah_lab.tasks.dextrah_kuka_allegro.gym_setup
import dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup
import dextrah_lab.tasks.dextrah_single_yam_multi_object_grasp.gym_setup
import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup
import dextrah_lab.tasks.dextrah_franka_multi_object_grasp.gym_setup
import dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup

import time
from rl_games_utils import DirectInfoJsonlObserver, DextrahResumableAlgoObserver, MultiObserver, RLGPUAlgoObserver

from isaaclab.envs import (
    DirectMARLEnv,
    DirectMARLEnvCfg,
    DirectRLEnvCfg,
    ManagerBasedRLEnvCfg,
    multi_agent_to_single_agent,
)
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.dict import print_dict
from isaaclab.utils.io import dump_pickle, dump_yaml

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config


class DextrahRlGamesVecEnvWrapper(RlGamesVecEnvWrapper):
    def get_env_state(self):
        if hasattr(self.unwrapped, "get_env_state"):
            return self.unwrapped.get_env_state()
        return None

    def set_env_state(self, env_state):
        if hasattr(self.unwrapped, "set_env_state"):
            self.unwrapped.set_env_state(env_state)

    def get_current_obs(self):
        if hasattr(self.unwrapped, "get_current_observations"):
            obs_dict = self.unwrapped.get_current_observations()
        else:
            obs_dict = self.unwrapped._get_observations()
        return self._process_obs(obs_dict)


class DextrahRlGamesGpuEnv(RlGamesGpuEnv):
    def set_train_info(self, env_frames, *args_, **kwargs_):
        if hasattr(self.env, "set_train_info"):
            self.env.set_train_info(env_frames, *args_, **kwargs_)

    def get_env_state(self):
        if hasattr(self.env, "get_env_state"):
            return self.env.get_env_state()
        return None

    def set_env_state(self, env_state):
        if hasattr(self.env, "set_env_state"):
            self.env.set_env_state(env_state)

    def get_current_obs(self):
        if hasattr(self.env, "get_current_obs"):
            return self.env.get_current_obs()
        raise AttributeError("Wrapped environment does not expose get_current_obs")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _auto_resume_enabled() -> bool:
    if args_cli.no_auto_resume:
        return False
    if args_cli.auto_resume:
        return True
    if os.environ.get("DEXTRAH_AUTO_RESUME") is not None:
        return _bool_env("DEXTRAH_AUTO_RESUME")
    return os.environ.get("SLURM_JOB_ID") is not None


def _checkpoint_sort_key(path: str):
    match = re.search(r"_ep_(-?\d+)", os.path.basename(path))
    epoch = int(match.group(1)) if match else -1
    return epoch, os.path.getmtime(path)


def _find_latest_checkpoint(log_root_path: str, log_dir: str) -> str | None:
    nn_dir = os.path.join(log_root_path, log_dir, "nn")
    candidates = []
    for path in glob.glob(os.path.join(nn_dir, "*.pth")):
        name = os.path.basename(path)
        if name.startswith("dextrah_runtime_rank_") or ".tmp." in name:
            continue
        candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=_checkpoint_sort_key)[-1]


@hydra_task_config(args_cli.task, "rl_games_cfg_entry_point")
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: dict):
    """Train with RL-Games agent."""
    # override configurations with non-hydra CLI arguments

    # parse seed from command line
    if args_cli.seed == -1:
        args_cli.seed = int(time.time())

    env_cfg.scene.num_envs = args_cli.num_envs if args_cli.num_envs is not None else env_cfg.scene.num_envs
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device

    agent_cfg["params"]["seed"] = args_cli.seed if args_cli.seed is not None else agent_cfg["params"]["seed"]
    agent_cfg["params"]["config"]["max_epochs"] = (
        args_cli.max_iterations if args_cli.max_iterations is not None else agent_cfg["params"]["config"]["max_epochs"]
    )

    resume_path = None
    if args_cli.checkpoint is not None:
        resume_path = retrieve_file_path(args_cli.checkpoint)
    train_sigma = float(args_cli.sigma) if args_cli.sigma is not None else None

    # multi-gpu training config
    if args_cli.distributed:
        agent_cfg["params"]["seed"] += app_launcher.global_rank
        agent_cfg["params"]["config"]["device"] = f"cuda:{app_launcher.local_rank}"
        agent_cfg["params"]["config"]["device_name"] = f"cuda:{app_launcher.local_rank}"
        agent_cfg["params"]["config"]["multi_gpu"] = True
        # update env config device
        env_cfg.sim.device = f"cuda:{app_launcher.local_rank}"

    # set the environment seed (after multi-gpu config for updated rank from agent seed)
    # note: certain randomizations occur in the environment initialization so we set the seed here
    env_cfg.seed = agent_cfg["params"]["seed"]

    # specify directory for logging experiments
    # Cluster jobs set DEXTRAH_LOG_ROOT to avoid mutating a shared code-checkout
    # "logs" symlink while multiple Slurm jobs may be starting or stopping.
    log_root_base = os.environ.get("DEXTRAH_LOG_ROOT")
    if log_root_base:
        log_root_path = os.path.join(log_root_base, "rl_games", agent_cfg["params"]["config"]["name"])
    else:
        log_root_path = os.path.join("logs", "rl_games", agent_cfg["params"]["config"]["name"])
    log_root_path = os.path.abspath(log_root_path)
    print(f"[INFO] Logging experiment in directory: {log_root_path}")
    # specify directory for logging runs
    log_dir = agent_cfg["params"]["config"].get("full_experiment_name")
    if not log_dir:
        log_dir = os.environ.get("DEXTRAH_RUN_NAME")
    if not log_dir and os.environ.get("SLURM_JOB_ID") is not None:
        log_dir = f"slurm_{os.environ['SLURM_JOB_ID']}"
    if not log_dir:
        log_dir = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # set directory into agent config
    # logging directory path: <train_dir>/<full_experiment_name>
    agent_cfg["params"]["config"]["train_dir"] = log_root_path
    agent_cfg["params"]["config"]["full_experiment_name"] = log_dir

    if resume_path is None and _auto_resume_enabled():
        resume_path = _find_latest_checkpoint(log_root_path, log_dir)
        if resume_path is not None:
            print(f"[INFO]: Auto-resuming from latest checkpoint: {resume_path}")

    if resume_path is not None:
        agent_cfg["params"]["load_checkpoint"] = True
        agent_cfg["params"]["load_path"] = resume_path
        print(f"[INFO]: Loading model checkpoint from: {agent_cfg['params']['load_path']}")

    # Dump rank-0 configs only.  In distributed runs each rank has a distinct
    # seed/device; letting every rank write the same files makes the saved
    # config nondeterministically reflect whichever rank wrote last.
    if not args_cli.distributed or int(app_launcher.global_rank) == 0:
        dump_yaml(os.path.join(log_root_path, log_dir, "params", "env.yaml"), env_cfg)
        dump_yaml(os.path.join(log_root_path, log_dir, "params", "agent.yaml"), agent_cfg)
        dump_pickle(os.path.join(log_root_path, log_dir, "params", "env.pkl"), env_cfg)
        dump_pickle(os.path.join(log_root_path, log_dir, "params", "agent.pkl"), agent_cfg)

    # read configurations about the agent-training
    rl_device = agent_cfg["params"]["config"]["device"]
    clip_obs = agent_cfg["params"]["env"].get("clip_observations", math.inf)
    clip_actions = agent_cfg["params"]["env"].get("clip_actions", math.inf)

    # create isaac environment
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None)
    # wrap for video recording
    if args_cli.video:
        video_kwargs = {
            "video_folder": os.path.join(log_root_path, log_dir, "videos", "train"),
            "step_trigger": lambda step: step % args_cli.video_interval == 0,
            "video_length": args_cli.video_length,
            "disable_logger": True,
        }
        print("[INFO] Recording videos during training.")
        print_dict(video_kwargs, nesting=4)
        env = gym.wrappers.RecordVideo(env, **video_kwargs)

    # convert to single-agent instance if required by the RL algorithm
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)

    # wrap around environment for rl-games
    env = DextrahRlGamesVecEnvWrapper(env, rl_device, clip_obs, clip_actions)

    # register the environment to rl-games registry
    # note: in agents configuration: environment name must be "rlgpu"
    vecenv.register(
        "IsaacRlgWrapper", lambda config_name, num_actors, **kwargs: DextrahRlGamesGpuEnv(config_name, num_actors, **kwargs)
    )
    env_configurations.register("rlgpu", {"vecenv_type": "IsaacRlgWrapper", "env_creator": lambda **kwargs: env})

    # set number of actors into agent config
    agent_cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
    # create runner from rl-games

    observers = [IsaacAlgoObserver(), RLGPUAlgoObserver(), DirectInfoJsonlObserver(), DextrahResumableAlgoObserver()]

    if agent_cfg["wandb_activate"]:
        if not args_cli.distributed or int(app_launcher.local_rank) == 0:
            # initialize wandb only once per horovod run (or always for non-horovod runs)
            from wandb_utils import WandbAlgoObserver

            wandb_observer = WandbAlgoObserver(agent_cfg)
            observers.append(wandb_observer)

    runner = Runner(MultiObserver(observers))
    model_builder.register_network("a2c_rgb_resnet", A2CRgbResnetBuilder)
    runner.load(agent_cfg)

    # reset the agent and env
    runner.reset()
    # train the agent
    if resume_path is not None:
        runner.run({"train": True, "play": False, "sigma": train_sigma, "checkpoint": resume_path})
    else:
        runner.run({"train": True, "play": False, "sigma": train_sigma})

    # close the simulator
    env.close()


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()
