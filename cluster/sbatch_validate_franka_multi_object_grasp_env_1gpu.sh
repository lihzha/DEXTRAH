#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_multi_val
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_%j.out

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

TASK="${TASK:-Dextrah-Franka-Multi-Object-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_multi_object_env_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-8}"
NUM_STEPS="${NUM_STEPS:-120}"
VIDEO_LENGTH="${VIDEO_LENGTH:-120}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
RENDER_CHECK="${RENDER_CHECK:-False}"
RENDER_CHECK_FRAMES="${RENDER_CHECK_FRAMES:-2}"
RENDER_WARMUP_FRAMES="${RENDER_WARMUP_FRAMES:-2}"
PRINT_INTERVAL="${PRINT_INTERVAL:-30}"
SEED="${SEED:-42}"
OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-}"
OBJECT_ASSETS_DIR="${OBJECT_ASSETS_DIR:-}"
MAX_OBJECTS="${MAX_OBJECTS:-8}"
OBJECT_SPAWN_XY_RANDOMIZATION="${OBJECT_SPAWN_XY_RANDOMIZATION:-0.08}"
OBJECT_SPAWN_YAW_RANDOMIZATION_DEG="${OBJECT_SPAWN_YAW_RANDOMIZATION_DEG:-180.0}"
GRASP_PRIOR_RESET_ENABLED="${GRASP_PRIOR_RESET_ENABLED:-False}"
GRASP_PRIOR_LIBRARY_DIR="${GRASP_PRIOR_LIBRARY_DIR:-}"
GRASP_PRIOR_ALLOW_MISSING="${GRASP_PRIOR_ALLOW_MISSING:-False}"
GRASP_PRIOR_RESET_CYCLES="${GRASP_PRIOR_RESET_CYCLES:-4}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_franka_multi_object_${SLURM_JOB_ID_SAFE}.out"

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

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH CAPTURE_VIDEO RENDER_CHECK RENDER_CHECK_FRAMES RENDER_WARMUP_FRAMES PRINT_INTERVAL SEED
export OBJECT_ASSET_MANIFEST_PATH OBJECT_ASSETS_DIR MAX_OBJECTS OBJECT_SPAWN_XY_RANDOMIZATION OBJECT_SPAWN_YAW_RANDOMIZATION_DEG
export GRASP_PRIOR_RESET_ENABLED GRASP_PRIOR_LIBRARY_DIR GRASP_PRIOR_ALLOW_MISSING GRASP_PRIOR_RESET_CYCLES CODE_COMMIT
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka multi-object environment validation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "NUM_STEPS=$NUM_STEPS"
echo "VIDEO_LENGTH=$VIDEO_LENGTH"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "RENDER_CHECK=$RENDER_CHECK"
echo "RENDER_CHECK_FRAMES=$RENDER_CHECK_FRAMES"
echo "RENDER_WARMUP_FRAMES=$RENDER_WARMUP_FRAMES"
echo "SEED=$SEED"
echo "OBJECT_ASSET_MANIFEST_PATH=$OBJECT_ASSET_MANIFEST_PATH"
echo "OBJECT_ASSETS_DIR=$OBJECT_ASSETS_DIR"
echo "MAX_OBJECTS=$MAX_OBJECTS"
echo "OBJECT_SPAWN_XY_RANDOMIZATION=$OBJECT_SPAWN_XY_RANDOMIZATION"
echo "OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
echo "GRASP_PRIOR_RESET_ENABLED=$GRASP_PRIOR_RESET_ENABLED"
echo "GRASP_PRIOR_LIBRARY_DIR=$GRASP_PRIOR_LIBRARY_DIR"
echo "GRASP_PRIOR_ALLOW_MISSING=$GRASP_PRIOR_ALLOW_MISSING"
echo "GRASP_PRIOR_RESET_CYCLES=$GRASP_PRIOR_RESET_CYCLES"
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
    echo "git_status_skipped=container_git_lfs_unavailable"
    nvidia-smi || true

    cd /code/dextrah_lab/rl_games
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH")
    fi
    RENDER_ARGS=()
    case "$RENDER_CHECK" in
      True|true|1|yes|Yes)
        RENDER_ARGS=(--render_check --render_check_frames "$RENDER_CHECK_FRAMES" --render_warmup_frames "$RENDER_WARMUP_FRAMES")
        ;;
    esac
    ASSET_ARGS=()
    if [ -n "$OBJECT_ASSET_MANIFEST_PATH" ]; then
      ASSET_ARGS+=(--object_asset_manifest_path "$OBJECT_ASSET_MANIFEST_PATH")
    fi
    if [ -n "$OBJECT_ASSETS_DIR" ]; then
      ASSET_ARGS+=(--object_assets_dir "$OBJECT_ASSETS_DIR")
    fi
    PRIOR_ARGS=()
    case "$GRASP_PRIOR_RESET_ENABLED" in
      True|true|1|yes|Yes)
        PRIOR_ARGS=(--enable_grasp_prior_reset --grasp_prior_reset_cycles "$GRASP_PRIOR_RESET_CYCLES")
        if [ -n "$GRASP_PRIOR_LIBRARY_DIR" ]; then
          PRIOR_ARGS+=(--grasp_prior_library_dir "$GRASP_PRIOR_LIBRARY_DIR")
        fi
        if [ "$GRASP_PRIOR_ALLOW_MISSING" = "True" ]; then
          PRIOR_ARGS+=(--grasp_prior_allow_missing)
        fi
        ;;
    esac

    VALIDATE_ARGS=(
      validate_franka_multi_object_grasp_env.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --max_objects "$MAX_OBJECTS"
      --object_spawn_xy_randomization "$OBJECT_SPAWN_XY_RANDOMIZATION"
      --object_spawn_yaw_randomization_deg "$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
      "${ASSET_ARGS[@]}"
      "${PRIOR_ARGS[@]}"
      "${RENDER_ARGS[@]}"
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
