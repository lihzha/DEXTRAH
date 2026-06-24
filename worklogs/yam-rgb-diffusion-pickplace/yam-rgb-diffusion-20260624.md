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
