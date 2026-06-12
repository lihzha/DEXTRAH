#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_cube_val
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_env_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-4}"
NUM_STEPS="${NUM_STEPS:-160}"
VIDEO_LENGTH="${VIDEO_LENGTH:-160}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
PRINT_INTERVAL="${PRINT_INTERVAL:-30}"
SEED="${SEED:-42}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
CUBE_SPAWN_YAW_RANDOMIZATION_DEG="${CUBE_SPAWN_YAW_RANDOMIZATION_DEG:-0.0}"
GRASP_PRIOR_RESET_ENABLED="${GRASP_PRIOR_RESET_ENABLED:-False}"
GRASP_PRIOR_LIBRARY_PATH="${GRASP_PRIOR_LIBRARY_PATH:-}"
GRASP_PRIOR_RESET_CYCLES="${GRASP_PRIOR_RESET_CYCLES:-4}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
TRAJECTORY_TRACKING_REFERENCE_PATH="${TRAJECTORY_TRACKING_REFERENCE_PATH:-}"
CUBE_APPROACH_WEIGHT="${CUBE_APPROACH_WEIGHT:-}"
CUBE_ENCLOSURE_WEIGHT="${CUBE_ENCLOSURE_WEIGHT:-}"
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
TRAJECTORY_TRACKING_POSITION_WEIGHT="${TRAJECTORY_TRACKING_POSITION_WEIGHT:-}"
TRAJECTORY_TRACKING_ORIENTATION_WEIGHT="${TRAJECTORY_TRACKING_ORIENTATION_WEIGHT:-}"
TRAJECTORY_TRACKING_GRIPPER_WEIGHT="${TRAJECTORY_TRACKING_GRIPPER_WEIGHT:-}"
TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT="${TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT:-}"
TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT="${TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT:-}"
TRAJECTORY_TRACKING_START_WEIGHT="${TRAJECTORY_TRACKING_START_WEIGHT:-}"
TRAJECTORY_TRACKING_END_WEIGHT="${TRAJECTORY_TRACKING_END_WEIGHT:-}"

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_franka_cube_${SLURM_JOB_ID_SAFE}.out"

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

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH CAPTURE_VIDEO PRINT_INTERVAL SEED CUBE_SPAWN_XY_RANDOMIZATION TRAJECTORY_TRACKING_REFERENCE_PATH
export CUBE_SPAWN_YAW_RANDOMIZATION_DEG
export GRASP_PRIOR_RESET_ENABLED GRASP_PRIOR_LIBRARY_PATH GRASP_PRIOR_RESET_CYCLES CODE_COMMIT
export CUBE_APPROACH_WEIGHT CUBE_ENCLOSURE_WEIGHT CUBE_LIFT_WEIGHT CUBE_HEIGHT_TRACKING_WEIGHT CUBE_XY_STABILITY_WEIGHT CUBE_SUCCESS_BONUS_WEIGHT
export CUBE_CLOSE_ACTION_WEIGHT CUBE_LIFT_ACTION_WEIGHT CUBE_DESCEND_ACTION_PENALTY_WEIGHT CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT CUBE_GRIPPER_CLOSE_REG_WEIGHT CUBE_ACTION_PENALTY_WEIGHT
export TRAJECTORY_TRACKING_POSITION_WEIGHT TRAJECTORY_TRACKING_ORIENTATION_WEIGHT TRAJECTORY_TRACKING_GRIPPER_WEIGHT TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT
export TRAJECTORY_TRACKING_START_WEIGHT TRAJECTORY_TRACKING_END_WEIGHT
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube-grasp environment validation"
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
echo "SEED=$SEED"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "CUBE_SPAWN_YAW_RANDOMIZATION_DEG=$CUBE_SPAWN_YAW_RANDOMIZATION_DEG"
echo "GRASP_PRIOR_RESET_ENABLED=$GRASP_PRIOR_RESET_ENABLED"
echo "GRASP_PRIOR_LIBRARY_PATH=$GRASP_PRIOR_LIBRARY_PATH"
echo "GRASP_PRIOR_RESET_CYCLES=$GRASP_PRIOR_RESET_CYCLES"
echo "TRAJECTORY_TRACKING_REFERENCE_PATH=$TRAJECTORY_TRACKING_REFERENCE_PATH"
echo "CUBE_APPROACH_WEIGHT=$CUBE_APPROACH_WEIGHT"
echo "CUBE_ENCLOSURE_WEIGHT=$CUBE_ENCLOSURE_WEIGHT"
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
echo "TRAJECTORY_TRACKING_POSITION_WEIGHT=$TRAJECTORY_TRACKING_POSITION_WEIGHT"
echo "TRAJECTORY_TRACKING_ORIENTATION_WEIGHT=$TRAJECTORY_TRACKING_ORIENTATION_WEIGHT"
echo "TRAJECTORY_TRACKING_GRIPPER_WEIGHT=$TRAJECTORY_TRACKING_GRIPPER_WEIGHT"
echo "TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT=$TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT"
echo "TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT=$TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT"
echo "TRAJECTORY_TRACKING_START_WEIGHT=$TRAJECTORY_TRACKING_START_WEIGHT"
echo "TRAJECTORY_TRACKING_END_WEIGHT=$TRAJECTORY_TRACKING_END_WEIGHT"
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
    PRIOR_ARGS=()
    case "$GRASP_PRIOR_RESET_ENABLED" in
      True|true|1|yes|Yes)
        if [ -z "$GRASP_PRIOR_LIBRARY_PATH" ]; then
          echo "GRASP_PRIOR_RESET_ENABLED requires GRASP_PRIOR_LIBRARY_PATH" >&2
          exit 2
        fi
        PRIOR_ARGS=(
          --enable_grasp_prior_reset
          --grasp_prior_library_path "$GRASP_PRIOR_LIBRARY_PATH"
          --grasp_prior_reset_cycles "$GRASP_PRIOR_RESET_CYCLES"
        )
        ;;
    esac
    REFERENCE_ARGS=()
    if [ -n "${TRAJECTORY_TRACKING_REFERENCE_PATH:-}" ]; then
      REFERENCE_ARGS=(--trajectory_tracking_reference_path "$TRAJECTORY_TRACKING_REFERENCE_PATH")
    fi
    REWARD_ARGS=()
    append_reward_arg() {
      local flag="$1"
      local value="$2"
      if [ -n "$value" ]; then
        REWARD_ARGS+=(--"$flag" "$value")
      fi
    }
    append_reward_arg cube_approach_weight "$CUBE_APPROACH_WEIGHT"
    append_reward_arg cube_enclosure_weight "$CUBE_ENCLOSURE_WEIGHT"
    append_reward_arg cube_lift_weight "$CUBE_LIFT_WEIGHT"
    append_reward_arg cube_height_tracking_weight "$CUBE_HEIGHT_TRACKING_WEIGHT"
    append_reward_arg cube_xy_stability_weight "$CUBE_XY_STABILITY_WEIGHT"
    append_reward_arg cube_success_bonus_weight "$CUBE_SUCCESS_BONUS_WEIGHT"
    append_reward_arg cube_close_action_weight "$CUBE_CLOSE_ACTION_WEIGHT"
    append_reward_arg cube_lift_action_weight "$CUBE_LIFT_ACTION_WEIGHT"
    append_reward_arg cube_descend_action_penalty_weight "$CUBE_DESCEND_ACTION_PENALTY_WEIGHT"
    append_reward_arg cube_table_clearance_penalty_weight "$CUBE_TABLE_CLEARANCE_PENALTY_WEIGHT"
    append_reward_arg cube_gripper_close_reg_weight "$CUBE_GRIPPER_CLOSE_REG_WEIGHT"
    append_reward_arg cube_action_penalty_weight "$CUBE_ACTION_PENALTY_WEIGHT"
    append_reward_arg trajectory_tracking_position_weight "$TRAJECTORY_TRACKING_POSITION_WEIGHT"
    append_reward_arg trajectory_tracking_orientation_weight "$TRAJECTORY_TRACKING_ORIENTATION_WEIGHT"
    append_reward_arg trajectory_tracking_gripper_weight "$TRAJECTORY_TRACKING_GRIPPER_WEIGHT"
    append_reward_arg trajectory_tracking_close_action_weight "$TRAJECTORY_TRACKING_CLOSE_ACTION_WEIGHT"
    append_reward_arg trajectory_tracking_lift_action_weight "$TRAJECTORY_TRACKING_LIFT_ACTION_WEIGHT"
    append_reward_arg trajectory_tracking_start_weight "$TRAJECTORY_TRACKING_START_WEIGHT"
    append_reward_arg trajectory_tracking_end_weight "$TRAJECTORY_TRACKING_END_WEIGHT"

    VALIDATE_ARGS=(
      validate_franka_cube_grasp_env.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --cube_spawn_xy_randomization "$CUBE_SPAWN_XY_RANDOMIZATION"
      --cube_spawn_yaw_randomization_deg "$CUBE_SPAWN_YAW_RANDOMIZATION_DEG"
      "${PRIOR_ARGS[@]}"
      "${REFERENCE_ARGS[@]}"
      "${REWARD_ARGS[@]}"
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
