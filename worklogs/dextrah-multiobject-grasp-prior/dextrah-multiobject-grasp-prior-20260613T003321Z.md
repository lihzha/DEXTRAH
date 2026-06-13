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
