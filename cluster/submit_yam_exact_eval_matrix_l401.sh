#!/bin/bash
set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
WRAPPER="${WRAPPER:-$CODE_NFS/cluster/sbatch_eval_yam_exact_matrix_entry_1gpu.sh}"
CURRICULUM_JSON="${CURRICULUM_JSON:?Set CURRICULUM_JSON.}"
STAGE_SIZE="${STAGE_SIZE:?Set STAGE_SIZE.}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT.}"
MATRIX_NAME="${MATRIX_NAME:-yam_exact_eval_stage${STAGE_SIZE}_$(date -u +%Y%m%dT%H%M%SZ)}"
N_TRAIN="${N_TRAIN:-2}"
N_VAL="${N_VAL:-3}"
MAX_CONCURRENT="${MAX_CONCURRENT:-3}"
POLL_SECONDS="${POLL_SECONDS:-20}"
SBATCH_TIME="${SBATCH_TIME:-01:30:00}"
NUM_STEPS="${NUM_STEPS:-1200}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-1}"
DEBUG_OBS_INTERVAL="${DEBUG_OBS_INTERVAL:-120}"
DEBUG_OBS_MAX_FRAMES="${DEBUG_OBS_MAX_FRAMES:-40}"
EXACT_VISUAL_RESAMPLE="${EXACT_VISUAL_RESAMPLE:-True}"
EXACT_SHARD_KIND="${EXACT_SHARD_KIND:-training}"
YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="${YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION:-True}"
YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="${YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION:-True}"
CODE_COMMIT="${CODE_COMMIT:-$(git -C "$CODE_NFS" rev-parse HEAD)}"
JOB_NAME_PREFIX="${JOB_NAME_PREFIX:-yamev_$(printf '%s' "$MATRIX_NAME" | cksum | awk '{print $1}')}"

MATRIX_DIR="$RESULTS_NFS/evals/$MATRIX_NAME"
MATRIX_TSV="$MATRIX_DIR/eval_matrix.tsv"
mkdir -p "$MATRIX_DIR"
if [ "$MAX_CONCURRENT" -lt 1 ] || [ "$POLL_SECONDS" -lt 1 ]; then
  echo "MAX_CONCURRENT and POLL_SECONDS must be positive" >&2
  exit 2
fi
if [[ ! "$JOB_NAME_PREFIX" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "JOB_NAME_PREFIX may contain only letters, digits, underscores, and hyphens" >&2
  exit 2
fi
exec 9>"$MATRIX_DIR/submitter.lock"
if ! flock -n 9; then
  echo "Another submitter owns $MATRIX_DIR/submitter.lock" >&2
  exit 2
fi

python3 - "$CURRICULUM_JSON" "$STAGE_SIZE" "$N_TRAIN" "$N_VAL" "$MATRIX_TSV" "$MATRIX_NAME" "$EXACT_SHARD_KIND" <<'PY'
import json
import re
import sys
from pathlib import Path

curriculum_path = Path(sys.argv[1])
stage_size = int(sys.argv[2])
n_train = int(sys.argv[3])
n_val = int(sys.argv[4])
output_path = Path(sys.argv[5])
matrix_name = sys.argv[6]
shard_kind = sys.argv[7]
payload = json.loads(curriculum_path.read_text(encoding="utf-8"))
stage = next((row for row in payload.get("stages", []) if int(row["size"]) == stage_size), None)
if stage is None:
    raise SystemExit(f"No stage {stage_size} in {curriculum_path}")
if shard_kind not in {"training", "source"}:
    raise SystemExit(f"EXACT_SHARD_KIND must be training or source, got {shard_kind}")


def container_path(path: Path) -> str:
    text = str(path.resolve())
    marker = "/results/dextrah/"
    if marker in text:
        return "/results/" + text.split(marker, 1)[1]
    if text.startswith("/results/"):
        return text
    raise SystemExit(f"Cannot map exact shard into the results container: {text}")

selected = []
if shard_kind == "training":
    stage_manifest_path = Path(stage["manifest"])
    stage_manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
    for split, count in (("train", n_train), ("val", n_val)):
        rows = [row for row in stage_manifest.get("shards", []) if row.get("split") == split]
        if len(rows) < count:
            raise SystemExit(f"Stage {stage_size} has only {len(rows)} {split} shards, requested {count}")
        for split_index, row in enumerate(rows[:count]):
            source_index = int(row["source_index"])
            path = Path(str(row["path"]))
            if not path.is_absolute():
                path = stage_manifest_path.parent / path
            run_name = f"{matrix_name}_{split}_src{source_index:06d}"
            selected.append(
                (split, source_index, container_path(path), run_name, split_index == 0)
            )
else:
    for split, key, count in (
        ("train", "train_source_policy_shards", n_train),
        ("val", "val_source_policy_shards", n_val),
    ):
        paths = [str(path) for path in stage.get(key, [])]
        if len(paths) < count:
            raise SystemExit(f"Stage {stage_size} has only {len(paths)} {split} shards, requested {count}")
        for split_index, path in enumerate(paths[:count]):
            match = re.search(r"(\d+)$", Path(path).name)
            if match is None:
                raise SystemExit(f"Cannot infer source index from {path}")
            source_index = int(match.group(1))
            run_name = f"{matrix_name}_{split}_src{source_index:06d}"
            selected.append((split, source_index, path, run_name, split_index == 0))

lines = ["matrix_index\tsplit\tsource_index\texact_policy_shard\trun_name\tcapture_video"]
for index, (split, source_index, path, run_name, capture_video) in enumerate(selected):
    lines.append(
        f"{index}\t{split}\t{source_index}\t{path}\t{run_name}\t{'True' if capture_video else 'False'}"
    )
output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"matrix": str(output_path), "entries": len(selected)}, sort_keys=True))
PY

ENTRY_COUNT="$(( $(wc -l < "$MATRIX_TSV") - 1 ))"
if [ "$ENTRY_COUNT" -lt 1 ]; then
  echo "Empty eval matrix: $MATRIX_TSV" >&2
  exit 2
fi
python3 - "$MATRIX_DIR/config.json" <<PY
import json
from pathlib import Path
payload = {
    "code_commit": "$CODE_COMMIT",
    "checkpoint": "$CHECKPOINT",
    "curriculum_json": "$CURRICULUM_JSON",
    "stage_size": int("$STAGE_SIZE"),
    "n_train": int("$N_TRAIN"),
    "n_val": int("$N_VAL"),
    "num_steps": int("$NUM_STEPS"),
    "action_chunk_steps": int("$ACTION_CHUNK_STEPS"),
    "debug_obs_interval": int("$DEBUG_OBS_INTERVAL"),
    "debug_obs_max_frames": int("$DEBUG_OBS_MAX_FRAMES"),
    "exact_visual_resample": "$EXACT_VISUAL_RESAMPLE" == "True",
    "exact_shard_kind": "$EXACT_SHARD_KIND",
    "robot_material_randomization": "$YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION" == "True",
    "object_material_randomization": "$YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION" == "True",
    "matrix_tsv": "$MATRIX_TSV",
    "max_concurrent": int("$MAX_CONCURRENT"),
    "poll_seconds": int("$POLL_SECONDS"),
    "sbatch_time": "$SBATCH_TIME",
    "job_name_prefix": "$JOB_NAME_PREFIX",
    "submission_mode": "ordinary_jobs_with_submitter_throttle",
}
Path("$MATRIX_DIR/config.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

SUBMISSIONS_TSV="$MATRIX_DIR/submissions.tsv"
touch "$SUBMISSIONS_TSV"
printf '%s\t%s\t%s\t%s\t%s\n' "timestamp_utc" "job_id" "entry_index" "job_name" "code_commit" > "$MATRIX_DIR/submissions_header.tsv"
printf '%s\t%s\t%s\n' "$(hostname)" "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$MATRIX_DIR/submitter_process.tsv"

active_jobs() {
  squeue -h -u "${USER:-lzha}" -t PENDING,RUNNING,CONFIGURING,COMPLETING -o "%j" \
    | grep -c "^${JOB_NAME_PREFIX}_e" || true
}

for entry_index in $(seq 0 "$((ENTRY_COUNT - 1))"); do
  while [ "$(active_jobs)" -ge "$MAX_CONCURRENT" ]; do
    sleep "$POLL_SECONDS"
  done
  entry_index_padded="$(printf '%03d' "$entry_index")"
  job_name="${JOB_NAME_PREFIX}_e${entry_index_padded}"
  job_id="$(
    sbatch --parsable \
      --job-name="$job_name" \
      --time="$SBATCH_TIME" \
      --output="$NFS_ROOT/slurm_logs/dextrah/eval_yam_exact_${MATRIX_NAME}_${entry_index_padded}_%j.out" \
      --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",CODE_COMMIT="$CODE_COMMIT",MATRIX_TSV="$MATRIX_TSV",ENTRY_INDEX="$entry_index",CHECKPOINT="$CHECKPOINT",NUM_STEPS="$NUM_STEPS",ACTION_CHUNK_STEPS="$ACTION_CHUNK_STEPS",DEBUG_OBS_INTERVAL="$DEBUG_OBS_INTERVAL",DEBUG_OBS_MAX_FRAMES="$DEBUG_OBS_MAX_FRAMES",EXACT_VISUAL_RESAMPLE="$EXACT_VISUAL_RESAMPLE",YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION="$YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION",YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION="$YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION" \
      "$WRAPPER"
  )"
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$job_id" "$entry_index" "$job_name" "$CODE_COMMIT" \
    | tee -a "$SUBMISSIONS_TSV"
done

echo "submitted_jobs=$SUBMISSIONS_TSV"
echo "matrix_dir=$MATRIX_DIR"
