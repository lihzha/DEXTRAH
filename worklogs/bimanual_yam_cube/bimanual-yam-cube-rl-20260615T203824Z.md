# Bimanual YAM Cube RL Worklog

## 2026-06-15 20:38Z - RL training setup

Goal:
- Set up RL-Games training for `Dextrah-Bimanual-YAM-Cube-Grasp` and run it until policy success can be demonstrated with unassisted physics.

Hypothesis:
- The existing bimanual YAM cube env can reuse the Franka cube RL-Games training path if the task is registered in the generic launchers, the validator separates assisted demos from the strict RLability gate, and cluster wrappers make the validation/train/eval loop reproducible.

Change:
- Added bimanual task registration imports to `dextrah_lab/rl_games/train.py`, `play.py`, and `eval_rollout.py`.
- Extended `eval_rollout.py` metrics for bimanual YAM fields: left/right hold distances, max hold distance, side success, left/right gripper widths, and 14D action signals.
- Added `--allow_grasp_assist` / `--no-allow_grasp_assist` and `--require_unassisted_lift` to `validate_bimanual_yam_cube_grasp_env.py`.
- Added bimanual defaults and task overrides to `cluster/sbatch_train_teacher_8gpu.sh`.
- Added reproducible one-GPU wrappers:
  - `cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh`
  - `cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh`
  - `cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh`

Validation plan:
- Local: `python3 -m py_compile` on touched Python files, `bash -n` on changed wrappers, `git diff --check`.
- Cluster strict RLability gate: bimanual validator with `ALLOW_GRASP_ASSIST=False REQUIRE_UNASSISTED_LIFT=True`.
- If strict validation fails, tune contact/control/reward and rerun; do not use the assisted demo as RLability evidence.
- Training smoke: one L40S GPU, small env/iteration count, JSONL metrics and checkpoints required.
- Training/eval loop: inspect reward terms, lift/success metrics, reset reasons, checkpoints, and policy-only eval video/metrics; tune/relaunch until success or external blocker.

Version state:
- agent_id: `bimanual-yam-cube-rl-20260615T203824Z`
- local_repo: `/home/lzha/code/DEXTRAH`
- base_head: `ac5128c2e028a4ffc30c8710b34aa3f4aee60f98`
- remote_worktree: planned `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/bimanual-yam-cube-rl-20260615T203824Z`
- commit/push: pending local checks

Local checks:
- `python3 -m py_compile dextrah_lab/rl_games/train.py dextrah_lab/rl_games/play.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/validate_bimanual_yam_cube_grasp_env.py`
- `bash -n cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`
- Result: passed.

## 2026-06-15 21:17Z - bimanual action-prior path for RL training

Goal:
- Make the YAM cube task trainable through the same RL-Games path as Franka while keeping policy evaluation unassisted.

Observation:
- Strict top-camera close-first validation on A100 job `29114858` failed as expected when `ALLOW_GRASP_ASSIST=False`.
- The environment and asset checks passed, but the close-first scripted choreography only reached `max_lift=0.0539` with `max_success_rate=0.0`; the failure was physical contact/lift, not task registration or observation/reward plumbing.
- Prior worklog evidence showed the environment can physically lift with a different rest-to-contact path, so the next gate should exercise the 14D RL action interface rather than the assisted demo sequence.

Change:
- Added opt-in bimanual scripted-action prior reward fields to `DextrahBimanualYAMCubeGraspEnvCfg`.
- Added vectorized `compute_grasp_prior_reference_actions()` to the bimanual env. This reuses the eval script's existing `reference_delta` action-source hook and returns 14D left/right delta-IK plus gripper actions.
- Added bimanual action-prior reward logging: active rate, phase rates, teacher z/gripper actions, action error, and hold-target error.
- Exposed the new knobs through the 1-GPU bimanual train wrapper and the shared 8-GPU teacher wrapper.
- Updated the bimanual eval wrapper to accept `ACTION_SOURCE=reference_delta` without requiring a checkpoint.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env.py dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env_cfg.py dextrah_lab/rl_games/eval_rollout.py`
- `bash -n cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`
- Result: passed.

Next:
- Commit and deploy to the remote worktree.
- Run an A100 `ACTION_SOURCE=reference_delta` eval with no checkpoint to prove action-interface solvability.
- If reference eval succeeds, launch PPO with `BIMANUAL_ACTION_PRIOR_REWARD_ENABLED=True`; inspect JSONL reward/success metrics before scaling.

## 2026-06-15 21:24Z - reference action target follows cube

Observation:
- A100 eval job `29115184` with `ACTION_SOURCE=reference_delta` reached the cube sides and briefly lifted, but then lost the cube.
- Live metrics showed the contact action dragged the cube from `x=-0.30` to about `x=-0.205`; the reference kept targeting the original reset cube XY, so the lift phase fought the cube's physical motion.
- The run was cancelled at 1:34 elapsed to avoid wasting GPU time.

Change:
- Updated the bimanual reference action target to follow the current cube XY during contact and lift.
- Kept the lift target height tied to `cube_goal_pos.z + cube_center_to_hold_z` so the reference still aims at the configured success height.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env.py`
- `git diff --check`
- Result: passed.

## 2026-06-15 21:30Z - loosen reference lift trigger

Observation:
- A100 eval job `29115291` with the live-cube reference improved the contact behavior but still failed to solve.
- The cube briefly lifted to `0.014 m` with only `0.033 m` XY drift by step 80, but the teacher waited for `max_hold_to_cube_dist <= 0.120`; observed side-contact distances were typically `0.136-0.140`.
- Because the lift phase did not start early enough, the reference kept commanding downward approach and reset/lost contact.
- The run was cancelled at about 1:30 elapsed.

Change:
- Increased the reference-action lift trigger `bimanual_reference_contact_dist` from `0.120` to `0.145`.
- This only affects the scripted reference/action-prior target; the actual task success predicate is unchanged.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env_cfg.py`
- `git diff --check`
- Result: passed.
