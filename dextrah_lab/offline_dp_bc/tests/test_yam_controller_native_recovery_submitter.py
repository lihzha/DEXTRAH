from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "cluster" / "submit_yam_controller_native_recoveries_l401.py"
SPEC = importlib.util.spec_from_file_location("yam_recovery_submitter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_normalized_state_handles_slurm_suffixes() -> None:
    assert MODULE._normalized_state("COMPLETED|\n") == "COMPLETED"
    assert MODULE._normalized_state("CANCELLED by 12345|\n") == "CANCELLED"
    assert MODULE._normalized_state("TIMEOUT+|\n") == "TIMEOUT"


def test_submission_parsers_keep_latest_main_job(tmp_path: Path) -> None:
    main = tmp_path / "main.tsv"
    main.write_text(
        "timestamp\tjob\tsource\n"
        "t0\t100\t103\n"
        "t1\t101\t104\n"
        "t2\t102\t103\n",
        encoding="utf-8",
    )
    parsed = MODULE._read_main_submissions(main)
    assert parsed[103].job_id == "102"
    assert parsed[104].job_id == "101"

    recoveries = tmp_path / "recoveries.tsv"
    recoveries.write_text(
        "timestamp_utc\tjob_id\tsource_index\tmain_job_id\tmain_state\n"
        "t3\t200\t103\t102\tFAILED\n",
        encoding="utf-8",
    )
    assert MODULE._read_recovery_sources(recoveries) == {103}


def test_accepted_marker_uses_padded_source_index(tmp_path: Path) -> None:
    assert MODULE._accepted_marker(tmp_path, 103) == (
        tmp_path
        / "records"
        / "source_000103"
        / "policy_dataset"
        / "yam_rgb_policy_000103"
        / "metadata.json"
    )


def test_absolute_path_preserves_symlink_spelling(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)

    actual = MODULE._absolute_without_resolving_symlinks(alias / "records")

    assert str(actual).startswith(str(alias))


def test_visual_retry_can_use_pose_targets(tmp_path: Path) -> None:
    args = MODULE._parser().parse_args(
        [
            "--output-root",
            str(tmp_path / "output"),
            "--source-manifest",
            str(tmp_path / "manifest.json"),
            "--code-nfs",
            str(tmp_path / "code"),
            "--code-commit",
            "abc123",
            "--control-mode",
            "dataset_pose_targets",
        ]
    )

    assert args.control_mode == "dataset_pose_targets"
