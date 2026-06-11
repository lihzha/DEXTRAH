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
- implementation_commit: current HEAD after this checkpoint; exact deployed commit recorded in the launch entry
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

## 2026-06-11T19:33:41Z - final 8-GPU training monitor checkpoint

Goal:
- Record the first full-scale training health checkpoint while continuing to monitor job `28987954`.

Result:
- status: running_healthy
- scheduler: `RUNNING`, elapsed about `00:04:52`, node `batch-block5-00308`
- startup evidence: log prints `torch ... cuda_available True device_count 8`; distributed command uses `--nproc_per_node=8`; ranks `0-7` initialize with `world_size = 8`; each rank creates `Number of environments: 2048`
- config evidence: wrapper logs `NUM_ENVS=2048`, `NPROC_PER_NODE=8`, `DISTRIBUTED=True`, `MULTI_GPU=True`, `HORIZON_LENGTH=64`, `MINIBATCH_SIZE=32768`, `SAVE_FREQUENCY=25`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`, `GRASP_PRIOR_RESET_ENABLED=True`, and JSONL metrics enabled
- artifacts: rank-local metric files created; rank 0 is writing scalar records; all rank runtime sidecars written at epoch 25; TensorBoard event file is nonzero; first model checkpoint written at `nn/last_dextrah_franka_cube_grasp_ep_25_rew_1176.0144.pth`
- current log progress: epoch `36/10000` visible in the live log; latest local snapshot has 33 rank-0 JSONL records through epoch 33
- scalar health from local snapshot: `bad_scalar_count=0`; prior attempt/success/farther rates all `1.0`; reset pos error min/max/mean `0.0000974/0.0017676/0.001138 m`; reset rot error min/max/mean `0.002747/0.017189/0.010816 rad`; prior finger table clearance min/mean `0.134935/0.135270 m`; pregrasp distance remains larger than exact grasp distance; table-clearance violation mean `0.00000333`
- behavior snapshot: approach reward increased to `0.907` by epoch 33; enclosure reward to `0.530`; lift reward remains small; success and lifted rates are still `0.0`, which is not yet abnormal this early in training
- errors: no traceback/runtime/NCCL/child-failure signature observed in fetched log snapshot

Analysis:
- The reset-prior path remains stable at final scale and within configured IK tolerances. The run is not complete; continue monitoring checkpoint cadence, scalar health, requeue behavior, and eventual success/lift metrics.

Next:
- Keep monitoring job `28987954`; fetch and inspect later checkpoints/metrics; update this worklog after the next meaningful checkpoint or requeue event; do not mark complete until final training and artifact inspection are done.

## 2026-06-11T19:37:01Z - final 8-GPU training monitor checkpoint

Goal:
- Record the next full-scale training health checkpoint while continuing to monitor job `28987954`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326 for the running job; latest branch/worklog commit before this entry is `81ca0f4d952d70459b2deecd23c2cdcd6726b737`
- remote_commit/status: a1001 NFS worktree remains clean at `99ea26d5b449581988594f40168806642c486326`; later local commits are worklog-only monitor records

Command / Job:
- monitor command: `squeue -j 28987954 -o "%.18i %.24j %.10T %.10M %.9l %.12N %.18R"; sacct -j 28987954 --format=JobID,JobName%24,State,ExitCode,Elapsed,NodeList -P`
- monitor command: parse `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/metrics/direct_info_rank_0.jsonl`
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`

Result:
- status: running_healthy
- scheduler: `RUNNING`, elapsed about `00:08:01`, node `batch-block5-00308`
- log progress: epochs visible through `72/10000`; no traceback/runtime/NCCL/child-failure signatures in the inspected tail
- checkpoints: `last_dextrah_franka_cube_grasp_ep_25_rew_1176.0144.pth` and `last_dextrah_franka_cube_grasp_ep_50_rew_1646.5193.pth`, both `140033037` bytes; rank runtime sidecars are present for ranks `0-7`
- metric artifacts: TensorBoard event file is nonzero; JSONL files exist for ranks `0-7`, with rank 0 writing `656114` bytes and nonzero scalar records
- JSONL scalar health: 72 records, last epoch `72`, `bad_scalar_count=0`
- prior reset metrics: success/farther rates are `1.0` for all records; reset position error min/max/mean `0.0000974/0.0019149/0.001502 m`; reset rotation error min/max/mean `0.002747/0.019035/0.014168 rad`; finger-table clearance min/mean `0.134935/0.135155 m`
- behavior/reward metrics: approach reward last/mean `0.97594/0.87968`; enclosure reward last/mean `0.56250/0.51335`; lift reward last/max/mean `0.00200/0.01889/0.00510`; success and lifted rates remain `0.0`; finger table-clearance violation max/mean `0.0000686/0.00000152`

Analysis:
- The final-scale reset-prior path remains active and numerically stable. Checkpoints and sidecars are advancing at the expected cadence. The task has not yet reached lift/success, but this is still early in a long run and not yet a failure signal given the increasing approach/enclosure rewards.

Next:
- Continue monitoring through the next checkpoint/requeue event. If success/lift metrics remain flat after substantially more training, inspect against the baseline learning curve before patching; preserve the apple-to-apple config unless there is a clear reset-prior defect.

## 2026-06-11T19:44:38Z - final 8-GPU training monitor checkpoint

Goal:
- Record the epoch 100/125 checkpoint window and early behavior evidence for job `28987954`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326 for the running job; latest branch/worklog commit before this entry is `19eaf870d686e77289dd1853e2d60e8fb74734f5`
- remote_commit/status: a1001 NFS worktree remains clean at `99ea26d5b449581988594f40168806642c486326`; later local commits are worklog-only monitor records

Command / Job:
- monitor command: six-sample local polling loop reading `squeue` and rank-0 JSONL from `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/metrics/direct_info_rank_0.jsonl`
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`

Result:
- status: running_healthy
- scheduler: `RUNNING`, elapsed about `00:14:47` at the last sample, node `batch-block5-00308`
- JSONL scalar health: records advanced from epoch `90` to `146`; `bad_scalar_count=0` at every sample
- checkpoints: epoch 100 checkpoint `last_dextrah_franka_cube_grasp_ep_100_rew_1739.3138.pth`; epoch 125 checkpoint `last_dextrah_franka_cube_grasp_ep_125_rew_1777.433.pth`; earlier epoch 25/50/75 checkpoints still present
- prior reset metrics: success/farther rates remain `1.0`; latest reset position error `0.001653 m`; latest reset rotation error `0.017002 rad`; latest finger-table clearance `0.135049 m`
- behavior/reward metrics: approach reward rose to `1.06079` by epoch 146; enclosure reward rose to `0.60161`; lift reward remains sparse but finite; `cube_has_lifted_rate` produced nonzero samples, including `0.0009765625` at epoch 124 and `0.00048828125` at epoch 146; `cube_success_rate` first showed a nonzero sample of `0.00048828125` at epoch 124, then returned to `0.0` in later samples

Analysis:
- The final run is still early but no longer completely flat on lift/success, and the primary reset-prior acceptance metrics continue to hold. The reward increase and occasional lift/success samples argue against an immediate reset-path regression. Continue monitoring instead of changing configuration.

Next:
- Continue monitoring toward the next checkpoints and wall-time/requeue boundary. Inspect whether lift/success become more frequent with training; if not, compare to baseline timing before any code/config intervention.

## 2026-06-11T19:55:41Z - final 8-GPU training monitor checkpoint

Goal:
- Record the epoch 150-250 checkpoint window for job `28987954` and confirm the reset-prior path remains stable while training progresses.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326 for the running job; latest branch/worklog commit before this entry is `6eea3ba0cffb86804a2259a9668e1d5cf54c7b67`
- remote_commit/status: a1001 NFS worktree remains clean at `99ea26d5b449581988594f40168806642c486326`; later local commits are worklog-only monitor records

Command / Job:
- monitor command: ten-sample local polling loop reading `squeue` and rank-0 JSONL from `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/metrics/direct_info_rank_0.jsonl`
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`

Result:
- status: running_healthy
- scheduler: `RUNNING`, elapsed about `00:25:55` at the last sample, node `batch-block5-00308`
- JSONL scalar health: records advanced from epoch `166` to `267`; `bad_scalar_count=0` at every sample
- checkpoints: epoch 150 `rew_1823.7875`, epoch 175 `rew_1837.514`, epoch 200 `rew_1861.1962`, epoch 225 `rew_1870.5924`, epoch 250 `rew_1925.6487`
- prior reset metrics: success/farther rates remain `1.0`; latest reset position error `0.001821 m`; latest reset rotation error `0.015713 rad`; latest finger-table clearance `0.135130 m`
- behavior/reward metrics: approach reward reached `1.08332` at epoch 256 and was `1.08062` at epoch 267; enclosure reward reached `0.61189` at epoch 256 and was `0.61050` at epoch 267; lift remains sparse but produced repeated nonzero samples (`0.00048828125` at epochs 166/177/211/233/245/256); success remained mostly zero in this window

Analysis:
- The final-scale run continues to checkpoint at the expected cadence with no numerical or reset-prior pathology. The policy is clearly improving on approach/enclosure and has intermittent lift, but sustained success has not emerged yet. This remains a monitor condition, not a patch condition.

Next:
- Continue monitoring toward later checkpoints and the first wall-time/requeue boundary. Watch for sustained lift/success growth and verify requeue resumes from the latest checkpoint without losing reset metrics.

## 2026-06-11T20:10:14Z - final 8-GPU training monitor checkpoint

Goal:
- Record the epoch 300-400 training window for job `28987954` using artifact-based liveness while Slurm CLI probes are slow.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326 for the running job; latest branch/worklog commit before this entry is `ad584acd751f897c3a4ed1fe775db72f266ea887`
- remote_commit/status: a1001 NFS worktree remains clean at `99ea26d5b449581988594f40168806642c486326`; later local commits are worklog-only monitor records

Command / Job:
- monitor command: six-sample artifact liveness loop reading rank-0 JSONL, checkpoint files, and Slurm log tail from `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- note: `squeue`/`sacct` probes on a1001 timed out during this window, but the JSONL/log/checkpoint artifacts continued advancing normally
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`

Result:
- status: running_healthy
- JSONL scalar health: records advanced from epoch `305` to `415`; `bad_scalar_count=0` at every sample
- checkpoints: epoch 300 `rew_1974.4305`, epoch 325 `rew_1987.0923`, epoch 350 `rew_2022.6237`, epoch 375 `rew_2001.7737`, epoch 400 `rew_2044.1816`
- prior reset metrics: success/farther rates remain `1.0`; latest reset position error `0.001838 m`; latest reset rotation error `0.017492 rad`; latest finger-table clearance `0.135041 m`
- behavior/reward metrics: approach reward rose to `1.12921` at epoch 415; enclosure reward rose to `0.63244`; lift reward reached `0.00904`; `cube_has_lifted_rate` reached `0.0014648438`; `cube_success_rate` remained `0.0` in the latest sample
- log evidence: log tail reached epoch `415/10000` and continued printing normal fps/frames lines; a specific error-signature grep for traceback/runtime/child/CUDA/NCCL failure patterns returned no matches

Analysis:
- Training is still healthy and no reset-prior pathology has appeared. The best and interval checkpoints are advancing, reward terms trend upward, and lift is becoming more frequent. Sparse success is acceptable at this stage, but it remains the main behavior metric to watch.

Next:
- Continue artifact-based monitoring until Slurm CLI responsiveness returns. Record the next checkpoint window and verify eventual wall-time requeue/resume semantics.

## 2026-06-11T20:23:17Z - final 8-GPU training monitor checkpoint

Goal:
- Record the epoch 425-550 monitor window for job `28987954`, including restored Slurm visibility, best-checkpoint updates, and rank-0 JSONL health.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: 99ea26d5b449581988594f40168806642c486326 for the running job; latest branch/worklog commit before this entry is `651b7d6e6e813fce3f502a26f6929a90c228ef18`
- remote_commit/status: a1001 NFS worktree remains clean at `99ea26d5b449581988594f40168806642c486326`; later local commits are worklog-only monitor records

Command / Job:
- monitor command: bounded `squeue`/`sacct` probes plus log-tail/error-signature probes for job `28987954`
- monitor command: six-sample artifact loop reading rank-0 JSONL and checkpoints under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- job_id: 28987954
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`

Result:
- status: running_healthy
- scheduler: `RUNNING` on `batch-block5-00308`; bounded `squeue` reported elapsed `00:45:17` and time remaining `3:04:43`; `sacct` reported job and batch step `RUNNING`, exit `0:0`
- JSONL scalar health: records advanced from epoch `448` to `558`; `bad_scalar_count=0` at every sample
- checkpoints: epoch 425 `rew_2057.8845`, epoch 450 `rew_2076.4912`, epoch 475 `rew_2083.0796`, epoch 500 `rew_2086.0613`, epoch 525 `rew_2070.765`, epoch 550 `rew_2110.0083`
- best-checkpoint evidence: log saved best policy at epoch 402 with `rew_2084.8135` and again at epoch 466 with `rew_2116.91`
- prior reset metrics: success/farther rates remain `1.0`; latest reset position error `0.001836 m`; latest reset rotation error `0.018304 rad`; latest finger-table clearance `0.134983 m`
- behavior/reward metrics: latest approach reward `1.13741`; latest enclosure reward `0.63599`; latest lift reward `0.00306`; latest `cube_has_lifted_rate=0.00048828125`; latest `cube_success_rate=0.00048828125`
- log/error evidence: log tail shows normal fps/frames, interval checkpoint, best checkpoint, and runtime-sidecar writes; targeted grep found no traceback/runtime/child/CUDA/NCCL failure signatures

Analysis:
- The final run remains healthy past the mid-500 epochs. Prior reset metrics continue to prove the branch is active and stable. Best reward is now above 2116, and both lift and success have appeared again in rank-0 metrics, so the behavior is not flatlined.

Next:
- Continue monitoring toward later checkpoints and wall-time/requeue. If the job requeues, verify it resumes in the same run dir from the latest checkpoint/runtime sidecars and that JSONL/checkpoint cadence continues without reset-metric regressions.

## 2026-06-11T20:29:11Z - interim inspection artifact bundle

Goal:
- Produce inspectable user artifacts from existing run outputs only, without interrupting or slowing active job `28987954`.

Command / Job:
- source artifacts: copied rank-0 JSONL, Slurm stdout, params, checkpoint filename listing, and scheduler snapshot from the active run
- local bundle: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705`
- generated files: `summary.json`, `training_curves.png`, `REPORT.md`, plus `raw/` copied text inputs
- viewer: `viz-open /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705/training_curves.png`
- viewer_url: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705/training_curves.png`

Result:
- status: produced
- summary snapshot: rank-0 JSONL reached epoch `622`, frame `651165696`, with `622` records and `bad_scalar_count=0`
- best reward: stdout best checkpoint reward `2128.5742` at epoch `595`
- last interval checkpoint in the snapshot: `last_dextrah_franka_cube_grasp_ep_600_rew_2112.7615.pth`
- prior reset metrics: success/farther rates stayed `1.0`; latest pos error `0.001877 m`; max pos error `0.002012 m`; latest rot error is recorded in `summary.json`; reset clearance remains positive
- behavior metrics: latest success rate `0.0` with max `0.00048828125`; latest lifted rate `0.00048828125`, max `0.00244140625`; lift height is sparse but present; approach reward latest `1.13808`; enclosure reward latest `0.636284`
- report: `REPORT.md` lists exact remote paths for the run dir, Slurm log, rank-0 JSONL, checkpoint dir, best checkpoint, and last checkpoint, plus healthy signals and watch items
- visual inspection: `training_curves.png` renders reset success/farther, reset pose/clearance, success/lift/lift-height, reward terms, and checkpoint reward curves; the PNG is readable via the viewer URL above

Analysis:
- The bundle gives an inspectable, self-contained interim view without copying checkpoint weights or modifying the active run. It supports the same conclusion as the live monitor: reset-prior behavior is stable, no rank-0 bad scalars are present, checkpoints/best reward are advancing, and the main watch item is still sparse success frequency.

Next:
- Continue the active monitor loop on job `28987954`; do not treat this artifact bundle as completion. Update/refresh artifacts later if the orchestrator asks or if the run reaches a requeue/final boundary.

## 2026-06-11T20:41:56Z - refreshed interim inspection artifact bundle

Goal:
- Refresh the inspectable artifact bundle after the next meaningful checkpoint window without interrupting active job `28987954`.

Command / Job:
- source artifacts: copied rank-0 JSONL, Slurm stdout, params, checkpoint filename listing, and scheduler snapshot from the active run
- local bundle: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_204031`
- generated files: `summary.json`, `training_curves.png`, `REPORT.md`, plus `raw/` copied text inputs
- viewer: `viz-open /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_204031/training_curves.png`
- viewer_url: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_204031/training_curves.png`

Result:
- status: produced
- scheduler snapshot: `RUNNING`, elapsed `01:11:56`, remaining `2:38:04`, node `batch-block5-00308`; `sacct` job and batch step are `RUNNING`, exit `0:0`
- summary snapshot: rank-0 JSONL reached epoch `770`, frame `806354944`, with `770` records, `bad_scalar_count=0`, and `targeted_error_signature_count=0`
- best reward: stdout best checkpoint reward `2186.5708` at epoch `748`
- last interval checkpoint in the snapshot: `last_dextrah_franka_cube_grasp_ep_750_rew_2153.0076.pth`
- prior reset metrics: success/farther rates stayed `1.0`; latest pos error `0.001906 m`, max pos error `0.002012 m`; latest rot error `0.017208 rad`, max rot error `0.020425 rad`; latest finger/table clearance `0.134984 m`
- behavior metrics: latest success rate `0.0` with max `0.00048828125`; latest lifted rate `0.00146484375`, max `0.00244140625`; latest lift height `0.0003055 m`; latest lift reward `0.009072`; latest approach/enclosure rewards `1.13898` / `0.636892`
- visual inspection: refreshed `training_curves.png` extends through epoch `770` and remains readable via the viewer URL above

Analysis:
- The refreshed bundle shows continued training progress after the previous artifact handoff. Reset-prior health remains stable, best reward improved from `2128.5742` to `2186.5708`, and lift frequency/height improved in the latest snapshot. Success is still sparse and remains the main behavior watch item, not an immediate reset-prior defect.

Next:
- Continue monitoring through wall-time/requeue. Refresh artifacts again after a requeue/resume event or another substantive checkpoint window if requested.

## 2026-06-11T20:50:11Z - eval video artifact plan

Goal:
- Produce a bounded rollout video artifact from the current reset-prior best checkpoint without interrupting or slowing active 8-GPU training job `28987954`.

Plan:
- Make a minimal eval-wrapper change only: expose disabled-by-default `GRASP_PRIOR_RESET_ENABLED` and `GRASP_PRIOR_LIBRARY_PATH` through `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, mirroring the training wrapper override style.
- Commit/push that wrapper/worklog change and deploy the exact commit to the agent-owned NFS worktree.
- Launch a 1-GPU l401 eval/render job from the agent worktree with `TASK=Dextrah-Franka-Cube-Grasp`, `NUM_ENVS=1`, short `NUM_STEPS`/`VIDEO_LENGTH`, reset prior enabled, and checkpoint `/results/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/nn/dextrah_franka_cube_grasp.pth`.
- Monitor eval scheduler/logs/metrics to completion; fetch metrics/video locally; run `viz-open`; record exact job id, checkpoint, metrics, video path, and viewer URL.
- Continue training monitor separately; do not cancel or modify job `28987954`.

Next:
- Patch the eval wrapper, run local `bash -n`, commit/push/deploy, and submit the small l401 eval.

## 2026-06-11T20:54:38Z - eval video artifact result

Goal:
- Produce and inspect a bounded rollout video artifact for the reset-prior run without interrupting active 8-GPU training job `28987954`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- implementation_commit: `51cac4a7ced0d23ef967e806cfef3cfe872bb810`
- changed_files: `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`, owned worklog
- push/pull: pushed to `origin/codex/franka-cube-ggx-pregrasp-reset`; deployed to l401 agent worktree via Git bundle
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` detached at `51cac4a7ced0d23ef967e806cfef3cfe872bb810`

Command / Job:
- launch command: `sbatch --parsable --partition=batch --time=00:25:00 --job-name=ggx_eval_video --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,TASK=Dextrah-Franka-Cube-Grasp,RUN_NAME=franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141,NUM_ENVS=1,NUM_STEPS=360,VIDEO_LENGTH=360,PRINT_INTERVAL=30,CAPTURE_VIDEO=True,DETERMINISTIC=True,USE_CUDA_GRAPH=False,SEED=20260611,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/nn/last_dextrah_franka_cube_grasp_ep_875_rew_2194.6606.pth,VIDEO_NAME_PREFIX=ggx-pregrasp-reset-ep875 cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `1027734`
- checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/nn/last_dextrah_franka_cube_grasp_ep_875_rew_2194.6606.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027734.out`
- local_artifacts: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141`

Result:
- status: completed
- scheduler: `COMPLETED`, exit `0:0`, elapsed `00:01:11`, node `pool0-00016`
- metrics: `num_envs=1`, `num_steps_completed=360`, `done_count=0`, `reward_mean=3.83645`, `reward_final=4.06477`, `success_rate_mean=0.0`, `success_rate_final=0.0`, `success_rate_last_window_mean=0.0`
- task metrics: `cube_lift_height` and `has_lifted_cube` stayed `0.0` in this single deterministic rollout; `finger_table_clearance` mean/min/final `0.08445/0.07862/0.08454 m`; `finger_table_clearance_violation=0.0`; `ee_to_cube_dist` mean/final `0.06855/0.07057 m`; `finger_center_to_cube_dist` mean/final `0.06270/0.06196 m`
- video: remote `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141/videos/ggx-pregrasp-reset-ep875-step-0.mp4`
- video: local raw `cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141/videos/ggx-pregrasp-reset-ep875-step-0.mp4`
- video: local trimmed preview `cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141/videos/ggx-pregrasp-reset-ep875-step-0-trimmed.mp4`
- video validation: raw video H.264 `1280x720`, `359` frames, `5.983 s`, `60 fps`; trimmed preview H.264 `1280x720`, `353` frames, `5.883 s`, `60 fps`
- visual inspection: first raw frame is black, likely a capture-start frame; middle/final sampled frames show the Franka hand at the cube with close but usable camera framing; trimmed preview skips the black opener
- viewer_url: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141/videos/ggx-pregrasp-reset-ep875-step-0-trimmed.mp4`
- errors: no traceback/runtime/child failure; log contains only the known non-fatal Warp CUDA driver-entry warning observed in successful Isaac runs
- active training status during eval: job `28987954` continued running on a1001 and reached epoch `906` with `bad_scalars=0` and checkpoint `last_dextrah_franka_cube_grasp_ep_900_rew_2213.7234.pth`

Analysis:
- The video artifact was produced without touching the active 8-GPU training job. This single deterministic rollout did not lift or succeed, which is consistent with sparse success in rank-0 training metrics so far and should be treated as behavior evidence to watch, not a reset-prior runtime failure. The rollout remained finite, did not terminate early, kept table clearance positive, and produced an inspectable video.

Next:
- Continue monitoring the active training job through wall-time/requeue and later checkpoints. Consider a later multi-seed eval video after success frequency improves, but do not change training config for this artifact.

## 2026-06-11T20:59:02Z - final 8-GPU training monitor checkpoint

Goal:
- Record the post-artifact training health window while continuing to monitor active job `28987954`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- running_job_commit: `99ea26d5b449581988594f40168806642c486326`
- latest_branch_commit_before_entry: `7878b1b`
- note: code changes after the running job commit are wrapper/worklog only and do not mutate the active training process

Command / Job:
- monitor command: eight-sample loop reading bounded `squeue`, rank-0 JSONL, checkpoint files, best checkpoint size, and targeted log error signatures
- job_id: `28987954`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`

Result:
- status: running_healthy
- scheduler latest: `RUNNING`, elapsed `01:28:09`, remaining `2:21:51`, node `batch-block5-00308`
- JSONL scalar health: records advanced through epoch `952`; `bad_scalar_count=0`; targeted error signatures `0`
- checkpoints observed in this window: epoch 775 `rew_2167.0908`, epoch 800 `rew_2172.8542`, epoch 825 `rew_2178.2688`, epoch 850 `rew_2183.0295`, epoch 875 `rew_2194.6606`, epoch 900 `rew_2213.7234`, epoch 925 `rew_2196.059`, epoch 950 `rew_2206.857`
- prior reset metrics at latest sample: success/farther rates `1.0`; pos error `0.001854 m`; rot error `0.018178 rad`; finger-table clearance `0.134985 m`
- behavior metrics at latest sample: approach reward `1.11909`; enclosure reward `0.627716`; lift reward `0.002958`; lift height `0.0001858 m`; lifted rate `0.00048828125`; success rate `0.0`
- active job remained healthy while the separate l401 eval job ran and completed

Analysis:
- The active final training is still numerically stable and checkpointing. Interval reward improved above `2200`, reset metrics remain ideal, and lift remains present but sparse. Success frequency remains the main watch item; no reset-prior or runtime defect is indicated.

Next:
- Continue monitoring toward wall-time/requeue. Verify resume behavior if Slurm requeues, and inspect metrics/checkpoints after resume before any final report.

## 2026-06-11T21:30:05Z - final 8-GPU training monitor checkpoint

Goal:
- Record the epoch 975-1250 checkpoint window while continuing active monitoring of final job `28987954`.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- running_job_commit: `99ea26d5b449581988594f40168806642c486326`
- latest_branch_commit_before_entry: `fbe9782`
- note: later branch commits are wrapper/worklog/artifact records only and do not mutate the active training process

Command / Job:
- monitor command: six-sample loop reading bounded `squeue`, rank-0 JSONL, tail-100 lift/success metrics, checkpoint files, and targeted log error signatures
- job_id: `28987954`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`

Result:
- status: running_healthy
- scheduler latest: `RUNNING`, elapsed `01:56:17`, remaining `1:53:43`, node `batch-block5-00308`
- JSONL scalar health: records advanced through epoch `1265`; `bad_scalar_count=0`; targeted error signatures `0`
- checkpoints observed in this window: epoch 975 `rew_2226.7686`, epoch 1000 `rew_2209.9124`, epoch 1025 `rew_2199.798`, epoch 1050 `rew_2206.5005`, epoch 1075 `rew_2220.847`, epoch 1100 `rew_2195.5464`, epoch 1125 `rew_2223.8977`, epoch 1150 `rew_2230.6763`, epoch 1175 `rew_2247.8704`, epoch 1200 `rew_2227.9263`, epoch 1225 `rew_2223.4565`, epoch 1250 `rew_2250.487`
- best-checkpoint note: orchestrator observed a stdout best reward `2276.3032` near epoch 1202; this is consistent with interval checkpointing continuing normally and will be included in the next artifact refresh from stdout
- prior reset metrics at latest sample: success/farther rates `1.0`; pos error `0.001929 m`; rot error `0.019827 rad`; finger-table clearance `0.135199 m`
- behavior metrics at latest sample: approach reward `1.11606`; enclosure reward `0.626357`; lift reward `0.0000656`; lift height `0.00000196 m`; lifted rate `0.0`; success rate `0.0`
- tail-100 metrics at latest sample: success mean/max `0.0000146/0.000488`; lifted mean/max `0.000449/0.0014648`; lift-height mean/max `0.0001136/0.0003417 m`; lift-reward mean/max `0.003045/0.007978`

Analysis:
- The final job remains stable with ideal reset-prior metrics, no bad scalars, no log error signatures, and normal checkpoint cadence. Interval reward improved to `2250.487`, with stdout best reportedly higher. Lift/success remain sparse and are the main behavior watch item, but there is no reset-prior runtime defect.

Next:
- Refresh inspectable artifacts from current stdout/JSONL/checkpoints, then launch a bounded eval video from the next usable recent checkpoint without interrupting the active training job. Continue monitoring training through wall-time/requeue.

## 2026-06-11T21:35:12Z - refreshed artifacts and second eval video

Goal:
- Produce the next inspectable artifact set and eval video from a newer usable checkpoint while keeping active training job `28987954` running.

Command / Job:
- artifact source: copied rank-0 JSONL, Slurm stdout, params, checkpoint filename listing, and scheduler snapshot from the active run
- local artifact bundle: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_213041`
- plot viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_213041/training_curves.png`
- eval launch command: `sbatch --parsable --partition=batch --time=00:25:00 --job-name=ggx_eval_video2 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset,TASK=Dextrah-Franka-Cube-Grasp,RUN_NAME=franka_cube_ggx_pregrasp_reset_eval_ep1325_20260611_213227,NUM_ENVS=1,NUM_STEPS=360,VIDEO_LENGTH=360,PRINT_INTERVAL=30,CAPTURE_VIDEO=True,DETERMINISTIC=True,USE_CUDA_GRAPH=False,SEED=20260612,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz,CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/nn/last_dextrah_franka_cube_grasp_ep_1325_rew_2241.5117.pth,VIDEO_NAME_PREFIX=ggx-pregrasp-reset-ep1325,CAMERA_EYE_X=-0.15,CAMERA_EYE_Y=-1.05,CAMERA_EYE_Z=1.55,CAMERA_TARGET_X=-0.41,CAMERA_TARGET_Y=-0.08,CAMERA_TARGET_Z=0.78 cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- eval job_id: `1027749`
- eval run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_ggx_pregrasp_reset_eval_ep1325_20260611_213227`
- eval log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027749.out`
- local eval artifacts: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep1325_20260611_213227`

Result:
- artifact status: produced
- artifact snapshot: active job `RUNNING`, elapsed `02:02:07`, remaining `1:47:53`; rank-0 JSONL epoch `1328`, frame `1391460352`, `bad_scalar_count=0`, targeted log error signatures `0`
- artifact best/checkpoint evidence: stdout best reward `2276.3032` at epoch `1202`; latest interval checkpoint in bundle `last_dextrah_franka_cube_grasp_ep_1325_rew_2241.5117.pth`; checkpoint list now verified numerically through epochs `975, 1000, 1025, 1050, 1075, 1100, 1125, 1150, 1175, 1200, 1225, 1250, 1275, 1300, 1325`
- artifact reset metrics: success/farther rates `1.0`; latest pos error `0.001873 m`; latest rot error `0.017186 rad`; latest finger-table clearance `0.135052 m`
- artifact behavior metrics: latest success rate `0.0`; latest lifted rate `0.00146484375`; latest lift height `0.000472 m`; latest lift reward `0.008748`; latest approach/enclosure `1.11228/0.624592`
- eval status: `COMPLETED`, exit `0:0`, elapsed `00:01:10`, node `pool0-00016`
- eval checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/nn/last_dextrah_franka_cube_grasp_ep_1325_rew_2241.5117.pth`
- eval metrics: `num_envs=1`, `num_steps_completed=360`, `done_count=0`, `reward_mean=3.88144`, `reward_final=4.17788`, `success_rate_mean/final=0.0`, `cube_lift_height max=0.0`, `has_lifted_cube max=0.0`
- eval clearance/contact metrics: finger-table clearance mean/min/final `0.08337/0.07290/0.08053 m`; `finger_table_clearance_violation=0.0`; `ee_to_cube_dist` mean/final `0.06826/0.06858 m`; `finger_center_to_cube_dist` mean/final `0.05806/0.05532 m`
- eval video: raw H.264 `1280x720`, `359` frames, `5.983 s`, `60 fps`; trimmed preview H.264 `1280x720`, `353` frames, `5.883 s`, `60 fps`
- eval video viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep1325_20260611_213227/videos/ggx-pregrasp-reset-ep1325-step-0-trimmed.mp4`
- visual inspection: wider camera view is better than the first eval; middle/final frames show the robot, gripper, and cube clearly; the rollout still does not lift in this single deterministic seed
- active training during eval: job `28987954` remained `RUNNING` and reached epoch `1352`, with no bad scalars and interval checkpoint `last_dextrah_franka_cube_grasp_ep_1350_rew_2255.2527.pth`

Analysis:
- The refreshed artifact bundle and second eval video are inspectable and were produced without affecting active training. The single deterministic eval remains non-successful, matching sparse success in training metrics. The active training itself continues to show stable reset-prior metrics, no numerical issues, and improving checkpoint/best rewards.

Next:
- Continue monitoring active job `28987954` through wall-time/requeue. If later checkpoints show sustained success/lift improvement, produce another eval video from a newer checkpoint; otherwise keep the current videos as evidence of approach behavior and sparse lift.

## 2026-06-11T21:42:12Z - reset-grasp geometry diagnostic plan

Goal:
- Resolve the user/orchestrator concern that the prior-enabled reset may be numerically tracking an end-effector target without placing the gripper in a physically graspable geometry around the cube.

Hypothesis:
- The existing `cube_grasp_prior_reset_success_rate` likely measures reset IK/target tracking only. A transform, tool-frame, approach-axis, gripper-open-width, or root-frame convention issue could still make the reset branch report success while fingertips are not positioned to enclose a 0.06 m cube.

Change:
- Planned before edits: add a reset-only diagnostic artifact path that records cube center, sampled exact grasp pose, 3 cm pregrasp target, offset direction, left/right fingertip centers, gripper center, gripper opening, fingertip/cube distances, table clearance, and a separate reset-grasp-quality verdict.
- Planned before edits: generate labeled reset-only frames/video before policy actions, plus a policy rollout trace from the latest checkpoint with reset geometry metrics, action/gripper signals, cube lift, success/lift, and target pose error.
- Planned before edits: audit training-vs-eval consistency for task config, prior library, reset path, cube randomization, robot/root conventions, action scaling, and checkpoint normalization.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- worklog: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md`
- branch: `codex/franka-cube-ggx-pregrasp-reset`
- base_commit: `efe5562769ae78ca5c31a5d92a638f6b3d717343`
- implementation_commit: pending
- push/pull: pending
- changed_files: pending; expected owned source/wrapper/worklog only
- remote_commit/status: pending after deploy

Command / Job:
- intended local checks: targeted `py_compile` plus `bash -n` on any changed wrapper
- intended cluster jobs: bounded l401 reset-only diagnostic and latest-checkpoint eval artifact job, both in the agent-owned remote worktree
- active training guardrail: do not interrupt job `28987954`; keep monitoring rank-0 JSONL, stdout, checkpoints, and reset/lift/success trends

Result:
- status: planned
- current active training state at plan time: job `28987954` `RUNNING`, elapsed `02:13:09`, remaining `01:36:51`, node `batch-block5-00308`; stdout just wrote epoch `1450` checkpoint `last_dextrah_franka_cube_grasp_ep_1450_rew_2270.1106.pth`

Analysis:
- The scalar reset success/farther metrics remain useful for IK/path health, but they do not by themselves prove grasp-quality geometry. The next artifact must directly answer where the cube, target, pregrasp, fingertips, gripper center, and 3 cm approach offset are in the same frame, and whether the opening is compatible with a 0.06 m cube.

Next:
- Inspect current env/eval code, add explicit reset-grasp-quality instrumentation and artifact generation, commit/push/deploy, then run and inspect the bounded l401 diagnostic without touching active training.

## 2026-06-11T21:48:20Z - reset-grasp diagnostic implementation checkpoint

Goal:
- Add instrumentation and artifact generation that directly answers the reset geometry questions before launching the l401 diagnostic.

Change:
- Added diagnostic-only reset buffers for cube world pose, exact tool pose, pregrasp tool pose, target EE pose, offset direction, fingertip positions, gripper width/margin, offset radial angle, projected exact finger-center distance, and reset-grasp-quality success.
- Extended eval rollout trace output with JSONL/CSV step traces, prior reset-quality metrics, and action/gripper command fields.
- Added a reset-only diagnostic script that renders labeled reset frames/video with colored markers and writes JSON/CSV geometry tables in world/env/root frames.
- Added a minimal l401 Slurm wrapper for the reset diagnostic.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- branch: `codex/franka-cube-ggx-pregrasp-reset`
- base_commit: `efe5562769ae78ca5c31a5d92a638f6b3d717343`
- implementation_commit: pending commit after this entry
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, `dextrah_lab/rl_games/diagnose_franka_cube_grasp_prior_reset.py`, `cluster/sbatch_diagnose_franka_cube_grasp_prior_1gpu.sh`, this worklog
- remote_commit/status: pending after deploy

Command / Job:
- local syntax: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/diagnose_franka_cube_grasp_prior_reset.py`
- wrapper syntax: `bash -n cluster/sbatch_diagnose_franka_cube_grasp_prior_1gpu.sh cluster/sbatch_eval_franka_cube_grasp_1gpu.sh cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- active training monitor: bounded A100 query of `squeue`, rank-0 JSONL, latest checkpoints, and log error signatures for job `28987954`

Result:
- status: local_checks_passed
- syntax checks: passed
- active training guardrail: job `28987954` still `RUNNING`, elapsed `02:19:39`, remaining `01:30:21`; rank-0 JSONL reached epoch `1522`, `bad_scalars=0`, targeted error signatures `0`
- latest active training metrics: reset success/farther `1.0/1.0`; pos/rot error `0.001938 m/0.017254 rad`; finger-table clearance `0.134919 m`; lift reward `0.003508`; lift height `0.000115 m`; lifted rate `0.000488`; success rate `0.0`
- latest checkpoints observed: epoch `1450` reward `2270.1106`, epoch `1475` reward `2271.4248`, epoch `1500` reward `2260.2036`

Analysis:
- The new diagnostics intentionally do not change observations, actions, rewards, terminations, PPO settings, cube reset randomization, or prior-disabled defaults. They add inspectable evidence for the frame/geometry concern that scalar IK success alone cannot resolve.

Next:
- Commit/push this diagnostic checkpoint, deploy the exact commit to the l401 agent worktree, run the bounded reset-only diagnostic and latest-checkpoint eval trace/video, fetch artifacts, open the most useful frames/video with `viz-open`, and inspect the geometry before making validity claims about the active training.

## 2026-06-11T21:55:07Z - invalid reset geometry confirmed and A100 run canceled

Goal:
- Close the loop on reset diagnostic job `1027755`, preserve inspectable evidence, and stop the active A100 training run that used invalid reset geometry.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- diagnostic_commit: `17d5c5e6b68055540a6f020e2a5450afcda52311`
- running_a100_job_commit: `99ea26d5b449581988594f40168806642c486326`
- branch: `codex/franka-cube-ggx-pregrasp-reset`
- changed_files: this worklog entry only

Command / Job:
- diagnostic job: `1027755`
- diagnostic run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/diagnostics/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944`
- diagnostic log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/diagnose_franka_cube_prior_1027755.out`
- local artifact copy: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944`
- opened frame URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/frames/reset_000_last_side.png`
- opened JSON URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/reset_geometry.json`
- canceled A100 job: `28987954`
- canceled A100 run_dir retained for traceability: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- canceled A100 log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28987954.out`

Result:
- status: failed_reset_geometry
- diagnostic job status: `COMPLETED`, exit `0:0`
- reset scalar/quality mismatch: `reset_success_rate=1.0`, `reset_quality_success_rate=0.0`, `farther_rate=1.0`, `immediate_done_rate=0.0`, `all_scalars_finite=true`
- reset 0 evidence: cube env pos `[-0.3749, -0.0861, 0.7810]`; exact tool relative to cube `[-0.0001, +0.0000, +0.1335]`; pregrasp relative to cube `[-0.0001, +0.0000, +0.1635]`; left/right finger body origins relative to cube `[-0.0371, -0.0068, +0.1031]` and `[+0.0417, +0.0070, +0.1027]`; gripper width `0.0800 m`; open-width margin over 0.06 m cube `0.0200 m`; projected exact finger-center distance `0.0729 m`
- reset 1-4 evidence: projected exact finger-center distance stayed `0.0659-0.0739 m`; quality stayed false despite IK success
- visual evidence: side-view labeled frame shows the gripper/finger body origins above the cube rather than an enclosing grasp-quality reset
- A100 cancellation: `sacct` reports `28987954|ggx_reset_8gpu|CANCELLED by 158351|0:0|02:24:51`; `.batch` exited `FAILED|15:0` from cancellation; `squeue` still showed transient `COMPLETING` while the node drained

Analysis:
- The active 8-GPU run `28987954` is invalid for the apple-to-apple GraspGenX pregrasp-reset comparison. It trained with a reset branch that satisfied IK/farther/table-clearance scalars but did not produce grasp-quality geometry under the current diagnostic definition and visual inspection.
- Do not report this as a successful RL result. The useful result is that reset-only diagnostics caught a geometry bug before accepting the training run.
- Likely causes remain frame/convention-related: the GraspGenX `run_graspgen` poses appear to be `panda_hand` tool-frame poses with a high top-down tool origin; DEXTRAH reward/diagnostics were using finger body origins as fingertip centers; and the current reset target offsets along the top-down tool axis, yielding a hover-pregrasp rather than an enclosing geometry by the diagnostic.

Next:
- Verify `28987954` leaves `squeue` and no replacement/requeue appears; cancel any requeued replacement as invalidated by reset geometry.
- Patch the reset geometry/debug path. Prioritize correct fingertip/contact-point measurement and the reset target frame/offset so reset-only diagnostics can distinguish valid top-down pregrasp from invalid hover geometry.
- Rerun reset-only l401 diagnostics until numeric `reset_grasp_quality_success_rate` and labeled frames show a plausible pregrasp/grasp geometry. No A100 RL relaunch before that passes.

## 2026-06-11T22:03:52Z - patch reset-prior quality geometry instrumentation

Goal:
- Fix the reset-only diagnostic blind spot before any RL relaunch by making grasp quality measure the frame the reset IK actually controls and by exposing numeric/visual evidence for tool, TCP, fingertip proxy, offset, and clearance geometry.

Hypothesis:
- The failed diagnostic used `panda_hand` and finger link body origins as grasp-quality contact proxies. DEXTRAH Franka controls `panda_hand + ee_offset_pos`; GraspGenX/Franka `panda_hand` top-down poses can therefore sit about 10 cm above the controlled TCP/fingertip plane. A diagnostic that reports both frames should tell whether the implementation is truly hovering or whether the prior geometry was mis-measured.

Change:
- Add reset-prior buffers and RL extras for exact/pregrasp DEXTRAH EE/TCP poses, projected exact/pregrasp TCP fingertip proxies, projected exact TCP/tip distances, and TCP-proxy table clearance.
- Tighten the opt-in `grasp_prior_reset_quality_success` metric to require reset success, open width margin, outward pregrasp offset, projected exact TCP/tip proximity to the cube, and TCP-proxy table clearance.
- Update `diagnose_franka_cube_grasp_prior_reset.py` to render and write both `panda_hand` tool poses and DEXTRAH TCP/tip-proxy poses in world/env/root frames, keeping old body-origin distances for reward-context comparison.
- Update `eval_rollout.py` to include the new reset quality metrics in rollout traces.

Version Control:
- agent_id: franka-cube-ggx-pregrasp-reset
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- worklog: `worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md`
- branch: `codex/franka-cube-ggx-pregrasp-reset`
- base_commit: `17d5c5e6b68055540a6f020e2a5450afcda52311`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/rl_games/diagnose_franka_cube_grasp_prior_reset.py`, `dextrah_lab/rl_games/eval_rollout.py`, this worklog

Command / Job:
- cheap checks: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/diagnose_franka_cube_grasp_prior_reset.py`
- cheap checks: `bash -n cluster/sbatch_diagnose_franka_cube_grasp_prior_1gpu.sh`
- cheap checks: `git diff --check`
- scheduler guard: `ssh a1001 'squeue ...; sacct -j 28987954 ...'`

Result:
- status: local_checks_passed
- A100 invalidated run state: no queued `28987954` requeue/replacement observed; `sacct` reports `28987954|ggx_reset_8gpu|CANCELLED by 158351|0:0|02:24:51`.
- old diagnostic artifacts re-opened with `viz-open`: side frame `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/frames/reset_000_last_side.png`; JSON `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/reset_geometry.json`
- local validation: `py_compile`, wrapper `bash -n`, and `git diff --check` passed.

Analysis:
- This is a bounded diagnostic/reset-quality patch, not an RL result. The old A100 run remains invalidated until a fresh l401 reset-only diagnostic shows plausible geometry under the new metrics and visual labels.
- The patch intentionally keeps the prior disabled by default and does not change cube spawn randomization, observation/action spaces, reward terms, PPO settings, or default wrappers.

Next:
- Commit/push this checkpoint, deploy the exact commit to the agent-owned l401 worktree, run a fresh reset-only diagnostic, fetch artifacts, inspect the new TCP/tip-proxy tables and labeled frames, and only then decide whether the actual reset target needs a further transform/offset correction.
