# Worklog - franka-cube-grasp-prior / franka-cube-traj-tracking

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- created: 2026-06-11T18:39:17Z

## 2026-06-11T11:43:02-07:00 - trajectory-tracking variant plan

Goal:
- Explore the separate GraspGenX + cuRobo task-space trajectory tracking alternative for Franka cube RL without changing the production `Dextrah-Franka-Cube-Grasp` baseline.

Hypothesis:
- A reward-only tracking variant can provide early approach/close/lift guidance while preserving the baseline observation/action spaces. Task-space waypoints can be transformed by each sampled cube pose; joint trajectories must remain offline validation artifacts and must not be transformed blindly.

Plan:
- Add a compact reference helper under `dextrah_lab/tasks/dextrah_franka_cube_grasp/` that loads phase-labeled task-space waypoints, interpolates by episode time, transforms object-local poses into env-local task-space targets, and validates table/clearance metadata.
- Add a new experiment env/config module for `Dextrah-Franka-Cube-Grasp-Traj-Tracking` that subclasses the baseline cube env, adds reward-only EE pose and optional gripper schedule tracking, logs tracking metrics, and leaves phase/reference observations disabled by default.
- Add a DEXTRAH-owned script under `dextrah_lab/scene_scripts/` to emit and validate a compact reference JSON. The initial template is an unvalidated scaffold for the future GraspGenX/cuRobo export path; it stores task-space waypoints and metadata, not joint arrays.
- Register the new task id in `dextrah_lab/tasks/dextrah_franka_cube_grasp/gym_setup.py` while preserving `Dextrah-Franka-Cube-Grasp` unchanged.
- Validate with bounded local checks only: Python compile/importable pure helper checks and reference JSON generation/validation. Do not launch full training or cluster jobs.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md
- branch: codex/franka-cube-trajectory-tracking
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: `7e6c38f76699c134ad2f0d71de871e1b5f10d659`
- push/pull: n/a, local implementation checkpoint only unless requested by orchestrator
- changed_files: pending
- remote_commit/status: n/a, no cluster launch planned

Command / Job:
- command: `python3 -m py_compile <new files>`
- command: `python3 dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py --output ... --validate-only ...`
- job_id: n/a
- run_dir: local_results/franka_cube_traj_tracking/franka-cube-traj-tracking/
- logs: command stdout/stderr in terminal only unless a validation artifact is created
- artifacts: compact reference JSON and validation summary JSON

Expected Design Decisions:
- Reward-only tracking is the default so this remains closer to the baseline; adding phase/reference observations will be documented as a separate ablation because it changes the observation space.
- Track DEXTRAH EE pose and gripper schedule, not raw joint trajectories. Joint plans from cuRobo are only acceptable as offline validation/replay evidence or as a validated reference library keyed by object pose.
- Validate transformed waypoints through table clearance, cube clearance/envelope checks, finite pose checks, and later Isaac/cuRobo collision checks before any training run.

## 2026-06-11T12:02:00-07:00 - reward-only tracking scaffold

Goal:
- Add a coherent, isolated implementation checkpoint for the trajectory-tracking alternative without launching training.

Hypothesis:
- A separate task id can add GraspGenX/cuRobo-style task-space tracking rewards while leaving the production `Dextrah-Franka-Cube-Grasp` baseline unchanged.

Change:
- Added a compact reference helper/validator for phase-labeled object-local EE waypoints and optional gripper schedule.
- Added `Dextrah-Franka-Cube-Grasp-Traj-Tracking` config/env modules. The env subclasses the baseline cube task and adds additive reward-only tracking terms for EE position, EE orientation, and gripper width schedule.
- Registered the new task id separately in `gym_setup.py`; the original `Dextrah-Franka-Cube-Grasp` registration is still present and unchanged.
- Added a scene script that generates or validates compact reference JSON. The default generated template is explicitly marked `curobo_validated=false` and `manual_template`, so it is not usable as evidence of a planner-validated reference.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md
- branch: codex/franka-cube-trajectory-tracking
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: `9a8f697ef718f1d1fedfa1b9b51af6b8f54f5c2b` (source checkpoint; following worklog-only commit records this hash)
- push/pull: n/a, no cluster launch
- changed_files: dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_reference.py; dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py; dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py; dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py; dextrah_lab/tasks/dextrah_franka_cube_grasp/gym_setup.py; worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md
- remote_commit/status: n/a/local only

Command / Job:
- command: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_reference.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py dextrah_lab/tasks/dextrah_franka_cube_grasp/gym_setup.py`
- command: `PYTHONDONTWRITEBYTECODE=1 python3 dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py --validate-only`
- command: `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... build_template_reference() ... validate_reference_payload() ...`
- command: `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... import gymnasium ... import dextrah_lab.tasks.dextrah_franka_cube_grasp.gym_setup ...`
- job_id: n/a
- run_dir: n/a
- logs: terminal stdout/stderr only
- artifacts: no retained generated artifacts; template generation is reproducible from the script

Result:
- status: passed for pure syntax/reference checks; blocked for gym registration import in this local shell
- metrics/artifacts: reference validator passed 11/11 checks, with 5 waypoints, phases `approach/pregrasp/grasp/close/lift`, min approximate EE table margin 0.060 m, min cube AABB clearance 0.025 m, and no joint trajectory arrays.
- key evidence: validator output included `curobo_validated=false`, `task_space_transform_policy=transform_task_space_waypoints_by_cube_pose`, and `joint_trajectory_policy=do_not_transform_joint_trajectories`.
- local import blocker: the gym registration import failed immediately with `ModuleNotFoundError: No module named 'gymnasium'`, before reaching DEXTRAH/Isaac code.

Analysis:
- Reward-only tracking is the implemented default. Phase/reference observations remain disabled and raise a config error if requested, because adding them would change the observation space and would no longer be a strict comparison to the baseline.
- EE pose tracking is implemented as task-space position/orientation tracking against transformed object-local waypoints. Gripper schedule tracking is additive and low-weight. Joint tracking is intentionally not implemented.
- The env transforms task-space waypoints by the cube pose at reward time, so object pose randomization is handled in pose space. It does not transform or replay joint trajectories.
- Validation currently covers finite schema, monotonic phase timing, approximate table clearance, cube AABB clearance, and absence of joint arrays. Before any training claim, a real GraspGenX/cuRobo-exported reference must be collision-validated in Isaac/cuRobo for table, finger, and object contact issues.

Next:
- Run `Dextrah-Franka-Cube-Grasp-Traj-Tracking` in an Isaac Lab environment with small `num_envs` to validate observation shape, reset stability, tracking logs, unsafe target rate, and immediate termination rate.
- Replace the manual template with a compact reference exported from actual GraspGenX/cuRobo cube planning, keeping only task-space waypoints plus gripper schedule and recording cuRobo/Isaac validation evidence.

## 2026-06-11T12:08:00-07:00 - handoff checkpoint

Goal:
- Record the completed local implementation checkpoint for the orchestrator.

Version Control:
- agent_id: franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- implementation_commit: 8ac8dc54cc3841ca623be242c448a54361ff44ec
- push/pull: pushed to origin/codex/franka-cube-trajectory-tracking; no cluster job launched
- active jobs: none launched by this agent
- cleanup: generated local reference JSON and Python bytecode caches were removed before commit

Result:
- status: coherent checkpoint committed
- evidence: syntax/reference validation passed; gym registration import remains locally blocked by missing `gymnasium` in this shell

Next:
- Orchestrator can inspect/cherry-pick commit `8ac8dc54cc3841ca623be242c448a54361ff44ec` and run Isaac Lab smoke validation in an environment with the DEXTRAH dependencies installed.

## 2026-06-11T12:09:00-07:00 - resumed Isaac smoke plan

Goal:
- Move beyond the local scaffold and validate `Dextrah-Franka-Cube-Grasp-Traj-Tracking` in a real Isaac/DEXTRAH runtime, or reach a hard external blocker.

Hypothesis:
- The existing Franka cube validation entry point can be extended to assert tracking-specific runtime evidence while preserving the baseline task, then run as a small l401 smoke if local dependencies remain unavailable.

Plan:
- Re-check local runtime availability from this worktree: GPU, `gymnasium`, Isaac Lab imports, repo wrappers, and a short validation command when feasible.
- Patch the validation script only as needed to record tracking reward/log finite checks, baseline registration sanity, reference source metadata, and immediate termination/reset pathology.
- Run cheap local syntax/reference checks after edits.
- If local remains blocked, commit and push fixes, deploy exact commit to an agent-owned l401 worktree with Git/LFS, and launch a small one-GPU Isaac validation smoke. No full training.
- Monitor the l401 job to completion, inspect logs/metrics/artifacts, patch and relaunch if the smoke fails for code reasons.

Acceptance Criteria:
- New task id registers in Isaac runtime.
- Original `Dextrah-Franka-Cube-Grasp` registration still resolves.
- Reset observation dim remains baseline size 72 for the tracking variant.
- Tracking reward/log terms are finite and visible.
- Runtime metadata makes the manual template's `curobo_validated=false` state explicit.
- Short rollout has no NaN/Inf, no immediate reset/termination spike, and no tracking target table-clearance pathology.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md
- branch: codex/franka-cube-trajectory-tracking
- base_commit: 92556e3215938ca222bd60cf1ddab6c1531b21f3
- implementation_commit: pending
- push/pull: pending after edits
- changed_files: pending
- remote_commit/status: pending if l401 fallback is needed

Command / Job:
- command: `nvidia-smi -L`
- command: `python3 - <<'PY' ... import gymnasium, isaaclab, isaaclab_tasks, torch ...`
- command: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_reference.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/gym_setup.py`
- command: `PYTHONDONTWRITEBYTECODE=1 python3 dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py --validate-only`
- command: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: n/a
- run_dir: n/a
- logs: terminal stdout/stderr only
- artifacts: no retained local artifacts

Result:
- status: local Isaac runtime blocked; validation-script patch cheap checks passed
- metrics/artifacts: local host has GPUs `NVIDIA RTX 6000 Ada Generation` and `NVIDIA T400 4GB`; `/usr/bin/python3` is Python 3.12.3 but lacks `gymnasium`, `isaaclab`, `isaaclab_tasks`, and `torch`.
- key evidence: reference template validation passed with `curobo_validated=false`; shell wrapper syntax check passed.

Analysis:
- Local GPU exists, but the active local Python is not a DEXTRAH/Isaac Lab runtime. A real local smoke is therefore externally blocked by missing local dependencies, so the next valid execution surface is l401 using the DEXTRAH Isaac Lab container.
- The validation script now needs to be committed and deployed before l401 launch because it adds the required tracking-specific evidence checks.

Next:
- Commit and push the validation-check patch, deploy the exact commit into an agent-owned l401 worktree, and run a small `Dextrah-Franka-Cube-Grasp-Traj-Tracking` validation smoke through the repo wrapper with `TASK` and `CODE_NFS` overrides.

## 2026-06-11T12:24:00-07:00 - l401 tracking smoke launch

Goal:
- Run a bounded real Isaac/DEXTRAH validation smoke for `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.

Hypothesis:
- The patched validation script will exercise the tracking task in Isaac Lab, confirm baseline and tracking task registration, verify unchanged observation dimension, and log finite tracking rewards/targets.

Change:
- Committed validation patch locally as `6aa69470a33f5338091fed7fce02e2fad9b12341` and pushed `origin/codex/franka-cube-trajectory-tracking`.
- Deployed the exact commit to l401 via HTTPS Git fetch because l401 SSH GitHub auth failed with `Permission denied (publickey)`.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- base_commit: 92556e3215938ca222bd60cf1ddab6c1531b21f3
- implementation_commit: 6aa69470a33f5338091fed7fce02e2fad9b12341
- push/pull: pushed to origin; deployed to l401 agent worktree via `git fetch https://github.com/lihzha/DEXTRAH.git 6aa69470a33f5338091fed7fce02e2fad9b12341`
- changed_files: dextrah_lab/rl_games/validate_franka_cube_grasp_env.py; dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py; worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at 6aa69470a33f5338091fed7fce02e2fad9b12341, detached clean

Command / Job:
- command: `sbatch --partition=batch --time=0-00:45:00 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=<run>,NUM_ENVS=4,NUM_STEPS=80,VIDEO_LENGTH=80,CAPTURE_VIDEO=False,PRINT_INTERVAL=10 cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027680
- run_name: franka_cube_traj_tracking_smoke_20260611_120609
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_smoke_20260611_120609
- logs: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027680.out
- artifacts: metrics.json

Expected Success Evidence:
- `passed=true` in metrics.
- checks include `task_registration_resolves`, `trajectory_tracking_reference_runtime_summary`, `trajectory_tracking_template_marked_unvalidated`, `trajectory_tracking_logs_present_and_finite`, `trajectory_tracking_runtime_targets_safe`, `reset_observation_shape`, and `rollout_no_immediate_termination_spike`.

## 2026-06-11T12:26:00-07:00 - l401 tracking smoke result

Goal:
- Close out the real Isaac/DEXTRAH validation smoke for `Dextrah-Franka-Cube-Grasp-Traj-Tracking` and inspect actual metrics/logs, not only Slurm status.

Version Control:
- agent_id: franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- implementation_commit: 6aa69470a33f5338091fed7fce02e2fad9b12341
- push/pull: pushed to origin before launch; l401 worktree deployed at the exact commit
- changed_files_since_commit: worklog only
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at 6aa69470a33f5338091fed7fce02e2fad9b12341, detached clean

Command / Job:
- command: `sbatch --parsable --partition=batch --time=0-00:45:00 --job-name=franka_cube_traj_val --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_smoke_20260611_120609,NUM_ENVS=4,NUM_STEPS=80,VIDEO_LENGTH=80,CAPTURE_VIDEO=False,PRINT_INTERVAL=10 cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027680
- node: pool0-00016
- state: COMPLETED
- exit_code: 0:0
- elapsed: 00:00:51
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_smoke_20260611_120609
- logs: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027680.out
- copied_artifacts: cluster_results/l401/franka_cube_traj_tracking_smoke_20260611_120609/metrics.json; cluster_results/l401/franka_cube_traj_tracking_smoke_20260611_120609/validate_franka_cube_1027680.out

Result:
- status: PASSED
- checks: 33 total, 0 failed
- task_registration_resolves: passed; baseline entry point remains `dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_grasp_env:DextrahFrankaCubeGraspEnv`; tracking entry point resolves to `dextrah_lab.tasks.dextrah_franka_cube_grasp.franka_cube_traj_tracking_env:DextrahFrankaCubeTrajTrackingEnv`
- observation_dim: `initial_observation_shape` and `reset_observation_shape` both `[4, 72]`, matching the baseline-size expected shape
- rollout: 80/80 steps completed, `done_count=0`, `early_done_count=0`, `reward_mean=1.6670513838529586`, `reward_final=1.6635054349899292`
- tracking_logs: present and finite; `tracking_reward_mean=0.10527513367123902`, `tracking_reward_final=0.19135458767414093`, `tracking_target_table_clearance_min=0.06249913573265076`, `tracking_unsafe_target_rate_max=0.0`
- reset_safety: cube remained on table; reset finger-table clearance min `0.050090670585632324`; rollout mean finger-table clearance min `0.06031647324562073`
- reference_runtime_summary: `planner=manual_template`, `source_tag=manual_template_pending_graspgenx_curobo_export`, `curobo_validated=false`, `graspgenx_source=false`, `joint_trajectory_policy=do_not_transform_joint_trajectories`, `transform_policy=transform_task_space_waypoints_by_cube_pose`, `waypoint_count=5`, `validation_passed=true`

Analysis:
- The first real Isaac smoke is viable: task registration works, the baseline task registration still resolves, the tracking variant preserves the baseline observation dimension, tracking reward/log terms are finite, transformed task-space targets remain above the table margin, and there is no immediate reset/termination pathology over a small 4-env, 80-step rollout.
- The current reference is still a manual unvalidated template by design. The runtime and metrics correctly expose `curobo_validated=false` and `graspgenx_source=false`; this is acceptable only for plumbing smoke, not for a training-quality trajectory prior.
- The next development boundary is to prepare short RL-smoke plumbing for the tracking task while continuing the reference path toward a real GraspGenX/cuRobo-exported compact task-space reference or a clearly logged validation blocker.

Next:
- Audit the teacher-training wrapper/config path so `Dextrah-Franka-Cube-Grasp-Traj-Tracking` inherits the Franka cube training settings rather than falling through to unrelated defaults.
- Add a bounded short-RL-smoke launch path after the wrapper audit. Do not run full training until short RL smoke evidence is sane.
- Continue investigating feasible GraspGenX/cuRobo cube reference export and keep the manual template marked unvalidated until real planner/validation evidence exists.

## 2026-06-11T12:32:00-07:00 - short RL smoke prep plan

Goal:
- Prepare a bounded RL-Games training smoke for the trajectory-tracking task without changing the original baseline task.

Audit:
- `Dextrah-Franka-Cube-Grasp-Traj-Tracking` currently registers, but its RL-Games config points at the baseline YAML, so logs/checkpoints would share the `dextrah_franka_cube_grasp` namespace.
- `cluster/sbatch_train_teacher_8gpu.sh` only recognizes exact `TASK=Dextrah-Franka-Cube-Grasp`; the tracking task would fall through to unrelated Kuka/default teacher settings unless patched.
- `dextrah_lab/rl_games/eval_rollout.py` can run arbitrary task ids, but its metric collection does not yet include trajectory-tracking fields.

Plan:
- Add a separate RL-Games YAML for the tracking variant with the same Franka cube hyperparameters but a distinct `params.config.name`, W&B metadata, and experiment namespace.
- Register only `Dextrah-Franka-Cube-Grasp-Traj-Tracking` to the new YAML; leave `Dextrah-Franka-Cube-Grasp` registration unchanged.
- Update `cluster/sbatch_train_teacher_8gpu.sh` so the tracking task uses the same Franka cube default env count, horizon, minibatch, and task overrides as the baseline, while retaining `TASK` as the tracking id.
- Extend eval metric collection with tracking target/reward/error fields for later checkpoint evaluation.
- Run local cheap validation (`py_compile`, wrapper `bash -n`, reference validation). If local Isaac remains unavailable, commit/push and launch a short l401 RL smoke with small `NUM_ENVS`, one GPU, `MAX_ITERATIONS` capped, `AUTO_RESUME=False`, and `DISTRIBUTED=False`.

Acceptance Criteria:
- Original `Dextrah-Franka-Cube-Grasp` keeps its baseline YAML and wrapper behavior.
- Tracking variant logs under `dextrah_franka_cube_traj_tracking`.
- Short RL smoke launches the tracking task in Isaac/RL-Games, writes params/checkpoints/logs, exposes finite tracking metrics, and shows no immediate reset/termination pathology in logs.

## 2026-06-11T12:42:00-07:00 - short RL smoke launch plan

Goal:
- Run a one-GPU, bounded RL-Games smoke for `Dextrah-Franka-Cube-Grasp-Traj-Tracking` after the real env smoke passed.

Version Control:
- agent_id: franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- implementation_commit: 7d9c18066421638331888692d08d9185cc3d00d7
- push/pull: pushed to origin; l401 agent worktree deployed at the exact commit via HTTPS Git fetch
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at 7d9c18066421638331888692d08d9185cc3d00d7, detached clean

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:45:00 --job-name=franka_cube_traj_rl_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_rl_smoke_20260611_124200,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08 cluster/sbatch_train_teacher_8gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job_id>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200

Acceptance Criteria:
- RL-Games starts with `TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking` and `params.config.name=dextrah_franka_cube_traj_tracking`.
- The run completes 3 iterations or reaches a concrete code/runtime blocker.
- Logs show finite rewards/losses and tracking terms such as `cube_traj_tracking_reward`.
- No immediate reset/termination pathology is visible in rollout statistics or env logs.
- Output params and any checkpoints remain under the tracking namespace, not the baseline `dextrah_franka_cube_grasp` namespace.

## 2026-06-11T12:46:00-07:00 - short RL smoke checkpoint and eval plan

Goal:
- Close the RL smoke with explicit tracking metrics by evaluating the saved epoch-3 checkpoint for a short rollout.

RL Smoke Result So Far:
- job_id: 1027682
- state: COMPLETED
- exit_code: 0:0
- elapsed: 00:00:53
- node: pool0-00037
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027682.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200
- checkpoint: /results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.481527.pth
- evidence: training used `DextrahFrankaCubeTrajTrackingEnvCfg`, parsed `rl_games_ppo_franka_cube_traj_tracking_cfg.yaml`, logged under `/results/logs/rl_games/dextrah_franka_cube_traj_tracking`, built MLP with observation dim 72, completed epochs 1/3 through 3/3, and saved checkpoints at each epoch.

Gap:
- The RL-Games event file under `summaries/` was zero bytes for this 3-epoch smoke, and stdout did not print per-term tracking scalars. Scheduler success plus checkpoint creation is not enough for the tracking claim.

Plan:
- Run `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` against the epoch-3 checkpoint with `TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking`, 4 envs, 120 steps, no video, and the patched `eval_rollout.py` tracking metric collection.
- Inspect `metrics.json` for finite `cube_traj_tracking_reward`, position/orientation/gripper errors, unsafe target rate, reward, success, done count, and cube/finger safety metrics.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:30:00 --job-name=franka_cube_traj_eval_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_eval_smoke_20260611_124600,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.481527.pth,NUM_ENVS=4,NUM_STEPS=120,VIDEO_LENGTH=120,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,USE_CUDA_GRAPH=False,SEED=42,CUBE_SPAWN_XY_RANDOMIZATION=0.08 cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_eval_smoke_20260611_124600/metrics.json
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job_id>.out

## 2026-06-11T12:50:00-07:00 - short RL smoke and checkpoint eval result

Goal:
- Inspect the short RL smoke and checkpoint rollout artifacts for the trajectory-tracking variant.

Version Control:
- agent_id: franka-cube-traj-tracking
- branch: codex/franka-cube-trajectory-tracking
- implementation_commit: 7d9c18066421638331888692d08d9185cc3d00d7
- push/pull: pushed to origin before both jobs; l401 worktree ran the exact commit
- changed_files_since_commit: worklog only

RL Training Smoke:
- job_id: 1027682
- state: COMPLETED
- exit_code: 0:0
- elapsed: 00:00:53
- node: pool0-00037
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027682.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200
- copied_artifacts: cluster_results/l401/franka_cube_traj_tracking_rl_smoke_20260611_124200/
- checkpoint: /results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_rl_smoke_20260611_124200/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.481527.pth
- result: completed epochs 1/3 through 3/3, saved checkpoints at each epoch, used observation dim 72, and logged under `dextrah_franka_cube_traj_tracking` rather than the baseline namespace.

Checkpoint Eval:
- job_id: 1027684
- state: COMPLETED
- exit_code: 0:0
- elapsed: 00:00:48
- node: pool0-00016
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027684.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_eval_smoke_20260611_124600
- metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_eval_smoke_20260611_124600/metrics.json
- copied_artifacts: cluster_results/l401/franka_cube_traj_tracking_eval_smoke_20260611_124600/

Metrics:
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`
- rollout: 120/120 steps completed, `done_count=0`, `reward_mean=1.8547612518072127`, `reward_final=1.835127353668213`, `success_rate_mean=0.0`
- tracking_reward: mean `0.16274007273217042`, min `0.06703692674636841`, max `0.3394785225391388`, final `0.17202991247177124`
- tracking_position_error: mean `0.2675555331011613`, min `0.2272346168756485`, max `0.3607536554336548`, final `0.26861393451690674`
- tracking_orientation_error: mean `0.03302687865992387`, min `0.031078606843948364`, max `0.03564339876174927`, final `0.03564339876174927`
- tracking_gripper_error: mean `0.02828299894463271`, min `0.0012944750487804413`, max `0.042235828936100006`, final `0.012320716865360737`
- tracking_target_table_clearance: mean `0.09891407762964567`, min `0.054998964071273804`, max `0.17129141092300415`, final `0.1519220471382141`
- tracking_unsafe_target_rate: mean/min/max/final `0.0`
- finger_table_clearance: mean `0.054331634069482486`, min `0.053225547075271606`, final `0.05461743474006653`
- cube_lift_height: mean/max/final `0.0`
- cube_xy_error: mean `1.0017365164927127e-06`, max `5.385340500652092e-06`, final `9.675526371211163e-07`

Analysis:
- The trajectory-tracking variant now has a real Isaac env smoke and a bounded RL-Games smoke/eval path. The tracking task registers, trains for a tiny capped run, saves checkpoints in its own namespace, reloads the checkpoint, and reports finite tracking metrics in eval.
- This is not evidence of task success or learning yet: the 3-epoch smoke did not lift the cube (`success_rate=0.0`, `cube_lift_height=0.0`). It only validates plumbing, stability, checkpoint load, and finite tracking reward/log terms.
- The training event file for the 3-epoch smoke was zero bytes, so checkpoint eval is currently the better artifact for per-term tracking evidence.
- The manual reference remains unvalidated (`curobo_validated=false`). The next boundary is real GraspGenX/cuRobo reference validation/export, not scaling RL yet.

Next:
- Run the GraspGenX Franka cube cuRobo validator in a bounded cluster smoke to determine whether the real cube grasp/plan path is available.
- Keep the template unvalidated until task-space waypoints are exported from the GraspGenX/cuRobo trajectory path and accepted by the compact loader.

## 2026-06-11T12:54:00-07:00 - GraspGenX/cuRobo cube validation launch plan

Goal:
- Determine whether the real GraspGenX + cuRobo Franka cube path is available on l401 and produces a validated grasp/plan prior. This is reference validation, not RL training.

Version Control:
- DEXTRAH branch: codex/franka-cube-trajectory-tracking
- DEXTRAH head for tracking code: 25fb8bbd1f81eb90f88730ea8352c5705a8770ce
- GraspGenX l401 checkout: /lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx
- GraspGenX branch/head: franka-cube-ggx-rl at a0ca3d9f3f85cb3325ca2238107087f03d1555e3
- GraspGenX local note: `/home/lzha/code/graspgenx` has an unrelated modified `WORKLOG.md`; this agent does not touch/revert it.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:45:00 --job-name=ggx_cube_traj_ref_val --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx,RUN_NAME=franka_cube_traj_ref_ggx_curobo_20260611_125400,SEED=0,NUM_GRASPS=80,TOPK=40,GRASP_THRESHOLD=0.7,GRASP_PLANNER=graspmoe,MOE_OBB_DENSITY=dense,MAX_PLAN_ATTEMPTS=40 cluster/sbatch_validate_franka_cube_graspgenx_curobo.sh`
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_20260611_125400
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/validate_curobo_<job_id>.out
- expected_artifacts: environment.json, prior.json, validation.json

Acceptance Criteria:
- Environment checks find CUDA, GraspGenX checkpoints, Franka gripper assets, cuRobo Python, and Franka cuRobo robot assets.
- GraspGenX returns at least one cube grasp.
- cuRobo plans approach/grasp/lift to a selected grasp with positive segment lengths.
- If this passes, it is evidence of a real selected grasp/plan, but not yet a compact task-space tracking reference because the validator does not export object-local EE waypoints. A separate converter/exporter is still required before setting `curobo_validated=true` in the DEXTRAH runtime reference.

## 2026-06-11T12:58:00-07:00 - GraspGenX trajectory converter plan

Goal:
- Add an offline converter for GraspGenX `trajectory.json` artifacts so a future cuRobo-planned trajectory can be reduced to the compact DEXTRAH task-space reference schema.

Plan:
- Add a DEXTRAH-owned scene script that reads GraspGenX `trajectory.json`, loads the Franka profile/FK helpers from a provided GraspGenX checkout, computes the `panda_hand` pose for selected frames, applies the DEXTRAH EE offset, transforms the EE poses into the object frame, and writes only object-local task-space waypoints plus gripper-width schedule.
- Keep joint arrays out of the compact output. The input may contain joint positions, but the emitted payload must pass `no_joint_trajectory_arrays`.
- Require an explicit `--mark-curobo-validated` plus a passed GraspGenX validation JSON before setting `source.curobo_validated=true`; otherwise emit `curobo_validated=false`.
- Preserve the current runtime template behavior. The converter is an offline tool and does not change the baseline or tracking task defaults.

Validation:
- Run `py_compile`.
- Run `--help` locally.
- Run compact loader validation on the generated output when a real trajectory JSON becomes available.

## 2026-06-11T13:01:00-07:00 - GraspGenX/cuRobo validation retry plan

Result From First Attempt:
- job_id: 1027686
- state: FAILED
- exit_code: 1:0
- elapsed: 00:01:46
- node: pool0-00016
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/validate_curobo_1027686.out
- partial_artifact: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_20260611_125400/environment.json

Evidence:
- Environment checks passed: CUDA, GraspGenX checkpoints, Franka gripper assets, cuRobo robot config, and cuRobo kernels initialized.
- GraspGenX returned grasps, but `GRASP_THRESHOLD=0.7` left only 6 candidates after repeated sampling.
- cuRobo tried the configured approach/grasp/lift strategy sweep and failed all selected candidates with `Goalset planning returned None`.

Analysis:
- This is not an external blocker yet. The grasp set was too narrow for the planner. Relaunch with threshold disabled and the larger default candidate set so cuRobo can choose among more reachable candidates.
- Caveat remains: the GraspGenX env config is a 45 mm cube, while DEXTRAH Franka cube is 60 mm. Even a passed retry is availability evidence, not a DEXTRAH-ready compact reference.

Retry Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:45:00 --job-name=ggx_cube_traj_ref_val2 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx,RUN_NAME=franka_cube_traj_ref_ggx_curobo_retry_20260611_130100,SEED=1,NUM_GRASPS=200,TOPK=80,GRASP_THRESHOLD=-1,GRASP_PLANNER=graspmoe,MOE_OBB_DENSITY=dense,MAX_PLAN_ATTEMPTS=80 cluster/sbatch_validate_franka_cube_graspgenx_curobo.sh`
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_retry_20260611_130100
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/validate_curobo_<job_id>.out

## 2026-06-11T13:24:00-07:00 - GraspGenX trajectory JSON export plan

Goal:
- Move beyond selected-pose prior validation by producing a real GraspGenX/cuRobo `trajectory.json` for the cube path, then use it to exercise the DEXTRAH compact task-space converter.

Hypothesis:
- The same broader candidate settings that passed validation (`GRASP_THRESHOLD=-1`, 80 goalset candidates) should let `end2end/e2e_grasp_demo.py` plan and export the kinematic `pick_and_lift` trajectory without editing GraspGenX.

Version Control:
- agent_id: franka-cube-traj-tracking
- DEXTRAH branch/head: codex/franka-cube-trajectory-tracking at 25fb8bbd1f81eb90f88730ea8352c5705a8770ce plus local converter/worklog edits
- GraspGenX checkout: /lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx at a0ca3d9f3f85cb3325ca2238107087f03d1555e3
- changed_files_pending: `dextrah_lab/scene_scripts/convert_graspgenx_cube_trajectory_reference.py`, this worklog

Command / Job:
- command: custom l401 `sbatch` using the GraspGenX container and NFS venv, running `python end2end/e2e_grasp_demo.py --robot_config end2end/robots/franka_panda.yaml --env_config end2end/envs/franka_cube_lift.yaml --mesh_file assets/sample_data/object_mesh/box.obj --task pick_and_lift --playback_mode kinematic --no-viser --num_grasps 200 --topk 80 --grasp_threshold -1 --planner graspmoe --moe_obb_density dense --max_plan_attempts 80 --seed 1 --export-trajectory /results/trajectory_exports/franka_cube_traj_ref_export_20260611_132400/trajectory.json`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/e2e_export_<job_id>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/trajectory_exports/franka_cube_traj_ref_export_20260611_132400
- expected_artifacts: `trajectory.json`, `static_meshes/*.obj`

Acceptance Criteria:
- Export job reaches `Trajectory JSON:` with positive frames and no full training launched.
- DEXTRAH converter either produces a compact reference with `curobo_validated=false` for the 45 mm cube or correctly rejects attempts to mark it valid against the 60 mm DEXTRAH cube.
- Any accepted compact reference contains only object-local task-space waypoints and gripper schedule, not joint trajectory arrays.

## 2026-06-11T13:28:00-07:00 - GraspGenX validation/export result and converter deploy plan

Goal:
- Close the failed `1027686` alert with root-cause evidence, record the successful relaunch/export artifacts, and deploy the DEXTRAH converter for a real compact-reference smoke.

Result:
- failed_job: 1027686 `ggx_cube_traj_ref_val`
- failed_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/validate_curobo_1027686.out
- failed_local_copy: cluster_results/l401/graspgenx_franka_cube_traj_ref_20260611_125400_failed/
- failed_state: FAILED, exit `1:0`, elapsed `00:01:46`, node `pool0-00016`
- root_cause: environment/assets were available, but `GRASP_THRESHOLD=0.7` left only 6 candidates for cuRobo and every `plan_grasp` strategy returned `Goalset planning returned None`; the script raised `RuntimeError("cuRobo failed to plan to all sampled Franka cube grasps")`.
- retry_job: 1027688 `ggx_cube_traj_ref_val2`
- retry_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/validate_curobo_1027688.out
- retry_local_copy: cluster_results/l401/graspgenx_franka_cube_traj_ref_20260611_130100_retry/
- retry_state: COMPLETED, exit `0:0`, elapsed `00:00:54`, node `pool0-00016`
- retry_evidence: 200 raw grasps, threshold disabled, 80 goalset candidates, selected grasp #22 at confidence `0.6011205911636353`, successful strategy `full (a=15, lift=20)`, approach/grasp/lift segment lengths all 42.
- retry_validation_json: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_retry_20260611_130100/validation.json
- retry_caveat: validation geometry is GraspGenX `franka_cube_lift.yaml`, a 45 mm cube (`object_extents_m=[0.045, 0.045, 0.045]`), not the DEXTRAH 60 mm cube.

Trajectory Export:
- job_id: 1027689 `ggx_cube_traj_export`
- state: COMPLETED, exit `0:0`, elapsed `00:00:53`, node `pool0-00016`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/e2e_export_1027689.out
- local_copy: cluster_results/l401/graspgenx_franka_cube_traj_ref_export_20260611_132400/
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/trajectory_exports/franka_cube_traj_ref_export_20260611_132400
- command: `python end2end/e2e_grasp_demo.py --robot_config end2end/robots/franka_panda.yaml --env_config end2end/envs/franka_cube_lift.yaml --mesh_file assets/sample_data/object_mesh/box.obj --task pick_and_lift --playback_mode kinematic --no-viser --num_grasps 200 --topk 80 --grasp_threshold -1 --planner graspmoe --moe_obb_density dense --max_plan_attempts 80 --seed 1 --export-trajectory /results/trajectory_exports/franka_cube_traj_ref_export_20260611_132400/trajectory.json`
- artifact: `trajectory.json`, 662 frames, 30 fps, 8 joint columns, static keys `object` and `table`, object z `0.5225`
- export_evidence: selected grasp #28 at confidence `0.597`, successful strategy `full (a=15, lift=20)`, approach/grasp/lift segment lengths all 42, task trajectory segments total 662 waypoints.

Analysis:
- The immediate scheduler failure has been debugged and corrected by broadening the candidate set. The GraspGenX/cuRobo path is live on l401 for the 45 mm cube.
- This is still not a DEXTRAH-ready validated 60 mm reference. The compact converter must keep `curobo_validated=false` for this artifact unless a validation JSON with matching 60 mm extents is supplied.
- The converter should prove both sides: produce a task-space-only compact reference from the real trajectory, and reject an attempt to mark it validated for the 60 mm DEXTRAH cube using the 45 mm validation JSON.

Next:
- Commit the converter/worklog, push the DEXTRAH branch, deploy the exact commit to the l401 DEXTRAH agent worktree, and run the converter in the GraspGenX container with DEXTRAH mounted at `/dextrah`.

## 2026-06-11T13:36:00-07:00 - compact converter smoke result

Goal:
- Exercise the DEXTRAH converter on a real GraspGenX/cuRobo-exported `trajectory.json` and prove it refuses to mark a 45 mm validation artifact as DEXTRAH 60 mm validated.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: ffe0e671ed2bac13ae8cd4db388e16f69915f2e4
- push/pull: pushed to origin; l401 DEXTRAH agent worktree deployed at the exact commit
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at ffe0e671ed2bac13ae8cd4db388e16f69915f2e4, detached clean
- deploy_note: initial SSH-origin fetch failed on l401 (`Permission denied (publickey)`); retried with HTTPS fetch and deployed successfully.

Command / Job:
- failed_job: 1027691 `dextrah_ggx_ref_convert`, FAILED after `00:00:27`
- failed_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/ggx_ref_convert_1027691.out
- failure_cause: wrapper tried `git -C /dextrah rev-parse HEAD` inside a Pyxis mount of a Git worktree; the `.git` pointer referenced an unmounted canonical path, so Git failed before the converter ran.
- relaunch_job: 1027692 `dextrah_ggx_ref_convert2`, COMPLETED `0:0` after `00:00:33` on `pool0-00016`
- relaunch_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/ggx_ref_convert_1027692.out
- command: `python /dextrah/dextrah_lab/scene_scripts/convert_graspgenx_cube_trajectory_reference.py --trajectory /results/trajectory_exports/franka_cube_traj_ref_export_20260611_132400/trajectory.json --output /dextrah_results/trajectory_references/franka_cube_traj_ref_export_20260611_132400_45mm_unvalidated/compact_reference.json --summary /dextrah_results/trajectory_references/franka_cube_traj_ref_export_20260611_132400_45mm_unvalidated/conversion_summary.json --graspgenx-root /code --validation-json /results/prior_validation/franka_cube_traj_ref_ggx_curobo_retry_20260611_130100/validation.json --cube-size 0.045 --table-surface-z 0.5 --cube-spawn-z 0.5225 --source-tag graspgenx_curobo_45mm_export_unvalidated_for_dextrah`
- negative_gate_command: same converter with `--mark-curobo-validated --cube-size 0.06 --table-surface-z 0.746` against the 45 mm validation JSON.

Artifacts:
- remote_reference: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/trajectory_references/franka_cube_traj_ref_export_20260611_132400_45mm_unvalidated/compact_reference.json
- remote_summary: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/trajectory_references/franka_cube_traj_ref_export_20260611_132400_45mm_unvalidated/conversion_summary.json
- local_copy: cluster_results/l401/franka_cube_traj_ref_export_20260611_132400_45mm_unvalidated/

Metrics / Checks:
- compact reference validation: passed 11/11 records
- waypoint_count: 9
- cube_size_m: 0.045
- source.graspgenx_source: true
- source.curobo_validated: false
- validation.requires_curobo_collision_validation_before_training: true
- no joint arrays stored: `no_joint_trajectory_arrays` passed and local grep found no payload joint arrays; only policy/diagnostic strings mention `joint_trajectory`.
- min target table margin under 45 mm GraspGenX table model: `0.04510111162814601 m`
- min cube AABB clearance: `0.00010111162814604308 m`
- negative gate: expected failure with `object_extents_match_cube_size=false`; converter exited rc `1` and wrapper printed `EXPECTED_60MM_VALIDATION_GATE_REJECTION`.

Analysis:
- The new converter is operational against a real GraspGenX/cuRobo-exported trajectory and emits compact object-local task-space waypoints only.
- The reference is intentionally not DEXTRAH-ready: it is a 45 mm GraspGenX cube artifact and remains `curobo_validated=false`.
- The validation gate prevents silently blessing the 45 mm GraspGenX validation as a 60 mm DEXTRAH reference.

Next:
- Try a scratch GraspGenX 60 mm cube env config by changing only `mesh_scale` to `0.60` in a temporary l401 job. If validation/export succeeds, convert a 60 mm compact reference. If it fails, record the exact planner/export blocker and keep the runtime task on the unvalidated template path.

## 2026-06-11T13:40:00-07:00 - 60 mm GraspGenX reference attempt plan

Goal:
- Determine whether the GraspGenX/cuRobo path can produce a DEXTRAH-geometry 60 mm cube validation/export without modifying the GraspGenX repo.

Plan:
- Submit a bounded l401 GraspGenX container job that creates `/tmp/franka_cube_lift_60mm.yaml` by copying `end2end/envs/franka_cube_lift.yaml` and replacing `mesh_scale: 0.45` with `mesh_scale: 0.60`.
- Run `validate_franka_cube_graspgenx_curobo.py` with `--env-config /tmp/franka_cube_lift_60mm.yaml --cube-size 0.06`, broad grasp settings, and no fallback.
- If validation passes, run `e2e_grasp_demo.py` against the same scratch env to export a 60 mm `trajectory.json`.
- If export passes, run the DEXTRAH converter for a 60 mm compact reference. Keep `curobo_validated=false` unless the validation/export evidence is exact enough to avoid overstating readiness.

Acceptance Criteria:
- No full training.
- Validation JSON must report `object_extents_m` near `[0.06, 0.06, 0.06]` and positive approach/grasp/lift segments before any DEXTRAH-ready claim.
- Export must produce a positive-frame trajectory JSON.
- Converter output must still contain no joint trajectory arrays and must pass compact loader checks.

## 2026-06-11T13:50:00-07:00 - 60 mm GraspGenX reference attempt result

Goal:
- Run the scratch 60 mm GraspGenX/cuRobo path and convert a DEXTRAH-geometry compact reference if validation/export pass.

Command / Job:
- failed_job: 1027693 `ggx_cube_60mm_ref`, FAILED after `00:00:26`
- failed_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/ggx_cube_60mm_ref_1027693.out
- failure_cause: wrapper generated the scratch 60 mm YAML correctly but did not `cd /code` before running `python end2end/validate_franka_cube_graspgenx_curobo.py`; Python looked under `/workspace/end2end/...`.
- relaunch_job: 1027694 `ggx_cube_60mm_ref2`, COMPLETED `0:0` after `00:01:24` on `pool0-00016`
- relaunch_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/graspgenx/ggx_cube_60mm_ref_1027694.out
- scratch_env: copied `end2end/envs/franka_cube_lift.yaml` and replaced `mesh_scale: 0.45` with `mesh_scale: 0.60`; no GraspGenX repo files modified.

60 mm Validation:
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_60mm_retry_20260611_134500
- validation_json: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/prior_validation/franka_cube_traj_ref_ggx_curobo_60mm_retry_20260611_134500/validation.json
- result: `VALIDATION_PASSED`
- object_extents_m: `[0.06, 0.06, 0.06]`
- num_grasps: 120
- confidence_range: `0.6334112882614136..0.8303762674331665`
- selected_grasp_index: 36
- selected_grasp_confidence: `0.6739507913589478`
- plan_segments: approach 42, grasp 42, lift 42

60 mm Export:
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/trajectory_exports/franka_cube_traj_ref_export_60mm_retry_20260611_134500
- trajectory_json: /lustre/fsw/portfolios/nvr/users/lzha/results/graspgenx/trajectory_exports/franka_cube_traj_ref_export_60mm_retry_20260611_134500/trajectory.json
- result: exported `trajectory.json` with 662 frames, 30 fps, 8 joint columns, static `object` and `table` meshes
- export_selected_grasp: original grasp #101 at confidence `0.714`
- export_plan_segments: approach 42, grasp 42, lift 42

60 mm Compact Reference:
- remote_reference: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json
- remote_summary: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/conversion_summary.json
- local_copy: cluster_results/l401/franka_cube_traj_ref_60mm_retry_20260611_134500/
- compact validation: passed 11/11 records locally and in-container
- cube_size_m: 0.06
- waypoint_count: 9
- source.curobo_validated: false
- no joint arrays stored: `no_joint_trajectory_arrays` passed and grep found no payload joint arrays; only policy/diagnostic strings mention `joint_trajectory`.
- min DEXTRAH-table target margin: `0.06511412328056643 m`
- min cube AABB clearance: `0.0001141232805663972 m`

Analysis:
- The GraspGenX/cuRobo path can validate and export a 60 mm cube reference when the env config geometry is adjusted to match DEXTRAH.
- I intentionally kept the converted reference `curobo_validated=false`. The validation and export used the same scratch geometry and object pose but selected different grasp indices in separate processes (#36 for validator, #101 for exporter), so this is a strong DEXTRAH-geometry reference artifact but not an exact single-run validated trajectory record.
- The next exactness improvement is a unified GraspGenX export/validation path that writes validation metadata from the same `e2e_grasp_demo.py` trajectory export process.

Next:
- Patch the DEXTRAH env validator/wrapper to accept an external compact reference path, then run a real Isaac task smoke for `Dextrah-Franka-Cube-Grasp-Traj-Tracking` loading the 60 mm compact reference.

## 2026-06-11T13:53:00-07:00 - external-reference env smoke patch plan

Goal:
- Validate the tracking task against the 60 mm compact reference instead of only the built-in manual template.

Change:
- Add `--trajectory_tracking_reference_path` to `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py` and set `env_cfg.trajectory_tracking_reference_path` when provided.
- Add `TRAJECTORY_TRACKING_REFERENCE_PATH` passthrough to `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`.
- Keep default path empty so `Dextrah-Franka-Cube-Grasp` and the tracking variant baseline behavior remain unchanged unless explicitly overridden.

Validation Plan:
- Local: `python3 -m py_compile dextrah_lab/rl_games/validate_franka_cube_grasp_env.py` and `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`.
- Cluster: run `Dextrah-Franka-Cube-Grasp-Traj-Tracking` validation with `TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`, 4 envs, 80 steps, no video.
- Acceptance: task registers, baseline registration still resolves, observation dim stays 72, runtime reference summary points at the external path with `graspgenx_source=true`, tracking metrics finite, unsafe target rate 0, no immediate reset/termination pathology.

## 2026-06-11T14:07:00-07:00 - external-reference env smoke result and RL wrapper plan

Goal:
- Close the DEXTRAH Isaac task smoke against the 60 mm compact GraspGenX-derived reference, then prepare a short RL smoke that uses the same external reference.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: faa568ad11b8c0fc4b114a88e6649b8e96beb067
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at faa568ad11b8c0fc4b114a88e6649b8e96beb067, detached clean
- changed_files_pending: this worklog; planned wrapper/eval changes below

Command / Job:
- job_id: 1027695 `franka_cube_traj_60mm_ref_val`
- state: COMPLETED `0:0`, elapsed `00:00:44`, node `pool0-00016`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:30:00 --job-name=franka_cube_traj_60mm_ref_val --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_60mm_ref_env_smoke_20260611_135700,NUM_ENVS=4,NUM_STEPS=80,VIDEO_LENGTH=80,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,SEED=7,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027695.out
- metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_60mm_ref_env_smoke_20260611_135700/metrics.json
- local_copy: cluster_results/l401/franka_cube_traj_tracking_60mm_ref_env_smoke_20260611_135700/

Result:
- status: passed
- checks: validation payload `passed=true`; observation shape stayed `[4, 72]`; baseline task registration still resolved inside the validator; 80/80 rollout steps completed; `done_count=0`; `early_done_count=0`.
- tracking_reference: external path `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`; `graspgenx_source=true`; `curobo_validated=false`; `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`; `waypoint_count=9`; `validation_passed=true`.
- tracking_metrics: reward mean `0.039574575144797564`; reward final `0.039327189326286316`; target table clearance min `0.27639952301979065`; unsafe target rate max `0.0`.
- rollout_metrics: reward mean `1.816138543188572`; reward final `1.7689825296401978`; cube stayed in workspace with min z `0.775999903678894`.

Analysis:
- The trajectory-tracking task now has a real Isaac/DEXTRAH env smoke with a GraspGenX-derived 60 mm task-space reference and no observation-size change.
- The reference is still not marked DEXTRAH-ready validated because validation and export selected different grasps in separate GraspGenX processes, despite matching the 60 mm geometry. The runtime summary correctly keeps `curobo_validated=false`.

Next / Patch Plan:
- Add optional `TRAJECTORY_TRACKING_REFERENCE_PATH` passthrough to `cluster/sbatch_train_teacher_8gpu.sh` and `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`.
- Keep the default empty so `Dextrah-Franka-Cube-Grasp` baseline and the built-in template path remain unchanged unless explicitly overridden.
- Add eval metrics for `trajectory_tracking_reference_summary()` when the task exposes it, so the checkpoint rollout can prove which reference was loaded.
- Local validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`, `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, `git diff --check`.
- Cluster validation after commit/deploy: short RL smoke with 16 envs, 3 iterations, no full training, then short checkpoint eval with the same external reference.

## 2026-06-11T14:40:00-07:00 - external-reference short RL smoke launch

Goal:
- Verify RL-Games can train the trajectory-tracking variant for a tiny bounded smoke while loading the 60 mm compact GraspGenX-derived reference.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: fa534c7d8decbf5978d4a21d32a04fc3df7e2bd7
- push/pull: pushed to origin; l401 agent worktree deployed at exact commit
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at fa534c7d8decbf5978d4a21d32a04fc3df7e2bd7, detached clean
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, `dextrah_lab/rl_games/eval_rollout.py`, this worklog

Local Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`: passed
- `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`: passed
- `git diff --check`: passed

Command / Job:
- job_id: 1027697 `franka_cube_traj_60mm_rl`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --time=0-00:45:00 --job-name=franka_cube_traj_60mm_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124055,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027697.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124055
- expected_artifacts: resolved env/agent params, checkpoint(s), stdout log, TensorBoard/W&B sidecars if produced.

Acceptance Criteria:
- Job completes without full training; no Hydra override errors.
- Log proves `TRAJECTORY_TRACKING_REFERENCE_PATH` reached the wrapper and env config.
- Checkpoint is written by epoch 3.
- Reward/loss diagnostics are finite, and follow-up eval loads the same external reference.

Monitor Update:
- `1027697` remained PENDING with `Reason=Resources`; `scontrol show job` showed the inherited 8-GPU teacher wrapper defaults still requested `NumCPUs=64` and `ReqTRES=mem=1004G` despite the one-GPU smoke override.
- Action: canceled `1027697` before it started; no log/run artifacts were produced.
- Relaunch job_id: 1027698 `franka_cube_traj_60mm_rl`
- relaunch_command_delta: same training/env/reference settings, plus `--cpus-per-task=16 --mem=160G`.
- relaunch_run_name: `franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124252`
- relaunch_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027698.out
- relaunch_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124252

Result Update:
- `1027698` completed `0:0` after `00:00:48` on `pool0-00016`.
- wrapper/path evidence: log command included `env.trajectory_tracking_reference_path=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.
- resolved config evidence: `params/env.yaml` contains `trajectory_tracking_enabled: true`, the external reference path above, and `trajectory_tracking_phase_observations: false`.
- observation/network evidence: RL-Games built the actor/critic MLP with `72` observations.
- checkpoint: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124252/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth
- caveat: the `rew_-inf` suffix is expected for this tiny three-epoch smoke because no environment terminated before max epochs; the TensorBoard event file is 0 bytes, so the reward/term sanity check must come from checkpoint rollout eval.

Next:
- Run short eval with the same external reference path, 4 envs, 120 steps, no video, and inspect `metric_summaries` plus the new `trajectory_tracking_reference` summary in `metrics.json`.

## 2026-06-11T14:44:00-07:00 - external-reference checkpoint eval launch

Goal:
- Inspect finite rollout metrics for the checkpoint from the external-reference RL smoke.

Command / Job:
- job_id: 1027700 `franka_cube_traj_60mm_eval`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_60mm_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_60mm_ref_eval_smoke_20260611_124447,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl_smoke_20260611_124252/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth,NUM_ENVS=4,NUM_STEPS=120,VIDEO_LENGTH=120,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,USE_CUDA_GRAPH=False,SEED=42,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027700.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_60mm_ref_eval_smoke_20260611_124447/metrics.json

Acceptance Criteria:
- Eval loads checkpoint and same external compact reference.
- 120 rollout steps complete with finite reward and tracking metric summaries.
- `trajectory_tracking_reference` in metrics reports `graspgenx_source=true`, `curobo_validated=false`, and the external path, not the manual template.
- No immediate reset/termination pathology.

Result:
- job_id: 1027700 completed `0:0` after `00:00:47` on `pool0-00016`.
- remote_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_60mm_ref_eval_smoke_20260611_124447/metrics.json
- local_copy: cluster_results/l401/franka_cube_traj_tracking_60mm_ref_eval_smoke_20260611_124447/
- rollout: 120/120 steps completed, `done_count=0`, `reward_mean=1.7681481450796128`, `reward_final=1.777575969696045`, `success_rate_mean=0.0`.
- finite_check: recursive JSON numeric scan reported `nonfinite_count=0`.
- tracking_reference: `source=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `waypoint_count=9`, `transform_policy=transform_task_space_waypoints_by_cube_pose`, `joint_trajectory_policy=do_not_transform_joint_trajectories`.
- tracking_reward: mean `0.04245300240193804`, final `0.04073528200387955`, max `0.09654676914215088`.
- tracking_errors: position mean `0.34843481456240016`, final `0.27720147371292114`; orientation mean `0.1784153180817763`, final `0.19622422754764557`; gripper mean `0.037403301584223905`, final `0.03949643671512604`.
- safety: tracking target clearance min `0.245569109916687`; unsafe target rate max `0.0`; finger table clearance min `0.05314174294471741`; finger table violation max `0.0`.

Analysis:
- The external-reference tracking path now has a real task smoke, short RL smoke, and checkpoint rollout smoke in Isaac/DEXTRAH, all loading the same compact 60 mm reference.
- The short RL checkpoint is not a performance claim: three epochs ended before any environment terminated and did not lift the cube. It is only evidence that the training/eval path is wired, finite, and baseline observation-compatible.
- The next useful step is a modest one-GPU scale-up, still not full training, with enough iterations to produce non-empty scalar logs and at least a small number of resets/episode statistics.

Next:
- Commit/push this worklog result.
- Launch a bounded one-GPU scale-up smoke with the same external reference, more envs/iterations than the 3-epoch wiring smoke, and explicit reduced CPU/memory Slurm resources.

## 2026-06-11T14:55:00-07:00 - bounded external-reference RL scale-up plan

Goal:
- Move beyond pure wiring smoke by running enough policy steps to observe timeout resets/episode statistics and scalar logging, while staying clearly below full training.

Hypothesis:
- A one-GPU 256-env, 25-epoch run with horizon 64 produces `25 * 64 = 1600` policy steps per env, exceeding the 600-step/10-second timeout and giving at least two timeout windows for episode/reward diagnostics.
- 256 envs should fit on one L40S with the already validated state-only Franka cube task; if it fails for memory or launch reasons, reduce env count before changing task code.

Planned Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=franka_cube_traj_60mm_rl25 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=<run>,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=256,HORIZON_LENGTH=64,MINIBATCH_SIZE=4096,CENTRAL_VALUE_MINIBATCH_SIZE=4096,MINI_EPOCHS=2,MAX_ITERATIONS=25,SAVE_FREQUENCY=5,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/<run>

Acceptance Criteria:
- No full training: 25 epochs only, one GPU.
- Job writes non-empty scalar/event or equivalent logs, resolved configs, and checkpoints.
- It reaches at least one timeout/reset window without NaNs, runaway reward/loss, or table/finger safety pathology.
- Follow-up eval of the latest checkpoint loads the same external reference and reports finite tracking metrics.

Launch:
- local_commit: 8388132ebab6a66ca6b3e4d60cea205f39991b6e
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at 8388132ebab6a66ca6b3e4d60cea205f39991b6e, detached clean
- job_id: 1027704 `franka_cube_traj_60mm_rl25`
- run_name: `franka_cube_traj_tracking_60mm_ref_rl25_20260611_124829`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027704.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl25_20260611_124829

Result Update:
- `1027704` completed `0:0` after `00:01:26` on `pool0-00016`.
- env/command evidence: 256 envs, horizon 64, 25 epochs, one GPU, external reference override in the train command.
- training progressed through epoch 25/25 with no traceback or NaN visible in stdout.
- checkpoint reward suffixes: ep5 `151.08821`, ep10 `843.2302`, ep15 `729.8349`, ep20 `850.1078`, ep25 `852.57153`.
- checkpoints: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl25_20260611_124829/nn/
- caveat: TensorBoard event file is still 0 bytes, so scalar/loss logging remains insufficient from the trainer side; use checkpoint rollout metrics as the current reward-term evidence and patch trainer logging later if this alternative graduates beyond smoke/scale-up.

Next:
- Run a 720-step eval of the epoch-25 checkpoint with the same external reference. This spans a 600-step timeout window and should expose reset/done behavior in addition to tracking reward/target-safety metrics.

## 2026-06-11T14:50:00-07:00 - rl25 checkpoint 720-step eval launch

Goal:
- Evaluate the bounded scale-up checkpoint across a timeout/reset window and inspect tracking reward/safety metrics.

Command / Job:
- job_id: 1027707 `franka_cube_traj_rl25_eval`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_rl25_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_60mm_ref_rl25_eval720_20260611_125035,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl25_20260611_124829/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_852.57153.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=43,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027707.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_60mm_ref_rl25_eval720_20260611_125035/metrics.json

Acceptance Criteria:
- 720/720 steps complete.
- `done_count` shows timeout/reset behavior rather than immediate reset pathology.
- Tracking reference summary remains the external 60 mm compact reference with `curobo_validated=false`.
- Tracking rewards/errors/target safety finite; unsafe target rate remains 0.

Result / Analysis:
- `1027707` completed `0:0` after `00:00:59` on `pool0-00016`; metrics fetched to `cluster_results/l401/franka_cube_traj_tracking_60mm_ref_rl25_eval720_20260611_125035/`.
- rollout: 720/720 steps, `done_count=5`, recursive numeric scan finite (`nonfinite_count=0`), reward mean `2.2687899066`, reward final `2.4857230186`.
- tracking_reference: external 60 mm compact reference loaded with `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `waypoint_count=9`, `transform_policy=transform_task_space_waypoints_by_cube_pose`, `joint_trajectory_policy=do_not_transform_joint_trajectories`.
- tracking metrics improved relative to the 3-epoch smoke: tracking reward mean `0.1123663048`, final `0.1652323902`; position error mean `0.1842913469`, final `0.0945282578`; orientation error mean `0.4052810603`; gripper error mean `0.0644654408`.
- abnormality: `cube_traj_tracking_unsafe_target_rate` reached max `0.25` and mean `0.0149305556`, even though the logged `cube_traj_tracking_target_table_clearance` mean stayed above `0.15`. This indicates at least one env produced an unsafe transformed task-space target while the eval logged only means.
- related policy behavior: `finger_table_clearance_violation` max `0.25`, cube lift max only `0.0039871`, success `0.0`, and gripper width collapsed near closed. This is not a performance success; it is a useful smoke exposing target-safety and policy-safety issues.

Patch Plan Before Edits:
- Keep `Dextrah-Franka-Cube-Grasp` baseline untouched and patch only the trajectory-tracking variant plus eval diagnostics.
- In `franka_cube_traj_tracking_env.py`, compute the target safety mask before reward assembly and zero the effective tracking phase weight for envs whose transformed task-space target violates `trajectory_tracking_min_target_table_clearance`. This prevents the policy from being rewarded for chasing an unsafe transformed target.
- Add log terms for effective/safe phase weight and min target clearance so the guard is visible in eval logs. Preserve the existing unsafe-rate diagnostic rather than hiding it.
- In `eval_rollout.py`, report min/max tensor metrics for tracking target clearance and finger/table clearance so future evals can distinguish a mean-safe batch from one unsafe env.
- Local validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/rl_games/eval_rollout.py`, `git diff --check`.
- Cluster validation after commit/deploy: rerun a bounded env/eval smoke with the same external 60 mm reference and inspect logs/metrics. The exact next job may reuse the RL25 checkpoint to compare the safety guard under the same policy.

Plan Refinement:
- While inspecting the transform path, I found that `trajectory_tracking_follow_current_cube_pose=False` still used the current cube quaternion. That would continue to rotate reference waypoints with a tipped/moved cube even when the intent is reset-pose tracking.
- Patch the tracking variant to store a reset/reference object quaternion on reset and use `(cube_initial_pos, reset_cube_quat)` when `trajectory_tracking_follow_current_cube_pose=False`.
- Change the trajectory-tracking variant default to reset/reference-pose tracking. This is still a task-space transform under object randomization, but it avoids moving the demonstration target with post-contact cube tumbles; the current-pose behavior remains available as an explicit ablation.

## 2026-06-11T12:57:48-07:00 - reset-pose tracking safety patch validation launch

Goal:
- Validate the unsafe-target patch in a real Isaac/DEXTRAH task-registration smoke before any additional RL training.

Change:
- `franka_cube_traj_tracking_env.py`: store reset/reference object quaternion, use reset-pose task-space transforms by default, and zero the effective tracking phase weight for targets below `trajectory_tracking_min_target_table_clearance`.
- `franka_cube_traj_tracking_env_cfg.py`: default `trajectory_tracking_follow_current_cube_pose=False` for this variant.
- `eval_rollout.py` and `validate_franka_cube_grasp_env.py`: expose min/max clearance and new tracking safety-gate diagnostics.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: dfd55878f102359d09ccb5bc57a7236baffeaf15
- push/pull: pushed to origin; l401 agent worktree deployed at exact commit using HTTPS fallback after SSH git auth failed
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at dfd55878f102359d09ccb5bc57a7236baffeaf15, detached clean
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog

Local Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`: passed
- `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed
- `git diff --check`: passed

Planned Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_reset_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_resetpose_ref_env_smoke_20260611_125748,NUM_ENVS=4,NUM_STEPS=160,VIDEO_LENGTH=160,CAPTURE_VIDEO=False,PRINT_INTERVAL=40,SEED=44,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_resetpose_ref_env_smoke_20260611_125748/metrics.json

Acceptance Criteria:
- Task registers and short rollout completes with finite rewards/observations.
- Observation shape remains baseline `[4, 72]`; baseline task registration still resolves.
- Runtime reference summary reports the external 60 mm compact reference, `curobo_validated=false`, and `runtime_object_pose_policy=reset_cube_pose`.
- Tracking logs include effective phase weight and min clearance; `tracking_unsafe_target_rate_max=0.0`.

Launch:
- job_id: 1027714 `franka_cube_traj_reset_smoke`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027714.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_resetpose_ref_env_smoke_20260611_125748

Result:
- status: passed; Slurm completed `0:0` after `00:00:42` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_env_smoke_20260611_125748/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_env_smoke_20260611_125748/validate_franka_cube_1027714.out`
- metrics: validation `passed=true`, failed checks `[]`, recursive numeric scan `nonfinite_count=0`.
- task/obs: task registration passed; baseline task registration still resolved; reset observation shape `[4, 72]`; rollout completed 160/160 steps with `done_count=0`, `early_done_count=0`.
- tracking_reference: external 60 mm compact reference, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `runtime_object_pose_policy=reset_cube_pose`, `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`.
- tracking_safety: `tracking_unsafe_target_rate_max=0.0`, `tracking_target_table_clearance_batch_min=0.2197389006614685`, `tracking_effective_phase_weight_mean=0.44981886483728883`.
- reward: rollout reward mean `1.8193612858653068`, final `1.5274521112442017`; tracking reward mean `0.0430974296759814`, final `0.07310818880796432`.

Analysis:
- The reset-pose reference transform addresses the previous immediate target-safety issue in the short real Isaac/DEXTRAH env smoke. It also keeps the strict reward-only observation contract.
- This does not yet prove policy performance. The next check should evaluate the existing RL25 checkpoint under the patched reset-pose target for a 720-step horizon to compare safety, reset behavior, and finite metrics across a timeout window. Because the checkpoint was trained before the reset-pose default, use the result as a safety/debug smoke, not as a fair performance number.

## 2026-06-11T12:59:36-07:00 - reset-pose RL25 checkpoint eval launch

Goal:
- Evaluate the existing RL25 checkpoint under the patched reset-pose target transform for a 720-step horizon.

Hypothesis:
- The patched reset-pose transform should keep transformed task-space targets clear of the table across the longer rollout (`cube_traj_tracking_unsafe_target_rate` remains 0 and batch-min clearance is visible in metrics).
- The policy may score differently because it was trained under the previous current-pose target default; this eval is only a safety/debug comparison.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_reset_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_125936,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_60mm_ref_rl25_20260611_124829/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_852.57153.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=45,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_125936/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite reward/tracking metrics and no immediate reset pathology.
- Tracking reference summary reports external 60 mm reference, `curobo_validated=false`, and `runtime_object_pose_policy=reset_cube_pose`.
- Eval metrics include per-step min/max target clearance; `cube_traj_tracking_unsafe_target_rate` max stays `0.0`.

Launch:
- job_id: 1027715 `franka_cube_traj_reset_eval`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027715.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_125936

Result:
- status: passed; Slurm completed `0:0` after `00:00:59` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_125936/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_125936/eval_franka_cube_1027715.out`
- rollout: 720/720 steps, `done_count=4`, reward mean `2.2150335532095697`, reward final `2.127321720123291`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `runtime_object_pose_policy=reset_cube_pose`, `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `cube_traj_tracking_safe_target_rate` min/mean/final `1.0`; target clearance batch min over all steps `0.06511414051055908`, above the configured `0.025`.
- tracking: tracking reward mean `0.122686019873557`, final `0.09833449125289917`; position error mean `0.18823349295804898`; orientation error mean `0.35798341702255937`; gripper error mean `0.06324747810140252`.
- reset_behavior: phase-progress drops at steps 438, 469, and 599; summary `done_count=4`; no immediate reset pathology.
- remaining policy issue: no lift/success (`cube_lift_height_max` max `0.013358712196350098`, success `0.0`), gripper still often collapses closed, and finger/table violation still appears in 43 steps with max violation `0.14615871012210846` and min finger clearance `0.02134603261947632`.

Analysis:
- The target-generation/safety issue exposed by the old current-pose eval is fixed for the reset-pose transform: transformed references remain above the table and unsafe targets no longer appear over a timeout-window rollout.
- The existing RL25 policy was trained under the old current-pose target default, so this eval is not a fair reset-pose training result. The continuing finger-clearance and no-lift behavior must be checked after training under the patched reset-pose target.

Next:
- Commit/push this worklog result, redeploy the l401 worktree to the new commit, and run a tiny reset-pose RL smoke with the same external 60 mm reference. If the smoke writes a checkpoint and eval remains sane, scale again with reset-pose training.

## 2026-06-11T13:01:34-07:00 - reset-pose short RL smoke plan

Goal:
- Verify RL-Games training still runs under the patched reset-pose trajectory target before launching another bounded scale-up.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_reset_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134

Acceptance Criteria:
- Job completes without Hydra/config errors; resolved env config has `trajectory_tracking_follow_current_cube_pose=false` and the external reference path.
- Actor/critic observation dimension remains 72.
- Checkpoint is written by epoch 3; no visible NaN/traceback in training log.
- Follow-up eval can load the checkpoint and report finite reset-pose tracking metrics.

Launch:
- local_commit: e822cc1e36bc9e3bcc361a0f4e5167144f23945b
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at e822cc1e36bc9e3bcc361a0f4e5167144f23945b, detached clean
- job_id: 1027716 `franka_cube_traj_reset_rl`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027716.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134

Result:
- status: passed; Slurm completed `0:0` after `00:00:48` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134/`
- resolved_config: `params/env.yaml` has `observation_space: 72`, `trajectory_tracking_enabled: true`, external reference path, `trajectory_tracking_phase_observations: false`, and `trajectory_tracking_follow_current_cube_pose: false`.
- training_log: actor and critic MLPs both built with `72`; epochs 1/3, 2/3, and 3/3 completed; checkpoint written at `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth`.
- caveat: `rew_-inf` suffix is expected for this tiny smoke because no environment terminated before max epochs. TensorBoard event file is still 0 bytes, so rollout eval remains the reward-term evidence.
- log_scan: no traceback/Hydra/runtime error; the only `inf` grep hit is the expected checkpoint filename suffix.

Next:
- Run a short eval of the epoch-3 reset-pose checkpoint to confirm finite tracking metrics and target safety under the freshly trained reset-pose configuration.

## 2026-06-11T13:03:36-07:00 - reset-pose short RL eval launch

Goal:
- Evaluate the tiny reset-pose RL-smoke checkpoint with the same external 60 mm reference.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_reset_eval3 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_resetpose_ref_eval_smoke_20260611_130336,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl_smoke_20260611_130134/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth,NUM_ENVS=4,NUM_STEPS=120,VIDEO_LENGTH=120,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,USE_CUDA_GRAPH=False,SEED=46,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_ref_eval_smoke_20260611_130336/metrics.json

Acceptance Criteria:
- 120/120 steps complete, finite metrics, no immediate reset pathology.
- Tracking reference summary reports reset-pose runtime policy, external 60 mm compact reference, and `curobo_validated=false`.
- `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target and finger clearance diagnostics are present.

Launch:
- job_id: 1027717 `franka_cube_traj_reset_eval3`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027717.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_ref_eval_smoke_20260611_130336

Result:
- status: passed; Slurm completed `0:0` after `00:00:48` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_eval_smoke_20260611_130336/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_eval_smoke_20260611_130336/eval_franka_cube_1027717.out`
- rollout: 120/120 steps, `done_count=0`, reward mean `1.7085258146127065`, reward final `1.7065653800964355`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `runtime_object_pose_policy=reset_cube_pose`, `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `safe_target_rate` min/mean/final `1.0`; target clearance min over all steps `0.2505703568458557`.
- contact_safety: finger table clearance min over all steps `0.04527193307876587`; finger table violation max `0.0`.
- behavior: no lift yet (`cube_lift_height_max` max `0.01784271001815796`) and no success, as expected for a 3-epoch wiring smoke.

Analysis:
- The patched reset-pose tracking variant has now passed real env smoke, train smoke, and checkpoint eval with the external 60 mm compact reference.
- The path is viable enough for a bounded one-GPU reset-pose scale-up, but not for full training. The next run should be comparable in scale to the previous 25-epoch current-pose RL25 smoke, then evaluated across 720 steps.

## 2026-06-11T13:05:09-07:00 - reset-pose bounded RL25 plan

Goal:
- Run a bounded reset-pose trajectory-tracking scale-up that is large enough to see timeout/reset behavior and basic policy trends, while staying far below full training.

Hypothesis:
- With reset-pose targets and target-safety gating, the 25-epoch one-GPU run should keep target safety clean and may reduce the finger-table issue seen in the old current-pose checkpoint.
- If reset-pose training is behaving sensibly, the 720-step eval should remain finite, target-safe, and show no immediate reset pathology. It may still not achieve lifting at this scale.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=franka_cube_traj_reset_rl25 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=256,HORIZON_LENGTH=64,MINIBATCH_SIZE=4096,CENTRAL_VALUE_MINIBATCH_SIZE=4096,MINI_EPOCHS=2,MAX_ITERATIONS=25,SAVE_FREQUENCY=5,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509

Acceptance Criteria:
- Still not full training: one GPU, 256 envs, 25 epochs.
- Resolved env config remains reset-pose with external reference and observation space 72.
- Epochs complete without traceback/NaN; checkpoint written at epoch 25.
- Follow-up 720-step eval has finite metrics, no unsafe tracking targets, and no immediate reset pathology.

Launch:
- local_commit: 9abe6fbcd732afbe4a1339d3f4ffed72d29ff82c
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at 9abe6fbcd732afbe4a1339d3f4ffed72d29ff82c, detached clean
- job_id: 1027718 `franka_cube_traj_reset_rl25`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027718.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509

Result:
- status: passed; Slurm completed `0:0` after `00:01:27` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509/` with params, TensorBoard sidecar, and stdout log; checkpoints remain on NFS under the run `nn/` directory.
- resolved_config: `params/env.yaml` has `observation_space: 72`, `trajectory_tracking_enabled: true`, external reference path, `trajectory_tracking_phase_observations: false`, and `trajectory_tracking_follow_current_cube_pose: false`.
- training_log: actor and critic MLPs both built with `72`; epochs 1-25 completed with no traceback/runtime/NaN pattern in stdout.
- checkpoint reward suffixes: ep5 `202.9117`, ep10 `968.0235`, ep15 `639.41724`, ep20 `931.91156`, ep25 `864.1978`.
- checkpoint: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_864.1978.pth
- caveat: TensorBoard event file is still 0 bytes, so follow-up rollout eval is the usable reward-term/safety evidence.

Next:
- Evaluate the epoch-25 checkpoint for 720 steps with the same external 60 mm reference and reset-pose target policy.

## 2026-06-11T13:07:48-07:00 - reset-pose RL25 checkpoint 720-step eval launch

Goal:
- Inspect the bounded reset-pose RL25 checkpoint across a timeout/reset window.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_reset25_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_resetpose_ref_rl25_20260611_130509/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_864.1978.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=47,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite metrics and no immediate reset pathology.
- Tracking reference summary reports reset-pose runtime policy, external 60 mm compact reference, and `curobo_validated=false`.
- `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target min clearance remains above `0.025`.
- Inspect policy behavior: success/lift, finger table clearance, gripper collapse, and reset/termination count.

Launch:
- job_id: 1027719 `franka_cube_traj_reset25_eval`
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027719.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748

Result:
- status: passed; Slurm completed `0:0` after `00:00:58` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748/eval_franka_cube_1027719.out`
- rollout: 720/720 steps, `done_count=7`, reward mean `1.9178464568323559`, reward final `2.1220836639404297`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `runtime_object_pose_policy=reset_cube_pose`, `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`, source duration `22.033333333333335` s.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `cube_traj_tracking_safe_target_rate` min/mean/final `1.0`; target clearance batch min over all steps `0.06511414051055908`, above the configured `0.025`.
- task_behavior: no success/lift; `cube_lift_height_max` max only `0.030698418617248535`, `has_lifted_cube` remains `0.0`.
- finger_safety: `finger_table_clearance_min` min `0.023657560348510742`; `finger_table_clearance_violation_max` max `0.053697600960731506` across 8 violation steps around steps 373-380.
- tracking_metrics: tracking reward mean `0.11186522472028931`, final `0.07273757457733154`; position error mean `0.2378308145329356`; orientation error mean `0.516163813509047`; gripper error mean `0.01963886580973243`.
- phase_progress: max `0.35835859179496765`, final `0.11081695556640625`; phase drops at steps 6, 211, 497, and 599 due environment resets.

Analysis:
- Target-generation safety is now clean under reset-pose transforms: no unsafe task-space targets, the safety gate never had to zero targets, and baseline observation size remained unchanged in the preceding smoke/train/eval sequence.
- The remaining failure is behavior/learning, not target validity: the policy does not lift and sometimes dips a finger below the configured table clearance.
- The most suspicious wiring issue is reference timing. The compact GraspGenX/cuRobo reference still runs over `22.033333333333335` s, while the DEXTRAH episode is 10 s. The 720-step eval never gets beyond phase progress `0.358`, so the policy mainly sees approach targets and never reaches the intended grasp/lift phase before resets/timeouts.

Next:
- Commit and push this worklog result first, per orchestrator request.
- Patch the trajectory-tracking variant to retime external compact references to a runtime horizon shorter than the DEXTRAH episode, while preserving source timing in the reference summary and keeping `curobo_validated=false`.
- Add a validator check that the runtime reference duration fits within the task episode, then rerun task-registration/env smoke before any further RL.

## 2026-06-11T13:12:00-07:00 - reference retiming patch plan

Goal:
- Fix the identified trajectory timing mismatch without changing the production `Dextrah-Franka-Cube-Grasp` baseline or adding reference observations.

Hypothesis:
- The 60 mm compact GraspGenX/cuRobo export is a task-space path with useful approach/grasp/lift phases, but its source timestamps span `22.033333333333335` s. Retiming the same task-space waypoints to an 8 s runtime reference should let a 10 s DEXTRAH episode reach all phases and expose the grasp/lift curriculum to RL.
- Because the source export is still not exact DEXTRAH-geometry/cuRobo-validated in one single run, runtime summaries must continue reporting `curobo_validated=false` and the 45 mm vs 60 mm history remains a caveat.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: add `trajectory_tracking_reference_duration_s=8.0`.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: preserve source timestamps/duration, normalize waypoint timestamps to the configured runtime duration when positive, and report source/runtime durations plus the retime policy in `trajectory_tracking_reference_summary()`.
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`: check that the runtime reference duration fits within the task episode and expose the source/runtime timing in validation metrics.
- Owned worklog: record patch, checks, l401 deploy, job ids, and metrics.

Validation Plan:
- Local cheap checks: `python3 -m py_compile` on touched Python files, `git diff --check`, wrapper syntax as needed.
- Commit/push, deploy exact commit to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`.
- First cluster validation only: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`, 4 envs, short rollout, same 60 mm compact reference. Acceptance: obs stays `[4, 72]`, baseline task registration still resolves, summary reports runtime duration `8.0` s and source duration `22.033333333333335` s, tracking terms finite, unsafe target rate `0.0`, target clearance above margin, no immediate reset pathology.

Change:
- implementation_commit: `22f674cd42eaf79fa9e42433a9e2f1dff04a917a`
- push/pull: pushed to origin and deployed to l401 agent worktree at exact detached commit using HTTPS fallback after SSH git auth failed.
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `22f674cd42eaf79fa9e42433a9e2f1dff04a917a`, detached clean.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog.

Local Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py`: passed.
- `git diff --check`: passed.
- `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_retime_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430,NUM_ENVS=4,NUM_STEPS=240,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=40,SEED=48,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027720 `franka_cube_traj_retime_smoke`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430/metrics.json

Result:
- status: passed; Slurm completed `0:0` after `00:00:49` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_retime_ref_env_smoke_20260611_131430/validate_franka_cube_1027720.out`
- validation: `passed=true`, failed checks `[]`, recursive numeric scan `nonfinite_count=0`.
- task/obs: task registration passed; baseline task registration still resolved; reset observation shape `[4, 72]`; rollout completed 240/240 steps with `done_count=0`, `early_done_count=0`.
- reference_timing: `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `configured_runtime_duration_s=8.0`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `episode_length_s=10.0`; the new `trajectory_tracking_runtime_duration_within_episode` check passed.
- tracking_reference: external 60 mm compact reference, `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`, `runtime_object_pose_policy=reset_cube_pose`, `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`.
- tracking_safety: `tracking_unsafe_target_rate_max=0.0`, `tracking_target_table_clearance_batch_min=0.06511414051055908`, `tracking_effective_phase_weight_mean=0.5628080325822036`.
- rollout_reward: reward mean `1.7527947117884954`, final `1.498579502105713`; tracking reward mean `0.08229613187722862`, final `0.13901259005069733`.

Analysis:
- The retiming patch fixes the identified runtime mismatch at the task-registration level: the same task-space reference is now played over 8 s inside the 10 s episode while source duration remains auditable.
- Target safety remains clean under retimed playback; the tighter timing did not introduce table-clearance violations.
- This is still a reward-only variant with baseline observation size. The next question is whether a policy can learn from the retimed shaping without the earlier phase starvation.

Next:
- Commit/push this worklog result and redeploy the l401 agent worktree.
- Run a tiny retimed RL-Games smoke, then checkpoint eval, before any larger scale-up.

## 2026-06-11T13:17:04-07:00 - retimed reference short RL smoke launch

Goal:
- Verify RL-Games training still runs with the retimed 8 s reference and writes a checkpoint that can be evaluated.

Hypothesis:
- Since task-registration validation passed with finite tracking metrics and safe retimed targets, a tiny 3-epoch run should complete with the same baseline observation dimension. This only validates training wiring under retiming; it is not expected to solve the task.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `08ce93bb4afb294dee88f1202fcf64e82e028f6e`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `08ce93bb4afb294dee88f1202fcf64e82e028f6e`, detached clean.
- push/pull: pushed to origin and deployed on l401 using HTTPS fallback after SSH git auth failed.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_retime_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_retime_ref_rl_smoke_20260611_131704,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027721 `franka_cube_traj_retime_rl`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl_smoke_20260611_131704

Acceptance Criteria:
- Job completes without traceback/Hydra/config errors.
- Resolved env config has observation space `72`, `trajectory_tracking_reference_duration_s: 8.0`, external reference path, `trajectory_tracking_phase_observations: false`, and `trajectory_tracking_follow_current_cube_pose: false`.
- Actor/critic observation dimension remains 72; checkpoint is written by epoch 3.
- Follow-up eval can load the checkpoint and report finite retimed tracking metrics.

Result:
- status: passed; Slurm completed `0:0` after `00:00:48` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_retime_ref_rl_smoke_20260611_131704/` with params, TensorBoard sidecar, and stdout log; checkpoints remain on NFS under the run `nn/` directory.
- resolved_config: `params/env.yaml` has `episode_length_s: 10.0`, `observation_space: 72`, `trajectory_tracking_enabled: true`, external reference path, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_phase_observations: false`, and `trajectory_tracking_follow_current_cube_pose: false`.
- training_log: actor and critic MLPs both built with `72`; epochs 1/3, 2/3, and 3/3 completed; no traceback/Hydra/runtime error and no NaN pattern in stdout.
- checkpoints: epoch 1/2/3 checkpoints were written; selected eval checkpoint `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl_smoke_20260611_131704/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_9.2871895.pth`.
- caveat: TensorBoard event file is still 0 bytes; rollout eval remains the reward-term/safety evidence.

Next:
- Evaluate the epoch-3 checkpoint for 720 steps so retimed phase progress can reach the end of the 8 s reference.

## 2026-06-11T13:18:55-07:00 - retimed short RL checkpoint 720-step eval launch

Goal:
- Verify the tiny retimed checkpoint can be loaded and evaluated across a full reference horizon.

Hypothesis:
- The checkpoint itself will not solve the task, but rollout metrics should remain finite, target-safe, and show phase progress reaching near 1.0 under the 8 s runtime reference.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_retime_eval3 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_retime_ref_eval720_20260611_131855,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl_smoke_20260611_131704/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_9.2871895.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=49,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027723 `franka_cube_traj_retime_eval3`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_retime_ref_eval720_20260611_131855/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite metrics and no immediate reset pathology.
- Reference summary reports runtime duration `8.0`, source duration `22.033333333333335`, reset-pose target policy, and `curobo_validated=false`.
- Phase progress reaches near 1.0 in at least one interval; `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target min clearance remains above `0.025`.

Result:
- status: passed; Slurm completed `0:0` after `00:00:58` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_retime_ref_eval720_20260611_131855/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_retime_ref_eval720_20260611_131855/eval_franka_cube_1027723.out`
- rollout: 720/720 steps, `done_count=4`, reward mean `1.7883200655380884`, reward final `1.933864712715149`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `curobo_validated=false`, `validation_passed=true`.
- phase_progress: `traj_phase_progress` max `1.0` at step 480, final `0.25208336114883423`, with one reset drop at step 599. This proves the full reference now fits within the episode.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `safe_target_rate` min/mean/final `1.0`; target clearance min over all steps `0.06511414051055908`, above the configured `0.025`.
- finger_safety: `finger_table_clearance_min` min `0.05048090219497681`; `finger_table_clearance_violation_max` max `0.0`; no violation steps.
- task_behavior: no lift/success, as expected for a 3-epoch wiring smoke; `cube_lift_height_max` max `0.011038422584533691`, `has_lifted_cube` remains `0.0`.
- tracking_metrics: tracking reward mean `0.10420224249569907`, final `0.13189668953418732`; position error mean `0.23880642677346867`; orientation error mean `0.1835750435789426`; gripper error mean `0.03696417411685818`.

Analysis:
- The retiming patch fixes the phase-starvation problem: the 8 s runtime reference reaches close/lift phases before timeout while staying target-safe.
- The tiny checkpoint is not a performance result. The next useful test is a bounded one-GPU 25-iteration scale-up comparable to the earlier RL25 smoke, now using the retimed target schedule.

Next:
- Commit/push this worklog evidence, redeploy the l401 worktree, and launch a bounded retimed RL25 run. If it completes, evaluate 720 steps and inspect lift/success, finger clearance, phase tracking, and target safety.

## 2026-06-11T13:21:07-07:00 - retimed bounded RL25 plan

Goal:
- Run a bounded retimed trajectory-tracking scale-up to see whether exposing the full approach/grasp/lift reference improves behavior relative to the previous phase-starved RL25 run.

Hypothesis:
- Compared with the 22 s source-timing run, the 8 s retimed run should train against all phases within the episode. The scale is still too small to guarantee success, but the 720-step eval should remain finite, target-safe, and may show stronger gripper/lift behavior.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=franka_cube_traj_retime_rl25 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_retime_ref_rl25_20260611_132107,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=256,HORIZON_LENGTH=64,MINIBATCH_SIZE=4096,CENTRAL_VALUE_MINIBATCH_SIZE=4096,MINI_EPOCHS=2,MAX_ITERATIONS=25,SAVE_FREQUENCY=5,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027724 `franka_cube_traj_retime_rl25`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl25_20260611_132107

Acceptance Criteria:
- Still not full training: one GPU, 256 envs, 25 iterations, no self-relaunch.
- Resolved env config remains reward-only with observation space 72, external reference path, `trajectory_tracking_reference_duration_s: 8.0`, phase observations false, and reset-pose target policy.
- Epochs complete without traceback/NaN; checkpoint written at epoch 25.
- Follow-up 720-step eval has finite metrics, phase progress reaching 1.0, no unsafe tracking targets, and no immediate reset pathology.

Launch:
- implementation_commit: `26fa0b7ef0b412979aa6476c075125c49a32afcc`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `26fa0b7ef0b412979aa6476c075125c49a32afcc`, detached clean.
- job_id: 1027724 `franka_cube_traj_retime_rl25`

Result:
- status: passed; Slurm completed `0:0` after `00:01:25` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_retime_ref_rl25_20260611_132107/` with params, TensorBoard sidecar, and stdout log; checkpoints remain on NFS under the run `nn/` directory.
- resolved_config: `params/env.yaml` has `episode_length_s: 10.0`, `observation_space: 72`, `trajectory_tracking_enabled: true`, external reference path, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_phase_observations: false`, and `trajectory_tracking_follow_current_cube_pose: false`.
- training_log: actor and critic MLPs both built with `72`; epochs 1-25 completed; no traceback/Hydra/runtime error and no NaN pattern in stdout.
- checkpoint reward suffixes: ep5 `311.5034`, ep10 `762.69403`, ep15 `714.5559`, ep20 `952.6169`, ep25 `937.84894`.
- checkpoint: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl25_20260611_132107/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_937.84894.pth
- caveat: TensorBoard event file is still 0 bytes; rollout eval remains the usable reward-term/safety evidence.

Next:
- Evaluate the epoch-25 checkpoint for 720 steps with the retimed reference.

## 2026-06-11T13:24:11-07:00 - retimed RL25 checkpoint 720-step eval launch

Goal:
- Inspect the bounded retimed RL25 checkpoint across a timeout/reset window.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_retime25_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_retime_ref_rl25_20260611_132107/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_937.84894.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=50,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027726 `franka_cube_traj_retime25_eval`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite metrics and no immediate reset pathology.
- Reference summary reports runtime duration `8.0`, source duration `22.033333333333335`, reset-pose target policy, and `curobo_validated=false`.
- Phase progress reaches 1.0; `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target min clearance remains above `0.025`.
- Inspect policy behavior: success/lift, finger table clearance, gripper collapse, and reset/termination count.

Result:
- status: passed; Slurm completed `0:0` after `00:00:58` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_retime_rl25_eval720_20260611_132411/eval_franka_cube_1027726.out`
- rollout: 720/720 steps, `done_count=5`, reward mean `2.421528760592143`, reward final `2.6456546783447266`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `curobo_validated=false`, `validation_passed=true`.
- phase_progress: `traj_phase_progress` max `1.0` at step 480, final `0.24895834922790527`, with a reset drop at step 599.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `safe_target_rate` min/mean/final `1.0`; target clearance min over all steps `0.06511414051055908`, above the configured `0.025`.
- finger_safety: `finger_table_clearance_min` min `0.04968386888504028`; `finger_table_clearance_violation_max` max `0.0`; no violation steps.
- task_behavior: still no lift/success; `cube_lift_height_max` max only `0.01680278778076172`, `has_lifted_cube` remains `0.0`.
- tracking_metrics: tracking reward mean `0.3129379769994153`, final `0.23790881037712097`; position error mean `0.13399624147245454`; orientation error mean `0.6262307724811964`; gripper error mean `0.01597770556602174`.
- behavior_metrics: gripper width mean `0.02455970673686857`, min `0.00021008600015193224`; EE-to-cube mean `0.07299324613478449`; finger-center-to-cube mean `0.10512903414459693`.

Analysis:
- Retiming remains valid and safe under the RL25 checkpoint: the reference reaches the lift phase inside the episode, unsafe target rate stays zero, and finger-table violations are gone.
- The RL25 policy improves reward and tracking/approach metrics compared with the phase-starved reset-pose RL25 eval, but it still does not establish a useful grasp/lift. The gripper collapses nearly closed while the finger-center distance remains roughly 10 cm on average, and orientation error is high during the retimed run.
- The next bounded iteration should target behavior rather than target generation: gripper schedule and orientation/contact reward balance are likely suspects.

Next:
- Generate the requested inspectable artifact bundle before launching more training.

## 2026-06-11T13:27:29-07:00 - retimed artifact bundle plan

Goal:
- Produce inspectable local artifacts comparing the old phase-starved trajectory-tracking path with the retimed path, while continuing the bounded debug loop.

Hypothesis:
- The plots/report should make the retiming effect obvious: phase progress should reach `1.0` after retiming while target safety remains clean. The same artifacts should also expose the remaining behavior failure: no lift/success and imperfect approach/grasp behavior after RL25.

Planned Change:
- Add a small reproducible report generator under `dextrah_lab/scene_scripts/` that reads existing fetched JSON metrics and training logs, writes a markdown comparison report, CSV/JSON summary, phase/safety PNG, and behavior PNG into an ignored local artifact bundle under `cluster_results/l401/`.
- Include these completed runs: old phase-starved reset-pose RL25/eval `1027718`/`1027719`, retimed env smoke `1027720`, retimed 3-epoch eval `1027723`, retimed RL25 train `1027724`, and retimed RL25 eval `1027726`.
- Open the most useful artifact with `viz-open` and record the local path/URL.

Validation Plan:
- Run `python3 -m py_compile` on the new report script and `git diff --check`.
- Run the generator locally against fetched artifacts and inspect its summary output.
- If `1027726` metrics confirm no lift/success, use the comparison to choose the next bounded patch/ablation before any new training scale-up.

Result:
- status: passed; generated from existing fetched metrics/logs only, no new training launched.
- generator: `dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py`
- command: `python3 dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py --root cluster_results/l401 --output-dir cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000`
- artifact_dir: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000`
- report: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/comparison_report.md`
- summary_json: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/summary.json`
- summary_csv: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/summary.csv`
- phase_safety_png: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/phase_progress_and_target_safety.png`
- behavior_png: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/behavior_reward_lift_finger_metrics.png`
- viz_open_phase_safety: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/phase_progress_and_target_safety.png`
- viz_open_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/comparison_report.md`

Validation:
- `python3 -m py_compile dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py`: passed.
- `git diff --check`: passed.
- Artifact inspection: report table includes jobs `1027718`, `1027719`, `1027720`, `1027723`, `1027724`, `1027726`; summary JSON contains 6 run records; PNGs open locally at `1500x1142` and `1500x1254`.

Analysis:
- Artifact conclusion matches the rollout evidence: retiming fixes phase starvation (`0.3584` max phase before retime vs `1.0` after), target safety remains clean (`unsafe_target_rate_max=0.0`, target clearance min `0.0651` m), but behavior is not yet successful (`success=0.0`, RL25 max lift `0.0168` m).
- The artifact bundle should be regenerated after each next ablation so the comparison remains inspectable without rereading raw logs.

Next:
- Commit and push the generator plus worklog.
- Continue bounded debugging with a small variant-only ablation around gripper schedule/orientation/contact shaping before any additional training scale-up.

## 2026-06-11T13:35:44-07:00 - gripper schedule contact-width clamp plan

Goal:
- Remove the most obvious reward-shaping mismatch in the trajectory-tracking variant before any further training scale-up.

Hypothesis:
- The compact GraspGenX/cuRobo reference uses `gripper_width=0.0` as a close command, but the DEXTRAH Franka task logs/rewards `gripper_width` as measured fingertip-body separation. Rewarding the policy for measured width `0.0` encourages collapse even when the gripper is not enclosing the cube. The existing cube reward tests treat `0.024` m as a closed-near contact width, so clamping the tracking target to at least `0.024` m should preserve close-phase intent without rewarding an impossible over-closed measured width.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: add a variant-only `trajectory_tracking_min_target_gripper_width=0.024` config field. Setting it to `0.0` restores raw reference widths.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: clamp loaded reference gripper widths into `[min_target_gripper_width, max_gripper_width]`, keep source/runtime width stats, and report the clamp policy in `trajectory_tracking_reference_summary()`.
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`: extend validation/details to prove the runtime reference no longer contains measured target width `0.0` when the clamp is enabled.

Validation Plan:
- Local: `python3 -m py_compile` on touched Python files, `git diff --check`.
- Cluster smoke only: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`, 4 envs, short validation rollout against the same 60 mm compact reference. Acceptance: obs remains `[4,72]`, baseline task registration still resolves, runtime summary reports `min_target_gripper_width_m=0.024`, target gripper min is `0.024`, target safety remains clean, tracking metrics finite, and no immediate reset pathology.

Change:
- implementation_commit: `c786e59eb6058081ff5d0d8b27c1f947b66f1e40`
- push/pull: pushed to origin and deployed on l401 agent worktree using HTTPS fallback after SSH Git auth failed.
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `c786e59eb6058081ff5d0d8b27c1f947b66f1e40`, detached clean.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog.

Local Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py`: passed.
- `git diff --check`: passed.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_gripclamp_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_gripclamp_env_smoke_20260611_133800,NUM_ENVS=4,NUM_STEPS=240,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=40,SEED=51,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027728 `franka_cube_traj_gripclamp_smoke`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027728.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_gripclamp_env_smoke_20260611_133800/metrics.json

Result:
- status: passed; Slurm completed `0:0` after `00:00:45` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_env_smoke_20260611_133800/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_env_smoke_20260611_133800/validate_franka_cube_1027728.out`
- validation: `passed=true`, 35 checks, failed checks `[]`, recursive numeric scan `nonfinite_count=0`.
- task/obs: reset observation shape `[4, 72]`; rollout completed 240/240 steps with `done_count=0`, `early_done_count=0`.
- gripper_policy: `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`; source gripper width min/max `0.0`/`0.07999999821186066`; runtime gripper width min/max `0.024`/`0.07999999821186066`; `min_target_gripper_width_m=0.024`.
- tracking_reference: external 60 mm compact reference, `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `curobo_validated=false`, `validation_passed=true`.
- target_safety: `tracking_unsafe_target_rate_max=0.0`; target clearance min over rollout `0.06511414051055908`, above configured `0.025`.
- rollout_behavior: reward mean `2.3197436779737473`, final `7.1029462814331055`; max mean lift `0.031335875391960144`; final success rate `0.25`; final gripper width `0.029464447870850563`; min mean finger-table clearance `0.05007199943065643`.

Analysis:
- The gripper schedule clamp is wired correctly and does not break registration, observation shape, target transforms, or target safety.
- This is only a validation rollout, not a learned-policy result. The useful next step is a short RL-Games smoke with this clamp, followed by a bounded eval, to see whether avoiding the raw zero-width target reduces gripper collapse and improves approach/lift metrics.

Next:
- Commit/push this worklog result.
- Launch a tiny clamp RL smoke before any longer training: one GPU, 16 envs, 3 iterations, then evaluate the checkpoint for 720 steps if training completes.

## 2026-06-11T13:39:28-07:00 - gripper clamp short RL smoke launch

Goal:
- Verify RL-Games training still runs with the gripper target clamp and writes a checkpoint suitable for eval.

Hypothesis:
- The clamp should keep observation size and training wiring unchanged while changing only the trajectory tracking target for close-phase gripper width. A 3-iteration run is enough to catch config/runtime breakage and produce a checkpoint; it is not expected to solve the task.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `0eafbad235c2b821f86eb46f61095fdd3f710031`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `0eafbad235c2b821f86eb46f61095fdd3f710031`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_gripclamp_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027730 `franka_cube_traj_gripclamp_rl`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027730.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928

Acceptance Criteria:
- Job completes without traceback/Hydra/config errors.
- Resolved env config has observation space `72`, `trajectory_tracking_min_target_gripper_width: 0.024`, external reference path, `trajectory_tracking_reference_duration_s: 8.0`, phase observations false, and reset-pose target policy.
- Actor/critic observation dimension remains 72; checkpoint is written by epoch 3.
- Follow-up eval can load the checkpoint and report finite tracking metrics with runtime gripper target min `0.024`.

Result:
- status: passed; Slurm completed `0:0` after `00:00:52` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928/params/`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928/teacher_8gpu_1027730.out`; checkpoints remain on NFS under the run `nn/` directory.
- resolved_config: `params/env.yaml` has `observation_space: 72`, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_phase_observations: false`, `trajectory_tracking_min_target_gripper_width: 0.024`, `trajectory_tracking_follow_current_cube_pose: false`, and the external 60 mm reference path.
- training_log: actor and critic MLPs both built with `72`; epochs 1/3, 2/3, and 3/3 completed; no traceback/Hydra/runtime error and no NaN pattern in stdout.
- checkpoints: epoch 1/2/3 checkpoints were written; selected eval checkpoint `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.704905.pth`.
- caveat: TensorBoard event file is 0 bytes, consistent with prior short smokes; rollout eval remains the behavior evidence.

Analysis:
- The clamp does not break RL-Games wiring. This still is not a policy-performance result because it only ran 3 iterations.
- The next bounded check is a 720-step eval of this epoch-3 checkpoint to compare early behavior against the prior retimed 3-epoch eval and verify runtime gripper target min stays clamped.

Next:
- Commit/push this worklog checkpoint.
- Launch a 720-step eval of the gripper-clamp 3-epoch checkpoint; do not scale training until that eval is inspected.

## 2026-06-11T13:42:40-07:00 - gripper clamp short checkpoint eval launch

Goal:
- Evaluate the gripper-clamp 3-iteration checkpoint across a full 8 s retimed reference horizon.

Hypothesis:
- The tiny checkpoint will not solve the task, but metrics should remain finite and target-safe. Compared with the raw-zero gripper retimed 3-epoch eval, the runtime target gripper width should stay at or above `0.024` and the learned gripper should avoid collapsing to near zero.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `92e69c06b8c99a09d6c8ab97177c81f5bf2d0c33`; implementation code is `0eafbad235c2b821f86eb46f61095fdd3f710031`.
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `92e69c06b8c99a09d6c8ab97177c81f5bf2d0c33`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_gripclamp_eval3 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_gripclamp_eval720_20260611_134240,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl_smoke_20260611_133928/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.704905.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=52,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027731 `franka_cube_traj_gripclamp_eval3`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027731.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite metrics and no immediate reset pathology.
- Reference summary reports runtime duration `8.0`, source duration `22.033333333333335`, `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`, runtime gripper min `0.024`, reset-pose target policy, and `curobo_validated=false`.
- Phase progress reaches 1.0; `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target min clearance remains above `0.025`.
- Inspect policy behavior without overclaiming: gripper width, finger distances, lift/success, finger table clearance, resets/terminations.

Result:
- status: passed; Slurm completed `0:0` after `00:00:58` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/eval_franka_cube_1027731.out`
- rollout: 720/720 steps, `done_count=5`, reward mean `1.8378516377674208`, reward final `1.7632802724838257`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`, runtime gripper width min/max `0.024`/`0.07999999821186066`, source gripper width min/max `0.0`/`0.07999999821186066`, `curobo_validated=false`, `validation_passed=true`.
- phase_progress: `traj_phase_progress` max `1.0` at step 480, final `0.24947918951511383`, with one reset drop at step 599.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `safe_target_rate` min/mean/final `1.0`; target clearance min over all steps `0.06511414051055908`, above configured `0.025`.
- gripper_tracking: runtime target gripper width min `0.023999998345971107`; measured gripper width mean `0.041848357487469914`, min `0.04020160809159279`, final `0.041851937770843506`. The clamp avoided the previous near-zero measured collapse in this tiny checkpoint.
- finger_safety: `finger_table_clearance_min` min `0.03446274995803833`; `finger_table_clearance_violation_max` max `0.0`; no violation steps.
- task_behavior: no lift/success; `cube_lift_height_max` max `0.0`, `has_lifted_cube` remains `0.0`; EE-to-cube mean `0.170544162289136`; finger-center-to-cube mean `0.1705603083388673`.
- tracking_metrics: tracking reward mean `0.14404999003745617`, final `0.06403794139623642`; position error mean `0.1954453206103709`; orientation error mean `0.28658324856725004`; gripper error mean `0.025671546287938125`.

Analysis:
- This eval satisfies the bounded smoke acceptance criteria and removes the stale `job_id: pending` handoff state: job `1027731` ran to completion and produced finite metrics.
- The clamp changes the learned gripper behavior in the intended direction for this tiny checkpoint: measured gripper width no longer collapses to ~0.0. However, it does not by itself produce useful approach, grasp, lift, or success after only 3 training iterations.
- The next comparable bounded test is a 25-iteration one-GPU clamp run, matching the previous retimed RL25 scale, then a 720-step eval. That is still not full training and should reveal whether the clamp improves behavior at the same small scale or merely trades off approach reward.

Next:
- Commit/push this worklog result.
- Launch a bounded clamp RL25 run only after the worklog push, then monitor/evaluate it before considering larger training.

## 2026-06-11T13:46:13-07:00 - gripper clamp bounded RL25 plan

Goal:
- Compare the gripper-clamp variant at the same small scale as the previous retimed RL25 run.

Hypothesis:
- At 25 iterations, the clamp may prevent the raw-zero-width reward from encouraging over-closed gripper collapse while still preserving close-phase intent. The expected signal is not guaranteed success, but should be finite metrics, phase completion, safe targets, no finger-table regression, and either improved or clearly worsened approach/lift behavior relative to the unclamped RL25 eval.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `b4fc9d75a8be253ce542366960023682aeb07ad7`; implementation code is `0eafbad235c2b821f86eb46f61095fdd3f710031`.
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `b4fc9d75a8be253ce542366960023682aeb07ad7`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=franka_cube_traj_gripclamp_rl25 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_gripclamp_rl25_20260611_134613,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=256,HORIZON_LENGTH=64,MINIBATCH_SIZE=4096,CENTRAL_VALUE_MINIBATCH_SIZE=4096,MINI_EPOCHS=2,MAX_ITERATIONS=25,SAVE_FREQUENCY=5,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027732 `franka_cube_traj_gripclamp_rl25`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027732.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613

Acceptance Criteria:
- Still not full training: one GPU, 256 envs, 25 iterations, no self-relaunch.
- Resolved env config remains reward-only with observation space 72, external reference path, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_min_target_gripper_width: 0.024`, phase observations false, and reset-pose target policy.
- Epochs complete without traceback/NaN; checkpoint written at epoch 25.
- Follow-up 720-step eval has finite metrics, phase progress reaching 1.0, runtime gripper target min `0.024`, no unsafe tracking targets, and no immediate reset pathology.

Result:
- status: passed; Slurm completed `0:0` after `00:01:27` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613/params/`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613/teacher_8gpu_1027732.out`; checkpoints remain on NFS under the run `nn/` directory.
- resolved_config: `params/env.yaml` has `observation_space: 72`, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_phase_observations: false`, `trajectory_tracking_min_target_gripper_width: 0.024`, `trajectory_tracking_follow_current_cube_pose: false`, and the external 60 mm reference path.
- training_log: actor and critic MLPs both built with `72`; epochs 1-25 completed; no traceback/Hydra/runtime error and no NaN pattern in stdout.
- checkpoint reward suffixes: ep5 `310.19437`, ep10 `819.8631`, ep15 `659.3525`, ep20 `938.2097`, ep25 `1037.0807`.
- checkpoint: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_1037.0807.pth
- caveat: TensorBoard event file is 0 bytes, as in the prior short runs; rollout eval remains the behavior evidence.

Analysis:
- The clamp RL25 run is a clean bounded comparison to the prior retimed RL25 run. The checkpoint reward suffix is higher than the prior unclamped RL25 ep25 suffix (`1037.0807` vs `937.84894`), but that is only a training-side scalar and must not be overinterpreted without rollout metrics.

Next:
- Commit/push this worklog checkpoint.
- Evaluate the epoch-25 clamp checkpoint for 720 steps before any larger training or tuning.

## 2026-06-11T13:49:18-07:00 - gripper clamp RL25 checkpoint eval launch

Goal:
- Evaluate the bounded gripper-clamp RL25 checkpoint across a full reference horizon and compare behavior against the previous unclamped retimed RL25 eval.

Hypothesis:
- If the gripper clamp helps, the eval should keep target safety clean and avoid measured gripper collapse while maintaining or improving approach/lift metrics. If it hurts, expect wider gripper/finger distances and no lift despite finite safe targets.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `6f8bbdda08d6686b8b308d32adf9c225e1d2978b`; implementation code is `0eafbad235c2b821f86eb46f61095fdd3f710031`.
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `6f8bbdda08d6686b8b308d32adf9c225e1d2978b`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_gripclamp25_eval --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_gripclamp_rl25_eval720_20260611_134918,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_1037.0807.pth,NUM_ENVS=4,NUM_STEPS=720,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=53,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027733 `franka_cube_traj_gripclamp25_eval`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027733.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_gripclamp_rl25_eval720_20260611_134918/metrics.json

Acceptance Criteria:
- 720/720 steps complete with finite metrics and no immediate reset pathology.
- Reference summary reports runtime duration `8.0`, source duration `22.033333333333335`, `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`, runtime gripper min `0.024`, reset-pose target policy, and `curobo_validated=false`.
- Phase progress reaches 1.0; `cube_traj_tracking_unsafe_target_rate` remains `0.0`; target min clearance remains above `0.025`.
- Inspect policy behavior: success/lift, finger table clearance, gripper width, finger distances, orientation/position errors, resets/terminations.

Result:
- status: inconclusive/failed acceptance; Slurm completed `0:0` after `00:00:58` on `pool0-00016`, but the mean phase trace did not reach 1.0 because some envs reset before the end of the reference.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_eval720_20260611_134918/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_eval720_20260611_134918/eval_franka_cube_1027733.out`
- rollout: 720/720 steps, `done_count=5`, reward mean `2.3614377533396085`, reward final `2.6098151206970215`, success mean/final/last-window `0.0`.
- finite_check: recursive JSON numeric scan `nonfinite_count=0`.
- tracking_reference: external 60 mm compact reference, `duration_s=8.0`, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`, runtime gripper width min/max `0.024`/`0.07999999821186066`, source gripper width min/max `0.0`/`0.07999999821186066`, `curobo_validated=false`, `validation_passed=true`.
- phase_progress: `traj_phase_progress` max `0.8875000476837158`, final `0.33645835518836975`; mean phase drops around steps 429, 599, and 607 due resets, so the full mean rollout did not reach phase 1.0.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max/mean/final `0.0`; `safe_target_rate` min/mean/final `1.0`; target clearance min over all steps `0.06511414051055908`, above configured `0.025`.
- gripper_tracking: target gripper width min `0.023999998345971107`; measured gripper width mean `0.05157652743574646`, min `0.04474366828799248`, final `0.044823113828897476`. The clamp prevented near-zero measured gripper collapse but the policy keeps a wider opening than the clamped target.
- finger_safety: `finger_table_clearance_min` min `0.04111748933792114`; `finger_table_clearance_violation_max` max `0.0`; no violation steps.
- task_behavior: no success and `has_lifted_cube` remains `0.0`; `cube_lift_height_max` max `0.08642691373825073` at step 7 but still below the `0.12` success lift threshold and not sustained; EE-to-cube mean `0.10301682248504626`; finger-center-to-cube mean `0.09497410427365038`.
- tracking_metrics: tracking reward mean `0.20148737518530752`, final `0.19174256920814514`; position error mean `0.16218089361985524`; orientation error mean `0.25570363098134596`; gripper error mean `0.02780139044366984`.
- comparison_to_unclamped_retime_RL25: unclamped RL25 reached mean phase max `1.0`, reward mean `2.421528760592143`, target gripper min `0.0`, measured gripper min `0.00021008600015193224`, max lift `0.01680278778076172`, and finger-center mean `0.10512903414459693`. Clamp RL25 avoids gripper collapse and improves finger-center mean and orientation error, but has lower tracking reward/reward mean, does not complete the mean phase trace, and still has zero success.

Analysis:
- The clamp is not an immediate win. It fixes one pathology (near-zero measured gripper collapse) and may encourage more physically plausible gripper openings, but the policy still fails to lift/succeed and now resets before the averaged phase trace reaches the final lift target.
- The partial lift spike and resets need visual or per-step diagnosis before scaling. The likely failure is not target safety; it is contact/drag behavior under a wider gripper and the reward balance between approach, lift, and trajectory tracking.

Next:
- Commit/push this result.
- Generate/update a comparison artifact including the clamp runs and launch a cheap video eval of the clamp RL25 checkpoint if feasible, because the reset/partial-lift behavior needs visual inspection before another training change.

## 2026-06-11T13:55:12-07:00 - reconcile stale clamp eval pending handoff

Goal:
- Resolve the orchestrator report that `franka_cube_traj_tracking_gripclamp_eval720_20260611_134240` was still recorded with `job_id: pending` and appeared to have no l401 metrics directory.

Result:
- status: resolved; no resubmission required.
- branch_tip: local and origin `codex/franka-cube-trajectory-tracking` are at `b1242078721c71896c89390448306825ca7f1168`, which is ahead of the orchestrator-observed `92e69c06b8c99a09d6c8ab97177c81f5bf2d0c33`.
- actual_job_id: `1027731` (`franka_cube_traj_gripclamp_eval3`), completed `0:0` in `00:00:58` on `pool0-00016`.
- actual_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/metrics.json`
- actual_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027731.out`
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_eval720_20260611_134240/eval_franka_cube_1027731.out`
- scheduler_check: `sacct -j 1027731` confirms `COMPLETED|0:0`; current `squeue -u lzha` shows no active l401 jobs from this run.

Analysis:
- The stale `job_id: pending` state was from an older branch/worklog view. The resolved launch/result block is present in the pushed branch at and after `d32d980` and explicitly lists job `1027731`.
- The missing-directory check likely looked outside the DEXTRAH eval namespace. Evaluation metrics are under `/results/dextrah/evals/<run_name>/`, not directly under the top-level DEXTRAH results directory.

Next:
- Commit/push this reconciliation note.
- Continue with the already planned clamp comparison artifact update and cheap visual diagnosis of the clamp RL25 reset/partial-lift behavior.

## 2026-06-11T13:58:28-07:00 - clamp comparison artifact bundle

Goal:
- Generate the requested inspectable artifact bundle from fetched metrics/logs, now including the gripper-clamp validation, tiny eval, RL25 train, and RL25 eval runs in addition to the old phase-starved and retimed runs.

Change:
- Extended `dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py` to include clamp run specs/jobs `1027728`, `1027731`, `1027732`, and `1027733`.
- Added gripper-schedule policy fields to the summary JSON/CSV and report: target gripper width min, runtime/source gripper min, and clamp policy.
- Updated the phase/safety and behavior PNGs to overlay clamp RL25 against the old phase-starved and retimed traces.

Validation:
- `python3 -m py_compile dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py`: passed.
- `git diff --check`: passed.
- `python3 dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py --root cluster_results/l401 --output-dir cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512`: passed.
- Visual inspection via `view_image`: phase/safety and behavior PNGs are nonblank and legible; phase/safety shows retiming reaching phase 1.0, clamp RL25 resetting before phase 1.0, and unsafe targets staying at 0.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/comparison_report.md`
- summary_json: `cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/summary.json`
- summary_csv: `cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/summary.csv`
- phase_safety_png: `cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/phase_progress_and_target_safety.png`
- behavior_png: `cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/behavior_reward_lift_finger_metrics.png`
- viz_phase_safety_png: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/phase_progress_and_target_safety.png`
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/comparison_report.md`

Result:
- status: passed; artifact bundle generated from existing fetched metrics/logs before any additional training launch.
- main conclusion: retiming fixed the phase-starvation failure. The gripper clamp prevents raw zero target widths and measured gripper collapse, but clamp RL25 is not a learned-policy success: success remains `0.0`, max lift is `0.0864` m but not sustained, and phase max is only `0.8875` because resets occur before the full reference completes. Target safety remains clean.
- caveat: the 60 mm compact reference still reports `curobo_validated=false`, so this remains an unvalidated geometry-match reference.

Next:
- Commit/push the artifact generator and this worklog entry.
- Launch a cheap video/per-step visual diagnosis of the clamp RL25 checkpoint if feasible before any further reward/tuning change.

## 2026-06-11T13:59:50-07:00 - clamp RL25 video eval launch

Goal:
- Generate a cheap inspectable video/per-step rollout for the latest gripper-clamp RL25 checkpoint to diagnose the partial-lift/reset behavior before any reward or training-scale change.

Hypothesis:
- A 480-step deterministic rollout should cover the approach/grasp segment and the early reset/partial-lift behavior seen in the 720-step metrics, while staying bounded and avoiding any training launch.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `1cf832442f02f23b936d3a745f8d36ae88651fce`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `1cf832442f02f23b936d3a745f8d36ae88651fce`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_gripclamp_vid --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_gripclamp_rl25_20260611_134613/nn/last_dextrah_franka_cube_traj_tracking_ep_25_rew_1037.0807.pth,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=gripclamp-rl25-eval480,CAPTURE_VIDEO=True,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=54,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027738 `franka_cube_traj_gripclamp_vid`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027738.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930
- expected_artifacts: metrics JSON plus `videos/gripclamp-rl25-eval480*.mp4` or equivalent Gymnasium video output.

Acceptance Criteria:
- Job completes without traceback and writes metrics JSON.
- Metrics remain finite; target unsafe rate remains 0; target clearance stays above 0.025 m.
- Video exists, has nonzero duration/frames, and is inspected or opened with `viz-open`.
- Do not treat video rollout as learned-policy success; use it to diagnose behavior before the next bounded ablation.

Result:
- status: passed as a diagnostic artifact; Slurm completed `0:0` after `00:01:18` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/eval_franka_cube_1027738.out`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/videos/gripclamp-rl25-eval480-step-0.mp4`, `cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/video_frames/contact_sheet.png`
- video_metadata: `ffprobe` reports `1280x720`, `479` frames, `7.983333` s, `60/1` fps.
- viz_video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/videos/gripclamp-rl25-eval480-step-0.mp4`
- viz_contact_sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/video_frames/contact_sheet.png`
- rollout: 480/480 steps, `done_count=0`, reward mean `2.5610283367335795`, reward final `2.5189738273620605`, success mean/final `0.0`, nonfinite numeric count `0`.
- phase/safety: phase reaches `1.0` at step 480; `cube_traj_tracking_unsafe_target_rate` max `0.0`; target clearance min `0.06511414051055908`; finger table violation max `0.0`.
- gripper/contact: measured gripper width mean/min `0.04682684224875023`/`0.04380180314183235`; target gripper min `0.023999998345971107`; finger-center-to-cube mean `0.08327599153853953`; EE-to-cube mean `0.09221385022004445`.
- lift/task: `cube_lift_height_max` max only `0.00038486719131469727`; `has_lifted_cube` max `0.0`; success stays `0.0`.
- reference: external 60 mm compact reference still reports `curobo_validated=false`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, and `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`.

Analysis:
- The video confirms the metric diagnosis: the policy approaches near the cube and keeps a plausible non-collapsed gripper width, but it does not close into a useful two-finger grasp and does not lift. The cube remains on the table through the 480-step reference.
- This points away from target safety and toward behavior/reward wiring: the tracker can follow gross pose timing, but the current reward does not produce contact closure or lift under the clamped schedule. A likely next bounded ablation is to increase close/lift phase incentives or change phase-specific weighting so approach/orientation/gripper terms do not dominate without contact.

Next:
- Commit/push this worklog result.
- Before any more RL scale-up, inspect the variant reward terms/config and implement one small behavior-side ablation with cheap local checks plus a short env/RL smoke.

## 2026-06-11T14:03:23-07:00 - phase-gated contact/lift shaping plan

Goal:
- Patch one small variant-only behavior-side ablation based on the clamp video: encourage actual gripper close and upward lift actions during the reference grasp/lift phases without changing the baseline `Dextrah-Franka-Cube-Grasp` task or observation space.

Hypothesis:
- The current additive tracker rewards position/orientation/gripper width, but the clamp RL25 video shows the policy stays near the cube with a plausible width and never establishes contact or lift. Adding small phase-gated action bonuses should make the reward less satisfied by hovering near the cube: close the gripper when the compact reference is in its clamped closed phase, and prefer upward action after the lift phase starts.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: add variant-only shaping config for close-action and lift-action bonuses, with defaults enabled only in this trajectory-tracking variant.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: add logged reward terms inside `_compute_trajectory_tracking_reward()`:
  - `cube_traj_tracking_close_action_reward`: close action gated by phase, safe target, and finger proximity to cube.
  - `cube_traj_tracking_lift_action_reward`: upward action gated by later phase, safe target, and finger proximity to cube.
  - supporting gates for diagnosis.

Validation Plan:
- Local: `python3 -m py_compile` on the touched variant files and validator; `git diff --check`.
- Cluster: run the existing task-registration/env validation with 4 envs and 240 steps against the same 60 mm compact reference. Acceptance: observation remains `[4,72]`, tracking metrics finite, new reward/log terms finite, target unsafe rate remains `0.0`, target clearance remains above `0.025`, and baseline registration still works.
- If validation passes, run only a tiny RL smoke/eval before any larger RL scale.

Result:
- status: implemented locally; cluster validation pending.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog.
- implementation: added phase-gated `cube_traj_tracking_close_action_reward` and `cube_traj_tracking_lift_action_reward` to the variant tracking reward, gated by safe target, reference closed-gripper phase, phase progress, max finger distance to cube, and finger balance.
- logging: validator now requires the new reward/gate terms to appear and remain finite during the trajectory-tracking env smoke.
- local_validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py` passed.
- local_validation: `git diff --check` passed.

Next:
- Commit/push the ablation and deploy the exact commit to the l401 agent-owned worktree.
- Launch only the bounded 4-env/240-step task-registration/env validation first. If it fails, inspect logs and patch before any RL smoke.

## 2026-06-11T14:05:52-07:00 - phase-gated shaping env smoke launch

Goal:
- Validate the phase-gated close/lift shaping ablation in Isaac before any RL smoke or longer training.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `c0d545dfbb9f7417bb7bba2d6a3941509a371b86`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `c0d545dfbb9f7417bb7bba2d6a3941509a371b86`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_phasegate_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_phasegate_env_smoke_20260611_140552,NUM_ENVS=4,NUM_STEPS=240,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=40,SEED=55,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027739 `franka_cube_traj_phasegate_smoke`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027739.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_phasegate_env_smoke_20260611_140552/metrics.json

Acceptance Criteria:
- Task registration and baseline registration still resolve.
- Reset observation shape remains `[4,72]`; this is still a reward-only observation contract.
- Tracking metrics and the new close/lift/gate logs are present and finite.
- Target unsafe rate remains `0.0`; target clearance stays above `0.025`.
- No immediate reset/termination pathology.

Result:
- status: passed; Slurm completed `0:0` after `00:00:47` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_phasegate_env_smoke_20260611_140552/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_env_smoke_20260611_140552/validate_franka_cube_1027739.out`
- validation: `passed=true`, 35 checks, failed checks `[]`, recursive numeric scan `nonfinite_count=0`.
- task/obs: registration resolved to `DextrahFrankaCubeTrajTrackingEnv`; reset and initial observation shapes were `[4,72]`, so this remains reward-only with baseline-sized observations.
- tracking_logs: new `cube_traj_tracking_close_action_reward`, `cube_traj_tracking_lift_action_reward`, `cube_traj_tracking_closed_target_gate`, `cube_traj_tracking_close_phase_gate`, `cube_traj_tracking_lift_phase_gate`, and `cube_traj_tracking_contact_gate` were present and finite.
- rollout: 240/240 steps, `done_count=1`, `early_done_count=0`, reward mean `1.7976593032479287`, reward final `1.548109531402588`, final success `0.0`, max mean lift `0.014957889914512634`.
- target_safety: `tracking_unsafe_target_rate_max=0.0`; target clearance min and batch min `0.06511414051055908`, above configured `0.025`.
- phasegate_behavior: scripted validation produced `tracking_close_action_reward_mean=0.0`, `tracking_lift_action_reward_mean=0.0`, `tracking_contact_gate_mean=0.009603163352585398`, `tracking_close_phase_gate_final=0.08238638937473297`, `tracking_lift_phase_gate_final=0.0`. This proves logging/wiring but not learned behavior; the zero action rewards are expected because the scripted smoke does not hold contact while phase gates are active.
- reference: external 60 mm compact reference, `runtime_duration_s=8.0`, `source_duration_s=22.033333333333335`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`, `curobo_validated=false`, `validation_passed=true`.

Analysis:
- The ablation is runtime-safe and does not alter the observation contract or baseline task registration. Target safety remains clean.
- The validation smoke is insufficient to judge the ablation's learning value, because scripted zero/close/up actions do not create the same near-contact state as the RL policy. The next bounded step is a tiny RL smoke to verify training runs and writes a checkpoint with the new reward terms, followed by a short eval only if the checkpoint is valid.

Next:
- Commit/push this validation result.
- Launch a tiny 3-iteration phase-gated RL smoke, not a longer training run, and inspect config/log/checkpoint before any eval.

## 2026-06-11T14:07:30-07:00 - phase-gated shaping tiny RL smoke launch

Goal:
- Verify RL-Games training still runs and writes a checkpoint with the phase-gated contact/lift shaping ablation before any longer training.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `5aba7a9ce03e8fd73c2c51fa5fc139f488389a69`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `5aba7a9ce03e8fd73c2c51fa5fc139f488389a69`, detached clean. SSH Git auth failed; HTTPS fetch fallback succeeded.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_phasegate_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027740 `franka_cube_traj_phasegate_rl`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027740.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730

Acceptance Criteria:
- One GPU, 16 envs, 3 iterations only; no auto-resume or self-relaunch.
- Resolved config has observation space `72`, phase observations false, reference duration `8.0`, gripper clamp `0.024`, and the new phase-gated shaping config values.
- Actor/critic input dimensions remain `72`; no traceback/NaN; epoch-3 checkpoint written.
- Inspect stdout/config for the new reward/gate instrumentation. Only if this is clean, run a bounded eval/video to see whether behavior changes.

Result:
- status: passed as an RL wiring smoke; Slurm completed `0:0` after `00:00:50` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/teacher_8gpu_1027740.out`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/params/env.yaml`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/params/agent.yaml`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_4.5636964.pth`
- stdout: no traceback/NaN match in the inspected log; RL-Games reached `MAX EPOCHS NUM!` and `Training Done`.
- checkpoint: epoch 1/2/3 checkpoints were written, plus a runtime sidecar; final checkpoint size was about `7.76 MB`.
- config: `params/env.yaml` resolved `observation_space: 72`, `trajectory_tracking_phase_observations: false`, `trajectory_tracking_reference_duration_s: 8.0`, `trajectory_tracking_min_target_gripper_width: 0.024`, `trajectory_tracking_follow_current_cube_pose: false`, and the new phase-gated shaping defaults (`close_action_weight=0.35`, `lift_action_weight=0.5`, `contact_gate_max_finger_dist=0.14`, `contact_gate_width=0.08`).
- network: stdout logged `build mlp: 72` for both actor/central value paths.
- trainer: `NUM_ENVS=16`, `horizon_length=16`, `mini_epochs=1`, `max_epochs=3`, `multi_gpu=false`, no auto-resume or self-relaunch.
- caveat: the TensorBoard event sidecar is still `0` bytes for this short smoke, so behavior/reward-term evidence must come from a bounded rollout eval rather than curves.

Analysis:
- This verifies that the phase-gated ablation is trainable in the Isaac/RL-Games runtime and preserves the reward-only observation contract. It does not show learned policy success.
- Because the env smoke had zero close/lift action rewards under scripted actions, the next bounded check must be an eval/video of this epoch-3 checkpoint with the new reward logs in `metrics.json`. If close/lift rewards remain zero for the learned rollout too, the gates are too strict for early learning and should be loosened before any longer training.

Next:
- Commit/push this result.
- Launch one short phase-gated epoch-3 eval/video rollout (not training scale-up) to inspect behavior and reward-term activation before any additional training.

## 2026-06-11T14:12:22-07:00 - phase-gated epoch-3 eval/video launch

Goal:
- Inspect whether the phase-gated close/lift shaping terms activate under the tiny epoch-3 policy and whether visible behavior changes before any longer training.

Hypothesis:
- If the learned rollout reaches near-contact states, `cube_traj_tracking_contact_gate`, `cube_traj_tracking_close_action_reward`, and possibly `cube_traj_tracking_lift_action_reward` should become nonzero. If they remain zero, the gates are too strict for early learning.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `51b0e4be7a41cfce139af38af9b76c5cd7786bb8`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `51b0e4be7a41cfce139af38af9b76c5cd7786bb8`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_phasegate_vid --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_4.5636964.pth,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=phasegate-ep3-eval480,CAPTURE_VIDEO=True,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=56,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027742 `franka_cube_traj_phasegate_vid`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027742.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222

Acceptance Criteria:
- 480-step eval completes without traceback and writes metrics plus MP4.
- Numeric metrics are finite; target unsafe rate remains `0.0`; target clearance remains above `0.025`.
- New close/lift/contact gate reward terms are present and inspected.
- Video metadata is valid and frames are inspected before deciding the next ablation.

Result:
- status: failed the instrumentation acceptance criterion; Slurm completed `0:0` after `00:01:18` on `pool0-00016`, and the rollout/video are valid, but the eval metrics omit the new phase-gated terms.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222/eval_franka_cube_1027742.out`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222/videos/phasegate-ep3-eval480-step-0.mp4`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222/video_frames/contact_sheet.png`
- viz_contact_sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_video480_20260611_141222/video_frames/contact_sheet.png`
- video_metadata: `ffprobe` reports `1280x720`, `479` frames, `7.983333` s, `60/1` fps.
- rollout: 480/480 steps, `done_count=1`, `reward_mean=1.510228872547547`, `reward_final=1.312933087348938`, success mean/final `0.0`, nonfinite numeric count `0`.
- task_behavior: `cube_lift_height` max `0.025222614407539368` at step 2 but no sustained lift and `has_lifted_cube` max `0.0`; EE-to-cube distance worsened from min `0.17762282490730286` to final `0.34083348512649536`; finger-center-to-cube distance worsened from min `0.17076227068901062` to final `0.34247004985809326`; max finger-to-cube distance final `0.36102867126464844`.
- gripper: measured gripper width mean `0.039188646928717694`, final `0.038653671741485596`, min `0.036159977316856384`.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max `0.0`, `cube_traj_tracking_safe_target_rate` mean `1.0`, target clearance min `0.06511414051055908`, finger-table violation max `0.0`.
- phase/reference: phase reached `0.9984375238418579`; reference still reports `curobo_validated=false`, `runtime_retime_policy=normalize_to_configured_runtime_duration`, `runtime_object_pose_policy=reset_cube_pose`, and `gripper_schedule_policy=clamp_source_width_to_min_target_gripper_width`.
- missing_terms: `rg` and JSON inspection found no `close_action`, `lift_action`, `contact_gate`, `closed_target_gate`, `close_phase_gate`, or `lift_phase_gate` entries in `metrics.json` or stdout.
- visual_diagnosis: the contact sheet shows the gripper hovering beside/above the cube and moving away over the rollout rather than closing around or lifting the cube. The first contact-sheet tile is blank from video startup; subsequent frames are valid.

Analysis:
- This eval answers behavior but not phase-gate activation. Behavior is poor: the tiny phase-gated policy does not grasp, lift, or maintain contact; the hand drifts farther from the cube while target safety remains clean.
- The missing phase-gate metrics are an eval instrumentation bug, not evidence that the terms are zero. Env validation `1027739` already showed the new logs exist in `extras["log"]`; `eval_rollout.py` simply omitted them from its fixed export whitelist.

Next:
- Patch eval metric export before any longer training. Rerun a short bounded eval from the same checkpoint to inspect `cube_traj_tracking_close_action_reward`, `cube_traj_tracking_lift_action_reward`, and all gate terms.

## 2026-06-11T14:14:44-07:00 - eval tracking-log instrumentation patch plan

Goal:
- Fix the eval metrics export so the phase-gated close/lift action reward and gate terms can be inspected explicitly before any longer training.

Finding:
- Job `1027742` completed and produced a valid video/metrics file, but `metrics.json` and stdout do not contain `cube_traj_tracking_close_action_reward`, `cube_traj_tracking_lift_action_reward`, `cube_traj_tracking_contact_gate`, `cube_traj_tracking_closed_target_gate`, `cube_traj_tracking_close_phase_gate`, or `cube_traj_tracking_lift_phase_gate`.
- Root cause: `dextrah_lab/rl_games/eval_rollout.py` copies only a fixed whitelist from `task_env.extras["log"]`; the new terms were present in env validation but omitted from eval export.

Planned Change:
- Patch `dextrah_lab/rl_games/eval_rollout.py` to export all scalar/tensor `cube_traj_tracking_*` log terms from `extras["log"]` instead of the stale whitelist.
- Keep the change eval-helper-only; do not touch the baseline task implementation.

Validation Plan:
- Local: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py` and `git diff --check`.
- Commit/push and deploy the exact commit to the l401 agent worktree.
- Relaunch a bounded 480-step eval from the same epoch-3 checkpoint, metrics-focused and without another video unless needed, to inspect the newly exported terms.

Result:
- status: implemented locally; cluster relaunch pending.
- changed_files: `dextrah_lab/rl_games/eval_rollout.py`, this worklog.
- implementation: `_collect_task_metrics()` now exports every scalar/tensor `extras["log"]` key whose name starts with `cube_traj_tracking_`, instead of relying on a stale fixed whitelist.
- local_validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py` passed.
- local_validation: `git diff --check` passed.

## 2026-06-11T14:17:25-07:00 - phase-gated epoch-3 metrics rerun launch

Goal:
- Rerun the same short epoch-3 rollout after the eval instrumentation patch so the close/lift action rewards and gate terms can be inspected directly.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `6125e1d8537da61b16c8a5d11c3dd9bbc56d890a`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `6125e1d8537da61b16c8a5d11c3dd9bbc56d890a`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_phasegate_metrics --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_phasegate_ep3_metrics480_20260611_141725,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_4.5636964.pth,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=1,VIDEO_NAME_PREFIX=phasegate-ep3-metrics480,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=56,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027743 `franka_cube_traj_phasegate_metrics`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027743.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_phasegate_ep3_metrics480_20260611_141725

Acceptance Criteria:
- 480-step eval completes without traceback and writes `metrics.json`.
- Numeric metrics are finite; target unsafe rate remains `0.0`; target clearance remains above `0.025`.
- `cube_traj_tracking_close_action_reward`, `cube_traj_tracking_lift_action_reward`, `cube_traj_tracking_contact_gate`, `cube_traj_tracking_closed_target_gate`, `cube_traj_tracking_close_phase_gate`, and `cube_traj_tracking_lift_phase_gate` are present in `metrics.json`.
- If close/lift rewards and contact gate remain effectively zero, treat the gates as too strict or unreachable for this policy and patch before any longer training.

Result:
- status: passed instrumentation, failed behavior/shaping activation; Slurm completed `0:0` after `00:00:54` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_metrics480_20260611_141725/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_metrics480_20260611_141725/eval_franka_cube_1027743.out`
- rollout: 480/480 steps, `done_count=1`, reward mean/final `1.510228872547547`/`1.312933087348938`, success mean/final `0.0`, nonfinite numeric count `0`.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max `0.0`, `cube_traj_tracking_safe_target_rate` mean `1.0`, target clearance min `0.06511414051055908`.
- phase/gates: required new terms are present in `metrics.json`; `closed_target_gate` mean/final `0.5622601961323413`/`0.9999998807907104`, `close_phase_gate` mean/final `0.27448512139698406`/`0.9971591234207153`, `lift_phase_gate` mean/final `0.22448643996419074`/`0.9965277910232544`.
- contact/action_rewards: `cube_traj_tracking_contact_gate` max/mean only `0.006634526886045933`/`0.0016727626404886564`; `cube_traj_tracking_close_action_reward` max/mean/final all `0.0`; `cube_traj_tracking_lift_action_reward` max/mean/final all `0.0`.
- task_behavior: same poor behavior as the video run; success `0.0`, no sustained lift, final EE-to-cube `0.34083348512649536`, final finger-center-to-cube `0.34247004985809326`, final max finger-to-cube `0.36102867126464844`, gripper width mean/final `0.039188646928717694`/`0.038653671741485596`.
- reference: still `curobo_validated=false`; 60 mm source remains exact-geometry-unvalidated.

Analysis:
- The eval instrumentation is now fixed. The reward ablation itself is not useful yet: phase and closed-target gates activate, but the contact gate is effectively unreachable for this policy by the time the reference reaches the grasp/lift phases.
- Because close/lift action rewards are multiplied by the near-zero contact gate, the new shaping terms provide no learning signal in this bounded rollout. This matches the visual diagnosis that the gripper hovers and drifts away rather than establishing contact.

Next:
- Patch the trajectory variant only: loosen the proximity/contact gate to activate within the observed 20-30 cm approach envelope and add explicit tracking action-signal diagnostics (`action_close`, `action_up`, etc.) so the next smoke can tell whether the policy lacks proximity, close/up commands, or both.
- Run local syntax checks, then a bounded env validation before any RL smoke or training.

## 2026-06-11T14:21:20-07:00 - relaxed proximity-gate patch plan

Goal:
- Make the phase-gated close/lift shaping reachable enough to provide a nonzero early learning signal, while logging enough diagnostics to avoid guessing about action sign.

Hypothesis:
- The current contact gate (`max_finger_to_cube_dist < 0.14 m`, width `0.08`) is too strict for the current tracking policy, whose max-finger distance is about `0.26 m` at the close phase and worsens later. A broader proximity gate should activate around the close phase without changing observations or baseline task code.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: relax `trajectory_tracking_contact_gate_max_finger_dist` and `trajectory_tracking_contact_gate_width` for this variant only, and document it as a broad proximity/contact gate.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: log `cube_traj_tracking_action_close`, `cube_traj_tracking_action_up`, `cube_traj_tracking_action_z`, `cube_traj_tracking_gripper_action`, `cube_traj_tracking_contact_distance_gate`, and `cube_traj_tracking_finger_balance_gate`.

Validation Plan:
- Local: `python3 -m py_compile` on the variant env/cfg and eval helper; `git diff --check`.
- Cluster: bounded 4-env/240-step env validation first. Acceptance: obs remains `[4,72]`, metrics finite, target unsafe `0`, relaxed gate/action diagnostics present, and no immediate reset pathology.

Result:
- status: implemented locally; cluster validation pending.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog.
- implementation: relaxed the trajectory variant proximity/contact gate from `0.14 m`/`0.08 m` to `0.30 m`/`0.18 m`; added tracking logs for contact-distance gate, finger-balance gate, close/up action signals, raw z action, and raw gripper action; validator now requires these logs.
- local_validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py` passed.
- local_validation: `git diff --check` passed.

Next:
- Commit/push and deploy exact commit to l401.
- Launch a 4-env/240-step env validation before any RL smoke.

## 2026-06-11T14:22:30-07:00 - phase-gate diagnostic artifact bundle

Goal:
- Provide inspectable evidence for why the current phase-gated shaping is not ready for scale-up.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/report.md`
- metrics_plot: `cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/phasegate_diagnostic_metrics.png`
- summary_csv: `cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/summary.csv`
- summary_json: `cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/summary.json`
- viz_plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/phasegate_diagnostic_metrics.png`
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_diagnostic_20260611_142230/report.md`

Result:
- status: generated locally from fetched `1027742`/`1027743` metrics and video artifacts.
- note: first attempt to use `matplotlib` failed because the local Python environment lacks that dependency; regenerated the PNG with Pillow, which is available.

## 2026-06-11T14:23:12-07:00 - relaxed proximity-gate env smoke launch

Goal:
- Validate the relaxed proximity/contact gate and new diagnostics in the Isaac task runtime before any RL or eval relaunch.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `b7edd3f355db556626577f22be1155518083ff03`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `b7edd3f355db556626577f22be1155518083ff03`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_relaxgate_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_relaxgate_env_smoke_20260611_142312,NUM_ENVS=4,NUM_STEPS=240,VIDEO_LENGTH=240,CAPTURE_VIDEO=False,PRINT_INTERVAL=40,SEED=57,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027745 `franka_cube_traj_relaxgate_smoke`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027745.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_relaxgate_env_smoke_20260611_142312/metrics.json

Acceptance Criteria:
- Task registration and baseline registration still resolve.
- Reset observation shape remains `[4,72]`.
- Metrics are finite; target unsafe rate remains `0.0`; target clearance remains above `0.025`.
- Relaxed-gate/action diagnostics are present and finite: contact-distance gate, finger-balance gate, action-close/up, raw z/gripper action.
- No immediate reset/termination pathology.

Result:
- status: passed; Slurm completed `0:0` after `00:00:45` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_relaxgate_env_smoke_20260611_142312/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_env_smoke_20260611_142312/validate_franka_cube_1027745.out`
- validation: `passed=true`, 35 checks, failed checks `[]`, recursive numeric scan nonfinite count `0`.
- task/obs: reset observation shape `[4,72]`; baseline and trajectory task registration still resolved.
- rollout: 240/240 steps, `done_count=0`, `early_done_count=0`, reward mean/final `1.6414374127984046`/`1.4329001903533936`, final success `0.0`, max mean lift `0.004192143678665161`.
- relaxed_gate_signal: `tracking_contact_distance_gate_mean=0.6774192040165266`, `tracking_finger_balance_gate_mean=0.9482417523860931`, `tracking_contact_gate_mean=0.6521847594529391`, `tracking_action_close_mean=0.33125`, `tracking_action_up_mean=0.16458333333333333`.
- shaping_terms: `tracking_close_action_reward_mean=0.000215970992482221`; `tracking_lift_action_reward_mean=0.0` because the 240-step smoke only reaches close phase (`tracking_close_phase_gate_final=0.09090910851955414`, `tracking_lift_phase_gate_final=0.0`).
- target_safety: `tracking_unsafe_target_rate_max=0.0`, target clearance min and batch min `0.06511414051055908`.
- reference: still `curobo_validated=false`, exact 60 mm geometry validation remains pending.

Analysis:
- The relaxed gate is runtime-safe and no longer silent in the controlled env smoke. It creates a measurable close-action shaping signal while preserving the reward-only observation contract and target safety.
- This does not prove policy improvement. The next bounded diagnostic is a metrics-only eval of the existing epoch-3 checkpoint under the relaxed-gate code, to see whether the previously drifting policy now receives nonzero close/lift shaping and whether the action diagnostics reveal wrong gripper/up commands.

Next:
- Commit/push this worklog evidence.
- Run a short metrics-only eval from the same epoch-3 checkpoint under the relaxed-gate commit. Do not launch longer training.

## 2026-06-11T14:25:40-07:00 - relaxed-gate tiny RL smoke launch

Goal:
- Verify that RL-Games training still runs with the relaxed proximity/contact gate and writes a checkpoint before any longer training.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `edc10277c13cfde7a4e1a005d44796157420d0a8`
- remote_commit/status: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking at `edc10277c13cfde7a4e1a005d44796157420d0a8`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_relaxgate_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027747 `franka_cube_traj_relaxgate_rl`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027747.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540

Acceptance Criteria:
- One GPU, 16 envs, 3 iterations only; no auto-resume or self-relaunch.
- Resolved config has observation space `72`, phase observations false, reference duration `8.0`, gripper clamp `0.024`, and relaxed proximity gate config `0.30`/`0.18`.
- Actor/critic input dimensions remain `72`; no traceback/NaN; epoch-3 checkpoint written.
- After this smoke, run a bounded eval to inspect close/lift/contact/action metrics. Do not scale training.

Result:
- status: passed smoke-training criteria; Slurm completed `0:0` after `00:00:49` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540/`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540/teacher_8gpu_1027747.out`.
- runtime: one L40S GPU, `NUM_ENVS=16`, `HORIZON_LENGTH=16`, `MINI_EPOCHS=1`, `MAX_ITERATIONS=3`, `AUTO_RESUME=False`, `SELF_RELAUNCH=False`.
- config: resolved `observation_space=72`, `state_space=72`, `trajectory_tracking_phase_observations=false`, `trajectory_tracking_reference_duration_s=8.0`, `trajectory_tracking_contact_gate_max_finger_dist=0.3`, `trajectory_tracking_contact_gate_width=0.18`, `trajectory_tracking_min_target_gripper_width=0.024`.
- model_shapes: train log shows actor and central-value MLPs both built with input dimension `72`.
- checkpoints: epoch checkpoints were written through `nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.782907.pth`; no traceback or NaN signature found in the fetched log.
- reference: still `curobo_validated=false`, exact DEXTRAH 60 mm geometry validation remains pending.

Analysis:
- This only proves the relaxed-gate variant can train for a tiny RL-Games smoke without registration/config regressions. It does not prove learned grasping, lift, or success.
- Next required check is a bounded epoch-3 rollout/eval that exports the relaxed gate, action, target-safety, distance, gripper, and lift metrics. I will include a short video because it is cheap at this scale and makes the behavior inspectable.

## 2026-06-11T14:29:10-07:00 - relaxed-gate epoch-3 metrics-only eval launch plan

Goal:
- Evaluate the 3-iteration relaxed-gate smoke checkpoint with a bounded metrics-only rollout to verify whether the relaxed gate produces nonzero learning signal and whether behavior remains sane.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `edc10277c13cfde7a4e1a005d44796157420d0a8`
- remote_commit/status: expected `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `edc10277c13cfde7a4e1a005d44796157420d0a8`, clean/detached.

Planned Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_relaxgate_metrics --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_relaxgate_ep3_metrics480_20260611_142910,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_5.782907.pth,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=1,VIDEO_NAME_PREFIX=relaxgate-ep3-metrics480,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=58,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027748 `franka_cube_traj_relaxgate_metrics`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job_id>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_relaxgate_ep3_metrics480_20260611_142910

Acceptance Criteria:
- Eval completes without traceback and writes `metrics.json`.
- Numeric metrics are finite; target unsafe rate remains `0.0`; target clearance remains above `0.025`.
- Required relaxed-gate terms are present and non-missing: `cube_traj_tracking_contact_gate`, `cube_traj_tracking_contact_distance_gate`, `cube_traj_tracking_finger_balance_gate`, `cube_traj_tracking_action_close`, `cube_traj_tracking_action_up`, `cube_traj_tracking_close_action_reward`, and `cube_traj_tracking_lift_action_reward`.
- Evidence should show whether the relaxed gate creates nonzero reward signal in eval. If behavior still drifts away or close/lift shaping remains negligible, patch/debug rather than scale training.
- After fetch/inspection, generate a small local report/plot artifact and open the useful plot or report with `viz-open`.

Result:
- status: completed `0:0`; 480/480 steps fetched and parsed; no traceback/NaN signature in fetched eval log.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics480_20260611_142910/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics480_20260611_142910/eval_franka_cube_1027748.out`.
- report_bundle: `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/report.md`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/relaxgate_ep3_metrics_plot.png`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/summary.csv`.
- viz_plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/relaxgate_ep3_metrics_plot.png`
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics_diagnostic_20260611_143020/report.md`
- rollout: `done_count=0`, reward mean/final `1.6773871454099814`/`1.3972491025924683`, success mean/final `0.0005208333333333333`/`0.0`, last-window success `0.0`.
- target_safety: `cube_traj_tracking_unsafe_target_rate` max `0.0`, target clearance min `0.06511414051055908`.
- relaxed_gate_signal: `contact_gate` mean/final `0.5602442137276132`/`0.387542188167572`, `contact_distance_gate` mean/final `0.5986778396492203`/`0.39807820320129395`, `finger_balance_gate` mean/final `0.9052443617333968`/`0.942093014717102`.
- action_signal: `action_close` mean/final `0.02885243067673097`/`0.03220806270837784`, `action_up` mean/final `0.010836406107409857`/`0.01688719354569912`, raw `gripper_action` mean/final `0.02067194979948302`/`0.03351552039384842`, raw z action mean/final about `-0.0079`/`-0.0019`.
- shaping_signal: `close_action_reward` mean/final/max `0.0005198891313200132`/`0.0012755959760397673`/`0.0013440798502415419`; `lift_action_reward` mean/final/max `0.0006137145110794033`/`0.00183013454079628`/`0.002015831647440791`.
- behavior: final EE-to-cube `0.23227976262569427`, final finger-center-to-cube `0.22668778896331787`, final max-finger-to-cube `0.23908522725105286`, final gripper width `0.04132682830095291`, final cube lift `0.0`.
- reference: still `curobo_validated=false`; source tag remains `graspgenx_curobo_60mm_export_pending_exact_validation`.

Analysis:
- The relaxed gate fixes the earlier silent-shaping issue and satisfies the metrics-only eval acceptance criteria. However, the learned behavior remains poor: the hand moves away from the cube during close/lift phases and the gripper remains too open relative to the 0.024 m target.
- The action bonuses are active but too small to influence policy behavior in this smoke. Lift-phase averages: close/lift action rewards are about `0.0012`/`0.0016`, while position/gripper tracking terms are about `0.0607`/`0.0799` and total reward remains around `1.4-1.7`.
- The next bounded debug ablation should stay in the trajectory variant: increase the close/lift action shaping scale and log the gate-normalized potential reward ceilings so it is clear whether the policy is choosing small actions or whether gating/weighting still suppresses the signal. Do not launch longer training before this diagnostic passes a cheap env/eval check.

## 2026-06-11T14:36:05-07:00 - action-scale/reference-pull diagnostic ablation plan

Goal:
- Test the current failure mode without scaling training: distinguish weak close/up action incentives from late-phase reference attraction pulling the EE away from the cube.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: trajectory variant only; increase close/lift action reward weights to diagnostic scale and add configurable late-phase reference reweighting knobs.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: apply the late-phase reference reweight only to position/orientation/gripper tracking terms, not to close/lift action terms; log `cube_traj_tracking_reference_reweight`, action reward ceilings, and action utilization ratios.
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`: require the new diagnostic logs in trajectory validation.

Hypothesis:
- If gate-normalized reward ceilings are now significant but action utilization remains near zero after a tiny smoke/eval, the issue is policy/action learning rather than gate silence.
- If late-phase position/orientation/gripper reweighting reduces the reward incentive to chase a moving lift target while target safety stays clean, the next learning smoke can test whether close/up commands improve without reference pull dominating.

Validation Plan:
- Local: `python3 -m py_compile` for touched files and `git diff --check`.
- Cluster: 4-env/240-step env smoke for registration/logs/finite metrics/target safety only.
- If env smoke passes, run only a bounded metrics-only eval or tiny smoke/eval as requested; no longer training.
- Reference caveat remains explicit: the compact reference is `curobo_validated=false` and should not be called DEXTRAH-ready exact-geometry validated.

Result:
- status: implemented locally; cluster validation pending.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog.
- implementation: increased trajectory-only close/lift action reward weights from `0.35`/`0.50` to `2.5`/`4.0`; added late-phase reference reweighting after phase `0.55` with scale `0.35` for position/orientation/gripper tracking terms only; action bonuses still use the unscaled safe phase weight.
- diagnostics: added logs for `cube_traj_tracking_reference_reweight`, `cube_traj_tracking_tracking_term_weight`, `cube_traj_tracking_close_action_reward_ceiling`, `cube_traj_tracking_lift_action_reward_ceiling`, `cube_traj_tracking_close_action_utilization`, and `cube_traj_tracking_lift_action_utilization`; validator now requires/summarizes them.
- local_validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py` passed.
- local_validation: `git diff --check` passed.

Next:
- Commit/push and deploy the exact commit to l401.
- Launch a bounded 4-env/240-step env smoke; acceptance is registration/log presence/finite metrics/target safety/no immediate reset pathology. No longer training.

## 2026-06-11T14:37:20-07:00 - action-scale diagnostic env smoke launch

Goal:
- Validate the action-scale/reference-reweight diagnostic wiring in Isaac before any training or eval. Use 480 steps so close/lift phases and late reference reweight actually activate.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `c1452dfa990714cde3565bbb3880cc24683d5d7f`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `c1452dfa990714cde3565bbb3880cc24683d5d7f`, detached after HTTPS fetch.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_actionscale_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_actionscale_env_smoke_20260611_143720,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=1,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,SEED=59,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027750 `franka_cube_traj_actionscale_smoke`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_<job_id>.out
- expected_metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_actionscale_env_smoke_20260611_143720/metrics.json

Acceptance Criteria:
- Task registration still works and reset observation shape remains `[4,72]`.
- All tracking logs, including new ceiling/utilization/reference-reweight terms, are present and finite.
- Target unsafe rate remains `0.0`, target clearance min remains above `0.025`, and there is no immediate reset/termination pathology.
- This is wiring/runtime validation only; no learning or policy success claim.

Result:
- status: passed; Slurm completed `0:0` after `00:00:50` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_actionscale_env_smoke_20260611_143720/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_env_smoke_20260611_143720/validate_franka_cube_1027750.out`.
- validation: `passed=true`, 35 checks, failed checks `[]`.
- rollout: 480/480 steps, `done_count=0`, `early_done_count=0`, reward mean/final `1.9010794838269551`/`1.17800772190094`, final success `0.0`, max mean lift `0.00035771727561950684`, final gripper width `0.020000029355287552`.
- target_safety: `tracking_unsafe_target_rate_max=0.0`, target clearance min and batch min `0.06511414051055908`.
- diagnostic_logs: missing logs `[]`; `tracking_reference_reweight_mean=0.8530728967239459`, `tracking_term_weight_mean=0.5911970233544708`.
- action_scale_signal: `tracking_close_action_reward_ceiling_mean=0.19872593636010868`, `tracking_lift_action_reward_ceiling_mean=0.2142587032498947`; realized close/lift rewards mean `0.09936296818005434`/`0.08621291266851282` under scripted close/up actions; utilization means `0.23072916666666668`/`0.1203125`.
- reference: still `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`, transform policy `transform_task_space_waypoints_by_cube_pose`, runtime object pose policy `reset_cube_pose`.

Analysis:
- The diagnostic-scale weights and late reference reweighting are runtime-safe in the environment smoke and produce action reward ceilings large enough to matter when actions are present.
- The smoke is scripted and does not answer learned behavior. The next bounded step is a metrics-only eval of the existing epoch-3 checkpoint under this diagnostic reward config. That will not change actions, but it will show whether the failed policy has large available close/up reward ceilings and low utilization, which isolates weak policy actions from gate silence.

## 2026-06-11T14:37:11-07:00 - action-scale diagnostic tiny RL smoke launch plan

Goal:
- Run a tiny RL-Games smoke under the action-scale/reference-reweight diagnostic reward config, then evaluate the resulting epoch-3 checkpoint only if the smoke passes.

Version Control:
- agent_id: franka-cube-traj-tracking
- source_commit: `c1452dfa990714cde3565bbb3880cc24683d5d7f`
- remote_commit/status: will redeploy `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` to the exact pushed branch commit before launch.

Planned Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_actionscale_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_actionscale_rl_smoke_20260611_143711,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=16,MINIBATCH_SIZE=256,CENTRAL_VALUE_MINIBATCH_SIZE=256,MINI_EPOCHS=1,MAX_ITERATIONS=3,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027751 `franka_cube_traj_actionscale_rl`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<job_id>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionscale_rl_smoke_20260611_143711

Acceptance Criteria:
- One GPU, 16 envs, 3 iterations only; no auto-resume or self-relaunch.
- Resolved config keeps observation/state dimensions at `72`, phase observations false, action-scale close/lift weights `2.5`/`4.0`, and reference reweight `0.35` after phase `0.55`.
- Actor/critic MLP input dimensions remain `72`; no traceback/NaN; epoch-3 checkpoint written.
- If the smoke passes, launch one bounded metrics-only epoch-3 eval with all `cube_traj_tracking_*` terms exported. Do not launch longer training.
- Reference caveat remains explicit: `curobo_validated=false`, exact DEXTRAH 60 mm geometry validation remains pending.

Result:
- status: completed scheduler/runtime, but **not a clean RL smoke pass**; treat as metric-pathology smoke.
- slurm: job `1027751` completed `0:0` after `00:00:48` on `pool0-00016`.
- local_artifacts: `cluster_results/l401/franka_cube_traj_tracking_actionscale_rl_smoke_20260611_143711/`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rl_smoke_20260611_143711/teacher_8gpu_1027751.out`.
- config: resolved `observation_space=72`, `state_space=72`, `trajectory_tracking_phase_observations=false`, close/lift weights `2.5`/`4.0`, reference reweight phase/scale `0.55`/`0.35`, reference duration `8.0`, min gripper width `0.024`.
- model_shapes: actor and central-value MLPs both built with input dimension `72`.
- pathology: log warning `Max epochs reached before any env terminated at least once`; only checkpoint is `nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth`.
- no full-training claim: this does not establish reward improvement or learned behavior and must not be used for scale-up.
- reference: still `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.

Analysis:
- The `-inf` reward suffix is likely expected for a 3-iteration RL-Games smoke in this env because no episode terminates during the short rollout. With `num_envs=16`, `horizon_length=16`, and `max_iterations=3`, the trainer only advances tens of policy steps per actor, while the DEXTRAH episode horizon is about 10 s / 0.0167 s = ~600 policy steps. RL-Games episode-return bookkeeping stays at its initialized value until at least one episode finishes.
- The wrapper therefore needs a short-run interpretability route: either run enough iterations to force at least one termination, or keep tiny RL smoke as a wiring-only training check and immediately use a diagnostic eval/video/trace from the produced checkpoint. For B, prefer the latter before any further RL.

Next:
- Patch eval artifact export to write trace CSV/JSONL with target/EE/cube pose, distance, gripper/action, gate/reward, lift/success, and target-safety fields.
- Add a local summarizer for report/plot/train-vs-eval consistency artifacts.
- Run a diagnostic-only video eval from the `rew_-inf` checkpoint, explicitly labeled as diagnostic-only. Use it only to inspect behavior/reward-term wiring.

## 2026-06-11T14:45:10-07:00 - diagnostic artifact export patch

Goal:
- Make every bounded B eval produce inspectable artifacts: video, per-step trace files, trace plot, report, and train-vs-eval consistency check.

Change:
- `dextrah_lab/rl_games/eval_rollout.py`: added default `trace.csv` and `trace.jsonl` outputs; trace now includes target EE pose/quaternion, EE pose/quaternion, cube pose, EE-to-target distance, policy action z/gripper/close/up, existing task metrics, and all `cube_traj_tracking_*` terms.
- `dextrah_lab/rl_games/eval_rollout.py`: added `env_config` summary to `metrics.json` for observation/action size, reset/randomization, reference path/duration/transform-related flags, phase observation flag, action-scale weights, reference reweight knobs, and safety gates.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: added local artifact summarizer that writes `trajectory_trace_plot.png`, `summary.json`, `train_eval_consistency.json`, and `report.md` from fetched eval outputs.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- `git diff --check` passed.

Next:
- Commit/push/deploy this exact code.
- Launch one diagnostic-only video eval from the `1027751` `rew_-inf` checkpoint. Do not treat it as a clean learned-policy checkpoint; use it only to inspect behavior and reward-term wiring.

## 2026-06-11T14:43:18-07:00 - action-scale `rew_-inf` diagnostic video eval launch

Goal:
- Produce inspectable artifacts for the pathological `1027751` checkpoint: short rollout video, per-step trace CSV/JSONL, metrics JSON, and later local plot/report/consistency bundle.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `3eece1ab59be14ee9457e4f7a0da8b7b29f7b167`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `3eece1ab59be14ee9457e4f7a0da8b7b29f7b167`, detached after HTTPS fetch.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_rewinf_diag --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionscale_rl_smoke_20260611_143711/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=actionscale-rewinf-diag-video480,CAPTURE_VIDEO=True,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=61,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027753 `franka_cube_traj_rewinf_diag`
- expected_log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job_id>.out
- expected_run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318

Acceptance Criteria:
- Diagnostic-only eval completes without traceback and writes `metrics.json`, `trace.csv`, `trace.jsonl`, and a valid video.
- Trace includes phase/progress, target pose, EE-to-target, EE/cube/finger distances, gripper width/action, contact gate, close/lift action rewards, lift/success, and target-safety/clearance terms.
- Local post-processing must produce a plot/report/summary and train-vs-eval consistency JSON, then `viz-open` the main plot/video/report.
- Do not treat this as a clean learned-policy result because the source checkpoint is `rew_-inf`.

Result:
- status: completed diagnostic eval; Slurm job `1027753` completed `0:0` after `00:01:18` on `pool0-00016`; rollout completed 480/480 steps with `done_count=0`.
- remote_artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/metrics.json`, `trace.csv`, `trace.jsonl`, and `videos/actionscale-rewinf-diag-video480-step-0.mp4`.
- local_run_artifacts: `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/trace.jsonl`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/eval_franka_cube_1027753.out`.
- local_summary_bundle: `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/report.md`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/trajectory_trace_plot.png`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/train_eval_consistency.json`, `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/actionscale_rewinf_contact_sheet.png`, and first/mid/last frames under `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/frames/`.
- viz_video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
- viz_plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/trajectory_trace_plot.png`
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/report.md`
- viz_contact_sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/actionscale_rewinf_contact_sheet.png`
- video_validation: `ffprobe` reports width `1280`, height `720`, frame rate `60/1`, duration `7.983333`, frame count `479`.
- frame_inspection: first extracted frame is black; mid frame is valid and shows the gripper close to the cube without stable grasp/lift; final frame is valid and shows the hand backed off/open above the table while the cube remains unmoved.
- rollout_metrics: reward mean/final `1.7957129741708437`/`1.4740009307861328`; success mean/final `0.0`/`0.0`; cube lift max/final `0.0011679381132125854`/`0.0`.
- behavior_metrics: EE-to-cube mean/final/min/max `0.16845380614201227`/`0.2437351942062378`/`0.14689967036247253`/`0.2437351942062378`; finger-center-to-cube mean/final/min/max `0.16707455115392805`/`0.24166952073574066`/`0.1404552161693573`/`0.24166952073574066`; gripper width mean/final/min/max `0.03806898454980304`/`0.03689180314540863`/`0.03685402497649193`/`0.0735347718000412`.
- target_safety: unsafe target rate max `0.0`; target table clearance min `0.06511414051055908`, above the configured `0.025` m minimum.
- gate_reward_metrics: contact gate mean/final `0.671323234277467`/`0.4682384431362152`; close action reward mean/final/max `0.04193698822834461`/`0.10366229712963104`/`0.12158110737800598`; lift action reward mean/final/max `0.0014248974564035658`/`0.008166111074388027`/`0.008166111074388027`.
- reward_ceiling_vs_utilization: close reward ceiling mean/final/max `0.3401560637184102`/`0.8174505233764648`/`0.8863068222999573` with utilization mean/final/max `0.04562834727888306`/`0.08682597428560257`/`0.09350184351205826`; lift reward ceiling mean/final/max `0.4283437394549882`/`1.3079209327697754`/`1.3080124855041504` with utilization mean/final/max `0.0014013022674286427`/`0.007636710070073605`/`0.007636710070073605`.
- action_metrics: policy close action mean/final `0.07871637370747825`/`0.08682597428560257`; policy up action mean/final `0.026006365313272304`/`0.04892357438802719`; gripper action mean/final `-0.06638652887195348`/`-0.07222630828619003`; z action mean/final `-0.033771018986590205`/`-0.022558368742465973`.
- train_eval_consistency: `train_eval_consistency.json` passed with no mismatches for observation/state/action sizes, cube randomization, reference path/duration, phase observations, close/lift weights, relaxed gate thresholds, min gripper width, and late reference reweight knobs.
- reference: still `curobo_validated=false`; source tag remains `graspgenx_curobo_60mm_export_pending_exact_validation`; this eval remains a trajectory-tracking diagnostic, not a DEXTRAH-ready exact-geometry validated reference claim.

Analysis:
- This confirms the eval artifact path works for the pathological `rew_-inf` checkpoint: per-step trace, summary report, train/eval consistency check, and valid short video are all present and locally inspectable.
- The `-inf` RL-Games suffix is not itself a simulation failure here; it is a short-training metric semantics issue caused by no episode termination before `MAX_ITERATIONS=3`. The useful signal comes from the diagnostic eval, not the checkpoint reward suffix.
- The behavior is not useful for scale-up: reward is finite and target safety is clean, but success/lift remain zero, EE/finger distances worsen by the end, and final visual behavior shows the hand moving away rather than closing/lifting.
- The reward ablation isolates a concrete issue: gate-normalized close/lift reward ceilings are large enough by late rollout, but realized utilization is tiny, especially lift. That points to policy/action learning or action-path incentives failing to produce close/up commands, not to missing logs, unsafe target transforms, or train/eval config drift.

Next:
- Do not launch longer RL from this checkpoint.
- Next bounded debugging should be a diagnostic ablation that makes the short-run metric route interpretable without relying on episode termination: either force a short eval-only action prior / scripted action comparison against the same reference, or alter the tiny RL smoke/eval route to log rollout reward summaries independent of episode completion before any further training.

## 2026-06-11T14:50:58-07:00 - fixed-window rollout metrics and reference-delta sanity plan

Goal:
- Make short trajectory-tracking RL/eval smoke results interpretable without relying on RL-Games episode return suffixes when no env terminates.
- Run one bounded policy-free sanity eval to separate "the learned policy does not emit useful close/up actions" from "the task-space reference cannot be followed through the current Franka delta-IK action interface."

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add episode-independent fixed-window metric summaries to `metrics.json` and add an `action_source` option. Default remains `policy`; a new `reference_delta` mode will step the env without a checkpoint by mapping the current trajectory target EE position plus target gripper width into the existing 7-D Franka action interface.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: add `ACTION_SOURCE` env plumbing and allow no checkpoint only for non-policy evals. Baseline policy eval behavior remains unchanged.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include action source and fixed-window summaries in the report/summary so short runs expose reward terms, EE-to-target, EE/finger-to-cube, gripper, action utilization, safety, lift, and success independent of episode termination.
- Worklog: record the action-interface caveat. This is not cuRobo joint replay; it is a cheap position-only delta-IK sanity baseline using transformed task-space waypoints and the env's gripper schedule.

Validation Plan:
- Local cheap checks: `python3 -m py_compile` on touched Python files, `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, and `git diff --check`.
- Commit/push/deploy exact commit to B l401 worktree.
- Launch one bounded 4-env/480-step `ACTION_SOURCE=reference_delta` eval with video and trace artifacts for `Dextrah-Franka-Cube-Grasp-Traj-Tracking`, same reference path, same reset randomization.
- Fetch full run, validate video metadata/frames, generate trace plot/report/summary/consistency JSON, `viz-open` video/plot/report/contact sheet, inspect behavior, and record exact metrics/URLs.

Acceptance Criteria:
- No long RL training.
- Eval writes `metrics.json`, `trace.csv`, `trace.jsonl`, a valid video, and fixed-window summaries.
- Target unsafe rate remains zero and target clearance stays above `0.025`.
- The result should show whether the current delta-IK action interface can at least approach/contact the reference target. If it cannot, document the minimal bridge needed: a proper IK/action bridge that uses both task-space pose orientation and validated gripper/object contact timing, not blind joint trajectory replay.

Result:
- status: implemented locally; cluster launch pending.
- changed_files: `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, this worklog.
- implementation: `eval_rollout.py` now writes `fixed_window_summaries` for first/middle/last rollout windows and records `action_source`/notes in the summary. The default `policy` action source still loads an RL-Games checkpoint. The new `reference_delta` source runs without a checkpoint and maps the current runtime task-space reference target position plus gripper target width into the existing 7-D Franka delta-IK action convention.
- caveat: `reference_delta` is position-only delta IK plus gripper schedule; it does not replay cuRobo joint trajectories and does not yet track reference orientation. It is intended only as a cheap controller/reference feasibility sanity check.
- wrapper: `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` accepts `ACTION_SOURCE`; `policy` still requires a checkpoint, non-policy sources may omit one. Default behavior remains `ACTION_SOURCE=policy`.
- local_validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- local_validation: `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- local_validation: `git diff --check` passed.

Next:
- Commit/push/deploy exact implementation commit.
- Launch one bounded l401 `ACTION_SOURCE=reference_delta` eval with video, trace files, fixed-window summaries, and artifact bundle. No RL training.

## 2026-06-11T14:54:40-07:00 - reference-delta sanity eval launch

Goal:
- Run the policy-free reference-following sanity baseline through the same trajectory-tracking eval artifact path.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `c1e3bffb619b05ee7abfb87d5ebda685602e2cc6`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `c1e3bffb619b05ee7abfb87d5ebda685602e2cc6`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_refdelta --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refdelta_video480_20260611_145440,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=refdelta-video480,CAPTURE_VIDEO=True,ACTION_SOURCE=reference_delta,PRINT_INTERVAL=120,USE_CUDA_GRAPH=False,SEED=62,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: 1027757 `franka_cube_traj_refdelta`
- expected_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027757.out`
- expected_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refdelta_video480_20260611_145440`

Acceptance Criteria:
- Completion alone is not enough. Inspect `metrics.json`, `trace.csv/jsonl`, video metadata/frames, generated plot/report/consistency JSON, and behavior.
- Fixed-window summaries must exist in `metrics.json`.
- Target unsafe rate remains zero; target clearance remains above `0.025`.
- Result must be labeled as `reference_delta` position-only delta-IK baseline, not learned policy and not cuRobo joint replay.

Result:
- status: completed and inspected; Slurm job `1027757` completed `0:0` after `00:01:18` on `pool0-00016`.
- remote_artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refdelta_video480_20260611_145440/metrics.json`, `trace.csv`, `trace.jsonl`, and `videos/refdelta-video480-step-0.mp4`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027757.out`.
- local_run_artifacts: `cluster_results/l401/franka_cube_traj_tracking_refdelta_video480_20260611_145440/metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refdelta-video480-step-0.mp4`, and `eval_franka_cube_1027757.out`.
- local_summary_bundle: `cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/report.md`, `trajectory_trace_plot.png`, `summary.json`, `train_eval_consistency.json`, `refdelta_contact_sheet_scene_labeled.png`, `refdelta_contact_sheet_labeled.png`, plus extracted frames under `frames/`.
- viz_video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_video480_20260611_145440/videos/refdelta-video480-step-0.mp4`
- viz_plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/trajectory_trace_plot.png`
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/report.md`
- viz_contact_sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/refdelta_contact_sheet_scene_labeled.png`
- video_validation: `ffprobe` reports width `1280`, height `720`, frame rate `60/1`, duration `7.983333`, frame count `479`.
- visual_inspection: first encoded frame is black, so the labeled scene sheet uses frames 30/239/478; frame 30 shows approach above the cube, frame 239 shows contact/closing around the cube, and frame 478 shows the hand away/releasing with cube on the table.
- action_source: `reference_delta`; notes `position_only_delta_ik_from_runtime_task_space_reference_plus_gripper_schedule`. This is not a learned policy, not cuRobo replay, and not joint-trajectory replay.
- rollout_metrics: 480/480 steps, `done_count=2`, reward mean/final `3.2933460235595704`/`1.8666270971298218`, success mean/final/last-window `0.0125`/`0.0`/`0.045`.
- behavior_metrics: cube lift mean/final/max `0.006362190749496221`/`0.0`/`0.06810680031776428`; EE-to-target mean/final/min `0.0446284413880979`/`0.008654721081256866`/`0.002153026405721903`; EE-to-cube mean/final/min `0.11663868233251075`/`0.19660887122154236`/`0.03757987171411514`; finger-center-to-cube mean/final/min `0.15371926327546437`/`0.2357914000749588`/`0.07885409891605377`; gripper width mean/final/min `0.06098952287963281`/`0.051999446004629135`/`0.039746686816215515`.
- target_safety: unsafe target rate max `0.0`; target clearance min `0.06511414051055908`, above the configured `0.025` m minimum.
- action_reward_metrics: close/lift action reward means `0.1146852563705276`/`0.11695309294833957`; close/lift utilization means `0.16947482296576102`/`0.10177070496914288`; contact gate mean `0.6714751257250706`.
- fixed_windows: first window reward `1.7790`, EE-target `0.1011`, no close/lift utilization, no success; middle window reward `3.7954`, EE-target `0.0035`, EE-cube `0.0389`, finger-cube `0.0799`, close utilization `0.2279`, no success; last window reward `3.6765`, success mean `0.05`, lift max `0.0681`, close/lift utilization `0.2500`/`0.1687`, but EE/finger distances worsen to `0.1797`/`0.2148`.
- train_eval_consistency: `train_eval_consistency.json` passed with no mismatches for observation/state/action sizes, cube randomization, reference path/duration, phase observations, close/lift weights, relaxed gate thresholds, min gripper width, and late reference reweight knobs.
- reference: still `curobo_validated=false`; source tag remains `graspgenx_curobo_60mm_export_pending_exact_validation`. The 45 mm GraspGenX vs DEXTRAH 60 mm geometry caveat remains unresolved, so this is not a DEXTRAH-ready exact-geometry validated reference.

Analysis:
- The reference-delta sanity eval answers the immediate controller/reference feasibility question more positively than the learned checkpoint eval: the same transformed runtime task-space reference can drive the Franka delta-IK interface to millimeter-scale EE-target error in the middle window and to near-cube contact, with nonzero close/up utilization and transient lift/success.
- This strongly suggests the remaining B failure is mostly policy/action learning and reward incentive use, not an impossible task-space reference transform or target-safety issue. The learned `rew_-inf` checkpoint failed to emit meaningful close/up actions and drifted away, while the policy-free action source follows the target and produces some lift signal.
- It is still not a solved controller. Final success is zero, `done_count=2` occurs, final EE/finger-to-cube distances worsen, and the video shows the hand releasing/backing away by the end. Because `reference_delta` tracks position only and follows the gripper schedule without orientation/contact hold logic, it likely exposes a timing/hold weakness after transient lift.

Next:
- Do not scale RL training yet.
- Next bounded debugging should use this evidence to make learned policy actions easier to compare against the scripted prior: either add a short diagnostic eval that mixes/clamps learned actions toward `reference_delta` for close/up dimensions, or add a behavior-cloning/action-prior reward/log that penalizes divergence from the reference-delta action in contact/lift phases. The first check should remain eval/smoke-only with video/trace/report artifacts and `curobo_validated=false` explicit.

## 2026-06-11T15:02:24-07:00 - reference-action alignment diagnostic plan

Goal:
- Test whether PPO can be made to emit useful reference-like close/up actions now that the policy-free `reference_delta` baseline proved the transformed task-space reference and current delta-IK action interface can produce contact/transient lift.

Hypothesis:
- The learned checkpoint failed because the reward does not make reference-like close/up/vertical actions salient early enough for PPO. A small auxiliary reward that aligns the policy action with the same position-only `reference_delta` action vector used in the sanity eval should increase close/up utilization in a tiny smoke if action incentives are the primary issue.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: add diagnostic-only config fields for action-alignment weight, phase start, optional contact gate, position/gripper dimensions, and sharpness. Keep defaults scoped to `Dextrah-Franka-Cube-Grasp-Traj-Tracking`; baseline `Dextrah-Franka-Cube-Grasp` remains unchanged.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: factor the `reference_delta` action computation into the task variant, add a gated action-alignment reward against policy actions, and log target/policy action means, alignment error, reward, ceiling, utilization, and gate.
- `dextrah_lab/rl_games/eval_rollout.py`: reuse the task helper for `ACTION_SOURCE=reference_delta` when available; include action-alignment config in eval env summaries for train-vs-eval consistency.
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`: require/summarize the new action-alignment logs in the env smoke.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: add action-alignment config checks and summary/report fields so the tiny eval artifacts show whether PPO action utilization moves toward the prior.
- `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, and `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`: add environment-variable overrides for the new diagnostic knobs so the run is reproducible from Slurm logs.

Validation Plan:
- Local cheap checks: `python3 -m py_compile` on touched Python files, `bash -n` on touched wrappers, and `git diff --check`.
- Commit/push/deploy exact commit to the B l401 worktree.
- Launch one bounded 4-env env smoke for `Dextrah-Franka-Cube-Grasp-Traj-Tracking` with the same unvalidated compact reference. Acceptance: registration works, reset obs remains `[4,72]`, new alignment logs are present/finite, target unsafe remains `0.0`, target clearance stays above `0.025`, no immediate reset pathology.
- If env smoke passes, launch one tiny RL smoke only, with no auto-resume/self-relaunch and no scale-up claim. Then run one short video eval from the resulting checkpoint with fixed-window metrics, trace CSV/JSONL, report, plot, consistency JSON, video/contact sheet, and `viz-open` URLs.

Acceptance Criteria:
- No long training and no A100 scale-up.
- Original `Dextrah-Franka-Cube-Grasp` baseline remains untouched and runnable.
- Observation/state/action dimensions remain baseline-sized (`72`/`72`/`7`); no phase observations.
- Reference caveat remains explicit: `reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay or learned policy, and the compact reference remains `curobo_validated=false`.
- The diagnostic answer should be whether alignment reward produces nonzero, interpretable action-alignment reward/utilization and whether the tiny PPO eval emits more reference-like close/up actions than the previous `rew_-inf` checkpoint.

Result:
- status: implemented locally; cluster env smoke pending.
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`, `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`, this worklog.
- implementation: added `compute_reference_delta_actions()` to the trajectory-tracking task and reused it from eval; added a reward-only `trajectory_tracking_action_alignment_*` diagnostic term that compares policy actions against the reference-delta target over XY/Z/gripper dims, with phase/contact gates and logs for reward, ceiling, utilization, error, target close/up/z/gripper, and policy close/up.
- config: default diagnostic settings are `trajectory_tracking_action_alignment_weight=1.5`, phase start `0.0`, sharpness `1.0`, contact gate disabled, XY/Z/gripper included. This remains only on `Dextrah-Franka-Cube-Grasp-Traj-Tracking`; baseline `Dextrah-Franka-Cube-Grasp` is not modified.
- artifact support: eval metrics/env config and summarizer now include action-alignment knobs and metrics; trace plot height increased to render all four panels, including lift/action.
- wrapper support: validate/eval/train wrappers echo and pass optional `TRAJECTORY_TRACKING_ACTION_ALIGNMENT_*` overrides.
- local_validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- local_validation: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh && bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh && bash -n cluster/sbatch_train_teacher_8gpu.sh` passed.
- local_validation: `git diff --check` passed.

Next:
- Commit/push/deploy exact implementation commit to the B l401 worktree.
- Launch one 4-env/480-step alignment env smoke with no video first. If it passes and logs are finite/present with target safety intact, launch the tiny PPO smoke and a short video eval artifact bundle. No scale-up.

## 2026-06-11T15:08:40-07:00 - reference-action alignment env smoke launch

Goal:
- Validate the action-alignment diagnostic wiring in the real DEXTRAH/Isaac task before any PPO smoke.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `c5d5b50568aefb5b44ae43e93d5c56239e05e7c8`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `c5d5b50568aefb5b44ae43e93d5c56239e05e7c8`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_align_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=1,CAPTURE_VIDEO=False,PRINT_INTERVAL=120,SEED=63,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027763 `franka_cube_traj_align_smoke`
- expected_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027763.out`
- expected_metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840/metrics.json`

Acceptance Criteria:
- Task registration works and reset observation remains `[4,72]`.
- New `cube_traj_tracking_action_alignment_*` and reference-action logs are present and finite.
- Target unsafe rate remains `0.0`, target clearance remains above `0.025`, and no immediate reset/termination pathology appears.
- This validates wiring only; no learned-policy behavior claim.

Result:
- status: passed wiring/runtime validation; Slurm job `1027763` completed `0:0` after `00:00:57` on `pool0-00016`.
- remote_artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840/metrics.json`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027763.out`.
- local_run_artifacts: `cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840/metrics.json`, `cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840/validate_franka_cube_1027763.out`.
- local_summary_bundle: `cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_artifacts_20260611_150840/report.md`, `summary.json`, `config.json`, `validation_trace.csv`, `validation_trace.jsonl`, `validation_trace_plot.png`, and `no_video_contact_sheet.png`.
- viz_report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_artifacts_20260611_150840/report.md`
- viz_plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_artifacts_20260611_150840/validation_trace_plot.png`
- viz_no_video_sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_env_smoke_artifacts_20260611_150840/no_video_contact_sheet.png`
- validation: `passed=true`; registration/reset obs `[4,72]`; 480/480 steps; `done_count=0`, `early_done_count=0`; reward mean/final `2.146636782834927`/`1.5051473379135132`; final success `0.0`; max mean lift `0.0026998966932296753`; final gripper width `0.020000018179416656`.
- target_safety: `tracking_unsafe_target_rate_max=0.0`; target clearance min and batch min `0.06511414051055908`.
- alignment_logs: missing logs `[]`; alignment reward mean `0.3232666042396886`; ceiling mean `0.5921848454435046`; utilization mean `0.49077520444989203`; alignment error mean `0.8480767693370581`; alignment phase gate final `1.0`; contact gate for alignment `1.0`.
- action_comparison: scripted validation policy action close/up means `0.33229166666666665`/`0.165625`; reference-delta close/up means `0.20780815382798512`/`0.8821516993736925`, confirming the diagnostic target asks for substantially more upward action than the current scripted validation actions.
- reference: still `curobo_validated=false`; source tag `graspgenx_curobo_60mm_export_pending_exact_validation`; `reference_delta` remains position-only delta IK plus gripper schedule, not cuRobo replay.
- artifact_caveat: this smoke was launched with `CAPTURE_VIDEO=False` before the stricter artifact cadence. The bundle includes a no-video sheet and parsed trace/plot, but the next PPO/eval step must include video/contact sheets.

Analysis:
- The action-alignment reward path is wired and finite under Isaac. It adds a meaningful reward scale without target-safety regression or reset pathology.
- The reference-vs-actual action comparison shows the diagnostic is testing the intended question: the reference prior wants high upward action on average (`0.882`) while the scripted validation action schedule only supplies low upward action (`0.166`). PPO eval can now reveal whether the learned policy moves toward that reference-like action profile.
- This remains wiring evidence only. No learning or behavior success is claimed from 1027763.

Next:
- Commit/push the validation artifact summarizer and worklog result.
- Launch exactly one tiny PPO smoke from the pushed branch, then run fixed-seed and random-seed short video evals from its checkpoint if a checkpoint is produced. Fetch each eval's metrics/video/trace artifacts, generate plots/reports/contact sheets, `viz-open` them, and record pass/fail interpretation before any further action.

## 2026-06-11T15:12:47-07:00 - artifact lineage clarification before PPO smoke

Goal:
- Make the trajectory-tracking artifact lineage explicit before launching the next bounded PPO smoke, because the user asked specifically about the older `actionscale-rewinf-diag-video480-step-0.mp4`.

Lineage:
- `franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`: earlier failed learned-policy diagnostic from the pathological `1027751` `rew_-inf` checkpoint. It showed zero success/lift, worsening EE/finger distances, and the hand drifting/hovering rather than grasping. It is not the current action-alignment run.
- `franka_cube_traj_tracking_refdelta_video480_20260611_145440/videos/refdelta-video480-step-0.mp4`: policy-free feasibility diagnostic. `ACTION_SOURCE=reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay and not a learned policy. It produced contact/transient lift and showed the transformed reference plus current action interface are not impossible.
- `1027763` / `franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840`: current action-alignment wiring smoke. It passed with action-alignment metrics present/finite, target unsafe max `0.0`, target clearance min `0.06511414051055908`, no early done, but no video because it was launched before the stricter visual artifact cadence.
- Next run: one bounded tiny PPO smoke under the action-alignment diagnostic config, followed by fixed-seed and random-seed short video eval bundles if a checkpoint is produced. Each eval bundle must include video/contact sheet, trace CSV/JSONL, reward/action-alignment plot, report, train-vs-eval consistency JSON, `viz-open` URLs, and a pass/fail interpretation of whether the policy follows the object-conditioned reference instead of drifting.

Status:
- Current branch commit before PPO launch: `a0a92c04fdd4d3f3b132c73aaa3f1f66590837e7`.
- Local worktree was clean before this worklog-only clarification.

## 2026-06-11T15:15:20-07:00 - action-alignment tiny PPO smoke launch

Goal:
- Run one bounded PPO smoke under the action-alignment diagnostic config, then evaluate the produced checkpoint with video artifacts if checkpoint creation succeeds.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `14730339f35bac7409b93cebd50c82aaa6bbf9ce`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` at `14730339f35bac7409b93cebd50c82aaa6bbf9ce`, detached clean after HTTPS fetch fallback.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=franka_cube_traj_align_rl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=16,HORIZON_LENGTH=32,MINIBATCH_SIZE=512,CENTRAL_VALUE_MINIBATCH_SIZE=512,MINI_EPOCHS=1,MAX_ITERATIONS=5,SAVE_FREQUENCY=5,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027766 `franka_cube_traj_align_rl`
- expected_log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027766.out`
- expected_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`

Acceptance Criteria:
- One GPU, 16 envs, horizon `32`, max iterations `5`; no auto-resume/self-relaunch.
- Resolved env config remains obs/state/action `72`/`72`/`7`, phase observations false, action-alignment weight/phase/sharpness/contact-gate `1.5`/`0.0`/`1.0`/`False`, same unvalidated reference path.
- No traceback/NaN; actor/critic build with input dimension `72`; checkpoint written.
- This is training wiring only. Any `rew_-inf` suffix from no episode termination must be labeled as short-run metric semantics, not policy success/failure by itself.
- If a checkpoint exists, run fixed-seed and random-seed short video eval bundles before any further training.

Result:
- status: completed `0:0` in `00:00:53` on `pool0-00016`; checkpoint produced.
- remote_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth`
- evidence: actor/critic both built with MLP input `72`; run wrote `params/env.yaml`, `params/agent.yaml`, TensorBoard event file, `dextrah_runtime_rank_0.pth`, and the epoch-5 checkpoint.
- metric_semantics: `rew_-inf` is the expected short RL-Games episode-return suffix when no environment terminates during this five-epoch smoke (`WARNING: Max epochs reached before any env terminated at least once`). It is not by itself a policy verdict.

Analysis:
- This is a training-wrapper/checkpoint smoke only. It confirms the action-alignment task variant can instantiate and optimize for five short epochs without NaN/traceback, but no conclusion about approach/grasp behavior can be drawn until fixed-window eval/video artifacts are inspected.

Next:
- Run fixed-seed and alternate-seed 480-step video evals from the epoch-5 `rew_-inf` checkpoint. Required artifacts: metrics JSON, trace CSV/JSONL, train-vs-eval consistency JSON, reward/action-alignment plots, contact sheets, mp4s, `viz-open` URLs, and pass/fail interpretation against the old actionscale failed learned-policy video.

## 2026-06-11T15:24:20-07:00 - action-alignment PPO eval video launch

Goal:
- Evaluate the `1027766` action-alignment checkpoint with two bounded 480-step policy rollouts so behavior is numerically and visually inspectable before any further training.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `2fddf05102af4e9b620f7adca40640a98478be89`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `2fddf05102af4e9b620f7adca40640a98478be89`, clean; HTTPS fetch was required because l401 SSH fetch to `git@github.com:lihzha/DEXTRAH.git` lacks a key.

Command / Jobs:
- fixed command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=traj_align_eval_fix --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=actionalign-rl5-fixed-video480,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- fixed job_id: `1027769`
- fixed run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420`
- fixed log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027769.out`
- random command: same config with `RUN_NAME=franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420`, `VIDEO_NAME_PREFIX=actionalign-rl5-random-video480`, and `SEED=165`.
- random job_id: `1027770`
- random run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420`
- random log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027770.out`

Acceptance Criteria:
- Both evals write `metrics.json`, `trace.csv`, `trace.jsonl`, and a valid 480-frame-ish mp4.
- Summaries include `cube_traj_tracking_action_alignment_*`, close/up action diagnostics, target safety/clearance, EE/finger/cube distances, gripper width/action, lift/success, and fixed-window summaries.
- Train/eval config audit is saved and reviewed. Expected observation size remains 72 and phase observations remain false.
- Pass/fail interpretation must answer whether action alignment increases close/up/reference-like actions and produces approach/contact behavior compared with the old `actionscale-rewinf` failed learned-policy artifact. No scale-up before inspection.

Result:
- status: completed and fetched; both evals wrote metrics, trace CSV/JSONL, and mp4s.
- fixed job `1027769`: completed `0:0` in `00:01:21` on `pool0-00016`; local run dir `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420`.
- random job `1027770`: completed `0:0` in `00:01:47` on `pool0-00037`; local run dir `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420`.
- video validation: both mp4s are valid `1280x720`, `479` frames, `7.983333` seconds. Frame 0 is black recorder warm-up, so contact sheets use first usable frame 30 plus middle and last frames.
- train/eval consistency: both per-run `train_eval_consistency.json` files passed with no mismatches.
- fixed metrics: reward mean/final `1.5777`/`1.3953`; success final `0`; lift max `0.0015115 m`; final EE-to-cube `0.5963 m`; final finger-center-to-cube `0.5611 m`; final gripper width `0.0587 m`; target unsafe max `0`; target clearance min `0.065114 m`; action-alignment utilization mean `0.3469`; close/lift utilization mean `0.0`/`0.000106`; reference close/up action means `0.2078`/`0.4614`.
- random metrics: reward mean/final `1.6756`/`1.6011`; success final `0`; lift max `0`; final EE-to-cube `0.4168 m`; final finger-center-to-cube `0.3783 m`; final gripper width `0.0492 m`; target unsafe max `0`; target clearance min `0.065114 m`; action-alignment utilization mean `0.4012`; close/lift utilization mean `0.0110`/`0.00124`; reference close/up action means `0.2078`/`0.8033`.
- visual diagnosis: fixed contact sheet shows an initial approach but by middle/last frames the hand moves away/around the cube with no grasp. Random contact sheet shows the hand near the cube initially but drifting/hovering without grasp by middle/last frames. Neither eval is a plausible approach/contact behavior.
- artifact bundle:
  - combined report: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_comparison_20260611_152420/comparison_report.md`
  - combined summary: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_comparison_20260611_152420/summary.json` and `summary.csv`
  - combined plot: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_comparison_20260611_152420/behavior_action_comparison.png`
  - fixed per-run report/plot/sheet/video: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420_artifacts/report.md`, `trajectory_trace_plot.png`, `contact_sheet_firstusable.png`, and `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420/videos/actionalign-rl5-fixed-video480-step-0.mp4`
  - random per-run report/plot/sheet/video: `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420_artifacts/report.md`, `trajectory_trace_plot.png`, `contact_sheet_firstusable.png`, and `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420/videos/actionalign-rl5-random-video480-step-0.mp4`
- viz_urls:
  - combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_comparison_20260611_152420/comparison_report.md`
  - combined plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_comparison_20260611_152420/behavior_action_comparison.png`
  - fixed contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420_artifacts/contact_sheet_firstusable.png`
  - random contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420_artifacts/contact_sheet_firstusable.png`
  - fixed video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420/videos/actionalign-rl5-fixed-video480-step-0.mp4`
  - random video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420/videos/actionalign-rl5-random-video480-step-0.mp4`

Analysis:
- Pass/fail: fail behaviorally. The action-alignment reward is wired and nonzero, but this 5-epoch PPO checkpoint still does not emit sufficiently reference-like close/up/gripper actions and does not grasp.
- Compared with the old `actionscale-rewinf` failed learned-policy artifact, action-alignment improves the availability of a reference-action reward signal but does not improve the core behavior enough. Fixed seed is worse on final EE/finger distances; alternate seed is still far from the cube and has zero lift/success.
- Compared with policy-free `reference_delta`, the learned policy remains much worse. `reference_delta` produced transient lift (`0.068 m` max) and much larger close/lift utilization, so the transformed reference plus delta-IK action interface is feasible. The remaining issue is policy/action learning and incentive strength/timing, not basic reference transform/controller impossibility.
- Reference caveat remains explicit: `curobo_validated=false`; `reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay and not a learned policy.
- No scale-up is justified from these artifacts.

Next:
- Proposed next bounded fix: implement an eval-only reference-action mixing/clamping diagnostic before new PPO training. Add an `ACTION_SOURCE=policy_reference_mix` route (or equivalent) that loads the learned policy action, computes `reference_delta`, and blends selected dimensions with coefficients such as `0.25`, `0.50`, `0.75`, and `1.0`.
- Acceptance: same 480-step video/trace bundle, target unsafe remains `0`, consistency JSON passes, and traces log raw policy action, reference action, mixed action, action error, lift/success, EE/finger distances, gripper width/action, and close/up utilization. If mixing recovers approach/contact, the next training-side step should be stronger direct imitation/BC or a higher-weight KL/action imitation term. If mixing fails, inspect controller/action mapping or phase/reference timing before more PPO.

## 2026-06-11T15:30:44-07:00 - policy-reference mix eval-only diagnostic plan

Goal:
- Implement and launch the bounded `policy_reference_mix` diagnostic requested by the user. This is eval-only and uses the epoch-5 action-alignment PPO checkpoint; no PPO scale-up.

Hypothesis:
- If the transformed task-space reference plus delta-IK action interface is feasible, blending the failed learned policy action toward the policy-free `reference_delta` action should monotonically recover approach/contact as alpha increases. If `alpha=1.0` does not resemble the earlier `reference_delta` feasibility run, the bug is likely in the action-source plumbing, action mapping, phase/reference timing, or eval config rather than PPO learning.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add `--action_source policy_reference_mix` and `--reference_mix_alpha`; load the RL-Games checkpoint, compute raw policy actions and `reference_delta` actions each step, blend `mixed=(1-alpha)*policy+alpha*reference`, clamp to action range, step the env with the mixed action, and log raw policy/reference/mixed action statistics plus action error.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: export `REFERENCE_MIX_ALPHA`, require `CHECKPOINT` for `policy_reference_mix`, echo the setting, and pass `--reference_mix_alpha`.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include mix alpha and the new policy/reference/mixed action-error metrics in `summary.json`/`report.md` so every run has an inspectable artifact bundle.
- Owned worklog only: record commands, commits, job IDs, artifact paths, `viz-open` URLs, and pass/fail interpretation.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- Commit and push the implementation, then update the agent-owned l401 worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` to the exact commit via Git.

Planned Jobs:
- Four l401 eval-only 480-step video jobs with `ACTION_SOURCE=policy_reference_mix`, `REFERENCE_MIX_ALPHA` in `{0.25,0.50,0.75,1.0}`, `NUM_ENVS=4`, fixed seed `64`, same unvalidated 60 mm compact reference path, same action-alignment eval config, and checkpoint `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth`.

Artifact Contract:
- For every mix run fetch remote results locally, validate video metadata/frame count, generate a first-usable/middle/last contact sheet, run the trajectory summarizer, create/record `viz-open` URLs for mp4/contact sheet/plot/report, and inspect metrics plus frames.
- Generate a combined comparison report/summary/plot across old `actionscale-rewinf`, current failed `actionalign-rl5`, policy-free `reference_delta`, and the four mix alphas.

Acceptance Criteria:
- Each mix eval writes `metrics.json`, `trace.csv`, `trace.jsonl`, mp4, per-run report, plot, consistency JSON, contact sheet, and summary.
- Logs include raw policy action, reference action, mixed action, policy-reference error, lift/success, EE/finger distances, gripper width/action, close/up utilization, target unsafe/clearance, and `reference_mix_alpha`.
- Target unsafe remains `0`; train/eval config audit is understood; observation size remains `72`, phase observations false; reference caveat remains explicit: `curobo_validated=false`, and `reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay.
- Final interpretation directly answers whether mixing recovers approach/contact compared with the old `actionscale-rewinf` and current `actionalign-rl5` failures.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `6dc3fd22668f7625b9d6c706d3a65964aa351908`
- implementation_commit: `60630378cfc5ff0035143afed32dc829ce36a368` before worklog hash amendment
- changed_files: `dextrah_lab/rl_games/eval_rollout.py`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`, `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Implementation Checkpoint:
- `eval_rollout.py` now supports `ACTION_SOURCE=policy_reference_mix` via `--reference_mix_alpha`, loads the RL-Games policy, computes the existing `reference_delta` action, applies the clamped blended action, and records raw-policy/reference/mixed action statistics and error terms in `metrics.json`/trace rows.
- `sbatch_eval_franka_cube_grasp_1gpu.sh` now exports/echoes `REFERENCE_MIX_ALPHA`, requires a checkpoint for `policy_reference_mix`, and passes `--reference_mix_alpha`.
- `summarize_traj_tracking_eval_artifacts.py` now includes mix alpha, raw/reference/mixed close-up action overlays, and policy/reference error summaries in `summary.json`, report tables, and the diagnostic trace plot.
- validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- validation: `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- validation: summarizer regression on `cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420/metrics.json` wrote `/tmp/traj_summary_regression/{report.md,summary.json,train_eval_consistency.json,trajectory_trace_plot.png}` and correctly showed new mix-only fields as `n/a` for the older pure-policy run.

## 2026-06-11T15:34:42-07:00 - policy-reference mix eval launch

Goal:
- Run the bounded alpha sweep for `policy_reference_mix` using the action-alignment epoch-5 checkpoint. This is diagnostic eval only; no new training or PPO scale-up.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `354c9c9057f728e3ad48982d9ce5c0a24c5e934e`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `354c9c9057f728e3ad48982d9ce5c0a24c5e934e`, clean after HTTPS fetch.

Shared Config:
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`
- action source: `policy_reference_mix`
- seed: `64`; num_envs: `4`; num_steps/video_length: `480`; deterministic: `True`
- tracking/action-alignment eval config: `TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5`, phase start `0.0`, sharpness `1.0`, contact gate `False`, reset XY randomization `0.08`, CUDA graph disabled.
- caveat: compact reference remains `curobo_validated=false`; `reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay.

Command / Jobs:
- command template: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_a<tag> --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=<run>,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=<prefix>,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix,REFERENCE_MIX_ALPHA=<alpha>,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- alpha `0.25`: job_id `1027777`; run `franka_cube_traj_tracking_policy_refmix_a025_video480_20260611_153442`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027777.out`
- alpha `0.50`: job_id `1027778`; run `franka_cube_traj_tracking_policy_refmix_a050_video480_20260611_153442`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027778.out`
- alpha `0.75`: job_id `1027779`; run `franka_cube_traj_tracking_policy_refmix_a075_video480_20260611_153442`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027779.out`
- alpha `1.0`: job_id `1027780`; run `franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442`; log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027780.out`

Acceptance:
- For each job, fetch results, inspect log and metrics, validate mp4 metadata, generate contact sheet/report/plot/summary/consistency JSON, open viewer URLs, and compare behavior against old `actionscale-rewinf`, failed `actionalign-rl5`, and policy-free `reference_delta`.

Result:
- status: all four jobs completed `0:0`, fetched locally, summarized, and visually inspected.
- video validation: all four mp4s are valid `1280x720`, `479` frames, `7.983333` seconds, `60/1` FPS.
- train/eval consistency: all four per-run consistency JSONs passed with no mismatches. Observation/state/action sizes remained `72/72/7`, phase observations stayed `False`, reset randomization/reference path/action-alignment config matched the training smoke config.
- target safety: all four had `target_unsafe_rate_max=0.0` and `target_clearance_min=0.06511414051055908`.
- reference caveat: all four use the compact reference with `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`; `reference_delta` remains position-only delta IK plus gripper schedule, not cuRobo replay.

Alpha Sweep Metrics:

| Alpha | Job | Reward mean/final | Success final/last | Lift max m | EE-cube final m | Finger-cube final m | Mixed ref L2 | Mixed up/close mean | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.25 | 1027777 | 1.8533 / 1.5442 | 0.0 / 0.0 | 0.0000 | 0.5752 | 0.5319 | 1.5136 | 0.1243 / 0.0000 | weak mix stays close to failed policy; approaches then drifts away, no lift/success |
| 0.50 | 1027778 | 2.8628 / 2.3131 | 0.0 / 0.0 | 0.0000 | 0.2572 | 0.2559 | 0.7402 | 0.1815 / 0.0142 | clearer mid-rollout approach/contact vicinity but final hand away and cube on table |
| 0.75 | 1027779 | 3.1953 / 2.6037 | 0.0 / 0.0 | 0.0000 | 0.2406 | 0.2685 | 0.2861 | 0.2084 / 0.1054 | similar partial recovery; near cube mid-rollout then departs, no lift/success |
| 1.00 | 1027780 | 4.0495 / 2.3340 | 0.0 / 0.0675 | 0.1021 | 0.1774 | 0.2178 | 0.0000 | 0.2969 / 0.1507 | full reference override recovers transient contact/lift; final success still zero after release |

Artifacts:
- combined report: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/comparison_report.md`
- combined summary: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/summary.json` and `summary.csv`
- combined plot: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/policy_refmix_comparison_plot.png`
- combined contact-sheet grid: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/policy_refmix_contact_sheet_grid.png`
- alpha 0.25 bundle: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a025_video480_20260611_153442/` and `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a025_video480_20260611_153442_artifacts/`
- alpha 0.50 bundle: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a050_video480_20260611_153442/` and `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a050_video480_20260611_153442_artifacts/`
- alpha 0.75 bundle: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a075_video480_20260611_153442/` and `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a075_video480_20260611_153442_artifacts/`
- alpha 1.00 bundle: `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/` and `cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442_artifacts/`
- per-run bundle contents: `metrics.json`, `trace.csv`, `trace.jsonl`, stdout log copy, mp4, `report.md`, `summary.json`, `summary.csv`, `trajectory_trace_plot.png`, `train_eval_consistency.json`, `video_metadata.json`, first/middle/last frames, and `contact_sheet_firstusable.png`.

Viz URLs:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/comparison_report.md`
- combined plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/policy_refmix_comparison_plot.png`
- combined contact grid: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_comparison_20260611_153442/policy_refmix_contact_sheet_grid.png`
- alpha 0.25 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a025_video480_20260611_153442_artifacts/contact_sheet_firstusable.png`
- alpha 0.50 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a050_video480_20260611_153442_artifacts/contact_sheet_firstusable.png`
- alpha 0.75 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a075_video480_20260611_153442_artifacts/contact_sheet_firstusable.png`
- alpha 1.00 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442_artifacts/contact_sheet_firstusable.png`
- alpha 1.00 quick sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/contact_sheet_quick.jpg`
- alpha 1.00 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/videos/policy-refmix-a10-video480-step-0.mp4`

Analysis:
- Direct answer: the mix implementation is acting correctly. `mixed_reference_action_error_l2_mean` decreases with alpha and reaches exactly `0.0` at alpha `1.0`; alpha `1.0` recovers the policy-free reference-style transient lift signal. This rejects the hypothesis that the failure is a basic task-space transform, delta-IK action interface, or phase schedule impossibility.
- The remaining failure is timing/phase/hold/stability. The reference/action path can produce contact/lift mid-rollout, but the rollout ends with the cube back on the table and the hand away. Partial mixes approach more plausibly than the learned policy but still do not produce enough close/hold/lift behavior.
- This is not learned-policy success. Alpha `1.0` is an eval-only action override equivalent to `reference_delta`; no PPO scale-up is justified from the learned checkpoint.
- The next training-side direction should not track the whole reference blindly. It should either train/imitation-match through approach/pregrasp/grasp and then hand off to a hold/lift objective, or add a terminal hold/stability phase to the reference/action diagnostic before PPO scale-up.

Next Proposed Bounded Diagnostic:
- Implement an eval-only `reference_delta_hold` or `policy_reference_mix_hold` action source/config: run alpha `1.0`/reference_delta until contact/lift/success or a fixed phase threshold, then freeze the current lifted/object-conditioned EE target, keep the gripper command closed, and hold/lift vertically for the remainder of a 480-step rollout.
- Acceptance for this tiny job: target unsafe remains `0`, no reset pathology, `mixed_reference_l2=0` before hold, final success/lift remains positive rather than only transient, and video/contact sheet shows sustained grasp/hold through the final frame.
- If hold fixes final success, patch the training design toward approach/pregrasp/grasp tracking followed by RL hold/lift stabilization instead of full-trajectory tracking. If hold still fails, debug gripper closure/contact geometry/pose target stability before more PPO.
- No long PPO scale-up until this hold/stabilization diagnostic is run and visually/quantitatively inspected.

## 2026-06-11T15:44:28-07:00 - terminal hold/reference stabilization diagnostic plan

Goal:
- Implement and run the next bounded eval-only terminal hold diagnostic requested by the orchestrator. This is not PPO scale-up.

Hypothesis:
- The alpha `1.0` policy-reference sweep proved the transformed reference plus delta-IK action interface can produce transient lift, but final success drops because the reference/phase timing moves the hand away or fails to stabilize the grasp. If we follow the reference until contact/lift/success or a fixed phase threshold, then hold a stable object-conditioned lifted EE target with a closed gripper, final lift/success should be sustained. If not, the remaining problem is gripper/contact/hold target stability rather than PPO learning alone.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add eval-only action sources `reference_delta_hold` and `policy_reference_mix_hold`; add hold parameters for phase trigger, lift trigger, contact trigger, hold lift height, and gripper close command; maintain per-env hold state; log hold-active/trigger rates, hold target position, reference/policy/mixed/hold actions, and action errors.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: export/pass the hold parameters and require `CHECKPOINT` for `policy_reference_mix_hold`.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include hold config and hold metrics in summary/report artifacts so the run is inspectable without opening raw `metrics.json`.
- Owned worklog only: record validation, exact commit, l401 deploy state, job id, remote/local run dirs, artifact paths, `viz-open` URLs, and interpretation.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- Commit/push, then update the agent-owned l401 worktree to the exact commit via Git.

Planned Job:
- One 480-step video eval on l401 with `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=1.0`, the same epoch-5 action-alignment checkpoint, `NUM_ENVS=4`, seed `64`, same unvalidated 60 mm compact reference, and bounded hold defaults.
- Candidate hold defaults: trigger when `traj_phase_progress >= 0.42`, `cube_lift_height >= 0.02 m`, `in_success_region > 0`, or `max_finger_to_cube_dist <= 0.16 m`; target is `cube_pos_at_trigger + [0, 0, 0.10]` with z at least current EE z; gripper action `-1.0`.

Acceptance Criteria:
- `metrics.json`, `trace.csv`, `trace.jsonl`, stdout log, mp4, contact sheet, `report.md`, `summary.json/csv`, `trajectory_trace_plot.png`, and `train_eval_consistency.json` are fetched locally and opened with `viz-open`.
- Target unsafe remains `0`; target clearance remains sane; observation size remains `72`, phase observations false, no reset pathology, and reference caveat remains explicit: `curobo_validated=false`, `reference_delta` is position-only delta IK plus gripper schedule, not cuRobo replay.
- The report directly answers whether terminal hold recovers sustained final lift/success compared with alpha `1.0` transient lift and the failed learned-policy artifacts.

Implementation Checkpoint:
- `eval_rollout.py` now supports `reference_delta_hold` and `policy_reference_mix_hold`, including per-env hold state, phase/lift/success/contact triggers, frozen object-conditioned lift targets, closed gripper hold actions, pre-hold policy/reference/mixed action metrics, applied hold action metrics, and reset-aware hold-state clearing.
- `sbatch_eval_franka_cube_grasp_1gpu.sh` now exports/echoes/passes `HOLD_PHASE_START`, `HOLD_TRIGGER_LIFT_HEIGHT`, `HOLD_CONTACT_MAX_FINGER_DIST`, `HOLD_LIFT_HEIGHT`, and `HOLD_GRIPPER_ACTION`; `policy_reference_mix_hold` requires `CHECKPOINT`.
- `summarize_traj_tracking_eval_artifacts.py` now includes hold config, hold activation/trigger/action/error metrics, fixed-window hold columns, and hold-active trace plotting.
- validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- validation: `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- validation: `git diff --check` passed.
- validation: summarizer regression on previous alpha `1.0` refmix metrics wrote `/tmp/traj_hold_summary_regression/{report.md,summary.json,train_eval_consistency.json,trajectory_trace_plot.png}` with hold-only fields as `n/a`.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `d8956ac8131e26130ebba16be6082119c71e22a7`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `d8956ac8131e26130ebba16be6082119c71e22a7` after HTTPS fetch.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_hold_a10 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=refmix-hold-a10-video480,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=1.0,HOLD_PHASE_START=0.42,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.16,HOLD_LIFT_HEIGHT=0.10,HOLD_GRIPPER_ACTION=-1.0,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027825`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027825.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refmix-hold-a10-video480-step-0.mp4`, local summary/report/plot/contact sheet after fetch.

Launch Status:
- submitted to l401 as eval-only diagnostic. Awaiting completion and artifact inspection.

Result:
- status: completed `0:0` in `00:01:25` on `pool0-00004`; fetched locally, summarized, and visually inspected.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts`
- video validation: `1280x720`, `479` frames, `7.983333 s`, `60/1` FPS.
- metrics: `num_steps_completed=480`, `done_count=3`, `reward_mean/final=3.9467/2.6719`, `success_rate_mean/final/max=0.01875/0/0.75`, `cube_lift_height_max=0.108942 m`, `cube_lift_height_final=0`, `target_unsafe_rate_max=0`, `target_clearance_min=0.065114 m`.
- hold metrics: `hold_active_rate_mean/final=0.1729/0.25`; first trigger at step `319`; trigger route was lift (`hold_lift_trigger_rate_mean=0.1729`, phase/success/contact triggers `0`); target policy id `1.0` confirms `cube_current_plus_trigger_ee_offset`; final trigger offset mean x/y/z `-0.000152/0.000365/0.009102 m`; `mixed_reference_action_error_l2_mean=0.0`; `applied_reference_action_error_l2_mean=0.1274`.
- behavior metrics: final EE-to-cube `0.1190 m`, final finger-center-to-cube `0.1601 m`, final gripper width `0.0660 m`. These final values are post-reset/post-drop and should not be read as the whole rollout behavior.
- success-window trace: step `319` entered hold at cube lift `0.0225 m`; step `363` reached `success_rate=0.75`; step `373` reached `cube_lift_height=0.1089 m` and `success_rate=0.75`; by step `380`, phase dropped to `0.206`, lift reset to `0`, and only one env remained in hold (`hold_active_rate=0.25`), consistent with `done_count=3`.
- consistency artifact: corrected after the initial summary used a nonexistent train YAML. Final `train_eval_consistency.json` status is `passed`, with real mismatches, missing train keys, and missing eval keys all empty; expected eval overrides include action source, alpha, hold config, checkpoint, deterministic/video settings, and requested step count.
- artifact paths:
  - report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/report.md`
  - summary: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/summary.json` and `summary.csv`
  - trace plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/trajectory_trace_plot.png`
  - full video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358/videos/refmix-hold-offset-a10-video480-step-0.mp4`
  - full contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/contact_sheet_first_mid_lift_final.jpg`
  - success-window slow video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_slow_step300_380.mp4`
  - success-window contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_contact_sheet.jpg`
  - consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/train_eval_consistency.json`
- viz_urls:
  - full video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358/videos/refmix-hold-offset-a10-video480-step-0.mp4`
  - full contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/contact_sheet_first_mid_lift_final.jpg`
  - success-window slow video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_slow_step300_380.mp4`
  - success-window contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_contact_sheet.jpg`
  - trace plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/trajectory_trace_plot.png`
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/report.md`
  - consistency JSON: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/train_eval_consistency.json`

Analysis:
- This is not a simple drift failure and not a learned-policy success claim. The offset-hold policy preserved the trigger-frame contact geometry well enough to produce transient task success (`success_rate=0.75`) and max lift `0.1089 m`, with target safety still clean.
- The final `success_rate=0` is misleading by itself because three envs reset after the success window (`done_count=3`), and the final frame/last metrics reflect post-reset/post-drop state for most envs.
- Existing `1027851` metrics were produced before per-env success/done instrumentation, so `success_ever` and done reasons cannot be recovered exactly from the aggregate trace. The aggregate trace does show max concurrent success `0.75`, but not per-env success history or done reason attribution.

Next:
- Patch eval artifacts to log `success_ever`, first/last success step, per-step done rates, done-after-success count, and per-env first-done event records with pre-auto-reset reason snapshots. Then run one bounded success-window eval/video around the same offset-hold setup; no PPO scale-up.

## 2026-06-11T16:10:00-07:00 - success/done semantics artifact plan

Goal:
- Make the offset-hold diagnostic interpretable around the first success/reset window rather than relying on final metrics after auto-reset.

Hypothesis:
- `1027851` likely reached real task success in three envs and reset due success-timeout semantics rather than simply drifting/dropping. Adding per-env event logging and a short success-window video should distinguish robust success/reset from brief visual lift/drop.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: track per-env `success_ever`, first/last success step, done-ever, first done step, done-after-success, and first-done event records. Snapshot likely done reasons before `env.step()` can auto-reset state, including success-timeout, cube-out, pre-lift drag, finger-table penetration, and truncation.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: surface success/done semantics in `summary.json`, `summary.csv`, and `report.md`.
- Artifact generation: produce a success-window slow video/contact sheet focused on steps around lift trigger, success, max lift, and reset.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`

Planned Job:
- One bounded eval-only success-window run on l401 with the same checkpoint/reference/seed/config as `1027851`, `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=1.0`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_CONTACT_MAX_FINGER_DIST=0.0`, `HOLD_PHASE_START=0.67`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_LIFT_HEIGHT=0.03`, `HOLD_GRIPPER_ACTION=-0.4`, `NUM_ENVS=4`, `NUM_STEPS=390`, `VIDEO_LENGTH=390`.

Acceptance:
- Report must include non-null `success_ever`, first/last success steps, done-after-success counts, and per-env first-done event records when any env resets.
- Viewer bundle must include mp4, success-window contact sheet, trace plot, report, summary JSON/CSV, consistency JSON, and stdout log.
- Interpretation must answer whether offset-hold achieves task success before reset and whether reset/drop semantics make final success misleading. No PPO scale-up.

Result:
- status: completed `0:0` in `00:01:25` on `pool0-00016`; fetched locally and summarized.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts`
- video validation: `1280x720`, `479` frames, `7.983333 s`, `60/1` FPS.
- metrics: `num_steps_completed=480`, `done_count=0`, `reward_mean/final=2.9975/4.0639`, `success_rate_mean/final=0/0`, `cube_lift_height_max=0`, `target_unsafe_rate_max=0`, `target_clearance_min=0.065114`.
- hold metrics: `hold_active_rate_mean/final=0.7464/1.0`; first trigger around step `122.75`; `hold_contact_trigger_rate_mean=0.7464`, while phase/lift/success trigger rates stayed `0`; `mixed_reference_action_error_l2_mean=0.0` as expected for alpha `1.0`; `applied_reference_action_error_l2_mean=1.0199` after hold diverged from the reference; final gripper width `0.000212 m`.
- behavior metrics: final EE-to-cube `0.1128 m`, final finger-center-to-cube `0.1538 m`, final gripper closed, but no lift/success.
- visual diagnosis: contact sheet/video show the hand hovering above/near the cube through middle and final frames. The cube remains on the table; the terminal hold closes the gripper away from a valid grasp rather than stabilizing a lifted cube.
- artifact paths:
  - report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/report.md`
  - summary: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/summary.json` and `summary.csv`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/trajectory_trace_plot.png`
  - contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/contact_sheet_firstusable.png`
  - video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910/videos/refmix-hold-a10-video480-step-0.mp4`
  - consistency: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/train_eval_consistency.json`
- viz_urls:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/report.md`
  - plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/trajectory_trace_plot.png`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/contact_sheet_firstusable.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910/videos/refmix-hold-a10-video480-step-0.mp4`

Analysis:
- This run is a useful negative diagnostic, not a success. The hold code and artifact cadence are wired, and alpha `1.0` still has zero pre-hold reference error, but the hold trigger fired from the loose contact-distance condition at about step `123` / phase `0.256`, before the reference gripper schedule began closing. It therefore froze a hover pose and closed the hand with no cube in the grasp.
- Compared with the earlier alpha `1.0` refmix sweep, the previous transient lift occurred much later: lift began around step `320` / phase `0.667`, max lift `0.102 m` occurred around step `389` / phase `0.810`, and the gripper width remained around `0.048-0.055 m`. The early contact-distance trigger in this first hold run prevents reaching that regime.
- The next bounded test should delay hold until after actual lift or late phase, and use the reference schedule closed-gripper action rather than full overclose. This tests terminal stabilization without the early-hover failure mode.

Next:
- Launch one more bounded eval-only delayed-hold job from the same pushed code: `policy_reference_mix_hold`, alpha `1.0`, `HOLD_CONTACT_MAX_FINGER_DIST=0.0` to effectively disable the loose contact trigger, `HOLD_PHASE_START=0.67`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, and `HOLD_GRIPPER_ACTION=-0.4` to match the compact reference minimum gripper schedule. Produce the same video/report/plot/contact-sheet bundle. No PPO scale-up.

## 2026-06-11T15:55:08-07:00 - delayed strict terminal hold plan

Goal:
- Run exactly one bounded delayed-hold eval that avoids the early-hover failure from job `1027825`.

Hypothesis:
- The previous alpha `1.0` refmix run lifted only after the gripper began closing and the reference reached the late lift regime: lift started around step `320` / phase `0.667`, max lift `0.102 m` occurred around step `389` / phase `0.810`, and success transiently reached `0.75`. If terminal hold starts only after actual lift (`cube_lift_height >= 0.02 m`) or the same late phase window, and the gripper command matches the reference minimum (`-0.4`, not full overclose), hold may preserve final lift/success. If it still fails, the issue is not only early trigger timing; it likely needs grasp/hold target geometry or a task-space/object-relative hold controller rather than direct EE hover hold.

Change:
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` patched so `train_eval_consistency.json` separates real env-config mismatches, missing train/eval keys, and expected eval-only overrides (`action_source`, `reference_mix_alpha`, `hold_config`, checkpoint, video, deterministic settings). This prevents eval-only hold settings from being mistaken for train/eval env drift.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/eval_rollout.py` passed.
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- `git diff --check` passed.
- Regenerated `1027825` summary with the train env YAML; consistency now reports `status=passed`, `mismatches=[]`, and expected eval-only overrides separately.

Planned Job:
- `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=1.0`, `HOLD_CONTACT_MAX_FINGER_DIST=0.0`, `HOLD_PHASE_START=0.67`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_LIFT_HEIGHT=0.10`, `HOLD_GRIPPER_ACTION=-0.4`, `NUM_ENVS=4`, `NUM_STEPS=480`, same checkpoint/reference/config/seed as `1027825`.

Acceptance:
- Fetch and inspect mp4, contact sheet, `metrics.json`, trace CSV/JSONL, summary JSON/CSV, trace plot, report, and consistency JSON.
- Required pass condition for this diagnostic: no target-safety regression, no reset pathology, hold activates after late phase or lift/success rather than early contact-distance alone, and final lift/success improves over `1027825`. If final lift/success remains zero, do not train; debug hold target/action geometry next.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `0210951c42d31237e98f617254b4c8666096e527`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `0210951c42d31237e98f617254b4c8666096e527`.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_hold_late --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=refmix-hold-late-a10-video480,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=1.0,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.10,HOLD_GRIPPER_ACTION=-0.4,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027845`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027845.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refmix-hold-late-a10-video480-step-0.mp4`, local summary/report/plot/contact sheet after fetch.

Result:
- status: completed `0:0` in `00:01:26` on `pool0-00004`; fetched locally, summarized, and visually inspected by orchestrator and B.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508_artifacts`
- video validation: `1280x720`, `479` frames, `7.983333 s`, `60/1` FPS.
- metrics: `num_steps_completed=480`, `done_count=0`, `reward_mean/final=4.3530/6.1762`, `success_rate_mean/final=0/0`, `cube_lift_height_max=0.062284 m`, `cube_lift_height_final=0.062284 m`, `target_unsafe_rate_max=0`, `target_clearance_min=0.065114 m`.
- hold metrics: `hold_active_rate_mean/final=0.3375/1.0`; trigger step mean `319.0`; trigger was actual lift (`hold_lift_trigger_rate_mean=0.3375`, phase/success/contact triggers `0`); `mixed_reference_action_error_l2_mean=0.0`; `applied_reference_action_error_l2_mean=0.2757`.
- behavior metrics: final EE-to-cube `0.058844 m`, final finger-center-to-cube `0.100829 m`, final gripper width `0.047560 m`; final success still `0`.
- consistency artifact: `train_eval_consistency.json` status `passed`; real mismatches, missing train keys, and missing eval keys are empty; expected eval-only overrides include action source, alpha, hold config, checkpoint, deterministic/video settings, and requested step count.
- visual diagnosis: cube is lifted/perturbed around the middle/lift-trigger region, but by final frame the grasp is not held and success remains zero. The strict delayed trigger fixed the early-hover failure from `1027825`, but the frozen `cube_pos_at_trigger + lift` target likely pulls the gripper off the actual grasp frame.
- viz_urls:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508_artifacts/report.md`
  - plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508_artifacts/trajectory_trace_plot.png`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508/contact_sheet_quick.jpg`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_late_a10_video480_20260611_155508/videos/refmix-hold-late-a10-video480-step-0.mp4`

Analysis:
- This is partial physical improvement, not success and not a PPO scale-up gate. The job demonstrates that a lift-triggered hold can preserve some final lift (`0.062 m`) without target-safety regression, but it does not stabilize the cube to task success.
- The next hypothesis to test is whether the hold target is wrong. At lift trigger, the current EE pose/object offset is the actual grasp frame that produced lift; replacing it with `cube_pos_at_trigger + [0, 0, hold_lift_height]` may change the contact geometry enough to drop the cube.

Next:
- Implement a single eval-only target-policy option that stores the trigger-frame EE-minus-cube offset and holds `cube_current_pos + stored_offset + vertical_bias`, keeping the gripper command at `-0.4`. Launch one 480-step video/report bundle with the same alpha `1.0` checkpoint/reference config. No PPO scale-up.

## 2026-06-11T16:00:19-07:00 - trigger-frame offset hold plan

Goal:
- Test whether preserving the actual grasp frame at first lift trigger sustains final lift/success better than the previous cube-plus-height terminal hold.

Hypothesis:
- If `cube_pos_at_trigger + [0, 0, hold_lift_height]` pulled the gripper away from the contact geometry, then holding the current trigger-frame EE-minus-cube offset while adding only a small vertical bias should preserve contact better. If this also drops the cube, the reference grasp is not stable under the current Franka gripper/contact geometry, and B should pivot to approach/pregrasp/grasp action/reference loss plus RL stabilization rather than full-trajectory hold.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add a `--hold_target_policy` argument while preserving the existing default policy. Add a new eval-only policy that stores `ee_pos_at_trigger - cube_pos_at_trigger` and tracks `cube_current_pos + stored_offset + hold_lift_height*z` after hold activation. Log the selected hold target policy and stored offset metrics.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: export/echo/pass `HOLD_TARGET_POLICY`.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include hold target policy and offset/target diagnostics in `summary.json`, `report.md`, and plots if present.
- Worklog: record validation, exact commit/deploy state, job id, metrics, video/contact-sheet/report URLs, and the pass/fail interpretation.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- Commit/push and update the agent-owned l401 worktree to the exact commit via Git.

Planned Job:
- One l401 eval-only run: `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=1.0`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_CONTACT_MAX_FINGER_DIST=0.0`, `HOLD_PHASE_START=0.67`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_LIFT_HEIGHT=0.03` vertical bias above the trigger offset, `HOLD_GRIPPER_ACTION=-0.4`, `NUM_ENVS=4`, `NUM_STEPS=480`, same checkpoint/reference/seed as `1027845`.

Acceptance:
- Produce and fetch `metrics.json`, trace CSV/JSONL, mp4, contact sheet, summary JSON/CSV, trace plot, report, consistency JSON, and `viz-open` URLs.
- Target unsafe remains `0`; consistency report keeps expected eval overrides separate from real mismatches; hold triggers from actual lift/late phase rather than contact-distance; final lift/success and visual hold are compared directly to `1027845`.

Implementation Checkpoint:
- `eval_rollout.py` now supports `--hold_target_policy={cube_trigger_plus_lift,cube_current_plus_trigger_ee_offset}`. The default preserves the prior static cube-plus-lift behavior; the new opt-in policy stores `ee_pos - cube_pos` at first hold trigger and tracks `cube_current_pos + stored_offset + hold_lift_height*z`.
- `eval_rollout.py` logs `hold_target_policy_id` and trigger-frame EE-cube offset components so the trace/report can confirm the selected target route.
- `sbatch_eval_franka_cube_grasp_1gpu.sh` exports, echoes, and passes `HOLD_TARGET_POLICY`.
- `summarize_traj_tracking_eval_artifacts.py` includes hold target policy and trigger offset diagnostics in `summary.json`/`summary.csv`/`report.md`.
- validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- validation: `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- validation: `git diff --check` passed.
- validation: summarizer regression on `1027845` metrics wrote `/tmp/traj_hold_offset_summary_regression/{report.md,summary.json,train_eval_consistency.json,trajectory_trace_plot.png}` and preserved old metrics while showing new offset fields as `n/a` for old artifacts.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `0a8cf038bae6a12b26ff94cb6dc837c5c98da06d`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `0a8cf038bae6a12b26ff94cb6dc837c5c98da06d`. First remote fetch via `git@github.com` failed with public-key auth; retry used one-shot HTTPS fetch without changing persistent remote config.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_hold_offset --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358,NUM_ENVS=4,NUM_STEPS=480,VIDEO_LENGTH=480,VIDEO_NAME_PREFIX=refmix-hold-offset-a10-video480,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=1.0,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027851`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027851.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refmix-hold-offset-a10-video480-step-0.mp4`, local summary/report/plot/contact sheet after fetch.

Launch Status:
- submitted to l401 as eval-only diagnostic. Awaiting completion and artifact inspection.

## 2026-06-11T16:12:00-07:00 - current 1027851 acknowledgement and next launch state

Status:
- Acknowledged orchestrator diagnosis: job `1027851` is a transient-success/reset-semantics artifact, not a simple drift failure.
- Key evidence from fetched artifacts: `done_count=3`, `success_rate_max=0.75` around steps `363-373`, `cube_lift_height_max=0.108942 m`, target unsafe `0`, target clearance min `0.065114 m`, and final success/lift reset to `0` after env resets/drop.
- Local artifacts updated with explicit addendum and success-window views:
  - report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/report.md`
  - full video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358/videos/refmix-hold-offset-a10-video480-step-0.mp4`
  - full contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/contact_sheet_first_mid_lift_final.jpg`
  - success-window slow video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_slow_step300_380.mp4`
  - success-window contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_contact_sheet.jpg`
  - trace plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/trajectory_trace_plot.png`
  - consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/train_eval_consistency.json`
- Current implementation patch adds per-env eval semantics for the next run: `success_ever`, first/last success step summaries, done-ever/done-after-success, per-step done rates, and first-done event records with pre-auto-reset reason snapshots.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- `git diff --check` passed.

Next:
- Commit/push/deploy this instrumentation patch, then launch exactly one bounded success-window eval with the same offset-hold config as `1027851` but `NUM_STEPS=390` / `VIDEO_LENGTH=390`. No PPO scale-up.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `f8aa20b7b413394554999f16706c36c39ed471f6`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `f8aa20b7b413394554999f16706c36c39ed471f6`.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_hold_successwin --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503,NUM_ENVS=4,NUM_STEPS=390,VIDEO_LENGTH=390,VIDEO_NAME_PREFIX=refmix-hold-offset-successwin390,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=1.0,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027856`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027856.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refmix-hold-offset-successwin390-step-0.mp4`, local summary/report/plot/contact sheet after fetch.

Launch Status:
- submitted to l401 as eval-only success-window diagnostic. Awaiting completion and artifact inspection.

Result:
- status: completed `0:0` in `00:02:39` on `pool0-00032`; fetched locally and summarized.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts`
- stdout_log: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/slurm_eval_franka_cube_1027856.out`
- video validation: `1280x720`, `389` frames, `6.483333 s`, `60/1` FPS. The first encoded frame is black, so the contact sheet uses frame 30 as first usable.
- metrics: `num_steps_completed=390`, `done_count=3`, `reward_mean/final=4.3246/2.1124`, `success_rate_mean/final/max=0.0250/0.0/0.75`, `success_ever_count/rate=3/0.75`, `success_rate_last_window_mean=0.0975`, `cube_lift_height_max=0.108942 m`, `target_unsafe_rate_max=0`, `target_clearance_min=0.065114 m`.
- hold metrics: `hold_active_rate_mean/final=0.1551/0.25`; trigger step mean `319.0`; trigger came from actual lift only (`hold_lift_trigger_rate_mean=0.1551`, phase/success/contact trigger rates `0`); hold target policy `cube_current_plus_trigger_ee_offset`; final trigger offset `x/y/z=-0.000152/0.000365/0.009102 m`.
- done semantics: first success step count `3`, mean `362.67`, min/max `362/363`; last success step count `3`, mean `374.67`; first done step count `3`, mean `374.67`; `done_after_success_count/rate=3/0.75`; done reason counts `success_done=3`, all other reasons `0`. This directly answers the reset-semantics question: the offset-hold succeeds in three envs and then resets by task success, so final success/lift of zero is post-reset state, not absence of success.
- behavior metrics: final EE-to-cube `0.1625 m`, finger-center-to-cube `0.1795 m`, gripper width `0.0658 m`; final visual frame is post-reset. The success-window contact sheet shows approach, lift trigger, first success, success-done, and final post-reset frames. The camera angle makes vertical lift clearer in the trace plot than in still frames.
- consistency artifact: `train_eval_consistency.json` status `passed`; real mismatches, missing train keys, and missing eval keys are empty; expected eval-only overrides include action source, alpha, hold config, checkpoint, deterministic/video settings, and requested step count.
- reference caveat remains explicit in report and metrics: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`.
- artifact files:
  - report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/trajectory_trace_plot.png`
  - full video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/videos/refmix-hold-offset-successwin390-step-0.mp4`
  - slow success-window video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/success_window_slow_step300_389.mp4`
  - success-window contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/success_window_contact_sheet.jpg`
  - metrics: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/metrics.json`
  - trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/trace.jsonl`
  - summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/summary.csv`
  - consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/train_eval_consistency.json`
  - video metadata: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/video_metadata.json`
  - manifest: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/artifact_manifest.json`
- viz_urls:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/report.md`
  - plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/trajectory_trace_plot.png`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/success_window_contact_sheet.jpg`
  - full video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/videos/refmix-hold-offset-successwin390-step-0.mp4`
  - slow success-window video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/success_window_slow_step300_389.mp4`

Analysis:
- The terminal offset-hold diagnostic is now mechanically viable for the policy-free/reference-action path: alpha `1.0` plus trigger-frame EE-cube offset hold reaches task success in three of four envs without target-safety regression.
- The prior `1027851` final-zero ambiguity is resolved. Final state is not a good sole metric for this diagnostic because auto-reset hides the success window; `success_ever`, first/last success steps, and done reasons are required for future short eval reports.
- This does not justify PPO scale-up by itself. It shows reference/action feasibility and a plausible terminal stabilization target, while the learned PPO checkpoint still does not imitate the required action profile without heavy reference injection.

Next:
- Do not scale PPO. The next bounded development step should make this terminal-stabilization route trainable/interpretable: either add a training/eval metric that reports success-ever/done reason windows for RL smokes by default, or run one small eval-only curriculum diagnostic that blends learned actions until the offset-hold trigger and then hands off to the stable hold target. Any next run must include the same artifact bundle and viewer URLs.

## 2026-06-11T16:29:02-07:00 - no-auto-reset stabilization diagnostic plan

Goal:
- Determine whether the reference/offset-hold controller keeps the cube stable after first success when the env does not immediately auto-reset on `success_done`.
- Make the existing success-window artifact easier to parse by emitting a dedicated success/done diagnostics JSON/CSV and a focused success-window trace CSV.

Hypothesis:
- If the offset-hold controller can keep success/lift after the first success when success termination is suppressed, then the current final-zero issue is purely task auto-reset semantics and this terminal-hold target is physically stable enough to train toward.
- If success is reached and then lost without reset, the remaining issue is post-success hold/contact stability under the reference/hold controller, not just PPO policy weakness.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add an eval-only `--suppress_success_termination` flag. It will mask only `success_done` out of the environment termination signal by monkeypatching the instantiated eval env, while the metrics still record hypothetical success-done events from a pre-step snapshot. This does not change baseline task code.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: pass `SUPPRESS_SUCCESS_TERMINATION` through the wrapper and echo it in logs.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: write `success_diagnostics.json`, `success_diagnostics.csv`, and `success_window_trace.csv` with success-ever, done-after-success, hold trigger, lift, EE/finger distances, gripper width/action, target safety, and done-reason fields.
- Worklog: record validation, exact commit/deploy state, job id, artifacts, and pass/fail interpretation.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- Regenerate artifacts for `1027856` to verify the new success diagnostics outputs are written.
- `git diff --check`
- Commit/push and update the agent-owned l401 worktree to the exact commit via Git.

Planned Job:
- One l401 eval-only run with the same offset-hold config as `1027856`, plus `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, `NUM_ENVS=4`, `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=1.0`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_CONTACT_MAX_FINGER_DIST=0.0`, `HOLD_PHASE_START=0.67`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_LIFT_HEIGHT=0.03`, `HOLD_GRIPPER_ACTION=-0.4`, same seed/checkpoint/reference.

Acceptance:
- Fetch and inspect mp4, success-window contact sheet, slow success/loss window video, `metrics.json`, trace CSV/JSONL, summary JSON/CSV, success diagnostics JSON/CSV/window trace, trace plot, report, consistency JSON, stdout log, and `viz-open` URLs.
- Target unsafe remains `0`; no reset occurs due to success termination; report whether success/lift persist after first success or drop under the controller. No PPO scale-up.

Implementation Checkpoint:
- `eval_rollout.py` now supports eval-only `--suppress_success_termination`. The instantiated eval env masks `success_done` out of termination while preserving other done reasons; metrics record `suppressed_success_done_count/rate` and first suppressed success-done step.
- `sbatch_eval_franka_cube_grasp_1gpu.sh` now echoes and passes `SUPPRESS_SUCCESS_TERMINATION`.
- `summarize_traj_tracking_eval_artifacts.py` now emits `success_diagnostics.json`, `success_diagnostics.csv`, and `success_window_trace.csv`, and includes success-suppression fields in the report.
- Regenerated the existing `1027856` local artifact summary; new files exist under `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- `git diff --check` passed.
- Existing `1027856` success diagnostics parse expected fields: `success_ever_count=3`, `success_rate_max=0.75`, `done_after_success_count=3`, `done_reason_counts.success_done=3`, `hold_trigger_step_mean=319.0`, `cube_lift_height_max=0.108942`, `target_unsafe_rate_max=0`.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `26b5476a6c06f63a39390e8f003a9be68d40d2ef`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `26b5476a6c06f63a39390e8f003a9be68d40d2ef`.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=refmix_hold_noreset --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=refmix-hold-offset-noreset520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=1.0,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027866`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027866.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/refmix-hold-offset-noreset520-step-0.mp4`, local summary/report/plot/contact sheet/success diagnostics after fetch.

Launch Status:
- submitted to l401 as eval-only no-success-auto-reset stabilization diagnostic. Awaiting completion and artifact inspection.

Result:
- status: completed `0:0` in `00:01:31` on `pool0-00016`; fetched locally, summarized, and visually inspected.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts`
- stdout_log: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/slurm_eval_franka_cube_1027866.out`
- video validation: `1280x720`, `520` frames, `8.666667 s`, `60/1` FPS.
- metrics: `num_steps_completed=520`, `done_count=0`, `reward_mean/final=8.8291/16.2509`, `success_rate_mean/final/max=0.2255/0.5/0.75`, `success_ever_count/rate=3/0.75`, `success_rate_last_window_mean=0.735`, `suppressed_success_done_count/rate=3/0.75`, first suppressed success-done step mean `374.67`, `cube_lift_height_max/final=0.220861/0.220861 m`, final EE-to-cube `0.0439 m`, final finger-center-to-cube `0.0861 m`, target unsafe max `0`.
- done semantics: success termination suppression installed and active; no actual done/reset events; all done reason counts are zero. This confirms the final-zero result in the normal eval was auto-reset semantics, not loss of hold at the success window.
- visual diagnosis: contact sheet and trace show stable reference/offset hold through the rollout tail. Success remains nonzero at final step (`0.5`) with high lift; one previously successful env appears to leave the strict success region by the end, but the object remains lifted and close to the end effector in aggregate.
- reference caveat remains explicit in report/metrics: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`.
- artifact files:
  - report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/trajectory_trace_plot.png`
  - full video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/videos/refmix-hold-offset-noreset520-step-0.mp4`
  - slow success/hold video: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/noreset_success_hold_slow_step300_519.mp4`
  - contact sheet: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/noreset_success_hold_contact_sheet.jpg`
  - metrics: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/metrics.json`
  - trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/trace.jsonl`
  - success diagnostics: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/success_diagnostics.json`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/success_diagnostics.csv`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/success_window_trace.csv`
  - summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/summary.csv`
  - consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/train_eval_consistency.json`
  - video metadata: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/video_metadata.json`
  - manifest: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/artifact_manifest.json`
- viz_urls:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/report.md`
  - plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/trajectory_trace_plot.png`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/noreset_success_hold_contact_sheet.jpg`
  - full video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/videos/refmix-hold-offset-noreset520-step-0.mp4`
  - slow success/hold video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/noreset_success_hold_slow_step300_519.mp4`
  - success diagnostics JSON: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/success_diagnostics.json`

Analysis:
- The reference/offset-hold controller is stable enough to sustain lift after the success window when success auto-reset is disabled. The transition from transient success to final reset/drop in `1027851`/`1027856` is primarily task termination semantics, not a controller inability to hold.
- The remaining trainability problem is upstream: the learned PPO checkpoint does not reliably produce approach/close/up actions before the terminal hold. The stable hold target gives a useful curriculum/handoff target, but PPO should not scale until a small learned-prefix handoff eval shows non-drifting behavior or a training diagnostic proves the policy can reach the handoff trigger.

Next:
- Bounded trainability diagnostic, no PPO scale-up: run a learned-prefix handoff eval using the same stable hold machinery but with `REFERENCE_MIX_ALPHA=0.0` before hold, `SUPPRESS_SUCCESS_TERMINATION=True`, and a phase fallback trigger. This tests whether the current learned policy can reach a usable handoff state before the controller takes over, while producing the same video/trace/report/success-diagnostics bundle.

## 2026-06-11T16:40:00-07:00 - learned-prefix handoff diagnostic plan

Goal:
- Test the minimal handoff/curriculum idea requested by orchestrator: use learned checkpoint actions before the terminal hold trigger, then switch to the stable offset-hold target and keep success-window metrics visible.

Hypothesis:
- If learned-prefix actions approach the cube well enough before the phase/lift trigger, the stable hold target should recover some lift/success. If it fails, this confirms the next training work should improve approach/pregrasp action imitation/rewards before any longer PPO.

Planned Job:
- Eval-only l401 run, no code changes: `ACTION_SOURCE=policy_reference_mix_hold`, `REFERENCE_MIX_ALPHA=0.0`, `SUPPRESS_SUCCESS_TERMINATION=True`, same stable hold config as `1027866`, `NUM_ENVS=4`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, same checkpoint/reference/seed.

Acceptance:
- Full artifact bundle: mp4, contact sheet, slow handoff window video, `metrics.json`, trace CSV/JSONL, summary JSON/CSV, success diagnostics JSON/CSV/window trace, trace plot, report, consistency JSON, stdout log, and `viz-open` URLs.
- Target unsafe remains `0`; report whether learned-prefix handoff reaches lift/success or simply holds in free space. No PPO scale-up.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `20444260437fde3fefc6eb8af623a48fb37bd9a1`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `20444260437fde3fefc6eb8af623a48fb37bd9a1`.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=learned_prefix_hold --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=learned-prefix-hold-noreset520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=0.0,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027870`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027870.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/learned-prefix-hold-noreset520-step-0.mp4`, local summary/report/plot/contact sheet/success diagnostics after fetch.

Launch Status:
- submitted to l401 as eval-only learned-prefix handoff diagnostic. Awaiting completion and artifact inspection.

Result:
- status: completed `0:0` in `00:01:38` on `pool0-00015`; fetched locally, summarized, and visually inspected.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts`
- stdout_log: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/slurm_eval_franka_cube_1027870.out`
- video validation: `1280x720`, `520` frames, `8.666667 s`, `60/1` FPS.
- metrics: `num_steps_completed=520`, `done_count=0`, `reward_mean/final=1.6404/1.5443`, `success_rate_mean/final/max=0/0/0`, `success_ever_count/rate=0/0`, `suppressed_success_done_count/rate=0/0`, `cube_lift_height_max=0.001512 m`, final EE-to-cube `0.5066 m`, final finger-center-to-cube `0.4771 m`, target unsafe max `0`.
- action diagnostics: raw learned close/up means `0.0445/0.1454` versus reference-delta close/up means `0.2218/0.4453`; policy-reference L2 mean `2.1153`. Close/lift reward means are both `0`.
- hold diagnostics: hold became active by phase fallback at step `323` (`hold_active_rate_final=1.0`) with no lift/success/contact trigger; trigger EE-cube offset was large (`x/y/z=-0.105/-0.153/0.273 m`), so the terminal hold stabilized free space instead of a grasp.
- visual diagnosis: the labeled contact sheet shows an early near approach, then the learned prefix moves away; after the phase-triggered hold the hand remains away from the cube through the final frame.
- reference caveat remains explicit in report/metrics: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`.
- artifact files:
  - report: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/trajectory_trace_plot.png`
  - full video: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/videos/learned-prefix-hold-noreset520-step-0.mp4`
  - slow handoff video: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/learned_prefix_handoff_slow_step80_519.mp4`
  - labeled contact sheet: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/learned_prefix_handoff_contact_sheet.jpg`
  - quick contact sheet from summarizer: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/contact_sheet_quick.jpg`
  - metrics: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/metrics.json`
  - trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/trace.jsonl`
  - success diagnostics: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/success_diagnostics.json`, `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/success_diagnostics.csv`, `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/success_window_trace.csv`
  - summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/summary.csv`
  - consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/train_eval_consistency.json`
  - video metadata: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/video_metadata.json`
  - manifest: `cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/artifact_manifest.json`
- viz_urls:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/report.md`
  - plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/trajectory_trace_plot.png`
  - labeled contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/learned_prefix_handoff_contact_sheet.jpg`
  - full video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724/videos/learned-prefix-hold-noreset520-step-0.mp4`
  - slow handoff video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/learned_prefix_handoff_slow_step80_519.mp4`
  - success diagnostics JSON: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/success_diagnostics.json`

Analysis:
- This is a clear learned-policy prefix failure, not a terminal hold failure. `1027866` proves the same hold can sustain lift when the prefix/reference reaches a valid grasp; `1027870` shows the five-epoch PPO policy moves away before the handoff and never reaches lift/success.
- The next bounded question is quantitative: how much reference blending is required before the stable hold becomes viable? If only alpha `1.0` works, the trainable path should be approach/action imitation or teacher-forced reference mixing before terminal hold, not longer PPO with the current reward.

Next:
- Run eval-only no-reset stable-hold alpha sweep for `REFERENCE_MIX_ALPHA=0.25,0.50,0.75` using the same checkpoint/reference/seed and artifact bundle. Acceptance: identify the lowest alpha that reaches lift/success while keeping target unsafe max `0`; no PPO scale-up.

## 2026-06-11T16:58:00-07:00 - no-reset hold alpha sweep plan

Goal:
- Quantify how much reference_delta blending is needed before the stable offset-hold target becomes viable after the learned action-alignment checkpoint.

Hypothesis:
- Intermediate blend values may recover the approach/handoff that pure learned policy misses. If alpha `0.25/0.50/0.75` still fail and only the earlier alpha `1.0` succeeds, then the immediate training task is stronger approach/action imitation or a teacher-forced curriculum before PPO scale-up.

Planned Jobs:
- Eval-only l401 runs, no source changes: `ACTION_SOURCE=policy_reference_mix_hold`, `SUPPRESS_SUCCESS_TERMINATION=True`, stable hold config from `1027866`, `NUM_ENVS=4`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, same checkpoint/reference/seed, `REFERENCE_MIX_ALPHA in {0.25,0.50,0.75}`.

Acceptance:
- Per-run artifact bundle: mp4, labeled contact sheet, slow handoff video, `metrics.json`, trace CSV/JSONL, summary JSON/CSV, success diagnostics JSON/CSV/window trace, trace plot, report, consistency JSON, stdout log, `viz-open` URLs.
- Sweep result table answers lowest viable alpha for lift/success and confirms target unsafe remains `0`. No PPO scale-up.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_commit: `5d7bd12b4e363bcde0b67d910f5770e9a407f058`
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `5d7bd12b4e363bcde0b67d910f5770e9a407f058`.
- changed_files: worklog only

Command / Jobs:
- alpha `0.25`: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=hold_nr_a025 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=refmix-hold-noreset-a025-520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy_reference_mix_hold,REFERENCE_MIX_ALPHA=0.25,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_PHASE_START=0.67,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_CONTACT_MAX_FINGER_DIST=0.0,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=1.5,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- alpha `0.50`: same command with `RUN_NAME=franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421`, `VIDEO_NAME_PREFIX=refmix-hold-noreset-a050-520`, `REFERENCE_MIX_ALPHA=0.50`, `--job-name=hold_nr_a050`.
- alpha `0.75`: same command with `RUN_NAME=franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421`, `VIDEO_NAME_PREFIX=refmix-hold-noreset-a075-520`, `REFERENCE_MIX_ALPHA=0.75`, `--job-name=hold_nr_a075`.
- job_ids: alpha `0.25` -> `1027886`, alpha `0.50` -> `1027887`, alpha `0.75` -> `1027888`
- run_dirs:
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421`
- logs:
  - `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027886.out`
  - `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027887.out`
  - `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027888.out`

Launch Status:
- submitted to l401. Initial `squeue`: all three jobs pending behind other batch work. Awaiting completion and artifact inspection.

Result:
- status: all three sweep jobs completed `0:0`.
  - alpha `0.25` / job `1027886`: `COMPLETED`, elapsed `00:01:30`, node `pool0-00037`
  - alpha `0.50` / job `1027887`: `COMPLETED`, elapsed `00:02:46`, node `pool0-00037`
  - alpha `0.75` / job `1027888`: `COMPLETED`, elapsed `00:01:30`, node `pool0-00004`
- local run dirs:
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421`
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421`
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421`
- local artifact dirs:
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421_artifacts`
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421_artifacts`
  - `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421_artifacts`
  - combined: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts`
- video validation: all three videos are `1280x720`, `520` frames, `8.666667 s`, `60/1` FPS.

Metrics:

| Alpha | Job | success_ever | success max/final | suppressed_success_done | max lift m | final EE-cube m | final finger-cube m | target unsafe max | mixed-ref L2 | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 1027870 | 0 | 0.000/0.000 | 0 | 0.001512 | 0.5066 | 0.4771 | 0.000 | 2.1153 | learned-prefix failed handoff |
| 0.25 | 1027886 | 0 | 0.000/0.000 | 0 | 0.000000 | 0.3344 | 0.3020 | 0.000 | 1.5144 | failed handoff |
| 0.50 | 1027887 | 0 | 0.000/0.000 | 0 | 0.000000 | 0.1119 | 0.1298 | 0.000 | 0.7197 | close but no lift |
| 0.75 | 1027888 | 0 | 0.000/0.000 | 0 | 0.000000 | 0.1006 | 0.1352 | 0.000 | 0.2885 | close but no lift |
| 1.00 | 1027866 | 3 | 0.750/0.500 | 3 | 0.220861 | 0.0439 | 0.0861 | 0.000 | 0.0000 | viable reference-dominant hold |

Artifact files:
- combined report: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/report.md`
- combined plot: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/alpha_sweep_plot.png`
- combined summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/alpha_sweep_summary.json`, `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/alpha_sweep_summary.csv`
- alpha `0.25`: report `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421_artifacts/report.md`, plot `.../trajectory_trace_plot.png`, contact sheet `.../refmix_hold_noreset_a025_contact_sheet.jpg`, slow video `.../refmix_hold_noreset_a025_slow_step80_519.mp4`, full video `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421/videos/refmix-hold-noreset-a025-520-step-0.mp4`, metrics/trace under the local run dir.
- alpha `0.50`: report `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421_artifacts/report.md`, plot `.../trajectory_trace_plot.png`, contact sheet `.../refmix_hold_noreset_a050_contact_sheet.jpg`, slow video `.../refmix_hold_noreset_a050_slow_step80_519.mp4`, full video `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421/videos/refmix-hold-noreset-a050-520-step-0.mp4`, metrics/trace under the local run dir.
- alpha `0.75`: report `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421_artifacts/report.md`, plot `.../trajectory_trace_plot.png`, contact sheet `.../refmix_hold_noreset_a075_contact_sheet.jpg`, slow video `.../refmix_hold_noreset_a075_slow_step80_519.mp4`, full video `cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421/videos/refmix-hold-noreset-a075-520-step-0.mp4`, metrics/trace under the local run dir.

viz_urls:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/report.md`
- combined plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/alpha_sweep_plot.png`
- alpha `0.25` contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421_artifacts/refmix_hold_noreset_a025_contact_sheet.jpg`
- alpha `0.25` video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a025_520_20260611_164421/videos/refmix-hold-noreset-a025-520-step-0.mp4`
- alpha `0.50` contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421_artifacts/refmix_hold_noreset_a050_contact_sheet.jpg`
- alpha `0.50` video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a050_520_20260611_164421/videos/refmix-hold-noreset-a050-520-step-0.mp4`
- alpha `0.75` contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421_artifacts/refmix_hold_noreset_a075_contact_sheet.jpg`
- alpha `0.75` video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421/videos/refmix-hold-noreset-a075-520-step-0.mp4`
- alpha `0.75` slow video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_a075_520_20260611_164421_artifacts/refmix_hold_noreset_a075_slow_step80_519.mp4`

Analysis:
- The alpha sweep answers the handoff threshold question: `0.25`, `0.50`, and `0.75` all preserve target safety but never produce lift/success. `0.50` and `0.75` approach the cube and reduce the mixed-reference error substantially, but they still trigger terminal hold by phase fallback rather than by lift/success. The hold then keeps the gripper near but not grasping the cube.
- Only the reference-dominant alpha `1.0` no-reset run (`1027866`) is currently viable, with `success_ever=3/4`, suppressed success done `3/4`, max lift `0.220861 m`, and final success `0.5`.
- This narrows the trainability issue to the approach/pregrasp/closure action profile. The next B training-oriented diagnostic should be stronger action imitation / teacher-forced reference mixing through approach-pregrasp-grasp, or BC-style supervised pretraining from `reference_delta` actions, before trying longer PPO. The reference caveat remains unchanged: `curobo_validated=false`.

Next:
- Do not scale PPO from the current action-alignment checkpoint. Prepare a bounded curriculum/BC diagnostic: keep phase/reference observations disabled for apple-to-apple clarity unless explicitly documented, use fixed-window rollout metrics, and evaluate with videos after a tiny smoke. Candidate least-invasive next patch: add a configurable training-time reference-action imitation term or scripted teacher-forcing probability for the approach/pregrasp phase only, then run env smoke plus tiny PPO/eval; do not run a long job until the short eval video shows actual contact/lift.

## 2026-06-11T17:14:00-07:00 - teacher-forced approach imitation diagnostic plan

Goal:
- Build the smallest artifact-backed trainability step after the alpha sweep: teach the PPO policy to match the `reference_delta` approach action under the actual Franka delta-IK controller instead of only rewarding imitation while the policy drifts.

Hypothesis:
- Prior action-alignment reward failed because the policy explored off-reference states and never learned the approach/closure profile. A bounded teacher-forced curriculum that applies `alpha * reference_delta + (1-alpha) * raw_policy_action` during approach/pregrasp, while computing imitation reward/error from the raw policy action, should keep rollouts on the successful reference manifold and provide a meaningful supervised-like signal. If this does not reduce raw policy-reference error or allow alpha below `1.0` in eval, the next blocker is action/obs normalization or reference phase/handoff conditions rather than PPO scale.

Planned Change:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`: add disabled-by-default teacher-forcing curriculum knobs: enable flag, alpha start/end, phase end, global-step anneal, raw-action imitation reward switch.
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`: override `_pre_physics_step` for the trajectory variant only. Store raw policy actions, reference actions, applied blended actions, teacher alpha, and action-error diagnostics. Use raw policy actions for action-alignment reward when teacher forcing is active so reward cannot be gamed by the applied blend.
- `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: expose the new flags as logged Hydra overrides.
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, and `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include teacher-force metrics in smoke/eval/report artifacts.

Validation Before Launch:
- `python3 -m py_compile` on edited Python files.
- `bash -n` on edited Slurm wrappers.
- `git diff --check`.
- Cluster env smoke only after commit/push/deploy: small `Dextrah-Franka-Cube-Grasp-Traj-Tracking` validation with teacher forcing enabled, no full training.

Planned Bounded Run Sequence:
1. Teacher-force env smoke: `NUM_ENVS=4`, short rollout, `alpha_start=1.0`, `alpha_end=1.0`, `phase_end=0.67`, same 60 mm unvalidated reference, action-alignment reward high enough to make raw-policy error visible. Acceptance: obs remains `[4,72]`, target unsafe `0`, teacher-force logs present/finite, applied-reference error near zero while raw-policy-reference error remains measurable, no reset pathology.
2. If smoke passes, tiny PPO smoke only, then eval videos at alpha `1.0` and a reduced alpha candidate. Acceptance: raw policy-reference error decreases and alpha can drop below `1.0` without losing contact/lift. No large PPO scale-up.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `9c79c59922f6ed9a68d03192ea4ba0897c71dcbf`
- changed_files: pending

## 2026-06-11T17:31:00-07:00 - teacher-forced approach imitation implementation checkpoint

Goal:
- Implement the disabled-by-default teacher-forced/action-imitation diagnostic and validate syntax/wrapper hygiene before l401 launch.

Change:
- Added trajectory-task-only teacher forcing knobs to `franka_cube_traj_tracking_env_cfg.py`.
- Added `DextrahFrankaCubeTrajTrackingEnv._pre_physics_step()` blending for `alpha * reference_delta + (1-alpha) * raw_policy_action`, with raw/reference/applied action buffers and teacher-alpha diagnostics.
- Changed trajectory action-alignment reward to compare against raw policy actions when configured, so teacher-forced applied actions cannot by themselves satisfy the imitation term.
- Added smoke/eval/report metrics for teacher alpha, raw-policy/reference action error, env-applied/reference action error, env-applied/raw-policy action error, raw close/up, and applied close/up.
- Exposed the flags through validation, eval, and PPO Slurm wrappers as logged overrides.

Version Control:
- agent_id: franka-cube-traj-tracking
- base_commit: `9c79c59922f6ed9a68d03192ea4ba0897c71dcbf`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`
  - `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
  - `dextrah_lab/rl_games/eval_rollout.py`
  - `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
  - `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
  - `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `cluster/sbatch_train_teacher_8gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` -> passed.
- `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh && bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh && bash -n cluster/sbatch_train_teacher_8gpu.sh` -> passed.
- `git diff --check` -> passed.

Next:
- Commit/push this implementation, deploy the exact commit to the l401 agent-owned worktree, and launch the bounded teacher-force env smoke only. No PPO launch until that smoke has finite logs/artifacts and target safety remains clean.

## 2026-06-11T17:02:49-07:00 - teacher-force env smoke launch

Goal:
- Validate the new teacher-forcing/action-imitation wiring in a real DEXTRAH/Isaac runtime before any PPO run.

Acceptance:
- Task registers as `Dextrah-Franka-Cube-Grasp-Traj-Tracking`; reset obs remains `[4,72]`.
- Rollout completes `240` steps with no early reset pathology and finite logs.
- New teacher-force/action-error logs are present: teacher alpha/active rate, raw-policy/reference L2, applied/reference L2, applied/raw L2, raw close/up, applied close/up.
- Target unsafe rate remains `0`; target clearance remains above the configured floor.
- Reference caveat remains explicit: compact reference is 60 mm retry, `curobo_validated=false`.

Version Control:
- agent_id: franka-cube-traj-tracking
- local_branch_head: `5c6e272bc8e5239f2d91d42396ff4b2d4202a00a`
- pushed: yes, `origin/codex/franka-cube-trajectory-tracking`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_commit/status: detached clean at `5c6e272bc8e5239f2d91d42396ff4b2d4202a00a`

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=tf_env_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249,NUM_ENVS=4,NUM_STEPS=240,VIDEO_LENGTH=240,CAPTURE_VIDEO=True,PRINT_INTERVAL=60,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=5.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=0.67,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh'`
- job_id: `1027895`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027895.out`
- expected artifacts: `metrics.json`, validation video under `videos/`, stdout log, local fetched report/contact sheet if the run completes.

Result:
- status: passed wiring/runtime smoke. Slurm `COMPLETED 0:0`, elapsed `00:01:05`, node `pool0-00030`.
- local run dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249`
- local artifact dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts`
- metrics: `passed=true`, `steps_completed=240`, `done_count=0`, `early_done_count=0`, `reward_mean=2.90757`, `reward_final=5.38198`, `final_success_rate=0`, `max_mean_lift=0.022727 m`, `final_gripper_width=0.048918 m`.
- observation contract: reset observation shape `[4,72]`.
- target safety: `tracking_unsafe_target_rate_max=0`, target clearance min `0.065114 m`.
- teacher/action diagnostics: `missing_logs=[]`, `tracking_teacher_force_alpha_mean=1.0`, `tracking_teacher_force_active_mean=1.0`, raw-policy/reference L2 `1.41593`, applied/reference L2 `0.026128`, applied/policy L2 `1.42461`, raw close/up `0.33125/0.16458`, applied close/up `0.01395/0.22098`.
- reference caveat: `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.
- video metadata: `1280x720`, `239` frames, `3.983333 s`, `60/1` FPS.
- visual diagnosis: contact sheet shows the reference-forced controller approaching and closing near the cube by the last frame; this 240-step validation does not demonstrate stable learned behavior or final success/lift and should only be treated as wiring evidence.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/report.md`
- plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/validation_trace_plot.png`
- contact sheet: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/video_contact_sheet.png`
- video: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249/videos/franka-cube-validate-step-0.mp4`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249/metrics.json`
- trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/validation_trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/validation_trace.jsonl`
- stdout log: `cluster_results/l401/slurm_logs/validate_franka_cube_1027895.out`

viz_urls:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/report.md`
- plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/validation_trace_plot.png`
- contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/video_contact_sheet.png`
- video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249/videos/franka-cube-validate-step-0.mp4`

Analysis:
- The env smoke validates the new diagnostic wiring: task registration, obs size, target safety, teacher-force action application, raw-policy action-error logging, and video artifact generation all work in Isaac runtime.
- The large raw-policy/reference error is expected because the validation actions are scripted zeros/close/up, not a trained policy. The applied/reference error being near zero confirms the env-level blend is actually applying reference_delta actions.
- This is not evidence that PPO learned the behavior. The next bounded step can be a tiny teacher-forced PPO smoke with high raw-action imitation reward, followed by short fixed/random eval videos. Do not scale training unless raw-policy/reference error decreases and reduced-alpha eval preserves approach/contact.

Implementation Follow-up:
- `summarize_franka_cube_validation_artifacts.py` was patched after this run to discover local MP4s next to fetched metrics and emit a real `video_contact_sheet.png`; earlier output incorrectly claimed no video even though the MP4 existed.

Next:
- Commit/push the summarizer fix plus this worklog result. Then deploy the exact branch head and launch one tiny teacher-forced PPO smoke only, with artifact cadence preserved.

## 2026-06-11T17:07:40-07:00 - tiny teacher-force PPO anneal smoke launch

Goal:
- Test whether PPO can quickly reduce raw-policy/reference action error when the env applies a reference-dominated teacher-force blend during approach/pregrasp.

Hypothesis:
- With `trajectory_tracking_teacher_force_enabled=True`, alpha annealed `1.0 -> 0.75`, phase end `0.67`, raw-policy comparison enabled, and stronger action-alignment reward, the policy gets an immediate action-dependent imitation signal while rollouts remain near the reference manifold. If raw-policy/reference error does not move after this tiny smoke/eval, the next blocker is likely observation/action normalization or reward wiring, not training scale.

Acceptance:
- This is wiring/trainability only; no long PPO and no success claim from checkpoint suffix.
- Training completes without traceback/NaN and writes checkpoints.
- Follow-up fixed/random eval videos from the epoch-5 checkpoint include teacher-force/action-error traces.
- Pass condition for proceeding beyond this diagnostic: eval raw-policy/reference L2 decreases versus validation baseline `1.416`, and at least alpha `1.0` plus one lower alpha shows approach/contact/lift without drift. Otherwise stop and debug.

Version Control:
- local_branch_head: `858402985719ec3ceb79db696a555443f976c997`
- pushed: yes
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_commit/status: detached clean at `858402985719ec3ceb79db696a555443f976c997`

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=tf_rl5 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_teacherforce_rl5_20260611_170740,NUM_ENVS=128,MAX_ITERATIONS=5,HORIZON_LENGTH=120,MINI_EPOCHS=4,MINIBATCH_SIZE=4096,CENTRAL_VALUE_MINIBATCH_SIZE=4096,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,REQUEUE_ON_EARLY_TERM=False,SAVE_FREQUENCY=1,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.75,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=0.67,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=600,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True cluster/sbatch_train_teacher_8gpu.sh'`
- job_id: `1027899`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5_20260611_170740`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027899.out`

Result:
- status: failed before PPO updates. Slurm `FAILED 1:0`, elapsed `00:00:51`, node `pool0-00037`.
- root cause: RL-Games assertion `assert(self.batch_size % self.minibatch_size == 0)`. With `NUM_ENVS=128` and `HORIZON_LENGTH=120`, batch size is `15360`; requested minibatch `4096` does not divide it.
- useful artifacts: params were written under the run dir, but no checkpoint or training curve was produced.

Next:
- Relaunch same bounded diagnostic with only minibatch sizes corrected to `3840` (`15360 / 3840 = 4`). Keep `MAX_ITERATIONS=5`, `NUM_ENVS=128`, `HORIZON_LENGTH=120`, teacher forcing, and action-alignment settings unchanged.

## 2026-06-11T17:09:13-07:00 - tiny teacher-force PPO anneal smoke relaunch

Goal:
- Rerun the same tiny teacher-force PPO diagnostic after fixing the RL-Games minibatch divisibility issue.

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=tf_rl5b --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913,NUM_ENVS=128,MAX_ITERATIONS=5,HORIZON_LENGTH=120,MINI_EPOCHS=4,MINIBATCH_SIZE=3840,CENTRAL_VALUE_MINIBATCH_SIZE=3840,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,REQUEUE_ON_EARLY_TERM=False,SAVE_FREQUENCY=1,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.75,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=0.67,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=600,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True cluster/sbatch_train_teacher_8gpu.sh'`
- job_id: `1027900`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027900.out`

Result:
- status: completed `0:0`, elapsed `00:01:05`, node `pool0-00030`.
- training startup: actor/critic `build mlp: 72`, observation size remained baseline `[72]`; no traceback/NaN in stdout.
- checkpoints written:
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_1_rew_18.131819.pth`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_2_rew_18.131819.pth`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_3_rew_18.131819.pth`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_4_rew_18.131819.pth`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth`
- interpretation: training smoke wiring passed. The epoch-5 reward suffix is finite/high but not a policy success signal; must inspect fixed rollout metrics/video next.

Next:
- Launch short `ACTION_SOURCE=policy` video evals from epoch-5 checkpoint with env teacher-force alpha fixed at `1.0` and `0.75`. Acceptance: raw-policy/reference L2 decreases versus validation baseline `1.416`, target unsafe remains `0`, and videos show approach/contact/lift rather than drift.

## 2026-06-11T17:11:00-07:00 - teacher-force PPO eval launch

Goal:
- Evaluate whether the tiny teacher-forced PPO checkpoint learned reference-like raw actions, first under full teacher application (`alpha=1.0`) and then under a reduced teacher blend (`alpha=0.75`).

Command / Jobs:
- alpha `1.0` command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=tf_eval_a100 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=tf-eval-a100-520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=0.67,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- alpha `0.75` command: same as above with `RUN_NAME=franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100`, `VIDEO_NAME_PREFIX=tf-eval-a075-520`, and `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=0.75`, `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.75`.
- job_ids: alpha `1.0` -> `1027902`; alpha `0.75` -> `1027901`
- run_dirs:
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100`
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100`

## 2026-06-11T17:33:00-07:00 - teacher-force eval artifact verdict and alpha-gate diagnosis

Goal:
- Close out the two teacher-force evals with inspectable artifacts and prevent confusion with the older `actionscale-rewinf` drift-away video.

Result:
- `1027902` / `franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100`: completed `0:0`, 520/520 steps, target unsafe max `0`, target clearance min `0.065114 m`, raw-policy/reference L2 mean/final `1.0188/1.1534` vs teacher-force env-smoke baseline `1.416`, applied/reference L2 mean `0.3483`, reward mean/final `7.8834/12.9059`, success ever/final/max `1/0.25/0.25`, max/final lift `0.059976/0.059976 m`, final EE-cube `0.09645 m`, final finger-center-cube `0.13766 m`, done count `2` with unclassified resets before success. Visual: approach and some lift signal in one env, but not robust; the sheet/video still end with the visible env away from the cube. This is partial teacher-assisted behavior, not learned handoff success.
- `1027901` / `franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100`: completed `0:0`, 520/520 steps, target unsafe max `0`, target clearance min `0.065114 m`, raw-policy/reference L2 mean/final `1.0464/1.5687`, applied/reference L2 mean `0.5988`, reward mean/final `7.7163/8.3491`, success/lift essentially zero (`success_ever=0`, max lift `0.000042 m`), final EE-cube `0.09681 m`, final finger-center-cube `0.12821 m`. Visual: reaches/contact-ish near the cube but does not lift and ends without grasp.
- Train/eval consistency reports pass after separating expected eval-only overrides from true mismatches. The fixed eval alpha values and zero anneal are now marked as intentional diagnostic overrides, not production train/eval mismatches.
- The old `actionscale-rewinf-diag-video480-step-0.mp4` belongs to job `1027753`, an obsolete failed action-scale/reward-inference learned-policy diagnostic. It is now labeled with `OBSOLETE_FAILED_DIAGNOSTIC.md` and should only be used as evidence of the old drift-away failure mode.

Alpha Schedule Analysis:
- No code bug found in the alpha reports. `_compute_teacher_force_alpha()` uses the configured alpha as an amplitude only while `traj_phase_progress <= trajectory_tracking_teacher_force_phase_end`; after that it returns zero.
- Therefore alpha `1.0` with `phase_end=0.67` can report mean/final `0.7067/0.5` when two envs reset around steps 418/440 and restart into the active teacher phase by the final frame.
- Alpha `0.75` with no resets reports mean/final `0.4644/0.0` because `0.75 * active_rate(0.6192) ~= 0.4644`, and all envs are beyond the teacher phase by the final step.
- Artifact reports now include this phase-gating note plus local trace/video/contact-sheet paths.

Artifacts:
- combined report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/comparison_report.md`
- combined plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/teacherforce_comparison_plot.png`
- combined CSV/JSON: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/summary.csv`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/summary.json`
- alpha `1.0` report/contact/video:
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100_artifacts/report.md`
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100_artifacts/video_contact_sheet.png`
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100/videos/tf-eval-a100-520-step-0.mp4`
- alpha `0.75` report/contact/video:
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100_artifacts/report.md`
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100_artifacts/video_contact_sheet.png`
  - `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100/videos/tf-eval-a075-520-step-0.mp4`
- obsolete old-diagnostic marker: `cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/OBSOLETE_FAILED_DIAGNOSTIC.md`

viz_urls:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/comparison_report.md`
- combined plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_comparison_20260611_171100/teacherforce_comparison_plot.png`
- alpha `1.0` report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100_artifacts/report.md`
- alpha `1.0` contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100_artifacts/video_contact_sheet.png`
- alpha `1.0` video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100/videos/tf-eval-a100-520-step-0.mp4`
- alpha `0.75` report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100_artifacts/report.md`
- alpha `0.75` contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100_artifacts/video_contact_sheet.png`
- alpha `0.75` video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100/videos/tf-eval-a075-520-step-0.mp4`
- obsolete marker: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/OBSOLETE_FAILED_DIAGNOSTIC.md`

Analysis:
- Teacher-force application and action-error instrumentation work; target safety remains clean.
- Tiny PPO reduced raw-policy/reference error from the env-smoke baseline but did not make a usable policy. The lower-alpha eval fails lift, and the full-alpha eval only produces partial teacher-assisted success.
- Do not scale PPO. The next iteration should isolate whether the handoff fails because teacher force turns off too early at phase `0.67` or because raw policy actions remain too far from the reference profile.

Next:
- Commit/push the summarizer/report/worklog update.
- Run one bounded eval-only schedule diagnostic from the same epoch-5 checkpoint with `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=0.75`, `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.75`, and `TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0`. This keeps the same lower alpha active for the whole trajectory to test whether the previous alpha `0.75` failure was mainly the phase gate/handoff turning off too early. Acceptance: target unsafe remains `0`, artifacts generated, and lift/success/contact behavior improves relative to `1027901`; if not, focus next on raw-policy/reference error or action normalization rather than schedule.

## 2026-06-11T17:23:22-07:00 - teacher-force phase-end diagnostic launch

Goal:
- Test whether the lower-alpha teacher-force failure in `1027901` was caused by the phase gate turning teacher application off at phase `0.67`, rather than raw policy/reference error alone.

Change:
- No new training. Eval-only diagnostic from the same epoch-5 checkpoint.
- Keep alpha amplitude fixed at `0.75`, but extend `trajectory_tracking_teacher_force_phase_end` from `0.67` to `1.0` so the lower teacher blend remains active through the whole 520-step rollout.

Version Control:
- local_source_commit: `25e97a2f42e460ff296fff6e22979f4780501a15` (`Clarify teacher-force eval artifacts`)
- pushed: yes
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_runtime_commit: `858402985719ec3ceb79db696a555443f976c997`
- remote_status: detached clean at `858402985719ec3ceb79db696a555443f976c997`
- remote_fetch_note: updating l401 to `25e97a2` failed due GitHub SSH auth (`Permission denied (publickey)`). This is acceptable for this eval-only launch because the only diff from `8584029` to `25e97a2` is the local artifact summarizer and this worklog; env/eval runtime files are identical.

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=tf_eval_p100 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=tf-eval-a075-phase100-520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=0.75,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.75,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh'`
- job_id: `1027907`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027907.out`
- expected artifacts: remote `metrics.json`, `trace.csv/jsonl`, `videos/tf-eval-a075-phase100-520-step-0.mp4`; local report/contact sheet/plot after fetch.

Acceptance:
- Target unsafe max remains `0`.
- Train/eval consistency has no real mismatches after expected alpha/phase eval overrides.
- If lift/success improves versus `1027901`, the previous lower-alpha failure is primarily schedule/handoff timing.
- If lift/success remains poor, next debugging should focus on raw-policy/reference action error, action normalization, or stronger imitation rather than only phase schedule.

## 2026-06-11T17:35:30-07:00 - teacher-force phase-end diagnostic result

Goal:
- Close out schedule-only diagnostic `1027907` and decide whether phase gating was the main blocker for the alpha `0.75` teacher-force handoff.

Command / Job:
- job_id: `1027907`
- run_name: `franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322`
- remote_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts`
- logs: `cluster_results/l401/slurm_logs/eval_franka_cube_1027907.out`

Result:
- status: completed `0:0`, 520/520 steps, no done events.
- target safety: unsafe target max `0`, target clearance min `0.065114 m`.
- teacher schedule: alpha mean/final/active `0.75/0.75/1.0`, confirming the phase gate was removed as intended.
- success/lift: success ever/final/max `0/0/0`, cube lift max `0.000042 m`, final lift `0`.
- behavior metrics: reward mean/final `8.5433/12.1490`, final EE-cube `0.2351 m`, final finger-center-cube `0.2724 m`, final gripper width `0.0236 m`.
- action metrics: raw-policy/reference L2 mean/final improved to `0.7531/0.1956`; applied/reference L2 mean `0.1863`; raw close/up mean `0.1891/0.00819`; applied close/up mean `0.2081/0.1949`.
- visual: contact sheet/video show reach/contact-ish behavior mid-rollout, then the gripper moves up/away by final frame without grasp or lift.
- consistency: artifact report now treats `trajectory_tracking_teacher_force_phase_end=1.0` as an expected eval-only override; real mismatches `[]`.

Comparison to `1027901`:
- `1027901` alpha `0.75`, phase end `0.67`: success/lift `0`, final EE-cube `0.0968 m`, final finger-cube `0.1282 m`, raw/ref L2 mean/final `1.0464/1.5687`, applied/ref L2 `0.5988`.
- `1027907` alpha `0.75`, phase end `1.0`: success/lift still `0`, final EE-cube and finger-cube worse (`0.2351/0.2724 m`), but raw/ref and applied/ref action errors substantially lower.
- Interpretation: the phase gate was not the main blocker. Lower action error against the current reference action profile is not sufficient for grasp/lift; this points to action semantics/timing, especially up/close/reference action meaning around the grasp/lift window, or the need for a stronger imitation/BC diagnostic rather than more schedule-only evals.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/report.md`
- contact sheet: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/video_contact_sheet.png`
- trace plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/trajectory_trace_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322/metrics.json`
- summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/summary.csv`
- consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/train_eval_consistency.json`
- full video: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322/videos/tf-eval-a075-phase100-520-step-0.mp4`

viz_urls:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/report.md`
- contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/video_contact_sheet.png`
- trace plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322_artifacts/trajectory_trace_plot.png`
- video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322/videos/tf-eval-a075-phase100-520-step-0.mp4`

Analysis:
- Negative schedule diagnostic: removing the phase gate did not recover lift/success.
- The raw/reference L2 improvement is real but misleading as a grasp success proxy, because the final frame still moves away and the cube never lifts.
- Do not launch more schedule-only evals and do not scale PPO.

Next:
- Focus the next bounded work on reference/action semantics and trainability:
  - inspect reference action components around the grasp/lift window where reference_delta succeeds under alpha `1.0`/offset hold but learned/alpha `0.75` fails;
  - check whether action normalization or gripper/up semantics make low L2 hide wrong close/up timing;
  - consider a small BC/action-imitation diagnostic over logged reference_delta actions before PPO, with artifacts proving raw close/up/gripper timing matches the reference and produces contact/lift.

## 2026-06-11T17:28:48-07:00 - pure-reference teacher-force sanity diagnostic plan

Goal:
- Determine whether the teacher-force reference action path itself can produce stable grasp/lift/hold when the learned policy is fully overridden for the entire 520-step rollout.

Hypothesis:
- If `teacher_force_alpha=1.0` and `phase_end=1.0` succeeds robustly, the reference/action path is viable and the remaining blocker is raw-action learning/imitation.
- If it still fails or moves away, the blocker is the teacher/reference action semantics, missing terminal hold, or the reference trajectory itself, not simply policy learning.

Change:
- No PPO and no source/runtime changes.
- Eval-only run from the same epoch-5 checkpoint used by `1027901`, `1027902`, and `1027907`.
- Set `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0`, `TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0`, `TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0`, `TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0`, `NUM_ENVS=4`, `NUM_STEPS=520`, video enabled.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- local_source_commit: `462b067cc78d1e766cf8cd0343fe746a368907ef`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_runtime_commit: `858402985719ec3ceb79db696a555443f976c997`
- remote_status: detached clean at `858402985719ec3ceb79db696a555443f976c997`
- remote_commit_note: local commits after `8584029` only touch artifact summarizers and this worklog, not `dextrah_lab/tasks`, `eval_rollout.py`, or the eval wrapper, so launching from the existing remote runtime is valid for this eval.

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=tf_eval_ref100 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=tf-eval-a100-phase100-520,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh'`
- job_id: `1027919`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027919.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, `videos/tf-eval-a100-phase100-520-step-0.mp4`; local report/contact sheet/plot after fetch.

Acceptance:
- Target unsafe max must remain `0`.
- Produce report, summary JSON/CSV, success diagnostics, trace plot, contact sheet, full MP4, and `viz-open` URLs.
- Compare directly with `1027907` and the earlier `alpha=1.0 phase=0.67` eval `1027902`.
- If robust success/lift appears, proceed next to raw-action imitation/BC diagnostics. If not, inspect teacher/reference action semantics and terminal-hold/reference trajectory behavior before any PPO scale-up.

## 2026-06-11T17:40:55-07:00 - pure-reference teacher-force sanity diagnostic result

Goal:
- Close out `1027919`, the pure-reference teacher-force eval with alpha `1.0` and phase end `1.0`, and determine whether the teacher/reference action path can produce stable grasp/lift/hold when the learned policy action is fully overridden.

Command / Job:
- job_id: `1027919`
- status: completed `0:0` in `00:01:28`
- run_name: `franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848`
- remote_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts`
- logs: `cluster_results/l401/slurm_logs/eval_franka_cube_1027919.out`

Result:
- steps/video: 520/520 rollout steps; MP4 metadata `1280x720`, `520` frames, `8.666667 s`.
- safety: target unsafe max `0`, target clearance min `0.065114 m`; train/eval consistency `passed` with no real mismatches.
- teacher override: teacher alpha mean/final/active `1.0/1.0/1.0`; configured alpha start/end/phase_end `1.0/1.0/1.0`; applied/reference L2 mean `0.0140`.
- success/lift: success mean/final/max `0.20625/0.75/0.75`; success ever `3/4`; first success step `378`; last success step `520`; suppressed success-done `3/4`; actual done count `0`.
- behavior metrics: cube lift max `0.144406 m`; reward mean/final `13.6888/29.1143`; final EE-cube `0.08613 m`; final finger-center-cube `0.12805 m`; final gripper width `0.04758 m`.
- action metrics: raw-policy/reference L2 mean/final `0.7224/0.3561`; raw policy close/up mean `0.0833/0.0665`; applied close/up mean `0.2218/0.2253`; reference close/up mean `0.2226/0.2234`.
- reference caveat: compact reference remains `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.

Visual / artifact note:
- The captured video/contact sheet appears to show env 0, which is likely the single non-successful environment in this 4-env rollout; the aggregate trace/report show 3/4 envs successful through the final step. This should be called out when sharing the video so it is not misread as contradicting the scalar result.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/report.md`
- contact sheet: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/video_contact_sheet.png`
- trace plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/trajectory_trace_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/metrics.json`
- trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/trace.jsonl`
- summary JSON/CSV: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/summary.json`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/summary.csv`
- success diagnostics: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/success_diagnostics.json`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/success_diagnostics.csv`
- consistency JSON: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/train_eval_consistency.json`
- full video: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/videos/tf-eval-a100-phase100-520-step-0.mp4`

viz_urls:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/report.md`
- contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/video_contact_sheet.png`
- trace plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/trajectory_trace_plot.png`
- video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/videos/tf-eval-a100-phase100-520-step-0.mp4`

Interpretation:
- Positive pure-reference sanity result. With alpha `1.0` held active through phase `1.0`, the teacher/reference action path can produce sustained lift/success in `3/4` envs while keeping target safety clean and without actual resets.
- This separates the current blocker from basic reference transform/controller impossibility. The main blocker is learned raw-action imitation/handoff: alpha `0.75` phase `1.0` (`1027907`) lowered action error but still failed lift, while full override succeeds.
- Do not scale PPO yet. Next bounded work should focus on why the policy does not reproduce the reference close/up/gripper timing strongly enough: inspect action normalization and per-dimension semantics, then run a small BC/action-imitation or stronger teacher-forced imitation diagnostic with frequent artifacts. If visual clarity is required before that, add or rerun a camera/env selection artifact so the recorded video follows a successful env rather than env 0.

## 2026-06-11T17:36:06-07:00 - action-semantics and clearer-reference-artifact plan

Goal:
- Continue from the positive pure-reference diagnostic `1027919` without PPO scale-up.
- Produce clearer inspectable evidence for the user and diagnose why alpha `0.75`/learned handoff fails while alpha `1.0` full override succeeds.

Planned files / edits:
- Add a local artifact helper under `dextrah_lab/rl_games/` to compare trajectory-tracking action semantics from existing `metrics.json` files:
  - raw policy vs reference vs applied action per dimension;
  - close/up/gripper timing through approach/grasp/lift windows;
  - phase, lift, success, EE/finger distances, target safety;
  - report/CSV/PNG output suitable for `viz-open`.
- Update this owned worklog with artifact paths, URLs, commands, and interpretation.
- Avoid touching the baseline `Dextrah-Franka-Cube-Grasp` task.

Validation / artifacts:
- First use existing fetched runs:
  - positive full-reference run `1027919`;
  - negative lower-alpha schedule run `1027907`;
  - earlier alpha `1.0` phase `0.67` run `1027902` if the local metrics are present.
- Generate a comparison report and plot that make the action timing mismatch visible without relying only on L2.
- For clearer video evidence, test whether a wide 4-env camera can show all envs in a cheap pure-reference rerun; if not, record the limitation and launch only a small single-env/seed pure-reference replay to capture a visibly successful env0 rollout.

Bounded trainability step:
- After the action-semantics comparison, make at most one small trainability change/launch:
  - prefer a stronger imitation/action-alignment smoke using existing env knobs if that is enough;
  - otherwise patch a minimal diagnostic knob or script, commit/push, and only then launch smoke-scale jobs.
- Acceptance before any further PPO scale-up: target unsafe remains `0`; raw close/up/gripper timing moves toward reference; short eval video/contact sheet shows approach/contact/lift rather than drift.

## 2026-06-11T17:39:22-07:00 - action-semantics artifact result

Goal:
- Compare the failed alpha `0.75` handoff runs against the positive alpha `1.0` full-reference run by action component and phase window, not only L2.

Change:
- Added local helper: `dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`.
- This does not change the env or baseline task; it consumes existing fetched `metrics.json` files and writes report/CSV/PNG artifacts.

Command:
- `python3 dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py --run alpha075_phase067=cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100/metrics.json --run alpha100_phase067=cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100/metrics.json --run alpha075_phase100=cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_phase100_520_20260611_172322/metrics.json --run alpha100_phase100=cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/metrics.json --output-dir cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606`
- validation: `python3 -m py_compile dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_report.md`
- plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_plot.png`
- CSV: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_windows.csv`
- summary JSON: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_summary.json`

viz_urls:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_report.md`
- plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_action_semantics_20260611_173606/action_semantics_plot.png`

Key comparison:
- `alpha075_phase100` still fails despite lower applied/reference L2 (`0.134` in lift window, `0.075` in hold window) because partial teacher blend leaves residual raw-policy pose/gripper terms that prevent contact/lift.
- In the lift window, `alpha075_phase100` applies close/up/gripper roughly `0.353/0.276/-0.353` versus reference `0.400/0.376/-0.400`, with residual rotation action dimensions around `0.003/-0.024/0.031`; final EE/finger distances are `0.164/0.202 m` and lift is effectively zero.
- In the same lift window, `alpha100_phase100` applies close/up/gripper `0.400/0.340/-0.400` nearly exactly on reference, with zeroed rotation dimensions; it reaches success `0.75` and max lift `0.096 m` within that window, then `0.144 m` by final.
- Raw policy remains weak on the important axes: for `alpha100_phase100` lift window raw close/up/gripper are only `0.115/0.081/-0.114` while reference is `0.400/0.343/-0.400`.

Analysis:
- The failed handoff is not primarily a phase-schedule problem after `1027907`; it is action imitation strength/semantics. A scalar L2 can look acceptable while close/up/gripper and residual pose components are still not sufficient for stable contact.
- The next trainability diagnostic should directly make raw close/up/gripper and task-space delta action match the reference around the close/lift window. Do not run another schedule-only eval or a long PPO scale-up.

Next:
- Produce the clearer pure-reference video artifact requested by the user. The existing `1027919` video appears to track env0, likely the one failing env, so try a wide-camera 4-env rerun under the same pure-reference alpha `1.0`/phase `1.0` settings.
- Then run one bounded training/eval smoke with stronger action imitation/alignment if no new runtime patch is required, or patch the smallest diagnostic knob if needed.

## 2026-06-11T17:39:22-07:00 - pure-reference wide-camera artifact launch

Goal:
- Produce a clearer visual artifact for the positive pure-reference result. The `1027919` metrics showed 3/4 final success, but the captured video appears to follow env0, likely the single failing env. This rerun uses the same pure-reference settings with a pulled-back camera intended to show multiple envs.

Version Control:
- local_commit: `a1c4c3df3b9e443600e14aca445ee29179c99e3a`
- remote_runtime_commit: `858402985719ec3ceb79db696a555443f976c997`
- remote_status: detached clean at `858402985719ec3ceb79db696a555443f976c997`
- remote_commit_note: runtime files for eval remain identical to local; local commit only added artifact helper/worklog since the last runtime-affecting commit.

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=tf_ref100_wide --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922,NUM_ENVS=4,NUM_STEPS=520,VIDEO_LENGTH=520,VIDEO_NAME_PREFIX=tf-ref100-wide4env,CAPTURE_VIDEO=True,DETERMINISTIC=True,ACTION_SOURCE=policy,SUPPRESS_SUCCESS_TERMINATION=True,USE_CUDA_GRAPH=False,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,CAMERA_EYE_X=3.0,CAMERA_EYE_Y=-3.4,CAMERA_EYE_Z=2.8,CAMERA_TARGET_X=0.8,CAMERA_TARGET_Y=0.8,CAMERA_TARGET_Z=0.85,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=15.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh'`
- job_id: `1027923`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027923.out`

Acceptance:
- Same safety/behavior expectations as `1027919`: target unsafe max `0`, success/lift comparable if camera change does not alter physics.
- Artifact acceptance: full MP4, contact sheet, trace plot, report, metrics, and `viz-open` URLs. If the camera still does not expose successful envs, record that limitation explicitly and use this run only as a broad-scene visual.

## 2026-06-11T17:43:10-07:00 - pure-reference wide-camera artifact result

Goal:
- Close out the clearer visual artifact request for the positive pure-reference path.

Command / Job:
- job_id: `1027923`
- status: completed `0:0` in `00:01:27`
- run_name: `franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922`
- remote_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922`
- local_artifact_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts`
- logs: `cluster_results/l401/slurm_logs/eval_franka_cube_1027923.out`

Result:
- steps/video: 520/520 rollout steps; MP4 metadata `1280x720`, `520` frames, `8.666667 s`.
- safety: target unsafe max `0`, target clearance min `0.065114 m`; train/eval consistency passed.
- success/lift: success mean/final/max `0.20625/0.75/0.75`, success ever `3/4`, cube lift max `0.144406 m`.
- action/reference: teacher alpha mean/final `1.0/1.0`, applied/reference L2 mean `0.0140`, raw-policy/reference L2 mean `0.7224`.
- visual: wide contact sheet/video show multiple envs at once; final frame visibly resolves the earlier closeup ambiguity by showing lifted cubes in the multi-env scene while one cube remains on the table.
- reference caveat remains: compact reference is `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.

Artifacts:
- report: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/report.md`
- contact sheet: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/video_contact_sheet.png`
- trace plot: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/trajectory_trace_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922/metrics.json`
- trace CSV/JSONL: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922/trace.csv`, `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922/trace.jsonl`
- full video: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922/videos/tf-ref100-wide4env-step-0.mp4`

viz_urls:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/report.md`
- contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/video_contact_sheet.png`
- trace plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922_artifacts/trajectory_trace_plot.png`
- video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_ref100_wide4env_20260611_173922/videos/tf-ref100-wide4env-step-0.mp4`

Analysis:
- This artifact resolves the user-facing confusion from the old closeup videos: the reference path is visibly viable in multiple envs when fully applied.
- The remaining trainability problem is still the learned raw policy's weak/incorrect action timing, especially close/up/gripper and residual pose components around lift.

Next:
- Launch only a smoke-scale trainability diagnostic. Use stronger existing action-alignment/teacher-force knobs first to avoid an unnecessary runtime patch: e.g. high action-alignment weight and full teacher force through the horizon for a tiny PPO run, then immediately evaluate with lower/no teacher to see whether raw close/up/gripper timing moves toward the reference.

## 2026-06-11T17:45:00-07:00 - high-alignment full-teacher PPO smoke launch plan

Goal:
- Test whether the raw policy can be pushed closer to the reference action profile with a stronger action-imitation reward when the stable reference path is fully applied.

Hypothesis:
- If weak raw close/up/gripper timing is the bottleneck, a short fine-tune from the previous teacher-force epoch-5 checkpoint with high action-alignment weight and full teacher force should reduce raw-policy/reference action error quickly.
- If raw error and partial-teacher behavior do not improve, the next issue is likely action normalization/optimization, not reference feasibility or schedule.

Change:
- No source/runtime changes.
- Tiny PPO fine-tune from `franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913` epoch-5 checkpoint.
- Increase `trajectory_tracking_action_alignment_weight` from `15.0` to `80.0`.
- Keep teacher force fully active through the full horizon: alpha start/end `1.0/1.0`, phase end `1.0`, anneal steps `0`.

Version Control:
- local_commit: `acc94c7c3ca6a9c72062575cdcb3da1af21b67c0`
- remote_runtime_commit: `858402985719ec3ceb79db696a555443f976c997`
- remote_status: detached clean; runtime source compatible with local for this no-code-change smoke.

Acceptance:
- Training job exits cleanly with checkpoints and no NaN/traceback.
- Immediate eval artifacts after training must include at least:
  - policy-only / alpha `0.0` instrumentation;
  - partial teacher alpha `0.75`, phase `1.0`;
  - full teacher alpha `1.0`, phase `1.0`.
- Compare raw/ref close/up/gripper and L2 against the previous `1027907`/`1027919` action-semantics bundle. Do not scale PPO unless partial/no-teacher videos show plausible approach/contact/lift and target unsafe remains `0`.

Command / Job:
- command: `ssh l401 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=tf_align80_ft5 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_teacherforce_align80_ft5_20260611_174500,NUM_ENVS=128,MAX_ITERATIONS=5,HORIZON_LENGTH=120,MINI_EPOCHS=4,MINIBATCH_SIZE=3840,CENTRAL_VALUE_MINIBATCH_SIZE=3840,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,REQUEUE_ON_EARLY_TERM=False,SAVE_FREQUENCY=1,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=80.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True cluster/sbatch_train_teacher_8gpu.sh'`
- job_id: `1027925`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft5_20260611_174500`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027925.out`

## 2026-06-11T17:48:20-07:00 - high-alignment full-teacher PPO smoke result

Goal:
- Close out job `1027925` before launching eval artifacts from its checkpoint.

Result:
- job_id: `1027925`
- status: completed `0:0`, elapsed `00:00:51`, node `pool0-00030`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_align80_ft5_20260611_174500`
- local_log: `cluster_results/l401/slurm_logs/teacher_8gpu_1027925.out`
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft5_20260611_174500/nn/last_dextrah_franka_cube_traj_tracking_ep_6_rew_464.60687.pth`
- train env: observation space `72`, action space `7`, `trajectory_tracking_action_alignment_weight=80.0`, teacher force alpha start/end `1.0/1.0`, phase end `1.0`, anneal steps `0`, reference path `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.

Important nuance:
- This is not a five-new-epoch run. RL-Games restored the prior runtime state at epoch `5`; with `max_iterations=5`, the run advanced only one rollout/update and stopped at `epoch 6/5`.
- Treat this checkpoint as a tiny high-alignment diagnostic, not a clean training pass or a scale-up signal. The reward suffix `464.60687` is not by itself a behavior verdict.

Next:
- Launch bounded 520-step video evals from this epoch-6 checkpoint at teacher alpha `0.0`, `0.75`, and `1.0`, all with phase end `1.0` and no alpha anneal.
- Acceptance remains visual and metric based: target unsafe max `0`; no reset pathology; report raw/reference/applied action components; policy-only or partial-teacher behavior must approach/contact/lift before any longer PPO.

## 2026-06-11T17:49:13-07:00 - high-alignment epoch-6 eval sweep launch

Goal:
- Evaluate whether the one-update high-alignment checkpoint changed raw-policy action semantics enough to improve policy-only or partial-teacher behavior.

Version Control:
- local_commit: `2eec9a7db2553f04b287878ee6f4e86872cc3be1`
- remote_runtime_commit: `2eec9a7db2553f04b287878ee6f4e86872cc3be1`
- remote_update_note: l401 could not fetch GitHub directly due SSH key access, so I transferred a local git bundle and checked out the exact commit detached.

Common eval settings:
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft5_20260611_174500/nn/last_dextrah_franka_cube_traj_tracking_ep_6_rew_464.60687.pth`
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`
- `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `SUPPRESS_SUCCESS_TERMINATION=True`, `SEED=64`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`)
- action alignment weight `80.0`; teacher force enabled; phase end `1.0`; anneal steps `0`; raw-policy/reference comparison enabled.

Jobs:
- alpha `0.0`: job_id `1027926`, run `franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913`
- alpha `0.75`: job_id `1027927`, run `franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913`
- alpha `1.0`: job_id `1027928`, run `franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913`

Acceptance:
- Fetch each run, validate MP4 frame count, produce report/contact sheet/trace plot/summary JSON/CSV/consistency JSON, and `viz-open` URLs.
- Then regenerate action-semantics comparison against pre-finetune `1027907`/`1027919`.
- No PPO scale-up unless video and per-dimension action plots show policy-only or alpha `0.75` reaches contact/lift without target safety regression.

## 2026-06-11T17:52:06-07:00 - high-alignment epoch-6 eval sweep result

Goal:
- Determine whether the one-update high-alignment checkpoint from `1027925` made policy-only or partial-teacher handoff grasp/lift.

Jobs / Artifacts:
- alpha `0.0`: job_id `1027926`, run `franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913`
  - report: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913_artifacts/report.md`
  - trace plot: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913_artifacts/trajectory_trace_plot.png`
  - contact sheet: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`
  - video: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913/videos/align80_a000-step-0.mp4`
- alpha `0.75`: job_id `1027927`, run `franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913`
  - report: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913_artifacts/report.md`
  - trace plot: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913_artifacts/trajectory_trace_plot.png`
  - contact sheet: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`
  - video: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913/videos/align80_a075-step-0.mp4`
- alpha `1.0`: job_id `1027928`, run `franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913`
  - report: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913_artifacts/report.md`
  - trace plot: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913_artifacts/trajectory_trace_plot.png`
  - contact sheet: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`
  - video: `cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913/videos/align80_a100-step-0.mp4`
- combined action semantics:
  - report: `cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/action_semantics_report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/action_semantics_plot.png`
  - CSV: `cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/action_semantics_windows.csv`
  - concise diagnostic report: `cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/alignment_diagnostic_report.md`

viz_urls:
- concise report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/alignment_diagnostic_report.md`
- action semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/action_semantics_report.md`
- action semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_action_semantics_20260611_175206/action_semantics_plot.png`
- alpha `0.0` report/contact/video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913_artifacts/report.md`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a000_phase100_520_20260611_174913/videos/align80_a000-step-0.mp4`
- alpha `0.75` report/contact/video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913_artifacts/report.md`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a075_phase100_520_20260611_174913/videos/align80_a075-step-0.mp4`
- alpha `1.0` report/contact/video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913_artifacts/report.md`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913_artifacts/video_contact_sheet.png`, `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80_eval_a100_phase100_520_20260611_174913/videos/align80_a100-step-0.mp4`

Metrics:
- alpha `0.0`: success mean/final/max `0/0/0`; lift max `0`; final EE/finger distances `0.465/0.442 m`; target unsafe max `0`; MP4 metadata `1280x720`, `520` frames.
- alpha `0.75`: success mean/final/max `0/0/0`; lift max `0.000139 m`; final EE/finger distances `0.236/0.270 m`; target unsafe max `0`; MP4 metadata `1280x720`, `520` frames.
- alpha `1.0`: success mean/final/max `0.20625/0.75/0.75`; success ever `3/4`; lift max `0.144406 m`; final EE/finger distances `0.086/0.128 m`; target unsafe max `0`; MP4 metadata `1280x720`, `520` frames.
- train/eval consistency: all three evals passed; expected eval-only overrides were separated from real mismatches, and real mismatches were `[]`.

Action-semantics diagnosis:
- The high-alignment one-update checkpoint did not fix handoff.
- Policy-only lift window raw close/up/gripper: `0.356 / 0.004 / -0.356` while reference was `0.400 / 0.718 / -0.400`.
- Partial-teacher alpha `0.75` lift window raw close/up/gripper: `0.281 / 0.037 / -0.281`; applied blend was `0.370 / 0.277 / -0.370`, still no lift.
- Full-teacher alpha `1.0` lift window applied close/up/gripper: `0.400 / 0.340 / -0.400`, and the run succeeded in `3/4` envs.
- Visuals match metrics: policy-only drifts away; alpha `0.75` reaches near/contact-ish but leaves cube on table; alpha `1.0` is the reference-driven success path.

Verdict:
- Do not scale PPO from this checkpoint.
- The diagnostic remains an action-imitation/handoff problem, not reference feasibility. The one-update smoke was also weaker than intended because resume/max-iteration semantics only advanced one epoch.

## 2026-06-11T17:56:10-07:00 - corrected high-alignment smoke plan

Goal:
- Run one bounded corrected trainability diagnostic that actually performs several additional high-alignment updates from the epoch-5 checkpoint, then evaluate it with the same alpha `0.0/0.75/1.0` video bundle.

Reason:
- `1027925` resumed at epoch `5` with `MAX_ITERATIONS=5`, so it only produced one update (`epoch 6/5`). That is useful evidence but not enough to test whether the stronger action-imitation reward can move raw close/up/gripper timing.

Plan:
- Resume from the epoch-5 checkpoint:
  - `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth`
- Keep smoke scale: `NUM_ENVS=128`, `HORIZON_LENGTH=120`, single GPU, no distributed, save every epoch.
- Set `MAX_ITERATIONS=10` so a resume at epoch `5` should advance roughly five more updates.
- Keep teacher force alpha `1.0/1.0`, phase end `1.0`, no anneal, action-alignment weight `80.0`.
- After training, run the same 520-step eval bundle at alpha `0.0`, `0.75`, and `1.0`; no long PPO and no scale-up.

Acceptance:
- Training must complete without traceback/NaN and produce checkpoints beyond epoch 6.
- Eval acceptance remains metric/video based: target unsafe max `0`, no reset pathology, raw/ref action component plots show improvement, and alpha `0.75` must achieve actual lift before considering any longer training.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=tf_align80_ft10 --export=ALL,...,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513,NUM_ENVS=128,MAX_ITERATIONS=10,HORIZON_LENGTH=120,MINIBATCH_SIZE=3840,CENTRAL_VALUE_MINIBATCH_SIZE=3840,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=80.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0 cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1027933`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027933.out`
- code_commit: `2cb0fc6f8650392a3ee00d266ba134c709c0dca5`

## 2026-06-11T17:57:06-07:00 - corrected high-alignment eval sweep launch

Training result:
- job_id: `1027933`
- status: completed `0:0`, elapsed `00:01:05`, node `pool0-00030`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513`
- local_log: `cluster_results/l401/slurm_logs/teacher_8gpu_1027933.out`
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513/nn/last_dextrah_franka_cube_traj_tracking_ep_10_rew_9268.733.pth`
- training advanced as intended: restored epoch `5`, then saved checkpoints for epochs `6`, `7`, `8`, `9`, and `10`.
- reward suffix note: epoch 6-8 suffix was `15.325785`, epoch 9 `7552.5454`, epoch 10 `9268.733`; behavior verdict still requires eval videos/metrics.

Common eval settings:
- checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513/nn/last_dextrah_franka_cube_traj_tracking_ep_10_rew_9268.733.pth`
- `NUM_ENVS=4`, `NUM_STEPS=520`, video enabled, success termination suppressed, seed `64`
- teacher force enabled; alpha fixed per run; phase end `1.0`; no anneal; action alignment compare raw policy enabled.
- reference caveat remains `curobo_validated=false`.

Jobs:
- alpha `0.0`: job_id `1027936`, run `franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706`
- alpha `0.75`: job_id `1027937`, run `franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706`
- alpha `1.0`: job_id `1027938`, run `franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706`

Acceptance:
- Fetch logs/runs, validate video frame counts, run summarizer, open reports/video sheets/plots with `viz-open`, and regenerate combined action-semantics comparison against pre-finetune and epoch-6 align80 artifacts.
- If alpha `0.0` and `0.75` still do not lift, stop PPO schedule tweaks and switch to explicit supervised action-imitation/BC diagnostic.

## 2026-06-11T18:06:30-07:00 - corrected high-alignment ft10 eval verdict and BC pivot

Goal:
- Close the corrected high-alignment continuation loop and decide whether additional PPO schedule/reward tweaks are justified.

Result:
- training job `1027933` completed and advanced the intended resumed updates from epoch `5` through epoch `10`.
- eval alpha `0.0`, job `1027936`, run `franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706`
  - status: completed `0:0`; video metadata valid (`1280x720`, `520` frames).
  - metrics: success mean/final/max `0/0/0`; lift max `0.002424 m`; target unsafe max `0`; target clearance min `0.065114 m`; raw/reference L2 mean/final `1.8834/1.8332`; final EE/finger-center distances `0.2879/0.3175 m`.
  - artifacts: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706_artifacts/report.md`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706/videos/al80ft10_a000-step-0.mp4`.
  - viewer contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a000_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`
- eval alpha `0.75`, job `1027937`, run `franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706`
  - status: completed `0:0`; video metadata valid (`1280x720`, `520` frames).
  - metrics: success mean/final/max `0/0/0`; lift max `0.000615 m`; target unsafe max `0`; target clearance min `0.065114 m`; raw/reference L2 mean/final `0.8396/0.4410`; applied/reference L2 mean `0.2064`; final EE/finger-center distances `0.2335/0.2640 m`.
  - artifacts: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706_artifacts/report.md`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706/videos/al80ft10_a075-step-0.mp4`.
  - viewer contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a075_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`
- eval alpha `1.0`, job `1027938`, run `franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706`
  - status: completed `0:0`; video metadata valid (`1280x720`, `520` frames).
  - metrics: success mean/final/max `0.20625/0.75/0.75`; success ever `3/4`; lift max `0.144406 m`; target unsafe max `0`; target clearance min `0.065114 m`; applied/reference L2 mean `0.0140`; final EE/finger-center distances `0.0861/0.1280 m`.
  - artifacts: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706_artifacts/report.md`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`, `cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706/videos/al80ft10_a100-step-0.mp4`.
  - viewer contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80ft10_eval_a100_phase100_520_20260611_175706_artifacts/video_contact_sheet.png`
- combined action-semantics artifacts:
  - report: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_action_semantics_20260611_180016/action_semantics_report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_action_semantics_20260611_180016/action_semantics_plot.png`
  - CSV: `cluster_results/l401/franka_cube_traj_tracking_align80ft10_action_semantics_20260611_180016/action_semantics_windows.csv`
  - viewer report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80ft10_action_semantics_20260611_180016/action_semantics_report.md`
  - viewer plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_align80ft10_action_semantics_20260611_180016/action_semantics_plot.png`

Analysis:
- Corrected several-update PPO/high-alignment still leaves alpha `0.0` and alpha `0.75` with no lift, while alpha `1.0` full teacher remains successful. This cleanly preserves the prior conclusion: reference feasibility and target safety are good, but raw-policy imitation/handoff is not solved by PPO reward shaping.
- Per-dimension action semantics show the policy learned some close/gripper behavior but still misses the lift/hold profile. In the alpha `0.75` lift window, raw close/up/gripper were about `0.486 / 0.117 / -0.486` versus reference `0.400 / 0.338 / -0.400`; the applied blend was closer (`0.421 / 0.272 / -0.421`) but still produced no lift. In the full-teacher hold window the raw policy regressed to weak/incorrect hold actions, including gripper opening, while the applied reference override succeeded.
- This is a negative verdict for PPO schedule/teacher-force tweaking. No scale-up.

Next:
- Implement a bounded explicit supervised action-imitation/BC diagnostic for the same 72-D observation and 7-D action parameterization.
- First source change: add an eval/export route that records policy observations, reference_delta labels, raw policy actions, applied actions, phase/progress, lift/success, and safety metadata from a full-reference/teacher rollout.
- Second source change, if checkpoint/model access is feasible in the Isaac container: add a tiny actor overfit script that loads the same RL-Games checkpoint, minimizes MSE from raw actor output to reference labels on the exported batch, writes train/held-out action-error curves, and saves a normal RL-Games-compatible checkpoint.
- Acceptance for the BC diagnostic: prove raw/reference MSE drops on a held-out batch, then evaluate the resulting checkpoint with alpha `0.0`, `0.75`, and `1.0` using the existing video/report/action-semantics artifact bundle. If alpha `0.0`/`0.75` still fail, debug action normalization/model-output semantics before any further RL.

## 2026-06-11T18:11:50-07:00 - BC reference-action imitation runtime smoke launch

Goal:
- Validate the new supervised reference-action imitation/export path inside the Isaac/RL-Games container before running a fuller BC diagnostic.

Change:
- Added `dextrah_lab/rl_games/bc_reference_action_imitation.py`, a diagnostic-only script that collects policy observations while stepping `reference_delta`, labels them with the same 7-D reference action interface, optimizes the loaded RL-Games actor by supervised MSE, writes loss artifacts, and saves an RL-Games-compatible checkpoint.
- Added `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to run the diagnostic on l401 with the same container/mount patterns as eval.

Version Control:
- implementation_commit: `802959fab452995dd4fabb3439de55bbbc7285b4`
- branch: `codex/franka-cube-trajectory-tracking`
- push: pushed to origin; l401 GitHub fetch still unavailable, so deployed via local git bundle.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `802959fab452995dd4fabb3439de55bbbc7285b4`, clean.
- changed_files: `dextrah_lab/rl_games/bc_reference_action_imitation.py`, `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`, this worklog.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py` passed locally.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh` passed locally.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:25:00 --job-name=bc_ref_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_ref_smoke_20260611_181150,NUM_ENVS=4,COLLECTION_STEPS=80,TRAIN_STEPS=20,BATCH_SIZE=128,LEARNING_RATE=0.0003,VALIDATION_FRACTION=0.25,LOSS_DIMS=0,1,2,3,4,5,6,EVAL_INTERVAL=5,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513/nn/last_dextrah_franka_cube_traj_tracking_ep_10_rew_9268.733.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- job_id: `1027939`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_ref_smoke_20260611_181150`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027939.out`
- expected_artifacts: `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `report.md`, `reference_action_dataset.pt`, `nn/bc_reference_action_imitation.pth`

Acceptance:
- Container/job exits cleanly and writes metrics plus checkpoint.
- Train/held-out raw/reference MSE decreases over the tiny smoke. This validates wiring only; it is not a behavior claim.
- If it passes, launch the fuller bounded BC diagnostic and then alpha `0.0/0.75/1.0` video evals from the BC checkpoint.

## 2026-06-11T18:14:20-07:00 - BC runtime smoke result and wrapper fix

Result:
- job_id: `1027939`
- status: failed `1:0`, elapsed `00:00:49`, node `pool0-00030`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_smoke_20260611_181150`
- local_log: `cluster_results/l401/slurm_logs/bc_franka_cube_1027939.out`
- viewer report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_smoke_20260611_181150/report.md`
- viewer plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_smoke_20260611_181150/bc_loss_plot.png`

Metrics / Artifacts:
- The BC collection/training code ran and wrote `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `report.md`, `reference_action_dataset.pt`, and a checkpoint payload.
- Smoke dataset: `320` samples (`240` train / `80` validation), observation dim `72`, action dim `7`, `curobo_validated=false`.
- Because Slurm `--export` split comma-separated `LOSS_DIMS`, this smoke trained only dimension `0` (`loss_dims=[0]`), not all seven action dimensions.
- Even with that launch mistake, the actor API is trainable on the batch: held-out x-dim MSE dropped from `0.272798` to `0.008420`; held-out x abs dropped from `0.4001` to `0.0584`.

Root Cause:
- Wrapper failure was post-run artifact validation, not a model/env error. `torch_ext.save_checkpoint("/.../bc_reference_action_imitation.pth", ...)` wrote `bc_reference_action_imitation.pth.pth`, while the wrapper checked for `bc_reference_action_imitation.pth`.
- The all-dimension loss string cannot be passed as `LOSS_DIMS=0,1,2,3,4,5,6` through `sbatch --export` because commas delimit variables.

Patch:
- Change the BC script to accept `--loss_dims all` (also supports colon/space-separated indices).
- Save the BC checkpoint with `torch.save` to the exact requested `.pth` path.
- Change the wrapper default to `LOSS_DIMS=all`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py` passed after the patch.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` passed after the patch.

Next:
- Commit/push/deploy the wrapper fix and relaunch a bounded all-dimension BC diagnostic.
- Use the resulting BC checkpoint only after confirming held-out all-dim errors decrease; then run alpha `0.0`, `0.75`, `1.0` video evals and action-semantics comparison.

## 2026-06-11T18:16:20-07:00 - all-dimension BC diagnostic launch

Goal:
- Test whether explicit supervised actor imitation can reduce raw/reference action error over all seven action dimensions using teacher/reference rollouts from the actual trajectory-tracking env.

Version Control:
- implementation_commit: `70ec748f5f25ba80e7419be7364cab9972b5fc91`
- branch: `codex/franka-cube-trajectory-tracking`
- push: pushed to origin; deployed to l401 via git bundle because remote GitHub fetch is unavailable.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `70ec748f5f25ba80e7419be7364cab9972b5fc91`, clean.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:35:00 --job-name=bc_ref_all7 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_ref_all7_20260611_181620,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.0002,VALIDATION_FRACTION=0.2,EVAL_INTERVAL=25,SEED=64,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_align80_ft10_20260611_175513/nn/last_dextrah_franka_cube_traj_tracking_ep_10_rew_9268.733.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- job_id: `1027940`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027940.out`
- expected_artifacts: `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `report.md`, `reference_action_dataset.pt`, `nn/bc_reference_action_imitation.pth`

Acceptance:
- Job exits cleanly and writes the exact `.pth` checkpoint path.
- `loss_dims` resolves to all seven dims, not only dim `0`.
- Held-out all-dim MSE/L2 and close/up/gripper abs errors decrease materially.
- Only if this passes: run alpha `0.0`, `0.75`, `1.0` 520-step video evals from the BC checkpoint, then regenerate action-semantics artifacts.

## 2026-06-11T18:18:40-07:00 - all-dimension BC diagnostic result

Result:
- job_id: `1027940`
- status: completed `0:0`, elapsed `00:01:00`, node `pool0-00030`
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620`
- local_log: `cluster_results/l401/slurm_logs/bc_franka_cube_1027940.out`
- report: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/report.md`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/bc_metrics.json`
- loss CSV: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/bc_loss_curve.csv`
- loss plot: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/bc_loss_plot.png`
- dataset: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/reference_action_dataset.pt`
- BC checkpoint: `/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth`
- local checkpoint copy: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth`
- viewer report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/report.md`
- viewer plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/bc_loss_plot.png`

Dataset metadata:
- samples: `4160` total, `3328` train, `832` held-out validation.
- observation dim: `72`; action dim: `7`; `loss_dims=[0,1,2,3,4,5,6]`.
- dataset file size: `1,501,627` bytes.
- reference caveat: `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.

Action-error table:

| Split | Initial MSE | Final MSE | Initial L2 | Final L2 | Initial close abs | Final close abs | Initial up abs | Final up abs | Initial gripper abs | Final gripper abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.142877 | 0.000163 | 0.885323 | 0.024477 | 0.099118 | 0.005470 | 0.242639 | 0.005768 | 0.536239 | 0.010539 |
| held-out | 0.141185 | 0.000213 | 0.882957 | 0.026307 | 0.099468 | 0.005373 | 0.236709 | 0.006976 | 0.539630 | 0.011249 |

Analysis:
- The explicit supervised actor update can reduce raw/reference action error on held-out observations by more than an order of magnitude across all action dimensions. This proves the actor/checkpoint/model-output path is trainable for the reference labels under the same 72-D/7-D parameterization.
- This is still only action-imitation loss evidence. It does not prove behavior until evaluated with videos and task metrics.
- Acceptance gate for eval is met: all-dim held-out errors materially decreased, target reference remains marked `curobo_validated=false`, and the checkpoint exists at the exact wrapper-expected path.

Next:
- Launch alpha `0.0`, `0.75`, and `1.0` 520-step video evals from `/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth`.
- Fetch/open each eval report/contact sheet/video and regenerate action-semantics comparison before making any behavior claim.

## 2026-06-11T18:19:50-07:00 - BC checkpoint eval sweep launch

Goal:
- Evaluate whether the explicit supervised BC checkpoint changes behavior, not just action MSE. Compare policy-only, partial-teacher, and full-teacher rollouts with the same 520-step video/action-semantics bundle as previous diagnostics.

Common eval settings:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth`
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`
- `NUM_ENVS=4`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, video enabled, deterministic policy, success termination suppressed, seed `64`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`)
- teacher force enabled for all evals; alpha fixed per run; phase end `1.0`; anneal steps `0`; raw-policy/reference comparison enabled.
- action alignment config held at weight `80.0`, phase start `0.0`, sharpness `1.0`, contact gate disabled, to keep metric semantics consistent with align80/ft10 evals.

Jobs:
- alpha `0.0`: job_id `1027941`, run `franka_cube_traj_tracking_bc_ref_all7_eval_a000_phase100_520_20260611_181950`
- alpha `0.75`: job_id `1027942`, run `franka_cube_traj_tracking_bc_ref_all7_eval_a075_phase100_520_20260611_181950`
- alpha `1.0`: job_id `1027943`, run `franka_cube_traj_tracking_bc_ref_all7_eval_a100_phase100_520_20260611_181950`

Acceptance:
- Fetch/open report, trace plot, contact sheet, full video, metrics JSON/CSV, and consistency JSON for each run.
- Validate MP4 metadata/frame count for all three videos.
- Regenerate combined action-semantics report/plot across alpha `0.0/0.75/1.0`.
- Explicitly check train/eval consistency: task, obs dim `72`, action dim/scaling, cube randomization `0.08`, reference path, teacher force alpha/phase, and checkpoint semantics.
- No longer training unless alpha `0.0` or alpha `0.75` video/metrics show actual contact/lift with target unsafe max `0`.

## 2026-06-11T18:16:18-07:00 - BC eval visual mismatch plan

Goal:
- Resolve the BC eval artifact mismatch before any more training: aggregate metrics show alpha `0.75` and `1.0` lift/succeed, but the single MP4/contact sheet is the default env0 camera and appears to show a failure.

Plan:
- Patch `dextrah_lab/rl_games/eval_rollout.py` to expose an eval-only `--camera_env_index` and to record per-env success/lift/done summaries in `metrics.json`.
- Patch `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` to pass/log `CAMERA_ENV_INDEX`.
- Run cheap validation: `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py` and `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`.
- Commit/push/deploy the exact commit to the l401 agent worktree.
- Rerun bounded 520-step video evals from the BC checkpoint with `NUM_ENVS=4`, success termination suppressed, and camera targeted to envs beyond env0. Minimum required viewer set: alpha `0.0` env0 failure, alpha `0.75` successful env, alpha `1.0` successful env.
- Fetch/open reports, contact sheets, videos, trace plots, action-semantics summaries, and explicitly flag env0-only video as misleading in the final artifact report.

Acceptance:
- `metrics.json` identifies which envs succeeded/lifted.
- At least one alpha `0.75` and one alpha `1.0` video/contact sheet visually show a successful env if the deterministic rerun reproduces the aggregate success.
- Target unsafe remains `0`; baseline task remains untouched; reference remains `curobo_validated=false`.

## 2026-06-11T18:20:33-07:00 - BC eval targeted visual launch

Version Control:
- implementation_commit: `61200b73caeece99b781fee66d2774145f125ac8`
- branch: `codex/franka-cube-trajectory-tracking`
- push: pushed to origin; l401 deployed via local git bundle because GitHub fetch is unavailable on the remote.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `61200b73caeece99b781fee66d2774145f125ac8`, clean.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_franka_cube_validation_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`: passed.
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: passed.

Selector jobs:
- alpha `0.75` selector: job `1027945`, run `franka_cube_traj_tracking_bc_ref_all7_eval_a075_envselect_520_20260611_181852`, no video.
- alpha `1.0` selector: job `1027946`, run `franka_cube_traj_tracking_bc_ref_all7_eval_a100_envselect_520_20260611_181852`, no video.
- selector result: alpha `0.75` succeeds in envs `2` and `3`; alpha `1.0` succeeds in envs `1`, `2`, and `3`; env0 remains a failure in both. Target unsafe max remained `0`.

Viewer jobs:
- alpha `0.0`, env0 failure video: job `1027947`, run `franka_cube_traj_tracking_bc_ref_all7_vis_a000_env0_520_20260611_182033`.
- alpha `0.75`, env2 success video: job `1027948`, run `franka_cube_traj_tracking_bc_ref_all7_vis_a075_env2_520_20260611_182033`.
- alpha `1.0`, env1 success video: job `1027949`, run `franka_cube_traj_tracking_bc_ref_all7_vis_a100_env1_520_20260611_182033`.

Next:
- Monitor viewer jobs to completion, fetch `metrics.json`, `trace.csv/jsonl`, mp4s, stdout logs.
- Run artifact summarizer and action-semantics comparison; validate video frame counts.
- `viz-open` the report/contact sheet/video/trace plot for each viewer run.
- Explicitly mark the previous env0-only BC eval videos as misleading for aggregate success interpretation.

## 2026-06-11T18:28:40-07:00 - BC targeted visual result

Result:
- status: passed visual-mismatch closure; no training launched.
- jobs: `1027947`, `1027948`, `1027949` all completed `0:0`.
- selector jobs: `1027945`/`1027946` completed `0:0` and produced per-env success/lift fields.
- artifact report: `cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_targeted_visual_report_20260611_1828.md`
- artifact report URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_targeted_visual_report_20260611_1828.md`

Artifacts:
- alpha `0.0` env0 failure report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a000_env0_520_20260611_182033_artifacts/report.md`
- alpha `0.0` env0 failure sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a000_env0_520_20260611_182033_artifacts/video_contact_sheet.png`
- alpha `0.0` env0 failure video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a000_env0_520_20260611_182033/videos/bc-ref-all7-a000-env0-step-0.mp4`
- alpha `0.75` env2 success report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a075_env2_520_20260611_182033_artifacts/report.md`
- alpha `0.75` env2 success sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a075_env2_520_20260611_182033_artifacts/video_contact_sheet.png`
- alpha `0.75` env2 success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a075_env2_520_20260611_182033/videos/bc-ref-all7-a075-env2-step-0.mp4`
- alpha `1.0` env1 success report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a100_env1_520_20260611_182033_artifacts/report.md`
- alpha `1.0` env1 success sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a100_env1_520_20260611_182033_artifacts/video_contact_sheet.png`
- alpha `1.0` env1 success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_vis_a100_env1_520_20260611_182033/videos/bc-ref-all7-a100-env1-step-0.mp4`
- action-semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_targeted_visual_action_semantics_20260611_1826/action_semantics_report.md`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_ref_all7_targeted_visual_action_semantics_20260611_1826/action_semantics_plot.png`

Metrics:
- MP4 validation: all three videos are `1280x720`, `520` frames, `8.666667s`, `60 fps`.
- alpha `0.0` env0: `success_ever_by_env=[false,false,false,false]`, final/max lift all `0.0`, target unsafe max `0.0`, target clearance min `0.065114 m`, raw/ref L2 mean/final `0.9755/1.1988`.
- alpha `0.75` env2: `success_ever_by_env=[false,false,true,true]`, final success `0.5`, final lift by env `[0.0,0.0,0.19347,0.19387]`, target unsafe max `0.0`, target clearance min `0.065114 m`, raw/ref L2 mean/final `0.0519/0.0916`.
- alpha `1.0` env1: `success_ever_by_env=[false,true,true,true]`, final success `0.75`, final lift by env `[0.0,0.19264,0.19255,0.19244]`, target unsafe max `0.0`, target clearance min `0.065114 m`, raw/ref L2 mean/final `0.0438/0.0788`.

Visual diagnosis:
- The old BC eval videos were default env0 views and are misleading for aggregate success: env0 fails even when other envs succeed.
- The new alpha `0.75` env2 sheet/video visibly shows grasp/lift by the final frame.
- The new alpha `1.0` env1 sheet/video visibly shows grasp/lift by the final frame.
- The alpha `0.0` env0 policy-only sheet/video remains a clear no-lift failure.

Analysis:
- The visual mismatch is closed. The all-7 BC checkpoint makes partial teacher alpha `0.75` viable in 2/4 envs under this deterministic seed, while policy-only alpha `0.0` remains non-lifting.
- This is real progress over the earlier PPO-only/teacher-force state, where alpha `0.75` did not lift. It is not a reason to scale PPO yet: learned policy-only control is still insufficient.
- Next bounded trainability direction should be on-policy imitation / DAgger-style aggregation for states reached by alpha `0.0`, or a curriculum that gradually lowers teacher alpha only after targeted success-window videos remain plausible.

## 2026-06-11T18:28:13-07:00 - BC-initialized PPO handoff smoke plan

Goal:
- Test the smallest safe learned handoff step after the targeted visual gate: resume PPO from the all-7 BC checkpoint with teacher-assisted rollouts and high raw-action alignment, then evaluate whether policy-only or lower-alpha behavior improves.

Hypothesis:
- The BC checkpoint already matches the reference action labels on held-out reference states, but policy-only alpha `0.0` fails because rollout states drift off the reference manifold. A short on-policy PPO continuation with teacher force `0.75 -> 0.5`, full-phase teacher availability, and raw-policy action-alignment reward may keep rollouts near successful reference states while updating the raw policy.

Plan:
- Use existing wrappers only; no baseline task or reset-prior files touched.
- Commit/push this worklog update, then deploy exact commit `82b60d38849e06e76ca19ec543374504a6bfaff1` to the l401 agent worktree.
- Launch one bounded one-GPU train smoke from `/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth`.
- Training config: `NUM_ENVS=128`, `HORIZON_LENGTH=32`, `MINIBATCH_SIZE=1024`, `CENTRAL_VALUE_MINIBATCH_SIZE=1024`, `MINI_EPOCHS=2`, `MAX_ITERATIONS=15`, `SAVE_FREQUENCY=1`, `DISTRIBUTED=False`, `MULTI_GPU=False`, `AUTO_RESUME=False`, `SELF_RELAUNCH=False`, `USE_CUDA_GRAPH=False`.
- Teacher/action config: `TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True`, alpha start/end `0.75/0.5`, `TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0`, `TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=160`, `TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=80.0`, phase start `0.0`, sharpness `1.0`, contact gate disabled, raw-policy comparison enabled.
- After training, fetch logs/checkpoint metadata and run bounded 520-step video evals from the resulting checkpoint at alpha `0.0`, `0.5`, `0.75`, and `1.0` with `NUM_ENVS=4`, success termination suppressed, per-env metrics, targeted videos/contact sheets where needed, and action-semantics comparison.

Validation:
- Local cheap checks passed before launch: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`; `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`.

Acceptance:
- Train wrapper exits cleanly and writes an epoch-15 checkpoint without relying on episode-return suffixes.
- Eval artifacts include report, metrics JSON/CSV, trace plot, contact sheet, full video, consistency JSON, and action-semantics tables.
- Target unsafe remains `0`.
- A pass requires alpha `0.0` or alpha `0.5` to show visible contact/lift improvement over the current alpha `0.0` failure, not just scheduler success.
- If policy-only/low-alpha remains dead, stop PPO handoff tweaks and move to explicit on-policy dataset aggregation / DAgger-style BC from policy-reached states.

## 2026-06-11T18:30:00-07:00 - BC-initialized PPO handoff smoke launch

Version Control:
- implementation_commit: `ea49425766fabed234845789c6cabb45b9cfa93c`
- branch: `codex/franka-cube-trajectory-tracking`
- push: pushed to origin.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `ea49425766fabed234845789c6cabb45b9cfa93c`, clean after git-bundle deploy.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bcinit_tfppo15 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_bcinit_tfppo15_20260611_183000,NPROC_PER_NODE=1,NUM_NODES=1,DISTRIBUTED=False,MULTI_GPU=False,NUM_ENVS=128,HORIZON_LENGTH=32,MINIBATCH_SIZE=1024,CENTRAL_VALUE_MINIBATCH_SIZE=1024,MINI_EPOCHS=2,MAX_ITERATIONS=15,SAVE_FREQUENCY=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_WEIGHT=80.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_PHASE_START=0.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_SHARPNESS=1.0,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_USE_CONTACT_GATE=False,TRAJECTORY_TRACKING_ACTION_ALIGNMENT_COMPARE_RAW_POLICY=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ENABLED=True,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_START=0.75,TRAJECTORY_TRACKING_TEACHER_FORCE_ALPHA_END=0.5,TRAJECTORY_TRACKING_TEACHER_FORCE_PHASE_END=1.0,TRAJECTORY_TRACKING_TEACHER_FORCE_ANNEAL_STEPS=160,LEARNING_RATE=0.00005,CENTRAL_VALUE_LEARNING_RATE=0.00005,KL_THRESHOLD=0.006,ENTROPY_COEF=0.0001 cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1027954`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_bcinit_tfppo15_20260611_183000`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027954.out`

Next:
- Monitor job `1027954` through completion.
- Fetch stdout/logs and checkpoint listing immediately after completion.
- Do not launch eval until the smoke checkpoint and config are verified.

## 2026-06-11T18:31:00-07:00 - BC-initialized PPO handoff smoke result and selector launch

Train Result:
- job_id: `1027954`
- status: completed `0:0`, elapsed `00:00:52`, node `pool0-00030`.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_20260611_183000`
- local_log: `cluster_results/l401/slurm_logs/teacher_8gpu_1027954.out`
- restored checkpoint epoch: `10`.
- completed epochs: `11/15`, `12/15`, `13/15`, `14/15`, `15/15`.
- final checkpoint: `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_bcinit_tfppo15_20260611_183000/nn/last_dextrah_franka_cube_traj_tracking_ep_15_rew_829.6681.pth`
- note: reward suffix is not a behavior verdict; this is only a bounded continuation checkpoint for eval.

Selector Eval Launch:
- alpha `0.0`: job `1027959`, run `franka_cube_traj_tracking_bcinit_tfppo15_select_a000_520_20260611_183100`.
- alpha `0.5`: job `1027960`, run `franka_cube_traj_tracking_bcinit_tfppo15_select_a050_520_20260611_183100`.
- alpha `0.75`: job `1027961`, run `franka_cube_traj_tracking_bcinit_tfppo15_select_a075_520_20260611_183100`.
- alpha `1.0`: job `1027962`, run `franka_cube_traj_tracking_bcinit_tfppo15_select_a100_520_20260611_183100`.
- shared eval config: checkpoint above, `NUM_ENVS=4`, `NUM_STEPS=520`, no video, deterministic, success termination suppressed, seed `64`, target reference still `curobo_validated=false`, action-alignment weight `80.0`, teacher alpha fixed per run with phase end `1.0`.

Next:
- Fetch selector outputs when complete.
- Use per-env success/lift fields to launch targeted viewer videos for alpha `0.0`, `0.5`, `0.75`, and `1.0`.

## 2026-06-11T18:38:00-07:00 - BC-initialized PPO handoff eval result

Result:
- status: negative for learned handoff; no PPO scale-up.
- train job: `1027954`, completed `0:0`, final checkpoint `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_bcinit_tfppo15_20260611_183000/nn/last_dextrah_franka_cube_traj_tracking_ep_15_rew_829.6681.pth`.
- selector jobs: alpha `0.0/0.5/0.75/1.0` jobs `1027959`/`1027960`/`1027961`/`1027962`, all completed `0:0`.
- targeted viewer jobs: alpha `0.0/0.5/0.75/1.0` jobs `1027963`/`1027964`/`1027965`/`1027966`, all completed `0:0`.
- comparison report: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838/report.md`
- comparison report URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838/report.md`
- comparison plot: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838/comparison_plot.png`
- comparison plot URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838/comparison_plot.png`
- action-semantics report: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838_action_semantics/action_semantics_report.md`
- action-semantics plot: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_comparison_20260611_1838_action_semantics/action_semantics_plot.png`

Viewer artifacts:
- post-PPO alpha `0.0` env0 report/sheet/video: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a000_env0_520_20260611_183400_artifacts/report.md`, `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a000_env0_520_20260611_183400_artifacts/video_contact_sheet.png`, `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a000_env0_520_20260611_183400/videos/bcinit-tfppo15-a000-env0-step-0.mp4`.
- post-PPO alpha `0.5` env0 report/sheet/video: `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a050_env0_520_20260611_183400_artifacts/report.md`, `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a050_env0_520_20260611_183400_artifacts/video_contact_sheet.png`, `cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a050_env0_520_20260611_183400/videos/bcinit-tfppo15-a050-env0-step-0.mp4`.
- post-PPO alpha `0.75` env0 sheet URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a075_env0_520_20260611_183400_artifacts/video_contact_sheet.png`
- post-PPO alpha `0.75` env0 video URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a075_env0_520_20260611_183400/videos/bcinit-tfppo15-a075-env0-step-0.mp4`
- post-PPO alpha `1.0` env1 sheet URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a100_env1_520_20260611_183400_artifacts/video_contact_sheet.png`
- post-PPO alpha `1.0` env1 video URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bcinit_tfppo15_vis_a100_env1_520_20260611_183400/videos/bcinit-tfppo15-a100-env1-step-0.mp4`

Metrics:
- pre-PPO BC alpha `0.75`: success `2/4`, final success `0.50`, max lift `0.0968 m`, raw/reference L2 mean `0.0519`, target unsafe max `0`.
- post-PPO alpha `0.0`: success `0/4`, max lift `0.0 m`, raw/reference L2 mean `1.6138`, target unsafe max `0`.
- post-PPO alpha `0.5`: success `0/4`, max lift `0.0009 m`, raw/reference L2 mean `0.4044`, target unsafe max `0`.
- post-PPO alpha `0.75`: success `0/4`, max lift `0.0015 m`, raw/reference L2 mean `0.2528`, target unsafe max `0`.
- post-PPO alpha `1.0`: success `3/4`, final success `0.75`, max lift `0.1444 m`, target unsafe max `0`.
- MP4 validation: all four post-PPO videos are `1280x720`, `520` frames, `8.666667 s`, `60 fps`.

Visual diagnosis:
- Post-PPO alpha `0.75` approaches near the cube but ends above/away with no lift. It is a clear regression from the pre-PPO BC alpha `0.75` env2 success video.
- Post-PPO full-teacher alpha `1.0` still visibly grasps/lifts in env1. That keeps the reference/controller path viable and isolates the failure to learned low-alpha handoff.

Analysis:
- No concrete wrapper/config bug was found. The run used the intended epoch-15 checkpoint, fixed alpha evals, success termination suppression, per-env camera targeting, and target unsafe stayed `0`.
- The five PPO updates moved the policy away from the useful BC handoff manifold: alpha `0.75` dropped from `2/4` success to `0/4` even though alpha `1.0` remained `3/4`.
- Per the acceptance plan, stop PPO schedule tweaking. The next bounded step is explicit on-policy dataset aggregation / DAgger-style BC from policy-reached states.
- Reference caveat remains explicit: `curobo_validated=false`, source tag `graspgenx_curobo_60mm_export_pending_exact_validation`.

## 2026-06-11T18:39:00-07:00 - on-policy DAgger-style BC plan

Goal:
- Test whether supervised action imitation can recover low-alpha/policy-only behavior when trained on states actually reached by the failing policy, rather than only states from a reference-delta rollout.

Hypothesis:
- The all-7 BC actor overfits reference-rollout observations well, but low-alpha rollouts visit off-reference states. Labeling policy-reached states with the current `compute_reference_delta_actions()` should reduce raw/reference error on the failure manifold more directly than PPO reward shaping.

Implementation plan:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with a diagnostic collection action source:
  - `reference_delta` keeps the current behavior and remains default.
  - `policy` steps raw policy actions while still labeling each observation with `compute_reference_delta_actions()`.
  - `teacher_mix` steps `(1-alpha) * raw_policy + alpha * reference_delta` while labeling with reference actions.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to expose `COLLECTION_ACTION_SOURCE` and `COLLECTION_TEACHER_ALPHA`.
- Keep the model/action parameterization unchanged: 72-D observation, 7-D action, no phase observations, baseline task untouched.
- Cheap validation before launch: `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py` and `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`.

Bounded run plan:
- First run a small on-policy dataset/BC smoke from the pre-PPO all-7 BC checkpoint, not from the regressed PPO checkpoint:
  - `COLLECTION_ACTION_SOURCE=teacher_mix`, `COLLECTION_TEACHER_ALPHA=0.5`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`, `TRAIN_STEPS=400`, all 7 dims, one L40S GPU.
  - Optional follow-up only if the smoke lowers held-out error: repeat with `COLLECTION_ACTION_SOURCE=policy` to cover fully unassisted failure states.
- Evaluate resulting checkpoint with alpha `0.0`, `0.5`, `0.75`, and `1.0`, `NUM_ENVS=4`, `NUM_STEPS=520`, success termination suppressed, per-env success/lift fields, targeted videos/contact sheets, trace plots, action-semantics comparison, and train/eval consistency JSON.

Acceptance:
- Held-out action error decreases on the on-policy/teacher-mix dataset.
- Alpha `0.5` or alpha `0.75` shows visible contact/lift and nonzero final/ever success without target-safety regression.
- No PPO or long training scale-up until low-alpha video/metrics improve.

Implementation:
- Added `--collection_action_source {reference_delta,policy,teacher_mix}` to `dextrah_lab/rl_games/bc_reference_action_imitation.py`.
- Added `--collection_teacher_alpha` to blend raw policy and reference actions when collecting teacher-mix states.
- Labels remain `compute_reference_delta_actions()` for all collection modes; only the rollout state distribution changes.
- Dataset now records `applied_collection_actions`, `collection_action_source`, and `collection_teacher_alpha`.
- Extended `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` with `COLLECTION_ACTION_SOURCE` and `COLLECTION_TEACHER_ALPHA`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py`: passed.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`: passed.

## 2026-06-11T18:42:00-07:00 - teacher-mix DAgger BC launch

Version Control:
- implementation_commit: `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`
- branch: `codex/franka-cube-trajectory-tracking`
- push: pushed to origin.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`, clean after git-bundle deploy.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:35:00 --job-name=bc_dagger_tm05 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_tm05_20260611_184200,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00015,VALIDATION_FRACTION=0.2,LOSS_DIMS=0,1,2,3,4,5,6,EVAL_INTERVAL=25,SEED=65,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.5,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_ref_all7_20260611_181620/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- job_id: `1027967`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_tm05_20260611_184200`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027967.out`

Acceptance:
- `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `report.md`, dataset, and checkpoint are written.
- Report shows `collection_action_source=teacher_mix`, `collection_teacher_alpha=0.5`.
- Held-out all-dim error decreases materially before any eval launch.

## 2026-06-11T18:43:00-07:00 - teacher-mix DAgger BC relaunch

Result:
- job `1027967` was canceled deliberately before completion.
- root cause: launch used `LOSS_DIMS=0,1,2,3,4,5,6` inside Slurm `--export`; Slurm split the comma-separated value and the wrapper received `LOSS_DIMS=0`.
- interpretation: `1027967` is not a valid all-dimension DAgger BC run and must not be used as evidence.

Relaunch:
- job_id: `1027968`
- run_name: `franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300`
- command change: `LOSS_DIMS=all` to avoid `--export` comma parsing.
- wrapper echo verified: `LOSS_DIMS=all`, `COLLECTION_ACTION_SOURCE=teacher_mix`, `COLLECTION_TEACHER_ALPHA=0.5`.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027968.out`

## 2026-06-11T18:45:00-07:00 - teacher-mix DAgger BC result and selector launch

BC Result:
- job_id: `1027968`
- status: completed `0:0`, elapsed `00:00:59`, node `pool0-00030`.
- local_run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300`
- local_log: `cluster_results/l401/slurm_logs/bc_franka_cube_1027968.out`
- report URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300/report.md`
- loss plot URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300/bc_loss_plot.png`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300/nn/bc_reference_action_imitation.pth`
- collection: `teacher_mix`, teacher alpha `0.5`, labels still `compute_reference_delta_actions()`.
- loss dims: all seven dims `[0,1,2,3,4,5,6]`.

Supervised metrics:
- validation MSE: `0.002193 -> 0.000102`.
- validation L2: `0.109585 -> 0.019993`.
- validation close/up/gripper abs: `0.03185/0.01306/0.05379 -> 0.00418/0.00539/0.00683`.
- This passes the supervised gate and earns bounded eval, but it is not yet behavior evidence.

Selector Eval Launch:
- alpha `0.0`: job `1027969`, run `franka_cube_traj_tracking_bc_dagger_tm05_select_a000_520_20260611_184500`.
- alpha `0.5`: job `1027970`, run `franka_cube_traj_tracking_bc_dagger_tm05_select_a050_520_20260611_184500`.
- alpha `0.75`: job `1027971`, run `franka_cube_traj_tracking_bc_dagger_tm05_select_a075_520_20260611_184500`.
- alpha `1.0`: job `1027972`, run `franka_cube_traj_tracking_bc_dagger_tm05_select_a100_520_20260611_184500`.
- shared eval config: checkpoint above, `NUM_ENVS=4`, `NUM_STEPS=520`, no video, deterministic, success termination suppressed, seed `64`, target reference still `curobo_validated=false`, action-alignment weight `80.0`, fixed teacher alpha per run with phase end `1.0`.

## 2026-06-11T18:48:00-07:00 - teacher-mix DAgger selector result and video launch

Selector Result:
- alpha `0.0`, job `1027969`: success `0/4`, final success `0.0`, max lift `0.01825 m`, raw/reference L2 mean `1.1102`, target unsafe max `0`.
- alpha `0.5`, job `1027970`: success `1/4`, final success `0.25`, max lift `0.04931 m`, raw/reference L2 mean `0.1209`, target unsafe max `0`.
- alpha `0.75`, job `1027971`: success `1/4`, final success `0.25`, max lift `0.04799 m`, raw/reference L2 mean `0.0850`, target unsafe max `0`.
- alpha `1.0`, job `1027972`: success `3/4`, final success `0.75`, max lift `0.14441 m`, raw/reference L2 mean `0.0798`, target unsafe max `0`.

Analysis:
- This is the first low-alpha improvement after explicit on-policy/teacher-mix BC: alpha `0.5` and alpha `0.75` recover `1/4` final success where bcinit PPO had `0/4`.
- Policy-only alpha `0.0` still fails, so this is not ready for RL/PPO scale-up.
- Need targeted videos before claiming behavior improvement.

Targeted Video Launch:
- alpha `0.0`, env0 failure: job `1027973`, run `franka_cube_traj_tracking_bc_dagger_tm05_vis_a000_env0_520_20260611_184800`.
- alpha `0.5`, env1 success: job `1027974`, run `franka_cube_traj_tracking_bc_dagger_tm05_vis_a050_env1_520_20260611_184800`.
- alpha `0.75`, env2 success: job `1027975`, run `franka_cube_traj_tracking_bc_dagger_tm05_vis_a075_env2_520_20260611_184800`.
- alpha `1.0`, env1 full-teacher reference: job `1027976`, run `franka_cube_traj_tracking_bc_dagger_tm05_vis_a100_env1_520_20260611_184800`.

## 2026-06-11T18:55:00-07:00 - teacher-mix DAgger targeted visual result

Jobs / Fetch:
- jobs `1027973`, `1027974`, `1027975`, `1027976` all completed `0:0`.
- fetched full run dirs, logs, metrics, trace CSV/JSONL, and videos under `cluster_results/l401/`.
- video metadata for all four targeted MP4s: `1280x720`, `520` frames, `8.67 s`.

Targeted Visual Artifacts:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_comparison_20260611_1850/report.md`
- combined plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_comparison_20260611_1850/comparison_plot.png`
- action-semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_visual_action_semantics_20260611_1848/action_semantics_report.md`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_visual_action_semantics_20260611_1848/action_semantics_plot.png`

Per-run viewer URLs:
- alpha `0.0` env0 failure sheet/video/report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a000_env0_520_20260611_184800_artifacts/video_contact_sheet.png`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a000_env0_520_20260611_184800/videos/dagger-tm05-a000-env0-step-0.mp4`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a000_env0_520_20260611_184800_artifacts/report.md`
- alpha `0.5` env1 success sheet/video/report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a050_env1_520_20260611_184800_artifacts/video_contact_sheet.png`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a050_env1_520_20260611_184800/videos/dagger-tm05-a050-env1-step-0.mp4`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a050_env1_520_20260611_184800_artifacts/report.md`
- alpha `0.75` env2 success sheet/video/report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a075_env2_520_20260611_184800_artifacts/video_contact_sheet.png`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a075_env2_520_20260611_184800/videos/dagger-tm05-a075-env2-step-0.mp4`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a075_env2_520_20260611_184800_artifacts/report.md`
- alpha `1.0` env1 full-teacher context sheet/video/report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a100_env1_520_20260611_184800_artifacts/video_contact_sheet.png`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a100_env1_520_20260611_184800/videos/dagger-tm05-a100-env1-step-0.mp4`
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm05_vis_a100_env1_520_20260611_184800_artifacts/report.md`

Metrics / Interpretation:
- DAgger alpha `0.0`: success `0/4`, max lift `0.01825 m`, target unsafe max `0`; contact sheet shows policy-only still moves away and leaves the cube on the table.
- DAgger alpha `0.5`: success `1/4`, final success `0.25`, max lift `0.04931 m`, target unsafe max `0`; targeted env1 sheet/video visibly lifts the cube.
- DAgger alpha `0.75`: success `1/4`, final success `0.25`, max lift `0.04799 m`, target unsafe max `0`; targeted env2 sheet/video visibly lifts the cube.
- DAgger alpha `1.0`: success `3/4`, final success `0.75`, max lift `0.14441 m`, target unsafe max `0`; full-teacher reference ceiling remains stable.
- Comparison against previous checkpoints:
  - pre-PPO all-7 BC: alpha `0.75` was `2/4`, alpha `1.0` was `3/4`, alpha `0.0` failed.
  - post-PPO `bcinit_tfppo15`: alpha `0.0`, `0.5`, and `0.75` all failed; only alpha `1.0` stayed `3/4`.
  - teacher-mix DAgger BC partially recovers the low-alpha handoff: alpha `0.5` and `0.75` are now `1/4` with visible lift, but policy-only still fails.
- Action semantics:
  - alpha `0.0` still has large close/gripper/up errors in the close/lift/hold windows and no success.
  - alpha `0.5` and `0.75` reduce close/up/gripper mismatch enough for one environment to lift.
  - This supports continuing bounded DAgger/on-policy BC, not PPO schedule tweaking.

Next bounded plan:
- Do not launch full PPO/RL scale-up.
- Run one more DAgger/on-policy BC iteration from the current `1027968` checkpoint:
  - collect states with lower teacher support, preferably `COLLECTION_ACTION_SOURCE=teacher_mix`, `COLLECTION_TEACHER_ALPHA=0.25`, all seven dims, same `NUM_ENVS=8`, `COLLECTION_STEPS=520`, `TRAIN_STEPS=400`, one L40S GPU.
  - labels remain `reference_delta`; target reference remains `curobo_validated=false`.
  - acceptance before eval launch: held-out all-dim MSE/L2 and close/up/gripper abs decrease; checkpoint written at expected path.
- If that supervised gate passes, run the same alpha selector/eval bundle for `0.0`, `0.5`, `0.75`, and `1.0`, followed by targeted videos for the lowest-alpha success plus alpha `0.0` failure and alpha `1.0` context.
- Success criterion for considering any later PPO/RL handoff: low-alpha success rate improves beyond the current `1/4` without target-safety regression and with action semantics showing lower raw/reference error in close/lift/hold windows.

## 2026-06-11T18:59:00-07:00 - teacher-mix DAgger tm0.25 launch

Goal:
- Run the next bounded on-policy/DAgger BC collection with lower teacher support to test whether policy-reached states closer to low-alpha handoff improve raw-policy imitation.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- local_branch: `codex/franka-cube-trajectory-tracking`
- source_code_commit: `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`
- worklog_commit_before_launch: `8678afdc57add0ce97284816a63a03fecc2ed04f`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_commit/status: detached at `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`, clean.
- note: l401 `git fetch origin` failed with `Permission denied (publickey)`; `8678afd` differs from `114b86d` only in this worklog, so the launched source code is identical to the latest code-bearing commit.

Command / Job:
- job_id: `1027981`
- run_name: `franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:35:00 --job-name=bc_dagger_tm025 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00015,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=66,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.25,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm05_all_20260611_184300/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027981.out`

Acceptance:
- wrapper echoes `LOSS_DIMS=all`, `COLLECTION_ACTION_SOURCE=teacher_mix`, `COLLECTION_TEACHER_ALPHA=0.25`.
- `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `report.md`, dataset, and checkpoint are written.
- supervised held-out all-dim MSE/L2 and close/up/gripper abs decrease before any eval launch.
- if supervised gate passes, run selector evals alpha `0.0`, `0.5`, `0.75`, `1.0`; then targeted videos for alpha `0.0` failure, lowest-alpha success, and alpha `1.0` context.

## 2026-06-11T19:01:00-07:00 - teacher-mix DAgger tm0.25 supervised result

Result:
- job `1027981` completed `0:0`, elapsed `00:00:58`, node `pool0-00030`.
- fetched artifacts locally under `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900`.
- report URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/report.md`
- loss plot URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/bc_loss_plot.png`
- metrics URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`

Supervised Gate:
- collection: `teacher_mix`, teacher alpha `0.25`, labels still `reference_delta`, all seven action dims.
- samples: `4160`; obs/action dims: `72/7`.
- validation MSE: `0.018831 -> 0.000310`.
- validation L2: `0.224434 -> 0.036811`.
- validation close/up/gripper abs: `0.056997/0.051634/0.123230 -> 0.005735/0.012403/0.012235`.
- reference caveat preserved: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`, task-space waypoint transform, `do_not_transform_joint_trajectories`.

Decision:
- supervised gate passes; launch bounded selector evals alpha `0.0`, `0.5`, `0.75`, and `1.0`.
- This is still not behavior success. Selector metrics and targeted videos are required before any next DAgger iteration or PPO/RL consideration.

## 2026-06-11T19:02:00-07:00 - teacher-mix DAgger tm0.25 selector launch

Selector Eval Launch:
- alpha `0.0`: job `1027983`, run `franka_cube_traj_tracking_bc_dagger_tm025_select_a000_520_20260611_190200`.
- alpha `0.5`: job `1027984`, run `franka_cube_traj_tracking_bc_dagger_tm025_select_a050_520_20260611_190200`.
- alpha `0.75`: job `1027985`, run `franka_cube_traj_tracking_bc_dagger_tm025_select_a075_520_20260611_190200`.
- alpha `1.0`: job `1027986`, run `franka_cube_traj_tracking_bc_dagger_tm025_select_a100_520_20260611_190200`.
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- shared eval config: `NUM_ENVS=4`, `NUM_STEPS=520`, no video, deterministic, success termination suppressed, seed `64`, target reference still `curobo_validated=false`, action-alignment weight `80.0`, fixed teacher alpha per run with phase end `1.0`.

Acceptance:
- all four selectors complete with metrics/trace JSON/CSV, no NaNs/tracebacks, target unsafe max `0`.
- compare success/lift/raw-reference error against tm0.5 DAgger and bcinit PPO.
- if any low-alpha run improves beyond current `1/4`, launch targeted videos for alpha `0.0` failure, lowest-alpha success, and alpha `1.0` context.

## 2026-06-11T19:06:00-07:00 - teacher-mix DAgger tm0.25 selector result and targeted video launch

Selector Result:
- all selector jobs completed `0:0`; fetched metrics/traces locally under `cluster_results/l401/`.
- alpha `0.0`, job `1027983`: success `0/4`, final success `0.0`, max lift `0.0 m`, raw/reference L2 mean `1.3303`, target unsafe max `0`.
- alpha `0.5`, job `1027984`: success `3/4`, final success `0.75`, max lift `0.14125 m`, raw/reference L2 mean `0.2444`, applied/reference L2 mean `0.1247`, target unsafe max `0`; successful envs `0,2,3`.
- alpha `0.75`, job `1027985`: success `3/4`, final success `0.75`, max lift `0.14349 m`, raw/reference L2 mean `0.1741`, applied/reference L2 mean `0.0498`, target unsafe max `0`; successful envs `0,2,3`.
- alpha `1.0`, job `1027986`: success `3/4`, final success `0.75`, max lift `0.14441 m`, raw/reference L2 mean `0.1279`, applied/reference L2 mean `0.0140`, target unsafe max `0`; successful envs `1,2,3`.

Interpretation:
- tm0.25 is a clear behavior improvement over tm0.5: alpha `0.5` and `0.75` improved from `1/4` to `3/4` final success.
- Policy-only alpha `0.0` still fails, so this is still teacher-assisted trajectory tracking, not learned handoff readiness.
- Video validation is required before treating the selector result as visually reliable; no PPO scale-up.

Targeted Video Launch:
- alpha `0.0`, env0 failure: job `1027988`, run `franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600`.
- alpha `0.5`, env0 lowest-alpha success: job `1027989`, run `franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600`.
- alpha `0.75`, env0 success: job `1027990`, run `franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600`.
- alpha `1.0`, env1 full-teacher context: job `1027991`, run `franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600`.
- shared video config: `NUM_ENVS=4`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, deterministic, success termination suppressed, seed `64`, target reference still `curobo_validated=false`.

Next:
- Fetch all four video run dirs and logs after completion.
- Validate MP4 metadata with `ffprobe`, inspect contact sheets, summarize with reports/trace plots/action semantics, and open key artifacts with `viz-open`.
- Build final comparison report against tm0.5 DAgger and post-PPO `bcinit_tfppo15`.

## 2026-06-11T19:06:25-07:00 - teacher-mix DAgger tm0.25 targeted visual handoff

Result:
- jobs `1027988`-`1027991` all completed `0:0`.
- fetched all four run dirs, logs, metrics, traces, and videos locally under `cluster_results/l401/`.
- MP4 metadata validated for all four videos: `1280x720`, `520` frames, `8.666667 s`.
- train/eval consistency reports passed for all four targeted videos.
- target unsafe max remained `0` for all four videos; target clearance minimum remained above the configured threshold.
- generated per-run reports, trace plots, contact sheets, usable-frame contact sheets, action-semantics report/plot, and combined comparison report/plot.

Artifacts:
- comparison report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_comparison_20260611_1906/report.md`
- comparison plot:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_comparison_20260611_1906/comparison_plot.png`
- action-semantics report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_visual_action_semantics_20260611_1906/action_semantics_report.md`
- action-semantics plot:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_visual_action_semantics_20260611_1906/action_semantics_plot.png`

Targeted Videos:
- alpha `0.0`, job `1027988`, env0 failure:
  - result: success `0/4`, max lift `0.0 m`, final EE/finger distances `0.313/0.307 m`.
  - visual: policy-only still approaches/contacts poorly and leaves the cube on the table.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600/videos/dagger-tm025-a000-env0-step-0.mp4`
- alpha `0.5`, job `1027989`, env0 lowest-alpha success:
  - result: success `3/4`, max lift `0.14125 m`.
  - visual: targeted env0 contact sheet/video visibly lifts and holds the cube.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600/videos/dagger-tm025-a050-env0-step-0.mp4`
- alpha `0.75`, job `1027990`, env0 success:
  - result: success `3/4`, max lift `0.14349 m`.
  - visual: targeted env0 contact sheet/video visibly lifts and holds the cube.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600/videos/dagger-tm025-a075-env0-step-0.mp4`
- alpha `1.0`, job `1027991`, env1 teacher context:
  - result: success `3/4`, max lift `0.14441 m`.
  - visual: full-teacher/reference context remains stable; targeted env1 contact sheet/video visibly lifts and holds the cube.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600/videos/dagger-tm025-a100-env1-step-0.mp4`

Verdict:
- tm0.25 DAgger is the best Worker B result so far for teacher-assisted trajectory tracking.
- It improves low-alpha assisted behavior from tm0.5's `1/4` at alpha `0.5`/`0.75` to `3/4` at alpha `0.5`/`0.75`, and the targeted videos verify the lift is visually real rather than hidden in an unrecorded env.
- Policy-only alpha `0.0` still fails (`0/4`, no lift), so this is not a full PPO/RL scale-up gate.
- Reference caveat remains explicit: the compact task-space reference is still `curobo_validated=false` and should not be presented as a DEXTRAH-ready cuRobo-validated joint replay.

## 2026-06-11T19:08:28-07:00 - teacher-mix DAgger tm0.10 bounded plan

Goal:
- Reduce teacher reliance toward policy-only while preserving the tm0.25 visual success/safety result.
- First gate is supervised action-imitation only; do not launch selector/video jobs unless held-out action errors improve and the checkpoint is written.

Hypothesis:
- tm0.25 DAgger succeeded at alpha `0.5`/`0.75` because collecting from low-teacher policy-reached states made the raw policy more reference-like near the grasp/lift window.
- A smaller teacher-mix collection alpha `0.10` should expose more low-assistance states than tm0.25 while still preventing fully dead policy-only rollouts from dominating the dataset.
- Pure policy collection is not the first diagnostic because alpha `0.0` still has `0/4` success and no lift; collecting entirely from that regime risks mostly off-trajectory/no-contact states before we know whether lower-but-nonzero teacher support can keep useful contact/lift supervision.

Planned Change:
- No source changes for this step.
- Run one bounded BC/DAgger collection/training job from the tm0.25 checkpoint:
  - `COLLECTION_ACTION_SOURCE=teacher_mix`
  - `COLLECTION_TEACHER_ALPHA=0.10`
  - labels remain `reference_delta`
  - `LOSS_DIMS=all`
  - `NUM_ENVS=8`, `COLLECTION_STEPS=520`, `TRAIN_STEPS=400`, `BATCH_SIZE=1024`, `LEARNING_RATE=0.00015`
  - target reference remains `curobo_validated=false`.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- local_head_before_plan: `83867d1455467cb071dd6259c57b9d199bd13b11`
- remote_code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- remote_code_commit: `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`
- note: remote code remains at the latest code-bearing commit used for tm0.25; local commits after `114b86d` are worklog-only. Previous l401 `git fetch origin` failed with `Permission denied (publickey)`, so no source-code redeploy is required for this no-code-change job.

Validation Before Launch:
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`

Supervised Gate:
- Fetch `report.md`, `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, dataset metadata, and checkpoint.
- Pass condition: validation MSE/L2 and close/up/gripper abs errors decrease materially; no NaNs/tracebacks; checkpoint exists at `/results/bc/<run>/nn/bc_reference_action_imitation.pth`.
- If the gate passes, launch selector evals alpha `0.0`, `0.25`, `0.5`, `0.75`, `1.0` with metrics/traces first.
- If selector improves policy-only or lower-alpha behavior without target-unsafe regression, launch targeted videos/contact sheets for alpha `0.0` failure or improvement, lowest-alpha success, and alpha `1.0` context.

No-Scale Rule:
- No full PPO/RL scale-up in this iteration. Acceptance is any improvement in policy-only or lower-alpha success without target-unsafe regression, documented with metrics and visual artifacts.

## 2026-06-11T19:09:00-07:00 - teacher-mix DAgger tm0.10 supervised launch

Command / Job:
- job_id: `1027994`
- run_name: `franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:35:00 --job-name=bc_dagger_tm010 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00015,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=67,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1027994.out`
- local_plan_commit: `82f61a703977298e44309d561b8ea402fe14e24d`
- remote_code_commit: `114b86d7019b5ac59ecfbd8306798a5ce6ea0e39`

Expected Artifacts:
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/report.md`
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/bc_metrics.json`
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/bc_loss_curve.csv`
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/bc_loss_plot.png`
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/reference_action_dataset.pt`
- `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/nn/bc_reference_action_imitation.pth`

Next:
- Monitor job `1027994`.
- Fetch and inspect supervised artifacts before any selector eval launch.

## 2026-06-11T19:11:20-07:00 - teacher-mix DAgger tm0.10 supervised result

Result:
- job `1027994` completed `0:0`, elapsed `00:01:10`, node `pool0-00014`.
- fetched artifacts locally under `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900`.
- report URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/report.md`
- loss plot URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/bc_loss_plot.png`
- metrics URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/nn/bc_reference_action_imitation.pth`

Supervised Gate:
- collection: `teacher_mix`, teacher alpha `0.10`, labels still `reference_delta`, all seven action dims.
- samples: `4160`; obs/action dims: `72/7`.
- validation MSE: `0.103369 -> 0.001338`.
- validation L2: `0.628728 -> 0.079111`.
- validation close/up/gripper abs: `0.090374/0.217260/0.231394 -> 0.015930/0.015096/0.033793`.
- dataset applied collection means show lower assistance than tm0.25: `applied_collection_close_mean=0.1959`, `applied_collection_up_mean=0.1852`, `applied_collection_gripper_mean=0.2506`.
- reference caveat preserved: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`, task-space waypoint transform, `do_not_transform_joint_trajectories`.

Decision:
- supervised gate passes; launch metrics-only selector evals alpha `0.0`, `0.25`, `0.5`, `0.75`, and `1.0`.
- Do not launch targeted videos until selector metrics identify alpha `0.0` failure/improvement, lowest-alpha success, and alpha `1.0` context.

## 2026-06-11T19:12:00-07:00 - teacher-mix DAgger tm0.10 selector launch

Selector Eval Launch:
- alpha `0.0`: job `1027997`, run `franka_cube_traj_tracking_bc_dagger_tm010_select_a000_520_20260611_191200`.
- alpha `0.25`: job `1027998`, run `franka_cube_traj_tracking_bc_dagger_tm010_select_a025_520_20260611_191200`.
- alpha `0.5`: job `1027999`, run `franka_cube_traj_tracking_bc_dagger_tm010_select_a050_520_20260611_191200`.
- alpha `0.75`: job `1028000`, run `franka_cube_traj_tracking_bc_dagger_tm010_select_a075_520_20260611_191200`.
- alpha `1.0`: job `1028001`, run `franka_cube_traj_tracking_bc_dagger_tm010_select_a100_520_20260611_191200`.
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm010_all_20260611_190900/nn/bc_reference_action_imitation.pth`.
- shared eval config: `NUM_ENVS=4`, `NUM_STEPS=520`, no video, deterministic, success termination suppressed, seed `64`, target reference still `curobo_validated=false`, action-alignment weight `80.0`, fixed teacher alpha per run with phase end `1.0`.

Acceptance:
- all five selectors complete with metrics/trace JSON/CSV, no NaNs/tracebacks, target unsafe max `0`.
- compare success/lift/raw-reference error against tm0.25 and tm0.5.
- if lower-alpha success improves and target safety holds, launch targeted videos for alpha `0.0` failure/improvement, lowest-alpha success, and alpha `1.0` context.

## 2026-06-11T19:14:00-07:00 - teacher-mix DAgger tm0.10 selector result and minimal diagnostic video launch

Selector Result:
- all selector jobs completed `0:0`; fetched metrics/traces locally under `cluster_results/l401/`.
- alpha `0.0`, job `1027997`: success `0/4`, final success `0.0`, max lift `0.0 m`, raw/reference L2 mean `1.7608`, target unsafe max `0`.
- alpha `0.25`, job `1027998`: success `0/4`, final success `0.0`, max lift `0.0 m`, raw/reference L2 mean `1.2012`, target unsafe max `0`.
- alpha `0.5`, job `1027999`: success `0/4`, final success `0.0`, max lift `0.00084 m`, raw/reference L2 mean `0.5770`, target unsafe max `0`.
- alpha `0.75`, job `1028000`: success `1/4`, final success `0.25`, max lift `0.17736 m`, raw/reference L2 mean `0.5692`, target unsafe max `0`; successful env is env1.
- alpha `1.0`, job `1028001`: success `3/4`, final success `0.75`, max lift `0.19264 m`, raw/reference L2 mean `0.5460`, target unsafe max `0`; successful envs are env1/env2/env3.
- target clearance min stayed `0.065114 m` for all selector runs.
- action-semantics artifacts:
  - report: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_selector_action_semantics_20260611_1912/action_semantics_report.md`
  - plot: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_selector_action_semantics_20260611_1912/action_semantics_plot.png`

Comparison:
- tm0.10 is worse than tm0.25 at low teacher assistance:
  - tm0.25 alpha `0.5`/`0.75`: `3/4` and `3/4` final success.
  - tm0.10 alpha `0.5`/`0.75`: `0/4` and `1/4` final success.
- tm0.10 also underperforms tm0.5 at alpha `0.5`/`0.75` (`0/4` and `1/4` vs tm0.5 `1/4` and `1/4`), and only matches the `3/4` alpha `1.0` teacher ceiling.
- The supervised tm0.10 loss improved strongly within-run, but final held-out L2 (`0.0791`) was worse than tm0.25 (`~0.0368`), and rollout behavior confirms that this matters.

Decision:
- tm0.10 is not an improvement gate and should not replace tm0.25.
- Do not launch broad tm0.10 videos or any PPO/RL scale-up.
- Minimal targeted diagnostic videos were launched only to make the regression inspectable:
  - alpha `0.0` env0 failure: job `1028002`, run `franka_cube_traj_tracking_bc_dagger_tm010_vis_a000_env0_520_20260611_191500`.
  - alpha `0.75` env1 lowest-alpha success: job `1028003`, run `franka_cube_traj_tracking_bc_dagger_tm010_vis_a075_env1_520_20260611_191500`.
  - alpha `1.0` env1 teacher context: job `1028004`, run `franka_cube_traj_tracking_bc_dagger_tm010_vis_a100_env1_520_20260611_191500`.

Next Bounded Adjustment Proposal:
- Keep tm0.25 as the current best checkpoint.
- Next candidate should preserve tm0.25 successful-state coverage while adding low-assistance exposure, e.g. mixed/rehearsal BC with a retained tm0.25 dataset plus a smaller low-alpha collection, rather than replacing the dataset entirely with tm0.10 states.
- Hypothesis: tm0.10 collection over-weighted lower-assistance states that were harder/off-distribution and lost the useful tm0.25 successful grasp/lift manifold; rehearsal should reduce forgetting while still nudging policy-only behavior.

## 2026-06-11T19:20:00-07:00 - teacher-mix DAgger tm0.10 targeted visual handoff

Result:
- targeted diagnostic video jobs `1028002`-`1028004` all completed `0:0`.
- fetched all three run dirs, logs, metrics, traces, and videos locally under `cluster_results/l401/`.
- MP4 metadata validated for all three videos: `1280x720`, `520` frames, `8.666667 s`.
- generated per-run reports, trace plots, original contact sheets, and cleaner usable-frame contact sheets that skip the black frame `0`.
- train/eval consistency passed for all three targeted videos.
- target unsafe max remained `0` for all three targeted videos; target clearance min stayed `0.065114 m`.
- generated final tm0.10 comparison report/CSV/plot against tm0.25, tm0.5, and the post-PPO `bcinit_tfppo15` selector context.

Artifacts:
- comparison report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_comparison_20260611_1915/report.md`
- comparison plot:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_comparison_20260611_1915/comparison_plot.png`
- selector action-semantics report:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_selector_action_semantics_20260611_1912/action_semantics_report.md`
- selector action-semantics plot:
  - `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_selector_action_semantics_20260611_1912/action_semantics_plot.png`

Targeted Videos:
- alpha `0.0`, job `1028002`, env0 failure:
  - result: success `0/4`, max lift `0.0 m`, final EE/finger distances `0.389/0.427 m`.
  - visual: cube remains on table; policy-only still drifts/fails and does not recover contact/lift.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a000_env0_520_20260611_191500_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a000_env0_520_20260611_191500_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a000_env0_520_20260611_191500/videos/dagger-tm010-a000-env0-step-0.mp4`
- alpha `0.75`, job `1028003`, env1 lowest-alpha visible success:
  - result: success `1/4`, final success `0.25`, mean lift max in the targeted video run `0.04434 m`; selector max lift for the same alpha was `0.17736 m`.
  - visual: targeted env1 visibly contacts/lifts by the end, but the aggregate result is only `1/4`, so this is a regression versus tm0.25.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a075_env1_520_20260611_191500_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a075_env1_520_20260611_191500_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a075_env1_520_20260611_191500/videos/dagger-tm010-a075-env1-step-0.mp4`
- alpha `1.0`, job `1028004`, env1 full-teacher context:
  - result: success `3/4`, final success `0.75`, max lift `0.14441 m`.
  - visual: teacher/reference path remains viable and visibly lifts/holds in the targeted successful env.
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a100_env1_520_20260611_191500_artifacts/report.md`
  - contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a100_env1_520_20260611_191500_artifacts/usable_frame_contact_sheet.png`
  - video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm010_vis_a100_env1_520_20260611_191500/videos/dagger-tm010-a100-env1-step-0.mp4`

Verdict:
- tm0.10 is not an improvement over tm0.25. It regresses low-teacher behavior from tm0.25's alpha `0.5`/`0.75` `3/4` final success to tm0.10's `0/4` and `1/4`.
- The lower-alpha targeted visual does show a real env1 lift at alpha `0.75`, but the aggregate `1/4` result is not a scale-up gate.
- Keep tm0.25 as the best Worker B checkpoint for teacher-assisted trajectory tracking.
- Policy-only alpha `0.0` still fails, so no full PPO/RL scale-up.
- Reference caveat remains explicit: compact task-space reference is still `curobo_validated=false` and should not be described as DEXTRAH-ready cuRobo-validated joint replay.

Next Bounded Adjustment Proposal:
- Do not continue pure lower-alpha replacement collection.
- Proposed next small trainability step is mixed/rehearsal BC:
  - keep tm0.25 successful-state coverage as a retained dataset component;
  - add a smaller low-alpha (`0.10` or mixed `0.0/0.10/0.25`) collection component;
  - train on the combined dataset with all seven action dims and explicit per-dataset loss/validation reporting;
  - gate on selector alpha `0.0/0.25/0.5/0.75/1.0` before targeted videos.
- Acceptance for the next step remains improvement in policy-only or lower-alpha success without target-unsafe regression, with viewer-ready reports, plots, videos/contact sheets, and train/eval consistency JSON.

## 2026-06-11T19:27:00-07:00 - mixed/rehearsal BC bounded plan

Goal:
- Preserve tm0.25's successful-state coverage while adding lower-teacher exposure, then test whether the combined dataset improves policy-only or lower-alpha selector behavior without target-safety regression.

Hypothesis:
- tm0.10 regressed because replacing the dataset with mostly harder/lower-teacher states lost the tm0.25 successful grasp/lift manifold.
- A rehearsal run that combines retained tm0.25 samples with a fresh low-teacher (`teacher_mix`, alpha `0.10`) collection should reduce forgetting while still nudging the raw policy toward lower assistance.

Planned Change:
- Add minimal combined-dataset support to `dextrah_lab/rl_games/bc_reference_action_imitation.py`:
  - load one or more `reference_action_dataset.pt` rehearsal files;
  - concatenate their `obs` and `reference_actions` with the freshly collected dataset;
  - preserve source labels (`current_alpha010`, `tm025_rehearsal`) for explicit per-dataset train/val metrics;
  - save combined source metadata in `bc_metrics.json` and `reference_action_dataset.pt`.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` with pass-through env vars for rehearsal dataset paths/names.
- Keep all seven action dims (`LOSS_DIMS=all`).
- Keep the compact task-space reference caveat explicit: `curobo_validated=false`, task-space waypoint transform, no joint-trajectory replay.
- Keep old `actionscale-rewinf-diag-video480-step-0.mp4` labeled obsolete failed diagnostic; it is not current evidence.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit_before_plan: `8e17bbeedd006f08090b596bd10320098791496c`
- changed_files_planned:
  - `dextrah_lab/rl_games/bc_reference_action_imitation.py`
  - `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- commit and push before l401 launch; update agent-owned l401 worktree to the exact commit if remote Git auth allows. If remote fetch remains blocked, record that blocker and only use the already-deployed code if no source change is required; otherwise do not silently launch stale code.

Planned Supervised Job:
- run name: `franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_<timestamp>`.
- input checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- fresh collection: `COLLECTION_ACTION_SOURCE=teacher_mix`, `COLLECTION_TEACHER_ALPHA=0.10`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`.
- rehearsal dataset: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt`.
- training: `TRAIN_STEPS=400`, `BATCH_SIZE=1024`, `LEARNING_RATE=0.00015`, `VALIDATION_FRACTION=0.2`, `LOSS_DIMS=all`.

Supervised Gate:
- Fetch/open `report.md`, `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, combined dataset metadata, and checkpoint.
- Required: no traceback/NaN; checkpoint exists; global held-out L2 improves materially; per-source validation metrics are reported for both current alpha `0.10` and tm0.25 rehearsal; close/up/gripper held-out errors remain in the tm0.25/tm0.10 range or better.

Selector Gate If Supervised Passes:
- Eval selector alphas `0.0`, `0.25`, `0.5`, `0.75`, `1.0`, metrics/traces first, no videos initially.
- Acceptance: any improvement in policy-only or lower-alpha success over tm0.25/tm0.10 without target unsafe regression. If selector improves, launch targeted videos/contact sheets only for alpha `0.0` failure/improvement, lowest-alpha success, and alpha `1.0` context.
- No full PPO/RL scale-up in this iteration.

## 2026-06-11T19:31:40-07:00 - mixed/rehearsal BC supervised launch

Implementation:
- changed `dextrah_lab/rl_games/bc_reference_action_imitation.py` to support one or more rehearsal datasets plus per-source train/val metrics.
- changed `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass `REHEARSAL_DATASET_PATHS` and `REHEARSAL_DATASET_NAMES`.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
  - `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`
- implementation commit: `b5e7b34c4be7cb6fd740b98828704d1629fa2869` (`Add rehearsal BC dataset support`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- l401 GitHub fetch remains blocked by `Permission denied (publickey)`, so I used an agent-owned bare Git mirror at `/lustre/fsw/portfolios/nvr/users/lzha/src/git/DEXTRAH-franka-cube-traj-tracking.git` and detached the agent worktree at `b5e7b34c4be7cb6fd740b98828704d1629fa2869`.
- remote code path: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`.

Command / Job:
- job_id: `1028053`
- run_name: `franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_rehearsal --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00015,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=69,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028053.out`
- expected artifacts:
  - `report.md`
  - `bc_metrics.json`
  - `bc_loss_curve.csv`
  - `bc_loss_plot.png`
  - `reference_action_dataset.pt`
  - `nn/bc_reference_action_imitation.pth`

Monitor Plan:
- Inspect scheduler state and log, then fetch artifacts once complete.
- Gate on supervised metrics before selector evals; do not launch videos or PPO/RL scale-up from scheduler success alone.

## 2026-06-11T19:39:38-07:00 - mixed/rehearsal BC supervised result

Result:
- job `1028053` completed `0:0`, elapsed `00:01:12`, node `pool0-00006`.
- fetched log and artifacts locally:
  - run dir: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140`
  - log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028053.out`
- generated/fetched artifacts:
  - report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140/report.md`
  - loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140/bc_loss_plot.png`
  - metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140/bc_metrics.json`
  - checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140/nn/bc_reference_action_imitation.pth`
  - combined dataset: `/results/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_tm025_tm010_all_20260611_193140/reference_action_dataset.pt`

Supervised Gate Metrics:
- dataset: `8320` total samples = `4160` fresh `current_teacher_mix_alpha0p10` + `4160` `tm025_rehearsal`.
- global val L2: `0.437874 -> 0.094008`.
- global val MSE: `0.081238 -> 0.002044`.
- global val close/up/gripper abs: `0.065633/0.139325/0.187060 -> 0.023542/0.018783/0.044337`.
- fresh alpha `0.10` source val L2: `0.815697 -> 0.115862`.
- fresh alpha `0.10` source val close/up/gripper abs: `0.121326/0.259713/0.350414 -> 0.032686/0.018308/0.060443`.
- tm0.25 rehearsal val L2 degraded: `0.035676 -> 0.070744`.
- tm0.25 rehearsal val close/up/gripper abs degraded: `0.006348/0.011170/0.013168 -> 0.013807/0.019289/0.027192`.
- reference caveat remains: `curobo_validated=false`.

Verdict:
- supervised gate failed / ambiguous negative.
- The combined loss improves from the mixed initial checkpoint, but the final global val L2 `0.094008` is worse than tm0.10 (`~0.079`) and much worse than tm0.25 (`~0.0368`).
- The current low-teacher source remains worse than the previous tm0.10 held-out result, and the tm0.25 rehearsal source is clearly damaged.
- This does not justify launching the broad alpha selector sweep as an improvement gate.
- No selector jobs, videos, PPO, or RL scale-up launched from this checkpoint.

Analysis:
- Equal-size rehearsal alone was not enough to preserve tm0.25 successful-state behavior under 400 full-network AdamW updates at `1.5e-4`.
- The optimization moved the policy toward the harder alpha `0.10` source but partially forgot the tm0.25 manifold that was producing the best low-alpha visual success.
- A selector from this checkpoint would be diagnostic only, not a gate. I am not launching it automatically because the supervised metric gate is worse than both relevant baselines.

Next Bounded Adjustment Proposal:
- Keep tm0.25 as the current best checkpoint.
- Next trainability experiment should be analysis/adjustment before eval scale:
  - add source-balanced minibatches and/or explicit source loss weights favoring tm0.25 rehearsal;
  - use lower learning rate or early stopping on tm0.25 rehearsal validation degradation;
  - optionally freeze lower actor layers or run a shorter update budget to prevent forgetting;
  - report per-source metrics as the primary gate before any selector eval.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence and should not be compared against the current best tm0.25/DAgger artifacts.

## 2026-06-11T19:48:00-07:00 - source-balanced rehearsal BC bounded plan

Goal:
- Address the `1028053` failure mode before any rollout: improve the fresh alpha `0.10` source while preserving tm0.25 rehearsal validation near its initialization baseline.

Hypothesis:
- `1028053` used equal-size rehearsal but unconstrained random minibatches and a single unweighted MSE objective for 400 full-network updates at `1.5e-4`.
- This optimized toward the harder alpha `0.10` states and partially forgot the tm0.25 source.
- Source-balanced minibatches, rehearsal-favoring source weights, a lower learning rate, and best-checkpoint selection by a source-aware validation score should reduce forgetting while still improving the current alpha `0.10` source.

Planned Change:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with supervised-only controls:
  - `--source_batch_mode=random|balanced`, where balanced samples each source every minibatch.
  - `--source_loss_weights` to weight per-source MSE terms, e.g. `current_teacher_mix_alpha0p10=1,tm025_rehearsal=3`.
  - `--best_score_weights` to choose the saved checkpoint by a weighted validation score, e.g. `val_source_current_teacher_mix_alpha0p10_l2=1,val_source_tm025_rehearsal_l2=3`.
  - `--early_stop_patience` to stop if the weighted score does not improve.
  - save/report the selected best step and score, not just the final step.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass the new knobs.
- Keep all seven action dims and the same compact reference (`curobo_validated=false`).

Planned Job If Validation Passes:
- run name: `franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_<timestamp>`.
- input checkpoint: tm0.25 BC checkpoint.
- fresh collection: teacher_mix alpha `0.10`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`.
- rehearsal dataset: tm0.25 `reference_action_dataset.pt`.
- training: all seven dims, `TRAIN_STEPS=400`, `BATCH_SIZE=1024`, lower `LEARNING_RATE=0.00005`.
- source controls:
  - `SOURCE_BATCH_MODE=balanced`
  - `SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1,tm025_rehearsal=3`
  - `BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1,val_source_tm025_rehearsal_l2=3`
  - `EARLY_STOP_PATIENCE=6`

Supervised Gate:
- no selector sweep unless this gate improves materially.
- Required evidence:
  - checkpoint/report/metrics exist and no NaNs/tracebacks.
  - tm0.25 rehearsal val L2 remains near baseline (`~0.0357`), target ceiling `<=0.045` preferred and `<=0.055` maximum for considering eval.
  - current alpha `0.10` source val L2 improves materially relative to its initial `~0.816` and ideally beats/approaches tm0.10 final (`~0.079`); if not, report the tradeoff instead of launching selectors.
  - global val L2 must not be worse than `1028053` (`0.094`) if considering any selector.
- No PPO/RL scale-up.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- commit/push; deploy exact commit to l401 agent worktree using the agent-owned bare mirror if GitHub SSH auth is still blocked.

## 2026-06-11T19:59:40-07:00 - source-balanced rehearsal BC launch correction

Attempt:
- implementation commit before correction: `fb8cda15e6e3f42349f0d50ad3a78d1335bc68fa`.
- submitted job `1028065` with run name `franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_195940`.
- I immediately noticed the source-weight and best-score maps were passed through Slurm `--export` using `__COMMA__` placeholders, but the parser did not yet decode that placeholder.
- Cancelled job `1028065` before it produced useful artifacts; Slurm state `CANCELLED`, elapsed `00:00:19`.

Fix:
- Update `_parse_float_map()` in `dextrah_lab/rl_games/bc_reference_action_imitation.py` to translate `__COMMA__` back to commas before parsing weight maps.
- Relaunch only after local validation, commit/push, and exact l401 deployment.

Cancellation Root Cause:
- Scheduler evidence: `sacct -j 1028065` reports `CANCELLED by 158351`, elapsed `00:00:19`, exit `0:0` for the job and `0:15` for the batch/step; `scontrol show job 1028065` reports `JobState=CANCELLED`, `Reason=None`, `ExitCode=0:15`.
- Log evidence: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028065.out` reached Isaac startup and printed the full `bc_command`, then Slurm killed the step at `2026-06-11T20:00:00`. It did not reach dataset collection, parser output, metrics, report writing, or a Python traceback.
- Interpretation: this was my manual cancellation after noticing the launch used `__COMMA__`-encoded maps before the parser supported that encoding. It was not a supervised result, not a scheduler/container failure, and not direct evidence that the parser failed at runtime.
- Validation of the fix: local parser check on the exact exported strings now returns `{'current_teacher_mix_alpha0p10': 1.0, 'tm025_rehearsal': 3.0}` and `{'val_source_current_teacher_mix_alpha0p10_l2': 1.0, 'val_source_tm025_rehearsal_l2': 3.0}`; the completed relaunch metrics also contain these decoded maps.

## 2026-06-11T20:01:12-07:00 - source-balanced rehearsal BC supervised launch

Implementation:
- implementation commit: `6054377cfbfd7c1de493e39892cdb1f1f4ed95b7` (`Handle Slurm weight map placeholders`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `6054377cfbfd7c1de493e39892cdb1f1f4ed95b7` via the agent-owned l401 bare Git mirror.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
  - `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`

Command / Job:
- job_id: `1028067`
- run_name: `franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_bal_reh --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00005,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=70,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1__COMMA__tm025_rehearsal=3,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1__COMMA__val_source_tm025_rehearsal_l2=3,EARLY_STOP_PATIENCE=6,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028067.out`

Acceptance:
- supervised-only gate. No selector/video/PPO launch unless this run materially improves per-source metrics.
- preserve tm0.25 rehearsal val L2 near baseline while improving current alpha `0.10` source.

## 2026-06-11T20:04:09-07:00 - source-balanced rehearsal BC supervised result

Job:
- job_id: `1028067`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:00`, node `pool0-00006`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028067.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028067.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112/report.md`
- loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112/bc_loss_plot.png`
- metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_cube_traj_tracking_bc_dagger_rehearsal_balanced_tm025_tm010_all_20260611_200112/reference_action_dataset.pt`

Configuration Evidence:
- `source_batch_mode=balanced`.
- decoded `source_loss_weights={'current_teacher_mix_alpha0p10': 1.0, 'tm025_rehearsal': 3.0}`.
- decoded `best_score_weights={'val_source_current_teacher_mix_alpha0p10_l2': 1.0, 'val_source_tm025_rehearsal_l2': 3.0}`.
- selected checkpoint step: `400`.
- selected score: `0.0818919986486435`.
- `early_stop_triggered=False`.
- reference caveat remains: compact reference is `curobo_validated=false`.

Supervised Metrics:
- global selected val L2: `0.104960`, worse than 1028053 (`0.094008`) and worse than tm0.10 (`~0.0791`) and tm0.25 (`~0.0368`).
- global selected val MSE: `0.002995`.
- current alpha `0.10` source val L2: `0.151430`, worse than 1028053 (`0.115862`).
- current alpha `0.10` source close/up/gripper abs: `0.032906/0.024288/0.063323`.
- tm0.25 rehearsal source val L2: `0.058713`, better than 1028053 (`0.070744`) but still above the maximum preservation gate (`<=0.055`) and preferred gate (`<=0.045`).
- tm0.25 rehearsal source close/up/gripper abs: `0.009048/0.018056/0.021938`.

Verdict:
- supervised gate failure.
- No selector sweep, no videos, no PPO, and no RL scale-up launched from this checkpoint.

Analysis:
- The weighted balanced objective did what its weights implied: it reduced tm0.25 forgetting compared with the unweighted 1028053 checkpoint (`0.058713` vs `0.070744` rehearsal L2), but only partially.
- That preservation came at a larger cost to the fresh low-teacher source: current alpha `0.10` val L2 worsened from 1028053's `0.115862` to `0.151430`, and global val L2 worsened from `0.094008` to `0.104960`.
- The likely tradeoff is conflicting source distributions. The tm0.25 policy manifold contains the current best teacher-assisted success behavior, while the alpha `0.10` collection exposes lower-assistance states where the input policy is farther from the reference. A 3x rehearsal weight and weighted validation score constrained updates enough to underfit the fresh alpha `0.10` labels without preserving tm0.25 below the evaluation gate.
- This result argues against broad selector/video rollout from the balanced checkpoint. The next bounded iteration should be supervised-only analysis of source conflict or a more conservative preservation method, such as distillation/regularization to the tm0.25 actor on rehearsal states, freezing part of the actor, or a two-stage/early-stop rule that hard-stops when tm0.25 rehearsal exceeds the preservation ceiling.

Active Jobs:
- `squeue -u lzha` shows no active l401 jobs for this worker at the time of this entry.

## 2026-06-11T20:30:14-07:00 - tm0.25 actor distillation bounded plan

Goal:
- Make one more bounded learned-handoff attempt that explicitly preserves tm0.25 behavior while fitting lower-teacher alpha `0.10` labels.
- Keep this supervised-only until metrics pass. No selector/video/PPO/RL launch from this attempt unless the supervised gate materially improves.

Hypothesis:
- Dataset mixing and source-weighting failed because tm0.25 rehearsal labels and low-teacher alpha `0.10` labels compete in the same reference-label MSE objective.
- The actual behavior to preserve is the tm0.25 actor manifold on tm0.25 successful-state observations, not just the reference labels in that dataset.
- A frozen-initial-actor distillation loss on tm0.25 rehearsal observations should preserve the current best teacher-assisted behavior more directly while allowing the label loss to focus on fresh lower-teacher alpha `0.10` observations.

Planned Change:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with diagnostic-only actor distillation controls:
  - `--distill_sources` selecting source names/slugs/ids to regularize, e.g. `tm025_rehearsal`.
  - `--distill_loss_weight` controlling an extra MSE loss to frozen initial actor outputs on those source observations.
  - `--distill_dims`, defaulting to the supervised action dims.
  - report distillation train/val errors and per-source distillation metrics in `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, and `report.md`.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass and echo the new knobs.
- The distillation target for this run is the input checkpoint loaded at startup, which will be the tm0.25 checkpoint.

Planned Job If Validation Passes:
- run name: `franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_<timestamp>`.
- input checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- fresh collection: teacher_mix alpha `0.10`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`.
- rehearsal dataset: tm0.25 `reference_action_dataset.pt`.
- training: all seven dims, `TRAIN_STEPS=400`, `BATCH_SIZE=1024`, `LEARNING_RATE=0.00005`.
- objective:
  - `SOURCE_BATCH_MODE=balanced`.
  - reference-label loss only on fresh alpha `0.10`: `SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1,tm025_rehearsal=0`.
  - actor distillation on tm0.25 source: `DISTILL_SOURCES=tm025_rehearsal`, `DISTILL_LOSS_WEIGHT=2.0`, `DISTILL_DIMS=all`.
  - checkpoint selection still uses supervised gate-oriented metrics: `BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1,val_source_tm025_rehearsal_l2=2`.

Supervised Gate:
- Preserve tm0.25 rehearsal val L2 near baseline: preferred `<=0.045`, hard ceiling `<=0.055`.
- Current alpha `0.10` source val L2 must improve materially relative to latest balanced run (`0.15143`) and ideally approach/beat previous tm0.10 (`~0.079`).
- Global val L2 should not regress relative to `1028053` (`0.094008`) if considering any rollout.
- If these fail, stop at report/metrics and do not launch selectors or videos.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- commit/push and deploy exact commit to the l401 agent-owned worktree via Git before any Slurm launch.

Notes:
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.
- Compact trajectory reference remains `curobo_validated=false`.

## 2026-06-11T21:20:00-07:00 - residual oracle analysis launch

Implementation:
- implementation commit: `f3e0618403da29559892aa5582045a04c68d7c6d` (`Add residual oracle gating diagnostics`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `f3e0618403da29559892aa5582045a04c68d7c6d`.
- remote deployment used the agent-owned bare Git mirror `/lustre/fsw/portfolios/nvr/users/lzha/src/git/DEXTRAH-franka-cube-traj-tracking.git` because l401 GitHub SSH fetch is unavailable.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py dextrah_lab/rl_games/residual_action_adapter.py`
  - `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`

Command / Job:
- job_id: `1028119`
- run_name: `franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:30:00 --job-name=bc_oracle --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=0,BATCH_SIZE=1024,LEARNING_RATE=0.00005,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=1,SEED=73,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1__COMMA__tm025_rehearsal=0,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1__COMMA__val_source_tm025_rehearsal_l2=3,EARLY_STOP_PATIENCE=0,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=64,RESIDUAL_MAX_ACTION=0.5,RESIDUAL_PRESERVE_SOURCES=tm025_rehearsal,RESIDUAL_PRESERVE_WEIGHT=50,RESIDUAL_L2_WEIGHT=0.001,RESIDUAL_GATE_ENABLED=False,SOURCE_PROBE_STEPS=200,SOURCE_PROBE_LR=0.01,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028119.out`

Acceptance:
- analysis-only; `TRAIN_STEPS=0`.
- Required artifacts: `report.md`, `bc_metrics.json`, `bc_loss_curve.csv`, `oracle_residual_source.csv`, `oracle_residual_dim.csv`, `oracle_residual_plot.png`, `bc_source_metric_plot.png`.
- No selector/video/PPO/RL launch from this job.

## 2026-06-11T21:22:05-07:00 - residual oracle analysis result

Job:
- job_id: `1028119`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:00`, node `pool0-00015`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028119.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028119.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/report.md`
- oracle residual plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/oracle_residual_plot.png`
- oracle source CSV: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/oracle_residual_source.csv`
- oracle dim CSV: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/oracle_residual_dim.csv`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/bc_metrics.json`
- source plot: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_20260611_212000/bc_source_metric_plot.png`

Oracle / Source-Probe Evidence:
- `TRAIN_STEPS=0`; selected step `0`.
- frozen-base current alpha `0.10` val L2: `0.566324`.
- frozen-base tm0.25 rehearsal val L2: `0.035376`.
- current alpha `0.10` oracle residual validation L2: mean `0.566324`, p95 `1.407616`, p99 `1.615753`, max `1.687153`.
- current alpha `0.10` residual clipping at `RESIDUAL_MAX_ACTION=0.5`: dim rate `0.076884`, sample rate `0.439141`.
- clipped-oracle achievable current alpha `0.10` val L2 with max `0.5`: `0.184034`, so max-action clipping alone explains part but not all of the gap to the `~0.079` target.
- dominant current-source dimensions: z abs p95 `1.148`, z clip rate `0.3508`; gripper abs p95 `1.156`, gripper clip rate `0.1778`.
- tm0.25 oracle residual validation L2: mean `0.035376`, p95 `0.081654`, p99 `0.113546`, max `0.220493`; clip rate `0`.
- source separability probe over observations: val accuracy `0.691106` vs val baseline `0.503606`; this is moderate but not perfect separability.

Decision:
- Oracle stats justify one bounded supervised-only gated/capacity residual attempt:
  - raise `RESIDUAL_MAX_ACTION` to `1.5` because current z/gripper p95 requirements exceed `0.5`;
  - increase residual head capacity;
  - enable observation gate because the source probe has nontrivial source signal;
  - preserve tm0.25 with residual-to-zero on tm0.25 rehearsal.
- This still does not authorize selector rollout, videos, PPO, or RL. A follow-up supervised job must pass gates first.

Planned Follow-Up:
- run name: `franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_<timestamp>`.
- use same fresh alpha `0.10` collection and tm0.25 rehearsal dataset.
- `RESIDUAL_ADAPTER_ENABLED=True`, `RESIDUAL_HIDDEN_DIM=256`, `RESIDUAL_MAX_ACTION=1.5`.
- `RESIDUAL_GATE_ENABLED=True`, `RESIDUAL_GATE_HIDDEN_DIM=128`, `RESIDUAL_GATE_BIAS_INIT=0.0`.
- keep base actor frozen and tm0.25 preserve source `tm025_rehearsal`.
- supervised gates remain: tm0.25 val L2 preferred `<=0.045`, hard `<=0.055`; current alpha `0.10` val L2 materially better than `0.15143` and ideally near `~0.079`; no rollout unless gates pass.

## 2026-06-11T21:25:00-07:00 - gated high-capacity residual supervised launch

Implementation:
- implementation/worklog commit: `c48b0ec17f3ed1291fe1b6352a961d78fe4cd251` (`Record residual oracle analysis`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `c48b0ec17f3ed1291fe1b6352a961d78fe4cd251`.

Command / Job:
- job_id: `1028122`
- run_name: `franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_resid_gate --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=800,BATCH_SIZE=1024,LEARNING_RATE=0.0001,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=74,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1__COMMA__tm025_rehearsal=0,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1__COMMA__val_source_tm025_rehearsal_l2=4,EARLY_STOP_PATIENCE=12,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=256,RESIDUAL_MAX_ACTION=1.5,RESIDUAL_PRESERVE_SOURCES=tm025_rehearsal,RESIDUAL_PRESERVE_WEIGHT=25,RESIDUAL_L2_WEIGHT=0.0005,RESIDUAL_GATE_ENABLED=True,RESIDUAL_GATE_HIDDEN_DIM=128,RESIDUAL_GATE_BIAS_INIT=0.0,SOURCE_PROBE_STEPS=200,SOURCE_PROBE_LR=0.01,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028122.out`

Acceptance:
- supervised-only.
- tm0.25 rehearsal val L2 preferred `<=0.045`, hard `<=0.055`.
- current alpha `0.10` val L2 must improve materially over residual `0.6875`, balanced `0.15143`, and ideally approach `~0.079`.
- global val L2 must not regress relative to `1028053` (`0.094008`) if considering selector rollout.
- gate/residual metrics must show tm0.25 residual near zero and no hidden full-base updates.
- No selector/video/PPO/RL launch unless this supervised gate passes.

## 2026-06-11T21:27:04-07:00 - gated high-capacity residual supervised result

Job:
- job_id: `1028122`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:01`, node `pool0-00030`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028122.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028122.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/report.md`
- source/gate plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_source_metric_plot.png`
- loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_loss_plot.png`
- oracle residual plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/oracle_residual_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_metrics.json`
- curve CSV: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_loss_curve.csv`
- oracle source CSV: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/oracle_residual_source.csv`
- oracle dim CSV: `cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/oracle_residual_dim.csv`

Configuration Evidence:
- residual base: frozen tm0.25 actor checkpoint.
- residual hidden dim / max action: `256 / 1.5`.
- residual gate enabled / hidden dim / bias init: `true / 128 / 0.0`.
- residual preserve source/weight: `tm025_rehearsal / 25`.
- residual L2 weight: `0.0005`.
- best-score weights: current alpha `0.10` val L2 weight `1`, tm0.25 rehearsal val L2 weight `4`.
- selected step: `800`; `early_stop_triggered=False`.
- reference caveat remains: compact reference is `curobo_validated=false`.

Supervised Metrics:
- current alpha `0.10` val L2: `0.388490`.
- tm0.25 rehearsal val L2: `0.039825`, which passes the preferred preservation gate `<=0.045`.
- global val L2: `0.213319`, worse than rollout consideration ceiling `0.094008`.
- current alpha `0.10` residual L2: `0.227570`; tm0.25 residual L2: `0.012442`.
- current alpha `0.10` gate mean: `0.555579`; tm0.25 gate mean: `0.144581`.
- current alpha `0.10` z/gripper abs errors: `0.293475 / 0.134768`.
- source probe val accuracy: `0.758413` vs baseline `0.502404`.

Verdict:
- supervised gate failure.
- No selector sweep, no videos, no PPO, and no RL scale-up launched from this checkpoint.

Analysis:
- The oracle analysis was correct that `RESIDUAL_MAX_ACTION=0.5` was a bottleneck: with max `1.5`, oracle clipping dropped to roughly `0.0193` sample rate on current validation.
- The gated residual learned a meaningful source-dependent gate and preserved tm0.25: current gate mean `0.556`, tm0.25 gate mean `0.145`, tm0.25 val L2 `0.039825`.
- However, the adapter still underfits the current alpha `0.10` source badly (`0.388490`), far above balanced `0.15143` and the target neighborhood `~0.079`. It improves over the frozen/current residual baseline (`0.566324` in this seed) but not enough to justify rollout.
- This suggests the remaining issue is not simple residual clipping. The lower-assistance alpha `0.10` states require a large corrective action that a preserved observation-gated residual cannot fit well without either stronger source conditioning, more data on the transition manifold, or a different handoff objective. The current evidence still leaves tm0.25 as B's best checkpoint for teacher-assisted trajectory tracking.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.

Active Jobs:
- No selector/video/PPO/RL jobs launched for this attempt.

## 2026-06-11T20:34:21-07:00 - tm0.25 actor distillation supervised launch

Implementation:
- implementation commit: `1e618c1f0ae5a985880313ffc89e014c1b85a708` (`Add tm025 actor distillation BC diagnostic`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `1e618c1f0ae5a985880313ffc89e014c1b85a708` via the agent-owned l401 bare Git mirror.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py`
  - `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`

Command / Job:
- job_id: `1028088`
- run_name: `franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_distill --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00005,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=71,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1__COMMA__tm025_rehearsal=0,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1__COMMA__val_source_tm025_rehearsal_l2=2,EARLY_STOP_PATIENCE=8,DISTILL_SOURCES=tm025_rehearsal,DISTILL_LOSS_WEIGHT=2.0,DISTILL_DIMS=all,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028088.out`

Acceptance:
- supervised-only gate. No selector/video/PPO launch unless this run materially improves per-source metrics.
- preserve tm0.25 rehearsal val L2 `<=0.055` hard ceiling, preferred `<=0.045`.
- current alpha `0.10` source val L2 must improve over latest balanced run `0.15143` and ideally approach/beat tm0.10 `~0.079`.
- global val L2 should not regress relative to `1028053` (`0.094008`) if considering rollout.

## 2026-06-11T20:36:10-07:00 - tm0.25 actor distillation supervised result

Job:
- job_id: `1028088`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:01`, node `pool0-00006`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028088.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028088.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/report.md`
- aggregate loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/bc_loss_plot.png`
- source metric plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/bc_source_metric_plot.png`
- metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_cube_traj_tracking_bc_dagger_distill_tm025_tm010_all_20260611_203421/reference_action_dataset.pt`

Configuration Evidence:
- `source_batch_mode=balanced`.
- reference-label source weights: `{'current_teacher_mix_alpha0p10': 1.0, 'tm025_rehearsal': 0.0}`.
- best-score weights: `{'val_source_current_teacher_mix_alpha0p10_l2': 1.0, 'val_source_tm025_rehearsal_l2': 2.0}`.
- distillation target: input checkpoint initial actor, i.e. the tm0.25 checkpoint for this launch.
- distillation sources: `['tm025_rehearsal']`.
- distillation loss weight: `2.0`.
- distillation dims: all 7 action dims.
- selected checkpoint step: `400`; `early_stop_triggered=False`.
- reference caveat remains: compact reference is `curobo_validated=false`.

Supervised Metrics:
- initial/current source val L2: `0.676034`; selected/current source val L2: `0.182791`.
- selected current alpha `0.10` source val L2 `0.182791` is worse than the latest balanced run (`0.15143`) and worse than 1028053 (`0.115862`), far from tm0.10 (`~0.079`).
- selected current alpha `0.10` close/up/gripper abs: `0.047545/0.046967/0.091194`.
- initial tm0.25 rehearsal val L2: `0.034867`; selected tm0.25 rehearsal val L2: `0.070334`.
- selected tm0.25 rehearsal val L2 `0.070334` fails the hard preservation ceiling `<=0.055` and is only similar to the earlier failed 1028053 rehearsal damage (`0.070744`).
- selected tm0.25 rehearsal close/up/gripper abs: `0.013872/0.018742/0.028762`.
- selected global val L2: `0.126292`, worse than 1028053 (`0.094008`).
- selected distillation val L2 to the frozen tm0.25 actor on tm0.25 rehearsal states: `0.058396`, so the regularizer did not preserve the initial actor closely enough at weight `2.0`.

Verdict:
- supervised gate failure.
- No selector sweep, no videos, no PPO, and no RL scale-up launched from this checkpoint.

Analysis:
- The distillation implementation and artifact wiring worked: metrics include distillation source errors and `bc_source_metric_plot.png` shows current-source, tm0.25 reference, and tm0.25 distillation curves.
- The actual optimization did not solve the source conflict. Label loss on fresh alpha `0.10` improved that source from its initial L2, but not enough; tm0.25 reference error and frozen-actor distillation error both drifted above the preservation gate.
- Compared with the weighted balanced run, this traded off in the wrong direction: worse current-source performance (`0.182791` vs `0.151430`) and worse tm0.25 preservation (`0.070334` vs `0.058713`).
- That suggests a simple additive distillation loss at weight `2.0` is not sufficient. The next attempt, if any, should not launch rollout first; it should either strengthen/diagnose preservation in supervised space only, or switch to a safer method such as freezing most actor layers, hard early stopping on tm0.25 validation ceiling, or a two-head/residual adapter approach that cannot overwrite the tm0.25 base behavior.
- tm0.25 remains the best B checkpoint; old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.

Active Jobs:
- No selector/video/PPO jobs launched for this attempt.

## 2026-06-11T22:12:48-07:00 - stage/alpha-conditioned selector metrics result and visual gate plan

Job Results:
- selector jobs `1028138`, `1028139`, `1028140`, `1028141`, and `1028142` all completed `0:0`; fetched metrics/traces/logs locally.
- local selector dirs:
  - alpha0.00: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_a000_520_20260611_220700`
  - alpha0.25: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_a025_520_20260611_220700`
  - alpha0.50: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_a050_520_20260611_220700`
  - alpha0.75: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_a075_520_20260611_220700`
  - alpha1.00: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_a100_520_20260611_220700`
- logs: `cluster_results/l401/slurm_logs/eval_franka_cube_1028138.out` through `cluster_results/l401/slurm_logs/eval_franka_cube_1028142.out`.

Artifacts:
- selector summary report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_summary_20260611_2207/report.md`
- selector summary plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_summary_20260611_2207/selector_summary_plot.png`
- selector summary CSV/JSON: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_summary_20260611_2207/summary.csv`, `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_summary_20260611_2207/summary.json`
- action-semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_action_semantics_20260611_2207/action_semantics_report.md`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_selector_action_semantics_20260611_2207/action_semantics_plot.png`

Metrics:
- alpha0.00: success ever `0/4`, final success `0.0`, max success `0.0`, max lift `0.015447 m`, target unsafe max `0`, clearance min `0.065114 m`, raw/ref L2 mean `1.572714`.
- alpha0.25: success ever `3/4`, final success `0.0`, max success `0.5`, max lift `0.082562 m`, target unsafe max `0`, clearance min `0.065114 m`, raw/ref L2 mean `0.273926`; successful envs `1/2/3`, last success steps `453/386/390`.
- alpha0.50: success ever `3/4`, final success `0.0`, max success `0.75`, max lift `0.099041 m`, target unsafe max `0`, clearance min `0.065114 m`, raw/ref L2 mean `0.074226`; successful envs `1/2/3`.
- alpha0.75: success ever `3/4`, final success `0.0`, max success `0.75`, max lift `0.100324 m`, target unsafe max `0`, clearance min `0.065114 m`, raw/ref L2 mean `0.034299`; successful envs `1/2/3`.
- alpha1.00: success ever `3/4`, final success `0.0`, max success `0.75`, max lift `0.101156 m`, target unsafe max `0`, clearance min `0.065114 m`, raw/ref L2 mean `0.020483`; successful envs `1/2/3`.
- Assisted final success is `0` because success triggers done/reset in the normal eval; this is a transient-lift/success result, not a final-hold success claim.

Verdict:
- The supervised stage/alpha checkpoint improves lower-assisted selector behavior: alpha `0.25` reaches transient success in `3/4` envs with target unsafe max `0`.
- Policy-only alpha `0.0` remains failed (`0/4`), so this is not a PPO/RL scale-up gate.
- The next bounded gate is visual sanity only: alpha `0.0` failure, alpha `0.25` lowest-alpha transient success, and alpha `1.0` context. Videos should target successful envs for assisted alphas because env0-only videos are known to be misleading.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed diagnostic evidence.

Next:
- Launch three short labeled video evals from the same stage/alpha checkpoint:
  - alpha0.00, env0 failure.
  - alpha0.25, env2 transient success window.
  - alpha1.00, env1 teacher-assisted context.
- Fetch videos/logs/metrics, validate mp4 metadata, generate reports/contact sheets, and record `viz-open` URLs before any further decision.
- No PPO/RL scale-up.

## 2026-06-11T22:14:00-07:00 - stage/alpha-conditioned targeted visual gate launch

Goal:
- Produce minimal visual sanity artifacts for the selector result: policy-only failure, lowest-alpha transient success, and alpha1 context.

Version Control:
- local_commit: `986b584cd0052de6308d750c7c202bf2a1a0ebc0`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `986b584cd0052de6308d750c7c202bf2a1a0ebc0`, clean.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/nn/bc_reference_action_imitation.pth`
- task/action source: `Dextrah-Franka-Cube-Grasp-Traj-Tracking` / `policy_reference_mix`
- num_envs/steps: `4 / 520`
- capture_video/video_length: `True / 520`
- seed: `73`
- cube randomization: `0.08`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`
- reference caveat: `curobo_validated=false`

Jobs:
- alpha0.00 failure: job `1028146`, run `franka_cube_traj_tracking_bc_stagealpha_vis_a000_env0_520_20260611_221400`, `CAMERA_ENV_INDEX=0`, `VIDEO_NAME_PREFIX=stg-a000-env0`.
- alpha0.25 lowest-alpha success candidate: job `1028147`, run `franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400`, `CAMERA_ENV_INDEX=2`, `VIDEO_NAME_PREFIX=stg-a025-env2`.
- alpha1.00 context: job `1028148`, run `franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400`, `CAMERA_ENV_INDEX=1`, `VIDEO_NAME_PREFIX=stg-a100-env1`.

Acceptance:
- Fetch logs/run dirs and inspect `metrics.json`, trace CSV/JSONL, train/eval consistency, video metadata/frame counts, contact sheets, and reports.
- Confirm target unsafe max stays `0`.
- Confirm whether alpha0.25 env2 visually shows the transient lift implied by selector metrics.
- No PPO/RL scale-up.

Active Jobs:
- `1028146`, `1028147`, `1028148`.

## 2026-06-11T22:20:00-07:00 - stage/alpha-conditioned targeted visual gate result

Job Results:
- alpha0.00 failure video job `1028146`: `COMPLETED 0:0`, elapsed `00:01:29`, node `pool0-00015`.
- alpha0.25 lowest-alpha success video job `1028147`: `COMPLETED 0:0`, elapsed `00:01:30`, node `pool0-00030`.
- alpha1.00 context video job `1028148`: `COMPLETED 0:0`, elapsed `00:01:40`, node `pool0-00017`.
- fetched run dirs and logs locally:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a000_env0_520_20260611_221400`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028146.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028147.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028148.out`

Artifact Bundle:
- combined visual-gate report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_visual_gate_20260611_2214/report.md`
- combined visual-gate CSV: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_visual_gate_20260611_2214/summary.csv`
- alpha0.00 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a000_env0_520_20260611_221400_artifacts/report.md`
- alpha0.00 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a000_env0_520_20260611_221400_artifacts/video_contact_sheet.png`
- alpha0.00 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a000_env0_520_20260611_221400/videos/stg-a000-env0-step-0.mp4`
- alpha0.25 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400_artifacts/report.md`
- alpha0.25 default contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400_artifacts/video_contact_sheet.png`
- alpha0.25 success-window contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400_artifacts/success_window_contact_sheet.png`
- alpha0.25 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a025_env2_520_20260611_221400/videos/stg-a025-env2-step-0.mp4`
- alpha1.00 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400_artifacts/report.md`
- alpha1.00 default contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400_artifacts/video_contact_sheet.png`
- alpha1.00 success-window contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400_artifacts/success_window_contact_sheet.png`
- alpha1.00 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_vis_a100_env1_520_20260611_221400/videos/stg-a100-env1-step-0.mp4`

Validation:
- `ffprobe` verified all three MP4s are `1280x720`, `520` frames, `8.666667s`, `60/1`.
- summarizer generated per-run `report.md`, `summary.json/csv`, `success_diagnostics.json/csv`, `success_window_trace.csv`, `train_eval_consistency.json`, `trajectory_trace_plot.png`, and `video_contact_sheet.png`.
- train/eval consistency artifact status is `train_config_unavailable` because no training env YAML was supplied for BC checkpoints; expected eval overrides are recorded, and real mismatch list is empty.
- reference caveat remains explicit: `curobo_validated=false`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`.

Metrics:
- alpha0.00 env0: success ever `0/4`, final success `0`, max success `0`, max lift `0.015447 m`, target unsafe max `0`, clearance min `0.065114 m`, final EE/finger distances `0.179766/0.209505 m`, raw/ref L2 mean `1.572714`.
- alpha0.25 env2: success ever `3/4`, final success `0`, max success `0.5`, max lift `0.082562 m`, target unsafe max `0`, clearance min `0.065114 m`, final EE/finger distances `0.144186/0.184688 m`, raw/ref L2 mean `0.273926`, done-after-success count `3`.
- alpha1.00 env1: success ever `3/4`, final success `0`, max success `0.75`, max lift `0.101156 m`, target unsafe max `0`, clearance min `0.065114 m`, final EE/finger distances `0.136633/0.177053 m`, raw/ref L2 mean `0.020483`, done-after-success count `3`.

Visual Diagnosis:
- alpha0.00 video/contact sheet shows the policy-only hand moves away/around the cube and never lifts. This remains the policy-only failure mode.
- alpha0.25 env2 success-window contact sheet visually confirms a real transient lift during the metric success window (`first_success_step=374`, `last_success_step=386` for camera env2), followed by cube back on the table after success termination/reset.
- alpha1.00 success-window contact sheet visually confirms the teacher/reference context also lifts during the success window (`first_success_step=381`, `last_success_step=393` for camera env1), then resets/drops by final frame.

Verdict:
- Stage/alpha-conditioned BC improves the assisted trajectory-tracking handoff: the lowest tested assisted alpha with visual success is now `0.25`, compared with tm0.25 DAgger's best verified low-alpha result at alpha `0.5`.
- This is positive for teacher-assisted trajectory tracking only. Policy-only alpha `0.0` remains failed, and final success is zero in assisted runs because normal success termination/reset occurs after transient lift.
- This is not a PPO/RL/full-scale gate. Next work should remain bounded and should either pursue no-reset/stability analysis for alpha0.25 or supervised policy-only improvement; do not launch PPO/RL scale-up from this evidence.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed diagnostic evidence.

Active Jobs:
- none for Worker B after jobs `1028146`-`1028148` completed.

## 2026-06-11T22:22:41-07:00 - policy-only stabilization handoff supervised plan

Goal:
- Stay supervised-only and test whether the successful assisted manifold can teach a policy-only/stabilization context without damaging alpha0.5/0.75/1.0 assisted behavior.

Hypothesis:
- The stage/alpha checkpoint improved alpha0.25 assisted behavior but still leaves alpha0 policy-only failed because context `teacher_alpha=0.0` was outside the supervised training support.
- A small derived handoff source can duplicate successful/lifted alpha0.5/0.75 assisted states and relabel their residual context to `teacher_alpha=0.0`, while labels remain the reference_delta action. This directly tests whether the same actor parameterization can fit policy-only stabilization/hold actions on states known to be physically reachable.
- If this supervised gate fails, the blocker is representation/source conflict rather than PPO exploration.

Planned Change:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with an optional derived handoff source:
  - select source ids/names from an existing dataset, initially alpha0.5 and alpha0.75 assisted sources;
  - filter by phase/lift/success window, initially `phase >= 0.55` and either success or lift over a small threshold;
  - duplicate selected samples as a new source with `teacher_alpha=0.0`;
  - record source/filter counts in `reference_action_dataset.pt`, `bc_metrics.json`, and `report.md`.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` with matching environment variables and command arguments.
- Keep the original baseline task and production `Dextrah-Franka-Cube-Grasp` untouched.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `a3a68c157cbf7308982fd3ac6d8922095fb3fdce`
- implementation_commit: pending
- owned worklog: `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/residual_action_adapter.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `git diff --check`

Supervised Gate:
- No selector/videos/PPO/RL until supervised metrics pass.
- Preserve assisted alpha0.5/0.75/1.0 validation L2 near the stage/alpha checkpoint (`~0.0929/0.0820/0.0663`); hard fail if materially worse than the stage-alpha visual-gate source metrics without a compensating handoff improvement.
- Derived alpha0 handoff source must reach low held-out action error and report enough selected samples to be meaningful; if sample count is tiny or labels conflict, stop with the report.
- Global val L2 should not regress relative to stage/alpha supervised (`~0.0805`) if considering any rollout.

If Supervised Gate Passes:
- Run selector metrics only for alpha `0.0/0.25/0.5/0.75/1.0`.
- Generate videos/contact sheets only for policy-only alpha0 failure/improvement, the lowest-alpha success/improvement, and alpha1 context.
- No PPO/RL scale-up.

## 2026-06-11T22:30:00-07:00 - policy-only stabilization handoff implementation checkpoint

Change:
- Added an optional derived handoff source to `dextrah_lab/rl_games/bc_reference_action_imitation.py`.
- The derived source duplicates selected assisted samples, relabels their residual context to a configurable `HANDOFF_TEACHER_ALPHA` (planned `0.0`), and keeps the reference_delta action label.
- Added report/metrics/dataset fields for selected source ids, per-source selected counts, filter settings, phase/lift/success/unsafe rates, and the derived source metadata.
- Extended `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass and echo:
  - `HANDOFF_SOURCE_ENABLED`
  - `HANDOFF_SOURCE_SOURCES`
  - `HANDOFF_SOURCE_NAME`
  - `HANDOFF_TEACHER_ALPHA`
  - `HANDOFF_MIN_PHASE`
  - `HANDOFF_MAX_PHASE`
  - `HANDOFF_MIN_LIFT_HEIGHT`
  - `HANDOFF_REQUIRE_SUCCESS`
  - `HANDOFF_REQUIRE_SAFE_TARGET`
  - `HANDOFF_MAX_SAMPLES`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/residual_action_adapter.py` passed.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` passed.
- `git diff --check` passed.

Version Control:
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/bc_reference_action_imitation.py`
  - `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Next:
- Commit/push, deploy exact commit to l401, then launch one supervised-only handoff BC run.
- Planned collection: fresh teacher_mix alphas `0.50/0.75/1.00`; derived alpha0 handoff source from alpha0.50/0.75 samples with `phase >= 0.55` and success or `cube_lift_height >= 0.02`.
- No selector/video unless supervised gate passes.

## 2026-06-11T22:32:00-07:00 - policy-only stabilization handoff supervised launch

Version Control:
- implementation_commit: `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc` (`Add supervised handoff source diagnostic`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc`, clean.

Command / Job:
- job_id: `1028154`
- job_name: `bc_handoff0`
- run_name: `franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_handoff0 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=700,BATCH_SIZE=1024,LEARNING_RATE=0.0001,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=74,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHAS=0.50__COMMA__0.75__COMMA__1.00,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p50=1__COMMA__current_teacher_mix_alpha0p75=1__COMMA__current_teacher_mix_alpha1p00=1__COMMA__policy0_success_handoff=1,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p50_l2=1__COMMA__val_source_current_teacher_mix_alpha0p75_l2=1__COMMA__val_source_current_teacher_mix_alpha1p00_l2=1__COMMA__val_source_policy0_success_handoff_l2=1,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=256,RESIDUAL_MAX_ACTION=1.0,RESIDUAL_GATE_ENABLED=False,RESIDUAL_CONTEXT_FEATURES=phase__COMMA__teacher_alpha,RESIDUAL_L2_WEIGHT=0.0005,SOURCE_PROBE_STEPS=200,HANDOFF_SOURCE_ENABLED=True,HANDOFF_SOURCE_SOURCES=current_teacher_mix_alpha0p50__COMMA__current_teacher_mix_alpha0p75,HANDOFF_SOURCE_NAME=policy0_success_handoff,HANDOFF_TEACHER_ALPHA=0.0,HANDOFF_MIN_PHASE=0.55,HANDOFF_MAX_PHASE=1.0,HANDOFF_MIN_LIFT_HEIGHT=0.02,HANDOFF_REQUIRE_SUCCESS=False,HANDOFF_REQUIRE_SAFE_TARGET=True,HANDOFF_MAX_SAMPLES=0,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028154.out`

Acceptance:
- Supervised-only gate. No selector/video/PPO/RL until metrics and report are fetched and inspected.
- Verify the derived handoff source selected a meaningful number of samples from alpha0.5/0.75 and records safe target rate.
- Assisted alpha0.5/0.75/1.0 val L2 should remain near the stage/alpha checkpoint (`~0.0929/0.0820/0.0663`).
- Policy0 handoff source val L2 must be low enough to justify a tiny visual/selector probe; otherwise stop at the supervised report.
- Global val L2 should not regress materially relative to stage/alpha supervised (`~0.0805`) if considering rollout.
- Reference caveat remains `curobo_validated=false`.

Active Jobs:
- `1028154`.

## 2026-06-11T22:35:00-07:00 - policy-only stabilization handoff supervised result

Job:
- job_id: `1028154`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:26`, node `pool0-00030`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028154.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028154.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/report.md`
- source metric plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/bc_source_metric_plot.png`
- aggregate loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/bc_loss_plot.png`
- oracle residual plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/oracle_residual_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/reference_action_dataset.pt`

Derived Handoff Source:
- enabled: `true`.
- name/slug: `policy0_success_handoff`.
- selected samples: `507` total, all target-safe (`unsafe_rate=0`).
- selected from alpha0.5 and alpha0.75 assisted fresh sources:
  - alpha0.5: `73/4160` samples selected, `12` success samples, `73` lift-threshold samples.
  - alpha0.75: `434/4160` samples selected, `60` success samples, `434` lift-threshold samples.
- filter: `phase >= 0.55`, `phase <= 1.0`, success OR `cube_lift_height >= 0.02`, safe target required.
- handoff source mean phase/lift/success-rate: `0.7321 / 0.0753 m / 0.1420`.

Supervised Metrics:
- selected step/score: `700 / 0.066359`.
- global val L2: `0.117003 -> 0.073941`; this is better than the stage/alpha supervised reference value (`~0.08046`).
- alpha0.5 val L2: `0.149997 -> 0.092610`; essentially matches/preserves the stage/alpha checkpoint (`~0.09288`).
- alpha0.75 val L2: `0.115956 -> 0.074349`; improves over stage/alpha (`~0.08195`).
- alpha1.0 val L2: `0.078938 -> 0.057882`; improves over stage/alpha (`~0.06631`).
- derived policy0 handoff val L2: `0.147575 -> 0.040597`; up abs `0.097305 -> 0.027700`; close/gripper abs `0.039961 -> 0.019338`.
- source separability probe val accuracy: `0.5237` vs baseline `0.3281`, so the residual context/obs can separate sources better than chance.
- reference caveat remains `curobo_validated=false`.

Verdict:
- Supervised gate passes for a metrics-only selector sweep.
- This is not yet a policy-only rollout success claim; the derived alpha0 handoff source only covers lifted/success-window states, so selector eval is required to see whether alpha0 or low-alpha rollout behavior improves.
- No videos/PPO/RL scale-up yet. Launch selector metrics for alpha `0.0/0.25/0.5/0.75/1.0`; only if behavior improves, generate targeted videos/contact sheets.

Next:
- Launch metrics-only selector evals from `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.

## 2026-06-11T21:36:00-07:00 - trajectory-tracking handoff comparison plan

Goal:
- Produce a small inspectable handoff diagnostic that answers what is currently usable for RL from the trajectory-tracking branch.
- Treat tm0.25 DAgger as the current best B checkpoint and the low-assistance residual line as failed unless later supervised evidence changes that.

Hypothesis:
- Existing fetched artifacts are sufficient for a handoff comparison without launching new Slurm jobs:
  - tm0.25 teacher-assisted behavior has selector metrics and targeted videos (`1027988`-`1027991`).
  - pure teacher/reference-force alpha `1.0`, phase end `1.0` has a successful reference feasibility video (`1027919`).
  - gated residual max-1.5 (`1028122`) is a supervised negative/control and should not be rolled out because it failed the supervised gate.
- A consolidated audit will make the usable path explicit: reference and teacher-assisted trajectory tracking are viable; policy-only and the latest residual handoff are not.

Planned Change:
- Add a small local report generator under `dextrah_lab/rl_games/` if the existing summarizers cannot produce a cross-run comparison directly.
- Generate a local artifact bundle under `cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_<timestamp>/` with:
  - `report.md` comparing tm0.25, pure teacher/reference, and gated residual negative/control.
  - `summary.json` and `summary.csv` with success/lift/safety/action-error/supervised-gate metrics.
  - train/eval match audit fields: checkpoint path, reference path, teacher alpha/mix settings, object randomization, action scale, reward/log terms, observation/action dims, and `curobo_validated=false`.
  - links to existing trace plots, contact sheets, videos, source plots, and action-semantics plots.
- Run `viz-open` on the final report and the most important visual artifacts, then record URLs in this worklog.

Validation:
- Local only unless an artifact is missing:
  - parse existing `metrics.json`, `bc_metrics.json`, and generated reports.
  - verify referenced videos/contact sheets/plots exist.
  - `python3 -m py_compile` for any new report generator.
  - `git diff --check`.

Acceptance:
- No new PPO/RL scale-up and no rollout from the failed residual checkpoint.
- The final report must explicitly mark `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` as obsolete failed diagnostic evidence.
- If no candidate is usable for policy-only RL handoff, propose the next supervised-only fix with supporting evidence.

Active Jobs:
- none at plan time.

## 2026-06-11T21:39:59-07:00 - trajectory-tracking handoff comparison result

Implementation:
- Added local artifact-only utility: `dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py`.
- No Slurm job, rollout, PPO, or RL scale-up was launched for this diagnostic.
- Generated local bundle: `cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py` passed.
- `git diff --check` passed.
- Verified all five referenced videos with `ffprobe`: `1280x720`, `520` frames, `8.666667s`.

Artifacts:
- comparison report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/report.md`
- success/lift plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/handoff_success_lift_plot.png`
- summary JSON: `cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/summary.json`
- summary CSV: `cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/summary.csv`
- tm0.25 alpha0.0 failure contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600_artifacts/video_contact_sheet.png`
- tm0.25 alpha0.0 failure video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600/videos/dagger-tm025-a000-env0-step-0.mp4`
- tm0.25 alpha0.5 lowest verified success contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600_artifacts/video_contact_sheet.png`
- tm0.25 alpha0.5 lowest verified success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600/videos/dagger-tm025-a050-env0-step-0.mp4`
- tm0.25 alpha0.75 success contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600_artifacts/video_contact_sheet.png`
- tm0.25 alpha0.75 success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600/videos/dagger-tm025-a075-env0-step-0.mp4`
- tm0.25 alpha1.0 context contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600_artifacts/video_contact_sheet.png`
- tm0.25 alpha1.0 context video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600/videos/dagger-tm025-a100-env1-step-0.mp4`
- pure reference/teacher-force contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848_artifacts/video_contact_sheet.png`
- pure reference/teacher-force video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/videos/tf-eval-a100-phase100-520-step-0.mp4`
- tm0.25 action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_visual_action_semantics_20260611_1906/action_semantics_plot.png`
- gated residual source plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_source_metric_plot.png`

Key Metrics:
- tm0.25 alpha0.0 policy-only: `0/4` final/ever success, max lift `0.0000 m`, target unsafe max `0`, final EE/finger distances `0.3135/0.3075 m`. Not usable for RL handoff.
- tm0.25 alpha0.5 teacher-assisted: `3/4` final/ever success, max lift `0.14125 m`, target unsafe max `0`, raw/ref L2 mean `0.2444`, applied/ref L2 mean `0.1247`. Lowest verified assisted success.
- tm0.25 alpha0.75 teacher-assisted: `3/4` final/ever success, max lift `0.14349 m`, target unsafe max `0`.
- tm0.25 alpha1.0 full teacher context: `3/4` final/ever success, max lift `0.14441 m`, target unsafe max `0`.
- pure reference/teacher-force alpha1.0 phase1.0: `3/4` final/ever success, max lift `0.14441 m`, target unsafe max `0`; confirms reference path/controller feasibility.
- gated residual max1.5 negative/control (`1028122`): tm0.25 val L2 `0.0398` preserved, current alpha0.10 val L2 `0.3885`, global val L2 `0.2133`; supervised gate failed, so no rollout/video/PPO was launched.

Train/Eval Audit:
- tm0.25 evals use checkpoint `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`, task `Dextrah-Franka-Cube-Grasp-Traj-Tracking`, observation/action dims `72/7`, cube spawn randomization `0.08`, action alignment weight `80`, close/lift weights `2.5/4.0`, and train/eval consistency sidecars pass.
- pure reference/teacher-force eval uses checkpoint `/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_teacherforce_rl5b_20260611_170913/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_3560.5405.pth`, same task/dims/randomization, alpha `1.0`, phase end `1.0`, and consistency sidecar passes.
- compact reference remains `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` with `curobo_validated=false`, task-space waypoint transform by cube pose, no joint-trajectory blind transform, and target-unsafe weight zeroed below the table-clearance threshold.

Verdict:
- Current usable B evidence is teacher-assisted trajectory tracking, not policy-only RL handoff.
- No candidate is ready for PPO/RL scale-up because alpha0 policy-only remains `0/4`, while the latest residual handoff is supervised-negative.
- Next supervised-only fix should target the visually successful tm0.25 alpha0.5/0.75 manifold rather than lower-teacher alpha0.10 off-manifold states; a stage-conditioned handoff or separate policy-only hold/stabilization head is the safest next direction.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` is explicitly obsolete failed learned-policy evidence and is not a current handoff candidate.

Active Jobs:
- none.

## 2026-06-11T23:06:00-07:00 - gripper-alpha reference-mix diagnostic plan

Goal:
- Test whether the low-alpha no-reset failures are primarily weak or mistimed gripper closure/hold rather than pose/reference-transform failure.
- Stay eval-only. No PPO/RL scale-up.

Hypothesis:
- Boundary videos show real held lifts in successful envs, while failures keep the cube on the table even as the hand follows the lift-away path.
- If we keep the global pose/reference mix alpha low but increase only the gripper action's reference mix alpha, then a success-rate increase would implicate closure timing/hold as the bottleneck.
- If gripper-only assistance does not improve alpha0.10/0.15/0.20, then the remaining blocker is likely pre-grasp pose/contact geometry or a coupled pose+closure timing issue.

Planned Change:
- Patch `dextrah_lab/rl_games/eval_rollout.py` with an optional `--reference_mix_gripper_alpha` argument for `policy_reference_mix*` action sources.
- Patch `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` to pass `REFERENCE_MIX_GRIPPER_ALPHA` only when set.
- Defaults preserve existing behavior exactly: if the gripper override is unset, all seven action dimensions still use `REFERENCE_MIX_ALPHA`.
- Log effective `reference_mix_gripper_alpha` in per-step metrics and rollout summary.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- Commit/push and deploy exact commit to the l401 agent-owned worktree.

Planned Bounded Probe If Validation Passes:
- Same checkpoint/reference/seed/no-reset setup as the boundary sweep.
- Start with gripper override `REFERENCE_MIX_GRIPPER_ALPHA=1.0` at global alphas `0.10/0.15/0.20`.
- Metrics first; videos/contact sheets for the lowest-alpha improvement and a representative failure if any behavior changes.
- Acceptance is improved sustained no-reset success without target-unsafe regression. This would still be assisted handoff, not policy-only.

Active Jobs:
- none before implementation.

## 2026-06-11T23:30:00-07:00 - z+gripper reference-mix video launch

Implementation:
- commit: `59bb44623f252257600a831e69ef4396813ab084` (`Add z and gripper mix diagnostic`), pushed.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, clean detached at `59bb44623f252257600a831e69ef4396813ab084`.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix`.
- `REFERENCE_MIX_Z_ALPHA=1.0`, `REFERENCE_MIX_GRIPPER_ALPHA=1.0`, `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).

Jobs:
- alpha0.10 previous-success env3: job `1028200`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a010_env3prevsucc_zg100_520_20260611_233000`.
- alpha0.10 previous-failure env0: job `1028201`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a010_env0prevfail_zg100_520_20260611_233000`.
- alpha0.15 previous-success env1: job `1028202`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a015_env1prevsucc_zg100_520_20260611_233000`.
- alpha0.15 previous-failure env0: job `1028203`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a015_env0prevfail_zg100_520_20260611_233000`.
- alpha0.20 previous-success env1: job `1028204`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a020_env1prevsucc_zg100_520_20260611_233000`.
- alpha0.20 previous-failure env2: job `1028205`, run `franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a020_env2prevfail_zg100_520_20260611_233000`.

Acceptance:
- Fetch logs, metrics, traces, MP4s, reports, trace plots, contact sheets, and consistency JSON.
- Validate MP4 metadata.
- Compare against no-override and gripper-only boundary behavior.
- No PPO/RL launch unless video and metrics establish a credible handoff target.

Active Jobs:
- `1028200`, `1028201`, `1028202`, `1028203`, `1028204`, `1028205`.

## 2026-06-11T23:10:00-07:00 - gripper-alpha reference-mix diagnostic launch

Implementation:
- commit: `b0803018cce3a3b9eef6b460e31d53e21195947f` (`Add gripper alpha reference-mix diagnostic`), pushed.
- changed files:
  - `dextrah_lab/rl_games/eval_rollout.py`
  - `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
  - this worklog.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, clean detached at `b0803018cce3a3b9eef6b460e31d53e21195947f`.
- deploy note: the first l401 fetch via SSH failed with the known GitHub public-key issue; direct HTTPS fetch of `codex/franka-cube-trajectory-tracking` succeeded, then checkout detached to `b0803018`.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix`.
- `REFERENCE_MIX_GRIPPER_ALPHA=1.0`, `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=False`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).

Jobs:
- alpha0.10 pose/global mix with gripper alpha1.0: job `1028189`, run `franka_cube_traj_tracking_bc_handoff_noreset_gripref_a010_g100_520_20260611_231000`.
- alpha0.15 pose/global mix with gripper alpha1.0: job `1028190`, run `franka_cube_traj_tracking_bc_handoff_noreset_gripref_a015_g100_520_20260611_231000`.
- alpha0.20 pose/global mix with gripper alpha1.0: job `1028191`, run `franka_cube_traj_tracking_bc_handoff_noreset_gripref_a020_g100_520_20260611_231000`.

Acceptance:
- Fetch metrics/logs/reports first.
- If the gripper override improves sustained no-reset success at a lower alpha, generate targeted video/contact-sheet artifacts for the lowest improved alpha and a representative failure.
- Target unsafe must remain `0`; train/eval consistency must record the gripper override as an expected eval-only field.
- No PPO/RL launch.

Active Jobs:
- `1028189`, `1028190`, `1028191`.

## 2026-06-11T23:13:00-07:00 - gripper-alpha reference-mix metric result and targeted visual plan

Jobs:
- `1028189`, `1028190`, and `1028191` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a010_g100_520_20260611_231000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a015_g100_520_20260611_231000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a020_g100_520_20260611_231000`
- local fetched logs:
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028189.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028190.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028191.out`

Artifacts:
- alpha0.10 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a010_g100_520_20260611_231000_artifacts/report.md`
- alpha0.15 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a015_g100_520_20260611_231000_artifacts/report.md`
- alpha0.20 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_a020_g100_520_20260611_231000_artifacts/report.md`
- action-semantics report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2310_action_semantics/action_semantics_report.md`
- action-semantics plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2310_action_semantics/action_semantics_plot.png`

Metrics:
- alpha0.10 pose/global + gripper1.0 (`1028189`): final/ever success `2/4`, done count `0`, suppressed success-done `2/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.00118, 0.21793, 0.0, 0.25804]` m. This improves alpha0.10 from `1/4` to `2/4` relative to the no-override boundary.
- alpha0.15 pose/global + gripper1.0 (`1028190`): final/ever success `2/4`, done count `0`, suppressed success-done `2/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.0, 0.24016, 0.0, 0.24414]` m. This matches the no-override `2/4` count.
- alpha0.20 pose/global + gripper1.0 (`1028191`): final/ever success `2/4`, done count `0`, suppressed success-done `2/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.06001, 0.22839, 0.0, 0.23163]` m. This regresses from no-override alpha0.20's `3/4`.
- The override is wired: summaries report `reference_mix_alpha=0.10/0.15/0.20`, `reference_mix_gripper_alpha=1.0`, `reference_mix_gripper_alpha_override=true`, and mixed/reference gripper abs error `0.0`.

Analysis:
- Gripper-only reference override is not a clean fix. It helps one alpha0.10 env, but does not improve alpha0.15 and hurts alpha0.20 by losing env0 success.
- This means missed closure is part of the boundary behavior but not the only bottleneck. Pose/contact timing and closure are coupled.
- Target safety remains clean, so the diagnostic is valid as an assisted handoff probe, not a safety regression.

Targeted Visual Plan:
- Launch alpha0.10 gripper1.0 env1 video because env1 is the new success relative to the no-override alpha0.10 boundary.
- Launch alpha0.20 gripper1.0 env0 video because env0 regressed from no-override success to a partial/failed final state.
- No PPO/RL launch.

Active Jobs:
- none before targeted video launch.

## 2026-06-11T23:15:00-07:00 - gripper-alpha targeted visual launch

Version Control:
- remote source remains clean detached at `b0803018cce3a3b9eef6b460e31d53e21195947f`.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix`.
- `REFERENCE_MIX_GRIPPER_ALPHA=1.0`, `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).

Jobs:
- alpha0.10 new-success visual: job `1028196`, run `franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a010_env1newsucc_g100_520_20260611_231500`, `CAMERA_ENV_INDEX=1`.
- alpha0.20 regression visual: job `1028197`, run `franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a020_env0regress_g100_520_20260611_231500`, `CAMERA_ENV_INDEX=0`.

Acceptance:
- Fetch logs, metrics, traces, MP4s, reports, trace plots, contact sheets, and train/eval consistency sidecars.
- Validate MP4 metadata.
- Record visual diagnosis against the no-override boundary videos.
- No PPO/RL launch.

Active Jobs:
- `1028196`, `1028197`.

## 2026-06-11T23:20:00-07:00 - gripper-alpha targeted visual result

Jobs:
- `1028196` and `1028197` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a010_env1newsucc_g100_520_20260611_231500`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a020_env0regress_g100_520_20260611_231500`
- local fetched logs:
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028196.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028197.out`
- MP4 validation: both videos are `1280x720`, `520` frames, `8.666667 s`.

Viewer Artifacts:
- combined gripper diagnostic report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2315/report.md`
- combined gripper diagnostic plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2315/gripper_override_summary.png`
- combined gripper summary JSON/CSV:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2315/summary.json`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2315/summary.csv`
- action-semantics report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2310_action_semantics/action_semantics_report.md`
- action-semantics plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_g100_20260611_2310_action_semantics/action_semantics_plot.png`
- alpha0.10 gripper1.0 env1 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a010_env1newsucc_g100_520_20260611_231500_artifacts/report.md`
- alpha0.10 gripper1.0 env1 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a010_env1newsucc_g100_520_20260611_231500_artifacts/video_contact_sheet.png`
- alpha0.10 gripper1.0 env1 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a010_env1newsucc_g100_520_20260611_231500/videos/handoff-noreset-gripref-a010_env1newsucc-g100-step-0.mp4`
- alpha0.20 gripper1.0 env0 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a020_env0regress_g100_520_20260611_231500_artifacts/report.md`
- alpha0.20 gripper1.0 env0 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a020_env0regress_g100_520_20260611_231500_artifacts/video_contact_sheet.png`
- alpha0.20 gripper1.0 env0 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_gripref_vis_a020_env0regress_g100_520_20260611_231500/videos/handoff-noreset-gripref-a020_env0regress-g100-step-0.mp4`

Metrics / Visual Diagnosis:
- alpha0.10 gripper1.0 (`1028196`): final success `2/4`, success envs `[false, true, false, true]`, target unsafe max `0`, selected env1 final lift `0.21793 m`. Contact sheet shows a real held lift. This is a new success compared with no-override alpha0.10.
- alpha0.20 gripper1.0 (`1028197`): final success `2/4`, success envs `[false, true, false, true]`, target unsafe max `0`, selected env0 final lift `0.06001 m` but `success=false`. Contact sheet shows a partial pickup/drag that does not stabilize into a success; this env was a no-override alpha0.20 success.
- The override is correctly logged in each report: `reference_mix_alpha=0.10/0.20`, `reference_mix_gripper_alpha=1.0`, override `true`, and train/eval consistency `bc_metadata_partial_pass` with no mismatches.

Verdict:
- Gripper closure is a real factor but not sufficient. Increasing only gripper reference assistance can create one additional low-alpha success, but it also degrades another env at alpha0.20.
- The boundary failure is a coupled pose/contact/closure timing issue. A clean handoff plan should not simply force the gripper schedule; it likely needs a phase/contact-aware grasp closure plus pose stabilization objective, or a formal low-alpha assisted controller gate.
- This remains assisted `policy_reference_mix`; alpha0.0 policy-only remains failed. No PPO/RL scale-up.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed diagnostic evidence.

Active Jobs:
- none (`squeue -u lzha` on l401 showed no active jobs after fetching artifacts).

## 2026-06-11T23:24:00-07:00 - z+gripper reference-mix diagnostic plan

Goal:
- Test whether the boundary failures are specifically coupled vertical lift timing plus gripper closure, rather than pure gripper closure or global pose tracking.
- Keep this eval-only with videos/contact sheets. No PPO/RL scale-up.

Hypothesis:
- Gripper-only override showed mixed results: alpha0.10 gained one success, alpha0.20 lost one success.
- If the issue is close+lift timing, overriding both action dim2 (z/lift) and dim6 (gripper) toward the reference while leaving the other action dimensions at low global alpha should improve low-alpha sustained success.
- If this regresses or still leaves failures on the table, then the bottleneck is not just vertical lift and closure; it is coupled contact geometry/XY pose/timing, so the clean handoff plan should not rely on a simple close+lift override.

Planned Change:
- Add optional `--reference_mix_z_alpha` to `dextrah_lab/rl_games/eval_rollout.py` for `policy_reference_mix*` sources.
- Add `REFERENCE_MIX_Z_ALPHA` passthrough to `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`.
- Add the z-alpha override fields to `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`.
- Defaults preserve current behavior exactly: if unset, dim2 uses the scalar `REFERENCE_MIX_ALPHA`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- commit/push/deploy exact commit to the l401 agent worktree before launch.

Planned Video Jobs If Validation Passes:
- Run six labeled no-reset videos with `REFERENCE_MIX_Z_ALPHA=1.0`, `REFERENCE_MIX_GRIPPER_ALPHA=1.0`, and global alphas `0.10/0.15/0.20`.
- Use the same success/failure camera envs from the no-override boundary: alpha0.10 env3/env0, alpha0.15 env1/env0, alpha0.20 env1/env2.
- Each video run writes metrics for all four envs, so the report can compare aggregate effects and selected-camera behavior.

Acceptance:
- Target unsafe max must remain `0`.
- Videos/contact sheets must show whether z+gripper assistance creates real held lifts or causes the hand to lift away from an ungrasped cube.
- No PPO/RL launch unless a credible low-alpha handoff target is visually and numerically established.

Active Jobs:
- none before implementation.

## 2026-06-11T22:58:00-07:00 - no-reset boundary visual sweep plan

Goal:
- Produce inspectable video/contact-sheet evidence for the no-reset lower-alpha boundary cases requested by the orchestrator: alpha0.10, alpha0.15, and alpha0.20.
- Keep this eval/video-only. No PPO/RL scale-up.

Context:
- Old `actionscale-rewinf-diag-video480-step-0.mp4` from job `1027753` remains obsolete failed diagnostic evidence.
- Metric-only no-reset selector result:
  - alpha0.10 (`1028173`): final/ever success `1/4`; success env3, failure envs0/1/2.
  - alpha0.15 (`1028174`): final/ever success `2/4`; success envs1/3, failure envs0/2.
  - alpha0.20 (`1028175`): final/ever success `3/4`; success envs0/1/3, failure env2.
- Target unsafe max was `0` for all three selector jobs; compact reference remains `curobo_validated=false`.

Planned Visual Jobs:
- alpha0.10 success env: `REFERENCE_MIX_ALPHA=0.10`, `CAMERA_ENV_INDEX=3`.
- alpha0.10 failure env: `REFERENCE_MIX_ALPHA=0.10`, `CAMERA_ENV_INDEX=0`.
- alpha0.15 success env: `REFERENCE_MIX_ALPHA=0.15`, `CAMERA_ENV_INDEX=1`.
- alpha0.15 failure env: `REFERENCE_MIX_ALPHA=0.15`, `CAMERA_ENV_INDEX=0`.
- alpha0.20 success env: `REFERENCE_MIX_ALPHA=0.20`, `CAMERA_ENV_INDEX=1`.
- alpha0.20 failure env: `REFERENCE_MIX_ALPHA=0.20`, `CAMERA_ENV_INDEX=2`.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix`.
- `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.

Acceptance:
- Fetch logs, metrics, traces, MP4s, reports, trace plots, contact sheets, and train/eval consistency sidecars.
- Regenerate reports using `--train-bc-metrics` and record unverified train keys from older BC metadata rather than treating them as hidden pass/fail.
- Validate MP4 metadata with `ffprobe`.
- Produce a compact comparison report/table after the six runs.
- No PPO/RL launch; next development direction remains either reducing/eliminating reference mix or documenting a clean low-alpha assisted handoff plan.

Active Jobs:
- none before launch.

## 2026-06-11T23:00:00-07:00 - no-reset boundary visual sweep launch

Version Control:
- local plan commit: `4243a0c` (`Plan no-reset boundary visual sweep`), pushed.
- remote eval source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, clean detached at `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc`.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix`.
- `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).

Jobs:
- alpha0.10 success-env visual: job `1028178`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env3succ_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.10`, `CAMERA_ENV_INDEX=3`.
- alpha0.10 failure-env visual: job `1028179`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env0fail_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.10`, `CAMERA_ENV_INDEX=0`.
- alpha0.15 success-env visual: job `1028180`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env1succ_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.15`, `CAMERA_ENV_INDEX=1`.
- alpha0.15 failure-env visual: job `1028181`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env0fail_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.15`, `CAMERA_ENV_INDEX=0`.
- alpha0.20 success-env visual: job `1028182`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env1succ_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.20`, `CAMERA_ENV_INDEX=1`.
- alpha0.20 failure-env visual: job `1028183`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env2fail_520_20260611_230000`, `REFERENCE_MIX_ALPHA=0.20`, `CAMERA_ENV_INDEX=2`.

Acceptance:
- Fetch logs, metrics, traces, MP4s, reports, trace plots, contact sheets, and train/eval consistency sidecars.
- Regenerate reports with `--train-bc-metrics` and explicitly list unverified train keys from old BC metadata.
- Validate videos with `ffprobe`.
- Produce a compact comparison report/table and `viz-open` URLs.
- No PPO/RL launch.

Active Jobs:
- `1028178`, `1028179`, `1028180`, `1028181`, `1028182`, `1028183`.

## 2026-06-11T23:03:00-07:00 - no-reset boundary visual sweep result

Jobs:
- `1028178`-`1028183` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env3succ_520_20260611_230000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env0fail_520_20260611_230000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env1succ_520_20260611_230000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env0fail_520_20260611_230000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env1succ_520_20260611_230000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env2fail_520_20260611_230000`
- local fetched logs:
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028178.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028179.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028180.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028181.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028182.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028183.out`

Validation:
- `ffprobe` validated all six MP4s as `1280x720`, `520` frames, `8.666667 s`.
- per-run reports regenerated with `--train-bc-metrics`.
- train/eval consistency status is `bc_metadata_partial_pass`, `passed=true`, mismatch count `0` for all six.
- old BC metrics still do not include the following train-side keys, which remain explicitly unverified rather than silently passing: cube spawn randomization, phase observations, close/lift reward weights, contact-gate parameters, reference late reweight parameters, action-alignment parameters, and teacher-force parameters.

Viewer Artifacts:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/report.md`
- comparison plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/boundary_success_lift_safety.png`
- action-semantics report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/action_semantics/action_semantics_report.md`
- action-semantics plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/action_semantics/action_semantics_plot.png`
- summary JSON/CSV:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/summary.json`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_boundary_visual_20260611_2300/summary.csv`
- alpha0.10 success env3 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env3succ_520_20260611_230000/videos/handoff-noreset-a010_env3succ-step-0.mp4`
- alpha0.10 success env3 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env3succ_520_20260611_230000_artifacts/video_contact_sheet.png`
- alpha0.10 failure env0 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env0fail_520_20260611_230000/videos/handoff-noreset-a010_env0fail-step-0.mp4`
- alpha0.10 failure env0 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a010_env0fail_520_20260611_230000_artifacts/video_contact_sheet.png`
- alpha0.15 success env1 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env1succ_520_20260611_230000/videos/handoff-noreset-a015_env1succ-step-0.mp4`
- alpha0.15 success env1 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env1succ_520_20260611_230000_artifacts/video_contact_sheet.png`
- alpha0.15 failure env0 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env0fail_520_20260611_230000/videos/handoff-noreset-a015_env0fail-step-0.mp4`
- alpha0.15 failure env0 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a015_env0fail_520_20260611_230000_artifacts/video_contact_sheet.png`
- alpha0.20 success env1 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env1succ_520_20260611_230000/videos/handoff-noreset-a020_env1succ-step-0.mp4`
- alpha0.20 success env1 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env1succ_520_20260611_230000_artifacts/video_contact_sheet.png`
- alpha0.20 failure env2 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env2fail_520_20260611_230000/videos/handoff-noreset-a020_env2fail-step-0.mp4`
- alpha0.20 failure env2 sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a020_env2fail_520_20260611_230000_artifacts/video_contact_sheet.png`

Metrics / Visual Diagnosis:
- alpha0.10: final/ever success `1/4`, done count `0`, suppressed success-done `1/4`, target unsafe max `0`, final lift by env `[0.00059, 0.00410, 0.0, 0.27511]` m. Env3 video is a real held lift; env0 video is a failure with the cube on the table.
- alpha0.15: final/ever success `2/4`, done count `0`, suppressed success-done `2/4`, target unsafe max `0`, final lift by env `[0.0, 0.21644, 0.0, 0.24450]` m. Env1 video is a real held lift; env0 video fails on the table.
- alpha0.20: final/ever success `3/4`, last-window success mean `0.6425`, done count `0`, suppressed success-done `3/4`, target unsafe max `0`, final lift by env `[0.17922, 0.23008, 0.0, 0.23151]` m. Env1 video is a real held lift; env2 video fails with the gripper rising while the cube remains on the table.
- The failure cases do not look like the old drift-away/train-eval mismatch pattern. They look like weak or missed grasp closure/hold at the cube. The alpha0.20 env2 failure is the cleanest example: the arm follows the lift-away motion while the cube is left behind.

Verdict:
- Current best boundary result is assisted `policy_reference_mix`: alpha0.20 reaches `3/4` sustained no-reset success with clean target safety and visual confirmation; alpha0.10 and alpha0.15 show partial success but are below that gate.
- This is not policy-only handoff. Alpha0.0 policy-only previously failed, and no PPO/RL scale-up is justified.
- Next bounded development should focus on reducing/eliminating reference mix through grasp closure/hold improvements, or explicitly defining a low-alpha assisted handoff objective. A direct next diagnostic is to separate pose assistance from gripper/closure assistance with a per-dimension reference-mix probe.

Active Jobs:
- none.

## 2026-06-11T22:54:00-07:00 - no-reset lower-alpha threshold selector result and alpha0.20 visual plan

Jobs:
- `1028173`, `1028174`, and `1028175` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a010_520_20260611_232200`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a015_520_20260611_232200`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a020_520_20260611_232200`
- local fetched logs:
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028173.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028174.out`
  - `cluster_results/l401/slurm_logs/eval_franka_cube_1028175.out`

Artifacts:
- alpha0.10 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a010_520_20260611_232200_artifacts/report.md`
- alpha0.10 trace plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a010_520_20260611_232200_artifacts/trajectory_trace_plot.png`
- alpha0.15 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a015_520_20260611_232200_artifacts/report.md`
- alpha0.15 trace plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a015_520_20260611_232200_artifacts/trajectory_trace_plot.png`
- alpha0.20 report: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a020_520_20260611_232200_artifacts/report.md`
- alpha0.20 trace plot: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_selector_a020_520_20260611_232200_artifacts/trajectory_trace_plot.png`

Metrics:
- alpha0.10 (`1028173`): final/ever success `1/4`, done count `0`, suppressed success-done `1/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.00059, 0.00410, 0.0, 0.27511]` m, raw/applied reference-action L2 mean `0.7094`.
- alpha0.15 (`1028174`): final/ever success `2/4`, done count `0`, suppressed success-done `2/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.0, 0.21644, 0.0, 0.24450]` m, raw/applied reference-action L2 mean `0.4689`.
- alpha0.20 (`1028175`): final/ever success `3/4`, last-window success mean `0.6425`, done count `0`, suppressed success-done `3/4`, target unsafe max `0`, clearance min `0.065114 m`, final lift by env `[0.17922, 0.23008, 0.0, 0.23151]` m, raw/applied reference-action L2 mean `0.3368`.

Analysis:
- The threshold sweep improves monotonically with assistance alpha. Alpha0.10 and alpha0.15 are below the current low-alpha handoff gate. Alpha0.20 matches alpha0.25's `3/4` sustained no-reset success count in metrics, with clean target safety.
- This is still low-alpha assisted trajectory tracking, not policy-only. Policy-only alpha0.0 remains failed from the current targeted visual gate.
- The compact reference caveat remains unchanged: `curobo_validated=false`.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` from job `1027753` remains obsolete failed diagnostic evidence.

Next:
- Launch exactly one targeted alpha0.20 no-reset video/contact-sheet eval with `CAMERA_ENV_INDEX=1`, because env1 succeeded with final lift `0.23008 m` in the metrics-only run.
- Do not launch PPO/RL. If the alpha0.20 video visually confirms sustained lift and train/eval consistency remains clean, record alpha0.20 as the lowest current defensible assisted handoff gate.

Active Jobs:
- none before the alpha0.20 visual launch.

## 2026-06-11T23:22:00-07:00 - no-reset lower-alpha threshold selector launch

Goal:
- Find whether assistance below alpha0.25 can sustain final success with success termination suppressed.

Version Control:
- local evidence commit: `793bf0c75577cfe28ef738b32830fa4ea9ecec5c` (`Record no-reset low-alpha handoff gate`), pushed.
- remote eval source remains at `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc`; no new runtime source is needed for this eval-only sweep.

Command / Jobs:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`
- common eval config: `ACTION_SOURCE=policy_reference_mix`, `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=False`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- alpha0.10: job_id `1028173`, run `franka_cube_traj_tracking_bc_handoff_noreset_selector_a010_520_20260611_232200`.
- alpha0.15: job_id `1028174`, run `franka_cube_traj_tracking_bc_handoff_noreset_selector_a015_520_20260611_232200`.
- alpha0.20: job_id `1028175`, run `franka_cube_traj_tracking_bc_handoff_noreset_selector_a020_520_20260611_232200`.

Acceptance:
- metrics/logs only first. If a lower alpha has sustained final success and target unsafe max `0`, generate targeted video/contact sheet.
- If all fail below alpha0.25, keep alpha0.25 as the lowest current defensible assisted gate and do not launch PPO/RL.

Active Jobs:
- `1028173`, `1028174`, `1028175`.

## 2026-06-11T23:08:00-07:00 - BC train/eval consistency audit fix plan

Goal:
- Replace the inconclusive `train_config_unavailable` consistency artifact for BC checkpoints with a partial but machine-readable train/eval audit from `bc_metrics.json`.

Plan:
- Patch `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` to accept `--train-bc-metrics`.
- Derive comparable training metadata from the BC report: task, obs/action dims, output checkpoint, collection action source/teacher alphas, residual adapter metadata, compact reference source/duration/gripper policy/validation caveat.
- Compare these fields against eval metadata and keep the existing expected eval overrides for selector alpha/video/num_steps.
- Mark fields unavailable in old BC metrics, such as cube randomization and detailed reward weights, as `bc_metadata_unavailable` instead of hard failure; this documents the remaining gap without hiding it.
- Regenerate the three current handoff visual reports and the combined report, re-open viewer URLs, and update this worklog. No new Slurm jobs or PPO/RL launch.

Acceptance:
- `train_eval_consistency.json` no longer reports global `train_config_unavailable`.
- It must explicitly say what matched, what remains unverified, and that `curobo_validated=false` remains the reference status.

## 2026-06-11T23:12:00-07:00 - BC train/eval consistency audit fix result

Change:
- patched `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` with `--train-bc-metrics`.
- regenerated the three current handoff visual artifact directories using `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/bc_metrics.json`.
- updated the combined report at `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_visual_gate_20260611_2240/report.md`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- `git diff --check` passed.

Consistency Result:
- alpha0.0 / alpha0.25 / alpha1.0 targeted reports now show `status=bc_metadata_partial_pass`, `passed=true`, `train_source=bc_metrics`.
- no real mismatches, no missing train keys, no missing eval keys for comparable metadata.
- matched fields include task, output checkpoint, obs/action dims `72/7`, compact reference path, runtime duration, minimum gripper width, reference `curobo_validated=false`, `validation_passed=true`, `transform_policy=transform_task_space_waypoints_by_cube_pose`, `joint_trajectory_policy=do_not_transform_joint_trajectories`, `runtime_object_pose_policy=reset_cube_pose`, and source tag.
- remaining unverified keys are explicitly listed in each `train_eval_consistency.json`: cube randomization, phase observations, detailed reward/gate weights, and teacher-force env config were not recorded by older BC metrics. This is now documented rather than hidden as a global unavailable train config.

Viewer Artifacts:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_visual_gate_20260611_2240/report.md`
- alpha0.0 consistency: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000_artifacts/train_eval_consistency.json`
- alpha0.25 consistency: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000_artifacts/train_eval_consistency.json`
- alpha1.0 consistency: `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000_artifacts/train_eval_consistency.json`

Next:
- Commit the audit-tooling/worklog update.
- Run a bounded eval-only no-reset visual probe for alpha0.25 (and alpha1.0 context if needed) with `SUPPRESS_SUCCESS_TERMINATION=True` to determine whether the low-alpha handoff can maintain lift after the first success window. No PPO/RL.

## 2026-06-11T23:15:00-07:00 - no-reset low-alpha handoff visual launch

Version Control:
- local implementation/worklog commit: `6d9c0b6773df663c7955a705038f5bbec6e4e60f` (`Add BC metrics consistency audit`), pushed.
- remote eval source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, clean at `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc`; this already contains the eval/runtime code needed for `SUPPRESS_SUCCESS_TERMINATION=True`. The `6d9c0b6` commit is local artifact tooling and worklog.

Goal:
- Determine whether the alpha0.25 low-teacher handoff can remain successful after the first success window when automatic success termination is suppressed.

Command / Jobs:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`
- common eval config: `TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking`, `ACTION_SOURCE=policy_reference_mix`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`, `SUPPRESS_SUCCESS_TERMINATION=True`.
- alpha0.25: job_id `1028169`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a025_env1_520_20260611_231500`, `CAMERA_ENV_INDEX=1`.
- alpha1.0 context: job_id `1028170`, run `franka_cube_traj_tracking_bc_handoff_noreset_vis_a100_env0_520_20260611_231500`, `CAMERA_ENV_INDEX=0`.

Acceptance:
- fetch metrics/videos/logs, validate MP4 metadata, regenerate reports using `--train-bc-metrics`, inspect contact sheets.
- alpha0.25 only becomes a defensible low-alpha handoff gate if success remains active near the end without target-unsafe regression. If success/lift drops after suppression, stay supervised/eval-only and do not launch PPO/RL.

Active Jobs:
- `1028169`, `1028170`.

## 2026-06-11T23:19:00-07:00 - no-reset low-alpha handoff visual result

Jobs:
- `1028169` / `1028170` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a025_env1_520_20260611_231500`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a100_env0_520_20260611_231500`
- MP4 validation: both videos are `1280x720`, `520` frames, `8.666667 s`.

Viewer Artifacts:
- combined no-reset report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_visual_gate_20260611_2315/report.md`
- alpha0.25 no-reset report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a025_env1_520_20260611_231500_artifacts/report.md`
- alpha0.25 no-reset contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a025_env1_520_20260611_231500_artifacts/video_contact_sheet.png`
- alpha0.25 no-reset video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a025_env1_520_20260611_231500/videos/handoff-noreset-a025-env1-step-0.mp4`
- alpha1.0 no-reset report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a100_env0_520_20260611_231500_artifacts/report.md`
- alpha1.0 no-reset contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a100_env0_520_20260611_231500_artifacts/video_contact_sheet.png`
- alpha1.0 no-reset video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_vis_a100_env0_520_20260611_231500/videos/handoff-noreset-a100-env0-step-0.mp4`
- no-reset action-semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_action_semantics_20260611_2315/action_semantics_report.md`
- no-reset action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_action_semantics_20260611_2315/action_semantics_plot.png`

Metrics / Visual Diagnosis:
- alpha0.25 no-reset (`1028169`): final success `3/4`, success-ever `3/4`, last-window success `0.75`, done count `0`, suppressed success-done `3/4`, target unsafe max `0`, clearance min `0.065114 m`; final lift by env `[0.20256, 0.22152, 0.0, 0.22493]` m. Contact sheet shows selected env1 still holding the cube in the final frame.
- alpha1.0 no-reset (`1028170`): final success `4/4`, last-window success `1.0`, done count `0`, suppressed success-done `4/4`, target unsafe max `0`; final lift by env `[0.19259, 0.19277, 0.19251, 0.19266]` m. Contact sheet shows sustained lift in final frame.
- train/eval consistency artifacts now use `--train-bc-metrics` and report `bc_metadata_partial_pass`, no mismatches, and explicit unverified train keys for older BC metadata gaps.
- Reference caveat remains `curobo_validated=false`.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` from job `1027753` remains obsolete failed diagnostic evidence.

Verdict:
- This is the best current B result for a low-alpha assisted handoff: alpha0.25 can sustain final success under suppressed success termination, with target safety clean and visual evidence.
- It is still not a policy-only gate. Alpha0.0 policy-only remains failed from the targeted visual gate, so PPO/RL scale-up remains unauthorized unless the objective is explicitly changed to low-alpha assisted tracking or policy-only improves in a bounded supervised/eval loop.

Next:
- If continuing toward policy-only, collect/fit around no-reset alpha0.25 success states and test alpha0.0/alpha0.1 no-reset before any RL.
- If accepting low-alpha assisted tracking as the objective, define a formal low-alpha gate around alpha0.25 no-reset success, including target safety, BC metadata consistency, and visual sustained lift.

Active Jobs:
- none.

## 2026-06-11T22:31:26-07:00 - handoff selector metrics launch plan

Goal:
- Run the bounded selector metric gate for the supervised handoff checkpoint before any video or rollout scale-up decision.

Version Control:
- local worklog commit: `8b286bfd9e922721aba961340de55e631205d3ff` (`Record handoff BC supervised result`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source fetch of `8b286bfd9e922721aba961340de55e631205d3ff` from GitHub failed on l401 with `Permission denied (publickey)`.
- remote source remains clean at `6a403ae2d7bfb39b5faa5b805fa97da8ebb4d4dc`, which is the exact source-code commit that implements the handoff selector/eval path; `8b286bfd9e922721aba961340de55e631205d3ff` is worklog-only.

Planned Jobs:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- alphas: `0.0/0.25/0.5/0.75/1.0`.
- action source: `policy_reference_mix`, metrics only, `NUM_ENVS=4`, `NUM_STEPS=520`, video disabled.
- acceptance: inspect metrics/logs first; only generate targeted videos/contact sheets if policy-only or lower-alpha behavior improves. No PPO/RL scale-up.
- reference caveat remains `curobo_validated=false`.

Submitted Jobs:
- alpha0.0: job_id `1028156`, run `franka_cube_traj_tracking_bc_handoff_selector_a000_520_20260611_223300`.
- alpha0.25: job_id `1028157`, run `franka_cube_traj_tracking_bc_handoff_selector_a025_520_20260611_223300`.
- alpha0.5: job_id `1028158`, run `franka_cube_traj_tracking_bc_handoff_selector_a050_520_20260611_223300`.
- alpha0.75: job_id `1028159`, run `franka_cube_traj_tracking_bc_handoff_selector_a075_520_20260611_223300`.
- alpha1.0: job_id `1028160`, run `franka_cube_traj_tracking_bc_handoff_selector_a100_520_20260611_223300`.

## 2026-06-11T22:36:00-07:00 - handoff selector metrics result and visual probe plan

Job Results:
- jobs `1028156`-`1028160` all completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_selector_a000_520_20260611_223300`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_selector_a025_520_20260611_223300`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_selector_a050_520_20260611_223300`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_selector_a075_520_20260611_223300`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_selector_a100_520_20260611_223300`

Metrics:
- alpha0.0: success_ever `0/4`, final success `0`, max lift by env `[0.00917, 0.01502, 0.0, 0.02780]`; target unsafe max `0`; final EE/finger/max-finger distances `0.0868/0.1088/0.1171` m.
- alpha0.25: success_ever `3/4`, final success `0`, done_after_success `3`; max lift by env `[0.13599, 0.13747, 0.0, 0.13694]`; first success steps min/mean/max `366/371.3/382`; target unsafe max `0`.
- alpha0.5: success_ever `3/4`, final success `0`, done_after_success `3`; max lift by env `[0.13613, 0.13566, 0.00108, 0.13595]`; target unsafe max `0`.
- alpha0.75: success_ever `3/4`, final success `0`, done_after_success `3`; max lift by env `[0.13590, 0.13523, 0.00095, 0.13554]`; target unsafe max `0`.
- alpha1.0: success_ever `4/4`, final success `0`, done_after_success `4`; max lift by env `[0.13611, 0.13629, 0.13600, 0.13616]`; target unsafe max `0`.

Analysis:
- The derived handoff source did not make policy-only alpha0.0 succeed; policy-only remains outside the acceptance gate.
- Low-teacher alpha0.25 reaches the same transient success pattern as the prior stage-alpha selector: successful envs trigger success_done/reset and end with final success `0`. This is useful as a low-teacher visual probe, but not a PPO/RL scale-up gate.
- Because the supervised gate passed and alpha0.25 is the lowest successful assistance level, launch only targeted videos: alpha0.0 env0 failure, alpha0.25 env1 success-window visual, and alpha1.0 env0 teacher/reference context.

Next:
- Launch three short 520-step video evals from the same handoff checkpoint. No PPO/RL scale-up.

Submitted Visual Jobs:
- alpha0.0 failure: job_id `1028162`, run `franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000`, `CAMERA_ENV_INDEX=0`, video prefix `handoff-a000-env0-failure`.
- alpha0.25 low-alpha success-window probe: job_id `1028163`, run `franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000`, `CAMERA_ENV_INDEX=1`, video prefix `handoff-a025-env1-lowalpha`.
- alpha1.0 teacher/reference context: job_id `1028164`, run `franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000`, `CAMERA_ENV_INDEX=0`, video prefix `handoff-a100-env0-context`.

## 2026-06-11T22:45:00-07:00 - handoff visual gate result

Jobs:
- `1028162` / `1028163` / `1028164` completed `0:0`.
- local fetched runs:
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000`
  - `cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000`
- MP4 validation: all three videos are `1280x720`, `520` frames, `8.666667 s`.

Viewer Artifacts:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_visual_gate_20260611_2240/report.md`
- alpha0.0 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000_artifacts/report.md`
- alpha0.0 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000_artifacts/video_contact_sheet.png`
- alpha0.0 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a000_env0_520_20260611_224000/videos/handoff-a000-env0-failure-step-0.mp4`
- alpha0.25 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000_artifacts/report.md`
- alpha0.25 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000_artifacts/video_contact_sheet.png`
- alpha0.25 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a025_env1_520_20260611_224000/videos/handoff-a025-env1-lowalpha-step-0.mp4`
- alpha1.0 report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000_artifacts/report.md`
- alpha1.0 contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000_artifacts/video_contact_sheet.png`
- alpha1.0 video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_vis_a100_env0_520_20260611_224000/videos/handoff-a100-env0-context-step-0.mp4`
- action-semantics report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_visual_action_semantics_20260611_2240/action_semantics_report.md`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_visual_action_semantics_20260611_2240/action_semantics_plot.png`

Metrics / Visual Diagnosis:
- alpha0.0 (`1028162`): policy-only remains failed. `success_ever=0/4`, `success_final=0`, `done_count=0`, target unsafe max `0`, target clearance min `0.065114 m`; contact sheet shows approach/perturbation but no lift. Raw-policy/reference L2 mean/final `1.141/1.033`; action semantics show weak close/lift timing versus reference during close/lift windows.
- alpha0.25 (`1028163`): lowest-alpha transient success. `success_ever=3/4`, `success_final=0`, `success_done=3`, target unsafe max `0`; selected env1 first/last success `366/378` and done at `378`. Contact sheet visibly shows lift in the success window; final-zero is due success termination/reset, not a physical final-frame hold failure in the selected episode segment.
- alpha1.0 (`1028164`): teacher/reference context remains positive. `success_ever=4/4`, `success_final=0`, `success_done=4`, all envs first/last success `378/390` and done at `390`; target unsafe max `0`. Contact sheet visibly shows lift and then post-reset final frame.
- Train/eval consistency: auto helper reports `train_config_unavailable` because this is a BC checkpoint without train-env YAML. Manual audit in the combined report confirms task/checkpoint/action source, obs/action dims `72/7`, cube randomization `0.08`, reference path, selector alpha, deterministic eval, and target safety. No mismatch was found in available eval metadata.
- Reference caveat remains `curobo_validated=false`.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` from job `1027753` remains obsolete failed diagnostic evidence, not current B status.

Verdict:
- Not a PPO/RL scale-up gate.
- Handoff supervised training created a useful low-alpha transient success at alpha0.25, but policy-only alpha0.0 still fails. Any next run should stay supervised/eval-only and target policy-only terminal stability or no-reset success-window retention before considering RL.

Active Jobs:
- none.

## 2026-06-11T21:49:54-07:00 - stage/alpha-conditioned assisted-manifold BC plan

Goal:
- Target the verified assisted manifold instead of the failed alpha0.10 residual line.
- Run a supervised-only diagnostic on alpha0.5, alpha0.75, and alpha1.0 teacher-assisted states collected from the tm0.25 checkpoint.
- Do not launch PPO/RL scale-up. Only launch a tiny selector/video eval if the supervised gate clearly passes.

Hypothesis:
- tm0.25 alpha0.5/0.75/1.0 already lifts with reference assistance, so those states are on a usable manifold.
- The previous residual attempts failed because they targeted alpha0.10/off-manifold states and lacked explicit stage/assistance context.
- A frozen tm0.25 base actor plus a small residual adapter conditioned on trajectory phase and teacher-assist alpha can reduce raw/reference action error on the successful assisted manifold while preserving the original 72-D task observation and the original baseline task.

Planned Change:
- Extend `dextrah_lab/rl_games/residual_action_adapter.py` so residual adapters can optionally consume context features in addition to the 72-D observation.
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with:
  - multi-alpha fresh collection, e.g. `--collection_teacher_alphas 0.5,0.75,1.0`;
  - per-sample `teacher_alpha` metadata saved in `reference_action_dataset.pt`;
  - residual context features `phase,teacher_alpha`;
  - supervised per-source metrics for alpha0.5/0.75/1.0.
- Extend `dextrah_lab/rl_games/eval_rollout.py` to supply the same residual context at eval time from `traj_phase_progress` and the eval `reference_mix_alpha` (or an explicit override).
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to echo/pass the new knobs.

Planned Supervised Job If Validation Passes:
- run name: `franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_<timestamp>`.
- input checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- collection action source: `teacher_mix`.
- collection alphas: `0.50,0.75,1.00`.
- no alpha0.10 collection in this round.
- `NUM_ENVS=8`, `COLLECTION_STEPS=520` per alpha, all 7 action dims.
- residual adapter: enabled, frozen base, hidden `256`, max action `1.0`, context features `phase,teacher_alpha`.
- source-balanced batches and equal source weights.

Supervised Gate Before Any Eval:
- Each alpha source should improve materially over its frozen-base raw/reference L2.
- No alpha0.5/0.75/1.0 source may regress versus its frozen-base source L2.
- Global val L2 should be clearly below the prior off-manifold residual attempts and ideally near or below the current tm0.25 assisted raw/ref selector errors.
- Residual magnitude must be bounded and context metadata must be present in the checkpoint/report.
- If the supervised gate fails, stop at report/metrics/plots and do not launch selector/videos/PPO.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/residual_action_adapter.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- commit/push and deploy exact commit to the l401 agent-owned worktree before Slurm launch.

Artifact Contract:
- supervised report, `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `bc_source_metric_plot.png`, oracle residual CSV/plot, and `viz-open` URLs after fetch.
- train/eval audit must include checkpoint path, reference path, alpha/stage conditioning, object randomization, action scale, observation/action dims, and `curobo_validated=false`.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed evidence.

Active Jobs:
- none at plan time.

## 2026-06-11T21:55:50-07:00 - stage/alpha-conditioned assisted-manifold implementation

Goal:
- Implement the supervised-only stage/alpha-conditioned handoff diagnostic planned above, without launching PPO/RL or selector evals.

Change:
- Added multi-alpha fresh collection to `dextrah_lab/rl_games/bc_reference_action_imitation.py` with per-sample `teacher_alpha` stored in `reference_action_dataset.pt`.
- Added residual adapter context features (`phase`, `teacher_alpha`) for frozen-base residual BC; checkpoint/report metadata now records the context list and collection alpha list.
- Updated `dextrah_lab/rl_games/eval_rollout.py` so residual adapters receive the same context at eval time from `traj_phase_progress` and the current `REFERENCE_MIX_ALPHA`.
- Updated `dextrah_lab/rl_games/residual_action_adapter.py` to concatenate optional context with the 72-D policy observation while preserving old zero-context checkpoints.
- Updated `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to echo/pass `COLLECTION_TEACHER_ALPHAS` and `RESIDUAL_CONTEXT_FEATURES`.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `05c0872251e1c56581aba9b2e540ed093a75dfae`
- implementation_commit: pending
- changed_files: `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`, `dextrah_lab/rl_games/bc_reference_action_imitation.py`, `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/residual_action_adapter.py`, `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Validation:
- passed: `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/residual_action_adapter.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py`
- passed: `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- passed: `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- passed: `git diff --check`

Analysis:
- The implementation is intentionally supervised-only. The selector/video gate remains blocked until a supervised l401 run proves each alpha0.5/0.75/1.0 source improves over its frozen tm0.25 base action error without target/reference/config drift.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed evidence from job `1027753`; current artifacts should refer to the tm0.25 assisted manifold and this new stage/alpha-conditioned diagnostic.

Next:
- Commit/push this implementation, deploy the exact commit to the l401 agent worktree, and launch one supervised l401 BC job on `COLLECTION_TEACHER_ALPHAS=0.50,0.75,1.00`.
- No selector evals, videos, PPO, or RL scale-up unless the supervised gate passes.

Active Jobs:
- none.

## 2026-06-11T21:58:10-07:00 - stage/alpha-conditioned assisted-manifold BC launch

Goal:
- Run the supervised-only stage/alpha-conditioned residual BC diagnostic on the verified alpha0.5/0.75/1.0 assisted manifold.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- local_commit: `e0db570315961f84e2ad49af917ff21191a9d3cc`
- branch: `codex/franka-cube-trajectory-tracking`
- push/pull: pushed to origin; l401 SSH Git auth failed as usual, HTTPS fetch succeeded.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `e0db570315961f84e2ad49af917ff21191a9d3cc`, clean.

Command / Job:
- job_id: `1028133`
- job_name: `bc_stagealpha`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_stagealpha --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_20260611_215726,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=600,BATCH_SIZE=1024,LEARNING_RATE=0.0001,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=73,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHAS=0.50__COMMA__0.75__COMMA__1.00,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p50=1__COMMA__current_teacher_mix_alpha0p75=1__COMMA__current_teacher_mix_alpha1p00=1,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p50_l2=1__COMMA__val_source_current_teacher_mix_alpha0p75_l2=1__COMMA__val_source_current_teacher_mix_alpha1p00_l2=1,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=256,RESIDUAL_MAX_ACTION=1.0,RESIDUAL_GATE_ENABLED=False,RESIDUAL_CONTEXT_FEATURES=phase__COMMA__teacher_alpha,RESIDUAL_L2_WEIGHT=0.0005,SOURCE_PROBE_STEPS=200,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_20260611_215726`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028133.out`
- expected_artifacts: `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `bc_source_metric_plot.png`, `oracle_residual_*.csv`, `oracle_residual_*.png`, `reference_action_dataset.pt`, `nn/bc_reference_action_imitation.pth`, `report.md`

Acceptance / Gate:
- supervised only; no selector/videos/PPO until report and metrics are fetched and inspected.
- target safety/reference audit must retain `curobo_validated=false` for the compact reference.
- each alpha0.5/0.75/1.0 source should improve materially over frozen-base source L2; no rollout if source metrics are ambiguous or negative.

Active Jobs:
- `1028133` pending/running.

## 2026-06-11T22:01:26-07:00 - stage/alpha-conditioned BC launch failure and parser fix

Job:
- job_id: `1028133`
- scheduler state: `CANCELLED by 158351`, elapsed `00:02:21`, node `pool0-00015`.
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028133.out`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028133.out`
- local failed-run log copy: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_20260611_215726_failed/bc_franka_cube_1028133.out`
- run_dir state: no `bc_metrics.json`, no dataset, and no report/checkpoint written.

Failure Evidence:
- The job registered `Dextrah-Franka-Cube-Grasp-Traj-Tracking` with observation/action spaces `(72,) / (7,)` and loaded the tm0.25 BC checkpoint path.
- Immediately after `=> loading checkpoint ...`, Hydra printed `Error executing job with overrides` and no dataset/training artifacts appeared.
- The echoed command passed list-valued args using Slurm-safe comma encoding:
  - `--collection_teacher_alphas 0.50__COMMA__0.75__COMMA__1.00`
  - `--residual_context_features phase__COMMA__teacher_alpha`
  - source/best-score maps also used `__COMMA__`.

Root Cause:
- `bc_reference_action_imitation.py::_split_list()` did not decode `__COMMA__`.
- Therefore `--collection_teacher_alphas` was parsed as one token and attempted as `float("0.50__COMMA__0.75__COMMA__1.00")` after checkpoint restore. This matches the failure location and explains why no collection/training artifacts exist.
- `_parse_float_map()` already handled this encoding, so map args were not the issue.

Fix:
- Patched `_split_list()` to replace `__COMMA__` with literal commas before splitting.
- This also fixes `--residual_context_features phase__COMMA__teacher_alpha`.

Validation:
- passed: `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/residual_action_adapter.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py`
- passed: `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh && bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh && git diff --check`
- passed local parser sanity: `0.50__COMMA__0.75__COMMA__1.00 -> [0.5, 0.75, 1.0]`; `phase__COMMA__teacher_alpha -> ['phase', 'teacher_alpha']`.

Next:
- Commit/push/deploy the parser fix and relaunch the same bounded supervised-only stage/alpha BC job under a new run name.
- No selector/video/PPO/RL launch unless the supervised gate passes after fetching and inspecting the report/metrics/plots.

Active Jobs:
- none after canceling `1028133`.

## 2026-06-11T22:03:00-07:00 - stage/alpha-conditioned assisted-manifold BC relaunch

Goal:
- Relaunch the same supervised-only alpha0.5/0.75/1.0 assisted-manifold residual BC after fixing Slurm-safe list argument decoding.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- local_commit: `9a3d7387565f7f3ae10de2f280cb88268effac0a`
- branch: `codex/franka-cube-trajectory-tracking`
- push/pull: pushed to origin; deployed to l401 with HTTPS fetch because SSH GitHub auth fails on l401.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `9a3d7387565f7f3ae10de2f280cb88268effac0a`, clean.

Command / Job:
- job_id: `1028136`
- job_name: `bc_stagealpha2`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_stagealpha2 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=600,BATCH_SIZE=1024,LEARNING_RATE=0.0001,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=73,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHAS=0.50__COMMA__0.75__COMMA__1.00,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p50=1__COMMA__current_teacher_mix_alpha0p75=1__COMMA__current_teacher_mix_alpha1p00=1,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p50_l2=1__COMMA__val_source_current_teacher_mix_alpha0p75_l2=1__COMMA__val_source_current_teacher_mix_alpha1p00_l2=1,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=256,RESIDUAL_MAX_ACTION=1.0,RESIDUAL_GATE_ENABLED=False,RESIDUAL_CONTEXT_FEATURES=phase__COMMA__teacher_alpha,RESIDUAL_L2_WEIGHT=0.0005,SOURCE_PROBE_STEPS=200,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028136.out`
- expected_artifacts: `bc_metrics.json`, `bc_loss_curve.csv`, `bc_loss_plot.png`, `bc_source_metric_plot.png`, oracle residual CSV/plots, `reference_action_dataset.pt`, `nn/bc_reference_action_imitation.pth`, `report.md`

Acceptance / Gate:
- supervised report/metrics/plots only first.
- No selector/video/PPO/RL unless the supervised source metrics pass after artifact inspection.
- Compact reference caveat remains `curobo_validated=false`.

Active Jobs:
- `1028136` pending/running.

## 2026-06-11T22:05:00-07:00 - stage/alpha-conditioned assisted-manifold BC supervised result

Job:
- job_id: `1028136`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:26`, node `pool0-00030`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028136.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028136.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/report.md`
- source metric plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/bc_source_metric_plot.png`
- aggregate loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/bc_loss_plot.png`
- oracle residual plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/oracle_residual_plot.png`
- metrics: `cluster_results/l401/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/reference_action_dataset.pt`

Configuration Evidence:
- task registered with observation/action spaces `(72,) / (7,)`; baseline observation size is preserved.
- collection teacher alphas: `[0.5, 0.75, 1.0]`; no alpha0.10 data in this run.
- residual context features: `['phase', 'teacher_alpha']`.
- residual adapter: enabled, frozen tm0.25 base, hidden dim `256`, max action `1.0`, no gate, residual L2 weight `0.0005`.
- selected step/score: `600 / 0.08038045465946198`.
- source separability probe val accuracy `0.6530` vs baseline `0.3353`, so phase/obs context contains some source signal.
- compact trajectory reference remains `curobo_validated=false`.
- log scan: completed `BC Diagnostic Done`, no traceback/Hydra/runtime error.

Supervised Metrics:
- global val L2: frozen base `0.147099` -> selected `0.080459`.
- alpha0.50 val L2: frozen base `0.148781` -> selected `0.092877`; close/up/gripper abs `0.026820/0.026473/0.033492`.
- alpha0.75 val L2: frozen base `0.143247` -> selected `0.081952`; close/up/gripper abs `0.021229/0.018453/0.035998`.
- alpha1.00 val L2: frozen base `0.149302` -> selected `0.066312`; close/up/gripper abs `0.019375/0.015874/0.024634`.
- oracle residual clipping rate was `0.0` for all three sources at residual max `1.0`.

Verdict:
- supervised gate passes for a bounded selector eval: all three assisted-manifold sources improve materially over frozen tm0.25 base action error, context metadata is present, and the reference caveat remains explicit.
- This is not a policy-only success claim. It only authorizes metrics-only selector evals for alpha `0.0/0.25/0.5/0.75/1.0`; videos/contact sheets remain gated on selector metrics.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed learned-policy evidence.

Next:
- Commit/push this supervised result worklog.
- Launch selector evals from `/results/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/nn/bc_reference_action_imitation.pth` for alphas `0.0`, `0.25`, `0.5`, `0.75`, and `1.0`, no video initially.
- Fetch metrics/traces/reports before deciding whether targeted videos are justified.

Active Jobs:
- none after `1028136`.

## 2026-06-11T22:07:00-07:00 - stage/alpha-conditioned selector metrics launch

Goal:
- Run metrics-only selector evals from the supervised-passing stage/alpha checkpoint before any video generation.

Version Control:
- local_commit: `782f9a55e529264804135ce86736cfd941034da5`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached at `782f9a55e529264804135ce86736cfd941034da5`, clean.

Common Config:
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_stagealpha_tm025_a050_a075_a100_fix_20260611_220300/nn/bc_reference_action_imitation.pth`
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`
- action_source: `policy_reference_mix`
- num_envs/steps: `4 / 520`
- capture_video: `False`
- seed: `73`
- cube randomization: `0.08`
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`
- reference caveat: `curobo_validated=false`

Jobs:
- alpha0.00: job `1028138`, run `franka_cube_traj_tracking_bc_stagealpha_selector_a000_520_20260611_220700`
- alpha0.25: job `1028139`, run `franka_cube_traj_tracking_bc_stagealpha_selector_a025_520_20260611_220700`
- alpha0.50: job `1028140`, run `franka_cube_traj_tracking_bc_stagealpha_selector_a050_520_20260611_220700`
- alpha0.75: job `1028141`, run `franka_cube_traj_tracking_bc_stagealpha_selector_a075_520_20260611_220700`
- alpha1.00: job `1028142`, run `franka_cube_traj_tracking_bc_stagealpha_selector_a100_520_20260611_220700`

Acceptance:
- Fetch and inspect `metrics.json`, trace CSV/JSONL, logs, and train/eval consistency before deciding on videos.
- Target unsafe must remain `0`.
- Videos/contact sheets are only justified for policy-only failure/improvement, lowest-alpha success/improvement, and alpha1 context after metrics identify the relevant cases.
- No PPO/RL scale-up.

Active Jobs:
- `1028138`, `1028139`, `1028140`, `1028141`, `1028142`.

## 2026-06-11T21:12:52-07:00 - residual oracle/capacity diagnostic plan

Goal:
- Explain why the frozen-base residual adapter preserved tm0.25 but could not fit current alpha `0.10` labels.
- Stay supervised-only. No selector rollout, videos, PPO, RL, or scale-up unless supervised gates pass.

Hypothesis:
- The previous residual adapter failed either because the required label-minus-base residual on current alpha `0.10` states is too large for `RESIDUAL_MAX_ACTION=0.5`, because the shared residual cannot separate current alpha `0.10` states from tm0.25 rehearsal states while preserving tm0.25, or because the preservation/gating objective keeps the residual near zero globally.
- Measuring the oracle residual distribution first should decide whether increasing residual max/capacity is justified before another training run.

Planned Change:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` to compute and report oracle residual statistics:
  - oracle residual = `reference_action - frozen_base_action`.
  - per-source train/val L2, per-dimension mean/std/abs mean, percentiles, and `RESIDUAL_MAX_ACTION` saturation rate.
  - source-conditioned residual norms for current alpha `0.10` and tm0.25 rehearsal.
  - a small source-separability probe over observations, if feasible, so residual gating has an empirical basis.
- Extend `dextrah_lab/rl_games/residual_action_adapter.py` with optional observation-gated residual capacity while keeping the base actor frozen.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass new residual gating/oracle knobs.

Planned Analysis Job If Validation Passes:
- run name: `franka_cube_traj_tracking_bc_residual_oracle_tm025_tm010_<timestamp>`.
- input checkpoint: tm0.25 BC checkpoint `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- fresh collection: teacher_mix alpha `0.10`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`.
- rehearsal dataset: tm0.25 `reference_action_dataset.pt`.
- `TRAIN_STEPS=0`; this is analysis-only and will not be used for selector rollout.
- residual adapter enabled only to define the frozen-base/oracle context; no residual training in this first job.

Decision Gate For Any Follow-Up Training:
- tm0.25 rehearsal val L2 must remain preferred `<=0.045`, hard ceiling `<=0.055`.
- current alpha `0.10` val L2 must improve materially over residual `0.6875`, balanced `0.15143`, and ideally approach `~0.079`.
- residual magnitude on tm0.25 must stay near zero; base actor must remain frozen.
- If oracle stats show heavy residual clipping at `0.5`, a bounded follow-up can increase `RESIDUAL_MAX_ACTION`.
- If oracle stats show source separability/gating signal, a bounded follow-up can enable observation-gated residual.
- If neither condition holds, stop at analysis artifacts and do not launch training.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py dextrah_lab/rl_games/residual_action_adapter.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- commit/push and deploy exact commit to the l401 agent-owned worktree via Git before Slurm launch.

Notes:
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.
- Compact trajectory reference remains `curobo_validated=false`.

## 2026-06-11T20:58:05-07:00 - frozen-base residual adapter bounded plan

Goal:
- Preserve tm0.25 behavior by construction while testing whether a small learned residual can fit lower-assistance alpha `0.10` states.
- Keep this supervised-only unless the gate passes. No selector/video/PPO/RL scale-up from current B evidence.

Hypothesis:
- Previous full-actor BC, rehearsal, weighting, and additive distillation all updated the same actor parameters and either forgot tm0.25 behavior or underfit the current low-teacher source.
- A frozen tm0.25 base actor plus a zero-initialized residual action adapter changes only the residual path. The base actor weights remain exactly unchanged in the checkpoint.
- A strong residual-zero preservation term on tm0.25 rehearsal states can keep the residual near zero there, so tm0.25 behavior is preserved by construction plus an explicit supervised check, while the residual can still move lower-assistance current states toward reference labels.

Planned Change:
- Add a small reusable residual module under `dextrah_lab/rl_games/`, storing adapter architecture/state in checkpoint metadata rather than overwriting the base actor.
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py`:
  - `--residual_adapter_enabled`
  - `--residual_hidden_dim`
  - `--residual_max_action`
  - `--residual_preserve_sources`
  - `--residual_preserve_weight`
  - `--residual_l2_weight`
  - train only adapter parameters when enabled; base model remains frozen.
  - report base label error, final label error, residual magnitude, and base-preservation error per source.
- Extend `dextrah_lab/rl_games/eval_rollout.py` to apply the residual adapter only when checkpoint metadata is present, and log base/residual/final action metrics. This is needed only if the supervised gate later passes.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass and echo residual flags.

Planned Supervised Job If Validation Passes:
- run name: `franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_<timestamp>`.
- input checkpoint: tm0.25 BC checkpoint `/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth`.
- fresh collection: teacher_mix alpha `0.10`, `NUM_ENVS=8`, `COLLECTION_STEPS=520`.
- rehearsal dataset: tm0.25 `reference_action_dataset.pt`.
- objective:
  - `SOURCE_BATCH_MODE=balanced`.
  - reference-label loss only on fresh alpha `0.10`: `SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1,tm025_rehearsal=0`.
  - residual preservation on tm0.25: `RESIDUAL_PRESERVE_SOURCES=tm025_rehearsal`, `RESIDUAL_PRESERVE_WEIGHT=50`.
  - small residual head: `RESIDUAL_HIDDEN_DIM=64`, `RESIDUAL_MAX_ACTION=0.5`.
  - small residual L2 penalty: `RESIDUAL_L2_WEIGHT=0.001`.
  - selection score: current-source label L2 plus tm0.25 label L2, e.g. `BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1,val_source_tm025_rehearsal_l2=3`.

Supervised Gate:
- tm0.25 rehearsal val L2 preferred `<=0.045`, hard ceiling `<=0.055`.
- current alpha `0.10` source val L2 must improve materially vs latest distill `0.182791` and balanced `0.15143`; ideally approach `~0.079`.
- global val L2 must not regress relative to `1028053` (`0.094008`) if considering selector rollout.
- residual/base-preservation metrics must show tm0.25 residual magnitude near zero; otherwise stop at supervised artifacts.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py dextrah_lab/rl_games/residual_action_adapter.py`
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- commit/push and deploy exact commit to the l401 agent-owned worktree via Git before Slurm launch.

Notes:
- Old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.
- Compact trajectory reference remains `curobo_validated=false`.

## 2026-06-11T21:03:02-07:00 - frozen-base residual adapter supervised launch

Implementation:
- implementation commit: `6094b33c5daa283076a660e55a0061a3a2d75f9b` (`Add frozen-base residual BC diagnostic`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached at `6094b33c5daa283076a660e55a0061a3a2d75f9b` via the agent-owned l401 bare Git mirror.
- local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py dextrah_lab/rl_games/residual_action_adapter.py`
  - `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `git diff --check`
- local runtime adapter smoke was not available because this workstation Python lacks `torch`; runtime validation is the l401 DEXTRAH container.

Command / Job:
- job_id: `1028114`
- run_name: `franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302`
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_resid --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302,NUM_ENVS=8,COLLECTION_STEPS=520,TRAIN_STEPS=400,BATCH_SIZE=1024,LEARNING_RATE=0.00005,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=72,COLLECTION_ACTION_SOURCE=teacher_mix,COLLECTION_TEACHER_ALPHA=0.10,REHEARSAL_DATASET_PATHS=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/reference_action_dataset.pt,REHEARSAL_DATASET_NAMES=tm025_rehearsal,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_teacher_mix_alpha0p10=1__COMMA__tm025_rehearsal=0,BEST_SCORE_WEIGHTS=val_source_current_teacher_mix_alpha0p10_l2=1__COMMA__val_source_tm025_rehearsal_l2=3,EARLY_STOP_PATIENCE=8,RESIDUAL_ADAPTER_ENABLED=True,RESIDUAL_HIDDEN_DIM=64,RESIDUAL_MAX_ACTION=0.5,RESIDUAL_PRESERVE_SOURCES=tm025_rehearsal,RESIDUAL_PRESERVE_WEIGHT=50,RESIDUAL_L2_WEIGHT=0.001,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_dagger_tm025_all_20260611_185900/nn/bc_reference_action_imitation.pth cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028114.out`

Acceptance:
- supervised-only gate. No selector/video/PPO launch unless this run materially improves per-source metrics.
- tm0.25 rehearsal val L2 preferred `<=0.045`, hard ceiling `<=0.055`.
- current alpha `0.10` source val L2 must improve over latest distill `0.182791` and balanced `0.15143`; ideally approach `~0.079`.
- global val L2 should not regress relative to `1028053` (`0.094008`) if considering rollout.
- residual/base-preservation metrics must show tm0.25 residual magnitude near zero.

## 2026-06-11T21:05:35-07:00 - frozen-base residual adapter supervised result

Job:
- job_id: `1028114`
- scheduler state: `COMPLETED 0:0`, elapsed `00:01:08`, node `pool0-00030`.
- remote run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302`
- remote log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028114.out`
- local fetched run_dir: `cluster_results/l401/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302`
- local fetched log: `cluster_results/l401/slurm_logs/bc_franka_cube_1028114.out`

Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/report.md`
- aggregate loss plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/bc_loss_plot.png`
- source/residual plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/bc_source_metric_plot.png`
- metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/bc_metrics.json`
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_cube_traj_tracking_bc_dagger_residual_tm025_tm010_all_20260611_210302/reference_action_dataset.pt`

Configuration Evidence:
- residual adapter enabled: `true`.
- base actor checkpoint: tm0.25 BC checkpoint; base actor weights are frozen and stored unchanged in the output checkpoint.
- residual hidden dim / max action: `64 / 0.5`.
- residual preserve sources: `['tm025_rehearsal']`.
- residual preserve/l2 weights: `50.0 / 0.001`.
- reference-label source weights: `{'current_teacher_mix_alpha0p10': 1.0, 'tm025_rehearsal': 0.0}`.
- best-score weights: `{'val_source_current_teacher_mix_alpha0p10_l2': 1.0, 'val_source_tm025_rehearsal_l2': 3.0}`.
- selected checkpoint step: `400`; `early_stop_triggered=False`.
- reference caveat remains: compact reference is `curobo_validated=false`.

Supervised Metrics:
- frozen-base current alpha `0.10` source val L2: `0.703556`.
- selected current alpha `0.10` source val L2: `0.687492`; this is only a tiny improvement from base and is much worse than latest distill (`0.182791`) and balanced (`0.15143`), far from tm0.10 (`~0.079`).
- selected current alpha `0.10` close/up/gripper abs: `0.119141/0.221269/0.314976`.
- frozen-base tm0.25 rehearsal val L2: `0.035162`.
- selected tm0.25 rehearsal val L2: `0.038308`; this passes the preferred preservation gate (`<=0.045`).
- selected tm0.25 rehearsal close/up/gripper abs: `0.006304/0.012121/0.015197`.
- selected global val L2: `0.372653`, far worse than the rollout consideration ceiling from 1028053 (`0.094008`) because the current alpha `0.10` source remains largely unfitted.
- residual magnitude on current alpha `0.10` val source: `0.024956` L2.
- residual magnitude on tm0.25 rehearsal val source: `0.012248` L2.
- base-preservation error on tm0.25 rehearsal val source: `0.012135` L2.

Verdict:
- supervised gate failure.
- No selector sweep, no videos, no PPO, and no RL scale-up launched from this checkpoint.

Analysis:
- This attempt achieved the construction goal: the base actor was frozen and tm0.25 label behavior was preserved inside the preferred gate (`0.038308`).
- The same construction prevented meaningful correction on lower-assistance states. The residual stayed small on both sources; current alpha `0.10` val L2 improved by only `0.016063` from the frozen base (`0.703556 -> 0.687492`).
- The result is useful because it separates two failure modes:
  - full actor updates can fit current-source labels but damage tm0.25 behavior;
  - a strongly preserved residual adapter can preserve tm0.25 but cannot reach current-source labels at this constraint/weight setting.
- This does not justify rollout. If the project continues this line, the next supervised-only diagnostic should explore a more expressive or selectively gated residual with a weaker/harder preservation tradeoff, or collect lower-assistance data closer to tm0.25's reachable manifold. It should still gate on supervised metrics before any selector/video.
- tm0.25 remains the best B checkpoint; old `actionscale-rewinf-diag-video480-step-0.mp4` remains obsolete failed diagnostic evidence.

Active Jobs:
- No selector/video/PPO jobs launched for this attempt.

## 2026-06-11T21:42:53-07:00 - current handoff comparison tail marker

Status:
- Handoff comparison bundle generated locally from already completed/fetched artifacts; no new Slurm job, rollout, PPO, or RL scale-up launched.
- Source helper added: `dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py`.
- Bundle: `cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140`.

Viewer Artifacts:
- report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/report.md`
- success/lift plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_handoff_comparison_20260611_2140/handoff_success_lift_plot.png`
- alpha0.0 failure video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a000_env0_520_20260611_190600/videos/dagger-tm025-a000-env0-step-0.mp4`
- alpha0.5 lowest verified success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a050_env0_520_20260611_190600/videos/dagger-tm025-a050-env0-step-0.mp4`
- alpha0.75 success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a075_env0_520_20260611_190600/videos/dagger-tm025-a075-env0-step-0.mp4`
- alpha1.0 teacher context video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_vis_a100_env1_520_20260611_190600/videos/dagger-tm025-a100-env1-step-0.mp4`
- pure reference/teacher-force video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_phase100_520_20260611_172848/videos/tf-eval-a100-phase100-520-step-0.mp4`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_dagger_tm025_visual_action_semantics_20260611_1906/action_semantics_plot.png`
- residual negative/control plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_residual_gated_m15_tm025_tm010_20260611_212500/bc_source_metric_plot.png`

Verdict:
- tm0.25 remains the best B checkpoint for teacher-assisted trajectory tracking: alpha0.5/0.75/1.0 are `3/4` with target unsafe max `0` and validated videos.
- Policy-only alpha0.0 remains `0/4` and is not usable for RL handoff.
- Pure reference/teacher-force alpha1.0 phase1.0 is `3/4`, so reference/controller feasibility is not the blocker.
- Latest gated residual max1.5 is supervised-negative (`tm0.25 L2 0.0398`, current alpha0.10 L2 0.3885); it was not rolled out.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed learned-policy evidence.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py` passed.
- `git diff --check` passed.
- Referenced videos verified with `ffprobe`: all five are `1280x720`, `520` frames, `8.666667s`.

Active Jobs:
- none.

## 2026-06-11T23:26:00-07:00 - z+gripper reference-mix tail handoff

Status:
- Bounded z+gripper diagnostic is complete and inspected; no PPO/RL scale-up launched.
- Implementation commit remains `59bb44623f252257600a831e69ef4396813ab084` (`Add z and gripper mix diagnostic`), pushed before launch.
- This tail entry mirrors the full result block above so the current Worker B state is visible from the end of the worklog.

Jobs:
- `1028200` alpha0.10 previous-success env3: completed `0:0`.
- `1028201` alpha0.10 previous-failure env0: completed `0:0`.
- `1028202` alpha0.15 previous-success env1: completed `0:0`.
- `1028203` alpha0.15 previous-failure env0: completed `0:0`.
- `1028204` alpha0.20 previous-success env1: completed `0:0`.
- `1028205` alpha0.20 previous-failure env2: completed `0:0`.

Artifacts:
- combined report: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_zg100_20260611_2330/report.md`
- summary plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_zg100_20260611_2330/zgrip_override_summary.png`
- action-semantics plot: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_zg100_20260611_2330_action_semantics/action_semantics_plot.png`
- alpha0.10 previous-success regression video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a010_env3prevsucc_zg100_520_20260611_233000/videos/handoff-noreset-zgripref-a010_env3prevsucc-zg100-step-0.mp4`
- alpha0.10 previous-success regression contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a010_env3prevsucc_zg100_520_20260611_233000_artifacts/video_contact_sheet.png`
- alpha0.10 previous-failure video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a010_env0prevfail_zg100_520_20260611_233000/videos/handoff-noreset-zgripref-a010_env0prevfail-zg100-step-0.mp4`
- alpha0.15 env1 success video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a015_env1prevsucc_zg100_520_20260611_233000/videos/handoff-noreset-zgripref-a015_env1prevsucc-zg100-step-0.mp4`
- alpha0.15 env1 success contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a015_env1prevsucc_zg100_520_20260611_233000_artifacts/video_contact_sheet.png`
- alpha0.20 env2 failure video: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a020_env2prevfail_zg100_520_20260611_233000/videos/handoff-noreset-zgripref-a020_env2prevfail-zg100-step-0.mp4`
- alpha0.20 env2 failure contact sheet: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_zgripref_vis_a020_env2prevfail_zg100_520_20260611_233000_artifacts/video_contact_sheet.png`

Metrics:
- action source: `policy_reference_mix`, not policy-only.
- z and gripper override: `REFERENCE_MIX_Z_ALPHA=1.0`, `REFERENCE_MIX_GRIPPER_ALPHA=1.0`.
- alpha0.10/0.15/0.20 final success: `1/4`, `1/4`, `1/4`.
- compare against no-override alpha0.10/0.15/0.20: `1/4`, `2/4`, `3/4`.
- compare against gripper-only override alpha0.10/0.15/0.20: `2/4`, `2/4`, `2/4`.
- target unsafe max: `0` for all six runs.
- train/eval consistency: `bc_metadata_partial_pass`, mismatch count `0` for all six runs.
- compact reference remains `curobo_validated=false`.

Visual Verdict:
- alpha0.10 env3 regressed from a previous no-reset success: the gripper lifts out of contact and leaves the cube on the table by final frame.
- alpha0.15 env1 still holds a real lift; this is the only preserved success pattern.
- alpha0.20 env2 remains a miss: the gripper rises while the cube stays on the table.
- This is a coupled pose/contact/closure timing failure, not the old drift-away train/eval mismatch.

Decision:
- z+gripper open-loop override is negative and should not be used as a handoff target.
- preserve alpha0.20/no-reset as the best assisted gate for now.
- next bounded direction should be contact-aware: trigger terminal hold or close+lift changes only after verified finger/cube contact or lift evidence.
- no active B jobs after this handoff; old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed diagnostic evidence.

## 2026-06-11T23:31:42-07:00 - contact-aware terminal hold plan

Goal:
- Run the next bounded diagnostic requested by the orchestrator: contact/lift-aware terminal hold after low-alpha `policy_reference_mix`, with videos for success and regression cases.
- Preserve the baseline task and existing action sources; no PPO/RL scale-up.

Hypothesis:
- The z+gripper override failed because it changed lift/closure open-loop before a stable grasp existed. A safer terminal-hold route should only activate after evidence of contact in the late grasp/lift phase or after actual cube lift/success.
- If contact-aware hold improves alpha0.10/0.15/0.20 relative to no-hold, then the next trainable target is a contact-conditioned hold/handoff head. If it regresses or only preserves the already successful env1 pattern, the blocker remains approach/contact geometry and policy-only handoff is still not credible.

Planned Change:
- `dextrah_lab/rl_games/eval_rollout.py`: add opt-in `--hold_trigger_mode` while preserving current default trigger behavior. New mode will use `(phase >= hold_phase_start AND max_finger_to_cube_dist <= hold_contact_max_finger_dist) OR lift OR success`, so phase alone cannot trigger free-space hold.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`: export, echo, and pass `HOLD_TRIGGER_MODE`.
- `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`: include `hold_trigger_mode` and contact-after-phase rate in compact summaries and reports.

Validation Before Launch:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `git diff --check`
- Commit/push and deploy the exact commit to the l401 Worker B worktree via Git/HTTPS fallback if needed.

Planned Eval Probe:
- Action source: `policy_reference_mix_hold`.
- Checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- Reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).
- Common config: `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=True`, `SEED=75`, cube randomization `0.08`, `HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success`, `HOLD_PHASE_START=0.67`, `HOLD_CONTACT_MAX_FINGER_DIST=0.08`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_LIFT_HEIGHT=0.03`, `HOLD_GRIPPER_ACTION=-0.4`.
- Launch targeted videos for the same boundary camera envs: alpha0.10 env3/env0, alpha0.15 env1/env0, alpha0.20 env1/env2.

Acceptance:
- Each run writes metrics, trace CSV/JSONL, report, trace plot, consistency JSON, MP4, and contact sheet.
- Target unsafe max remains `0`; train/eval consistency has no real mismatches.
- Compare final/success-ever and visual behavior against no-hold, gripper-only, and z+gripper. No PPO/RL launch unless this establishes a better handoff target with inspectable videos.

Implementation:
- `eval_rollout.py` now supports `--hold_trigger_mode` with choices:
  - `any`: legacy phase OR lift OR success OR contact trigger behavior.
  - `contact_after_phase_or_lift_success`: no phase-only hold; trigger is `(phase AND contact) OR lift OR success`.
  - `lift_success_only`: ignores phase/contact triggers.
- `eval_rollout.py` logs `hold_trigger_mode_id` and `hold_contact_after_phase_trigger_rate`.
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` exports, echoes, and passes `HOLD_TRIGGER_MODE`.
- `summarize_traj_tracking_eval_artifacts.py` includes the trigger mode and contact-after-phase trigger rate in reports/summary.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py` passed.
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` passed.
- `git diff --check` passed.
- summarizer regression on old z+gripper metrics wrote `/tmp/traj_contact_hold_summary_regression/{report.md,summary.json,train_eval_consistency.json,trajectory_trace_plot.png}` and reports missing trigger-mode fields as `n/a`.

Version Control:
- implementation_commit: `d0098ae5f0979c5d127fd07cdc6969634c88c296` (`Add contact-aware hold trigger mode`), pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking` detached clean at `d0098ae5f0979c5d127fd07cdc6969634c88c296`. Deployed with HTTPS fetch because l401 GitHub SSH auth remains unavailable.
- changed_files:
  - `dextrah_lab/rl_games/eval_rollout.py`
  - `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

## 2026-06-11T23:36:00-07:00 - contact-aware terminal hold video launch

Version Control:
- launch_commit: `287ed11479e04eddc086930e9eb02d1b4655c81b` (`Record contact-aware hold implementation`), pushed.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached clean at `287ed11479e04eddc086930e9eb02d1b4655c81b`.

Common Config:
- task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
- action source: `policy_reference_mix_hold`.
- checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
- reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).
- `HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success`, `HOLD_PHASE_START=0.67`, `HOLD_CONTACT_MAX_FINGER_DIST=0.08`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_LIFT_HEIGHT=0.03`, `HOLD_GRIPPER_ACTION=-0.4`.
- `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `VIDEO_LENGTH=520`, `CAPTURE_VIDEO=True`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.

Jobs:
- alpha0.10 previous-success env3: job `1028224`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a010_env3prevsucc_520_20260611_233600`.
- alpha0.10 previous-failure env0: job `1028225`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a010_env0prevfail_520_20260611_233600`.
- alpha0.15 previous-success env1: job `1028226`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a015_env1prevsucc_520_20260611_233600`.
- alpha0.15 previous-failure env0: job `1028227`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a015_env0prevfail_520_20260611_233600`.
- alpha0.20 previous-success env1: job `1028228`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env1prevsucc_520_20260611_233600`.
- alpha0.20 previous-failure env2: job `1028229`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env2prevfail_520_20260611_233600`.

Acceptance:
- Fetch logs and run dirs after completion; generate per-run reports/contact sheets/trace plots and a combined comparison report.
- Validate MP4 metadata and visually inspect success/regression cases.
- Target unsafe max must remain `0`; train/eval consistency should have no real mismatches.
- No PPO/RL scale-up until this result is inspected.

Active Jobs:
- `1028224`, `1028225`, `1028226`, `1028227`, `1028228`, `1028229`.

Result:
- jobs `1028224`-`1028229` completed `0:0`; fetched logs and run dirs locally under `cluster_results/l401/`.
- Per-run artifact summarizer generated `report.md`, `summary.json/csv`, `success_diagnostics.json/csv`, `success_window_trace.csv`, `trajectory_trace_plot.png`, `train_eval_consistency.json`, and `video_contact_sheet.png`.
- MP4 validation passed for all six videos: 1280x720, 520 frames, 8.67 s.
- Combined artifact bundle:
  - report: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_comparison_20260611_233600/report.md
  - plot: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_comparison_20260611_233600/contacthold_comparison_plot.png
  - summary CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_comparison_20260611_233600/summary.csv`
  - aggregate CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_comparison_20260611_233600/aggregate_summary.csv`

Metrics:
- contact-aware hold alpha0.10: final success `3/4`, success ever `3/4`, max lift `0.2878 m`, final lift `0.2827 m`, done count `0`, target unsafe max `0`, target clearance final/min trace `0.2651 m`.
- contact-aware hold alpha0.15: final success `3/4`, success ever `3/4`, max lift `0.2668 m`, final lift `0.2612 m`, done count `0`, target unsafe max `0`, target clearance final/min trace `0.2651 m`.
- contact-aware hold alpha0.20: final success `3/4`, success ever `3/4`, max lift `0.2575 m`, final lift `0.2537 m`, done count `0`, target unsafe max `0`, target clearance final/min trace `0.2651 m`.
- Hold trigger mode was `contact_after_phase_or_lift_success`; final hold active rate was `0.75` in the contact-aware runs. Final contact-after-phase trigger rate was `0.50` for alpha0.10 and `0.25` for alpha0.15/0.20; final lift-trigger rate was `0.25` for alpha0.10 and `0.50` for alpha0.15/0.20.
- Comparison against prior assisted boundary probes:
  - no-hold: alpha0.10/0.15/0.20 final success `1/4`, `2/4`, `3/4`.
  - gripper-only override: alpha0.10/0.20 final success `2/4`, `2/4`.
  - z+gripper override: alpha0.10/0.15/0.20 final success `1/4`, `1/4`, `1/4`.
  - contact-aware hold: alpha0.10/0.15/0.20 final success `3/4`, `3/4`, `3/4`.

Visual Artifacts:
- alpha0.10 previous-failure env0 recovered:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a010_env0prevfail_520_20260611_233600_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a010_env0prevfail_520_20260611_233600/videos/handoff-noreset-contacthold-a010_env0prevfail-step-0.mp4
- alpha0.15 previous-failure env0 recovered:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a015_env0prevfail_520_20260611_233600_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a015_env0prevfail_520_20260611_233600/videos/handoff-noreset-contacthold-a015_env0prevfail-step-0.mp4
- alpha0.20 previous-success env1 remains successful:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env1prevsucc_520_20260611_233600_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env1prevsucc_520_20260611_233600/videos/handoff-noreset-contacthold-a020_env1prevsucc-step-0.mp4
- alpha0.20 previous-failure env2 remains a visible failure/regression example despite aggregate `3/4` success:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env2prevfail_520_20260611_233600_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vis_a020_env2prevfail_520_20260611_233600/videos/handoff-noreset-contacthold-a020_env2prevfail-step-0.mp4

Train/Eval Audit:
- `train_eval_consistency.json` status is `bc_metadata_partial_pass`: available BC metadata matches task/action/observation dims, reference path, min target gripper width, reference duration, and `curobo_validated=false`.
- Missing keys are unavailable in the old BC metadata, not detected mismatches. Intentional eval-only overrides are `ACTION_SOURCE=policy_reference_mix_hold`, targeted `CAMERA_ENV_INDEX`, alpha sweep values, `SUPPRESS_SUCCESS_TERMINATION=True`, and `HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success`.

Analysis:
- Contact-aware terminal hold is the best assisted boundary result so far and fixes the alpha0.10/0.15 boundary better than direct gripper-only or z+gripper overrides.
- The improvement is still assisted `policy_reference_mix_hold`, not policy-only. Alpha0 policy-only remains previously failed, so this is not a PPO/RL scale-up gate.
- Visual inspection shows real late lift/hold for alpha0.10 env0/env3, alpha0.15 env0, and alpha0.20 env1. Alpha0.20 env2 still fails with the cube on the table at the final frame, so the remaining failure is not an old train/eval drift mismatch; it is residual grasp/contact/hold robustness.

Next:
- Treat contact-aware hold as the best current handoff target for B. The next bounded step should be supervised/trainability work that learns the contact-conditioned terminal hold or reduces assistance from this improved assisted manifold, with visual alpha0/low-alpha gates before any PPO/RL scale-up.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` / job `1027753` remains obsolete failed diagnostic evidence.
- Active jobs after result fetch: none.

## 2026-06-11T23:43:35-07:00 - lower-alpha contact-aware hold selector plan

Goal:
- Reduce assistance below the current alpha0.10 contact-aware hold boundary without changing training or launching PPO/RL.
- Identify whether `policy_reference_mix_hold` with verified contact/lift-triggered terminal hold can succeed at alpha0.075, alpha0.05, alpha0.025, or alpha0.0.

Hypothesis:
- Contact-aware hold fixed the low-alpha boundary by avoiding phase-only free-space hold. If the learned policy can get close enough for contact/lift evidence with less reference assistance, lower alphas should still trigger terminal hold and sustain lift.
- If alpha0.0/0.025/0.05 fail while alpha0.075 or 0.10 works, the next trainability target is not a new open-loop override; it is learning the approach/contact prefix before the contact-aware terminal handoff.

Planned Probe:
- First run a metrics-only selector sweep for `REFERENCE_MIX_ALPHA=0.0,0.025,0.05,0.075,0.10`, no video, same seed/config as the accepted contact-aware run.
- Common config:
  - task: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
  - action source: `policy_reference_mix_hold`.
  - checkpoint: `/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth`.
  - reference: `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json` (`curobo_validated=false`).
  - `HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success`, `HOLD_PHASE_START=0.67`, `HOLD_CONTACT_MAX_FINGER_DIST=0.08`, `HOLD_TRIGGER_LIFT_HEIGHT=0.02`, `HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset`, `HOLD_LIFT_HEIGHT=0.03`, `HOLD_GRIPPER_ACTION=-0.4`.
  - `SUPPRESS_SUCCESS_TERMINATION=True`, `NUM_ENVS=4`, `NUM_STEPS=520`, `CAPTURE_VIDEO=False`, `SEED=75`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`.
- If selector metrics identify a lower-alpha success/improvement, launch targeted videos/contact sheets for:
  - lowest-alpha success camera env(s),
  - alpha0.0 or nearest failed alpha control,
  - alpha0.10 context only if needed.

Acceptance:
- Selector produces metrics/trace/report/plot/consistency JSON for every alpha.
- Target unsafe max remains `0`; done count remains `0` under no-reset mode.
- Any new claimed lower-alpha boundary must have a short labeled MP4/contact sheet before it is treated as real.
- No PPO/RL scale-up from selector metrics alone.

Launch:
- launch_commit: `4639602304be0e8210060898ff23164554fc537f` (`Plan lower-alpha contact-aware hold selector`), pushed.
- remote source: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached clean at `4639602304be0e8210060898ff23164554fc537f`.
- command: `sbatch cluster/sbatch_eval_franka_cube_grasp_1gpu.sh` with the common config above and `CAPTURE_VIDEO=False`.
- alpha0.0: job `1028232`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_selector_a000_520_20260611_234600`.
- alpha0.025: job `1028233`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_selector_a0025_520_20260611_234600`.
- alpha0.05: job `1028234`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_selector_a005_520_20260611_234600`.
- alpha0.075: job `1028235`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_selector_a0075_520_20260611_234600`.
- alpha0.10: job `1028236`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_selector_a010_520_20260611_234600`.
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_<job>.out`.
- expected artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/<run>/{metrics.json,trace.csv,trace.jsonl}`.

Active Jobs:
- `1028232`, `1028233`, `1028234`, `1028235`, `1028236`.

Selector Result:
- jobs `1028232`-`1028236` completed `0:0`; fetched metrics/traces/logs locally.
- Per-run summaries generated under `cluster_results/l401/<run>_artifacts/`.
- alpha0.0: final success `2/4`, success ever `2/4`, max lift `0.2307 m`, done count `0`, target unsafe max `0`, success envs `[1,3]`, failure envs `[0,2]`.
- alpha0.025: final success `2/4`, success ever `2/4`, max lift `0.2993 m`, done count `0`, target unsafe max `0`, success envs `[0,1]`, failure envs `[2,3]`.
- alpha0.05: final success `3/4`, success ever `3/4`, max lift `0.2875 m`, done count `0`, target unsafe max `0`, success envs `[0,1,3]`, failure env `[2]`.
- alpha0.075: final success `3/4`, success ever `3/4`, max lift `0.2844 m`, done count `0`, target unsafe max `0`.
- alpha0.10: final success `3/4`, success ever `3/4`, max lift `0.2878 m`, done count `0`, target unsafe max `0`.

Analysis:
- The lower-alpha selector improved the assisted boundary again: alpha0.05 is now the lowest `3/4` no-reset contact-aware hold setting, and alpha0.0 reaches `2/4` once terminal hold is allowed to trigger after contact evidence.
- This is still not policy-only success. Action source remains `policy_reference_mix_hold`; alpha0.0 means policy prefix plus contact-aware terminal hold, not an autonomous policy rollout.
- Need visual confirmation before treating alpha0.05 as the new assisted boundary or interpreting alpha0.0 successes.

Targeted Video Launch:
- alpha0.0 success env1: job `1028240`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env1succ_520_20260611_235000`.
- alpha0.0 failure env0: job `1028241`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env0fail_520_20260611_235000`.
- alpha0.05 success env0: job `1028242`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env0succ_520_20260611_235000`.
- alpha0.05 failure env2: job `1028243`, run `franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env2fail_520_20260611_235000`.
- common video config: same selector config with `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=520`, targeted `CAMERA_ENV_INDEX`.

Active Jobs:
- `1028240`, `1028241`, `1028242`, `1028243`.

Targeted Video Result:
- jobs `1028240`-`1028243` completed `0:0`; fetched logs and run dirs locally.
- Per-run reports/contact sheets/trace plots generated under `cluster_results/l401/<run>_artifacts/`.
- MP4 validation passed for all four targeted videos: 1280x720, 520 frames, 8.67 s.
- Combined low-alpha artifact bundle:
  - report: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/report.md
  - plot: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/lowalpha_contacthold_plot.png
  - selector summary CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/selector_summary.csv`
  - targeted video summary CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/targeted_video_summary.csv`

Metrics:
- alpha0.0 selector: final success `2/4`, success envs `[1,3]`, failure envs `[0,2]`, max lift `0.2307 m`, done count `0`, target unsafe max `0`, final contact-after-phase trigger rate `0.75`.
- alpha0.025 selector: final success `2/4`, success envs `[0,1]`, failure envs `[2,3]`, max lift `0.2993 m`, done count `0`, target unsafe max `0`, final contact-after-phase trigger rate `0.75`.
- alpha0.05 selector: final success `3/4`, success envs `[0,1,3]`, failure env `[2]`, max lift `0.2875 m`, done count `0`, target unsafe max `0`, final contact-after-phase trigger rate `0.75`.
- alpha0.075 selector: final success `3/4`, success envs `[0,1,3]`, max lift `0.2844 m`, done count `0`, target unsafe max `0`.
- alpha0.10 selector: final success `3/4`, success envs `[0,1,3]`, max lift `0.2878 m`, done count `0`, target unsafe max `0`.

Visual Artifacts:
- alpha0.0 env1 success:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env1succ_520_20260611_235000_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env1succ_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a000_env1succ-step-0.mp4
- alpha0.0 env0 failure:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env0fail_520_20260611_235000_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env0fail_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a000_env0fail-step-0.mp4
- alpha0.05 env0 success:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env0succ_520_20260611_235000_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env0succ_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a005_env0succ-step-0.mp4
- alpha0.05 env2 failure:
  - sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env2fail_520_20260611_235000_artifacts/video_contact_sheet.png
  - video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env2fail_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a005_env2fail-step-0.mp4

Visual Diagnosis:
- alpha0.0 env1 is a real assisted handoff success: the learned policy prefix gets usable contact, then contact-aware terminal hold lifts and maintains the cube.
- alpha0.0 env0 is the paired failure: the hand reaches/touches but does not lift, so alpha0.0 is not a reliable handoff gate.
- alpha0.05 env0 visually confirms the new lowest `3/4` assisted boundary with sustained final lift.
- alpha0.05 env2 remains a visible failure where the hand gets around the cube but closure/hold is insufficient and the cube remains on the table.

Train/Eval Audit:
- Available BC metadata still matches task/action/observation dims, reference path, reference duration, min target gripper width, and `curobo_validated=false`.
- Consistency status remains `bc_metadata_partial_pass` only because the old BC metadata lacks some eval-only reward/hold keys. Intentional eval-only overrides: `ACTION_SOURCE=policy_reference_mix_hold`, `HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success`, `SUPPRESS_SUCCESS_TERMINATION=True`, alpha values, and targeted `CAMERA_ENV_INDEX`.

Analysis:
- New best assisted boundary is alpha0.05 contact-aware hold (`3/4` final success, no resets, target unsafe max `0`, visually confirmed).
- Alpha0.0 can succeed in `2/4` with contact-aware terminal hold, which means the policy prefix sometimes reaches usable contact, but it is not reliable and it is still not policy-only because the terminal hold controller is doing the lift/hold.
- This result supports a clean handoff target: learn a reliable approach/contact prefix that reaches terminal-hold trigger states, or train a contact-conditioned hold/handoff head. It does not justify PPO/RL scale-up yet.

Next:
- Keep alpha0.05 contact-aware hold as the current best low-assistance assisted gate.
- Next bounded work should be supervised/trainability: collect or label states around successful alpha0.0/0.05 contact trigger windows and explicitly train the policy to reproduce the successful approach/contact prefix before terminal hold. Keep alpha0 and alpha0.05 videos as gates.
- Active B jobs after artifact fetch: none.

## 2026-06-11 23:59 PDT - contact-window handoff BC collection plan

Goal:
- Start the next bounded trainability step around the successful alpha0.0/alpha0.05 contact-trigger windows, without PPO/RL scale-up.

Hypothesis:
- The alpha0.0 and alpha0.05 `policy_reference_mix_hold` results show that the current policy sometimes reaches usable contact, then the terminal hold controller can lift/hold. A supervised dataset collected under the exact contact-aware hold controller, plus a derived source of post-trigger lift/contact windows relabeled with alpha0 context, should tell whether the policy/action parameterization can learn that prefix/handoff target before any closed-loop training.

Planned Change:
- Extend `dextrah_lab/rl_games/bc_reference_action_imitation.py` with a diagnostic-only `policy_reference_mix_hold` collection action source that mirrors eval-time policy/reference blending plus contact-aware terminal hold.
- Extend `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to pass the hold/mix env vars used by the accepted alpha0.05 contact-aware hold gate.
- Keep labels as `compute_reference_delta_actions()` and action source labels explicit; this is assisted/handoff BC, not policy-only and not PPO/RL.

Planned Validation:
- Local cheap checks: `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py`, `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`, `git diff --check`.
- Commit/push and deploy the exact commit to the agent-owned l401 worktree.
- Launch one small supervised-only L401 BC job with `COLLECTION_ACTION_SOURCE=policy_reference_mix_hold`, alphas `0.0,0.05`, contact-aware hold settings, and a derived handoff source selected by phase/lift/safety.

Supervised Gate Before Any Selector/Video:
- `bc_metrics.json`, `bc_loss_curve.csv`, source plots, oracle/source metrics, and report must be present and inspectable.
- Handoff source must select nonzero lift/contact samples; target unsafe must remain clean.
- Source validation should improve on the selected handoff/contact-window source without destroying the base alpha0/alpha0.05 collection sources. If this gate is weak or contradictory, stop at supervised artifacts and do not launch selector/video/PPO.

Expected Run:
- run name target: `franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_<timestamp>`.
- result root: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/<run>`.
- local fetch root: `cluster_results/l401/<run>`.

Implementation Update:
- Added `policy_reference_mix_hold` as a BC collection action source, with contact-aware terminal hold state isolated as `_bc_terminal_hold_state`.
- Added collection tensors for `max_finger_to_cube_dist`, `hold_active`, and `hold_contact_after_phase` so the supervised report can audit contact-trigger windows directly.
- Added handoff source filters `--handoff_max_finger_dist` and `--handoff_require_hold_active`.
- Extended the L401 BC wrapper to echo/pass reference-mix and hold/handoff env vars.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py` passed.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` passed.
- `git diff --check` passed.

Current Framing:
- This remains assisted/handoff training. The current best videos are `policy_reference_mix_hold`, and alpha0.0 successes still use terminal hold after contact evidence. No policy-only RL success is claimed.

Version Control / Deployment:
- implementation_commit: `4cf2baeb5b36ed91e5b984b9b082c3f99f43878e` (`Add contact-hold BC collection source`).
- pushed branch: `codex/franka-cube-trajectory-tracking`.
- remote deploy: l401 GitHub fetch failed with `Permission denied (publickey)`, so the exact branch delta was deployed to the agent-owned worktree via a temporary Git bundle and fetched with Git.
- remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`.
- remote commit/status: `4cf2baeb5b36ed91e5b984b9b082c3f99f43878e`, detached HEAD, clean.

Planned Launch:
- job_name: `bc_chold_handoff`.
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=bc_chold_handoff --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_<timestamp>,CHECKPOINT=/results/bc/franka_cube_traj_tracking_bc_handoff_success_alpha0_20260611_223200/nn/bc_reference_action_imitation.pth,NUM_ENVS=4,COLLECTION_STEPS=520,TRAIN_STEPS=300,BATCH_SIZE=1024,LEARNING_RATE=0.0001,VALIDATION_FRACTION=0.2,LOSS_DIMS=all,EVAL_INTERVAL=25,SEED=77,COLLECTION_ACTION_SOURCE=policy_reference_mix_hold,COLLECTION_TEACHER_ALPHAS=0.00__COMMA__0.05,HOLD_TRIGGER_MODE=contact_after_phase_or_lift_success,HOLD_PHASE_START=0.67,HOLD_CONTACT_MAX_FINGER_DIST=0.08,HOLD_TRIGGER_LIFT_HEIGHT=0.02,HOLD_TARGET_POLICY=cube_current_plus_trigger_ee_offset,HOLD_LIFT_HEIGHT=0.03,HOLD_GRIPPER_ACTION=-0.4,HANDOFF_SOURCE_ENABLED=True,HANDOFF_SOURCE_SOURCES=current_policy_reference_mix_hold_alpha0p00__COMMA__current_policy_reference_mix_hold_alpha0p05,HANDOFF_SOURCE_NAME=contacthold_success_handoff_alpha0,HANDOFF_TEACHER_ALPHA=0.0,HANDOFF_MIN_PHASE=0.67,HANDOFF_MAX_PHASE=1.01,HANDOFF_MIN_LIFT_HEIGHT=0.02,HANDOFF_MAX_FINGER_DIST=0.08,HANDOFF_REQUIRE_HOLD_ACTIVE=True,HANDOFF_REQUIRE_SUCCESS=False,HANDOFF_REQUIRE_SAFE_TARGET=True,HANDOFF_MAX_SAMPLES=0,SOURCE_BATCH_MODE=balanced,SOURCE_LOSS_WEIGHTS=current_policy_reference_mix_hold_alpha0p00=1__COMMA__current_policy_reference_mix_hold_alpha0p05=1__COMMA__contacthold_success_handoff_alpha0=2,BEST_SCORE_WEIGHTS=val_source_current_policy_reference_mix_hold_alpha0p00_l2=1__COMMA__val_source_current_policy_reference_mix_hold_alpha0p05_l2=1__COMMA__val_source_contacthold_success_handoff_alpha0_l2=2,EARLY_STOP_PATIENCE=5,SOURCE_PROBE_STEPS=200,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`.
- acceptance: supervised artifacts only first; do not launch selector/video/PPO unless the report shows nonzero contact/hold handoff samples and coherent per-source validation.

Launch:
- job_id: `1028250`.
- run_name: `franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700`.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700`.
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028250.out`.
- action source label: assisted `policy_reference_mix_hold` collection with alphas `0.0,0.05`; still not policy-only RL.
- active_jobs: `1028250`.

Shutdown Handoff Update:
- User requested stop/development shutdown before further debugging or selector/video launch.
- job `1028250` reached `COMPLETED 0:0` in `00:01:16` on `pool0-00030`; no active B Slurm jobs remain.
- The log printed completed supervised metrics and `BC Diagnostic Done`, but the result directory has not been fetched/opened locally due shutdown.
- Visible stdout metrics: derived `contacthold_success_handoff_alpha0` selected `94` train + `24` val samples; selected step `300`; selected score `0.1256902925670147`; handoff val L2 `0.0222403556`; alpha0.00 collection val L2 `0.2409972697`; alpha0.05 collection val L2 `0.2172831893`; global val L2 `0.2230899781`; reference remains `curobo_validated=false`.
- Handoff file written at `worklogs/franka-cube-grasp-prior/HANDOFF_B.md`.
- Do not claim policy-only RL success; this remains assisted/handoff BC and needs artifact fetch/full supervised review before any selector/video/PPO.

## 2026-06-12T00:40:14-07:00 - clean tracking-loss RL preflight fix

Goal:
- Convert the trajectory-tracking branch back to a clean RL-with-tracking-loss path before any PPO launch.
- Find or rule out branch-specific bugs instead of trusting the handoff diagnostics.

Hypothesis:
- The previous tracking branch was not a clean tracking-loss RL setup because the default tracking env rewarded reference-action imitation (`trajectory_tracking_action_alignment_weight=1.5`) and wrappers exposed teacher-force/action-alignment overrides.
- The tracking shaping also faded from `1.0` to `0.0`, which can remove the reference objective during training. Upstream Franka cube PPO is known good, so the safest first fix is to keep upstream PPO/task plumbing and make reference use strictly task-space reward shaping.

Change:
- Disabled the default action-alignment reward by setting `trajectory_tracking_action_alignment_weight=0.0`.
- Kept tracking loss constant by setting `trajectory_tracking_end_weight=1.0`.
- Removed teacher-force/action-alignment override plumbing from production train/validate/eval wrappers.
- Made tracking train wrapper require an explicit `TRAJECTORY_TRACKING_REFERENCE_PATH`.
- Added validation checks for clean tracking config, explicit reference path, end-of-reference phase progress, disabled action-alignment reward, disabled teacher forcing, constant curriculum, and safe runtime targets.
- Guarded `policy_reference_mix`, `policy_reference_mix_hold`, and `reference_delta_hold` eval modes behind `ALLOW_DIAGNOSTIC_ACTION_SOURCES=True`; guarded assisted BC collection the same way for `policy_reference_mix_hold`.

Version Control:
- agent_id: `franka-cube-traj-tracking`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `03d4dae`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`
  - `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
  - `cluster/sbatch_train_teacher_8gpu.sh`
  - `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
  - `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
  - `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/bc_reference_action_imitation.py` passed.
- `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` passed.
- `git diff --check` passed.

Version Control Update:
- implementation_commit: `01650b275c7d69bd8e3d4e10e1f33fc1c70ef2d0` (`Clean trajectory tracking RL preflight`).
- push: pushed to `origin/codex/franka-cube-trajectory-tracking`.
- remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`, detached clean at `01650b275c7d69bd8e3d4e10e1f33fc1c70ef2d0`.
- remote deploy: used HTTPS fetch on l401 because GitHub SSH auth is still unavailable there.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=128G --time=0-00:45:00 --job-name=traj_preflight --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_clean_preflight_20260612_004500,NUM_ENVS=4,NUM_STEPS=480,CAPTURE_VIDEO=False,VIDEO_LENGTH=480,PRINT_INTERVAL=120,SEED=42,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `1028252`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_traj_tracking_clean_preflight_20260612_004500`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1028252.out`
- acceptance: validation metrics must pass; specific required checks include clean tracking config, explicit reference path, retimed phase reaches reference end, safe targets, action-alignment reward disabled, teacher forcing disabled, and constant curriculum.

Next:
- Monitor job `1028252`, fetch metrics/logs, inspect pass/fail records, and only then decide whether a tiny PPO smoke is warranted.

Validation Result:
- job `1028252` completed and printed `Validation Done`.
- fetched local metrics: `cluster_results/l401/franka_cube_traj_tracking_clean_preflight_20260612_004500/metrics.json`.
- fetched local log: `cluster_logs/l401/slurm_logs/dextrah/validate_franka_cube_1028252.out`.
- status: passed, failed checks `[]`.
- clean preconditions passed:
  - explicit reference path configured: true.
  - clean tracking config: true.
  - runtime duration within episode: true.
  - gripper width policy: true, runtime min width `0.024 m`.
  - targets clear table: true, min batch target clearance `0.065114 m`.
  - runtime target unsafe rate max `0.0`.
  - phase reaches reference end: true, final/max phase `1.0/1.0`.
  - action-alignment disabled: true, reward ceiling mean `0.0`.
  - teacher forcing disabled: true, alpha mean `0.0`.
  - curriculum constant: true, min/max `1.0/1.0`.
- reference summary: `graspgenx_source=true`, planner `graspgenx_curobo_trajectory_json`, source duration `22.033333 s`, runtime duration `8.0 s`, `curobo_validated=false`, validation records passed.
- analysis: environment/task preconditions for clean tracking-loss RL are now correct enough for a tiny PPO smoke. Exact CuRobo collision-validation provenance is still caveated by the reference metadata and should stay explicit.

## 2026-06-12T00:52:00-07:00 - clean PPO smoke launch

Goal:
- Verify that the clean tracking-loss RL task launches under PPO with upstream Franka cube hyperparameters scaled down for a one-GPU smoke, without action mixing, teacher forcing, or action-alignment rewards.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=traj_rl_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,FULL_EXPERIMENT_NAME=franka_cube_traj_tracking_clean_ppo_smoke_20260612_005200,NUM_ENVS=16,MAX_ITERATIONS=5,HORIZON_LENGTH=32,MINIBATCH_SIZE=512,CENTRAL_VALUE_MINIBATCH_SIZE=512,MINI_EPOCHS=2,SAVE_FREQUENCY=1,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1028253`
- source_commit: remote worktree detached at `01650b275c7d69bd8e3d4e10e1f33fc1c70ef2d0`.
- expected run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_clean_ppo_smoke_20260612_005200`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1028253.out`
- acceptance: training exits cleanly, writes resolved config and checkpoints, reward terms are finite, `cube_traj_tracking_action_alignment_reward` is zero, teacher force logs remain zero, and no auto-resume/requeue occurs.

Next:
- Monitor `1028253`; fetch log/run artifacts; inspect reward/checkpoint/config before any larger PPO run.

PPO Smoke Result:
- job `1028253` completed and printed `Training Done`.
- fetched local run dir: `cluster_results/l401/franka_cube_traj_tracking_clean_ppo_smoke_20260612_005200/`.
- fetched local log: `cluster_logs/l401/slurm_logs/dextrah/teacher_8gpu_1028253.out`.
- resolved env config confirms clean settings:
  - `num_envs=16`, `observation_space=72`, `action_space=7`, `use_cuda_graph=false`.
  - `trajectory_tracking_reference_path=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.
  - `trajectory_tracking_action_alignment_weight=0.0`.
  - `trajectory_tracking_teacher_force_enabled=false`.
  - `trajectory_tracking_start_weight=1.0`, `trajectory_tracking_end_weight=1.0`.
  - `trajectory_tracking_reference_duration_s=8.0`, `trajectory_tracking_min_target_gripper_width=0.024`.
- resolved agent config confirms smoke overrides: `max_epochs=5`, `horizon_length=32`, `minibatch_size=512`, `multi_gpu=false`, `full_experiment_name=franka_cube_traj_tracking_clean_ppo_smoke_20260612_005200`.
- checkpoint written: `nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth` (`~8.0 MB`) plus runtime sidecar.
- stdout reached epochs 1/5 through 5/5 with finite FPS and no traceback/runtime error. The `rew_-inf` checkpoint suffix is expected because no env terminated during the intentionally tiny 5-epoch run.
- TensorBoard event file was zero bytes, so reward-term inspection from this smoke is limited to stdout and dumped configs.

## 2026-06-12T00:57:00-07:00 - clean policy-only eval smoke launch

Goal:
- Verify the tiny PPO checkpoint loads and rolls out with `ACTION_SOURCE=policy`, without `policy_reference_mix`, terminal hold, teacher forcing, or action-alignment overrides.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=160G --time=0-00:45:00 --job-name=traj_eval_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking,RUN_NAME=franka_cube_traj_tracking_clean_ppo_eval_smoke_20260612_005700,NUM_ENVS=4,NUM_STEPS=240,CAPTURE_VIDEO=False,VIDEO_LENGTH=240,PRINT_INTERVAL=60,ACTION_SOURCE=policy,DETERMINISTIC=True,USE_CUDA_GRAPH=False,SEED=43,CUBE_SPAWN_XY_RANDOMIZATION=0.08,TRAJECTORY_TRACKING_REFERENCE_PATH=/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_clean_ppo_smoke_20260612_005200/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1028254`
- expected run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_clean_ppo_eval_smoke_20260612_005700`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1028254.out`
- acceptance: eval exits cleanly, writes metrics/trace, `action_source=policy`, finite rewards/metrics, zero target-unsafe, no mixed/hold metrics except absent/none.

Next:
- Monitor `1028254`, fetch metrics/logs, inspect rollout summary, and then decide whether a longer one-GPU PPO run is justified.

Eval Smoke Result:
- job `1028254` completed and printed `Evaluation Done`.
- fetched local run dir: `cluster_results/l401/franka_cube_traj_tracking_clean_ppo_eval_smoke_20260612_005700/`.
- fetched local log: `cluster_logs/l401/slurm_logs/dextrah/eval_franka_cube_1028254.out`.
- checkpoint loaded successfully from the clean PPO smoke.
- metrics summary:
  - task `Dextrah-Franka-Cube-Grasp-Traj-Tracking`.
  - action source `policy` / notes `rl_games_policy`; `ALLOW_DIAGNOSTIC_ACTION_SOURCES=False`.
  - `num_steps_completed=240`, `num_steps_requested=240`, `num_envs=4`.
  - reward mean/final `1.57045` / `1.54220`.
  - final and ever success rates `0.0`; done count `0`. This is expected for a 5-epoch checkpoint and is not a success claim.
  - trace rows `240`; no non-finite rows.
  - tracking reward mean/final `0.07618` / `0.11128`.
  - position error mean/final `0.24787 m` / `0.19742 m`.
  - target unsafe rate mean/final/max `0.0`.
  - action-alignment reward and ceiling mean/final/max `0.0`.
  - teacher-force alpha and active-rate mean/final/max `0.0`.
  - curriculum scale mean/final/min/max `1.0`.
  - phase reached `0.5` over the 240-step half-reference eval, as expected for an 8 s reference at 60 Hz.
  - target table clearance min over trace `0.065114 m`.
- reference metadata in eval still reports `graspgenx_source=true`, runtime duration `8.0 s`, min runtime gripper width `0.024 m`, validation records passed, and `curobo_validated=false`.

Analysis:
- Confirmed the earlier branch bug: default tracking training was contaminated by a reference-action imitation reward and wrapper-accessible teacher-force/action-alignment controls; tracking loss also faded out. Those are now disabled/guarded for the clean route.
- Clean environment validation, tiny PPO launch, checkpoint save, and policy-only eval all pass. This proves the preconditions and execution path are correct enough for a longer one-GPU PPO probe.
- It does not prove task learning yet. The 5-epoch smoke is too short and no env terminated, so the next useful training run should be a bounded longer clean PPO run with full reward-term curves.

Next:
- Run a one-GPU clean PPO probe long enough to produce non-empty scalar curves and early behavior signal before any 8-GPU scale-up. Suggested next run: `NUM_ENVS=256`, `HORIZON_LENGTH=64`, `MAX_ITERATIONS=25` or `50`, `SAVE_FREQUENCY=5`, no auto-resume, same reference path, then policy-only eval/video if reward curves are finite.
## 2026-06-12T01:16:01-07:00 - reward ablation override plumbing

Goal:
- Make reward tuning experiments explicit and reproducible before running more RL.

Hypothesis:
- The current tracking reward may be redundant with, or dominated by, the baseline dense Franka cube closeness/shaping terms. To test that cleanly, each run must record exact active reward weights and allow turning off tracking state closeness, tracking action shaping, and selected baseline dense rewards without code edits between runs.

Change:
- Added explicit reward-weight override plumbing for Franka cube baseline weights and trajectory-tracking weights in train/eval/validation wrappers.
- Added validator arguments and metrics for resolved reward weights.
- Relaxed validator geometry-reward checks so intentional zero-weight ablations do not fail solely because a disabled reward term is zero.
- Added reward-weight fields to eval `env_config` summaries.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- worklog: `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `0cd14f545e023edfb70f22e71cc9956703cd6f0d`
- implementation_commit: pending
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Command / Job:
- static_checks: `python3 -m py_compile dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py`
- wrapper_checks: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- diff_check: `git diff --check`

Result:
- status: local static validation passed.
- key evidence: py_compile, bash -n, and diff check exited cleanly.

Analysis:
- Existing cluster artifacts show plain no-tracking baselines and reset-prior variants separately. The 8-GPU run `franka_cube_lowz_resetprior_policy8gpu_cd1d66e_20260612_004111` completed 300 epochs with reward around `13500`, but came from a different worktree with reset-prior overrides, so it proves the train stack can succeed but should not be treated as no-prior A. The ablation comparison should start by replicating a plain `Dextrah-Franka-Cube-Grasp` A run from this branch, then compare matched tracking variants using resolved reward weights and per-term curves.

Next:
- Commit/push this plumbing, deploy exact commit to l401, run plain baseline A replication first, then run tracking reward preflights/probes with individual reward-term comparisons.

## 2026-06-12T08:30:07Z - baseline A replication and tracking preflight

Goal:
- Prove the current branch still runs upstream-style Franka cube PPO before attributing failures to trajectory tracking, and validate the clean 60 mm tracking reference path before any tracking RL scale-up.

Hypothesis:
- Because the base Franka cube env/reward files are unchanged relative to `main`, plain `Dextrah-Franka-Cube-Grasp` should learn if the wrapper/deployment/config are correct. Tracking should remain reward-only, with action-alignment and teacher forcing disabled by default.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- implementation_commit: `581890b1c4bb0209e70e657f962d1d19e3455015`
- remote_commit/status: l401 worktree detached at `581890b1c4bb0209e70e657f962d1d19e3455015`

Command / Job:
- baseline validation job: `1028286`, l401 `batch`, run `franka_cube_baseline_A_validate_581890b_20260612_011753`
- baseline validation metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_baseline_A_validate_581890b_20260612_011753/metrics.json`
- baseline A replication job: `29004014`, a1001 `interactive_singlenode`, run `franka_cube_baseline_A_repl8gpu_581890b_20260612_011911`
- baseline A run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_A_repl8gpu_581890b_20260612_011911`
- tracking preflight job: `1028295`, l401 `batch`, run `franka_cube_tracking_60mm_preflight_581890b_20260612_0129`
- tracking preflight metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_tracking_60mm_preflight_581890b_20260612_0129/metrics.json`

Result:
- baseline validation passed on l401 with default cube rewards and no tracking reference.
- tracking 60 mm preflight passed with explicit reference `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.
- tracking preflight metrics:
  - `passed=true`, `steps_completed=520`, `done_count=0`.
  - rollout reward mean/final `1.78505 / 1.00897`.
  - tracking reward mean/final `0.35126 / 0.06996`.
  - action-alignment reward mean and ceiling mean `0.0 / 0.0`.
  - teacher-force alpha/active mean `0.0 / 0.0`.
  - unsafe target rate max `0.0`; target clearance min `0.065114 m`.
  - phase progress max/final `1.0 / 1.0`; curriculum min/max `1.0 / 1.0`.
  - source duration `22.033333 s`, runtime duration `8.0 s`, retime policy `normalize_to_configured_runtime_duration`.
- active baseline A replication status at this note:
  - job `29004014` still running.
  - reached about epoch `169/300`.
  - checkpoints observed: epoch 25 reward `915.3153`, 50 `1488.1699`, 75 `1509.2474`, 100 `1583.0918`, 125 `1587.0731`, 150 `1506.844`.
  - best checkpoint suffix reached at least `1658.4258` by epoch 159.

Analysis:
- The current branch adds a separate tracking task registration and does not diff the base Franka cube env/reward/config files relative to `main`; a plain-baseline regression would likely be wrapper/config/run-setting related.
- The 60 mm reference matches the cube size/table height and passes compact-reference validation. It remains marked `curobo_validated=false`, so experiment notes should preserve that caveat unless the compact reference is regenerated/marked from validated provenance.
- Tracking preflight confirms clean RL preconditions: no teacher forcing, no action-alignment reward, no unsafe targets, no phase-observation change, constant tracking curriculum.
- The tracking term is modest under the scripted rollout compared with total reward, supporting the user's suspicion that default dense cube rewards may dominate. Matched reward ablations should compare default dense reward, tracking-only/mostly tracking, and reduced baseline closeness.

Next:
- Monitor job `29004014` to completion, inspect final logs/checkpoints/configs, then run policy eval/term extraction on the baseline checkpoint.
- After A is understood, launch matched tracking/reward ablation probes with explicit resolved weights and per-term metrics.

## 2026-06-12T08:38:33Z - baseline A replication completed but non-matching

Goal:
- Finish the first branch-local 8-GPU baseline A replication and decide whether the branch/env preconditions are trustworthy enough for tracking ablations.

Hypothesis:
- If the current branch and wrapper are equivalent to known-good upstream A, plain `Dextrah-Franka-Cube-Grasp` should show the same late reward transition near epochs 275-300.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- implementation_commit: `581890b1c4bb0209e70e657f962d1d19e3455015`
- remote_commit/status: a1001/l401 worktree detached at `581890b1c4bb0209e70e657f962d1d19e3455015`

Command / Job:
- job: `29004014`, a1001 `interactive_singlenode`, run `franka_cube_baseline_A_repl8gpu_581890b_20260612_011911`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29004014.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_A_repl8gpu_581890b_20260612_011911`
- command essentials: `TASK=Dextrah-Franka-Cube-Grasp`, `MAX_ITERATIONS=300`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`, `AUTO_RESUME=False`, `env.use_cuda_graph=True`

Result:
- status: completed cleanly, but non-matching relative to historical A.
- scheduler: `COMPLETED`, exit `0:0`, elapsed `00:16:48`.
- final checkpoint: `last_dextrah_franka_cube_grasp_ep_300_rew_1639.0187.pth`.
- best checkpoint: `dextrah_franka_cube_grasp.pth`, best reward `1775.1749`.
- key checkpoints: epoch 250 `1659.0822`, epoch 275 `1632.1989`, epoch 300 `1639.0187`.
- historical A comparison: job `28957528` used `MAX_ITERATIONS=600`, `env.use_cuda_graph=False`; historical rewards were epoch 250 `1738.1412`, epoch 275 `3275.8337`, epoch 300 `7956.269`, and best around `13224.685`.
- saved reward/env settings match historical A for the checked fields: `num_envs=2048`, `cube_spawn_xy_randomization=0.08`, and all cube reward weights.

Analysis:
- This does not prove a base-env bug in the tracking branch. The base task ran stably and only diverged from historical A after the known-good run's late transition window.
- The concrete config mismatch is now identified: the failed replication was not exact because it used `env.use_cuda_graph=True` and stopped at 300 epochs, while known-good historical A used `env.use_cuda_graph=False` and 600 epochs.
- Do not launch tracking ablations from this evidence yet. First run exact historical-A settings from the current commit so the baseline precondition is actually tested.

Next:
- Launch exact A replication on A100 with `USE_CUDA_GRAPH=False`, `MAX_ITERATIONS=600`, `AUTO_RESUME=False`, same reward/spawn settings, and monitor through at least the epoch-300 transition window and completion.

## 2026-06-12T08:40:00Z - exact historical A rerun launched

Goal:
- Test the current commit with the exact known-good baseline settings before any tracking or reward-ablation RL launch.

Hypothesis:
- The previous non-matching run may be explained by runtime/config drift (`env.use_cuda_graph=True`, 300 epochs). Matching historical A should reproduce the late reward transition if the branch and base task are correct.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- implementation_commit: `581890b1c4bb0209e70e657f962d1d19e3455015`
- remote_commit/status: a1001 worktree detached at `581890b1c4bb0209e70e657f962d1d19e3455015`

Command / Job:
- job: `29004556`, a1001, run `franka_cube_baseline_A_exact600_581890b_20260612_0840`
- command:
  `cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking && sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_baseline_A_exact600_581890b_20260612_0840,MAX_ITERATIONS=600,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,CUBE_SPAWN_XY_RANDOMIZATION=0.08 cluster/sbatch_train_teacher_8gpu.sh`
- expected log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29004556.out`
- expected run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_A_exact600_581890b_20260612_0840`

Result:
- status: launched; monitor pending.

Next:
- Verify the wrapper command echoes `--max_iterations 600` and `env.use_cuda_graph=False`, then monitor reward checkpoints against historical A at epochs 250, 275, 300, and completion.

## 2026-06-12T09:18:00Z - add explicit train seed override

Goal:
- Remove the last known hidden mismatch between historical A and branch-local baseline reruns.

Hypothesis:
- Historical A's success may be seed-sensitive. The wrapper hardcoded `--seed -1`, so even with matching visible hyperparameters it could not reproduce the historical seed sequence.

Change:
- Added `SEED="${SEED:--1}"` to `cluster/sbatch_train_teacher_8gpu.sh`.
- Echo `SEED` in wrapper logs.
- Pass `--seed '$SEED'` to `train.py`.
- Default remains `-1`, preserving current behavior unless `SEED` is explicitly set.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- base_commit: `581890b1c4bb0209e70e657f962d1d19e3455015`
- implementation_commit: pending
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`

Command / Job:
- check: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- check: `git diff --check`

Result:
- status: local wrapper checks passed.

Analysis:
- Saved `params/env.yaml` and `params/agent.yaml` comparison between historical A and exact600 `581890b` run shows only seed, rank device, and experiment name differences for persisted config.
- Historical A used seed sequence starting at `1781139395`; exact600 `581890b` used seed sequence around `1781253651` because `--seed -1` is time-derived.

Next:
- Commit/push/deploy this seed override, then launch a historical-seed baseline rerun with `SEED=1781139395`, `USE_CUDA_GRAPH=False`, `MAX_ITERATIONS=600`.

## 2026-06-12T09:22:00Z - historical-seed baseline launched

Goal:
- Test whether the known-good historical A learning transition depends on the original time-derived seed.

Hypothesis:
- If the branch-local exact600 run is flat because of seed sensitivity rather than code/config drift, rerunning with historical seed `1781139395` should recover the known-good transition window.

Version Control:
- agent_id: franka-cube-traj-tracking
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- branch: `codex/franka-cube-trajectory-tracking`
- implementation_commit: `2557f3e397320dc1070ec1c2ece6713d502cafce`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking-seed`
- remote_commit/status: detached at `2557f3e397320dc1070ec1c2ece6713d502cafce`

Command / Job:
- job: `29005171`, a1001, run `franka_cube_baseline_A_histseed_2557f3e_20260612_0922`
- command:
  `cd /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking-seed && sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking-seed,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_baseline_A_histseed_2557f3e_20260612_0922,MAX_ITERATIONS=600,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,SEED=1781139395,CUBE_SPAWN_XY_RANDOMIZATION=0.08 cluster/sbatch_train_teacher_8gpu.sh`
- expected log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29005171.out`
- expected run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_A_histseed_2557f3e_20260612_0922`

Result:
- status: launched and wrapper command verified.
- key evidence: log echoed `SEED=1781139395` and train command includes `--seed 1781139395`, `--max_iterations 600`, `env.use_cuda_graph=False`, `env.cube_spawn_xy_randomization=0.08`.

Next:
- Compare checkpoints to historical A. Decisive windows: epoch 25/50 for early sanity and 250/275/300 for the historical transition.

## 2026-06-12T09:56:00Z - unseeded exact600 control completed

Goal:
- Determine whether matching visible PPO/env hyperparameters is sufficient to reproduce historical A.

Result:
- job `29004556`, run `franka_cube_baseline_A_exact600_581890b_20260612_0840`, completed cleanly: `COMPLETED`, exit `0:0`, elapsed `00:32:47`.
- Final checkpoint: `last_dextrah_franka_cube_grasp_ep_600_rew_2298.376.pth`.
- Best observed reward: `2364.3098`.
- It did not reproduce the handoff curve: no breakout by epoch 600.

Analysis:
- Saved `params/env.yaml` and `params/agent.yaml` match historical A after normalizing run name, node/time, rank device, and seed, so this run is a negative control for seed sensitivity.
- The historical-seed rerun `29005171` uses the same resolved config plus explicit `SEED=1781139395`; it has matched historical checkpoint rewards exactly through epoch 225 so far.
- Conclusion so far: the concrete bug was the training wrapper's inability to pin the seed because it hardcoded `--seed -1`. `--seed -1` resolves to a fresh time/random-derived seed, so a nominal replication was not replaying the same stochastic experiment.

Next:
- Keep monitoring `29005171` through the historical breakout window at epochs 250, 275, and 300.
- For final tracking/ablation experiments, never use `--seed -1`; launch explicit parallel seeds `1,2,3,4,5` with identical resolved config per method.

## 2026-06-12T10:08:00Z - keep action-reference diagnostics disabled by default

Goal:
- Make the default trajectory-tracking RL path clearly state/task-space reward-only, without action-imitation diagnostics doing extra work or producing misleading logs.

Change:
- In `DextrahFrankaCubeTrajTrackingEnv._compute_trajectory_tracking_reward`, skip `compute_reference_delta_actions()` unless `trajectory_tracking_action_alignment_weight != 0` or teacher forcing is enabled.
- When reference-action diagnostics are disabled, log neutral zero policy/reference action errors instead of measuring distance to a zero action placeholder.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

Analysis:
- `trajectory_tracking_action_alignment_weight` was already `0.0` and teacher forcing was already disabled by default. This change makes the default implementation align with that intent and removes accidental action-imitation-style bookkeeping from clean tracking-loss RL runs.

## 2026-06-12T10:35:00Z - historical-seed baseline completed

Goal:
- Finish the exact historical-seed baseline replication and close the base-env precondition before tracking-loss RL.

Result:
- job `29005171`, run `franka_cube_baseline_A_histseed_2557f3e_20260612_0922`, completed cleanly: `COMPLETED`, exit `0:0`, elapsed `00:32:04`.
- Final checkpoint: `last_dextrah_franka_cube_grasp_ep_600_rew_13045.947.pth`.
- Best checkpoint reward: `13224.685`.
- Checkpoint rewards match the handoff config exactly, including the transition window:
  - epoch 250 `1738.1412`
  - epoch 275 `3275.8337`
  - epoch 300 `7956.269`
  - epoch 325 `10704.136`
  - epoch 600 `13045.947`

Analysis:
- The baseline reproduction bug is fixed: the wrapper now supports explicit `SEED`, and pinning the historical seed reproduces the known-good curve exactly.
- The previous exact600 no-seed control had the same visible config but a different generated seed and failed to break out by epoch 600, confirming seed sensitivity.
- This validates the base Franka cube env and PPO preconditions for subsequent tracking-loss and reward-weight ablations.

Next:
- Push the latest cleanup commit when GitHub SSH permits.
- Deploy the latest commit to an agent-owned A100 worktree.
- Run tracking-loss RL with explicit seeds `1,2,3,4,5` and matched config; do not use `--seed -1`.

## 2026-06-12T10:42:00Z - default tracking-loss PPO 5-seed sweep launched

Goal:
- Run the first scaled clean RL-with-tracking-loss experiment with explicit seeds after baseline seed-control debugging.

Preflight:
- Commit: `b7e04f066e895f3572e993f675a1017bbc15cd90` in remote worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-tracking-loss-seeds`.
- Validation job `29017195`, run `franka_cube_trackloss_b7e04f0_preflight_20260612_1038`, passed.
- Validation confirmed: explicit 60 mm reference path, reference validation passed, `trajectory_tracking_action_alignment_reward_mean=0`, teacher forcing inactive, unsafe target max `0`, and `curobo_validated=false` retained.

Command / Jobs:
- Common settings: `TASK=Dextrah-Franka-Cube-Grasp-Traj-Tracking`, `MAX_ITERATIONS=600`, `USE_CUDA_GRAPH=False`, `AUTO_RESUME=False`, `SELF_RELAUNCH=False`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`, reference `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`.
- seed `1`: job `29017224`, run `franka_cube_trackloss_default_b7e04f0_seed1_20260612_1042`.
- seed `2`: job `29017225`, run `franka_cube_trackloss_default_b7e04f0_seed2_20260612_1042`.
- seed `3`: job `29017227`, run `franka_cube_trackloss_default_b7e04f0_seed3_20260612_1042`.
- seed `4`: job `29017228`, run `franka_cube_trackloss_default_b7e04f0_seed4_20260612_1042`.
- seed `5`: job `29017229`, run `franka_cube_trackloss_default_b7e04f0_seed5_20260612_1042`.

Next:
- Monitor launches, checkpoint rewards, tracking reward terms, and final checkpoints. Do not compare against baseline without accounting for seed sensitivity and per-term reward composition.

## 2026-06-12T19:59:07Z - distributed seed/config provenance fix

Goal:
- Remove misleading saved-config seed values before launching evals and reward ablations.

Finding:
- Tracking jobs were launched with explicit base seeds `1,2,3,4,5`.
- `train.py` intentionally adds `global_rank` to the base seed under `--distributed`, so the seed-2 job uses rank seeds `2..9`.
- In distributed runs every rank was writing the same `params/env.yaml` and `params/agent.yaml`; the persisted YAML therefore reflected whichever rank wrote last, e.g. seed-2 could show `seed: 6`.
- This was a provenance/logging bug, not evidence that the launched base seed was wrong. The Slurm command line remains the authoritative seed record for already-running jobs.

Change:
- `dextrah_lab/rl_games/train.py`: write `params/env.yaml`, `params/agent.yaml`, and matching pickle files only from rank 0 in distributed training.
- `cluster/sbatch_train_teacher_8gpu.sh`: echo `/code` Git head and short status in the Slurm log before training.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/train.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`

Next:
- Commit/push/deploy this provenance fix before the next eval/ablation launch.
- Let seed 3 finish, then run pure-policy evals on the best checkpoints for seeds 1-5.

## 2026-06-12T20:05:05Z - default tracking-loss sweep completed and base-closeness ablation launched

Goal:
- Evaluate the first clean RL+tracking-loss method over explicit base seeds `1..5`, then test whether base EE/finger/cube closeness shaping is masking the tracking term.

Default Tracking-Loss Result:
- implementation commit used for training: `b7e04f066e895f3572e993f675a1017bbc15cd90`
- source worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-tracking-loss-seeds`
- common config: `Dextrah-Franka-Cube-Grasp-Traj-Tracking`, `MAX_ITERATIONS=600`, `USE_CUDA_GRAPH=False`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`, reference `/results/trajectory_references/franka_cube_traj_ref_export_60mm_retry_20260611_134500_unvalidated/compact_reference.json`
- training jobs all completed `COMPLETED 0:0`:
  - seed 1 job `29017224`: final reward `2845.6494`, best reward `3223.9722`
  - seed 2 job `29017225`: final reward `13037.167`, best reward `13478.595`
  - seed 3 job `29017227`: final reward `11790.546`, best reward `12168.292`
  - seed 4 job `29017228`: final reward `2431.5935`, best reward `2708.623`
  - seed 5 job `29017229`: final reward `12797.634`, best reward `12860.89`

Pure-Policy Eval:
- eval source commit: `2de8b038cc5ddafaff73e35cea58e1f96cac84f8`
- eval jobs all completed `COMPLETED 0:0`, `ACTION_SOURCE=policy`, deterministic, `NUM_ENVS=16`, `NUM_STEPS=720`, `VIDEO_LENGTH=240`.
- jobs/runs:
  - seed 1: job `29018848`, run `franka_cube_trackloss_default_eval_policy_seed1_2de8b03_20260612_1205`
  - seed 2: job `29018849`, run `franka_cube_trackloss_default_eval_policy_seed2_2de8b03_20260612_1205`
  - seed 3: job `29018850`, run `franka_cube_trackloss_default_eval_policy_seed3_2de8b03_20260612_1205`
  - seed 4: job `29018851`, run `franka_cube_trackloss_default_eval_policy_seed4_2de8b03_20260612_1205`
  - seed 5: job `29018853`, run `franka_cube_trackloss_default_eval_policy_seed5_2de8b03_20260612_1205`
- eval success-rate final / last-window mean:
  - seed 1: `0.0` / `0.0`
  - seed 2: `1.0` / `0.64`
  - seed 3: `0.875` / `0.585`
  - seed 4: `0.0` / `0.0`
  - seed 5: `0.875` / `0.430625`
- videos fetched and probed locally under `/tmp/franka_trackloss_eval_policy_2de8b03`; all five are valid `1280x720`, `240` frames, `4.0` s. Contact sheet: `/tmp/franka_trackloss_eval_policy_2de8b03/contact_sheet.png`.

Per-Term Analysis:
- Event scalar summary fetched under `/tmp/franka_trackloss_events_by_seed`.
- Last-20 training-window aggregate reward tracks success, but tracking reward alone does not:
  - failed seed 1: aggregate reward `~2983`, success `~0.003`, tracking reward `~2.119`
  - failed seed 4: aggregate reward `~2493`, success `~0.003`, tracking reward `~1.677`
  - solved seed 2: aggregate reward `~13250`, success `~0.822`, tracking reward `~0.768`
  - solved seed 3: aggregate reward `~10770`, success `~0.645`, tracking reward `~0.484`
  - solved seed 5: aggregate reward `~12640`, success `~0.783`, tracking reward `~1.017`
- Interpretation: the current tracking term can be earned by following task-space targets without completing a robust grasp/lift. Base lift/success terms dominate final aggregate reward once the task is solved.

New Ablation:
- Hypothesis: base approach/enclosure distance shaping may be too strong or may obscure the tracking-loss contribution.
- Change from default tracking run: set `CUBE_APPROACH_WEIGHT=0.0` and `CUBE_ENCLOSURE_WEIGHT=0.0`; keep lift/success/action/tracking weights unchanged.
- source commit: `2de8b038cc5ddafaff73e35cea58e1f96cac84f8`
- jobs launched:
  - seed 1: job `29018883`, run `franka_cube_trackloss_baseclose0_2de8b03_seed1_20260612_1310`
  - seed 2: job `29018885`, run `franka_cube_trackloss_baseclose0_2de8b03_seed2_20260612_1310`
  - seed 3: job `29018893`, run `franka_cube_trackloss_baseclose0_2de8b03_seed3_20260612_1310`
  - seed 4: job `29018905`, run `franka_cube_trackloss_baseclose0_2de8b03_seed4_20260612_1310`
  - seed 5: job `29018916`, run `franka_cube_trackloss_baseclose0_2de8b03_seed5_20260612_1310`

Next:
- Monitor `29018883,29018885,29018893,29018905,29018916`; verify full train commands include `env.cube_approach_weight=0.0` and `env.cube_enclosure_weight=0.0`.
- Evaluate best checkpoints with pure-policy eval after training completes.

## 2026-06-12T20:48:48Z - base-closeness-off ablation completed

Goal:
- Test whether disabling base EE/finger/cube closeness rewards lets the trajectory-tracking term matter more for RL.

Result:
- All five training jobs completed cleanly with `COMPLETED 0:0`.
- Full train commands verified: explicit base seeds `1..5`, `env.cube_approach_weight=0.0`, `env.cube_enclosure_weight=0.0`, same reference path, same PPO settings as default tracking.
- Final / best rewards:
  - seed 1 job `29018883`: final `1490.731`, best `1783.6609`
  - seed 2 job `29018885`: final `1792.3971`, best `2135.4285`
  - seed 3 job `29018893`: final `1903.5316`, best `2092.6956`
  - seed 4 job `29018905`: final `1456.6378`, best `1747.2065`
  - seed 5 job `29018916`: final `1795.5365`, best `1842.2112`
- Last-20 training event summaries:
  - aggregate reward range `~1491..1970`
  - success rate range `~0.00004..0.0031`
  - cube lift height range `~0.00047..0.00203 m`
  - approach/enclosure rewards are exactly `0`
  - tracking reward remains nonzero, `~1.50..1.97`
- Negative-control eval:
  - job `29019487`, run `franka_cube_trackloss_baseclose0_eval_policy_seed2_2de8b03_20260612_1350`
  - `ACTION_SOURCE=policy`, deterministic, seed `2`, best no-closeness checkpoint.
  - completed `COMPLETED 0:0`; metrics: final success `0.0`, last-window success `0.0`, max success `0.0`.
  - video fetched to `/tmp/franka_trackloss_baseclose0_eval_seed2`; video is valid `1280x720`, `240` frames, `4.0` s. Contact sheet confirms approach/near-cube behavior without stable grasp/lift.

Analysis:
- The user's suspicion was worth testing, but full removal of base approach/enclosure shaping is too severe.
- The ablation did not improve tracking-loss learning; it made every seed worse than the default tracking-loss sweep, including worse than the default failed seeds.
- Tracking reward can still be collected while lift/success remains near zero, so the better next tuning direction is likely partial reduction of approach/enclosure or contact/lift-gated tracking terms, not fully disabling closeness.

Next:
- Recommended next reward tuning: run a partial-closeness ablation (`cube_approach_weight`/`cube_enclosure_weight` at `0.5x` or `0.25x`) or modify tracking reward so position/gripper tracking receives late-phase weight only after contact/lift gates.

## 2026-06-12T21:07:56Z - logged tracking-vs-baseline reward and success comparison

Goal:
- Create durable reward-curve and success-rate comparison artifacts for the known-good no-tracking baseline and the current RL+tracking-loss method.

Inputs:
- no-tracking baseline training: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_A_histseed_2557f3e_20260612_0922`
- no-tracking baseline eval metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_evalsuccess1024_4b5e140_20260612_122845_noprior_seed1781139395/metrics.json`
- tracking-loss training seeds 1-5: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_trackloss_default_b7e04f0_seed*_20260612_1042`
- tracking-loss pure-policy eval metrics: `/tmp/franka_trackloss_eval_policy_2de8b03/seed*/metrics.json`

Artifacts:
- comparison directory: `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612`
- plots: `reward_curve_comparison.svg`, `success_rate_curve_comparison.svg`, `eval_success_comparison.svg`
- tables: `training_curves.csv`, `training_summary.csv`, `reward_terms_summary.csv`, `eval_success_summary.csv`
- manifest/readme: `manifest.json`, `README.md`

Result:
- Training aggregate reward and success:

| Method | Final reward | Last-20 reward | Final train success | Last-20 train success |
| --- | ---: | ---: | ---: | ---: |
| no tracking baseline, seed `1781139395` | `13044.795` | `13067.345` | `0.819` | `0.828` |
| tracking-loss mean, seeds `1..5` | `8515.849 +/- 4789.768` | `8427.648 +/- 4719.371` | `0.474 +/- 0.385` | `0.451 +/- 0.370` |

- Existing eval success:

| Method | Eval success definition | Success |
| --- | --- | ---: |
| no tracking baseline | `eval_success_rate` over 1024-env first-attempt eval | `0.948242` |
| tracking-loss mean | mean per-seed `success_ever_rate` over five 16-env evals | `0.600000` |

Analysis:
- This is now logged as data, not just a narrative comparison.
- The no-tracking baseline still looks materially stronger than the current tracking-loss method in both training success and existing eval success.
- Reward is not a perfectly clean outcome comparison because tracking adds reward terms; success-rate curves and eval success are the better behavioral comparisons.
- Eval definitions are not identical because they reuse the existing artifacts: baseline has a 1024-env eval, tracking has five 16-env evals. `eval_success_summary.csv` records the exact definitions and occupancy metrics.

Next:
- Use these artifacts as the comparison baseline for the next reward-tuning sweep, especially partial base-closeness reductions or better contact/lift-gated tracking terms.

## 2026-06-12T22:55:51Z - added combined seed-sweep plots and visual inspection

Goal:
- Plot the tracking-loss seed sweep together with the existing no-prior baseline and grasp-pose-prior seed sweeps.
- Visually inspect the key plot artifacts instead of relying only on XML/CSV validation.

Inputs:
- seed-sweep reward means/scalars: `/home/lzha/code/DEXTRAH/cluster_results/a1001/franka_cube_seed_sweep600_c7e66a0_20260612_092951/reward_plot_means.csv`, `reward_plot_scalars.csv`
- seed-sweep success means/scalars: `/home/lzha/code/DEXTRAH/cluster_results/a1001/franka_cube_seed_sweep600_c7e66a0_20260612_092951/success_rate_plot_means.csv`, `success_rate_plot_scalars.csv`
- tracking-loss curves: `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/training_curves.csv`

Artifacts:
- `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/combined_reward_mean_std.svg`
- `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/combined_success_rate_mean_std.svg`
- `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/combined_reward_plot_means.csv`
- `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/combined_success_rate_plot_means.csv`
- `worklogs/franka-cube-grasp-prior/reward_success_comparison_20260612/combined_plot_manifest.json`

Method:
- Ignored any previous-baseline rows.
- Reward plot is recomputed from scalar rows and restricted to strict common seed-`1..5` epochs per method:
  - no-prior baseline: epochs `1..567`
  - grasp pose prior: epochs `1..589`
  - tracking loss: epochs `1..571`
- Success plot uses the supplied mean CSV for no-prior/grasp-prior epochs `1..600` and recomputes tracking loss over common seed-`1..5` epochs `1..571`.
- Shaded bands are mean `+/-` std.

Visual Inspection:
- Rendered and opened the existing `reward_curve_comparison.svg`, `success_rate_curve_comparison.svg`, and `eval_success_comparison.svg`; they render correctly but only compare tracking loss against a single historical no-tracking seed.
- Rendered and opened the new combined reward/success plots. The final combined plots are visually coherent and do not include misleading reward tail rows with `n < 5`.

Result:
- Last strict-five-seed reward mean/std:

| Method | Epoch | Reward mean +/- std |
| --- | ---: | ---: |
| no-prior baseline | `567` | `4293.220 +/- 4467.953` |
| grasp pose prior | `589` | `13825.325 +/- 310.439` |
| tracking loss | `571` | `8630.591 +/- 4811.139` |

- Last training success mean/std:

| Method | Epoch | Success mean +/- std |
| --- | ---: | ---: |
| no-prior baseline | `600` | `0.179 +/- 0.356` |
| grasp pose prior | `600` | `0.865 +/- 0.030` |
| tracking loss | `571` | `0.475 +/- 0.387` |

Analysis:
- Grasp pose prior is clearly strongest in both reward and success.
- Tracking loss is better than the no-prior mean by late training, but its variance is large and it remains well below grasp pose prior.
- The earlier tracking-only plot was useful for debugging, but the combined plot is the right high-level comparison.

Next:
- Use the combined success plot as the primary figure when deciding whether tracking-loss reward tuning is worth continuing versus prioritizing grasp-pose-prior integration.

## 2026-06-12T23:26:54Z - integrated trajectory-tracking branch into main

Goal:
- Merge `codex/franka-cube-trajectory-tracking` into `main` and remove the completed worktree.

Change:
- Resolved merge conflicts in the Franka cube training/eval/validation wrappers and rollout/validation scripts.
- Kept main's first-attempt episode outcome definition for `eval_success_rate` and `eval_success_hold_rate`.
- Removed the false `success_occupancy_final` summary field while retaining clearly labeled per-step occupancy diagnostics.
- Left diagnostic action-source paths guarded by wrapper defaults, not used by standard launch defaults.

Version Control:
- feature_branch: `codex/franka-cube-trajectory-tracking`
- feature_head: `059372b04320dc7774ba42d5916d3e5b7a53739e`
- merge_commit: `8ad94557aec8e31534aba47cc2906898234d7a8b`
- pushed_main: `origin/main`

Validation:
- `bash -n cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py dextrah_lab/rl_games/train.py dextrah_lab/rl_games/analyze_traj_tracking_action_semantics.py dextrah_lab/rl_games/bc_reference_action_imitation.py dextrah_lab/rl_games/build_traj_tracking_handoff_comparison.py dextrah_lab/rl_games/residual_action_adapter.py dextrah_lab/rl_games/summarize_franka_cube_validation_artifacts.py dextrah_lab/rl_games/summarize_traj_tracking_eval_artifacts.py dextrah_lab/scene_scripts/convert_graspgenx_cube_trajectory_reference.py dextrah_lab/scene_scripts/make_franka_cube_traj_tracking_reference.py dextrah_lab/scene_scripts/summarize_franka_cube_traj_tracking_artifacts.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_traj_tracking_reference.py`
- `git diff --check HEAD^ HEAD`

Cleanup:
- Removed local worktrees `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking` and `/home/lzha/code/.codex-worktrees/DEXTRAH/integrate-franka-cube-traj-tracking-20260612`.
- Deleted merged local branches `codex/franka-cube-trajectory-tracking` and `codex/integrate-franka-cube-traj-tracking-20260612`.
- Checked a1001 and l401 queues; no active Slurm jobs for this user.
