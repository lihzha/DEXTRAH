#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_cube_relabel_set
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_%j.out

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
RUN_NAME="${RUN_NAME:-franka_cube_contact_relabel_set_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
DATASET="${DATASET:?Set DATASET to a converted lowdim NPZ visible in the container.}"
TRAJECTORY_ROOT="${TRAJECTORY_ROOT:-/results/dp_bc/curobo_plans}"
TRAJECTORY_TEMPLATE="${TRAJECTORY_TEMPLATE:-}"
if [ -z "$TRAJECTORY_TEMPLATE" ]; then
  TRAJECTORY_TEMPLATE='cube_curobo_scale32_20260611_125957_seed{episode}/trajectory.json'
fi
TRAJECTORY_JSON="${TRAJECTORY_JSON:-}"
SPEC_COUNT="${SPEC_COUNT:-0}"
EPISODE="${EPISODE:-24}"
EPISODE_STEP="${EPISODE_STEP:-260}"
RESET_JOINT_BLEND_ALPHA="${RESET_JOINT_BLEND_ALPHA:-1.0}"
SEED="${SEED:-42}"
VARIANT="${VARIANT:-center_high30}"
ORIENTATION_MODE="${ORIENTATION_MODE:-live}"
ALIGN_STEPS="${ALIGN_STEPS:-80}"
CLOSE_STEPS="${CLOSE_STEPS:-80}"
LIFT_STEPS="${LIFT_STEPS:-160}"
LIFT_HEIGHT="${LIFT_HEIGHT:-0.22}"
FINGER_GAIN="${FINGER_GAIN:-0.75}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
POSE_ACTION_FILTER="${POSE_ACTION_FILTER:-clip}"
POSE_ACTION_LIMIT="${POSE_ACTION_LIMIT:-1.0}"
PRINT_INTERVAL="${PRINT_INTERVAL:-80}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
VIDEO_LENGTH="${VIDEO_LENGTH:-320}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-franka-cube-contact-relabel}"
CAMERA_EYE_X="${CAMERA_EYE_X:--0.10}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:--0.78}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-1.42}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.41}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:--0.10}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.82}"
GATE_MIN_LIFT="${GATE_MIN_LIFT:-0.10}"
GATE_MAX_POSE_CLIP_FRACTION="${GATE_MAX_POSE_CLIP_FRACTION:-0.0}"
GATE_MAX_FINAL_EE_TO_CUBE="${GATE_MAX_FINAL_EE_TO_CUBE:-0.05}"
GATE_MAX_FINAL_FINGER_TO_CUBE="${GATE_MAX_FINAL_FINGER_TO_CUBE:-0.08}"

RUN_DIR_HOST="$RESULTS_NFS/contact_relabel_sets/$RUN_NAME"
RUN_DIR_CONTAINER="/results/contact_relabel_sets/$RUN_NAME"
LOG_FILE="$NFS_ROOT/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_${SLURM_JOB_ID_SAFE}.out"

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

resolve_trajectory_for_host_check() {
  local spec="$1"
  local ep step traj alpha
  IFS=: read -r ep step traj alpha <<< "$spec"
  if [ -z "${traj:-}" ]; then
    local template="$TRAJECTORY_TEMPLATE"
    template="$(printf '%s' "$template" | sed "s/{episode}/$ep/g; s/{seed}/$ep/g")"
    traj="$TRAJECTORY_ROOT/$template"
  fi
  host_path_from_container "$traj"
}

DATASET_HOST="$(host_path_from_container "$DATASET")"
DATASET_ARG="$(container_path_from_host "$DATASET")"
TRAJECTORY_ROOT_ARG="$(container_path_from_host "$TRAJECTORY_ROOT")"
TRAJECTORY_JSON_ARG=""
if [ -n "$TRAJECTORY_JSON" ]; then
  TRAJECTORY_JSON_ARG="$(container_path_from_host "$TRAJECTORY_JSON")"
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

SPEC_LIST=()
if [ "$SPEC_COUNT" -gt 0 ]; then
  for ((i=0; i<SPEC_COUNT; i++)); do
    name="SPEC_$i"
    if [ -z "${!name:-}" ]; then
      echo "Missing required $name while SPEC_COUNT=$SPEC_COUNT"
      exit 2
    fi
    export "$name"
    SPEC_LIST+=("${!name}")
  done
else
  if [ -z "$TRAJECTORY_JSON_ARG" ]; then
    echo "Set TRAJECTORY_JSON for the default single spec, or use SPEC_COUNT/SPEC_N with TRAJECTORY_ROOT."
    exit 2
  fi
  SPEC_LIST+=("$EPISODE:$EPISODE_STEP:$TRAJECTORY_JSON_ARG")
fi

for spec in "${SPEC_LIST[@]}"; do
  traj_host="$(resolve_trajectory_for_host_check "$spec")"
  if [ ! -f "$traj_host" ]; then
    echo "Missing trajectory JSON for spec $spec: $traj_host"
    exit 2
  fi
done

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME SEED DATASET_ARG TRAJECTORY_ROOT_ARG TRAJECTORY_TEMPLATE TRAJECTORY_JSON_ARG SPEC_COUNT
export RESET_JOINT_BLEND_ALPHA
export VARIANT ORIENTATION_MODE ALIGN_STEPS CLOSE_STEPS LIFT_STEPS LIFT_HEIGHT FINGER_GAIN CLIP_ACTIONS
export POSE_ACTION_FILTER POSE_ACTION_LIMIT PRINT_INTERVAL
export CAPTURE_VIDEO VIDEO_LENGTH VIDEO_NAME_PREFIX RUN_DIR_CONTAINER ENV_NAME
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export GATE_MIN_LIFT GATE_MAX_POSE_CLIP_FRACTION GATE_MAX_FINAL_EE_TO_CUBE GATE_MAX_FINAL_FINGER_TO_CUBE

echo "Running DextrAH Franka cube contact-aware relabel set gate"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "SPEC_COUNT=$SPEC_COUNT"
for ((i=0; i<${#SPEC_LIST[@]}; i++)); do
  echo "SPEC_$i=${SPEC_LIST[$i]}"
done
echo "VARIANT=$VARIANT"
echo "ORIENTATION_MODE=$ORIENTATION_MODE"
echo "RESET_JOINT_BLEND_ALPHA=$RESET_JOINT_BLEND_ALPHA"
echo "ALIGN_STEPS=$ALIGN_STEPS CLOSE_STEPS=$CLOSE_STEPS LIFT_STEPS=$LIFT_STEPS"
echo "LIFT_HEIGHT=$LIFT_HEIGHT FINGER_GAIN=$FINGER_GAIN CLIP_ACTIONS=$CLIP_ACTIONS"
echo "POSE_ACTION_FILTER=$POSE_ACTION_FILTER POSE_ACTION_LIMIT=$POSE_ACTION_LIMIT"
echo "DATASET_ARG=$DATASET_ARG"
echo "DATASET_HOST=$DATASET_HOST"
echo "TRAJECTORY_ROOT_ARG=$TRAJECTORY_ROOT_ARG"

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
    mkdir -p "$RUN_DIR_CONTAINER/rollouts"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    nvidia-smi || true

    SPEC_LIST=()
    if [ "${SPEC_COUNT:-0}" -gt 0 ]; then
      for ((i=0; i<SPEC_COUNT; i++)); do
        name="SPEC_$i"
        SPEC_LIST+=("${!name}")
      done
    else
      SPEC_LIST+=("${EPISODE:-24}:${EPISODE_STEP:-260}:${TRAJECTORY_JSON_ARG}")
    fi

    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH")
    fi

    for spec in "${SPEC_LIST[@]}"; do
      IFS=: read -r ep step traj alpha <<< "$spec"
      if [ -z "${traj:-}" ]; then
        template="$TRAJECTORY_TEMPLATE"
        template="$(printf "%s" "$template" | sed "s/{episode}/$ep/g; s/{seed}/$ep/g")"
        traj="$TRAJECTORY_ROOT_ARG/$template"
      fi
      if [ -z "${alpha:-}" ]; then
        alpha="$RESET_JOINT_BLEND_ALPHA"
      fi
      alpha_tag=$(printf "%s" "$alpha" | tr "." "p" | tr -c "A-Za-z0-9p_-" "_")
      rollout_id=$(printf "ep%02ds%03d_a%s" "$ep" "$step" "$alpha_tag")
      rollout_dir="$RUN_DIR_CONTAINER/rollouts/$rollout_id"
      mkdir -p "$rollout_dir"
      CMD=(
        /code/dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py
        --headless
        --device cuda:0
        --task "$TASK"
        --dataset "$DATASET_ARG"
        --trajectory_json "$traj"
        --episode "$ep"
        --episode_step "$step"
        --seed "$SEED"
        --align_steps "$ALIGN_STEPS"
        --close_steps "$CLOSE_STEPS"
        --lift_steps "$LIFT_STEPS"
        --lift_height "$LIFT_HEIGHT"
        --finger_gain "$FINGER_GAIN"
        --clip_actions "$CLIP_ACTIONS"
        --pose_action_filter "$POSE_ACTION_FILTER"
        --pose_action_limit "$POSE_ACTION_LIMIT"
        --orientation_mode "$ORIENTATION_MODE"
        --reset_joint_blend_alpha "$alpha"
        --output_dir "$rollout_dir"
        --print_interval "$PRINT_INTERVAL"
        --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
        --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
        --variant "$VARIANT"
        "${VIDEO_ARGS[@]}"
        --video_name_prefix "$VIDEO_NAME_PREFIX-$rollout_id"
      )
      printf "contact_relabel_rollout_command="
      printf "%q " /isaac-sim/python.sh "${CMD[@]}"
      printf "\n"
      /isaac-sim/python.sh "${CMD[@]}"
    done

    AGG_CMD=(
      /code/dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py
      --set_dir "$RUN_DIR_CONTAINER"
      --min_lift "$GATE_MIN_LIFT"
      --max_pose_clip_fraction "$GATE_MAX_POSE_CLIP_FRACTION"
      --max_final_ee_to_cube "$GATE_MAX_FINAL_EE_TO_CUBE"
      --max_final_finger_to_cube "$GATE_MAX_FINAL_FINGER_TO_CUBE"
    )
    printf "contact_relabel_set_aggregate_command="
    printf "%q " /isaac-sim/python.sh "${AGG_CMD[@]}"
    printf "\n"
    /isaac-sim/python.sh "${AGG_CMD[@]}"
  '

if [ -f "$LOG_FILE" ] && grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|FRANKA_CUBE_CONTACT_ROLLOUT_FAILED" "$LOG_FILE" >/dev/null; then
  echo "Detected contact-aware relabel set error patterns in $LOG_FILE."
  exit 1
fi

for artifact in contact_relabel_set_summary.json contact_relabel_set_rollouts.csv contact_relabel_set_failures.csv contact_relabel_set_report.md contact_relabel_set_accepted.npz; do
  if [ ! -s "$RUN_DIR_HOST/$artifact" ]; then
    echo "Missing contact relabel set artifact: $RUN_DIR_HOST/$artifact"
    exit 1
  fi
done

if [ "$CAPTURE_VIDEO" = "True" ] && ! find "$RUN_DIR_HOST/rollouts" -type f -name "*.mp4" -print -quit 2>/dev/null | grep -q .; then
  echo "Missing contact relabel rollout videos in $RUN_DIR_HOST/rollouts"
  exit 1
fi

echo "CONTACT_AWARE_FRANKA_CUBE_RELABEL_SET_DONE run_dir=$RUN_DIR_HOST"
