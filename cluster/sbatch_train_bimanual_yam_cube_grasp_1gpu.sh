#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_yam_cube_rl
#SBATCH --partition=batch
#SBATCH --time=0-03:50:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bimanual_yam_cube_rl_%j.out

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
RUN_NAME="${FULL_EXPERIMENT_NAME:-bimanual_yam_cube_rl_${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)}"
CODE_COMMIT="${CODE_COMMIT:-}"
NUM_ENVS="${NUM_ENVS:-1024}"
MAX_ITERATIONS="${MAX_ITERATIONS:-120}"
HORIZON_LENGTH="${HORIZON_LENGTH:-64}"
MINIBATCH_SIZE="${MINIBATCH_SIZE:-16384}"
CENTRAL_VALUE_MINIBATCH_SIZE="${CENTRAL_VALUE_MINIBATCH_SIZE:-$MINIBATCH_SIZE}"
LEARNING_RATE="${LEARNING_RATE:-0.0002}"
CENTRAL_VALUE_LEARNING_RATE="${CENTRAL_VALUE_LEARNING_RATE:-0.0001}"
MINI_EPOCHS="${MINI_EPOCHS:-4}"
SAVE_FREQUENCY="${SAVE_FREQUENCY:-10}"
GAMMA="${GAMMA:-0.995}"
TAU="${TAU:-0.95}"
KL_THRESHOLD="${KL_THRESHOLD:-0.012}"
ENTROPY_COEF="${ENTROPY_COEF:-0.0005}"
E_CLIP="${E_CLIP:-0.2}"
GRAD_NORM="${GRAD_NORM:-1.0}"
SIGMA_INIT_VAL="${SIGMA_INIT_VAL:-0}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:--1}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.015}"
DEXTRAH_RLGAMES_JSONL_METRICS="${DEXTRAH_RLGAMES_JSONL_METRICS:-True}"
AUTO_RESUME="${AUTO_RESUME:-False}"
CHECKPOINT="${CHECKPOINT:-}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"

CUBE_APPROACH_WEIGHT="${CUBE_APPROACH_WEIGHT:-}"
CUBE_ENCLOSURE_WEIGHT="${CUBE_ENCLOSURE_WEIGHT:-}"
CUBE_SIDE_ALIGNMENT_WEIGHT="${CUBE_SIDE_ALIGNMENT_WEIGHT:-}"
CUBE_LIFT_WEIGHT="${CUBE_LIFT_WEIGHT:-}"
CUBE_HEIGHT_TRACKING_WEIGHT="${CUBE_HEIGHT_TRACKING_WEIGHT:-}"
CUBE_XY_STABILITY_WEIGHT="${CUBE_XY_STABILITY_WEIGHT:-}"
CUBE_SUCCESS_BONUS_WEIGHT="${CUBE_SUCCESS_BONUS_WEIGHT:-}"
CUBE_CLOSE_ACTION_WEIGHT="${CUBE_CLOSE_ACTION_WEIGHT:-}"
CUBE_LIFT_ACTION_WEIGHT="${CUBE_LIFT_ACTION_WEIGHT:-}"
CUBE_DESCEND_ACTION_PENALTY_WEIGHT="${CUBE_DESCEND_ACTION_PENALTY_WEIGHT:-}"
CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT="${CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT:-}"
CUBE_GRIPPER_CLOSE_REG_WEIGHT="${CUBE_GRIPPER_CLOSE_REG_WEIGHT:-}"
CUBE_ACTION_PENALTY_WEIGHT="${CUBE_ACTION_PENALTY_WEIGHT:-}"

RUN_DIR_HOST="$RESULTS_NFS/logs/rl_games/dextrah_bimanual_yam_cube_grasp/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/bimanual_yam_cube_rl_${SLURM_JOB_ID:-0}.out"

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
elif git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

echo "Running DEXTRAH bimanual YAM cube-grasp 1-GPU RL"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "NUM_ENVS=$NUM_ENVS"
echo "MAX_ITERATIONS=$MAX_ITERATIONS"
echo "HORIZON_LENGTH=$HORIZON_LENGTH"
echo "MINIBATCH_SIZE=$MINIBATCH_SIZE"
echo "CENTRAL_VALUE_MINIBATCH_SIZE=$CENTRAL_VALUE_MINIBATCH_SIZE"
echo "SAVE_FREQUENCY=$SAVE_FREQUENCY"
echo "LEARNING_RATE=$LEARNING_RATE"
echo "CENTRAL_VALUE_LEARNING_RATE=$CENTRAL_VALUE_LEARNING_RATE"
echo "MINI_EPOCHS=$MINI_EPOCHS"
echo "GAMMA=$GAMMA"
echo "TAU=$TAU"
echo "KL_THRESHOLD=$KL_THRESHOLD"
echo "ENTROPY_COEF=$ENTROPY_COEF"
echo "E_CLIP=$E_CLIP"
echo "GRAD_NORM=$GRAD_NORM"
echo "SIGMA_INIT_VAL=$SIGMA_INIT_VAL"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "CUBE_APPROACH_WEIGHT=$CUBE_APPROACH_WEIGHT"
echo "CUBE_ENCLOSURE_WEIGHT=$CUBE_ENCLOSURE_WEIGHT"
echo "CUBE_SIDE_ALIGNMENT_WEIGHT=$CUBE_SIDE_ALIGNMENT_WEIGHT"
echo "CUBE_LIFT_WEIGHT=$CUBE_LIFT_WEIGHT"
echo "CUBE_HEIGHT_TRACKING_WEIGHT=$CUBE_HEIGHT_TRACKING_WEIGHT"
echo "CUBE_XY_STABILITY_WEIGHT=$CUBE_XY_STABILITY_WEIGHT"
echo "CUBE_SUCCESS_BONUS_WEIGHT=$CUBE_SUCCESS_BONUS_WEIGHT"
echo "CUBE_CLOSE_ACTION_WEIGHT=$CUBE_CLOSE_ACTION_WEIGHT"
echo "CUBE_LIFT_ACTION_WEIGHT=$CUBE_LIFT_ACTION_WEIGHT"
echo "CUBE_DESCEND_ACTION_PENALTY_WEIGHT=$CUBE_DESCEND_ACTION_PENALTY_WEIGHT"
echo "CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT=$CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT"
echo "CUBE_GRIPPER_CLOSE_REG_WEIGHT=$CUBE_GRIPPER_CLOSE_REG_WEIGHT"
echo "CUBE_ACTION_PENALTY_WEIGHT=$CUBE_ACTION_PENALTY_WEIGHT"
echo "DEXTRAH_RLGAMES_JSONL_METRICS=$DEXTRAH_RLGAMES_JSONL_METRICS"
echo "AUTO_RESUME=$AUTO_RESUME"
echo "CHECKPOINT=$CHECKPOINT"
echo "PREPARE_YAM_ASSETS=$PREPARE_YAM_ASSETS"

export TASK RUN_NAME NUM_ENVS MAX_ITERATIONS HORIZON_LENGTH MINIBATCH_SIZE CENTRAL_VALUE_MINIBATCH_SIZE
export LEARNING_RATE CENTRAL_VALUE_LEARNING_RATE MINI_EPOCHS SAVE_FREQUENCY GAMMA TAU KL_THRESHOLD
export ENTROPY_COEF E_CLIP GRAD_NORM SIGMA_INIT_VAL USE_CUDA_GRAPH SEED CUBE_SPAWN_XY_RANDOMIZATION
export DEXTRAH_RLGAMES_JSONL_METRICS AUTO_RESUME CHECKPOINT ENV_NAME PREPARE_YAM_ASSETS
export CUBE_APPROACH_WEIGHT CUBE_ENCLOSURE_WEIGHT CUBE_SIDE_ALIGNMENT_WEIGHT CUBE_LIFT_WEIGHT
export CUBE_HEIGHT_TRACKING_WEIGHT CUBE_XY_STABILITY_WEIGHT CUBE_SUCCESS_BONUS_WEIGHT
export CUBE_CLOSE_ACTION_WEIGHT CUBE_LIFT_ACTION_WEIGHT CUBE_DESCEND_ACTION_PENALTY_WEIGHT
export CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT CUBE_GRIPPER_CLOSE_REG_WEIGHT CUBE_ACTION_PENALTY_WEIGHT

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euxo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    export DEXTRAH_AUTO_RESUME="$AUTO_RESUME"
    export DEXTRAH_RUN_NAME="$RUN_NAME"
    export DEXTRAH_LOG_ROOT=/results/logs
    export DEXTRAH_RLGAMES_JSONL_METRICS="$DEXTRAH_RLGAMES_JSONL_METRICS"
    mkdir -p /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default /results/logs

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

    RESUME_ARGS=()
    if [ -n "$CHECKPOINT" ]; then
      RESUME_ARGS=(--checkpoint "$CHECKPOINT")
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
    append_env_override cube_approach_weight "$CUBE_APPROACH_WEIGHT"
    append_env_override cube_enclosure_weight "$CUBE_ENCLOSURE_WEIGHT"
    append_env_override cube_side_alignment_weight "$CUBE_SIDE_ALIGNMENT_WEIGHT"
    append_env_override cube_lift_weight "$CUBE_LIFT_WEIGHT"
    append_env_override cube_height_tracking_weight "$CUBE_HEIGHT_TRACKING_WEIGHT"
    append_env_override cube_xy_stability_weight "$CUBE_XY_STABILITY_WEIGHT"
    append_env_override cube_success_bonus_weight "$CUBE_SUCCESS_BONUS_WEIGHT"
    append_env_override cube_close_action_weight "$CUBE_CLOSE_ACTION_WEIGHT"
    append_env_override cube_lift_action_weight "$CUBE_LIFT_ACTION_WEIGHT"
    append_env_override cube_descend_action_penalty_weight "$CUBE_DESCEND_ACTION_PENALTY_WEIGHT"
    append_env_override cube_table_clearance_penalty_weight "$CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT"
    append_env_override cube_gripper_close_reg_weight "$CUBE_GRIPPER_CLOSE_REG_WEIGHT"
    append_env_override cube_action_penalty_weight "$CUBE_ACTION_PENALTY_WEIGHT"

    TRAIN_ARGS=(
      train.py
      --headless
      --task="$TASK"
      --seed "$SEED"
      --num_envs "$NUM_ENVS"
      --max_iterations "$MAX_ITERATIONS"
      "${RESUME_ARGS[@]}"
      agent.params.config.minibatch_size="$MINIBATCH_SIZE"
      agent.params.config.central_value_config.minibatch_size="$CENTRAL_VALUE_MINIBATCH_SIZE"
      agent.params.config.learning_rate="$LEARNING_RATE"
      agent.params.config.central_value_config.learning_rate="$CENTRAL_VALUE_LEARNING_RATE"
      agent.params.config.horizon_length="$HORIZON_LENGTH"
      agent.params.config.mini_epochs="$MINI_EPOCHS"
      agent.params.config.gamma="$GAMMA"
      agent.params.config.tau="$TAU"
      agent.params.config.kl_threshold="$KL_THRESHOLD"
      agent.params.config.central_value_config.kl_threshold="$KL_THRESHOLD"
      agent.params.config.entropy_coef="$ENTROPY_COEF"
      agent.params.network.space.continuous.sigma_init.val="$SIGMA_INIT_VAL"
      agent.params.config.e_clip="$E_CLIP"
      agent.params.config.grad_norm="$GRAD_NORM"
      agent.params.config.save_frequency="$SAVE_FREQUENCY"
      agent.params.config.multi_gpu=False
      "${TASK_OVERRIDES[@]}"
    )

    printf "train_command="
    printf "%q " /isaac-sim/python.sh "${TRAIN_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${TRAIN_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load|nan|NaN" "$LOG_FILE" >/dev/null; then
  echo "Detected training error patterns in $LOG_FILE." >&2
  exit 1
fi

if [ ! -d "$RUN_DIR_HOST/nn" ] || ! find "$RUN_DIR_HOST/nn" -maxdepth 1 -type f -name "*.pth" | grep -q .; then
  echo "Missing checkpoint under $RUN_DIR_HOST/nn" >&2
  exit 1
fi

if [ "$DEXTRAH_RLGAMES_JSONL_METRICS" = "True" ] && [ ! -s "$RUN_DIR_HOST/metrics/direct_info_rank_0.jsonl" ]; then
  echo "Missing JSONL metrics: $RUN_DIR_HOST/metrics/direct_info_rank_0.jsonl" >&2
  exit 1
fi

echo "Bimanual YAM cube 1-GPU training done"
