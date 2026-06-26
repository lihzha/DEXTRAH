#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_train_yam_pickplace_rgb_dp_1gpu.sh}"

MANIFEST="${MANIFEST:?Set MANIFEST to the YAM RGB policy manifest.json path.}"
RUN_NAME="${RUN_NAME:-yam_pickplace_rgb_dp_long_$(date -u +%Y%m%dT%H%M%SZ)}"
INIT_CHECKPOINT="${INIT_CHECKPOINT:-}"
TARGET_TRAIN_STEPS="${TARGET_TRAIN_STEPS:-2000000}"
NUM_EPOCHS="${NUM_EPOCHS:-50}"
MAX_TRAIN_STEPS="${MAX_TRAIN_STEPS:-$TARGET_TRAIN_STEPS}"
TOPK_CHECKPOINTS="${TOPK_CHECKPOINTS:-50}"
MAX_SUBMISSIONS="${MAX_SUBMISSIONS:-128}"
POLL_SECONDS="${POLL_SECONDS:-60}"
JOB_NAME="${JOB_NAME:-yam_rgb_dp_train}"
CODE_COMMIT="${CODE_COMMIT:-}"

if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
if [ ! -f "$WRAPPER" ]; then
  echo "Missing wrapper: $WRAPPER" >&2
  exit 2
fi

RUN_ROOT_HOST="$RESULTS_NFS/dp_bc/yam_pickplace_rgb/$RUN_NAME"
TRAIN_DIR_HOST="$RUN_ROOT_HOST/official_dp_train"
CHECKPOINT_HOST="$TRAIN_DIR_HOST/checkpoints/latest.ckpt"
SUBMIT_DIR="$RUN_ROOT_HOST/submitter"
mkdir -p "$SUBMIT_DIR" "$LOG_DIR"
SUBMITTED_TSV="$SUBMIT_DIR/submitted_train_jobs.tsv"
CONFIG_JSON="$SUBMIT_DIR/long_train_submitter_config.json"
touch "$SUBMITTED_TSV"

python3 - "$CONFIG_JSON" <<PY
import json
from pathlib import Path
payload = {
    "code_commit": "$CODE_COMMIT",
    "code_nfs": "$CODE_NFS",
    "manifest": "$MANIFEST",
    "run_name": "$RUN_NAME",
    "run_root": "$RUN_ROOT_HOST",
    "train_dir": "$TRAIN_DIR_HOST",
    "init_checkpoint": "$INIT_CHECKPOINT" or None,
    "target_train_steps": int("$TARGET_TRAIN_STEPS"),
    "max_train_steps": int("$MAX_TRAIN_STEPS"),
    "num_epochs": int("$NUM_EPOCHS"),
    "topk_checkpoints": int("$TOPK_CHECKPOINTS"),
    "wrapper": "$WRAPPER",
    "max_submissions": int("$MAX_SUBMISSIONS"),
    "poll_seconds": int("$POLL_SECONDS"),
}
Path("$CONFIG_JSON").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "long_train_submitter_config_written", "path": "$CONFIG_JSON"}))
PY

last_step() {
  python3 - "$TRAIN_DIR_HOST/logs.json.txt" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
best = -1
if path.is_file():
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "global_step" in row:
            best = max(best, int(row["global_step"]))
print(best)
PY
}

wait_for_job() {
  local job_id="$1"
  while squeue -h -j "$job_id" >/dev/null 2>&1 && [ -n "$(squeue -h -j "$job_id" 2>/dev/null)" ]; do
    sleep "$POLL_SECONDS"
  done
}

job_state() {
  local job_id="$1"
  sacct -n -X -j "$job_id" --format=State -P 2>/dev/null | head -1 | tr -d ' ' || true
}

log_has_failure() {
  local job_id="$1"
  local log="$LOG_DIR/train_yam_rgb_dp_${job_id}.out"
  [ -f "$log" ] || return 1
  grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError|YAM RGB DP Training Done" "$log" >/dev/null || return 1
  if grep -E "Traceback|RuntimeError:|ModuleNotFoundError|ImportError" "$log" >/dev/null; then
    return 0
  fi
  return 1
}

submission=0
while [ "$submission" -lt "$MAX_SUBMISSIONS" ]; do
  current_step="$(last_step)"
  if [ "$current_step" -ge "$((TARGET_TRAIN_STEPS - 1))" ]; then
    echo "target_reached step=$current_step target=$TARGET_TRAIN_STEPS"
    exit 0
  fi

  resume="false"
  init_arg="$INIT_CHECKPOINT"
  if [ -s "$CHECKPOINT_HOST" ]; then
    resume="true"
    init_arg=""
  fi
  if [ "$submission" -gt 0 ] && [ ! -s "$CHECKPOINT_HOST" ]; then
    echo "Cannot resume: missing checkpoint $CHECKPOINT_HOST" >&2
    exit 1
  fi

  job_id="$(
    sbatch --parsable \
      --job-name="$JOB_NAME" \
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",RUN_NAME="$RUN_NAME",MANIFEST="$MANIFEST",INIT_CHECKPOINT="$init_arg",RESUME="$resume",NUM_EPOCHS="$NUM_EPOCHS",MAX_TRAIN_STEPS="$MAX_TRAIN_STEPS",TOPK_CHECKPOINTS="$TOPK_CHECKPOINTS" \
      "$WRAPPER"
  )"
  submission=$((submission + 1))
  printf "%s\t%s\t%s\t%s\t%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$submission" "$job_id" "$resume" "$current_step" | tee -a "$SUBMITTED_TSV"
  wait_for_job "$job_id"

  state="$(job_state "$job_id")"
  new_step="$(last_step)"
  echo "job_done job_id=$job_id state=${state:-unknown} previous_step=$current_step new_step=$new_step"
  if log_has_failure "$job_id"; then
    echo "Detected failure pattern in $LOG_DIR/train_yam_rgb_dp_${job_id}.out" >&2
    exit 1
  fi
  if [ "$new_step" -le "$current_step" ] && [ "${state%%+*}" != "TIMEOUT" ]; then
    echo "Training made no progress and did not time out; stopping." >&2
    exit 1
  fi
done

echo "Reached MAX_SUBMISSIONS=$MAX_SUBMISSIONS before TARGET_TRAIN_STEPS=$TARGET_TRAIN_STEPS" >&2
exit 1
