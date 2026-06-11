# DEXTRAH Eval Videos - dextrah-eval-videos-20260611T102249

## 2026-06-11 10:22 PDT - Isolated eval setup

Goal:
- Generate validated rollout videos for the completed DEXTRAH Kuka Allegro teacher run `teacher_short_20260609_100021`.

Hypothesis:
- The existing `eval_rollout.py` video path can render deterministic one-env rollouts from the final teacher checkpoint if launched through a Kuka-specific A100 wrapper with the same core task overrides used by teacher training.

Change:
- Added `cluster/sbatch_eval_kuka_allegro_1gpu.sh` for 1-GPU Kuka Allegro checkpoint evaluation with video capture, parameterized source/results paths, camera pose, checkpoint, seed, and run name.

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249`
- worklog: `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- branch: `codex/dextrah-eval-videos/20260611T102249`
- base_commit: `d7ff3d0`
- implementation_commit: pending
- push/pull: pending
- changed_files: `cluster/sbatch_eval_kuka_allegro_1gpu.sh`, `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- remote_commit/status: pending

Command / Job:
- command: pending validation and Slurm submission
- job_id: pending
- run_dir: pending
- logs: pending
- artifacts: expected `metrics.json` and `videos/*.mp4`

Result:
- status: in progress
- metrics/artifacts: pending
- key evidence: pending

Analysis:
- The shared checkout is dirty and behind remote, so all edits and launches are isolated in this worktree. Eval will use the final checkpoint `last_dextrah_lstm_ep_20000_rew_673.2542.pth`.

Next:
- Run shell syntax checks, commit/push, deploy the exact commit to an agent-owned A100 worktree, then submit short video eval jobs.
