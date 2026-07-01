import unittest

from dextrah_lab.offline_dp_bc.exact_visual_replay import select_exact_visual_asset


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


if __name__ == "__main__":
    unittest.main()
