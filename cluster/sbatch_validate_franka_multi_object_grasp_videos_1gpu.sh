#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_franka_multi_vid
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_%j.out

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
RUN_NAME="${RUN_NAME:-franka_multi_object_video_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-4}"
SEED="${SEED:-42}"
OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-}"
MAX_OBJECTS="${MAX_OBJECTS:-4}"
OBJECT_ASSET_ASSIGNMENT="${OBJECT_ASSET_ASSIGNMENT:-round_robin}"
OBJECT_SPAWN_CENTER_OFFSET_X="${OBJECT_SPAWN_CENTER_OFFSET_X:-0.05}"
OBJECT_SPAWN_CENTER_OFFSET_Y="${OBJECT_SPAWN_CENTER_OFFSET_Y:-0.0}"
OBJECT_SPAWN_XY_RANDOMIZATION="${OBJECT_SPAWN_XY_RANDOMIZATION:-0.10}"
OBJECT_SPAWN_YAW_RANDOMIZATION_DEG="${OBJECT_SPAWN_YAW_RANDOMIZATION_DEG:-180.0}"
RENDER_WARMUP_FRAMES="${RENDER_WARMUP_FRAMES:-2}"
RESET_CYCLES="${RESET_CYCLES:-3}"
SETTLE_STEPS="${SETTLE_STEPS:-72}"
PERTURB_STEPS="${PERTURB_STEPS:-96}"
PERTURB_PUSH_STEPS="${PERTURB_PUSH_STEPS:-10}"
PERTURB_LINEAR_VELOCITY="${PERTURB_LINEAR_VELOCITY:-0.60}"
PERTURB_LATERAL_VELOCITY="${PERTURB_LATERAL_VELOCITY:-0.20}"
PERTURB_ANGULAR_VELOCITY="${PERTURB_ANGULAR_VELOCITY:-4.0}"
GRASP_STEPS="${GRASP_STEPS:-72}"
GRASP_OBJECT_SETTLE_STEPS="${GRASP_OBJECT_SETTLE_STEPS:-48}"
OBJECT_RESET_SETTLE_STEPS="${OBJECT_RESET_SETTLE_STEPS:-120}"
CAPTURE_INTERVAL="${CAPTURE_INTERVAL:-2}"
GRASP_RESET_ATTEMPTS="${GRASP_RESET_ATTEMPTS:-12}"
GRASP_RESET_MIN_PREGRASP_Z="${GRASP_RESET_MIN_PREGRASP_Z:-0.15}"
GRASP_CONTACT_SCORE_STEPS="${GRASP_CONTACT_SCORE_STEPS:-60}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/video_metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_franka_multi_object_videos_${SLURM_JOB_ID_SAFE}.out"

if [ -z "$OBJECT_ASSET_MANIFEST_PATH" ]; then
  echo "OBJECT_ASSET_MANIFEST_PATH is required"
  exit 2
fi
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

export TASK RUN_NAME NUM_ENVS SEED OBJECT_ASSET_MANIFEST_PATH MAX_OBJECTS OBJECT_ASSET_ASSIGNMENT
export OBJECT_SPAWN_CENTER_OFFSET_X OBJECT_SPAWN_CENTER_OFFSET_Y OBJECT_SPAWN_XY_RANDOMIZATION
export OBJECT_SPAWN_YAW_RANDOMIZATION_DEG RENDER_WARMUP_FRAMES
export RESET_CYCLES SETTLE_STEPS PERTURB_STEPS PERTURB_PUSH_STEPS
export PERTURB_LINEAR_VELOCITY PERTURB_LATERAL_VELOCITY PERTURB_ANGULAR_VELOCITY
export GRASP_STEPS GRASP_OBJECT_SETTLE_STEPS CAPTURE_INTERVAL GRASP_RESET_ATTEMPTS GRASP_RESET_MIN_PREGRASP_Z
export GRASP_CONTACT_SCORE_STEPS
export OBJECT_RESET_SETTLE_STEPS
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME CODE_COMMIT

echo "Running DextrAH Franka multi-object video validation"
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
echo "SEED=$SEED"
echo "OBJECT_ASSET_MANIFEST_PATH=$OBJECT_ASSET_MANIFEST_PATH"
echo "MAX_OBJECTS=$MAX_OBJECTS"
echo "OBJECT_ASSET_ASSIGNMENT=$OBJECT_ASSET_ASSIGNMENT"
echo "OBJECT_SPAWN_CENTER_OFFSET_X=$OBJECT_SPAWN_CENTER_OFFSET_X"
echo "OBJECT_SPAWN_CENTER_OFFSET_Y=$OBJECT_SPAWN_CENTER_OFFSET_Y"
echo "OBJECT_SPAWN_XY_RANDOMIZATION=$OBJECT_SPAWN_XY_RANDOMIZATION"
echo "OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
echo "RESET_CYCLES=$RESET_CYCLES"
echo "SETTLE_STEPS=$SETTLE_STEPS"
echo "PERTURB_STEPS=$PERTURB_STEPS"
echo "PERTURB_PUSH_STEPS=$PERTURB_PUSH_STEPS"
echo "PERTURB_LINEAR_VELOCITY=$PERTURB_LINEAR_VELOCITY"
echo "PERTURB_LATERAL_VELOCITY=$PERTURB_LATERAL_VELOCITY"
echo "PERTURB_ANGULAR_VELOCITY=$PERTURB_ANGULAR_VELOCITY"
echo "GRASP_STEPS=$GRASP_STEPS"
echo "GRASP_OBJECT_SETTLE_STEPS=$GRASP_OBJECT_SETTLE_STEPS"
echo "OBJECT_RESET_SETTLE_STEPS=$OBJECT_RESET_SETTLE_STEPS"
echo "CAPTURE_INTERVAL=$CAPTURE_INTERVAL"
echo "GRASP_RESET_ATTEMPTS=$GRASP_RESET_ATTEMPTS"
echo "GRASP_RESET_MIN_PREGRASP_Z=$GRASP_RESET_MIN_PREGRASP_Z"
echo "GRASP_CONTACT_SCORE_STEPS=$GRASP_CONTACT_SCORE_STEPS"
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
    VIDEO_VALIDATE_ARGS=(
      validate_franka_multi_object_grasp_videos.py
      --headless
      --device cuda:0
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --object_asset_manifest_path "$OBJECT_ASSET_MANIFEST_PATH"
      --max_objects "$MAX_OBJECTS"
      --object_asset_assignment "$OBJECT_ASSET_ASSIGNMENT"
      --object_spawn_center_offset_x "$OBJECT_SPAWN_CENTER_OFFSET_X"
      --object_spawn_center_offset_y "$OBJECT_SPAWN_CENTER_OFFSET_Y"
      --object_spawn_xy_randomization "$OBJECT_SPAWN_XY_RANDOMIZATION"
      --object_spawn_yaw_randomization_deg "$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG"
      --render_warmup_frames "$RENDER_WARMUP_FRAMES"
      --reset_cycles "$RESET_CYCLES"
      --settle_steps "$SETTLE_STEPS"
      --perturb_steps "$PERTURB_STEPS"
      --perturb_push_steps "$PERTURB_PUSH_STEPS"
      --perturb_linear_velocity "$PERTURB_LINEAR_VELOCITY"
      --perturb_lateral_velocity "$PERTURB_LATERAL_VELOCITY"
      --perturb_angular_velocity "$PERTURB_ANGULAR_VELOCITY"
      --grasp_steps "$GRASP_STEPS"
      --grasp_object_settle_steps "$GRASP_OBJECT_SETTLE_STEPS"
      --object_reset_settle_steps "$OBJECT_RESET_SETTLE_STEPS"
      --capture_interval "$CAPTURE_INTERVAL"
      --grasp_reset_attempts "$GRASP_RESET_ATTEMPTS"
      --grasp_reset_min_pregrasp_z "$GRASP_RESET_MIN_PREGRASP_Z"
      --grasp_contact_score_steps "$GRASP_CONTACT_SCORE_STEPS"
    )

    printf "video_validate_command="
    printf "%q " /isaac-sim/python.sh "${VIDEO_VALIDATE_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${VIDEO_VALIDATE_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected video validation error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/video_metrics.json" ]; then
  echo "Missing video metrics JSON: $RUN_DIR_HOST/video_metrics.json"
  exit 1
fi

python3 - "$RUN_DIR_HOST/video_metrics.json" <<'PY'
import json
import sys

metrics_path = sys.argv[1]
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)
if not bool(payload.get("passed", False)):
    failed = [name for name, item in payload.get("scenarios", {}).items() if not bool(item.get("passed", False))]
    print(f"Video validation metrics failed: {failed}")
    sys.exit(1)
print("Video validation metrics passed")
PY

echo "Video Validation Done"
