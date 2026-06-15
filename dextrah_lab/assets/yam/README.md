# Bimanual YAM Assets

The YAM MJCF and mesh files are downloaded from the MolmoAct2 simulation asset
dataset, `TreeePlanter/molmoact2-sim-eval-assets`, then converted into a USD
cache for Isaac Lab.  The environment spawns the cached USD through a
DEXTRAH-style `ArticulationCfg` and `UsdFileCfg`.  The default cache is produced
by Isaac Lab's MJCF converter, which wraps Isaac Sim's official MJCF importer.
The generated URDF path is retained only as a legacy fallback for debugging.

Prepare them from the DEXTRAH repo root with:

```bash
/isaac-sim/python.sh dextrah_lab/assets/scripts/prepare_yam_assets.py --headless
```

The generated environment expects:

- `dextrah_lab/assets/yam/yam_mujoco/bimanual_yam_linear_flattened.xml`
- `dextrah_lab/assets/yam/yam_mjcf_usd/bimanual_yam_linear_flattened.usd`
- `dextrah_lab/assets/yam/yam_urdf/bimanual_yam.urdf` only when using `--converter urdf`
