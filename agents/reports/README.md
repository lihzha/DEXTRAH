# Agent Reports

Each parallel agent owns exactly one report file named `agents/reports/<CODEX_AGENT_ID>.md`.

Report template:

```markdown
# <CODEX_AGENT_ID> Report

## Assignment

- Branch:
- Local worktree:
- Remote worktree:
- Starting hypothesis:
- Base commit:

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
