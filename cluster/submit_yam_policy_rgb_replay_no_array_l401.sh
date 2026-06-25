#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ACCEPTED_JSONL="${ACCEPTED_JSONL:?Set ACCEPTED_JSONL to an accepted_demos.jsonl generated on A100.}"
RGB_BATCH_NAME="${RGB_BATCH_NAME:-yam_policy_rgb_$(date -u +%Y%m%dT%H%M%SZ)}"
RGB_BATCH_DIR="${RGB_BATCH_DIR:-$RESULTS_NFS/yam_policy_rgb_replays/$RGB_BATCH_NAME}"
SHARD_COUNT="${SHARD_COUNT:-8}"
MAX_CONCURRENT="${MAX_CONCURRENT:-4}"
MAX_ROWS="${MAX_ROWS:-0}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yam_policy_rgb}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_replay_yam_policy_rgb_l40_1gpu.sh}"
RENDER_WIDTH="${RENDER_WIDTH:-1024}"
RENDER_HEIGHT="${RENDER_HEIGHT:-1024}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
RECORD_RGB_WIDTH="${RECORD_RGB_WIDTH:-256}"
RECORD_RGB_HEIGHT="${RECORD_RGB_HEIGHT:-256}"
RECORD_RGB_INTERVAL="${RECORD_RGB_INTERVAL:-1}"
YAM_POLICY_TABLE_TEXTURE_DIR="${YAM_POLICY_TABLE_TEXTURE_DIR:-$CODE_NFS/dextrah_lab/assets/textures/tabletop_wood_polyhaven}"
YAM_POLICY_TABLE_TEXTURE_TILING_RANGE="${YAM_POLICY_TABLE_TEXTURE_TILING_RANGE:-1.4 3.8}"
YAM_POLICY_BACKGROUND_TEXTURE_DIR="${YAM_POLICY_BACKGROUND_TEXTURE_DIR:-/home/lzha/code/RoboLab/assets/backgrounds/indoors}"
YAM_POLICY_BACKGROUND_TEXTURE_TILING_RANGE="${YAM_POLICY_BACKGROUND_TEXTURE_TILING_RANGE:-1.0 2.2}"
YAM_POLICY_DOME_LIGHT_TEXTURE_DIR="${YAM_POLICY_DOME_LIGHT_TEXTURE_DIR:-/home/lzha/code/RoboLab/assets/backgrounds/indoors}"
CAMERA_EYE="${CAMERA_EYE:-}"
CAMERA_TARGET="${CAMERA_TARGET:-}"
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
if [ ! -f "$ACCEPTED_JSONL" ]; then
  echo "Missing ACCEPTED_JSONL: $ACCEPTED_JSONL" >&2
  exit 2
fi
if [ ! -f "$WRAPPER" ]; then
  echo "Missing wrapper: $WRAPPER" >&2
  exit 2
fi

mkdir -p "$RGB_BATCH_DIR" "$LOG_DIR"
submitted="$RGB_BATCH_DIR/submitted_no_array_jobs.txt"
run_record="$RGB_BATCH_DIR/no_array_submitter_config.json"
: > "$submitted"

python3 - "$run_record" <<PY
import json
from pathlib import Path

payload = {
    "accepted_jsonl": "$ACCEPTED_JSONL",
    "code_commit": "$CODE_COMMIT",
    "code_nfs": "$CODE_NFS",
    "rgb_batch_name": "$RGB_BATCH_NAME",
    "rgb_batch_dir": "$RGB_BATCH_DIR",
    "shard_count": int("$SHARD_COUNT"),
    "max_concurrent": int("$MAX_CONCURRENT"),
    "max_rows_per_shard": int("$MAX_ROWS"),
    "wrapper": "$WRAPPER",
    "rendering_mode": "$RENDERING_MODE",
    "render_resolution": [int("$RENDER_WIDTH"), int("$RENDER_HEIGHT")],
    "image_resolution": [int("$RECORD_RGB_WIDTH"), int("$RECORD_RGB_HEIGHT")],
    "record_rgb_interval": int("$RECORD_RGB_INTERVAL"),
    "table_texture_dir": "$YAM_POLICY_TABLE_TEXTURE_DIR",
    "table_texture_tiling_range": "$YAM_POLICY_TABLE_TEXTURE_TILING_RANGE",
    "background_texture_dir": "$YAM_POLICY_BACKGROUND_TEXTURE_DIR",
    "background_texture_tiling_range": "$YAM_POLICY_BACKGROUND_TEXTURE_TILING_RANGE",
    "dome_light_texture_dir": "$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR",
    "camera_eye": "$CAMERA_EYE" or None,
    "camera_target": "$CAMERA_TARGET" or None,
}
Path("$run_record").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "rgb_submitter_config_written", "path": "$run_record"}))
PY

active_jobs() {
  squeue -h -u "${USER:-lzha}" -t PENDING,RUNNING,CONFIGURING,COMPLETING -o "%j" \
    | grep -c "^${JOB_NAME_PREFIX}" || true
}

for shard_index in $(seq 0 "$((SHARD_COUNT - 1))"); do
  while [ "$(active_jobs)" -ge "$MAX_CONCURRENT" ]; do
    sleep 20
  done
  job_name="${JOB_NAME_PREFIX}_s$(printf '%03d' "$shard_index")"
  job_id="$(
    sbatch --parsable \
      --job-name="$job_name" \
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",ACCEPTED_JSONL="$ACCEPTED_JSONL",RGB_BATCH_NAME="$RGB_BATCH_NAME",RGB_BATCH_DIR="$RGB_BATCH_DIR",SHARD_COUNT="$SHARD_COUNT",SHARD_INDEX="$shard_index",MAX_ROWS="$MAX_ROWS",RENDER_WIDTH="$RENDER_WIDTH",RENDER_HEIGHT="$RENDER_HEIGHT",RENDERING_MODE="$RENDERING_MODE",RECORD_RGB_WIDTH="$RECORD_RGB_WIDTH",RECORD_RGB_HEIGHT="$RECORD_RGB_HEIGHT",RECORD_RGB_INTERVAL="$RECORD_RGB_INTERVAL",YAM_POLICY_TABLE_TEXTURE_DIR="$YAM_POLICY_TABLE_TEXTURE_DIR",YAM_POLICY_TABLE_TEXTURE_TILING_RANGE="$YAM_POLICY_TABLE_TEXTURE_TILING_RANGE",YAM_POLICY_BACKGROUND_TEXTURE_DIR="$YAM_POLICY_BACKGROUND_TEXTURE_DIR",YAM_POLICY_BACKGROUND_TEXTURE_TILING_RANGE="$YAM_POLICY_BACKGROUND_TEXTURE_TILING_RANGE",YAM_POLICY_DOME_LIGHT_TEXTURE_DIR="$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR",CAMERA_EYE="$CAMERA_EYE",CAMERA_TARGET="$CAMERA_TARGET",CODE_COMMIT="$CODE_COMMIT" \
      "$WRAPPER"
  )"
  echo "$job_id shard=$shard_index name=$job_name" | tee -a "$submitted"
done

echo "submitted_jobs=$submitted"
echo "rgb_batch_dir=$RGB_BATCH_DIR"
