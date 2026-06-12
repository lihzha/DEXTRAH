# Worker B Handoff - Franka Cube Trajectory Tracking

## Branch / Worktree / Commit

- Agent: `franka-cube-traj-tracking`
- Worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`
- Branch: `codex/franka-cube-trajectory-tracking`
- Current source commit before this handoff commit: `4cf2baeb5b36ed91e5b984b9b082c3f99f43878e`
- Owned worklog: `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`
- Remote l401 worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-traj-tracking`
- Remote deployed source commit: `4cf2baeb5b36ed91e5b984b9b082c3f99f43878e`

## Latest Status / Conclusions

- Current best B result remains assisted handoff, not policy-only RL.
- Best low-assistance gate before shutdown: `policy_reference_mix_hold` alpha `0.05`, with `3/4` final success, max lift about `0.2875 m`, no resets, target unsafe max `0`, visually verified.
- Alpha `0.0` under contact-aware terminal hold reached `2/4`, but this is still not policy-only because the terminal hold controller performs lift/hold after contact evidence.
- Failure mode is now closure/hold robustness around contact, not the old drift-away/train-eval mismatch.
- Old `actionscale-rewinf-diag-video480-step-0.mp4` from job `1027753` is obsolete failed diagnostic evidence.
- Compact trajectory reference remains caveated: `curobo_validated=false` and uses the 60 mm GraspGenX/cuRobo export pending exact DEXTRAH geometry validation.

## Recent Code Change

Committed in `4cf2bae`:
- `dextrah_lab/rl_games/bc_reference_action_imitation.py`
  - Added diagnostic-only BC collection source `policy_reference_mix_hold`.
  - Added contact-aware terminal hold support for collection with isolated `_bc_terminal_hold_state`.
  - Added dataset tensors for `max_finger_to_cube_dist`, `hold_active`, and `hold_contact_after_phase`.
  - Added handoff filters `--handoff_max_finger_dist` and `--handoff_require_hold_active`.
  - Report now prints hold/mix config and contact-window handoff summaries.
- `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - Added env-var pass-through and stdout echo for collection mix/hold/handoff settings.
- `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md`
  - Recorded plan, validation, deploy notes, and launch record.

Local validation before launch:
- `python3 -m py_compile dextrah_lab/rl_games/bc_reference_action_imitation.py` passed.
- `bash -n cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` passed.
- `git diff --check` passed.

## Active / Recent Slurm Jobs

No active B Slurm jobs at handoff.

Recent job needing artifact fetch/full review:

| Job | State | Run | Log | Result Path | Notes |
| --- | --- | --- | --- | --- | --- |
| `1028250` | `COMPLETED 0:0`, elapsed `00:01:16`, node `pool0-00030` | `franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700` | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028250.out` | `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700` | Supervised-only assisted/handoff BC job. It completed and printed metrics, but artifacts have not been fetched/opened locally due shutdown request. |

Key `1028250` stdout metrics already visible:
- selected step: `300`; selected score: `0.1256902925670147`.
- derived handoff source counts: `94` train + `24` val selected samples, total `118`.
- handoff val L2: `0.0222403556`; handoff val up abs `0.00309`; handoff val close/gripper abs `0.01155`.
- alpha0.00 collection val L2: `0.2409972697`.
- alpha0.05 collection val L2: `0.2172831893`.
- global val L2: `0.2230899781`.
- reference summary in stdout: `curobo_validated=false`, `validation_passed=true`, `source_tag=graspgenx_curobo_60mm_export_pending_exact_validation`.

Important: treat `1028250` as a supervised artifact to inspect, not as a closed-loop behavior result. No selector/video/PPO was launched from it.

## Latest Artifact URLs / Paths

Best current assisted gate bundle:
- report: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/report.md
- plot: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/lowalpha_contacthold_plot.png
- selector summary CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/selector_summary.csv`
- targeted video summary CSV: `cluster_results/l401/franka_cube_traj_tracking_contacthold_lowalpha_20260611_235000/targeted_video_summary.csv`

Targeted videos from current best gate:
- alpha0.0 env1 success sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env1succ_520_20260611_235000_artifacts/video_contact_sheet.png
- alpha0.0 env1 success video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env1succ_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a000_env1succ-step-0.mp4
- alpha0.0 env0 failure sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env0fail_520_20260611_235000_artifacts/video_contact_sheet.png
- alpha0.0 env0 failure video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a000_env0fail_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a000_env0fail-step-0.mp4
- alpha0.05 env0 success sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env0succ_520_20260611_235000_artifacts/video_contact_sheet.png
- alpha0.05 env0 success video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env0succ_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a005_env0succ-step-0.mp4
- alpha0.05 env2 failure sheet: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env2fail_520_20260611_235000_artifacts/video_contact_sheet.png
- alpha0.05 env2 failure video: http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_bc_handoff_noreset_contacthold_vislow_a005_env2fail_520_20260611_235000/videos/handoff-noreset-contacthold-vislow-a005_env2fail-step-0.mp4

New `1028250` supervised artifacts exist remotely but were not fetched/opened:
- remote report: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/report.md`
- remote metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/bc_metrics.json`
- remote loss plot: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/bc_loss_plot.png`
- remote source plot: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/bc_source_metric_plot.png`
- remote oracle plot: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/oracle_residual_plot.png`
- remote checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/nn/bc_reference_action_imitation.pth`
- remote dataset: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/reference_action_dataset.pt`

## Current Git Status At Handoff Preparation

Before creating this handoff commit:
- committed source/wrapper changes are in `4cf2bae`.
- uncommitted owned files: `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md` and this handoff file.
- no generated artifacts/checkpoints/videos/logs should be committed.

## Exact Next Recommended Step

1. Fetch job `1028250` artifacts locally:
   - `rsync -av l401:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/ cluster_results/l401/franka_cube_traj_tracking_bc_contacthold_handoff_a000_a005_20260612_000700/`
   - also fetch `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1028250.out`.
2. Open with `viz-open`:
   - `report.md`, `bc_loss_plot.png`, `bc_source_metric_plot.png`, `oracle_residual_plot.png`.
3. Decide whether the supervised gate is coherent:
   - Handoff source is strong (`val_source_contacthold_success_handoff_alpha0_l2 ~0.022`) but broad alpha0/alpha0.05 collection errors are still high (`~0.24`, `~0.217` L2). This may be useful specifically for a contact-window head, but not enough by itself to claim policy-only or broad handoff learning.
4. If and only if supervised artifacts pass the intended gate, run small selector metrics first, then videos only for current/lowest-alpha improvement and failure pairs.

Do not claim:
- policy-only RL success;
- final trajectory-tracking solve;
- cuRobo-validated DEXTRAH-ready reference;
- readiness for PPO/RL scale-up.

Do not launch:
- full PPO/RL training;
- broad selector/video sweeps before `1028250` artifacts are fetched and inspected.

## Blockers / Risks

- l401 GitHub fetch failed with `git@github.com: Permission denied (publickey)`. The exact commit was deployed via a temporary Git bundle into the agent-owned worktree. Future agents should either fix l401 GitHub auth or use the same bundle-style Git transfer deliberately.
- Inside the container, `git rev-parse HEAD` printed a fatal “not a git repository” due the mounted worktree `.git` file referencing the original NFS worktree metadata path. The job still ran and wrote artifacts; logs may not include in-container git provenance.
- `1028250` completed but has not been fully fetched/opened locally because the user requested shutdown.
- The new `policy_reference_mix_hold` BC collection source has passed local syntax checks and one clean supervised job exit, but it has not yet been closed-loop evaluated.
- Reference remains `curobo_validated=false`; keep the 45/60 mm geometry caveat explicit.
