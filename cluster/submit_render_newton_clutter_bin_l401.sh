#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-l401}"
NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
REMOTE_CODE_DIR="${REMOTE_CODE_DIR:-$NFS_ROOT/src/DEXTRAH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE="$REMOTE" NFS_ROOT="$NFS_ROOT" REMOTE_CODE_DIR="$REMOTE_CODE_DIR" \
  "$SCRIPT_DIR/sync_to_a1001.sh"

export_arg="ALL"
for name in \
  RUN_NAME WIDTH HEIGHT FPS VIDEO_SECONDS PHYSICS_DT DEVICE SEED BIN_L \
  GRIPPER_OPEN_WIDTH SPHERE_COUNT SPHERE_GRID DROP_HEIGHT SOLVER_ITERATIONS \
  SOLVER_LS_ITERATIONS COLLIDE_SUBSTEPS CONTACT_MAX NO_ENCODE INSTALL_GL_RUNTIME; do
  if [ -n "${!name+x}" ]; then
    export_arg="$export_arg,$name=${!name}"
  fi
done

ssh "$REMOTE" "bash -lc 'mkdir -p \"$NFS_ROOT/slurm_logs/dextrah\" \"$NFS_ROOT/results/dextrah/newton_clutter_bin\" && cd \"$REMOTE_CODE_DIR\" && sbatch --parsable --export=\"$export_arg\" cluster/sbatch_render_newton_clutter_bin.sh'"
