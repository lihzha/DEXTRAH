#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_record_yam_controller_native_shard_1gpu.sh}"

SOURCE_MANIFEST="${SOURCE_MANIFEST:?Set SOURCE_MANIFEST to the original 500-shard manifest.}"
DATASET_RUN_NAME="${DATASET_RUN_NAME:-yam_controller_native_v2_$(date -u +%Y%m%dT%H%M%SZ)}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$RESULTS_NFS/dp_bc/yam_pickplace_rgb_policy/$DATASET_RUN_NAME}"
INDEX_SPEC="${INDEX_SPEC:-0-499}"
MAX_CONCURRENT="${MAX_CONCURRENT:-3}"
CODE_COMMIT="${CODE_COMMIT:-}"
VIDEO_EVERY="${VIDEO_EVERY:-50}"
DATASET_TARGET_LOOKAHEAD="${DATASET_TARGET_LOOKAHEAD:-8}"
DATASET_ACTION_TRANSLATION_GAIN="${DATASET_ACTION_TRANSLATION_GAIN:-1.0}"
DATASET_ACTION_ROTATION_GAIN="${DATASET_ACTION_ROTATION_GAIN:-1.0}"
RENDERING_MODE="${RENDERING_MODE:-quality}"

if [ -z "$CODE_COMMIT" ]; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
if [ ! -f "$SOURCE_MANIFEST" ]; then
  echo "Missing source manifest: $SOURCE_MANIFEST" >&2
  exit 2
fi
if [ ! -x "$WRAPPER" ]; then
  echo "Missing or non-executable wrapper: $WRAPPER" >&2
  exit 2
fi
if [ "$MAX_CONCURRENT" -lt 1 ]; then
  echo "MAX_CONCURRENT must be positive" >&2
  exit 2
fi

mkdir -p "$OUTPUT_ROOT/submitter" "$LOG_DIR"
CONFIG_JSON="$OUTPUT_ROOT/submitter/config.json"
python3 - "$CONFIG_JSON" <<PY
import json
from pathlib import Path

payload = {
    "code_commit": "$CODE_COMMIT",
    "source_manifest": "$SOURCE_MANIFEST",
    "dataset_run_name": "$DATASET_RUN_NAME",
    "output_root": "$OUTPUT_ROOT",
    "index_spec": "$INDEX_SPEC",
    "max_concurrent": int("$MAX_CONCURRENT"),
    "video_every": int("$VIDEO_EVERY"),
    "dataset_target_lookahead": int("$DATASET_TARGET_LOOKAHEAD"),
    "dataset_action_translation_gain": float("$DATASET_ACTION_TRANSLATION_GAIN"),
    "dataset_action_rotation_gain": float("$DATASET_ACTION_ROTATION_GAIN"),
    "rendering_mode": "$RENDERING_MODE",
    "dynamics_mode": True,
    "recording_require_success": True,
    "recording_replay_gate": True,
    "hide_robot_debug_sites": True,
}
Path("$CONFIG_JSON").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

job_id="$(
  sbatch --parsable \
    --array="${INDEX_SPEC}%${MAX_CONCURRENT}" \
    --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",SOURCE_MANIFEST="$SOURCE_MANIFEST",OUTPUT_ROOT="$OUTPUT_ROOT",DATASET_RUN_NAME="$DATASET_RUN_NAME",CODE_COMMIT="$CODE_COMMIT",VIDEO_EVERY="$VIDEO_EVERY",DATASET_TARGET_LOOKAHEAD="$DATASET_TARGET_LOOKAHEAD",DATASET_ACTION_TRANSLATION_GAIN="$DATASET_ACTION_TRANSLATION_GAIN",DATASET_ACTION_ROTATION_GAIN="$DATASET_ACTION_ROTATION_GAIN",RENDERING_MODE="$RENDERING_MODE" \
    "$WRAPPER"
)"
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$job_id" "$INDEX_SPEC" "$CODE_COMMIT" \
  | tee -a "$OUTPUT_ROOT/submitter/submissions.tsv"
echo "dataset_array_job_id=$job_id"
echo "output_root=$OUTPUT_ROOT"
