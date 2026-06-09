#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-l401}"
NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
REMOTE_CODE_DIR="${REMOTE_CODE_DIR:-$NFS_ROOT/src/DEXTRAH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE="$REMOTE" NFS_ROOT="$NFS_ROOT" REMOTE_CODE_DIR="$REMOTE_CODE_DIR" \
  "$SCRIPT_DIR/sync_to_a1001.sh"

ssh "$REMOTE" "bash -lc 'mkdir -p \"$NFS_ROOT/slurm_logs/dextrah\" \"$NFS_ROOT/results/dextrah/clutter_bin_env\" && sbatch \"$REMOTE_CODE_DIR/cluster/sbatch_render_clutter_bin_env.sh\"'"
