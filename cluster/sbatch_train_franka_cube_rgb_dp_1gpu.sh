#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_rgb_dp_train
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/train_franka_cube_rgb_dp_%j.out

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

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-franka_cube_rgb_dp_train_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
DATASET="${DATASET:?Set DATASET to an RGB BC dataset path visible on host or under /results.}"
INIT_CHECKPOINT="${INIT_CHECKPOINT:-}"
NORMALIZER_CHECKPOINT="${NORMALIZER_CHECKPOINT:-$INIT_CHECKPOINT}"
DISTILL_REFERENCE_CHECKPOINT="${DISTILL_REFERENCE_CHECKPOINT:-$INIT_CHECKPOINT}"
CREATE_MODEL_ONLY_BOOTSTRAP="${CREATE_MODEL_ONLY_BOOTSTRAP:-False}"
COPY_FINAL_CHECKPOINT="${COPY_FINAL_CHECKPOINT:-True}"

ROBOT_STATE_DIM="${ROBOT_STATE_DIM:-8}"
APPEND_PHASE_PROGRESS="${APPEND_PHASE_PROGRESS:-false}"
VAL_RATIO="${VAL_RATIO:-0.02}"
LR="${LR:-0.0001}"
NUM_EPOCHS="${NUM_EPOCHS:-20}"
MAX_TRAIN_STEPS="${MAX_TRAIN_STEPS:-10000}"
MAX_VAL_STEPS="${MAX_VAL_STEPS:-100}"
LR_WARMUP_STEPS="${LR_WARMUP_STEPS:-500}"
BATCH_SIZE="${BATCH_SIZE:-32}"
VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-32}"
USE_EMA="${USE_EMA:-false}"
TRAINING_DEVICE="${TRAINING_DEVICE:-cuda:0}"
RESUME="${RESUME:-false}"
DISTILL_MASK_MODE="${DISTILL_MASK_MODE:-none}"
DISTILL_MASK_TOLERANCE="${DISTILL_MASK_TOLERANCE:-1.0e-6}"
DISTILL_LOSS_WEIGHT="${DISTILL_LOSS_WEIGHT:-0.0}"
DISTILL_USE_ACTION_LOSS_WEIGHTS="${DISTILL_USE_ACTION_LOSS_WEIGHTS:-true}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
SAMPLE_EVERY="${SAMPLE_EVERY:-1000}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-1}"
VAL_EVERY="${VAL_EVERY:-1}"
ROLLOUT_EVERY="${ROLLOUT_EVERY:-1}"
SEED="${SEED:-42}"

RUN_ROOT_HOST="$RESULTS_NFS/dp_bc/official_dp_rgb/$RUN_NAME"
TRAIN_DIR_HOST="$RUN_ROOT_HOST/official_dp_train"
RUN_ROOT_CONTAINER="/results/dp_bc/official_dp_rgb/$RUN_NAME"
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

DATASET_HOST="$(host_path_from_container "$DATASET")"
DATASET_ARG="$(container_path_from_host "$DATASET")"
INIT_CHECKPOINT_HOST="$(host_path_from_container "$INIT_CHECKPOINT")"
INIT_CHECKPOINT_ARG="$(container_path_from_host "$INIT_CHECKPOINT")"
NORMALIZER_CHECKPOINT_HOST="$(host_path_from_container "$NORMALIZER_CHECKPOINT")"
NORMALIZER_CHECKPOINT_ARG="$(container_path_from_host "$NORMALIZER_CHECKPOINT")"
DISTILL_REFERENCE_CHECKPOINT_HOST="$(host_path_from_container "$DISTILL_REFERENCE_CHECKPOINT")"
DISTILL_REFERENCE_CHECKPOINT_ARG="$(container_path_from_host "$DISTILL_REFERENCE_CHECKPOINT")"

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
if [ ! -f "$DATASET_HOST" ]; then
  echo "Missing RGB BC dataset: $DATASET_HOST"
  exit 2
fi
if [ -n "$INIT_CHECKPOINT" ] && [ ! -f "$INIT_CHECKPOINT_HOST" ]; then
  echo "Missing init checkpoint: $INIT_CHECKPOINT_HOST"
  exit 2
fi
if [ -n "$NORMALIZER_CHECKPOINT" ] && [ ! -f "$NORMALIZER_CHECKPOINT_HOST" ]; then
  echo "Missing normalizer checkpoint: $NORMALIZER_CHECKPOINT_HOST"
  exit 2
fi
if [ -n "$DISTILL_REFERENCE_CHECKPOINT" ] && [ ! -f "$DISTILL_REFERENCE_CHECKPOINT_HOST" ]; then
  echo "Missing distill reference checkpoint: $DISTILL_REFERENCE_CHECKPOINT_HOST"
  exit 2
fi
if [ "$CREATE_MODEL_ONLY_BOOTSTRAP" = "True" ] && [ -z "$INIT_CHECKPOINT" ]; then
  echo "CREATE_MODEL_ONLY_BOOTSTRAP=True requires INIT_CHECKPOINT"
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

export RUN_NAME RUN_ROOT_CONTAINER TRAIN_DIR_CONTAINER
export DATASET_ARG INIT_CHECKPOINT_ARG NORMALIZER_CHECKPOINT_ARG DISTILL_REFERENCE_CHECKPOINT_ARG
export CREATE_MODEL_ONLY_BOOTSTRAP ROBOT_STATE_DIM APPEND_PHASE_PROGRESS VAL_RATIO
export LR NUM_EPOCHS MAX_TRAIN_STEPS MAX_VAL_STEPS LR_WARMUP_STEPS BATCH_SIZE VAL_BATCH_SIZE
export USE_EMA TRAINING_DEVICE RESUME DISTILL_MASK_MODE DISTILL_MASK_TOLERANCE
export DISTILL_LOSS_WEIGHT DISTILL_USE_ACTION_LOSS_WEIGHTS NUM_INFERENCE_STEPS
export SAMPLE_EVERY CHECKPOINT_EVERY VAL_EVERY ROLLOUT_EVERY SEED ENV_NAME OFFICIAL_DP_ENV_NAME

echo "Running DextrAH Franka cube RGB Diffusion Policy training"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_ROOT_HOST=$RUN_ROOT_HOST"
echo "TRAIN_DIR_HOST=$TRAIN_DIR_HOST"
echo "DATASET_ARG=$DATASET_ARG"
echo "DATASET_HOST=$DATASET_HOST"
echo "INIT_CHECKPOINT_ARG=${INIT_CHECKPOINT_ARG:-}"
echo "NORMALIZER_CHECKPOINT_ARG=${NORMALIZER_CHECKPOINT_ARG:-}"
echo "DISTILL_REFERENCE_CHECKPOINT_ARG=${DISTILL_REFERENCE_CHECKPOINT_ARG:-}"
echo "CREATE_MODEL_ONLY_BOOTSTRAP=$CREATE_MODEL_ONLY_BOOTSTRAP"
echo "ROBOT_STATE_DIM=$ROBOT_STATE_DIM APPEND_PHASE_PROGRESS=$APPEND_PHASE_PROGRESS"
echo "VAL_RATIO=$VAL_RATIO LR=$LR NUM_EPOCHS=$NUM_EPOCHS MAX_TRAIN_STEPS=$MAX_TRAIN_STEPS"
echo "MAX_VAL_STEPS=$MAX_VAL_STEPS LR_WARMUP_STEPS=$LR_WARMUP_STEPS"
echo "DISTILL_MASK_MODE=$DISTILL_MASK_MODE DISTILL_LOSS_WEIGHT=$DISTILL_LOSS_WEIGHT"
echo "STAGED_CHECKPOINT_HOST=$STAGED_CHECKPOINT_HOST"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
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
    mkdir -p "$TRAIN_DIR_CONTAINER/checkpoints"
    cd /official_dp
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git -C /code rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    if [ "$CREATE_MODEL_ONLY_BOOTSTRAP" = "True" ]; then
      /isaac-sim/python.sh - "$INIT_CHECKPOINT_ARG" "$TRAIN_DIR_CONTAINER/checkpoints/latest.ckpt" <<'"'"'PY'"'"'
import dill
import sys
import torch

src, dst = sys.argv[1:3]
payload = torch.load(src, pickle_module=dill, map_location="cpu")
model_state = payload["state_dicts"]["model"]
payload["state_dicts"] = {"model": model_state}
payload.setdefault("pickles", {})
payload["pickles"]["global_step"] = dill.dumps(0)
payload["pickles"]["epoch"] = dill.dumps(0)
torch.save(payload, dst, pickle_module=dill)
print(f"model_only_bootstrap src={src} dst={dst} tensors={len(model_state)}")
PY
    fi

    TRAIN_ARGS=(
      /official_dp/train.py
      --config-dir /code/dextrah_lab/offline_dp_bc/config
      --config-name franka_cube_rgb_dp
      "task.dataset_path=$DATASET_ARG"
      "+task.dataset.append_phase_progress=$APPEND_PHASE_PROGRESS"
      "shape_meta.obs.robot_state.shape=[$ROBOT_STATE_DIM]"
      "training.device=$TRAINING_DEVICE"
      "training.use_ema=$USE_EMA"
      "training.resume=$RESUME"
      "training.num_epochs=$NUM_EPOCHS"
      "training.max_train_steps=$MAX_TRAIN_STEPS"
      "training.max_val_steps=$MAX_VAL_STEPS"
      "training.lr_warmup_steps=$LR_WARMUP_STEPS"
      "training.checkpoint_every=$CHECKPOINT_EVERY"
      "training.rollout_every=$ROLLOUT_EVERY"
      "training.val_every=$VAL_EVERY"
      "training.sample_every=$SAMPLE_EVERY"
      "policy.num_inference_steps=$NUM_INFERENCE_STEPS"
      "policy.distill_loss_weight=$DISTILL_LOSS_WEIGHT"
      "policy.distill_use_action_loss_weights=$DISTILL_USE_ACTION_LOSS_WEIGHTS"
      "task.dataset.distill_mask_mode=$DISTILL_MASK_MODE"
      "task.dataset.distill_mask_tolerance=$DISTILL_MASK_TOLERANCE"
      "task.dataset.val_ratio=$VAL_RATIO"
      "dataloader.batch_size=$BATCH_SIZE"
      "val_dataloader.batch_size=$VAL_BATCH_SIZE"
      "optimizer.lr=$LR"
      "logging.mode=offline"
      "logging.name=$RUN_NAME"
      "training.seed=$SEED"
      "hydra.run.dir=$TRAIN_DIR_CONTAINER"
    )
    if [ -n "$DISTILL_REFERENCE_CHECKPOINT_ARG" ]; then
      TRAIN_ARGS+=("policy.distill_reference_checkpoint=$DISTILL_REFERENCE_CHECKPOINT_ARG")
    fi
    if [ -n "$NORMALIZER_CHECKPOINT_ARG" ]; then
      TRAIN_ARGS+=("task.dataset.normalizer_checkpoint=$NORMALIZER_CHECKPOINT_ARG")
    fi
    printf "rgb_train_command="
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
print("RGB DP train metrics passed")
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

echo "RGB DP Training Done"
echo "RUN_ROOT_HOST=$RUN_ROOT_HOST"
echo "STAGED_CHECKPOINT_HOST=$STAGED_CHECKPOINT_HOST"
