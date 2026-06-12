"""Convert an RL-Games resume checkpoint into a policy-initialization checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch

from checkpoint_init import sanitize_rlgames_checkpoint_for_initialization


def _json_safe(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return value.detach().cpu().item()
        return {"type": "tensor", "shape": list(value.shape), "dtype": str(value.dtype)}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _load_checkpoint(path: str) -> dict[str, Any]:
    try:
        state = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        state = torch.load(path, map_location="cpu")
    if not isinstance(state, dict):
        raise RuntimeError(f"Expected dict checkpoint, got {type(state).__name__}")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input RL-Games checkpoint path.")
    parser.add_argument("--output", required=True, help="Output policy-initialization checkpoint path.")
    parser.add_argument("--summary", default=None, help="Optional JSON summary path.")
    parser.add_argument("--strip_optimizer", action="store_true", help="Also remove optimizer/scheduler state.")
    args = parser.parse_args()

    input_path = str(Path(args.input).expanduser())
    output_path = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser() if args.summary else output_path.with_suffix(".sanitize_summary.json")

    state = _load_checkpoint(input_path)
    sanitized, summary = sanitize_rlgames_checkpoint_for_initialization(
        state,
        source_checkpoint=input_path,
        metadata={"note": "Standalone conversion to policy-initialization checkpoint."},
        strip_optimizer=bool(args.strip_optimizer),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(sanitized, output_path)
    summary_path.write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(_json_safe({"output": str(output_path), "summary": str(summary_path), **summary}), sort_keys=True))


if __name__ == "__main__":
    main()
