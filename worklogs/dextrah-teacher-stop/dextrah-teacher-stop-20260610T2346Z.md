# Worklog - dextrah-teacher-stop / dextrah-teacher-stop-20260610T2346Z

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z
- branch: codex/dextrah-teacher-stop/dextrah-teacher-stop-20260610T2346Z
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- created: 2026-06-10T23:47:13Z

## 2026-06-10 16:50 PDT - Held Requeue For Teacher Job 28942245

Goal:
- Temporarily stop DEXTRAH teacher job `28942245` without letting the
  self-relaunch wrapper immediately consume another allocation.

Version Control:
- agent_id: `dextrah-teacher-stop-20260610T2346Z`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`
- worklog:
  `worklogs/dextrah-teacher-stop/dextrah-teacher-stop-20260610T2346Z.md`
- branch: `codex/dextrah-teacher-stop/dextrah-teacher-stop-20260610T2346Z`
- base_commit: `b684a9649e046124119bf4b965007f5bad2477ba`
- shared checkout: `/home/lzha/code/DEXTRAH` left dirty and not pulled after
  reading the updated multi-agent isolation guidance.

Command / Job:
- command: `ssh a1001 'scontrol requeuehold 28942245'`
- job_id: `28942245`
- run_name: `teacher_short_20260609_100021`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28942245.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: stopped temporarily.
- scheduler: `PENDING`, reason `(job requeued in held state)`, no node
  assigned, elapsed `0:00`.
- wrapper log confirms `Requeuing DEXTRAH job 28942245 for run
  teacher_short_20260609_100021 after TERM`.
- final log tail reached epoch `13491/20000`; artifact listing shows latest
  checkpoint `last_dextrah_lstm_ep_13500_rew_577.9305.pth`.
- runtime sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `16:46`.

Analysis:
- `scontrol requeuehold` achieved the requested temporary stop while preserving
  resumability. The job is held pending rather than running, queued for
  immediate dispatch, restoring, or consuming GPUs.
- Updated skill guidance requires future code edits and launches to use
  agent-owned worktrees, branches, worklogs, run namespaces, and remote
  worktrees. The shared checkout should not be pulled, switched, or used for
  new parallel launches while other workers may be active.

Next:
- To resume intentionally, release the held job with `scontrol release
  28942245` from `a1001`, then verify it restores from
  `last_dextrah_lstm_ep_13500_rew_577.9305.pth` and the rank runtime
  sidecars.

## 2026-06-10 17:10 PDT - Isolated Teacher Resume Relaunch

Goal:
- Continue the teacher run while following the updated multi-agent isolation
  guidance.

Change:
- Pushed branch
  `codex/dextrah-teacher-stop/dextrah-teacher-stop-20260610T2346Z`.
- Created remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`.
- Submitted a replacement resume job from the remote worktree with
  `CODE_NFS` pointing to that same remote worktree.
- Canceled old held job `28942245` after replacement job `28955904` was
  confirmed running.

Version Control:
- agent_id: `dextrah-teacher-stop-20260610T2346Z`
- local_commit: `12c3119d4363922f352a79fc74827d5595121a66`
- remote_commit: `12c3119d4363922f352a79fc74827d5595121a66`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z FULL_EXPERIMENT_NAME=teacher_short_20260609_100021 AUTO_RESUME=True SELF_RELAUNCH=True TASK=Dextrah-Kuka-Allegro DISTRIBUTED=True MULTI_GPU=True sbatch --parsable cluster/sbatch_train_teacher_8gpu.sh`
- new_job_id: `28955904`
- old_job_id: `28942245`, canceled after new job was running.
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy after isolated resume.
- scheduler: `28955904` running on `batch-block5-03072`.
- log confirms `CODE_NFS` uses the agent-owned remote worktree.
- auto-resume loaded
  `last_dextrah_lstm_ep_13500_rew_577.9305.pth`.
- runtime state restored at epoch `13500`.
- post-resume training advanced to epoch `13520/20000`.
- new complete checkpoints:
  - `last_dextrah_lstm_ep_13510_rew_731.1301.pth`
  - `last_dextrah_lstm_ep_13520_rew_725.3122.pth`
- runtime sidecars rank `0` through `7` refreshed at `17:09`.

Analysis:
- The replacement job removes the shared-checkout resume risk from the held
  Slurm job. Future wall-time requeues of `28955904` should rerun the batch
  script from the agent-owned remote worktree and keep mounting that same path
  as `/code`.

Next:
- Continue active monitoring, parse TensorBoard once the new event file has
  flushed, and verify loss/reward/success/KL remain healthy after the
  isolated resume.

## 2026-06-10 17:11 PDT - Post-Resume Metric Check

Goal:
- Verify that the isolated resume is not just advancing stdout, but has healthy
  scalar metrics and no fresh failure signatures.

Command / Job:
- job_id: `28955904`
- metrics source:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/summaries`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`

Result:
- status: running healthy.
- TensorBoard parsed through epoch `13521`.
- `in_success_region/iter`: latest `0.471436`, last-50 `0.455444`,
  last-200 `0.451368`.
- `rewards/iter`: latest `671.356`, last-50 `632.381`,
  last-200 `623.643`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00744328`, last-50 `0.00966099`,
  last-200 `0.00953316`.
- `losses/a_loss`: last-50 `-0.00408088`.
- `losses/c_loss`: last-50 `0.0203441`.
- `performance/step_inference_rl_update_fps`: last-50 about `106459`.
- recent failure scan found no traceback, RuntimeError, CUDA error, OOM,
  ChildFailedError, or training-failure signature; only the NCCL version banner
  matched the broad NCCL pattern.

Analysis:
- The isolated resume is behaving like the previous healthy run: max ADR,
  success-region comfortably above `0.4`, stable KL/losses, normal throughput,
  and fresh checkpoints/sidecars.

Next:
- Continue active monitoring for checkpoint cadence, metric stability, and the
  next wall-time requeue window for job `28955904`.
