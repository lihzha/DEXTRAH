import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from dextrah_lab.offline_dp_bc.build_yam_controller_native_curriculum import _validate_shard


V13_ACCEPTANCE_MODE = "final_physical_success_plus_dynamics_replay"


def _write_shard(
    root: Path,
    *,
    controller_version: int,
    descent_started: bool,
    controller_path: str | None,
) -> Path:
    shard = root / "source_000005" / "policy_dataset" / "yam_rgb_policy_000005"
    shard.mkdir(parents=True)
    num_steps = 3
    rgb = np.full((num_steps, 8, 8, 3), 127, dtype=np.uint8)
    np.save(shard / "scene_rgb.npy", rgb, allow_pickle=False)
    np.save(shard / "wrist_rgb.npy", rgb, allow_pickle=False)
    np.save(shard / "robot_state.npy", np.zeros((num_steps, 24), dtype=np.float32), allow_pickle=False)
    np.save(shard / "action.npy", np.zeros((num_steps, 7), dtype=np.float32), allow_pickle=False)
    np.save(shard / "episode_ends.npy", np.asarray([num_steps], dtype=np.int64), allow_pickle=False)

    recording = {
        "replay_gate": {
            "enabled": True,
            "passed": True,
            "episodes": [{"final_success": True}],
        },
        "episode_success": [True],
        "episode_final_success": [True],
        "episode_drop_descent_started": [descent_started],
        "episode_drop_fallback_used": [False],
        "episode_drop_release_hold_started": [False],
        "dynamics_mode": True,
        "exact_reset": True,
        "rendering_mode": "quality",
        "initial_render_warmup_frames": 64,
        "exact_visual_resample": True,
        "robot_material_randomization": True,
        "object_material_randomization": True,
        "dataset_drop_targeting_mode": "live_object_to_bin_center",
        "dataset_drop_release_height_mode": "above_bin_top_then_contained_descent",
        "dataset_drop_controller_version": controller_version,
        "dataset_drop_release_criterion": "gripper_open_or_hand_separated",
        "recording_gate_fallback_replay_mode": "robot_pose_target_dynamics",
        "dataset_drop_spec_source": "exact_stable_scene",
        "robot_debug_site_visibility": {"hidden_count": 2},
    }
    if controller_version >= 13:
        recording["dataset_drop_acceptance_mode"] = V13_ACCEPTANCE_MODE
        recording["episode_controller_paths"] = [controller_path]
    (shard / "metadata.json").write_text(
        json.dumps(
            {
                "recording": recording,
                "target_uuid": "test-object",
                "source_dataset": "/tmp/source.npz",
                "source_policy_shard": "/tmp/source-shard",
            }
        ),
        encoding="utf-8",
    )
    return shard


class YamControllerNativeCurriculumValidationTest(unittest.TestCase):
    def test_v13_accepts_replay_gated_source_tracked_drop(self):
        with tempfile.TemporaryDirectory() as directory:
            shard = _write_shard(
                Path(directory),
                controller_version=13,
                descent_started=False,
                controller_path="source_tracked_drop",
            )

            record, reason = _validate_shard(shard)

            self.assertIsNone(reason)
            self.assertEqual(record["source_index"], 5)

    def test_v13_rejects_controller_path_inconsistent_with_descent_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            shard = _write_shard(
                Path(directory),
                controller_version=13,
                descent_started=False,
                controller_path="staged_descent",
            )

            record, reason = _validate_shard(shard)

            self.assertIsNone(record)
            self.assertEqual(reason, "recording_controller_paths_inconsistent")

    def test_v12_still_requires_staged_descent(self):
        with tempfile.TemporaryDirectory() as directory:
            shard = _write_shard(
                Path(directory),
                controller_version=12,
                descent_started=False,
                controller_path=None,
            )

            record, reason = _validate_shard(shard)

            self.assertIsNone(record)
            self.assertEqual(reason, "recording_staged_descent_not_observed")


if __name__ == "__main__":
    unittest.main()
