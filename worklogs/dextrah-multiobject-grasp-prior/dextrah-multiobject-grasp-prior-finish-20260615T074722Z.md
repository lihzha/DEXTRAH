## 2026-06-15T07:47:22Z - Start isolated continuation

Goal:
- Finish Franka multi-object RL training with grasp prior, treating the handoff and current implementation as useful but not fully trusted.

Hypothesis:
- The stable-pose object initialization is likely close to correct, but multi-object grasp-prior candidate selection, verified-cache use, and/or validation/training wrapper wiring may still differ from the known-good single-cube Franka environment enough to break training.

Change:
- Created an isolated local worktree and branch from current main.
- No source edits yet.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `ee2594e1320010e1f59c355aa6955c899b08a9df`
- implementation_commit: self, commit containing this worklog entry
- push/pull: pending
- changed_files: this worklog
- remote_commit/status: n/a

Command / Job:
- command: `git worktree add -b codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z /home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z ee2594e1320010e1f59c355aa6955c899b08a9df`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: n/a

Result:
- status: passed
- metrics/artifacts: local worktree created.
- key evidence: base commit is `ee2594e1320010e1f59c355aa6955c899b08a9df`; shared checkout had only unrelated untracked `worklogs/franka-star-kitting-rl/`.

Analysis:
- Follow-up work must use the isolated branch/worktree. Current live queue check showed no l401 jobs and only unrelated a1001 CPU job `29061545`.

Next:
- Audit single-cube versus multi-object reset/grasp-prior implementation, then patch the smallest confirmed bug set before cluster validation.

## 2026-06-15T08:04:00Z - Finger-level table gate and bounded validation scoring

Goal:
- Fix reset candidate selection so a selected multi-object grasp-prior reset cannot be considered table-valid merely because the EE frame is above the table.
- Prevent close-camera grasp-contact validation from stalling in unbounded pre-capture scoring.

Hypothesis:
- The current multi-object selector checks pregrasp EE z and contact-reference z for table safety, but the gripper bodies that collide with the table are the left/right finger bodies. The single-cube path catches some failures after IK, but multi-object candidate scoring can still waste attempts on physically invalid candidates before post-IK quality checks.
- Validation jobs stalled because `_select_scored_grasp_contact_state()` scored every quality candidate across many attempts with no wall-clock or env-count cap.

Change:
- Added EE-frame left/right finger offsets in `franka_multi_object_grasp_env.py`.
- Candidate selection now computes projected left/right finger positions for both pregrasp and exact-contact poses and requires both to clear the table floor.
- The post-selection topdown/table mask now uses selected projected finger clearances when available.
- Added `--grasp_contact_max_score_envs` and `--grasp_contact_max_score_seconds` to the multi-object video validation script.
- Exposed those validation caps in `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, defaulting to 4 candidate envs and 300 seconds.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `ee2594e1320010e1f59c355aa6955c899b08a9df`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, this worklog
- remote_commit/status: n/a

Command / Job:
- command: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`
- command: `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`
- command: `git diff --check`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: n/a

Result:
- status: passed
- metrics/artifacts: local syntax and diff checks passed.
- key evidence: diff is limited to reset candidate table filtering, validation scoring caps, wrapper pass-through, and this worklog.

Analysis:
- This directly addresses the user constraint that reset sampling must not select gripper/table-colliding poses and should reject below-table or below-object approaches before training.
- It does not yet prove grasp robustness or training success; l401 validation must regenerate/verify current metrics after this commit.

Next:
- Commit, then continue audit and run cluster validation from the exact committed source.

## 2026-06-15T07:53:42Z - Regenerate verified cache with finger-clearance gate

Goal:
- Produce a current verified-grasp cache after the stricter projected finger/table clearance gate, instead of relying on pre-patch cached indices.

Hypothesis:
- The previous practical cache may still identify useful sample indices, but it was generated before candidate selection rejected projected finger table collisions. A fresh small cache should confirm which indices survive the current reset contract.

Change:
- Deployed commit `5af8191fbdaecddbbf278272acc38f176d6e71e8` to an agent-owned l401 worktree via Git bundle.
- Launched bounded robust verified-grasp collection with top-side `min_pregrasp_z=0.70`, stable-pose cache, full yaw randomization, `MIN_PASS_OBSERVATIONS_PER_INDEX=3`, and `MIN_PASS_RATE_PER_INDEX=0.10`.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `ee2594e1320010e1f59c355aa6955c899b08a9df`
- implementation_commit: `5af8191fbdaecddbbf278272acc38f176d6e71e8`
- push/pull: deployed to l401 by Git bundle, fetched into `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`, checked out detached remote worktree.
- changed_files: worklog only since commit `5af8191fbdaecddbbf278272acc38f176d6e71e8`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` at `5af8191fbdaecddbbf278272acc38f176d6e71e8`, clean.

Command / Job:
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=5af8191fbdaecddbbf278272acc38f176d6e71e8,RUN_NAME=verified_fingerclear_obs3_rate10_train2_7195_b87_5af8191_20260615T0753Z,... cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`
- job_id: `1029724`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_fingerclear_obs3_rate10_train2_7195_b87_5af8191_20260615T0753Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029724.out`
- artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_fingerclear_obs3_rate10_train2_7195_b87_5af8191_20260615T0753Z/verified_indices.json`

Result:
- status: canceled
- metrics/artifacts: after 16 cycles, no robust indices exported. Final partial summary after cancel: object0 `quality_reset_count=0`, `pass_count=0`; object1 `quality_reset_count=347`, `pass_count=1`; `indices_by_uuid` empty for both objects.
- key evidence: `sacct` reported job `1029724` canceled at `00:03:33`. Partial JSON was `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_fingerclear_obs3_rate10_train2_7195_b87_5af8191_20260615T0753Z/verified_indices.json`.

Analysis:
- Negative diagnostic. Requiring projected exact-contact left/right finger bodies to clear the table over-pruned object0 to zero quality resets. The user requirement is about the reset pose being collision-free; the environment resets to pregrasp, not to the exact contact pose. The hard table gate should apply to projected pregrasp finger bodies and contact/reference height, leaving exact-contact clearance as a diagnostic or softer post-rollout signal.

Next:
- Patch the hard table gate to require pregrasp finger clearance only, rerun local checks, deploy a new commit, and regenerate the verified cache.

## 2026-06-15T07:58:00Z - Narrow hard table gate to pregrasp reset pose

Goal:
- Keep the hard no-table-collision invariant focused on the pose actually written at reset.

Hypothesis:
- The exact-contact finger body clearance check is stricter than the real reset safety requirement and rejects valid top-side pregrasp resets, especially for object0. A pregrasp-only hard gate should restore quality reset coverage while still preventing table-colliding resets.

Change:
- `table_ok` in multi-object candidate selection now requires projected pregrasp left/right finger clearance and contact/reference height above the table floor.
- The selected exact-contact finger clearance remains computed and returned for diagnostics, but no longer participates in the hard topdown/table mask.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `5af8191fbdaecddbbf278272acc38f176d6e71e8`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog
- remote_commit/status: pending

Command / Job:
- command: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
- command: `git diff --check`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: n/a

Result:
- status: passed
- metrics/artifacts: local Python and diff checks passed.
- key evidence: pregrasp-only table mask compiles.

Analysis:
- This preserves the user’s reset-safety rule without requiring the later exact-contact target to already be table-clear under a static projection.

Next:
- Commit, deploy the updated source to l401, and rerun verified-cache collection.
