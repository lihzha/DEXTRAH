# YAM RGB Pick-Place Reproduction Handoff

This note records the exact code, data, checkpoint, and video state for the
single-object YAM RGB diffusion pick-place run as of 2026-07-10. It is intended
to make the `lihzha/DEXTRAH` GitHub branch sufficient to reproduce the data
generation, rebuild the frozen training manifest, resume training, and fetch
the relevant checkpoints and videos.

## Git State

- GitHub remote: `git@github.com:lihzha/DEXTRAH.git`
- Branch: `codex/yam-ground-randomization-20260709`
- Pre-handoff source commit: `32d368ad4289060643ad004b619666930eebb904`
- Production collection commit: `482b1b3c4c2ce856e4ddb0570757e63c03ff1d89`
- Finalizer commit used for the 500-row freeze: `876edb2f`
- Material-matched eval fix: `27addad2`
- Final-frame dual-video fix: `00eb6f85`

Use the branch tip for new reruns. Use the pinned production commit only when
reproducing the exact already-generated collection.

```bash
git clone git@github.com:lihzha/DEXTRAH.git
cd DEXTRAH
git checkout codex/yam-ground-randomization-20260709
git lfs pull
```

## Fixed Cluster Paths

```bash
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
CODE_ROOT=$NFS_ROOT/src/DEXTRAH
RESULTS_ROOT=$NFS_ROOT/results/dextrah
RUN_NAME=yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
DATA_ROOT=$RESULTS_ROOT/dp_bc/yam_pickplace_rgb_policy/$RUN_NAME
SOURCE_MANIFEST=$DATA_ROOT/replacement_source_manifest_500.json
LATEST_REPLACEMENT_MANIFEST=$DATA_ROOT/replacement_source_manifest_711.json
FINAL_FREEZE=$DATA_ROOT/audits/final_0500_20260710T1032Z
FINAL_MANIFEST=$FINAL_FREEZE/curriculum_source_split/manifest_0500.json
```

The 500-row final freeze currently has `500` accepted rows, `342` original
rows, `158` replacement rows, `74` unique target objects, `342` unique source
policy shards, and no duplicate selected slot. The final training manifest
contains `403360` control steps with a source-preserved, object-disjoint
`456/44` train/validation split.

Final randomization report:

```bash
viz-open /home/lzha/code/cluster_results/l401/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z_final500/visualization_source_split/randomization_report.md
```

Viewer URL observed during handoff:
`http://localhost:8765/view?path=cluster_results/l401/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z_final500/visualization_source_split/randomization_report.md`.

## Reproduce Data Generation

Deploy the exact production collection commit into an isolated L40 worktree:

```bash
ssh l401 'bash -s' <<'REMOTE'
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
repo=$NFS_ROOT/src/DEXTRAH
commit=482b1b3c4c2ce856e4ddb0570757e63c03ff1d89
worktree=$NFS_ROOT/src/worktrees/DEXTRAH/yam-ground-randomization-11e3e64e-20260709
git -C "$repo" fetch origin
mkdir -p "$(dirname "$worktree")"
if [ -e "$worktree/.git" ] || [ -f "$worktree/.git" ]; then
  git -C "$worktree" fetch origin
  git -C "$worktree" checkout --detach "$commit"
else
  git -C "$repo" worktree add --detach "$worktree" "$commit"
fi
git -C "$worktree" lfs pull
git -C "$worktree" rev-parse HEAD
REMOTE
```

Launch the first-pass L40 collection with ordinary Slurm jobs:

```bash
ssh l401 'bash -lc "
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
DATA_ROOT=\$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
CODE_NFS=\$NFS_ROOT/src/worktrees/DEXTRAH/yam-ground-randomization-11e3e64e-20260709
cd \$CODE_NFS
SOURCE_MANIFEST=\$DATA_ROOT/replacement_source_manifest_500.json \
DATASET_RUN_NAME=yam_controller_stateobs_v17_ground500_visual_20260709T1418Z \
OUTPUT_ROOT=\$DATA_ROOT \
INDEX_SPEC=0-499 \
MAX_CONCURRENT=10 \
POLL_SECONDS=20 \
SBATCH_TIME=00:15:00 \
JOB_NAME_PREFIX=yv17main_482b \
CODE_COMMIT=482b1b3c4c2ce856e4ddb0570757e63c03ff1d89 \
RENDERING_MODE=quality \
YAM_POLICY_ROBOT_MATERIAL_RANDOMIZATION=True \
YAM_POLICY_OBJECT_MATERIAL_RANDOMIZATION=True \
bash cluster/submit_yam_controller_native_dataset_l401.sh
"'
```

Run recovery and replacement submitters until `find "$DATA_ROOT/records" -name
metadata.json | wc -l` returns `500`:

```bash
ssh l401 'bash -lc "
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
DATA_ROOT=\$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
CODE_NFS=\$NFS_ROOT/src/worktrees/DEXTRAH/yam-ground-randomization-11e3e64e-20260709
python3 \$CODE_NFS/cluster/submit_yam_controller_native_recoveries_l401.py \
  --output-root \$DATA_ROOT \
  --source-manifest \$DATA_ROOT/replacement_source_manifest_500.json \
  --code-nfs \$CODE_NFS \
  --code-commit 482b1b3c4c2ce856e4ddb0570757e63c03ff1d89 \
  --max-concurrent 3 \
  --poll-seconds 30 \
  --sbatch-time 00:15:00 \
  --job-name-prefix yv17rec_482b \
  --control-mode dataset_pose_recovery
"'
```

```bash
ssh l401 'bash -lc "
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
DATA_ROOT=\$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
CODE_NFS=\$NFS_ROOT/src/worktrees/DEXTRAH/yam-ground-randomization-11e3e64e-20260709
DONORS=\$(cat \$DATA_ROOT/object_distinct_donor_indices.txt)
python3 \$CODE_NFS/cluster/submit_yam_controller_native_replacements_l401.py \
  --output-root \$DATA_ROOT \
  --code-nfs \$CODE_NFS \
  --code-commit 482b1b3c4c2ce856e4ddb0570757e63c03ff1d89 \
  --donor-sources \"\$DONORS\" \
  --max-concurrent 2 \
  --poll-seconds 30 \
  --sbatch-time 00:15:00 \
  --job-name-prefix yv17rep_482b \
  --control-mode dataset_pose_recovery
"'
```

## Freeze And Audit Final 500 Rows

The final freeze is deterministic from `records/`, the base 500-row source
manifest, and the latest replacement manifest:

```bash
ssh l401 'bash -s' <<'REMOTE'
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
DATA_ROOT=$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
CODE=$NFS_ROOT/src/worktrees/DEXTRAH/yam-v17-finalizer-876edb2f-20260709
OUT=$DATA_ROOT/audits/final_0500_20260710T1032Z
/usr/bin/env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 "$CODE/dextrah_lab/offline_dp_bc/freeze_yam_controller_native_records.py" \
    --records-root "$DATA_ROOT/records" \
    --base-source-manifest "$DATA_ROOT/replacement_source_manifest_500.json" \
    --replacement-source-manifest "$DATA_ROOT/replacement_source_manifest_711.json" \
    --output-dir "$OUT"
REMOTE
```

Build the final object-disjoint training manifest and randomization report:

```bash
ssh l401 'bash -s' <<'REMOTE'
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
DATA_ROOT=$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z
CODE=$NFS_ROOT/src/worktrees/DEXTRAH/yam-v17-finalizer-876edb2f-20260709
FREEZE=$DATA_ROOT/audits/final_0500_20260710T1032Z
/usr/bin/env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 "$CODE/dextrah_lab/offline_dp_bc/build_yam_controller_native_curriculum.py" \
    --records_root "$FREEZE/records" \
    --output_dir "$FREEZE/curriculum_source_split" \
    --sizes 100 250 500 \
    --expected_count 500 \
    --require_authoritative_visual_replay \
    --require_ground_texture_replay \
    --split_source_manifest "$DATA_ROOT/replacement_source_manifest_500.json" \
    --max_stationary_tcp_steps 60 \
    --stationary_tcp_delta_m 0.00001

/usr/bin/env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 "$CODE/dextrah_lab/offline_dp_bc/visualize_yam_rgb_randomization.py" \
    --manifest "$FREEZE/curriculum_source_split/manifest_0500.json" \
    --results-root "$DATA_ROOT" \
    --output-dir "$FREEZE/visualization_source_split" \
    --grid-count 100 \
    --grid-cols 10 \
    --thumbnail-size 160
REMOTE
```

## Train

Production-scale baseline training was still running on A100 as of the handoff.
The latest healthy v16 run was:

```bash
RUN_NAME=yam_rgb_dp_stateobs_v16_n500_bs80_2m_20260702T050018Z
TRAIN_ROOT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb/$RUN_NAME
```

The corrected v17 100-row pilot used a weight-only EMA initialization from the
v16 checkpoint at step 1,154,781, batch size 80, LR `1e-5`, 500 warmup steps,
100 diffusion inference steps, two 256x256 RGB streams, 24-D robot state,
`n_obs_steps=1`, and no phase/progress or privileged task state:

```bash
ssh a1001 'bash -lc "
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
CODE_NFS=\$NFS_ROOT/src/worktrees/DEXTRAH/yam-v17-train-10c26560-20260709
RUN_NAME=yam_rgb_dp_stateobs_v17_live100_ftema1154781_bs80_20k_20260709T1510Z
MANIFEST=\$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z/audits/live_0100_20260709T1505Z/curriculum_source_split/manifest_0100.json
INIT=\$NFS_ROOT/results/dextrah/dp_bc/yam_pickplace_rgb/yam_rgb_dp_stateobs_v16_n500_bs80_2m_20260702T050018Z/official_dp_train/checkpoints/epoch=0234-val_loss=0.029664.ckpt
cd \$CODE_NFS
MANIFEST=\$MANIFEST \
RUN_NAME=\$RUN_NAME \
INIT_CHECKPOINT=\$INIT \
INIT_MODE=weights \
TARGET_TRAIN_STEPS=20000 \
MAX_TRAIN_STEPS=20000 \
NUM_EPOCHS=100 \
BATCH_SIZE=80 \
VAL_BATCH_SIZE=80 \
JOB_NAME=yv17pilot \
CODE_COMMIT=10c26560 \
bash cluster/submit_yam_rgb_dp_long_train_a100.sh
"'
```

For final v17 training, replace `MANIFEST` with
`$FINAL_FREEZE/curriculum_source_split/manifest_0500.json` and set a longer
target, for example `TARGET_TRAIN_STEPS=100000`.

## Evaluate

Material-matched L40S evals must run from a branch containing `27addad2` and
`00eb6f85`. Use quality rendering, 4,800 uninterrupted dynamics steps, full-rate
scene+wrist video, action chunk 8 unless intentionally testing chunk 1, and
100 diffusion sampling steps.

```bash
ssh l401 'bash -lc "
set -euo pipefail
NFS_ROOT=/lustre/fsw/portfolios/nvr/users/lzha
CODE_NFS=\$NFS_ROOT/src/worktrees/DEXTRAH/yam-v17-dualeval-material-27addad2-20260709
TRAIN_RUN_NAME=yam_rgb_dp_stateobs_v17_live100_ftema1154781_bs80_20k_20260709T1510Z
MONITOR_NAME=\${TRAIN_RUN_NAME}_periodic5k_dual_20260709T1550Z
cd \$CODE_NFS
TRAIN_RUN_NAME=\$TRAIN_RUN_NAME \
MONITOR_NAME=\$MONITOR_NAME \
EVAL_EVERY_STEPS=5000 \
TARGET_TRAIN_STEPS=20000 \
MAX_EVALS=4 \
NUM_STEPS=4800 \
VIDEO_LENGTH=4800 \
ACTION_CHUNK_STEPS=8 \
RENDERING_MODE=quality \
CAPTURE_VIDEO=True \
DUAL_CAMERA_VIDEO=True \
DUAL_CAMERA_VIDEO_FPS=60.0 \
DISABLE_FAILURE_TERMINATIONS=True \
DISABLE_SUCCESS_TERMINATION=True \
STOP_ON_DONE=False \
STOP_ON_BIN_DROP_SUCCESS=False \
SEED=42 \
POLICY_SAMPLE_SEED=42 \
bash cluster/submit_yam_rgb_dp_checkpoint_eval_monitor_l401.sh
"'
```

The step-15,518 pilot eval completed `4,800` steps with no reset and `0/1`
success. The object was not lifted (`max_lift_height=0.000823 m`), so that eval
is a genuine grasp-stage failure under material-matched visuals, not an
eval/train observation mismatch.

```bash
viz-open /home/lzha/code/cluster_results/l401/yam_rgb_dp_v17_pilot_step15518_material_s42_20260709T1716Z/videos/yam-pickplace-rgb-dp-eval-scene-wrist.mp4
```

Viewer URL observed during handoff:
`http://localhost:8765/view?path=cluster_results/l401/yam_rgb_dp_v17_pilot_step15518_material_s42_20260709T1716Z/videos/yam-pickplace-rgb-dp-eval-scene-wrist.mp4`.

## Fetch Artifacts

Lightweight reports and eval videos can be mirrored locally:

```bash
mkdir -p cluster_results/l401/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z_final500
rsync -av l401:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z/audits/final_0500_20260710T1032Z/ \
  cluster_results/l401/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z_final500/

mkdir -p cluster_results/l401/yam_rgb_dp_v17_pilot_step15518_material_s42_20260709T1716Z
rsync -av l401:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/yam_rgb_dp_stateobs_v17_live100_ftema1154781_bs80_20k_20260709T1510Z_periodic5k_dual_20260709T1550Z_step0015518/ \
  cluster_results/l401/yam_rgb_dp_v17_pilot_step15518_material_s42_20260709T1716Z/
```

Large checkpoints are intentionally not tracked in Git. Fetch them explicitly:

```bash
rsync -av a1001:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb/yam_rgb_dp_stateobs_v16_n500_bs80_2m_20260702T050018Z/official_dp_train/checkpoints/latest.ckpt \
  cluster_results/a1001/yam_rgb_dp_stateobs_v16_n500_bs80_2m_latest.ckpt

rsync -av a1001:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb/yam_rgb_dp_stateobs_v17_live100_ftema1154781_bs80_20k_20260709T1510Z/official_dp_train/checkpoints/latest.ckpt \
  cluster_results/a1001/yam_rgb_dp_stateobs_v17_live100_ftema1154781_bs80_20k_latest.ckpt
```

Open local artifacts with:

```bash
viz-open /home/lzha/code/cluster_results/l401/yam_rgb_dp_v17_pilot_step15518_material_s42_20260709T1716Z/videos/yam-pickplace-rgb-dp-eval-scene-wrist.mp4
viz-open /home/lzha/code/cluster_results/l401/yam_controller_stateobs_v17_ground500_visual_20260709T1418Z_live250/randomization_report.md
```
