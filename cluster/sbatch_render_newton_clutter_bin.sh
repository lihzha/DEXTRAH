#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_newton_bin
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/newton_bin_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/graspgenx_ngc2503_base.sqsh}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
VENV_NAME="${VENV_NAME:-graspgenx-py312}"
NEWTON_SITE="${NEWTON_SITE:-/envs/dextrah-newton-render-site}"
NEWTON_SITE_NFS="${NEWTON_SITE_NFS:-$ENV_NFS/dextrah-newton-render-site}"
PIP_CACHE_NFS="${PIP_CACHE_NFS:-$NFS_ROOT/cache/pip}"
GL_CACHE_NFS="${GL_CACHE_NFS:-$NFS_ROOT/cache/glcache}"
RUN_NAME="${RUN_NAME:-newton_clutter_bin_${SLURM_JOB_ID:-manual}}"
OUT_DIR="$RESULTS_NFS/newton_clutter_bin/$RUN_NAME"

if [ ! -f "$IMAGE" ]; then
  echo "Missing GraspGenX base image: $IMAGE"
  exit 2
fi
if [ ! -x "$ENV_NFS/$VENV_NAME/bin/python" ]; then
  echo "Missing GraspGenX venv python: $ENV_NFS/$VENV_NAME/bin/python"
  exit 2
fi

mkdir -p "$OUT_DIR" "$NFS_ROOT/slurm_logs/dextrah" "$NEWTON_SITE_NFS" "$PIP_CACHE_NFS" "$GL_CACHE_NFS"

echo "Rendering DEXTRAH Newton/OpenGL clutter-bin scene"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "VENV=$ENV_NFS/$VENV_NAME"
echo "NEWTON_SITE_NFS=$NEWTON_SITE_NFS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$RESULTS_NFS":/results,"$ENV_NFS":/envs,"$PIP_CACHE_NFS":/root/.cache/pip,"$GL_CACHE_NFS":/root/.cache/nvidia/GLCache \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1,PYOPENGL_PLATFORM=egl,PYGLET_HEADLESS=true,EGL_PLATFORM=surfaceless,__GLX_VENDOR_LIBRARY_NAME=nvidia,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1 \
  bash -lc "
    set -euxo pipefail
    export VIRTUAL_ENV=/envs/$VENV_NAME
    export PATH=/envs/$VENV_NAME/bin:\$PATH
    export PYTHONPATH=$NEWTON_SITE:/code:\${PYTHONPATH:-}
    mkdir -p '$NEWTON_SITE'
    cd /code

    set +e
    python - <<'PY'
import importlib.util
missing = [name for name in ('newton', 'warp') if importlib.util.find_spec(name) is None]
print('missing_newton_runtime', missing)
raise SystemExit(0 if not missing else 10)
PY
    status=\$?
    set -e
    if [ \"\$status\" = \"10\" ]; then
      python -m pip install --target '$NEWTON_SITE' --upgrade 'newton[sim]'
    elif [ \"\$status\" != \"0\" ]; then
      exit \"\$status\"
    fi

    python - <<'PY'
import sys
import newton, warp, pyrender, trimesh
print('python', sys.version)
print('newton', getattr(newton, '__version__', 'unknown'), newton.__file__)
print('warp', getattr(warp, '__version__', 'unknown'), warp.__file__)
print('pyrender', pyrender.__file__)
print('trimesh', trimesh.__version__)
PY

    python dextrah_lab/scene_scripts/render_newton_clutter_bin.py \
      --output_dir /results/newton_clutter_bin/$RUN_NAME \
      --width \"${WIDTH:-960}\" \
      --height \"${HEIGHT:-540}\" \
      --fps \"${FPS:-24}\" \
      --video_seconds \"${VIDEO_SECONDS:-5.0}\" \
      --physics_dt \"${PHYSICS_DT:-0.002}\" \
      --device \"${DEVICE:-cuda:0}\" \
      --seed \"${SEED:-17}\" \
      --bin_l \"${BIN_L:-0.48}\" \
      --gripper_open_width \"${GRIPPER_OPEN_WIDTH:-0.09}\" \
      --sphere_count \"${SPHERE_COUNT:-64}\" \
      --sphere_grid \"${SPHERE_GRID:-4}\" \
      --drop_height \"${DROP_HEIGHT:-0.34}\" \
      --solver_iterations \"${SOLVER_ITERATIONS:-80}\" \
      --solver_ls_iterations \"${SOLVER_LS_ITERATIONS:-40}\" \
      --collide_substeps \"${COLLIDE_SUBSTEPS:-4}\" \
      --contact_max \"${CONTACT_MAX:-262144}\" \
      \${NO_ENCODE:+--no_encode}
  "

echo "Done: $OUT_DIR"
