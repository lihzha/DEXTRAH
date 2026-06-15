"""DEXTRAH-specific RL-Games PPO extensions for grasp-prior action anchoring."""

from __future__ import annotations

import torch
import time
import copy

from rl_games.algos_torch import a2c_continuous, torch_ext
from rl_games.common import common_losses
from rl_games.common.experience import ExperienceBuffer


BaseA2CAgent = a2c_continuous.A2CAgent


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


class DextrahGraspPriorA2CAgent(BaseA2CAgent):
    """Continuous PPO agent with an optional supervised grasp-prior action loss.

    The environment supplies per-step teacher actions in ``infos``.  This agent
    stores them in the on-policy rollout buffer and adds an MSE term on the
    current policy mean for active teacher phases.
    """

    _TEACHER_ACTIONS_KEY = "dextrah_grasp_prior_teacher_actions"
    _TEACHER_ACTIVE_KEY = "dextrah_grasp_prior_teacher_active"

    def __init__(self, base_name, params):
        super().__init__(base_name, params)
        self.dextrah_bc_loss_enabled = _as_bool(self.config.get("dextrah_grasp_prior_bc_loss_enabled", False))
        self.dextrah_bc_loss_weight = float(self.config.get("dextrah_grasp_prior_bc_loss_weight", 0.0))
        self.dextrah_bc_loss_dims = self._parse_bc_loss_dims(self.config.get("dextrah_grasp_prior_bc_loss_dims", "all"))
        self.dextrah_bc_loss_last = torch.zeros((), device=self.ppo_device)
        self.dextrah_bc_active_rate_last = torch.zeros((), device=self.ppo_device)
        self.dextrah_bc_policy_anchor_enabled = _as_bool(
            self.config.get("dextrah_bc_policy_anchor_enabled", False)
        )
        self.dextrah_bc_policy_anchor_weight = float(self.config.get("dextrah_bc_policy_anchor_weight", 0.0))
        self.dextrah_bc_policy_anchor_model = None
        self.dextrah_bc_policy_anchor_loss_last = torch.zeros((), device=self.ppo_device)
        self.dextrah_freeze_obs_rms_enabled = _as_bool(
            self.config.get("dextrah_freeze_obs_rms_enabled", False)
        )
        self.dextrah_frozen_obs_rms_state = None
        self.dextrah_actor_loss_scale = float(self.config.get("dextrah_actor_loss_scale", 1.0))
        self.dextrah_critic_loss_scale = float(self.config.get("dextrah_critic_loss_scale", 1.0))
        self.dextrah_trainable_param_scope = str(self.config.get("dextrah_trainable_param_scope", "all"))
        self._apply_dextrah_trainable_param_scope()

    def _dextrah_param_trainable(self, name: str) -> bool:
        scope = self.dextrah_trainable_param_scope.strip().lower()
        if scope in ("", "all", "*"):
            return True
        lower = name.lower()
        if scope in ("mu", "action_head", "policy_head"):
            return "mu" in lower and "sigma" not in lower and "value" not in lower and "critic" not in lower
        if scope in ("mu_sigma", "policy_output"):
            return ("mu" in lower or "sigma" in lower) and "value" not in lower and "critic" not in lower
        if scope in ("actor", "policy"):
            return "value" not in lower and "critic" not in lower
        raise ValueError(f"Unsupported dextrah_trainable_param_scope={self.dextrah_trainable_param_scope!r}")

    def _apply_dextrah_trainable_param_scope(self) -> None:
        scope = self.dextrah_trainable_param_scope.strip().lower()
        if scope in ("", "all", "*"):
            return

        trainable_names = []
        frozen_names = []
        for name, param in self.model.named_parameters():
            trainable = self._dextrah_param_trainable(name)
            param.requires_grad_(trainable)
            if trainable:
                trainable_names.append(name)
            else:
                frozen_names.append(name)
        if not trainable_names:
            raise ValueError(
                f"dextrah_trainable_param_scope={self.dextrah_trainable_param_scope!r} matched no model parameters"
            )
        preview = ", ".join(trainable_names[:12])
        if len(trainable_names) > 12:
            preview += f", ... (+{len(trainable_names) - 12} more)"
        print(
            f"[DEXTRAH] trainable parameter scope {self.dextrah_trainable_param_scope!r}: "
            f"{len(trainable_names)} trainable, {len(frozen_names)} frozen; trainable={preview}",
            flush=True,
        )

    def _clone_obs_rms_state(self, module) -> dict[str, torch.Tensor]:
        return {
            key: value.detach().clone()
            for key, value in module.state_dict().items()
            if isinstance(value, torch.Tensor)
        }

    def _obs_rms_modules(self):
        modules = []
        seen_ids = set()
        for name, module in (
            ("algo.running_mean_std", getattr(self, "running_mean_std", None)),
            ("model.running_mean_std", getattr(self.model, "running_mean_std", None)),
        ):
            if module is None or id(module) in seen_ids:
                continue
            if not hasattr(module, "state_dict") or not hasattr(module, "load_state_dict"):
                continue
            modules.append((name, module))
            seen_ids.add(id(module))
        return modules

    def _ensure_dextrah_frozen_obs_rms(self):
        if not self.dextrah_freeze_obs_rms_enabled:
            return None
        modules = self._obs_rms_modules()
        if not modules:
            return None
        if self.dextrah_frozen_obs_rms_state is None:
            self.dextrah_frozen_obs_rms_state = {
                name: self._clone_obs_rms_state(module) for name, module in modules
            }
            frozen_names = ", ".join(self.dextrah_frozen_obs_rms_state)
            print(
                f"[DEXTRAH] froze observation RunningMeanStd for BC-initialized PPO: {frozen_names}",
                flush=True,
            )
        return self.dextrah_frozen_obs_rms_state

    def dextrah_restore_frozen_obs_rms(self):
        state = self._ensure_dextrah_frozen_obs_rms()
        if state is None:
            return
        modules = dict(self._obs_rms_modules())
        for name, module_state in state.items():
            module = modules.get(name)
            if module is not None:
                module.load_state_dict(module_state, strict=True)

    def _parse_bc_loss_dims(self, raw_dims) -> torch.Tensor | None:
        if raw_dims is None:
            return None
        if isinstance(raw_dims, str):
            value = raw_dims.strip().lower()
            if value in ("", "all", "*"):
                return None
            tokens = value.replace(":", ",").replace(" ", ",").split(",")
            dims = [int(token) for token in tokens if token != ""]
        else:
            dims = [int(dim) for dim in raw_dims]
        if not dims:
            return None
        invalid = [dim for dim in dims if dim < 0 or dim >= int(self.actions_num)]
        if invalid:
            raise ValueError(f"Invalid dextrah_grasp_prior_bc_loss_dims {invalid}; action dim is {self.actions_num}")
        return torch.as_tensor(dims, dtype=torch.long, device=self.ppo_device)

    def init_tensors(self):
        if not self.dextrah_bc_loss_enabled or self.dextrah_bc_loss_weight <= 0.0:
            return super().init_tensors()

        batch_size = self.num_agents * self.num_actors
        algo_info = {
            "num_actors": self.num_actors,
            "horizon_length": self.horizon_length,
            "has_central_value": self.has_central_value,
            "use_action_masks": self.use_action_masks,
        }
        aux_tensor_dict = {
            self._TEACHER_ACTIONS_KEY: (int(self.actions_num),),
            self._TEACHER_ACTIVE_KEY: (1,),
        }
        self.experience_buffer = ExperienceBuffer(self.env_info, algo_info, self.ppo_device, aux_tensor_dict)
        self.init_current_rewards(batch_size, (batch_size, self.value_size))

        if self.is_rnn:
            raise NotImplementedError("DEXTRAH grasp-prior BC loss is only implemented for feed-forward PPO.")

        self.update_list = ["actions", "neglogpacs", "values", "mus", "sigmas"]
        self.tensor_list = self.update_list + [
            "obses",
            "states",
            "dones",
            self._TEACHER_ACTIONS_KEY,
            self._TEACHER_ACTIVE_KEY,
        ]

    def _info_tensor(self, infos: dict, key: str, fallback: torch.Tensor) -> torch.Tensor:
        value = infos.get(key)
        if value is None:
            return fallback
        if not isinstance(value, torch.Tensor):
            value = torch.as_tensor(value)
        return value.to(device=self.ppo_device, dtype=fallback.dtype).reshape_as(fallback)

    def play_steps(self):
        self.dextrah_restore_frozen_obs_rms()
        if not self.dextrah_bc_loss_enabled or self.dextrah_bc_loss_weight <= 0.0:
            batch_dict = super().play_steps()
            self.dextrah_restore_frozen_obs_rms()
            return batch_dict

        update_list = self.update_list
        step_time = 0.0

        for n in range(self.horizon_length):
            self.dextrah_restore_frozen_obs_rms()
            if self.use_action_masks:
                masks = self.vec_env.get_action_masks()
                res_dict = self.get_masked_action_values(self.obs, masks)
            else:
                res_dict = self.get_action_values(self.obs)
            self.dextrah_restore_frozen_obs_rms()

            self.experience_buffer.update_data("obses", n, self.obs["obs"])
            self.experience_buffer.update_data("dones", n, self.dones)

            for key in update_list:
                self.experience_buffer.update_data(key, n, res_dict[key])
            if self.has_central_value:
                self.experience_buffer.update_data("states", n, self.obs["states"])

            step_time_start = time.perf_counter()
            self.obs, rewards, self.dones, infos = self.env_step(res_dict["actions"])
            step_time += time.perf_counter() - step_time_start

            teacher_actions = self._info_tensor(
                infos,
                self._TEACHER_ACTIONS_KEY,
                torch.zeros_like(res_dict["actions"]),
            )
            teacher_active = self._info_tensor(
                infos,
                self._TEACHER_ACTIVE_KEY,
                torch.zeros((res_dict["actions"].shape[0], 1), device=self.ppo_device, dtype=torch.float32),
            )
            self.experience_buffer.update_data(self._TEACHER_ACTIONS_KEY, n, teacher_actions)
            self.experience_buffer.update_data(self._TEACHER_ACTIVE_KEY, n, teacher_active)

            shaped_rewards = self.rewards_shaper(rewards)
            if self.value_bootstrap and "time_outs" in infos:
                shaped_rewards += self.gamma * res_dict["values"] * self.cast_obs(infos["time_outs"]).unsqueeze(1).float()

            self.experience_buffer.update_data("rewards", n, shaped_rewards)

            self.current_rewards += rewards
            self.current_shaped_rewards += shaped_rewards
            self.current_lengths += 1

            all_done_indices = self.dones.nonzero(as_tuple=False)
            env_done_indices = all_done_indices[:: self.num_agents]

            self.game_rewards.update(self.current_rewards[env_done_indices])
            self.game_shaped_rewards.update(self.current_shaped_rewards[env_done_indices])
            self.game_lengths.update(self.current_lengths[env_done_indices])
            self.algo_observer.process_infos(infos, env_done_indices)

            not_dones = 1.0 - self.dones.float()
            self.current_rewards = self.current_rewards * not_dones.unsqueeze(1)
            self.current_shaped_rewards = self.current_shaped_rewards * not_dones.unsqueeze(1)
            self.current_lengths = self.current_lengths * not_dones

        last_values = self.get_values(self.obs)
        self.dextrah_restore_frozen_obs_rms()

        fdones = self.dones.float()
        mb_fdones = self.experience_buffer.tensor_dict["dones"].float()
        mb_values = self.experience_buffer.tensor_dict["values"]
        mb_rewards = self.experience_buffer.tensor_dict["rewards"]
        mb_advs = self.discount_values(fdones, last_values, mb_fdones, mb_values, mb_rewards)
        mb_returns = mb_advs + mb_values

        batch_dict = self.experience_buffer.get_transformed_list(
            torch_ext.swap_and_flatten01 if hasattr(torch_ext, "swap_and_flatten01") else _swap_and_flatten01,
            self.tensor_list,
        )
        batch_dict["returns"] = _swap_and_flatten01(mb_returns)
        batch_dict["played_frames"] = self.batch_size
        batch_dict["step_time"] = step_time
        return batch_dict

    def prepare_dataset(self, batch_dict):
        teacher_actions = batch_dict.get(self._TEACHER_ACTIONS_KEY)
        teacher_active = batch_dict.get(self._TEACHER_ACTIVE_KEY)
        super().prepare_dataset(batch_dict)
        if (
            self.dextrah_bc_loss_enabled
            and self.dextrah_bc_loss_weight > 0.0
            and teacher_actions is not None
            and teacher_active is not None
        ):
            self.dataset.values_dict[self._TEACHER_ACTIONS_KEY] = teacher_actions
            self.dataset.values_dict[self._TEACHER_ACTIVE_KEY] = teacher_active

    def _compute_dextrah_bc_loss(self, mu: torch.Tensor, input_dict: dict) -> torch.Tensor:
        teacher_actions = input_dict.get(self._TEACHER_ACTIONS_KEY)
        teacher_active = input_dict.get(self._TEACHER_ACTIVE_KEY)
        if (
            teacher_actions is None
            or teacher_active is None
            or not self.dextrah_bc_loss_enabled
            or self.dextrah_bc_loss_weight <= 0.0
        ):
            self.dextrah_bc_loss_last = torch.zeros((), device=self.ppo_device)
            self.dextrah_bc_active_rate_last = torch.zeros((), device=self.ppo_device)
            return self.dextrah_bc_loss_last

        active = teacher_active.to(dtype=mu.dtype).reshape(mu.shape[0], -1)[:, 0].clamp(0.0, 1.0)
        self.dextrah_bc_active_rate_last = active.detach().mean()
        if self.dextrah_bc_loss_dims is None:
            pred = mu
            target = teacher_actions.to(dtype=mu.dtype)
        else:
            pred = mu.index_select(-1, self.dextrah_bc_loss_dims)
            target = teacher_actions.to(dtype=mu.dtype).index_select(-1, self.dextrah_bc_loss_dims)
        mse = torch.mean(torch.square(pred - target), dim=-1)
        denom = torch.clamp(active.sum(), min=1.0)
        bc_loss = self.dextrah_bc_loss_weight * torch.sum(mse * active) / denom
        self.dextrah_bc_loss_last = bc_loss.detach()
        return bc_loss

    def _ensure_dextrah_policy_anchor_model(self):
        if (
            not self.dextrah_bc_policy_anchor_enabled
            or self.dextrah_bc_policy_anchor_weight <= 0.0
        ):
            return None
        if self.dextrah_bc_policy_anchor_model is None:
            self.dextrah_bc_policy_anchor_model = copy.deepcopy(self.model)
            self.dextrah_bc_policy_anchor_model.to(self.ppo_device)
            self.dextrah_bc_policy_anchor_model.eval()
            for param in self.dextrah_bc_policy_anchor_model.parameters():
                param.requires_grad_(False)
        return self.dextrah_bc_policy_anchor_model

    def _compute_dextrah_policy_anchor_loss(self, mu: torch.Tensor, batch_dict: dict) -> torch.Tensor:
        anchor_model = self._ensure_dextrah_policy_anchor_model()
        if anchor_model is None:
            self.dextrah_bc_policy_anchor_loss_last = torch.zeros((), device=self.ppo_device)
            return self.dextrah_bc_policy_anchor_loss_last

        student_batch = dict(batch_dict)
        student_batch["is_train"] = False
        teacher_batch = dict(batch_dict)
        teacher_batch["is_train"] = False
        student_res = self.model(student_batch)
        student_mu = student_res["mus"]
        with torch.no_grad():
            teacher_res = anchor_model(teacher_batch)
            teacher_mu = teacher_res["mus"].detach()
        anchor_loss = self.dextrah_bc_policy_anchor_weight * torch.mean(torch.square(student_mu - teacher_mu))
        self.dextrah_bc_policy_anchor_loss_last = anchor_loss.detach()
        return anchor_loss

    def calc_gradients(self, input_dict):
        self.dextrah_restore_frozen_obs_rms()
        value_preds_batch = input_dict["old_values"]
        old_action_log_probs_batch = input_dict["old_logp_actions"]
        advantage = input_dict["advantages"]
        old_mu_batch = input_dict["mu"]
        old_sigma_batch = input_dict["sigma"]
        return_batch = input_dict["returns"]
        actions_batch = input_dict["actions"]
        obs_batch = self._preproc_obs(input_dict["obs"])

        lr_mul = 1.0
        curr_e_clip = self.e_clip
        batch_dict = {"is_train": True, "prev_actions": actions_batch, "obs": obs_batch}

        rnn_masks = None
        if self.is_rnn:
            rnn_masks = input_dict["rnn_masks"]
            batch_dict["rnn_states"] = input_dict["rnn_states"]
            batch_dict["seq_length"] = self.seq_length
            if self.zero_rnn_on_done:
                batch_dict["dones"] = input_dict["dones"]

        with torch.cuda.amp.autocast(enabled=self.mixed_precision):
            res_dict = self.model(batch_dict)
            action_log_probs = res_dict["prev_neglogp"]
            values = res_dict["values"]
            entropy = res_dict["entropy"]
            mu = res_dict["mus"]
            sigma = res_dict["sigmas"]

            a_loss = self.actor_loss_func(old_action_log_probs_batch, action_log_probs, advantage, self.ppo, curr_e_clip)
            if self.has_value_loss:
                c_loss = common_losses.critic_loss(
                    self.model,
                    value_preds_batch,
                    values,
                    curr_e_clip,
                    return_batch,
                    self.clip_value,
                )
            else:
                c_loss = torch.zeros(1, device=self.ppo_device)
            if self.bound_loss_type == "regularisation":
                b_loss = self.reg_loss(mu)
            elif self.bound_loss_type == "bound":
                b_loss = self.bound_loss(mu)
            else:
                b_loss = torch.zeros(1, device=self.ppo_device)
            losses, _ = torch_ext.apply_masks(
                [a_loss.unsqueeze(1), c_loss, entropy.unsqueeze(1), b_loss.unsqueeze(1)],
                rnn_masks,
            )
            a_loss, c_loss, entropy, b_loss = losses[0], losses[1], losses[2], losses[3]

            bc_loss = self._compute_dextrah_bc_loss(mu, input_dict)
            policy_anchor_loss = self._compute_dextrah_policy_anchor_loss(mu, batch_dict)
            loss = (
                self.dextrah_actor_loss_scale * a_loss
                + 0.5 * self.dextrah_critic_loss_scale * c_loss * self.critic_coef
                - entropy * self.entropy_coef
                + b_loss * self.bounds_loss_coef
                + bc_loss
                + policy_anchor_loss
            )
            aux_loss = self.model.get_aux_loss()
            self.aux_loss_dict = {}
            if aux_loss is not None:
                for key, value in aux_loss.items():
                    loss += value
                    self.aux_loss_dict.setdefault(key, []).append(value.detach())
            self.aux_loss_dict.setdefault("dextrah_grasp_prior_bc_loss", []).append(self.dextrah_bc_loss_last)
            self.aux_loss_dict.setdefault("dextrah_grasp_prior_bc_active_rate", []).append(
                self.dextrah_bc_active_rate_last
            )
            self.aux_loss_dict.setdefault("dextrah_bc_policy_anchor_loss", []).append(
                self.dextrah_bc_policy_anchor_loss_last
            )
            self.aux_loss_dict.setdefault("dextrah_actor_loss_scale", []).append(
                torch.as_tensor(self.dextrah_actor_loss_scale, device=self.ppo_device)
            )
            self.aux_loss_dict.setdefault("dextrah_critic_loss_scale", []).append(
                torch.as_tensor(self.dextrah_critic_loss_scale, device=self.ppo_device)
            )

            if self.multi_gpu:
                self.optimizer.zero_grad()
            else:
                for param in self.model.parameters():
                    param.grad = None

        self.scaler.scale(loss).backward()
        self.trancate_gradients_and_step()
        self.dextrah_restore_frozen_obs_rms()

        with torch.no_grad():
            reduce_kl = rnn_masks is None
            kl_dist = torch_ext.policy_kl(mu.detach(), sigma.detach(), old_mu_batch, old_sigma_batch, reduce_kl)
            if rnn_masks is not None:
                kl_dist = (kl_dist * rnn_masks).sum() / rnn_masks.numel()

        self.diagnostics.mini_batch(
            self,
            {
                "values": value_preds_batch,
                "returns": return_batch,
                "new_neglogp": action_log_probs,
                "old_neglogp": old_action_log_probs_batch,
                "masks": rnn_masks,
            },
            curr_e_clip,
            0,
        )

        self.train_result = (
            a_loss,
            c_loss,
            entropy,
            kl_dist,
            self.last_lr,
            lr_mul,
            mu.detach(),
            sigma.detach(),
            b_loss,
        )


def _swap_and_flatten01(arr):
    if arr is None:
        return arr
    shape = arr.size()
    return arr.transpose(0, 1).reshape(shape[0] * shape[1], *shape[2:])
