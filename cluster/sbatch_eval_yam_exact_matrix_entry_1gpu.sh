#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_exact_eval
#SBATCH --partition=batch
#SBATCH --time=00:30:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_yam_exact_matrix_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
EVAL_WRAPPER="${EVAL_WRAPPER:-$CODE_NFS/cluster/sbatch_eval_yam_pickplace_rgb_dp_policy_1gpu.sh}"
MATRIX_TSV="${MATRIX_TSV:?Set MATRIX_TSV.}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT.}"
CODE_COMMIT="${CODE_COMMIT:-}"
ENTRY_INDEX="${ENTRY_INDEX:-${SLURM_ARRAY_TASK_ID:?Set ENTRY_INDEX or submit as an array.}}"
NUM_STEPS="${NUM_STEPS:-1200}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-1}"

if [ ! -f "$MATRIX_TSV" ] || [ ! -f "$EVAL_WRAPPER" ]; then
  echo "Missing matrix or eval wrapper: $MATRIX_TSV $EVAL_WRAPPER" >&2
  exit 2
fi
if [ -n "$CODE_COMMIT" ] && [ "$(git -C "$CODE_NFS" rev-parse HEAD)" != "$CODE_COMMIT" ]; then
  echo "CODE_COMMIT mismatch" >&2
  exit 2
fi

line="$(sed -n "$((ENTRY_INDEX + 2))p" "$MATRIX_TSV")"
if [ -z "$line" ]; then
  echo "Missing matrix entry $ENTRY_INDEX" >&2
  exit 2
fi
IFS=$'\t' read -r matrix_index split source_index exact_policy_shard run_name capture_video <<<"$line"
if [ "$matrix_index" != "$ENTRY_INDEX" ]; then
  echo "Matrix index mismatch: expected $ENTRY_INDEX got $matrix_index" >&2
  exit 2
fi

exec env \
  CODE_NFS="$CODE_NFS" \
  RESULTS_NFS="$RESULTS_NFS" \
  CODE_COMMIT="$CODE_COMMIT" \
  RUN_NAME="$run_name" \
  CONTROL_MODE=policy \
  CHECKPOINT="$CHECKPOINT" \
  EXACT_POLICY_SHARD="$exact_policy_shard" \
  NUM_EPISODES=1 \
  NUM_STEPS="$NUM_STEPS" \
  ACTION_CHUNK_STEPS="$ACTION_CHUNK_STEPS" \
  DISABLE_FAILURE_TERMINATIONS=True \
  DISABLE_SUCCESS_TERMINATION=True \
  STOP_ON_DONE=False \
  CAPTURE_VIDEO="$capture_video" \
  VIDEO_LENGTH="$NUM_STEPS" \
  DEBUG_OBS_INTERVAL=120 \
  DEBUG_OBS_MAX_FRAMES=12 \
  RENDERING_MODE=quality \
  HIDE_ROBOT_DEBUG_SITES=True \
  POLICY_SAMPLE_SEED="$((42000 + source_index))" \
  SEED="$((79000001 + source_index))" \
  bash "$EVAL_WRAPPER"
