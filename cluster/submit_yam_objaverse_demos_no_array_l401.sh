#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
BATCH_NAME="${BATCH_NAME:-yam_selected50_multidemo_$(date -u +%Y%m%dT%H%M%SZ)}"
BATCH_DIR="${BATCH_DIR:-$RESULTS_NFS/yam_demos/$BATCH_NAME}"
TOTAL_TARGET="${TOTAL_TARGET:-500}"
SHARD_COUNT="${SHARD_COUNT:-10}"
MAX_CONCURRENT="${MAX_CONCURRENT:-4}"
START_SEED="${START_SEED:-1500000}"
SELECTED_OBJECTS_JSONL="${SELECTED_OBJECTS_JSONL:-$BATCH_DIR/selected_common_50_no_overlay_manifest.jsonl}"
POOL_MANIFEST="${POOL_MANIFEST:-$BATCH_DIR/yam_selected_common50_pool_manifest.json}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yam_sel50_demo}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_collect_yam_objaverse_demos_1gpu.sh}"

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
if [ ! -f "$SELECTED_OBJECTS_JSONL" ]; then
  echo "Missing selected objects JSONL: $SELECTED_OBJECTS_JSONL" >&2
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
    "total_target": int("$TOTAL_TARGET"),
    "shard_count": int("$SHARD_COUNT"),
    "max_concurrent": int("$MAX_CONCURRENT"),
    "start_seed": int("$START_SEED"),
    "selected_objects_jsonl": "$SELECTED_OBJECTS_JSONL",
    "pool_manifest": "$POOL_MANIFEST",
    "wrapper": "$WRAPPER",
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
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",BATCH_NAME="$BATCH_NAME",BATCH_DIR="$BATCH_DIR",TOTAL_TARGET="$TOTAL_TARGET",SHARD_COUNT="$SHARD_COUNT",SHARD_INDEX="$shard_index",SHARD_TARGET="$shard_target",START_SEED="$START_SEED",SELECTED_OBJECTS_JSONL="$SELECTED_OBJECTS_JSONL",POOL_MANIFEST="$POOL_MANIFEST" \
      "$WRAPPER"
  )"
  echo "$job_id shard=$shard_index target=$shard_target name=$job_name" | tee -a "$submitted"
done

echo "submitted_jobs=$submitted"
echo "batch_dir=$BATCH_DIR"
