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
SLURM_QUERY_FAILURE_RETRIES="${SLURM_QUERY_FAILURE_RETRIES:-5}"
SBATCH_RETRIES="${SBATCH_RETRIES:-5}"
SBATCH_RETRY_SECONDS="${SBATCH_RETRY_SECONDS:-60}"
ADOPT_JOB_ID="${ADOPT_JOB_ID:-}"

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
    "adopt_job_id": "$ADOPT_JOB_ID" or None,
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
  local failures=0
  local empty_results=0
  local out rc
  while true; do
    set +e
    out="$(squeue -h -j "$job_id" 2>&1)"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
      failures=$((failures + 1))
      echo "squeue_query_failed job_id=$job_id attempt=$failures rc=$rc output=$out" >&2
      if [ "$failures" -ge "$SLURM_QUERY_FAILURE_RETRIES" ]; then
        return "$rc"
      fi
      sleep "$POLL_SECONDS"
      continue
    fi
    failures=0
    if [ -z "$out" ]; then
      empty_results=$((empty_results + 1))
      if [ "$empty_results" -ge 2 ]; then
        break
      fi
    else
      empty_results=0
    fi
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

submit_train_job() {
  local resume="$1"
  local init_arg="$2"
  local attempt=1
  local out rc err
  while true; do
    err="$SUBMIT_DIR/sbatch_attempt_${attempt}.err"
    set +e
    out="$(
      sbatch --parsable \
        --job-name="$JOB_NAME" \
        --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",RUN_NAME="$RUN_NAME",MANIFEST="$MANIFEST",INIT_CHECKPOINT="$init_arg",RESUME="$resume",NUM_EPOCHS="$NUM_EPOCHS",MAX_TRAIN_STEPS="$MAX_TRAIN_STEPS",TOPK_CHECKPOINTS="$TOPK_CHECKPOINTS" \
        "$WRAPPER" \
        2>"$err"
    )"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
      if [ -s "$err" ]; then
        cat "$err" >&2
      fi
      printf "%s\n" "$out"
      return 0
    fi
    echo "sbatch_failed attempt=$attempt rc=$rc stdout=$out stderr=$(cat "$err" 2>/dev/null || true)" >&2
    if [ "$attempt" -ge "$SBATCH_RETRIES" ]; then
      return "$rc"
    fi
    attempt=$((attempt + 1))
    sleep "$SBATCH_RETRY_SECONDS"
  done
}

submission=0
if [ -n "$ADOPT_JOB_ID" ]; then
  current_step="$(last_step)"
  submission=$((submission + 1))
  printf "%s\t%s\t%s\t%s\t%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$submission" "$ADOPT_JOB_ID" "adopted" "$current_step" | tee -a "$SUBMITTED_TSV"
  wait_for_job "$ADOPT_JOB_ID"
  state="$(job_state "$ADOPT_JOB_ID")"
  new_step="$(last_step)"
  echo "adopted_job_done job_id=$ADOPT_JOB_ID state=${state:-unknown} previous_step=$current_step new_step=$new_step"
  if log_has_failure "$ADOPT_JOB_ID"; then
    echo "Detected failure pattern in $LOG_DIR/train_yam_rgb_dp_${ADOPT_JOB_ID}.out" >&2
    exit 1
  fi
  if [ "$new_step" -le "$current_step" ] && [ "${state%%+*}" != "TIMEOUT" ]; then
    echo "Adopted training job made no progress and did not time out; stopping." >&2
    exit 1
  fi
fi

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

  job_id="$(submit_train_job "$resume" "$init_arg")"
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
