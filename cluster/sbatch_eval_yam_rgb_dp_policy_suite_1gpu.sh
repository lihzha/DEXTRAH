#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=yam_rgb_dp_eval
#SBATCH --partition=batch
#SBATCH --time=0-02:00:00
#SBATCH --mem=160G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_rgb_dp_eval_suite_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
ROBOLAB_NFS="${ROBOLAB_NFS:-$NFS_ROOT/src/RoboLab}"
OFFICIAL_DP_NFS="${OFFICIAL_DP_NFS:-$NFS_ROOT/src/external/real-stanford-diffusion_policy}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
DP_ENV_NAME="${DP_ENV_NAME:-franka-cube-dp-bc-warmstart-official-dp}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"

TASK="${TASK:-Dextrah-Single-YAM-Tabletop-Clutter-Grasp}"
CHECKPOINT_HOST="${CHECKPOINT_HOST:-$RESULTS_NFS/dp_bc/checkpoints/yam_rgb_dp_full500_b16_s10000_20260623/latest.ckpt}"
ACCEPTED_MANIFEST_HOST="${ACCEPTED_MANIFEST_HOST:-$RESULTS_NFS/yam_demos/yam_selected50_multidemo_500_dropoffset_20260622/accepted_demos_first500.jsonl}"
FULL_OBJAVERSE_ASSET_ROOT="${FULL_OBJAVERSE_ASSET_ROOT:-$RESULTS_NFS/assets/graspgen_objects_full_cpu_20260617_153051}"
FULL_OBJAVERSE_MANIFEST_HOST="${FULL_OBJAVERSE_MANIFEST_HOST:-$FULL_OBJAVERSE_ASSET_ROOT/manifest.json}"
FULL_OBJAVERSE_CONTAINER_ASSET_ROOT="${FULL_OBJAVERSE_CONTAINER_ASSET_ROOT:-/results/assets/graspgen_objects_full_cpu_20260617_153051}"

SLURM_JOB_ID_SAFE="${SLURM_JOB_ID:-manual}"
RUN_NAME="${RUN_NAME:-yam_rgb_dp_eval_suite_${SLURM_JOB_ID_SAFE}_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR_HOST="$RESULTS_NFS/evals/$RUN_NAME"
RUN_DIR_CONTAINER="/results/evals/$RUN_NAME"
ID_EXPECTED_OBJECTS="${ID_EXPECTED_OBJECTS:-3}"
ID_CASE_INDEX="${ID_CASE_INDEX:-0}"
OOD_SEED="${OOD_SEED:-9400001}"
OOD_EXPECTED_OBJECTS="${OOD_EXPECTED_OBJECTS:-$ID_EXPECTED_OBJECTS}"
OOD_SETTLE_STEPS="${OOD_SETTLE_STEPS:-100}"
OOD_MANIFEST_POOL_SIZE="${OOD_MANIFEST_POOL_SIZE:-512}"
OOD_MIN_XY_RADIUS="${OOD_MIN_XY_RADIUS:-0.012}"
OOD_MAX_XY_RADIUS="${OOD_MAX_XY_RADIUS:-0.075}"
OOD_MIN_HEIGHT="${OOD_MIN_HEIGHT:-0.010}"
OOD_MAX_HEIGHT="${OOD_MAX_HEIGHT:-0.160}"
OOD_MAX_GRASP_WIDTH_P95="${OOD_MAX_GRASP_WIDTH_P95:-0.145}"
OOD_EXCLUDE_KEYWORDS="${OOD_EXCLUDE_KEYWORDS:-animal,building,car,chair,person,plant,room,statue,tree,vehicle}"
if [ "$ID_EXPECTED_OBJECTS" -lt 1 ]; then
  echo "ID_EXPECTED_OBJECTS must be >= 1, got $ID_EXPECTED_OBJECTS" >&2
  exit 2
fi
if [ "$OOD_EXPECTED_OBJECTS" -lt 1 ]; then
  echo "OOD_EXPECTED_OBJECTS must be >= 1, got $OOD_EXPECTED_OBJECTS" >&2
  exit 2
fi
DEMO_STEPS="${DEMO_STEPS:-1621}"
CAPTURE_INTERVAL="${CAPTURE_INTERVAL:-20}"
FPS="${FPS:-30}"
RECORD_RGB_WIDTH="${RECORD_RGB_WIDTH:-160}"
RECORD_RGB_HEIGHT="${RECORD_RGB_HEIGHT:-120}"
RECORD_RGB_INTERVAL="${RECORD_RGB_INTERVAL:-1}"
POLICY_IMAGE_HEIGHT="${POLICY_IMAGE_HEIGHT:-96}"
POLICY_IMAGE_WIDTH="${POLICY_IMAGE_WIDTH:-128}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-100}"
NUM_ACTION_SAMPLES="${NUM_ACTION_SAMPLES:-1}"
POLICY_SAMPLE_SEED="${POLICY_SAMPLE_SEED:-}"
ACTION_CHUNK_STEPS="${ACTION_CHUNK_STEPS:-8}"
POLICY_MAX_JOINT_DELTA="${POLICY_MAX_JOINT_DELTA:-0.20}"
POLICY_MAX_GRIPPER_DELTA="${POLICY_MAX_GRIPPER_DELTA:-0.02}"
VALIDATION_REQUIRE_ACCEPTED="${VALIDATION_REQUIRE_ACCEPTED:-False}"
DISABLE_FABRIC="${DISABLE_FABRIC:-False}"
PREPARE_YAM_ASSETS="${PREPARE_YAM_ASSETS:-auto}"
YAM_ASSET_PREPARE_LOCK="${YAM_ASSET_PREPARE_LOCK:-$RESULTS_NFS/locks/yam_asset_prepare.lock}"
CODE_COMMIT="${CODE_COMMIT:-}"
if [ -z "$CODE_COMMIT" ] && git -C "$CODE_NFS" rev-parse HEAD >/dev/null 2>&1; then
  CODE_COMMIT="$(git -C "$CODE_NFS" rev-parse HEAD)"
fi

if [ ! -f "$IMAGE" ]; then
  echo "Missing Isaac Lab container image: $IMAGE" >&2
  exit 2
fi
if [ ! -d "$ENV_ROOT/$ENV_NAME/site" ]; then
  echo "Missing DEXTRAH Python target: $ENV_ROOT/$ENV_NAME/site" >&2
  exit 2
fi
if [ ! -d "$ENV_ROOT/$DP_ENV_NAME/site" ]; then
  echo "Missing Diffusion Policy Python target: $ENV_ROOT/$DP_ENV_NAME/site" >&2
  exit 2
fi
if [ ! -f "$CHECKPOINT_HOST" ]; then
  echo "Missing checkpoint: $CHECKPOINT_HOST" >&2
  exit 2
fi
if [ ! -f "$ACCEPTED_MANIFEST_HOST" ]; then
  echo "Missing accepted demo manifest: $ACCEPTED_MANIFEST_HOST" >&2
  exit 2
fi
if [ ! -f "$FULL_OBJAVERSE_MANIFEST_HOST" ]; then
  echo "Missing full Objaverse manifest: $FULL_OBJAVERSE_MANIFEST_HOST" >&2
  exit 2
fi
if [ -n "$CODE_COMMIT" ]; then
  actual_commit="$(git -C "$CODE_NFS" rev-parse HEAD)"
  if [ "$actual_commit" != "$CODE_COMMIT" ]; then
    echo "CODE_COMMIT mismatch: expected $CODE_COMMIT, found $actual_commit in $CODE_NFS" >&2
    exit 2
  fi
fi

mkdir -p \
  "$RUN_DIR_HOST" \
  "$NFS_ROOT/slurm_logs/dextrah" \
  "$CACHE_NFS/kit" "$CACHE_NFS/ov" "$CACHE_NFS/pip" \
  "$CACHE_NFS/glcache" "$CACHE_NFS/computecache" \
  "$CACHE_NFS/omni_logs" "$CACHE_NFS/carb_logs" \
  "$CACHE_NFS/data" "$CACHE_NFS/documents"

CASE_ENV_HOST="$RUN_DIR_HOST/case_env.sh"
python3 - "$ACCEPTED_MANIFEST_HOST" "$FULL_OBJAVERSE_MANIFEST_HOST" "$RUN_DIR_HOST" "$ID_EXPECTED_OBJECTS" "$ID_CASE_INDEX" "$OOD_SEED" "$RESULTS_NFS" "$FULL_OBJAVERSE_CONTAINER_ASSET_ROOT" "$OOD_MANIFEST_POOL_SIZE" "$OOD_MIN_XY_RADIUS" "$OOD_MAX_XY_RADIUS" "$OOD_MIN_HEIGHT" "$OOD_MAX_HEIGHT" "$OOD_MAX_GRASP_WIDTH_P95" "$OOD_EXPECTED_OBJECTS" "$OOD_EXCLUDE_KEYWORDS" <<'PY'
import json
import math
import random
import shlex
import sys
from collections import Counter
from pathlib import Path
from typing import Any

accepted_manifest = Path(sys.argv[1])
full_manifest = Path(sys.argv[2])
run_dir = Path(sys.argv[3])
id_expected_objects = int(sys.argv[4])
id_case_index = int(sys.argv[5])
ood_seed = int(sys.argv[6])
results_root = Path(sys.argv[7])
container_asset_root = sys.argv[8]
ood_manifest_pool_size = int(sys.argv[9])
ood_min_xy_radius = float(sys.argv[10])
ood_max_xy_radius = float(sys.argv[11])
ood_min_height = float(sys.argv[12])
ood_max_height = float(sys.argv[13])
ood_max_grasp_width_p95 = float(sys.argv[14])
ood_expected_objects = int(sys.argv[15])
ood_exclude_keywords = tuple(item.strip().lower() for item in sys.argv[16].split(",") if item.strip())
if ood_expected_objects < 1:
    raise SystemExit(f"OOD expected object count must be >= 1, got {ood_expected_objects}")

def host_path(value):
    text = str(value or "")
    if text.startswith("/results/"):
        return str(results_root / text[len("/results/"):])
    return text

def as_float_list(value: Any, length: int) -> list[float] | None:
    if not isinstance(value, list) or len(value) != length:
        return None
    try:
        values = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in values):
        return None
    return values

def bounds(record: dict[str, Any]) -> tuple[list[float], list[float]] | None:
    bounds_min = as_float_list(record.get("scaled_bounds_min"), 3)
    bounds_max = as_float_list(record.get("scaled_bounds_max"), 3)
    if bounds_min is not None and bounds_max is not None:
        return bounds_min, bounds_max
    half_extents = as_float_list(record.get("scaled_half_extents"), 3)
    if half_extents is not None:
        return [-v for v in half_extents], half_extents
    try:
        scale = float(record.get("scale", 1.0))
    except (TypeError, ValueError):
        return None
    raw_min = as_float_list(record.get("bounds_min"), 3)
    raw_max = as_float_list(record.get("bounds_max"), 3)
    if raw_min is not None and raw_max is not None:
        return [scale * v for v in raw_min], [scale * v for v in raw_max]
    raw_half = as_float_list(record.get("half_extents"), 3)
    if raw_half is not None:
        half = [scale * v for v in raw_half]
        return [-v for v in half], half
    return None

def xy_radius(bounds_min: list[float], bounds_max: list[float]) -> float:
    return max(abs(bounds_min[0]), abs(bounds_max[0]), abs(bounds_min[1]), abs(bounds_max[1]))

def height(bounds_min: list[float], bounds_max: list[float]) -> float:
    return bounds_max[2] - bounds_min[2]

def metadata_text(record: dict[str, Any]) -> str:
    fragments: list[str] = []
    for key in ("name", "title", "category", "categories", "labels", "tags", "description", "metadata", "uuid"):
        value = record.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            fragments.extend(str(item) for item in value)
        elif isinstance(value, dict):
            fragments.extend(str(item) for item in value.values())
        else:
            fragments.append(str(value))
    return " ".join(fragments).lower()

rows = []
for line in accepted_manifest.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    rows.append(row)
if not rows:
    raise SystemExit(f"No rows in accepted manifest: {accepted_manifest}")

matching = []
for row in rows:
    sequence = row.get("object_sequence")
    count = row.get("objects_per_demo")
    if count is None and isinstance(sequence, list):
        count = len(sequence)
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = -1
    if count == id_expected_objects:
        matching.append(row)
pool = matching if matching else rows
id_row = pool[id_case_index % len(pool)]
stable_scene = id_row.get("stable_scene")
if not stable_scene:
    metadata = id_row.get("dataset_metadata")
    if isinstance(metadata, dict):
        stable_scene = metadata.get("stable_scene_path")
if not stable_scene and id_row.get("dataset"):
    try:
        import numpy as np
        with np.load(host_path(id_row["dataset"]), allow_pickle=False) as data:
            metadata = json.loads(str(data["metadata_json"].item()))
        stable_scene = metadata.get("stable_scene_path")
    except Exception as exc:
        raise SystemExit(f"Could not resolve stable scene from dataset metadata: {exc}") from exc
stable_scene = host_path(stable_scene)
if not stable_scene or not Path(stable_scene).is_file():
    raise SystemExit(f"Resolved ID stable scene does not exist: {stable_scene}")
id_sequence = id_row.get("object_sequence") if isinstance(id_row.get("object_sequence"), list) else []
id_case = {
    "case": "id",
    "source_manifest": str(accepted_manifest),
    "stable_scene_host": stable_scene,
    "expected_objects": int(id_expected_objects if matching else len(id_sequence) or 1),
    "objects_per_demo": id_row.get("objects_per_demo"),
    "dataset": id_row.get("dataset"),
    "video": id_row.get("video"),
    "object_sequence": id_sequence,
}
(run_dir / "id_case.json").write_text(json.dumps(id_case, indent=2, sort_keys=True) + "\n", encoding="utf-8")

train_uuids = set()
for row in rows:
    sequence = row.get("object_sequence")
    if not isinstance(sequence, list):
        continue
    for item in sequence:
        if isinstance(item, dict) and item.get("uuid"):
            train_uuids.add(str(item["uuid"]))
source = json.loads(full_manifest.read_text(encoding="utf-8"))
objects = source.get("objects")
if not isinstance(objects, list):
    raise SystemExit(f"Full manifest has no objects list: {full_manifest}")
skipped = Counter()
candidates = []
for obj in objects:
    if not isinstance(obj, dict):
        skipped["not_object"] += 1
        continue
    uuid = str(obj.get("uuid") or "")
    if not uuid:
        skipped["missing_uuid"] += 1
        continue
    if uuid in train_uuids:
        skipped["training_uuid"] += 1
        continue
    if not (obj.get("usd_path") or obj.get("path")):
        skipped["missing_usd_path"] += 1
        continue
    obj_bounds = bounds(obj)
    if obj_bounds is None:
        skipped["invalid_bounds"] += 1
        continue
    bounds_min, bounds_max = obj_bounds
    radius = xy_radius(bounds_min, bounds_max)
    object_height = height(bounds_min, bounds_max)
    if radius < ood_min_xy_radius:
        skipped["too_small_xy_radius"] += 1
        continue
    if radius > ood_max_xy_radius:
        skipped["too_large_xy_radius"] += 1
        continue
    if object_height < ood_min_height:
        skipped["too_short"] += 1
        continue
    if object_height > ood_max_height:
        skipped["too_tall"] += 1
        continue
    prior = obj.get("grasp_prior") if isinstance(obj.get("grasp_prior"), dict) else {}
    width_p95 = prior.get("grasp_width_p95")
    if width_p95 is not None:
        try:
            if float(width_p95) > ood_max_grasp_width_p95:
                skipped["too_wide_grasp"] += 1
                continue
        except (TypeError, ValueError):
            pass
    text = metadata_text(obj)
    if any(keyword in text for keyword in ood_exclude_keywords):
        skipped["excluded_keyword"] += 1
        continue
    normalized = dict(obj)
    normalized["yam_rgb_dp_eval_filter"] = {
        "xy_radius": radius,
        "height": object_height,
    }
    candidates.append(normalized)
if not candidates:
    raise SystemExit(f"No OOD candidates after filtering; skipped={dict(skipped)}")
rng = random.Random(ood_seed)
rng.shuffle(candidates)
ood_pool = candidates if ood_manifest_pool_size <= 0 else candidates[:ood_manifest_pool_size]
ood_object = ood_pool[0]
ood_filter = {
    "source_count": len(objects),
    "candidate_count": len(candidates),
    "manifest_pool_size": len(ood_pool),
    "excluded_training_uuid_count": len(train_uuids),
    "skipped": dict(sorted(skipped.items())),
    "seed": ood_seed,
    "min_xy_radius": ood_min_xy_radius,
    "max_xy_radius": ood_max_xy_radius,
    "min_height": ood_min_height,
    "max_height": ood_max_height,
    "max_grasp_width_p95": ood_max_grasp_width_p95,
    "exclude_keywords": list(ood_exclude_keywords),
}
ood_manifest = run_dir / "ood_object_manifest.json"
ood_payload = {
    "format": "dextrah_yam_rgb_dp_ood_eval_manifest_v1",
    "asset_root": container_asset_root,
    "source_manifest": str(full_manifest),
    "ood_filter": ood_filter,
    "objects": ood_pool,
}
ood_manifest.write_text(json.dumps(ood_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
ood_case = {
    "case": "ood",
    "source_manifest": str(full_manifest),
    "manifest_host": str(ood_manifest),
    "expected_objects": int(ood_expected_objects),
    "seed": ood_seed,
    "first_manifest_candidate": {
        "uuid": str(ood_object.get("uuid") or ""),
        "name": str(ood_object.get("name") or ood_object.get("uuid") or ""),
        "usd_path": str(ood_object.get("usd_path") or ood_object.get("path") or ""),
        "xy_radius": ood_object.get("xy_radius"),
        "scaled_half_extents": ood_object.get("scaled_half_extents"),
    },
    "manifest_candidate_uuids": [str(obj.get("uuid") or "") for obj in ood_pool[:64]],
    "ood_filter": ood_filter,
}
(run_dir / "ood_case.json").write_text(json.dumps(ood_case, indent=2, sort_keys=True) + "\n", encoding="utf-8")

env = {
    "ID_STABLE_SCENE_HOST": stable_scene,
    "ID_EXPECTED_OBJECTS_RESOLVED": str(id_case["expected_objects"]),
    "OOD_MANIFEST_HOST": str(ood_manifest),
    "OOD_EXPECTED_OBJECTS_RESOLVED": str(ood_expected_objects),
}
(run_dir / "case_env.sh").write_text("".join(f"{key}={shlex.quote(value)}\n" for key, value in env.items()), encoding="utf-8")
print(json.dumps({"event": "yam_rgb_dp_eval_cases_prepared", "id": id_case, "ood": ood_case}, sort_keys=True))
PY
# shellcheck source=/dev/null
source "$CASE_ENV_HOST"

export NFS_ROOT CODE_NFS FABRICS_NFS ISAACLAB_NFS ROBOLAB_NFS OFFICIAL_DP_NFS RESULTS_NFS ENV_ROOT ENV_NAME DP_ENV_NAME
export TASK RUN_NAME RUN_DIR_CONTAINER CHECKPOINT_HOST FULL_OBJAVERSE_ASSET_ROOT FULL_OBJAVERSE_MANIFEST_HOST
export FULL_OBJAVERSE_CONTAINER_ASSET_ROOT ID_STABLE_SCENE_HOST ID_EXPECTED_OBJECTS_RESOLVED
export OOD_MANIFEST_HOST OOD_EXPECTED_OBJECTS_RESOLVED OOD_SETTLE_STEPS OOD_SEED
export DEMO_STEPS CAPTURE_INTERVAL FPS RECORD_RGB_WIDTH RECORD_RGB_HEIGHT RECORD_RGB_INTERVAL
export POLICY_IMAGE_HEIGHT POLICY_IMAGE_WIDTH NUM_INFERENCE_STEPS NUM_ACTION_SAMPLES POLICY_SAMPLE_SEED
export ACTION_CHUNK_STEPS POLICY_MAX_JOINT_DELTA POLICY_MAX_GRIPPER_DELTA VALIDATION_REQUIRE_ACCEPTED
export DISABLE_FABRIC PREPARE_YAM_ASSETS YAM_ASSET_PREPARE_LOCK CODE_COMMIT

echo "Running YAM RGB-DP eval suite"
echo "SLURM_JOB_ID=$SLURM_JOB_ID_SAFE"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "RUN_DIR_HOST=$RUN_DIR_HOST"
echo "CODE_NFS=$CODE_NFS"
echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
echo "CHECKPOINT_HOST=$CHECKPOINT_HOST"
echo "ID_STABLE_SCENE_HOST=$ID_STABLE_SCENE_HOST"
echo "ID_EXPECTED_OBJECTS_RESOLVED=$ID_EXPECTED_OBJECTS_RESOLVED"
echo "OOD_MANIFEST_HOST=$OOD_MANIFEST_HOST"
echo "OOD_EXPECTED_OBJECTS_RESOLVED=$OOD_EXPECTED_OBJECTS_RESOLVED"
echo "OOD_FILTER=pool=$OOD_MANIFEST_POOL_SIZE min_xy=$OOD_MIN_XY_RADIUS max_xy=$OOD_MAX_XY_RADIUS min_height=$OOD_MIN_HEIGHT max_height=$OOD_MAX_HEIGHT max_width_p95=$OOD_MAX_GRASP_WIDTH_P95 exclude=$OOD_EXCLUDE_KEYWORDS"
echo "DEMO_STEPS=$DEMO_STEPS"
echo "CAPTURE_INTERVAL=$CAPTURE_INTERVAL"
echo "VALIDATION_REQUIRE_ACCEPTED=$VALIDATION_REQUIRE_ACCEPTED"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ROBOLAB_NFS":/home/lzha/code/RoboLab,"$OFFICIAL_DP_NFS":/official_dp,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,TORCH_SHOW_CPP_STACKTRACES=1,PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc '
    set -euo pipefail
    export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
    export SITE="/envs/$ENV_NAME/site"
    export DP_SITE="/envs/$DP_ENV_NAME/site"
    export PYTHONPATH="$SITE:$DP_SITE:/code:/fabrics/src:/official_dp"
    for d in /IsaacLab/source/*; do
      if [ -d "$d" ]; then
        export PYTHONPATH="$d:$PYTHONPATH"
      fi
    done
    export WANDB_MODE=offline
    mkdir -p "$RUN_DIR_CONTAINER"/{id,ood,ood_settle} /results/logs

    cd /code
    echo "container_host=$(hostname)"
    echo "container_cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
    echo "CODE_COMMIT=${CODE_COMMIT:-unknown}"
    git rev-parse HEAD 2>/dev/null || true
    nvidia-smi || true

    if [[ "$TASK" == *YAM* ]]; then
      YAM_USD=/code/dextrah_lab/assets/yam/yam_mjcf_usd/yam_linear.usd
      YAM_PREPARE_ARGS=(--headless --converter mjcf --robot single)
      if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
        mkdir -p "$(dirname "$YAM_ASSET_PREPARE_LOCK")"
        (
          flock 9
          if [ "$PREPARE_YAM_ASSETS" = "True" ] || { [ "$PREPARE_YAM_ASSETS" = "auto" ] && [ ! -s "$YAM_USD" ]; }; then
            /isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py "${YAM_PREPARE_ARGS[@]}"
          fi
        ) 9>"$YAM_ASSET_PREPARE_LOCK"
      fi
      test -s "$YAM_USD"
    fi

    container_path_arg() {
      local value="$1"
      if [ -z "$value" ]; then
        return 0
      fi
      if [[ "$value" == "$RESULTS_NFS"* ]]; then
        printf "/results%s" "${value#$RESULTS_NFS}"
      elif [[ "$value" == "$CODE_NFS"* ]]; then
        printf "/code%s" "${value#$CODE_NFS}"
      elif [[ "$value" == "$FABRICS_NFS"* ]]; then
        printf "/fabrics%s" "${value#$FABRICS_NFS}"
      elif [[ "$value" == "$ISAACLAB_NFS"* ]]; then
        printf "/IsaacLab%s" "${value#$ISAACLAB_NFS}"
      elif [[ "$value" == "$OFFICIAL_DP_NFS"* ]]; then
        printf "/official_dp%s" "${value#$OFFICIAL_DP_NFS}"
      else
        printf "%s" "$value"
      fi
    }

    bool_arg() {
      local flag="$1"
      local value="$2"
      if [ "$value" = "True" ] || [ "$value" = "true" ] || [ "$value" = "1" ]; then
        printf "%s" "$flag"
      fi
    }

    run_settle_ood() {
      local manifest_container
      manifest_container="$(container_path_arg "$OOD_MANIFEST_HOST")"
      local ood_expected_objects
      local ood_clutter_count
      ood_expected_objects="${OOD_EXPECTED_OBJECTS_RESOLVED:-1}"
      ood_clutter_count=$((ood_expected_objects - 1))
      /isaac-sim/python.sh /code/dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py \
        --task "$TASK" \
        --num_envs 1 \
        --seed "$OOD_SEED" \
        --output_dir "$RUN_DIR_CONTAINER/ood_settle" \
        --video_path "$RUN_DIR_CONTAINER/ood_settle/settle.mp4" \
        --metrics_path "$RUN_DIR_CONTAINER/ood_settle/metrics.json" \
        --stable_scene_output_path "$RUN_DIR_CONTAINER/ood/stable_scene.json" \
        --demo_mode settle \
        --settle_steps "$OOD_SETTLE_STEPS" \
        --capture_interval "$CAPTURE_INTERVAL" \
        --fps "$FPS" \
        --object_asset_manifest_path "$manifest_container" \
        --object_assets_dir "$FULL_OBJAVERSE_CONTAINER_ASSET_ROOT" \
        --max_objects 1 \
        --object_asset_assignment round_robin \
        --object_validate_usd_bounds \
        --tabletop_clutter_asset_manifest_path "$manifest_container" \
        --tabletop_clutter_assets_dir "$FULL_OBJAVERSE_CONTAINER_ASSET_ROOT" \
        --tabletop_clutter_max_objects "$ood_clutter_count" \
        --tabletop_clutter_object_count "$ood_clutter_count" \
        --tabletop_clutter_asset_assignment round_robin \
        --no-tabletop_clutter_validate_usd_bounds \
        --headless \
        $(bool_arg --disable_fabric "$DISABLE_FABRIC")
      test -s "$RUN_DIR_CONTAINER/ood/stable_scene.json"
    }

    run_policy_case() {
      local case_name="$1"
      local seed="$2"
      local stable_scene_host="$3"
      local stable_scene_container
      stable_scene_container="$(container_path_arg "$stable_scene_host")"
      local out_dir="$RUN_DIR_CONTAINER/$case_name"
      local checkpoint_container
      checkpoint_container="$(container_path_arg "$CHECKPOINT_HOST")"
      local policy_seed_args=()
      if [ -n "$POLICY_SAMPLE_SEED" ]; then
        policy_seed_args=(--policy_sample_seed "$POLICY_SAMPLE_SEED")
      fi
      /isaac-sim/python.sh /code/dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py \
        --task "$TASK" \
        --num_envs 1 \
        --seed "$seed" \
        --output_dir "$out_dir" \
        --video_path "$out_dir/policy.mp4" \
        --metrics_path "$out_dir/metrics.json" \
        --stable_scene_path "$stable_scene_container" \
        --demo_mode single_yam_rgb_dp_policy \
        --demo_steps "$DEMO_STEPS" \
        --demo_trajectory_source none \
        --checkpoint "$checkpoint_container" \
        --diffusion_policy_root /official_dp \
        --policy_image_height "$POLICY_IMAGE_HEIGHT" \
        --policy_image_width "$POLICY_IMAGE_WIDTH" \
        --num_inference_steps "$NUM_INFERENCE_STEPS" \
        --num_action_samples "$NUM_ACTION_SAMPLES" \
        --action_chunk_steps "$ACTION_CHUNK_STEPS" \
        --policy_max_joint_delta "$POLICY_MAX_JOINT_DELTA" \
        --policy_max_gripper_delta "$POLICY_MAX_GRIPPER_DELTA" \
        --record_trajectory_dataset \
        --trajectory_dataset_path "$out_dir/trajectory_dataset.npz" \
        --record_rgb_width "$RECORD_RGB_WIDTH" \
        --record_rgb_height "$RECORD_RGB_HEIGHT" \
        --record_rgb_interval "$RECORD_RGB_INTERVAL" \
        --capture_interval "$CAPTURE_INTERVAL" \
        --fps "$FPS" \
        --headless \
        $(bool_arg --disable_fabric "$DISABLE_FABRIC") \
        "${policy_seed_args[@]}"
      test -s "$out_dir/policy.mp4"
      test -s "$out_dir/metrics.json"
      test -s "$out_dir/trajectory_dataset.npz"
    }

    validate_case() {
      local case_name="$1"
      local expected_objects="$2"
      local stable_scene_container="$3"
      set +e
      /isaac-sim/python.sh /code/dextrah_lab/scene_scripts/validate_yam_pick_place_dataset.py \
        --dataset_path "$RUN_DIR_CONTAINER/$case_name/trajectory_dataset.npz" \
        --metrics_path "$RUN_DIR_CONTAINER/$case_name/metrics.json" \
        --stable_scene_path "$stable_scene_container" \
        --output_path "$RUN_DIR_CONTAINER/$case_name/validation_metrics.json" \
        --expected_objects "$expected_objects"
      local status=$?
      set -e
      echo "validation_exit_$case_name=$status"
      if [ "$VALIDATION_REQUIRE_ACCEPTED" = "True" ] || [ "$VALIDATION_REQUIRE_ACCEPTED" = "true" ] || [ "$VALIDATION_REQUIRE_ACCEPTED" = "1" ]; then
        return "$status"
      fi
      return 0
    }

    run_settle_ood
    run_policy_case id 42 "$ID_STABLE_SCENE_HOST"
    run_policy_case ood "$OOD_SEED" "$RESULTS_NFS/evals/${RUN_NAME}/ood/stable_scene.json"
    validate_case id "$ID_EXPECTED_OBJECTS_RESOLVED" "$(container_path_arg "$ID_STABLE_SCENE_HOST")"
    validate_case ood "$OOD_EXPECTED_OBJECTS_RESOLVED" "$RUN_DIR_CONTAINER/ood/stable_scene.json"

    /isaac-sim/python.sh - "$RUN_DIR_CONTAINER" "$CHECKPOINT_HOST" "$CODE_COMMIT" <<'"'"'PY'"'"'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
checkpoint = sys.argv[2]
code_commit = sys.argv[3]

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}

cases = {}
for case_name in ("id", "ood"):
    metrics = read_json(run_dir / case_name / "metrics.json")
    validation = read_json(run_dir / case_name / "validation_metrics.json")
    rgb_dp = metrics.get("rgb_dp_policy_eval") if isinstance(metrics.get("rgb_dp_policy_eval"), dict) else {}
    traj = metrics.get("trajectory_dataset") if isinstance(metrics.get("trajectory_dataset"), dict) else {}
    cases[case_name] = {
        "metrics_path": str(run_dir / case_name / "metrics.json"),
        "video_path": str(run_dir / case_name / "policy.mp4"),
        "dataset_path": str(run_dir / case_name / "trajectory_dataset.npz"),
        "validation_path": str(run_dir / case_name / "validation_metrics.json"),
        "validation_status": validation.get("status"),
        "validation_checks": validation.get("checks"),
        "policy_call_count": rgb_dp.get("policy_call_count"),
        "clipped_step_count": rgb_dp.get("clipped_step_count"),
        "action_min": rgb_dp.get("action_min"),
        "action_max": rgb_dp.get("action_max"),
        "trajectory_dataset": traj,
    }
summary = {
    "run_dir": str(run_dir),
    "checkpoint": checkpoint,
    "code_commit": code_commit,
    "cases": cases,
    "id_case": read_json(run_dir / "id_case.json"),
    "ood_case": read_json(run_dir / "ood_case.json"),
}
(run_dir / "suite_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"event": "yam_rgb_dp_eval_suite_done", "summary_path": str(run_dir / "suite_summary.json")}, sort_keys=True))
PY
  '

echo "Finished. Host artifacts:"
echo "  $RUN_DIR_HOST/id/policy.mp4"
echo "  $RUN_DIR_HOST/ood/policy.mp4"
echo "  $RUN_DIR_HOST/suite_summary.json"
