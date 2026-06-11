# Worklog - franka-cube-grasp-prior / franka-cube-dp-bc-warmstart

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- created: 2026-06-11T18:39:21Z

## 2026-06-11T11:40:53-07:00 - initial plan / official DP verification

Goal:
- Explore Alternative B: a behavior-cloning warm start from offline
  GraspGenX/cuRobo Franka cube trajectories using Diffusion Policy, kept
  separate from reset-prior and tracking-reward branches.

Hypothesis:
- A low-dimensional Diffusion Policy can imitate planner-generated
  approach-to-pregrasp state-action windows if actions are converted to the
  same DEXTRAH 7D relative EE pose plus gripper convention used by PPO.
- Starting from the official `real-stanford/diffusion_policy` low-dimensional
  config/workspace conventions avoids a misleading simplified reimplementation.

Change:
- Planned source edits only in new BC/Diffusion Policy files:
  - `dextrah_lab/offline_dp_bc/` for trajectory conversion, dataset metadata,
    relative EE action derivation, and smoke validation helpers.
  - `dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml` as a minimal
    official-convention Diffusion Policy config template.
  - optional tests under `tests/` only if the repo has suitable test layout.
- Do not edit Worker A reset-prior env files or Worker B tracking-reward files.
- Do not launch full training. Local import/config/dataset-shape and a tiny
  synthetic one-step smoke are allowed if dependencies permit.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a, local implementation checkpoint only unless requested
- changed_files: owned worklog pending
- remote_commit/status: n/a/local env

Command / Job:
- command: `web search/open for https://github.com/real-stanford/diffusion_policy and https://diffusion-policy.cs.columbia.edu/; local repo inspection pending`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: planned config/smoke output only

Result:
- status: in_progress
- metrics/artifacts: none yet
- key evidence: official project page links the Sim & Real repo; official repo
  README documents hydra `train.py`, low_dim experiment data/configs, logs, and
  checkpoint layout.

Analysis:
- The action target should be relative task-space deltas, not raw planner joint
  commands, to bridge cleanly into the existing DEXTRAH PPO controller. The
  first dataset should label approach-to-pregrasp and keep close/lift optional
  because close/lift may require contact-state and gripper semantics not present
  in all planner traces.

Next:
- Inspect DEXTRAH action/controller scaling and current package layout.
- Add converter/config/smoke modules, validate on a synthetic trajectory, then
  record final commit and remaining integration questions.

## 2026-06-11T11:49:04-07:00 - offline DP BC converter checkpoint

Goal:
- Add a bounded, official-Diffusion-Policy-compatible starting point for
  Franka cube BC warm-start from GraspGenX/cuRobo trajectories.

Hypothesis:
- Converting task-space waypoints to DEXTRAH normalized relative EE actions
  plus raw gripper commands is the least-mismatch action target for later RL.
- A compact low-dimensional observation schema is enough for initial BC
  validation, but it is not a direct PPO weight-initialization path because PPO
  currently consumes the full 72D environment observation.

Change:
- Added `dextrah_lab/offline_dp_bc/action_conversion.py` with NumPy versions of
  the Isaac Lab relative pose convention:
  - position delta in meters divided by `(0.060, 0.060, 0.045)`;
  - rotation delta as axis-angle from `q_target * inv(q_current)` divided by
    `(0.25, 0.25, 0.30)`;
  - gripper action `-1` closes and `+1` opens, matching DEXTRAH reward/control.
- Added `trajectory_conversion.py` to convert explicit task-space NPZ files or
  GraspGenX trajectory JSON files. JSON conversion uses explicit EE poses when
  present, or optional GraspGenX FK from `joint_position` plus the DEXTRAH
  `panda_hand` EE offset.
- Added `dp_dataset.py` with an NPZ-backed official Diffusion Policy
  `BaseLowdimDataset` adapter and a no-op lowdim runner for offline BC.
- Added `validate_dataset_smoke.py` for synthetic dataset shape/action replay
  validation.
- Added `config/franka_cube_lowdim_dp.yaml` using official
  `real-stanford/diffusion_policy` low-dimensional Hydra target conventions.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a local checkpoint
- changed_files:
  - `dextrah_lab/offline_dp_bc/__init__.py`
  - `dextrah_lab/offline_dp_bc/action_conversion.py`
  - `dextrah_lab/offline_dp_bc/trajectory_conversion.py`
  - `dextrah_lab/offline_dp_bc/dp_dataset.py`
  - `dextrah_lab/offline_dp_bc/validate_dataset_smoke.py`
  - `dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: n/a/local env

Command / Job:
- command: `python3 -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: syntax compile passed.
- key evidence: no py_compile errors.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --synthetic-output /tmp/franka_cube_dp_bc_synthetic_smoke.npz`
- job_id: n/a
- run_dir: /tmp
- logs: terminal
- artifacts:
  - `/tmp/franka_cube_dp_bc_synthetic_smoke.npz`
  - `/tmp/franka_cube_dp_bc_synthetic_smoke.npz.metadata.json`

Result:
- status: passed
- metrics/artifacts: sample obs shape `[8, 21]`, sample action shape `[8, 7]`,
  dataset steps `38`, episodes `2`, first real-step position replay error
  `0.0`.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.trajectory_conversion /tmp/franka_cube_dp_bc_taskspace_input.npz --output /tmp/franka_cube_dp_bc_converted_cli.npz --input-format npz --phase-set approach_pregrasp && PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset /tmp/franka_cube_dp_bc_converted_cli.npz`
- job_id: n/a
- run_dir: /tmp
- logs: terminal
- artifacts:
  - `/tmp/franka_cube_dp_bc_converted_cli.npz`
  - `/tmp/franka_cube_dp_bc_converted_cli.npz.metadata.json`

Result:
- status: passed
- metrics/artifacts: converted one episode, `12` steps, obs dim `21`, action
  dim `7`; smoke sample obs `[8, 21]`, action `[8, 7]`, replay error `0.0`.
- key evidence: printed `FRANKA_CUBE_DP_BC_CONVERTED` and
  `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python - <<'PY' ... yaml.safe_load('dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml') ... PY`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: YAML parsed with `task_name=franka_cube_lowdim`, `obs_dim=21`, `action_dim=7`.
- key evidence: printed `yaml ok franka_cube_lowdim 21 7`.

Analysis:
- I chose approach-to-pregrasp as the default phase set. It avoids teaching
  contact and lift behavior before the planner-to-sim contact semantics are
  validated. The converter exposes `approach_grasp`, `full_pick_lift`, and
  explicit phase filters for later ablations.
- A Diffusion Policy checkpoint from this template should first be used through
  an evaluation/fine-tuning wrapper, or distilled into the PPO actor, because a
  diffusion denoising UNet cannot be loaded directly into the current rl_games
  Gaussian PPO network and the compact 21D BC observation is not the full 72D
  PPO observation.
- Official Diffusion Policy forward/training-step validation was not run
  locally because neither `diffusion_policy` nor `omegaconf` is installed in
  the local shell or GraspGenX venv. The config and dataset targets are written
  for the official repo environment.

Next:
- Commit this coherent checkpoint.
- Before any real BC run, generate or locate real Franka cube GraspGenX/cuRobo
  trajectories with explicit EE poses or provide GraspGenX FK inputs, then run
  the converter and an official Diffusion Policy one-step debug train in the
  official DP environment.

## 2026-06-11T11:50:48-07:00 - final handoff

Goal:
- Record final checkpoint state for Worker C handoff.

Hypothesis:
- The branch is ready for orchestrator review because source, config, local
  shape validation, and the worklog are committed, with no active local or
  cluster jobs.

Change:
- Source checkpoint committed.
- Updated this final handoff entry after commit so the worklog names the code
  implementation commit explicitly.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: ca1bcae19a07b45d530860bfc12169ea3efc8ebd
- push/pull: not pushed; local agent branch checkpoint
- changed_files: owned worklog final entry only since implementation commit
- remote_commit/status: n/a/local env

Command / Job:
- command: `git status --short --branch`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: after implementation commit, only the owned worklog final
  entry was modified.
- key evidence: no active local process, Slurm job, or remote submitter was
  launched by this worker.

Analysis:
- The useful next validation is not more local synthetic testing; it is running
  the official Diffusion Policy debug train against a real converted Franka
  cube dataset in an environment where `real-stanford/diffusion_policy` is
  installed.

Next:
- Commit this log-only handoff entry.
- Orchestrator can inspect/cherry-pick the branch; no Worker C job monitoring
  remains.

## 2026-06-11T12:02:11-07:00 - official DP validation plan

Goal:
- Move beyond synthetic DEXTRAH-only smoke tests and validate the Franka cube
  BC path against the official `real-stanford/diffusion_policy` implementation.

Hypothesis:
- The DEXTRAH lowdim dataset adapter and config will need small compatibility
  fixes once exercised inside the official workspace, especially around Hydra
  config loading, runner assertions, normalizer imports, and output/log paths.
- A local isolated official-DP venv can reuse the existing GraspGenX venv's
  Torch/NumPy packages via a venv-local `.pth` bridge, avoiding a full CUDA
  PyTorch reinstall while keeping official-DP dependencies outside DEXTRAH.

Change:
- Planned external-only setup:
  - clone official repo to `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`;
  - create official-DP validation venv under
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv`;
  - keep generated debug dataset/logs under
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts`.
- Planned DEXTRAH edits only if official validation exposes issues in our
  adapter/config or if an eval-wrapper/distillation stub is practical.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: a21857f58ce211cb67f3174e56bb49c5f8f64ae8
- implementation_commit: pending
- push/pull: will push branch after coherent checkpoint
- changed_files: worklog plan only so far
- remote_commit/status: n/a/local env

Command / Job:
- command: `git clone https://github.com/real-stanford/diffusion_policy ...; uv venv ...; uv pip install ...; tiny official-DP debug train/forward`
- job_id: n/a
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart`
- logs: planned under `artifacts/logs`
- artifacts: planned converted dataset, resolved config, official-DP debug output

Result:
- status: in_progress
- metrics/artifacts: none yet
- key evidence: n/a

Analysis:
- No full BC training will be launched. Stop condition for this attempt is
  official config/dataset/model construction plus one tiny train/forward step,
  or a precise external dependency blocker with command output and paths.

Next:
- Materialize official repo and environment, generate a tiny converted dataset,
  run official workspace, patch DEXTRAH if the failure is ours, then commit and
  push.

## 2026-06-11T12:14:08-07:00 - official DP one-step train and bridge smoke

Goal:
- Validate Worker C's Franka cube lowdim BC path with the official
  `real-stanford/diffusion_policy` code, then make the PPO handoff concrete
  enough for eval-wrapper/distillation follow-up.

Hypothesis:
- Official DP compatibility is now mostly a dependency/config issue, not a
  dataset-shape issue. The generated checkpoint still cannot initialize
  rl_games PPO directly because the official DP policy is a denoising UNet over
  action sequences with a compact 21D observation history, while rl_games PPO is
  a 72D-observation Gaussian actor-critic MLP.

Change:
- Materialized the official repository externally, not vendored into DEXTRAH:
  - source URL: `https://github.com/real-stanford/diffusion_policy`
  - project page verified: `https://diffusion-policy.cs.columbia.edu/`
  - local path:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
  - official commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- Built an isolated official-DP validation venv at
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv`, with
  the GraspGenX venv Torch packages exposed through a venv-local `.pth`.
  Relevant resolved versions:
  `torch==2.6.0`, `numpy==1.26.4`, `hydra-core==1.3.2`,
  `omegaconf==2.3.0`, `diffusers==0.11.1`,
  `huggingface-hub==0.10.1`, `transformers==4.25.1`,
  `wandb==0.13.3`, `zarr==2.18.3`, `numcodecs==0.12.1`,
  `pandas==2.2.2`, `einops==0.4.1`, `dill==0.3.5.1`.
- Added `dextrah_lab/offline_dp_bc/ppo_bridge.py`:
  - extracts the 21D DP lowdim observation from the Franka cube 72D PPO
    observation using the env's actual observation concatenation;
  - keeps the DP `n_obs_steps` history for inference;
  - provides a lowdim-to-PPO embedding helper for bridge tests and future
    distillation data generation;
  - exposes `predict_action_from_ppo_obs()` for eval wrappers, explicitly not
    for direct PPO weight initialization.
- Added `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py` to
  load an official DP checkpoint and query it through the PPO bridge.
- Updated `dextrah_lab/offline_dp_bc/__init__.py` exports.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: a21857f58ce211cb67f3174e56bb49c5f8f64ae8
- implementation_commit: 59e562501f84224808b589f45839dbdbb124c398
- push/pull: branch push boundary; final pushed commit reported in the
  orchestrator/final response
- changed_files:
  - `dextrah_lab/offline_dp_bc/__init__.py`
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: pending

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: all Worker C offline BC modules compile.
- key evidence: command exited 0.

Command / Job:
- command: bridge round-trip smoke with NumPy and torch PPO observations
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: extracted lowdim shape `(3, 21)`, embedded PPO shape
  `(3, 72)`, history shape `(3, 2, 21)`.
- key evidence: printed `ppo_bridge ok ...`.

Command / Job:
- command: official import smoke for
  `diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace`,
  `diffusion_policy.dataset.base_dataset`, DEXTRAH adapter, and checkpoint
  smoke script.
- job_id: n/a
- run_dir: local worktree with external official repo on `PYTHONPATH`
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: official workspace and DEXTRAH adapter import together.
- key evidence: printed `official imports ok`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.trajectory_conversion "$art/datasets/franka_cube_taskspace_debug_input.npz" --output "$art/datasets/franka_cube_lowdim_debug.npz" --input-format npz --phase-set approach_pregrasp`
- job_id: n/a
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/converter_debug_current.log`
- artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_lowdim_debug.npz`

Result:
- status: passed
- metrics/artifacts: one approach/pregrasp debug episode, `24` steps,
  `obs_dim=21`, `action_dim=7`.
- key evidence: printed `FRANKA_CUBE_DP_BC_CONVERTED`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$art/datasets/franka_cube_lowdim_debug.npz"`
- job_id: n/a
- run_dir: external artifacts directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/dextrah_dataset_smoke_current.log`
- artifacts: converted dataset plus metadata JSON

Result:
- status: passed
- metrics/artifacts: `sample_obs_shape=[8, 21]`,
  `sample_action_shape=[8, 7]`, `num_train_samples=24`,
  first-step position replay error `0.0`, official DP import visible.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: official one-step debug train from the external official repo:
  `"$venv/bin/python" train.py --config-dir "$dex/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$art/datasets/franka_cube_lowdim_debug.npz" training.device=cpu training.max_train_steps=1 training.max_val_steps=1 training.num_epochs=1 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir="$out"`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_120953_current`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_debug_train_current.log`
  and the run's `logs.json.txt`
- artifacts:
  `.hydra/config.yaml`, `.hydra/overrides.yaml`, `train.log`,
  `checkpoints/latest.ckpt`,
  `checkpoints/epoch=0000-test_mean_score=0.000.ckpt`, W&B offline run.

Result:
- status: passed
- metrics/artifacts: official UNet parameters `1.662478e+07`; one training
  step logged `train_loss=1.1275699138641357`, `lr=1e-6`,
  `test/mean_score=0.0`, `train_action_mse_error=0.7768738865852356`.
  Two checkpoints were produced, each about `254M`.
- key evidence: official W&B run finished successfully; `logs.json.txt`
  contains two JSON records for global step `0`.

Command / Job:
- command: checkpoint bridge smoke:
  `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint "$run_dir/checkpoints/latest.ckpt" --dataset "$art/datasets/franka_cube_lowdim_debug.npz" --device cpu --batch-size 2 --num-inference-steps 2`
- job_id: n/a
- run_dir: external official-DP debug run
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_checkpoint_smoke_current.log`
- artifacts: uses `latest.ckpt`; no new training artifact

Result:
- status: passed
- metrics/artifacts: loaded `TrainDiffusionUnetLowdimWorkspace` and
  `DiffusionUnetLowdimPolicy`, lowdim sequence shape `[2, 2, 21]`,
  PPO observation shape `[2, 72]`, direct official action shape `[2, 8, 7]`,
  bridge first-action shape `[2, 7]`, all finite.
- key evidence: printed `FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED`.

Command / Job:
- command: dataset/checkpoint metadata probe
- job_id: n/a
- run_dir: external artifacts directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_metadata_current.log`
- artifacts: none beyond logs

Result:
- status: passed after adjusting the probe to official `LinearNormalizer`
  state-dict APIs.
- metrics/artifacts: dataset `obs_shape=[24, 21]`, `action_shape=[24, 7]`,
  `train_samples=24`, `val_samples=0` because this bounded debug dataset has
  one episode; checkpoint state contains both `model` and `ema_model`;
  normalizer has 12 parameter/stat keys for `obs` and `action`.
- key evidence: printed `FRANKA_CUBE_DP_BC_METADATA`.

Analysis:
- Official implementation validation is now achieved for config parsing,
  dataset construction, normalizer construction, model construction, one
  bounded train step, checkpoint save, checkpoint load, and bridge inference.
- The one-episode debug dataset is intentionally too small to assess BC
  quality and produces no validation split. That is acceptable for this
  milestone but not for BC evaluation. Next dataset generation should use
  multiple real GraspGenX/cuRobo rollouts with varied cube poses and include
  a held-out split.
- The debug action range is nearly constant because the synthetic waypoints are
  a straight approach segment. A meaningful BC smoke should include multiple
  approach directions and, once contact semantics are validated, separate
  approach-only vs approach+close+lift ablations.
- PPO bridge decision: do not direct-load DP weights into rl_games. Use either
  (1) a DP eval wrapper that extracts the 21D lowdim observation from the 72D
  env observation and sends the first denoised action to the existing 7D IK
  controller, or (2) distill DP actions into the 72D-observation PPO actor by
  collecting `obs72 -> action7` targets from the DP teacher. PPO fine-tuning
  should then initialize from the distilled actor or run RL with the DP wrapper
  as a scripted teacher/curriculum, not by loading the DP checkpoint into
  rl_games.
- No local/cluster full BC or RL training was launched. No active jobs remain.

Next:
- Commit and push this coherent official-validation checkpoint.
- Next Worker C loop should generate a multi-episode converted dataset from
  real GraspGenX/cuRobo traces, run a tiny official DP train with a validation
  split, then choose between DP eval-wrapper rollouts in Isaac Lab or
  distillation into the rl_games PPO actor.

## 2026-06-11T12:22:40-07:00 - grasp-library geometric BC smoke plan

Goal:
- Continue the BC warm-start loop after official-DP validation by creating a
  multi-episode dataset that exercises validation splits and varied cube poses.

Hypothesis:
- No real Franka cube cuRobo trajectory artifacts are currently present in the
  local Worker C workspace, Worker B trajectory-tracking worktree, or shared
  local results. Worker A's cube GraspGenX artifact is a grasp library, not a
  time-indexed trajectory. A clearly labeled geometric approach generator from
  that grasp library can still test official DP mechanics on varied
  multi-episode data while preserving the cuRobo-data blocker.

Change:
- Planned new script:
  `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`.
- The script will read a GraspGenX cube grasp-library NPZ with object-local
  grasps, sample cube poses from the current Franka cube reset range, transform
  grasp/tool poses into the DEXTRAH EE frame using the `panda_hand` plus
  `0.1034 m` EE offset convention, interpolate approach-to-pregrasp waypoints,
  and write the same lowdim dataset schema used by official DP.
- This is intentionally marked `curobo_validated=false`; it is a bridge smoke,
  not final offline BC data.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 1fad16fa6b4b9eacbe1edf67ca8153ff399694ad
- implementation_commit: pending
- push/pull: pending after validation
- changed_files: owned worklog plan only so far
- remote_commit/status: origin/codex/franka-cube-diffusion-policy-bc currently at
  `1fad16fa6b4b9eacbe1edf67ca8153ff399694ad`

Command / Job:
- command: locate artifacts under `/home/lzha/code/local_results`,
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`, and
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- job_id: n/a
- run_dir: local filesystems
- logs: terminal
- artifacts: discovered Worker A grasp library
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz`

Result:
- status: in_progress
- metrics/artifacts: grasp library has `32` object-frame grasps,
  `gripper_name=franka_panda`, `tool_frame=panda_hand`, `cube_size_m=0.06`,
  and `grasp_to_tool_transform`; no cube cuRobo trajectory JSON/NPZ found.

Analysis:
- This generator should not be used to claim cuRobo trajectory BC success.
  It is useful for testing official-DP training and PPO bridge mechanics with
  multiple episodes before real cube planner traces are available.

Next:
- Implement the generator, run DEXTRAH dataset smoke and a bounded official DP
  debug train with a validation split, inspect logs/metadata/checkpoint, then
  commit and push if coherent.

## 2026-06-11T12:30:21-07:00 - grasp-library geometric BC smoke validation

Goal:
- Exercise official Diffusion Policy on a multi-episode Franka cube dataset
  with validation samples while keeping the data provenance honest.

Hypothesis:
- A geometric GraspGenX grasp-library approach dataset should validate the
  official DP training/validation path and PPO bridge under varied cube poses,
  but it should still be treated as `curobo_validated=false` until real cube
  planner traces are generated or located.

Change:
- Added `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`.
- The generator:
  - reads GraspGenX cube grasp-library fields `grasps_object`, `confidence`,
    `grasp_to_tool_transform`, `tool_frame`, and `gripper_name`;
  - samples cube positions from the current Franka cube reset center and
    `0.08 m` XY randomization range;
  - computes `T_world_ee` as
    `T_world_object @ T_object_grasp @ T_grasp_tool @ T_panda_hand_ee_offset`;
  - interpolates open-gripper approach-to-pregrasp waypoints;
  - verifies pregrasp EE distance is farther from the cube than exact grasp EE
    distance for every episode;
  - writes the same lowdim NPZ/metadata schema as the cuRobo converter.
- No Worker A/B task files were edited.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 1fad16fa6b4b9eacbe1edf67ca8153ff399694ad
- implementation_commit: d61beb2df3760d0fc86e08e789427cf82a65990e
- push/pull: branch push boundary; final pushed commit reported in the
  orchestrator/final response
- changed_files:
  - `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: origin branch currently at
  `1fad16fa6b4b9eacbe1edf67ca8153ff399694ad`

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: offline BC modules compile with the new generator.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.generate_grasp_library_demos --grasp-library "$library" --output "$art/datasets/franka_cube_grasp_library_geometric_debug.npz" --num-episodes 16 --steps 24 --hold-steps 4 --top-k 16 --seed 123`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/grasp_library_geometric_generate.log`
- artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_grasp_library_geometric_debug.npz`
  and `.metadata.json`

Result:
- status: passed
- metrics/artifacts: `16` episodes, `448` steps, `obs_dim=21`,
  `action_dim=7`, `curobo_validated=false`, all generated pregrasps farther
  from the cube than their exact grasp poses.
- key evidence: printed `FRANKA_CUBE_DP_BC_GRASP_LIBRARY_DEMOS`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$art/datasets/franka_cube_grasp_library_geometric_debug.npz"`
- job_id: n/a
- run_dir: external artifact directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/grasp_library_geometric_dataset_smoke.log`
- artifacts: generated dataset and metadata

Result:
- status: passed
- metrics/artifacts: sample obs `[8, 21]`, action `[8, 7]`,
  `num_train_samples=252`, first-step position replay error `0.0`, official
  DP import visible.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: official tiny train with validation split:
  `"$venv/bin/python" train.py --config-dir "$dex/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$art/datasets/franka_cube_grasp_library_geometric_debug.npz" task.dataset.val_ratio=0.25 training.device=cpu training.max_train_steps=2 training.max_val_steps=1 training.num_epochs=1 policy.num_inference_steps=2 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir="$out"`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_121600_grasp_library`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_grasp_library_debug_train.log`
  and run `logs.json.txt`
- artifacts:
  `.hydra/config.yaml`, `.hydra/overrides.yaml`, `train.log`,
  `checkpoints/latest.ckpt`,
  `checkpoints/epoch=0000-test_mean_score=0.000.ckpt`, W&B offline run.

Result:
- status: passed
- metrics/artifacts: official UNet parameters `1.662478e+07`; logged two
  train steps and one validation batch. Final record:
  `train_loss=1.143653690814972`, `val_loss=1.0723308324813843`,
  `train_action_mse_error=0.6667237877845764`, `test/mean_score=0.0`,
  `lr=2e-6`. Two checkpoints were produced, each about `254M`.
- key evidence: `logs.json.txt` contains train step records for global steps
  `0` and `1`, plus the validation/sample metrics record.

Command / Job:
- command: checkpoint bridge smoke on the grasp-library debug checkpoint:
  `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint "$run_dir/checkpoints/latest.ckpt" --dataset "$art/datasets/franka_cube_grasp_library_geometric_debug.npz" --device cpu --batch-size 2 --num-inference-steps 2`
- job_id: n/a
- run_dir: external official-DP debug run
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_grasp_library_checkpoint_smoke.log`
- artifacts: uses generated official DP checkpoint

Result:
- status: passed
- metrics/artifacts: loaded official workspace/policy, dataset episodes `16`,
  dataset steps `448`, lowdim sequence `[2, 2, 21]`, PPO obs `[2, 72]`,
  direct action `[2, 8, 7]`, bridge first-action `[2, 7]`, finite outputs.
- key evidence: printed `FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED`.

Analysis:
- The official DP path is now validated on both one-episode synthetic data and
  a multi-episode GraspGenX grasp-library geometric dataset with a validation
  split.
- This still does not close the real-data requirement: no local Franka cube
  cuRobo trajectory JSON/NPZ was found. The geometric dataset should be used
  only for mechanics/debugging and not for claims about cuRobo-planned BC.
- The action ranges are bounded and mostly approach/open-gripper:
  min approximately `[-0.066, -0.00008, -0.126, 0, 0, 0, 1]`,
  max approximately `[0.00036, 0, 0, 0, 0, 0, 1]`.
- Because the generated trajectories keep orientation and gripper state mostly
  fixed, they are not sufficient for final BC quality. The next real dataset
  must include true planner approach diversity and later close/lift ablations.

Next:
- Commit and push this generator/validation checkpoint.
- Next Worker C loop should either generate true Franka cube cuRobo trajectories
  from the grasp library or build the Isaac eval wrapper around
  `predict_action_from_ppo_obs()` for no-learning policy rollout inspection.
