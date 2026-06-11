# DEXTRAH a1001 Workflow

This follows the local a1001 workflow pattern used for GraspGenX.

Fixed paths:

- Remote host: `a1001`
- NFS root: `/lustre/fsw/portfolios/nvr/users/lzha`
- Remote code: `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`
- Remote FABRICS source: `/lustre/fsw/portfolios/nvr/users/lzha/src/FABRICS`
- Remote IsaacLab source overlay: `/lustre/fsw/portfolios/nvr/users/lzha/src/IsaacLab-v2.2.1`
- Isaac Lab image: `/lustre/fsw/portfolios/nvr/users/lzha/cache/isaac_lab_2.2.0.sqsh`
- Extra Python target: `/lustre/fsw/portfolios/nvr/users/lzha/envs/dextrah-isaaclab/site`
- Logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah`
- Results: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah`

Submit order:

```bash
./cluster/submit_import_isaaclab_sqsh_a1001.sh
./cluster/submit_setup_dextrah_env_a1001.sh
./cluster/submit_train_teacher_8gpu_a1001.sh
```

The sync script runs `git lfs pull` on a1001, where `git-lfs` is available, so the DEXTRAH assets are materialized on NFS even if the local checkout only has LFS pointer files.

The teacher training script runs the README command from `dextrah_lab/rl_games` with one node and eight local processes:

```bash
/isaac-sim/python.sh -m torch.distributed.run --nnodes=1 --nproc_per_node=8 train.py ...
```

Override common settings through Slurm export, for example:

```bash
ssh a1001 'NUM_ENVS=2048 MAX_ITERATIONS=1000 sbatch /lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH/cluster/sbatch_train_teacher_8gpu.sh'
```

Fetch logs:

```bash
./cluster/fetch_a1001_logs.sh
```
