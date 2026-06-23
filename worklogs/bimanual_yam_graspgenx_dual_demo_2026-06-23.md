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
  - Also stages the ignored bimanual YAM USD `configuration/` payloads required by the bimanual Isaac asset.

## Validation

- Local checks passed:
  - `python3 -m py_compile dextrah_lab/scene_scripts/plan_bimanual_yam_dual_pick_graspgenx_curobo.py dextrah_lab/scene_scripts/render_bimanual_yam_dual_pick_demo.py`
  - `bash -n cluster/sbatch_demo_bimanual_yam_dual_pick_graspgenx_curobo_1gpu.sh`
  - `git diff --check`
- l401 job `1039674` failed with the default 8 cm cube:
  - GraspGenX produced grasps, but the YAM gripper/OBB sweep rejected the 8 cm object as wider than the configured 7.1 cm gripper width.
  - cuRobo returned `Goalset planning returned None`.
- l401 job `1039679` with a 5.5 cm cube passed both single-arm GraspGenX/cuRobo plans, then failed in render because ignored bimanual USD payloads were not staged.
- l401 job `1039683` passed planning and rendered frames/videos, then failed writing metadata due a missing `_write_json` helper.
- l401 job `1039691` completed end-to-end at commit `faca8c26`.
  - Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bimanual_yam_dual_pick_demo/yam_dual_pick_demo_faca8c26_smallobj_20260622T2151`
  - Local copy: `cluster_results/l401/yam_dual_pick_demo_faca8c26_smallobj_20260622T2151`
  - Videos: composite, overview, top camera, left wrist camera, right wrist camera.
  - `ffprobe` verified 211 frames, 12 fps, 17.58 seconds for each MP4.
- l401 jobs `1039695` and `1039699` completed end-to-end after overview-camera changes for better inspection.
  - Final completed visual artifact: `cluster_results/l401/yam_dual_pick_demo_891fbe76_smallobj_20260622T2202/render/bimanual_yam_dual_pick_composite.mp4`
  - Viz URL opened locally: `http://localhost:8765/view?path=DEXTRAH/cluster_results/l401/yam_dual_pick_demo_891fbe76_smallobj_20260622T2202/render/bimanual_yam_dual_pick_composite.mp4`
  - Metadata reports both objects moving from z=0.0275 m to z=0.2697 m and z=0.2851 m.
- A final replay-loop fix at commit `bd4be36b` switches the renderer to `scene.write_data_to_sim()` + `sim.forward()` and records actual object root poses after scene update.
  - Validation job `1039728` was submitted for this commit but remained pending on priority with an estimated start over an hour later.
  - Job `1039728` was canceled to avoid leaving an unmanaged cluster job.

## Conclusion

- Single-YAM GraspGenX + cuRobo is ready for the YAM profile on l401.
- The bimanual YAM is not yet natively ready as one 16-DOF cuRobo robot. There is no native bimanual YAM cuRobo asset/profile in the checked setup.
- A composed bimanual demo path now exists: plan each YAM independently with GraspGenX/cuRobo, synchronize the two plans, and replay them on the Isaac Lab bimanual YAM scene.
- The completed demo artifacts show the full environment plus three policy camera streams, but the visual replay remains a kinematic demonstration rather than a dynamic contact validation. The latest replay-loop fix needs a GPU validation run once the queue is available.
