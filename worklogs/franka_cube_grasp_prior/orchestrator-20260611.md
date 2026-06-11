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

