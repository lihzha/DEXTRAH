import unittest

from dextrah_lab.offline_dp_bc.exact_visual_replay import (
    authoritative_recorded_visual_asset,
    authoritative_recorded_visual_value,
    recorded_surface_texture_tiling_range,
    select_exact_visual_asset,
    should_replay_resampled_assets,
)


class ExactVisualReplayTest(unittest.TestCase):
    def test_recorded_asset_wins_when_candidate_pool_drifts(self):
        selection = select_exact_visual_asset(
            recorded="/code/textures/recorded.jpg",
            sampled="/assets/textures/new-pool-choice.jpg",
        )

        self.assertEqual(selection["selected"], "/code/textures/recorded.jpg")
        self.assertEqual(selection["selected_source"], "recorded")

    def test_sampled_asset_is_only_a_missing_metadata_fallback(self):
        selection = select_exact_visual_asset(recorded="", sampled="/assets/fallback.hdr")

        self.assertEqual(selection["selected"], "/assets/fallback.hdr")
        self.assertEqual(selection["selected_source"], "sampled_fallback")

    def test_resampled_recording_replays_rng_asset(self):
        selection = select_exact_visual_asset(
            recorded="/code/textures/source.jpg",
            sampled="/assets/textures/controller-recording.jpg",
            replay_resampled_asset=True,
        )

        self.assertEqual(selection["selected"], "/assets/textures/controller-recording.jpg")
        self.assertEqual(selection["selected_source"], "rng_resample")

    def test_exact_policy_eval_restores_recorded_asset(self):
        self.assertFalse(
            should_replay_resampled_assets(
                visual_resample_requested=True,
                shard_recorded_visual_resample=True,
                recording_output_requested=False,
            )
        )

    def test_nested_recording_can_resample_a_resampled_source(self):
        self.assertTrue(
            should_replay_resampled_assets(
                visual_resample_requested=True,
                shard_recorded_visual_resample=True,
                recording_output_requested=True,
            )
        )

    def test_disabled_visual_resampling_uses_recorded_asset(self):
        self.assertFalse(
            should_replay_resampled_assets(
                visual_resample_requested=False,
                shard_recorded_visual_resample=True,
                recording_output_requested=True,
            )
        )

    def test_nested_recording_selected_asset_becomes_authoritative(self):
        selected = authoritative_recorded_visual_asset(
            shard_metadata={
                "exact_visual_replay": {
                    "paths": {
                        "table_texture": {
                            "recorded": "/textures/source.jpg",
                            "sampled": "/textures/resampled.jpg",
                            "selected": "/textures/resampled.jpg",
                        }
                    }
                }
            },
            asset_name="table_texture",
            fallback="/textures/source.jpg",
        )

        self.assertEqual(selected, "/textures/resampled.jpg")

    def test_legacy_shard_uses_source_metadata_asset(self):
        selected = authoritative_recorded_visual_asset(
            shard_metadata={},
            asset_name="dome_texture",
            fallback="/textures/source.hdr",
        )

        self.assertEqual(selected, "/textures/source.hdr")

    def test_nested_recording_restores_ground_values(self):
        shard_metadata = {
            "exact_visual_replay": {
                "ground_texture_enabled": True,
                "ground_texture_size": [20.0, 20.0],
                "background_texture_tiling": 3.25,
            }
        }

        self.assertTrue(
            authoritative_recorded_visual_value(
                shard_metadata=shard_metadata,
                key="ground_texture_enabled",
                fallback=False,
            )
        )
        self.assertEqual(
            authoritative_recorded_visual_value(
                shard_metadata=shard_metadata,
                key="background_texture_tiling",
                fallback=1.5,
            ),
            3.25,
        )

    def test_legacy_ground_value_uses_source_fallback(self):
        value = authoritative_recorded_visual_value(
            shard_metadata={},
            key="ground_texture_enabled",
            fallback=False,
        )

        self.assertFalse(value)

    def test_ground_tiling_uses_recorded_ground_range(self):
        value = recorded_surface_texture_tiling_range(
            background_metadata={"background_texture_tiling_range": [1.0, 2.2]},
            ground_metadata={"texture_tiling_range": [2.0, 5.0]},
            ground_enabled=True,
            eval_ground_fallback=(3.0, 4.0),
        )

        self.assertEqual(value, (2.0, 5.0))

    def test_early_ground_shard_uses_eval_ground_range(self):
        value = recorded_surface_texture_tiling_range(
            background_metadata={},
            ground_metadata={},
            ground_enabled=True,
            eval_ground_fallback=(2.0, 5.0),
        )

        self.assertEqual(value, (2.0, 5.0))

    def test_legacy_background_uses_original_range(self):
        value = recorded_surface_texture_tiling_range(
            background_metadata={},
            ground_metadata={},
            ground_enabled=False,
            eval_ground_fallback=(2.0, 5.0),
        )

        self.assertEqual(value, (1.0, 2.2))


if __name__ == "__main__":
    unittest.main()
