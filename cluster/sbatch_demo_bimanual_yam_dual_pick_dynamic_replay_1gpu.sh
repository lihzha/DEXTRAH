#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_dynamic_replay
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bimanual_yam_dynamic_replay_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
ISAAC_ENV_NAME="${ISAAC_ENV_NAME:-dextrah-isaaclab}"
ISAAC_IMAGE="${ISAAC_IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ISAAC_CACHE_NFS="${ISAAC_CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-bimanual_yam_dynamic_replay_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR_HOST="$RESULTS_NFS/bimanual_yam_dual_pick_dynamic_replay/$RUN_NAME"
RUN_DIR_CONTAINER="/results/bimanual_yam_dual_pick_dynamic_replay/$RUN_NAME"
TRAJECTORY_HOST="${TRAJECTORY_HOST:-$RESULTS_NFS/bimanual_yam_dual_pick_demo/yam_dual_pick_demo_891fbe76_smallobj_20260622T2202/planning/dual_pick/bimanual_trajectory.json}"
TRAJECTORY_CONTAINER="${TRAJECTORY_CONTAINER:-}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
export CODE_COMMIT

SEED="${SEED:-42}"
RENDER_STRIDE="${RENDER_STRIDE:-4}"
FPS="${FPS:-15}"
SIM_STEPS_PER_FRAME="${SIM_STEPS_PER_FRAME:-2}"
SETTLE_STEPS="${SETTLE_STEPS:-60}"
DISABLE_FABRIC="${DISABLE_FABRIC:-True}"
VIDEO_CRF="${VIDEO_CRF:-18}"
WARMUP_RENDER_UPDATES="${WARMUP_RENDER_UPDATES:-6}"
RENDER_SYNC_UPDATES="${RENDER_SYNC_UPDATES:-3}"
FORCE_CAMERA_RECOMPUTE="${FORCE_CAMERA_RECOMPUTE:-True}"
FAIL_ON_STATIC_VISUAL="${FAIL_ON_STATIC_VISUAL:-True}"
VISUAL_MOTION_MIN_CHANGED_PIXELS="${VISUAL_MOTION_MIN_CHANGED_PIXELS:-2500}"
VISUAL_MOTION_DIFF_THRESHOLD="${VISUAL_MOTION_DIFF_THRESHOLD:-8}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
YAM_ASSET_SOURCE_NFS="${YAM_ASSET_SOURCE_NFS:-$NFS_ROOT/src/worktrees/DEXTRAH/yam-molmoact2-camera-viz-78b99de/dextrah_lab/assets/yam}"

if [ -z "$TRAJECTORY_CONTAINER" ]; then
  case "$TRAJECTORY_HOST" in
    "$RESULTS_NFS"/*)
      trajectory_rel="${TRAJECTORY_HOST#"$RESULTS_NFS"/}"
      TRAJECTORY_CONTAINER="/results/$trajectory_rel"
      ;;
    *)
      echo "Set TRAJECTORY_CONTAINER when TRAJECTORY_HOST is outside RESULTS_NFS: $TRAJECTORY_HOST" >&2
      exit 2
      ;;
  esac
fi

if [ ! -f "$ISAAC_IMAGE" ]; then
  echo "Missing Isaac Lab container image: $ISAAC_IMAGE" >&2
  exit 2
fi
if [ ! -d "$ENV_NFS/$ISAAC_ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Isaac Python target: $ENV_NFS/$ISAAC_ENV_NAME/site" >&2
  exit 2
fi
if [ ! -s "$TRAJECTORY_HOST" ]; then
  echo "Missing bimanual trajectory: $TRAJECTORY_HOST" >&2
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
  "$ISAAC_CACHE_NFS/kit" "$ISAAC_CACHE_NFS/ov" "$ISAAC_CACHE_NFS/pip" \
  "$ISAAC_CACHE_NFS/glcache" "$ISAAC_CACHE_NFS/computecache" \
  "$ISAAC_CACHE_NFS/omni_logs" "$ISAAC_CACHE_NFS/carb_logs" \
  "$ISAAC_CACHE_NFS/data" "$ISAAC_CACHE_NFS/documents"

stage_yam_ignored_assets() {
  local target="$CODE_NFS/dextrah_lab/assets/yam"
  if [ -d "$YAM_ASSET_SOURCE_NFS/yam_mujoco/assets" ] && [ ! -s "$target/yam_mujoco/assets/d405.stl" ]; then
    mkdir -p "$target/yam_mujoco/assets"
    cp -a "$YAM_ASSET_SOURCE_NFS/yam_mujoco/assets"/d405* "$target/yam_mujoco/assets"/
    cp -a "$YAM_ASSET_SOURCE_NFS/yam_mujoco/assets"/wrist_camera_mount* "$target/yam_mujoco/assets"/
  fi
  if [ -d "$YAM_ASSET_SOURCE_NFS/yam_mjcf_usd" ] && [ ! -s "$target/yam_mjcf_usd/bimanual_yam_linear_flattened.usd" ]; then
    mkdir -p "$target/yam_mjcf_usd"
    cp -a "$YAM_ASSET_SOURCE_NFS/yam_mjcf_usd"/bimanual_yam_linear_flattened.usd "$target/yam_mjcf_usd"/
  fi
  if [ -d "$YAM_ASSET_SOURCE_NFS/yam_mjcf_usd/configuration" ]; then
    mkdir -p "$target/yam_mjcf_usd/configuration"
    for asset in \
      bimanual_yam_linear_flattened_base.usd \
      bimanual_yam_linear_flattened_physics.usd \
      bimanual_yam_linear_flattened_robot.usd \
      bimanual_yam_linear_flattened_sensor.usd
    do
      if [ ! -s "$target/yam_mjcf_usd/configuration/$asset" ] && [ -s "$YAM_ASSET_SOURCE_NFS/yam_mjcf_usd/configuration/$asset" ]; then
        cp -a "$YAM_ASSET_SOURCE_NFS/yam_mjcf_usd/configuration/$asset" "$target/yam_mjcf_usd/configuration/"
      fi
    done
  fi
}
stage_yam_ignored_assets

echo "Running bimanual YAM dual-pick dynamic replay"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "TRAJECTORY_HOST=$TRAJECTORY_HOST"
echo "RENDER_STRIDE=$RENDER_STRIDE FPS=$FPS SIM_STEPS_PER_FRAME=$SIM_STEPS_PER_FRAME SETTLE_STEPS=$SETTLE_STEPS"
echo "WARMUP_RENDER_UPDATES=$WARMUP_RENDER_UPDATES RENDER_SYNC_UPDATES=$RENDER_SYNC_UPDATES FORCE_CAMERA_RECOMPUTE=$FORCE_CAMERA_RECOMPUTE FAIL_ON_STATIC_VISUAL=$FAIL_ON_STATIC_VISUAL"
echo "VISUAL_MOTION_MIN_CHANGED_PIXELS=$VISUAL_MOTION_MIN_CHANGED_PIXELS VISUAL_MOTION_DIFF_THRESHOLD=$VISUAL_MOTION_DIFF_THRESHOLD"

export RUN_DIR_CONTAINER RUN_NAME SEED RENDER_STRIDE FPS SIM_STEPS_PER_FRAME SETTLE_STEPS DISABLE_FABRIC VIDEO_CRF
export WARMUP_RENDER_UPDATES RENDER_SYNC_UPDATES FORCE_CAMERA_RECOMPUTE FAIL_ON_STATIC_VISUAL
export VISUAL_MOTION_MIN_CHANGED_PIXELS VISUAL_MOTION_DIFF_THRESHOLD
export PREPARE_YAM_ASSETS ISAAC_ENV_NAME TRAJECTORY_CONTAINER
srun \
  --ntasks=1 \
  --container-image="$ISAAC_IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_NFS":/envs,"$RESULTS_NFS":/results,"$ISAAC_CACHE_NFS/kit":/isaac-sim/kit/cache,"$ISAAC_CACHE_NFS/ov":/root/.cache/ov,"$ISAAC_CACHE_NFS/pip":/root/.cache/pip,"$ISAAC_CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$ISAAC_CACHE_NFS/computecache":/root/.nv/ComputeCache,"$ISAAC_CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$ISAAC_CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$ISAAC_CACHE_NFS/data":/root/.local/share/ov/data,"$ISAAC_CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export SITE="/envs/$ISAAC_ENV_NAME/site"
    export PYTHONPATH="$SITE:/code:/fabrics/src"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    mkdir -p "$RUN_DIR_CONTAINER/render" /results/logs /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default
    cd /code
    echo render_container_host=$(hostname)
    echo CODE_COMMIT=${CODE_COMMIT:-unknown}
    nvidia-smi || true
    YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd
    if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
      /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless --converter mjcf
    fi
    test -s "$YAM_USD"
    for asset in \
      /code/dextrah_lab/assets/yam/yam_mjcf_usd/configuration/bimanual_yam_linear_flattened_base.usd \
      /code/dextrah_lab/assets/yam/yam_mjcf_usd/configuration/bimanual_yam_linear_flattened_physics.usd \
      /code/dextrah_lab/assets/yam/yam_mjcf_usd/configuration/bimanual_yam_linear_flattened_robot.usd \
      /code/dextrah_lab/assets/yam/yam_mjcf_usd/configuration/bimanual_yam_linear_flattened_sensor.usd
    do
      test -s "$asset" || { echo "Missing required bimanual YAM USD payload: $asset" >&2; exit 2; }
    done
    ARGS=(
      dextrah_lab/scene_scripts/render_bimanual_yam_dual_pick_demo.py
      --headless
      --enable_cameras
      --device cuda:0
      --trajectory_path "$TRAJECTORY_CONTAINER"
      --output_dir "$RUN_DIR_CONTAINER/render"
      --seed "$SEED"
      --render_stride "$RENDER_STRIDE"
      --fps "$FPS"
      --sim_steps_per_frame "$SIM_STEPS_PER_FRAME"
      --settle_steps "$SETTLE_STEPS"
      --dynamic_replay
      --video_crf "$VIDEO_CRF"
      --warmup_render_updates "$WARMUP_RENDER_UPDATES"
      --render_sync_updates "$RENDER_SYNC_UPDATES"
      --visual_motion_min_changed_pixels "$VISUAL_MOTION_MIN_CHANGED_PIXELS"
      --visual_motion_diff_threshold "$VISUAL_MOTION_DIFF_THRESHOLD"
    )
    if [ "$DISABLE_FABRIC" = "True" ]; then
      ARGS+=(--disable_fabric)
    fi
    if [ "$FORCE_CAMERA_RECOMPUTE" = "True" ]; then
      ARGS+=(--force_camera_recompute)
    else
      ARGS+=(--no-force_camera_recompute)
    fi
    if [ "$FAIL_ON_STATIC_VISUAL" = "True" ]; then
      ARGS+=(--fail_on_static_visual)
    fi
    printf "dynamic_replay_command="
    printf "%q " /isaac-sim/python.sh "${ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${ARGS[@]}"
  '

if [ ! -s "$RUN_DIR_HOST/render/metadata.json" ]; then
  echo "Missing dynamic replay metadata: $RUN_DIR_HOST/render/metadata.json" >&2
  exit 1
fi
if [ ! -s "$RUN_DIR_HOST/render/bimanual_yam_dual_pick_composite.mp4" ]; then
  echo "Missing dynamic replay composite video: $RUN_DIR_HOST/render/bimanual_yam_dual_pick_composite.mp4" >&2
  exit 1
fi

echo "Bimanual YAM dynamic replay done: $RUN_DIR_HOST"
