# YAM Two-Bin Demo Worklog

## 2026-06-22 16:30 PDT

- Goal: add a single-YAM two-bin primitive environment and produce a two-view demo video using GraspGen-X + cuRobo for pickup and scripted placement into the empty bin.
- Agent: `yam-two-bin-demo-20260622T233055Z-3635211`.
- Branch: `codex/yam-two-bin-demo-20260622T233055Z-3635211`.
- Base commit: `78b99de4d3e61b9b80981db09650a015707f6b32`.
- Worktree: `/home/lzha/code/worktrees/DEXTRAH/yam-two-bin-demo-20260622T233055Z-3635211`.
- Initial status: implementation approved; no jobs launched yet.
- Planned evidence: py_compile/bash syntax checks, local smoke where available, GraspGen-X/cuRobo planner result, Isaac replay logs/metrics, validation JSON, final side-by-side MP4 with default and top-down views, ffprobe output, representative frame inspection, and viz-open URL.

## 2026-06-22 16:54 PDT

- Added deterministic task `Dextrah-Single-YAM-Two-Bin-Primitive-Grasp` with one dynamic target rectangle, fixed primitive clutter, source/goal bins, and fixed source-bin layout.
- Added primitive manifest and simple raw OBJ meshes under `dextrah_lab/assets/primitives`.
- Extended stable-scene payloads with `bins` and primitive asset metadata.
- Updated YAM GraspGen-X/cuRobo planner collision setup to use captured goal/source bin geometry and pass the captured goal bin to scripted placement.
- Added `dextrah_lab/scene_scripts/compose_two_view_video.py` and `cluster/sbatch_yam_two_bin_demo_1gpu.sh`.
- Static validation passed:
  - `bash -n cluster/sbatch_yam_two_bin_demo_1gpu.sh cluster/sbatch_render_tabletop_clutter_settle_video_1gpu.sh`
  - `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile` on touched Python scripts.
- Next: local smoke render/planner if possible, otherwise sync/launch on l401 and inspect artifacts.

## 2026-06-22 16:59 PDT

- Local final artifacts completed under `artifacts/yam_two_bin_final_local`; both final camera replays were run with `--headless`.
- Stable scene: `settle/stable_scene.json`; default replay: `default_view/default_view.mp4`; top-down replay: `topdown_view/topdown_view.mp4`; composed video: `yam_two_bin_two_view.mp4`.
- GraspGen-X/cuRobo planning succeeded with forced scripted placement, and the replay trajectory includes `target/move_to_above_bin_scripted`, `target/open_fingers_to_drop`, and final hold phases.
- Dataset validation accepted `default_view/trajectory_dataset.npz` against stable-scene goal-bin geometry:
  - final target position `[-0.2426, 0.2780, 0.0260]`
  - goal bin center `[-0.3000, 0.2200]`, inner size `[0.36, 0.28]`
  - lift delta `0.1665`
- Final two-view video verified with `ffprobe`: 1280x512, 376 frames, 12 fps, 31.33 s.
- Representative frames extracted to `inspection_frames/`; final frame visually inspected and shows the target rectangle in the blue receiving bin while remaining clutter stays in the yellow source bin.
- Top-down replay was rerun with `--headless` after an Isaac startup was killed during initialization. The default replay was also rerun with `--headless` before final validation and composition.

## 2026-06-22 21:35 PDT

- New goal: build on the accepted two-bin demo with a closed-loop iterative bin-clear demo.
- Plan confirmed by user: replan with GraspGen-X + cuRobo for the next selected object after each physics replay updates all object poses; repeat until the source bin is clear; render final default/top-down two-view video with headless Isaac replays.
- Implementation started in the existing agent-owned worktree/branch because the new demo depends on the two-bin environment changes already present here.
- Added `dextrah_lab/scene_scripts/run_yam_iterative_bin_clear_demo.py`, which loops over current source-bin objects, writes a per-iteration planning scene, plans one pick/drop, replays it dynamically to get updated poses, validates the selected object, and carries all final object poses into the next iteration.
- Extended `dextrah_lab/scene_scripts/compose_two_view_video.py` so the final video can concatenate multiple per-iteration clips for both camera views.
- Next: static checks, then a one-pick driver smoke before attempting all objects.

## 2026-06-22 21:50 PDT

- One-pick iterative smoke completed under `artifacts/yam_two_bin_iterative_smoke`.
- First selected object was `clutter_04`. The smoke exposed two implementation issues and fixed them:
  - preserve venv Python symlinks instead of resolving them, so the GraspGen-X venv imports NumPy;
  - allow `render_tabletop_clutter_settle_video.py` to write a refreshed stable scene after restoring/settling an input stable scene, and apply stable-scene target/clutter manifests for settle refreshes as well as trajectory replays.
- Added opt-in `--scripted_target_transport` to the replay script for the iterative demo. GraspGen-X/cuRobo still plans the YAM grasp/lift/place path, while the selected target is carried with the gripper during lift/place phases and released over the goal bin.
- Smoke status was `partial` as expected with `--max_picks 1 --allow_partial`; selected object lift delta was about `0.1004`, and its final pose was inside the goal bin.
- Next: full run with all source-bin objects and per-pick goal-bin y offsets to avoid dropping every object at the same point.

## 2026-06-22 22:23 PDT

- Full iterative bin-clear run completed under `artifacts/yam_two_bin_iterative_final` with status `accepted`.
- Final video: `artifacts/yam_two_bin_iterative_final/yam_two_bin_iterative_two_view.mp4`.
- Final validation checks all passed:
  - `all_objects_picked_once: true`
  - `all_final_inside_goal_bin: true`
  - `source_bin_clear: true`
  - `all_iteration_lifts_valid: true`
- Pick order and lift deltas:
  - `clutter_04`: `0.1494`
  - `clutter_02`: `0.1532`
  - `clutter_00`: `0.1572`
  - `clutter_01`: `0.1520`
  - `clutter_03`: `0.1465`
  - `target`: `0.1572`
- Fixed a full-run rejection found on iteration 2: the target was lifted but released too close to the goal-bin x edge. The planner now writes scripted placement metadata into `trajectory.json`, and the replay's opt-in scripted target transport uses that intended object-drop pose through the bin-drop/opening phase before release.
- Video evidence:
  - `ffprobe`: 1024x416, 2256 frames, 12 fps, 188.0 s.
  - Inspection frames extracted to `artifacts/yam_two_bin_iterative_final/inspection_frames`.
  - Frame inspection confirmed initial source-bin clutter, mid-run object transfer, and final empty source bin with all objects in the goal bin.
- Process cleanup check found no active demo Isaac/planner/render jobs after completion.

## 2026-06-22 22:34 PDT

- User inspection found the generated iterative artifact is physically invalid: the gripper does not visibly contact the selected object, but the object moves to the destination bin.
- Diagnosis: the iterative run used `--scripted_target_transport`, which kinematically carries the selected object with the TCP during lift/place phases. Pose validation accepted the final state, but this does not prove real gripper-object contact.
- Marked `artifacts/yam_two_bin_iterative_final/yam_two_bin_iterative_two_view.mp4` and its validation summary as invalid physical evidence.
- Immediate correction path: disable scripted target transport for real demos, add contact/near-grasp validation, run a no-transport one-pick smoke, debug the physical grasp/replay, and only then rerun the iterative bin-clear video.

## 2026-06-22 23:03 PDT

- Updated `validate_yam_pick_place_dataset.py` so scripted target transport is rejected by default and each dataset reports a contact proxy from TCP/object distance, gripper closure, and target lift while the gripper is closed.
- Changed `run_yam_iterative_bin_clear_demo.py` so `--scripted_target_transport` is disabled by default; future physical demos must opt into that shortcut explicitly.
- Static compile passed for the validator, iterative driver, and render script.
- Revalidated `artifacts/yam_two_bin_iterative_final/iter_02_clutter_00/default_view/trajectory_dataset.npz`; it is now rejected with failed checks `scripted_target_transport_disabled` and `contact_proxy`.

## 2026-06-22 23:15 PDT

- Resized the two-bin primitive objects and regenerated the settled two-bin scene under `artifacts/yam_two_bin_physical_assets/settle`.
- No-transport smoke with the prior YAM tool frame failed physically: the selected target root never lifted, and the closest TCP/object distance was about `0.139 m`.
- Patched the YAM GraspGen-X/cuRobo frame handoff: `grasp_to_tool_transform.translation` is now `[0, 0, 0.04]`, aligning the GraspGen-X sweep frame with the DEXTRAH `link_6` fingertip collision region.
- Added a fallback geometry-cost guard so outside-aperture YAM grasps cannot be silently accepted as physical candidates.
- Reran one-pick no-transport smoke in `artifacts/yam_two_bin_iterative_contact_smoke_offset`.
  - The selected `clutter_04` object visibly contacts the gripper, is carried over the goal bin, and drops into the goal bin.
  - Revalidated `iter_00_clutter_04/default_view/trajectory_dataset.npz` as accepted after updating the contact proxy to use commanded finger closure plus target lift during the closed-carry window.
  - Physical metrics: target lift delta `0.1476 m`, final pose `[-0.2923, 0.2920, 0.0470]`, scripted target transport disabled, contact proxy passed.
- Next: rerun the full iterative bin-clear demo without scripted target transport and inspect both views before accepting a final artifact.

## 2026-06-22 23:15 PDT

- Continued correction after a v2 two-pick physical smoke failed on iteration 1 during GraspGen-X/cuRobo planning for the updated `target` pose.
- Evidence from `artifacts/yam_two_bin_iterative_physical_v2_two_pick_smoke/iter_01_target/plan/pick_drop/plan_summary.json`: strict YAM aperture/lift/height filtering kept exactly one candidate; cuRobo reported `Goalset planning returned None`, so no physical replay/video was generated for the second pick.
- Patch: keep strict contact-oriented YAM grasps first, but when fewer than `--yam_grasp_filter_min_keep` survive and `--yam_allow_lift_filter_fallback` is enabled, add ranked inside-aperture backups and geometry-bounded backups. Scripted target transport remains disabled and rejected by validation.
- Static check: `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile dextrah_lab/scene_scripts/plan_yam_graspgenx_curobo.py` passed.
- Next run: relaunch the same two-pick smoke from `artifacts/yam_two_bin_physical_assets_v2/settle/stable_scene.json`; success requires iteration 1 to plan, replay without scripted target transport, pass contact/lift validation, and produce inspectable videos/frames.

## 2026-06-22 23:20 PDT

- Two-pick relaunch `artifacts/yam_two_bin_iterative_physical_v2_two_pick_smoke2` still failed on iteration 1 for `target`; widened candidate retention worked (`kept_count=4`), but all candidates were unreachable. A direct planner retry with `--yam_grasp_filter_min_keep 8` also failed, with cuRobo reporting start/end collision on the occluded target pose.
- Diagnosis: the target rectangle is partly under or next to `clutter_01`, so it should not be chosen before the exposed upper objects are removed.
- Patched the iterative driver to rank exposed/high-z objects before lower objects, retry another object when planning fails for a candidate, pass `--yam_grasp_filter_min_keep`, and avoid promoting settle-refresh poses from failed candidate plans into the authoritative object state.
- Static check: `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile dextrah_lab/scene_scripts/run_yam_iterative_bin_clear_demo.py` passed.
- Selector check on the v2 stable scene now picks `clutter_04` first again.

## 2026-06-22 23:42 PDT

- User clarified that failed object attempts are acceptable and the original tall-bin environment is preferred.
- Stopped the superseded shallow-tray smoke and restored the two-bin environment config to the original tall-bin layout/poses.
- Patched `run_yam_iterative_bin_clear_demo.py` so planning failures and validation failures are non-fatal when `--allow_partial` is set. Failed object IDs are recorded and excluded from future attempts; successful and failed replay attempts with videos are still included in the composed two-view video.
- Static check passed:
  - `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile dextrah_lab/scene_scripts/run_yam_iterative_bin_clear_demo.py dextrah_lab/tasks/dextrah_single_yam_multi_object_grasp/single_yam_multi_object_grasp_env_cfg.py`
- Next run: tolerant full iterative run from original v2 stable scene, continuing past individual object failures.

## 2026-06-22 23:47 PDT

- Tolerant original-environment run completed under `artifacts/yam_two_bin_iterative_original_env_tolerant_final`.
- Final two-view video: `artifacts/yam_two_bin_iterative_original_env_tolerant_final/yam_two_bin_iterative_two_view.mp4`.
- Viewer URL: `http://localhost:8765/view?path=worktrees/DEXTRAH/yam-two-bin-demo-20260622T233055Z-3635211/artifacts/yam_two_bin_iterative_original_env_tolerant_final/yam_two_bin_iterative_two_view.mp4`.
- Final status is intentionally `partial` under the updated acceptance rule:
  - accepted pick: `clutter_04`
  - failed/skipped objects: `clutter_00`, `clutter_01`, `clutter_02`, `clutter_03`, `target`
- Video evidence:
  - `ffprobe`: 1024x416, 752 frames, 12 fps, 62.666667 s.
  - Inspection frames extracted to `artifacts/yam_two_bin_iterative_original_env_tolerant_final/inspection_frames`.
  - Frame inspection confirmed the original tall two-bin setup, side-by-side default/top-down views, one object placed in the goal bin, and remaining failed/skipped objects left in the source bin.
- Process cleanup check found no active demo Isaac/planner/render jobs after completion.

## 2026-06-22 23:54 PDT

- User requested another tolerant iterative run with the smaller original object sizes from the first one-object pick-and-place demo.
- Recovered original sizes from `artifacts/yam_two_bin_final_local/settle/stable_scene.json`:
  - target rectangle: `0.060 x 0.038 x 0.028`
  - large sphere radius: `0.030`
  - low rectangle: `0.052 x 0.032 x 0.032`
  - small sphere radius: `0.024`
  - tall rectangle: `0.040 x 0.036 x 0.036`
- Added separate original-size raw meshes and manifest under `dextrah_lab/assets/primitives`, leaving the enlarged manifest used for the previous good artifact unchanged.
- Derived the launch stable scene at `artifacts/yam_two_bin_original_size_assets/settle/stable_scene.json` from the first demo's stable scene, preserving its object layout and redirecting every `raw_object_path` to the original-size mesh files.
- Launch plan:
  - run name/output: `artifacts/yam_two_bin_iterative_original_size_tolerant_final`
  - local cwd: `/home/lzha/code/worktrees/DEXTRAH/yam-two-bin-demo-20260622T233055Z-3635211`
  - HEAD: `78b99de4d3e61b9b80981db09650a015707f6b32`
  - local GPU: `CUDA_VISIBLE_DEVICES=0`, `NVIDIA_VISIBLE_DEVICES=0`
  - Isaac rendering: headless only through `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python`
  - GraspGen-X planner: `/home/lzha/code/worktrees/graspgenx-yam-ggx-curobo/.venv/bin/python`
  - success criteria: produce a two-view MP4, inspect sampled frames, record accepted/failed object IDs, and leave no active render/planner jobs.

## 2026-06-23 00:02 PDT

- First original-size tolerant pass (`artifacts/yam_two_bin_iterative_original_size_tolerant_final`) completed with status `partial` but produced no composed video: all six candidates failed in cuRobo with `Goalset planning returned None`.
- Diagnosis: the original-size one-object artifact was authored before the YAM GraspGen-X-to-cuRobo tool-frame handoff was shifted by `+0.04 m` for the enlarged physical-contact variant. With the small objects sitting low in the tall bin, that shifted frame made the goalsets unreachable.
- Patched `plan_yam_graspgenx_curobo.py` to expose `--yam_grasp_to_tool_z` while preserving the enlarged-object default of `0.04`.
- Patched `run_yam_iterative_bin_clear_demo.py` to forward `--planner_yam_grasp_to_tool_z` to the planner.
- Static check passed:
  - `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile dextrah_lab/scene_scripts/plan_yam_graspgenx_curobo.py dextrah_lab/scene_scripts/run_yam_iterative_bin_clear_demo.py`
- Planner smoke with `--yam_grasp_to_tool_z 0.0` on the original-size target succeeded and wrote `artifacts/yam_two_bin_original_size_plan_offset0_smoke/pick_drop/trajectory.json` with 1321 frames.
- Relaunch plan:
  - output: `artifacts/yam_two_bin_iterative_original_size_offset0_tolerant_final`
  - same original-size stable scene
  - scripted target transport remains disabled
  - planner uses `--planner_yam_grasp_to_tool_z 0.0`, `--num_grasps 96`, `--max_plan_attempts 48`, `--planner_clutter_margin 0.006`, `--yam_grasp_filter_min_keep 4`, and no lift-filter fallback to match the original small-object settings more closely.

## 2026-06-23 00:18 PDT

- Original-size tolerant run with zero YAM grasp-to-tool offset completed under `artifacts/yam_two_bin_iterative_original_size_offset0_tolerant_final`.
- Final two-view video: `artifacts/yam_two_bin_iterative_original_size_offset0_tolerant_final/yam_two_bin_iterative_two_view.mp4`.
- Viewer URL: `http://localhost:8765/view?path=worktrees/DEXTRAH/yam-two-bin-demo-20260622T233055Z-3635211/artifacts/yam_two_bin_iterative_original_size_offset0_tolerant_final/yam_two_bin_iterative_two_view.mp4`.
- Final status is intentionally `partial` under the tolerant acceptance rule:
  - accepted picks: `clutter_02`, `clutter_00`, `clutter_03`, `target`
  - failed/skipped objects left in source bin: `clutter_01`, `clutter_04`
- Lift validation for accepted objects:
  - `clutter_02`: `0.1613 m`
  - `clutter_00`: `0.1756 m`
  - `clutter_03`: `0.1822 m`
  - `target`: `0.1846 m`
- Video evidence:
  - `ffprobe`: 1024x416, 2256 frames, 12 fps, 188.0 s.
  - Inspection frames extracted to `artifacts/yam_two_bin_iterative_original_size_offset0_tolerant_final/inspection_frames`.
  - Frame inspection confirmed the original small object sizes, side-by-side default/top-down views, four objects in the goal bin by the final frame, and two failed objects remaining in the source bin.
- Process cleanup check found no active demo Isaac/planner/render jobs after completion.

## 2026-06-23 00:34 PDT

- User requested a more continuous iterative demo: no visible hard robot reset between picks, and avoid environment re-settling that can slightly shift object poses.
- Patch in progress in `run_yam_iterative_bin_clear_demo.py`:
  - added `--continuous_episode`, which disables per-iteration settle refresh and preserves object poses directly from replay datasets;
  - added `--append_return_home_between_picks`, `--return_home_frames`, and `--return_home_hold_frames`;
  - each rendered pick trajectory can now append a scripted minimum-jerk joint-space return to the stable-scene home pose before the next pick.
- Static check passed:
  - `/home/lzha/code/.venvs/dextrah-isaaclab/bin/python -m py_compile dextrah_lab/scene_scripts/run_yam_iterative_bin_clear_demo.py`
- Smoke plan:
  - output: `artifacts/yam_two_bin_iterative_original_size_continuous_home_smoke`
  - max picks: 2
  - same original-size stable scene and zero YAM grasp-to-tool offset as the previous good small-object run
  - render remains headless only
  - success criteria: composed two-view MP4 exists, no settle-refresh artifacts are generated, return-home summary is recorded, continuity diagnostics show the next planning start matches previous final joint state, and sampled frames show the robot returning home instead of snapping.

## 2026-06-23 00:49 PDT

- Two-pick continuous-home smoke completed under `artifacts/yam_two_bin_iterative_original_size_continuous_home_smoke`.
- Result status is `partial` with both attempted picks rejected (`clutter_04`, `clutter_02`), which is acceptable for the tolerant failure policy but worse than the previous settle-refresh version.
- Continuity evidence:
  - no `settle_refresh` directories were generated;
  - both rendered trajectories used `trajectory_with_return_home.json`;
  - render logs captured `return_home_scripted` and `hold_home_after_return` phases;
  - iteration 1 planning start matched iteration 0 replay-final joint state exactly (`max_abs=0.0`);
  - final-to-home joint errors were small: `2.7e-5` and `1.7e-5` max abs.
- Video evidence:
  - `ffprobe`: 1024x416, 794 frames, 12 fps, 66.166667 s.
  - sampled frames in `artifacts/yam_two_bin_iterative_original_size_continuous_home_smoke/inspection_frames` showed valid default/top-down views and visible return-home behavior.
- Full run launch plan:
  - output: `artifacts/yam_two_bin_iterative_original_size_continuous_home_final`
  - same continuous flags as smoke, no `--max_picks`
  - expected final status may remain `partial`; the primary acceptance criterion is continuous return-home behavior plus no settle-refresh pose nudging.

## 2026-06-23 01:03 PDT

- Full continuous-home run completed under `artifacts/yam_two_bin_iterative_original_size_continuous_home_final`.
- Final two-view video: `artifacts/yam_two_bin_iterative_original_size_continuous_home_final/yam_two_bin_iterative_two_view.mp4`.
- Viewer URL: `http://localhost:8765/view?path=worktrees/DEXTRAH/yam-two-bin-demo-20260622T233055Z-3635211/artifacts/yam_two_bin_iterative_original_size_continuous_home_final/yam_two_bin_iterative_two_view.mp4`.
- Final status is `partial` under `--allow_partial`:
  - accepted picks: `clutter_00`, `clutter_03`
  - failed objects left in source bin: `clutter_01`, `clutter_02`, `clutter_04`, `target`
- Validation summary:
  - `clutter_00` lift delta: `0.1561 m`
  - `clutter_03` lift delta: `0.1857 m`
  - all failed attempts were retained and the run continued to the next object.
- Continuity evidence:
  - no `settle_refresh` directories were generated;
  - all six iterations used `trajectory_with_return_home.json`;
  - all six iterations recorded `return_home.enabled=true`;
  - iteration-to-iteration planning starts matched the previous replay final joint state exactly after the first iteration (`max_abs=0.0`);
  - final-to-home joint max errors remained small: `1.6e-5` to `3.3e-5`.
- Video evidence:
  - `ffprobe`: 1024x416, 2390 frames, 12 fps, 199.166667 s.
  - inspection frames extracted to `artifacts/yam_two_bin_iterative_original_size_continuous_home_final/inspection_frames`.
  - sampled frames showed valid side-by-side default/top-down panes, two objects in the goal bin by the final frame, and the remaining failed objects still in the source bin.
- Process cleanup check found no active demo Isaac/planner/render jobs after completion.
