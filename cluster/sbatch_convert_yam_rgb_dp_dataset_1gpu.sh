#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_yam_rgb_dp_convert
#SBATCH --partition=batch
#SBATCH --time=0-02:00:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/convert_yam_rgb_dp_%j.out

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
HOST_RESULTS_ROOT="${HOST_RESULTS_ROOT:-$RESULTS_NFS}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_rgb_dp_dataset_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
MANIFEST="${MANIFEST:?Set MANIFEST to accepted_demos_first500.jsonl or a compatible JSONL.}"
OUTPUT="${OUTPUT:-$RESULTS_NFS/dp_bc/datasets/$RUN_NAME.npz}"
METADATA_OUTPUT="${METADATA_OUTPUT:-$OUTPUT.metadata.json}"
MAX_DEMOS="${MAX_DEMOS:-}"
IMAGE_HEIGHT="${IMAGE_HEIGHT:-96}"
IMAGE_WIDTH="${IMAGE_WIDTH:-128}"
ROBOT_STATE_MODE="${ROBOT_STATE_MODE:-actual_joint_position}"
ACTION_MODE="${ACTION_MODE:-command_joint_position}"
MAKE_REPORT="${MAKE_REPORT:-False}"
REPORT_DIR="${REPORT_DIR:-$RESULTS_NFS/dp_bc/dataset_reports/$RUN_NAME}"

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

MANIFEST_HOST="$(host_path_from_container "$MANIFEST")"
MANIFEST_ARG="$(container_path_from_host "$MANIFEST")"
OUTPUT_HOST="$(host_path_from_container "$OUTPUT")"
OUTPUT_ARG="$(container_path_from_host "$OUTPUT")"
METADATA_OUTPUT_HOST="$(host_path_from_container "$METADATA_OUTPUT")"
METADATA_OUTPUT_ARG="$(container_path_from_host "$METADATA_OUTPUT")"
REPORT_DIR_HOST="$(host_path_from_container "$REPORT_DIR")"
REPORT_DIR_ARG="$(container_path_from_host "$REPORT_DIR")"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$MANIFEST_HOST" ]; then
  echo "Missing YAM accepted manifest: $MANIFEST_HOST"
  exit 2
fi

mkdir -p \
  "$(dirname "$OUTPUT_HOST")" \
  "$(dirname "$METADATA_OUTPUT_HOST")" \
  "$REPORT_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export MANIFEST_ARG OUTPUT_ARG METADATA_OUTPUT_ARG MAX_DEMOS IMAGE_HEIGHT IMAGE_WIDTH
export ROBOT_STATE_MODE ACTION_MODE MAKE_REPORT REPORT_DIR_ARG ENV_NAME HOST_RESULTS_ROOT

echo "Running DextrAH YAM RGB DP dataset conversion"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "MANIFEST_HOST=$MANIFEST_HOST"
echo "OUTPUT_HOST=$OUTPUT_HOST"
echo "METADATA_OUTPUT_HOST=$METADATA_OUTPUT_HOST"
echo "MAX_DEMOS=${MAX_DEMOS:-<all>}"
echo "IMAGE_SHAPE=[$IMAGE_HEIGHT,$IMAGE_WIDTH,3]"
echo "ROBOT_STATE_MODE=$ROBOT_STATE_MODE ACTION_MODE=$ACTION_MODE"
echo "MAKE_REPORT=$MAKE_REPORT REPORT_DIR_HOST=$REPORT_DIR_HOST"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
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
    git -C /code rev-parse HEAD || true
    nvidia-smi || true
    CONVERT_ARGS=(
      -m dextrah_lab.offline_dp_bc.convert_yam_pick_place_rgb_dataset
      --manifest "$MANIFEST_ARG"
      --output "$OUTPUT_ARG"
      --metadata-output "$METADATA_OUTPUT_ARG"
      --results-root /results
      --host-results-root "$HOST_RESULTS_ROOT"
      --image-height "$IMAGE_HEIGHT"
      --image-width "$IMAGE_WIDTH"
      --robot-state-mode "$ROBOT_STATE_MODE"
      --action-mode "$ACTION_MODE"
    )
    if [ -n "${MAX_DEMOS:-}" ]; then
      CONVERT_ARGS+=(--max-demos "$MAX_DEMOS")
    fi
    printf "yam_rgb_convert_command="
    printf "%q " /isaac-sim/python.sh "${CONVERT_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${CONVERT_ARGS[@]}"
    if [ "$MAKE_REPORT" = "True" ]; then
      /isaac-sim/python.sh -m dextrah_lab.offline_dp_bc.make_rgb_dataset_report \
        --dataset "$OUTPUT_ARG" \
        --output-dir "$REPORT_DIR_ARG" \
        --expected-robot-state-dim 8 \
        --expected-action-dim 8 \
        --fps 12 \
        --scale 2
    fi
  '

if [ ! -s "$OUTPUT_HOST" ]; then
  echo "Missing converted dataset: $OUTPUT_HOST"
  exit 1
fi
if [ ! -s "$METADATA_OUTPUT_HOST" ]; then
  echo "Missing converted dataset metadata: $METADATA_OUTPUT_HOST"
  exit 1
fi

python3 - "$METADATA_OUTPUT_HOST" "$OUTPUT_HOST" <<'PY'
import json
import os
import sys

metadata_path, output_path = sys.argv[1:3]
metadata = json.load(open(metadata_path, "r", encoding="utf-8"))
print("YAM RGB DP conversion metrics passed")
print(json.dumps({
    "output": output_path,
    "bytes": os.path.getsize(output_path),
    "num_episodes": metadata.get("num_episodes"),
    "num_steps": metadata.get("num_steps"),
    "image_shape": metadata.get("image_shape"),
    "robot_state_shape": metadata.get("robot_state_shape"),
    "action_shape": metadata.get("action_shape"),
    "phase_counts": metadata.get("phase_counts"),
}, sort_keys=True))
PY

echo "YAM RGB DP Dataset Conversion Done"
echo "OUTPUT_HOST=$OUTPUT_HOST"
echo "METADATA_OUTPUT_HOST=$METADATA_OUTPUT_HOST"
echo "REPORT_DIR_HOST=$REPORT_DIR_HOST"
