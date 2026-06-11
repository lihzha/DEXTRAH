# Worklog - franka-cube-grasp-prior / franka-cube-dp-bc-warmstart

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- created: 2026-06-11T18:39:21Z

## 2026-06-11T11:40:53-07:00 - initial plan / official DP verification

Goal:
- Explore Alternative B: a behavior-cloning warm start from offline
  GraspGenX/cuRobo Franka cube trajectories using Diffusion Policy, kept
  separate from reset-prior and tracking-reward branches.

Hypothesis:
- A low-dimensional Diffusion Policy can imitate planner-generated
  approach-to-pregrasp state-action windows if actions are converted to the
  same DEXTRAH 7D relative EE pose plus gripper convention used by PPO.
- Starting from the official `real-stanford/diffusion_policy` low-dimensional
  config/workspace conventions avoids a misleading simplified reimplementation.

Change:
- Planned source edits only in new BC/Diffusion Policy files:
  - `dextrah_lab/offline_dp_bc/` for trajectory conversion, dataset metadata,
    relative EE action derivation, and smoke validation helpers.
  - `dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml` as a minimal
    official-convention Diffusion Policy config template.
  - optional tests under `tests/` only if the repo has suitable test layout.
- Do not edit Worker A reset-prior env files or Worker B tracking-reward files.
- Do not launch full training. Local import/config/dataset-shape and a tiny
  synthetic one-step smoke are allowed if dependencies permit.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a, local implementation checkpoint only unless requested
- changed_files: owned worklog pending
- remote_commit/status: n/a/local env

Command / Job:
- command: `web search/open for https://github.com/real-stanford/diffusion_policy and https://diffusion-policy.cs.columbia.edu/; local repo inspection pending`
- job_id: n/a
- run_dir: n/a
- logs: n/a
- artifacts: planned config/smoke output only

Result:
- status: in_progress
- metrics/artifacts: none yet
- key evidence: official project page links the Sim & Real repo; official repo
  README documents hydra `train.py`, low_dim experiment data/configs, logs, and
  checkpoint layout.

Analysis:
- The action target should be relative task-space deltas, not raw planner joint
  commands, to bridge cleanly into the existing DEXTRAH PPO controller. The
  first dataset should label approach-to-pregrasp and keep close/lift optional
  because close/lift may require contact-state and gripper semantics not present
  in all planner traces.

Next:
- Inspect DEXTRAH action/controller scaling and current package layout.
- Add converter/config/smoke modules, validate on a synthetic trajectory, then
  record final commit and remaining integration questions.

## 2026-06-11T11:49:04-07:00 - offline DP BC converter checkpoint

Goal:
- Add a bounded, official-Diffusion-Policy-compatible starting point for
  Franka cube BC warm-start from GraspGenX/cuRobo trajectories.

Hypothesis:
- Converting task-space waypoints to DEXTRAH normalized relative EE actions
  plus raw gripper commands is the least-mismatch action target for later RL.
- A compact low-dimensional observation schema is enough for initial BC
  validation, but it is not a direct PPO weight-initialization path because PPO
  currently consumes the full 72D environment observation.

Change:
- Added `dextrah_lab/offline_dp_bc/action_conversion.py` with NumPy versions of
  the Isaac Lab relative pose convention:
  - position delta in meters divided by `(0.060, 0.060, 0.045)`;
  - rotation delta as axis-angle from `q_target * inv(q_current)` divided by
    `(0.25, 0.25, 0.30)`;
  - gripper action `-1` closes and `+1` opens, matching DEXTRAH reward/control.
- Added `trajectory_conversion.py` to convert explicit task-space NPZ files or
  GraspGenX trajectory JSON files. JSON conversion uses explicit EE poses when
  present, or optional GraspGenX FK from `joint_position` plus the DEXTRAH
  `panda_hand` EE offset.
- Added `dp_dataset.py` with an NPZ-backed official Diffusion Policy
  `BaseLowdimDataset` adapter and a no-op lowdim runner for offline BC.
- Added `validate_dataset_smoke.py` for synthetic dataset shape/action replay
  validation.
- Added `config/franka_cube_lowdim_dp.yaml` using official
  `real-stanford/diffusion_policy` low-dimensional Hydra target conventions.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: pending
- push/pull: n/a local checkpoint
- changed_files:
  - `dextrah_lab/offline_dp_bc/__init__.py`
  - `dextrah_lab/offline_dp_bc/action_conversion.py`
  - `dextrah_lab/offline_dp_bc/trajectory_conversion.py`
  - `dextrah_lab/offline_dp_bc/dp_dataset.py`
  - `dextrah_lab/offline_dp_bc/validate_dataset_smoke.py`
  - `dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: n/a/local env

Command / Job:
- command: `python3 -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: syntax compile passed.
- key evidence: no py_compile errors.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --synthetic-output /tmp/franka_cube_dp_bc_synthetic_smoke.npz`
- job_id: n/a
- run_dir: /tmp
- logs: terminal
- artifacts:
  - `/tmp/franka_cube_dp_bc_synthetic_smoke.npz`
  - `/tmp/franka_cube_dp_bc_synthetic_smoke.npz.metadata.json`

Result:
- status: passed
- metrics/artifacts: sample obs shape `[8, 21]`, sample action shape `[8, 7]`,
  dataset steps `38`, episodes `2`, first real-step position replay error
  `0.0`.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.trajectory_conversion /tmp/franka_cube_dp_bc_taskspace_input.npz --output /tmp/franka_cube_dp_bc_converted_cli.npz --input-format npz --phase-set approach_pregrasp && PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset /tmp/franka_cube_dp_bc_converted_cli.npz`
- job_id: n/a
- run_dir: /tmp
- logs: terminal
- artifacts:
  - `/tmp/franka_cube_dp_bc_converted_cli.npz`
  - `/tmp/franka_cube_dp_bc_converted_cli.npz.metadata.json`

Result:
- status: passed
- metrics/artifacts: converted one episode, `12` steps, obs dim `21`, action
  dim `7`; smoke sample obs `[8, 21]`, action `[8, 7]`, replay error `0.0`.
- key evidence: printed `FRANKA_CUBE_DP_BC_CONVERTED` and
  `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: `PYTHONPATH=$PWD /home/lzha/code/graspgenx/.venv/bin/python - <<'PY' ... yaml.safe_load('dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml') ... PY`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: YAML parsed with `task_name=franka_cube_lowdim`, `obs_dim=21`, `action_dim=7`.
- key evidence: printed `yaml ok franka_cube_lowdim 21 7`.

Analysis:
- I chose approach-to-pregrasp as the default phase set. It avoids teaching
  contact and lift behavior before the planner-to-sim contact semantics are
  validated. The converter exposes `approach_grasp`, `full_pick_lift`, and
  explicit phase filters for later ablations.
- A Diffusion Policy checkpoint from this template should first be used through
  an evaluation/fine-tuning wrapper, or distilled into the PPO actor, because a
  diffusion denoising UNet cannot be loaded directly into the current rl_games
  Gaussian PPO network and the compact 21D BC observation is not the full 72D
  PPO observation.
- Official Diffusion Policy forward/training-step validation was not run
  locally because neither `diffusion_policy` nor `omegaconf` is installed in
  the local shell or GraspGenX venv. The config and dataset targets are written
  for the official repo environment.

Next:
- Commit this coherent checkpoint.
- Before any real BC run, generate or locate real Franka cube GraspGenX/cuRobo
  trajectories with explicit EE poses or provide GraspGenX FK inputs, then run
  the converter and an official Diffusion Policy one-step debug train in the
  official DP environment.

## 2026-06-11T11:50:48-07:00 - final handoff

Goal:
- Record final checkpoint state for Worker C handoff.

Hypothesis:
- The branch is ready for orchestrator review because source, config, local
  shape validation, and the worklog are committed, with no active local or
  cluster jobs.

Change:
- Source checkpoint committed.
- Updated this final handoff entry after commit so the worklog names the code
  implementation commit explicitly.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 589dd81c9f9691fcda3a3d4b9ad714d90dae4794
- implementation_commit: ca1bcae19a07b45d530860bfc12169ea3efc8ebd
- push/pull: not pushed; local agent branch checkpoint

## 2026-06-11T12:22:08-07:00 - real GraspGenX/cuRobo cube dataset plan

Goal:
- Move Worker C beyond geometric/debug demonstrations by generating real
  cuRobo-validated Franka cube task-space trajectories for official Diffusion
  Policy BC, or prove a precise external blocker.

Hypothesis:
- The existing GraspGenX `end2end` planner stack can be reused for DEXTRAH's
  60 mm cube if a DEXTRAH-owned scene wrapper writes a matching cube mesh,
  table/cube/robot config, and exports `trajectory.json` plus
  `plan_summary.json`.
- The safest first BC target remains approach-to-pregrasp. Close/lift will be
  exported in the raw cuRobo plan but kept out of the initial DP dataset until
  contact/lift semantics are inspected in DEXTRAH/Isaac.

Evidence before edits:
- No existing Franka cube cuRobo time-indexed trajectory dataset was found in
  local DEXTRAH/GraspGenX artifacts. Existing local `trajectory.json` artifacts
  are Franka star kitting, not cube.
- Worker A's cube artifact
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz`
  is a static grasp library, not a cuRobo trajectory dataset.
- Canonical local GraspGenX venv imports Torch/CUDA but lacks `curobo`.
- Isolated prior GraspGenX/cuRobo worktrees are viable for planning:
  - GraspGenX:
    `/home/lzha/code/.codex-worktrees/graspgenx/franka-ggx-curobo-local-20260610T234641Z-86074`
  - cuRobo:
    `/home/lzha/code/.codex-worktrees/curobo/franka-ggx-curobo-local-20260610T234641Z-86074`
  - Python:
    `/home/lzha/code/.codex-worktrees/graspgenx/franka-ggx-curobo-local-20260610T234641Z-86074/.venv/bin/python`
  - import check: Torch 2.6.0+cu124, CUDA available, cuRobo imports from the
    isolated cuRobo worktree.
- GraspGenX attempted to fetch `gripper_descriptions` during import and hit
  upstream LFS budget limits, but the local checkout already contains the
  `franka_panda` assets needed for this path.

Planned source edits:
- Add a DEXTRAH-owned
  `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py`, adapted
  from the existing Franka star GraspGenX/cuRobo script and GraspGenX's
  `validate_franka_cube_graspgenx_curobo.py`.
- Patch `dextrah_lab/offline_dp_bc/trajectory_conversion.py` to propagate
  `curobo_validated=true/false` and planner summary fields into converted DP
  dataset metadata. The converter should only mark a dataset as cuRobo
  validated when all source summaries say planning succeeded.
- Keep all generated artifacts under the external Worker C artifact root:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/`.

Planned validation:
- Run syntax/import checks for the new script and converter.
- Launch a bounded local planning smoke first: one or a few seeds, GraspGenX
  topdown/grasp-ranking enabled, capped planning attempts, no full BC/RL run.
- If real planning succeeds, convert successful `trajectory.json` files with
  `--phase-set approach_pregrasp`, validate shapes/metadata, run a tiny
  official `real-stanford/diffusion_policy` train with validation split, then
  run the existing checkpoint bridge smoke.
- If real planning is blocked by missing assets, dependency failures, or
  planner infeasibility, record the exact command/log/blocker and pivot to the
  next bridge milestone: an explicit DEXTRAH/Isaac eval wrapper for a geometric
  DP checkpoint, clearly marked non-curobo/geometric-only.

Version Control:
- branch: codex/franka-cube-diffusion-policy-bc
- starting_commit: c3c33fd0e6e2404200bce9091d7345981227a13a
- implementation_commit: pending
- push/pull: pending

## 2026-06-11T12:27:37-07:00 - real cuRobo planning smoke

Goal:
- Prove a real GraspGenX + cuRobo Franka cube trajectory can be generated for
  the DP BC path, separate from prior geometric/debug datasets.

Change:
- Added DEXTRAH-owned cube planner wrapper
  `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py`.
- Patched `dextrah_lab/offline_dp_bc/trajectory_conversion.py` to propagate
  per-source `plan_summary.json` fields and top-level `curobo_validated`.
- Fixed wrapper default yaw after debugging: DEXTRAH's
  `robot_yaw_wxyz=(0, 0, 0, 1)` is a 180 degree Z rotation in wxyz, while
  GraspGenX YAML uses xyzw. The wrapper now defaults to `--robot_yaw_deg 180`.

Command / Job:
- command: `PYTHONPATH=$DEX:$GGX:$GGX/end2end:$CU GRASPGENX_ROOT=$GGX GRASPGENX_CUROBO_DIR=$CU GRASPGENX_CHECKPOINT_DIR=$GGX/ext/graspgenx_checkpoints GRASPGENX_GRIPPER_CFG_DIR=$GGX/ext/gripper_descriptions CUDA_VISIBLE_DEVICES=0 $GGX/.venv/bin/python dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py --output_dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans --run_name cube_curobo_smoke_seed0_20260611_122546 --seed 0 --num_sample_points 1000 --num_grasps 64 --topk 32 --grasp_threshold 0.0 --grasp_planner topdown --moe_obb_density dense --max_plan_attempts 32 --rank_grasps_by_confidence`
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_smoke_seed0_20260611_122546`
- log: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_smoke_seed0_20260611_122546.log`

Result:
- status: failed, useful diagnostic
- key evidence: CUDA/checkpoints/GraspGenX/cuRobo all loaded; GraspGenX
  produced 32 topdown grasp candidates; cuRobo rejected every candidate with
  `Start or End state in collision` and `No grasp in goal set was reachable`.
- diagnosis: wrapper used `--robot_yaw_deg 0`, which points the GraspGenX
  Franka away from the negative-X DEXTRAH table. This mismatched Isaac's
  wxyz yaw convention.

Command / Job:
- command: same as above after wrapper yaw fix, run name
  `cube_curobo_smoke_seed0_yaw180_20260611_122709`
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_smoke_seed0_yaw180_20260611_122709`
- log: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_smoke_seed0_yaw180_20260611_122709.log`
- artifacts:
  - `trajectory.json`
  - `plan_summary.json`
  - `run_config.json`
  - `environment.json`

Result:
- status: passed
- metrics/artifacts: `curobo_validated=true`, 32 grasp candidates, selected
  grasp index `0`, confidence `0.7619073987007141`, plan segments
  `approach=62`, `grasp=42`, `lift=42`, exported trajectory frames `722`.
- key evidence: log printed `DEXTRAH_CUBE_GRASPGENX_CUROBO_PLAN_PASSED`.

Analysis:
- The real-planner blocker was not external; it was a wrapper convention bug.
- The raw plan includes close/lift, but the first DP conversion will continue
  to use `approach_pregrasp` for low-risk BC. Full pick/lift can be converted
  later once contact rollout behavior is inspected in DEXTRAH/Isaac.

Next:
- Generate a tiny multi-episode real cuRobo dataset using varied cube XY
  offsets inside DEXTRAH reset randomization.
- Convert successful `trajectory.json` files with real planner metadata,
  validate dataset shape/normalization, run official Diffusion Policy tiny
  train with validation split, and bridge-smoke the checkpoint.

## 2026-06-11T12:33:54-07:00 - real cuRobo DP BC tiny train + eval wrapper

Goal:
- Move from geometric/debug demonstrations to real GraspGenX + cuRobo
  trajectory demonstrations and prove official Diffusion Policy compatibility
  through a tiny train/validation run and checkpoint bridge smoke.

Change:
- Generated an 8-episode real cuRobo cube trajectory batch with varied cube XY
  offsets inside the DEXTRAH reset randomization range.
- Fixed converter phase expansion for sorted JSON `task_segments` by using
  GraspGenX pick-and-lift canonical phase order.
- Added `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`, a no-learning
  Isaac/DEXTRAH rollout wrapper that:
  - loads an official Diffusion Policy checkpoint;
  - extracts 21D lowdim observations from DEXTRAH's 72D PPO observations;
  - calls `predict_action_from_ppo_obs()`;
  - clips DEXTRAH 7D relative EE + gripper actions;
  - writes rollout metrics/video paths for inspection.

Official Diffusion Policy Source:
- source URL: `https://github.com/real-stanford/diffusion_policy`
- project page: `https://diffusion-policy.cs.columbia.edu/`
- local checkout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
- commit: `5ba07ac6661db573af695b419a7947ecb704690f`

Command / Job:
- command: 8-run local batch using
  `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py`
  with `--grasp_planner topdown --num_grasps 64 --topk 32
  --max_plan_attempts 32 --rank_grasps_by_confidence`.
- batch: `cube_curobo_batch_20260611_122807`
- success list:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_batch_20260611_122807_success_trajectories.txt`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_batch_20260611_122807_seed{0..7}.log`
- run dirs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_batch_20260611_122807_seed{0..7}`

Result:
- status: passed
- metrics/artifacts: 8/8 trajectories passed with `curobo_validated=true`.
  Seed 0 selected grasp confidence `0.7619073987007141` with segments
  `approach=62`, `grasp=42`, `lift=42`; seeds 1-7 each used
  `approach=42`, `grasp=42`, `lift=42`.
- key evidence: every per-seed log printed
  `DEXTRAH_CUBE_GRASPGENX_CUROBO_PLAN_PASSED`.

Command / Job:
- command: `PYTHONPATH=$DEX:$GGX:$GGX/end2end:$CU $GGX/.venv/bin/python -m dextrah_lab.offline_dp_bc.trajectory_conversion <8 trajectory.json files> --output $ART/datasets/franka_cube_curobo_lowdim_cube_curobo_batch_20260611_122807_approach_pregrasp.npz --input-format json --phase-set approach_pregrasp --graspgenx-root $GGX --robot-config $ART/curobo_plans/cube_curobo_batch_20260611_122807_seed0/configs/franka_panda_dextrah_cube.yaml`
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_cube_curobo_batch_20260611_122807_approach_pregrasp.npz`
- metadata:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_cube_curobo_batch_20260611_122807_approach_pregrasp.npz.metadata.json`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_batch_20260611_122807_conversion_rerun.log`
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_batch_20260611_122807_dataset_smoke_rerun.log`

Result:
- status: passed
- metrics/artifacts: `num_episodes=8`, `num_steps=836`, `obs_dim=21`,
  `action_dim=7`, top-level `curobo_validated=true`, all source flags true.
  Selected approach-to-pregrasp frames per source:
  `[122, 102, 102, 102, 102, 102, 102, 102]`.
- smoke: `FRANKA_CUBE_DP_BC_SMOKE_PASSED`, sample obs `[8, 21]`, sample action
  `[8, 7]`, first-step position replay error `0.0`.

Command / Job:
- command: `PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp task.dataset_path=$DATASET task.dataset.val_ratio=0.25 training.device=cpu training.max_train_steps=2 training.max_val_steps=1 training.num_epochs=1 policy.num_inference_steps=2 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir=$OUT`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_123104_curobo_batch`
- log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo_batch_debug_train.log`
- artifacts:
  - `.hydra/config.yaml`
  - `logs.json.txt`
  - `train.log`
  - `checkpoints/latest.ckpt`
  - `checkpoints/epoch=0000-test_mean_score=0.000.ckpt`

Result:
- status: passed
- metrics/artifacts: official model constructed with `1.662478e+07`
  parameters. Final logged row:
  `train_loss=1.186620056629181`, `val_loss=1.0896008014678955`,
  `train_action_mse_error=0.6653574705123901`, `test/mean_score=0.0`,
  `global_step=1`. Checkpoints are present, about 254 MB each.

Command / Job:
- command: `PYTHONPATH=$DP:$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint $OUT/checkpoints/latest.ckpt --dataset $DATASET --device cpu --batch-size 2 --num-inference-steps 2`
- log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo_batch_checkpoint_smoke.log`

Result:
- status: passed
- metrics/artifacts: loaded official
  `TrainDiffusionUnetLowdimWorkspace` / `DiffusionUnetLowdimPolicy`, direct
  action shape `[2, 8, 7]`, PPO bridge action shape `[2, 7]`, PPO obs shape
  `[2, 72]`, dataset episodes `8`, dataset steps `836`, finite bridge
  actions. Action extrema were close to the clipped controller range; eval
  wrapper clips before stepping DEXTRAH.

Command / Job:
- command: `TERM=xterm PYTHONPATH=$DEX /home/lzha/code/IsaacLab-v2.2.1/isaaclab.sh -p $DEX/dextrah_lab/rl_games/eval_franka_cube_dp_policy.py --help`
- log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/dp_policy_eval_help_isaaclab_blocker.log`

Result:
- status: externally blocked locally
- blocker evidence: command exited `1` with
  `python: command not found` and
  `Unable to find any Python executable at path: '/home/lzha/code/IsaacLab-v2.2.1/_isaac_sim/python.sh'`.
- local inspection: no local `/isaac-sim/python.sh` was found and `srun` is not
  installed on this host. Existing DEXTRAH cluster scripts run Isaac through
  `/isaac-sim/python.sh` inside the cluster Isaac container.

Analysis:
- Real cuRobo data generation is now viable. The first failure was caused by
  a DEXTRAH/GraspGenX quaternion convention mismatch, not missing assets.
- The current BC dataset intentionally imitates approach-to-pregrasp only.
  Close/lift are present in the real exported trajectories and can be included
  later, but contact rollout should be inspected in Isaac before training DP
  on close/lift.
- The DP checkpoint remains a teacher/eval artifact, not an rl_games PPO
  initialization. PPO fine-tuning should either run through the eval wrapper as
  a no-learning teacher rollout, or distill DP teacher actions into a PPO actor
  that consumes the full 72D observation.

Version Control:
- branch: codex/franka-cube-diffusion-policy-bc
- source_checkpoint_commit: b62f3b2
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- changed_files:
  - `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py`
  - `dextrah_lab/offline_dp_bc/trajectory_conversion.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- changed_files: owned worklog final entry only since implementation commit
- remote_commit/status: n/a/local env

Command / Job:
- command: `git status --short --branch`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: after implementation commit, only the owned worklog final
  entry was modified.
- key evidence: no active local process, Slurm job, or remote submitter was
  launched by this worker.

Analysis:
- The useful next validation is not more local synthetic testing; it is running
  the official Diffusion Policy debug train against a real converted Franka
  cube dataset in an environment where `real-stanford/diffusion_policy` is
  installed.

Next:
- Commit this log-only handoff entry.
- Orchestrator can inspect/cherry-pick the branch; no Worker C job monitoring
  remains.

## 2026-06-11T12:02:11-07:00 - official DP validation plan

Goal:
- Move beyond synthetic DEXTRAH-only smoke tests and validate the Franka cube
  BC path against the official `real-stanford/diffusion_policy` implementation.

Hypothesis:
- The DEXTRAH lowdim dataset adapter and config will need small compatibility
  fixes once exercised inside the official workspace, especially around Hydra
  config loading, runner assertions, normalizer imports, and output/log paths.
- A local isolated official-DP venv can reuse the existing GraspGenX venv's
  Torch/NumPy packages via a venv-local `.pth` bridge, avoiding a full CUDA
  PyTorch reinstall while keeping official-DP dependencies outside DEXTRAH.

Change:
- Planned external-only setup:
  - clone official repo to `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`;
  - create official-DP validation venv under
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv`;
  - keep generated debug dataset/logs under
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts`.
- Planned DEXTRAH edits only if official validation exposes issues in our
  adapter/config or if an eval-wrapper/distillation stub is practical.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: a21857f58ce211cb67f3174e56bb49c5f8f64ae8
- implementation_commit: pending
- push/pull: will push branch after coherent checkpoint
- changed_files: worklog plan only so far
- remote_commit/status: n/a/local env

Command / Job:
- command: `git clone https://github.com/real-stanford/diffusion_policy ...; uv venv ...; uv pip install ...; tiny official-DP debug train/forward`
- job_id: n/a
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart`
- logs: planned under `artifacts/logs`
- artifacts: planned converted dataset, resolved config, official-DP debug output

Result:
- status: in_progress
- metrics/artifacts: none yet
- key evidence: n/a

Analysis:
- No full BC training will be launched. Stop condition for this attempt is
  official config/dataset/model construction plus one tiny train/forward step,
  or a precise external dependency blocker with command output and paths.

Next:
- Materialize official repo and environment, generate a tiny converted dataset,
  run official workspace, patch DEXTRAH if the failure is ours, then commit and
  push.

## 2026-06-11T12:14:08-07:00 - official DP one-step train and bridge smoke

Goal:
- Validate Worker C's Franka cube lowdim BC path with the official
  `real-stanford/diffusion_policy` code, then make the PPO handoff concrete
  enough for eval-wrapper/distillation follow-up.

Hypothesis:
- Official DP compatibility is now mostly a dependency/config issue, not a
  dataset-shape issue. The generated checkpoint still cannot initialize
  rl_games PPO directly because the official DP policy is a denoising UNet over
  action sequences with a compact 21D observation history, while rl_games PPO is
  a 72D-observation Gaussian actor-critic MLP.

Change:
- Materialized the official repository externally, not vendored into DEXTRAH:
  - source URL: `https://github.com/real-stanford/diffusion_policy`
  - project page verified: `https://diffusion-policy.cs.columbia.edu/`
  - local path:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
  - official commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- Built an isolated official-DP validation venv at
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv`, with
  the GraspGenX venv Torch packages exposed through a venv-local `.pth`.
  Relevant resolved versions:
  `torch==2.6.0`, `numpy==1.26.4`, `hydra-core==1.3.2`,
  `omegaconf==2.3.0`, `diffusers==0.11.1`,
  `huggingface-hub==0.10.1`, `transformers==4.25.1`,
  `wandb==0.13.3`, `zarr==2.18.3`, `numcodecs==0.12.1`,
  `pandas==2.2.2`, `einops==0.4.1`, `dill==0.3.5.1`.
- Added `dextrah_lab/offline_dp_bc/ppo_bridge.py`:
  - extracts the 21D DP lowdim observation from the Franka cube 72D PPO
    observation using the env's actual observation concatenation;
  - keeps the DP `n_obs_steps` history for inference;
  - provides a lowdim-to-PPO embedding helper for bridge tests and future
    distillation data generation;
  - exposes `predict_action_from_ppo_obs()` for eval wrappers, explicitly not
    for direct PPO weight initialization.
- Added `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py` to
  load an official DP checkpoint and query it through the PPO bridge.
- Updated `dextrah_lab/offline_dp_bc/__init__.py` exports.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: a21857f58ce211cb67f3174e56bb49c5f8f64ae8
- implementation_commit: 59e562501f84224808b589f45839dbdbb124c398
- push/pull: branch push boundary; final pushed commit reported in the
  orchestrator/final response
- changed_files:
  - `dextrah_lab/offline_dp_bc/__init__.py`
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: pending

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: all Worker C offline BC modules compile.
- key evidence: command exited 0.

Command / Job:
- command: bridge round-trip smoke with NumPy and torch PPO observations
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: extracted lowdim shape `(3, 21)`, embedded PPO shape
  `(3, 72)`, history shape `(3, 2, 21)`.
- key evidence: printed `ppo_bridge ok ...`.

Command / Job:
- command: official import smoke for
  `diffusion_policy.workspace.train_diffusion_unet_lowdim_workspace`,
  `diffusion_policy.dataset.base_dataset`, DEXTRAH adapter, and checkpoint
  smoke script.
- job_id: n/a
- run_dir: local worktree with external official repo on `PYTHONPATH`
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: official workspace and DEXTRAH adapter import together.
- key evidence: printed `official imports ok`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.trajectory_conversion "$art/datasets/franka_cube_taskspace_debug_input.npz" --output "$art/datasets/franka_cube_lowdim_debug.npz" --input-format npz --phase-set approach_pregrasp`
- job_id: n/a
- run_dir: `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/converter_debug_current.log`
- artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_lowdim_debug.npz`

Result:
- status: passed
- metrics/artifacts: one approach/pregrasp debug episode, `24` steps,
  `obs_dim=21`, `action_dim=7`.
- key evidence: printed `FRANKA_CUBE_DP_BC_CONVERTED`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$art/datasets/franka_cube_lowdim_debug.npz"`
- job_id: n/a
- run_dir: external artifacts directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/dextrah_dataset_smoke_current.log`
- artifacts: converted dataset plus metadata JSON

Result:
- status: passed
- metrics/artifacts: `sample_obs_shape=[8, 21]`,
  `sample_action_shape=[8, 7]`, `num_train_samples=24`,
  first-step position replay error `0.0`, official DP import visible.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: official one-step debug train from the external official repo:
  `"$venv/bin/python" train.py --config-dir "$dex/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$art/datasets/franka_cube_lowdim_debug.npz" training.device=cpu training.max_train_steps=1 training.max_val_steps=1 training.num_epochs=1 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir="$out"`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_120953_current`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_debug_train_current.log`
  and the run's `logs.json.txt`
- artifacts:
  `.hydra/config.yaml`, `.hydra/overrides.yaml`, `train.log`,
  `checkpoints/latest.ckpt`,
  `checkpoints/epoch=0000-test_mean_score=0.000.ckpt`, W&B offline run.

Result:
- status: passed
- metrics/artifacts: official UNet parameters `1.662478e+07`; one training
  step logged `train_loss=1.1275699138641357`, `lr=1e-6`,
  `test/mean_score=0.0`, `train_action_mse_error=0.7768738865852356`.
  Two checkpoints were produced, each about `254M`.
- key evidence: official W&B run finished successfully; `logs.json.txt`
  contains two JSON records for global step `0`.

Command / Job:
- command: checkpoint bridge smoke:
  `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint "$run_dir/checkpoints/latest.ckpt" --dataset "$art/datasets/franka_cube_lowdim_debug.npz" --device cpu --batch-size 2 --num-inference-steps 2`
- job_id: n/a
- run_dir: external official-DP debug run
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_checkpoint_smoke_current.log`
- artifacts: uses `latest.ckpt`; no new training artifact

Result:
- status: passed
- metrics/artifacts: loaded `TrainDiffusionUnetLowdimWorkspace` and
  `DiffusionUnetLowdimPolicy`, lowdim sequence shape `[2, 2, 21]`,
  PPO observation shape `[2, 72]`, direct official action shape `[2, 8, 7]`,
  bridge first-action shape `[2, 7]`, all finite.
- key evidence: printed `FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED`.

Command / Job:
- command: dataset/checkpoint metadata probe
- job_id: n/a
- run_dir: external artifacts directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_metadata_current.log`
- artifacts: none beyond logs

Result:
- status: passed after adjusting the probe to official `LinearNormalizer`
  state-dict APIs.
- metrics/artifacts: dataset `obs_shape=[24, 21]`, `action_shape=[24, 7]`,
  `train_samples=24`, `val_samples=0` because this bounded debug dataset has
  one episode; checkpoint state contains both `model` and `ema_model`;
  normalizer has 12 parameter/stat keys for `obs` and `action`.
- key evidence: printed `FRANKA_CUBE_DP_BC_METADATA`.

Analysis:
- Official implementation validation is now achieved for config parsing,
  dataset construction, normalizer construction, model construction, one
  bounded train step, checkpoint save, checkpoint load, and bridge inference.
- The one-episode debug dataset is intentionally too small to assess BC
  quality and produces no validation split. That is acceptable for this
  milestone but not for BC evaluation. Next dataset generation should use
  multiple real GraspGenX/cuRobo rollouts with varied cube poses and include
  a held-out split.
- The debug action range is nearly constant because the synthetic waypoints are
  a straight approach segment. A meaningful BC smoke should include multiple
  approach directions and, once contact semantics are validated, separate
  approach-only vs approach+close+lift ablations.
- PPO bridge decision: do not direct-load DP weights into rl_games. Use either
  (1) a DP eval wrapper that extracts the 21D lowdim observation from the 72D
  env observation and sends the first denoised action to the existing 7D IK
  controller, or (2) distill DP actions into the 72D-observation PPO actor by
  collecting `obs72 -> action7` targets from the DP teacher. PPO fine-tuning
  should then initialize from the distilled actor or run RL with the DP wrapper
  as a scripted teacher/curriculum, not by loading the DP checkpoint into
  rl_games.
- No local/cluster full BC or RL training was launched. No active jobs remain.

Next:
- Commit and push this coherent official-validation checkpoint.
- Next Worker C loop should generate a multi-episode converted dataset from
  real GraspGenX/cuRobo traces, run a tiny official DP train with a validation
  split, then choose between DP eval-wrapper rollouts in Isaac Lab or
  distillation into the rl_games PPO actor.

## 2026-06-11T12:22:40-07:00 - grasp-library geometric BC smoke plan

Goal:
- Continue the BC warm-start loop after official-DP validation by creating a
  multi-episode dataset that exercises validation splits and varied cube poses.

Hypothesis:
- No real Franka cube cuRobo trajectory artifacts are currently present in the
  local Worker C workspace, Worker B trajectory-tracking worktree, or shared
  local results. Worker A's cube GraspGenX artifact is a grasp library, not a
  time-indexed trajectory. A clearly labeled geometric approach generator from
  that grasp library can still test official DP mechanics on varied
  multi-episode data while preserving the cuRobo-data blocker.

Change:
- Planned new script:
  `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`.
- The script will read a GraspGenX cube grasp-library NPZ with object-local
  grasps, sample cube poses from the current Franka cube reset range, transform
  grasp/tool poses into the DEXTRAH EE frame using the `panda_hand` plus
  `0.1034 m` EE offset convention, interpolate approach-to-pregrasp waypoints,
  and write the same lowdim dataset schema used by official DP.
- This is intentionally marked `curobo_validated=false`; it is a bridge smoke,
  not final offline BC data.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 1fad16fa6b4b9eacbe1edf67ca8153ff399694ad
- implementation_commit: pending
- push/pull: pending after validation
- changed_files: owned worklog plan only so far
- remote_commit/status: origin/codex/franka-cube-diffusion-policy-bc currently at
  `1fad16fa6b4b9eacbe1edf67ca8153ff399694ad`

Command / Job:
- command: locate artifacts under `/home/lzha/code/local_results`,
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-traj-tracking`, and
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset`
- job_id: n/a
- run_dir: local filesystems
- logs: terminal
- artifacts: discovered Worker A grasp library
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-ggx-pregrasp-reset/local_results/franka_cube_grasp_prior/franka_cube_ggx_grasps_smoke.npz`

Result:
- status: in_progress
- metrics/artifacts: grasp library has `32` object-frame grasps,
  `gripper_name=franka_panda`, `tool_frame=panda_hand`, `cube_size_m=0.06`,
  and `grasp_to_tool_transform`; no cube cuRobo trajectory JSON/NPZ found.

Analysis:
- This generator should not be used to claim cuRobo trajectory BC success.
  It is useful for testing official-DP training and PPO bridge mechanics with
  multiple episodes before real cube planner traces are available.

Next:
- Implement the generator, run DEXTRAH dataset smoke and a bounded official DP
  debug train with a validation split, inspect logs/metadata/checkpoint, then
  commit and push if coherent.

## 2026-06-11T12:30:21-07:00 - grasp-library geometric BC smoke validation

Goal:
- Exercise official Diffusion Policy on a multi-episode Franka cube dataset
  with validation samples while keeping the data provenance honest.

Hypothesis:
- A geometric GraspGenX grasp-library approach dataset should validate the
  official DP training/validation path and PPO bridge under varied cube poses,
  but it should still be treated as `curobo_validated=false` until real cube
  planner traces are generated or located.

Change:
- Added `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`.
- The generator:
  - reads GraspGenX cube grasp-library fields `grasps_object`, `confidence`,
    `grasp_to_tool_transform`, `tool_frame`, and `gripper_name`;
  - samples cube positions from the current Franka cube reset center and
    `0.08 m` XY randomization range;
  - computes `T_world_ee` as
    `T_world_object @ T_object_grasp @ T_grasp_tool @ T_panda_hand_ee_offset`;
  - interpolates open-gripper approach-to-pregrasp waypoints;
  - verifies pregrasp EE distance is farther from the cube than exact grasp EE
    distance for every episode;
  - writes the same lowdim NPZ/metadata schema as the cuRobo converter.
- No Worker A/B task files were edited.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- base_commit: 1fad16fa6b4b9eacbe1edf67ca8153ff399694ad
- implementation_commit: d61beb2df3760d0fc86e08e789427cf82a65990e
- push/pull: branch push boundary; final pushed commit reported in the
  orchestrator/final response
- changed_files:
  - `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: origin branch currently at
  `1fad16fa6b4b9eacbe1edf67ca8153ff399694ad`

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m py_compile dextrah_lab/offline_dp_bc/*.py`
- job_id: n/a
- run_dir: local worktree
- logs: terminal
- artifacts: none

Result:
- status: passed
- metrics/artifacts: offline BC modules compile with the new generator.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.generate_grasp_library_demos --grasp-library "$library" --output "$art/datasets/franka_cube_grasp_library_geometric_debug.npz" --num-episodes 16 --steps 24 --hold-steps 4 --top-k 16 --seed 123`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/grasp_library_geometric_generate.log`
- artifacts:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_grasp_library_geometric_debug.npz`
  and `.metadata.json`

Result:
- status: passed
- metrics/artifacts: `16` episodes, `448` steps, `obs_dim=21`,
  `action_dim=7`, `curobo_validated=false`, all generated pregrasps farther
  from the cube than their exact grasp poses.
- key evidence: printed `FRANKA_CUBE_DP_BC_GRASP_LIBRARY_DEMOS`.

Command / Job:
- command: `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$art/datasets/franka_cube_grasp_library_geometric_debug.npz"`
- job_id: n/a
- run_dir: external artifact directory
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/grasp_library_geometric_dataset_smoke.log`
- artifacts: generated dataset and metadata

Result:
- status: passed
- metrics/artifacts: sample obs `[8, 21]`, action `[8, 7]`,
  `num_train_samples=252`, first-step position replay error `0.0`, official
  DP import visible.
- key evidence: printed `FRANKA_CUBE_DP_BC_SMOKE_PASSED`.

Command / Job:
- command: official tiny train with validation split:
  `"$venv/bin/python" train.py --config-dir "$dex/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$art/datasets/franka_cube_grasp_library_geometric_debug.npz" task.dataset.val_ratio=0.25 training.device=cpu training.max_train_steps=2 training.max_val_steps=1 training.num_epochs=1 policy.num_inference_steps=2 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir="$out"`
- job_id: n/a
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_121600_grasp_library`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_grasp_library_debug_train.log`
  and run `logs.json.txt`
- artifacts:
  `.hydra/config.yaml`, `.hydra/overrides.yaml`, `train.log`,
  `checkpoints/latest.ckpt`,
  `checkpoints/epoch=0000-test_mean_score=0.000.ckpt`, W&B offline run.

Result:
- status: passed
- metrics/artifacts: official UNet parameters `1.662478e+07`; logged two
  train steps and one validation batch. Final record:
  `train_loss=1.143653690814972`, `val_loss=1.0723308324813843`,
  `train_action_mse_error=0.6667237877845764`, `test/mean_score=0.0`,
  `lr=2e-6`. Two checkpoints were produced, each about `254M`.
- key evidence: `logs.json.txt` contains train step records for global steps
  `0` and `1`, plus the validation/sample metrics record.

Command / Job:
- command: checkpoint bridge smoke on the grasp-library debug checkpoint:
  `PYTHONPATH="$dp:$dex" "$venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint "$run_dir/checkpoints/latest.ckpt" --dataset "$art/datasets/franka_cube_grasp_library_geometric_debug.npz" --device cpu --batch-size 2 --num-inference-steps 2`
- job_id: n/a
- run_dir: external official-DP debug run
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_grasp_library_checkpoint_smoke.log`
- artifacts: uses generated official DP checkpoint

Result:
- status: passed
- metrics/artifacts: loaded official workspace/policy, dataset episodes `16`,
  dataset steps `448`, lowdim sequence `[2, 2, 21]`, PPO obs `[2, 72]`,
  direct action `[2, 8, 7]`, bridge first-action `[2, 7]`, finite outputs.
- key evidence: printed `FRANKA_CUBE_DP_BC_CHECKPOINT_SMOKE_PASSED`.

Analysis:
- The official DP path is now validated on both one-episode synthetic data and
  a multi-episode GraspGenX grasp-library geometric dataset with a validation
  split.
- This still does not close the real-data requirement: no local Franka cube
  cuRobo trajectory JSON/NPZ was found. The geometric dataset should be used
  only for mechanics/debugging and not for claims about cuRobo-planned BC.
- The action ranges are bounded and mostly approach/open-gripper:
  min approximately `[-0.066, -0.00008, -0.126, 0, 0, 0, 1]`,
  max approximately `[0.00036, 0, 0, 0, 0, 0, 1]`.
- Because the generated trajectories keep orientation and gripper state mostly
  fixed, they are not sufficient for final BC quality. The next real dataset
  must include true planner approach diversity and later close/lift ablations.

Next:
- Commit and push this generator/validation checkpoint.
- Next Worker C loop should either generate true Franka cube cuRobo trajectories
  from the grasp library or build the Isaac eval wrapper around
  `predict_action_from_ppo_obs()` for no-learning policy rollout inspection.

## 2026-06-11T12:38:20-07:00 - l401 DP eval-wrapper smoke plan

Goal:
- Validate the implemented
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py` no-learning wrapper in
  a bounded DEXTRAH/Isaac cluster smoke instead of stopping at the local
  IsaacLab Python blocker.

Hypothesis:
- The official Diffusion Policy checkpoint trained from 8 real
  GraspGenX/cuRobo-planned cube demonstrations can be loaded inside the
  DEXTRAH Isaac container if the official `real-stanford/diffusion_policy`
  checkout and minimal DP dependencies are mounted separately from DEXTRAH.
- A 1-env, 16-step rollout is enough to validate mechanics:
  official checkpoint load, 72D PPO observation to 21D DP bridge, 7D relative
  EE + gripper action emission, env stepping, and metrics serialization. It is
  not a BC-quality or final-training claim.

Change:
- Planned new cluster launcher:
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.
- The launcher will:
  - mount the Worker C remote worktree at `/code`;
  - mount official Diffusion Policy at `/official_dp`;
  - optionally add an isolated official-DP dependency target from
    `/envs/franka-cube-dp-bc-warmstart-official-dp/site`;
  - run `eval_franka_cube_dp_policy.py` with `NUM_ENVS=1`,
    `NUM_STEPS=16`, `NUM_INFERENCE_STEPS=2`, and no video by default;
  - fail if logs contain Python error patterns or `metrics.json` is missing,
    incomplete, non-finite, or reports an unclosed env.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart
- worklog: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md
- branch: codex/franka-cube-diffusion-policy-bc
- implementation_commit: pending
- local_head_before_edits: 30b305ecf65630b03a9fa8a07574f6bf228eac70
- official_dp_source: `https://github.com/real-stanford/diffusion_policy`
- official_dp_commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- source_checkpoint_for_eval:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_123104_curobo_batch/checkpoints/latest.ckpt`
- source_dataset_for_eval_context:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_cube_curobo_batch_20260611_122807_approach_pregrasp.npz`
- changed_files:
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- planned deploy: push branch, update remote worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  to the exact commit.
- planned artifact copy: rsync only untracked/generated artifacts, including
  the 254M official DP checkpoint, to
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/franka-cube-dp-bc-warmstart/`.
- planned run:
  `sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` with
  `CODE_NFS` set to the Worker C remote worktree and `CHECKPOINT` set to the
  copied official DP checkpoint under `/results/dp_bc/.../latest.ckpt`.

Result:
- status: first submission blocked before scheduling
- job_id: n/a
- logs: terminal only
- artifacts: none
- key evidence: l401 rejected the inherited DEXTRAH partition list with
  `sbatch: error: invalid partition specified: batch_singlenode`. Current
  `sinfo` reports GPU partitions `batch` and `batch_long`; the DP launcher is
  being patched to use `batch` only.

Analysis:
- The 8 real cuRobo demonstrations are sufficient only for mechanics
  validation and bridge debugging. They should not be described as a final BC
  dataset or final warm-start quality evidence.
- If the first cluster eval fails, expected debug targets are official-DP
  dependency visibility, checkpoint module import paths, Isaac env creation,
  or bridge/action shape assumptions. Patch DEXTRAH-owned code/launcher issues
  and relaunch before claiming success.

Next:
- Deploy code and artifacts to l401, run an import/eval smoke, inspect logs and
  `metrics.json`, then update this worklog with exact job IDs and results.

## 2026-06-11T12:46:10-07:00 - l401 DP eval first failure / protobuf patch

Goal:
- Debug the first bounded l401 eval smoke for the official-DP Franka cube
  no-learning wrapper.

Hypothesis:
- The first eval failed before metrics because the official DP workspace import
  reached `wandb`, and the Isaac Sim Python environment has a `wandb`/protobuf
  compatibility issue. The known protobuf workaround should let official DP
  imports proceed without installing a separate dependency site.

Change:
- Patched `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` to export
  `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` inside the container.
- Patched `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py` with
  `DP_EVAL_STAGE` markers around startup, official DP import, checkpoint load,
  policy device transfer, gym creation, reset, rollout, and env close.
- Added explicit top-level exception printing before `simulation_app.close()`.

Version Control:
- implementation_commit: pending
- changed_files:
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- eval command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_123104_curobo_batch/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo8_smoke_20260611_124302 NUM_ENVS=1 NUM_STEPS=16 NUM_INFERENCE_STEPS=2 PRINT_INTERVAL=4 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- eval job_id: `1027699`
- eval log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027699.out`
- eval run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo8_smoke_20260611_124302`

Result:
- status: failed as expected by launcher guard
- sacct: `FAILED`, exit `1:0`, elapsed `00:00:36`
- metrics/artifacts: no `metrics.json` was produced.
- key evidence: log reached Isaac startup and DEXTRAH task config parsing,
  then the launcher emitted `Missing DP eval metrics JSON`. No traceback was
  present in the eval log, which motivated stage-marker instrumentation.

Command / Job:
- import/checkpoint diagnostic: one-off Slurm job using the same Isaac
  container, Worker C `/code`, official DP `/official_dp`, copied checkpoint,
  and `/isaac-sim/python.sh` without creating an Isaac env.
- import job_id: `1027701`
- import log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/dp_ckpt_import_smoke_1027701.out`

Result:
- status: failed before official DP workspace construction
- key evidence: Python `3.11.13`, Torch `2.7.0+cu128`, official DP import path
  visible, then `wandb` import failed with protobuf:
  `TypeError: Descriptors cannot be created directly`.
- diagnosis: the container's installed `wandb` generated protos are
  incompatible with the active protobuf runtime. The error message recommends
  either protobuf `3.20.x` or setting
  `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`; the launcher now uses the
  latter to avoid mutating the shared Isaac environment.

Analysis:
- This is not a data or policy-shape failure yet. The official DP checkpoint
  was not constructed in the cluster container before the protobuf blocker.
- The real cuRobo dataset remains an 8-demo mechanics dataset only. This loop
  is validating bridge/eval mechanics, not final BC performance.

Next:
- Commit/push the protobuf/stage-marker patch, update the remote worktree via
  Git bundle, and relaunch the 1-env/16-step eval smoke.

## 2026-06-11T12:55:32-07:00 - l401 DP dependency site + eval summary fix

Goal:
- Continue the l401 eval-wrapper smoke until the official DP checkpoint can
  run through DEXTRAH/Isaac and serialize metrics.

Hypothesis:
- The eval path is mechanically sound after official-DP dependencies are
  isolated. The current failure is a wrapper bookkeeping bug: metrics are
  read from `task_env` after `gym_env.close()`, but Isaac Lab removes
  `task_env.scene` during close.

Change:
- Created isolated official-DP dependency target:
  `/lustre/fsw/portfolios/nvr/users/lzha/envs/franka-cube-dp-bc-warmstart-official-dp/site`.
- Installed only cluster-eval dependencies there, leaving shared Isaac env
  untouched:
  `dill==0.3.5.1`, `diffusers==0.11.1`,
  `huggingface-hub==0.10.1`, `einops==0.4.1`,
  `transformers==4.25.1`, `tokenizers==0.13.3`,
  `zarr==2.18.3`, `numcodecs==0.12.1`, `asciitree==0.3.3`,
  `fasteners==0.19`.
- Patched `eval_franka_cube_dp_policy.py` to snapshot final cube pose,
  gripper width, and `num_envs` before closing the Isaac env.

Version Control:
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- dependency install jobs:
  - `1027703`: installed `dill`, `diffusers`, `huggingface-hub`, `einops`;
    completed, exit `0:0`.
  - `1027706`: installed `transformers==4.25.1`; validation found container
    `tokenizers==0.21.4` incompatible; failed intentionally as diagnostic.
  - `1027708`: installed `tokenizers==0.13.3`; completed, exit `0:0`.
  - `1027710`: installed `zarr`, `numcodecs`, `asciitree`, `fasteners`;
    completed, exit `0:0`.
- checkpoint import/forward jobs:
  - `1027702`: protobuf workaround passed, failed on missing `dill`.
  - `1027705`: failed on container `transformers` vs pinned
    `huggingface-hub` mismatch.
  - `1027709`: failed on missing `zarr`.
  - `1027711`: passed official DP checkpoint forward:
    `TrainDiffusionUnetLowdimWorkspace`, `DiffusionUnetLowdimPolicy`,
    `n_obs_steps=2`, action shape `(1, 8, 7)`, finite `True`.

Command / Job:
- eval relaunch command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart OFFICIAL_DP_ENV_NAME=franka-cube-dp-bc-warmstart-official-dp CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_123104_curobo_batch/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo8_smoke2_20260611_125418 NUM_ENVS=1 NUM_STEPS=16 NUM_INFERENCE_STEPS=2 PRINT_INTERVAL=4 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- eval job_id: `1027712`
- eval log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027712.out`
- eval run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo8_smoke2_20260611_125418`

Result:
- status: failed after successful 16-step rollout
- key evidence:
  - official DP checkpoint loaded and moved to CUDA;
  - DEXTRAH env created and reset with PPO obs shape `[1, 72]`;
  - rollout printed steps `1`, `4`, `8`, `12`, and `16`;
  - action bounds were finite but heavily clipped to `[-1, 1]`, expected for
    a tiny 8-demo debug checkpoint;
  - no success/lift claim: final printed `success_rate=0.0`,
    `cube_lift_height=0.0`;
  - metrics writing failed with
    `AttributeError: 'DextrahFrankaCubeGraspEnv' object has no attribute 'scene'`
    while reading `task_env.num_envs` after env close.

Analysis:
- This failure is a DEXTRAH wrapper summary-order bug, not an official DP
  checkpoint or environment stepping failure. The next relaunch should pass if
  metrics are snapshotted before close.
- The 8 real cuRobo demonstrations remain mechanics-only; the clipped actions
  and no-lift result are expected and should not be presented as final BC
  performance.

Next:
- Commit/push the summary snapshot fix, update remote worktree, and relaunch
  the bounded 1-env/16-step eval once more.

## 2026-06-11T12:57:38-07:00 - l401 DP eval-wrapper smoke passed

Goal:
- Close the bounded DEXTRAH/Isaac cluster mechanics validation for
  `eval_franka_cube_dp_policy.py` using the official DP checkpoint trained
  from 8 real cuRobo demonstrations.

Hypothesis:
- With official-DP dependencies isolated and final metrics snapshotted before
  env close, the no-learning wrapper should serialize a valid 16-step rollout
  metrics artifact.

Change:
- No new source changes after commit `df98650f3d8f7c6c9fb172171f4a50172c2c38a1`.
- Remote l401 Worker C worktree was updated to exactly that commit via git
  bundle because l401 cannot fetch GitHub over SSH.

Version Control:
- implementation_commit: df98650f3d8f7c6c9fb172171f4a50172c2c38a1
- branch: codex/franka-cube-diffusion-policy-bc
- official_dp_source: `https://github.com/real-stanford/diffusion_policy`
- official_dp_commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- official_dp_cluster_path:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy`
- official_dp_dependency_site:
  `/lustre/fsw/portfolios/nvr/users/lzha/envs/franka-cube-dp-bc-warmstart-official-dp/site`

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy OFFICIAL_DP_ENV_NAME=franka-cube-dp-bc-warmstart-official-dp CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_123104_curobo_batch/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo8_smoke3_20260611_125635 NUM_ENVS=1 NUM_STEPS=16 NUM_INFERENCE_STEPS=2 PRINT_INTERVAL=4 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1027713`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027713.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo8_smoke3_20260611_125635`
- metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo8_smoke3_20260611_125635/metrics.json`

Result:
- status: passed
- sacct: `COMPLETED`, exit `0:0`, elapsed `00:00:42`,
  step max RSS about `22101932K`.
- launcher validation: printed `DP eval metrics passed` and
  `DP Evaluation Done`.
- metrics summary:
  - `official_workspace=TrainDiffusionUnetLowdimWorkspace`
  - `policy_class=DiffusionUnetLowdimPolicy`
  - `ppo_bridge=predict_action_from_ppo_obs`
  - `num_envs=1`
  - `steps_completed=16`
  - `env_closed=true`
  - `reward_mean=1.3180006965994835`
  - `reward_final=1.308260202407837`
  - `final_success_rate=0.0`
  - `window_success_rate=0.0`
  - `final_gripper_width=0.04295472055673599`
  - `action_min=[-1.0, -1.0, -0.9044985771179199, -1.0, -1.0, -1.0, -1.0]`
  - `action_max=[1.0, 1.0, 1.0, 1.0, 1.0, 0.9629597067832947, 1.0]`
- artifact inspection:
  - `metrics.json` has 16 step records.
  - grep for Python error patterns in the Slurm log found none.
  - no video was requested for this smoke.

Analysis:
- The eval-wrapper mechanics milestone is complete: official DP checkpoint
  load, 72D PPO observation to 21D lowdim bridge, 7D relative EE+gripper action
  output, Isaac env stepping, metrics serialization, and launcher validation
  all passed on l401.
- The behavior is not successful manipulation. The policy is a tiny debug
  checkpoint from 8 approach-only real cuRobo demos, actions saturate at clip
  bounds, and cube lift/success remain zero. This is expected and should be
  reported only as mechanics validation.
- The next practical step is to scale the real cuRobo demo dataset and run a
  bounded official-DP BC pretrain with validation, still approach-only at
  first. After action saturation improves, add close/lift ablation and then
  route through the same eval wrapper or a PPO distillation bridge.

Next:
- Commit/push this worklog checkpoint.
- Start the next bounded scale-up: expand real cuRobo demonstrations beyond 8
  episodes and run a small official-DP validation pretrain, not final BC/RL.

## 2026-06-11T12:59:02-07:00 - 32-demo real cuRobo scale-up plan

Goal:
- Move beyond the 8-demo mechanics dataset by generating a bounded 32-demo
  real GraspGenX/cuRobo approach-to-pregrasp dataset and running a small
  official-DP validation pretrain.

Hypothesis:
- Increasing from 8 to 32 real cuRobo-validated episodes with varied cube XY
  positions should reduce the most extreme debug/checkpoint artifacts, while
  still remaining a mechanics/early-BC scale-up rather than a final BC claim.
- Approach-to-pregrasp remains the right first expansion because the l401
  eval smoke showed no lift and saturated actions from an approach-only
  8-demo checkpoint. Close/lift should be added as a separate ablation after
  approach behavior and action normalization look sane.

Change:
- No source edits planned for generation/conversion unless a DEXTRAH bug is
  found.
- Planned new artifacts under
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/`:
  - real cuRobo plan batch `cube_curobo_scale32_<timestamp>_seed{8..31}`;
  - converted NPZ using existing seed `0..7` trajectories plus new successful
    seed `8..31` trajectories;
  - official DP debug-pretrain run with validation split.

Command / Job:
- generation command: local RTX 6000 Ada, sequential seeds `8..31`, script
  `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py`, same
  GraspGenX/cuRobo worktrees as the 8-demo batch:
  - GraspGenX:
    `/home/lzha/code/.codex-worktrees/graspgenx/franka-ggx-curobo-local-20260610T234641Z-86074`
  - cuRobo:
    `/home/lzha/code/.codex-worktrees/curobo/franka-ggx-curobo-local-20260610T234641Z-86074`
  - Python:
    `/home/lzha/code/.codex-worktrees/graspgenx/franka-ggx-curobo-local-20260610T234641Z-86074/.venv/bin/python`
- planned planner args:
  `--num_sample_points 1000 --num_grasps 64 --topk 32 --grasp_threshold 0.0 --grasp_planner topdown --moe_obb_density dense --max_plan_attempts 32 --rank_grasps_by_confidence`.
- conversion: `trajectory_conversion --input-format json --phase-set approach_pregrasp`
  with the DEXTRAH/GraspGenX FK robot config.
- official-DP pretrain: external official repo
  `real-stanford/diffusion_policy@5ba07ac6661db573af695b419a7947ecb704690f`,
  local venv, validation split `0.25`, bounded `max_train_steps` around
  `100`, no final/full BC or RL training.

Result:
- status: planned
- logs/artifacts: pending

Analysis:
- Acceptance criterion for data scale-up is not task success. It is:
  successful cuRobo plan summaries, converted dataset shape/provenance,
  official-DP training/validation logs without NaNs, finite bridge actions,
  and a clearer decision about whether action clipping/normalization needs
  adjustment before any larger pretrain or PPO handoff.

Next:
- Launch local generation, monitor success/failure logs, then convert and run
  the bounded official-DP validation pretrain if enough new trajectories pass.

## 2026-06-11T13:06:18-07:00 - 32-demo cuRobo generation completed

Goal:
- Produce enough real GraspGenX/cuRobo-validated Franka cube trajectories for
  the next bounded official Diffusion Policy BC pretrain.

Hypothesis:
- Sequential local planning for seeds `8..31` should provide a small but
  materially better mechanics dataset than the original 8-demo checkpoint,
  while keeping generation inspectable and recoverable seed by seed.

Change:
- No source code changed. Generated new untracked real cuRobo plan artifacts.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `7ae5d242832ee42f453166e9cd8a14a687b66569`
- implementation_commit: pending for this worklog/data-loop update
- push/pull: pending
- changed_files: worklog only so far

Command / Job:
- command: local sequential planner loop over seeds `8..31` using
  `dextrah_lab/scene_scripts/plan_franka_cube_graspgenx_curobo.py` with
  `--num_sample_points 1000 --num_grasps 64 --topk 32 --grasp_threshold 0.0 --grasp_planner topdown --moe_obb_density dense --max_plan_attempts 32 --rank_grasps_by_confidence`.
- job_id: local session `77761`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_seed{8..31}`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_scale32_20260611_125957_seed{8..31}.log`
- artifacts:
  - success list:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_success_trajectories.txt`
  - failed list:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_failed_seeds.txt`
  - positions:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_positions.txt`

Result:
- status: passed
- metrics/artifacts:
  - planner result: `PLAN_BATCH_DONE batch=cube_curobo_scale32_20260611_125957 success=24 fail=0`
  - success list length: `24`
  - failed list length: `0`
  - representative seed `31`: `curobo_validated=true`,
    `plan_segments={"approach":42,"grasp":42,"lift":42}`,
    `trajectory.json` has `702` frames.

Analysis:
- The dataset remains small and should be described as mechanics/early-BC
  validation only. The `curobo_validated=true` flag is backed by the planner
  success marker in each seed log rather than being synthesized by the
  converter.
- The next conversion should combine the original 8 successful real cuRobo
  trajectories with these 24 new trajectories, keeping the output name and
  metadata distinct from all geometric/debug datasets.

Next:
- Convert the combined 32 real cuRobo trajectories to low-dimensional
  approach-to-pregrasp DP demonstrations, run dataset-shape validation, then
  run a bounded official-DP pretrain with a validation split.

## 2026-06-11T13:07:42-07:00 - 32-demo conversion and bounded official-DP pretrain launch plan

Goal:
- Validate the official Diffusion Policy BC path on a combined 32-demo real
  cuRobo dataset, then inspect losses/checkpoints/action bridge behavior.

Hypothesis:
- A 32-demo approach/pregrasp dataset with all sources cuRobo-validated should
  run through the official `TrainDiffusionUnetLowdimWorkspace` with validation
  enabled and produce a finite debug checkpoint. This is still not a final BC
  claim because the dataset omits close/lift and remains small.

Change:
- Converted combined 8+24 real cuRobo trajectories to:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_approach_pregrasp.npz`

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: pending
- changed_files: worklog only

Command / Job:
- conversion command:
  `PYTHONPATH="$DEX:$GGX:$GGX/end2end:$CU" GRASPGENX_ROOT="$GGX" "$GGX/.venv/bin/python" -m dextrah_lab.offline_dp_bc.trajectory_conversion <32 trajectory.json files> --output "$DATASET" --input-format json --phase-set approach_pregrasp --graspgenx-root "$GGX" --robot-config "$ROBOT_CONFIG"`
- conversion log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_scale32_20260611_125957_conversion.log`
- dataset smoke command:
  `PYTHONPATH="$DP:$DEX" "$VENV/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$DATASET"`
- dataset smoke log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_scale32_20260611_125957_dataset_smoke.log`
- planned official-DP pretrain command:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=100 training.max_val_steps=4 training.num_epochs=5 policy.num_inference_steps=2 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_130742_curobo32_scale`

Result:
- conversion: passed with `num_episodes=32`, `num_steps=3284`,
  `obs_dim=21`, `action_dim=7`.
- dataset smoke: passed with `official_diffusion_policy_imported=true`,
  train samples `1958`, sample shapes `(8,21)` and `(8,7)`, and position
  replay error `0.0`.
- metadata:
  - dataset-level `curobo_validated=true`
  - source-level cuRobo validation true for all 32 trajectories
  - action bounds are finite and within the DEXTRAH normalized range:
    min `[-0.04198,-0.16348,-0.000001,-0.07269,-0.09689,-0.16468,1.0]`,
    max `[0.13624,0.04179,0.20882,0.09963,0.000001,0.25439,1.0]`

Analysis:
- This approach/pregrasp dataset has stable numeric ranges and should avoid
  the extreme clipping seen during the 8-demo cluster eval except where the
  learned policy extrapolates badly from too little data.
- Gripper action is constant open (`1.0`) by design for approach/pregrasp, so
  this checkpoint cannot learn close/lift. Close/lift remains a required next
  ablation before any manipulation-success claim.

Next:
- Run the bounded official-DP debug pretrain, inspect `logs.json.txt`,
  checkpoints, and bridge-smoke action ranges, then decide whether to launch
  a second tiny l401 eval with the scaled checkpoint.

## 2026-06-11T13:09:17-07:00 - 32-demo official-DP overfit/debug run plan

Goal:
- Determine whether the action saturation seen in the 32-demo 5-epoch
  checkpoint is mainly undertraining/debug-inference noise by running a still
  bounded official Diffusion Policy overfit/debug pretrain on the same real
  cuRobo dataset.

Hypothesis:
- The first 5-epoch run produced finite, decreasing losses but only `405`
  optimizer steps and bridge samples still touched `[-1,1]` clip bounds.
  A roughly 2k-step run should reduce sampling noise if the lowdim official-DP
  config and dataset are coherent.

Change:
- No source edits planned.
- Training scale increases only within the same 32 real cuRobo approach-only
  dataset. This is not a final BC run and still cannot learn close/lift.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `7ae5d242832ee42f453166e9cd8a14a687b66569`
- implementation_commit: pending worklog update

Command / Job:
- command:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=100 training.max_val_steps=4 training.num_epochs=25 policy.num_inference_steps=25 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`
- note: official `train_diffusion_unet_lowdim_workspace.py` applies
  `training.max_train_steps` per epoch (`batch_idx >= max_train_steps-1`),
  not globally. With 32 demos the dataloader has `81` batches, so this launch
  is expected to run about `25 * 81 = 2025` optimizer/log steps.
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_130917_curobo32_overfit2k`
- planned log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_overfit2k_train.log`

Result:
- status: pending

Analysis:
- If bridge actions remain saturated after this bounded overfit run, the next
  patch should be on the BC representation/training setup rather than another
  simulator eval: likely action normalization, deterministic DDIM inference,
  reduced output clip impact, or close/lift data balance.

Next:
- Launch and monitor the official-DP overfit/debug run, then inspect
  `logs.json.txt`, checkpoint files, and bridge action ranges at realistic
  inference-step counts.

## 2026-06-11T13:11:10-07:00 - 32-demo official-DP train inspection

Goal:
- Inspect the 32-demo official-DP checkpoints and decide whether the scaled
  checkpoint is sane enough for a tiny l401 Isaac eval wrapper smoke.

Command / Job:
- first debug run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_130742_curobo32_scale`
- first debug train log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_scale_train.log`
- overfit/debug run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_130917_curobo32_overfit2k`
- overfit/debug train log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_overfit2k_train.log`
- checkpoint smoke logs:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_scale_checkpoint_smoke_25step.log`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_overfit2k_checkpoint_smoke_25step.log`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_overfit2k_checkpoint_smoke_100step.log`

Result:
- first 5-epoch debug run:
  - completed with `405` JSON log rows, `global_step=404`.
  - `train_loss` decreased to `0.06738`; `val_loss` to `0.05896`.
  - `train_action_mse_error=0.63745`.
  - `latest.ckpt` written, size about `266 MB`.
  - bridge smoke at 25 denoising steps still sampled pose actions at clip
    bounds.
- 25-epoch overfit/debug run:
  - completed with `2025` JSON log rows, `global_step=2024`.
  - `train_loss` decreased to `0.00821`; `val_loss=0.00871`.
  - `train_action_mse_error=0.29439`.
  - `latest.ckpt` written, size about `266 MB`.
  - bridge smoke at 25 denoising steps still touched clip bounds in some pose
    dimensions.
  - bridge smoke at 100 denoising steps produced small pose actions:
    min `[-0.04952,-0.04517,0.01290,-0.02120,-0.03273,-0.03319,0.98674]`,
    max `[-0.00841,-0.01031,0.09045,0.00534,-0.00904,0.03201,1.00001]`.

Analysis:
- The official-DP mechanics now validate on a real 32-demo cuRobo dataset:
  official config parsing, official workspace construction/training,
  validation split, checkpoints, and PPO observation bridge all run.
- Inference-step count matters. The fast 2-step/25-step debug settings are too
  noisy for simulator policy rollout, while 100 denoising steps matches the
  100-step train scheduler and gives action ranges consistent with the
  demonstration deltas.
- This remains approach/pregrasp only. The constant open gripper action and no
  close/lift data mean the next Isaac smoke should be interpreted as rollout
  wiring and approach behavior only, not manipulation success.

Next:
- Copy the 32-demo overfit/debug `latest.ckpt` to l401 results storage and run
  a tiny `eval_franka_cube_dp_policy.py` cluster smoke with
  `NUM_INFERENCE_STEPS=100`, `NUM_ENVS=1`, and a short horizon. Inspect logs
  and metrics before any further scale-up.

## 2026-06-11T13:17:20-07:00 - full pick/lift dataset plan

Goal:
- Move beyond the approach-only BC checkpoint by creating a close/lift-capable
  official Diffusion Policy dataset from the same 32 real cuRobo-validated
  trajectories, then run cheap local validation before any l401 eval.

Hypothesis:
- The existing real GraspGenX/cuRobo trajectories contain all phases needed
  for a first full-pick BC mechanics dataset:
  `go_to_pre_grasp_pose`, `hold_at_pre_grasp`,
  `go_from_pre_grasp_to_grasp_pose`, `hold_at_grasp`, `close_fingers`,
  `hold_after_close`, `lift_object`, and `hold_after_lift`.
- Converting `phase_set=full_pick_lift` should produce a 7D DEXTRAH
  relative-EE plus gripper dataset where the gripper action is no longer
  constant open. This gives the DP checkpoint a plausible close/lift behavior
  target for later Isaac eval and PPO distillation.

Change:
- No source edits planned initially. Use existing converter support for
  `full_pick_lift`.
- Supersede the previous immediate l401 eval next-step for the approach-only
  checkpoint. A cluster eval is only useful after a close/lift-capable
  checkpoint has sane local action ranges.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `20b45767b2f3434bd0645e718365dc652192f27d`
- implementation_commit: pending

Command / Job:
- conversion command:
  `PYTHONPATH="$DEX:$GGX:$GGX/end2end:$CU" GRASPGENX_ROOT="$GGX" "$GGX/.venv/bin/python" -m dextrah_lab.offline_dp_bc.trajectory_conversion <32 trajectory.json files> --output "$DATASET" --input-format json --phase-set full_pick_lift --graspgenx-root "$GGX" --robot-config "$ROBOT_CONFIG"`
- planned dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift.npz`
- planned smoke:
  `PYTHONPATH="$DP:$DEX" "$VENV/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset "$DATASET"`
- planned official-DP debug train:
  local official `real-stanford/diffusion_policy@5ba07ac6661db573af695b419a7947ecb704690f`,
  validation split `0.25`, small bounded run first, then a bounded overfit
  run only if the data shape and action stats are sane.

Result:
- status: pending

Analysis:
- This is still not a final BC or RL claim: the trajectories are planned
  task-space/FK demonstrations and not Isaac closed-loop successes.
- Important checks before simulator eval:
  - dataset-level and source-level `curobo_validated=true`;
  - gripper action min below zero and max near open;
  - no non-finite values;
  - loss curves finite/decreasing with validation;
  - bridge action ranges at 100 denoising steps are plausible, especially the
    gripper action showing close commands after the policy conditions on close
    states.

Next:
- Convert the full-pick/lift dataset, inspect metadata/action ranges, run the
  official-DP dataset smoke, then launch a bounded local official-DP train if
  the dataset is numerically sane.

## 2026-06-11T13:18:45-07:00 - full pick/lift conversion and train launch plan

Goal:
- Validate a close/lift-capable real cuRobo dataset through official Diffusion
  Policy training, without launching full BC/RL training.

Hypothesis:
- The same 32 real cuRobo trajectories are enough to prove mechanics for a
  close/lift-capable BC checkpoint if the full-pick/lift conversion yields
  finite observation/action tensors and a non-constant gripper target.

Change:
- Converted full-pick/lift dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift.npz`

Command / Job:
- conversion log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_scale32_20260611_125957_full_pick_lift_conversion.log`
- dataset smoke log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/cube_curobo_scale32_20260611_125957_full_pick_lift_dataset_smoke.log`
- planned official-DP train command:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=100 training.max_val_steps=4 training.num_epochs=5 policy.num_inference_steps=100 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_131845_curobo32_full_pick_lift_debug`

Result:
- conversion: passed with `num_episodes=32`, `num_steps=22484`,
  `obs_dim=21`, `action_dim=7`.
- dataset smoke: passed with `official_diffusion_policy_imported=true`,
  train samples `13358`, sample shapes `(8,21)` and `(8,7)`, and position
  replay error `0.0`.
- metadata/stats:
  - dataset-level `curobo_validated=true`
  - all 32 sources have `curobo_validated=true`
  - selected phases include all 8 pick/lift phases
  - gripper action min/max: `-1.0` / `1.0`
  - close-command fraction: `0.5764`
  - observation gripper width min/max: `0.0` / `0.08`
  - pose action bounds remain inside normalized DEXTRAH limits:
    min `[-0.04198,-0.16348,-0.05103,-0.07269,-0.09689,-0.16468]`,
    max `[0.13624,0.04179,0.20882,0.09963,0.00084,0.25439]`

Analysis:
- This dataset can train close/lift mechanics, unlike the approach-only
  checkpoint. It still does not prove Isaac closed-loop success because the
  object pose in the demonstration is planned/recorded rather than generated
  by closed-loop policy rollouts.
- `phase_ids` are saved for audit but not currently part of the DP observation.
  The checkpoint must infer progress from EE pose, cube pose, goal delta,
  gripper width, and the two-step history. If the policy averages incompatible
  hold/close/lift actions, the next representation patch should add a compact
  phase/progress feature or split approach and grasp/lift policies.

Next:
- Run the bounded official-DP debug train, inspect losses/checkpoint, then run
  bridge smoke at `100` denoising steps against both early/open and
  closed/lift dataset windows.

## 2026-06-11T13:21:05-07:00 - full pick/lift checkpoint smoke inspection

Goal:
- Prove the close/lift-capable dataset can train through official Diffusion
  Policy and that the resulting checkpoint produces plausible bridge actions
  for open, closed, and lifted closed states.

Change:
- Extended `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`
  with `--row-selector` and `--warm-history-from-dataset` so checkpoint smokes
  can query representative full-pick/lift dataset regions instead of only the
  first approach rows.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `20b45767b2f3434bd0645e718365dc652192f27d`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- train run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_131845_curobo32_full_pick_lift_debug`
- train log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_debug_train.log`
- syntax check:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`
- checkpoint smokes:
  - first/open:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_first_warm_100step.log`
  - gripper-closed:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_closed_warm_100step.log`
  - lift-high:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_debug_checkpoint_smoke_lift_high_warm_100step.log`

Result:
- official-DP train: passed
  - `logs.json.txt` rows: `505`
  - final `global_step=503`
  - `train_loss=0.04288`
  - `val_loss=0.03742`
  - `train_action_mse_error=0.01642`
  - finite losses, decreasing validation curve, `latest.ckpt` written
    at about `266 MB`.
- py_compile: passed.
- first/open 100-step bridge smoke:
  - selected gripper width: `[0.08,0.08,0.08,0.08]`
  - bridge gripper range: `[0.35893,1.00001]`
  - pose actions remain small.
- gripper-closed 100-step bridge smoke:
  - selected gripper width: `[0.0,0.0,0.0,0.0]`
  - bridge gripper range: `[-0.96083,-0.25979]`
  - pose actions remain small.
- lift-high 100-step bridge smoke:
  - selected EE z: about `1.01115`
  - selected gripper width: `[0.0,0.0,0.0,0.0]`
  - bridge gripper range: `[-1.00001,-0.51134]`
  - pose actions remain small.

Analysis:
- This is the first close/lift-capable DP BC checkpoint on the branch with
  official implementation validation and state-dependent gripper behavior.
- The checkpoint is still small-data and planned-trajectory based, so it is
  appropriate for a bounded Isaac eval smoke, not a manipulation-performance
  claim.
- Because bridge action ranges are now sane at `100` denoising steps, the next
  l401 eval should use `NUM_INFERENCE_STEPS=100`. A shorter diffusion schedule
  is known to produce noisy clipped actions on these checkpoints.

Next:
- Commit and push the helper/worklog patch.
- Deploy the exact commit to the agent-owned l401 worktree, copy the full
  pick/lift checkpoint as an untracked artifact, and launch a tiny Isaac eval
  with `NUM_ENVS=1`, short horizon, and `NUM_INFERENCE_STEPS=100`.

## 2026-06-11T13:15:58-07:00 - full pick/lift l401 eval launch plan

Goal:
- Validate that the full-pick/lift official-DP checkpoint can load through the
  DEXTRAH Isaac eval wrapper and step a tiny Franka cube environment with sane
  action ranges.

Hypothesis:
- The local bridge smokes show the checkpoint is action-range sane at
  `100` denoising steps, so a tiny l401 eval should now be useful mechanics
  evidence. Success still means eval-wrapper mechanics and plausible
  approach/close/lift commands, not final manipulation performance.

Change:
- Source commit to deploy:
  `8a96fd5acea097539d5b5dd5bdf149bba39f5c49`
- Checkpoint artifact to copy:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_131845_curobo32_full_pick_lift_debug/checkpoints/latest.ckpt`

Command / Job:
- remote code:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_131845_curobo32_full_pick_lift_debug/latest.ckpt`
- planned run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558`
- planned command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy OFFICIAL_DP_ENV_NAME=franka-cube-dp-bc-warmstart-official-dp CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_131845_curobo32_full_pick_lift_debug/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558 NUM_ENVS=1 NUM_STEPS=64 NUM_INFERENCE_STEPS=100 PRINT_INTERVAL=8 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_<job_id>.out`
- expected metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558/metrics.json`

Result:
- status: pending

Analysis:
- This eval should be launched only after the remote source tree is updated to
  the exact commit and the checkpoint is present at the expected path.
- Pass criteria: Slurm exit 0, wrapper prints metrics validation, metrics JSON
  has `env_closed=true`, `steps_completed>=64`, finite action min/max, and no
  Python error patterns in the log. Reward/success are inspected but are not
  expected to prove task success on this tiny planned-demo checkpoint.

Next:
- Deploy source/checkpoint to l401, submit the job, monitor scheduler/logs,
  inspect `metrics.json`, patch/relaunch if the wrapper fails.

## 2026-06-11T13:21:50-07:00 - full pick/lift l401 eval smoke result and chunk-bridge plan

Goal:
- Inspect the full pick/lift checkpoint in DEXTRAH/Isaac and identify the next
  bridge patch needed for a useful BC warm-start path.

Hypothesis:
- The full pick/lift checkpoint should load and step in Isaac with finite
  actions. If it fails to make task progress, the most likely bridge issue is
  that the wrapper executes only the first action of each 8-action DP output
  and replans every simulator step, rather than executing an action chunk as
  official Diffusion Policy is designed to do.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- local_branch: `codex/franka-cube-diffusion-policy-bc`
- local_source_commit_deployed: `8a96fd5acea097539d5b5dd5bdf149bba39f5c49`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status: detached at
  `8a96fd5acea097539d5b5dd5bdf149bba39f5c49`; clean after transient Git
  bundle removal.
- deploy note: l401 GitHub fetch failed with `Permission denied (publickey)`,
  so the source commit was deployed via a Git bundle requiring base commit
  `589dd81c9f9691fcda3a3d4b9ad714d90dae4794`.

Command / Job:
- checkpoint copied to:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_131845_curobo32_full_pick_lift_debug/latest.ckpt`
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy OFFICIAL_DP_ENV_NAME=franka-cube-dp-bc-warmstart-official-dp CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_131845_curobo32_full_pick_lift_debug/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558 NUM_ENVS=1 NUM_STEPS=64 NUM_INFERENCE_STEPS=100 PRINT_INTERVAL=8 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1027722`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027722.out`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558`
- metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_20260611_131558/metrics.json`

Result:
- status: passed mechanics, failed task progress
- sacct: `COMPLETED`, exit `0:0`, elapsed `00:01:13`, step max RSS about
  `22394056K`.
- wrapper printed `DP eval metrics passed` and
  `FRANKA_CUBE_DP_POLICY_EVAL_DONE`.
- metrics summary:
  - `steps_completed=64`
  - `env_closed=true`
  - `reward_mean=1.3106193002313375`
  - `reward_final=1.264480471611023`
  - `final_success_rate=0.0`
  - `window_success_rate=0.0`
  - `action_min=[-0.20807,-0.35009,-0.05984,-0.16531,-0.31083,-0.26626,-0.30297]`
  - `action_max=[0.37037,0.19806,0.39653,0.27571,0.28798,0.22835,1.0]`
  - gripper width decreased from about `0.0796` to final `0.0491`,
    min `0.04516` at step `56`.
  - `cube_lift_height.max=0.0`.
  - final `ee_to_cube_dist=0.26818`,
    `finger_center_to_cube_dist=0.26017`.

Analysis:
- The cluster eval validates the full-pick checkpoint load path, official-DP
  policy inference, PPO-observation bridge, DEXTRAH 7D action stepping, metric
  writing, and environment shutdown.
- It does not show useful manipulation behavior yet. The policy starts with
  plausible open-gripper approach actions and eventually emits close commands
  by step 48, but the hand drifts away from the cube and never lifts.
- The next bridge patch should execute DP action chunks. The official lowdim
  policy is configured with `n_action_steps=8`; repeatedly throwing away
  seven predicted actions may prevent phase progress and amplify sampling
  jitter.

Next:
- Add an optional action-chunk execution mode to the PPO bridge/eval wrapper:
  default remains first-action replanning for compatibility, while
  `--action_chunk_steps 8` queues the predicted action sequence for execution.
- Run local syntax/checkpoint smokes, commit/push, deploy, and relaunch a
  tiny l401 eval with `ACTION_CHUNK_STEPS=8` if the local checks pass.

## 2026-06-11T13:25:40-07:00 - action chunk bridge patch validation

Goal:
- Make the DEXTRAH eval wrapper closer to official Diffusion Policy rollout
  mechanics by optionally executing DP action chunks instead of only the first
  predicted action at every simulator step.

Hypothesis:
- Chunk execution should preserve phase progression better for the full
  pick/lift checkpoint. The previous first-action eval only partially closed
  the gripper and drifted away from the cube.

Change:
- `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - added `predict_action_sequence_from_ppo_obs()`;
  - preserved `predict_action_from_ppo_obs()` as the first-action wrapper.
- `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - added `--action_chunk_steps`;
  - added action-queue execution for predicted DP action sequences;
  - clears the queue on env reset.
- `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - added `ACTION_CHUNK_STEPS` env var, preamble logging, and CLI forwarding.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `8a96fd5acea097539d5b5dd5bdf149bba39f5c49`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- syntax:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py && bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- preserved first-action checkpoint smoke:
  `validate_official_checkpoint_smoke --row-selector lift_high --warm-history-from-dataset --num-inference-steps 100`
- sequence-shape smoke:
  local official-DP checkpoint load plus
  `predict_action_sequence_from_ppo_obs()` on two open dataset rows.

Result:
- syntax checks: passed.
- preserved first-action smoke: passed with the same lift-high closed gripper
  action range as before, about `[-1.00001,-0.51134]`.
- sequence-shape smoke at 4 denoising steps: returned finite `(2,8,7)` but
  clipped/noisy actions as expected for too few denoising steps.
- sequence-shape smoke at 100 denoising steps: returned finite `(2,8,7)` with
  open-row action range:
  - full sequence min
    `[-0.00888,-0.11842,0.01279,-0.01949,-0.13708,0.01630,0.67468]`
  - full sequence max
    `[0.12398,-0.00496,0.20087,0.12081,-0.01849,0.20287,0.98030]`

Analysis:
- The patch is backward-compatible for first-action bridge smokes and exposes
  the action sequence needed for more faithful Diffusion Policy rollout.
- The chunked cluster smoke should use `ACTION_CHUNK_STEPS=8`,
  `NUM_INFERENCE_STEPS=100`, and the same full-pick/lift checkpoint as job
  `1027722`.

Next:
- Commit/push the chunk bridge patch, deploy the exact commit to l401 via Git,
  then run a bounded chunked eval smoke and compare gripper/finger/cube metrics
  against the first-action job.

## 2026-06-11T13:22:13-07:00 - chunked l401 eval launch plan

Goal:
- Test whether executing official DP action chunks improves the full-pick/lift
  checkpoint rollout compared with first-action replanning job `1027722`.

Hypothesis:
- With `ACTION_CHUNK_STEPS=8`, the wrapper will follow the policy's learned
  action horizon instead of discarding seven predicted actions every step.
  This should improve phase progression or at least clarify whether the
  remaining failure is data/training rather than bridge mechanics.

Version Control:
- source_commit_to_deploy:
  `52bcc43c19253205ee37a5d375e0afaad82d8df7`
- branch: `codex/franka-cube-diffusion-policy-bc`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`

Command / Job:
- run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213`
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy OFFICIAL_DP_ENV_NAME=franka-cube-dp-bc-warmstart-official-dp CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_131845_curobo32_full_pick_lift_debug/latest.ckpt RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213 NUM_ENVS=1 NUM_STEPS=64 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=8 PRINT_INTERVAL=8 CAPTURE_VIDEO=False sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- expected metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213/metrics.json`

Result:
- status: pending

Analysis:
- Pass criteria remain mechanics: Slurm exit `0`, wrapper metrics validation,
  `steps_completed=64`, `env_closed=true`, finite action ranges.
- Behavior comparison targets versus job `1027722`: gripper width, action
  gripper min, finger-center distance, EE-to-cube distance, and cube lift
  height. Success is not expected yet, but chunk execution should not degrade
  stability.

Next:
- Deploy source commit `52bcc43` to l401, submit chunked eval, monitor logs,
  inspect metrics, and record the comparison.

## 2026-06-11T13:24:10-07:00 - chunked eval result and full-pick overfit plan

Goal:
- Compare chunked DP action execution against first-action replanning and pick
  the next development step.

Command / Job:
- source commit deployed:
  `52bcc43c19253205ee37a5d375e0afaad82d8df7`
- run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213`
- job_id: `1027725`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027725.out`
- metrics:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_chunk8_20260611_132213/metrics.json`

Result:
- status: passed mechanics, worse behavior than first-action replanning
- sacct: `COMPLETED`, exit `0:0`, elapsed `00:00:47`, step max RSS about
  `22304884K`.
- wrapper printed `DP eval metrics passed`.
- comparison against first-action job `1027722`:
  - first-action:
    - final gripper width `0.04912`, min width `0.04516` at step `56`
    - gripper action min `-0.30297`
    - final EE-to-cube distance `0.26818`
    - final finger-center-to-cube distance `0.26017`
    - cube lift max `0.0`, success `0.0`
  - chunk8:
    - final gripper width `0.07726`, min width `0.07096` at step `32`
    - gripper action min `0.50134`
    - final EE-to-cube distance `0.28375`
    - final finger-center-to-cube distance `0.27481`
    - cube lift max `0.0`, success `0.0`

Analysis:
- The action-chunk implementation is mechanically valid and useful to keep,
  but the current 32-demo full-pick checkpoint is not trained enough for
  rollout. Chunking preserves an open/approach sequence and never reaches close
  commands in 64 steps; first-action replanning closes partially but still
  drifts away and never lifts.
- This shifts the next bottleneck back to the BC checkpoint/dataset, not the
  eval wrapper. The full-pick checkpoint only saw about `503` optimizer/log
  steps, whereas the approach-only overfit needed about `2024` steps before
  local bridge actions became stable.

Next:
- Run a bounded local full-pick/lift official-DP overfit/debug pretrain:
  same 32 real cuRobo demos, validation split `0.25`, `num_epochs=25`,
  `max_train_steps=100` per epoch, `policy.num_inference_steps=100`,
  expected about `2500` optimizer/log steps.
- Inspect losses, checkpoint, first/open and closed/lift bridge smokes, then
  decide whether to relaunch l401 eval with first-action or chunked execution.

## 2026-06-11T13:28:20-07:00 - full-pick overfit checkpoint inspection and long chunk eval plan

Goal:
- Improve the full pick/lift BC checkpoint enough to justify another bounded
  DEXTRAH/Isaac smoke.

Hypothesis:
- The previous full-pick checkpoint was undertrained at about `503` optimizer
  steps. A bounded ~2.5k-step official-DP overfit/debug run should learn the
  close/lift parts of the planned trajectories more cleanly.

Command / Job:
- local train command:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=100 training.max_val_steps=4 training.num_epochs=25 policy.num_inference_steps=100 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_132410_curobo32_full_pick_lift_overfit2k`
- train log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_overfit2k_train.log`
- checkpoint smokes:
  - first/open:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_first_warm_100step.log`
  - gripper-closed:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_closed_warm_100step.log`
  - lift-high:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_overfit2k_checkpoint_smoke_lift_high_warm_100step.log`

Result:
- official-DP train: passed
  - `logs.json.txt` rows: `2525`
  - final `global_step=2523`
  - `train_loss=0.00913`
  - `val_loss=0.00968`
  - `train_action_mse_error=0.001124`
  - finite/decreasing loss curves, `latest.ckpt` written at about `266 MB`.
- first/open 100-step bridge smoke:
  - selected gripper width `[0.08,0.08,0.08,0.08]`
  - bridge gripper range `[0.93863,1.00001]`
  - small pose actions.
- gripper-closed 100-step bridge smoke:
  - selected gripper width `[0.0,0.0,0.0,0.0]`
  - bridge gripper range `[-0.96638,-0.85467]`
  - small pose actions.
- lift-high 100-step bridge smoke:
  - selected EE z about `1.01115`
  - selected gripper width `[0.0,0.0,0.0,0.0]`
  - bridge gripper range `[-0.99948,-0.93076]`
  - small pose actions.

Analysis:
- The overfit checkpoint now has the state-dependent open/close behavior that
  the 503-step checkpoint lacked.
- The previous 64-step l401 eval is too short to test full-pick behavior on
  the planned trajectory timescale. In the converted demonstrations, close
  starts after approach/hold/grasp/hold phases, roughly hundreds of frames into
  the episode, so a 64-step smoke mostly tests approach.
- The next bounded cluster eval should use the overfit checkpoint, `chunk8`,
  one env, no video, and a longer but still small horizon such as `360` steps
  to cover approach, close, and early lift.

Next:
- Commit/push this worklog boundary.
- Copy the overfit checkpoint to l401 results storage and run a single-env
  chunked eval with `NUM_STEPS=360`, `ACTION_CHUNK_STEPS=8`,
  `NUM_INFERENCE_STEPS=100`, then inspect metrics and compare close/lift
  progress.

## 2026-06-11T13:36:40-07:00 - inspectable artifact bundle plan

Goal:
- Produce an inspectable bundle for the Diffusion Policy BC warm-start path,
  including train curves, bridge/eval behavior plots, summary tables, the
  overfit2k rollout video, and a markdown report with analysis.

Hypothesis:
- The completed overfit2k chunk8 DEXTRAH eval will show whether the improved
  local official-DP close/lift behavior survives the 72D PPO-observation bridge
  inside Isaac. If it still fails, the metrics/video should isolate whether the
  failure is action range, gripper schedule, observation mismatch, or closed-loop
  drift.

Change:
- Add a scoped offline artifact-report script under `dextrah_lab/offline_dp_bc/`
  that reads existing official-DP logs, checkpoint-smoke logs, and fetched
  l401 eval metrics. The script will write generated artifacts under the
  external artifact namespace, not into git.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- worklog: `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `ce5940a459a632f6e1ce20b3155fd4ac94e99d62`
- implementation_commit: pending

Command / Job:
- completed l401 eval: job `1027727`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_video_20260611_132637`
- local fetched copy:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_video_20260611_132637`
- video:
  `videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`

Result:
- status: in progress
- scheduler evidence: `COMPLETED`, exit `0:0`, elapsed `00:01:29`
- video evidence: `1280x720`, `359` frames, `5.98s`, fetched locally.

Analysis:
- Initial metrics show the run completed mechanically but still failed the task:
  success `0`, cube lift `0`, final gripper width about `0.0798 m`, final
  EE-to-cube distance about `0.609 m`, and reward decayed from about `1.36` to
  `1.01`. This points to closed-loop drift and open-gripper behavior, not a
  simulator crash or missing checkpoint.

Next:
- Generate the artifact bundle, run `viz-open` on the most useful video/plot,
  update this worklog with paths and analysis, then continue with the next
  bounded diagnostic for why chunked overfit execution still drifts away.

## 2026-06-11T13:35:30-07:00 - inspectable artifact bundle and trace-hook checkpoint

Goal:
- Hand off inspectable artifacts for the DP BC warm-start path and continue the
  low-level debug loop with a bounded policy-call trace diagnostic.

Hypothesis:
- If the overfit2k checkpoint still stays open in Isaac while bridge smokes
  close on selected dataset states, the failure is likely due to live
  observation/history drift or bridge-channel mismatch. A per-policy-call trace
  should expose which 21D lowdim states the policy actually sees during eval.

Change:
- Added `dextrah_lab/offline_dp_bc/make_artifact_bundle.py` to generate report,
  plots, CSV/JSON summaries, and copy the fetched rollout video into a stable
  external bundle.
- Added disabled-by-default policy-call tracing to
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
- Added `DEBUG_POLICY_TRACE_MAX_CALLS`, `DEBUG_POLICY_TRACE_ENV_INDEX`, and
  optional `DEBUG_POLICY_TRACE_PATH` forwarding in
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `ce5940a459a632f6e1ce20b3155fd4ac94e99d62`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/make_artifact_bundle.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- fetched eval artifacts:
  `rsync -a l401:/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/<run>/ .../artifacts/cluster_evals/<run>/`
- artifact bundle command:
  `VENV=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv; "$VENV/bin/python" -m dextrah_lab.offline_dp_bc.make_artifact_bundle --output-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640`
- validation:
  - `python3 -m py_compile dextrah_lab/offline_dp_bc/make_artifact_bundle.py`
  - `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/make_artifact_bundle.py`
  - `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`

Result:
- status: artifact bundle passed; trace hook validated locally
- bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640`
- report:
  `.../report.md`
- train plots:
  - `plots/full_pick_train_val_loss_5epoch_vs_25epoch.png`
  - `plots/full_pick_train_action_mse_5epoch_vs_25epoch.png`
- bridge/eval plots:
  - `plots/bridge_gripper_action_ranges.png`
  - `plots/bridge_pose_action_ranges.png`
  - `plots/eval_behavior_metrics.png`
- summary tables:
  - `tables/train_summary.csv`
  - `tables/bridge_smokes_summary.csv`
  - `tables/eval_summary.csv`
  - `tables/eval_timeseries.csv`
  - `tables/artifact_manifest.json`
- video:
  `videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`
  (`1280x720`, `359` frames, `5.98s`)
- viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640/videos/franka-cube-dp-overfit2k-chunk8-step-0.mp4`
  - behavior plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dp_bc_warmstart_artifacts_20260611_133640/plots/eval_behavior_metrics.png`

Analysis:
- The artifact evidence is consistent:
  - 5-epoch full-pick first-action partially closes late but does not lift.
  - 5-epoch chunk8 stays mostly open.
  - overfit2k chunk8 uses the best local checkpoint but still stays open
    (`gripper_action_min=0.855`, gripper width final `0.0798 m`) and drifts
    away (`EE-to-cube distance 0.234 m -> 0.609 m`, reward final `1.010`).
  - local overfit2k bridge smokes prove the checkpoint can close for
    closed/lift dataset rows (`gripper action roughly -0.97` to `-0.85` for
    closed rows and `-1.00` to `-0.93` for lift-high rows).
- Therefore the current blocker is not official-DP model construction or
  checkpoint loading; it is live closed-loop observation/history mismatch,
  covariate shift, or a subtle PPO-observation channel mismatch.

Next:
- Commit/push the artifact generator and trace hook.
- Deploy the commit to the agent-owned l401 worktree and run a tiny traced
  no-video eval, e.g. `NUM_STEPS=96`, `ACTION_CHUNK_STEPS=8`,
  `DEBUG_POLICY_TRACE_MAX_CALLS=12`, then fetch `policy_trace.json` and compare
  live lowdim observations/action chunks against the converted dataset phases.

## 2026-06-11T13:38:15-07:00 - traced overfit2k chunk8 eval launch

Goal:
- Capture live policy-call lowdim observations and action chunks for the
  overfit2k chunk8 failure mode.

Hypothesis:
- The first dozen policy calls will show gripper-open action chunks and growing
  cube-minus-EE / distance features, confirming the policy remains in approach
  mode while drifting away from the demonstration manifold.

Version Control:
- implementation_commit: `fdb77c9dc967d1476361b4cb106190cec696e0a8`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`; deployed
  to l401 agent worktree via Git bundle because l401 GitHub SSH fetch is still
  unavailable.
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `fdb77c9dc967d1476361b4cb106190cec696e0a8`, detached clean.

Command / Job:
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_trace96_20260611_133812,NUM_ENVS=1,NUM_STEPS=96,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=8,DEBUG_POLICY_TRACE_MAX_CALLS=12,DEBUG_POLICY_TRACE_ENV_INDEX=0,PRINT_INTERVAL=24,CAPTURE_VIDEO=False,CHECKPOINT=/results/dp_bc/franka-cube-dp-bc-warmstart/checkpoints/run_20260611_132410_curobo32_full_pick_lift_overfit2k/latest.ckpt cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1027729`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_trace96_20260611_133812`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027729.out`
- expected artifacts:
  - `metrics.json`
  - `policy_trace.json`

Result:
- status: running/queued, monitoring pending.

Next:
- Poll job `1027729`, inspect logs and artifacts, fetch metrics/trace locally,
  then compare trace records against dataset phases before deciding the next
  patch or data augmentation step.

## 2026-06-11T13:49:30-07:00 - traced eval diagnosis and frame-fixed dataset

Goal:
- Analyze traced eval job `1027729`, resolve the open/drift failure mode, and
  create the next valid BC dataset boundary.

Hypothesis:
- If live lowdim observations stay nearest to early pregrasp frames and the
  predicted action chunks move away from the cube, the failure is not just
  undertraining; it is likely a mismatch between how trajectory labels are
  encoded and how the DEXTRAH Franka controller interprets actions.

Change:
- Added `dextrah_lab/offline_dp_bc/analyze_policy_trace.py` to compare traced
  live lowdim observations/action chunks against converted dataset phases.
- Fixed `dextrah_lab/offline_dp_bc/action_conversion.py` so task-space deltas
  are rotated from world/env frame into the Franka controller action frame
  before normalization. For the cube task this is the robot root yaw of 180 deg,
  represented as WXYZ quaternion `[0, 0, 0, 1]`.
- Added replay helpers that convert normalized action-frame commands back to
  world deltas for validation.
- Exposed `--world-to-action-quat-wxyz` in both trajectory converters and
  updated `validate_dataset_smoke.py` to validate replay in world coordinates.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `fdb77c9dc967d1476361b4cb106190cec696e0a8`
- implementation_commit: pending
- push/pull: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/action_conversion.py`
  - `dextrah_lab/offline_dp_bc/analyze_policy_trace.py`
  - `dextrah_lab/offline_dp_bc/trajectory_conversion.py`
  - `dextrah_lab/offline_dp_bc/generate_grasp_library_demos.py`
  - `dextrah_lab/offline_dp_bc/validate_dataset_smoke.py`
  - `dextrah_lab/offline_dp_bc/__init__.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- completed traced eval:
  - job_id: `1027729`
  - remote run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_trace96_20260611_133812`
  - local fetched run_dir:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_overfit2k_chunk8_trace96_20260611_133812`
  - log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027729.out`
- trace analysis:
  `PYTHONPATH=$PWD $VENV/bin/python -m dextrah_lab.offline_dp_bc.analyze_policy_trace --dataset .../franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift.npz --trace .../policy_trace.json --output-dir .../reports/trace_analysis_1027729_20260611_133812`
- corrected conversion:
  `PYTHONPATH="$DEX:$GGX:$GGX/end2end:$CU" GRASPGENX_ROOT="$GGX" "$GGX/.venv/bin/python" -m dextrah_lab.offline_dp_bc.trajectory_conversion <32 trajectory.json files> --output .../datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz --input-format json --phase-set full_pick_lift --graspgenx-root "$GGX" --robot-config "$ROBOT_CONFIG"`
- corrected dataset smoke:
  `PYTHONPATH="$DEX" "$GGX/.venv/bin/python" -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset .../franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
- official-DP tiny train:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=20 training.max_val_steps=2 training.num_epochs=1 policy.num_inference_steps=25 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`

Result:
- traced eval status: passed mechanically, failed behavior
  - `steps_completed=96`
  - `debug_policy_trace_records=12`
  - action gripper range `[0.890, 1.000]`
  - gripper width stayed open, final `0.07725 m`
  - EE-to-cube distance increased `0.2337 m -> 0.3047 m`
  - cube lift remained `0`
- trace analysis artifacts:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027729_20260611_133812/trace_phase_comparison.csv`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027729_20260611_133812/trace_phase_comparison.json`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027729_20260611_133812/trace_phase_comparison.png`
  - viewer:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027729_20260611_133812/trace_phase_comparison.png`
- trace-vs-dataset finding:
  - all 12 policy calls nearest to `go_to_pre_grasp_pose`
  - nearest-demo scaled distance grew `0.356 -> 1.293`
  - live `cube_minus_ee` drifted from `[0.1457,-0.1815,0.0200]` to
    `[0.1960,-0.2203,-0.0367]`
  - model action labels from the old checkpoint had positive x / negative y,
    but the Franka root-frame controller applied them as negative world x /
    positive world y, matching the observed drift.
- corrected dataset:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - `32` episodes, `22484` steps, obs/action dims `21/7`
  - corrected smoke `first_step_position_replay_error=0.0`
  - observations and phase ids are identical to the old dataset; action labels
    flip the expected x/y and roll/pitch signs.
- official-DP tiny train on corrected dataset:
  - run_dir:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_134700_curobo32_full_pick_lift_framefix_tiny`
  - final `global_step=19`, `train_loss=1.0844`, `val_loss=1.0373`,
    `train_action_mse_error=0.7494`
  - checkpoint-smoke loads passed for `first`, `gripper_closed`, and
    `lift_high`; action ranges are saturated because this is only a 20-step
    mechanics smoke, not a trained policy.

Analysis:
- Root cause for the previous BC eval failure is now concrete: the old
  full-pick/approach datasets encoded EE translation/rotation deltas in
  world/env coordinates, but `DextrahFrankaStarKittingEnv._pre_physics_step`
  passes relative commands to `DifferentialIKController` in the robot root
  frame. The Franka cube robot root is yawed 180 deg, so x/y and roll/pitch
  signs were inverted at execution.
- Existing checkpoints trained on the old labels, including the 503-step and
  overfit2k full-pick checkpoints, are stale for behavior. Their official-DP
  mechanics evidence remains useful, but no further l401 policy eval should use
  them as BC quality evidence.
- The corrected framefix dataset is the next valid input for a bounded overfit
  run. Since the 20-step checkpoint is intentionally undertrained and saturated,
  the next scale-up should be a local official-DP 2k-step overfit/debug similar
  to the prior overfit2k, then local bridge smokes, then l401 eval only if
  action ranges are sane.

Next:
- Commit/push the frame-fix, trace-analysis utility, and worklog.
- Launch a bounded corrected-label official-DP overfit/debug run only after
  this source checkpoint is recorded; do not reuse stale old-label checkpoints
  for more behavior claims.
