"""Small loss-weight adapters for official Diffusion Policy training."""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as F
from einops import reduce

from diffusion_policy.common.pytorch_util import dict_apply
from diffusion_policy.policy.diffusion_unet_image_policy import DiffusionUnetImagePolicy
from diffusion_policy.policy.diffusion_unet_lowdim_policy import DiffusionUnetLowdimPolicy


def _load_image_policy_from_checkpoint(checkpoint_path: str | Path):
    from diffusion_policy.workspace.train_diffusion_unet_image_workspace import TrainDiffusionUnetImageWorkspace

    path = Path(checkpoint_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    workspace = TrainDiffusionUnetImageWorkspace.create_from_checkpoint(str(path))
    policy = workspace.ema_model if getattr(workspace, "ema_model", None) is not None else workspace.model
    if policy is None:
        raise RuntimeError(f"{path} did not contain a usable model or EMA policy")
    policy.eval()
    policy.requires_grad_(False)
    return policy


def _image_policy_sample_prediction(
    policy: DiffusionUnetImagePolicy,
    obs_dict: dict[str, torch.Tensor],
    action: torch.Tensor,
    noise: torch.Tensor,
    timesteps: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return raw-action clean-sample prediction and the diffusion loss mask."""

    nobs = policy.normalizer.normalize(obs_dict)
    nactions = policy.normalizer["action"].normalize(action)
    batch_size = nactions.shape[0]
    horizon = nactions.shape[1]

    local_cond = None
    global_cond = None
    trajectory = nactions
    cond_data = trajectory
    if policy.obs_as_global_cond:
        this_nobs = dict_apply(
            nobs,
            lambda x: x[:, : policy.n_obs_steps, ...].reshape(-1, *x.shape[2:]),
        )
        nobs_features = policy.obs_encoder(this_nobs)
        global_cond = nobs_features.reshape(batch_size, -1)
    else:
        this_nobs = dict_apply(nobs, lambda x: x.reshape(-1, *x.shape[2:]))
        nobs_features = policy.obs_encoder(this_nobs)
        nobs_features = nobs_features.reshape(batch_size, horizon, -1)
        cond_data = torch.cat([nactions, nobs_features], dim=-1)
        trajectory = cond_data.detach()

    if policy.noise_scheduler.config.prediction_type != "sample":
        raise ValueError(
            "Reference distillation currently expects prediction_type='sample', "
            f"got {policy.noise_scheduler.config.prediction_type!r}"
        )

    condition_mask = policy.mask_generator(trajectory.shape)
    noisy_trajectory = policy.noise_scheduler.add_noise(trajectory, noise, timesteps)
    noisy_trajectory[condition_mask] = cond_data[condition_mask]
    pred = policy.model(noisy_trajectory, timesteps, local_cond=local_cond, global_cond=global_cond)
    raw_action = policy.normalizer["action"].unnormalize(pred[..., : policy.action_dim])
    return raw_action, ~condition_mask[..., : policy.action_dim]


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
    """Official image Diffusion Policy with optional action weighting/distillation."""

    def __init__(
        self,
        *args,
        action_loss_weights=None,
        distill_reference_checkpoint=None,
        distill_loss_weight: float = 0.0,
        distill_mask_key: str = "distill_mask",
        distill_use_action_loss_weights: bool = True,
        **kwargs,
    ):
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
        self.distill_reference_checkpoint = (
            None if distill_reference_checkpoint in (None, "") else str(distill_reference_checkpoint)
        )
        self.distill_loss_weight = float(distill_loss_weight)
        self.distill_mask_key = str(distill_mask_key)
        self.distill_use_action_loss_weights = bool(distill_use_action_loss_weights)
        self._distill_reference_holder: dict[str, object] = {}
        self.last_loss_breakdown: dict[str, float] = {}

    def _get_distill_reference_policy(self, device: torch.device):
        if self.distill_reference_checkpoint is None or self.distill_loss_weight <= 0.0:
            return None
        policy = self._distill_reference_holder.get("policy")
        if policy is None:
            policy = _load_image_policy_from_checkpoint(self.distill_reference_checkpoint)
            self._distill_reference_holder["policy"] = policy
        policy = policy.to(device)
        policy.eval()
        policy.requires_grad_(False)
        return policy

    def compute_loss(self, batch):
        # Mirrors official DiffusionUnetImagePolicy.compute_loss, with one
        # default scoped change: action-channel weights are applied before
        # reduction. Optional frozen-reference distillation preserves nominal
        # behavior during support-expansion fine-tunes.
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
        supervised_loss = loss.mean()
        total_loss = supervised_loss

        distill_loss = pred.new_tensor(0.0)
        reference_policy = self._get_distill_reference_policy(pred.device)
        if reference_policy is not None:
            if pred_type != "sample":
                raise ValueError("Reference distillation requires prediction_type='sample'")
            student_raw_action = self.normalizer["action"].unnormalize(pred[..., : self.action_dim])
            with torch.no_grad():
                teacher_raw_action, teacher_loss_mask = _image_policy_sample_prediction(
                    reference_policy,
                    batch["obs"],
                    batch["action"],
                    noise.detach(),
                    timesteps.detach(),
                )
            distill_mask = loss_mask[..., : self.action_dim] & teacher_loss_mask
            if self.distill_mask_key in batch:
                row_mask = batch[self.distill_mask_key].to(device=pred.device)
                if row_mask.ndim == 2:
                    row_mask = row_mask.unsqueeze(-1)
                if row_mask.shape[:2] != distill_mask.shape[:2]:
                    raise ValueError(
                        f"{self.distill_mask_key} has shape {tuple(row_mask.shape)}, "
                        f"expected leading dims {tuple(distill_mask.shape[:2])}"
                    )
                distill_mask = distill_mask & (row_mask > 0.5)
            distill_terms = F.mse_loss(student_raw_action, teacher_raw_action, reduction="none")
            if self.distill_use_action_loss_weights:
                distill_terms = distill_terms * self.action_loss_weights.to(
                    device=distill_terms.device,
                    dtype=distill_terms.dtype,
                )
            distill_mask_f = distill_mask.type(distill_terms.dtype)
            active = distill_mask_f.sum()
            if bool(active.item() > 0):
                distill_loss = (distill_terms * distill_mask_f).sum() / active.clamp_min(1.0)
                total_loss = total_loss + float(self.distill_loss_weight) * distill_loss

        self.last_loss_breakdown = {
            "supervised_loss": float(supervised_loss.detach().cpu()),
            "distill_loss": float(distill_loss.detach().cpu()),
            "distill_loss_weight": float(self.distill_loss_weight),
        }
        return total_loss
