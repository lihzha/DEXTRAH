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
- committed as `c22bfb637016a8074c28ff0ebf6d3a38477fc827`. Since `a1001`
  could not authenticate to GitHub, deployed with a complete Git bundle into
  the remote canonical repo and created detached worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-20260624-filter-c22bfb63`.
  The remote worktree passed both shell syntax checks and has the warmed YAM
  assets copied into `dextrah_lab/assets/yam`.
- cancelled pending unfiltered jobs `29473409` and `29473410`, then submitted
  filtered ordinary jobs `29473480` and `29473481`, batch
  `yam_rgb_source_filter_wave2_16_a100_20260624T1236Z`, target `16` accepted
  demos. Both jobs are pending behind A100 maintenance; Slurm accepted them
  with the recurring stale-data warning.
- rerouted the same batch to `backfill_singlenode` after Slurm projected the
  first filtered jobs to start at `19:00`. Replacement jobs `29473535` and
  `29473537` are also pending with `ReqNodeNotAvail, Reserved for maintenance`
  and `StartTime=Unknown`, so this is an A100 maintenance/scheduler block.
- fetched four accepted fallback source replays and generated local inspection
  sheet
  `/home/lzha/code/cluster_results/a1001/yam_rgb_source_fallback_smoke32_a100_20260624T1147Z/sample/inspection/fallback_source_motion_sheet.png`.
  `viz-open` URLs were produced for the sheet and one representative MP4.
  Sample datasets have nonblank `rgb` `[226,120,160,3]`, finite
  `robot_state` `[900,1,24]`, finite `action` `[900,1,7]`, and coherent
  right-side object to left-side bin motion.

## 2026-06-25T09:39:37Z Gripper-Down Qpos And Dynamic Drop Tuning

- updated the YAM default/home qpos to the requested gripper-down pose
  `(0.0, 1.0, 1.0, -1.5, 0.0, 0.0)` for the six arm joints, with fingers
  open at `0.0`, and made the default demo replay mode `dynamic`.
- fixed a planner/sim base mismatch in `plan_yam_graspgenx_curobo.py`:
  planner YAM base now matches the single-YAM policy environment base
  `[-0.65, -0.25, 0.01]`. The corrected qpos/dynamic smoke
  `29480957`, batch `yam_qpos_dynamic_smoke_basefix_retry_20260625T083200Z`,
  accepted on the first attempt.
- full 500-source attempt before the place fix produced no accepted demos
  because lifted objects often never received a bin-transport segment. The
  failing seed `67000000` showed `scripted_place.success=false` from a strict
  IK tolerance despite the approximate solved object drop being inside the
  randomized bin.
- patched scripted bin placement to accept approximate IK only when the solved
  object drop point is inside the randomized bin, and to reject planner outputs
  that still lack a bin transport/open segment for `pick_and_drop_in_bin`.
  Commit deployed on A100 via bundle:
  `e2688b91236363314c5d0b4efab851bc854ac43d`.
- the same seed then transported to the bin but dynamic replay overshot the
  far +Y bin wall with zero drop offset. A seed-specific smoke with
  `SCRIPTED_BIN_DROP_Y_OFFSET=-0.08`, gripper gains
  `stiffness_scale=2.0`, `damping_scale=0.25`, `effort_scale=5.0`, and
  dynamic replay accepted on the first attempt:
  `29481883`, batch
  `yam_qpos_dynamic_placefix_seed67000000_yoff08_retry_20260625T093214Z`.
  Validation passed all checks; final object center
  `[-0.1153, 0.2435, 0.0641]` was inside bin center
  `[-0.1816, 0.1971]`, size `[0.2942, 0.1983]`.
- visual smoke artifacts copied locally:
  `/home/lzha/code/cluster_results/a100/yam_yoff08_seed67000000/yam_pick_place.mp4`
  and contact sheet
  `/home/lzha/code/cluster_results/a100/yam_yoff08_seed67000000/contact_sheet.jpg`.
  Inspection shows the scene camera sees the object initially, mostly table
  and robot, no visible room background, and a plausible continuous
  pick-transport-drop motion.
- launched current 500-source A100 collection batch
  `yam_single_object_qpos_dynamic_yoff08_500_20260625T093853Z` from commit
  `e2688b91236363314c5d0b4efab851bc854ac43d`, with `TOTAL_TARGET=500`,
  `SHARD_COUNT=20`, `MAX_CONCURRENT=4`, `START_SEED=69000000`,
  `SCRIPTED_BIN_DROP_Y_OFFSET=-0.08`, same gripper gains, and bad-node
  excludes `batch-block7-01934,batch-block5-00055,batch-block7-01554`.
  First submitted shards are `29481954`, `29481955`, `29481957`, and
  `29481958`.

## 2026-06-25T09:58:31Z Full Source Wave Monitoring

- stopped the conservative no-array submitter after the first four shards and
  manually submitted remaining shards `4`-`19` into the same batch directory
  with the same commit/settings, because the initial four-concurrent throttle
  was too slow for the 500-demo target. Slurm accepted all remaining shards;
  20 shard jobs are running under prefix `yam_yoff08_500`.
- aggregate monitor at `09:58:31Z`: `19` accepted, `46` rejected. Reject
  stages were `planner=31`, `post_settle_filter=10`, `validation=5`.
  Validation rejects were mostly real missed lifts or out-of-bin drops; only
  one was a marginal clearance-only reject, so the validator was left
  unchanged.
- current accepted source visual sample copied to
  `/home/lzha/code/cluster_results/a100/yam_yoff08_500_sample/`; contact sheet
  `contact_sheet.jpg` shows the object visible at the start, robot/bin/table
  visible throughout, and only a very small non-table edge sliver in some
  frames.
- L40 direct SSH remains blocked from both local host and A100:
  `l401/l402/l403/l40data` all deny public-key/password auth, and no local
  SSH agent is available to forward. A100 Slurm does not expose the standalone
  L40 hosts, so high-quality RGB replay is still gated on resolving L40 access
  once source rows are ready.

## 2026-06-25T10:43:03Z Expanded Source Wave

- aggregate monitor at `10:43:43Z` showed the original 20 shards still
  running, with `91` accepted, `214` rejected, and reject stages
  `planner=132`, `validation=44`, `post_settle_filter=38`.
- inspected a representative planner reject. The failure was a genuine cuRobo
  approach-planning miss (`Planning to approach pose failed`) with five grasp
  candidates after filtering, not a scene/runtime crash. Current validator and
  scene settings were left unchanged.
- submitted additional independent shard indices `20`-`49` into the same
  batch directory using the same commit
  `e2688b91236363314c5d0b4efab851bc854ac43d`, qpos, dynamic replay, gripper
  gains, bad-node excludes, and `SCRIPTED_BIN_DROP_Y_OFFSET=-0.08`.
  Submitted jobs: `29483175`, `29483176`, `29483177`, `29483178`,
  `29483180`, `29483182`, `29483183`, `29483185`, `29483187`, `29483188`,
  `29483189`, `29483190`, `29483192`, `29483194`, `29483196`, `29483197`,
  `29483198`, `29483200`, `29483201`, `29483202`, `29483203`, `29483204`,
  `29483207`, `29483208`, `29483209`, `29483210`, `29483212`, `29483214`,
  `29483215`, and `29483216`.
- Slurm started all 30 extra shard jobs immediately. It emitted an advisory
  stale-data quota warning on submission, but accepted the jobs.
- mid-run inspection at `251` accepted rows fetched source row `249`
  (`shard_048`, seed `73800006`) to
  `/home/lzha/code/cluster_results/a100/yam_yoff08_500_mid_sample/`.
  `ffprobe` reported a `1280x720`, `91` frame, `7.58s`, `12 FPS` video.
  Contact sheet and MP4 were opened with `viz-open`. Visual inspection: the
  source replay has the object visible at the beginning, continuous robot
  motion into the left-side bin, and a frame dominated by table/bin/robot with
  no meaningful background. Empty black cells in the contact sheet are unused
  tile slots, not video frames.
- final cutoff loop reached `500` accepted rows at `12:31Z`, wrote and
  verified
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_single_object_qpos_dynamic_yoff08_500_20260625T093853Z/accepted_500.jsonl`
  with exactly `500` lines, and wrote
  `accepted_500_summary.json`. Local copies are under
  `/home/lzha/code/cluster_results/a100/yam_yoff08_500_accepted/`.
  The selected rows are all single-object demos, with seeds spanning
  `69000001` through `73900034`.
- canceled remaining source jobs after the aggregate file was verified. One
  source job (`29484661`, shard `004`) briefly relaunched/requeued after the
  bulk cancel; it was explicitly canceled and the source queue then cleared.
- retried L40 access for the high-quality replay stage. Direct local SSH to
  `l401`, `l402`, `l403`, and `l40data` still fails with
  `Permission denied (publickey,password)`. A100 cannot resolve those aliases.
  Local SSH config only contains direct `10.49.119.*` host mappings with
  `ForwardAgent`; `ssh-add -l` reports no local agent, and explicit
  `~/.ssh/id_ed25519` and `~/.ssh/google_compute_engine` attempts to `l401`
  are also rejected. High-quality L40 replay, RGB shard conversion, diffusion
  training, and evaluation remain blocked on L40 authentication.

## 2026-06-25T16:50:00Z L40 Camera Candidate Loop And Patch

- L40 access is now available from this environment through `ssh l401`; the
  user's interactive `sshl401` wrapper/alias is not defined in the non-
  interactive Codex shell, but direct `ssh l401` reaches
  `oci-ord-cs-004-login-01` without a password prompt.
- rendered and inspected L40 quality-mode one-row RGB replay candidates from
  commit `0053cad68f8bf24c7f54ca3b1eff6879649465ec` with dynamic replay,
  qpos-start source rows, and gripper gains
  `YAM_GRIPPER_STIFFNESS_SCALE=2.0`,
  `YAM_GRIPPER_DAMPING_SCALE=0.25`,
  `YAM_GRIPPER_EFFORT_SCALE=5.0`.
  - `yam_rgb_camera_candidate3_20260625T162944Z`
    (`eye=(-0.51,-0.16,0.72)`, `target=(-0.24,-0.16,0.02)`) accepted
    1/1 but still exposed a right-side off-table strip and hid the initial
    object behind the robot.
  - `yam_rgb_camera_candidate4_20260625T163659Z`
    (`eye=(-0.50,-0.08,0.72)`, `target=(-0.23,-0.08,0.03)`) accepted
    1/1 and improved over candidate 3 but kept a top-right table-edge sliver.
  - `yam_rgb_camera_candidate5_20260625T163659Z`
    (`eye=(-0.50,0.04,0.74)`, `target=(-0.22,0.04,0.03)`) accepted
    1/1 and improved robot/bin coverage but exposed a top off-table strip.
  - `yam_rgb_camera_candidate6_20260625T164313Z`
    (`eye=(-0.50,0.04,0.68)`, `target=(-0.25,0.04,0.03)`) accepted
    1/1 and gave the best scene camera: high-resolution frames are dominated
    by table/bin/robot with no meaningful visible background while preserving
    x-parallel camera-axis projection.
- local visual evidence:
  - candidate 6 contact sheet:
    `/home/lzha/code/cluster_results/l401/yam_rgb_camera_candidate6_20260625T164313Z/inspection/candidate6_scene_wrist_contact_sheet.jpg`
  - candidate 6 validation video:
    `/home/lzha/code/cluster_results/l401/yam_rgb_camera_candidate6_20260625T164313Z/validation/yam_rgb_replay.mp4`
  - candidate 6 tensors: `scene_rgb` and `wrist_rgb` are both
    `(825,256,256,3)` uint8 and nonblank.
- source-row distribution diagnostic over the first 500 accepted A100 demos:
  target `y` spans roughly `[-0.267,-0.090]` with median `-0.177`.
  This explains why the hard row-0 object remains weakly visible at the start
  even with the improved camera. The next source collection should keep the
  object on robot-right but closer to the table center.
- patched defaults in `render_tabletop_clutter_settle_video.py`,
  `sbatch_render_tabletop_clutter_settle_video_1gpu.sh`,
  `sbatch_collect_yam_single_object_policy_demos_1gpu.sh`, and
  `sbatch_replay_yam_policy_rgb_l40_1gpu.sh`:
  candidate-6 camera base, reduced camera jitter
  `(0.018,0.018,0.018)` / `(0.012,0.012,0.012)`, and single-object target
  `YAM_POLICY_OBJECT_Y_RANGE=-0.16 -0.04` for future data generation.
- validation passed locally:
  `python3 -m py_compile dextrah_lab/rl_games/render_tabletop_clutter_settle_video.py`
  and `bash -n` on the affected Slurm wrappers and submitters.
- committed patch as `92fad5038b4e80c48b1129b5c4126dd938c68e5b` and pushed
  branch `codex/yam-rgb-diffusion-pickplace/yam-rgb-diffusion-20260624`.
  Deployed the exact commit by Git bundle to:
  - L40 worktree:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-l40-0053cad6`
  - A100 worktree:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-a100-92fad503`
- post-patch L40 default-camera smoke
  `yam_rgb_default_camera_postpatch_20260625T165236Z`, job `1041929`,
  accepted `1/1` using default camera randomization, quality rendering,
  dynamic replay, 256x256 scene+wrist RGB, and the same gripper gains.
  Visual inspection showed table-dominated frames with no meaningful scene
  background leakage. Local artifacts:
  `/home/lzha/code/cluster_results/l401/yam_rgb_default_camera_postpatch_20260625T165236Z/inspection/postpatch_default_scene_wrist_contact_sheet.jpg`
  and
  `/home/lzha/code/cluster_results/l401/yam_rgb_default_camera_postpatch_20260625T165236Z/validation/yam_rgb_replay.mp4`.

## 2026-06-25T16:59:00Z Centered-Y Source Regeneration Launch

- launched regenerated A100 source collection from commit
  `92fad5038b4e80c48b1129b5c4126dd938c68e5b` to improve initial object
  visibility before L40 RGB replay/training.
- batch:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_single_object_center_y_dynamic_500_20260625T165831Z`
- exact submit settings:
  `TOTAL_TARGET=500`, `SHARD_COUNT=50`, `MAX_CONCURRENT=50`,
  `START_SEED=79000000`, `JOB_NAME_PREFIX=yam_centery500`,
  `YAM_POLICY_OBJECT_Y_RANGE=-0.16 -0.04`,
  `SCRIPTED_BIN_DROP_Y_OFFSET=-0.08`, dynamic replay, and gripper gains
  `2.0/0.25/5.0`.
- Slurm accepted shards `0`-`21` before hitting
  `QOSMaxSubmitJobPerUserLimit`; submitted jobs are `29491998`, `29492000`,
  `29492001`, `29492002`, `29492003`, `29492004`, `29492006`, `29492007`,
  `29492009`, `29492010`, `29492011`, `29492012`, `29492013`, `29492014`,
  `29492015`, `29492016`, `29492017`, `29492018`, `29492019`, `29492020`,
  `29492021`, and `29492023`. Remaining shards `22`-`49` need rolling
  submission as the queue clears.
- early log checks on jobs `29491998`, `29492000`, `29492001`, and `29492002`
  confirm the new object-y range, dynamic replay mode, commit hash, and gripper
  gains. Startup warnings are standard headless Isaac warnings.

## 2026-06-25T17:58:00Z Source Collection Timeout Fix and Relaunch

- first source wave reached `81` accepted rows, but several shards hung inside
  a single settle attempt. Cancelled stale shards `004`, `007`, `014`, and
  `018`, then submitted replacement shards `022`-`026`.
- diagnosed that updating the shared A100 worktree from `92fad5038` to a newer
  commit while the original jobs were still running caused later attempts in
  those old jobs to fail the render wrapper's `CODE_COMMIT` guard. The failed
  attempts were recorded as settle rejects and did not produce validation
  artifacts. Accepted rows produced before the checkout mutation remain valid.
- patched `cluster/sbatch_collect_yam_objaverse_demos_1gpu.sh` with
  configurable per-stage timeouts:
  `SETTLE_TIMEOUT_SECONDS=600`, `PLANNER_TIMEOUT_SECONDS=900`,
  `REPLAY_TIMEOUT_SECONDS=900`, and `VALIDATE_TIMEOUT_SECONDS=180`.
  The timeout values are logged in `collector_start` metadata.
- validated with `bash -n` on the shared and single-object collection wrappers.
  Committed and pushed as `7e754bfc7dbea882ee4ffbb08f80f575105e1fcd`
  (`Add timeouts to YAM demo collection stages`).
- deployed commit `7e754bfc7` to the A100 checkout by Git bundle because the
  A100 host does not have GitHub SSH credentials.
- launched a new commit-matched wave with `CODE_COMMIT=7e754bfc7` and
  `MAX_ATTEMPTS=300`:
  - shard `026`: job `29493194`
  - shards `027`-`047`: jobs `29493305`, `29493306`, `29493307`,
    `29493308`, `29493309`, `29493310`, `29493311`, `29493312`,
    `29493313`, `29493314`, `29493315`, `29493316`, `29493317`,
    `29493318`, `29493319`, `29493320`, `29493321`, `29493322`,
    `29493323`, `29493324`, and `29493326`
- fresh inspection of new shard event logs confirms `code_commit=7e754bfc7`
  and timeout metadata are present. Early new rejects are planner or
  post-settle-filter rejects, not commit-mismatch rejects.
- important operational note: do not mutate a shared remote worktree while
  active jobs from an older `CODE_COMMIT` are still calling scripts from it.
  For future source or replay fixes while jobs are active, deploy a separate
  remote worktree path and submit only new jobs against that path.

## 2026-06-25T19:20:00Z Source Autosubmit Controller

- the centered-y source batch had `229` accepted rows with `22` active
  `yam_centery500` jobs and `24` total A100 jobs for the user. No new
  commit-matched shard was stale.
- started a remote source autosubmit controller on A100 to append ordinary
  shards into the same batch without mutating the active worktree:
  - PID: `2047837`
  - script:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_single_object_center_y_dynamic_500_20260625T165831Z/source_autosubmit_controller.sh`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/yam_demos/yam_single_object_center_y_dynamic_500_20260625T165831Z/source_autosubmit_controller.log`
  - next shard: `048`
  - caps: `YAM_ACTIVE_CAP=22`, `TOTAL_ACTIVE_CAP=24`
  - target: stop submitting once accepted demos reach `500`
  - buffer: maintain projected capacity up to `530` accepted demos to tolerate
    incomplete shards without large overrun.
- controller submission settings match the commit-matched wave:
  `CODE_COMMIT=7e754bfc7dbea882ee4ffbb08f80f575105e1fcd`,
  `SHARD_TARGET=10`, `MAX_ATTEMPTS=300`, `START_SEED=79000000`,
  `YAM_POLICY_OBJECT_Y_RANGE=-0.16 -0.04`,
  `SCRIPTED_BIN_DROP_Y_OFFSET=-0.08`, and gripper gains `2.0/0.25/5.0`.

## 2026-06-25T19:38:00Z YAM RGB Policy Eval Path

- while A100 source collection continued, added a dedicated closed-loop YAM
  RGB Diffusion Policy evaluator:
  `dextrah_lab/rl_games/eval_yam_pickplace_rgb_dp_policy.py`.
- evaluator policy inputs are exactly `scene_rgb`, `wrist_rgb`, and 24D
  `robot_state`; it records task/object/bin metrics for evaluation but never
  passes privileged object/bin state or phase/progress features to the policy.
- evaluator creates the same link-6 D405 wrist camera sensor used by replay and
  uses the patched scene camera default with optional small jitter. It also
  forces the requested YAM default pose `(0, 1, 1, -1.5, 0, 0)` and gripper
  qpos `0.0` during reset config.
- added L40-oriented wrapper:
  `cluster/sbatch_eval_yam_pickplace_rgb_dp_policy_1gpu.sh`, defaulting to
  `RENDERING_MODE=quality`, 256x256 scene+wrist RGB, centered object/bin
  randomization, and gripper gains `2.0/0.25/5.0`.
- validation passed:
  `python3 -m py_compile dextrah_lab/rl_games/eval_yam_pickplace_rgb_dp_policy.py`
  and `bash -n cluster/sbatch_eval_yam_pickplace_rgb_dp_policy_1gpu.sh`.
- deployed commit `9287922cce131632b4f960d75d261d43ee5cd1d3` to separate
  downstream worktrees without touching the active A100 source-generation
  checkout:
  - A100 conversion/training worktree:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-a100-dp-9287922c`
  - L40 quality replay/eval worktree:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-l40-dp-9287922c`

## 2026-06-25T19:50:00Z YAM RGB Dataset Conversion Wrapper

- added `cluster/sbatch_make_yam_rgb_policy_shards_1gpu.sh` to convert L40
  RGB replay `accepted_rgb_replays.jsonl` files into manifest-backed sharded
  Diffusion Policy datasets with `scene_rgb`, `wrist_rgb`, `robot_state`, and
  `action`.
- wrapper runs the existing
  `dextrah_lab/offline_dp_bc/make_yam_rgb_policy_shards.py` converter inside
  the Isaac Lab container, validates the manifest has both RGB keys and a
  positive step count, and supports `CODE_COMMIT` guarding.
- validation passed: `bash -n cluster/sbatch_make_yam_rgb_policy_shards_1gpu.sh`.

## 2026-06-26T02:31:00Z Closed-Loop Eval Relabel Finding

- L40 quality-render eval smoke `1044919`
  (`yam_pickplace_rgb_dp_500_mmap_20k_eval_smoke3_20260626T022031Z`) completed
  2 episodes and wrote video/metrics locally under
  `cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_20k_eval_smoke3_20260626T022031Z`.
  It reported `episode_success_rate=0.0`, max lift below `1e-6`, and gripper
  actions remained positive.
- The first smoke was only 240 steps; source demo phase inspection showed close
  begins around step 243 and lift around step 303, so a longer quality eval was
  launched.
- L40 long smoke `1044968`
  (`yam_pickplace_rgb_dp_500_mmap_20k_eval_longsmoke_20260626T022701Z`) ran to
  truncation at step 719. It still had `episode_success_rate=0.0`, max lift
  `6.4e-7`, and policy gripper action range `[0.276, 1.0]`.
- Root cause hypothesis: the dataset converter labeled the gripper action from
  measured `gripper_width`; the replayed demos have contact-limited widths that
  map to positive/open actions even during close/lift phases. The converter now
  uses phase-derived open/close labels when `phase` is present and falls back to
  width only for older datasets without phase.
- Validation before commit: `python3 -m py_compile
  dextrah_lab/offline_dp_bc/make_yam_rgb_policy_shards.py`.

## 2026-06-26T02:56:00Z Phase-Gripper Rebuild Audit

- One-row A100 shard smoke `29512372`
  (`yam_rgb_policy_shards_phase_smoke_20260626T0234Z`) confirmed the relabel
  path writes `gripper_label_source=phase` and produces `+1/-1/+1` transitions
  around close and drop.
- Full 500-shard rebuild `29512393`
  (`yam_rgb_policy_shards_500_mmap_phasegrip_20260626T0242Z`) completed with
  500 shards and 414,460 steps, but aggregate action audit found extra reopen
  transitions in some episodes during bin transport.
- Source inspection showed scripted place phases are labeled
  `target/move_to_above_bin_scripted`; the converter close-phase allowlist only
  included `target/move_to_above_bin`. Added the scripted alias before training
  so labels keep the gripper closed through object transport to the bin.

## 2026-06-27T03:49:14Z Long-Run Restart Robustness

- Inherited long YAM RGB Diffusion Policy training run
  `yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z`.
  The latest durable checkpoint is epoch 5 at `global_step=458395`; the live
  A100 job `29537791` on `batch-block7-03023` had only advanced to about
  `global_step=460294` after roughly 20 minutes and `nvidia-smi` showed `0%`
  GPU utilization, so the job is not likely to reach the next epoch checkpoint
  before the short A100 wall time.
- Eval/train audit remains clean: policy observations are `scene_rgb`,
  `wrist_rgb`, and 24D `robot_state`; no phase/progress or privileged object
  state is used. Periodic L40 eval monitor `3139751` has already run long
  horizon evals at steps 109218, 240143, 327219, and 416608, with 2400-step
  episodes and both camera streams.
- Patched `cluster/submit_yam_rgb_dp_long_train_a100.sh` so progress tracking
  uses the latest appended `logs.json.txt` record instead of the maximum
  historical step. This avoids stale unsaved timeout rows causing a restarted
  checkpoint resume to look like non-progress.
- Added `SBATCH_EXCLUDE` support to the long-train submitter and recorded it in
  `long_train_submitter_config.json`. Next step is to deploy this patch,
  stop the old submitter/job, and relaunch excluding `batch-block7-03023`.

## 2026-06-27T03:58:30Z Long-Run Relaunch On Healthy A100 Node

- Local commit `68157edd` (`Harden YAM RGB long train submitter`) was pushed.
  The A100 checkout cannot fetch `origin` over SSH, so the exact submitter-file
  diff from that commit was applied to the existing detached remote worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-rgb-diffusion-long-ef0d3b59`
  and validated with `bash -n`.
- Stopped the inherited submitter `3167244` and cancelled slow job `29537791`
  on `batch-block7-03023`. The final appended training row before cancellation
  was `global_step=460542`, but the durable checkpoint remains epoch 5
  `latest.ckpt` at `global_step=458395`.
- Started replacement submitter PID `2013382`, log
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z/submitter/a100_submitter_restart_20260627T035330Z.log`.
  It submitted resumed A100 job `29537920` with
  `SBATCH_EXCLUDE=batch-block7-03023`; the job landed on
  `batch-block5-02014`.
- The restart correctly appended fresh rows from the checkpoint
  (`global_step=458395`, `458396`) after the older unsaved `460542` row,
  confirming the latest-row progress accounting is required for this run.
- First healthy-node throughput check at about 4.5 minutes showed tail steps
  `459350..459379`, about `7.38` steps/sec over the measured JSON window, and
  `nvidia-smi` reported nonzero GPU utilization. Next expected durable
  checkpoint is the epoch-5 completion around `global_step=502k`; the L40
  periodic eval monitor should then trigger the `500k` checkpoint eval.

## 2026-06-27T05:57:00Z 500k Periodic Eval Evidence

- A100 job `29537920` reached the next durable checkpoint:
  `epoch=0005-test_mean_score=0.000.ckpt` and `latest.ckpt` were saved at
  `2026-06-27T05:25:53Z` with validation loss `0.008938116021454334`.
  Training continued into epoch 6; at the post-eval check it was at
  `global_step=517974`, job elapsed `02:08:50`, with submitter PID `2013382`
  still alive.
- The L40 periodic eval monitor behaved correctly. It logged
  `threshold_seen threshold=500000 step=501664`, waited for the old checkpoint
  mtime to become fresh, then submitted eval job `1052572` from snapshot
  `step_0504041.ckpt`.
- Eval job `1052572` completed successfully on `pool0-00013` in `00:25:09`.
  Local fetched artifacts are under
  `cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/`.
- Metrics: `episode_success_rate=0.0`, `episodes_completed=3`,
  `steps_completed=7200`, `num_steps_requested=2400`, `reward_mean=3.012600833872954`.
  All episodes ran the full long horizon with no `done` and no lift
  (`max_lift_height` around `6.5e-7`, `6.4e-7`, and `5.2e-8`).
- Eval/train input audit from metrics remains clean:
  `obs_schema={scene_rgb:[3,256,256], wrist_rgb:[3,256,256], robot_state:24}`,
  `phase_progress_in_policy=false`, and
  `privileged_object_state_in_policy=false`.
- Visual inspection:
  - rollout:
    `cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/videos/yam-pickplace-rgb-dp-eval-step-0.mp4`
    is 1280x720, 2400 frames, 40 seconds.
  - observation debug images are 512x284 scene+wrist pairs; the scene camera
    sees the bin/object/table with essentially no background, and the wrist
    camera stream is live.
  - observation grid:
    `cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/obs_ep000_grid.png`.
- Behavioral finding: the 500k checkpoint is still not closed-loop useful. The
  policy sometimes issues hard close commands (`gripper=-1`) but then settles
  into tiny pose deltas without reaching or lifting the object. This looks like
  continued undertraining/closed-loop weakness rather than a camera/schema or
  eval-horizon bug.

## 2026-06-27T06:10:08Z 504k Offline Coherence Diagnostic

- Launched a short A100 offline coherence diagnostic for the exact checkpoint
  used by the 500k periodic eval:
  job `29539184`, snapshot
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z/periodic_eval_snapshots/step_0504041.ckpt`,
  manifest
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/yam_pickplace_rgb_policy/yam_rgb_policy_shards_500_mmap_phasegrip2_trimstart_20260626T042729Z/manifest.json`.
- The diagnostic completed successfully on `batch-block1-2092` in `00:01:03`
  and scored `112` stored dataset observations with the official DP checkpoint
  loader and the same policy code path used by eval. Local artifacts were
  fetched to
  `/home/lzha/code/cluster_results/a1003/yam_rgb_dp_offline_diag_step0504041_20260627T060638Z/`;
  viewer URL:
  `http://localhost:8765/view?path=cluster_results/a1003/yam_rgb_dp_offline_diag_step0504041_20260627T060638Z/yam_rgb_offline_coherence_report.md`.
- Summary: pose scale is aligned (`pred_first_pose_l2_mean=0.0308`,
  `label_first_pose_l2_mean=0.0294`, `pose_l2_ratio_mean=1.046`), and gripper
  sign match is `0.964`. By regime, close rows have predicted mean gripper
  `-0.928` against label `-1.0`; open rows have predicted mean gripper
  `0.927` against label `1.0`.
- This makes a remaining train/eval plumbing bug unlikely for the 504k
  checkpoint. The failed closed-loop behavior remains best explained by
  undertraining/closed-loop distribution drift rather than image layout,
  normalizer, action scale, checkpoint source, or gripper-sign mismatch.
- Live state after the diagnostic: A100 long-train submitter PID `2013382` is
  still active, job `29537920` is running on `batch-block5-02014`, and the
  trainer is in epoch 6 at about `global_step=521041`. The L40 periodic eval
  monitor PID `3139751` remains alive and is correctly waiting for the next
  fresh checkpoint after the `600000` threshold.

## 2026-06-27T07:12:56Z Epoch 6 Durable Checkpoint

- A100 job `29537920` on `batch-block5-02014` reached the next durable save.
  `epoch=0006-test_mean_score=0.000.ckpt` and `latest.ckpt` were written at
  `2026-06-27T07:11:34Z` with size `1606332835` bytes.
- Validation row: `global_step=546074`, `epoch=6`,
  `val_loss=0.010338570922613144`. This is worse than the 502k validation
  loss (`0.008938116021454334`) but finite; training continued into epoch 7
  and was at about `global_step=546718` at the verification check.
- The L40 periodic eval monitor PID `3139751` stayed idle, as intended, because
  this checkpoint is below the next `600000` eval threshold. The submitted eval
  ledger still ends at snapshot `step_0504041.ckpt` / l401 job `1052572`.
- Next step: keep the A100 submitter PID `2013382` under supervision through
  the current allocation's remaining wall time. It is unlikely to finish epoch
  7 before timeout, so the expected healthy behavior is a timeout/relaunch from
  the fresh `546074` checkpoint.

## 2026-06-27T07:47:35Z A100 Timeout And Resume From 546k

- A100 job `29537920` timed out after writing unsaved epoch-7 rows up to
  `global_step=559289`. The submitter stayed alive and appended:
  `job_done job_id=29537920 state=TIMEOUT previous_step=460542
  new_step=559289`.
- The submitter launched replacement job `29541424` at
  `2026-06-27T07:45:52Z`; it is running on `batch-block5-01628`.
- Verified the replacement resumed from the durable epoch-6 checkpoint, not the
  unsaved timeout tail: the newest training rows restarted at
  `global_step=546108..546127`, with latest validation still
  `global_step=546074`, `val_loss=0.010338570922613144`, and checkpoint mtime
  `2026-06-27T07:11:34Z`.
- This confirms the patched submitter latest-row accounting is doing the right
  thing for timeout/relaunch cycles. Continue monitoring job `29541424` toward
  the next durable checkpoint and the eventual fresh post-`600000` eval.

## 2026-06-27T09:39:00Z Latest Eval Video Open And 590k Checkpoint

- Responded to the latest artifact request by opening the newest completed L40
  eval artifacts through `viz-open`. No eval newer than the `step_0504041`
  snapshot exists yet. Viewer URLs:
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/videos/yam-pickplace-rgb-dp-eval-step-0.mp4`,
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/videos/yam-pickplace-rgb-dp-eval-step-0-scene-wrist-obs.mp4`,
  and
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0504041/obs_ep000_grid.png`.
- Rechecked the artifacts: the rollout video is `1280x720`, `60 FPS`,
  `2400` frames, and `40.0s`; the generated scene/wrist observation clip is
  `512x284`, `4 FPS`, `36` frames, and `9.0s`. Metrics remain the expected
  504k failure case: `episode_success_rate=0.0` over 3 long-horizon episodes,
  with no object lift and no premature truncation.
- A100 job `29541424` wrote the next durable checkpoint while monitoring.
  `latest.ckpt` and `epoch=0006-test_mean_score=0.000.ckpt` were refreshed at
  `2026-06-27T09:34:24Z` / `2026-06-27T09:34:25Z` with size `1606332835`
  bytes. The validation row is `global_step=589913`, `epoch=6`,
  `val_loss=0.008642744272947311`; training continued into epoch 7 and was at
  about `global_step=590846` at the inspection check.
- The checkpoint is still below the next periodic eval threshold (`600000`).
  The L40 eval monitor PID `3139751` remains alive and the submitted-eval
  ledger still ends at `step_0504041.ckpt` / job `1052572`, so no below-
  threshold eval was launched. Continue monitoring for a fresh post-600k
  checkpoint and the next L40 eval videos.

## 2026-06-27T11:49:00Z 634k Periodic Eval Evidence

- The trainer crossed the 600k threshold at `global_step=600426`. The L40
  monitor correctly waited for a fresh checkpoint newer than that crossing.
  A100 job `29541424` then wrote `epoch=0007-test_mean_score=0.000.ckpt` and
  `latest.ckpt` at `2026-06-27T11:15:10Z` / `2026-06-27T11:15:11Z`.
  Validation row: `global_step=633753`, `epoch=7`,
  `val_loss=0.008767523802816868`.
- The L40 periodic monitor submitted eval job `1054027` from snapshot
  `step_0634735.ckpt` at `2026-06-27T11:17:29Z`; it ran on `pool0-00011` and
  completed successfully. Artifacts were fetched to
  `/home/lzha/code/cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0634735`.
- Opened latest visualization artifacts:
  rollout
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0634735/videos/yam-pickplace-rgb-dp-eval-step-0.mp4`,
  scene/wrist observation clip
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0634735/videos/yam-pickplace-rgb-dp-eval-step-0-scene-wrist-obs.mp4`,
  and observation grid
  `http://localhost:8765/view?path=cluster_results/l401/yam_pickplace_rgb_dp_500_mmap_phasegrip2_trimstart_long2m_horizonfix_20260626T080838Z_periodic_eval_step0634735/obs_ep000_grid.png`.
  The rollout is `1280x720`, `60 FPS`, `2400` frames, and `40.0s`; the
  generated observation clip is `512x284`, `4 FPS`, `36` frames, and `9.0s`.
- Metrics remain unsuccessful: `episode_success_rate=0.0`,
  `episodes_completed=3`, `steps_completed=7200`, `num_steps_requested=2400`,
  and no object lift (`max_lift_height` about `6.5e-7`, `6.4e-7`, and
  `5.2e-8`). Reward mean is `2.958997673889001`, worse than the 504k eval.
  The policy observation schema is unchanged and clean:
  `scene_rgb=[3,256,256]`, `wrist_rgb=[3,256,256]`, `robot_state=24`,
  `phase_progress_in_policy=false`, and
  `privileged_object_state_in_policy=false`.
- Visual inspection of the scene/wrist grid shows the camera setup remains
  appropriate: the table/object/bin fill the scene camera with essentially no
  background, and the wrist stream is live. The failure is behavioral: the
  object stays stationary and actions settle into small corrections; episode 0
  and 1 finish with open gripper widths around `0.186 m`, episode 2 closes to
  about `0.108 m`, but none lift.
- A100 job `29541424` timed out after unsaved rows up to `global_step=642113`.
  The submitter launched replacement job `29544942` at
  `2026-06-27T11:38:03Z` on `batch-block7-01718`; verified fresh training rows
  restarted from the durable `633753` checkpoint (`global_step=633802+`).
  Continue monitoring toward the 700k threshold.

## 2026-06-27T13:23:00Z 677k Checkpoint Before 700k Threshold

- A100 job `29544942` wrote the next durable checkpoint at
  `2026-06-27T13:19:56Z` / `2026-06-27T13:19:57Z`. The validation row is
  `global_step=677592`, `epoch=7`, `val_loss=0.009714050218462944`.
  Training continued into epoch 8 and was at about `global_step=677987` at
  the inspection check.
- This checkpoint is below the next periodic eval threshold (`700000`). The
  L40 monitor and submitted-eval ledger remained unchanged, ending at
  `step_0634735.ckpt` / job `1054027`, so it did not launch a below-threshold
  eval. Continue monitoring job `29544942` toward the 700k threshold and the
  next fresh post-threshold eval.
