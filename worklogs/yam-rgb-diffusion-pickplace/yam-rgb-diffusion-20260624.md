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
