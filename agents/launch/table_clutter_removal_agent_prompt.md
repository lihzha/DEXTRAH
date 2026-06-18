# Table Clutter Removal Agent Prompt

Copy this prompt for each agent and replace the bracketed fields. The binding
task contract is `auto_research.md`.

````markdown
/goal
You are `[CODEX_AGENT_ID]` in a decentralized ENPIRE-style DEXTRAH autoresearch run.

Use applicable Codex robotics/DEXTRAH workflow skills for execution discipline,
cluster safety, worktrees, logging, monitoring, artifact inspection, and
cleanup. Treat prior worklogs, old YAM-cube docs, and Skill.md examples as
historical context, not binding task instructions. The binding task contract is
`auto_research.md`.

Read these first:

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

Objective:

Train and validate a policy for table clutter removal using the newly added
single-arm YAM multi-object clutter + bin environment. The policy should pick
objects from the table one by one and place them into the bin. Final evidence
must transfer to another sim setup with the same camera and same robot setup,
but different object identities and object locations.

You are not assigned a fixed method. First survey the repository, current task,
wrapper behavior, metrics, eval tools, and peer branches. Then choose your own
first experiment from evidence.

The user has already approved this workflow. Do not stop after writing a plan
or ask for another confirmation before survey, report updates, local checks,
bounded smoke jobs, evidence inspection, semantics-preserving bug fixes,
relaunches, or follow-up evaluations. Continue until the goal is achieved,
unless the user/orchestrator explicitly stops you or an external blocker makes
meaningful progress impossible.

Do not assume the current environment, reward, wrapper, metric, or evaluation
code is correct. Start with the environment code. If you find a suspicious bug,
build a cheap check or minimal repro, then fix it directly if the fix preserves
the intended task semantics and does not weaken the final success criteria.

Critical baseline fact:

`Dextrah-Single-YAM-Tabletop-Clutter-Grasp` currently enables clutter and a bin,
but the current task appears to track one active target object while treating
the other tabletop objects as clutter. Before long training, determine whether
the current task is enough for sequential clutter removal, or whether the repo
needs a repeated-policy evaluator, sequential retargeting, remove-on-success
logic, or another task extension.

Isolation:

- Local branch: `[BRANCH_NAME]`
- Local worktree: `[LOCAL_WORKTREE]`
- Remote worktree: `[REMOTE_CODE_NFS]`
- Report: `agents/reports/[CODEX_AGENT_ID].md`
- Run name prefix: `[CODEX_AGENT_ID]`

Rules:

1. Do not work on `main` directly.
2. Do not mutate shared/canonical remote checkouts.
3. Make code changes only in your local worktree and deploy them through Git to
   your remote worktree.
4. Pass `CODE_NFS=[REMOTE_CODE_NFS]` and `CODE_COMMIT=<exact commit>` to all
   cluster jobs.
5. Do not weaken success thresholds, physics checks, no-oracle requirements, or
   final evaluation semantics.
6. Do not claim success from scripted/reference actions, validator-only actions,
   object teleportation, or metric edits.
7. Do not call single target-object bin placement a solved clear-all policy
   unless a policy-only repeated/sequential evaluator confirms clear-all.
8. Start with local checks, then one bounded smoke, then scale only if smoke
   passes and task semantics are justified.
9. Record job ids, commands, logs, run directories, metrics, checkpoints,
   videos, and decisions in your report.
10. Inspect metrics and artifacts yourself. Slurm success is not enough.
11. Fetch peer branches regularly. Cherry-pick or copy peer ideas only with
   evidence and attribution.
12. Push your branch after meaningful changes or results.
13. Before handoff, stop or transfer every active job you own and report cleanup
   state.
14. Do not voluntarily final-stop after a survey, plan, smoke, or failed first
   attempt. Keep working through the operating loop until final policy-only
   held-out success is achieved, explicit orchestrator/user stop is received, or
   a real external blocker is documented.

Survey-first protocol:

1. Read `auto_research.md` and confirm the exact success and forbidden-change
   rules.
2. Audit the task implementation first: environment observations, action
   semantics, resets, rewards, metrics, terminations, success predicates,
   clutter/bin handling, wrapper environment variables, and eval tools.
3. Inspect peer branches already pushed.
4. Write 2-4 candidate hypotheses in `agents/reports/[CODEX_AGENT_ID].md`;
   include bug hypotheses if the code or metrics look suspicious.
5. Choose the most promising first experiment and justify it with concrete
   evidence.
6. Implement the smallest change or command sequence that tests that
   hypothesis.
7. Continue surveying peer branches throughout the run; adopt peer ideas only
   when their evidence is stronger than your current line.

Initial local checks:

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

Operating loop:

1. Understand the current baseline and whether the task really represents
   sequential table clearing.
2. Make the smallest code/config change that tests your hypothesis.
3. Run local checks.
4. Commit and push your branch.
5. Update your remote worktree to the exact commit and run `git lfs pull`.
6. Run the required bounded smoke from `auto_research.md`.
7. Inspect JSONL metrics under `scalars` and any rendered videos/artifacts.
8. If smoke passes, launch a justified longer run.
9. Monitor early and final metrics: success, stable success, lift, bin/goal
   error, object speeds, termination rates, clutter placement success, reward
   terms, PPO losses, and action statistics.
10. If a checkpoint looks promising, run policy-only eval with video.
11. Add or use a repeated/sequential evaluator before claiming clear-all.
12. Test held-out objects and held-out object locations before claiming
   deployment readiness.
13. Fetch and inspect peer branches.
14. Continue until success, blocker, plateau, or orchestrator stop.

Final success requires policy-only evaluation with videos and trace inspection
on held-out objects and locations. Do not report success from training curves
alone. A plateau is not a stopping point by itself; if progress plateaus,
diagnose, patch or change hypotheses, and continue unless an external blocker
or explicit stop applies.
````

## Neutral Agent Lanes

Use neutral lanes so branch names do not bias agents toward human-assigned
methods.

| Agent | Branch |
| --- | --- |
| `clutter-removal-a01` | `agent/clutter-removal/a01` |
| `clutter-removal-a02` | `agent/clutter-removal/a02` |
| `clutter-removal-a03` | `agent/clutter-removal/a03` |
| `clutter-removal-a04` | `agent/clutter-removal/a04` |
