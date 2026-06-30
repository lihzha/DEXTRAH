#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_rgb_dp_eval
#SBATCH --partition=batch
#SBATCH --time=0-01:30:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_yam_pickplace_rgb_dp_policy_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
ROBOLAB_NFS="${ROBOLAB_NFS:-$NFS_ROOT/src/RoboLab}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
OFFICIAL_DP_NFS="${OFFICIAL_DP_NFS:-$NFS_ROOT/src/external/real-stanford-diffusion_policy}"
OFFICIAL_DP_ENV_NAME="${OFFICIAL_DP_ENV_NAME:-franka-cube-dp-bc-warmstart-official-dp}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
TASK="${TASK:-Dextrah-Single-YAM-Single-Object-Policy-Grasp}"
RUN_NAME="${RUN_NAME:-yam_pickplace_rgb_dp_eval_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
CONTROL_MODE="${CONTROL_MODE:-policy}"
DATASET_ACTION_POSE_GAIN="${DATASET_ACTION_POSE_GAIN:-1.0}"
CHECKPOINT="${CHECKPOINT:-}"
EXACT_POLICY_SHARD="${EXACT_POLICY_SHARD:-}"
EXACT_RENDER_WIDTH="${EXACT_RENDER_WIDTH:-1024}"
EXACT_RENDER_HEIGHT="${EXACT_RENDER_HEIGHT:-1024}"
CODE_COMMIT="${CODE_COMMIT:-}"

NUM_EPISODES="${NUM_EPISODES:-20}"
NUM_STEPS="${NUM_STEPS:-4800}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
NUM_ACTION_SAMPLES="${NUM_ACTION_SAMPLES:-1}"
POLICY_SAMPLE_SEED="${POLICY_SAMPLE_SEED:-}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-8}"
CLIP_ACTIONS="${CLIP_ACTIONS:-1.0}"
STOP_ON_DONE="${STOP_ON_DONE:-True}"
PRINT_INTERVAL="${PRINT_INTERVAL:-20}"
IMAGE_HEIGHT="${IMAGE_HEIGHT:-256}"
IMAGE_WIDTH="${IMAGE_WIDTH:-256}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
VIDEO_LENGTH="${VIDEO_LENGTH:-4800}"
VIDEO_NAME_PREFIX="${VIDEO_NAME_PREFIX:-yam-pickplace-rgb-dp-eval}"
SEED="${SEED:-42}"

CAMERA_EYE_X="${CAMERA_EYE_X:--0.50}"
CAMERA_EYE_Y="${CAMERA_EYE_Y:-0.04}"
CAMERA_EYE_Z="${CAMERA_EYE_Z:-0.68}"
CAMERA_TARGET_X="${CAMERA_TARGET_X:--0.25}"
CAMERA_TARGET_Y="${CAMERA_TARGET_Y:-0.04}"
CAMERA_TARGET_Z="${CAMERA_TARGET_Z:-0.03}"
SCENE_CAMERA_EYE_JITTER="${SCENE_CAMERA_EYE_JITTER:-0.018 0.018 0.018}"
SCENE_CAMERA_TARGET_JITTER="${SCENE_CAMERA_TARGET_JITTER:-0.012 0.012 0.012}"

YAM_POLICY_SCENE_RANDOMIZATION="${YAM_POLICY_SCENE_RANDOMIZATION:-True}"
YAM_POLICY_OBJECT_X_RANGE="${YAM_POLICY_OBJECT_X_RANGE:--0.34 -0.22}"
YAM_POLICY_OBJECT_Y_RANGE="${YAM_POLICY_OBJECT_Y_RANGE:--0.16 -0.04}"
YAM_POLICY_BIN_X_RANGE="${YAM_POLICY_BIN_X_RANGE:--0.32 -0.12}"
YAM_POLICY_BIN_Y_RANGE="${YAM_POLICY_BIN_Y_RANGE:-0.10 0.26}"
YAM_POLICY_BIN_INNER_SIZE_X_RANGE="${YAM_POLICY_BIN_INNER_SIZE_X_RANGE:-0.22 0.32}"
YAM_POLICY_BIN_INNER_SIZE_Y_RANGE="${YAM_POLICY_BIN_INNER_SIZE_Y_RANGE:-0.16 0.24}"
YAM_POLICY_BIN_WALL_HEIGHT_RANGE="${YAM_POLICY_BIN_WALL_HEIGHT_RANGE:-0.08 0.14}"
YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE="${YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE:-450 1600}"
YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE="${YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE:-250 1400}"
YAM_POLICY_MATERIAL_VALUE_RANGE="${YAM_POLICY_MATERIAL_VALUE_RANGE:-0.32 0.82}"
YAM_POLICY_TABLE_TEXTURE_DIR="${YAM_POLICY_TABLE_TEXTURE_DIR:-/code/dextrah_lab/assets/textures/tabletop_wood_light_polyhaven}"
YAM_POLICY_TABLE_TEXTURE_TILING_RANGE="${YAM_POLICY_TABLE_TEXTURE_TILING_RANGE:-1.4 3.8}"
YAM_POLICY_DOME_LIGHT_TEXTURE_DIR="${YAM_POLICY_DOME_LIGHT_TEXTURE_DIR:-/home/lzha/code/RoboLab/assets/backgrounds/indoors}"
YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH="${YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH:-}"
YAM_POLICY_OBJECT_ASSETS_DIR="${YAM_POLICY_OBJECT_ASSETS_DIR:-}"
YAM_POLICY_MAX_OBJECTS="${YAM_POLICY_MAX_OBJECTS:-0}"
YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS="${YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS:-}"
DEBUG_OBS_INTERVAL="${DEBUG_OBS_INTERVAL:-0}"
DEBUG_OBS_MAX_FRAMES="${DEBUG_OBS_MAX_FRAMES:-120}"
SCENE_RGB_CAPTURE_ATTEMPTS="${SCENE_RGB_CAPTURE_ATTEMPTS:-6}"
SCENE_RGB_BLACK_MEAN_THRESHOLD="${SCENE_RGB_BLACK_MEAN_THRESHOLD:-3.0}"

YAM_DEFAULT_ARM_QPOS="${YAM_DEFAULT_ARM_QPOS:-0.0 1.0 1.0 -1.5 0.0 0.0}"
YAM_DEFAULT_FINGER_QPOS="${YAM_DEFAULT_FINGER_QPOS:--0.0475}"
YAM_GRIPPER_STIFFNESS_SCALE="${YAM_GRIPPER_STIFFNESS_SCALE:-2.0}"
YAM_GRIPPER_DAMPING_SCALE="${YAM_GRIPPER_DAMPING_SCALE:-0.25}"
YAM_GRIPPER_EFFORT_SCALE="${YAM_GRIPPER_EFFORT_SCALE:-5.0}"

RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"

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
EXACT_POLICY_SHARD_HOST="$(host_path_from_container "$EXACT_POLICY_SHARD")"
EXACT_POLICY_SHARD_ARG="$(container_path_from_host "$EXACT_POLICY_SHARD")"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ ! -d "$OFFICIAL_DP_NFS/diffusion_policy" ]; then
  echo "Missing official Diffusion Policy checkout: $OFFICIAL_DP_NFS"
  exit 2
fi
if [ "$CONTROL_MODE" = "policy" ] && [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing YAM RGB Diffusion Policy checkpoint: $CHECKPOINT_HOST"
  exit 2
fi
if [ "$CONTROL_MODE" = "dataset_actions" ] && [ -z "$EXACT_POLICY_SHARD" ]; then
  echo "CONTROL_MODE=dataset_actions requires EXACT_POLICY_SHARD"
  exit 2
fi
if [ -n "$EXACT_POLICY_SHARD" ] && [ ! -e "$EXACT_POLICY_SHARD_HOST" ]; then
  echo "Missing exact YAM policy shard: $EXACT_POLICY_SHARD_HOST"
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
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

export TASK RUN_NAME CONTROL_MODE DATASET_ACTION_POSE_GAIN CHECKPOINT_ARG EXACT_POLICY_SHARD_ARG
export EXACT_RENDER_WIDTH EXACT_RENDER_HEIGHT
export RUN_DIR_CONTAINER METRICS_CONTAINER ENV_NAME OFFICIAL_DP_ENV_NAME
export NUM_EPISODES NUM_STEPS NUM_INFERENCE_STEPS NUM_ACTION_SAMPLES POLICY_SAMPLE_SEED
export ACTION_CHUNK_STEPS CLIP_ACTIONS STOP_ON_DONE PRINT_INTERVAL IMAGE_HEIGHT IMAGE_WIDTH RENDERING_MODE
export CAPTURE_VIDEO VIDEO_LENGTH VIDEO_NAME_PREFIX SEED
export CAMERA_EYE_X CAMERA_EYE_Y CAMERA_EYE_Z CAMERA_TARGET_X CAMERA_TARGET_Y CAMERA_TARGET_Z
export SCENE_CAMERA_EYE_JITTER SCENE_CAMERA_TARGET_JITTER YAM_POLICY_SCENE_RANDOMIZATION
export YAM_POLICY_OBJECT_X_RANGE YAM_POLICY_OBJECT_Y_RANGE YAM_POLICY_BIN_X_RANGE YAM_POLICY_BIN_Y_RANGE
export YAM_POLICY_BIN_INNER_SIZE_X_RANGE YAM_POLICY_BIN_INNER_SIZE_Y_RANGE YAM_POLICY_BIN_WALL_HEIGHT_RANGE
export YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE YAM_POLICY_MATERIAL_VALUE_RANGE
export YAM_POLICY_TABLE_TEXTURE_DIR YAM_POLICY_TABLE_TEXTURE_TILING_RANGE
export YAM_POLICY_DOME_LIGHT_TEXTURE_DIR
export YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH YAM_POLICY_OBJECT_ASSETS_DIR YAM_POLICY_MAX_OBJECTS
export YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS
export YAM_DEFAULT_ARM_QPOS YAM_DEFAULT_FINGER_QPOS
export YAM_GRIPPER_STIFFNESS_SCALE YAM_GRIPPER_DAMPING_SCALE YAM_GRIPPER_EFFORT_SCALE
export DEBUG_OBS_INTERVAL DEBUG_OBS_MAX_FRAMES
export SCENE_RGB_CAPTURE_ATTEMPTS SCENE_RGB_BLACK_MEAN_THRESHOLD

echo "Running DextrAH YAM pick-place RGB Diffusion Policy evaluation"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-}"
echo "OFFICIAL_DP_NFS=$OFFICIAL_DP_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TASK=$TASK"
echo "CONTROL_MODE=$CONTROL_MODE"
echo "DATASET_ACTION_POSE_GAIN=$DATASET_ACTION_POSE_GAIN"
echo "EXACT_POLICY_SHARD_ARG=${EXACT_POLICY_SHARD_ARG:-}"
echo "EXACT_RENDER_RESOLUTION=${EXACT_RENDER_WIDTH}x${EXACT_RENDER_HEIGHT}"
echo "NUM_EPISODES=$NUM_EPISODES NUM_STEPS=$NUM_STEPS"
echo "NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS NUM_ACTION_SAMPLES=$NUM_ACTION_SAMPLES"
echo "ACTION_CHUNK_STEPS=$ACTION_CHUNK_STEPS CLIP_ACTIONS=$CLIP_ACTIONS STOP_ON_DONE=$STOP_ON_DONE"
echo "IMAGE_HEIGHT=$IMAGE_HEIGHT IMAGE_WIDTH=$IMAGE_WIDTH RENDERING_MODE=$RENDERING_MODE"
echo "CAPTURE_VIDEO=$CAPTURE_VIDEO VIDEO_LENGTH=$VIDEO_LENGTH VIDEO_NAME_PREFIX=$VIDEO_NAME_PREFIX"
echo "SEED=$SEED"
echo "CAMERA_EYE=($CAMERA_EYE_X $CAMERA_EYE_Y $CAMERA_EYE_Z)"
echo "CAMERA_TARGET=($CAMERA_TARGET_X $CAMERA_TARGET_Y $CAMERA_TARGET_Z)"
echo "SCENE_CAMERA_EYE_JITTER=$SCENE_CAMERA_EYE_JITTER"
echo "SCENE_CAMERA_TARGET_JITTER=$SCENE_CAMERA_TARGET_JITTER"
echo "YAM_POLICY_OBJECT_X_RANGE=$YAM_POLICY_OBJECT_X_RANGE"
echo "YAM_POLICY_OBJECT_Y_RANGE=$YAM_POLICY_OBJECT_Y_RANGE"
echo "YAM_POLICY_BIN_X_RANGE=$YAM_POLICY_BIN_X_RANGE"
echo "YAM_POLICY_BIN_Y_RANGE=$YAM_POLICY_BIN_Y_RANGE"
echo "YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH=$YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH"
echo "YAM_POLICY_OBJECT_ASSETS_DIR=$YAM_POLICY_OBJECT_ASSETS_DIR"
echo "YAM_POLICY_MAX_OBJECTS=$YAM_POLICY_MAX_OBJECTS"
echo "YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS=$YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS"
echo "YAM_POLICY_TABLE_TEXTURE_DIR=$YAM_POLICY_TABLE_TEXTURE_DIR"
echo "YAM_POLICY_TABLE_TEXTURE_TILING_RANGE=$YAM_POLICY_TABLE_TEXTURE_TILING_RANGE"
echo "YAM_POLICY_DOME_LIGHT_TEXTURE_DIR=$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR"
echo "YAM_DEFAULT_ARM_QPOS=$YAM_DEFAULT_ARM_QPOS"
echo "YAM_DEFAULT_FINGER_QPOS=$YAM_DEFAULT_FINGER_QPOS"
echo "YAM_GRIPPER_GAINS=$YAM_GRIPPER_STIFFNESS_SCALE/$YAM_GRIPPER_DAMPING_SCALE/$YAM_GRIPPER_EFFORT_SCALE"
echo "DEBUG_OBS_INTERVAL=$DEBUG_OBS_INTERVAL DEBUG_OBS_MAX_FRAMES=$DEBUG_OBS_MAX_FRAMES"
echo "SCENE_RGB_CAPTURE_ATTEMPTS=$SCENE_RGB_CAPTURE_ATTEMPTS"
echo "SCENE_RGB_BLACK_MEAN_THRESHOLD=$SCENE_RGB_BLACK_MEAN_THRESHOLD"
echo "CHECKPOINT_ARG=$CHECKPOINT_ARG"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
echo "METRICS_CONTAINER=$METRICS_CONTAINER"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ROBOLAB_NFS":/home/lzha/code/RoboLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y,OMNI_KIT_ACCEPT_EULA=YES,CI=1,NONINTERACTIVE=1 \
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
    mkdir -p "$RUN_DIR_CONTAINER"
    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    git rev-parse HEAD || true
    git -C /official_dp rev-parse HEAD || true
    nvidia-smi || true

    VIDEO_ARGS=()
    if [ "$CAPTURE_VIDEO" = "True" ]; then
      VIDEO_ARGS=(--video --video_length "$VIDEO_LENGTH" --video_name_prefix "$VIDEO_NAME_PREFIX")
    fi
    STOP_ON_DONE_ARGS=(--stop_on_done)
    if [ "$STOP_ON_DONE" != "True" ]; then
      STOP_ON_DONE_ARGS=(--no-stop_on_done)
    fi
    RANDOMIZATION_ARGS=(--yam_policy_scene_randomization)
    if [ "$YAM_POLICY_SCENE_RANDOMIZATION" != "True" ]; then
      RANDOMIZATION_ARGS=(--no-yam_policy_scene_randomization)
    fi
    OBJECT_ASSET_ARGS=()
    if [ -n "$YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH" ]; then
      OBJECT_ASSET_ARGS+=(--yam_policy_object_asset_manifest_path "$YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH")
    fi
    if [ -n "$YAM_POLICY_OBJECT_ASSETS_DIR" ]; then
      OBJECT_ASSET_ARGS+=(--yam_policy_object_assets_dir "$YAM_POLICY_OBJECT_ASSETS_DIR")
    fi
    if [ "$YAM_POLICY_MAX_OBJECTS" != "0" ]; then
      OBJECT_ASSET_ARGS+=(--yam_policy_max_objects "$YAM_POLICY_MAX_OBJECTS")
    fi
    if [ "$YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS" = "True" ]; then
      OBJECT_ASSET_ARGS+=(--yam_policy_object_validate_usd_bounds)
    elif [ "$YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS" = "False" ]; then
      OBJECT_ASSET_ARGS+=(--no-yam_policy_object_validate_usd_bounds)
    fi
    POLICY_SEED_ARGS=()
    if [ -n "$POLICY_SAMPLE_SEED" ]; then
      POLICY_SEED_ARGS=(--policy_sample_seed "$POLICY_SAMPLE_SEED")
    fi

    CMD=(
      /isaac-sim/python.sh /code/dextrah_lab/rl_games/eval_yam_pickplace_rgb_dp_policy.py
      --checkpoint "$CHECKPOINT_ARG"
      --diffusion_policy_root /official_dp
      --task "$TASK"
      --control_mode "$CONTROL_MODE"
      --dataset_action_pose_gain "$DATASET_ACTION_POSE_GAIN"
      --exact_policy_shard "$EXACT_POLICY_SHARD_ARG"
      --exact_render_width "$EXACT_RENDER_WIDTH"
      --exact_render_height "$EXACT_RENDER_HEIGHT"
      --num_episodes "$NUM_EPISODES"
      --num_steps "$NUM_STEPS"
      --num_inference_steps "$NUM_INFERENCE_STEPS"
      --num_action_samples "$NUM_ACTION_SAMPLES"
      --action_chunk_steps "$ACTION_CHUNK_STEPS"
      --clip_actions "$CLIP_ACTIONS"
      --print_interval "$PRINT_INTERVAL"
      --image_height "$IMAGE_HEIGHT"
      --image_width "$IMAGE_WIDTH"
      --output_dir "$RUN_DIR_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --video_folder "$RUN_DIR_CONTAINER/videos"
      --seed "$SEED"
      --camera_eye "$CAMERA_EYE_X" "$CAMERA_EYE_Y" "$CAMERA_EYE_Z"
      --camera_target "$CAMERA_TARGET_X" "$CAMERA_TARGET_Y" "$CAMERA_TARGET_Z"
      --scene_camera_eye_jitter $SCENE_CAMERA_EYE_JITTER
      --scene_camera_target_jitter $SCENE_CAMERA_TARGET_JITTER
      "${RANDOMIZATION_ARGS[@]}"
      --yam_policy_object_x_range $YAM_POLICY_OBJECT_X_RANGE
      --yam_policy_object_y_range $YAM_POLICY_OBJECT_Y_RANGE
      --yam_policy_bin_x_range $YAM_POLICY_BIN_X_RANGE
      --yam_policy_bin_y_range $YAM_POLICY_BIN_Y_RANGE
      --yam_policy_bin_inner_size_x_range $YAM_POLICY_BIN_INNER_SIZE_X_RANGE
      --yam_policy_bin_inner_size_y_range $YAM_POLICY_BIN_INNER_SIZE_Y_RANGE
      --yam_policy_bin_wall_height_range $YAM_POLICY_BIN_WALL_HEIGHT_RANGE
      --yam_policy_dome_light_intensity_range $YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE
      --yam_policy_key_light_intensity_range $YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE
      --yam_policy_material_value_range $YAM_POLICY_MATERIAL_VALUE_RANGE
      --yam_policy_table_texture_dir "$YAM_POLICY_TABLE_TEXTURE_DIR"
      --yam_policy_table_texture_tiling_range $YAM_POLICY_TABLE_TEXTURE_TILING_RANGE
      --yam_policy_dome_light_texture_dir "$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR"
      "${OBJECT_ASSET_ARGS[@]}"
      --yam_default_arm_qpos $YAM_DEFAULT_ARM_QPOS
      --yam_default_finger_qpos "$YAM_DEFAULT_FINGER_QPOS"
      --yam_gripper_stiffness_scale "$YAM_GRIPPER_STIFFNESS_SCALE"
      --yam_gripper_damping_scale "$YAM_GRIPPER_DAMPING_SCALE"
      --yam_gripper_effort_scale "$YAM_GRIPPER_EFFORT_SCALE"
      --debug_obs_interval "$DEBUG_OBS_INTERVAL"
      --debug_obs_max_frames "$DEBUG_OBS_MAX_FRAMES"
      --scene_rgb_capture_attempts "$SCENE_RGB_CAPTURE_ATTEMPTS"
      --scene_rgb_black_mean_threshold "$SCENE_RGB_BLACK_MEAN_THRESHOLD"
      --headless
      --enable_cameras
      --device cuda:0
      --rendering_mode "$RENDERING_MODE"
      "${VIDEO_ARGS[@]}"
      "${STOP_ON_DONE_ARGS[@]}"
      "${POLICY_SEED_ARGS[@]}"
    )
    printf "yam_rgb_eval_command="
    printf "%q " "${CMD[@]}"
    printf "\n"
    "${CMD[@]}" 2>&1 | tee "$RUN_DIR_CONTAINER/eval_stdout.log"
  '

if [ ! -s "$RUN_DIR_HOST/metrics.json" ]; then
  echo "Missing eval metrics JSON: $RUN_DIR_HOST/metrics.json"
  exit 1
fi

python3 - "$RUN_DIR_HOST/metrics.json" "$NUM_STEPS" <<'PY'
import json
import math
import sys

path = sys.argv[1]
requested_steps = int(sys.argv[2])
payload = json.load(open(path, "r", encoding="utf-8"))
summary = payload.get("summary", {})
rate = summary.get("episode_success_rate")
if rate is not None and not math.isfinite(float(rate)):
    raise SystemExit(f"Non-finite episode_success_rate: {rate}")
early_truncations = []
for episode in summary.get("episodes", []):
    steps_completed = int(episode.get("steps_completed") or 0)
    first_done = episode.get("first_done") or {}
    if steps_completed < requested_steps and bool(first_done.get("truncated")) and not bool(first_done.get("terminated")):
        early_truncations.append({
            "episode": episode.get("episode"),
            "steps_completed": steps_completed,
            "requested_steps": requested_steps,
            "first_done": first_done,
        })
if early_truncations:
    raise SystemExit("Eval truncated before requested horizon: " + json.dumps(early_truncations[:3], sort_keys=True))
print("YAM RGB DP eval metrics passed")
print(json.dumps({
    "episodes_completed": summary.get("episodes_completed"),
    "steps_completed": summary.get("steps_completed"),
    "episode_success_rate": rate,
    "reward_mean": summary.get("reward_mean"),
    "video_files": summary.get("video_files", []),
}, sort_keys=True))
PY

echo "YAM RGB DP Eval Done"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "METRICS_HOST=$RUN_DIR_HOST/metrics.json"
