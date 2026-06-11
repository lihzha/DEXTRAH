# Worklog - franka-cube-grasp-prior / franka-cube-ggx-pregrasp-reset

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- created: 2026-06-11T18:39:11Z

## 2026-06-11T18:42:25Z - pre-edit plan

Goal:
- Implement variant 1 only: an optional, disabled-by-default GraspGenX object-local pregrasp reset for `Dextrah-Franka-Cube-Grasp`.

Hypothesis:
- The existing Franka cube task can remain apple-to-apple if the prior only changes robot joint reset state after the baseline cube pose is sampled and before normal RL step 0. A reset-only absolute differential IK loop can reuse the existing EE offset Jacobian path without putting cuRobo or planning into the PPO action path.

Change:
- Add optional prior config fields to `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, all disabled by default.
- Add grasp-library loading, object-local grasp sampling, `T_world_object @ T_object_grasp @ T_grasp_tool` composition, 3 cm farther-from-cube pregrasp sign selection, reset-only IK, open gripper reset, target-buffer synchronization, and reset metrics to `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`.
- Add a compact GraspGenX cube-library export script under `dextrah_lab/scene_scripts/`.
- Extend bounded validation in `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py` with optional prior-reset checks, keeping default validator behavior unchanged.
- Do not edit PPO configs, training wrappers, observations/actions/rewards/terminations, trajectory tracking, or diffusion-policy BC files.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a for local implementation checkpoint unless requested by orchestrator
- changed_files: planned as above, plus this owned worklog
- remote_commit/status: n/a/local env

Command / Job:
- command: `python3 -m compileall dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: bounded import/config checks with prior disabled and enabled using a synthetic compact library if Isaac Lab imports are available
- command: optional bounded Isaac reset smoke via `python3 dextrah_lab/rl_games/validate_franka_cube_grasp_env.py --num_envs 8 --num_steps 4 --enable_grasp_prior_reset ... --headless` if the local Isaac runtime is usable
- job_id: n/a
- run_dir: local worktree
- logs: command output in Codex transcript; no cluster logs expected
- artifacts: compact synthetic or exported grasp library only if needed for validation, not committed unless intentionally small and source-owned

Result:
- status: in_progress
- metrics/artifacts: pending
- key evidence: pending

Analysis:
- Key risk is frame interpretation: GraspGenX outputs a grasp frame, the Franka config maps it to `panda_hand`, while DEXTRAH controls an EE frame offset from `panda_hand` by `ee_offset_pos`. Reset IK must command the offset EE frame derived from the target `panda_hand`, and must validate that the 3 cm pregrasp moves farther from the cube center.

Next:
- Patch config/env/scripts, run bounded checks, update this worklog with results, then commit only owned source files and this worklog.

## 2026-06-11T18:49:23Z - implementation and bounded validation

Goal:
- Reach a coherent local checkpoint for the optional GraspGenX pregrasp reset without launching full training.

Hypothesis:
- The reset prior can be implemented as a disabled-by-default task option, and a local GraspGenX export smoke can validate the compact object-local library format even though local Isaac reset smoke depends on an unavailable Isaac Sim runtime.

Change:
- Added disabled-by-default prior fields to `franka_cube_grasp_env_cfg.py`.
- Added compact `.npz`/`.json` library loading, object-local grasp sampling, `T_world_object @ T_object_grasp @ T_grasp_tool` composition, 3 cm farther-from-cube pregrasp sign selection, reset-only DLS IK, open-gripper target synchronization, fallback-to-baseline on failed prior resets, and prior reset metrics to `franka_cube_grasp_env.py`.
- Extended `validate_franka_cube_grasp_env.py` with opt-in prior reset checks. Default validation behavior remains unchanged unless `--enable_grasp_prior_reset` is supplied.
- Added `dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py` for one-time centered 0.06 m cube GraspGenX library export. The first smoke found a cuRobo path-expansion dependency in GraspGenX `load_yaml`; the script now parses the Franka YAML directly so export does not require cuRobo.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a/local checkpoint
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this owned worklog
- remote_commit/status: n/a/local env

Command / Job:
- command: `python3 -m compileall dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: `cd /home/lzha/code/graspgenx && uv run python -c "import graspgenx; from graspgenx import get_checkpoints_version_dir, get_gripper_descriptions_assets; print(get_checkpoints_version_dir()); print(get_gripper_descriptions_assets())"`
- command: `cd /home/lzha/code/graspgenx && uv run python scripts/list_grippers.py`
- command: `cd /home/lzha/code/graspgenx && uv run python /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py --output /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz --graspgenx_root /home/lzha/code/graspgenx --cube_size 0.06 --seed 0 --num_sample_points 1000 --num_grasps 64 --topk 32 --planner topdown --moe_obb_density dense`
- command: `cd /home/lzha/code/graspgenx && uv run python - <<'PY' ... inspect smoke npz schema ... PY`
- command: `TERM=xterm /home/lzha/code/IsaacLab-v2.2.1/isaaclab.sh -p -c "import isaaclab; print(isaaclab.__file__)"`
- job_id: n/a
- run_dir: local worktree and `/home/lzha/code/graspgenx`
- logs: Codex transcript output
- artifacts: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz` (untracked validation artifact)

Result:
- status: partially passed; Isaac reset smoke blocked by local runtime
- metrics/artifacts: compile passed; GraspGenX import resolved checkpoints at `/home/lzha/code/graspgenx/ext/graspgenx_checkpoints/release`; `scripts/list_grippers.py` found 58 grippers including `franka_panda`; export wrote 32 grasps with confidence range 0.6894338726997375 to 0.7567837238311768; library metadata records `cube_size_m=0.06`, `tool_frame=panda_hand`, `gripper_name=franka_panda`, `pregrasp_farther_fraction=1.0`; schema inspection confirmed `grasps_object` shape `(32, 4, 4)`, `confidence` shape `(32,)`, and `grasp_to_tool_transform` shape `(4, 4)`.
- key evidence: IsaacLab local launcher failed with missing `/home/lzha/code/IsaacLab-v2.2.1/_isaac_sim/python.sh`; system Python also lacks `isaaclab`, `torch`, `trimesh`, and `graspgenx`, so a local Isaac reset smoke could not run here.

Analysis:
- The implementation preserves the baseline path by default: the new reset branch is gated by `grasp_prior_reset_enabled=False`, and no observation/action/reward term/termination/PPO/env-count/cube-spawn defaults were changed.
- Cube reset pose code remains the original XY randomization, clamp, spawn height, and identity orientation. The prior is applied only after that sampled cube pose is written.
- The reset prior composes the GraspGenX grasp frame through the stored Franka `T_grasp_tool`, treats the tool frame as `panda_hand`, then commands DEXTRAH's offset EE frame for IK. This explicitly handles the `panda_hand` versus `ee_offset_pos` frame difference.
- No online cuRobo or planning was added to the PPO action path or reset path.

Next:
- Commit this coherent checkpoint.
- The next validation step needs an Isaac Sim/Isaac Lab runtime: run `validate_franka_cube_grasp_env.py --headless --device cuda:0 --num_envs 8 --num_steps 4 --enable_grasp_prior_reset --grasp_prior_library_path <library.npz>` and inspect the prior reset metrics before any full training.
