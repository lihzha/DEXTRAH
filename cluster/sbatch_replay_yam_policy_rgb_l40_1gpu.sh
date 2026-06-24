#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_policy_rgb
#SBATCH --partition=batch
#SBATCH --time=0-03:50:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_policy_rgb_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ACCEPTED_JSONL="${ACCEPTED_JSONL:?Set ACCEPTED_JSONL to one accepted_demos.jsonl from A100 collection.}"
SHARD_INDEX="${SHARD_INDEX:-0}"
SHARD_COUNT="${SHARD_COUNT:-1}"
MAX_ROWS="${MAX_ROWS:-0}"
RGB_BATCH_NAME="${RGB_BATCH_NAME:-yam_policy_rgb_$(date -u +%Y%m%dT%H%M%SZ)}"
RGB_BATCH_DIR="${RGB_BATCH_DIR:-$RESULTS_NFS/yam_policy_rgb_replays/$RGB_BATCH_NAME}"
SHARD_DIR="$RGB_BATCH_DIR/shard_$(printf '%03d' "$SHARD_INDEX")"
ROWS_JSONL="$SHARD_DIR/source_rows.jsonl"
ROWS_TSV="$SHARD_DIR/source_rows.tsv"
ACCEPTED_RGB_JSONL="$SHARD_DIR/accepted_rgb_replays.jsonl"
FAILED_RGB_JSONL="$SHARD_DIR/failed_rgb_replays.jsonl"
SUMMARY_JSON="$SHARD_DIR/summary.json"

RENDER_WIDTH="${RENDER_WIDTH:-1024}"
RENDER_HEIGHT="${RENDER_HEIGHT:-1024}"
RENDERING_MODE="${RENDERING_MODE:-quality}"
RECORD_RGB_WIDTH="${RECORD_RGB_WIDTH:-256}"
RECORD_RGB_HEIGHT="${RECORD_RGB_HEIGHT:-256}"
RECORD_RGB_INTERVAL="${RECORD_RGB_INTERVAL:-1}"
CAPTURE_INTERVAL="${CAPTURE_INTERVAL:-10}"
FPS="${FPS:-12}"
DEMO_STEPS="${DEMO_STEPS:-0}"
DEMO_START_BLEND_STEPS="${DEMO_START_BLEND_STEPS:-36}"

YAM_POLICY_SCENE_RANDOMIZATION="${YAM_POLICY_SCENE_RANDOMIZATION:-True}"
YAM_POLICY_SCENE_CAMERA_EYE_JITTER="${YAM_POLICY_SCENE_CAMERA_EYE_JITTER:-0.04 0.04 0.04}"
YAM_POLICY_SCENE_CAMERA_TARGET_JITTER="${YAM_POLICY_SCENE_CAMERA_TARGET_JITTER:-0.03 0.03 0.02}"
YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE="${YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE:-450 1600}"
YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE="${YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE:-250 1400}"
YAM_POLICY_MATERIAL_VALUE_RANGE="${YAM_POLICY_MATERIAL_VALUE_RANGE:-0.32 0.82}"
WRIST_CAMERA_POS_OFFSET="${WRIST_CAMERA_POS_OFFSET:-0.035 0.0 0.085}"
WRIST_CAMERA_FORWARD="${WRIST_CAMERA_FORWARD:-0.16 0.0 -0.10}"

if [ "$SHARD_COUNT" -lt 1 ]; then
  echo "SHARD_COUNT must be >= 1" >&2
  exit 2
fi
if [ "$SHARD_INDEX" -lt 0 ] || [ "$SHARD_INDEX" -ge "$SHARD_COUNT" ]; then
  echo "SHARD_INDEX must be in [0, SHARD_COUNT), got $SHARD_INDEX/$SHARD_COUNT" >&2
  exit 2
fi
if [ ! -f "$ACCEPTED_JSONL" ]; then
  echo "Missing ACCEPTED_JSONL: $ACCEPTED_JSONL" >&2
  exit 2
fi

mkdir -p "$SHARD_DIR" "$NFS_ROOT/slurm_logs/dextrah"
: > "$ACCEPTED_RGB_JSONL"
: > "$FAILED_RGB_JSONL"

python3 - "$ACCEPTED_JSONL" "$ROWS_JSONL" "$ROWS_TSV" "$SHARD_INDEX" "$SHARD_COUNT" "$MAX_ROWS" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
rows_jsonl = Path(sys.argv[2])
rows_tsv = Path(sys.argv[3])
shard_index = int(sys.argv[4])
shard_count = int(sys.argv[5])
max_rows = int(sys.argv[6])

selected = []
for source_index, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
    if not line.strip():
        continue
    row = json.loads(line)
    if source_index % shard_count != shard_index:
        continue
    if max_rows > 0 and len(selected) >= max_rows:
        break
    stable = str(row.get("stable_scene") or "")
    trajectory = str(row.get("trajectory") or "")
    if not stable or not trajectory:
        raise SystemExit(f"row {source_index} missing stable_scene or trajectory")
    selected.append((source_index, row))

rows_jsonl.parent.mkdir(parents=True, exist_ok=True)
with rows_jsonl.open("w", encoding="utf-8") as f_jsonl, rows_tsv.open("w", encoding="utf-8") as f_tsv:
    for source_index, row in selected:
        f_jsonl.write(json.dumps(row, sort_keys=True) + "\n")
        values = [
            str(source_index),
            str(row.get("seed", source_index)),
            str(row.get("stable_scene") or ""),
            str(row.get("trajectory") or ""),
            str(row.get("dataset") or ""),
            str(row.get("objects_per_demo", 1)),
        ]
        f_tsv.write("\t".join(values) + "\n")
print(json.dumps({"event": "rgb_replay_rows_selected", "rows": len(selected), "rows_jsonl": str(rows_jsonl)}))
PY

echo "Running YAM policy RGB replay on L40"
echo "CODE_NFS=$CODE_NFS"
echo "RESULTS_NFS=$RESULTS_NFS"
echo "ACCEPTED_JSONL=$ACCEPTED_JSONL"
echo "RGB_BATCH_DIR=$RGB_BATCH_DIR"
echo "SHARD_INDEX=$SHARD_INDEX"
echo "SHARD_COUNT=$SHARD_COUNT"
echo "RENDERING_MODE=$RENDERING_MODE"
echo "RECORD_RGB=${RECORD_RGB_WIDTH}x${RECORD_RGB_HEIGHT}"
echo "ROWS_TSV=$ROWS_TSV"

run_render_wrapper() {
  bash "$CODE_NFS/cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh" </dev/null
}

accepted=0
failed=0
while IFS=$'\t' read -r source_row_index seed stable_scene trajectory source_dataset objects_per_demo; do
  row_dir="$SHARD_DIR/row_$(printf '%06d' "$source_row_index")"
  mkdir -p "$row_dir"
  run_name="${RGB_BATCH_NAME}_s$(printf '%03d' "$SHARD_INDEX")_row$(printf '%06d' "$source_row_index")"
  dataset_path="$row_dir/trajectory_dataset.npz"
  video_path="$RESULTS_NFS/validations/$run_name/yam_rgb_replay.mp4"
  metrics_path="$RESULTS_NFS/validations/$run_name/metrics.json"
  if RUN_NAME="$run_name" \
    TASK="Dextrah-Single-YAM-Tabletop-Clutter-Grasp" \
    NUM_ENVS=1 \
    SEED="$seed" \
    DEMO_MODE=single_yam_trajectory \
    DEMO_STEPS="$DEMO_STEPS" \
    CAPTURE_INTERVAL="$CAPTURE_INTERVAL" \
    FPS="$FPS" \
    VIDEO_FILENAME=yam_rgb_replay.mp4 \
    DEMO_TRAJECTORY_PATH="$trajectory" \
    DEMO_TRAJECTORY_SOURCE=graspgenx_replay \
    DEMO_TRAJECTORY_REPLAY_MODE=dynamic \
    DEMO_TRAJECTORY_TIMING_MODE=realtime \
    DEMO_TRAJECTORY_VELOCITY_TARGETS=True \
    DEMO_TRAJECTORY_VELOCITY_TARGET_SCALE=1.0 \
    DEMO_START_BLEND_STEPS="$DEMO_START_BLEND_STEPS" \
    STABLE_SCENE_PATH="$stable_scene" \
    RECORD_TRAJECTORY_DATASET=True \
    TRAJECTORY_DATASET_PATH="$dataset_path" \
    RECORD_MULTICAM_RGB=True \
    RECORD_SCENE_RGB=True \
    RECORD_WRIST_RGB=True \
    RECORD_RGB_WIDTH="$RECORD_RGB_WIDTH" \
    RECORD_RGB_HEIGHT="$RECORD_RGB_HEIGHT" \
    RECORD_RGB_INTERVAL="$RECORD_RGB_INTERVAL" \
    RENDER_WIDTH="$RENDER_WIDTH" \
    RENDER_HEIGHT="$RENDER_HEIGHT" \
    RENDERING_MODE="$RENDERING_MODE" \
    YAM_POLICY_SCENE_RANDOMIZATION="$YAM_POLICY_SCENE_RANDOMIZATION" \
    YAM_POLICY_SCENE_CAMERA_EYE_JITTER="$YAM_POLICY_SCENE_CAMERA_EYE_JITTER" \
    YAM_POLICY_SCENE_CAMERA_TARGET_JITTER="$YAM_POLICY_SCENE_CAMERA_TARGET_JITTER" \
    YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE="$YAM_POLICY_DOME_LIGHT_INTENSITY_RANGE" \
    YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE="$YAM_POLICY_KEY_LIGHT_INTENSITY_RANGE" \
    YAM_POLICY_MATERIAL_VALUE_RANGE="$YAM_POLICY_MATERIAL_VALUE_RANGE" \
    WRIST_CAMERA_POS_OFFSET="$WRIST_CAMERA_POS_OFFSET" \
    WRIST_CAMERA_FORWARD="$WRIST_CAMERA_FORWARD" \
    HIDE_ROBOT_DEBUG_SITES=True \
    CODE_NFS="$CODE_NFS" \
    run_render_wrapper && [ -s "$dataset_path" ]; then
    accepted="$((accepted + 1))"
    python3 - "$ACCEPTED_RGB_JSONL" "$source_row_index" "$seed" "$stable_scene" "$trajectory" "$source_dataset" "$dataset_path" "$video_path" "$metrics_path" "$objects_per_demo" <<'PY'
import json
import sys
from pathlib import Path

out, source_row_index, seed, stable, trajectory, source_dataset, dataset, video, metrics, objects_per_demo = sys.argv[1:]
payload = {
    "source_row_index": int(source_row_index),
    "seed": int(seed),
    "objects_per_demo": int(objects_per_demo),
    "stable_scene": stable,
    "trajectory": trajectory,
    "source_dataset": source_dataset,
    "final_rgb_dataset": dataset,
    "final_rgb_dataset_metadata": dataset + ".metadata.json",
    "final_rgb_video": video,
    "final_rgb_metrics": metrics,
}
with Path(out).open("a", encoding="utf-8") as f:
    f.write(json.dumps(payload, sort_keys=True) + "\n")
print(json.dumps({"event": "rgb_replay_accepted", "source_row_index": int(source_row_index), "dataset": dataset}))
PY
  else
    failed="$((failed + 1))"
    python3 - "$FAILED_RGB_JSONL" "$source_row_index" "$seed" "$stable_scene" "$trajectory" "$dataset_path" <<'PY'
import json
import sys
from pathlib import Path

out, source_row_index, seed, stable, trajectory, dataset = sys.argv[1:]
with Path(out).open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "source_row_index": int(source_row_index),
        "seed": int(seed),
        "stable_scene": stable,
        "trajectory": trajectory,
        "attempted_dataset": dataset,
    }, sort_keys=True) + "\n")
print(json.dumps({"event": "rgb_replay_failed", "source_row_index": int(source_row_index)}))
PY
  fi
done < "$ROWS_TSV"

python3 - "$SUMMARY_JSON" "$RGB_BATCH_NAME" "$RGB_BATCH_DIR" "$SHARD_INDEX" "$SHARD_COUNT" "$accepted" "$failed" "$ACCEPTED_RGB_JSONL" "$FAILED_RGB_JSONL" "$RENDERING_MODE" "$RECORD_RGB_WIDTH" "$RECORD_RGB_HEIGHT" <<'PY'
import json
import sys
from pathlib import Path

(
    path,
    batch_name,
    batch_dir,
    shard_index,
    shard_count,
    accepted,
    failed,
    accepted_jsonl,
    failed_jsonl,
    rendering_mode,
    record_rgb_width,
    record_rgb_height,
) = sys.argv[1:]
payload = {
    "batch_name": batch_name,
    "batch_dir": batch_dir,
    "shard_index": int(shard_index),
    "shard_count": int(shard_count),
    "accepted": int(accepted),
    "failed": int(failed),
    "accepted_rgb_jsonl": accepted_jsonl,
    "failed_rgb_jsonl": failed_jsonl,
    "rendering_mode": rendering_mode,
    "image_resolution": [int(record_rgb_width), int(record_rgb_height)],
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "rgb_replay_summary_written", "path": path, "accepted": int(accepted), "failed": int(failed)}))
PY

if [ "$failed" -gt 0 ]; then
  exit 1
fi
