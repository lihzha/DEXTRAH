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

## 2026-06-10 19:26 PDT - Teacher Monitor Metric Pass

Goal:
- Continue active monitoring as the allocation moves within roughly 75 minutes
  of the expected wall-time signal window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `1:17:45`.
- stdout advanced to epoch `15206/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15200_rew_568.57153.pth`.
- sidecars refreshed in stdout at `19:26:00`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15190`.
- `in_success_region/iter`: latest `0.445068`, last-50 `0.444155`,
  last-200 `0.445642`.
- `rewards/iter`: latest `550.848`, last-50 `607.674`,
  last-200 `619.596`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00439076`, last-50 `0.00706198`,
  last-200 `0.00771977`.
- `losses/a_loss`: last-50 `-0.00401585`.
- `losses/c_loss`: last-50 `0.0184235`.
- `performance/step_inference_rl_update_fps`: latest `92540.3`,
  last-50 about `110105`, last-200 about `110123`.

Analysis:
- Rolling metrics remain healthy. Latest FPS is from a checkpoint/sidecar
  interval; rolling throughput is back in the normal band.

Next:
- Continue periodic monitoring; start tightening cadence around `20:20 PDT`
  and verify signal/requeue behavior around `20:39 PDT`.

## 2026-06-10 19:38 PDT - Teacher Monitor Metric Pass

Goal:
- Continue monitoring and check whether the intermittent throughput dips are
  affecting training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `1:06:31`.
- stdout advanced to epoch `15342/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15340_rew_573.71826.pth`.
- sidecars refreshed in stdout at `19:37:32`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15336`.
- `in_success_region/iter`: latest `0.442139`, last-50 `0.452363`,
  last-200 `0.450874`.
- `rewards/iter`: latest `712.889`, last-50 `629.174`,
  last-200 `628.1`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.00553722`, last-50 `0.00687874`,
  last-200 `0.00722852`.
- `losses/a_loss`: last-50 `-0.00409601`.
- `losses/c_loss`: last-50 `0.021564`.
- `performance/step_inference_rl_update_fps`: latest `101339`,
  last-50 about `107588`, last-200 about `109128`.

Analysis:
- Training quality remains healthy. Throughput again dipped for a short run of
  epochs around `15331-15341`, then recovered in stdout by epoch `15342`.
  Continue to watch, but there is no evidence of a training failure or stalled
  checkpoint cadence.

Next:
- Continue periodic monitoring, and start shorter polling intervals closer to
  `20:20 PDT`.

## 2026-06-10 19:49 PDT - Teacher Monitor Metric Pass

Goal:
- Continue active monitoring as the current allocation moves under one hour
  remaining.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `55:13`.
- stdout advanced to epoch `15479/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15470_rew_692.07513.pth`.
- sidecars refreshed in stdout at `19:48:18`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15457`.
- `in_success_region/iter`: latest `0.454346`, last-50 `0.456699`,
  last-200 `0.4533`.
- `rewards/iter`: latest `656.66`, last-50 `640.087`,
  last-200 `633.938`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.0100388`, last-50 `0.00769837`,
  last-200 `0.00696036`.
- `losses/a_loss`: last-50 `-0.00390426`.
- `losses/c_loss`: last-50 `0.0243148`.
- `performance/step_inference_rl_update_fps`: latest `110828`,
  last-50 about `109919`, last-200 about `107918`.

Analysis:
- Metrics look strong. Success and reward are slightly better than recent
  monitor passes, KL remains controlled, and rolling throughput is back in the
  expected band.

Next:
- Continue periodic monitoring and tighten near `20:20 PDT`.

## 2026-06-10 20:00 PDT - Teacher Monitor Metric Pass

Goal:
- Verify run health with under 45 minutes remaining in the current allocation.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `43:54`.
- stdout advanced to epoch `15618/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15610_rew_675.95154.pth`.
- sidecars refreshed in stdout at `19:59:42`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15604`.
- `in_success_region/iter`: latest `0.453613`, last-50 `0.455356`,
  last-200 `0.456844`.
- `rewards/iter`: latest `639.124`, last-50 `636.983`,
  last-200 `637.528`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.0100831`, last-50 `0.00663687`,
  last-200 `0.00735408`.
- `losses/a_loss`: last-50 `-0.00402971`.
- `losses/c_loss`: last-50 `0.0232297`.
- `performance/step_inference_rl_update_fps`: latest `112705`,
  last-50 about `109075`, last-200 about `109375`.

Analysis:
- Metrics remain healthy and stable. Checkpoint cadence, sidecar refreshes, and
  rolling throughput are all normal.

Next:
- Continue five-minute monitoring through about `20:20 PDT`, then shorten
  cadence for signal/requeue validation.

## 2026-06-10 20:12 PDT - Teacher Monitor Metric Pass

Goal:
- Verify health before tightening the cadence for wall-time signal/requeue
  validation.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy.
- scheduler: running on `batch-block5-03072`, time left `32:26`.
- stdout advanced to epoch `15756/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_15750_rew_601.42883.pth`.
- sidecars refreshed in stdout at `20:11:17`.
- narrow failure scan returned no matches.
- TensorBoard parsed through epoch `15749`.
- `in_success_region/iter`: latest `0.446289`, last-50 `0.454551`,
  last-200 `0.455035`.
- `rewards/iter`: latest `596.484`, last-50 `626.231`,
  last-200 `634.999`.
- `num_adr_increases/iter`: `50`.
- `info/kl`: latest `0.0047396`, last-50 `0.00669583`,
  last-200 `0.00687517`.
- `losses/a_loss`: last-50 `-0.00373115`.
- `losses/c_loss`: last-50 `0.0182164`.
- `performance/step_inference_rl_update_fps`: latest `112163`,
  last-50 about `109555`, last-200 about `108398`.

Analysis:
- Training remains healthy and stable. The run is ready for tighter monitoring
  around the wall-time signal/requeue window.

Next:
- Shorten polling cadence as the job approaches the expected `20:39 PDT` TERM
  signal and verify requeue/resume from the newest checkpoint and sidecars.

## 2026-06-10 20:42 PDT - Teacher Requeue Signal Observed

Goal:
- Validate the wall-time TERM/requeue path for replacement job `28955904`.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: requeued, pending resume validation.
- scheduler: `PENDING`, `Reason=BeginTime`, eligible/start time
  `2026-06-10T20:42:29`, time limit `03:50:00`.
- command/workdir still point at the agent-owned remote worktree
  `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`.
- stdout showed Slurm cancellation for requeue at `20:39:12-20:39:13` and the
  wrapper message `Requeuing DEXTRAH job 28955904 ... after TERM`.
- latest complete checkpoint before termination:
  `last_dextrah_lstm_ep_16090_rew_585.0768.pth` at `20:39:30`.
- runtime sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` were all refreshed at `20:39:28`.
- narrow failure scan over the recent stdout tail returned no matches.

Analysis:
- The signal path behaved as intended: the wrapper trapped TERM, requested
  Slurm requeue for the same job id, forwarded TERM to the running `srun`, and
  preserved a complete checkpoint plus all rank runtime sidecars. The run is
  not yet validated after resume because the job is still pending its next
  allocation.

Next:
- Continue short one-shot SSH polling until the job returns to `RUNNING`, then
  verify allocation, wrapper restart, checkpoint/runtime-sidecar restore, epoch
  advancement beyond `16090`, and absence of fresh failure signatures.

## 2026-06-10 20:59 PDT - Teacher Requeue Resume Validated

Goal:
- Confirm replacement job `28955904` resumed correctly after the TERM/requeue
  cycle and returned to healthy training.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy after requeue.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `16:16`, time left
  `03:33:44` at `20:58:49 PDT`.
- wrapper restarted from the agent-owned remote worktree
  `/lustre/fs11/portfolios/nvr/projects/nvr_lpr_rvp/users/lzha/src/worktrees/DEXTRAH/dextrah-teacher-stop-20260610T2346Z`.
- all ranks logged restored runtime state at epoch `16090`.
- stdout advanced after resume from epoch `16091` through epoch `16128/20000`.
- latest complete checkpoints:
  `last_dextrah_lstm_ep_16100_rew_530.53937.pth`,
  `last_dextrah_lstm_ep_16110_rew_780.6249.pth`, and
  `last_dextrah_lstm_ep_16120_rew_566.7988.pth`.
- runtime sidecars `dextrah_runtime_rank_0.pth` through
  `dextrah_runtime_rank_7.pth` all refreshed at `20:58:07`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries were rsynced locally and parsed with
  `PYTHONPATH=/tmp/codex_tensorboard_pkg`.
- TensorBoard parsed through epoch `16111` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.472656`, last-50 `0.468911`,
  last-200 `0.461284`, post-resume mean for epochs `>=16090` `0.481852`.
- `rewards/iter`: latest `637.557`, last-50 `640.431`, last-200 `637.087`,
  post-resume mean for epochs `>=16090` `645.473`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00420051`, last-50 `0.00658351`,
  last-200 `0.00637556`.
- `losses/a_loss`: latest `-0.00444179`, last-50 `-0.00382845`.
- `losses/c_loss`: latest `0.0206344`, last-50 `0.0217725`.
- `performance/step_inference_rl_update_fps`: latest `98750.2`,
  last-50 about `107685`, last-200 about `109573`.

Analysis:
- Requeue/resume is validated. The restored runtime state matched the newest
  pre-signal checkpoint and rank sidecars, training advanced beyond the resume
  epoch, sidecar/checkpoint cadence resumed, and reward/success/KL/loss
  metrics remain healthy.
- The first post-resume epoch had expected lower throughput due to startup,
  and later throughput recovered into the normal range.

Next:
- Continue active monitoring at a wider cadence while the job is running.
  Watch checkpoint/sidecar cadence, success-region and KL stability, and the
  next wall-time/requeue window.

## 2026-06-10 21:05 PDT - Teacher Monitor Metric Pass

Goal:
- Verify steady-state health after the validated requeue/resume.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `22:21`, time left
  `03:27:39` at `21:04:55 PDT`.
- stdout advanced to epoch `16203/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16200_rew_583.6304.pth` at `21:04:38`.
- runtime sidecars rank `0-7` all refreshed at `21:04:36`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16185` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.46875`, last-50 `0.460566`,
  last-200 `0.462706`, post-resume mean `0.463667`.
- `rewards/iter`: latest `619.194`, last-50 `632.377`,
  last-200 `639.781`, post-resume mean `643.058`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00688349`, last-50 `0.00590158`,
  last-200 `0.00629317`.
- `losses/a_loss`: latest `-0.00186837`, last-50 `-0.00398713`.
- `losses/c_loss`: latest `0.0204783`, last-50 `0.0219376`.
- `performance/step_inference_rl_update_fps`: latest `112235`,
  last-50 about `110081`, last-200 about `109235`.

Analysis:
- Post-resume training is stable. Success remains above the ADR threshold,
  reward and losses are in the recent historical range, KL is controlled, and
  checkpoint/sidecar cadence is normal.

Next:
- Continue active monitoring at a widened cadence while this allocation is
  running.

## 2026-06-10 21:16 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued health after the requeue/resume validation and 21:05 pass.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `33:48`, time left
  `03:16:12` at `21:16:21 PDT`.
- stdout advanced to epoch `16343/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16340_rew_759.84076.pth` at `21:16:05`.
- runtime sidecars rank `0-7` refreshed at `21:16:03-21:16:04`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16331` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.466309`, last-50 `0.460093`,
  last-200 `0.461899`, post-resume mean `0.463165`.
- `rewards/iter`: latest `529.719`, last-50 `635.854`,
  last-200 `636.392`, post-resume mean `640.582`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00856836`, last-50 `0.00685097`,
  last-200 `0.00621095`.
- `losses/a_loss`: latest `-0.00297445`, last-50 `-0.00354536`.
- `losses/c_loss`: latest `0.0186439`, last-50 `0.0179362`.
- `performance/step_inference_rl_update_fps`: latest `112616`,
  last-50 about `110392`, last-200 about `109511`.

Analysis:
- The training curve remains healthy and stable after the requeue. Checkpoints,
  runtime sidecars, KL, losses, and throughput are all within the expected
  recent range; the success metric remains above the ADR threshold.

Next:
- Continue widened active monitoring through the allocation, with tighter
  polling again near the next wall-time signal window.

## 2026-06-10 21:27 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `45:01`, time left
  `03:04:59` at `21:27:35 PDT`.
- stdout advanced to epoch `16480/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16480_rew_609.60065.pth` at `21:27:31`.
- runtime sidecars rank `0-7` all refreshed at `21:27:29`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16479` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.465088`, last-50 `0.459917`,
  last-200 `0.459951`, post-resume mean `0.461893`.
- `rewards/iter`: latest `682.418`, last-50 `633.741`,
  last-200 `634.216`, post-resume mean `637.962`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00426967`, last-50 `0.00594044`,
  last-200 `0.0060537`.
- `losses/a_loss`: latest `-0.00418612`, last-50 `-0.0037655`.
- `losses/c_loss`: latest `0.0214659`, last-50 `0.0205859`.
- `performance/step_inference_rl_update_fps`: latest `112249`,
  last-50 about `109730`, last-200 about `109550`.

Analysis:
- Training remains stable: success is still above the ADR threshold, KL and
  losses are controlled, throughput is recovered, and checkpoint/sidecar cadence
  is normal.

Next:
- Continue widened active monitoring. Tighten polling near the next wall-time
  signal window.

## 2026-06-10 21:50 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `01:07:26`,
  time left `02:42:34` at `21:50:00 PDT`.
- stdout advanced to epoch `16755/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16750_rew_620.87317.pth` at `21:49:36`.
- runtime sidecars rank `0-7` all refreshed at `21:49:34`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16748` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.465576`, last-50 `0.461694`,
  last-200 `0.460469`, post-resume mean `0.4616`.
- `rewards/iter`: latest `762.176`, last-50 `659.001`,
  last-200 `649.409`, post-resume mean `641.687`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.0105329`, last-50 `0.00592015`,
  last-200 `0.00564754`.
- `losses/a_loss`: latest `-0.00222372`, last-50 `-0.00362507`.
- `losses/c_loss`: latest `0.0224711`, last-50 `0.0219947`.
- `performance/step_inference_rl_update_fps`: latest `112787`,
  last-50 about `110788`, last-200 about `110371`.

Analysis:
- Training remains healthy. Checkpoints and sidecars continue on cadence, and
  success, reward, KL, losses, and throughput remain in the expected band.

Next:
- Continue widened active monitoring, tightening near the next wall-time signal
  window.

## 2026-06-10 22:12 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `01:29:51`,
  time left `02:20:09` at `22:12:24 PDT`.
- stdout advanced to epoch `17028/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17020_rew_674.27325.pth` at `22:11:44`.
- runtime sidecars rank `0-7` refreshed at `22:11:42-22:11:43`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17016` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.476562`, last-50 `0.471118`,
  last-200 `0.466094`, post-resume mean `0.462458`.
- `rewards/iter`: latest `651.442`, last-50 `649.274`,
  last-200 `642.435`, post-resume mean `642.204`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00349445`, last-50 `0.00518375`,
  last-200 `0.00533017`.
- `losses/a_loss`: latest `-0.00423858`, last-50 `-0.00377606`.
- `losses/c_loss`: latest `0.0232393`, last-50 `0.0253416`.
- `performance/step_inference_rl_update_fps`: latest `112752`,
  last-20 about `108630`, last-50 about `104408`, last-200 about `108211`.

Analysis:
- Training remains healthy. The success metric improved over the last pass,
  reward and KL are stable, checkpoint/sidecar cadence is normal, and the brief
  throughput dip recovered in the recent last-20 window.

Next:
- Continue widened active monitoring, tightening near the next wall-time signal
  window.

## 2026-06-10 22:01 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `01:18:40`,
  time left `02:31:20` at `22:01:12 PDT`.
- stdout advanced to epoch `16892/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16890_rew_745.96277.pth` at `22:01:00`.
- runtime sidecars rank `0-7` all refreshed at `22:00:58`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16895` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.466797`, last-50 `0.464277`,
  last-200 `0.461298`, post-resume mean `0.46151`.
- `rewards/iter`: latest `611.166`, last-50 `647.012`,
  last-200 `646.313`, post-resume mean `641.434`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00423428`, last-50 `0.00546438`,
  last-200 `0.00586561`.
- `losses/a_loss`: latest `-0.00366867`, last-50 `-0.00359075`.
- `losses/c_loss`: latest `0.0288976`, last-50 `0.0299657`.
- `performance/step_inference_rl_update_fps`: latest `113989`,
  last-50 about `110464`, last-200 about `109933`.

Analysis:
- Training remains healthy with normal artifact cadence. Success is stable above
  the ADR threshold, KL is controlled, and throughput is normal.

Next:
- Continue widened active monitoring, tightening near the next wall-time signal
  window.

## 2026-06-10 21:38 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `56:13`, time left
  `02:53:47` at `21:38:47 PDT`.
- stdout advanced to epoch `16616/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_16610_rew_589.4641.pth` at `21:38:17`.
- runtime sidecars rank `0-7` all refreshed at `21:38:15`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `16599` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.462891`, last-50 `0.462017`,
  last-200 `0.461051`, post-resume mean `0.46211`.
- `rewards/iter`: latest `634.927`, last-50 `654.959`,
  last-200 `638.927`, post-resume mean `639.906`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00420684`, last-50 `0.00545612`,
  last-200 `0.00571981`.
- `losses/a_loss`: latest `-0.00388787`, last-50 `-0.00378896`.
- `losses/c_loss`: latest `0.0210969`, last-50 `0.0221763`.
- `performance/step_inference_rl_update_fps`: latest `112866`,
  last-50 about `110464`, last-200 about `108587`.

Analysis:
- Training remains healthy. Success and reward are stable, KL is controlled,
  losses are not diverging, throughput is normal, and checkpoint/sidecar
  cadence is intact.

Next:
- Continue widened active monitoring. Tighten polling near the next wall-time
  signal window.

## 2026-06-10 22:25 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health after the validated requeue
  resume.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `01:42:49`,
  time left `02:07:11` at `22:25:23 PDT`.
- stdout advanced to epoch `17185/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17180_rew_486.6669.pth` at `22:24:57`.
- runtime sidecars rank `0-7` all refreshed at `22:24:55`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17186` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.468018`, last-50 `0.455352`,
  last-200 `0.459124`, post-resume mean `0.461755`.
- `rewards/iter`: latest `649.808`, last-50 `632.478`,
  last-200 `638.268`, post-resume mean `641.384`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00438264`, last-50 `0.00516815`,
  last-200 `0.00509207`.
- `losses/a_loss`: latest `-0.00258737`, last-50 `-0.0032819`.
- `losses/c_loss`: latest `0.0199249`, last-50 `0.0186364`.
- `performance/step_inference_rl_update_fps`: latest `112634`,
  last-20 about `110564`, last-50 about `110450`, last-200 about `108432`.

Analysis:
- Training remains healthy. Success and reward dipped slightly from the prior
  rolling window but remain in the same band as earlier post-resume passes,
  ADR remains saturated, KL is controlled, losses are low, and artifact cadence
  is intact.

Next:
- Continue widened active monitoring until the next wall-time signal window,
  then tighten polling to validate checkpoint/sidecar refresh and requeue
  behavior again.

## 2026-06-10 22:38 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health and check the short throughput
  dip visible in the stdout tail.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `01:55:14`,
  time left `01:54:46` at `22:37:48 PDT`.
- stdout advanced to epoch `17336/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17330_rew_612.2449.pth` at `22:37:16`.
- runtime sidecars rank `0-7` all refreshed at `22:37:14`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17332` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.47876`, last-50 `0.47144`,
  last-200 `0.463901`, post-resume mean `0.462375`.
- `rewards/iter`: latest `649.654`, last-50 `647.435`,
  last-200 `644.556`, post-resume mean `642.186`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00704429`, last-50 `0.00489331`,
  last-200 `0.00521332`.
- `losses/a_loss`: latest `-0.00289003`, last-50 `-0.00359385`.
- `losses/c_loss`: latest `0.0228959`, last-50 `0.0255061`.
- `performance/step_inference_rl_update_fps`: latest `112934`,
  last-20 about `101295`, last-50 about `106590`, last-200 about `109094`.

Analysis:
- Training remains healthy. The stdout tail showed a brief throughput dip near
  epochs `17314-17326`, but FPS recovered by the latest scalar, checkpoint and
  sidecar cadence stayed intact, and success/reward/KL remain in the expected
  post-resume band.

Next:
- Continue widened active monitoring, with the next tight polling window still
  expected near the wall-time signal around `2026-06-11 00:27 PDT`.

## 2026-06-10 22:51 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health after the prior transient
  throughput dip recovered.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `02:08:32`,
  time left `01:41:28` at `22:51:05 PDT`.
- stdout advanced to epoch `17500/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17500_rew_653.61145.pth` at `22:51:04`.
- runtime sidecars rank `0-7` all refreshed at `22:51:02`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17479` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.46167`, last-50 `0.461421`,
  last-200 `0.467341`, post-resume mean `0.46276`.
- `rewards/iter`: latest `641.475`, last-50 `646.843`,
  last-200 `648.88`, post-resume mean `643.009`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00540916`, last-50 `0.00449403`,
  last-200 `0.00471028`.
- `losses/a_loss`: latest `-0.00346748`, last-50 `-0.00319876`.
- `losses/c_loss`: latest `0.0253422`, last-50 `0.0233809`.
- `performance/step_inference_rl_update_fps`: latest `112045`,
  last-20 about `110814`, last-50 about `110787`, last-200 about `109106`.

Analysis:
- Training remains healthy. The prior throughput dip recovered, checkpoint and
  sidecar cadence remains intact, success and reward are steady, KL is
  controlled, and losses remain low without divergence.

Next:
- Continue widened monitoring until closer to the expected wall-time TERM
  signal around `2026-06-11 00:27 PDT`.

## 2026-06-10 23:06 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `02:23:43`,
  time left `01:26:17` at `23:06:17 PDT`.
- stdout advanced to epoch `17688/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17680_rew_640.2444.pth` at `23:05:39`.
- runtime sidecars rank `0-7` refreshed at `23:05:37-23:05:38`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17677` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.469238`, last-50 `0.461978`,
  last-200 `0.462888`, post-resume mean `0.462778`.
- `rewards/iter`: latest `587.875`, last-50 `642.258`,
  last-200 `649.419`, post-resume mean `643.863`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00486958`, last-50 `0.00423239`,
  last-200 `0.00436882`.
- `losses/a_loss`: latest `-0.0027175`, last-50 `-0.00319704`.
- `losses/c_loss`: latest `0.0221314`, last-50 `0.0224796`.
- `performance/step_inference_rl_update_fps`: latest `112702`,
  last-20 about `111032`, last-50 about `110388`, last-200 about `110091`.

Analysis:
- Training remains healthy. Success and reward are steady in the post-resume
  band, KL and losses remain controlled, throughput is normal, and checkpoint
  and sidecar cadence is intact.

Next:
- Continue widened monitoring for one more interval, then begin tightening as
  the expected wall-time TERM/requeue window approaches.

## 2026-06-10 23:20 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued steady-state training health before switching to a shorter
  cadence ahead of the wall-time signal window.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `02:37:54`,
  time left `01:12:06` at `23:20:28 PDT`.
- stdout advanced to epoch `17860/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_17860_rew_643.3928.pth` at `23:20:25`.
- runtime sidecars rank `0-7` all refreshed at `23:20:23`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `17848` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.458984`, last-50 `0.467007`,
  last-200 `0.464991`, post-resume mean `0.463094`.
- `rewards/iter`: latest `638.031`, last-50 `651.344`,
  last-200 `649.861`, post-resume mean `644.568`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00632707`, last-50 `0.00389646`,
  last-200 `0.00412442`.
- `losses/a_loss`: latest `-0.00274446`, last-50 `-0.00336167`.
- `losses/c_loss`: latest `0.0254587`, last-50 `0.0260481`.
- `performance/step_inference_rl_update_fps`: latest `113254`,
  last-20 about `109407`, last-50 about `107915`, last-200 about `109093`.

Analysis:
- Training remains healthy. A short stdout throughput valley near epochs
  `17821-17830` recovered, checkpoint/sidecar cadence stayed intact, and the
  rolling success, reward, KL, loss, and FPS windows remain normal.

Next:
- Shorten monitoring cadence as the next expected wall-time TERM/requeue window
  approaches.

## 2026-06-10 23:34 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued training health on shorter cadence as the wall-time signal
  window approaches.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `02:51:40`,
  time left `58:20` at `23:34:14 PDT`.
- stdout advanced to epoch `18029/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_18020_rew_616.2878.pth` at `23:33:25`.
- runtime sidecars rank `0-7` all refreshed at `23:34:13`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `18020` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.477295`, last-50 `0.463472`,
  last-200 `0.463857`, post-resume mean `0.463116`.
- `rewards/iter`: latest `616.288`, last-50 `632.749`,
  last-200 `637.019`, post-resume mean `643.634`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00231622`, last-50 `0.00328188`,
  last-200 `0.00385593`.
- `losses/a_loss`: latest `-0.00339492`, last-50 `-0.00325661`.
- `losses/c_loss`: latest `0.0244347`, last-50 `0.0253629`.
- `performance/step_inference_rl_update_fps`: latest `90084.8`,
  last-20 about `110199`, last-50 about `110134`, last-200 about `109347`.

Analysis:
- Training remains healthy. The job continued past epoch `18000/20000` and is
  still advancing toward `20000`. The latest FPS sample is low on a
  checkpoint/sidecar interval, but the rolling windows are normal and artifacts
  are refreshing on cadence.

Next:
- Keep the shorter monitoring cadence and tighten again near the expected
  `2026-06-11 00:27 PDT` TERM/requeue signal.

## 2026-06-10 23:43 PDT - Teacher Monitor Metric Pass

Goal:
- Verify continued training health on shorter cadence.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `03:00:56`,
  time left `49:04` at `23:43:29 PDT`.
- stdout advanced to epoch `18144/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_18140_rew_728.52997.pth` at `23:43:09`.
- runtime sidecars rank `0-7` all refreshed at `23:43:07`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `18143` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.44873`, last-50 `0.461323`,
  last-200 `0.462301`, post-resume mean `0.463055`.
- `rewards/iter`: latest `609.916`, last-50 `651.516`,
  last-200 `649.219`, post-resume mean `644.372`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.003654`, last-50 `0.00306509`,
  last-200 `0.00341482`.
- `losses/a_loss`: latest `-0.0033099`, last-50 `-0.00295416`.
- `losses/c_loss`: latest `0.0234913`, last-50 `0.0213291`.
- `performance/step_inference_rl_update_fps`: latest `112558`,
  last-20 about `108695`, last-50 about `110028`, last-200 about `109974`.

Analysis:
- Training remains healthy. The short two-epoch FPS dip in stdout recovered,
  rolling throughput is normal, and success, reward, KL, losses, checkpoints,
  and runtime sidecars remain in the expected post-resume band.

Next:
- Continue shortened cadence and tighten further inside the final 15 minutes
  before the expected TERM/requeue signal.

## 2026-06-10 23:53 PDT - Teacher Monitor Metric Pass

Goal:
- Verify that the stdout throughput dip seen around epochs `18221-18231`
  recovered while the job remains on shortened cadence.

Command / Job:
- job_id: `28955904`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28955904.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`
- local TensorBoard copy:
  `/tmp/dextrah_teacher_events`

Result:
- status: running healthy.
- scheduler: `RUNNING` on `batch-block5-03072`, elapsed `03:11:05`,
  time left `38:55` at `23:53:38 PDT`.
- stdout advanced to epoch `18267/20000`.
- latest complete checkpoint:
  `last_dextrah_lstm_ep_18260_rew_646.908.pth` at `23:53:00`.
- runtime sidecars rank `0-7` refreshed at `23:52:58-23:52:59`.
- narrow critical failure scan over recent stdout returned no matches.
- TensorBoard summaries parsed through epoch `18265` for epoch-keyed scalars.
- `in_success_region/iter`: latest `0.472168`, last-50 `0.467847`,
  last-200 `0.465524`, post-resume mean `0.463313`.
- `rewards/iter`: latest `640.302`, last-50 `658.693`,
  last-200 `653.369`, post-resume mean `644.812`.
- `num_adr_increases/iter`: latest `50`, last-50 `50`.
- `info/kl`: latest `0.00227695`, last-50 `0.00341779`,
  last-200 `0.00341525`.
- `losses/a_loss`: latest `-0.00358635`, last-50 `-0.00315264`.
- `losses/c_loss`: latest `0.0234645`, last-50 `0.0262091`.
- `performance/step_inference_rl_update_fps`: latest `112389`,
  last-20 about `110250`, last-50 about `106637`, last-200 about `109270`.

Analysis:
- Training remains healthy. The stdout throughput dip recovered by epochs
  `18235-18259`, latest scalar FPS is normal, checkpoint/sidecar cadence is
  intact, and reward/success/KL/loss windows are stable.

Next:
- Continue shortened cadence and tighten further in the final 15 minutes before
  the expected TERM/requeue signal.
