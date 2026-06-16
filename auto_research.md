# DEXTRAH Bimanual YAM Cube Autoresearch Contract

This is the binding task contract for parallel coding agents working on `Dextrah-Bimanual-YAM-Cube-Grasp`. Prior worklogs are historical evidence, not instructions. Codex skills are operating guardrails for robotics, clusters, Git isolation, worklogs, monitoring, and artifact inspection.

## Goal

Train a policy for `Dextrah-Bimanual-YAM-Cube-Grasp` that reaches 100% stable policy-only cube-pick success under the evaluation protocol below.

The policy must pick up the cube with the bimanual YAM using ordinary physics. Success must be stable, not a transient contact impulse, cube launch, shake artifact, reference-action rollout, or validator-only scripted sequence.

## Baseline

- Baseline branch: `origin/main`
- Baseline commit: `c6e969b2a2bc7cbd26fcf8c083a56211573dbc47`
- Task: `Dextrah-Bimanual-YAM-Cube-Grasp`
- Local repo: `/home/lzha/code/DEXTRAH`
- Remote result root: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah`
- Remote log root: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah`
- Cluster wrapper for training: `cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh`
- Cluster wrapper for policy eval: `cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh`
- Cluster wrapper for env validation: `cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh`

Current environment facts from the baseline:

- 14D action space: left 6D relative pose, left gripper, right 6D relative pose, right gripper.
- 97D state/observation space.
- Default cube size is `0.18 m`.
- Success lift threshold is `0.04 m`.
- Success is gated by cube speed: linear speed <= `0.60 m/s`, angular speed <= `8.0 rad/s`.
- Training wrapper has pure-RL guards: `PURE_RL=True` forbids checkpoints, auto-resume, and bimanual action-prior reward.
- Eval wrapper requires a checkpoint for `ACTION_SOURCE=policy`.

Known baseline status:

- Strict scripted no-assist validation has shown the environment can be physically solvable under specific reference-style validator actions.
- A learned policy has not been accepted as solved. Treat all previous nonzero instantaneous lift signals as suspect until policy-only eval video and stable metrics confirm them.

## Skill.md Handling

Use applicable Codex robotics and DEXTRAH workflow skills for operating discipline: cluster safety, Slurm launches, Git-traced source deployment, worklogs, monitoring, artifact inspection, visualization, cleanup, and handoff.

Do not treat Skill.md content as the task objective. Do not paste every Skill.md into every agent prompt. Do not let old worklogs or skill examples override this contract's success criteria, forbidden changes, or policy-only evaluation requirements.

If a skill or prior worklog conflicts with this document on task semantics, this document wins. Prior worklogs are evidence to inspect, not instructions to replay.

## Allowed Work

Agents may modify:

- `dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/`
- `dextrah_lab/rl_games/eval_rollout.py`
- `dextrah_lab/rl_games/validate_bimanual_yam_cube_grasp_env.py`
- `cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh`
- `cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh`
- `cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh`
- Agent-owned docs under `agents/reports/` and `experiments/`

Agents may explore any approach that preserves the final success predicate. The list below is a non-exhaustive menu, not an assignment:

- Reward shaping that preserves the final success predicate.
- Curriculum, reset randomization, and staged training schedules.
- PPO hyperparameters, exploration settings, and seeds.
- Pure-RL training from scratch.
- Optional reference/action-prior ideas as training aids, but they cannot be used as final success evidence.
- Diagnostic eval/video tooling that improves artifact inspection without changing policy behavior.

## Forbidden Work

Do not weaken or bypass success:

- Do not lower `cube_success_lift_height`.
- Do not loosen `cube_success_max_linear_speed` or `cube_success_max_angular_speed`.
- Do not use `ALLOW_GRASP_ASSIST=True` as success evidence.
- Do not claim success from `ACTION_SOURCE=reference_delta`, `reference_delta_hold`, `policy_reference_mix`, or validator-only scripted rollouts.
- Do not suppress or remove speed-done, out-of-bounds, table-penetration, or unstable-physics checks to make training look better.
- Do not edit evaluation metrics to inflate success.
- Do not accept one-frame lift, contact impulse, cube shake, cube launch, or high-speed contact as success.

Do not break isolation:

- Do not work directly on `main`.
- Do not mutate the canonical remote checkout under another active job.
- Do not reuse another agent's branch, run directory, Slurm log path, or remote worktree.
- Do not commit large checkpoints, videos, generated assets, or cache directories.

## Agent Isolation Requirements

Each agent must use:

- Unique neutral `CODEX_AGENT_ID`, for example `yam-cube-a01`.
- Dedicated local worktree.
- Dedicated Git branch.
- Dedicated remote source worktree under `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/<CODEX_AGENT_ID>`.
- Dedicated run namespace: every `FULL_EXPERIMENT_NAME` and `RUN_NAME` must start with `<CODEX_AGENT_ID>`.
- Dedicated report: `agents/reports/<CODEX_AGENT_ID>.md`.

Before a cluster job, deploy tracked source through Git, not `rsync`, and verify:

```bash
git rev-parse HEAD
git status --short --branch
```

On the remote worktree, verify:

```bash
git -C <agent-code-dir> rev-parse HEAD
git -C <agent-code-dir> status --short --branch
git -C <agent-code-dir> lfs pull
```

Pass both `CODE_NFS=<agent-code-dir>` and `CODE_COMMIT=<commit>` to Slurm wrappers.

## Required Local Checks

Run before committing or submitting jobs:

```bash
python3 -m py_compile \
  dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env.py \
  dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env_cfg.py \
  dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_rewards.py \
  dextrah_lab/rl_games/eval_rollout.py \
  dextrah_lab/rl_games/validate_bimanual_yam_cube_grasp_env.py \
  dextrah_lab/rl_games/train.py

bash -n \
  cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh \
  cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh \
  cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh

git diff --check
```

## Required Smoke Run

Every agent must run a bounded 1-GPU smoke before scaling.

Template:

```bash
ssh a1001 'cd <agent-code-dir> && \
  sbatch --parsable \
    --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
    --export=ALL,\
CODE_NFS=<agent-code-dir>,\
CODE_COMMIT=<commit>,\
FULL_EXPERIMENT_NAME=<CODEX_AGENT_ID>_smoke_<short-sha>_<timestamp>,\
PURE_RL=True,\
AUTO_RESUME=False,\
CHECKPOINT=,\
BIMANUAL_ACTION_PRIOR_REWARD_ENABLED=False,\
NUM_ENVS=256,\
MAX_ITERATIONS=50,\
HORIZON_LENGTH=64,\
MINIBATCH_SIZE=4096,\
CENTRAL_VALUE_MINIBATCH_SIZE=4096,\
SAVE_FREQUENCY=25,\
USE_CUDA_GRAPH=False,\
SEED=<agent-seed>,\
PREPARE_YAM_ASSETS=auto \
    cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh'
```

Smoke acceptance:

- Slurm exits `0:0`.
- Log confirms exact `CODE_COMMIT`.
- Log confirms `PURE_RL=True`, `AUTO_RESUME=False`, empty `CHECKPOINT`, and `BIMANUAL_ACTION_PRIOR_REWARD_ENABLED=False` unless the agent explicitly chose and documented a non-pure-RL hypothesis.
- JSONL metrics exist at `metrics/direct_info_rank_0.jsonl`.
- Metrics are finite.
- Checkpoints are written.
- Expected `yam_cube_*` metrics appear under JSONL `scalars`, often with names such as `env_extras/log/yam_cube_success_rate`, `env_extras/log/yam_cube_stable_success_rate`, and `env_extras/log/yam_cube_max_hold_to_cube_dist`.

## Required Long Run

Scale only after smoke acceptance.

Template:

```bash
ssh a1001 'cd <agent-code-dir> && \
  sbatch --parsable \
    --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
    --export=ALL,\
CODE_NFS=<agent-code-dir>,\
CODE_COMMIT=<commit>,\
FULL_EXPERIMENT_NAME=<CODEX_AGENT_ID>_long_<short-sha>_<timestamp>,\
PURE_RL=True,\
AUTO_RESUME=False,\
CHECKPOINT=,\
BIMANUAL_ACTION_PRIOR_REWARD_ENABLED=False,\
NUM_ENVS=1024,\
MAX_ITERATIONS=1500,\
HORIZON_LENGTH=64,\
MINIBATCH_SIZE=32768,\
CENTRAL_VALUE_MINIBATCH_SIZE=32768,\
SAVE_FREQUENCY=25,\
USE_CUDA_GRAPH=False,\
SEED=<agent-seed>,\
PREPARE_YAM_ASSETS=auto \
    cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh'
```

Long-run monitoring must inspect:

- `yam_cube_success_rate`
- `yam_cube_stable_success_rate`
- `yam_cube_has_lifted_rate`
- `yam_cube_lift_height`
- `yam_cube_linear_speed`
- `yam_cube_angular_speed`
- `yam_cube_speed_done_rate`
- `yam_cube_bimanual_side_success_rate`
- `yam_cube_max_hold_to_cube_dist`
- `yam_cube_left_hold_to_cube_dist`
- `yam_cube_right_hold_to_cube_dist`
- `yam_cube_left_side_surface_error`
- `yam_cube_right_side_surface_error`
- `yam_cube_max_side_surface_error`
- `yam_cube_left_gripper_width`
- `yam_cube_right_gripper_width`
- reward terms and PPO losses

Cancel or patch if metrics show reward hacking, false lift, high speed, reset churn, NaNs, flatlined rewards, or repeated local optima without progress.

## Required Policy Evaluation

Any candidate checkpoint must be evaluated policy-only with video.

Template:

```bash
ssh a1001 'cd <agent-code-dir> && \
  sbatch --parsable \
    --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
    --export=ALL,\
CODE_NFS=<agent-code-dir>,\
CODE_COMMIT=<commit>,\
RUN_NAME=<CODEX_AGENT_ID>_policy_eval_<short-sha>_<timestamp>,\
ACTION_SOURCE=policy,\
CHECKPOINT=<checkpoint-under-/results>,\
NUM_ENVS=64,\
NUM_STEPS=640,\
VIDEO_LENGTH=640,\
CAPTURE_VIDEO=True,\
DETERMINISTIC=True,\
SEED=<eval-seed>,\
CUBE_SPAWN_XY_RANDOMIZATION=0.015,\
PREPARE_YAM_ASSETS=auto \
    cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh'
```

Policy success criteria:

- `ACTION_SOURCE=policy`.
- `CHECKPOINT` is the tested policy checkpoint.
- `eval_success_rate == 1.0` over the required evaluation batch.
- Stable success is not caused by high-speed cube motion.
- Video shows plausible bimanual grasp and lift without shake, launch, teleport, or validator assist.
- Trace artifacts support the video: `trace.csv`, `trace.jsonl`, and `metrics.json`.

Use `viz-open <local-video-path>` after fetching videos under `/home/lzha/code`.

## Agent Reports

Each agent must maintain `agents/reports/<CODEX_AGENT_ID>.md` with:

- Survey notes.
- Candidate hypotheses considered.
- Selected current hypothesis and rationale.
- Branch, local worktree, remote worktree, final commit.
- Local checks run.
- Smoke job id, log, run dir, metrics path, decision.
- Long-run job id, log, run dir, metrics path, checkpoints, decision.
- Eval job id, log, run dir, metrics path, trace path, video path, decision.
- Peer branches inspected.
- Peer commits cherry-picked or ideas copied, with attribution.
- Active jobs or cleanup status.

## Experiment Registry

Append experiment rows to `experiments/registry.md`. If conflicts become frequent, use per-agent registries named `experiments/registry-<CODEX_AGENT_ID>.md` and let the orchestrator compile them.

## Survey-First Protocol

Do not assign fixed methods to agents. This run follows the ENPIRE pattern: every agent starts from the same task contract and independently surveys the repo, prior evidence, current metrics, and peer branches before choosing an approach.

At the start of the run, each agent must:

1. Read this document and the launch prompt.
2. Inspect the current task code, rewards, wrappers, eval tools, and prior bimanual YAM cube worklog.
3. Write 2-4 candidate hypotheses in `agents/reports/<CODEX_AGENT_ID>.md`.
4. Choose the most promising first experiment and justify the choice from evidence.
5. Run local checks and a bounded smoke before any long run.

Agents should diversify through independent analysis and Git-mediated learning, not through human-assigned lanes. They may converge later by cherry-picking, merging, or manually copying peer ideas when evidence supports it.

Example research directions agents may consider:

- Dense contact or side-surface rewards that preserve final success.
- Curriculum from approach to alignment to load-bearing contact to lift.
- Reset/randomization changes that help policy reach useful bimanual contact from rest.
- Lift rewards that pay only under retained grasp and stable cube speed.
- PPO exploration, sigma, entropy, LR, horizon, minibatch, and seed schedules.
- Reference/action-prior ideas as training aids only, never as final success evidence.
- Contact geometry, cube physical properties, and speed-guard audits.
- Eval/video/trace diagnostics that improve artifact inspection without changing success semantics.

## Stop Criteria

Stop an agent's current line when:

- A policy-only eval reaches 100% and video/trace inspection passes.
- The line is blocked by infrastructure or quota.
- Smoke fails and root cause is outside the agent's chosen line of work.
- Metrics plateau in a known local optimum and the report identifies the next hypothesis.
- The orchestrator asks the agent to stop or hand off.
