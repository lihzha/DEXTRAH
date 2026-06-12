#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_prior_diag
#SBATCH --partition=batch
#SBATCH --time=0-00:30:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/diagnose_franka_cube_prior_%j.out

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

TASK="${TASK:-Dextrah-Franka-Cube-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_cube_prior_diag_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_RESETS="${NUM_RESETS:-3}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:?Set GRASP_PRIOR_LIBRARY_PATH to a library path visible inside the container.}"
DIAGNOSTIC_ENV_ID="${DIAGNOSTIC_ENV_ID:-0}"
RENDER_WIDTH="${RENDER_WIDTH:-1280}"
RENDER_HEIGHT="${RENDER_HEIGHT:-720}"
VIDEO_FPS="${VIDEO_FPS:-6}"
INCLUDE_EXACT_CLOSE_CHECK="${INCLUDE_EXACT_CLOSE_CHECK:-0}"
EXACT_CLOSE_STEPS="${EXACT_CLOSE_STEPS:-80}"
EXACT_CLOSE_COMMAND_WIDTH="${EXACT_CLOSE_COMMAND_WIDTH:-0.0}"
EXACT_CLOSE_APPROACH_OFFSET="${EXACT_CLOSE_APPROACH_OFFSET:-0.0}"
EXACT_CLOSE_LATERAL_OFFSET="${EXACT_CLOSE_LATERAL_OFFSET:-0.0}"
INCLUDE_ORACLE_CLOSE_LIFT_CHECK="${INCLUDE_ORACLE_CLOSE_LIFT_CHECK:-0}"
ORACLE_APPROACH_STEPS="${ORACLE_APPROACH_STEPS:-16}"
ORACLE_EXACT_HOLD_STEPS="${ORACLE_EXACT_HOLD_STEPS:-0}"
ORACLE_CLOSE_STEPS="${ORACLE_CLOSE_STEPS:-50}"
ORACLE_LIFT_STEPS="${ORACLE_LIFT_STEPS:-80}"
ORACLE_HOLD_STEPS="${ORACLE_HOLD_STEPS:-30}"
ORACLE_APPROACH_DISTANCE="${ORACLE_APPROACH_DISTANCE:-0.030}"
ORACLE_APPROACH_MODE="${ORACLE_APPROACH_MODE:-fixed_direction}"
ORACLE_PROPORTIONAL_GAIN="${ORACLE_PROPORTIONAL_GAIN:-1.0}"
ORACLE_MAX_POSITION_ACTION="${ORACLE_MAX_POSITION_ACTION:-1.0}"
ORACLE_TRACK_ORIENTATION="${ORACLE_TRACK_ORIENTATION:-0}"
ORACLE_CLOSE_WIDTH="${ORACLE_CLOSE_WIDTH:-0.055}"
ORACLE_LIFT_ACTION_Z="${ORACLE_LIFT_ACTION_Z:-0.05}"
ORACLE_LIFT_SUCCESS_HEIGHT="${ORACLE_LIFT_SUCCESS_HEIGHT:-0.020}"
ORACLE_RENDER_INTERVAL="${ORACLE_RENDER_INTERVAL:-12}"
RENDER_ALL_RESETS="${RENDER_ALL_RESETS:-0}"
RENDER_FAILED_EXACT_CLOSE="${RENDER_FAILED_EXACT_CLOSE:-0}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.15}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--1.05}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.55}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.08}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.80}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/diagnostics/$RUN_NAME"
RUN_DIR_CONTAINER="/results/diagnostics/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/reset_geometry.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/diagnose_franka_cube_prior_${SLURM_JOB_ID_SAFE}.out"

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

export TASK RUN_NAME NUM_ENVS NUM_RESETS SEED CUBE_SPAWN_XY_RANDOMIZATION
export GRASP_PRIOR_LIBRARY_PATH DIAGNOSTIC_ENV_ID RENDER_WIDTH RENDER_HEIGHT VIDEO_FPS
export INCLUDE_EXACT_CLOSE_CHECK EXACT_CLOSE_STEPS EXACT_CLOSE_COMMAND_WIDTH
export EXACT_CLOSE_APPROACH_OFFSET EXACT_CLOSE_LATERAL_OFFSET
export INCLUDE_ORACLE_CLOSE_LIFT_CHECK ORACLE_APPROACH_STEPS ORACLE_EXACT_HOLD_STEPS ORACLE_CLOSE_STEPS
export ORACLE_LIFT_STEPS ORACLE_HOLD_STEPS ORACLE_APPROACH_DISTANCE
export ORACLE_APPROACH_MODE ORACLE_PROPORTIONAL_GAIN ORACLE_MAX_POSITION_ACTION ORACLE_TRACK_ORIENTATION
export ORACLE_CLOSE_WIDTH ORACLE_LIFT_ACTION_Z ORACLE_LIFT_SUCCESS_HEIGHT ORACLE_RENDER_INTERVAL
export RENDER_ALL_RESETS RENDER_FAILED_EXACT_CLOSE
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export CODE_COMMIT RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube GraspGenX reset-prior diagnostic"
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
echo "NUM_RESETS=$NUM_RESETS"
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "GRASP_PRIOR_LIBRARY_PATH=$GRASP_PRIOR_LIBRARY_PATH"
echo "DIAGNOSTIC_ENV_ID=$DIAGNOSTIC_ENV_ID"
echo "RENDER_WIDTH=$RENDER_WIDTH"
echo "RENDER_HEIGHT=$RENDER_HEIGHT"
echo "INCLUDE_EXACT_CLOSE_CHECK=$INCLUDE_EXACT_CLOSE_CHECK"
echo "EXACT_CLOSE_STEPS=$EXACT_CLOSE_STEPS"
echo "EXACT_CLOSE_COMMAND_WIDTH=$EXACT_CLOSE_COMMAND_WIDTH"
echo "EXACT_CLOSE_APPROACH_OFFSET=$EXACT_CLOSE_APPROACH_OFFSET"
echo "EXACT_CLOSE_LATERAL_OFFSET=$EXACT_CLOSE_LATERAL_OFFSET"
echo "INCLUDE_ORACLE_CLOSE_LIFT_CHECK=$INCLUDE_ORACLE_CLOSE_LIFT_CHECK"
echo "ORACLE_APPROACH_STEPS=$ORACLE_APPROACH_STEPS"
echo "ORACLE_EXACT_HOLD_STEPS=$ORACLE_EXACT_HOLD_STEPS"
echo "ORACLE_CLOSE_STEPS=$ORACLE_CLOSE_STEPS"
echo "ORACLE_LIFT_STEPS=$ORACLE_LIFT_STEPS"
echo "ORACLE_HOLD_STEPS=$ORACLE_HOLD_STEPS"
echo "ORACLE_APPROACH_DISTANCE=$ORACLE_APPROACH_DISTANCE"
echo "ORACLE_APPROACH_MODE=$ORACLE_APPROACH_MODE"
echo "ORACLE_PROPORTIONAL_GAIN=$ORACLE_PROPORTIONAL_GAIN"
echo "ORACLE_MAX_POSITION_ACTION=$ORACLE_MAX_POSITION_ACTION"
echo "ORACLE_TRACK_ORIENTATION=$ORACLE_TRACK_ORIENTATION"
echo "ORACLE_CLOSE_WIDTH=$ORACLE_CLOSE_WIDTH"
echo "ORACLE_LIFT_ACTION_Z=$ORACLE_LIFT_ACTION_Z"
echo "ORACLE_LIFT_SUCCESS_HEIGHT=$ORACLE_LIFT_SUCCESS_HEIGHT"
echo "ORACLE_RENDER_INTERVAL=$ORACLE_RENDER_INTERVAL"
echo "RENDER_ALL_RESETS=$RENDER_ALL_RESETS"
echo "RENDER_FAILED_EXACT_CLOSE=$RENDER_FAILED_EXACT_CLOSE"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
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
    DIAG_ARGS=(
      diagnose_franka_cube_grasp_prior_reset.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_resets "$NUM_RESETS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --cube_spawn_xy_randomization "$CUBE_SPAWN_XY_RANDOMIZATION"
      --grasp_prior_library_path "$GRASP_PRIOR_LIBRARY_PATH"
      --diagnostic_env_id "$DIAGNOSTIC_ENV_ID"
      --render_width "$RENDER_WIDTH"
      --render_height "$RENDER_HEIGHT"
      --video_fps "$VIDEO_FPS"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
    )
    if [ "$INCLUDE_EXACT_CLOSE_CHECK" = "1" ] || [ "$INCLUDE_EXACT_CLOSE_CHECK" = "true" ] || [ "$INCLUDE_EXACT_CLOSE_CHECK" = "True" ]; then
      DIAG_ARGS+=(
        --include_exact_close_check
        --exact_close_steps "$EXACT_CLOSE_STEPS"
        --exact_close_command_width "$EXACT_CLOSE_COMMAND_WIDTH"
        --exact_close_approach_offset "$EXACT_CLOSE_APPROACH_OFFSET"
        --exact_close_lateral_offset "$EXACT_CLOSE_LATERAL_OFFSET"
      )
    fi
    if [ "$INCLUDE_ORACLE_CLOSE_LIFT_CHECK" = "1" ] || [ "$INCLUDE_ORACLE_CLOSE_LIFT_CHECK" = "true" ] || [ "$INCLUDE_ORACLE_CLOSE_LIFT_CHECK" = "True" ]; then
      DIAG_ARGS+=(
        --include_oracle_close_lift_check
        --oracle_approach_steps "$ORACLE_APPROACH_STEPS"
        --oracle_exact_hold_steps "$ORACLE_EXACT_HOLD_STEPS"
        --oracle_close_steps "$ORACLE_CLOSE_STEPS"
        --oracle_lift_steps "$ORACLE_LIFT_STEPS"
        --oracle_hold_steps "$ORACLE_HOLD_STEPS"
        --oracle_approach_distance "$ORACLE_APPROACH_DISTANCE"
        --oracle_approach_mode "$ORACLE_APPROACH_MODE"
        --oracle_proportional_gain "$ORACLE_PROPORTIONAL_GAIN"
        --oracle_max_position_action "$ORACLE_MAX_POSITION_ACTION"
        --oracle_close_width "$ORACLE_CLOSE_WIDTH"
        --oracle_lift_action_z "$ORACLE_LIFT_ACTION_Z"
        --oracle_lift_success_height "$ORACLE_LIFT_SUCCESS_HEIGHT"
        --oracle_render_interval "$ORACLE_RENDER_INTERVAL"
      )
      if [ "$ORACLE_TRACK_ORIENTATION" = "1" ] || [ "$ORACLE_TRACK_ORIENTATION" = "true" ] || [ "$ORACLE_TRACK_ORIENTATION" = "True" ]; then
        DIAG_ARGS+=(--oracle_track_orientation)
      fi
    fi
    if [ "$RENDER_ALL_RESETS" = "1" ] || [ "$RENDER_ALL_RESETS" = "true" ] || [ "$RENDER_ALL_RESETS" = "True" ]; then
      DIAG_ARGS+=(--render_all_resets)
    fi
    if [ "$RENDER_FAILED_EXACT_CLOSE" = "1" ] || [ "$RENDER_FAILED_EXACT_CLOSE" = "true" ] || [ "$RENDER_FAILED_EXACT_CLOSE" = "True" ]; then
      DIAG_ARGS+=(--render_failed_exact_close)
    fi

    printf "diagnose_command="
    printf "%q " /isaac-sim/python.sh "${DIAG_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${DIAG_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected diagnostic error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/reset_geometry.json" ]; then
  echo "Missing reset diagnostic metrics JSON: $RUN_DIR_HOST/reset_geometry.json"
  exit 1
fi

echo "Reset Diagnostic Done"
