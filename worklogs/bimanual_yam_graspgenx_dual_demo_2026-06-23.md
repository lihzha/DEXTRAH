# Bimanual YAM GraspGenX/cuRobo Dual-Pick Demo

Date: 2026-06-23
Branch: `codex/bimanual-yam-graspgenx-dual-demo`

## Goal

Check whether the bimanual YAM setup is ready for a GraspGenX + cuRobo demo, then generate a demo where the bimanual YAM picks two objects simultaneously, one object per arm.

## Initial Readiness Finding

- The existing DEXTRAH YAM GraspGenX/cuRobo bridge is single-arm. It targets the `yam_linear` profile and exports 8-DOF trajectories.
- l401 has the required single-YAM GraspGenX/cuRobo assets:
  - `/lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx/end2end/robots/yam_linear.yaml`
  - `/lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx/end2end/curobo_assets/yam_linear.yml`
  - `/lustre/fsw/portfolios/nvr/users/lzha/src/graspgenx/end2end/curobo_assets/yam_linear.urdf`
  - `/lustre/fsw/portfolios/nvr/users/lzha/cache/graspgenx_ngc2503_base.sqsh`
  - `/lustre/fsw/portfolios/nvr/users/lzha/envs/graspgenx-py312/bin/python`
- No native 16-DOF bimanual YAM cuRobo profile is present yet. The first demo path composes two single-arm plans and replays them simultaneously on the Isaac Lab bimanual YAM asset.

## Implementation

- Added `dextrah_lab/scene_scripts/plan_bimanual_yam_dual_pick_graspgenx_curobo.py`.
  - Generates one minimal stable scene per arm.
  - Uses the original MolmoAct2/MJCF home keyframe as the single-arm planner start.
  - Calls the existing `plan_yam_graspgenx_curobo.py` twice.
  - Converts the two 8-DOF plans into one time-padded 16-DOF bimanual trajectory.
- Added `dextrah_lab/scene_scripts/render_bimanual_yam_dual_pick_demo.py`.
  - Spawns the bimanual YAM task with two object cubes.
  - Replays the synchronized 16-DOF trajectory.
  - Carries each cube kinematically after that arm's grasp/lift phase starts.
  - Renders overview plus the three MolmoAct2 policy cameras.
- Added `cluster/sbatch_demo_bimanual_yam_dual_pick_graspgenx_curobo_1gpu.sh`.
  - Runs GraspGenX/cuRobo planning in the GraspGenX container.
  - Runs Isaac Lab replay/render in the Isaac Lab container.
  - Stages ignored D405/wrist-camera YAM assets from the previously validated l401 worktree when missing.
