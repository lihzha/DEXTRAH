#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_target_frame
#SBATCH --partition=batch
#SBATCH --time=0-00:20:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/audit_franka_cube_target_frames_%j.out

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
TASK="${TASK:-Dextrah-Franka-Cube-Grasp}"
RUN_NAME="${RUN_NAME:-franka_cube_target_frame_audit_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
EPISODE="${EPISODE:-24}"
EPISODE_STEPS="${EPISODE_STEPS:-260,282,297,310,312,402,450,487}"
SEED="${SEED:-42}"
DATASET="${DATASET:?Set DATASET to a converted lowdim NPZ visible in the container.}"
TRAJECTORY_JSON="${TRAJECTORY_JSON:?Set TRAJECTORY_JSON to the raw source trajectory JSON visible in the container.}"
REPLAY_CSV="${REPLAY_CSV:-}"
REFERENCE_VIDEO="${REFERENCE_VIDEO:-}"
REFERENCE_CONTACT_SHEET="${REFERENCE_CONTACT_SHEET:-}"

RUN_DIR_HOST="$RESULTS_NFS/target_frame_audits/$RUN_NAME"
RUN_DIR_CONTAINER="/results/target_frame_audits/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/audit_franka_cube_target_frames_${SLURM_JOB_ID_SAFE}.out"

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
TRAJECTORY_JSON_HOST="$(host_path_from_container "$TRAJECTORY_JSON")"
DATASET_ARG="$(container_path_from_host "$DATASET")"
TRAJECTORY_JSON_ARG="$(container_path_from_host "$TRAJECTORY_JSON")"
REPLAY_CSV_ARG=""
if [ -n "$REPLAY_CSV" ]; then
  REPLAY_CSV_HOST="$(host_path_from_container "$REPLAY_CSV")"
  REPLAY_CSV_ARG="$(container_path_from_host "$REPLAY_CSV")"
else
  REPLAY_CSV_HOST=""
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -f "$DATASET_HOST" ]; then
  echo "Missing dataset: $DATASET_HOST"
  exit 2
fi
if [ ! -f "$TRAJECTORY_JSON_HOST" ]; then
  echo "Missing trajectory JSON: $TRAJECTORY_JSON_HOST"
  exit 2
fi
if [ -n "$REPLAY_CSV_HOST" ] && [ ! -f "$REPLAY_CSV_HOST" ]; then
  echo "Missing replay CSV: $REPLAY_CSV_HOST"
  exit 2
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME EPISODE EPISODE_STEPS SEED DATASET_ARG TRAJECTORY_JSON_ARG
export REPLAY_CSV_ARG REFERENCE_VIDEO REFERENCE_CONTACT_SHEET RUN_DIR_CONTAINER ENV_NAME

echo "Running DextrAH Franka cube target-frame audit"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "EPISODE=$EPISODE"
echo "EPISODE_STEPS=$EPISODE_STEPS"
echo "DATASET_ARG=$DATASET_ARG"
echo "DATASET_HOST=$DATASET_HOST"
echo "TRAJECTORY_JSON_ARG=$TRAJECTORY_JSON_ARG"
echo "TRAJECTORY_JSON_HOST=$TRAJECTORY_JSON_HOST"
echo "REPLAY_CSV_ARG=${REPLAY_CSV_ARG:-}"
echo "REPLAY_CSV_HOST=${REPLAY_CSV_HOST:-}"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    mkdir -p "$RUN_DIR_CONTAINER"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    nvidia-smi || true

    STEP_ARGS=()
    IFS=, read -ra STEP_LIST <<< "$EPISODE_STEPS"
    for step in "${STEP_LIST[@]}"; do
      STEP_ARGS+=(--episode_step "$step")
    done
    REPLAY_ARGS=()
    if [ -n "${REPLAY_CSV_ARG:-}" ]; then
      REPLAY_ARGS=(--replay_csv "$REPLAY_CSV_ARG")
    fi
    REFERENCE_ARGS=()
    if [ -n "${REFERENCE_VIDEO:-}" ]; then
      REFERENCE_ARGS+=(--reference_video "$REFERENCE_VIDEO")
    fi
    if [ -n "${REFERENCE_CONTACT_SHEET:-}" ]; then
      REFERENCE_ARGS+=(--reference_contact_sheet "$REFERENCE_CONTACT_SHEET")
    fi
    CMD=(
      /code/dextrah_lab/rl_games/audit_franka_cube_target_frames.py
      --headless
      --device cuda:0
      --task "$TASK"
      --dataset "$DATASET_ARG"
      --trajectory_json "$TRAJECTORY_JSON_ARG"
      --episode "$EPISODE"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      "${STEP_ARGS[@]}"
      "${REPLAY_ARGS[@]}"
      "${REFERENCE_ARGS[@]}"
    )
    printf "audit_command="
    printf "%q " /isaac-sim/python.sh "${CMD[@]}"
    printf "\n"
    /isaac-sim/python.sh "${CMD[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|FRANKA_CUBE_TARGET_FRAME_AUDIT_FAILED" "$LOG_FILE" >/dev/null; then
  echo "Detected target-frame audit error patterns in $LOG_FILE."
  exit 1
fi

for artifact in target_frame_summary.json target_frame_state_rows.csv target_frame_one_step.csv target_frame_report.md target_frame_state_plot.png target_frame_one_step_plot.png; do
  if [ ! -s "$RUN_DIR_HOST/$artifact" ]; then
    echo "Missing target-frame audit artifact: $RUN_DIR_HOST/$artifact"
    exit 1
  fi
done

echo "TARGET_FRAME_AUDIT_DONE run_dir=$RUN_DIR_HOST"
