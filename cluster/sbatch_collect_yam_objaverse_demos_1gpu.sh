#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_objaverse_demos
#SBATCH --partition=batch_long
#SBATCH --time=1-00:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_objaverse_demos_%A_%a.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
GRASPGENX_NFS="${GRASPGENX_NFS:-$NFS_ROOT/src/graspgenx}"
CUROBO_NFS="${CUROBO_NFS:-$NFS_ROOT/src/curobo}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
GRASPGENX_VENV_NAME="${GRASPGENX_VENV_NAME:-graspgenx-py312}"
GRASPGENX_IMAGE="${GRASPGENX_IMAGE:-$NFS_ROOT/cache/graspgenx_ngc2503_base.sqsh}"
PIP_CACHE_NFS="${PIP_CACHE_NFS:-$NFS_ROOT/cache/pip}"

FULL_OBJAVERSE_ASSET_ROOT="${FULL_OBJAVERSE_ASSET_ROOT:-$RESULTS_NFS/assets/graspgen_objects_full_cpu_20260617_153051}"
FULL_OBJAVERSE_MANIFEST_PATH="${FULL_OBJAVERSE_MANIFEST_PATH:-$FULL_OBJAVERSE_ASSET_ROOT/manifest.json}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
SHARD_INDEX="${SHARD_INDEX:-${SLURM_ARRAY_TASK_ID:-0}}"
SHARD_COUNT="${SHARD_COUNT:-${SLURM_ARRAY_TASK_COUNT:-1}}"
TOTAL_TARGET="${TOTAL_TARGET:-300}"
if [ -z "${SHARD_TARGET:-}" ]; then
  SHARD_TARGET="$(( (TOTAL_TARGET + SHARD_COUNT - 1) / SHARD_COUNT ))"
fi
START_SEED="${START_SEED:-91000}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-$((SHARD_TARGET * 5 + 5))}"
OBJECTS_PER_DEMO="${OBJECTS_PER_DEMO:-3}"
CLUTTER_OBJECT_COUNT="$((OBJECTS_PER_DEMO - 1))"
if [ "$CLUTTER_OBJECT_COUNT" -lt 0 ]; then
  echo "OBJECTS_PER_DEMO must be >= 1, got $OBJECTS_PER_DEMO" >&2
  exit 2
fi

BATCH_NAME="${BATCH_NAME:-yam_objaverse_pickplace_300_$(date +%Y%m%dT%H%M%SZ)}"
BATCH_DIR="${BATCH_DIR:-$RESULTS_NFS/yam_demos/$BATCH_NAME}"
SHARD_DIR="$BATCH_DIR/shard_$(printf '%03d' "$SHARD_INDEX")"
POOL_MANIFEST="${POOL_MANIFEST:-$BATCH_DIR/yam_objaverse_pool_manifest.json}"
EVENTS_JSONL="$SHARD_DIR/events.jsonl"
ACCEPTED_JSONL="$SHARD_DIR/accepted_demos.jsonl"
REJECTED_JSONL="$SHARD_DIR/rejected_attempts.jsonl"

POOL_MAX_ASSETS="${POOL_MAX_ASSETS:-1024}"
POOL_MIN_XY_RADIUS="${POOL_MIN_XY_RADIUS:-0.012}"
POOL_MAX_XY_RADIUS="${POOL_MAX_XY_RADIUS:-0.075}"
POOL_MIN_HEIGHT="${POOL_MIN_HEIGHT:-0.010}"
POOL_MAX_HEIGHT="${POOL_MAX_HEIGHT:-0.160}"
POOL_MAX_GRASP_WIDTH_P95="${POOL_MAX_GRASP_WIDTH_P95:-0.145}"

SETTLE_STEPS="${SETTLE_STEPS:-100}"
SETTLE_CAPTURE_INTERVAL="${SETTLE_CAPTURE_INTERVAL:-10}"
REPLAY_CAPTURE_INTERVAL="${REPLAY_CAPTURE_INTERVAL:-5}"
FPS="${FPS:-12}"
RECORD_RGB_WIDTH="${RECORD_RGB_WIDTH:-160}"
RECORD_RGB_HEIGHT="${RECORD_RGB_HEIGHT:-120}"
RECORD_RGB_INTERVAL="${RECORD_RGB_INTERVAL:-1}"
DEMO_STEPS_PER_OBJECT="${DEMO_STEPS_PER_OBJECT:-1500}"
DEMO_STEPS="${DEMO_STEPS:-$((DEMO_STEPS_PER_OBJECT * OBJECTS_PER_DEMO))}"

NUM_GRASPS="${NUM_GRASPS:-96}"
TOPK="${TOPK:-48}"
MAX_PLAN_ATTEMPTS="${MAX_PLAN_ATTEMPTS:-48}"
SCRIPTED_LIFT_HEIGHT="${SCRIPTED_LIFT_HEIGHT:-0.14}"
SCRIPTED_LIFT_FRAMES="${SCRIPTED_LIFT_FRAMES:-240}"
MOVE_TO_BIN_FRAMES="${MOVE_TO_BIN_FRAMES:-360}"
DROP_HEIGHT_ABOVE_BIN="${DROP_HEIGHT_ABOVE_BIN:-0.18}"

OBJECT_SPAWN_XY_RANDOMIZATION="${OBJECT_SPAWN_XY_RANDOMIZATION:-0.06}"
TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION="${TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION:-0.24}"
TABLETOP_CLUTTER_PLACEMENT_PADDING="${TABLETOP_CLUTTER_PLACEMENT_PADDING:-0.015}"
TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS="${TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS:-1024}"
TABLETOP_CLUTTER_MAX_XY_RADIUS="${TABLETOP_CLUTTER_MAX_XY_RADIUS:-$POOL_MAX_XY_RADIUS}"

CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

mkdir -p "$SHARD_DIR" "$NFS_ROOT/slurm_logs/dextrah" "$PIP_CACHE_NFS"

json_event() {
  local event="$1"
  shift
  python3 - "$event" "$@" <<'PY' | tee -a "$EVENTS_JSONL"
import json
import os
import sys
event = sys.argv[1]
pairs = sys.argv[2:]
payload = {"event": event}
for pair in pairs:
    key, _, value = pair.partition("=")
    payload[key] = value
print(json.dumps(payload, sort_keys=True))
PY
}

host_to_results_container() {
  local value="$1"
  if [[ "$value" == "$RESULTS_NFS"* ]]; then
    printf "/results%s" "${value#$RESULTS_NFS}"
  elif [[ "$value" == "$CODE_NFS"* ]]; then
    printf "/code%s" "${value#$CODE_NFS}"
  elif [[ "$value" == "$GRASPGENX_NFS"* ]]; then
    printf "/graspgenx%s" "${value#$GRASPGENX_NFS}"
  elif [[ "$value" == "$CUROBO_NFS"* ]]; then
    printf "/curobo%s" "${value#$CUROBO_NFS}"
  else
    printf "%s" "$value"
  fi
}

prepare_pool_manifest() {
  mkdir -p "$(dirname "$POOL_MANIFEST")"
  (
    flock 9
    if [ ! -s "$POOL_MANIFEST" ]; then
      output_asset_root="${FULL_OBJAVERSE_CONTAINER_ASSET_ROOT:-}"
      if [ -z "$output_asset_root" ]; then
        output_asset_root="$(host_to_results_container "$FULL_OBJAVERSE_ASSET_ROOT")"
      fi
      python3 "$CODE_NFS/dextrah_lab/scene_scripts/prepare_yam_objaverse_pool_manifest.py" \
        --source_manifest "$FULL_OBJAVERSE_MANIFEST_PATH" \
        --output_manifest "$POOL_MANIFEST" \
        --output_asset_root "$output_asset_root" \
        --max_assets "$POOL_MAX_ASSETS" \
        --seed "$START_SEED" \
        --min_xy_radius "$POOL_MIN_XY_RADIUS" \
        --max_xy_radius "$POOL_MAX_XY_RADIUS" \
        --min_height "$POOL_MIN_HEIGHT" \
        --max_height "$POOL_MAX_HEIGHT" \
        --max_grasp_width_p95 "$POOL_MAX_GRASP_WIDTH_P95"
    fi
  ) 9>"$POOL_MANIFEST.lock"
}

run_render_wrapper() {
  bash "$CODE_NFS/cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh"
}

run_settle() {
  local seed="$1"
  local run_name="$2"
  RUN_NAME="$run_name" \
  TASK="Dextrah-Single-YAM-Tabletop-Clutter-Grasp" \
  NUM_ENVS=1 \
  SEED="$seed" \
  SETTLE_STEPS="$SETTLE_STEPS" \
  CAPTURE_INTERVAL="$SETTLE_CAPTURE_INTERVAL" \
  FPS="$FPS" \
  DEMO_MODE=settle \
  DEMO_STEPS="$SETTLE_STEPS" \
  VIDEO_FILENAME=settle.mp4 \
  OBJECT_ASSET_MANIFEST_PATH="$POOL_MANIFEST" \
  OBJECT_ASSETS_DIR="$(dirname "$POOL_MANIFEST")" \
  OBJECT_ASSET_ASSIGNMENT=random \
  OBJECT_VALIDATE_USD_BOUNDS=False \
  OBJECT_SPAWN_XY_RANDOMIZATION="$OBJECT_SPAWN_XY_RANDOMIZATION" \
  TABLETOP_CLUTTER_ASSET_MANIFEST_PATH="$POOL_MANIFEST" \
  TABLETOP_CLUTTER_ASSETS_DIR="$(dirname "$POOL_MANIFEST")" \
  TABLETOP_CLUTTER_OBJECT_COUNT="$CLUTTER_OBJECT_COUNT" \
  TABLETOP_CLUTTER_MAX_OBJECTS=0 \
  TABLETOP_CLUTTER_ASSET_ASSIGNMENT=random \
  TABLETOP_CLUTTER_VALIDATE_USD_BOUNDS=False \
  TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION="$TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION" \
  TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE=0.006 \
  TABLETOP_CLUTTER_SPAWN_Z_JITTER=0.0 \
  TABLETOP_CLUTTER_NON_OVERLAPPING=True \
  TABLETOP_CLUTTER_PLACEMENT_PADDING="$TABLETOP_CLUTTER_PLACEMENT_PADDING" \
  TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS="$TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS" \
  TABLETOP_CLUTTER_MAX_XY_RADIUS="$TABLETOP_CLUTTER_MAX_XY_RADIUS" \
  TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS=16 \
  TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS=6 \
  TABLETOP_CLUTTER_LINEAR_DAMPING=0.25 \
  TABLETOP_CLUTTER_ANGULAR_DAMPING=1.25 \
  TABLETOP_CLUTTER_SLEEP_THRESHOLD=0.06 \
  TABLETOP_CLUTTER_STABILIZATION_THRESHOLD=0.03 \
  TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY=2.0 \
  CODE_NFS="$CODE_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  run_render_wrapper
}

run_planner() {
  local seed="$1"
  local stable_scene_host="$2"
  local plan_dir_host="$3"
  local stable_scene_container
  local plan_dir_container
  stable_scene_container="$(host_to_results_container "$stable_scene_host")"
  plan_dir_container="$(host_to_results_container "$plan_dir_host")"
  mkdir -p "$plan_dir_host"
  srun \
    --ntasks=1 \
    --container-image="$GRASPGENX_IMAGE" \
    --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$GRASPGENX_NFS":/graspgenx,"$CUROBO_NFS":/curobo,"$RESULTS_NFS":/results,"$ENV_NFS":/envs,"$PIP_CACHE_NFS":/root/.cache/pip \
    --no-container-entrypoint \
    --container-remap-root \
    --container-writable \
    --export=ALL,PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1,PYOPENGL_PLATFORM=egl,PYGLET_HEADLESS=true,EGL_PLATFORM=surfaceless,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,GRASPGENX_ROOT=/graspgenx,GRASPGENX_CUROBO_DIR=/curobo,GRASPGENX_CHECKPOINT_DIR=/graspgenx/ext/graspgenx_checkpoints,GRASPGENX_GRIPPER_CFG_DIR=/graspgenx/ext/gripper_descriptions \
    bash -lc "
      set -euo pipefail
      export VIRTUAL_ENV=/envs/$GRASPGENX_VENV_NAME
      export PATH=/envs/$GRASPGENX_VENV_NAME/bin:\$PATH
      export PYTHONPATH=/code:/graspgenx:/graspgenx/end2end:\${PYTHONPATH:-}
      cd /code
      python dextrah_lab/scene_scripts/plan_yam_multi_object_pick_place.py \
        --stable_scene_path '$stable_scene_container' \
        --output_dir '$plan_dir_container' \
        --run_name pick_drop \
        --graspgenx_root /graspgenx \
        --curobo_root /curobo \
        --seed '$seed' \
        --max_objects '$OBJECTS_PER_DEMO' \
        --num_grasps '$NUM_GRASPS' \
        --topk '$TOPK' \
        --max_plan_attempts '$MAX_PLAN_ATTEMPTS' \
        --move_to_bin_frames '$MOVE_TO_BIN_FRAMES' \
        --drop_height_above_bin '$DROP_HEIGHT_ABOVE_BIN' \
        --scripted_lift_mode always \
        --scripted_lift_height '$SCRIPTED_LIFT_HEIGHT' \
        --scripted_lift_frames '$SCRIPTED_LIFT_FRAMES'
    "
}

run_replay() {
  local seed="$1"
  local run_name="$2"
  local stable_scene_host="$3"
  local trajectory_host="$4"
  RUN_NAME="$run_name" \
  TASK="Dextrah-Single-YAM-Tabletop-Clutter-Grasp" \
  NUM_ENVS=1 \
  SEED="$seed" \
  DEMO_MODE=single_yam_trajectory \
  DEMO_STEPS="$DEMO_STEPS" \
  CAPTURE_INTERVAL="$REPLAY_CAPTURE_INTERVAL" \
  FPS="$FPS" \
  VIDEO_FILENAME=yam_pick_place.mp4 \
  DEMO_TRAJECTORY_PATH="$trajectory_host" \
  DEMO_TRAJECTORY_SOURCE=graspgenx_replay \
  DEMO_TRAJECTORY_REPLAY_MODE=dynamic \
  DEMO_TRAJECTORY_TIMING_MODE=realtime \
  DEMO_TRAJECTORY_VELOCITY_TARGETS=True \
  DEMO_TRAJECTORY_VELOCITY_TARGET_SCALE=1.0 \
  DEMO_START_BLEND_STEPS=36 \
  STABLE_SCENE_PATH="$stable_scene_host" \
  RECORD_TRAJECTORY_DATASET=True \
  TRAJECTORY_DATASET_PATH="$RESULTS_NFS/validations/$run_name/trajectory_dataset.npz" \
  RECORD_RGB_WIDTH="$RECORD_RGB_WIDTH" \
  RECORD_RGB_HEIGHT="$RECORD_RGB_HEIGHT" \
  RECORD_RGB_INTERVAL="$RECORD_RGB_INTERVAL" \
  OBJECT_VALIDATE_USD_BOUNDS=False \
  TABLETOP_CLUTTER_VALIDATE_USD_BOUNDS=False \
  HIDE_ROBOT_DEBUG_SITES=True \
  CODE_NFS="$CODE_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  run_render_wrapper
}

run_validate() {
  local replay_run_name="$1"
  local stable_scene_host="$2"
  local validation_host="$3"
  local dataset_container="/results/validations/$replay_run_name/trajectory_dataset.npz"
  local metrics_container="/results/validations/$replay_run_name/metrics.json"
  local stable_scene_container
  local validation_container
  stable_scene_container="$(host_to_results_container "$stable_scene_host")"
  validation_container="$(host_to_results_container "$validation_host")"
  srun \
    --ntasks=1 \
    --container-image="$GRASPGENX_IMAGE" \
    --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$GRASPGENX_NFS":/graspgenx,"$CUROBO_NFS":/curobo,"$RESULTS_NFS":/results,"$ENV_NFS":/envs,"$PIP_CACHE_NFS":/root/.cache/pip \
    --no-container-entrypoint \
    --container-remap-root \
    --container-writable \
    --export=ALL,PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1 \
    bash -lc "
      set -euo pipefail
      export VIRTUAL_ENV=/envs/$GRASPGENX_VENV_NAME
      export PATH=/envs/$GRASPGENX_VENV_NAME/bin:\$PATH
      cd /code
      python dextrah_lab/scene_scripts/validate_yam_pick_place_dataset.py \
        --dataset_path '$dataset_container' \
        --metrics_path '$metrics_container' \
        --stable_scene_path '$stable_scene_container' \
        --output_path '$validation_container' \
        --expected_objects '$OBJECTS_PER_DEMO'
    "
}

record_json_file_line() {
  local json_path="$1"
  local output_path="$2"
  if [ -s "$json_path" ]; then
    python3 - "$json_path" <<'PY' >> "$output_path"
import json
import sys
print(json.dumps(json.load(open(sys.argv[1])), sort_keys=True))
PY
  fi
}

echo "Collecting YAM Objaverse demos"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "BATCH_NAME=$BATCH_NAME"
echo "SHARD_INDEX=$SHARD_INDEX"
echo "SHARD_COUNT=$SHARD_COUNT"
echo "SHARD_TARGET=$SHARD_TARGET"
echo "TOTAL_TARGET=$TOTAL_TARGET"
echo "OBJECTS_PER_DEMO=$OBJECTS_PER_DEMO"
echo "POOL_MANIFEST=$POOL_MANIFEST"
echo "SHARD_DIR=$SHARD_DIR"

prepare_pool_manifest
json_event "collector_start" \
  "batch_name=$BATCH_NAME" \
  "shard_index=$SHARD_INDEX" \
  "shard_count=$SHARD_COUNT" \
  "shard_target=$SHARD_TARGET" \
  "code_commit=${CODE_COMMIT:-unknown}" \
  "pool_manifest=$POOL_MANIFEST"

accepted=0
attempt=0
while [ "$accepted" -lt "$SHARD_TARGET" ] && [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  seed="$((START_SEED + SHARD_INDEX * 100000 + attempt))"
  attempt_dir="$SHARD_DIR/attempt_seed_${seed}"
  mkdir -p "$attempt_dir"
  settle_run="${BATCH_NAME}_s$(printf '%03d' "$SHARD_INDEX")_seed${seed}_settle"
  replay_run="${BATCH_NAME}_s$(printf '%03d' "$SHARD_INDEX")_seed${seed}_replay"
  stable_scene_host="$RESULTS_NFS/validations/$settle_run/stable_scene.json"
  plan_dir_host="$attempt_dir/plan"
  trajectory_host="$plan_dir_host/trajectory.json"
  validation_host="$attempt_dir/validation_metrics.json"
  json_event "attempt_start" "seed=$seed" "attempt=$attempt" "accepted=$accepted"

  if ! run_settle "$seed" "$settle_run"; then
    json_event "attempt_rejected" "seed=$seed" "stage=settle" "settle_run=$settle_run"
    echo "{\"seed\":$seed,\"stage\":\"settle\",\"settle_run\":\"$settle_run\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi
  if [ ! -s "$stable_scene_host" ]; then
    json_event "attempt_rejected" "seed=$seed" "stage=stable_scene_missing" "settle_run=$settle_run"
    echo "{\"seed\":$seed,\"stage\":\"stable_scene_missing\",\"settle_run\":\"$settle_run\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi
  if ! run_planner "$seed" "$stable_scene_host" "$plan_dir_host"; then
    json_event "attempt_rejected" "seed=$seed" "stage=planner" "plan_dir=$plan_dir_host"
    echo "{\"seed\":$seed,\"stage\":\"planner\",\"plan_dir\":\"$plan_dir_host\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi
  if [ ! -s "$trajectory_host" ]; then
    json_event "attempt_rejected" "seed=$seed" "stage=trajectory_missing" "plan_dir=$plan_dir_host"
    echo "{\"seed\":$seed,\"stage\":\"trajectory_missing\",\"plan_dir\":\"$plan_dir_host\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi
  if ! run_replay "$seed" "$replay_run" "$stable_scene_host" "$trajectory_host"; then
    json_event "attempt_rejected" "seed=$seed" "stage=replay" "replay_run=$replay_run"
    echo "{\"seed\":$seed,\"stage\":\"replay\",\"replay_run\":\"$replay_run\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi
  if ! run_validate "$replay_run" "$stable_scene_host" "$validation_host"; then
    json_event "attempt_rejected" "seed=$seed" "stage=validation" "replay_run=$replay_run" "validation=$validation_host"
    echo "{\"seed\":$seed,\"stage\":\"validation\",\"replay_run\":\"$replay_run\",\"validation\":\"$validation_host\"}" >> "$REJECTED_JSONL"
    attempt="$((attempt + 1))"
    continue
  fi

  accepted="$((accepted + 1))"
  json_event "attempt_accepted" \
    "seed=$seed" \
    "accepted=$accepted" \
    "settle_run=$settle_run" \
    "replay_run=$replay_run" \
    "trajectory=$trajectory_host" \
    "validation=$validation_host"
  python3 - "$seed" "$settle_run" "$replay_run" "$stable_scene_host" "$trajectory_host" "$validation_host" "$RESULTS_NFS" <<'PY' >> "$ACCEPTED_JSONL"
import json
import sys
seed, settle, replay, stable, trajectory, validation, results_nfs = sys.argv[1:]
print(json.dumps({
    "seed": int(seed),
    "settle_run": settle,
    "replay_run": replay,
    "stable_scene": stable,
    "trajectory": trajectory,
    "dataset": f"{results_nfs}/validations/{replay}/trajectory_dataset.npz",
    "video": f"{results_nfs}/validations/{replay}/yam_pick_place.mp4",
    "validation": validation,
}, sort_keys=True))
PY
  record_json_file_line "$validation_host" "$SHARD_DIR/accepted_validation_metrics.jsonl"
  attempt="$((attempt + 1))"
done

status="completed"
if [ "$accepted" -lt "$SHARD_TARGET" ]; then
  status="incomplete"
fi
json_event "collector_done" "status=$status" "accepted=$accepted" "attempts=$attempt" "shard_target=$SHARD_TARGET"

python3 - "$SHARD_DIR/summary.json" <<PY
import json
from pathlib import Path
summary = {
    "status": "$status",
    "batch_name": "$BATCH_NAME",
    "shard_index": int("$SHARD_INDEX"),
    "shard_count": int("$SHARD_COUNT"),
    "shard_target": int("$SHARD_TARGET"),
    "accepted": int("$accepted"),
    "attempts": int("$attempt"),
    "events_jsonl": "$EVENTS_JSONL",
    "accepted_jsonl": "$ACCEPTED_JSONL",
    "rejected_jsonl": "$REJECTED_JSONL",
    "pool_manifest": "$POOL_MANIFEST",
    "code_commit": "${CODE_COMMIT:-unknown}",
}
path = Path("$SHARD_DIR/summary.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({"event": "summary_written", "path": str(path), "status": "$status"}))
PY

if [ "$status" != "completed" ]; then
  exit 1
fi
