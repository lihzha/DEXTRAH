"""Small residual action adapters for trajectory-tracking BC diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

import torch


class ResidualActionAdapter(torch.nn.Module):
    """Zero-initialized residual action head added on top of a frozen actor."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 64, max_action: float = 0.5):
        super().__init__()
        if obs_dim <= 0:
            raise ValueError(f"obs_dim must be positive, got {obs_dim}")
        if action_dim <= 0:
            raise ValueError(f"action_dim must be positive, got {action_dim}")
        if hidden_dim < 0:
            raise ValueError(f"hidden_dim must be non-negative, got {hidden_dim}")
        if max_action < 0.0:
            raise ValueError(f"max_action must be non-negative, got {max_action}")
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.hidden_dim = int(hidden_dim)
        self.max_action = float(max_action)
        if self.hidden_dim > 0:
            self.net = torch.nn.Sequential(
                torch.nn.Linear(self.obs_dim, self.hidden_dim),
                torch.nn.Tanh(),
                torch.nn.Linear(self.hidden_dim, self.action_dim),
            )
            final_layer = self.net[-1]
        else:
            self.net = torch.nn.Linear(self.obs_dim, self.action_dim)
            final_layer = self.net
        if isinstance(final_layer, torch.nn.Linear):
            torch.nn.init.zeros_(final_layer.weight)
            torch.nn.init.zeros_(final_layer.bias)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        obs = obs.float()
        return self.max_action * torch.tanh(self.net(obs))

    def metadata(self) -> dict[str, int | float | str]:
        return {
            "type": "ResidualActionAdapter",
            "obs_dim": self.obs_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "max_action": self.max_action,
        }


def build_residual_adapter_from_metadata(metadata: Mapping[str, object]) -> ResidualActionAdapter:
    adapter = ResidualActionAdapter(
        obs_dim=int(metadata["obs_dim"]),
        action_dim=int(metadata["action_dim"]),
        hidden_dim=int(metadata.get("hidden_dim", 64)),
        max_action=float(metadata.get("max_action", 0.5)),
    )
    raw_state = metadata.get("state_dict")
    if raw_state is None:
        raise KeyError("Residual adapter metadata lacks state_dict")
    state_dict = {str(key): value for key, value in raw_state.items()}
    adapter.load_state_dict(state_dict)
    return adapter
