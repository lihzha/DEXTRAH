#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_yam_cube_eval
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-01:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_bimanual_yam_cube_%j.out

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
RUN_NAME="${RUN_NAME:-bimanual_yam_cube_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
CODE_COMMIT="${CODE_COMMIT:-}"
NUM_ENVS="${NUM_ENVS:-64}"
NUM_STEPS="${NUM_STEPS:-640}"
VIDEO_LENGTH="${VIDEO_LENGTH:-640}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-bimanual-yam-cube-eval}"
PRINT_INTERVAL="${PRINT_INTERVAL:-40}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
DETERMINISTIC="${DETERMINISTIC:-True}"
ACTION_SOURCE="${ACTION_SOURCE:-policy}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.015}"
BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z="${BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z:-}"
BIMANUAL_REFERENCE_MIN_HOLD_Z="${BIMANUAL_REFERENCE_MIN_HOLD_Z:-}"
BIMANUAL_REFERENCE_CONTACT_DIST="${BIMANUAL_REFERENCE_CONTACT_DIST:-}"
BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST="${BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST:-}"
BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN="${BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN:-}"
BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y="${BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y:-}"
BIMANUAL_REFERENCE_LIFT_HEIGHT="${BIMANUAL_REFERENCE_LIFT_HEIGHT:-}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.50}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:-0.0}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-0.81}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.375}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:-0.0}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.10}"
CAMERA_ENV_INDEX="${CAMERA_ENV_INDEX:-0}"
CHECKPOINT="${CHECKPOINT:-}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
if [ -z "$CHECKPOINT" ] && [[ "$ACTION_SOURCE" == policy* ]]; then
  echo "Set CHECKPOINT to a bimanual YAM cube RL-Games .pth file." >&2
  exit 2
fi

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_bimanual_yam_cube_${SLURM_JOB_ID_SAFE}.out"

CHECKPOINT_ARG="$CHECKPOINT"
CHECKPOINT_HOST="$CHECKPOINT"
if [[ -n "$CHECKPOINT" && "$CHECKPOINT" == /results/* ]]; then
  CHECKPOINT_HOST="$RESULTS_NFS/${CHECKPOINT#/results/}"
elif [[ -n "$CHECKPOINT" && "$CHECKPOINT" == "$RESULTS_NFS"/* ]]; then
  rel_checkpoint="${CHECKPOINT#$RESULTS_NFS/}"
  CHECKPOINT_ARG="/results/$rel_checkpoint"
fi

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
if [ -n "$CHECKPOINT_HOST" ] && [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST" >&2
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH VIDEO_NAME_PREFIX PRINT_INTERVAL CAPTURE_VIDEO
export DETERMINISTIC ACTION_SOURCE USE_CUDA_GRAPH SEED CUBE_SPAWN_XY_RANDOMIZATION
export BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z BIMANUAL_REFERENCE_MIN_HOLD_Z
export BIMANUAL_REFERENCE_CONTACT_DIST BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST
export BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y
export BIMANUAL_REFERENCE_LIFT_HEIGHT
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z CAMERA_ENV_INDEX
export CHECKPOINT_ARG RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME PREPARE_YAM_ASSETS

echo "Running DEXTRAH bimanual YAM cube-grasp checkpoint evaluation"
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
echo "DETERMINISTIC=$DETERMINISTIC"
echo "ACTION_SOURCE=$ACTION_SOURCE"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z=$BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z"
echo "BIMANUAL_REFERENCE_MIN_HOLD_Z=$BIMANUAL_REFERENCE_MIN_HOLD_Z"
echo "BIMANUAL_REFERENCE_CONTACT_DIST=$BIMANUAL_REFERENCE_CONTACT_DIST"
echo "BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST=$BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST"
echo "BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN=$BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN"
echo "BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y=$BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y"
echo "BIMANUAL_REFERENCE_LIFT_HEIGHT=$BIMANUAL_REFERENCE_LIFT_HEIGHT"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "CHECKPOINT_ARG=${CHECKPOINT_ARG:-none}"
echo "CHECKPOINT_HOST=${CHECKPOINT_HOST:-none}"
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
    nvidia-smi || true

    YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd
    if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
      /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless --converter mjcf
    fi
    test -s "$YAM_USD"

    cd /code/dextrah_lab/rl_games
    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    DETERMINISTIC_ARGS=(--deterministic)
    if [ "$DETERMINISTIC" != "True" ]; then
      DETERMINISTIC_ARGS=(--no-deterministic)
    fi

    TASK_OVERRIDES=(
      agent.wandb_activate=False
      env.use_cuda_graph="$USE_CUDA_GRAPH"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
    )
    append_env_override() {
      local field="$1"
      local value="$2"
      if [ -n "$value" ]; then
        TASK_OVERRIDES+=(env."$field"="$value")
      fi
    }
    append_env_override bimanual_reference_cube_center_to_hold_z "$BIMANUAL_REFERENCE_CUBE_CENTER_TO_HOLD_Z"
    append_env_override bimanual_reference_min_hold_z "$BIMANUAL_REFERENCE_MIN_HOLD_Z"
    append_env_override bimanual_reference_contact_dist "$BIMANUAL_REFERENCE_CONTACT_DIST"
    append_env_override bimanual_reference_contact_trigger_dist "$BIMANUAL_REFERENCE_CONTACT_TRIGGER_DIST"
    append_env_override bimanual_reference_contact_side_margin "$BIMANUAL_REFERENCE_CONTACT_SIDE_MARGIN"
    append_env_override bimanual_reference_lift_squeeze_y "$BIMANUAL_REFERENCE_LIFT_SQUEEZE_Y"
    append_env_override bimanual_reference_lift_height "$BIMANUAL_REFERENCE_LIFT_HEIGHT"

    EVAL_ARGS=(
      eval_rollout.py
      --headless
      --task="$TASK"
      --action_source "$ACTION_SOURCE"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      "${DETERMINISTIC_ARGS[@]}"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      --camera_env_index "$CAMERA_ENV_INDEX"
      "${VIDEO_ARGS[@]}"
      "${TASK_OVERRIDES[@]}"
    )
    if [ -n "$CHECKPOINT_ARG" ]; then
      EVAL_ARGS+=(--checkpoint "$CHECKPOINT_ARG")
    fi

    printf "eval_command="
    printf "%q " /isaac-sim/python.sh "${EVAL_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${EVAL_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load|nan|NaN" "$LOG_FILE" >/dev/null; then
  echo "Detected eval error patterns in $LOG_FILE." >&2
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing eval metrics: $RUN_DIR_HOST/metrics.json" >&2
  exit 1
fi

echo "Bimanual YAM cube evaluation done"
