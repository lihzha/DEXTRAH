#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
BATCH_NAME="${BATCH_NAME:-yam_single_object_policy_500_$(date -u +%Y%m%dT%H%M%SZ)}"
BATCH_DIR="${BATCH_DIR:-$RESULTS_NFS/yam_demos/$BATCH_NAME}"
TOTAL_TARGET="${TOTAL_TARGET:-500}"
SHARD_COUNT="${SHARD_COUNT:-10}"
MAX_CONCURRENT="${MAX_CONCURRENT:-4}"
START_SEED="${START_SEED:-2400000}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yam_policy_demo}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_collect_yam_single_object_policy_demos_1gpu.sh}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

if [ "$SHARD_COUNT" -lt 1 ]; then
  echo "SHARD_COUNT must be >= 1" >&2
  exit 2
fi
if [ "$MAX_CONCURRENT" -lt 1 ]; then
  echo "MAX_CONCURRENT must be >= 1" >&2
  exit 2
fi
if [ ! -f "$WRAPPER" ]; then
  echo "Missing wrapper: $WRAPPER" >&2
  exit 2
fi

mkdir -p "$BATCH_DIR" "$LOG_DIR"
submitted="$BATCH_DIR/submitted_no_array_jobs.txt"
run_record="$BATCH_DIR/no_array_submitter_config.json"
: > "$submitted"

python3 - "$run_record" <<PY
import json
from pathlib import Path

payload = {
    "batch_name": "$BATCH_NAME",
    "batch_dir": "$BATCH_DIR",
    "code_nfs": "$CODE_NFS",
    "code_commit": "$CODE_COMMIT",
    "total_target": int("$TOTAL_TARGET"),
    "shard_count": int("$SHARD_COUNT"),
    "max_concurrent": int("$MAX_CONCURRENT"),
    "start_seed": int("$START_SEED"),
    "wrapper": "$WRAPPER",
    "axis_convention": {
        "x": "YAM forward/back",
        "y": "long table axis; object on robot-right negative Y; bin on robot-left positive Y",
    },
}
Path("$run_record").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "submitter_config_written", "path": "$run_record"}))
PY

active_jobs() {
  squeue -h -u "${USER:-lzha}" -t PENDING,RUNNING,CONFIGURING,COMPLETING -o "%j" \
    | grep -c "^${JOB_NAME_PREFIX}" || true
}

for shard_index in $(seq 0 "$((SHARD_COUNT - 1))"); do
  while [ "$(active_jobs)" -ge "$MAX_CONCURRENT" ]; do
    sleep 20
  done
  shard_target="$(( (TOTAL_TARGET + SHARD_COUNT - 1 - shard_index) / SHARD_COUNT ))"
  job_name="${JOB_NAME_PREFIX}_s$(printf '%03d' "$shard_index")"
  job_id="$(
    sbatch --parsable \
      --job-name="$job_name" \
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",BATCH_NAME="$BATCH_NAME",BATCH_DIR="$BATCH_DIR",TOTAL_TARGET="$TOTAL_TARGET",SHARD_COUNT="$SHARD_COUNT",SHARD_INDEX="$shard_index",SHARD_TARGET="$shard_target",START_SEED="$START_SEED",CODE_COMMIT="$CODE_COMMIT" \
      "$WRAPPER"
  )"
  echo "$job_id shard=$shard_index target=$shard_target name=$job_name" | tee -a "$submitted"
done

echo "submitted_jobs=$submitted"
echo "batch_dir=$BATCH_DIR"
