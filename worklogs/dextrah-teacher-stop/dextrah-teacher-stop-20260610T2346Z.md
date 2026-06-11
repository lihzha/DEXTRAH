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

## 2026-06-10 17:50 PDT - Isolated Teacher Monitor Pass

Goal:
- Confirm the replacement job remains isolated, advancing, checkpointing, and
  numerically healthy after the resume from epoch `13500`.

Version Control:
- agent_id: `dextrah-teacher-stop-20260610T2346Z`
- branch: `codex/dextrah-teacher-stop/dextrah-teacher-stop-20260610T2346Z`
- local_worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`
- running_remote_commit: `12c3119d4363922f352a79fc74827d5595121a66`

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, `EndTime=2026-06-10T20:44:19`;
  expected TERM/relaunch window around `20:39:19 PDT`.
- `Command` and `WorkDir` still point at the agent-owned remote worktree.
- stdout advanced to epoch `14010/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14010_rew_567.0352.pth`.
- rank sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `17:48:52`.
- TensorBoard parsed through epoch `13989`.
- `in_success_region/iter`: latest `0.439209`, last-50 `0.448428`,
  last-200 `0.445414`.
- `rewards/iter`: latest `713.596`, last-50 `609.623`,
  last-200 `607.849`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00514335`, last-50 `0.00883904`,
  last-200 `0.00867971`.
- `losses/a_loss`: last-50 `-0.00405108`.
- `losses/c_loss`: last-50 `0.0156901`.
- `performance/step_inference_rl_update_fps`: last-50 about `110712`.

Analysis:
- Resume remains stable: checkpoints and sidecars are advancing on schedule,
  success-region is consistent with the prior healthy band, KL is controlled,
  and losses/throughput show no immediate instability. A broad `inf` error
  scan matched normal `inference` text, so later scans should use a narrower
  failure-signature pattern.

Next:
- Continue active monitoring with short one-shot SSH checks. Tighten polling
  before the `20:39 PDT` signal window and verify the next relaunch resumes
  from the newest checkpoint and rank runtime sidecars.

## 2026-06-10 18:09 PDT - Teacher Monitor SSH-Agent Workaround

Goal:
- Continue active monitoring after local SSH checks began stalling, without
  mutating shared source or leaving hung monitor processes behind.

Change:
- Killed four stuck local SSH monitor processes from the `18:02 PDT` poll.
- Diagnosed SSH with a bounded verbose trace; the connection reached userauth
  and then stalled at the local SSH agent socket.
- Switched monitor commands and rsync to explicit key auth:
  `IdentityAgent=none`, `IdentitiesOnly=yes`,
  `-i /home/lzha/.ssh/id_ed25519`, bounded by local `timeout`.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `2:36:18`.
- stdout advanced to epoch `14244/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14240_rew_597.21844.pth`.
- rank sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `18:07:37`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14235`.
- `in_success_region/iter`: latest `0.454834`, last-50 `0.44252`,
  last-200 `0.44916`.
- `rewards/iter`: latest `666.285`, last-50 `611.116`,
  last-200 `623.045`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00953345`, last-50 `0.00850648`,
  last-200 `0.00883697`.
- `losses/a_loss`: last-50 `-0.0043094`.
- `losses/c_loss`: last-50 `0.0206826`.
- `performance/step_inference_rl_update_fps`: last-50 about `109634`.

Analysis:
- The apparent monitor stall was local SSH-agent behavior, not evidence of a
  Slurm or training stall. Explicit key auth keeps future one-shot checks
  bounded and responsive.
- Training remains healthy: checkpoint cadence, sidecar cadence, success,
  reward, KL, losses, and throughput are all consistent with the prior
  post-resume band.

Next:
- Continue monitoring with explicit-key SSH/rsync commands. Tighten polling
  before the `20:39 PDT` TERM/requeue window.

## 2026-06-10 18:20 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued training health after the SSH monitor workaround and record
  the current checkpoint/metric state.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `2:23:53`.
- stdout advanced to epoch `14397/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14390_rew_709.83954.pth`.
- rank sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `18:19:47`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14383`.
- `in_success_region/iter`: latest `0.458984`, last-50 `0.454028`,
  last-200 `0.449281`.
- `rewards/iter`: latest `687.197`, last-50 `626.175`,
  last-200 `621.101`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00679376`, last-50 `0.00789`,
  last-200 `0.00829513`.
- `losses/a_loss`: last-50 `-0.00427106`.
- `losses/c_loss`: last-50 `0.01878`.
- `performance/step_inference_rl_update_fps`: last-50 about `110299`.

Analysis:
- Training remains stable and productive. Success-region and reward are in the
  same healthy band as before the temporary stop, KL remains controlled, value
  loss is not drifting upward, and checkpoint/sidecar cadence is intact.

Next:
- Continue periodic monitoring. Increase polling frequency as `20:39 PDT`
  approaches, then verify signal-triggered relaunch and resume from the newest
  checkpoint/runtime sidecars.

## 2026-06-10 18:32 PDT - Teacher Monitor Metric Pass

Goal:
- Verify the teacher run remains healthy as it progresses toward the next
  wall-time requeue window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `2:12:20`.
- stdout advanced to checkpoint epoch `14540/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14540_rew_629.14905.pth`.
- rank sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `18:31:55`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14531`.
- `in_success_region/iter`: latest `0.449951`, last-50 `0.444839`,
  last-200 `0.448263`.
- `rewards/iter`: latest `559.612`, last-50 `601.323`,
  last-200 `618.826`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00526183`, last-50 `0.00753725`,
  last-200 `0.00766392`.
- `losses/a_loss`: last-50 `-0.00409548`.
- `losses/c_loss`: last-50 `0.0157005`.
- `performance/step_inference_rl_update_fps`: last-50 about `110219`.

Analysis:
- No evidence of instability or stalled training. Reward last-50 is slightly
  below the previous monitor pass but still in the normal post-resume band;
  success-region, KL, losses, and throughput remain healthy.

Next:
- Continue periodic monitoring. Recheck metrics in roughly 10-15 minutes unless
  logs or scheduler state indicate a problem sooner.

## 2026-06-10 18:43 PDT - Teacher Monitor Metric Pass

Goal:
- Continue validating checkpoint cadence, sidecar freshness, and scalar health
  while the job remains well before the wall-time signal window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `2:00:51`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14680_rew_705.1611.pth`.
- rank sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` refreshed at `18:43:23-18:43:24`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14678`.
- `in_success_region/iter`: latest `0.452393`, last-50 `0.4473`,
  last-200 `0.447701`.
- `rewards/iter`: latest `628.279`, last-50 `628.08`,
  last-200 `622.474`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.0137938`, last-50 `0.00839118`,
  last-200 `0.00820649`.
- `losses/a_loss`: last-50 `-0.00411436`.
- `losses/c_loss`: last-50 `0.0190789`.
- `performance/step_inference_rl_update_fps`: last-50 about `110541`.

Analysis:
- Metrics remain in the healthy post-resume band. Latest KL is a bit above the
  last-50 mean but still not an instability signal; rolling KL, reward,
  success, losses, throughput, checkpoints, and sidecars all look normal.

Next:
- Continue periodic monitoring with another scalar pass in roughly 10-15
  minutes, then tighten polling closer to the `20:39 PDT` signal window.

## 2026-06-10 18:55 PDT - Teacher Monitor Metric Pass

Goal:
- Keep the teacher run supervised and verify metrics remain stable as the job
  passes two hours of runtime in the isolated allocation.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `1:49:28`.
- stdout advanced to epoch `14819/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14810_rew_562.22235.pth`.
- rank sidecars were refreshed in stdout at `18:54:02`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14799`.
- `in_success_region/iter`: latest `0.464844`, last-50 `0.449004`,
  last-200 `0.448431`.
- `rewards/iter`: latest `632.04`, last-50 `622.848`,
  last-200 `624.864`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00743778`, last-50 `0.00749235`,
  last-200 `0.00810663`.
- `losses/a_loss`: last-50 `-0.00412983`.
- `losses/c_loss`: last-50 `0.0185559`.
- `performance/step_inference_rl_update_fps`: last-50 about `108848`.

Analysis:
- Training remains healthy. Rolling success, reward, KL, and losses continue to
  match the post-resume baseline; throughput is a little lower than the prior
  scalar pass but still within the normal observed range.

Next:
- Continue periodic monitoring, with a status-only poll next and another
  scalar pass around `19:05 PDT`.

## 2026-06-10 19:06 PDT - Teacher Monitor Metric Pass

Goal:
- Verify training health and investigate a visible throughput dip in the
  recent stdout window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running, training metrics healthy, throughput lower than prior band.
- scheduler: running on `batch-block5-03072`, time left `1:37:36`.
- stdout advanced to epoch `14961/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14960_rew_657.4944.pth`.
- rank sidecars refreshed in stdout at `19:06:32`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `14946`.
- `in_success_region/iter`: latest `0.451904`, last-50 `0.449844`,
  last-200 `0.450654`.
- `rewards/iter`: latest `510.678`, last-50 `622.799`,
  last-200 `626.377`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00794625`, last-50 `0.00727767`,
  last-200 `0.00741877`.
- `losses/a_loss`: last-50 `-0.00412864`.
- `losses/c_loss`: last-50 `0.0198254`.
- `performance/step_inference_rl_update_fps`: latest `98783`,
  last-50 about `106117`, last-200 about `108764`.

Analysis:
- Training quality metrics remain healthy: success, reward, KL, losses, and ADR
  state are not showing instability.
- Throughput has dipped below the prior ~109-110k last-50 band, and stdout
  showed one checkpoint interval around `75k-83k` total FPS followed by
  `98k-100k`. This looks like a performance regression or transient node/load
  effect rather than a training failure, but it warrants a closer follow-up
  poll.

Next:
- Recheck stdout throughput and checkpoint cadence sooner than the usual
  5-minute interval. If FPS continues falling or checkpoints stall, inspect
  node/job state more deeply.

## 2026-06-10 19:10 PDT - Teacher Throughput Follow-Up

Goal:
- Check whether the throughput dip observed at `19:06 PDT` persisted.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`

Result:
- status: running healthy; throughput recovered.
- scheduler: running on `batch-block5-03072`, time left `1:34:36`.
- stdout advanced to epoch `14998/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_14990_rew_634.49927.pth`.
- recent non-checkpoint epochs returned to roughly `111k-113k` total FPS.
- sidecars refreshed in stdout at `19:08:59`; checkpoint-sidecar interval at
  epoch `14990` showed the expected temporary FPS dip.

Analysis:
- The earlier throughput drop appears transient, likely tied to checkpoint or
  system load rather than a persistent training slowdown. Checkpoint cadence and
  stdout progression remain normal.

Next:
- Return to normal periodic monitoring and continue scalar checks.

## 2026-06-10 19:15 PDT - Teacher Monitor Metric Pass

Goal:
- Verify the run remains healthy after throughput recovered and continue
  tracking progress toward the next requeue window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `1:28:57`.
- stdout advanced to epoch `15068/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15060_rew_621.1394.pth`.
- sidecars refreshed in stdout at `19:14:39`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15067`.
- `in_success_region/iter`: latest `0.437988`, last-50 `0.448037`,
  last-200 `0.448562`.
- `rewards/iter`: latest `516.786`, last-50 `627.454`,
  last-200 `624.963`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.0114014`, last-50 `0.00817234`,
  last-200 `0.00786435`.
- `losses/a_loss`: last-50 `-0.00383889`.
- `losses/c_loss`: last-50 `0.0192318`.
- `performance/step_inference_rl_update_fps`: latest `112755`,
  last-50 about `110035`, last-200 about `107896`.

Analysis:
- Metrics remain healthy and throughput has returned to the expected band
  outside checkpoint/sidecar intervals.

Next:
- Continue periodic monitoring. Tighten cadence as the job approaches the
  `20:39 PDT` signal/requeue window.
