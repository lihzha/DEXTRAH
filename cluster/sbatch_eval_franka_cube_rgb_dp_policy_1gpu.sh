#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_rgb_dp_eval
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_rgb_dp_policy_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
OFFICIAL_DP_NFS="${OFFICIAL_DP_NFS:-$NFS_ROOT/src/external/real-stanford-diffusion_policy}"
OFFICIAL_DP_ENV_NAME="${OFFICIAL_DP_ENV_NAME:-franka-cube-dp-bc-warmstart-official-dp}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
TASK="${TASK:-Dextrah-Franka-Cube-Grasp}"
RUN_NAME="${RUN_NAME:-franka_cube_rgb_dp_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_STEPS="${NUM_STEPS:-320}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
NUM_ACTION_SAMPLES="${NUM_ACTION_SAMPLES:-1}"
POLICY_SAMPLE_SEED="${POLICY_SAMPLE_SEED:-}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-8}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
SUCCESS_WINDOW="${SUCCESS_WINDOW:-80}"
SUCCESS_TIMEOUT_OVERRIDE="${SUCCESS_TIMEOUT_OVERRIDE:-}"
IMAGE_HEIGHT="${IMAGE_HEIGHT:-96}"
IMAGE_WIDTH="${IMAGE_WIDTH:-96}"
VIDEO_LENGTH="${VIDEO_LENGTH:-320}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-rgb-dp-eval}"
PRINT_INTERVAL="${PRINT_INTERVAL:-20}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-False}"
SEED="${SEED:-42}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to an official image Diffusion Policy .ckpt path.}"
DEMO_RESET_DATASET="${DEMO_RESET_DATASET:-}"
DEMO_RESET_EPISODE="${DEMO_RESET_EPISODE:-0}"
DEMO_RESET_STEP="${DEMO_RESET_STEP:-0}"
DEMO_RESET_CUBE_POS_BLEND_ALPHA="${DEMO_RESET_CUBE_POS_BLEND_ALPHA:-1.0}"
APPEND_PHASE_PROGRESS="${APPEND_PHASE_PROGRESS:-False}"
PHASE_PROGRESS_DATASET="${PHASE_PROGRESS_DATASET:-}"
PHASE_PROGRESS_EPISODE="${PHASE_PROGRESS_EPISODE:-0}"
PHASE_PROGRESS_START_STEP="${PHASE_PROGRESS_START_STEP:-0}"

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_franka_cube_rgb_dp_policy_${SLURM_JOB_ID_SAFE}.out"

host_path_from_container() {
  local path="$1"
  if [[ "$path" == /results/* ]]; then
    echo "$RESULTS_NFS/${path#/results/}"
  else
    echo "$path"
  fi
}

container_path_from_host() {
  local path="$1"
  if [[ "$path" == "$RESULTS_NFS"/* ]]; then
    echo "/results/${path#$RESULTS_NFS/}"
  else
    echo "$path"
  fi
}

CHECKPOINT_HOST="$(host_path_from_container "$CHECKPOINT")"
CHECKPOINT_ARG="$(container_path_from_host "$CHECKPOINT")"
DEMO_RESET_DATASET_HOST="$DEMO_RESET_DATASET"
DEMO_RESET_DATASET_ARG="$DEMO_RESET_DATASET"
if [ -n "$DEMO_RESET_DATASET" ]; then
  DEMO_RESET_DATASET_HOST="$(host_path_from_container "$DEMO_RESET_DATASET")"
  DEMO_RESET_DATASET_ARG="$(container_path_from_host "$DEMO_RESET_DATASET")"
fi
PHASE_PROGRESS_DATASET_HOST="$PHASE_PROGRESS_DATASET"
PHASE_PROGRESS_DATASET_ARG="$PHASE_PROGRESS_DATASET"
if [ -n "$PHASE_PROGRESS_DATASET" ]; then
  PHASE_PROGRESS_DATASET_HOST="$(host_path_from_container "$PHASE_PROGRESS_DATASET")"
  PHASE_PROGRESS_DATASET_ARG="$(container_path_from_host "$PHASE_PROGRESS_DATASET")"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -d "$OFFICIAL_DP_NFS/diffusion_policy" ]; then
  echo "Missing official Diffusion Policy checkout: $OFFICIAL_DP_NFS"
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing RGB Diffusion Policy checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ -n "$DEMO_RESET_DATASET" ] && [ ! -f "$DEMO_RESET_DATASET_HOST" ]; then
  echo "Missing demo reset dataset: $DEMO_RESET_DATASET_HOST"
  exit 2
fi
if [ "$APPEND_PHASE_PROGRESS" = "True" ] && [ -z "$PHASE_PROGRESS_DATASET" ]; then
  echo "APPEND_PHASE_PROGRESS=True requires PHASE_PROGRESS_DATASET"
  exit 2
fi
if [ -n "$PHASE_PROGRESS_DATASET" ] && [ ! -f "$PHASE_PROGRESS_DATASET_HOST" ]; then
  echo "Missing phase/progress dataset: $PHASE_PROGRESS_DATASET_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS NUM_INFERENCE_STEPS NUM_ACTION_SAMPLES POLICY_SAMPLE_SEED
export ACTION_CHUNK_STEPS CLIP_ACTIONS SUCCESS_WINDOW SUCCESS_TIMEOUT_OVERRIDE
export IMAGE_HEIGHT IMAGE_WIDTH VIDEO_LENGTH VIDEO_NAME_PREFIX PRINT_INTERVAL CAPTURE_VIDEO SEED
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export CHECKPOINT_ARG RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME OFFICIAL_DP_ENV_NAME
export DEMO_RESET_DATASET_ARG DEMO_RESET_EPISODE DEMO_RESET_STEP DEMO_RESET_CUBE_POS_BLEND_ALPHA
export APPEND_PHASE_PROGRESS PHASE_PROGRESS_DATASET_ARG PHASE_PROGRESS_EPISODE PHASE_PROGRESS_START_STEP

echo "Running DextrAH Franka cube RGB Diffusion Policy evaluation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "NUM_ENVS=$NUM_ENVS NUM_STEPS=$NUM_STEPS"
echo "NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS NUM_ACTION_SAMPLES=$NUM_ACTION_SAMPLES"
echo "POLICY_SAMPLE_SEED=$POLICY_SAMPLE_SEED"
echo "ACTION_CHUNK_STEPS=$ACTION_CHUNK_STEPS CLIP_ACTIONS=$CLIP_ACTIONS"
echo "IMAGE_HEIGHT=$IMAGE_HEIGHT IMAGE_WIDTH=$IMAGE_WIDTH"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO VIDEO_LENGTH=$VIDEO_LENGTH VIDEO_NAME_PREFIX=$VIDEO_NAME_PREFIX"
echo "SEED=$SEED"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
if [ -n "$DEMO_RESET_DATASET" ]; then
  echo "DEMO_RESET_DATASET_ARG=$DEMO_RESET_DATASET_ARG"
  echo "DEMO_RESET_DATASET_HOST=$DEMO_RESET_DATASET_HOST"
  echo "DEMO_RESET_EPISODE=$DEMO_RESET_EPISODE DEMO_RESET_STEP=$DEMO_RESET_STEP"
  echo "DEMO_RESET_CUBE_POS_BLEND_ALPHA=$DEMO_RESET_CUBE_POS_BLEND_ALPHA"
fi
echo "APPEND_PHASE_PROGRESS=$APPEND_PHASE_PROGRESS"
if [ -n "$PHASE_PROGRESS_DATASET" ]; then
  echo "PHASE_PROGRESS_DATASET_ARG=$PHASE_PROGRESS_DATASET_ARG"
  echo "PHASE_PROGRESS_DATASET_HOST=$PHASE_PROGRESS_DATASET_HOST"
  echo "PHASE_PROGRESS_EPISODE=$PHASE_PROGRESS_EPISODE PHASE_PROGRESS_START_STEP=$PHASE_PROGRESS_START_STEP"
fi
echo "METRICS_CONTAINER=$METRICS_CONTAINER"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export DP_SITE="/envs/$OFFICIAL_DP_ENV_NAME/site"
    export PYTHONPATH="$SITE:$DP_SITE:/code:/fabrics/src:/official_dp"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    mkdir -p "$RUN_DIR_CONTAINER"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    SUCCESS_TIMEOUT_ARGS=()
    if [ -n "$SUCCESS_TIMEOUT_OVERRIDE" ]; then
      SUCCESS_TIMEOUT_ARGS=(--success_timeout_override "$SUCCESS_TIMEOUT_OVERRIDE")
    fi
    POLICY_SEED_ARGS=()
    if [ -n "$POLICY_SAMPLE_SEED" ]; then
      POLICY_SEED_ARGS=(--policy_sample_seed "$POLICY_SAMPLE_SEED")
    fi
    DEMO_RESET_ARGS=()
    if [ -n "$DEMO_RESET_DATASET_ARG" ]; then
      DEMO_RESET_ARGS=(
        --demo_reset_dataset "$DEMO_RESET_DATASET_ARG"
        --demo_reset_episode "$DEMO_RESET_EPISODE"
        --demo_reset_step "$DEMO_RESET_STEP"
        --demo_reset_cube_pos_blend_alpha "$DEMO_RESET_CUBE_POS_BLEND_ALPHA"
      )
    fi
    PHASE_PROGRESS_ARGS=()
    if [ "$APPEND_PHASE_PROGRESS" = "True" ]; then
      PHASE_PROGRESS_ARGS=(
        --append_phase_progress
        --phase_progress_dataset "$PHASE_PROGRESS_DATASET_ARG"
        --phase_progress_episode "$PHASE_PROGRESS_EPISODE"
        --phase_progress_start_step "$PHASE_PROGRESS_START_STEP"
      )
    fi

    EVAL_ARGS=(
      /code/dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py
      --headless
      --device cuda:0
      --task "$TASK"
      --checkpoint "$CHECKPOINT_ARG"
      --diffusion_policy_root /official_dp
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --num_inference_steps "$NUM_INFERENCE_STEPS"
      --num_action_samples "$NUM_ACTION_SAMPLES"
      "${POLICY_SEED_ARGS[@]}"
      --action_chunk_steps "$ACTION_CHUNK_STEPS"
      --clip_actions "$CLIP_ACTIONS"
      --success_window "$SUCCESS_WINDOW"
      "${SUCCESS_TIMEOUT_ARGS[@]}"
      --image_height "$IMAGE_HEIGHT"
      --image_width "$IMAGE_WIDTH"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      "${DEMO_RESET_ARGS[@]}"
      "${PHASE_PROGRESS_ARGS[@]}"
      "${VIDEO_ARGS[@]}"
    )
    printf "rgb_eval_command="
    printf "%q " /isaac-sim/python.sh "${EVAL_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${EVAL_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|FRANKA_CUBE_RGB_DP_POLICY_EVAL_FAILED" "$LOG_FILE" >/dev/null; then
  echo "Detected RGB DP eval error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing RGB DP eval metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" "$NUM_STEPS" <<'PY'
import json
import math
import sys

metrics_path = sys.argv[1]
requested_steps = int(sys.argv[2])
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)
summary = payload.get("summary", {})
if not bool(summary.get("env_closed", False)):
    raise SystemExit("RGB DP eval env did not close cleanly")
if int(summary.get("steps_completed", 0)) < requested_steps:
    raise SystemExit(f"RGB DP eval completed {summary.get('steps_completed')} steps, expected {requested_steps}")
if bool(summary.get("privileged_object_state_in_policy", True)):
    raise SystemExit("RGB DP metrics did not confirm object-state-free policy obs")
for key in ("action_min", "action_max"):
    values = summary.get(key)
    if not isinstance(values, list) or len(values) != 7:
        raise SystemExit(f"Bad {key}: {values}")
    if not all(math.isfinite(float(v)) for v in values):
        raise SystemExit(f"Non-finite {key}: {values}")
print("RGB DP eval metrics passed")
PY

if [ "$CAPTURE_VIDEO" = "True" ] && ! find "$RUN_DIR_HOST/videos" -type f -name "*.mp4" -print -quit 2>/dev/null | grep -q .; then
  echo "Missing RGB DP eval video in $RUN_DIR_HOST/videos"
  exit 1
fi

echo "RGB DP Evaluation Done"
