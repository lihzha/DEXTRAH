from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "cluster" / "submit_yam_controller_native_replacements_l401.py"
SPEC = importlib.util.spec_from_file_location("yam_replacement_submitter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _manifest(path: Path, count: int = 3) -> None:
    rows = [{"num_steps": 10 + index, "path": f"/source/{index}"} for index in range(count)]
    path.write_text(
        json.dumps(
            {
                "num_shards": count,
                "num_steps": sum(row["num_steps"] for row in rows),
                "replacement_provenance": [],
                "shards": rows,
            }
        ),
        encoding="utf-8",
    )


def test_submission_parsers(tmp_path: Path) -> None:
    recoveries = tmp_path / "recoveries.tsv"
    recoveries.write_text(
        "timestamp\tjob\tsource\n"
        "t0\t100\t103\n"
        "t1\t101\t103\n",
        encoding="utf-8",
    )
    assert MODULE._read_recovery_submissions(recoveries)[103].job_id == "101"

    replacements = tmp_path / "replacements.tsv"
    replacements.write_text(
        "timestamp\tjob\tcandidate\texcluded\tdonor\n"
        "t2\t200\t523\t103\t9\n",
        encoding="utf-8",
    )
    parsed = MODULE._read_replacement_submissions(replacements)
    assert parsed == [MODULE.ReplacementSubmission("200", 523, 103, 9)]


def test_append_manifest_records_one_for_one_provenance(tmp_path: Path) -> None:
    source = tmp_path / "replacement_source_manifest_3.json"
    _manifest(source)
    payload = json.loads(source.read_text(encoding="utf-8"))

    output, candidate = MODULE._append_replacement_manifest(
        source,
        payload,
        donor_source_index=1,
        excluded_source_index=114,
    )

    assert output.name == "replacement_source_manifest_4.json"
    assert candidate == 3
    updated = json.loads(output.read_text(encoding="utf-8"))
    assert updated["num_shards"] == 4
    assert updated["num_steps"] == 44
    assert updated["shards"][3]["path"] == "/source/1"
    assert updated["shards"][3]["replacement_for_source_index"] == 114
    assert updated["replacement_provenance"][-1]["new_source_index"] == 3


def test_latest_manifest_uses_numeric_suffix(tmp_path: Path) -> None:
    _manifest(tmp_path / "replacement_source_manifest_3.json", count=3)
    _manifest(tmp_path / "replacement_source_manifest_12.json", count=12)

    path, payload = MODULE._latest_manifest(tmp_path)

    assert path.name == "replacement_source_manifest_12.json"
    assert len(payload["shards"]) == 12
