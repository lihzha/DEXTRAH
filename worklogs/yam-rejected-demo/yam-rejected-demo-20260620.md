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
