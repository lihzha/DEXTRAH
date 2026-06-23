#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_yam_cam_viz
#SBATCH --partition=batch
#SBATCH --time=0-00:30:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bimanual_yam_cam_viz_%j.out

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
RUN_NAME="${RUN_NAME:-bimanual_yam_molmoact2_camera_viz_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR_HOST="$RESULTS_NFS/bimanual_yam_molmoact2_camera_viz/$RUN_NAME"
RUN_DIR_CONTAINER="/results/bimanual_yam_molmoact2_camera_viz/$RUN_NAME"
TASK="${TASK:-Dextrah-Bimanual-YAM-Cube-Grasp}"
FRAMES="${FRAMES:-48}"
FPS="${FPS:-12}"
SIM_STEPS_PER_FRAME="${SIM_STEPS_PER_FRAME:-1}"
SEED="${SEED:-42}"
DISABLE_FABRIC="${DISABLE_FABRIC:-True}"
VIDEO_CRF="${VIDEO_CRF:-18}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

if [ "$TASK" != "Dextrah-Bimanual-YAM-Cube-Grasp" ]; then
  echo "This wrapper is only for TASK=Dextrah-Bimanual-YAM-Cube-Grasp" >&2
  exit 2
fi
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

export TASK RUN_NAME RUN_DIR_CONTAINER FRAMES FPS SIM_STEPS_PER_FRAME SEED DISABLE_FABRIC VIDEO_CRF
export PREPARE_YAM_ASSETS CODE_COMMIT ENV_NAME

echo "Rendering bimanual YAM MolmoAct2 camera visualization"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "FABRICS_NFS=$FABRICS_NFS"
echo "ISAACLAB_NFS=$ISAACLAB_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "TASK=$TASK"
echo "RUN_NAME=$RUN_NAME"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "FRAMES=$FRAMES"
echo "FPS=$FPS"
echo "SIM_STEPS_PER_FRAME=$SIM_STEPS_PER_FRAME"
echo "DISABLE_FABRIC=$DISABLE_FABRIC"
echo "PREPARE_YAM_ASSETS=$PREPARE_YAM_ASSETS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
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
    mkdir -p "$RUN_DIR_CONTAINER" /results/logs /isaac-sim/kit/data/Kit/Isaac-Sim/5.0/pip3-envs/default

    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true
    nvidia-smi || true

    YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd
    if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
      /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless --converter mjcf
    fi
    test -s "$YAM_USD"

    VIZ_ARGS=(
      dextrah_lab/scene_scripts/render_bimanual_yam_molmoact2_cameras.py
      --headless
      --enable_cameras
      --device cuda:0
      --task "$TASK"
      --num_envs 1
      --seed "$SEED"
      --output_dir "$RUN_DIR_CONTAINER"
      --frames "$FRAMES"
      --fps "$FPS"
      --sim_steps_per_frame "$SIM_STEPS_PER_FRAME"
      --video_crf "$VIDEO_CRF"
    )
    if [ "$DISABLE_FABRIC" = "True" ]; then
      VIZ_ARGS+=(--disable_fabric)
    fi

    printf "viz_command="
    printf "%q " /isaac-sim/python.sh "${VIZ_ARGS[@]}"
    printf "\n"
    /isaac-sim/python.sh "${VIZ_ARGS[@]}"
  '

if [ ! -s "$RUN_DIR_HOST/metadata.json" ]; then
  echo "Missing metadata: $RUN_DIR_HOST/metadata.json" >&2
  exit 1
fi
if [ ! -s "$RUN_DIR_HOST/bimanual_yam_molmoact2_cameras_composite.mp4" ]; then
  echo "Missing composite video: $RUN_DIR_HOST/bimanual_yam_molmoact2_cameras_composite.mp4" >&2
  exit 1
fi

echo "Bimanual YAM MolmoAct2 camera visualization done: $RUN_DIR_HOST"
