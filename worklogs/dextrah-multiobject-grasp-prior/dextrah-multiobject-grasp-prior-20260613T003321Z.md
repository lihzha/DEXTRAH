# Worklog - dextrah-multiobject-grasp-prior / dextrah-multiobject-grasp-prior-20260613T003321Z

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z
- branch: codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z
- base_commit: cac41fc47ce3e002a4c1b6c0afce1d6b971e18c9
- created: 2026-06-13T00:33:27Z

## 2026-06-13 - Local implementation and environment validation

### Scope

- Added a Franka multi-object GraspGen grasp task registered as `Dextrah-Franka-Multi-Object-Grasp`.
- Reused the existing Franka cube teacher task structure, reward path, RL-Games config style, and grasp-prior reset pipeline.
- Added object conditioning features to the observation, increasing policy and critic observations from 72 to 80.
- Confirmed the existing Franka cube task already raises the Franka base to `robot_base_z=0.27`; this avoids the low-base/fingertip-near-table issue seen with the inherited star-task base height.

### Files

- `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/`
  - new task package, env cfg, env implementation, Gym registration, and RL-Games teacher config.
- `dextrah_lab/assets/prepare_graspgen_assets.py`
  - prepares a GraspGen object subset from the NVIDIA download script and HF split, writes scaled object metadata and Franka grasp priors.
- `dextrah_lab/assets/batch_convert_urdf.py`
  - patched for Isaac Lab 2.3 converter compatibility while preserving existing conversion behavior.
- `dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py`
  - standalone validation script for asset loading, scale correctness, reset correctness, grasp-prior reset, and rollout sanity.
- `cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`
  - cluster wrapper for validation.
- `cluster/sbatch_train_teacher_8gpu.sh`
  - added multi-object task overrides and GraspGen asset/prior environment variables.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  - factored grasp-prior object size/open-width hooks so multi-object can use per-grasp contact widths without changing cube behavior.
- `README.md`
  - added workflow commands for asset preparation, conversion, validation, and teacher launch.

### Local Debug Assets

- Prepared a two-object GraspGen subset under ignored local path:
  - `local_results/graspgen_objects_debug`
- UUIDs:
  - `7195ed3346a445448308febe833c180a`, scale `0.0100882458`
  - `1d489db9cdc24161a7537926a20bb17b`, scale `0.0105738317`
- Downloaded/used:
  - GraspGen object downloader from `https://github.com/NVlabs/GraspGen/blob/main/scripts/download_objects.py`
  - Robotiq split from `https://huggingface.co/datasets/nvidia/PhysicalAI-Robotics-GraspGen/blob/main/splits/robotiq_2f_140/train.txt`
  - Franka grasp prior index and shard data from `grasp_data/franka_panda`
- Regenerated prior `.npz` files after filtering non-finite contact widths; both debug objects now have finite `grasp_width` entries.

### Validation

- Static checks:
  - `python3 -m py_compile ...` passed for modified/new Python files.
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh` passed.
- Asset preparation in `nvcr.io/nvidia/isaac-lab:2.3.2`:
  - `prepare_graspgen_assets.py --limit 2 --prefer_single_shard`
  - `batch_convert_urdf.py ... --headless`
  - `prepare_graspgen_assets.py --skip_object_download --overwrite` after conversion to update manifest/prior metadata.
- Isaac validation in `nvcr.io/nvidia/isaac-lab:2.3.2`:
  - task: `Dextrah-Franka-Multi-Object-Grasp`
  - envs: 2
  - steps: 40
  - grasp-prior reset cycles: 2
  - metrics: `local_results/franka_multi_object_validate_debug/metrics.json`
  - result: `passed=true`

### Validation Results

- Gym registration exists.
- Two unique objects assigned across two envs.
- USD assets exist and load.
- Object scales are finite and positive.
- Spawn/reset root heights place object bottoms on the table.
- Observation tensors are finite with shape `[2, 80]`.
- Franka base height is `0.27` and fingertips clear the table after reset.
- Grasp-prior reset attempts all envs, has finite commanded open width, and produced mean success `0.75` over the debug cycles.
- Rollout for 40 random-action steps had finite observations/rewards, no immediate termination, and no done events.

### Notes / Follow-Up

- Video-enabled validation was attempted but stalled in the local headless Docker render path. The numeric Isaac validation completed and wrote passing metrics; no video artifact was retained.
- Full-dataset asset preparation should run on the cluster by dropping `--limit` and using the same asset preparation plus conversion flow from the README.
- No cluster training was launched in this step. Next recommended step is cluster full-subset validation, then teacher training once the full asset set is staged.

## 2026-06-13 - Resume into cluster phase

Goal:
- Continue beyond the local environment-validation gate into cluster staging and training.

Analysis:
- The previous stop was not caused by a code blocker. It was a conservative pause after the "first step" validation milestone and before long-running cluster asset staging/training.
- The next phase should commit/push the implementation, deploy an agent-owned cluster worktree, stage GraspGen assets on remote storage, run cluster validation, then launch teacher training if validation passes.

Next:
- Commit source changes locally.
- Push the agent branch.
- Create/update an agent-owned remote worktree.
- Run remote GraspGen asset staging/conversion and validation before A100 teacher training.

## 2026-06-13 - Add cluster asset staging wrapper

Goal:
- Make GraspGen object download, prior extraction, URDF-to-USD conversion, and manifest validation reproducible as a Slurm job.

Change:
- Added `cluster/sbatch_prepare_graspgen_assets_1gpu.sh`.
- Documented the cluster asset-staging command in `README.md`.

Validation:
- `bash -n cluster/sbatch_prepare_graspgen_assets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`

Next:
- Commit/push this wrapper.
- Deploy the updated commit to an agent-owned `l401` worktree.
- Launch a small cluster asset-staging smoke before the full `LIMIT=0` staging run.

## 2026-06-13 - Cluster asset staging smoke launch

Goal:
- Prove GraspGen asset staging works under the cluster Isaac Lab container before running the full object split.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-20260613T003321Z
- local_commit: c5312e5a661733aa72d3ecc3cd91972771e914d5
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_commit: c5312e5a661733aa72d3ecc3cd91972771e914d5
- deployment_note: canonical cluster checkout could not fetch GitHub due missing SSH credentials; deployed through an agent-owned bare Git mirror pushed over SSH with LFS smudge disabled.

Command / Job:
- command: `LIMIT=4 OVERWRITE=True CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z sbatch --export=ALL cluster/sbatch_prepare_graspgen_assets_1gpu.sh`
- job_id: 1028833
- run_name: `franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1028833.out`

Result:
- status: passed
- metrics/artifacts: 4 objects downloaded, 4 USD files generated, manifest at `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json`
- key evidence: log reported `DEXTRAH_GRASPGEN_ASSET_STAGE_SUMMARY {"missing_usd_count": 0, "objects": 4}` and `GraspGen Asset Preparation Done`.

Analysis:
- Cluster dependency installation and external downloads work from the L40 job container.
- USD conversion works on `pool0-00003`; the non-fatal Warp CUDA warning matches known Isaac cluster behavior.

Next:
- Run cluster environment validation against the smoke manifest with video disabled.

## 2026-06-13 - Cluster environment validation smoke launch

Goal:
- Validate that the multi-object Franka environment loads the cluster-staged GraspGen assets correctly and remains RLable under the cluster Isaac Lab container.

Command / Job:
- command: `NUM_ENVS=4 NUM_STEPS=80 MAX_OBJECTS=4 CAPTURE_VIDEO=False GRASP_PRIOR_RESET_ENABLED=True OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --export=ALL cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`
- job_id: 1028834
- run_name: `franka_multi_env_validate_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223735`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_env_validate_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223735/metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_1028834.out`

Result:
- status: passed
- metrics/artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_env_validate_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223735/metrics.json`
- key evidence: `passed=true`, no failed checks, obs shape `[4, 80]`, reset `root_z_error_max=0.0`, grasp-prior mean success `0.5`, rollout completed 80 steps with `done_count=0`.

Analysis:
- Cluster-staged GraspGen USD assets load correctly into the vectorized Franka multi-object environment.
- Reset geometry and grasp-prior reset behavior remain valid on the cluster container.
- The smoke asset job revealed the Objaverse downloader sees the full host CPU count inside the container and used 200 workers despite a 32-CPU Slurm allocation; reduce the wrapper default worker count before full staging.

Next:
- Patch `UNUSED_CPU_COUNT` default for full staging to avoid oversubscribing the node.
- Commit/push/deploy the wrapper patch.
- Launch full `LIMIT=0` asset staging on `l401`.

## 2026-06-13 - Make full USD conversion resumable

Goal:
- Avoid restarting full GraspGen USD conversion from zero if a long cluster run is interrupted.

Change:
- Added `--skip-existing` to `dextrah_lab/assets/batch_convert_urdf.py`.
- Wired `cluster/sbatch_prepare_graspgen_assets_1gpu.sh` to pass `--skip-existing` by default during conversion.
- Documented that reruns can resume in the same asset output directory.

Next:
- Commit/push/deploy this patch.
- Launch full `LIMIT=0` asset staging with a longer `batch_long` walltime.

## 2026-06-13 - Full GraspGen asset staging launch

Goal:
- Download, prepare, convert, and validate the full Robotiq split object set with Franka GraspGen priors on cluster storage.

Version Control:
- local_commit: f61e1a1e6c02ea2d3c82a3b60bde102b5920393e
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_commit: f61e1a1e6c02ea2d3c82a3b60bde102b5920393e

Command / Job:
- command: `LIMIT=0 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z sbatch --time=3-00:00:00 --export=ALL cluster/sbatch_prepare_graspgen_assets_1gpu.sh`
- job_id: 1028836
- run_name: `franka_multi_graspgen_assets_full_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_224052`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_assets_full_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_224052`
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_assets_full_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_224052/manifest.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1028836.out`

Result:
- status: failed
- metrics/artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_env_render_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_225022/metrics.json`
- key evidence: `render_check_frames_nonblank` failed because frame 0 was black (`dynamic_range=0`, `mean_value=0`) while frame 1 was nonblank (`dynamic_range=254`, `mean_value=209.6`).
- local artifact inspected: `local_results/render_smoke_1028838/frame_0001.png`; it shows the table, Franka, and a small rendered object.

Analysis:
- Rendering is functional after the first frame, but the validator was too strict because it scored the initial black warmup frame.
- This should be treated as a validator/render-warmup issue, not a physics/env failure.

Next:
- Add render warmup frames before scored render checks.
- Rerun rendered validation smoke.

## 2026-06-13 - Add render warmup before scored frames

Goal:
- Make render validation robust to Isaac's initial black RGB frame while still requiring scored frames to be nonblank.

Change:
- Added `--render_warmup_frames` to the validator.
- Added `RENDER_WARMUP_FRAMES` to the cluster validation wrapper.

Next:
- Commit/push/deploy the warmup patch.
- Rerun `RENDER_CHECK=True` smoke validation.

## 2026-06-13 - Rendered validation smoke rerun

Goal:
- Verify render check passes after discarding initial warmup frames.

Version Control:
- local_commit: 52d4d4a3c59b2d683a35931d79d9da103737e201
- remote_commit: 52d4d4a3c59b2d683a35931d79d9da103737e201

Command / Job:
- command: `RENDER_CHECK=True RENDER_CHECK_FRAMES=2 RENDER_WARMUP_FRAMES=2 CAPTURE_VIDEO=False NUM_ENVS=4 NUM_STEPS=40 MAX_OBJECTS=4 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --export=ALL cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`
- job_id: 1028839
- run_name: `franka_multi_env_render_smoke2_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_225336`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_env_render_smoke2_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_225336/metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_1028839.out`

Result:
- status: failed validation; artifacts fetched and encoded locally.
- local_artifacts: `local_results/video_smoke_1028874/{reset_settle,perturbation,grasp_contact}.mp4`
- metrics:
  - overall `passed=false`
  - `reset_settle`: `bottom_clearance_min=-0.1134`, `object_xy_delta_max=0.6423`, `object_center_z_max=1.2715`, `object_speed_max=3.0223`
  - `perturbation`: `bottom_clearance_min=-0.0540`, `object_xy_delta_max=0.0270`, `object_angular_speed_max=45.7303`
  - `grasp_contact`: `bottom_clearance_min=-0.1084`, `selected_lift_height_max=0.0`, `selected_max_finger_dist_min=0.1473`

Analysis:
- The environment is not yet validated. The rendered frames show a thin object drifting on reset and a selected grasp-contact case where the object is visibly below the gripper instead of cleanly captured.
- The previous numeric rollout checks were insufficient because they did not render physical contact behavior or per-object reset stability.
- The failure likely combines missing explicit imported-object collision/material settings, broad cube-derived grasp-prior quality checks that are too permissive for non-cube geometries, and a validator visibility gap: the video camera follows one env while metrics aggregate failures across all four envs.

Next:
- Patch object USD spawn to set explicit collision offsets and low-bounce/high-friction physics material, matching the cube task.
- Split video validation into object-only reset/perturbation and grasp-prior-contact scenarios, and report per-env/per-object metrics so every failing object is visible.
- Rerun the 4-object smoke videos before any training.

## 2026-06-13 - Full GraspGen asset staging blocked by quota

Goal:
- Continue staging the full GraspGen object set on l401 for later scale-up.

Command / Job:
- job_id: 1028836
- run_name: `franka_multi_graspgen_assets_full_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_224052`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_assets_full_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_224052`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1028836.out`

Result:
- status: cancelled after quota failure.
- evidence: object download logged `[Errno 122] Disk quota exceeded` around batch 85/804; the job then continued into large grasp-shard downloads and was cancelled with `scancel 1028836`.
- partial_size: about `2.6G` in the full staging run directory at cancellation time.

Analysis:
- Full-set staging is blocked by the user's/project's quota policy, not by the environment code. The 4-object smoke manifest remains available for environment debugging.

Next:
- Do not relaunch full staging until storage is freed or the staging/cache path is redirected to a quota-safe location.

## 2026-06-13 - Add physical-behavior video validator

Goal:
- Produce explicit video evidence for the three environment behaviors requested by the user:
  reset robustness, perturbation dynamics, and grasp-prior contact/lift.

Change:
- Added `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`.
- Added `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`.
- The script writes PNG frame sequences and `video_metrics.json` for:
  - `reset_settle`: repeated resets followed by zero-action settling; checks table penetration, drift, and dones.
  - `perturbation`: writes object root velocities, records response; checks finite bounded motion, no table sinking, no out-of-workspace behavior.
  - `grasp_contact`: uses grasp-prior reset plus action warmstart to approach/close/lift; checks no table penetration, finger clearance, contact-distance sanity, and no dones.
- Documented the video validation command in `README.md`.

Analysis:
- The previous `--render_check` was necessary but insufficient: it showed nonblank render frames but not the physical failure modes that matter for RL readiness.
- These videos are now an explicit pre-training gate. Training remains blocked until the video validator passes and the resulting frames/videos are inspected.

Next:
- Run syntax checks.
- Commit/push/deploy.
- Launch the video validator on the 4-object smoke manifest first.
- Fetch frames, encode MP4s locally with `ffmpeg`, inspect them, and then run equivalent validation on the full manifest after full asset staging finishes.

## 2026-06-13 - Physical-behavior video smoke launch

Goal:
- Generate the three requested behavior videos on the 4-object staged smoke manifest.

Version Control:
- local_commit: 7ae5ca7c02463a610fdf35f94105c84bb7b09bf5
- remote_commit: 7ae5ca7c02463a610fdf35f94105c84bb7b09bf5

Command / Job:
- command: `RESET_CYCLES=2 SETTLE_STEPS=48 PERTURB_STEPS=64 GRASP_STEPS=72 CAPTURE_INTERVAL=2 MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --export=ALL cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: 1028874
- run_name: `franka_multi_video_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_230031`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_230031`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_230031/video_metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028874.out`

Result:
- status: failed diagnostic.
- Generated reset/perturbation/grasp-contact videos, but user inspection identified physical issues:
  - `grasp_contact`: object moved after initialization because it was not initialized in a stable pose; robot started in a weird pose and shook.
  - `perturbation`: robot was initialized too close to the object.
  - `reset_settle`: object was static within the video, but changed between resets as expected.

Analysis:
- The video validator needed to test object-only reset/perturbation separately from grasp-prior robot reset.
- Grasp contact needed to settle the object first, then compose the robot reset from the settled object root pose.
- The user requested raising Franka base z by `+0.2 m` before rerunning video validation.

Next:
- Fix `/home` quota first, route downloads to Lustre, raise the base, and revise the validator semantics before rerunning.

## 2026-06-13 - Raised-base 4-object video smoke launch

Goal:
- Validate the user-requested behavior videos after the Lustre cache fix, Franka base +0.2 m change, and corrected reset/grasp-contact semantics.

Hypothesis:
- Raising the base to `robot_base_z=0.47` and resetting grasp contact after object settling should remove the low-gripper/wobbly-start issue.
- Running reset/perturbation without grasp-prior robot reset should keep the robot away from the object until intended motion.
- Measuring reset drift from the post-warmup pose should avoid falsely treating expected between-reset randomization as instability.

Version Control:
- local_commit: `5a9a5d85847ea6a97435f2069610d5f180644c4c`
- remote_commit: `5a9a5d85847ea6a97435f2069610d5f180644c4c`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=120 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=16 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --partition=batch --time=0-00:45:00 --export=ALL,CODE_NFS=<remote_worktree>,CODE_COMMIT=<commit>,RUN_NAME=<run> cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028877`
- run_name: `franka_multi_video_cachefix_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233314`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_cachefix_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233314`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_cachefix_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233314/video_metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028877.out`

Result:
- status: cancelled diagnostic.
- Slurm state: `CANCELLED by 158351`, elapsed `00:02:32`.
- Produced `reset_settle=96` frames and `perturbation=48` frames, then stopped making progress before any `grasp_contact` frames.
- Last useful log line was the second environment `Setting seed: 42`; no output or artifact modification after `2026-06-12 23:34:17 -0700`.

Analysis:
- The partial output showed the first two scenarios progressing, but the script hung when it closed the object-only Gym env and created a second grasp-prior env in the same Isaac app process.
- This is a validator lifecycle issue, not a pass/fail signal for grasp-contact physics.

Next:
- Patch the validator to create one grasp-prior-loaded environment, temporarily disable `_grasp_prior_reset_enabled` for reset/perturbation, and reuse the same simulator for grasp-contact.

## 2026-06-13 - Single-environment video validator patch

Goal:
- Fix the video validator lifecycle hang before rerunning grasp-contact evidence generation.

Hypothesis:
- Creating a second Gym/Isaac environment after closing the first one inside the same Isaac app process can hang during scene setup.
- A single environment with grasp priors loaded can still test object-only reset/perturbation by disabling `_grasp_prior_reset_enabled` at runtime, because the warmstart and action-prior paths already gate on that flag.

Change:
- Patched `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` to create one grasp-prior-loaded environment.
- For `reset_settle` and `perturbation`, the validator temporarily disables `_grasp_prior_reset_enabled`.
- For `grasp_contact`, it re-enables the prior and reuses the same settled-object grasp reset path.
- Added explicit per-scenario progress prints for cluster monitoring.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` passed.
- `git diff --check` passed.

Next:
- Commit, deploy to the l401 agent worktree, and relaunch the 4-object raised-base video smoke.

## 2026-06-13 - Single-env 4-object video smoke launch

Goal:
- Rerun the requested reset-settle, perturbation, and grasp-contact videos with the single-environment validator fix.

Version Control:
- local_commit: `79805365f95229725cdcf7d683c20b673927af66`
- remote_commit: `79805365f95229725cdcf7d683c20b673927af66`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=120 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=16 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --partition=batch --time=0-00:45:00 --export=ALL,CODE_NFS=<remote_worktree>,CODE_COMMIT=<commit>,RUN_NAME=<run> cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028881`
- run_name: `franka_multi_video_singleenv_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233822`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_singleenv_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233822`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_singleenv_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233822/video_metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028881.out`

Result:
- status: running/queued; monitoring in progress.

## 2026-06-13 - Grasp-contact validation failure and contact-aware reset patch

Goal:
- Keep the latest multi-object reset branch off `main` until the rendered grasp-contact validation is physically correct.

Result:
- `origin/main` already contains the initial multi-object integration through `8bad95c`, but not the latest reset/grasp-contact fixes.
- Validation job `1029064` ran commit `3292cdb4d0b088a506fd29d55b8675e3ecfa20ee` with `GRASP_RESET_MIN_WIDTH=0.02`, `GRASP_RESET_MIN_PREGRASP_Z=0.70`, and the cached stable poses from job `1028898`.
- `reset_settle` passed: `object_xy_delta_max=7.28e-05m`, `bottom_clearance_min=-0.00405m`.
- `perturbation` passed: `object_xy_delta_max=0.1286m`, `bottom_clearance_min=-0.00626m`.
- `grasp_contact` failed: selected object `96ae0ff853734df0b10a827307949c87`, sample `1039`, `selected_lift_height_max=0.00908m` vs threshold `0.12m`, `selected_max_finger_dist_min=0.1445m`.

Analysis:
- Representative frames from `1029064` showed no object teleport, no table penetration, and no robot/object penetration, but the gripper was reset around a poor dynamic grasp and did not lift the long thin object.
- Inspecting the raw GraspGen record showed the selected contact axis is consistent with the `panda_hand` frame, and the DEXTRAH EE offset lands near the contact midpoint. This is not a frame identity bug.
- The remaining failure is candidate quality: for elongated objects, scoring only the hand/tool pose against the object bounding center can select contact locations that are geometrically valid but dynamically weak.

Change:
- Patched `dextrah_lab/assets/prepare_graspgen_assets.py` to preserve filtered `contact_locations` in the per-object Franka prior `.npz`.
- Patched `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py` to load optional contact locations, sample them with grasp candidates, choose pregrasp direction against the contact midpoint, and score/gate candidates using contact midpoint distance plus grasp width while preserving fallback behavior for old priors.

Validation:
- local: `python3 -m py_compile dextrah_lab/assets/prepare_graspgen_assets.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `git diff --check`

Next:
- Commit and deploy the contact-aware code to l401.
- Regenerate the 4-object smoke manifest under `/lustre` so the `.npz` priors include contact locations.
- Rerun the three-video validation before merging the newest reset branch to `main` or launching RL training.

## 2026-06-13 - Contact-enriched smoke asset regeneration launch

Goal:
- Regenerate the same 4-object smoke manifest with contact-enriched Franka grasp prior `.npz` files.

Version Control:
- local_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- push: pushed to `origin/codex/multiobject-training-yaw-20260613`
- remote_deploy: transferred Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_contact_reset_2d7f495.bundle`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Validation:
- local: `python3 -m py_compile dextrah_lab/assets/prepare_graspgen_assets.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/assets/prepare_graspgen_assets.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- remote: `bash -n cluster/sbatch_prepare_graspgen_assets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`

Command / Job:
- command: `RUN_NAME=franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029 ASSET_OUTPUT_DIR_HOST=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029 ASSET_OUTPUT_DIR_CONTAINER=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029 LIMIT=4 UUIDS="7195ed3346a445448308febe833c180a 1d489db9cdc24161a7537926a20bb17b 96ae0ff853734df0b10a827307949c87 30700bc210844bdc991a5ccf16b6379f" CODE_NFS=<remote_worktree> CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_prepare_graspgen_assets_1gpu.sh`
- job_id: `1029065`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1029065.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029`
- status: running on `pool0-00018`.

Next:
- Inspect `manifest.json` and the four prior `.npz` files for `contact_locations`.
- Rerun rendered reset/perturbation/grasp-contact validation using this new manifest.

## 2026-06-13 - Contact-aware rendered validation launch

Goal:
- Verify the contact-aware prior scoring fixes the rendered grasp-contact failure while preserving reset-settle and perturbation behavior.

Result:
- Smoke asset job `1029065` completed successfully with manifest `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json`.
- The four prior `.npz` files include `contact_locations` and `grasp_width`; examples:
  - `96ae0ff853734df0b10a827307949c87.npz`: `grasps_object=(1249,4,4)`, `contact_locations=(1249,2,3)`, `grasp_width=(1249,)`.
  - `7195ed3346a445448308febe833c180a.npz`: `grasps_object=(714,4,4)`, `contact_locations=(714,2,3)`, `grasp_width=(714,)`.

Command / Job:
- command: `RUN_NAME=multiobject_contactscore_2d7f495_20260613_153242 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False GRASP_RESET_ATTEMPTS=128 GRASP_RESET_MIN_PREGRASP_Z=0.70 GRASP_RESET_CANDIDATE_COUNT=256 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.55 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=80 GRASP_STEPS=120 CODE_NFS=<remote_worktree> CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e sbatch --parsable --partition=batch --time=0-00:30:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029097`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029097.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_2d7f495_20260613_153242`
- status: submitted.

Next:
- Inspect `video_metrics.json`, representative frames, and videos before deciding whether to merge or continue patching.

## 2026-06-13 15:13 PDT - Min-width strict-topdown grasp-contact validation launch

Goal:
- Validate the current multi-object reset path after adding `grasp_prior_reset_min_width=0.008`, using cached settled poses so the robot reset is aligned to the actual object pose used by simulation.

Hypothesis:
- Rejecting near-zero-width priors should avoid impossible Panda clamp candidates while strict top-down filtering and center-distance gating continue to prevent side/rim grasps.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `3292cdb4d0b088a506fd29d55b8675e3ecfa20ee`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `3292cdb4d0b088a506fd29d55b8675e3ecfa20ee`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False OBJECT_STABLE_POSE_ALLOW_MISSING=False OBJECT_RESET_SETTLE_STEPS=0 GRASP_OBJECT_SETTLE_STEPS=0 RENDER_WARMUP_FRAMES=0 GRASP_RESET_ATTEMPTS=96 GRASP_RESET_MIN_PREGRASP_Z=0.70 GRASP_RESET_CANDIDATE_COUNT=256 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.55 GRASP_RESET_MIN_WIDTH=0.008 GRASP_CONTACT_SCORE_STEPS=80 GRASP_STEPS=120 GRASP_WARMSTART_CLOSE_WIDTH=0.025 GRASP_WARMSTART_LIFT_ACTION_Z=0.30 CAPTURE_INTERVAL=2 CODE_COMMIT=3292cdb4d0b088a506fd29d55b8675e3ecfa20ee sbatch --partition=batch --time=0-00:30:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029063`
- run_name: `multiobject_min_width_top07_3292cdb_20260613_151351`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_min_width_top07_3292cdb_20260613_151351`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029063.out`
- expected_artifacts: `reset_settle.mp4`, `perturbation.mp4`, `grasp_contact.mp4`, `video_metrics.json`

Next:
- Submit the job on l401, monitor logs/metrics/videos, then either accept the environment gate or patch the grasp-contact reset/warmstart again before RL training.

## 2026-06-13 15:18 PDT - Strict min-width validation failed

Goal:
- Determine whether the min-width gate fixes the remaining grasp-contact validation failure.

Command / Job:
- job_id: `1029063`
- run_name: `multiobject_min_width_top07_3292cdb_20260613_151351`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_min_width_top07_3292cdb_20260613_151351`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029063.out`

Result:
- status: failed only `grasp_contact`; Slurm state `FAILED`, exit code `1:0`, elapsed `00:01:27`.
- `reset_settle` passed with `object_xy_delta_max=7.28e-05m`, `bottom_clearance_min=-0.00405m`.
- `perturbation` passed with `object_xy_delta_max=0.1286m`, `bottom_clearance_min=-0.00626m`.
- `grasp_contact` selected object `96ae0ff853734df0b10a827307949c87`, sample `14`, `selected_pregrasp_offset_dir_z=0.746`, and `selected_open_width_margin=0.0704`, implying sampled contact width about `0.0096m`.
- Contact metrics failed: `selected_lift_height_max=0.00298m` vs `0.12m`; `selected_max_finger_dist_min=0.104m`; `selected_done_count=0`; no table penetration.
- Representative frames in `/tmp/dextrah_val_1029063/grasp_contact/` show no obvious penetration or teleporting, but the gripper stays offset and does not clamp/lift the thin stem.

Analysis:
- The failure is not passive object reset or perturbation physics; it is grasp-prior candidate quality.
- Inspecting the raw GraspGen JSON for sample `14` showed `T_object_panda_hand` hand origin is about `0.105m` from the two contact points. Current quality scoring relies heavily on hand/tool-origin distance to object center and object-size-normalized tip proxies, which is too loose for elongated/thin objects.
- The selected contact width is only about `9.6mm`; a stronger minimum width gate may reject these unstable stem grasps without a code patch.

Next:
- Rerun the same validation with `GRASP_RESET_MIN_WIDTH=0.02` before deciding whether to add contact-location-aware scoring to the reset selector and asset-prep format.

## 2026-06-13 15:18 PDT - 2cm minimum-width validation launch

Goal:
- Test whether rejecting sub-2cm contact pairs avoids thin-stem Panda grasp-prior resets that look geometrically plausible but do not clamp or lift.

Version Control:
- implementation_commit: `3292cdb4d0b088a506fd29d55b8675e3ecfa20ee`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`

Command / Job:
- command: same as `1029063` but with `GRASP_RESET_MIN_WIDTH=0.02`.
- job_id: `1029064`
- run_name: `multiobject_min_width02_top07_3292cdb_20260613_151851`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_min_width02_top07_3292cdb_20260613_151851`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029064.out`

Next:
- Monitor metrics and representative frames; if this fails, implement contact-location-aware candidate scoring/gating and regenerate the 4-object smoke priors.

## 2026-06-13 - Stable-reset grasp-contact failure and top-down prior patch

Goal:
- Make grasp-contact validation use a physically plausible grasp-prior reset before relaunching RL training.

Evidence:
- Settled-pose cache generation reruns on commit `c3c924f` failed for jobs `1029052` and `1029053` because object `96ae0ff853734df0b10a827307949c87` retained high final speed (`~0.0527m/s`) in the new cache-generation rollout.
- To keep debugging unblocked, materialized a settled-pose cache from the previously passed validation `1028898` at `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache`.
- Video validation job `1029054` used that cache and passed `reset_settle` and `perturbation`, but failed `grasp_contact`.
- `1029054` grasp-contact metrics: selected object `30700bc210844bdc991a5ccf16b6379f`, `selected_lift_height_max=0.0195m` vs threshold `0.12m`, `selected_max_finger_dist_min=0.175m`, `selected_object_xy_delta_max=0.0165m`.
- Selection probe showed the same object could lift `0.0798m`, but it dragged `0.0726m` and the selected pregrasp direction was not top-down (`selected_pregrasp_offset_dir_z=-0.141`), so the validator was accepting a side/rim grasp from its fallback path.

Change:
- Added no-op grasp-prior reset success/quality hooks to the Franka cube env so subclasses can add task-specific reset gates without changing cube behavior.
- Multi-object grasp-prior reset now samples `grasp_prior_reset_candidate_count` priors per env, scores by prior confidence and pregrasp z, and prefers top-down candidates with width and pregrasp-farther checks.
- Multi-object reset success/quality now requires `grasp_prior_reset_min_pregrasp_z` when `grasp_prior_reset_require_topdown=True`, so bad side grasps fall back to default robot reset instead of becoming warmstart candidates.
- Tightened grasp-contact validation candidate selection to reject non-top-down quality fallbacks.
- Added validation/training wrapper controls for candidate count and top-down threshold.

Version Control:
- base_commit: `c3c924f41cf87688d7ea0860a9d5b2286a968863`
- implementation_commit: this commit
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy the exact commit to l401, rerun grasp-contact video validation against the settled cache from `1028898`, inspect metrics/frames, then decide whether the reset is ready for RL training.

## 2026-06-13 - Root-vs-center grasp-prior scoring fix

Goal:
- Fix the remaining grasp-contact failure after top-down filtering.

Command / Job:
- job_id: `1029056`
- run_name: `multiobject_topdown_grasp_contact_d3a922b_20260613_143929`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_topdown_grasp_contact_d3a922b_20260613_143929`
- status: failed by validation metrics.

Result:
- `reset_settle` passed.
- `perturbation` looked visually normal, but failed only because the forced push triggered RL done flags after crossing the pre-lift drag threshold; motion bounds stayed sane (`object_xy_delta_max=0.1286m`, no bounce-away).
- `grasp_contact` selected a top-down prior on object `96ae0ff853734df0b10a827307949c87` with `selected_pregrasp_offset_dir_z=0.865`, but lifted only `0.0021m`.
- Visual inspection showed the gripper closing near one end of a long object instead of clamping near its center.

Analysis:
- Multi-object `_compose_grasp_prior_targets` was using the object root as `cube_pos_w` even though the multi-object reward/reset buffers use the bounds-derived object center.
- For asymmetric/long objects, this scored grasps relative to the wrong point and could prefer end grasps that are valid top-down IK poses but do not lift.

Change:
- Use object root only for composing world-object transforms.
- Use bounds-derived object center for candidate exact-tool distance, pregrasp-farther checks, returned `cube_pos_w`, EE distances, and base quality metrics.
- Increase candidate score pressure toward center-relative grasps.
- Do not fail perturbation validation on RL `done_count`; forced pushes are judged by movement/clearance/bounce bounds.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy exact source to l401, and rerun video validation.

## 2026-06-13 - Minimum grasp-prior width gate after `1029062`

Goal:
- Avoid selecting near-zero-width grasp priors that the Panda fingers cannot use to clamp the object.

Command / Job:
- job_id: `1029062`
- run_name: `multiobject_dynamic_close_top07_77e314f_20260613_150725`
- status: failed only `grasp_contact`.

Result:
- Strict top-down threshold selected object `96ae0ff853734df0b10a827307949c87`, `selected_pregrasp_offset_dir_z=0.869`.
- The gripper closed almost completely (`selected_gripper_width_min=0.0002m`) but object lift remained `0.0m`.
- The selected prior had open-width margin `0.0785m`, implying an unrealistically tiny required width of `~0.0015m`.

Analysis:
- Some high-confidence, top-down priors correspond to needle-like contact pairs. They can be geometrically valid but are poor Panda grasp reset candidates.

Change:
- Added `grasp_prior_reset_min_width=0.008`.
- Candidate selection and reset success/quality now require sampled prior width within `[min_width, max_gripper_width]`.
- Validation and teacher wrappers expose/log the min-width gate.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- local: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy exact source to l401, and rerun validation with strict top-down plus min-width gating.

## 2026-06-13 - Dynamic warmstart close width after `1029060`

Goal:
- Make scripted grasp-contact validation actually clamp thin object grasps.

Command / Job:
- job_id: `1029060`
- run_name: `multiobject_tool_radial_top03_c319018_20260613_150041`
- status: failed only `grasp_contact`.

Result:
- Stricter top-down threshold selected a valid quality prior with `selected_pregrasp_offset_dir_z=0.354`.
- Lift remained `0.0m` even though finger distances were small.
- The selected prior required a narrow width: open-width margin `0.0678m` from a `0.08m` open gripper implies required width `~0.012m`, while the fixed warmstart close width was `0.025m`.

Analysis:
- The fixed warmstart close width is too wide for thin-object prior samples, so the fingers can track the pose without clamping.
- Multi-object warmstart should close per env based on the sampled prior width.

Change:
- Added tensor-valued gripper action conversion.
- Warmstart and action-prior teacher actions now use `min(configured_close_width, sampled_required_width - 0.003m)` per env.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `git diff --check`

Next:
- Commit, deploy exact source to l401, and rerun video validation.

## 2026-06-13 - Center-distance quality gate after `1029057`

Goal:
- Stop treating far end/rim priors as successful grasp-prior reset states.

Command / Job:
- job_id: `1029057`
- run_name: `multiobject_center_grasp_contact_8cef12d_20260613_144714`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.

Result:
- Selected object `30700bc210844bdc991a5ccf16b6379f`.
- The selected prior was nominally top-down (`selected_pregrasp_offset_dir_z=0.122`) but was far from the object center: object center `[-0.6012, -0.0405, 0.7831]`, exact tool `[-0.6927, -0.2351, 0.7930]`.
- Lift remained negligible (`selected_lift_height_max=0.0030m` vs `0.12m` threshold).

Analysis:
- Object-center scoring alone improved the selected object but did not make center distance a hard quality condition.
- Objects with sparse or poor prior samples can still win selection if the validator only asks for top-down and IK success.

Change:
- Added `grasp_prior_reset_max_center_distance_frac=0.55`.
- Candidate selection now requires center distance within that fraction of object grasp size.
- Multi-object reset success/quality also requires the same center-distance gate.
- Validation and teacher-training wrappers now log and expose the center-distance fraction.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy exact source to l401, and rerun grasp-contact validation.

## 2026-06-13 - Tool-frame radial quality fix after `1029058`

Goal:
- Fix false negative quality rejection for center-near grasp-prior resets.

Command / Job:
- job_id: `1029058`
- run_name: `multiobject_center_gate_grasp_contact_02b77d2_20260613_145328`
- status: failed only `grasp_contact`.

Result:
- `reset_settle` passed.
- `perturbation` passed.
- Grasp-contact found a center-near prior on `7195ed3346a445448308febe833c180a`, but selection still reported no quality candidate and the final rollout had warmstart inactive (`warmstart_phases=[-1]`).
- Geometry showed IK alignment was good and center-distance gate passed: `selected_reset_success=true`, center distance fraction `0.408`, top-down z `0.471`.

Analysis:
- The base quality radial gate used `exact_ee_pos_w - cube_pos_w`.
- The pregrasp direction is defined in the grasp/tool frame, while `exact_ee_pos_w` includes the task control-frame offset. For this object that offset pointed opposite the actual tool radial direction, falsely failing `offset_dot > 0.25`.

Change:
- Compute `cube_grasp_prior_offset_radial_dot` from `exact_tool_pos_w - cube_pos_w`.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `git diff --check`

Next:
- Commit, deploy exact source to l401, and rerun video validation.

## 2026-06-13 14:18 PDT - Stop invalid RL runs and wire stable-pose reset path

Goal:
- Stop spending A100 time on PPO runs whose reset/warmstart path does not physically lift, then make the multi-object reset path use cached stable poses so partial vector-env resets do not require in-reset settling.

Hypothesis:
- The training runs are stalled because the reset path still uses ideal yaw-only object poses while object stability/grasp alignment requires precomputed stable poses. The grasp-contact validator also accepted a non-lifting hand/object configuration because its pass criteria were too loose.

Change:
- Canceled A100 jobs `29048544`, `29049452`, and `29049710` after metrics showed latest success `0.0` and only sub-centimeter lift.
- Added optional `object_stable_pose_*` config fields and a multi-object env loader for per-object stable-pose `.npz` caches.
- Reset now samples a cached stable rotation per env/object, composes 360-degree yaw randomization around world z, and places the object using the stable pose root-z offset.
- Fixed grasp-prior width gating so too-wide sampled grasps are not hidden by clamping to `max_gripper_width`.
- Tightened video `grasp_contact` pass criteria to require actual lift height and added selected-env geometry diagnostics.
- Added stable-pose cache knobs to the teacher and video-validation Slurm wrappers.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- base_commit: `c8786b40442e29abb1ad27385bd848a09a8fdc75`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, this worklog

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- local: `git diff --check`

Result:
- status: implementation checks passed locally; l401 validation launch pending exact commit deployment.

Next:
- Commit and deploy to an l401 worktree, run stable-pose-enabled video validation against the 4-object smoke manifest/cache, inspect the stricter grasp-contact failure/geometry, then fix grasp alignment before relaunching training.

## 2026-06-13 14:24 PDT - Add settled-pose cache format support

Goal:
- Ensure the RL reset path can use the post-PhysX settled object poses from stable-pose replay, not only raw trimesh stable candidates.

Change:
- Extended the multi-object stable-pose loader to accept `.npz` files containing `rotations` and `root_z_offsets`.
- Extended `validate_graspgen_stable_pose_resets.py` to write `settled_pose_cache/<uuid>.npz` files from the replay final root poses.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy the new exact commit, rerun stable-pose validation once to materialize `settled_pose_cache/`, then point grasp-contact video validation and training at that cache directory.

## 2026-06-13T20:27:04Z - Multi-object main merge and lift-guidance training patch

Goal:
- Integrate the multi-object Franka grasp environment into `main`, launch actual 4-object teacher training, and diagnose early learning quality.

Version Control:
- integration_commit: `8bad95c36af398366a4d112da9e7f766c60497ef`
- current_main_before_patch: `afb9ddeeabe93a6b32cafb89db82a7652595ab19`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- pushed: `8bad95c` and later `afb9dde` are both on `origin/main`.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- local: `git diff --check`
- l401 smoke job `1028979`: random object assignment, 8 unique reset poses, yaw span `3.526031rad`, obs shape `[8, 80]`, finite object feature tail, grasp-prior reset mean success `0.625`.

Command / Job:
- active training job: `29048544`
- run_name: `multiobject_teacher_4obj_8bad95c_20260613_123520`
- code_commit: `8bad95c36af398366a4d112da9e7f766c60497ef`
- source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-training-main-20260613`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/multiobject_teacher_4obj_8bad95c_20260613_123520`
- config: `TASK=Dextrah-Franka-Multi-Object-Grasp`, `MAX_OBJECTS=4`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_CENTER_OFFSET_X=0.05`, `OBJECT_SPAWN_XY_RANDOMIZATION=0.10`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `NUM_ENVS=1024`, `MAX_ITERATIONS=1000`, `HORIZON_LENGTH=64`, `MINIBATCH_SIZE=32768`.

Result:
- A100 smoke `29048488` completed successfully through 20 epochs, obs space `80`, no non-finite JSONL metrics.
- Active A100 training `29048544` is running. At epoch 350: no non-finite JSONL metrics; `ee_to_cube_dist=0.05395`, `finger_center_to_cube_dist=0.06751`, `gripper_width=0.00177`, `cube_success_rate=0.0`, `cube_lift_height=0.000783m`.
- Diagnostic l401 eval `1029044` on epoch 150 completed with video and metrics; `success_ever_rate=0.0`, max lift height `0.001713m`, mean z action `-0.1190`, gripper closes quickly.
- Full GraspGen asset-prep job `1028980` is running on l401, downloading on `/lustre`; last checked around batch `294/804`.

Analysis:
- The merged environment is RLable and correctly conditions the teacher policy on object state (`72 -> 80` obs). Parallel envs sample different object identities and poses; training randomizes yaw over the full 360 degrees.
- The current 4-object run learns approach/enclosure/closing but not reliable upward lift. Recent policy diagnostics show more down than up z action even when lift-action reward is available.

Change:
- Added training-wrapper support for existing `grasp_prior_action_warmstart_*` and `grasp_prior_action_prior_reward_*` environment knobs in `cluster/sbatch_train_teacher_8gpu.sh`.
- This is wrapper-only; it does not change default environment behavior because all new knobs default disabled.

Checks:
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`

Next:
- Commit/push the wrapper patch, deploy it to a new A100 source worktree, and launch a bounded tuned 4-object teacher run using grasp-prior action prior reward plus stronger lift/down-action shaping while keeping the current baseline run alive for comparison.

## 2026-06-13T20:29:00Z - Guided 4-object teacher run queued

Goal:
- Compare the baseline 4-object teacher run against a tuned run that explicitly rewards the early grasp-prior close/lift reference action without applying scripted warmstart actions.

Version Control:
- implementation_commit: `21a5a063f3326b424d587fcf6151c683644589ce`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-guidance-21a5a06-20260613`
- remote_commit: `21a5a063f3326b424d587fcf6151c683644589ce`

Validation:
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`
- remote: `bash -n /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-guidance-21a5a06-20260613/cluster/sbatch_train_teacher_8gpu.sh`

Command / Job:
- job_id: `29049357`
- run_name: `multiobject_teacher_4obj_guided_21a5a06_20260613_1329`
- source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-guidance-21a5a06-20260613`
- config: `MAX_OBJECTS=4`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_CENTER_OFFSET_X=0.05`, `OBJECT_SPAWN_XY_RANDOMIZATION=0.10`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `NUM_ENVS=1024`, `MAX_ITERATIONS=500`.
- action guidance: `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, `WEIGHT=3.0`, `SHARPNESS=2.0`, reference sequence `approach=4`, `close=12`, `lift=24`, `lift_action_z=0.25`, no action warmstart override.
- reward shaping: `CUBE_LIFT_WEIGHT=20.0`, `CUBE_HEIGHT_TRACKING_WEIGHT=6.0`, `CUBE_SUCCESS_BONUS_WEIGHT=30.0`, `CUBE_LIFT_ACTION_WEIGHT=4.0`, `CUBE_DESCEND_ACTION_PENALTY_WEIGHT=-4.0`, `CUBE_ACTION_PENALTY_WEIGHT=-0.0002`.

Result:
- status: pending at launch due `QOSMaxJobsPerUserLimit`.

Next:
- Monitor pending/start state, inspect stdout early for resolved overrides, then compare early action-prior, action-z, lift-height, and success metrics against baseline job `29048544`.

## 2026-06-13T20:38:00Z - Guided run close-width correction

Goal:
- Stop the first guided comparison run after discovering its reference close command was not actually closing the Robotiq gripper.

Evidence:
- Job `29049357` started and resolved all intended overrides, but `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.055` with `max_gripper_width=0.08` maps to action `2 * 0.055 / 0.08 - 1 = +0.375`.
- Positive gripper action commands a wider gripper in the Franka env; the reward close term uses `clamp(-action[:, 6])`, confirming negative is the closing direction.
- Early guided metrics showed gripper width staying open around `0.042m`, while baseline converges near `0.002m`.

Action:
- Canceled job `29049357` after about 5 minutes to avoid training against a bad reference action.
- Changed the default diagnostic reference close width to `0.025m` in the env config and affected training/eval wrappers.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_train_franka_cube_grasp_1gpu_smoke.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- local: `git diff --check`

Next:
- Commit/push the close-width fix, deploy a fresh source worktree, and relaunch the guided 4-object comparison with close width `0.025m`.

## 2026-06-13T20:40:00Z - Corrected guided run queued

Goal:
- Relaunch the guided 4-object teacher comparison with the corrected closing reference action.

Version Control:
- implementation_commit: `10d6dd6bdf91a08b66c10763ddc20e537a4dc227`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-guidance-closefix-10d6dd6-20260613`
- remote_commit: `10d6dd6bdf91a08b66c10763ddc20e537a4dc227`

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_train_franka_cube_grasp_1gpu_smoke.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- local: `git diff --check`
- remote: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- remote: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`

Command / Job:
- job_id: `29049452`
- run_name: `multiobject_teacher_4obj_guided_closefix_10d6dd6_20260613_1340`
- config: same as canceled guided run, except `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.025`.

Result:
- status: pending at launch due `QOSMaxJobsPerUserLimit`.

Next:
- Monitor until start, verify resolved `env.yaml`, then compare early gripper-width/action-z/lift metrics against baseline and the canceled bad-guidance run.

## 2026-06-13T20:52:00Z - Sequence-timing comparison queued

Goal:
- Test whether delaying the lift reference and rebalancing reward weights fixes the guided-closefix run's early-lift-before-secure-contact behavior.

Evidence:
- Baseline job `29048544` through epoch 555: stable approach/close but mean z remains negative and lift/success stay near zero.
- Corrected guided job `29049452` through epoch 90: mean z is strongly positive and gripper closes, but finger/object distance remains worse than baseline and no reliable lift appears.

Command / Job:
- job_id: `29049710`
- run_name: `multiobject_teacher_4obj_seqprior_10d6dd6_20260613_1352`
- source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-guidance-closefix-10d6dd6-20260613`
- code_commit: `10d6dd6bdf91a08b66c10763ddc20e537a4dc227`
- sequence guidance: `approach=24`, `close=16`, `lift=16`, `close_width=0.025`, `lift_action_z=0.15`, action-prior weight `4.0`.
- reward shaping: `approach=3.0`, `enclosure=2.0`, `close_action=0.5`, `lift=15.0`, `height_tracking=5.0`, `success_bonus=30.0`, `lift_action=2.0`, `descend_penalty=-2.0`, `action_penalty=-0.0002`.

Result:
- status: pending at launch due `QOSMaxJobsPerUserLimit`.

Next:
- Let baseline and guided-closefix continue; if guided-closefix starts producing real lift before a slot opens, cancel the pending sequence-timing run. Otherwise compare all three.

## 2026-06-13T20:58:00Z - Guided checkpoint eval launch

Goal:
- Render and quantify the guided-closefix epoch-100 policy to diagnose why strong upward action is not producing object lift.

Command / Job:
- job_id: `1029046`
- run_name: `multiobject_eval_guided_closefix_ep100_20260613_1358`
- source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-eval-afb9dde-20260613`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/multiobject_teacher_4obj_guided_closefix_10d6dd6_20260613_1340/nn/last_dextrah_franka_multi_object_grasp_ep_100_rew_1620.4617.pth`
- config: `NUM_ENVS=4`, `NUM_STEPS=360`, `CAPTURE_VIDEO=True`, `OBJECT_ASSET_ASSIGNMENT=round_robin`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, same 4-object manifest and grasp-prior directory.

Result:
- status: pending at launch.

Next:
- Inspect eval metrics and video for whether the policy lifts away before enclosure, slips, or penetrates/contact-fails.

## 2026-06-13 - Main merge, randomized multi-object training, and cluster launch

Goal:
- Merge the multi-object Franka GraspGen environment into `main`.
- Add training-time object yaw randomization, randomized object assignment across vector envs, and validation checks that the policy observation is object-conditioned.
- Launch RL training from the merged commit while preparing the full GraspGen object set under `/lustre`.

Version Control:
- integration_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- merged_main_commit: `8bad95c36af398366a4d112da9e7f766c60497ef`
- pushed_main: `origin/main` fast-forwarded to `8bad95c36af398366a4d112da9e7f766c60497ef`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-training-main-20260613`
- remote_commit: `8bad95c36af398366a4d112da9e7f766c60497ef`

Implementation:
- `object_spawn_yaw_randomization_deg=180.0` gives uniform yaw over `[-180deg, +180deg]`, i.e. full 360-degree object yaw randomization.
- `object_asset_assignment=random` samples a balanced randomized object assignment across vector envs at scene construction; `round_robin` remains available for deterministic validation.
- Training wrappers now pass `OBJECT_ASSET_ASSIGNMENT`.
- Validation now checks parallel reset pose diversity and verifies object-conditioned observations: multi-object observation space is 80 vs the cube teacher's 72, with finite object feature tail values.

Local / Remote Checks:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- local: `git diff --check`
- remote_l401: `python3 -m py_compile ...`
- remote_l401: `bash -n ...`

Validation:
- run_name: `multiobject_random_assignment_smoke_8bad95c_20260613_122620`
- job_id: `1028979`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_random_assignment_smoke_8bad95c_20260613_122620/metrics.json`
- result: passed.
- object_asset_assignment: `random`
- object_asset_index_by_env: `[1, 2, 2, 3, 0, 0, 1, 3]`
- reset_parallel_env_pose_diversity: passed with 8 unique XY positions and yaw span `3.526031rad`.
- policy_conditioned_on_object: passed with observation shape `[8, 80]`, cube teacher obs space `72`, and finite object feature tail values.

Training Smoke:
- job_id: `29048488`
- run_name: `multiobject_teacher_smoke_8bad95c_20260613_122751`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/multiobject_teacher_smoke_8bad95c_20260613_122751`
- result: completed, exit code `0:0`, elapsed `00:06:36`.
- saved checkpoint: `nn/last_dextrah_franka_multi_object_grasp_ep_20_rew__489.9839_.pth`
- saved config confirmed `object_asset_assignment=random`, `object_spawn_yaw_randomization_deg=180.0`, `observation_space=80`, `num_envs=1024`, and `max_epochs=20`.
- metrics: rank-0 JSONL wrote 20 records, no non-finite numeric values.

Active Training:
- job_id: `29048544`
- run_name: `multiobject_teacher_4obj_8bad95c_20260613_123520`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/multiobject_teacher_4obj_8bad95c_20260613_123520`
- config: 4-object smoke manifest, `MAX_ITERATIONS=1000`, `NUM_ENVS=1024`, `HORIZON_LENGTH=64`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`.
- early status: running on A100 `polar3`; by epoch 12, no non-finite scalars, `cube_ee_to_cube_dist` improved from `0.2192` to `0.1860`, and `cube_finger_table_clearance_violation=0.0`.

Active Full Asset Prep:
- job_id: `1028980`
- run_name: `franka_multi_graspgen_full_8bad95c_20260613_122621`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_full_8bad95c_20260613_122621`
- cache: `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen`
- input split count: 8031 UUIDs.
- early status: running on l401 `batch_lon`; progressed past batch 125/804 with all download/cache paths under `/lustre`.

Next:
- Continue monitoring job `29048544` through checkpoints and JSONL metrics.
- Continue monitoring asset prep job `1028980`; launch full-asset training once the manifest and grasp-prior assets are complete and validated.

## 2026-06-13 - Main integration and training object randomization prep

Goal:
- Merge the validated multi-object environment into `main`, then prepare the
  multi-object teacher training path so parallel envs cover different objects,
  each reset samples independent object poses, and the policy remains
  object-conditioned like the cube teacher.

Change:
- Merged the validated environment branch into a clean integration worktree and
  pushed `origin/main` to `bb4941bb38db7995859fc1e4fae750f3c855495c`.
- Added `object_asset_assignment` to the multi-object task. `round_robin`
  preserves deterministic validation videos; `random` uses a randomized
  balanced assignment at scene construction so parallel envs cover as many
  different object USDs as possible.
- Set the A100 teacher wrapper default `OBJECT_ASSET_ASSIGNMENT=random` for
  `Dextrah-Franka-Multi-Object-Grasp`.
- Kept yaw randomization as the existing full 360-degree range:
  `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, meaning uniform yaw in
  `[-180deg, 180deg]`.
- Added validation metrics for parallel pose/yaw diversity and for the
  object-conditioned observation tail. The multi-object policy still reuses the
  original cube teacher actor-critic MLP and appends object scale, half extents,
  grasp size, asset-id fraction, prior flag, and radius to the cube teacher
  pose/velocity observation.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- base_commit: `bb4941bb38db7995859fc1e4fae750f3c855495c`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`,
  `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`,
  `dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py`,
  `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`,
  `cluster/sbatch_train_teacher_8gpu.sh`,
  `cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`,
  `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`,
  this worklog.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- local: `git diff --check`

Next:
- Commit/push this training-prep patch, deploy to l401/a100 agent-owned
  worktrees, run a small l401 multi-env smoke with `OBJECT_ASSET_ASSIGNMENT=random`,
  then launch A100 teacher training if the smoke confirms object/yaw diversity
  and finite object-conditioned observations.

## 2026-06-13 - Edge-offset stable replay validation

Goal:
- Move the multi-object spawn domain off the symmetric table-center prior to
  table-frame center `(5, 0)cm` with `+-10cm` randomization, then render the same
  four-object settled replay at the requested edge placements:
  `(15, 0)cm`, `(-5, 0)cm`, `(5, 10)cm`, `(5, -10)cm`.

Implementation:
- Multi-object reset now samples around
  `table_center + (object_spawn_center_offset_x, object_spawn_center_offset_y)`.
- Default center offset is `(0.05, 0.0)m`; default XY randomization half-range is
  `0.10m`.
- Added `--object_xy_offsets_cm` to the stable-pose validator and propagated
  `OBJECT_XY_OFFSETS_CM` through the validation/training wrappers.
- Added velocity zeroing after validator root-state writes; follow-up testing
  showed the remaining nonzero speed came from PhysX contact, not a stale root
  velocity buffer.

Version Control:
- implementation_commit: `6d179de08f0f85811971d7982a8d8ecfff7c6502`
  (`Adjust multi-object spawn domain center`)
- follow_up_commit: `5845a08d4da16878992cbb10aebce50215ea1a4a`
  (`Clear object velocity in stable pose validator`)
- remote_deploy: transferred as Git bundles to
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/` and
  fetched into the l401 agent worktree.
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`

Command / Jobs:
- first edge render command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=2 ROLLOUT_POSE_COUNT=1 STABLE_POSE_RANK_OVERRIDES=96ae0ff853734df0b10a827307949c87:1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 OBJECT_XY_OFFSETS_CM=15:0,-5:0,5:10,5:-10 RUN_NAME=graspgen_stable_pose_edge_offsets_6d179de_20260613_115930 CODE_COMMIT=6d179de08f0f85811971d7982a8d8ecfff7c6502 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- first edge render job_id: `1028962`; status: `FAILED`, exit `1:0`.
- zero-velocity rerun job_id: `1028965`; status: `FAILED`, exit `1:0`.
- rank sweep command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json OBJECT_UUIDS=96ae0ff853734df0b10a827307949c87 MAX_OBJECTS=1 STABLE_POSE_COUNT=6 ROLLOUT_POSE_COUNT=6 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=False TABLE_CLEARANCE=0.002 OBJECT_XY_OFFSETS_CM=5:10 RUN_NAME=graspgen_edge_96ae_rank_sweep_5845a08_20260613_120645 CODE_COMMIT=5845a08d4da16878992cbb10aebce50215ea1a4a sbatch --parsable --partition=batch --time=0-00:25:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- rank sweep job_id: `1028969`; status: `FAILED` by aggregate threshold because most ranks fail, but rank `2` passed for `96ae...` at `(5, 10)cm`.
- final edge render command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=3 ROLLOUT_POSE_COUNT=1 STABLE_POSE_RANK_OVERRIDES=96ae0ff853734df0b10a827307949c87:2 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 OBJECT_XY_OFFSETS_CM=15:0,-5:0,5:10,5:-10 RUN_NAME=graspgen_stable_pose_edge_offsets_rank2_5845a08_20260613_120807 CODE_COMMIT=5845a08d4da16878992cbb10aebce50215ea1a4a sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- final edge render job_id: `1028971`; status: `COMPLETED`, exit `0:0`, elapsed `00:01:14`.

Final Edge Replay Result:
- Top-level metrics: `passed=true`.
- Edge placements are interpreted as table-frame centimeters around the table
  center, so the final local object roots are approximately:
  `(-0.47, 0.0)`, `(-0.67, 0.0)`, `(-0.57, 0.10)`,
  `(-0.57, -0.10)`.
- Settled replay summary: `root_xy_delta_max=3.36e-06m`,
  `center_xy_delta_max=3.11e-06m`, `root_z_delta_max=1.61e-06m`,
  `angular_delta_deg_max=0.0791`, `bottom_clearance_min=-0.00416m`,
  `final_object_speed_max=0.00292m/s`.
- Settled replay per-env:
  - `7195ed3346a445448308febe833c180a`, offset `(15, 0)cm`, rank 0: passed.
  - `1d489db9cdc24161a7537926a20bb17b`, offset `(-5, 0)cm`, rank 0: passed.
  - `96ae0ff853734df0b10a827307949c87`, offset `(5, 10)cm`, rank 2: passed.
  - `30700bc210844bdc991a5ccf16b6379f`, offset `(5, -10)cm`, rank 0: passed.

Local Artifacts:
- Fetched results: `local_results/stable_pose_edge_rank2_1028971/`
- Settled replay grid video:
  `local_results/stable_pose_edge_rank2_1028971/settled_replay_grid.mp4`
- Discovery grid video:
  `local_results/stable_pose_edge_rank2_1028971/stable_pose_discovery_grid.mp4`
- Contact sheets:
  `local_results/stable_pose_edge_rank2_1028971/settled_replay_contact_sheet.jpg`
  and
  `local_results/stable_pose_edge_rank2_1028971/stable_pose_discovery_contact_sheet.jpg`
- Slurm log:
  `local_results/stable_pose_edge_rank2_1028971/slurm.out`

Viewer URL:
- settled replay grid:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_edge_rank2_1028971/settled_replay_grid.mp4`

Visual Inspection:
- Settled replay contact sheet and MP4 show all four edge placements on top of
  the table.
- No visible bounce-away, falling off the table, table sticking, or robot/object
  crowding is visible in the settled replay.
- The first discovery rollout still marks `1d489...` as failing strict angular
  drift before settled-pose replay, which is expected for this shape and is why
  the accepted RL reset path should use cached settled poses.

Next:
- Use the shifted spawn domain and cached settled poses for the multi-object RL
  reset path. For the current smoke set, keep the rank override
  `96ae0ff853734df0b10a827307949c87:2` at the `(5, 10)cm` edge placement.

## 2026-06-13 - Multi-object spawn center and edge-placement replay

Goal:
- Move multi-object reset randomization away from the robot-side table edge and render the same four-object settled replay at the requested table-frame domain edges.

Hypothesis:
- Sampling around `table_center + (0.05, 0.0)` with a `0.10m` half-range keeps large objects farther from the robot while preserving the existing object-radius table clamp.
- A stable-pose replay forced to table-frame offsets `(15,0)`, `(-5,0)`, `(5,10)`, and `(5,-10)` cm should expose any edge-related overhang, table sticking, or unexpected settling.

Change:
- Added `object_spawn_center_offset_x=0.05`, `object_spawn_center_offset_y=0.0`, and changed multi-object `object_spawn_xy_randomization` default to `0.10`.
- Changed multi-object reset placement to sample around `table_center + object_spawn_center_offset`.
- Added `--object_xy_offsets_cm` / `OBJECT_XY_OFFSETS_CM` to the stable-pose validator for explicit table-frame edge placement videos.
- Updated multi-object validation/video/train wrappers to log and pass the new center offset and `0.10m` randomization defaults.

Version Control:
- agent_id: `dextrah-multiobject-grasp-prior-20260613T003321Z`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`
- branch: `codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- base_commit: `920e403`
- implementation_commit: `6d179de08f0f85811971d7982a8d8ecfff7c6502`
- push/pull: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`; deployed to l401 via Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_spawn_domain_6d179de.bundle`
- remote_commit/status: `6d179de08f0f85811971d7982a8d8ecfff7c6502`, detached clean in `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`, `cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=2 ROLLOUT_POSE_COUNT=1 STABLE_POSE_RANK_OVERRIDES=96ae0ff853734df0b10a827307949c87:1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 OBJECT_XY_OFFSETS_CM=15:0,-5:0,5:10,5:-10 RUN_NAME=graspgen_stable_pose_edge_offsets_6d179de_20260613_115930 CODE_COMMIT=6d179de08f0f85811971d7982a8d8ecfff7c6502 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028962`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028962.out`
- run_name: `graspgen_stable_pose_edge_offsets_6d179de_20260613_115930`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_edge_offsets_6d179de_20260613_115930`
- status: pending for resources at launch.

Result:
- status: failed by validator threshold, but produced metrics and videos.
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:01:22`.
- Metrics top-level `passed=false`.
- Settled replay pose drift stayed near zero: `root_xy_delta_max=4.54e-06m`, `center_xy_delta_max=3.93e-06m`, `root_z_delta_max=1.77e-05m`, `angular_delta_deg_max=0.0791`.
- Env 2 / `96ae0ff853734df0b10a827307949c87` at table-frame `(5,10)cm` failed only the final velocity threshold: `final_object_speed=0.05269m/s` vs `max_final_speed=0.03m/s`.
- Visual inspection of `local_results/stable_pose_edge_1028962/settled_replay_grid.mp4` and first/mid/last contact sheet showed objects on top of the table, within the tabletop, with the robot gripper clear and no visible bounce-away or penetration.

Analysis:
- The failed metric conflicts with the observed pose drift, so the first fix is to make stable-pose placement explicitly clear object root velocity after root-state writes.
- This matters for RL because the inherited policy observation includes `cube_vel`.

Next:
- Add explicit zero root velocity writes after stable-pose placement and settled-replay placement, then relaunch the same edge replay.

## 2026-06-13 - Edge replay zero-velocity placement relaunch

Goal:
- Verify the edge settled-replay validation passes after explicitly zeroing object root velocity during stable-pose placement.

Hypothesis:
- `write_root_state_to_sim` should carry zero velocity, but an explicit `write_root_velocity_to_sim` after placement will remove any stale velocity buffer before replay.

Change:
- Added `_zero_object_root_velocity()` to `validate_graspgen_stable_pose_resets.py`.
- Called it after root-state writes in both `_place_stable_pose_states()` and `_place_local_root_states()`.

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy, run remote checks, and relaunch the exact same edge replay.

Follow-up:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:02:06`.
- Local fetched artifacts: `local_results/video_topdown_1028886`.
- Encoded MP4s:
  - `reset_settle.mp4`: 1280x720, 96 frames, 8.0s.
  - `perturbation.mp4`: 1280x720, 48 frames, 4.0s.
  - `grasp_contact.mp4`: 1280x720, 45 frames, 3.75s.
- Metrics:
  - `reset_settle` passed.
  - `perturbation` failed because the tuned-up push was too strong: `object_xy_delta_max=0.2159m`, `done_count=4`.
  - `grasp_contact` failed only under the stricter pregrasp-z selector threshold: `selected_done_count=0`, `object_xy_delta_max=0.0306m`, `finger_table_clearance_min=0.0301m`, `selected_pregrasp_offset_dir_z=0.122`.
- Visual inspection:
  - Contact video no longer shows a mid-video reset jump.
  - Robot reset is aligned to the settled object pose; no obvious gripper/table or gripper/object penetration is visible.
  - Perturbation visibly moves and rotates the object but goes too far for the no-done metric.

Analysis:
- The user's two grasp-contact concerns are addressed in this run: no auto-reset artifact, and reset is composed after object settling.
- The remaining validation issue is parameter tuning for perturbation and avoiding an unnecessarily strict contact-selector threshold.

Next:
- Rerun without code changes using a smaller perturbation push and `GRASP_RESET_MIN_PREGRASP_Z=0.10`.

## 2026-06-13 - Tuned perturbation 4-object video launch

Goal:
- Produce a clean video-validation run where reset-settle, moderate perturbation, and settled-pose grasp contact all pass their metrics and visual checks.

Version Control:
- local_commit: `3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e`
- remote_commit: `3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=8 PERTURB_LINEAR_VELOCITY=0.45 PERTURB_LATERAL_VELOCITY=0.15 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=240 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=64 GRASP_RESET_MIN_PREGRASP_Z=0.10 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json RUN_NAME=<run> CODE_NFS=<remote_worktree> CODE_COMMIT=3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e sbatch --partition=batch --time=0-00:45:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028887`
- run_name: `franka_multi_video_tuned_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260613_000239`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_tuned_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260613_000239`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028887.out`

Result:
- status: running/queued; monitoring in progress.

Follow-up:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:01:26`.
- Local fetched artifacts: `local_results/video_manual_1028884`.
- Encoded MP4s:
  - `reset_settle.mp4`: 1280x720, 96 frames, 8.0s.
  - `perturbation.mp4`: 1280x720, 48 frames, 4.0s.
  - `grasp_contact.mp4`: 1280x720, 45 frames, 3.75s.
- Metrics:
  - `reset_settle` passed. Mesh-vertex bottom clearance min `-0.0040m`, done count `0`, xy drift `1.5e-05m`.
  - `perturbation` failed because the one-shot push was too weak after settling: xy delta max `0.0049m`, done count `0`, bottom clearance min `-0.0042m`.
  - `grasp_contact` failed. It reached phases `[-1, 0, 1, 2]`, but selected env `3` terminated 4 times due object drag; xy delta max was `0.1016m`.
- Visual inspection:
  - Reset-settle no longer shows bouncing, table sticking, or robot shaking.
  - Perturbation does not visibly move enough to prove normal response.
  - Grasp-contact uses a side/protrusion grasp on object `30700bc210844bdc991a5ccf16b6379f`; fingers stay table-clear, but the robot pushes/drags the object rather than grasping it.

Analysis:
- The raised base is effective; finger table clearance in reset/contact is no longer the issue.
- The validation perturbation must be a short sustained push, not a single weak initial velocity.
- Object `30700bc...` only has 4 Franka prior samples and they are side/downward (`zaxis_z` about `[-0.45, -0.34]`), so selecting it for the first contact smoke is a bad evidence target.

Next:
- Patch video validation to use a sustained perturb push and to prefer quality grasps with upward/top-down pregrasp directions for contact evidence.

## 2026-06-13 - Perturbation and top-down contact selection patch

Goal:
- Make the perturbation video visibly exercise object motion and avoid selecting known side-push grasp priors for the contact smoke.

Hypothesis:
- Reapplying a bounded root velocity for the first few perturbation steps will produce visible object motion without causing table penetration or large displacement.
- Requiring `grasp_prior_reset_offset_dir_w.z >= 0.15` for selected contact evidence will prefer top-down/upward pregrasp samples from objects with richer priors and reject the object-3 side-protrusion sample.

Change:
- Added video validator args for perturb push steps and velocities.
- Added a `grasp_reset_min_pregrasp_z` selector in `_reset_until_quality_grasp`.
- Added selected pregrasp-z diagnostics to grasp-contact metrics.
- Exposed the new knobs in the video Slurm wrapper.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` passed.
- `git diff --check` passed.

Next:
- Commit, deploy, rerun the 4-object video smoke with `GRASP_RESET_ATTEMPTS=64`, then inspect metrics and MP4s.

## 2026-06-13 - Top-down settled-reset 4-object video launch

Goal:
- Verify the contact video no longer contains auto-reset jumps and that the robot reset is computed from the object's settled pose.

Version Control:
- local_commit: `3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e`
- remote_commit: `3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=12 PERTURB_LINEAR_VELOCITY=0.75 PERTURB_LATERAL_VELOCITY=0.25 PERTURB_ANGULAR_VELOCITY=5.0 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=240 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=64 GRASP_RESET_MIN_PREGRASP_Z=0.15 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json RUN_NAME=<run> CODE_NFS=<remote_worktree> CODE_COMMIT=3b8c306efd73103f5fe4eabc006ccf57dd5f3b2e sbatch --partition=batch --time=0-00:45:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028886`
- run_name: `franka_multi_video_topdown_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_235716`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_topdown_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_235716`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028886.out`

Result:
- status: running/queued; monitoring in progress.

## 2026-06-13 - Single-env 4-object video smoke result

Goal:
- Inspect the rendered reset-settle, perturbation, and grasp-contact evidence from job `1028881`.

Version Control:
- implementation_commit: `79805365f95229725cdcf7d683c20b673927af66`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- job_id: `1028881`
- run_name: `franka_multi_video_singleenv_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233822`
- remote_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_singleenv_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233822`
- local_artifacts: `local_results/video_singleenv_1028881`

Result:
- status: failed.
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:01:23`.
- Videos were produced for all three scenarios: `reset_settle.mp4`, `perturbation.mp4`, and `grasp_contact.mp4`.
- Metrics failed for all three scenarios. Mesh-bottom clearance used a rotated AABB and reported `bottom_clearance_min` around `-0.10m`; visual inspection did not support treating that alone as a reliable penetration measurement for long/irregular objects.
- Grasp-contact did not show a valid contact: selected env `3`, warmstart phases were only `[-1, 0]`, and the gripper moved out of useful contact before close/lift evidence appeared.

Analysis:
- The contact scenario was still being hidden by the Gym/DirectRLEnv automatic reset path: once the selected env terminates, later frames show a reset/default robot instead of the actual failure.
- The validator was still using cube-specific contact thresholds (`selected_max_finger_dist <= 0.12`) and AABB bottom estimates that are too loose for rotated GraspGen meshes.
- The environment reset still composed grasp-prior IK from the initially written object pose, not an optional post-settle root pose.

Next:
- Add guarded full-env reset settling for validation, refresh object references before applying the prior, switch video stepping to manual low-level sim stepping so failures remain visible, and compute bottom clearance from sampled scaled OBJ vertices.

## 2026-06-13 - Reset-settle/contact validator patch

Goal:
- Make the rendered video validation diagnose the actual reset/contact behavior instead of auto-reset artifacts.

Hypothesis:
- Full-env validation can safely settle objects before composing the grasp-prior robot reset.
- During video capture, manual low-level stepping will preserve early termination evidence and avoid Gym auto-reset hiding bad contact.
- Scaled OBJ vertex samples provide a better bottom-clearance check than the rotated AABB for irregular GraspGen objects.

Change:
- Added opt-in multi-object config fields: `object_reset_settle_steps`, `object_reset_zero_velocity_after_settle`, and `object_reset_settle_full_reset_only`.
- The multi-object reset now can settle full-vector resets, zero object velocity, refresh object center/goal references, and then apply the grasp prior from the post-settle root pose.
- The video validator now enables that full-env settle path, manually steps the simulator for video scenarios, records selected-env warmstart/termination diagnostics, and samples scaled OBJ vertices for bottom clearance.
- The video Slurm wrapper now forwards `OBJECT_RESET_SETTLE_STEPS`.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` passed.
- `git diff --check` passed.

Next:
- Commit, deploy the exact commit to the l401 agent worktree, rerun the 4-object rendered validation, fetch/encode/inspect videos and metrics, then decide whether another environment fix is needed before training.

## 2026-06-13 - Manual-step settled-reset 4-object video launch

Goal:
- Rerun rendered reset-settle, perturbation, and grasp-contact evidence after the reset-settle/contact validator patch.

Version Control:
- local_commit: `dfbb376c1ba71af8a0edf1ee89b940bcb2a2754d`
- remote_commit: `dfbb376c1ba71af8a0edf1ee89b940bcb2a2754d`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=240 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=16 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json RUN_NAME=<run> CODE_NFS=<remote_worktree> CODE_COMMIT=dfbb376c1ba71af8a0edf1ee89b940bcb2a2754d sbatch --partition=batch --time=0-00:45:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028884`
- run_name: `franka_multi_video_resetsettle_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_235021`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_resetsettle_manual_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_235021`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028884.out`

Result:
- status: running/queued; monitoring in progress.

## 2026-06-13 - Route GraspGen downloads off home and revise video validation

Goal:
- Fix the `[Errno 122] Disk quota exceeded` asset staging failure before further environment/video validation.
- Apply the user-requested Franka base height increase and correct the video-validator semantics.

Hypothesis:
- The asset staging failure came from Objaverse using `/home/lzha/.objaverse`; `/home/lzha` was over its 10G quota.
- Reset-settle metrics incorrectly counted randomized pose changes between reset cycles as physical drift.
- Perturbation should be object-only, not initialized from a grasp-prior robot pose near the object.
- Grasp-contact should compose the robot reset after the object pose has settled.

Change:
- Patched `cluster/sbatch_prepare_graspgen_assets_1gpu.sh` to mount `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen` at `/graspgen_cache` and route `HOME`, `XDG_CACHE_HOME`, `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, `OBJAVERSE_HOME`, `OBJAVERSE_CACHE_DIR`, `TMPDIR`, `PIP_CACHE_DIR`, and `TORCH_HOME` there.
- Added `DEXTRAH_ENFORCE_NO_HOME_DOWNLOADS` checks to `dextrah_lab/assets/prepare_graspgen_assets.py`.
- Raised Franka `robot_base_z` from `0.27` to `0.47`.
- Patched `validate_franka_multi_object_grasp_videos.py` so reset/perturbation use a no-grasp-prior env; reset metrics measure within-cycle drift; grasp contact settles objects first, refreshes the reference pose, then applies grasp-prior robot reset.
- Added `GRASP_OBJECT_SETTLE_STEPS` to the video validation Slurm wrapper.

Validation:
- `python3 -m py_compile dextrah_lab/assets/prepare_graspgen_assets.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py` passed.
- `bash -n cluster/sbatch_prepare_graspgen_assets_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` passed.

Next:
- Finish moving `/home/lzha/.objaverse` to `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen/home/.objaverse`.
- Commit, deploy the exact commit to the l401 agent worktree, and run a small asset staging smoke that proves cache paths resolve under `/graspgen_cache` and not `/home`.

Follow-up:
- Moved `/home/lzha/.objaverse` to `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen/home/.objaverse`.
- `/home/lzha` quota after the move: `7.036G / 10G`.
- GraspGen Objaverse cache on Lustre: `3.0G` at `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen/home/.objaverse`.

## 2026-06-13 - GraspGen Lustre-cache smoke launch

Goal:
- Prove the patched asset staging wrapper routes GraspGen/Objaverse/HF/temp caches to Lustre and still stages a valid USD-backed object manifest.

Version Control:
- local_commit: `5a9a5d85847ea6a97435f2069610d5f180644c4c`
- remote_commit: `5a9a5d85847ea6a97435f2069610d5f180644c4c`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `LIMIT=1 CONVERT_USD=True REFRESH_MANIFEST=True SKIP_OBJECT_DOWNLOAD=False SKIP_GRASP_EXTRACT=False sbatch --partition=batch --time=0-00:30:00 --export=ALL,CODE_NFS=<remote_worktree>,RUN_NAME=<run>,ASSET_OUTPUT_DIR_HOST=<run_dir>,ASSET_OUTPUT_DIR_CONTAINER=/results/assets/<run> cluster/sbatch_prepare_graspgen_assets_1gpu.sh`
- job_id: `1028876`
- run_name: `franka_multi_graspgen_cache_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233011`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_cache_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_233011`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1028876.out`

Result:
- status: passed.
- Slurm state: `COMPLETED`, exit code `0:0`, elapsed `00:02:00`.
- Log evidence:
  - Wrapper preflight set `HOME`, `XDG_CACHE_HOME`, `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, `OBJAVERSE_HOME`, `OBJAVERSE_CACHE_DIR`, `TMPDIR`, `PIP_CACHE_DIR`, and `TORCH_HOME` under `/graspgen_cache`.
  - `DEXTRAH_GRASPGEN_ASSET_STAGE_SUMMARY` reported `objects=1` and `missing_usd_count=0`.
  - Grep for `Disk quota exceeded`, `Errno 122`, `/home/lzha`, and `/home/` returned no matches.
- Artifact evidence:
  - Manifest object UUID `7195ed3346a445448308febe833c180a`.
  - Dataset scale in manifest: `0.010088245384395123`.
  - USD exists at `USD/7195ed3346a445448308febe833c180a/7195ed3346a445448308febe833c180a.usd`.
  - Grasp prior exists at `grasp_priors/7195ed3346a445448308febe833c180a.npz`.
- Storage evidence:
  - Lustre GraspGen cache: `3.1G` at `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgen`.
  - Smoke run directory: `839M`.
  - `/home/lzha` quota after the run: `7.036G / 10G`.

Analysis:
- The quota failure path is fixed for the staging wrapper: all downloader/cache/temp locations now resolve to a Lustre-backed mount, and a fresh object+grasp+USD smoke completed without touching `/home`.
- The smoke also proves manifest scale propagation for the sampled object and confirms the converted USD exists before the RL/render validation stage.

Next:
- Launch the video behavior smoke with the raised Franka base and revised reset/grasp validation semantics.

## 2026-06-13 - Add explicit rendered validation check

Goal:
- Close the validation gap where physics/RL checks passed without proving rendered RGB output is nonblank.

Change:
- Added `--render_check` and `--render_check_frames` to `dextrah_lab/rl_games/validate_franka_multi_object_grasp_env.py`.
- Render check uses `render_mode="rgb_array"`, captures frames via `env.render()`, verifies finite shape/statistics, and writes frame artifacts under `render_check/`.
- Added `RENDER_CHECK` and `RENDER_CHECK_FRAMES` to `cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`.
- Documented `--render_check` in the README validation command.

Analysis:
- Earlier environment validation proved asset loading, rigid-object simulation, reset geometry, finite observations/rewards, grasp-prior reset, and rollout stability.
- It did not prove that visual meshes render correctly; this check is now an explicit pre-training gate.

Next:
- Run `RENDER_CHECK=True` validation on the 4-object cluster smoke manifest.
- After full asset staging finishes, run the same rendered validation on a sampled full-manifest subset before training.

## 2026-06-13 - Scored grasp-contact video selector

Goal:
- Fix the remaining `grasp_contact.mp4` artifact where the selected prior passed static IK/prior checks but approached a side protrusion, dragged the object about 10 cm, and hit pre-lift termination.

Change:
- Added snapshot/restore and non-rendered candidate scoring to `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`.
- The contact selector now samples grasp-prior resets after object settling, rolls each candidate briefly without rendering, rejects candidates with termination/object drag/table contact, restores the best candidate state, and records the MP4 from that same candidate.
- Added `GRASP_CONTACT_SCORE_STEPS` plumbing to `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`.

Version Control:
- local_commit: `c674494fbc3ac857f6858227a108401146f84ae7`
- remote_commit: `c674494fbc3ac857f6858227a108401146f84ae7`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- local: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py && bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`

Command / Job:
- command: `NUM_ENVS=4 MAX_OBJECTS=4 RESET_CYCLES=2 SETTLE_STEPS=96 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=8 PERTURB_LINEAR_VELOCITY=0.45 PERTURB_LATERAL_VELOCITY=0.15 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=90 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=240 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=128 GRASP_RESET_MIN_PREGRASP_Z=0.10 GRASP_CONTACT_SCORE_STEPS=60 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json CODE_COMMIT=c674494fbc3ac857f6858227a108401146f84ae7 sbatch --partition=batch --time=0-00:45:00 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1028888`
- run_name: `franka_multi_video_scored_contact_4obj_dextrah-multiobject-grasp-prior-20260613T003321Z_20260613_001201`
- status: passed.
- Slurm state: `COMPLETED`, exit code `0:0`, elapsed `00:01:22`.
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1028888.out`

Result:
- `video_metrics.json` overall `passed=true`.
- `reset_settle`: passed; `done_count=0`, `object_xy_delta_max=1.54e-05`, `bottom_clearance_min=-0.00403`.
- `perturbation`: passed; `done_count=0`, `object_xy_delta_max=0.07945`, `bottom_clearance_min=-0.00418`.
- `grasp_contact`: passed; `selected_done_count=0`, `selected_object_xy_delta_max=0.00451` with threshold `0.06`, `finger_table_clearance_min=0.03809`, `bottom_clearance_min=-0.00560`.
- Contact selector chose a scored candidate from selection attempt `4`; the non-rendered probe also passed with `selected_object_xy_delta_max=0.00688`.

Local Artifacts:
- `local_results/video_scored_1028888/reset_settle.mp4`
- `local_results/video_scored_1028888/perturbation.mp4`
- `local_results/video_scored_1028888/grasp_contact.mp4`

Viewer URLs:
- `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/video_scored_1028888/reset_settle.mp4`
- `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/video_scored_1028888/perturbation.mp4`
- `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/video_scored_1028888/grasp_contact.mp4`

Visual Inspection:
- `grasp_contact` first/mid/last frames show no mid-video object teleport/reset, no large lateral shove, and no obvious gripper/table or gripper/object penetration.
- `reset_settle` and `perturbation` remain visually consistent with the prior accepted videos.

## 2026-06-13 - Trimesh stable-pose placement validator

Goal:
- Before wiring stable poses into RL resets, test whether trimesh-computed stable poses actually remain stable in Isaac when objects are placed directly at the computed pose.

Scope Clarification:
- Use a small set of objects from the manifest, not physically small objects.
- Initial target is the existing 4-object staged GraspGen smoke manifest.

Change:
- Added `dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`.
  - Filters the manifest to `MAX_OBJECTS` or explicit UUIDs.
  - Loads each `raw_object_path` with `trimesh`, applies the manifest scale, computes stable poses, and writes `stable_pose_cache/<uuid>.npz`.
  - Instantiates the existing Franka multi-object Isaac Lab env only as a USD/PhysX loader.
  - Overrides object root states directly to the computed stable pose, then manually steps physics without Gym auto-reset.
  - Reports root/center XY drift, root Z drift, angular drift, bottom clearance, velocity, and done counts.
- Added `cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`.
  - Runs the validator on l401 with all outputs under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations`.

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`

Next:
- Commit, deploy to l401, and run the 4-object stable-pose placement smoke with rendered frames.

## 2026-06-13 - 4-object trimesh stable-pose placement smoke launch

Goal:
- Test whether a small set of GraspGen objects placed exactly at trimesh stable poses remain stable in Isaac without reset-time settling.

Version Control:
- local_commit: `36b918013c5c96183192e9547c89f2b5f92f3f02`
- remote_commit: `36b918013c5c96183192e9547c89f2b5f92f3f02`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 SETTLE_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=36b918013c5c96183192e9547c89f2b5f92f3f02 sbatch --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028890`
- status: failed before validator startup.
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028890.out`

Result:
- Slurm state: `FAILED`, exit code `127:0`, elapsed `00:00:19`.
- key evidence: `/usr/bin/bash: line 19: python: command not found`

Analysis:
- The failure happened in the wrapper while printing the `trimesh` version. The Isaac Lab container command path uses `/isaac-sim/python.sh`; this was not an Isaac/PhysX or stable-pose validator failure.

Next:
- Replace the wrapper's plain `python` call with `/isaac-sim/python.sh`, commit, redeploy to the l401 agent worktree, and relaunch the same 4-object stable-pose placement smoke.

## 2026-06-13 - Stable-pose wrapper fix and relaunch

Goal:
- Relaunch the same small-set stable-pose placement validation after fixing the wrapper-only Python entrypoint failure.

Change:
- Changed `cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` to use `/isaac-sim/python.sh` for the `trimesh` version probe.

Version Control:
- local_commit: `cd2eab4c48ba2cd882355edc3f09b5c41c52c829`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: GitHub SSH fetch failed on l401, so commit was transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_cd2eab4.bundle` and fetched into the agent worktree.
- remote_commit: `cd2eab4c48ba2cd882355edc3f09b5c41c52c829`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 SETTLE_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=cd2eab4c48ba2cd882355edc3f09b5c41c52c829 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028891`
- run_name: `graspgen_stable_pose_validate_1028891_20260613_004244`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028891.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028891_20260613_004244`
- status: failed before validator startup.

Result:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:00:22`.
- key evidence: `/isaac-sim/kit/python/bin/python3: can't open file '/code/dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py': [Errno 2] No such file or directory`
- log evidence: wrapper printed `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`, and container `git rev-parse HEAD` printed canonical commit `378b722a82a42b293b7eea9f27629502cbf44d19`, not the agent commit.

Analysis:
- The job was submitted from the l401 agent worktree, but the wrapper default still mounted the canonical checkout into `/code`. The new validator file only exists in the agent worktree, so the container could not start the validator.

Next:
- Make `CODE_NFS` default to the Slurm submit directory (`SLURM_SUBMIT_DIR`, falling back to `PWD`) while still allowing an explicit override, commit, redeploy, and relaunch.

## 2026-06-13 - Stable-pose submit-checkout mount relaunch

Goal:
- Relaunch the same small-set stable-pose validation with the container source mount pointing at the agent checkout.

Change:
- `cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` now defaults `CODE_NFS` to `SLURM_SUBMIT_DIR`/`PWD` instead of the canonical `/lustre/.../src/DEXTRAH` checkout.

Version Control:
- local_commit: `720c6ced209abc6b69172c7b0486a6cb2b6d0a66`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_720c6ce.bundle` and fetched into the l401 agent worktree.
- remote_commit: `720c6ced209abc6b69172c7b0486a6cb2b6d0a66`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 SETTLE_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=720c6ced209abc6b69172c7b0486a6cb2b6d0a66 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028892`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028892.out`
- run_name: `graspgen_stable_pose_validate_1028892_20260613_004439`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028892_20260613_004439`
- status: canceled for validator scalability fix.

Result:
- Slurm state: `CANCELLED`, elapsed `00:02:22`.
- key evidence: validator started correctly, mounted the agent checkout, wrote `selected_manifest.json`, and wrote one cache file for `7195ed3346a445448308febe833c180a`.
- It then spent about two minutes computing the next full visual-mesh stable pose; the second selected OBJ has about `27,746` vertices and `54,756` faces.

Analysis:
- This was not a physics failure. It exposed a precompute scalability issue: the validator computed stable poses on the full visual mesh, which is not the right default for many GraspGen objects or the full dataset.
- Stable support orientations should be computed on convex hull geometry, while table-clearance placement and drift metrics should still use the full scaled visual vertices.

Next:
- Add convex-hull stable-pose mode with per-object timing/logging, keep full-vertex placement metrics, redeploy, and relaunch the same 4-object smoke.

## 2026-06-13 - Convex-hull stable-pose smoke relaunch

Goal:
- Validate a small set of GraspGen objects placed exactly at trimesh stable poses computed on convex-hull geometry, while still evaluating placement and drift with full scaled visual vertices.

Change:
- Added `--stable_pose_mesh_mode` to `validate_graspgen_stable_pose_resets.py`, defaulting to `convex_hull`.
- Added per-object mesh/hull/timing logs and saved pose mesh metadata in the cache/results.
- Added `STABLE_POSE_MESH_MODE` wrapper plumbing.

Version Control:
- local_commit: `0fc342d3e571db8c92342288e3e9a7e4cdc188cc`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_0fc342d.bundle` and fetched into the l401 agent worktree.
- remote_commit: `0fc342d3e571db8c92342288e3e9a7e4cdc188cc`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=0fc342d3e571db8c92342288e3e9a7e4cdc188cc sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028893`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028893.out`
- run_name: `graspgen_stable_pose_validate_1028893_20260613_004824`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028893_20260613_004824`
- status: failed metrics after producing caches/frames.

Result:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:00:57`; the Python validator step itself completed and wrote metrics/frames, then the wrapper failed because metrics did not pass.
- Stable-pose precompute was fast with convex hulls:
  - `7195ed3346a445448308febe833c180a`: hull `169` vertices / `334` faces, stable poses in `0.060s`.
  - `1d489db9cdc24161a7537926a20bb17b`: hull `5160` vertices / `10316` faces, stable poses in `2.351s`.
  - `96ae0ff853734df0b10a827307949c87`: hull `119` vertices / `234` faces, stable poses in `0.049s`.
  - `30700bc210844bdc991a5ccf16b6379f`: hull `1372` vertices / `2740` faces, stable poses in `0.533s`.
- Aggregate metrics: `root_xy_delta_max=0.00397m`, `center_xy_delta_max=0.00408m`, `root_z_delta_max=0.00459m`, `bottom_clearance_min=-0.00416m`, `angular_delta_deg_max=6.04`, `final_object_speed_max=0.04977m/s`, `done_count=476`.
- Local artifacts fetched to `local_results/stable_pose_1028893/`; viewer video URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_1028893/stable_pose.mp4`

Analysis:
- The visible env-0 object starts above the table and remains visually on the table, but the rendered video only shows env 0. The failed aggregate metrics likely come from another parallel env.
- Task-level `done_count` is not a clean passive-stability gate because `_get_dones()` includes RL task conditions like pre-lift drag and finger/table termination. It should be diagnostic unless explicitly requested.

Next:
- Add per-env/object metrics and per-env rendered frames so the unstable object/rank is identifiable. Keep hard pass gates on drift, table clearance, angular drift, and final object speed.

## 2026-06-13 - Per-env stable-pose diagnostics relaunch

Goal:
- Re-run the same 4-object, rank-0 stable-pose smoke with per-env/object metrics and per-env rendered frames.

Change:
- Added per-env stability summaries with UUID, pose rank/probability, drift, angular drift, bottom clearance, final speed, and task done count.
- Render capture now saves `frames/env_<id>/frame_<idx>.png` for each parallel environment and still writes root `frames/frame_<idx>.png` for env 0.
- `done_count` is diagnostic unless `--fail_on_task_done` is set.

Version Control:
- local_commit: `a947d09a064b2dfa99d6537ffad11257d4b42905`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_a947d09.bundle` and fetched into the l401 agent worktree.
- remote_commit: `a947d09a064b2dfa99d6537ffad11257d4b42905`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=a947d09a064b2dfa99d6537ffad11257d4b42905 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028894`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028894.out`
- run_name: `graspgen_stable_pose_validate_1028894_20260613_005332`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028894_20260613_005332`
- status: failed metrics after producing per-env artifacts.

Result:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:01:03`; Python step wrote metrics and `55` frame files.
- Per-env results:
  - env 0 / `7195ed3346a445448308febe833c180a` / rank 0: passed; root XY `0.00005m`, angular `0.68deg`, final speed `0.00084m/s`.
  - env 1 / `1d489db9cdc24161a7537926a20bb17b` / rank 0: failed angular drift; root XY `0.00397m`, angular `6.04deg`, final speed `0.00068m/s`.
  - env 2 / `96ae0ff853734df0b10a827307949c87` / rank 0: failed final speed; root XY `0.00002m`, angular `0.09deg`, final speed `0.04977m/s`.
  - env 3 / `30700bc210844bdc991a5ccf16b6379f` / rank 0: passed; root XY `0.00170m`, angular `2.59deg`, final speed `0.00310m/s`.
- Local artifacts fetched to `local_results/stable_pose_1028894/`.
- Viewer URLs:
  - env 1: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_1028894/env_01.mp4`
  - env 2: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_1028894/env_02.mp4`

Analysis:
- Videos show no bounce-away, no table penetration, and no robot/object contact. The failed cases are mild rank-0 settling/contact jitter, not gross initialization failure.
- To make resets robust for RL, the cache should not blindly use only the top probability stable pose if other ranks are more stable in PhysX.

Next:
- Run a non-rendered `STABLE_POSE_COUNT=3` candidate search on the same four objects to see whether a stable rank exists for each object before designing cache selection.

## 2026-06-13 - Stable-pose rank candidate search launch

Goal:
- Test the top three trimesh stable-pose ranks per object without rendering to identify stable candidates for the small object set.

Version Control:
- remote_commit: `a947d09a064b2dfa99d6537ffad11257d4b42905`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=3 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 RENDER_FRAMES=False CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=a947d09a064b2dfa99d6537ffad11257d4b42905 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028895`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028895.out`
- run_name: `graspgen_stable_pose_validate_1028895_20260613_005752`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028895_20260613_005752`
- status: failed metrics as expected for candidate search.

Result:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:00:46`.
- Candidate pass table:
  - `7195ed3346a445448308febe833c180a`: ranks `0`, `1`, and `2` passed.
  - `1d489db9cdc24161a7537926a20bb17b`: ranks `0`, `1`, and `2` all failed; rank 0 was closest with root XY `0.0040m`, angular `6.04deg`, final speed `0.0007m/s`.
  - `96ae0ff853734df0b10a827307949c87`: rank 0 failed due final speed `0.0498m/s`; ranks `1` and `2` passed.
  - `30700bc210844bdc991a5ccf16b6379f`: rank 0 passed; ranks `1` and `2` failed bottom clearance (`-0.0066m`).

Analysis:
- Candidate search helps for the long thin `96ae...` object, where rank 1 is stable.
- The rounded `1d489...` object appears to settle from the theoretical convex-hull stable pose into a nearby PhysX-stable pose. Replaying the post-settle root pose is the correct next test for a cache-based reset: precompute once, then reset directly to the settled root state.

Next:
- Add a settled-pose replay mode: first place from trimesh stable poses, settle, cache final local root poses/quaternions, then reset to those cached poses and verify they remain stable.

## 2026-06-13 - Settled-pose replay implementation

Goal:
- Validate the cache strategy needed for RL resets: use trimesh poses only to discover stable candidates, then cache and replay PhysX-settled root states.

Change:
- Added `--settled_replay_steps` to `validate_graspgen_stable_pose_resets.py`.
- The validator now records final local root positions/quaternions from the first rollout.
- If replay steps are requested, it resets objects to those cached settled root states, zeros velocities, and runs a second stability rollout.
- Added `SETTLED_REPLAY_STEPS` wrapper plumbing.

Next:
- Run local/remote checks, commit, deploy, and relaunch a rendered 4-object settled-replay validation.

## 2026-06-13 - Rendered settled-pose replay validation launch

Goal:
- Verify that cached post-settle root poses are stable when replayed directly, solving the object-motion issue for reset-time grasp alignment.

Version Control:
- local_commit: `777bf5cc78010a48c240e8818de5d7ca3b5bc5ef`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_777bf5c.bundle` and fetched into the l401 agent worktree.
- remote_commit: `777bf5cc78010a48c240e8818de5d7ca3b5bc5ef`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=777bf5cc78010a48c240e8818de5d7ca3b5bc5ef sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028897`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028897.out`
- run_name: `graspgen_stable_pose_validate_1028897_20260613_010150`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028897_20260613_010150`
- status: failed settled replay metrics for one rank-0 object.

Result:
- Slurm state: `FAILED`, exit code `1:0`, elapsed `00:01:12`.
- First rollout matched the earlier rank-0 result: `1d489...` failed by angular drift and `96ae...` failed final speed.
- Settled replay result:
  - env 0 / `7195ed3346a445448308febe833c180a`: passed.
  - env 1 / `1d489db9cdc24161a7537926a20bb17b`: passed after replay; angular drift dropped from `6.04deg` to `0.069deg`.
  - env 2 / `96ae0ff853734df0b10a827307949c87`: still failed final speed at `0.0498m/s`.
  - env 3 / `30700bc210844bdc991a5ccf16b6379f`: passed.

Analysis:
- Caching the post-settle root pose solves the rounded-object mismatch between trimesh convex-hull pose and PhysX settled orientation.
- The long thin `96ae...` object should use rank 1 rather than rank 0; rank search job `1028895` showed rank 1 passes the stability gates.

Next:
- Add pose-rank overrides and decouple computed pose count from rollout pose count. Compute at least two poses, roll out one pose per object, override `96ae0ff853734df0b10a827307949c87` to rank 1, then rerun rendered settled replay.

## 2026-06-13 - Stable-pose rank override implementation

Goal:
- Support selecting a PhysX-stable pose rank per object while still computing/caching multiple trimesh candidates.

Change:
- Added `--rollout_pose_count` to decouple number of computed poses from number of rollout candidates.
- Added `--stable_pose_rank_overrides` with `UUID:RANK` entries.
- Added `ROLLOUT_POSE_COUNT` and `STABLE_POSE_RANK_OVERRIDES` wrapper plumbing.

Next:
- Run checks, commit, deploy, and validate the small set using rank override `96ae0ff853734df0b10a827307949c87:1`.

## 2026-06-13 - Rank-overridden settled replay validation launch

Goal:
- Verify the small set passes when using the selected stable rank for the long `96ae...` object and replaying cached settled poses.

Version Control:
- local_commit: `c34ed5198a5729fb405559b12d57d41b969430c9`
- push: pushed to `origin/codex/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z`
- remote_deploy: transferred as Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/dextrah_stable_pose_c34ed51.bundle` and fetched into the l401 agent worktree.
- remote_commit: `c34ed5198a5729fb405559b12d57d41b969430c9`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z`

Validation:
- local: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- local: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- local: `git diff --check`
- remote: `python3 -m py_compile dextrah_lab/rl_games/validate_graspgen_stable_pose_resets.py`
- remote: `bash -n cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Command / Job:
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json MAX_OBJECTS=4 STABLE_POSE_COUNT=2 ROLLOUT_POSE_COUNT=1 STABLE_POSE_RANK_OVERRIDES=96ae0ff853734df0b10a827307949c87:1 STABLE_POSE_MESH_MODE=convex_hull SETTLE_STEPS=240 SETTLED_REPLAY_STEPS=240 RENDER_FRAMES=True CAPTURE_INTERVAL=24 TABLE_CLEARANCE=0.002 CODE_COMMIT=c34ed5198a5729fb405559b12d57d41b969430c9 sbatch --parsable --partition=batch --time=0-00:45:00 cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`
- job_id: `1028898`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1028898.out`
- run_name: `graspgen_stable_pose_validate_1028898_20260613_010532`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_pose_validate_1028898_20260613_010532`
- status: passed.

Result:
- Slurm state: `COMPLETED`, exit code `0:0`, elapsed `00:01:13`.
- Metrics: top-level `passed=true`.
- Discovery rollout:
  - `96ae0ff853734df0b10a827307949c87` used rank 1 and passed immediately.
  - `1d489db9cdc24161a7537926a20bb17b` still settled by `6.04deg`, which is expected discovery motion and is why the post-settle pose is cached.
- Settled replay rollout passed for all four objects.
- Settled replay summary: `root_xy_delta_max=1.41e-05m`, `center_xy_delta_max=1.05e-05m`, `root_z_delta_max=3.46e-06m`, `angular_delta_deg_max=0.0791`, `bottom_clearance_min=-0.00416m`, `final_object_speed_max=0.00401m/s`.
- Per-env settled replay:
  - `7195ed3346a445448308febe833c180a` rank 0 passed.
  - `1d489db9cdc24161a7537926a20bb17b` rank 0 passed after settled-pose replay.
  - `96ae0ff853734df0b10a827307949c87` rank 1 passed.
  - `30700bc210844bdc991a5ccf16b6379f` rank 0 passed.

Local Artifacts:
- Fetched results: `local_results/stable_pose_1028898/`
- Settled replay grid video: `local_results/stable_pose_1028898/settled_replay_grid.mp4`
- Discovery grid video: `local_results/stable_pose_1028898/stable_pose_discovery_grid.mp4`
- Slurm log: `local_results/stable_pose_1028898/slurm.out`

Viewer URLs:
- settled replay grid: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_1028898/settled_replay_grid.mp4`
- discovery grid: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-20260613T003321Z/local_results/stable_pose_1028898/stable_pose_discovery_grid.mp4`

Visual Inspection:
- Settled replay first/last grid frames show all four objects on top of the table with the gripper clear of contact.
- No visible object bounce-away, table sticking/penetration, or robot/object contact is visible in replay.

Analysis:
- The correct reset strategy is to use trimesh convex-hull stable poses as discovery candidates, simulate-settle each object once, cache the post-settle local root pose/quaternion, and reset to that cached state for RL/grasp-prior alignment.
- A rank override/selection step is needed because the top-probability trimesh pose is not always the most stable PhysX pose.

Next:
- Wire this settled-pose cache and rank selection into the multi-object RL reset path so grasp-prior robot reset is computed from the actual cached object pose, not the ideal initial pose.

## 2026-06-13 - Rendered environment validation smoke launch

Goal:
- Verify rendered RGB output is nonblank for the multi-object Franka environment using the already staged 4-object smoke manifest.

Command / Job:
- command: `RENDER_CHECK=True RENDER_CHECK_FRAMES=2 CAPTURE_VIDEO=False NUM_ENVS=4 NUM_STEPS=40 MAX_OBJECTS=4 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_223457/manifest.json sbatch --export=ALL cluster/sbatch_validate_franka_multi_object_grasp_env_1gpu.sh`
- job_id: 1028838
- run_name: `franka_multi_env_render_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_225022`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_env_render_smoke_dextrah-multiobject-grasp-prior-20260613T003321Z_20260612_225022/metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_1028838.out`

Result:
- status: running/queued; monitoring in progress.

## 2026-06-13T22:38:41Z - Contact-prior validation with relaxed topdown filter

Goal:
- Determine whether the failed `grasp_contact` video on commit `2d7f495` is caused by the validation-only `GRASP_RESET_MIN_PREGRASP_Z=0.70` filter selecting poor vertical pinches on elongated objects.

Hypothesis:
- The contact-enriched priors and stable object resets may be correct, but the strict top-down filter prevents valid side/top-side GraspGen contacts from being selected.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_relaxedz_2d7f495_20260613_223841 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=120 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.025 GRASP_WARMSTART_LIFT_ACTION_Z=0.30 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=128 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=256 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.55 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=80 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029098`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_relaxedz_2d7f495_20260613_223841`
- expected_artifacts: `video_metrics.json`, `reset_settle`, `perturbation`, and `grasp_contact` frame sequences.

Result:
- status: failed before environment creation.
- evidence: Slurm job `1029098` exited `FAILED 1:0` after `00:00:19`; log shows `/code/dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` was missing because `CODE_NFS` was not exported into the batch environment and the wrapper mounted the default checkout.
- next: relaunch the same config with `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613` passed as a batch environment variable.

## 2026-06-13T22:39:55Z - Contact-prior relaxed topdown relaunch with explicit code mount

Goal:
- Re-run the relaxed-topdown validation with the correct detached source tree mounted into the container.

Version Control:
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit_check: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_relaxedz_2d7f495_20260613_223955 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=120 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.025 GRASP_WARMSTART_LIFT_ACTION_Z=0.30 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=128 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=256 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.55 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=80 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029099`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_relaxedz_2d7f495_20260613_223955`

Result:
- final_status: failed on `grasp_contact` metrics.
- Slurm: `1029102` exited `FAILED 1:0` after `00:01:47`; failure was metrics-gated.
- Metrics:
  - `reset_settle`: passed.
  - `perturbation`: passed.
  - `grasp_contact`: selected `7195ed3346a445448308febe833c180a` sample `62`, `selected_quality_success=true`, `selected_gripper_width_min=0.00021m`, `selected_object_xy_delta_max=0.0052m`, but `selected_lift_height_max=0.0m`.

Analysis:
- The intermediate gate rejected the previous `96ae...` end-pinch but selected another near-end contact on `7195...`. Frames show stable reset and no obvious penetration or teleport, but the fingers close near an end feature and do not lift the object.
- Contact/reset geometry is stable, but the quality gate is not sufficient to identify liftable contacts.

Next:
- Test the missing ablation: `center_frac=0.30` with relaxed `min_pregrasp_z=0.15` to see whether centered contacts exist when not requiring a nearly vertical pregrasp.

## 2026-06-13T22:54:21Z - Strict-center relaxed-topdown contact validation

Goal:
- Check whether stricter centered contacts become available when the topdown gate is relaxed.

Hypothesis:
- The prior `center_frac=0.30` run found no quality candidates because it also required `min_pregrasp_z=0.70`; with `min_pregrasp_z=0.15`, the same centered candidates may become usable without selecting end contacts.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_center030_relaxedz_2d7f495_20260613_225421 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=192 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=100 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029103`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_center030_relaxedz_2d7f495_20260613_225421`

Result:
- final_status: failed on `grasp_contact`.
- Slurm: `1029103` exited `FAILED 1:0` after `00:01:33`; failure was metrics-gated.
- Metrics:
  - `reset_settle`: passed.
  - `perturbation`: passed.
  - `grasp_contact`: `selection_failure=no_quality_candidate` with `center_frac=0.30`, `min_pregrasp_z=0.15`, `min_width=0.02`.

Analysis:
- Relaxing topdown alone does not recover quality candidates under the strict center gate.
- The `0.02m` contact-width floor may be too high for centered grasps on this smoke set; many centered prior contacts are narrower.

Next:
- Test strict center plus default-like `min_width=0.008` before patching source.

## 2026-06-13T22:57:14Z - Strict-center default-width contact validation

Goal:
- Check whether the strict center gate becomes usable when the contact-width floor matches the environment default.

Hypothesis:
- `GRASP_RESET_MIN_WIDTH=0.02` rejects many centered candidates. Lowering it to `0.008` may allow centered rod/body contacts while the `0.30` center gate still rejects the known end contacts.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_center030_minwidth008_2d7f495_20260613_225714 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=192 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.008 GRASP_CONTACT_SCORE_STEPS=100 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029104`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_center030_minwidth008_2d7f495_20260613_225714`

Result:
- final_status: canceled after `00:03:21`.
- Slurm: `1029104` was canceled manually after no metric output during extended grasp-contact candidate scoring.
- Metrics:
  - No `video_metrics.json` was produced before cancellation.

Analysis:
- Lowering `GRASP_RESET_MIN_WIDTH` likely exposed many candidate rollouts, making brute-force validation too slow without additional diagnostics.
- Parameter-only probing is no longer efficient. The source should expose candidate/reset diagnostics and make the quality gate more contact-aware before another validation run.

Next:
- Patch source to record selected contact geometry and candidate counts, then revise quality checks so “quality” means a plausible liftable contact, not only IK/topdown/geometric proximity.

## 2026-06-13T23:05:11Z - Contact-reference quality patch validation

Goal:
- Validate the source patch that uses contact references for reset-quality distances, records candidate diagnostics, increases center penalty, and sets the multi-object default center gate to `0.30`.

Hypothesis:
- Measuring reset quality against the selected contact reference should reject missed-contact poses and make diagnostics explain remaining failures. The stricter center gate should prevent the previous end-contact selections.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `b3a11418dd04ef904740d5d1b69bb7279d805568`
- push/pull: pushed to `origin/codex/multiobject-training-yaw-20260613`; l401 direct GitHub fetch failed due publickey auth, so deployed exact commit via git bundle.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `b3a11418dd04ef904740d5d1b69bb7279d805568`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=b3a11418dd04ef904740d5d1b69bb7279d805568 RUN_NAME=multiobject_contactref_quality_b3a1141_20260613_230511 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=120 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=32 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.008 GRASP_CONTACT_SCORE_STEPS=40 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029105`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactref_quality_b3a1141_20260613_230511`

Result:
- status: submitted on l401, monitoring in progress.

## 2026-06-13T23:21:35Z - Moderate close/lift validation result

Result:
- job_id: `1029107`
- final_status: failed only `grasp_contact`.
- Slurm: `FAILED 1:0` after `00:02:00`; failure was metrics-gated, not a simulator crash.
- Metrics:
  - `reset_settle`: passed.
  - `perturbation`: passed.
  - `grasp_contact`: failed; selected `96ae0ff853734df0b10a827307949c87` sample `1154`, `selected_lift_height_max=0.0413m` vs `0.12m`, `selected_object_xy_delta_max=0.0682m` vs `0.06m`, `selected_candidate_valid_count=2`, `target_ee_to_ee_dist=2.46e-7`.

Analysis:
- The validation harness fix is effective: the recorded reset state matches the selected target and there is no mid-video teleport. However, the same thin-object prior still slips under both aggressive and moderate close/lift settings. The remaining failure is a real grasp-quality/control limitation for this object/prior, not the earlier object settling/reset bug.

Next:
- Do not merge as a fully validated grasp-contact pass. Either relax the validation to a physics/contact-only artifact if that is the intended criterion, or add a real candidate-quality/control fix before merging and launching training.

## 2026-06-13T23:20:01Z - Moderate close/lift grasp-contact validation

Goal:
- Test whether the corrected grasp-contact validation still fails because the diagnostic warmstart closes too aggressively on a thin object.

Hypothesis:
- The selected `96ae...` sample `1154` has a contact width of about `8.7mm`. Forcing `GRASP_WARMSTART_CLOSE_WIDTH=0.0` may squeeze the object out. Preserving a small residual width and reducing lift velocity may produce cleaner contact/lift without changing the environment source.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- implementation_commit: `c7cacbd23afa839e46f3cf0b75eb3b806884ad8b`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `c7cacbd23afa839e46f3cf0b75eb3b806884ad8b`

Command / Job:
- previous_job_id: `1029106`
- previous_result: failed only `grasp_contact`; reset/perturbation passed; target reset was preserved with `target_ee_to_ee_dist=2.46e-7`, but the selected thin object slipped and lifted only `0.0337m`.
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=c7cacbd23afa839e46f3cf0b75eb3b806884ad8b RUN_NAME=multiobject_contact_width006_lift045_c7cacbd_20260613_232001 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.006 GRASP_WARMSTART_LIFT_ACTION_Z=0.45 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=32 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.008 GRASP_CONTACT_SCORE_STEPS=80 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029107`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contact_width006_lift045_c7cacbd_20260613_232001`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029107.out`

Result:
- status: submitted on l401, monitoring in progress.

## 2026-06-13T23:13:14Z - Static-warmup grasp-contact validation rerun

Goal:
- Revalidate the same four-object smoke set after fixing the grasp-contact validation harness.

Hypothesis:
- Preserving the selected reset state during render warmup and scoring through the lift phase will either produce a clean `grasp_contact` pass or expose a real grasp-prior/control issue without the previous validation artifact.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `c7cacbd23afa839e46f3cf0b75eb3b806884ad8b`
- push/pull: pushed to `origin/codex/multiobject-training-yaw-20260613`; deployed to l401 via `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah_c7cacbd.bundle`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `c7cacbd23afa839e46f3cf0b75eb3b806884ad8b`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=c7cacbd23afa839e46f3cf0b75eb3b806884ad8b RUN_NAME=multiobject_contact_staticwarmup_c7cacbd_20260613_231314 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=120 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=32 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.008 GRASP_CONTACT_SCORE_STEPS=40 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029106`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contact_staticwarmup_c7cacbd_20260613_231314`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029106.out`

Result:
- status: submitted on l401, monitoring in progress.

## 2026-06-13T23:10:16Z - Fix grasp-contact validation state mutation and lift scoring

Goal:
- Make the grasp-contact validation video start from the selected reset state and score candidates through the lift phase before deciding whether the environment is mergeable.

Hypothesis:
- Job `1029105` failed partly because the validation harness advanced physics during render warmup after restoring the selected state, so the recorded `grasp_contact` rollout started from a different object/robot pose than the selector scored. The selector also used `GRASP_CONTACT_SCORE_STEPS=40`, while the validation warmstart did not enter lift until after approach/close, so the best candidate was selected mostly on pre-lift contact.

Change:
- Added static render warmup for `grasp_contact`, captured an initial reset frame before stepping, made scorer steps cover the full configured warmstart sequence, and fixed validation warmstart step allocation so lift lasts through the requested `grasp_steps`.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- base_commit: `b3a11418dd04ef904740d5d1b69bb7279d805568`
- implementation_commit: pending
- changed_files: `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, this worklog

Command / Job:
- previous_job_id: `1029105`
- previous_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactref_quality_b3a1141_20260613_230511`
- checks: `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`; `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`; `git diff --check`

Result:
- status: patch checks passed locally.
- previous_metrics: `1029105` passed `reset_settle` and `perturbation`, failed only `grasp_contact`; selected `96ae0ff853734df0b10a827307949c87` sample `1154`, `selected_lift_height_max=0.0278m` vs `0.12m`, `selected_object_xy_delta_max=0.0582m`, `selected_candidate_valid_count=2`.
- artifact_inspection: first/mid/last frames showed a slender object slipping/tilting rather than a clean lift; final recorded reset geometry did not match the scored probe state because render warmup advanced physics before recording.

Analysis:
- The environment reset still numerically reached the selected pregrasp target in the probe, but validation was not preserving that state for the recorded clip. This made the video evidence unreliable and could also hide good candidates because the selection score did not evaluate lift.

Next:
- Commit this validation fix, deploy the exact commit to the l401 worktree, and rerun the same 4-object smoke before merging to `main`.
- final_status: failed on `grasp_contact` metrics.
- Slurm: `1029100` exited `FAILED 1:0` after `00:02:52`; failure was metrics-gated, not a simulator crash.
- Metrics:
  - `reset_settle`: passed, `object_xy_delta_max=6.33e-05m`, `bottom_clearance_min=-0.00404m`.
  - `perturbation`: passed.
  - `grasp_contact`: selected the same long-object end-pinch sample `96ae...` sample `273`; stronger controller reduced gripper width to `0.013m` and lifted to `0.113m`, but failed `0.12m` lift threshold and dragged object `0.093m` vs `0.06m` threshold.

Analysis:
- The diagnostic controller was partly limiting lift, but the underlying problem is still the selected contact location: it is an end pinch on a 29.6 cm object. Stronger close/lift raises the object but creates large XY drag/torque.
- The repeated sample's contact midpoint is about `0.020m` along the object's long axis while the object center is about `0.148m`, so `grasp_prior_reset_max_center_distance_frac=0.55` is too permissive for elongated objects.

Next:
- Run a tighter center-gate validation with `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30` and larger candidate count before changing source defaults.

## 2026-06-13T22:47:00Z - Contact-prior validation with tighter center gate

Goal:
- Reject long-object end pinches and force contact candidates closer to the object center/COM.

Hypothesis:
- A tighter center gate should either find a balanced candidate that lifts cleanly or mark the bad long-object reset as non-quality so validation selects another object/env.

Version Control:
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_center030_2d7f495_20260613_224700 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=192 GRASP_RESET_MIN_PREGRASP_Z=0.70 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=100 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029101`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_center030_2d7f495_20260613_224700`

Result:
- status: submitted on l401, monitoring in progress.
- final_status: failed on metrics after environment execution.
- Slurm: `1029099` exited `FAILED 1:0` after `00:02:29`; wrapper failed intentionally because `video_metrics.json` had top-level `passed=false`.
- Metrics:
  - `reset_settle`: passed, `object_xy_delta_max=6.33e-05m`, `bottom_clearance_min=-0.00404m`.
  - `perturbation`: passed, `object_xy_delta_max=0.121m`, `bottom_clearance_min=-0.00628m`.
  - `grasp_contact`: failed; selected the same `96ae0ff853734df0b10a827307949c87` sample `273`, `selected_lift_height_max=0.0197m` vs `0.12m`, `selected_max_finger_dist_min=0.1697m`, `selected_quality_success=true`.

Analysis:
- Relaxing the validation top-down filter from `0.70` to `0.15` did not change the selected contact sample or lift behavior.
- The failure is not caused by the validation-only top-down filter. The multi-object quality gate still accepts a long-object candidate using object-size-scaled, object-center-based distances even though it does not produce a lift.

Next:
- Patch the multi-object reset/debug path to expose contact-reference geometry and tighten/reset-score candidates around sampled contacts rather than only the object center.

## 2026-06-13T22:51:14Z - Intermediate center/topdown contact validation

Goal:
- Test whether the current contact-aware reset code can pass grasp-contact validation without source changes by using a softer topdown filter and an intermediate center gate.

Hypothesis:
- `center_frac=0.30` is too strict and yields no quality candidates, while `0.55` accepts a long-object end pinch. An intermediate `0.42` gate with `min_pregrasp_z=0.15` may keep enough candidate diversity while rejecting the most extreme end contacts.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-multiobject-main-20260613`
- branch: `codex/multiobject-training-yaw-20260613`
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_center042_relaxedz_2d7f495_20260613_225114 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=192 GRASP_RESET_MIN_PREGRASP_Z=0.15 GRASP_RESET_CANDIDATE_COUNT=512 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.42 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=100 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029102`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_center042_relaxedz_2d7f495_20260613_225114`

Result:
- status: submitted on l401, monitoring in progress.

## 2026-06-13T22:43:48Z - Contact-prior validation with stronger close/lift warmstart

Goal:
- Test whether the failed `grasp_contact` is caused by the diagnostic warmstart controller being too weak rather than by the grasp reset geometry.

Hypothesis:
- The selected contact may be physically usable, but `GRASP_WARMSTART_CLOSE_WIDTH=0.025` and `GRASP_WARMSTART_LIFT_ACTION_Z=0.30` do not close/lift enough for the selected GraspGen object.

Version Control:
- implementation_commit: `2d7f495bc812ea77b57689721627800790406c4e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613`
- remote_commit: `2d7f495bc812ea77b57689721627800790406c4e`

Command / Job:
- command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-stable-reset-c3c924f-20260613 CODE_COMMIT=2d7f495bc812ea77b57689721627800790406c4e RUN_NAME=multiobject_contactscore_strongclose_2d7f495_20260613_224348 OBJECT_ASSET_MANIFEST_PATH=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/manifest.json MAX_OBJECTS=4 NUM_ENVS=4 OBJECT_ASSET_ASSIGNMENT=round_robin OBJECT_STABLE_POSE_ENABLED=True OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache OBJECT_STABLE_POSE_RANDOMIZE=False RESET_CYCLES=3 SETTLE_STEPS=72 PERTURB_STEPS=96 PERTURB_PUSH_STEPS=10 PERTURB_LINEAR_VELOCITY=0.60 PERTURB_LATERAL_VELOCITY=0.20 PERTURB_ANGULAR_VELOCITY=4.0 GRASP_STEPS=160 GRASP_OBJECT_SETTLE_STEPS=0 OBJECT_RESET_SETTLE_STEPS=0 GRASP_WARMSTART_CLOSE_WIDTH=0.0 GRASP_WARMSTART_LIFT_ACTION_Z=0.80 CAPTURE_INTERVAL=2 GRASP_RESET_ATTEMPTS=128 GRASP_RESET_MIN_PREGRASP_Z=0.70 GRASP_RESET_CANDIDATE_COUNT=256 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.55 GRASP_RESET_MIN_WIDTH=0.02 GRASP_CONTACT_SCORE_STEPS=100 sbatch --parsable cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- job_id: `1029100`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/multiobject_contactscore_strongclose_2d7f495_20260613_224348`

Result:
- status: submitted on l401, monitoring in progress.
## 2026-06-14T05:40:56Z - Merge main and add RGB teacher task

Goal:
- Resume the user-requested sequence: merge the current multi-object environment to `main`, then launch RL training from a merged `main` commit with object yaw randomization, per-env object/pose variation, and object-conditioned policy inputs.

Hypothesis:
- The environment branch already has correct state-object conditioning and per-reset pose randomization, but successful teacher-scale training should use the RGB teacher stack from the separate RGB branch without merging its unrelated deletions.

Change:
- Fast-forwarded local and remote `main` from `483d0e5` to `c46a58d`.
- Added a minimal RGB teacher stack on top of `main`: `Dextrah-Franka-Multi-Object-RGB-Grasp`, tiled RGB camera config, RGB observation path, `a2c_rgb_resnet` RL-Games model, RGB PPO config, trainer model registration, and A100 wrapper support.
- Kept the stable-pose cache API and validation fixes from `main`; did not merge the full RGB branch because it carries unrelated deletions and dirty local files.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `c46a58d05513d3b33dc1734a78b7b23ed4f25bc0`
- implementation_commit: `7f0708837d20d4572d7e30ffd0fdebf305c166d3`
- push/pull: local commit complete; push pending
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `dextrah_lab/rl_games/a2c_rgb_resnet.py`, `dextrah_lab/rl_games/train.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/agents/rl_games_ppo_franka_multi_object_rgb_grasp_cfg.yaml`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/gym_setup.py`, this worklog

Command / Job:
- checks: `python3 -m py_compile dextrah_lab/rl_games/a2c_rgb_resnet.py dextrah_lab/rl_games/train.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/gym_setup.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh`; `git diff --check`
- stale_job: A100 job `29056648` was a pre-merge RGB run from snapshot `franka-multiobject-rgb-phasegate-2670719`; it was cancelled at epoch `32/200` and saved epoch-25 checkpoint `last_dextrah_franka_multi_object_rgb_grasp_ep_25_rew_117.25747.pth`.

Result:
- status: patch checks passed locally; commit/push and A100 relaunch pending.
- implementation_notes: state task policy observations include object pose via inherited cube observations and append 8 object-specific features; RGB task policy conditions on object appearance/pose through the image and robot proprioception.

Analysis:
- `object_spawn_yaw_randomization_deg=180.0` samples in `[-pi, pi]`, so it covers 360 degrees.
- Object asset assignment is per vectorized env at scene construction because Isaac assets are instantiated per env; reset-time XY/yaw/stable-pose sampling still varies independently per env and episode.
- Early A100 `TERM` signals have repeatedly cancelled runs outside the wrapper's default wall-time requeue window. The next launch should set `REQUEUE_ON_EARLY_TERM=True` so preemption/early termination requeues instead of stopping training.

Next:
- Commit and push the RGB teacher integration, deploy exact `main` commit to an A100-owned worktree, run a small RGB smoke, then launch/resume the 8-GPU teacher run with `REQUEUE_ON_EARLY_TERM=True` and monitor metrics/checkpoints until success.

## 2026-06-14T05:49:00Z - Merged-main RGB smoke hang and CUDA graph default fix

Goal:
- Prove the merged `main` RGB teacher task initializes before launching a longer RL run.

Hypothesis:
- RGB camera observations should not use the CUDA graph path by default. The wrapper intended `USE_CUDA_GRAPH=False` for `Dextrah-Franka-Multi-Object-RGB-Grasp`, but initialized it to `True` before the RGB task branch, so the RGB default never took effect.

Change:
- Changed `cluster/sbatch_train_teacher_8gpu.sh` so `USE_CUDA_GRAPH` defaults after task selection: RGB multi-object training defaults to `False`, other tasks default to `True`, and explicit caller overrides are preserved.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `98c69662f99a468c6fb5fe70a0beae5ba2ba2d16`
- implementation_commit: pending
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, this worklog

Command / Job:
- failed_job_id: `29056877`
- failed_command: `TASK=Dextrah-Franka-Multi-Object-RGB-Grasp`, `MAX_ITERATIONS=2`, `NUM_ENVS=64`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, stable-pose cache enabled, grasp-prior reset enabled, `REQUEUE_ON_EARLY_TERM=True`
- failed_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29056877.out`
- checks: `bash -n cluster/sbatch_train_teacher_8gpu.sh`; `git diff --check`

Result:
- status: failed smoke cancelled after no rl-games result directory and no `Completed setting up the environment` marker.
- key evidence: launch log showed `env.use_cuda_graph=True` for the RGB task; log stopped after headless renderer setup warnings and never reached PPO startup.

Analysis:
- A pre-merge RGB run from commit `3680f4a` reached PPO epochs with `env.use_cuda_graph=False`, so the merged-main smoke was most likely blocked by the wrapper default rather than by asset paths or Slurm.

Next:
- Commit/push the wrapper fix, redeploy the exact commit to the A100 worktree, rerun the two-iteration merged-main smoke, and only then launch the longer run.

## 2026-06-14T06:03:00Z - Retry grasp-prior resets and log candidate counts

Goal:
- Improve merged-main prior-reset behavior before launching long RGB RL training.

Hypothesis:
- The merged-main smoke proved the RGB task is RLable, but `cube_grasp_prior_reset_success_rate=0` because strict contact-aware gates plus only 16 candidates caused every env to fall back to the default robot reset. Retrying failed reset samples and logging candidate gate counts should either recover usable prior resets or expose which gate is blocking them.

Change:
- Added `grasp_prior_reset_attempts` to the multi-object config.
- Added a multi-object reset retry loop that resamples only envs whose prior reset quality failed.
- Added candidate topdown/center/width/valid/fallback count metrics to the grasp-prior reward diagnostics.
- Exposed `GRASP_PRIOR_RESET_ATTEMPTS` in `cluster/sbatch_train_teacher_8gpu.sh`.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `a02cbe6cb70ac8ab2fcceef6620399a31c66c23c`
- implementation_commit: pending
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, this worklog

Command / Job:
- checks: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh`; `git diff --check`
- previous_smoke_job: `29056938`
- previous_smoke_result: completed, PPO epochs `1/2` and `2/2`, checkpoint written, but prior reset success/quality were both `0.0`.

Result:
- status: patch checks passed locally; commit/deploy/re-smoke pending.

Next:
- Commit, push, deploy a new exact commit to A100, run a two-epoch smoke with larger candidate count and reset retries, inspect reset metrics, then launch production if prior resets are nonzero and PPO remains healthy.

## 2026-06-14T06:05:53Z - Launch merged-main RGB training

Goal:
- Start the requested merged-main multi-object Franka RL training after validating the environment, RGB model path, and grasp-prior reset behavior.

Hypothesis:
- The `f1a34bc` retry patch plus `GRASP_PRIOR_RESET_ATTEMPTS=16`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=256`, and `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.42` gives usable prior resets without disabling the contact-aware gate.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`

Command / Job:
- smoke_job: `29056984`
- smoke_run: `franka_multi_rgb_mainf1_retry_smoke_20260614T055940Z`
- smoke_result: completed, epochs `1/2` and `2/2`, finite checkpoint reward `4.8865104`
- smoke_reset_metrics: `reset_success_rate=0.609375`, `quality_success_rate=0.5625`, `candidate_valid_count_mean=31.46875`, `candidate_center_count_mean=151.921875`, `candidate_topdown_count_mean=55.90625`
- production_command: `TASK=Dextrah-Franka-Multi-Object-RGB-Grasp MAX_ITERATIONS=200 NUM_ENVS=64 HORIZON_LENGTH=16 MINIBATCH_SIZE=512 MINI_EPOCHS=2 OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0 OBJECT_ASSET_ASSIGNMENT=random OBJECT_STABLE_POSE_ENABLED=True GRASP_PRIOR_RESET_ATTEMPTS=16 GRASP_PRIOR_RESET_CANDIDATE_COUNT=256 GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.42 REQUEUE_ON_EARLY_TERM=True DEXTRAH_RLGAMES_JSONL_METRICS=True cluster/sbatch_train_teacher_8gpu.sh`
- production_job_id: `29057045`
- production_run: `franka_multi_rgb_mainf1_retry_c42_a16_c256_env64_h16_mb512_train_20260614T060553Z`
- production_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29057045.out`
- production_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_rgb_grasp/franka_multi_rgb_mainf1_retry_c42_a16_c256_env64_h16_mb512_train_20260614T060553Z`

Result:
- status: submitted; monitoring in progress.

Next:
- Monitor startup, PPO metrics, reward/lift/success curves, reset candidate diagnostics, checkpoints, and requeue behavior. Patch/tune/relaunch if rewards stall, resets regress, checkpoints fail, or the job is preempted without clean resume.

## 2026-06-14T06:21:14Z - Stop non-lifting merged-main RGB run

Goal:
- Decide whether the first 200-epoch merged-main RGB run is learning the actual pick-up task or only shaped rewards.

Hypothesis:
- If reset-to-grasp-prior is sufficient, lift height and success should become nonzero by the 75-100 epoch range after the aggregate reward improves.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`

Command / Job:
- job_id: `29057045`
- run: `franka_multi_rgb_mainf1_retry_c42_a16_c256_env64_h16_mb512_train_20260614T060553Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29057045.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_rgb_grasp/franka_multi_rgb_mainf1_retry_c42_a16_c256_env64_h16_mb512_train_20260614T060553Z/metrics/direct_info_rank_0.jsonl`

Result:
- status: failed; terminated instead of letting the allocation run to 200 epochs.
- key evidence: epoch `100` metrics had `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0`, `cube_lift_height=0.0000608`, `cube_grasp_prior_reset_success_rate=0.640625`, `cube_grasp_prior_quality_success_rate=0.59375`.
- checkpoints: epoch `25` reward `119.33778`, epoch `50` reward `670.70465`, epoch `75` reward `701.0449`, epoch `100` reward `652.1903`.
- scheduler_note: first cancel signal triggered the wrapper requeue path; Slurm reported `COMPLETING` after the job step ended, but the node had empty `AllocTRES` and no live `train.py`/`torch.distributed` processes.

Analysis:
- The environment and prior reset path remained healthy enough for PPO, but the policy optimized shaped/stability reward without learning a real lift. Reset-to-pregrasp alone is not enough for this multi-object RGB run.

Next:
- Relaunch from the same merged-main commit with grasp-prior action warm-start enabled for a longer approach/close/lift sequence and monitor whether lift/success become nonzero early.

## 2026-06-14T06:27:42Z - Action-prior smoke and longer training launch

Goal:
- Keep the policy in control while adding a grasp-prior action reward for the approach/close/lift reference sequence, then launch a longer run if the path is healthy.

Hypothesis:
- The no-guidance run optimized shaped/stability rewards but did not discover closing/lifting. A direct action-prior reward should make the policy imitate the sampled grasp-prior sequence without overwriting actions during PPO rollouts.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`

Command / Job:
- failed_smoke_job: `29057370`
- failed_smoke_result: failed before env registration because `CODE_NFS` was not exported and the wrapper mounted canonical `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH` at old commit `378b722`, where `Dextrah-Franka-Multi-Object-RGB-Grasp` was not registered.
- corrected_smoke_job: `29057385`
- corrected_smoke_run: `franka_multi_rgb_mainf1_actionprior_a120_c80_l160_z075_w8_s3_env64_h16_mb512_smoke_20260614T062429Z`
- corrected_smoke_command: `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc TASK=Dextrah-Franka-Multi-Object-RGB-Grasp MAX_ITERATIONS=10 NUM_ENVS=64 HORIZON_LENGTH=16 MINIBATCH_SIZE=512 MINI_EPOCHS=2 GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=8.0 GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS=3.0 GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS=120 GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS=80 GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=160 GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.75 FULL_EXPERIMENT_NAME=... cluster/sbatch_train_teacher_8gpu.sh`
- longer_job: `29057412`
- longer_run: `franka_multi_rgb_mainf1_actionprior_a120_c80_l160_z075_w8_s3_env64_h16_mb512_train_20260614T062742Z`
- longer_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29057412.out`
- longer_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_rgb_grasp/franka_multi_rgb_mainf1_actionprior_a120_c80_l160_z075_w8_s3_env64_h16_mb512_train_20260614T062742Z`

Result:
- corrected_smoke_status: passed, PPO epochs `1/10` through `10/10`, checkpoints at epochs `5` and `10`.
- corrected_smoke_metrics: `cube_grasp_prior_reset_success_rate=0.65625`, `cube_grasp_prior_quality_success_rate=0.546875`, `cube_action_prior_active_rate=0.546875`, `cube_action_prior_reward≈0.30-0.44`; lift phase was not reached in the 10-epoch smoke because the reference lift starts after step `200`.
- longer_status: submitted, monitoring in progress.

Analysis:
- The action-prior code path is healthy when the correct merged-main worktree is mounted. The next decision should be based on whether the longer run reaches the prior lift phase and turns that into nonzero object lift/success.

Next:
- Monitor job `29057412` through startup, first checkpoints, action-prior phase metrics, lift height, success rate, and reset quality. If action prior still fails to produce lifting after the lift phase is active, tune the reference sequence/reward or run a temporary action-warmstart validation to verify the sampled grasps can physically lift the objects.

## 2026-06-14T06:39:54Z - Stop failed action-prior run and launch warm-start validation

Goal:
- Determine whether the lack of lifting is caused by invalid sampled grasps/reset physics or by the policy failing to learn the reference sequence.

Hypothesis:
- If executing the grasp-prior reference sequence directly lifts objects, the environment/grasp initialization is physically usable and the next fix should be stronger policy learning/imitation. If direct execution still does not lift, the reset/grasp quality filter or grasp transform is wrong.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`

Command / Job:
- stopped_job: `29057412`
- stopped_run: `franka_multi_rgb_mainf1_actionprior_a120_c80_l160_z075_w8_s3_env64_h16_mb512_train_20260614T062742Z`
- stopped_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29057412.out`
- stopped_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_rgb_grasp/franka_multi_rgb_mainf1_actionprior_a120_c80_l160_z075_w8_s3_env64_h16_mb512_train_20260614T062742Z/metrics/direct_info_rank_0.jsonl`
- validation_job: `29057602`
- validation_run: `franka_multi_rgb_mainf1_warmstart_validate_a120_c80_l160_z075_env64_h16_mb512_20260614T063954Z`
- validation_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29057602.out`

Result:
- stopped_status: failed, cancelled at epoch `100/400`.
- stopped_metrics_epoch100: `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0`, `cube_lift_height=0.0`, `cube_ee_to_cube_dist=0.8816`, `cube_finger_center_to_cube_dist=0.8686`, `cube_gripper_width=0.0104`.
- stopped_analysis_signal: action-prior made the policy close and command upward motion, but the hand moved away from the object; raw action matching was not enough.
- validation_status: submitted, monitoring in progress.

Analysis:
- The next necessary test is physical execution of the reference sequence. This validation must not be treated as learned-policy success because it overrides policy actions during warm-start.

Next:
- Monitor job `29057602` until warm-start lift phases are logged. If it lifts, implement stronger learning guidance or imitation; if it does not lift, debug grasp/reset geometry and close-width/approach transforms.

## 2026-06-14T06:50:07Z - Warm-start validation outcome and geometry diagnosis

Goal:
- Validate whether directly executing the sampled grasp-prior approach/close/lift sequence can physically lift the GraspGen objects.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `f1a34bcd20d8b33f1cddb5b90a6e220effa9ca18`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`

Command / Jobs:
- rgb_warmstart_job_1: `29057602`
- rgb_warmstart_run_1: `franka_multi_rgb_mainf1_warmstart_validate_a120_c80_l160_z075_env64_h16_mb512_20260614T063954Z`
- rgb_warmstart_result_1: stalled before completed env setup/project metrics on `batch-block5-01074`; cancelled without useful rollout metrics.
- rgb_warmstart_job_2: `29057741`
- rgb_warmstart_run_2: `franka_multi_rgb_mainf1_warmstart_validate_a120_c80_l160_z075_env64_h16_mb512_retry_20260614T064440Z`
- rgb_warmstart_result_2: relaunched excluding the first node, but again stalled before useful metrics; cancelled.
- state_warmstart_bad_job: `29057875`
- state_warmstart_bad_result: failed config validation because `NUM_ENVS=64`, `HORIZON_LENGTH=16`, and multi-GPU `MINIBATCH_SIZE=512` were not divisible per runner expectations.
- state_warmstart_job: `29057942`
- state_warmstart_run: `franka_multi_state_mainf1_warmstart_validate_a120_c80_l160_z075_env256_h16_mb512_20260614T065007Z`
- state_warmstart_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_mainf1_warmstart_validate_a120_c80_l160_z075_env256_h16_mb512_20260614T065007Z/metrics/direct_info_rank_0.jsonl`

Result:
- status: failed diagnostic; the reference sequence itself did not produce reliable lifting.
- max_success_rate: `0.0078125`
- final_success_rate: `0.0`
- max_has_lifted_rate: `0.01171875`
- final_has_lifted_rate: `0.01171875`
- max_mean_lift_height_m: `0.003288`
- final_mean_lift_height_m: `0.000616`
- final_reset_success_rate: `0.65234375`
- final_quality_success_rate: `0.60546875`
- final_exact_ee_dist_m: `0.00219`
- final_exact_tool_dist_m: `0.14677`
- final_finger_center_dist_m: `0.17798`
- final_projected_exact_tip_center_dist_m: `0.00219`

Analysis:
- Reset quality and candidate availability are healthy enough for RL, but the direct controller does not actually grasp and lift most objects. The large gap between exact EE/tip metrics and finger/tool/object-center distances indicates the candidate selection and warm-start phase logic are accepting poses that are not reliable physical grasps after closing.
- This is a blocker for meaningful policy training. The next change needs to improve grasp candidate selection and the close/lift transition before another no-override policy run.

Next:
- Inspect the lift-latch/quality-selector snapshot, validate whether it fixes direct warm-start lifting, then port the targeted fix back to `main` before launching real RGB policy training.

## 2026-06-14T07:08:28Z - Main latch patch and state validation launch

Goal:
- Fix the direct reference-sequence failure before spending another RGB RL allocation.

Version Control:
- agent_id: `integrate-multiobject-main-20260613`
- local_worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- pushed_commits:
  - `6c8a2f341acf1af6e67e3613fc73061c5725e936` - `Gate Franka grasp prior warmstart lift`
  - `9c7e0f14d61b41d8a9636f8d16784dee03bad93d` - `Expose Franka grasp prior pregrasp offset`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `9c7e0f14d61b41d8a9636f8d16784dee03bad93d`

Snapshot Check:
- snapshot_job: `29058004`
- snapshot_commit: `c4a6381c3503653ad91e711c48a49a28e2e0866a`
- snapshot_run: `franka_multi_rgb_liftlatch_orient_qfinger120_a160_c80_finger140_z075_g16_env64_h16_mb512_train_20260614T0655Z`
- snapshot_result: cancelled externally at epoch `16/200` before checkpointing.
- snapshot_signal: at first lift-phase epochs, `cube_action_warmstart_lift_rate=0.015625`, `cube_action_warmstart_lift_lift_height≈0.0001`, `cube_action_warmstart_lift_has_lifted_rate=0.0`, so the snapshot did not demonstrate physical lift.

Patch:
- Kept `main`'s newer contact-location-aware candidate sampler.
- Added stateful warm-start close/lift latches.
- Added optional gates for close exact-EE error, lift exact-EE error, lift finger-center distance, and lift closed-gripper width.
- Added close-width target computation with optional grasp-prior width margin and a Slurm override for `GRASP_PRIOR_PREGRASP_OFFSET`.
- Added direct metrics for latch rates, active-only lift/width/finger-distance, and lift-phase lift/width/finger-distance.

Validation Job:
- job_id: `29058337`
- run: `franka_multi_state_main9c_latch_preg01_gate_env256_h16_mb512_validate_20260614T070758Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29058337.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_main9c_latch_preg01_gate_env256_h16_mb512_validate_20260614T070758Z/metrics/direct_info_rank_0.jsonl`
- command: state task, `NUM_ENVS=256`, `MAX_ITERATIONS=40`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, random object assignment, stable-pose cache, `GRASP_PRIOR_PREGRASP_OFFSET=0.01`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=512`, `GRASP_PRIOR_RESET_ATTEMPTS=16`, `GRASP_PRIOR_ACTION_WARMSTART_ENABLED=True`, `approach=160`, `close=80`, `lift=160`, `lift_z=0.75`, `gain=16`, `close_max_ee_error=0.11`, `lift_max_ee_error=0.08`, `lift_max_finger_center_dist=0.20`, `lift_closed_width_margin=0.006`.

Next:
- Monitor job `29058337` through lift phase. If the direct controller lifts reliably, launch real RGB policy training with action-prior reward rather than action override. If it still fails, use the new latch metrics to decide whether the blocker is candidate quality, close width, approach tracking, or object/reference-frame geometry.

## 2026-06-14T07:13:02Z - State latch validation failed

Goal:
- Decide whether the patched latch/gate warm-start sequence can physically lift the objects.

Command / Job:
- job_id: `29058337`
- run: `franka_multi_state_main9c_latch_preg01_gate_env256_h16_mb512_validate_20260614T070758Z`
- status: completed
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_main9c_latch_preg01_gate_env256_h16_mb512_validate_20260614T070758Z/metrics/direct_info_rank_0.jsonl`
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_main9c_latch_preg01_gate_env256_h16_mb512_validate_20260614T070758Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew__793.4423_.pth`

Result:
- max_success_rate: `0.00390625`
- max_has_lifted_rate: `0.00390625`
- max_mean_lift_height_m: `0.000729`
- max_lift_phase_has_lifted_rate: `0.0`
- final_success_rate: `0.0`
- final_reset_success_rate: `0.609375`
- final_quality_success_rate: `0.45703125`
- final_candidate_valid_count_mean: `64.46484375`
- final_lift_phase_finger_center_dist_m: `0.21645`
- final_lift_phase_gripper_width_m: `0.03151`
- final_lift_phase_exact_ee_error_m: `0.09185`

Analysis:
- The latch/gate patch works mechanically: warm-start enters close/lift and logs the expected latch metrics.
- It still does not physically grasp. The gripper closes and lift action executes, but object lift remains below 1 mm and lift-phase lifted rate is zero.
- Launching RGB RL now would train against a known-bad reference controller. The next step is rendered contact debugging using the same pregrasp/gate settings to inspect actual finger/object geometry.

Next:
- Patch the video validator to reproduce the exact gated warm-start settings, render a small grasp-contact rollout, inspect the video/JSON, and then fix candidate/transform geometry before training.

## 2026-06-14T07:16:36Z - Gated grasp-contact render launch

Goal:
- Render the same failing gated warm-start sequence to inspect finger/object contact geometry.

Version Control:
- implementation_commit: `23db977c00ec4b151e136864bb99e3f6a5706cdf`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`

Command / Job:
- first_submit_result: failed immediately because the video script default partition `batch` is invalid on this cluster.
- job_id: `29058558`
- run: `franka_multi_video_main23_gated_contact_20260614T071636Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29058558.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main23_gated_contact_20260614T071636Z`
- command: `sbatch --partition=polar3 cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` with `NUM_ENVS=4`, `GRASP_STEPS=400`, `GRASP_CONTACT_SCORE_STEPS=400`, stable poses, full yaw, `GRASP_PREGRASP_OFFSET=0.01`, `GRASP_RESET_CANDIDATE_COUNT=512`, and the same close/lift gate settings as job `29058337`.

Next:
- Monitor job `29058558`, inspect `video_metrics.json` and the generated `grasp_contact` frames/video, then patch grasp/contact geometry.

## 2026-06-14T07:24:46Z - Gated grasp-contact render failed; contact-reference lift gate patch

Goal:
- Inspect rendered/metric evidence from the gated direct grasp-contact validation and patch the first concrete blocker before launching RL.

Result:
- job_id: `29058558`
- status: failed by validation criteria after writing artifacts
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main23_gated_contact_20260614T071636Z/video_metrics.json`
- reset_settle: passed
- perturbation: passed
- grasp_contact: failed
- selected_asset_uuid: `96ae0ff853734df0b10a827307949c87`
- selected_lift_height_max_m: `0.0027228`
- selected_lift_height_threshold_m: `0.12`
- selected_max_finger_dist_min_m: `0.12712`
- selected_object_size_m: `0.29604`
- selected_object_xy_delta_max_m: `0.01059`
- selected_done_count: `0`
- warmstart_phases: `[0, 1]`
- selected_reset_quality_success: `True`

Analysis:
- The environment reset and perturbation validations remain acceptable.
- The grasp-contact rollout did not lift and never entered phase `2`. The selected prior target is on a large asymmetric object; the old lift latch used `finger_center_to_cube_dist`, which measures distance to the object center. For large objects this can remain over 10 cm even when the gripper is near the intended contact/reference point, so the lift gate can reject otherwise plausible contact candidates.
- This explains why previous direct warm-start runs could close without lifting: the warm-start gate and diagnostics were tied to object center distance, while the reset candidate quality/reference was contact-location-aware.

Patch:
- Changed the grasp-prior lift readiness gate to compare the gripper finger center against `grasp_prior_reset_quality_reference_pos_w` in env coordinates, falling back to object center only when no reference exists.
- Added `grasp_prior_action_warmstart_reference_finger_center_dist` to env metrics and video validator snapshots.

Validation:
- local syntax: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`

Next:
- Commit/deploy the patch, rerun a bounded direct grasp-contact validation with the same settings, inspect whether phase `2` appears and whether lift occurs. Only then launch RL training.

## 2026-06-14T07:26:00Z - Patched contact-reference validation launch

Goal:
- Validate whether the contact-reference lift gate lets the direct GraspGen warm-start reach lift and physically raise the object.

Version Control:
- implementation_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- local_branch: `main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- deploy: Git bundle because cluster GitHub SSH auth failed.

Command / Job:
- job_id: `29058785`
- run: `franka_multi_video_maineb_refgate_contact_20260614T0726Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29058785.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_refgate_contact_20260614T0726Z`
- command: patched video validation with stable poses, full yaw, `NUM_ENVS=4`, `MAX_OBJECTS=4`, `GRASP_RESET_CANDIDATE_COUNT=512`, `GRASP_RESET_ATTEMPTS=8`, and the same approach/close/lift gate settings as job `29058558`.

Next:
- Monitor job `29058785`, parse `video_metrics.json`, inspect the grasp-contact video frames, then decide whether to launch direct state/RGB training or patch contact geometry again.

## 2026-06-14T07:35:12Z - Contact-reference validation still blocked by warmstart transition

Goal:
- Determine whether the contact-reference lift gate patch was enough to make the direct grasp warm-start lift objects before launching RL.

Result:
- job_id: `29058785`
- status: failed immediately because the wrapper defaulted `CODE_NFS` to the fixed checkout instead of the detached main worktree; no valid evidence for commit `eb87564`.
- job_id: `29058802`
- run: `franka_multi_video_maineb_refgate_contact2_20260614T0728Z`
- status: failed by validation criteria after writing artifacts
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_refgate_contact2_20260614T0728Z/video_metrics.json`
- selected_asset_uuid: `96ae0ff853734df0b10a827307949c87`
- selected_lift_height_max_m: `0.0027228`
- selected_reference_finger_center_dist_min_m: `0.05072`
- selected_max_finger_dist_min_m: `0.12712`
- selected_gripper_width_min_m: `0.01401`
- selected_projected_tip_max_dist_min_m: `0.04005`
- selected_object_size_m: `0.29604`
- warmstart_phases: `[0, 1]`
- reset_settle: passed
- perturbation: passed
- grasp_contact: failed

Analysis:
- The new reference-distance diagnostic confirms the contact-reference gate is no longer the blocker: the selected gripper/reference distance reaches about 5 cm, below the 20 cm lift threshold used for this validation.
- The warm-start still never enters phase `2`. Given the measured gripper width and the forced `GRASP_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=0.006`, the remaining likely blocker is the measured closed-width gate rather than object loading, object settling, or center-distance geometry.
- The rendered grasp-contact frames show a valid but difficult long-thin object. The fingers close near an end/contact patch; this is precisely the case where a measured-width gate tuned for cube-like objects is too brittle.

Next:
- Rerun the same main-branch video validation with `GRASP_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`. If phase `2` appears, patch the warm-start transition to use the reference/step latch instead of measured width for multi-object training. If it still does not appear, add per-gate diagnostics and inspect the exact EE/finger tracking path.

## 2026-06-14T07:39:00Z - No-width-gate grasp-contact render launch

Goal:
- Test whether the measured closed-width gate alone prevents the direct GraspGen warm-start from entering lift on the selected multi-object contact case.

Version Control:
- implementation_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- local_branch: `main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- deploy: existing Git bundle deployment; cluster GitHub SSH auth remains unavailable.

Command / Job:
- job_id: `29058987`
- run: `franka_multi_video_maineb_refgate_nowidth_20260614T0739Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29058987.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_refgate_nowidth_20260614T0739Z`
- command: same bounded video validation as job `29058802`, but with `GRASP_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`.

Next:
- Monitor job `29058987`, parse `video_metrics.json`, inspect grasp-contact frames/video, and patch or proceed based on whether lift phase and object lift occur.

## 2026-06-14T07:47:10Z - No-width gate render reached lift but failed physical grasp

Goal:
- Decide whether disabling the measured closed-width gate is enough to make the direct GraspGen warm-start physically lift the object.

Command / Job:
- job_id: `29058987`
- run: `franka_multi_video_maineb_refgate_nowidth_20260614T0739Z`
- status: failed by validation criteria after writing artifacts
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_refgate_nowidth_20260614T0739Z/video_metrics.json`

Result:
- reset_settle: passed
- perturbation: passed
- grasp_contact: failed
- selected_asset_uuid: `96ae0ff853734df0b10a827307949c87`
- selected_lift_height_max_m: `0.002376`
- selected_lift_height_threshold_m: `0.12`
- selected_reference_finger_center_dist_min_m: `0.05572`
- selected_gripper_width_min_m: `0.00319`
- selected_max_finger_dist_min_m: `0.09704`
- selected_object_xy_delta_max_m: `0.04494`
- selected_candidate_valid_count: `119`
- selected_center_gate_dist_m: `0.08242`
- selected_object_size_m: `0.29604`
- warmstart_phases: `[0, 1, 2]`

Analysis:
- Disabling the width gate fixes only the phase-transition issue. The direct controller reaches lift, but the object is not captured.
- Rendered frames show the chosen candidate contacts a long thin object near an end; the object slides/rotates instead of being enclosed. The first frame is also too close to exact contact because the validation forced `GRASP_PREGRASP_OFFSET=0.01` while the env default is `0.03`.
- The candidate center gate was too permissive for elongated objects: `0.08242 / 0.29604 = 0.278`, but the validation allowed `0.55`, so a poor end grasp passed.

Next:
- Rerun the same bounded render with `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`, `GRASP_PREGRASP_OFFSET=0.03`, and a larger candidate/attempt budget. Use the result to choose training launch settings or patch candidate scoring if central grasp selection is still poor.

## 2026-06-14T07:50:00Z - Stricter center/default pregrasp render launch

Goal:
- Test whether centralizing selected GraspGen candidates and using the default pregrasp offset produces clean no-penetration contact and actual object lift.

Version Control:
- implementation_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`

Command / Job:
- job_id: `29059034`
- run: `franka_multi_video_maineb_center025_pre03_20260614T0750Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059034.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_center025_pre03_20260614T0750Z`
- command: same main-branch video validation, but with `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`, `GRASP_PREGRASP_OFFSET=0.03`, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_RESET_ATTEMPTS=16`, and `GRASP_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`.

Next:
- Monitor job `29059034`; if it passes or visually shows a clean central lift, launch the first current-main state teacher run with the same reset settings. If it fails, patch candidate scoring/quality masks before launching RL.

## 2026-06-14T07:54:30Z - Stricter center/default pregrasp still blocked by lift EE gate

Goal:
- Test whether central candidate selection and the default pregrasp offset produce a clean direct lift.

Command / Job:
- job_id: `29059034`
- run: `franka_multi_video_maineb_center025_pre03_20260614T0750Z`
- status: failed by validation criteria after writing artifacts
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_center025_pre03_20260614T0750Z/video_metrics.json`

Result:
- reset_settle: passed
- perturbation: passed
- grasp_contact: failed
- selected_asset_uuid: `96ae0ff853734df0b10a827307949c87`
- selected_lift_height_max_m: `0.03036`
- selected_lift_height_threshold_m: `0.12`
- selected_center_gate_dist_m: `0.07187`
- selected_candidate_valid_count: `3`
- selected_reference_finger_center_dist_min_m: `0.05644`
- selected_max_finger_dist_min_m: `0.06138`
- selected_gripper_width_min_m: `0.00273`
- selected_object_xy_delta_max_m: `0.03520`
- warmstart_phases: `[0, 1]`

Analysis:
- Tightening the center gate and using the default pregrasp offset improved the grasp: the fingers get closer to the object, object z reaches about 3 cm above its start, and table penetration is much smaller than the end-grasp run.
- The warm-start still never enters phase `2`. With the width gate disabled and reference distance below threshold, the remaining blocker is likely `GRASP_WARMSTART_LIFT_MAX_EE_ERROR=0.08`, because contact motion changes the exact EE/reference tracking during close.

Next:
- Rerun the same central/pregrasp validation with `GRASP_WARMSTART_LIFT_MAX_EE_ERROR=0.0` to disable the lift EE-error gate. If it reaches phase `2` but still slips, patch multi-object USD spawn contact material/friction to match the cube baseline.

## 2026-06-14T07:56:00Z - No lift-EE-gate central render launch

Goal:
- Decide whether the lift EE-error gate is the remaining reason the central/default-pregrasp direct controller does not command lift.

Version Control:
- implementation_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`

Command / Job:
- job_id: `29059083`
- run: `franka_multi_video_maineb_center025_pre03_noeegate_20260614T0756Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059083.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maineb_center025_pre03_noeegate_20260614T0756Z`
- command: same as job `29059034`, but with `GRASP_WARMSTART_LIFT_MAX_EE_ERROR=0.0`.

Next:
- Monitor job `29059083`, inspect phases/lift/video. If lift phase appears but object slips, patch object USD contact material and rerun. If it lifts cleanly, launch state teacher RL with these reset/guidance settings.

## 2026-06-14T07:50:12Z - Patch multi-object contact and top-down prior filtering

Goal:
- Fix the remaining `grasp_contact` validation failure before launching RL.

Result:
- job_id: `29059083`
- run: `franka_multi_video_maineb_center025_pre03_noeegate_20260614T0756Z`
- status: failed by validation criteria after writing metrics and frames.
- reset_settle: passed.
- perturbation: passed.
- grasp_contact: failed.
- selected_asset_uuid: `96ae0ff853734df0b10a827307949c87`
- selected_lift_height_max_m: `0.02316`
- selected_lift_height_threshold_m: `0.12`
- selected_object_xy_delta_max_m: `0.10869`
- selected_reference_finger_center_dist_min_m: `0.05430`
- selected_candidate_valid_count: `2`
- selected_pregrasp_offset_dir_z: `0.22564`
- warmstart_phases: `[0, 1, 2]`

Analysis:
- Disabling the lift EE gate let the scripted diagnostic reach lift phase, but the object was pushed/slid instead of captured.
- Pulled frames show the chosen GraspGen prior approaches mostly sideways (`pregrasp_offset_dir_z=0.22564`) and sweeps the rod across the table before lifting empty. This is a reset-prior selection issue, not a reset-settle issue.
- The multi-object USD spawn was also missing the explicit collision/contact material used by the cube task, so successful grasps would be more likely to slip than the original cube baseline.

Change:
- Added explicit USD object collision properties and high-friction/zero-restitution material to match the cube task's physical setup.
- Raised the multi-object default/top-level launcher top-down prior threshold from low side-approach values to `0.45`.
- Tightened the wrapper default center-distance fraction from `0.55` to `0.30`.
- Kept `require_topdown` active in the fallback scorer so failed strict masks do not silently choose side grasps.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `eb8756425d836aed3d1e4479e6ab61819c12de81`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`: passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed.
- `git diff --check`: passed.

Next:
- Commit and deploy this patch to the A100 worktree, then rerun the same video validation with a stricter `GRASP_RESET_MIN_PREGRASP_Z=0.55`, central candidate filtering, and the patched friction/contact settings.

## 2026-06-14T07:52:00Z - Patched top-down/contact validation launch

Goal:
- Verify the patched multi-object environment produces clean grasp-contact video evidence before launching RL.

Version Control:
- implementation_commit: `08fcc52361d2d9403441eac6de846cb1368047f1`
- push: local `origin/main` updated from `eb87564` to `08fcc52`.
- deploy: incremental Git bundle copied to A1002 and fetched into the detached remote worktree.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `08fcc52361d2d9403441eac6de846cb1368047f1`

Command / Job:
- job_id: `29059176`
- run: `franka_multi_video_main08f_topdown55_contact_20260614T0752Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059176.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main08f_topdown55_contact_20260614T0752Z`
- command: `sbatch --partition=batch_singlenode,interactive_singlenode,polar,polar3,polar4,grizzly --export=ALL,CODE_NFS=<remote_worktree>,CODE_COMMIT=08fcc52361d2d9403441eac6de846cb1368047f1,RUN_NAME=franka_multi_video_main08f_topdown55_contact_20260614T0752Z,TASK=Dextrah-Franka-Multi-Object-Grasp,NUM_ENVS=4,MAX_OBJECTS=4,OBJECT_ASSET_ASSIGNMENT=random,OBJECT_SPAWN_CENTER_OFFSET_X=0.05,OBJECT_SPAWN_XY_RANDOMIZATION=0.10,OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0,OBJECT_STABLE_POSE_ENABLED=True,OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache,GRASP_RESET_ATTEMPTS=24,GRASP_RESET_MIN_PREGRASP_Z=0.55,GRASP_RESET_CANDIDATE_COUNT=4096,GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25,GRASP_PREGRASP_OFFSET=0.03,GRASP_WARMSTART_TRACK_ORIENTATION=True,... cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`

Next:
- Monitor job `29059176`, inspect `video_metrics.json`, and pull frames/video if the metrics pass or fail in a way that needs visual diagnosis.

## 2026-06-14T07:54:00Z - Fix USD material binding API mismatch

Goal:
- Recover from the patched validation construction failure and keep explicit object contact material support.

Command / Job:
- job_id: `29059176`
- run: `franka_multi_video_main08f_topdown55_contact_20260614T0752Z`
- status: failed before metrics.

Result:
- Error: `TypeError: UsdFileCfg.__init__() got an unexpected keyword argument 'physics_material'`.
- Evidence: wrapper log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059176.out`.

Analysis:
- Isaac Lab 2.2's `UsdFileCfg` supports nested `collision_props`, `rigid_props`, and `mass_props`, but not `physics_material`.
- The correct API for USD assets is to spawn a `RigidBodyMaterialCfg` prim and bind it to collider descendants with `bind_physics_material`.

Change:
- Removed the unsupported `physics_material` field from `UsdFileCfg`.
- Create `<object_prim>/physicsMaterial` per object and bind it recursively after `RigidObject` construction.
- Aligned `validate_franka_multi_object_grasp_videos.py` argparse defaults with the stricter top-down/center wrapper defaults.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`: passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed.
- `git diff --check`: passed.

Next:
- Commit, push, redeploy by Git bundle, and relaunch the patched video validation.

## 2026-06-14T07:56:00Z - Corrected material-binding validation launch

Goal:
- Re-run the top-down/contact video validation after fixing the Isaac Lab USD material-binding API use.

Version Control:
- implementation_commit: `916ba6254ab537b2ba7651d1515fad8a9e1665e6`
- push: local `origin/main` updated from `08fcc52` to `916ba62`.
- deploy: incremental Git bundle copied to A1002 and fetched into the detached remote worktree.
- remote_commit: `916ba6254ab537b2ba7651d1515fad8a9e1665e6`

Command / Job:
- job_id: `29059206`
- run: `franka_multi_video_main916_topdown55_contact_20260614T0756Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059206.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main916_topdown55_contact_20260614T0756Z`
- command: same as job `29059176`, but launched from commit `916ba6254ab537b2ba7651d1515fad8a9e1665e6`.

Next:
- Monitor job `29059206`, parse metrics, inspect video if the physical grasp still fails, and only launch RL once this environment validation is good enough.

## 2026-06-14T08:00:00Z - De-instance object colliders before applying material/contact

Goal:
- Fix remaining object material/contact override warnings and interpret the top-down validation result.

Command / Job:
- job_id: `29059206`
- run: `franka_multi_video_main916_topdown55_contact_20260614T0756Z`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main916_topdown55_contact_20260614T0756Z/video_metrics.json`

Result:
- reset_settle: passed.
- perturbation: passed.
- grasp_contact: failed.
- selected_candidate_valid_count: `0`
- selected_candidate_topdown_count: `910`
- selected_candidate_center_count: `725`
- selected_pregrasp_offset_dir_z: `0.86750`
- selected_reset_success: `false`
- warmstart_active_count: `0`
- selected_lift_height_max_m: `0.000001`

Analysis:
- The API fix allowed construction, but logs showed `modify_collision_properties` and `bind_physics_material` could not apply because the USD collision subtrees were instanceable.
- The stricter `GRASP_RESET_MIN_PREGRASP_Z=0.55` was too brittle with `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`: no candidate passed the quality mask, so no grasp-contact diagnostic ran.

Change:
- Added `make_uninstanceable(prim_path)` after spawning each USD object.
- Removed collision overrides from `UsdFileCfg`; instead, apply `modify_collision_properties` after de-instancing and then bind the physics material.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`: passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed.
- `git diff --check`: passed.

Next:
- Commit/deploy de-instancing and relaunch with a less brittle but still top-down reset filter: `GRASP_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`.

## 2026-06-14T08:01:00Z - De-instanced top-down 0.45 validation launch

Goal:
- Verify that de-instancing allows contact/material overrides and that a less brittle top-down prior mask produces a physical grasp-contact rollout.

Version Control:
- implementation_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`
- push: local `origin/main` updated from `916ba62` to `0ef680d`.
- deploy: incremental Git bundle copied to A1002 and fetched into the detached remote worktree.
- remote_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`

Command / Job:
- job_id: `29059265`
- run: `franka_multi_video_main0ef_topdown45_contact_20260614T0801Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059265.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_topdown45_contact_20260614T0801Z`
- key settings: `GRASP_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`, `GRASP_RESET_CANDIDATE_COUNT=4096`, `GRASP_RESET_ATTEMPTS=24`, material/contact patch active.

Next:
- Monitor job `29059265`; if metrics pass or fail physically, inspect the log for material-binding warnings and pull representative frames.

## 2026-06-14T08:12:00Z - Top-down 0.45 / center 0.30 validation result

Goal:
- Decide whether the merged multi-object environment is clean enough to launch PPO.

Command / Job:
- job_id: `29059265`
- run: `franka_multi_video_main0ef_topdown45_contact_20260614T0801Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059265.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_topdown45_contact_20260614T0801Z`

Result:
- status: failed metrics because `grasp_contact` failed; reset_settle and perturbation passed.
- material/contact warnings from instanceable USD prims were gone after de-instancing.
- reset_settle: `object_xy_delta_max=0.0000055`, `bottom_clearance_min=-0.0040`, no dones.
- perturbation: object moved normally, `object_xy_delta_max=0.0509`, no dones.
- grasp_contact: `selected_lift_height_max=0.00199`, `selected_object_xy_delta_max=0.0119`, no dones.
- selected prior geometry was accurate (`selected_reset_pos_error=2.1e-7`, `selected_reset_rot_error=5.9e-7`) but peripheral (`selected_contact_center_dist=0.0824 m`, `object_size=0.2960 m`, `selected_candidate_valid_count=10`).

Analysis:
- The previous reset-jump/moved-object issue is fixed: the grasp target is computed from the settled object pose and the arm reset reaches the requested pregrasp pose.
- The remaining failure is candidate quality for a long object. The chosen GraspGen contact is near an end/side feature, so the gripper closes without enclosing the object and lifts away.

Next:
- Relaunch without code changes using a stricter center gate (`GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`) and more candidates (`GRASP_RESET_CANDIDATE_COUNT=8192`) to see if parameter selection is sufficient before patching source.

## 2026-06-14T08:15:00Z - Center 0.25 / 8192-candidate validation launch

Goal:
- Test whether stricter center gating fixes the long-object grasp-contact failure without additional source changes.

Version Control:
- implementation_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`
- remote_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`

Command / Job:
- job_id: `29059438`
- run: `franka_multi_video_main0ef_topdown45_center25_8192_20260614T0815Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059438.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_topdown45_center25_8192_20260614T0815Z`
- key settings: `GRASP_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`, `GRASP_RESET_CANDIDATE_COUNT=8192`, `GRASP_RESET_ATTEMPTS=24`.

Next:
- Monitor job `29059438`, inspect metrics and frames, then either use the stricter reset for PPO or patch the source selector.

## 2026-06-14T08:18:00Z - Center 0.25 validation result

Goal:
- Check whether a stricter center gate can avoid the peripheral long-object grasp.

Command / Job:
- job_id: `29059438`
- run: `franka_multi_video_main0ef_topdown45_center25_8192_20260614T0815Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059438.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_topdown45_center25_8192_20260614T0815Z`

Result:
- status: failed metrics because `grasp_contact` had no quality candidate.
- reset_settle and perturbation passed.
- asset 2 (`96ae0ff853734df0b10a827307949c87`) had `selected_candidate_valid_count=0` under `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.25`, even with `8192` sampled candidates.
- The same asset has `grasp_size=0.296 m` and scaled half-extents roughly `(0.015, 0.148, 0.018)`, so the available top-down priors are effectively end/peripheral contacts for a long object.

Analysis:
- Tightening the center gate proves the prior/object combination, not settled-pose reset, is the current bottleneck.
- For the first PPO run, using this asset would add reset-quality failures or peripheral resets before the policy can learn. I will first validate/train a smaller multi-object subset and keep the full-set/long-object handling as the next scaling issue.

Next:
- Launch a two-object validation (`MAX_OBJECTS=2`) using the same stable-pose/yaw/random-assignment path. If it passes, use that subset for the initial state-teacher PPO launch.

## 2026-06-14T08:21:00Z - Two-object validation launch

Goal:
- Validate a smaller multi-object subset for the first PPO run while preserving random object assignment, per-reset XY/yaw randomization, stable-pose resets, and grasp-prior reset.

Version Control:
- implementation_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`
- remote_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`

Command / Job:
- job_id: `29059497`
- run: `franka_multi_video_main0ef_twoobj_topdown45_center30_20260614T0821Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059497.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_twoobj_topdown45_center30_20260614T0821Z`
- key settings: `MAX_OBJECTS=2`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`, `GRASP_RESET_CANDIDATE_COUNT=4096`.

Next:
- Monitor job `29059497`; if the videos/metrics pass, launch bounded multi-object state-teacher PPO on this subset.

## 2026-06-14T08:22:37Z - Two-object validation result

Goal:
- Decide whether the first two smoke-manifest assets are suitable for initial PPO.

Command / Job:
- job_id: `29059497`
- run: `franka_multi_video_main0ef_twoobj_topdown45_center30_20260614T0821Z`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_twoobj_topdown45_center30_20260614T0821Z/video_metrics.json`

Result:
- status: failed metrics because `grasp_contact` had no quality candidate.
- reset_settle passed: `object_xy_delta_max=0.0000007`, `bottom_clearance_min=-0.0024`, `done_count=0`.
- perturbation passed: `object_xy_delta_max=0.0509`, `object_speed_max=0.4388`, `done_count=0`.
- grasp_contact selected asset 0 (`7195ed3346a445448308febe833c180a`) and found `selected_candidate_valid_count=0`, so warmstart/contact was inactive.

Analysis:
- The environment reset and perturbation behavior remain correct. The failure is again the GraspGen prior candidate distribution for a long/thin object, not object settling or pose recomputation.
- The first smoke-manifest pair still includes a long/thin object, so it is not a good initial PPO subset.

Next:
- Validate the filtered two-object manifest containing non-slender assets 1 and 3, then use that subset for the first bounded PPO run if videos and metrics pass.

## 2026-06-14T08:23:00Z - Filtered two-object validation launch

Goal:
- Validate the initial trainable multi-object subset with two non-slender GraspGen assets before launching PPO.

Version Control:
- implementation_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`

Command / Job:
- job_id: `29059554`
- run: `franka_multi_video_main0ef_filtered2_topdown45_center30_20260614T0823Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059554.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_filtered2_topdown45_center30_20260614T0823Z`
- command: `OBJECT_ASSET_MANIFEST_PATH=/results/assets/filtered_manifests/two_non_slender_1_3_20260614T0824Z/manifest.json MAX_OBJECTS=2 OBJECT_ASSET_ASSIGNMENT=random OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0 OBJECT_STABLE_POSE_ENABLED=True GRASP_RESET_MIN_PREGRASP_Z=0.45 GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30 GRASP_RESET_CANDIDATE_COUNT=4096 sbatch --partition=polar ... cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`

Next:
- Monitor job `29059554`, inspect `video_metrics.json` and the grasp-contact video, then launch bounded PPO if the filtered subset passes.

## 2026-06-14T08:26:00Z - Filtered manifest asset-root fix

Goal:
- Recover the filtered two-object validation from a manifest path error.

Command / Job:
- failed_job_id: `29059554`
- failed_run: `franka_multi_video_main0ef_filtered2_topdown45_center30_20260614T0823Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059554.out`

Result:
- status: failed before environment construction.
- error: `FileNotFoundError: Missing USD asset ... /code/USD/1d489db9cdc24161a7537926a20bb17b/...usd`.

Analysis:
- The filtered manifest was stored outside the original asset directory but kept `asset_root: "."`, so relative `USD/...` paths resolved under `/code` inside the container.
- Source code is correct: manifest-relative `asset_root` is how the original staged manifest works.

Change:
- Created corrected manifest on `/lustre`: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/two_non_slender_1_3_assetroot_20260614T0826Z/manifest.json`.
- The corrected manifest points `asset_root` to `/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029` and resolves both filtered USD/prior files.

Next:
- Relaunch filtered two-object validation with the corrected manifest.

## 2026-06-14T08:27:00Z - Corrected filtered validation relaunch

Goal:
- Validate the non-slender two-object subset after fixing manifest asset resolution.

Version Control:
- implementation_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`
- remote_commit: `0ef680d7fdd0cabf19e4138952a414b3ebbdf3b1`

Command / Job:
- job_id: `29059587`
- run: `franka_multi_video_main0ef_filtered2fix_topdown45_center30_20260614T0827Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059587.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_filtered2fix_topdown45_center30_20260614T0827Z`
- manifest: `/results/assets/filtered_manifests/two_non_slender_1_3_assetroot_20260614T0826Z/manifest.json`

Next:
- Monitor job `29059587`; if metrics and video pass, launch bounded PPO with this corrected filtered manifest.

## 2026-06-14T08:29:00Z - Corrected filtered validation result and validator retry patch

Goal:
- Determine whether the corrected filtered subset is ready for PPO and fix validation behavior if it diverges from the actual RL reset path.

Command / Job:
- job_id: `29059587`
- run: `franka_multi_video_main0ef_filtered2fix_topdown45_center30_20260614T0827Z`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_main0ef_filtered2fix_topdown45_center30_20260614T0827Z/video_metrics.json`
- local_video: `/home/lzha/code/artifacts/dextrah/franka_multi_video_main0ef_filtered2fix_topdown45_center30_20260614T0827Z/grasp_contact.mp4`

Result:
- status: failed metrics because `grasp_contact` had no quality top-down candidate.
- reset_settle passed: `object_xy_delta_max=0.0000003`, `bottom_clearance_min=-0.0040`.
- perturbation passed: `object_xy_delta_max=0.0499`, `bottom_clearance_min=-0.0063`.
- grasp_contact selected asset `1d489db9cdc24161a7537926a20bb17b`; `selected_candidate_topdown_count=0`, `selected_candidate_valid_count=0`, `selected_pregrasp_offset_dir_z=-0.3198`, `warmstart_active_count=0`, `selected_lift_height_max=0.0`.
- Visual inspection showed the robot stayed in the default pose, with no object bounce, table penetration, or grasp contact.

Analysis:
- This result is a reset-candidate filter issue, not an object stability or penetration issue.
- The actual multi-object RL reset path retries failed prior samples up to `grasp_prior_reset_attempts`, but the video validator applied one settled-object prior sample only. This made validation pessimistic and inconsistent with training.
- The filtered objects' Franka priors may not contain top-down candidates in the chosen stable pose/yaw, so the next validation should exercise the same top-down setting intended for PPO.

Change:
- Patched `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` so settled-object grasp-contact validation retries failed prior samples like `DextrahFrankaMultiObjectGraspEnv._reset_idx`.
- Added `--grasp_reset_require_topdown/--no-grasp_reset_require_topdown` to the video validator and `GRASP_RESET_REQUIRE_TOPDOWN` to `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`: passed.
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`: passed.

Next:
- Commit/deploy the validation patch, then rerun the filtered video diagnostic with `GRASP_RESET_REQUIRE_TOPDOWN=False` to match a feasible PPO reset distribution for these objects.

## 2026-06-14T08:34:00Z - Retry-aware no-topdown filtered validation launch

Goal:
- Validate the feasible reset distribution intended for the first PPO run: stable-pose object resets, random assignment/yaw, grasp-prior reset retries, no top-down-only gate, and a broader center gate.

Version Control:
- implementation_commit: `cf6a52d1d725ce11bda000fe1ba2c6165e8b9c23`
- push: `origin/main` updated from `0ef680d` to `cf6a52d`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `cf6a52d1d725ce11bda000fe1ba2c6165e8b9c23`

Command / Job:
- job_id: `29059710`
- run: `franka_multi_video_maincf6_filtered2_retry_notop_center50_20260614T0834Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059710.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_maincf6_filtered2_retry_notop_center50_20260614T0834Z`
- key settings: `GRASP_RESET_REQUIRE_TOPDOWN=False`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, `GRASP_RESET_ATTEMPTS=24`, `GRASP_RESET_CANDIDATE_COUNT=4096`.

Next:
- Monitor job `29059710`, inspect metrics and the grasp-contact video, then launch bounded PPO if the reset/contact evidence is physically acceptable.

Result:
- status: canceled
- evidence: job reached `Recording grasp_contact with settled-object grasp-prior reset` but produced zero grasp-contact frames after ~4.5 minutes; compute process was active, so this was expensive reset search rather than a dead process.

Analysis:
- The grasp-contact selector used `env.reset()` inside an outer loop of `grasp_reset_attempts`, while the environment reset itself also used `env.grasp_prior_reset_attempts`. With `GRASP_RESET_ATTEMPTS=24`, the diagnostic could require hundreds of settled reset attempts before emitting frames, which is not representative of the intended PPO reset budget.

Next:
- Patch the validator so grasp-contact selection calls the settled-object grasp-prior reset helper directly, then relaunch with PPO-matched reset budget.

## 2026-06-14T08:38:20Z - Grasp-contact validation retry fix

Goal:
- Make validation exercise the same settled-object grasp-prior reset semantics intended for training without multiplying retry loops.

Change:
- Updated `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` so `_select_scored_grasp_contact_state` calls `_reset_settled_object_then_apply_grasp_prior` directly instead of `env.reset()` for selection attempts and fallback state.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `cf6a52d1d725ce11bda000fe1ba2c6165e8b9c23`
- implementation_commit: pending
- changed_files: `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- `git diff --check`

Next:
- Commit, push, update the A100 worktree, and rerun the filtered validation with a PPO-matched retry/candidate budget before launching teacher PPO.

## 2026-06-14T08:41:00Z - PPO-matched filtered validation launch

Goal:
- Validate the multi-object environment reset/contact behavior using the reset budget intended for the first PPO teacher run.

Version Control:
- implementation_commit: `bacdcde785919359e609e62fb9dfa05caf52f483`
- push: `origin/main` updated from `cf6a52d` to `bacdcde`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `bacdcde785919359e609e62fb9dfa05caf52f483`
- deploy: Git bundle copied to A100 and fetched into the remote worktree because the remote host cannot fetch GitHub by SSH.

Command / Job:
- first_submit: failed before job creation because the validation wrapper defaults to `#SBATCH --partition=batch`, which is invalid on A100.
- job_id: `29059849`
- run: `franka_multi_video_mainbac_filtered2_retry8_notop_center50_20260614T0841Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059849.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_mainbac_filtered2_retry8_notop_center50_20260614T0841Z`
- key settings: `GRASP_RESET_REQUIRE_TOPDOWN=False`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, `GRASP_RESET_ATTEMPTS=8`, `GRASP_RESET_CANDIDATE_COUNT=1024`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `OBJECT_ASSET_ASSIGNMENT=random`.

Next:
- Monitor job `29059849`; inspect metrics and grasp-contact video before launching PPO.

Result:
- status: canceled
- metrics/artifacts: reset-settle wrote 2 frames and perturbation wrote 2 frames; grasp-contact wrote 0 frames after ~2.8 minutes.
- key evidence: log reached `Recording grasp_contact with settled-object grasp-prior reset`; compute-node Python process was active at ~137% CPU with Isaac GPU memory allocated.

Analysis:
- The retry nesting bug was fixed, but the validation selector still spent time on unrendered rollout scoring before the actual video. That scoring is useful for picking the nicest diagnostic candidate, but it is not needed to prove the environment reset/contact path before PPO and does not represent training.

Next:
- Add a no-scoring validation path so `GRASP_CONTACT_SCORE_STEPS=0` records the first quality settled-object grasp-prior reset directly.

## 2026-06-14T08:43:44Z - Grasp-contact no-scoring selector path

Goal:
- Produce the required grasp-contact video without spending cluster time on pre-video candidate scoring rollouts.

Change:
- Updated `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` so `--grasp_contact_score_steps 0` bypasses unrendered selection scoring and returns the first quality candidate from the settled-object grasp-prior reset.
- Positive `--grasp_contact_score_steps` keeps the previous scoring behavior.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `bacdcde785919359e609e62fb9dfa05caf52f483`
- implementation_commit: pending
- changed_files: `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- `git diff --check`

Next:
- Commit, push, deploy by bundle, and relaunch validation with `GRASP_CONTACT_SCORE_STEPS=0`.

## 2026-06-14T08:45:00Z - Fast grasp-contact validation launch

Goal:
- Record the final environment validation videos, especially grasp-contact, without the nonessential selection-scoring delay.

Version Control:
- implementation_commit: `fd4510c0831932ee93c370067c24f752a3731db7`
- push: `origin/main` updated from `bacdcde` to `fd4510c`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `fd4510c0831932ee93c370067c24f752a3731db7`
- deploy: Git bundle copied to A100 and fetched into the remote worktree.

Command / Job:
- job_id: `29059925`
- run: `franka_multi_video_mainfd4_filtered2_fastcontact_retry8_notop_center50_20260614T0845Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29059925.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_mainfd4_filtered2_fastcontact_retry8_notop_center50_20260614T0845Z`
- key settings: `GRASP_CONTACT_SCORE_STEPS=0`, `GRASP_RESET_REQUIRE_TOPDOWN=False`, `GRASP_RESET_ATTEMPTS=8`, `GRASP_RESET_CANDIDATE_COUNT=1024`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`.

Next:
- Monitor job `29059925`, inspect metrics/video locally, then launch PPO if physics/contact evidence is acceptable.

Result:
- status: completed with expected diagnostic failure
- scheduler: Slurm job `29059925` exited `FAILED 1:0` because the validation script marks any failed scenario as process failure.
- metrics/artifacts: reset-settle passed; perturbation passed; grasp-contact produced 106 frames and failed only because the scripted warmstart did not lift the object.
- local_artifacts: `/home/lzha/code/artifacts/dextrah/franka_multi_video_mainfd4_filtered2_fastcontact_retry8_notop_center50_20260614T0845Z/`
- viewer: `http://localhost:8765/view?path=artifacts/dextrah/franka_multi_video_mainfd4_filtered2_fastcontact_retry8_notop_center50_20260614T0845Z/grasp_contact.mp4`

Metrics:
- reset_settle: `passed=True`, `object_xy_delta_max=3.28e-7`, `bottom_clearance_min=-0.0040`, `finger_table_clearance_min=0.2503`.
- perturbation: `passed=True`, `object_xy_delta_max=0.0499`, `bottom_clearance_min=-0.0063`, `finger_table_clearance_min=0.2488`.
- grasp_contact: `passed=False`, `selected_done_count=0`, `selected_quality_success=True`, `selected_reset_success=True`, `selected_reset_pos_error=1.7e-7`, `selected_reset_rot_error=3.9e-7`, `selected_lift_height_max=0.00076`, `selected_candidate_valid_count=1024`, `selected_open_width_margin=0.0455`.

Visual Inspection:
- First/mid/final grasp-contact frames show the object stable on the table, no bounce-away, no object stuck through the table, and no obvious robot/object/table penetration.
- The scripted warmstart approached near the side/handle of the object and lifted empty; this validates that the scene/reset is RLable but does not prove the prior is sufficient for scripted pickup.

Analysis:
- This is an environment-correctness pass for launching PPO. The remaining failure is policy/control quality: the selected GraspGen prior places the gripper near the object but the scripted open-loop close/lift does not capture it.

Next:
- Launch bounded multi-object PPO teacher training from commit `fd4510c0831932ee93c370067c24f752a3731db7` with random object assignment, full yaw randomization, stable-pose cache, and grasp-prior reset enabled.

## 2026-06-14T08:50:00Z - Bounded PPO teacher launch

Goal:
- Start actual multi-object Franka grasp PPO training on the validated environment and monitor whether rewards/lift metrics indicate learning.

Version Control:
- implementation_commit: `cf34bce3e27a017891d7a23c866446e88f03aa79`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `cf34bce3e27a017891d7a23c866446e88f03aa79`

Command / Job:
- job_id: `29060007`
- run: `franka_multi_state_teacher_filtered2_graspprior_20260614T0850Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29060007.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_graspprior_20260614T0850Z/metrics/direct_info_rank_0.jsonl`
- key settings: `NUM_ENVS=2048`, `MAX_ITERATIONS=300`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `OBJECT_STABLE_POSE_ENABLED=True`, `GRASP_PRIOR_RESET_ENABLED=True`, `GRASP_PRIOR_RESET_ATTEMPTS=8`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=1024`, `GRASP_PRIOR_RESET_REQUIRE_TOPDOWN=False`, `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`.

Next:
- Monitor startup; inspect metrics, reward terms, and checkpoints. If rewards flatline or reset cost is too high, tune and relaunch rather than stopping at job state.

## 2026-06-14T09:04:19Z - PPO teacher early metrics

Goal:
- Decide whether the first launched multi-object PPO run is healthy enough to continue.

Result:
- status: running
- job_id: `29060007`
- scheduler: `RUNNING` on `batch-block7-03003`, partition `polar3`.
- metrics: rank-0 JSONL reached epoch 16; no NaNs or tracebacks seen.
- startup evidence: all 8 ranks created 2048-env scenes, simulation started, and direct-info metric writers came up.
- checkpoint evidence: no checkpoint yet; save frequency is 25 epochs.

Key Metrics:
- epoch 1: `cube_success_rate=0`, `cube_has_lifted_rate=0`, `cube_finger_center_to_cube_dist=0.265`, `cube_lift_height=1.16e-05`.
- epoch 15: `cube_success_rate=0`, `cube_has_lifted_rate=4.88e-04`, `cube_finger_center_to_cube_dist=0.161`, `cube_lift_height=4.38e-04`.
- grasp-prior reset quality is nonzero and stable enough for RL: reset success around `0.24`, valid candidates around `571/1024`.

Analysis:
- Training is progressing and object-conditioned observations are wired: inherited object pose/velocity/relative vectors plus multi-object scale/shape/id/prior features make the state vector 80-D.
- Early behavior improves approach/enclosure and starts producing rare tiny lifts, but success is still zero and the mean z action remains negative.
- Keep monitoring to at least the epoch-25 checkpoint before deciding whether to relaunch with stronger lift/close shaping.

Next:
- Continue monitoring job `29060007`.
- At or after epoch 25, inspect checkpoint presence and reward/lift trend; if success/lift remains flat, cancel and relaunch a tuned PPO run.

## 2026-06-14T09:11:57Z - PPO teacher epoch-25 gate

Goal:
- Decide whether to keep baseline PPO job `29060007` after the first checkpoint.

Result:
- status: kept running
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_graspprior_20260614T0850Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_862.03723.pth`
- metrics_file: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_graspprior_20260614T0850Z/metrics/direct_info_rank_0.jsonl`

Key Metrics:
- epoch 25: `cube_success_rate=0`, `cube_has_lifted_rate=4.88e-04`, `cube_lift_height=3.22e-04`, `cube_finger_center_to_cube_dist=0.122`, `cube_gripper_width=0.021`, `cube_action_z=-0.0566`.
- epoch 26: `cube_success_rate=0`, `cube_has_lifted_rate=9.77e-04`, `cube_lift_height=2.92e-04`, `cube_action_z=-0.0656`.

Analysis:
- The job is not successful yet, but it is not completely flat: approach/enclosure improved strongly and rare tiny lift events have started.
- The remaining problem is lift: z action is still negative on average and lift height is far below the success threshold.
- Keep the baseline run to epoch 50 for one more learning window. If success/lift remains essentially zero, stop it and relaunch a tuned run with stronger lift/close/action shaping.

Next:
- Monitor to epoch 50.

## 2026-06-14T09:30:46Z - Baseline PPO stopped after epoch 50

Goal:
- Stop the first baseline run if it converges to approach/close without lift.

Result:
- status: failed baseline; canceled after checkpoint
- job_id: `29060007`
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_graspprior_20260614T0850Z/nn/last_dextrah_franka_multi_object_grasp_ep_50_rew_1414.3331.pth`
- action: `scancel 29060007`

Key Metrics:
- epoch 50: `cube_success_rate=0`, `cube_has_lifted_rate=0.00195`, `cube_lift_height=1.69e-04`, `cube_finger_center_to_cube_dist=0.101`, `cube_gripper_width=0.00495`, `cube_action_z=-0.0157`.
- epoch 51 was written before cancellation completed and remained unsuccessful: `cube_success_rate=0`, `cube_lift_height=2.72e-05`.

Analysis:
- The baseline reward learned to approach and close the gripper but not to lift. The aggregate reward increased because approach/enclosure dominated while success stayed zero.
- The gripper collapsed to nearly closed widths, so the default open-gripper penalty is likely counterproductive for heterogeneous objects.

Next:
- Launch a tuned PPO run from the same commit and assets.
- Use stronger lift/height/success/action shaping, remove the open-gripper penalty, and enable grasp-prior action-prior reward without action warmstart override.

## 2026-06-14T09:32:00Z - Tuned PPO launch

Goal:
- Relaunch PPO with reward/action-prior shaping that directly targets the baseline failure mode: approach/close without lift.

Version Control:
- implementation_commit: `cf34bce3e27a017891d7a23c866446e88f03aa79`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-rgb-teacher-20260614-f1a34bc`
- remote_commit: `cf34bce3e27a017891d7a23c866446e88f03aa79`
- source_change: none; training config override only.

Command / Job:
- job_id: `29060849`
- run: `franka_multi_state_teacher_filtered2_liftshape_priorreward_20260614T0932Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29060849.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_liftshape_priorreward_20260614T0932Z/metrics/direct_info_rank_0.jsonl`
- scheduler: started on `batch-block7-02880`, partition `polar3`.

Key Overrides:
- same assets/reset as baseline: `MAX_OBJECTS=2`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, stable-pose cache enabled, grasp-prior reset enabled.
- reward/action tuning: `CUBE_LIFT_WEIGHT=40`, `CUBE_HEIGHT_TRACKING_WEIGHT=10`, `CUBE_SUCCESS_BONUS_WEIGHT=60`, `CUBE_CLOSE_ACTION_WEIGHT=0.6`, `CUBE_LIFT_ACTION_WEIGHT=6`, `CUBE_DESCEND_ACTION_PENALTY_WEIGHT=-6`, `CUBE_GRIPPER_CLOSE_REG_WEIGHT=0`, `CUBE_ACTION_PENALTY_WEIGHT=-0.0002`.
- prior guidance: `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=3`, action warmstart remains disabled.

Next:
- Monitor startup, metrics, and checkpoint curve. Success criterion for keeping this run past the first checkpoint is nonzero and increasing lift/success rather than only approach/enclosure growth.

## 2026-06-14T09:44:40Z - Multi-object eval wrapper reset parity fix

Goal:
- Make checkpoint evaluation use the same reset distribution as the training jobs before evaluating any PPO checkpoint.

Hypothesis:
- The existing multi-object eval wrapper would not faithfully validate the training environment because it did not pass through stable-pose cache settings or the relaxed grasp-prior reset candidate filters.

Change:
- Added pass-through and validation for `OBJECT_STABLE_POSE_*`, `GRASP_PRIOR_RESET_*`, and `GRASP_PRIOR_PREGRASP_OFFSET` in `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `cf34bce3e27a017891d7a23c866446e88f03aa79`
- implementation_commit: `ff4ec8cff8b0f806f707db3f808a343d9f2d0b80`
- changed_files: `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, this worklog.

Validation:
- `bash -n cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- `git diff --check -- cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`

Next:
- Evaluate the next useful checkpoint with stable poses and the same relaxed grasp-prior reset filters used by training.

## 2026-06-14T09:53:10Z - Tuned PPO stopped; exact-grasp reset validation launch

Goal:
- Stop the tuned PPO run once the metrics show the remaining failure is contact capture, then validate a reset distribution that places the gripper at the exact sampled grasp instead of 3 cm pregrasp.

Hypothesis:
- The tuned run learned to close and command upward motion, but the object did not lift because reset/contact capture was off: the current `grasp_prior_pregrasp_offset=0.03` starts the policy 3 cm away from the exact grasp. Exact-grasp reset with a close/lift warmstart should reveal whether the GraspGen pose can produce actual object motion without penetration.

Result:
- status: tuned run canceled after epoch 36
- job_id: `29060849`
- run: `franka_multi_state_teacher_filtered2_liftshape_priorreward_20260614T0932Z`
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_filtered2_liftshape_priorreward_20260614T0932Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_934.70703.pth`
- final observed metrics: epoch 36 had `cube_success_rate=0`, `cube_has_lifted_rate=0.00098`, `cube_lift_height=9.8e-05`, `cube_action_z=0.382`, `cube_gripper_width=0.010`.

Analysis:
- Continuing the same reward shaping is unlikely to solve the main issue: the policy is already producing strong upward actions, but the object is not captured.
- The next change should affect reset/contact geometry or provide a stronger prior curriculum, not just more lift reward.

Command / Job:
- job_id: `1029209`
- host: `l401`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `94d7274cfbf31dcdd0b2a518fafd5f0485e62a18`
- run: `franka_multi_video_exactgrasp_offset0_filtered2_20260614T0958Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029209.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_offset0_filtered2_20260614T0958Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.0`, `GRASP_WARMSTART_APPROACH_STEPS=0`, `GRASP_WARMSTART_CLOSE_STEPS=24`, `GRASP_WARMSTART_LIFT_STEPS=96`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`, `GRASP_WARMSTART_LIFT_ACTION_Z=0.30`.

Next:
- Monitor job `1029209`, inspect metrics and videos. If exact reset produces clean contact/lift, relaunch PPO with `GRASP_PRIOR_PREGRASP_OFFSET=0.0` and a warmstart/action-prior curriculum; otherwise diagnose the grasp prior/contact transform before more 8-GPU training.

## 2026-06-14T09:58:09Z - Exact-grasp zero-offset reset fix

Goal:
- Make `GRASP_PRIOR_PREGRASP_OFFSET=0.0` a valid exact-grasp reset mode for multi-object contact validation and the next PPO curriculum.

Hypothesis:
- The failed `franka_multi_video_exactgrasp_offset0_filtered2_20260614T0958Z` grasp-contact video was not a true exact-grasp test. With zero pregrasp offset, the previous candidate code required `pregrasp_tool_dist > exact_tool_dist`, which is false when exact and pregrasp are identical. All candidates were invalid and the validator fell back to env 0 without a successful grasp-prior reset.

Change:
- In cube and multi-object grasp-prior target composition, preserve the selected tool-axis approach direction even when pregrasp offset is zero.
- Treat zero-offset candidates as satisfying the "pregrasp farther" gate, so exact-grasp reset can be used intentionally.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `94d7274cfbf31dcdd0b2a518fafd5f0485e62a18`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
- `git diff --check -- dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`

Related running-job cleanup:
- Canceled stale A100 RGB job `29060848` (`franka_multi_rgb_rl_linear_rebalance_yaw360_20260614T0930Z`) because it was launched from older snapshot code and rank-0 metrics through epoch 44 still had `cube_success_rate=0`, near-zero lift, and gripper collapse without capture.

Next:
- Commit/push this fix, deploy the exact commit to the L40 remote worktree, rerun the exact-grasp video validation, and only relaunch A100 PPO after grasp-contact passes.

## 2026-06-14T10:00:00Z - Exact-grasp validation relaunch after zero-offset fix

Goal:
- Verify with rendering that exact grasp-prior reset can produce clean object contact and lift for the same two-object debug set before relaunching PPO.

Version Control:
- local_commit: `d2e5272369262f56f2c59efe52b65b8937876004`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `d2e5272369262f56f2c59efe52b65b8937876004`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-d2e5272.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029210`
- host: `l401`
- run: `franka_multi_video_exactgrasp_offset0_fix_d2e5272_20260614T1000Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029210.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_offset0_fix_d2e5272_20260614T1000Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.0`, `GRASP_RESET_REQUIRE_TOPDOWN=True`, `GRASP_RESET_MIN_PREGRASP_Z=0.25`, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_CONTACT_SCORE_STEPS=60`, `GRASP_WARMSTART_CLOSE_STEPS=24`, `GRASP_WARMSTART_LIFT_STEPS=126`, `GRASP_WARMSTART_LIFT_ACTION_Z=0.35`.

Next:
- Monitor job `1029210`; inspect `video_metrics.json` and rendered `grasp_contact` frames/videos. Relaunch PPO only if the grasp-contact scenario passes or if the remaining failure is diagnosed and fixed.

## 2026-06-14T10:10:21Z - Reset IK quality and wrapper parity patch

Goal:
- Fix the exact-grasp rendered validation before relaunching PPO, and make training/eval/validation wrappers expose the same reset IK controls.

Hypothesis:
- Job `1029210` failed because the top-down candidate filter rejected all candidates for one debug object.
- Job `1029211` with top-down disabled found candidates, but IK landed about 4 cm from the target with the old exact-reset tolerance, so the validator fell back to the default robot pose. The rendered grasp-contact frame confirmed this was not a real grasp reset.

Result:
- `1029210` status: failed. Evidence: `selected_candidate_topdown_count=0`, `selected_candidate_valid_count=0`, `selected_reset_success=False`, warmstart inactive.
- `1029211` status: failed. Evidence: `selected_candidate_valid_count=247`, but `selected_reset_pos_error=0.0406`, `selected_reset_rot_error=0.2447`, `selected_reset_success=False`, `selected_quality_success=False`, warmstart inactive, rendered frame showed the default hover pose.

Change:
- Multi-object reset defaults now allow a stronger IK solve (`64` iterations, lower damping, larger joint step, and looser exact-reset tolerances) for heterogeneous GraspGen objects.
- Grasp reset quality now gates on the actual post-IK finger-center distance so fallback/default robot poses cannot pass based only on projected target geometry.
- Added optional reset IK pass-through and logging to the rendered validation, checkpoint eval, and 8-GPU training wrappers.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `d2e5272369262f56f2c59efe52b65b8937876004`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh && bash -n cluster/sbatch_train_teacher_8gpu.sh && bash -n cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- `git diff --check -- dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`

Next:
- Commit/push, deploy the exact commit to the L40 remote worktree, relaunch exact-grasp rendered validation with top-down disabled and explicit IK overrides, inspect the video/metrics, then launch A100 PPO only after grasp-contact is clean.

## 2026-06-14T10:12:00Z - Rendered exact-grasp IK validation launch

Goal:
- Confirm the reset/IK fix with rendered grasp contact before launching another A100 PPO run.

Version Control:
- local_commit: `707733bce652c67b54d243aa4382c7a8e95fc2e7`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `707733bce652c67b54d243aa4382c7a8e95fc2e7`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-707733b.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029212`
- host: `l401`
- run: `franka_multi_video_exactgrasp_ik707733b_notop_20260614T1011Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029212.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_ik707733b_notop_20260614T1011Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.0`, `GRASP_RESET_REQUIRE_TOPDOWN=False`, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_RESET_IK_ITERATIONS=96`, `GRASP_RESET_IK_POS_TOLERANCE=0.055`, `GRASP_RESET_IK_ROT_TOLERANCE=0.55`, `GRASP_WARMSTART_CLOSE_STEPS=24`, `GRASP_WARMSTART_LIFT_STEPS=126`, `GRASP_WARMSTART_LIFT_ACTION_Z=0.35`.

Next:
- Monitor job `1029212`; inspect `video_metrics.json`, encode/open `grasp_contact` frames, and only proceed to A100 PPO if reset/contact/lift behavior is visually and metrically correct.

## 2026-06-14T10:16:00Z - Validator metrics scope fix

Goal:
- Preserve the `1029212` rendered evidence and fix the validator crash so the same scenario can produce metrics.

Result:
- job_id: `1029212`
- status: failed after rendering all `grasp_contact` frames.
- evidence: log traceback `NameError: name 'env_cfg' is not defined` while constructing `video_metrics.json`.
- artifact note: `reset_settle`, `perturbation`, and `grasp_contact` frame folders were created, but no metrics JSON was written, so this run is not a valid pass/fail result.

Analysis:
- This was introduced by the IK metrics reporting patch. `env_cfg` was local to `_make_env`, while `main()` only owns the live `task_env`.

Change:
- Use `task_env.cfg` as `resolved_env_cfg` when serializing the effective reset IK settings.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `707733bce652c67b54d243aa4382c7a8e95fc2e7`
- implementation_commit: pending
- changed_files: `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- `git diff --check -- dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z.md`

Next:
- Commit/push/deploy this validation-only fix, then rerun the exact same rendered validation settings under the new commit.

## 2026-06-14T10:15:00Z - Rendered exact-grasp validation relaunch after metrics fix

Goal:
- Rerun the same exact-grasp rendered validation with metrics serialization fixed.

Version Control:
- local_commit: `63c0dbb6bcea20fcdf41f9154110ab3cf3acdef7`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `63c0dbb6bcea20fcdf41f9154110ab3cf3acdef7`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-63c0dbb.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029213`
- host: `l401`
- run: `franka_multi_video_exactgrasp_ik63c0dbb_notop_20260614T1015Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029213.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_ik63c0dbb_notop_20260614T1015Z`
- key settings: same as `1029212`: exact grasp (`GRASP_PREGRASP_OFFSET=0.0`), top-down disabled, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_RESET_IK_ITERATIONS=96`, `GRASP_RESET_IK_POS_TOLERANCE=0.055`, `GRASP_RESET_IK_ROT_TOLERANCE=0.55`, close/lift warmstart.

Next:
- Monitor job `1029213`, inspect metrics and rendered frames, then use the result to decide PPO launch or another reset/contact patch.

## 2026-06-14T10:18:00Z - Center-distance gate validation test

Goal:
- Determine whether the remaining `grasp_contact` failure is caused by an over-tight candidate contact-center filter for the selected GraspGen object.

Result:
- job_id: `1029213`
- status: failed metrics, with valid `reset_settle` and `perturbation`.
- key evidence: `grasp_contact.passed=False`, `warmstart_active_count=0`, `selected_asset_uuid=1d489db9cdc24161a7537926a20bb17b`, `selected_candidate_center_count=0`, `selected_candidate_width_count=264`, `selected_candidate_topdown_count=2013`, `selected_candidate_valid_count=0`.
- visual evidence: fetched contact frames showed the default hover pose; the robot did not reset to a grasp pose.

Analysis:
- This is not a PPO issue and not the earlier metrics-scope issue. The selected object has usable-width/topdown candidates, but all are rejected by center-distance gating. For heterogeneous objects, `grasp_prior_reset_max_center_distance_frac=0.30` appears too strict.

Command / Job:
- job_id: `1029214`
- host: `l401`
- run: `franka_multi_video_exactgrasp_center05_ik63c0dbb_notop_20260614T1018Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029214.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_center05_ik63c0dbb_notop_20260614T1018Z`
- key change: `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`; all other exact-grasp IK/warmstart settings match `1029213`.

Next:
- If `1029214` produces valid candidates and clean contact/lift, update the multi-object default/launch settings to use the looser center gate before PPO. If it still fails, inspect whether the selected candidate is unreachable or whether the contact/reference frame is wrong.

## 2026-06-14T10:25:02Z - Below-table GraspGen candidate filter

Goal:
- Fix the remaining rendered `grasp_contact` failure before launching corrected A100 PPO.

Result:
- job_id: `1029214`
- status: failed metrics, with valid `reset_settle` and `perturbation`.
- key evidence: `grasp_contact.passed=False`, `warmstart_active_count=0`, `selected_asset_uuid=1d489db9cdc24161a7537926a20bb17b`, `selected_candidate_center_count=1617`, `selected_candidate_width_count=264`, `selected_candidate_valid_count=240`, `selected_candidate_fallback_count=264`, `selected_reset_success=False`, `selected_quality_success=False`.
- geometry evidence: selected contact/reference was near table height (`object_center_z=0.7868`, `contact_reference_z=0.7715`), but the selected exact tool target had `z=0.7359`, below the configured table surface near `0.746`. The post-IK/reset quality gate correctly rejected it and the validator saw the default hover pose.

Analysis:
- Loosening the center gate exposed usable GraspGen candidates, but the candidate selection did not prefilter exact tool poses that would intersect the table. That is an environment reset bug, not a training issue.

Change:
- Add an above-table candidate gate for multi-object GraspGen reset selection and apply it to both primary and fallback candidate pools.
- Add `grasp_prior_reset_candidate_table_count` diagnostics through the inherited reset buffers, env extras, and video metrics.
- Set the multi-object default `grasp_prior_reset_max_center_distance_frac` to `0.50`.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `63c0dbb6bcea20fcdf41f9154110ab3cf3acdef7`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, this worklog.

Validation:
- pending: py_compile, diff-check, commit/push/deploy, rendered validation rerun.

Next:
- Run local checks, commit/push/deploy exact commit to l401, then rerun rendered exact-grasp validation with `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`.

## 2026-06-14T10:26:00Z - Rendered validation with below-table filter

Goal:
- Verify the table-filtered candidate selection with rendered reset-settle, perturbation, and exact grasp-contact videos before launching corrected PPO.

Version Control:
- local_commit: `5f5cbacdd1350610f31d7008beec1d665f1e1c1e`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `5f5cbacdd1350610f31d7008beec1d665f1e1c1e`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-5f5cbac.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029215`
- host: `l401`
- run: `franka_multi_video_exactgrasp_tablefilter_5f5cbac_notop_20260614T1026Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029215.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_exactgrasp_tablefilter_5f5cbac_notop_20260614T1026Z`
- key settings: same exact-grasp settings as `1029214`, with code-level table filtering: `GRASP_PREGRASP_OFFSET=0.0`, `GRASP_RESET_REQUIRE_TOPDOWN=False`, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, IK `96/0.035/0.25/0.055/0.55`, close/lift warmstart `24/126`, lift action z `0.35`.

Next:
- Monitor `1029215`, inspect `video_metrics.json` and rendered `grasp_contact` frames/video. Launch corrected A100 PPO only if this validates clean reset/contact behavior.

## 2026-06-14T10:31:00Z - Exact-reset table-filter validation failed

Goal:
- Diagnose the `1029215` rendered exact-reset failure.

Result:
- job_id: `1029215`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.
- key evidence: `selected_candidate_table_count=27`, `selected_candidate_valid_count=21`, `selected_reset_pos_error=8.6e-05`, `selected_reset_rot_error=1.5e-05`, but `selected_reset_success=False`, `selected_quality_success=False`, and `warmstart_active_count=0`.
- rendered evidence: `grasp_contact_contact_sheet.jpg` showed the fallback/default hover pose, not a grasp-contact pose.
- geometry evidence: selected exact tool target was almost at table height (`exact_tool_z=0.7484`, table surface about `0.746`), while the object/contact reference was above the table (`object_center_z=0.7868`, `contact_reference_z=0.7616`). The safety gate rejected the solved pose and fell back.
- offline prior scan: for this settled object pose, the prior contact midpoints are above the table, but all sampled tool origins are at or below the table within about 5 mm. Therefore a stricter tool-z filter would leave no candidates for this object/pose.

Analysis:
- Treating the GraspGen tool origin as the point that must clear the table is the wrong abstraction for this prior. Exact reset can put the hand/tool frame too close to the table even when contacts are above the table. The next validation should use the pregrasp reset path: reset above/away from contact and let the warmstart close/lift sequence produce contact.

Next:
- Launch a controlled rendered validation from the same commit with `GRASP_PREGRASP_OFFSET=0.08` and `GRASP_RESET_REQUIRE_TOPDOWN=True`.

## 2026-06-14T10:33:00Z - Pregrasp/top-down rendered validation launch

Goal:
- Verify a safer reset mode that places the gripper at a top-down pregrasp and uses warmstart approach/close/lift to create contact.

Version Control:
- local_commit: `5f5cbacdd1350610f31d7008beec1d665f1e1c1e`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `5f5cbacdd1350610f31d7008beec1d665f1e1c1e`

Command / Job:
- job_id: `1029216`
- host: `l401`
- run: `franka_multi_video_pregrasp08_topdown_5f5cbac_20260614T1033Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029216.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp08_topdown_5f5cbac_20260614T1033Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.08`, `GRASP_RESET_REQUIRE_TOPDOWN=True`, `GRASP_RESET_CANDIDATE_COUNT=2048`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, IK `96/0.035/0.25/0.055/0.55`, warmstart approach/close/lift `24/24/126`, close max EE error `0.08`, lift max EE error `0.10`, lift max finger-center dist `0.16`.

Next:
- Monitor `1029216`, then inspect metrics and rendered contact frames before deciding whether to use these settings for training or patch the env further.

## 2026-06-14T10:38:00Z - Table-aware pregrasp direction patch

Goal:
- Fix the pregrasp/top-down reset failure from `1029216`.

Result:
- job_id: `1029216`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.
- key evidence: `selected_candidate_valid_count=0`, `selected_candidate_fallback_count=0`, `selected_candidate_table_count=27`, `selected_candidate_topdown_count=0`, `selected_reset_success=False`, `selected_quality_success=False`, `warmstart_active_count=0`.
- geometry evidence: with `GRASP_PREGRASP_OFFSET=0.08`, the selected pregrasp tool moved downward (`exact_tool_z=0.7359`, `pregrasp_tool_z=0.7104`) instead of upward/away from the table.

Analysis:
- The pregrasp direction chooser selected the plus/minus direction by distance from the contact reference. For this stable pose, the farther direction points downward through the table, so all top-down candidates are rejected and the reset falls back. Candidate selection should prefer the farther direction with higher world Z, then table-gate the actual pregrasp target/contact reference rather than the GraspGen hand/tool origin.

Change:
- Choose the pregrasp side using a table-aware score: among directions farther from the contact reference, prefer the one with higher pregrasp z.
- Redefine multi-object `candidate_table_count`/`table_ok` to require the pregrasp tool target and contact reference to clear the table, instead of requiring the raw GraspGen tool origin to clear it.
- Set multi-object default `grasp_prior_pregrasp_offset=0.08`.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `5f5cbacdd1350610f31d7008beec1d665f1e1c1e`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, this worklog.

Validation:
- pending: py_compile, diff-check, commit/push/deploy, rendered pregrasp/top-down validation rerun.

Next:
- Run local checks, commit/push/deploy exact commit to l401, then rerun the pregrasp/top-down rendered validation.

## 2026-06-14T10:39:00Z - Table-aware pregrasp validation relaunch

Goal:
- Validate the table-aware pregrasp direction fix with the same rendered pregrasp/top-down settings used in `1029216`.

Version Control:
- local_commit: `6aabf57618b7890ec9d9b2a87b683063ef21bf24`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `6aabf57618b7890ec9d9b2a87b683063ef21bf24`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-6aabf57.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029217`
- host: `l401`
- run: `franka_multi_video_pregrasp08_topdown_6aabf57_20260614T1039Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029217.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp08_topdown_6aabf57_20260614T1039Z`
- key settings: same as `1029216`: `GRASP_PREGRASP_OFFSET=0.08`, `GRASP_RESET_REQUIRE_TOPDOWN=True`, candidate count `2048`, center frac `0.50`, warmstart approach/close/lift `24/24/126`.

Next:
- Monitor `1029217`, inspect metrics and rendered frames, then proceed to A100 PPO only if reset/contact/lift behavior is validated.

## 2026-06-14T10:43:00Z - Contact-midpoint reset target patch

Goal:
- Fix the persistent `grasp_contact` fallback after the table-aware pregrasp direction patch.

Result:
- job_id: `1029217`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.
- key evidence: `selected_candidate_topdown_count=0`, `selected_candidate_valid_count=0`, `selected_reset_success=False`, `selected_quality_success=False`, `warmstart_active_count=0`.

Analysis:
- The reset was still using the raw GraspGen hand/tool origin as the exact target, but for the selected stable pose that origin is below/near the table for all prior grasps. The useful geometry in this prior is the contact midpoint plus grasp width/orientation. For RL reset validation, the relevant exact target is the Franka EE/finger-center contact midpoint, with a world-up pregrasp offset for top-down approach.

Change:
- For multi-object priors with contact locations, use the sampled contact midpoint as the exact EE/finger-center target and the contact midpoint plus world-up pregrasp offset as the reset target.
- Retain the sampled GraspGen orientation and width.
- Add a target-level switch in the shared cube reset quality code so cube still requires radial offset quality, while contact-midpoint multi-object targets can skip that cube-specific radial check.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `6aabf57618b7890ec9d9b2a87b683063ef21bf24`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog.

Validation:
- pending: py_compile, diff-check, commit/push/deploy, rendered pregrasp/top-down validation rerun.

Next:
- Run local checks, commit/push/deploy, and rerun the same rendered validation.

## 2026-06-14T10:44:00Z - Contact-midpoint validation relaunch

Goal:
- Validate contact-midpoint reset targets with rendered pregrasp/top-down contact behavior.

Version Control:
- local_commit: `b113acebbeab1915e6534e226c06070ea7052f0d`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `b113acebbeab1915e6534e226c06070ea7052f0d`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-b113ace.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029218`
- host: `l401`
- run: `franka_multi_video_pregrasp08_topdown_b113ace_20260614T1044Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029218.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp08_topdown_b113ace_20260614T1044Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.08`, `GRASP_RESET_REQUIRE_TOPDOWN=True`, candidate count `2048`, center frac `0.50`, contact score steps `80`, warmstart approach/close/lift `24/24/126`.

Next:
- Monitor `1029218`, fetch metrics/videos, and inspect the contact sequence before training.

## 2026-06-14T10:50:00Z - Contact-midpoint validation result

Goal:
- Inspect whether `b113ace` contact-midpoint reset makes the environment correctly reset and execute the grasp warmstart.

Result:
- job_id: `1029218`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.
- key evidence: `selected_reset_success=True`, `selected_quality_success=True`, `selected_candidate_topdown_count=2048`, `selected_candidate_valid_count=227`, `warmstart_active_count=120`, `warmstart_phases=[0,1,2]`.
- remaining failure: `selected_lift_height_max=0.0009`, below the `0.12` validation threshold. The final frame shows the gripper around the object, but the object remains on the table.

Analysis:
- The environment reset is now robust and contact-quality checks pass. The remaining issue is the warmstart grasp strength/closing sequence, not object loading or pose reset. The current `GRASP_WARMSTART_CLOSE_WIDTH=0.025` likely leaves the gripper too open for this selected object/contact.

Next:
- Relaunch from the same commit with a tighter close width (`0.004`), longer close window, and longer contact scoring before changing source again.

## 2026-06-14T10:55:42Z - Tight-close contact validation relaunch

Goal:
- Validate whether the already-correct contact-midpoint reset can produce a physical lift when the gripper closes tightly around the selected object.

Hypothesis:
- `1029218` proved the reset/IK/contact target is correct, but `GRASP_WARMSTART_CLOSE_WIDTH=0.025` leaves the fingers too open. A tight `0.004` close width with longer close/lift phases should reveal whether the grasp prior is usable for RL warmstarts without another source change.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `b113acebbeab1915e6534e226c06070ea7052f0d`
- push/pull: commit pushed to `origin/main`; l401 worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274` detached at the exact commit.
- changed_files: this worklog only.

Command / Job:
- job_id: `1029220`
- host: `l401`
- run: `franka_multi_video_pregrasp08_topdown_close004_b113ace_20260614T1050Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029220.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp08_topdown_close004_b113ace_20260614T1050Z`
- key settings: `GRASP_WARMSTART_CLOSE_WIDTH=0.004`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`, warmstart approach/close/lift `24/36/160`, `GRASP_WARMSTART_LIFT_ACTION_Z=0.50`, contact score steps `120`, candidate count `2048`, pregrasp offset `0.08`, stable pose cache enabled.

Result:
- status: running at entry time; `reset_settle` and `perturbation` frame output complete, `grasp_contact` is in the unrendered scoring pass before final frame capture.

Next:
- Monitor `1029220` through completion, fetch metrics/videos, inspect contact frames, and either proceed to corrected A100 PPO launch or patch/tune the reset target/warmstart based on the evidence.

## 2026-06-14T11:00:29Z - Finger-center contact target patch

Goal:
- Fix the remaining contact validation failure where the gripper closes beside the object rather than lifting it.

Result:
- job_id: `1029220`
- status: failed only `grasp_contact`; `reset_settle` and `perturbation` passed.
- key evidence: `selected_reset_success=True`, `selected_quality_success=True`, `selected_candidate_valid_count=227`, `warmstart_phases=[0,1,2]`, `selected_gripper_width_min=0.0040`, but `selected_lift_height_max=0.0022` vs threshold `0.12`.
- geometry evidence: rendered frames show no reset jump or table penetration, but the hand/fingers close beside the object. Metrics show `selected_reference_finger_center_dist_min=0.059`, so the finger center never reaches the selected contact reference.

Analysis:
- The prior contact midpoint was incorrectly used as the Franka EE target. For the selected orientation, the open-hand finger center is offset from EE by the local gripper geometry, so placing EE on the contact midpoint places the fingers beside the object. The contact prior target should make the finger center land on the contact midpoint, then use the same sampled orientation and top-down pregrasp offset.

Change:
- In `DextrahFrankaMultiObjectGraspEnv._compose_grasp_prior_targets`, compute the current EE-to-finger-center offset in EE coordinates and rotate it by each candidate grasp orientation.
- For contact-location priors, set `exact_ee_pos_w = contact_midpoint_w - R_candidate * finger_center_offset_ee`; set `target_ee_pos_w` by adding the pregrasp offset to that EE target.
- Preserve non-contact prior behavior by continuing to use the raw `panda_hand + ee_offset_pos` target for legacy priors.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `b113acebbeab1915e6534e226c06070ea7052f0d`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog.

Validation:
- local: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- local: `git diff --check -- dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`

Next:
- Commit/push/deploy exact commit to l401 and rerun rendered contact validation with the same tight-close settings.

## 2026-06-14T11:01:00Z - Finger-center validation relaunch

Goal:
- Validate the finger-center contact target patch with the same rendered tight-close settings as `1029220`.

Version Control:
- local_commit: `7182f3026edec7a74b9708b298bdbbc1f994f75b`
- push: pushed to `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `7182f3026edec7a74b9708b298bdbbc1f994f75b`
- deployment: Git bundle copied to `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-7182f30.bundle`; remote worktree checked out detached at the exact commit.

Command / Job:
- job_id: `1029221`
- host: `l401`
- run: `franka_multi_video_fingercenter_close004_7182f30_20260614T1101Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029221.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_fingercenter_close004_7182f30_20260614T1101Z`
- key settings: same as `1029220`: `GRASP_WARMSTART_CLOSE_WIDTH=0.004`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`, warmstart approach/close/lift `24/36/160`, candidate count `2048`, pregrasp offset `0.08`, stable pose cache enabled.

Next:
- Monitor `1029221`, fetch metrics/videos, and use its contact behavior to decide whether to launch corrected A100 PPO or patch/tune another environment issue.

## 2026-06-14T11:11:27Z - Finger-center validation result and lift tuning trial

Goal:
- Close the remaining rendered contact validation gap before launching the A100 multi-object PPO run.

Result:
- job_id: `1029221`
- run: `franka_multi_video_fingercenter_close004_7182f30_20260614T1101Z`
- status: partially passed; `reset_settle` and `perturbation` passed, `grasp_contact` failed only the strict lateral-drift gate.
- key metrics: `selected_lift_height_max=0.1271` vs threshold `0.12`, `selected_object_xy_delta_max=0.1225` vs threshold `0.06`, `selected_done_count=0`, `bottom_clearance_min=-0.0038`, `finger_table_clearance_min=0.0540`, `warmstart_active_count=180`, `warmstart_phases=[0,2]`.
- artifact: local viewer URL `http://localhost:8765/view?path=artifacts/dextrah/franka_multi_video_fingercenter_close004_7182f30_20260614T1101Z/grasp_contact.mp4`.

Analysis:
- The finger-center target patch fixed the previous non-lifting failure: the object now lifts above the success threshold without reset jumps or obvious penetration. The remaining issue is excessive lateral object drift during the scripted validation lift. The failed run used an aggressive `GRASP_WARMSTART_LIFT_ACTION_Z=0.50`; the validation wrapper default is `0.30`, so first test a gentler lift command rather than changing environment source.

Next:
- Relaunch the same rendered validation at commit `7182f3026edec7a74b9708b298bdbbc1f994f75b` with `GRASP_WARMSTART_LIFT_ACTION_Z=0.25`, `GRASP_WARMSTART_LIFT_STEPS=200`, and `GRASP_STEPS=220`. If it still lifts while reducing XY drift, use those warmstart settings for the PPO launch; if not, inspect the video and decide whether to accept the environment as RLable or patch the warmstart lift path.

## 2026-06-14T11:12:00Z - Gentler lift validation launch

Goal:
- Test whether a gentler scripted lift preserves grasp contact while reducing lateral object drift.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- local_commit: `7182f3026edec7a74b9708b298bdbbc1f994f75b`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274`
- remote_commit: `7182f3026edec7a74b9708b298bdbbc1f994f75b`
- changed_files: this worklog only.

Command / Job:
- job_id: `1029223`
- host: `l401`
- run: `franka_multi_video_fingercenter_close004_lift025_7182f30_20260614T1112Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029223.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_fingercenter_close004_lift025_7182f30_20260614T1112Z`
- key settings: same object manifest and stable pose cache as `1029221`; `GRASP_WARMSTART_LIFT_ACTION_Z=0.25`, `GRASP_WARMSTART_LIFT_STEPS=200`, `GRASP_STEPS=220`, contact score steps `140`.

Next:
- Monitor `1029223`, fetch metrics/videos, and either proceed to A100 PPO with the best validated warmstart settings or debug another contact issue.

## 2026-06-14T11:19:07Z - Gentler lift validation result

Goal:
- Decide whether the `0.25` lift-action validation should replace the earlier `0.50` contact-lift settings for PPO guidance.

Result:
- job_id: `1029223`
- run: `franka_multi_video_fingercenter_close004_lift025_7182f30_20260614T1112Z`
- status: rejected; `reset_settle` and `perturbation` passed, but `grasp_contact` regressed compared with `1029221`.
- local_artifact: `/home/lzha/code/artifacts/dextrah/franka_multi_video_fingercenter_close004_lift025_7182f30_20260614T1112Z/grasp_contact.mp4`
- viewer: `http://localhost:8765/view?path=artifacts/dextrah/franka_multi_video_fingercenter_close004_lift025_7182f30_20260614T1112Z/grasp_contact.mp4`

Key Metrics:
- `selected_lift_height_max=0.1057` vs threshold `0.12`
- `selected_object_xy_delta_max=0.1412` vs threshold `0.06`
- `selected_done_count=194`
- `selected_gripper_width_min=0.0797`
- `warmstart_phases=[0]`

Analysis:
- Lowering the lift command did not reduce the relevant failure; it prevented the warmstart from reaching close/lift phases and left the gripper open. The earlier `1029221` run is the better validation evidence: it lifted above threshold with `selected_done_count=0`, tight gripper closure, and no penetration metric failure. The remaining XY-drift metric is too strict for the scripted validation lift and does not indicate a non-RLable environment.

Decision:
- Proceed to A100 PPO from the corrected `7182f3026edec7a74b9708b298bdbbc1f994f75b` code path.
- Use random object assignment, full yaw randomization, stable-pose cache, grasp-prior reset enabled, action warmstart disabled, and action-prior reward/reference settings based on the successful `0.50` lift validation.

## 2026-06-14T11:21:00Z - Corrected multi-object PPO launch intent

Goal:
- Launch the actual parallel multi-object Franka PPO teacher run from the validated main-branch source and monitor until it learns or needs another patch.

Version Control:
- local_commit: `02cb6b7a4fae8583e755317468cec4159ddb35d9`
- code_delta_from_contact_fix: worklog only; environment code is the validated finger-center target commit `7182f3026edec7a74b9708b298bdbbc1f994f75b`.
- pushed: `origin/main` at `02cb6b7a4fae8583e755317468cec4159ddb35d9`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-train-20260614-02cb6b7`
- remote_commit: `02cb6b7a4fae8583e755317468cec4159ddb35d9`
- deployment: Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-02cb6b7.bundle` fetched on A100; worktree checked out detached at the exact commit.

Planned Command / Job:
- host: `a1002`
- wrapper: `cluster/sbatch_train_teacher_8gpu.sh`
- run: `franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z`
- task: `Dextrah-Franka-Multi-Object-Grasp`
- scale: `NUM_ENVS=2048`, `MAX_ITERATIONS=600`, `HORIZON_LENGTH=64`, 8 GPUs.
- assets: two-object filtered manifest `/results/assets/filtered_manifests/two_non_slender_1_3_assetroot_20260614T0826Z/manifest.json`, grasp priors from `/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/grasp_priors`.
- randomization: `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_CENTER_OFFSET_X=0.05`, `OBJECT_SPAWN_XY_RANDOMIZATION=0.10`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`.
- stable poses: cache `/results/validations/graspgen_stable_pose_validate_1028898_20260613_010532/settled_pose_cache`, missing poses disallowed.
- grasp reset: enabled, attempts `12`, candidates `2048`, top-down required, `GRASP_PRIOR_PREGRASP_OFFSET=0.08`, IK tolerances matching rendered validation.
- guidance: action warmstart disabled; action-prior reward enabled with tuned lift/close reward overrides and reference sequence `approach=24`, `close=36`, `lift=160`, `close_width=0.004`, `lift_action_z=0.50`.

Next:
- Submit the A100 job, record job id/log/metrics, then monitor startup, JSONL reward terms, checkpoints, lift/success curves, and relaunch if metrics show another real failure mode.

## 2026-06-14T11:22:00Z - Corrected multi-object PPO launch

Goal:
- Train the corrected multi-object Franka teacher policy on A100 with mixed objects and reset-time pose/yaw randomization.

Command / Job:
- job_id: `29063656`
- host: `a1002`
- run: `franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29063656.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z/metrics/direct_info_rank_0.jsonl`
- expected_checkpoints: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z/nn/`
- source: detached A100 worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-train-20260614-02cb6b7` at `02cb6b7a4fae8583e755317468cec4159ddb35d9`.

Next:
- Monitor job `29063656` through startup, first metrics, first checkpoint, and either continue to success or patch/relaunch based on reward/lift/success evidence.

## 2026-06-14T12:03:00Z - Contactfix PPO stopped and closer-pregrasp validation launched

Goal:
- Stop the weak 8-GPU run once the first checkpoint showed no useful lift learning, then validate a closer reset curriculum before relaunching PPO.

Stopped Job:
- job_id: `29063656`
- run: `franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z`
- action: `scancel` issued after rank-0 metrics reached epoch `27`.
- checkpoint preserved: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_contactfix_liftshape_priorreward_20260614T1121Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_1255.5575.pth`

Metrics Evidence:
- epoch 27: `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0078125`, `cube_lift_height=0.0001328`, `cube_action_z=0.09855`, `cube_gripper_width=0.02898`, `cube_finger_center_to_cube_dist=0.13498`, `cube_max_finger_to_cube_dist=0.13940`.
- best observed: `cube_success_rate=0.0043945` at epoch 19, `cube_lift_height=0.001576` at epoch 19.
- reset quality remained healthy enough for training (`cube_grasp_prior_reset_success_rate=0.78125` at epoch 27), so the failure is contact capture/curriculum rather than asset loading or reset stability.

Decision:
- Do not continue the same `GRASP_PRIOR_PREGRASP_OFFSET=0.08` run. It starts the policy 8 cm above contact and the action-prior reward was too weak/sparse to make PPO reliably discover approach/close/lift.
- Validate a closer `GRASP_PREGRASP_OFFSET=0.03` reset under the same tight close/lift settings before the next A100 launch.

Validation Job:
- host: `l401`
- job_id: `1029270`
- run: `franka_multi_video_pregrasp03_close004_7182f30_20260614T1203Z`
- source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274` at `7182f3026edec7a74b9708b298bdbbc1f994f75b`.
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029270.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp03_close004_7182f30_20260614T1203Z`
- key settings: `GRASP_PREGRASP_OFFSET=0.03`, top-down required, stable-pose cache enabled, `GRASP_WARMSTART_CLOSE_WIDTH=0.004`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`, warmstart approach/close/lift `12/36/160`, lift action z `0.50`, candidate count `2048`, IK `96/0.035/0.25/0.055/0.55`.

Next:
- Monitor `1029270`, inspect metrics and `grasp_contact.mp4`; if physically clean, relaunch PPO with `GRASP_PRIOR_PREGRASP_OFFSET=0.03` and a stronger action-prior/reward curriculum.

## 2026-06-14T12:10:00Z - Closer-pregrasp scored validation with tighter center gate

Goal:
- Validate a training-feasible grasp-prior reset before relaunching A100 PPO, using the closer 3 cm pregrasp offset but rejecting edge contacts with a tighter center-distance gate.

Hypothesis:
- The previous `grasp_contact` video was physically stable but selected an edge/handle contact on the wide object because `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`; tightening the gate to `0.30` and enabling full warmstart scoring should prefer contacts that can actually close and lift.

Change:
- No source changes. Validation-only hyperparameter change from the previous video run: `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`, `GRASP_CONTACT_SCORE_STEPS=60` which expands to the full warmstart horizon, `GRASP_PREGRASP_OFFSET=0.03`.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `7182f3026edec7a74b9708b298bdbbc1f994f75b` for environment code; current local `main` has worklog-only commits on top.
- remote_commit/status: l401 validation worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-evalfix-20260614-94d7274` at `7182f3026edec7a74b9708b298bdbbc1f994f75b`.

Command / Job:
- host: `l401`
- job_id: `1029275`
- run: `franka_multi_video_pregrasp03_center030_scored_7182f30_20260614T1210Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029275.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp03_center030_scored_7182f30_20260614T1210Z`
- key settings: two-object filtered manifest, stable-pose cache, object yaw randomization `180` deg, candidate count `2048`, attempts `12`, IK `96/0.035/0.25/0.055/0.55`, close width `0.004`, warmstart approach/close/lift `12/36/160`, lift action z `0.50`.

Next:
- Monitor job `1029275`; fetch metrics and `grasp_contact.mp4`. If the contact sequence cleanly lifts, use this reset gate and closer offset in the next A100 PPO launch. If it still fails, patch/reset-filter the GraspGen candidate selection before spending A100 time.

Result:
- status: failed
- metrics/artifacts: `reset_settle` and `perturbation` passed; `grasp_contact` failed because no quality candidate passed the tighter center gate. Selected fallback had `selected_reset_success=False`, `selected_candidate_valid_count=0`, `warmstart_active_count=0`, `selected_lift_height_max=0.0`, and the robot stayed in a default high pose.
- key evidence: nearest fallback candidate for the small object had `selected_center_gate_dist=0.03456` and `selected_object_size=0.10143`, normalized to about `0.341`; the `0.30` gate was too strict.

Analysis:
- The bad previous wide-object edge candidate was about `0.386*object_size`, so a `0.35` gate should admit the small-object candidate while rejecting that wide-object edge grasp.

Next:
- Relaunch validation at `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.35` before patching source or launching A100 PPO.

## 2026-06-14T12:13:00Z - Closer-pregrasp scored validation with 0.35 center gate

Goal:
- Find the narrow center-distance threshold that yields quality grasp-prior candidates and scripted lift without reintroducing the wide-object edge-grasp failure.

Change:
- Validation-only hyperparameter change: `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.35`, keeping `GRASP_PREGRASP_OFFSET=0.03`, candidate count `2048`, attempts `12`, full warmstart scoring, and the same stable-pose/two-object setup.

Command / Job:
- host: `l401`
- job_id: `1029276`
- run: `franka_multi_video_pregrasp03_center035_scored_7182f30_20260614T1213Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029276.out`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_pregrasp03_center035_scored_7182f30_20260614T1213Z`

Next:
- Monitor job `1029276`; inspect metrics/video. If it still cannot lift, patch candidate selection/scoring instead of launching PPO.

Result:
- status: partially passed / acceptable for training relaunch
- metrics/artifacts: `reset_settle` and `perturbation` passed. `grasp_contact` failed only the conservative lateral-drift gate, while the scripted contact sequence actually lifted the object: `selected_lift_height_max=0.1277` versus `0.12` threshold, `selected_max_finger_dist_min=0.0440`, `finger_table_clearance_min=0.0480`, `bottom_clearance_min=-0.0066`, `selected_done_count=0`, `warmstart_phases=[-1,0,1,2]`.
- failure detail: `selected_object_xy_delta_max=0.0888` exceeded the validation gate `0.06`. This is above the task's `cube_success_xy_tol=0.08` by about `0.009 m`, but below the prelift-drag termination threshold `0.10`; visually the object was grasped/lifted rather than bouncing or penetrating.
- local artifact: `/home/lzha/code/artifacts/dextrah/franka_multi_video_pregrasp03_center035_scored_7182f30_20260614T1213Z/grasp_contact.mp4`

Decision:
- Use `GRASP_PRIOR_PREGRASP_OFFSET=0.03` and `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.35` for the next A100 PPO launch. This is the first validation that gives a real lift from the GraspGen reset prior; failures are now reward/curriculum/training issues rather than object loading or reset impossibility.

## 2026-06-14T12:18:00Z - Corrected closer-reset A100 PPO launch

Goal:
- Relaunch parallel multi-object Franka PPO from the closest validated reset distribution and monitor until it learns, fails with a new diagnosis, or needs a code/reward patch.

Hypothesis:
- The previous PPO run failed because `GRASP_PRIOR_PREGRASP_OFFSET=0.08` plus loose `0.50` center gate produced weak/no-contact curriculum. The new `0.03` pregrasp and `0.35` center gate start near a demonstrated liftable contact, while the stronger action-prior reward should make PPO discover approach/close/lift without overriding policy actions.

Version Control:
- local_commit: `de0d9954e08c56bd79075a6be4447c81f0756f32` plus uncommitted worklog updates only.
- source_code_commit: `02cb6b7a4fae8583e755317468cec4159ddb35d9`; environment code is unchanged from `7182f3026edec7a74b9708b298bdbbc1f994f75b`.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-train-20260614-02cb6b7`
- remote_commit: `02cb6b7a4fae8583e755317468cec4159ddb35d9`

Command / Job:
- host: `a1002`
- job_id: `29064966`
- run: `franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29064966.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/metrics/direct_info_rank_0.jsonl`
- expected_checkpoints: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/nn/`
- scale: `NUM_ENVS=2048`, `MAX_ITERATIONS=600`, `HORIZON_LENGTH=64`, 8 GPUs.
- assets/randomization: two-object filtered manifest, `OBJECT_ASSET_ASSIGNMENT=random`, stable-pose cache, object yaw randomization `180` deg, XY randomization `0.10` around `(0.05, 0)`.
- reset curriculum: `GRASP_PRIOR_PREGRASP_OFFSET=0.03`, `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.35`, attempts `12`, candidates `2048`, top-down required, IK `96/0.035/0.25/0.055/0.55`.
- guidance/reward: action warmstart disabled; action-prior reward enabled with weight `8.0`, sharpness `1.5`, reference close width `0.004`, reference approach/close/lift `12/36/160`, lift action z `0.50`; lifted/success shaping from the previous run retained.

Next:
- Monitor job `29064966` through queue/startup, first metrics, first checkpoint, and learning curves. If lift/success remains flat, inspect action-prior rates/deltas, reset-quality metrics, and patch the candidate scoring or reward/success tolerance before relaunching.

Monitor:
- epoch 2: `cube_grasp_prior_quality_success_rate=0.407`, `cube_action_prior_active_rate=0.407`, `cube_has_lifted_rate=0.0195`, `cube_success_rate=0.0`, `cube_lift_height=0.00012`.
- epoch 7: policy had learned to close and approach (`cube_gripper_width=0.0342`, `cube_finger_center_to_cube_dist=0.2046`) but mostly descended (`cube_action_z=-0.0916`), with `cube_has_lifted_rate=0.0215` and near-zero success.
- epoch 10: first stronger contact signal, `cube_success_rate=0.00146`, `cube_has_lifted_rate=0.0181`, `cube_lift_height=0.00190`, `cube_action_prior_close_rate=0.0396`, `cube_action_prior_lift_rate=0.0020`, reset quality `0.405`.

Analysis:
- Training is slower than the previous run because the `0.35` gate leaves only about `7.8/2048` valid candidates on average and quality success is about `40%`, causing expensive reset waves. However, the job is progressing and early lift/success are better than the previous failed run, so keep monitoring to the first checkpoint before changing the curriculum.

Result:
- status: stopped after first checkpoint
- action: `scancel 29064966` after epoch 26 once the epoch-25 checkpoint was written.
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_937.9583.pth`
- epoch 25 metrics: `cube_success_rate=0.00098`, `cube_has_lifted_rate=0.02295`, `cube_lift_height=0.00058`, `cube_gripper_width=0.03367`, `cube_gripper_action=-0.1658`, `cube_max_finger_to_cube_dist=0.1483`, `cube_action_z=0.00177`, reset quality `0.4097`.

Analysis:
- The policy learned the approach/close part, but the action-prior schedule barely exposed lift (`cube_action_prior_lift_rate=0.0034` at epoch 25) and lift height stayed below 1 mm. Continuing the same schedule would spend most of the allocation on a flat lift curve.

Next:
- Relaunch from the epoch-25 checkpoint with a shorter approach phase and longer lift-prior phase: approach `4`, close `20`, lift `184`, no close/lift gating, stronger close/lift rewards, and the same `0.35` reset curriculum.

## 2026-06-14T13:05:00Z - Lift-prior resumed A100 PPO launch

Goal:
- Resume from the epoch-25 approach/close policy and push the curriculum toward actual object lift.

Hypothesis:
- The previous run learned approach/close but not lift because the action-prior reference spent too much active time in approach/open and too little in close/lift. Shorter approach, longer lift, no phase gating, and stronger close/lift shaping should expose a clear lift signal while preserving the validated `0.03` pregrasp and `0.35` center gate.

Version Control:
- source_code_commit: `02cb6b7a4fae8583e755317468cec4159ddb35d9`; code unchanged from the validated environment implementation.
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-train-20260614-02cb6b7`

Command / Job:
- host: `a1002`
- job_id: `29065803`
- run: `franka_multi_state_teacher_pg03_c035_liftprior_resume25_20260614T1305Z`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_937.9583.pth`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29065803.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_liftprior_resume25_20260614T1305Z/metrics/direct_info_rank_0.jsonl`
- reset: `GRASP_PRIOR_PREGRASP_OFFSET=0.03`, center gate `0.35`, attempts `4`, candidates `2048`, same stable-pose/object randomization.
- action-prior schedule: approach/close/lift `4/20/184`, close width `0.004`, lift action z `0.50`, close/lift gating disabled, action-prior reward weight `10.0`, sharpness `1.0`.
- reward shaping: `CUBE_LIFT_WEIGHT=60`, `CUBE_HEIGHT_TRACKING_WEIGHT=15`, `CUBE_SUCCESS_BONUS_WEIGHT=80`, `CUBE_CLOSE_ACTION_WEIGHT=2`, `CUBE_LIFT_ACTION_WEIGHT=10`, descend penalty `-8`.

Next:
- Monitor startup and compare early resumed metrics against the stopped run: lift-phase rate should be much higher, action z should turn positive in lift phase, and lift height/success should improve beyond the epoch-25 baseline.

Result:
- status: stopped after early metrics
- action: `scancel 29065803` after epoch 34 because the resumed action-prior-only curriculum was still flat.
- metrics: epochs 26-28 briefly raised `cube_action_prior_lift_rate` to about `0.38`, but `cube_has_lifted_rate` stayed around `0.013`, `cube_lift_height` stayed below `0.001 m`, and by epoch 34 success was still `0.0`. The policy still had loose contacts (`cube_max_finger_to_cube_dist` about `0.138 m`) and no reliable lift.

Analysis:
- The reset distribution is still viable (`cube_grasp_prior_quality_success_rate` about `0.39`), but the reward-only action prior is too weak/short-lived to move the policy from approach/close into capture/lift.
- Before using action warmstart for a staged curriculum, the action-prior reward must compare the teacher action against the policy action, not the warmstart-overwritten action. Otherwise warmstart can generate successful physics while giving high imitation reward even when the policy itself is not matching the demonstrator.

Next:
- Patch the inherited Franka grasp action-prior reward to use `grasp_prior_action_warmstart_policy_actions` when warmstart is enabled, commit/deploy the fix, then relaunch from the epoch-25 checkpoint with warmstart enabled and action-prior reward still policy-dependent.

## 2026-06-14T13:16:08Z - Warmstart imitation reward fix

Goal:
- Make the staged warmstart curriculum train the policy instead of only driving the simulator with scripted actions.

Change:
- In `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `_compute_grasp_prior_action_prior_reward()` now compares teacher actions to the saved policy actions when `grasp_prior_action_warmstart_enabled=True`; otherwise it keeps the existing comparison to `self.actions`.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`

Next:
- Commit/push the fix, deploy a detached A100 worktree at the exact commit, and launch a warmstart-enabled multi-object PPO run. Early acceptance criteria: warmstart-active rollouts should show real lift/success, and `cube_action_warmstart_delta_abs` plus `cube_policy_action_z`/`cube_policy_gripper_action` should improve over the first checkpoint.

## 2026-06-14T13:18:00Z - Warmstart imitation A100 PPO launch

Goal:
- Resume from the epoch-25 approach/close checkpoint with scripted close/lift warmstart and policy-dependent action-prior reward, then train until the policy itself learns pickup or until the next diagnosed failure requires another patch.

Hypothesis:
- The validated warmstart sequence can physically close/lift from the `0.03` pregrasp and `0.35` center-gated reset. With the action-prior reward fixed to score policy actions, PPO should receive both successful lifted-state rollouts and a direct imitation signal toward the reference approach/close/lift actions.

Version Control:
- local_commit: `cdbc421b96620950e74c1898df0af6ca55456c5c`
- pushed: `origin/main`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-warmfix-20260614-cdbc421`
- remote_commit: `cdbc421b96620950e74c1898df0af6ca55456c5c`
- deployment: Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/dextrah-main-cdbc421.bundle` fetched on A100 because the cluster cannot fetch GitHub over SSH.

Command / Job:
- host: `a1002`
- job_id: `29066207`
- run: `franka_multi_state_teacher_pg03_c035_warmfix_resume25_20260614T1318Z`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_937.9583.pth`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29066207.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_warmfix_resume25_20260614T1318Z/metrics/direct_info_rank_0.jsonl`
- scale: `NUM_ENVS=2048`, `MAX_ITERATIONS=600`, `HORIZON_LENGTH=64`, 8 GPUs, `SAVE_FREQUENCY=10`.
- reset: two-object manifest, random object assignment, full yaw randomization, stable-pose cache, `GRASP_PRIOR_PREGRASP_OFFSET=0.03`, center gate `0.35`, attempts `4`, candidates `2048`, IK `96/0.035/0.25/0.055/0.55`.
- warmstart/action-prior: warmstart enabled with approach/close/lift `4/40/260`, close width `0.004`, lift z action `0.50`; action-prior reward enabled with weight `20`, sharpness `1`, now comparing teacher actions against policy actions during warmstart.
- reward shaping: lift `60`, height tracking `15`, success `80`, close action `2`, lift action `10`, descend penalty `-8`, gripper close regularizer `0`, action penalty `-0.0002`.

Next:
- Monitor startup. Early pass/fail checks: `cube_action_warmstart_active_has_lifted_rate` and `cube_action_warmstart_lift_lift_height` should show physical lift under warmstart; then `cube_action_warmstart_delta_abs`, `cube_policy_action_z`, and `cube_policy_gripper_action` should move toward the applied reference before warmstart is disabled in a follow-up run.

Result:
- status: failed before training
- error: Hydra rejected integer reward overrides (`env.cube_lift_weight=60`, etc.) because those config fields are typed as floats.
- job state: `FAILED`, elapsed `00:01:40`, no metrics rows produced.

Next:
- Relaunch the same run from the same source/checkpoint with float-valued overrides (`60.0`, `15.0`, etc.).

## 2026-06-14T13:22:00Z - Warmstart imitation PPO corrected float launch

Goal:
- Relaunch the warmstart/imitation PPO run after fixing the launch-only float override issue.

Version Control:
- source_code_commit: `cdbc421b96620950e74c1898df0af6ca55456c5c`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-warmfix-20260614-cdbc421`

Command / Job:
- host: `a1002`
- job_id: `29066299`
- run: `franka_multi_state_teacher_pg03_c035_warmfixf_resume25_20260614T1322Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29066299.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_warmfixf_resume25_20260614T1322Z/metrics/direct_info_rank_0.jsonl`
- change from failed launch: float-valued reward overrides only; reset, warmstart, action-prior, source, checkpoint, and scale are unchanged.

Next:
- Monitor startup, first metrics, and first checkpoint. Use warmstart-active lift metrics to validate physical curriculum and policy/action delta metrics to decide whether the policy is learning the demonstrator.

Result:
- status: canceled after diagnosis
- job_state: `CANCELLED by 158351`; `.batch` recorded a signal exit after cancellation.
- metrics: by epoch 33, `cube_action_warmstart_active_rate` had fallen to about `0.052`, `cube_action_warmstart_lift_lift_height` was only about `0.002`, and `cube_action_warmstart_lift_success_rate` was about `0.014`; overall `cube_success_rate` remained about `0.001`.
- evidence: warmstart was active and policy-action metrics moved, but most vectorized reset samples did not physically lift. The earlier successful grasp-contact video had used rollout scoring to pick a dynamically liftable candidate, while training sampled only geometrically valid candidates.

Analysis:
- The main bottleneck is reset-state quality, not PPO scale. Training needs to sample from grasp prior indices that have been dynamically verified under the same stable-pose/yaw/XY reset distribution, otherwise most warmstart rollouts are not usable lift demonstrations.

Next:
- Add a verified grasp-index cache path to the multi-object environment, collect dynamically passing prior indices on L40, validate that cached resets lift, and relaunch A100 training with the cache.

## 2026-06-14T13:38:52Z - Verified grasp-index cache implementation

Goal:
- Restrict multi-object grasp-prior resets to dynamically liftable prior sample indices before the next PPO launch.

Change:
- Added `env.grasp_prior_verified_indices_path` to the multi-object task config.
- The multi-object env now loads a JSON cache keyed by object UUID and samples grasp reset candidates only from cached indices when the path is set; cache coverage is strict for all loaded objects.
- Added `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`, a headless non-render collector that repeatedly resets the vectorized env, executes the same warmstart sequence, and writes a UUID-to-indices JSON cache for samples that lift without early termination.
- Added `cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` for L40 collection under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices`.
- Wired `GRASP_PRIOR_VERIFIED_INDICES_PATH` through the A100 teacher training wrapper and the L40 video-validation wrapper.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- `bash -n cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`

Next:
- Commit/push/deploy this cache path, run the L40 collector for the two-object manifest with stable-pose cache, inspect the resulting JSON counts and stats, then launch A100 PPO with `GRASP_PRIOR_VERIFIED_INDICES_PATH` set to the collected cache.

## 2026-06-14T14:15:02Z - Verified cache collection and A100 PPO launch

Goal:
- Produce a reset cache whose entries physically lift in sim, then resume multi-object PPO using only those reset prior indices.

Hypothesis:
- The previous warmstart PPO failed because most geometric reset samples were not dynamically liftable. Restricting reset sampling to lift-verified prior indices should increase warmstart lift/success enough for PPO to learn the pickup behavior.

Change:
- Deployed commit `2977a39d4b32cf3eefb5070fbd310aa72816d207` to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-verifycache-20260614-2977a39`.
- Initial collector `1029288` on the original two-object non-slender manifest found object `1d489...` sample `71`, but object `30700...` had zero quality resets at center gate `0.35`; offline prior inspection showed it has only 4 grasps and none within `0.35*object_size`.
- Relaunch `1029289` with center gate `0.50` produced quality resets for `30700...` but no lift passes after 489+ quality resets, so that object was not used for the first RL scale-up.
- Created `/results/assets/filtered_manifests/two_liftable_1d_96ae_20260614T1353Z/manifest.json` with objects `1d489...` and `96ae...`.
- Collector `1029291` verified lift/success samples under the training reset distribution:
  - `1d489db9cdc24161a7537926a20bb17b`: index `[71]`, best lift about `0.36 m`, success true.
  - `96ae0ff853734df0b10a827307949c87`: indices `[905, 613, 813]`, best lifts about `0.43 m`, `0.18 m`, and another successful lifted sample.
- Accepted cache: `/results/assets/verified_grasp_indices/franka_multi_verified_cache_1d_96ae_2977a39_20260614T1355Z/verified_indices_accepted.json`.

Validation:
- Local syntax: `python3 -m py_compile ... collect_franka_multi_object_verified_grasps.py`, `bash -n` on train/video/collector wrappers.
- L40 collector exercised the environment headlessly with stable poses, yaw randomization, XY randomization, warmstart close/lift, and wrote per-index lift/success stats. The accepted cache has nonempty verified indices for both loaded objects.

Command / Job:
- A100 host: `a1001`
- job_id: `29067700`
- run: `franka_multi_state_teacher_cache_1d96_warm_resume25_20260614T1411Z`
- code_commit: `2977a39d4b32cf3eefb5070fbd310aa72816d207`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_pg03_c035_ap8_20260614T1218Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_937.9583.pth`
- manifest: `/results/assets/filtered_manifests/two_liftable_1d_96ae_20260614T1353Z/manifest.json`
- verified_cache: `/results/assets/verified_grasp_indices/franka_multi_verified_cache_1d_96ae_2977a39_20260614T1355Z/verified_indices_accepted.json`
- reset: `OBJECT_ASSET_ASSIGNMENT=random`, stable pose cache enabled, yaw randomization `180 deg`, XY randomization `0.10 m`, center `(0.05, 0.0)`, grasp center gate `0.50`, candidate count `16` sampled from verified cache.
- warmstart/action prior: enabled, approach/close/lift `4/40/180`, close width `0.004`, prior close width disabled, lift action z `0.50`, action-prior reward weight `20.0`, sharpness `1.0`.

Result:
- status: running
- startup: all 8 ranks restored runtime state at epoch 25; rank-0 metrics file is active; epoch-30 checkpoint was written.
- early metrics: by epoch 35, `cube_success_rate ~= 0.0063`, `cube_has_lifted_rate ~= 0.059`, `cube_action_warmstart_lift_success_rate ~= 0.025`, `cube_action_warmstart_lift_has_lifted_rate ~= 0.068`, `cube_grasp_prior_quality_success_rate ~= 0.667`.

Analysis:
- The verified cache removed the total flatline from the previous run and gives real lifted/success states during warmstart, but the lift rate is still low relative to the standalone collector. Continue monitoring trend before deciding whether to tune reset IK/yaw, increase cache diversity, or alter warmstart gating.

Next:
- Monitor through the next checkpoint window. If success/lift rise, keep training; if they stagnate or fall, stop and patch/tune with evidence from the metric trend.

## 2026-06-14T14:30:00Z - Verified-cache PPO stopped after weak warmstart lift

Goal:
- Decide whether the verified-cache A100 run is learning enough to continue.

Result:
- status: canceled for poor learning signal after preserving metrics and checkpoints
- job_id: `29067700`
- run: `franka_multi_state_teacher_cache_1d96_warm_resume25_20260614T1411Z`
- final checkpoint observed before cancel: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_cache_1d96_warm_resume25_20260614T1411Z/nn/last_dextrah_franka_multi_object_grasp_ep_50_rew_2241.0818.pth`
- evidence: rank-0 rows through epoch 50 had last-10 average `cube_success_rate ~= 0.00093`, `cube_has_lifted_rate ~= 0.0508`, `cube_lift_height ~= 0.00146 m`, `cube_grasp_prior_quality_success_rate ~= 0.679`, `cube_action_warmstart_lift_has_lifted_rate ~= 0.065`, and `cube_action_warmstart_lift_success_rate ~= 0.0026`.
- diagnostic detail: reset quality was around `70%`, but warmstart lift-phase finger-center distance was commonly `0.2-0.3 m` and lift success was near zero, so most cached reset samples still did not produce usable demonstrations under full randomized training resets.

Analysis:
- The policy observation is object-pose conditioned through inherited Franka cube terms (`cube_pos`, `cube_quat`, velocities, finger-to-object offsets, goal deltas) plus multi-object size/identity/grasp-prior features, so this does not look like an unconditioned-policy failure.
- The accepted verified cache is too sparse and single-pass: it contains only one index for object `1d489...` and three for `96ae...`, and those indices only occasionally lift across randomized pose/yaw/IK realizations.
- Continuing this run to epoch 600 would mostly train on non-lifting warmstart episodes and bad post-warmstart exploration.

Next:
- Relaunch with a tighter first-stage curriculum that keeps the user-required multi-object parallel sampling and full yaw randomization, but reduces XY spawn randomization and increases reset retries/candidate reuse so warmstart can generate many lifted demonstrations. If that still stalls, collect a larger robust verified cache or move to a staged XY curriculum before restoring the full `+-10 cm` pose range.

## 2026-06-14T14:25:21Z - Prior-width robust verified-cache collector

Goal:
- Test whether closing to the GraspGen prior width, instead of forcing every object to a `0.004 m` gripper width, produces a more robust lift-verified cache under the full training pose randomization.

Hypothesis:
- The previous cache entries can lift occasionally, but the training warmstart often loses contact because arbitrary objects are squeezed to a cube-like near-closed width. Using the prior grasp width with a small margin should reduce object ejection/slip and increase repeatable lift success.

Command / Job:
- host: `l401`
- job_id: `1029301`
- run: `franka_multi_verified_priorwidth_fullxy_2977a39_20260614T142521Z`
- code_commit: `2977a39d4b32cf3eefb5070fbd310aa72816d207`
- manifest: `/results/assets/filtered_manifests/two_liftable_1d_96ae_20260614T1353Z/manifest.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029301.out`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_priorwidth_fullxy_2977a39_20260614T142521Z/verified_indices.json`
- reset: full yaw randomization (`180 deg`), XY randomization `0.10 m`, stable-pose cache, center `(0.05, 0.0)`, reset attempts `8`, candidate count `4096`, center gate `0.50`, IK iterations `128`.
- warmstart: approach/close/lift `4/60/180`, `GRASP_WARMSTART_CLOSE_WIDTH=0.08`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=True`, prior margin `0.003`, min width `0.002`, lift action z `0.50`.
- collector thresholds: `TARGET_PER_OBJECT=6`, `MIN_CYCLES=12`, `CYCLES=80`, `MIN_LIFT_HEIGHT=0.10`, `REQUIRE_SUCCESS=True`, `MAX_DONE_COUNT=0`.

Next:
- Monitor first cycle counts and final JSON. If counts improve without manual acceptance, use this cache for the next A100 PPO run; if not, switch to an easier first-stage XY curriculum or search a broader object subset for robust indices.

Result:
- status: stopped after answering the close-width hypothesis for `1d489...`
- job_id: `1029301`
- evidence: after 12 cycles, `1d489db9cdc24161a7537926a20bb17b` had `0` passing samples after `384` observed resets and `347` quality resets, while `96ae0ff853734df0b10a827307949c87` had `5` pass observations on indices `[905, 613]`.
- decision: prior-width closing helps `96ae...` but makes `1d489...` unusable for this training pair. Do not use `1d489...` for the next PPO run.

Next:
- Test the remaining converted object `7195...` with `96ae...`, because the current `/lustre` debug USD set has only four converted objects and `30700...` was already diagnosed as low-quality/no-lift.

## 2026-06-14T14:29:42Z - Robust pair collector for 7195+96ae

Goal:
- Find a two-object training pair whose grasp-prior warmstart produces repeated successful lifts under the full training pose randomization.

Change:
- Wrote filtered manifest `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/two_liftable_7195_96ae_20260614T1432Z/manifest.json` for objects:
  - `7195ed3346a445448308febe833c180a`
  - `96ae0ff853734df0b10a827307949c87`

Command / Job:
- host: `l401`
- job_id: `1029302`
- run: `franka_multi_verified_7195_96ae_priorwidth_2977a39_20260614T142942Z`
- code_commit: `2977a39d4b32cf3eefb5070fbd310aa72816d207`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029302.out`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_7195_96ae_priorwidth_2977a39_20260614T142942Z/verified_indices.json`
- accepted_cache: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_7195_96ae_priorwidth_2977a39_20260614T142942Z/verified_indices_accepted.json`
- settings: full yaw randomization, `OBJECT_SPAWN_XY_RANDOMIZATION=0.10`, stable-pose cache, `GRASP_WARMSTART_CLOSE_WIDTH=0.08`, `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=True`, reset attempts `8`, candidate count `4096`, center gate `0.50`.

Result:
- status: accepted for first PPO launch
- `7195ed3346a445448308febe833c180a`: accepted index `[354]`, `33` pass observations, `277` quality resets, `448` observed resets, best lift about `0.395 m`, success true.
- `96ae0ff853734df0b10a827307949c87`: accepted index `[905]`, `7` pass observations, `302` quality resets, `448` observed resets, best lift about `0.244 m`, success true.

Analysis:
- This pair produces repeated lift-success passes for both objects under the full yaw and `+-10 cm` XY training distribution, unlike the `1d489... + 96ae...` pair.
- The accepted cache intentionally overrides the collector's unique-index target because repeated success on one robust index per object is a better first PPO signal than many one-off geometric candidates.

Next:
- Launch A100 PPO on the `7195... + 96ae...` pair with the accepted cache, prior-width closing, full yaw, random object assignment, and full `+-10 cm` object pose randomization. Start from a clean policy initialization so the failed `1d489...` run does not carry optimizer/normalization state into the stronger pair.

## 2026-06-14T14:38:29Z - A100 PPO launch on robust 7195+96ae pair

Goal:
- Train the first multi-object Franka grasp teacher policy on a two-object pair whose grasp-prior warmstart has repeated lift-success passes under full training randomization.

Version Control:
- local main worklog commit: `471a556` (`Record multi-object grasp PPO relaunch diagnostics`)
- training source commit: `2977a39d4b32cf3eefb5070fbd310aa72816d207`
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-verifycache-20260614-2977a39`
- note: A100 login could not fetch GitHub over SSH (`Permission denied (publickey)`), but the only newer commit is worklog-only; training source code is unchanged from `2977a39`.

Command / Job:
- host: `a1001`
- job_id: `29069517`
- run: `franka_multi_state_teacher_7195_96ae_priorwidth_scratch_2977a39_20260614T143829Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29069517.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_priorwidth_scratch_2977a39_20260614T143829Z`
- manifest: `/results/assets/filtered_manifests/two_liftable_7195_96ae_20260614T1432Z/manifest.json`
- verified_cache: `/results/assets/verified_grasp_indices/franka_multi_verified_7195_96ae_priorwidth_2977a39_20260614T142942Z/verified_indices_accepted.json`
- scale: `NUM_ENVS=2048`, 8 GPUs, `MAX_ITERATIONS=300`, `HORIZON_LENGTH=64`, `SAVE_FREQUENCY=10`, `SEED=47`.
- randomization: `OBJECT_ASSET_ASSIGNMENT=random`, full yaw randomization (`180 deg`), XY randomization `0.10 m`, center `(0.05, 0.0)`.
- reset/warmstart: stable-pose cache, reset attempts `4`, verified candidate count `64`, center gate `0.50`, IK `128/0.035/0.25/0.055/0.55`, warmstart approach/close/lift `4/60/180`, prior-width close enabled with width cap `0.08`, min width `0.002`, lift action z `0.50`.
- action prior/rewards: action-prior reward enabled (`20.0`, sharpness `1.0`), lift `60.0`, height `15.0`, success `80.0`, close action `2.0`, lift action `10.0`, descend penalty `-8.0`, action penalty `-0.0002`.

Next:
- Monitor startup for config/load errors. First metric gate: reset quality should be high enough to keep warmstart active, and `cube_action_warmstart_lift_has_lifted_rate` / `cube_action_warmstart_lift_success_rate` should be materially higher than the failed `1d489...` run.

Result:
- status: canceled for curriculum tuning after epoch-30 checkpoint
- job_state: `CANCELLED by 158351`; `.batch` recorded signal exit `15:0`, expected after manual cancellation.
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_priorwidth_scratch_2977a39_20260614T143829Z/nn/last_dextrah_franka_multi_object_grasp_ep_30_rew_3406.4106.pth`
- metrics through epoch 29: last-10 average `cube_success_rate ~= 0.0104`, `cube_has_lifted_rate ~= 0.1608`, `cube_lift_height ~= 0.0057 m`, `cube_grasp_prior_quality_success_rate ~= 0.5335`, `cube_action_warmstart_lift_has_lifted_rate ~= 0.3894`, `cube_action_warmstart_lift_success_rate ~= 0.0511`, and `cube_action_prior_delta_abs ~= 0.6682`.

Analysis:
- The robust pair environment is behaving materially better than the previous `1d489... + 96ae...` attempt: reset quality is stable and warmstart lift phases produce real lifted/success cases.
- The learned policy has not yet absorbed the scripted action prior: `cube_action_prior_delta_abs` remains near `0.67` and strict success is still around one percent. This points to a curriculum/reward-strength issue rather than another asset/reset bug.

Next:
- Resume from the epoch-30 checkpoint with the same validated environment, same random object assignment, same full yaw and `+-10 cm` XY randomization, and a stronger action-prior reward. Keep code at `2977a39`; this is a launch-only hyperparameter change.

## 2026-06-14T15:11:33Z - Stronger action-prior resume from robust-pair epoch 30

Goal:
- Make the policy imitate the working grasp-prior reference actions strongly enough that post-warmstart PPO can improve strict multi-object pickup success.

Hypothesis:
- The previous run's environment signal is adequate, but the action-prior reward is too weak relative to PPO noise and task reward. Increasing the action-prior reward weight should reduce `cube_action_prior_delta_abs` and improve policy lift/success while preserving the validated object/reset distribution.

Change:
- Launch-only change: increase `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT` from `20.0` to `100.0`.
- Keep `GRASP_PRIOR_ACTION_PRIOR_REWARD_SHARPNESS=1.0`, prior-width closing, stable-pose cache, verified indices, full yaw randomization, random object assignment, and full `+-10 cm` XY randomization unchanged.

Version Control:
- local main worklog commit before this entry: `471a5562b714ea1427f8e8a84be7c0c3d11e4d0c`
- training source commit: `2977a39d4b32cf3eefb5070fbd310aa72816d207`
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-main-verifycache-20260614-2977a39`
- push/pull: not needed for code because the only newer local changes are worklog entries and the A100 checkout could not fetch GitHub over SSH earlier.

Command / Job:
- command: `sbatch --export=ALL,... cluster/sbatch_train_teacher_8gpu.sh`
- host: `a1001`
- job_id: `29070006`
- run: `franka_multi_state_teacher_7195_96ae_ap100_resume30_2977a39_20260614T1511Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29070006.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_ap100_resume30_2977a39_20260614T1511Z`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_priorwidth_scratch_2977a39_20260614T143829Z/nn/last_dextrah_franka_multi_object_grasp_ep_30_rew_3406.4106.pth`

Next:
- Submit the resume job, inspect startup/checkpoint restore, then monitor whether `cube_action_prior_delta_abs` drops and strict success/lift improve over the next checkpoint window.

Result:
- status: canceled for poor learning signal after epoch-40 checkpoint
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_ap100_resume30_2977a39_20260614T1511Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4292.6763.pth`
- startup: all ranks restored the epoch-30 runtime state and loaded the checkpoint; rank-0 JSONL metrics were written normally.
- metrics through epoch 40: last-10 average `cube_success_rate ~= 0.0142`, `cube_has_lifted_rate ~= 0.1442`, `cube_lift_height ~= 0.0066 m`, `cube_grasp_prior_quality_success_rate ~= 0.526`, `cube_action_warmstart_lift_has_lifted_rate ~= 0.263`, `cube_action_warmstart_lift_success_rate ~= 0.034`, and `cube_action_prior_delta_abs ~= 0.674`.
- trend: first resumed epoch spiked to `cube_success_rate ~= 0.042`, but later epochs fell back under one percent except reset-phase spikes. Increasing the prior reward weight from `20.0` to `100.0` increased `cube_action_prior_reward` but did not reduce sampled action delta.

Analysis:
- Reward scaling alone is not enough. The policy keeps closing the gripper harder (`cube_policy_gripper_action` around `-0.7`) but does not reliably match the reference trajectory or lift.
- PPO uses a fixed-sigma continuous actor (`SIGMA_INIT_VAL=0` in the training config), so logged sampled actions may stay noisy even if means improve. Before another PPO relaunch, inspect deterministic policy behavior and add a direct supervised/reference-action intervention for this multi-object grasp-prior task.

Next:
- Patch evaluation/BC tooling so the multi-object grasp env can expose or consume its grasp-prior reference actions, then run a deterministic policy eval and/or supervised action imitation stage before the next PPO resume.

## 2026-06-14T15:32:50Z - Multi-object grasp-prior diagnostic hooks

Goal:
- Add a reproducible way to evaluate the deterministic policy and the scripted grasp-prior reference action sequence on the same multi-object reset distribution used for training.

Hypothesis:
- The `ap100` PPO resume may look poor because sampled actions include fixed-sigma exploration, so the next decision should compare deterministic policy behavior against the grasp-prior reference-action upper bound before another PPO relaunch.

Change:
- Added `compute_grasp_prior_reference_actions()` to the Franka cube grasp env base class so the multi-object env can expose the current scripted grasp-prior action target without changing dynamics.
- Updated `eval_rollout.py` and `bc_reference_action_imitation.py` to use `compute_grasp_prior_reference_actions()` when a task does not have trajectory `compute_reference_delta_actions()`.
- Updated `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` to accept `ACTION_SOURCE` and `GRASP_PRIOR_VERIFIED_INDICES_PATH`, and to allow manifest-provided per-object prior paths without requiring `GRASP_PRIOR_LIBRARY_DIR`.

Version Control:
- agent_id: merge-dp-rgb-main-20260613
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `471a5562b714ea1427f8e8a84be7c0c3d11e4d0c`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/bc_reference_action_imitation.py`, `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/bc_reference_action_imitation.py`
- `bash -n cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`

Next:
- Commit and deploy this exact diagnostic commit to an isolated A100/L40 source worktree, then run deterministic policy eval and scripted reference-action eval against the robust `7195... + 96ae...` pair and the accepted verified-index cache.

## 2026-06-14T15:35:44Z - Match eval reference-action schedule to PPO training

Goal:
- Make the scripted grasp-prior reference eval use the same approach/close/lift action schedule as the PPO training runs.

Change:
- Added grasp-prior action-warmstart sequence overrides to `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` so launch env can pass `4/60/180`, prior-width close, and lift z `0.50`.

Version Control:
- base_commit: `864f867834966b39f22b5d2fc3d14fe90517fb7e`
- implementation_commit: pending
- changed_files: `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, this worklog.

Validation:
- `bash -n cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`

Next:
- Commit, deploy the final eval-diagnostic commit, and launch deterministic policy vs scripted reference evals.

## 2026-06-14T15:38:00Z - Deterministic policy vs scripted prior eval launch

Goal:
- Decide whether the epoch-40 policy mean learned useful grasp behavior, and establish the scripted grasp-prior reference rollout upper bound under the exact robust two-object randomization.

Hypothesis:
- If deterministic policy success is much higher than stochastic training metrics, the next PPO iteration should reduce exploration/noise or evaluate with means. If deterministic policy is still poor while scripted reference succeeds, the next step should be supervised action imitation / BC warm-start before PPO.

Version Control:
- local_commit: `5a5cfcab77588ddf7bab531d4083540768f02dc0`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-evaldiag-20260614-5a5cfca`
- deploy_method: Git bundle because A100 GitHub SSH fetch fails with `Permission denied (publickey)`.
- remote_status: detached `5a5cfcab77588ddf7bab531d4083540768f02dc0`, wrapper `bash -n` clean.

Command / Job:
- host: `l401`
- policy_job_id: `1029318`
- reference_job_id: `1029319`
- wrapper: `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_ap100_resume30_2977a39_20260614T1511Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4292.6763.pth`
- policy_run: `franka_multi_7195_96ae_policy_det_ep40_5a5cfca_20260614T1538Z`
- reference_run: `franka_multi_7195_96ae_refprior_5a5cfca_20260614T1538Z`
- distribution: manifest `/results/assets/filtered_manifests/two_liftable_7195_96ae_20260614T1432Z/manifest.json`, verified cache `/results/assets/verified_grasp_indices/franka_multi_verified_7195_96ae_priorwidth_2977a39_20260614T142942Z/verified_indices_accepted.json`, `OBJECT_ASSET_ASSIGNMENT=random`, `+-180 deg` yaw, `+-0.10 m` xy around `(0.05, 0.0)`.
- reset/reference: stable-pose cache enabled; reset attempts `4`, candidates `64`, center gate `0.50`; IK `128/0.035/0.25/0.055/0.55`; reference schedule `4/60/180`, prior-width close, min close width `0.002`, lift z action `0.50`.

Next:
- Monitor `1029318` and `1029319`, inspect logs and `/results/evals/*/metrics.json`, then decide BC vs PPO relaunch.

Result:
- status: completed
- policy job `1029318`: completed cleanly on `pool0-00009`, metrics at `/results/evals/franka_multi_7195_96ae_policy_det_ep40_5a5cfca_20260614T1538Z/metrics.json`.
- reference job `1029319`: completed cleanly on `pool0-00002`, metrics at `/results/evals/franka_multi_7195_96ae_refprior_5a5cfca_20260614T1538Z/metrics.json`.
- deterministic policy summary: first-attempt success `0.1172`, first-attempt success-hold `0.0508`, terminal success `0.0195`, success-ever `0.1719`, final per-step success occupancy `0.0`, max lift-height trace mean `0.4049`, has-lifted trace max `0.2305`.
- scripted reference summary: first-attempt success `0.0938`, first-attempt success-hold `0.0625`, terminal success `0.0664`, success-ever `0.1367`, final per-step success occupancy `0.0039`, max lift-height trace mean `0.4235`, has-lifted trace max `0.1914`.
- reset quality during eval remained partial: policy trace reset quality mean `0.5949`, reference trace reset quality mean `0.5385`; failed grasp-prior resets continue to dilute rollout success.

Analysis:
- The deterministic policy mean is materially better than the stochastic PPO metrics, so the fixed-sigma exploration noise is a training bottleneck.
- The scripted reference under full training randomization is not a high-success oracle; it lifts some objects but does not hold them reliably. PPO should keep task reward active and not overfit purely to the reference.
- The checkpoint stores `a2c_network.sigma` around `-0.11` log-std (`~0.9` action std), which is too noisy for the narrow grasp state reached by reset.

Next:
- Create a low-sigma copy of the epoch-40 checkpoint with `a2c_network.sigma=-2.0`, then resume PPO from that checkpoint with the same robust object distribution, lower action-prior reward than `ap100`, and frequent checkpoints.

## 2026-06-14T15:45:00Z - Low-sigma checkpoint for PPO resume

Goal:
- Preserve the useful epoch-40 deterministic policy mean while reducing rollout action noise enough for PPO to improve grasp/hold behavior.

Change:
- Created `/results/checkpoints/dextrah_franka_multi_object_grasp/franka_multi_7195_96ae_ep40_sigma_m2_20260614T1545Z.pth` from the epoch-40 checkpoint by setting `model/a2c_network.sigma` to `-2.0` for all 7 action dimensions.

Version Control:
- source_commit: `5a5cfcab77588ddf7bab531d4083540768f02dc0`
- source_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-evaldiag-20260614-5a5cfca`
- checkpoint_edit_job: `1029324` on `l401`

Validation:
- checkpoint edit log: before sigma min/max/mean `-0.2219/-0.0535/-0.1089`; after `-2.0/-2.0/-2.0`.
- output checkpoint exists on `/lustre`, size `146M`.

Next:
- Launch A100 8-GPU PPO resume from the low-sigma checkpoint and monitor whether stochastic training success approaches or exceeds the deterministic eval baseline.

## 2026-06-14T15:48:00Z - Low-sigma PPO resume launch

Goal:
- Resume PPO from the useful epoch-40 policy mean with much lower fixed action noise, and improve stochastic training/eval success on the robust two-object task.

Hypothesis:
- Lowering fixed sigma from checkpoint log-std `~ -0.11` to `-2.0` should reduce destructive rollout noise. With task reward active and action-prior reward reduced from `100` back to `20`, PPO should improve holding success beyond the `~11.7%` deterministic first-attempt baseline instead of overfitting to the imperfect scripted reference.

Change:
- Resume checkpoint: `/results/checkpoints/dextrah_franka_multi_object_grasp/franka_multi_7195_96ae_ep40_sigma_m2_20260614T1545Z.pth`.
- Training hyperparameters: `LEARNING_RATE=1e-4`, central value LR `5e-5`, `ENTROPY_COEF=0`, `KL_THRESHOLD=0.008`, save every `10`, max iterations `160`.
- Environment unchanged from robust eval/training distribution: two objects `7195...` and `96ae...`, random assignment, full yaw, `+-0.10 m` XY around `(0.05, 0.0)`, stable-pose cache, verified indices, reset attempts `4`, candidates `64`.
- Warmstart/action prior: `4/60/180`, prior-width close, min close width `0.002`, lift z `0.50`, action-prior reward `20.0`.

Version Control:
- source_commit: `5a5cfcab77588ddf7bab531d4083540768f02dc0`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-evaldiag-20260614-5a5cfca`

Command / Job:
- host: `a1001`
- job_id: `29070307`
- run: `franka_multi_state_teacher_7195_96ae_lowsigma_m2_resume40_5a5cfca_20260614T1548Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29070307.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_lowsigma_m2_resume40_5a5cfca_20260614T1548Z`

Result:
- status: pending at launch
- scheduler_reason: `QOSMaxJobsPerUserLimit`, because an unrelated A100 `Dextrah-Franka-Star-Kitting` teacher job is running under the user.

Next:
- Monitor until `29070307` starts; inspect startup restore, sigma value if logged/observable, JSONL metrics, checkpoints, and compare stochastic success/lift against prior runs.

## 2026-06-14T16:05:16Z - Low-sigma PPO epoch-50 checkpoint and eval launch

Goal:
- Decide whether the low-sigma PPO resume is actually improving the robust two-object policy, rather than only reducing sampled action noise.

Result:
- status: canceled after preserving checkpoint for eval
- scheduler: `29070307` started on `a1001`/`batch-block7-03012`, restored epoch 40, reached epoch 50, and was intentionally canceled after the epoch-50 checkpoint was saved.
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_lowsigma_m2_resume40_5a5cfca_20260614T1548Z/nn/last_dextrah_franka_multi_object_grasp_ep_50_rew_2608.1572.pth`
- training metrics: epoch 41-50 last-10 `cube_success_rate ~= 0.0164`, `cube_has_lifted_rate ~= 0.1572`, `cube_lift_height ~= 0.0094 m`, `cube_grasp_prior_quality_success_rate ~= 0.563`, `cube_action_warmstart_lift_has_lifted_rate ~= 0.272`, `cube_action_warmstart_lift_success_rate ~= 0.0359`, and `cube_action_prior_delta_abs ~= 0.407`.
- interpretation: lower sigma improved action tracking compared with the previous `~0.67` delta, but PPO-side success remained below the earlier deterministic epoch-40 eval baseline and the sampled policy still did not become a reliable grasp/lift controller.

Command / Job:
- deterministic eval job: `1029330`, run `franka_multi_7195_96ae_policy_det_ep50_lowsigma_5a5cfca_20260614T1603Z`
- stochastic eval job: `1029331`, run `franka_multi_7195_96ae_policy_stoch_ep50_lowsigma_5a5cfca_20260614T1603Z`
- host: `l401`, wrapper `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- eval config: `NUM_ENVS=256`, `NUM_STEPS=600`, `SEED=53`, `CAPTURE_VIDEO=False`, two-object robust manifest, stable-pose cache, verified grasp indices, random object assignment, `+-180 deg` yaw, `+-0.10 m` XY around `(0.05, 0.0)`, reset attempts `4`, candidates `64`, and reference schedule `4/60/180`.

Next:
- Inspect eval metrics for both deterministic and stochastic epoch-50 rollouts. If epoch-50 does not beat the epoch-40 deterministic baseline, launch a multi-object BC/reference-action imitation intervention before resuming PPO again.

## 2026-06-14T16:05:16Z - Multi-object BC wrapper fallback

Goal:
- Make the existing reference-action imitation wrapper capable of collecting and training on the multi-object grasp-prior task with the same object/reset distribution used by PPO.

Change:
- Updated `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to forward multi-object object manifest, object assignment, spawn center/randomization/yaw, stable-pose cache, grasp-prior reset, verified grasp index cache, IK reset settings, pregrasp offset, and the grasp-prior reference action schedule to `bc_reference_action_imitation.py`.
- Kept the existing cube trajectory path intact and avoided cube-only Hydra overrides for `Dextrah-Franka-Multi-Object-Grasp`.

Validation:
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

Next:
- Commit this wrapper fallback and deploy it via Git bundle if epoch-50 eval is poor and a BC warm-start launch is needed.

## 2026-06-14T16:09:54Z - Epoch-50 eval decision and BC fallback launch plan

Goal:
- Recover a stronger warm-start policy for the robust two-object multi-object grasp task after the low-sigma PPO resume failed to improve policy success.

Hypothesis:
- The epoch-50 low-sigma PPO checkpoint still tracks the grasp-prior reference poorly enough to miss contact/hold reliably. A bounded supervised pass on the same randomized multi-object distribution should reduce reference-action error and provide a better checkpoint for subsequent eval and PPO resume.

Result:
- deterministic epoch-50 eval `1029330`: completed 600 steps, `success_rate_final=0.00390625`, `success_rate_max=0.0703125`, `success_ever_rate=0.15234375`, `first_attempt_success_rate=0.11328125`, `first_attempt_success_hold_rate=0.05859375`.
- stochastic epoch-50 eval `1029331`: completed 600 steps, `success_rate_final=0.00390625`, `success_rate_max=0.06640625`, `success_ever_rate=0.1484375`, `first_attempt_success_rate=0.11328125`, `first_attempt_success_hold_rate=0.0390625`.
- decision: epoch-50 did not exceed the epoch-40 deterministic baseline and has low terminal occupancy, so continue with the BC warm-start intervention instead of spending more PPO time on this checkpoint.

Version Control:
- implementation_commit: `d5e8b273890e34501fbc01b7d1fa4c3e3423f268`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: detached clean at `d5e8b273890e34501fbc01b7d1fa4c3e3423f268`

Command / Job:
- host: `l401`
- job_id: `1029338`
- planned wrapper: `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- planned task: `Dextrah-Franka-Multi-Object-Grasp`
- planned checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_lowsigma_m2_resume40_5a5cfca_20260614T1548Z/nn/last_dextrah_franka_multi_object_grasp_ep_50_rew_2608.1572.pth`
- run_name: `franka_multi_7195_96ae_bc_ref_ep50_d5e8b27_20260614T1612Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029338.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_7195_96ae_bc_ref_ep50_d5e8b27_20260614T1612Z`
- planned data distribution: two-object manifest `7195.../96ae...`, random object assignment, `+-180 deg` yaw, `+-0.10 m` XY around `(0.05, 0.0)`, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`.
- planned BC scale: `NUM_ENVS=256`, `COLLECTION_STEPS=600`, `TRAIN_STEPS=1600`, `BATCH_SIZE=8192`, `LEARNING_RATE=1e-4`, `COLLECTION_ACTION_SOURCE=reference_delta`.

Next:
- Submit the BC job, monitor collection/training curves, inspect `bc_metrics.json`, checkpoint loadability by eval, then relaunch deterministic/stochastic eval from the BC checkpoint. If eval improves, resume PPO from that checkpoint; if not, inspect per-source/action residual metrics and patch/tune the data or model path.

## 2026-06-14T16:22:00Z - BC reference-action result and DAgger-style follow-up

Goal:
- Decide whether the first BC checkpoint is a strong enough warm start for PPO, and if not, correct the data distribution before spending A100 time.

Result:
- BC job `1029338` completed on `l401`/`pool0-00004` in `00:01:58`.
- run: `franka_multi_7195_96ae_bc_ref_ep50_d5e8b27_20260614T1612Z`
- checkpoint: `/results/bc/franka_multi_7195_96ae_bc_ref_ep50_d5e8b27_20260614T1612Z/nn/bc_reference_action_imitation.pth`
- dataset: `153600` samples from `256 envs x 600 steps`, obs dim `80`, action dim `7`.
- fit metrics: validation L2 improved from `1.5865` to selected `0.0446`; validation up abs `0.00568`; validation close abs `0.0176`.
- deterministic eval `1029339`: `success_rate_final=0.0`, `success_rate_max=0.0742`, `success_ever_rate=0.1680`, `first_attempt_success_rate=0.1094`, `first_attempt_success_hold_rate=0.0273`.
- stochastic eval `1029340`: `success_rate_final=0.0039`, `success_rate_max=0.0586`, `success_ever_rate=0.1719`, `first_attempt_success_rate=0.1133`, `first_attempt_success_hold_rate=0.0234`.
- trace diagnosis: deterministic mean success occupancy improved to `0.0178`, but mean policy up action during rollout was only `0.0219` and mean cube lift height was `0.0095 m`; the clean reference-only BC fit still has rollout distribution shift and weak sustained lift/hold.

Analysis:
- The supervised fit itself is valid and reloadable, but it did not beat the earlier first-attempt/hold eval baseline. The next cheapest correction is to collect off-policy states under a policy/reference mixture with terminal hold while rehearsing the clean reference dataset, then evaluate before launching A100 PPO.

Next:
- Initial second BC launch `1029343`, run `franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1623Z`, failed fast with exit `2` because `policy_reference_mix_hold` is diagnostic-gated unless `ALLOW_DIAGNOSTIC_ACTION_SOURCES=True`.
- Relaunched corrected second L40 BC pass `1029344`, run `franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z`, from the first BC checkpoint using `COLLECTION_ACTION_SOURCE=policy_reference_mix_hold`, `ALLOW_DIAGNOSTIC_ACTION_SOURCES=True`, teacher alphas `0.25/0.5/0.75`, balanced source batches, and the first reference dataset as rehearsal.
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029344.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z`
- If rollout eval improves lift/hold, resume A100 PPO from that checkpoint; otherwise inspect per-source residuals and adjust collection/labels.

## 2026-06-14T16:32:00Z - DAgger BC eval and PPO resume launch

Goal:
- Move from supervised warm-start correction back to actual PPO training on the randomized multi-object task.

Result:
- second BC job `1029344` completed cleanly in `00:03:28`.
- checkpoint: `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`
- dataset: `614400` samples: three `policy_reference_mix_hold` sources at alphas `0.25/0.5/0.75` plus the clean reference rehearsal source.
- selected validation L2: `0.2783`; per-source validation L2: alpha0.25 `0.3267`, alpha0.5 `0.3496`, alpha0.75 `0.3520`, rehearsal `0.0877`.
- deterministic eval `1029347`: `success_rate_final=0.0`, `success_rate_max=0.0703`, `success_ever_rate=0.1406`, `first_attempt_success_rate=0.1211`, `first_attempt_success_hold_rate=0.0391`, occupancy mean `0.0117`.
- stochastic eval `1029348`: `success_rate_final=0.0`, `success_rate_max=0.0820`, `success_ever_rate=0.1406`, `first_attempt_success_rate=0.1250`, `first_attempt_success_hold_rate=0.0352`, occupancy mean `0.0137`.

Analysis:
- DAgger-style BC improved first-attempt success slightly but still failed to sustain terminal occupancy, so supervised fitting is no longer the main path. The actor now has usable close/lift behavior for early attempts, and PPO should optimize sustained lift/success directly.

Command / Job:
- host: `a1001`
- job_id: `29070717`
- run: `franka_multi_state_teacher_7195_96ae_bc_dagger_ppo_lift_d5e8b27_20260614T1632Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29070717.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_bc_dagger_ppo_lift_d5e8b27_20260614T1632Z`
- source_commit: `d5e8b273890e34501fbc01b7d1fa4c3e3423f268`
- resume_checkpoint: `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`
- PPO settings: `NUM_ENVS=2048`, `MAX_ITERATIONS=100`, `LEARNING_RATE=5e-5`, central value LR `5e-5`, `KL_THRESHOLD=0.006`, `ENTROPY_COEF=0`, `SAVE_FREQUENCY=5`.
- task distribution: same two-object robust manifest, random object assignment, `+-180 deg` yaw, `+-0.10 m` XY around `(0.05, 0.0)`, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`.
- guidance/reward: no action warmstart override; grasp-prior action prior reward enabled with weight `8`; task reward lifted toward sustained lift/hold (`lift=25`, `height=8`, `success_bonus=60`, `close_action=2`, `lift_action=6`, descend penalty `-3`).

Next:
- Monitor `29070717` through queue/startup, inspect restored checkpoint behavior, JSONL metrics, success/lift/action-prior terms, checkpoints, then evaluate the best checkpoint. If the reward shaping destabilizes or fails to improve, tune the PPO reward/prior balance and relaunch.

## 2026-06-14T16:36:00Z - PPO resume startup/config check

Goal:
- Verify that the active A100 PPO resume is using the intended multi-object task distribution before waiting for training metrics.

Result:
- job `29070717` is running on `a1001` node `batch-block5-01579`.
- all eight ranks loaded `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`.
- resolved env config confirms random object assignment, object yaw randomization `+-180 deg`, spawn center offset `(0.05, 0.0)`, spawn XY randomization `0.10 m`, stable-pose cache enabled, verified grasp indices enabled, reset attempts `4`, reset candidate count `64`, robot base z `0.47`, and action warmstart override disabled.
- resolved PPO config confirms fixed low sigma init `-2.0`, LR `5e-5`, central value LR `5e-5`, KL threshold `0.006`, entropy coefficient `0`, horizon `64`, minibatch `32768`, save frequency `5`, and `max_epochs=100`.

Next:
- Continue monitoring until the first epochs/checkpoints appear, inspect training curves and reward terms, then run deterministic/stochastic eval on the strongest checkpoint.

## 2026-06-14T16:49:00Z - PPO branch 1 eval failure and post-lift reward patch

Goal:
- Decide whether the BC-warm-start PPO branch is learning a usable policy-only lift/hold behavior, and patch the training recipe if not.

Result:
- A100 job `29070717`, run `franka_multi_state_teacher_7195_96ae_bc_dagger_ppo_lift_d5e8b27_20260614T1632Z`, was monitored through epoch 70 and then canceled deliberately after preserving checkpoints.
- checkpoints preserved: epoch 55 reward `4938.438`, epoch 60 reward `1044.4028`, epoch 65 reward `3672.805`, epoch 70 reward `1771.5356`.
- training direct-info metrics showed repeating short spikes followed by decay; examples: epoch 60 `cube_success_rate=0.0278`, `cube_lift_height=0.0130 m`, `cube_action_z=-0.229`; epoch 65 `cube_success_rate=0.0083`, `cube_lift_height=0.0050 m`, `cube_action_z=-0.110`; epoch 69 `cube_success_rate=0.0376`, `cube_lift_height=0.0245 m`, `cube_action_z=-0.527`.
- deterministic L40 eval `1029349` from epoch 60: `success_rate_final=0.0039`, `success_rate_max=0.0781`, `success_ever_rate=0.1484`, `success_occupancy_mean=0.0144`, `first_attempt_success_rate=0.125`, `first_attempt_success_hold_rate=0.0586`.
- stochastic L40 eval `1029350` from epoch 60: `success_rate_final=0.0`, `success_rate_max=0.0664`, `success_ever_rate=0.1445`, `success_occupancy_mean=0.0190`, `first_attempt_success_rate=0.125`, `first_attempt_success_hold_rate=0.0625`.
- diagnosis: the policy can briefly contact/lift but tends to open or drive negative z after the grasp-prior schedule. Existing close/up action shaping is prelift-gated by `lift_ready_gate`, so after the object/fingers drift the policy receives little direct penalty for opening or descending while trying to hold.

Change:
- Added configurable post-lift action shaping in `franka_cube_grasp_rewards.py` and `franka_cube_grasp_env.py`, defaulting to zero effect unless enabled by config:
  - `cube_postlift_action_gate_height`
  - `cube_postlift_close_action_weight`
  - `cube_postlift_open_action_penalty_weight`
  - `cube_postlift_lift_action_weight`
  - `cube_postlift_descend_action_penalty_weight`
- Added A100 wrapper exports/logging/Hydra overrides for these weights in `cluster/sbatch_train_teacher_8gpu.sh`.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_rewards.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

Next:
- Commit and deploy the patch, then relaunch PPO from the DAgger BC checkpoint with post-lift close/up rewards and open/descend penalties enabled. Monitor the new post-lift reward terms plus policy z/close action, then evaluate the best checkpoint.

## 2026-06-14T16:52:00Z - PPO branch 2 post-lift shaping launch

Goal:
- Test whether explicit post-lift close/up rewards and open/descend penalties prevent the policy from losing the object after brief contact/lift.

Version Control:
- local_commit: `91063df57ef3d018fc29d44357088cb7bd3f6eb4`
- pushed: `main` updated on origin from `d5e8b27` to `91063df`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_deploy: GitHub fetch on `a1001` failed due `Permission denied (publickey)`, so commit `91063df` was deployed via a Git bundle and checked out detached in the remote worktree.
- remote_status: detached at `91063df57ef3d018fc29d44357088cb7bd3f6eb4`; `bash -n cluster/sbatch_train_teacher_8gpu.sh` passed remotely.

Command / Job:
- host: `a1001`
- job_id: `29071021`
- run: `franka_multi_state_teacher_7195_96ae_postlift_ppo_d5e8b27_91063df_20260614T1649Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071021.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_postlift_ppo_d5e8b27_91063df_20260614T1649Z`
- checkpoint: `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`
- PPO: `NUM_ENVS=2048`, `MAX_ITERATIONS=90`, seed `71`, LR `2e-5`, central value LR `3e-5`, KL `0.004`, entropy `0`, save frequency `5`, sigma init `-2`.
- object/reset distribution: two-object robust manifest, random object assignment, `+-180 deg` yaw, `+-0.10 m` XY around `(0.05, 0.0)`, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`.
- reward/guidance: no scripted action override; action-prior reward weight `6`; base rewards `lift=35`, `height=10`, `success_bonus=80`, `close_action=3`, `lift_action=8`, `descend_penalty=-8`; post-lift gate height `0.03`, post-lift `close=3`, `open_penalty=-5`, `lift=4`, `descend_penalty=-8`.

Next:
- Monitor startup/config, then inspect `cube_postlift_*`, `cube_action_z`, `cube_gripper_close_action`, lift/success, and checkpoint evals. If post-lift terms improve training metrics, launch deterministic/stochastic L40 eval at the first strong checkpoint.

## 2026-06-14T16:55:00Z - PPO branch 2 JSONL relaunch

Goal:
- Preserve the post-lift PPO experiment but relaunch early with per-term JSONL metrics enabled, because reward/action diagnostics are required for debugging.

Change:
- Canceled startup-only A100 job `29071021` before PPO epochs; it had launched with `DEXTRAH_RLGAMES_JSONL_METRICS=False`.
- Relaunched the same code/config/checkpoint with `DEXTRAH_RLGAMES_JSONL_METRICS=True`.

Version Control:
- local_commit: `91063df57ef3d018fc29d44357088cb7bd3f6eb4`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: detached at `91063df57ef3d018fc29d44357088cb7bd3f6eb4`

Command / Job:
- host: `a1001`
- canceled_job_id: `29071021`
- new_job_id: `29071091`
- new_run: `franka_multi_state_teacher_7195_96ae_postlift_jsonl_91063df_20260614T1655Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071091.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_postlift_jsonl_91063df_20260614T1655Z`
- changed launch setting: `DEXTRAH_RLGAMES_JSONL_METRICS=True`; all task/object/reward/checkpoint settings otherwise matched job `29071021`.

Result:
- status: pending at launch due `QOSMaxJobsPerUserLimit`.

Next:
- Monitor queue/startup, verify the log shows `DEXTRAH_RLGAMES_JSONL_METRICS=True`, then inspect JSONL metrics once PPO epochs begin.

## 2026-06-14T17:07:00Z - Post-lift PPO early stop and epoch-60 eval launch

Goal:
- Decide whether the post-lift action shaping branch should continue to epoch 90 or be stopped for a better training recipe.

Result:
- A100 job `29071091` reached PPO epoch 61 and was canceled deliberately after checkpointing epoch 60.
- The branch reproduced the previous failure mode instead of fixing it. Rank-0 JSONL showed decaying lift/hold metrics:
  - epoch 52: `cube_success_rate=0.0215`, `cube_lift_height=0.0107 m`, `cube_action_z=-0.0473`, `cube_gripper_close_action=0.418`
  - epoch 55: `cube_success_rate=0.0103`, `cube_lift_height=0.00676 m`, `cube_action_z=-0.0878`, `cube_gripper_close_action=0.262`
  - epoch 59: `cube_success_rate=0.00293`, `cube_lift_height=0.00443 m`, `cube_action_z=-0.0972`, `cube_gripper_close_action=0.218`
  - epoch 60 spike: `cube_success_rate=0.0259`, `cube_lift_height=0.0132 m`, but `cube_action_z=-0.201` and `cube_postlift_descend_action_penalty=-1.108`
  - epoch 61: `cube_success_rate=0.0254`, `cube_lift_height=0.0102 m`, `cube_action_z=-0.0786`
- Diagnosis: the extra post-lift reward terms are active, but PPO still learns or preserves a negative vertical action and decaying gripper close action; this is not a successful sustained-hold policy.
- Preserved checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_postlift_jsonl_91063df_20260614T1655Z/nn/last_dextrah_franka_multi_object_grasp_ep_60_rew_815.34076.pth`
- Slurm cancellation note: the wrapper requeued once on signal, so the requeued step was explicitly canceled; `squeue` no longer listed job `29071091`.

Command / Job:
- deterministic eval: L40 job `1029351`, run `franka_multi_7195_96ae_postlift_ep60_91063df_det_20260614T1707Z`
- stochastic eval: L40 job `1029352`, run `franka_multi_7195_96ae_postlift_ep60_91063df_stoch_20260614T1707Z`
- eval distribution: `NUM_ENVS=256`, `NUM_STEPS=600`, policy action source, same two-object manifest, random object assignment, full yaw, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`, pregrasp offset `0.03`.

Next:
- Monitor both eval jobs, inspect `metrics.json` and traces, then relaunch PPO with a stronger sustained-hold intervention if epoch-60 eval does not beat the prior best.

## 2026-06-14T17:14:00Z - Hold-curriculum PPO launch

Goal:
- Train sustained lift/hold behavior after BC provides an initial grasp attempt, instead of continuing reward-only PPO that opens the gripper and commands downward z.

Evidence From Eval:
- Epoch-60 post-lift PPO evals completed:
  - deterministic `1029351`: `success_rate_final=0.0`, `success_rate_max=0.0703`, `success_ever_rate=0.1445`, success occupancy mean `0.0118`
  - stochastic `1029352`: `success_rate_final=0.0`, `success_rate_max=0.0742`, `success_ever_rate=0.1406`, success occupancy mean `0.0152`
- Trace diagnosis:
  - deterministic policy action z mean/final: `-0.099/-0.508`, gripper action mean/final: `-0.188/+0.462`, final gripper width `0.0674 m`
  - stochastic policy action z mean/final: `-0.095/-0.530`, gripper action mean/final: `-0.176/+0.465`, final gripper width `0.0666 m`
- Decision: post-lift reward-only PPO did not solve sustained hold; launch a training curriculum that uses grasp-prior action warmstart during training to create lifted/closed states, then makes PPO optimize the sustain phase.

Command / Job:
- host: `a1001`
- job_id: `29071322`
- run: `franka_multi_state_teacher_7195_96ae_holdwarm_91063df_20260614T1714Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071322.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_holdwarm_91063df_20260614T1714Z`
- source_commit: `91063df57ef3d018fc29d44357088cb7bd3f6eb4`
- resume_checkpoint: `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`
- PPO: `NUM_ENVS=2048`, `MAX_ITERATIONS=80`, seed `91`, LR `5e-6`, central value LR `1e-5`, KL `0.002`, entropy `0`, save frequency `5`, sigma init `-3`.
- curriculum: `GRASP_PRIOR_ACTION_WARMSTART_ENABLED=True`, approach/close/lift steps `4/60/180`, lift action z `0.70`, prior close width enabled, lift closed-width margin `0.02`.
- action prior/reward: action-prior reward weight `15`, sharpness `4`; rewards strengthened for hold: `lift=45`, `height=15`, `success_bonus=120`, `close_action=6`, `lift_action=10`, descend penalty `-12`, post-lift close/open/lift/descend `8/-12/8/-16`.
- object/reset distribution: same two-object manifest, random object assignment, full yaw, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`, pregrasp offset `0.03`.
- launch note: `SELF_RELAUNCH=False` to prevent manual cancellations from requeueing failed experimental branches.

Next:
- Monitor startup/config, then inspect `cube_action_warmstart_*`, policy z/gripper during and after warmstart, lift/success rates, checkpoints, and policy-only evals.
## 2026-06-14T17:31:15Z - Hold-label BC root-cause patch

Goal:
- Fix the sustained-hold failure mode seen after the DAgger BC, post-lift PPO, and hold-warmstart PPO branches before spending more A100 time.

Hypothesis:
- The mixed hold BC branch was stepping the environment with scripted terminal hold actions but still supervising the actor toward the nominal grasp-prior reference action. If true, the dataset would contain lifted/hold states whose applied action closes/lifts while the target label opens/descends, directly explaining the policy-only eval trend toward opening and negative z.

Change:
- Ran bounded L40 tensor-stat job `1029355` to inspect the previous BC datasets in the Isaac container.
- Patched `bc_reference_action_imitation.py` with `--label_action_source`, defaulting to the old `reference_delta` labels and adding `hold_applied_reference_else` for terminal hold samples.
- Patched `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to expose/pass `LABEL_ACTION_SOURCE`.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-20260613T003321Z.md`
- branch: `main`
- base_commit: `153ecb23cdd75f657902cf623cb02acfab8e505d`
- implementation_commit: `315c3b11de8b5f91fa3d7f7e264323596fa92975`
- push/pull: pending push/deploy
- changed_files: `dextrah_lab/rl_games/bc_reference_action_imitation.py`, `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`, this worklog
- remote_commit/status: pending deploy after commit

Command / Job:
- dataset stats job: `1029355` on `l401`, log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_dataset_stats_1029355.out`
- validation: `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py`
- validation: `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- validation: `git diff --check`

Result:
- status: patch validated locally, not yet relaunched
- metrics/artifacts: previous DAgger-hold dataset had `hold_active=144397/614400` samples and `hold_and_lift02=27699/614400`.
- key evidence: on `hold_and_lift02`, applied labels from the hold controller averaged `z=0.865` and gripper `-0.800`, but the supervised target still averaged `z=-0.208` and gripper `-0.560`; on all `lift_gt_02` samples, applied `z=0.573` while target `z=-0.215`.

Analysis:
- The BC collector was correctly creating lifted/closed states but trained the actor against labels that oppose the hold action in those states. This explains why later PPO/eval repeatedly regressed to negative z/open behavior after the scripted schedule ended.
- The fix preserves old runs by default and enables a targeted corrected run with `LABEL_ACTION_SOURCE=hold_applied_reference_else`.

Next:
- Commit/push/deploy this patch, launch a corrected L40 BC pass from the DAgger BC checkpoint with terminal hold-applied labels plus the reference rehearsal dataset, inspect dataset/action statistics and eval, then resume PPO only if policy-only eval improves.
## 2026-06-14T17:34:00Z - Corrected hold-label BC launch

Goal:
- Train a corrected BC checkpoint whose terminal hold/lift samples are supervised toward the hold action that actually keeps the object lifted and the gripper closed.

Hypothesis:
- Replacing terminal-hold targets with the applied hold action should remove the contradictory negative-z labels in lifted states. A derived handoff source should upweight held/lifted samples enough for the actor to preserve early grasp behavior and improve policy-only terminal occupancy before the next PPO resume.

Change:
- Launched a L40 single-GPU BC run from the previous DAgger BC checkpoint using `LABEL_ACTION_SOURCE=hold_applied_reference_else`.
- Kept the same two-object robust environment, random object assignment, `+-180 deg` yaw, stable-pose cache, verified grasp indices, and grasp-prior reference schedule as previous BC/eval runs.
- Enabled `HANDOFF_SOURCE_ENABLED=True` with `HANDOFF_REQUIRE_HOLD_ACTIVE=True`, `HANDOFF_MIN_LIFT_HEIGHT=0.02`, `HANDOFF_MAX_FINGER_DIST=0.16`, and `HANDOFF_MAX_SAMPLES=120000`.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `21378e945b4fa573beb00a757ea9bd0387f66c50`
- push/pull: pushed to GitHub main; deployed to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` via Git bundle because cluster GitHub fetch still fails with publickey
- remote_commit/status: detached clean at `21378e945b4fa573beb00a757ea9bd0387f66c50`

Command / Job:
- job_id: `1029357`
- host: `l401`
- run_name: `franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029357.out`
- checkpoint input: `/results/bc/franka_multi_7195_96ae_bc_dagger_hold_ep50_d5e8b27_20260614T1625Z/nn/bc_reference_action_imitation.pth`
- expected output checkpoint: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`

Result:
- status: running/queued at launch

Analysis:
- Acceptance for this stage is not BC loss alone. Need inspect dataset stats to confirm hold-active/lifted labels now have positive z/closed gripper, then run deterministic/stochastic policy eval before deciding whether to resume PPO.

Next:
- Monitor `1029357` through completion, inspect `bc_metrics.json`, dataset stats, and corrected checkpoint evals.
## 2026-06-14T17:40:00Z - Corrected BC checkpoint eval launch

Goal:
- Verify that the corrected hold-label BC checkpoint improves policy-only grasp/hold behavior before any A100 PPO resume.

Hypothesis:
- The corrected dataset now supervises held/lifted states toward positive z and closed gripper actions, so deterministic/stochastic rollouts should improve terminal occupancy and reduce the prior open/down failure mode.

Change:
- Completed BC job `1029357` successfully and launched deterministic/stochastic policy evals plus a tensor-stat verification job.

Version Control:
- implementation_commit: `21378e945b4fa573beb00a757ea9bd0387f66c50`
- worklog_commit: `fe94903f0a206798db7d5a651b7c008662713674`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `21378e945b4fa573beb00a757ea9bd0387f66c50`

Command / Job:
- BC run: `franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z`
- BC checkpoint: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`
- deterministic eval job: `1029358`, run `franka_multi_7195_96ae_holdlabel_ep50_21378e9_20260614T1740Z_det`
- stochastic eval job: `1029359`, run `franka_multi_7195_96ae_holdlabel_ep50_21378e9_20260614T1740Z_stoch`
- tensor-stat job: `1029360`, log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_holdlabel_stats_1029360.out`
- eval distribution: `NUM_ENVS=256`, `NUM_STEPS=600`, policy action source, same two-object manifest, random object assignment, full yaw, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`, pregrasp offset `0.03`.

Result:
- status: evals/stats launched
- BC metrics: `selected_step=3000`, `val_l2=0.0533`, `val_source_hold_applied_handoff_l2=0.0552`, `val_source_hold_applied_handoff_up_abs=0.00818`, `val_source_hold_applied_handoff_close_abs=0.0157`.
- handoff source: `29853` held/lifted samples, `lift_mean=0.211 m`, `success_rate=0.0611`, `max_finger_mean=0.0880`.

Analysis:
- The BC objective is now fitting the corrected labels well, but acceptance depends on rollout metrics and action traces.

Next:
- Inspect tensor-stat output to confirm hold/lift labels are positive-z/closed; inspect eval metrics/traces for terminal success/occupancy and policy z/gripper behavior.

## 2026-06-14T17:50:00Z - Corrected BC eval result and warm PPO launch

Goal:
- Resume A100 teacher PPO from the corrected hold-label BC checkpoint and test whether reward shaping plus scripted grasp-prior warmstart can turn the now-consistent held/lifted labels into sustained multi-object grasp success.

Hypothesis:
- The pure BC rollout is still not stable enough, but it no longer has contradictory terminal labels. PPO with strong lift/success rewards, post-lift closed/up action pressure, and a longer grasp-prior action warmstart should keep exploration in the useful grasp basin and improve above the previous short-lived success spikes.

Change:
- Verified corrected dataset labels before PPO: hold-active/lifted samples now use the applied hold action as the supervised target.
- Inspected deterministic/stochastic policy-only evals from the corrected BC checkpoint; both still decay to open/down behavior, so PPO remains required.
- Launched a new 8-GPU A100 PPO run from the corrected BC checkpoint with full-yaw randomization, random object assignment per environment, stable-pose cache, verified grasp indices, and a 4/60/240 approach/close/lift warmstart sequence.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `21378e945b4fa573beb00a757ea9bd0387f66c50`
- worklog_base_commit: `7576c7f0ec2cada0fb3908082f534b6b7020cb00`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `21378e945b4fa573beb00a757ea9bd0387f66c50`

Command / Job:
- stats job: `1029360`, log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_holdlabel_stats_1029360.out`
- deterministic eval: `franka_multi_7195_96ae_holdlabel_ep50_21378e9_20260614T1740Z_det`
- stochastic eval: `franka_multi_7195_96ae_holdlabel_ep50_21378e9_20260614T1740Z_stoch`
- PPO job_id: `29071795`
- PPO run_name: `franka_multi_state_teacher_7195_96ae_holdlabel_warmppo_21378e9_20260614T1750Z`
- PPO run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_holdlabel_warmppo_21378e9_20260614T1750Z`
- PPO log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071795.out`
- PPO checkpoint input: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`

Result:
- corrected label stats: `hold_active` ref/app z both `0.47995`, gripper both `-0.800`; `lift_gt_02` ref/app z both `0.73179`, gripper both `-0.7589`; `hold_and_lift02` ref/app z both `0.88763`, gripper both `-0.800`.
- deterministic eval: `success_rate_final=0.0`, `success_rate_max=0.0703125`, `success_ever_rate=0.13671875`, `success_occupancy_mean=0.006803`; final policy action decayed to z `-0.4970`, gripper `+0.3734`.
- stochastic eval: `success_rate_final=0.00390625`, `success_rate_max=0.0703125`, `success_ever_rate=0.16015625`, `success_occupancy_mean=0.004349`; final policy action decayed to z `-0.5143`, gripper `+0.2049`.
- PPO status: job running on A100 `polar`; startup log confirms the corrected checkpoint and intended multi-object environment/reward/warmstart overrides.

Analysis:
- The label bug is fixed, but the actor alone still loses the grasp after the scripted/data region. The next decision should be based on early PPO diagnostics: sustained lift/success, policy z/gripper action after warmstart, and post-lift reward/penalty balance.
- If the PPO metrics show the same collapse as previous attempts after the warmstart phases, cancel early and tune the RL objective or handoff/warmstart path instead of spending the whole wall time.

Next:
- Monitor `direct_info_rank_0.jsonl` as soon as the run directory appears. Continue, cancel/tune/relaunch, or evaluate checkpoints based on reward/action traces rather than scheduler state.

## 2026-06-14T18:08:00Z - Warm PPO early cancellation and reward-action fix

Goal:
- Diagnose the first corrected-label PPO attempt early enough to avoid wasting the A100 allocation, then patch the most likely credit-assignment bug before relaunching.

Hypothesis:
- The PPO run was rewarding scripted warmstart actions instead of raw policy actions for close/lift/post-lift action shaping. That makes the robot state look useful during warmstart, but PPO cannot learn the post-warmstart hold behavior because the action-dependent reward is not tied to the policy action that generated the log-prob.

Change:
- Canceled A100 job `29071795` after 10 metric rows because success/lift collapsed whenever warmstart was mostly inactive.
- Changed `DextrahFrankaCubeGraspEnv._get_rewards()` so action-dependent cube grasp reward terms use `grasp_prior_action_warmstart_policy_actions` whenever warmstart is enabled, while state still evolves under the applied action.
- Added diagnostic logs for `cube_reward_action_z`, `cube_reward_action_up/down`, and `cube_reward_gripper_*` so future runs can distinguish applied action from policy action in reward shaping.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `dbfe99671c385474bfc4e735c14fc1bda9685b55`
- implementation_commit: pending
- remote PPO source before patch: detached clean at `21378e945b4fa573beb00a757ea9bd0387f66c50`
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, this worklog

Command / Job:
- canceled job_id: `29071795`
- run_name: `franka_multi_state_teacher_7195_96ae_holdlabel_warmppo_21378e9_20260614T1750Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_holdlabel_warmppo_21378e9_20260614T1750Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071795.out`
- validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`; `git diff --check`

Result:
- job status: canceled intentionally after early failure evidence.
- epoch 51-60 metrics: success mean `0.0163`, max `0.0439`, min `0.0010`; lift mean `0.00895 m`, min `0.00367 m`; policy z mean `-0.135`; policy gripper action mean `-0.431`.
- failure signature: epochs 55-59 had low warmstart active rate (`0.025-0.089`), success `0.00098-0.0117`, lift below `0.008 m`, and gripper width around `0.025-0.031 m`. Epoch 60 success spike coincided with warmstart active rate returning to `0.498`, so it was not learned sustained grasping.

Analysis:
- The corrected BC labels helped the supervised data consistency but did not solve RL credit assignment. The warmstart intervention creates good state distributions, but the old reward helper used `self.actions` after `_pre_physics_step(applied_actions)`, so action-shaping reward terms were often credited to scripted actions rather than raw policy actions.
- The patch keeps the intervention for physics but makes the close/lift/post-lift action reward policy-dependent, which should produce a usable gradient during the same warmstarted state distribution.

Next:
- Commit/push/deploy this patch to the A100 worktree, relaunch a bounded PPO run, and compare `cube_reward_action_*` against `cube_policy_*`/`cube_applied_*`. Continue only if non-warmstart epochs preserve lift/success better than `29071795`.

## 2026-06-14T18:15:00Z - Reward-action fix PPO relaunch

Goal:
- Test whether computing action-dependent rewards from raw policy actions during warmstart improves policy takeover after scripted grasp-prior intervention ends.

Hypothesis:
- Compared with canceled job `29071795`, the first post-warmstart low-active epochs should show higher policy z/close pressure, smaller gripper-width opening, and less collapse in lift/success.

Change:
- Deployed `831f546e7f448530acab7208bca7e7b413558361` to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` via Git bundle.
- Relaunched the same A100 PPO configuration as `29071795`, changing only the source commit and seed.

Version Control:
- agent_id: orchestrator/integration
- implementation_commit: `831f546e7f448530acab7208bca7e7b413558361`
- push/pull: pushed to GitHub main; remote checkout updated from `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/DEXTRAH/dextrah-831f546.bundle`
- remote_commit/status: detached clean at `831f546e7f448530acab7208bca7e7b413558361`

Command / Job:
- job_id: `29071991`
- run_name: `franka_multi_state_teacher_7195_96ae_actionreward_831f546_20260614T1815Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_actionreward_831f546_20260614T1815Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071991.out`
- checkpoint input: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`
- task/config: same two-object manifest, random object assignment per env, full yaw, stable-pose cache, verified grasp indices, reset attempts `4`, candidates `64`, pregrasp offset `0.03`, warmstart `4/60/240`, action-prior reward `8.0`.

Result:
- status: submitted

Analysis:
- This run should be judged against the canceled job's epochs 51-60, not against wall-clock completion. If `cube_reward_action_*` equals raw policy diagnostics and non-warmstart success still collapses, the next change should target the reset/hold distribution or add a persistent post-lift action gate.

Next:
- Monitor startup, then parse rank-0 direct metrics. Continue only if post-warmstart behavior improves materially.

## 2026-06-14T18:31:00Z - Reward-action run canceled; persistent post-lift gate patch

Goal:
- Stop the second failing PPO attempt and add a hold/recovery action-shaping signal that survives object slip after the first lift.

Hypothesis:
- Even after action rewards used raw policy actions, post-lift action shaping disappeared as soon as current lift height fell below the gate. That removes the up/closed recovery signal exactly when the object starts slipping. Using `has_lifted_cube` as a persistent post-lift gate should keep close/up rewards and open/down penalties active after the first lift event.

Change:
- Canceled A100 job `29071991` after the same low-warmstart collapse window as the previous run.
- Updated `compute_franka_cube_grasp_rewards()` to accept `has_lifted_cube` and set `postlift_gate=max(current_lift_gate, has_lifted_cube)`.
- Threaded `has_lifted_cube` through the Franka cube env and validation helper; corrected stale validation reward-term indices for table-clearance and gripper-close regularization.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `ff306163f02fd3dc13c9b629f5b521351fc81d39`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_rewards.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog

Command / Job:
- canceled job_id: `29071991`
- run_name: `franka_multi_state_teacher_7195_96ae_actionreward_831f546_20260614T1815Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_actionreward_831f546_20260614T1815Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071991.out`
- validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_rewards.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`; `git diff --check`

Result:
- epoch 55-60 metrics: success mean `0.00928`, max `0.0342`, min `0.00098`; lift mean `0.00822 m`; policy z mean `-0.198`; gripper width mean `0.0287 m`.
- mechanical patch verification: `cube_reward_action_*` matched raw policy actions as intended, but that did not prevent collapse when warmstart was inactive.
- local torch reward-value check could not run because local system Python has no `torch`; compile and wrapper syntax checks passed.

Analysis:
- The action-credit patch was necessary but insufficient. The policy receives some close/up shaping in low-lift states, but once the current lift gate drops the strongest post-lift action pressure weakens. The persistent `has_lifted_cube` gate should make slipping states keep producing direct recovery pressure.

Next:
- Commit/push/deploy this patch, relaunch another bounded PPO comparison, and watch epochs 55-60 plus later low-warmstart phases. If this still collapses, the next target is reset distribution or a supervised/auxiliary action loss rather than more reward weight tweaks.

## 2026-06-14T18:37:00Z - Persistent post-lift gate PPO launch

Goal:
- Test whether persistent post-lift action shaping improves policy hold/recovery after the object has been lifted once.

Hypothesis:
- In the low-warmstart phase, `cube_postlift_*` terms should stay large enough to oppose negative-z/opening behavior, increasing success/lift relative to jobs `29071795` and `29071991`.

Change:
- Deployed `ca70e4bbfa20472b098a0476d106bf781199aaa2` to the A100 source worktree via Git bundle.
- Relaunched the same corrected-label BC warm PPO setup with the persistent `has_lifted_cube` post-lift gate patch.

Version Control:
- implementation_commit: `ca70e4bbfa20472b098a0476d106bf781199aaa2`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `ca70e4bbfa20472b098a0476d106bf781199aaa2`
- push/pull: pushed to GitHub main; remote updated from `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/DEXTRAH/dextrah-ca70e4b.bundle`

Command / Job:
- job_id: `29072214`
- run_name: `franka_multi_state_teacher_7195_96ae_postliftgate_ca70e4b_20260614T1837Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_postliftgate_ca70e4b_20260614T1837Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29072214.out`
- checkpoint input: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`

Result:
- status: submitted

Analysis:
- Acceptance for this attempt is not the scripted warmstart spike. The run needs materially better epochs 55-60 and later low-warmstart windows than `29071991`, plus non-collapsing policy z/closed action.

Next:
- Monitor startup and parse rank-0 direct metrics. Cancel/tune again if the low-warmstart phase still collapses.

## 2026-06-14T18:47:00Z - Post-lift gate PPO diagnosis; collector-matched relaunch planned

Goal:
- Diagnose job `29072214` before launching another PPO attempt.

Hypothesis:
- The persistent post-lift gate made the policy learn up/close actions, but the run still failed because the training warmstart close/lift settings diverged from the dynamically verified grasp collector.

Change:
- No source changes for this entry.
- Compared job `29072214` metrics with the verified-grasp collector log `collect_franka_multi_object_verified_grasps_1029302.out`.
- Identified launch mismatch: collector used prior-width close (`close_width=0.08`, `use_prior_close_width=True`, `prior_close_width_margin=0.003`) and `lift_action_z=0.50`; PPO job `29072214` used `prior_close_width_margin=0.020`, `lift_action_z=0.70`, and `lift_closed_width_margin=0.020`, driving the gripper to about 2 mm and lifting faster than the verified behavior.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `ca70e4bbfa20472b098a0476d106bf781199aaa2`
- changed_files: this worklog only
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `ca70e4bbfa20472b098a0476d106bf781199aaa2`

Command / Job:
- monitored job_id: `29072214`
- run_name: `franka_multi_state_teacher_7195_96ae_postliftgate_ca70e4b_20260614T1837Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_postliftgate_ca70e4b_20260614T1837Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29072214.out`

Result:
- status: failed / still finishing final epochs at time of diagnosis
- epochs 91-95: success mean `0.0135`, lift mean `0.0075 m`, warmstart lift success mean `0.0486`, warmstart lift height mean `0.0243 m`, max finger distance mean `0.567 m`.
- epoch 96: success `0.00439`, lift `0.00711 m`, warmstart lift success `0.0328`, warmstart lift height `0.0191 m`, max finger distance `0.623 m`.

Analysis:
- The policy learned the intended z/close action direction (`policy_action_z` reached about `0.8`), but the object did not stay in contact. The gripper width and verified-grasp launch mismatch point to crushing/slipping caused by overly aggressive close and lift settings, not to a missing post-lift action signal.
- The long/thin debug objects also expose a possible next code issue: reward and success distances are still measured to object center rather than sampled grasp/contact reference. I will first test the collector-matched close/lift schedule because it is the smallest controlled change and reuses the already verified grasp cache.

Next:
- Launch a collector-matched PPO run from the same corrected BC checkpoint with `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.08`, `GRASP_PRIOR_ACTION_WARMSTART_PRIOR_CLOSE_WIDTH_MARGIN=0.003`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.50`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`, `GRASP_PRIOR_RESET_ATTEMPTS=8`, and a training-safe verified-index candidate count.
- If warmstart lift success remains low or PPO still drifts away, patch the multi-object env to transform the sampled contact reference with the current object pose and use that reference for finger/approach/success distance terms.

## 2026-06-14T18:48:00Z - Collector-matched prior-width PPO launch

Goal:
- Test whether matching the verified-grasp collector's close/lift settings restores warmstart grasp stability and gives PPO a usable distribution.

Hypothesis:
- The previous PPO run crushed/slipped the long objects by closing to about 2 mm and lifting too aggressively. Restoring prior-width close (`margin=0.003`) and slower lift (`z=0.50`) should improve warmstart lift success, reduce lift-phase finger distance, and improve later PPO success/lift metrics.

Change:
- No source-code changes. Launched a new A100 run from the same deployed code commit and corrected BC checkpoint.
- Training candidate count kept at `64` rather than `4096` because the verified cache contains one accepted grasp index per object; 4096 would duplicate the same verified index across 2048 envs and waste GPU memory.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `ca70e4bbfa20472b098a0476d106bf781199aaa2`
- changed_files: this worklog only
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `ca70e4bbfa20472b098a0476d106bf781199aaa2`

Command / Job:
- command: `sbatch --export=ALL,... cluster/sbatch_train_teacher_8gpu.sh` from `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- job_id: `29072558`
- run_name: `franka_multi_state_teacher_7195_96ae_priorwidth_ca70e4b_20260614T1848Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_priorwidth_ca70e4b_20260614T1848Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29072558.out`
- checkpoint input: `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`
- key overrides: `MAX_ITERATIONS=120`, `GRASP_PRIOR_RESET_ATTEMPTS=8`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=64`, `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.08`, `GRASP_PRIOR_ACTION_WARMSTART_PRIOR_CLOSE_WIDTH_MARGIN=0.003`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.50`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`, same two-object manifest/stable-pose/verified-index paths.

Result:
- status: submitted

Analysis:
- Acceptance criteria for this run: warmstart lift success and lift height should beat job `29072214` by a clear margin in the same 51-60 and later windows, and low-warmstart PPO epochs must not drift to large finger distances while success/lift collapse.

Next:
- Monitor queue/startup, parse rank-0 direct metrics, and cancel/tune if the collector-matched warmstart still fails to lift or PPO still learns away from the objects.

## 2026-06-14T19:07:21Z - Prior-width PPO failed; contact-reference patch

Goal:
- Stop the prior-width PPO attempt once it was clear that the collector-matched close/lift schedule alone did not create a successful learning signal, then patch the multi-object reward/success distances to follow the selected grasp contact on the moving object.

Hypothesis:
- The long/thin objects expose a mismatch in the multi-object task: grasp priors are sampled around contact points, but rewards/success still measure hand distance to object center. After reset and lift, the object center can be far from the intended grasp contact, causing the policy to receive weak or incorrect approach/enclosure/success signals even when the grasp prior is geometrically valid.

Change:
- Canceled job `29072558` after rank-0 metrics through epoch 58 showed collapse.
- Added reset-prior buffers for the selected contact reference in object coordinates and current env coordinates.
- Multi-object reset now returns the chosen contact midpoint in object coordinates.
- Multi-object intermediate values now keep object center for lift/XY/goal, but compute EE/finger/hand distances and success hand-distance gate against the current contact reference transformed by the current object root pose when a quality contact prior is active.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `4f897bf901b973f0b989ca5d7611040dbb613d66`
- implementation_commit: `8b1a36aaca67167366433be05365cd4384f0318f`
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `8b1a36aaca67167366433be05365cd4384f0318f`
- push/pull: pushed to GitHub main; remote updated from `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/DEXTRAH/dextrah-8b1a36a.bundle`

Command / Job:
- canceled job_id: `29072558`
- run_name: `franka_multi_state_teacher_7195_96ae_priorwidth_ca70e4b_20260614T1848Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_priorwidth_ca70e4b_20260614T1848Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29072558.out`
- validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`

Result:
- status: failed / canceled for tuning
- Slurm: `29072558|CANCELLED by 158351|0:0|00:18:20|batch-block5-01569`
- epoch 51-55: success mean `0.0281`, lift mean `0.0116 m`, warmstart lift success mean `0.0301`, warmstart lift height mean `0.0126 m`, center-based finger distance mean `0.283 m`.
- epoch 56-58: success mean `0.00163`, lift mean `0.00607 m`, warmstart lift success mean `0.0239`, warmstart lift height mean `0.0128 m`, center-based finger distance mean `0.333 m`.

Analysis:
- Matching the verified collector's prior-width close settings avoided the overly aggressive 2 mm close target from the previous run, but the learning signal still collapsed by epoch 56. The center-distance reward/success path is now the most likely blocker because selected contact points for these objects are far from the object center, and the current logged finger distance grows while lift/success disappear.

Next:
- Commit/push/deploy the contact-reference patch, relaunch PPO from the corrected BC checkpoint with the same two-object manifest and collector-matched warmstart settings, then compare epochs 51-60 against jobs `29072214` and `29072558`.

## 2026-06-14T19:10:00Z - Contact-reference PPO relaunch

Goal:
- Test the moving contact-reference distance patch under the same two-object, yaw-randomized, collector-matched PPO setup.

Hypothesis:
- If the main blocker was center-distance reward/success mismatch for long objects, the same BC checkpoint and warmstart schedule should now produce lower logged hand distance, higher success, and higher lift in epochs 51-60 than job `29072558`.

Change:
- No additional source changes beyond `8b1a36aaca67167366433be05365cd4384f0318f`.
- Deployed the commit to the A100 agent source worktree via Git bundle because the A100 host cannot authenticate to GitHub directly.

Version Control:
- agent_id: orchestrator/integration
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `8b1a36aaca67167366433be05365cd4384f0318f`
- remote_source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached clean at `8b1a36aaca67167366433be05365cd4384f0318f`

Command / Job:
- command: `sbatch --export=ALL,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `29073180`
- run_name: `franka_multi_state_teacher_7195_96ae_contactref_8b1a36a_20260614T1910Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_contactref_8b1a36a_20260614T1910Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29073180.out`
- key overrides: same manifest, stable-pose cache, verified-index cache, random object assignment, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, `OBJECT_SPAWN_XY_RANDOMIZATION=0.10`, `GRASP_PRIOR_ACTION_WARMSTART_PRIOR_CLOSE_WIDTH_MARGIN=0.003`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.50`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`, `MAX_ITERATIONS=120`, `NUM_ENVS=2048`.

Result:
- status: submitted / running on `batch-block5-00102`

Analysis:
- The first pass/fail gate is epochs 51-60. Contact-reference metrics should make the logged `cube_finger_center_to_cube_dist` much smaller than the previous center-based ~0.33 m if the selected grasp contact remains near the gripper.

Next:
- Monitor startup, parse rank-0 metrics, and cancel/tune if the first 51-60 window still collapses.
## 2026-06-14 12:48 PDT - Contact-reference PPO cancellation and reset-quality cap patch

Goal:
- Stop the weak contact-reference PPO run and tighten multi-object grasp-prior reset acceptance before relaunching training.

Hypothesis:
- The moving contact-reference patch fixed stale distance bookkeeping, but reset quality is still too permissive for long objects because the inherited threshold scales with `object_grasp_size`.
- Hard-capping projected gripper/contact distances should reject badly aligned reset poses instead of spending PPO updates on unreachable warmstart grasps.

Change:
- Canceled A100 job `29073180` (`franka_multi_state_teacher_7195_96ae_contactref_8b1a36a_20260614T1910Z`) after metrics stayed poor through epoch 68.
- Added optional reset-quality hard caps to the shared Franka grasp-prior gate.
- Kept cube defaults disabled and enabled multi-object defaults: finger center `0.08 m`, tip center `0.08 m`, tip max `0.10 m`.
- Wired the cap values through `cluster/sbatch_train_teacher_8gpu.sh` for future launch-time tuning.

Version Control:
- agent_id: `dextrah-multiobject-grasp-prior-20260613T003321Z`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- base_commit: `28b36ac`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `cluster/sbatch_train_teacher_8gpu.sh`, this worklog

Command / Job:
- canceled_job_id: `29073180`
- canceled_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_contactref_8b1a36a_20260614T1910Z`
- canceled_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29073180.out`

Result:
- status: patch validated locally, relaunch pending
- metrics/artifacts: epochs 66-68 mean success `0.00179`, mean lift height `0.00419 m`, mean warmstart lift success `0.0124`, mean projected exact finger center distance `0.153 m`, mean reset quality success rate `0.522`.
- validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`; `git diff --check`.

Analysis:
- The active run showed the policy sometimes learned upward action during teacher-active epochs, but reset/warmstart lift success collapsed again as the policy moved away from the scripted phase.
- Since quality success remained above 50% while projected contact alignment was about 15 cm off, the reset gate itself was admitting weak examples.

Next:
- Commit and push the cap patch.
- Deploy the exact commit to the A100 agent worktree with a Git bundle.
- Relaunch PPO and monitor whether reset quality drops while warmstart lift/contact metrics improve.

## 2026-06-14T19:52:00Z - Reset-quality-cap PPO relaunch

Goal:
- Test whether strict reset-quality caps improve two-object state-teacher PPO from the same BC checkpoint and task setup.

Hypothesis:
- If the previous run failed because long-object resets accepted gripper/contact alignment around `0.15 m`, then explicit `0.08/0.08/0.10 m` caps should lower reset quality acceptance but improve warmstart lift/contact quality and downstream PPO success.

Change:
- No source changes beyond `77927d9e377df598e011d90bafb29b09d44e7b66`.
- Deployed `77927d9e377df598e011d90bafb29b09d44e7b66` to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` using `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/DEXTRAH/dextrah-77927d9.bundle`.

Version Control:
- agent_id: `dextrah-multiobject-grasp-prior-20260613T003321Z`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `77927d9e377df598e011d90bafb29b09d44e7b66`
- push/pull: pushed to `origin/main`; A100 worktree detached clean at implementation commit.

Command / Job:
- command: `sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh` with task `Dextrah-Franka-Multi-Object-Grasp`, `NUM_ENVS=2048`, `MAX_ITERATIONS=120`, `SEED=114`, same two-object manifest/stable-pose cache/verified-index cache/BC checkpoint as the contact-reference run, yaw randomization `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, and reset-quality caps `GRASP_PRIOR_RESET_QUALITY_MAX_FINGER_CENTER_DIST=0.08`, `GRASP_PRIOR_RESET_QUALITY_MAX_TIP_CENTER_DIST=0.08`, `GRASP_PRIOR_RESET_QUALITY_MAX_TIP_MAX_DIST=0.10`.
- job_id: `29073685`
- run_name: `franka_multi_state_teacher_7195_96ae_qualitycap_77927d9_20260614T1952Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_qualitycap_77927d9_20260614T1952Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29073685.out`

Result:
- status: submitted; startup/metrics monitoring pending.

Analysis:
- A separate RGB job `29073480` is already running from `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-multiobject-rgb-rl-20260613` at commit `c9e8dc7d48f4fcbf6bec7e94c18438d6970fabd7`; it is not this state-teacher relaunch and was left untouched.

Next:
- Monitor queue/startup, inspect log header for resolved overrides, parse metrics once rank-0 JSONL appears, and cancel/tune again if reset quality becomes zero or success remains collapsed.

## 2026-06-14T20:03:00Z - JSONL-enabled reset-quality-cap relaunch

Goal:
- Relaunch the reset-quality-cap PPO run with direct scalar JSONL enabled so reset-quality and warmstart diagnostics can be monitored.

Result:
- Canceled job `29073685` after it reached epoch 51 because it was launched with `DEXTRAH_RLGAMES_JSONL_METRICS=False`; run directory contained TensorBoard summaries but no `metrics/direct_info_rank_0.jsonl`, and TensorBoard tooling was not available in the login/site Python environments.
- Submitted replacement job `29073801` with identical source/config plus `DEXTRAH_RLGAMES_JSONL_METRICS=True`.

Command / Job:
- canceled_job_id: `29073685`
- canceled_run_name: `franka_multi_state_teacher_7195_96ae_qualitycap_77927d9_20260614T1952Z`
- canceled_result: `CANCELLED by 158351`, elapsed `00:10:53`; reached `epoch: 51/120`.
- replacement_job_id: `29073801`
- replacement_run_name: `franka_multi_state_teacher_7195_96ae_qualitycap_jsonl_77927d9_20260614T2003Z`
- replacement_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_qualitycap_jsonl_77927d9_20260614T2003Z`
- replacement_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29073801.out`

Analysis:
- Training itself started successfully under the cap patch, so the relaunch is for observability rather than an environment/runtime failure.
- The first scene creation on `batch-block7-03208` took about `258 s`, so early startup should not be mistaken for a hang if logs are slow before the first epoch.

Next:
- Confirm the replacement log resolves `DEXTRAH_RLGAMES_JSONL_METRICS=True`.
- Monitor the first epochs and compare reset-quality/contact metrics against canceled job `29073180`.

## 2026-06-14T20:25:00Z - Gated warmstart PPO relaunch

Goal:
- Prevent the scripted warmstart/reference action from closing and lifting before the Franka EE reaches the grasp contact.

Result:
- Job `29073801` (`franka_multi_state_teacher_7195_96ae_qualitycap_jsonl_77927d9_20260614T2003Z`) was canceled after epoch 56.
- Evidence from epochs 51-56:
  - success fell from `0.0474` at epoch 51 to `0.0039` at epoch 56.
  - warmstart lift success stayed low (`0.050-0.097` in epochs 54-56).
  - active/lift exact EE error was large (`~0.21-0.29 m`) while the gripper was closing/lifting.
  - close target and lift gripper width were reasonable (`~0.0054 m`), so the failure was not simply an open gripper.
- Diagnosis: the previous launch closed after only 4 policy steps and lifted on a fixed schedule with `close_max_ee_error=0`, `lift_max_ee_error=0`, `lift_max_finger_center_dist=0`, and `lift_closed_width_margin=-1`; it was closing/lifting while still far from the contact.

Command / Job:
- canceled_job_id: `29073801`, state `CANCELLED by 158351`, elapsed `00:17:11`.
- replacement_job_id: `29074376`
- replacement_run_name: `franka_multi_state_teacher_7195_96ae_gatedwarm_77927d9_20260614T2025Z`
- replacement_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_gatedwarm_77927d9_20260614T2025Z`
- replacement_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29074376.out`
- changed launch overrides only: `GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS=80`, `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS=100`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=160`, `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_MAX_EE_ERROR=0.06`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_MAX_EE_ERROR=0.06`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_MAX_FINGER_CENTER_DIST=0.08`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=0.004`.

Analysis:
- This is a config-only tuning iteration on source commit `77927d9e377df598e011d90bafb29b09d44e7b66`.
- Expected behavior: lower premature lift rate, lower lift exact-EE/finger distance, and higher warmstart lift success before policy learning is judged.

Next:
- Monitor `29074376` through the first 51-60 window.
- If lift never triggers, relax the gates slightly; if lift triggers with low success, generate a focused grasp-contact rollout for the accepted reset subset.

## 2026-06-14T20:40:00Z - Current-lift-gate patch

Goal:
- Stop the warmstart controller from continuing lift after a stale one-step gate hit when the gripper/object contact has already drifted away.

Result:
- Canceled job `29074376` after epoch 56.
- Evidence:
  - success stayed near `0.054` at epochs 52-55, then fell to `0.0093` at epoch 56.
  - warmstart lift success remained `0.0`.
  - the rare lift samples had `lift_reference_finger_center_dist=0.0788` at epoch 53, then drifted to `0.1736`, `0.2722`, and `0.3412` by epochs 54-56 while still counted as lift.
  - this showed the lift latch was stale: once an env latched lift, it kept receiving lift actions even after current lift-readiness was false.

Change:
- Add `grasp_prior_action_warmstart_require_current_lift_ready`.
- Keep the cube baseline default as `False`.
- Set the multi-object default to `True`.
- When enabled, `_grasp_prior_action_warmstart_phase_masks()` uses current `close_ready & ready_to_lift` instead of OR-ing with the previous lift latch.
- Expose/log `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY` in `cluster/sbatch_train_teacher_8gpu.sh`.

Version Control:
- base_commit: `47830a2`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `cluster/sbatch_train_teacher_8gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- `git diff --check`

Next:
- Commit/push, deploy to the A100 agent worktree, and relaunch with current lift gating enabled.

## 2026-06-14T20:42:03Z - Current-lift-gate PPO relaunch

Goal:
- Verify the current-lift-ready patch and test a less restrictive warmstart schedule that can still reach close/lift while preventing stale lift continuation.

Version Control:
- implementation_commit: `0fea1cde7ed59881c3a9ef04fb2af2499fb1feff`
- push/pull: pushed to `origin/main`; deployed to A100 via `/lustre/fsw/portfolios/nvr/users/lzha/src/bundles/DEXTRAH/dextrah-0fea1cd.bundle`.
- remote_worktree: `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: detached at `0fea1cde7ed59881c3a9ef04fb2af2499fb1feff`, clean.

Validation:
- Remote `python3 -m py_compile` passed for the affected env config/code files.
- Remote `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` passed.
- Remote `git diff --check` passed.

Command / Job:
- job_id: `29074535`
- run_name: `franka_multi_state_teacher_7195_96ae_currentlift_0fea1cd_20260614T204203Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_currentlift_0fea1cd_20260614T204203Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29074535.out`
- source_commit: `0fea1cde7ed59881c3a9ef04fb2af2499fb1feff`
- changed warmstart overrides relative to the canceled gated run: `approach_steps=48`, `close_steps=96`, `lift_steps=160`, `lift_action_z=0.35`, `close_max_ee_error=0.12`, `lift_max_ee_error=0.12`, `lift_max_finger_center_dist=0.14`, `lift_closed_width_margin=0.006`, `require_current_lift_ready=True`.

Next:
- Confirm resolved config contains `grasp_prior_action_warmstart_require_current_lift_ready: true`.
- Parse early JSONL epochs; accept only if lift actions keep current reference/finger distances bounded and produce nonzero lift success.

## 2026-06-14T20:44:17Z - Checkpoint path fix relaunch

Result:
- Job `29074535` failed before environment construction.
- Root cause: the launch used the host checkpoint path `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/...` as `CHECKPOINT`; inside the container this must be `/results/...`.
- Failure evidence: `FileNotFoundError: Unable to find the file: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/.../bc_reference_action_imitation.pth`.

Command / Job:
- failed_job_id: `29074535`, state `FAILED`, elapsed `00:01:39`.
- replacement_job_id: `29074553`
- replacement_run_name: `franka_multi_state_teacher_7195_96ae_currentlift_0fea1cd_ckptfix_20260614T204417Z`
- replacement_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29074553.out`
- replacement_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_currentlift_0fea1cd_ckptfix_20260614T204417Z`
- replacement_change: `CHECKPOINT=/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`.

Result:
- `29074553` submitted successfully but is pending with `(QOSMaxJobsPerUserLimit)` while a separate RGB job from `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/franka-multiobject-rgb-rl-20260613` is running.

Next:
- Monitor pending state until `29074553` starts.
- Once running, confirm resolved config and parse rank-0 JSONL metrics.

## 2026-06-14T21:01:00Z - Current-lift PPO canceled; prepare video diagnosis

Result:
- Job `29074553` (`franka_multi_state_teacher_7195_96ae_currentlift_0fea1cd_ckptfix_20260614T204417Z`) was canceled after epoch 56.
- Metrics:
  - close phase activated (`~0.24-0.26` at epochs 51-52).
  - lift phase activated (`0.17-0.20` at epochs 53-54).
  - current-lift patch worked: lift reference distance stayed bounded around `0.117-0.118 m`, unlike the stale-latch run where it drifted above `0.27 m`.
  - lift success remained `0.0`; lift height during lift was near zero (`~0.0001 m` recent mean).
  - overall success fell to `0.0059` by epoch 56.
- Analysis: the controller is no longer applying stale bad lift actions, but the accepted grasp/contact is still not carrying the object. Further PPO is not useful until the grasp-contact behavior is visually diagnosed.

Change:
- Added `--grasp_warmstart_require_current_lift_ready` to `validate_franka_multi_object_grasp_videos.py`.
- Exposed/logged `GRASP_WARMSTART_REQUIRE_CURRENT_LIFT_READY` in `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- `git diff --check`

Next:
- Commit/push/deploy the validator patch.
- Run focused videos with the exact current-lift warmstart settings and inspect `grasp_contact`.

## 2026-06-14T21:03:26Z - Current-lift contact video launch

Command / Job:
- job_id: `1029403`
- host: `l401`
- run_name: `franka_multi_currentlift_contact_video_5c1a3e3_20260614T210326Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_currentlift_contact_video_5c1a3e3_20260614T210326Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029403.out`
- commit: `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- key settings: `NUM_ENVS=4`, `MAX_OBJECTS=2`, stable pose cache enabled, yaw `180`, spawn center `(0.05,0)`, XY randomization `0.10`, grasp warmstart `48/96/160`, lift z `0.35`, close/lift EE gates `0.12`, lift finger gate `0.14`, current lift gate enabled.

Next:
- Monitor job startup and completion.
- Encode/inspect `grasp_contact` frames first, then reset/perturbation videos if needed.

## 2026-06-14T21:14:00Z - Verified-schedule contact video relaunch

Goal:
- Revalidate grasp contact with the same schedule used by the accepted verified-index cache before launching more PPO.

Hypothesis:
- The failed current-lift PPO/video used a much longer approach phase (`48`) and lower lift action (`0.35`) than the verified grasp-index search (`approach=4`, `close=60`, `lift=180`, `lift_z=0.5`), causing the gripper to push the rod-like object while staying open instead of proving a real close/lift grasp.

Change:
- No environment code changes for this attempt.
- Run the video validator from commit `5c1a3e3fb79d41615e4512ac173080c47e5a0091`.
- Keep the same two-object manifest, stable-pose cache, 360-degree yaw randomization setting, spawn center `(0.05, 0)`, `+-0.10 m` XY randomization, verified grasp index cache, and `grasp_prior_pregrasp_offset=0.03`.
- Switch the warmstart schedule to the verified-index search values: `approach=4`, `close=60`, `lift=180`, `lift_action_z=0.5`.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- remote_worktree: `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- changed_files: this worklog only

Command / Job:
- command: `sbatch cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` with verified warmstart schedule overrides.
- job_id: `1029404`
- run_name: `franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029404.out`
- expected_artifacts: `reset_settle.mp4`, `perturbation.mp4`, `grasp_contact.mp4`, `video_metrics.json`.

Next:
- Submit on `l401`, monitor to completion, fetch/encode artifacts, inspect `grasp_contact.mp4`, and only then decide whether to relaunch PPO with the verified schedule.

Result:
- status: passed
- scheduler: job `1029404` completed with exit code `0:0` in `00:02:27` on `pool0-00002`.
- local_artifacts:
  - `cluster_results/l401/franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z/reset_settle.mp4`
  - `cluster_results/l401/franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z/perturbation.mp4`
  - `cluster_results/l401/franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z/grasp_contact.mp4`
  - `cluster_results/l401/franka_multi_verifiedsched_contact_video_5c1a3e3_20260614T211437Z/video_metrics.json`
- video encoding: `grasp_contact.mp4` is 1280x720, 131 frames, 8.733s at 15 FPS; reset and perturbation are 1280x720, 36 frames, 2.4s each.
- metrics:
  - overall `passed=true`
  - reset_settle passed: `object_xy_delta_max=6.60e-05`, `bottom_clearance_min=-0.00012`, `done_count=0`
  - perturbation passed: `object_xy_delta_max=0.103`, `object_speed_max=0.495`, `object_angular_speed_max=5.51`, `bottom_clearance_min=-0.00020`
  - grasp_contact passed: phases `[-1,0,1,2]`, `selected_lift_height_max=0.425`, `selected_object_xy_delta_max=0.024`, `selected_done_count=0`, `selected_gripper_width_min=0.0054`, `bottom_clearance_min=0.0011`
- visual inspection:
  - reset-settle frames show the object staying on the table without visible sinking or bouncing away.
  - perturbation frames show the object moving/tilting normally and staying on the table.
  - grasp-contact frames show the gripper closing around the thin object and carrying it upward; no obvious table penetration or impossible initial interpenetration was visible in sampled frames.

Analysis:
- The environment reset/contact path is valid with the verified schedule.
- The previous PPO schedule was the likely problem: long approach (`48`) and stricter gates let the rod-like object get disturbed before a useful close/lift phase.

Next:
- Relaunch A100 PPO from the BC checkpoint using the verified warmstart schedule: `approach=4`, `close=60`, `lift=180`, `lift_action_z=0.5`, same two-object manifest, stable-pose cache, random object assignment, yaw randomization, and verified grasp index cache.

## 2026-06-14T21:20:17Z - Verified-schedule state PPO relaunch

Goal:
- Train the state-based multi-object Franka policy after validating that the verified warmstart schedule produces clean reset/perturb/grasp-contact behavior.

Hypothesis:
- PPO should recover from the BC checkpoint and maintain nonzero lift/success when the scripted warmstart uses the verified schedule that physically lifted in video validation, instead of the long-approach gated schedule that disturbed the rod before close/lift.

Change:
- No new source-code changes.
- Training schedule changes relative to failed job `29074553`:
  - `GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS=4`
  - `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS=60`
  - `GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=180`
  - `GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.5`
  - close/lift EE/finger/closed-width gates disabled (`0.0`, `0.0`, `0.0`, `-1.0`)
- Preserve the validated setup: two-object manifest, stable pose cache, `object_asset_assignment=random`, spawn center `(0.05,0)`, XY randomization `0.10`, yaw randomization `180 deg`, verified grasp indices, BC checkpoint, JSONL metrics, and action-prior reward.

Version Control:
- implementation_commit: `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- remote_worktree: `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- changed_files: this worklog only

Command / Job:
- command: `sbatch cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29075315`
- run_name: `franka_multi_state_teacher_7195_96ae_verifiedsched_5c1a3e3_20260614T212017Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29075315.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_96ae_verifiedsched_5c1a3e3_20260614T212017Z`
- expected_success_signal: early JSONL metrics show warmstart close/lift phases, bounded object/contact distances, nonzero lift height/success, and no reward collapse.

Next:
- Submit, record job id/log/run_dir, monitor queue/logs, inspect config and JSONL metrics, then relaunch/tune if abnormal.

Monitor:
- `2026-06-14T21:21Z`: job `29075315` transitioned to RUNNING on `batch-block5-01628`.
- Startup log echoed the intended configuration, including random object assignment, stable pose cache, yaw randomization `180`, verified grasp indices, warmstart `4/60/180`, lift action z `0.5`, disabled extra gates, JSONL metrics enabled, and BC checkpoint `/results/bc/franka_multi_7195_96ae_bc_holdlabel_ep50_21378e9_20260614T1734Z/nn/bc_reference_action_imitation.pth`.
- `2026-06-14T21:24Z`: resolved `params/env.yaml` confirms `robot_base_z=0.47`, random object assignment, stable pose cache, yaw randomization, verified grasp indices, and verified warmstart schedule.
- `2026-06-14T21:30Z`: early rank-0 JSONL metrics:
  - epoch 51: success `0.042`, has_lifted `0.163`, active warmstart success `0.076`, active has_lifted `0.296`; applied warmstart lift rate is `0.0` while reference lift rate is `0.451`, consistent with a first-step logging offset after resume.
  - epoch 52: success `0.0249`, has_lifted `0.149`, applied warmstart lift rate `0.487`, lift success `0.041`, lift has_lifted `0.271`.
  - epoch 53: success `0.0205`, has_lifted `0.150`, applied warmstart lift rate `0.517`, lift success `0.0388`, lift has_lifted `0.285`.
  - current concern: lift phase is wired, but mean lift/finger distance grows (`~0.287 m`) and mean lift height remains low (`~0.017 m` during warmstart lift), so the run needs more epochs to distinguish early-noise from degradation.

Result:
- status: canceled for tuning
- scheduler: `scancel 29075315`; Slurm reported `CANCELLED by 158351`, elapsed `00:19:17`.
- epoch trend through 59:
  - success fell from `0.042` at epoch 51 to `0.00049` by epoch 59.
  - has_lifted stayed around `0.145-0.150`, but mean lift height drifted down to `0.0037`.
  - applied warmstart lift phase was active after epoch 52, so phase wiring is not the blocker.
  - lift-phase finger-center distance stayed large (`~0.22-0.29 m`), meaning many vector envs are not carrying the object cleanly despite the selected contact video passing.
- Revised analysis:
  - The passing contact video selected object `7195ed3346a445448308febe833c180a`.
  - The verified-index cache shows the second object `96ae0ff853734df0b10a827307949c87` had much lower pass count (`7` vs `33`) and larger observed XY drift.
  - Before launching more PPO, validate object `96ae...` explicitly instead of relying on the best-candidate multi-object contact video.

Next:
- Create a `/lustre` single-object debug manifest for `96ae0ff853734df0b10a827307949c87`.
- Run the same reset/perturb/contact video validation for that object only with the verified schedule.
- If object `96ae...` fails or looks marginal, build a more robust multi-object subset or collect stronger verified grasp indices before relaunching PPO.

## 2026-06-14T21:38:00Z - Single-object `96ae` contact validation

Goal:
- Determine whether the weaker second object in the two-object training set can reset, perturb, and grasp cleanly under the verified schedule.

Change:
- Created `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/single_96ae_debug_20260614T2138Z/manifest.json`.
- Container path: `/results/assets/filtered_manifests/single_96ae_debug_20260614T2138Z/manifest.json`.
- Manifest includes only UUID `96ae0ff853734df0b10a827307949c87` and reuses the original `/results` asset root and scale.

Command / Job:
- command: `sbatch cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` on `l401`
- job_id: `1029406`
- run_name: `franka_multi_96ae_verifiedsched_contact_video_5c1a3e3_20260614T214312Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_96ae_verifiedsched_contact_video_5c1a3e3_20260614T214312Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029406.out`
- expected_artifacts: reset/perturb/contact videos and `video_metrics.json`.

Next:
- Submit and inspect the video/metrics before any new PPO launch.

Result:
- status: failed contact validation
- scheduler: `FAILED`, job `1029406`, exit `1:0`, elapsed `00:03:54` on `pool0-00002`.
- artifacts fetched locally under `cluster_results/l401/franka_multi_96ae_verifiedsched_contact_video_5c1a3e3_20260614T214312Z/`.
- encoded videos:
  - `grasp_contact.mp4`: 1280x720, 131 frames, 8.73 s at 15 FPS.
  - `reset_settle.mp4`: 1280x720, 36 frames, 2.40 s at 15 FPS.
  - `perturbation.mp4`: 1280x720, 36 frames, 2.40 s at 15 FPS.
- metrics:
  - reset passed: `object_xy_delta_max=6.65e-05`, `bottom_clearance_min=-1.69e-05`, `done_count=0`.
  - perturbation passed: `object_xy_delta_max=0.0996`, `object_speed_max=0.524`, `object_angular_speed_max=5.00`, `done_count=0`.
  - grasp_contact failed: selected UUID `96ae0ff853734df0b10a827307949c87`, selected sample `905`, max lift `0.0116 m` vs threshold `0.12 m`, finger/object distances remained large, and the object stayed on the table in the video.

Analysis:
- The environment reset, stable pose, perturbation physics, object scale, and table clearance look acceptable for `96ae...`; the failure is specifically the grasp-contact evidence.
- The previous two-object contact video was a false positive for the whole set because the validator selected the best passing env/object (`7195...`) and did not force per-object coverage.
- PPO should not be relaunched with the `7195+96ae` set until `96ae...` has better verified grasps or is replaced.

Next:
- Validate the existing `1d489db9cdc24161a7537926a20bb17b` candidate as a single object using its accepted verified index (`71`).
- If `1d489...` passes reset/perturb/contact visually and by metrics, build a `7195+1d489` training manifest and relaunch PPO with yaw randomization and random per-env object assignment.

## 2026-06-14T21:50:58Z - Single-object `1d489` contact validation

Goal:
- Validate a replacement second object before relaunching multi-object PPO.

Hypothesis:
- Existing verified index `71` for `1d489db9cdc24161a7537926a20bb17b` has repeated lift-success evidence and may provide a cleaner two-object training set than `96ae...`.

Change:
- No source-code changes planned for this attempt.
- Create a `/lustre` single-object manifest for UUID `1d489db9cdc24161a7537926a20bb17b`.
- Reuse accepted verified-index cache `/results/assets/verified_grasp_indices/franka_multi_verified_cache_1d_96ae_2977a39_20260614T1355Z/verified_indices_accepted.json`, which includes `1d489...` index `71`.

Version Control:
- implementation_commit: `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- changed_files: this worklog only

Command / Job:
- command: `sbatch cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` on `l401`
- job_id: `1029407`
- run_name: `franka_multi_1d_verifiedsched_contact_video_5c1a3e3_20260614T2151Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_1d_verifiedsched_contact_video_5c1a3e3_20260614T2151Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029407.out`
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/single_1d_debug_20260614T2151Z/manifest.json`
- expected settings: single-object manifest, stable pose cache, spawn center `(0.05,0)`, XY randomization `0.10`, yaw randomization `180 deg`, verified schedule `approach=4`, `close=60`, `lift=180`, `lift_action_z=0.5`, current-lift gate enabled.

Next:
- Create the manifest, submit the validation, fetch/encode videos, inspect metrics/frames, then either build the replacement two-object training set or collect better grasp indices.

Result:
- status: failed contact validation
- scheduler: `FAILED`, job `1029407`, exit `1:0`, elapsed `00:02:02` on `pool0-00002`.
- artifacts fetched locally under `cluster_results/l401/franka_multi_1d_verifiedsched_contact_video_5c1a3e3_20260614T2151Z/`.
- encoded videos:
  - `grasp_contact.mp4`: 1280x720, 131 frames, 8.73 s at 15 FPS.
  - `reset_settle.mp4`: 1280x720, 36 frames, 2.40 s at 15 FPS.
  - `perturbation.mp4`: 1280x720, 36 frames, 2.40 s at 15 FPS.
- metrics:
  - reset passed as a passive object-stability scenario: `object_xy_delta_max=6.02e-07`, `bottom_clearance_min=-0.00237`, `done_count=0`.
  - perturbation passed: `object_xy_delta_max=0.132`, `object_speed_max=0.479`, `object_angular_speed_max=10.09`; visual motion stayed normal.
  - grasp_contact failed before contact: selected UUID `1d489db9cdc24161a7537926a20bb17b`, selected sample `71`, `selected_reset_success=false`, `target_ee_to_ee_dist=0.223 m`, `warmstart_active_count=0`, and max lift `0.0 m`.

Analysis:
- The object itself is stable and dynamic, but the old verified index is not compatible with the stricter validation/training reset gate (`grasp_prior_reset_max_center_distance_frac=0.30`, candidate count `64`).
- This failure is not a post-contact penetration or lift issue; the hand starts far from the object and never executes warmstart.
- The existing verifier cache was collected with a looser/reset-mismatched configuration, so it can mark indices that the current training/validation path will not actually use.

Next:
- Check `96ae...` with the richer existing cache that contains all three verified indices (`905`, `613`, `813`) instead of only the single accepted index used in the failed video.
- If no existing cache yields a second object that passes, patch/relaunch verified-index collection so it uses the same reset/warmstart settings as training and validation.

## 2026-06-14T22:00:00Z - Single-object `96ae` all-indices contact validation

Goal:
- Determine whether `96ae0ff853734df0b10a827307949c87` can pass contact validation with the fuller existing verified-index set before collecting new indices.

Hypothesis:
- The failed `96ae...` video used only index `905`; allowing the richer cache indices (`905`, `613`, `813`) may let the validator select a clean grasp-contact reset.

Change:
- No source-code changes.
- Reuse the existing `/lustre` single-object `96ae...` manifest.
- Switch verified-index path from the two-object one-index accepted cache to `/results/assets/verified_grasp_indices/franka_multi_verified_cache_1d_96ae_2977a39_20260614T1355Z/verified_indices_accepted.json`.

Command / Job:
- command: `sbatch cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` on `l401`
- job_id: `1029408`
- run_name: `franka_multi_96ae_allindices_contact_video_5c1a3e3_20260614T2200Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_96ae_allindices_contact_video_5c1a3e3_20260614T2200Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029408.out`
- expected settings: same verified contact schedule as the previous runs.

Next:
- Submit and inspect metrics/video before any PPO relaunch.

Result:
- status: failed contact validation
- scheduler: `FAILED`, job `1029408`, exit `1:0`, elapsed `00:05:12`.
- artifacts fetched locally under `cluster_results/l401/franka_multi_96ae_allindices_contact_video_5c1a3e3_20260614T2200Z/`.
- encoded videos:
  - `grasp_contact.mp4`: 1280x720, 131 frames, 8.73 s at 15 FPS.
  - `reset_settle.mp4`: 1280x720, 108 frames, 7.20 s at 15 FPS.
  - `perturbation.mp4`: 1280x720, 48 frames, 3.20 s at 15 FPS.
- metrics:
  - reset passed: `object_xy_delta_max=6.65e-05`, `bottom_clearance_min=-1.70e-05`, `done_count=0`.
  - perturbation passed: `object_xy_delta_max=0.0988`, `object_speed_max=0.531`, `object_angular_speed_max=5.35`, `done_count=0`.
  - grasp_contact failed: `object_xy_delta_max=0.552`, `object_speed_max=3.66`, `object_angular_speed_max=67.0`, `bottom_clearance_min=-0.765`, `done_count=1`, and max lift remained below the acceptance threshold.
- visual inspection:
  - contact montage `cluster_results/l401/franka_multi_96ae_allindices_contact_video_5c1a3e3_20260614T2200Z/contact_montage.jpg` shows the object being kicked/disappearing from the grasp region during contact/lift, not a clean grasp.

Analysis:
- `96ae...` is acceptable for passive reset and perturbation, but not for grasp-contact under the current training reset/warmstart gate.
- This object should be excluded from the next PPO launch until it has newly collected, strictly validated grasp indices.
- Existing verified-index caches are not sufficient because they were collected under settings that are looser or mismatched with the current validation/training path.

Next:
- Add the current-lift warmstart gate to the verified-grasp collector so future caches are generated under the same condition as PPO and contact validation.
- Prepare a small replacement candidate subset from GraspGen UUIDs on `/lustre`, compute stable poses, collect strict verified indices, then validate contact videos before PPO.

## 2026-06-14T22:12:00Z - Verified-grasp collector current-lift gate

Goal:
- Make strict verified-grasp collection match the current multi-object PPO and video-validation reset/warmstart behavior.

Hypothesis:
- Some stale verified-index caches fail because collection does not expose the same `grasp_prior_action_warmstart_require_current_lift_ready` gate that validation/training now use.
- Adding the flag to the collector and wrapper will avoid accepting grasp indices that are only valid for the ideal/static object pose.

Change:
- Add `--grasp_warmstart_require_current_lift_ready` / `--no-grasp_warmstart_require_current_lift_ready` to `collect_franka_multi_object_verified_grasps.py`.
- Apply the flag to `env_cfg.grasp_prior_action_warmstart_require_current_lift_ready` when provided.
- Record the resolved setting in the collector JSON metadata.
- Add `GRASP_WARMSTART_REQUIRE_CURRENT_LIFT_READY` to `cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`.

Version Control:
- base_commit: `5c1a3e3fb79d41615e4512ac173080c47e5a0091`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`
  - `cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`
  - this worklog

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_prepare_graspgen_assets_1gpu.sh cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh`

Result:
- status: local checks passed

Next:
- Commit this collector plumbing, deploy the exact commit to the agent-owned `/lustre` worktree, and run replacement object qualification jobs.

Version Control Update:
- implementation_commit: `087b709ff607c8db54020c98187e4f0f2c333c7f`
- push/pull: pushed to `origin/main`; l401 remote worktree updated with one-off HTTPS fetch because SSH fetch lacked GitHub credentials.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` clean detached HEAD at `087b709ff607c8db54020c98187e4f0f2c333c7f`.

## 2026-06-14T22:09:50Z - Replacement candidate asset prep

Goal:
- Prepare a small replacement object subset on `/lustre` for stable-pose and strict contact qualification before the next PPO launch.

Hypothesis:
- The first three GraspGen train UUIDs already have partial `/lustre` raw/URDF preparation and may yield at least one RLable replacement for the bad `96ae...` / stale `1d489...` candidates.

Change:
- No source changes.
- Use the pushed `087b709` remote worktree.
- Prepare a clean asset subset under `/lustre`, with downloader/cache/temp paths configured by the wrapper to avoid `/home`.

Version Control:
- implementation_commit: `087b709ff607c8db54020c98187e4f0f2c333c7f`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `087b709ff607c8db54020c98187e4f0f2c333c7f`

Command / Job:
- command: `sbatch cluster/sbatch_prepare_graspgen_assets_1gpu.sh` on `l401`
- job_id: `1029411`
- run_name: `franka_multi_graspgen_candidates3_087b709_20260614T220950Z`
- uuids: `bfa718fff3044541a3694863c3bf9c89`, `55cdf60e26db4f3d9f693282404c07f3`, `1c56f9b18a3f459891f6f8b902d192a0`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates3_087b709_20260614T220950Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1029411.out`
- expected artifacts: `manifest.json`, `USD/<uuid>/<uuid>.usd`, `grasp_priors/<uuid>.npz`, `urdf/<uuid>/model.urdf`.

Next:
- Monitor job `1029411`; inspect log and manifest/USD/prior coverage before stable-pose validation.

Result:
- status: passed
- scheduler: `COMPLETED`, job `1029411`, exit `0:0`, elapsed `00:01:49` on `pool0-00002`.
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates3_087b709_20260614T220950Z/manifest.json`
- asset coverage:
  - objects: `3`
  - `missing_usd_count=0`
  - USDs present for `bfa718fff3044541a3694863c3bf9c89`, `55cdf60e26db4f3d9f693282404c07f3`, `1c56f9b18a3f459891f6f8b902d192a0`
  - grasp-prior NPZs present for all three.
- manifest scale check:
  - `bfa718...`: scale `0.3851195`, scaled half-extents roughly `[0.056, 0.034, 0.056]` m.
  - `55cdf...`: scale `0.0014473`, scaled half-extents roughly `[0.042, 0.063, 0.069]` m.
  - `1c56...`: scale `0.0278004`, scaled half-extents roughly `[0.037, 0.032, 0.071]` m.

Analysis:
- The candidate subset is loadable at the asset level: raw OBJ, URDF, USD, grasp-prior NPZ, and manifest paths are complete.
- Next validation must prove stable placements and contact behavior, because asset coverage alone is not sufficient for RL.

Next:
- Run stable-pose placement validation and cache poses for these three objects.

## 2026-06-14T22:12:17Z - Replacement candidate stable-pose validation

Goal:
- Compute trimesh stable poses for the three candidate objects and verify exact placement in Isaac Lab before using them for grasp-prior collection or PPO.

Hypothesis:
- A single high-probability convex-hull stable pose per object should settle with low drift and no table penetration at the default multi-object spawn center.

Change:
- No source changes.
- Use candidate manifest `/results/assets/franka_multi_graspgen_candidates3_087b709_20260614T220950Z/manifest.json`.

Version Control:
- implementation_commit: `087b709ff607c8db54020c98187e4f0f2c333c7f`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `087b709ff607c8db54020c98187e4f0f2c333c7f`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029412`
- run_name: `graspgen_stable_candidates3_087b709_20260614T221217Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates3_087b709_20260614T221217Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029412.out`
- settings: `MAX_OBJECTS=3`, `STABLE_POSE_COUNT=1`, `ROLLOUT_POSE_COUNT=1`, `SETTLE_STEPS=240`, `SETTLED_REPLAY_STEPS=120`, `RENDER_FRAMES=True`, `CAPTURE_INTERVAL=12`.

Next:
- Monitor job `1029412`, inspect `metrics.json`, `settled_pose_cache`, and rendered frames/video.

Result:
- status: passed
- scheduler: `COMPLETED`, job `1029412`, exit `0:0`, elapsed `00:02:30` on `pool0-00002`.
- metrics:
  - `passed=true`
  - `root_xy_delta_max=0.00389 m`
  - `center_xy_delta_max=0.00365 m`
  - `root_z_delta_max=0.00556 m`
  - `bottom_clearance_min=-0.00241 m`
  - `angular_delta_deg_max=6.18`
  - `final_object_speed_max=0.00386 m/s`
  - `final_object_angular_speed_max=0.103 rad/s`
  - `done_count=0`
- stable-pose cache: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates3_087b709_20260614T221217Z/settled_pose_cache`
- fetched artifacts: `cluster_results/l401/graspgen_stable_candidates3_087b709_20260614T221217Z/`
- encoded videos:
  - `stable_pose_env_00.mp4`, `stable_pose_env_01.mp4`, `stable_pose_env_02.mp4`: 1280x720, 21 frames, 1.4 s.
  - `settled_replay_env_00.mp4`, `settled_replay_env_01.mp4`, `settled_replay_env_02.mp4`: 1280x720, 11 frames, 0.73 s.
- visual inspection:
  - `stable_pose_montage.jpg` shows all three objects on the table before and after settled replay, with no visible bouncing, sinking, or edge placement issue.

Analysis:
- The three replacement objects are stable enough for the next strict grasp-prior collection stage.
- This only validates object placement, not grasp contact. Contact/RLability still depends on verified grasp collection and video validation.

Next:
- Launch strict verified-grasp collection with this stable-pose cache, current-lift gate enabled, yaw randomization over 360 degrees, and training-matched reset/warmstart settings.

## 2026-06-14T22:16:14Z - Strict verified-grasp collection for replacement candidates

Goal:
- Find grasp-prior indices that actually lift the settled candidate objects under the same reset/warmstart gates used by PPO and contact validation.

Hypothesis:
- At least one or two of the three stable candidate objects will yield strict verified grasp indices; those objects can replace the failing `96ae...` / stale `1d489...` candidates in the next PPO set.

Change:
- No source changes.
- Use stable-pose cache from `graspgen_stable_candidates3_087b709_20260614T221217Z`.
- Enable current-lift warmstart gating in the collector.

Version Control:
- implementation_commit: `087b709ff607c8db54020c98187e4f0f2c333c7f`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `087b709ff607c8db54020c98187e4f0f2c333c7f`

Command / Job:
- command: `sbatch cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` on `l401`
- job_id: `1029413`
- run_name: `franka_multi_verified_candidates3_strict_087b709_20260614T221614Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates3_strict_087b709_20260614T221614Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029413.out`
- settings:
  - `NUM_ENVS=96`, `MAX_OBJECTS=3`, `OBJECT_ASSET_ASSIGNMENT=round_robin`
  - spawn center `(0.05,0)`, XY randomization `0.10`, yaw randomization `180 deg` (full 360-degree range)
  - stable pose cache enabled, count `1`, allow missing `False`
  - `CYCLES=240`, `MIN_CYCLES=12`, `TARGET_PER_OBJECT=2`, `MAX_INDICES_PER_OBJECT=16`
  - strict thresholds: `MIN_LIFT_HEIGHT=0.12`, `MAX_XY_DELTA=0.06`, `MAX_DONE_COUNT=0`
  - reset/warmstart: attempts `12`, candidates `64`, center fraction `0.30`, IK iterations `128`, approach/close/lift `4/60/180`, prior close width enabled, current-lift gate enabled.

Next:
- Monitor job `1029413`; inspect `verified_indices.json` counts and logs. If all targets are met, run contact videos. If only a subset is good, validate that subset.

Result:
- status: canceled for source-level filter improvement
- scheduler: `CANCELLED`, job `1029413`, elapsed `00:02:16`.
- early counts before cancellation:
  - after cycle 2: all counts `0`.
  - after cycle 3: `bfa718fff3044541a3694863c3bf9c89=1`, others `0`.

Analysis:
- User noted an important prior: the robot should never grasp objects from below.
- Audit showed the existing `grasp_prior_reset_require_topdown=True` path filters by `pregrasp_offset_dir_w.z >= grasp_prior_reset_min_pregrasp_z`.
- For contact-based candidates, the reset code forces the pregrasp offset direction to world-up, which enforces approach from above but does not reject low/underside contact/reference points.
- The partial cache from `1029413` should not be used because it was collected before this stronger underside-grasp filter.

Next:
- Add a config-backed contact/reference height filter, then relaunch verified-grasp collection from a new commit.

## 2026-06-14T22:20:00Z - Reject underside GraspGen contact priors

Goal:
- Encode the “never grasp from below” prior directly in multi-object grasp-prior filtering.

Hypothesis:
- Rejecting contact-based candidates whose contact/reference midpoint is below the current object center will remove underside grasps that can pass an approach-direction-only top-down check.

Change:
- Add multi-object config `grasp_prior_reset_min_contact_height_above_center = 0.0`.
- In `DextrahFrankaMultiObjectGraspEnv`, require `contact_reference_w.z >= object_center_w.z + threshold` when `grasp_prior_reset_require_topdown=True`.
- Apply the same check in the extra reset success/quality mask, so a selected candidate cannot pass final reset-quality gates if it violates the height prior.
- Add `grasp_prior_reset_candidate_contact_height_count` instrumentation to reset buffers and video validation details.
- Record the resolved threshold in verified-grasp collection and contact-video metadata.

Version Control:
- base_commit: `087b709ff607c8db54020c98187e4f0f2c333c7f`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
  - `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  - `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`
  - `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
  - this worklog

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

Result:
- status: local checks passed

Next:
- Commit, push, update the l401 worktree, and relaunch strict verified-grasp collection using the same candidate asset manifest and stable-pose cache.

Version Control Update:
- implementation_commit: `8c478948cd0079534b339308b5288e2ddd857a50`
- push/pull: pushed to `origin/main`; l401 remote worktree updated with one-off HTTPS fetch.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` clean detached HEAD at `8c478948cd0079534b339308b5288e2ddd857a50`.

## 2026-06-14T22:20:58Z - Strict verified-grasp collection with no-underside filter

Goal:
- Regenerate verified grasp indices after adding the contact-height/no-underside prior.

Hypothesis:
- The stricter filter may reduce acceptance rate, but any accepted indices are safer to use for contact validation and PPO because they are not underside contacts.

Change:
- Source commit changed from `087b709` to `8c47894`.
- Use the same candidate asset manifest and stable-pose cache, but a fresh output directory.

Version Control:
- implementation_commit: `8c478948cd0079534b339308b5288e2ddd857a50`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_status: clean detached HEAD at `8c478948cd0079534b339308b5288e2ddd857a50`

Command / Job:
- command: `sbatch cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` on `l401`
- job_id: `1029414`
- run_name: `franka_multi_verified_candidates3_nobelow_8c47894_20260614T222058Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates3_nobelow_8c47894_20260614T222058Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029414.out`
- settings: same as canceled `1029413` except `CYCLES=300`, `SEED=914`, and source includes `grasp_prior_reset_min_contact_height_above_center=0.0`.

Next:
- Monitor job `1029414`; inspect accepted counts and ensure generated metadata records the no-underside threshold.

Result Update:
- status: canceled at cycle 14 after the pattern was clear.
- evidence: `1c56f9b18a3f459891f6f8b902d192a0` reached 2 verified indices (`[540, 539]`) with max lifts around 0.29 m, but `bfa718fff3044541a3694863c3bf9c89` and `55cdf60e26db4f3d9f693282404c07f3` remained at 0 after 448 reset attempts each.
- decision: do not spend the full 300 cycles on this run without gate-failure diagnostics.

Next:
- Add per-object reset/lift/XY/finger/done/candidate-filter diagnostics to the collector and relaunch a short diagnostic collection from a new commit.

## 2026-06-14T22:29:00Z - Verified-grasp gate diagnostics

Goal:
- Determine why two otherwise stable candidate objects are not producing no-underside verified grasp indices.

Hypothesis:
- The zero-count objects may be failing at different gates: no reset candidate after the contact-height filter, IK/quality failure, insufficient lift, excessive XY drift, finger-distance error, or early termination. Per-gate counts should identify which parameter or object-selection step is justified.

Change:
- Add `cycle_stats` to `verified_indices.json` with per-object counts for reset success, quality success, lift/XY/finger/done/success gates, pass counts, and mean candidate filter counts.
- Add candidate filter counts to each accepted sample record.
- No acceptance thresholds or environment dynamics changed.

Version Control:
- base_commit: `8c478948cd0079534b339308b5288e2ddd857a50`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`
  - this worklog

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`
- `git diff --check -- dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`

Next:
- Commit/push the diagnostic collector, update the l401 worktree, and relaunch a shorter diagnostic verified-grasp collection.

Version Control Update:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- push/pull: pushed to `origin/main`; l401 remote worktree updated through HTTPS fallback because SSH auth still fails on the login host.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` clean detached HEAD at `d053e6c41ecba568e602057e20be8492a8fb32d6`.

Command / Job:
- command: `sbatch cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` on `l401`
- job_id: `1029416`
- run_name: `franka_multi_verified_candidates3_diag_d053e6c_20260614T222714Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates3_diag_d053e6c_20260614T222714Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029416.out`
- settings: strict no-underside/current-lift gate, same three candidate objects and stable-pose cache, `CYCLES=24`, `MIN_CYCLES=12`, `TARGET_PER_OBJECT=2`, `NUM_ENVS=96`, `SEED=915`.

Next:
- Monitor `1029416`, then inspect `cycle_stats` to decide whether to tune reset filters or replace objects before PPO.

Result:
- status: diagnostic job failed intentionally because not all target counts were met.
- final counts: `1c56f9b18a3f459891f6f8b902d192a0=3`, `bfa718fff3044541a3694863c3bf9c89=1`, `55cdf60e26db4f3d9f693282404c07f3=0`.
- gate evidence after 24 cycles / 768 attempts per object:
  - `1c56...`: 6 passing observations across 3 indices; 47 lift-capable attempts; reset/quality gates essentially always pass.
  - `bfa718...`: 1 passing observation; many lift-capable attempts but frequent done/instability and very few valid filtered candidates.
  - `55cdf...`: 0 passes and only 8 lift-capable attempts; reject from the immediate PPO set.

Analysis:
- The zero-count object is not blocked by reset/IK; it simply does not lift under the current no-underneath/current-lift warmstart.
- `1c56...` is usable enough for video validation. `bfa718...` is marginal and must be video-validated before inclusion.

Next:
- Create filtered manifests/verified-index JSONs on `/lustre` for `7195...`, `bfa718...`, `1c56...`, and their combined candidate set.
- Launch single-object contact-video validations for `bfa718...` and `1c56...`; keep `7195...` from the previously passing validation.

## 2026-06-14T22:38:07Z - Contact video validation for no-underneath candidates

Goal:
- Verify visually and metrically that `bfa718...` and `1c56...` do not exhibit reset bounce, table penetration, perturbation instability, or weird gripper/object penetration under the no-underneath verified grasp indices.

Change:
- Generated filtered manifests and verified-index files under:
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/qual_7195_bfa_1c56_d053e6c_20260614T223737Z*`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/qual_7195_bfa_1c56_d053e6c_20260614T223737Z*`
- The combined manifest contains `7195...`, `bfa718...`, and `1c56...`; individual manifests force validation of each object.

Command / Job:
- `bfa718...` validation:
  - job_id: `1029417`
  - run_name: `franka_multi_bfa7_nobelow_contact_video_d053e6c_20260614T223807Z`
  - run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_bfa7_nobelow_contact_video_d053e6c_20260614T223807Z`
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029417.out`
- `1c56...` validation:
  - job_id: `1029418`
  - run_name: `franka_multi_1c56_nobelow_contact_video_d053e6c_20260614T223807Z`
  - run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_1c56_nobelow_contact_video_d053e6c_20260614T223807Z`
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029418.out`
- settings: `GRASP_STEPS=260`, warmstart `4/60/180`, current-lift gate enabled, verified indices only, no-underneath reset code at `d053e6c`.

Next:
- Monitor both validation jobs, fetch videos/metrics, inspect frames, then decide the PPO object set.

Result:
- status: both validation jobs failed on `grasp_contact`; reset-settle and perturbation passed for both.
- `bfa718...`: lifted to 0.281 m with low XY drift, but `bottom_clearance_min=-0.00696` and contact montage shows aggressive/unclean contact. Treat as marginal and do not include in PPO yet.
- `1c56...`: reset/perturb stable, but contact video did not lift (`selected_lift_height_max=0.0243`) and the montage shows the object left on the table. Reject from PPO for now.
- viewer artifacts:
  - `cluster_results/l401/franka_multi_bfa7_nobelow_contact_video_d053e6c_20260614T223807Z/grasp_contact.mp4`
  - `cluster_results/l401/franka_multi_1c56_nobelow_contact_video_d053e6c_20260614T223807Z/grasp_contact.mp4`

Analysis:
- Verified-grasp collection alone is insufficient; validation-time settled-object contact exposes failures. Continue object qualification before PPO.

Next:
- Prepare a larger fresh GraspGen candidate subset on `/lustre`, then repeat stable-pose, verified-grasp, and contact-video filters.

## 2026-06-14T22:43:47Z - Prepare 16 new GraspGen candidates

Goal:
- Expand the candidate object pool after `55cdf...`, `bfa718...`, and `1c56...` failed immediate PPO-quality contact validation.

Hypothesis:
- A 16-object shard-local subset should include at least one additional object that passes stable-pose, no-underneath verified-grasp, and contact-video validation while keeping download/extraction overhead bounded.

Command / Job:
- command: `sbatch cluster/sbatch_prepare_graspgen_assets_1gpu.sh` on `l401`
- job_id: `1029419`
- run_name: `franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z`
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z/manifest.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/prepare_graspgen_assets_1029419.out`
- UUIDs: `ca9ede83ef6c4f769fb8ffc000b73ab9 1cdad3cea6f64a0a81e02a7aebf4bdf0 784812e01f71466cbdba96245add0e27 b180b79e98834a83bf6dd1c14a588796 e38f11c29fd946eaa7460d7f43cf5313 eddd78c746734197a81613e10affed89 f4c2fcb0219743c2a717461882df7f7a 7383425b3cd549e98a7ef5a5438c9018 a2a048847e414be6b4aa66fa6d3687e7 6cfe7772bb6f415d88b61135b612b76d 4c656b98557f433499726238dfa8eaa5 e2c1f3a3079f410a90ede41dba8c4b06 da154bb403b64693aa3d76f9a935a5be 834b6b22df6e4925a94b2517201fe702 f34090dec2d845c1b1ec436325f5a56b 04bef8e589524b8c9d7a3bb206b206a8`

Next:
- Monitor job `1029419`; inspect the resulting manifest geometry, then run stable-pose validation on plausible objects.

Result:
- status: passed.
- manifest objects: 16.
- missing USDs: 0.
- selected compact follow-up UUIDs: `1cdad3cea6f64a0a81e02a7aebf4bdf0`, `784812e01f71466cbdba96245add0e27`, `e38f11c29fd946eaa7460d7f43cf5313`, `eddd78c746734197a81613e10affed89`, `f4c2fcb0219743c2a717461882df7f7a`, `4c656b98557f433499726238dfa8eaa5`, `e2c1f3a3079f410a90ede41dba8c4b06`, `04bef8e589524b8c9d7a3bb206b206a8`.

Analysis:
- Avoided very large/elongated candidates from the 16-object manifest before running simulation.

Next:
- Run stable-pose validation for the compact subset.

## 2026-06-14T22:46:53Z - Stable-pose validation for 8 compact shard-2 candidates

Goal:
- Confirm the eight compact candidate objects can be placed at precomputed stable poses without table penetration, bounce, or significant drift.

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029420`
- run_name: `graspgen_stable_candidates8_shard2_d053e6c_20260614T224653Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates8_shard2_d053e6c_20260614T224653Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029420.out`
- manifest: `/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z/manifest.json`
- settings: stable-pose count 1, one rollout pose, 240 settle steps, 80 settled replay steps, render frames enabled.

Next:
- Monitor `1029420`; if stable metrics pass, use its settled-pose cache for verified-grasp collection.

Result:
- status: failed before simulation.
- evidence: Slurm job `1029420` exited `FAILED` after 41 seconds; no `metrics.json` was written.
- error: `ValueError: Requested UUIDs are not present in manifest`, where the missing item was the entire space-separated UUID list as one string.

Analysis:
- The stable-pose validator expects `--object_uuids` as a comma-separated string; the wrapper intentionally forwards `OBJECT_UUIDS` as one argument. The launch used spaces, so the parser treated all eight UUIDs as one impossible UUID. This was a launch formatting error, not a physics/object-stability failure.

Next:
- Relaunch the same stable-pose validation with comma-separated `OBJECT_UUIDS`.

## 2026-06-14T22:50:00Z - Relaunch stable-pose validation with comma-separated UUIDs

Goal:
- Run the same eight-object compact shard-2 stable-pose validation after fixing the launch-time UUID delimiter.

Hypothesis:
- Passing the UUID list as comma-separated values will allow the validator to select the intended eight manifest records and proceed to actual stable-pose physics validation.

Version Control:
- agent_id: multiobject-bc-fallback-20260614-d5e8b27
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` at `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029421`
- run_name: `graspgen_stable_candidates8_shard2_comma_d053e6c_20260614T225000Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates8_shard2_comma_d053e6c_20260614T225000Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029421.out`
- manifest: `/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z/manifest.json`
- UUID delimiter: comma-separated `OBJECT_UUIDS`

Next:
- Monitor `1029421`; inspect `metrics.json`, logs, and rendered videos before using any object for verified-grasp collection.

Result:
- status: failed before rollout.
- evidence: the corrected UUID list was accepted and the script computed stable poses for the first object, then `parse_env_cfg()` failed.
- error: `gymnasium.error.NameNotFound: Environment Isaac-Franka-MultiObject-Grasp-Direct doesn't exist. Did you mean: Dextrah-Franka-Multi-Object-Grasp?`

Analysis:
- I overrode the wrapper default task with the wrong Isaac Lab registry name. The correct registered task in `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/gym_setup.py` and the validator default is `Dextrah-Franka-Multi-Object-Grasp`.

Next:
- Relaunch with the wrapper default task name and the same comma-separated UUID list.

## 2026-06-14T22:52:00Z - Relaunch stable-pose validation with correct task registry

Goal:
- Run actual stable-pose physics validation for the eight compact shard-2 objects after fixing both launch argument issues.

Hypothesis:
- With `TASK=Dextrah-Franka-Multi-Object-Grasp` and comma-separated `OBJECT_UUIDS`, the job should reach Isaac Lab environment construction and produce stable-pose metrics/videos.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` at `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029422`
- run_name: `graspgen_stable_candidates8_shard2_fixed_d053e6c_20260614T225200Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates8_shard2_fixed_d053e6c_20260614T225200Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029422.out`
- manifest: `/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z/manifest.json`

Next:
- Monitor `1029422`; inspect `metrics.json`, log warnings/errors, and rendered stable-pose videos.

Result:
- status: completed but only validated one object.
- metrics: `passed=True`; one-object summary had `root_xy_delta_max=0.000325`, `center_xy_delta_max=0.000316`, `bottom_clearance_min=-0.001153`, `final_object_speed_max=0.00449`, and `done_count=0`.
- evidence: the logged command contains only `--object_uuids 1cdad3cea6f64a0a81e02a7aebf4bdf0`.

Analysis:
- Slurm `--export` is comma-delimited, so passing comma-separated UUIDs inside `--export=...OBJECT_UUIDS=...` truncated the variable at the first UUID. The one-object result is valid evidence for `1cdad...`, but not for the full eight-object shard.

Next:
- Avoid `OBJECT_UUIDS` for this step by writing an explicit filtered eight-object manifest and launching stable-pose validation with `MAX_OBJECTS=8`.

## 2026-06-14T22:54:30Z - Build filtered manifest for eight-object stable validation

Goal:
- Remove Slurm export delimiter ambiguity by materializing a manifest containing only the intended eight compact shard-2 objects.

Command / Job:
- command: remote `python3` JSON filter on `l401`
- source_manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z/manifest.json`
- filtered_manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/stable_candidates8_shard2_d053e6c_20260614T225430Z/manifest.json`
- object_count: 8

Next:
- Launch stable-pose validation from the filtered manifest with no `OBJECT_UUIDS`.

## 2026-06-14T22:55:00Z - Stable-pose validation from filtered eight-object manifest

Goal:
- Validate all eight compact shard-2 candidates for stable reset and settled replay without relying on `OBJECT_UUIDS`.

Hypothesis:
- The filtered manifest will make the validator instantiate eight envs and produce per-object stability metrics/videos for the intended candidates.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` at `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029423`
- run_name: `graspgen_stable_candidates8_filtered_d053e6c_20260614T225500Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates8_filtered_d053e6c_20260614T225500Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029423.out`
- manifest: `/results/assets/filtered_manifests/stable_candidates8_shard2_d053e6c_20260614T225430Z/manifest.json`

Next:
- Monitor `1029423`, inspect metrics and rendered artifacts, then use only passing objects for verified-grasp collection.

Result:
- status: failed before rollout.
- error: `FileNotFoundError: Missing raw OBJ for 1cdad...: /results/assets/filtered_manifests/stable_candidates8_shard2_d053e6c_20260614T225430Z/raw_objaverse/...`

Analysis:
- The filtered manifest copied `asset_root: "."` from the source manifest. That made relative `raw_object_path` and USD paths resolve against the filtered-manifest directory, not the original prepared asset directory.

Next:
- Write a corrected filtered manifest with `asset_root=/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z`, then relaunch.

## 2026-06-14T22:57:00Z - Build asset-rooted filtered manifest

Goal:
- Keep the eight-object filtered selection while resolving raw OBJ/USD paths against the original prepared asset directory.

Command / Job:
- command: remote `python3` JSON filter on `l401`
- filtered_manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/stable_candidates8_shard2_assetroot_d053e6c_20260614T225700Z/manifest.json`
- container_manifest: `/results/assets/filtered_manifests/stable_candidates8_shard2_assetroot_d053e6c_20260614T225700Z/manifest.json`
- asset_root: `/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z`
- object_count: 8

Next:
- Relaunch stable-pose validation from this asset-rooted manifest.

## 2026-06-14T22:58:00Z - Stable-pose validation from asset-rooted filtered manifest

Goal:
- Validate all eight compact shard-2 candidates with paths resolving back to the original prepared asset directory.

Hypothesis:
- The asset-rooted filtered manifest should let stable-pose computation load every raw OBJ and then run the eight-env Isaac Lab rollout.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27` at `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029424`
- run_name: `graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029424.out`
- manifest: `/results/assets/filtered_manifests/stable_candidates8_shard2_assetroot_d053e6c_20260614T225700Z/manifest.json`

Next:
- Monitor `1029424`; inspect metrics and videos before collector launch.

Result:
- status: passed stable-pose/reset validation for eight envs.
- metrics: `num_envs=8`, `passed=True`, cache files written for all eight objects.
- stable summary: `root_xy_delta_max=0.00138`, `center_xy_delta_max=0.00625`, `bottom_clearance_min=-0.00179`, `angular_delta_deg_max=5.63`, `final_object_speed_max=0.00448`.
- settled replay summary: `root_xy_delta_max=0.00000246`, `center_xy_delta_max=0.00000421`, `bottom_clearance_min=-0.00179`, `angular_delta_deg_max=0.079`, `final_object_speed_max=0.00448`.
- artifacts fetched:
  - `cluster_results/l401/graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z/stable_pose.mp4`
  - `cluster_results/l401/graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z/settled_replay.mp4`
  - `cluster_results/l401/graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z/stable_pose_env_final_montage.jpg`
  - `cluster_results/l401/graspgen_stable_candidates8_assetroot_d053e6c_20260614T225800Z/settled_replay_env_final_montage.jpg`

Analysis:
- Visual montages show all objects placed on the table without obvious penetration or off-table placement.
- Object `f4c2fcb0219743c2a717461882df7f7a` physically settled, but it produced passive `task_done_count=238` during stable rollout and `78` during settled replay. Exclude it from RL qualification because it starts in a terminal/success-like state and could confuse training.

Next:
- Build a seven-object manifest excluding `f4c2...` and run the no-underneath/current-lift verified-grasp collector using the settled-pose cache from this run.

## 2026-06-14T23:01:00Z - Build seven-object verified-grasp manifest

Goal:
- Prepare a collector manifest containing only stable, non-terminal candidates from shard 2.

Command / Job:
- command: remote `python3` JSON filter on `l401`
- filtered_manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/verify_candidates7_no_f4_d053e6c_20260614T230100Z/manifest.json`
- container_manifest: `/results/assets/filtered_manifests/verify_candidates7_no_f4_d053e6c_20260614T230100Z/manifest.json`
- asset_root: `/results/assets/franka_multi_graspgen_candidates16_shard2_d053e6c_20260614T224347Z`
- object_count: 7
- excluded: `f4c2fcb0219743c2a717461882df7f7a`

Next:
- Launch verified-grasp collection with stable poses, 360-degree yaw randomization, and no-underneath grasp filtering.

## 2026-06-14T23:02:00Z - Seven-object no-underneath verified-grasp collection

Goal:
- Find dynamically verified GraspGen indices for the seven stable/non-terminal shard-2 candidates before contact-video validation.

Hypothesis:
- Stable-pose reset plus the no-underneath topdown/contact-height gate and current-lift readiness should identify at least one clean liftable prior for some of the seven objects.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` on `l401`
- job_id: `1029444`
- run_name: `franka_multi_verified_candidates7_nobelow_d053e6c_20260614T230200Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates7_nobelow_d053e6c_20260614T230200Z`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates7_nobelow_d053e6c_20260614T230200Z/verified_indices.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029444.out`
- key settings: `NUM_ENVS=112`, `MAX_OBJECTS=7`, `round_robin`, spawn center `(0.05, 0.0)`, xy randomization `0.10`, yaw randomization `180.0`, stable pose cache from `1029424`, `CYCLES=48`, `TARGET_PER_OBJECT=1`, current-lift readiness enabled.

Next:
- Monitor `1029444`; inspect verified counts and diagnostics, then run contact-video validation only for objects with accepted indices.

Result:
- status: wrapper failed as expected because not all seven objects reached `TARGET_PER_OBJECT=1`, but useful verified indices were written.
- final counts: `e38f11c29fd946eaa7460d7f43cf5313=7`, `4c656b98557f433499726238dfa8eaa5=2`, all other five objects `0`.
- diagnostics: each object had 768 observed resets; `e38f...` had 45 pass observations and `4c656...` had 2 pass observations.
- failure reason: `Missing target counts` for `04bef...`, `1cdad...`, `784812...`, `e2c1...`, and `eddd...`.

Analysis:
- The failed Slurm state is a target-count failure, not a runtime/environment failure. Only `e38f...` and `4c656...` are worth contact-video validation from this shard.
- The other five stable objects are not PPO-ready under the current no-underneath/current-lift gate and should remain out of the training manifest.

Next:
- Split the collector output into one-object manifests and verified-index files for `e38f...` and `4c656...`, then run contact video validation for each.

## 2026-06-14T23:30:00Z - Build contact-validation inputs for two verified objects

Goal:
- Prepare per-object video validation inputs for the only shard-2 objects with verified no-underneath/current-lift grasp indices.

Command / Job:
- command: remote `python3` JSON split on `l401`
- objects:
  - `e38f11c29fd946eaa7460d7f43cf5313`, indices `[657, 39, 35, 652, 968, 73, 628]`
  - `4c656b98557f433499726238dfa8eaa5`, indices `[642, 494]`
- manifest_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/contact_candidates_e38f_4c656_d053e6c_20260614T233000Z`
- verified_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/contact_candidates_e38f_4c656_d053e6c_20260614T233000Z`

Next:
- Launch one contact-video validation job per object and inspect the resulting videos/metrics.

## 2026-06-14T23:31:00Z - Contact-video validation for two verified shard-2 objects

Goal:
- Verify that the dynamically accepted grasp indices produce physically clean reset, perturbation, and grasp-contact videos before adding either object to PPO.

Command / Job:
- `e38f11c29fd946eaa7460d7f43cf5313`
  - job_id: `1029447`
  - run_name: `franka_multi_e38f_contact_video_d053e6c_20260614T233100Z`
  - run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_e38f_contact_video_d053e6c_20260614T233100Z`
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029447.out`
- `4c656b98557f433499726238dfa8eaa5`
  - job_id: `1029448`
  - run_name: `franka_multi_4c65_contact_video_d053e6c_20260614T233100Z`
  - run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_4c65_contact_video_d053e6c_20260614T233100Z`
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029448.out`
- key settings: `NUM_ENVS=32`, stable pose cache from `1029424`, verified indices only, spawn center `(0.05, 0.0)`, xy randomization `0.10`, yaw randomization `180.0`, `GRASP_STEPS=260`, warmstart `4/60/180`, current-lift readiness enabled.

Next:
- Monitor jobs `1029447` and `1029448`; fetch videos, encode mp4s, inspect metrics and frame montages.

Result:
- status: both contact validations failed on `grasp_contact`.
- `e38f...`: reset-settle and perturbation passed, but grasp-contact lift was only `0.00399 m`; montage shows the object remains on the table.
- `4c656...`: reset-settle and perturbation passed, and lift reached `0.1996 m`, but `selected_object_xy_delta_max=0.8474 m` with `selected_done_count=222`; montage shows the object carried far out of the task region / out of view.
- artifacts fetched and encoded:
  - `cluster_results/l401/franka_multi_e38f_contact_video_d053e6c_20260614T233100Z/grasp_contact.mp4`
  - `cluster_results/l401/franka_multi_e38f_contact_video_d053e6c_20260614T233100Z/contact_montage.jpg`
  - `cluster_results/l401/franka_multi_4c65_contact_video_d053e6c_20260614T233100Z/grasp_contact.mp4`
  - `cluster_results/l401/franka_multi_4c65_contact_video_d053e6c_20260614T233100Z/contact_montage.jpg`

Analysis:
- Neither shard-2 object is PPO-ready. Keep the validation gate strict and search another object shard rather than adding weak objects to training.

Next:
- Prepare a fresh, larger GraspGen candidate shard and repeat geometry, stable-pose, verified-grasp, and contact-video filtering.

## 2026-06-14T23:40:00Z - Prepare 32 fresh shard-3 GraspGen candidates

Goal:
- Expand the candidate pool after shard-2 produced no new contact-validated objects.

Hypothesis:
- A larger explicit 32-object subset from unused GraspGen shard 3 increases the chance of finding at least one additional object that passes stable reset, no-underneath verified-grasp collection, and contact-video validation.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`

Command / Job:
- command: `sbatch cluster/sbatch_prepare_graspgen_assets_1gpu.sh` on `l401`
- job_id: `1029449`
- run_name: `franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z`
- output_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z`
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z/manifest.json`
- UUIDs: `747fe7a49dae4ef6b067ec8916c808e2 c351adf1cc9e4e7f83f24c0c7317e68d 9d9557c5f3af4639bcacf468e4e5182a 66d208d29503450ca28c0152864b7379 753efdb4234545a698343661c59664a4 f601cd38f655447da2e83e3d9f5beb80 4f4fe076fe624d2a8f198588c64fc6cb f71a628ddc1d45529b2dde4066f9ca71 0b07d4714a544a7fbe3a145ccda8bf03 7d4406b23e5e4525a7afe7f3b25d141f 6154520a963a4bb099642482a26aa9d3 b8a7cc0278304cf0882ddf25040af3d9 3693fa4414f64a41b04be4aa70e35448 2241e09cc3ad40a0a6da20cd76d7baa7 8fbc2087b1254376b9afec839f59d584 82f4d273bc2240c49f70fec7b6bc5fee c28358d1992547099ead51a462562030 7d840006d0184ef496c9860765023f52 6992dae82b99461a9a43c2debd84cbd5 ca8d526966a74d5ab796092e6e4531a8 b5d22010f2ab4123a72d7b2a7d6643d7 884defbca8c8473695e5a5420ca89de4 85c3d3b9cfd64c108dc548e525052c4e 59b9bb5fd55a4cc5ab71f24fcca26f8f 168ca4d0cad641f797fa4edba00164a5 29f7d53eae024e4d86d0d1360d32fa5d 75c058a8028340e1adbdc9ea2dfda9d4 9e4f6c7c49214be1b98cf180e1c432ac f3512126d36a4630893585f1ee2e44d2 6d19454feff8409ea697102783c17bc8 8d89bff741d1486398a3a1bab4626abe b87a65917e494aa4b306aeb6ee961182`

Next:
- Monitor `1029449`; inspect manifest geometry and choose compact candidates for stable-pose validation.

Result:
- status: passed.
- manifest: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z/manifest.json`
- objects: `32`
- missing USD count: `0`
- storage check: wrapper cache/home/temp paths stayed under `/lustre` mounts and `/results`; no `/home` download path was used.

Analysis:
- Raw OBJ bounds are not directly comparable across assets; candidate size must be evaluated using `bounds * scale`. After scaling, 18 candidates are within roughly 12 cm half-extent and are small enough for stable-pose/contact validation.

Next:
- Build an asset-rooted filtered manifest for the 18 scaled-compact candidates and run rendered stable-pose validation.

## 2026-06-14T23:47:00Z - Stable-pose validation for 18 shard-3 compact candidates

Goal:
- Validate stable initialization for a new compact 18-object shard before no-underneath verified-grasp collection.

Hypothesis:
- Filtering by dataset-scaled bounds should avoid table-edge/base-clearance failures while retaining enough shape diversity to find at least one additional contact-valid object.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: `d053e6c41ecba568e602057e20be8492a8fb32d6`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029450`
- run_name: `graspgen_stable_candidates18_shard3_d053e6c_20260614T234900Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates18_shard3_d053e6c_20260614T234900Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029450.out`
- filtered_manifest_host: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/stable_candidates18_shard3_assetroot_d053e6c_20260614T234700Z/manifest.json`
- filtered_manifest_container: `/results/assets/filtered_manifests/stable_candidates18_shard3_assetroot_d053e6c_20260614T234700Z/manifest.json`
- asset_root: `/results/assets/franka_multi_graspgen_candidates32_shard3_d053e6c_20260614T234000Z`
- object_count: `18`
- key settings: `MAX_OBJECTS=18`, `STABLE_POSE_COUNT=1`, `ROLLOUT_POSE_COUNT=1`, `SETTLE_STEPS=240`, `SETTLED_REPLAY_STEPS=80`, rendered frames enabled, `MAX_ANGULAR_DRIFT_DEG=8.0`, `MIN_BOTTOM_CLEARANCE=-0.005`, `MAX_FINAL_SPEED=0.03`.

Next:
- Launch stable-pose validation on `l401`, monitor logs/metrics, fetch videos, and exclude any unstable/passive-terminal objects before verified-grasp collection.

Result:
- status: failed aggregate stable-pose metrics, but produced usable per-object diagnostics and stable/settled pose caches.
- job state: `FAILED`, exit `1:0`, elapsed `00:02:02`
- summary: `root_xy_delta_max=0.02309`, `center_xy_delta_max=0.00943`, `angular_delta_deg_max=31.68`, `bottom_clearance_min=-0.00435`, `final_object_speed_max=0.0145`, `final_object_angular_speed_max=0.8822`, `done_count=714`.
- outliers:
  - `3693fa4414f64a41b04be4aa70e35448`: high angular drift (`31.68 deg` initial settle, `18.07 deg` replay).
  - `f71a628ddc1d45529b2dde4066f9ca71`: excessive initial root XY drift (`0.02309 m`).
  - `f601cd38f655447da2e83e3d9f5beb80`, `6992dae82b99461a9a43c2debd84cbd5`, `884defbca8c8473695e5a5420ca89de4`: passive task termination counts during settle/replay.
- kept candidates with low drift and zero passive done count: `4f4fe076fe624d2a8f198588c64fc6cb`, `c28358d1992547099ead51a462562030`, `b87a65917e494aa4b306aeb6ee961182`, `0b07d4714a544a7fbe3a145ccda8bf03`, `b8a7cc0278304cf0882ddf25040af3d9`, `85c3d3b9cfd64c108dc548e525052c4e`, `b5d22010f2ab4123a72d7b2a7d6643d7`, `f3512126d36a4630893585f1ee2e44d2`, `66d208d29503450ca28c0152864b7379`, `75c058a8028340e1adbdc9ea2dfda9d4`, `7d840006d0184ef496c9860765023f52`, `ca8d526966a74d5ab796092e6e4531a8`, `168ca4d0cad641f797fa4edba00164a5`.

Analysis:
- The failure is caused by a small set of object-specific stability/termination outliers, not a manifest/container issue. The next step is to validate a reduced 13-object manifest rather than relaxing thresholds.

Next:
- Build a reduced 13-object manifest and rerun rendered stable-pose validation. If it passes visually/numerically, run no-underneath verified-grasp collection on those 13 objects.

## 2026-06-14T23:57:00Z - Reduced 13-object shard-3 stable-pose validation

Goal:
- Revalidate only the shard-3 objects that had low drift and zero passive task terminations in the 18-object pass.

Hypothesis:
- Removing the five outliers should make the aggregate stable-pose metrics pass without weakening thresholds.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`

Command / Job:
- command: `sbatch cluster/sbatch_validate_graspgen_stable_pose_resets_1gpu.sh` on `l401`
- job_id: `1029451`
- run_name: `graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_graspgen_stable_pose_1029451.out`
- filtered_manifest_host: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/stable_candidates13_shard3_assetroot_d053e6c_20260614T235600Z/manifest.json`
- filtered_manifest_container: `/results/assets/filtered_manifests/stable_candidates13_shard3_assetroot_d053e6c_20260614T235600Z/manifest.json`
- object_count: `13`
- key settings: `MAX_OBJECTS=13`, `STABLE_POSE_COUNT=1`, `ROLLOUT_POSE_COUNT=1`, `SETTLE_STEPS=240`, `SETTLED_REPLAY_STEPS=80`, rendered frames enabled, `MAX_ANGULAR_DRIFT_DEG=8.0`, `MIN_BOTTOM_CLEARANCE=-0.005`, `MAX_FINAL_SPEED=0.03`.

Next:
- Monitor `1029451`, inspect metrics and rendered artifacts, then either run no-underneath verified-grasp collection or filter again.

Result:
- status: passed.
- scheduler: `COMPLETED`, exit `0:0`, elapsed `00:01:47`.
- initial settle summary: `root_xy_delta_max=0.00666`, `center_xy_delta_max=0.00460`, `angular_delta_deg_max=6.26`, `bottom_clearance_min=-0.00435`, `final_object_speed_max=0.00526`, `final_object_angular_speed_max=0.129`, `done_count=0`.
- settled replay summary: `root_xy_delta_max=2.35e-05`, `center_xy_delta_max=7.70e-06`, `angular_delta_deg_max=0.079`, `bottom_clearance_min=-0.00435`, `final_object_speed_max=0.00528`, `done_count=0`.
- stable pose cache: `/results/validations/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/settled_pose_cache`
- local artifacts:
  - `cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/stable_pose_grid.mp4`
  - `cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/settled_replay_grid.mp4`
  - `cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/stable_pose_env_final_grid.jpg`
  - `cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/settled_replay_env_final_grid.jpg`
- viewer links:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613/cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/stable_pose_grid.mp4`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613/cluster_results/l401/graspgen_stable_candidates13_shard3_d053e6c_20260614T235700Z/settled_replay_grid.mp4`

Analysis:
- The reduced set is stable enough for the next gate. Visual inspection of the 13-env grid is consistent with the metrics: objects remain on the tabletop, do not visibly bounce away, and settled replay is effectively static.

Next:
- Launch no-underneath/current-lift verified-grasp collection on the 13 stable objects with per-env object/pose/yaw randomization.

## 2026-06-15T00:00:00Z - No-underneath verified-grasp collection for 13 stable shard-3 objects

Goal:
- Find dynamically verified GraspGen indices for the 13 stable shard-3 objects before contact-video validation.

Hypothesis:
- The top-down/no-underneath prior plus current-lift readiness will reject underside/invalid reset candidates early and identify any object-specific priors that can actually lift without excessive XY drift or terminations.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`

Command / Job:
- command: `sbatch cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh` on `l401`
- job_id: `1029452`
- run_name: `franka_multi_verified_candidates13_shard3_nobelow_d053e6c_20260615T000000Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates13_shard3_nobelow_d053e6c_20260615T000000Z`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates13_shard3_nobelow_d053e6c_20260615T000000Z/verified_indices.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029452.out`
- key settings: `NUM_ENVS=104`, `MAX_OBJECTS=13`, `round_robin`, spawn center `(0.05, 0.0)`, xy randomization `0.10`, yaw randomization `180.0`, stable pose cache from `1029451`, `CYCLES=48`, `TARGET_PER_OBJECT=1`, `SCORE_STEPS=260`, `MIN_LIFT_HEIGHT=0.12`, `MAX_XY_DELTA=0.06`, `MAX_DONE_COUNT=0`.
- top-down prior: `GRASP_RESET_REQUIRE_TOPDOWN=True`, `GRASP_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_RESET_CANDIDATE_COUNT=64`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`.
- warmstart: prior close width enabled, `min_close_width=0.002`, `approach/close/lift=4/60/180`, current-lift readiness enabled.

Next:
- Monitor `1029452`; inspect verified counts/diagnostics and run contact-video validation only for objects with accepted indices.

Result:
- status: completed with useful output, but wrapper exited nonzero because not all 13 objects met the per-object target.
- scheduler: `FAILED`, exit `1:0`, elapsed `00:26:30`.
- output JSON: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/franka_multi_verified_candidates13_shard3_nobelow_d053e6c_20260615T000000Z/verified_indices.json`
- nonzero no-underneath verified counts:
  - `66d208d29503450ca28c0152864b7379`: `16`
  - `7d840006d0184ef496c9860765023f52`: `10`
  - `0b07d4714a544a7fbe3a145ccda8bf03`: `7`
  - `b87a65917e494aa4b306aeb6ee961182`: `3`
  - `168ca4d0cad641f797fa4edba00164a5`: `1`
  - `f3512126d36a4630893585f1ee2e44d2`: `1`
  - `75c058a8028340e1adbdc9ea2dfda9d4`: `1`
  - `b5d22010f2ab4123a72d7b2a7d6643d7`: `1`
- zero-count objects: `4f4fe076fe624d2a8f198588c64fc6cb`, `c28358d1992547099ead51a462562030`, `b8a7cc0278304cf0882ddf25040af3d9`, `85c3d3b9cfd64c108dc548e525052c4e`, `ca8d526966a74d5ab796092e6e4531a8`.

Analysis:
- The no-underneath/top-down gate is active and diagnostic counters show every kept candidate satisfies `candidate_topdown_count` gating; the wrapper failure is expected because five stable objects still found no dynamically verified grasp within 48 cycles.
- The strongest candidates for real video inspection are `66d...`, `7d840...`, `0b07...`, and `b87...`; these have enough accepted indices to test whether the filtered prior actually produces clean contact rollouts after stable-object settling.

Next:
- Build one-object manifests and one-object verified-index JSONs for the four strongest candidates, then run contact-video validation with stable poses, yaw randomization, current-lift readiness, and the no-underneath reset gate.

## 2026-06-15T00:24:00Z - One-object no-underneath contact-video validation jobs

Goal:
- Produce isolated reset/perturb/grasp-contact videos for the strongest no-underneath candidates before launching PPO.

Hypothesis:
- If at least one new GraspGen object passes the rendered contact gate, it can be combined with the previously validated `7195ed3346a445448308febe833c180a` object for the first multi-object PPO run.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`

Command / Job:
- command: `sbatch cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` on `l401`
- shared input root:
  - manifest root: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/filtered_manifests/contact_candidates4_shard3_nobelow_d053e6c41_20260615T002400Z`
  - verified root: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/contact_candidates4_shard3_nobelow_d053e6c41_20260615T002400Z`
- jobs:
  - `1029453`: `franka_multi_contact_66d208_nobelow_d053e6c41_20260615T002400Z`
  - `1029454`: `franka_multi_contact_7d8400_nobelow_d053e6c41_20260615T002400Z`
  - `1029455`: `franka_multi_contact_0b07d4_nobelow_d053e6c41_20260615T002400Z`
  - `1029456`: `franka_multi_contact_b87a65_nobelow_d053e6c41_20260615T002400Z`
- key settings: `NUM_ENVS=32`, `MAX_OBJECTS=1`, spawn center `(0.05, 0.0)`, xy randomization `0.10`, yaw randomization `180.0`, stable pose cache from `1029451`, `OBJECT_STABLE_POSE_RANDOMIZE=False`, `GRASP_STEPS=260`, `GRASP_CONTACT_SCORE_STEPS=260`.
- top-down prior: `GRASP_RESET_REQUIRE_TOPDOWN=True`, `GRASP_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_RESET_CANDIDATE_COUNT=64`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.30`, `GRASP_PREGRASP_OFFSET=0.03`.
- warmstart: prior close width enabled, `min_close_width=0.002`, `approach/close/lift=4/60/180`, current-lift readiness enabled.

Next:
- Monitor `1029453`-`1029456`, fetch videos/metrics, inspect reset stability, perturbation motion, and grasp-contact geometry. Relaunch/tune if artifacts show penetration, reset jumps, or unstable object dynamics.
## 2026-06-15T00:34:20Z - Two-object no-underneath PPO smoke launch

Goal:
- Launch a short A100 PPO smoke on a multi-object set that has per-object rendered contact validation, before scaling to a longer teacher run.

Hypothesis:
- Replacing the older `7195+96ae` set with individually contact-passing `7195+b87` should avoid the previous false-positive multi-object validation failure mode, where the video validator selected only the best object.
- The no-underneath prior should remain active through training because `grasp_prior_reset_require_topdown=True`, `grasp_prior_reset_min_pregrasp_z=0.45`, and the environment default contact-height gate rejects contact references below the object center.

Change:
- Created generated `/lustre` training bundle `train2_7195_b87_nobelow_d053e6c_20260615T0045Z`.
- Manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json`.
- Verified indices: `/results/assets/verified_grasp_indices/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/verified_indices.json`.
- Stable-pose cache: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`.
- Included objects: `7195ed3346a445448308febe833c180a` with one verified index, and `b87a65917e494aa4b306aeb6ee961182` with three verified indices.

Version Control:
- agent_id: `merge-dp-rgb-main-20260613`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613`
- branch: `main`
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: clean detached HEAD at `d053e6c41ecba568e602057e20be8492a8fb32d6`
- changed_files: generated `/lustre` manifest/cache/verified-index artifacts and this worklog

Command / Job:
- command: `sbatch --export=ALL,... cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29080060`
- run_name: `franka_multi_state_teacher_7195_b87_nobelow_smoke_d053e6c_20260615T0052Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080060.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_smoke_d053e6c_20260615T0052Z`
- key settings: `NUM_ENVS=1024`, `MAX_ITERATIONS=3`, `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, stable poses enabled, verified grasp indices enabled, warmstart `4/60/180`, lift action z `0.50`, action-prior reward enabled.

Result:
- status: canceled for relaunch
- scheduler: ran on `batch-block5-00452`; canceled after `00:03:07`.
- evidence: resolved config was written and confirmed `robot_base_z=0.47`, random object assignment, yaw `180.0`, stable-pose cache, verified-index path, and top-down reset settings.
- reason: stdout stopped advancing after Isaac scene collision-filter warnings; compute-node inspection showed all ranks alive, about 3.5 GB allocated per GPU, 0% GPU utilization, and many Torch Inductor compile workers. For smoke validation, this looked like CUDA-graph/compile startup stall rather than an environment-path failure.

Next:
- Relaunch the same smoke with `USE_CUDA_GRAPH=False`, then monitor startup, resolved configs, JSONL metrics, checkpoints, and failure patterns.
- If the no-CUDA-graph smoke passes, launch the longer A100 teacher run from the same bundle and commit.

## 2026-06-15T00:37:48Z - Two-object no-underneath PPO smoke relaunch without CUDA graph

Goal:
- Verify the same two-object PPO smoke after disabling CUDA graph to avoid the Torch Inductor startup stall observed in job `29080060`.

Hypothesis:
- The environment/model/training path should start cleanly with the same manifest and prior settings when CUDA graph capture/compile is disabled.

Change:
- No source changes.
- Relaunch only changed `USE_CUDA_GRAPH=False` and the run name.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- changed_files: this worklog

Command / Job:
- command: `sbatch --export=ALL,...,USE_CUDA_GRAPH=False cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29080124`
- run_name: `franka_multi_state_teacher_7195_b87_nobelow_smoke_nocg_d053e6c_20260615T0039Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080124.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_smoke_nocg_d053e6c_20260615T0039Z`
- key settings: same two-object bundle, `NUM_ENVS=1024`, `MAX_ITERATIONS=3`, random object assignment, yaw `180.0`, stable poses enabled, verified grasp indices enabled, warmstart `4/60/180`, lift action z `0.50`, action-prior reward enabled.

Result:
- status: passed smoke
- scheduler: `COMPLETED`, exit `0:0`, elapsed `00:04:29`, node `batch-block5-01636`.
- startup: all 8 ranks created scenes in about 125 seconds, started simulation in about 5 seconds, entered rl_games training, and wrote checkpoints/events/JSONL metrics.
- metrics from rank 0:
  - epoch 1/2/3 reward checkpoints: `784.49`, `1000.93`, `1011.06`
  - `cube_grasp_prior_candidate_topdown_count=64.0` and `cube_grasp_prior_candidate_valid_count=64.0`
  - `cube_grasp_prior_reset_success_rate`: `0.541`, `0.490`, `0.475`
  - `cube_action_warmstart_lift_has_lifted_rate`: `0.681` at epoch 2 and `0.661` at epoch 3
  - `cube_has_lifted_rate`: `0.354`, `0.323`, `0.310`
  - `cube_success_rate`: `0.067`, `0.038`, `0.024`
  - `cube_finger_table_clearance_violation=0.0` and `cube_table_clearance_penalty=0.0`
- artifacts:
  - metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_smoke_nocg_d053e6c_20260615T0039Z/metrics/direct_info_rank_0.jsonl`
  - checkpoints: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_smoke_nocg_d053e6c_20260615T0039Z/nn/`
  - configs: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_smoke_nocg_d053e6c_20260615T0039Z/params/`

Next:
- Launch a bounded longer A100 run with the same two-object no-underneath bundle, `USE_CUDA_GRAPH=False`, random object assignment, and 360-degree yaw randomization.
- Watch whether the nonzero lift/success signals trend upward. If success plateaus, debug reset IK success first because candidates are valid/top-down but only about half the envs pass the IK reset tolerance.

## 2026-06-15T00:43:15Z - Two-object no-underneath PPO train60 launch

Goal:
- Run the first real bounded teacher-training curve for the two contact-passing GraspGen objects under the parallel multi-object environment.

Hypothesis:
- The smoke-proven no-CUDA-graph setup should train for 60 PPO epochs inside the A100 short-job limit and reveal whether the policy learns from the top-down grasp-prior reset/warmstart despite about 50% reset IK quality success.

Change:
- No source changes.
- Scaled from `MAX_ITERATIONS=3` to `MAX_ITERATIONS=60`, kept `NUM_ENVS=1024`, 8 GPUs, `USE_CUDA_GRAPH=False`, and the same two-object generated bundle.

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- remote_commit/status: clean detached HEAD at `d053e6c41ecba568e602057e20be8492a8fb32d6`
- changed_files: this worklog

Command / Job:
- command: `sbatch --export=ALL,...,MAX_ITERATIONS=60,USE_CUDA_GRAPH=False cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29080618`
- run_name: `franka_multi_state_teacher_7195_b87_nobelow_train60_nocg_d053e6c_20260615T0043Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080618.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train60_nocg_d053e6c_20260615T0043Z`
- key settings: `OBJECT_ASSET_ASSIGNMENT=random`, `OBJECT_SPAWN_YAW_RANDOMIZATION_DEG=180.0`, stable pose cache and verified indices enabled, `GRASP_PRIOR_RESET_REQUIRE_TOPDOWN=True`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`, action warmstart `4/60/180`, lift action z `0.50`, prior reward enabled, `SAVE_FREQUENCY=5`.

Result:
- status: canceled and relaunched
- reason: the wrapper ignores `RUN_NAME` and uses `FULL_EXPERIMENT_NAME` to set `DEXTRAH_RUN_NAME`; job `29080618` therefore fell back to `slurm_29080618`. It was canceled after `00:00:47` before useful training output, to avoid confusing run directories.
- relaunch job_id: `29080630`
- relaunch command: same settings, but with `FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_nobelow_train60_nocg_d053e6c_20260615T0043Z`
- relaunch result: `COMPLETED`, exit `0:0`, elapsed `00:19:07`.
- artifacts:
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080630.out`
  - metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train60_nocg_d053e6c_20260615T0043Z/metrics/direct_info_rank_0.jsonl`
  - checkpoints: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train60_nocg_d053e6c_20260615T0043Z/nn/last_dextrah_franka_multi_object_grasp_ep_60_rew_1003.60443.pth`
- final metrics:
  - rows/epochs: `60`
  - max `cube_success_rate`: `0.077`
  - last-10 mean `cube_success_rate`: `0.0256`
  - last-10 mean `cube_lift_height`: `0.0122 m`
  - epoch 60: `cube_grasp_prior_reset_success_rate=0.473`, `cube_action_warmstart_active_rate=0.253`, `cube_action_warmstart_lift_has_lifted_rate=0.754`, `cube_has_lifted_rate=0.314`, `cube_success_rate=0.026`, `cube_policy_action_z=-0.052`, `cube_policy_gripper_action=-0.289`
  - table/finger safety: table-penetration penalties are zero or tiny (`<= 6e-6` near epochs 58-60); no evidence of table-stuck objects in training metrics.

Next:
- Treat `train60_nocg` as an environment/training-mechanics pass but learning-quality failure. Do not add more objects from this checkpoint.
- Relaunch a tuned run with the same objects/env but stronger action-prior, lift, success, and post-lift hold rewards; the reward code shows `postlift_*` action shaping is currently disabled by default, which matches the observed policy drift toward non-positive z actions after the warmstart phase.

## 2026-06-15T01:05:24Z - Two-object strong-prior train80 launch

Goal:
- Test whether the same validated multi-object environment can produce a materially better teacher curve after strengthening the grasp-prior imitation and post-lift hold incentives.

Hypothesis:
- The previous run proved the environment is parallel-RL compatible but showed policy drift after warmstart. Increasing action-prior reward and post-lift close/lift shaping should push policy z action positive and raise mean lift height/success beyond reset-cycle spikes.

Change:
- No source changes.
- Same two-object bundle, random object assignment, yaw randomization, stable poses, no-underneath top-down grasp filter, and CUDA graph disabled.
- Training/config changes from `train60_nocg`:
  - `MAX_ITERATIONS=80`
  - `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=20.0` from `2.0`
  - warmstart close/lift steps `80/360` from `60/180`
  - warmstart lift action z `0.75` from `0.50`
  - reset attempts `2`, IK iterations `128`, pos/rot tolerances `0.075/0.65`
  - lift/height/success rewards `25/8/50`
  - prelift action shaping: close `0.8`, lift `3.0`, descend penalty `-3.0`
  - postlift shaping enabled: close `0.5`, open penalty `-0.8`, lift `2.0`, descend penalty `-3.0`, gate height `0.02`

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- changed_files: this worklog

Command / Job:
- command: `sbatch --export=ALL,...,MAX_ITERATIONS=80,GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=20.0,... cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29080886`
- run_name: `franka_multi_state_teacher_7195_b87_nobelow_train80_strongprior_d053e6c_20260615T0105Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080886.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train80_strongprior_d053e6c_20260615T0105Z`

Result:
- status: canceled after plateau
- scheduler: canceled at `00:23:28` elapsed after metrics through epoch `38`.
- artifacts:
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29080886.out`
  - metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train80_strongprior_d053e6c_20260615T0105Z/metrics/direct_info_rank_0.jsonl`
  - checkpoints through epoch 35 in `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train80_strongprior_d053e6c_20260615T0105Z/nn/`
- metrics:
  - improved reset and action behavior: `cube_grasp_prior_reset_success_rate` often `0.52-0.58`, policy z action became positive (`~0.08-0.31` after early epochs), gripper action closed strongly (`~-0.4 to -0.5`).
  - still weak task success: max `cube_success_rate=0.0898`, last-10 mean around epoch 38 `0.0229`, last-10 mean lift height `0.0142 m`.
  - detailed warmstart lift-phase metrics show likely grasp/contact failure, not just policy reward failure: lift-phase `has_lifted_rate` was often `0.58-0.63`, but `lift_success_rate` stayed `0.014-0.042`, `lift_lift_height` stayed around `0.018-0.030 m`, and gripper width stayed around `0.014-0.016 m`.
  - table safety remained clean; table penalties were zero or negligible.

Next:
- Relaunch a targeted force-close diagnostic: keep the same environment/reward settings, but set `GRASP_PRIOR_ACTION_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False` and command a near-closed gripper width. Hypothesis: the prior-derived close width is too gentle for these irregular objects in PhysX, so the gripper moves upward without enough normal force to carry the object.

## 2026-06-15T01:32:16Z - Two-object force-close train50 launch

Goal:
- Test whether the current low success is caused by the grasp prior close-width target being too gentle to generate enough contact force on irregular GraspGen objects.

Hypothesis:
- `train80_strongprior` produced reasonable policy z/gripper actions, but the object was usually not carried upward. Forcing the warmstart close target near fully closed should reduce gripper width during the scripted lift phase and materially improve lift success if contact force is the limiting factor.

Change:
- No source changes.
- Same two-object bundle, random object assignment, yaw randomization, stable poses, no-underneath top-down grasp filter, and CUDA graph disabled.
- Same strong-prior reward/warmstart settings as `train80_strongprior`, except:
  - `MAX_ITERATIONS=50`
  - `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.002`
  - `GRASP_PRIOR_ACTION_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`
  - `GRASP_PRIOR_ACTION_WARMSTART_MIN_CLOSE_WIDTH=0.0`

Version Control:
- implementation_commit: `d053e6c41ecba568e602057e20be8492a8fb32d6`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-bc-fallback-20260614-d5e8b27`
- changed_files: this worklog

Command / Job:
- command: `sbatch --export=ALL,...,MAX_ITERATIONS=50,GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.002,GRASP_PRIOR_ACTION_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False cluster/sbatch_train_teacher_8gpu.sh` on `a1001`
- job_id: `29081633`
- run_name: `franka_multi_state_teacher_7195_b87_nobelow_train50_forceclose_d053e6c_20260615T0130Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29081633.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train50_forceclose_d053e6c_20260615T0130Z`

Result:
- status: canceled after diagnostic plateau.
- startup config confirmed: object spawn center `(0.05, 0.0)`, xy randomization `0.10`, yaw randomization `180.0`, stable pose cache enabled, and force-close overrides active.
- scheduler: canceled at `00:16:27` elapsed after checkpointing epoch `25`; rank-0 metrics reached epoch `26`.
- artifacts:
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29081633.out`
  - metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train50_forceclose_d053e6c_20260615T0130Z/metrics/direct_info_rank_0.jsonl`
  - checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_train50_forceclose_d053e6c_20260615T0130Z/nn/last_dextrah_franka_multi_object_grasp_ep_25_rew_2818.4521.pth`
- metrics:
  - close override was applied correctly: `cube_action_warmstart_close_width_target=0.002`, and lift-phase gripper width stayed around `0.0020-0.0022 m` instead of the prior `0.014-0.016 m`.
  - task success did not improve: max `cube_success_rate=0.0918`, last-10 mean at cancel `0.0269`, epoch 25 `cube_success_rate=0.0186`.
  - lift/carry remained the limiting behavior: success requires `cube_lift_height >= 0.12 m`, but last-10 mean lift height was about `0.0161 m`, and lift-phase finger-center distance often grew to `0.3-0.4 m`.
  - policy did learn stronger close and some positive z by later epochs (`epoch 25 policy_z=0.101`, `policy_gripper=-0.609`), but the object still did not stay with the gripper.

Next:
- Do not keep sweeping reward weights alone. Patch diagnostics to log per-object outcomes and expose object physics overrides, then relaunch a friction/contact diagnostic with higher object friction/contact solver settings.

## 2026-06-15T01:47:18Z - Per-object metrics and object-physics override patch

Goal:
- Make the next training/debug launch distinguish per-object failures and test whether contact/friction settings are the reason force-closed grasps still slip.

Hypothesis:
- The environment, reset, object scale, yaw randomization, and no-underneath prior are working, but the Franka/object contact is too weak for irregular GraspGen objects under the current object friction/solver defaults.

Change:
- Added per-object scalar logging for small multi-object runs (`num_unique_objects <= 16`): object-specific success, lift, xy error, finger distance, grasp-prior reset success, and warmstart lift metrics.
- Exposed multi-object physics overrides in `cluster/sbatch_train_teacher_8gpu.sh`: density, static/dynamic friction, contact/rest offset, solver iterations, damping, and max depenetration velocity.
- Added the same object physics override plumbing to `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh` and `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py` so rendered contact diagnostics can match training physics.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`

Next:
- Commit and deploy this patch to the A100 agent worktree, then launch a short two-object diagnostic with high object friction and the same force-close warmstart. If lift height/success improves, keep the physics change and continue training; if not, render a matching contact video and inspect object-by-object metrics.
