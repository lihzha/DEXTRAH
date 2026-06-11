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
