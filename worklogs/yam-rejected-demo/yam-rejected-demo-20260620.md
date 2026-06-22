# YAM Rejected-Path Demo Worklog

## 2026-06-20 - Implementation

- Goal: merge the earlier rejected-path visualization logic into the current DEXTRAH single-YAM tabletop clutter environment and render a new demo using DEXTRAH's current meshes, collision setup, and start pose.
- Branch/worktree: `codex/yam-rejected-demo` at `/home/lzha/code/worktrees/DEXTRAH-yam-rejected-demo`.
- Plan: reuse `Dextrah-Single-YAM-Tabletop-Clutter-Grasp`, add a scripted low-clearance demo mode to the existing tabletop render script, preserve the default settle render path, and run through the existing l401 wrapper when local Isaac is unavailable.
- Change: added `single_yam_rejected_path` mode to `dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py`. The mode manually steps the task to avoid Gym auto-reset, drives the YAM hold point through a low table-clearance path, records the first table-clearance rejection, and writes per-step trajectory metrics.
- Change: updated `cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh` to pass demo-mode arguments and prepare the single-YAM USD with `--robot single` when launching single-YAM tasks.
- Local validation: `python3 -m py_compile dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py` passed.
- Local validation: `bash -n cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh` passed.
- Next: commit/push the exact source revision, deploy it to an agent-owned l401 worktree, launch a small demo render, fetch artifacts, and inspect the resulting video/metrics.

## 2026-06-21 - l401 Render Iteration

- Version: `5687c923af79925b6fc2642fe247c0af37af7d4e`.
- Remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rejected-demo-20260621T065917Z`.
- Job: `1038483`, run `single_yam_rejected_path_5687c923_20260621T0701Z`, node `pool0-00019`.
- Command: `sbatch --parsable --export=ALL,CODE_NFS=<agent-worktree>,CODE_COMMIT=5687c923af79925b6fc2642fe247c0af37af7d4e,TASK=Dextrah-Single-YAM-Tabletop-Clutter-Grasp,RUN_NAME=single_yam_rejected_path_5687c923_20260621T0701Z,NUM_ENVS=1,SEED=42,SETTLE_STEPS=0,CAPTURE_INTERVAL=3,FPS=24,VIDEO_SECONDS=3.0,DEMO_MODE=single_yam_rejected_path,DEMO_STEPS=144,DEMO_HIGH_HOLD_Z=0.16,DEMO_LOW_HOLD_Z=-0.02,RENDER_WARMUP_FRAMES=2,PREPARE_YAM_ASSETS=auto,DISABLE_FABRIC=False cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`.
- Result: Slurm completed and wrote a 72-frame MP4 plus metrics, but this was rejected as evidence because metrics reported `first_rejected_step=null`; minimum finger-table clearance was about `0.05098 m`, above the `-0.008 m` penetration rejection margin.
- Analysis: the scripted target used the object center buffer, which can be shifted far away by object bounds for some Objaverse assets. The controller saturated laterally and did not descend far enough to trip the DEXTRAH table-clearance rejection.
- Change: update the demo action target to use the simulated target object root, clamped to the current table footprint, before applying the low-clearance descent.
- Next: commit the target-selection fix, redeploy to the same agent worktree, and rerun with a lower `DEMO_LOW_HOLD_Z`.

## 2026-06-21 - Replay and Current-Scene Diagnosis

- Version: `204235d0bfc0fb823bfed2b31537353474c60f6c`.
- Job: `1038488`, run `single_yam_rejected_path_204235d0_low_20260621T0710Z`.
- Result: Slurm completed and wrote a valid 72-frame MP4, but metrics still reported `first_rejected_step=null`; minimum finger-table clearance was about `0.03153 m`.
- Analysis: the action-driven fallback plateaued above the current table and did not visibly show the rejected nominal path.
- Version: `f2b11bac7eeaa7a16b6763dd27ac69c66129c869`.
- Change: imported the compact GraspGenX/cuRobo rejected nominal trajectory from `/home/lzha/code/worktrees/graspgenx-yam-ggx-curobo/end2end/runs/yam_linear_rejected`, added a kinematic replay branch, and recorded the original GraspGenX tabletop rejection metadata.
- Job: `1038494`, run `single_yam_rejected_trajectory_f2b11bac_20260621T0734Z`.
- Result: Slurm completed and wrote a valid 96-frame, 4.0 s MP4. The video was nonblank and replayed the trajectory, but current DEXTRAH metrics still reported `first_rejected_step=null`; minimum current-scene finger-table clearance was about `0.30922 m`.
- Analysis: the exported GraspGenX trajectory was rejected in its original tabletop scene, but its YAM base/table frame differs from current DEXTRAH. In current DEXTRAH, the replayed hand stays high above the table, so it is not sufficient evidence for a current-scene rejected-path demo.

## 2026-06-21 - DEXTRAH-Native Rejected Path

- Change: added `--demo_trajectory_source` with `dextrah_table_rejection`, preserving `graspgenx_replay` for the imported trajectory and `none` for the older action fallback.
- Change: added a sampled single-YAM joint target in the current DEXTRAH joint order. The target is within URDF joint limits, lies over the current table footprint, and drives the finger links below the current `table_surface_z` when replayed kinematically from the live DEXTRAH start pose.
- Change: added `--demo_table_rejection_target_fraction` and wrapper env passthrough so the render can tune how deeply the nominal rejected path enters the current table collision.
- Local validation: `python3 -m py_compile dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py` passed.
- Local validation: `bash -n cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh` passed.
- Local validation: `python3 -m json.tool dextrah_lab/assets/yam/rejected_nominal_trajectory_compact.json >/dev/null` passed.
- Local validation: `git diff --check` passed.
- Version: `d4d752c96c68247a82a20118d35612ada352dea6`.
- Remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rejected-demo-20260621T065917Z`.
- Job: `1038499`, run `single_yam_dextrah_rejected_d4d752c9_20260621T0738Z`, node `pool0-00034`.
- Command: `sbatch --parsable --export=ALL,CODE_NFS=<agent-worktree>,CODE_COMMIT=d4d752c96c68247a82a20118d35612ada352dea6,TASK=Dextrah-Single-YAM-Tabletop-Clutter-Grasp,RUN_NAME=single_yam_dextrah_rejected_d4d752c9_20260621T0738Z,NUM_ENVS=1,SEED=43,SETTLE_STEPS=0,CAPTURE_INTERVAL=4,FPS=24,VIDEO_SECONDS=4.0,DEMO_MODE=single_yam_rejected_path,DEMO_STEPS=360,DEMO_TRAJECTORY_SOURCE=dextrah_table_rejection,DEMO_TABLE_REJECTION_TARGET_FRACTION=0.82,DEMO_START_BLEND_STEPS=0,MAX_OBJECTS=64,TABLETOP_CLUTTER_MAX_OBJECTS=64,OBJECT_ASSET_ASSIGNMENT=round_robin,OBJECT_SPAWN_XY_RANDOMIZATION=0.0,RENDER_WARMUP_FRAMES=2,PREPARE_YAM_ASSETS=auto cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`.
- Result: Slurm completed with `ExitCode=0:0` in `00:03:21`.
- Evidence: fetched artifacts to `/home/lzha/code/cluster_results/l401/single_yam_dextrah_rejected_d4d752c9_20260621T0738Z`.
- Evidence: `single_yam_rejected_path.mp4` is 1280x720, 24 FPS, 4.0 s, 96 frames.
- Evidence: metrics report `trajectory_source=dextrah_table_rejection`, `first_rejected_step=204`, `min_clearance=-0.2217942327`, `min_clearance_step=281`, and `rejected_row_count=157`.
- Evidence: inspected frames `0048`, `0055`, `0075`, and `0095`; they are nonblank and show the current YAM arm descending into the current tabletop region and then holding the rejected nominal pose.
- Status: accepted as the new DEXTRAH current-scene rejected-path demo. The prior GraspGenX/cuRobo exported trajectory remains available as `graspgenx_replay`, but the final render uses the current DEXTRAH scene collision metric for the rejection event.
