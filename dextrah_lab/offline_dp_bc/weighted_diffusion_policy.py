"""Small loss-weight adapters for official Diffusion Policy training."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from einops import reduce

from diffusion_policy.common.pytorch_util import dict_apply
from diffusion_policy.policy.diffusion_unet_image_policy import DiffusionUnetImagePolicy
from diffusion_policy.policy.diffusion_unet_lowdim_policy import DiffusionUnetLowdimPolicy


class WeightedDiffusionUnetLowdimPolicy(DiffusionUnetLowdimPolicy):
    """Official lowdim Diffusion Policy with optional per-action loss weights.

    This adapter intentionally keeps the official model, normalizer, sampler,
    and inference behavior unchanged. It only weights the denoising loss by
    action channel during training, which is useful for bounded diagnostics on
    tiny datasets where the binary gripper channel can be washed out by pose
    channels.
    """

    def __init__(self, *args, action_loss_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        if action_loss_weights is None:
            weights = torch.ones(self.action_dim, dtype=torch.float32)
        else:
            weights = torch.as_tensor(action_loss_weights, dtype=torch.float32)
            if weights.numel() != self.action_dim:
                raise ValueError(
                    f"action_loss_weights must have {self.action_dim} entries, got {weights.numel()}"
                )
        self.register_buffer("action_loss_weights", weights.reshape(1, 1, self.action_dim))

    def compute_loss(self, batch):
        # This mirrors official DiffusionUnetLowdimPolicy.compute_loss, with one
        # scoped change: action-channel weights are applied before reduction.
        assert "valid_mask" not in batch
        nbatch = self.normalizer.normalize(batch)
        obs = nbatch["obs"]
        action = nbatch["action"]

        local_cond = None
        global_cond = None
        trajectory = action
        if self.obs_as_local_cond:
            local_cond = obs
            local_cond[:, self.n_obs_steps :, :] = 0
        elif self.obs_as_global_cond:
            global_cond = obs[:, : self.n_obs_steps, :].reshape(obs.shape[0], -1)
            if self.pred_action_steps_only:
                start = self.n_obs_steps
                if self.oa_step_convention:
                    start = self.n_obs_steps - 1
                end = start + self.n_action_steps
                trajectory = action[:, start:end]
        else:
            trajectory = torch.cat([action, obs], dim=-1)

        if self.pred_action_steps_only:
            condition_mask = torch.zeros_like(trajectory, dtype=torch.bool)
        else:
            condition_mask = self.mask_generator(trajectory.shape)

        noise = torch.randn(trajectory.shape, device=trajectory.device)
        timesteps = torch.randint(
            0,
            self.noise_scheduler.config.num_train_timesteps,
            (trajectory.shape[0],),
            device=trajectory.device,
        ).long()
        noisy_trajectory = self.noise_scheduler.add_noise(trajectory, noise, timesteps)

        loss_mask = ~condition_mask
        noisy_trajectory[condition_mask] = trajectory[condition_mask]
        pred = self.model(noisy_trajectory, timesteps, local_cond=local_cond, global_cond=global_cond)

        pred_type = self.noise_scheduler.config.prediction_type
        if pred_type == "epsilon":
            target = noise
        elif pred_type == "sample":
            target = trajectory
        else:
            raise ValueError(f"Unsupported prediction type {pred_type}")

        loss = F.mse_loss(pred, target, reduction="none")
        if loss.shape[-1] == self.action_dim:
            loss = loss * self.action_loss_weights.to(device=loss.device, dtype=loss.dtype)
        loss = loss * loss_mask.type(loss.dtype)
        loss = reduce(loss, "b ... -> b (...)", "mean")
        return loss.mean()


class WeightedDiffusionUnetImagePolicy(DiffusionUnetImagePolicy):
    """Official image Diffusion Policy with optional per-action loss weights."""

    def __init__(self, *args, action_loss_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        if action_loss_weights is None:
            weights = torch.ones(self.action_dim, dtype=torch.float32)
        else:
            weights = torch.as_tensor(action_loss_weights, dtype=torch.float32)
            if weights.numel() != self.action_dim:
                raise ValueError(
                    f"action_loss_weights must have {self.action_dim} entries, got {weights.numel()}"
                )
        self.register_buffer("action_loss_weights", weights.reshape(1, 1, self.action_dim))

    def compute_loss(self, batch):
        # Mirrors official DiffusionUnetImagePolicy.compute_loss, with one
        # scoped change: action-channel weights are applied before reduction.
        assert "valid_mask" not in batch
        nobs = self.normalizer.normalize(batch["obs"])
        nactions = self.normalizer["action"].normalize(batch["action"])
        batch_size = nactions.shape[0]
        horizon = nactions.shape[1]

        local_cond = None
        global_cond = None
        trajectory = nactions
        cond_data = trajectory
        if self.obs_as_global_cond:
            this_nobs = dict_apply(
                nobs,
                lambda x: x[:, : self.n_obs_steps, ...].reshape(-1, *x.shape[2:]),
            )
            nobs_features = self.obs_encoder(this_nobs)
            global_cond = nobs_features.reshape(batch_size, -1)
        else:
            this_nobs = dict_apply(nobs, lambda x: x.reshape(-1, *x.shape[2:]))
            nobs_features = self.obs_encoder(this_nobs)
            nobs_features = nobs_features.reshape(batch_size, horizon, -1)
            cond_data = torch.cat([nactions, nobs_features], dim=-1)
            trajectory = cond_data.detach()

        condition_mask = self.mask_generator(trajectory.shape)
        noise = torch.randn(trajectory.shape, device=trajectory.device)
        timesteps = torch.randint(
            0,
            self.noise_scheduler.config.num_train_timesteps,
            (batch_size,),
            device=trajectory.device,
        ).long()
        noisy_trajectory = self.noise_scheduler.add_noise(trajectory, noise, timesteps)

        loss_mask = ~condition_mask
        noisy_trajectory[condition_mask] = cond_data[condition_mask]
        pred = self.model(noisy_trajectory, timesteps, local_cond=local_cond, global_cond=global_cond)

        pred_type = self.noise_scheduler.config.prediction_type
        if pred_type == "epsilon":
            target = noise
        elif pred_type == "sample":
            target = trajectory
        else:
            raise ValueError(f"Unsupported prediction type {pred_type}")

        loss = F.mse_loss(pred, target, reduction="none")
        if loss.shape[-1] == self.action_dim:
            loss = loss * self.action_loss_weights.to(device=loss.device, dtype=loss.dtype)
        loss = loss * loss_mask.type(loss.dtype)
        loss = reduce(loss, "b ... -> b (...)", "mean")
        return loss.mean()
