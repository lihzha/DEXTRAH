# Training With Full Objaverse GraspGen Assets

This document describes the cluster pipeline for training DEXTRAH single-arm
YAM tabletop clutter on the full Objaverse-backed subset supported by the
GraspGen/GraspGen-X data contract.

The important contract is not "all Objaverse objects". It is the intersection
of objects that have:

- a raw Objaverse mesh;
- a converted USD at `USD/<uuid>/<uuid>.usd`;
- a GraspGen prior at `grasp_priors/<uuid>.npz`;
- a finite positive `object_scale` inside that prior.

The single-YAM tabletop clutter task now defaults to
`dextrah_lab/assets/graspgen_objects` and requires GraspGen prior scale for the
target object and tabletop clutter. Production cluster runs should usually pass
an explicit asset manifest path instead of copying a large generated asset tree
into the Git checkout.

## Fixed Cluster Paths

- a1001 login host: `a1001`
- NFS root: `/lustre/fsw/portfolios/nvr/users/lzha`
- DEXTRAH checkout: `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`
- DEXTRAH results: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah`
- DEXTRAH logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah`
- Isaac Lab image: `/lustre/fsw/portfolios/nvr/users/lzha/cache/isaac_lab_2.2.0.sqsh`
- Isaac Lab source: `/lustre/fsw/portfolios/nvr/users/lzha/src/IsaacLab-v2.2.1`
- Isaac Lab venv site: `/lustre/fsw/portfolios/nvr/users/lzha/envs/dextrah-isaaclab/site`

Suggested full asset root:

```bash
ASSET_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full
```

Keep `ASSET_ROOT` outside the repo. The generated meshes, USDs, caches, and
priors are large data artifacts, not source files.

## Step 1: Deploy Exact Training Code

Use Git for source deployment. The cluster checkout must run the same commit
that was validated locally.

```bash
cd /home/lzha/code/DEXTRAH
git status --short --branch
git rev-parse HEAD
git push origin main
```

Then update the a1001 checkout or an agent-owned worktree:

```bash
ssh a1001 'bash -s' <<'REMOTE'
set -euo pipefail
REPO=/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH
cd "$REPO"
git fetch origin
git checkout main
git pull --ff-only origin main
git lfs pull
git rev-parse HEAD
git status --short --branch
REMOTE
```

For parallel agent work, prefer an agent-owned worktree:

```bash
ssh a1001 'bash -s' <<'REMOTE'
set -euo pipefail
REPO=/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH
WORKTREE=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/full_objaverse_assets
COMMIT=<commit-sha>

cd "$REPO"
git fetch origin
mkdir -p "$(dirname "$WORKTREE")"
if [ -e "$WORKTREE/.git" ] || [ -f "$WORKTREE/.git" ]; then
  git -C "$WORKTREE" fetch origin
  git -C "$WORKTREE" checkout --detach "$COMMIT"
else
  git worktree add --detach "$WORKTREE" "$COMMIT"
fi
git -C "$WORKTREE" lfs pull
git -C "$WORKTREE" rev-parse HEAD
REMOTE
```

## Step 2: Materialize Full GraspGen/Objaverse Assets

The DEXTRAH prep script is:

```bash
dextrah_lab/assets/prepare_graspgen_assets.py
```

It downloads/selects UUIDs, fetches raw Objaverse meshes through the GraspGen
object downloader, extracts GraspGen prior shards, writes URDFs, and emits a
manifest. The "all supported objects" mode is `--limit 0`.

Do not run the prep script with bare `python3` on the a1001 login node. The
login Python is too old for the script's CLI and does not have the required
packages. Use the Isaac container wrapper, or run the script inside an
equivalent Python 3.11+ container environment.

Minimal full command:

```bash
cd /lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH
ASSET_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full

python dextrah_lab/assets/prepare_graspgen_assets.py \
  --output_dir "$ASSET_ROOT" \
  --limit 0
```

This creates:

```text
$ASSET_ROOT/manifest.json
$ASSET_ROOT/raw_objaverse/
$ASSET_ROOT/urdf/
$ASSET_ROOT/grasp_priors/
$ASSET_ROOT/splits/selected_uuids.txt
```

Then convert URDFs to USD:

```bash
python dextrah_lab/assets/batch_convert_urdf.py \
  "$ASSET_ROOT/urdf" \
  "$ASSET_ROOT/USD" \
  --headless \
  --skip-existing
```

The current converter loops serially through all object directories inside one
Isaac process. For a full dataset, use the sharded strategy below.

The repo wrapper that configures the container, cache paths, and dependencies is
`cluster/sbatch_prepare_graspgen_assets_1gpu.sh`. Override its partition/time
when running on a1001:

```bash
sbatch --parsable \
  --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
  --time=0-03:50:00 \
  --cpus-per-task=32 \
  --mem=128G \
  --gpus-per-node=1 \
  --export=ALL,RUN_NAME="$RUN_NAME",ASSET_OUTPUT_DIR_HOST="$ASSET_ROOT",ASSET_OUTPUT_DIR_CONTAINER=/results/assets/graspgen_objects_full,LIMIT=0,CONVERT_USD=True,REFRESH_MANIFEST=True,UNUSED_CPU_COUNT=224 \
  cluster/sbatch_prepare_graspgen_assets_1gpu.sh
```

## Fast Sharded Asset Preparation

Use two stages:

1. Prepare raw meshes, URDFs, and grasp priors in object shards.
2. Convert each shard's URDFs to USD in parallel Slurm jobs.

Shard first by GraspGen prior shard, not by a fixed object count. The supported
training split currently contains 8,031 objects across 8 prior shards, roughly
1,000 objects per shard. If a job blindly splits into 256-object chunks, several
tasks may download or contend on the same 800MB-ish prior tar.

Create prior-shard UUID lists from the GraspGen split/intersection:

```bash
ASSET_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full
SHARD_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full_shards
mkdir -p "$SHARD_ROOT/splits"

python3 - <<'PY'
import json
from pathlib import Path
from urllib.request import urlopen

split_url = "https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GraspGen/resolve/main/splits/robotiq_2f_140/train.txt"
index_url = "https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GraspGen/resolve/main/grasp_data/franka_panda/uuid_index.json"
shard_root = Path("/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full_shards")

with urlopen(split_url, timeout=120) as f:
    split = [line.decode().strip() for line in f if line.strip()]
with urlopen(index_url, timeout=120) as f:
    index = json.load(f)

selected = [uuid for uuid in split if uuid in index]
for shard in sorted({int(index[uuid]) for uuid in selected}):
    uuids = [uuid for uuid in selected if int(index[uuid]) == shard]
    path = shard_root / "splits" / f"shard_{shard:03d}.txt"
    path.write_text("\n".join(uuids) + "\n")
    print(f"{path}: {len(uuids)} objects")
PY
```

For each shard:

```bash
SHARD_ID=000
SHARD_DIR=$SHARD_ROOT/shard_$SHARD_ID

python dextrah_lab/assets/prepare_graspgen_assets.py \
  --output_dir "$SHARD_DIR" \
  --uuid_list "$SHARD_ROOT/splits/shard_$SHARD_ID.txt" \
  --limit 0 \
  --unused_cpu_count 224
```

Then convert the shard:

```bash
python dextrah_lab/assets/batch_convert_urdf.py \
  "$SHARD_DIR/urdf" \
  "$SHARD_DIR/USD" \
  --headless \
  --skip-existing
```

After all shards finish, merge by rsyncing shard contents into one asset root
and writing a merged `manifest.json` whose records point to the merged root.
Validate before training. For USD conversion, pass each shard manifest to
`batch_convert_urdf.py --manifest <manifest.json>` so skipped or invalid records
are not converted by a directory-wide scan.

Use `cluster/sbatch_prepare_graspgen_assets_cpu_array.sh` for the CPU-only
stage. It reads `splits/chunk_<id>.txt`, calls
`prepare_graspgen_assets.py --uuid_list ...`, shares prior tar downloads through
a per-prior-shard cache, and validates raw meshes, URDFs, priors, GraspGen
scales, and nondegenerate scaled bounds.

## Slurm Array Shape

Use A100 short partitions for asset prep when the downloader/prior extraction
benefits from the A100 container and shared NFS paths. Use many independent
array tasks rather than one long job.

Recommended initial sizing:

- shard size: either one GraspGen prior shard, currently about 995 to 1,013
  objects, or four chunks per prior shard for 32 CPU array tasks;
- `--cpus-per-task`: 16 to 32;
- `--mem`: 64G to 128G;
- wall time: start with 1 hour for 250-object CPU chunks and 3 hours for
  1,000-object prior shards, then adjust from measured throughput;
- one GPU for USD conversion shards because Isaac conversion starts Kit;
- no GPU is usually required for pure mesh/prior extraction, but using the
  Isaac image may still reserve a GPU depending on wrapper constraints.

Pseudo-array layout:

```bash
#SBATCH --array=0-<num_shards_minus_1>
#SBATCH --account=nvr_lpr_rvp
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-03:50:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G

SHARD_ID=$(printf "%03d" "$SLURM_ARRAY_TASK_ID")
SHARD_DIR="$SHARD_ROOT/shard_$SHARD_ID"
UUID_LIST="$SHARD_ROOT/splits/shard_$SHARD_ID.txt"
```

For maximum throughput:

- run CPU-only prep chunks concurrently up to the account CPU quota. On a1001,
  32 chunks at 32 CPUs/task were limited to 6 concurrent jobs by a 192 CPU/user
  cap;
- set `UNUSED_CPU_COUNT` so the Objaverse downloader uses approximately the
  Slurm CPU allocation. On the probed A100 node, `UNUSED_CPU_COUNT=240` produced
  15 workers with `--cpus-per-task=16`; for 32 workers, use about
  `UNUSED_CPU_COUNT=224`;
- keep each shard in its own output directory and use `--skip-existing` so
  failed conversion shards are restartable;
- reject records with non-finite, zero, or near-zero GraspGen-scaled half
  extents before training. These are degenerate physical objects even if their
  raw Objaverse mesh and GraspGen prior exist;
- only subdivide a prior shard further if a 1,000-object shard does not fit in
  the time limit. If subdividing, keep the prior tar cache shared so the same
  prior shard is not downloaded repeatedly.

## Asset Validation

Run this before training:

```bash
python - <<'PY'
import json
import math
from pathlib import Path
import numpy as np

manifest = Path("$ASSET_ROOT/manifest.json")
payload = json.loads(manifest.read_text())
root = Path(payload.get("asset_root") or ".")
if not root.is_absolute():
    root = (manifest.parent / root).resolve()

missing_usd = []
missing_prior = []
bad_scale = []
bad_extents = []
scales = []

for record in payload["objects"]:
    uuid = record["uuid"]
    usd = root / record["usd_path"]
    prior = root / record["grasp_prior_path"]
    if not usd.is_file():
        missing_usd.append(str(usd))
    if not prior.is_file():
        missing_prior.append(str(prior))
        continue
    with np.load(prior, allow_pickle=False) as data:
        scale = float(data["object_scale"])
    if not math.isfinite(scale) or scale <= 0.0:
        bad_scale.append((uuid, scale))
    extents = record.get("scaled_half_extents", [])
    if (
        not isinstance(extents, list)
        or len(extents) != 3
        or any((not isinstance(v, (int, float))) or (not math.isfinite(float(v))) or float(v) <= 0.0 for v in extents)
    ):
        bad_extents.append((uuid, extents))
    scales.append(scale)

print({
    "manifest": str(manifest),
    "objects": len(payload["objects"]),
    "missing_usd": len(missing_usd),
    "missing_prior": len(missing_prior),
    "bad_scale": len(bad_scale),
    "bad_extents": len(bad_extents),
    "scale_min": min(scales) if scales else None,
    "scale_max": max(scales) if scales else None,
})

if missing_usd or missing_prior or bad_scale or bad_extents:
    raise SystemExit(1)
PY
```

Also run a small DEXTRAH env/render smoke with `max_objects` and
`tabletop_clutter_max_objects` capped to 32 or 128 before using the full
manifest.

## Step 3: Train Against The Full Manifest

Prefer explicit asset overrides in the training command:

```bash
ASSET_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full
RUN_NAME=single_yam_full_objaverse_$(date +%Y%m%d_%H%M%S)

python dextrah_lab/rl_games/train.py \
  --task Dextrah-Single-YAM-Tabletop-Clutter-Grasp \
  --num_envs 1024 \
  --device cuda:0 \
  --max_iterations <epochs> \
  env.object_asset_manifest_path="$ASSET_ROOT/manifest.json" \
  env.tabletop_clutter_asset_manifest_path="$ASSET_ROOT/manifest.json" \
  env.max_objects=0 \
  env.tabletop_clutter_max_objects=0
```

Use the A100 training wrapper for production:

- 8 GPUs per node;
- A100 short partitions;
- checkpoint/resume enabled;
- `DEXTRAH_LOG_ROOT` under results, not the shared source checkout;
- `DEXTRAH_RUN_NAME` set;
- resolved `env.yaml` and `agent.yaml` saved next to logs.

## What To Inspect During Training

Do not judge success from Slurm state alone. Inspect:

- `params/env.yaml` for resolved asset paths and `require_graspgen_scale`;
- `multi_object_asset_summary.scale_sources` if emitted by render/eval jobs;
- loss/reward curves, termination reasons, reset failures, action statistics;
- representative rollout videos;
- object-specific success/failure rates when available;
- checkpoints and resume state.

## Current Known State

As of 2026-06-17:

- Local `main`, `origin/main`, and the a1001 checkout include the
  single-YAM Objaverse-scale defaults, this pipeline doc, and the CPU array
  wrapper through commit `abe26b1`.
- The exact repo default path
  `dextrah_lab/assets/graspgen_objects/manifest.json` is absent locally and on
  a1001.
- Step 2 metadata probe on a1001 found `8,031` supported objects in the
  `robotiq_2f_140/train.txt` split, all present in the Franka Panda GraspGen
  prior index. The supported set is distributed across 8 prior shards:
  `996`, `1013`, `1013`, `1007`, `1004`, `999`, `995`, and `1004` objects.
- Bounded a1001 asset probe `29213914` created
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/full_objaverse_probe_20260617_150433/manifest.json`
  with 8 objects, 0 missing USDs, 0 missing priors, and 0 bad scales. Slurm
  elapsed time was `00:02:45`, including first-time prep dependency install,
  raw object download, prior shard download, URDF generation, serial USD
  conversion, and manifest refresh.
- Full CPU-only prep array `29214576` used 32 chunks under
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects_full_cpu_20260617_153051`.
  All 32 tasks completed with exit code 0. Per-task elapsed time was about
  `00:09:34` to `00:20:27`; account CPU quota limited concurrency to 6 tasks,
  so the full CPU stage took about 1.3 hours after launch. The stage produced
  8,031 unique records with all raw mesh, URDF, and prior paths present.
- Aggregate validation found 11 records with a zero scaled half extent. Future
  prep runs skip these records, and the runtime loader defensively skips any
  invalid bounds. Use the filtered set for USD conversion and training.
- Earlier l401 prep/conversion references using the same wrapper completed 3
  objects in `00:01:49`, 16 objects in `00:02:11`, and 32 objects in
  `00:03:11`. A full prior-shard job of about 1,000 objects should be budgeted
  at roughly 1.5 to 3 hours until a larger shard probe confirms throughput.
- Usable prepared subsets exist on a1001, for example:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z/manifest.json`.
- That 32-object subset has USDs and priors present and can be used as a
  smoke-test asset bundle, but it is not the full supported dataset.

Estimated full materialization time with multiprocessing:

- CPU-only raw/URDF/prior prep: with the observed a1001 CPU quota, budget about
  1.5 hours plus queue wait for 32 chunks. If all 32 chunks could run
  simultaneously, the measured per-task runtime suggests about 20 to 30 minutes
  plus queue wait.
- USD conversion still needs a GPU/Isaac array measurement. Start with 32 GPU
  shard jobs using `batch_convert_urdf.py --manifest`; budget 1 to 3 hours for
  the first full conversion pass until measured.
- Serial full materialization is not recommended and will not fit the A100 short
  partition limit.
- Storage is object-dependent. Based on existing 8/16/32-object probes, reserve
  at least several hundred GB for raw meshes, URDFs, USDs, logs, and caches; use
  1TB free space as the safer target before starting the full dataset.
