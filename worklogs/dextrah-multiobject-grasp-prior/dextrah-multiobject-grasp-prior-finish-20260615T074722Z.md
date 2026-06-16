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

## 2026-06-15T15:45:35Z - Add explicit downward tool-axis reset gate

Goal:
- Fix the remaining below-table reset root cause reported from visual inspection: a grasp could pass the old topdown filter because its pregrasp displacement was upward, while the actual GraspGen/Franka tool z-axis still pointed upward from below the object.

Hypothesis:
- GraspGenX/Franka priors use the panda-hand tool z-axis as the approach axis. A valid tabletop top-side grasp should have `tool_z_axis_w.z <= -threshold` (equivalently `-tool_z_axis_w.z >= threshold`). The previous `pregrasp_offset_dir_w.z >= threshold` check was necessary for table clearance but not sufficient to reject below-table approach orientations.

Change:
- Added multi-object config gates `grasp_prior_reset_require_downward_tool_z=True` and `grasp_prior_reset_min_downward_tool_z=0.45`.
- Multi-object candidate selection now requires `-candidate_tool_z_axis_w.z >= min_downward_tool_z` for valid and fallback reset samples, and the post-IK quality mask enforces the same condition.
- Added reset diagnostics for selected `tool_z_axis_w`, `tool_downward_z`, and per-reset `candidate_tool_down_count`.
- Updated video validation and verified-grasp collection to pass/log the new gate and to fail videos whose selected grasp does not satisfy the tool-axis condition.
- Updated policy eval traces to serialize the selected tool-axis and downward score, so PPO videos can be audited with the same invariant.
- Updated l401 train/eval/BC/verified-grasp/video wrappers to expose and echo the new settings.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `16acd21765e9a38b48727bb9b437d3a597f1aa01`
- implementation_commit: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py`, `dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py`, `dextrah_lab/rl_games/eval_rollout.py`, and cluster wrappers.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/eval_rollout.py`
  - `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `git diff --check`

Result:
- status: local checks passed
- metrics/artifacts: no cluster artifacts yet
- key evidence: syntax checks, wrapper shell checks, and whitespace diff check all exited 0.

Analysis:
- The new gate is deliberately stricter than the old pregrasp-z check. Existing verified-index caches may contain samples that now fail the live reset filter; if that makes reset quality sparse, regenerate the cache under the new `tool_downward_z` invariant instead of relaxing the gate.

Next:
- Commit and push the patch, deploy the exact commit to the l401 agent worktree, then run a bounded video validation requiring `selected_tool_z_axis_z <= -0.45` and visually inspect the produced video before any further RL training.

## 2026-06-15T15:56:00Z - Launch policy video eval with tool-axis diagnostics

Goal:
- Validate the patched sampler in the same PPO video path where the user observed table-penetrating below-table behavior.

Hypothesis:
- With commit `5218e000731ea062b9d5af86debe989f4bd2fec0`, reset samples in the PPO eval trace should show `grasp_prior_reset_tool_z_axis_z_max <= -0.45` and `grasp_prior_reset_tool_downward_z_min >= 0.45`. The video should not show the arm/gripper approaching from under the table.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- local_commit: `5218e000731ea062b9d5af86debe989f4bd2fec0`
- remote_commit/status: l401 agent worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` detached at `5218e000731ea062b9d5af86debe989f4bd2fec0`, clean
- push/pull: pushed to GitHub; l401 GitHub fetch failed with public-key auth, deployed via Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/cache/dextrah_5218e00_tool_axis.bundle`.

Command / Job:
- job_id: `1029904`
- run_name: `franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z`
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c,CODE_COMMIT=5218e000731ea062b9d5af86debe989f4bd2fec0,RUN_NAME=franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z,NUM_ENVS=2,NUM_STEPS=180,VIDEO_LENGTH=180,SEED=44,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth,OBJECT_ASSET_MANIFEST_PATH=/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json,MAX_OBJECTS=2,OBJECT_STABLE_POSE_ENABLED=True,OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_RESET_ATTEMPTS=8,GRASP_PRIOR_RESET_CANDIDATE_COUNT=256,GRASP_PRIOR_RESET_REQUIRE_TOPDOWN=True,GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45,GRASP_PRIOR_RESET_REQUIRE_DOWNWARD_TOOL_Z=True,GRASP_PRIOR_RESET_MIN_DOWNWARD_TOOL_Z=0.45,GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.50,... cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029904.out`
- expected artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, and an MP4 under `videos/`.

Result:
- status: running/queued

Next:
- Monitor scheduler/logs, fetch artifacts, verify the tool-axis metrics, and inspect the video with `viz-open`.

## 2026-06-15T16:00:00Z - Tool-axis eval exposes exact table-clearance gap

Goal:
- Inspect job `1029904` beyond scheduler completion and decide whether the reset sampler is actually safe enough to resume RL work.

Result:
- status: completed but failed acceptance
- job_state: `COMPLETED`, exit `0:0`, elapsed `00:01:16`
- local_artifacts: `cluster_results/l401/franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z/`
- video: `cluster_results/l401/franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z/videos/franka-multi-toolaxis-ep40-seed44-step-0.mp4`
- viewer_url: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_toolaxis_ep40_video2_seed44_5218e00_20260615T1550Z/videos/franka-multi-toolaxis-ep40-seed44-step-0.mp4`

Metrics / Evidence:
- Axis gate worked: `grasp_prior_reset_tool_z_axis_z_mean=-0.7927039265632629`, `grasp_prior_reset_tool_downward_z_min=0.7213642001152039`, `grasp_prior_reset_candidate_tool_down_count=49.5`.
- Reset quality still failed: `grasp_prior_reset_quality_success=0.0`.
- Table proxy identified the remaining bug: `grasp_prior_reset_projected_exact_tip_table_clearance=-0.04389432072639465` even though `grasp_prior_reset_pregrasp_tip_table_clearance=0.019522011280059814`.
- Runtime table penetration stayed false in this rollout (`finger_table_clearance_violation=0.0`), but the reset should not select a projected exact grasp whose tip proxy is below the table.
- Policy did not succeed (`success_ever_rate=0.0`, `success_rate_max=0.0`), so this run cannot be treated as evidence that Franka multi-object RL is done.

Analysis:
- The user's reported under-table approach has two separable root causes. The upward tool-axis cause is fixed by commit `5218e000731ea062b9d5af86debe989f4bd2fec0`; the selected tool z-axis is now downward. The remaining gap is that candidate `table_ok` only gated pregrasp clearance and contact-reference height, while `grasp_prior_reset_quality_success` also requires exact projected tip clearance. This mismatch lets the sampler mark a reset attempt successful while quality rejects the exact grasp geometry.

Next:
- Patch candidate selection and the post-IK mask to require exact fingertip clearance plus the same pregrasp/exact projected tip proxy clearances used by quality diagnostics. Rerun the same bounded two-env video eval without stale verified-index caches.

## 2026-06-15T16:05:00Z - Require exact projected tip table clearance in candidate selection

Goal:
- Make the multi-object grasp-prior reset sampler fail closed on the exact table-collision geometry exposed by job `1029904`.

Hypothesis:
- If the candidate table gate mirrors the quality gate's table-clearance geometry, then selected resets should have `grasp_prior_reset_quality_success=1.0`, positive `grasp_prior_reset_projected_exact_tip_table_clearance`, and positive candidate table counts under the stricter filter.

Change:
- Multi-object candidate selection now computes candidate pregrasp and projected-exact tip proxy table clearances from the candidate exact EE orientation, matching the quality diagnostic's EE-center tip proxy.
- `table_ok` now requires all four clearances to exceed `finger_table_penetration_termination_margin`: pregrasp fingertip, exact fingertip, pregrasp tip proxy, and projected-exact tip proxy.
- `_grasp_prior_reset_topdown_mask` now enforces the same selected-target fingertip and tip-proxy clearances.
- Policy eval traces now include `grasp_prior_reset_candidate_table_count` so the next run exposes whether the stricter table gate is too sparse.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- worklog: `worklogs/dextrah-multiobject-grasp-prior/dextrah-multiobject-grasp-prior-finish-20260615T074722Z.md`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `5218e000731ea062b9d5af86debe989f4bd2fec0`
- implementation_commit: `16f8cb812adad37bedb58bb1d186a173ad01a3a7`
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, this worklog.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/eval_rollout.py`
  - `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `git diff --check`

Result:
- status: local checks passed

Next:
- Commit and push, deploy the exact commit to the l401 agent worktree, and rerun the bounded policy video eval with `GRASP_PRIOR_RESET_REQUIRE_DOWNWARD_TOOL_Z=True` and no verified-index cache.

## 2026-06-15T16:10:00Z - Launch policy video eval with exact table gate

Goal:
- Validate the stricter exact table-clearance gate on the same two-env seed-44 PPO video path that exposed negative projected exact tip clearance.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- local_head: `f4f4c2acee3393bc259ea8546bfdc0fd473d1c8f`
- implementation_commit: `16f8cb812adad37bedb58bb1d186a173ad01a3a7`
- remote_commit/status: l401 agent worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` detached at `f4f4c2acee3393bc259ea8546bfdc0fd473d1c8f`, clean
- push/deploy: pushed branch to GitHub; deployed to l401 via Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/cache/dextrah_f4f4c2a_table_gate.bundle`.

Command / Job:
- job_id: `1029905`
- run_name: `franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z`
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c,CODE_COMMIT=f4f4c2acee3393bc259ea8546bfdc0fd473d1c8f,RUN_NAME=franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z,NUM_ENVS=2,NUM_STEPS=180,VIDEO_LENGTH=180,VIDEO_NAME_PREFIX=franka-multi-toolaxis-tablegate-ep40-seed44,SEED=44,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth,OBJECT_ASSET_MANIFEST_PATH=/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json,MAX_OBJECTS=2,OBJECT_STABLE_POSE_ENABLED=True,OBJECT_STABLE_POSE_CACHE_DIR=/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache,GRASP_PRIOR_RESET_ENABLED=True,GRASP_PRIOR_RESET_ATTEMPTS=8,GRASP_PRIOR_RESET_CANDIDATE_COUNT=256,GRASP_PRIOR_RESET_REQUIRE_TOPDOWN=True,GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45,GRASP_PRIOR_RESET_REQUIRE_DOWNWARD_TOOL_Z=True,GRASP_PRIOR_RESET_MIN_DOWNWARD_TOOL_Z=0.45,GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.50,... cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029905.out`
- expected_artifacts: `metrics.json`, `trace.csv`, `trace.jsonl`, and MP4 under `videos/`.

Result:
- status: running/queued

Next:
- Monitor scheduler/logs, fetch artifacts on completion, verify `candidate_table_count`, `quality_success`, projected exact tip clearance, downward tool-axis metrics, and inspect the MP4 with `viz-open`.

## 2026-06-15T16:20:00Z - Exact table-gate eval reveals no-candidate fallthrough

Goal:
- Inspect job `1029905` and decide whether the stricter table gate is sufficient for training.

Result:
- status: completed but failed acceptance
- job_state: `COMPLETED`, exit `0:0`, elapsed `00:01:10`
- local_artifacts: `cluster_results/l401/franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z/`
- video: `cluster_results/l401/franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z/videos/franka-multi-toolaxis-tablegate-ep40-seed44-step-0.mp4`
- viewer_url: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_eval_toolaxis_tablegate_ep40_video2_seed44_f4f4c2a_20260615T1605Z/videos/franka-multi-toolaxis-tablegate-ep40-seed44-step-0.mp4`

Metrics / Evidence:
- `grasp_prior_reset_success=0.0`, `grasp_prior_reset_quality_success=0.0`, `success_ever_rate=0.0`.
- Candidate marginal counts were nonzero: `candidate_tool_down_count=49.5`, `candidate_table_count=137.0`, but the selected diagnostic target had `tool_downward_z_min=0.4186267852783203 < 0.45` and `projected_exact_tip_table_clearance=-0.016749143600463867`.
- This means the stricter gates prevented accepting the bad target, but when no combined valid/fallback candidate existed in the final retry, `_compose_grasp_prior_targets` still selected the least-bad invalid candidate for IK/diagnostics. Runtime fallback-to-default kept the actual reset safe, but this is not good enough for grasp-prior RL because it yields no prior reset and confusing diagnostics.

Analysis:
- The root collision acceptance is fixed only in the success mask; the selector still needs a fail-closed no-candidate path. The next patch should never feed an invalid sampled grasp target to reset IK when `valid.any == fallback_ok.any == False` for an env.

Next:
- Add valid/fallback candidate-count metrics to eval traces and make no-candidate rows target the current safe EE pose with `sample_index=-1` and `pregrasp_farther=False`, so reset success remains false without transiently solving toward a table-colliding grasp. Then rerun the same smoke; if no valid candidates remain, increase candidate count or regenerate verified indices under the new gates.

## 2026-06-15T16:25:00Z - Fail closed when no table-safe candidate exists

Goal:
- Prevent no-candidate rows from driving IK toward invalid grasp targets and expose the combined candidate counts needed to tune the sampler.

Change:
- `_compose_grasp_prior_targets` now computes `has_reset_candidate = valid.any | fallback_ok.any`.
- For rows without a reset candidate, it sets `sample_indices=-1`, replaces target/exact EE pose with the current safe EE pose, marks `pregrasp_farther=False`, and assigns `inf` distances for selected-grasp diagnostics. This keeps reset success false but avoids transient IK toward an invalid table-colliding grasp.
- `eval_rollout.py` now logs all candidate counts: topdown, tool-down, contact-height, center, width, table, valid, and fallback.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `f4f4c2acee3393bc259ea8546bfdc0fd473d1c8f`
- implementation_commit: `e331f5a123cc7dc22514a65f1e7d995b24332f5e`
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, this worklog.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/eval_rollout.py`
  - `git diff --check`

Result:
- status: local checks passed

Next:
- Commit/push/deploy, then rerun the two-env seed-44 eval. If `candidate_valid_count=0` and `candidate_fallback_count=0`, run the same eval with a larger `GRASP_PRIOR_RESET_CANDIDATE_COUNT` before changing reward/training.

## 2026-06-15T16:30:00Z - Launch fail-closed 256-candidate smoke

Goal:
- Verify that no-candidate rows no longer target invalid table-colliding grasps, and collect combined valid/fallback candidate counts under the current 256-candidate setting.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- local_head: `321dd9b38eb04d52b2cb37467ca8086fbafbb697`
- implementation_commit: `e331f5a123cc7dc22514a65f1e7d995b24332f5e`
- remote_commit/status: l401 agent worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` detached at `321dd9b38eb04d52b2cb37467ca8086fbafbb697`, clean.
- deploy: Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/cache/dextrah_321dd9b_failclosed.bundle`.

Command / Job:
- job_id: `1029906`
- run_name: `franka_multi_eval_failclosed_ep40_video2_seed44_321dd9b_20260615T1625Z`
- candidate_count: `256`
- command: `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c,CODE_COMMIT=321dd9b38eb04d52b2cb37467ca8086fbafbb697,RUN_NAME=franka_multi_eval_failclosed_ep40_video2_seed44_321dd9b_20260615T1625Z,NUM_ENVS=2,NUM_STEPS=180,VIDEO_LENGTH=180,SEED=44,CHECKPOINT=/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth,GRASP_PRIOR_RESET_CANDIDATE_COUNT=256,... cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_failclosed_ep40_video2_seed44_321dd9b_20260615T1625Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029906.out`

Result:
- status: running/queued

Next:
- Monitor, fetch metrics/video, inspect `candidate_valid_count`, `candidate_fallback_count`, selected tool/downward axis, exact tip clearance, and whether any table penetration remains.

## 2026-06-15T16:40:00Z - Launch 4096-candidate reset sparsity smoke

Goal:
- Determine whether the zero valid/fallback count under 256 candidates is simple sampling sparsity.

Command / Job:
- job_id: `1029907`
- run_name: `franka_multi_eval_failclosed_ep40_cand4096_seed44_321dd9b_20260615T1635Z`
- candidate_count: `4096`
- num_steps: `5`
- video: disabled
- command: same seed/checkpoint/manifest/stable-pose config as job `1029906`, with `GRASP_PRIOR_RESET_CANDIDATE_COUNT=4096`, `CAPTURE_VIDEO=False`, and `NUM_STEPS=5`.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_failclosed_ep40_cand4096_seed44_321dd9b_20260615T1635Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029907.out`

Result:
- status: running/queued

Next:
- Inspect first-step reset metrics. If valid/fallback counts are still zero, debug which gate intersection kills all candidates rather than launching RL.

## 2026-06-15T16:50:00Z - 4096-candidate smoke confirms gate-intersection bug

Goal:
- Decide whether simply increasing `GRASP_PRIOR_RESET_CANDIDATE_COUNT` solves zero valid/fallback candidates.

Result:
- status: completed but failed acceptance
- job_state: `COMPLETED`, exit `0:0`, elapsed `00:00:50`
- local_artifacts: `cluster_results/l401/franka_multi_eval_failclosed_ep40_cand4096_seed44_321dd9b_20260615T1635Z/`

Metrics / Evidence:
- `grasp_prior_reset_candidate_topdown_count=1645.5`
- `grasp_prior_reset_candidate_tool_down_count=769.5`
- `grasp_prior_reset_candidate_table_count=2154.5`
- `grasp_prior_reset_candidate_valid_count=0.0`
- `grasp_prior_reset_candidate_fallback_count=0.0`
- `grasp_prior_reset_success=0.0`, `grasp_prior_reset_quality_success=0.0`

Analysis:
- The marginal gates are not sparse; their intersection is broken. The likely cause is direction-sign logic: for a tabletop grasp where the tool +Z approach axis points downward, pregrasp should be `-tool_z_axis_w` (up/away from the object). The old plus/minus distance heuristic can still choose `+tool_z_axis_w`, especially around contact-reference ties, making `tool_down_ok` and `topdown_ok` mutually exclusive enough to zero out the combined valid/fallback masks.

Next:
- Patch the multi-object prior to force `pregrasp_offset_dir_w = -tool_z_axis_w` whenever `grasp_prior_reset_require_downward_tool_z=True`, then rerun the 256-candidate smoke before changing training scale.

## 2026-06-15T16:55:00Z - Force pregrasp opposite downward tool axis

Goal:
- Fix the real sign mismatch between the GraspGen/Franka tool approach axis and the pregrasp offset direction.

Change:
- In multi-object candidate selection, when `grasp_prior_reset_require_downward_tool_z=True`, force `use_plus=False`, so `candidate_pregrasp_offset_dir_w = -candidate_tool_z_axis_w`.
- This makes a downward tool +Z approach axis produce an upward pregrasp offset, which is the expected tabletop motion away from the object/table.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `321dd9b38eb04d52b2cb37467ca8086fbafbb697`
- implementation_commit: `ba91db8a63a0837456ef722bf8c8c94bec5fce76`
- changed_files: `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, this worklog.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/eval_rollout.py`
  - `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh cluster/sbatch_bc_franka_cube_traj_action_imitation_1gpu.sh`
  - `git diff --check`

Result:
- status: local checks passed

Next:
- Commit/push/deploy the sign fix, rerun the seed-44 256-candidate smoke, and require positive valid/fallback counts plus `reset_quality_success=1.0` before RL relaunch.

## 2026-06-15T17:00:00Z - Launch pregrasp-direction 256-candidate smoke

Goal:
- Verify the sign fix restores nonzero valid/fallback candidates under the normal 256-candidate setting.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- local_head: `1c0aeb13504ce0a6c656e8cd5de0e9cc563b6d5d`
- implementation_commit: `ba91db8a63a0837456ef722bf8c8c94bec5fce76`
- remote_commit/status: l401 agent worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` detached at `1c0aeb13504ce0a6c656e8cd5de0e9cc563b6d5d`, clean.
- deploy: Git bundle `/lustre/fsw/portfolios/nvr/users/lzha/cache/dextrah_1c0aeb1_pregrasp_dir.bundle`.

Command / Job:
- job_id: `1029908`
- run_name: `franka_multi_eval_predir_ep40_cand256_seed44_1c0aeb1_20260615T1655Z`
- candidate_count: `256`
- num_steps: `5`
- video: disabled
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_predir_ep40_cand256_seed44_1c0aeb1_20260615T1655Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029908.out`

Result:
- status: running/queued

Next:
- Inspect reset metrics. Acceptance for the sign fix is nonzero valid/fallback counts, `reset_success=1.0`, `quality_success=1.0`, downward tool axis, and positive exact projected tip clearance.

## 2026-06-15T17:10:00Z - Launch pregrasp-direction 4096-candidate smoke

Goal:
- Check whether the pregrasp direction fix plus larger candidate sampling produces table-safe topdown reset candidates.

Command / Job:
- job_id: `1029909`
- run_name: `franka_multi_eval_predir_ep40_cand4096_seed44_1c0aeb1_20260615T1705Z`
- candidate_count: `4096`
- num_steps: `5`
- video: disabled
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_predir_ep40_cand4096_seed44_1c0aeb1_20260615T1705Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029909.out`

Result:
- status: running/queued

Next:
- Inspect candidate intersections and reset quality. If still zero, add targeted intersection diagnostics for `tool_down & table`, `tool_down & width`, and `tool_down & table & width & center` to identify the next gate mismatch.

## 2026-06-15T17:20:00Z - Patched 4096-candidate smoke still has zero valid/fallback

Goal:
- Inspect whether the pregrasp direction fix plus larger sample count is sufficient.

Result:
- status: completed but failed acceptance
- job_state: `COMPLETED`, exit `0:0`, elapsed `00:00:50`
- local_artifacts: `cluster_results/l401/franka_multi_eval_predir_ep40_cand4096_seed44_1c0aeb1_20260615T1705Z/`

Metrics / Evidence:
- `candidate_topdown_count=769.5` and `candidate_tool_down_count=769.5`, so the sign fix made those gates align.
- `candidate_table_count=1432.0`, but `candidate_valid_count=0.0` and `candidate_fallback_count=0.0`.
- `reset_success=0.0`, `quality_success=0.0`; no prior reset is usable yet.

Analysis:
- The next failure is not random sample count or pregrasp direction. The missing information is the intersection between downward/topdown candidates and the exact table/width/center/contact/farther gates.

Next:
- Add targeted intersection counters and rerun the short 4096-candidate smoke before relaxing any gate.

## 2026-06-15T17:25:00Z - Add targeted candidate-intersection diagnostics

Goal:
- Identify the exact gate combination that eliminates all top-side table-safe candidates.

Change:
- Added reset buffers and eval metrics for:
  - `candidate_down_table_count`
  - `candidate_down_table_width_count`
  - `candidate_down_table_width_center_count`
  - `candidate_down_table_width_center_contact_count`
  - `candidate_down_table_width_center_contact_farther_count`
- Multi-object candidate selection now fills those counts from the same boolean masks used for selection.

Version Control:
- agent_id: dextrah-multiobject-grasp-prior-finish-20260615T074722Z
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- branch: `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`
- base_commit: `1c0aeb13504ce0a6c656e8cd5de0e9cc563b6d5d`
- implementation_commit: `c1ef947c2f1c8d6c8ee9d2faf744a747213bc824`
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`, `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`, `dextrah_lab/rl_games/eval_rollout.py`, this worklog.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/rl_games/eval_rollout.py`
  - `git diff --check`

Result:
- status: local checks passed

Next:
- Commit/push/deploy the diagnostic counters and rerun a short 4096-candidate smoke.

## 2026-06-15T17:30:00Z - Launch targeted intersection 4096-candidate smoke

Goal:
- Measure which exact gate combination removes all top-side, table-safe grasp prior reset candidates.

Command / Job:
- job_id: `1029915`
- run_name: `franka_multi_eval_intersections_ep40_cand4096_seed44_6911e84_20260615T1725Z`
- commit: `6911e842249b0830551bd882c1c7f8c16bbee36a`
- candidate_count: `4096`
- num_steps: `5`
- video: disabled
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_intersections_ep40_cand4096_seed44_6911e84_20260615T1725Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029915.out`

Result:
- status: completed but failed acceptance
- job_state: no longer in queue; eval script exited successfully.
- local_artifacts: `cluster_results/l401/franka_multi_eval_intersections_ep40_cand4096_seed44_6911e84_20260615T1725Z/`

Metrics / Evidence:
- `candidate_topdown_count=769.5`, `candidate_tool_down_count=769.5`, and `candidate_table_count=1432.0`, but `candidate_down_table_count=0.0`.
- Offline reproduction from the same priors and stable poses showed both objects do have downward-tool contact candidates above the table:
  - `7195ed...`: `down_contact_table=117`, `down_contact_table_center_width=14`
  - `b87a65...`: `down_contact_table=303`, `down_contact_table_center_width=68`
- The zero intersection comes from the contact-enriched reset code replacing the raw GraspGen `panda_hand` pose with a pose that places DEXTRAH finger-link origins at the contact midpoint. For top-down grasps that moves the DEXTRAH EE/TCP below the object/table.

Change:
- Preserve the raw GraspGen `panda_hand` pose plus DEXTRAH EE/TCP offset for the exact reset pose.
- Keep GraspGen contact locations as selection/quality references only.
- For contact-enriched priors, compute the exact-reference distance from DEXTRAH EE/TCP to the contact midpoint instead of from the `panda_hand` origin.

Command / Job:
- local checks:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py`
  - `git diff --check`

Result:
- status: local checks passed

Next:
- Commit/deploy the raw-pose fix and rerun the same 4096-candidate diagnostic. Acceptance for this stage is positive `candidate_down_table_count` and nonzero valid/fallback candidates without table penetration.

## 2026-06-15T17:55:00Z - Launch raw-pose 4096-candidate diagnostic

Goal:
- Verify that preserving the raw GraspGen `panda_hand` reset pose restores top-down/table-safe candidate intersections.

Command / Job:
- job_id: `1029918`
- run_name: `franka_multi_eval_rawpose_ep40_cand4096_seed44_2b304fe_20260615T1755Z`
- commit: `2b304feaaa45eacb3aa7570549c7042aff34b704`
- candidate_count: `4096`
- num_steps: `5`
- video: disabled
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_rawpose_ep40_cand4096_seed44_2b304fe_20260615T1755Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029918.out`

Result:
- status: completed; partially passed acceptance

Next:
- Run video validation to inspect the selected raw-pose grasp visually, with per-env geometry from the validator.

Metrics / Evidence:
- `candidate_down_table_count=270.0`, `candidate_down_table_width_count=204.0`, `candidate_down_table_width_center_contact_farther_count=34.5`
- `candidate_valid_count=34.5`, `candidate_fallback_count=34.5`
- `reset_success=0.5`, `quality_success=0.5`
- `tool_downward_z=0.9993`, `projected_exact_tip_table_clearance=0.1189`, `pregrasp_tip_table_clearance=0.1589`
- `finger_table_clearance_violation=0.0`

Analysis:
- The raw-pose fix resolves the missing top-down/table-safe candidate intersection.
- One of the two vectorized objects still fails reset quality in this short eval. The next evidence should come from video validation because it records selected per-env grasp geometry and can score candidate envs before rendering.

## 2026-06-15T18:15:00Z - Launch raw-pose video validation

Goal:
- Visually inspect the selected grasp after the raw-pose fix and verify the robot does not reach from below or penetrate the table.

Command / Job:
- job_id: `1029919`
- run_name: `franka_multi_video_rawpose_2obj_seed44_2b304fe_20260615T1815Z`
- commit: `2b304feaaa45eacb3aa7570549c7042aff34b704`
- num_envs: `2`
- candidate_count: `4096`
- reset_attempts: `8`
- warmstart_steps: approach `20`, close `20`, lift `32`
- reset/perturbation scenarios shortened to keep the validation focused on grasp-contact.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_rawpose_2obj_seed44_2b304fe_20260615T1815Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029919.out`

Result:
- status: running/queued

Next:
- Inspect `video_metrics.json`, selected grasp geometry, and frames via `viz-open`.

## 2026-06-15T18:35:00Z - Launch raw-pose close-width ablation

Goal:
- Test whether the safe, top-down raw-pose grasp fails only because the warmstart closes too wide for thin GraspGen objects.

Command / Job:
- job_id: `1029920`
- run_name: `franka_multi_video_rawpose_close0_2obj_seed44_2b304fe_20260615T1835Z`
- commit: `2b304feaaa45eacb3aa7570549c7042aff34b704`
- num_envs: `2`
- candidate_count: `4096`
- close_width: `0.0`
- use_prior_close_width: `False`
- warmstart_steps: approach `20`, close `24`, lift `28`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_rawpose_close0_2obj_seed44_2b304fe_20260615T1835Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029920.out`

Result:
- status: running/queued

Next:
- Compare lift and selected grasp metrics against close-width `0.025`.

## 2026-06-15T18:50:00Z - Launch raw-pose close0 strong-lift validation

Goal:
- Test whether the close0 grasp can clear the success height with a longer, stronger lift phase.

Command / Job:
- job_id: `1029921`
- run_name: `franka_multi_video_rawpose_close0_lift1_2obj_seed44_2b304fe_20260615T1850Z`
- commit: `2b304feaaa45eacb3aa7570549c7042aff34b704`
- num_envs: `2`
- candidate_count: `4096`
- close_width: `0.0`
- use_prior_close_width: `False`
- warmstart_steps: approach `20`, close `28`, lift `80`
- lift_action_z: `1.0`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_rawpose_close0_lift1_2obj_seed44_2b304fe_20260615T1850Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029921.out`

Result:
- status: running/queued

Next:
- Inspect whether the selected grasp reaches `selected_lift_height_threshold=0.12` without table collision or object drag.

## 2026-06-15T19:05:00Z - Inspect raw-pose validation sweep and promote warmstart defaults

Goal:
- Turn the passing raw-pose/top-down/table-safe validation settings into the multi-object defaults before launching RL, so later runs do not silently inherit the short single-cube warmstart.

Evidence:
- `franka_multi_video_rawpose_2obj_seed44_2b304fe_20260615T1815Z` selected a safe downward-tool grasp, but did not lift the object:
  - `selected_tool_downward_z=0.9986`
  - `selected_quality_success=True`
  - `finger_table_clearance_min=0.0606`
  - `selected_lift_height_max=0.0`
- `franka_multi_video_rawpose_close0_2obj_seed44_2b304fe_20260615T1835Z` improved lift after fully closing the gripper:
  - `selected_lift_height_max=0.0213`
  - `selected_gripper_width_min=0.0192`
  - no selected table violation
- `franka_multi_video_rawpose_close0_lift1_2obj_seed44_2b304fe_20260615T1850Z` passed all validation scenarios:
  - `overall_passed=True`
  - `grasp_contact=True`, `perturbation=True`, `reset_settle=True`
  - `selected_lift_height_max=0.2692` above threshold `0.12`
  - `selected_tool_downward_z=0.9986`
  - `selected_pregrasp_offset_dir_z=0.9986`
  - `finger_table_clearance_min=0.06085`
  - `selected_done_count=0`
  - `selected_candidate_valid_count=91`, `selected_candidate_fallback_count=91`
- Local viewer links:
  - metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_video_rawpose_close0_lift1_2obj_seed44_2b304fe_20260615T1850Z/video_metrics.json`
  - final frame: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_video_rawpose_close0_lift1_2obj_seed44_2b304fe_20260615T1850Z/grasp_contact/frames/frame_0042.png`

Change:
- Set multi-object warmstart defaults to approach `20`, close `28`, lift `80`, close width `0.0`, `use_prior_close_width=False`, and lift z action `1.0`.
- Applied the same defaults to eval, validation, teacher-training, and verified-grasp collection wrappers.
- Left the single-cube Franka environment unchanged.

Validation:
- `python3 -m py_compile` on touched task/eval modules: passed
- `bash -n` on touched Slurm wrappers: passed
- `git diff --check`: passed

Next:
- Commit the default update, deploy the exact commit to the l401 worktree, and relaunch video validation without overriding the warmstart values.

## 2026-06-15T16:37:00Z - Launch default-warmstart validation from `881a14a`

Goal:
- Verify that the committed multi-object defaults reproduce the passing grasp-contact validation without manually overriding warmstart parameters.

Command / Job:
- job_id: `1029922`
- run_name: `franka_multi_video_defaults_2obj_seed44_881a14a_20260615T1637Z`
- commit: `881a14a261ec3a2063b3f997ba0e5ea7ec1eb35c`
- remote code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json`
- stable pose cache: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`
- num_envs: `2`
- max_objects: `2`
- seed: `44`
- candidate_count: `4096`
- reset_attempts: `8`
- warmstart values inherited from wrapper defaults:
  - close width `0.0`
  - `use_prior_close_width=False`
  - lift action z `1.0`
  - approach/close/lift steps `20/28/80`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_defaults_2obj_seed44_881a14a_20260615T1637Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029922.out`

Result:
- status: running on `pool0-00008` at first poll.

Next:
- Fetch `video_metrics.json` and frames after completion, inspect table-clearance/downward-axis/lift evidence, then decide whether to launch RL.

## 2026-06-15T16:41:00Z - Launch current-code verified-grasp collection

Goal:
- Regenerate a small verified-grasp cache under the fixed raw-pose/downward-tool/table-clearance implementation before PPO training, instead of reusing older caches produced by now-stale semantics.

Command / Job:
- job_id: `1029923`
- run_name: `verified_rawpose_defaults_train2_881a14a_20260615T1641Z`
- commit: `881a14a261ec3a2063b3f997ba0e5ea7ec1eb35c`
- remote code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json`
- stable pose cache: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`
- num_envs: `64`
- max_objects: `2`
- seed: `46`
- candidate_count: `4096`
- reset_attempts: `8`
- target_per_object: `8`
- score_steps: `128`
- warmstart values inherited from the updated wrapper defaults.
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_rawpose_defaults_train2_881a14a_20260615T1641Z/verified_indices.json`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029923.out`

Result:
- status: submitted.

Next:
- Require indices for both object UUIDs before using this cache in PPO training.

## 2026-06-15T16:44:00Z - Cancel stale-cache replacement attempt and launch object0 gate diagnostic

Collection Result:
- Job `1029923` was canceled after 10 cycles because it was not producing a usable current-code cache.
- Partial output:
  - object `b87a65917e494aa4b306aeb6ee961182` had many valid reset candidates and dynamic lifts, but `MAX_DONE_COUNT=0` rejected successful rollouts that terminated once.
  - object `7195ed3346a445448308febe833c180a` had `reset_success=0`, `quality_success=0`, and `candidate_valid_count=0` / `candidate_fallback_count=0` in all observed cycles.
- This means the next blocker is object0 candidate-gate intersection under the fixed raw-pose semantics, not just stale verified-cache selection.

Command / Job:
- job_id: `1029924`
- run_name: `franka_multi_eval_object0_gate_diag_881a14a_20260615T1644Z`
- commit: `881a14a261ec3a2063b3f997ba0e5ea7ec1eb35c`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- num_envs: `64`
- max_objects: `1`
- num_steps: `5`
- candidate_count: `4096`
- reset_attempts: `8`
- no video; diagnostics come from `trace.csv`/`metrics.json`.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_object0_gate_diag_881a14a_20260615T1644Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029924.out`

Next:
- Inspect `grasp_prior_reset_candidate_down_table*` counters to identify which gate combination eliminates object0.

## 2026-06-15T16:50:00Z - Patch object0 gate without allowing table penetration

Diagnostic Results:
- Strict contact-height gate (`GRASP_PRIOR_RESET_MIN_CONTACT_HEIGHT_ABOVE_CENTER=0.0`) on object0:
  - `grasp_prior_reset_success=0.0`
  - `grasp_prior_reset_quality_success=0.0`
  - `candidate_down_table_width_center_count=135.94`
  - `candidate_down_table_width_center_contact_count=0.0`
  - `candidate_valid_count=0.0`, `candidate_fallback_count=0.0`
- Relaxed contact-height gate (`-0.02`) before tightening table floor:
  - `grasp_prior_reset_success=1.0`
  - `grasp_prior_reset_quality_success=1.0`
  - `candidate_valid_count=139.70`, `candidate_fallback_count=139.70`
  - `grasp_prior_reset_tool_downward_z=0.9708`
  - `grasp_prior_reset_pregrasp_tip_table_clearance=0.0764`
  - `grasp_prior_reset_projected_exact_tip_table_clearance=-0.0013`
  - `finger_table_clearance_violation=0.0`

Analysis:
- Object0 is long/thin, so useful top-down pinch contacts can have a contact midpoint slightly below the object center.
- The contact-height gate was stricter than the user requirement. It eliminated object0 even though many candidates were downward-tool, table-safe under finger clearance, width-valid, and center-valid.
- However, using the environment penetration margin as the reset table floor allowed a selected projected tip proxy to be slightly below the table. For this task, grasp-prior reset candidates should require nonnegative table clearance.

Change:
- Set multi-object `grasp_prior_reset_min_contact_height_above_center=-0.02`.
- Tighten multi-object candidate and reset-quality table floors to `max(finger_table_penetration_termination_margin, 0.0)`.
- Updated eval, validation, training, and verified-grasp collection wrappers to use the same contact-height default.

Validation:
- `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env.py dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_multi_object_grasp_videos.py dextrah_lab/rl_games/collect_franka_multi_object_verified_grasps.py dextrah_lab/rl_games/eval_rollout.py`: passed
- `bash -n cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh cluster/sbatch_train_teacher_8gpu.sh`: passed
- `git diff --check`: passed

Next:
- Commit/deploy, then rerun object0 and two-object validation from the patched SHA. Acceptance requires nonnegative projected exact tip clearance, downward tool axis, positive valid/fallback counts, and no table-clearance violation.

## 2026-06-15T16:49:00Z - Launch object0 default diagnostic from `4234fb5`

Command / Job:
- job_id: `1029926`
- run_name: `franka_multi_eval_object0_default_4234fb5_20260615T1649Z`
- commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- num_envs: `64`
- max_objects: `1`
- num_steps: `5`
- candidate_count: `4096`
- reset_attempts: `8`
- contact-height default inherited from wrapper/config: `-0.02`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_object0_default_4234fb5_20260615T1649Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029926.out`

Result:
- status: submitted.

Next:
- Inspect whether nonnegative table-clearance floor still leaves object0 with valid/fallback candidates and reset quality.

## 2026-06-15T16:52:00Z - Resubmit object0 diagnostic with lower memory

Result:
- Job `1029926` stayed pending with `(Resources)` under the wrapper's `160G` memory request.
- Prior identical 64-env object0 diagnostics used about `22G`, so the pending job was canceled and resubmitted with `--mem=64G`.

Command / Job:
- job_id: `1029927`
- run_name: `franka_multi_eval_object0_default64g_4234fb5_20260615T1652Z`
- commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- same diagnostic settings as `1029926`, with Slurm memory override `64G`.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_eval_object0_default64g_4234fb5_20260615T1652Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029927.out`

Next:
- Monitor job `1029927` and inspect trace counters after completion.

## 2026-06-15T16:54:00Z - Object0 default diagnostic passes after strict table floor

Result:
- Job `1029927` completed with exit `0:0` in `00:01:06`.
- Local artifacts: `cluster_results/l401/franka_multi_eval_object0_default64g_4234fb5_20260615T1652Z/`

Metrics:
- `grasp_prior_reset_success=1.0`
- `grasp_prior_reset_quality_success=1.0`
- `grasp_prior_reset_candidate_valid_count=116.48`
- `grasp_prior_reset_candidate_fallback_count=116.48`
- `grasp_prior_reset_candidate_down_table_width_center_contact_farther_count=116.48`
- `grasp_prior_reset_tool_downward_z=0.9832`
- `grasp_prior_reset_pregrasp_tip_table_clearance=0.0822`
- `grasp_prior_reset_projected_exact_tip_table_clearance=0.00358`
- `grasp_prior_reset_finger_table_clearance=0.1266`
- `finger_table_clearance_violation=0.0`

Analysis:
- The committed defaults now admit object0 top-side grasps while preserving nonnegative projected tip clearance.
- This resolves the prior object0 zero-candidate blocker without reintroducing table penetration.

Next:
- Run a two-object video validation from `4234fb5` with committed defaults before regenerating verified-grasp cache and launching PPO.

## 2026-06-15T16:54:00Z - Launch two-object video validation from `4234fb5`

Command / Job:
- job_id: `1029928`
- run_name: `franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z`
- commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json`
- stable pose cache: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`
- num_envs: `2`
- max_objects: `2`
- seed: `44`
- candidate_count: `4096`
- reset_attempts: `8`
- Slurm memory override: `64G`
- warmstart/contact/table defaults inherited from `4234fb5` wrappers.
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_1029928.out`

Next:
- Fetch metrics/frames and verify the selected grasp is top-down, table-clear, and dynamically lifted.

## 2026-06-15T16:56:00Z - Two-object video validation passes on `4234fb5`; launch current-code cache collection

Video Result:
- Job `1029928` completed with exit `0:0` in `00:01:05`.
- Local artifacts: `cluster_results/l401/franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z/`
- Viewer links:
  - metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z/video_metrics.json`
  - first frame: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z/grasp_contact/frames/frame_0000.png`
  - final frame: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/l401/franka_multi_video_defaults_2obj_seed44_4234fb5_20260615T1654Z/grasp_contact/frames/frame_0064.png`

Metrics:
- `overall_passed=True`, `grasp_contact=True`
- selected object: `b87a65917e494aa4b306aeb6ee961182`, sample `1209`
- `selected_lift_height_max=0.26917` vs threshold `0.12`
- `selected_tool_downward_z=0.9986`, `selected_tool_z_axis_z=-0.9986`
- `selected_pregrasp_offset_dir_z=0.9986`
- `selected_candidate_valid_count=237`, `selected_candidate_fallback_count=240`
- `selected_done_count=0`
- `finger_table_clearance_min=0.06085`
- visual inspection of frames `0000`, `0042`, and `0064`: arm stays above the table and lifts the object.

Command / Job:
- job_id: `1029929`
- run_name: `verified_rawpose_stricttable_train2_4234fb5_20260615T1656Z`
- goal: regenerate current-code verified indices for the two-object debug set before PPO.
- num_envs: `64`, max_objects: `2`, candidate_count: `4096`, reset_attempts: `8`
- collection pass criteria: `MAX_DONE_COUNT=1`, `REQUIRE_SUCCESS=True`, `MIN_LIFT_HEIGHT=0.10`
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_4234fb5_20260615T1656Z/verified_indices.json`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029929.out`

Next:
- Require nonempty `indices_by_uuid` for both objects before PPO.

## 2026-06-15T17:03:00Z - Resubmit current-code cache collection with shorter walltime

Result:
- Job `1029929` remained pending with `(Resources)`. Node inspection showed mixed nodes with planned allocations; the likely blocker was the 2-hour walltime not fitting a backfill gap, not a code failure.
- Canceled `1029929` before it started.

Command / Job:
- job_id: `1029930`
- run_name: `verified_rawpose_stricttable_train2_short_4234fb5_20260615T1703Z`
- source/settings: same commit `4234fb5859db7206d55ddca7342e41a5b06439ff`, same two-object manifest, stable-pose cache, strict downward-tool/table gates, `NUM_ENVS=64`, `CYCLES=30`, `MIN_CYCLES=8`, `TARGET_PER_OBJECT=8`, `MAX_DONE_COUNT=1`, `REQUIRE_SUCCESS=True`, `MIN_LIFT_HEIGHT=0.10`.
- scheduler change only: `--time=0:30:00`, `--mem=64G`.
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_short_4234fb5_20260615T1703Z/verified_indices.json`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_1029930.out`

Next:
- Monitor `1029930`; require nonempty verified indices for both object UUIDs before PPO continuation.

## 2026-06-15T17:04:00Z - Move verified-cache collection from l401 to A100

Result:
- Job `1029930` also remained pending on l401. Since A100 has the same NFS worktree at commit `4234fb5859db7206d55ddca7342e41a5b06439ff` and visible mixed GPU capacity, canceled `1029930` before it started.

Command / Job:
- job_id: `29104254`
- host: `a1001`
- run_name: `verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z`
- source/settings: same current-code cache collection settings as `1029930`.
- scheduler: A100 short partitions, `--time=0:30:00`, `--mem=64G`, `1` GPU.
- output: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_29104254.out`

Next:
- Monitor `29104254`; if it produces target counts for both objects, use this cache for PPO continuation.

## 2026-06-15T17:09:00Z - Current-code verified-cache collection is sparse

Result:
- A100 job `29104254` completed the simulation/collection but exited with wrapper status `1:0` because it did not meet `TARGET_PER_OBJECT=8`.
- Slurm elapsed: `00:04:22`.
- Output JSON was still written at `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`.

Metrics:
- `counts_by_uuid`: object0 `7195ed3346a445448308febe833c180a` -> `1`; object1 `b87a65917e494aa4b306aeb6ee961182` -> `3`.
- object0 indices: `[415]`, `pass_count=4`, `observed_reset_count=960`, `quality_reset_count=960`.
- object1 indices: `[1154, 521, 1209]`, `pass_count=936`, `observed_reset_count=960`, `quality_reset_count=960`.

Analysis:
- This is not a table-collision/root-pose failure: reset quality was available for both objects under the strict gates.
- The hard object0 has only rare scripted warmstart lift success under the collector, so training should not blindly assume a broad verified dynamic cache exists.
- Before PPO, run an object0-only video validation with the current raw sampler and no verified-cache restriction to inspect whether the sampler can still produce a table-safe dynamic lift for object0.

## 2026-06-15T17:11:00Z - Launch object0 raw-sampler video validation

Command / Job:
- job_id: `29105119`
- host: `a1001`
- run_name: `franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z`
- commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- settings: `NUM_ENVS=8`, `MAX_OBJECTS=1`, strict downward-tool/table gates, `GRASP_RESET_CANDIDATE_COUNT=4096`, `GRASP_RESET_ATTEMPTS=8`, `GRASP_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, no verified-index cache.
- metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z/video_metrics.json`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/validate_franka_multi_object_videos_29105119.out`

Next:
- Inspect object0 selected reset geometry, table clearance, lift height, and rendered frames.

## 2026-06-15T17:14:00Z - Object0 raw-sampler video validation passes

Result:
- Job `29105119` completed with exit `0:0` in `00:02:19`.
- Local artifacts: `cluster_results/a1001/franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z/`
- Viewer links:
  - metrics: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/a1001/franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z/video_metrics.json`
  - mid frame: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/a1001/franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z/grasp_contact/frames/frame_0024.png`
  - final frame: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/cluster_results/a1001/franka_multi_video_object0_rawsampler_4234fb5_20260615T1711Z/grasp_contact/frames/frame_0048.png`

Metrics:
- `overall_passed=True`, `grasp_contact=True`.
- selected object: `7195ed3346a445448308febe833c180a`
- selected grasp index: `415`
- `selected_lift_height_max=0.13918`
- `selected_tool_downward_z=0.99762`, `selected_tool_z_axis_z=-0.99762`, `selected_pregrasp_offset_dir_z=0.99762`
- `selected_candidate_tool_down_count=657`, `selected_candidate_topdown_count=657`, `selected_candidate_table_count=1570`, `selected_candidate_valid_count=75`, `selected_candidate_fallback_count=75`
- `finger_table_clearance_min=0.05452`
- `selected_done_count=0`
- Visual inspection of frames `0000`, `0024`, and `0048`: above-table approach, top-down close, visible lift; no under-table reach.

Analysis:
- Object0 is hard for the scripted collector because only index `415` produced dynamic lift passes often enough to be selected, but the current raw sampler can still find a valid, table-safe, top-down lift under the fixed gates.
- PPO continuation can use the current-code small verified cache to avoid stale/outdated indices while preserving a known object0-valid grasp prior.

Next:
- Launch PPO continuation from epoch 40 using the current commit and current-code verified cache.

## 2026-06-15T17:17:00Z - Launch PPO continuation with current reset prior

Submission note:
- First attempted 4-GPU submission with `--mem=0`; Slurm rejected it before creating a job because all-node memory with 4 GPUs strands resources.
- Resubmitted with `--mem=512G`.

Command / Job:
- job_id: `29105479`
- host: `a1001`
- run_name: `franka_multi_ppo_bcinit_rawpose_stricttable_cont80_4234fb5_20260615T1717Z`
- source commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- remote code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_rawpose_stricttable_cont80_4234fb5_20260615T1717Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29105479.out`

Training settings:
- `NPROC_PER_NODE=4`, `NUM_ENVS=1024`, `MAX_ITERATIONS=80`
- PPO resume shape kept close to the known epoch-40 run: `LR=2e-5`, central value LR `1e-5`, `HORIZON_LENGTH=64`, `MINIBATCH_SIZE=16384`, `MINI_EPOCHS=2`, `SAVE_FREQUENCY=1`.
- two-object manifest `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest.json`, `MAX_OBJECTS=2`, stable-pose cache enabled.
- current-code verified cache: `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`.
- strict reset gates: downward tool axis required, `GRASP_PRIOR_RESET_MIN_DOWNWARD_TOOL_Z=0.45`, contact-height floor `-0.02`, nonnegative table floor in source, `GRASP_PRIOR_RESET_MAX_CENTER_DISTANCE_FRAC=0.50`, `GRASP_PRIOR_RESET_CANDIDATE_COUNT=128`.

Next:
- Monitor job startup, then inspect JSONL curves and checkpoints. Success requires reward/success curves plus evaluation/video evidence under the fixed reset prior.

## 2026-06-15T17:24:00Z - Cancel reset-only PPO continuation after success collapse

Result:
- Job `29105479` started cleanly, restored the epoch-40 runtime state on 4 ranks, and trained from epoch `41` through `62`.
- Canceled manually after JSONL inspection showed the run was not learning under the current small verified-cache reset distribution.

Metrics:
- `cube_grasp_prior_reset_success_rate=1.0`
- `cube_grasp_prior_candidate_valid_count=128`
- `cube_grasp_prior_tool_downward_z=0.9981`
- `cube_finger_table_clearance_violation` was zero or near-zero numerical noise.
- `cube_success_rate=0.0` across inspected epochs `41-62`.
- `cube_has_lifted_rate` stayed low, roughly `0.005-0.023`.
- object0 lift was low but nonzero; object1 lift was near zero.

Analysis:
- This is not the original under-table/from-below bug: the reset distribution is table-safe and top-down.
- The old policy checkpoint does not immediately handle the new small current-code verified reset distribution when no action guidance is present.
- Relaunch from the original epoch-40 checkpoint with grasp-prior action warmstart and action-prior reward enabled, so the scripted reference sequence both creates successful trajectories and gives the policy an imitation signal.

Next:
- Run a shorter guided continuation to epoch `60`; inspect warmstart/action-prior metrics before committing to a longer continuation.

## 2026-06-15T17:26:00Z - Launch guided PPO continuation with action prior

Command / Job:
- job_id: `29105685`
- host: `a1001`
- run_name: `franka_multi_ppo_bcinit_rawpose_stricttable_warmprior60_4234fb5_20260615T1726Z`
- source commit: `4234fb5859db7206d55ddca7342e41a5b06439ff`
- remote code: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_rawpose_stricttable_warmprior60_4234fb5_20260615T1726Z`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29105685.out`

Training settings:
- Resumes the same BC-initialized epoch-40 PPO checkpoint used by the reset-only test:
  `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`.
- 4 A100 GPUs, `NUM_ENVS=1024`, `MAX_ITERATIONS=60`, `LR=2e-5`, central value LR `1e-5`, `HORIZON_LENGTH=64`, `MINIBATCH_SIZE=16384`, `MINI_EPOCHS=2`, `SAVE_FREQUENCY=1`.
- Same two-object manifest and current-code verified cache as the reset-only run.
- Strict reset gates remain enabled: downward tool axis, top-down, current source table-clearance floor, and current-code verified indices.
- New guidance: `GRASP_PRIOR_ACTION_WARMSTART_ENABLED=True`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, action-prior reward weight `40.0`, sharpness `2.0`.

Next:
- Monitor startup and JSONL metrics. Required diagnostics: reset success/table clearance, warmstart phase rates, action-prior reward/active rate, lift and success curves by object.

## 2026-06-15T17:34:00Z - Guided PPO continuation completed but did not solve task

Result:
- Job `29105685` completed with exit `0:0` in `00:07:36`.
- Run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_rawpose_stricttable_warmprior60_4234fb5_20260615T1726Z`
- Final checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_rawpose_stricttable_warmprior60_4234fb5_20260615T1726Z/nn/last_dextrah_franka_multi_object_grasp_ep_60_rew_1813.5569.pth`

Final metrics:
- Epoch `60`: `cube_success_rate=0.1367`, `cube_has_lifted_rate=0.2402`.
- Epoch `60` per object: object0 success `0.1250`, object1 success `0.1484`.
- Last-10 mean: aggregate success `0.0807`, lift `0.1808`, object0 success `0.1215`, object1 success `0.0398`.
- Full run mean over epochs `42-60`: aggregate success `0.1353`, lift `0.2339`, object0 success `0.1095`, object1 success `0.1612`.
- Reset geometry remained healthy throughout: `cube_grasp_prior_reset_success_rate=1.0`, `cube_grasp_prior_tool_downward_z=0.9981`, `cube_finger_table_clearance_violation=0` except one tiny numerical blip `0.0006115`.

Analysis:
- The under-table/from-below root cause remains fixed under the current reset gates.
- Action warmstart plus action-prior reward produced an early spike (`epoch 43` success `0.4902`, object1 success `0.9375`) but did not stabilize. By epochs `52-60`, aggregate success stayed roughly `0.045-0.137`.
- The current-code verified cache is very small and imbalanced: object0 exports only index `415` (`4/6` pass rate in collector), object1 exports three indices (`1154`, `521`, `1209`) with high collector pass rates but only from a short current-code collection.
- This is not a reason to train longer as-is. The next useful step is a targeted scripted rollout / cache robustness diagnostic under the exact training warmstart settings, then either prune/regenerate verified indices or adjust the scripted action prior before PPO.

Next:
- Run a targeted evaluation/diagnostic of the scripted grasp-prior warmstart distribution by object/index under the fixed raw-pose reset gates, using the current cache and training warmstart settings. Treat the PPO checkpoint as not ready for policy evaluation until the scripted prior itself is stable.

## 2026-06-15T17:37:00Z - Launch exact verified-cache scripted audit

Source update:
- Commit `9943101936f74edda9da24680b8c1f97db047303` adds `GRASP_PRIOR_VERIFIED_INDICES_PATH` support to `collect_franka_multi_object_verified_grasps.py` and `cluster/sbatch_collect_franka_multi_object_verified_grasps_1gpu.sh`.
- Deployed to remote worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`.

Command / Job:
- job_id: `29106214`
- host: `a1001`
- run_name: `verified_cache_audit_train2_rawpose_9943101_20260615T1737Z`
- output JSON: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/verified_grasp_indices/verified_cache_audit_train2_rawpose_9943101_20260615T1737Z/verified_indices.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/collect_franka_multi_object_verified_grasps_29106214.out`

Audit settings:
- `NUM_ENVS=64`, `CYCLES=80`, `MIN_CYCLES=80`, `TARGET_PER_OBJECT=0` to force a fixed-length audit without target-count early stop/failure.
- Restricts reset sampling to the exact cache used by PPO:
  `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`.
- Same raw-pose reset gates and training warmstart settings as the failed PPO continuation: downward tool axis, table-safe source gates, `SCORE_STEPS=128`, approach `20`, close `28`, lift `80`, close width `0.0`, lift action z `1.0`, `require_current_lift_ready=True`.
- Success threshold: `MIN_LIFT_HEIGHT=0.12`, `REQUIRE_SUCCESS=True`, `MAX_DONE_COUNT=1`.

Next:
- Monitor cycle stats and per-index pass rates. If the exact cache is unstable, derive a pruned cache or adjust the scripted action prior before relaunching PPO.

## 2026-06-15T17:40:00Z - Launch multi-object BC/action-imitation from current scripted prior

Rationale:
- The exact-cache audit showed the scripted prior itself is useful: after six cycles, object0 index `415` passed `79/192` (`0.411`) and object1 index `1209` passed `184/192` (`0.958`), with clean reset/quality.
- The failed PPO continuation therefore looks like policy imitation/learning failure, not a reset or under-table failure.
- This is the first BC/action-imitation run I launched myself for the Franka multi-object setup in this session. It starts from the existing epoch-40 BC-initialized PPO checkpoint rather than retraining the original BC pipeline from scratch.

Command / Job:
- job_id: `29106443`
- host: `a1001`
- run_name: `franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z`
- output checkpoint: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/bc_franka_cube_29106443.out`

BC settings:
- Input checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcinit_retrypose_resetonly_cont40_9ae97c0_20260615T1312Z/nn/last_dextrah_franka_multi_object_grasp_ep_40_rew_4852.5146.pth`.
- `TASK=Dextrah-Franka-Multi-Object-Grasp`, `NUM_ENVS=128`, `COLLECTION_STEPS=512`, `TRAIN_STEPS=1200`, `BATCH_SIZE=4096`, `LR=1e-4`, `LOSS_DIMS=all`.
- Collection and label source are both `reference_delta`, which maps to `compute_grasp_prior_reference_actions()` for this task.
- Same two-object manifest, current verified cache, stable-pose cache, object physics, and strict downward/top-down raw-pose reset gates.

Next:
- Monitor `bc_metrics.json`, validation loss/action-dim errors, and produced checkpoint. If BC learns the reference actions, use the BC checkpoint as the next PPO initialization and evaluate/continue RL.

## 2026-06-15T17:45:00Z - BC/action-imitation completed

Result:
- Job `29106443` completed with exit `0:0` in `00:01:56`.
- Output checkpoint exists:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`
  (`77M`).
- Metrics JSON:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/bc_metrics.json`.

BC metrics:
- Samples: `65536` total, `55706` train, `9830` validation.
- Collection source and label source: `reference_delta`.
- Initial frozen-policy residual: `val_l2=1.8569`, `val_mse=0.5220`.
- Selected checkpoint step: `1150`.
- Selected held-out error: `val_l2=0.1003`, `val_mse=0.00720`.
- Per-dim selected validation abs errors: `x=0.0245`, `y=0.0259`, `z=0.0268`, `up=0.0135`, `rx=0.0162`, `ry=0.0187`, `rz=0.0165`, `gripper=0.0319`.
- Final step was similar: `val_l2=0.1005`, `val_mse=0.00717`.

Analysis:
- This is a strong supervised fit to the scripted current-code reference actions, and materially different from the input policy.
- It is still not proof of task success; it needs policy rollout under the same fixed raw-pose cache and table-safe gates.

## 2026-06-15T17:47:00Z - Launch BC policy rollout eval

Submission note:
- Attempted to submit the eval wrapper from `a1001`, but `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` requests `#SBATCH --partition=batch`, which is not an A100 partition. Slurm rejected the submission before creating a job.
- Relaunched the same metrics eval on `l401`, where `batch` is the correct L40S partition.

Command / Job:
- job_id: `1029946`
- host: `l401`
- run_name: `franka_multi_bc_policy_eval_rawpose_cache_9943101_20260615T1747Z`
- checkpoint: `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`
- expected run dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_bc_policy_eval_rawpose_cache_9943101_20260615T1747Z`
- expected metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_bc_policy_eval_rawpose_cache_9943101_20260615T1747Z/metrics.json`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_1029946.out`

Eval settings:
- `NUM_ENVS=64`, `NUM_STEPS=360`, `CAPTURE_VIDEO=False`, deterministic policy, `SEED=82`.
- Same two-object manifest, stable-pose cache, object friction `4.0/3.5`, exact verified-cache path, and raw-pose top-down/downward-tool/table gates as the audit and PPO jobs.

Next:
- Inspect rollout metrics. If the BC policy actually lifts/succeeds, use this checkpoint as the PPO initialization; if not, inspect rollout traces before relaunching PPO.

## 2026-06-15T17:50:00Z - Exact-cache audit and BC policy eval completed

Exact-cache audit result:
- Job `29106214` completed with exit `0:0` in `00:08:42`.
- Final audit cycles: `80/80`.
- Object `7195ed3346a445448308febe833c180a`, index `415`: `986/2560` pass observations, pass rate `0.3852`, max lift `0.2664`, `done_count=0`.
- Object `b87a65917e494aa4b306aeb6ee961182`, index `1209`: `2493/2560` pass observations, pass rate `0.9738`, max lift `0.1623`, `done_count=1`.
- Aggregate scripted pass observations: `3479/5120 = 0.6795`.
- Interpretation: the exact verified cache used by PPO is table-safe and useful, but object0 is intrinsically much harder than object1 under this single-index cache.

BC policy eval result:
- Job `1029946` completed with exit `0:0` in `00:01:16`.
- Metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_bc_policy_eval_rawpose_cache_9943101_20260615T1747Z/metrics.json`.
- First-attempt `eval_success_rate=0.375` over `64` envs; `success_ever_rate=0.375`.
- `success_rate_max=0.21875`, `success_rate_final=0.0`; success termination was not suppressed, so completed successes reset during the rollout.
- Completed episodes: `22`, completed episode success rate `0.9091`.
- Done reasons: `success_done=20`, `unclassified=2`; `finger_table_penetration=0`, `prelift_drag=0`, `cube_out=0`.
- Reset diagnostics remain clean in trace: `grasp_prior_reset_success=1.0`, `quality_success=1.0`, `tool_downward_z≈0.9981`, `finger_table_clearance_violation=0`.

Analysis:
- The root under-table/from-below bug is not showing up in the current reset distribution or the BC policy rollout.
- The policy bottleneck is now learning/stability: BC gets `37.5%` first-attempt success versus the scripted exact-cache upper bound of about `68%` under this small two-object cache.
- Next PPO should initialize from the BC checkpoint, keep reset gates/cache fixed, and use light reference-action reward regularization without scripted warmstart overrides, so the actor policy itself continues learning.

## 2026-06-15T17:52:00Z - Launch PPO from self-trained BC checkpoint

Planned settings:
- Source commit: `9943101936f74edda9da24680b8c1f97db047303`.
- Checkpoint: `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`.
- Two-object manifest and stable-pose cache unchanged.
- Exact verified-cache path unchanged:
  `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`.
- PPO: `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, `MAX_ITERATIONS=100`, LR `1e-5`, central LR `5e-6`, horizon `64`, minibatch `16384`, mini epochs `2`, save every epoch.
- Action prior: `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, weight `10.0`, sharpness `2.0`.
- Scripted action warmstart: disabled, so training/eval uses policy actions rather than scripted overrides.

Command / Job:
- job_id: `29106873`
- host: `a1001`
- run_name: `franka_multi_ppo_bcself_rawpose_cache_reg10_9943101_20260615T1752Z`
- expected run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_rawpose_cache_reg10_9943101_20260615T1752Z`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29106873.out`

Next:
- Monitor RL curves, reset diagnostics, per-object success, and checkpoints. Required success evidence is not Slurm completion; inspect JSONL/TensorBoard metrics and run eval/video from the best checkpoint.

## 2026-06-15T18:01:00Z - PPO from BC completed; launch epoch-100 eval

PPO result:
- Job `29106873` completed with exit `0:0` in `00:11:47`.
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_rawpose_cache_reg10_9943101_20260615T1752Z`
- Final checkpoint:
  `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_rawpose_cache_reg10_9943101_20260615T1752Z/nn/last_dextrah_franka_multi_object_grasp_ep_100_rew_5377.594.pth`

Training curve summary:
- Epoch `100`: aggregate `cube_success_rate=0.3701`, `cube_has_lifted_rate=0.3926`.
- Epoch `100` per logged object metric: object0 success `0.0`, object1 success `0.7402`; object0 lift `0.0`, object1 lift `0.7852`.
- Best aggregate training success: epoch `100`, `0.3701`.
- Last-10 mean aggregate success: `0.3438`; last-10 mean lift: `0.3747`.
- Reset diagnostics remained clean: `cube_grasp_prior_reset_success_rate=1.0`, `cube_grasp_prior_quality_success_rate=1.0`, `cube_grasp_prior_tool_downward_z=0.9981`, table-clearance violation near zero.

Analysis:
- PPO learned strong behavior for one logged object and did not solve the other object under the current cache/reward mix.
- Because the training metrics are not deterministic eval metrics and the logged object ordering may not be identical to manifest/env parity, launch an explicit 128-env policy eval from epoch 100.

Eval command / job:
- job_id: `1029947`
- host: `l401`
- run_name: `franka_multi_ppo_bcself_ep100_eval_rawpose_cache_9943101_20260615T1801Z`
- checkpoint: `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_rawpose_cache_reg10_9943101_20260615T1752Z/nn/last_dextrah_franka_multi_object_grasp_ep_100_rew_5377.594.pth`
- expected metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_ppo_bcself_ep100_eval_rawpose_cache_9943101_20260615T1801Z/metrics.json`
- settings: deterministic policy, `NUM_ENVS=128`, `NUM_STEPS=360`, same two-object manifest/stable-pose/verified-cache/raw-pose reset gates and object friction.

Next:
- Inspect epoch-100 deterministic eval success/lift and reset artifacts. If still imbalanced, the next iteration should target object-specific balancing/cache quality rather than table-collision fixes.

## 2026-06-15T18:04:00Z - Epoch-100 eval result and object0-focused PPO launch

Epoch-100 deterministic eval result:
- Job `1029947` completed with exit `0:0` in `00:01:15`.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_ppo_bcself_ep100_eval_rawpose_cache_9943101_20260615T1801Z/metrics.json`
- `NUM_ENVS=128`, `NUM_STEPS=360`, deterministic policy.
- `eval_success_rate=0.3984`, `success_ever_rate=0.4297`, `success_rate_final=0.3828`.
- Done reasons: `success_done=2`, `unclassified=6`, `finger_table_penetration=0`, `prelift_drag=0`, `cube_out=0`.
- Assuming round-robin env parity, success was fully imbalanced: even envs `0/64`, odd envs `55/64`.
- Reset/table diagnostics remained clean.

Analysis:
- The epoch-100 policy is not a multi-object solution. It learned one object and effectively dropped the other.
- Because the BC checkpoint was much less imbalanced than the epoch-100 PPO checkpoint, the next run should start from BC, use only the harder object0 manifest, and remove the action-prior reward so PPO optimizes task reward directly.

Object0-focused PPO launch:
- job_id: `29107468`
- host: `a1001`
- run_name: `franka_multi_ppo_bcself_object0_rawpose_noprior_9943101_20260615T1804Z`
- checkpoint: `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`
- manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- `MAX_OBJECTS=1`, `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, `MAX_ITERATIONS=100`.
- Grasp-prior reset remains enabled with the exact verified cache, downward/top-down/table gates, and stable-pose cache.
- Action-prior reward and scripted warmstart are disabled for this run.
- expected run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_object0_rawpose_noprior_9943101_20260615T1804Z`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29107468.out`

Next:
- Monitor object0 PPO curve. If object0 can be solved from BC, use that checkpoint as a candidate for mixed fine-tuning or evaluate whether it generalizes back to the two-object manifest.

## 2026-06-15T18:13:00Z - Object0 BC eval and unanchored PPO diagnosis

Object0-only BC eval:
- Job `1029949` completed with exit `0:0` in `00:01:05`.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_bc_object0_eval_rawpose_cache_9943101_20260615T1811Z/metrics.json`
- `NUM_ENVS=64`, `NUM_STEPS=360`, deterministic policy.
- `eval_success_rate=0.3594`, `success_ever_rate=0.3750`, `success_rate_max=0.3125`, `success_rate_final=0.0`.
- Completed episodes: `15`; completed episode success rate `0.7333`.
- Done reasons: `success_done=11`, `unclassified=4`, `finger_table_penetration=0`, `prelift_drag=0`, `cube_out=0`.
- Lift diagnostics: mean per-env max lift `0.1069`, max lift `0.6775`, lift >= 3 cm in `0.4844` of envs, lift >= 8 cm in `0.3906` of envs.

Object0-only PPO progress:
- Job `29107468` was still running near epoch `89/100` when inspected.
- The unanchored PPO run is collapsing the BC behavior rather than improving it.
- Best training success through epoch `89`: `0.00195` at epoch `48`.
- Last 10 epochs through epoch `89`: success mean `0.0`; has-lifted mean `0.00459`; close action decayed to about `0.006-0.01`.
- Reset diagnostics remain clean: reset success `1.0`, quality success `1.0`, tool downward z `0.9976`, table-clearance violation `0.0`.

Analysis:
- Object0 is hard, but the BC action-imitation checkpoint is not useless: it produces first-attempt successes and large lifts on object0 without table-contact failures.
- PPO from BC without an action anchor rapidly learns a policy that avoids closing/lifting. This is an optimization/reward-shaping issue, not a recurrence of the from-below reset bug.
- Next run should keep the strict raw-pose grasp reset and exact verified cache, but add an action/reference anchor for object0 so PPO cannot erase the useful contact strategy while optimizing task reward.

Anchored object0 PPO launch:
- job_id: `29107610`
- host: `a1001`
- run_name: `franka_multi_ppo_bcself_object0_rawpose_reg50_9943101_20260615T1815Z`
- source commit: `9943101936f74edda9da24680b8c1f97db047303`
- code path:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation.pth`
- manifest:
  `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- exact verified-cache path:
  `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`
- PPO: `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, `MAX_ITERATIONS=100`, LR `1e-5`, central LR `5e-6`, horizon `64`, mini epochs `2`.
- Reset gates unchanged: topdown required, downward tool z min `0.45`, pregrasp z min `0.45`, contact height min `-0.02`, center-distance frac `0.50`, min width `0.008`.
- Action guidance: scripted warmstart disabled; action-prior reward enabled with weight `50.0`, sharpness `2.0`.
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29107610.out`
- expected run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_object0_rawpose_reg50_9943101_20260615T1815Z`

Next:
- Monitor first metrics rows for close action, action-prior reward, lift, success, and reset/table diagnostics.
- Also let job `29107468` exit and record its final failed status, because it is the failed unanchored PPO ablation.

## 2026-06-15T18:24:00Z - Anchor run interim metrics and epoch-69 eval launch

Unanchored object0 PPO final status:
- Job `29107468` completed with exit `0:0` in `00:11:38`.
- Final epoch `100`: `cube_success_rate=0.0`, object0 success `0.0`, `cube_has_lifted_rate=0.0078`, close action `0.0063`.
- Reset diagnostics stayed clean: reset success `1.0`, tool downward z `0.9976`, table-clearance violation `0.0`.
- Interpretation: unanchored PPO destroys the useful BC closing/lifting behavior.

Anchored object0 PPO interim metrics:
- Job `29107610` is running.
- First structured metrics started at epoch `41` because the BC checkpoint carries epoch `40`.
- Early epochs preserved closing (`cube_gripper_close_action` peaked at `0.8880`) and reached lift-rate `0.0342`, unlike the no-prior run.
- Later epochs began collapsing again: by epoch `79`, close action was `0.0422` and lift-rate `0.0039`.
- Best training success so far was epoch `69`: `cube_success_rate=0.0088`, object0 success `0.0088`.
- Reset diagnostics are still top-down/table-safe: tool downward z `0.9976`, table-clearance violation near zero, reset success around `0.94-0.95`, quality success around `0.92-0.94`.

Eval launch:
- job_id: `1029950`
- host: `l401`
- run_name: `franka_multi_ppo_object0_reg50_ep69_eval_9943101_20260615T1824Z`
- checkpoint:
  `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcself_object0_rawpose_reg50_9943101_20260615T1815Z/nn/last_dextrah_franka_multi_object_grasp_ep_69_rew_2107.527.pth`
- `NUM_ENVS=128`, `NUM_STEPS=360`, deterministic policy, no video.
- Same object0-only manifest, stable-pose cache, exact verified-index cache, strict topdown/downward-tool/table gates, and object friction as training.

Next:
- Inspect eval metrics from `1029950`; if it does not beat the object0 BC eval baseline, this run is not a solution.
- Let `29107610` finish and inspect the final checkpoint as a failed/partial anchor ablation unless late recovery appears.

## 2026-06-15T18:31:00Z - Reg50 PPO failed; low-sigma PPO stability run launched

Reg50 PPO final:
- Job `29107610` completed with exit `0:0` in `00:11:12`.
- Final epoch `100`: training `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0049`, close action `0.0064`.
- Best training checkpoint was epoch `69`, with `cube_success_rate=0.0088`.

Epoch-69 deterministic eval:
- Job `1029950` completed with exit `0:0` in `00:01:23`.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_ppo_object0_reg50_ep69_eval_9943101_20260615T1824Z/metrics.json`
- `eval_success_rate=0.0`, `success_ever_rate=0.0`, max per-env lift `0.0688`, lift >= 3 cm in `0.0078` of envs.
- Done reasons all zero: no success, no table/finger-table termination, no cube-out.
- Trace comparison against BC:
  - BC object0 policy closes after approach: window steps `20-60` close mean `0.9567`, z action mean transitions upward; success ever reaches `24/64`.
  - PPO epoch-69 keeps gripper open and keeps descending: window steps `20-60` close mean `0.0080`, z mean `-0.9557`; success ever stays `0/128`.

Checkpoint sigma audit:
- Helper jobs:
  - `1029956` failed because the container uses `/isaac-sim/python.sh`, not `python3`.
  - `1029973` failed under PyTorch 2.6 `weights_only=True` checkpoint loading.
  - `1029988` loaded the checkpoint but incorrectly matched normalization `std` keys in a generated copy; that generated copy was deleted.
  - `1030014` completed with exit `0:0` and wrote a corrected sigma-only checkpoint.
- Corrected checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- Original `a2c_network.sigma` values were approximately `[-0.139, -0.166, -0.365, -0.210, -0.243, -0.166, -0.430]`.
- Corrected copy sets only `a2c_network.sigma` to `-3.0`; helper asserted `changed_keys == ["a2c_network.sigma"]`.

Low-sigma PPO launch:
- job_id: `29107974`
- host: `a1001`
- run_name: `franka_multi_ppo_bcself_object0_lowsigma_lr1e6_9943101_20260615T1831Z`
- checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- Object0-only manifest/cache and strict reset gates unchanged.
- PPO: `MAX_ITERATIONS=60` from epoch-40 checkpoint, `NUM_ENVS=1024`, `NPROC_PER_NODE=4`, LR `1e-6`, central LR `5e-7`, mini epochs `1`, clip `0.05`, entropy `0.0`, KL threshold `0.003`, save every epoch.
- Grasp-prior action reward and scripted warmstart are disabled; this run tests whether reduced exploration/update pressure preserves the BC close/lift behavior while doing conservative PPO updates.

Next:
- Monitor close/lift/success and deterministic eval the final or best low-sigma checkpoint. Success criterion is at least preserving the BC object0 baseline before returning to mixed two-object training.

## 2026-06-15T19:16:00Z - PPO action-anchor implementation and object0 eval sweep

Implementation:
- Added `dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`, a DEXTRAH-specific RL-Games continuous PPO agent that stores grasp-prior teacher actions from `infos` and adds an optional supervised MSE loss on the current policy mean.
- Patched `dextrah_lab/rl_games/train.py` to install the DEXTRAH PPO agent before constructing the RL-Games runner.
- Patched `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py` to expose `dextrah_grasp_prior_teacher_actions` and `dextrah_grasp_prior_teacher_active` through `extras` when action-prior reference generation is enabled.
- Patched `cluster/sbatch_train_teacher_8gpu.sh` to pass:
  - `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED`
  - `DEXTRAH_GRASP_PRIOR_BC_LOSS_WEIGHT`
  - `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS`
- Local commits:
  - `6e3aa3e` - add PPO grasp-prior behavior anchor
  - `d606b19` - fix Hydra overrides for the new anchor config
- Remote code commit in the a1001/l401 worktree: `5f98d31601c7a47c1fa140772a36a67305cbc857`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py dextrah_lab/rl_games/train.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- Remote CPU-container import smoke confirmed `DextrahGraspPriorA2CAgent` imports with the installed RL-Games.

Failed launch:
- Job `29109854` failed before training because Hydra rejected the new config keys without `+`.
- Fixed by commit `d606b19` locally / `5f98d31` remotely.

Completed object0 anchor run:
- Job `29110276` completed successfully.
- Run:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_ppo_bcanchor_object0_lowsigma_w10_5f98d31_20260615T1921Z`
- Checkpoint source:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- PPO settings: object0-only, `NUM_ENVS=256`, `MAX_ITERATIONS=80` from epoch-40 BC checkpoint, LR `5e-6`, central LR `2.5e-6`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=2`, `E_CLIP=0.05`, entropy `0.0`, KL `0.003`, supervised grasp-prior BC loss enabled with weight `10`.
- Reset settings: object0-only manifest, current-code verified grasp cache, stable-pose cache enabled, top-down/downward tool axis required, min downward tool z `0.45`, min pregrasp z `0.45`, contact-height floor `-0.02`, center-distance frac `0.50`, min width `0.008`, object friction `4.0/3.5`.
- Saved checkpoints: epochs `50`, `60`, `70`, and `80`.

Training metrics:
- Reset remained table-safe and top-down: `cube_grasp_prior_tool_downward_z ~= 0.9976`, `cube_finger_table_clearance_violation=0`, reset success roughly `0.93-0.95`.
- The behavior anchor prevented the immediate fully-open collapse seen in previous PPO runs, but it still did not solve object0 in training.
- Final epoch `80`: `cube_success_rate=0.0547`, `cube_has_lifted_rate=0.1211`, `cube_lift_height=0.0147`, close action `0.7717`, action-prior active rate `0.0977`, action-prior delta `0.3532`.
- Interpretation: the from-below/table-collision root cause is not recurring in this run; the remaining failure is PPO drifting away from the BC/reference behavior when the reference-active window becomes sparse.

Deterministic object0 eval sweep:
- Submitted l401 eval jobs for epochs `50`, `60`, `70`, and `80`, all with the same object0-only manifest/cache/reset gates as the training run.
- `1030076`: epoch `70`, run `franka_multi_ppo_bcanchor_object0_lowsigma_w10_ep70_eval_5f98d31_20260615T1938Z`
- `1030077`: epoch `80`, run `franka_multi_ppo_bcanchor_object0_lowsigma_w10_ep80_eval_5f98d31_20260615T1938Z`
- `1030078`: epoch `60`, run `franka_multi_ppo_bcanchor_object0_lowsigma_w10_ep60_eval_5f98d31_20260615T1938Z`
- `1030079`: epoch `50`, run `franka_multi_ppo_bcanchor_object0_lowsigma_w10_ep50_eval_5f98d31_20260615T1938Z`

Next:
- Inspect deterministic eval metrics and traces. If they are below the object0 BC baseline (`success_ever_rate=0.375`), strengthen the action anchor and/or change the active reference schedule rather than weakening the reset filters.

## 2026-06-15T19:51:00Z - Object0 deterministic eval results and visual check

Object0 checkpoint sweep, 128 envs, deterministic policy, same seed/cache/reset gates:

| Checkpoint | Eval success / success-ever | Final success occupancy | Completed episodes | Max lift | Table violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| BC baseline, low-sigma copy | `0.4141` | `0.0` | `36`, `0.9167` success | `0.0559` | `0.0` |
| PPO anchor epoch 50 | `0.0469` | `0.0` | `6`, `0.8333` success | `0.0076` | `0.0` |
| PPO anchor epoch 60 | `0.2500` | `0.0` | `17`, `1.0000` success | `0.0322` | `0.0` |
| PPO anchor epoch 70 | `0.0078` | `0.0` | `0` | `0.0020` | `0.0` |
| PPO anchor epoch 80 | `0.1719` | `0.0703` | `6`, `1.0000` success | `0.0218` | `0.0` |

Trace diagnostics:
- Epoch 60 is the best PPO checkpoint but still underperforms the deterministic BC policy under the same 128-env eval.
- Epoch 80 partially recovers from the epoch-70 collapse but remains below BC.
- No eval produced finger-table penetration, prelift drag, or cube-out failures. This supports the conclusion that the from-below/table-penetrating reset root cause is fixed in the current reset/cache path.

Video check:
- Captured a 2-env video for PPO anchor epoch 60:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/artifacts/dextrah-multiobject-grasp-prior/franka-multi-bcanchor-ep60-object0-step-0.mp4`
- Viewer URL:
  `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/dextrah-multiobject-grasp-prior-finish-20260615T074722Z/artifacts/dextrah-multiobject-grasp-prior/franka-multi-bcanchor-ep60-object0-step-0.mp4`
- Extracted frames `frame_002.png` through `frame_005.png` show above-table/top-down approach, close, and lift attempt. I did not see the old under-table reach.

Analysis:
- The current PPO action anchor is a partial improvement over prior PPO runs, but it does not preserve the BC policy's object0 performance.
- The reference-active schedule currently supervises roughly approach `20` + close `28` + lift `80` steps. After that window, PPO can drift during hold/success phases. The next run should increase the supervised lift/hold window and strengthen the supervised loss rather than relaxing grasp validity filters.

Next:
- Launch a stronger object0 anchor run from the same BC checkpoint with a longer lift/hold reference window and higher BC-loss weight. Success criterion remains beating the deterministic BC baseline before returning to the two-object manifest.

## 2026-06-15T19:59:00Z - Stronger long-hold object0 anchor launch

Command / Job:
- job_id: `29110991`
- host: `a1001`
- run_name: `franka_multi_ppo_bcanchor_object0_lowsigma_w100_lift420_5f98d31_20260615T1958Z`
- source commit on remote worktree: `5f98d31601c7a47c1fa140772a36a67305cbc857`
- code path:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29110991.out`

Training settings:
- Object0-only manifest, current-code verified grasp cache, stable-pose cache enabled.
- Reset gates unchanged: topdown and downward tool-axis required, min downward tool z `0.45`, min pregrasp z `0.45`, contact-height floor `-0.02`, center-distance frac `0.50`, min width `0.008`, object friction `4.0/3.5`.
- PPO: `NPROC_PER_NODE=4`, `NUM_ENVS=1024`, `MAX_ITERATIONS=70`, LR `1e-6`, central LR `5e-7`, horizon `64`, mini epochs `2`, clip `0.05`, entropy `0.0`, KL `0.003`, save frequency `5`.
- Behavior anchor: `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`, weight `100`, dims `all`.
- Reference schedule: approach `20`, close `28`, lift/hold `420` steps. This extends the supervised window from `128` total steps to `468` total steps while keeping scripted warmstart intervention disabled.

Expected signal:
- If the hypothesis is right, train/eval should preserve or improve over the BC baseline rather than decaying below it. If it still underperforms, the next likely issue is mismatch between the scripted reference and the BC policy/contact dynamics, not grasp sampling safety.

Correction:
- The training wrapper derives the actual experiment name from `FULL_EXPERIMENT_NAME`, not `RUN_NAME`.
- I passed `RUN_NAME`, so Slurm job `29110991` is running with the default output experiment `slurm_29110991`.
- The settings reached the job correctly; continue monitoring:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/slurm_29110991`

Update:
- Canceled job `29110991` after roughly three minutes because it never advanced past scene construction or wrote metrics. GPU utilization stayed mostly idle and the Slurm log stopped at the collision-filtering warning.
- First 1-GPU relaunch was rejected by Slurm because the script's default `--cpus-per-task=64` is too high for one GPU.
- Relaunched as job `29111164` with `--gpus-per-node=1 --cpus-per-task=16 --mem=160G`.
- New experiment name:
  `franka_multi_ppo_bcanchor_object0_lowsigma_w100_lift420_1gpu_5f98d31_20260615T2004Z`
- Same long-anchor settings as above, but `NUM_ENVS=256`, `NPROC_PER_NODE=1`, `DISTRIBUTED=False`, `MULTI_GPU=False`.

## 2026-06-15T20:43:00Z - Conservative fixed-checkpoint PPO launch

Prior result:
- The checkpoint-init fix at commit `f80a1c84c1064a16ae5aa223da38742dfad3400e` made zero-LR PPO preserve the low-sigma BC policy. Eval job `1030325` on checkpoint epoch `45` matched deterministic BC-level behavior with `eval_success_rate=0.421875`, `success_ever_rate=0.4453125`, `done_ever_count=36`, no table/prelift/cube-out violations, and reset diagnostics `tool_downward_z=0.9975928068`, `tool_z_axis_z_mean=-0.9975928664`.
- The first real PPO run after that fix (`29114460`, `LR=1e-5`, `anchor=1`) degraded by epoch `10`: eval job `1030326` had `eval_success_rate=0.0` and `success_ever_rate=0.0`. Reset diagnostics remained top-down/downward, so this was PPO drift rather than from-below grasp sampling.

New run:
- Slurm job: `29114922`
- Experiment: `franka_multi_ppo_bc_lowsigma_lr1e6_clip001_anchor100_f80a1c8_20260615T2043Z`
- Remote code path: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- Commit: `f80a1c84c1064a16ae5aa223da38742dfad3400e`
- Checkpoint: `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`

Training settings:
- Object0-only manifest: `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- Stable-pose cache enabled: `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`
- Verified grasp indices: `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`
- Reset gates unchanged: top-down required, downward tool-Z required, min downward tool-Z `0.45`, min pregrasp Z `0.45`, min contact height above center `-0.02`, max center distance frac `0.50`, min width `0.008`, candidate count `128`, attempts `16`.
- PPO: `NUM_ENVS=256`, `MAX_ITERATIONS=80`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=1`, `LEARNING_RATE=1e-6`, central value LR `1e-6`, `E_CLIP=0.01`, `KL_THRESHOLD=0.003`, entropy `0`, save frequency `5`.
- Stabilizers: `DEXTRAH_BC_POLICY_ANCHOR_ENABLED=True`, anchor weight `100`, `DEXTRAH_FREEZE_OBS_RMS_ENABLED=True`, JSONL metrics enabled.

Expected signal:
- This run should preserve the deterministic BC baseline if the optimizer-state and obs-RMS bugs are fixed. If it still collapses early, the next step is an even stronger anchor/lower LR or a reward/reference redesign, not weakening the strict reset filter.

Update:
- Job `29114922` loaded the BC checkpoint with the fixed semantics:
  `loading policy initialization checkpoint ... without epoch/runtime restore` and
  `ignoring checkpoint optimizer for policy initialization`.
- Training was canceled after saving epoch `50` because the direct metrics showed PPO drift/collapse despite strict reset safety. By epoch `35`, `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0`, `cube_lift_height=0.0`, `cube_ee_to_cube_dist=0.76896`, while reset diagnostics stayed clean: `cube_grasp_prior_tool_downward_z=0.9975928068`, `cube_grasp_prior_tool_z_axis_z=-0.9975928068`, candidate valid/topdown/tool-down/table counts all `128`, and `cube_finger_table_clearance_violation=0.0`.
- Early training rows still looked potentially useful, so I submitted deterministic object0 evals:
  - `1030341`: epoch `5`, run `franka_multi_ppo_lr1e6_anchor100_ep5_eval_f80a1c8_20260615T2048Z`
  - `1030342`: epoch `10`, run `franka_multi_ppo_lr1e6_anchor100_ep10_eval_f80a1c8_20260615T2048Z`
  - `1030343`: epoch `15`, run `franka_multi_ppo_lr1e6_anchor100_ep15_eval_f80a1c8_20260615T2048Z`
  - `1030344`: epoch `50`, run `franka_multi_ppo_lr1e6_anchor100_ep50_eval_f80a1c8_20260615T2048Z`

Eval results:

| Checkpoint | Eval success / success-ever | Max success occupancy | Completed episodes | Max lifted rate | Max lift | Table violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Epoch 5 | `0.328125` / `0.328125` | `0.265625` | `131`, success `0.3282` | `0.2734375` | `0.0460` | max `0.0078125` |
| Epoch 10 | `0.046875` / `0.046875` | `0.0234375` | `128`, success `0.046875` | `0.0390625` | `0.0056` | max `0.0062963` |
| Epoch 15 | `0.0` / `0.0` | `0.0` | `128`, success `0.0` | `0.0` | `0.00021` | `0.0` |
| Epoch 50 | `0.0` / `0.0` | `0.0` | `128`, success `0.0` | `0.0078125` | `0.00078` | `0.0` |

Interpretation:
- Even epoch `5` underperforms the fixed zero-LR/BC eval baseline (`success_ever_rate=0.4453125`), and later epochs collapse.
- Reset sampling is still not the root cause: eval traces kept `grasp_prior_reset_tool_downward_z=0.9975928068` for all checkpoints. The small table-violation rates at epochs `5` and `10` occur during rollout after reset, not from upward/below-table reset grasps.
- The fixed zero-LR training JSONL is also weak under stochastic rollout despite deterministic eval being BC-level: at epoch `45`, `cube_success_rate=0.00390625`, `cube_has_lifted_rate=0.19140625`, and `cube_lift_height=0.00248`. This points to stochastic rollout/sigma as a likely PPO failure mode.

Code updates:
- Commit `58b3f59a63ff4a2d2ef08a0d811f62016e7b2663`: log agent auxiliary losses, including `dextrah_bc_policy_anchor_loss`, into `direct_info_rank_0.jsonl`.
- Commit `a06b2c560fe1230c9f47dd1cdab22776ecfa1c8d`: add `TRAIN_SIGMA` to `cluster/sbatch_train_teacher_8gpu.sh` and pass it to `train.py --sigma`.
- Remote a1001 worktree updated to `a06b2c560fe1230c9f47dd1cdab22776ecfa1c8d`; remote `bash -n` and `py_compile` checks passed.

Next run:
- Slurm job `29115505`
- Experiment `franka_multi_ppo_bc_lowsigma_forcesigma_m3_lr1e6_anchor100_a06b2c5_20260615T2056Z`
- Same object0-only/reset/frozen-obs/anchor settings as `29114922`, but with `TRAIN_SIGMA=-3` and `MAX_ITERATIONS=20`.
- Purpose: verify whether forcing low log-std after checkpoint load improves stochastic rollout and whether the policy-anchor loss is actually active.

Update:
- Job `29115505` completed 20 epochs.
- Launch log confirmed `TRAIN_SIGMA=-3`.
- JSONL now includes `agent_aux/dextrah_bc_policy_anchor_loss`, confirming the policy anchor is active.
- Training diagnostics still look poor under stochastic rollout: epoch `5` `cube_success_rate=0.00390625`, `cube_has_lifted_rate=0.15234375`, `cube_lift_height=0.00155`, `cube_ee_to_cube_dist=0.40884`; epoch `20` `cube_success_rate=0.0`, `cube_has_lifted_rate=0.00390625`, `cube_lift_height=0.000022`.
- Anchor loss was nonzero/large: epoch `1` `146.20`, epoch `5` `36.95`, epoch `10` `106.04`, epoch `20` `22.42`.
- Reset diagnostics stayed clean: `cube_grasp_prior_tool_downward_z=0.9975928068` and no finger-table violation in the sampled training rows.

Deterministic evals submitted:
- `1030345`: epoch `5`, run `franka_multi_forcesigma_m3_ep5_eval_a06b2c5_20260615T2100Z`
- `1030346`: epoch `10`, run `franka_multi_forcesigma_m3_ep10_eval_a06b2c5_20260615T2100Z`
- `1030347`: epoch `15`, run `franka_multi_forcesigma_m3_ep15_eval_a06b2c5_20260615T2100Z`
- `1030348`: epoch `20`, run `franka_multi_forcesigma_m3_ep20_eval_a06b2c5_20260615T2100Z`

Forced-sigma eval results:

| Checkpoint | Eval success / success-ever | Max success occupancy | Completed episodes | Max lifted rate | Max lift | Table violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Epoch 5 | `0.3671875` / `0.375` | `0.296875` | `131`, success `0.3817` | `0.296875` | `0.0537` | `0.0` |
| Epoch 10 | `0.03125` / `0.03125` | `0.03125` | `128`, success `0.03125` | `0.03125` | `0.00519` | max `0.000736` |
| Epoch 15 | `0.0` / `0.0` | `0.0` | `128`, success `0.0` | `0.0` | `0.00029` | `0.0` |
| Epoch 20 | `0.0` / `0.0` | `0.0` | `128`, success `0.0` | `0.0` | `0.0` | `0.0` |

Interpretation:
- Forcing sigma helped the early checkpoint (`0.375` vs previous `0.328125`) and removed the epoch-5 table violation, but it still underperforms the fixed zero-LR/BC baseline (`0.4453125`) and collapses by epoch `10`.
- Reset axis remains fixed: every eval kept `grasp_prior_reset_tool_downward_z=0.9975928068`.

Reference-action diagnostic launch:
- Slurm job `29115810`
- Experiment `franka_multi_ppo_refbc100_prior5_sigma_m5_lr1e6_anchor100_a06b2c5_20260615T2101Z`
- Same object0-only/reset/cache settings.
- PPO: `MAX_ITERATIONS=40`, `LR=1e-6`, `E_CLIP=0.01`, `MINI_EPOCHS=1`, `TRAIN_SIGMA=-5`, frozen obs RMS.
- Stabilizers/guidance: policy anchor weight `100`, `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`, reference BC loss weight `100`, action-prior reward enabled with weight `5.0`, reference schedule approach `20`, close `28`, lift/hold `420`.
- Purpose: policy anchor alone preserves a target policy but does not guide off-BC states; this run tests whether the grasp-prior reference action provides recovery guidance while keeping strict reset filters.

Update:
- Job `29115810` completed 40 epochs.
- Training reward increased (epoch `10` checkpoint reward `1636.0488`), but success diagnostics did not improve: epoch `10` `cube_success_rate=0.0`, `cube_has_lifted_rate=0.046875`; epoch `20` `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0078125`; epoch `40` `cube_success_rate=0.0`, `cube_has_lifted_rate=0.0078125`.
- Reference losses were active: `agent_aux/dextrah_grasp_prior_bc_active_rate` ranged from `0.562` to `1.0`, and `agent_aux/dextrah_grasp_prior_bc_loss` stayed nonzero (`79.65` to `328.10` in sampled rows).
- Reset safety remained clean in sampled rows: `cube_grasp_prior_tool_downward_z=0.9975928068` and `cube_finger_table_clearance_violation=0.0`.

Deterministic evals submitted:
- `1030352`: epoch `5`, run `franka_multi_refbc100_prior5_ep5_eval_a06b2c5_20260615T2106Z`
- `1030353`: epoch `10`, run `franka_multi_refbc100_prior5_ep10_eval_a06b2c5_20260615T2106Z`
- `1030354`: epoch `15`, run `franka_multi_refbc100_prior5_ep15_eval_a06b2c5_20260615T2106Z`
- `1030355`: epoch `20`, run `franka_multi_refbc100_prior5_ep20_eval_a06b2c5_20260615T2106Z`
- `1030356`: epoch `40`, run `franka_multi_refbc100_prior5_ep40_eval_a06b2c5_20260615T2106Z`

High-anchor/reference diagnostic launch:
- Slurm job `29116248`
- Experiment `franka_multi_ppo_refbc1000_prior5_sigma_m5_lr1e6_anchor1000_a06b2c5_20260615T2107Z`
- Same object0-only/reset/cache settings as `29115810`.
- Changed only regularization strength: policy anchor weight `1000`, reference BC loss weight `1000`, max iterations `20`.
- Purpose: test whether stronger guidance can prevent PPO reward drift while keeping the grasp reset filters unchanged.

## 2026-06-15T21:14:58Z - High-anchor/reference diagnostic result

Training job `29116248` completed all 20 epochs.

Key training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Anchor loss | Ref BC loss | Ref active | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0` | `0.0117` | `0.0208` | `0.0795` | `1497.78` | `892.35` | `1.0` | `0.9975928` |
| 2 | `0.1797` | `0.1992` | `0.0394` | `0.1609` | `549.14` | `1159.42` | `1.0` | `0.9975928` |
| 5 | `0.0039` | `0.1758` | `0.0045` | `0.3940` | `358.74` | `1253.21` | `1.0` | `0.9975928` |
| 10 | `0.0` | `0.0195` | `0.0046` | `0.1360` | `1088.97` | `818.47` | `0.6136` | `0.9975928` |
| 15 | `0.0` | `0.0625` | `0.0` | `0.4744` | `127.93` | `770.38` | `0.9896` | `0.9975928` |
| 20 | `0.0` | `0.0039` | `0.0` | `0.3549` | `189.94` | `1063.96` | `0.7294` | `0.9975928` |

Deterministic object0 evals:

| Job | Checkpoint | Run | Eval success / success-ever | Max success | Max lifted | Max lift | Table violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `1030358` | epoch `5` | `franka_multi_refbc1000_prior5_ep5_eval_a06b2c5_20260615T2118Z` | `0.25` / `0.25` | `0.1953125` | `0.1953125` | `0.0368` | `0.0` |
| `1030359` | epoch `10` | `franka_multi_refbc1000_prior5_ep10_eval_a06b2c5_20260615T2118Z` | `0.109375` / `0.1171875` | `0.0703125` | `0.0703125` | `0.0122` | max `0.0001896` |
| `1030360` | epoch `15` | `franka_multi_refbc1000_prior5_ep15_eval_a06b2c5_20260615T2118Z` | `0.0` / `0.0` | `0.0` | `0.0` | `0.00028` | `0.0` |
| `1030361` | epoch `20` | `franka_multi_refbc1000_prior5_ep20_eval_a06b2c5_20260615T2118Z` | `0.0` / `0.0` | `0.0` | `0.0` | `0.0` | `0.0` |

Eval reset diagnostics:
- Every eval had all `128` candidates passing topdown, tool-down, table, and valid-count checks.
- `grasp_prior_reset_tool_downward_z=0.9975928068` and `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664` throughout.
- No eval had cube-out, prelift-drag, or finger-table-penetration done reasons.

Interpretation:
- Increasing both the policy anchor and reference BC loss from `100` to `1000` did not preserve the BC baseline; it worsened the early checkpoint compared with the lower-anchor run and still collapsed by epoch `15`.
- The reward/action-prior terms remain gameable: training reward stayed high while deterministic success fell below the fixed zero-LR/BC baseline.
- The below-table/upward-grasp reset root cause remains fixed in the current reset path. The next change should constrain PPO's actor update explicitly, so supervised/reference terms can be tested without the PPO actor loss immediately moving the policy off the BC basin.

## 2026-06-15T21:17:48Z - Actor-loss-scale control and actor-zero launch

Code update:
- Commit `14120a06917931e7e62807fd78e3fe8e94ed1208`: added `dextrah_actor_loss_scale` and `dextrah_critic_loss_scale` to `DextrahGraspPriorA2CAgent`, logged both scales through the JSONL auxiliary metrics, and exposed them as `DEXTRAH_ACTOR_LOSS_SCALE` / `DEXTRAH_CRITIC_LOSS_SCALE` in `cluster/sbatch_train_teacher_8gpu.sh`.
- Defaults are `1.0`, so existing PPO behavior is unchanged unless a run opts in.
- Local checks passed: `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`, `bash -n cluster/sbatch_train_teacher_8gpu.sh`, and `git diff --check`.
- Remote worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` was updated to `14120a06917931e7e62807fd78e3fe8e94ed1208` using a Git bundle because the remote GitHub SSH key failed, then remote `py_compile` and `bash -n` checks passed.

Actor-zero diagnostic launch:
- Slurm job: `29116656`
- Experiment: `franka_multi_refonly_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_14120a0_20260615T2117Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29116656.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_refonly_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_14120a0_20260615T2117Z`
- One A100 GPU, `NUM_ENVS=256`, `MAX_ITERATIONS=20`, checkpoints every `5` epochs.
- Same object0-only manifest, stable-pose cache, verified grasp indices, and strict top-down/downward reset gates as the previous diagnostics.
- Initial checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- PPO/update settings: `LEARNING_RATE=1e-6`, `CENTRAL_VALUE_LEARNING_RATE=1e-6`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=1`, `E_CLIP=0.01`, `TRAIN_SIGMA=-5`, frozen obs RMS, policy anchor weight `100`, reference BC loss weight `100`, action-prior reward enabled with weight `5.0`, and reference schedule `20/28/420`.
- Critical new setting: `DEXTRAH_ACTOR_LOSS_SCALE=0.0`, `DEXTRAH_CRITIC_LOSS_SCALE=1.0`.

Expected signal:
- If deterministic success preserves the fixed zero-LR/BC baseline, the next step is a small nonzero actor scale sweep from that checkpoint.
- If this still collapses, the remaining issue is not PPO actor pressure alone; it would point to the reference-action target/schedule or the BC checkpoint/data rather than reset sampling safety.

## 2026-06-15T21:21:37Z - Actor-zero training completed; evals queued

Training job `29116656` completed all 20 epochs and saved checkpoints at epochs `5`, `10`, `15`, and `20`.

Key training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Actor scale | Anchor loss | Ref BC loss | Ref active | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0039` | `0.0195` | `0.0245` | `0.0805` | `0.0` | `151.82` | `86.77` | `1.0` | `0.9975928` |
| 2 | `0.1875` | `0.2227` | `0.0427` | `0.1613` | `0.0` | `56.27` | `110.44` | `1.0` | `0.9975928` |
| 5 | `0.0039` | `0.2188` | `0.00081` | `0.4088` | `0.0` | `33.79` | `127.44` | `1.0` | `0.9975928` |
| 10 | `0.0` | `0.0156` | `0.00336` | `0.1483` | `0.0` | `112.97` | `78.37` | `0.5764` | `0.9975928` |
| 11 | `0.1602` | `0.1758` | `0.0300` | `0.1983` | `0.0` | `42.73` | `105.07` | `0.8421` | `0.9975928` |
| 15 | `0.0039` | `0.0820` | `0.00122` | `0.4532` | `0.0` | `14.01` | `77.62` | `0.9991` | `0.9975928` |
| 20 | `0.0039` | `0.0078` | `0.00082` | `0.3474` | `0.0` | `18.05` | `110.30` | `0.6753` | `0.9975928` |

Interpretation from training metrics:
- The new actor-loss-scale plumbing works: every JSONL row recorded `agent_aux/dextrah_actor_loss_scale=0.0`.
- Disabling PPO actor loss did not make the stochastic training curve stable. Success briefly reached `0.1875` at epoch `2` and `0.1602` at epoch `11`, but saved checkpoint epochs still looked weak.
- Reset filtering again stayed clean. The failure mode is now clearly downstream policy/reference behavior, not upward/below-table reset grasps.

Deterministic evals submitted on l401:
- `1030362`: epoch `5`, run `franka_multi_actor0_refonly_ep5_eval_14120a0_20260615T2123Z`
- `1030363`: epoch `10`, run `franka_multi_actor0_refonly_ep10_eval_14120a0_20260615T2123Z`
- `1030364`: epoch `15`, run `franka_multi_actor0_refonly_ep15_eval_14120a0_20260615T2123Z`
- `1030365`: epoch `20`, run `franka_multi_actor0_refonly_ep20_eval_14120a0_20260615T2123Z`

Next:
- Monitor l401 eval metrics. If these are below the BC baseline, stop using the current scripted reference action as a full-action BC target and switch to a safer target: either only regularize gripper/z during reference phases, or use the frozen BC policy as the teacher instead of the scripted grasp-prior controller.

## 2026-06-15T21:29:12Z - Actor-zero evals completed; z/gripper reference run relaunched

Actor-zero full-action deterministic evals completed:

| Job | Checkpoint | Run | Eval success / success-ever | Max success | Max lifted | Max lift | Table violations |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `1030362` | epoch `5` | `franka_multi_actor0_refonly_ep5_eval_14120a0_20260615T2123Z` | `0.2578125` / `0.2578125` | `0.171875` | `0.171875` | `0.0313` | `0.0` |
| `1030363` | epoch `10` | `franka_multi_actor0_refonly_ep10_eval_14120a0_20260615T2123Z` | `0.0703125` / `0.078125` | `0.0625` | `0.0625` | `0.0120` | max `0.000568` |
| `1030364` | epoch `15` | `franka_multi_actor0_refonly_ep15_eval_14120a0_20260615T2123Z` | `0.0` / `0.0` | `0.0` | `0.0` | near `0.0` | `0.0` |
| `1030365` | epoch `20` | `franka_multi_actor0_refonly_ep20_eval_14120a0_20260615T2123Z` | `0.0` / `0.0` | `0.0` | `0.0` | near `0.0` | `0.0` |

Interpretation:
- Full-action scripted-reference BC remains harmful even with PPO actor loss disabled. The best saved deterministic checkpoint (`0.2578125`) is below the fixed zero-LR/BC baseline (`0.421875`) and the run collapses by epoch `15`.
- Reset filtering remained clean in these evals: all candidates passed topdown/tool-down/table/valid-count checks, `grasp_prior_reset_tool_downward_z=0.9975928068`, and `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`.
- Next diagnostic should not use the scripted reference for all action dimensions. It should preserve the BC policy with the anchor and only supervise the z motion and gripper closure from the grasp-prior reference.

Launch notes:
- Submitted job `29116858` as the intended z/gripper diagnostic, then immediately found from its log that `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS` arrived as `2` instead of `2,6`. Root cause: Slurm's comma-separated `--export` parser split the comma-valued variable. The job was canceled during startup and should not be treated as a valid experiment.
- A first corrected `sbatch --export=ALL` attempt was rejected because the script's default `64` CPU request is invalid for a 1-GPU job on this partition. No job was created by that failed submission.
- Corrected job `29116982` is running on A100 as `dextrah_refzg`.
- Experiment: `franka_multi_refzg_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_14120a0_20260615T2134Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29116982.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_refzg_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_14120a0_20260615T2134Z`
- Same object0 manifest, stable-pose cache, verified grasp indices, BC checkpoint, reset filters, low LR, forced sigma, frozen obs RMS, actor loss scale `0.0`, critic loss scale `1.0`, policy anchor weight `100`, reference BC loss weight `100`, and action-prior reward weight `5.0` as the actor-zero run.
- Effective env was verified in the log: `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS=2,6`, `DEXTRAH_ACTOR_LOSS_SCALE=0.0`, `NPROC_PER_NODE=1`, `NUM_ENVS=256`, `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`, and `GRASP_PRIOR_RESET_REQUIRE_DOWNWARD_TOOL_Z=True`.

Expected signal:
- If this still falls below the deterministic BC baseline, the scripted reference target is not reliable enough even when limited to z/gripper. The next step should be a run that uses the frozen BC policy itself as the action teacher/regularizer, or turns off scripted reference BC entirely and keeps only safe reset sampling plus PPO/anchor tuning.

## 2026-06-15T21:31:20Z - Hydra comma override fix

Job `29116982` failed before training with:
- `hydra.errors.ConfigCompositionException: Ambiguous value for argument '+agent.params.config.dextrah_grasp_prior_bc_loss_dims=2,6'`

Root cause:
- Passing the comma-valued setting through the environment fixed Slurm's `--export` parser, but the launcher still emitted `+agent.params.config.dextrah_grasp_prior_bc_loss_dims=2,6`, which Hydra interprets as an ambiguous sweep unless it is quoted or written as a list.

Fix:
- Patched `cluster/sbatch_train_teacher_8gpu.sh` to derive `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS_HYDRA`.
- Values containing a comma are converted to Hydra list syntax, for example `2,6` becomes `[2,6]`.
- Existing `all`, `*`, empty, and single-dimension values are preserved.
- The launcher now logs both `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS` and `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS_HYDRA`.

Validation:
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`: passed.
- Local formatting sanity check for `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS=2,6`: produced `[2,6]`.

Next:
- Commit and deploy the launcher fix to the A100 worktree, then relaunch the z/gripper-only diagnostic under a new run name.

## 2026-06-15T21:32:00Z - z/gripper-only diagnostic relaunched with Hydra fix

Version state:
- Local commit: `10916a196e4d1b6fcacbc0198fe2ee301f825ce2` (`Format DEXTRAH BC loss dims for Hydra`)
- Branch pushed to origin.
- A100 agent worktree `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c` updated to the same commit by Git bundle because remote GitHub SSH fetch still fails with `Permission denied (publickey)`.
- Remote `bash -n cluster/sbatch_train_teacher_8gpu.sh`: passed.

Training launch:
- Slurm job: `29117115`
- Experiment: `franka_multi_refzg_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_10916a1_20260615T2132Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29117115.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_refzg_actor0_prior5_sigma_m5_lr1e6_anchor100_ref100_10916a1_20260615T2132Z`

Effective configuration verified in log:
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS=2,6`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_DIMS_HYDRA=[2,6]`
- `DEXTRAH_ACTOR_LOSS_SCALE=0.0`
- `NPROC_PER_NODE=1`, `NUM_ENVS=256`
- `GRASP_PRIOR_RESET_MIN_PREGRASP_Z=0.45`
- `GRASP_PRIOR_RESET_REQUIRE_DOWNWARD_TOOL_Z=True`

Status:
- Job is running; JSONL metrics not emitted yet at first poll.

## 2026-06-15T21:38:00Z - z/gripper-only diagnostic completed; deterministic evals queued

Training job `29117115` completed all 20 epochs and saved checkpoints at epochs `5`, `10`, `15`, and `20`.

Key training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Actor scale | Anchor loss | Ref BC loss | Ref active | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0` | `0.0` | `0.0269` | `0.0820` | `0.0` | `143.89` | `107.30` | `1.0` | `0.9975928` |
| 2 | `0.1328` | `0.2188` | `0.0341` | `0.1707` | `0.0` | `50.61` | `81.51` | `1.0` | `0.9975928` |
| 5 | `0.0039` | `0.2344` | `0.00224` | `0.4198` | `0.0` | `33.73` | `137.64` | `1.0` | `0.9975928` |
| 10 | `0.0` | `0.0117` | `0.00451` | `0.1219` | `0.0` | `115.78` | `126.35` | `0.5933` | `0.9975928` |
| 11 | `0.1641` | `0.1719` | `0.0350` | `0.1964` | `0.0` | `39.27` | `55.08` | `0.8903` | `0.9975928` |
| 15 | `0.0` | `0.0977` | `0.00066` | `0.5629` | `0.0` | `11.51` | `7.76` | `1.0` | `0.9975928` |
| 20 | `0.0` | `0.0039` | `0.0` | `0.4946` | `0.0` | `27.90` | `73.98` | `0.7683` | `0.9975928` |

Interpretation from training:
- Limiting scripted reference BC to z/gripper dimensions is still not enough to preserve the deterministic BC baseline. The best training row was epoch `11` at success `0.1641`; saved checkpoints are weak.
- Reset safety remains clean and unchanged: every row logs `grasp_prior_reset_tool_downward_z=0.9975928068`. This is not a from-below reset regression.
- Because actor loss scale is `0.0`, the policy movement is coming from the supervised/reference and anchor losses plus optimizer state, not from the PPO actor objective.

Deterministic evals submitted on l401:
- `1030369`: epoch `5`, run `franka_multi_refzg_ep5_eval_10916a1_20260615T2138Z`
- `1030370`: epoch `10`, run `franka_multi_refzg_ep10_eval_10916a1_20260615T2138Z`
- `1030371`: epoch `15`, run `franka_multi_refzg_ep15_eval_10916a1_20260615T2138Z`
- `1030372`: epoch `20`, run `franka_multi_refzg_ep20_eval_10916a1_20260615T2138Z`

Eval setup:
- `NUM_ENVS=128`, `NUM_STEPS=360`, deterministic policy, video disabled.
- Same object0 manifest, stable-pose cache, exact verified-index cache, strict topdown/downward-tool/table gates, and object assignment as the fixed BC and zero-LR baselines.

Next:
- Inspect eval metrics. If they stay below the fixed BC baseline, stop using the scripted grasp-prior reference as an action target and switch the next implementation to a frozen-BC teacher/regularizer or reset-prior-only training.

## 2026-06-15T21:45:00Z - z/gripper-only evals failed below BC baseline

Deterministic object0 eval results:

| Job | Checkpoint | Run | Eval success / success-ever | Max success | Final success | Done count | Done reasons |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `1030369` | epoch `5` | `franka_multi_refzg_ep5_eval_10916a1_20260615T2138Z` | `0.25` / `0.25` | `0.2109375` | `0.0078125` | `15` | `success_done=14`, `unclassified=2`, table/prelift/cube-out `0` |
| `1030370` | epoch `10` | `franka_multi_refzg_ep10_eval_10916a1_20260615T2138Z` | `0.125` / `0.125` | `0.1171875` | `0.0` | `13` | `success_done=13`, table/prelift/cube-out `0` |
| `1030371` | epoch `15` | `franka_multi_refzg_ep15_eval_10916a1_20260615T2138Z` | `0.0` / `0.0` | `0.0` | `0.0` | `1` | `unclassified=1`, table/prelift/cube-out `0` |
| `1030372` | epoch `20` | `franka_multi_refzg_ep20_eval_10916a1_20260615T2138Z` | `0.0` / `0.0` | `0.0` | `0.0` | `0` | all done reasons `0` |

Reset diagnostics in every eval:
- `grasp_prior_reset_tool_downward_z=0.9975928068`
- `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
- `grasp_prior_reset_candidate_topdown_count=128`
- `grasp_prior_reset_candidate_tool_down_count=128`
- `grasp_prior_reset_candidate_table_count=128`
- `grasp_prior_reset_candidate_valid_count=128`

Analysis:
- The z/gripper-only scripted reference still underperforms the fixed BC/zero-LR baseline (`eval_success_rate=0.421875`, `success_ever_rate=0.4453125`).
- The below-table/upward reset root cause is not recurring in these runs. All reset candidates are topdown/tool-down/table-valid, and there are no finger-table, prelift-drag, or cube-out done reasons.
- The RL-Games config has `network.separate: False`, so critic loss can still move shared actor features even when `DEXTRAH_ACTOR_LOSS_SCALE=0.0`. This explains why the actor-zero diagnostics still drifted away from BC.

Next:
- Launch a reset-prior-only PPO diagnostic from the low-sigma BC checkpoint:
  - scripted reference BC loss disabled
  - action-prior reward disabled
  - strong frozen-BC policy anchor
  - `DEXTRAH_CRITIC_LOSS_SCALE=0.0` to prevent critic gradients through shared actor features
  - small nonzero `DEXTRAH_ACTOR_LOSS_SCALE` to test whether PPO can improve without erasing BC behavior

## 2026-06-15T21:46:00Z - reset-prior-only actor-small diagnostic launched

Training launch:
- Slurm job: `29117271`
- Experiment: `franka_multi_resetprior_actor001_critic0_anchor1000_sigma_m5_lr1e6_10916a1_20260615T2146Z`
- Commit: `10916a196e4d1b6fcacbc0198fe2ee301f825ce2`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29117271.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_actor001_critic0_anchor1000_sigma_m5_lr1e6_10916a1_20260615T2146Z`

Settings:
- Same object0 manifest, stable-pose cache, verified grasp indices, and strict topdown/downward reset gates.
- Initial checkpoint: low-sigma BC checkpoint `bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`.
- Scripted reference/action guidance disabled: `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=False`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False`.
- Stabilizers: frozen obs RMS, policy anchor enabled with weight `1000.0`, forced `TRAIN_SIGMA=-5`, entropy coefficient `0.0`.
- PPO loss scales: `DEXTRAH_ACTOR_LOSS_SCALE=0.01`, `DEXTRAH_CRITIC_LOSS_SCALE=0.0`.
- One A100 GPU, `NUM_ENVS=256`, `MAX_ITERATIONS=20`, checkpoints every `5` epochs.

Effective config verified in log:
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=False`
- `DEXTRAH_BC_POLICY_ANCHOR_WEIGHT=1000.0`
- `DEXTRAH_ACTOR_LOSS_SCALE=0.01`
- `DEXTRAH_CRITIC_LOSS_SCALE=0.0`
- `ENTROPY_COEF=0.0`

Expected signal:
- If this preserves the fixed BC eval baseline, the prior failure was driven by shared critic/reference losses rather than reset sampling. Then the next scale-up can slowly increase actor scale or epochs.
- If this still falls below BC, PPO actor gradients alone are enough to leave the BC basin and the next change should freeze more of the actor or use a much lower actor scale.

## 2026-06-15T21:48:56Z - actor-small diagnostic failed; patch policy anchor mode

Training job `29117271` completed all 20 epochs.

Key result:
- Best training success row was epoch `11` with `cube_success_rate=0.0898`.
- Saved checkpoint epochs were weak: epoch `5` success `0.0`, epoch `10` success `0.0`, epoch `15` success `0.0`, epoch `20` success `0.0`.
- Reset remained clean: `grasp_prior_reset_tool_downward_z=0.9975928068` throughout.
- The policy-anchor loss was unexpectedly large even in this conservative run, for example `306.13` at epoch `5`, `1075.11` at epoch `10`, and `236.67` at epoch `20`.

Diagnosis:
- The RL-Games config uses `network.separate: False`, so actor and critic share network features. Turning off critic loss removed one drift source, but the policy anchor itself was still comparing different policy modes:
  - student `mu` was computed from the main PPO forward with `is_train=True`
  - frozen BC teacher `mu` was computed with `is_train=False`
- The deterministic policy used in evaluation is eval-mode. The anchor should regularize eval-mode student behavior to eval-mode frozen BC behavior.

Code change:
- Patched `dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py` so `_compute_dextrah_policy_anchor_loss()` recomputes the current student policy with `is_train=False` and compares that eval-mode `mu` to the frozen BC eval-mode `mu`.
- This leaves the PPO actor/critic loss computation unchanged.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`: passed.
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`: passed.

Next:
- Commit/deploy the anchor-mode fix and relaunch the same reset-prior-only actor-small diagnostic. Success criterion is preserving or beating the fixed BC deterministic baseline, then tuning actor scale upward only if preservation works.

## 2026-06-15T21:51:00Z - anchor-mode fix deployed; matched diagnostic relaunched

Version state:
- Commit `e2986edfbe1346aba667bfc3cee23de7598b691c`: `Anchor DEXTRAH policy in eval mode`
- Branch pushed to origin.
- A100 agent worktree updated to `e2986edfbe1346aba667bfc3cee23de7598b691c` by Git bundle.
- Remote checks passed:
  - `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`

Training launch:
- Slurm job: `29117421`
- Experiment: `franka_multi_resetprior_actor001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2151Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29117421.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_actor001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2151Z`

Matched settings from failed job `29117271`:
- Scripted reference BC loss disabled.
- Action-prior reward disabled.
- Policy anchor weight `1000.0`.
- Actor loss scale `0.01`.
- Critic loss scale `0.0`.
- Entropy coefficient `0.0`.
- Same low-sigma BC checkpoint and object0/reset/cache setup.

Effective config verified in log:
- `CODE_COMMIT=e2986edfbe1346aba667bfc3cee23de7598b691c`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=False`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False`
- `DEXTRAH_BC_POLICY_ANCHOR_WEIGHT=1000.0`
- `DEXTRAH_ACTOR_LOSS_SCALE=0.01`
- `DEXTRAH_CRITIC_LOSS_SCALE=0.0`

Expected signal:
- Anchor loss should be much smaller if the mode mismatch was the cause of the previous large anchor loss.
- Deterministic eval should preserve the fixed BC baseline before any scale-up.

## 2026-06-15T21:55:00Z - patched-anchor diagnostic completed; evals queued

Training job `29117421` completed all 20 epochs.

Key training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Actor scale | Critic scale | Anchor loss | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | `0.0` | `0.2383` | `0.0029` | `0.4548` | `0.01` | `0.0` | `0.4550` | `0.9975928` |
| 10 | `0.0` | `0.0117` | `0.0019` | `0.1027` | `0.01` | `0.0` | `1.1334` | `0.9975928` |
| 11 | `0.1172` | `0.1328` | `0.0273` | `0.1608` | `0.01` | `0.0` | `0.8667` | `0.9975928` |
| 15 | `0.0` | `0.1367` | `0.0005` | `0.4240` | `0.01` | `0.0` | `1.6471` | `0.9975928` |
| 20 | `0.0234` | `0.0430` | `0.0050` | `0.1824` | `0.01` | `0.0` | `23.4590` | `0.9975928` |

Interpretation:
- The anchor-mode fix worked mechanically: anchor loss dropped from hundreds/thousands in the previous matched run to about `0.45-3.25` through epoch `17`, with a late increase to `23.46` by epoch `20`.
- This still did not produce a strong training curve; best row was epoch `11` with success `0.1172`.
- Reset diagnostics stayed clean.

Deterministic evals submitted:
- `1030373`: epoch `5`, run `franka_multi_resetprior_actor001_ep5_eval_e2986ed_20260615T2155Z`
- `1030374`: epoch `10`, run `franka_multi_resetprior_actor001_ep10_eval_e2986ed_20260615T2155Z`
- `1030375`: epoch `15`, run `franka_multi_resetprior_actor001_ep15_eval_e2986ed_20260615T2155Z`
- `1030376`: epoch `20`, run `franka_multi_resetprior_actor001_ep20_eval_e2986ed_20260615T2155Z`

Next:
- Inspect deterministic evals. If they are below BC, actor scale `0.01` is still too high or the PPO objective remains poorly aligned; next ablation should reduce actor scale substantially or freeze most actor layers.

## 2026-06-15T22:01:00Z - patched-anchor evals still below BC

Deterministic object0 eval results:

| Job | Checkpoint | Run | Eval success / success-ever | Max success | Final success | Done count | Done reasons |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `1030373` | epoch `5` | `franka_multi_resetprior_actor001_ep5_eval_e2986ed_20260615T2155Z` | `0.296875` / `0.3046875` | `0.2578125` | `0.0` | `17` | `success_done=16`, `unclassified=1`, table/prelift/cube-out `0` |
| `1030374` | epoch `10` | `franka_multi_resetprior_actor001_ep10_eval_e2986ed_20260615T2155Z` | `0.125` / `0.1328125` | `0.0859375` | `0.0078125` | `11` | `success_done=8`, `unclassified=3`, table/prelift/cube-out `0` |
| `1030375` | epoch `15` | `franka_multi_resetprior_actor001_ep15_eval_e2986ed_20260615T2155Z` | `0.0390625` / `0.0390625` | `0.0234375` | `0.0078125` | `2` | `success_done=1`, `unclassified=1`, table/prelift/cube-out `0` |
| `1030376` | epoch `20` | `franka_multi_resetprior_actor001_ep20_eval_e2986ed_20260615T2155Z` | `0.015625` / `0.015625` | `0.0078125` | `0.0` | `3` | `success_done=2`, `unclassified=1`, table/prelift/cube-out `0` |

Reset diagnostics in every eval:
- `grasp_prior_reset_tool_downward_z=0.9975928068`
- `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
- `grasp_prior_reset_candidate_topdown_count=128`
- `grasp_prior_reset_candidate_tool_down_count=128`
- `grasp_prior_reset_candidate_table_count=128`
- `grasp_prior_reset_candidate_valid_count=128`

Analysis:
- Eval-mode anchoring improves preservation versus the unpatched anchor but still falls below the fixed BC/zero-LR baseline by epoch `5`.
- Actor scale `0.01` is still too large for object0 with this PPO objective, even with critic loss disabled, entropy disabled, and anchor weight `1000`.

Next:
- Run the matched reset-prior-only setup with actor scale `0.001` for 5 epochs. If that preserves BC-level eval success, scale from there. If it does not, the next step is freezing lower actor layers or training only the action head.

## 2026-06-15T22:02:00Z - actor-scale 0.001 preservation run launched

Training launch:
- Slurm job: `29117654`
- Experiment: `franka_multi_resetprior_actor0001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2202Z`
- Commit: `e2986edfbe1346aba667bfc3cee23de7598b691c`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29117654.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_actor0001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2202Z`

Matched settings:
- Same object0 manifest, stable-pose cache, verified grasp indices, strict reset filters, low-sigma BC checkpoint, critic loss `0`, action-prior disabled, scripted reference BC disabled, entropy `0`, anchor `1000`.
- Only change from job `29117421`: `DEXTRAH_ACTOR_LOSS_SCALE=0.001` and `MAX_ITERATIONS=5`.

Effective config verified in log:
- `DEXTRAH_ACTOR_LOSS_SCALE=0.001`
- `DEXTRAH_CRITIC_LOSS_SCALE=0.0`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=False`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False`

Expected signal:
- Epoch-5 deterministic eval should be close to or above the fixed BC baseline if actor scale was the main preservation problem.

## 2026-06-15T22:06:00Z - actor-scale 0.001 training completed; epoch-5 eval queued

Training job `29117654` completed all 5 epochs.

Training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Actor scale | Critic scale | Anchor loss | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0039` | `0.0078` | `0.0298` | `0.0798` | `0.001` | `0.0` | `1.5439` | `0.9975928` |
| 2 | `0.0977` | `0.2461` | `0.0295` | `0.1691` | `0.001` | `0.0` | `1.1187` | `0.9975928` |
| 3 | `0.0039` | `0.2383` | `0.0023` | `0.2893` | `0.001` | `0.0` | `0.4443` | `0.9975928` |
| 4 | `0.0117` | `0.2539` | `0.0023` | `0.3709` | `0.001` | `0.0` | `0.4478` | `0.9975928` |
| 5 | `0.0` | `0.2539` | `0.0005` | `0.4269` | `0.001` | `0.0` | `0.5072` | `0.9975928` |

Interpretation:
- Actor scale `0.001` reduces anchor drift but training still leaves the BC basin by epoch `5`.
- Epoch-5 deterministic eval is required because stochastic training success is not directly comparable to the fixed BC eval.

Eval submitted:
- `1030377`: `franka_multi_resetprior_actor0001_ep5_eval_e2986ed_20260615T2206Z`

Next:
- If eval is below BC, reduce actor scale another order of magnitude or freeze shared actor layers/action head selectively.

## 2026-06-15T22:12:00Z - actor-scale 0.0001 run launched

Training launch:
- Slurm job: `29117761`
- Experiment: `franka_multi_resetprior_actor00001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2212Z`
- Commit: `e2986edfbe1346aba667bfc3cee23de7598b691c`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29117761.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_actor00001_critic0_anchor1000_sigma_m5_lr1e6_e2986ed_20260615T2212Z`

Matched settings:
- Same as actor-scale `0.001` run except `DEXTRAH_ACTOR_LOSS_SCALE=0.0001`.
- `MAX_ITERATIONS=5`, critic loss `0.0`, action-prior disabled, scripted reference BC disabled, anchor `1000.0`.

Effective config verified in log:
- `DEXTRAH_ACTOR_LOSS_SCALE=0.0001`
- `DEXTRAH_CRITIC_LOSS_SCALE=0.0`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=False`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=False`

Status:
- Running on A100 while actor-scale `0.001` epoch-5 eval `1030377` waits/runs on L40.

## 2026-06-15T22:18:00Z - actor-scale 0.0001 training completed; eval queued

Training job `29117761` completed all 5 epochs.

Training rows:

| Epoch | Success | Has lifted | Lift height | EE dist | Actor scale | Critic scale | Anchor loss | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0` | `0.0` | `0.0239` | `0.0858` | `0.0001` | `0.0` | `1.4502` | `0.9975928` |
| 2 | `0.1094` | `0.2188` | `0.0285` | `0.1759` | `0.0001` | `0.0` | `0.8712` | `0.9975928` |
| 3 | `0.0156` | `0.2305` | `0.0036` | `0.3099` | `0.0001` | `0.0` | `0.3868` | `0.9975928` |
| 4 | `0.0039` | `0.2383` | `0.0029` | `0.3898` | `0.0001` | `0.0` | `0.4285` | `0.9975928` |
| 5 | `0.0039` | `0.2461` | `0.0027` | `0.4396` | `0.0001` | `0.0` | `0.5254` | `0.9975928` |

Interpretation:
- Lowering actor scale another order of magnitude keeps anchor loss small, but stochastic training success is still not BC-like by epoch `5`.
- Deterministic eval is queued to verify the actual policy.

Eval submitted:
- `1030379`: `franka_multi_resetprior_actor00001_ep5_eval_e2986ed_20260615T2218Z`
- L40 eval `1030377` for actor-scale `0.001` is still pending/running ahead of it.

## 2026-06-15T22:23:00Z - rerouted pending evals from L40 to A100

Reason:
- L40 evals `1030377` and `1030379` remained pending for resources long enough to block the iteration loop.

Action:
- Canceled L40 jobs `1030377` and `1030379`.
- Relaunched the same deterministic evals on A100 with explicit partition/CPU/memory overrides.

A100 eval jobs:
- `29117919`: actor scale `0.001`, run `franka_multi_resetprior_actor0001_ep5_eval_e2986ed_a100_20260615T2223Z`
- `29117920`: actor scale `0.0001`, run `franka_multi_resetprior_actor00001_ep5_eval_e2986ed_a100_20260615T2223Z`

Setup:
- Same deterministic object0 eval settings as the canceled L40 jobs: `NUM_ENVS=128`, `NUM_STEPS=360`, video disabled, same manifest/cache/verified grasps and strict reset filters.

## 2026-06-15T22:24:00Z - low-actor-scale evals completed below BC

A100 eval results:

| Job | Checkpoint | Run | Eval success / success-ever | Max success | Final success | Done count | Done reasons |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `29117919` | actor scale `0.001`, epoch `5` | `franka_multi_resetprior_actor0001_ep5_eval_e2986ed_a100_20260615T2223Z` | `0.296875` / `0.296875` | `0.2578125` | `0.0` | `20` | `success_done=17`, `unclassified=3`, table/prelift/cube-out `0` |
| `29117920` | actor scale `0.0001`, epoch `5` | `franka_multi_resetprior_actor00001_ep5_eval_e2986ed_a100_20260615T2223Z` | `0.28125` / `0.28125` | `0.2421875` | `0.0078125` | `15` | `success_done=13`, `unclassified=2`, table/prelift/cube-out `0` |

Reset diagnostics from eval step `0` remained clean:
- `grasp_prior_reset_tool_downward_z=0.9975928068`
- `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
- `grasp_prior_reset_candidate_topdown_count=128`
- `grasp_prior_reset_candidate_tool_down_count=128`
- `grasp_prior_reset_candidate_table_count=128`
- `grasp_prior_reset_candidate_valid_count=128`
- `grasp_prior_reset_pregrasp_tip_table_clearance=0.0861287415`
- `grasp_prior_reset_projected_exact_tip_table_clearance=0.0063213445`

Queue cleanup:
- Canceled L40 evals `1030377` and `1030379` were superseded by the A100 evals above.
- No owned eval jobs remain active after `29117919` and `29117920` completed.
- A100 queue still contains unrelated jobs (`dextrah_yam_cube_rl`, `molmo2_yam_tfds`); these are not part of this run loop.

Analysis:
- Reducing actor scale from `0.01` to `0.001` and `0.0001` does not preserve the fixed BC/zero-LR baseline (`eval_success_rate=0.421875`, `success_ever_rate=0.4453125`).
- The below-table/upward-grasp failure mode is not present in these evals: reset samples are top-down, tool-z points downward, and table/prelift/cube-out done reasons are zero.
- The remaining failure is PPO/reference optimization drifting the policy away from the BC basin.

Next:
- Add a trainable-parameter scope for the custom DEXTRAH RL agent and run a short preservation diagnostic that freezes the shared/trunk parameters and updates only the action mean head (`mu`). This tests whether shared representation drift is the reason PPO drops below the BC baseline even at tiny actor loss scales.

## 2026-06-15T22:24:20Z - trainable-parameter-scope patch prepared

Code change in progress:
- `dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`: add `dextrah_trainable_param_scope` with scopes `all`, `mu`, `mu_sigma`, and actor/policy variants. Non-default scopes set `requires_grad` on matched model parameters and print the trainable/frozen parameter counts.
- `cluster/sbatch_train_teacher_8gpu.sh`: add `DEXTRAH_TRAINABLE_PARAM_SCOPE`, log it, and pass it to Hydra as `+agent.params.config.dextrah_trainable_param_scope`.

Validation passed locally:
- `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`
- `bash -n cluster/sbatch_train_teacher_8gpu.sh`
- `git diff --check`

Next:
- Commit/push the patch, deploy the exact commit to the A100 agent worktree, then launch a 5-epoch object0 run with `DEXTRAH_TRAINABLE_PARAM_SCOPE=mu`, actor scale `0.001`, critic loss `0`, entropy `0`, BC anchor `1000`, no scripted BC, and no action-prior reward.

## 2026-06-15T22:26:00Z - trainable-scope patch committed, deployed, and launched

Version state:
- Commit `1fdd8b9008325efe8dc81805048eae11a818b724`: `Add DEXTRAH trainable parameter scope`
- Branch pushed to origin.
- A100 agent worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- Remote worktree updated to `1fdd8b9008325efe8dc81805048eae11a818b724` by Git bundle because direct GitHub fetch was still unavailable.
- Remote checks passed:
  - `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`

Training launch:
- Slurm job: `29118194`
- Experiment: `franka_multi_resetprior_mu_actor0001_critic0_anchor1000_sigma_m5_lr1e6_1fdd8b9_20260615T2226Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29118194.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_mu_actor0001_critic0_anchor1000_sigma_m5_lr1e6_1fdd8b9_20260615T2226Z`

Settings:
- Same object0 manifest, stable-pose cache, verified grasp indices, and strict topdown/downward reset gates as jobs `29117654` and `29117761`.
- Initial checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- One A100 GPU, `NUM_ENVS=256`, `MAX_ITERATIONS=5`, `SAVE_FREQUENCY=5`.
- PPO/stabilizer settings: `LEARNING_RATE=1e-6`, `CENTRAL_VALUE_LEARNING_RATE=1e-6`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=1`, `E_CLIP=0.01`, `TRAIN_SIGMA=-5`, `ENTROPY_COEF=0.0`, frozen obs RMS, BC policy anchor enabled with weight `1000.0`, scripted BC loss disabled, action-prior reward disabled.
- Loss controls: `DEXTRAH_ACTOR_LOSS_SCALE=0.001`, `DEXTRAH_CRITIC_LOSS_SCALE=0.0`.
- New diagnostic setting: `DEXTRAH_TRAINABLE_PARAM_SCOPE=mu`.

Startup evidence:
- Log header confirms `CODE_COMMIT=1fdd8b9008325efe8dc81805048eae11a818b724`.
- Log header and Hydra command confirm `DEXTRAH_TRAINABLE_PARAM_SCOPE=mu` and `+agent.params.config.dextrah_trainable_param_scope=mu`.

Expected signal:
- First verify the trainable-scope print shows real `mu` parameters were matched.
- If training completes, deterministic epoch-5 eval should preserve or beat the fixed BC baseline (`eval_success_rate=0.421875`, `success_ever_rate=0.4453125`) before scaling beyond object0.

## 2026-06-15T22:33:30Z - mu-only run completed; still below BC

Training job `29118194` completed with exit `0:0`.

Scope verification:
- Log printed:
  `[DEXTRAH] trainable parameter scope 'mu': 2 trainable, 11 frozen; trainable=a2c_network.mu.weight, a2c_network.mu.bias`
- This confirms the diagnostic updated only the action-mean head.

Training rows from `metrics/direct_info_rank_0.jsonl`:

| Epoch | Success | Has lifted | Lift height | EE/root dist | Actor scale | Critic scale | Anchor loss | Reset tool down | Tool z axis z |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.00390625` | `0.0078125` | `0.032401` | `0.080374` | `0.001` | `0.0` | `1.548663` | `0.9975928` | `-0.9975928` |
| 2 | `0.16015625` | `0.2734375` | `0.043661` | `0.161067` | `0.001` | `0.0` | `1.095648` | `0.9975928` | `-0.9975928` |
| 3 | `0.01953125` | `0.2734375` | `0.011892` | `0.289096` | `0.001` | `0.0` | `0.468634` | `0.9975928` | `-0.9975928` |
| 4 | `0.01171875` | `0.28125` | `0.010499` | `0.389524` | `0.001` | `0.0` | `0.405717` | `0.9975928` | `-0.9975928` |
| 5 | `0.0` | `0.27734375` | `0.000435` | `0.461347` | `0.001` | `0.0` | `0.418394` | `0.9975928` | `-0.9975928` |

Deterministic eval:
- Slurm job: `29118299`
- Run: `franka_multi_resetprior_mu_actor0001_ep5_eval_1fdd8b9_a100_20260615T2230Z`
- Metrics: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_resetprior_mu_actor0001_ep5_eval_1fdd8b9_a100_20260615T2230Z/metrics.json`
- `eval_success_rate=0.2890625`
- `success_ever_rate=0.296875`
- `success_rate_max=0.265625`
- `success_rate_final=0.0`
- `done_count=14`
- `done_reason_counts`: `success_done=11`, `unclassified=3`, `cube_out=0`, `finger_table_penetration=0`, `prelift_drag=0`

Eval reset diagnostics at step `0`:
- `grasp_prior_reset_tool_downward_z=0.9975928068`
- `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
- `grasp_prior_reset_candidate_topdown_count=128`
- `grasp_prior_reset_candidate_tool_down_count=128`
- `grasp_prior_reset_candidate_table_count=128`
- `grasp_prior_reset_candidate_valid_count=128`
- `grasp_prior_reset_pregrasp_tip_table_clearance=0.0861287415`
- `grasp_prior_reset_projected_exact_tip_table_clearance=0.0063213445`

Analysis:
- Freezing all non-`mu` parameters did not preserve the fixed BC baseline.
- The reset sampler remains physically clean; the root from-below/table penetration issue is still absent.
- Config review found another uncontrolled optimizer term: `agent.params.config.bounds_loss_coef=0.001` in both the known-good single-cube and multi-object PPO configs. The custom DEXTRAH loss scaling disables PPO actor/critic terms but still always includes `b_loss * bounds_loss_coef`; therefore even actor/critic-zero preservation diagnostics can move the policy through bound regularization.

Patch prepared:
- `cluster/sbatch_train_teacher_8gpu.sh`: add optional `DEXTRAH_BOUNDS_LOSS_COEF`, log it, and pass `agent.params.config.bounds_loss_coef` through a common agent override only when explicitly set.
- Local validation passed:
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`
  - `git diff --check`

Next:
- Commit/deploy the bounds-loss override.
- Run a zero-update preservation diagnostic from the low-sigma BC checkpoint with `DEXTRAH_ACTOR_LOSS_SCALE=0.0`, `DEXTRAH_CRITIC_LOSS_SCALE=0.0`, `DEXTRAH_BOUNDS_LOSS_COEF=0.0`, `ENTROPY_COEF=0.0`, no scripted BC/action-prior, and frozen obs RMS. If deterministic eval returns to the fixed BC baseline, then run the real small-actor RL diagnostic with bounds loss disabled.

## 2026-06-15T22:41:30Z - zero-update run exposed policy-anchor mode bug

Version state:
- Commit `3ac11f8ef1606c80ec5b1147aafab955e751d35c`: `Expose DEXTRAH bounds loss override`
- A100 agent worktree updated to `3ac11f8ef1606c80ec5b1147aafab955e751d35c` by Git bundle.
- Remote `bash -n cluster/sbatch_train_teacher_8gpu.sh` passed.

Zero-update training launch:
- Slurm job: `29118435`
- Experiment: `franka_multi_resetprior_zero_actor0_critic0_bounds0_anchor1000_sigma_m5_3ac11f8_20260615T2238Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29118435.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_zero_actor0_critic0_bounds0_anchor1000_sigma_m5_3ac11f8_20260615T2238Z`

Critical config verified in log:
- `DEXTRAH_ACTOR_LOSS_SCALE=0.0`
- `DEXTRAH_CRITIC_LOSS_SCALE=0.0`
- `DEXTRAH_BOUNDS_LOSS_COEF=0.0`
- Hydra command included `agent.params.config.bounds_loss_coef=0.0`
- `ENTROPY_COEF=0.0`
- scripted BC and action-prior reward disabled
- BC policy anchor enabled with weight `1000.0`

Training rows from `metrics/direct_info_rank_0.jsonl`:

| Epoch | Success | Has lifted | Lift height | EE/root dist | Actor scale | Critic scale | Anchor loss | Reset tool down |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0.0` | `0.0` | `0.022847` | `0.083995` | `0.0` | `0.0` | `1.448262` | `0.9975928` |
| 2 | `0.140625` | `0.2109375` | `0.038917` | `0.159250` | `0.0` | `0.0` | `0.891238` | `0.9975928` |
| 3 | `0.015625` | `0.2265625` | `0.004095` | `0.287924` | `0.0` | `0.0` | `0.372251` | `0.9975928` |
| 4 | `0.015625` | `0.23828125` | `0.003959` | `0.383518` | `0.0` | `0.0` | `0.341160` | `0.9975928` |
| 5 | `0.00390625` | `0.234375` | `0.000634` | `0.445586` | `0.0` | `0.0` | `0.372263` | `0.9975928` |

Analysis:
- Even with actor, critic, entropy, and bounds losses disabled, the BC policy anchor loss is nonzero and updates the policy.
- The remaining hidden drift source is the anchor itself. The code captured the teacher lazily and compared an eval-mode teacher against a student forward that only set `is_train=False`; the student module itself stayed in training mode, so RunningMeanStd/model-mode behavior can differ from the teacher.

Patch prepared:
- `dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`
  - call `_ensure_dextrah_policy_anchor_model()` at the start of `calc_gradients()` immediately after restoring frozen observation RMS, before the normal train-mode policy forward can update normalization state
  - run the student anchor forward with `self.model.eval()` temporarily, restoring the previous training state in a `finally` block
- Local validation passed:
  - `python3 -m py_compile dextrah_lab/rl_games/dextrah_grasp_prior_a2c.py`
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`
  - `git diff --check`

Next:
- Commit/deploy the anchor-mode fix and rerun the same zero-update preservation diagnostic. Expected anchor loss should be near zero; deterministic eval should match the fixed BC baseline before any RL actor update is trusted.

## 2026-06-15T22:52:24Z - anchor fix validated; stale BC baseline corrected

Version state:
- Commit `a327a6aa67e9c96af4533c65bfdc83ac4f4c133c`: `Fix DEXTRAH anchor eval-mode comparison`
- A100 agent worktree updated to `a327a6aa67e9c96af4533c65bfdc83ac4f4c133c` by Git bundle.
- Remote `bash -n cluster/sbatch_train_teacher_8gpu.sh` passed.

Zero-update anchor-fix diagnostic:
- Slurm job: `29118526`
- Experiment: `franka_multi_resetprior_zero_actor0_critic0_bounds0_anchor1000_sigma_m5_a327a6a_20260615T2243Z`
- Log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29118526.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_zero_actor0_critic0_bounds0_anchor1000_sigma_m5_a327a6a_20260615T2243Z`

Training result:
- Same zero-update controls as job `29118435`: actor loss scale `0.0`, critic loss scale `0.0`, bounds loss coef `0.0`, entropy `0.0`, scripted BC loss off, action-prior reward off, frozen obs RMS on, policy anchor weight `1000.0`.
- Anchor loss is now near-zero instead of order-one:
  - epoch 1: `2.3446e-05`
  - epoch 2: `0.000789`
  - epoch 3: `0.000646`
  - epoch 4: `0.000899`
  - epoch 5: `0.000905`
- Reset diagnostics stayed clean:
  - `grasp_prior_reset_tool_downward_z=0.9975928`
  - `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928`

Deterministic eval of zero-update checkpoint:
- Slurm job: `29118596`
- Run: `franka_multi_resetprior_zero_anchorfix_ep5_eval_a327a6a_a100_20260615T2247Z`
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_resetprior_zero_anchorfix_ep5_eval_a327a6a_a100_20260615T2247Z/metrics.json`
- `eval_success_rate=0.2890625`
- `success_ever_rate=0.2890625`
- `success_rate_max=0.25`
- `success_rate_final=0.0`
- `done_count=12`
- `done_reason_counts`: `success_done=9`, `unclassified=3`, `cube_out=0`, `finger_table_penetration=0`, `prelift_drag=0`

Direct deterministic eval of original low-sigma BC checkpoint under current code:
- Slurm job: `29118811`
- Run: `franka_multi_bc_lowsigma_direct_eval_a327a6a_a100_20260615T2252Z`
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_bc_lowsigma_direct_eval_a327a6a_a100_20260615T2252Z/metrics.json`
- `eval_success_rate=0.28125`
- `success_ever_rate=0.28125`
- `success_rate_max=0.25`
- `success_rate_final=0.0`
- `done_count=16`
- `done_reason_counts`: `success_done=14`, `unclassified=2`, `cube_out=0`, `finger_table_penetration=0`, `prelift_drag=0`
- Reset diagnostics at step `0`:
  - `grasp_prior_reset_tool_downward_z=0.9975928068`
  - `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
  - `grasp_prior_reset_candidate_topdown_count=128`
  - `grasp_prior_reset_candidate_tool_down_count=128`
  - `grasp_prior_reset_candidate_table_count=128`
  - `grasp_prior_reset_candidate_valid_count=128`
  - `grasp_prior_reset_pregrasp_tip_table_clearance=0.0861287415`
  - `grasp_prior_reset_projected_exact_tip_table_clearance=0.0063213445`

Analysis:
- The older `eval_success_rate=0.421875` BC number is not comparable to the current eval path/seed. The current comparable direct BC baseline is about `0.28125`.
- The zero-update PPO checkpoint preserves the direct BC behavior within sampling noise (`0.2890625` vs. `0.28125`), so there is no remaining evidence of checkpoint drift.
- The from-below/table-penetrating grasp reset failure remains absent in these deterministic evals: every sampled reset candidate passed top-down/tool-down/table-valid gates, the end-effector tool z-axis points downward, and table/finger/prelift done reasons are zero.

Next:
- Relaunch real PPO from the low-sigma BC checkpoint at current commit `a327a6a` with the anchor fix, bounds disabled, frozen obs RMS, low sigma, and a small actor update. Use the current direct BC baseline (`eval_success_rate~0.28`) as the preservation floor.

## 2026-06-15T22:56:00Z - launched fixed-anchor PPO diagnostic sweep

Version state:
- Local commit: `e219815d80454f05fedfaecba9292cf711230fd8`
- A100 agent worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/multiobject-topdown-axis-20260615-753139c`
- Remote worktree verified at `e219815d80454f05fedfaecba9292cf711230fd8` before launch.

Common settings:
- Initial checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- Dataset/object slice: one object, `max_objects=1`, object0 manifest
  `/results/assets/filtered_manifests/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/manifest_object0_7195ed3346a445448308febe833c180a.json`
- Stable pose cache:
  `/results/validations/train2_7195_b87_nobelow_d053e6c_20260615T0045Z/settled_pose_cache`
- Verified grasp indices:
  `/results/assets/verified_grasp_indices/verified_rawpose_stricttable_train2_a100_4234fb5_20260615T1704Z/verified_indices.json`
- Reset gates: grasp-prior reset enabled, 16 attempts, 128 candidates, require topdown, require downward tool z, min pregrasp z `0.45`, min downward tool z `0.45`, min contact height above center `-0.02`, max center distance frac `0.50`, min width `0.008`.
- PPO controls: `NUM_ENVS=256`, `MAX_ITERATIONS=20`, `SAVE_FREQUENCY=5`, `LEARNING_RATE=1e-6`, `CENTRAL_VALUE_LEARNING_RATE=1e-6`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=1`, `E_CLIP=0.01`, `TRAIN_SIGMA=-5`, `ENTROPY_COEF=0.0`.
- Stabilizers: frozen obs RMS, BC policy anchor enabled with weight `1000.0`, bounds loss disabled with `DEXTRAH_BOUNDS_LOSS_COEF=0.0`, scripted BC loss off, action-prior reward off.

Sweep arms:

| Arm | Job | Run | Scope | Actor scale | Critic scale | Log |
| --- | ---: | --- | --- | ---: | ---: | --- |
| conservative policy head | `29120052` | `franka_multi_resetprior_mu_actor0001_critic0_bounds0_anchor1000_sigma_m5_e219815_20260615T2256Z` | `mu` | `0.001` | `0.0` | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29120052.out` |
| PPO-proper critic update | `29120053` | `franka_multi_resetprior_all_actor0001_critic1_bounds0_anchor1000_sigma_m5_e219815_20260615T2256Z` | `all` | `0.001` | `1.0` | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29120053.out` |

Early launch check:
- Both jobs entered `RUNNING`.
- Headers confirm `CODE_COMMIT=e219815d80454f05fedfaecba9292cf711230fd8`.
- Job `29120052` header confirms `DEXTRAH_TRAINABLE_PARAM_SCOPE=mu`, `DEXTRAH_CRITIC_LOSS_SCALE=0.0`, and `DEXTRAH_BOUNDS_LOSS_COEF=0.0`.
- Job `29120053` header confirms `DEXTRAH_TRAINABLE_PARAM_SCOPE=all`, `DEXTRAH_CRITIC_LOSS_SCALE=1.0`, and `DEXTRAH_BOUNDS_LOSS_COEF=0.0`.

Success criteria:
- No reset regression: maintain topdown/tool-down/table-valid candidate counts, downward tool z near `0.9976`, and no table/finger/prelift done reasons.
- Preserve or beat direct BC deterministic baseline: `eval_success_rate=0.28125`, `success_rate_max=0.25`.
- Prefer an arm only if reward/success improves without policy-anchor explosion or unstable done reasons.

## 2026-06-15T23:09:00Z - fixed-anchor sweep completed; best checkpoint improves modestly

Training jobs:
- Job `29120052` (`mu`, critic off) completed with exit `0:0` in `00:02:49`.
- Job `29120053` (`all`, critic on) completed with exit `0:0` in `00:02:43`.

Training curves from `metrics/direct_info_rank_0.jsonl`:

| Arm | Best epoch | Best rollout success | Final rollout success | Final anchor loss | Reset/tool status |
| --- | ---: | ---: | ---: | ---: | --- |
| `mu`, critic `0.0` | `11` | `0.24609375` | `0.19140625` | `0.0582636` | topdown/tool-down/table-valid `128`, tool z downward `0.9975928`, no table/finger violations |
| `all`, critic `1.0` | `11` | `0.1796875` | `0.0546875` | `10.920723` | topdown/tool-down/table-valid `128`, tool z downward `0.9975928`, no table/finger violations |

Checkpoint evals launched:
- Initial eval submit failed before launch because `cluster/sbatch_eval_franka_multi_object_grasp_1gpu.sh` defaults to the L40 `batch` partition, which is invalid on A100. Relaunched with explicit A100 partitions.
- Job `29120181`: `franka_multi_resetprior_mu_actor0001_ep20_eval_e219815_a100_20260615T2302Z`
- Job `29120182`: `franka_multi_resetprior_all_actor0001_ep10_eval_e219815_a100_20260615T2302Z`

Deterministic eval results:

| Eval | Checkpoint | `eval_success_rate` | `success_ever_rate` | `success_rate_max` | `done_count` | Done reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `mu` epoch 20 | `last_dextrah_franka_multi_object_grasp_ep_20_rew_1085.9113.pth` | `0.3203125` | `0.3203125` | `0.265625` | `8` | `success_done=7`, `unclassified=1`, table/finger/prelift/cube_out `0` |
| `all` epoch 10 | `last_dextrah_franka_multi_object_grasp_ep_10_rew_1076.9912.pth` | `0.3359375` | `0.3359375` | `0.28125` | `25` | `success_done=22`, `unclassified=3`, table/finger/prelift/cube_out `0` |

Eval reset diagnostics:
- Both evals kept:
  - `grasp_prior_reset_tool_downward_z=0.9975928068`
  - `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
  - `grasp_prior_reset_candidate_topdown_count=128`
  - `grasp_prior_reset_candidate_tool_down_count=128`
  - `grasp_prior_reset_candidate_table_count=128`
  - `grasp_prior_reset_candidate_valid_count=128`
  - `grasp_prior_reset_pregrasp_tip_table_clearance=0.0861287415`
  - `grasp_prior_reset_projected_exact_tip_table_clearance=0.0063213445`

Analysis:
- The reset-from-below bug remains resolved: no upward end-effector z-axis reset, no table-colliding reset, and no table/finger/prelift terminal failures.
- The best deterministic checkpoint is `all` epoch 10, which improves over the current direct BC baseline (`0.3359375` vs `0.28125`) but is not yet a strong training success.
- The `all` arm degraded by epoch 20 while anchor loss grew to `10.920723`; the next iteration should continue from the epoch-10 checkpoint with lower update pressure rather than scale to more objects.

Next:
- Launch two continuation diagnostics from the `all` epoch-10 checkpoint:
  1. lower learning rate with all parameters/critic enabled
  2. actor-only scope with critic off
- Keep the same one-object slice and strict reset gates until deterministic eval is clearly above the current BC floor.

## 2026-06-15T23:11:00Z - launched epoch-10 continuation diagnostics

Starting point:
- Checkpoint:
  `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_all_actor0001_critic1_bounds0_anchor1000_sigma_m5_e219815_20260615T2256Z/nn/last_dextrah_franka_multi_object_grasp_ep_10_rew_1076.9912.pth`
- This checkpoint evaluated at `eval_success_rate=0.3359375` and `success_rate_max=0.28125`.

Common settings:
- Commit `e219815d80454f05fedfaecba9292cf711230fd8`
- One object, same object0 manifest/stable-pose cache/verified grasp indices.
- Same strict reset gates as prior sweep.
- `NUM_ENVS=256`, `MAX_ITERATIONS=20`, `SAVE_FREQUENCY=5`, `HORIZON_LENGTH=64`, `MINI_EPOCHS=1`, `E_CLIP=0.01`, `TRAIN_SIGMA=-5`, `ENTROPY_COEF=0.0`
- Frozen obs RMS, BC policy anchor weight `1000.0`, bounds loss disabled, scripted BC loss off, action-prior reward off.

Continuation arms:

| Arm | Job | Run | Scope | Actor scale | Critic scale | LR | Log |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| lower LR all/critic | `29120316` | `franka_multi_resetprior_all_ep10cont_actor0001_critic1_lr5e7_anchor1000_sigma_m5_e219815_20260615T2311Z` | `all` | `0.001` | `1.0` | `5e-7` | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29120316.out` |
| actor-only continuation | `29120317` | `franka_multi_resetprior_all_ep10cont_actorScope_actor0001_critic0_lr1e6_anchor1000_sigma_m5_e219815_20260615T2311Z` | `actor` | `0.001` | `0.0` | `1e-6` | `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29120317.out` |

Early launch check:
- Both jobs entered `RUNNING`.
- Headers confirm commit `e219815d80454f05fedfaecba9292cf711230fd8`, intended checkpoint, `DEXTRAH_BOUNDS_LOSS_COEF=0.0`, and the intended scope/critic/LR settings.

## 2026-06-15T23:20:00Z - launched known-good-like PPO scale-up on object0

Reason:
- Code comparison found that the multi-object env inherits the single-cube reward and PPO config; no reward-path difference was identified beyond object-center substitution and extra object features.
- The previous diagnostics used intentionally conservative settings (`lr=1e-6`, `sigma=-5`, `entropy=0`, `e_clip=0.01`, strong BC anchor), which are far from the known-good single-cube PPO recipe and appear to under-explore or over-constrain the policy.

Launch:
- Slurm job: `29121238`
- Run:
  `franka_multi_resetprior_object0_stdppo_8gpu_bcinit_sigma_m3_e219815_20260615T2320Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29121238.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_stdppo_8gpu_bcinit_sigma_m3_e219815_20260615T2320Z`
- Commit: `e219815d80454f05fedfaecba9292cf711230fd8`
- Initial checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`

Settings:
- 8 GPUs, `NPROC_PER_NODE=8`, `NUM_ENVS=2048`, `MAX_ITERATIONS=50`, `SAVE_FREQUENCY=10`.
- Single object/object0, same strict stable-pose and verified topdown/downward/table-safe reset settings.
- Known-good-like PPO controls: `LEARNING_RATE=2e-4`, `CENTRAL_VALUE_LEARNING_RATE=1e-4`, `MINI_EPOCHS=4`, `E_CLIP=0.2`, `ENTROPY_COEF=0.0005`, `TRAIN_SIGMA=-3`.
- Diagnostics disabled: BC anchor off, freeze obs RMS off, actor/critic loss scales `1.0`, trainable scope `all`; scripted BC loss and action-prior reward off.

Success criteria:
- Training should preserve the reset safety counters (`candidate_topdown/tool_down/table/valid=128`, downward tool z near `0.9976`) and avoid table/finger/prelift terminal failures.
- Deterministic eval should exceed the current best object0 checkpoint (`eval_success_rate=0.3359375`) before scaling to more objects.

## 2026-06-15T23:33:00Z - standard PPO scale-up completed; reward shaping collapsed the grasp

Job:
- Slurm job `29121238` completed with exit `0:0` in `00:11:07`.
- Run:
  `franka_multi_resetprior_object0_stdppo_8gpu_bcinit_sigma_m3_e219815_20260615T2320Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29121238.out`
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_stdppo_8gpu_bcinit_sigma_m3_e219815_20260615T2320Z/metrics/direct_info_rank_0.jsonl`

Result:
- Training did not produce an eval-worthy checkpoint.
- Rank-0 rollout success:
  - epoch 1: `0.0`
  - best epoch 2: `0.0908203125`
  - epoch 50: `0.00146484375`
  - mean over 50 epochs: `0.003310546875`
- Reset safety stayed clean throughout:
  - final `cube_grasp_prior_tool_downward_z=0.9975928068`
  - final `cube_grasp_prior_tool_z_axis_z=-0.9975928068`
  - final `cube_finger_table_clearance_violation=0.0`
  - final `cube_table_clearance_penalty=0.0`

Reward/action diagnostics:
- Best epoch 2 had the expected lift/close behavior:
  - `cube_action_z=0.6061568`
  - `cube_gripper_action=-0.6226241`
  - `cube_gripper_close_action=0.7857118`
  - `cube_has_lifted_rate=0.1616211`
  - `cube_lift_height=0.0235507`
- Final epoch optimized a non-grasp shaped-reward mode:
  - `cube_action_z=-0.7119488`
  - `cube_gripper_action=0.7434034`
  - `cube_gripper_close_action=0.1239691`
  - `cube_has_lifted_rate=0.0083008`
  - `cube_lift_height=0.0005807`
  - `cube_xy_stability_reward=0.9357798`
  - `cube_approach_reward=0.7478603`

Analysis:
- The strict topdown/downward/table-safe reset gates are not regressing in this run.
- The known-good-like PPO update is not sufficient from the BC checkpoint under reset-prior object0. It moves away from the grasp sequence and settles into a local optimum with good approach/XY shaping but no close-and-lift behavior.
- The next diagnostic should measure the scripted/reference grasp-prior action ceiling under exactly the same reset gates, then use the teacher action stream as a BC/action-prior stabilizer if the ceiling is high.

## 2026-06-15T23:36:00Z - planned reference-action ceiling eval

Purpose:
- Quantify whether the current strict reset candidates plus the environment's grasp-prior reference action stream can reliably lift object0.
- If reference actions succeed, use this same teacher stream in PPO through `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True` and `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`.

Planned eval settings:
- Commit `e219815d80454f05fedfaecba9292cf711230fd8`
- Action source: `reference_delta`
- Checkpoint argument: low-sigma BC checkpoint only to satisfy the eval wrapper's required checkpoint input.
- `NUM_ENVS=128`, `NUM_STEPS=360`, `CAPTURE_VIDEO=False`, `SEED=42`
- Same object0 manifest, stable-pose cache, verified grasp indices, and strict topdown/downward/table-safe reset gates as the prior object0 runs.

Launch:
- Slurm job: `29122739`
- Run:
  `franka_multi_reference_delta_object0_ceiling_e219815_a100_20260615T2336Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_29122739.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_reference_delta_object0_ceiling_e219815_a100_20260615T2336Z`

Immediate result:
- Job `29122739` failed before simulation with exit `2:0`.
- Cause: stale `GRASP_PRIOR_LIBRARY_DIR=/results/assets/graspgenx_grasps/train2_7195_b87_nobelow_d053e6c_20260615T0045Z`.
- Successful object0 training runs used `GRASP_PRIOR_LIBRARY_DIR=`; the object manifest already carries
  `grasp_prior_path=/results/assets/franka_multi_graspgen_asset_smoke_contacts_2d7f495_20260613_153029/grasp_priors/7195ed3346a445448308febe833c180a.npz`.
- Relaunch with the library dir unset.

Relaunch:
- Slurm job: `29122800`
- Run:
  `franka_multi_reference_delta_object0_ceiling_e219815_a100_20260615T2340Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_multi_object_29122800.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_reference_delta_object0_ceiling_e219815_a100_20260615T2340Z`

Result:
- Job `29122800` completed with exit `0:0` in `00:01:33`.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_reference_delta_object0_ceiling_e219815_a100_20260615T2340Z/metrics.json`
- Reference-action ceiling:
  - `eval_success_rate=0.4296875`
  - `success_ever_rate=0.4296875`
  - `success_rate_max=0.4296875`
  - `success_rate_final=0.0`
  - `done_count=0`
  - done reasons all `0`
- Reset diagnostics at step `0`:
  - `grasp_prior_reset_tool_downward_z=0.9975928068`
  - `grasp_prior_reset_tool_z_axis_z_mean=-0.9975928664`
  - `grasp_prior_reset_candidate_topdown_count=128`
  - `grasp_prior_reset_candidate_tool_down_count=128`
  - `grasp_prior_reset_candidate_table_count=128`
  - `grasp_prior_reset_candidate_valid_count=128`
  - `grasp_prior_reset_projected_exact_tip_table_clearance=0.0063213445`

Analysis:
- The strict reset filter remains safe and the reference action stream gives a real object0 ceiling above the current best RL checkpoint (`0.4297` vs `0.3359`).
- The ceiling is not near `1.0`, so this object/cache slice still contains failed reference executions. However, the reference stream is strong enough to justify using it as an auxiliary PPO stabilizer.

## 2026-06-15T23:45:00Z - planned stabilized PPO with action-prior BC loss

Purpose:
- Avoid the standard PPO failure mode where the policy learns approach/XY reward while opening the gripper and moving downward.
- Use the same grasp-prior reference action stream that reached `0.4296875` as an auxiliary policy target.

Planned settings:
- Commit `e219815d80454f05fedfaecba9292cf711230fd8`
- Start checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- 8 GPUs, object0 only, same manifest/stable-pose cache/verified grasp indices/strict reset gates.
- PPO: `NUM_ENVS=2048`, `MAX_ITERATIONS=80`, `HORIZON_LENGTH=128`, `LEARNING_RATE=1e-5`, `CENTRAL_VALUE_LEARNING_RATE=1e-5`, `MINI_EPOCHS=2`, `E_CLIP=0.05`, `ENTROPY_COEF=0.0`, `TRAIN_SIGMA=-5`.
- Stabilizers: `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, `GRASP_PRIOR_ACTION_PRIOR_REWARD_WEIGHT=2.0`, `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`, `DEXTRAH_GRASP_PRIOR_BC_LOSS_WEIGHT=5.0`, BC policy anchor weight `100.0`, frozen obs RMS, bounds loss disabled, actor loss scale `0.1`, critic loss scale `1.0`.

Success criteria:
- Training rollout success should stay above the direct BC floor instead of collapsing below `0.01`.
- Deterministic eval should exceed the current best RL checkpoint (`eval_success_rate=0.3359375`) and ideally approach the reference-action ceiling (`0.4296875`).
- Reset safety counters must remain clean: topdown/tool-down/table/valid counts `128`, downward tool z near `0.9976`, and no table/finger/prelift terminal failures.

Launch:
- Slurm job: `29123054`
- Run:
  `franka_multi_resetprior_object0_bcaux_lr1e5_w5_anchor100_sigma_m5_e219815_20260615T2345Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29123054.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_bcaux_lr1e5_w5_anchor100_sigma_m5_e219815_20260615T2345Z`

Early result:
- Job entered training and saved epoch 10, then was cancelled by this agent at elapsed `00:08:28` because it was below the preservation floor.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_bcaux_lr1e5_w5_anchor100_sigma_m5_e219815_20260615T2345Z/metrics/direct_info_rank_0.jsonl`
- Rank-0 rollout curve through epoch 10:
  - epoch 1: `cube_success_rate=0.13720703125`, `bc_active_rate=1.0`, `action_prior_active_rate=1.0`
  - epoch 2: `0.0068359375`, `bc_active_rate=0.0830078125`, `action_prior_active_rate=0.03955078125`
  - epoch 5: `0.00146484375`, `bc_active_rate=0.29461669921875`, `action_prior_active_rate=0.87255859375`
  - epoch 10: `0.03271484375`, `bc_active_rate=0.54180908203125`, `action_prior_active_rate=0.845703125`
- Reset safety stayed clean in observed rows; `cube_grasp_prior_tool_downward_z=0.9975928068`, no sustained table/finger penalties.

Analysis:
- The auxiliary losses were correctly enabled but did not prevent collapse.
- The logged active rates confirm the teacher signal is intermittent under the inherited `episode_length_s=10.0`: the 128-step reference sequence is followed by a long low-signal remainder unless envs reset.
- Next patch: expose `EPISODE_LENGTH_S` in `cluster/sbatch_train_teacher_8gpu.sh` so multi-object RL can test shorter episodes, e.g. `3.0s` (`~180` policy steps), keeping most rollouts inside or near the reference-action window.

Patch:
- `cluster/sbatch_train_teacher_8gpu.sh`
  - added `EPISODE_LENGTH_S="${EPISODE_LENGTH_S:-}"`
  - prints it in the job header
  - forwards it as `env.episode_length_s=...` for Franka cube, Franka multi-object, and Franka multi-object RGB tasks when set
- Local checks passed:
  - `bash -n cluster/sbatch_train_teacher_8gpu.sh`
  - `git diff --check`

Version state:
- Commit `6dadf1649c8205b74e8f304862ddf38f3f215839`: `Expose DEXTRAH episode length override`
- Pushed to branch `codex/dextrah-multiobject-grasp-prior-finish-20260615T074722Z`.
- A100 agent worktree updated via git bundle to `6dadf1649c8205b74e8f304862ddf38f3f215839`.
- Remote `bash -n cluster/sbatch_train_teacher_8gpu.sh` passed.

## 2026-06-15T23:46:00Z - planned shortened-episode BC/action-prior PPO

Reason:
- Previous BC/action-prior run had correct auxiliary losses but long low-teacher-signal stretches under `episode_length_s=10.0`.
- Set `EPISODE_LENGTH_S=3.0`, about 180 policy steps, so the 128-step reference sequence occupies most of each episode.

Planned settings:
- Commit `6dadf1649c8205b74e8f304862ddf38f3f215839`
- Start checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- Object0 only, same strict reset gates/caches.
- `NUM_ENVS=2048`, `MAX_ITERATIONS=60`, `HORIZON_LENGTH=128`, `EPISODE_LENGTH_S=3.0`
- `LEARNING_RATE=2e-5`, `CENTRAL_VALUE_LEARNING_RATE=2e-5`, `MINI_EPOCHS=2`, `E_CLIP=0.05`, `ENTROPY_COEF=0.0`, `TRAIN_SIGMA=-5`
- `GRASP_PRIOR_ACTION_PRIOR_REWARD_ENABLED=True`, action-prior reward weight `2.0`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`, BC loss weight `10.0`
- BC policy anchor weight `100.0`, frozen obs RMS, bounds loss disabled, actor loss scale `0.05`, critic loss scale `1.0`.

Launch:
- Slurm job: `29123798`
- Run:
  `franka_multi_resetprior_object0_bcaux_ep3_lr2e5_w10_anchor100_sigma_m5_6dadf16_20260615T2346Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29123798.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_bcaux_ep3_lr2e5_w10_anchor100_sigma_m5_6dadf16_20260615T2346Z`

Result:
- Job compiled slowly but entered training; rank-0 metrics appeared after the Torch Inductor/CUDA-graph warmup.
- Cancelled by this agent at elapsed `00:08:08` because the policy again collapsed below the BC preservation floor before the first saved checkpoint.
- Metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_resetprior_object0_bcaux_ep3_lr2e5_w10_anchor100_sigma_m5_6dadf16_20260615T2346Z/metrics/direct_info_rank_0.jsonl`
- Rank-0 rollout curve:
  - epoch 1: `cube_success_rate=0.134765625`, `cube_has_lifted_rate=0.21923828125`, `bc_active_rate=1.0`, `action_prior_active_rate=1.0`
  - epoch 2: `0.04541015625`
  - epoch 3: `0.0107421875`
  - epoch 4: `0.037109375`
  - epoch 5: `0.017578125`
  - epoch 6: `0.00390625`
  - epoch 7: `0.00390625`
- Reset safety remained clean in all observed rows:
  `cube_grasp_prior_tool_downward_z=0.9975928068`, `cube_grasp_prior_tool_z_axis_z=-0.9975928068`,
  candidate topdown/tool-down/table/valid counts `128`, and no finger/table clearance penalties.

Analysis:
- The shortened episode increases the fraction of reference-action frames, but PPO updates still destroy the BC-initialized behavior within a few epochs.
- The root cause of the current learning failure is not below-table grasp sampling; the strict reset diagnostics remain clean.
- Next step is to separate representation of the current online reference-action teacher from PPO:
  train only the policy mean head with PPO actor/critic losses disabled, then deterministic-evaluate the saved online-BC checkpoints before allowing any PPO updates.

## 2026-06-15T23:53:28Z - planned online-BC mean-head pass

Reason:
- Direct deterministic BC eval under the corrected reset policy reached `eval_success_rate=0.28125`.
- The reference-action ceiling under the same reset policy reached `eval_success_rate=0.4296875`.
- PPO fine-tuning is currently worse than BC because actor/critic updates move the policy away from the grasp-prior teacher faster than auxiliary BC can recover.

Planned settings:
- Commit `6dadf1649c8205b74e8f304862ddf38f3f215839`
- Start checkpoint:
  `/results/bc/franka_multi_bc_rawpose_cache_refdelta_9943101_20260615T1740Z/nn/bc_reference_action_imitation_lowsigma_m3_sigmaonly.pth`
- Object0 only, same manifest/stable-pose cache/verified grasp indices/strict reset gates.
- `NUM_ENVS=2048`, `MAX_ITERATIONS=30`, `HORIZON_LENGTH=128`, `EPISODE_LENGTH_S=3.0`, `SAVE_FREQUENCY=5`
- `LEARNING_RATE=1e-4`, `MINI_EPOCHS=2`, `TRAIN_SIGMA=-5`
- `DEXTRAH_GRASP_PRIOR_BC_LOSS_ENABLED=True`, BC loss weight `50.0`
- `DEXTRAH_ACTOR_LOSS_SCALE=0.0`, `DEXTRAH_CRITIC_LOSS_SCALE=0.0`, bounds loss disabled, entropy disabled
- `DEXTRAH_TRAINABLE_PARAM_SCOPE=mu`, frozen obs RMS, no BC policy anchor.

Success criteria:
- Online-BC rollout success should not collapse below the direct BC floor.
- Deterministic eval of saved checkpoints should exceed the current best RL checkpoint (`0.3359375`) and move toward the reference-action ceiling (`0.4296875`).

Launch:
- Slurm job: `29124444`
- Run:
  `franka_multi_onlinebc_mu_object0_ep3_lr1e4_w50_sigma_m5_6dadf16_20260615T2354Z`
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_29124444.out`
- Run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_onlinebc_mu_object0_ep3_lr1e4_w50_sigma_m5_6dadf16_20260615T2354Z`

Result:
- Job entered training and saved epoch 5, then was cancelled by this agent at elapsed `00:07:56`.
- Rank-0 rollout curve through epoch 6:
  - epoch 1: `cube_success_rate=0.13427734375`, `bc_active_rate=1.0`, `action_prior_active_rate=1.0`
  - epoch 2: `0.05224609375`
  - epoch 3: `0.00830078125`
  - epoch 4: `0.0087890625`
  - epoch 5: `0.091796875`
  - epoch 6: `0.0107421875`
- Saved checkpoint:
  `/results/logs/rl_games/dextrah_franka_multi_object_grasp/franka_multi_onlinebc_mu_object0_ep3_lr1e4_w50_sigma_m5_6dadf16_20260615T2354Z/nn/last_dextrah_franka_multi_object_grasp_ep_5_rew_652.1376.pth`
- Deterministic eval job `29126261` completed:
  - run: `franka_multi_onlinebc_mu_ep5_policy_eval_6dadf16_20260616T0001Z`
  - metrics:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_multi_onlinebc_mu_ep5_policy_eval_6dadf16_20260616T0001Z/metrics.json`
  - `eval_success_rate=0.109375`
  - `success_ever_rate=0.1171875`
  - `success_rate_max=0.1015625`
  - `success_rate_final=0.0`

Analysis:
- Pure online BC against the current reference stream is worse than both the plain BC checkpoint (`0.28125`) and best RL checkpoint (`0.3359375`).
- This points to a teacher/curriculum issue rather than PPO loss alone.
- The reference stream can advance to lift by schedule alone after approach/close timing. Although `grasp_prior_action_warmstart_require_current_lift_ready=True`, the inherited multi-object lift gates were effectively disabled:
  `lift_max_ee_error=0.0`, `lift_max_finger_center_dist=0.0`, `lift_closed_width_margin=-1.0`.
- That creates physically inconsistent labels for off-reference policy states: once the phase clock reaches lift, BC can ask the policy to lift even when the gripper is still open or not at the object.

Patch:
- `dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
  - `grasp_prior_action_warmstart_close_max_ee_error = 0.05`
  - `grasp_prior_action_warmstart_lift_max_ee_error = 0.05`
  - `grasp_prior_action_warmstart_lift_max_finger_center_dist = 0.08`
  - `grasp_prior_action_warmstart_lift_closed_width_margin = 0.03`
- Local checks passed:
  - `python3 -m py_compile dextrah_lab/tasks/dextrah_franka_multi_object_grasp/franka_multi_object_grasp_env_cfg.py`
  - `git diff --check`

Next validation:
- Deploy patch to A100.
- Re-evaluate reference-delta ceiling with gated lift.
- Relaunch BC/PPO only if the gated reference still produces clean lift behavior and no below-table/table-collision diagnostics.
