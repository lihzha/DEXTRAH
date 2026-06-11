# Franka Cube Grasp Prior Orchestration

Date: 2026-06-11

Base commit for all worker branches:

- `589dd81c9f9691fcda3a3d4b9ad714d90dae4794`

Shared design note:

- `worklogs/franka_cube_grasp_prior/franka-cube-grasp-prior-design-20260611.md`

## Agent Assignments

| Role | Agent ID | Nickname | Branch | Worktree | Owned worklog |
| --- | --- | --- | --- | --- | --- |
| Variant 1 reset prior | `019eb7fc-023c-7a00-91c8-c080fe0a39f3` | Aquinas | `codex/franka-cube-ggx-pregrasp-reset` | `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset` | `worklogs/franka-cube-grasp-prior/franka-cube-ggx-pregrasp-reset.md` |
| Trajectory tracking alternative | `019eb7fc-025b-78b1-907a-9fb8d2b9b879` | Popper | `codex/franka-cube-trajectory-tracking` | `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking` | `worklogs/franka-cube-grasp-prior/franka-cube-traj-tracking.md` |
| Diffusion Policy BC warm start | `019eb7fc-028b-7492-8add-227b9d81b46e` | Meitner | `codex/franka-cube-diffusion-policy-bc` | `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart` | `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md` |

## Orchestrator Rules

- Current `/home/lzha/code/DEXTRAH` checkout is the orchestrator/reference
  checkout.
- Workers use isolated worktrees and branches. They should not merge into
  `main` directly.
- No worker should launch full training without orchestrator/user approval.
- Bounded local/import/reset/dataset-shape smoke checks are allowed.
- Cluster or full-scale jobs must use agent-owned run namespaces and, if
  launched later, exact committed worker branches.
- Generated datasets, logs, videos, checkpoints, and large artifacts should
  remain untracked and live in agent-owned output paths.

## Source Notes

The Diffusion Policy BC worker was instructed to verify and start from the
official Diffusion Policy implementation:

- GitHub: `https://github.com/real-stanford/diffusion_policy`
- Project page: `https://diffusion-policy.cs.columbia.edu/`

The official project page links the sim/real repo and describes Diffusion
Policy as a conditional denoising diffusion process for visuomotor policy
learning with receding-horizon action prediction.

## 2026-06-11 Worker Completion Update

All three workers reported completion. No full training, cluster job, or Isaac
smoke was launched by the workers.

| Role | Final commit | Remote branch status | Local status | Validation summary | Remaining blocker |
| --- | --- | --- | --- | --- | --- |
| Variant 1 reset prior | `86ae7dfc5820e59ad310ef7c2ac1f64a49e0e399` | present on `origin/codex/franka-cube-ggx-pregrasp-reset` | worktree has untracked `local_results/` smoke artifact only | compile passed; GraspGenX import/list grippers passed; exported 32 centered-cube grasps, confidence `0.6894..0.7568`, `cube_size_m=0.06`, `tool_frame=panda_hand`, `pregrasp_farther_fraction=1.0` | local Isaac reset smoke blocked by missing Isaac Sim launcher/runtime |
| Trajectory tracking alternative | `92556e3215938ca222bd60cf1ddab6c1531b21f3` | present on `origin/codex/franka-cube-trajectory-tracking` | clean | py_compile passed; compact reference validator passed 11/11 checks; 5 phase waypoints; no joint arrays; approximate EE table margin `0.060 m`; original baseline registration unchanged | gym registration import blocked locally by missing `gymnasium`; reference is template and `curobo_validated=false` |
| Diffusion Policy BC warm start | `a21857f58ce211cb67f3174e56bb49c5f8f64ae8` | present on `origin/codex/franka-cube-diffusion-policy-bc` after orchestrator push | clean | py_compile passed; synthetic DP dataset smoke passed with obs `[8, 21]`, action `[8, 7]`, replay error `0.0`; converter CLI smoke passed; YAML parse passed | official Diffusion Policy one-step train blocked locally because `diffusion_policy` and `omegaconf` are not installed |

Notes:

- Worker C's final worklog said the branch was not pushed, while the agent
  notification said it was pushed. The orchestrator verified the branch was
  absent on `origin`, then pushed
  `codex/franka-cube-diffusion-policy-bc` to `origin` at `a21857f`.
- Worker A's untracked artifact is:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz`.

## Integration Queue

Recommended next steps before merging any worker branch into `main`:

1. Review Worker A's diff first because it is the main apple-to-apple variant.
   Run a real Isaac reset smoke in an environment with Isaac Sim/Isaac Lab
   available before launching training.
2. Review Worker B as a separate experimental task id. Require a real
   GraspGenX/cuRobo-exported, collision-validated reference before any training
   claims.
3. Review Worker C as offline utilities only. Install or clone the official
   `real-stanford/diffusion_policy` environment and run a one-step train/debug
   check on a real converted dataset before treating it as a trainable BC path.

## 2026-06-11 Resume After Early Checkpoint Stop

The user clarified that worker checkpoint completion is not enough; agents
should follow the robotics development loop and continue validating/debugging.
The orchestrator resumed all three agent sessions after they had been closed
and assigned another pass:

- Worker A: continue the GraspGenX pregrasp reset branch until there is a real
  Isaac Lab reset smoke or a hard external blocker. Local runtime should be
  rechecked; if blocked, use an agent-owned l401 worktree and a small Slurm
  validation job. No full RL training.
- Worker B: continue the trajectory-tracking branch until the new task id has a
  real DEXTRAH/Isaac task-registration/env smoke or a hard external blocker.
  No full training.
- Worker C: continue the Diffusion Policy BC branch until the official
  `real-stanford/diffusion_policy` implementation has at least config/model
  construction and preferably one-step/debug-train validation on a converted
  Franka cube dataset, or a precise external blocker is documented.

Current orchestrator stance:

- Do not merge worker branches into `main` yet.
- Keep monitoring workers until the next validation/debug loop completes.
- If any worker launches a local or cluster job, scheduler state alone is not
  sufficient; logs, metrics, and artifacts must be inspected.

## 2026-06-11 Long-Running Orchestration Goal

The user clarified that all agents should remain on their duties through the
full robotics development loop, including many code-fix/debug/relaunch rounds
before final RL training. The orchestrator should keep agents on track and
monitor progress, while leaving low-level debugging to the responsible worker.

Updated agent directives:

- Worker A owns the main apple-to-apple GraspGenX pregrasp-reset variant. It
  should continue from real Isaac reset smoke to short RL smoke and eventually
  final same-config Franka cube RL training once evidence is sane.
- Worker B owns the trajectory-tracking alternative. It should continue through
  real task-registration/env smoke, reference validation/export, short RL
  smoke, and possible scaled alternative training if viable.
- Worker C owns the Diffusion Policy BC warm-start alternative. It should
  continue through official `real-stanford/diffusion_policy` setup/debug-train,
  BC dataset/training validation, and a bridge toward RL fine-tuning if viable.

Orchestrator guardrails:

- Workers may launch cluster validation/training jobs when their own smokes
  justify scaling; no direct jump to full training without smoke evidence.
- Workers must inspect logs, metrics, artifacts, checkpoints, and abnormal
  behavior before declaring progress.
- Worker branches remain isolated; integration into `main` waits for reviewed
  evidence and an explicit merge decision.

## 2026-06-11 Active Loop Progress

Current observed progress after resuming workers:

- Worker A has passed a real l401 reset-prior validation smoke and launched a
  short RL-Games smoke for the prior-reset variant. Job `1027683` completed
  successfully on l401 (`ggx_rl_smoke`, exit `0:0`, elapsed `00:00:47`). The
  log shows `Dextrah-Franka-Cube-Grasp`, 64 envs, 2 epochs, checkpoint output,
  and prior-enabled wrapper plumbing. Worker A still owns interpretation of
  short-smoke quality before any scale-up.
- Worker B has passed a real l401 Isaac validation smoke for
  `Dextrah-Franka-Cube-Grasp-Traj-Tracking`: task registration, baseline
  registration, 72D observation shape, finite tracking logs, no immediate
  termination spike, and manual reference clearly marked unvalidated. It has
  prepared RL-smoke wrapper/config work for the tracking task.
- Worker C has progressed beyond synthetic validation: it set up the official
  `real-stanford/diffusion_policy` path, ran a one-step official lowdim debug
  train on converted Franka cube data, saved/loaded a checkpoint, and validated
  a PPO-bridge smoke with finite 7D action output. No full BC/RL training yet.

Latest remote worker refs observed:

- Worker A: `origin/codex/franka-cube-ggx-pregrasp-reset` at `4cdc8c19516fed4fae4355ab7fd3e9f3bba5c5fc`.
- Worker B: `origin/codex/franka-cube-trajectory-tracking` at `7d9c18066421638331888692d08d9185cc3d00d7`.
- Worker C: `origin/codex/franka-cube-diffusion-policy-bc` at `1fad16fa6b4b9eacbe1edf67ca8153ff399694ad`.

Current queue state when checked: no a1001 jobs; l401 job `1027683` had
completed. Continue polling workers rather than closing them.

## 2026-06-11 Worker C DP Milestone And Reassignment

Worker C reported a completed official-Diffusion-Policy mechanics milestone on
branch `codex/franka-cube-diffusion-policy-bc` at
`c3c33fd0e6e2404200bce9091d7345981227a13a`.

Evidence reported:

- Official Diffusion Policy source:
  `https://github.com/real-stanford/diffusion_policy`, external clone commit
  `5ba07ac6661db573af695b419a7947ecb704690f`.
- Official DP import/config/model construction passed.
- One-step official DP train on converted debug data passed and saved a
  checkpoint.
- Official checkpoint load plus PPO bridge smoke passed:
  PPO obs `[2, 72]`, lowdim sequence `[2, 2, 21]`, direct DP action `[2, 8, 7]`,
  bridge action `[2, 7]`.
- Multi-episode geometric grasp-library debug dataset passed:
  `16` episodes, `448` steps, `obs_dim=21`, `action_dim=7`,
  `curobo_validated=false`.
- Tiny official DP train on that multi-episode debug dataset passed with
  `train_loss=1.14365`, `val_loss=1.07233`,
  `train_action_mse_error=0.66672`.

Important limitation:

- Worker C did not find real Franka cube cuRobo trajectory artifacts locally.
  The geometric dataset is valid for mechanics/debugging only, not for a
  cuRobo-planned BC claim.

Orchestrator action:

- Reassigned Worker C immediately. Next milestone is to generate/find real
  GraspGenX+cuRobo trajectory demonstrations for BC, or document a hard blocker
  and proceed to a DEXTRAH/Isaac DP eval-wrapper or distillation bridge smoke.

## 2026-06-11 Active Monitor Check 19:24 UTC

The user clarified that this is a long-running orchestration job: keep all
three agents developing/debugging through many iterations until the final RL
training is finished. The orchestrator should not take over low-level debugging.

Current observations:

- Worker A reset-prior branch advanced to
  `c36d3f867bc87dc65617dd0942dcc0507f3c33c1`
  (`Add opt-in RL direct metrics sidecar`). Prior scalar smoke job `1027687`
  completed with exit `0:0`, checkpoints at epochs 15/30/45, and finite reward
  filenames up to about `581.206`, but TensorBoard events were still zero-byte.
  Worker A is expected to launch the same bounded 64-env/45-epoch prior-enabled
  smoke with `DEXTRAH_RLGAMES_JSONL_METRICS=True` and gate full 8-GPU training
  on inspecting JSONL sidecar metrics.
- Worker B retry job `1027688` completed with exit `0:0` and is a real
  GraspGenX/cuRobo availability pass: 80 candidates, selected grasp #22,
  selected confidence about `0.601`, and 42-waypoint approach/grasp/lift
  segments. Caveat: the validator used the GraspGenX 45 mm cube asset, so this
  is not yet a DEXTRAH 60 mm validated tracking reference. Worker B launched
  trajectory export job `1027689` (`ggx_cube_traj_export`) and owns conversion
  / geometry validation.
- Worker C has no new visible committed milestone after the geometric
  Diffusion Policy validation. It was nudged to either consume Worker B's real
  trajectory artifact when available or build the DEXTRAH/Isaac eval bridge
  around `predict_action_from_ppo_obs()` without waiting idle.

Queue state:

- l401: job `1027689` pending for Worker B trajectory export at this check.
- a1001: no active jobs observed in this loop.

Orchestrator actions:

- Sent targeted continuation messages to all workers.
- Keep polling agents and Slurm. If a worker completes another milestone,
  immediately assign the next development/debugging loop unless final
  apple-to-apple RL training and artifact inspection are truly finished.

## 2026-06-11 Active Monitor Check 19:28 UTC

Cluster jobs from the previous check both completed cleanly:

- Worker A job `1027690` (`ggx_rl_jsonl`) completed with exit `0:0` after
  `00:01:08`. The run wrote
  `metrics/direct_info_rank_0.jsonl` with 45 records, 162 scalar keys, no
  NaN/Inf scalars, and sane prior reset metrics. Prior attempt/success/farther
  rates were all `1.0`; reset position error mean/max was about
  `0.000242/0.000469 m`; reset rotation error mean/max was about
  `0.00585/0.00875 rad`; finger-table clearance min was about `0.134568 m`.
  The short smoke remained unsuccessful at lifting, as expected for an
  untrained 64-env/45-epoch run, but checkpointed at epoch 45 with reward
  filename about `736.6942`. Worker A recorded that the final same-config
  8-GPU run is now ready to launch with only prior/library overrides plus the
  JSONL inspection sidecar.
- Worker B job `1027689` (`ggx_cube_traj_export`) completed with exit `0:0`
  after `00:00:53`. It exported a real GraspGenX/cuRobo `trajectory.json` with
  662 frames for the 45 mm GraspGenX cube path, using 80 goalset candidates and
  selected grasp #28 at confidence about `0.597`. Worker B is expected to
  validate/commit the DEXTRAH compact converter and keep the 45 mm vs 60 mm
  caveat explicit.

Current worker expectations:

- Worker A: commit/push the JSONL result note and launch the final
  apple-to-apple 8-GPU Franka cube prior-reset RL training. Then monitor logs,
  JSONL metrics, checkpoints, reward/success curves, and abnormal terminations.
- Worker B: convert the exported trajectory into a compact task-space-only
  reference if possible, reject invalid 60 mm validation claims, and run the
  next tracking smoke/debug loop.
- Worker C: continue real cuRobo-demo dataset generation or the DP eval bridge;
  do not stop at the geometric DP debug dataset.

## 2026-06-11 Final RL Launch Monitor 19:31 UTC

Worker A launched the final apple-to-apple prior-reset RL training on a1001:

- job_id: `28987954`
- job_name: `ggx_reset_8gpu`
- node: `batch-block5-00308`
- run_name: `franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005`
- branch commit used by the job:
  `99ea26d5b449581988594f40168806642c486326`
- reason a1001 was used: l401 rejected the wrapper's 8-GPU partition shape;
  a1001 exposes valid 8-GPU partitions, keeping the final training geometry
  unchanged.

Startup log evidence:

- `NPROC_PER_NODE=8`
- `NUM_ENVS=2048`
- `DISTRIBUTED=True`
- `MULTI_GPU=True`
- `TASK=Dextrah-Franka-Cube-Grasp`
- default PPO wrapper values visible: horizon `64`, minibatch `32768`,
  mini-epochs `4`, learning rate `0.0002`, gamma `0.995`, tau `0.95`,
  save frequency `25`
- prior reset enabled with library
  `/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasps_smoke.npz`
- `DEXTRAH_RLGAMES_JSONL_METRICS=True`

Current queue state:

- a1001: `28987954` running.
- l401: Worker B converter validation job `1027692`
  (`dextrah_ggx_ref_convert2`) running.

Worker B converter evidence observed so far:

- The 45 mm export converted to a compact task-space-only reference with
  9 waypoints and `curobo_validated=false`.
- Converter validation passed schema, waypoint validity, increasing time,
  phase labels, approximate EE table clearance, target-outside-cube AABB,
  no joint trajectory arrays, and explicit task-space transform policy checks.
- The job then started the negative validation gate that tries to mark the
  45 mm validation JSON as a 60 mm DEXTRAH reference; this should reject.

Next monitoring actions:

- Keep polling a1001 job `28987954` through startup into real epochs. Confirm
  distributed ranks train, JSONL metrics appear, checkpoints are written, and
  reward/success curves are not pathological.
- Keep polling l401 job `1027692` until the negative gate result and artifacts
  are inspected by Worker B.

## 2026-06-11 Final RL Early Health 19:35 UTC

Final RL job `28987954` remains running on a1001 after startup:

- all 8 ranks initialized with `world_size = 8`
- rank-local JSONL metric files were opened; rank 0 is the active non-empty
  scalar stream at this point
- training reached at least epoch 31 / 10000
- first checkpoint written at epoch 25:
  `last_dextrah_franka_cube_grasp_ep_25_rew_1176.0144.pth`
- runtime sidecars were written for all ranks
- TensorBoard event file is non-empty
- grep for traceback/runtime/NCCL/CUDA failure signatures found no actionable
  error pattern

Early rank-0 JSONL sanity:

- 31 records, 162 scalar keys
- `bad_scalar_count=0`
- prior reset attempt/success/farther rates are all `1.0`
- latest reset position error about `0.00174 m`
- latest reset rotation error about `0.01642 rad`
- latest prior finger-table clearance about `0.13511 m`
- latest finger-table clearance violation `0.0`
- success/lifted rates remain `0.0`, expected this early

Worker B status:

- Converter job `1027692` completed successfully. It produced the 45 mm compact
  task-space reference, kept `curobo_validated=false`, and the intentional
  60 mm validation gate rejected the 45 mm validation JSON as expected.
- Worker B launched job `1027694` (`ggx_cube_60mm_ref2`) to attempt a scratch
  60 mm GraspGenX/cuRobo validation/export path.

## 2026-06-11 Worker Alternatives Progress 19:38 UTC

Final RL job `28987954` continues normally:

- still running on a1001 at about 8 minutes elapsed
- reached at least epoch 71 / 10000
- checkpoints written at epochs 25 and 50:
  `rew_1176.0144` and `rew_1646.5193`
- throughput remains in the expected hundreds-of-thousands fps range

Worker B trajectory-tracking alternative:

- 60 mm GraspGenX/cuRobo scratch attempt job `1027694` completed with exit
  `0:0`.
- It reported validation status `passed`, object extents `[0.06, 0.06, 0.06]`,
  positive approach/grasp/lift segment lengths of 42 each, selected grasp
  confidence about `0.674`, and a 662-frame trajectory export.
- The converter produced a 9-waypoint compact reference with no joint arrays
  and valid table/cube clearance checks.
- Worker B kept the reference `curobo_validated=false` for now under
  `graspgenx_curobo_60mm_export_pending_exact_validation`, which is conservative
  pending exact validation/export consistency.
- A follow-up l401 job `1027695` (`franka_cube_traj_60mm_ref`) is pending.

Worker C Diffusion Policy alternative:

- Worker C completed another milestone and pushed
  `origin/codex/franka-cube-diffusion-policy-bc` at
  `30b305e` (`Record DP BC branch push`).
- It added a real GraspGenX/cuRobo DP BC path, generated 8/8 real cuRobo
  trajectories, converted an 8-episode / 836-step lowdim dataset, ran an
  official Diffusion Policy tiny train, and passed the PPO-observation bridge
  smoke through `predict_action_from_ppo_obs()`.
- Reported tiny-train metrics: `train_loss=1.1866`, `val_loss=1.0896`,
  `train_action_mse_error=0.6654`.
- Local Isaac eval is blocked by the local IsaacLab install missing
  `_isaac_sim/python.sh`; Worker C was reassigned to validate the eval wrapper
  on cluster instead of stopping.

## 2026-06-11 Mid-Run Monitor 19:42 UTC

Final RL job `28987954` remains healthy:

- running on a1001 at about 12 minutes elapsed
- reached at least epoch 115 / 10000
- checkpoints written at epochs 25, 50, 75, and 100; best checkpoint updates
  started after epoch 100, reaching reward filenames / best-reward messages
  around `1768.6901`
- rank-0 JSONL: 115 records, 162 scalar keys, `bad_scalar_count=0`
- latest prior reset success rate `1.0`; reset position error about
  `0.00171 m`
- latest lifted rate `0.00048828125`; success rate still `0.0`

Worker B status:

- 60 mm external-reference DEXTRAH Isaac env smoke job `1027695` completed
  with exit `0:0`.
- Metrics: validation payload `passed=true`, observation shape `[4, 72]`,
  rollout 80/80 steps, `done_count=0`, `early_done_count=0`, final reward
  about `1.769`, mean reward about `1.816`.
- Tracking reference loaded from the 60 mm compact GraspGenX-derived reference,
  with `graspgenx_source=true`, `curobo_validated=false`,
  `waypoint_count=9`, and `validation_passed=true`.
- Tracking metrics were finite: tracking reward mean about `0.03957`, target
  table clearance min about `0.2764`, unsafe target rate max `0.0`.
- Worker B is planning train/eval wrapper passthroughs for the external
  reference before any trajectory-tracking RL smoke.

Worker C status:

- Worker C accepted the cluster continuation and is preparing
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` for a bounded l401 DP
  policy eval smoke using the official-DP checkpoint and the real cuRobo-demo
  dataset context.

## 2026-06-11 Monitor Check 19:46 UTC

Final RL job `28987954`:

- still running on a1001 at about 15.5 minutes elapsed
- reached at least epoch 154 / 10000
- latest rank-0 JSONL: 154 records, `bad_scalar_count=0`
- prior reset success rate remains `1.0`
- latest success rate `0.0`; lifted rate returned to `0.0` after a small
  earlier nonzero blip
- best-checkpoint messages continue improving, reaching about `1823.7875` at
  epoch 150

Worker B:

- Short 60 mm external-reference tracking RL smoke job `1027698` completed
  with exit `0:0`, 16 envs, 3 epochs, and the external trajectory-tracking
  reference task/config.
- Job `1027697` was a cancelled duplicate / stale submission with no assigned
  node.
- The RL smoke produced a checkpoint named with `rew_-inf` because max epochs
  were reached before any env terminated. This is not sufficient training
  evidence by itself; Worker B still owns checkpoint eval / metric inspection
  and any wrapper patch/relaunch loop before claiming the trajectory-tracking
  variant is viable.

Worker C:

- First l401 DP-eval submission was blocked before scheduling by an invalid
  inherited partition list (`batch_singlenode` on l401). Worker C is patching
  the DP eval launcher to use the l401 `batch` partition.

## 2026-06-11 Monitor Check 19:50 UTC

Final RL job `28987954`:

- still running on a1001 at about 19 minutes elapsed
- reached at least epoch 194 / 10000
- rank-0 JSONL: 194 records, `bad_scalar_count=0`
- prior reset success rate remains `1.0`; average reset position error over
  the last 20 records about `0.00179 m`
- best reward messages continue improving up to about `1866.2578`
- latest success rate `0.0`; last-20 average success rate is a small
  `2.44e-05`; last-20 lifted-rate average about `2.20e-04`

Worker B:

- External-reference checkpoint eval job `1027700` completed with exit `0:0`.
- Eval loaded the same 60 mm compact reference path and reported
  `graspgenx_source=true`, `curobo_validated=false`, `validation_passed=true`,
  `waypoint_count=9`, and the expected transform/joint policies.
- Rollout completed 120/120 steps with no non-finite JSON metrics, reward mean
  about `1.768`, final reward about `1.778`, success rate `0.0`.
- Tracking metrics were finite: tracking reward mean about `0.04245`, position
  error mean about `0.348`, orientation error mean about `0.178`, target table
  clearance min about `0.2456`, unsafe target rate max `0.0`.
- Worker B's next step is a modest one-GPU scale-up smoke, still not full
  trajectory-tracking training.

Worker C:

- DP eval job `1027699` failed with no metrics JSON after Isaac task config
  parsing; a diagnostic checkpoint-import job `1027701` isolated the blocker to
  official DP importing `wandb` in the Isaac Python environment.
- The concrete error is protobuf incompatibility:
  `TypeError: Descriptors cannot be created directly`.
- Worker C is patching the eval launcher with
  `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` and adding DP eval stage
  markers before relaunch.

## 2026-06-11 Monitor Check 20:00 UTC

Final RL job `28987954`:

- still running on a1001 at about 32 minutes elapsed
- reached at least epoch 331 / 10000
- rank-0 JSONL: 331 records, `bad_scalar_count=0`
- best-reward messages improved past `2007.6512`
- latest prior reset success rate `1.0`
- latest lifted rate `0.0009765625`; latest success rate still `0.0`

Worker B trajectory alternative:

- 720-step eval job `1027707` completed with exit `0:0` after `00:00:59`.
  The visible metrics report 720/720 steps, reward mean about `2.269`, final
  reward about `2.486`, success rate `0.0`, tracking reference loaded from the
  same 60 mm compact GraspGenX path, and no non-finite JSON values.
- Worker B then patched target safety behavior and pushed
  `origin/codex/franka-cube-trajectory-tracking` at
  `dfd5587` (`Gate unsafe tracking targets`).
- Reset/target-gating smoke job `1027714` completed with exit `0:0`. It ran
  160/160 validation steps, kept the external reference summary, reported
  `runtime_object_pose_policy=reset_cube_pose`,
  `unsafe_target_reward_policy=zero_tracking_weight_below_min_target_table_clearance`,
  tracking target clearance min about `0.2197`, unsafe target rate `0.0`, and
  no immediate termination spike.

Worker C Diffusion Policy alternative:

- After several dependency diagnostics, Worker C passed the cluster DP eval
  smoke on job `1027713` with exit `0:0`.
- The passing eval loaded the official `real-stanford/diffusion_policy`
  checkpoint, bridged 72D PPO observations through `predict_action_from_ppo_obs`,
  emitted 7D actions, stepped the Isaac env for 16/16 steps, wrote
  `metrics.json`, and the launcher printed `DP eval metrics passed`.
- Metrics: `reward_mean=1.3180`, `reward_final=1.3083`,
  `final_success_rate=0.0`, `window_success_rate=0.0`,
  `final_gripper_width=0.04295`; actions are clipped/saturated, which matches
  the tiny 8-demo debug-checkpoint limitation.
- Worker C pushed `origin/codex/franka-cube-diffusion-policy-bc` at
  `7ae5d24` (`Plan real cuRobo DP dataset scale-up`) and is moving toward a
  bounded real-demo dataset expansion, still not final BC/RL.

## 2026-06-11 Monitor Check 20:11 UTC

Final RL job `28987954`:

- still running on a1001 at about 41 minutes elapsed
- reached at least epoch `436` in rank-0 JSONL and epoch `432` in the visible
  stdout tail during this check
- rank-0 JSONL: `436` records, `bad_scalar_count=0`
- best-checkpoint messages improved to at least `2084.8135` at epoch `402`
- interval checkpoint observed at epoch `425` with reward suffix `2057.8845`
- latest rank-0 sidecar still reports prior reset diagnostics, including reset
  attempt/farther/success rates at `1.0`; the run remains a live final
  apple-to-apple RL training, not a completed result

Worker B trajectory-tracking alternative:

- l401 queue is empty, and reset-pose RL25 eval job `1027719` completed with
  exit `0:0` after `00:00:58`
- eval artifacts:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_resetpose_rl25_eval720_20260611_130748/metrics.json`
  and
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027719.out`
- rollout completed `720/720` requested steps with `done_count=7`,
  `reward_mean=1.9178464568323559`, `reward_final=2.1220836639404297`, and
  success mean/final/window all `0.0`
- recursive numeric JSON check found no non-finite values
- trajectory target safety remained clean:
  `cube_traj_tracking_unsafe_target_rate=0.0`,
  `cube_traj_tracking_safe_target_rate=1.0`, and
  `cube_traj_tracking_target_table_clearance_min` minimum
  `0.06511414051055908` above the `0.025 m` safety threshold
- behavior is still not task-successful: `cube_lift_height_max` maximum is only
  about `0.0307 m`, `has_lifted_cube=0.0`, and there is a small finger-table
  violation signal with `finger_table_clearance_violation_max` maximum about
  `0.0537`
- Worker B was nudged to append/commit/push this eval result and continue with
  a bounded next iteration focused on no-lift/no-success and table-contact
  behavior, while keeping the target-safety path intact

Worker C Diffusion Policy alternative:

- l401 queue is empty; Worker C's latest activity is local official-DP training
  and checkpoint validation
- 32-demo real cuRobo conversion and dataset smoke completed locally:
  `num_episodes=32`, `num_steps=3284`, `obs_dim=21`, `action_dim=7`,
  all source trajectories marked `curobo_validated=true`
- bounded official-DP overfit/debug run
  `run_20260611_130917_curobo32_overfit2k` completed with `global_step=2024`,
  `train_loss=0.00821`, `val_loss=0.00871`, and
  `train_action_mse_error=0.29439`
- checkpoint bridge smoke at `25` diffusion inference steps still touches some
  normalized clip bounds; at `100` inference steps action ranges are mostly
  small and inside bounds except the constant-open gripper near `1.0`, which is
  expected for the approach/pregrasp-only dataset
- this is still only a mechanics/BC sanity result because approach-only demos
  cannot teach close/lift; Worker C was nudged to append/commit/push and then
  continue toward close/lift-capable data or a clearly documented BC-to-RL
  initialization path

## 2026-06-11 Monitor Check 20:21 UTC

Final RL job `28987954`:

- still running on a1001 at about 52.5 minutes elapsed
- reached at least epoch `559` in the visible stdout tail
- rank-0 JSONL check at epoch `541`: `541` records, `bad_scalar_count=0`
- latest interval checkpoint observed at epoch `550`:
  `last_dextrah_franka_cube_grasp_ep_550_rew_2110.0083.pth`
- best reward remains at least `2116.91` from the earlier epoch-466 best
  checkpoint message
- reset-prior diagnostics remain healthy: rank-0 reset success `1.0`; lift and
  success signals are still tiny/intermittent, with success max observed so far
  only `0.00048828125`

Worker B trajectory-tracking alternative:

- committed and pushed retiming patch `22f674c`
  (`Retime cube trajectory tracking references`), then committed retiming smoke
  evidence `08ce93b` (`Record retimed trajectory smoke`)
- retimed validation job `1027720` completed `0:0`; validation metrics passed
  with observation shape `[4,72]`, 240/240 rollout steps, no non-finite JSON
  values, no early termination spike, unsafe target rate `0.0`, target table
  clearance batch min `0.06511414051055908`, and reference summary reporting
  `runtime_duration_s=8.0` while preserving `source_duration_s=22.033333333333335`
- retimed 3-epoch RL smoke job `1027721` completed `0:0`; actor/critic still
  build with obs dim `72`, checkpoints written through epoch 3, resolved config
  keeps `trajectory_tracking_phase_observations=false` and
  `trajectory_tracking_follow_current_cube_pose=false`
- retimed checkpoint eval job `1027723` completed `0:0`; metrics show 720/720
  steps, `done_count=4`, reward mean `1.7883200655380884`, final reward
  `1.933864712715149`, no non-finite JSON values, success still `0.0`
- key retiming result: `cube_traj_tracking_phase_progress.max=1.0` at step
  `480`, compared with the old run stalling around `0.358`; target safety
  stayed clean with unsafe target rate `0.0`, safe target rate `1.0`, and
  target clearance min `0.06511414051055908`
- task behavior is still a smoke-level negative: no success/lift, but finger
  table clearance stayed clean (`finger_table_clearance_violation_max=0.0`);
  next useful Worker B step is a bounded retimed scale-up, not a full claim

Worker C Diffusion Policy alternative:

- converted the 32 real cuRobo trajectories to a full pick/lift lowdim dataset:
  `num_episodes=32`, `num_steps=22484`, `obs_dim=21`, `action_dim=7`,
  all sources marked `curobo_validated=true`, gripper action min/max `-1.0/1.0`,
  and close-command fraction about `0.5764`
- trained a bounded official-DP full-pick/lift checkpoint locally:
  `global_step=503`, `train_loss=0.04288`, `val_loss=0.03742`,
  `train_action_mse_error=0.01642`; bridge checks at 100 denoising steps
  showed open-gripper behavior on first rows and close commands on closed/lift
  rows
- l401 DP eval job `1027722` completed `0:0`; metrics passed with
  `steps_completed=64`, `env_closed=true`, reward mean `1.3106193002313375`,
  final reward `1.264480471611023`, success `0.0`, finite action ranges
  `[-0.20807,-0.35009,-0.05984,-0.16531,-0.31083,-0.26626,-0.30297]` to
  `[0.37037,0.19806,0.39653,0.27571,0.28798,0.22835,1.0]`, and final gripper
  width `0.0491`
- Worker C diagnosed the next bridge issue: the eval wrapper currently executes
  only the first action from each 8-action DP output and replans every sim step;
  worker is patching optional action-chunk execution while preserving the
  default first-action behavior

## 2026-06-11 Monitor Check 20:40 UTC

User artifact request:

- Sent explicit artifact-generation requests to all three workers.
- Worker A has produced an inspectable interim bundle for the final reset-prior
  RL run:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705`
- Worker A artifact viewer:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705/training_curves.png`
- Worker B was interrupted and redirected to produce its planned retimed vs
  phase-starved trajectory-tracking artifact bundle before further training.
  At this checkpoint, no B report/PNG/CSV/summary artifact has appeared yet.
- Worker C was interrupted and redirected to produce its DP BC comparison
  bundle. It has fetched the overfit2k chunk8 rollout video locally, but the
  full report/plots/summary bundle is still in progress.
- Worker C video viewer:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_video_20260611_132637/videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`

Final RL job `28987954`:

- still running on a1001 at about `1:03:38` elapsed, with time limit `3:50:00`
- reached epoch `683`, frame `715128832` in rank-0 JSONL
- rank-0 direct metrics use a nested `scalars` object; parsed that layout for
  this checkpoint
- `bad_scalar_count=0`
- latest interval checkpoints include epoch `650` reward suffix `2158.793` and
  epoch `675` reward suffix `2121.1836`; epoch `650` also updated the best
  checkpoint to `2158.793`
- prior reset diagnostics remain healthy: reset success tail100 mean `1.0`,
  reset-farther tail100 mean `1.0`, finger/table clearance latest
  `0.134811 m`, reset position error latest `0.001875 m`, reset rotation error
  latest `0.018712 rad`
- task terms continue to improve: approach reward latest `1.14001` and tail100
  mean `1.12873`; enclosure latest `0.637126` and tail100 mean `0.631843`
- lift/success remain sparse: success max `0.00048828125`, tail100 mean
  `0.000009765625`; lifted max `0.00244140625`, tail100 mean `0.00041015625`;
  lift-height tail100 mean about `0.0001008 m`

Worker B trajectory-tracking alternative:

- last confirmed state remains retimed RL25/eval complete:
  `1027724` and `1027726` both completed `0:0`
- retiming fixed phase starvation: old reset-pose eval only reached phase
  progress about `0.358`; retimed eval reaches `1.0`
- target safety remains clean in the retimed eval: unsafe target rate `0.0`,
  target clearance min `0.065114 m`
- behavior remains negative at RL25 scale: no lift/success
- artifact bundle remains pending after the orchestrator interruption

Worker C Diffusion Policy alternative:

- overfit2k chunk8 l401 eval job `1027727` completed `0:0` in `00:01:29`
- local fetched video:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_video_20260611_132637/videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`
- video metadata: `1280x720`, `359` frames, `5.98 s`
- mechanical eval passed, but behavior is still poor: reward decays from about
  `1.36` to `1.01`, final EE-to-cube distance about `0.609 m`, final
  finger-center distance about `0.588 m`, final gripper width about
  `0.0798 m`, cube lift `0.0`, success `0.0`
- artifact bundle/report remains pending after the orchestrator interruption

## 2026-06-11 Monitor Check 20:50 UTC

Artifact request status:

- Worker A reset-prior bundle remains available at
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/a1001/franka_cube_ggx_pregrasp_reset_8gpu_20260611_193005/inspection_20260611_202705`
- Worker B trajectory-tracking bundle is now available at
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000`
- Worker B viewer URLs:
  - phase/safety:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/phase_progress_and_target_safety.png`
  - behavior:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_20260611_133000/behavior_reward_lift_finger_metrics.png`
- Worker C DP BC bundle is now available at
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640`
- Worker C viewer URLs:
  - eval behavior:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640/plots/eval_behavior_metrics.png`
  - train/val loss:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640/plots/full_pick_train_val_loss_5epoch_vs_25epoch.png`
  - rollout video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640/videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`

Final RL job `28987954`:

- still running on a1001 at about `1:08:30` elapsed
- rank-0 JSONL reached epoch `740`, frame `774897664`; `bad_scalar_count=0`
- best checkpoint reward has improved to at least `2183.229` by epoch `731`
- recent interval checkpoints include epoch `700` reward suffix `2141.7861`
  and epoch `725` reward suffix `2149.8704`
- reset-prior success tail100 mean remains `1.0`
- approach/enclosure reward terms remain high but oscillatory; success and lift
  are still sparse (`cube_success_rate` max `0.00048828125`, lifted max
  `0.00244140625`)

Worker B trajectory-tracking alternative:

- artifact report conclusion: retiming fixed the phase-starvation failure
  (`0.3584` max phase before retiming versus `1.0` after retiming), while
  target safety stayed clean (`unsafe_target_rate_max=0.0`, target clearance
  min `0.0651 m`)
- behavior remains unsolved at retimed RL25 scale: success `0.0`, max lift
  `0.0168 m`, gripper collapses near zero, and orientation error remains high
- branch moved to commit `c786e59` with a variant-only gripper target clamp
  (`trajectory_tracking_min_target_gripper_width=0.024`)
- l401 validation job `1027728` completed `0:0` in `00:00:45`; metrics passed
  with 240 rollout steps, no early dones, target unsafe rate `0.0`, target
  clearance min `0.065114 m`, source gripper min `0.0`, runtime gripper min
  `0.024`, and final gripper width about `0.02946`
- Worker B was told to append/commit/push this result and only then proceed to
  the next bounded RL smoke/eval; the validation result is not learned-policy
  success

Worker C Diffusion Policy alternative:

- artifact report conclusion: the official-DP overfit2k checkpoint can output
  close/lift commands on dataset-like closed/lift rows, but live Isaac chunk8
  rollout stays open and drifts away
- overfit2k chunk8 eval behavior: final success `0.0`, lift `0.0`, gripper
  width final about `0.0798 m`, EE-to-cube distance grows from about `0.234 m`
  to `0.609 m`, and reward decays to about `1.01`
- branch moved to commit `fdb77c9` with the artifact generator plus a
  disabled-by-default policy-call trace hook
- Worker C was nudged to run the next tiny traced eval and compare live lowdim
  observation history/action chunks against converted dataset phases

## 2026-06-11 Monitor Check 20:58 UTC

Worker A reset-prior eval video:

- User asked whether the first agent has eval videos. Initially only curve and
  report artifacts existed; Worker A then patched the eval wrapper to expose
  reset-prior overrides and launched a bounded 1-GPU l401 eval from the current
  reset-prior checkpoint without interrupting active training job `28987954`.
- Worker A branch now includes `51cac4a`:
  `Enable prior reset eval video overrides`.
- Eval job `1027734` (`ggx_eval_video`) completed `0:0` in `00:01:11` on
  `pool0-00016`.
- Remote eval run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141`
- Local fetched eval run:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141`
- Video viewer:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep875_20260611_205141/videos/ggx-pregrasp-reset-ep875-step-0.mp4`
- Video metadata: `1280x720`, `359` frames, `5.98 s`; representative frame is
  nonblank and shows a tight camera on the gripper/cube.
- Eval metrics from `metrics.json`: 360 steps; reward mean `3.836`, reward
  final `4.065`; success rate mean/final/max `0.0`; has-lifted mean/final/max
  `0.0`; cube lift height mean/final/max `0.0`; gripper width closes from
  about `0.0796 m` to `0.00022 m`; finger-center-to-cube distance improves
  from about `0.0956 m` to `0.0620 m`; table-clearance violation remains `0.0`.
- Interpretation: the first-agent checkpoint is visually and metrically doing
  the pregrasp/close behavior, but not yet a task-solving lift. This matches
  the online training metrics: reset-prior is stable and reward is improving,
  but sustained success/lift has not emerged yet.

Final RL job `28987954`:

- still running on a1001 at about `1:26` elapsed; reached at least epoch `928`
  in stdout during this monitor window
- interval checkpoints continue, including epoch `900` reward suffix
  `2213.7234` and epoch `925` reward suffix `2196.059`
- best reward improved to at least `2217.4502` around epoch `837`
  before the eval-video checkpoint was sampled

## 2026-06-11 Monitor Check 21:04 UTC

Worker C DP train/eval mismatch escalation:

- User reviewed Worker C's DP rollout video and called out the same failure:
  the policy visibly drifts away from the object and ignores it. This is being
  treated as a train/eval mismatch or bug until disproven, not as merely weak
  BC performance.
- Worker C has found a concrete mismatch: the stale approach/full-pick datasets
  encoded EE translation/rotation deltas in world/env coordinates, while the
  DEXTRAH Franka action path passes relative commands to the differential IK
  controller in the robot root frame. The Franka cube robot root is yawed
  180 degrees, so old-label x/y and roll/pitch signs were inverted at execution
  time.
- Consequence: old 503-step and overfit2k full-pick checkpoints are stale for
  behavior claims. Their mechanics checks remain useful only for checkpoint
  loading and bridge plumbing, not for manipulation quality.
- Worker C produced a frame-corrected dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
- Worker C trained a corrected overfit/debug checkpoint with official DP:
  `global_step=2523`, train loss about `0.00885`, val loss about `0.00978`,
  train action MSE about `0.00115`.
- Corrected checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k/checkpoints/latest.ckpt`
- Corrected 96-step l401 trace job `1027736` completed `0:0`. It still failed
  behavior within the short horizon, but approach improved versus the stale
  trace: EE-to-cube distance `0.2332 -> 0.1729 m` and finger-center-to-cube
  distance `0.2200 -> 0.1777 m`. Gripper stayed open (`0.0798 -> 0.0739 m`)
  and success/lift remained `0`.
- Worker C's dataset timing check shows close starts around local step
  `282/283`, lift around `402/403`, and hold-after-lift around `642/643`, so
  the 96-step trace is too short to validate whether close/lift phases are now
  reached.
- Worker C launched or queued a longer corrected 512-step trace job `1027737`
  to test whether the corrected policy closes/lifts at the dataset phase timing.
  This remains active/pending at this checkpoint.
- Orchestrator instruction to Worker C: do not pivot to data augmentation or RL
  warm-start until action frame, observation bridge, action timing, train/eval
  normalization, and history ordering are all explicitly checked and recorded.

## 2026-06-11 Monitor Check 21:11 UTC

Worker C DP mismatch follow-up:

- Corrected 512-step l401 trace job `1027737` completed `0:0` in `00:01:24`.
  Remote run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907`
- Local fetched run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907`
- Metrics: `512/512` steps, reward mean `1.6550`, reward final `1.6986`,
  success/window success `0.0`, lift `0.0`, no dones. EE-to-cube distance
  improved `0.2332 -> 0.1343 m`, finger-center-to-cube distance improved
  `0.2200 -> 0.1680 m`, and gripper width closed from about `0.0798 m` to
  `0.0012 m`.
- Trace analysis:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907`
- Trace plot viewer:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907/trace_phase_comparison.png`
- Analysis summary: the corrected policy no longer behaves like the stale
  action-frame-bug run, because it approaches and closes at the expected later
  phase. It is still not acceptable: nearest-demo distance worsens
  `0.356 -> 1.220`, live cube-minus-EE norm only improves `0.234 -> 0.134 m`,
  and the rollout ends off-manifold with the gripper closed away from contact.
- Worker C has started a systematic train/eval mismatch audit in its worklog,
  with planned utility `dextrah_lab/offline_dp_bc/audit_eval_mismatch.py` and
  output namespace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907`
- Orchestrator stance: C is not cleared. The old video was a real bug/stale
  artifact; the corrected run still needs observation/action/timing/reset audit
  before any DP scale-up or RL warm-start.

Worker B trajectory-tracking artifacts:

- Gripper-clamp RL25 eval job `1027733` completed earlier with zero success and
  zero sustained lift. It fixed the near-zero gripper-collapse pathology but
  still failed task behavior; mean phase did not reach `1.0` in the 720-step
  averaged rollout because some envs reset.
- Worker B produced a refreshed comparison bundle:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512`
- Viewer:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_artifact_bundle_clamp_20260611_135512/comparison_report.md`
- B also launched video eval job `1027738`, which completed `0:0` in
  `00:01:18`; local fetched video:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/videos/gripclamp-rl25-eval480-step-0.mp4`
- Video viewer:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_gripclamp_rl25_video480_20260611_135930/videos/gripclamp-rl25-eval480-step-0.mp4`
- Video metadata: `1280x720`, `479` frames, `7.98 s`. Contact sheet is
  nonblank; visually the gripper approaches but stays wide/off-contact and
  does not lift the cube.
- Video metrics: `480/480` steps, reward mean `2.5610`, success `0.0`, lift
  `0.0`, phase reaches `1.0`, target unsafe rate `0.0`, target clearance min
  `0.0651 m`, EE-to-cube distance `0.1799 -> 0.0841 m`, finger-center-to-cube
  distance `0.1690 -> 0.0773 m`, gripper width ends around `0.0444 m`.
- Worker B was asked to inspect the video and propose the next bounded ablation
  before any longer training.

Worker A reset-prior final RL:

- A100 job `28987954` is still running at about `1:35` elapsed. Stdout reached
  epoch `1036` during this monitor window; rank-0 JSONL reached epoch `1039`,
  frame `1088421888`.
- Latest interval checkpoint observed: epoch `1025` reward suffix `2199.798`.
  Best stdout checkpoint reward improved to at least `2236.2048` around epoch
  `993`.
- Rank-0 last-50 JSONL means: reset success `1.0`, reset farther rate `1.0`,
  reset position error about `0.00193 m`, reset rotation error about
  `0.01845 rad`, table-clearance violation `0.0`, success mean about
  `9.77e-06`, lifted mean about `3.71e-04`, EE-to-cube distance about
  `0.0675 m`, finger-center-to-cube distance about `0.0592 m`, and gripper
  width about `0.0025 m`.
- Interpretation: reset-prior mechanics remain healthy and the policy learns
  approach/close behavior, but sustained lift/success is still sparse at this
  training point. Continue monitoring/requeue rather than declaring success.

## 2026-06-11 Monitor Check 21:18 UTC

Worker C DP mismatch audit:

- Worker C finalized and pushed the mismatch-audit utility at branch commit
  `aad5eef` (`Add Franka DP mismatch audit report utility`).
- Audit artifact directory:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907`
- Audit report viewer:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907/mismatch_audit_report.md`
- Plots:
  `obs_distribution.png`, `trace_phase_action.png`, `behavior_metrics.png`
  in the same artifact directory; all are nonblank and inspected.
- Audit result: old pre-framefix videos/checkpoints remain invalid for behavior
  claims. The framefix action convention, eval action scales, 72D observation
  bridge layout, and checkpoint normalizer now check out. The failure remains
  a geometric/temporal train-eval mismatch: the policy closes before the live
  cube-relative geometry matches the demo grasp geometry.
- Key evidence: trace fields outside dataset support include `ee_pos_x/y/z`,
  `ee_quat_w`, `cube_pos_z`, `cube_minus_ee_z`, and `cube_goal_delta_z`;
  cube-minus-EE z-score is especially bad in x/y. First negative gripper chunk
  occurs at step `184`, hard close at `208`, live gripper width `<1cm` at
  `216`, and first nearest `lift_object` phase at `392`. Final
  cube-minus-EE is about `[-0.0105, -0.1022, -0.0867]`, with EE-to-cube
  `0.134 m`, finger-center-to-cube `0.168 m`, and lift `0.0`.
- Worker C was instructed to run a bounded live-vs-demo geometry/history/timing
  check next: compare cube-minus-EE and gripper width against nearest demo step
  and first-close/hard-close demo geometry, and verify two-step history
  initialization plus chunk/repeat timing before any larger DP training.

Worker B trajectory-tracking phase-gated ablation:

- B's phase-gated env smoke `1027739` completed `0:0`; local metrics fetched
  to:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_env_smoke_20260611_140552`
- Env smoke result: `35` checks passed; reset obs shape `[4,72]`; target
  unsafe rate `0.0`; target clearance min `0.0651 m`; no nonfinite values.
  The new close/lift/gate logs are present and finite. Close/lift action reward
  means are `0.0` in scripted validation because contact gate mean is only
  `0.0096`, so this proves wiring but not learned behavior.
- B's tiny phase-gated RL smoke `1027740` completed `0:0`; params fetched to:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730`
- RL smoke log shows actor/critic input dim `72`, 16 envs, 3 iterations, and
  checkpoints for epochs 1-3. Remote checkpoints remain under:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_phasegate_rl_smoke_20260611_140730/nn`
- Resolved config confirms reward-only observation contract and ablation
  settings: `observation_space=72`, `trajectory_tracking_phase_observations=false`,
  reference duration `8.0`, min target gripper width `0.024`,
  close-action weight `0.35`, lift-action weight `0.5`, contact gate max
  finger distance `0.14`, and contact gate width `0.08`.
- TensorBoard event file is still `0` bytes; stdout/params/checkpoint listing
  are the current smoke evidence. Worker B still needs to commit its latest
  worklog update and should only launch a bounded eval/video before considering
  any longer training.

Worker A reset-prior final RL:

- A100 job `28987954` remains running at about `1:41` elapsed. Stdout reached
  epoch `1094`; rank-0 JSONL reached epoch `1103`, frame `1155530752`.
- Best stdout reward improved to at least `2239.0322` around epoch `1062`;
  latest observed interval checkpoint is epoch `1075` reward suffix `2220.847`.
- Latest rank-0 scalar line: reset success `1.0`, reset farther rate `1.0`,
  reset pos error `0.00184 m`, reset rot error `0.01863 rad`, success rate
  `0.000488`, lifted rate `0.001465`, EE-to-cube `0.0676 m`,
  finger-center-to-cube `0.0584 m`, and gripper width `0.00179 m`.
- Last-50 means: success `2.93e-05`, lifted `4.69e-04`, lift height
  `1.07e-04 m`, reset success `1.0`, reset farther rate `1.0`. Continue
  monitoring; not task-solved yet.

## 2026-06-11 Monitor Check 21:22 UTC

Worker C DP mismatch audit:

- User flagged C's video as clearly wrong: the hand drifts away and ignores the
  object. Orchestrator agrees this remains a real train/eval mismatch bug until
  disproven.
- History-cadence fix trace job `1027744` completed `0:0` in `00:01:20`.
  Remote run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- Local fetched run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- Metrics: `512/512` steps, reward mean `1.6488`, reward final `1.6844`,
  success/window success `0.0`, lift `0.0`, no dones, final gripper width
  `0.00116 m`.
- Behavior: EE-to-cube distance improves from `0.2332 m` to best `0.1360 m`
  and final `0.1371 m`, but finger-center-to-cube remains far at best
  `0.1640 m` and final `0.1695 m`. The gripper becomes fully closed while the
  fingers are still far from a valid grasp.
- Trace check: the history-cadence patch is mechanically effective. The first
  policy call has the reset duplicate `history_step_gap=0`; all later recorded
  policy calls have `history_step_gap=1` and histories like `[t-1, t]`.
- Interpretation: C has fixed the prior action-frame bug and the eval history
  cadence bug, but behavior remains invalid. The next bug search should focus
  on train/eval observation schema and normalization, action scale/sign/clamp,
  gripper convention, frame/root transforms, reset distribution/object pose,
  DP sequence padding, and live geometry vs nearest training window.
- Worker C was interrupted with this evidence and instructed to generate a
  new mismatch report/plots comparing live eval windows to nearest train
  windows around approach and close before any scale-up training.

Worker B trajectory-tracking phase-gate eval:

- Metrics rerun job `1027743` completed and was fetched to:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_phasegate_ep3_metrics480_20260611_141725`
- The instrumentation patch worked: new phase-gate terms are now present in
  metrics.
- Result: `480` steps, reward mean about `1.510`, success `0.0`, lift `0.0`,
  position error mean about `0.296` and final about `0.403`. EE-to-cube and
  finger-center distances worsen to roughly `0.34 m` by the end.
- Key diagnosis: `cube_traj_tracking_close_action_reward` and
  `cube_traj_tracking_lift_action_reward` are exactly `0`; contact gate mean is
  only about `0.00167` and max about `0.00663`, while the closed-target gate is
  active by the end. The current gate makes close/lift shaping effectively
  silent for this policy.
- Worker B was instructed not to scale training, to record the metrics, and to
  run a bounded gate/reward diagnostic or ablation with inspectable report/video
  evidence.

Worker A reset-prior final RL:

- A100 job `28987954` remains running at about `1:51` elapsed. Stdout reached
  epoch `1213`; rank-0 JSONL reached epoch `1216`, frame `1274019840`.
- Best stdout reward improved to `2276.3032` around epoch `1202`.
- Latest interval checkpoints include epoch `1175` reward suffix `2247.8704`
  and epoch `1200` reward suffix `2227.9263`; best checkpoint file
  `dextrah_franka_cube_grasp.pth` was updated at epoch `1202`.
- Latest rank-0 scalars keep reset mechanics healthy:
  `cube_grasp_prior_reset_success_rate=1.0`, reset farther rate `1.0`, reset
  position error around `0.00185 m`, reset rotation error around `0.0186 rad`,
  and table-clearance violation `0.0`.
- Policy behavior is improving but still needs artifact validation: gripper is
  closing hard and finger-center distance is about `0.059 m`, but lift/success
  remain sparse in the sampled scalar stream. Continue monitoring and require
  eval/video evidence from a usable checkpoint before making the comparison
  claim.

## 2026-06-11 Monitor Check 21:31 UTC

Worker C DP BC mismatch:

- C committed/pushed the history-fix eval result as branch commit `b487ba6`.
- Chunk-size ablation job `1027746` completed `0:0` in `00:04:54`.
  Run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- Local fetched run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- Chunk-1 did not fix the bad video behavior. It delayed gripper closure but
  worsened geometry relative to chunk-8 history-fix:

| Setting | Success/Lift | Reward mean/final | EE-to-cube min/final | Finger-center min/final | First negative grip | Hard close |
| --- | --- | --- | --- | --- | --- | --- |
| chunk 8 history-fix | `0/0` | `1.6488/1.6844` | `0.1360/0.1371 m` | `0.1640/0.1695 m` | step `144` | step `168` |
| chunk 1 history-fix | `0/0` | `1.5820/1.5789` | `0.1458/0.1517 m` | `0.1686/0.1824 m` | step `207` | step `224` |

- Both traces have valid adjacent history gaps `[0, 1]`; chunk 1 has policy
  call deltas of `1`, chunk 8 has deltas of `8`.
- Chunk 1 still closes before the dataset mean first-close and hard-close
  timing (`~282.6` and `~310.6` steps), and it closes with incorrect
  cube-relative geometry. Final chunk-1 cube-minus-EE is approximately
  `[-0.0076, -0.1180, -0.0949]`, still far from the hard-close demo geometry.
- Interpretation: the remaining C bug is not primarily eight-step open-loop
  chunk drift. Continue train/eval bug search around action/trajectory target
  semantics, real-controller one-step action replay, sequence target alignment,
  reset/live state distribution, and predicted actions at matched demo states.
- Worker C was instructed to produce a chunk8-vs-chunk1 mismatch report/plot
  artifact and not to train or scale.

Worker B trajectory-tracking relaxed gate:

- Relaxed-gate env validation job `1027745` completed `0:0`; local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_relaxgate_env_smoke_20260611_142312`
- Result: 35/35 checks passed, reset obs `[4,72]`, no immediate dones, no
  nonfinite values, target unsafe max `0.0`, target clearance min `0.0651 m`.
  The relaxed gate is no longer silent: contact gate mean `0.6522`, contact
  distance gate mean `0.6774`, finger balance gate mean `0.9482`.
- Tiny RL smoke job `1027747` completed `0:0`; local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_relaxgate_rl_smoke_20260611_142540`
- RL smoke criteria passed: one GPU, 16 envs, 3 iterations, actor/central value
  MLP input `72`, no traceback/NaN, relaxed gate config `0.30/0.18`, and
  epoch-3 checkpoint written with reward suffix `5.782907`.
- Metrics eval job `1027748` completed `0:0`; local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_relaxgate_ep3_metrics480_20260611_142910`
- Eval result: 480 steps, no dones, reward mean/final `1.6774/1.3972`,
  success mean/final `0.00052/0.0`, last-window success `0.0`, target unsafe
  max `0.0`, target clearance min `0.0651 m`.
- Relaxed gate/action diagnostics are present and nonzero but weak:
  contact gate mean/final `0.560/0.388`, action-close mean/final
  `0.0289/0.0322`, action-up mean/final `0.0108/0.0169`, gripper-action
  mean/final `0.0207/0.0335`, close reward mean/final `0.00052/0.00128`, lift
  reward mean/final `0.00061/0.00183`.
- Behavior remains poor: EE-to-cube final `0.232 m`, finger-center final
  `0.227 m`, max-finger final `0.239 m`, gripper width final `0.0413 m`, cube
  lift final `0.0`. Worker B was instructed to generate the planned
  report/plot artifact and debug action-signal scale/weights or phase timing
  before any longer training.

Worker A reset-prior final RL:

- A100 job `28987954` remains running at about `2:01` elapsed. Stdout reached
  epoch `1322`; checkpoint `last_dextrah_franka_cube_grasp_ep_1300_rew_2244.6438.pth`
  was written. The best checkpoint remains at least the epoch-1202 reward
  `2276.3032` observed earlier.
- Continue monitoring. The run is not complete and still needs checkpoint
  selection, eval videos, metrics, and artifact inspection before the
  apple-to-apple claim can be made.

## 2026-06-11 Monitor Check 21:40 UTC

Artifact cadence and visual-debug directive:

- The user reported that Agent C's video drifts away/ignores the object and
  that Agent A's uploaded artifact also looks off because the robot is not
  grasping the cube. Treat both as likely implementation/debugging signals, not
  acceptable weak-policy artifacts.
- All three workers were instructed to fetch/upload compact artifacts more
  often: short labeled videos or first/middle/last frames, trace CSV/JSONL,
  plots, train-vs-eval consistency audits, exact commands/job ids, local paths,
  and `viz-open` URLs. Prefer frequent small bundles after every diagnostic,
  tiny smoke, meaningful checkpoint interval, or new-best checkpoint.
- For A, the next required bundle must separate reset-only evidence from policy
  rollout evidence. It must report cube center, sampled grasp, 3 cm pregrasp
  offset target, gripper/fingertip centers, gripper width, pose errors, and
  whether train/eval use the same reset path and root-relative conventions.
  The current reset-success scalar may only prove robot target tracking, not
  grasp-quality geometry.
- For C, no scale-up is allowed until official-DP action-semantics diagnostics
  and one-step/short-horizon controller replay prove the predicted and executed
  actions match dataset labels and move in the expected direction. Every eval
  video must be paired with action/history/chunk/object-pose traces.
- For B, every trajectory-tracking smoke/eval must include visual artifacts and
  reference/phase/reward/action traces before any longer training.

Worker A reset-prior visual concern:

- The active A100 job `28987954` is still numerically stable and reached epoch
  `1425` / frame `1.493B`. Recent stdout observed a new best checkpoint update
  around epoch `1422` with reward `2282.798`; interval checkpoint epoch `1425`
  had suffix `2248.1533`.
- Latest rank-0 scalar window still shows ideal reset-prior target tracking:
  `cube_grasp_prior_reset_success_rate=1.0`, reset position error about
  `0.0019 m`, reset rotation error about `0.018 rad`, and no reset-target
  failure in the sampled logs.
- Behavior remains suspicious despite reward improvement: mean success over the
  last 200 samples is about `1.5e-5`, mean lifted rate about `5.4e-4`, mean lift
  height about `0.00013 m`, finger-center distance about `0.059 m`, and the
  gripper is nearly always hard-closing.
- I extracted a first/middle/last-frame triptych from A's ep1325 eval video.
  The file is valid (`1280x720`, 353 frames, about 5.9 s), but visually the
  fingers are near the cube rather than clearly enclosing it, and the rollout
  does not grasp or lift. Agent A was told to debug transform/gripper-frame/
  reset-geometry and add a reset-grasp-quality diagnostic if the current scalar
  only checks target pose tracking.
- Current A eval viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_eval_ep1325_20260611_213227/videos/ggx-pregrasp-reset-ep1325-step-0-trimmed.mp4`

Worker B trajectory-tracking smoke concern:

- l401 job `1027751` (`franka_cube_traj_actionscale_rl`) completed `0:0`, but
  stdout saved checkpoint
  `last_dextrah_franka_cube_traj_tracking_ep_3_rew_-inf.pth` after warning
  `Max epochs reached before any env terminated at least once`.
- Agent B was told not to record this as a clean RL-smoke pass or scale-up
  evidence. The immediate B question is whether no-termination/`-inf` is an
  expected artifact of this very short RL-Games smoke or a wrapper/metric
  pathology that needs a different bounded eval route.

Worker C DP BC:

- C's latest committed evidence still says chunk-size 1 does not fix the
  drifting/early-close failure. C has an uncommitted
  `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py` diagnostic in
  progress and was re-instructed to finish it before any next training or RL
  handoff.

## 2026-06-11 Monitor Check 21:49 UTC

Worker B trajectory-tracking artifact refresh:

- B fetched and summarized diagnostic eval job `1027753` from the
  `rew_-inf` checkpoint. Branch commit:
  `830ad738a3d5ef33c4b7ec079eef1959f2ab8e7d`.
- Local eval artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318`
- Local summary artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
  - plot:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/trajectory_trace_plot.png`
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/report.md`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/actionscale_rewinf_contact_sheet.png`
- Metrics: `480/480` steps, reward mean/final `1.7957/1.4740`,
  success mean/final `0/0`, cube lift max/final `0.00117/0.0 m`, final
  EE-to-cube `0.2437 m`, final finger-center-to-cube `0.2417 m`, final
  gripper width `0.0369 m`, target unsafe max `0`, target clearance min
  `0.0651 m`.
- Train/eval consistency JSON passed for tracked fields: observation/action
  dimensions, cube spawn randomization, phase observations, reference duration,
  action weights, safety gates, and min gripper width.
- Visual inspection: first frame is black, but middle/final frames are valid.
  The hand approaches early and then drifts away; there is no grasp or lift.
- Interpretation: B currently shows weak learned actions/reference use rather
  than an obvious train/eval config mismatch. Close utilization mean is only
  about `0.0456` and lift utilization mean about `0.0014` despite nonzero
  gates. The `rew_-inf` suffix is expected for a 3-iteration smoke with no env
  termination, so B was assigned the next task of adding/using
  episode-independent rollout metrics and a bounded reference/controller
  feasibility sanity check before any longer RL training.

Worker C DP BC status:

- Offline diagnostics now show the DP checkpoint predicts correct hard-close
  behavior on exact demo hard-close rows, and EMA/raw checkpoints agree on the
  live failure. On live hard-close windows, the nearest demo row is still
  pregrasp/open gripper, but the policy predicts hard close. This points to
  live rollout distribution/support drift rather than a gripper-sign,
  normalizer, or history-cadence bug.
- Config audit says normalizer means match the dataset, PPO-to-lowdim slices
  match the 72D env layout, framefix action scale/frame metadata matches, and
  gripper sign physically closes. Live trace remains outside demo support in
  several EE/cube relative coordinates.
- C launched real-env teacher-forcing replay job `1027754`
  (`dextrah_cube_dp_replay`) on l401 with modes
  `dataset_t,dataset_t_plus_1,dataset_t_plus_7,dp_replan`, `STEPS=8`.
  The job is running and must be fetched/inspected before any BC warm-start
  claim.

## 2026-06-11 Monitor Check 21:54 UTC

Worker A reset-prior bug confirmed:

- A reset-only diagnostic job `1027755`
  (`franka_cube_ggx_pregrasp_reset_geometry_20260611_214944`) completed
  `0:0` on l401 from commit `17d5c5e6b68055540a6f020e2a5450afcda52311`.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944`
- Viewer URLs:
  - geometry video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/reset_geometry_frames.mp4`
  - first oblique frame:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/frames/reset_000_first_oblique.png`
  - side frame:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/frames/reset_000_last_side.png`
  - JSON:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_20260611_214944/reset_geometry.json`
- Result: old reset metric passes, but grasp-quality fails. `reset_success`
  is true for all 5 sampled resets, while `reset_grasp_quality_success` is
  false for all 5. CSV examples show gripper width about `0.080 m` and width
  margin `0.020 m`, but finger-center-to-cube is about `0.095-0.104 m`, and
  projected exact finger-center distance is about `0.066-0.074 m`.
- Visual inspection confirms the user's concern. The side frame shows the
  finger/tool above the cube rather than around it. Overlay for reset 0 reports
  exact tool about `0.134 m` above cube center, pregrasp about `0.164 m` above,
  and gripper center about `0.103 m` above cube center.
- Decision: active A100 training job `28987954` was canceled by the
  orchestrator because it is invalid for the intended apple-to-apple
  grasp-prior comparison. Slurm recorded `CANCELLED by 158351`, elapsed
  `02:24:51`; wrapper log says it did not requeue because time left exceeded
  the requeue window.
- A was instructed not to relaunch RL until reset-only artifacts pass. The next
  A work is to patch the low-level reset geometry, likely around GraspGenX
  tool frame vs Franka EE frame, exact grasp vs pregrasp convention,
  approach-axis/offset sign, or centered-object grasp pose compatibility with
  the DEXTRAH cube/gripper frame.

Worker C DP replay result:

- Replay job `1027754`
  (`franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800`)
  completed `0:0` on l401 and was fetched/inspected by C.
- Viewer URLs:
  - replay plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800/replay_motion.png`
  - replay report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800/replay_report.md`
  - inspection report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_report.md`
- Result: dataset and DP replay actions move in the expected direction at the
  reset state, so the controller/action frame is not grossly inverted there.

| mode | start EE-cube | final EE-cube | reward start/final | mean cosine | sign match |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dataset_t` | `0.2336` | `0.2317` | `1.3647/1.3673` | `0.836` | `1.000` |
| `dataset_t_plus_1` | `0.2336` | `0.2311` | `1.3647/1.3693` | `0.851` | `1.000` |
| `dataset_t_plus_7` | `0.2336` | `0.2268` | `1.3657/1.3819` | `0.904` | `0.958` |
| `dp_replan` | `0.2336` | `0.2293` | `1.3654/1.3741` | `0.875` | `0.958` |

- Interpretation: C's failure is not a gross controller/action-frame inversion
  at reset. The remaining DP bug is closed-loop live-state/support drift: later
  close windows are outside demo support and nearest train rows are still
  pregrasp/open while the policy commands hard close. C should continue with a
  bounded later-window teacher-forcing/reset-alignment diagnostic before any
  BC/RL scale-up.

Worker B trajectory tracking:

- B launched next bounded l401 job `1027757`
  (`franka_cube_traj_refdelta`) after completing the `rew_-inf` diagnostic.
  This job is part of the requested episode-independent/reference feasibility
  follow-up and needs the same artifact inspection before any scale-up.

## 2026-06-11 Monitor Check 21:59 UTC

Worker B reference-delta sanity result:

- B's policy-free `reference_delta` eval job `1027757`
  (`franka_cube_traj_tracking_refdelta_video480_20260611_145440`) completed
  `0:0` on l401 and artifacts are local.
- Local run artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_video480_20260611_145440`
- Local summary artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_video480_20260611_145440/videos/refdelta-video480-step-0.mp4`
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refdelta_artifacts_20260611_145440/trajectory_trace_plot.png`
- Metrics: `480/480` steps, reward mean/final `3.2933/1.8666`,
  success mean/final `0.0125/0.0`, last-window success mean `0.045`, done
  count `2`, cube lift max `0.0681 m`, final EE-to-cube `0.1966 m`, final
  finger-center-to-cube `0.2358 m`, final gripper width `0.0520 m`, target
  unsafe max `0`, target clearance min `0.0651 m`.
- Fixed-window summary: the middle window tracks the reference closely
  (`EE-to-target` mean `0.0035 m`, `EE-to-cube` mean `0.0389 m`) with no
  success; the last window has `lift max 0.0681 m` and success mean `0.05`,
  but the hand/cube geometry degrades by the final frame.
- Visual inspection: first frame is black, middle frame shows contact/enclosure
  around the cube, and final frame shows the hand moved away with the cube not
  stably lifted.
- Interpretation: the current trajectory reference and delta-IK action path are
  partially feasible; a simple non-policy reference-delta baseline can create
  contact and transient lift/success. The learned policy failure is therefore
  not explained by an impossible reference transform alone. Remaining B work is
  policy/action learning, reward timing/hold incentives, and orientation/contact
  quality. The result is still diagnostic only: `reference_delta` is a
  position-only delta-IK plus gripper schedule baseline, not cuRobo joint replay
  and not a learned policy result.

Worker C later-window replay:

- C launched l401 job `1027759`
  (`franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`)
  with modes `dataset_open_t_plus_7,dp_replan`, `STEPS=320`. This job is meant
  to test the later close-window support issue after the reset-time replay
  showed the controller/action frame is not grossly inverted.
