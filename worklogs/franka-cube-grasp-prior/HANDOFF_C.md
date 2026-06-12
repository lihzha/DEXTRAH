# Worker C Handoff - Diffusion Policy BC Warm-Start

Timestamp: `2026-06-12T00:07:55-07:00`

## Branch / Worktree

- Agent ID: `franka-cube-dp-bc-warmstart`
- Worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- Branch: `codex/franka-cube-diffusion-policy-bc`
- Current commit before this handoff commit: `39f367910a6f5d13f3e471695c41073ea09390cf`
- Owned worklog: `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- External artifact root: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart`
- Official Diffusion Policy checkout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
- Official DP source/commit:
  `real-stanford/diffusion_policy` @ `5ba07ac6661db573af695b419a7947ecb704690f`

## Latest Status

- Raw GraspGenX/cuRobo labels were ruled out as BC-ready for the DEXTRAH
  controller; controller/relabel work was required.
- Contact-aware relabeling with left/right finger centering produced a small
  accepted alpha0.75 set: 4/4 pass, 936 transitions, zero executed clipping.
- Official DP 25D phase/progress offline smoke passed the gripper-sign gate, but
  closed-loop DP still drifted in align/open support.
- Eval-only coherent action replacement proved the controller/relabel labels
  can succeed if all 7 action dims are replaced with nearest accepted labels.
- The latest 260-step oracle action-replacement run reached durable success,
  but this is explicitly **not** official DP policy readiness.
- Policy-facing blocker remains: the official DP checkpoint must emit coherent
  coupled pose + gripper + phase-conditioned actions before any Isaac closed-loop
  policy eval, DP fine-tune scale-up, or RL handoff.

## Slurm Jobs

No active C jobs were visible from:

```bash
ssh l401 'squeue -u lzha -o "%.18i %.12T %.24j %.10M %.20R" | grep -E "JOBID|franka_cube|dextrah|dp|contact|10282" || true'
```

Recent relevant completed jobs:

| Job | Run | Status | Log | Result path | Needs monitoring |
| --- | --- | --- | --- | --- | --- |
| `1028246` | `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528` | completed, bounded oracle pass | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028246.out` | `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528` | no |
| `1028239` | `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712` | completed, oracle partial pass below lift threshold | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028239.out` | `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712` | no |
| `1028230` | `franka_cube_dp_eval_phaseprogress_set4_ep0_nearest_label_align_pose...` | completed, pose-only oracle failed | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028230.out` | DEXTRAH eval artifact namespace for job `1028230`; see worklog | no |
| `1028199` | `franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008` | completed, official DP closed-loop failure video | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028199.out` | DEXTRAH eval artifact namespace for job `1028199`; see worklog | no |

## Latest Artifacts

Latest oracle horizon result, fetched locally:

- Local dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528`
- Report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/full_action_oracle_horizon260_report.md`
- Video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/videos/franka-cube-dp-phaseprogress-fullcorr260-step-0.mp4`
- Contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/dp_fullcorr260_contact_sheet.jpg`
- Support trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/closed_loop_support_trace.png`
- Action component plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/closed_loop_action_components.png`

Latest accepted relabel set:

- Local dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- Report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_report.md`
- Contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_sheet_2x2.jpg`

Latest 25D official DP offline smoke:

- Local dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001`
- Dataset:
  `contact_relabel_set_phase_progress.npz` with `obs=(936,25)`,
  `action=(936,7)`, `episode_ends=[240,480,706,936]`.
- Checkpoint:
  `official_dp_train/checkpoints/latest.ckpt`
- Existing action semantics report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/action_semantics_100steps/action_semantics_report.md`

## Git Status / Changed Files

Current owned changes at handoff-prep time:

- Modified:
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- Added:
  `worklogs/franka-cube-grasp-prior/HANDOFF_C.md`

No source-code edits were started after the stop request. Generated artifacts,
checkpoints, logs, and videos remain outside Git under `.codex-external`.

## Exact Next Recommended Step

Stop launching simulator jobs. The next agent should run the offline-only
official-DP pose + gripper + phase coherence gate that was planned in the
worklog:

1. Use the official DP checkpoint:
   `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_train/checkpoints/latest.ckpt`
2. Use the accepted phase-progress dataset:
   `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`
3. Compare official DP predicted first actions and action horizons against the
   successful nearest-label oracle labels over all accepted relabel windows,
   grouped by `align_open`, `close_hold`, and `lift`.
4. Report pose direction cosine, pose norm ratio, per-channel errors, gripper
   sign/magnitude, best temporal offset, phase/progress feature values, and a
   clear pass/fail verdict.

Do **not** claim BC warm-start readiness from `1028246`. It is a
nearest-label full-action oracle replacement, not an official DP policy rollout.

Do **not** launch:

- DP fine-tuning or broad DP training.
- Isaac closed-loop DP eval.
- RL/PPO warm-start.

until the offline coherence gate explains how to make the checkpoint emit
coherent coupled actions and a separate tiny gate is explicitly authorized.

## Blockers / Risks

- Official DP 25D checkpoint has not yet shown closed-loop policy competence;
  prior video showed align/open support drift before coherent contact/lift.
- The 260-step pass is only proof that accepted relabel labels and controller
  can succeed under oracle action replacement.
- The 25D policy requires runtime phase/progress features; any future closed
  loop must preserve exact feature semantics or it will introduce a train/eval
  mismatch.
- Normal-reset generalization remains unproven and previously failed.
- l401 GitHub SSH fetch was unavailable earlier; remote worktree updates used
  HTTPS fetch from `https://github.com/lihzha/DEXTRAH.git`.
