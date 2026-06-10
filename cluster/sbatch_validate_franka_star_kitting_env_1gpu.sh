#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_star_val
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_star_%j.out

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

TASK="${TASK:-Dextrah-Franka-Star-Kitting}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_star_env_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-4}"
NUM_STEPS="${NUM_STEPS:-480}"
VIDEO_LENGTH="${VIDEO_LENGTH:-480}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
PRINT_INTERVAL="${PRINT_INTERVAL:-30}"
SEED="${SEED:-42}"
STAR_RESET_NEAR_HAND_PROBABILITY="${STAR_RESET_NEAR_HAND_PROBABILITY:-0.0}"
STAR_RESET_NEAR_HAND_X="${STAR_RESET_NEAR_HAND_X:--0.432}"
STAR_RESET_NEAR_HAND_Y="${STAR_RESET_NEAR_HAND_Y:-0.009}"
STAR_RESET_NEAR_HAND_XY_NOISE="${STAR_RESET_NEAR_HAND_XY_NOISE:-0.020}"

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_franka_star_${SLURM_JOB_ID_SAFE}.out"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH CAPTURE_VIDEO PRINT_INTERVAL SEED
export STAR_RESET_NEAR_HAND_PROBABILITY STAR_RESET_NEAR_HAND_X STAR_RESET_NEAR_HAND_Y STAR_RESET_NEAR_HAND_XY_NOISE
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka star-kitting environment validation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "NUM_STEPS=$NUM_STEPS"
echo "VIDEO_LENGTH=$VIDEO_LENGTH"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "SEED=$SEED"
echo "STAR_RESET_NEAR_HAND_PROBABILITY=$STAR_RESET_NEAR_HAND_PROBABILITY"
echo "STAR_RESET_NEAR_HAND_X=$STAR_RESET_NEAR_HAND_X"
echo "STAR_RESET_NEAR_HAND_Y=$STAR_RESET_NEAR_HAND_Y"
echo "STAR_RESET_NEAR_HAND_XY_NOISE=$STAR_RESET_NEAR_HAND_XY_NOISE"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "METRICS_CONTAINER=$METRICS_CONTAINER"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    mkdir -p "$RUN_DIR_CONTAINER" /results/logs

    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    echo "git_status_skipped=container_git_lfs_unavailable"
    nvidia-smi || true

    cd /code/dextrah_lab/rl_games
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH")
    fi

    VALIDATE_ARGS=(
      validate_franka_star_kitting_env.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --star_reset_near_hand_probability "$STAR_RESET_NEAR_HAND_PROBABILITY"
      --star_reset_near_hand_x "$STAR_RESET_NEAR_HAND_X"
      --star_reset_near_hand_y "$STAR_RESET_NEAR_HAND_Y"
      --star_reset_near_hand_xy_noise "$STAR_RESET_NEAR_HAND_XY_NOISE"
      "${VIDEO_ARGS[@]}"
    )

    printf "validate_command="
    printf "%q " /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected validation error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing validation metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" <<'PY'
import json
import sys

metrics_path = sys.argv[1]
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

if not bool(payload.get("passed", False)):
    failed = [
        record.get("name", "<unnamed>")
        for record in payload.get("checks", [])
        if not bool(record.get("passed", False))
    ]
    print(f"Validation metrics failed: {failed}")
    sys.exit(1)

print("Validation metrics passed")
PY

echo "Validation Done"
