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
NUM_STEPS="${NUM_STEPS:-1200}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-1}"
CODE_COMMIT="${CODE_COMMIT:-$(git -C "$CODE_NFS" rev-parse HEAD)}"

MATRIX_DIR="$RESULTS_NFS/evals/$MATRIX_NAME"
MATRIX_TSV="$MATRIX_DIR/eval_matrix.tsv"
mkdir -p "$MATRIX_DIR"

python3 - "$CURRICULUM_JSON" "$STAGE_SIZE" "$N_TRAIN" "$N_VAL" "$MATRIX_TSV" "$MATRIX_NAME" <<'PY'
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
payload = json.loads(curriculum_path.read_text(encoding="utf-8"))
stage = next((row for row in payload.get("stages", []) if int(row["size"]) == stage_size), None)
if stage is None:
    raise SystemExit(f"No stage {stage_size} in {curriculum_path}")

selected = []
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
    "matrix_tsv": "$MATRIX_TSV",
}
Path("$MATRIX_DIR/config.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

job_id="$(
  sbatch --parsable \
    --array="0-$((ENTRY_COUNT - 1))%${MAX_CONCURRENT}" \
    --export=ALL,CODE_NFS="$CODE_NFS",RESULTS_NFS="$RESULTS_NFS",CODE_COMMIT="$CODE_COMMIT",MATRIX_TSV="$MATRIX_TSV",CHECKPOINT="$CHECKPOINT",NUM_STEPS="$NUM_STEPS",ACTION_CHUNK_STEPS="$ACTION_CHUNK_STEPS" \
    "$WRAPPER"
)"
printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$job_id" "$ENTRY_COUNT" \
  | tee -a "$MATRIX_DIR/submissions.tsv"
echo "eval_matrix_job_id=$job_id"
echo "matrix_dir=$MATRIX_DIR"
