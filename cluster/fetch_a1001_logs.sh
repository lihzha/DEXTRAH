#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-a1001}"
NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
LOCAL_LOG_DIR="${LOCAL_LOG_DIR:-cluster_logs/a1001}"

mkdir -p "$LOCAL_LOG_DIR"
rsync -az "$REMOTE:$NFS_ROOT/slurm_logs/dextrah/" "$LOCAL_LOG_DIR/slurm_logs/"
rsync -az --exclude='*.pth' --exclude='events.out.tfevents*' "$REMOTE:$NFS_ROOT/results/dextrah/logs/" "$LOCAL_LOG_DIR/result_logs/" 2>/dev/null || true

echo "Fetched DEXTRAH logs into $LOCAL_LOG_DIR"
