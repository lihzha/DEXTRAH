#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --job-name=dextrah_graspgen_cpu
#SBATCH --partition=cpu
#SBATCH --time=0-06:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=32
#SBATCH --array=0-31
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_cpu_%A_%a.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
GRASPGEN_CACHE_NFS="${GRASPGEN_CACHE_NFS:-$NFS_ROOT/cache/graspgen}"
PREP_DEPS_DIR="${PREP_DEPS_DIR:-$ENV_ROOT/dextrah-graspgen-prep/site}"

SLURM_ARRAY_TASK_ID_SAFE="${SLURM_ARRAY_TASK_ID:-0}"
SLURM_ARRAY_JOB_ID_SAFE="${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-manual}}"
CHUNK_ID="${CHUNK_ID:-$(printf "%03d" "$SLURM_ARRAY_TASK_ID_SAFE")}"
RUN_NAME="${RUN_NAME:-graspgen_objects_full_cpu_${SLURM_ARRAY_JOB_ID_SAFE}}"

ASSET_ROOT_HOST="${ASSET_ROOT_HOST:-$RESULTS_NFS/assets/$RUN_NAME}"
ASSET_ROOT_CONTAINER="${ASSET_ROOT_CONTAINER:-/results/assets/$RUN_NAME}"
UUID_SPLIT_DIR_HOST="${UUID_SPLIT_DIR_HOST:-$ASSET_ROOT_HOST/splits}"
UUID_SPLIT_DIR_CONTAINER="${UUID_SPLIT_DIR_CONTAINER:-$ASSET_ROOT_CONTAINER/splits}"
CHUNK_METADATA_HOST="${CHUNK_METADATA_HOST:-$ASSET_ROOT_HOST/splits/chunk_manifest.json}"
CHUNK_METADATA_CONTAINER="${CHUNK_METADATA_CONTAINER:-$ASSET_ROOT_CONTAINER/splits/chunk_manifest.json}"

SHARD_DIR_HOST="${SHARD_DIR_HOST:-$ASSET_ROOT_HOST/shards/$CHUNK_ID}"
SHARD_DIR_CONTAINER="${SHARD_DIR_CONTAINER:-$ASSET_ROOT_CONTAINER/shards/$CHUNK_ID}"
UUID_LIST_HOST="${UUID_LIST_HOST:-$UUID_SPLIT_DIR_HOST/chunk_$CHUNK_ID.txt}"
UUID_LIST_CONTAINER="${UUID_LIST_CONTAINER:-$UUID_SPLIT_DIR_CONTAINER/chunk_$CHUNK_ID.txt}"

PRIOR_CACHE_HOST="${PRIOR_CACHE_HOST:-$ASSET_ROOT_HOST/shared_prior_cache/franka_panda}"
PRIOR_CACHE_CONTAINER="${PRIOR_CACHE_CONTAINER:-$ASSET_ROOT_CONTAINER/shared_prior_cache/franka_panda}"
LOCK_DIR_HOST="${LOCK_DIR_HOST:-$ASSET_ROOT_HOST/locks}"

LIMIT="${LIMIT:-0}"
UNUSED_CPU_COUNT="${UNUSED_CPU_COUNT:-auto}"
SIMPLIFY="${SIMPLIFY:-False}"
OVERWRITE="${OVERWRITE:-False}"
SKIP_OBJECT_DOWNLOAD="${SKIP_OBJECT_DOWNLOAD:-False}"
SKIP_GRASP_EXTRACT="${SKIP_GRASP_EXTRACT:-False}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -f "$UUID_LIST_HOST" ]; then
  echo "Missing UUID chunk file: $UUID_LIST_HOST"
  exit 2
fi

PRIOR_SHARD="$(
python3 - "$CHUNK_ID" "$CHUNK_METADATA_HOST" <<'PY'
import json
import sys
from pathlib import Path

chunk_id = sys.argv[1]
metadata_path = Path(sys.argv[2])
if not metadata_path.is_file():
    raise SystemExit(f"Missing chunk metadata: {metadata_path}")
payload = json.loads(metadata_path.read_text())
entry = payload["chunks"][chunk_id]
print(int(entry["prior_shard"]))
PY
)"
PRIOR_SHARD_PADDED="$(printf "%03d" "$PRIOR_SHARD")"

mkdir -p \
  "$ASSET_ROOT_HOST" \
  "$SHARD_DIR_HOST" \
  "$SHARD_DIR_HOST/cache/grasp_data" \
  "$PRIOR_CACHE_HOST" \
  "$LOCK_DIR_HOST" \
  "$PREP_DEPS_DIR" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$GRASPGEN_CACHE_NFS/home" "$GRASPGEN_CACHE_NFS/xdg" \
  "$GRASPGEN_CACHE_NFS/huggingface/hub" "$GRASPGEN_CACHE_NFS/objaverse" \
  "$GRASPGEN_CACHE_NFS/tmp" "$GRASPGEN_CACHE_NFS/pip" "$GRASPGEN_CACHE_NFS/torch"

ln -sfn "$PRIOR_CACHE_HOST" "$SHARD_DIR_HOST/cache/grasp_data/franka_panda"

PRIOR_TAR_HOST="$PRIOR_CACHE_HOST/shard_${PRIOR_SHARD_PADDED}.tar"
LOCK_FILE="$LOCK_DIR_HOST/shard_${PRIOR_SHARD_PADDED}.lock"
(
  flock 9
  if [ ! -s "$PRIOR_TAR_HOST" ]; then
    echo "Prefetching GraspGen prior shard $PRIOR_SHARD_PADDED to $PRIOR_TAR_HOST"
    python3 - "$PRIOR_SHARD_PADDED" "$PRIOR_TAR_HOST" <<'PY'
import shutil
import sys
import urllib.request
from pathlib import Path

shard = sys.argv[1]
path = Path(sys.argv[2])
url = (
    "https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GraspGen/resolve/main/"
    f"grasp_data/franka_panda/shard_{shard}.tar"
)
path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(path.suffix + ".tmp")
print(f"[PRIOR_PREFETCH] {url} -> {path}", flush=True)
with urllib.request.urlopen(url, timeout=180) as response, tmp.open("wb") as f:
    shutil.copyfileobj(response, f)
tmp.replace(path)
PY
  else
    echo "Prior shard already cached: $PRIOR_TAR_HOST"
  fi
) 9>"$LOCK_FILE"

export RUN_NAME ASSET_ROOT_CONTAINER UUID_LIST_CONTAINER SHARD_DIR_CONTAINER LIMIT
export UNUSED_CPU_COUNT SIMPLIFY OVERWRITE SKIP_OBJECT_DOWNLOAD SKIP_GRASP_EXTRACT
export PREP_DEPS_DIR CODE_COMMIT PRIOR_SHARD PRIOR_SHARD_PADDED PRIOR_CACHE_CONTAINER CHUNK_METADATA_CONTAINER

echo "Running DextrAH GraspGen CPU asset preparation"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "SLURM_ARRAY_JOB_ID=$SLURM_ARRAY_JOB_ID_SAFE"
echo "SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "CODE_NFS=$CODE_NFS"
echo "IMAGE=$IMAGE"
echo "RUN_NAME=$RUN_NAME"
echo "ASSET_ROOT_HOST=$ASSET_ROOT_HOST"
echo "SHARD_DIR_HOST=$SHARD_DIR_HOST"
echo "UUID_LIST_HOST=$UUID_LIST_HOST"
echo "PRIOR_SHARD=$PRIOR_SHARD_PADDED"
echo "PRIOR_TAR_HOST=$PRIOR_TAR_HOST"
echo "LIMIT=$LIMIT"
echo "UNUSED_CPU_COUNT=$UNUSED_CPU_COUNT"
echo "SIMPLIFY=$SIMPLIFY"
echo "OVERWRITE=$OVERWRITE"
echo "SKIP_OBJECT_DOWNLOAD=$SKIP_OBJECT_DOWNLOAD"
echo "SKIP_GRASP_EXTRACT=$SKIP_GRASP_EXTRACT"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$GRASPGEN_CACHE_NFS":/graspgen_cache \
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
    export DEXTRAH_ENFORCE_NO_HOME_DOWNLOADS=1
    mkdir -p "$HOME" "$XDG_CACHE_HOME" "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" \
      "$OBJAVERSE_HOME" "$TMPDIR" "$PIP_CACHE_DIR" "$TORCH_HOME"

    echo "container_host=$(hostname)"
    echo "container_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true

    export PREP_PYTHONPATH="$PREP_DEPS_DIR:/code"
    if ! PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh - <<'"'"'PY'"'"'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("objaverse") and importlib.util.find_spec("webdataset") else 1)
PY
    then
      echo "Installing GraspGen preparation dependencies into $PREP_DEPS_DIR"
      /isaac-sim/python.sh -m pip install --target "$PREP_DEPS_DIR" --upgrade objaverse webdataset
    fi

    if [ "$UNUSED_CPU_COUNT" = "auto" ]; then
      HOST_CPUS="$(/isaac-sim/python.sh - <<'"'"'PY'"'"'
import multiprocessing
print(multiprocessing.cpu_count())
PY
)"
      TASK_CPUS="${SLURM_CPUS_PER_TASK:-32}"
      UNUSED_CPU_COUNT="$(( HOST_CPUS - TASK_CPUS ))"
      if [ "$UNUSED_CPU_COUNT" -lt 0 ]; then
        UNUSED_CPU_COUNT=0
      fi
    fi
    echo "effective_unused_cpu_count=$UNUSED_CPU_COUNT"

    PREP_ARGS=(
      dextrah_lab/assets/prepare_graspgen_assets.py
      --output_dir "$SHARD_DIR_CONTAINER"
      --uuid_list "$UUID_LIST_CONTAINER"
      --limit "$LIMIT"
      --unused_cpu_count "$UNUSED_CPU_COUNT"
    )
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

    printf "prepare_command="
    printf "%q " /isaac-sim/python.sh "${PREP_ARGS[@]}"
    printf "\n"
    PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh "${PREP_ARGS[@]}"

    PYTHONPATH="$PREP_PYTHONPATH" /isaac-sim/python.sh - "$SHARD_DIR_CONTAINER/manifest.json" <<'"'"'PY'"'"'
import json
import math
import sys
from pathlib import Path

import numpy as np

manifest = Path(sys.argv[1])
payload = json.loads(manifest.read_text())
root = Path(payload.get("asset_root") or ".")
if not root.is_absolute():
    root = (manifest.parent / root).resolve()

missing_raw = []
missing_urdf = []
missing_prior = []
bad_scale = []
scales = []
for record in payload.get("objects", []):
    raw = root / record["raw_object_path"]
    urdf = root / record["urdf_path"]
    prior = root / record["grasp_prior_path"]
    if not raw.is_file():
        missing_raw.append(str(raw))
    if not urdf.is_file():
        missing_urdf.append(str(urdf))
    if not prior.is_file():
        missing_prior.append(str(prior))
        continue
    with np.load(prior, allow_pickle=False) as data:
        scale = float(data["object_scale"])
    if not math.isfinite(scale) or scale <= 0.0:
        bad_scale.append((record["uuid"], scale))
    scales.append(scale)

summary = {
    "manifest": str(manifest),
    "objects": len(payload.get("objects", [])),
    "missing_raw": len(missing_raw),
    "missing_urdf": len(missing_urdf),
    "missing_prior": len(missing_prior),
    "bad_scale": len(bad_scale),
    "scale_min": min(scales) if scales else None,
    "scale_max": max(scales) if scales else None,
}
print("DEXTRAH_GRASPGEN_CPU_STAGE_SUMMARY", json.dumps(summary, sort_keys=True), flush=True)
if not payload.get("objects") or missing_raw or missing_urdf or missing_prior or bad_scale:
    raise SystemExit(1)
PY
  '

touch "$SHARD_DIR_HOST/_CPU_PREP_DONE"
echo "GraspGen CPU Asset Preparation Done: $SHARD_DIR_HOST"
