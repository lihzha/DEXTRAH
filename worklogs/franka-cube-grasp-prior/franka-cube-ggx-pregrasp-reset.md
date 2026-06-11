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

## 2026-06-11T18:50:38Z - commit and handoff

Goal:
- Record the committed implementation checkpoint and branch handoff status.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: ba066a2a771d1bf1017e61031ca70ceacaf29d8d
- push/pull: pushed `codex/franka-cube-ggx-pregrasp-reset` to `origin`
- changed_files: implementation source plus owned worklog committed in `ba066a2a771d1bf1017e61031ca70ceacaf29d8d`; this final handoff note is a worklog-only follow-up
- remote_commit/status: origin branch updated to implementation commit before this worklog-only follow-up

Result:
- status: handoff_ready after committing this note
- metrics/artifacts: no active local jobs or cluster jobs launched; untracked validation artifact remains at `local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz`

Next:
- Push this worklog-only follow-up commit and report final branch status to the orchestrator.

## 2026-06-11T19:03:51Z - resumed l401 reset-prior smoke plan

Goal:
- Validate and debug the actual `Dextrah-Franka-Cube-Grasp` GraspGenX pregrasp reset path in an Isaac Lab runtime, not just local import/export checks.

Hypothesis:
- Local Isaac is blocked by missing runtime setup, so the fastest reproducible validation path is a small l401 Slurm/Pyxis job launched from an agent-owned remote worktree pinned to this branch commit, using the previously exported compact 0.06 m cube grasp library as an untracked artifact.

Change:
- Re-check local runtime paths and wrappers instead of assuming the earlier missing `_isaac_sim/python.sh` was the only blocker.
- Add only opt-in prior-reset environment variables and argument forwarding to `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, preserving its current defaults when disabled.
- Commit and push the wrapper/worklog change, deploy the exact commit to `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`, rsync only the untracked `.npz` library, then submit a small l401 validation with `GRASP_PRIOR_RESET_ENABLED=True`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 86ae7dfc5820e59ad310ef7c2ac1f64a49e0e399
- implementation_commit: pending
- push/pull: pending
- changed_files: planned `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, this owned worklog
- remote_commit/status: pending l401 agent-owned worktree

Command / Job:
- local runtime probes: `which python python3 conda micromamba mamba poetry uv`; `find /home/lzha/code/IsaacLab-v2.2.1 -maxdepth 3 \( -name python.sh -o -name _isaac_sim -o -name isaaclab.sh \) -print`; `python3 - <<'PY' ... importlib probes ... PY`; `TERM=xterm /home/lzha/code/IsaacLab-v2.2.1/isaaclab.sh -p -c "import isaaclab; print(isaaclab.__file__)"`
- local wrapper checks after edit: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`; `python3 -m compileall dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- planned l401 job: `sbatch --partition=batch --export=ALL,CODE_NFS=<agent worktree>,RUN_NAME=<unique>,NUM_ENVS=8,NUM_STEPS=4,CAPTURE_VIDEO=False,PRINT_INTERVAL=1,SEED=0,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz,GRASP_PRIOR_RESET_CYCLES=3 cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: pending
- run_dir: pending `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/<run_name>`
- logs: pending `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_<job_id>.out`
- artifacts: expected `metrics.json` plus fetched local copies under `cluster_results/l401/`

Result:
- status: in_progress
- metrics/artifacts: local probes confirm GPU present but local Isaac unavailable: `isaaclab`, `isaacsim`, `isaaclab_tasks`, `torch`, `trimesh`, and `graspgenx` are absent from system Python; `isaaclab.sh` fails because `python` is not on PATH and `/home/lzha/code/IsaacLab-v2.2.1/_isaac_sim/python.sh` is missing.
- key evidence: local GPU exists (`NVIDIA RTX 6000 Ada Generation` plus `NVIDIA T400`), so the blocker is software/runtime setup rather than hardware.

Analysis:
- The cluster route is appropriate because the DEXTRAH wrapper already mounts the known Isaac Lab image, IsaacLab source, FABRICS, venv target, and results/cache paths. The wrapper just needs disabled-by-default prior argument forwarding so the actual reset branch can be exercised by Slurm.

Next:
- Patch wrapper, run cheap checks, commit/push, deploy exact commit to l401, launch and actively monitor the bounded reset-prior smoke until metrics/logs are inspected or a hard external blocker is identified.

## 2026-06-11T19:07:37Z - l401 reset smoke launch record

Goal:
- Run the smallest practical Isaac Lab validation that actually exercises `grasp_prior_reset_enabled=True` for `Dextrah-Franka-Cube-Grasp`.

Hypothesis:
- The DEXTRAH Isaac Lab container on l401 can load the pinned agent worktree and compact GraspGenX library, then the validator will report whether reset-time IK, pregrasp sign, table clearance, finite observations, and immediate dones are sane.

Change:
- Added disabled-by-default prior-reset argument forwarding to `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh` in commit `9d5e98271c7aa6012900e161cd0a5f81b6273e12`.
- Because l401 cannot fetch GitHub over SSH (`Permission denied (publickey)`), deployed tracked source as Git objects via a small bundle into the remote canonical repository and created the agent-owned detached worktree from that commit. No tracked source was rsynced.
- Copied only the untracked compact grasp library artifact to the DEXTRAH results mount.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 86ae7dfc5820e59ad310ef7c2ac1f64a49e0e399
- implementation_commit: 9d5e98271c7aa6012900e161cd0a5f81b6273e12
- push/pull: pushed to `origin/codex/franka-cube-ggx-pregrasp-reset`; l401 GitHub fetch blocked, so used Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/franka-cube-ggx-pregrasp-reset-9d5e982.bundle`
- changed_files: `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, this owned worklog
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` detached at `9d5e98271c7aa6012900e161cd0a5f81b6273e12`, clean

Command / Job:
- command: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- command: `python3 -m compileall dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: `sbatch --partition=batch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,RUN_NAME=franka_cube_ggx_pregrasp_reset_smoke_20260611_190737,NUM_ENVS=8,NUM_STEPS=4,CAPTURE_VIDEO=False,PRINT_INTERVAL=1,SEED=0,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz,GRASP_PRIOR_RESET_CYCLES=3 cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: 1027681
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_ggx_pregrasp_reset_smoke_20260611_190737`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027681.out`
- artifacts: `metrics.json`; compact library `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz` with SHA256 `028fe588421014832e95e65ff0451500ff1c497fd4ac6f98455ee0366ff25660`

Result:
- status: submitted
- metrics/artifacts: pending
- key evidence: pending

Analysis:
- Success requires more than Slurm completion: inspect the metrics JSON for prior reset attempt/success rates, pose errors, pregrasp-farther sign, table clearance, immediate done count, finite observation/reward checks, and the printed `validate_command` proving the prior arguments were active.

Next:
- Submit the l401 job, monitor queue and logs to completion, fetch/inspect artifacts, then patch and relaunch if the metrics show reset pathology.

## 2026-06-11T19:09:43Z - l401 reset smoke result

Goal:
- Inspect the actual Isaac reset-prior smoke results for job `1027681` and decide whether the reset path is sane enough for a short RL smoke.

Hypothesis:
- If the prior reset path is wired correctly, every reset cycle should show attempted resets, high IK success, the pregrasp pose farther from the cube than the exact grasp pose, finite observations, safe finger/table clearance, and no immediate dones.

Change:
- No code changes after launch.
- Fetched Slurm log and metrics locally for inspection.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md
- branch: codex/franka-cube-ggx-pregrasp-reset
- implementation_commit: 9d5e98271c7aa6012900e161cd0a5f81b6273e12
- remote_commit/status: l401 worktree detached at `9d5e98271c7aa6012900e161cd0a5f81b6273e12`

Command / Job:
- command: `ssh l401 'sacct -j 1027681 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -P'`
- command: `rsync -av l401:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_ggx_pregrasp_reset_smoke_20260611_190737/ cluster_results/l401/franka_cube_ggx_pregrasp_reset_smoke_20260611_190737/`
- command: `rsync -av l401:/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027681.out cluster_logs/l401/dextrah/`
- job_id: 1027681
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_ggx_pregrasp_reset_smoke_20260611_190737`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_1027681.out`; local copy `cluster_logs/l401/dextrah/validate_franka_cube_1027681.out`
- artifacts: remote/local `metrics.json` under the run dir and `cluster_results/l401/franka_cube_ggx_pregrasp_reset_smoke_20260611_190737/metrics.json`

Result:
- status: passed
- scheduler: `COMPLETED`, exit code `0:0`, elapsed `00:00:43`, node `pool0-00016`
- metrics/artifacts: metrics `passed=True`, failed checks `[]`; log `validate_command` includes `--enable_grasp_prior_reset`, expected `--grasp_prior_library_path`, and `--grasp_prior_reset_cycles 3`
- key evidence:
  - prior cycles: 3 cycles x 8 envs
  - attempt rate: 1.0 for every cycle
  - IK/reset success rate: 1.0 for every cycle
  - pregrasp farther rate: 1.0 for every cycle
  - immediate done count: 0
  - min finger/table clearance: 0.120101 m, above penetration margin -0.002 m and above the normal 0.025 m clearance check in the rollout reset
  - max finger center distance: 0.107195 m
  - target position error: per-cycle max values 0.006292 m, 0.001199 m, 0.017894 m; mean values 0.001145 m, 0.000150 m, 0.002353 m
  - target rotation error: per-cycle max values 0.222254 rad, 0.000793 rad, 0.159875 rad; mean values 0.027893 rad, 0.000100 rad, 0.020036 rad
  - pregrasp sign evidence: exact tool distance means 0.130382/0.130946/0.127957 m versus pregrasp tool distance means 0.160262/0.160722/0.157818 m
  - rollout finite check passed for 4/4 steps with reward mean 2.135709 and done count 0

Analysis:
- The reset-prior branch is genuinely exercised and passes the requested smoke evidence: IK success/failure, target pose error, pregrasp-farther sign, finger/table clearance, immediate termination rate, finite observations/rewards, and prior-branch logging.
- Warnings observed in the log are non-blocking for this run: the known Warp CUDA UUID warning appeared, and `git rev-parse HEAD` printed a worktree metadata warning inside the container because the `.git` file points outside the mounted worktree. The latter is worth cleaning up in wrappers before longer jobs so logs can record the commit without noise.
- This smoke is metrics-only (`CAPTURE_VIDEO=False`), intentionally avoiding renderer/camera overhead for the first reset gate.

Next:
- Add minimal opt-in prior override support to the RL training wrapper and clean up commit logging for agent-owned worktrees.
- Run a short RL smoke with the same task and prior enabled, using reduced envs/steps but preserving the default prior-disabled path and final-training defaults.

## 2026-06-11T19:10:32Z - RL smoke wrapper patch plan

Goal:
- Prepare the existing DEXTRAH teacher-training wrapper for a short RL smoke and eventual apple-to-apple full training with the prior enabled.

Hypothesis:
- The training path can remain apple-to-apple if the wrapper only adds opt-in Hydra env overrides for `Dextrah-Franka-Cube-Grasp` and leaves all default task/PPO/env settings unchanged when `GRASP_PRIOR_RESET_ENABLED` is unset.

Change:
- Patch `cluster/sbatch_train_teacher_8gpu.sh` to add disabled-by-default `GRASP_PRIOR_RESET_ENABLED` and `GRASP_PRIOR_LIBRARY_PATH` env vars, echo them, validate that the prior is only used with `Dextrah-Franka-Cube-Grasp`, and append Hydra overrides `env.grasp_prior_reset_enabled=True` and `env.grasp_prior_library_path=<path>` only when requested.
- Add a `CODE_COMMIT` echo path to training and validation wrappers so agent-owned Git worktrees that are mounted without their external `.git/worktrees` metadata can still log the pinned commit cleanly.
- Do not change the default Franka cube PPO settings, default `NUM_ENVS=2048`, observation/action spaces, reward logic, termination logic, cube reset behavior, or the prior-disabled default path.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- branch: codex/franka-cube-ggx-pregrasp-reset
- base_commit: 9d5e98271c7aa6012900e161cd0a5f81b6273e12
- implementation_commit: pending
- changed_files: planned `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`, this owned worklog

Command / Job:
- local checks after edit: `bash -n cluster/sbatch_train_teacher_8gpu.sh`; `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`; `python3 -m compileall dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/rl_games/train.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- planned short RL smoke after commit/deploy: one L40S GPU, `TASK=Dextrah-Franka-Cube-Grasp`, reduced `NUM_ENVS` and `MAX_ITERATIONS`, `DISTRIBUTED=False`, prior enabled with the same compact library.

Result:
- status: planned

Next:
- Apply the wrapper patch, run cheap checks, commit/push, deploy exact commit to the l401 agent worktree, then launch/monitor a short RL smoke if checks pass.

## 2026-06-11T19:12:22Z - short RL smoke launch record

Goal:
- Run a bounded one-GPU RL smoke with `Dextrah-Franka-Cube-Grasp` and the GraspGenX pregrasp reset prior enabled, after the reset-only validation passed.

Hypothesis:
- A two-iteration, reduced-env PPO smoke should prove that the prior-enabled reset path can run inside the normal RL training wrapper, write rl_games logs/checkpoints/configs, and expose reset-prior reward extras without NaNs or immediate training failures.

Change:
- Committed wrapper support for prior-enabled training in `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc`.
- Deployed `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc` to the l401 agent-owned worktree using a Git bundle delta from `9d5e982`, because l401 GitHub SSH fetch remains blocked.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset
- branch: codex/franka-cube-ggx-pregrasp-reset
- implementation_commit: 4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc
- push/pull: pushed to `origin/codex/franka-cube-ggx-pregrasp-reset`; l401 updated through bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/franka-cube-ggx-pregrasp-reset-4cdc8c1.bundle`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` detached at `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc`, clean

Command / Job:
- command: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- command: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- command: `python3 -m compileall dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/rl_games/train.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: `sbatch --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=128G --time=00:45:00 --job-name=ggx_rl_smoke --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_rl_smoke_20260611_191222,NUM_ENVS=64,MAX_ITERATIONS=2,HORIZON_LENGTH=8,MINIBATCH_SIZE=512,CENTRAL_VALUE_MINIBATCH_SIZE=512,SAVE_FREQUENCY=1,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027683
- run_dir: expected `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_smoke_20260611_191222`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027683.out`
- artifacts: expected `params/env.yaml`, `params/agent.yaml`, `summaries/`, `nn/` checkpoints

Result:
- status: submitted
- metrics/artifacts: pending

Analysis:
- This is intentionally not the final apple-to-apple training scale. It reduces env count, horizon, and max iterations only to smoke the normal RL path with the prior enabled. Final training must return to the Franka cube wrapper defaults: 2048 envs, 8 GPUs, same PPO settings, and only prior/library overrides.

Next:
- Submit, monitor logs to completion, fetch and inspect rl_games configs, reward/reset metrics, summaries, and checkpoints. Patch/relaunch before any full-scale run if behavior is abnormal.

## 2026-06-11T19:14:36Z - longer RL smoke launch record

Goal:
- Run a bounded one-GPU RL smoke that is long enough to produce episode/reset scalar summaries, after the two-epoch smoke proved training startup/checkpointing but ended before any environment terminated.

Hypothesis:
- With `HORIZON_LENGTH=16` and `MAX_ITERATIONS=45`, each env gets 720 policy steps, enough to cross the 600-step timeout implied by `episode_length_s=10.0` and `decimation=2`. This should produce TensorBoard scalars for rewards/extras, including the prior reset metrics, while remaining a small smoke rather than a production run.

Change:
- No source changes since commit `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc`.
- First RL smoke `1027683` completed and wrote a checkpoint, but its TensorBoard event file was 0 bytes and rl_games warned that max epochs were reached before any environment terminated. It is useful execution evidence but not enough for reward/reset-metric inspection.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc
- remote_commit/status: l401 worktree detached at `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc`

Command / Job:
- command: `sbatch --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=128G --time=01:00:00 --job-name=ggx_rl_smoke2 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_rl_smoke2_20260611_191436,NUM_ENVS=64,MAX_ITERATIONS=45,HORIZON_LENGTH=16,MINIBATCH_SIZE=1024,CENTRAL_VALUE_MINIBATCH_SIZE=1024,SAVE_FREQUENCY=15,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027685
- run_dir: expected `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_smoke2_20260611_191436`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027685.out`
- artifacts: expected params, TensorBoard scalars, checkpoints, Slurm log

Result:
- status: submitted
- metrics/artifacts: pending

Analysis:
- This is the current gate before final training: it must show prior-enabled config, finite scalar values, sane reset success/farther rates, no termination pathology, and at least one checkpoint. If it fails or produces abnormal metrics, patch/relaunch rather than scaling.

Next:
- Submit and actively monitor job; fetch and parse scalars/checkpoints/logs before deciding on full-scale training.

## 2026-06-11T19:16:49Z - train scalar observability patch plan

Goal:
- Fix the RL smoke observability gap: the normal training stack completed and checkpointed, but TensorBoard events stayed empty, so reward terms and prior reset metrics could not be inspected from scalars.

Hypothesis:
- `dextrah_lab/rl_games/rl_games_utils.py` already contains `RLGPUAlgoObserver`, which logs `infos` scalars, episode cumulatives, and direct env extras through `writer.add_scalar`, but `train.py` currently does not install it. Adding this existing observer should produce the required scalar evidence without changing training behavior.

Change:
- Patch `dextrah_lab/rl_games/train.py` to import `RLGPUAlgoObserver` and include it in `observers = [IsaacAlgoObserver(), RLGPUAlgoObserver(), DextrahResumableAlgoObserver()]`.
- Do not change PPO hyperparameters, task config defaults, reward code, termination logic, action/observation spaces, cube reset, or the prior reset mechanics.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- base_commit: 4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc
- implementation_commit: pending
- changed_files: planned `dextrah_lab/rl_games/train.py`, this owned worklog

Command / Job:
- local checks after edit: `python3 -m compileall dextrah_lab/rl_games/train.py dextrah_lab/rl_games/rl_games_utils.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- planned relaunch: same bounded one-GPU prior-enabled RL smoke as `1027685`, new run namespace, then parse TensorBoard scalars and checkpoints.

Result:
- status: planned

Next:
- Patch, validate, commit/push/deploy exact commit, rerun the bounded RL smoke, and inspect scalar tags/values for finite rewards and prior reset metrics.

## 2026-06-11T19:17:53Z - scalar-observer RL smoke relaunch record

Goal:
- Rerun the bounded prior-enabled RL smoke after enabling `RLGPUAlgoObserver`, so reward terms and prior reset metrics can be inspected as TensorBoard scalars.

Hypothesis:
- The same 64-env, 45-epoch smoke should still complete and checkpoint, but now the event file should contain scalar tags for direct env extras such as `cube_grasp_prior_reset_success_rate` plus episode/reward metrics.

Change:
- Commit `53e7011fd3794cfafe16459696e434eb1fd9e3b9` imports and installs `RLGPUAlgoObserver` in `train.py`.
- Deployed exact commit to l401 agent worktree via Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/franka-cube-ggx-pregrasp-reset-53e7011.bundle`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 53e7011fd3794cfafe16459696e434eb1fd9e3b9
- remote_commit/status: l401 worktree detached at `53e7011fd3794cfafe16459696e434eb1fd9e3b9`

Command / Job:
- command: `python3 -m compileall dextrah_lab/rl_games/train.py dextrah_lab/rl_games/rl_games_utils.py`
- command: `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- command: `sbatch --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=128G --time=01:00:00 --job-name=ggx_rl_scalar --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=53e7011fd3794cfafe16459696e434eb1fd9e3b9,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_rl_scalar_20260611_191753,NUM_ENVS=64,MAX_ITERATIONS=45,HORIZON_LENGTH=16,MINIBATCH_SIZE=1024,CENTRAL_VALUE_MINIBATCH_SIZE=1024,SAVE_FREQUENCY=15,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027687
- run_dir: expected `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_scalar_20260611_191753`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027687.out`
- artifacts: expected params, non-empty TensorBoard event file with scalar tags, checkpoints, Slurm log

Result:
- status: submitted
- metrics/artifacts: pending

Analysis:
- If this run still lacks scalar data, the next fallback should be a lightweight JSONL metrics sidecar from the observer, not full training.

Next:
- Submit, monitor, fetch artifacts, parse scalar tags/values, and only then decide whether final 8-GPU training is ready.

## 2026-06-11T19:23:02Z - JSONL metric sidecar patch plan

Goal:
- Close the remaining RL-smoke evidence gap. The prior-enabled training path completes and checkpoints, but TensorBoard event files are still empty in the l401 Isaac runtime, so reward terms and reset-prior scalars cannot yet be inspected from the training artifact.

Hypothesis:
- A lightweight opt-in `AlgoObserver` can mirror direct env info/extras to rank-local JSONL files under the run directory. This is observability only: it does not alter actions, observations, rewards, terminations, PPO hyperparameters, reset mechanics, or default training behavior when the env var is not set.

Change:
- Add `DirectInfoJsonlObserver` to `dextrah_lab/rl_games/rl_games_utils.py`.
- Install it in `dextrah_lab/rl_games/train.py`.
- Add disabled-by-default `DEXTRAH_RLGAMES_JSONL_METRICS` forwarding to `cluster/sbatch_train_teacher_8gpu.sh`.
- Rerun the same bounded one-GPU prior-enabled RL smoke with `DEXTRAH_RLGAMES_JSONL_METRICS=True`, then inspect the JSONL scalars for prior reset rates, pose/table metrics, reward terms, finite values, and training pathology before scaling up.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- base_commit: 53e7011fd3794cfafe16459696e434eb1fd9e3b9
- implementation_commit: pending
- changed_files: planned `dextrah_lab/rl_games/rl_games_utils.py`, `dextrah_lab/rl_games/train.py`, `cluster/sbatch_train_teacher_8gpu.sh`, this owned worklog

Command / Job:
- completed prior job: `1027687`
- completed prior run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_scalar_20260611_191753`
- local checks after edit: `python3 -m compileall dextrah_lab/rl_games/train.py dextrah_lab/rl_games/rl_games_utils.py dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`; `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- planned relaunch: same 64-env, 45-epoch prior-enabled smoke as `1027687`, with `DEXTRAH_RLGAMES_JSONL_METRICS=True`.

Result:
- status: patch_in_progress
- metrics/artifacts from `1027687`: Slurm `COMPLETED` exit `0:0`; prior enabled in command and `params/env.yaml`; `cube_spawn_xy_randomization: 0.08`; checkpoints at epochs 15/30/45 with finite reward filenames `317.39478`, `569.0881`, and `581.206`; `summaries/events.out.tfevents...` remained `0 bytes`, so scalar inspection is still blocked.

Analysis:
- The scalar observer commit was not sufficient because the cluster TensorBoard writer still produced an empty file. JSONL sidecars are the minimal next step and are opt-in for smoke/final runs.

Next:
- Commit/push/deploy the JSONL observer patch, launch the short prior-enabled RL smoke with JSONL metrics enabled, inspect the resulting metric sidecar and checkpoints, then decide whether the full 8-GPU apple-to-apple training is ready.

## 2026-06-11T19:24:30Z - JSONL RL smoke launch record

Goal:
- Run the bounded 64-env/45-epoch prior-enabled RL smoke with the opt-in JSONL direct metrics sidecar enabled.

Hypothesis:
- The same normal RL path that already completed and checkpointed will now additionally write `metrics/direct_info_rank_0.jsonl`, allowing inspection of reset-prior success/farther rates, pose/table metrics, reward terms, finite values, and any termination pathology before full-scale training.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: c36d3f8bcd8237bcc127019aac35f0f7217f554f
- push/pull: pushed to `origin/codex/franka-cube-ggx-pregrasp-reset`; l401 updated through Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/.bundles/franka-cube-ggx-pregrasp-reset-c36d3f8.bundle`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` detached at `c36d3f8bcd8237bcc127019aac35f0f7217f554f`, clean before submission

Command / Job:
- command: `python3 -m compileall dextrah_lab/rl_games/train.py dextrah_lab/rl_games/rl_games_utils.py dextrah_lab/tasks/dextrah_franka_cube_grasp dextrah_lab/scene_scripts/export_franka_cube_graspgenx_library.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- command: `sbatch --partition=batch --gpus-per-node=1 --cpus-per-task=16 --mem=128G --time=01:00:00 --job-name=ggx_rl_jsonl --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=c36d3f8bcd8237bcc127019aac35f0f7217f554f,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_rl_jsonl_20260611_192430,NUM_ENVS=64,MAX_ITERATIONS=45,HORIZON_LENGTH=16,MINIBATCH_SIZE=1024,CENTRAL_VALUE_MINIBATCH_SIZE=1024,SAVE_FREQUENCY=15,DISTRIBUTED=False,MULTI_GPU=False,NPROC_PER_NODE=1,AUTO_RESUME=False,SELF_RELAUNCH=False,USE_CUDA_GRAPH=False,DEXTRAH_RLGAMES_JSONL_METRICS=True,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 1027690
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_jsonl_20260611_192430`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027690.out`
- artifacts: expected params, `metrics/direct_info_rank_0.jsonl`, checkpoints, Slurm log

Result:
- status: running
- metrics/artifacts: pending

Next:
- Monitor job 1027690 to completion, fetch logs/artifacts, parse `direct_info_rank_0.jsonl`, inspect configs/checkpoints, update this worklog with metrics, and only then decide on full 8-GPU launch.

## 2026-06-11T19:26:31Z - JSONL RL smoke result and full-run plan

Goal:
- Decide whether the prior-enabled branch is ready for the final apple-to-apple 8-GPU Franka cube run.

Result:
- status: passed
- job_id: 1027690
- scheduler: `COMPLETED`, exit `0:0`, elapsed `00:01:08`, node `pool0-00016`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_rl_jsonl_20260611_192430`
- local_artifacts: `cluster_results/l401/franka_cube_ggx_pregrasp_rl_jsonl_20260611_192430/`, `cluster_logs/l401/dextrah/teacher_8gpu_1027690.out`
- checkpoints: `last_dextrah_franka_cube_grasp_ep_45_rew_736.6942.pth`, `last_dextrah_franka_cube_grasp_ep_45_rew__736.6942_.pth`, plus `dextrah_runtime_rank_0.pth`
- JSONL sidecar: `metrics/direct_info_rank_0.jsonl`, 400920 bytes, 45 records, epochs 1-45, frames 0-45056, 162 scalar keys
- scalar health: `bad_scalar_count=0`; no NaN/Inf in JSONL; Slurm log has no traceback/runtime/child-failure patterns and ends with `Training Done`
- prior reset metrics: attempt/success/farther rates all `1.0` for all 45 records; reset position error mean/max `0.0002419/0.0004691 m`; reset rotation error mean/max `0.005852/0.008752 rad`; exact tool distance mean `0.129151 m`; pregrasp tool distance mean `0.158952 m`; prior finger-center distance mean `0.100986 m`; prior finger-table clearance min/mean `0.134568/0.134635 m`
- reward/behavior scalars: approach reward mean `0.1891`; enclosure reward mean `0.1262`; lift reward mean/max `0.00289/0.04286`; xy stability reward mean/min `0.9452/0.8520`; action penalty mean `-0.00238`; success/lifted rates remained `0.0` in this short untrained smoke; table-clearance violation mean/max `0.00129/0.03552`
- config evidence: `params/env.yaml` records `num_envs: 64`, `observation_space: 72`, `action_space: 7`, `cube_spawn_xy_randomization: 0.08`, `grasp_prior_reset_enabled: true`, `grasp_prior_pregrasp_offset: 0.03`; `params/agent.yaml` records the smoke-only overrides `max_epochs: 45`, `horizon_length: 16`, `minibatch_size: 1024`, `multi_gpu: false`

Analysis:
- The actual Isaac RL path uses the prior branch, produces sane reset metrics, finite reward/extras values, and checkpoints. The short smoke does not solve the task, but that is expected for a 45-epoch, 64-env random-start smoke. No reset pathology or immediate-failure signature appeared. The earlier reset validator remains the stronger immediate-done evidence: `passed=True`, immediate done count `0`, reset success/farther rates `1.0`, and positive table clearance.
- The full run is now clear to launch with the wrapper defaults for `Dextrah-Franka-Cube-Grasp`: 2048 envs, 8 GPUs, default horizon/minibatch/lr/gamma/tau/save cadence/max epochs, default PPO wrapper/settings, and only the prior/library Hydra overrides. `DEXTRAH_RLGAMES_JSONL_METRICS=True` will be used for inspection only; it does not change the policy data path.

Next:
- Commit/push this worklog result.
- Deploy the latest branch commit to the l401 agent worktree.
- Launch final 8-GPU training with `TASK=Dextrah-Franka-Cube-Grasp`, default wrapper PPO/env settings, `GRASP_PRIOR_RESET_ENABLED=True`, `GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz`, and JSONL direct metrics enabled for artifact inspection.
- Monitor through requeues if needed; inspect JSONL reset/reward metrics, checkpoints, logs, and any eval artifacts before considering the final run complete.

## 2026-06-11T19:30:05Z - final 8-GPU training launch record

Goal:
- Launch the apple-to-apple GraspGenX pregrasp-reset variant at the required final scale: `Dextrah-Franka-Cube-Grasp`, 2048 envs, 8 GPUs, same PPO wrapper/settings, only prior reset plus library overrides, with JSONL direct metrics enabled for inspection.

Change:
- Committed and pushed worklog result as `99ea26d5b449581988594f40168806642c486326`.
- Deployed the exact branch state to the NFS agent worktree; both l401 and a1001 see `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` at `99ea26d5b449581988594f40168806642c486326`.
- Attempted to submit from l401 first, but no job was created because l401 rejected the wrapper's default partition list: `invalid partition specified: batch_singlenode`. `sinfo` on l401 shows only `batch`/`batch_long` GPU partitions with `gpu:4`, so l401 cannot run the required single-node 8-GPU shape without changing the training geometry.
- Switched final training to a1001, where `sinfo` shows valid 8-GPU partitions (`batch_singlenode`, `grizzly`, `polar`, `polar3`, `polar4`, etc.) and the same DEXTRAH container/env/worktree/results paths are visible.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326
- push/pull: pushed to `origin/codex/franka-cube-ggx-pregrasp-reset`
- remote_commit/status: a1001 NFS worktree clean at `99ea26d5b449581988594f40168806642c486326`

Command / Job:
- failed l401 command: `sbatch --job-name=ggx_reset_8gpu --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=99ea26d5b449581988594f40168806642c486326,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_reset_8gpu_20260611_192735,AUTO_RESUME=True,SELF_RELAUNCH=True,DEXTRAH_RLGAMES_JSONL_METRICS=True,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- final a1001 command: `sbatch --job-name=ggx_reset_8gpu --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,CODE_COMMIT=99ea26d5b449581988594f40168806642c486326,TASK=Dextrah-Franka-Cube-Grasp,FULL_EXPERIMENT_NAME=franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005,AUTO_RESUME=True,SELF_RELAUNCH=True,DEXTRAH_RLGAMES_JSONL_METRICS=True,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`
- expected artifacts: rank-local JSONL direct metrics, checkpoints under `nn/`, runtime sidecars, params, Slurm log

Result:
- status: submitted
- metrics/artifacts: pending

Next:
- Monitor job `28987954` on a1001 through startup and any requeues. Confirm the log prints 8 GPUs, 2048 envs, distributed/multi-GPU defaults, prior enabled, and JSONL metrics enabled. Inspect rank-local metrics/checkpoints/logs, patch/relaunch if abnormal, and do not stop at scheduler completion.
