#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_star_kitting
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/star_kitting_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
GRASPGENX_NFS="${GRASPGENX_NFS:-$NFS_ROOT/src/graspgenx}"
CUROBO_ASSETS_NFS="${CUROBO_ASSETS_NFS:-$NFS_ROOT/assets/curobo/content/assets}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
ROBOT="${ROBOT:-graspgenx_franka}"
RUN_NAME="${RUN_NAME:-star_kitting_${SLURM_JOB_ID:-manual}}"
OUT_DIR="$RESULTS_NFS/star_kitting_env/$RUN_NAME"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi
if [ "$ROBOT" = "graspgenx_franka" ]; then
  if [ ! -f "$GRASPGENX_NFS/end2end/robots/franka_panda.yaml" ]; then
    echo "Missing GraspGenX Franka config: $GRASPGENX_NFS/end2end/robots/franka_panda.yaml"
    exit 2
  fi
  if [ ! -f "$CUROBO_ASSETS_NFS/robot/franka_description/franka_panda.urdf" ]; then
    echo "Missing cuRobo Franka URDF: $CUROBO_ASSETS_NFS/robot/franka_description/franka_panda.urdf"
    exit 2
  fi
fi

mkdir -p \
  "$OUT_DIR" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

CONTAINER_MOUNTS="/dev/shm:/dev/shm,$CODE_NFS:/code,$FABRICS_NFS:/fabrics,$ISAACLAB_NFS:/IsaacLab,$ENV_ROOT:/envs,$RESULTS_NFS:/results,$CACHE_NFS/kit:/isaac-sim/kit/cache,$CACHE_NFS/ov:/root/.cache/ov,$CACHE_NFS/pip:/root/.cache/pip,$CACHE_NFS/glcache:/root/.cache/nvidia/GLCache,$CACHE_NFS/computecache:/root/.nv/ComputeCache,$CACHE_NFS/omni_logs:/root/.nvidia-omniverse/logs,$CACHE_NFS/carb_logs:/isaac-sim/kit/logs/Kit/Isaac-Sim,$CACHE_NFS/data:/root/.local/share/ov/data,$CACHE_NFS/documents:/root/Documents"
if [ -d "$GRASPGENX_NFS" ]; then
  CONTAINER_MOUNTS="$CONTAINER_MOUNTS,$GRASPGENX_NFS:/graspgenx"
fi
if [ -d "$CUROBO_ASSETS_NFS" ]; then
  CONTAINER_MOUNTS="$CONTAINER_MOUNTS,$CUROBO_ASSETS_NFS:/curobo_assets"
fi

echo "Rendering DEXTRAH star-kitting scene"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"
echo "ROBOT=$ROBOT"
echo "GRASPGENX_NFS=$GRASPGENX_NFS"
echo "CUROBO_ASSETS_NFS=$CUROBO_ASSETS_NFS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts="$CONTAINER_MOUNTS" \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc "
    set -euxo pipefail
    export SITE='/envs/$ENV_NAME/site'
    export PYTHONPATH=\"\$SITE:/code:/fabrics/src\"
    for d in /IsaacLab/source/*; do
      if [ -d \"\$d\" ]; then
        export PYTHONPATH=\"\$d:\$PYTHONPATH\"
      fi
    done
    mkdir -p /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default
    cd /code
    /isaac-sim/python.sh dextrah_lab/scene_scripts/render_star_kitting_env.py \
      --headless \
      --enable_cameras \
      --device cuda:0 \
      --output_dir /results/star_kitting_env/$RUN_NAME \
      --width \"${WIDTH:-1280}\" \
      --height \"${HEIGHT:-720}\" \
      --fps \"${FPS:-12}\" \
      --video_seconds \"${VIDEO_SECONDS:-3.0}\" \
      --sim_steps_per_frame \"${SIM_STEPS_PER_FRAME:-2}\" \
      --settle_steps \"${SETTLE_STEPS:-30}\" \
      --physics_device \"${PHYSICS_DEVICE:-cuda:0}\" \
      --robot \"$ROBOT\" \
      --graspgenx_root /graspgenx \
      --curobo_assets_root /curobo_assets \
      --seed \"${SEED:-23}\" \
      --star_outer_radius \"${STAR_OUTER_RADIUS:-0.092}\" \
      --star_inner_radius \"${STAR_INNER_RADIUS:-0.042}\" \
      --star_thickness \"${STAR_THICKNESS:-0.034}\" \
      --fixture_size_x \"${FIXTURE_SIZE_X:-0.33}\" \
      --fixture_size_y \"${FIXTURE_SIZE_Y:-0.33}\" \
      --fixture_thickness \"${FIXTURE_THICKNESS:-0.052}\" \
      --fixture_clearance \"${FIXTURE_CLEARANCE:-0.012}\" \
      --star_start_yaw_deg \"${STAR_START_YAW_DEG:--24.0}\" \
      --fixture_yaw_deg \"${FIXTURE_YAW_DEG:-18.0}\" \
      --view \"${VIEW:-overview}\" \
      --dynamic_star \
      \${STATIC_STAR:+--static_star} \
      \${CAPTURE_VIDEO:+--capture_video}
  "

echo "Done: $OUT_DIR"
