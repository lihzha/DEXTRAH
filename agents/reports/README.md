# Agent Reports

Each parallel agent owns exactly one report file named `agents/reports/<CODEX_AGENT_ID>.md`.

Report template:

```markdown
# <CODEX_AGENT_ID> Report

## Assignment

- Branch:
- Local worktree:
- Remote worktree:
- Base commit:

## Survey

- Files inspected:
- Prior runs/worklogs inspected:
- Peer branches inspected before first experiment:
- Key bottlenecks inferred:

## Candidate Hypotheses

1.
2.
3.
4.

## Selected Current Hypothesis

- Hypothesis:
- Evidence/rationale:
- Smallest first test:

## Current Best

- Commit:
- Checkpoint:
- Policy eval metrics:
- Video:
- Decision:

## Experiments

| Attempt | Commit | Job | Run Dir | Key Settings | Result | Decision |
| --- | --- | --- | --- | --- | --- | --- |

## Peer Branches Inspected

| Time | Branch | Commit | Finding | Action |
| --- | --- | --- | --- | --- |

## Adopted Peer Ideas

- Source:
- Local commit:
- Reason:

## Active Jobs And Cleanup

- Active jobs:
- Logs fetched:
- Artifacts fetched:
- Cleanup status:

## Final Handoff

- Final commit:
- Final status:
- Remaining blockers:
- Suggested next step:
```
