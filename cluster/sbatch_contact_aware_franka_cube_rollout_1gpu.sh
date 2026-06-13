#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_contact_rollout
#SBATCH --partition=batch
#SBATCH --time=0-00:25:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
TASK="${TASK:-Dextrah-Franka-Cube-Grasp}"
RUN_NAME="${RUN_NAME:-franka_cube_contact_rollout_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
EPISODE="${EPISODE:-24}"
EPISODE_STEP="${EPISODE_STEP:-260}"
SEED="${SEED:-42}"
DATASET="${DATASET:?Set DATASET to a converted lowdim NPZ visible in the container.}"
TRAJECTORY_JSON="${TRAJECTORY_JSON:?Set TRAJECTORY_JSON to the raw source trajectory JSON visible in the container.}"
VARIANTS="${VARIANTS:-center,center_high15,center_high30}"
VARIANT_COUNT="${VARIANT_COUNT:-0}"
ALIGN_STEPS="${ALIGN_STEPS:-80}"
CLOSE_STEPS="${CLOSE_STEPS:-80}"
LIFT_STEPS="${LIFT_STEPS:-120}"
LIFT_HEIGHT="${LIFT_HEIGHT:-0.14}"
FINGER_GAIN="${FINGER_GAIN:-0.75}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
PRINT_INTERVAL="${PRINT_INTERVAL:-40}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
VIDEO_LENGTH="${VIDEO_LENGTH:-280}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-contact-rollout}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"

RUN_DIR_HOST="$RESULTS_NFS/contact_rollouts/$RUN_NAME"
RUN_DIR_CONTAINER="/results/contact_rollouts/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/contact_aware_franka_cube_rollout_${SLURM_JOB_ID_SAFE}.out"

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

DATASET_HOST="$(host_path_from_container "$DATASET")"
TRAJECTORY_JSON_HOST="$(host_path_from_container "$TRAJECTORY_JSON")"
DATASET_ARG="$(container_path_from_host "$DATASET")"
TRAJECTORY_JSON_ARG="$(container_path_from_host "$TRAJECTORY_JSON")"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$DATASET_HOST" ]; then
  echo "Missing dataset: $DATASET_HOST"
  exit 2
fi
if [ ! -f "$TRAJECTORY_JSON_HOST" ]; then
  echo "Missing trajectory JSON: $TRAJECTORY_JSON_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME EPISODE EPISODE_STEP SEED DATASET_ARG TRAJECTORY_JSON_ARG
export VARIANTS VARIANT_COUNT ALIGN_STEPS CLOSE_STEPS LIFT_STEPS LIFT_HEIGHT FINGER_GAIN CLIP_ACTIONS PRINT_INTERVAL
export CAPTURE_VIDEO VIDEO_LENGTH VIDEO_NAME_PREFIX RUN_DIR_CONTAINER ENV_NAME
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z

echo "Running DextrAH Franka cube contact-aware rollout smoke"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "EPISODE=$EPISODE"
echo "EPISODE_STEP=$EPISODE_STEP"
echo "VARIANTS=$VARIANTS"
echo "VARIANT_COUNT=$VARIANT_COUNT"
if [ "$VARIANT_COUNT" -gt 0 ]; then
  for ((i=0; i<VARIANT_COUNT; i++)); do
    name="VARIANT_$i"
    echo "$name=${!name:-}"
    if [ -z "${!name:-}" ]; then
      echo "Missing required $name while VARIANT_COUNT=$VARIANT_COUNT"
      exit 2
    fi
    export "$name"
  done
fi
echo "ALIGN_STEPS=$ALIGN_STEPS CLOSE_STEPS=$CLOSE_STEPS LIFT_STEPS=$LIFT_STEPS"
echo "LIFT_HEIGHT=$LIFT_HEIGHT FINGER_GAIN=$FINGER_GAIN CLIP_ACTIONS=$CLIP_ACTIONS"
echo "DATASET_ARG=$DATASET_ARG"
echo "DATASET_HOST=$DATASET_HOST"
echo "TRAJECTORY_JSON_ARG=$TRAJECTORY_JSON_ARG"
echo "TRAJECTORY_JSON_HOST=$TRAJECTORY_JSON_HOST"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    mkdir -p "$RUN_DIR_CONTAINER"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    nvidia-smi || true

    VARIANT_ARGS=()
    if [ "${VARIANT_COUNT:-0}" -gt 0 ]; then
      for ((i=0; i<VARIANT_COUNT; i++)); do
        name="VARIANT_$i"
        variant="${!name:-}"
        if [ -z "$variant" ]; then
          echo "Missing $name while VARIANT_COUNT=$VARIANT_COUNT"
          exit 2
        fi
        VARIANT_ARGS+=(--variant "$variant")
      done
    else
      IFS=, read -ra VARIANT_LIST <<< "$VARIANTS"
      for variant in "${VARIANT_LIST[@]}"; do
        VARIANT_ARGS+=(--variant "$variant")
      done
    fi
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    CMD=(
      /code/dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py
      --headless
      --device cuda:0
      --task "$TASK"
      --dataset "$DATASET_ARG"
      --trajectory_json "$TRAJECTORY_JSON_ARG"
      --episode "$EPISODE"
      --episode_step "$EPISODE_STEP"
      --seed "$SEED"
      --align_steps "$ALIGN_STEPS"
      --close_steps "$CLOSE_STEPS"
      --lift_steps "$LIFT_STEPS"
      --lift_height "$LIFT_HEIGHT"
      --finger_gain "$FINGER_GAIN"
      --clip_actions "$CLIP_ACTIONS"
      --output_dir "$RUN_DIR_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      "${VARIANT_ARGS[@]}"
      "${VIDEO_ARGS[@]}"
    )
    printf "contact_rollout_command="
    printf "%q " /isaac-sim/python.sh "${CMD[@]}"
    printf "\n"
    /isaac-sim/python.sh "${CMD[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|FRANKA_CUBE_CONTACT_ROLLOUT_FAILED" "$LOG_FILE" >/dev/null; then
  echo "Detected contact-aware rollout error patterns in $LOG_FILE."
  exit 1
fi

for artifact in contact_rollout_summary.json contact_rollout_steps.csv contact_rollout_report.md contact_rollout_plot.png; do
  if [ ! -s "$RUN_DIR_HOST/$artifact" ]; then
    echo "Missing contact rollout artifact: $RUN_DIR_HOST/$artifact"
    exit 1
  fi
done

if [ "$CAPTURE_VIDEO" = "True" ] && ! find "$RUN_DIR_HOST/videos" -maxdepth 1 -type f -name "*.mp4" -print -quit 2>/dev/null | grep -q .; then
  echo "Missing contact rollout video in $RUN_DIR_HOST/videos"
  exit 1
fi

echo "CONTACT_AWARE_FRANKA_CUBE_ROLLOUT_DONE run_dir=$RUN_DIR_HOST"
