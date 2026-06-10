#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_eval
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-01:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_%j.out

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

TASK="${TASK:-Dextrah-Cube-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-cube_grasp_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-16}"
NUM_STEPS="${NUM_STEPS:-600}"
VIDEO_LENGTH="${VIDEO_LENGTH:-600}"
PRINT_INTERVAL="${PRINT_INTERVAL:-20}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-False}"
SEED="${SEED:-42}"
CHECKPOINT="${CHECKPOINT:-/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426/nn/last_dextrah_cube_grasp_ep_475_rew_1588.7792.pth}"

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/eval_cube_grasp_${SLURM_JOB_ID_SAFE}.out"

CHECKPOINT_ARG="$CHECKPOINT"
CHECKPOINT_HOST="$CHECKPOINT"
if [[ "$CHECKPOINT" == /results/* ]]; then
  CHECKPOINT_HOST="$RESULTS_NFS/${CHECKPOINT#/results/}"
elif [[ "$CHECKPOINT" == "$RESULTS_NFS"/* ]]; then
  rel_checkpoint="${CHECKPOINT#$RESULTS_NFS/}"
  CHECKPOINT_ARG="/results/$rel_checkpoint"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME NUM_ENVS NUM_STEPS VIDEO_LENGTH PRINT_INTERVAL CAPTURE_VIDEO USE_CUDA_GRAPH SEED
export CHECKPOINT_ARG RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME

echo "Running DextrAH cube grasp checkpoint evaluation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "NUM_STEPS=$NUM_STEPS"
echo "VIDEO_LENGTH=$VIDEO_LENGTH"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO"
echo "USE_CUDA_GRAPH=$USE_CUDA_GRAPH"
echo "SEED=$SEED"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
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
    git rev-parse HEAD || true
    echo "git_status_skipped=container_git_lfs_unavailable"
    nvidia-smi || true

    cd /code/dextrah_lab/rl_games

    /isaac-sim/python.sh - <<'"'"'PY'"'"'
import sys
import torch
import isaaclab
import fabrics_sim
import dextrah_lab
print("python", sys.version)
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(), "device_count", torch.cuda.device_count())
print("isaaclab", isaaclab.__file__)
print("fabrics_sim", fabrics_sim.__file__)
print("dextrah_lab", dextrah_lab.__file__)
PY

    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH")
    fi

    TASK_OVERRIDES=(
      agent.wandb_activate=False
      env.max_pose_angle=45.0
      env.enable_adr=False
      env.use_cuda_graph="$USE_CUDA_GRAPH"
      "env.adr_custom_cfg_dict.object_spawn.x_width_spawn=[0.08, 0.08]"
      "env.adr_custom_cfg_dict.object_spawn.y_width_spawn=[0.08, 0.08]"
    )

    EVAL_ARGS=(
      eval_rollout.py
      --headless
      --task="$TASK"
      --checkpoint "$CHECKPOINT_ARG"
      --num_envs "$NUM_ENVS"
      --num_steps "$NUM_STEPS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --print_interval "$PRINT_INTERVAL"
      "${VIDEO_ARGS[@]}"
      "${TASK_OVERRIDES[@]}"
    )

    printf "eval_command="
    printf "%q " /isaac-sim/python.sh "${EVAL_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${EVAL_ARGS[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected eval error patterns in $LOG_FILE."
  exit 1
fi

echo "Evaluation Done"
