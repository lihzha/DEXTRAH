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
- push/pull: not pushed; no cluster job launched
- active jobs: none launched by this agent
- cleanup: generated local reference JSON and Python bytecode caches were removed before commit

Result:
- status: coherent checkpoint committed
- evidence: syntax/reference validation passed; gym registration import remains locally blocked by missing `gymnasium` in this shell

Next:
- Orchestrator can inspect/cherry-pick commit `8ac8dc54cc3841ca623be242c448a54361ff44ec` and run Isaac Lab smoke validation in an environment with the DEXTRAH dependencies installed.
