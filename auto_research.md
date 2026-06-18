# DEXTRAH Table Clutter Removal Autoresearch Contract

This is the binding task contract for parallel coding agents working on table
clutter removal in DEXTRAH. Prior worklogs, old YAM-cube launch files, and
Skill.md files are operating context only. They are not the task objective.

## Goal

Train and validate a policy that uses the single-arm YAM robot to remove table
clutter by picking objects from a tabletop one by one and placing them into a
bin.

The final deployment target is another simulation setup with the same camera
and same robot setup, but different objects and different object locations.
Therefore final evidence must include held-out objects and held-out object
locations, not only train-layout performance.

## Baseline

- Baseline branch: `origin/main`
- Baseline commit: `d0cddef0c01fbf2377272488e058fccf2176ec4c`
- Current clutter/bin task: `Dextrah-Single-YAM-Tabletop-Clutter-Grasp`
- Current multi-object task: `Dextrah-Single-YAM-Multi-Object-Grasp`
- Local repo: `/home/lzha/code/DEXTRAH`
- Remote result root: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah`
- Remote log root: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah`
- Training wrapper: `cluster/sbatch_train_teacher_8gpu.sh`
- Clutter/bin render wrapper: `cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`
- Generic policy eval tool: `dextrah_lab/rl_games/eval_rollout.py`

Current baseline facts:

- `Dextrah-Single-YAM-Tabletop-Clutter-Grasp` is registered in
  `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/gym_setup.py`.
- The current tabletop-clutter config enables `tabletop_clutter_enabled` and
  `tabletop_goal_bin_enabled`.
- The current reward and termination code tracks one active target object and
  treats the additional tabletop objects as clutter.
- Sequential clear-all behavior is not proven by the current task as written.
  Agents must decide from evidence whether to solve clutter removal by repeated
  single-object episodes, an outer receding-horizon evaluation loop, or an
  environment extension that retargets/removes multiple objects in one episode.

## Skill.md Handling

Use applicable Codex robotics and DEXTRAH workflow skills for cluster safety,
Git isolation, worklogs, monitoring, artifact inspection, visualization,
cleanup, and handoff.

Do not paste every Skill.md into agent prompts. Do not treat Skill.md examples
as task semantics. If a skill conflicts with this document on success criteria,
forbidden changes, or final evaluation, this document wins.

## Research Method

This run follows a decentralized ENPIRE-style workflow: multiple agents start
from the same objective and independently survey the codebase, current task,
wrappers, prior evidence, and peer branches before choosing an approach.

The user has already confirmed this overall workflow. Agents must not stop
after presenting another plan or asking for confirmation to proceed with the
survey, report update, local checks, bounded smoke, evidence inspection, bug
fixes, relaunches, or follow-up evaluations described in this contract.

Agents are not assigned fixed methods. Each agent must:

1. Audit the environment, reward, reset, observation, action, success, and eval
   code before assuming the task works correctly.
2. Write 2-4 candidate hypotheses in its report.
3. Choose the smallest first test that can falsify or support the chosen
   hypothesis.
4. Use bounded smokes before long training.
5. Inspect metrics, logs, videos, and artifacts directly.
6. Fetch peer branches regularly and adopt peer ideas only when evidence
   supports them.

## Stop Rule

Agents should continue working until the table-clutter-removal goal is genuinely
achieved with the required policy-only held-out evidence. Do not stop merely
because a survey is complete, a plan has been written, a smoke has finished, or
a first attempt failed.

The only acceptable non-goal stopping points are:

- The user or orchestrator explicitly says to stop or pause.
- An external blocker prevents meaningful progress, such as infrastructure
  failure, missing required assets, authentication failure, quota exhaustion, or
  unavailable cluster resources. In that case, document the blocker, preserve
  logs/artifacts, stop or transfer active jobs, and make the next required
  external action explicit.

Otherwise, continue the loop: audit, hypothesize, test cheaply, patch or tune,
commit, deploy, smoke, inspect evidence, relaunch, compare peer branches, and
repeat until the final goal is achieved.

## Core Question Agents Must Answer First

The current repo contains a clutter + bin setup, but it is not sufficient to
blindly launch training and assume it solves table clutter removal.

Agents must explicitly determine:

- Does `Dextrah-Single-YAM-Tabletop-Clutter-Grasp` train a policy that places a
  target object into the bin, or only lifts/stabilizes it?
- Are clutter objects part of observations, reward, and success, or only scene
  distractors?
- Is there an existing policy-only evaluator that measures sequential
  clear-all, or must one be added?
- Should final deployment be represented by state-only observations, camera
  observations, or a staged state-to-camera handoff?
- What object split and location split will test transfer to the target
  deployment setup?

## Allowed Work

Agents may modify:

- `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/`
- `dextrah_lab/tasks/dextrah_multi_object_grasp/`
- `dextrah_lab/rl_games/eval_rollout.py`
- `dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py`
- `dextrah_lab/rl_games/train.py`
- `cluster/sbatch_train_teacher_8gpu.sh`
- `cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`
- New narrowly scoped validators/evaluators under `dextrah_lab/rl_games/`
- New narrowly scoped cluster wrappers under `cluster/`
- Agent-owned reports under `agents/reports/`
- Experiment records under `experiments/`

Agents may explore any approach that preserves the final success predicate,
including:

- Environment bug fixes when justified by source evidence, logs, metrics,
  videos, or minimal repros.
- Reward shaping that preserves final policy-only clear-all evaluation.
- Sequential retargeting or remove-on-success task extensions.
- A repeated single-pick evaluator that resets or retargets objects one by one.
- Curriculum over object count, object set, location randomization, and bin
  placement.
- PPO hyperparameters, seeds, normalization, and exploration settings.
- Diagnostic render/eval tooling that improves artifact inspection without
  changing policy behavior.
- State-policy first passes, as long as final deployment constraints and
  camera-policy needs are recorded honestly.

## Forbidden Work

Do not weaken or bypass success:

- Do not claim success from scripted/reference actions.
- Do not use validator-only actions, oracle object selection, or hard-coded
  object teleportation as policy success evidence.
- Do not edit eval metrics to inflate success.
- Do not call a single target-object bin placement a solved clear-all policy
  unless a repeated/sequential evaluator confirms the table is cleared.
- Do not train and evaluate on the exact same object identities and object
  layouts when claiming deployment readiness.
- Do not suppress unstable physics checks, out-of-bounds checks, table
  penetration checks, or speed gates to improve metrics.
- Do not accept object launch, object shake, transient bin contact, or one-frame
  bin entry as success.

Do not break isolation:

- Do not work directly on `main`.
- Do not mutate canonical remote checkouts under active jobs.
- Do not reuse another agent's branch, run directory, Slurm log path, or remote
  worktree.
- Do not commit large checkpoints, videos, generated assets, or cache
  directories.

## Agent Isolation Requirements

Each agent must use:

- Unique neutral `CODEX_AGENT_ID`, for example `clutter-removal-a01`.
- Dedicated local worktree.
- Dedicated Git branch.
- Dedicated remote source worktree under
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/<CODEX_AGENT_ID>`.
- Dedicated run namespace: every `FULL_EXPERIMENT_NAME` and `RUN_NAME` must
  start with `<CODEX_AGENT_ID>`.
- Dedicated report: `agents/reports/<CODEX_AGENT_ID>.md`.

Before a cluster job, deploy tracked source through Git, not `rsync`, and
verify:

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

Pass both `CODE_NFS=<agent-code-dir>` and `CODE_COMMIT=<commit>` to Slurm
wrappers.

## Required Initial Files To Read

Agents should start with:

- `auto_research.md`
- `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/gym_setup.py`
- `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/single_yam_multi_object_grasp_env.py`
- `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/single_yam_multi_object_grasp_env_cfg.py`
- `dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/agents/rl_games_ppo_single_yam_multi_object_grasp_cfg.yaml`
- `dextrah_lab/tasks/dextrah_multi_object_grasp/multi_object_grasp_cfg.py`
- `dextrah_lab/tasks/dextrah_multi_object_grasp/multi_object_grasp_task.py`
- `dextrah_lab/rl_games/eval_rollout.py`
- `dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py`
- `dextrah_lab/rl_games/train.py`
- `cluster/sbatch_train_teacher_8gpu.sh`
- `cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`

## Required Local Checks

Run before committing or submitting jobs:

```bash
python3 -m py_compile \
  dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/gym_setup.py \
  dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/single_yam_multi_object_grasp_env.py \
  dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/single_yam_multi_object_grasp_env_cfg.py \
  dextrah_lab/tasks/dextrah_multi_object_grasp/multi_object_grasp_cfg.py \
  dextrah_lab/tasks/dextrah_multi_object_grasp/multi_object_grasp_task.py \
  dextrah_lab/rl_games/eval_rollout.py \
  dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py \
  dextrah_lab/rl_games/train.py

bash -n \
  cluster/sbatch_train_teacher_8gpu.sh \
  cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh

git diff --check
```

## Required Smoke Run

Every agent must run a bounded smoke before scaling. The exact smoke may change
if the agent first adds a validator or fixes a task bug, but it must stay small
and record metrics/logs/artifacts.

Current training smoke template:

```bash
ssh a1001 'cd <agent-code-dir> && \
  sbatch --parsable \
    --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
    --export=ALL,\
CODE_NFS=<agent-code-dir>,\
CODE_COMMIT=<commit>,\
TASK=Dextrah-Single-YAM-Tabletop-Clutter-Grasp,\
FULL_EXPERIMENT_NAME=<CODEX_AGENT_ID>_smoke_<short-sha>_<timestamp>,\
NUM_ENVS=128,\
MAX_ITERATIONS=25,\
HORIZON_LENGTH=32,\
MINIBATCH_SIZE=2048,\
CENTRAL_VALUE_MINIBATCH_SIZE=2048,\
SAVE_FREQUENCY=25,\
USE_CUDA_GRAPH=False,\
OBJECT_ASSET_ASSIGNMENT=random,\
TABLETOP_CLUTTER_OBJECT_COUNT=3,\
TABLETOP_CLUTTER_ASSET_ASSIGNMENT=random,\
SEED=<agent-seed> \
    cluster/sbatch_train_teacher_8gpu.sh'
```

Smoke acceptance:

- Slurm exits cleanly.
- Log confirms exact `CODE_COMMIT`.
- Metrics JSONL exists and is finite.
- Checkpoints are written when training is expected.
- Key environment extras appear, including success, lift/placement, object,
  clutter-placement, and reward terms.
- If a video or reset renderer is part of the smoke, inspect it before scaling.

## Required Long Run

Scale only after smoke acceptance and after the agent has justified the task
semantics. Do not run a long job solely because the wrapper exists.

Current long-run starting point:

```bash
ssh a1001 'cd <agent-code-dir> && \
  sbatch --parsable \
    --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode \
    --export=ALL,\
CODE_NFS=<agent-code-dir>,\
CODE_COMMIT=<commit>,\
TASK=Dextrah-Single-YAM-Tabletop-Clutter-Grasp,\
FULL_EXPERIMENT_NAME=<CODEX_AGENT_ID>_long_<short-sha>_<timestamp>,\
NUM_ENVS=1024,\
MAX_ITERATIONS=1500,\
HORIZON_LENGTH=64,\
MINIBATCH_SIZE=16384,\
CENTRAL_VALUE_MINIBATCH_SIZE=16384,\
SAVE_FREQUENCY=25,\
USE_CUDA_GRAPH=False,\
OBJECT_ASSET_ASSIGNMENT=random,\
TABLETOP_CLUTTER_OBJECT_COUNT=6,\
TABLETOP_CLUTTER_ASSET_ASSIGNMENT=random,\
SEED=<agent-seed> \
    cluster/sbatch_train_teacher_8gpu.sh'
```

Monitor at least:

- placement/success rate and stable success rate
- lift height and goal/bin distance
- object linear and angular speed
- out-of-bounds, table penetration, and termination rates
- clutter placement success and bin clearance
- reward terms and PPO losses
- policy action statistics and gripper behavior

Cancel or patch if metrics show reward hacking, false bin placement, high-speed
object launch, reset churn, NaNs, flatlined rewards, or repeated local optima.

## Required Policy Evaluation

Any candidate checkpoint must be evaluated policy-only with representative
videos and metrics.

Minimum acceptance tiers:

1. Target-object bin placement: policy places the active target object into the
   bin under randomized clutter.
2. Repeated removal: a policy-only loop clears multiple tabletop objects one by
   one, with no scripted action source.
3. Deployment-style held-out evaluation: same camera and robot setup, but
   held-out object identities and held-out object locations.

Final success requires tier 3. Training curves alone are not success evidence.

## Reporting

Each agent report must include:

- Branch, local worktree, remote worktree, and base commit.
- Files audited before first experiment.
- Candidate hypotheses and chosen first test.
- Exact commands, job ids, logs, run directories, metrics, checkpoints, videos,
  and decisions.
- Peer branches inspected and ideas adopted.
- Active jobs and cleanup state before handoff.

## Neutral Agent Lanes

Use neutral lanes so branch names do not bias agents toward methods.

| Agent | Branch |
| --- | --- |
| `clutter-removal-a01` | `agent/clutter-removal/a01` |
| `clutter-removal-a02` | `agent/clutter-removal/a02` |
| `clutter-removal-a03` | `agent/clutter-removal/a03` |
| `clutter-removal-a04` | `agent/clutter-removal/a04` |
