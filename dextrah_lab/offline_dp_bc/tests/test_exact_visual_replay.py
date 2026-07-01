import unittest

from dextrah_lab.offline_dp_bc.exact_visual_replay import (
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


if __name__ == "__main__":
    unittest.main()
