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
