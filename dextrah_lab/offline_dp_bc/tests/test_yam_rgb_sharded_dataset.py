import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from dextrah_lab.offline_dp_bc.dp_dataset import YamRgbShardedDataset


def _write_manifest(tmp_path, *, num_steps=20):
    shard = tmp_path / "yam_rgb_policy_000000"
    shard.mkdir()
    frame_values = np.arange(num_steps, dtype=np.uint8)[:, None, None, None]
    images = np.broadcast_to(frame_values, (num_steps, 8, 8, 3)).copy()
    robot_state = np.arange(num_steps * 24, dtype=np.float32).reshape(num_steps, 24)
    action = np.arange(num_steps * 7, dtype=np.float32).reshape(num_steps, 7)
    np.save(shard / "scene_rgb.npy", images, allow_pickle=False)
    np.save(shard / "wrist_rgb.npy", images, allow_pickle=False)
    np.save(shard / "robot_state.npy", robot_state, allow_pickle=False)
    np.save(shard / "action.npy", action, allow_pickle=False)
    np.save(shard / "episode_ends.npy", np.asarray([num_steps], dtype=np.int64), allow_pickle=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "shards": [
                    {
                        "path": str(shard),
                        "scene_rgb_shape": list(images.shape),
                        "wrist_rgb_shape": list(images.shape),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest


class YamRgbShardedDatasetTest(unittest.TestCase):
    def test_n_obs_steps_limits_observations_but_not_action_horizon(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = _write_manifest(Path(directory))
            dataset = YamRgbShardedDataset(
                manifest_path=str(manifest),
                horizon=16,
                n_obs_steps=1,
                pad_after=15,
                image_augmentation={"enabled": False},
            )

            sample = dataset[0]

            self.assertEqual(sample["obs"]["scene_rgb"].shape, (1, 3, 8, 8))
            self.assertEqual(sample["obs"]["wrist_rgb"].shape, (1, 3, 8, 8))
            self.assertEqual(sample["obs"]["robot_state"].shape, (1, 24))
            self.assertEqual(sample["action"].shape, (16, 7))
            np.testing.assert_array_equal(
                sample["action"].numpy()[0], np.arange(7, dtype=np.float32)
            )

    def test_n_obs_steps_must_not_exceed_horizon(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = _write_manifest(Path(directory))
            with self.assertRaisesRegex(ValueError, "n_obs_steps"):
                YamRgbShardedDataset(
                    manifest_path=str(manifest),
                    horizon=16,
                    n_obs_steps=17,
                )


if __name__ == "__main__":
    unittest.main()
