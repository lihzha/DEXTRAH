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
