#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_cube_bc
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-00:45:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_%j.out

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

TASK="${TASK:-Dextrah-Franka-Cube-Grasp-Traj-Tracking}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_cube_traj_bc_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-8}"
COLLECTION_STEPS="${COLLECTION_STEPS:-520}"
TRAIN_STEPS="${TRAIN_STEPS:-400}"
BATCH_SIZE="${BATCH_SIZE:-1024}"
LEARNING_RATE="${LEARNING_RATE:-0.0001}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.0}"
VALIDATION_FRACTION="${VALIDATION_FRACTION:-0.2}"
LOSS_DIMS="${LOSS_DIMS:-all}"
EVAL_INTERVAL="${EVAL_INTERVAL:-25}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:-42}"
COLLECTION_ACTION_SOURCE="${COLLECTION_ACTION_SOURCE:-reference_delta}"
COLLECTION_TEACHER_ALPHA="${COLLECTION_TEACHER_ALPHA:-0.5}"
REHEARSAL_DATASET_PATHS="${REHEARSAL_DATASET_PATHS:-}"
REHEARSAL_DATASET_NAMES="${REHEARSAL_DATASET_NAMES:-}"
SOURCE_BATCH_MODE="${SOURCE_BATCH_MODE:-random}"
SOURCE_LOSS_WEIGHTS="${SOURCE_LOSS_WEIGHTS:-}"
BEST_SCORE_WEIGHTS="${BEST_SCORE_WEIGHTS:-}"
EARLY_STOP_PATIENCE="${EARLY_STOP_PATIENCE:-0}"
DISTILL_SOURCES="${DISTILL_SOURCES:-}"
DISTILL_LOSS_WEIGHT="${DISTILL_LOSS_WEIGHT:-0.0}"
DISTILL_DIMS="${DISTILL_DIMS:-}"
RESIDUAL_ADAPTER_ENABLED="${RESIDUAL_ADAPTER_ENABLED:-False}"
RESIDUAL_HIDDEN_DIM="${RESIDUAL_HIDDEN_DIM:-64}"
RESIDUAL_MAX_ACTION="${RESIDUAL_MAX_ACTION:-0.5}"
RESIDUAL_PRESERVE_SOURCES="${RESIDUAL_PRESERVE_SOURCES:-}"
RESIDUAL_PRESERVE_WEIGHT="${RESIDUAL_PRESERVE_WEIGHT:-0.0}"
RESIDUAL_L2_WEIGHT="${RESIDUAL_L2_WEIGHT:-0.0}"
RESIDUAL_GATE_ENABLED="${RESIDUAL_GATE_ENABLED:-False}"
RESIDUAL_GATE_HIDDEN_DIM="${RESIDUAL_GATE_HIDDEN_DIM:--1}"
RESIDUAL_GATE_BIAS_INIT="${RESIDUAL_GATE_BIAS_INIT:-0.0}"
SOURCE_PROBE_STEPS="${SOURCE_PROBE_STEPS:-200}"
SOURCE_PROBE_LR="${SOURCE_PROBE_LR:-0.01}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
TRAJECTORY_TRACKING_REFERENCE_PATH="${TRAJECTORY_TRACKING_REFERENCE_PATH:-}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to an RL-Games checkpoint path visible in /results or on the host}"

RUN_DIR_HOST="$RESULTS_NFS/bc/$RUN_NAME"
RUN_DIR_CONTAINER="/results/bc/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/bc_franka_cube_${SLURM_JOB_ID_SAFE}.out"
BC_CHECKPOINT_CONTAINER="$RUN_DIR_CONTAINER/nn/bc_reference_action_imitation.pth"
DATASET_CONTAINER="$RUN_DIR_CONTAINER/reference_action_dataset.pt"

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
if [ -n "$CHECKPOINT_HOST" ] && [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS COLLECTION_STEPS TRAIN_STEPS BATCH_SIZE LEARNING_RATE WEIGHT_DECAY VALIDATION_FRACTION LOSS_DIMS EVAL_INTERVAL USE_CUDA_GRAPH SEED COLLECTION_ACTION_SOURCE COLLECTION_TEACHER_ALPHA REHEARSAL_DATASET_PATHS REHEARSAL_DATASET_NAMES SOURCE_BATCH_MODE SOURCE_LOSS_WEIGHTS BEST_SCORE_WEIGHTS EARLY_STOP_PATIENCE DISTILL_SOURCES DISTILL_LOSS_WEIGHT DISTILL_DIMS RESIDUAL_ADAPTER_ENABLED RESIDUAL_HIDDEN_DIM RESIDUAL_MAX_ACTION RESIDUAL_PRESERVE_SOURCES RESIDUAL_PRESERVE_WEIGHT RESIDUAL_L2_WEIGHT RESIDUAL_GATE_ENABLED RESIDUAL_GATE_HIDDEN_DIM RESIDUAL_GATE_BIAS_INIT SOURCE_PROBE_STEPS SOURCE_PROBE_LR CUBE_SPAWN_XY_RANDOMIZATION TRAJECTORY_TRACKING_REFERENCE_PATH
export CHECKPOINT_ARG RUN_DIR_CONTAINER BC_CHECKPOINT_CONTAINER DATASET_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube trajectory BC diagnostic"
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
echo "COLLECTION_STEPS=$COLLECTION_STEPS"
echo "TRAIN_STEPS=$TRAIN_STEPS"
echo "BATCH_SIZE=$BATCH_SIZE"
echo "LEARNING_RATE=$LEARNING_RATE"
echo "WEIGHT_DECAY=$WEIGHT_DECAY"
echo "VALIDATION_FRACTION=$VALIDATION_FRACTION"
echo "LOSS_DIMS=$LOSS_DIMS"
echo "EVAL_INTERVAL=$EVAL_INTERVAL"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "COLLECTION_ACTION_SOURCE=$COLLECTION_ACTION_SOURCE"
echo "COLLECTION_TEACHER_ALPHA=$COLLECTION_TEACHER_ALPHA"
echo "REHEARSAL_DATASET_PATHS=$REHEARSAL_DATASET_PATHS"
echo "REHEARSAL_DATASET_NAMES=$REHEARSAL_DATASET_NAMES"
echo "SOURCE_BATCH_MODE=$SOURCE_BATCH_MODE"
echo "SOURCE_LOSS_WEIGHTS=$SOURCE_LOSS_WEIGHTS"
echo "BEST_SCORE_WEIGHTS=$BEST_SCORE_WEIGHTS"
echo "EARLY_STOP_PATIENCE=$EARLY_STOP_PATIENCE"
echo "DISTILL_SOURCES=$DISTILL_SOURCES"
echo "DISTILL_LOSS_WEIGHT=$DISTILL_LOSS_WEIGHT"
echo "DISTILL_DIMS=$DISTILL_DIMS"
echo "RESIDUAL_ADAPTER_ENABLED=$RESIDUAL_ADAPTER_ENABLED"
echo "RESIDUAL_HIDDEN_DIM=$RESIDUAL_HIDDEN_DIM"
echo "RESIDUAL_MAX_ACTION=$RESIDUAL_MAX_ACTION"
echo "RESIDUAL_PRESERVE_SOURCES=$RESIDUAL_PRESERVE_SOURCES"
echo "RESIDUAL_PRESERVE_WEIGHT=$RESIDUAL_PRESERVE_WEIGHT"
echo "RESIDUAL_L2_WEIGHT=$RESIDUAL_L2_WEIGHT"
echo "RESIDUAL_GATE_ENABLED=$RESIDUAL_GATE_ENABLED"
echo "RESIDUAL_GATE_HIDDEN_DIM=$RESIDUAL_GATE_HIDDEN_DIM"
echo "RESIDUAL_GATE_BIAS_INIT=$RESIDUAL_GATE_BIAS_INIT"
echo "SOURCE_PROBE_STEPS=$SOURCE_PROBE_STEPS"
echo "SOURCE_PROBE_LR=$SOURCE_PROBE_LR"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "TRAJECTORY_TRACKING_REFERENCE_PATH=$TRAJECTORY_TRACKING_REFERENCE_PATH"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "BC_CHECKPOINT_CONTAINER=$BC_CHECKPOINT_CONTAINER"
echo "DATASET_CONTAINER=$DATASET_CONTAINER"

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

    TASK_OVERRIDES=(
      agent.wandb_activate=False
      env.use_cuda_graph="$USE_CUDA_GRAPH"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
      env.trajectory_tracking_teacher_force_enabled=False
    )
    if [ -n "$TRAJECTORY_TRACKING_REFERENCE_PATH" ]; then
      TASK_OVERRIDES+=(
        env.trajectory_tracking_reference_path="$TRAJECTORY_TRACKING_REFERENCE_PATH"
      )
    fi

    BC_ARGS=(
      bc_reference_action_imitation.py
      --headless
      --task="$TASK"
      --num_envs "$NUM_ENVS"
      --collection_steps "$COLLECTION_STEPS"
      --train_steps "$TRAIN_STEPS"
      --batch_size "$BATCH_SIZE"
      --learning_rate "$LEARNING_RATE"
      --weight_decay "$WEIGHT_DECAY"
      --validation_fraction "$VALIDATION_FRACTION"
      --loss_dims "$LOSS_DIMS"
      --eval_interval "$EVAL_INTERVAL"
      --seed "$SEED"
      --collection_action_source "$COLLECTION_ACTION_SOURCE"
      --collection_teacher_alpha "$COLLECTION_TEACHER_ALPHA"
      --rehearsal_dataset_paths "$REHEARSAL_DATASET_PATHS"
      --rehearsal_dataset_names "$REHEARSAL_DATASET_NAMES"
      --source_batch_mode "$SOURCE_BATCH_MODE"
      --source_loss_weights "$SOURCE_LOSS_WEIGHTS"
      --best_score_weights "$BEST_SCORE_WEIGHTS"
      --early_stop_patience "$EARLY_STOP_PATIENCE"
      --distill_sources "$DISTILL_SOURCES"
      --distill_loss_weight "$DISTILL_LOSS_WEIGHT"
      --distill_dims "$DISTILL_DIMS"
      --residual_adapter_enabled "$RESIDUAL_ADAPTER_ENABLED"
      --residual_hidden_dim "$RESIDUAL_HIDDEN_DIM"
      --residual_max_action "$RESIDUAL_MAX_ACTION"
      --residual_preserve_sources "$RESIDUAL_PRESERVE_SOURCES"
      --residual_preserve_weight "$RESIDUAL_PRESERVE_WEIGHT"
      --residual_l2_weight "$RESIDUAL_L2_WEIGHT"
      --residual_gate_enabled "$RESIDUAL_GATE_ENABLED"
      --residual_gate_hidden_dim "$RESIDUAL_GATE_HIDDEN_DIM"
      --residual_gate_bias_init "$RESIDUAL_GATE_BIAS_INIT"
      --source_probe_steps "$SOURCE_PROBE_STEPS"
      --source_probe_lr "$SOURCE_PROBE_LR"
      --output_dir "$RUN_DIR_CONTAINER"
      --dataset_path "$DATASET_CONTAINER"
      --bc_checkpoint_path "$BC_CHECKPOINT_CONTAINER"
      --checkpoint "$CHECKPOINT_ARG"
      "${TASK_OVERRIDES[@]}"
    )

    printf "bc_command="
    printf "%q " /isaac-sim/python.sh "${BC_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${BC_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected BC diagnostic error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/bc_metrics.json" ]; then
  echo "Missing BC metrics JSON: $RUN_DIR_HOST/bc_metrics.json"
  exit 1
fi
if [ ! -s "$RUN_DIR_HOST/nn/bc_reference_action_imitation.pth" ]; then
  echo "Missing BC checkpoint: $RUN_DIR_HOST/nn/bc_reference_action_imitation.pth"
  exit 1
fi

echo "BC Diagnostic Done"
