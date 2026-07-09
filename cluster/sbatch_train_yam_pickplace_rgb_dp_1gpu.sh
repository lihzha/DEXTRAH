#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_rgb_dp_train
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-03:50:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/train_yam_rgb_dp_%j.out

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
TORCH_CACHE_NFS="${TORCH_CACHE_NFS:-$NFS_ROOT/cache/torch}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_pickplace_rgb_dp_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
MANIFEST="${MANIFEST:?Set MANIFEST to the YAM RGB policy manifest.json path.}"
INIT_CHECKPOINT="${INIT_CHECKPOINT:-}"
INIT_MODE="${INIT_MODE:-resume}"
NORMALIZER_CHECKPOINT="${NORMALIZER_CHECKPOINT:-$INIT_CHECKPOINT}"
COPY_FINAL_CHECKPOINT="${COPY_FINAL_CHECKPOINT:-True}"
CODE_COMMIT="${CODE_COMMIT:-}"

ROBOT_STATE_DIM="${ROBOT_STATE_DIM:-24}"
IMAGE_SIZE="${IMAGE_SIZE:-256}"
VAL_RATIO="${VAL_RATIO:-0.1}"
LR="${LR:-0.0001}"
NUM_EPOCHS="${NUM_EPOCHS:-50}"
MAX_TRAIN_STEPS="${MAX_TRAIN_STEPS:-2000000}"
MAX_VAL_STEPS="${MAX_VAL_STEPS:-200}"
LR_WARMUP_STEPS="${LR_WARMUP_STEPS:-500}"
BATCH_SIZE="${BATCH_SIZE:-80}"
VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-80}"
NUM_WORKERS="${NUM_WORKERS:-8}"
VAL_NUM_WORKERS="${VAL_NUM_WORKERS:-4}"
USE_EMA="${USE_EMA:-true}"
TRAINING_DEVICE="${TRAINING_DEVICE:-cuda:0}"
RESUME="${RESUME:-false}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
RGB_MODEL_WEIGHTS="${RGB_MODEL_WEIGHTS:-IMAGENET1K_V1}"
SHARE_RGB_MODEL="${SHARE_RGB_MODEL:-false}"
IMAGE_AUGMENTATION="${IMAGE_AUGMENTATION:-true}"
SAMPLE_EVERY="${SAMPLE_EVERY:-5}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-1}"
VAL_EVERY="${VAL_EVERY:-1}"
ROLLOUT_EVERY="${ROLLOUT_EVERY:-1}"
TOPK_CHECKPOINTS="${TOPK_CHECKPOINTS:-50}"
SEED="${SEED:-42}"

RUN_ROOT_HOST="$RESULTS_NFS/dp_bc/yam_pickplace_rgb/$RUN_NAME"
TRAIN_DIR_HOST="$RUN_ROOT_HOST/official_dp_train"
RUN_ROOT_CONTAINER="/results/dp_bc/yam_pickplace_rgb/$RUN_NAME"
TRAIN_DIR_CONTAINER="$RUN_ROOT_CONTAINER/official_dp_train"
STAGED_CHECKPOINT_HOST="$RESULTS_NFS/dp_bc/checkpoints/$RUN_NAME/latest.ckpt"

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
INIT_CHECKPOINT_HOST="$(host_path_from_container "$INIT_CHECKPOINT")"
INIT_CHECKPOINT_ARG="$(container_path_from_host "$INIT_CHECKPOINT")"
NORMALIZER_CHECKPOINT_HOST="$(host_path_from_container "$NORMALIZER_CHECKPOINT")"
NORMALIZER_CHECKPOINT_ARG="$(container_path_from_host "$NORMALIZER_CHECKPOINT")"

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
if [ ! -f "$MANIFEST_HOST" ]; then
  echo "Missing YAM RGB policy manifest: $MANIFEST_HOST"
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT got $actual_commit" >&2
    exit 2
  fi
fi
if [ -n "$INIT_CHECKPOINT" ] && [ ! -f "$INIT_CHECKPOINT_HOST" ]; then
  echo "Missing init checkpoint: $INIT_CHECKPOINT_HOST"
  exit 2
fi
if [ "$INIT_MODE" != "resume" ] && [ "$INIT_MODE" != "weights" ]; then
  echo "INIT_MODE must be resume or weights, got: $INIT_MODE" >&2
  exit 2
fi
if [ -n "$NORMALIZER_CHECKPOINT" ] && [ ! -f "$NORMALIZER_CHECKPOINT_HOST" ]; then
  echo "Missing normalizer checkpoint: $NORMALIZER_CHECKPOINT_HOST"
  exit 2
fi
if [ "$VAL_EVERY" -lt 1 ] || [ "$CHECKPOINT_EVERY" -lt 1 ] || [ $((CHECKPOINT_EVERY % VAL_EVERY)) -ne 0 ]; then
  echo "CHECKPOINT_EVERY must be a positive multiple of VAL_EVERY: $CHECKPOINT_EVERY/$VAL_EVERY" >&2
  exit 2
fi

mkdir -p \
  "$TRAIN_DIR_HOST/checkpoints" \
  "$(dirname "$STAGED_CHECKPOINT_HOST")" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"
mkdir -p "$TORCH_CACHE_NFS/hub/checkpoints"

if [ -n "$INIT_CHECKPOINT" ] && [ "$INIT_MODE" = "resume" ]; then
  cp "$INIT_CHECKPOINT_HOST" "$TRAIN_DIR_HOST/checkpoints/latest.ckpt"
  RESUME=true
elif [ -n "$INIT_CHECKPOINT" ]; then
  RESUME=false
fi

export RUN_NAME RUN_ROOT_CONTAINER TRAIN_DIR_CONTAINER MANIFEST_ARG INIT_CHECKPOINT_ARG INIT_MODE NORMALIZER_CHECKPOINT_ARG
export ROBOT_STATE_DIM IMAGE_SIZE VAL_RATIO LR NUM_EPOCHS MAX_TRAIN_STEPS MAX_VAL_STEPS LR_WARMUP_STEPS
export BATCH_SIZE VAL_BATCH_SIZE NUM_WORKERS VAL_NUM_WORKERS USE_EMA TRAINING_DEVICE RESUME NUM_INFERENCE_STEPS
export RGB_MODEL_WEIGHTS SHARE_RGB_MODEL IMAGE_AUGMENTATION
export SAMPLE_EVERY CHECKPOINT_EVERY VAL_EVERY ROLLOUT_EVERY TOPK_CHECKPOINTS SEED ENV_NAME OFFICIAL_DP_ENV_NAME

echo "Running YAM pick-place RGB Diffusion Policy training"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-}"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "TRAIN_DIR_HOST=$TRAIN_DIR_HOST"
echo "MANIFEST_ARG=$MANIFEST_ARG"
echo "INIT_CHECKPOINT_ARG=${INIT_CHECKPOINT_ARG:-}"
echo "INIT_MODE=$INIT_MODE"
echo "NORMALIZER_CHECKPOINT_ARG=${NORMALIZER_CHECKPOINT_ARG:-}"
echo "ROBOT_STATE_DIM=$ROBOT_STATE_DIM IMAGE_SIZE=$IMAGE_SIZE"
echo "VAL_RATIO=$VAL_RATIO LR=$LR NUM_EPOCHS=$NUM_EPOCHS MAX_TRAIN_STEPS=$MAX_TRAIN_STEPS"
echo "BATCH_SIZE=$BATCH_SIZE VAL_BATCH_SIZE=$VAL_BATCH_SIZE NUM_WORKERS=$NUM_WORKERS VAL_NUM_WORKERS=$VAL_NUM_WORKERS USE_EMA=$USE_EMA"
echo "RGB_MODEL_WEIGHTS=$RGB_MODEL_WEIGHTS SHARE_RGB_MODEL=$SHARE_RGB_MODEL IMAGE_AUGMENTATION=$IMAGE_AUGMENTATION"
echo "CHECKPOINT_EVERY=$CHECKPOINT_EVERY TOPK_CHECKPOINTS=$TOPK_CHECKPOINTS"
echo "STAGED_CHECKPOINT_HOST=$STAGED_CHECKPOINT_HOST"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$TORCH_CACHE_NFS":/root/.cache/torch,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export DP_SITE="/envs/$OFFICIAL_DP_ENV_NAME/site"
    export PYTHONPATH="$SITE:$DP_SITE:/code:/fabrics/src:/official_dp"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    export TORCH_HOME=/root/.cache/torch
    mkdir -p "$TRAIN_DIR_CONTAINER/checkpoints"
    WEIGHT_INIT_CHECKPOINT_ARG=""
    if [ "$INIT_MODE" = "weights" ]; then
      WEIGHT_INIT_CHECKPOINT_ARG="$INIT_CHECKPOINT_ARG"
    fi
    cd /official_dp
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git -C /code rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    TRAIN_ARGS=(
      /official_dp/train.py
      --config-dir /code/dextrah_lab/offline_dp_bc/config
      --config-name yam_pickplace_rgb_dp
      "task.manifest_path=$MANIFEST_ARG"
      "task.dataset.val_ratio=$VAL_RATIO"
      "shape_meta.obs.scene_rgb.shape=[3,$IMAGE_SIZE,$IMAGE_SIZE]"
      "shape_meta.obs.wrist_rgb.shape=[3,$IMAGE_SIZE,$IMAGE_SIZE]"
      "shape_meta.obs.robot_state.shape=[$ROBOT_STATE_DIM]"
      "training.device=$TRAINING_DEVICE"
      "training.use_ema=$USE_EMA"
      "training.resume=$RESUME"
      "training.init_checkpoint=$WEIGHT_INIT_CHECKPOINT_ARG"
      "training.num_epochs=$NUM_EPOCHS"
      "training.max_train_steps=$MAX_TRAIN_STEPS"
      "training.max_val_steps=$MAX_VAL_STEPS"
      "training.lr_warmup_steps=$LR_WARMUP_STEPS"
      "training.checkpoint_every=$CHECKPOINT_EVERY"
      "training.rollout_every=$ROLLOUT_EVERY"
      "training.val_every=$VAL_EVERY"
      "training.sample_every=$SAMPLE_EVERY"
      "policy.num_inference_steps=$NUM_INFERENCE_STEPS"
      "policy.obs_encoder.rgb_model.weights=$RGB_MODEL_WEIGHTS"
      "policy.obs_encoder.share_rgb_model=$SHARE_RGB_MODEL"
      "task.dataset.image_augmentation.enabled=$IMAGE_AUGMENTATION"
      "checkpoint.topk.k=$TOPK_CHECKPOINTS"
      "dataloader.batch_size=$BATCH_SIZE"
      "dataloader.num_workers=$NUM_WORKERS"
      "val_dataloader.batch_size=$VAL_BATCH_SIZE"
      "val_dataloader.num_workers=$VAL_NUM_WORKERS"
      "optimizer.lr=$LR"
      "logging.mode=offline"
      "logging.name=$RUN_NAME"
      "training.seed=$SEED"
      "hydra.run.dir=$TRAIN_DIR_CONTAINER"
    )
    if [ -n "$NORMALIZER_CHECKPOINT_ARG" ]; then
      TRAIN_ARGS+=("task.dataset.normalizer_checkpoint=$NORMALIZER_CHECKPOINT_ARG")
    fi
    printf "yam_rgb_train_command="
    printf "%q " /isaac-sim/python.sh "${TRAIN_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${TRAIN_ARGS[@]}" 2>&1 | tee "$RUN_ROOT_CONTAINER/train_stdout.log"
  '

if [ ! -s "$TRAIN_DIR_HOST/logs.json.txt" ]; then
  echo "Missing training logs JSON: $TRAIN_DIR_HOST/logs.json.txt"
  exit 1
fi
if [ ! -s "$TRAIN_DIR_HOST/checkpoints/latest.ckpt" ]; then
  echo "Missing latest checkpoint: $TRAIN_DIR_HOST/checkpoints/latest.ckpt"
  exit 1
fi
if [ "$COPY_FINAL_CHECKPOINT" = "True" ]; then
  cp "$TRAIN_DIR_HOST/checkpoints/latest.ckpt" "$STAGED_CHECKPOINT_HOST"
fi

python3 - "$TRAIN_DIR_HOST/logs.json.txt" <<'PY'
import json
import math
import sys

path = sys.argv[1]
rows = []
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
if not rows:
    raise SystemExit(f"No JSON rows in {path}")
losses = [float(r["train_loss"]) for r in rows if "train_loss" in r]
if not losses or not all(math.isfinite(v) for v in losses):
    raise SystemExit("Missing or non-finite train losses")
last = rows[-1]
print("YAM RGB DP train metrics passed")
print(json.dumps({
    "rows": len(rows),
    "first_step": rows[0].get("global_step"),
    "last_step": last.get("global_step"),
    "last_epoch": last.get("epoch"),
    "last_train_loss": last.get("train_loss"),
    "last_val_loss": last.get("val_loss"),
    "last_lr": last.get("lr"),
}, sort_keys=True))
PY

echo "YAM RGB DP Training Done"
echo "RUN_ROOT_HOST=$RUN_ROOT_HOST"
echo "STAGED_CHECKPOINT_HOST=$STAGED_CHECKPOINT_HOST"
