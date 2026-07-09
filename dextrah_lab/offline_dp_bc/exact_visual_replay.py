"""Pure helpers for reconstructing recorded YAM visual randomization."""

from __future__ import annotations

from collections.abc import Mapping


def should_replay_resampled_assets(
    *,
    visual_resample_requested: bool,
    shard_recorded_visual_resample: bool,
    recording_output_requested: bool,
) -> bool:
    """Use a fresh RNG asset only while producing another recorded shard."""
    return bool(
        visual_resample_requested
        and shard_recorded_visual_resample
        and recording_output_requested
    )


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


def authoritative_recorded_visual_asset(
    *,
    shard_metadata: Mapping[str, object],
    asset_name: str,
    fallback: object,
) -> str:
    """Return the asset that actually produced a recorded policy shard."""
    replay = shard_metadata.get("exact_visual_replay")
    if isinstance(replay, Mapping):
        paths = replay.get("paths")
        if isinstance(paths, Mapping):
            asset = paths.get(asset_name)
            if isinstance(asset, Mapping):
                selected = str(asset.get("selected") or "")
                if selected:
                    return selected
    return str(fallback or "")


def recorded_surface_texture_tiling_range(
    *,
    background_metadata: Mapping[str, object],
    ground_metadata: Mapping[str, object],
    ground_enabled: bool,
    eval_ground_fallback: object,
) -> tuple[float, float]:
    """Recover the RNG range that produced the shared background/floor draw."""
    candidates = (
        ground_metadata.get("texture_tiling_range"),
        background_metadata.get("background_texture_tiling_range"),
        eval_ground_fallback if ground_enabled else (1.0, 2.2),
    )
    for candidate in candidates:
        if isinstance(candidate, (list, tuple)) and len(candidate) == 2:
            low, high = float(candidate[0]), float(candidate[1])
            if low <= high:
                return low, high
    raise ValueError("Could not recover a valid background/floor texture tiling range")
