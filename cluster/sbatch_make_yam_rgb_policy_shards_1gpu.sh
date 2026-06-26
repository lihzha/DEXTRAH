#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_rgb_shards
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-02:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/make_yam_rgb_policy_shards_%j.out

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

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_rgb_policy_shards_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
ACCEPTED_JSONL="${ACCEPTED_JSONL:?Set ACCEPTED_JSONL to the L40 RGB replay accepted JSONL.}"
OUTPUT_DIR="${OUTPUT_DIR:-$RESULTS_NFS/dp_bc/yam_pickplace_rgb_policy/$RUN_NAME/shards}"
MANIFEST="${MANIFEST:-$RESULTS_NFS/dp_bc/yam_pickplace_rgb_policy/$RUN_NAME/manifest.json}"
MIN_SHARDS="${MIN_SHARDS:-1}"
COMPRESS_SHARDS="${COMPRESS_SHARDS:-True}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-npz}"
TRIM_INITIAL_STATIC_POSE_THRESHOLD="${TRIM_INITIAL_STATIC_POSE_THRESHOLD:-0.0}"
TRIM_INITIAL_STATIC_KEEP_STEPS="${TRIM_INITIAL_STATIC_KEEP_STEPS:-0}"
CODE_COMMIT="${CODE_COMMIT:-}"

host_path_from_container() {
  local path="$1"
  if [[ "$path" == /results/* ]]; then
    echo "$RESULTS_NFS/${path#/results/}"
  else
    echo "$path"
  fi
}

container_path_from_host() {
  local path="$1"
  if [[ "$path" == "$RESULTS_NFS"/* ]]; then
    echo "/results/${path#$RESULTS_NFS/}"
  else
    echo "$path"
  fi
}

ACCEPTED_JSONL_HOST="$(host_path_from_container "$ACCEPTED_JSONL")"
ACCEPTED_JSONL_ARG="$(container_path_from_host "$ACCEPTED_JSONL")"
OUTPUT_DIR_HOST="$(host_path_from_container "$OUTPUT_DIR")"
OUTPUT_DIR_ARG="$(container_path_from_host "$OUTPUT_DIR")"
MANIFEST_HOST="$(host_path_from_container "$MANIFEST")"
MANIFEST_ARG="$(container_path_from_host "$MANIFEST")"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$ACCEPTED_JSONL_HOST" ]; then
  echo "Missing accepted JSONL: $ACCEPTED_JSONL_HOST"
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT got $actual_commit"
    exit 2
  fi
fi

mkdir -p \
  "$OUTPUT_DIR_HOST" "$(dirname "$MANIFEST_HOST")" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export ACCEPTED_JSONL_ARG OUTPUT_DIR_ARG MANIFEST_ARG ENV_NAME COMPRESS_SHARDS OUTPUT_FORMAT
export TRIM_INITIAL_STATIC_POSE_THRESHOLD TRIM_INITIAL_STATIC_KEEP_STEPS

echo "Building YAM RGB policy shards"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-}"
echo "RUN_NAME=$RUN_NAME"
echo "ACCEPTED_JSONL_HOST=$ACCEPTED_JSONL_HOST"
echo "ACCEPTED_JSONL_ARG=$ACCEPTED_JSONL_ARG"
echo "OUTPUT_DIR_HOST=$OUTPUT_DIR_HOST"
echo "OUTPUT_DIR_ARG=$OUTPUT_DIR_ARG"
echo "MANIFEST_HOST=$MANIFEST_HOST"
echo "MANIFEST_ARG=$MANIFEST_ARG"
echo "MIN_SHARDS=$MIN_SHARDS"
echo "COMPRESS_SHARDS=$COMPRESS_SHARDS"
echo "OUTPUT_FORMAT=$OUTPUT_FORMAT"
echo "TRIM_INITIAL_STATIC_POSE_THRESHOLD=$TRIM_INITIAL_STATIC_POSE_THRESHOLD"
echo "TRIM_INITIAL_STATIC_KEEP_STEPS=$TRIM_INITIAL_STATIC_KEEP_STEPS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y,OMNI_KIT_ACCEPT_EULA=YES,CI=1,NONINTERACTIVE=1 \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    CMD=(
      /isaac-sim/python.sh /code/dextrah_lab/offline_dp_bc/make_yam_rgb_policy_shards.py
      --accepted_jsonl "$ACCEPTED_JSONL_ARG"
      --output_dir "$OUTPUT_DIR_ARG"
      --manifest "$MANIFEST_ARG"
    )
    if [ "$COMPRESS_SHARDS" != "True" ] && [ "$COMPRESS_SHARDS" != "true" ] && [ "$COMPRESS_SHARDS" != "1" ]; then
      CMD+=(--no_compress)
    fi
    CMD+=(--output_format "$OUTPUT_FORMAT")
    if [ "$TRIM_INITIAL_STATIC_POSE_THRESHOLD" != "0.0" ] && [ "$TRIM_INITIAL_STATIC_POSE_THRESHOLD" != "0" ]; then
      CMD+=(
        --trim_initial_static_pose_threshold "$TRIM_INITIAL_STATIC_POSE_THRESHOLD"
        --trim_initial_static_keep_steps "$TRIM_INITIAL_STATIC_KEEP_STEPS"
      )
    fi
    printf "yam_rgb_shard_command="
    printf "%q " "${CMD[@]}"
    printf "\n"
    "${CMD[@]}"
  '

if [ ! -s "$MANIFEST_HOST" ]; then
  echo "Missing manifest: $MANIFEST_HOST"
  exit 1
fi

python3 - "$MANIFEST_HOST" "$MIN_SHARDS" <<'PY'
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
min_shards = int(sys.argv[2])
payload = json.loads(manifest.read_text(encoding="utf-8"))
num_shards = int(payload.get("num_shards", 0))
num_steps = int(payload.get("num_steps", 0))
if num_shards < min_shards:
    raise SystemExit(f"Expected at least {min_shards} shards, got {num_shards}")
if num_steps <= 0:
    raise SystemExit(f"Expected positive num_steps, got {num_steps}")
for key in ("scene_rgb", "wrist_rgb"):
    if key not in payload.get("image_keys", []):
        raise SystemExit(f"Manifest image_keys missing {key}")
print("YAM RGB policy shard manifest passed")
print(json.dumps({"manifest": str(manifest), "num_shards": num_shards, "num_steps": num_steps}, sort_keys=True))
PY

echo "YAM RGB Policy Shards Done"
echo "MANIFEST_HOST=$MANIFEST_HOST"
echo "OUTPUT_DIR_HOST=$OUTPUT_DIR_HOST"
