#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_prior_audit
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/audit_franka_cube_prior_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_prior_action_audit_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_RESETS="${NUM_RESETS:-3}"
HORIZON_STEPS="${HORIZON_STEPS:-40}"
MATCH_RESET_STATE="${MATCH_RESET_STATE:-False}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:?Set GRASP_PRIOR_LIBRARY_PATH to a library path visible inside the container.}"
CHECKPOINTS="${CHECKPOINTS:?Set CHECKPOINTS to comma- or semicolon-separated label=/container/path checkpoint pairs.}"
DETERMINISTIC="${DETERMINISTIC:-True}"
RENDER="${RENDER:-True}"
RENDER_RESETS="${RENDER_RESETS:-1}"
RENDER_INTERVAL="${RENDER_INTERVAL:-10}"
RENDER_CANDIDATES="${RENDER_CANDIDATES:-policy_ep10,policy_ep45,script_noop,script_hold_open,script_approach_exact_open,script_close_light_pregrasp,script_lift_closed,script_assisted_oracle_short}"
RENDER_CANDIDATES_ARG="${RENDER_CANDIDATES//;/,}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
ORACLE_PROPORTIONAL_GAIN="${ORACLE_PROPORTIONAL_GAIN:-1.0}"
ORACLE_MAX_POSITION_ACTION="${ORACLE_MAX_POSITION_ACTION:-1.0}"
ORACLE_TRACK_ORIENTATION="${ORACLE_TRACK_ORIENTATION:-1}"
CLOSE_WIDTH="${CLOSE_WIDTH:-0.055}"
LIFT_ACTION_Z="${LIFT_ACTION_Z:-0.15}"
ASSISTED_APPROACH_STEPS="${ASSISTED_APPROACH_STEPS:-20}"
ASSISTED_CLOSE_STEPS="${ASSISTED_CLOSE_STEPS:-10}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/diagnostics/$RUN_NAME"
RUN_DIR_CONTAINER="/results/diagnostics/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/audit_franka_cube_prior_${SLURM_JOB_ID_SAFE}.out"

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

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_RESETS HORIZON_STEPS MATCH_RESET_STATE SEED CUBE_SPAWN_XY_RANDOMIZATION
export GRASP_PRIOR_LIBRARY_ARG CHECKPOINTS CHECKPOINTS_CONTAINER DETERMINISTIC RENDER RENDER_RESETS RENDER_INTERVAL RENDER_CANDIDATES RENDER_CANDIDATES_ARG
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export ORACLE_PROPORTIONAL_GAIN ORACLE_MAX_POSITION_ACTION ORACLE_TRACK_ORIENTATION CLOSE_WIDTH LIFT_ACTION_Z
export ASSISTED_APPROACH_STEPS ASSISTED_CLOSE_STEPS CODE_COMMIT RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube reset-prior action/reward audit"
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
echo "HORIZON_STEPS=$HORIZON_STEPS"
echo "MATCH_RESET_STATE=$MATCH_RESET_STATE"
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "GRASP_PRIOR_LIBRARY_ARG=$GRASP_PRIOR_LIBRARY_ARG"
echo "CHECKPOINTS=$CHECKPOINTS"
echo "CHECKPOINTS_CONTAINER=$CHECKPOINTS_CONTAINER"
echo "DETERMINISTIC=$DETERMINISTIC"
echo "RENDER=$RENDER"
echo "RENDER_RESETS=$RENDER_RESETS"
echo "RENDER_INTERVAL=$RENDER_INTERVAL"
echo "RENDER_CANDIDATES=$RENDER_CANDIDATES"
echo "RENDER_CANDIDATES_ARG=$RENDER_CANDIDATES_ARG"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "ORACLE_PROPORTIONAL_GAIN=$ORACLE_PROPORTIONAL_GAIN"
echo "ORACLE_MAX_POSITION_ACTION=$ORACLE_MAX_POSITION_ACTION"
echo "ORACLE_TRACK_ORIENTATION=$ORACLE_TRACK_ORIENTATION"
echo "CLOSE_WIDTH=$CLOSE_WIDTH"
echo "LIFT_ACTION_Z=$LIFT_ACTION_Z"
echo "ASSISTED_APPROACH_STEPS=$ASSISTED_APPROACH_STEPS"
echo "ASSISTED_CLOSE_STEPS=$ASSISTED_CLOSE_STEPS"
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
      audit_franka_cube_grasp_prior_actions.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_resets "$NUM_RESETS"
      --horizon_steps "$HORIZON_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --cube_spawn_xy_randomization "$CUBE_SPAWN_XY_RANDOMIZATION"
      --grasp_prior_library_path "$GRASP_PRIOR_LIBRARY_ARG"
      --render_resets "$RENDER_RESETS"
      --render_interval "$RENDER_INTERVAL"
      --render_candidates "$RENDER_CANDIDATES_ARG"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      --oracle_proportional_gain "$ORACLE_PROPORTIONAL_GAIN"
      --oracle_max_position_action "$ORACLE_MAX_POSITION_ACTION"
      --close_width "$CLOSE_WIDTH"
      --lift_action_z "$LIFT_ACTION_Z"
      --assisted_approach_steps "$ASSISTED_APPROACH_STEPS"
      --assisted_close_steps "$ASSISTED_CLOSE_STEPS"
      "${CHECKPOINT_ARGS[@]}"
      agent.wandb_activate=False
      env.use_cuda_graph=False
      env.grasp_prior_reset_enabled=True
      env.grasp_prior_library_path="$GRASP_PRIOR_LIBRARY_ARG"
      env.cube_spawn_xy_randomization="$CUBE_SPAWN_XY_RANDOMIZATION"
    )
    if [ "$RENDER" = "1" ] || [ "$RENDER" = "true" ] || [ "$RENDER" = "True" ]; then
      AUDIT_ARGS+=(--render)
    fi
    if [ "$DETERMINISTIC" = "False" ] || [ "$DETERMINISTIC" = "false" ] || [ "$DETERMINISTIC" = "0" ]; then
      AUDIT_ARGS+=(--no-deterministic)
    else
      AUDIT_ARGS+=(--deterministic)
    fi
    if [ "$MATCH_RESET_STATE" = "1" ] || [ "$MATCH_RESET_STATE" = "true" ] || [ "$MATCH_RESET_STATE" = "True" ]; then
      AUDIT_ARGS+=(--match_reset_state)
    else
      AUDIT_ARGS+=(--no-match_reset_state)
    fi
    if [ "$ORACLE_TRACK_ORIENTATION" = "1" ] || [ "$ORACLE_TRACK_ORIENTATION" = "true" ] || [ "$ORACLE_TRACK_ORIENTATION" = "True" ]; then
      AUDIT_ARGS+=(--oracle_track_orientation)
    fi

    printf "audit_command="
    printf "%q " /isaac-sim/python.sh "${AUDIT_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${AUDIT_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected audit error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing audit metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

echo "Action/reward audit Done"
