#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_yam_cube_val
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_bimanual_yam_cube_%j.out

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

TASK="${TASK:-Dextrah-Bimanual-YAM-Cube-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-bimanual_yam_cube_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_STEPS="${NUM_STEPS:-560}"
VIDEO_LENGTH="${VIDEO_LENGTH:-560}"
LIFT_HEIGHT="${LIFT_HEIGHT:-0.14}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-False}"
PRINT_INTERVAL="${PRINT_INTERVAL:-40}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.0}"
ALLOW_GRASP_ASSIST="${ALLOW_GRASP_ASSIST:-False}"
REQUIRE_UNASSISTED_LIFT="${REQUIRE_UNASSISTED_LIFT:-True}"
DISABLE_FABRIC="${DISABLE_FABRIC:-True}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_bimanual_yam_cube_${SLURM_JOB_ID_SAFE}.out"

if [ "$TASK" != "Dextrah-Bimanual-YAM-Cube-Grasp" ]; then
  echo "This wrapper is only for TASK=Dextrah-Bimanual-YAM-Cube-Grasp" >&2
  exit 2
fi
if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE" >&2
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site" >&2
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT, found $actual_commit in $CODE_NFS" >&2
    exit 2
  fi
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH LIFT_HEIGHT CAPTURE_VIDEO PRINT_INTERVAL SEED
export CUBE_SPAWN_XY_RANDOMIZATION ALLOW_GRASP_ASSIST REQUIRE_UNASSISTED_LIFT DISABLE_FABRIC
export PREPARE_YAM_ASSETS CODE_COMMIT RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DEXTRAH bimanual YAM cube-grasp environment validation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "NUM_STEPS=$NUM_STEPS"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "VIDEO_LENGTH=$VIDEO_LENGTH"
echo "LIFT_HEIGHT=$LIFT_HEIGHT"
echo "ALLOW_GRASP_ASSIST=$ALLOW_GRASP_ASSIST"
echo "REQUIRE_UNASSISTED_LIFT=$REQUIRE_UNASSISTED_LIFT"
echo "DISABLE_FABRIC=$DISABLE_FABRIC"
echo "PREPARE_YAM_ASSETS=$PREPARE_YAM_ASSETS"
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
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true
    nvidia-smi || true

    YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd
    if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
      /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless --converter mjcf
    fi
    test -s "$YAM_USD"

    cd /code/dextrah_lab/rl_games
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH")
    fi
    ASSIST_ARGS=()
    if [ "$ALLOW_GRASP_ASSIST" != "True" ]; then
      ASSIST_ARGS+=(--no-allow_grasp_assist)
    fi
    if [ "$REQUIRE_UNASSISTED_LIFT" = "True" ]; then
      ASSIST_ARGS+=(--require_unassisted_lift)
    fi
    FABRIC_ARGS=()
    if [ "$DISABLE_FABRIC" = "True" ]; then
      FABRIC_ARGS+=(--disable_fabric)
    fi

    VALIDATE_ARGS=(
      validate_bimanual_yam_cube_grasp_env.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --cube_spawn_xy_randomization "$CUBE_SPAWN_XY_RANDOMIZATION"
      --print_interval "$PRINT_INTERVAL"
      --lift_height "$LIFT_HEIGHT"
      "${VIDEO_ARGS[@]}"
      "${ASSIST_ARGS[@]}"
      "${FABRIC_ARGS[@]}"
    )

    printf "validate_command="
    printf "%q " /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load|nan|NaN" "$LOG_FILE" >/dev/null; then
  echo "Detected validation error patterns in $LOG_FILE." >&2
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing validation metrics: $RUN_DIR_HOST/metrics.json" >&2
  exit 1
fi

echo "Bimanual YAM cube validation done"
