#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_policy_state
#SBATCH --partition=batch
#SBATCH --time=0-00:35:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=12
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/audit_franka_cube_policy_state_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_policy_state_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-64}"
NUM_RESETS="${NUM_RESETS:-3}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:?Set GRASP_PRIOR_LIBRARY_PATH to a library path visible inside the container.}"
CHECKPOINTS="${CHECKPOINTS:?Set CHECKPOINTS to comma- or semicolon-separated label=/container/path checkpoint pairs.}"
TRAINING_JSONL_PATH="${TRAINING_JSONL_PATH:-}"
STOCHASTIC_SAMPLES="${STOCHASTIC_SAMPLES:-16}"
HISTOGRAM_BINS="${HISTOGRAM_BINS:-41}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/diagnostics/$RUN_NAME"
RUN_DIR_CONTAINER="/results/diagnostics/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/audit_franka_cube_policy_state_${SLURM_JOB_ID_SAFE}.out"

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

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi

GRASP_PRIOR_LIBRARY_HOST="$(container_to_host_path "$GRASP_PRIOR_LIBRARY_PATH")"
GRASP_PRIOR_LIBRARY_ARG="$(host_to_container_path "$GRASP_PRIOR_LIBRARY_PATH")"
if [ ! -f "$GRASP_PRIOR_LIBRARY_HOST" ]; then
  echo "Missing grasp prior library: $GRASP_PRIOR_LIBRARY_HOST"
  exit 2
fi

CHECKPOINTS_PARSE="${CHECKPOINTS//;/,}"
IFS=',' read -r -a CHECKPOINT_ITEMS <<<"$CHECKPOINTS_PARSE"
CHECKPOINT_CONTAINER_ITEMS=()
for item in "${CHECKPOINT_ITEMS[@]}"; do
  if [[ "$item" != *=* ]]; then
    echo "CHECKPOINTS item must be label=path, got: $item"
    exit 2
  fi
  label="${item%%=*}"
  path="${item#*=}"
  host_path="$(container_to_host_path "$path")"
  container_path="$(host_to_container_path "$path")"
  if [ ! -f "$host_path" ]; then
    echo "Missing checkpoint for $label: $host_path"
    exit 2
  fi
  CHECKPOINT_CONTAINER_ITEMS+=("$label=$container_path")
done
CHECKPOINTS_CONTAINER="$(IFS=','; echo "${CHECKPOINT_CONTAINER_ITEMS[*]}")"

TRAINING_JSONL_ARG=""
if [ -n "$TRAINING_JSONL_PATH" ]; then
  TRAINING_JSONL_HOST="$(container_to_host_path "$TRAINING_JSONL_PATH")"
  TRAINING_JSONL_ARG="$(host_to_container_path "$TRAINING_JSONL_PATH")"
  if [ ! -f "$TRAINING_JSONL_HOST" ]; then
    echo "Missing training JSONL: $TRAINING_JSONL_HOST"
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

export TASK RUN_NAME NUM_ENVS NUM_RESETS SEED CUBE_SPAWN_XY_RANDOMIZATION
export GRASP_PRIOR_LIBRARY_ARG CHECKPOINTS CHECKPOINTS_CONTAINER TRAINING_JSONL_ARG
export STOCHASTIC_SAMPLES HISTOGRAM_BINS CODE_COMMIT RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube reset-prior policy state audit"
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
echo "CHECKPOINTS=$CHECKPOINTS"
echo "CHECKPOINTS_CONTAINER=$CHECKPOINTS_CONTAINER"
echo "TRAINING_JSONL_ARG=$TRAINING_JSONL_ARG"
echo "STOCHASTIC_SAMPLES=$STOCHASTIC_SAMPLES"
echo "HISTOGRAM_BINS=$HISTOGRAM_BINS"
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
    IFS=',' read -r -a CHECKPOINT_ITEMS_INNER <<<"$CHECKPOINTS_CONTAINER"
    CHECKPOINT_ARGS=()
    for item in "${CHECKPOINT_ITEMS_INNER[@]}"; do
      CHECKPOINT_ARGS+=(--checkpoint "$item")
    done

    AUDIT_ARGS=(
      audit_franka_cube_policy_state.py
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
      --stochastic_samples "$STOCHASTIC_SAMPLES"
      --histogram_bins "$HISTOGRAM_BINS"
      "${CHECKPOINT_ARGS[@]}"
      agent.wandb_activate=False
      env.use_cuda_graph=False
      env.grasp_prior_reset_enabled=True
      env.grasp_prior_library_path="$GRASP_PRIOR_LIBRARY_ARG"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
    )
    if [ -n "$TRAINING_JSONL_ARG" ]; then
      AUDIT_ARGS+=(--training_jsonl_path "$TRAINING_JSONL_ARG")
    fi

    printf "policy_state_audit_command="
    printf "%q " /isaac-sim/python.sh "${AUDIT_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${AUDIT_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected policy state audit error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing policy state audit metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

echo "Policy state audit Done"
