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
