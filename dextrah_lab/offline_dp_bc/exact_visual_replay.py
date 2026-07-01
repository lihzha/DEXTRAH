"""Pure helpers for reconstructing recorded YAM visual randomization."""

from __future__ import annotations


def select_exact_visual_asset(
    *,
    recorded: object,
    sampled: object,
    replay_resampled_asset: bool = False,
) -> dict[str, str]:
    """Select the asset mode recorded by the evaluated policy shard."""
    recorded_path = str(recorded or "")
    sampled_path = str(sampled or "")
    if replay_resampled_asset and sampled_path:
        selected_path = sampled_path
        selected_source = "rng_resample"
    elif recorded_path:
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
