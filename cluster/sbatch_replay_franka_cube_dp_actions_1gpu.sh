#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_dp_replay
#SBATCH --partition=batch
#SBATCH --time=0-00:30:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_dp_replay_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
STEPS="${STEPS:-8}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
POSE_ACTION_MULTIPLIER="${POSE_ACTION_MULTIPLIER:-1.0}"
ACTION_REPEAT="${ACTION_REPEAT:-1}"
PRINT_INTERVAL="${PRINT_INTERVAL:-1}"
SEED="${SEED:-42}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-False}"
VIDEO_LENGTH="${VIDEO_LENGTH:-80}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-dp-replay}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to an official Diffusion Policy .ckpt visible in the container.}"
DATASET="${DATASET:?Set DATASET to a converted lowdim NPZ visible in the container.}"
MODES="${MODES:-dataset_t,dp_replan}"
DEMO_RESET_DATASET="${DEMO_RESET_DATASET:-}"
DEMO_RESET_TRAJECTORY_JSON="${DEMO_RESET_TRAJECTORY_JSON:-}"
DEMO_RESET_EPISODE="${DEMO_RESET_EPISODE:-0}"
DEMO_RESET_STEP="${DEMO_RESET_STEP:-0}"
DATASET_START_ROW="${DATASET_START_ROW:--1}"
DATASET_START_EPISODE="${DATASET_START_EPISODE:--1}"
DATASET_START_STEP="${DATASET_START_STEP:-0}"

RUN_DIR_HOST="$RESULTS_NFS/replays/$RUN_NAME"
RUN_DIR_CONTAINER="/results/replays/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/replay_franka_cube_dp_actions_${SLURM_JOB_ID_SAFE}.out"

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
DATASET_HOST="$(host_path_from_container "$DATASET")"
CHECKPOINT_ARG="$(container_path_from_host "$CHECKPOINT")"
DATASET_ARG="$(container_path_from_host "$DATASET")"
if [ -n "$DEMO_RESET_DATASET" ]; then
  DEMO_RESET_DATASET_HOST="$(host_path_from_container "$DEMO_RESET_DATASET")"
  DEMO_RESET_DATASET_ARG="$(container_path_from_host "$DEMO_RESET_DATASET")"
else
  DEMO_RESET_DATASET_HOST=""
  DEMO_RESET_DATASET_ARG=""
fi
if [ -n "$DEMO_RESET_TRAJECTORY_JSON" ]; then
  DEMO_RESET_TRAJECTORY_JSON_HOST="$(host_path_from_container "$DEMO_RESET_TRAJECTORY_JSON")"
  DEMO_RESET_TRAJECTORY_JSON_ARG="$(container_path_from_host "$DEMO_RESET_TRAJECTORY_JSON")"
else
  DEMO_RESET_TRAJECTORY_JSON_HOST=""
  DEMO_RESET_TRAJECTORY_JSON_ARG=""
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
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ ! -f "$DATASET_HOST" ]; then
  echo "Missing dataset: $DATASET_HOST"
  exit 2
fi
if [ -n "$DEMO_RESET_DATASET_HOST" ] && [ ! -f "$DEMO_RESET_DATASET_HOST" ]; then
  echo "Missing demo reset dataset: $DEMO_RESET_DATASET_HOST"
  exit 2
fi
if [ -n "$DEMO_RESET_TRAJECTORY_JSON_HOST" ] && [ ! -f "$DEMO_RESET_TRAJECTORY_JSON_HOST" ]; then
  echo "Missing demo reset trajectory JSON: $DEMO_RESET_TRAJECTORY_JSON_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS STEPS NUM_INFERENCE_STEPS CLIP_ACTIONS PRINT_INTERVAL SEED
export POSE_ACTION_MULTIPLIER ACTION_REPEAT
export CAPTURE_VIDEO VIDEO_LENGTH VIDEO_NAME_PREFIX
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export CHECKPOINT_ARG DATASET_ARG RUN_DIR_CONTAINER ENV_NAME OFFICIAL_DP_ENV_NAME MODES
export DEMO_RESET_DATASET_ARG DEMO_RESET_TRAJECTORY_JSON_ARG DEMO_RESET_EPISODE DEMO_RESET_STEP
export DATASET_START_ROW DATASET_START_EPISODE DATASET_START_STEP

echo "Running DextrAH Franka cube DP dataset-action replay"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "NUM_ENVS=$NUM_ENVS"
echo "STEPS=$STEPS"
echo "NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS"
echo "POSE_ACTION_MULTIPLIER=$POSE_ACTION_MULTIPLIER"
echo "ACTION_REPEAT=$ACTION_REPEAT"
echo "MODES=$MODES"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
echo "DATASET_ARG=$DATASET_ARG"
echo "DATASET_HOST=$DATASET_HOST"
echo "DEMO_RESET_DATASET_ARG=${DEMO_RESET_DATASET_ARG:-}"
echo "DEMO_RESET_DATASET_HOST=${DEMO_RESET_DATASET_HOST:-}"
echo "DEMO_RESET_TRAJECTORY_JSON_ARG=${DEMO_RESET_TRAJECTORY_JSON_ARG:-}"
echo "DEMO_RESET_TRAJECTORY_JSON_HOST=${DEMO_RESET_TRAJECTORY_JSON_HOST:-}"
echo "DEMO_RESET_EPISODE=$DEMO_RESET_EPISODE"
echo "DEMO_RESET_STEP=$DEMO_RESET_STEP"
echo "DATASET_START_ROW=$DATASET_START_ROW"
echo "DATASET_START_EPISODE=$DATASET_START_EPISODE"
echo "DATASET_START_STEP=$DATASET_START_STEP"

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
    export PYTHONPATH="$SITE:/code:/fabrics/src:/official_dp"
    if [ -d "$DP_SITE" ]; then
      export PYTHONPATH="$DP_SITE:$PYTHONPATH"
    fi
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
    mkdir -p "$RUN_DIR_CONTAINER"

    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    MODE_ARGS=()
    IFS=, read -ra MODE_LIST <<< "$MODES"
    for mode in "${MODE_LIST[@]}"; do
      MODE_ARGS+=(--mode "$mode")
    done
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    DEMO_RESET_ARGS=()
    if [ -n "${DEMO_RESET_DATASET_ARG:-}" ]; then
      DEMO_RESET_ARGS=(
        --demo_reset_dataset "$DEMO_RESET_DATASET_ARG"
        --demo_reset_episode "$DEMO_RESET_EPISODE"
        --demo_reset_step "$DEMO_RESET_STEP"
      )
      if [ -n "${DEMO_RESET_TRAJECTORY_JSON_ARG:-}" ]; then
        DEMO_RESET_ARGS+=(--demo_reset_trajectory_json "$DEMO_RESET_TRAJECTORY_JSON_ARG")
      fi
    fi
    DATASET_START_ARGS=()
    if [ "$DATASET_START_ROW" -ge 0 ]; then
      DATASET_START_ARGS=(--dataset_start_row "$DATASET_START_ROW")
    elif [ "$DATASET_START_EPISODE" -ge 0 ]; then
      DATASET_START_ARGS=(
        --dataset_start_episode "$DATASET_START_EPISODE"
        --dataset_start_step "$DATASET_START_STEP"
      )
    fi
    REPLAY_ARGS=(
      /code/dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py
      --headless
      --device cuda:0
      --task "$TASK"
      --dataset "$DATASET_ARG"
      --checkpoint "$CHECKPOINT_ARG"
      --diffusion_policy_root /official_dp
      --num_envs "$NUM_ENVS"
      --steps "$STEPS"
      --seed "$SEED"
      --num_inference_steps "$NUM_INFERENCE_STEPS"
      --clip_actions "$CLIP_ACTIONS"
      --pose_action_multiplier "$POSE_ACTION_MULTIPLIER"
      --action_repeat "$ACTION_REPEAT"
      --output_dir "$RUN_DIR_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      "${MODE_ARGS[@]}"
      "${VIDEO_ARGS[@]}"
      "${DEMO_RESET_ARGS[@]}"
      "${DATASET_START_ARGS[@]}"
    )
    printf "replay_command="
    printf "%q " /isaac-sim/python.sh "${REPLAY_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${REPLAY_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|FRANKA_CUBE_DP_DATASET_REPLAY_FAILED" "$LOG_FILE" >/dev/null; then
  echo "Detected replay error patterns in $LOG_FILE."
  exit 1
fi

for artifact in replay_summary.json replay_steps.csv replay_report.md replay_motion.png; do
  if [ ! -s "$RUN_DIR_HOST/$artifact" ]; then
    echo "Missing replay artifact: $RUN_DIR_HOST/$artifact"
    exit 1
  fi
done

echo "DP_REPLAY_DONE run_dir=$RUN_DIR_HOST"
