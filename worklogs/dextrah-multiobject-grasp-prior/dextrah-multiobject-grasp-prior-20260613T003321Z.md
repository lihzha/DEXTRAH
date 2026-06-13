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
