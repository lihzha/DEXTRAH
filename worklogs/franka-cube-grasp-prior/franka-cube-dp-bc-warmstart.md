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
