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
- implementation_commit: pending

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
- status: pending

Analysis:
- The current GraspGenX NFS venv has pyrender/trimesh/PIL but not Newton or
  Warp. The Slurm wrapper will install `newton[sim]` into
  `/envs/dextrah-newton-render-site` only when those imports are missing.

Next:
- Run syntax checks, commit/push, pull to l401, launch a low-resolution smoke,
  inspect frames/logs, then scale to the final requested video.
