# Bimanual YAM Assets

The YAM MJCF and mesh files are downloaded from the MolmoAct2 simulation asset
dataset, `TreeePlanter/molmoact2-sim-eval-assets`, then converted into a USD
cache for Isaac Lab.  The environment spawns the cached USD through a
DEXTRAH-style `ArticulationCfg` and `UsdFileCfg`; the generated URDF is only an
offline converter intermediate because Isaac Lab 2.2 does not provide a stable
direct MJCF spawner for this asset.

Prepare them from the DEXTRAH repo root with:

```bash
/isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless
```

The generated environment expects:

- `dextrah_lab/assets/yam/yam_mujoco/bimanual_yam_linear_flattened.xml`
- `dextrah_lab/assets/yam/yam_urdf/bimanual_yam.urdf`
- `dextrah_lab/assets/yam/yam_usd/bimanual_yam.usd`
