# YAM Demo Main Integration - 2026-06-23

## 2026-06-23 Integration

- Goal: merge the YAM two-bin iterative demo, YAM 50-object multi-demo, and bimanual YAM GraspGen-X dual demo into `main` while preserving all three workflows.
- Integration worktree: `/home/lzha/code/worktrees/DEXTRAH/main-yam-demo-integration`
- Base `main`: `a90b0739609c87b2c966c74682b173d9df2ad9df`
- Branch tips merged:
  - `codex/bimanual-yam-graspgenx-dual-demo`: `7ee6e0a088f563970bcb5e8d4294ae9d06e51f7a`
  - `codex/yam-50-multidemo`: `e5c2737b2f0f5283b05d76c3c386ed0502531058`
  - `codex/yam-two-bin-demo-20260622T233055Z-3635211`: `8a9e53cfeab8c78b20af53a1366b4ad2402f77ef`
- Two-bin handoff commit created before integration: `8a9e53cfeab8c78b20af53a1366b4ad2402f77ef`.
- Merge commits:
  - `Merge bimanual YAM dual demo`
  - `Merge YAM 50-object multi-demo`
  - `Merge YAM two-bin iterative demo`
- Conflict resolution:
  - `dextrah_lab/scene_scripts/plan_yam_multi_object_pick_place.py`: preserved the 50-demo greedy remaining-object retry loop, completed-object removal, return-to-start behavior, grasp filter controls, and sequence-aware drop offsets; added the two-bin `--scripted_place_mode` forwarding to `plan_yam_graspgenx_curobo.py`.
  - `dextrah_lab/scene_scripts/validate_yam_pick_place_dataset.py`: preserved 50-demo expected-object and sequence metadata checks; added two-bin goal-bin validation and contact-proxy metrics.
- Validation:
  - Broad `py_compile` over all Python files changed since base `main`: passed.
  - `bash -n` over all shell files changed since base `main`: passed.
  - `git diff --check`: passed.
  - `git merge-base --is-ancestor` verified all three requested branch tips are included in integrated `main`.
- Runtime note: no new render/simulation jobs were launched during integration; previously inspected branch artifacts remain in their source worktrees.
