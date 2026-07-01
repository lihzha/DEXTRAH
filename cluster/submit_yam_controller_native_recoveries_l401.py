#!/usr/bin/env python3
"""Submit one strict recovery job for each failed YAM first-pass shard."""

from __future__ import annotations

import argparse
import fcntl
import getpass
import json
import os
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


@dataclass(frozen=True)
class MainSubmission:
    job_id: str
    source_index: int


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--code-nfs", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--start-source", type=int, default=0)
    parser.add_argument("--stop-source", type=int, default=499)
    parser.add_argument("--max-concurrent", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--sbatch-time", default="00:08:00")
    parser.add_argument("--job-name-prefix", default="yv15auto")
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


def _read_main_submissions(path: Path) -> dict[int, MainSubmission]:
    submissions: dict[int, MainSubmission] = {}
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
        submissions[source_index] = MainSubmission(job_id=fields[1], source_index=source_index)
    return submissions


def _read_recovery_sources(path: Path) -> set[int]:
    sources: set[int] = set()
    if not path.is_file():
        return sources
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        try:
            sources.add(int(fields[2]))
        except ValueError:
            continue
    return sources


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


def _submit_recovery(args: argparse.Namespace, source_index: int) -> str:
    padded = f"{source_index:06d}"
    wrapper = args.code_nfs / "cluster" / "sbatch_record_yam_controller_native_shard_1gpu.sh"
    log_path = (
        Path("/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah")
        / f"record_yam_controller_native_v15auto_s{padded}_recovery_%j.out"
    )
    export = ",".join(
        [
            "ALL",
            f"CODE_NFS={args.code_nfs}",
            f"CODE_COMMIT={args.code_commit}",
            f"SOURCE_MANIFEST={args.source_manifest}",
            f"OUTPUT_ROOT={args.output_root}",
            f"SOURCE_INDEX={source_index}",
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
        print(json.dumps({"event": "dry_run_submit", "command": command, "source_index": source_index}))
        return f"dry-run-{source_index}"
    last_error = ""
    for attempt in range(1, 4):
        result = _run(command, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split(";", 1)[0]
        last_error = f"attempt={attempt} rc={result.returncode} stderr={result.stderr.strip()}"
        time.sleep(10)
    raise RuntimeError(f"sbatch failed for source {source_index}: {last_error}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    args = _parser().parse_args()
    args.output_root = args.output_root.expanduser().resolve()
    args.source_manifest = args.source_manifest.expanduser().resolve()
    args.code_nfs = args.code_nfs.expanduser().resolve()
    if args.max_concurrent < 1 or args.poll_seconds < 1:
        raise SystemExit("max-concurrent and poll-seconds must be positive")
    if not 0 <= args.start_source <= args.stop_source:
        raise SystemExit("invalid source range")
    if not args.source_manifest.is_file():
        raise SystemExit(f"missing source manifest: {args.source_manifest}")
    wrapper = args.code_nfs / "cluster" / "sbatch_record_yam_controller_native_shard_1gpu.sh"
    if not wrapper.is_file():
        raise SystemExit(f"missing recovery wrapper: {wrapper}")
    actual_commit = _run(["git", "-C", str(args.code_nfs), "rev-parse", "HEAD"]).stdout.strip()
    if actual_commit != args.code_commit:
        raise SystemExit(f"code commit mismatch: expected {args.code_commit}, got {actual_commit}")

    run_dir = args.output_root / "recovery_submitter"
    run_dir.mkdir(parents=True, exist_ok=True)
    lock_file = (run_dir / "submitter.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit(f"another recovery submitter owns {lock_file.name}") from exc

    main_tsv = args.output_root / "submitter" / "submissions.tsv"
    recovery_tsv = run_dir / "submissions.tsv"
    if not recovery_tsv.exists():
        recovery_tsv.write_text(
            "timestamp_utc\tjob_id\tsource_index\tmain_job_id\tmain_state\n",
            encoding="utf-8",
        )
    config = {
        "code_commit": args.code_commit,
        "code_nfs": str(args.code_nfs),
        "dry_run": bool(args.dry_run),
        "job_name_prefix": args.job_name_prefix,
        "main_submissions": str(main_tsv),
        "max_concurrent": args.max_concurrent,
        "output_root": str(args.output_root),
        "poll_seconds": args.poll_seconds,
        "sbatch_time": args.sbatch_time,
        "source_manifest": str(args.source_manifest),
        "source_range": [args.start_source, args.stop_source],
        "submission_mode": "ordinary_jobs_failed_first_pass_once",
    }
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    while True:
        main_submissions = _read_main_submissions(main_tsv)
        recovered_sources = _read_recovery_sources(recovery_tsv)
        candidates: list[tuple[MainSubmission, str]] = []
        for source_index, submission in sorted(main_submissions.items()):
            if not args.start_source <= source_index <= args.stop_source:
                continue
            if source_index in recovered_sources or _accepted_marker(args.output_root, source_index).is_file():
                continue
            state = _job_state(submission.job_id)
            if state in TERMINAL_STATES:
                candidates.append((submission, state))

        slots = max(0, args.max_concurrent - _active_jobs(args.user, args.job_name_prefix))
        for submission, state in candidates[:slots]:
            job_id = _submit_recovery(args, submission.source_index)
            with recovery_tsv.open("a", encoding="utf-8") as stream:
                stream.write(
                    f"{_utc_now()}\t{job_id}\t{submission.source_index}\t"
                    f"{submission.job_id}\t{state}\n"
                )
                stream.flush()
                os.fsync(stream.fileno())
            print(
                json.dumps(
                    {
                        "event": "recovery_submitted",
                        "job_id": job_id,
                        "main_job_id": submission.job_id,
                        "main_state": state,
                        "source_index": submission.source_index,
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
