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
POLL_SECONDS="${POLL_SECONDS:-20}"
SBATCH_TIME="${SBATCH_TIME:-00:10:00}"
CODE_COMMIT="${CODE_COMMIT:-}"
VIDEO_EVERY="${VIDEO_EVERY:-50}"
INITIAL_RENDER_WARMUP_FRAMES="${INITIAL_RENDER_WARMUP_FRAMES:-64}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yamcn_$(printf '%s' "$DATASET_RUN_NAME" | cksum | awk '{print $1}')}"
DATASET_TARGET_LOOKAHEAD="${DATASET_TARGET_LOOKAHEAD:-8}"
DATASET_PRECISION_LOOKAHEAD="${DATASET_PRECISION_LOOKAHEAD:-2}"
DATASET_OBJECT_FEEDBACK_GAIN="${DATASET_OBJECT_FEEDBACK_GAIN:-1.0}"
DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M="${DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M:-0.015}"
DATASET_MAX_EXTRA_STEPS="${DATASET_MAX_EXTRA_STEPS:-768}"
DATASET_PRECISION_POSITION_TOLERANCE_M="${DATASET_PRECISION_POSITION_TOLERANCE_M:-0.01}"
DATASET_PRECISION_ROTATION_TOLERANCE_RAD="${DATASET_PRECISION_ROTATION_TOLERANCE_RAD:-0.20}"
DATASET_PRECISION_MAX_REPEATS="${DATASET_PRECISION_MAX_REPEATS:-2}"
DATASET_DROP_REFERENCE_INSET_M="${DATASET_DROP_REFERENCE_INSET_M:-0.06}"
DATASET_DROP_RELEASE_CLEARANCE_M="${DATASET_DROP_RELEASE_CLEARANCE_M:-0.015}"
DATASET_DROP_TRANSPORT_CLEARANCE_M="${DATASET_DROP_TRANSPORT_CLEARANCE_M:-0.015}"
DATASET_DROP_DESCENT_CENTER_TOLERANCE_M="${DATASET_DROP_DESCENT_CENTER_TOLERANCE_M:-0.015}"
DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M="${DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M:-0.01}"
DATASET_DROP_POSE_MAX_CORRECTION_M="${DATASET_DROP_POSE_MAX_CORRECTION_M:-0.008}"
DATASET_DROP_RETRACT_HEIGHT_M="${DATASET_DROP_RETRACT_HEIGHT_M:-0.08}"
DATASET_DROP_RETRACT_GRIPPER_WIDTH_M="${DATASET_DROP_RETRACT_GRIPPER_WIDTH_M:-0.18}"
DATASET_DROP_SETTLE_MAX_STEPS="${DATASET_DROP_SETTLE_MAX_STEPS:-240}"
DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M="${DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M:-0.01}"
DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M="${DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M:-0.01}"
DATASET_DROP_SETTLE_LINEAR_SPEED="${DATASET_DROP_SETTLE_LINEAR_SPEED:-0.10}"
DATASET_DROP_SETTLE_ANGULAR_SPEED="${DATASET_DROP_SETTLE_ANGULAR_SPEED:-10.0}"
DATASET_DROP_FALLBACK_AFTER_STEPS="${DATASET_DROP_FALLBACK_AFTER_STEPS:-240}"
DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M="${DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M:-0.10}"
DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M="${DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M:-0.055}"
DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M="${DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M:-0.015}"
DATASET_DROP_FALLBACK_LINEAR_SPEED="${DATASET_DROP_FALLBACK_LINEAR_SPEED:-0.03}"
DATASET_DROP_FALLBACK_ANGULAR_SPEED="${DATASET_DROP_FALLBACK_ANGULAR_SPEED:-4.0}"
DATASET_DROP_FALLBACK_OPEN_STEPS="${DATASET_DROP_FALLBACK_OPEN_STEPS:-60}"
DATASET_DROP_FALLBACK_RETRACT_LATERAL_M="${DATASET_DROP_FALLBACK_RETRACT_LATERAL_M:-0.0}"
DATASET_POST_ACTION_SETTLE_STEPS="${DATASET_POST_ACTION_SETTLE_STEPS:-30}"
DATASET_ACTION_TRANSLATION_GAIN="${DATASET_ACTION_TRANSLATION_GAIN:-1.0}"
DATASET_ACTION_ROTATION_GAIN="${DATASET_ACTION_ROTATION_GAIN:-1.0}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="${YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION:-True}"
YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="${YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION:-True}"
CONTROL_MODE="${CONTROL_MODE:-dataset_pose_targets}"
RECOVERY_PHASE_PATTERN="${RECOVERY_PHASE_PATTERN:-target/go_from_pre_grasp_to_grasp_pose}"
RECOVERY_PHASE_FRACTION="${RECOVERY_PHASE_FRACTION:-0.5}"
RECOVERY_PERTURBATION_STEPS="${RECOVERY_PERTURBATION_STEPS:-2}"
RECOVERY_TRANSLATION_ACTION_MAX="${RECOVERY_TRANSLATION_ACTION_MAX:-0.18}"
RECOVERY_ROTATION_ACTION_MAX="${RECOVERY_ROTATION_ACTION_MAX:-0.12}"

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
if [ "$POLL_SECONDS" -lt 1 ]; then
  echo "POLL_SECONDS must be positive" >&2
  exit 2
fi
if [[ ! "$JOB_NAME_PREFIX" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "JOB_NAME_PREFIX may contain only letters, digits, underscores, and hyphens" >&2
  exit 2
fi

mapfile -t SOURCE_INDICES < <(
  python3 - "$SOURCE_MANIFEST" "$INDEX_SPEC" <<'PY'
import json
import sys

manifest_path, spec = sys.argv[1:]
count = len(json.load(open(manifest_path, "r", encoding="utf-8")).get("shards") or [])
indices = []
seen = set()
for token in spec.split(","):
    token = token.strip()
    if not token:
        continue
    if "-" in token:
        start_text, stop_text = token.split("-", 1)
        start, stop = int(start_text), int(stop_text)
        if stop < start:
            raise SystemExit(f"descending index range is not supported: {token}")
        values = range(start, stop + 1)
    else:
        values = (int(token),)
    for value in values:
        if not 0 <= value < count:
            raise SystemExit(f"source index {value} outside [0, {count})")
        if value not in seen:
            indices.append(value)
            seen.add(value)
for value in indices:
    print(value)
PY
)
if [ "${#SOURCE_INDICES[@]}" -eq 0 ]; then
  echo "INDEX_SPEC resolved to no source indices: $INDEX_SPEC" >&2
  exit 2
fi

mkdir -p "$OUTPUT_ROOT/submitter" "$LOG_DIR"
exec 9>"$OUTPUT_ROOT/submitter/submitter.lock"
if ! flock -n 9; then
  echo "Another submitter owns $OUTPUT_ROOT/submitter/submitter.lock" >&2
  exit 2
fi
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
    "source_indices": [int(value) for value in "${SOURCE_INDICES[*]}".split()],
    "max_concurrent": int("$MAX_CONCURRENT"),
    "poll_seconds": int("$POLL_SECONDS"),
    "sbatch_time": "$SBATCH_TIME",
    "job_name_prefix": "$JOB_NAME_PREFIX",
    "submission_mode": "ordinary_jobs_with_submitter_throttle",
    "video_every": int("$VIDEO_EVERY"),
    "initial_render_warmup_frames": int("$INITIAL_RENDER_WARMUP_FRAMES"),
    "dataset_target_lookahead": int("$DATASET_TARGET_LOOKAHEAD"),
    "dataset_precision_lookahead": int("$DATASET_PRECISION_LOOKAHEAD"),
    "dataset_object_feedback_gain": float("$DATASET_OBJECT_FEEDBACK_GAIN"),
    "dataset_object_feedback_max_correction_m": float("$DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M"),
    "dataset_max_extra_steps": int("$DATASET_MAX_EXTRA_STEPS"),
    "dataset_precision_position_tolerance_m": float("$DATASET_PRECISION_POSITION_TOLERANCE_M"),
    "dataset_precision_rotation_tolerance_rad": float("$DATASET_PRECISION_ROTATION_TOLERANCE_RAD"),
    "dataset_precision_max_repeats": int("$DATASET_PRECISION_MAX_REPEATS"),
    "dataset_drop_reference_inset_m": float("$DATASET_DROP_REFERENCE_INSET_M"),
    "dataset_drop_release_clearance_m": float("$DATASET_DROP_RELEASE_CLEARANCE_M"),
    "dataset_drop_transport_clearance_m": float("$DATASET_DROP_TRANSPORT_CLEARANCE_M"),
    "dataset_drop_descent_center_tolerance_m": float("$DATASET_DROP_DESCENT_CENTER_TOLERANCE_M"),
    "dataset_drop_descent_height_tolerance_m": float("$DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M"),
    "dataset_drop_pose_max_correction_m": float("$DATASET_DROP_POSE_MAX_CORRECTION_M"),
    "dataset_drop_retract_height_m": float("$DATASET_DROP_RETRACT_HEIGHT_M"),
    "dataset_drop_retract_gripper_width_m": float("$DATASET_DROP_RETRACT_GRIPPER_WIDTH_M"),
    "dataset_drop_settle_max_steps": int("$DATASET_DROP_SETTLE_MAX_STEPS"),
    "dataset_drop_settle_containment_margin_m": float("$DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M"),
    "dataset_drop_settle_height_tolerance_m": float("$DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M"),
    "dataset_drop_settle_linear_speed": float("$DATASET_DROP_SETTLE_LINEAR_SPEED"),
    "dataset_drop_settle_angular_speed": float("$DATASET_DROP_SETTLE_ANGULAR_SPEED"),
    "dataset_drop_fallback_after_steps": int("$DATASET_DROP_FALLBACK_AFTER_STEPS"),
    "dataset_drop_fallback_trigger_height_error_m": float("$DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M"),
    "dataset_drop_fallback_release_clearance_m": float("$DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M"),
    "dataset_drop_fallback_height_tolerance_m": float("$DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M"),
    "dataset_drop_fallback_linear_speed": float("$DATASET_DROP_FALLBACK_LINEAR_SPEED"),
    "dataset_drop_fallback_angular_speed": float("$DATASET_DROP_FALLBACK_ANGULAR_SPEED"),
    "dataset_drop_fallback_open_steps": int("$DATASET_DROP_FALLBACK_OPEN_STEPS"),
    "dataset_drop_fallback_retract_lateral_m": float("$DATASET_DROP_FALLBACK_RETRACT_LATERAL_M"),
    "dataset_post_action_settle_steps": int("$DATASET_POST_ACTION_SETTLE_STEPS"),
    "dataset_action_translation_gain": float("$DATASET_ACTION_TRANSLATION_GAIN"),
    "dataset_action_rotation_gain": float("$DATASET_ACTION_ROTATION_GAIN"),
    "rendering_mode": "$RENDERING_MODE",
    "robot_material_randomization": "$YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION" == "True",
    "object_material_randomization": "$YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION" == "True",
    "control_mode": "$CONTROL_MODE",
    "recovery_phase_pattern": "$RECOVERY_PHASE_PATTERN",
    "recovery_phase_fraction": float("$RECOVERY_PHASE_FRACTION"),
    "recovery_perturbation_steps": int("$RECOVERY_PERTURBATION_STEPS"),
    "recovery_translation_action_max": float("$RECOVERY_TRANSLATION_ACTION_MAX"),
    "recovery_rotation_action_max": float("$RECOVERY_ROTATION_ACTION_MAX"),
    "dynamics_mode": True,
    "recording_require_success": True,
    "recording_replay_gate": True,
    "exact_visual_resample": True,
    "hide_robot_debug_sites": True,
}
Path("$CONFIG_JSON").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

SUBMISSIONS_TSV="$OUTPUT_ROOT/submitter/submissions.tsv"
touch "$SUBMISSIONS_TSV"
printf '%s\t%s\t%s\t%s\t%s\n' "timestamp_utc" "job_id" "source_index" "job_name" "code_commit" > "$OUTPUT_ROOT/submitter/submissions_header.tsv"
printf '%s\t%s\t%s\n' "$(hostname)" "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUTPUT_ROOT/submitter/submitter_process.tsv"

active_jobs() {
  squeue -h -u "${USER:-lzha}" -t PENDING,RUNNING,CONFIGURING,COMPLETING -o "%j" \
    | grep -c "^${JOB_NAME_PREFIX}_s" || true
}

for source_index in "${SOURCE_INDICES[@]}"; do
  while [ "$(active_jobs)" -ge "$MAX_CONCURRENT" ]; do
    sleep "$POLL_SECONDS"
  done
  source_index_padded="$(printf '%06d' "$source_index")"
  job_name="${JOB_NAME_PREFIX}_s${source_index_padded}"
  job_id="$(
    sbatch --parsable \
      --job-name="$job_name" \
      --time="$SBATCH_TIME" \
      --output="$LOG_DIR/record_yam_controller_native_${DATASET_RUN_NAME}_${source_index_padded}_%j.out" \
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",SOURCE_MANIFEST="$SOURCE_MANIFEST",SOURCE_INDEX="$source_index",OUTPUT_ROOT="$OUTPUT_ROOT",DATASET_RUN_NAME="$DATASET_RUN_NAME",CODE_COMMIT="$CODE_COMMIT",VIDEO_EVERY="$VIDEO_EVERY",INITIAL_RENDER_WARMUP_FRAMES="$INITIAL_RENDER_WARMUP_FRAMES",YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="$YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION",YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="$YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION",DATASET_TARGET_LOOKAHEAD="$DATASET_TARGET_LOOKAHEAD",DATASET_PRECISION_LOOKAHEAD="$DATASET_PRECISION_LOOKAHEAD",DATASET_OBJECT_FEEDBACK_GAIN="$DATASET_OBJECT_FEEDBACK_GAIN",DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M="$DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M",DATASET_MAX_EXTRA_STEPS="$DATASET_MAX_EXTRA_STEPS",DATASET_PRECISION_POSITION_TOLERANCE_M="$DATASET_PRECISION_POSITION_TOLERANCE_M",DATASET_PRECISION_ROTATION_TOLERANCE_RAD="$DATASET_PRECISION_ROTATION_TOLERANCE_RAD",DATASET_PRECISION_MAX_REPEATS="$DATASET_PRECISION_MAX_REPEATS",DATASET_DROP_REFERENCE_INSET_M="$DATASET_DROP_REFERENCE_INSET_M",DATASET_DROP_RELEASE_CLEARANCE_M="$DATASET_DROP_RELEASE_CLEARANCE_M",DATASET_DROP_TRANSPORT_CLEARANCE_M="$DATASET_DROP_TRANSPORT_CLEARANCE_M",DATASET_DROP_DESCENT_CENTER_TOLERANCE_M="$DATASET_DROP_DESCENT_CENTER_TOLERANCE_M",DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M="$DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M",DATASET_DROP_POSE_MAX_CORRECTION_M="$DATASET_DROP_POSE_MAX_CORRECTION_M",DATASET_DROP_RETRACT_HEIGHT_M="$DATASET_DROP_RETRACT_HEIGHT_M",DATASET_DROP_RETRACT_GRIPPER_WIDTH_M="$DATASET_DROP_RETRACT_GRIPPER_WIDTH_M",DATASET_DROP_SETTLE_MAX_STEPS="$DATASET_DROP_SETTLE_MAX_STEPS",DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M="$DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M",DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M="$DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M",DATASET_DROP_SETTLE_LINEAR_SPEED="$DATASET_DROP_SETTLE_LINEAR_SPEED",DATASET_DROP_SETTLE_ANGULAR_SPEED="$DATASET_DROP_SETTLE_ANGULAR_SPEED",DATASET_DROP_FALLBACK_AFTER_STEPS="$DATASET_DROP_FALLBACK_AFTER_STEPS",DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M="$DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M",DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M="$DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M",DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M="$DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M",DATASET_DROP_FALLBACK_LINEAR_SPEED="$DATASET_DROP_FALLBACK_LINEAR_SPEED",DATASET_DROP_FALLBACK_ANGULAR_SPEED="$DATASET_DROP_FALLBACK_ANGULAR_SPEED",DATASET_DROP_FALLBACK_OPEN_STEPS="$DATASET_DROP_FALLBACK_OPEN_STEPS",DATASET_DROP_FALLBACK_RETRACT_LATERAL_M="$DATASET_DROP_FALLBACK_RETRACT_LATERAL_M",DATASET_POST_ACTION_SETTLE_STEPS="$DATASET_POST_ACTION_SETTLE_STEPS",DATASET_ACTION_TRANSLATION_GAIN="$DATASET_ACTION_TRANSLATION_GAIN",DATASET_ACTION_ROTATION_GAIN="$DATASET_ACTION_ROTATION_GAIN",RENDERING_MODE="$RENDERING_MODE",CONTROL_MODE="$CONTROL_MODE",RECOVERY_PHASE_PATTERN="$RECOVERY_PHASE_PATTERN",RECOVERY_PHASE_FRACTION="$RECOVERY_PHASE_FRACTION",RECOVERY_PERTURBATION_STEPS="$RECOVERY_PERTURBATION_STEPS",RECOVERY_TRANSLATION_ACTION_MAX="$RECOVERY_TRANSLATION_ACTION_MAX",RECOVERY_ROTATION_ACTION_MAX="$RECOVERY_ROTATION_ACTION_MAX" \
      "$WRAPPER"
  )"
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$job_id" "$source_index" "$job_name" "$CODE_COMMIT" \
    | tee -a "$SUBMISSIONS_TSV"
done

echo "submitted_jobs=$SUBMISSIONS_TSV"
echo "output_root=$OUTPUT_ROOT"
