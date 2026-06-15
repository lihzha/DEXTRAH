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
- Committed `e71616ce0b9d9462276e99151178a4d019ebae11`, deployed it to l401 via Git bundle, and relaunched verified-cache collection.

## 2026-06-15T07:59:09Z - Relaunch verified cache with pregrasp-only hard gate

Goal:
- Regenerate the robust verified cache after correcting the hard table gate.

Hypothesis:
- Removing exact-contact finger clearance from hard candidate selection will restore object0 quality resets while preserving reset-time table safety through pregrasp finger clearance.

Change:
- Remote worktree updated to `e71616ce0b9d9462276e99151178a4d019ebae11`.
- Relaunched the same bounded collector settings as job `1029724`.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `5af8191fbdaecddbbf278272acc38f176d6e71e8`
- implementation_commit: `e71616ce0b9d9462276e99151178a4d019ebae11`
- push/pull: deployed to l401 by Git bundle, remote worktree clean at implementation commit.
- changed_files: worklog only since `e71616ce0b9d9462276e99151178a4d019ebae11`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` at `e71616ce0b9d9462276e99151178a4d019ebae11`, clean.

Command / Job:
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=e71616ce0b9d9462276e99151178a4d019ebae11,RUN_NAME=verified_pregraspclear_obs3_rate10_train2_7195_b87_e71616c_20260615T0759Z,... cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`
- job_id: `1029727`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_pregraspclear_obs3_rate10_train2_7195_b87_e71616c_20260615T0759Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029727.out`
- artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_pregraspclear_obs3_rate10_train2_7195_b87_e71616c_20260615T0759Z/verified_indices.json`

Result:
- status: running
- metrics/artifacts: pending
- key evidence: pending

Analysis:
- Key early check: object0 quality resets should no longer be zero. If pass counts remain weak, inspect selected indices and validation videos before using a cache for training.

Next:
- Monitor job `1029727`, inspect partial/final `verified_indices.json`, then validate any exported indices with close-camera videos.

## 2026-06-15T08:17:55Z - Object1 index 1075 validation and long-lift ablations

Goal:
- Determine whether the remaining object1 failure is still reset geometry/table collision, or whether the bounded validation rollout is too short/weak to reproduce the collector's previous successful lifts.

Hypothesis:
- The selected reset for object1 index `1075` is top-down and table-safe. The short training-style validation failed because `GRASP_STEPS=72` and lift action `0.30` under-lifted a grasp that the earlier collector scored with a longer lift phase.

Evidence:
- Job `1029727` was canceled after partial collector stats showed object0 quality and pass observations were restored, but object1 still had zero passes under the bounded collector settings.
- Job `1029728` validated object1 index `1075` with training-style close/lift. It wrote frames and metrics, then failed only the `grasp_contact` scenario.
- Local artifact: `cluster_results/l401/franka_multi_grasp_video_obj1_1075_trainwarm_e71616c_20260615T0807Z/grasp_contact.mp4`
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_grasp_video_obj1_1075_trainwarm_e71616c_20260615T0807Z/grasp_contact.mp4`
- Metrics: selected sample index `1075`, selected env `7`, approach z `0.9987`, selected lift max `0.0712m`, threshold `0.12m`, object XY delta max `0.0198m`, max finger/object distance min `0.0553m`, finger table clearance min `0.1067m`, done count `0`.
- Visual inspection: no table collision or below-object approach. The object is contacted and slightly lifted but does not reach the success height in the short clip.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- implementation_commit: `e71616ce0b9d9462276e99151178a4d019ebae11`
- remote_commit/status: remote worktree remains at `e71616ce0b9d9462276e99151178a4d019ebae11`.

Command / Jobs:
- command: two `sbatch` validations with object1 manifest, stable pose cache, robust cache index `1075`, topdown min pregrasp z `0.70`, IK `128/.035/.25/.09/.75`, pregrasp offset `0.08`, score cap `4 envs / 300s`.
- job_id: `1029730`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_grasp_video_obj1_1075_longlift_trainclose_e71616c_20260615T0817Z`
- job_id: `1029731`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_grasp_video_obj1_1075_longlift_collectclose_e71616c_20260615T0817Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029730.out`, `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029731.out`

Result:
- status: running
- metrics/artifacts: pending
- key evidence: pending

Next:
- Monitor both jobs. If long-lift train-close passes, update validation/collector defaults to avoid rejecting valid top-down grasps with too-short warmstarts. If both fail, inspect contact/lift frames and regenerate object1 verified indices with stronger contact-quality selection.

## 2026-06-15T08:31:11Z - Diagnose and fix overlarge multi-object pregrasp offset

Goal:
- Resolve why object1 index `1075` stopped passing despite previous evidence that it can lift when sampled top-down.

Diagnosis:
- Jobs `1029730` and `1029731` both failed even with long lift timing. They plateaued at `0.067-0.069m` lift with no table collision, no done events, and top-down approach z `0.9987`.
- Comparing against older passing metrics showed the decisive difference: passing object1 `1075` runs used `grasp_pregrasp_offset=0.03`; failed current runs used `0.08`.
- With `0.08`, the reset target leaves the hand about `0.08m` above the exact contact pose (`exact_ee_to_ee_dist=0.08`), and the scripted approach/close never gets the fingers close enough to the object (`max_finger_to_object_min ~= 0.048-0.051m`).
- With `0.03`, the same index reaches close contact (`max_finger_to_object_min=0.0385m`) and lifts above the `0.12m` threshold.

Change:
- Set `DextrahFrankaMultiObjectGraspEnvCfg.grasp_prior_pregrasp_offset` back to the known-good Franka cube default `0.03`.
- Keep the hard reset safety requirement in the candidate selection gates: top-down approach and projected pregrasp finger/table clearance. The smaller offset is not a table-collision workaround; it is the reset distance that lets the post-reset warmstart reach contact.

Validation:
- Local checks passed:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
  - `git diff --check`
- Job `1029733` validated object1 index `1075` on the current code with `GRASP_PREGRASP_OFFSET=0.03`.
- Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_grasp_video_obj1_1075_preoffset03_e71616c_20260615T0825Z`
- Logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029733.out`
- Result: `COMPLETED`, `00:05:30`, exit `0:0`, video validation passed.
- Metrics: selected sample `1075`, approach z `0.9987`, selected lift max `0.1322m`, threshold `0.12m`, finger-table clearance min `0.0872m`, bottom clearance min `0.1003m`, object XY delta max `0.0233m`, done count `0`, candidate table/valid counts `128/128`.
- Local video: `cluster_results/l401/franka_multi_grasp_video_obj1_1075_preoffset03_e71616c_20260615T0825Z/grasp_contact.mp4`
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_grasp_video_obj1_1075_preoffset03_e71616c_20260615T0825Z/grasp_contact.mp4`

Next:
- Commit and deploy the config patch, regenerate a current verified-grasp cache using the corrected default, then validate object0/object1 videos from that cache before launching RL training.

## 2026-06-15T08:33:37Z - Regenerate verified cache after pregrasp-offset fix

Goal:
- Build a current verified-grasp cache from source commit `45662dad6957100102393082c7fddce36fcce72b`, rather than relying on the older `4828698` cache.

Change:
- Committed `45662dad6957100102393082c7fddce36fcce72b` (`Use cube pregrasp offset for multiobject priors`).
- Deployed to l401 via Git bundle and fast-forwarded remote worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`.
- Relaunched the collector with the corrected default `GRASP_PREGRASP_OFFSET=0.03`, topdown min pregrasp z `0.70`, stable-pose cache, and full yaw randomization.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- implementation_commit: `45662dad6957100102393082c7fddce36fcce72b`
- push/pull: deployed to l401 by Git bundle, remote worktree fast-forwarded to implementation commit.
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, this worklog

Command / Job:
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=45662dad6957100102393082c7fddce36fcce72b,RUN_NAME=verified_preoffset03_obs3_rate10_train2_7195_b87_45662da_20260615T0833Z,... cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`
- job_id: `1029734`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_obs3_rate10_train2_7195_b87_45662da_20260615T0833Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029734.out`
- artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_obs3_rate10_train2_7195_b87_45662da_20260615T0833Z/verified_indices.json`

Result:
- status: running
- metrics/artifacts: pending
- key evidence: pending

Next:
- Monitor `verified_indices.json`. Require at least one robust index per object, then validate object0/object1 videos from this current cache.

## 2026-06-15T08:36:42Z - Relaunch collector with collector-close default

Goal:
- Avoid generating a current cache with validation-style close-width behavior that under-samples object0.

Result of job `1029734` before cancellation:
- Canceled at `00:02:41` after diagnostic partial stats.
- Object1 was fixed: index `1075` already exported with `23/52` pass observations, pass rate `0.4423`, lift `0.1553m`.
- Object0 index `354` had `9/184` pass observations, pass rate `0.0489`, lift `0.1974m`, but was not exported because the threshold was `0.10`.
- This run used `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=True`, which differs from the collector default and previous robust-cache collection.

Change:
- Relaunched the collector with `GRASP_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`, while keeping the corrected pregrasp offset `0.03` and the same topdown/table safety gates.

Command / Job:
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=45662dad6957100102393082c7fddce36fcce72b,RUN_NAME=verified_preoffset03_collectclose_obs3_rate10_train2_7195_b87_45662da_20260615T0836Z,... cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`
- job_id: `1029735`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate10_train2_7195_b87_45662da_20260615T0836Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029735.out`
- artifacts: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate10_train2_7195_b87_45662da_20260615T0836Z/verified_indices.json`

Result:
- status: running
- metrics/artifacts: pending

Next:
- Monitor job `1029735`; expect object0 index `354` and object1 index `1075` to pass rate-gated export if the default collector close behavior matches earlier robust stats.

## 2026-06-15T09:02:33Z - Current cache and per-object video validation pass

Goal:
- Produce a usable current-code verified-grasp cache and validate both selected objects visually before launching RL training.

Result of job `1029735`:
- Status: completed wrapper with a failed strict export condition because object0 ended just below the original `0.10` pass-rate threshold.
- Strict run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate10_train2_7195_b87_45662da_20260615T0836Z`
- Strict JSON: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate10_train2_7195_b87_45662da_20260615T0836Z/verified_indices.json`
- Object0 `7195ed3346a445448308febe833c180a`, index `354`: `180/1885` pass observations, pass rate `0.09549071618037135`, max lift `0.5092969536781311m`, pregrasp approach z `0.748419463634491`, done count `0`.
- Object1 `b87a65917e494aa4b306aeb6ee961182`, index `1075`: `152/385` pass observations, pass rate `0.3948051948051948`, max lift `0.1998199224472046m`, pregrasp approach z `0.9986640214920044`, done count `0`.

Derived cache:
- Path: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate09_train2_7195_b87_45662da_20260615T0852Z/verified_indices.json`
- Derivation: lowered `min_pass_rate_per_index` from `0.10` to `0.09` only for the final export, preserving `min_pass_observations_per_index=3` and `max_indices_per_object=16`.
- Rationale: object0 index `354` had strong absolute evidence (`180` pass observations and `0.509m` lift) but missed the strict rate cutoff by `0.00451`. Object1 index `1075` remained comfortably above either threshold.
- Exported indices: object0 `[354]`, object1 `[1075]`.

Per-object video validation:
- Job `1029736` object0 validation: `COMPLETED`, exit `0:0`.
- Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_grasp_video_currentcache_obj0_354_collectclose_45662da_20260615T0853Z`
- Local artifact: `cluster_results/l401/franka_multi_grasp_video_currentcache_obj0_354_collectclose_45662da_20260615T0853Z/grasp_contact.mp4`
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_grasp_video_currentcache_obj0_354_collectclose_45662da_20260615T0853Z/grasp_contact.mp4`
- Metrics: passed, selected lift max `0.48980289697647095m`, object XY delta max `0.055749937891960144`, done count `0`. Visual sample showed top-side approach and no table-colliding reset.
- Job `1029737` object1 validation: `COMPLETED`, exit `0:0`.
- Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_grasp_video_currentcache_obj1_1075_collectclose_45662da_20260615T0853Z`
- Local artifact: `cluster_results/l401/franka_multi_grasp_video_currentcache_obj1_1075_collectclose_45662da_20260615T0853Z/grasp_contact.mp4`
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_grasp_video_currentcache_obj1_1075_collectclose_45662da_20260615T0853Z/grasp_contact.mp4`
- Metrics: passed, selected lift max `0.1321670413017273m`, object XY delta max `0.023270754143595695`, done count `0`. Visual sample showed the previously failing object1 grasp now lifts after the `0.03m` pregrasp-offset fix.

Analysis:
- The reset safety bug and the training-warmstart reachability bug appear separable. The final reset selector rejects below-object/table-colliding reset candidates via top-down pregrasp direction and projected pregrasp finger-table clearance, while the config reset distance now matches the known-good Franka cube behavior.
- The derived cache is intentionally minimal: one validated index per object, generated and validated on source commit `45662dad6957100102393082c7fddce36fcce72b`.

Next:
- Commit this provenance update, deploy the current source/worklog to l401, then launch Franka multi-object RL training with the derived verified cache and current grasp-prior reset/action-warmstart settings.

## 2026-06-15T09:09:01Z - Launch current-cache RL smoke continuation

Goal:
- Smoke-test RL training on the repaired source and current verified cache before launching a longer continuation.

Change:
- Committed provenance update `34a696a283015cfbec6134cf1dd78f613c62ea06`.
- Deployed the local branch to l401 by Git bundle and updated `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` to `34a696a283015cfbec6134cf1dd78f613c62ea06`.
- Initial `sbatch` submit failed because l401 exposes `batch` with 4 GPUs/node, not the wrapper's directive partition `batch_singlenode`.
- Resubmitted with explicit `--partition=batch --gpus-per-node=4`, `NPROC_PER_NODE=4`, `NUM_ENVS=1024`, and `MINIBATCH_SIZE=16384`.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- implementation_commit: `34a696a283015cfbec6134cf1dd78f613c62ea06`
- remote_commit/status: remote worktree at `34a696a283015cfbec6134cf1dd78f613c62ea06`, clean.

Command / Job:
- command: `sbatch --partition=batch --gpus-per-node=4 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=34a696a283015cfbec6134cf1dd78f613c62ea06,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_currentcache_smoke66_34a696a_20260615T0907Z,MAX_ITERATIONS=66,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_ikrelax61_resume60_3c4e22e_20260615T0501Z_r3/nn/last_dextrah_franka_multi_object_grasp_ep_61_rew__3078.7478_.pth,AUTO_RESUME=False,SELF_RELAUNCH=False,DEXTRAH_RLGAMES_JSONL_METRICS=True,USE_CUDA_GRAPH=False,NUM_ENVS=1024,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1029740`
- run_name: `franka_multi_state_teacher_7195_b87_currentcache_smoke66_34a696a_20260615T0907Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_currentcache_smoke66_34a696a_20260615T0907Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029740.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_currentcache_smoke66_34a696a_20260615T0907Z/metrics/direct_info_rank_0.jsonl`
- checkpoint source: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_ikrelax61_resume60_3c4e22e_20260615T0501Z_r3/nn/last_dextrah_franka_multi_object_grasp_ep_61_rew__3078.7478_.pth`
- verified cache: `/results/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate09_train2_7195_b87_45662da_20260615T0852Z/verified_indices.json`
- stable pose cache: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`

Key settings:
- `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.70`
- `GRASP_PRIOR_RESET_ATTEMPTS=8`
- `GRASP_PRIOR_RESET_CANDIDATE_COUNT=128`
- `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.35`
- `GRASP_PRIOR_PREGRASP_OFFSET=0.03`
- `GRASP_PRIOR_ACTION_WARMSTART_APPROACH_STEPS=8`
- `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_STEPS=32`
- `GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=240`
- `GRASP_PRIOR_ACTION_WARMSTART_CLOSE_WIDTH=0.004`
- `GRASP_PRIOR_ACTION_WARMSTART_USE_PRIOR_CLOSE_WIDTH=False`
- `GRASP_PRIOR_ACTION_WARMSTART_LIFT_ACTION_Z=0.45`
- `GRASP_PRIOR_ACTION_WARMSTART_LIFT_MAX_FINGER_CENTER_DIST=0.12`
- `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=0.008`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=40.0`
- `OBJECT_STATIC_FRICTION=4.0`
- `OBJECT_DYNAMIC_FRICTION=3.5`
- `OBJECT_SOLVER_POSITION_ITERATIONS=24`
- `OBJECT_SOLVER_VELOCITY_ITERATIONS=8`

Result:
- status: pending
- metrics/artifacts: pending; first queue check showed `PENDING (Resources)`.

Next:
- Monitor queue and startup log. Once metrics are emitted, compare reset quality, table-clearance, success, lift, and warmstart-lift metrics against the prior epoch-61 baseline before launching a longer continuation.

## 2026-06-15T09:24:53Z - Restore multi-object reward distances to object center

Goal:
- Diagnose why the current-cache RL smokes had table-safe reset priors but regressed from the epoch-61 baseline after resume.

Result of current-cache RL smokes:
- Job `1029740` (`franka_multi_state_teacher_7195_b87_currentcache_smoke66_34a696a_20260615T0907Z`) completed in `00:06:23`, exit `0:0`.
- Job `1029742` (`franka_multi_state_teacher_7195_b87_currentcache_priorclose_smoke66_34a696a_20260615T0918Z`) completed in `00:06:30`, exit `0:0`.
- Both runs preserved safe reset diagnostics: candidate valid/table/topdown counts stayed `128/128/128`, pregrasp tip-table clearance stayed around `0.0736m`, projected exact tip-table clearance stayed around `0.0475m`, and reset success stayed around `0.63-0.66`.
- Fixed-close smoke epoch 66: `cube_success_rate=0.0107`, `cube_has_lifted_rate=0.4932`, `cube_lift_height=0.0143m`, `cube_grasp_prior_quality_success_rate=0.6191`.
- Prior-close smoke epoch 66: `cube_success_rate=0.0078`, `cube_has_lifted_rate=0.5195`, `cube_lift_height=0.0123m`, `cube_grasp_prior_quality_success_rate=0.6436`.
- Baseline checkpoint row at epoch 61 from `franka_multi_state_teacher_7195_b87_nobelow_ikrelax61_resume60_3c4e22e_20260615T0501Z_r3`: `cube_success_rate=0.1104`, `cube_has_lifted_rate=0.3398`, `cube_lift_height=0.0532m`, `cube_grasp_prior_quality_success_rate=0.6318`.

Analysis:
- The poor current-cache smokes are not explained by the original table-collision suspicion: the current reset gates are selecting top-side grasps with positive finger/table clearance.
- The suspicious behavioral signature is high small-lift frequency but very low object-center lift height and success.
- Code inspection found a multi-object-only divergence from the known-good Franka cube task: `_compute_intermediate_values()` replaced object-center distance inputs with the grasp contact reference point whenever a grasp-prior reset succeeded. This changes reward shaping and success hand-distance gating away from the cube baseline, even though the desired differences from cube are only object stable-pose initialization and valid grasp-pose sampling.

Change:
- Patched `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py` so per-step `ee_to_cube_dist`, `finger_center_to_cube_dist`, left/right finger distances, reward inputs, and success hand-distance gating are again measured to the object center.
- Kept `grasp_prior_current_contact_reference_pos` updates for reset diagnostics and warmstart readiness; the validated contact-reference grasp selection path is unchanged.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `30db93ba332982bdf0ae7bbe3d1243ed44053d42`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog

Validation:
- Local checks passed:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
  - `git diff --check`

Next:
- Commit and deploy this patch, then launch a bounded RL continuation from the epoch-61 checkpoint with the current verified cache. Require safe reset metrics to remain intact and compare success/lift recovery against the `1029740`/`1029742` smokes before launching a longer run.

## 2026-06-15T09:29:00Z - Launch center-distance RL smoke

Goal:
- Test whether restoring multi-object reward/success distances to the object center recovers the epoch-61 policy behavior while retaining the current safe grasp-prior reset sampling.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- implementation_commit: `3ff7a1bfcbd8b980378283edc939ea9bb0b28650`
- push/pull: pushed branch to GitHub; l401 GitHub fetch is blocked by SSH key access, so deployed to the agent-owned remote worktree with a Git bundle from `34a696a` through `3ff7a1b`.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` at `3ff7a1bfcbd8b980378283edc939ea9bb0b28650`, detached and clean.

Command / Job:
- command: `sbatch --partition=batch --gpus-per-node=4 --job-name=dextrah_franka_multi_center --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=3ff7a1bfcbd8b980378283edc939ea9bb0b28650,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_centerdist_priorclose_smoke66_3ff7a1b_20260615T0928Z,MAX_ITERATIONS=66,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_ikrelax61_resume60_3c4e22e_20260615T0501Z_r3/nn/last_dextrah_franka_multi_object_grasp_ep_61_rew__3078.7478_.pth,AUTO_RESUME=False,SELF_RELAUNCH=False,DEXTRAH_RLGAMES_JSONL_METRICS=True,USE_CUDA_GRAPH=False,NUM_ENVS=1024,MINIBATCH_SIZE=16384,CENTRAL_VALUE_MINIBATCH_SIZE=16384,SAVE_FREQUENCY=1,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1029752`
- run_name: `franka_multi_state_teacher_7195_b87_centerdist_priorclose_smoke66_3ff7a1b_20260615T0928Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_centerdist_priorclose_smoke66_3ff7a1b_20260615T0928Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029752.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_centerdist_priorclose_smoke66_3ff7a1b_20260615T0928Z/metrics/direct_info_rank_0.jsonl`
- checkpoint source: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_nobelow_ikrelax61_resume60_3c4e22e_20260615T0501Z_r3/nn/last_dextrah_franka_multi_object_grasp_ep_61_rew__3078.7478_.pth`
- verified cache: `/results/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate09_train2_7195_b87_45662da_20260615T0852Z/verified_indices.json`

Key settings:
- Same safe reset settings as previous current-cache smokes: topdown min pregrasp z `0.70`, attempts `8`, candidate count `128`, max center-distance frac `0.35`, projected table clearance gates, IK `128/.035/.25/.09/.75`, pregrasp offset `0.03`.
- Baseline-compatible action guidance: `GRASP_PRIOR_ACTION_WARMSTART_USE_PRIOR_CLOSE_WIDTH=True`, min close width `0.002`, close width `0.004`, approach/close/lift steps `8/32/240`, lift action z `0.45`, action-prior reward weight `40`.

Result:
- status: submitted
- metrics/artifacts: pending

Next:
- Monitor job `1029752`; compare success/lift, reset safety counters, and object-specific metrics against `1029740`, `1029742`, and the epoch-61 baseline.

## 2026-06-15T10:18:00Z - Restore training-capable top-side defaults

Goal:
- Resolve the remaining RL collapse after the reward-distance patch and choose a grasp-prior cache/settings combination that is table-safe and trains from the epoch-61 Franka multi-object checkpoint.

Result of center-distance/current-cache smoke:
- Job `1029752` completed in `00:06:38`, exit `0:0`.
- Run: `franka_multi_state_teacher_7195_b87_centerdist_priorclose_smoke66_3ff7a1b_20260615T0928Z`
- Source/cache/settings: commit `3ff7a1b`, current derived cache `/results/assets/verified_grasp_indices/verified_preoffset03_collectclose_obs3_rate09_train2_7195_b87_45662da_20260615T0852Z/verified_indices.json`, `GRASP_PRIOR_PREGRASP_OFFSET=0.03`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.70`.
- Safety counters stayed good: candidate valid/table/topdown `128/128/128`, pregrasp tip-table clearance about `0.0738m`, projected exact tip-table clearance about `0.0476m`, reset success about `0.61`.
- RL behavior still collapsed: epoch 66 `cube_success_rate=0.0117`, `cube_has_lifted_rate=0.4805`, `cube_lift_height=0.0152m`, `cube_xy_error=0.1251m`. This rules out the object-center reward patch as the only missing fix.

Old-cache validation under current source:
- Jobs `1029753` and `1029754` both completed, exit `0:0`.
- Cache: `/results/assets/verified_grasp_indices/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/verified_indices.json`; settings: `GRASP_PRIOR_PREGRASP_OFFSET=0.08`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`, topdown required, projected table gates active.
- Object0 run `franka_multi_grasp_video_oldcache_obj0_354_pre08_3ff7a1b_20260615T0940Z`: passed; local MP4 `cluster_results/l401/franka_multi_grasp_video_oldcache_obj0_354_pre08_3ff7a1b_20260615T0940Z/grasp_contact.mp4`; `1280x720`, `161` frames, `5.37s`; grasp-contact lift reached `0.9353m` object-center z, XY delta max `0.0599m`, finger-table clearance min `0.0923m`, object bottom clearance min `0.0228m`, done count `0`.
- Object1 run `franka_multi_grasp_video_oldcache_obj1_pre08_3ff7a1b_20260615T0940Z`: passed; local MP4 `cluster_results/l401/franka_multi_grasp_video_oldcache_obj1_pre08_3ff7a1b_20260615T0940Z/grasp_contact.mp4`; `1280x720`, `161` frames, `5.37s`; grasp-contact lift reached `0.9783m` object-center z, XY delta max `0.0406m`, finger-table clearance min `0.0673m`, object bottom clearance min `0.0621m`, done count `0`.

Old-cache RL smoke:
- Job `1029755` completed in `00:07:04`, exit `0:0`.
- Run: `franka_multi_state_teacher_7195_b87_oldcache_pre08_smoke66_3ff7a1b_20260615T0945Z`
- Epoch 62 recovered above baseline: success `0.1455`, lifted `0.2676`, lift height `0.0690m`, XY error `0.0341m`, reset quality `0.6865`, reset success `0.7031`, candidate valid/table/topdown `106.63/128/106.63`, pregrasp tip-table clearance `0.0755m`, projected exact tip-table clearance `0.0257m`.
- Epoch 66 remained near the known-good baseline: success `0.1123`, lifted `0.2686`, lift height `0.0554m`, XY error `0.0432m`, reset quality `0.6045`, reset success `0.6250`, active warmstart success `0.2555`.

Analysis:
- The current derived cache was table-safe but over-constrained by `min_pregrasp_z=0.70` and `pregrasp_offset=0.03`; it selected a near-vertical object1 grasp that produced high lift attempts but poor object-center progress and large XY drift.
- The old cache/settings still satisfy the user's no-below/table-safety requirement: positive-z approach, positive projected finger-table clearance, positive grasp-contact bottom clearance, and no reset done events.
- `0.45` is a top-side threshold, not a below-object approach. It preserves useful side/top grasps while the contact-height and finger/table clearance gates reject underside/table-colliding candidates.

Change:
- Updated Franka multi-object defaults to the settings that validated and trained: `grasp_prior_pregrasp_offset=0.08`, `grasp_prior_reset_min_pregrasp_z=0.45`.
- Updated multi-object collector/validator defaults to match.
- Updated teacher/eval wrapper defaults so Franka multi-object runs no longer override the config back to `0.70`; cube-specific imitation defaults are unchanged.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `3ff7a1bfcbd8b980378283edc939ea9bb0b28650`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `cluster/sbatch_train_teacher_8gpu.sh`, `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, `cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`, `cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh`, this worklog.

Next:
- Run local syntax/wrapper checks, commit/deploy this default correction, then launch a longer continuation from `1029755` epoch 66 using the old verified cache and the same table-safe grasp-prior/action-prior settings.

## 2026-06-15T09:54:00Z - Launch old-cache continuation to 120

Goal:
- Continue the now-training Franka multi-object run beyond the 5-epoch smoke and check whether the old verified cache plus table-safe top-side defaults can sustain or improve success.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- implementation_commit: `703f554eecc70bccd74786709df5583f763bb0d9`
- push/pull: pushed branch to GitHub; deployed to l401 agent worktree with Git bundle because remote GitHub fetch is blocked by SSH auth.
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` at `703f554eecc70bccd74786709df5583f763bb0d9`, detached and clean.
- validation: `python3 -m py_compile` on edited Python files, `bash -n` on edited wrappers, and `git diff --check` all passed before launch.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=4 --job-name=dextrah_franka_multi_oldcache --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=703f554eecc70bccd74786709df5583f763bb0d9,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z,MAX_ITERATIONS=120,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_smoke66_3ff7a1b_20260615T0945Z/nn/last_dextrah_franka_multi_object_grasp_ep_66_rew__5617.8804_.pth,AUTO_RESUME=False,SELF_RELAUNCH=False,DEXTRAH_RLGAMES_JSONL_METRICS=True,USE_CUDA_GRAPH=False,NUM_ENVS=1024,MINIBATCH_SIZE=16384,CENTRAL_VALUE_MINIBATCH_SIZE=16384,SAVE_FREQUENCY=5,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1029759`
- run_name: `franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029759.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z/metrics/direct_info_rank_0.jsonl`
- checkpoint source: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_smoke66_3ff7a1b_20260615T0945Z/nn/last_dextrah_franka_multi_object_grasp_ep_66_rew__5617.8804_.pth`
- verified cache: `/results/assets/verified_grasp_indices/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/verified_indices.json`

Key settings:
- `GRASP_PRIOR_PREGRASP_OFFSET=0.08`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`, `GRASP_PRIOR_RESET_ATTEMPTS=8`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=128`, `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.35`.
- Table/contact safety gates: `GRASP_PRIOR_RESET_REQUIRE_TOPDOWN=True`, `GRASP_PRIOR_RESET_MIN_CONTACT_HEIGHT_ABOVE_CENTER=0.0`, `GRASP_PRIOR_RESET_QUALITY_MAX_FINGER_CENTER_DIST=0.08`, `GRASP_PRIOR_RESET_QUALITY_MAX_TIP_CENTER_DIST=0.08`, `GRASP_PRIOR_RESET_QUALITY_MAX_TIP_MAX_DIST=0.10`.
- Action prior/warmstart: approach/close/lift `8/32/240`, prior close width enabled with min close width `0.002`, lift action z `0.45`, require current lift-ready, action-prior reward weight `40`.

Result:
- status: submitted
- metrics/artifacts: pending

Next:
- Monitor job `1029759`; inspect startup logs, JSONL reward/success/reset-safety metrics, final checkpoints, and decide whether to evaluate the final checkpoint or relaunch from a better intermediate checkpoint.

## 2026-06-15T10:05:00Z - Stop drifting continuation and prepare low-LR run

Goal:
- Avoid wasting cluster time after the long continuation started to move away from the successful prior-guided behavior.

Result:
- Job `1029759` was manually canceled at elapsed `00:09:59`.
- It produced checkpoints at epoch 70 and 75:
  - `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z/nn/last_dextrah_franka_multi_object_grasp_ep_70_rew_2914.3018.pth`
  - `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_cont120_703f554_20260615T0954Z/nn/last_dextrah_franka_multi_object_grasp_ep_75_rew_5165.937.pth`
- Best observed metrics were before the first saved checkpoint: epoch 67 success `0.1572`, lift height `0.0687m`, XY error `0.0340m`, reset quality `0.6787`, reset success `0.6836`.
- Best saved checkpoint row was epoch 70: success `0.1279`, lift height `0.0601m`, XY error `0.0417m`, reset quality `0.6523`, reset success `0.6621`.
- By epoch 75 the policy regressed: success `0.0225`, lift height `0.0616m`, XY error `0.0727m`, active warmstart success `0.1015`.

Analysis:
- The reset sampler did not regress into unsafe table/below approaches: candidate table count stayed `128`, topdown/valid stayed about `106.85`, pregrasp tip-table clearance increased from `0.0758m` to `0.0792m`, and projected exact tip clearance stayed positive.
- The behavioral drift appears optimizer-driven after resume: action-prior active rate and active warmstart success fall sharply after epoch 70 while XY error rises.
- Next test should preserve the same safe prior/cache but reduce learning rate and checkpoint every epoch so the good early continuation point is recoverable.

Next:
- Launch a short continuation from the same epoch-66 checkpoint to iteration 80 with `LEARNING_RATE=5e-5`, `CENTRAL_VALUE_LEARNING_RATE=2.5e-5`, and `SAVE_FREQUENCY=1`.

## 2026-06-15T10:05:00Z - Launch low-LR old-cache continuation

Goal:
- Test whether reducing optimizer step size preserves the successful prior-guided behavior while continuing training from the same epoch-66 checkpoint.

Command / Job:
- command: `sbatch --parsable --partition=batch --gpus-per-node=4 --job-name=dextrah_franka_multi_lowlr --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=703f554eecc70bccd74786709df5583f763bb0d9,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_703f554_20260615T1005Z,MAX_ITERATIONS=80,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_smoke66_3ff7a1b_20260615T0945Z/nn/last_dextrah_franka_multi_object_grasp_ep_66_rew__5617.8804_.pth,LEARNING_RATE=0.00005,CENTRAL_VALUE_LEARNING_RATE=0.000025,SAVE_FREQUENCY=1,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1029760`
- run_name: `franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_703f554_20260615T1005Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_703f554_20260615T1005Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029760.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_703f554_20260615T1005Z/metrics/direct_info_rank_0.jsonl`

Result:
- status: submitted
- metrics/artifacts: pending

Next:
- Monitor job `1029760`; if success remains above baseline through epoch 80, evaluate the best checkpoint. If it still drifts, try reducing or disabling the action-prior reward while keeping the warmstart/reset priors.

## 2026-06-15T10:21:00Z - Resubmit low-LR continuation as short backfill job

Goal:
- Get the low-LR diagnostic onto l401 sooner by using an accurate short wall-time request, and avoid a bad checkpoint-path submission.

Result:
- Job `1029760` was canceled before start because its default `03:50:00` wall time kept slipping in the backfill queue.
- Job `1029761` was canceled before start because I caught a typo in the checkpoint run directory (`3c4e22e` instead of `3ff7a1b`).
- Submitted corrected short job `1029762` with `--time=00:45:00`.

Command / Job:
- command: `sbatch --parsable --time=00:45:00 --partition=batch --gpus-per-node=4 --job-name=dextrah_franka_multi_lowlr --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=703f554eecc70bccd74786709df5583f763bb0d9,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z,MAX_ITERATIONS=80,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_smoke66_3ff7a1b_20260615T0945Z/nn/last_dextrah_franka_multi_object_grasp_ep_66_rew__5617.8804_.pth,LEARNING_RATE=0.00005,CENTRAL_VALUE_LEARNING_RATE=0.000025,SAVE_FREQUENCY=1,... cluster/sbatch_train_teacher_8gpu.sh`
- job_id: `1029762`
- run_name: `franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029762.out`
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/metrics/direct_info_rank_0.jsonl`

Next:
- Monitor `1029762`; reject it if it reproduces the post-epoch-70 success collapse, otherwise evaluate the best saved checkpoint.

## 2026-06-15T10:43:00Z - Low-LR checkpoint and first fresh eval

Goal:
- Select a recoverable checkpoint from the low-LR run and test it from fresh reset conditions.

Result of low-LR run:
- Job `1029762` was canceled at elapsed `00:11:18` after reproducing the same post-epoch-71 success collapse.
- Per-epoch checkpoints were saved through epoch 75.
- Best saved checkpoint was epoch 67:
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth`
  - training row: success `0.1406`, lifted `0.2578`, lift height `0.0684m`, XY error `0.0369m`, reset success `0.6807`, projected exact tip-table clearance `0.0261m`.
- Later rows drifted similarly to the higher-LR run, so the issue is not simply optimizer step size. The early high rows are likely affected by resumed runtime/warmstart state; fresh eval is required.

Fresh eval:
- Job `1029771` completed in `00:01:35`, exit `0:0`.
- Run: `franka_multi_eval_oldcache_lowlr_ep67_metrics_703f554_20260615T1036Z`
- Checkpoint: low-LR epoch 67.
- Metrics: `success_ever_rate=0.3125`, `success_rate_max=0.25`, `success_rate_final=0.0`, `completed_episode_success_rate=0.6538`, `completed_episode_count=26`.
- Caveat: wrapper inspection showed this eval did not forward `OBJECT_STATIC_FRICTION=4.0`, `OBJECT_DYNAMIC_FRICTION=3.5`, or solver iteration overrides, so it is useful as a policy sanity check but not final parity evidence.

Change:
- Patched `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` to accept, echo, export, and forward the same object physics overrides used by training.

Version Control:
- implementation_commit: pending
- changed_files: `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`, this worklog.

Next:
- Commit/deploy the eval wrapper fix after job `1029771` releases the remote source, then rerun metrics-only eval with object physics parity.

## 2026-06-15T10:58:00Z - Physics-parity eval and reward-only continuation launch

Goal:
- Validate the selected low-LR epoch-67 checkpoint under the same object physics overrides used for training, inspect the rendered rollout, and launch the next diagnostic because first-attempt success is nonzero but not yet final-quality.

Version Control:
- implementation_commit: `5e387a5116d122922c384fd5342b0f8ddb6a1087`
- change: `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` now forwards multi-object object physics overrides to `eval_rollout.py`.

Physics-parity metrics eval:
- Job `1029772` completed in `00:01:19`, exit `0:0`.
- Run: `franka_multi_eval_oldcache_lowlr_ep67_phys_5e387a5_20260615T1046Z`
- Checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth`
- Confirmed wrapper/runtime overrides: `env.object_static_friction=4.0`, `env.object_dynamic_friction=3.5`, `env.object_solver_position_iterations=24`, `env.object_solver_velocity_iterations=8`.
- Metrics: `eval_success_rate=0.34375`, `success_ever_rate=0.34375`, `success_rate_max=0.28125`, `completed_episode_success_rate=0.96296`, `completed_episode_count=27`, `done_after_success_rate=0.25`.
- Summary: 22/64 envs reached success at least once. Completed episodes were high quality, but many first attempts never completed, so this is a useful checkpoint rather than a finished policy.
- Local artifacts: `cluster_results/l401/franka_multi_eval_oldcache_lowlr_ep67_phys_5e387a5_20260615T1046Z/{metrics.json,trace.csv,trace.jsonl}`.

Physics-parity video eval:
- Job `1029773` completed in `00:01:15`, exit `0:0`.
- Run: `franka_multi_eval_oldcache_lowlr_ep67_video_phys_5e387a5_20260615T1050Z`
- Metrics: `eval_success_rate=0.25`, `success_ever_rate=0.5`, `completed_episode_success_rate=0.5`, `completed_episode_count=4`.
- Video: `cluster_results/l401/franka_multi_eval_oldcache_lowlr_ep67_video_phys_5e387a5_20260615T1050Z/videos/franka-multi-oldcache-lowlr-ep67-phys-step-0.mp4`
- ffprobe: `1280x720`, `239` frames, `3.983s`, `60 fps`.
- Viewer URL from `viz-open`: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_oldcache_lowlr_ep67_video_phys_5e387a5_20260615T1050Z/videos/franka-multi-oldcache-lowlr-ep67-phys-step-0.mp4`
- Visual inspection: rollout renders correctly after the recorder's initial black frame; the gripper approaches from above and there is no visible table-penetrating reset.

Analysis:
- The reset/prior path is no longer the primary blocker: old-cache top-side validated resets are table-safe, and physics-parity eval produces real lifts/successes.
- Training/eval still shows the policy is not fully owning the grasp. In the warmstart run, epoch 67 had `cube_success_rate=0.1406`, but `cube_action_prior_delta_abs=0.8114`; applied warmstart actions were still far from raw policy actions (`cube_applied_action_z=-0.6142`, `cube_policy_action_z=0.2268`).
- This suggests the long action warmstart is acting as a crutch: the environment executes scripted actions while PPO is rewarded on raw policy actions. The next diagnostic disables action override and keeps only the action-prior reward, forcing the policy to execute its own approach/close/lift actions.

Reward-only continuation:
- Job `1029774` submitted and currently pending on resources.
- Run: `franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_w80_5e387a5_20260615T1115Z`
- Command: `sbatch --parsable --time=00:45:00 --partition=batch --gpus-per-node=4 --job-name=dextrah_franka_prioronly --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z,CODE_COMMIT=5e387a5116d122922c384fd5342b0f8ddb6a1087,NPROC_PER_NODE=4,TASK=Dextrah-Franka-Multi-Object-Grasp,FULL_EXPERIMENT_NAME=franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_w80_5e387a5_20260615T1115Z,MAX_ITERATIONS=90,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth,... cluster/sbatch_train_teacher_8gpu.sh`
- Key overrides: `GRASP_PRIOR_ACTION_WARMSTART_ENABLED=False`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=80.0`, old verified index cache, `pregrasp_offset=0.08`, `min_pregrasp_z=0.45`, object friction `4.0/3.5`, solver iterations `24/8`.
- Expected artifacts:
  - logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029774.out`
  - run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_w80_5e387a5_20260615T1115Z`
  - metrics: `.../metrics/direct_info_rank_0.jsonl`

Next:
- Monitor job `1029774`. If raw policy success/lift improves with lower `cube_action_prior_delta_abs`, evaluate the best checkpoint with physics parity. If it fails to learn lift, run the same reward-only continuation with `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY=False` so the prior provides a fixed schedule teacher signal.

## 2026-06-15T11:08:00Z - Reward-only ready-gated diagnostic failed; launch fixed-schedule ablation

Ready-gated reward-only result:
- Job `1029774` was manually canceled at elapsed `00:09:46` after the failure mode was clear.
- Best training row was epoch 68 with `cube_success_rate=0.1621`, `has_lifted=0.3545`, `lift_height=0.0683m`, `xy_error=0.0421m`, and `cube_action_prior_delta_abs=0.9076`.
- By epoch 76, success had collapsed to `0.0020`, XY error rose to `0.1113m`, and `cube_action_prior_active_rate` fell to `0.0273`.
- Diagnosis: with `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY=True`, the prior almost stops producing lift-phase teacher reward once the raw policy misses the close/finger-distance gate. The policy keeps closing/lifting poorly and drifts the object away.

Fixed-schedule reward-only ablation:
- Job `1029776` submitted and currently pending.
- Run: `franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_sched_w80_5e387a5_20260615T1108Z`
- Change from `1029774`: `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY=False`; all other reset/prior/physics/checkpoint settings are the same.
- Expected signal: `cube_action_prior_lift_rate` should remain scheduled after the close phase instead of disappearing, and policy-controlled success should not collapse if the issue was only the lift-ready teacher gate.

Next:
- Monitor `1029776`. If fixed-schedule reward-only improves raw policy success, evaluate the best checkpoint. If it still drifts, inspect whether the policy action frame/sign convention is mismatched for the z/lift action or whether the inherited single-cube success/XY shaping is overconstraining long objects.

## 2026-06-15T11:18:00Z - Fixed-schedule prior was still gated; launch ungated schedule

Fixed-schedule result:
- Job `1029776` was manually canceled at elapsed `00:09:10`.
- Best row was epoch 68 with `cube_success_rate=0.1602`, `has_lifted=0.3740`, `lift_height=0.0764m`, `xy_error=0.0471m`.
- Later rows collapsed similarly; by epoch 76, `cube_success_rate=0.0029`, `xy_error=0.1212m`.
- Diagnosis: setting `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY=False` was insufficient because `GRASP_PRIOR_ACTION_WARMSTART_LIFT_MAX_FINGER_CENTER_DIST=0.12` and `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=0.008` still gated lift. The teacher stayed mostly in exact-close/approach, with `cube_action_prior_lift_rate` near zero and negative mean teacher z.

Ungated fixed-schedule reward-only ablation:
- Job `1029777` submitted.
- Run: `franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_schednogate_w80_5e387a5_20260615T1118Z`
- Changes from `1029776`: `GRASP_PRIOR_ACTION_WARMSTART_LIFT_MAX_FINGER_CENTER_DIST=0.0`, `GRASP_PRIOR_ACTION_WARMSTART_LIFT_CLOSED_WIDTH_MARGIN=-1.0`, `GRASP_PRIOR_ACTION_WARMSTART_REQUIRE_CURRENT_LIFT_READY=False`.
- Expected signal: after the 8-step approach and 32-step close phase, `cube_action_prior_lift_rate` should remain substantial and `cube_action_prior_teacher_z` should become positive enough to train the raw policy's lift action.

Next:
- Monitor `1029777`; keep/evaluate only if policy-controlled success or lift improves without the same XY drift collapse.

## 2026-06-15T11:42:00Z - Ungated prior still collapsed; patch action-prior timing

Ungated fixed-schedule result:
- Job `1029777` was manually canceled at elapsed `00:11:29` after reproducing collapse under the old code.
- Best row was epoch 68 with `cube_success_rate=0.16699`, `has_lifted=0.34766`, lift height `0.06642m`, XY error `0.04499m`, and `cube_action_prior_delta_abs=0.85575`.
- The ungated schedule did produce lift teacher signal: epoch 69 had `cube_action_prior_lift_rate=0.47461` and `cube_action_prior_teacher_z=0.15400`; epoch 71 had `cube_action_prior_lift_rate=0.49609` and `cube_action_prior_teacher_z=0.21250`.
- Despite that, train success dropped to `0.03809` at epoch 69, `0.00586` at epoch 71, and stayed near zero for several rows while XY error rose toward `0.10m`.

Diagnosis:
- `_compute_grasp_prior_action_prior_reward()` recomputed `_grasp_prior_reference_actions()` inside `_get_rewards`, after the policy action had already been applied and the simulator had advanced.
- That compares the action taken from the previous pre-step state against a teacher action generated for the next state. The action-prior deltas were therefore partly measuring time misalignment, not only policy error.

Change:
- Patched `DextrahFrankaCubeGraspEnv` to cache the grasp-prior teacher action in `_pre_physics_step()` before `super()._pre_physics_step(applied_actions)`.
- `_compute_grasp_prior_action_prior_reward()` now consumes the cached pre-step teacher action and compares it to the matching policy action; it no longer recomputes the teacher from post-step state.
- Reset now clears action-prior diagnostics for reset envs to avoid stale active/phase state.

Version Control:
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `git diff --check`

Next:
- Commit and deploy this patch, then relaunch the same ungated reward-only diagnostic from the low-LR epoch-67 checkpoint. The expected first signal is lower/more coherent `cube_action_prior_delta_abs`; the required outcome is that policy-controlled success/lift no longer collapses from XY drift.

## 2026-06-15T11:39:00Z - Relaunch cached action-prior diagnostic

Version Control:
- implementation_commit: `14c986b1772bf9838e6b2cfbc336599abca0003b`
- branch_push: pushed to `origin/codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- remote_commit/status: l401 worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` detached at `14c986b1772bf9838e6b2cfbc336599abca0003b`, clean.
- deployment: GitHub fetch failed on l401 due missing SSH key, so the branch was deployed with a Git bundle copied to `/tmp/dextrah-multiobject-grasp-prior-14c986b.bundle`.

Command / Job:
- job_id: `1029808`
- run_name: `franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_cached_schednogate_w80_14c986b_20260615T1139Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_cached_schednogate_w80_14c986b_20260615T1139Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029808.out`
- metrics: `.../metrics/direct_info_rank_0.jsonl`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth`
- key overrides: same as failed ungated prior-only job `1029777`, but with cached pre-step action-prior reward code at `14c986b`. Warmstart action override remains disabled, action-prior reward enabled with weight `80`, fixed ungated approach/close/lift schedule `8/32/240`, old verified indices, old top-side pregrasp settings, object friction `4.0/3.5`, solver iterations `24/8`, `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, LR `5e-5`, CV LR `2.5e-5`.

Next:
- Monitor `1029808` startup, then inspect early epoch metrics. Keep the run only if cached action-prior metrics improve and success/lift avoid the old drift-collapse pattern.

## 2026-06-15T11:49:00Z - Cached action-prior diagnostic failed similarly

Result:
- Job `1029808` was manually canceled at elapsed `00:08:39` after the failure mode was clear.
- `sacct`: job `CANCELLED by 158351`, batch step `FAILED` due signal after manual cancel.
- Metrics rows covered epochs 68-73.
- Best row was epoch 68: `cube_success_rate=0.15625`, `has_lifted=0.34375`, lift height `0.06758m`, XY error `0.03974m`, `cube_action_prior_delta_abs=0.84558`.
- Collapse reproduced:
  - epoch 69: success `0.03418`, XY `0.06064m`, lift-rate teacher `0.46094`, teacher z `0.13613`
  - epoch 70: success `0.01172`, XY `0.07971m`, lift-rate teacher `0.49121`, teacher z `0.20054`
  - epoch 73: success `0.00977`, XY `0.09358m`, lift-rate teacher `0.07715`

Analysis:
- Caching the teacher at pre-step state fixed a real mismatch, but it did not solve the collapse. The run still learns/executes strong positive z and close actions while losing XY stability.
- The next likely bug is in the scripted reference itself rather than timing: the lift-phase teacher may be encouraging lateral motion or object drag because it reuses exact-contact tracking components while overriding only z.

Next:
- Audit `_grasp_prior_exact_tracking_action()` and lift-phase reference construction. If the teacher keeps pulling the gripper laterally toward a stale reset contact pose during lift, patch lift to hold/limit lateral motion instead of continuing exact-contact XY tracking.

## 2026-06-15T11:50:00Z - Relaunch with full-episode lift prior

Hypothesis:
- The prior-only runs collapse partly because the teacher schedule ends at `8 + 32 + 240 = 280` steps while the episode can run for about 600 steps. Once a poor policy has lifted the object at all, `prelift_drag` termination no longer resets failed large-XY episodes, so they can spend the rest of the episode with no active teacher and no success.

Command / Job:
- job_id: `1029809`
- run_name: `franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_cached_schedfull_w80_14c986b_20260615T1150Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_prioronly90_cached_schedfull_w80_14c986b_20260615T1150Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029809.out`
- metrics: `.../metrics/direct_info_rank_0.jsonl`
- change from `1029808`: `GRASP_PRIOR_ACTION_WARMSTART_LIFT_STEPS=600`; all source/reset/cache/physics/LR/action-prior settings unchanged.

Expected signal:
- `cube_action_prior_active_rate` should remain high after the old collapse window instead of dropping below `0.1`.
- If the active-rate hypothesis is sufficient, success/lift should stop degrading as XY error approaches the success tolerance.

## 2026-06-15T12:16:00Z - Full-episode prior completed; prepare BC handoff

Result:
- Job `1029809` completed normally at elapsed `00:24:18`.
- Metrics rows covered epochs 68-90.
- Full-episode lift prior kept teacher signal active, but did not solve success:
  - epoch 83: success `0.00781`, has-lifted `0.45313`, lift height `0.12212m`, XY `0.14661m`, active prior `0.66895`
  - epoch 87: success `0.03516`, has-lifted `0.42578`, lift height `0.09762m`, XY `0.09998m`, active prior `0.72266`
  - epoch 90: success `0.01953`, has-lifted `0.49414`, lift height `0.11571m`, XY `0.14419m`, active prior `0.70801`
- Best row remained epoch 68: success `0.18066`, has-lifted `0.36914`, lift height `0.07388m`, XY `0.04362m`.

Analysis:
- The old active-rate collapse was real, but it was not the main blocker. Keeping the action prior active through the full episode mostly taught strong lift/close behavior while still allowing large XY drift and poor grasp ownership.
- Reward-only PPO is not providing a reliable supervised handoff from the scripted grasp prior. The existing BC diagnostic supports `compute_grasp_prior_reference_actions()` and imports the multi-object task, so the next practical route is supervised action imitation on the old-cache grasp-prior reference, followed by PPO fine-tuning/eval.
- The BC wrapper did not forward multi-object object physics overrides, which would make BC collection inconsistent with training/eval.

Change:
- Patched `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh` to accept, export, echo, and forward object physics overrides for multi-object BC collection: density, friction, contact/rest offsets, solver iterations, damping, and max depenetration velocity.

Version Control:
- implementation_commit: pending
- changed_files: `cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`, this worklog.

Next:
- Commit/deploy the BC wrapper parity fix.
- Launch a 1-GPU BC run on `Dextrah-Franka-Multi-Object-Grasp` from the low-LR epoch-67 checkpoint using the old verified cache and physics-parity settings.
- Evaluate the BC checkpoint with the same physics-parity eval wrapper; if BC can imitate the prior rollouts, continue PPO fine-tuning from the BC checkpoint.

## 2026-06-15T12:17:00Z - Launch multi-object grasp-prior BC

Version Control:
- implementation_commit: `0f235d3b3693f5237e9b74f2a7696f6ac7f1c39c`
- remote_commit/status: l401 worktree detached at `0f235d3b3693f5237e9b74f2a7696f6ac7f1c39c`, clean.

Command / Job:
- job_id: `1029811`
- run_name: `franka_multi_bc_oldcache_refdelta_0f235d3_20260615T1217Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_oldcache_refdelta_0f235d3_20260615T1217Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029811.out`
- input_checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth`
- output_checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_0f235d3_20260615T1217Z/nn/bc_reference_action_imitation.pth`
- dataset: `/results/bc/franka_multi_bc_oldcache_refdelta_0f235d3_20260615T1217Z/reference_action_dataset.pt`
- settings: `NUM_ENVS=128`, `COLLECTION_STEPS=640`, `TRAIN_STEPS=2000`, `BATCH_SIZE=8192`, `COLLECTION_ACTION_SOURCE=reference_delta`, `LABEL_ACTION_SOURCE=reference_delta`, old verified indices, old stable-pose cache, object physics `4.0/3.5`, solver iterations `24/8`, reset prior `pregrasp_offset=0.08`, old top-side/quality settings, reference schedule `8/32/600`.

Expected signal:
- Collection should show nonzero teacher success/lift under reference actions.
- BC validation loss should drop enough to produce an actor that tracks the prior better than the PPO reward-only continuations. If the checkpoint is produced, run physics-parity eval next.

## 2026-06-15T12:19:39Z - BC launch failed on stale library-dir override

Result:
- Job `1029811` failed before container execution with exit `2:0`.
- Log evidence: `Missing grasp prior library dir: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/franka_multi_object_grasp_priors`.

Analysis:
- The multi-object manifest already contains per-object `grasp_prior_path` entries, which are the paths used successfully by the validated reset/prior jobs and PPO/eval runs.
- Passing `GRASP_PRIOR_LIBRARY_DIR=/results/assets/franka_multi_object_grasp_priors` forced the wrapper to validate a nonexistent stale cache directory and blocked startup before the environment could use the manifest-owned prior paths.

Next:
- Relaunch the same BC configuration from commit `0f235d3b3693f5237e9b74f2a7696f6ac7f1c39c`, but omit `GRASP_PRIOR_LIBRARY_DIR`.
- Keep old verified indices and stable-pose cache unchanged because both objects were already independently validated as safe top-side grasps with positive table clearance.

## 2026-06-15T12:20:00Z - Relaunch BC without stale library dir

Command / Job:
- job_id: `1029812`
- run_name: `franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029812.out`
- source: l401 worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` detached at `0f235d3b3693f5237e9b74f2a7696f6ac7f1c39c`
- scheduler: submitted on l401 with explicit `--partition=batch` because the wrapper's default A100-style partition list is invalid for L40S.
- change from `1029811`: `GRASP_PRIOR_LIBRARY_DIR` left unset; all object manifest, old verified indices, stable-pose, physics, reference schedule, and BC hyperparameters unchanged.

Expected artifacts:
- `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/reference_action_dataset.pt`
- `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation.pth`

Next:
- Monitor startup, collection, loss curve, and produced artifacts. If the checkpoint is produced, run a physics-parity multi-object eval before using it for PPO fine-tuning.

## 2026-06-15T12:24:00Z - Launch BC checkpoint physics-parity eval

BC Result:
- Job `1029812` completed with exit `0:0` in `00:02:51`.
- Dataset: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/reference_action_dataset.pt`, 35 MB, 81,920 samples.
- Checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation.pth`, 64 MB.
- Held-out error improved from `val_l2=1.8792` at step 0 to `val_l2=0.07336` at step 2000; held-out x/y/z abs errors were `0.01357/0.01049/0.01150`.

Analysis:
- The supervised fit is strong enough to warrant rollout eval, but it is not an acceptance criterion by itself because the reference-action dataset is on-policy under the scripted reference and may not cover policy drift.

Command / Job:
- job_id: `1029813`
- run_name: `franka_multi_eval_bc_oldcache_refdelta_phys_0f235d3_20260615T1224Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_bc_oldcache_refdelta_phys_0f235d3_20260615T1224Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029813.out`
- checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation.pth`
- settings: metrics-only, `NUM_ENVS=64`, `NUM_STEPS=360`, deterministic policy, old manifest/stable-pose/verified-cache settings, object physics `4.0/3.5` and solver iterations `24/8`, `GRASP_PRIOR_LIBRARY_DIR` unset.

Next:
- Inspect rollout metrics and trace. If policy rollout is good, run a video eval before PPO fine-tuning; if it fails, inspect action drift and reset/reference mismatch.

## 2026-06-15T12:28:00Z - Launch BC checkpoint video eval

Metrics Result:
- Job `1029813` completed with exit `0:0` in `00:01:42`.
- `eval_success_rate=0.359375`, `success_ever_rate=0.390625`, `success_rate_max=0.28125`.
- Completed episodes: `50`, with `completed_episode_success_rate=0.68` and `completed_episode_success_hold_rate=0.68`.
- Done reasons: no `prelift_drag`, no `finger_table_penetration`, no `cube_out`; `done_after_success_rate=0.359375`.
- Trace pattern: success rises by step 39, then drops mostly because successful envs terminate/reset; later horizon episodes are much weaker and final success is zero.

Analysis:
- The BC actor is a real grasping policy under the physics-parity reset settings, but the post-reset/horizon performance is weaker than the initial episode distribution. Before PPO fine-tuning, inspect video for whether failures are due to grasp closure timing, lateral drift, object identity/pose changes, or reset artifacts.

Command / Job:
- job_id: `1029814`
- run_name: `franka_multi_eval_bc_oldcache_refdelta_video_0f235d3_20260615T1228Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_bc_oldcache_refdelta_video_0f235d3_20260615T1228Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029814.out`
- settings: `NUM_ENVS=4`, `NUM_STEPS=180`, video enabled, deterministic policy, same checkpoint and physics-parity old-cache settings as `1029813`.

Next:
- Fetch/open video and inspect visible behavior. Use this to choose PPO fine-tune settings rather than treating BC loss alone as success.

## 2026-06-15T12:34:00Z - Launch shorter-pregrasp reset ablation

Video Result:
- Job `1029814` completed with exit `0:0` in `00:01:14`.
- Video artifact: `/results/evals/franka_multi_eval_bc_oldcache_refdelta_video_0f235d3_20260615T1228Z/videos/franka-multi-bc-oldcache-refdelta-step-0.mp4`.
- Local viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_bc_oldcache_refdelta_video_0f235d3_20260615T1228Z/videos/franka-multi-bc-oldcache-refdelta-step-0.mp4`
- Video metadata: `1280x720`, `179` frames, `2.98s`.
- Sampled env-0 failure shows a miss/post-reset failure rather than a finger-table collision. Logs showed no finger-table penetration.

Analysis:
- The stronger blocker is reset quality: metrics-only eval had `grasp_prior_reset_quality_success` around `0.59` at initial reset and decaying after resets, with positive table clearance. Failed resets have larger IK position/orientation errors and fall back to default arm pose, so PPO would be learning around a mixed valid/default reset distribution.
- Hypothesis for ablation: `GRASP_PRIOR_PREGRASP_OFFSET=0.08` makes the top-side pregrasp IK target too hard for the Franka on some object yaw/spawn combinations. The logged exact-tip table clearance remains positive, so shortening the pregrasp to `0.04` may improve reset IK while still avoiding table collision.

Command / Job:
- job_id: `1029815`
- run_name: `franka_multi_eval_bc_oldcache_refdelta_pre04_phys_0f235d3_20260615T1234Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_bc_oldcache_refdelta_pre04_phys_0f235d3_20260615T1234Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029815.out`
- change from `1029813`: only `GRASP_PRIOR_PREGRASP_OFFSET=0.04`; same BC checkpoint, old verified cache, stable-pose cache, object physics, and eval settings.

Next:
- Compare reset quality, eval success, table clearance, and trace against `1029813`. If shorter pregrasp improves reset quality, regenerate BC/fine-tune using this reset distribution; otherwise patch the reset IK/retry path.

## 2026-06-15T12:38:00Z - Patch retry loop to resample object pose

Result:
- Shorter-pregrasp ablation job `1029815` completed with exit `0:0`.
- Compared to `pre08`, `pre04` improved `eval_success_rate` from `0.359375` to `0.40625` and initial reset quality from `0.59375` to `0.6875`, but mean/late reset quality remained poor (`~0.46` mean, `0.375` final).
- Table clearance stayed positive, so the main issue is not below-table collision in these runs; it is failed grasp-prior reset IK/quality, especially after post-success resets.

Hypothesis:
- The multi-object retry loop resampled grasp candidates but kept the same object pose. For objects with only one or a few verified candidate indices, an unreachable object yaw/spawn could repeatedly fail and then fall back to the default arm pose. Retrying must resample the object reset pose too.

Change:
- Added `_sample_and_write_object_reset_state()` to factor the multi-object object-spawn/stable-pose write path.
- On failed grasp-prior reset quality, retry now resamples/writes a fresh object pose for those envs, updates `cube_initial_pos` and `cube_goal_pos`, then applies the next grasp-prior IK target.
- Single-cube reset code is untouched.

Version Control:
- implementation_commit: `0898bb2a0fcad0f000e37f51baa2bcbc32ccf452`
- validation: `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`; `git diff --check`
- branch_push: pushed to `origin/codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- remote_commit/status: l401 worktree detached at `0898bb2a0fcad0f000e37f51baa2bcbc32ccf452`, clean.
- deployment: GitHub fetch unavailable on l401, so deployed with `/tmp/dextrah-reset-retry-0898bb2.bundle`.

Command / Job:
- job_id: `1029816`
- run_name: `franka_multi_eval_bc_oldcache_refdelta_retrypose_phys_0898bb2_20260615T1238Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_bc_oldcache_refdelta_retrypose_phys_0898bb2_20260615T1238Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029816.out`
- checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation.pth`
- settings: same as `1029813`, with source commit `0898bb2` and `GRASP_PRIOR_PREGRASP_OFFSET=0.08`.

Next:
- Compare reset quality and rollout metrics against `1029813`. If quality improves materially, regenerate BC/fine-tune at the patched commit; if not, inspect IK target selection/reachability next.

## 2026-06-15T12:46:00Z - Patched reset-retry eval verifies reset-quality fix

Result:
- Job `1029816` completed with exit `0:0` in `00:01:15`.
- Metrics improved sharply versus the same BC checkpoint on the old reset code:
  - old reset eval `1029813`: `eval_success_rate=0.359375`, `success_ever_rate=0.390625`, `success_rate_max=0.28125`.
  - patched reset eval `1029816`: `eval_success_rate=0.65625`, `success_ever_rate=0.71875`, `success_rate_max=0.484375`, `success_rate_mean=0.09765625`.
- Completed episodes: `87`, with `completed_episode_success_rate=0.7241379310344828`, `terminal_success_rate=0.7126436781609196`, and `done_after_success_rate=0.625`.
- Done reasons: no `cube_out`, no `finger_table_penetration`, and no `prelift_drag`; `44` `success_done`, `33` `done_after_success_unclassified`, `10` `unclassified`.

Reset Diagnostics:
- `grasp_prior_reset_success=1.0` and `grasp_prior_reset_quality_success=1.0` for all `360` trace rows.
- Exact projected finger-tip table clearance stayed positive: min `0.016721786931157112`, mean `0.017134606206996573`.
- Pregrasp tip table clearance stayed positive: min `0.06654615700244904`, mean `0.06695897804780139`.
- Projected exact finger-center distance remained bounded: min `0.007992328144609928`, mean `0.03000422019718422`, max `0.03589753806591034`.

Analysis:
- The main multi-object Franka bug was the reset retry loop: it retried grasp candidates while keeping an object pose that could be unreachable for the small verified-candidate set, then fell back to the default arm pose. Resampling the object reset pose during failed reset-quality retries fixes the mixed reset distribution.
- The current BC policy was trained before this patch and still reaches `0.71875` success-ever under the corrected reset distribution. The next step should retrain BC data collection at commit `0898bb2`, then evaluate that checkpoint before PPO fine-tuning.

Artifacts:
- local metrics/trace: `cluster_results/l401/franka_multi_eval_bc_oldcache_refdelta_retrypose_phys_0898bb2_20260615T1238Z/`

Next:
- Launch BC reference-action imitation at source commit `0898bb2` using the patched reset distribution and no stale `GRASP_PRIOR_LIBRARY_DIR`.

## 2026-06-15T12:43:00Z - Launch patched-reset BC training

Command / Job:
- job_id: `1029819`
- run_name: `franka_multi_bc_oldcache_refdelta_retrypose_0898bb2_20260615T1243Z`
- source_commit: `0898bb2a0fcad0f000e37f51baa2bcbc32ccf452`
- expected_run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_oldcache_refdelta_retrypose_0898bb2_20260615T1243Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_1029819.out`

Settings:
- Same old-cache manifest/stable-pose/verified-index inputs as the successful evals, but source code includes the reset retry object-pose resampling patch.
- `GRASP_PRIOR_LIBRARY_DIR` explicitly unset to avoid stale or missing cached prior directories.
- Collection/labels use `reference_delta`; `NUM_ENVS=128`, `COLLECTION_STEPS=640`, `TRAIN_STEPS=2000`, `BATCH_SIZE=8192`, `LEARNING_RATE=0.0001`.
- Seed policy checkpoint remains the low-LR PPO checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_state_teacher_7195_b87_oldcache_pre08_lowlr80_short_703f554_20260615T1021Z/nn/last_dextrah_franka_multi_object_grasp_ep_67_rew_2916.8196.pth`.

Next:
- Monitor job `1029819`; fetch and inspect the BC report/checkpoint, then run patched-reset eval with the new BC policy.

## 2026-06-15T12:47:00Z - Patched-reset BC completes; launch matched eval

BC Result:
- Job `1029819` completed with exit `0:0` in `00:02:09`.
- Artifacts fetched locally to `cluster_results/l401/franka_multi_bc_oldcache_refdelta_retrypose_0898bb2_20260615T1243Z/`.
- Dataset: `reference_action_dataset.pt`, `36379213` bytes.
- Checkpoint: `nn/bc_reference_action_imitation.pth`, `80184666` bytes.
- Selected BC step: `2000`, `selected_score=0.12192357331514359`.
- Held-out metrics: `val_l2=0.12192357331514359`, `val_mse=0.008468596264719963`, `val_x_abs=0.018328633159399033`, `val_y_abs=0.016300488263368607`, `val_z_abs=0.016632050275802612`, `val_gripper_abs=0.06531829386949539`, `val_close_abs=0.05451121926307678`.

Analysis:
- The corrected-reset BC imitation loss is worse than the earlier old-reset BC (`val_l2=0.07336`), but the dataset distribution is no longer polluted by default-arm fallback resets. Closed-loop eval is needed before deciding whether to use this checkpoint or the old BC checkpoint under corrected resets.

Command / Job:
- job_id: `1029820`
- run_name: `franka_multi_eval_bc_retrypose_refdelta_phys_0898bb2_20260615T1247Z`
- source_commit: `0898bb2a0fcad0f000e37f51baa2bcbc32ccf452`
- checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_retrypose_0898bb2_20260615T1243Z/nn/bc_reference_action_imitation.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_bc_retrypose_refdelta_phys_0898bb2_20260615T1247Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029820.out`
- settings: same 64-env, 360-step patched-reset physics eval as `1029816`; only checkpoint changed.

Next:
- Inspect eval metrics/trace. If the new BC is worse than the old BC under patched resets, keep the old BC checkpoint for PPO fine-tuning and investigate better BC labels/settings separately.

## 2026-06-15T12:53:00Z - Select old BC under fixed reset and launch PPO smoke

Matched Eval Result:
- Job `1029820` completed with exit `0:0` in `00:01:30`.
- Run `franka_multi_eval_bc_retrypose_refdelta_phys_0898bb2_20260615T1247Z` evaluated the new patched-reset BC checkpoint.
- New BC under fixed reset: `eval_success_rate=0.625`, `success_ever_rate=0.6875`, `success_rate_max=0.53125`, `success_rate_mean=0.11141493055555556`, `completed_episode_success_rate=0.7549019607843137`.
- Old BC under fixed reset (`1029816`): `eval_success_rate=0.65625`, `success_ever_rate=0.71875`, `success_rate_max=0.484375`, `success_rate_mean=0.09765625`, `completed_episode_success_rate=0.7241379310344828`.
- Both had `grasp_prior_reset_success=1.0`, `grasp_prior_reset_quality_success=1.0`, no `finger_table_penetration`, no `prelift_drag`, and no `cube_out`.

Decision:
- Use the old BC checkpoint for PPO initialization because it has better first-attempt and success-ever performance under the corrected reset code. The new BC is useful evidence that corrected reset collection is viable, but it is not a clear policy upgrade.

Sanitization:
- Created policy-init checkpoint inside the Isaac container:
  - input: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation.pth`
  - output: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation_policy_init.pth`
  - summary: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation_policy_init.sanitize_summary.json`
- Sanitizer removed `dextrah_runtime_state`, `env_state`, and `optimizer`, reset epoch/frame (`67`, `65536000`) to zero, and marked `dextrah_checkpoint_semantics=policy_initialization`.

Command / Job:
- job_id: `1029822`
- run_name: `franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_0898bb2_20260615T1253Z`
- source_commit: `0898bb2a0fcad0f000e37f51baa2bcbc32ccf452`
- checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation_policy_init.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_0898bb2_20260615T1253Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029822.out`

Settings:
- `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, `MAX_ITERATIONS=20`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=2`, `LEARNING_RATE=2e-5`, `CENTRAL_VALUE_LEARNING_RATE=1e-5`, `SAVE_FREQUENCY=1`.
- Corrected reset-only grasp prior: `GRASP_PRIOR_RESET_ENABLED=True`, old verified cache, `GRASP_PRIOR_PREGRASP_OFFSET=0.08`, `GRASP_PRIOR_RESET_ATTEMPTS=8`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=128`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`, IK tolerances `0.09/0.75`.
- Object physics matches successful eval: static/dynamic friction `4.0/3.5`, solver iterations `24/8`.
- Action warmstart override disabled and action-prior reward disabled. Previous reward-only PPO guidance was unstable; this smoke tests whether PPO can improve from the BC actor using task reward plus corrected grasp-prior resets.

Next:
- Monitor `1029822`; inspect JSONL metrics, reset quality, success/lift/XY drift, checkpoints, then evaluate the best checkpoint against the fixed-reset physics eval.

## 2026-06-15T12:59:00Z - PPO policy-init smoke exposes optimizer restore bug

Result:
- Job `1029822` failed with exit `1:0` at elapsed `00:03:05`, before any PPO epoch metrics/checkpoints.
- Startup was otherwise healthy: all four ranks loaded the sanitized checkpoint and constructed the corrected-reset multi-object environment.
- Failure:
  - `DextrahResumableAlgoObserver` detected the policy-init checkpoint and set `set_epoch=False`.
  - The sanitizer intentionally stripped `optimizer`.
  - RL-Games' `set_full_state_weights()` still expected `weights['optimizer']`, causing `KeyError: 'optimizer'` on all ranks.

Fix:
- Patched `dextrah_lab/rl_games/rl_games_utils.py` so policy-initialization checkpoints inject the freshly-created optimizer state before calling RL-Games' original loader.
- Normal resume checkpoints are unchanged: saved optimizer/runtime state still load as before.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/rl_games_utils.py`
- `git diff --check`

Next:
- Commit/deploy the restore fix, then relaunch the same PPO smoke from the sanitized BC policy-init checkpoint.

## 2026-06-15T12:58:00Z - Relaunch PPO smoke after policy-init restore fix

Version Control:
- implementation_commit: `9ae97c0d36b3baea3acd45977b9b30cd1c8f078f`
- commit message: `Allow optimizer-free policy initialization checkpoints`
- pushed branch: `origin/codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- remote deploy: l401 worktree updated via `/tmp/dextrah-policy-init-9ae97c0.bundle`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z` detached at `9ae97c0d36b3baea3acd45977b9b30cd1c8f078f`, clean.

Command / Job:
- job_id: `1029823`
- run_name: `franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_9ae97c0_20260615T1258Z`
- checkpoint: `/results/bc/franka_multi_bc_oldcache_refdelta_nolibdir_0f235d3_20260615T1220Z/nn/bc_reference_action_imitation_policy_init.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_9ae97c0_20260615T1258Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029823.out`
- settings: identical to failed job `1029822`, except source commit is `9ae97c0`.

Next:
- Confirm the optimizer-free policy-init checkpoint now loads and reaches epoch metrics. If stable, evaluate the best checkpoint from this smoke.

## 2026-06-15T13:10:00Z - PPO BC-init smoke completes; launch epoch-20 eval

PPO Result:
- Job `1029823` completed with exit `0:0` in `00:10:12`.
- The restore fix worked: all ranks loaded the optimizer-free policy-init checkpoint and trained normally.
- Best training success was epoch `20`:
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_9ae97c0_20260615T1258Z/nn/last_dextrah_franka_multi_object_grasp_ep_20_rew_4873.9688.pth`
  - `cube_success_rate=0.30078125`
  - `cube_has_lifted_rate=0.5859375`
  - `cube_lift_height=0.0806846171617508`
  - `cube_xy_error=0.05585388094186783`
  - `cube_grasp_prior_quality_success_rate=0.9990234375`
  - `cube_grasp_prior_reset_success_rate=0.9990234375`
  - `cube_finger_table_clearance_violation=0.0`
- Training had an early dip through epoch 9, then recovered through epoch 20. Reset safety stayed intact throughout.

Command / Job:
- job_id: `1029825`
- run_name: `franka_multi_eval_ppo_bcinit_ep20_retrypose_phys_9ae97c0_20260615T1310Z`
- source_commit: `9ae97c0d36b3baea3acd45977b9b30cd1c8f078f`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_9ae97c0_20260615T1258Z/nn/last_dextrah_franka_multi_object_grasp_ep_20_rew_4873.9688.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_ppo_bcinit_ep20_retrypose_phys_9ae97c0_20260615T1310Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029825.out`
- settings: same corrected-reset 64-env, 360-step physics eval used for `1029816` and `1029820`.

Next:
- Inspect eval metrics and compare PPO epoch 20 against old BC fixed-reset baseline (`eval_success_rate=0.65625`, `success_ever_rate=0.71875`).

## 2026-06-15T13:12:00Z - Epoch-20 eval shows stable held success; launch continuation to 40

Eval Result:
- Job `1029825` completed with exit `0:0` in `00:01:09`.
- Run `franka_multi_eval_ppo_bcinit_ep20_retrypose_phys_9ae97c0_20260615T1310Z`.
- PPO epoch 20:
  - `eval_success_rate=0.609375`
  - `success_ever_rate=0.671875`
  - `success_rate_max=0.5625`
  - `success_rate_final=0.515625`
  - `success_rate_mean=0.4956597222222222`
  - `success_rate_last_window_mean=0.51625`
  - reset success/quality: `1.0` throughout trace.
  - no `cube_out`, no `finger_table_penetration`, no `prelift_drag`.
- Comparison to old BC under fixed reset:
  - old BC had better first-attempt/ever success (`0.65625` / `0.71875`) but collapsed to low sustained occupancy (`success_rate_final=0.015625`, mean `0.09765625`).
  - PPO epoch 20 has lower first-attempt/ever success but much better sustained success occupancy and final held success.

Analysis:
- PPO reset-only fine-tuning changed the policy from a quick success-and-reset behavior into a more stable object-holding behavior. Since training success improved into epoch 20 and reset safety stayed clean, continue the same run family to epoch 40 before selecting the final checkpoint.

Command / Job:
- job_id: `1029827`
- run_name: `franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z`
- source_commit: `9ae97c0d36b3baea3acd45977b9b30cd1c8f078f`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_smoke20_9ae97c0_20260615T1258Z/nn/last_dextrah_franka_multi_object_grasp_ep_20_rew_4873.9688.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_1029827.out`
- settings: same as `1029823`, with `MAX_ITERATIONS=40` and checkpointed continuation from epoch 20.

Next:
- Monitor epochs 21-40. Keep the continuation only if reset safety remains clean and success/hold metrics improve or stay stable.

## 2026-06-15T13:22:00Z - Continuation to epoch 40 completes; launch epoch selection evals

PPO Result:
- Job `1029827` completed with exit `0:0` in `00:07:30`.
- Best training success was epoch `28`:
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_28_rew_2699.3933.pth`
  - `cube_success_rate=0.525390625`
  - `cube_has_lifted_rate=0.7080078125`
  - `cube_lift_height=0.09716371446847916`
  - `cube_xy_error=0.05214633047580719`
  - `cube_grasp_prior_quality_success_rate=1.0`
  - `cube_grasp_prior_reset_success_rate=1.0`
  - `cube_finger_table_clearance_violation=0.0`
- Final epoch `40` remained useful but lower by training success:
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`
  - `cube_success_rate=0.47265625`, `cube_has_lifted_rate=0.646484375`, `cube_xy_error=0.0447169691324234`.
- Reset quality remained `~1.0` and table-clearance violations stayed zero in the logged epochs.

Command / Jobs:
- job_id: `1029828`
  - run_name: `franka_multi_eval_ppo_bcinit_ep28_retrypose_phys_9ae97c0_20260615T1322Z`
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_28_rew_2699.3933.pth`
- job_id: `1029829`
  - run_name: `franka_multi_eval_ppo_bcinit_ep40_retrypose_phys_9ae97c0_20260615T1322Z`
  - checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`
- settings: same corrected-reset 64-env, 360-step physics eval used for prior comparisons.

Next:
- Fetch and compare epoch 28 vs epoch 40 evals. Then run a short video eval for the selected checkpoint.

## 2026-06-15T13:33:00Z - Select PPO epoch 40 for sustained-success video checks

Goal:
- Compare the epoch-28 and epoch-40 checkpoints from the BC-initialized reset-only PPO continuation, then render policy behavior for the selected checkpoint.

Eval Results:
- Job `1029828`, run `franka_multi_eval_ppo_bcinit_ep28_retrypose_phys_9ae97c0_20260615T1322Z`, completed with exit `0:0`.
  - `eval_success_rate=0.640625`
  - `success_ever_rate=0.703125`
  - `success_rate_max=0.546875`
  - `success_rate_final=0.484375`
  - `success_rate_mean=0.4890190972222222`
  - `success_rate_last_window_mean=0.50265625`
- Job `1029829`, run `franka_multi_eval_ppo_bcinit_ep40_retrypose_phys_9ae97c0_20260615T1322Z`, completed with exit `0:0`.
  - `eval_success_rate=0.640625`
  - `success_ever_rate=0.6875`
  - `success_rate_max=0.59375`
  - `success_rate_final=0.578125`
  - `success_rate_mean=0.5296875`
  - `success_rate_last_window_mean=0.5575`

Safety Diagnostics:
- Both evals had `grasp_prior_reset_success=1.0` and `grasp_prior_reset_quality_success=1.0` for all trace rows.
- Epoch 40 reset clearances stayed positive:
  - pregrasp tip table clearance min `0.06740409880876541m`.
  - projected exact tip table clearance min `0.017579711973667145m`.
  - reset finger table clearance min `0.041523486375808716m`.
  - runtime finger table penetration done rate `0.0`.
- No `cube_out`, `finger_table_penetration`, or `prelift_drag` done reasons appeared in either eval.

Decision:
- Select epoch 40 for visual inspection and as the current best PPO checkpoint because it matches epoch 28 on first-attempt success and is better on sustained held success, final occupancy, and max occupancy.
- Selected checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`.

Video Eval:
- Jobs `1029831` and `1029832` were canceled while pending to reduce resource shape from 4 envs / 160G to 1 env / 64G.
- Job `1029833`, run `franka_multi_eval_ppo_bcinit_ep40_video1_phys_9ae97c0_20260615T1333Z`, completed with exit `0:0`.
- Video: `cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_phys_9ae97c0_20260615T1333Z/videos/franka-multi-ppo-bcinit-ep40-phys-1env-step-0.mp4`.
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_phys_9ae97c0_20260615T1333Z/videos/franka-multi-ppo-bcinit-ep40-phys-1env-step-0.mp4`.
- Result: this single seed did not succeed (`success_ever_rate=0.0`) but reset diagnostics were clean: reset success/quality `1.0`, pregrasp tip table clearance `0.0918087363243103m`, projected exact tip table clearance `0.031935155391693115m`, reset finger table clearance `0.014400243759155273m`, runtime finger table penetration `0.0`.
- Visual inspection: the sampled failure is not a table-collision or below-object reset; the policy misses/does not lift the object from this pose.

Next:
- Jobs `1029834`, `1029835`, and `1029836` are queued for one-env visual samples with seeds `43`, `44`, and `45` to capture a representative successful rollout from the same selected epoch-40 checkpoint.

## 2026-06-15T13:50:00Z - Video seed sweep completes

Goal:
- Capture visual evidence for the selected PPO epoch-40 checkpoint while keeping the aggregate 64-env eval as the primary policy metric.

Jobs:
- `1029834`, run `franka_multi_eval_ppo_bcinit_ep40_video1_seed43_phys_9ae97c0_20260615T1338Z`, completed with exit `0:0`.
- `1029835`, run `franka_multi_eval_ppo_bcinit_ep40_video1_seed44_phys_9ae97c0_20260615T1338Z`, completed with exit `0:0`.
- `1029836`, run `franka_multi_eval_ppo_bcinit_ep40_video1_seed45_phys_9ae97c0_20260615T1338Z`, completed with exit `0:0`.

Result:
- Seed 43: `success_ever_rate=0.0`, reset quality `1.0`, reset finger table clearance `0.03770244121551514m`, runtime finger table penetration `0.0`.
- Seed 44: `eval_success_rate=1.0`, `success_ever_rate=1.0`, `success_rate_max=1.0`, `success_rate_final=0.0`, max lift `0.14014548063278198m`, reset quality `1.0`, reset finger table clearance `0.02714639902114868m`, runtime finger table penetration `0.0`.
- Seed 45: `success_ever_rate=0.0`, reset quality `1.0`, reset finger table clearance `0.0630999207496643m`, runtime finger table penetration `0.0`.

Artifacts:
- Successful visual sample: `cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_seed44_phys_9ae97c0_20260615T1338Z/videos/franka-multi-ppo-bcinit-ep40-phys-seed44-step-0.mp4`
- Viewer URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_seed44_phys_9ae97c0_20260615T1338Z/videos/franka-multi-ppo-bcinit-ep40-phys-seed44-step-0.mp4`
- Additional contrast videos:
  - `cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_phys_9ae97c0_20260615T1333Z/videos/franka-multi-ppo-bcinit-ep40-phys-1env-step-0.mp4`
  - `cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_seed43_phys_9ae97c0_20260615T1338Z/videos/franka-multi-ppo-bcinit-ep40-phys-seed43-step-0.mp4`
  - `cluster_results/l401/franka_multi_eval_ppo_bcinit_ep40_video1_seed45_phys_9ae97c0_20260615T1338Z/videos/franka-multi-ppo-bcinit-ep40-phys-seed45-step-0.mp4`

Analysis:
- The selected checkpoint is not perfect across individual random reset seeds, but the 64-env metric eval is successful and substantially better than BC on sustained held-success occupancy.
- The user-suspected reset bug is addressed: all selected-policy metric/video evals have reset quality `1.0`, positive projected/reset finger-table clearance, and no finger-table penetration, cube-out, or prelift-drag done reasons.
- The visual seed sweep did not show a below-object or table-colliding reset. Failures are policy grasp/hold failures, not reset-safety failures.

Final Selected Policy:
- Checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`
- Best 64-env eval: `franka_multi_eval_ppo_bcinit_ep40_retrypose_phys_9ae97c0_20260615T1322Z`
- Key eval metrics: `eval_success_rate=0.640625`, `success_ever_rate=0.6875`, `success_rate_max=0.59375`, `success_rate_final=0.578125`, `success_rate_mean=0.5296875`, `success_rate_last_window_mean=0.5575`.

Next:
- No active jobs remain. Commit this worklog update and report the selected checkpoint, metrics, and caveats.
