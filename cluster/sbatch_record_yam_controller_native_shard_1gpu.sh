#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_ctrl_record
#SBATCH --partition=batch
#SBATCH --time=00:30:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/record_yam_controller_native_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
SOURCE_MANIFEST="${SOURCE_MANIFEST:?Set SOURCE_MANIFEST to the original 500-shard manifest.}"
OUTPUT_ROOT="${OUTPUT_ROOT:?Set OUTPUT_ROOT for controller-native records.}"
EVAL_WRAPPER="${EVAL_WRAPPER:-$CODE_NFS/cluster/sbatch_eval_yam_pickplace_rgb_dp_policy_1gpu.sh}"
SOURCE_INDEX="${SOURCE_INDEX:-${SLURM_ARRAY_TASK_ID:?Set SOURCE_INDEX or submit as a Slurm array.}}"
DATASET_RUN_NAME="${DATASET_RUN_NAME:-$(basename "$OUTPUT_ROOT")}"
CODE_COMMIT="${CODE_COMMIT:-}"

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
DATASET_DROP_SETTLE_MAX_STEPS="${DATASET_DROP_SETTLE_MAX_STEPS:-60}"
DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M="${DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M:-0.01}"
DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M="${DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M:-0.01}"
DATASET_DROP_SETTLE_LINEAR_SPEED="${DATASET_DROP_SETTLE_LINEAR_SPEED:-0.10}"
DATASET_DROP_SETTLE_ANGULAR_SPEED="${DATASET_DROP_SETTLE_ANGULAR_SPEED:-10.0}"
DATASET_DROP_FALLBACK_AFTER_STEPS="${DATASET_DROP_FALLBACK_AFTER_STEPS:-30}"
DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M="${DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M:-0.03}"
DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M="${DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M:-0.055}"
DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M="${DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M:-0.015}"
DATASET_DROP_FALLBACK_LINEAR_SPEED="${DATASET_DROP_FALLBACK_LINEAR_SPEED:-0.03}"
DATASET_DROP_FALLBACK_ANGULAR_SPEED="${DATASET_DROP_FALLBACK_ANGULAR_SPEED:-4.0}"
DATASET_DROP_FALLBACK_OPEN_STEPS="${DATASET_DROP_FALLBACK_OPEN_STEPS:-60}"
DATASET_DROP_FALLBACK_RETRACT_LATERAL_M="${DATASET_DROP_FALLBACK_RETRACT_LATERAL_M:-0.0}"
DATASET_POST_ACTION_SETTLE_STEPS="${DATASET_POST_ACTION_SETTLE_STEPS:-30}"
DATASET_ACTION_TRANSLATION_GAIN="${DATASET_ACTION_TRANSLATION_GAIN:-1.0}"
DATASET_ACTION_ROTATION_GAIN="${DATASET_ACTION_ROTATION_GAIN:-1.0}"
RECORDING_GATE_FALLBACK_POSE_LOOKAHEAD="${RECORDING_GATE_FALLBACK_POSE_LOOKAHEAD:-4}"
CONTROL_MODE="${CONTROL_MODE:-dataset_pose_targets}"
RECOVERY_PHASE_PATTERN="${RECOVERY_PHASE_PATTERN:-target/go_from_pre_grasp_to_grasp_pose}"
RECOVERY_PHASE_FRACTION="${RECOVERY_PHASE_FRACTION:-0.5}"
RECOVERY_PERTURBATION_STEPS="${RECOVERY_PERTURBATION_STEPS:-2}"
RECOVERY_TRANSLATION_ACTION_MAX="${RECOVERY_TRANSLATION_ACTION_MAX:-0.18}"
RECOVERY_ROTATION_ACTION_MAX="${RECOVERY_ROTATION_ACTION_MAX:-0.12}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="${YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION:-True}"
YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="${YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION:-True}"
YAM_POLICY_GROUND_TEXTURE_DIR="${YAM_POLICY_GROUND_TEXTURE_DIR:-/code/dextrah_lab/assets/textures/floor_polyhaven}"
YAM_POLICY_GROUND_TEXTURE_TILING_RANGE="${YAM_POLICY_GROUND_TEXTURE_TILING_RANGE:-2.0 5.0}"
YAM_POLICY_GROUND_TEXTURE_SIZE="${YAM_POLICY_GROUND_TEXTURE_SIZE:-20.0 20.0}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-False}"
VIDEO_EVERY="${VIDEO_EVERY:-0}"
PRINT_INTERVAL="${PRINT_INTERVAL:-100}"
INITIAL_RENDER_WARMUP_FRAMES="${INITIAL_RENDER_WARMUP_FRAMES:-64}"
SEED_BASE="${SEED_BASE:-79000001}"

if [ ! -f "$SOURCE_MANIFEST" ]; then
  echo "Missing source manifest: $SOURCE_MANIFEST" >&2
  exit 2
fi
if [ ! -f "$EVAL_WRAPPER" ]; then
  echo "Missing eval wrapper: $EVAL_WRAPPER" >&2
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT got $actual_commit" >&2
    exit 2
  fi
fi

mapfile -t SOURCE_FIELDS < <(
  python3 - "$SOURCE_MANIFEST" "$SOURCE_INDEX" <<'PY'
import json
import os
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
index = int(sys.argv[2])
payload = json.loads(manifest.read_text(encoding="utf-8"))
shards = payload.get("shards") or []
if not 0 <= index < len(shards):
    raise SystemExit(f"source index {index} outside [0, {len(shards)})")
row = shards[index]
source_path = Path(str(row["path"])).expanduser()
if not source_path.is_absolute():
    source_path = Path(os.path.abspath(manifest.parent / source_path))
print(source_path)
print(int(row.get("num_steps") or row["action_shape"][0]))
PY
)
if [ "${#SOURCE_FIELDS[@]}" -ne 2 ]; then
  echo "Failed to resolve source shard $SOURCE_INDEX from $SOURCE_MANIFEST" >&2
  exit 2
fi

SOURCE_SHARD="${SOURCE_FIELDS[0]}"
NUM_STEPS="${SOURCE_FIELDS[1]}"
if [ "$CONTROL_MODE" = "dataset_pose_targets" ] || [ "$CONTROL_MODE" = "dataset_pose_recovery" ]; then
  NUM_STEPS=$((NUM_STEPS + DATASET_MAX_EXTRA_STEPS))
fi
if [ "$CONTROL_MODE" = "dataset_pose_recovery" ]; then
  NUM_STEPS=$((NUM_STEPS + RECOVERY_PERTURBATION_STEPS + 16))
fi
SOURCE_INDEX_PADDED="$(printf '%06d' "$SOURCE_INDEX")"
RECORD_DIR="$OUTPUT_ROOT/records/source_$SOURCE_INDEX_PADDED"
RECORD_POLICY_SHARD="$RECORD_DIR/policy_dataset/yam_rgb_policy_$SOURCE_INDEX_PADDED"
RUN_NAME="${DATASET_RUN_NAME}_source_${SOURCE_INDEX_PADDED}"
METRICS_PATH="$RESULTS_NFS/evals/$RUN_NAME/metrics.json"

if [ -s "$RECORD_POLICY_SHARD/metadata.json" ] && [ -s "$METRICS_PATH" ]; then
  if python3 - "$METRICS_PATH" "$RECORD_POLICY_SHARD/metadata.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8")).get("summary", {})
recording = summary.get("recording") or {}
gate = recording.get("replay_gate") or {}
metadata = json.load(open(sys.argv[2], "r", encoding="utf-8"))
provenance = metadata.get("recording") or {}
visual_replay = metadata.get("exact_visual_replay") or {}
visual_paths = visual_replay.get("paths") or {}
required_visual_assets = ["table_texture", "dome_texture"]
if bool(visual_replay.get("ground_texture_enabled")):
    required_visual_assets.append("background_texture")
authoritative_visual_assets = all(
    bool((visual_paths.get(name) or {}).get("selected"))
    for name in required_visual_assets
)
fallback_used = provenance.get("episode_drop_fallback_used") or []
release_hold = provenance.get("episode_drop_release_hold_started") or []
fallback_release_valid = (
    bool(fallback_used)
    and len(fallback_used) == len(release_hold)
    and all(not bool(fallback) or bool(held) for fallback, held in zip(fallback_used, release_hold))
)
controller_version = int(provenance.get("dataset_drop_controller_version") or 0)
drop_descent = provenance.get("episode_drop_descent_started") or []
controller_paths = provenance.get("episode_controller_paths") or []
drop_timeouts = provenance.get("episode_drop_settle_timed_out") or []
if controller_version == 12:
    controller_path_valid = bool(drop_descent) and all(bool(value) for value in drop_descent)
else:
    expected_paths = [
        "staged_descent" if bool(descent) else "source_tracked_drop"
        for descent in drop_descent
    ]
    controller_path_valid = (
        controller_version >= 13
        and provenance.get("dataset_drop_acceptance_mode")
        == "final_physical_success_plus_dynamics_replay"
        and bool(controller_paths)
        and [str(value) for value in controller_paths] == expected_paths
    )
expected_open_trigger = {
    14: "contained_geometry_without_hidden_timeout",
    15: "contained_geometry_with_tcp_stall_recovery",
    16: "contained_geometry_with_tcp_stall_recovery",
}.get(controller_version)
observable_open_valid = controller_version < 14 or (
    provenance.get("dataset_drop_open_trigger") == expected_open_trigger
    and len(drop_timeouts) == len(drop_descent)
    and not any(bool(value) for value in drop_timeouts)
)
valid = (
    recording.get("accepted")
    and gate.get("passed")
    and provenance.get("dynamics_mode")
    and provenance.get("exact_reset")
    and provenance.get("rendering_mode") == "quality"
    and int(provenance.get("initial_render_warmup_frames") or 0) >= 64
    and provenance.get("exact_visual_resample")
    and authoritative_visual_assets
    and provenance.get("robot_material_randomization")
    and provenance.get("object_material_randomization")
    and provenance.get("dataset_drop_targeting_mode") == "live_object_to_bin_center"
    and provenance.get("dataset_drop_release_height_mode") == "above_bin_top_then_contained_descent"
    and controller_version >= 12
    and provenance.get("dataset_drop_release_criterion") == "gripper_open_or_hand_separated"
    and provenance.get("recording_gate_fallback_replay_mode") == "robot_pose_target_dynamics"
    and provenance.get("dataset_drop_spec_source") == "exact_stable_scene"
    and all(provenance.get("episode_final_success") or [])
    and controller_path_valid
    and observable_open_valid
    and fallback_release_valid
    and all(bool(item.get("final_success")) for item in gate.get("episodes") or [])
)
raise SystemExit(0 if valid else 1)
PY
  then
    echo "Controller-native shard already passed: $RECORD_POLICY_SHARD"
    exit 0
  fi
fi

if [ "$VIDEO_EVERY" -gt 0 ] && [ $((SOURCE_INDEX % VIDEO_EVERY)) -eq 0 ]; then
  CAPTURE_VIDEO=True
fi

mkdir -p "$RECORD_DIR" "$OUTPUT_ROOT"
echo "source_index=$SOURCE_INDEX"
echo "source_shard=$SOURCE_SHARD"
echo "num_steps=$NUM_STEPS"
echo "record_policy_shard=$RECORD_POLICY_SHARD"
echo "run_name=$RUN_NAME"

exec env \
  CODE_NFS="$CODE_NFS" \
  RESULTS_NFS="$RESULTS_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  RUN_NAME="$RUN_NAME" \
  CONTROL_MODE="$CONTROL_MODE" \
  EXACT_POLICY_SHARD="$SOURCE_SHARD" \
  EXACT_VISUAL_RESAMPLE=True \
  YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="$YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION" \
  YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="$YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION" \
  YAM_POLICY_GROUND_TEXTURE_DIR="$YAM_POLICY_GROUND_TEXTURE_DIR" \
  YAM_POLICY_GROUND_TEXTURE_TILING_RANGE="$YAM_POLICY_GROUND_TEXTURE_TILING_RANGE" \
  YAM_POLICY_GROUND_TEXTURE_SIZE="$YAM_POLICY_GROUND_TEXTURE_SIZE" \
  RECORD_POLICY_SHARD="$RECORD_POLICY_SHARD" \
  NUM_EPISODES=1 \
  NUM_STEPS="$NUM_STEPS" \
  DATASET_TARGET_LOOKAHEAD="$DATASET_TARGET_LOOKAHEAD" \
  DATASET_PRECISION_LOOKAHEAD="$DATASET_PRECISION_LOOKAHEAD" \
  DATASET_OBJECT_FEEDBACK_GAIN="$DATASET_OBJECT_FEEDBACK_GAIN" \
  DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M="$DATASET_OBJECT_FEEDBACK_MAX_CORRECTION_M" \
  DATASET_PRECISION_POSITION_TOLERANCE_M="$DATASET_PRECISION_POSITION_TOLERANCE_M" \
  DATASET_PRECISION_ROTATION_TOLERANCE_RAD="$DATASET_PRECISION_ROTATION_TOLERANCE_RAD" \
  DATASET_PRECISION_MAX_REPEATS="$DATASET_PRECISION_MAX_REPEATS" \
  DATASET_DROP_REFERENCE_INSET_M="$DATASET_DROP_REFERENCE_INSET_M" \
  DATASET_DROP_RELEASE_CLEARANCE_M="$DATASET_DROP_RELEASE_CLEARANCE_M" \
  DATASET_DROP_TRANSPORT_CLEARANCE_M="$DATASET_DROP_TRANSPORT_CLEARANCE_M" \
  DATASET_DROP_DESCENT_CENTER_TOLERANCE_M="$DATASET_DROP_DESCENT_CENTER_TOLERANCE_M" \
  DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M="$DATASET_DROP_DESCENT_HEIGHT_TOLERANCE_M" \
  DATASET_DROP_POSE_MAX_CORRECTION_M="$DATASET_DROP_POSE_MAX_CORRECTION_M" \
  DATASET_DROP_RETRACT_HEIGHT_M="$DATASET_DROP_RETRACT_HEIGHT_M" \
  DATASET_DROP_RETRACT_GRIPPER_WIDTH_M="$DATASET_DROP_RETRACT_GRIPPER_WIDTH_M" \
  DATASET_DROP_SETTLE_MAX_STEPS="$DATASET_DROP_SETTLE_MAX_STEPS" \
  DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M="$DATASET_DROP_SETTLE_CONTAINMENT_MARGIN_M" \
  DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M="$DATASET_DROP_SETTLE_HEIGHT_TOLERANCE_M" \
  DATASET_DROP_SETTLE_LINEAR_SPEED="$DATASET_DROP_SETTLE_LINEAR_SPEED" \
  DATASET_DROP_SETTLE_ANGULAR_SPEED="$DATASET_DROP_SETTLE_ANGULAR_SPEED" \
  DATASET_DROP_FALLBACK_AFTER_STEPS="$DATASET_DROP_FALLBACK_AFTER_STEPS" \
  DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M="$DATASET_DROP_FALLBACK_TRIGGER_HEIGHT_ERROR_M" \
  DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M="$DATASET_DROP_FALLBACK_RELEASE_CLEARANCE_M" \
  DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M="$DATASET_DROP_FALLBACK_HEIGHT_TOLERANCE_M" \
  DATASET_DROP_FALLBACK_LINEAR_SPEED="$DATASET_DROP_FALLBACK_LINEAR_SPEED" \
  DATASET_DROP_FALLBACK_ANGULAR_SPEED="$DATASET_DROP_FALLBACK_ANGULAR_SPEED" \
  DATASET_DROP_FALLBACK_OPEN_STEPS="$DATASET_DROP_FALLBACK_OPEN_STEPS" \
  DATASET_DROP_FALLBACK_RETRACT_LATERAL_M="$DATASET_DROP_FALLBACK_RETRACT_LATERAL_M" \
  DATASET_POST_ACTION_SETTLE_STEPS="$DATASET_POST_ACTION_SETTLE_STEPS" \
  DATASET_ACTION_TRANSLATION_GAIN="$DATASET_ACTION_TRANSLATION_GAIN" \
  DATASET_ACTION_ROTATION_GAIN="$DATASET_ACTION_ROTATION_GAIN" \
  RECORDING_GATE_FALLBACK_POSE_LOOKAHEAD="$RECORDING_GATE_FALLBACK_POSE_LOOKAHEAD" \
  RECOVERY_PHASE_PATTERN="$RECOVERY_PHASE_PATTERN" \
  RECOVERY_PHASE_FRACTION="$RECOVERY_PHASE_FRACTION" \
  RECOVERY_PERTURBATION_STEPS="$RECOVERY_PERTURBATION_STEPS" \
  RECOVERY_TRANSLATION_ACTION_MAX="$RECOVERY_TRANSLATION_ACTION_MAX" \
  RECOVERY_ROTATION_ACTION_MAX="$RECOVERY_ROTATION_ACTION_MAX" \
  DISABLE_FAILURE_TERMINATIONS=True \
  DISABLE_SUCCESS_TERMINATION=True \
  STOP_ON_DONE=False \
  STOP_ON_BIN_DROP_SUCCESS=False \
  RECORDING_REQUIRE_SUCCESS=True \
  RECORDING_REPLAY_GATE=True \
  RECORDING_SELECT_REPLAYABLE_SUCCESS_PREFIX=True \
  CAPTURE_VIDEO="$CAPTURE_VIDEO" \
  VIDEO_LENGTH="$NUM_STEPS" \
  PRINT_INTERVAL="$PRINT_INTERVAL" \
  INITIAL_RENDER_WARMUP_FRAMES="$INITIAL_RENDER_WARMUP_FRAMES" \
  RENDERING_MODE="$RENDERING_MODE" \
  SEED="$((SEED_BASE + SOURCE_INDEX))" \
  HIDE_ROBOT_DEBUG_SITES=True \
  bash "$EVAL_WRAPPER"
