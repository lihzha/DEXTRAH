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
