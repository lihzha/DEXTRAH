# Worklog - franka-graspgenx-curobo-demo / franka-ggx-curobo-local-20260610T234641Z-86074

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- created: 2026-06-10T23:46:42Z

## 2026-06-10T23:46:42Z - Local workspace isolation

Goal:
- Continue Franka star GraspGenX/cuRobo demo without sharing the canonical checkout.

Change:
- Created agent-owned worktree and moved the kinematic playback planner diff here.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- changed_files: dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py

Command / Job:
- command: stopped local uv/Docker probes before isolating; no active demo process remains.
- job_id: n/a

Result:
- status: paused
- key evidence: source work will resume from this worktree; shared checkout retains only pre-existing dirty files.

Next:
- Run all future planner/render commands from the agent-owned worktree and namespaced output directories.

## 2026-06-10T23:53:40Z - Local dependency setup and planner fallback

Goal:
- Prepare isolated local planner execution for the Franka star GraspGenX/cuRobo demo.

Change:
- Added kinematic playback support to the DEXTRAH planner so local execution can export a GraspGenX/cuRobo trajectory without requiring Newton.
- The kinematic trajectory augments GraspGenX's JSON with an `object_poses.object` track attached to the Franka tool after close.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- implementation_commit: 1460efd71bb92ce05ec32705f6dd26a2a6cba16b
- changed_files: dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py

Command / Job:
- command: `UV_LINK_MODE=copy uv sync` in the agent-owned GraspGenX worktree
- command: `uv pip install --python <agent-graspgenx>/.venv/bin/python -e <agent-curobo> --no-deps`
- command: `uv pip install --python <agent-graspgenx>/.venv/bin/python 'cuda-core[cu12]<1.0' 'nvidia-cuda-runtime-cu12>=12' 'warp-lang>=0.10.0' numpy-quaternion importlib_resources`
- job_id: n/a
- run_dir: n/a

Result:
- status: passed
- key evidence: imports resolved from isolated GraspGenX and cuRobo worktrees; `torch.cuda.is_available()` returned true with 2 devices.
- validation: `python3 -m py_compile dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py dextrah_lab/scene_scripts/render_star_kitting_env.py`
- validation: `bash -n cluster/sbatch_plan_franka_star_graspgenx_curobo.sh cluster/sbatch_render_star_kitting_env.sh`
- validation: `git diff --check`

Next:
- Commit the DEXTRAH fallback and launch a bounded local planner smoke from the isolated worktree.

## 2026-06-11T00:00:55Z - Local planner smoke and render validation

Goal:
- Prove the GraspGenX + cuRobo Franka star demo runs locally from the isolated checkout and produces a visible DEXTRAH kitting artifact.

Hypothesis:
- GraspGenX can sample a viable Franka grasp for the DEXTRAH star mesh, cuRobo can export a collision-aware approach/grasp/lift trajectory, and the DEXTRAH render script can replay that trajectory with the star kinematically attached after close.

Change:
- No additional source change after commit 1460efd71bb92ce05ec32705f6dd26a2a6cba16b.
- Fixed the local Docker launch command by overriding the Isaac Lab image entrypoint with `/bin/bash`; the image's default `/isaac-sim/runheadless.sh` entrypoint had launched the default streaming app instead of the script.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- implementation_commit: 1460efd71bb92ce05ec32705f6dd26a2a6cba16b
- changed_files: worklogs/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074.md
- push/pull: n/a, local validation only

Command / Job:
- command: local planner smoke with `--playback_mode kinematic --num_grasps 80 --topk 40 --max_plan_attempts 40 --rank_grasps_by_confidence`
- job_id: n/a
- run_dir: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/planner/planner_smoke_20260610T235114Z
- logs: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/planner/planner_smoke_20260610T235114Z.log
- artifacts: trajectory.json, plan_summary.json, generated star/table meshes, resolved configs
- command: local Docker render smoke, first attempt `render_smoke_20260610T235307Z`
- result: failed/canceled intentionally; default image entrypoint launched `/isaac-sim/runheadless.sh` and never reached project logs or output_dir.
- command: local Docker render smoke with `--entrypoint /bin/bash`, run `render_smoke_entrypoint_20260610T235818Z`
- run_dir: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_smoke_entrypoint_20260610T235818Z
- logs: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/logs/render_smoke_entrypoint_20260610T235818Z.log
- artifacts: overview.mp4, frames/overview_*.png, scene_metadata.json, render_manifest.json, star_kitting_env.usda

Result:
- status: passed
- planner metrics: 40 top candidates, selected grasp index 19, selected confidence 0.8277818560600281, trajectory frames 508.
- plan segments: approach 82, grasp 42, lift 22.
- task segments: go_to_pre_grasp_pose 82, go_from_pre_grasp_to_grasp_pose 120, close_fingers 12, lift_object 240.
- trajectory evidence: `object_poses.object` z moved from 0.767 m to 0.8269999067 m; object pose mode is kinematic attached-to-tool after close.
- render evidence: 60 PNG frames at 640x360, encoded to 12 FPS / 5.0 s MP4.
- visual inspection: first frame shows Franka, star, and fixture; middle frame shows Franka approaching above the star; final frame shows gripper at the lifted star position.
- viewer: http://localhost:8765/view?path=local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_smoke_entrypoint_20260610T235818Z/overview.mp4

Analysis:
- The pipeline is validated as a local kinematic playback demo. It demonstrates GraspGenX grasp selection, cuRobo trajectory export, and DEXTRAH Franka/star replay in the kitting scene.
- This is not yet a dynamic contact grasp validation because local Newton playback was bypassed; the star is driven by the exported attachment track for robust local rendering.

Next:
- If dynamic contact validation is required, materialize the missing full Franka gripper assets and rerun with the Newton/dynamic playback path before merging into a shared checkout.

## 2026-06-11T00:07:30Z - Gripper timing playback fix

Goal:
- Fix the visualization issue where the Franka fingers appeared closed before the arm reached the star.

Hypothesis:
- The GraspGenX/cuRobo trajectory is correctly timed, but the Isaac articulation was lagging because the render path sent sparse joint targets through the controller with only one sim step per video frame.

Change:
- Added `--franka_trajectory_playback {target,state}` to `render_star_kitting_env.py`.
- `state` mode writes exact planned joint positions and zero joint velocities to the articulation for kinematic trajectory replay.
- Updated `cluster/sbatch_render_star_kitting_env.sh` so `FRANKA_MOTION=trajectory` defaults to `FRANKA_TRAJECTORY_PLAYBACK=state`.
- Recorded playback mode in render manifest and scene metadata.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: 1460efd71bb92ce05ec32705f6dd26a2a6cba16b
- implementation_commit: f8e1bf6d6d7078785b2f1bc30a4edd39718b94ee
- changed_files: dextrah_lab/scene_scripts/render_star_kitting_env.py, cluster/sbatch_render_star_kitting_env.sh, worklogs/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074.md

Command / Job:
- validation: `python3 -m py_compile dextrah_lab/scene_scripts/render_star_kitting_env.py dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py`
- validation: `bash -n cluster/sbatch_render_star_kitting_env.sh cluster/sbatch_plan_franka_star_graspgenx_curobo.sh`
- validation: `git diff --check`

Result:
- status: passed
- implementation_commit: f8e1bf6d6d7078785b2f1bc30a4edd39718b94ee
- corrected render: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z
- final video: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview.mp4
- zoomed video: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview_pickup_crop.mp4
- viewer: http://localhost:8765/view?path=local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview.mp4
- zoomed viewer: http://localhost:8765/view?path=local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview_pickup_crop.mp4
- ffprobe: 640x360, 72 frames, 12 FPS, 6.0 s.
- crop ffprobe: 960x720, 72 frames, 12 FPS, 6.0 s.
- metadata: `robot_motion.trajectory_playback=state`, `checks.franka_trajectory_state_playback=true`, final manifest `franka_trajectory_playback=state`.
- visual evidence: frame 20 shows open/approaching gripper at the star, frame 33 shows close at the star, and frame 71 shows the star lifted.
- key evidence: trajectory JSON keeps fingers open through approach and closes at the intended close segment; the original early-close visual was playback lag.

Next:
- Hand off the isolated branch/worktree for integration review. Dynamic contact validation remains future work because this local demo intentionally uses kinematic state playback.

## 2026-06-11T00:11:45Z - Final handoff

Goal:
- Preserve the final local demo evidence and hand off the isolated implementation branch without modifying the shared checkout.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- final_validated_commit: fc720f4f25fb6e390a7c66ae3406d5406ba7c4ab
- pushed_to: origin/codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074

Artifacts:
- planner: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/planner/planner_smoke_20260610T235114Z
- render: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z
- overview_video: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview.mp4
- zoomed_video: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview_pickup_crop.mp4
- overview_viewer: http://localhost:8765/view?path=local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview.mp4
- zoomed_viewer: http://localhost:8765/view?path=local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_state_playback_final_20260611T000518Z/overview_pickup_crop.mp4

Cleanup:
- active_demo_containers: none
- active_demo_gpu_processes: none
- worktree_status: clean before this final worklog entry
- unrelated_processes: existing non-DEXTRAH TPU command observed and left untouched

Next:
- Integration should happen from a separate integration worktree by reviewing or merging the pushed branch.

## 2026-06-11T01:52:30Z - Local dynamic PhysX validation after gripper asset fix

Goal:
- Verify the updated Franka gripper meshes resolve the GraspGenX dummy-gripper issue and continue toward a local dynamic Isaac Sim Franka star grasp demo.

Hypothesis:
- The restored `franka_panda` gripper meshes/TSDF should remove the GraspGenX dummy fallback. In Isaac Sim, raw PhysX contact may move the dynamic star, but the referenced Franka USD needs contact/proxy or grasp-assist support for a reliable thin-object lift.

Change:
- Verified GraspGenX `get_gripper_info("franka_panda")` loads real `vis_mesh.obj`, `coll_mesh.obj`, and `tsdf.npy`.
- Added `--franka_trajectory_object_mode physics` so the star can remain under live PhysX instead of replaying trajectory object poses.
- Added live `RigidObject` tracing for `star_motion_trajectory.json`.
- Added hidden articulation-child fingertip collision proxies and `--franka_contact_proxy_mode`, defaulting to `articulation`.
- Added optional `--franka_grasp_constraint_mode attach_on_close`, implemented as an explicit kinematic pose weld after the gripper closes near the dynamic star.
- Updated `cluster/sbatch_render_star_kitting_env.sh` to pass contact-proxy and grasp-assist knobs.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- implementation_commit: 7674e10
- changed_files: dextrah_lab/scene_scripts/render_star_kitting_env.py, cluster/sbatch_render_star_kitting_env.sh, worklogs/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074.md

Command / Job:
- planner rerun: `planner_assets_verify_20260611T005550Z`
- raw dynamic run: `render_dynamic_physics_live_star_articulation_proxy_gpu0_20260611T013615Z`
- fixed-joint attempts: `render_dynamic_physics_attach_constraint_gpu0_20260611T014147Z`, `render_dynamic_physics_pose_joint_gpu0_20260611T014447Z`
- assisted weld run: `render_dynamic_physics_weld_fix_gpu0_20260611T014920Z`
- logs: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/logs
- artifacts: each render run's `overview.mp4`, `contact_sheet.png`, `star_motion_trajectory.json`, `robot_motion_trajectory.json`, `scene_metadata.json`

Result:
- status: partial pass
- gripper assets: passed; GraspGenX loaded real Franka collision/visual meshes and TSDF with no dummy-gripper warnings.
- planner: passed; selected grasp index 16, confidence 0.8296340108, 742 trajectory frames.
- raw dynamic contact: partial; actual fingers closed to about 4-6 mm and live PhysX moved the star about 3.2 cm laterally, but it did not lift.
- USD fixed-joint grasp assist: failed; PhysX snapped or destabilized the star, so the fixed-joint path was removed.
- kinematic weld assist: passed as an assisted demo; attach fired at frame 22/substep 6, actual max finger opening 0.01196 m, star z moved from 0.763 m to 0.810 m, and lateral drift after attach stayed under about 6 mm.
- final assisted artifact: /home/lzha/code/local_results/franka_ggx_curobo_demo/franka-ggx-curobo-local-20260610T234641Z-86074/render/render_dynamic_physics_weld_fix_gpu0_20260611T014920Z/overview.mp4

Analysis:
- The user's gripper mesh fix resolves the hard GraspGenX asset constraint.
- The remaining hard dynamic-contact constraint is Isaac Sim contact fidelity for the referenced Franka USD and thin star: articulation-child proxies are enough to produce contact and close the fingers, but not enough for a clean frictional pinch/lift.
- The current demo is dynamic until grasp acquisition, then uses an explicit in-Isaac pose weld. It is suitable as a local pipeline visualization, not a proof of pure contact-only grasping.
- No Newton dependency is required; all validation here runs in Isaac Sim/PhysX.

Next:
- Run final syntax/wrapper validation, open the final artifact with `viz-open`, then commit the DEXTRAH worktree changes if clean.
