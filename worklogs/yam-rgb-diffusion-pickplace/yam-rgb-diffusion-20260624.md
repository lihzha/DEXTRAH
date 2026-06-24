# Worklog - yam-rgb-diffusion-pickplace / yam-rgb-diffusion-20260624

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/yam-rgb-diffusion-20260624
- branch: codex/yam-rgb-diffusion-pickplace/yam-rgb-diffusion-20260624
- base_commit: 49c769a603ad2d10c2d3f5f03e566945dfa4359b
- created: 2026-06-24T06:52:13Z

## 2026-06-24 Initial Scope

- goal: build a single-object YAM pick-and-place RGB diffusion-policy data path for sim2real transfer.
- user requirements: object on robot-right table side (-Y), randomized bin on robot-left table side (+Y), randomized object/bin/camera/texture/lighting, wrist D405 plus external scene RGB streams, 500 final trajectories, L40 photoreal replay after cheaper trajectory generation, no privileged policy inputs, no phase/progress inputs, `n_obs_steps=1`, image resolution at least 256.
- isolation: using this agent-owned worktree and branch; the source checkout has unrelated dirty YAM planner/demo edits and will not be modified.
- planned validation before scale-up: syntax checks, shell checks, one-trajectory smoke, RGB artifact inspection, then bounded shard scale-up.

## 2026-06-24T07:10:15Z Implementation Pass

- implemented single-YAM object spawn per-axis randomization so the policy setup can constrain the object to robot-right negative Y while preserving existing square randomization behavior for old configs.
- extended `render_tabletop_clutter_settle_video.py` with YAM policy scene randomization: object region, randomized goal-bin position/size/height on robot-left positive Y, table/ground/bin material color, dome/key light intensity, key-light direction, and scene-camera jitter around the right-far negative-Y view.
- added stable-scene bin restoration before replay env creation so A100-generated randomized bins are reused exactly during L40 RGB replay.
- added trajectory dataset `robot_state` as non-privileged proprioception: joint positions, joint velocities, TCP pose, and gripper width; privileged object/bin state remains only as debug/validation fields in replay NPZs.
- added two RGB streams during replay dataset recording: `scene_rgb` and `wrist_rgb`; the wrist stream is currently a metadata-labelled `virtual_tcp_relative_d405_view` driven from the TCP pose rather than a persistent single-YAM USD camera prim.
- added `make_yam_rgb_policy_shards.py` to convert replay NPZs into policy-only per-trajectory shards with `scene_rgb`, `wrist_rgb`, `robot_state`, 7D relative EE action, and `episode_ends`.
- added `YamRgbShardedDataset` plus `yam_pickplace_rgb_dp.yaml` for official Diffusion Policy training with `n_obs_steps=1`, two 256x256 RGB streams, 24D robot state, and no phase/progress inputs.
- added non-array cluster wrappers:
  - A100 trajectory generation: `cluster/sbatch_collect_yam_single_object_policy_demos_1gpu.sh`
  - A100 submitter: `cluster/submit_yam_single_object_policy_demos_no_array_a100.sh`
  - L40 photoreal replay: `cluster/sbatch_replay_yam_policy_rgb_l40_1gpu.sh`
  - L40 submitter: `cluster/submit_yam_policy_rgb_replay_no_array_l401.sh`
  - RGB DP training: `cluster/sbatch_train_yam_pickplace_rgb_dp_1gpu.sh`
- validation passed:
  - `bash -n` on all touched/new cluster wrappers.
  - `python3 -m py_compile` on touched Python modules.
  - `git diff --check`.
  - synthetic replay NPZ -> YAM RGB policy shard manifest -> `YamRgbShardedDataset` sample using `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python`; observed shapes: scene `(4,3,256,256)`, wrist `(4,3,256,256)`, robot `(4,24)`, action `(4,7)`.

## Pending Before Scale-Up

- no Slurm jobs launched yet from this worktree.
- before launching cluster jobs, commit/push this branch and deploy the exact commit to the cluster checkout used as `CODE_NFS`.
- recommended next validation is a one-row A100 collection smoke followed by one-row L40 `quality` replay and artifact inspection of `scene_rgb`, `wrist_rgb`, metadata, metrics, and video.
- for a stricter physical camera model, replace the current TCP-relative wrist viewpoint with the bimanual YAM `CameraCfg`/D405 prim path after a single-YAM wrist camera parent convention is finalized.

## 2026-06-24 Visualization Smoke Launch

- committed and pushed implementation: `8edc9727c75f72ba49a28bed9b02b30c7db09122`.
- deployed exact commit to remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-20260624`.
- A100 collection smoke:
  - job_id: `29466685`
  - batch_name: `yam_rgb_vis_smoke_20260624T072333Z`
  - batch_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_rgb_vis_smoke_20260624T072333Z`
  - log: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_policy_demo_29466685.out`
  - command shape: `sbatch --export=ALL,CODE_NFS=<agent-worktree>,RESULTS_NFS=<results>,CODE_COMMIT=8edc9727...,TOTAL_TARGET=1,SHARD_COUNT=1,SHARD_INDEX=0,SHARD_TARGET=1,MAX_ATTEMPTS=10,START_SEED=26062400 ... sbatch_collect_yam_single_object_policy_demos_1gpu.sh`
  - success criteria: one accepted row in `shard_000/accepted_demos.jsonl`, valid stable scene, planned trajectory, replay dataset, validation metrics, and MP4.

## 2026-06-24 Visualization Smoke Result

- accepted source demo: L40 job `1041670`, batch `yam_rgb_vis_l40_close_smoke_20260624T074746Z`, seed `26062800`, validation status `accepted`.
- axis check: object initial Y `-0.1714` (robot-right/negative-Y), randomized goal-bin center Y `0.1305` (robot-left/positive-Y), final object position inside bin.
- validation checks passed: `all_objects_inside_bin`, `all_objects_lifted`, `rgb_nonblank`, `scripted_target_transport_disabled`, finite joint/clearance checks, and not truncated final.
- wrist-camera inspection found the first virtual TCP-relative wrist stream was nonblank but poorly aimed. Patched `render_tabletop_clutter_settle_video.py` in commit `2c43c163fb4444212c613d34ffb470b8a192542c` to use a parented IsaacLab D405 `Camera` sensor on `/World/envs/env_0/Robot/arm/link_6` with the existing MolmoAct2 D405 intrinsics and mount pose.
- accepted D405 RGB replay: L40 job `1041671`, batch `yam_rgb_vis_l40_d405_smoke_20260624T080057Z`, accepted `1`, failed `0`, rendering mode `quality`, output resolution `256x256`.
- final D405 NPZ shapes: `scene_rgb`, `wrist_rgb`, and `rgb` are `[1417, 256, 256, 3]`; `robot_state` is `[1417, 1, 24]`; `action` is `[1417, 1, 7]`. `wrist_rgb` nonzero fraction: `0.999968`.
- local artifacts: `/home/lzha/code/cluster_results/l401/yam_rgb_vis_l40_d405_smoke_20260624T080057Z/`.
- `viz-open` URLs:
  - contact sheet: `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_d405_smoke_20260624T080057Z/observation_contact_sheet.png`
  - scene+wrist observation video: `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_d405_smoke_20260624T080057Z/observation_streams_side_by_side.mp4`
  - scene-camera replay: `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_d405_smoke_20260624T080057Z/replay/yam_rgb_replay.mp4`
  - randomized environment settle: `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_close_smoke_20260624T074746Z/settle/settle.mp4`

## 2026-06-24T08:48:56Z Camera Fit And Visual Randomization Loop

- confirmed rendering mode: the L40 replay wrapper uses Isaac Lab
  `--rendering_mode quality`, which is the highest AppLauncher preset exposed
  by the local Isaac Lab stack. This is not a custom offline path-traced
  accumulation pass.
- camera-fit run `1041672`, batch
  `yam_rgb_vis_l40_camfit_smoke_20260624T081842Z`, replayed one accepted demo
  at commit `32b848ffe6add9bc94cc20808f22b268879a2e8e` with scene camera near
  `[-0.6684, -0.6951, 0.8556]` looking at `[-0.3267, 0.0232, 0.0086]`.
  Artifact inspection showed better downward framing but still visible blue
  floor/background wedges and a partial robot crop.
- tightened-camera run `1041673`, batch
  `yam_rgb_vis_l40_camfit2_smoke_20260624T083000Z`, replayed one accepted demo
  at commit `303d5ce8508bf38863ddd251fc59f777039c75e1`, `quality` rendering,
  `1024x1024` render resolution, camera near
  `[-0.5947, -0.5258, 0.8165]` looking at `[-0.2975, 0.0319, -0.0143]`.
  Cluster-side image statistics found mean blue/background fraction increased
  from roughly `0.2895` to `0.3521`; source diagnosis is that camera-only
  tightening exposes simulator floor/background because the real table region
  is smaller than the square scene-camera frustum.
- implementation response: added render-only YAM policy tabletop surround,
  procedural tabletop texture strips, and neutral randomized background walls
  to `render_tabletop_clutter_settle_video.py` and the settle/replay wrapper.
  These USD cubes are visual-only and do not add collision APIs, so they should
  change RGB domain coverage without changing trajectories or grasp validation.
- local validation passed: `python3 -m py_compile` on the touched render/eval
  modules, `bash -n` on the settle and L40 replay wrappers, and
  `git diff --check`.
- current blocker before launch: l401 SSH checks timed out, and the local
  branch is ahead of origin by the visual-surround commit plus this
  texture/background change. Next step is to commit, retry push/update of the
  l401 worktree, replay one accepted demo in `quality`, inspect frames/video,
  and then decide whether to scale to candidate data generation.
- launch update: committed and pushed final visual-randomization code through
  `4bf3071394cf851089e153dd951a29e792319413`; l401 could not fetch from
  GitHub due SSH key rejection, so the exact commits were deployed via Git
  bundle fetch into the agent worktree. Submitted L40 replay job `1041674`
  (`yamvis_surtex`) from remote worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-20260624`
  with batch `yam_rgb_vis_l40_surround_tex_smoke_20260624T0852Z`, source
  accepted JSONL
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_rgb_vis_l40_close_smoke_20260624T074746Z/shard_000/accepted_demos.jsonl`,
  `RENDERING_MODE=quality`, render resolution `1024x1024`, policy RGB
  `256x256`, surround size `2.25 x 2.05`, tabletop texture enabled, background
  walls enabled, result directory
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_policy_rgb_replays/yam_rgb_vis_l40_surround_tex_smoke_20260624T0852Z`,
  and log
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/yam_policy_rgb_1041674.out`.
- result update: job `1041674` completed with accepted RGB replay count `1`,
  failed `0`, `quality` rendering, `1024x1024` render resolution, and `256x256`
  recorded scene/wrist streams. Local artifacts are under
  `/home/lzha/code/cluster_results/l401/yam_rgb_vis_l40_surround_tex_smoke_20260624T0852Z/`.
  The scene replay contact sheet shows the table/surround, bin, object, and
  most of the YAM arm dominate the frame; only a narrow wall/background strip
  remains. Wrist D405 observations are nonblank and useful during object/bin
  interactions. `viz-open` URLs:
  `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_surround_tex_smoke_20260624T0852Z/inspection/scene_replay_video_sheet.png`
  and
  `http://localhost:8765/view?path=cluster_results/l401/yam_rgb_vis_l40_surround_tex_smoke_20260624T0852Z/validation/yam_rgb_replay.mp4`.
- dataset evidence: replay metadata reports `scene_rgb` and `wrist_rgb` arrays
  `[1417, 256, 256, 3]`, `robot_state` `[1417, 1, 24]`, and `action`
  `[1417, 1, 7]`; the old blue/background proxy dropped to about `0.068`.
  This is good enough to move from visual-fit work into candidate data
  generation.
- timing cleanup: before candidate generation, patched the planner path so the
  shared multi-object planner forwards `close_frames`, `hold_frames`, and
  `hold_after_close_frames` into the per-object YAM planner, and the shared
  collector records those timing knobs. The single-object policy wrapper now
  defaults to `START_GUARD_FRAMES=12`, `CLOSE_FRAMES=36`, `HOLD_FRAMES=12`,
  `HOLD_AFTER_CLOSE_FRAMES=24`, `SCRIPTED_LIFT_FRAMES=120`,
  `MOVE_TO_BIN_FRAMES=220`, and `RETURN_TO_START_FRAMES=60` to reduce scripted
  stops while preserving enough close/drop dwell for physical validation.
- validation after timing cleanup passed: `python3 -m py_compile`,
  `bash -n`, and `git diff --check`.
- candidate data attempt: committed timing cleanup as
  `bca4e017be20c44382b86917fccb5fbdab063e41`, pushed the branch, and deployed
  the exact commit to the l401/A100 agent worktree via Git bundle because l401
  still cannot fetch from GitHub. Launched A100 no-array candidate batch
  `yam_rgb_candidate_short_a100_20260624T0905Z` with jobs `29469215` and
  `29469216`, two shards, target `4`, and short timing active.
- candidate diagnosis: both shards rejected their first seed at planner stage
  before trajectory generation; per-seed summaries showed cuRobo goalset
  planning returned `None` with grasps available, which is a normal planning
  miss from the broader object pool, not evidence that the shorter trajectory
  timing broke validation. Cancelled both jobs before additional wasted A100
  time.
- follow-up patch: set dedicated single-object policy wrapper defaults to the
  previously validated high-yield object pool and attempt budget:
  `POOL_MAX_ASSETS=512`, `POOL_MAX_GRASP_WIDTH_P95=0.110`, and
  `MAX_ATTEMPTS=180`, while keeping the short motion timing.
- high-yield relaunch: committed pool fix as
  `f9ec6e82d4ec00fff1ce9f33057e858f04db32a6`, deployed via Git bundle, and
  launched A100 batch `yam_rgb_candidate_hiyield_a100_20260624T0913Z` with jobs
  `29469493` and `29469495`. Both first seeds again rejected at planner stage.
  The logs show the high-yield pool was active, so the remaining problem is
  reach/planning distance from the broad Y ranges; one sampled bin was near
  `Y=0.455`.
- follow-up patch: narrow only the dedicated single-object policy defaults to
  object Y `[-0.30, -0.12]` and bin Y `[0.08, 0.30]`, still keeping object on
  robot-right negative Y and bin on robot-left positive Y, but closer to the
  previously accepted smoke range.

## 2026-06-24T11:10:02Z Final Short Candidate And Metadata Smoke

- follow-up object/bin fixes: added manifest filters for minimum XY/Z extents,
  max XY aspect, and max Z-to-min-XY aspect; set compact single-object defaults
  (`POOL_MAX_XY_RADIUS=0.060`, `POOL_MIN_XY_HALF_EXTENT=0.020`,
  `POOL_MIN_Z_HALF_EXTENT=0.032`, `POOL_MAX_XY_ASPECT=2.0`,
  `POOL_MAX_Z_TO_MIN_XY_ASPECT=1.8`); enlarged randomized bin sizes to
  X `[0.34,0.46]`, Y `[0.30,0.42]`; and biased drop target with
  `SCRIPTED_BIN_DROP_Y_OFFSET=-0.04`.
- final A100 source smoke:
  `yam_rgb_candidate_final_short_a100_20260624T103439Z`, jobs `29472633` and
  `29472637`, accepted both shards on first attempt. Combined source rows:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_rgb_candidate_final_short_a100_20260624T103439Z/accepted_demos_combined.jsonl`.
- L40 fixed replay:
  `yam_rgb_l40_final_short_fixed_20260624T104806Z`, job `1041723`, accepted
  `2`, failed `0`, after commit `7d98de6d` fixed nested wrapper stdin
  consumption. Render mode was `quality`, render frames were `1024x1024`, and
  policy observations were `256x256`.
- inspected local observation sheets and videos under
  `/home/lzha/code/cluster_results/l401/yam_rgb_l40_final_short_fixed_20260624T104806Z/`.
  Scene framing is good for sim2real: table/surround/bin/object/most robot
  dominate the view and only a narrow wall/background strip remains. Wrist D405
  stream is nonblank and sees the object near grasp/drop.
- replay dataset shapes:
  row 0 `scene_rgb`/`wrist_rgb` `[845,256,256,3]`, `robot_state`
  `[845,1,24]`, `action` `[845,1,7]`; row 1 `scene_rgb`/`wrist_rgb`
  `[825,256,256,3]`, `robot_state` `[825,1,24]`, `action` `[825,1,7]`.
  Final object centers are inside the actual rendered randomized bin for both
  rows.
- metadata correction: replay first sampled a fresh pre-restore randomized bin
  and then restored the source stable-scene bin, leaving the old summary
  misleading. Commit `9da88796` updates `yam_policy_scene_randomization` so
  `goal_bin`/`source_bin` report the effective restored bins while preserving
  `pre_restore_goal_bin`; commit `54bcf185` makes the `creating_env` log use
  the same effective summary.
- validation after metadata fix: L40 metadata smoke `1041727`, batch
  `yam_rgb_l40_metadata_smoke_20260624T1104Z`, accepted `1`, failed `0`.
  Metrics confirm `metadata_bin_source=stable_scene_restore`,
  `yam_policy_scene_randomization.goal_bin == tabletop_clutter_summary.goal_bin`,
  render mode `quality`, render resolution `[1024,1024]`, `scene_rgb`/`wrist_rgb`
  `[845,256,256,3]`, and `robot_state` `[845,1,24]`.
- current commit deployed on the shared remote agent worktree:
  `54bcf185a534365e15bbfb8cace374541f6436b7`. Next step is the full
  500-trajectory A100 source run, then L40 quality replay from the accepted
  source rows.

## 2026-06-24T11:34:00Z Production Pre-Wave And Reach Tuning

- first full-source attempt `yam_rgb_source500_a100_20260624T1110Z` submitted
  ordinary jobs until Slurm hit `QOSMaxSubmitJobPerUserLimit`; the 20 submitted
  jobs were then pending behind maintenance, so they were cancelled before
  consuming GPU time.
- relaunched `yam_rgb_source_prewave200_a100_20260624T1118Z` with 20 ordinary
  A100 jobs, target 10 accepted demos per shard, from commit
  `567be544e2a87cc4a12ab88a9b4b0934cde65ea3`.
- early diagnostics showed 10 durable accepted demos after roughly 13 minutes
  across 20 running GPUs. The accepted rows validate single-object
  table-right-to-bin-left behavior; failures were mostly cuRobo goalset
  planner misses with grasp candidates present, not rendering or dataset
  failures.
- patched the single-object policy wrapper for subsequent waves to improve
  production yield and drop margin while preserving randomization: object X
  `[-0.33,-0.24]`, object Y `[-0.32,-0.23]`, bin X `[-0.32,-0.12]`, bin Y
  `[0.10,0.26]`, bin sizes X `[0.38,0.48]` and Y `[0.36,0.46]`, bin height
  `[0.08,0.14]`, `MAX_PLAN_ATTEMPTS=128`, centered drop
  `SCRIPTED_BIN_DROP_Y_OFFSET=0.0`, and explicit visual surround
  `YAM_POLICY_TABLETOP_SURROUND=True`, size `2.25 2.05`.
- validation after the wrapper edit passed: `bash -n
  cluster/sbatch_collect_yam_single_object_policy_demos_1gpu.sh` and
  `git diff --check`.
- deployed commit `05fb97597a9b977c566d6987ceea6056cf861296` into sibling
  remote worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-20260624-tuned-05fb9759`
  to avoid changing code underneath the running pre-wave.
- cancelled five zero-accept old pre-wave shards and submitted tuned mini-wave
  `yam_rgb_source_tuned_smoke40_a100_20260624T1138Z`, jobs `29473187`,
  `29473189`, `29473190`, `29473191`, and `29473192`, with target `8` per
  shard and 95 minute walltime.
- the first fresh-worktree tuned attempts hit one-time asset-copy races in the
  YAM asset directory; subsequent retries created scenes and planned normally
  after the asset directory was populated.
- after roughly six minutes, tuned had two durable accepted rows and no
  validation rejects. Their final object centers were inside the restored bins
  with comfortable margins; remaining tuned misses were planner/candidate
  misses.
- follow-up patch in progress: enable `YAM_ALLOW_LIFT_FILTER_FALLBACK=True`
  for future waves because some tuned planner rejects were caused by
  `YAM aperture filtering removed all grasps`; replay validation will continue
  to filter failed lifts/drops.
- committed fallback default as
  `f91eb2630efd26fd95570512676bd105723c14ce`, deployed it to sibling worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-20260624-fallback-f91eb263`,
  and copied warmed YAM mesh assets from the tuned worktree to avoid fresh
  worktree asset-copy races.
- launched fallback smoke
  `yam_rgb_source_fallback_smoke32_a100_20260624T1147Z`, jobs `29473246`-
  `29473249`. Fallback became the best-yielding active cohort.
- created six-row source visual sample
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_rgb_source_visual_sample_20260624T1158Z.jsonl`
  covering old pre-wave, tuned, and fallback accepted rows. Submitted L40
  quality replay sample `yam_rgb_l40_source_visual_sample_20260624T1200Z`,
  jobs `1041731`-`1041733`, with `quality` rendering, `1024x1024` render
  frames, and `256x256` scene/wrist RGB observations. These jobs are pending
  behind L40 maintenance.
- source progress at latest check: pre-wave `75`, tuned `12`, fallback `17`,
  for `104` accepted rows total. Fallback wave 2
  `yam_rgb_source_fallback_wave2_16_a100_20260624T1218Z` submitted jobs
  `29473409` and `29473410` after replacing two low-yield old shards; those
  jobs are pending behind maintenance.

## 2026-06-24T12:34:00Z Post-Settle Source Filter

- active source monitoring showed at least `106` total accepted rows across
  pre-wave/tuned/fallback cohorts. Fallback remains the strongest cohort; its
  accepted validation metrics pass nonblank RGB, object lifted, object inside
  randomized bin, no truncation, and required trajectory dataset keys.
- fallback planner rejects are dominated by cuRobo goalset no-solution cases.
  Success/failure comparison showed a subset of failures have target root poses
  that drifted outside the intended right-side object region after settle or
  dipped below the tabletop, wasting expensive planning time.
- patched `cluster/sbatch_collect_yam_objaverse_demos_1gpu.sh` with an
  opt-out `POST_SETTLE_TARGET_FILTER` that reads `stable_scene.json` after
  settle and before planning. It logs rejected attempts as
  `stage=post_settle_filter` with a JSON diagnostic.
- enabled that filter in
  `cluster/sbatch_collect_yam_single_object_policy_demos_1gpu.sh` with
  `POST_SETTLE_TARGET_RANGE_MARGIN=0.035`, `POST_SETTLE_TARGET_MIN_Z=0.0`,
  and `POST_SETTLE_TARGET_MAX_Z=0.085`. Effective X/Y ranges are derived from
  the single-object spawn windows plus the margin.
- retrospective check on the current fallback batch: rejected `0/22` accepted
  demos and `4/22` planner failures (`2` below-table, `1` X drift, `1` Y
  drift). Local checks passed: both affected shell scripts with `bash -n` and
  `git diff --check`.
