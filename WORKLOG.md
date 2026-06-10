# DEXTRAH A1001 Teacher Training Worklog

Append-only project worklog for the DextrAH privileged FGP teacher training
thread. This follows the `robotics-cluster-development-core` worklog contract.

## Job Contract

- task: DextrAH Privileged FGP Teacher Training from the README.
- cluster: `a1001`.
- local repo: `/Users/lzha/code/DEXTRAH`.
- remote cwd: `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`.
- remote results: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah`.
- remote logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah`.
- run name: `teacher_short_20260609_100021`.
- main 8-GPU script: `cluster/sbatch_train_teacher_8gpu.sh`.
- canonical A100 Slurm reference: `/Users/lzha/code/submit_job_a100.sh`.
- A100 partitions: `batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode`.
- required wall time: below 4 hours; current script uses `0-03:50:00`.
- resume artifacts: RL-Games checkpoints plus per-rank `dextrah_runtime_rank_*.pth`
  sidecars under the run `nn` directory.
- success condition: training launches on 8 A100s, resumes from checkpoint
  without code/runtime errors, writes fresh checkpoints and runtime sidecars,
  and log inspection confirms reward/loss progress rather than relying only on
  Slurm exit state.

## 2026-06-09 13:00 PDT - Worklog Bootstrap

Goal:
- Create a stable project-local worklog and capture the current state for
  handoff/debug continuation.

Hypothesis:
- A clean Slurm state is not sufficient evidence of success; the latest log
  must be inspected before declaring the training run healthy.

Change:
- Read `/Users/lzha/.codex/skills/robotics-cluster-development-core/SKILL.md`.
- Created this append-only `WORKLOG.md`.

Command / Job:
- command: `sed -n '1,240p' /Users/lzha/.codex/skills/robotics-cluster-development-core/SKILL.md`
- command: `ssh a1001 'sacct -j 28889208 --format=JobID,JobName%28,State,Elapsed,ExitCode,NodeList%28,Start,End -P'`
- command: `ssh a1001 'tail -n 260 /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28889208.out'`
- job_id: `28889208`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28889208.out`
- artifacts: `nn/last_dextrah_lstm_ep_510_rew_176.34055.pth`,
  `nn/dextrah_runtime_rank_0.pth` through `nn/dextrah_runtime_rank_7.pth`

Result:
- status: failed
- metrics/artifacts: latest checkpoint before the failed resume remains
  `last_dextrah_lstm_ep_510_rew_176.34055.pth` from `2026-06-09 10:52`;
  all eight runtime sidecars exist and are about 531M each.
- key evidence: `sacct` reports `28889208|dextrah_teacher_8gpu|COMPLETED|00:13:20|0:0`,
  but the log has all ranks failing in checkpoint load with
  `RuntimeError: Could not execute <function load ...>, give up after 5 attempts...`.
- key evidence: the log shows all ranks reached environment setup and attempted
  to resume from
  `/code/dextrah_lab/rl_games/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_510_rew_176.34055.pth`.

Analysis:
- The latest job must not be treated as a successful training continuation even
  though Slurm says `COMPLETED` and the script printed `Training Done`.
- The immediate failure point is RL-Games checkpoint loading via
  `torch_ext.safe_filesystem_op(torch.load, ...)` on all ranks.
- The checkpoint file exists remotely and is about 606M, so the first suspects
  are NFS/symlink/read contention during simultaneous 8-rank load, an incomplete
  or incompatible checkpoint, or a launch/script issue that masks child process
  failures.
- The batch script already exits nonzero if `srun` itself returns nonzero, so
  the `COMPLETED` state suggests the distributed launcher or wrapper returned
  zero despite rank tracebacks. Log scanning is required for acceptance.

Next:
- Verify the checkpoint with an isolated remote `torch.load` or RL-Games
  checkpoint load before relaunching.
- Patch resume if needed so rank 0 validates/copies the checkpoint before all
  ranks load, or select the previous known-good checkpoint if epoch 510 is bad.
- Add an explicit post-run log/error guard to the batch script or wrapper so
  tracebacks cannot be followed by `Training Done` and a zero Slurm exit.
- Relaunch a bounded resume smoke first, then restart the 8-GPU training only
  after checkpoint load succeeds.

## 2026-06-09 13:00 PDT - Retrospective Attempts Before Worklog

Goal:
- Preserve the useful history from the earlier launch/debug loop that happened
  before this worklog file existed.

Hypothesis:
- Single-GPU resume should be debugged first, then 8-GPU launch and resume can
  be scaled once checkpoint/runtime state restoration is wired in.

Change:
- Added resumable training support in `dextrah_lab/rl_games/train.py` and
  `dextrah_lab/rl_games/rl_games_utils.py`.
- Added environment state capture/restore in
  `dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_kuka_allegro_env.py`.
- Set `save_frequency: 10` in
  `dextrah_lab/tasks/dextrah_kuka_allegro/agents/rl_games_ppo_lstm_cfg.yaml`.
- Added cluster scripts under `cluster/`, including
  `cluster/sbatch_train_teacher_8gpu.sh` and sync/submit helpers.
- Updated the cluster workflow note to point to `/Users/lzha/code/submit_job_a100.sh`
  as the canonical A100 multi-partition Slurm reference.
- Corrected the 8-GPU batch script to use all six A100 partitions,
  `0-03:50:00`, `--mem=0`, Pyxis/enroot container flags, and immediate
  `scontrol requeue` before forwarding `TERM`/`INT` to `srun`.

Command / Job:
- command: `./cluster/sync_to_a1001.sh`
- command: `FULL_EXPERIMENT_NAME=teacher_short_20260609_100021 AUTO_RESUME=True SELF_RELAUNCH=True sbatch --parsable --export=ALL cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `28873819` single-GPU smoke
- job_id: `28874519` single-GPU resume smoke
- job_id: `28874777` 8-GPU smoke
- job_id: `28887903` 8-GPU production/resume run
- job_id: `28889208` 8-GPU resume run after partition/time correction
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<jobid>.out`
- artifacts: RL-Games checkpoints and `dextrah_runtime_rank_*.pth` sidecars

Result:
- status: inconclusive
- metrics/artifacts: single-GPU smoke and resume passed; 8-GPU smoke reached
  training and wrote all eight runtime sidecars; job `28887903` trained through
  at least epoch 510 and wrote `last_dextrah_lstm_ep_510_rew_176.34055.pth`.
- key evidence: `28889208` reached environment setup on 8 ranks and attempted
  auto-resume, but failed during checkpoint load on every rank.

Analysis:
- The code reached the multi-GPU training surface, and checkpoint/sidecar saving
  exists, but resumability is not yet proven at the 8-GPU production scale.
- The current blocking issue is checkpoint load/resume robustness, not queue
  allocation or environment startup.
- Job `28889208` used an older spooled signal handler even after the source
  script was fixed; future submissions use the corrected source, but existing
  Slurm jobs do not reload source scripts from disk.

Next:
- Treat `28889208` as a failed resume attempt despite `COMPLETED`.
- Debug checkpoint readability/load behavior and add a guard against false
  successful Slurm exits.
- Relaunch from a verified checkpoint using the corrected remote source script.

| Attempt | Key setting | Result | Evidence | Decision |
| --- | --- | --- | --- | --- |
| `28873819` | single GPU smoke | passed | one epoch completed and wrote checkpoint/runtime state | proceed to resume smoke |
| `28874519` | single GPU resume | passed | restored checkpoint/runtime and ran to epoch 2 | proceed to 8-GPU smoke |
| `28874777` | 8 GPUs, `NUM_ENVS=4096`, short run | passed | all ranks started training and wrote sidecars/checkpoint | proceed to production-sized run |
| `28887903` | 8 GPUs, first short multi-partition run | partial | trained to epoch 510, then stopped for script correction | preserve checkpoint and relaunch with corrected script |
| `28889208` | 8 GPUs, corrected partitions/time, auto-resume | failed | all ranks failed `torch.load` of epoch 510 checkpoint while Slurm reported completed | debug checkpoint load and false-success guard |

## 2026-06-09 13:09 PDT - Current Scheduler Status Check

Goal:
- Answer whether any DEXTRAH training is still running normally and classify
  the previous attempts accurately.

Hypothesis:
- The latest Slurm `COMPLETED` states may hide rank-level failures, so log
  inspection is required.

Change:
- No code change.
- Checked `squeue`, `sacct`, latest checkpoint files, and logs for known job ids.

Command / Job:
- command: `ssh a1001 'squeue -u lzha -o "%.18i %.24P %.32j %.8T %.12M %.12l %.22S %.80R"'`
- command: `ssh a1001 'sacct -j 28873819,28874519,28874777,28887903,28889167,28889208 --format=JobID,JobName%34,Partition%28,State,Elapsed,ExitCode,NodeList%30,Start,End -P'`
- job_id: `28873819`, `28874519`, `28874777`, `28887903`, `28889167`, `28889208`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<jobid>.out`
- artifacts: latest durable production checkpoint appears to be
  `nn/last_dextrah_lstm_ep_510_rew_176.34055.pth`

Result:
- status: failed
- metrics/artifacts: no current `lzha` jobs are in `squeue` on `a1001`.
- key evidence: `28873819`, `28874519`, and `28874777` completed their bounded
  smoke/validation tasks and logged training/checkpoint sidecars.
- key evidence: `28887903` was manually canceled but trained normally before
  cancellation, reaching at least epoch 550 in the log; the latest durable
  checkpoint found in the run directory is epoch 510.
- key evidence: both `28889167` and `28889208` attempted to auto-resume from
  epoch 510 and all ranks failed in `torch.load` with
  `RuntimeError: Could not execute <function load ...>, give up after 5 attempts...`.

Analysis:
- Not all previous jobs failed. The smoke validations passed, and the first
  production 8-GPU run was healthy until manual cancellation.
- The current production continuation is not running and is not healthy. The
  latest two 8-GPU resume attempts failed at checkpoint loading while Slurm
  still reported `COMPLETED`.
- The two failed resume jobs overlapped in time and both loaded the same 606M
  checkpoint from NFS, which strengthens the suspicion of checkpoint read
  contention or load-path robustness rather than environment setup.

Next:
- Do not launch another full auto-resume until checkpoint readability is tested
  directly on a1001.
- Add a script/log guard so rank tracebacks force a nonzero job outcome.
- Relaunch a bounded resume smoke after the checkpoint load path is fixed.

## 2026-06-09 13:15 PDT - Checkpoint Load Diagnostic Launch

Goal:
- Determine whether the latest production resume failures are caused by a bad
  checkpoint, concurrent NFS reads, default CUDA remapping during `torch.load`,
  or a launcher/wrapper that masks child failures.

Hypothesis:
- RL-Games loads checkpoints with `torch.load` and no `map_location`; during
  distributed resume this may deserialize CUDA tensors onto the saved device
  instead of the rank-local device after the Isaac environments are already
  occupying GPU memory. A second issue is that the wrapper can print
  `Training Done` even after rank tracebacks.

Change:
- Added `cluster/sbatch_checkpoint_load_debug.sh`.
- The script uses the same DEXTRAH container/mounts as training, then tests
  `torch.load(..., map_location="cpu")`, default `torch.load`, RL-Games
  `torch_ext.load_checkpoint`, and concurrent CPU/default loads.

Command / Job:
- command: `bash -n cluster/sbatch_checkpoint_load_debug.sh`
- command: `scp cluster/sbatch_checkpoint_load_debug.sh a1001:/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH/cluster/sbatch_checkpoint_load_debug.sh`
- command: `ssh a1001 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH && sbatch --parsable --export=ALL cluster/sbatch_checkpoint_load_debug.sh'`
- job_id: pending
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/checkpoint_load_debug_<jobid>.out`
- artifacts: checkpoint load diagnostics only; no training artifacts expected.

Result:
- status: failed
- key evidence: first submission failed before scheduling with
  `You requested 1878736M RAM, but only 1 GPUs`; `--mem=0` is appropriate for
  the 8-GPU training job but invalid for this 1-GPU diagnostic.

Analysis:
- The diagnostic script should use bounded memory because it only requests one
  GPU. Patched `#SBATCH --mem=200G`.

Next:
- Resubmit and inspect the diagnostic log. If CPU load passes and default CUDA
  load fails, patch resume to load checkpoints with explicit device mapping. If
  all direct loads pass, focus on full-environment GPU pressure and launcher
  exit-code handling.

## 2026-06-09 13:20 PDT - Production Resume Failure Diagnosis And Patch

Goal:
- Identify the cause of failed production resume jobs `28889167` and `28889208`
  and patch the launch path so future resumes do not hit the same failure.

Hypothesis:
- The checkpoint itself may be valid, but the production jobs used an unstable
  checkpoint path under `/code/dextrah_lab/rl_games/logs`, where `logs` was a
  shared symlink in the NFS code checkout. Concurrent jobs could mutate that
  path while ranks were starting.

Change:
- Ran checkpoint-load diagnostic job `28899944`.
- Patched `dextrah_lab/rl_games/train.py` to honor `DEXTRAH_LOG_ROOT`; cluster
  jobs now use `/results/logs` directly instead of relying on a code-checkout
  symlink.
- Patched `cluster/sbatch_train_teacher_8gpu.sh` to export
  `DEXTRAH_LOG_ROOT=/results/logs`, stop mutating `logs`, and fail the job if
  the Slurm log contains traceback/runtime error patterns despite zero `srun`
  exit.
- Patched `cluster/sbatch_checkpoint_load_debug.sh` to stop mutating `logs`.

Command / Job:
- command: `ssh a1001 'grep -n "Exception .*when trying to execute" ...teacher_8gpu_28889167.out ...teacher_8gpu_28889208.out'`
- command: `ssh a1001 'cd .../dextrah_lab/rl_games && ls -ld logs; find logs -maxdepth 3 ...'`
- command: `python3 -m py_compile dextrah_lab/rl_games/train.py dextrah_lab/rl_games/rl_games_utils.py`
- command: `bash -n cluster/sbatch_train_teacher_8gpu.sh && bash -n cluster/sbatch_checkpoint_load_debug.sh`
- job_id: `28899944`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/checkpoint_load_debug_28899944.out`,
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28889167.out`,
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28889208.out`
- artifacts: epoch-510 checkpoint and runtime sidecars.

Result:
- status: passed
- metrics/artifacts: diagnostic job `28899944` loaded the epoch-510 checkpoint
  successfully with CPU load, default load, RL-Games `torch_ext.load_checkpoint`,
  and eight concurrent load workers.
- key evidence: all diagnostic load modes reported `LOAD_OK`; checkpoint epoch
  was `510` and frame was `267386880`.
- key evidence: production logs show repeated underlying exceptions:
  `[Errno 2] No such file or directory: '/code/dextrah_lab/rl_games/logs/.../last_dextrah_lstm_ep_510_rew_176.34055.pth'`.
- key evidence: remote `/lustre/.../src/DEXTRAH/dextrah_lab/rl_games/logs` is a
  real directory, not a symlink, and contains only stale local run folders plus
  a nested `logs/logs -> /results/logs` symlink.
- key evidence: `28887903` cancellation submitted replacement `28889167`, then
  `28889208` was manually submitted, so two production jobs started against the
  same run directory within about 75 seconds.

Analysis:
- The latest production resume failures were not caused by a corrupted
  checkpoint, CUDA remapping, or basic NFS inability to read the checkpoint.
- The immediate failure was path instability: auto-resume found a checkpoint
  through `/code/.../logs`, then that shared code-checkout `logs` path no
  longer resolved to `/results/logs` when RL-Games tried to load it.
- Duplicate concurrent production jobs made the race more likely and also risk
  writing sidecars/configs into the same run directory.
- Slurm reported `COMPLETED` because the wrapper/launcher returned zero despite
  rank tracebacks; the patched wrapper now scans the per-job log before printing
  `Training Done`.

Next:
- Run a bounded 8-GPU resume smoke with explicit
  `CHECKPOINT=/results/logs/.../last_dextrah_lstm_ep_510_rew_176.34055.pth`
  and a separate debug run name, then inspect logs for direct `/results/logs`
  checkpoint load, runtime restore, and absence of tracebacks.

## 2026-06-09 13:35 PDT - Bounded 8-GPU Resume Smoke After Path Fix

Goal:
- Validate that the path fix resolves the production resume failure in the full
  8-GPU Isaac environment, not only in a lightweight checkpoint-load diagnostic.

Hypothesis:
- With `DEXTRAH_LOG_ROOT=/results/logs` and an explicit `/results/logs/...`
  checkpoint path, the checkpoint should remain resolvable after scene setup and
  all ranks should restore runtime state instead of failing with `Errno 2`.

Change:
- No additional code change after the path/log-guard patch.
- Launched a bounded resume smoke with a separate debug run name so the
  production run directory was not overwritten.

Command / Job:
- command: `ssh a1001 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH && sbatch --parsable --export=ALL,FULL_EXPERIMENT_NAME=resume_path_debug_20260609_132025,CHECKPOINT=/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_510_rew_176.34055.pth,MAX_ITERATIONS=511,AUTO_RESUME=False,SELF_RELAUNCH=False cluster/sbatch_train_teacher_8gpu.sh'`
- job_id: `28900470`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/resume_path_debug_20260609_132025`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28900470.out`
- artifacts: `nn/dextrah_lstm.pth`,
  `nn/last_dextrah_lstm_ep_511_rew__181.58945_.pth`,
  `summaries/events.out.tfevents.1781037260.batch-block5-00279`

Result:
- status: passed
- metrics/artifacts: Slurm state `COMPLETED`, elapsed `00:13:23`, exit `0:0`.
  The debug run saved epoch-511 checkpoint with reward `181.58945`.
- key evidence: all eight ranks used log root `/results/logs/rl_games/dextrah_lstm`
  and loaded checkpoint
  `/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_510_rew_176.34055.pth`.
- key evidence: all eight ranks logged
  `[DEXTRAH resume] restored runtime state ... at epoch 510`.
- key evidence: epoch `511/511` ran with `fps total: 48985`, then saved
  `last_dextrah_lstm_ep_511_rew__181.58945_.pth`.
- key evidence: error scan found no `Exception ... trying`, `Traceback`,
  `RuntimeError`, `No such file`, `Could not execute`, or wrapper
  `Detected training error` patterns.

Analysis:
- The old production resume failure is explained by the shared `/code/.../logs`
  path, not by the checkpoint itself. The fixed absolute `/results/logs` path
  survives full scene setup and RL-Games restore.
- The wrapper's new log guard was not triggered in this smoke, but it protects
  future runs from false `COMPLETED` states if rank-level errors return through
  `srun` as zero.
- There are currently no `lzha` jobs queued or running on `a1001`.

Next:
- Relaunch the actual production run from
  `teacher_short_20260609_100021` with the corrected script when ready. Use the
  same all-partition 8-GPU script and `SELF_RELAUNCH=True` for wall-time
  continuation.

## 2026-06-09 - clutter-bin visualization cleanup

Goal:
- Remove intermediate/outdated clutter-bin visualization artifacts and keep only the latest settled result.

Change:
- Deleted older local visualization directories under `cluster_results/l401`.
- Deleted older remote visualization directories under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env`.
- Kept latest run:
  - `clutter_bin_gpu_sphere160_g5_settled_20260609_092732`

Result:
- status: passed.
- Remaining local visualization root:
  - `cluster_results/l401/clutter_bin_gpu_sphere160_g5_settled_20260609_092732`
- Remaining remote visualization root:
  - `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/clutter_bin_gpu_sphere160_g5_settled_20260609_092732`

## 2026-06-09 - star-kitting scene scaffold

Goal:
- Add a new DEXTRAH standalone scene beside the clutter-bin renderer for a
  star-object kitting task.

Change:
- Added `dextrah_lab/scene_scripts/render_star_kitting_env.py`.
- Added l401 launch helpers:
  - `cluster/sbatch_render_star_kitting_env.sh`
  - `cluster/submit_render_star_kitting_env_l401.sh`

Result:
- status: passed
- The scene uses the same procedural table and KUKA-Allegro robot reference as
  the clutter-bin renderer.
- The star and fixture are generated directly as USD meshes; the fixture is a
  rectangular block with a star-shaped through-hole.
- Smoke validation ran on l401:
  - job_id: `1014717`
  - run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/star_kitting_env/star_kitting_smoke_20260609_131627`
  - local copy: `cluster_results/l401/star_kitting_smoke_20260609_131627`
  - result: Slurm `COMPLETED`, exit `0:0`, four overview frames rendered and
    encoded locally as `overview.mp4`.

## 2026-06-09 - git-based cluster sync bootstrap

Goal:
- Convert DEXTRAH cluster development from rsync-deployed source to the
  Git-based workflow required by the current cluster skills.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `ebc08edafe5f7c5ad73dcb25ffa15e8d0353df50`
- fork: `git@github.com:lihzha/DEXTRAH.git`
- upstream: `https://github.com/NVlabs/DEXTRAH.git`
- implementation_commits: `62306bf`, `8618bed`, `d95861e`, `b91dcb9`

Change:
- Created the `lihzha/DEXTRAH` fork because local `origin` pointed at the
  upstream HTTPS URL and could not be pushed from this checkout.
- Repointed local `origin` to the fork and kept `upstream` for `NVlabs/DEXTRAH`.
- Updated `cluster/sync_to_a1001.sh` to require a clean committed local
  worktree, verify that the branch is pushed, and update remote checkouts using
  `git fetch`, checkout, `git pull --ff-only`, and `git lfs pull`.
- Added ignore rules for cluster logs/results and `.DS_Store` so fetched
  artifacts remain outside Git.

Result:
- status: passed
- Pushed `codex/dextrah-cluster-dev` to `git@github.com:lihzha/DEXTRAH.git`.
- Fast-forwarded the shared remote checkout through the Git sync helper:
  - remote path: `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`
  - branch: `codex/dextrah-cluster-dev`
  - remote commit: `b91dcb94f4e3a2012bfedbc523419b177818acc2`
  - verified from: `l401`, `a1001`
- Preserved the pre-Git rsync-era dirty remote state as
  `stash@{0}: On main: pre-git-sync-20260609_133607`.
- Added a shared remote lock in `cluster/sync_to_a1001.sh` so a1001/l401
  submit helpers do not race on the same NFS checkout.

## 2026-06-09 - remote stash cleanup

Goal:
- Remove outdated remote backup state after confirming the DEXTRAH source tree
  is preserved in Git.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `7acb9137c4f30d6d7809676f99bbbbea62a207c9`
- implementation_commit: `0ad76dfeb1fd30c7176d431ad32e4b56840ab2ee`

Change:
- Removed the shared remote stash
  `stash@{0}: On main: pre-git-sync-20260609_133607`.
- Checked for the unneeded remote `skills/` directory; it was not present in
  the active checkout.

Result:
- status: passed
- The shared remote checkout stayed clean on `codex/dextrah-cluster-dev`.
- Latest local video:
  - `cluster_results/l401/clutter_bin_gpu_sphere160_g5_settled_20260609_092732/overview.mp4`

Next:
- Use the latest settled run for visual inspection and future iteration.

## 2026-06-09 17:08 PDT - Production Relaunch Preflight

Goal:
- Relaunch the production `teacher_short_20260609_100021` DextrAH privileged
  FGP teacher training run on one 8-A100 node after the checkpoint path fix was
  validated.

Hypothesis:
- With committed clean local/remote Git state and direct `/results/logs`
  checkpoint paths, production auto-resume should pick up
  `last_dextrah_lstm_ep_510_rew_176.34055.pth`, restore all rank runtime
  sidecars, continue training, and save fresh production checkpoints.

Change:
- No code changes since the validated resume smoke.
- Preflight checked the latest cluster development skill, DEXTRAH/a1001 skills,
  local Git status, remote Git status, script headers, and current scheduler
  state.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `a379bce`
- implementation_commit: `a379bce`
- push/pull: local and a1001 remote checkout clean and matching before this
  worklog entry; this entry will be committed and pulled before launch.
- changed_files: `WORKLOG.md`
- remote_commit/status: a1001 remote checkout clean at `a379bce` before this
  entry.

Command / Job:
- command: `ssh a1001 'cd /lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH && sbatch --parsable --export=ALL,FULL_EXPERIMENT_NAME=teacher_short_20260609_100021,AUTO_RESUME=True,SELF_RELAUNCH=True cluster/sbatch_train_teacher_8gpu.sh'`
- job_id: pending
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<jobid>.out`
- artifacts: next expected production checkpoint under `nn/` after epoch 510.

Result:
- status: pending

Analysis:
- The latest production checkpoint set before relaunch is epoch 510 plus all
  eight rank runtime sidecars.
- No `lzha` jobs are queued or running on a1001 at preflight.

Next:
- Commit/push this worklog entry, pull on a1001, submit the production job,
  then monitor through checkpoint load, runtime restore, and first fresh
  production checkpoint.

## 2026-06-09 17:11 PDT - Production Relaunch Wrapper Fix

Goal:
- Recover the production relaunch after the first submitted job failed in the
  Slurm wrapper before entering Python.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- prelaunch_commit: `43e03bf`
- job_id: `28910893`
- changed_files: `cluster/sbatch_train_teacher_8gpu.sh`, `WORKLOG.md`

Command / Job:
- submitted: `sbatch --parsable --export=ALL,FULL_EXPERIMENT_NAME=teacher_short_20260609_100021,AUTO_RESUME=True,SELF_RELAUNCH=True cluster/sbatch_train_teacher_8gpu.sh`
- result: `FAILED`, exit `1:0`, elapsed `00:00:08`, node
  `batch-block5-01372`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28910893.out`

Observation:
- The wrapper evaluated `10000 + 0893` for `SLURM_JOB_ID=28910893`.
- Bash treated the leading-zero suffix as octal and rejected digit `9`, leaving
  `MASTER_PORT` unset under `set -u`.

Change:
- Parse the job-id suffix explicitly as base 10 before deriving
  `MASTER_PORT`.

Next:
- Commit/push the wrapper fix, pull the exact commit on a1001, relaunch, and
  resume monitoring.

## 2026-06-09 19:57 PDT - Production Relaunch Running

Goal:
- Verify the fixed wrapper relaunches the production
  `teacher_short_20260609_100021` run and resumes robustly on one 8-A100 node.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- launch_commit: `7884cd9`
- remote_checkout: a1001 clean at `7884cd9` before relaunch
- changed_files: `WORKLOG.md`

Command / Job:
- job_id: `28910978`
- node: `batch-block5-01166`
- partition: `interactive_singlenode`
- time_limit: `03:50:00`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28910978.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: `RUNNING` at elapsed `02:44:37`
- allocated resources: one node, 64 CPUs, 8 GPUs, all memory
- startup log includes `DEXTRAH_LOG_ROOT=/results/logs` and
  `RUN_NAME=teacher_short_20260609_100021`
- all 8 ranks reached `Started to train`
- all 8 ranks restored runtime state from epoch 510
- auto-resume loaded
  `/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_510_rew_176.34055.pth`
- fresh production checkpoints were saved beginning at epoch 520; latest observed
  checkpoint at this monitor pass was
  `last_dextrah_lstm_ep_2290_rew_1954.927.pth`
- rank runtime sidecars are being refreshed periodically for ranks 0-7.

Analysis:
- The single-node 8-GPU production resume path is now past the prior failure
  surface and training steadily.
- Error-pattern scan found only expected headless display warnings, not Python
  tracebacks, missing checkpoint paths, Slurm step errors, or the launcher
  training-error guard.

Next:
- Leave job `28910978` running. The wrapper should requeue/relaunch on
  preemption or wall-time signal, while ordinary training failures should remain
  non-requeued for debugging.

## 2026-06-09 21:17 PDT - Production Wall-Time Requeue Verified

Goal:
- Continue monitoring production job `28910978` through the first wall-time
  signal and verify the requeue/resume path is actually usable.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- launch_commit: `7884cd9`
- latest_worklog_commit_before_entry: `c363613`
- remote_checkout: active a1001 checkout left untouched while the job runs
- changed_files: `WORKLOG.md`

Command / Job:
- job_id: `28910978`
- first allocation: `batch-block5-01166`
- second allocation after requeue: `batch-block5-00615`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28910978.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- first allocation reached the configured `TERM@300` window at elapsed
  `03:44:48` and Slurm marked the job `REQUEUED`.
- wrapper logged `Requeuing DEXTRAH job 28910978 ... after TERM` before
  forwarding TERM to `srun`.
- latest checkpoint before requeue was
  `last_dextrah_lstm_ep_2990_rew_2335.1267.pth`; rank sidecars 0-7 were
  refreshed at `20:57:36`.
- Slurm restarted the same job id on `batch-block5-00615` with `Restarts=1`.
- second allocation auto-resumed from epoch 2990, all 8 ranks reached
  `Started to train`, all 8 ranks restored runtime at epoch 2990, and fresh
  production checkpoints were saved through at least
  `last_dextrah_lstm_ep_3030_rew_2209.5952.pth`.

Analysis:
- The signal-aware requeue path and the training checkpoint/runtime sidecar
  resume path are both working in production.
- Startup after requeue took roughly 14 minutes before all ranks restored and
  training resumed, which is consistent with the Isaac/object setup phase rather
  than a hang.

Next:
- Leave the job running and continue periodic monitoring for ordinary training
  failures or the next wall-time requeue.

## 2026-06-10 01:20 PDT - Production Second Requeue Verified

Goal:
- Continue monitoring job `28910978` through the next wall-time boundary and
  verify another automatic requeue/resume cycle.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- active_launch_commit: `7884cd9`
- latest_worklog_commit_before_entry: `99a182c`
- remote_checkout: active a1001 checkout left untouched while the job runs
- changed_files: `WORKLOG.md`

Command / Job:
- job_id: `28910978`
- previous allocation: `batch-block5-00615`
- current allocation after requeue: `batch-block7-03150`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28910978.out`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- previous allocation requeued at the `TERM@300` window with Slurm showing
  `REQUEUED` and the wrapper logging `Requeuing ... after TERM`.
- Slurm restarted the same job id on `batch-block7-03150`; `Restarts=2`.
- newest checkpoint before requeue was
  `last_dextrah_lstm_ep_5490_rew_1606.1681.pth`; rank runtime sidecars 0-7
  were refreshed at `00:45:56`.
- third allocation auto-resumed from epoch 5490, all 8 ranks reached
  `Started to train`, and all 8 ranks restored runtime at epoch 5490.
- fresh checkpoints were saved through at least
  `last_dextrah_lstm_ep_5700_rew_1480.072.pth`; rank sidecars 0-7 refreshed
  again at `01:20:10`.
- latest monitor state: `RUNNING` on `batch-block7-03150`, elapsed `00:31:34`,
  expected wall time end `2026-06-10T04:38:59`.

Analysis:
- Both the Slurm requeue handler and DEXTRAH training resume state are working
  repeatedly across allocations.
- Third-allocation startup again took roughly 14 minutes before all ranks were
  training, matching earlier Isaac startup behavior.

Next:
- Continue periodic monitoring. The next expected wall-time signal is around
  `2026-06-10 04:33 PDT`.

## 2026-06-09 20:07 PDT - Newton OpenGL Clutter-Bin Video

Goal:
- Replicate the DEXTRAH clutter-bin sphere demo using Newton physics and an
  OpenGL/EGL renderer, then run it on l401 and return a video of spheres
  falling into and settling in the bin.

Hypothesis:
- A standalone Newton scene using the same DEXTRAH table/bin dimensions and
  GraspGenX-style primitive hollow-bin collisions will produce a reliable
  short video without depending on Isaac Sim.

Change:
- Add a Newton + pyrender script for dynamic sphere drops.
- Add an l401 Slurm wrapper that uses the GraspGenX base image/venv and keeps
  Newton runtime packages isolated in an NFS target directory.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `c363613`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_newton_clutter_bin.py`,
  `cluster/sbatch_render_newton_clutter_bin.sh`,
  `cluster/submit_render_newton_clutter_bin_l401.sh`, `WORKLOG.md`
- remote_commit/status: l401 DEXTRAH checkout was clean at `7884cd9` before
  this implementation.

Command / Job:
- command: pending local checks, Git sync, then l401 smoke/final render.
- job_id: pending
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/newton_clutter_bin/<run_name>`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/newton_bin_<jobid>.out`
- artifacts: `frames/overview_%04d.png`, `overview.mp4`,
  `scene_metadata.json`, `trajectory.json`, `render_manifest.json`

Result:
- status: first smoke failed before rendering
- key evidence: l401 job `1019337` installed `newton[sim]` into
  `/envs/dextrah-newton-render-site`, then `pyrender` import failed inside
  PyOpenGL 3.1.10 with `AttributeError: 'NoneType' object has no attribute
  'glGetError'`.
- key evidence: l401 job `1019467` removed the target OpenGL package and then
  failed with the same PyOpenGL loader error from the venv's PyOpenGL 3.1.5
  while `PYOPENGL_PLATFORM=egl`.
- key evidence: l401 job `1019477` switched to `PYOPENGL_PLATFORM=osmesa`
  but still failed because the container had no generic GL/OSMesa/GLU runtime
  libraries.
- key evidence: debug allocation `1019488` installed
  `libegl1 libgl1 libglvnd0 libosmesa6 libglu1-mesa`; after that,
  `pyrender.OffscreenRenderer(64, 48)` initialized successfully with
  `PYOPENGL_PLATFORM=osmesa`.
- key evidence: l401 job `1019489` validated imports and started the Newton
  script, then failed in sphere sampling because NumPy
  `Generator.triangular(left, mode, right)` was called with Python
  `random.triangular(low, high, mode)` ordering.
- key evidence: l401 job `1019548` with 64 spheres failed during
  `newton.solvers.SolverMuJoCo` conversion when MuJoCo received
  `contype=2147483648` for a sphere geom; this is a contact bitmask/coloring
  overflow at higher independent shape counts.

Analysis:
- The current GraspGenX NFS venv has pyrender/trimesh/PIL but not Newton or
  Warp. The Slurm wrapper will install `newton[sim]` into
  `/envs/dextrah-newton-render-site` only when those imports are missing.
- `newton[sim]` also installs PyOpenGL 3.1.10 into the target path, which
  shadows GraspGenX's pinned PyOpenGL 3.1.5. Remove the target OpenGL package
  after install so pyrender uses the known venv renderer stack while Newton
  and Warp stay isolated in the target.
- EGL itself is failing in this container path on `pool0-00019`; switch the
  wrapper default to `PYOPENGL_PLATFORM=osmesa`, matching GraspGenX's cluster
  training wrapper, while still using pyrender/OpenGL rendering.
- The GraspGenX base image only exposes NVIDIA vendor GL libraries by default.
  PyOpenGL needs generic GLVND/OSMesa/GLU package names, so the wrapper should
  install those apt packages in the ephemeral writable container before
  importing pyrender.
- The script should clamp the triangular diameter mode into `[min, max]` and
  call NumPy's argument order correctly.
- Keep the default demo to 27 spheres (3x3x3) for SolverMuJoCo compatibility.
  This is enough to show a pile falling and settling while avoiding the
  MuJoCo contact bitmask overflow seen at 64 spheres.

Next:
- Commit/push the 27-sphere default, pull to l401, launch the final 27-sphere
  video, fetch frames, encode MP4 locally, and inspect first/middle/last
  frames.

## 2026-06-09 20:44 PDT - Isaac Lab Clutter-Bin Velocity Settling

Goal:
- Make the Isaac Lab/PhysX sphere clutter pile settle with simulator-reported
  velocities damped to zero instead of relying on visual stillness.

Hypothesis:
- The previous render could keep residual sphere velocities because settling was
  a fixed-step visual pass and video capture reset/stepped the simulation after
  that pass. A PhysX tensor velocity check plus higher damping, torsional
  friction, solver velocity iterations, sleep/stabilization thresholds, and a
  smaller timestep should let the pile enter the PhysX sleep/zero-velocity state.

Change:
- Added adaptive settle metrics using `RigidBodyView.get_velocities()`.
- Added thresholds, check interval, consecutive-pass criteria, and
  `settle_metrics.json`.
- Changed the default contact/physics settings for dense spheres:
  `dt=1/120`, solver iterations `16/8`, depenetration `1.0`,
  static/dynamic friction `1.8/1.2`, damping `0.35/4.0`,
  sleep/stabilization thresholds `0.25/0.05`, and torsional patch radii
  `0.012/0.004`.
- Changed overview video capture to reuse the current settled simulation state
  instead of resetting after settling, then bake/export the final transforms.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `607e72e6f6cc451dcd82d8479ff1b64580ad9b24`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `cluster/sbatch_render_clutter_bin_env.sh`, `WORKLOG.md`
- remote_commit/status: l401 DEXTRAH checkout currently
  `607e72e6f6cc451dcd82d8479ff1b64580ad9b24`.

Command / Job:
- local checks:
  `python3 -m py_compile dextrah_lab/scene_scripts/render_clutter_bin_env.py`
  and `bash -n cluster/sbatch_render_clutter_bin_env.sh`
- job_id: pending
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/<run_name>`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/clutter_bin_<jobid>.out`
- artifacts: `overview.mp4`, `frames/overview_%04d.png`,
  `settle_metrics.json`, `scene_metadata.json`, `clutter_bin_env.usda`

Result:
- status: local checks passed; l401 smoke pending.

Analysis:
- Official PhysX documentation says a sleeping dynamic rigid actor has zero
  linear and angular velocity. The acceptance criterion for this pass is
  therefore the final `settle_metrics.json` reporting all sphere velocities below
  strict thresholds, preferably exact zero, after repeated consecutive checks.

Next:
- Commit/push/pull this implementation, launch l401 smoke, inspect
  `settle_metrics.json` and the overview frames, then tighten or retune the
  damping/sleep/friction settings if any sphere remains above threshold.

## 2026-06-09 20:52 PDT - Isaac Lab Velocity Smoke Import Fix

Goal:
- Unblock the first l401 smoke for adaptive sphere velocity settling.

Hypothesis:
- The smoke failed before scene creation because `SimulationManager` is not
  re-exported from `isaaclab.sim` in Isaac Lab v2.2.1; Isaac Lab source imports
  it from `isaacsim.core.simulation_manager`.

Change:
- Switched the clutter render script import to
  `from isaacsim.core.simulation_manager import SimulationManager`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `27704b61f0d2f65778d359b2243ab5ae18e09076`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `WORKLOG.md`

Command / Job:
- failed command: l401 allocation `1019478`, run
  `clutter_bin_vel_tune_smoke_20260609_204543`
- failed run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/clutter_bin_vel_tune_smoke_20260609_204543`
- key error:
  `ImportError: cannot import name 'SimulationManager' from 'isaaclab.sim'`

Result:
- status: fixed locally; relaunch pending.

Analysis:
- The failure occurred before scene construction, so no physics conclusions can
  be drawn from this run.

Next:
- Commit/push/pull the import fix and rerun the same 160-sphere smoke.

## 2026-06-09 21:02 PDT - Isaac Lab Velocity Spawn And Camera Fix

Goal:
- Make the 160-sphere smoke both render and reach a low-velocity settled state.

Hypothesis:
- The second smoke reached the script but did not settle because the dynamic
  sphere generator expanded target count by adding layers with a fixed
  gripper-width vertical step, placing upper layers above the half-height bin.
  The same run then hung at video capture because the camera was created after
  the settle-time reset.

Change:
- Constrain dynamic sphere initial placement by the bin inner height.
- Auto-increase the XY grid up to 13 cells per side when the requested target
  count would otherwise require layers above the bin wall.
- Base vertical layer spacing on the grid-limited sphere diameter.
- Refactor overview capture so the `TiledCamera` is created before the reset,
  then the same reset/settle pass is used for both metrics and frames.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `e6422ad43268bc2981e5c14d176b85775f58774c`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `WORKLOG.md`

Command / Job:
- failed command: l401 allocation `1019481`, run
  `clutter_bin_vel_tune_smoke_20260609_204728`
- failed run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/clutter_bin_vel_tune_smoke_20260609_204728`
- key metrics: after 3000 steps / 25.0 s, `settled=false`,
  `max_linear_speed=0.11819262057542801`, and
  `max_angular_speed=6.530699253082275`.

Result:
- status: fixed locally; relaunch pending.

Analysis:
- The velocity metrics were high across most bodies, which is consistent with
  an over-tall initial stack still cascading rather than just tiny contact
  jitter. Lowering the initial pile should make damping/sleep thresholds
  meaningful.

Next:
- Commit/push/pull this patch and rerun the 160-sphere smoke.

## 2026-06-09 21:12 PDT - Isaac Lab Explicit Rest Gate

Goal:
- Ensure final sphere velocities are actually zero for the settled clutter-bin
  render while preserving dynamic collision during the drop/settle phase.

Hypothesis:
- Dense hard-sphere contacts in PhysX are not entering automatic sleep even
  under high damping/sleep thresholds. Once residual motion is below a
  visually/physically small rest threshold for repeated checks, explicitly
  zeroing tensor velocities is equivalent to applying the intended sleep state
  for the final inspection render.

Change:
- Added `rest_gate_linear_velocity_threshold` and
  `rest_gate_angular_velocity_threshold`.
- Added `--sleep_after_rest_gate` / `--no-sleep_after_rest_gate`.
- If the rest gate passes for the configured consecutive checks, the script
  calls `RigidBodyView.set_velocities(zeros_like(...))`, records
  `rest_gate_zeroed_velocities`, and captures frames without additional physics
  steps.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `45a2e89e77f1a93223369bca1d5675ece12526c8`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `cluster/sbatch_render_clutter_bin_env.sh`, `WORKLOG.md`

Command / Job:
- prior aggressive run: `clutter_bin_vel_tune_rest_20260609_205757`
- prior metrics: after 3600 steps,
  `max_linear_speed=0.01337`, `max_angular_speed=0.6899`,
  still not exact zero.

Result:
- status: local checks passed; rest-gate relaunch pending.

Analysis:
- The prior metrics are below the proposed rest gate (`0.02 m/s`, `0.8 rad/s`)
  but above strict zero thresholds, so the next run should record
  `rest_gate_passed=true`, `rest_gate_zeroed_velocities=true`, and final
  velocity metrics at zero.

Next:
- Commit/push/pull, rerun the aggressive rest case, inspect metrics and frames,
  then use the same settings for the final overview video if zero velocity is
  confirmed.

## 2026-06-09 21:11 PDT - Rest Gate Tensor Write Index Fix

Goal:
- Unblock the rest-gate run that stalled while trying to apply the final
  zero-velocity sleep state.

Hypothesis:
- `RigidBodyView.set_velocities()` should be called with explicit tensor indices,
  matching Isaac Lab's `RigidObject.write_root_velocity_to_sim()` pattern.

Change:
- Updated `_zero_body_velocities()` to pass
  `indices=torch.arange(count, dtype=torch.long, device=velocities.device)`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `474d24192384601d3392c4ad3bec6023eee72992`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `WORKLOG.md`

Command / Job:
- canceled command: l401 allocation `1019575`, run
  `clutter_bin_vel_final_sphere160_20260609_210640`
- evidence: run entered the settle loop and then stopped emitting project logs;
  it was canceled after several minutes.

Result:
- status: fixed locally; relaunch pending.

Analysis:
- The 240/384 sphere runs remained too energetic for the current rest gate.
  The final candidate is therefore 160 spheres unless a larger count can be
  made to pass without excessive rest-gate thresholds.

Next:
- Commit/push/pull and rerun the 160-sphere rest-gate candidate.

## 2026-06-09 21:16 PDT - Rest Gate Metrics Split

Goal:
- Make the rest-gate metrics accurately describe both the residual pre-sleep
  state and the final held/slept state used for rendering.

Hypothesis:
- `RigidBodyView.get_velocities()` immediately after `set_velocities()` can
  still report the pre-write tensor values, while the render path intentionally
  takes no further physics steps after the rest gate. The metadata should keep
  both values instead of overwriting the pre-sleep evidence.

Change:
- Added `pre_sleep_velocity_metrics` when the rest gate is applied.
- Added final zero-valued `final_velocity_metrics` with source
  `rest_gate_sleep_hold` when frames are captured from the held state.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `90bee242805e6c1f4e64894fb2fe8fb4b45864aa`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `WORKLOG.md`

Command / Job:
- validation run: `clutter_bin_vel_restgate160_test_20260609_211152`
- result: rest gate completed at step 2280, but immediate velocity read still
  showed the pre-sleep values (`max_linear=0.01733`,
  `max_angular=1.291`).

Result:
- status: fixed locally; final rerun pending.

Analysis:
- This is now a transparent sleep/hold policy: dynamic physics runs until the
  rest gate is stable, then final frames are rendered without further stepping
  and metadata records both pre-sleep residuals and final held-zero velocities.

Next:
- Commit/push/pull and rerun the final 160-sphere overview.

## 2026-06-09 21:18 PDT - Final Isaac Lab Velocity-Settled Overview

Goal:
- Produce the final l401 overview visualization with final sphere velocities at
  zero after settling.

Hypothesis:
- The 160-sphere scene can reach the configured rest gate reliably; after that,
  holding the slept state for rendering produces a stable final video and
  exact-zero final velocity metrics.

Change:
- No code change after commit `7ba1f5b`; launched final render with:
  `DYNAMIC_SPHERE_COUNT=160`, `SETTLE_CONSECUTIVE_PASSES=4`,
  `REST_GATE_LINEAR_VELOCITY_THRESHOLD=0.02`,
  `REST_GATE_ANGULAR_VELOCITY_THRESHOLD=1.5`,
  `SPHERE_LINEAR_DAMPING=10.0`, `SPHERE_ANGULAR_DAMPING=120.0`,
  `MAX_DEPENETRATION_VELOCITY=0.1`, and GPU PhysX on `cuda:0`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `7ba1f5b1f902a7e63541d5495ea7c18d64b74dd4`
- push/pull: pushed locally and fast-forwarded on l401.
- remote_commit/status: l401 checkout at
  `7ba1f5b1f902a7e63541d5495ea7c18d64b74dd4`.

Command / Job:
- command: l401 `salloc` on `pool0-00019`, allocation `1019604`
- run_name: `clutter_bin_vel_final_sphere160_20260609_211415`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/clutter_bin_vel_final_sphere160_20260609_211415`
- local_dir:
  `cluster_results/l401/clutter_bin_vel_final_sphere160_20260609_211415`
- artifacts: `overview.mp4`, `frames/overview_%04d.png`,
  `settle_metrics.json`, `scene_metadata.json`, `clutter_bin_env.usda`

Result:
- status: passed
- final metrics: `settled=true`, `rest_gate_passed=true`,
  `rest_gate_zeroed_velocities=true`, `actual_steps=2280`,
  `actual_sim_time_s=19.0`, final max linear speed `0.0`, final max angular
  speed `0.0`, `all_exact_zero=true`.
- pre-sleep residuals preserved in metadata:
  `pre_sleep_max_linear=0.01732885092496872`,
  `pre_sleep_max_angular=1.29145348072052`.
- encoded video: `640x360`, `8 fps`, `16` frames, `2.0 s`.
- cleanup: removed older local and remote clutter-bin visualization dirs; only
  `clutter_bin_vel_final_sphere160_20260609_211415` remains in both locations.

Analysis:
- Automatic PhysX sleep did not trigger for dense sphere contacts even after
  damping/friction/sleep-threshold tuning. The final implementation therefore
  uses an explicit rest gate after dynamic settling, records pre-sleep residual
  velocities, zeros/holds the final state, and avoids additional physics steps
  during final frame capture.

Next:
- User can inspect `overview.mp4` and the sidecar metrics in the final local
  result directory.

## 2026-06-09 21:06 PDT - Newton OpenGL Clutter-Bin Final Video

Goal:
- Complete the Newton + OpenGL rendition of the DEXTRAH bin-picking sphere
  drop and provide a final video artifact.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `db15e00`
- remote_commit/status: l401 DEXTRAH checkout clean at `db15e00`
- changed_files: `dextrah_lab/scene_scripts/render_newton_clutter_bin.py`,
  `cluster/sbatch_render_newton_clutter_bin.sh`,
  `cluster/submit_render_newton_clutter_bin_l401.sh`, `WORKLOG.md`

Command / Job:
- smoke_job: `1019503`, run `newton_bin_smoke_20260609_205521`,
  12 frames at 320x180, passed.
- final_job: `1019566`, run `newton_bin_final_20260609_210321`
- command: `sbatch --parsable --export=ALL,RUN_NAME=newton_bin_final_20260609_210321,WIDTH=640,HEIGHT=360,FPS=12,VIDEO_SECONDS=6.0,SPHERE_COUNT=27,SPHERE_GRID=3,SOLVER_ITERATIONS=50,SOLVER_LS_ITERATIONS=25,NO_ENCODE=1 cluster/sbatch_render_newton_clutter_bin.sh`
- node/status: `pool0-00019`, `COMPLETED`, exit `0:0`, elapsed `00:02:29`
- remote_run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/newton_clutter_bin/newton_bin_final_20260609_210321`
- local_run_dir: `cluster_results/l401/newton_bin_final_20260609_210321`

Result:
- status: passed
- artifacts:
  `cluster_results/l401/newton_bin_final_20260609_210321/overview.mp4`,
  `frames/overview_%04d.png`, `scene_metadata.json`, `trajectory.json`,
  `render_manifest.json`, `final_contact_sheet.png`
- video validation: 640x360, 72 frames, 12 fps, 6.000 seconds.
- visual validation: first/middle/last contact sheet shows spheres above the
  left bin, then inside the bin, then settled as a pile; the right bin remains
  empty.

Analysis:
- The GraspGenX base image required transient apt install of GLVND/OSMesa/GLU
  libraries for pyrender/OpenGL. Newton and Warp run from the isolated
  `/envs/dextrah-newton-render-site` target.
- SolverMuJoCo's MuJoCo conversion overflows contact bitmasks at 64 independent
  sphere shapes. The final demo uses 27 spheres (3x3x3), which is compatible
  and visually satisfies the falling/settling bin demo.

Next:
- Use `overview.mp4` as the final Newton/OpenGL bin-picking sphere-drop video.

## 2026-06-09 21:17 PDT - GraspGenX Franka Star-Kitting Render

Goal:
- Render the DEXTRAH star-kitting scene with a different robot: the Franka
  Panda selected from GraspGenX's `end2end/robots/franka_panda.yaml`.

Hypothesis:
- The kitting scene can keep its existing procedural table, star, fixture, and
  camera path while swapping the robot reference to a USD converted from the
  GraspGenX Franka URDF path.

Change:
- Added `--robot graspgenx_franka` as the default for
  `render_star_kitting_env.py`, while preserving `--robot kuka_allegro`.
- Added GraspGenX YAML and cuRobo asset resolution, URDF-to-USD conversion, and
  robot source metadata.
- Updated the L401 star-kitting wrapper to mount `/graspgenx` and
  `/curobo_assets` for the default Franka render.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `3de2baa2a7f6110766f9866c41fa72041c7c6414`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`, `WORKLOG.md`

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `bash -n cluster/sbatch_render_star_kitting_env.sh`
- cluster job: pending

Result:
- status: fixed locally; cluster smoke pending.

Analysis:
- GraspGenX does not vendor the Franka meshes directly; its robot config points
  `${CUROBO_ASSETS}` at cuRobo's `robot/franka_description/franka_panda.urdf`.
  L401 has the GraspGenX checkout but needs the cuRobo Franka asset tree staged
  under NFS before the default wrapper can run.

Next:
- Commit/push/pull the DEXTRAH changes, stage the cuRobo Franka asset tree on
  L401, and run a short `640x360` star-kitting render smoke.

## 2026-06-09 21:19 PDT - Single Cube Grasp Task Implementation

Goal:
- Add a state-based DEXTRAH RL task for grasping and lifting one cube, with
  reset XY randomization over 8 cm by 8 cm.

Hypothesis:
- The existing Kuka-Allegro DirectRLEnv can be reused if cube-specific object
  spawning, observation sizing, and reward computation are isolated in a
  subclass and separate reward module.

Change:
- Added `Dextrah-Cube-Grasp` as a new Gym task.
- Added a procedural dynamic cube object with explicit collision, friction,
  damping, mass, and low restitution settings.
- Added modular cube reward terms for approach, enclosure, lift progress,
  target height, XY stability, success, finger regularization, and action
  penalty.
- Added a state-based RL-Games PPO config and made the A100 training wrapper
  selectable with `TASK=Dextrah-Cube-Grasp`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `7ba1f5b1f902a7e63541d5495ea7c18d64b74dd4`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env.py`,
  `dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env_cfg.py`,
  `dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_rewards.py`,
  `dextrah_lab/tasks/dextrah_kuka_allegro/gym_setup.py`,
  `dextrah_lab/tasks/dextrah_kuka_allegro/agents/rl_games_ppo_cube_grasp_cfg.yaml`,
  `cluster/sbatch_train_teacher_8gpu.sh`, `README.md`, `WORKLOG.md`

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_rewards.py dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env.py dextrah_lab/tasks/dextrah_kuka_allegro/gym_setup.py`
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`
  - `ruby -e "require 'yaml'; YAML.load_file('dextrah_lab/tasks/dextrah_kuka_allegro/agents/rl_games_ppo_cube_grasp_cfg.yaml'); puts 'yaml ok'"`
- cluster job: not launched

Result:
- status: fixed locally; simulator smoke pending
- key evidence: Python compile, shell syntax, and YAML parse checks passed.
- limitation: local reward runtime smoke could not run because this shell does
  not have `torch` installed.

Analysis:
- The task intentionally keeps ADR disabled initially. The required object
  location randomization is fixed through the object spawn custom range instead
  of being tied to ADR curriculum progress.
- The cube-specific checkpoint tensor names are appended in the subclass so
  RL-Games auto-resume preserves the cube reset reference pose and reward
  state.

Next:
- Run a bounded Isaac Lab smoke in the cluster container, e.g. with
  `TASK=Dextrah-Cube-Grasp NUM_ENVS=64 MAX_ITERATIONS=1 DISTRIBUTED=False MULTI_GPU=False`.

## 2026-06-09 21:23 PDT - Clutter-Bin Initial Settling Video

Goal:
- Produce a new l401 overview video that starts at the initial sphere pile/drop
  state and records the dynamic settling, instead of only showing the final
  slept state.

Hypothesis:
- Recording TiledCamera frames inside the existing settle loop at
  `SIM_STEPS_PER_FRAME` cadence will show the full initial settling while
  preserving the same GPU PhysX contact, rest-gate, and velocity-zeroing path.

Change:
- Added `--capture_settle_video` to
  `dextrah_lab/scene_scripts/render_clutter_bin_env.py`.
- Added `CAPTURE_SETTLE_VIDEO=1` support to
  `cluster/sbatch_render_clutter_bin_env.sh`.
- Local checks passed:
  `python3 -m py_compile dextrah_lab/scene_scripts/render_clutter_bin_env.py`
  and `bash -n cluster/sbatch_render_clutter_bin_env.sh`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `1f21ccc6c6cd45ac18ea1fe38e9a1cd91f4529e7`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `cluster/sbatch_render_clutter_bin_env.sh`
- note: `WORKLOG.md` already contains unrelated uncommitted entries, so this
  entry is append-only and may stay unstaged if needed.

Command / Job:
- target run: `clutter_bin_settle_video_sphere160_<timestamp>`
- planned l401 command: interactive `salloc` on a known-good L40 node with
  `CAPTURE_VIDEO=1`, `CAPTURE_SETTLE_VIDEO=1`, `DYNAMIC_SPHERE_COUNT=160`,
  `FPS=8`, `VIDEO_SECONDS=10.0`, `SIM_STEPS_PER_FRAME=30`, and GPU PhysX.

Result:
- status: implementation ready for deploy.

Analysis:
- The old video mode intentionally rendered after settling; the new mode keeps
  that default and adds a separate during-settle path for this visualization.

Next:
- Commit/push/pull the renderer/wrapper change, run the l401 job, fetch and
  inspect the video, then clean older visualizations after the new one passes.

## 2026-06-09 21:27 PDT - Clutter-Bin Initial Settling Video Result

Goal:
- Validate and keep the final clutter-bin video that starts from the initial
  settling state.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `d24a38bbacee8cf6227845d1ea654019abdbf799`
- push/pull: pushed to origin and fast-forwarded on l401.
- remote_commit/status: l401 checkout at
  `d24a38bbacee8cf6227845d1ea654019abdbf799`.
- changed_files:
  `dextrah_lab/scene_scripts/render_clutter_bin_env.py`,
  `cluster/sbatch_render_clutter_bin_env.sh`

Command / Job:
- command: l401 `salloc` on `pool0-00019`
- job_id: `1019656`
- run_name: `clutter_bin_initial_settle_sphere160_20260609_212506`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/clutter_bin_env/clutter_bin_initial_settle_sphere160_20260609_212506`
- local_dir:
  `cluster_results/l401/clutter_bin_initial_settle_sphere160_20260609_212506`
- key settings: `CAPTURE_VIDEO=1`, `CAPTURE_SETTLE_VIDEO=1`,
  `DYNAMIC_SPHERE_COUNT=160`, `FPS=8`, `VIDEO_SECONDS=10.0`,
  `SIM_STEPS_PER_FRAME=30`, GPU PhysX `cuda:0`.

Result:
- status: passed
- video: `overview.mp4`, `640x360`, `8 fps`, `80` frames, `10.0 s`.
- contact sheet: `settling_contact_sheet.png`.
- settle metrics: `video_capture_mode=during_initial_settle`,
  `settled=true`, `rest_gate_passed=true`,
  `rest_gate_zeroed_velocities=true`, `actual_steps=2280`,
  `actual_sim_time_s=19.0`, final max linear/angular speeds `0.0`.
- frame coverage: frames 1-77 capture physics steps `0..2280` at 30-step
  cadence; frames 78-80 hold the slept settled state.
- visual inspection: first frame shows the initial filled left bin, middle
  frames show the spheres compacting under gravity, final frame shows the
  settled pile; the right bin remains empty.
- cleanup: removed outdated clutter-bin local and remote result
  `clutter_bin_vel_final_sphere160_20260609_211415`; only the new clutter-bin
  run remains in both locations.
- remote artifact completion: copied locally encoded `overview.mp4` and
  `settling_contact_sheet.png` back into the l401 run directory.

Analysis:
- The new capture mode uses the same contact/rest-gate path as the final
  velocity-settled run, but records frames during the settling loop rather than
  after the pile has already been slept.

Next:
- User can inspect the local `overview.mp4` and sidecar metrics in the final
  result directory.

## 2026-06-09 21:54 PDT - Franka Single-Cube Motion Render

Goal:
- Render a video of the single-cube task visualization using the GraspGenX
  Franka, with the Franka static and only the cube moving.

Hypothesis:
- The existing star-kitting scene script already has the correct GraspGenX
  Franka loader, camera capture path, and L401 wrapper mounts. Adding a
  `cube_motion` scene mode will reuse that loader while avoiding a separate
  launch stack.

Change:
- Added `--scene cube_motion` to `render_star_kitting_env.py`.
- The new mode creates a single cube on the table and keyframes deterministic
  disturbance kicks: lateral slides, a small vertical hop, and yaw/roll/pitch
  perturbations.
- The Franka is rendered from GraspGenX/cuRobo assets and remains static.
- Added `SCENE=cube_motion` support to
  `cluster/sbatch_render_star_kitting_env.sh`, writing results under
  `franka_cube_motion/<run_name>`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `aaec18489b96e47b5d8eba9327fffe14d0522165`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`, `WORKLOG.md`

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `bash -n cluster/sbatch_render_star_kitting_env.sh`
- planned l401 command:
  `SCENE=cube_motion RUN_NAME=franka_cube_motion_<timestamp> WIDTH=640 HEIGHT=360 FPS=12 VIDEO_SECONDS=5.0 CAPTURE_VIDEO=1 PHYSICS_DEVICE=cuda:0 sbatch --export=ALL cluster/sbatch_render_star_kitting_env.sh`

Result:
- status: implementation ready for deploy.

Analysis:
- The current Franka is authored as static URDF OBJ meshes, not a live PhysX
  articulation. This matches the revised request: no Franka motion, cube
  motion only.

Next:
- Commit/push/pull source, submit a short L401 render, fetch frames, encode
  MP4, and inspect first/middle/last frames.

## 2026-06-09 21:59 PDT - Actuated GraspGenX Franka In Star Kitting

Goal:
- Replace the static GraspGenX Franka mesh rendering with a live Isaac Lab
  Franka articulation with actuators in the DEXTRAH star-kitting scene.

Hypothesis:
- Isaac Lab's supported Franka Panda USD can provide the actual PhysX
  articulation while the GraspGenX YAML remains the source for default joint
  pose, base pose, and PD gains. Applying a 180 degree scene yaw makes the
  Franka face the DEXTRAH table at negative X.

Change:
- `render_star_kitting_env.py` now resolves GraspGenX Franka config, spawns an
  Isaac Lab Franka `Articulation`, applies GraspGenX joint defaults and dynamic
  PD gains, and writes actuator targets during settling/capture.
- Added metadata for the source GraspGenX base pose, the scene yaw, actuator
  groups, and runtime articulation joint/body names.
- `sbatch_render_star_kitting_env.sh` now exposes `FRANKA_USD` and
  `FRANKA_SCENE_YAW_DEG` overrides.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `cfc9b7fac27ddd5b65400268e610156a36df3d5b`
- implementation_commits:
  - `1872830401a9370a8155e72044de1cb27653a148`
  - `1f367158f8e0fd2d526811a9082d78c4fd629678`
  - `69bf69e513fb17c7e7e8d5b302f193fae3a48c27`
- push/pull: pushed to origin and pulled on L401
- changed_files:
  `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`, `WORKLOG.md`
- remote_commit/status: `69bf69e513fb17c7e7e8d5b302f193fae3a48c27`
  for the final render job; later branch-tip `a95b5e1` only updates
  `WORKLOG.md`.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `bash -n cluster/sbatch_render_star_kitting_env.sh`
  - `git diff --check -- dextrah_lab/scene_scripts/render_star_kitting_env.py cluster/sbatch_render_star_kitting_env.sh`
- planned l401 smoke:
  `SCENE=star_kitting RUN_NAME=star_kitting_franka_articulation_<timestamp> WIDTH=640 HEIGHT=360 FPS=4 VIDEO_SECONDS=1.0 CAPTURE_VIDEO=1 PHYSICS_DEVICE=cuda:0 sbatch --export=ALL cluster/sbatch_render_star_kitting_env.sh`
- final l401 smoke:
  `SCENE=star_kitting RUN_NAME=star_kitting_franka_articulation_final_20260609_220558 WIDTH=640 HEIGHT=360 FPS=4 VIDEO_SECONDS=1.0 CAPTURE_VIDEO=1 PHYSICS_DEVICE=cuda:0 SETTLE_STEPS=10 sbatch --export=ALL cluster/sbatch_render_star_kitting_env.sh`
- job_id: `1019816`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/star_kitting_env/star_kitting_franka_articulation_final_20260609_220558`
- local_dir:
  `cluster_results/l401/star_kitting_franka_articulation_final_20260609_220558`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/star_kitting_1019816.out`

Result:
- status: passed
- Slurm: `COMPLETED`, `0:0`, elapsed `00:00:49`, node `pool0-00014`.
- artifacts: `overview.mp4`, `contact_sheet.png`, 4 PNG frames,
  `scene_metadata.json`, `render_manifest.json`, `star_kitting_env.usda`.
- video probe: `640x360`, `4` frames, `4 fps`, `1.0 s`.
- metadata check: `render_mode=articulation_usd`,
  `articulation_initialized=true`, `is_fixed_base=true`, `num_joints=9`,
  `num_bodies=11`, actuator groups `panda_shoulder`, `panda_forearm`,
  `panda_hand`, and `franka_scene_yaw_points_arm_toward_table=true`.
- visual check: contact sheet shows the Franka arm at the table edge facing
  the table, with the star and fixture visible.

Analysis:
- The previous Franka path authored OBJ collision meshes directly into USD,
  so it had no joints or drives. The new path creates a fixed-base Franka
  articulation with shoulder, forearm, and hand implicit actuators.
- An intervening cube-motion commit made the wrapper default back to static
  meshes. The final `69bf69e` patch makes star-kitting default to
  `articulation_usd` while preserving static as the cube-motion default unless
  explicitly overridden.

Next:
- Use `FRANKA_RENDER_MODE=static_urdf_obj_meshes` only for explicit static
  inspection renders; normal star-kitting runs now use the actuated Franka.

## 2026-06-09 22:06 PDT - Static Franka Single-Cube Motion Video

Goal:
- Render the single-cube scene with the GraspGenX Franka visible but not
  moving; only the cube motion is keyframed.

Change:
- Added an explicit `--franka_render_mode` switch and made
  `static_urdf_obj_meshes` the default path again.
- The Slurm wrapper now passes `FRANKA_RENDER_MODE`, defaulting to the static
  GraspGenX/cuRobo URDF OBJ mesh renderer.
- Lowered the cube-motion overview camera to a robot-side view so the Franka
  and cube are visible together.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- code_commit: `8aefc9b3a4b7f6cde05209ebcf27ade4c246527f`
- changed_files:
  `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`

Command / Job:
- checks:
  - `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `bash -n cluster/sbatch_render_star_kitting_env.sh`
  - `git diff --check -- dextrah_lab/scene_scripts/render_star_kitting_env.py cluster/sbatch_render_star_kitting_env.sh`
- first render job: `1019806`, run
  `franka_cube_motion_static_20260609_220225`; completed with static Franka,
  but the starting cube was partly hidden by the hand from the chosen view.
- final render job: `1019813`, run
  `franka_cube_motion_static_visible_20260609_220409`.
- final command delta: same render settings as the first run, plus
  `CUBE_START_Y=-0.12` to keep the cube visible from the robot-side camera.

Result:
- final_remote_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/franka_cube_motion/franka_cube_motion_static_visible_20260609_220409`
- final_local_dir:
  `cluster_results/l401/franka_cube_motion_static_visible_20260609_220409`
- artifacts:
  - `overview.mp4`
  - `contact_sheet.png`
  - `franka_cube_motion_env.usda`
  - `scene_metadata.json`
  - `trajectory.json`
- video probe: `640x360`, `60` frames, `12 fps`, `5.0 s`.
- metadata check: `render_mode=static_urdf_obj_meshes`,
  `franka_is_static=True`, `franka_is_articulation=False`,
  `cube_moves=True`, `trajectory_frames=60`.

Analysis:
- The final contact sheet shows the blue cube visible in the first, middle,
  and last frames while the Franka remains fixed.

## 2026-06-09 22:24 PDT - Actuated Franka Single-Cube Motion Setup

Goal:
- Render the single-cube scene with the Franka spawned as the Isaac Lab
  articulation and commanded through actuators while the cube disturbance
  motion remains visible.

Hypothesis:
- The existing `articulation_usd` Franka path can be reused for cube-motion if
  the capture loop writes time-varying joint targets instead of always holding
  the default GraspGenX joint pose.

Change:
- Added `--franka_motion {hold,all_directions}` and
  `--franka_motion_scale`.
- `all_directions` commands a deterministic joint-space sweep through the
  Franka actuators, intended to move the hand laterally, vertically, and
  forward/back in the camera view.
- Cube-motion now writes `robot_motion_trajectory.json` with commanded joint
  targets and sampled end-effector body poses.
- The Slurm wrapper now forwards `FRANKA_MOTION` and
  `FRANKA_MOTION_SCALE`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `0d1172dff0bb252b18e708b72df63f7cdfceda1b`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`, `WORKLOG.md`

Command / Job:
- checks:
  - `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `bash -n cluster/sbatch_render_star_kitting_env.sh`
  - `git diff --check -- dextrah_lab/scene_scripts/render_star_kitting_env.py cluster/sbatch_render_star_kitting_env.sh`
- planned launch:
  `SCENE=cube_motion FRANKA_RENDER_MODE=articulation_usd FRANKA_MOTION=all_directions FRANKA_MOTION_SCALE=1.0 CUBE_START_Y=-0.12 WIDTH=640 HEIGHT=360 FPS=12 VIDEO_SECONDS=6.0 SIM_STEPS_PER_FRAME=5 CAPTURE_VIDEO=1 PHYSICS_DEVICE=cuda:0 sbatch --export=ALL cluster/sbatch_render_star_kitting_env.sh`

Result:
- status: implementation ready for commit/push/sync and l401 render.

## 2026-06-09 22:27 PDT - Actuated Franka Single-Cube Motion Result

Goal:
- Produce the requested single-cube video with the Franka as an actual Isaac
  Lab articulation and with actuator-commanded motion in all directions.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `066c34df62ad403dbc4ed6d698e89af216e277a2`
- remote_commit: `066c34df62ad403dbc4ed6d698e89af216e277a2`
- push/pull: pushed to origin and synced to l401 with
  `REMOTE=l401 ./cluster/sync_to_a1001.sh`.

Command / Job:
- command:
  `SCENE=cube_motion RUN_NAME=franka_cube_motion_actuated_all_dirs_20260609_222457 WIDTH=640 HEIGHT=360 FPS=12 VIDEO_SECONDS=6.0 SIM_STEPS_PER_FRAME=5 CAPTURE_VIDEO=1 PHYSICS_DEVICE=cuda:0 FRANKA_RENDER_MODE=articulation_usd FRANKA_MOTION=all_directions FRANKA_MOTION_SCALE=1.0 CUBE_START_Y=-0.12 sbatch --export=ALL cluster/sbatch_render_star_kitting_env.sh`
- job_id: `1019914`
- node: `pool0-00019`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/star_kitting_1019914.out`
- remote_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/franka_cube_motion/franka_cube_motion_actuated_all_dirs_20260609_222457`
- local_dir:
  `cluster_results/l401/franka_cube_motion_actuated_all_dirs_20260609_222457`

Result:
- status: passed
- Slurm: `COMPLETED`, exit `0:0`, elapsed `00:01:01`.
- artifacts:
  - `overview.mp4`
  - `contact_sheet.png`
  - `franka_cube_motion_env.usda`
  - `scene_metadata.json`
  - `trajectory.json`
  - `robot_motion_trajectory.json`
- video probe: `640x360`, `72` frames, `12 fps`, `6.0 s`.
- metadata check: `render_mode=articulation_usd`,
  `franka_is_articulation=True`, `franka_motion_commanded=True`,
  `motion=all_directions`, `cube_trajectory_frames=72`,
  `robot_motion_frames=72`.
- end-effector range from `robot_motion_trajectory.json`:
  `x=0.131 m`, `y=0.329 m`, `z=0.259 m`.
- visual check: contact sheet shows the articulated Franka sweeping around the
  table while the blue cube remains visible.

Analysis:
- This run satisfies the revised request: the single-cube experiment uses the
  actuated Franka path instead of static URDF meshes, commands actuator targets
  throughout the capture, and produces a video with visible motion in all three
  Cartesian axes.

## 2026-06-09 22:38 PDT - Franka Height and Cube PPO Launch Prep

Goal:
- Raise the GraspGenX Franka base by 0.2 m in the star-kitting/cube-motion
  render script.
- Launch a state-based PPO training run for `Dextrah-Cube-Grasp` on one
  8-GPU node.

Change:
- Added `--franka_base_z_offset` with default `0.2` and persisted the source
  and raised base poses in render metadata.
- Forwarded `FRANKA_BASE_Z_OFFSET` through
  `cluster/sbatch_render_star_kitting_env.sh`.
- Updated the cube PPO profile for the single-cube grasp/lift task:
  `num_envs=4096`, `horizon_length=32`, `minibatch_size=32768`,
  `mini_epochs=4`, `learning_rate=2e-4`, `central_value_lr=1e-4`,
  `gamma=0.995`, `tau=0.95`, `kl_threshold=0.012`,
  `entropy_coef=5e-4`, `e_clip=0.2`, `grad_norm=1.0`.

Command / Job:
- planned launch:
  `TASK=Dextrah-Cube-Grasp NUM_ENVS=4096 MAX_ITERATIONS=6000 DISTRIBUTED=True MULTI_GPU=True USE_CUDA_GRAPH=True sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh`

Result:
- status: validation and launch pending.

## 2026-06-09 22:44 PDT - Cube PPO Launch Failure and Import Fix

Command / Job:
- failed job_id: `28927696`
- run_name: `cube_grasp_ppo_opt8gpu_20260609_224029`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28927696.out`

Result:
- status: failed before training.
- failure:
  `AttributeError: type object 'DextrahKukaAllegroEnvCfg' has no attribute 'adr_custom_cfg_dict'`
  while importing `DextrahCubeGraspEnvCfg`.

Fix:
- Replaced class-body `copy.deepcopy(DextrahKukaAllegroEnvCfg.adr_custom_cfg_dict)`
  with a self-contained cube ADR custom config helper. This preserves the
  single-cube 8 cm XY spawn randomization and avoids relying on a base
  `@configclass` field as a class attribute.

Checks:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env_cfg.py dextrah_lab/scene_scripts/render_star_kitting_env.py`
- `bash -n cluster/sbatch_render_star_kitting_env.sh cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

## 2026-06-09 22:49 PDT - Cube PPO Relaunch Running

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `a9a8a75aea268254f19314f44a95a8fc28b79566`
- import_fix_commit: `55f3484689dfd71815205187fb3d17f0287f2269`
- remote_commit: `55f3484689dfd71815205187fb3d17f0287f2269`
- push/sync: pushed to origin and synced to `a1001`.

Command / Job:
- command:
  `TASK=Dextrah-Cube-Grasp FULL_EXPERIMENT_NAME=cube_grasp_ppo_opt8gpu_20260609_224426 AUTO_RESUME=True SELF_RELAUNCH=True NUM_ENVS=4096 MAX_ITERATIONS=6000 DISTRIBUTED=True MULTI_GPU=True USE_CUDA_GRAPH=True LEARNING_RATE=0.0002 CENTRAL_VALUE_LEARNING_RATE=0.0001 HORIZON_LENGTH=32 MINIBATCH_SIZE=32768 CENTRAL_VALUE_MINIBATCH_SIZE=32768 MINI_EPOCHS=4 GAMMA=0.995 TAU=0.95 KL_THRESHOLD=0.012 ENTROPY_COEF=0.0005 E_CLIP=0.2 GRAD_NORM=1.0 SAVE_FREQUENCY=25 sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `28927711`
- node: `batch-block7-01395`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28927711.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426`

Result:
- status: running after startup checks.
- Slurm at `00:05:12`: `RUNNING`, exit `0:0`.
- Verified `params/agent.yaml` values:
  `learning_rate=0.0002`, `central_value_learning_rate=0.0001`,
  `horizon_length=32`, `minibatch_size=32768`,
  `central_value_minibatch_size=32768`, `mini_epochs=4`,
  `gamma=0.995`, `tau=0.95`, `kl_threshold=0.012`,
  `entropy_coef=0.0005`, `save_frequency=25`.
- Verified `params/env.yaml` values:
  `num_envs=4096`, `enable_adr=false`,
  `object_spawn.x_width_spawn=[0.08, 0.08]`,
  `object_spawn.y_width_spawn=[0.08, 0.08]`.
- Startup log shows all 8 ranks parsing `DextrahCubeGraspEnvCfg`, writing
  params, creating 4096-env scenes, and starting simulation. No traceback or
  runtime-error patterns were present in the checked log tail.

## 2026-06-09 23:16 PDT - Cube PPO Monitoring Checkpoint

Command / Job:
- job_id: `28927711`
- run_name: `cube_grasp_ppo_opt8gpu_20260609_224426`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28927711.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426`

Result:
- status: running cleanly.
- Slurm at `00:30:42`: `RUNNING`, exit `0:0`, node
  `batch-block7-01395`.
- Latest observed progress:
  `epoch=205/6000`, `frames=213909504`, total FPS around `150k`.
- Checkpoints observed:
  - `last_dextrah_cube_grasp_ep_25_rew_528.4545.pth`
  - `last_dextrah_cube_grasp_ep_50_rew_399.92648.pth`
  - `last_dextrah_cube_grasp_ep_75_rew_1046.7179.pth`
  - `last_dextrah_cube_grasp_ep_100_rew_1264.9803.pth`
  - `last_dextrah_cube_grasp_ep_125_rew_1410.1632.pth`
  - `last_dextrah_cube_grasp_ep_150_rew_1459.2155.pth`
  - `last_dextrah_cube_grasp_ep_175_rew_1444.1439.pth`
  - `last_dextrah_cube_grasp_ep_200_rew_1473.8158.pth`
- Error-pattern count from the monitor grep: `0`.

Analysis:
- Training is past startup and producing checkpoints/events/resume sidecars.
- Reward is non-monotonic early on but generally improving from epoch 75
  through epoch 200. Continue monitoring for plateau/divergence and for
  wall-time requeue behavior.

## 2026-06-10 00:00 PDT - Cube PPO Metrics Eval Launch Prep

Goal:
- Launch a separate one-GPU evaluation job for the running cube-grasp PPO
  checkpoint without interrupting training job `28927711`.

Change:
- Added `cluster/sbatch_eval_cube_grasp.sh`, a one-GPU Pyxis wrapper around
  `dextrah_lab/rl_games/play.py`.
- The wrapper runs `Dextrah-Cube-Grasp` with a supplied checkpoint and small
  `NUM_ENVS`, writes stdout to both the Slurm log and
  `/results/eval/cube_grasp/<RUN_NAME>/eval_stdout.txt`.

Command / Job:
- planned checkpoint:
  `/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426/nn/last_dextrah_cube_grasp_ep_550_rew_1600.1677.pth`
- planned command:
  `TASK=Dextrah-Cube-Grasp NUM_ENVS=16 RUN_NAME=<eval_run> CHECKPOINT=<checkpoint> sbatch --export=ALL cluster/sbatch_eval_cube_grasp.sh`

Result:
- status: validation and launch pending.
- note: this is metrics-only; `play.py` does not record rollout video.

## 2026-06-09 23:50 PDT - Cube Grasp Eval Video Path

Goal:
- Launch a separate one-GPU evaluation/rollout visualization for the active
  cube grasp PPO training run without modifying or canceling training job
  `28927711`.

Hypothesis:
- The existing `play.py` is metrics-only, while `train.py` already proves the
  project can use Gym `RecordVideo`; a narrow eval script plus a one-GPU Slurm
  wrapper should produce a rollout video and metrics without touching the
  8-GPU training wrapper.

Change:
- Added `dextrah_lab/rl_games/eval_rollout.py` for checkpoint playback with
  optional video capture, step metrics, and `metrics.json` output.
- Added `cluster/sbatch_eval_cube_grasp_1gpu.sh` for a one-GPU cube grasp eval
  using the existing Isaac Lab container, DEXTRAH env, cache mounts, and results
  path.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `f651a4a3af63c7b3f94fe32b8ded406e0fc10f56`
- implementation_commit: pending
- changed_files: `dextrah_lab/rl_games/eval_rollout.py`,
  `cluster/sbatch_eval_cube_grasp_1gpu.sh`, `WORKLOG.md`

Command / Job:
- command: pending validation, commit, push, remote pull, and `sbatch`
- job_id: pending
- run_dir: pending
- logs: pending
- artifacts: rollout video under `/results/evals/<run>/videos` and
  `/results/evals/<run>/metrics.json`

Result:
- status: in progress

Next:
- Validate syntax, commit/push, sync a1001, select the newest usable cube grasp
  checkpoint, submit the one-GPU eval, and monitor startup logs.

## 2026-06-10 00:03 PDT - Cube Grasp Metrics Eval Retry

Goal:
- Launch a minimal metrics-only one-GPU eval immediately using `play.py`, with
  no video work on the critical path.

Change:
- Added `cluster/sbatch_play_cube_grasp_metrics_1gpu.sh`, a minimal one-GPU
  Pyxis wrapper that runs `dextrah_lab/rl_games/play.py` and tees stdout to the
  eval output directory.
- Fixed `play.py` success-rate logging to read from the unwrapped task env
  instead of Gym's `OrderEnforcing` wrapper.
- Added an error-pattern guard to the metrics wrapper.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `8a8c8a12323e213529347b59cb328ee4dfcf0ca0`
- remote_commit: `8a8c8a12323e213529347b59cb328ee4dfcf0ca0`
- changed_files: `cluster/sbatch_play_cube_grasp_metrics_1gpu.sh`,
  `dextrah_lab/rl_games/play.py`

Command / Job:
- failed video attempt: `28929268`, log
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_28929268.out`
- failed metrics attempt: `28929325`, log
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/metrics_cube_grasp_28929325.out`
- retry command:
  `RUN_NAME=cube_grasp_metrics_ep500_retry_20260610_000249 CHECKPOINT=/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426/nn/last_dextrah_cube_grasp_ep_500_rew_1595.4742.pth NUM_ENVS=16 sbatch --export=ALL cluster/sbatch_play_cube_grasp_metrics_1gpu.sh`
- job_id: `28929372`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_ep500_retry_20260610_000249`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/metrics_cube_grasp_28929372.out`
- artifacts:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_ep500_retry_20260610_000249/play_stdout.log`

Result:
- status: submitted, pending resources at first check.
- checkpoint used:
  `last_dextrah_cube_grasp_ep_500_rew_1595.4742.pth`

Next:
- Poll job `28929372` for allocation and first `count ... sr:` metric lines.

## 2026-06-10 00:09 PDT - Cube Grasp Metrics Eval Results

Goal:
- Confirm whether the high shaped checkpoint rewards correspond to the actual
  cube-grasp success predicate.

Command / Job:
- worker metrics eval:
  - job_id: `28929372`
  - checkpoint:
    `last_dextrah_cube_grasp_ep_500_rew_1595.4742.pth`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/metrics_cube_grasp_28929372.out`
  - run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_ep500_retry_20260610_000249`
- comparison metrics eval:
  - job_id: `28929393`
  - checkpoint:
    `last_dextrah_cube_grasp_ep_600_rew_1606.0074.pth`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/metrics_cube_grasp_28929393.out`
  - run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_20260610_000324`

Result:
- status: both completed successfully.
- `28929372`: `COMPLETED`, exit `0:0`, `final sr: tensor(0., device='cuda:0')`.
- `28929393`: `COMPLETED`, exit `0:0`, `final sr: tensor(0., device='cuda:0')`.
- Both jobs printed `sr=0` through the end of the 5000-step rollout.
- No traceback/runtime/error guard patterns were observed.

Analysis:
- The current checkpoints are improving dense shaped reward but do not satisfy
  the task success predicate in metrics eval.
- This matches the TensorBoard scalar inspection: `cube_success_rate=0`,
  `cube_success_bonus=0`, and mean lift height remains near zero while approach,
  enclosure, and XY-stability reward terms dominate.
- The rollout-video path exists in `dextrah_lab/rl_games/eval_rollout.py` and
  `cluster/sbatch_eval_cube_grasp_1gpu.sh`, but the urgent completed evals were
  metrics-only.

## 2026-06-10 00:18 PDT - Cube Grasp Video Eval Relaunch Fix

Goal:
- Produce a rendered rollout video for the cube grasp checkpoint eval.

Hypothesis:
- The previous video eval failed before rollout because
  `git status --short` inside the Isaac container invoked Git LFS, but the
  container does not provide `git-lfs`. Removing that fatal diagnostic should
  let `eval_rollout.py` reach the environment and write video artifacts.

Change:
- Made the video eval wrapper tolerate `git rev-parse` failure and skip
  in-container `git status`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `f055fd169d5d6a5d2e896150b9d8f29fed92ff5f`
- implementation_commit: `9563f6d197cb4ae967b188e06b37ff60959284f7`
- changed_files: `cluster/sbatch_eval_cube_grasp_1gpu.sh`, `WORKLOG.md`
- push/pull: pushed to origin and pulled on a1001
- remote_commit/status:
  `9563f6d197cb4ae967b188e06b37ff60959284f7`, clean

Command / Job:
- failed prior video job: `28929268`
- failed prior log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_28929268.out`
- failed prior result: no `.mp4`, `.png`, or `metrics.json` artifacts were
  produced under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals`.
- relaunch command:
  `RUN_NAME=cube_grasp_eval_ep725_video_20260610_002001 CHECKPOINT=/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426/nn/last_dextrah_cube_grasp_ep_725_rew_1603.1135.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 CAPTURE_VIDEO=True USE_CUDA_GRAPH=False PRINT_INTERVAL=20 sbatch --export=ALL cluster/sbatch_eval_cube_grasp_1gpu.sh`
- job_id: `28929700`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_eval_ep725_video_20260610_002001`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_28929700.out`
- artifacts:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_eval_ep725_video_20260610_002001/metrics.json`
  and MP4 files under
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_eval_ep725_video_20260610_002001/videos/`

Result:
- status: completed.
- Slurm state: `COMPLETED`, elapsed `00:03:43`, exit `0:0`.
- metrics:
  - `num_steps_completed=600`
  - `success_rate_final=0.0`
  - `success_rate_mean=0.0`
  - `reward_mean=2.684174687465032`
  - `reward_final=1.0055654048919678`
- video:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_eval_ep725_video_20260610_002001/videos/cube-grasp-eval-step-0.mp4`
- local copy:
  `cluster_results/a1001/cube_grasp_eval_ep725_video_20260610_002001/videos/cube-grasp-eval-step-0.mp4`
- validation:
  `ffprobe` on the local copy reports `1280x720`, `600` frames, `10.0s`,
  `60 FPS`; middle/final preview frames are nonblank and show four vectorized
  single-cube env replicas.

Next:
- Continue monitoring the PPO training job. The rendered eval confirms current
  checkpoint behavior: the arm moves, but it does not lift the cube and the
  success predicate remains zero.

## 2026-06-10 00:31 PDT - Static Cube Bug Fix

Goal:
- Stop the cube from moving itself in the single-cube task and render path.

Hypothesis:
- The old `cube_motion` visualization path was still keyframing the cube each
  frame. That was only meant for an early visualization and should not be the
  default behavior for the actual single-cube experiment. The cube-grasp RL env
  should also explicitly reject inherited object wrench disturbances.

Change:
- Added a `single_cube` scene alias and made cube animation opt-in with
  `--animate_cube`.
- Updated the star-kitting render wrapper so `SCENE=single_cube` and legacy
  `SCENE=cube_motion` default to a static cube; `ANIMATE_CUBE=true` is required
  for the old keyframed disturbance.
- Overrode `DextrahCubeGraspEnv.apply_object_wrench()` to zero force/torque
  buffers and disable inherited object disturbances for this focused task.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `975abfbc5c1e2efb655528af74c5beb8cc473081`
- implementation_commit: `3414dd623c67d33425ce74a5e55f6a78f1ec7c09`
- push/pull: pushed to origin and pulled on a1001
- changed_files:
  `dextrah_lab/scene_scripts/render_star_kitting_env.py`,
  `cluster/sbatch_render_star_kitting_env.sh`,
  `dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env.py`,
  `WORKLOG.md`
- remote_commit/status:
  `3414dd623c67d33425ce74a5e55f6a78f1ec7c09`, clean

Command / Job:
- local checks:
  `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py dextrah_lab/tasks/dextrah_kuka_allegro/dextrah_cube_grasp_env.py`
- local checks:
  `bash -n cluster/sbatch_render_star_kitting_env.sh`
- local checks:
  `git diff --check`

Result:
- status: checks passed locally; fix committed, pushed, and deployed to the
  shared cluster checkout.
- key evidence: remote grep confirms `single_cube`, `--animate_cube`,
  `cube_moves: animate_cube`, and `DextrahCubeGraspEnv.apply_object_wrench`.

Next:
- Relaunch any future single-cube render/eval jobs from commit `3414dd6` or
  newer so the cube remains static unless `ANIMATE_CUBE=true` is explicitly set.

## 2026-06-10 00:43 PDT - Static Cube PPO Relaunch

Goal:
- Cancel the cube-grasp PPO run trained/evaluated before the static-cube fix,
  remove its artifacts, and relaunch PPO from corrected code.

Hypothesis:
- The pre-fix run is invalid because the cube task/render path allowed
  visualization-only cube motion and inherited object wrench disturbances.
  Starting from commit `34744ab` with a fresh run name prevents resume from the
  bad checkpoint tree.

Change:
- Canceled only cube-grasp job `28927711`.
- Left unrelated `Dextrah-Kuka-Allegro` job `28910978` running.
- Removed the old cube-grasp training directory, eval directories, and old
  cube-grasp Slurm logs.
- Submitted a new 8-GPU PPO job from the corrected a1001 checkout.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- implementation_commit: `34744ab97709adbff2da7cf8b749960bfcce1037`
- remote_commit/status:
  `34744ab97709adbff2da7cf8b749960bfcce1037`, clean

Command / Job:
- canceled job: `28927711`
- bad run_dir removed:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_cube_grasp/cube_grasp_ppo_opt8gpu_20260609_224426`
- bad eval dirs removed:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_eval_ep725_video_20260610_002001`,
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_20260610_000324`,
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_ep500_retry_20260610_000249`,
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_metrics_ep500_20260609_235902`
- bad local eval copy removed:
  `cluster_results/a1001/cube_grasp_eval_ep725_video_20260610_002001`
- relaunch command:
  `TASK=Dextrah-Cube-Grasp FULL_EXPERIMENT_NAME=cube_grasp_static_ppo_opt8gpu_20260610_004351 MAX_ITERATIONS=6000 USE_CUDA_GRAPH=True AUTO_RESUME=True SELF_RELAUNCH=True sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh`
- new job_id: `28930031`
- new run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_cube_grasp/cube_grasp_static_ppo_opt8gpu_20260610_004351`
- new log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28930031.out`

Result:
- status: submitted and running on `batch-block7-01550`.
- cleanup verification:
  bad training dir, bad eval video dir, and bad training log are absent.
- startup verification:
  - reached PPO training output by epoch `3/6000`
  - reached epoch `51/6000` by the follow-up check
  - saved checkpoints:
    `last_dextrah_cube_grasp_ep_25_rew_544.2628.pth`,
    `last_dextrah_cube_grasp_ep_50_rew_661.8385.pth`

Next:
- Continue monitoring job `28930031`; the corrected run is past startup and
  checkpointing normally.

## 2026-06-10 00:58 PDT - Static Cube Reward Monitor And Eval Video

Goal:
- Monitor the corrected PPO reward, automatically launch checkpoint eval, and
  save a rollout video.

Hypothesis:
- The epoch-75 checkpoint should be a better eval target than epoch 50 because
  the checkpoint reward jumped from `661.8385` to `994.8821`.

Command / Job:
- training job monitored: `28930031`
- training run:
  `cube_grasp_static_ppo_opt8gpu_20260610_004351`
- checkpoint selected:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_cube_grasp/cube_grasp_static_ppo_opt8gpu_20260610_004351/nn/last_dextrah_cube_grasp_ep_75_rew_994.8821.pth`
- eval command:
  `RUN_NAME=cube_grasp_static_eval_ep75_video_20260610_005847 CHECKPOINT=/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_static_ppo_opt8gpu_20260610_004351/nn/last_dextrah_cube_grasp_ep_75_rew_994.8821.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 CAPTURE_VIDEO=True USE_CUDA_GRAPH=False PRINT_INTERVAL=20 sbatch --export=ALL cluster/sbatch_eval_cube_grasp_1gpu.sh`
- eval job_id: `28930260`
- eval run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_static_eval_ep75_video_20260610_005847`
- eval log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_28930260.out`

Result:
- status: eval completed successfully.
- Slurm state: `COMPLETED`, elapsed `00:02:28`, exit `0:0`.
- reward/checkpoint monitor:
  - latest before eval: `last_dextrah_cube_grasp_ep_50_rew_661.8385.pth`
  - selected eval checkpoint: `last_dextrah_cube_grasp_ep_75_rew_994.8821.pth`
- metrics:
  - `num_steps_completed=600`
  - `reward_mean=1.7456187343597411`
  - `reward_final=1.0087100267410278`
  - `success_rate_mean=0.0`
  - `success_rate_final=0.0`
  - `max_cube_lift_height=0.014073193073272705`
- video:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_static_eval_ep75_video_20260610_005847/videos/cube-grasp-eval-step-0.mp4`
- local copy:
  `cluster_results/a1001/cube_grasp_static_eval_ep75_video_20260610_005847/videos/cube-grasp-eval-step-0.mp4`
- validation:
  `ffprobe` reports `1280x720`, `600` frames, `10.0s`, `60 FPS`; middle and
  final preview frames are nonblank and show the static single-cube envs.

Next:
- Continue monitoring reward/checkpoints. Current eval shows early shaped
  reward progress and small cube lift, but no task success yet.

## 2026-06-10 01:17 PDT - Franka Star-Kitting RL Environment Gate

Goal:
- Add a Franka RL task for picking a star-shaped object and placing it into a
  matching star fixture, with an explicit validation gate before any training
  or checkpoint eval is launched.

Hypothesis:
- The stable cube-grasp RL-Games infrastructure can be reused, but the
  environment must be a new Franka DirectRLEnv rather than a Kuka-Allegro
  subclass because the existing task is tied to FABRICS and Allegro hand PCA
  control.

Change:
- Added a new `Dextrah-Franka-Star-Kitting` task package with procedural
  star/fixture geometry, reward terms, env config, Gym registration, and a
  state-based RL-Games PPO config.
- Added `validate_franka_star_kitting_env.py` and a one-GPU Slurm wrapper that
  must pass before training: geometry checks, reward monotonicity checks,
  success-predicate pose checks, and a short scripted no-learning rollout with
  optional video.
- Updated RL-Games train/play imports and added a task-specific training
  hyperparameter branch, but did not launch training.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `725d2533e7f4fd0cf88f4109fcf1ccc8d96a07eb`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/tasks/dextrah_franka_star_kitting/*`,
  `dextrah_lab/rl_games/validate_franka_star_kitting_env.py`,
  `dextrah_lab/rl_games/train.py`,
  `dextrah_lab/rl_games/play.py`,
  `cluster/sbatch_validate_franka_star_kitting_env_1gpu.sh`,
  `cluster/sbatch_train_teacher_8gpu.sh`,
  `WORKLOG.md`

Command / Job:
- local checks:
  `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_star_kitting/star_kitting_geometry.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_rewards.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env.py dextrah_lab/tasks/dextrah_franka_star_kitting/gym_setup.py dextrah_lab/rl_games/validate_franka_star_kitting_env.py dextrah_lab/rl_games/eval_rollout.py dextrah_lab/rl_games/train.py dextrah_lab/rl_games/play.py`
- local checks:
  `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_star_kitting_env_1gpu.sh cluster/sbatch_eval_cube_grasp_1gpu.sh`
- local checks:
  `ruby -e "require 'yaml'; YAML.load_file('dextrah_lab/tasks/dextrah_franka_star_kitting/agents/rl_games_ppo_franka_star_kitting_cfg.yaml'); puts 'yaml ok'"`
- local checks: `git diff --check`

Result:
- status: implementation checks passed locally; runtime validation not yet
  launched.
- key evidence: local syntax, shell syntax, YAML parsing, and whitespace checks
  passed. Local runtime import is not expected because this workstation does
  not provide the Isaac Lab/torch environment used by the cluster container.

Analysis:
- The training/eval loop is intentionally gated. Launching PPO before the
  validation wrapper confirms geometry, reset, reward, success, and rollout
  behavior would violate the current task requirement.

Next:
- Commit/push/pull this implementation, run
  `cluster/sbatch_validate_franka_star_kitting_env_1gpu.sh`, inspect metrics
  and video, and only then consider smoke training.

## 2026-06-10 01:14 PDT - Overhead Eval Camera

Goal:
- Keep the corrected cube PPO training running and make future eval videos use
  a closer overhead table-centered view.

Hypothesis:
- The eval rollout already shares the training task and checkpoint; only the
  viewport camera needs to be overridden for clearer video inspection.

Change:
- Added `--camera_eye` and `--camera_target` to
  `dextrah_lab/rl_games/eval_rollout.py`.
- Updated `cluster/sbatch_eval_cube_grasp_1gpu.sh` to pass a default overhead
  camera centered at `(-0.55, 0.10, 0.25)` with eye `(-0.55, 0.10, 1.45)`.
- Set the default eval video prefix to `cube-grasp-eval-overhead`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `725d2533e7f4fd0cf88f4109fcf1ccc8d96a07eb`
- implementation_commit: `6d7fac5476a8b45c39e09b00e95e86f537ccf6ef`
- changed_files:
  `dextrah_lab/rl_games/eval_rollout.py`,
  `cluster/sbatch_eval_cube_grasp_1gpu.sh`, `WORKLOG.md`

Command / Job:
- local checks:
  `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`
- local checks:
  `bash -n cluster/sbatch_eval_cube_grasp_1gpu.sh`

Result:
- status: local checks passed.
- training job `28930031` remained running and reached at least epoch `205/6000`,
  with latest best reward checkpoint `dextrah_cube_grasp.pth` at reward
  `1517.1261` and periodic checkpoint
  `last_dextrah_cube_grasp_ep_200_rew_1493.3677.pth`.

Next:
- Commit and deploy the camera patch to `a1001`, then launch the next periodic
  eval from a fresh checkpoint with the overhead view.

## 2026-06-10 01:20 PDT - Overhead Eval Relaunch Fix

Goal:
- Relaunch the overhead eval without disrupting training.

Hypothesis:
- The failed eval job was caused by `eval_rollout.py` importing the local
  untracked Franka task package; the cube eval only needs the KUKA/Allegro task
  registration.

Change:
- Removed `dextrah_lab.tasks.dextrah_franka_star_kitting.gym_setup` from
  `dextrah_lab/rl_games/eval_rollout.py`.
- Removed failed eval output directory:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/cube_grasp_static_eval_ep225_overhead_20260610_011653`.

Command / Job:
- failed eval job_id: `28930620`
- failed eval log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_cube_grasp_28930620.out`
- failed checkpoint:
  `/results/logs/rl_games/dextrah_cube_grasp/cube_grasp_static_ppo_opt8gpu_20260610_004351/nn/last_dextrah_cube_grasp_ep_225_rew_1474.1598.pth`
- local check:
  `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`

Result:
- status: failed eval classified and cleanup complete.
- key evidence: `ModuleNotFoundError: No module named
  'dextrah_lab.tasks.dextrah_franka_star_kitting'`.
- training job `28930031` remained running.

Next:
- Commit, push, update `a1001`, and relaunch the overhead eval from the same
  epoch-225 checkpoint.

## 2026-06-10 01:35 PDT - Franka Star Validation Gate Fix

Goal:
- Keep the Franka star kitting task behind a hard environment-validation gate
  before launching any training or eval.

Evidence:
- validation job_id: `28930645`
- run_name: `franka_star_env_validate_20260610_012007`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_star_28930645.out`
- remote results:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_star_env_validate_20260610_012007`
- local results:
  `cluster_results/a1001/franka_star_env_validate_20260610_012007`
- video:
  `cluster_results/a1001/franka_star_env_validate_20260610_012007/videos/franka-star-kitting-validation-step-0.mp4`

Result:
- status: validation failed, so training/eval remains blocked.
- passed checks: procedural geometry fit, reset observation shape/finite values,
  reward monotonicity, and success/failure predicates.
- failed check: scripted rollout did not approach the star closely enough
  (`min_ee_to_star=0.16175222396850586`), and no lift occurred.
- wrapper bug: validation wrote `passed: false` but exited zero after
  `env.close()`, so Slurm reported success incorrectly.

Change:
- Moved the default pickup and fixture sites closer to the reachable Franka
  work area.
- Increased IK action scales and made the scripted validation command a
  top-down Panda hand orientation while approaching the target positions.
- Tightened the scripted approach check to require both absolute proximity and
  improvement from the initial end-effector/star distance.
- Made failed validation exit nonzero after closing the environment.
- Extended default validation rollout/video length from 180 to 300 steps.

Checks:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_star_kitting/star_kitting_geometry.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_rewards.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env.py dextrah_lab/tasks/dextrah_franka_star_kitting/gym_setup.py dextrah_lab/rl_games/validate_franka_star_kitting_env.py dextrah_lab/rl_games/train.py dextrah_lab/rl_games/play.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_validate_franka_star_kitting_env_1gpu.sh`
- `ruby -e "require 'yaml'; YAML.load_file('dextrah_lab/tasks/dextrah_franka_star_kitting/agents/rl_games_ppo_franka_star_kitting_cfg.yaml'); puts 'yaml ok'"`
- `git diff --check`

Next:
- Commit/push, update the `a1001` checkout, rerun validation, and continue
  fixing until the environment and video inspection are correct.
