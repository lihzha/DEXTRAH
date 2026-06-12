# Copyright (c) 2018-2021, NVIDIA Corporation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from collections import deque
from typing import Callable

import json
import os
import random
import signal
import numpy as np
import torch
from rl_games.common import env_configurations, vecenv
from rl_games.common.algo_observer import AlgoObserver

from checkpoint_init import is_policy_initialization_checkpoint

# from isaacgymenvs.tasks import isaacgym_task_map
# from isaacgymenvs.utils.utils import set_seed, flatten_dict

import time
from collections import OrderedDict


def flatten_dict(d, prefix='', separator='.'):
    res = dict()
    for key, value in d.items():
        if isinstance(value, (dict, OrderedDict)):
            res.update(flatten_dict(value, prefix + key + separator, separator))
        else:
            res[prefix + key] = value

    return res



# def multi_gpu_get_rank(multi_gpu):
#     if multi_gpu:
#         import horovod.torch as hvd
#         rank = hvd.rank()
#         print("Horovod rank: ", rank)
#         return rank

#     return 0


# def get_rlgames_env_creator(
#         # used to create the vec task
#         seed: int,
#         task_config: dict,
#         task_name: str,
#         sim_device: str,
#         rl_device: str,
#         graphics_device_id: int,
#         headless: bool,
#         # Used to handle multi-gpu case
#         multi_gpu: bool = False,
#         post_create_hook: Callable = None,
# ):
#     """Parses the configuration parameters for the environment task and creates a VecTask

#     Args:
#         seed: environment seed
#         task_config: environment configuration.
#         task_name: Name of the task, used to evaluate based on the imported name (eg 'Trifinger')
#         sim_device: The type of env device, eg 'cuda:0'
#         rl_device: Device that RL will be done on, eg 'cuda:0'
#         graphics_device_id: Graphics device ID.
#         headless: Whether to run in headless mode.
#         multi_gpu: Whether to use multi gpu
#         post_create_hook: Hooks to be called after environment creation.
#             [Needed to setup WandB only for one of the RL Games instances when doing multiple GPUs]
#     Returns:
#         A VecTaskPython object.
#     """
#     def create_rlgpu_env(_sim_device=sim_device, _rl_device=rl_device, **_kwargs):
#         """
#         Creates the task from configurations and wraps it using RL-games wrappers if required.
#         """

#         if multi_gpu:
#             import horovod.torch as hvd

#             hvd.init()

#             rank = hvd.rank()
#             set_seed(seed + rank)

#             print("Horovod rank: ", rank)

#             _sim_device = f'cuda:{rank}'
#             _rl_device = f'cuda:{rank}'

#             task_config['rank'] = rank
#             task_config['rl_device'] = 'cuda:' + str(rank)
#         else:
#             _sim_device = sim_device
#             _rl_device = rl_device

#         # create native task and pass custom config
#         env = isaacgym_task_map[task_name](
#             cfg=task_config,
#             sim_device=_sim_device,
#             graphics_device_id=graphics_device_id,
#             headless=headless
#         )

#         if post_create_hook is not None:
#             post_create_hook()

#         return env
#     return create_rlgpu_env


class RLGPUAlgoObserver(AlgoObserver):
    """Allows us to log stats from the env along with the algorithm running stats. """

    def __init__(self):
        super().__init__()
        self.algo = None
        self.writer = None

        self.ep_infos = []
        self.direct_info = {}

        self.episode_cumulative = dict()
        self.episode_cumulative_avg = dict()
        self.new_finished_episodes = False

    def after_init(self, algo):
        self.algo = algo
        self.writer = self.algo.writer

    def process_infos(self, infos, done_indices):
        assert isinstance(infos, dict), 'RLGPUAlgoObserver expects dict info'
        if not isinstance(infos, dict):
            return

        if 'episode' in infos:
            self.ep_infos.append(infos['episode'])

        if 'episode_cumulative' in infos:
            for key, value in infos['episode_cumulative'].items():
                if key not in self.episode_cumulative:
                    self.episode_cumulative[key] = torch.zeros_like(value)
                self.episode_cumulative[key] += value

            for done_idx in done_indices:
                self.new_finished_episodes = True
                done_idx = done_idx.item()

                for key, value in infos['episode_cumulative'].items():
                    if key not in self.episode_cumulative_avg:
                        self.episode_cumulative_avg[key] = deque([], maxlen=self.algo.games_to_track)

                    self.episode_cumulative_avg[key].append(self.episode_cumulative[key][done_idx].item())
                    self.episode_cumulative[key][done_idx] = 0

        # turn nested infos into summary keys (i.e. infos['scalars']['lr'] -> infos['scalars/lr']
        if len(infos) > 0 and isinstance(infos, dict):  # allow direct logging from env
            infos_flat = flatten_dict(infos, prefix='', separator='/')
            self.direct_info = {}
            for k, v in infos_flat.items():
                # only log scalars
                if isinstance(v, float) or isinstance(v, int) or (isinstance(v, torch.Tensor) and len(v.shape) == 0):
                    self.direct_info[k] = v

    def after_print_stats(self, frame, epoch_num, total_time):
        if self.ep_infos:
            for key in self.ep_infos[0]:
                infotensor = torch.tensor([], device=self.algo.device)
                for ep_info in self.ep_infos:
                    # handle scalar and zero dimensional tensor infos
                    if not isinstance(ep_info[key], torch.Tensor):
                        ep_info[key] = torch.Tensor([ep_info[key]])
                    if len(ep_info[key].shape) == 0:
                        ep_info[key] = ep_info[key].unsqueeze(0)
                    infotensor = torch.cat((infotensor, ep_info[key].to(self.algo.device)))
                value = torch.mean(infotensor)
                self.writer.add_scalar('Episode/' + key, value, epoch_num)
            self.ep_infos.clear()
        
        # log these if and only if we have new finished episodes
        if self.new_finished_episodes:
            for key in self.episode_cumulative_avg:
                self.writer.add_scalar(f'episode_cumulative/{key}', np.mean(self.episode_cumulative_avg[key]), frame)
                self.writer.add_scalar(f'episode_cumulative_min/{key}_min', np.min(self.episode_cumulative_avg[key]), frame)
                self.writer.add_scalar(f'episode_cumulative_max/{key}_max', np.max(self.episode_cumulative_avg[key]), frame)
            self.new_finished_episodes = False

        for k, v in self.direct_info.items():
            self.writer.add_scalar(f'{k}/frame', v, frame)
            self.writer.add_scalar(f'{k}/iter', v, epoch_num)
            self.writer.add_scalar(f'{k}/time', v, total_time)


class MultiObserver(AlgoObserver):
    """Meta-observer that allows the user to add several observers."""

    def __init__(self, observers_):
        super().__init__()
        self.observers = observers_

    def _call_multi(self, method, *args_, **kwargs_):
        for o in self.observers:
            getattr(o, method)(*args_, **kwargs_)

    def before_init(self, base_name, config, experiment_name):
        self._call_multi('before_init', base_name, config, experiment_name)

    def after_init(self, algo):
        self._call_multi('after_init', algo)

    def process_infos(self, infos, done_indices):
        self._call_multi('process_infos', infos, done_indices)

    def after_steps(self):
        self._call_multi('after_steps')

    def after_clear_stats(self):
        self._call_multi('after_clear_stats')

    def after_print_stats(self, frame, epoch_num, total_time):
        self._call_multi('after_print_stats', frame, epoch_num, total_time)


class DirectInfoJsonlObserver(AlgoObserver):
    """Writes direct environment scalars to rank-local JSONL sidecars.

    TensorBoard event files are not always reliable in the headless cluster
    runtime, so this observer provides a minimal opt-in artifact for smoke and
    training inspection without changing the RL update path.
    """

    def __init__(self):
        super().__init__()
        self.algo = None
        self._enabled = os.environ.get("DEXTRAH_RLGAMES_JSONL_METRICS", "0").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self._base_name = None
        self._config = {}
        self._experiment_name = None
        self._direct_info = {}
        self._file = None
        self._path = None

    def before_init(self, base_name, config, experiment_name):
        self._base_name = base_name
        self._config = config if isinstance(config, dict) else {}
        self._experiment_name = experiment_name

    def after_init(self, algo):
        self.algo = algo
        if not self._enabled:
            return

        run_dir = self._resolve_run_dir()
        metrics_dir = os.path.join(run_dir, "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        self._path = os.path.join(metrics_dir, f"direct_info_rank_{self._rank()}.jsonl")
        self._file = open(self._path, "a", encoding="utf-8")
        print(f"[DEXTRAH metrics] writing direct info scalars to {self._path}")

    def process_infos(self, infos, done_indices):
        if not self._enabled or not isinstance(infos, dict):
            return

        flat_infos = flatten_dict(infos, prefix="", separator="/")
        self._direct_info = {
            key: scalar
            for key, value in flat_infos.items()
            for scalar in [self._to_scalar(value)]
            if scalar is not None
        }

    def after_print_stats(self, frame, epoch_num, total_time):
        if not self._enabled or self._file is None:
            return

        scalars = dict(self._direct_info)
        scalars.update(self._collect_env_extras())
        if not scalars:
            return

        record = {
            "frame": int(frame),
            "epoch": int(epoch_num),
            "rank": self._rank(),
            "world_size": self._world_size(),
            "time": float(total_time),
            "wall_time": time.time(),
            "scalars": scalars,
        }
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._file.flush()

    def _resolve_run_dir(self):
        train_dir = self._config.get("train_dir")
        experiment_name = self._config.get("full_experiment_name") or self._experiment_name
        if train_dir and experiment_name:
            return os.path.join(str(train_dir), str(experiment_name))

        writer = getattr(self.algo, "writer", None)
        for attr in ("log_dir", "logdir"):
            value = getattr(writer, attr, None)
            if value:
                path = os.path.abspath(str(value))
                return os.path.dirname(path) if os.path.basename(path) == "summaries" else path

        get_logdir = getattr(getattr(writer, "file_writer", None), "get_logdir", None)
        if callable(get_logdir):
            path = os.path.abspath(str(get_logdir()))
            return os.path.dirname(path) if os.path.basename(path) == "summaries" else path

        log_root = os.environ.get("DEXTRAH_LOG_ROOT", "logs")
        run_name = os.environ.get("DEXTRAH_RUN_NAME", experiment_name or "unknown_run")
        base_name = self._base_name or self._config.get("name") or "unknown_task"
        return os.path.abspath(os.path.join(log_root, "rl_games", str(base_name), str(run_name)))

    def _collect_env_extras(self):
        env = self._find_env_with_extras()
        if env is None:
            return {}

        extras = getattr(env, "extras", None)
        if not isinstance(extras, dict):
            return {}

        flat_extras = flatten_dict(extras, prefix="", separator="/")
        return {
            f"env_extras/{key}": scalar
            for key, value in flat_extras.items()
            for scalar in [self._to_scalar(value)]
            if scalar is not None
        }

    def _find_env_with_extras(self):
        candidates = [getattr(self.algo, "vec_env", None)]
        seen = set()
        while candidates:
            candidate = candidates.pop(0)
            if candidate is None:
                continue
            ident = id(candidate)
            if ident in seen:
                continue
            seen.add(ident)
            if isinstance(getattr(candidate, "extras", None), dict):
                return candidate
            for attr in ("env", "unwrapped", "_env", "venv"):
                child = getattr(candidate, attr, None)
                if child is not None:
                    candidates.append(child)
        return None

    def _to_scalar(self, value):
        if isinstance(value, torch.Tensor):
            if value.numel() != 1:
                return None
            return float(value.detach().cpu().item())
        if isinstance(value, np.ndarray):
            if value.size != 1:
                return None
            return float(value.reshape(()).item())
        if isinstance(value, np.generic):
            return float(value.item())
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (float, int)):
            return float(value)
        return None

    def _rank(self):
        if self.algo is not None:
            return int(getattr(self.algo, "global_rank", os.environ.get("RANK", 0)))
        return int(os.environ.get("RANK", 0))

    def _world_size(self):
        if self.algo is not None:
            return int(getattr(self.algo, "world_size", os.environ.get("WORLD_SIZE", 1)))
        return int(os.environ.get("WORLD_SIZE", 1))


class DextrahResumableAlgoObserver(AlgoObserver):
    """Adds DEXTRAH runtime state to RL-Games checkpoints.

    RL-Games restores env_state before train() calls env_reset(), so this observer
    defers env/runtime restore until after the first reset. It also writes
    rank-local runtime sidecars because distributed RL-Games only saves the main
    model checkpoint from rank 0.
    """

    def __init__(self):
        super().__init__()
        self.algo = None
        self.writer = None
        self._save_runtime_buffer = os.environ.get("DEXTRAH_RESUME_SAVE_BUFFER", "1") != "0"
        self._sidecar_interval = os.environ.get("DEXTRAH_RESUME_SIDECAR_INTERVAL")
        self._checkpoint_requested = False
        self._saving = False
        self._signals_installed = False

    def after_init(self, algo):
        self.algo = algo
        self.writer = self.algo.writer
        self._patch_algo()
        self._install_signal_handlers()

    def after_steps(self):
        if self.algo is None:
            return

        epoch_num = int(getattr(self.algo, "epoch_num", 0))
        interval = self._get_sidecar_interval()
        if interval > 0 and epoch_num > 0 and epoch_num % interval == 0:
            self._save_runtime_sidecar(reason="interval")

        if self._checkpoint_requested:
            self._save_interrupt_checkpoint()
            self._checkpoint_requested = False

    def _patch_algo(self):
        algo = self.algo
        if getattr(algo, "_dextrah_resume_patched", False):
            return

        original_get_full_state_weights = algo.get_full_state_weights
        original_set_full_state_weights = algo.set_full_state_weights
        original_env_reset = algo.env_reset
        original_restore = getattr(algo, "restore", None)

        def get_full_state_weights_with_runtime():
            state = original_get_full_state_weights()
            state["dextrah_runtime_state"] = self._pack_runtime_state()
            return state

        def set_full_state_weights_deferred(weights, set_epoch=True):
            is_init_checkpoint = is_policy_initialization_checkpoint(weights)
            if is_init_checkpoint:
                set_epoch = False
                checkpoint_epoch = None
                runtime_state = None
                env_state = None
                algo._dextrah_pending_runtime_state = None
                print(
                    f"[DEXTRAH resume] loading policy initialization checkpoint on rank {self._rank()} "
                    "without epoch/runtime restore"
                )
            else:
                checkpoint_epoch = self._as_int(weights.get("epoch"))
                runtime_state = weights.get("dextrah_runtime_state")
                env_state = weights.get("env_state")
                runtime_state = self._load_rank_runtime_sidecar(weights, checkpoint_epoch) or runtime_state
            if runtime_state is not None and not self._runtime_state_matches_checkpoint(
                runtime_state, checkpoint_epoch, "checkpoint"
            ):
                runtime_state = None

            weights_without_env = dict(weights)
            weights_without_env["env_state"] = None
            weights_without_env.pop("dextrah_runtime_state", None)
            original_set_full_state_weights(weights_without_env, set_epoch=set_epoch)

            if runtime_state is not None:
                algo._dextrah_pending_runtime_state = runtime_state
            elif env_state is not None:
                algo._dextrah_pending_runtime_state = {"env_state": env_state}

        def env_reset_with_deferred_restore(*args, **kwargs):
            obs = original_env_reset(*args, **kwargs)
            runtime_state = getattr(algo, "_dextrah_pending_runtime_state", None)
            if runtime_state is None:
                return obs

            restored_obs = self._restore_runtime_state(runtime_state)
            if restored_obs is not None:
                obs = self._to_device(restored_obs, algo.device)
            elif hasattr(algo.vec_env, "get_current_obs"):
                obs = algo.obs_to_tensors(algo.vec_env.get_current_obs())

            algo._dextrah_pending_runtime_state = None
            print(
                f"[DEXTRAH resume] restored runtime state on rank {self._rank()} "
                f"at epoch {getattr(algo, 'epoch_num', 'unknown')}"
            )
            return obs

        def restore_with_checkpoint_path(fn, set_epoch=True):
            algo._dextrah_restore_checkpoint = fn
            return original_restore(fn, set_epoch=set_epoch)

        algo.get_full_state_weights = get_full_state_weights_with_runtime
        algo.set_full_state_weights = set_full_state_weights_deferred
        algo.env_reset = env_reset_with_deferred_restore
        if original_restore is not None:
            algo.restore = restore_with_checkpoint_path
        algo._dextrah_resume_patched = True

    def _rank(self):
        return int(getattr(self.algo, "global_rank", os.environ.get("RANK", 0)))

    def _world_size(self):
        return int(getattr(self.algo, "world_size", os.environ.get("WORLD_SIZE", 1)))

    def _as_int(self, value):
        if isinstance(value, torch.Tensor):
            if value.numel() != 1:
                return None
            return int(value.item())
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _runtime_state_matches_checkpoint(self, runtime_state, checkpoint_epoch, source):
        state_rank = self._as_int(runtime_state.get("rank"))
        if state_rank is not None and state_rank != self._rank():
            print(
                f"[DEXTRAH resume] ignoring {source} runtime state for rank {state_rank} "
                f"on rank {self._rank()}"
            )
            return False

        state_world_size = self._as_int(runtime_state.get("world_size"))
        if state_world_size is not None and state_world_size != self._world_size():
            print(
                f"[DEXTRAH resume] ignoring {source} runtime state with world_size {state_world_size} "
                f"on world_size {self._world_size()}"
            )
            return False

        state_epoch = self._as_int(runtime_state.get("epoch"))
        if checkpoint_epoch is not None and state_epoch is not None and state_epoch != checkpoint_epoch:
            print(
                f"[DEXTRAH resume] ignoring {source} runtime state at epoch {state_epoch} "
                f"for checkpoint epoch {checkpoint_epoch}"
            )
            return False

        return True

    def _get_sidecar_interval(self):
        if self._sidecar_interval is not None:
            return int(self._sidecar_interval)
        save_freq = int(getattr(self.algo, "save_freq", 0))
        return save_freq if save_freq > 0 else 0

    def _cpu_clone(self, value):
        if isinstance(value, torch.Tensor):
            return value.detach().clone().cpu()
        if isinstance(value, np.ndarray):
            return value.copy()
        if isinstance(value, dict):
            return {key: self._cpu_clone(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._cpu_clone(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._cpu_clone(item) for item in value)
        return value

    def _to_device(self, value, device):
        if isinstance(value, torch.Tensor):
            return value.to(device=device)
        if isinstance(value, dict):
            return {key: self._to_device(item, device) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_device(item, device) for item in value]
        if isinstance(value, tuple):
            return tuple(self._to_device(item, device) for item in value)
        return value

    def _copy_algo_attr(self, name, value):
        if value is None:
            return
        if not hasattr(self.algo, name):
            setattr(self.algo, name, self._to_device(value, self.algo.device))
            return

        current_value = getattr(self.algo, name)
        if isinstance(current_value, torch.Tensor):
            restored_value = value.to(device=current_value.device, dtype=current_value.dtype)
            current_value.copy_(restored_value)
        else:
            setattr(self.algo, name, self._to_device(value, self.algo.device))

    def _rng_state(self):
        state = {
            "torch": self._cpu_clone(torch.get_rng_state()),
            "numpy": self._cpu_clone(np.random.get_state()),
            "python": random.getstate(),
        }
        if torch.cuda.is_available() and str(self.algo.device).startswith("cuda"):
            state["cuda"] = self._cpu_clone(torch.cuda.get_rng_state(self.algo.device))
        return state

    def _restore_rng_state(self, state):
        if not state:
            return
        if "torch" in state:
            torch.set_rng_state(state["torch"].cpu())
        if "cuda" in state and torch.cuda.is_available() and str(self.algo.device).startswith("cuda"):
            torch.cuda.set_rng_state(state["cuda"].cpu(), device=self.algo.device)
        if "numpy" in state:
            np.random.set_state(state["numpy"])
        if "python" in state:
            random.setstate(state["python"])

    def _pack_runtime_state(self):
        algo = self.algo
        runtime_state = {
            "version": 1,
            "rank": self._rank(),
            "world_size": self._world_size(),
            "epoch": int(getattr(algo, "epoch_num", 0)),
            "frame": int(getattr(algo, "frame", 0)),
            "rng": self._rng_state(),
        }

        for name in ("obs", "dones", "current_rewards", "current_shaped_rewards", "current_lengths", "rnn_states"):
            if hasattr(algo, name):
                runtime_state[name] = self._cpu_clone(getattr(algo, name))

        if hasattr(algo, "vec_env") and hasattr(algo.vec_env, "get_env_state"):
            runtime_state["env_state"] = self._cpu_clone(algo.vec_env.get_env_state())

        if self._save_runtime_buffer and hasattr(algo, "experience_buffer"):
            runtime_state["experience_buffer"] = {
                "tensor_dict": self._cpu_clone(getattr(algo.experience_buffer, "tensor_dict", None))
            }
        if self._save_runtime_buffer and hasattr(algo, "dataset"):
            runtime_state["dataset"] = {
                "values_dict": self._cpu_clone(getattr(algo.dataset, "values_dict", None)),
                "last_range": getattr(algo.dataset, "last_range", None),
            }
        if self._save_runtime_buffer and hasattr(algo, "central_value_net") and hasattr(algo.central_value_net, "dataset"):
            runtime_state["central_value_dataset"] = {
                "values_dict": self._cpu_clone(getattr(algo.central_value_net.dataset, "values_dict", None)),
                "last_range": getattr(algo.central_value_net.dataset, "last_range", None),
            }
        return runtime_state

    def _restore_runtime_state(self, runtime_state):
        algo = self.algo
        env_state = runtime_state.get("env_state")
        if env_state is not None and hasattr(algo.vec_env, "set_env_state"):
            algo.vec_env.set_env_state(env_state)

        for name in ("dones", "current_rewards", "current_shaped_rewards", "current_lengths", "rnn_states"):
            if name in runtime_state:
                self._copy_algo_attr(name, runtime_state[name])

        if "experience_buffer" in runtime_state and hasattr(algo, "experience_buffer"):
            tensor_dict = runtime_state["experience_buffer"].get("tensor_dict")
            if tensor_dict is not None:
                algo.experience_buffer.tensor_dict = self._to_device(tensor_dict, algo.device)

        if "dataset" in runtime_state and hasattr(algo, "dataset"):
            values_dict = runtime_state["dataset"].get("values_dict")
            algo.dataset.update_values_dict(self._to_device(values_dict, algo.device))
            if runtime_state["dataset"].get("last_range") is not None:
                algo.dataset.last_range = runtime_state["dataset"]["last_range"]

        if (
            "central_value_dataset" in runtime_state
            and hasattr(algo, "central_value_net")
            and hasattr(algo.central_value_net, "dataset")
        ):
            values_dict = runtime_state["central_value_dataset"].get("values_dict")
            algo.central_value_net.dataset.update_values_dict(self._to_device(values_dict, algo.device))
            if runtime_state["central_value_dataset"].get("last_range") is not None:
                algo.central_value_net.dataset.last_range = runtime_state["central_value_dataset"]["last_range"]

        self._restore_rng_state(runtime_state.get("rng"))
        return runtime_state.get("obs")

    def _runtime_sidecar_path(self):
        return os.path.join(self.algo.nn_dir, f"dextrah_runtime_rank_{self._rank()}.pth")

    def _save_runtime_sidecar(self, reason):
        if self.algo is None or self._saving:
            return
        self._saving = True
        try:
            os.makedirs(self.algo.nn_dir, exist_ok=True)
            path = self._runtime_sidecar_path()
            tmp_path = f"{path}.tmp.{os.getpid()}"
            torch.save(self._pack_runtime_state(), tmp_path)
            os.replace(tmp_path, path)
            print(
                f"[DEXTRAH resume] saved {reason} runtime sidecar for rank {self._rank()} "
                f"at {path}"
            )
        finally:
            self._saving = False

    def _load_rank_runtime_sidecar(self, weights, checkpoint_epoch):
        checkpoint_path = getattr(self.algo, "_dextrah_restore_checkpoint", None)
        if checkpoint_path is None:
            return None

        sidecar_path = os.path.join(os.path.dirname(checkpoint_path), f"dextrah_runtime_rank_{self._rank()}.pth")
        if not os.path.exists(sidecar_path):
            return None

        try:
            runtime_state = torch.load(sidecar_path, map_location="cpu", weights_only=False)
        except TypeError:
            runtime_state = torch.load(sidecar_path, map_location="cpu")

        if not self._runtime_state_matches_checkpoint(runtime_state, checkpoint_epoch, "sidecar"):
            return None
        return runtime_state

    def _install_signal_handlers(self):
        if self._signals_installed:
            return

        def handle_signal(signum, frame):
            print(f"[DEXTRAH resume] received signal {signum}; saving interrupt checkpoint")
            self._checkpoint_requested = True
            self._save_interrupt_checkpoint()
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        self._signals_installed = True

    def _save_interrupt_checkpoint(self):
        if self.algo is None or self._saving:
            return
        self._save_runtime_sidecar(reason="interrupt")
        if self._rank() != 0:
            return

        epoch_num = int(getattr(self.algo, "epoch_num", 0))
        frame = int(getattr(self.algo, "frame", 0))
        checkpoint_name = f"interrupt_{self.algo.config['name']}_ep_{epoch_num}_frame_{frame}"
        self.algo.save(os.path.join(self.algo.nn_dir, checkpoint_name))
        print(f"[DEXTRAH resume] saved interrupt checkpoint {checkpoint_name} on rank 0")


class RLGPUEnv(vecenv.IVecEnv):
    def __init__(self, config_name, _num_actors, **kwargs):
        self.env = env_configurations.configurations[config_name]['env_creator'](**kwargs)

    def step(self, action):
        return self.env.step(action)

    def reset(self):
        return self.env.reset()

    def get_number_of_agents(self):
        return self.env.get_number_of_agents()

    def get_env_info(self):
        info = {'action_space': self.env.action_space, 'observation_space': self.env.observation_space}

        if self.env.num_states > 0:
            info['state_space'] = self.env.state_space
            print(info['action_space'], info['observation_space'], info['state_space'])
        else:
            print(info['action_space'], info['observation_space'])

        return info

    def set_train_info(self, env_frames, *args_, **kwargs_):
        """
        Send the information in the direction algo->environment.
        Most common use case: tell the environment how far along we are in the training process. This is useful
        for implementing curriculums and things such as that.
        """
        if hasattr(self.env, 'set_train_info'):
            self.env.set_train_info(env_frames, *args_, **kwargs_)

    def get_env_state(self):
        """
        Return serializable environment state to be saved to checkpoint.
        Can be used for stateful training sessions, i.e. with adaptive curriculums.
        """
        if hasattr(self.env, 'get_env_state'):
            return self.env.get_env_state()
        else:
            return None

    def set_env_state(self, env_state):
        if hasattr(self.env, 'set_env_state'):
            self.env.set_env_state(env_state)
