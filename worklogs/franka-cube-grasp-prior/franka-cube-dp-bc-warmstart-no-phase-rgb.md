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
- implementation_commit: `a8e805a971b82ced017129c16341ef93cacfe36b`
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

## 2026-06-13T19:20:18Z - uniform3 no-phase RGB collection smoke

Goal:
- Collect and inspect a minimal 3-location RGB dataset with unique cube XY positions before scaling to 100-200 demos.

Hypothesis:
- The contact-aware controller settings that produced accepted normal-reset RGB demos should still produce successful demos when cube XY is explicitly sampled inside the default reachable support.

Change:
- No code changes after commit `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`.
- Generated 3 uniform specs over support `x=[-0.44,-0.28]`, `y=[-0.20,-0.04]`:
  - `8:260::0:710000:-0.404725:-0.047353`
  - `9:260::0:710001:-0.289497:-0.110581`
  - `10:260::0:710002:-0.397624:-0.049468`

Version Control:
- local_deploy_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`

Command / Job:
- job_id: `1028973`
- run_name: `franka_cube_rgb_uniform3_nophase_smoke_20260613_122018`
- command: `sbatch --export=ALL,CODE_NFS=<remote-worktree>,RUN_NAME=<run>,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,RESET_JOINT_BLEND_ALPHA=0.0,RESET_CUBE_POS_BLEND_ALPHA=0.0,SAVE_RGB_OBS=True,RGB_OBS_HEIGHT=96,RGB_OBS_WIDTH=96,CAPTURE_VIDEO=True,VIDEO_LENGTH=640,VARIANT=center_high30,ORIENTATION_MODE=source,ALIGN_STEPS=80,CONTACT_ALIGN_STEPS=320,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.055,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.08,FINGER_GATE_BALANCE_THRESHOLD=0.02,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.75,LATERAL_CENTERING_LIMIT=0.03,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,SEED=43 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- specs: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/uniform_rgb_specs/franka_cube_rgb_uniform3_nophase_smoke_20260613_122018/specs.json`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_rgb_uniform3_nophase_smoke_20260613_122018`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028973.out`

Result:
- status: running at launch on `pool0-00018`

Next:
- Monitor job `1028973`, then inspect gate summary, accepted RGB NPZ, cube XY coverage report, and rollout/video artifacts.

## 2026-06-13T19:27:56Z - confirmed default reachable support and failed smoke recap

Goal:
- Keep the next dataset on the default reachable Franka cube task support, with one unique successful RGB demo per uniformly sampled cube XY.

Hypothesis:
- The explicit cube XY reset and RGB logging path are working; the current blocker is the contact-aware data-generation controller settings under normal robot reset.

Change:
- User confirmed that "support" means the default reachable task support.
- No code changes after commit `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`.

Command / Job:
- `1028973`: `franka_cube_rgb_uniform3_nophase_smoke_20260613_122018`; canceled early by agent error after misreading Slurm elapsed time.
- `1028974`: `franka_cube_rgb_uniform1_nophase_smoke_20260613_122131`; one random support location, normal robot reset, 8D robot state RGB capture.
- `1028975`: `franka_cube_rgb_centerexplicit_nophase_smoke_20260613_122442`; support center location, normal robot reset, 8D robot state RGB capture.

Result:
- status: failed data-collection settings, not failed RGB plumbing.
- key evidence:
  - `1028974` saved raw RGB observations with `image (93, 96, 96, 3) uint8`, `robot_state (93, 8)`, `action (93, 7)`, and exact applied cube XY `[-0.317087, -0.169985]`.
  - `1028974` failed gate with lateral drag/early termination: final cube XY moved to approximately `[-0.270232, -0.254676]`, `cube_xy_error=0.098913`, final lift `0`, and left/right finger distances were unbalanced.
  - `1028975` at support center also failed before accepted close/lift under the same 320-step contact-align settings.

Analysis:
- The explicit reset path applies the requested cube XY and the RGB observation path is writing nonblank image/proprio/action arrays with the intended no-phase 8D robot state.
- The `ALIGN_STEPS=80`, `CONTACT_ALIGN_STEPS=320`, loose balance-threshold settings can drag the cube before close/lift. This is unsuitable as the smoke gate for scaling.
- Next retry should go back to the older accepted RGB relabel settings: no initial align, shorter contact align, tighter left/right gate, smaller centering limit, and small lateral search.

Next:
- Launch a one-location support-center smoke excluding `pool0-00018` with the older accepted RGB relabel settings. If accepted, make a dataset report/video; if not, inspect the rollout summary and tune the controller before scaling.

## 2026-06-13T19:28:40Z - center old-controller no-phase RGB smoke

Goal:
- Test whether normal robot reset plus explicit support-center cube XY can produce one accepted RGB demo using the older accepted relabel controller settings.

Hypothesis:
- The previous 320-step contact-align configuration was dragging the cube before close/lift. Returning to `ALIGN_STEPS=0`, `CONTACT_ALIGN_STEPS=160`, tighter left/right balance, smaller centering limit, and small lateral search should reduce pre-close cube drag.

Change:
- No code changes after commit `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`.
- Excluded `pool0-00018` because unrelated user/agent jobs are already running there.

Version Control:
- agent_id: `franka-cube-no-phase-rgb`
- local_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`

Command / Job:
- job_id: `1028982`
- run_name: `franka_cube_rgb_center_oldctrl_nophase_smoke_20260613_1228`
- command: `sbatch --parsable --exclude=pool0-00018 --export=ALL,CODE_NFS=<remote-worktree>,RUN_NAME=<run>,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,SPEC_COUNT=1,SPEC_0=8:260::0:740000:-0.360000:-0.120000,RESET_JOINT_BLEND_ALPHA=0.0,RESET_CUBE_POS_BLEND_ALPHA=0.0,SAVE_RGB_OBS=True,RGB_OBS_HEIGHT=96,RGB_OBS_WIDTH=96,CAPTURE_VIDEO=False,VARIANT=center_high30,ORIENTATION_MODE=source,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=160,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.055,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.075,FINGER_GATE_BALANCE_THRESHOLD=0.015,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.75,LATERAL_CENTERING_LIMIT=0.025,LATERAL_SEARCH_AMPLITUDE=0.004,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,SEED=43,PRINT_INTERVAL=40 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_rgb_center_oldctrl_nophase_smoke_20260613_1228`
- log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028982.out`

Result:
- status: running/queued at launch

Next:
- Monitor job `1028982`; inspect summary JSON, accepted NPZ, and raw RGB observations before deciding whether to scale.

## 2026-06-13T19:31:10Z - merge RGB BC implementation to main

Goal:
- Merge the current committed diffusion RGB implementation branch into `main` before continuing larger data generation.

Hypothesis:
- The implementation branch can be integrated cleanly on top of current `origin/main` in an isolated worktree without touching the dirty canonical checkout or the active experiment worktree.

Change:
- Created integration worktree `/home/lzha/code/.codex-worktrees/DEXTRAH/merge-dp-rgb-main-20260613` at `origin/main`.
- Merged `origin/codex/franka-cube-diffusion-policy-bc` into `main`.

Version Control:
- source_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`
- base_main: `8bad95c36af398366a4d112da9e7f766c60497ef`
- merge_commit: `fd970d35ee7dc5bf8742f5ab6e155e886b9338c7`
- push: `git push origin main` succeeded (`8bad95c..fd970d3 main -> main`)

Validation:
- `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/dp_dataset.py dextrah_lab/offline_dp_bc/weighted_diffusion_policy.py dextrah_lab/offline_dp_bc/make_rgb_dataset_report.py dextrah_lab/offline_dp_bc/make_uniform_cube_relabel_specs.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/combine_contact_relabel_rgb_sets.py dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/rl_games/eval_franka_cube_rgb_dp_policy.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh cluster/sbatch_train_franka_cube_rgb_dp_1gpu.sh cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`
- `git diff --check HEAD~1..HEAD`

Result:
- status: merged and pushed to `origin/main`

Next:
- Continue inspecting job `1028982` and tune the normal-reset RGB collection controller before scaling.

## 2026-06-13T19:36:20Z - center smoke failure analysis and ablation launch plan

Goal:
- Identify a normal-reset controller setting that produces one clean accepted center-location RGB demo without phase/progress features.

Hypothesis:
- Job `1028982` failed because contact alignment chased the live cube while the gripper was open, so the right finger bumped the cube and the target moved with it. The left/right gate never became true and the cube drifted about 10 cm before termination.

Evidence:
- `1028982` completed with scheduler state `COMPLETED`, but relabel summary verdict was hard failure.
- Raw RGB path still worked: `image (37, 96, 96, 3) uint8`, `robot_state (37, 8)`, `action (37, 7)`.
- The failed rollout stayed in `contact_align_open`; center finger distance decreased from `0.1192` to min `0.0698` m, but left/right were imbalanced (`left min 0.0944`, `right min 0.0630`), and `cube_xy_error` grew to `0.0999` m.

Change:
- No code changes.
- Next ablations keep the explicit center cube XY and normal robot reset, but freeze the contact target to the initial cube and remove lateral live-cube chasing. Variants:
  - `initref_nolat_center075`: source orientation, initial cube reference, no lateral/search, center gate `0.075`.
  - `initref_nolat_center085`: source orientation, initial cube reference, no lateral/search, center gate `0.085`.
  - `liveori_initref_nolat_center075`: live orientation, initial cube reference, no lateral/search, center gate `0.075`.

Next:
- Launch these three one-episode ablations on l401 excluding `pool0-00018`; inspect summary JSON/CSV for accepted lift, cube drift, and RGB integrity.

Command / Job:
- `1028983`: `franka_cube_rgb_center_initref_nolat_center075_20260613_1236`
- `1028984`: `franka_cube_rgb_center_initref_nolat_center085_20260613_1236`
- `1028985`: `franka_cube_rgb_center_liveori_initref_nolat_center075_20260613_1236`

Result:
- status: all three failed the hard relabel gate.
- key evidence:
  - Source-orientation jobs (`1028983`, `1028984`) still never reached a usable close/lift.
  - Live-orientation job (`1028985`) centered and closed cleanly, but with `center_high30` the closed fingers stayed about 6 cm from the cube; lift then moved the gripper away and the cube lift stayed zero.

Analysis:
- `ORIENTATION_MODE=live`, `CONTACT_ALIGN_REFERENCE=initial_cube`, no lateral/search fixes the left/right imbalance. The remaining issue is vertical/offset geometry: `center_high30` is too high to grip the cube.

Next:
- Run lower-offset live-orientation smokes with `VARIANT=center_high15` and `VARIANT=center`.

Command / Job:
- `1028986`: `franka_cube_rgb_center_liveori_initref_nolat_high15_20260613_1238`
- `1028987`: `franka_cube_rgb_center_liveori_initref_nolat_center_20260613_1238`

Result:
- status: failed hard relabel gate.
- key evidence:
  - `center_high15` reached finger-center distance about `0.0848` m but never crossed the `0.075` m center gate, so it stayed open through the entire rollout.
  - `center` briefly reached about `0.0796` m, then drifted away; it also never closed.

Analysis:
- Lowering the vertical offset alone is not enough when the close gate is too strict. A `0.09` m center gate should start close before the approach diverges; then the lower offsets can test whether early closing actually grips.

Next:
- Run `center_high15` and `center` again with live orientation, frozen initial target, no lateral/search, and `CONTACT_ALIGN_THRESHOLD=0.09`.

Command / Job:
- `1028988`: `franka_cube_rgb_center_liveori_initref_nolat_high15_thr09_20260613_1241`
- `1028989`: `franka_cube_rgb_center_liveori_initref_nolat_center_thr09_20260613_1241`

Result:
- status: failed hard relabel gate for both variants.
- `center_high15`: close gate fired at local step `32`, max cube lift was `0.0135` m, final lift was `0.0`, final finger-center distance was `0.2529` m.
- `center`: close gate fired at local step `33`, max cube lift was `0.0143` m, final lift was `0.0`, final finger-center distance was `0.2391` m.
- Both runs closed symmetrically around the cube and briefly lifted it about 1.3-1.4 cm, but the cube slipped away during lift.

Analysis:
- The failure is now in controller/data generation rather than RGB plumbing or explicit cube reset.
- CSV inspection shows the cube drifts during close while lift still uses the pre-close contact anchor. For example, in `center`, by local step `80` the live cube had moved from `[-0.3398, -0.1600, 0.7942]` to `[-0.3455, -0.1808, 0.7760]`, but the target anchor remained the old pose. Lift starts from this stale anchor, so the gripper moves up and away instead of preserving the closed grasp.

Next:
- Add an opt-in close/hold anchor policy: track the live cube during close/hold, then freeze the last close pose for lift. Validate on the same one-location center smoke before scaling.

## 2026-06-13T20:02:10Z - close-hold live-anchor controller patch

Goal:
- Fix the one-demo center collection failure where the frozen contact anchor becomes stale during gripper close.

Hypothesis:
- Updating the contact anchor from the live cube pose during close/hold should keep the finger target centered on the cube while the gripper squeezes it; freezing the last close pose for lift should avoid live-cube chasing during lift.

Change:
- Added `--close_hold_reference {contact_anchor,live_cube}` to `contact_aware_franka_cube_rollout.py`.
- Default remains `contact_anchor`, preserving prior behavior.
- Exposed the same knob in `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` as `CLOSE_HOLD_REFERENCE`.

Version Control:
- agent_id: `franka-cube-no-phase-rgb`
- base_commit: `5bf5f063bebf93e86eecfbf1daafdd7c401e297a`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart-no-phase-rgb.md`

Validation:
- `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`

Next:
- Commit, push/deploy to the agent-owned l401 worktree, and run a one-location smoke with `CLOSE_HOLD_REFERENCE=live_cube`.

Result:
- implementation_commit: `ce09babc57e74543c2e41d3858b0bb9e7282fe7c`
- pushed to GitHub branch `codex/franka-cube-diffusion-policy-bc`.
- pushed directly to l401 repo path and checked out in detached mode at `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`.

Command / Job:
- `1028992`: `franka_cube_rgb_center_liveclose_center_20260613_1305`, `VARIANT=center`, `CLOSE_HOLD_REFERENCE=live_cube`, explicit cube XY `[-0.36, -0.12]`, seed `780000`, video+RGB enabled.
- `1028993`: `franka_cube_rgb_center_liveclose_high15_20260613_1305`, `VARIANT=center_high15`, `CLOSE_HOLD_REFERENCE=live_cube`, explicit cube XY `[-0.36, -0.12]`, seed `780001`, video+RGB enabled.
- shared command base: `sbatch --exclude=pool0-00018 --export=ALL,CODE_NFS=<agent-worktree>,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,SPEC_COUNT=1,RESET_JOINT_BLEND_ALPHA=0.0,RESET_CUBE_POS_BLEND_ALPHA=0.0,SAVE_RGB_OBS=True,RGB_OBS_HEIGHT=96,RGB_OBS_WIDTH=96,CAPTURE_VIDEO=True,VIDEO_LENGTH=360,ORIENTATION_MODE=live,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=120,CONTACT_ALIGN_REFERENCE=initial_cube,CLOSE_HOLD_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.09,CONTACT_GATE_MODE=center,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.0,LATERAL_CENTERING_LIMIT=0.0,LATERAL_SEARCH_AMPLITUDE=0.0,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,PRINT_INTERVAL=40 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`

Next:
- Monitor `1028992,1028993`, inspect summaries/CSVs/videos, and either keep this setting for random-location smoke or tune again.

Result:
- `1028992` (`center`, live close anchor) failed the hard gate. It terminated after `99` rows, max/final cube lift `0.0166/0.0148` m, final finger-center-to-cube `0.0601` m.
- `1028993` (`center_high15`, live close anchor) failed the hard gate. It ran `360` rows, max/final cube lift `0.0163/0.0` m, final finger-center-to-cube `0.2516` m.
- Video inspection showed fingers close above/against the cube and then lift away. Live close anchoring improves centering but does not solve grasp capture.

Analysis:
- The failure is no longer primarily stale close/lift anchoring. The handcrafted finger-center controller remains too brittle for the explicit support center.
- Re-inspected the prior seed42 normal-reset accepted subset. It has only `3/32` accepted rollouts (`ep06`, `ep22`, `ep26`) and all three start from the same normal-reset cube pose `[-0.282, -0.1794, 0.781]`; that subset is not diverse enough and explains why repetition is misleading.

Next:
- Test whether the source orientations that accepted at the seed42 normal reset also work at the explicit support center. This separates "bad episode orientation" from "center support location is outside the current controller's usable region."

## 2026-06-13T20:45:20Z - known-orientation explicit-center smoke

Goal:
- Check whether known-good source episodes `6`, `22`, and `26` can produce accepted RGB demos when the cube is explicitly reset to the support center `[-0.36, -0.12]`.

Hypothesis:
- If any of the known-good source orientations work at the support center, the next data collector can use a bank of source orientations while sampling unique cube positions. If all fail, the current controller is not robust enough for uniform default support.

Version Control:
- implementation_commit: `ce09babc57e74543c2e41d3858b0bb9e7282fe7c`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `ce09babc57e74543c2e41d3858b0bb9e7282fe7c`

Command / Job:
- job_id: `1028996`
- run_name: `franka_cube_rgb_center_knownori_oldctrl_20260613_1345`
- command: `sbatch --exclude=pool0-00018 --export=ALL,CODE_NFS=<agent-worktree>,RUN_NAME=<run>,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=3,SPEC_0=6:260::0:790006:-0.360000:-0.120000,SPEC_1=22:260::0:790022:-0.360000:-0.120000,SPEC_2=26:260::0:790026:-0.360000:-0.120000,RESET_JOINT_BLEND_ALPHA=0.0,RESET_CUBE_POS_BLEND_ALPHA=0.0,SAVE_RGB_OBS=True,RGB_OBS_HEIGHT=96,RGB_OBS_WIDTH=96,CAPTURE_VIDEO=True,VIDEO_LENGTH=400,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=160,CONTACT_ALIGN_REFERENCE=live_cube,CLOSE_HOLD_REFERENCE=contact_anchor,CONTACT_ALIGN_THRESHOLD=0.055,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.075,FINGER_GATE_BALANCE_THRESHOLD=0.015,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.75,LATERAL_CENTERING_LIMIT=0.025,LATERAL_SEARCH_AMPLITUDE=0.004,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,PRINT_INTERVAL=40,SEED=43,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`

Next:
- Monitor `1028996`; inspect per-spec summaries, CSVs, and videos.

Result:
- status: failed before rollout; no physics/controller evidence produced.
- key evidence: Slurm log `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028996.out` contains `Missing trajectory JSON for spec 6:260::0:790006:-0.360000:-0.120000: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed6/trajectory.json`.

Analysis:
- This was a launch-configuration error. The known-good accepted episodes came from the scale264 dataset/plans, but the relaunch used the older scale32 dataset/template.

Next:
- Relaunch the same three explicit-center known-orientation specs with `/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale264_20260612_1449_full_pick_lift_framefix.npz` and trajectory template `cube_curobo_scale264_20260612_1449_seed{episode}/trajectory.json`.

## 2026-06-14T05:17:21Z - reset distribution and data-generation video visualization

Goal:
- Visualize the reset distributions used during data-generation attempts and expose representative success/failure videos.

Command / Job:
- job_id: n/a; local artifact inspection only.
- command: parsed existing `contact_relabel_set_summary.json` files, accepted NPZs, and the local scale264 source lowdim dataset with the project venv.
- artifacts:
  - `/home/lzha/code/shared_artifacts/franka-cube-dp-bc-reset-videos-20260613/reset_distribution_attempts.png`
  - `/home/lzha/code/shared_artifacts/franka-cube-dp-bc-reset-videos-20260613/reset_distribution_points.csv`
  - `/home/lzha/code/shared_artifacts/franka-cube-dp-bc-reset-videos-20260613/reset_distribution_summary.json`

Result:
- Source scale264 reference distribution: 232 unique source cube XY positions.
- Accepted source-position RGB relabel set: 183 accepted unique source positions.
- Seeded normal-reset attempts: 160 attempted rollouts across only 5 unique XY positions; per-seed pass counts were seed42 `3/32`, seed43 `11/32`, seed44 `2/32`, seed45 `13/32`, seed46 `1/32`.
- Target `xp015_nearest048` RGB attempts: 48 unique XY positions, 4 accepted and 44 failed.
- Fullstart/OOD19 RGB attempts: 19 unique XY positions, 3 accepted and 16 failed.
- Explicit support-center RGB smoke: fixed at approximately `[-0.36, -0.12]`, 0 accepted and 2 failed.

Analysis:
- The normal-reset data was not diverse: each seed repeated one cube XY for all 32 attempts. This confirms it should not be used as the main 100-200 trajectory BC dataset.
- The broader source-position and target/fullstart attempts cover real XY diversity, but success rate is poor off the old source-position relabel regime.
- The explicit support-center smoke is visually and metrically a grasp-capture failure, not an RGB/policy issue.

Next:
- Use the generated plot and representative videos to decide whether to repair the data-generation controller or switch to a known-good teacher rollout source for uniformly sampled default reachable cube positions.

## 2026-06-14T05:43:44Z - cube reset geometry patch

Goal:
- Raise the Franka reset geometry for the cube task and start from an upright/down gripper pose before retrying support-center data generation.

Hypothesis:
- The current cube-task reset initializes the Franka too close to the table and with a forward-tilted wrist, causing the handcrafted data-generation controller to close above or against the cube and then lose the grasp. Raising the cube-task base by `+0.2m` relative to its existing `0.27m` setting and using the standard Panda upright/down reset pose should improve table clearance and grasp approach geometry.

Change:
- Left the star-kitting default reset pose unchanged.
- Extended `_franka_star_robot_cfg(...)` with an optional keyword-only `joint_pos` override.
- Rebuilt the cube-task robot cfg with `robot_base_z = 0.47` and joint reset `{0.0, -0.569, 0.0, -2.810, 0.0, 3.037, 0.741}` plus open fingers.

Version Control:
- agent_id: `franka-cube-no-phase-rgb`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `ce09babc57e74543c2e41d3858b0bb9e7282fe7c`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py`
  - `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart-no-phase-rgb.md`

Validation:
- `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`

Next:
- Commit and deploy this exact source to the l401 agent worktree.
- Run a one-env reset/data-generation smoke at the explicit support center and inspect the produced metrics/video before any scale-up.

Result:
- implementation_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- validation passed locally:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  - `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh cluster/sbatch_eval_franka_cube_rgb_dp_policy_1gpu.sh`
  - `git diff --check -- dextrah_lab/tasks/dextrah_franka_star_kitting/franka_star_kitting_env_cfg.py dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart-no-phase-rgb.md`
- pushed to GitHub branch `codex/franka-cube-diffusion-policy-bc`.
- pushed directly to l401 repo and checked out in detached mode at `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`.

Command / Job:
- reset validation job_id: `1029179`
- run_name: `franka_cube_reset_upright_z047_validate_20260614_0548`
- result_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/franka_cube_validate/franka_cube_reset_upright_z047_validate_20260614_0548`
- local_fetch: `cluster_results/l401/franka_cube_reset_upright_z047_validate_20260614_0548`

Result:
- status: passed.
- metrics/artifacts:
  - `reset_cube_on_table`: cube z `0.781000018`, table surface `0.746`.
  - `reset_fingers_clear_table`: min/mean finger-table clearance `0.1673378944`, required `0.025`.
  - rollout finite for `40` steps and cube remained in workspace.
  - video artifact existed but viewport MP4 was black; metrics are the useful evidence for this validation job.

Analysis:
- Raising only the cube-task base fixed the table-clearance problem numerically.
- The subsequent contact-rollout videos still need to validate the intended gripper approach, because table clearance alone does not prove a usable grasp reset.

## 2026-06-14T05:57:20Z - raised-reset explicit-center contact rollout

Goal:
- Test whether the raised cube-task reset plus existing contact-aware controller can generate one accepted RGB demo at the explicit support center.

Command / Job:
- job_id `1029180`: `franka_cube_rgb_center_z047_liveclose_center_20260614_0552`, spec episode `6`, failed pre-rollout because the scale264 seed6 trajectory JSON does not exist.
- job_id `1029181`: `franka_cube_rgb_center_z047_liveclose_center_ep37_20260614_0557`, spec `37:260::0:850037:-0.360000:-0.120000`, `ORIENTATION_MODE=live`, `CONTACT_GATE_MODE=center`, `CONTACT_ALIGN_THRESHOLD=0.09`.
- job_id `1029182`: `franka_cube_rgb_low20_z047_liveclose_thr06_ep37_20260614_0612`, canceled because comma-valued custom `VARIANT=center_low20:0,0,-0.020` is split by Slurm `--export`.
- job_id `1029183`: `franka_cube_rgb_center_z047_liveclose_thr06_ep37_20260614_0612`, canceled after Isaac startup stall on `pool0-00017`.
- job_id `1029184`: `franka_cube_rgb_center_z047_liveclose_thr06_ep37_20260614_0617`, spec `37:260::0:850337:-0.360000:-0.120000`, `ORIENTATION_MODE=live`, `CONTACT_GATE_MODE=center`, `CONTACT_ALIGN_THRESHOLD=0.06`.

Result:
- `1029181` failed the hard gate: `accepted_episode_count=0`, `max_cube_lift_height=0.00095`, `final_cube_lift_height=0.0`, `pre_close_finger_center_to_cube=0.0856`, `final_finger_center_to_cube=0.2200`.
- `1029184` failed the hard gate: `accepted_episode_count=0`, `max_cube_lift_height=0.0`, `final_cube_lift_height=0.0`, `pre_close_finger_center_to_cube=0.0600`, `pre_close_left/right/balance=0.0837/0.0581/0.0256`, `final_finger_center_to_cube=0.2200`.
- `1029184` local video: `cluster_results/l401/franka_cube_rgb_center_z047_liveclose_thr06_ep37_20260614_0617/rollouts/ep37s260_a0_seed850337_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850337_xm0p360000_ym0p120000-step-0.mp4`
- `viz-open` URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/cluster_results/l401/franka_cube_rgb_center_z047_liveclose_thr06_ep37_20260614_0617/rollouts/ep37s260_a0_seed850337_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850337_xm0p360000_ym0p120000-step-0.mp4`

Analysis:
- The raised reset no longer starts near the table, but the "upright/down" joint reset is still visually slanted.
- `CONTACT_GATE_MODE=center` lets close start while left/right finger distances are imbalanced, so the gripper closes on one side/edge of the cube and then lifts away.
- The scale264 source row for episode `37`, step `260`, has a source EE quaternion whose local z-axis is effectively `[0, 0, -1]` and whose EE is about `0.030m` above the cube. That source orientation is a better next smoke target than `ORIENTATION_MODE=live`.

Next:
- Launch a one-location smoke at the same explicit support center with the raised reset, `ORIENTATION_MODE=source`, `CONTACT_GATE_MODE=left_right`, lateral centering enabled, and no source-joint reset. If this succeeds, scale to a few random default-reachable cube positions; if it fails, add a fixed top-down orientation/control patch instead of scaling.

## 2026-06-14T06:00:11Z - source-orientation balanced-gate center smoke

Goal:
- Determine whether the raised cube reset can produce a valid explicit-center demo when the controller drives the source CuRobo top-down orientation and waits for a balanced left/right finger gate before closing.

Hypothesis:
- The previous failure closed from a slanted live orientation with imbalanced finger distances. The source row for episode `37`, step `260`, has a top-down EE orientation and should make the same finger-center controller physically plausible if the left/right gate and lateral centering delay close until the cube is between the fingers.

Version Control:
- implementation_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`

Command / Job:
- job_id: `1029185`
- run_name: `franka_cube_rgb_center_z047_sourceori_lr_ep37_20260614_0600`
- command: `sbatch --exclude=pool0-00017,pool0-00018 --export=ALL,CODE_NFS=<agent-worktree>,RUN_NAME=franka_cube_rgb_center_z047_sourceori_lr_ep37_20260614_0600,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale264_20260612_1449_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,TRAJECTORY_TEMPLATE=cube_curobo_scale264_20260612_1449_seed{episode}/trajectory.json,SPEC_COUNT=1,SPEC_0=37:260::0:850537:-0.360000:-0.120000,RESET_JOINT_BLEND_ALPHA=0.0,RESET_CUBE_POS_BLEND_ALPHA=0.0,SAVE_RGB_OBS=True,RGB_OBS_HEIGHT=96,RGB_OBS_WIDTH=96,CAPTURE_VIDEO=True,VIDEO_LENGTH=480,VARIANT=center,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=220,CONTACT_ALIGN_REFERENCE=live_cube,CLOSE_HOLD_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.065,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.08,FINGER_GATE_BALANCE_THRESHOLD=0.015,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=1.0,LATERAL_CENTERING_LIMIT=0.03,LATERAL_SEARCH_AMPLITUDE=0.004,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,PRINT_INTERVAL=40,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`

Next:
- Monitor `1029185`; fetch summary/video; if accepted, launch a small random-location smoke; if not, inspect whether orientation convergence, gate, or target height is still wrong.

Result:
- status: failed the hard gate.
- artifacts:
  - local result dir: `cluster_results/l401/franka_cube_rgb_center_z047_sourceori_lr_ep37_20260614_0600`
  - video URL: `http://localhost:8765/view?path=.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/cluster_results/l401/franka_cube_rgb_center_z047_sourceori_lr_ep37_20260614_0600/rollouts/ep37s260_a0_seed850537_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850537_xm0p360000_ym0p120000-step-0.mp4`
- metrics: `accepted_episode_count=0`, `max_cube_lift_height=0.00734`, `final_cube_lift_height=0.0`, `pre_close_left/right/balance=0.0778/0.0682/0.0096`, `pre_close_finger_center_to_cube=0.0613`, `final_ee_to_cube=0.0490`, `terminated_next_step=true` at local step `205`.

Analysis:
- Source orientation and the `left_right` gate fixed the visibly imbalanced close from the previous run.
- The top-down open-gripper alignment still pushes/tilts the cube before close. The failure is now target height/contact geometry: `center` is too low for a collision-free pre-close approach with this finger-center controller.

Next:
- Run the same explicit-center source-orientation/left-right-gate smoke with `center_high15` and `center_high30` target variants. If one lifts, use that for a small random-location smoke. If both still fail, patch the controller to separate pre-close approach height from close/lift grasp height instead of relying on a single static target offset.

## 2026-06-14T06:03:02Z - source-orientation high-target center smokes

Goal:
- Test whether raising the finger-center target above cube center avoids pre-close cube pushing and produces a stable lift.

Hypothesis:
- `center` puts the top-down open fingers too low, causing side/top contact before close. `center_high15` or `center_high30` may approach without disturbing the cube and then close from a usable capture height.

Version Control:
- implementation_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`

Command / Job:
- command base: source-orientation, `CONTACT_GATE_MODE=left_right`, `CONTACT_ALIGN_REFERENCE=live_cube`, `CLOSE_HOLD_REFERENCE=live_cube`, `RESET_JOINT_BLEND_ALPHA=0.0`, explicit cube XY `[-0.36, -0.12]`, scale264 episode `37`, step `260`.
- job_id `1029187`: `franka_cube_rgb_center_z047_sourceori_lr_high15_ep37_20260614_0603`, `VARIANT=center_high15`.
- job_id `1029186`: `franka_cube_rgb_center_z047_sourceori_lr_high30_ep37_20260614_0603`, `VARIANT=center_high30`.
- job_id `1029188`: `franka_cube_rgb_center_z047_sourceori_lr_high15_ep37_retry_20260614_0606`, retry for `center_high15` after canceling stalled `1029187` startup on `pool0-00009`.

Next:
- Submit `center_high15` and `center_high30`; fetch summaries/videos and decide whether a controller patch is required.

Result:
- `1029186` (`center_high30`) failed: `max_cube_lift_height=0.00734`, `final_cube_lift_height=0.0`, terminated during `close_hold` at local step `129`.
- `1029187` (`center_high15`) stalled before task parsing on `pool0-00009`; canceled and treated as infrastructure evidence only.
- `1029188` (`center_high15` retry) failed: `max_cube_lift_height=0.00812`, `final_cube_lift_height=0.0`, terminated during `close_hold` at local step `108`.
- local videos:
  - high15: `cluster_results/l401/franka_cube_rgb_center_z047_sourceori_lr_high15_ep37_retry_20260614_0606/rollouts/ep37s260_a0_seed850638_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850638_xm0p360000_ym0p120000-step-0.mp4`
  - high30: `cluster_results/l401/franka_cube_rgb_center_z047_sourceori_lr_high30_ep37_20260614_0603/rollouts/ep37s260_a0_seed850737_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850737_xm0p360000_ym0p120000-step-0.mp4`

Analysis:
- Both target heights reach a balanced close gate but drag the cube laterally during close. CSV evidence shows `cube_xy_error` rises to about `0.10m`, which triggers `prelift_drag_done` before lift.
- Because `CLOSE_HOLD_REFERENCE=live_cube`, the controller chases the cube as it is dragged. Before adding new stages, test the existing `contact_anchor` close reference so close/lift stay tied to the pre-close anchor instead of following the moving cube.

Next:
- Run `center` and `center_high15` with `CLOSE_HOLD_REFERENCE=contact_anchor`. If they still drag/terminate before lift, patch the controller to separate high approach, descent/capture, close, and lift phases.

## 2026-06-14T06:10:03Z - contact-anchor close smokes

Goal:
- Test whether freezing the close/lift target at the contact anchor prevents the cube-drag failure seen with `CLOSE_HOLD_REFERENCE=live_cube`.

Hypothesis:
- Live-cube close anchoring follows the cube as the gripper pushes it, causing a 10 cm lateral drag and termination. Contact-anchor close/lift should keep the gripper centered around the original pre-close grasp anchor and may allow a lift if the grasp geometry is otherwise sufficient.

Version Control:
- implementation_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`

Command / Job:
- command base: source-orientation, `CONTACT_GATE_MODE=left_right`, `CONTACT_ALIGN_REFERENCE=live_cube`, `CLOSE_HOLD_REFERENCE=contact_anchor`, `RESET_JOINT_BLEND_ALPHA=0.0`, explicit cube XY `[-0.36, -0.12]`, scale264 episode `37`, step `260`.
- job_id `1029190`: `franka_cube_rgb_center_z047_sourceori_lr_anchor_center_ep37_20260614_0610`, `VARIANT=center`.
- job_id `1029189`: `franka_cube_rgb_center_z047_sourceori_lr_anchor_high15_ep37_20260614_0610`, `VARIANT=center_high15`.

Next:
- Submit `center` and `center_high15`, then inspect metrics/videos.

Result:
- `1029190` (`center`, contact anchor) failed after full `460` steps: `max_cube_lift_height=0.00027`, `final_cube_lift_height=0.0`, `final_finger_center_to_cube=0.2286`.
- `1029189` (`center_high15`, contact anchor) failed after full `460` steps: `max_cube_lift_height=0.00599`, `final_cube_lift_height=0.0`, `final_finger_center_to_cube=0.2388`.
- local high15 video: `cluster_results/l401/franka_cube_rgb_center_z047_sourceori_lr_anchor_high15_ep37_20260614_0610/rollouts/ep37s260_a0_seed850938_xm0p360000_ym0p120000/videos/franka-cube-contact-relabel-ep37s260_a0_seed850938_xm0p360000_ym0p120000-step-0.mp4`

Analysis:
- Contact-anchor prevents the early pre-lift drag termination, but the gripper closes while still beside the cube and then lifts away.
- The gate is too loose: close starts at finger-center distances around `0.063m`, roughly one cube half-width from center. Left/right balance is not enough; require a much smaller center distance before close.

Next:
- Run one stricter-gate high15/contact-anchor smoke with `CONTACT_ALIGN_THRESHOLD=0.035`, tighter left/right/balance gates, and a longer alignment budget. If this still fails, implement a staged controller patch.

## 2026-06-14T06:14:12Z - strict-center close-gate smoke

Goal:
- Verify whether the existing controller works when close is delayed until the finger center is actually near the cube center, instead of only approximately balanced around it.

Hypothesis:
- The previous contact-anchor runs closed with finger-center-to-cube around `0.063m`; this is too far. A `0.035m` center gate should force the gripper over/around the cube before close.

Version Control:
- implementation_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- remote_worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`

Command / Job:
- command base: source-orientation, `VARIANT=center_high15`, `CONTACT_GATE_MODE=left_right`, `CONTACT_ALIGN_THRESHOLD=0.035`, `FINGER_GATE_MAX_DISTANCE=0.065`, `FINGER_GATE_BALANCE_THRESHOLD=0.010`, `CONTACT_ALIGN_STEPS=320`, `CLOSE_HOLD_REFERENCE=contact_anchor`, explicit cube XY `[-0.36, -0.12]`.
- job_id `1029191`: `franka_cube_rgb_center_z047_sourceori_lr_anchor_high15_strict_ep37_20260614_0614`.

Next:
- Submit strict high15 smoke and inspect metrics/video.
## 2026-06-14T06:24:19Z - cube reset top-down posture correction

Goal:
- Fix the cube task default Franka reset so the gripper initializes upright and points down, rather than pitched forward after the base-z change.

Hypothesis:
- The previous cube reset joint set kept high table clearance but used `panda_joint6 ~= 3.04`, which leaves the hand visually pitched forward. A top-down Franka posture with `panda_joint6 ~= 1.5` should keep the raised base while aligning the EE local z-axis with world down.

Change:
- Updated only the cube task reset joints in `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`.
- Added `reset_gripper_points_down` to `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, reporting reset EE quaternion, reset tool local z-axis, and max/mean tilt in degrees.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- worklog: `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart-no-phase-rgb.md`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `dfc9c7f58650d0efc9ed2232c6f676f114ce9fce`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, `dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`, this worklog
- remote_commit/status: pending

Command / Job:
- command: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py dextrah_lab/rl_games/validate_franka_cube_grasp_env.py`
- command: `bash -n cluster/sbatch_validate_franka_cube_grasp_env_1gpu.sh`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: n/a

Result:
- status: local checks passed
- metrics/artifacts: py_compile and shell syntax succeeded.
- key evidence: validator now has an explicit posture gate; cluster validation pending.

Analysis:
- The prior reset validation only measured finger/table clearance and reward predicates, so it could pass while the gripper was pitched forward. The new gate should fail any reset whose local tool z-axis is more than 12 degrees away from world down.

Next:
- Commit, deploy exact commit to l401, and run a short validation job with video/metrics. If the measured reset tilt still fails, tune the cube joint reset again based on the reported quaternion/axis.

Follow-up Result:
- implementation_commit: `9a2947ffe6ef48e946451d9bce6de8def9da7ec9`
- push/pull: pushed to GitHub and pushed directly to l401 NFS repo; remote worktree checked out detached at the same commit.
- validation job `1029192`, run `franka_cube_reset_topdown_z047_validate_20260614_0626`, failed the new posture gate as intended:
  - `reset_tool_tilt_deg_max=17.5882`
  - `reset_tool_z_axis_w=[-0.2989, -0.0442, -0.9533]`
  - `finger_table_clearance_min=0.3054`
- local fetched artifact: `cluster_results/l401/franka_cube_reset_topdown_z047_validate_20260614_0626/metrics.json`

Analysis:
- The intermediate `q=[0,-1.3,0,-2.5,0,1.5,0.8]` reset improved over the visible ~45 degree pitch but still pointed the gripper forward by ~18 degrees. The validator caught this correctly; do not loosen the threshold.

Next:
- Use the one-process Isaac posture sweep to pick a measured top-down joint set, patch the cube config again, and rerun validation.

## 2026-06-14T06:34:00Z - measured top-down reset sweep

Goal:
- Find a cube reset joint posture whose reset EE local z-axis is actually aligned with world down in Isaac, not just visually plausible.

Hypothesis:
- The gripper pitch is primarily controlled by the `q2/q4/q6` relationship. A canonical Panda top-down posture or the source CuRobo row should produce near-zero tilt.

Change:
- No committed repo code changes for the sweep itself; used a scratch Isaac script under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_reset_posture_sweep_20260614_0634`.
- Patched local cube config after the sweep to the canonical symmetric top-down posture:
  - `panda_joint1=0.0`
  - `panda_joint2=-0.785398`
  - `panda_joint3=0.0`
  - `panda_joint4=-2.356194`
  - `panda_joint5=0.0`
  - `panda_joint6=1.570796`
  - `panda_joint7=0.785398`

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `9a2947ffe6ef48e946451d9bce6de8def9da7ec9`
- implementation_commit: pending
- push/pull: pending
- changed_files: `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`, this worklog
- remote_commit/status: pending

Command / Job:
- job_id: `1029195`
- command: scratch `posture_sweep.sbatch` under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_reset_posture_sweep_20260614_0634`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/validations/franka_cube_reset_posture_sweep_20260614_0634`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/franka_cube_posture_sweep_1029195.out`
- artifacts: `posture_sweep_summary.json`

Result:
- status: passed sweep
- metrics/artifacts:
  - `classic_down_pi`: tilt `0.0 deg`, local z axis approximately `[0, 0, -1]`, finger-table clearance `0.2559 m`.
  - `source_ep37`: tilt `0.0 deg`, local z axis approximately `[0, 0, -1]`, finger-table clearance `0.3001 m`, but includes episode-specific lateral/yaw joint offsets.
  - `sym_source_q7_0`: tilt `0.2307 deg`, finger-table clearance `0.3023 m`.
- key evidence: canonical top-down pose achieves exact down-axis without depending on a specific demonstration row.

Analysis:
- The previous `q6=1.5` candidate still had a measurable forward component. In the sweep, reducing the effective pitch through `q6=1.20` or `q4=-2.80` also gave zero tilt, but those were less canonical. The standard `[-pi/4, -3pi/4, pi/2, pi/4]` arm pattern is a clean, symmetric reset and remains well above the table after the cube-specific base-z raise.

Next:
- Commit the canonical reset patch, deploy it to l401, and rerun `validate_franka_cube_grasp_env.py` so `reset_gripper_points_down` passes.
