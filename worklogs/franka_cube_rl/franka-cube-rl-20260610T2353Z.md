# Franka Cube RL Debug Worklog - franka-cube-rl-20260610T2353Z

Owned worklog for continuing the Franka cube RL task from DEXTRAH stop-state
commit `d7ff3d0c4e293aee915d0a8780beb1c17b1a91c8`.

## 2026-06-10 16:53 PDT - Handoff Intake And Isolation

Goal:
- Continue the previous agent's Franka cube RL debugging until the task works,
  while preserving the dirty main checkout and existing worktrees.

Hypothesis:
- The validated Franka reward-gate fix may make PPO learnable, but first the
  Franka cube environment and reward must be audited against the known-good
  KUKA cube task so only robot-specific differences remain.

Change:
- Created isolated local worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`.
- Created branch:
  `codex/franka-cube-rl-debug/franka-cube-rl-20260610T2353Z`.
- Added this owned worklog.

Version Control:
- agent_id: `franka-cube-rl-20260610T2353Z`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- worklog: `worklogs/franka_cube_rl/franka-cube-rl-20260610T2353Z.md`
- branch: `codex/franka-cube-rl-debug/franka-cube-rl-20260610T2353Z`
- base_commit: `d7ff3d0c4e293aee915d0a8780beb1c17b1a91c8`
- implementation_commit: pending
- changed_files: `worklogs/franka_cube_rl/franka-cube-rl-20260610T2353Z.md`
- remote_commit/status: pending; no remote source update yet.

Command / Job:
- command: `git worktree add -b codex/franka-cube-rl-debug/franka-cube-rl-20260610T2353Z /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z origin/codex/dextrah-cluster-dev`
- job_id: n/a
- artifacts: n/a

Current State:
- Franka cube reward geometry validation passed at
  `b268d76034ecff0ea765a456cada8f0364280aae`.
- Existing stalled baseline:
  `franka_cube_ppo_20260610_1558`, job `28954774`, canceled after metrics
  showed near-zero lift/success.
- Inherited teacher job `28942245` requeued at `2026-06-10 16:46:05 PDT`,
  wrote `last_dextrah_lstm_ep_13500_rew_577.9305.pth`, refreshed all eight
  runtime sidecars, and was initially `PENDING` with reason
  `job_requeued_in_held_state`.

Acceptance Criteria:
- Code audit finds and documents all meaningful non-robot differences between
  `Dextrah-Franka-Cube-Grasp` and the known-good `Dextrah-Cube-Grasp`.
- Cluster validation passes after any parity/reward changes.
- Bounded PPO produces real lift progress, then checkpoint eval confirms
  nonzero success with cube lift above the `0.12 m` success threshold.
- Final evidence includes logs, scalar metrics, checkpoints, and a rendered
  rollout video inspection.

Next:
- Audit Franka cube env/config/reward/training wrapper against the KUKA cube
  implementation before launching PPO.

## 2026-06-10 16:58 PDT - KUKA-Parity Reward Patch

Goal:
- Remove non-robot-specific deviations between `Dextrah-Franka-Cube-Grasp` and
  the known-good `Dextrah-Cube-Grasp` task before launching another PPO run.

Hypothesis:
- The previous Franka cube PPO stalled partly because the Franka reward had
  drifted into star-kitting-style phase/action shaping. A KUKA-shaped cube
  reward should make the comparison cleaner: distance/enclosure/lift/height/XY
  stability/success plus robot-specific gripper regularization.

Audit Findings:
- Core cube geometry, lift target, success lift threshold, XY tolerance,
  spawn randomization, cube friction, density, solver settings, and contact
  offsets already match the KUKA cube task except for Franka table coordinates.
- Franka success hand tolerance remains robot-specific at `0.20 m`; the prior
  validator measured valid Franka lifted geometry around `0.17-0.18 m`.
- The main deviation was reward design:
  - KUKA cube uses `approach`, `enclosure`, `lift`, `height_tracking`,
    `xy_stability`, `success_bonus`, `finger_curl_reg`, and `action_penalty`.
  - Franka cube used extra `finger_approach`, `grasp_ready`, `closed_grasp`,
    `close_action`, `lift_action`, `prelift_move`, `close_far`, `open_near`,
    and `ungrasped_lift` terms.
- The stalled baseline `franka_cube_ppo_20260610_1558` improved grasp/close
  shaping while mean lift stayed near `1-2 mm` and mean vertical action was
  negative, consistent with a shaping/local-minimum problem.

Change:
- Replaced the Franka cube reward with a KUKA-cube-shaped reward:
  - `approach_reward = approach_weight * exp(-approach_sharpness * mean_two_finger_dist)`;
  - `enclosure_reward = enclosure_weight * exp(-enclosure_sharpness * max_two_finger_dist)`;
  - `lift_reward = lift_weight * lift_progress * (0.2 + 0.8 * near_gate)`;
  - `height_tracking`, `xy_stability`, and `success_bonus` match KUKA form;
  - Franka-specific gripper width regularizer replaces Allegro curl regularizer.
- Reset Franka cube reward weights to KUKA cube weights:
  `lift_weight=10`, `success_bonus=15`, `action_penalty=-0.0005`, etc.
- Set Franka cube PPO default learning rate to KUKA's `2e-4`.
- Kept `NUM_ENVS=2048` and `HORIZON_LENGTH=64` so the effective rollout sample
  count matches KUKA's `4096 x 32` despite the heavier Franka environment.
- Updated validation checks to expect KUKA-shaped reward terms.

Version Control:
- agent_id: `franka-cube-rl-20260610T2353Z`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- branch: `codex/franka-cube-rl-debug/franka-cube-rl-20260610T2353Z`
- base_commit: `d7ff3d0c4e293aee915d0a8780beb1c17b1a91c8`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_rewards.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  - `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/agents/rl_games_ppo_franka_cube_grasp_cfg.yaml`
  - `cluster/sbatch_train_teacher_8gpu.sh`
  - `worklogs/franka_cube_rl/franka-cube-rl-20260610T2353Z.md`

Validation:
- `python3 -m py_compile` passed for Franka cube reward/config/env and
  validator.
- `bash -n` passed for training, validation, and Franka cube eval wrappers.
- stale old-reward-term grep returned no matches in Franka cube code/validator.
- `git diff --check` passed.

Teacher Job Note:
- Inherited teacher job requeue is no longer held. New running job is `28955904`
  on `batch-block5-03072` as of `2026-06-10 16:58 PDT`.

Next:
- Commit this patch, deploy the exact commit to an isolated A100 worktree, run
  the Franka cube cluster validator, then launch bounded PPO only if validation
  passes.

## 2026-06-10 17:01 PDT - KUKA-Parity Cluster Validation Launch Intent

Goal:
- Run the Franka cube cluster validator from the isolated A100 worktree after
  the KUKA-parity reward patch.

Hypothesis:
- If the reward signature, config, and validator were updated consistently, the
  same validation surface that accepted `b268d76` should pass with the simpler
  KUKA-shaped reward and report positive approach/enclosure/lift/success
  checks at the measured Franka success geometry.

Version Control:
- agent_id: `franka-cube-rl-20260610T2353Z`
- local_commit_before_launch_intent: `ce84d85f5fb1e2c510ddbab0e809afa48084a232`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- remote_commit_before_launch_intent: `ce84d85f5fb1e2c510ddbab0e809afa48084a232`

Command / Job:
- planned command:
  `RUN_NAME=franka_cube_validate_kukaparity_20260610_1701 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=49 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: pending
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_kukaparity_20260610_1701`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_<jobid>.out`

Validation Before Launch:
- local `py_compile`, `bash -n`, stale-term grep, and `git diff --check` passed.

Next:
- Commit/push this launch intent, update the isolated A100 worktree to the new
  exact commit, submit the validation job, then monitor logs and artifacts.

## 2026-06-10 17:03 PDT - KUKA-Parity Cluster Validation Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_kukaparity_20260610_1701 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=49 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28956047`
- code_commit:
  `5830cc1e380f1ac721111f850cf35ce5c1e8cc1e`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_kukaparity_20260610_1701`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28956047.out`

Next:
- Monitor job `28956047`; inspect log, `metrics.json`, and validation video
  before launching PPO.

## 2026-06-10 17:05 PDT - KUKA-Parity Validation Threshold Fix

Command / Job:
- validation job_id: `28956047`
- run_name: `franka_cube_validate_kukaparity_20260610_1701`
- code_commit: `5830cc1e380f1ac721111f850cf35ce5c1e8cc1e`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28956047.out`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_kukaparity_20260610_1701`

Result:
- status: failed validator thresholds only.
- all environment, observation, success-predicate, reward-sign, rollout
  finite, workspace, and video-writing checks reached execution.
- failed checks:
  - `reward_actual_lift_dominates_no_lift_grasp`: lifted reward `9.6889`,
    no-lift reward `2.5724`, ratio about `3.77`; old validator demanded `10x`.
  - `reward_lift_intent_without_lift_is_capped`: lift-intent reward `2.5719`,
    lifted reward `9.6889`, fraction about `0.265`; old validator demanded
    `<0.15`.

Analysis:
- These two thresholds were remnants of the previous high-scale Franka reward,
  where `lift_weight=180` and success bonus was `80`.
- The KUKA cube formula itself would not satisfy a `10x` or `0.15` threshold at
  the same near-grasp state because no-lift approach/enclosure/XY rewards remain
  meaningful.
- This is not evidence against the KUKA-parity reward patch; it is a validator
  scale mismatch.

Change:
- Relaxed validator checks to KUKA-compatible values:
  - actual lift must exceed no-lift by `3.0x`;
  - lift intent without actual lift must stay below `0.35x` lifted reward.

Validation:
- local `python3 -m py_compile` passed for validator and reward helper.
- local `git diff --check` passed.

Next:
- Commit/push this validator-only fix, update the isolated A100 worktree, and
  rerun the same validation.

## 2026-06-10 17:06 PDT - KUKA-Parity Cluster Validation Relaunch

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_kukaparity2_20260610_1706 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=50 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28956084`
- code_commit:
  `287e818e26c5775074ec6471325c94430e6bf03e`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_kukaparity2_20260610_1706`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28956084.out`

Next:
- Monitor job `28956084`; inspect log, metrics, and video before launching PPO.

## 2026-06-10 17:09 PDT - KUKA-Parity Validation Passed

Command / Job:
- job_id: `28956084`
- run_name: `franka_cube_validate_kukaparity2_20260610_1706`
- code_commit:
  `287e818e26c5775074ec6471325c94430e6bf03e`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_kukaparity2_20260610_1706`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28956084.out`
- local artifact mirror:
  `cluster_results/a1002/validations/franka_cube_validate_kukaparity2_20260610_1706`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/validations/franka_cube_validate_kukaparity2_20260610_1706/videos/franka-cube-validate-step-0.mp4`

Result:
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:32`.
- validator status: passed.
- checks: `19 / 19` passed.
- video: present and decodable, `1280x720`, `159` frames, `2.65s`.
- visual inspection: contact sheet shows the cube on the tabletop and the
  Franka gripper approaching in the expected task frame; no obvious placement
  or rendering issue.

Key Metrics:
- `reward_enclosure_prefers_both_fingers_near`: balanced `2.5711`,
  imbalanced `1.9457`.
- `reward_actual_lift_dominates_no_lift_grasp`: lifted `9.6889`, no-lift
  `2.5724`, threshold floor `3.0x`.
- `reward_lift_intent_without_lift_is_capped`: lift-intent `2.5719`, lifted
  `9.6889`, cap `0.35x`.
- `success_predicate_accepts_lifted_cube_near_gripper`: success rate `1.0`,
  lift height `0.13m`, hand mean distance `0.1822m`, hand max distance
  `0.1832m`.
- rollout: `160 / 160` steps completed, final success `0.0` as expected for
  the non-solving scripted rollout, max mean lift `0.03235m`, cube stayed in
  workspace.

Decision:
- The Franka cube environment and reward surface are now validated against the
  KUKA-cube-shaped design, with only robot/table geometry differences retained.
- Proceed to bounded PPO from the isolated worktree with `AUTO_RESUME=False` to
  avoid inheriting the prior stalled checkpoint/run state.

## 2026-06-10 17:10 PDT - Bounded KUKA-Parity PPO Launch Intent

Goal:
- Launch a bounded Franka cube PPO run from the validated KUKA-parity reward
  patch and check whether it escapes the previous stalled behavior
  (`~1-2mm` lift, success near zero, downward mean z action).

Version Control:
- local commit before launch intent:
  `fad70b4c856da040e37b68f793157c9ef25ee44a`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- remote commit before launch intent:
  `fad70b4c856da040e37b68f793157c9ef25ee44a`

Planned Command:
- run_name: `franka_cube_kukaparity_ppo_20260610_1710`
- command:
  `TASK=Dextrah-Franka-Cube-Grasp FULL_EXPERIMENT_NAME=franka_cube_kukaparity_ppo_20260610_1710 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=2048 MAX_ITERATIONS=600 USE_CUDA_GRAPH=False CUBE_SPAWN_XY_RANDOMIZATION=0.08 AUTO_RESUME=False SELF_RELAUNCH=False sbatch --parsable cluster/sbatch_train_teacher_8gpu.sh`

Expected Artifacts:
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_<jobid>.out`
- training root:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/franka_cube_grasp/franka_cube_kukaparity_ppo_20260610_1710`

Monitoring Criteria:
- confirm no `--auto_resume` or inherited checkpoint is used.
- watch `cube_lift_height`, `cube_has_lifted_rate`, `cube_success_rate`,
  `in_success_region`, `cube_action_z`, `cube_action_up/down`,
  `cube_enclosure_reward`, `cube_lift_reward`, PPO loss/KL/entropy, and
  checkpoint creation.
- cancel and patch rather than let it run to walltime if it reproduces the old
  stalled signature after enough epochs for a clear trend.

## 2026-06-10 17:12 PDT - Bounded KUKA-Parity PPO Submitted

Command / Job:
- command:
  `TASK=Dextrah-Franka-Cube-Grasp FULL_EXPERIMENT_NAME=franka_cube_kukaparity_ppo_20260610_1710 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=2048 MAX_ITERATIONS=600 USE_CUDA_GRAPH=False CUBE_SPAWN_XY_RANDOMIZATION=0.08 AUTO_RESUME=False SELF_RELAUNCH=False sbatch --parsable cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `28956257`
- code_commit:
  `ec9d08d2db958073b616aed135827d6ae422f34f`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28956257.out`
- expected training root:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/franka_cube_grasp/franka_cube_kukaparity_ppo_20260610_1710`

Next:
- Monitor scheduler/log startup; confirm `AUTO_RESUME=False` prevents
  inherited checkpoint selection; inspect scalar trends and checkpoints before
  deciding whether to continue, cancel, patch, or evaluate.

## 2026-06-10 17:20 PDT - PPO Early Trend and Epoch-100 Eval Launch

Training Job:
- job_id: `28956257`
- actual training root:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_kukaparity_ppo_20260610_1710`
- note: the root includes `dextrah_franka_cube_grasp`; the earlier launch
  intent used the shorter expected path.

Early Training Result:
- startup confirmed fresh run: log shows `AUTO_RESUME=False`, empty
  `CHECKPOINT`, and epochs starting from `1/600`.
- checkpoints written:
  - epoch 25 reward `469.86267`
  - epoch 50 reward `746.7792`
  - epoch 75 reward `933.0838`
  - epoch 100 reward `813.57214`
- event scalars through epoch 77 show approach/enclosure improving and gripper
  close action increasing, but lift/success remain poor:
  - `cube_lift_height/iter`: max `0.00753m`, latest `0.00156m`
  - `cube_has_lifted_rate/iter`: max `0.01416`, latest `0.00391`
  - `cube_success_rate/iter`: max `0.000488`, latest `0.0`
  - `cube_action_z/iter`: latest `-0.0733`, with down action exceeding up
  - `cube_gripper_close_action/iter`: latest `0.6855`

Analysis:
- The KUKA-parity reward is learning approach and close behavior, but by
  epoch ~100 it still resembles the previous stall signature: little actual
  lift, essentially zero success, and net downward z action.
- Keep PPO running to the 150-200 epoch range for a clear trend, while
  evaluating the epoch-100 checkpoint to capture deterministic behavior/video.

Eval Command / Job:
- command:
  `RUN_NAME=franka_cube_kukaparity_eval_ep100_20260610_1720 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z CHECKPOINT=/results/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_kukaparity_ppo_20260610_1710/nn/last_dextrah_franka_cube_grasp_ep_100_rew_813.57214.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 CAPTURE_VIDEO=True DETERMINISTIC=True USE_CUDA_GRAPH=False CUBE_SPAWN_XY_RANDOMIZATION=0.08 SEED=101 sbatch --parsable cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- eval_job_id: `28956573`
- expected eval run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_kukaparity_eval_ep100_20260610_1720`
- expected eval log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_28956573.out`

## 2026-06-10 17:24 PDT - KUKA-Only PPO Canceled After Stall

Training Job:
- job_id: `28956257`
- status: canceled intentionally after epoch ~193.
- reason: the run reproduced the prior stall signature despite the validated
  KUKA-shaped reward surface.

Training Metrics:
- event scalars through epoch `191`:
  - reward latest `970.6882`, max `985.5291`
  - `cube_lift_height/iter`: latest `0.00264m`, max `0.00753m`
  - `cube_has_lifted_rate/iter`: latest `0.00537`, max `0.01416`
  - `cube_success_rate/iter`: latest `0.0`, max `0.000488`
  - `cube_action_z/iter`: latest `-0.2232`, last-10 mean `-0.2038`
  - `cube_action_down/iter`: latest `0.4688`, last-10 mean `0.4555`
  - `cube_action_up/iter`: latest `0.2456`, last-10 mean `0.2517`
  - `cube_gripper_close_action/iter`: latest `0.5899`, last-10 mean `0.6172`
  - `cube_ee_to_cube_dist/iter`: latest `0.1297m`
  - `cube_max_finger_to_cube_dist/iter`: latest `0.1362m`
- checkpoint rewards rose, but the policy optimized approach/close without
  discovering upward lift.

Eval Job:
- job_id: `28956573`
- checkpoint:
  `/results/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_kukaparity_ppo_20260610_1710/nn/last_dextrah_franka_cube_grasp_ep_100_rew_813.57214.pth`
- status: completed, exit `0:0`.
- local artifacts:
  `cluster_results/a1002/evals/franka_cube_kukaparity_eval_ep100_20260610_1720`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/evals/franka_cube_kukaparity_eval_ep100_20260610_1720/videos/franka-cube-grasp-eval-step-0.mp4`
- eval summary:
  - `num_envs=4`, `num_steps_completed=600`
  - `success_rate_mean=0.0`, `success_rate_final=0.0`
  - `cube_lift_height`: final `0.0m`, mean `0.00063m`, max `0.04455m`
    at step 5 only, before the policy settles.
  - `has_lifted_cube`: max `0.0`
  - `gripper_width`: mean `0.0400m`, min `0.0272m`
  - `hand_to_cube_mean_dist`: mean `0.1379m`, min `0.1142m`
- visual note: the default eval camera produced a valid `1280x720`, 600-frame
  MP4 but framed the wrist/table poorly for diagnosing cube contact. Use a
  closer camera on the next eval.

Decision:
- The environment/reward parity audit was still useful: it isolated the failure
  to Franka exploration/control rather than a gross KUKA task mismatch.
- Patch next by preserving the KUKA state rewards and adding small,
  tightly-gated Franka-specific close/up action shaping so the parallel gripper
  receives a gradient toward closing near the cube and lifting only after a
  near/enclosed/closed pre-grasp.

## 2026-06-10 17:25 PDT - Gated Franka Lift/Close Shaping Patch

Change:
- Preserved the KUKA-shaped state reward components:
  `approach`, `enclosure`, actual `lift`, height tracking, XY stability,
  success bonus, gripper width regularizer, and action penalty.
- Added three Franka-specific action terms gated by pre-lift,
  near/enclosed/balanced fingers, closed gripper, and XY stability:
  - `cube_close_action_reward`, weight `0.3`
  - `cube_lift_action_reward`, weight `1.0`
  - `cube_descend_action_penalty`, weight `-1.0`
- Added scalar logging for the three new terms.
- Updated the Franka cube validator to check:
  - intent-only lift remains capped below actual-lift reward;
  - downward z is penalized when lift-ready;
  - lift action reward is near-gated and not available far from the cube;
  - success-geometry reward checks include the new tuple layout.

Files:
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_rewards.py`
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`

Local Validation:
- `python3 -m py_compile ...` passed for the reward, config, env, and
  validator files.
- `git diff --check` passed.
- A direct local reward probe was attempted but local Python lacks `torch`;
  cluster validation will execute the reward checks inside the Isaac
  environment.

Next:
- Commit/push this patch, update the isolated A100 worktree, rerun the Franka
  cube validator, and only then launch the next bounded PPO attempt.

## 2026-06-10 17:26 PDT - Gated Lift-Action Validation Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_liftaction_20260610_1726 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=52 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28957056`
- code_commit:
  `71800a88bc9befe7c40412609ed811526a626e51`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_liftaction_20260610_1726`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957056.out`

Next:
- Monitor validator completion and inspect metrics/video before launching the
  second bounded PPO attempt.

## 2026-06-10 17:29 PDT - Gated Lift-Action Validation Passed

Command / Job:
- job_id: `28957056`
- run_name: `franka_cube_validate_liftaction_20260610_1726`
- code_commit:
  `71800a88bc9befe7c40412609ed811526a626e51`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_liftaction_20260610_1726`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957056.out`
- local artifact mirror:
  `cluster_results/a1002/validations/franka_cube_validate_liftaction_20260610_1726`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/validations/franka_cube_validate_liftaction_20260610_1726/videos/franka-cube-validate-step-0.mp4`

Result:
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:16`.
- validator status: passed.
- checks: `21 / 21` passed.
- video: present and decodable, `1280x720`, `159` frames, `2.65s`.
- visual inspection: contact sheet shows expected Franka/table/cube placement
  and no rendering/frame issue.

Key Metrics:
- `reward_lift_intent_without_lift_is_capped`: lift-intent `3.7950`,
  lifted `9.6889`, cap `0.45x`.
- `reward_penalizes_descend_when_lift_ready`: closed `2.8724`, descend
  `1.9488`.
- `reward_lift_action_is_near_gated`: near lift intent `3.7950`, far lift
  intent `1.4111`.
- `success_predicate_accepts_lifted_cube_near_gripper`: success rate `1.0`,
  lift `0.13m`, hand mean distance `0.1722m`, hand max distance `0.1724m`.
- rollout: `160 / 160` steps completed, final success `0.0` for the scripted
  rollout, max mean lift `0.0223m`, cube stayed in workspace.

Decision:
- Proceed to a second bounded PPO attempt from the gated lift-action patch.
- Monitor the new scalar terms directly:
  `cube_close_action_reward`, `cube_lift_action_reward`, and
  `cube_descend_action_penalty`, in addition to lift/success/z-action.

## 2026-06-10 17:30 PDT - Gated Lift-Action PPO Submitted

Command / Job:
- command:
  `TASK=Dextrah-Franka-Cube-Grasp FULL_EXPERIMENT_NAME=franka_cube_liftaction_ppo_20260610_1730 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=2048 MAX_ITERATIONS=600 USE_CUDA_GRAPH=False CUBE_SPAWN_XY_RANDOMIZATION=0.08 AUTO_RESUME=False SELF_RELAUNCH=False sbatch --parsable cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `28957106`
- code_commit:
  `295a1675acd30a4157a4b6ca55114ca81ca8d2bf`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28957106.out`
- expected training root:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_liftaction_ppo_20260610_1730`

Monitoring Criteria:
- confirm fresh run and no inherited checkpoint.
- compare against the canceled KUKA-only run:
  - z-action should not drift strongly negative by epoch ~100-200;
  - `cube_lift_height` and `cube_has_lifted_rate` should exceed the previous
    maxes (`0.00753m`, `0.01416`);
  - success should move above zero before committing to a long run.

## 2026-06-10 17:35 PDT - PPO Attempt 2 Canceled for Table Penetration Audit

User Artifact Observation:
- User inspected the new artifacts and reported that the Franka hand went
  directly to the table and the gripper tip penetrated the table.

Action:
- Canceled PPO attempt 2 (`28957106`) after `00:02:07` elapsed, at about epoch
  12, before spending more GPU time.
- Scheduler state:
  `CANCELLED by 158351`; batch step exit `15:0`.

Analysis:
- This is consistent with the previous eval/scalars: the policy can optimize
  approach/close rewards while moving downward toward the tabletop instead of
  setting up a valid side grasp.
- The Franka cube env did not expose a numeric table-clearance metric in
  training/eval artifacts, so invalid hand/table contact could be visible in
  video without being flagged in JSON.
- The likely root cause is reward geometry: distance-to-cube-center and close
  action shaping did not include a table-clearance constraint for the parallel
  gripper. This differs from the KUKA/Allegro hand because the Franka gripper
  can exploit tabletop contact while still reducing finger/cube distance.

Patch:
- Added `finger_table_clearance` and `finger_table_clearance_violation` buffers
  to the Franka cube env.
- Added `cube_table_clearance_penalty` to the reward, with margin
  `0.025m` and weight `-3.0`.
- Added conservative termination only when measured finger body clearance drops
  below the tabletop by more than `0.002m`.
- Rejected success unless finger table clearance is at least `0.005m`.
- Added training/eval scalar metrics for clearance and violation.
- Updated `eval_rollout.py` so checkpoint eval JSON includes these metrics.
- Updated the Franka cube validator reward checks and rollout summary to cover
  low-clearance penalties and min rollout clearance.

Local Validation:
- `python3 -m py_compile` passed for the reward, config, env, validator, and
  eval files.
- `git diff --check` passed.

Next:
- Commit/push, update the A100 worktree, rerun the Franka cube validator, and
  evaluate the previous epoch-100 checkpoint with the new clearance metrics and
  a better camera before launching any further PPO.

## 2026-06-10 17:36 PDT - Table-Clearance Validation Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_tableclear_20260610_1736 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=53 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28957205`
- code_commit:
  `af5da520c9d99d8efd2d0eb0faacce59a1e94c45`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_tableclear_20260610_1736`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957205.out`

Next:
- Monitor validator completion; if it passes, run a checkpoint eval with
  clearer camera framing and inspect `finger_table_clearance` metrics.

## 2026-06-10 17:43 PDT - GraspGenX Franka Panda Asset Audit

User Follow-Up:
- User asked to verify whether GraspGenX `franka_panda` gripper-description
  assets exist anywhere and whether they are corrupted/incomplete, because bad
  selected grasps could come from bad gripper geometry regardless of simulator.

Checked Locations:
- Local GraspGenX checkout:
  `/home/lzha/code/graspgenx/ext/gripper_descriptions/gripper_descriptions/assets/x_grippers/franka_panda`
- Shared cluster asset root used by GraspGenX jobs:
  `/lustre/fsw/portfolios/nvr/users/lzha/assets/gripper_descriptions_full/gripper_descriptions/assets/x_grippers/franka_panda`
- Local and shared result trees for cached copies of `coll_mesh.obj`,
  `vis_mesh.obj`, `tsdf.npy`, `hand.stl`, `hand.dae`, and `finger.dae`.

Result:
- The asset directory exists in both local and shared locations, and
  `config.json`, `points.json`, `proc_gripper_only_pointnet_vae_repr.json`,
  `gripper.urdf`, and `gripper_spherical_dof.urdf` parse successfully.
- The required LFS geometry/TSDF files are missing or only pointer stubs:
  - `coll_mesh.obj`: missing locally and on shared assets.
  - `vis_mesh.obj`: missing locally and on shared assets.
  - `tsdf.npy`: missing locally and on shared assets.
  - `meshes/collision/hand.stl`: missing locally; shared copy is a Git LFS
    pointer stub (`130` bytes), not the real `10084` byte STL.
  - `meshes/visual/finger.dae`: missing locally; shared copy is a Git LFS
    pointer stub (`130` bytes), not the real `51239` byte DAE.
  - `meshes/visual/hand.dae`: missing locally; shared copy is a Git LFS
    pointer stub (`131` bytes), not the real `549239` byte DAE.
- `git lfs ls-files -l` confirms all six files are expected LFS objects.
- The local and shared LFS object stores do not contain those six OIDs.
- `git lfs pull --include='gripper_descriptions/assets/x_grippers/franka_panda/**'`
  fails both locally and on shared storage with:
  `This repository exceeded its LFS budget.`

Impact:
- Confirmed: GraspGenX `franka_panda` gripper-description assets are
  incomplete/corrupted in the checkouts currently available to local and A100
  runs.
- `graspgenx.x_grippers.get_gripper_info()` silently falls back to dummy
  collision mesh, dummy visual mesh, and zero TSDF when those files are missing,
  so GraspGenX-generated Franka grasps can be geometrically degraded even if
  the simulator is correct.
- The Franka cube RL environment does not import GraspGenX or
  `gripper_descriptions`; DEXTRAH hits are in the separate Franka star
  GraspGenX/cuRobo planner. The table penetration found by the cube validator
  is therefore still an Isaac Lab robot/table geometry issue, not explained by
  GraspGenX assets alone.

Decision:
- Treat GraspGenX Franka grasp generation as externally asset-blocked until a
  valid `franka_panda` LFS asset copy is provided or the upstream LFS quota is
  restored.
- Continue the Franka cube RL path by fixing the confirmed table-clearance
  failure in the Isaac Lab environment.

## 2026-06-10 17:45 PDT - Table-Clearance Validation Failed; Base Height Patch

Validation Result:
- job_id: `28957205`
- run_name: `franka_cube_validate_tableclear_20260610_1736`
- scheduler status: `FAILED`, exit `1:0`.
- local artifact mirror:
  `cluster_results/a1002/validations/franka_cube_validate_tableclear_20260610_1736`

Key Failure Metrics:
- `success_predicate_accepts_lifted_cube_near_gripper`: failed with
  `finger_table_clearance=-0.01856m` and `success_rate=0.0`.
- `reward_accepts_success_geometry_for_prelift_enclosure`: failed because
  table-clearance penalty saturated at `-3.0`.
- `reward_accepts_success_geometry_for_lift`: failed because the clearance
  gate zeroed the success bonus.
- scripted rollout: `min_mean_finger_table_clearance=-0.01125m`,
  `done_count=11`.

Diagnosis:
- The issue is present at reset/synthetic geometry, not only after learning:
  the inherited Franka star robot base (`robot_base_z=0.20`) places the cube
  task's default fingertips below the table surface.
- This matches the user's video observation that the gripper penetrates the
  table.

Patch:
- Rebuilt the inherited Franka robot cfg only for
  `DextrahFrankaCubeGraspEnvCfg` with `robot_base_z=0.25`.
- Left the shared Franka star-kitting task unchanged.
- Added a validator check `reset_fingers_clear_table` requiring reset
  fingertips to clear the configured `finger_table_clearance_margin`.

Local Validation:
- `python3 -m py_compile` passed for:
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
  - `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- `git diff --check` passed.

Next:
- Commit/push this patch, update the A100 worktree, and rerun the Franka cube
  table-clearance validator before launching any new PPO.

## 2026-06-10 17:48 PDT - Base-Clearance Validation Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_baseclear_20260610_1748 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=54 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28957434`
- code_commit:
  `0c9dcc10f048e4a641ffaf335fe532d60de29578`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_baseclear_20260610_1748`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957434.out`

Monitoring Criteria:
- `reset_fingers_clear_table` must pass with all envs above
  `finger_table_clearance_margin=0.025m`.
- The previous failing checks must recover:
  `success_predicate_accepts_lifted_cube_near_gripper`,
  `reward_accepts_success_geometry_for_prelift_enclosure`, and
  `reward_accepts_success_geometry_for_lift`.
- Scripted rollout should have non-negative mean finger/table clearance and no
  early terminations from table penetration.

## 2026-06-10 17:49 PDT - Base-Clearance Validation Import Failure

Result:
- job_id: `28957434`
- scheduler state: failed during environment import.
- root cause:
  `AttributeError: type object 'DextrahFrankaStarKittingEnvCfg' has no attribute 'robot_yaw_wxyz'`

Diagnosis:
- `python3 -m py_compile` was insufficient because Isaac Lab's `@configclass`
  transformation does not expose inherited config fields as plain class
  attributes during subclass class-body evaluation.

Patch:
- Restated the inherited Franka robot constants locally in
  `DextrahFrankaCubeGraspEnvCfg` before rebuilding the cube-specific robot cfg:
  `robot_yaw_wxyz`, `finger_effort_limit`, `finger_stiffness`, and
  `finger_damping`.

Next:
- Re-run static checks, commit/push, update the A100 worktree, and relaunch
  the base-clearance validator.

## 2026-06-10 17:51 PDT - Corrected Base-Clearance Validation Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_baseclear2_20260610_1751 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=55 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28957460`
- code_commit:
  `98abd69609128371a57c90b1a1130fe0aa6f7140`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_baseclear2_20260610_1751`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957460.out`

## 2026-06-10 17:53 PDT - Base-Clearance Validation Mostly Fixed, Margin Too Tight

Result:
- job_id: `28957460`
- scheduler status: `FAILED`, exit `1:0`, because validator `passed=false`.
- Environment import and scene creation succeeded with the corrected config.

Recovered:
- Reset table clearance is now positive:
  `finger_table_clearance_min=0.02708m`, `mean=0.04579m`.
- Scripted rollout has no early table-penetration terminations:
  `done_count=0`.
- Rollout mean clearance stays positive:
  `min_mean_finger_table_clearance=0.04579m`.
- Previous hard failures recovered:
  - `success_predicate_accepts_lifted_cube_near_gripper`: passed with
    `success_rate=1.0`.
  - `reward_accepts_success_geometry_for_lift`: passed with
    `success_bonus=15.0`.

Remaining Failure:
- `reward_accepts_success_geometry_for_prelift_enclosure` failed because the
  table-clearance penalty was still `-0.1426` in synthetic success geometry.
- Mean synthetic clearance was `0.02809m`, only barely above the
  `0.025m` reward margin, so some envs can still sit inside the margin.

Patch:
- Raised the cube-only Franka base height from `0.25` to `0.27`.
- Added min-clearance diagnostics to the synthetic success/reward predicate
  checks, not just mean clearance.

Next:
- Re-run static checks, commit/push, update A100, and relaunch the validator.

## 2026-06-10 17:54 PDT - Eval Launch Authorization Note

User Instruction:
- Once the remaining issues are fixed and the actual training is launched,
  periodically launch evals for the current training run without asking for
  additional permission.
- Fetch eval videos locally and visualize them with `viz-open`.

Operational Note:
- For future training loops in this worklog, checkpoint evals are pre-approved.
- Do not rely only on scheduler state or scalar logs; inspect fetched videos
  through the visualization viewer before deciding whether to continue,
  cancel, patch, or relaunch.

## 2026-06-10 17:55 PDT - Base-Clearance Validator Relaunched

Command / Job:
- command:
  `RUN_NAME=franka_cube_validate_baseclear3_20260610_1755 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=4 NUM_STEPS=160 CAPTURE_VIDEO=True SEED=56 sbatch --parsable cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: `28957493`
- code_commit:
  `009ea18a0e8d08e9a24724a48e81b3c42c63799d`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_validate_baseclear3_20260610_1755`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_cube_28957493.out`

## 2026-06-10 17:57 PDT - Base-Clearance Validation Passed

Result:
- job_id: `28957493`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:35`.
- validator status: passed.
- checks: `23 / 23` passed.
- local artifact mirror:
  `cluster_results/a1002/validations/franka_cube_validate_baseclear3_20260610_1755`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/validations/franka_cube_validate_baseclear3_20260610_1755/videos/franka-cube-validate-step-0.mp4`

Key Metrics:
- reset clearance: min `0.04555m`, mean `0.07267m`, required margin `0.025m`.
- synthetic success clearance: min `0.04213m`, mean `0.05418m`.
- synthetic prelift table-clearance penalty: `0.0`.
- rollout: `160 / 160` steps completed, `done_count=0`,
  `min_mean_finger_table_clearance=0.07267m`.
- video: valid `1280x720`, `159` frames, `2.65s`.

Visual Inspection:
- Contact sheet from the fetched MP4 shows the Franka hand above the tabletop
  throughout the scripted rollout; no visible fingertip/table penetration.

Decision:
- The table-penetration/root-geometry issue is fixed for the Franka cube task.
- Proceed to a fresh PPO attempt from commit `009ea18` and monitor clearance,
  lift, success, z-action, reward terms, and eval video artifacts.

## 2026-06-10 17:56 PDT - Base-Clearance PPO Submitted

Command / Job:
- command:
  `TASK=Dextrah-Franka-Cube-Grasp FULL_EXPERIMENT_NAME=franka_cube_baseclear_ppo_20260610_1756 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z NUM_ENVS=2048 MAX_ITERATIONS=600 USE_CUDA_GRAPH=False CUBE_SPAWN_XY_RANDOMIZATION=0.08 AUTO_RESUME=False SELF_RELAUNCH=False sbatch --parsable cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `28957528`
- code_commit:
  `b75fcdbf8df5331ee89f170b6b1b02a44bd6d745`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28957528.out`
- expected training root:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756`

Monitoring Criteria:
- confirm fresh run and no inherited checkpoint (`AUTO_RESUME=False`).
- track `cube_finger_table_clearance`, `cube_finger_table_clearance_violation`,
  `cube_lift_height`, `cube_has_lifted_rate`, `cube_success_rate`,
  `cube_action_z`, `cube_action_up/down`, and PPO loss/KL/entropy.
- launch checkpoint evals without asking once checkpoints appear; fetch eval
  videos locally and open them with `viz-open`.

## 2026-06-10 18:02 PDT - Base-Clearance PPO Reached First Checkpoints

Result:
- job_id: `28957528`
- scheduler status: `RUNNING`, elapsed about `6m27s` on `batch-block7-01305`.
- stdout confirms epoch progress through `107/600` with no traceback.
- checkpoints written:
  - `last_dextrah_franka_cube_grasp_ep_25_rew_1105.9012.pth`
  - `last_dextrah_franka_cube_grasp_ep_50_rew_1443.2318.pth`
  - `last_dextrah_franka_cube_grasp_ep_75_rew_1486.4724.pth`
  - `last_dextrah_franka_cube_grasp_ep_100_rew_1626.5775.pth`
  - `dextrah_franka_cube_grasp.pth` best checkpoint updated after epoch 100.

Operational Note:
- SSH polling briefly stalled because the local SSH agent blocked
  authentication; direct-key polling with
  `-o IdentityAgent=none -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519`
  restored access.

Next:
- Launch the first pre-approved deterministic eval from the current best
  checkpoint and inspect `metrics.json` plus the fetched MP4 through
  `viz-open`.

## 2026-06-10 18:03 PDT - Ep100 Best-Checkpoint Eval Submitted

Command / Job:
- command:
  `RUN_NAME=franka_cube_baseclear_eval_ep100_20260610_1802 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 PRINT_INTERVAL=20 SEED=101 CUBE_SPAWN_XY_RANDOMIZATION=0.08 sbatch --parsable cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `28957635`
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_28957635.out`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_baseclear_eval_ep100_20260610_1802`

Monitoring Criteria:
- `metrics.json` exists and reports 600 completed steps.
- Inspect success, reward, lift height, table clearance, gripper width, and
  done count.
- Fetch and open the video locally with `viz-open`; reject the run if the hand
  dives into the table, fails to approach the cube, or exhibits obvious physics
  abuse.

## 2026-06-10 18:05 PDT - Ep100 Eval Completed, No Lift

Result:
- job_id: `28957635`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:57`.
- local artifact mirror:
  `cluster_results/a1002/evals/franka_cube_baseclear_eval_ep100_20260610_1802`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/evals/franka_cube_baseclear_eval_ep100_20260610_1802/videos/franka-cube-grasp-eval-step-0.mp4`
- video metadata: `1280x720`, `600` frames, `10.0s`.

Metrics:
- `num_steps_completed=600`, `done_count=4`.
- success: mean `0.0`, final `0.0`, last-window mean `0.0`.
- cube lift: max `0.00072m`, final `0.0m`.
- has-lifted: `0.0`.
- finger table clearance: mean `0.08406m`, min `0.04847m`.
- clearance violation: `0.0`.
- gripper width: mean `0.00142m`, final `0.07531m`.
- finger-center-to-cube distance: mean `0.06954m`, final `0.14979m`.

Visual Inspection:
- The fetched MP4 is valid, but the contact sheet mostly shows floor/table leg
  rather than the cube workspace. This exposed an eval-camera bug: unlike the
  validator, `eval_rollout.py` did not offset the camera by the first rendered
  environment origin for vectorized evals.

Analysis:
- Table penetration remains fixed in both training scalars and eval metrics.
- The policy has learned approach/close behavior but not reliable lift by this
  checkpoint.
- The first eval video cannot be used for behavioral acceptance because the
  camera target is wrong for vectorized eval origin placement.

Next:
- Patch `eval_rollout.py` to offset camera eye/target by env 0 origin, commit
  it, deploy it to a separate remote eval worktree, and relaunch visual eval.

## 2026-06-10 18:07 PDT - Eval Camera Origin Patch

Change:
- Updated `dextrah_lab/rl_games/eval_rollout.py` so `_configure_eval_camera`
  adds `task_env.scene.env_origins[0]` to the requested camera eye/target after
  environment construction.
- This matches the validator behavior and should make vectorized eval videos
  show the table/cube workspace instead of the global origin.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`

Next:
- Commit/push the patch and launch the next eval from a separate remote
  worktree so the still-running PPO job's source checkout is not mutated.

## 2026-06-10 18:10 PDT - Camera-Fixed Eval Submitted

Command / Job:
- local commit: `185d31c24f4fa4b0115ba6a468013ab36a2c0091`
- push: pushed to
  `origin/codex/franka-cube-rl-debug/franka-cube-rl-20260610T2353Z`.
- remote deployment:
  - A100 host could not fetch GitHub directly (`Permission denied
    (publickey)`), so the commit was transferred as a Git bundle rather than
    rsyncing source files.
  - bundle:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-franka-evalfix-185d31c.bundle`
  - keepalive ref:
    `refs/keepalive/franka-cube-rl-evalfix-185d31c`
  - eval worktree:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z-evalfix`
  - remote commit: `185d31c24f4fa4b0115ba6a468013ab36a2c0091`
- command:
  `RUN_NAME=franka_cube_baseclear_eval_camfix_20260610_1810 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z-evalfix CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 PRINT_INTERVAL=20 SEED=102 CUBE_SPAWN_XY_RANDOMIZATION=0.08 sbatch --parsable cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `28957758`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_28957758.out`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_baseclear_eval_camfix_20260610_1810`

Monitoring Criteria:
- Confirm MP4 now frames the table/cube workspace.
- Use metrics and video to decide whether current PPO should continue or a
  reward/control-shaping patch is required.

## 2026-06-10 18:13 PDT - Camera-Fixed Eval Passed Lift Smoke, Grasp Still Rough

Result:
- job_id: `28957758`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:02:10`.
- local artifact mirror:
  `cluster_results/a1002/evals/franka_cube_baseclear_eval_camfix_20260610_1810`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/evals/franka_cube_baseclear_eval_camfix_20260610_1810/videos/franka-cube-grasp-eval-step-0.mp4`
- video metadata: `1280x720`, `600` frames, `10.0s`.

Metrics:
- `num_steps_completed=600`, `done_count=4`.
- success: mean `0.59125`, final `0.25`, last-window mean `0.735`,
  max `1.0`.
- cube lift height: mean `0.10386m`, max `0.16181m`, final `0.03344m`.
- has-lifted: mean `0.7925`, max `1.0`, final `0.25`.
- finger table clearance: mean `0.14464m`, min `0.05342m`.
- clearance violation: `0.0`.
- cube XY error: mean `0.04998m`, max `0.07621m`, inside the `0.08m`
  success tolerance at peak.

Visual Inspection:
- The camera patch worked; the MP4 now frames the cube/table workspace.
- The robot approaches the cube, lifts it above the table, and carries it
  without fingertip/table penetration.
- The grasp is not yet robust-looking: the cube rides high on/near the gripper
  fingers instead of appearing as a clean centered pinch, and some envs have
  reset by the final frame.

Decision:
- Do not patch reward/control yet; training scalars changed qualitatively after
  epoch ~275 and the later checkpoint is already producing real lifts.
- Continue current PPO to later checkpoints and run another eval against a
  later/best checkpoint before deciding whether grasp-quality shaping is needed.

## 2026-06-10 18:15 PDT - Ep350 Best-Checkpoint Eval Submitted

Reason:
- Training continued improving after the camera-fixed eval checkpoint; stdout
  reached epoch `349/600` with best reward `11777.56`.
- Latest local TensorBoard scalars available through epoch `320` show
  last-10 mean success about `0.653`, has-lifted about `0.829`, mean lift about
  `0.128m`, and zero table-clearance violations.

Command / Job:
- command:
  `RUN_NAME=franka_cube_baseclear_eval_ep350_20260610_1815 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z-evalfix CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 PRINT_INTERVAL=20 SEED=103 CUBE_SPAWN_XY_RANDOMIZATION=0.08 sbatch --parsable cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `28957917`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_28957917.out`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_baseclear_eval_ep350_20260610_1815`

Monitoring Criteria:
- Compare success/lift/table-clearance metrics against the camera-fixed eval.
- Inspect MP4 via `viz-open` for robust grasp/lift quality.

## 2026-06-10 18:18 PDT - Ep350 Eval Completed, Similar Success

Result:
- job_id: `28957917`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:56`.
- local artifact mirror:
  `cluster_results/a1002/evals/franka_cube_baseclear_eval_ep350_20260610_1815`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/evals/franka_cube_baseclear_eval_ep350_20260610_1815/videos/franka-cube-grasp-eval-step-0.mp4`
- video metadata: `1280x720`, `600` frames, `10.0s`.

Metrics:
- `num_steps_completed=600`, `done_count=4`.
- success: mean `0.58292`, final `0.0`, last-window mean `0.65`,
  max `0.75`.
- cube lift height: mean `0.10905m`, max `0.12916m`, final `0.0m`.
- has-lifted: mean `0.65958`, max `0.75`, final `0.0`.
- finger table clearance: mean `0.15387m`, min `0.04580m`.
- clearance violation: `0.0`.
- cube XY error: mean `0.05878m`, max `0.07155m`.

Visual Inspection:
- The video again shows a real lift without table penetration.
- Grasp quality remains rough: the cube rides on the top/inner area of the
  gripper fingers rather than a clean centered pinch.

Decision:
- Continue the current PPO run. Do not declare final success yet.
- Run a final eval at a later or final checkpoint and decide whether the
  remaining issue is acceptable task behavior or needs additional grasp-quality
  shaping.

## 2026-06-10 18:29 PDT - Final PPO Training Completed

Result:
- job_id: `28957528`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:31:22`.
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28957528.out`
- final stdout reached `epoch: 600/600`, saved final checkpoints, then printed
  `MAX EPOCHS NUM!` and `Training Done`.
- best checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth`
- final checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/last_dextrah_franka_cube_grasp_ep_600_rew_13045.947.pth`

Training Scalars:
- final `rewards/iter`: `13052.224`; last-10 mean `13064.818`.
- final `Episode/cube_success_rate`: `0.85997`; last-10 mean `0.82792`.
- final `Episode/cube_has_lifted_rate`: `0.94377`; last-10 mean `0.90838`.
- final `Episode/cube_lift_height`: `0.15435m`; last-10 mean `0.14879m`.
- final `Episode/cube_finger_table_clearance`: `0.19452m`.
- final `Episode/cube_finger_table_clearance_violation`: `0.0`.
- final `Episode/cube_gripper_width`: `0.05884m`.
- final `Episode/cube_ee_to_cube_dist`: `0.01516m`.

Analysis:
- The base-height/table-clearance fix remains effective through training:
  final clearance violations are zero.
- PPO learned the lift objective after the earlier stuck phase: training
  success and has-lifted rates are high by the final epochs.
- Final visual eval is still required because prior evals showed real lifts but
  rough, high-on-fingers grasp geometry.

Next:
- Submit a final camera-fixed eval against the best checkpoint.

## 2026-06-10 18:29 PDT - Final Best-Checkpoint Eval Submitted

Goal:
- Verify the final best PPO checkpoint in camera-fixed eval with video and
  metrics, focusing on lift success, table clearance, and remaining grasp
  quality.

Command / Job:
- local commit: `7c8a301` plus this pending worklog update.
- eval source commit on A100:
  `185d31c24f4fa4b0115ba6a468013ab36a2c0091`.
- command:
  `RUN_NAME=franka_cube_baseclear_eval_final_20260610_1829 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z-evalfix CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseclear_ppo_20260610_1756/nn/dextrah_franka_cube_grasp.pth NUM_ENVS=4 NUM_STEPS=600 VIDEO_LENGTH=600 PRINT_INTERVAL=20 SEED=104 CUBE_SPAWN_XY_RANDOMIZATION=0.08 sbatch --parsable cluster/sbatch_eval_franka_cube_grasp_1gpu.sh`
- job_id: `28958630`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_28958630.out`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_baseclear_eval_final_20260610_1829`

Monitoring Criteria:
- Fetch final video and metrics locally.
- Open the MP4 with `viz-open`.
- Confirm nonblank video, valid frame count/duration, cube/table in frame, no
  gripper/table penetration, and whether grasp quality is acceptable or still
  needs shaping.

## 2026-06-10 18:34 PDT - Final Best-Checkpoint Eval Completed

Result:
- job_id: `28958630`
- scheduler status: `COMPLETED`, exit `0:0`, elapsed `00:01:45`.
- local artifact mirror:
  `cluster_results/a1002/evals/franka_cube_baseclear_eval_final_20260610_1829`
- fetched log:
  `cluster_logs/a1002/dextrah/eval_franka_cube_28958630.out`
- viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-rl-20260610T2353Z/cluster_results/a1002/evals/franka_cube_baseclear_eval_final_20260610_1829/videos/franka-cube-grasp-eval-step-0.mp4`
- video metadata: `1280x720`, `600` frames, `10.0s`.
- contact sheet:
  `cluster_results/a1002/evals/franka_cube_baseclear_eval_final_20260610_1829/inspection/contact_sheet.jpg`

Metrics:
- `num_steps_completed=600`, `done_count=4`.
- success: mean `0.83125`, final `0.0`, last-window mean `0.8975`,
  max `1.0`.
- cube lift height: mean `0.14686m`, max `0.16407m`, final `0.0m`.
- has-lifted: mean `0.90667`, max `1.0`, final `0.0`.
- finger table clearance: mean `0.18568m`, min `0.05630m`.
- clearance violation: `0.0`.
- cube XY error: mean `0.06959m`, max `0.07920m`.
- gripper width: mean `0.05912m`.
- ee-to-cube distance: mean `0.01497m`.

Visual Inspection:
- The video is valid and camera framing is correct.
- The final checkpoint repeatedly lifts the cube above the table; no fingertip
  or gripper/table penetration is visible.
- The last frame occurs after env resets/drop, matching `success_rate_final=0`.
- Residual grasp quality is still rough: the cube often rides high on or near
  the gripper fingers rather than a centered pinch. This is much better than
  the original table-penetration failure and is sufficient evidence that the
  Franka cube RL task now learns the cube-lift objective, but a future
  grasp-quality iteration could tighten the manipulation style.

Decision:
- Treat the Franka cube RL debug objective as functionally fixed for lift
  learning and table clearance.
- No further reward/base-height patch is required before handing this back.
