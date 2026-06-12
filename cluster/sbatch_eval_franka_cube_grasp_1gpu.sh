#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_cube_eval
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-01:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_STEPS="${NUM_STEPS:-600}"
VIDEO_LENGTH="${VIDEO_LENGTH:-600}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-grasp-eval}"
PRINT_INTERVAL="${PRINT_INTERVAL:-20}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
DETERMINISTIC="${DETERMINISTIC:-True}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
GRASP_PRIOR_RESET_ENABLED="${GRASP_PRIOR_RESET_ENABLED:-False}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:-}"
GRASP_PRIOR_ACTION_WARMSTART_ENABLED="${GRASP_PRIOR_ACTION_WARMSTART_ENABLED:-False}"
GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS="${GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS:-16}"
GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS="${GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS:-12}"
GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS="${GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS:-12}"
GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH="${GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH:-0.055}"
GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z="${GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z:-0.15}"
GRASP_PRIOR_ACTION_WARMSTART_GAIN="${GRASP_PRIOR_ACTION_WARMSTART_GAIN:-8.0}"
GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION="${GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION:-1.0}"
GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION="${GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION:-True}"
GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED="${GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED:-False}"
GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT="${GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT:-2.0}"
GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS="${GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS:-2.0}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to a checkpoint path visible inside the container, e.g. /results/logs/rl_games/dextrah_franka_cube_grasp/<run>/nn/foo.pth}"

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_franka_cube_${SLURM_JOB_ID_SAFE}.out"

CHECKPOINT_ARG="$CHECKPOINT"
CHECKPOINT_HOST="$CHECKPOINT"
if [[ "$CHECKPOINT" == /results/* ]]; then
  CHECKPOINT_HOST="$RESULTS_NFS/${CHECKPOINT#/results/}"
elif [[ "$CHECKPOINT" == "$RESULTS_NFS"/* ]]; then
  rel_checkpoint="${CHECKPOINT#$RESULTS_NFS/}"
  CHECKPOINT_ARG="/results/$rel_checkpoint"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
case "$GRASP_PRIOR_ACTION_WARMSTART_ENABLED" in
  True|true|1|yes|Yes)
    case "$GRASP_PRIOR_RESET_ENABLED" in
      True|true|1|yes|Yes) ;;
      *)
        echo "GRASP_PRIOR_ACTION_WARMSTART_ENABLED=True requires GRASP_PRIOR_RESET_ENABLED=True" >&2
        exit 2
        ;;
    esac
    ;;
esac

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH VIDEO_NAME_PREFIX PRINT_INTERVAL CAPTURE_VIDEO DETERMINISTIC USE_CUDA_GRAPH SEED CUBE_SPAWN_XY_RANDOMIZATION
export GRASP_PRIOR_RESET_ENABLED GRASP_PRIOR_LIBRARY_PATH
export GRASP_PRIOR_ACTION_WARMSTART_ENABLED GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS
export GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS
export GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z
export GRASP_PRIOR_ACTION_WARMSTART_GAIN GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION
export GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION
export GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT
export GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export CHECKPOINT_ARG RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube-grasp checkpoint evaluation"
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
echo "VIDEO_NAME_PREFIX=$VIDEO_NAME_PREFIX"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "DETERMINISTIC=$DETERMINISTIC"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "GRASP_PRIOR_RESET_ENABLED=$GRASP_PRIOR_RESET_ENABLED"
echo "GRASP_PRIOR_LIBRARY_PATH=$GRASP_PRIOR_LIBRARY_PATH"
echo "GRASP_PRIOR_ACTION_WARMSTART_ENABLED=$GRASP_PRIOR_ACTION_WARMSTART_ENABLED"
echo "GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS=$GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS"
echo "GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS=$GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS"
echo "GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=$GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS"
echo "GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=$GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH"
echo "GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=$GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z"
echo "GRASP_PRIOR_ACTION_WARMSTART_GAIN=$GRASP_PRIOR_ACTION_WARMSTART_GAIN"
echo "GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION=$GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION"
echo "GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION=$GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION"
echo "GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=$GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED"
echo "GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=$GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT"
echo "GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS=$GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
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
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi

    DETERMINISTIC_ARGS=(--deterministic)
    if [ "$DETERMINISTIC" = "False" ]; then
      DETERMINISTIC_ARGS=(--no-deterministic)
    fi

    TASK_OVERRIDES=(
      agent.wandb_activate=False
      env.use_cuda_graph="$USE_CUDA_GRAPH"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
    )
    if [ "$GRASP_PRIOR_RESET_ENABLED" = "True" ]; then
      if [ -z "$GRASP_PRIOR_LIBRARY_PATH" ]; then
        echo "GRASP_PRIOR_RESET_ENABLED=True requires GRASP_PRIOR_LIBRARY_PATH."
        exit 2
      fi
      TASK_OVERRIDES+=(
        env.grasp_prior_reset_enabled=True
        env.grasp_prior_library_path="$GRASP_PRIOR_LIBRARY_PATH"
      )
    fi

    append_grasp_prior_reference_sequence_overrides() {
      TASK_OVERRIDES+=(
        env.grasp_prior_action_warmstart_approach_steps="$GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS"
        env.grasp_prior_action_warmstart_close_steps="$GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS"
        env.grasp_prior_action_warmstart_lift_steps="$GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS"
        env.grasp_prior_action_warmstart_close_width="$GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH"
        env.grasp_prior_action_warmstart_lift_action_z="$GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z"
        env.grasp_prior_action_warmstart_gain="$GRASP_PRIOR_ACTION_WARMSTART_GAIN"
        env.grasp_prior_action_warmstart_max_position_action="$GRASP_PRIOR_ACTION_WARMSTART_MAX_POSITION_ACTION"
        env.grasp_prior_action_warmstart_track_orientation="$GRASP_PRIOR_ACTION_WARMSTART_TRACK_ORIENTATION"
      )
    }

    case "$GRASP_PRIOR_ACTION_WARMSTART_ENABLED" in
      True|true|1|yes|Yes)
        TASK_OVERRIDES+=(
          env.grasp_prior_action_warmstart_enabled=True
        )
        append_grasp_prior_reference_sequence_overrides
        ;;
    esac
    case "$GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED" in
      True|true|1|yes|Yes)
        TASK_OVERRIDES+=(
          env.grasp_prior_action_prior_reward_enabled=True
          env.grasp_prior_action_prior_reward_weight="$GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT"
          env.grasp_prior_action_prior_reward_sharpness="$GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS"
        )
        case "$GRASP_PRIOR_ACTION_WARMSTART_ENABLED" in
          True|true|1|yes|Yes) ;;
          *) append_grasp_prior_reference_sequence_overrides ;;
        esac
        ;;
    esac

    EVAL_ARGS=(
      eval_rollout.py
      --headless
      --task="$TASK"
      --checkpoint "$CHECKPOINT_ARG"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      "${VIDEO_ARGS[@]}"
      "${DETERMINISTIC_ARGS[@]}"
      "${TASK_OVERRIDES[@]}"
    )

    printf "eval_command="
    printf "%q " /isaac-sim/python.sh "${EVAL_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${EVAL_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected eval error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing eval metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

echo "Evaluation Done"
