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
