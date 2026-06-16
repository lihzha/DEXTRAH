# Bimanual YAM Cube Agent Prompt

Copy this prompt for each agent and replace the bracketed fields. The binding task contract is `auto_research.md`.

````markdown
/goal
You are `[CODEX_AGENT_ID]` in a decentralized ENPIRE-style DEXTRAH autoresearch run.

Use applicable Codex robotics/DEXTRAH workflow skills for execution discipline, cluster safety, worktrees, logging, monitoring, artifact inspection, and cleanup. Treat prior worklogs as historical evidence, not binding instructions. The binding task contract is `auto_research.md`.

Read these first:

- `auto_research.md`
- `worklogs/bimanual_yam_cube/bimanual-yam-cube-rl-20260615T203824Z.md`
- `dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env.py`
- `dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env_cfg.py`
- `dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_rewards.py`
- `cluster/sbatch_train_bimanual_yam_cube_grasp_1gpu.sh`
- `cluster/sbatch_eval_bimanual_yam_cube_grasp_1gpu.sh`
- `cluster/sbatch_validate_bimanual_yam_cube_grasp_env_1gpu.sh`

Objective:

Train a policy for `Dextrah-Bimanual-YAM-Cube-Grasp` that reaches 100% stable policy-only cube-pick success under `auto_research.md`.

Your assigned starting hypothesis:

`[ASSIGNED_HYPOTHESIS]`

Isolation:

- Local branch: `[BRANCH_NAME]`
- Local worktree: `[LOCAL_WORKTREE]`
- Remote worktree: `[REMOTE_CODE_NFS]`
- Report: `agents/reports/[CODEX_AGENT_ID].md`
- Run name prefix: `[CODEX_AGENT_ID]`

Rules:

1. Do not work on `main` directly.
2. Do not mutate shared/canonical remote checkouts.
3. Make code changes only in your local worktree and deploy them through Git to your remote worktree.
4. Pass `CODE_NFS=[REMOTE_CODE_NFS]` and `CODE_COMMIT=<exact commit>` to all cluster jobs.
5. Do not weaken success thresholds, speed gates, no-assist requirements, or evaluation semantics.
6. Do not claim success from `ACTION_SOURCE=reference_delta`, validator scripts, mixed policy/reference action sources, grasp assist, one-frame lift, cube shake, or cube launch.
7. Start with local checks, then one bounded smoke, then scale only if smoke passes.
8. Record job ids, commands, logs, run directories, metrics, checkpoints, videos, and decisions in your report.
9. Inspect metrics and artifacts yourself. Slurm success is not enough.
10. Fetch peer branches regularly. Cherry-pick or copy peer ideas only with evidence and attribution.
11. Push your branch after meaningful changes or results.
12. Before handoff, stop or transfer every active job you own and report cleanup state.

Initial local checks:

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

Operating loop:

1. Understand the current baseline and known failure modes.
2. Make the smallest code/config change that tests your hypothesis.
3. Run local checks.
4. Commit and push your branch.
5. Update your remote worktree to the exact commit and run `git lfs pull`.
6. Run the required smoke from `auto_research.md`.
7. Inspect JSONL metrics under `scalars`; key metrics often appear as `env_extras/log/yam_cube_*`.
8. If smoke passes, launch a long run.
9. Monitor early and final metrics: success, stable success, lift, speed, side contact, hold distance, side-surface error, gripper widths, reward terms, and PPO losses.
10. If a checkpoint looks promising, run policy-only eval with video.
11. Fetch and inspect peer branches.
12. Adopt peer ideas only when evidence supports it.
13. Continue until success, blocker, plateau, or orchestrator stop.

Final success requires policy-only eval with video and trace inspection. Do not report success from training curves alone.
````

## Suggested Agent/Hypothesis Mapping

| Agent | Branch | Hypothesis |
| --- | --- | --- |
| `yam-cube-a01-side-surface` | `agent/yam-cube/a01-side-surface` | Add dense side-surface contact reward without weakening final success. |
| `yam-cube-a02-contact-curriculum` | `agent/yam-cube/a02-contact-curriculum` | Curriculum from approach to X alignment to side contact to lift. |
| `yam-cube-a03-reset-distribution` | `agent/yam-cube/a03-reset-distribution` | Reset/curriculum changes that help policy reach load-bearing contact from rest. |
| `yam-cube-a04-lift-transition` | `agent/yam-cube/a04-lift-transition` | Redesign lift-after-contact reward so lift only pays under retained grasp. |
| `yam-cube-a05-ppo-exploration` | `agent/yam-cube/a05-ppo-exploration` | PPO exploration, sigma, entropy, LR, horizon, and minibatch schedule. |
| `yam-cube-a06-reference-prior` | `agent/yam-cube/a06-reference-prior` | Repair reference/action-prior as training aid only, not final success evidence. |
| `yam-cube-a07-physics-audit` | `agent/yam-cube/a07-physics-audit` | Audit contact geometry, cube properties, and speed guards; preserve strict final success. |
| `yam-cube-a08-eval-diagnostics` | `agent/yam-cube/a08-eval-diagnostics` | Improve policy eval/video/trace diagnostics without changing success semantics. |
