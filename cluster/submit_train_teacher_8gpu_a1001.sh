#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-a1001}"
NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
REMOTE_CODE_DIR="${REMOTE_CODE_DIR:-$NFS_ROOT/src/DEXTRAH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/sync_to_a1001.sh"

ssh "$REMOTE" "sbatch '$REMOTE_CODE_DIR/cluster/sbatch_train_teacher_8gpu.sh'"
