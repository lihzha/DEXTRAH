#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_graspgen_assets
#SBATCH --partition=batch_long
#SBATCH --time=1-00:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=32
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
PREP_DEPS_DIR="${PREP_DEPS_DIR:-$ENV_ROOT/dextrah-graspgen-prep/site}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-graspgen_assets_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
ASSET_OUTPUT_DIR_HOST="${ASSET_OUTPUT_DIR_HOST:-$RESULTS_NFS/assets/graspgen_objects}"
ASSET_OUTPUT_DIR_CONTAINER="${ASSET_OUTPUT_DIR_CONTAINER:-/results/assets/graspgen_objects}"
LIMIT="${LIMIT:-0}"
PREFER_SINGLE_SHARD="${PREFER_SINGLE_SHARD:-True}"
# The Objaverse downloader subtracts this from multiprocessing.cpu_count().
# On the cluster container it sees the full host CPU count, not the Slurm CPU
# cgroup, so keep the default conservative to avoid oversubscribing the node.
UNUSED_CPU_COUNT="${UNUSED_CPU_COUNT:-208}"
SIMPLIFY="${SIMPLIFY:-False}"
OVERWRITE="${OVERWRITE:-False}"
CONVERT_USD="${CONVERT_USD:-True}"
CONVERT_SKIP_EXISTING="${CONVERT_SKIP_EXISTING:-True}"
REFRESH_MANIFEST="${REFRESH_MANIFEST:-True}"
SKIP_OBJECT_DOWNLOAD="${SKIP_OBJECT_DOWNLOAD:-False}"
SKIP_GRASP_EXTRACT="${SKIP_GRASP_EXTRACT:-False}"
UUIDS="${UUIDS:-}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/prepare_graspgen_assets_${SLURM_JOB_ID_SAFE}.out"
MANIFEST_HOST="$ASSET_OUTPUT_DIR_HOST/manifest.json"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi

mkdir -p \
  "$ASSET_OUTPUT_DIR_HOST" \
  "$PREP_DEPS_DIR" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export RUN_NAME ASSET_OUTPUT_DIR_CONTAINER LIMIT PREFER_SINGLE_SHARD UNUSED_CPU_COUNT
export SIMPLIFY OVERWRITE CONVERT_USD CONVERT_SKIP_EXISTING REFRESH_MANIFEST SKIP_OBJECT_DOWNLOAD SKIP_GRASP_EXTRACT UUIDS CODE_COMMIT
export PREP_DEPS_DIR

echo "Running DextrAH GraspGen asset preparation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "ASSET_OUTPUT_DIR_HOST=$ASSET_OUTPUT_DIR_HOST"
echo "ASSET_OUTPUT_DIR_CONTAINER=$ASSET_OUTPUT_DIR_CONTAINER"
echo "MANIFEST_HOST=$MANIFEST_HOST"
echo "LIMIT=$LIMIT"
echo "PREFER_SINGLE_SHARD=$PREFER_SINGLE_SHARD"
echo "UNUSED_CPU_COUNT=$UNUSED_CPU_COUNT"
echo "SIMPLIFY=$SIMPLIFY"
echo "OVERWRITE=$OVERWRITE"
echo "CONVERT_USD=$CONVERT_USD"
echo "CONVERT_SKIP_EXISTING=$CONVERT_SKIP_EXISTING"
echo "REFRESH_MANIFEST=$REFRESH_MANIFEST"
echo "SKIP_OBJECT_DOWNLOAD=$SKIP_OBJECT_DOWNLOAD"
echo "SKIP_GRASP_EXTRACT=$SKIP_GRASP_EXTRACT"
echo "UUIDS=$UUIDS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true
    nvidia-smi || true

    mkdir -p "$ASSET_OUTPUT_DIR_CONTAINER" "$PREP_DEPS_DIR"

    export PREP_PYTHONPATH="$PREP_DEPS_DIR:/code"
    if ! PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh - <<'"'"'PY'"'"'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("objaverse") and importlib.util.find_spec("webdataset") else 1)
PY
    then
      echo "Installing GraspGen preparation dependencies into $PREP_DEPS_DIR"
      /isaac-sim/python.sh -m pip install --target "$PREP_DEPS_DIR" --upgrade objaverse webdataset
    fi

    PREP_ARGS=(
      dextrah_lab/assets/prepare_graspgen_assets.py
      --output_dir "$ASSET_OUTPUT_DIR_CONTAINER"
      --limit "$LIMIT"
      --unused_cpu_count "$UNUSED_CPU_COUNT"
    )
    case "$PREFER_SINGLE_SHARD" in
      False|false|0|no|No) PREP_ARGS+=(--no-prefer_single_shard) ;;
    esac
    case "$SIMPLIFY" in
      True|true|1|yes|Yes) PREP_ARGS+=(--simplify) ;;
    esac
    case "$OVERWRITE" in
      True|true|1|yes|Yes) PREP_ARGS+=(--overwrite) ;;
    esac
    case "$SKIP_OBJECT_DOWNLOAD" in
      True|true|1|yes|Yes) PREP_ARGS+=(--skip_object_download) ;;
    esac
    case "$SKIP_GRASP_EXTRACT" in
      True|true|1|yes|Yes) PREP_ARGS+=(--skip_grasp_extract) ;;
    esac
    if [ -n "$UUIDS" ]; then
      # shellcheck disable=SC2206
      UUID_LIST=($UUIDS)
      PREP_ARGS+=(--uuids "${UUID_LIST[@]}")
    fi

    printf "prepare_command="
    printf "%q " /isaac-sim/python.sh "${PREP_ARGS[@]}"
    printf "\n"
    PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh "${PREP_ARGS[@]}"

    case "$CONVERT_USD" in
      True|true|1|yes|Yes)
        export CONVERT_PYTHONPATH="/code"
        for d in /IsaacLab/source/*; do
          if [ -d "$d" ]; then
            export CONVERT_PYTHONPATH="$d:$CONVERT_PYTHONPATH"
          fi
        done
        CONVERT_ARGS=(
          dextrah_lab/assets/batch_convert_urdf.py
          "$ASSET_OUTPUT_DIR_CONTAINER/urdf"
          "$ASSET_OUTPUT_DIR_CONTAINER/USD"
          --headless
        )
        case "$CONVERT_SKIP_EXISTING" in
          True|true|1|yes|Yes) CONVERT_ARGS+=(--skip-existing) ;;
        esac
        printf "convert_command="
        printf "%q " /isaac-sim/python.sh "${CONVERT_ARGS[@]}"
        printf "\n"
        PYTHONPATH="$CONVERT_PYTHONPATH" /isaac-sim/python.sh "${CONVERT_ARGS[@]}"
        ;;
    esac

    case "$REFRESH_MANIFEST" in
      True|true|1|yes|Yes)
        REFRESH_ARGS=(
          dextrah_lab/assets/prepare_graspgen_assets.py
          --output_dir "$ASSET_OUTPUT_DIR_CONTAINER"
          --limit "$LIMIT"
          --unused_cpu_count "$UNUSED_CPU_COUNT"
          --skip_object_download
          --skip_grasp_extract
        )
        case "$PREFER_SINGLE_SHARD" in
          False|false|0|no|No) REFRESH_ARGS+=(--no-prefer_single_shard) ;;
        esac
        case "$SIMPLIFY" in
          True|true|1|yes|Yes) REFRESH_ARGS+=(--simplify) ;;
        esac
        if [ -n "$UUIDS" ]; then
          # shellcheck disable=SC2206
          UUID_LIST=($UUIDS)
          REFRESH_ARGS+=(--uuids "${UUID_LIST[@]}")
        fi
        printf "refresh_manifest_command="
        printf "%q " /isaac-sim/python.sh "${REFRESH_ARGS[@]}"
        printf "\n"
        PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh "${REFRESH_ARGS[@]}"
        ;;
    esac

    PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh - "$ASSET_OUTPUT_DIR_CONTAINER/manifest.json" <<'"'"'PY'"'"'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open("r", encoding="utf-8") as f:
    manifest = json.load(f)
objects = manifest.get("objects", [])
missing = [
    item.get("usd_path")
    for item in objects
    if not (path.parent / str(item.get("usd_path", ""))).is_file()
]
summary = {
    "manifest": str(path),
    "objects": len(objects),
    "missing_usd_count": len(missing),
    "missing_usd_examples": missing[:8],
}
print("DEXTRAH_GRASPGEN_ASSET_STAGE_SUMMARY", json.dumps(summary, sort_keys=True), flush=True)
if missing:
    raise SystemExit(1)
PY
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected asset preparation error patterns in $LOG_FILE."
  exit 1
fi

if [ ! -s "$MANIFEST_HOST" ]; then
  echo "Missing manifest JSON: $MANIFEST_HOST"
  exit 1
fi

python3 - "$MANIFEST_HOST" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open("r", encoding="utf-8") as f:
    manifest = json.load(f)
objects = manifest.get("objects", [])
missing = [
    item.get("usd_path")
    for item in objects
    if not (path.parent / str(item.get("usd_path", ""))).is_file()
]
if not objects:
    print(f"No objects in manifest: {path}")
    sys.exit(1)
if missing:
    print(f"Missing USD files: {missing[:8]} ({len(missing)} total)")
    sys.exit(1)
print(f"Asset manifest ready: {path} objects={len(objects)}")
PY

echo "GraspGen Asset Preparation Done"
