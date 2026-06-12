#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_pass7_bc
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_pass7_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_pass7_bc_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-64}"
NUM_RESETS="${NUM_RESETS:-16}"
SEED="${SEED:-20260624}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:?Set GRASP_PRIOR_LIBRARY_PATH to a path visible inside the container.}"
INIT_CHECKPOINT="${INIT_CHECKPOINT:?Set INIT_CHECKPOINT to a checkpoint path visible inside the container.}"
TRAIN_EPOCHS="${TRAIN_EPOCHS:-40}"
BATCH_SIZE="${BATCH_SIZE:-2048}"
LEARNING_RATE="${LEARNING_RATE:-0.001}"
TRAIN_SCOPE="${TRAIN_SCOPE:-mu}"
VALIDATION_FRACTION="${VALIDATION_FRACTION:-0.25}"
PHASE_BALANCE_LOSS="${PHASE_BALANCE_LOSS:-False}"
LIFT_PHASE_LOSS_WEIGHT="${LIFT_PHASE_LOSS_WEIGHT:-1.0}"
LIFT_Z_MSE_WEIGHT="${LIFT_Z_MSE_WEIGHT:-1.0}"
LIFT_Z_SIGN_LOSS_WEIGHT="${LIFT_Z_SIGN_LOSS_WEIGHT:-0.0}"
APPROACH_STEPS="${APPROACH_STEPS:-16}"
CLOSE_STEPS="${CLOSE_STEPS:-12}"
LIFT_STEPS="${LIFT_STEPS:-12}"
CLOSE_WIDTH="${CLOSE_WIDTH:-0.055}"
LIFT_ACTION_Z="${LIFT_ACTION_Z:-0.15}"
ORACLE_GAIN="${ORACLE_GAIN:-8.0}"
ORACLE_MAX_POSITION_ACTION="${ORACLE_MAX_POSITION_ACTION:-1.0}"
TRACK_ORIENTATION="${TRACK_ORIENTATION:-True}"
GATE_VAL_MSE="${GATE_VAL_MSE:-0.04}"
GATE_GRIPPER_SIGN="${GATE_GRIPPER_SIGN:-0.95}"
GATE_LIFT_Z_SIGN="${GATE_LIFT_Z_SIGN:-0.90}"
SAVE_BC_CHECKPOINT="${SAVE_BC_CHECKPOINT:-True}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/diagnostics/$RUN_NAME"
RUN_DIR_CONTAINER="/results/diagnostics/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/bc_franka_cube_pass7_${SLURM_JOB_ID_SAFE}.out"

container_to_host_path() {
  local path="$1"
  if [[ "$path" == /results/* ]]; then
    printf "%s/%s" "$RESULTS_NFS" "${path#/results/}"
  elif [[ "$path" == "$RESULTS_NFS"/* ]]; then
    printf "%s" "$path"
  else
    printf "%s" "$path"
  fi
}

host_to_container_path() {
  local path="$1"
  if [[ "$path" == "$RESULTS_NFS"/* ]]; then
    printf "/results/%s" "${path#$RESULTS_NFS/}"
  else
    printf "%s" "$path"
  fi
}

if [ "$TASK" != "Dextrah-Franka-Cube-Grasp" ]; then
  echo "This wrapper is only for TASK=Dextrah-Franka-Cube-Grasp" >&2
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

GRASP_PRIOR_LIBRARY_HOST="$(container_to_host_path "$GRASP_PRIOR_LIBRARY_PATH")"
GRASP_PRIOR_LIBRARY_ARG="$(host_to_container_path "$GRASP_PRIOR_LIBRARY_PATH")"
INIT_CHECKPOINT_HOST="$(container_to_host_path "$INIT_CHECKPOINT")"
INIT_CHECKPOINT_ARG="$(host_to_container_path "$INIT_CHECKPOINT")"
if [ ! -f "$GRASP_PRIOR_LIBRARY_HOST" ]; then
  echo "Missing grasp prior library: $GRASP_PRIOR_LIBRARY_HOST" >&2
  exit 2
fi
if [ ! -f "$INIT_CHECKPOINT_HOST" ]; then
  echo "Missing init checkpoint: $INIT_CHECKPOINT_HOST" >&2
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
export GRASP_PRIOR_LIBRARY_ARG INIT_CHECKPOINT_ARG TRAIN_EPOCHS BATCH_SIZE LEARNING_RATE TRAIN_SCOPE VALIDATION_FRACTION
export PHASE_BALANCE_LOSS LIFT_PHASE_LOSS_WEIGHT LIFT_Z_MSE_WEIGHT LIFT_Z_SIGN_LOSS_WEIGHT
export APPROACH_STEPS CLOSE_STEPS LIFT_STEPS CLOSE_WIDTH LIFT_ACTION_Z ORACLE_GAIN ORACLE_MAX_POSITION_ACTION TRACK_ORIENTATION
export GATE_VAL_MSE GATE_GRIPPER_SIGN GATE_LIFT_Z_SIGN SAVE_BC_CHECKPOINT
export CODE_COMMIT RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube pass7 BC action diagnostic"
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
echo "GRASP_PRIOR_LIBRARY_ARG=$GRASP_PRIOR_LIBRARY_ARG"
echo "INIT_CHECKPOINT_ARG=$INIT_CHECKPOINT_ARG"
echo "TRAIN_EPOCHS=$TRAIN_EPOCHS"
echo "BATCH_SIZE=$BATCH_SIZE"
echo "LEARNING_RATE=$LEARNING_RATE"
echo "TRAIN_SCOPE=$TRAIN_SCOPE"
echo "VALIDATION_FRACTION=$VALIDATION_FRACTION"
echo "PHASE_BALANCE_LOSS=$PHASE_BALANCE_LOSS"
echo "LIFT_PHASE_LOSS_WEIGHT=$LIFT_PHASE_LOSS_WEIGHT"
echo "LIFT_Z_MSE_WEIGHT=$LIFT_Z_MSE_WEIGHT"
echo "LIFT_Z_SIGN_LOSS_WEIGHT=$LIFT_Z_SIGN_LOSS_WEIGHT"
echo "APPROACH_STEPS=$APPROACH_STEPS"
echo "CLOSE_STEPS=$CLOSE_STEPS"
echo "LIFT_STEPS=$LIFT_STEPS"
echo "CLOSE_WIDTH=$CLOSE_WIDTH"
echo "LIFT_ACTION_Z=$LIFT_ACTION_Z"
echo "ORACLE_GAIN=$ORACLE_GAIN"
echo "ORACLE_MAX_POSITION_ACTION=$ORACLE_MAX_POSITION_ACTION"
echo "TRACK_ORIENTATION=$TRACK_ORIENTATION"
echo "GATE_VAL_MSE=$GATE_VAL_MSE"
echo "GATE_GRIPPER_SIGN=$GATE_GRIPPER_SIGN"
echo "GATE_LIFT_Z_SIGN=$GATE_LIFT_Z_SIGN"
echo "SAVE_BC_CHECKPOINT=$SAVE_BC_CHECKPOINT"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "METRICS_CONTAINER=$METRICS_CONTAINER"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,TORCH_DISABLE_ADDR2LINE=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
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
    BC_ARGS=(
      bc_franka_cube_pass7_actions.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_resets "$NUM_RESETS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --cube_spawn_xy_randomization "$CUBE_SPAWN_XY_RANDOMIZATION"
      --grasp_prior_library_path "$GRASP_PRIOR_LIBRARY_ARG"
      --init_checkpoint "$INIT_CHECKPOINT_ARG"
      --train_epochs "$TRAIN_EPOCHS"
      --batch_size "$BATCH_SIZE"
      --learning_rate "$LEARNING_RATE"
      --train_scope "$TRAIN_SCOPE"
      --validation_fraction "$VALIDATION_FRACTION"
      --lift_phase_loss_weight "$LIFT_PHASE_LOSS_WEIGHT"
      --lift_z_mse_weight "$LIFT_Z_MSE_WEIGHT"
      --lift_z_sign_loss_weight "$LIFT_Z_SIGN_LOSS_WEIGHT"
      --approach_steps "$APPROACH_STEPS"
      --close_steps "$CLOSE_STEPS"
      --lift_steps "$LIFT_STEPS"
      --close_width "$CLOSE_WIDTH"
      --lift_action_z "$LIFT_ACTION_Z"
      --oracle_gain "$ORACLE_GAIN"
      --oracle_max_position_action "$ORACLE_MAX_POSITION_ACTION"
      --gate_val_mse "$GATE_VAL_MSE"
      --gate_gripper_sign "$GATE_GRIPPER_SIGN"
      --gate_lift_z_sign "$GATE_LIFT_Z_SIGN"
      agent.wandb_activate=False
      env.use_cuda_graph=False
      env.grasp_prior_reset_enabled=True
      env.grasp_prior_library_path="$GRASP_PRIOR_LIBRARY_ARG"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
    )
    case "$TRACK_ORIENTATION" in
      False|false|0|no|No) BC_ARGS+=(--no-track_orientation) ;;
      *) BC_ARGS+=(--track_orientation) ;;
    esac
    case "$PHASE_BALANCE_LOSS" in
      False|false|0|no|No) BC_ARGS+=(--no-phase_balance_loss) ;;
      *) BC_ARGS+=(--phase_balance_loss) ;;
    esac
    case "$SAVE_BC_CHECKPOINT" in
      False|false|0|no|No) BC_ARGS+=(--no-save_bc_checkpoint) ;;
      *) BC_ARGS+=(--save_bc_checkpoint) ;;
    esac

    printf "bc_command="
    printf "%q " /isaac-sim/python.sh "${BC_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${BC_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected BC diagnostic error patterns in $LOG_FILE." >&2
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing BC metrics JSON: $RUN_DIR_HOST/metrics.json" >&2
  exit 1
fi

echo "BC pass7 action diagnostic Done"
