#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_graspgen_usd
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-03:50:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --array=0-31
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/convert_graspgen_assets_gpu_%A_%a.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
GRASPGEN_CACHE_NFS="${GRASPGEN_CACHE_NFS:-$NFS_ROOT/cache/graspgen}"

SLURM_ARRAY_TASK_ID_SAFE="${SLURM_ARRAY_TASK_ID:-0}"
SLURM_ARRAY_JOB_ID_SAFE="${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-manual}}"
CHUNK_ID="${CHUNK_ID:-$(printf "%03d" "$SLURM_ARRAY_TASK_ID_SAFE")}"
RUN_NAME="${RUN_NAME:-graspgen_objects_full_cpu_20260617_153051}"

ASSET_ROOT_HOST="${ASSET_ROOT_HOST:-$RESULTS_NFS/assets/$RUN_NAME}"
ASSET_ROOT_CONTAINER="${ASSET_ROOT_CONTAINER:-/results/assets/$RUN_NAME}"
SHARD_DIR_HOST="${SHARD_DIR_HOST:-$ASSET_ROOT_HOST/shards/$CHUNK_ID}"
SHARD_DIR_CONTAINER="${SHARD_DIR_CONTAINER:-$ASSET_ROOT_CONTAINER/shards/$CHUNK_ID}"
MANIFEST_HOST="${MANIFEST_HOST:-$SHARD_DIR_HOST/manifest.json}"
MANIFEST_CONTAINER="${MANIFEST_CONTAINER:-$SHARD_DIR_CONTAINER/manifest.json}"

CONVERT_SKIP_EXISTING="${CONVERT_SKIP_EXISTING:-True}"
MAX_OBJECTS="${MAX_OBJECTS:-0}"
MERGE_JOINTS="${MERGE_JOINTS:-False}"
FIX_BASE="${FIX_BASE:-False}"
MAKE_INSTANCEABLE="${MAKE_INSTANCEABLE:-False}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -f "$MANIFEST_HOST" ]; then
  echo "Missing shard manifest: $MANIFEST_HOST"
  exit 2
fi

mkdir -p \
  "$SHARD_DIR_HOST/USD" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$GRASPGEN_CACHE_NFS/home" "$GRASPGEN_CACHE_NFS/xdg" \
  "$GRASPGEN_CACHE_NFS/huggingface/hub" "$GRASPGEN_CACHE_NFS/objaverse" \
  "$GRASPGEN_CACHE_NFS/tmp" "$GRASPGEN_CACHE_NFS/pip" "$GRASPGEN_CACHE_NFS/torch" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export RUN_NAME ASSET_ROOT_CONTAINER SHARD_DIR_CONTAINER MANIFEST_CONTAINER
export CONVERT_SKIP_EXISTING MAX_OBJECTS MERGE_JOINTS FIX_BASE MAKE_INSTANCEABLE CODE_COMMIT

echo "Running DextrAH GraspGen USD conversion"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "SLURM_ARRAY_JOB_ID=$SLURM_ARRAY_JOB_ID_SAFE"
echo "SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "CODE_NFS=$CODE_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "IMAGE=$IMAGE"
echo "RUN_NAME=$RUN_NAME"
echo "ASSET_ROOT_HOST=$ASSET_ROOT_HOST"
echo "SHARD_DIR_HOST=$SHARD_DIR_HOST"
echo "MANIFEST_HOST=$MANIFEST_HOST"
echo "CONVERT_SKIP_EXISTING=$CONVERT_SKIP_EXISTING"
echo "MAX_OBJECTS=$MAX_OBJECTS"
echo "MERGE_JOINTS=$MERGE_JOINTS"
echo "FIX_BASE=$FIX_BASE"
echo "MAKE_INSTANCEABLE=$MAKE_INSTANCEABLE"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$GRASPGEN_CACHE_NFS":/graspgen_cache,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    cd /code
    export HOME=/graspgen_cache/home
    export XDG_CACHE_HOME=/graspgen_cache/xdg
    export HF_HOME=/graspgen_cache/huggingface
    export HUGGINGFACE_HUB_CACHE=/graspgen_cache/huggingface/hub
    export OBJAVERSE_HOME=/graspgen_cache/objaverse
    export OBJAVERSE_CACHE_DIR=/graspgen_cache/objaverse
    export TMPDIR=/graspgen_cache/tmp
    export PIP_CACHE_DIR=/graspgen_cache/pip
    export TORCH_HOME=/graspgen_cache/torch
    mkdir -p "$HOME" "$XDG_CACHE_HOME" "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" \
      "$OBJAVERSE_HOME" "$TMPDIR" "$PIP_CACHE_DIR" "$TORCH_HOME"

    echo "container_host=$(hostname)"
    echo "container_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true

    export CONVERT_PYTHONPATH="/code"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export CONVERT_PYTHONPATH="$d:$CONVERT_PYTHONPATH"
      fi
    done

    CONVERT_ARGS=(
      dextrah_lab/assets/batch_convert_urdf.py
      "$SHARD_DIR_CONTAINER/urdf"
      "$SHARD_DIR_CONTAINER/USD"
      --headless
      --manifest "$MANIFEST_CONTAINER"
      --max-objects "$MAX_OBJECTS"
    )
    case "$CONVERT_SKIP_EXISTING" in
      True|true|1|yes|Yes) CONVERT_ARGS+=(--skip-existing) ;;
    esac
    case "$MERGE_JOINTS" in
      True|true|1|yes|Yes) CONVERT_ARGS+=(--merge-joints) ;;
    esac
    case "$FIX_BASE" in
      True|true|1|yes|Yes) CONVERT_ARGS+=(--fix-base) ;;
    esac
    case "$MAKE_INSTANCEABLE" in
      True|true|1|yes|Yes) CONVERT_ARGS+=(--make-instanceable) ;;
    esac

    printf "convert_command="
    printf "%q " /isaac-sim/python.sh "${CONVERT_ARGS[@]}"
    printf "\n"
    PYTHONPATH="$CONVERT_PYTHONPATH" /isaac-sim/python.sh "${CONVERT_ARGS[@]}"

    PYTHONPATH="$CONVERT_PYTHONPATH" /isaac-sim/python.sh - "$MANIFEST_CONTAINER" "$MAX_OBJECTS" <<'"'"'PY'"'"'
import json
import math
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
max_objects = int(sys.argv[2])
payload = json.loads(manifest.read_text())
root = Path(payload.get("asset_root") or ".")
if not root.is_absolute():
    root = (manifest.parent / root).resolve()
objects = payload.get("objects", [])
if max_objects > 0:
    objects = sorted(objects, key=lambda record: str(record.get("uuid") or ""))[:max_objects]
missing_usd = []
small_usd = []
bad_extent = []
for record in objects:
    usd_path = root / str(record.get("usd_path", ""))
    if not usd_path.is_file():
        missing_usd.append(str(usd_path))
    elif usd_path.stat().st_size <= 1024:
        small_usd.append((str(usd_path), usd_path.stat().st_size))
    extents = record.get("scaled_half_extents", [])
    if (
        not isinstance(extents, list)
        or len(extents) != 3
        or any(
            (not isinstance(value, (int, float))) or (not math.isfinite(float(value))) or float(value) <= 0.0
            for value in extents
        )
    ):
        bad_extent.append((record.get("uuid"), extents))
summary = {
    "manifest": str(manifest),
    "objects_checked": len(objects),
    "max_objects": max_objects,
    "missing_usd": len(missing_usd),
    "missing_usd_examples": missing_usd[:8],
    "small_usd": len(small_usd),
    "small_usd_examples": small_usd[:8],
    "bad_scaled_half_extent": len(bad_extent),
    "bad_scaled_half_extent_examples": bad_extent[:8],
}
print("DEXTRAH_GRASPGEN_USD_STAGE_SUMMARY", json.dumps(summary, sort_keys=True), flush=True)
(manifest.parent / "usd_conversion_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
if missing_usd or small_usd or bad_extent or not objects:
    raise SystemExit(1)
PY
  '

if [ "${MAX_OBJECTS:-0}" -gt 0 ]; then
  touch "$SHARD_DIR_HOST/_USD_CONVERT_SMOKE_DONE"
  echo "GraspGen USD Conversion Smoke Done: $SHARD_DIR_HOST"
else
  touch "$SHARD_DIR_HOST/_USD_CONVERT_DONE"
  echo "GraspGen USD Conversion Done: $SHARD_DIR_HOST"
fi
