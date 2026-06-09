#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_clutter_bin
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/clutter_bin_%j.out

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
RUN_NAME="${RUN_NAME:-clutter_bin_${SLURM_JOB_ID:-manual}}"
OUT_DIR="$RESULTS_NFS/clutter_bin_env/$RUN_NAME"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site"
  exit 2
fi

mkdir -p \
  "$OUT_DIR" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

echo "Rendering DEXTRAH clutter-bin scene"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
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
    /isaac-sim/python.sh dextrah_lab/scene_scripts/render_clutter_bin_env.py \
      --headless \
      --enable_cameras \
      --device cuda:0 \
      --output_dir /results/clutter_bin_env/$RUN_NAME \
      --width \"${WIDTH:-1280}\" \
      --height \"${HEIGHT:-720}\" \
      --fps \"${FPS:-12}\" \
      --video_seconds \"${VIDEO_SECONDS:-3.0}\" \
      --sim_steps_per_frame \"${SIM_STEPS_PER_FRAME:-2}\" \
      --settle_steps \"${SETTLE_STEPS:-300}\" \
      --physics_device \"${PHYSICS_DEVICE:-cuda:0}\" \
      --contact_offset \"${CONTACT_OFFSET:-0.004}\" \
      --rest_offset \"${REST_OFFSET:-0.0}\" \
      --solver_position_iterations \"${SOLVER_POSITION_ITERATIONS:-12}\" \
      --solver_velocity_iterations \"${SOLVER_VELOCITY_ITERATIONS:-2}\" \
      --max_depenetration_velocity \"${MAX_DEPENETRATION_VELOCITY:-3.0}\" \
      --sphere_static_friction \"${SPHERE_STATIC_FRICTION:-1.2}\" \
      --sphere_dynamic_friction \"${SPHERE_DYNAMIC_FRICTION:-0.9}\" \
      --sphere_linear_damping \"${SPHERE_LINEAR_DAMPING:-0.12}\" \
      --sphere_angular_damping \"${SPHERE_ANGULAR_DAMPING:-0.65}\" \
      --sphere_sleep_threshold \"${SPHERE_SLEEP_THRESHOLD:-0.03}\" \
      --sphere_stabilization_threshold \"${SPHERE_STABILIZATION_THRESHOLD:-0.01}\" \
      --seed \"${SEED:-17}\" \
      --bin_l \"${BIN_L:-0.48}\" \
      --gripper_open_width \"${GRIPPER_OPEN_WIDTH:-0.09}\" \
      --clutter_shape \"${CLUTTER_SHAPE:-sphere}\" \
      --dynamic_sphere_grid \"${DYNAMIC_SPHERE_GRID:-3}\" \
      --dynamic_sphere_layers \"${DYNAMIC_SPHERE_LAYERS:-2}\" \
      --dynamic_sphere_count \"${DYNAMIC_SPHERE_COUNT:-0}\" \
      --view \"${VIEW:-overview}\" \
      --dynamic_clutter \
      \${STATIC_CLUTTER:+--static_clutter} \
      \${CAPTURE_VIDEO:+--capture_video}
  "

echo "Done: $OUT_DIR"
