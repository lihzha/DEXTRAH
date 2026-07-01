#!/usr/bin/env python3
"""Replace permanently rejected YAM sources with strict recovery trajectories."""

from __future__ import annotations

import argparse
import copy
import fcntl
import getpass
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TERMINAL_STATES = {
    "BOOT_FAIL",
    "CANCELLED",
    "COMPLETED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PREEMPTED",
    "TIMEOUT",
}
MANIFEST_PATTERN = re.compile(r"replacement_source_manifest_(\d+)\.json$")


@dataclass(frozen=True)
class RecoverySubmission:
    job_id: str
    source_index: int


@dataclass(frozen=True)
class ReplacementSubmission:
    job_id: str
    candidate_index: int
    excluded_source_index: int
    donor_source_index: int


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--code-nfs", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--donor-sources", default="0,2,3,7,9,10")
    parser.add_argument("--start-source", type=int, default=0)
    parser.add_argument("--stop-source", type=int, default=499)
    parser.add_argument("--max-concurrent", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--sbatch-time", default="00:08:00")
    parser.add_argument("--job-name-prefix", default="yv15rep")
    parser.add_argument("--user", default=getpass.getuser())
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def _normalized_state(raw_state: str) -> str:
    return raw_state.strip().split("|", 1)[0].split("+", 1)[0].split(" ", 1)[0]


def _job_state(job_id: str) -> str:
    result = _run(
        ["sacct", "-n", "-X", "-j", job_id, "--format=State", "-P"],
        check=False,
    )
    if result.returncode != 0:
        return ""
    for line in result.stdout.splitlines():
        state = _normalized_state(line)
        if state:
            return state
    return ""


def _active_jobs(user: str, prefix: str) -> int:
    result = _run(
        [
            "squeue",
            "-h",
            "-u",
            user,
            "-t",
            "PENDING,RUNNING,CONFIGURING,COMPLETING",
            "-o",
            "%j",
        ],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"squeue failed: {result.stderr.strip()}")
    marker = f"{prefix}_s"
    return sum(line.strip().startswith(marker) for line in result.stdout.splitlines())


def _read_recovery_submissions(path: Path) -> dict[int, RecoverySubmission]:
    submissions: dict[int, RecoverySubmission] = {}
    if not path.is_file():
        return submissions
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        try:
            source_index = int(fields[2])
        except ValueError:
            continue
        submissions[source_index] = RecoverySubmission(fields[1], source_index)
    return submissions


def _read_replacement_submissions(path: Path) -> list[ReplacementSubmission]:
    submissions: list[ReplacementSubmission] = []
    if not path.is_file():
        return submissions
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 5:
            continue
        try:
            submissions.append(
                ReplacementSubmission(
                    job_id=fields[1],
                    candidate_index=int(fields[2]),
                    excluded_source_index=int(fields[3]),
                    donor_source_index=int(fields[4]),
                )
            )
        except ValueError:
            continue
    return submissions


def _accepted_marker(output_root: Path, source_index: int) -> Path:
    padded = f"{source_index:06d}"
    return (
        output_root
        / "records"
        / f"source_{padded}"
        / "policy_dataset"
        / f"yam_rgb_policy_{padded}"
        / "metadata.json"
    )


def _latest_manifest(output_root: Path) -> tuple[Path, dict[str, object]]:
    candidates: list[tuple[int, Path]] = []
    for path in output_root.glob("replacement_source_manifest_*.json"):
        match = MANIFEST_PATTERN.search(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise RuntimeError(f"No replacement source manifest under {output_root}")
    suffix, path = max(candidates)
    payload = json.loads(path.read_text(encoding="utf-8"))
    shards = payload.get("shards")
    if not isinstance(shards, list) or len(shards) != suffix:
        raise RuntimeError(f"Manifest suffix/row mismatch for {path}: suffix={suffix}")
    return path, payload


def _replacement_candidates(payload: dict[str, object], excluded_source_index: int) -> list[int]:
    provenance = payload.get("replacement_provenance")
    if not isinstance(provenance, list):
        return []
    return [
        int(row["new_source_index"])
        for row in provenance
        if isinstance(row, dict)
        and int(row.get("excluded_source_index", -1)) == excluded_source_index
    ]


def _append_replacement_manifest(
    source_path: Path,
    payload: dict[str, object],
    *,
    donor_source_index: int,
    excluded_source_index: int,
) -> tuple[Path, int]:
    shards = payload.get("shards")
    if not isinstance(shards, list):
        raise RuntimeError(f"Missing shards in {source_path}")
    candidate_index = len(shards)
    if not 0 <= donor_source_index < candidate_index:
        raise RuntimeError(f"Invalid donor source {donor_source_index} for {source_path}")
    output_path = source_path.with_name(f"replacement_source_manifest_{candidate_index + 1}.json")
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite {output_path}")

    updated = copy.deepcopy(payload)
    updated_shards = updated["shards"]
    assert isinstance(updated_shards, list)
    row = copy.deepcopy(updated_shards[donor_source_index])
    if not isinstance(row, dict):
        raise RuntimeError(f"Donor row {donor_source_index} is not an object")
    row.update(
        {
            "replacement_for_source_index": excluded_source_index,
            "replacement_kind": "post_perturbation_teacher_recovery",
            "replacement_output_index": candidate_index,
            "replacement_source_index": donor_source_index,
        }
    )
    updated_shards.append(row)
    updated["num_shards"] = len(updated_shards)
    updated["num_steps"] = sum(int(item["num_steps"]) for item in updated_shards)
    provenance = updated.setdefault("replacement_provenance", [])
    if not isinstance(provenance, list):
        raise RuntimeError(f"Invalid replacement provenance in {source_path}")
    provenance.append(
        {
            "excluded_source_index": excluded_source_index,
            "new_source_index": candidate_index,
            "reason": (
                f"automated candidate from recovery-qualified source {donor_source_index} "
                "after nominal and recovery rejection"
            ),
            "source_index": donor_source_index,
        }
    )
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    return output_path, candidate_index


def _submit_replacement(
    args: argparse.Namespace,
    *,
    manifest: Path,
    candidate_index: int,
) -> str:
    padded = f"{candidate_index:06d}"
    wrapper = args.code_nfs / "cluster" / "sbatch_record_yam_controller_native_shard_1gpu.sh"
    log_path = (
        Path("/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah")
        / f"record_yam_controller_native_v15rep_s{padded}_recovery_%j.out"
    )
    export = ",".join(
        [
            "ALL",
            f"CODE_NFS={args.code_nfs}",
            f"CODE_COMMIT={args.code_commit}",
            f"SOURCE_MANIFEST={manifest}",
            f"OUTPUT_ROOT={args.output_root}",
            f"SOURCE_INDEX={candidate_index}",
            "CONTROL_MODE=dataset_pose_recovery",
            "DATASET_MAX_EXTRA_STEPS=768",
            "DATASET_POST_ACTION_SETTLE_STEPS=30",
            "INITIAL_RENDER_WARMUP_FRAMES=64",
            "CAPTURE_VIDEO=False",
            "PRINT_INTERVAL=100",
        ]
    )
    command = [
        "sbatch",
        "--parsable",
        f"--job-name={args.job_name_prefix}_s{padded}",
        f"--time={args.sbatch_time}",
        f"--output={log_path}",
        f"--export={export}",
        str(wrapper),
    ]
    if args.dry_run:
        print(json.dumps({"event": "dry_run_submit", "command": command}, sort_keys=True))
        return f"dry-run-{candidate_index}"
    last_error = ""
    for attempt in range(1, 4):
        result = _run(command, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split(";", 1)[0]
        last_error = f"attempt={attempt} rc={result.returncode} stderr={result.stderr.strip()}"
        time.sleep(10)
    raise RuntimeError(f"sbatch failed for replacement {candidate_index}: {last_error}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    args = _parser().parse_args()
    args.output_root = args.output_root.expanduser().resolve()
    args.code_nfs = args.code_nfs.expanduser().resolve()
    donor_sources = [int(value) for value in args.donor_sources.split(",") if value.strip()]
    if not donor_sources:
        raise SystemExit("donor-sources must not be empty")
    if args.max_concurrent < 1 or args.poll_seconds < 1:
        raise SystemExit("max-concurrent and poll-seconds must be positive")
    if not 0 <= args.start_source <= args.stop_source:
        raise SystemExit("invalid source range")
    actual_commit = _run(["git", "-C", str(args.code_nfs), "rev-parse", "HEAD"]).stdout.strip()
    if actual_commit != args.code_commit:
        raise SystemExit(f"code commit mismatch: expected {args.code_commit}, got {actual_commit}")

    run_dir = args.output_root / "replacement_submitter"
    run_dir.mkdir(parents=True, exist_ok=True)
    lock_file = (run_dir / "submitter.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit(f"another replacement submitter owns {lock_file.name}") from exc

    recovery_tsv = args.output_root / "recovery_submitter" / "submissions.tsv"
    replacement_tsv = args.output_root / "replacement_submissions.tsv"
    if not replacement_tsv.exists():
        replacement_tsv.write_text(
            "timestamp_utc\tjob_id\tsource_index\texcluded_source_index\t"
            "donor_source_index\tmanifest\tcode_commit\n",
            encoding="utf-8",
        )
    config = {
        "code_commit": args.code_commit,
        "code_nfs": str(args.code_nfs),
        "donor_sources": donor_sources,
        "dry_run": bool(args.dry_run),
        "job_name_prefix": args.job_name_prefix,
        "max_concurrent": args.max_concurrent,
        "output_root": str(args.output_root),
        "poll_seconds": args.poll_seconds,
        "recovery_submissions": str(recovery_tsv),
        "replacement_submissions": str(replacement_tsv),
        "sbatch_time": args.sbatch_time,
        "source_range": [args.start_source, args.stop_source],
        "submission_mode": "ordinary_jobs_one_for_one_after_failed_strict_recovery",
    }
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    while True:
        _, payload = _latest_manifest(args.output_root)
        recoveries = _read_recovery_submissions(recovery_tsv)
        replacement_submissions = _read_replacement_submissions(replacement_tsv)
        latest_by_excluded = {
            row.excluded_source_index: row for row in replacement_submissions
        }
        eligible: list[int] = []
        for source_index, recovery in sorted(recoveries.items()):
            if not args.start_source <= source_index <= args.stop_source:
                continue
            if _accepted_marker(args.output_root, source_index).is_file():
                continue
            recovery_state = _job_state(recovery.job_id)
            if recovery_state not in TERMINAL_STATES:
                continue
            candidates = _replacement_candidates(payload, source_index)
            if any(_accepted_marker(args.output_root, index).is_file() for index in candidates):
                continue
            latest = latest_by_excluded.get(source_index)
            if latest is not None and _job_state(latest.job_id) not in TERMINAL_STATES:
                continue
            eligible.append(source_index)

        slots = max(0, args.max_concurrent - _active_jobs(args.user, args.job_name_prefix))
        for excluded_source_index in eligible[:slots]:
            source_path, current_payload = _latest_manifest(args.output_root)
            candidate_index = len(current_payload["shards"])
            donor_source_index = donor_sources[candidate_index % len(donor_sources)]
            if args.dry_run:
                manifest = source_path.with_name(
                    f"replacement_source_manifest_{candidate_index + 1}.json"
                )
            else:
                manifest, candidate_index = _append_replacement_manifest(
                    source_path,
                    current_payload,
                    donor_source_index=donor_source_index,
                    excluded_source_index=excluded_source_index,
                )
            job_id = _submit_replacement(
                args,
                manifest=manifest,
                candidate_index=candidate_index,
            )
            if not args.dry_run:
                with replacement_tsv.open("a", encoding="utf-8") as stream:
                    stream.write(
                        f"{_utc_now()}\t{job_id}\t{candidate_index}\t"
                        f"{excluded_source_index}\t{donor_source_index}\t{manifest}\t"
                        f"{args.code_commit}\n"
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
            print(
                json.dumps(
                    {
                        "candidate_index": candidate_index,
                        "donor_source_index": donor_source_index,
                        "event": "replacement_submitted",
                        "excluded_source_index": excluded_source_index,
                        "job_id": job_id,
                        "manifest": str(manifest),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
