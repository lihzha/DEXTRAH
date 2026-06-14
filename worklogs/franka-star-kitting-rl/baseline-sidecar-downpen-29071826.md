## 2026-06-14T17:48:10Z - franka_star_no_prior_downpen_ep300_20260614_174810

Goal:
- Launch the no-prior PPO baseline sidecar for the DEXTRAH Franka star kitting down-action reward comparison, matching the main reset-prior run reward/domain-randomization settings while disabling grasp-prior helpers.

Hypothesis:
- With reset and action priors disabled, early metrics would show whether the abnormal pre-lift/down-action behavior reproduced without prior-assisted starts.

Change:
- No source code changes.
- Submitted only a Slurm job from the existing detached A100 worktree.
- Canceled immediately after the main-agent interrupt reported that the main reset-prior reward was superseded and job 29071773 was canceled.

Version Control:
- agent_id: baseline-sidecar-downpen
- local_worktree: /home/lzha/code/DEXTRAH
- remote_worktree: /lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-star-kitting-rl-bc
- worklog: worklogs/franka-star-kitting-rl/baseline-sidecar-downpen-29071826.md
- branch: local codex/robolab-orbit-render-20260613
- base_commit: local e4e659104d4466af3b91726fecc5970403c3e687
- implementation_commit: n/a, no source changes
- remote_commit/status: bae32d55657d3adb4242ee6aa7cbe62c72612f71, detached HEAD, clean before launch
- changed_files: this worklog only

Command / Job:
- command: `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-star-kitting-rl-bc,FULL_EXPERIMENT_NAME=franka_star_no_prior_downpen_ep300_20260614_174810,TASK=Dextrah-Franka-Star-Kitting,GRASP_PRIOR_RESET_ENABLED=False,GRASP_PRIOR_ACTION_WARMSTART_ENABLED=False,GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False,GRASP_PRIOR_ACTION_RESIDUAL_ENABLED=False,STAR_POST_LIFT_ONLY_PLACEMENT_REWARD=True,STAR_PLACEMENT_WEIGHT=160.0,STAR_PLACEMENT_XY_PROGRESS_WEIGHT=6500.0,STAR_TRANSPORT_XY_SHARPNESS=6.0,STAR_PLACEMENT_HEIGHT_SHARPNESS=18.0,NUM_ENVS=2048,MAX_ITERATIONS=300,DEXTRAH_RLGAMES_JSONL_METRICS=True,AUTO_RESUME=False,SELF_RELAUNCH=False,SCORE_TO_WIN=1000000000,CODE_COMMIT=bae32d55657d3adb4242ee6aa7cbe62c72612f71,MASTER_PORT=30137 cluster/sbatch_train_teacher_8gpu.sh`
- job_id: 29071826
- node: batch-block7-01724
- log: /lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29071826.out
- run_dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_star_kitting/franka_star_no_prior_downpen_ep300_20260614_174810
- metrics: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_star_kitting/franka_star_no_prior_downpen_ep300_20260614_174810/metrics/direct_info_rank_0.jsonl

Prior / Reward Flags:
- GRASP_PRIOR_RESET_ENABLED=False
- GRASP_PRIOR_ACTION_WARMSTART_ENABLED=False
- GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False
- GRASP_PRIOR_ACTION_RESIDUAL_ENABLED=False
- STAR_POST_LIFT_ONLY_PLACEMENT_REWARD=True
- STAR_PLACEMENT_WEIGHT=160.0
- STAR_PLACEMENT_XY_PROGRESS_WEIGHT=6500.0
- STAR_TRANSPORT_XY_SHARPNESS=6.0
- STAR_PLACEMENT_HEIGHT_SHARPNESS=18.0
- NUM_ENVS=2048
- MAX_ITERATIONS=300
- DEXTRAH_RLGAMES_JSONL_METRICS=True
- AUTO_RESUME=False
- SELF_RELAUNCH=False
- SCORE_TO_WIN=1000000000
- MASTER_PORT=30137
- CODE_COMMIT=bae32d55657d3adb4242ee6aa7cbe62c72612f71

Result:
- status: canceled by interrupt before startup metrics
- scheduler: `29071826|CANCELLED by 158351|0:0|00:00:22|batch-block7-01724`
- batch step: `29071826.batch|FAILED|15:0|00:00:23|batch-block7-01724`
- evidence: Slurm log echoed the requested no-prior flags, `CODE_NFS` pointed at the supplied detached worktree, and `SELF_RELAUNCH=False; not requeuing job` after cancellation.
- metrics/artifacts: run directory was not created; `metrics/direct_info_rank_0.jsonl` was not created.

Analysis:
- The baseline did launch and briefly allocate, but it was canceled immediately after the main-agent interrupt because the reward was superseded. The process had not reached Python training startup or JSONL metric creation, so there are no early success/lift/action metrics to compare.

Next:
- Do not relaunch this baseline until the main-agent provides the replacement reward/config direction.
