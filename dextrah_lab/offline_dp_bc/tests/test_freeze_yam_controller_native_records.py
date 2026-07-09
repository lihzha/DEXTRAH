from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dextrah_lab.offline_dp_bc.freeze_yam_controller_native_records import freeze_records


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _record(records_root: Path, source_index: int, target_uuid: str, source_policy_shard: str) -> None:
    padded = f"{source_index:06d}"
    _write_json(
        records_root
        / f"source_{padded}"
        / "policy_dataset"
        / f"yam_rgb_policy_{padded}"
        / "metadata.json",
        {
            "target_uuid": target_uuid,
            "source_policy_shard": source_policy_shard,
        },
    )


class FreezeYamControllerNativeRecordsTest(unittest.TestCase):
    def test_prefers_original_and_maximizes_replacement_object_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.json"
            replacement = root / "replacement.json"
            records = root / "records"
            output = root / "frozen"
            _write_json(base, {"shards": [{}, {}, {}]})
            _write_json(
                replacement,
                {
                    "shards": [{}, {}, {}, {}, {}, {}],
                    "replacement_provenance": [
                        {"new_source_index": 3, "excluded_source_index": 1},
                        {"new_source_index": 4, "excluded_source_index": 1},
                        {"new_source_index": 5, "excluded_source_index": 2},
                    ],
                },
            )
            _record(records, 0, "object-a", "policy-a")
            _record(records, 3, "object-c", "policy-c")
            _record(records, 4, "object-d", "policy-d")
            _record(records, 5, "object-c", "policy-c")

            report = freeze_records(
                records_root=records,
                base_source_manifest=base,
                replacement_source_manifest=replacement,
                output_dir=output,
            )

            selected = {row["original_slot"]: row for row in report["rows"]}
            self.assertEqual(selected[0]["selected_source_index"], 0)
            self.assertEqual(selected[1]["selected_source_index"], 4)
            self.assertEqual(selected[2]["selected_source_index"], 5)
            self.assertEqual(report["selected_original_count"], 1)
            self.assertEqual(report["selected_replacement_count"], 2)
            self.assertEqual(report["unique_target_uuid_count"], 3)
            self.assertEqual(len(list((output / "records").iterdir())), 3)
            self.assertTrue((output / "records" / "source_000004").is_symlink())

    def test_rejects_incomplete_original_slot_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.json"
            replacement = root / "replacement.json"
            records = root / "records"
            _write_json(base, {"shards": [{}, {}]})
            _write_json(replacement, {"shards": [{}, {}], "replacement_provenance": []})
            _record(records, 0, "object-a", "policy-a")

            with self.assertRaisesRegex(ValueError, "No accepted record for 1 original slots"):
                freeze_records(
                    records_root=records,
                    base_source_manifest=base,
                    replacement_source_manifest=replacement,
                    output_dir=root / "frozen",
                )


if __name__ == "__main__":
    unittest.main()
