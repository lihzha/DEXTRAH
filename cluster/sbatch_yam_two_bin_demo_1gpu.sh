#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_two_bin_demo
#SBATCH --partition=batch
#SBATCH --time=0-02:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_two_bin_demo_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
GRASPGENX_NFS="${GRASPGENX_NFS:-$NFS_ROOT/src/graspgenx}"
CUROBO_NFS="${CUROBO_NFS:-$NFS_ROOT/src/curobo}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
GRASPGENX_VENV_NAME="${GRASPGENX_VENV_NAME:-graspgenx-py312}"
GRASPGENX_IMAGE="${GRASPGENX_IMAGE:-$NFS_ROOT/cache/graspgenx_ngc2503_base.sqsh}"
ISAAC_IMAGE="${ISAAC_IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ROBOLAB_NFS="${ROBOLAB_NFS:-$NFS_ROOT/src/RoboLab}"
PIP_CACHE_NFS="${PIP_CACHE_NFS:-$NFS_ROOT/cache/pip}"
ISAAC_CACHE_NFS="${ISAAC_CACHE_NFS:-$NFS_ROOT/isaac_cache}"

TASK="${TASK:-Dextrah-Single-YAM-Two-Bin-Primitive-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_two_bin_demo_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%dT%H%M%SZ)}"
DEMO_DIR="${DEMO_DIR:-$RESULTS_NFS/yam_two_bin_demo/$RUN_NAME}"
EVENTS_JSONL="$DEMO_DIR/events.jsonl"
SUMMARY_JSON="$DEMO_DIR/summary.json"

SEED="${SEED:-62022}"
SETTLE_STEPS="${SETTLE_STEPS:-120}"
SETTLE_CAPTURE_INTERVAL="${SETTLE_CAPTURE_INTERVAL:-10}"
REPLAY_CAPTURE_INTERVAL="${REPLAY_CAPTURE_INTERVAL:-4}"
FPS="${FPS:-12}"
DEMO_STEPS="${DEMO_STEPS:-1500}"
NUM_GRASPS="${NUM_GRASPS:-160}"
TOPK="${TOPK:-80}"
MAX_PLAN_ATTEMPTS="${MAX_PLAN_ATTEMPTS:-80}"
SCRIPTED_LIFT_HEIGHT="${SCRIPTED_LIFT_HEIGHT:-0.14}"
SCRIPTED_LIFT_FRAMES="${SCRIPTED_LIFT_FRAMES:-220}"
MOVE_TO_BIN_FRAMES="${MOVE_TO_BIN_FRAMES:-320}"
DROP_HEIGHT_ABOVE_BIN="${DROP_HEIGHT_ABOVE_BIN:-0.18}"

CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

mkdir -p "$DEMO_DIR" "$NFS_ROOT/slurm_logs/dextrah" "$PIP_CACHE_NFS"

json_event() {
  local event="$1"
  shift
  python3 - "$event" "$@" <<'PY' | tee -a "$EVENTS_JSONL"
import json
import sys
payload = {"event": sys.argv[1]}
for pair in sys.argv[2:]:
    key, _, value = pair.partition("=")
    payload[key] = value
print(json.dumps(payload, sort_keys=True))
PY
}

host_to_container() {
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

run_render_wrapper() {
  bash "$CODE_NFS/cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh"
}

run_settle() {
  local run_name="$1"
  RUN_NAME="$run_name" \
  TASK="$TASK" \
  NUM_ENVS=1 \
  SEED="$SEED" \
  SETTLE_STEPS="$SETTLE_STEPS" \
  CAPTURE_INTERVAL="$SETTLE_CAPTURE_INTERVAL" \
  FPS="$FPS" \
  DEMO_MODE=settle \
  DEMO_STEPS="$SETTLE_STEPS" \
  VIDEO_FILENAME=settle.mp4 \
  CODE_NFS="$CODE_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  ENV_NAME="$ENV_NAME" \
  run_render_wrapper
}

run_planner() {
  local stable_scene_host="$1"
  local plan_dir_host="$2"
  local stable_scene_container
  local plan_dir_container
  stable_scene_container="$(host_to_container "$stable_scene_host")"
  plan_dir_container="$(host_to_container "$plan_dir_host")"
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
        --seed '$SEED' \
        --object_order target \
        --max_objects 1 \
        --num_grasps '$NUM_GRASPS' \
        --topk '$TOPK' \
        --max_plan_attempts '$MAX_PLAN_ATTEMPTS' \
        --move_to_bin_frames '$MOVE_TO_BIN_FRAMES' \
        --drop_height_above_bin '$DROP_HEIGHT_ABOVE_BIN' \
        --scripted_bin_drop_y_offset 0.0 \
        --scripted_place_mode always \
        --scripted_lift_mode always \
        --scripted_lift_height '$SCRIPTED_LIFT_HEIGHT' \
        --scripted_lift_frames '$SCRIPTED_LIFT_FRAMES'
    "
}

run_replay() {
  local run_name="$1"
  local video_filename="$2"
  local stable_scene_host="$3"
  local trajectory_host="$4"
  local camera_eye="$5"
  local camera_target="$6"
  local record_dataset="$7"
  RUN_NAME="$run_name" \
  TASK="$TASK" \
  NUM_ENVS=1 \
  SEED="$SEED" \
  DEMO_MODE=single_yam_trajectory \
  DEMO_STEPS="$DEMO_STEPS" \
  CAPTURE_INTERVAL="$REPLAY_CAPTURE_INTERVAL" \
  FPS="$FPS" \
  VIDEO_FILENAME="$video_filename" \
  DEMO_TRAJECTORY_PATH="$trajectory_host" \
  DEMO_TRAJECTORY_SOURCE=graspgenx_replay \
  DEMO_TRAJECTORY_REPLAY_MODE=dynamic \
  DEMO_TRAJECTORY_TIMING_MODE=realtime \
  DEMO_TRAJECTORY_VELOCITY_TARGETS=True \
  DEMO_TRAJECTORY_VELOCITY_TARGET_SCALE=1.0 \
  DEMO_START_BLEND_STEPS=36 \
  STABLE_SCENE_PATH="$stable_scene_host" \
  RECORD_TRAJECTORY_DATASET="$record_dataset" \
  TRAJECTORY_DATASET_PATH="$RESULTS_NFS/validations/$run_name/trajectory_dataset.npz" \
  CAMERA_EYE="$camera_eye" \
  CAMERA_TARGET="$camera_target" \
  CODE_NFS="$CODE_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  ENV_NAME="$ENV_NAME" \
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
  stable_scene_container="$(host_to_container "$stable_scene_host")"
  validation_container="$(host_to_container "$validation_host")"
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
        --expected_objects 1
    "
}

run_compose() {
  local left_host="$1"
  local right_host="$2"
  local output_host="$3"
  mkdir -p "$(dirname "$output_host")" "$ISAAC_CACHE_NFS/kit" "$ISAAC_CACHE_NFS/ov" "$ISAAC_CACHE_NFS/pip"
  srun \
    --ntasks=1 \
    --container-image="$ISAAC_IMAGE" \
    --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ROBOLAB_NFS":/home/lzha/code/RoboLab,"$ENV_NFS":/envs,"$RESULTS_NFS":/results,"$ISAAC_CACHE_NFS/kit":/isaac-sim/kit/cache,"$ISAAC_CACHE_NFS/ov":/root/.cache/ov,"$ISAAC_CACHE_NFS/pip":/root/.cache/pip \
    --no-container-entrypoint \
    --container-remap-root \
    --container-writable \
    --export=ALL,PYTHONUNBUFFERED=1 \
    bash -lc "
      set -euo pipefail
      export PYTHONPATH=/code:\${PYTHONPATH:-}
      /envs/$ENV_NAME/bin/python /code/dextrah_lab/scene_scripts/compose_two_view_video.py \
        --left '$(host_to_container "$left_host")' \
        --right '$(host_to_container "$right_host")' \
        --output '$(host_to_container "$output_host")' \
        --fps '$FPS' \
        --left_label 'default scene camera' \
        --right_label 'top-down camera'
    "
}

echo "Running YAM two-bin GraspGen-X + cuRobo demo"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "DEMO_DIR=$DEMO_DIR"

json_event "demo_start" "run_name=$RUN_NAME" "task=$TASK" "seed=$SEED" "code_commit=${CODE_COMMIT:-unknown}"

settle_run="${RUN_NAME}_settle"
default_run="${RUN_NAME}_default"
topdown_run="${RUN_NAME}_topdown"
stable_scene_host="$RESULTS_NFS/validations/$settle_run/stable_scene.json"
plan_dir_host="$DEMO_DIR/plan"
trajectory_host="$plan_dir_host/trajectory.json"
overlay_host="$plan_dir_host/grasp_pose_overlay.json"
default_video_host="$RESULTS_NFS/validations/$default_run/default_view.mp4"
topdown_video_host="$RESULTS_NFS/validations/$topdown_run/topdown_view.mp4"
validation_host="$DEMO_DIR/validation_metrics.json"
final_video_host="$DEMO_DIR/yam_two_bin_two_view.mp4"

json_event "settle_start" "run=$settle_run"
run_settle "$settle_run"
test -s "$stable_scene_host"
json_event "settle_done" "stable_scene=$stable_scene_host"

json_event "planner_start" "stable_scene=$stable_scene_host" "plan_dir=$plan_dir_host"
run_planner "$stable_scene_host" "$plan_dir_host"
test -s "$trajectory_host"
json_event "planner_done" "trajectory=$trajectory_host"

json_event "replay_default_start" "run=$default_run"
run_replay "$default_run" default_view.mp4 "$stable_scene_host" "$trajectory_host" "" "" True
test -s "$default_video_host"
json_event "replay_default_done" "video=$default_video_host"

json_event "validate_start" "replay_run=$default_run"
run_validate "$default_run" "$stable_scene_host" "$validation_host"
test -s "$validation_host"
json_event "validate_done" "validation=$validation_host"

json_event "replay_topdown_start" "run=$topdown_run"
run_replay "$topdown_run" topdown_view.mp4 "$stable_scene_host" "$trajectory_host" "-0.30 0.00 1.05" "-0.30 0.00 0.02" False
test -s "$topdown_video_host"
json_event "replay_topdown_done" "video=$topdown_video_host"

json_event "compose_start" "left=$default_video_host" "right=$topdown_video_host" "output=$final_video_host"
run_compose "$default_video_host" "$topdown_video_host" "$final_video_host"
test -s "$final_video_host"
json_event "compose_done" "video=$final_video_host"

python3 - "$SUMMARY_JSON" <<PY
import json
from pathlib import Path
summary = {
    "status": "completed",
    "task": "$TASK",
    "run_name": "$RUN_NAME",
    "seed": int("$SEED"),
    "code_commit": "${CODE_COMMIT:-unknown}",
    "demo_dir": "$DEMO_DIR",
    "stable_scene": "$stable_scene_host",
    "plan_dir": "$plan_dir_host",
    "trajectory": "$trajectory_host",
    "grasp_pose_overlay": "$overlay_host",
    "default_video": "$default_video_host",
    "topdown_video": "$topdown_video_host",
    "final_two_view_video": "$final_video_host",
    "validation": "$validation_host",
    "events_jsonl": "$EVENTS_JSONL",
}
path = Path("$SUMMARY_JSON")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({"event": "summary_written", "path": str(path), "final_two_view_video": "$final_video_host"}))
PY

json_event "demo_done" "summary=$SUMMARY_JSON" "final_video=$final_video_host"
