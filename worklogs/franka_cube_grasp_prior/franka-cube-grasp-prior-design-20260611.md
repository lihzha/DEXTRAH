# Franka Cube Grasp Prior Design

Date: 2026-06-11

## Goal

Build an apple-to-apple comparison against the existing
`Dextrah-Franka-Cube-Grasp` RL baseline to test whether a GraspGenX grasp prior
accelerates learning.

The first accepted variant is intentionally narrow:

- Use GraspGenX once on the centered cube mesh to produce a library of
  object-local grasp poses.
- During `Dextrah-Franka-Cube-Grasp` reset, keep the current cube reset
  distribution and task config unchanged.
- Sample a grasp from the precomputed library, transform it by the sampled cube
  pose, reset the Franka to a 3 cm pregrasp pose away from the cube, keep the
  gripper open, then start normal RL at environment step 0.
- Keep PPO settings, number of envs, number of GPUs, observation space, action
  space, reward terms, termination logic, and cube reset behavior the same as
  the current DEXTRAH Franka cube RL task.

The comparison claim should be: same RL task and training config, with only the
robot reset state changed by a GraspGenX-derived pregrasp prior.

## Baseline To Preserve

The current production task is `Dextrah-Franka-Cube-Grasp` in:

- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`
- `dextrah_lab/tasks/dextrah_franka_cube_grasp/agents/rl_games_ppo_franka_cube_grasp_cfg.yaml`

Important baseline properties to keep unchanged for variant 1:

- Cube size: 0.06 m.
- Cube spawn XY randomization: current `cube_spawn_xy_randomization`.
- Cube orientation: keep current behavior. Do not add yaw randomization for the
  first comparison.
- Cube spawn height, table geometry, reward weights, termination thresholds,
  action scaling, observation vector, and action vector: unchanged.
- PPO/training wrapper: keep the existing Franka cube branch in
  `cluster/sbatch_train_teacher_8gpu.sh`, including default `NUM_ENVS=2048`,
  `NPROC_PER_NODE=8`, horizon/minibatch/lr/gamma/tau settings.

The Franka policy action space is 7D relative end-effector pose plus gripper.
The grasp prior should only affect reset initialization, not the policy action
definition.

## Accepted Variant 1: Grasp-Open Pregrasp Reset

### Offline grasp library

GraspGenX centers the object point cloud before sampling, then un-centers
grasps back to the mesh-local/object frame. For this task, compute the cube
grasps once for a centered 60 mm cube and store object-local transforms.

Recommended compact library fields:

- `cube_size_m`
- `gripper_name`
- `tool_frame`
- `grasp_to_tool_transform`
- `grasps_object`: array of 4x4 `T_object_grasp` transforms
- `confidence`: per-grasp score
- optional labels such as top-down/side, source planner tag, and quality flags

Do not store full per-link mesh transforms or full rendered trajectory JSON for
this variant. This reset prior only needs object-local grasp/tool poses.

### Reset transform

At reset, after sampling the cube pose exactly as the baseline currently does:

1. Sample a grasp entry `T_object_grasp` from the library.
2. Build `T_world_object` from the sampled cube pose in the env-local/world
   frame used by the DEXTRAH task.
3. Compute:

   ```text
   T_world_grasp = T_world_object @ T_object_grasp
   T_world_tool = T_world_grasp @ T_grasp_tool
   ```

4. Apply the 3 cm pregrasp offset away from the object. Prefer the same approach
   convention used by the GraspGenX/cuRobo Franka config. The implementation
   must validate the sign visually/numerically: the resulting tool/finger
   center should be farther from the cube center than the exact grasp pose.
5. Solve/reset the Franka arm to that target `panda_hand`/tool pose.
6. Set gripper joints open.
7. Set robot target buffers and IK controller state consistently with the
   written joint state.
8. Start normal RL immediately. Do not add a pre-roll phase for variant 1.

The reset should be disabled by default and enabled only via explicit config or
launch override, so the original baseline remains available.

## Key Frame/IK Risks

The clean mathematical transform is for poses, not joint trajectories. For this
first variant, we are not transforming or replaying a trajectory.

Known frame details:

- GraspGenX Franka config targets `panda_hand`.
- DEXTRAH computes its end-effector frame as `panda_hand` plus
  `ee_offset_pos=(0, 0, 0.1034)`.
- GraspGenX's Franka config uses a non-identity `grasp_to_tool_transform` to
  align the grasp closing axis with the Panda hand frame.

Therefore implementation must explicitly verify which frame the reset IK target
uses. Do not assume a GraspGenX grasp frame is already equal to the DEXTRAH
policy end-effector frame.

The DEXTRAH env reset writes joint state directly. The prior target is a pose,
so implementation needs either:

- a reset-only absolute IK solve inside Isaac Lab, or
- an offline/cache step that maps sampled object pose and grasp index to Franka
  joint state.

For variant 1, a reset-only IK utility is acceptable if it runs outside the PPO
hot action path and is validated to be cheap enough for vectorized resets.

## Validation Plan Before Full Training

No full 8-GPU job should launch until the reset prior passes bounded checks.

Minimum checks:

1. Import/config check for the new prior fields with prior disabled and enabled.
2. Generate a small grasp library for the DEXTRAH 60 mm cube.
3. Run a small Isaac validation, for example 16-64 envs, that resets repeatedly
   with the prior enabled and records:
   - IK success/failure rate
   - target pose error
   - finger center to cube distance
   - finger table clearance
   - immediate termination rate
   - NaN/Inf checks
4. Visually inspect at least one reset/render artifact or selected frames.
5. Run a short RL smoke with the prior enabled and the same reward/task config.
6. Only then launch the production apple-to-apple training run using the
   existing `Dextrah-Franka-Cube-Grasp` 8-GPU wrapper settings.

Acceptance for the reset smoke:

- No systematic initial table penetration.
- No immediate episode termination spike from the prior reset.
- Most reset states place the open gripper within a plausible 3 cm pregrasp
  distance from the cube.
- With the prior disabled, baseline behavior remains unchanged.

## Parallel Alternatives For Other Agents

These are intentionally separate from variant 1 so the apple-to-apple reset
comparison stays clean.

### Alternative A: Trajectory Tracking Reward

Use GraspGenX + cuRobo to generate reference trajectories and add tracking
reward during early grasping.

Open design questions:

- Whether to expose reference phase/target in observations. This is likely more
  learnable but changes the observation space, so it is not a strict
  apple-to-apple baseline.
- Whether to track end-effector pose, joint state, gripper schedule, or a
  lower-dimensional progress signal.
- How to handle transformed trajectories safely. Joint trajectories should not
  be blindly transformed; task-space waypoints can be transformed, then solved
  and validated.

Suggested scope:

- Store task-space waypoints and phase labels, not just joint arrays.
- Add reward-only tracking first if preserving observation dimensions is
  important.
- Add phase/reference observations later as a separate ablation.

### Alternative B: BC Warm Start Then RL

Use offline GraspGenX/cuRobo trajectories to pretrain a policy, then continue
PPO on the real DEXTRAH Franka cube task.

Open design questions:

- Whether the BC action targets should be DEXTRAH relative EE actions or joint
  actions converted through the existing controller.
- Whether BC should learn only approach/pregrasp behavior or include close/lift.
- How to mix BC with PPO: pure pretrain, auxiliary imitation loss, or DAgger-like
  refresh.

Suggested scope:

- Convert planned task-space waypoints to the same 7D relative EE+gripper action
  convention used by the env.
- Pretrain only the approach-to-pregrasp portion first.
- Evaluate whether BC initialization improves early reward/success compared
  with both scratch RL and variant 1 reset prior.

### Alternative C: Offline Motion-Planning Library

Generate many object pose and grasp samples with cuRobo-validated joint states
or short plans.

This is useful if reset-time IK is too slow or unreliable. It is a larger design
than variant 1 because it introduces nearest-neighbor retrieval and validity
envelopes over object pose perturbations.

## Implementation Notes For Future Agent

Recommended file ownership for variant 1:

- Add grasp-library export script under `dextrah_lab/scene_scripts/`.
- Add optional prior config fields in
  `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env_cfg.py`.
- Add reset-prior loading/sampling/IK code in
  `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`.
- Optionally add a small validation script under `dextrah_lab/rl_games/` or
  `dextrah_lab/scene_scripts/`.
- Update this worklog with commands, artifacts, and observed reset metrics.

Parallel agents should use isolated worktrees/branches and avoid editing the
same task files at the same time unless an orchestrator assigns ownership.

No online cuRobo call should be placed inside the main RL action step. Online
planning at every reset is also a fallback, not the first design, because it
risks slowing vectorized PPO and complicating synchronization.

