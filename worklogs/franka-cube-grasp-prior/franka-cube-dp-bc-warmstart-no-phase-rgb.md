## 2026-06-13T19:17:10Z - no-phase unique RGB data setup

Goal:
- Replace repeated nominal RGB demos with unique uniformly sampled cube-location demos over the default reachable Franka cube support.
- Remove the four non-privileged phase/progress timing features from the next RGB BC train/eval loop.

Hypothesis:
- The previous nominal success did not prove useful data diversity because it trained on repeated episodes and timing features.
- A clean image policy test should use 8D robot proprio only and unique object locations with explicit coverage metadata.

Change:
- Added explicit task-frame cube XY reset support to contact-aware demo rollout and RGB eval.
- Extended relabel aggregation and RGB combination to preserve per-episode applied cube positions.
- Added a uniform reachable-support spec generator for per-demo cube XY specs.
- Added an RGB dataset report/video helper for shape checks, cube XY coverage, duplicate rollout IDs, and three-trajectory MP4 visualization.
- Changed the RGB train wrapper defaults to 8D robot state, no appended phase/progress, no distillation, and from-scratch training unless an init checkpoint is explicitly provided.

Version Control:
- agent_id: franka-cube-no-phase-rgb
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `10a924232fe6ac72eaef026acb1eed13d8db2533`
- implementation_commit: `40bd5c5d5e3b51d8a8419603bb40d9fbd418184b`
- changed_files: `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`, `cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`, `cluster/sbatch_train_franka_cube_rgb_dp_1gpu.sh`, `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`, `dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py`, `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`, `dextrah_lab/offline_dp_bc/combine_contact_relabel_rgb_sets.py`, `dextrah_lab/offline_dp_bc/make_uniform_cube_relabel_specs.py`, `dextrah_lab/offline_dp_bc/make_rgb_dataset_report.py`

Command / Job:
- local checks:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile ...`
  - `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh cluster/sbatch_train_franka_cube_rgb_dp_1gpu.sh cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`
  - `git diff --check -- <changed files>`
  - uniform spec generator smoke with 4 specs
  - RGB dataset report smoke on a synthetic two-episode NPZ

Result:
- status: passed local validation
- metrics/artifacts: synthetic RGB report produced an MP4 through the ffmpeg fallback; spec generator produced 4 unique rounded-to-1mm XY locations.

Analysis:
- Existing rollout generation could use normal task resets, but a global seed makes locations hard to audit and repeat across specs. Explicit cube XY per spec gives deterministic data collection and later OOD probes.
- Existing RGB train wrapper was a footgun: wrapper defaults were 12D/phase-progress even though the YAML defaults were 8D. This has been changed for the next experiment.

Next:
- Commit these changes, deploy the exact commit to the l401 agent worktree, then run a small unique-location RGB collection smoke before scaling.
