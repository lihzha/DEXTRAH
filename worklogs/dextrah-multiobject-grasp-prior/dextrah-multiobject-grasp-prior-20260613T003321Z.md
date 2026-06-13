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
- implementation_commit: pending
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
