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
- implementation_commit: pending
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
- implementation_commit: pending
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
