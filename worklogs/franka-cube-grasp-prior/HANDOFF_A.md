# Worker A Handoff: Franka Cube GraspGenX Pregrasp Reset

## Branch / Worktree

- Agent: `franka-cube-ggx-pregrasp-reset`
- Worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- Branch: `codex/franka-cube-ggx-pregrasp-reset`
- Source/wrapper commit used for latest jobs: `aec212660b3dafe1c7ef90869905ee79f52cef09`
- Owned worklog: `worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md`
- Remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- Remote code state for latest launch: detached `aec212660b3dafe1c7ef90869905ee79f52cef09`

## Current Status

- Reset geometry/library is healthy.
  - Low-z no-offset GraspGenX reset/prior gate previously passed.
  - Reset success/quality remains `1.0/1.0` in recent runs.
- Apple-to-apple reset-prior PPO is **not** ready to scale.
  - Prior and baseline learned policies failed bounded 45/200 epoch smokes.
  - Prior policies tend to hover/open or move away; baseline closes off-target.
  - Assisted scripted approach-to-exact plus light/medium close can lift, so the blocker is learned closed-loop action discovery/reward, not reset geometry.
- Latest accepted conclusion before shutdown:
  - Reward-only action-prior intervention is non-apple-to-apple and has not yet produced learned grasp/lift.
  - Do **not** claim successful apple-to-apple GraspGenX reset-prior RL.
  - Do **not** launch A100/full PPO without a bounded learned-policy video showing real grasp/lift.

## Recent Jobs

### Completed and Inspected

- Training job: `1028245`
  - Run: `franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655`
  - Type: non-apple-to-apple diagnostic, reset prior + action-prior reward, no action override
  - Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/franka_cube_smoke_1028245.out`
  - Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655`
  - Local fetch: `cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/`
  - Result: completed `0:0`, JSONL 45 rows, no bad scalars, reset success/quality `1.0/1.0`, success/lift `0/0`.

- Eval job: `1028247`
  - Run: `franka_cube_lowz_actionprior_seqfix_eval_ep10_20260612_0657`
  - Checkpoint: ep10 best-reward from `1028245`
  - Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1028247.out`
  - Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_lowz_actionprior_seqfix_eval_ep10_20260612_0657`
  - Local fetch: `cluster_results/l401/franka_cube_lowz_actionprior_seqfix_eval_ep10_20260612_0657/`
  - Result: no success/lift; brief near-cube behavior then moves away.

- Eval job: `1028248`
  - Run: `franka_cube_lowz_actionprior_seqfix_eval_ep45_20260612_0657`
  - Checkpoint: final ep45 from `1028245`
  - Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1028248.out`
  - Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_lowz_actionprior_seqfix_eval_ep45_20260612_0657`
  - Local fetch: `cluster_results/l401/franka_cube_lowz_actionprior_seqfix_eval_ep45_20260612_0657/`
  - Result: no success/lift; reaches/perturbs cube, then opens/off-target and moves away.

### Active / Needs Monitoring

- Training job: `1028249`
  - Run: `franka_cube_lowz_actionprior_hold_r8s07_45_20260612_0704`
  - Type: non-apple-to-apple staged action-prior preservation diagnostic
  - Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/franka_cube_smoke_1028249.out`
  - Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_lowz_actionprior_hold_r8s07_45_20260612_0704`
  - Config: 64 envs, 45 epochs, low-z prior library, `GRASP_PRIOR_ACTION_WARMSTART_ENABLED=False`, action-prior reward enabled, weight `8.0`, sharpness `0.7`, lift window `160`, lift action z `0.50`.
  - Last observed state: Slurm `RUNNING` at about 2 minutes elapsed; stdout reached epoch `41/45` and checkpoint `ep_40_rew_1430.2056`.
  - This job still needs monitoring, JSONL parsing, artifact fetch, and video eval if the metrics justify it.

## Latest Inspectable Artifacts

- Seqfix inspection report:
  - `cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/REPORT.md`
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/REPORT.md
- Contact sheets:
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/contact_sheet_ep10.jpg
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/contact_sheet_ep45.jpg
- Curves:
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/training_task_curves.png
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_r4s1_45_20260612_0655/inspection_20260612_0702/training_action_prior_curves.png
- Videos:
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_eval_ep10_20260612_0657/videos/lowz-actionprior-seqfix-step-0.mp4
  - http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_lowz_actionprior_seqfix_eval_ep45_20260612_0657/videos/lowz-actionprior-seqfix-step-0.mp4

## Changed Files

Owned source/wrapper changes already committed before this handoff:

- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `dextrah_lab/rl_games/eval_rollout.py`
- `cluster/sbatch_train_franka_cube_grasp_1gpu_smoke.sh`
- `cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- `worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md`

This handoff adds:

- `worklogs/franka-cube-grasp-prior/HANDOFF_A.md`

Generated artifacts, checkpoints, videos, logs, and `local_results/` are not committed.

## Recommended Next Step

1. Monitor job `1028249` to terminal state.
2. Fetch its run dir and log.
3. Parse `metrics/direct_info_rank_0.jsonl` for bad scalars, reset success/quality, action-prior active/reward, success/lift, gripper width/action, and EE/finger distances.
4. If metrics are at least sane, run video-first eval for best-reward and final checkpoint, then generate contact sheets/report.
5. Treat `1028249` as **non-apple-to-apple intervention**. Even if it succeeds, it is not the final reset-prior comparison.

Do not scale A100/full PPO and do not claim apple-to-apple success until a bounded learned-policy eval video shows real grasp/lift under the intended comparison protocol.

## Blockers / Risks

- Job `1028249` was active at handoff and uninspected.
- l401 remote could not fetch GitHub earlier due `Permission denied (publickey)`; I deployed commit `aec2126` to the remote worktree via a Git bundle and detached checkout.
- Reward-only/action-prior interventions are diagnostic and change behavior beyond the apple-to-apple reset-prior variant.
- Recent videos show learned policies can score reward while hovering/opening or perturbing without actual grasp/lift; video evidence is mandatory.
