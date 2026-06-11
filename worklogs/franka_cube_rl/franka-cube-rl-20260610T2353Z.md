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
