"""Diffusion Policy workspace with explicit weight-only initialization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dill
import torch
from diffusion_policy.workspace.train_diffusion_unet_image_workspace import (
    TrainDiffusionUnetImageWorkspace,
)
from omegaconf import OmegaConf


def _checkpoint_state_dicts(path: Path) -> dict[str, Any]:
    with path.open("rb") as checkpoint_file:
        payload = torch.load(
            checkpoint_file,
            map_location="cpu",
            pickle_module=dill,
        )
    state_dicts = payload.get("state_dicts") if isinstance(payload, dict) else None
    if not isinstance(state_dicts, dict):
        raise ValueError(f"Checkpoint has no state_dicts mapping: {path}")
    return state_dicts


class TrainDiffusionUnetImageWorkspaceWithInit(TrainDiffusionUnetImageWorkspace):
    """Reset training state while initializing policy weights from a checkpoint."""

    def _initialize_policy_weights(self, checkpoint: Path, use_ema: bool) -> str:
        state_dicts = _checkpoint_state_dicts(checkpoint)
        source_key = "ema_model" if use_ema and "ema_model" in state_dicts else "model"
        source_state = state_dicts.get(source_key)
        if not isinstance(source_state, dict):
            raise ValueError(f"Checkpoint is missing policy state {source_key!r}: {checkpoint}")
        self.model.load_state_dict(source_state, strict=True)
        if self.ema_model is not None:
            self.ema_model.load_state_dict(source_state, strict=True)
        return source_key

    def run(self) -> None:
        init_checkpoint = OmegaConf.select(self.cfg, "training.init_checkpoint")
        resume = bool(OmegaConf.select(self.cfg, "training.resume", default=False))
        if init_checkpoint and resume:
            raise ValueError("training.init_checkpoint and training.resume are mutually exclusive")
        if init_checkpoint:
            checkpoint = Path(str(init_checkpoint)).expanduser().resolve()
            if not checkpoint.is_file():
                raise FileNotFoundError(f"Missing weight initialization checkpoint: {checkpoint}")
            use_ema = bool(OmegaConf.select(self.cfg, "training.init_use_ema", default=True))
            source_key = self._initialize_policy_weights(checkpoint, use_ema=use_ema)
            print(
                "YAM_RGB_DP_WEIGHT_INIT "
                f"checkpoint={checkpoint} source_key={source_key} "
                f"global_step={self.global_step} epoch={self.epoch}"
            )
        super().run()
