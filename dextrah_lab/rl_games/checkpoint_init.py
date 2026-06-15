"""Utilities for RL-Games policy-initialization checkpoints."""

from __future__ import annotations

import copy
from typing import Any

import torch


POLICY_INITIALIZATION_SEMANTICS = "policy_initialization"

_RUNTIME_STATE_KEYS = (
    "dextrah_runtime_state",
    "env_state",
)

_COUNTER_ZERO_KEYS = (
    "epoch",
    "frame",
    "frames",
    "total_frames",
)

_OPTIONAL_OPTIMIZER_KEYS = (
    "optimizer",
    "optimizers",
    "optimizer_state_dict",
    "central_value_optimizer",
    "scheduler",
    "lr_scheduler",
    "scaler",
    "grad_scaler",
    "amp_scaler",
)


def _json_safe_repr(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return value.detach().cpu().item()
        return {
            "type": "tensor",
            "shape": list(value.shape),
            "dtype": str(value.dtype),
        }
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(str(key) for key in value.keys())[:64],
            "len": len(value),
        }
    if isinstance(value, (list, tuple)):
        return {
            "type": type(value).__name__,
            "len": len(value),
        }
    return value


def _zero_like(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return torch.zeros_like(value)
    if isinstance(value, float):
        return 0.0
    return 0


def is_policy_initialization_checkpoint(weights: dict[str, Any]) -> bool:
    """Return whether a checkpoint should initialize weights without resume state."""

    if weights.get("dextrah_checkpoint_semantics") == POLICY_INITIALIZATION_SEMANTICS:
        return True
    diagnostic = weights.get("dextrah_bc_diagnostic")
    if isinstance(diagnostic, dict) and diagnostic.get("checkpoint_semantics") == POLICY_INITIALIZATION_SEMANTICS:
        return True

    # Legacy BC checkpoints predate the explicit semantics marker but carry this
    # payload. They should seed PPO weights/RMS only, never optimizer/runtime state.
    return isinstance(weights.get("bc_reference_action_imitation"), dict)


def sanitize_rlgames_checkpoint_for_initialization(
    state: dict[str, Any],
    *,
    source_checkpoint: str,
    metadata: dict[str, Any] | None = None,
    strip_optimizer: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert an RL-Games resume checkpoint into a policy-initialization checkpoint.

    The returned checkpoint keeps load-required model/RMS payloads but removes
    DEXTRAH runtime/env resume state and resets epoch/frame counters. Optimizer
    payloads are preserved by default because RL-Games restore paths commonly
    expect them during training checkpoint loads; callers can strip them for
    compatibility experiments.
    """

    if not isinstance(state, dict):
        raise TypeError(f"Expected dict checkpoint, got {type(state).__name__}")

    sanitized = copy.deepcopy(state)
    removed: dict[str, Any] = {}
    reset: dict[str, Any] = {}

    for key in _RUNTIME_STATE_KEYS:
        if key in sanitized:
            removed[key] = _json_safe_repr(sanitized.pop(key))

    if strip_optimizer:
        for key in _OPTIONAL_OPTIMIZER_KEYS:
            if key in sanitized:
                removed[key] = _json_safe_repr(sanitized.pop(key))

    for key in _COUNTER_ZERO_KEYS:
        if key in sanitized:
            reset[key] = _json_safe_repr(sanitized[key])
            sanitized[key] = _zero_like(sanitized[key])

    diagnostic = copy.deepcopy(sanitized.get("dextrah_bc_diagnostic", {}))
    if not isinstance(diagnostic, dict):
        diagnostic = {"previous_dextrah_bc_diagnostic": _json_safe_repr(diagnostic)}
    diagnostic.update(metadata or {})
    diagnostic.update(
        {
            "checkpoint_semantics": POLICY_INITIALIZATION_SEMANTICS,
            "source_checkpoint": source_checkpoint,
            "sanitized_for_policy_initialization": True,
            "stripped_optimizer": bool(strip_optimizer),
            "removed_resume_fields": sorted(removed.keys()),
            "reset_counter_fields": sorted(reset.keys()),
        }
    )

    sanitized["dextrah_checkpoint_semantics"] = POLICY_INITIALIZATION_SEMANTICS
    sanitized["dextrah_bc_diagnostic"] = diagnostic

    summary = {
        "checkpoint_semantics": POLICY_INITIALIZATION_SEMANTICS,
        "source_checkpoint": source_checkpoint,
        "stripped_optimizer": bool(strip_optimizer),
        "removed": removed,
        "reset": reset,
        "output_keys": sorted(str(key) for key in sanitized.keys()),
    }
    return sanitized, summary
