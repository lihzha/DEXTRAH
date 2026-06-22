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
