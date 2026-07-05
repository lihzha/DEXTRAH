#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_rgb_dp_diag
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-00:30:00
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/diagnose_yam_rgb_dp_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
OFFICIAL_DP_NFS="${OFFICIAL_DP_NFS:-$NFS_ROOT/src/external/real-stanford-diffusion_policy}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
OFFICIAL_DP_ENV_NAME="${OFFICIAL_DP_ENV_NAME:-franka-cube-dp-bc-warmstart-official-dp}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_rgb_dp_offline_diag_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to an official image Diffusion Policy .ckpt path.}"
MANIFEST="${MANIFEST:?Set MANIFEST to the YAM RGB policy shard manifest.json path.}"
OUTPUT_DIR="${OUTPUT_DIR:-$RESULTS_NFS/dp_bc/diagnostics/$RUN_NAME}"

DEVICE="${DEVICE:-cuda:0}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
POLICY_SOURCE="${POLICY_SOURCE:-auto}"
BATCH_SIZE="${BATCH_SIZE:-8}"
SEED="${SEED:-42}"
RANDOM_ROWS="${RANDOM_ROWS:-32}"
SHARDS="${SHARDS:-0 1 37 123 250 399}"
SHARD_STEPS="${SHARD_STEPS:-0 64 128 216 251 493 775 824}"

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

CHECKPOINT_HOST="$(host_path_from_container "$CHECKPOINT")"
CHECKPOINT_ARG="$(container_path_from_host "$CHECKPOINT")"
MANIFEST_HOST="$(host_path_from_container "$MANIFEST")"
MANIFEST_ARG="$(container_path_from_host "$MANIFEST")"
OUTPUT_DIR_HOST="$(host_path_from_container "$OUTPUT_DIR")"
OUTPUT_DIR_ARG="$(container_path_from_host "$OUTPUT_DIR")"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$OFFICIAL_DP_ENV_NAME/site" ]; then
  echo "Missing official Diffusion Policy Python target: $ENV_ROOT/$OFFICIAL_DP_ENV_NAME/site"
  exit 2
fi
if [ ! -d "$OFFICIAL_DP_NFS/diffusion_policy" ]; then
  echo "Missing official Diffusion Policy checkout: $OFFICIAL_DP_NFS"
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ ! -f "$MANIFEST_HOST" ]; then
  echo "Missing manifest: $MANIFEST_HOST"
  exit 2
fi

mkdir -p \
  "$OUTPUT_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" "$CACHE_NFS/torch" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache"

export RUN_NAME CHECKPOINT_ARG MANIFEST_ARG OUTPUT_DIR_ARG DEVICE NUM_INFERENCE_STEPS POLICY_SOURCE
export BATCH_SIZE SEED RANDOM_ROWS SHARDS SHARD_STEPS ENV_NAME OFFICIAL_DP_ENV_NAME

echo "Running YAM RGB DP offline coherence diagnostic"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "CODE_NFS=$CODE_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "MANIFEST_ARG=$MANIFEST_ARG"
echo "OUTPUT_DIR_HOST=$OUTPUT_DIR_HOST"
echo "DEVICE=$DEVICE NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS POLICY_SOURCE=$POLICY_SOURCE"
echo "BATCH_SIZE=$BATCH_SIZE RANDOM_ROWS=$RANDOM_ROWS"
echo "SHARDS=$SHARDS"
echo "SHARD_STEPS=$SHARD_STEPS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/torch":/root/.cache/torch,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_HOME=/root/.cache/torch,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export DP_SITE="/envs/$OFFICIAL_DP_ENV_NAME/site"
    export PYTHONPATH="$SITE:$DP_SITE:/code:/official_dp"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    SHARD_ARGS=()
    for shard in $SHARDS; do
      SHARD_ARGS+=(--shard "$shard")
    done
    STEP_ARGS=()
    for step in $SHARD_STEPS; do
      STEP_ARGS+=(--shard-step "$step")
    done

    CMD=(
      /isaac-sim/python.sh /code/dextrah_lab/offline_dp_bc/diagnose_yam_rgb_dp_offline_coherence.py
      --checkpoint "$CHECKPOINT_ARG"
      --manifest "$MANIFEST_ARG"
      --output-dir "$OUTPUT_DIR_ARG"
      --diffusion-policy-root /official_dp
      --device "$DEVICE"
      --num-inference-steps "$NUM_INFERENCE_STEPS"
      --policy-source "$POLICY_SOURCE"
      --batch-size "$BATCH_SIZE"
      --seed "$SEED"
      --random-rows "$RANDOM_ROWS"
      "${SHARD_ARGS[@]}"
      "${STEP_ARGS[@]}"
    )
    printf "yam_rgb_offline_diag_command="
    printf "%q " "${CMD[@]}"
    printf "\n"
    "${CMD[@]}" 2>&1 | tee "$OUTPUT_DIR_ARG/diagnose_stdout.log"
  '

SUMMARY_HOST="$OUTPUT_DIR_HOST/yam_rgb_offline_coherence_summary.json"
if [ ! -s "$SUMMARY_HOST" ]; then
  echo "Missing diagnostic summary: $SUMMARY_HOST"
  exit 1
fi

python3 - "$SUMMARY_HOST" <<'PY'
import json
import sys
path = sys.argv[1]
payload = json.load(open(path, "r", encoding="utf-8"))
summary = payload.get("summary", {})
print("YAM RGB DP offline coherence diagnostic passed")
print(json.dumps({
    "selected_rows": payload.get("selected_rows"),
    "pred_first_pose_l2_mean": summary.get("pred_first_pose_l2_mean"),
    "label_first_pose_l2_mean": summary.get("label_first_pose_l2_mean"),
    "pose_l2_ratio_mean": summary.get("pose_l2_ratio_mean"),
    "gripper_sign_match_fraction": summary.get("gripper_sign_match_fraction"),
}, sort_keys=True))
PY

echo "YAM RGB DP Offline Diagnostic Done"
echo "OUTPUT_DIR_HOST=$OUTPUT_DIR_HOST"
