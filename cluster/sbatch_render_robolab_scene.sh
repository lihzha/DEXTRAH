#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_robolab_scene
#SBATCH --partition=batch
#SBATCH --time=0-00:45:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/robolab_scene_%j.out

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
RUN_NAME="${RUN_NAME:-robolab_scene_${SLURM_JOB_ID:-manual}}"
OUT_DIR="$RESULTS_NFS/robolab_scene/$RUN_NAME"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi

CONTAINER_MOUNTS="/dev/shm:/dev/shm,$CODE_NFS:/code,$FABRICS_NFS:/fabrics,$ISAACLAB_NFS:/IsaacLab,$ENV_ROOT:/envs,$RESULTS_NFS:/results,$CACHE_NFS/kit:/isaac-sim/kit/cache,$CACHE_NFS/ov:/root/.cache/ov,$CACHE_NFS/pip:/root/.cache/pip,$CACHE_NFS/glcache:/root/.cache/nvidia/GLCache,$CACHE_NFS/computecache:/root/.nv/ComputeCache,$CACHE_NFS/omni_logs:/root/.nvidia-omniverse/logs,$CACHE_NFS/carb_logs:/isaac-sim/kit/logs/Kit/Isaac-Sim,$CACHE_NFS/data:/root/.local/share/ov/data,$CACHE_NFS/documents:/root/Documents"
ROBOLAB_ARGS=""
ROBOLAB_PYTHONPATH=""
if [ -d "$ROBOLAB_NFS" ]; then
  CONTAINER_MOUNTS="$CONTAINER_MOUNTS,$ROBOLAB_NFS:/robolab"
  ROBOLAB_ARGS="--robolab_root /robolab"
  ROBOLAB_PYTHONPATH=":/robolab"
fi
if [ -n "${ROBOLAB_SCENE_DIR:-}" ]; then
  ROBOLAB_ARGS="$ROBOLAB_ARGS --robolab_scene_dir \"$ROBOLAB_SCENE_DIR\""
fi
case "${ENCODE_VIDEO:-1}" in
  0|false|False|FALSE|no|No|NO)
    ENCODE_VIDEO_ARG="--no-encode_video"
    ;;
  *)
    ENCODE_VIDEO_ARG="--encode_video"
    ;;
esac

mkdir -p \
  "$OUT_DIR" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

echo "Rendering RoboLab scene through DEXTRAH"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "RUN_NAME=$RUN_NAME"
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"
echo "ROBOLAB_NFS=$ROBOLAB_NFS"
echo "ROBOLAB_SCENE=${ROBOLAB_SCENE:-banana_bowl.usda}"

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
    export PYTHONPATH=\"\$SITE:/code:/fabrics/src$ROBOLAB_PYTHONPATH\"
    for d in /IsaacLab/source/*; do
      if [ -d \"\$d\" ]; then
        export PYTHONPATH=\"\$d:\$PYTHONPATH\"
      fi
    done
    mkdir -p /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default
    cd /code
    /isaac-sim/python.sh dextrah_lab/scene_scripts/render_robolab_scene.py \
      --headless \
      --enable_cameras \
      --device cuda:0 \
      --scene \"${ROBOLAB_SCENE:-banana_bowl.usda}\" \
      $ROBOLAB_ARGS \
      --output_dir /results/robolab_scene/$RUN_NAME \
      --width \"${WIDTH:-960}\" \
      --height \"${HEIGHT:-540}\" \
      --fps \"${FPS:-12}\" \
      --video_seconds \"${VIDEO_SECONDS:-6.0}\" \
      --sim_steps_per_frame \"${SIM_STEPS_PER_FRAME:-1}\" \
      --sim_dt \"${SIM_DT:-0.008333333333333333}\" \
      --settle_steps \"${SETTLE_STEPS:-12}\" \
      --warmup_frames \"${WARMUP_FRAMES:-8}\" \
      --rt_subframes \"${RT_SUBFRAMES:-4}\" \
      --physics_device \"${PHYSICS_DEVICE:-cuda:0}\" \
      --capture_backend \"${CAPTURE_BACKEND:-viewport}\" \
      --orbit_elevation_deg \"${ORBIT_ELEVATION_DEG:-45}\" \
      --orbit_start_deg \"${ORBIT_START_DEG:-35}\" \
      --target_source \"${TARGET_SOURCE:-table}\" \
      --target_z_offset \"${TARGET_Z_OFFSET:-0.05}\" \
      --scene_scale \"${SCENE_SCALE:-1.0}\" \
      --dome_intensity \"${DOME_INTENSITY:-750}\" \
      --sun_intensity \"${SUN_INTENSITY:-1800}\" \
      --robot \"${ROBOT:-none}\" \
      --seed \"${SEED:-17}\" \
      \${ORBIT_RADIUS:+--orbit_radius \"\$ORBIT_RADIUS\"} \
      \${ORBIT_HEIGHT:+--orbit_height \"\$ORBIT_HEIGHT\"} \
      \${ORBIT_TARGET:+--orbit_target \"\$ORBIT_TARGET\"} \
      \${RANDOMIZE_LIGHTING:+--randomize_lighting} \
      $ENCODE_VIDEO_ARG
  "

echo "Done: $OUT_DIR"
