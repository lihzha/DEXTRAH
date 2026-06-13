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

## 2026-06-12T21:11:56-07:00 - RGB epoch12 exact-reset chunked averaged eval

Goal:
- Test whether the RGB accepted183+normalreset25x2 epoch12 checkpoint fails exact ep183 because one-step stochastic DP sampling drifts/early-closes, rather than because RGB I/O or labels are incoherent.

Hypothesis:
- Offline RGB coherence on exact ep183 mostly matches labels, but row 43626/step80 predicts close one step early under one seeded sample, and the unseeded chunk1 eval uses aggressive first actions. Standard image-DP inference with `ACTION_CHUNK_STEPS=8`, `NUM_ACTION_SAMPLES=8`, and fixed `POLICY_SAMPLE_SEED=42` may reduce sampling noise and preserve the learned action sequence.

Change:
- Added offline-only diagnostic `dextrah_lab/offline_dp_bc/diagnose_rgb_dp_offline_coherence.py`.
- No policy/eval behavior changed.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `143bc9739875f6c2e047912d39db5097b7c6a108`
- implementation_commit: pending
- remote_commit/status: l401 eval code at detached `ea21066cb91a7bef36972f60f89996b62d6d09ac`; new diagnostic is local-only and not needed by eval wrapper.
- changed_files: `dextrah_lab/offline_dp_bc/diagnose_rgb_dp_offline_coherence.py`, `worklogs/franka-cube-grasp-prior/HANDOFF_C.md`

Command / Job:
- command: pending `sbatch cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh` with epoch12 checkpoint, exact demo reset ep183, `ACTION_CHUNK_STEPS=8`, `NUM_ACTION_SAMPLES=8`, `POLICY_SAMPLE_SEED=42`, video enabled.
- success condition: exact ep183 reset lifts cube / nonzero success; if it still fails, inspect video and compare to offline row diagnostics before changing data/model.

Result:
- status: launching

Analysis:
- Previous epoch12 chunk1 evals failed exact ep183 and default seed42 with zero success. Exact video shows gripper near cube, closes/pushes slightly off-axis, then retreats upward with gripper closed.
- Offline diagnostic report: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/diagnostics/rgb_offline_coherence_epoch12_ep183_20260612_210940/rgb_offline_coherence_report.md`.
- Exact ep183 row 43546 first action label roughly matches; row 43626/step80 still align/open label but policy predicts gripper close.

Next:
- Launch and monitor the chunked averaged exact eval, fetch metrics/video, then decide between inference tuning, adding non-object phase/progress/history, or retraining with better normal-reset data.

## 2026-06-12T21:23:42-07:00 - RGB epoch12 eval result and seed42 normal-reset data gate

Goal:
- Close out the RGB epoch12 chunked averaged eval and inspect the seed42 normal-reset RGB relabel job before any more training.

Hypothesis:
- If the epoch12 RGB checkpoint failure is mostly inference-noise driven, chunked averaged inference should recover exact ep183. If not, the seed42 relabel job should tell us whether normal-reset support data is broad enough for the next RGB training round.

Change:
- No eval/policy source changes after the offline RGB coherence diagnostic.
- Fetched and visualized the completed seed42 normal-reset RGB relabel set.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `143bc9739875f6c2e047912d39db5097b7c6a108`
- implementation_commit: pending
- changed_files: `dextrah_lab/offline_dp_bc/diagnose_rgb_dp_offline_coherence.py`, `worklogs/franka-cube-grasp-prior/HANDOFF_C.md`
- unrelated_untracked: `dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py` existed before this pass and was not touched.

Command / Job:
- eval job: `1028823`, run `franka_cube_rgb_dp_scale183_plus_normal25x2_epoch12_ep183_exact_chunk8_s8_seed42_video_20260612_2114`, checkpoint `rgb_scale264_accepted183_plus_normalreset25x2_20260612_2038_epoch12/latest.ckpt`, `ACTION_CHUNK_STEPS=8`, `NUM_ACTION_SAMPLES=8`, `POLICY_SAMPLE_SEED=42`, exact cube reset ep183, video enabled.
- data job: `1028819`, run `franka_cube_contact_relabel_scale264_normalreset_rgb_ep000_031_seed42_high30_20260612_2059`, normal reset (`reset_joint_blend_alpha=0`, `reset_cube_pos_blend_alpha=0`), RGB obs 96x96, episodes 0-31.

Result:
- eval status: failed behaviorally, process completed. `window_success_rate=0.0`, `final_success_rate=0.0`, max lift `0.00555` m, min finger-center-to-cube `0.05571` m, final cube around `[-0.4087, -0.1634, 0.776]`.
- eval video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_rgb_dp_scale183_plus_normal25x2_epoch12_ep183_exact_chunk8_s8_seed42_video_20260612_2114/videos/franka-cube-rgb-dp-scale183-normalx2-epoch12-ep183-exact-chunk8-s8-seed42-step-0.mp4`
- seed42 data status: Slurm `COMPLETED 0:0`, relabel-set verdict `FAIL: at least one contact-aware rollout failed the hard relabel gate; do not train DP on this set.`
- accepted seed42 RGB subset: `3/32` rollouts, `948` transitions, rollouts `ep06s260_a0_center_high30`, `ep22s260_a0_center_high30`, `ep26s260_a0_center_high30`.
- accepted lift metrics: final/max lift about `0.1366`, `0.1363`, and `0.1362` m; final finger-center-to-cube about `0.0586`, `0.0598`, and `0.0491` m.
- accepted RGB NPZ:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_rgb_normalreset_scale264_seed42_20260612_2059/franka_cube_contact_relabel_scale264_normalreset_rgb_ep000_031_seed42_high30_20260612_2059/contact_relabel_set_accepted_rgb.npz`
- accepted RGB visualization:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_rgb_normalreset_scale264_seed42_20260612_2059/franka_cube_contact_relabel_scale264_normalreset_rgb_ep000_031_seed42_high30_20260612_2059/accepted_rgb_visualization/seed42_accepted_rgb_three_rollouts.mp4`
- accepted RGB contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_rgb_normalreset_scale264_seed42_20260612_2059/franka_cube_contact_relabel_scale264_normalreset_rgb_ep000_031_seed42_high30_20260612_2059/accepted_rgb_visualization/seed42_accepted_rgb_contact_sheet.jpg`

Analysis:
- Lowdim already met the user's current bar: a trained lowdim policy produced success on a slightly shifted cube state, so no more lowdim polishing is needed before RGB.
- RGB I/O still looks correct: one-demo RGB overfit succeeds, the offline coherence diagnostic matches labels reasonably on dataset histories, and the accepted seed42 RGB frames are visually sane.
- The mixed RGB epoch12 policy failure is not fixed by chunked averaged inference. The video shows the same off-axis close/push pattern as chunk1.
- The seed42 normal-reset relabel controller is too fragile for blind scaling: only `3/32` rollouts passed, while failed rollouts often reached near-contact but did not lift or drifted far after closing. This is a data coverage/controller robustness problem, not evidence that the RGB observation schema is broken.

Next:
- Do not retrain on the full seed42 relabel set. At most merge only `contact_relabel_set_accepted_rgb.npz`, likely with oversampling, as a small seed42 support addition.
- Next RGB iteration should either (a) generate more accepted normal-reset RGB support with better controller settings / broader seeds, or (b) add a non-privileged time/phase/progress signal to RGB `robot_state` and retrain with accepted183 plus accepted normal-reset data.
- No active l401 DEXTRAH jobs remain after this entry.

## 2026-06-12T21:33:00-07:00 - RGB 12D phase/progress implementation and dataset build

Goal:
- Reduce RGB close/lift timing ambiguity without reintroducing privileged cube state.

Hypothesis:
- The successful lowdim proof-of-life used phase/progress features. RGB currently discards `phase_ids`, so two-frame image/proprio history must infer when to close/lift from a fragile closed-loop state. Appending three contact-phase one-hot bits plus episode progress to the non-privileged robot state should improve timing while keeping object state out of policy inputs.

Change:
- `FrankaCubeRgbDataset` now has optional `append_phase_progress=true`; it appends `[phase_align_open, phase_close_hold, phase_lift, episode_progress]` from `phase_ids` and `episode_ends` to `robot_state`.
- `eval_franka_cube_rgb_dp_policy.py` now has matching `--append_phase_progress` and dataset-backed runtime schedule flags.
- `cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh` forwards phase/progress eval flags.
- Built a new training dataset from `accepted183+normalreset25x2` plus the seed42 accepted RGB subset repeated `8x`.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `143bc9739875f6c2e047912d39db5097b7c6a108`
- implementation_commit: pending
- changed_files: `dextrah_lab/offline_dp_bc/dp_dataset.py`, `dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py`, `cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`, `dextrah_lab/offline_dp_bc/diagnose_rgb_dp_offline_coherence.py`, `worklogs/franka-cube-grasp-prior/HANDOFF_C.md`
- unrelated_untracked: `dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py` remains unstaged/untouched.

Command / Job:
- local checks:
  - `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/dp_dataset.py dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py`
  - `bash -n cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`
  - `git diff --check -- dextrah_lab/offline_dp_bc/dp_dataset.py dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`
- dataset combine:
  `PYTHONPATH=$DEX $VENV -m dextrah_lab.offline_dp_bc.combine_contact_relabel_rgb_sets --input <accepted183_plus_normalreset25x2> --input <seed42_accepted_rgb> ... x8 --output <combined_seed42x8_rgb_96.npz> --report <combined_rgb_report.md>`

Result:
- local checks passed.
- augmented dataset loader smoke passed: `image=(16,3,96,96)`, `robot_state=(16,12)`, `action=(16,7)`.
- combined dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_rgb_scale264_accepted183_plus_normalreset25x2_plus_seed42x8_20260612_2128/franka_cube_scale264_contact_relabel_accepted183_plus_normalreset25x2_plus_seed42x8_rgb_96.npz`
- combined dataset size: `257` episodes, `67186` transitions, phase counts `0:10062`, `1:20560`, `2:36564`; raw stored `robot_state` remains 8D and becomes 12D only through the dataset adapter.

Analysis:
- This is intentionally not privileged: eval-time phase/progress is a clock/schedule from an RGB NPZ, not cube pose/velocity/contact state.
- The old 8D RGB path remains the default, so existing checkpoints/evals still work.

Next:
- Commit the implementation, train a 12D RGB checkpoint on the combined dataset, then evaluate exact ep183 and a slight cube offset using `APPEND_PHASE_PROGRESS=True` with the same phase schedule.
