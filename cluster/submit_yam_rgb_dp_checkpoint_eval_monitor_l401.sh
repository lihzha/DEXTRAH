#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
LOG_DIR="${LOG_DIR:-$NFS_ROOT/slurm_logs/dextrah}"
EVAL_WRAPPER="${EVAL_WRAPPER:-$CODE_NFS/cluster/sbatch_eval_yam_pickplace_rgb_dp_policy_1gpu.sh}"

TRAIN_RUN_NAME="${TRAIN_RUN_NAME:?Set TRAIN_RUN_NAME to the YAM RGB DP training run name.}"
TRAIN_DIR_HOST="${TRAIN_DIR_HOST:-$RESULTS_NFS/dp_bc/yam_pickplace_rgb/$TRAIN_RUN_NAME/official_dp_train}"
TRAIN_LOG_JSON="${TRAIN_LOG_JSON:-$TRAIN_DIR_HOST/logs.json.txt}"
CHECKPOINT_HOST="${CHECKPOINT_HOST:-$TRAIN_DIR_HOST/checkpoints/latest.ckpt}"
MONITOR_NAME="${MONITOR_NAME:-${TRAIN_RUN_NAME}_periodic_eval_$(date -u +%Y%m%dT%H%M%SZ)}"
MONITOR_DIR="${MONITOR_DIR:-$RESULTS_NFS/evals/$MONITOR_NAME}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$RESULTS_NFS/dp_bc/checkpoints/$TRAIN_RUN_NAME/periodic_eval_snapshots}"

EVAL_EVERY_STEPS="${EVAL_EVERY_STEPS:-100000}"
TARGET_TRAIN_STEPS="${TARGET_TRAIN_STEPS:-2000000}"
POLL_SECONDS="${POLL_SECONDS:-300}"
MAX_EVALS="${MAX_EVALS:-0}"
MAX_CONCURRENT_EVALS="${MAX_CONCURRENT_EVALS:-1}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yam_rgb_dp_eval}"
CODE_COMMIT="${CODE_COMMIT:-}"
CHECKPOINT_FRESH_AFTER_THRESHOLD="${CHECKPOINT_FRESH_AFTER_THRESHOLD:-True}"

NUM_EPISODES="${NUM_EPISODES:-1}"
NUM_STEPS="${NUM_STEPS:-4800}"
VIDEO_LENGTH="${VIDEO_LENGTH:-4800}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-8}"
DISABLE_FAILURE_TERMINATIONS="${DISABLE_FAILURE_TERMINATIONS:-True}"
DISABLE_SUCCESS_TERMINATION="${DISABLE_SUCCESS_TERMINATION:-True}"
STOP_ON_DONE="${STOP_ON_DONE:-False}"
STOP_ON_BIN_DROP_SUCCESS="${STOP_ON_BIN_DROP_SUCCESS:-False}"
DEBUG_OBS_INTERVAL="${DEBUG_OBS_INTERVAL:-120}"
DEBUG_OBS_MAX_FRAMES="${DEBUG_OBS_MAX_FRAMES:-120}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
CAPTURE_VIDEO="${CAPTURE_VIDEO:-True}"
YAM_DEFAULT_FINGER_QPOS="${YAM_DEFAULT_FINGER_QPOS:--0.0475}"
YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH="${YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH:-/results/yam_demos/yam_single_object_center_y_dynamic_500_20260625T165831Z/yam_objaverse_pool_manifest.json}"
YAM_POLICY_MAX_OBJECTS="${YAM_POLICY_MAX_OBJECTS:-120}"
YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS="${YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS:-False}"
YAM_POLICY_TABLE_TEXTURE_DIR="${YAM_POLICY_TABLE_TEXTURE_DIR:-/code/dextrah_lab/assets/textures/tabletop_wood_polyhaven}"
YAM_POLICY_DOME_LIGHT_TEXTURE_DIR="${YAM_POLICY_DOME_LIGHT_TEXTURE_DIR:-/home/lzha/code/RoboLab/assets/backgrounds/indoors}"

if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi
if [ ! -f "$EVAL_WRAPPER" ]; then
  echo "Missing eval wrapper: $EVAL_WRAPPER" >&2
  exit 2
fi
mkdir -p "$MONITOR_DIR" "$SNAPSHOT_DIR" "$LOG_DIR"
SUBMITTED_TSV="$MONITOR_DIR/submitted_periodic_evals.tsv"
CONFIG_JSON="$MONITOR_DIR/periodic_eval_monitor_config.json"
touch "$SUBMITTED_TSV"

python3 - "$CONFIG_JSON" <<PY
import json
from pathlib import Path
payload = {
    "code_commit": "$CODE_COMMIT",
    "code_nfs": "$CODE_NFS",
    "train_run_name": "$TRAIN_RUN_NAME",
    "train_dir": "$TRAIN_DIR_HOST",
    "train_log_json": "$TRAIN_LOG_JSON",
    "checkpoint": "$CHECKPOINT_HOST",
    "monitor_name": "$MONITOR_NAME",
    "monitor_dir": "$MONITOR_DIR",
    "snapshot_dir": "$SNAPSHOT_DIR",
    "eval_every_steps": int("$EVAL_EVERY_STEPS"),
    "target_train_steps": int("$TARGET_TRAIN_STEPS"),
    "checkpoint_fresh_after_threshold": "$CHECKPOINT_FRESH_AFTER_THRESHOLD",
    "num_episodes": int("$NUM_EPISODES"),
    "num_steps": int("$NUM_STEPS"),
    "video_length": int("$VIDEO_LENGTH"),
    "action_chunk_steps": int("$ACTION_CHUNK_STEPS"),
    "disable_failure_terminations": "$DISABLE_FAILURE_TERMINATIONS" == "True",
    "disable_success_termination": "$DISABLE_SUCCESS_TERMINATION" == "True",
    "stop_on_done": "$STOP_ON_DONE" == "True",
    "stop_on_bin_drop_success": "$STOP_ON_BIN_DROP_SUCCESS" == "True",
    "rendering_mode": "$RENDERING_MODE",
    "object_asset_manifest_path": "$YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH",
    "yam_policy_max_objects": int("$YAM_POLICY_MAX_OBJECTS"),
    "yam_policy_table_texture_dir": "$YAM_POLICY_TABLE_TEXTURE_DIR",
    "yam_policy_dome_light_texture_dir": "$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR",
}
Path("$CONFIG_JSON").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "periodic_eval_monitor_config_written", "path": "$CONFIG_JSON"}))
PY

last_step() {
  python3 - "$TRAIN_LOG_JSON" <<'PY'
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

active_eval_jobs() {
  squeue -h -u "${USER:-lzha}" -t PENDING,RUNNING,CONFIGURING,COMPLETING -o "%j" \
    | grep -c "^${JOB_NAME_PREFIX}" || true
}

stable_copy_checkpoint() {
  local src="$1"
  local dst="$2"
  local size1 size2 mtime1 mtime2 size3 mtime3 tmp
  [ -s "$src" ] || return 1
  size1="$(stat -c %s "$src")"
  mtime1="$(stat -c %Y "$src")"
  sleep 10
  size2="$(stat -c %s "$src")"
  mtime2="$(stat -c %Y "$src")"
  [ "$size1" = "$size2" ] && [ "$mtime1" = "$mtime2" ] || return 1
  checkpoint_zip_valid "$src" || return 1
  tmp="${dst}.tmp.$$"
  rm -f "$tmp"
  cp "$src" "$tmp"
  size3="$(stat -c %s "$src")"
  mtime3="$(stat -c %Y "$src")"
  if [ "$size2" != "$size3" ] || [ "$mtime2" != "$mtime3" ] || ! checkpoint_zip_valid "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  mv "$tmp" "$dst"
  [ -s "$dst" ]
}

checkpoint_zip_valid() {
  python3 - "$1" <<'PY'
import sys
import zipfile

path = sys.argv[1]
try:
    with zipfile.ZipFile(path, "r") as archive:
        valid = bool(archive.infolist())
except (OSError, zipfile.BadZipFile):
    valid = False
raise SystemExit(0 if valid else 1)
PY
}

checkpoint_mtime() {
  local path="$1"
  if [ -s "$path" ]; then
    stat -c %Y "$path"
  else
    echo 0
  fi
}

evals=0
next_threshold="$EVAL_EVERY_STEPS"
if [ -s "$SUBMITTED_TSV" ]; then
  evals="$(awk 'NF {n++} END {print n + 0}' "$SUBMITTED_TSV")"
  last_submitted_step="$(
    awk -F '\t' 'NF >= 3 && $3 ~ /^[0-9]+$/ {if ($3 > max_step) max_step = $3} END {print max_step + 0}' "$SUBMITTED_TSV"
  )"
  while [ "$next_threshold" -le "$last_submitted_step" ]; do
    next_threshold=$((next_threshold + EVAL_EVERY_STEPS))
  done
  echo "resume_eval_monitor submitted_evals=$evals last_submitted_step=$last_submitted_step next_threshold=$next_threshold"
fi
threshold_seen_at=0
threshold_seen_step=-1
while true; do
  step="$(last_step)"
  if [ "$step" -ge "$next_threshold" ] && [ -s "$CHECKPOINT_HOST" ]; then
    if [ "$threshold_seen_at" -eq 0 ]; then
      threshold_seen_at="$(date +%s)"
      threshold_seen_step="$step"
      echo "threshold_seen threshold=$next_threshold step=$step wall_time=$threshold_seen_at checkpoint_mtime=$(checkpoint_mtime "$CHECKPOINT_HOST")"
    fi
    if [ "$CHECKPOINT_FRESH_AFTER_THRESHOLD" = "True" ]; then
      ckpt_mtime="$(checkpoint_mtime "$CHECKPOINT_HOST")"
      if [ "$ckpt_mtime" -lt "$threshold_seen_at" ]; then
        echo "waiting_for_fresh_checkpoint threshold=$next_threshold threshold_seen_step=$threshold_seen_step current_step=$step checkpoint_mtime=$ckpt_mtime threshold_seen_at=$threshold_seen_at path=$CHECKPOINT_HOST"
        sleep "$POLL_SECONDS"
        continue
      fi
    fi
    while [ "$(active_eval_jobs)" -ge "$MAX_CONCURRENT_EVALS" ]; do
      sleep "$POLL_SECONDS"
    done
    snapshot="$SNAPSHOT_DIR/step_$(printf '%07d' "$step").ckpt"
    if [ ! -s "$snapshot" ]; then
      stable_copy_checkpoint "$CHECKPOINT_HOST" "$snapshot" || {
        echo "checkpoint_not_stable step=$step path=$CHECKPOINT_HOST"
        sleep "$POLL_SECONDS"
        continue
      }
    fi
    run_name="${MONITOR_NAME}_step$(printf '%07d' "$step")"
    job_id="$(
      sbatch --parsable \
        --job-name="${JOB_NAME_PREFIX}_s$(printf '%07d' "$step")" \
        --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",CODE_COMMIT="$CODE_COMMIT",RUN_NAME="$run_name",CHECKPOINT="$snapshot",NUM_EPISODES="$NUM_EPISODES",NUM_STEPS="$NUM_STEPS",VIDEO_LENGTH="$VIDEO_LENGTH",ACTION_CHUNK_STEPS="$ACTION_CHUNK_STEPS",DISABLE_FAILURE_TERMINATIONS="$DISABLE_FAILURE_TERMINATIONS",DISABLE_SUCCESS_TERMINATION="$DISABLE_SUCCESS_TERMINATION",STOP_ON_DONE="$STOP_ON_DONE",STOP_ON_BIN_DROP_SUCCESS="$STOP_ON_BIN_DROP_SUCCESS",DEBUG_OBS_INTERVAL="$DEBUG_OBS_INTERVAL",DEBUG_OBS_MAX_FRAMES="$DEBUG_OBS_MAX_FRAMES",RENDERING_MODE="$RENDERING_MODE",CAPTURE_VIDEO="$CAPTURE_VIDEO",YAM_DEFAULT_FINGER_QPOS="$YAM_DEFAULT_FINGER_QPOS",YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH="$YAM_POLICY_OBJECT_ASSET_MANIFEST_PATH",YAM_POLICY_MAX_OBJECTS="$YAM_POLICY_MAX_OBJECTS",YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS="$YAM_POLICY_OBJECT_VALIDATE_USD_BOUNDS",YAM_POLICY_TABLE_TEXTURE_DIR="$YAM_POLICY_TABLE_TEXTURE_DIR",YAM_POLICY_DOME_LIGHT_TEXTURE_DIR="$YAM_POLICY_DOME_LIGHT_TEXTURE_DIR" \
        "$EVAL_WRAPPER"
    )"
    evals=$((evals + 1))
    printf "%s\t%s\t%s\t%s\t%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$evals" "$step" "$job_id" "$snapshot" | tee -a "$SUBMITTED_TSV"
    while [ "$next_threshold" -le "$step" ]; do
      next_threshold=$((next_threshold + EVAL_EVERY_STEPS))
    done
    threshold_seen_at=0
    threshold_seen_step=-1
    if [ "$MAX_EVALS" -gt 0 ] && [ "$evals" -ge "$MAX_EVALS" ]; then
      echo "max_evals_reached evals=$evals"
      exit 0
    fi
  fi
  if [ "$step" -ge "$((TARGET_TRAIN_STEPS - 1))" ]; then
    echo "target_seen step=$step target=$TARGET_TRAIN_STEPS evals=$evals"
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
