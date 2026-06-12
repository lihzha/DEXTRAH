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

## 2026-06-11 Monitor Check 22:11 UTC

Artifact cadence escalation:

- User reported that A's uploaded artifact also looked off: the robot was not
  visibly grasping the cube. I interrupted all three workers with a stricter
  artifact contract.
- New requirement for every meaningful smoke/diagnostic/eval/checkpoint loop:
  fetch/upload a viewer-ready bundle with run id, commit, config, log path,
  metrics JSON/CSV, plots, videos or labeled frames/contact sheets, worklog
  entry, `viz-open` URLs/paths, and a short pass/fail interpretation.
- Long training runs, when allowed, must produce artifacts at least every
  checkpoint or about every 30 minutes wall-clock. No worker may scale a run
  whose video drifts, ignores the cube, or lacks a train/eval/config audit.

Worker A reset-prior status:

- TCP-aware reset diagnostic job `1027761`
  (`franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608`) completed
  `0:0` on l401 and artifacts were fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608/reset_geometry_frames.mp4`
  - JSON:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608/reset_geometry.json`
  - side frame:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608/frames/reset_000_last_side.png`
  - top frame:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_reset_geometry_tcp_20260611_150608/frames/reset_000_middle_top.png`
- Metrics: `reset_success_rate=1.0`, `reset_quality_success_rate=1.0`,
  `immediate_done_rate=0.0`, `projected_exact_tip_center_dist_mean_m=0.0301`,
  `projected_exact_tip_max_dist_mean_m=0.0502`,
  `projected_exact_tip_table_clearance_mean_m=0.0650`,
  `pregrasp_tip_table_clearance_mean_m=0.0950`, `offset_radial_dot_mean=0.99999`.
- Interpretation: the prior frame/metric bug was at least partly diagnostic:
  `panda_hand` and finger body origins made the reset look much worse than the
  controlled TCP/tip-proxy geometry. However, the visible robot is intentionally
  at the open 3 cm pregrasp, not already holding the cube. To avoid confusing
  this with a failed grasp, A must produce a second bounded artifact showing
  the corresponding exact grasp/close check before any A100 relaunch.

Worker C DP BC status:

- Later-window replay job `1027759`
  (`franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`)
  completed `0:0` and was fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`
- Viewer URLs:
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800/replay_motion.png`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800/replay_report.md`
- Metrics: `dataset_open_t_plus_7` stalls around final EE-cube `0.2124 m`
  with gripper forced open; `dp_replan` moves to final EE-cube `0.1463 m` but
  nearest-demo distance grows beyond `1.1`, nearest phase remains
  `go_to_pre_grasp_pose`, and hard close starts around step `224`.
- Interpretation: this supports the closed-loop live-state/support-drift
  hypothesis, not BC readiness. C should continue bounded diagnostics with
  closed-loop video/contact sheets and train/eval audits before any scale-up.

Worker B trajectory tracking status:

- Action-alignment env smoke job `1027763`
  (`franka_cube_traj_tracking_actionalign_env_smoke_20260611_150840`)
  completed `0:0` on l401.
- Metrics from the log: validation passed; observation remained `[4,72]`;
  `done_count=0`; early done count `0`; target unsafe max `0.0`; target table
  clearance min `0.0651`; action-alignment logs present and finite;
  action-alignment reward mean `0.3233`; utilization mean `0.4908`.
- Interpretation: B's new diagnostic wiring is valid. Next step is a tiny PPO
  smoke followed by short eval/video/contact-sheet artifacts under the new
  artifact cadence. No scale-up.

## 2026-06-11 Monitor Check 22:14 UTC

Worker B artifact lineage clarification:

- User asked whether
  `actionscale-rewinf-diag-video480-step-0.mp4` was from Agent B. Yes: it is
  B's earlier failed learned-policy diagnostic artifact, not the current
  action-alignment run.
- Viewer URLs:
  - old failed learned-policy video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
  - old failed learned-policy report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_artifacts_20260611_144318/report.md`
- Metrics for that old video: success mean/final `0.0/0.0`, cube lift max
  `0.001168 m`, final EE-to-cube `0.243735 m`, final finger-center-to-cube
  `0.241670 m`, lift-action utilization mean `0.001401`, and train/eval
  consistency passed. Visual failure matches the metrics.
- B has since produced two more useful diagnostics: `reference_delta` showed
  policy-free reference following can make contact/transient lift, and job
  `1027763` showed action-alignment reward/log wiring is finite and target-safe.
- B branch now includes lineage clarification commit
  `1473033 Clarify trajectory diagnostic artifact lineage`; B worktree is clean
  at that commit. No B l401/a100 job is active yet. Next expected step remains
  the bounded tiny PPO smoke plus video/contact-sheet eval bundle.

## 2026-06-11 Monitor Check 22:17 UTC

Worker B tiny PPO smoke:

- B launched and completed l401 job `1027766`
  (`franka_cube_traj_align_rl`) for the bounded action-alignment PPO smoke.
- Run name:
  `franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`
- Remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`
- Local artifact copy:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1027766.out`
- Checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_traj_tracking/franka_cube_traj_tracking_actionalign_rl_smoke_20260611_151520/nn/last_dextrah_franka_cube_traj_tracking_ep_5_rew_-inf.pth`
- Scheduler/log result: completed `0:0` after `00:00:53`; actor/critic built with
  MLP input `72`; epochs `1/5` through `5/5`; checkpoint saved; no traceback or
  NaN observed in the tailed log.
- Resolved config spot check from fetched YAML: obs/state/action
  `72/72/7`, `cube_spawn_xy_randomization=0.08`,
  `trajectory_tracking_reference_path` points to the intended compact reference,
  `trajectory_tracking_action_alignment_weight=1.5`, phase start `0.0`,
  sharpness `1.0`, contact gate `false`, PPO horizon `32`, max epochs `5`,
  minibatch `512`.
- Local TensorBoard scalar decoding was attempted but unavailable because the
  local Python environment lacks `tensorboard`. The event file and resolved
  configs are fetched for later inspection.
- Interpretation: this proves the bounded PPO smoke can run and checkpoint with
  the action-alignment diagnostic enabled. The `rew_-inf` suffix is expected in
  this five-epoch smoke because no env terminated; it is not a policy-quality
  verdict. B must run the fixed-seed and random-seed video eval bundles from
  this checkpoint before any further training or scale-up.

## 2026-06-11 Monitor Check 22:22 UTC

Worker C closed-loop DP support trace:

- C's support-trace eval job `1027767`
  (`franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`)
  completed `0:0` and was fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/videos/franka-cube-dp-policy-eval-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/dp_supporttrace_contact_sheet.jpg`
- Metrics: success/lift stayed zero; final EE-to-cube `0.146 m`;
  final finger-center-to-cube `0.173 m`; final gripper width `0.0008 m`;
  nearest-demo phase was `go_to_pre_grasp_pose` for all `320` steps; nearest
  demo distance grew `0.354 -> 1.129`; first negative gripper at step `208`,
  first hard close at step `225`.
- Visual inspection: the contact sheet shows the hand remaining away from the
  cube while closing. This confirms C's original bad-video concern as a real
  closed-loop support-drift/train-eval mismatch. No BC/RL scale-up.

Worker B action-alignment PPO eval:

- Fixed eval job `1027769` and random eval job `1027770` completed `0:0` and
  were fetched locally.
- Local fixed artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420`
- Local random artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420`
- Viewer URLs:
  - fixed video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420/videos/actionalign-rl5-fixed-video480-step-0.mp4`
  - fixed contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_fixed_video480_20260611_152420/actionalign_fixed_contact_sheet.jpg`
  - random video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420/videos/actionalign-rl5-random-video480-step-0.mp4`
  - random contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionalign_rl5_eval_random_video480_20260611_152420/actionalign_random_contact_sheet.jpg`
- Fixed metrics: success mean/final/last `0/0/0`, cube lift max `0.0015 m`,
  final EE-to-cube `0.596 m`, final finger-center-to-cube `0.561 m`.
- Random metrics: success mean/final/last `0/0/0`, cube lift max `0.0 m`,
  final EE-to-cube `0.417 m`, final finger-center-to-cube `0.378 m`.
- Action diagnostics: action-alignment utilization was nonzero
  (`0.347` fixed, `0.401` random), but learned close/up actions stayed too weak
  or wrong. Random run had mean policy up `0.036` versus mean reference up
  `0.803`, and both runs ended with close action `0.0`.
- Visual inspection: both contact sheets show the hand moving away/around the
  cube rather than grasping. The action-alignment reward alone did not fix B's
  learned-policy behavior. No scale-up.

Worker A exact-close reset-prior gate:

- A's exact-close diagnostic job `1027771`
  (`franka_cube_ggx_pregrasp_exact_close_20260611_221828`) completed `0:0` and
  was fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_20260611_221828`
- Viewer URLs:
  - reset JSON:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_20260611_221828/reset_geometry.json`
  - exact-close side frame:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_20260611_221828/frames/reset_000_phase2_exact_close_last_side.png`
- Metrics: pregrasp reset gate passed (`reset_success_rate=1.0`,
  `reset_quality_success_rate=1.0`, `pregrasp_reset_gate_pass=true`), but the
  exact-close aggregate gate failed (`exact_close_gate_pass=false`,
  `rl_relaunch_gate_verdict=FAIL`). Exact-close enclosure and contact-proxy
  success were only `0.4`; tip-center mean `0.082 m`; tip-max mean `0.087 m`;
  cube displacement mean `0.0365 m`.
- Interpretation: the displayed sample can look plausible, but the sampled
  grasp library is not reliable enough across randomized resets. A must
  diagnose/filter grasp samples or fix exact-close execution before any A100
  relaunch.

## 2026-06-11 Monitor Check 22:46 UTC

Worker handoff state:

- B handed off and committed
  `6dc3fd2 Record action alignment eval failure` on
  `codex/franka-cube-trajectory-tracking`. Its comparison artifact bundle
  records the failed action-alignment PPO eval and proposes a bounded
  `policy_reference_mix` eval-only diagnostic at several blend coefficients.
  No B Slurm jobs are active.
- A committed `0e309ee Render all exact close diagnostic resets` on
  `codex/franka-cube-ggx-pregrasp-reset`. Its worklog records a pass/fail report
  for exact-close job `1027771`, observed PASS grasp indices `[6, 23]`, observed
  FAIL indices `[4, 19, 18]`, and a filtered-library rerun plan with
  `RENDER_ALL_RESETS=1`. No A Slurm jobs are active yet.
- C recorded the support-trace failure in its worklog and is editing
  `eval_franka_cube_dp_policy.py` plus the DP eval wrapper for a
  demo-conditioned reset diagnostic. No C Slurm jobs are active yet.
- Current orchestrator decision remains: all three branches are in bounded
  diagnostic/debug mode. No A100 or long-scale RL/BC run is allowed from the
  current artifacts.

## 2026-06-11 Monitor Check 23:00 UTC

User artifact lineage question:

- `actionscale-rewinf-diag-video480-step-0.mp4` is from Worker B's trajectory
  tracking branch, but it is an older failed learned-policy diagnostic from the
  action-scale experiment:
  `franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318`.
- Viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
- It is not evidence that B is currently progressing. The artifact report had
  zero success/lift, final EE-to-cube about `0.244 m`, final finger-center to
  cube about `0.242 m`, and visual drift/hovering rather than grasp.
- B's newer action-alignment PPO eval also failed behaviorally, so B has been
  asked to continue with an eval-only `policy_reference_mix` diagnostic at
  blend coefficients `0.25`, `0.50`, `0.75`, and `1.0`, with per-run videos,
  traces, plots, contact sheets, consistency checks, and pass/fail reports.

Worker A filtered exact-close gate:

- Filtered exact-close diagnostic job `1027772`
  (`franka_cube_ggx_pregrasp_exact_close_filtered_20260611_222557`) completed
  `0:0` and was fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_filtered_20260611_222557`
- Viewer URLs:
  - reset JSON:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_filtered_20260611_222557/reset_geometry.json`
  - all-reset contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_filtered_20260611_222557/inspection_20260611_2228/all_reset_contact_sheet.png`
  - all-reset exact-close video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_exact_close_filtered_20260611_222557/inspection_20260611_2228/all_reset_exact_close_frames.mp4`
- Metrics: pregrasp remains good (`reset_success_rate=1.0`,
  `reset_quality_success_rate=1.0`, `pregrasp_reset_gate_pass=true`,
  immediate done rate `0.0`), but exact-close still fails:
  enclosure/contact-proxy success `0.2`, exact-close tip-center mean
  `0.04447 m`, cube displacement mean `0.01971 m`, and
  `rl_relaunch_gate_verdict=FAIL`.
- Visual interpretation: the robot is not far away from the cube; this is a
  robustness/contact geometry failure. Pass-index filtering from job `1027771`
  is not stable under new reset/object randomization. A has been told not to
  launch A100 RL and to move to grasp-pose convention/TCP/tool/finger-axis and
  object-transform robustness diagnostics.

Worker C active demo-conditioned reset eval:

- C committed `7913a82` and launched l401 job `1027773`
  (`franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`).
- Remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027773.out`
- Early log confirms the selected demo row is loaded (`episode=24`, row
  `16868`, phase `go_to_pre_grasp_pose`) and the reset matches cube position
  exactly with lowdim infinity diff about `0.010 m`. Through step `64`, success
  and lift remain zero.
- Interpretation so far: if this persists through the final artifact bundle,
  C's drift is not explained by object/cube reset mismatch alone; likely next
  checks are robot/pregrasp alignment, history seeding, observation semantics,
  or policy rollout/action interpretation. Job `1027773` is still active and
  needs artifact inspection before any conclusion.

## 2026-06-11 Monitor Check 23:08 UTC

Worker C demo-conditioned reset result:

- C's l401 job `1027773`
  (`franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`)
  completed `0:0` and was fetched locally.
- Local artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700/videos/franka-cube-dp-policy-eval-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700/dp_demoreset_contact_sheet.jpg`
- Video validation: `1280x720`, `319` frames, `5.316667 s`.
- Metrics: `final_success_rate=0.0`, `window_success_rate=0.0`,
  cube-lift max/final `0.0`, `final_gripper_width=0.0009156 m`,
  final finger-center-to-cube `0.1619 m`, reward mean/final
  `1.6533/1.7558`, support trace records `320`.
- Demo reset matched the selected object state: `cube_pos_l2_diff=0.0`,
  lowdim infinity diff about `0.010 m`, and cube-minus-EE L2 diff about
  `0.0109 m` at reset.
- Visual inspection: the hand starts offset from the cube and drifts farther
  away while closing. This confirms the C failure is not explained by object
  pose randomization alone.
- C has been asked to continue with robot-state/demo alignment, open-loop demo
  action replay if feasible, history seeding, observation conversion, action
  normalization/order/sign, and gripper convention diagnostics. No BC/RL
  scale-up.

Current worker/scheduler state:

- l401 and a1001 queues are empty for `lzha` at this poll.
- B is editing `eval_rollout.py`, the eval wrapper, summarizer, and its owned
  worklog for the `policy_reference_mix` diagnostic.
- A has an owned worklog modification after receiving the filtered exact-close
  failure. No A100 RL launch is allowed.
- C is clean locally after the demo-reset run but has been handed the next
  diagnostic assignment.

## 2026-06-11 Monitor Check 23:42 UTC

Worker A reset-prior gate update:

- Same-grasp zero-width exact-close diagnostics completed and were inspected:
  - `1027775` deterministic XY, single grasp orig006, zero-width close:
    exact-close enclosure/contact `0.0`, pregrasp gate `1.0`.
  - `1027776` randomized XY, same grasp, zero-width close: exact-close
    enclosure/contact `0.2`, pregrasp gate `1.0`.
- Local zero-width artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_same_grasp_orig006_detxy_20260611_222927`
  and
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_same_grasp_orig006_randxy_20260611_222927`
- Visual interpretation: the gripper stays in the cube neighborhood and the
  object transform is coherent, but zero-width exact close ends offset/marginal
  relative to the cube. This points to close-command mechanics rather than an
  XY transform bug.
- Light-close follow-up diagnostics completed and passed:
  - `1027781` deterministic same-grasp light close with
    `EXACT_CLOSE_COMMAND_WIDTH=0.055`: enclosure/contact `1.0`, cube delta mean
    `0.00634 m`, `rl_relaunch_gate_verdict=PASS`.
  - `1027782` randomized same-grasp light close with
    `EXACT_CLOSE_COMMAND_WIDTH=0.055`: enclosure/contact `1.0`, cube delta mean
    `0.00647 m`, `rl_relaunch_gate_verdict=PASS`.
- Viewer URLs:
  - deterministic light-close sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_same_grasp_orig006_detxy_lightclose_20260611_223441/inspection_20260611_2242/contact_sheet.png`
  - randomized light-close sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_same_grasp_orig006_randxy_lightclose_20260611_223441/inspection_20260611_2242/contact_sheet.png`
  - randomized light-close report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_same_grasp_orig006_randxy_lightclose_20260611_223441/inspection_20260611_2242/REPORT.md`
- Orchestrator decision: the user's requested A variant resets to open
  3 cm-offset pregrasp, not a zero-width grasp. The current acceptance gate is
  pregrasp reset quality plus light-close feasibility, which passes under
  RL-style cube randomization. A is unblocked for one bounded RL smoke/eval with
  frequent artifacts, but not for full final-scale A100 training yet.

Worker B policy-reference mix diagnostic:

- B committed `354c9c9 Add policy-reference mix eval diagnostic` and launched
  alpha sweep jobs `1027777`-`1027780`.
- Alpha `0.25`, `0.50`, and `0.75` completed with zero success/lift. Higher
  alpha improved reward and approach, but videos show the hand approaches near
  the cube mid-rollout and then departs, leaving the cube on the table.
- Alpha `1.0` completed with transient success/lift:
  `success_rate_mean=0.01875`, `success_rate_last_window_mean=0.0675`,
  max lift about `0.102 m`, but `success_rate_final=0.0`.
- Viewer URLs:
  - alpha `0.25` quick sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a025_video480_20260611_153442/contact_sheet_quick.jpg`
  - alpha `0.50` quick sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a050_video480_20260611_153442/contact_sheet_quick.jpg`
  - alpha `0.75` quick sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a075_video480_20260611_153442/contact_sheet_quick.jpg`
  - alpha `1.0` quick sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/contact_sheet_quick.jpg`
  - alpha `1.0` video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/videos/policy-refmix-a10-video480-step-0.mp4`
- Interpretation: the transformed reference/action interface is partially
  feasible because alpha `1.0` can transiently grasp/lift. The problem is
  timing/phase/hold stability: the trajectory/reference does not preserve final
  grasp/lift. B has been asked to produce the full comparison report and then
  test a bounded terminal-hold/reference-stabilization variant before any PPO
  tracking-loss scale-up.

Current scheduler state:

- l401 queue was empty after fetching B alpha `1.0` and A light-close
  diagnostics.

## 2026-06-11 Monitor Check 22:49 UTC

Direct user question: `actionscale-rewinf-diag-video480-step-0.mp4`

- Answer: yes, this video is from Worker B / Popper's trajectory-tracking
  branch, but it is an older failed learned-policy diagnostic, not the current
  best B artifact.
- Artifact:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
- Interpretation: this run drifted/hovered away from the cube and did not
  grasp. Use it as evidence of a previous failure mode, not as evidence that
  B's current reference/action path is working.

Worker B current state:

- Current useful B signal is the policy-reference mix sweep, especially alpha
  `1.0`.
- Alpha `1.0` recovered transient contact/lift:
  `success_rate_mean=0.01875`, `success_rate_last_window_mean=0.0675`,
  `success_rate_final=0.0`, max lift about `0.102 m`.
- This suggests the transformed reference/delta-IK action interface can reach
  and lift transiently, but timing/phase/terminal hold is wrong. It is not a
  learned-policy success and does not authorize PPO scale-up.
- Current artifact:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_policy_refmix_a10_video480_20260611_153442/videos/policy-refmix-a10-video480-step-0.mp4`
- Orchestrator instruction sent to B: continue with a bounded terminal hold /
  reference-stabilization diagnostic and upload artifacts for every run; no
  long PPO tracking-loss training yet.

Worker C demo-reset fixed-label replay:

- Job `1027792` completed `0:0`:
  `franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`.
- Local artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`
- Viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/videos/franka-cube-dp-replay-demoreset-fixedlabels-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_contact_sheet.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_motion.png`
- Metrics:
  - fixed `dataset_open_t_plus_7`: final EE-cube `0.1861 m`, final
    finger-cube `0.1757 m`.
  - fixed `dataset_t`: final EE-cube `0.1848 m`, final finger-cube
    `0.1746 m`.
  - `dp_replan`: min EE-cube `0.1314 m`, final EE-cube `0.1323 m`, final
    finger-cube `0.1619 m`, final gripper width `0.0009 m`.
- Important report finding: demo cube reset matches, but
  `exact_robot_joint_reset_available=false`; the converted lowdim NPZ has no
  Franka joint state, so the robot remains at task reset. Fixed-label replay
  therefore starts from a robot state that does not actually match the selected
  demo robot state.
- Orchestrator interpretation: do not treat C's wrapper verdict as sufficient.
  The video/metrics are not acceptable for BC warm start. C must first prove
  replay from a matched robot state, either by recovering Franka joint state or
  resetting by IK to the dataset EE pose/cube-minus-EE, and must audit action
  semantics before more BC/RL.

Current scheduler state:

- After the B nudge, B implemented the hold diagnostic at local/remote commit
  `d8956ac8131e26130ebba16be6082119c71e22a7` and launched job `1027825`
  (`refmix_hold_a10`) on l401.
- B run:
  `franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910`.
- B log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_1027825.out`.
- C job `1027792` is complete and artifacts are fetched.
- Continue monitoring A/B/C; do not launch final-scale RL until bounded
  diagnostics produce visually and quantitatively acceptable artifacts.

## 2026-06-11 Monitor Check 22:53 UTC

Worker A bounded reset-prior smoke/eval:

- A reported completion and the orchestrator inspected the report/contact
  sheet.
- Branch: `codex/franka-cube-ggx-pregrasp-reset`.
- Latest pushed A commit: `cdaf066ce9e06eb38a1bf57be78bbdb6df22b4aa`.
- Smoke source commit: `1d3a8e30d2410413a83c8e3e2d6224f4a95ae7fe`.
- Jobs:
  - reset-prior RL smoke `1027808`: `COMPLETED 0:0`.
  - reset-prior eval/video `1027817`: `COMPLETED 0:0`.
- Viewer artifacts:
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_smoke_ep10_eval_20260611_224608/inspection_20260611_2248/REPORT.md`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_smoke_ep10_eval_20260611_224608/inspection_20260611_2248/contact_sheet.png`
  - geometry trace:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_smoke_ep10_eval_20260611_224608/inspection_20260611_2248/eval_geometry_trace.png`
  - eval video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_smoke_ep10_eval_20260611_224608/videos/franka-cube-ggx-pregrasp-smoke-ep10-step-0.mp4`
- Metrics:
  - smoke JSONL records `45`, bad scalar count `0`.
  - prior attempted/success/farther/quality rates all `1.0`.
  - eval max lift `0.01417 m` around step `56`, but success/lift flags stay
    `0`.
  - eval min EE-cube `0.0496 m`, final EE-cube `0.6780 m`; min
    finger-center `0.0870 m`, final finger-center `0.6852 m`.
- Visual interpretation: first frame is the intended open pregrasp; the policy
  briefly interacts/bumps the cube around steps `40-60`, then drifts far away.
- Orchestrator verdict: reset/pregrasp gate `PASS`, smoke runtime/checkpoint
  gate `PASS`, policy/eval scale-up gate `FAIL`; final A100 remains blocked.
- Instruction sent to A: run a matched prior-disabled 1-GPU/64-env/45-epoch
  baseline smoke/eval with the same cube randomization, seeds if compatible,
  checkpoint/eval cadence, and viewer artifact contract. No A100 launch.

Worker B terminal-hold diagnostic:

- Job `1027825` (`refmix_hold_a10`) completed `0:0`; source commit
  `d8956ac8131e26130ebba16be6082119c71e22a7`.
- Run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910`.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910`.
- Viewer artifacts:
  - video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910/videos/refmix-hold-a10-video480-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910/contact_sheet_quick.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/report.md`
  - trace plot:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_a10_video480_20260611_154910_artifacts/trajectory_trace_plot.png`
- Metrics:
  - success mean/final `0.0 / 0.0`; cube lift max `0.0 m`.
  - final EE-cube `0.1128 m`, final finger-center-cube `0.1538 m`.
  - final gripper width `0.0002 m`.
  - hold active mean/final `0.746 / 1.0`.
  - lift/success trigger rates `0.0 / 0.0`; hold activated via the loose
    contact-distance trigger.
- Visual interpretation: gripper approaches near the cube and closes in free
  space; the cube stays on the table.
- Orchestrator verdict: the first hold variant failed. The hold trigger was too
  loose and fired before a real grasp/lift. This does not unblock PPO scale-up.
- Instruction sent to B: compare against the previous alpha `1.0` transient
  lift trace, identify the actual lift window/conditions, then rerun a stricter
  hold that triggers only after real lift/success or the known lift window.
  Also clean up train/eval consistency reporting so expected eval overrides are
  not mixed with real mismatches.

Current scheduler state:

- l401 was empty immediately before A was assigned the matched baseline and B
  was assigned the stricter hold follow-up. Continue polling for new worker
  launches.

## 2026-06-11 Monitor Check 23:09 UTC

Worker B offset-hold diagnostic:

- Job `1027851` (`refmix_hold_offset`) completed `0:0` from B commit
  `0a8cf038bae6a12b26ff94cb6dc837c5c98da06d`.
- Run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358`.
- Local artifacts:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358`.
- Viewer artifacts:
  - video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358/videos/refmix-hold-offset-a10-video480-step-0.mp4`
  - selected contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/contact_sheet_selected.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/report.md`
  - trace plot:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/trajectory_trace_plot.png`
- Metrics:
  - `done_count=3`, transient `success_rate=0.75` from steps `363-373`,
    success mean/final `0.01875 / 0.0`.
  - max cube lift `0.10894 m`; target unsafe max `0.0`.
  - final EE-cube `0.1190 m`, final finger-center-cube `0.1601 m`, final
    gripper width `0.0660 m`.
  - hold activated from actual lift at mean trigger step `319`; contact/phase
    trigger rates stayed `0.0`.
  - train/eval consistency report passed with no real mismatches; eval-only
    overrides are listed separately.
- Visual interpretation: the selected frames and trace show a real transient
  lift/success event followed by reset/drop behavior. The final frame looks
  failed because the eval artifact continues after success resets; this is not
  the same failure mode as the earlier drift-only videos.
- Orchestrator verdict: B has a promising reference/hold diagnostic, but the
  artifact contract is not yet clear enough for PPO scale-up. Need explicit
  `success_ever`/done-reason reporting and a success-window/no-auto-reset video
  before deciding whether this trajectory variant is valid.
- Instruction sent to B: update B worklog/report with the transient-success
  interpretation and run one artifact-focused diagnostic for per-env
  success/done semantics. No PPO scale-up yet.

Worker C source-joint reset replay:

- Job `1027846` (`dextrah_cube_dp_replay`) completed `0:0`.
- Run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`.
- Local artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`.
- Viewer artifacts:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/videos/franka-cube-dp-replay-sourcejoint-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_contact_sheet.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_motion.png`
- Metrics:
  - exact source robot joint reset is now available and applied:
    `joint_linf_diff_after_write_env0=0.0`, lowdim/cube/EE diffs are about
    `1e-6` or lower.
  - fixed `dataset_open_t_plus_7`: final EE-cube `0.1902 m`.
  - fixed `dataset_t`: final EE-cube `0.1889 m`; first negative gripper action
    around step `297`.
  - `dp_replan`: final EE-cube `0.1276 m`, final finger-center-cube `0.1613 m`.
- Visual interpretation: the reset is no longer the blocker, but the robot
  still stays offset and never grasps in the source-joint replay video.
- Orchestrator verdict: C should stop spending cycles on reset mismatch and
  pivot to action/control semantics. The next bounded diagnostic should compare
  dataset action labels against actual live EE displacement under the Isaac
  controller at the same control rate, including action scaling, gripper
  sign/width mapping, quaternion/axis convention, and temporal offset.
- Instruction sent to C: produce an action-semantics audit artifact bundle
  before any further BC/RL training.

## 2026-06-11 Monitor Check 23:17 UTC

Worker A paired 200-epoch small PPO comparison:

- A planned, committed, deployed, and launched the next bounded apple-to-apple
  smoke pair. No A100 launch.
- A worktree commit: `1b8652d33ad56a5ae02a689fc31cd13b9219702d`.
- Prior-enabled job:
  - job_id: `1027853`
  - run: `franka_cube_ggx_pregrasp_long200_1gpu_20260611_2311`
  - run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_ggx_pregrasp_long200_1gpu_20260611_2311`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/franka_cube_smoke_1027853.out`
  - config delta: `GRASP_PRIOR_RESET_ENABLED=True`,
    `GRASP_PRIOR_LIBRARY_PATH=/results/franka_cube_grasp_prior/franka-cube-ggx-pregrasp-reset/franka_cube_ggx_grasp_orig006_single.npz`
- Prior-disabled baseline job:
  - job_id: `1027854`
  - run: `franka_cube_baseline_noprior_long200_1gpu_20260611_2311`
  - run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_cube_grasp/franka_cube_baseline_noprior_long200_1gpu_20260611_2311`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/franka_cube_smoke_1027854.out`
  - config delta: `GRASP_PRIOR_RESET_ENABLED=False`, no prior library override.
- Common config: l401 `batch`, 1 GPU, `NUM_ENVS=64`,
  `MAX_ITERATIONS=200`, `SAVE_FREQUENCY=25`, `HORIZON_LENGTH=64`,
  `MINIBATCH_SIZE=4096`, `CENTRAL_VALUE_MINIBATCH_SIZE=4096`,
  `SEED=20260620`, `CUBE_SPAWN_XY_RANDOMIZATION=0.08`,
  `DEXTRAH_RLGAMES_JSONL_METRICS=True`, `USE_CUDA_GRAPH=True`.
- Early monitor:
  - both jobs running and saving checkpoints.
  - prior reached at least epoch `98`; baseline reached at least epoch `110`.
  - no bad scalars in either direct-info JSONL.
  - prior aggregate checkpoint rewards: epoch 25 `719.01544`, epoch 50
    `595.4116`.
  - baseline aggregate checkpoint rewards: epoch 25 `643.44666`, epoch 50
    `567.51636`.
  - direct task metrics at current snapshot: prior success/lifted max
    `0.0 / 0.0`, prior min EE-cube `0.0798 m`; baseline success max `0.0`,
    lifted-rate max `0.015625`, min EE-cube `0.0853 m`.
- Orchestrator interpretation: early learning still does not solve the task.
  Continue to full 200 epochs, then require checkpoint/eval videos before any
  scale-up decision.

Worker B current state:

- B acknowledged job `1027851` as a transient-success/reset-semantics artifact.
- B generated additional local artifacts for the success window, including:
  `success_window_slow_step300_380.mp4` and
  `success_window_contact_sheet.jpg` under
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts`.
- B is patching eval instrumentation for `success_ever`, first/last success
  step, done-ever/done-after-success, per-step done rates, and done-reason
  snapshots. Planned next job: one bounded 390-step offset-hold eval with the
  same config as `1027851`, no PPO scale-up.

Worker C current state:

- C produced a focused action-realization report from source-joint replay job
  `1027846`:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/sourcejoint_action_realization_existing1027846.md`
- Plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/sourcejoint_action_realization_existing1027846.png`
- Key finding: exact reset is ruled out as the cause. Dataset labels point in
  the expected direction, but realized EE displacement is far too small:
  early approach commands request roughly `6-13 mm` translation while Isaac
  realizes about `0.3-1.2 mm`.
- C is patching replay diagnostics to log first-class action-semantics fields
  and per-mode videos before any BC/RL scale-up.

## 2026-06-11 Monitor Check 23:22 UTC

Worker B success-window artifact inspection:

- B's added success-window artifact clarifies the confusing full-run video.
- Viewer URLs:
  - success-window slow video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_slow_step300_380.mp4`
  - success-window contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_a10_video480_20260611_160358_artifacts/success_window_contact_sheet.jpg`
- Video metadata: 1280x720, 134 frames, 5.36 s, 25 FPS.
- Visual interpretation: the isolated frames show a real interaction/lift
  window: pre-trigger around step `300`, lift trigger at step `319`, held/lift
  frames at steps `340`, `363`, and `373`, then post-reset at step `380`.
  This supports the transient-success interpretation and explains why the full
  video ending looks off.
- B still needs a first-class `success_ever`/done-reason eval artifact before
  PPO scale-up.

Worker C action-realization audit result:

- Job `1027855` completed `0:0`:
  `franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`.
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`.
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`.
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/replay_report.md`
  - action audit plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/action_realization_audit.png`
  - videos:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-0.mp4`
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-96.mp4`
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-192.mp4`
- Report verdict: controller follows the expected dataset action direction but
  under-realizes one-step action magnitude for `dataset_t` and
  `dataset_t_plus_7`.
- Mode summary:
  - `dataset_t`: final EE-cube `0.1887 m`, median xyz realization ratio
    `0.0932`, mean target error `0.00294`.
  - `dataset_t_plus_7`: final EE-cube `0.1900 m`, median xyz realization
    ratio `0.0947`, mean target error `0.00279`.
  - `dp_replan`: final EE-cube `0.1657 m`, median xyz realization ratio
    `0.0849`, mean target error `0.00699`.
- Orchestrator interpretation: BC data/execution is blocked by controller
  semantics. The next C diagnostic should be a replay-only action multiplier or
  action-repeat sweep, not training.
- Instruction sent to C: run a bounded compensation sweep around multipliers
  `3`, `6`, `10` and/or repeats `2`, `4`, `8`, with exact source-joint reset
  and per-mode videos/audit plots. No BC/RL scale-up.

## 2026-06-11 Monitor Check 23:28 UTC

User artifact-provenance question:

- The video
  `actionscale-rewinf-diag-video480-step-0.mp4` is from Worker B/Popper's
  older action-scale/reward-inference diagnostic.
- Viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
- That video is not B's current best result; it is a failed diagnostic where
  the learned policy drifts/hovers away and does not grasp the cube.
- B's current useful artifact remains the offset-hold reference replay with a
  transient success window, including:
  - full video:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503/videos/refmix-hold-offset-successwin390-step-0.mp4`
  - keyframe sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/contact_sheet_keyframes.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_successwin390_20260611_161503_artifacts/report.md`
- Current B interpretation: B has a real transient grasp/lift signal
  (`success_ever=3/4`, `success_rate_max=0.75`, max lift about `0.10894 m`),
  but not a stable final hold/training result.

Worker A paired 200-epoch eval inspection:

- All five eval jobs completed cleanly: `1027857` through `1027861`.
- Local fetched dirs are under
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401`.
- Prior-enabled ep200 contact sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_long200_eval_ep200_20260611_2320/contact_sheet_quick.jpg`
- Baseline-best contact sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_baseline_noprior_long200_eval_best_20260611_2320/contact_sheet_quick.jpg`
- Parsed eval metrics:
  - baseline best: `success_max=0`, `lift_max=0`, `ee_min=0.031762 m`,
    `finger_min=0.075477 m`, mean reward `2.1157`.
  - baseline ep100: `success_max=0`, `lift_max=0.002084 m`,
    `ee_min=0.083333 m`, `finger_min=0.100734 m`, mean reward `1.5761`.
  - baseline ep200: `success_max=0`, `lift_max=0`,
    `ee_min=0.117119 m`, `finger_min=0.105674 m`, mean reward `1.6371`.
  - prior ep100: `success_max=0`, `lift_max=0.002204 m`,
    `ee_min=0.011820 m`, `finger_min=0.050677 m`, mean reward `2.0332`.
  - prior ep200: `success_max=0`, `lift_max=0.003682 m`,
    `ee_min=0.025132 m`, `finger_min=0.055386 m`, mean reward `2.2222`.
- Visual interpretation: the prior reset puts the gripper near the cube, but
  the policy does not establish a stable pinch/lift. High reward appears to be
  mostly proximity reward.
- Instruction sent to A: run focused diagnostics before longer final training:
  scripted/oracle close-from-prior-reset, reset distribution report, and PPO
  eval action/reward audit. Keep main RL behavior apple-to-apple and gate
  diagnostics behind debug/eval-only flags.

Worker C controller-compensation sweep inspection:

- Sweep jobs `1027862`, `1027863`, and `1027864` completed `0:0`.
- Local artifact dirs:
  - `franka_cube_dp_replay_sourcejoint_comp_m3_r1_128_20260611_162300`
  - `franka_cube_dp_replay_sourcejoint_comp_m6_r1_128_20260611_162300`
  - `franka_cube_dp_replay_sourcejoint_comp_m10_r1_128_20260611_162300`
  under
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays`.
- Mode-summary findings:
  - multiplier `3`: final EE-cube about `0.1469-0.1502 m`, median xyz
    realization ratio about `0.078-0.082`, no close/hard-close.
  - multiplier `6`: final EE-cube about `0.1056-0.1079 m`, median xyz
    realization ratio about `0.079-0.083`, mean clip fraction `0.012`, no
    close/hard-close.
  - multiplier `10`: final EE-cube about `0.1011-0.1036 m`, median xyz
    realization ratio about `0.079-0.092`, mean clip fraction `0.068`, max
    clip fraction `0.500`, no close/hard-close.
- Video/plot interpretation: larger multipliers bring the EE closer, but still
  mostly hover/approach. `m10` starts clipping strongly and does not execute
  the demonstrated pick.
- Instruction sent to C: stop treating label scaling as the fix. Diagnose and
  patch the controller/action temporal semantics: env decimation/action
  application, DifferentialIK relative command semantics, frame/root/EE
  transforms, action integration over env steps, and whether the dataset action
  is already normalized by task action scale. Run minimal replay diagnostics
  with videos/plots only; no BC/RL scale-up yet.

## 2026-06-11 Monitor Check 23:36 UTC

Worker A next diagnostic state:

- A acknowledged the paired 200-epoch failure mode and planned a focused
  pregrasp usability diagnostic instead of longer training.
- Planned A change: add debug-only oracle/scripted close-lift phases to
  `dextrah_lab/rl_games/diagnose_franka_cube_grasp_prior_reset.py`, extend the
  diagnostic Slurm wrapper, and generate a PPO action/reward audit from the
  prior ep200 eval traces.
- Planned A job: l401, one GPU, no PPO training, `NUM_ENVS=1`,
  `NUM_RESETS=5`, same validated prior library and same cube randomization.
- Orchestrator expectation: if the oracle cannot grasp/lift from the reset,
  debug reset/control geometry; if the oracle works but PPO does not, final
  A100 RL remains blocked by policy/reward/exploration rather than reset
  geometry.

Worker B no-auto-reset hold diagnostic:

- B implemented and launched eval-only success termination suppression for the
  offset-hold reference controller.
- Job `1027866` completed `0:0` in `00:01:31`.
- Run:
  `franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220`.
- Local run dir:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220`.
- Local artifact dir:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts`.
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/report.md`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/contact_sheet_quick.jpg`
  - slow success/hold window:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220_artifacts/success_hold_window_slow.mp4`
- Metrics:
  - `success_termination_suppression_installed=True`,
    `suppress_success_termination=True`.
  - no actual done/reset events: `done_count=0`, `done_ever_count=0`.
  - `success_ever_count/rate=3/0.75`.
  - `suppressed_success_done_count/rate=3/0.75`.
  - `success_rate_mean/final/max=0.2255/0.5/0.75`.
  - last-window success mean `0.735`.
  - first success step mean `362.67`; last success step min/mean/max
    `514/518/520`.
  - max lift `0.220861 m`; final EE-cube `0.043913 m`;
    final finger-center-cube `0.086143 m`; final gripper width `0.047492 m`.
  - target unsafe max `0`; target clearance min `0.065114 m`.
- Visual interpretation: the no-reset reference/offset-hold controller keeps a
  stable high lift in the successful envs through the end of the rollout. The
  prior final-zero ambiguity is confirmed to be auto-reset semantics for the
  previous success-window run, not loss of the cube under reference hold.
- Orchestrator instruction sent to B: commit/push the worklog/artifact links,
  then move to bounded trainability diagnostics. Do not launch a large PPO
  scale-up. Next useful step is making the success-window/hold metrics
  available for RL/eval and testing a minimal learned-action-to-reference-hold
  handoff/curriculum.

Worker C current next step:

- C produced a combined controller compensation report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/controller_compensation_20260611_162300/controller_compensation_report.md`
- Report conclusion matches orchestrator inspection: scaling labels reduces
  raw distance but does not solve the controller/action semantics mismatch; high
  multipliers leave support and clip.
- Orchestrator instruction sent to C: commit/push the report/worklog state, then
  run a bounded action-repeat/temporal semantics diagnostic from exact
  source-joint reset. No BC/RL training until replay labels follow the teacher
  EE geometry under the actual controller.

## 2026-06-11 Monitor Check 23:48 UTC

New worker jobs completed:

- Worker A oracle close/lift reset diagnostic: job `1027869`, completed `0:0`.
- Worker B learned-prefix handoff diagnostic: job `1027870`, completed `0:0`.
- Worker C action-repeat replay sweep: jobs `1027871`, `1027872`,
  `1027873`, completed `0:0`.
- Worker C residual-target job `1027867` was cancelled intentionally after an
  invalid Slurm `--export` parse dropped comma-separated modes; do not use it
  as residual-target evidence.

Worker A artifact inspection:

- Run: `franka_cube_ggx_pregrasp_oracle_close_lift_20260611_2338`.
- Local dir:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_oracle_close_lift_20260611_2338`.
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_oracle_close_lift_20260611_2338/inspection/REPORT.md`
  - keyframe sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_oracle_close_lift_20260611_2338/inspection/reset000_oracle_keyframes.jpg`
- Key metrics:
  - `reset_success_rate=1.0`, `reset_quality_success_rate=1.0`,
    `pregrasp_reset_gate_pass=True`.
  - `oracle_success_rate=0.0`, `oracle_lift_gate_pass_rate=0.0`.
  - `oracle_max_cube_lift_height_mean_m=0.0`,
    `oracle_final_cube_lift_height_mean_m=0.0`.
  - `oracle_min_tip_center_dist_mean_m=0.0576`.
  - `oracle_final_gripper_width_mean_m=0.0550`.
  - `rl_relaunch_gate_verdict=FAIL`.
- Interpretation: the 3 cm pregrasp reset passes the current reset quality
  checks, but the scripted reset-to-close/lift sequence does not create a
  physical lift. Final RL remains blocked. A should debug reset-to-contact and
  control geometry before any more PPO.
- Instruction sent to A: run a bounded diagnostic matrix for offset/approach,
  close width, lift action magnitude/frame, and fingertip/TCP/contact geometry.
  Keep all changes debug-only; do not change the main apple-to-apple reset path.

Worker B artifact inspection:

- Run: `franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724`.
- Local dir:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724`.
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/report.md`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_learned_prefix_hold_noreset520_20260611_163724_artifacts/contact_sheet_quick.jpg`
- Key metrics: `success_ever=0`, `success_rate_max=0`,
  `cube_lift_height_max=0.001512 m`, final EE-cube `0.5066 m`, final
  finger-center-cube `0.4771 m`, target unsafe max `0`.
- Visual interpretation: the learned prefix moves away from the cube; the
  phase-triggered stable hold then holds in free space. This confirms the
  stable reference hold is useful only if the prefix reaches the handoff state.
- Instruction sent to B: run a small eval-only reference-blend alpha sweep
  (`0.25`, `0.5`, `0.75`) with the same no-reset stable hold. Identify the
  minimum alpha that reaches lift/success before any training scale-up.

Worker C artifact inspection:

- Runs:
  - `franka_cube_dp_replay_sourcejoint_repeat2_dataset_t_96_20260611_163750`
  - `franka_cube_dp_replay_sourcejoint_repeat4_dataset_t_96_20260611_163750`
  - `franka_cube_dp_replay_sourcejoint_repeat8_dataset_t_96_20260611_163750`
- Local base:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays`.
- Representative viewer URL:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_repeat4_dataset_t_96_20260611_163750/replay_report.md`
- Repeat sweep metrics:
  - repeat `2`: final EE-cube `0.1672 m`, final finger-cube `0.1659 m`,
    median xyz realization ratio `0.0936`, no close/hard-close.
  - repeat `4`: final EE-cube `0.1449 m`, final finger-cube `0.1488 m`,
    median xyz realization ratio `0.0934`, no close/hard-close.
  - repeat `8`: final EE-cube `0.1713 m`, final finger-cube `0.1667 m`,
    median xyz realization ratio `0.0942`, no close/hard-close.
- Interpretation: simple action repeat is not a viable bridge; it does not fix
  the action/controller mismatch and still leaves the replay short of the
  teacher geometry.
- Instruction sent to C: rerun the residual-target diagnostic correctly with
  preserved modes (`dataset_t,dataset_target_t_plus_1,dataset_target_t_plus_7`)
  because the first residual-target launch was invalid. No BC/RL training.

## 2026-06-11 Monitor Check 23:52 UTC

User-facing B provenance:

- The video `actionscale-rewinf-diag-video480-step-0.mp4` is from Worker B
  / Popper, but it is an older failed action-scale/reward-inference diagnostic:
  `franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318`.
- Viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_actionscale_rewinf_diag_video480_20260611_144318/videos/actionscale-rewinf-diag-video480-step-0.mp4`
- Do not treat that video as the latest B result. The latest B positive
  control remains the no-reset reference/offset hold run:
  `franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220`.

Worker B alpha-sweep inspection:

- Combined report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_noreset_alpha_sweep_20260611_164421_artifacts/report.md`
- Positive-control video:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_refmix_hold_offset_noreset520_20260611_163220/videos/refmix-hold-offset-noreset520-step-0.mp4`
- Metrics:

| alpha | role | success ever | success max/final | max lift m | final EE-cube m | final finger-cube m | decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.00 | learned-prefix | 0 | 0.000/0.000 | 0.001512 | 0.5066 | 0.4771 | failed handoff |
| 0.25 | reference blend | 0 | 0.000/0.000 | 0.000000 | 0.3344 | 0.3020 | failed handoff |
| 0.50 | reference blend | 0 | 0.000/0.000 | 0.000000 | 0.1119 | 0.1298 | close but no lift |
| 0.75 | reference blend | 0 | 0.000/0.000 | 0.000000 | 0.1006 | 0.1352 | close but no lift |
| 1.00 | reference control | 3 | 0.750/0.500 | 0.220861 | 0.0439 | 0.0861 | viable positive control |

- Visual interpretation: alpha `0.75` approaches the cube but never gets a
  lifted grasp; alpha `1.0` clearly lifts and holds in the successful envs.
- Analysis: this is not currently a train/eval mismatch in the reference path.
  It is a learned-policy handoff/control-learning failure. Worker B should stop
  treating partial blending as sufficient and build a teacher-forced curriculum
  or action-imitation loss that first matches the reference approach under the
  actual env controller.

Worker A matrix inspection:

- Report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_matrix_20260611_2344_inspection/REPORT.md`
- Matrix contact sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_matrix_20260611_2344_inspection/matrix_contact_sheet.jpg`
- Metrics:
  - direct exact-pose light-close `exact_w055` passes the exact-close gate.
  - all normal `env.step` oracle variants fail:
    `oracle_success_rate=0.0`, `trace_max_cube_lift_m=0.0`.
  - approach distances `0.00/0.01/0.03 m`, close widths
    `0.055/0.045/0.035 m`, larger lift action `0.15`, and reversed approach
    sign all fail.
  - min tip-center distance stays around `0.0564-0.0565 m`; the gripper width
    command is applied but physical contact/lift does not occur.
- Analysis: saved grasp transform and cube XY randomization are unlikely to be
  the primary issue. The blocker is the normal action-space control path from
  pregrasp to exact/contact, or a mismatch between the RL action TCP proxy and
  the direct exact-pose diagnostic.

Worker C residual-target inspection:

- Report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300/replay_report.md`
- Quick sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300/videos/franka-cube-dp-replay-targetresidual-step-0_sheet.jpg`
- Metrics:

| mode | final EE-cube m | min EE-cube m | final finger-cube m | median xyz realization | mean cosine | mean target before/after | clip mean/max | first close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dataset_t | 0.1887 | 0.1887 | 0.1815 | 0.0932 | 0.8907 | n/a | 0.000/0.000 | none |
| dataset_target_t_plus_1 | 0.1752 | 0.0764 | 0.2199 | 0.0802 | 0.9603 | 0.0503/0.0474 | 0.090/0.333 | none |
| dataset_target_t_plus_7 | 0.1756 | 0.0762 | 0.2203 | 0.0803 | 0.9676 | 0.0506/0.0476 | 0.090/0.333 | none |

- Visual interpretation: replay approaches but does not close or lift in the
  inspected 96-step videos. The residual target variants improve direction but
  not enough magnitude; realized motion remains about `8%` of the requested
  step.
- Analysis: DP warm start remains blocked on controller/action realization. C
  should not launch BC/RL until the actual env controller can replay teacher
  waypoints with adequate magnitude and close-phase timing.

Next orchestrator actions:

- Send Worker A a targeted request for action-tracking probes and a
  controller-assisted move-to-exact diagnostic.
- Send Worker B a targeted request for teacher-forced/action-imitation
  curriculum artifacts before any large PPO.
- Send Worker C a targeted request to resolve controller realization and
  close-phase replay before more DP training.

## 2026-06-12 Monitor Check 00:05 UTC

Worker A action-tracking diagnostics:

- Jobs:
  - fixed `env.step` oracle: `1027891`, completed `0:0`, run
    `franka_cube_ggx_pregrasp_actiontrack_fixed_20260611_235922`.
  - proportional assisted oracle: `1027892`, completed `0:0`, run
    `franka_cube_ggx_pregrasp_actiontrack_assisted_20260611_235922`.
- Comparison sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_actiontrack_comparison_sheet.jpg`
- Metrics:

| mode | success rate | lift gate | max lift mean m | min tip-center m | min exact EE dist m | final exact EE dist m | final width m | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_direction | 0.000 | 0.000 | 0.000000 | 0.0573 | 0.0276 | 0.0698 | 0.0350 | fail |
| proportional_exact | 0.333 | 0.333 | 0.010937 | 0.0386 | 0.0081 | 0.0499 | 0.0413 | partial |

- Interpretation: receding-horizon assisted action tracking partially recovers
  contact/lift in 1 of 3 resets, while fixed action-space replay remains dead.
  This supports the hypothesis that reset geometry is usable but the
  policy/script needs a closed-loop controller or curriculum from pregrasp to
  contact. It is not enough for final PPO relaunch: success is only `1/3`,
  mean lift is about `1.1 cm`, and visual lift is marginal.
- Next for A: run a small assisted-parameter diagnostic, not PPO. Try
  proportional gain/max action/orientation tracking variants or exact-pose
  settle duration, and report whether success becomes robust across all resets.

Worker C controller-target-hold replay:

- Job `1027893`, completed `0:0`, run
  `franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939`.
- Report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/replay_report.md`
- Contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0_sheet.jpg`
- Metrics:
  - final EE-cube `0.0808 m`; min EE-cube `0.0299 m`.
  - final finger-cube `0.1247 m`; min finger-cube `0.0701 m`.
  - final gripper width `0.000565 m`; first close step `36`, hard-close
    step `49`, target lift step `226`.
  - median XYZ realization ratio `0.00023`; mean direction cosine `-0.0787`;
    clip fraction `0`.
- Interpretation: this reaches the close phase and physically closes the
  gripper, but the absolute-pose-to-relative target-hold replay does not follow
  teacher geometry through close/lift. It ends farther from the cube and the
  direction cosine is negative. DP/BC remains blocked; raw cuRobo waypoint
  deltas are not yet valid policy labels under this controller.
- Next for C: diagnose target-frame/source-row semantics and controller
  capability before training. Compare absolute source EE target, live FK source
  target, and task TCP frame; consider controller-rollout relabeling only if a
  replay can stay near teacher geometry through close/lift.

Worker B teacher-force env smoke:

- Job `1027895`, completed `0:0`, run
  `franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249`.
- Report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249_artifacts/report.md`
- Video sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249/videos/franka-cube-validate-step-0_sheet.jpg`
- Video:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_env_smoke_20260611_170249/videos/franka-cube-validate-step-0.mp4`
- Metrics:
  - validation passed, `steps_completed=240`, `done_count=0`,
    `early_done_count=0`, `target_unsafe_rate_max=0`.
  - `tracking_teacher_force_active_mean=1.0`,
    `tracking_teacher_force_alpha_mean=1.0`.
  - applied/reference action error `0.0261`, raw-policy/reference error
    `1.416`, applied/raw error `1.425`.
  - max mean lift `0.0227 m`, final success `0`, final gripper width
    `0.0489 m`.
- Interpretation: teacher-forced action application is wired and target-safe,
  and the video no longer has the older drift-away behavior. This is not yet a
  learned-policy result because alpha is `1.0`; raw policy action remains far
  from reference.
- Next for B: tiny PPO/anneal diagnostic only, with eval videos at alpha `1.0`
  and a lower alpha. Acceptance is reduced raw-policy/reference error and
  contact/lift under lower teacher alpha; no final-scale PPO yet.

Queue state:

- `l401` queue empty after the above jobs completed.
- `a1001` queue was empty during the previous check.

## 2026-06-11T17:19:01-07:00 - B teacher-force eval verdict and worker steering

Goal:
- Answer the user question about B's `actionscale-rewinf-diag-video480-step-0.mp4`
  artifact and keep the workers aligned on artifact quality.

Worker B status:

- The file `actionscale-rewinf-diag-video480-step-0.mp4` is from Worker B's
  earlier action-scale/reward-inference diagnostic. It is an obsolete failed
  artifact and should not be treated as B's current best evidence.
- Current B evidence is the teacher-force path:
  - Env smoke `1027895` validated task registration, target safety, and
    teacher-force action application.
  - Tiny teacher-force PPO `1027900` completed, but the checkpoint reward
    suffix is not a success signal.
  - Eval alpha `1.0`, run
    `franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100`:
    train/eval consistency passed, target unsafe max `0`, success final/max
    `0.25`, max/final lift about `0.060 m`, raw-policy/reference L2 mean
    `1.019`, applied/reference L2 mean `0.348`. Video shows approach and a
    transient lift, but it does not prove a robust learned handoff.
  - Eval alpha `0.75`, run
    `franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100`:
    train/eval consistency passed, target unsafe max `0`, success `0`, max lift
    about `0.00004 m`, raw-policy/reference L2 mean `1.046`. Video reaches or
    contacts near the cube but does not lift.

Worker B artifacts:

- Alpha `1.0` report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100_artifacts/report.md`
- Alpha `1.0` video:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a100_520_20260611_171100/videos/tf-eval-a100-520-step-0.mp4`
- Alpha `0.75` report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100_artifacts/report.md`
- Alpha `0.75` video:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-traj-tracking/cluster_results/l401/franka_cube_traj_tracking_teacherforce_eval_a075_520_20260611_171100/videos/tf-eval-a075-520-step-0.mp4`

Analysis:
- B is past the old drift-away failure under full teacher forcing, and
  train/eval consistency is no longer the first suspect for the latest videos.
- B is still not ready for final-scale PPO. The learned raw policy remains too
  far from the reference actions, and the lower-alpha handoff fails the lift
  gate.
- The reported teacher-force alpha schedule needs scrutiny: the nominal
  alpha-`1.0` eval reports alpha mean/final `0.7067/0.5`, and alpha-`0.75`
  reports final alpha `0.0`. If this is phase gating it must be made explicit;
  if unintended, it needs a patch before further scale-up.

Worker C update:
- Target-frame audit `1027903` passed as a diagnostic but failed the DP
  readiness gate. Converted lowdim EE targets and env FK agree, which rejects a
  converter/FK mismatch, but source-row finger-center distances remain about
  `6.8 cm` from the cube. Raw cuRobo/GraspGenX labels should not be used for
  DP BC/RL training as-is.
- Next for C is a contact-aware controller-rollout relabeler/generator or a
  corrected GraspGenX/cuRobo EE/TCP/grasp frame, with a stable close/lift
  Isaac diagnostic before DP training resumes.

Worker A update:
- L401 jobs `1027904` and `1027905` are running as follow-up reset-prior
  diagnostics. These are expected to test orientation/exact-hold or related
  robustness gates. No PPO/A100 reset-prior launch should happen until the
  diagnostic videos/metrics show robust contact/lift across all or near-all
  resets.

Worker steering sent:
- B: label the old `actionscale-rewinf` video as obsolete, update worklog with
  teacher-force eval verdicts and artifact URLs, debug raw-policy/reference
  error and teacher-alpha schedule before any scale-up.
- A: monitor `1027904`/`1027905`, fetch artifacts, produce report/contact
  sheets/trace plots, and continue bounded diagnostics only if inconclusive.
- C: do not train DP on raw labels; document the blocker and move only toward a
  contact-aware relabel/generator diagnostic with artifact cadence.

## 2026-06-11T17:31:30-07:00 - A orientation/hold diagnostic result

Goal:
- Inspect Worker A's follow-up reset-prior jobs `1027904` and `1027905` instead
  of relying on Slurm completion.

Jobs:
- `1027904`: `franka_cube_ggx_pregrasp_orienthold_20260611_171721_baseline_trace`,
  completed `0:0`.
- `1027905`: `franka_cube_ggx_pregrasp_orienthold_20260611_171721_hold60_approach120`,
  completed `0:0`.

Artifacts:
- Report:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_orienthold_20260611_171721_inspection/REPORT.md`
- Keyframe sheet:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_orienthold_20260611_171721_inspection/orienthold_keyframe_sheet.jpg`
- Trace plot:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_orienthold_20260611_171721_inspection/orienthold_trace_plot.png`
- Keyframe slideshow:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/cluster_results/l401/franka_cube_ggx_pregrasp_orienthold_20260611_171721_inspection/orienthold_keyframes.mp4`

Metrics:

| Variant | Success | Lift Gate | Mean Max Lift | Mean Min Tip | Mean Min Exact EE | Final Exact EE | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline_trace` | `2/3` | `2/3` | `0.023154` | `0.0350` | `0.0045` | `0.0455` | `FAIL` |
| `hold60_approach120` | `2/3` | `2/3` | `0.022684` | `0.0348` | `0.0044` | `0.0450` | `FAIL` |

Reset-specific evidence:
- Both variants lift resets `0` and `1`, then fail reset `2` with max lift `0`.
- Baseline reset `2`: min tip-center `0.0417 m`, min exact-EE error
  `0.0131 m`, final exact-EE error `0.0574 m`, final tip-center `0.0851 m`.
- Hold/long-approach reset `2`: min tip-center `0.0417 m`, min exact-EE error
  `0.0131 m`, final exact-EE error `0.0572 m`, final tip-center `0.0844 m`.
- Rotation traces show resets `0`/`1` can reach near-zero post-to-exact rotation
  error, while reset `2` minimum stays about `0.0372 rad` in both variants.

Analysis:
- The added 60-step exact-hold and longer approach do not improve robustness.
  The reset-2 failure is essentially unchanged.
- This rules out simple approach duration/open-settle time as the blocker.
  Remaining suspects are reset-2-specific pose/grasp robustness, action-space
  contact geometry, contact timing after close, or the single grasp sample
  being brittle under cube randomization.
- No reset-prior PPO/A100 launch should happen from this state.

Worker steering:
- A was told to update its owned worklog with the artifact URLs and to keep the
  next step bounded, targeting reset-2-specific failure mode or alternate grasp
  robustness rather than approach duration.
