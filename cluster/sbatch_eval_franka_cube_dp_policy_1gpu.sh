#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_dp_eval
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
OFFICIAL_DP_NFS="${OFFICIAL_DP_NFS:-$NFS_ROOT/src/external/real-stanford-diffusion_policy}"
OFFICIAL_DP_ENV_NAME="${OFFICIAL_DP_ENV_NAME:-franka-cube-dp-bc-warmstart-official-dp}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

TASK="${TASK:-Dextrah-Franka-Cube-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_cube_dp_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
NUM_STEPS="${NUM_STEPS:-16}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-2}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-1}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
SUCCESS_WINDOW="${SUCCESS_WINDOW:-16}"
SUCCESS_TIMEOUT_OVERRIDE="${SUCCESS_TIMEOUT_OVERRIDE:-}"
VIDEO_LENGTH="${VIDEO_LENGTH:-16}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-dp-policy-eval}"
PRINT_INTERVAL="${PRINT_INTERVAL:-4}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-False}"
SEED="${SEED:-42}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to an official Diffusion Policy .ckpt path visible inside the container, e.g. /results/dp_bc/checkpoints/latest.ckpt}"

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_franka_cube_dp_policy_${SLURM_JOB_ID_SAFE}.out"
DEBUG_POLICY_TRACE_MAX_CALLS="${DEBUG_POLICY_TRACE_MAX_CALLS:-0}"
DEBUG_POLICY_TRACE_ENV_INDEX="${DEBUG_POLICY_TRACE_ENV_INDEX:-0}"
DEBUG_POLICY_TRACE_PATH="${DEBUG_POLICY_TRACE_PATH:-}"
SUPPORT_DATASET="${SUPPORT_DATASET:-}"
SUPPORT_TRACE_PATH="${SUPPORT_TRACE_PATH:-}"
PHASE_PROGRESS_DATASET="${PHASE_PROGRESS_DATASET:-}"
PHASE_PROGRESS_EPISODE="${PHASE_PROGRESS_EPISODE:-0}"
PHASE_PROGRESS_START_STEP="${PHASE_PROGRESS_START_STEP:-0}"
PHASE_PROGRESS_MODE="${PHASE_PROGRESS_MODE:-dataset}"
PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD="${PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD:-0.55}"
PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD="${PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD:-0.75}"
PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD="${PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD:-0.025}"
DEMO_RESET_DATASET="${DEMO_RESET_DATASET:-}"
DEMO_RESET_EPISODE="${DEMO_RESET_EPISODE:-0}"
DEMO_RESET_STEP="${DEMO_RESET_STEP:-0}"
DEMO_RESET_SOURCE_TRAJECTORY_JSON="${DEMO_RESET_SOURCE_TRAJECTORY_JSON:-}"
DEMO_RESET_SOURCE_FRAME="${DEMO_RESET_SOURCE_FRAME:-}"
DEMO_RESET_JOINT_BLEND_ALPHA="${DEMO_RESET_JOINT_BLEND_ALPHA:-}"
DEMO_RESET_CUBE_POS_BLEND_ALPHA="${DEMO_RESET_CUBE_POS_BLEND_ALPHA:-}"

CHECKPOINT_ARG="$CHECKPOINT"
CHECKPOINT_HOST="$CHECKPOINT"
if [[ "$CHECKPOINT" == /results/* ]]; then
  CHECKPOINT_HOST="$RESULTS_NFS/${CHECKPOINT#/results/}"
elif [[ "$CHECKPOINT" == "$RESULTS_NFS"/* ]]; then
  rel_checkpoint="${CHECKPOINT#$RESULTS_NFS/}"
  CHECKPOINT_ARG="/results/$rel_checkpoint"
fi

SUPPORT_DATASET_ARG="$SUPPORT_DATASET"
SUPPORT_DATASET_HOST="$SUPPORT_DATASET"
if [ -n "$SUPPORT_DATASET" ]; then
  if [[ "$SUPPORT_DATASET" == /results/* ]]; then
    SUPPORT_DATASET_HOST="$RESULTS_NFS/${SUPPORT_DATASET#/results/}"
  elif [[ "$SUPPORT_DATASET" == "$RESULTS_NFS"/* ]]; then
    rel_support_dataset="${SUPPORT_DATASET#$RESULTS_NFS/}"
    SUPPORT_DATASET_ARG="/results/$rel_support_dataset"
  fi
fi

PHASE_PROGRESS_DATASET_ARG="$PHASE_PROGRESS_DATASET"
PHASE_PROGRESS_DATASET_HOST="$PHASE_PROGRESS_DATASET"
if [ -n "$PHASE_PROGRESS_DATASET" ]; then
  if [[ "$PHASE_PROGRESS_DATASET" == /results/* ]]; then
    PHASE_PROGRESS_DATASET_HOST="$RESULTS_NFS/${PHASE_PROGRESS_DATASET#/results/}"
  elif [[ "$PHASE_PROGRESS_DATASET" == "$RESULTS_NFS"/* ]]; then
    rel_phase_progress_dataset="${PHASE_PROGRESS_DATASET#$RESULTS_NFS/}"
    PHASE_PROGRESS_DATASET_ARG="/results/$rel_phase_progress_dataset"
  fi
fi

DEMO_RESET_DATASET_ARG="$DEMO_RESET_DATASET"
DEMO_RESET_DATASET_HOST="$DEMO_RESET_DATASET"
if [ -n "$DEMO_RESET_DATASET" ]; then
  if [[ "$DEMO_RESET_DATASET" == /results/* ]]; then
    DEMO_RESET_DATASET_HOST="$RESULTS_NFS/${DEMO_RESET_DATASET#/results/}"
  elif [[ "$DEMO_RESET_DATASET" == "$RESULTS_NFS"/* ]]; then
    rel_demo_reset_dataset="${DEMO_RESET_DATASET#$RESULTS_NFS/}"
    DEMO_RESET_DATASET_ARG="/results/$rel_demo_reset_dataset"
  fi
fi

DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG="$DEMO_RESET_SOURCE_TRAJECTORY_JSON"
DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST="$DEMO_RESET_SOURCE_TRAJECTORY_JSON"
if [ -n "$DEMO_RESET_SOURCE_TRAJECTORY_JSON" ]; then
  if [[ "$DEMO_RESET_SOURCE_TRAJECTORY_JSON" == /results/* ]]; then
    DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST="$RESULTS_NFS/${DEMO_RESET_SOURCE_TRAJECTORY_JSON#/results/}"
  elif [[ "$DEMO_RESET_SOURCE_TRAJECTORY_JSON" == "$RESULTS_NFS"/* ]]; then
    rel_demo_reset_source="${DEMO_RESET_SOURCE_TRAJECTORY_JSON#$RESULTS_NFS/}"
    DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG="/results/$rel_demo_reset_source"
  fi
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -d "$OFFICIAL_DP_NFS/diffusion_policy" ]; then
  echo "Missing official Diffusion Policy checkout: $OFFICIAL_DP_NFS"
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing official Diffusion Policy checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ -n "$SUPPORT_DATASET" ] && [ ! -f "$SUPPORT_DATASET_HOST" ]; then
  echo "Missing support dataset: $SUPPORT_DATASET_HOST"
  exit 2
fi
if [ -n "$PHASE_PROGRESS_DATASET" ] && [ ! -f "$PHASE_PROGRESS_DATASET_HOST" ]; then
  echo "Missing phase/progress dataset: $PHASE_PROGRESS_DATASET_HOST"
  exit 2
fi
if [ -n "$DEMO_RESET_DATASET" ] && [ ! -f "$DEMO_RESET_DATASET_HOST" ]; then
  echo "Missing demo reset dataset: $DEMO_RESET_DATASET_HOST"
  exit 2
fi
if [ -n "$DEMO_RESET_SOURCE_TRAJECTORY_JSON" ] && [ ! -f "$DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST" ]; then
  echo "Missing demo reset source trajectory JSON: $DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS NUM_INFERENCE_STEPS ACTION_CHUNK_STEPS CLIP_ACTIONS SUCCESS_WINDOW
export SUCCESS_TIMEOUT_OVERRIDE
export VIDEO_LENGTH VIDEO_NAME_PREFIX PRINT_INTERVAL CAPTURE_VIDEO SEED
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export CHECKPOINT_ARG RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME OFFICIAL_DP_ENV_NAME
export DEBUG_POLICY_TRACE_MAX_CALLS DEBUG_POLICY_TRACE_ENV_INDEX DEBUG_POLICY_TRACE_PATH
export SUPPORT_DATASET_ARG SUPPORT_TRACE_PATH
export PHASE_PROGRESS_DATASET_ARG PHASE_PROGRESS_EPISODE PHASE_PROGRESS_START_STEP
export PHASE_PROGRESS_MODE PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD
export PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD
export DEMO_RESET_DATASET_ARG DEMO_RESET_EPISODE DEMO_RESET_STEP
export DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG DEMO_RESET_SOURCE_FRAME
export DEMO_RESET_JOINT_BLEND_ALPHA DEMO_RESET_CUBE_POS_BLEND_ALPHA

echo "Running DextrAH Franka cube official Diffusion Policy evaluation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "OFFICIAL_DP_SITE=$ENV_ROOT/$OFFICIAL_DP_ENV_NAME/site"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "NUM_STEPS=$NUM_STEPS"
echo "NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS"
echo "ACTION_CHUNK_STEPS=$ACTION_CHUNK_STEPS"
echo "CLIP_ACTIONS=$CLIP_ACTIONS"
if [ -n "$SUCCESS_TIMEOUT_OVERRIDE" ]; then
  echo "SUCCESS_TIMEOUT_OVERRIDE=$SUCCESS_TIMEOUT_OVERRIDE"
fi
echo "VIDEO_LENGTH=$VIDEO_LENGTH"
echo "VIDEO_NAME_PREFIX=$VIDEO_NAME_PREFIX"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "SEED=$SEED"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
if [ -n "$SUPPORT_DATASET" ]; then
  echo "SUPPORT_DATASET_ARG=$SUPPORT_DATASET_ARG"
  echo "SUPPORT_DATASET_HOST=$SUPPORT_DATASET_HOST"
fi
if [ -n "$PHASE_PROGRESS_DATASET" ]; then
  echo "PHASE_PROGRESS_DATASET_ARG=$PHASE_PROGRESS_DATASET_ARG"
  echo "PHASE_PROGRESS_DATASET_HOST=$PHASE_PROGRESS_DATASET_HOST"
  echo "PHASE_PROGRESS_EPISODE=$PHASE_PROGRESS_EPISODE"
  echo "PHASE_PROGRESS_START_STEP=$PHASE_PROGRESS_START_STEP"
  echo "PHASE_PROGRESS_MODE=$PHASE_PROGRESS_MODE"
  echo "PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=$PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD"
  echo "PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=$PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD"
  echo "PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=$PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD"
fi
if [ -n "$DEMO_RESET_DATASET" ]; then
  echo "DEMO_RESET_DATASET_ARG=$DEMO_RESET_DATASET_ARG"
  echo "DEMO_RESET_DATASET_HOST=$DEMO_RESET_DATASET_HOST"
  echo "DEMO_RESET_EPISODE=$DEMO_RESET_EPISODE"
  echo "DEMO_RESET_STEP=$DEMO_RESET_STEP"
  if [ -n "$DEMO_RESET_SOURCE_TRAJECTORY_JSON" ]; then
    echo "DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG=$DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG"
    echo "DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST=$DEMO_RESET_SOURCE_TRAJECTORY_JSON_HOST"
    echo "DEMO_RESET_SOURCE_FRAME=$DEMO_RESET_SOURCE_FRAME"
  fi
  if [ -n "$DEMO_RESET_JOINT_BLEND_ALPHA" ]; then
    echo "DEMO_RESET_JOINT_BLEND_ALPHA=$DEMO_RESET_JOINT_BLEND_ALPHA"
  fi
  if [ -n "$DEMO_RESET_CUBE_POS_BLEND_ALPHA" ]; then
    echo "DEMO_RESET_CUBE_POS_BLEND_ALPHA=$DEMO_RESET_CUBE_POS_BLEND_ALPHA"
  fi
fi
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "METRICS_CONTAINER=$METRICS_CONTAINER"
echo "DEBUG_POLICY_TRACE_MAX_CALLS=$DEBUG_POLICY_TRACE_MAX_CALLS"
echo "DEBUG_POLICY_TRACE_ENV_INDEX=$DEBUG_POLICY_TRACE_ENV_INDEX"
if [ -n "$DEBUG_POLICY_TRACE_PATH" ]; then
  echo "DEBUG_POLICY_TRACE_PATH=$DEBUG_POLICY_TRACE_PATH"
fi

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export DP_SITE="/envs/$OFFICIAL_DP_ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src:/official_dp"
    if [ -d "$DP_SITE" ]; then
      export PYTHONPATH="$DP_SITE:$PYTHONPATH"
    fi
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
    mkdir -p "$RUN_DIR_CONTAINER" /results/logs

    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    echo "git_status_skipped=container_git_lfs_unavailable"
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    SUCCESS_TIMEOUT_ARGS=()
    if [ -n "$SUCCESS_TIMEOUT_OVERRIDE" ]; then
      SUCCESS_TIMEOUT_ARGS=(--success_timeout_override "$SUCCESS_TIMEOUT_OVERRIDE")
    fi
    TRACE_ARGS=()
    if [ "$DEBUG_POLICY_TRACE_MAX_CALLS" != "0" ]; then
      trace_path="$DEBUG_POLICY_TRACE_PATH"
      if [ -z "$trace_path" ]; then
        trace_path="$RUN_DIR_CONTAINER/policy_trace.json"
      fi
      TRACE_ARGS=(
        --debug_policy_trace_path "$trace_path"
        --debug_policy_trace_max_calls "$DEBUG_POLICY_TRACE_MAX_CALLS"
        --debug_policy_trace_env_index "$DEBUG_POLICY_TRACE_ENV_INDEX"
      )
    fi
    SUPPORT_ARGS=()
    if [ -n "$SUPPORT_DATASET_ARG" ]; then
      support_trace_path="$SUPPORT_TRACE_PATH"
      if [ -z "$support_trace_path" ]; then
        support_trace_path="$RUN_DIR_CONTAINER/support_trace.json"
      fi
      SUPPORT_ARGS=(
        --support_dataset "$SUPPORT_DATASET_ARG"
        --support_trace_path "$support_trace_path"
      )
    fi
    PHASE_PROGRESS_ARGS=()
    if [ -n "$PHASE_PROGRESS_DATASET_ARG" ]; then
      PHASE_PROGRESS_ARGS=(
        --phase_progress_dataset "$PHASE_PROGRESS_DATASET_ARG"
        --phase_progress_episode "$PHASE_PROGRESS_EPISODE"
        --phase_progress_start_step "$PHASE_PROGRESS_START_STEP"
        --phase_progress_mode "$PHASE_PROGRESS_MODE"
        --phase_close_support_distance_threshold "$PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD"
        --phase_lift_support_distance_threshold "$PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD"
        --phase_lift_gripper_width_threshold "$PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD"
      )
    fi
    DEMO_RESET_ARGS=()
    if [ -n "$DEMO_RESET_DATASET_ARG" ]; then
      DEMO_RESET_ARGS=(
        --demo_reset_dataset "$DEMO_RESET_DATASET_ARG"
        --demo_reset_episode "$DEMO_RESET_EPISODE"
        --demo_reset_step "$DEMO_RESET_STEP"
      )
      if [ -n "$DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG" ]; then
        DEMO_RESET_ARGS+=(
          --demo_reset_source_trajectory_json "$DEMO_RESET_SOURCE_TRAJECTORY_JSON_ARG"
        )
        if [ -n "$DEMO_RESET_SOURCE_FRAME" ]; then
          DEMO_RESET_ARGS+=(--demo_reset_source_frame "$DEMO_RESET_SOURCE_FRAME")
        fi
      fi
      if [ -n "$DEMO_RESET_JOINT_BLEND_ALPHA" ]; then
        DEMO_RESET_ARGS+=(--demo_reset_joint_blend_alpha "$DEMO_RESET_JOINT_BLEND_ALPHA")
      fi
      if [ -n "$DEMO_RESET_CUBE_POS_BLEND_ALPHA" ]; then
        DEMO_RESET_ARGS+=(--demo_reset_cube_pos_blend_alpha "$DEMO_RESET_CUBE_POS_BLEND_ALPHA")
      fi
    fi

    EVAL_ARGS=(
      /code/dextrah_lab/rl_games/eval_franka_cube_dp_policy.py
      --headless
      --device cuda:0
      --task "$TASK"
      --checkpoint "$CHECKPOINT_ARG"
      --diffusion_policy_root /official_dp
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --num_inference_steps "$NUM_INFERENCE_STEPS"
      --action_chunk_steps "$ACTION_CHUNK_STEPS"
      --clip_actions "$CLIP_ACTIONS"
      --success_window "$SUCCESS_WINDOW"
      "${SUCCESS_TIMEOUT_ARGS[@]}"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      "${TRACE_ARGS[@]}"
      "${SUPPORT_ARGS[@]}"
      "${PHASE_PROGRESS_ARGS[@]}"
      "${DEMO_RESET_ARGS[@]}"
      "${VIDEO_ARGS[@]}"
    )

    printf "eval_command="
    printf "%q " /isaac-sim/python.sh "${EVAL_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${EVAL_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected DP eval error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing DP eval metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi
if [ "$DEBUG_POLICY_TRACE_MAX_CALLS" != "0" ] && [ ! -s "$RUN_DIR_HOST/policy_trace.json" ]; then
  echo "Missing DP eval policy trace JSON: $RUN_DIR_HOST/policy_trace.json"
  exit 1
fi
if [ -n "$SUPPORT_DATASET" ] && [ ! -s "$RUN_DIR_HOST/support_trace.json" ]; then
  echo "Missing DP eval support trace JSON: $RUN_DIR_HOST/support_trace.json"
  exit 1
fi
if [ -n "$SUPPORT_DATASET" ] && [ ! -s "$RUN_DIR_HOST/support_trace.csv" ]; then
  echo "Missing DP eval support trace CSV: $RUN_DIR_HOST/support_trace.csv"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" "$NUM_STEPS" <<'PY'
import json
import math
import sys

metrics_path = sys.argv[1]
requested_steps = int(sys.argv[2])
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

summary = payload.get("summary", {})
if not bool(summary.get("env_closed", False)):
    raise SystemExit("DP eval env did not close cleanly")
if int(summary.get("steps_completed", 0)) < requested_steps:
    raise SystemExit(
        f"DP eval completed {summary.get('steps_completed')} steps, expected {requested_steps}"
    )
for key in ("action_min", "action_max"):
    values = summary.get(key)
    if not isinstance(values, list) or len(values) != 7:
        raise SystemExit(f"Bad {key}: {values}")
    if not all(math.isfinite(float(v)) for v in values):
        raise SystemExit(f"Non-finite {key}: {values}")
print("DP eval metrics passed")
PY

echo "DP Evaluation Done"
