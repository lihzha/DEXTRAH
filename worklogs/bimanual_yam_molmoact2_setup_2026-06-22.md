# Bimanual YAM MolmoAct2 Setup Alignment

Date: 2026-06-22
Branch: codex/yam-molmoact2-alignment

## Goal

Align the Isaac Lab bimanual YAM setup with the MolmoAct2 ManiSkill bimanual YAM reference while keeping execution in Isaac Lab. The target reference is `allenai/molmoact2/sim_eval/robots/bimanual_yam.py` at GitHub content SHA `dce2db3e0661382e0e534ac6d1b2ee303f6ef4df`.

## Source Values Applied

- Camera order: `top_cam`, `left_cam`, `right_cam`
- Camera resolution: 640 x 360
- Top camera: parent `bimanual_base`, local pos `(0.15, 0.0, 0.8)`, local quat `(0.7660444431189782, 0.0, 0.6427876096865391, 0.0)`, HFOV `69.4`
- Wrist cameras: parents `left_link_6` and `right_link_6`, local pos `(0.0, 0.09, 0.06)`, local quat `(0.612372429196013, -0.35355339154618404, -0.3535533966987049, -0.612372438120441)`, HFOV `87.0`
- Intrinsics from upstream HFOV:
  - top `fx=fy=462.1386898729645`, `cx=320`, `cy=180`
  - wrist `fx=fy=337.20964008990796`, `cx=320`, `cy=180`
- Bimanual arm root separation: `left_arm` y `+0.31`, `right_arm` y `-0.31`
- Robot root pose: `(-0.65, 0.0, 0.01)`
- Table dimensions from ManiSkill `TableSceneBuilder`: `(1.209, 2.418, 0.9196429)`, center `(-0.12, 0.0, -0.45982145)`, top z `0.0`
- Reset qpos follows the original MJCF `bimanual_yam.xml` `home` keyframe per user correction: `0 1.047 1.047 0.1 -0.1 0 0 0 0 1.047 1.047 0.1 -0.1 0 0 0`

## Commands Run

```bash
python3 -m py_compile dextrah_lab/assets/yam/bimanual_yam.py dextrah_lab/assets/scripts/prepare_yam_assets.py dextrah_lab/tasks/dextrah_bimanual_yam_cube_grasp/bimanual_yam_cube_grasp_env_cfg.py dextrah_lab/rl_games/validate_bimanual_yam_cube_grasp_env.py
```

```bash
OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y CI=1 NONINTERACTIVE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/home/lzha/code/DEXTRAH:/home/lzha/code/FABRICS/src:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_assets:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_tasks:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_rl:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_mimic /home/lzha/code/.venvs/dextrah-isaaclab/bin/python dextrah_lab/assets/scripts/prepare_yam_assets.py --robot bimanual --download-only --headless --device cuda:0
```

```bash
OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y CI=1 NONINTERACTIVE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/home/lzha/code/DEXTRAH:/home/lzha/code/FABRICS/src:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_assets:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_tasks:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_rl:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_mimic /home/lzha/code/.venvs/dextrah-isaaclab/bin/python dextrah_lab/assets/scripts/prepare_yam_assets.py --robot bimanual --converter mjcf --force-conversion --headless --device cuda:0
```

```bash
OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y CI=1 NONINTERACTIVE=1 PYTHONUNBUFFERED=1 HYDRA_FULL_ERROR=1 PYTHONFAULTHANDLER=1 PYTHONPATH=/home/lzha/code/DEXTRAH:/home/lzha/code/FABRICS/src:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_assets:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_tasks:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_rl:/home/lzha/code/IsaacLab-v2.2.1/source/isaaclab_mimic /home/lzha/code/.venvs/dextrah-isaaclab/bin/python dextrah_lab/rl_games/validate_bimanual_yam_cube_grasp_env.py --num_envs 1 --setup_only --print_interval 120 --output_dir /tmp/dextrah_bimanual_yam_molmoact2_setup_validate --headless --device cuda:0
```

## Results

- Syntax check passed.
- Asset preparation generated/updated ignored local MJCF assets:
  - `d405_collision.obj`
  - `wrist_camera_mount.obj`
  - `wrist_camera_mount_collision.obj`
  - `bimanual_yam_linear_flattened.xml`
  - `bimanual_yam_linear_flattened_isaac.xml`
  - `bimanual_yam_linear_flattened.usd`
- Setup-only Isaac validation passed with metrics at `/tmp/dextrah_bimanual_yam_molmoact2_setup_validate/metrics.json`.
- Full scripted pickup validation was also run once. All setup checks passed, but the existing scripted cube pickup failed after switching to the original home qpos because the controller missed contact by about 1.4 mm and did not lift. Metrics are at `/tmp/dextrah_bimanual_yam_molmoact2_validate/metrics.json`. This is tracked as a scripted-controller issue, not a setup-alignment failure.

## Camera Visualization Follow-up

- Added `dextrah_lab/scene_scripts/render_bimanual_yam_molmoact2_cameras.py` to render the overview, `top_cam`, `left_cam`, and `right_cam` streams with the shared MolmoAct2 camera constants.
- Added `cluster/sbatch_render_bimanual_yam_molmoact2_cameras_1gpu.sh` for l401 fallback rendering.
- Local strict headless render attempts reached Isaac/Kit startup but one run hit Vulkan `ERROR_DEVICE_LOST` and later runs stalled before project logs, so the render was moved to l401 per the Isaac Lab fallback guidance.
- Committed local changes as `78b99de4d3e61b9b80981db09650a015707f6b32` on `codex/yam-molmoact2-alignment`.
- l401 could not fetch GitHub directly due SSH public-key denial, so the commit was transferred as a Git bundle and fetched into the fixed remote repo.
- Remote worktree: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-molmoact2-camera-viz-78b99de`, detached at `78b99de4d3e61b9b80981db09650a015707f6b32`.
- Submitted l401 smoke render job `1039396`:

```bash
sbatch --parsable --exclude=pool0-00006,pool0-00032 --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/yam-molmoact2-camera-viz-78b99de,CODE_COMMIT=78b99de4d3e61b9b80981db09650a015707f6b32,RUN_NAME=yam_molmoact2_camviz_smoke_78b99de_20260622T1624,FRAMES=3,FPS=3,SIM_STEPS_PER_FRAME=1,DISABLE_FABRIC=True,PREPARE_YAM_ASSETS=auto cluster/sbatch_render_bimanual_yam_molmoact2_cameras_1gpu.sh
```

- Tried one additional local run with `--rendering_mode performance`; it also stalled before project logs and was stopped.
- Replaced pending smoke job `1039396` with leaner job `1039397` (`8` CPUs, `32G`, `10` minutes) using run name `yam_molmoact2_camviz_smoke_78b99de_20260622T1630`. Slurm estimated start: `2026-06-22T17:29:51` on `pool0-00009`.
- Job `1039397` started early on `pool0-00012` and failed during asset preparation because the D405 wrist camera mesh was not present in the detached l401 worktree. The real local D405 STL/OBJ plus generated collision/mount meshes were copied into the ignored remote asset directory for the render smoke.
- Job `1039404` then reached project code on `pool0-00009` but failed because the render script imported the package `__init__` instead of the `gym_setup` registration module. Patched the script to import `dextrah_lab.tasks.dextrah_bimanual_yam_cube_grasp.gym_setup`.
