#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=8
#SBATCH --job-name=dextrah_teacher_8gpu
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-03:50:00
#SBATCH --mem=0
#SBATCH --cpus-per-task=64
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_%j.out
#SBATCH --signal=B:TERM@300

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

NPROC_PER_NODE="${NPROC_PER_NODE:-8}"
NUM_NODES="${NUM_NODES:-1}"
TASK="${TASK:-Dextrah-Kuka-Allegro}"
USE_CUDA_GRAPH="${USE_CUDA_GRAPH:-True}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-0}"
JOB_ID_SUFFIX="${SLURM_JOB_ID_SAFE: -4}"
MASTER_PORT="${MASTER_PORT:-$((10000 + 10#$JOB_ID_SUFFIX))}"
MAX_ITERATIONS="${MAX_ITERATIONS:-}"
DISTRIBUTED="${DISTRIBUTED:-True}"
MULTI_GPU="${MULTI_GPU:-True}"
if [ "$TASK" = "Dextrah-Cube-Grasp" ]; then
  NUM_ENVS="${NUM_ENVS:-4096}"
  MINIBATCH_SIZE="${MINIBATCH_SIZE:-32768}"
  CENTRAL_VALUE_MINIBATCH_SIZE="${CENTRAL_VALUE_MINIBATCH_SIZE:-32768}"
  LEARNING_RATE="${LEARNING_RATE:-0.0002}"
  CENTRAL_VALUE_LEARNING_RATE="${CENTRAL_VALUE_LEARNING_RATE:-0.0001}"
  HORIZON_LENGTH="${HORIZON_LENGTH:-32}"
  MINI_EPOCHS="${MINI_EPOCHS:-4}"
  SAVE_FREQUENCY="${SAVE_FREQUENCY:-25}"
  GAMMA="${GAMMA:-0.995}"
  TAU="${TAU:-0.95}"
  KL_THRESHOLD="${KL_THRESHOLD:-0.012}"
  ENTROPY_COEF="${ENTROPY_COEF:-0.0005}"
  E_CLIP="${E_CLIP:-0.2}"
  GRAD_NORM="${GRAD_NORM:-1.0}"
elif [ "$TASK" = "Dextrah-Franka-Star-Kitting" ]; then
  NUM_ENVS="${NUM_ENVS:-2048}"
  MINIBATCH_SIZE="${MINIBATCH_SIZE:-32768}"
  CENTRAL_VALUE_MINIBATCH_SIZE="${CENTRAL_VALUE_MINIBATCH_SIZE:-32768}"
  LEARNING_RATE="${LEARNING_RATE:-0.00015}"
  CENTRAL_VALUE_LEARNING_RATE="${CENTRAL_VALUE_LEARNING_RATE:-0.0001}"
  HORIZON_LENGTH="${HORIZON_LENGTH:-48}"
  MINI_EPOCHS="${MINI_EPOCHS:-4}"
  SAVE_FREQUENCY="${SAVE_FREQUENCY:-25}"
  GAMMA="${GAMMA:-0.997}"
  TAU="${TAU:-0.95}"
  KL_THRESHOLD="${KL_THRESHOLD:-0.012}"
  ENTROPY_COEF="${ENTROPY_COEF:-0.001}"
  E_CLIP="${E_CLIP:-0.2}"
  GRAD_NORM="${GRAD_NORM:-1.0}"
elif [ "$TASK" = "Dextrah-Franka-Cube-Grasp" ]; then
  NUM_ENVS="${NUM_ENVS:-2048}"
  MINIBATCH_SIZE="${MINIBATCH_SIZE:-32768}"
  CENTRAL_VALUE_MINIBATCH_SIZE="${CENTRAL_VALUE_MINIBATCH_SIZE:-32768}"
  LEARNING_RATE="${LEARNING_RATE:-0.0002}"
  CENTRAL_VALUE_LEARNING_RATE="${CENTRAL_VALUE_LEARNING_RATE:-0.0001}"
  HORIZON_LENGTH="${HORIZON_LENGTH:-64}"
  MINI_EPOCHS="${MINI_EPOCHS:-4}"
  SAVE_FREQUENCY="${SAVE_FREQUENCY:-25}"
  GAMMA="${GAMMA:-0.995}"
  TAU="${TAU:-0.95}"
  KL_THRESHOLD="${KL_THRESHOLD:-0.012}"
  ENTROPY_COEF="${ENTROPY_COEF:-0.0005}"
  E_CLIP="${E_CLIP:-0.2}"
  GRAD_NORM="${GRAD_NORM:-1.0}"
else
  NUM_ENVS="${NUM_ENVS:-4096}"
  MINIBATCH_SIZE="${MINIBATCH_SIZE:-16384}"
  CENTRAL_VALUE_MINIBATCH_SIZE="${CENTRAL_VALUE_MINIBATCH_SIZE:-$MINIBATCH_SIZE}"
  LEARNING_RATE="${LEARNING_RATE:-0.0001}"
  CENTRAL_VALUE_LEARNING_RATE="${CENTRAL_VALUE_LEARNING_RATE:-0.00005}"
  HORIZON_LENGTH="${HORIZON_LENGTH:-16}"
  MINI_EPOCHS="${MINI_EPOCHS:-4}"
  SAVE_FREQUENCY="${SAVE_FREQUENCY:-10}"
  GAMMA="${GAMMA:-0.998}"
  TAU="${TAU:-0.95}"
  KL_THRESHOLD="${KL_THRESHOLD:-0.013}"
  ENTROPY_COEF="${ENTROPY_COEF:-0.002}"
  E_CLIP="${E_CLIP:-0.2}"
  GRAD_NORM="${GRAD_NORM:-1.0}"
fi
SIGMA_INIT_VAL="${SIGMA_INIT_VAL:-0}"
STAR_RESET_NEAR_HAND_PROBABILITY="${STAR_RESET_NEAR_HAND_PROBABILITY:-0.0}"
STAR_RESET_NEAR_HAND_X="${STAR_RESET_NEAR_HAND_X:--0.360}"
STAR_RESET_NEAR_HAND_Y="${STAR_RESET_NEAR_HAND_Y:--0.120}"
STAR_RESET_NEAR_HAND_XY_NOISE="${STAR_RESET_NEAR_HAND_XY_NOISE:-0.020}"
CUBE_SPAWN_XY_RANDOMIZATION="${CUBE_SPAWN_XY_RANDOMIZATION:-0.08}"
AUTO_RESUME="${AUTO_RESUME:-True}"
CHECKPOINT="${CHECKPOINT:-}"
FULL_EXPERIMENT_NAME="${FULL_EXPERIMENT_NAME:-}"
SELF_RELAUNCH="${SELF_RELAUNCH:-True}"
REQUEUE_SIGNAL_WINDOW_SECONDS="${REQUEUE_SIGNAL_WINDOW_SECONDS:-420}"
REQUEUE_ON_EARLY_TERM="${REQUEUE_ON_EARLY_TERM:-False}"
RUN_NAME="${FULL_EXPERIMENT_NAME:-slurm_${SLURM_JOB_ID}}"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/teacher_8gpu_${SLURM_JOB_ID}.out"
SRUN_PID=""
REQUEUE_SUBMITTED=0

time_left_to_seconds() {
  local raw="${1// /}"
  if [ -z "$raw" ] || [ "$raw" = "N/A" ] || [ "$raw" = "UNLIMITED" ] || [ "$raw" = "INVALID" ]; then
    echo "-1"
    return 0
  fi

  local days=0
  local clock="$raw"
  if [[ "$clock" == *-* ]]; then
    days="${clock%%-*}"
    clock="${clock#*-}"
  fi

  local p1=0
  local p2=0
  local p3=""
  local hours=0
  local minutes=0
  local seconds=0
  IFS=: read -r p1 p2 p3 <<< "$clock"
  if [ -n "$p3" ]; then
    hours="$p1"
    minutes="$p2"
    seconds="$p3"
  else
    minutes="$p1"
    seconds="$p2"
  fi

  if ! [[ "$days" =~ ^[0-9]+$ && "$hours" =~ ^[0-9]+$ && "$minutes" =~ ^[0-9]+$ && "$seconds" =~ ^[0-9]+$ ]]; then
    echo "-1"
    return 0
  fi
  echo $((10#$days * 86400 + 10#$hours * 3600 + 10#$minutes * 60 + 10#$seconds))
}

current_time_left_seconds() {
  local raw_left=""
  raw_left="$(squeue -h -j "$SLURM_JOB_ID" -o "%L" 2>/dev/null | head -n 1 || true)"
  local parsed
  parsed="$(time_left_to_seconds "$raw_left")"
  if [ "$parsed" -ge 0 ]; then
    echo "$parsed"
    return 0
  fi

  if [[ "${SLURM_JOB_END_TIME:-}" =~ ^[0-9]+$ ]]; then
    local now
    now="$(date +%s)"
    echo $((SLURM_JOB_END_TIME - now))
    return 0
  fi

  echo "-1"
}

should_requeue_job() {
  local reason="${1:-signal}"
  if [ "$SELF_RELAUNCH" != "True" ]; then
    echo "SELF_RELAUNCH=$SELF_RELAUNCH; not requeuing job"
    return 1
  fi

  if [ "$REQUEUE_ON_EARLY_TERM" = "True" ]; then
    return 0
  fi

  local time_left
  time_left="$(current_time_left_seconds)"
  if [ "$time_left" -ge 0 ] && [ "$time_left" -le "$REQUEUE_SIGNAL_WINDOW_SECONDS" ]; then
    return 0
  fi

  echo "Not requeuing DEXTRAH job ${SLURM_JOB_ID} after $reason; time_left=${time_left}s exceeds requeue window ${REQUEUE_SIGNAL_WINDOW_SECONDS}s"
  echo "Set REQUEUE_ON_EARLY_TERM=True to requeue non-walltime TERM signals."
  return 1
}

requeue_job() {
  local reason="${1:-signal}"
  if ! should_requeue_job "$reason"; then
    return 0
  fi

  if [ "$REQUEUE_SUBMITTED" = "1" ]; then
    return 0
  fi
  REQUEUE_SUBMITTED=1

  echo "Requeuing DEXTRAH job ${SLURM_JOB_ID} for run $RUN_NAME after $reason"
  scontrol requeue "$SLURM_JOB_ID" || true
}

handle_signal() {
  local signal_name="$1"

  requeue_job "$signal_name"

  if [ -n "$SRUN_PID" ]; then
    echo "Forwarding $signal_name to srun pid $SRUN_PID"
    kill "-$signal_name" "$SRUN_PID" 2>/dev/null || true
  fi

  if [ "$signal_name" = "INT" ]; then
    exit 130
  fi
  exit 15
}

trap 'handle_signal TERM' TERM
trap 'handle_signal INT' INT

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  echo "Submit cluster/sbatch_import_isaaclab_sqsh.sh first."
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  echo "Submit cluster/sbatch_setup_dextrah_env.sh first."
  exit 2
fi

mkdir -p \
  "$RESULTS_NFS/logs" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

echo "Running DextrAH privileged FGP teacher training"
echo "SLURM_JOB_ID=$SLURM_JOB_ID"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "NPROC_PER_NODE=$NPROC_PER_NODE"
echo "NUM_ENVS=$NUM_ENVS"
echo "TASK=$TASK"
echo "MASTER_PORT=$MASTER_PORT"
echo "DISTRIBUTED=$DISTRIBUTED"
echo "MULTI_GPU=$MULTI_GPU"
echo "LEARNING_RATE=$LEARNING_RATE"
echo "CENTRAL_VALUE_LEARNING_RATE=$CENTRAL_VALUE_LEARNING_RATE"
echo "HORIZON_LENGTH=$HORIZON_LENGTH"
echo "MINIBATCH_SIZE=$MINIBATCH_SIZE"
echo "CENTRAL_VALUE_MINIBATCH_SIZE=$CENTRAL_VALUE_MINIBATCH_SIZE"
echo "MINI_EPOCHS=$MINI_EPOCHS"
echo "GAMMA=$GAMMA"
echo "TAU=$TAU"
echo "KL_THRESHOLD=$KL_THRESHOLD"
echo "ENTROPY_COEF=$ENTROPY_COEF"
echo "E_CLIP=$E_CLIP"
echo "GRAD_NORM=$GRAD_NORM"
echo "SIGMA_INIT_VAL=$SIGMA_INIT_VAL"
echo "STAR_RESET_NEAR_HAND_PROBABILITY=$STAR_RESET_NEAR_HAND_PROBABILITY"
echo "STAR_RESET_NEAR_HAND_X=$STAR_RESET_NEAR_HAND_X"
echo "STAR_RESET_NEAR_HAND_Y=$STAR_RESET_NEAR_HAND_Y"
echo "STAR_RESET_NEAR_HAND_XY_NOISE=$STAR_RESET_NEAR_HAND_XY_NOISE"
echo "CUBE_SPAWN_XY_RANDOMIZATION=$CUBE_SPAWN_XY_RANDOMIZATION"
echo "SAVE_FREQUENCY=$SAVE_FREQUENCY"
echo "AUTO_RESUME=$AUTO_RESUME"
echo "CHECKPOINT=$CHECKPOINT"
echo "FULL_EXPERIMENT_NAME=$FULL_EXPERIMENT_NAME"
echo "SELF_RELAUNCH=$SELF_RELAUNCH"
echo "REQUEUE_SIGNAL_WINDOW_SECONDS=$REQUEUE_SIGNAL_WINDOW_SECONDS"
echo "REQUEUE_ON_EARLY_TERM=$REQUEUE_ON_EARLY_TERM"
echo "RUN_NAME=$RUN_NAME"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,NCCL_DEBUG=INFO,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc "
    set -euxo pipefail
    export SITE='/envs/$ENV_NAME/site'
    export PYTHONPATH=\"\$SITE:/code:/fabrics/src\"
    for d in /IsaacLab/source/*; do
      if [ -d \"\$d\" ]; then
        export PYTHONPATH=\"\$d:\$PYTHONPATH\"
      fi
    done
    export MASTER_ADDR=127.0.0.1
    export MASTER_PORT='$MASTER_PORT'
    export WANDB_MODE=offline
    export DEXTRAH_AUTO_RESUME='$AUTO_RESUME'
    export DEXTRAH_RUN_NAME='$RUN_NAME'
    export DEXTRAH_LOG_ROOT=/results/logs
    mkdir -p /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default
    mkdir -p /results/logs

    cd /code/dextrah_lab/rl_games

    /isaac-sim/python.sh - <<'PY'
import sys
import torch
import isaaclab
import fabrics_sim
import dextrah_lab
print('python', sys.version)
print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available(), 'device_count', torch.cuda.device_count())
print('isaaclab', isaaclab.__file__)
print('fabrics_sim', fabrics_sim.__file__)
print('dextrah_lab', dextrah_lab.__file__)
PY

    MAX_ITER_ARGS=()
    if [ -n '$MAX_ITERATIONS' ]; then
      MAX_ITER_ARGS=(--max_iterations '$MAX_ITERATIONS')
    fi

    DISTRIBUTED_ARGS=()
    if [ '$DISTRIBUTED' = 'True' ]; then
      DISTRIBUTED_ARGS=(--distributed)
    fi

    RESUME_ARGS=()
    if [ -n '$CHECKPOINT' ]; then
      RESUME_ARGS=(--checkpoint '$CHECKPOINT')
    elif [ '$AUTO_RESUME' = 'True' ]; then
      RESUME_ARGS=(--auto_resume)
    fi

    TASK_OVERRIDES=()
    if [ '$TASK' = 'Dextrah-Cube-Grasp' ]; then
      TASK_OVERRIDES=(
        agent.wandb_activate=False
        env.max_pose_angle=45.0
        env.use_cuda_graph='$USE_CUDA_GRAPH'
        env.enable_adr=False
        'env.adr_custom_cfg_dict.object_spawn.x_width_spawn=[0.08, 0.08]'
        'env.adr_custom_cfg_dict.object_spawn.y_width_spawn=[0.08, 0.08]'
      )
    elif [ '$TASK' = 'Dextrah-Franka-Star-Kitting' ]; then
      TASK_OVERRIDES=(
        agent.wandb_activate=False
        env.use_cuda_graph='$USE_CUDA_GRAPH'
        env.star_reset_near_hand_probability='$STAR_RESET_NEAR_HAND_PROBABILITY'
        env.star_reset_near_hand_x='$STAR_RESET_NEAR_HAND_X'
        env.star_reset_near_hand_y='$STAR_RESET_NEAR_HAND_Y'
        env.star_reset_near_hand_xy_noise='$STAR_RESET_NEAR_HAND_XY_NOISE'
      )
    elif [ '$TASK' = 'Dextrah-Franka-Cube-Grasp' ]; then
      TASK_OVERRIDES=(
        agent.wandb_activate=False
        env.use_cuda_graph='$USE_CUDA_GRAPH'
        env.cube_spawn_xy_randomization='$CUBE_SPAWN_XY_RANDOMIZATION'
      )
    else
      TASK_OVERRIDES=(
        agent.wandb_activate=False
        env.success_for_adr=0.4
        env.objects_dir=visdex_objects
        'env.adr_custom_cfg_dict.fabric_damping.gain=[10.0, 20.0]'
        'env.adr_custom_cfg_dict.reward_weights.finger_curl_reg=[-0.01, -0.01]'
        'env.adr_custom_cfg_dict.reward_weights.lift_weight=[5.0, 0.0]'
        env.max_pose_angle=45.0
        env.use_cuda_graph='$USE_CUDA_GRAPH'
      )
    fi

    TRAIN_ARGS=(
      train.py \
        --headless \
        --task='$TASK' \
        --seed -1 \
        \"\${DISTRIBUTED_ARGS[@]}\" \
        \"\${RESUME_ARGS[@]}\" \
        --num_envs '$NUM_ENVS' \
        \"\${MAX_ITER_ARGS[@]}\" \
        agent.params.config.minibatch_size='$MINIBATCH_SIZE' \
        agent.params.config.central_value_config.minibatch_size='$CENTRAL_VALUE_MINIBATCH_SIZE' \
        agent.params.config.learning_rate='$LEARNING_RATE' \
        agent.params.config.central_value_config.learning_rate='$CENTRAL_VALUE_LEARNING_RATE' \
        agent.params.config.horizon_length='$HORIZON_LENGTH' \
        agent.params.config.mini_epochs='$MINI_EPOCHS' \
        agent.params.config.gamma='$GAMMA' \
        agent.params.config.tau='$TAU' \
        agent.params.config.kl_threshold='$KL_THRESHOLD' \
        agent.params.config.central_value_config.kl_threshold='$KL_THRESHOLD' \
        agent.params.config.entropy_coef='$ENTROPY_COEF' \
        agent.params.network.space.continuous.sigma_init.val='$SIGMA_INIT_VAL' \
        agent.params.config.e_clip='$E_CLIP' \
        agent.params.config.grad_norm='$GRAD_NORM' \
        agent.params.config.save_frequency='$SAVE_FREQUENCY' \
        agent.params.config.multi_gpu='$MULTI_GPU' \
        \"\${TASK_OVERRIDES[@]}\"
    )

    if [ '$DISTRIBUTED' = 'True' ]; then
      /isaac-sim/python.sh -m torch.distributed.run \
        --nnodes='$NUM_NODES' \
        --nproc_per_node='$NPROC_PER_NODE' \
        --master_addr=127.0.0.1 \
        --master_port='$MASTER_PORT' \
        \"\${TRAIN_ARGS[@]}\"
    else
      /isaac-sim/python.sh \"\${TRAIN_ARGS[@]}\"
    fi
  " &
SRUN_PID=$!
set +e
wait "$SRUN_PID"
SRUN_EXIT=$?
set -e

if [ "$SRUN_EXIT" -ge 128 ]; then
  echo "srun killed by signal $((SRUN_EXIT - 128)) (exit $SRUN_EXIT)"
  requeue_job "srun_exit_$SRUN_EXIT"
  exit 15
elif [ "$SRUN_EXIT" -ne 0 ]; then
  echo "srun exited with code $SRUN_EXIT (training error), NOT requeuing."
  exit "$SRUN_EXIT"
fi

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|Error executing job with overrides|ChildFailedError|Could not execute <function load" "$LOG_FILE" >/dev/null; then
  echo "Detected training error patterns in $LOG_FILE despite zero srun exit; NOT requeuing."
  exit 1
fi

echo "Training Done"
