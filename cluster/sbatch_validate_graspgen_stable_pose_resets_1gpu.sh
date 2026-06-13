#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_stable_pose
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
SUBMIT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
CODE_NFS="${CODE_NFS:-$SUBMIT_DIR}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

TASK="${TASK:-Dextrah-Franka-Multi-Object-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-graspgen_stable_pose_validate_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-}"
MAX_OBJECTS="${MAX_OBJECTS:-4}"
OBJECT_UUIDS="${OBJECT_UUIDS:-}"
STABLE_POSE_COUNT="${STABLE_POSE_COUNT:-1}"
STABLE_POSE_MESH_MODE="${STABLE_POSE_MESH_MODE:-convex_hull}"
STABLE_POSE_SIGMA="${STABLE_POSE_SIGMA:-0.0}"
STABLE_POSE_SAMPLES="${STABLE_POSE_SAMPLES:-1}"
STABLE_POSE_THRESHOLD="${STABLE_POSE_THRESHOLD:-0.0}"
SETTLE_STEPS="${SETTLE_STEPS:-240}"
SEED="${SEED:-42}"
TABLE_CLEARANCE="${TABLE_CLEARANCE:-0.002}"
MAX_ROOT_XY_DRIFT="${MAX_ROOT_XY_DRIFT:-0.01}"
MAX_CENTER_XY_DRIFT="${MAX_CENTER_XY_DRIFT:-0.01}"
MAX_ROOT_Z_DRIFT="${MAX_ROOT_Z_DRIFT:-0.02}"
MAX_ANGULAR_DRIFT_DEG="${MAX_ANGULAR_DRIFT_DEG:-5.0}"
MIN_BOTTOM_CLEARANCE="${MIN_BOTTOM_CLEARANCE:--0.005}"
MAX_FINAL_SPEED="${MAX_FINAL_SPEED:-0.03}"
RENDER_FRAMES="${RENDER_FRAMES:-True}"
CAPTURE_INTERVAL="${CAPTURE_INTERVAL:-24}"
RENDER_WARMUP_FRAMES="${RENDER_WARMUP_FRAMES:-2}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/validate_graspgen_stable_pose_${SLURM_JOB_ID_SAFE}.out"

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

export TASK RUN_NAME OBJECT_ASSET_MANIFEST_PATH MAX_OBJECTS OBJECT_UUIDS
export STABLE_POSE_COUNT STABLE_POSE_MESH_MODE STABLE_POSE_SIGMA STABLE_POSE_SAMPLES STABLE_POSE_THRESHOLD
export SETTLE_STEPS SEED TABLE_CLEARANCE MAX_ROOT_XY_DRIFT MAX_CENTER_XY_DRIFT
export MAX_ROOT_Z_DRIFT MAX_ANGULAR_DRIFT_DEG MIN_BOTTOM_CLEARANCE MAX_FINAL_SPEED
export RENDER_FRAMES CAPTURE_INTERVAL RENDER_WARMUP_FRAMES
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME CODE_COMMIT

echo "Running DextrAH GraspGen stable-pose placement validation"
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
echo "OBJECT_ASSET_MANIFEST_PATH=$OBJECT_ASSET_MANIFEST_PATH"
echo "MAX_OBJECTS=$MAX_OBJECTS"
echo "OBJECT_UUIDS=$OBJECT_UUIDS"
echo "STABLE_POSE_COUNT=$STABLE_POSE_COUNT"
echo "STABLE_POSE_MESH_MODE=$STABLE_POSE_MESH_MODE"
echo "STABLE_POSE_SIGMA=$STABLE_POSE_SIGMA"
echo "STABLE_POSE_SAMPLES=$STABLE_POSE_SAMPLES"
echo "STABLE_POSE_THRESHOLD=$STABLE_POSE_THRESHOLD"
echo "SETTLE_STEPS=$SETTLE_STEPS"
echo "SEED=$SEED"
echo "TABLE_CLEARANCE=$TABLE_CLEARANCE"
echo "MAX_ROOT_XY_DRIFT=$MAX_ROOT_XY_DRIFT"
echo "MAX_CENTER_XY_DRIFT=$MAX_CENTER_XY_DRIFT"
echo "MAX_ROOT_Z_DRIFT=$MAX_ROOT_Z_DRIFT"
echo "MAX_ANGULAR_DRIFT_DEG=$MAX_ANGULAR_DRIFT_DEG"
echo "MIN_BOTTOM_CLEARANCE=$MIN_BOTTOM_CLEARANCE"
echo "MAX_FINAL_SPEED=$MAX_FINAL_SPEED"
echo "RENDER_FRAMES=$RENDER_FRAMES"
echo "CAPTURE_INTERVAL=$CAPTURE_INTERVAL"
echo "RENDER_WARMUP_FRAMES=$RENDER_WARMUP_FRAMES"
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
    /isaac-sim/python.sh - <<PY
import trimesh
print("trimesh_version=" + str(trimesh.__version__), flush=True)
PY

    cd /code/dextrah_lab/rl_games
    RENDER_ARGS=()
    case "$RENDER_FRAMES" in
      True|true|1|yes|Yes)
        RENDER_ARGS=(--render_frames)
        ;;
    esac
    UUID_ARGS=()
    if [ -n "$OBJECT_UUIDS" ]; then
      UUID_ARGS=(--object_uuids "$OBJECT_UUIDS")
    fi

    VALIDATE_ARGS=(
      validate_graspgen_stable_pose_resets.py
      --headless
      --device cuda:0
      --task "$TASK"
      --object_asset_manifest_path "$OBJECT_ASSET_MANIFEST_PATH"
      --max_objects "$MAX_OBJECTS"
      "${UUID_ARGS[@]}"
      --stable_pose_count "$STABLE_POSE_COUNT"
      --stable_pose_mesh_mode "$STABLE_POSE_MESH_MODE"
      --stable_pose_sigma "$STABLE_POSE_SIGMA"
      --stable_pose_samples "$STABLE_POSE_SAMPLES"
      --stable_pose_threshold "$STABLE_POSE_THRESHOLD"
      --settle_steps "$SETTLE_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --table_clearance "$TABLE_CLEARANCE"
      --max_root_xy_drift "$MAX_ROOT_XY_DRIFT"
      --max_center_xy_drift "$MAX_CENTER_XY_DRIFT"
      --max_root_z_drift "$MAX_ROOT_Z_DRIFT"
      --max_angular_drift_deg "$MAX_ANGULAR_DRIFT_DEG"
      --min_bottom_clearance "$MIN_BOTTOM_CLEARANCE"
      --max_final_speed "$MAX_FINAL_SPEED"
      --capture_interval "$CAPTURE_INTERVAL"
      --render_warmup_frames "$RENDER_WARMUP_FRAMES"
      "${RENDER_ARGS[@]}"
    )

    printf "stable_pose_validate_command="
    printf "%q " /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${VALIDATE_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected stable-pose validation error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing stable-pose metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" <<'PY'
import json
import sys

metrics_path = sys.argv[1]
with open(metrics_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

if not bool(payload.get("passed", False)):
    print("Stable-pose validation metrics failed")
    print(json.dumps(payload.get("result", {}).get("summary", {}), indent=2, sort_keys=True))
    sys.exit(1)

print("Stable-pose validation metrics passed")
PY

echo "Stable Pose Validation Done"
