# DextrAH on Isaac Lab

DextrAH is a high-performance hand-arm grasping policy. This codebase provides the machinery required to train such a policy in Isaac Lab starting with privileged RL training followed by online distillation that swaps the input space to camera data.

## Installation
**Note**: This project will download and install additional third-party open source software projects. Review the license terms of these open source projects before use.

1. [Install](https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/pip_installation.html) Isaac Sim, Isaac Lab following the local conda install route.

**Note**: After you clone the Isaac Lab repository and before installation, checkout the tag `v2.2.1` before installation (can also work with `v2.0.2` with minor code changes):
```bash
        cd <IsaacLab>
        git checkout v2.2.1
```
2. Install geometric fabrics from this [repo](https://github.com/NVlabs/FABRICS) within your new conda env

3. Install Dextrah for Isaac Lab within your new conda env
```bash
        curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
        git lfs clone git@github.com:NVlabs/DEXTRAH.git
        cd <DEXTRAH>
        poetry install
        or
        python -m pip install -e .
```
4. Ensure high enough `GLIBCXX_` can be found
```bash
        conda install -c conda-forge libstdcxx-ng
        conda install -c conda-forge libgcc-ng=12 libstdcxx-ng=12
```

## DextrAH Privileged FGP Teacher Training
1. Single-GPU training

**Note**: set `num_gpus_per_node` to the number of GPUs available, often 1. set `num_nodes` to number of training nodes (1 if running locally)

**Note**: `env.use_cuda_graph=True` uses a cuda graph capture of fabrics and makes training faster. It may lead to cuda memory issues in some cases.
```bash
        cd <DEXTRAH>/dextrah_lab/rl_games
        python -m torch.distributed.run --nnodes=<num_nodes> --nproc_per_node=<num_gpus_per_node>\
          train.py \
            --headless \
            --task=Dextrah-Kuka-Allegro \
            --seed -1 \
            --distributed \
            --num_envs 4096 \
            agent.params.config.minibatch_size=16384 \
            agent.params.config.central_value_config.minibatch_size=16384 \
            agent.params.config.learning_rate=0.0001 \
            agent.params.config.horizon_length=16 \
            agent.params.config.mini_epochs=4 \
            agent.params.config.multi_gpu=True \
            agent.wandb_activate=False \
            env.success_for_adr=0.4 \
            env.objects_dir=visdex_objects \
            env.adr_custom_cfg_dict.fabric_damping.gain="[10.0, 20.0]" \
            env.adr_custom_cfg_dict.reward_weights.finger_curl_reg="[-0.01, -0.01]" \
            env.adr_custom_cfg_dict.reward_weights.lift_weight="[5.0, 0.0]" \
            env.max_pose_angle=45.0 \
            env.use_cuda_graph=True
```

### Single-cube state-based grasp training
The single-cube task reuses the RL-Games PPO training path and registers as
`Dextrah-Cube-Grasp`. It spawns one procedural cube, randomizes its reset
location over an 8 cm by 8 cm XY square, exposes cube state to the policy, and
uses grasp/lift reward terms logged under `cube_*`.

```bash
        cd <DEXTRAH>/dextrah_lab/rl_games
        python train.py \
            --headless \
            --task=Dextrah-Cube-Grasp \
            --seed -1 \
            --num_envs 4096 \
            agent.params.config.minibatch_size=16384 \
            agent.params.config.central_value_config.minibatch_size=16384 \
            agent.params.config.learning_rate=0.0003 \
            agent.wandb_activate=False \
            env.use_cuda_graph=True
```

The A100 wrapper can launch the same task with:
```bash
        TASK=Dextrah-Cube-Grasp FULL_EXPERIMENT_NAME=cube_grasp_smoke \
          sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh
```

### Franka GraspGen multi-object grasp training
The multi-object Franka task registers as `Dextrah-Franka-Multi-Object-Grasp`.
It samples one object asset per vectorized environment, applies the GraspGen
object scale from the dataset manifest, and can reset the Franka near a
per-object Franka grasp prior. The policy input extends the cube teacher state
with object scale, bounds, object id, and prior-availability features.

Prepare a local debug subset from the Robotiq split while extracting Franka
priors and scales from the matching Franka GraspGen shards:

```bash
        python dextrah_lab/assets/prepare_graspgen_assets.py \
            --output_dir local_results/graspgen_objects_debug \
            --limit 16 \
            --prefer_single_shard
```

Convert the generated URDF assets to USD with Isaac Lab:

```bash
        python dextrah_lab/assets/batch_convert_urdf.py \
            local_results/graspgen_objects_debug/urdf \
            local_results/graspgen_objects_debug/USD \
            --headless
```

Validate loading, reset geometry, grasp-prior reset, and rollout finiteness
before training:

```bash
        cd dextrah_lab/rl_games
        python validate_franka_multi_object_grasp_env.py \
            --headless \
            --task Dextrah-Franka-Multi-Object-Grasp \
            --num_envs 8 \
            --object_asset_manifest_path ../../local_results/graspgen_objects_debug/manifest.json \
            --max_objects 8 \
            --enable_grasp_prior_reset \
            --render_check
```

Render pre-training evidence videos for reset settling, perturbation response,
and grasp-prior contact/lift:

```bash
        OBJECT_ASSET_MANIFEST_PATH=/results/assets/graspgen_objects/manifest.json \
        RUN_NAME=franka_multi_object_video_validate \
          sbatch --export=ALL cluster/sbatch_validate_franka_multi_object_grasp_videos_1gpu.sh
```

On the cluster, prepare/convert the full object set on mounted storage. Use a
small `LIMIT` first for a cluster smoke test, then set `LIMIT=0` for the full
Robotiq split:

```bash
        CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/<agent_id> \
        ASSET_OUTPUT_DIR_HOST=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/assets/graspgen_objects \
        ASSET_OUTPUT_DIR_CONTAINER=/results/assets/graspgen_objects \
        LIMIT=0 \
          sbatch --export=ALL cluster/sbatch_prepare_graspgen_assets_1gpu.sh

   The cluster wrapper skips existing USDs by default so interrupted full-set
   conversion can be resumed in the same output directory.
```

On a1001, launch teacher training with the staged manifest that passed
validation:

```bash
        TASK=Dextrah-Franka-Multi-Object-Grasp \
        OBJECT_ASSET_MANIFEST_PATH=/results/assets/graspgen_objects/manifest.json \
        GRASP_PRIOR_RESET_ENABLED=True \
        FULL_EXPERIMENT_NAME=franka_multi_object_grasp_teacher \
          sbatch --export=ALL cluster/sbatch_train_teacher_8gpu.sh
```

## DextrAH Camera-based FGP Student Distillation
**Note**: Before starting the student training, you also need to download the visual texture data (textures.zip) and place its contents inside `dextrah_lab/assets` directory. Download the assets from [link](https://huggingface.co/datasets/nvidia/dextrah_textures/blob/main/textures.zip) and unzip its contents into the assets folder.

1. Training

**Note**: If you want to train with additional data augmentation, you can pass the `--data_aug` flag, but this is often unnecessary.
```bash
        cd <DEXTRAH>/dextrah_lab/distillation
        # NOTE: in general we should try to use a perfect square number of tiles
        python -m torch.distributed.run --nnodes=<num_nodes> --nproc_per_node=<num_gpus_per_node> \
          run_distillation.py \
            --headless
            --distributed \
            --task=Dextrah-Kuka-Allegro \
            --num_envs 256 env.distillation=True \
            --enable_cameras env.simulate_stereo=True \
            --teacher <path_to_teacher>  \
            env.img_aug_type="rgb" \
            env.aux_coeff=10. \
            env.objects_dir="visdex_objects" \
            env.max_pose_angle=45.0 \
            env.adr_custom_cfg_dict.fabric_damping.gain="[10.0, 20.0]" \
            env.adr_custom_cfg_dict.reward_weights.finger_curl_reg="[-0.01, -0.01]" \
            env.adr_custom_cfg_dict.reward_weights.lift_weight="[5.0, 0.0]" \
            env.use_cuda_graph=True
```

2. Single-GPU evaluation
To eval (i.e. play) a trained student policy, run the following command:
```bash
        cd <DEXTRAH>/dextrah_lab/distillation
        python eval.py \
        --task=Dextrah-Kuka-Allegro \
        --num_envs 32 \
        --enable_cameras \
        --checkpoint <path_to_checkpoint> \
        --num_episodes 10 \
        env.distillation=True \
        env.simulate_stereo=True \
        env.img_aug_type="rgb" \
        env.objects_dir="visdex_objects" \
        env.max_pose_angle=45.0 \
        env.adr_custom_cfg_dict.fabric_damping.gain="[10.0, 20.0]" \
        env.adr_custom_cfg_dict.reward_weights.finger_curl_reg="[-0.01, -0.01]" \
        env.adr_custom_cfg_dict.reward_weights.lift_weight="[5.0, 0.0]" \
        env.use_cuda_graph=True
```

The eval script also provide functions to record data. Passing the following
extra args for data recording.
```bash
        --record_data \
        --max_records_per_file 100 \
        --create_video
```
**Note:** By default, most of the randomization are turned off for data recording.

**Note:** The create video arg will create videos for the recorded data for easy data inspection.
However, it will slow down the process. It's recommended to only use it for debugging.

## Notes
One can update dependences in deps.txt file, remove pyproject.toml and poetry.lock files, and regenerate them
```bash
    cd <DEXTRAH>
    rm pyproject.toml poetry.lock
    poetry init --name "dextrah_lab" --no-interaction
    xargs poetry add < deps.txt
    poetry install
```
The `dextrah_lab/deployment_scripts` directory contains several reference scripts to show how to deploy the trained FGP, fabric controller, state machine, and camera calibration. These will not run out of the box because they depend on camera, PD controller, and robot driver ROS 2 nodes to be running, which are not included. Specifically, these are of interest
```bash
    camera_calibration.py
    camera_transform_publisher.py
    kuka_allegro_fabric.py
    kuka_allegro_state_machine.py
    kuka_allegro_stereo_fgp.py
```
