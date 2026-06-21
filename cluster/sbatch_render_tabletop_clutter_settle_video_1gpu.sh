#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_clutter_vid
#SBATCH --partition=batch
#SBATCH --time=0-00:30:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/tabletop_clutter_video_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
ROBOLAB_NFS="${ROBOLAB_NFS:-$NFS_ROOT/src/RoboLab}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT="${GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT:-/results/assets/graspgen_objects_full_cpu_20260617_153051}"
GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH="${GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH:-$GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT/manifest.json}"

TASK="${TASK:-Dextrah-Franka-Tabletop-Clutter-Grasp}"
SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-tabletop_clutter_settle_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
NUM_ENVS="${NUM_ENVS:-1}"
SEED="${SEED:-42}"
SETTLE_STEPS="${SETTLE_STEPS:-180}"
CAPTURE_INTERVAL="${CAPTURE_INTERVAL:-2}"
FPS="${FPS:-30}"
VIDEO_SECONDS="${VIDEO_SECONDS:-}"
DEMO_MODE="${DEMO_MODE:-settle}"
DEMO_STEPS="${DEMO_STEPS:-180}"
DEMO_HIGH_HOLD_Z="${DEMO_HIGH_HOLD_Z:-0.16}"
DEMO_LOW_HOLD_Z="${DEMO_LOW_HOLD_Z:--0.02}"
RENDER_WARMUP_FRAMES="${RENDER_WARMUP_FRAMES:-2}"
CAMERA_EYE="${CAMERA_EYE:-}"
CAMERA_TARGET="${CAMERA_TARGET:-}"
if [ "$TASK" = "Dextrah-Single-YAM-Multi-Object-Grasp" ] || [ "$TASK" = "Dextrah-Single-YAM-Tabletop-Clutter-Grasp" ]; then
  OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-$GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH}"
  OBJECT_ASSETS_DIR="${OBJECT_ASSETS_DIR:-$GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT}"
else
  OBJECT_ASSET_MANIFEST_PATH="${OBJECT_ASSET_MANIFEST_PATH:-}"
  OBJECT_ASSETS_DIR="${OBJECT_ASSETS_DIR:-}"
fi
MAX_OBJECTS="${MAX_OBJECTS:-}"
OBJECT_ASSET_ASSIGNMENT="${OBJECT_ASSET_ASSIGNMENT:-}"
OBJECT_SPAWN_XY_RANDOMIZATION="${OBJECT_SPAWN_XY_RANDOMIZATION:-}"
OBJECT_SPAWN_YAW_RANDOMIZATION_DEG="${OBJECT_SPAWN_YAW_RANDOMIZATION_DEG:-}"
if [ "$TASK" = "Dextrah-Single-YAM-Tabletop-Clutter-Grasp" ]; then
  TABLETOP_CLUTTER_ASSET_MANIFEST_PATH="${TABLETOP_CLUTTER_ASSET_MANIFEST_PATH:-$GRASPGEN_FULL_OBJAVERSE_MANIFEST_PATH}"
  TABLETOP_CLUTTER_ASSETS_DIR="${TABLETOP_CLUTTER_ASSETS_DIR:-$GRASPGEN_FULL_OBJAVERSE_ASSET_ROOT}"
  TABLETOP_CLUTTER_MAX_OBJECTS="${TABLETOP_CLUTTER_MAX_OBJECTS:-0}"
else
  TABLETOP_CLUTTER_ASSET_MANIFEST_PATH="${TABLETOP_CLUTTER_ASSET_MANIFEST_PATH:-}"
  TABLETOP_CLUTTER_ASSETS_DIR="${TABLETOP_CLUTTER_ASSETS_DIR:-}"
  TABLETOP_CLUTTER_MAX_OBJECTS="${TABLETOP_CLUTTER_MAX_OBJECTS:-}"
fi
TABLETOP_CLUTTER_OBJECT_COUNT="${TABLETOP_CLUTTER_OBJECT_COUNT:-}"
TABLETOP_CLUTTER_ASSET_ASSIGNMENT="${TABLETOP_CLUTTER_ASSET_ASSIGNMENT:-}"
TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION="${TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION:-}"
TABLETOP_CLUTTER_SPAWN_YAW_RANDOMIZATION_DEG="${TABLETOP_CLUTTER_SPAWN_YAW_RANDOMIZATION_DEG:-}"
TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE="${TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE:-}"
TABLETOP_CLUTTER_SPAWN_Z_JITTER="${TABLETOP_CLUTTER_SPAWN_Z_JITTER:-}"
TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE="${TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE:-}"
TABLETOP_CLUTTER_STABLE_POSE_ENABLED="${TABLETOP_CLUTTER_STABLE_POSE_ENABLED:-}"
TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR="${TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR:-}"
TABLETOP_CLUTTER_STABLE_POSE_COUNT="${TABLETOP_CLUTTER_STABLE_POSE_COUNT:-}"
TABLETOP_CLUTTER_NON_OVERLAPPING="${TABLETOP_CLUTTER_NON_OVERLAPPING:-}"
TABLETOP_CLUTTER_PLACEMENT_PADDING="${TABLETOP_CLUTTER_PLACEMENT_PADDING:-}"
TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS="${TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS:-}"
TABLETOP_CLUTTER_MAX_XY_RADIUS="${TABLETOP_CLUTTER_MAX_XY_RADIUS:-}"
TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS="${TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS:-}"
TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS="${TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS:-}"
TABLETOP_CLUTTER_LINEAR_DAMPING="${TABLETOP_CLUTTER_LINEAR_DAMPING:-}"
TABLETOP_CLUTTER_ANGULAR_DAMPING="${TABLETOP_CLUTTER_ANGULAR_DAMPING:-}"
TABLETOP_CLUTTER_SLEEP_THRESHOLD="${TABLETOP_CLUTTER_SLEEP_THRESHOLD:-}"
TABLETOP_CLUTTER_STABILIZATION_THRESHOLD="${TABLETOP_CLUTTER_STABILIZATION_THRESHOLD:-}"
TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY="${TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY:-}"
OBJAVERSE_TEXTURED_MANIFEST_PATH="${OBJAVERSE_TEXTURED_MANIFEST_PATH:-}"
OBJAVERSE_TEXTURED_ASSET_DIR="${OBJAVERSE_TEXTURED_ASSET_DIR:-}"
OBJAVERSE_TEXTURED_MAX_ASSETS="${OBJAVERSE_TEXTURED_MAX_ASSETS:-}"
OBJAVERSE_TEXTURED_MESH_SOURCE="${OBJAVERSE_TEXTURED_MESH_SOURCE:-auto}"
OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE="${OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE:-False}"
OBJAVERSE_TEXTURED_FORCE_CONVERSION="${OBJAVERSE_TEXTURED_FORCE_CONVERSION:-False}"
OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION="${OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION:-convexHull}"
OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE="${OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE:-True}"
OBJAVERSE_TEXTURED_STABLE_POSE_MESH_MODE="${OBJAVERSE_TEXTURED_STABLE_POSE_MESH_MODE:-convex_hull}"
DISABLE_FABRIC="${DISABLE_FABRIC:-False}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

RUN_DIR_HOST="$RESULTS_NFS/validations/$RUN_NAME"
RUN_DIR_CONTAINER="/results/validations/$RUN_NAME"
if [ -z "${VIDEO_FILENAME:-}" ]; then
  if [ "$DEMO_MODE" = "settle" ]; then
    VIDEO_FILENAME="settle.mp4"
  else
    VIDEO_FILENAME="${DEMO_MODE}.mp4"
  fi
fi
VIDEO_CONTAINER="$RUN_DIR_CONTAINER/$VIDEO_FILENAME"
METRICS_CONTAINER="$RUN_DIR_CONTAINER/metrics.json"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE" >&2
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site" >&2
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT, found $actual_commit in $CODE_NFS" >&2
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

export NFS_ROOT CODE_NFS FABRICS_NFS ISAACLAB_NFS ROBOLAB_NFS RESULTS_NFS
export TASK RUN_NAME NUM_ENVS SEED SETTLE_STEPS CAPTURE_INTERVAL FPS VIDEO_SECONDS DEMO_MODE DEMO_STEPS
export DEMO_HIGH_HOLD_Z DEMO_LOW_HOLD_Z RENDER_WARMUP_FRAMES
export CAMERA_EYE CAMERA_TARGET DISABLE_FABRIC PREPARE_YAM_ASSETS CODE_COMMIT ENV_NAME
export OBJECT_ASSET_MANIFEST_PATH OBJECT_ASSETS_DIR MAX_OBJECTS OBJECT_ASSET_ASSIGNMENT
export OBJECT_SPAWN_XY_RANDOMIZATION OBJECT_SPAWN_YAW_RANDOMIZATION_DEG
export TABLETOP_CLUTTER_ASSET_MANIFEST_PATH TABLETOP_CLUTTER_ASSETS_DIR TABLETOP_CLUTTER_MAX_OBJECTS
export TABLETOP_CLUTTER_OBJECT_COUNT TABLETOP_CLUTTER_ASSET_ASSIGNMENT TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION
export TABLETOP_CLUTTER_SPAWN_YAW_RANDOMIZATION_DEG TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE
export TABLETOP_CLUTTER_SPAWN_Z_JITTER TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE
export TABLETOP_CLUTTER_STABLE_POSE_ENABLED TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR
export TABLETOP_CLUTTER_STABLE_POSE_COUNT
export TABLETOP_CLUTTER_NON_OVERLAPPING TABLETOP_CLUTTER_PLACEMENT_PADDING TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS
export TABLETOP_CLUTTER_MAX_XY_RADIUS TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS
export TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS TABLETOP_CLUTTER_LINEAR_DAMPING
export TABLETOP_CLUTTER_ANGULAR_DAMPING TABLETOP_CLUTTER_SLEEP_THRESHOLD
export TABLETOP_CLUTTER_STABILIZATION_THRESHOLD TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY
export OBJAVERSE_TEXTURED_MANIFEST_PATH OBJAVERSE_TEXTURED_ASSET_DIR OBJAVERSE_TEXTURED_MAX_ASSETS
export OBJAVERSE_TEXTURED_MESH_SOURCE OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE
export OBJAVERSE_TEXTURED_FORCE_CONVERSION OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION
export OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE OBJAVERSE_TEXTURED_STABLE_POSE_MESH_MODE
export RUN_DIR_CONTAINER VIDEO_CONTAINER METRICS_CONTAINER

echo "Running DEXTRAH tabletop clutter settle video"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "ROBOLAB_NFS=$ROBOLAB_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "NUM_ENVS=$NUM_ENVS"
echo "SEED=$SEED"
echo "SETTLE_STEPS=$SETTLE_STEPS"
echo "CAPTURE_INTERVAL=$CAPTURE_INTERVAL"
echo "FPS=$FPS"
echo "VIDEO_SECONDS=${VIDEO_SECONDS:-unset}"
echo "DEMO_MODE=$DEMO_MODE"
echo "DEMO_STEPS=$DEMO_STEPS"
echo "DEMO_HIGH_HOLD_Z=$DEMO_HIGH_HOLD_Z"
echo "DEMO_LOW_HOLD_Z=$DEMO_LOW_HOLD_Z"
echo "OBJAVERSE_TEXTURED_MANIFEST_PATH=${OBJAVERSE_TEXTURED_MANIFEST_PATH:-unset}"
echo "OBJAVERSE_TEXTURED_ASSET_DIR=${OBJAVERSE_TEXTURED_ASSET_DIR:-unset}"
echo "OBJAVERSE_TEXTURED_MAX_ASSETS=${OBJAVERSE_TEXTURED_MAX_ASSETS:-unset}"
echo "OBJAVERSE_TEXTURED_MESH_SOURCE=${OBJAVERSE_TEXTURED_MESH_SOURCE:-unset}"
echo "OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION=${OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION:-unset}"
echo "OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE=${OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE:-unset}"
echo "TABLETOP_CLUTTER_OBJECT_COUNT=${TABLETOP_CLUTTER_OBJECT_COUNT:-unset}"
echo "TABLETOP_CLUTTER_STABLE_POSE_ENABLED=${TABLETOP_CLUTTER_STABLE_POSE_ENABLED:-unset}"
echo "TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR=${TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR:-unset}"
echo "TABLETOP_CLUTTER_LINEAR_DAMPING=${TABLETOP_CLUTTER_LINEAR_DAMPING:-unset}"
echo "TABLETOP_CLUTTER_ANGULAR_DAMPING=${TABLETOP_CLUTTER_ANGULAR_DAMPING:-unset}"
echo "TABLETOP_CLUTTER_SLEEP_THRESHOLD=${TABLETOP_CLUTTER_SLEEP_THRESHOLD:-unset}"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "VIDEO_CONTAINER=$VIDEO_CONTAINER"
echo "METRICS_CONTAINER=$METRICS_CONTAINER"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ROBOLAB_NFS":/home/lzha/code/RoboLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
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
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true
    nvidia-smi || true

    if [[ "$TASK" == *YAM* ]]; then
      if [[ "$TASK" == Dextrah-Single-YAM-* ]]; then
        YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/yam_linear.usd
        YAM_PREPARE_ARGS=(--headless --converter mjcf --robot single)
      else
        YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd
        YAM_PREPARE_ARGS=(--headless --converter mjcf)
      fi
      if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
        /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py "${YAM_PREPARE_ARGS[@]}"
      fi
      test -s "$YAM_USD"
    fi

    cd /code/dextrah_lab/rl_games
    container_path_arg() {
      local value="$1"
      if [ -z "$value" ]; then
        return 0
      fi
      if [[ "$value" == "$RESULTS_NFS"* ]]; then
        printf "/results%s" "${value#$RESULTS_NFS}"
      elif [[ "$value" == "$CODE_NFS"* ]]; then
        printf "/code%s" "${value#$CODE_NFS}"
      elif [[ "$value" == "$FABRICS_NFS"* ]]; then
        printf "/fabrics%s" "${value#$FABRICS_NFS}"
      elif [[ "$value" == "$ISAACLAB_NFS"* ]]; then
        printf "/IsaacLab%s" "${value#$ISAACLAB_NFS}"
      elif [[ "$value" == "$ROBOLAB_NFS"* ]]; then
        printf "/home/lzha/code/RoboLab%s" "${value#$ROBOLAB_NFS}"
      else
        printf "%s" "$value"
      fi
    }
    ARGS=(
      --task "$TASK"
      --num_envs "$NUM_ENVS"
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --video_path "$VIDEO_CONTAINER"
      --metrics_path "$METRICS_CONTAINER"
      --settle_steps "$SETTLE_STEPS"
      --capture_interval "$CAPTURE_INTERVAL"
      --fps "$FPS"
      --demo_mode "$DEMO_MODE"
      --demo_steps "$DEMO_STEPS"
      --demo_high_hold_z "$DEMO_HIGH_HOLD_Z"
      --demo_low_hold_z "$DEMO_LOW_HOLD_Z"
      --render_warmup_frames "$RENDER_WARMUP_FRAMES"
      --headless
    )
    if [ -n "$VIDEO_SECONDS" ]; then
      ARGS+=(--video_seconds "$VIDEO_SECONDS")
    fi
    if [ "$DISABLE_FABRIC" = "True" ] || [ "$DISABLE_FABRIC" = "true" ] || [ "$DISABLE_FABRIC" = "1" ]; then
      ARGS+=(--disable_fabric)
    fi
    if [ -n "$CAMERA_EYE" ]; then
      read -r ex ey ez <<< "$CAMERA_EYE"
      ARGS+=(--camera_eye "$ex" "$ey" "$ez")
    fi
    if [ -n "$CAMERA_TARGET" ]; then
      read -r tx ty tz <<< "$CAMERA_TARGET"
      ARGS+=(--camera_target "$tx" "$ty" "$tz")
    fi
    if [ -n "$OBJECT_ASSET_MANIFEST_PATH" ]; then
      ARGS+=(--object_asset_manifest_path "$(container_path_arg "$OBJECT_ASSET_MANIFEST_PATH")")
    fi
    if [ -n "$OBJECT_ASSETS_DIR" ]; then
      ARGS+=(--object_assets_dir "$(container_path_arg "$OBJECT_ASSETS_DIR")")
    fi
    if [ -n "$MAX_OBJECTS" ]; then
      ARGS+=(--max_objects "$MAX_OBJECTS")
    fi
    if [ -n "$OBJECT_ASSET_ASSIGNMENT" ]; then
      ARGS+=(--object_asset_assignment "$OBJECT_ASSET_ASSIGNMENT")
    fi
    if [ -n "$OBJECT_SPAWN_XY_RANDOMIZATION" ]; then
      ARGS+=(--object_spawn_xy_randomization "$OBJECT_SPAWN_XY_RANDOMIZATION")
    fi
    if [ -n "$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG" ]; then
      ARGS+=(--object_spawn_yaw_randomization_deg "$OBJECT_SPAWN_YAW_RANDOMIZATION_DEG")
    fi
    if [ -n "$TABLETOP_CLUTTER_ASSET_MANIFEST_PATH" ]; then
      ARGS+=(--tabletop_clutter_asset_manifest_path "$(container_path_arg "$TABLETOP_CLUTTER_ASSET_MANIFEST_PATH")")
    fi
    if [ -n "$TABLETOP_CLUTTER_ASSETS_DIR" ]; then
      ARGS+=(--tabletop_clutter_assets_dir "$(container_path_arg "$TABLETOP_CLUTTER_ASSETS_DIR")")
    fi
    if [ -n "$TABLETOP_CLUTTER_MAX_OBJECTS" ]; then
      ARGS+=(--tabletop_clutter_max_objects "$TABLETOP_CLUTTER_MAX_OBJECTS")
    fi
    if [ -n "$TABLETOP_CLUTTER_OBJECT_COUNT" ]; then
      ARGS+=(--tabletop_clutter_object_count "$TABLETOP_CLUTTER_OBJECT_COUNT")
    fi
    if [ -n "$TABLETOP_CLUTTER_ASSET_ASSIGNMENT" ]; then
      ARGS+=(--tabletop_clutter_asset_assignment "$TABLETOP_CLUTTER_ASSET_ASSIGNMENT")
    fi
    if [ -n "$TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION" ]; then
      ARGS+=(--tabletop_clutter_spawn_xy_randomization "$TABLETOP_CLUTTER_SPAWN_XY_RANDOMIZATION")
    fi
    if [ -n "$TABLETOP_CLUTTER_SPAWN_YAW_RANDOMIZATION_DEG" ]; then
      ARGS+=(--tabletop_clutter_spawn_yaw_randomization_deg "$TABLETOP_CLUTTER_SPAWN_YAW_RANDOMIZATION_DEG")
    fi
    if [ -n "$TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE" ]; then
      ARGS+=(--tabletop_clutter_spawn_z_clearance "$TABLETOP_CLUTTER_SPAWN_Z_CLEARANCE")
    fi
    if [ -n "$TABLETOP_CLUTTER_SPAWN_Z_JITTER" ]; then
      ARGS+=(--tabletop_clutter_spawn_z_jitter "$TABLETOP_CLUTTER_SPAWN_Z_JITTER")
    fi
    if [ -n "$TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE" ]; then
      if [ "$TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE" = "True" ] || [ "$TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE" = "true" ] || [ "$TABLETOP_CLUTTER_REQUIRE_GRASPGEN_SCALE" = "1" ]; then
        ARGS+=(--tabletop_clutter_require_graspgen_scale)
      else
        ARGS+=(--no-tabletop_clutter_require_graspgen_scale)
      fi
    fi
    if [ -n "$TABLETOP_CLUTTER_STABLE_POSE_ENABLED" ]; then
      if [ "$TABLETOP_CLUTTER_STABLE_POSE_ENABLED" = "True" ] || [ "$TABLETOP_CLUTTER_STABLE_POSE_ENABLED" = "true" ] || [ "$TABLETOP_CLUTTER_STABLE_POSE_ENABLED" = "1" ]; then
        ARGS+=(--tabletop_clutter_stable_pose_enabled)
      else
        ARGS+=(--no-tabletop_clutter_stable_pose_enabled)
      fi
    fi
    if [ -n "$TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR" ]; then
      ARGS+=(--tabletop_clutter_stable_pose_cache_dir "$(container_path_arg "$TABLETOP_CLUTTER_STABLE_POSE_CACHE_DIR")")
    fi
    if [ -n "$TABLETOP_CLUTTER_STABLE_POSE_COUNT" ]; then
      ARGS+=(--tabletop_clutter_stable_pose_count "$TABLETOP_CLUTTER_STABLE_POSE_COUNT")
    fi
    if [ -n "$TABLETOP_CLUTTER_NON_OVERLAPPING" ]; then
      if [ "$TABLETOP_CLUTTER_NON_OVERLAPPING" = "True" ] || [ "$TABLETOP_CLUTTER_NON_OVERLAPPING" = "true" ] || [ "$TABLETOP_CLUTTER_NON_OVERLAPPING" = "1" ]; then
        ARGS+=(--tabletop_clutter_non_overlapping)
      else
        ARGS+=(--no-tabletop_clutter_non_overlapping)
      fi
    fi
    if [ -n "$TABLETOP_CLUTTER_PLACEMENT_PADDING" ]; then
      ARGS+=(--tabletop_clutter_placement_padding "$TABLETOP_CLUTTER_PLACEMENT_PADDING")
    fi
    if [ -n "$TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS" ]; then
      ARGS+=(--tabletop_clutter_placement_attempts "$TABLETOP_CLUTTER_PLACEMENT_ATTEMPTS")
    fi
    if [ -n "$TABLETOP_CLUTTER_MAX_XY_RADIUS" ]; then
      ARGS+=(--tabletop_clutter_max_xy_radius "$TABLETOP_CLUTTER_MAX_XY_RADIUS")
    fi
    if [ -n "$TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS" ]; then
      ARGS+=(--tabletop_clutter_solver_position_iterations "$TABLETOP_CLUTTER_SOLVER_POSITION_ITERATIONS")
    fi
    if [ -n "$TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS" ]; then
      ARGS+=(--tabletop_clutter_solver_velocity_iterations "$TABLETOP_CLUTTER_SOLVER_VELOCITY_ITERATIONS")
    fi
    if [ -n "$TABLETOP_CLUTTER_LINEAR_DAMPING" ]; then
      ARGS+=(--tabletop_clutter_linear_damping "$TABLETOP_CLUTTER_LINEAR_DAMPING")
    fi
    if [ -n "$TABLETOP_CLUTTER_ANGULAR_DAMPING" ]; then
      ARGS+=(--tabletop_clutter_angular_damping "$TABLETOP_CLUTTER_ANGULAR_DAMPING")
    fi
    if [ -n "$TABLETOP_CLUTTER_SLEEP_THRESHOLD" ]; then
      ARGS+=(--tabletop_clutter_sleep_threshold "$TABLETOP_CLUTTER_SLEEP_THRESHOLD")
    fi
    if [ -n "$TABLETOP_CLUTTER_STABILIZATION_THRESHOLD" ]; then
      ARGS+=(--tabletop_clutter_stabilization_threshold "$TABLETOP_CLUTTER_STABILIZATION_THRESHOLD")
    fi
    if [ -n "$TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY" ]; then
      ARGS+=(--tabletop_clutter_max_depenetration_velocity "$TABLETOP_CLUTTER_MAX_DEPENETRATION_VELOCITY")
    fi
    if [ -n "$OBJAVERSE_TEXTURED_MANIFEST_PATH" ]; then
      ARGS+=(--objaverse_textured_manifest_path "$(container_path_arg "$OBJAVERSE_TEXTURED_MANIFEST_PATH")")
    fi
    if [ -n "$OBJAVERSE_TEXTURED_ASSET_DIR" ]; then
      ARGS+=(--objaverse_textured_asset_dir "$(container_path_arg "$OBJAVERSE_TEXTURED_ASSET_DIR")")
    fi
    if [ -n "$OBJAVERSE_TEXTURED_MAX_ASSETS" ]; then
      ARGS+=(--objaverse_textured_max_assets "$OBJAVERSE_TEXTURED_MAX_ASSETS")
    fi
    if [ -n "$OBJAVERSE_TEXTURED_MESH_SOURCE" ]; then
      ARGS+=(--objaverse_textured_mesh_source "$OBJAVERSE_TEXTURED_MESH_SOURCE")
    fi
    if [ "$OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE" = "True" ] || [ "$OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE" = "true" ] || [ "$OBJAVERSE_TEXTURED_MAKE_INSTANCEABLE" = "1" ]; then
      ARGS+=(--objaverse_textured_make_instanceable)
    fi
    if [ -n "$OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION" ]; then
      ARGS+=(--objaverse_textured_collision_approximation "$OBJAVERSE_TEXTURED_COLLISION_APPROXIMATION")
    fi
    if [ -n "$OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE" ]; then
      if [ "$OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE" = "True" ] || [ "$OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE" = "true" ] || [ "$OBJAVERSE_TEXTURED_REQUIRE_GRASPGEN_PRIOR_SCALE" = "1" ]; then
        ARGS+=(--objaverse_textured_require_graspgen_prior_scale)
      else
        ARGS+=(--no-objaverse_textured_require_graspgen_prior_scale)
      fi
    fi
    if [ -n "$OBJAVERSE_TEXTURED_STABLE_POSE_MESH_MODE" ]; then
      ARGS+=(--objaverse_textured_stable_pose_mesh_mode "$OBJAVERSE_TEXTURED_STABLE_POSE_MESH_MODE")
    fi
    if [ "$OBJAVERSE_TEXTURED_FORCE_CONVERSION" = "True" ] || [ "$OBJAVERSE_TEXTURED_FORCE_CONVERSION" = "true" ] || [ "$OBJAVERSE_TEXTURED_FORCE_CONVERSION" = "1" ]; then
      ARGS+=(--objaverse_textured_force_conversion)
    fi

    /isaac-sim/python.sh render_tabletop_clutter_settle_video.py "${ARGS[@]}"
    test -s "$VIDEO_CONTAINER"
    test -s "$METRICS_CONTAINER"
  '

echo "Finished. Host artifacts:"
echo "  $RUN_DIR_HOST/settle.mp4"
echo "  $RUN_DIR_HOST/metrics.json"
