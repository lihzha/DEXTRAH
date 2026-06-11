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
