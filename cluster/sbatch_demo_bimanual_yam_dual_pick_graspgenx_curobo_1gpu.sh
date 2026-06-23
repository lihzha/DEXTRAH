#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_dual_pick_demo
#SBATCH --partition=batch
#SBATCH --time=0-01:30:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bimanual_yam_dual_pick_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
GRASPGENX_NFS="${GRASPGENX_NFS:-$NFS_ROOT/src/graspgenx}"
CUROBO_NFS="${CUROBO_NFS:-$NFS_ROOT/src/curobo}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
ISAAC_ENV_NAME="${ISAAC_ENV_NAME:-dextrah-isaaclab}"
GRASPGENX_VENV_NAME="${GRASPGENX_VENV_NAME:-graspgenx-py312}"
ISAAC_IMAGE="${ISAAC_IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
GRASPGENX_IMAGE="${GRASPGENX_IMAGE:-$NFS_ROOT/cache/graspgenx_ngc2503_base.sqsh}"
PIP_CACHE_NFS="${PIP_CACHE_NFS:-$NFS_ROOT/cache/pip}"
ISAAC_CACHE_NFS="${ISAAC_CACHE_NFS:-$NFS_ROOT/isaac_cache}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-bimanual_yam_dual_pick_demo_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR_HOST="$RESULTS_NFS/bimanual_yam_dual_pick_demo/$RUN_NAME"
RUN_DIR_CONTAINER="/results/bimanual_yam_dual_pick_demo/$RUN_NAME"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
export CODE_COMMIT

SEED="${SEED:-42}"
NUM_GRASPS="${NUM_GRASPS:-96}"
TOPK="${TOPK:-48}"
MAX_PLAN_ATTEMPTS="${MAX_PLAN_ATTEMPTS:-48}"
SCRIPTED_LIFT_HEIGHT="${SCRIPTED_LIFT_HEIGHT:-0.12}"
SCRIPTED_LIFT_FRAMES="${SCRIPTED_LIFT_FRAMES:-180}"
START_GUARD_FRAMES="${START_GUARD_FRAMES:-60}"
OBJECT_DIMS="${OBJECT_DIMS:-0.08 0.08 0.08}"
RENDER_STRIDE="${RENDER_STRIDE:-3}"
FPS="${FPS:-20}"
SIM_STEPS_PER_FRAME="${SIM_STEPS_PER_FRAME:-1}"
DISABLE_FABRIC="${DISABLE_FABRIC:-True}"
VIDEO_CRF="${VIDEO_CRF:-18}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
YAM_ASSET_SOURCE_NFS="${YAM_ASSET_SOURCE_NFS:-$NFS_ROOT/src/worktrees/DEXTRAH/yam-molmoact2-camera-viz-78b99de/dextrah_lab/assets/yam}"

if [ ! -f "$GRASPGENX_IMAGE" ]; then
  echo "Missing GraspGenX container image: $GRASPGENX_IMAGE" >&2
  exit 2
fi
if [ ! -f "$ISAAC_IMAGE" ]; then
  echo "Missing Isaac Lab container image: $ISAAC_IMAGE" >&2
  exit 2
fi
if [ ! -x "$ENV_NFS/$GRASPGENX_VENV_NAME/bin/python" ]; then
  echo "Missing GraspGenX venv python: $ENV_NFS/$GRASPGENX_VENV_NAME/bin/python" >&2
  exit 2
fi
if [ ! -d "$ENV_NFS/$ISAAC_ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Isaac Python target: $ENV_NFS/$ISAAC_ENV_NAME/site" >&2
  exit 2
fi
if [ ! -f "$GRASPGENX_NFS/end2end/robots/yam_linear.yaml" ] || [ ! -f "$GRASPGENX_NFS/end2end/curobo_assets/yam_linear.urdf" ]; then
  echo "Missing single-YAM GraspGenX/cuRobo assets under $GRASPGENX_NFS" >&2
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
  "$PIP_CACHE_NFS" \
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
}
stage_yam_ignored_assets

echo "Running bimanual YAM dual-pick GraspGenX/cuRobo demo"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "GRASPGENX_NFS=$GRASPGENX_NFS"
echo "CUROBO_NFS=$CUROBO_NFS"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "NUM_GRASPS=$NUM_GRASPS TOPK=$TOPK MAX_PLAN_ATTEMPTS=$MAX_PLAN_ATTEMPTS"
echo "OBJECT_DIMS=$OBJECT_DIMS RENDER_STRIDE=$RENDER_STRIDE FPS=$FPS"

srun \
  --ntasks=1 \
  --container-image="$GRASPGENX_IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$GRASPGENX_NFS":/graspgenx,"$CUROBO_NFS":/curobo,"$RESULTS_NFS":/results,"$ENV_NFS":/envs,"$PIP_CACHE_NFS":/root/.cache/pip \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1,PYOPENGL_PLATFORM=egl,PYGLET_HEADLESS=true,EGL_PLATFORM=surfaceless,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,GRASPGENX_ROOT=/graspgenx,GRASPGENX_CUROBO_DIR=/curobo,GRASPGENX_CHECKPOINT_DIR=/graspgenx/ext/graspgenx_checkpoints,GRASPGENX_GRIPPER_CFG_DIR=/graspgenx/ext/gripper_descriptions \
  bash -lc "
    set -euo pipefail
    export VIRTUAL_ENV=/envs/$GRASPGENX_VENV_NAME
    export PATH=/envs/$GRASPGENX_VENV_NAME/bin:\$PATH
    export PYTHONPATH=/code:/graspgenx:/graspgenx/end2end:\${PYTHONPATH:-}
    cd /code
    echo planning_container_host=\$(hostname)
    python dextrah_lab/scene_scripts/plan_bimanual_yam_dual_pick_graspgenx_curobo.py \
      --output_dir '$RUN_DIR_CONTAINER/planning' \
      --run_name dual_pick \
      --graspgenx_root /graspgenx \
      --curobo_root /curobo \
      --seed '$SEED' \
      --object_dims $OBJECT_DIMS \
      --num_grasps '$NUM_GRASPS' \
      --topk '$TOPK' \
      --max_plan_attempts '$MAX_PLAN_ATTEMPTS' \
      --scripted_lift_mode always \
      --scripted_lift_height '$SCRIPTED_LIFT_HEIGHT' \
      --scripted_lift_frames '$SCRIPTED_LIFT_FRAMES' \
      --start_guard_frames '$START_GUARD_FRAMES'
  "

TRAJ_HOST="$RUN_DIR_HOST/planning/dual_pick/bimanual_trajectory.json"
if [ ! -s "$TRAJ_HOST" ]; then
  echo "Missing bimanual trajectory: $TRAJ_HOST" >&2
  exit 1
fi

export RUN_DIR_CONTAINER RUN_NAME SEED RENDER_STRIDE FPS SIM_STEPS_PER_FRAME DISABLE_FABRIC VIDEO_CRF PREPARE_YAM_ASSETS ISAAC_ENV_NAME
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
    ARGS=(
      dextrah_lab/scene_scripts/render_bimanual_yam_dual_pick_demo.py
      --headless
      --enable_cameras
      --device cuda:0
      --trajectory_path "$RUN_DIR_CONTAINER/planning/dual_pick/bimanual_trajectory.json"
      --output_dir "$RUN_DIR_CONTAINER/render"
      --seed "$SEED"
      --render_stride "$RENDER_STRIDE"
      --fps "$FPS"
      --sim_steps_per_frame "$SIM_STEPS_PER_FRAME"
      --video_crf "$VIDEO_CRF"
    )
    if [ "$DISABLE_FABRIC" = "True" ]; then
      ARGS+=(--disable_fabric)
    fi
    printf "render_command="
    printf "%q " /isaac-sim/python.sh "${ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${ARGS[@]}"
  '

if [ ! -s "$RUN_DIR_HOST/render/metadata.json" ]; then
  echo "Missing render metadata: $RUN_DIR_HOST/render/metadata.json" >&2
  exit 1
fi
if [ ! -s "$RUN_DIR_HOST/render/bimanual_yam_dual_pick_composite.mp4" ]; then
  echo "Missing composite video: $RUN_DIR_HOST/render/bimanual_yam_dual_pick_composite.mp4" >&2
  exit 1
fi

echo "Bimanual YAM dual-pick demo done: $RUN_DIR_HOST"
