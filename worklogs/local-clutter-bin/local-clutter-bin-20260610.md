## 2026-06-10 13:50 PDT - Local Clutter-Bin 10-Sphere Setup

Goal:
- Render the DEXTRAH Isaac Lab clutter-bin scene locally with 10 dynamic
  spheres and the already half-height bin (`bin_h = 0.75 * bin_l`).

Hypothesis:
- A local Docker runtime using `nvcr.io/nvidia/isaac-lab:2.2.0`, the cloned
  IsaacLab `v2.2.1` source, mounted DEXTRAH/FABRICS sources, and a small
  extra Python target for `urdfpy==0.0.22` should reproduce the l401 render
  wrapper locally without installing duplicate Torch/Numpy wheels.

Change:
- Pulled the Isaac Lab 2.2.0 container locally.
- Cloned IsaacLab `v2.2.1` to `/home/lzha/code/IsaacLab-v2.2.1`.
- Verified `dextrah_lab/assets/kuka_allegro/kuka_allegro_colored.usd` is a
  materialized Git LFS asset, not a pointer.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `ae755a1b9e554771c541ba8a1f4253dc6f40dfdf`
- implementation_commit: pending
- push/pull: n/a, local render only.
- changed_files: `WORKLOG.md`
- remote_commit/status: n/a local; DEXTRAH dirty state has pre-existing
  untracked `AGENTS.md`.

Command / Job:
- setup command: pending local Docker run.
- job_id: n/a local
- run_dir: `/home/lzha/code/DEXTRAH/local_results/clutter_bin_env/<run_name>`
- logs: `<run_dir>/render_stdout.log`
- artifacts: `frames/overview_%04d.png`, `overview.mp4`,
  `settle_metrics.json`, `scene_metadata.json`, `clutter_bin_env.usda`

Result:
- Minimal Isaac Lab 2.3.2 camera smoke passed on Docker GPU 0 / RTX 6000 Ada
  and printed `APP_LAUNCHED_CAMERAS_R580_232`.
- The previous camera-enabled RTX startup crash no longer reproduces with
  driver `580.159.03`.

## 2026-06-10 14:45 PDT - Post-R580 Local 10-Sphere Clutter-Bin Render

Goal:
- Render the DEXTRAH clutter-bin environment locally with 10 dynamic spheres
  and the half-height bin after the R580 driver change.

Command / Job:
- image: `nvcr.io/nvidia/isaac-lab:2.2.0`
- IsaacLab source: `/home/lzha/code/IsaacLab-v2.2.1`
- run_name: `local_clutter_bin_sphere10_halfheight_postr580_20260610_144049`
- run_dir:
  `local_results/clutter_bin_env/local_clutter_bin_sphere10_halfheight_postr580_20260610_144049`
- command: local Docker render with `--headless --enable_cameras
  --device cuda:0 --physics_device cuda:0 --dynamic_sphere_count 10
  --bin_l 0.48 --capture_video --width 640 --height 360 --fps 8
  --video_seconds 2.0`.

Result:
- status: passed.
- The render reached DEXTRAH scene logs, created exactly 10 clutter spheres,
  settled the scene, captured 16 overview frames, wrote metadata, and exported
  `clutter_bin_env.usda`.
- Output artifacts:
  - `scene_metadata.json`
  - `settle_metrics.json`
  - `render_manifest.json`
  - `clutter_bin_env.usda`
  - `frames/overview_0000.png` through `frames/overview_0015.png`
  - `overview.gif` encoded locally from the PNG sequence with Pillow because
    neither host nor container had `ffmpeg` / `ffprobe`.

Validation:
- metadata confirms `bin_l = 0.48`, `bin_h = 0.36`, and
  `bin_h_over_l = 0.75`, with note `Half of the original 1.5*l bin height.`
- metadata confirms `dynamic_sphere_count_target = 10` and clutter record
  count `10`.
- checks passed for `bin_height_is_0p75_l`, wall/rim collision APIs, dynamic
  rigid-body sphere clutter, symmetric bins, and left-bin negative-Y placement.
- settle metrics: `settled=True`, `actual_steps=1110`, maximum final linear
  speed `3.061e-08`, maximum final angular speed `6.784e-07`.
- visual inspection of frames 0, 8, and 15 showed a coherent scene with two
  half-height bins on the table, sphere clutter in the left bin, empty right
  bin, and the robot visible at the side.
- no active Docker containers remained after the render.

Analysis:
- The local NVIDIA driver change resolved the original camera-enabled Isaac
  startup crash. The same Isaac Lab 2.2.x / Isaac Sim 5.0 render path that
  crashed under driver `595.71.05` now completes under driver `580.159.03`.
- The remaining Warp `cuDeviceGetUuid` warning is non-fatal for this run; the
  scene rendered and produced complete artifacts.
- local GPU visible in Docker: RTX 6000 Ada and T400.
- image: `nvcr.io/nvidia/isaac-lab:2.2.0`
- IsaacLab source: `0f00ca2b4b2d54d5f90006a92abb1b00a72b2f20` (`v2.2.1`)

Analysis:
- The scene script already uses the requested half-height bin setting and
  exposes `--dynamic_sphere_count` for the requested 10 balls, so no scene code
  edit is expected unless local runtime issues appear.

Next:
- Set up the local Python target, run import and compile checks, render the
  10-sphere overview video locally, then inspect metadata and frames.

## 2026-06-10 13:53 PDT - Local Render Retry Without CUDA_VISIBLE_DEVICES

Goal:
- Recover the first local 10-sphere clutter-bin render attempt after Isaac
  crashed before reaching project scene logs.

Hypothesis:
- Docker already exposed only GPU 0 with `--gpus '"device=0"'`; additionally
  setting `CUDA_VISIBLE_DEVICES=0` triggered the Omniverse warning about CUDA
  and renderer device-enumeration mismatch, and may have caused the RTX scene
  database crash during startup.

Change:
- No code change.
- Retry the same render command without `CUDA_VISIBLE_DEVICES`.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `ae755a1b9e554771c541ba8a1f4253dc6f40dfdf`
- implementation_commit: pending
- push/pull: n/a, local render only.
- changed_files: `WORKLOG.md`

Command / Job:
- failed run_name: `local_clutter_bin_sphere10_halfheight_20260610_135213`
- failed log:
  `local_results/clutter_bin_env/local_clutter_bin_sphere10_halfheight_20260610_135213/render_stdout.log`
- failed command: local Docker Isaac render with `CUDA_VISIBLE_DEVICES=0`
- retry command: same render settings, without `CUDA_VISIBLE_DEVICES`.
- artifacts: pending

Result:
- status: failed first attempt, retry pending.
- key evidence: Isaac loaded the headless rendering kit and detected the RTX
  6000 Ada, then crashed in `librtx.scenedb.plugin.so` before any
  `[clutter-bin]` project logs or metadata were written.

Analysis:
- The crash happened before scene construction, so the 10-sphere scene physics
  and camera path have not been tested yet.

Next:
- Relaunch without `CUDA_VISIBLE_DEVICES`; if it still crashes before project
  logs, test a lower-level headless Isaac startup and consider local driver /
  RTX renderer compatibility before changing scene code.

## 2026-06-10 14:02 PDT - Local Camera Render Blocked by RTX Startup Crash

Goal:
- Finish the requested local clutter-bin render with 10 dynamic spheres and the
  half-height bin.

Setup:
- Pulled `nvcr.io/nvidia/isaac-lab:2.2.0`.
- Cloned IsaacLab v2.2.1 to `/home/lzha/code/IsaacLab-v2.2.1`.
- Reused local DEXTRAH and FABRICS checkouts.
- Created `/home/lzha/code/.local_dextrah_envs/dextrah-isaaclab/site` and
  installed the extra `urdfpy==0.0.22` module expected by the DEXTRAH scene
  stack.
- Verified the Kuka Allegro USD asset is materialized from Git LFS.

Validation:
- `python3 -m py_compile dextrah_lab/scene_scripts/render_clutter_bin_env.py`
  passed.
- `bash -n cluster/sbatch_render_clutter_bin_env.sh` passed.
- Container import smoke passed for `isaaclab.app.AppLauncher`, `fabrics_sim`,
  `dextrah_lab`, `urdfpy`, and CUDA-enabled torch.
- Minimal headless IsaacLab launch without cameras passed.

Command / Job:
- run_name: `local_clutter_bin_sphere10_halfheight_20260610_135213`
- retry_run_name: `local_clutter_bin_sphere10_halfheight_20260610_135339`
- requested scene settings: `--dynamic_sphere_count 10`,
  `bin_h = 0.75 * bin_l`.
- logs:
  `local_results/clutter_bin_env/local_clutter_bin_sphere10_halfheight_20260610_135213/render_stdout.log`
  and
  `local_results/clutter_bin_env/local_clutter_bin_sphere10_halfheight_20260610_135339/render_stdout.log`

Result:
- status: blocked locally before scene construction.
- No `scene_metadata.json`, frames, or video were written.
- Both camera-enabled render attempts crashed inside Isaac/RTX startup before
  any `[clutter-bin]` scene logs.
- A minimal `AppLauncher` test with `--enable_cameras` reproduced the same
  crash, while the same launch without cameras succeeded.
- The generated 6.2 GB `core` dump was removed after preserving stdout logs.

Analysis:
- The blocker is local camera-enabled RTX startup, not the clutter-bin scene
  implementation. The crash stack is in `librtx.scenedb.plugin.so` /
  `omni.usd::UsdContext::newStage` on host driver `595.71.05`.
- The script already implements the requested bin height as half of the
  original `1.5 * l` value via `bin_h = 0.75 * bin_l`, and the ball count is
  controlled by `--dynamic_sphere_count 10`.

Next:
- Use a local NVIDIA driver supported by the Isaac Sim renderer stack and rerun
  the same saved command, or render this exact 10-sphere half-height scene on a
  known-good cluster GPU node.

## 2026-06-10 14:18 PDT - Local GPU Isolation Audit

Goal:
- Re-check whether the second local GPU could have interfered with the failed
  camera-enabled render before treating the NVIDIA driver / RTX stack as the
  main blocker.

Commands:
- `nvidia-smi -L`
- `nvidia-smi --query-gpu=index,uuid,name,driver_version,pci.bus_id,memory.total,display_active,display_mode --format=csv`
- `docker run --rm --gpus '"device=0"' -e ACCEPT_EULA=Y --entrypoint /usr/bin/nvidia-smi nvcr.io/nvidia/isaac-lab:2.2.0 -L`
- `docker run --rm --gpus '"device=1"' -e ACCEPT_EULA=Y --entrypoint /usr/bin/nvidia-smi nvcr.io/nvidia/isaac-lab:2.2.0 -L`
- inspected
  `local_results/clutter_bin_env/local_clutter_bin_sphere10_halfheight_20260610_135339/render_stdout.log`

Result:
- Host GPUs:
  - GPU 0: RTX 6000 Ada, UUID `GPU-d2100eb3-17c5-83a3-68ce-6b7876060a20`,
    bus `00000000:01:00.0`, display active.
  - GPU 1: T400 4GB, UUID `GPU-dee9f6dc-54c5-4b91-1b65-2c85dc8fca64`,
    bus `00000000:E1:00.0`, display inactive.
- Docker `--gpus '"device=0"'` exposes only the RTX 6000 Ada inside the
  container as container GPU 0.
- Docker `--gpus '"device=1"'` exposes only the T400 inside the container as
  container GPU 0.
- The failed render log reports `Attached GPUs: 1` and lists only the RTX 6000
  Ada; the T400 is absent from Kit's renderer GPU table.

Analysis:
- The second GPU was not visible to the failing render container, so ordinary
  mixed-GPU enumeration is unlikely to be the cause of the crash.
- Confidence that the immediate failure is in the local camera-enabled
  Isaac/RTX stack is high. Confidence that a driver change is the only fix is
  lower; additional camera-only smoke tests with explicit Kit GPU settings
  should be run before requiring a system driver change.

Next:
- With user approval, run bounded camera-only diagnostics that do not construct
  the DEXTRAH scene: explicit `active_gpu` / multi-GPU-off Kit args, UUID-based
  Docker GPU masking, and a T400-only camera startup check to fully separate
  GPU selection from the renderer/driver path.

## 2026-06-10 14:11 PDT - Isaac Lab 2.3.2 / Isaac Sim 5.1 Local Smoke

Goal:
- Test whether moving from the repo-suggested Isaac Lab 2.2.x / Isaac Sim 5.0
  runtime to the stable Isaac Lab 2.3.2 / Isaac Sim 5.1 runtime resolves the
  local camera-enabled RTX startup crash before changing DEXTRAH scene code.

Hypothesis:
- If the previous crash is specific to Isaac Sim 5.0's headless camera/RTX
  path on this host, the Isaac Lab 2.3.2 container may start cameras
  successfully. If the crash is caused by the host driver / RTX stack, a
  minimal camera smoke may fail before DEXTRAH imports again.

Plan:
- Pull or use `nvcr.io/nvidia/isaac-lab:2.3.2`.
- Run a minimal headless `AppLauncher` camera startup on Docker GPU 0 only.
- If it passes, prepare an IsaacLab `v2.3.2` source checkout/import path,
  rerun import checks with DEXTRAH/FABRICS, then attempt the same 10-sphere
  half-height local clutter-bin render.
- If it fails before DEXTRAH scene code, preserve logs and do not change scene
  implementation.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `ae755a1b9e554771c541ba8a1f4253dc6f40dfdf`
- changed_files: `WORKLOG.md`
- dirty_context: pre-existing untracked `AGENTS.md` and local render logs under
  `local_results/`.

Command / Job:
- image: `nvcr.io/nvidia/isaac-lab:2.3.2`
- gpu: Docker `--gpus '"device=0"'` targeting the RTX 6000 Ada only.
- run_dir: pending under `local_results/isaaclab_232_smoke/`.
- logs: pending.

Result:
- status: in progress.

## 2026-06-10 16:24 PDT - GraspGenX cuRobo Franka-Star Demo Integration

Goal:
- Create a DEXTRAH demo path where the Franka kitting scene can show a robot
  grasping the kitting object using the GraspGenX + cuRobo end-to-end pipeline.

Hypothesis:
- Keep the planner in a DEXTRAH-owned script but reuse GraspGenX `end2end`
  modules for grasp inference, cuRobo planning, and Newton playback. Render the
  resulting trajectory in the existing DEXTRAH Isaac star-kitting scene.

Change:
- Added `dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py`.
- Added `cluster/sbatch_plan_franka_star_graspgenx_curobo.sh`.
- Extended `dextrah_lab/scene_scripts/render_star_kitting_env.py` with
  `--franka_motion trajectory`, `--franka_trajectory_json`, robot joint target
  playback, and star object pose playback from GraspGenX trajectory frames.
- Extended `cluster/sbatch_render_star_kitting_env.sh` to pass trajectory JSON
  settings through to the renderer.
- The planning script writes generated star mesh/configs, `trajectory.json`,
  and `plan_summary.json` under a run directory.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- base_commit: `844bbc57f4f1336bb17b9998ffa1ba539bf35a02`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py`
  - `dextrah_lab/scene_scripts/render_star_kitting_env.py`
  - `cluster/sbatch_plan_franka_star_graspgenx_curobo.sh`
  - `cluster/sbatch_render_star_kitting_env.sh`
  - `WORKLOG.md`
- dirty_context: pre-existing untracked `AGENTS.md`, `local_results/`, and
  preserved local worklog notes from the pre-pull merge.

Command / Job:
- local checks:
  `python3 -m py_compile dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py dextrah_lab/scene_scripts/render_star_kitting_env.py`
- local checks:
  `bash -n cluster/sbatch_plan_franka_star_graspgenx_curobo.sh && bash -n cluster/sbatch_render_star_kitting_env.sh`
- local checks: `git diff --check`
- local setup note: a quick `uv run` bounds check in `/home/lzha/code/graspgenx`
  triggered a large local environment bootstrap. It was terminated after a long
  silent install phase and will not be used as the primary validation path.

Result:
- status: implementation checkpoint passed cheap local syntax checks.
- no GraspGenX/cuRobo runtime job has been launched yet for this integration.

Analysis:
- The demo uses the Franka-graspable DEXTRAH star dimensions
  (`outer_radius=0.032`, `inner_radius=0.0145`, `thickness=0.040`) rather than
  the larger visual-only star render defaults.
- The generated planner scene uses DEXTRAH coordinates and exact cuRobo cuboids
  for the tabletop and fixture, avoiding procedural-table height ambiguity.

Next:
- Run a GraspGenX/cuRobo import and trajectory-generation smoke in the existing
  container/venv path.
- Render the generated trajectory in the DEXTRAH star-kitting scene, inspect
  logs/metadata/frames/video, then patch and relaunch if the grasp or playback
  is abnormal.

## 2026-06-10 16:20 PDT - DEXTRAH Teacher Monitor After Pull

Goal:
- Continue active monitoring of teacher job `28942245` through the expected
  wall-time requeue window.

Version Control:
- branch: `codex/dextrah-cluster-dev`
- local pull: fast-forwarded to `04ed88c` from origin.
- local status: `WORKLOG.md` remains dirty with preserved local render notes
  and this monitor entry; untracked `AGENTS.md` and `local_results/` remain.
- remote checkout: not changed by this monitor step while the teacher job is
  running.

Command / Job:
- job_id: `28942245`
- run_name: `teacher_short_20260609_100021`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/teacher_8gpu_28942245.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021`

Result:
- status: running healthy at `16:19 PDT`.
- scheduler: `RUNNING` on `polar3`, node `batch-block7-01008`,
  `Requeue=1`, `Restarts=1`, end time `2026-06-10T16:58:55`.
- log tail reached epoch `13155/20000`.
- latest complete checkpoint observed:
  `last_dextrah_lstm_ep_13150_rew_685.8873.pth`.
- all runtime sidecars rank `0` through `7` refreshed at `16:16`.
- recent-tail error scan found no traceback, RuntimeError, CUDA/NCCL error,
  OOM, killed, requested-operation, or training-failure signatures.

Metrics:
- TensorBoard parsed through epoch `13147`:
  - `in_success_region/iter`: latest `0.45459`, last-50 `0.44918`,
    last-200 `0.447936`.
  - `rewards/iter`: latest `631.862`, last-50 `608.292`,
    last-200 `609.352`.
  - `num_adr_increases/iter`: `50`.
  - `info/kl`: latest `0.0104055`, last-50 `0.00879989`,
    last-200 `0.00963561`.
  - `losses/a_loss`: last-50 `-0.00467847`.
  - `losses/c_loss`: last-50 `0.0181603`.
  - `performance/step_inference_rl_update_fps`: last-50 about `105050`.

Analysis:
- Training remains stable in max-ADR mode, with success-region metrics above
  the `0.4` ADR threshold and no loss/KL instability.
- Checkpoint and runtime sidecar cadence is healthy for the next requeue.

Next:
- Continue short one-shot checks until the expected `TERM@300` signal around
  `16:53:55 PDT`, then verify requeue and restore from the newest checkpoint
  and runtime sidecars before reporting completion.

Next:
- Pull the 2.3.2 image and launch the minimal camera startup smoke.

## 2026-06-10 14:17 PDT - Isaac Lab 2.3.2 Smoke Result

Goal:
- Determine whether the stable Isaac Lab 2.3.2 / Isaac Sim 5.1 container fixes
  the local headless camera startup crash seen with the 2.2.x / 5.0 runtime.

Commands / Artifacts:
- image: `nvcr.io/nvidia/isaac-lab:2.3.2`
- run_dir:
  `local_results/isaaclab_232_smoke/smoke_20260610_141447`
- logs:
  - `no_camera_stdout.log`
  - `camera_stdout.log`
  - `camera_multigpu_off_stdout.log`
  - `camera_uuid_mask_stdout.log`
  - `camera_t400_only_stdout.log`

Result:
- no-camera baseline on Docker GPU 0 / RTX 6000 Ada: passed and printed
  `APP_LAUNCHED_NO_CAMERAS_232`.
- camera baseline on Docker GPU 0 / RTX 6000 Ada: failed with segmentation
  fault in `librtx.scenedb.plugin.so` / `omni::usd::UsdContext::newStage`.
- camera with explicit Kit multi-GPU disabled: failed in the same RTX scene
  database path.
- camera with UUID-based RTX 6000 Ada masking: failed in the same RTX scene
  database path; Kit still reported `Attached GPUs: 1`.
- camera with only the T400 exposed: failed earlier in the Vulkan/EGL stack.
  This is not a viable render target for the clutter-bin job due to the 4 GB
  GPU and different renderer startup failure.
- No DEXTRAH scene render was launched because the minimal camera-enabled
  Isaac Lab startup failed before any scene construction.
- No core dump remained after the runs; core dumps were disabled inside the
  smoke containers.

Analysis:
- Upgrading to the stable Isaac Lab 2.3.2 / Isaac Sim 5.1 container does not
  resolve the local camera-enabled startup crash on the RTX 6000 Ada with host
  driver `595.71.05`.
- The second GPU is not the cause of the RTX 6000 render failure: index and
  UUID masking expose exactly one GPU to the container, and the same RTX scene
  database crash occurs.
- The failure is now reproduced across Isaac Sim 5.0 and 5.1 camera-enabled
  Isaac Lab runtimes, while no-camera Isaac Lab startup succeeds.

Next:
- Do not spend time changing the DEXTRAH scene for this local failure. The next
  useful options are a supported local NVIDIA production driver for Isaac Sim's
  RTX renderer path, a known-good cluster render node, or a separate larger
  Isaac Sim 6.0 / Isaac Lab 3.x migration experiment.

## 2026-06-10 14:35 PDT - Post-Reboot R580 Local Camera Retest

Goal:
- Check whether the local Isaac camera crash is resolved after rebooting into
  the R580 NVIDIA driver branch.

Environment:
- host driver: `580.159.03`
- GPUs:
  - RTX 6000 Ada, UUID `GPU-d2100eb3-17c5-83a3-68ce-6b7876060a20`
  - T400 4GB, UUID `GPU-dee9f6dc-54c5-4b91-1b65-2c85dc8fca64`
- Docker `--gpus '"device=0"'` exposes only the RTX 6000 Ada and reports
  driver `580.159.03`.

Plan:
- Rerun the minimal Isaac Lab 2.3.2 `AppLauncher(headless=True,
  enable_cameras=True)` smoke that previously crashed under driver `595.71.05`.
- If it passes, rerun the DEXTRAH local clutter-bin render with 10 dynamic
  spheres and the half-height bin.

Result:
- status: in progress.
