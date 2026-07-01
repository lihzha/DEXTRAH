"""Pure helpers for reconstructing recorded YAM visual randomization."""

from __future__ import annotations


def select_exact_visual_asset(*, recorded: object, sampled: object) -> dict[str, str]:
    """Prefer the recorded asset while retaining the RNG sample for drift audits."""
    recorded_path = str(recorded or "")
    sampled_path = str(sampled or "")
    if recorded_path:
        selected_path = recorded_path
        selected_source = "recorded"
    elif sampled_path:
        selected_path = sampled_path
        selected_source = "sampled_fallback"
    else:
        selected_path = ""
        selected_source = "none"
    return {
        "recorded": recorded_path,
        "sampled": sampled_path,
        "selected": selected_path,
        "selected_source": selected_source,
    }
