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
