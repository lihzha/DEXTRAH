#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_multi_eval
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_%j.out

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

TASK="${TASK:-Dextrah-Franka-Multi-Object-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_multi_object_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-4}"
NUM_STEPS="${NUM_STEPS:-600}"
VIDEO_LENGTH="${VIDEO_LENGTH:-600}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-multi-object-grasp-eval}"
PRINT_INTERVAL="${PRINT_INTERVAL:-20}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
DETERMINISTIC="${DETERMINISTIC:-True}"
SUPPRESS_SUCCESS_TERMINATION="${SUPPRESS_SUCCESS_TERMINATION:-False}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:-42}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to a checkpoint path visible in /results or on the host}"

OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-}"
OBJECT_ASSETS_DIR="${OBJECT_ASSETS_DIR:-}"
MAX_OBJECTS="${MAX_OBJECTS:-4}"
OBJECT_ASSET_ASSIGNMENT="${OBJECT_ASSET_ASSIGNMENT:-round_robin}"
OBJECT_SPAWN_CENTER_OFFSET_X="${OBJECT_SPAWN_CENTER_OFFSET_X:-0.05}"
OBJECT_SPAWN_CENTER_OFFSET_Y="${OBJECT_SPAWN_CENTER_OFFSET_Y:-0.0}"
OBJECT_SPAWN_XY_RANDOMIZATION="${OBJECT_SPAWN_XY_RANDOMIZATION:-0.10}"
OBJECT_SPAWN_YAW_RANDOMIZATION_DEG="${OBJECT_SPAWN_YAW_RANDOMIZATION_DEG:-180.0}"
GRASP_PRIOR_RESET_ENABLED="${GRASP_PRIOR_RESET_ENABLED:-False}"
GRASP_PRIOR_LIBRARY_DIR="${GRASP_PRIOR_LIBRARY_DIR:-}"
GRASP_PRIOR_ALLOW_MISSING="${GRASP_PRIOR_ALLOW_MISSING:-False}"

CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
CAMERA_ENV_INDEX="${CAMERA_ENV_INDEX:-0}"

CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
TRACE_CSV_CONTAINER="$RUN_DIR_CONTAINER/trace.csv"
TRACE_JSONL_CONTAINER="$RUN_DIR_CONTAINER/trace.jsonl"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_franka_multi_object_${SLURM_JOB_ID_SAFE}.out"

CHECKPOINT_ARG="$CHECKPOINT"
CHECKPOINT_HOST="$CHECKPOINT"
if [[ "$CHECKPOINT" == /results/* ]]; then
  CHECKPOINT_HOST="$RESULTS_NFS/${CHECKPOINT#/results/}"
elif [[ "$CHECKPOINT" == "$RESULTS_NFS"/* ]]; then
  rel_checkpoint="${CHECKPOINT#$RESULTS_NFS/}"
  CHECKPOINT_ARG="/results/$rel_checkpoint"
fi

manifest_host=""
if [ -n "$OBJECT_ASSET_MANIFEST_PATH" ]; then
  if [[ "$OBJECT_ASSET_MANIFEST_PATH" == /results/* ]]; then
    manifest_host="$RESULTS_NFS/${OBJECT_ASSET_MANIFEST_PATH#/results/}"
  elif [[ "$OBJECT_ASSET_MANIFEST_PATH" == "$RESULTS_NFS"/* ]]; then
    rel_manifest="${OBJECT_ASSET_MANIFEST_PATH#$RESULTS_NFS/}"
    OBJECT_ASSET_MANIFEST_PATH="/results/$rel_manifest"
    manifest_host="$RESULTS_NFS/$rel_manifest"
  fi
fi

prior_host=""
if [ -n "$GRASP_PRIOR_LIBRARY_DIR" ]; then
  if [[ "$GRASP_PRIOR_LIBRARY_DIR" == /results/* ]]; then
    prior_host="$RESULTS_NFS/${GRASP_PRIOR_LIBRARY_DIR#/results/}"
  elif [[ "$GRASP_PRIOR_LIBRARY_DIR" == "$RESULTS_NFS"/* ]]; then
    rel_prior="${GRASP_PRIOR_LIBRARY_DIR#$RESULTS_NFS/}"
    GRASP_PRIOR_LIBRARY_DIR="/results/$rel_prior"
    prior_host="$RESULTS_NFS/$rel_prior"
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
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ -n "$manifest_host" ] && [ ! -f "$manifest_host" ]; then
  echo "Missing object asset manifest: $manifest_host"
  exit 2
fi
case "$GRASP_PRIOR_RESET_ENABLED" in
  True|true|1|yes|Yes)
    if [ -z "$GRASP_PRIOR_LIBRARY_DIR" ]; then
      echo "GRASP_PRIOR_RESET_ENABLED=True requires GRASP_PRIOR_LIBRARY_DIR"
      exit 2
    fi
    if [ -n "$prior_host" ] && [ ! -d "$prior_host" ]; then
      echo "Missing grasp prior library dir: $prior_host"
      exit 2
    fi
    ;;
esac

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH VIDEO_NAME_PREFIX PRINT_INTERVAL CAPTURE_VIDEO
export DETERMINISTIC SUPPRESS_SUCCESS_TERMINATION USE_CUDA_GRAPH SEED CHECKPOINT_ARG
export OBJECT_ASSET_MANIFEST_PATH OBJECT_ASSETS_DIR MAX_OBJECTS OBJECT_ASSET_ASSIGNMENT
export OBJECT_SPAWN_CENTER_OFFSET_X OBJECT_SPAWN_CENTER_OFFSET_Y OBJECT_SPAWN_XY_RANDOMIZATION
export OBJECT_SPAWN_YAW_RANDOMIZATION_DEG GRASP_PRIOR_RESET_ENABLED GRASP_PRIOR_LIBRARY_DIR GRASP_PRIOR_ALLOW_MISSING
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z CAMERA_ENV_INDEX
export RUN_DIR_CONTAINER METRICS_CONTAINER TRACE_CSV_CONTAINER TRACE_JSONL_CONTAINER ENV_NAME CODE_COMMIT

echo "Running DextrAH Franka multi-object checkpoint evaluation"
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
echo "VIDEO_NAME_PREFIX=$VIDEO_NAME_PREFIX"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "DETERMINISTIC=$DETERMINISTIC"
echo "SUPPRESS_SUCCESS_TERMINATION=$SUPPRESS_SUCCESS_TERMINATION"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
echo "OBJECT_ASSET_MANIFEST_PATH=$OBJECT_ASSET_MANIFEST_PATH"
echo "OBJECT_ASSETS_DIR=$OBJECT_ASSETS_DIR"
echo "MAX_OBJECTS=$MAX_OBJECTS"
echo "OBJECT_ASSET_ASSIGNMENT=$OBJECT_ASSET_ASSIGNMENT"
echo "OBJECT_SPAWN_CENTER_OFFSET_X=$OBJECT_SPAWN_CENTER_OFFSET_X"
echo "OBJECT_SPAWN_CENTER_OFFSET_Y=$OBJECT_SPAWN_CENTER_OFFSET_Y"
echo "OBJECT_SPAWN_XY_RANDOMIZATION=$OBJECT_SPAWN_XY_RANDOMIZATION"
echo "OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
echo "GRASP_PRIOR_RESET_ENABLED=$GRASP_PRIOR_RESET_ENABLED"
echo "GRASP_PRIOR_LIBRARY_DIR=$GRASP_PRIOR_LIBRARY_DIR"
echo "GRASP_PRIOR_ALLOW_MISSING=$GRASP_PRIOR_ALLOW_MISSING"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "CAMERA_ENV_INDEX=$CAMERA_ENV_INDEX"
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

    SUPPRESS_SUCCESS_TERMINATION_ARGS=(--no-suppress_success_termination)
    if [ "$SUPPRESS_SUCCESS_TERMINATION" = "True" ]; then
      SUPPRESS_SUCCESS_TERMINATION_ARGS=(--suppress_success_termination)
    fi

    TASK_OVERRIDES=(
      agent.wandb_activate=False
      env.use_cuda_graph="$USE_CUDA_GRAPH"
      env.max_objects="$MAX_OBJECTS"
      env.object_asset_assignment="$OBJECT_ASSET_ASSIGNMENT"
      env.object_spawn_center_offset_x="$OBJECT_SPAWN_CENTER_OFFSET_X"
      env.object_spawn_center_offset_y="$OBJECT_SPAWN_CENTER_OFFSET_Y"
      env.object_spawn_xy_randomization="$OBJECT_SPAWN_XY_RANDOMIZATION"
      env.object_spawn_yaw_randomization_deg="$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
    )
    if [ -n "$OBJECT_ASSET_MANIFEST_PATH" ]; then
      TASK_OVERRIDES+=(env.object_asset_manifest_path="$OBJECT_ASSET_MANIFEST_PATH")
    fi
    if [ -n "$OBJECT_ASSETS_DIR" ]; then
      TASK_OVERRIDES+=(env.object_assets_dir="$OBJECT_ASSETS_DIR")
    fi
    case "$GRASP_PRIOR_RESET_ENABLED" in
      True|true|1|yes|Yes)
        TASK_OVERRIDES+=(env.grasp_prior_reset_enabled=True)
        TASK_OVERRIDES+=(env.grasp_prior_library_dir="$GRASP_PRIOR_LIBRARY_DIR")
        TASK_OVERRIDES+=(env.grasp_prior_allow_missing="$GRASP_PRIOR_ALLOW_MISSING")
        ;;
    esac

    EVAL_ARGS=(
      eval_rollout.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --trace_csv_path "$TRACE_CSV_CONTAINER"
      --trace_jsonl_path "$TRACE_JSONL_CONTAINER"
      --checkpoint "$CHECKPOINT_ARG"
      --action_source policy
      --print_interval "$PRINT_INTERVAL"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      --camera_env_index "$CAMERA_ENV_INDEX"
      "${VIDEO_ARGS[@]}"
      "${DETERMINISTIC_ARGS[@]}"
      "${SUPPRESS_SUCCESS_TERMINATION_ARGS[@]}"
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

if [ "$CAPTURE_VIDEO" = "True" ] && ! find "$RUN_DIR_HOST/videos" -type f -name "*.mp4" -print -quit 2>/dev/null | grep -q .; then
  echo "Missing eval video in $RUN_DIR_HOST/videos"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" <<'PY'
import json
import sys

metrics_path = sys.argv[1]
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)
summary = payload.get("summary", {})
print("Eval metrics summary:")
for key in (
    "num_steps_completed",
    "success_rate_final",
    "success_rate_max",
    "success_ever_rate",
    "final_success_rate",
    "final_lift_height_mean",
    "max_lift_height_mean",
):
    if key in summary:
        print(f"  {key}: {summary[key]}")
PY

echo "Evaluation Done"
