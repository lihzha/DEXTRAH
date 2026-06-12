"""Small residual action adapters for trajectory-tracking BC diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

import torch


class ResidualActionAdapter(torch.nn.Module):
    """Zero-initialized residual action head added on top of a frozen actor."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_dim: int = 64,
        max_action: float = 0.5,
        gate_enabled: bool = False,
        gate_hidden_dim: int | None = None,
        gate_bias_init: float = 0.0,
        context_dim: int = 0,
        context_features: list[str] | tuple[str, ...] | None = None,
    ):
        super().__init__()
        if obs_dim <= 0:
            raise ValueError(f"obs_dim must be positive, got {obs_dim}")
        if action_dim <= 0:
            raise ValueError(f"action_dim must be positive, got {action_dim}")
        if hidden_dim < 0:
            raise ValueError(f"hidden_dim must be non-negative, got {hidden_dim}")
        if max_action < 0.0:
            raise ValueError(f"max_action must be non-negative, got {max_action}")
        if context_dim < 0:
            raise ValueError(f"context_dim must be non-negative, got {context_dim}")
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.hidden_dim = int(hidden_dim)
        self.max_action = float(max_action)
        self.gate_enabled = bool(gate_enabled)
        self.gate_hidden_dim = int(self.hidden_dim if gate_hidden_dim is None else gate_hidden_dim)
        self.gate_bias_init = float(gate_bias_init)
        self.context_dim = int(context_dim)
        self.context_features = tuple(str(item) for item in (context_features or ()))
        if self.context_features and len(self.context_features) != self.context_dim:
            raise ValueError(
                f"context_features length {len(self.context_features)} does not match context_dim {self.context_dim}"
            )
        if self.gate_hidden_dim < 0:
            raise ValueError(f"gate_hidden_dim must be non-negative, got {self.gate_hidden_dim}")
        input_dim = self.obs_dim + self.context_dim
        if self.hidden_dim > 0:
            self.net = torch.nn.Sequential(
                torch.nn.Linear(input_dim, self.hidden_dim),
                torch.nn.Tanh(),
                torch.nn.Linear(self.hidden_dim, self.action_dim),
            )
            final_layer = self.net[-1]
        else:
            self.net = torch.nn.Linear(input_dim, self.action_dim)
            final_layer = self.net
        if isinstance(final_layer, torch.nn.Linear):
            torch.nn.init.zeros_(final_layer.weight)
            torch.nn.init.zeros_(final_layer.bias)
        if self.gate_enabled:
            if self.gate_hidden_dim > 0:
                self.gate_net = torch.nn.Sequential(
                    torch.nn.Linear(input_dim, self.gate_hidden_dim),
                    torch.nn.Tanh(),
                    torch.nn.Linear(self.gate_hidden_dim, 1),
                )
                gate_final_layer = self.gate_net[-1]
            else:
                self.gate_net = torch.nn.Linear(input_dim, 1)
                gate_final_layer = self.gate_net
            if isinstance(gate_final_layer, torch.nn.Linear):
                torch.nn.init.zeros_(gate_final_layer.weight)
                torch.nn.init.constant_(gate_final_layer.bias, self.gate_bias_init)
        else:
            self.gate_net = None

    def _input(self, obs: torch.Tensor, context: torch.Tensor | None = None) -> torch.Tensor:
        obs = obs.float()
        if self.context_dim <= 0:
            return obs
        if context is None:
            raise ValueError(f"Residual adapter requires {self.context_dim} context features: {self.context_features}")
        context = context.float().to(device=obs.device)
        if context.ndim == 1:
            context = context.unsqueeze(-1)
        if context.shape[0] != obs.shape[0] or context.shape[-1] != self.context_dim:
            raise ValueError(
                f"Context shape {tuple(context.shape)} is incompatible with obs {tuple(obs.shape)} "
                f"and context_dim {self.context_dim}"
            )
        return torch.cat([obs, context], dim=-1)

    def gate_values(self, obs: torch.Tensor, context: torch.Tensor | None = None) -> torch.Tensor:
        x = self._input(obs, context)
        if self.gate_net is None:
            return torch.ones(x.shape[0], 1, dtype=x.dtype, device=x.device)
        return torch.sigmoid(self.gate_net(x))

    def forward(self, obs: torch.Tensor, context: torch.Tensor | None = None) -> torch.Tensor:
        x = self._input(obs, context)
        residual = self.max_action * torch.tanh(self.net(x))
        if self.gate_net is not None:
            residual = residual * self.gate_values(obs, context)
        return residual

    def metadata(self) -> dict[str, object]:
        return {
            "type": "ResidualActionAdapter",
            "obs_dim": self.obs_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "max_action": self.max_action,
            "gate_enabled": self.gate_enabled,
            "gate_hidden_dim": self.gate_hidden_dim,
            "gate_bias_init": self.gate_bias_init,
            "context_dim": self.context_dim,
            "context_features": list(self.context_features),
        }


def build_residual_adapter_from_metadata(metadata: Mapping[str, object]) -> ResidualActionAdapter:
    adapter = ResidualActionAdapter(
        obs_dim=int(metadata["obs_dim"]),
        action_dim=int(metadata["action_dim"]),
        hidden_dim=int(metadata.get("hidden_dim", 64)),
        max_action=float(metadata.get("max_action", 0.5)),
        gate_enabled=bool(metadata.get("gate_enabled", False)),
        gate_hidden_dim=int(metadata.get("gate_hidden_dim", metadata.get("hidden_dim", 64))),
        gate_bias_init=float(metadata.get("gate_bias_init", 0.0)),
        context_dim=int(metadata.get("context_dim", 0)),
        context_features=list(metadata.get("context_features", []) or []),
    )
    raw_state = metadata.get("state_dict")
    if raw_state is None:
        raise KeyError("Residual adapter metadata lacks state_dict")
    state_dict = {str(key): value for key, value in raw_state.items()}
    adapter.load_state_dict(state_dict)
    return adapter
