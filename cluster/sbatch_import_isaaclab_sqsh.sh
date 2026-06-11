#!/bin/bash
#SBATCH --nodes=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --partition=cpu_short
#SBATCH --time=0-04:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --job-name=dextrah_import_isaac
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/import_isaaclab_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
IMAGE_DIR="${IMAGE_DIR:-$NFS_ROOT/cache}"
BASE_IMAGE="${BASE_IMAGE:-nvcr.io#nvidia/isaac-lab:2.2.0}"
BASE_SQSH="${BASE_SQSH:-$IMAGE_DIR/isaac_lab_2.2.0.sqsh}"

mkdir -p "$IMAGE_DIR" "$NFS_ROOT/slurm_logs/dextrah"
rm -f "$BASE_SQSH"

echo "Importing docker://$BASE_IMAGE -> $BASE_SQSH"
echo "hostname=$(hostname)"
enroot import -o "$BASE_SQSH" "docker://$BASE_IMAGE"
ls -lh "$BASE_SQSH"
