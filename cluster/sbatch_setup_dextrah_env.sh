#!/bin/bash
#SBATCH --nodes=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --partition=cpu_short
#SBATCH --time=0-04:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --job-name=dextrah_setup_env
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/setup_env_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
EXTRA_SITE_NFS="$ENV_ROOT/$ENV_NAME/site"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
RESET_ENV="${RESET_ENV:-1}"

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE"
  echo "Submit cluster/sbatch_import_isaaclab_sqsh.sh first."
  exit 2
fi

if [ "$RESET_ENV" = "1" ]; then
  rm -rf "$EXTRA_SITE_NFS"
fi

mkdir -p \
  "$EXTRA_SITE_NFS" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

echo "Setting up DEXTRAH NFS Python target: $EXTRA_SITE_NFS"
echo "Using image: $IMAGE"

srun \
  --container-image="$IMAGE" \
  --container-mounts="$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,PIP_NO_CACHE_DIR=0 \
  bash -lc "
    set -euxo pipefail
    SITE='/envs/$ENV_NAME/site'
    export PYTHONPATH=\"\$SITE:/code:/fabrics/src\"
    for d in /IsaacLab/source/*; do
      if [ -d \"\$d\" ]; then
        export PYTHONPATH=\"\$d:\$PYTHONPATH\"
      fi
    done

    /isaac-sim/python.sh -m pip install --target \"\$SITE\" --no-deps \
      'urdfpy==0.0.22'

    URDFPY_DIR=\$(find \"\$SITE\" -maxdepth 2 -type d -name urdfpy | head -n 1)
    test -n \"\$URDFPY_DIR\"

    sed -i 's|value = np.asanyarray(value).astype(np.float)|value = np.asanyarray(value).astype(float)|g' \"\$URDFPY_DIR/urdf.py\"

    cd /code
    /isaac-sim/python.sh - <<'PY'
import sys
import torch
from isaaclab.app import AppLauncher
import fabrics_sim
import dextrah_lab
import urdfpy
import networkx
print('python', sys.version)
print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available())
print('AppLauncher', AppLauncher)
print('fabrics_sim', fabrics_sim.__file__)
print('dextrah_lab', dextrah_lab.__file__)
print('urdfpy', urdfpy.__file__)
print('networkx', networkx.__file__)
PY
  "

echo "DextrAH Python target ready: $EXTRA_SITE_NFS"
