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
- implementation_commit: `9a61e92ac15f8664f23a74dfac617d4ed248ac2d`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  l401 has no active jobs after `1027729` completed, next cluster launch must
  deploy the latest commit before running.
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

## 2026-06-11T13:52:00-07:00 - corrected-label overfit/debug launch

Goal:
- Train the first behavior-relevant official Diffusion Policy checkpoint on
  frame-corrected full-pick/lift labels.

Hypothesis:
- With x/y and roll/pitch labels rotated into the Franka root action frame, a
  bounded ~2.5k-step overfit/debug run should learn the same low train/val loss
  as the stale overfit2k checkpoint while producing approach actions that move
  toward the cube when interpreted by the Isaac controller.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- source_commit: `6f58a973c60fa21154c207a31b47ef8f20b46584`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`

Command / Job:
- command:
  `PYTHONPATH="$DP:$DEX" WANDB_MODE=offline "$VENV/bin/python" train.py --config-dir "$DEX/dextrah_lab/offline_dp_bc/config" --config-name franka_cube_lowdim_dp task.dataset_path="$DATASET" task.dataset.val_ratio=0.25 training.device=cuda:0 training.max_train_steps=100 training.max_val_steps=4 training.num_epochs=25 policy.num_inference_steps=100 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir="$RUN_DIR"`
- job_id: local process, no Slurm
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k`
- log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_framefix_overfit2k_train.log`

Result:
- status: passed local official-DP training and bridge-smoke gates.
- final official-DP metrics from `logs.json.txt`:
  - `global_step=2523`
  - `train_loss=0.00884601678699255`
  - `val_loss=0.009782439097762108`
  - `train_action_mse_error=0.0011517644161358476`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k/checkpoints/latest.ckpt`
- local checkpoint bridge smokes, all using official DP workspace loading,
  `--num-inference-steps 100`, and `--warm-history-from-dataset`:
  - first/open log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_framefix_overfit2k_checkpoint_smoke_first_warm_100step.log`
    - bridge action min/max:
      x `[-0.0309, 0.0088]`, y `[0.0294, 0.0569]`, z `[0.0769, 0.1583]`,
      gripper `[0.9341, 1.0000]`
  - gripper-closed log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_framefix_overfit2k_checkpoint_smoke_gripper_closed_warm_100step.log`
    - bridge action min/max:
      x `[-0.0186, -0.0030]`, y `[-0.0054, 0.0072]`,
      z `[-0.0037, 0.0235]`, gripper `[-0.9653, -0.8589]`
  - lift-high log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/official_dp_curobo32_full_pick_lift_framefix_overfit2k_checkpoint_smoke_lift_high_warm_100step.log`
    - bridge action min/max:
      x `[-0.0130, 0.0039]`, y `[-0.0020, 0.0083]`,
      z `[-0.0056, 0.0175]`, gripper `[-1.0000, -0.9333]`

Next:
- Commit/push this worklog-only evidence boundary, copy the corrected
  checkpoint to l401 results storage, deploy the exact branch commit into the
  agent-owned l401 worktree, then launch a tiny traced l401 eval with
  `NUM_STEPS=96`, `ACTION_CHUNK_STEPS=8`, and
  `DEBUG_POLICY_TRACE_MAX_CALLS=12`.

## 2026-06-11T13:59:30-07:00 - corrected-label l401 traced eval gate

Goal:
- Run the first bounded DEXTRAH/Isaac rollout against the frame-corrected
  official-DP overfit checkpoint, with trace enabled for the same 12-call
  dataset-nearest-neighbor diagnosis used on job `1027729`.

Hypothesis:
- If the frame fix is correct, early action chunks should no longer command
  the robot away from the cube in world x/y. The tiny rollout may still fail
  grasp/lift because the dataset is only 32 cuRobo demos and the observation
  bridge is sparse, but trace evidence should show approach motion and phase
  progression improving relative to stale job `1027729`.

Change:
- No eval-path source changes for this launch. The source boundary was the
  committed frame/action fix plus the worklog evidence update.
- After artifact inspection, patched
  `dextrah_lab/offline_dp_bc/analyze_policy_trace.py` so trace-analysis prose
  reports actual action-frame/world-delta means and distance changes instead
  of the stale old-label sign diagnosis.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `6f58a973c60fa21154c207a31b47ef8f20b46584`
- implementation_commit: `5e3e27c215cc2421fbcfab203457290864a6320b`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  deployed to l401 agent-owned worktree by Git bundle
- changed_files:
  - `dextrah_lab/offline_dp_bc/analyze_policy_trace.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `5e3e27c215cc2421fbcfab203457290864a6320b`, detached HEAD,
  clean at launch.

Command / Job:
- planned checkpoint source:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k/checkpoints/latest.ckpt`
- remote checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt`
- deployment:
  - bundle:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-5e3e27c215cc2421fbcfab203457290864a6320b.bundle`
  - checkpoint transfer verified remote size `254M`
- eval command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace96_20260611_135436 NUM_ENVS=1 NUM_STEPS=96 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=8 DEBUG_POLICY_TRACE_MAX_CALLS=12 DEBUG_POLICY_TRACE_ENV_INDEX=0 CAPTURE_VIDEO=False PRINT_INTERVAL=8 CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1027736`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace96_20260611_135436`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027736.out`

Result:
- status: passed mechanics, failed behavior within 96-step horizon.
- Slurm: `COMPLETED 0:0`, elapsed `00:00:49`, node `pool0-00016`.
- local fetched artifacts:
  - run_dir:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace96_20260611_135436`
  - log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027736.out`
  - trace analysis:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027736_framefix_20260611_135436`
- metrics:
  - `steps_completed=96`
  - `reward_mean=1.455226716895898`, `reward_final=1.5437241792678833`
  - `final_success_rate=0.0`, `cube_lift_height=0.0`
  - `ee_to_cube_dist` improved `0.2332 -> 0.1729 m`
  - `finger_center_to_cube_dist` improved `0.2200 -> 0.1777 m`
  - `gripper_width` stayed open `0.0798 -> 0.0739 m`
  - action range:
    x `[-0.0909, -0.0204]`, y `[0.0583, 0.1358]`,
    z `[0.0801, 0.2091]`, gripper `[0.7906, 1.0]`
- trace analysis against corrected framefix dataset:
  - all `12` policy calls nearest to `go_to_pre_grasp_pose`
  - nearest-demo distance `0.3563 -> 0.4031`
  - live cube-minus-EE norm `0.2336 -> 0.1766 m`
  - gripper chunks stayed open/positive `[0.791, 1.000]`
  - mean first action-frame xyz
    `[-0.0399, 0.0901, 0.1182]` maps to mean world delta xyz
    `[0.00239, -0.00541, 0.00532]`
- dataset timing check:
  - close starts at local step min/mean/max `282/282.625/302`
  - lift starts at `402/402.625/422`
  - hold-after-lift starts at `642/642.625/662`

Next:
- Commit/push the analyzer/worklog update, deploy the latest commit to the
  agent-owned l401 worktree, and launch a longer bounded no-video trace:
  `NUM_STEPS=512`, `ACTION_CHUNK_STEPS=8`,
  `DEBUG_POLICY_TRACE_MAX_CALLS=64`. This should reach the close/lift phase
  if the bridge can stay on-distribution; if gripper remains open through
  step 512, the next patch should target phase/history conditioning or
  dataset/action timing rather than the already-fixed action frame.

## 2026-06-11T14:00:00-07:00 - corrected-label 512-step trace plan

Goal:
- Test whether the corrected official-DP checkpoint reaches close/lift once
  the rollout horizon spans the dataset's close and lift phase timings.

Hypothesis:
- The 96-step trace was a mechanics smoke and ended before the demonstration
  phase where close starts. A 512-step trace should show negative gripper
  actions after ~283 env steps and lift intent after ~403 env steps if live
  observations stay close enough to the converted demo manifold.

Change:
- Source change since the previous launch is limited to the trace-analysis
  summary prose patch; eval behavior is unchanged.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `5e3e27c215cc2421fbcfab203457290864a6320b`
- implementation_commit: `cdd181dd7311fd913029143b762c81fe83af9d7e`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  deployed to l401 agent-owned worktree by Git bundle
- changed_files:
  - `dextrah_lab/offline_dp_bc/analyze_policy_trace.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `cdd181dd7311fd913029143b762c81fe83af9d7e`, detached HEAD,
  clean at launch.

Command / Job:
- eval command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907 NUM_ENVS=1 NUM_STEPS=512 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=8 DEBUG_POLICY_TRACE_MAX_CALLS=64 DEBUG_POLICY_TRACE_ENV_INDEX=0 CAPTURE_VIDEO=False PRINT_INTERVAL=32 CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1027737`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027737.out`

Result:
- status: completed, behavior still failed.
- Slurm: `COMPLETED 0:0`, elapsed `00:01:24`, node `pool0-00016`.
- local fetched artifacts:
  - run_dir:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907`
  - log:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027737.out`
  - trace analysis:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907`
- metrics:
  - `steps_completed=512`
  - `reward_final=1.6986042261123657`
  - `final_success_rate=0.0`, `cube_lift_height max=0.0`
  - `final_gripper_width=0.0012196956668049097`
  - `ee_to_cube_dist final/min=0.13433830440044403/0.13275255262851715`
  - `finger_center_to_cube_dist final/min=0.16798599064350128/0.16150173544883728`
  - `final_trace_cube_minus_ee=[-0.010522693395614624, -0.10216313600540161, -0.08673244714736938]`
- trace analysis:
  - nearest phases: `49` calls `go_to_pre_grasp_pose`, `15` calls `lift_object`
  - first negative gripper chunk at step `184`
  - first hard-close chunk at step `208`
  - first live gripper width `<1cm` at step `216`
  - first nearest `lift_object` at step `392`
  - nearest-demo distance increased `0.3563 -> 1.2201`
  - live cube-minus-EE norm improved `0.2336 -> 0.1344 m`

Analysis:
- The corrected-label checkpoint no longer simply drives away from the cube and
  it does close the gripper. The failure is still behaviorally invalid: closure
  happens while the live cube-relative grasp geometry is not near the converted
  demo manifold, and no cube lift occurs.

## 2026-06-11T14:08:30-07:00 - systematic DP BC train/eval mismatch audit

Goal:
- Treat the bad DP BC eval behavior as an implementation mismatch until
  disproven. Audit action frames, observation extraction/normalization,
  reset distribution, and temporal chunking before launching any more training,
  augmentation, or RL warm-start work.

Hypothesis:
- The framefix checkpoint now closes when the rollout reaches later phases, so
  the remaining failure is likely train/eval mismatch in observation bridge,
  reset distribution, temporal semantics, or residual action-frame handling.

Change:
- Planned new local audit utility:
  `dextrah_lab/offline_dp_bc/audit_eval_mismatch.py`
- Planned artifact namespace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907`

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cdd181dd7311fd913029143b762c81fe83af9d7e`
- implementation_commit: pending local commit for this entry
- changed_files:
  - `dextrah_lab/offline_dp_bc/audit_eval_mismatch.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- inputs:
  - dataset:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - metadata:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz.metadata.json`
  - metrics:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907/metrics.json`
  - trace:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907/policy_trace.json`
  - trace phase comparison:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907/trace_phase_comparison.json`
- planned command:
  `PYTHONPATH=$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.audit_eval_mismatch --dataset <framefix.npz> --metadata <metadata.json> --metrics <metrics.json> --trace <policy_trace.json> --trace-analysis <trace_phase_comparison.json> --output-dir <audit_dir>`
- actual command:
  `PYTHONPATH=/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.audit_eval_mismatch --dataset /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz --metadata /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz.metadata.json --metrics /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907/metrics.json --trace /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907/policy_trace.json --trace-analysis /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907/trace_phase_comparison.json --checkpoint /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k/checkpoints/latest.ckpt --output-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907`
- validation:
  `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/audit_eval_mismatch.py`

Result:
- status: completed.
- artifact_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907`
- files:
  - `mismatch_audit_report.md`
  - `audit_summary.json`
  - `behavior_metrics.png`
  - `trace_phase_action.png`
  - `obs_distribution.png`
  - `trace_phase_rows.csv`
- viz-open:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/mismatch_audit_1027737_framefix_20260611_135907/trace_phase_action.png`
- key evidence:
  - Old pre-framefix checkpoints/videos are stale and invalid for behavior
    claims.
  - Dataset action frame uses `world_to_action_quat_wxyz=[0.0, 0.0, 0.0, 1.0]`;
    eval action scales match `(0.06, 0.06, 0.045)` and `(0.25, 0.25, 0.30)`.
  - 72D bridge slices match the env layout and checkpoint normalizer matches
    dataset means (`obs mean max abs diff=6.22868537902832e-05`,
    action mean diff `0.0`).
  - Trace lowdim fields outside dataset min/max:
    `['ee_pos_x', 'ee_pos_y', 'ee_pos_z', 'ee_quat_w', 'cube_pos_z', 'cube_minus_ee_z', 'cube_goal_delta_z']`.
  - Reset start cube position is within dataset episode-start cube range;
    nearest dataset start has raw 21D L2 `0.0375`.
  - Temporal commands are no longer completely wrong: first negative gripper
    command at step `184`, hard close at `208`, live width `<1cm` at `216`,
    and first nearest `lift_object` at step `392`.
  - Actual failure: final cube-minus-EE
    `[-0.010522693395614624, -0.10216313600540161, -0.08673244714736938]`,
    EE-to-cube final/min `0.13433830440044403/0.13275255262851715 m`,
    finger-center final/min `0.16798599064350128/0.16150173544883728 m`,
    max lift `0.0`.

Analysis:
- The frame/action convention and checkpoint normalization are now checked and
  do not explain the bad video. The remaining concrete mismatch is geometric
  and temporal: the policy starts closing before the dataset close marker and
  while live cube-relative geometry is still far from the demo grasp geometry.
- Do not use stale pre-framefix videos/checkpoints for behavior claims.

Next:
- Commit/push the audit utility plus this worklog update.
- Next bounded root-cause check: compare live cube-minus-EE and gripper width
  against the nearest demo step and against the demo first-close/hard-close
  geometry; also verify two-step observation-history initialization and
  action-chunk/repeat timing before any larger training launch.

## 2026-06-11T14:10:22-07:00 - live-vs-demo geometry and history-cadence diagnostic plan

Goal:
- Verify whether the failed framefix rollout is caused by a reset/pregrasp
  distribution mismatch, wrong object-relative close/lift geometry, or a
  temporal-history mismatch introduced by chunked evaluation.

Hypothesis:
- Training samples two adjacent lowdim observations (`pad_before=1`,
  contiguous 16-step sequences). The current chunked eval only pushes a new
  observation into `LowdimObsHistory` when it queries a new 8-step action chunk,
  so after the first call the policy sees an 8-env-step history gap rather than
  adjacent control-timestep observations. This can explain early closing and
  off-manifold cube-relative geometry even though static slices/normalization
  are correct.

Change:
- Added local artifact utility:
  `dextrah_lab/offline_dp_bc/diagnose_live_demo_geometry.py`
- Artifact namespace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027737_framefix_20260611_135907`
- Patched `LowdimObsHistory` to track step timestamps and accept an optional
  `step=` on push/inference helpers.
- Patched `eval_franka_cube_dp_policy.py` so lowdim history is refreshed every
  env step while action chunks execute open-loop; the trace now writes
  `history_steps_after_push` and `history_step_gap`.
- Updated the diagnostic to prefer recorded history steps when present.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `aad5eef545aac4c1fffb6acf7507c1c6fc70255f`
- implementation_commit: `cadf96733e72454d1fd8bdb30bb20afefc723d66`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  l401 deployment pending.
- changed_files:
  - `dextrah_lab/offline_dp_bc/diagnose_live_demo_geometry.py`
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- planned diagnostic command:
  `PYTHONPATH=$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.diagnose_live_demo_geometry --dataset <framefix.npz> --trace <policy_trace.json> --trace-analysis <trace_phase_comparison.json> --output-dir <geometry_dir>`
- actual diagnostic command:
  `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.diagnose_live_demo_geometry --dataset /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz --trace /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_trace512_20260611_135907/policy_trace.json --trace-analysis /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027737_framefix_20260611_135907/trace_phase_comparison.json --output-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027737_framefix_20260611_135907`
- local validation:
  - `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/diagnose_live_demo_geometry.py dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `PYTHONPATH=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy:$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_debug/run_20260611_135200_curobo32_full_pick_lift_framefix_overfit2k/checkpoints/latest.ckpt --dataset /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz --device cpu --batch-size 2 --num-inference-steps 2 --row-selector first --warm-history-from-dataset`

Result:
- status: diagnostic passed, patch committed/pushed.
- artifact_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027737_framefix_20260611_135907`
- files:
  - `geometry_diagnosis_report.md`
  - `geometry_diagnosis_summary.json`
  - `live_vs_nearest_demo_geometry.csv`
  - `live_vs_nearest_demo_geometry.png`
- viz-open:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027737_framefix_20260611_135907/live_vs_nearest_demo_geometry.png`
- required table fields present:
  policy call index, env step, history obs timestamps/gap,
  live cube-minus-EE, nearest-demo cube-minus-EE, first-close demo
  cube-minus-EE, hard-close demo cube-minus-EE, gripper command/width,
  nearest phase, and nearest distance.
- diagnostic evidence:
  - training history step delta: `1`
  - pre-patch eval policy-call deltas: `[8]`
  - pre-patch history slot gaps: `[0, 8]`; the `0` is reset duplicate, then
    history is `step-8`/`step`
  - live first negative gripper step: `184`
  - live first hard-close step: `208`
  - dataset first close phase mean step: `282.625`
  - dataset first hard-close mean step: `310.625`
  - at live hard close, `history_step_gap=8`, live cube-minus-EE
    `[0.056520432233810425, -0.11438523977994919, -0.0592767596244812]`
  - nearest-demo cube-minus-EE at that point:
    `[0.08766841888427734, -0.09175277501344681, -0.05864214897155762]`
  - nearest-episode hard-close demo cube-minus-EE:
    `[-0.01989993453025818, -0.0000015050172805786133, -0.02014338970184326]`
  - live-to-demo hard-close mean distance: `0.126915844401538 m`
- local official-DP checkpoint bridge smoke passed after the history API patch.

Analysis:
- Concrete mismatch confirmed. The model was trained on adjacent lowdim
  histories but the chunked eval conditioned it on observations spaced by one
  8-step action chunk. This is an implementation bug in the eval bridge, not a
  reason to pivot to augmentation or RL.
- The post-patch trace must show policy calls still every 8 env steps, but
  `history_step_gap=1` after the reset duplicate because history is refreshed
  during open-loop chunk execution.

Next:
- Commit/push code and worklog, deploy exact commit to the agent-owned l401
  worktree, and launch a bounded no-video trace with the same checkpoint/seed:
  `NUM_ENVS=1`, `NUM_STEPS=512`, `ACTION_CHUNK_STEPS=8`,
  `DEBUG_POLICY_TRACE_MAX_CALLS=64`, `CAPTURE_VIDEO=False`.
- Acceptance for the next trace: recorded history slot gap should be `1`
  after reset, close timing should move toward demo timing, and EE/finger
  distances/cube-minus-EE should not regress relative to job `1027737`.

## 2026-06-11T14:18:02-07:00 - history-refresh l401 trace launch

Goal:
- Validate the narrow eval-history fix on l401 without training: history slots
  should be adjacent control steps while action chunks still execute open-loop.

Hypothesis:
- Refreshing `LowdimObsHistory` every env step will remove the `step-8`/`step`
  conditioning bug. With the same checkpoint/seed, close timing should move
  toward the demo close/hard-close timing and cube-relative/finger distances
  should not regress versus job `1027737`.

Change:
- No new source changes after commit `5d5b09520bce4e00517d1ce7e0a0d9db71eaa24e`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `5d5b09520bce4e00517d1ce7e0a0d9db71eaa24e`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  remote GitHub fetch blocked by l401 SSH auth, so deployed by Git bundle.
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `5d5b09520bce4e00517d1ce7e0a0d9db71eaa24e`, detached HEAD,
  clean at launch.

Command / Job:
- planned eval command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802 NUM_ENVS=1 NUM_STEPS=512 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=8 DEBUG_POLICY_TRACE_MAX_CALLS=64 DEBUG_POLICY_TRACE_ENV_INDEX=0 CAPTURE_VIDEO=False PRINT_INTERVAL=32 CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_<job_id>.out`
- job_id: `1027744`

Result:
- status: submitted, monitoring.

Next:
- Submit the bounded trace, monitor Slurm/logs, fetch `metrics.json` and
  `policy_trace.json`, rerun trace analysis plus live-vs-demo geometry
  diagnostic, and compare against job `1027737`.

## 2026-06-11T14:34:00-07:00 - history-refresh trace result and chunk ablation plan

Goal:
- Inspect job `1027744` and decide whether the history-cadence fix resolved
  the visible eval drift.

Command / Job:
- job_id: `1027744`
- run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk8_historyfix_trace512_20260611_141802`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027744.out`
- trace analysis:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027744_historyfix_20260611_141802`
- live-vs-demo geometry:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027744_historyfix_20260611_141802`

Result:
- Slurm status: `COMPLETED`, exit `0:0`.
- Eval metrics: `steps_completed=512`, `final_success_rate=0.0`,
  `cube_lift_height.max=0.0`, `reward_mean=1.6488098790869117`,
  `reward_final=1.6844426393508911`,
  `final_gripper_width=0.0011646132916212082`.
- Geometry metrics:
  `ee_to_cube_dist.min/final=0.13600821793079376/0.13712914288043976`,
  `finger_center_to_cube_dist.min/final=0.16404975950717926/0.16952744126319885`.
- Trace metrics:
  final live cube-minus-EE
  `[-0.00996100902557373, -0.10787208378314972, -0.08425873517990112]`;
  nearest-demo distance increased `0.3562566041946411 -> 1.2926826477050781`;
  nearest phases were `52` pregrasp calls and `12` lift calls.
- History validation:
  `eval_policy_call_step_delta_unique=[8]` as expected for chunk queries,
  but `history_slot_step_gap_unique=[0, 1]`; the `0` is only the reset
  duplicate and subsequent policy histories use adjacent control steps.
  Therefore the history-cadence patch is mechanically correct.
- Temporal behavior regressed relative to dataset timing:
  first negative gripper command moved to step `144`, first hard close to
  step `168`, while dataset first close/hard-close means are
  `282.625/310.625`.
- At live hard close, history gap is `1`, but grasp geometry is still wrong:
  live cube-minus-EE
  `[0.07217836380004883, -0.12357199192047119, -0.04983395338058472]`,
  nearest-demo cube-minus-EE
  `[0.09566575288772583, -0.11058403551578522, -0.04289048910140991]`,
  nearest episode hard-close cube-minus-EE
  `[-0.01989993453025818, -0.0000015050172805786133, -0.02014338970184326]`,
  live-to-hard-close-demo distance `0.14052984586502268 m`.

Analysis:
- The original history-cadence bug is fixed, but behavior remains invalid for
  BC claims: the policy closes/lifts while the live cube-relative grasp
  geometry is still far from the demo close geometry, and the cube never lifts.
- This is still a train/eval mismatch or bridge bug until disproven. Do not
  use old pre-framefix or pre-history-fix videos/checkpoints as behavior
  evidence.
- New orchestrator hypothesis: with history fixed, remaining mismatch may be
  open-loop execution drift from applying 8 predicted actions before the next
  policy query. Need a bounded `ACTION_CHUNK_STEPS=1` ablation using the same
  checkpoint/seed and no training.

Next:
- Commit/push this evidence checkpoint.
- Launch l401 no-video trace:
  `NUM_ENVS=1`, `NUM_STEPS=512`, `NUM_INFERENCE_STEPS=100`,
  `ACTION_CHUNK_STEPS=1`, `DEBUG_POLICY_TRACE_MAX_CALLS=512`,
  `DEBUG_POLICY_TRACE_ENV_INDEX=0`, `CAPTURE_VIDEO=False`,
  same framefix overfit checkpoint and remote code commit
  `5d5b09520bce4e00517d1ce7e0a0d9db71eaa24e`.
- Compare chunk 1 vs chunk 8 on close timing, EE/finger distances,
  cube-minus-EE at first negative/hard-close/live width <1 cm, gripper width,
  and nearest-demo distance. If chunk 1 improves substantially, root cause is
  action-chunk open-loop drift; if both are bad, continue observation/action
  semantics audit.

## 2026-06-11T14:39:00-07:00 - chunk1 open-loop ablation launch

Goal:
- Test whether the remaining failure after the history fix is caused by
  executing 8 predicted actions open-loop before querying the policy again.

Hypothesis:
- If chunk execution drift is the main bug, `ACTION_CHUNK_STEPS=1` with the
  same checkpoint/seed should delay close timing toward the demo close phases
  and improve EE/finger/cube geometry relative to job `1027744`.
- If chunk 1 is still bad, the remaining issue is likely in observation/action
  semantics, reset distribution, sequence target semantics, or controller
  execution rather than only chunk open-loop drift.

Command / Job:
- job_id: `1027746`
- run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900 NUM_ENVS=1 NUM_STEPS=512 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=1 DEBUG_POLICY_TRACE_MAX_CALLS=512 DEBUG_POLICY_TRACE_ENV_INDEX=0 CAPTURE_VIDEO=False PRINT_INTERVAL=32 CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote source:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at code commit `5d5b09520bce4e00517d1ce7e0a0d9db71eaa24e`.
- expected remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027746.out`

Result:
- status: submitted, monitoring.

Next:
- Fetch metrics/trace after completion.
- Run the same trace phase analysis and live-vs-demo geometry diagnostic as
  jobs `1027737` and `1027744`.
- Build an inspectable mismatch report comparing chunk 8 post-history-fix
  against chunk 1 on close timing, cube-minus-EE at close events, gripper width,
  EE/finger distance curves, and nearest-demo distance.

## 2026-06-11T14:44:00-07:00 - chunk1 ablation result and comparison artifact

Goal:
- Complete the chunk-size ablation requested after the history-cadence fix and
  determine whether open-loop 8-step chunk execution explains the bad video.

Command / Job:
- job_id: `1027746`
- run_name:
  `franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- Slurm status: `COMPLETED`, exit `0:0`, elapsed `00:04:54`,
  node `pool0-00016`.
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_full_pick_lift_framefix_overfit2k_chunk1_historyfix_trace512_20260611_143900`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027746.out`
- trace analysis:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/trace_analysis_1027746_chunk1_historyfix_20260611_143900`
- live-vs-demo geometry:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/live_demo_geometry_1027746_chunk1_historyfix_20260611_143900`
- comparison bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/chunk_ablation_1027744_chunk8_vs_1027746_chunk1_20260611_143900`
- viz-open:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/chunk_ablation_1027744_chunk8_vs_1027746_chunk1_20260611_143900/chunk_ablation_curves.png`

Result:
- Chunk 1 did not fix the task failure:
  `success=0`, `cube_lift_height.max=0`, `reward_mean/final=1.5820/1.5789`.
- Compared with chunk 8 historyfix (`1027744`):
  - chunk8: reward mean/final `1.6488/1.6844`,
    EE-to-cube min/final `0.1360/0.1371`,
    finger-center-to-cube min/final `0.1640/0.1695`,
    first negative/hard-close steps `144/168`,
    final cube-minus-EE `[-0.010, -0.108, -0.084]`.
  - chunk1: reward mean/final `1.5820/1.5789`,
    EE-to-cube min/final `0.1458/0.1517`,
    finger-center-to-cube min/final `0.1686/0.1824`,
    first negative/hard-close steps `207/224`,
    final cube-minus-EE `[-0.0076, -0.1180, -0.0949]`.
- Both runs have expected history slot gaps `[0, 1]`.
- Chunk 1 delays closure in the right direction, but it still closes before
  the dataset mean close/hard-close steps (`282.625/310.625`) and closes while
  nearest train windows are still pregrasp/open-gripper windows.
- At chunk1 hard close, nearest train action gripper is still `+1.0` open,
  while the live policy command is about `-0.954` close. Live hard-close
  cube-minus-EE is `[0.0611, -0.1192, -0.0633]`, still far from the demo
  hard-close geometry `[-0.0199, -0.0000015, -0.0201]`.

Analysis:
- Open-loop chunk execution contributes to premature close timing but is not
  the root cause of the drifting/ignoring-object failure.
- Since history cadence and chunk size are not sufficient, continue treating
  this as a train/eval mismatch or implementation bug. The next bounded checks
  are action/trajectory target semantics and controller execution.

Next:
- Do not train or scale.
- Add/run a local official-DP action-semantics diagnostic:
  compare checkpoint predictions on exact training windows and live trace
  windows against dataset labels at `t`, `t+1`, and future horizon offsets.
- Then validate one-step or short-snippet execution of selected dataset labels
  in the real DEXTRAH env/controller on l401. If dataset actions do not move
  the EE as recorded by the demos, patch action scale/frame/controller bridge;
  if replay works, focus on official-DP sequence indexing and live-state
  observation support mismatch.

## 2026-06-11T14:45:44-07:00 - action-semantics and train/eval config audit artifacts

Goal:
- Finish the bounded official-DP action-semantics diagnostic after the chunk
  ablation and add a dedicated train/eval config audit artifact. No training or
  rollout was launched for this entry.

Hypothesis:
- If the failure is a remaining train/eval mismatch rather than weak BC, exact
  training windows should be close to labels but live trace windows should show
  out-of-support state/action behavior. EMA-vs-raw-model comparison should
  indicate whether the short overfit EMA policy source is itself the cause.

Change:
- Added `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`.
  - Loads the official `real-stanford/diffusion_policy` checkpoint through
    `TrainDiffusionUnetLowdimWorkspace`.
  - Compares `predict_action()` output against dataset labels at offsets
    `[-2, -1, 0, 1, 2, 4, 7]`.
  - Samples exact demo windows and live trace windows from chunk8/chunk1
    history-fixed evals.
  - Supports `--policy-source ema|model|auto`.
- Added `dextrah_lab/offline_dp_bc/audit_train_eval_config.py`.
  - Audits official DP config, checkpoint normalizer, dataset metadata, PPO
    lowdim bridge slices, action frame/scale, gripper convention, history
    gaps, chunking, reset distribution, live observation support, and controller
    replay status.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `23ec84c`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`
  - `dextrah_lab/offline_dp_bc/audit_train_eval_config.py`

Commands:
- syntax:
  `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/offline_dp_bc/audit_train_eval_config.py dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`
- action semantics EMA:
  `PYTHONPATH=$OFFICIAL_DP:$PWD $VENV/bin/python -m dextrah_lab.offline_dp_bc.diagnose_dp_action_semantics --checkpoint $CKPT --dataset $DATA --output-dir .../action_semantics_framefix_overfit2k_ep29_chunk8_chunk1_ema_20260611_145500 --diffusion-policy-root $OFFICIAL_DP --device cpu --num-inference-steps 100 --policy-source ema --seed 42 --episode-index 29 --row-index 20393 --row-index 20394 --trace $TRACE8 --trace $TRACE1`
- action semantics raw model:
  `PYTHONPATH=$OFFICIAL_DP:$PWD $VENV/bin/python -m dextrah_lab.offline_dp_bc.diagnose_dp_action_semantics --checkpoint $CKPT --dataset $DATA --output-dir .../action_semantics_framefix_overfit2k_ep29_chunk8_chunk1_model_20260611_145500 --diffusion-policy-root $OFFICIAL_DP --device cpu --num-inference-steps 100 --policy-source model --seed 42 --episode-index 29 --row-index 20393 --row-index 20394 --trace $TRACE8 --trace $TRACE1`
- train/eval config audit:
  `PYTHONPATH=$PWD $VENV/bin/python -m dextrah_lab.offline_dp_bc.audit_train_eval_config --dataset $DATA --metadata ${DATA}.metadata.json --checkpoint $CKPT --train-config $CONFIG --metrics $RUN/metrics.json --trace $RUN/policy_trace.json --output-dir .../train_eval_config_audit_1027744_historyfix_20260611_150100`

Artifacts:
- action semantics EMA:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_semantics_framefix_overfit2k_ep29_chunk8_chunk1_ema_20260611_145500`
- action semantics raw model:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_semantics_framefix_overfit2k_ep29_chunk8_chunk1_model_20260611_145500`
- train/eval config audit:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/train_eval_config_audit_1027744_historyfix_20260611_150100`
- viz-open URLs:
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_semantics_framefix_overfit2k_ep29_chunk8_chunk1_ema_20260611_145500/action_semantics_offsets.png`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/chunk_ablation_1027744_chunk8_vs_1027746_chunk1_20260611_143900/chunk_ablation_curves.png`

Result:
- Official DP train/eval sequence convention from config:
  `horizon=16`, `n_obs_steps=2`, `n_action_steps=8`,
  `pad_before=1`, `pad_after=7`, `oa_step_convention=True`, so first returned
  eval action should target dataset `a[t]`.
- EMA and raw model agree on the important failure; raw model does not fix it.
- Exact demo rows:
  - `demo_first_hard_close`: EMA returned MSE@0 `0.000261`, pred grip
    `-0.970` vs label `-0.931`; raw model MSE@0 `0.000122`, pred grip
    `-1.000`.
  - `demo_first_negative_gripper`: best offset `4`, indicating the learned
    close ramp is temporally smeared/future-biased around the transition.
  - pregrasp rows `20393/20394`: best offset `7` but gripper remains open,
    so this offset bias alone does not explain hard-close failure.
- Live trace windows:
  - chunk8 `live_first_hard_close` nearest row `20393` is still
    `go_to_pre_grasp_pose`, nearest distance `0.819`, nearest dataset grip
    `+1.0`, but EMA predicts grip `-0.987` and raw model predicts `-1.000`.
  - chunk1 `live_first_hard_close` nearest row `20394` is still
    `go_to_pre_grasp_pose`, nearest distance `0.901`, nearest dataset grip
    `+1.0`, but EMA predicts grip `-0.884` and raw model predicts `-0.926`.
- Config audit:
  - normalizer matches dataset means: max obs mean diff `6.23e-05`, max action
    mean diff `0`.
  - PPO-to-lowdim bridge slices match the 72D env layout.
  - action frame/scale matches the framefix dataset:
    position `[0.06,0.06,0.045]`, rotation `[0.25,0.25,0.3]`,
    `world_to_action_quat_wxyz=[0,0,0,1]`.
  - gripper sign matches and physical gripper closes (`final_width=0.00116`).
  - history cadence is fixed (`history_step_gap` unique `[0,1]`).
  - live trace still leaves dataset support in:
    `ee_pos_x`, `ee_pos_y`, `ee_pos_z`, `ee_quat_w`, `cube_pos_z`,
    `cube_minus_ee_z`, and `cube_goal_delta_z`.

Analysis:
- Chunk size is not sufficient, and EMA lag is not the primary cause.
- The remaining failure is still a train/eval mismatch or controller/action
  execution issue: live rollout enters lowdim states that are outside demo
  support, then the policy outputs close commands while nearest demo windows
  are still pregrasp/open.
- Before any new training or RL handoff, run a real-env one-step/short-horizon
  teacher-forcing replay to verify dataset labels produce the expected EE
  motion direction in DEXTRAH's controller.

Next:
- Commit and push the new diagnostics.
- Deploy the commit to the agent-owned l401 worktree.
- Stage the framefix dataset under the mounted `/results` namespace if it is
  not already present on l401.
- Launch a bounded no-video replay job with `STEPS=8`,
  `MODES=dataset_t,dataset_t_plus_1,dataset_t_plus_7,dp_replan`,
  `NUM_ENVS=1`, same checkpoint and seed.

## 2026-06-11T14:45:44-07:00 - bounded replay implementation before launch

Goal:
- Add the real-env teacher-forcing replay path required before any scale-up or
  RL warm-start claim.

Change:
- Added `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`.
  - Runs the DEXTRAH Franka cube env through Isaac Lab.
  - Finds the nearest converted lowdim demo row to the live reset/current
    observation.
  - Compares official-DP first action against dataset labels at `t`, `t+1`,
    and `t+7`.
  - Executes short sequences for modes `dataset_t`, `dataset_t_plus_1`,
    `dataset_t_plus_7`, and/or `dp_replan`.
  - Records expected action-frame/world delta, actual EE delta, cosine,
    EE-to-cube distance, gripper width, labels, predictions, and executed
    actions to CSV/JSON/PNG/Markdown.
- Added `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`.
  - Reuses the DEXTRAH Isaac Lab container and official DP env mounts.
  - Writes artifacts under `/lustre/.../results/dextrah/replays/$RUN_NAME`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/offline_dp_bc/audit_train_eval_config.py dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`

Result:
- Local syntax validation passed.
- Replay cluster job not launched yet at this entry; commit/push/deploy first.

## 2026-06-11T14:51:56-07:00 - replay 1027754 fetched and inspected

Goal:
- Complete the artifact loop for the bounded real-env teacher-forcing replay
  and record what it proves before any BC/RL scale-up.

Command / Job:
- job_id: `1027754`
- run_name:
  `franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800`
- Slurm status: `COMPLETED`, exit `0:0`, elapsed `00:00:59`,
  node `pool0-00016`.
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/replay_franka_cube_dp_actions_1027754.out`
- local inspection report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_report.md`
- inspection CSV/JSON:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_summary.csv`
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_summary.json`
- viz-open:
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800/replay_motion.png`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_teacher8_20260611_144800/replay_report.md`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_report.md`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027754_teacher8_20260611_144800/replay_inspection_summary.json`

Result:
- Replay verdict printed by job:
  `Controller replay follows the expected dataset action direction at this reset; continue debugging policy/live-state semantics.`
- Mode-by-mode replay metrics:

| mode | start EE-cube before | final EE-cube | reward start | reward final | mean cosine | min cosine | sign match | result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `dataset_t` | `0.2336` | `0.2317` | `1.3647` | `1.3673` | `0.836` | `0.686` | `1.000` | moves toward cube |
| `dataset_t_plus_1` | `0.2336` | `0.2311` | `1.3647` | `1.3693` | `0.851` | `0.686` | `1.000` | moves toward cube |
| `dataset_t_plus_7` | `0.2336` | `0.2268` | `1.3657` | `1.3819` | `0.904` | `0.636` | `0.958` | moves toward cube |
| `dp_replan` | `0.2336` | `0.2293` | `1.3654` | `1.3741` | `0.875` | `0.348` | `0.958` | moves toward cube |

- All teacher-forced dataset modes reduce EE-to-cube distance over 8 env
  steps. `dataset_t_plus_7` moves fastest, but `dataset_t`, `dataset_t_plus_1`,
  and `dp_replan` also improve distance and reward.
- Expected-vs-actual EE motion direction checks are positive. Mean cosine is
  `0.836-0.904` for dataset modes and `0.875` for DP replan; sign-match is
  `1.000` for `dataset_t`/`dataset_t_plus_1` and `0.958` for
  `dataset_t_plus_7`/`dp_replan`.
- Initial nearest demo row is `16868` in `go_to_pre_grasp_pose`, with scaled
  nearest live distance about `0.356`.

Analysis:
- The replay narrows the bug: dataset labels and the DEXTRAH controller/action
  frame are not grossly inverted at reset.
- The reset is offset from the nearest demo window, but the short replay still
  moves toward the cube. This means the reset offset alone does not explain the
  later close failure.
- The remaining evidence points to live-state/support mismatch accumulated
  during closed-loop approach: by the close windows in the full eval, nearest
  train rows are still pregrasp/open while the policy commands hard close.
- Next DP fixes should focus on observation conditioning and live-state
  support, closed-loop recovery behavior, reset/pregrasp alignment, and dataset
  coverage around recovery/close timing. No BC/RL scale-up is justified yet.

Next:
- Do not launch BC/RL scale-up.
- Run the next bounded diagnostic against the later failure window: teacher
  force a longer open-gripper approach to the dataset close boundary or reset
  the env closer to the nearest demo/pregrasp geometry, then compare whether
  hard-close timing and cube-relative geometry become valid.
- If longer teacher forcing follows demos but DP replan drifts, patch policy
  conditioning/data support; if dataset teacher forcing also drifts later,
  inspect reset alignment/controller gains/timing more deeply.

## 2026-06-11T14:57:38-07:00 - later-window open-gripper replay plan

Goal:
- Test the later failure window rather than only reset-time replay:
  if the env follows dataset/reference pose labels with the gripper forced open
  toward the dataset close boundary, does cube-relative geometry become valid
  before close, or does it drift out of support even under teacher forcing?

Hypothesis:
- If teacher-forced open-gripper dataset pose labels reach the demo grasp
  geometry near the close boundary while DP closed-loop does not, the bug is
  policy/live-state support and closed-loop recovery.
- If teacher-forced labels also fail to reach valid geometry by the close
  boundary, the remaining issue is reset alignment, controller timing/gains, or
  label-to-controller execution over longer horizons.

Change:
- Extend `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py` only:
  - add `dataset_open_t`, `dataset_open_t_plus_1`,
    `dataset_open_t_plus_7` modes, which use dataset pose labels but override
    gripper action to `+1.0` open;
  - log live nearest demo row/episode step/phase at every step;
  - log live cube-minus-EE, dataset cube-minus-EE, nearest-demo cube-minus-EE;
  - log EE/finger-to-cube distances, cube lift, gripper width/action,
    first negative/hard-close timing, and expected-vs-actual motion direction;
  - expand the PNG plot and report for later-window inspection.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `ab6e1d43f8edb70298620e7fd5bd479b466b5a1b`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`

Planned Command / Job:
- run_name:
  `franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`
- local/remote commit: pending, then deploy exact commit to
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- command:
  `RUN_NAME=franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt NUM_ENVS=1 STEPS=320 NUM_INFERENCE_STEPS=100 MODES=dataset_open_t_plus_7,dp_replan PRINT_INTERVAL=32 CAPTURE_VIDEO=False SEED=42 sbatch cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- expected comparison:
  - `dataset_open_t_plus_7`: open-gripper teacher-forced pose labels toward
    close boundary;
  - `dp_replan`: closed-loop DP replanning from the same reset/horizon.

Acceptance:
- Diagnostic clarity only. Fetch run artifacts, inspect report/CSV/plot,
  generate/open viz URLs, update worklog. No BC/RL scale-up.

## 2026-06-11T15:11:12-07:00 - open-to-close320 replay fetched and inspected

Goal:
- Complete the artifact loop for the later-window replay and decide whether it
  supports train/eval mismatch, support drift, or a solved BC prior.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- local_commit: `00d96eb4a3d65abaad1d3d7706ae52ed1f1dfa96`
- remote worktree commit for job:
  `00d96eb4a3d65abaad1d3d7706ae52ed1f1dfa96`
- official Diffusion Policy commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`

Command / Job:
- job_id: `1027759`
- run_name:
  `franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`
- Slurm status: `COMPLETED`, exit `0:0`, elapsed `00:06:07`,
  node `pool0-00037`.
- command:
  `RUN_NAME=franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt NUM_ENVS=1 STEPS=320 NUM_INFERENCE_STEPS=100 MODES=dataset_open_t_plus_7,dp_replan PRINT_INTERVAL=32 CAPTURE_VIDEO=False SEED=42 sbatch cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/replay_franka_cube_dp_actions_1027759.out`
- local inspection bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027759_open_to_close320_20260611_145800`
- viz-open:
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027759_open_to_close320_20260611_145800/later_window_support_comparison.png`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/replay_inspection_1027759_open_to_close320_20260611_145800/inspection_report.md`
  - `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_framefix_overfit2k_open_to_close320_20260611_145800/replay_motion.png`

Result:
- `dataset_open_t_plus_7`:
  - EE-to-cube improves from `0.2331 m` to `0.2119 m` by step 32,
    then plateaus at `0.2124 m` through step 320.
  - Finger-center-to-cube final is `0.2014 m`.
  - Nearest live phase never leaves `go_to_pre_grasp_pose`; final nearest
    demo distance is `0.3182`.
  - Gripper stays open (`+1.0`), final width `0.0800 m`.
  - First label negative/hard-close markers on the selected demo timeline are
    steps `297/310`, but live geometry is still pregrasp-like at those steps.
- `dp_replan`:
  - EE-to-cube improves from `0.2332 m` to `0.1463 m` by step 320.
  - Finger-center-to-cube final is `0.1730 m`.
  - Nearest live phase still stays `go_to_pre_grasp_pose`, but nearest demo
    distance grows to `1.1283`, indicating increasing out-of-support drift.
  - First negative/hard-close commands occur at steps `207/224`, while the
    selected dataset label close markers are steps `297/310`.
  - Final gripper width is `0.00080 m`, and final live cube-minus-EE is
    `[0.0309, -0.1198, -0.0779]`, not valid grasp geometry.
- Motion-direction cosines remain positive:
  `dataset_open_t_plus_7` mean `0.9735`; `dp_replan` mean `0.9182`.

Analysis:
- This is diagnostic but not a solved BC prior. It supports the live-state /
  support-drift hypothesis.
- Longer teacher-forced one-step relative dataset labels do not reach the true
  close-boundary cube-relative geometry from the current eval reset. That
  implicates reset alignment, controller timing/cadence, or selected
  demo-window semantics for relative labels.
- DP replan moves closer in raw EE distance, but the nearest-demo distance gets
  worse and it closes while still nearest to pregrasp/open rows. That preserves
  the train/eval mismatch concern from the bad video.
- Do not scale BC/RL or claim warm-start viability until a closed-loop video
  shows the policy approaching and closing near the cube within demo support.

Next:
- Patch the closed-loop eval wrapper to emit per-step nearest-demo support
  traces against the converted dataset.
- Launch a bounded video eval with the same framefix overfit2k checkpoint,
  `NUM_ENVS=1`, `NUM_STEPS=320`, `ACTION_CHUNK_STEPS=1`,
  `DEBUG_POLICY_TRACE_MAX_CALLS=320`, and dataset support trace enabled.
- Fetch metrics, policy trace, support trace, video, contact sheet, and a
  train/eval audit bundle; open the most useful artifacts with `viz-open`.

## 2026-06-11T15:18:40-07:00 - closed-loop support trace instrumentation

Goal:
- Make the next closed-loop eval bundle directly inspect train/eval support
  drift instead of relying only on policy-call traces or post-hoc replay.

Change:
- Updated `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
  - Added optional `--support_dataset` and `--support_trace_path`.
  - When enabled, every env step records nearest converted demo row, episode
    step, phase, nearest-demo distance, live and nearest cube-minus-EE,
    gripper width/action, EE/finger/cube metrics, history step gap, and
    per-phase nearest distances.
  - Writes both `support_trace.json` and `support_trace.csv` next to eval
    metrics/video.
- Updated `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.
  - Adds `SUPPORT_DATASET` and `SUPPORT_TRACE_PATH` environment variables.
  - Maps `/results/...` paths consistently with checkpoint paths.
  - Fails the job if support tracing was requested but JSON/CSV are missing.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `00d96eb4a3d65abaad1d3d7706ae52ed1f1dfa96`
- implementation_commit: `558f2464210bbda784844a7cf36affcc1ab540df`
- changed_files:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`

Result:
- Local syntax validation passed.

Next:
- Commit/push and deploy this exact commit to the agent-owned l401 worktree.
- Launch a bounded closed-loop video eval with support tracing:
  `NUM_STEPS=320`, `ACTION_CHUNK_STEPS=1`, `DEBUG_POLICY_TRACE_MAX_CALLS=320`,
  `CAPTURE_VIDEO=True`, same framefix overfit2k checkpoint, same dataset.

## 2026-06-11T15:19:30-07:00 - closed-loop support-drift video eval launch

Goal:
- Run the bounded closed-loop diagnostic required after the bad C video:
  verify whether live closed-loop rollout leaves demo support, when it closes,
  and whether closing happens near valid cube-relative geometry.

Hypothesis:
- If nearest-demo phase/distance stays pregrasp or grows while the policy
  closes, then the remaining issue is train/eval support drift or hidden eval
  mismatch, not BC readiness.
- If nearest-demo support progresses into grasp/close phases before hard close
  and the video shows coherent object-relative motion, then the previous
  failure was tied to missing trace/video instrumentation or an older bug.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- local_commit: `065e81e54665eb88bb2eb75bf6750dcef51f9be9`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `065e81e54665eb88bb2eb75bf6750dcef51f9be9`, detached clean.
- official Diffusion Policy commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`

Command / Job:
- job_id: `1027767`
- run_name:
  `franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- command:
  `RUN_NAME=franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt SUPPORT_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz NUM_ENVS=1 NUM_STEPS=320 VIDEO_LENGTH=320 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=1 DEBUG_POLICY_TRACE_MAX_CALLS=320 DEBUG_POLICY_TRACE_ENV_INDEX=0 PRINT_INTERVAL=32 CAPTURE_VIDEO=True SEED=42 sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027767.out`
- expected artifacts:
  - `metrics.json`
  - `policy_trace.json`
  - `support_trace.json`
  - `support_trace.csv`
  - `videos/*.mp4`

Acceptance:
- Fetch logs/results locally.
- Generate a viewer-ready bundle with support plots, trace/config audit,
  video contact sheet, and `viz-open` URLs.
- No BC/RL scale-up unless the closed-loop video and support trace are
  coherent; expected outcome is still diagnostic, not final BC readiness.

## 2026-06-11T15:45:00-07:00 - support-trace eval result and matched-demo reset plan

Goal:
- Record the completed closed-loop support trace and move to the next bounded
  root-cause diagnostic: demo-conditioned reset alignment.

Result:
- job_id: `1027767`
- run_name:
  `franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/eval_franka_cube_dp_policy_1027767.out`
- artifacts:
  - metrics:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/metrics.json`
  - policy trace:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/policy_trace.json`
  - support trace:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/support_trace.json`
  - support trace CSV:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/support_trace.csv`
  - video:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/videos/franka-cube-dp-policy-eval-step-0.mp4`
  - contact sheet:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/dp_supporttrace_contact_sheet.jpg`
- metrics:
  - `steps_completed=320`
  - `final_success_rate=0.0`, `window_success_rate=0.0`
  - `cube_lift_height.max=0.0`
  - `ee_to_cube_dist.final=0.14623`, `ee_to_cube_dist.min=0.14578`
  - `finger_center_to_cube_dist.final=0.17304`, `finger_center_to_cube_dist.min=0.16859`
  - `final_gripper_width=0.000805`
- support trace:
  - nearest-demo phase counts: `{"go_to_pre_grasp_pose": 320}`
  - nearest-demo distance: `0.353998 -> 1.129334`
  - first negative gripper step: `208`
  - first hard-close step: `225`

Analysis:
- This confirms the bug. The closed-loop eval hard-closes while still nearest
  to open/pregrasp support and never reaches close/grasp/lift support.
- The video/contact sheet shows the gripper away from the cube while closing.
- This is a train/eval support-drift mismatch, not a solved DP warm-start.
- Do not scale BC/RL or claim prior readiness.

Next:
- Implement a narrow demo-conditioned reset path in
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
- First diagnostic: after normal env reset, write the cube pose/goal from a
  selected converted demo episode row, keep the Franka at the normal reset
  pose, record the initial lowdim diff/support distance, then run the same
  bounded closed-loop video/support trace.
- Acceptance: if this eliminates support drift, root cause is reset/demo
  initial distribution/conditioning. If it does not, continue with tighter
  pregrasp robot alignment, history seeding, observation ordering, or policy
  rollout semantics.

Artifact URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027767_20260611_151930/support_drift_report.md`
- plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027767_20260611_151930/support_drift_trace.png`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/dp_supporttrace_contact_sheet.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_supporttrace_video320_20260611_151930/videos/franka-cube-dp-policy-eval-step-0.mp4`

## 2026-06-11T15:58:00-07:00 - demo-conditioned reset implementation

Goal:
- Test whether closed-loop support drift is caused by reset/demo alignment by
  starting the eval from a selected converted demo episode row.

Hypothesis:
- If writing the cube pose/goal from a selected demo row makes the initial
  lowdim observation match demo support and the closed-loop policy reaches
  close/grasp/lift support, the main bug is initial-state conditioning.
- If drift persists despite a near-zero reset support mismatch, then the next
  root cause is likely robot/pregrasp alignment, observation semantics,
  history seeding, or policy rollout semantics.

Change:
- Added `--demo_reset_dataset`, `--demo_reset_episode`, and
  `--demo_reset_step` to `eval_franka_cube_dp_policy.py`.
- The first implementation overwrites the cube root pose, cube initial pose,
  and lift goal from the selected converted lowdim row after normal reset. It
  deliberately keeps the Franka at the normal reset pose so episode-step `0`
  tests object/reset conditioning without adding an IK servo confound.
- Metrics now include a `demo_reset` block with target/live lowdim values and
  initial lowdim/cube/cube-minus-EE diffs.
- The l401 Slurm wrapper passes and validates `DEMO_RESET_DATASET`,
  `DEMO_RESET_EPISODE`, and `DEMO_RESET_STEP`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `de31be95c282ffe9156aeeab0c6ece8bd52f79ae`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`

Next:
- Commit/push and deploy to the agent-owned l401 worktree.
- Launch a bounded video/support-trace eval with:
  - `DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - `DEMO_RESET_EPISODE=24`
  - `DEMO_RESET_STEP=0`
  - `NUM_ENVS=1`, `NUM_STEPS=320`, `ACTION_CHUNK_STEPS=1`,
    `DEBUG_POLICY_TRACE_MAX_CALLS=320`, `CAPTURE_VIDEO=True`, `SEED=42`

## 2026-06-11T16:07:00-07:00 - demo-conditioned reset eval launch

Goal:
- Run the bounded matched-demo reset diagnostic requested after support-trace
  job `1027767`.

Hypothesis:
- Demo episode `24`, row `0` was the nearest support episode at the start of
  the failing support-trace run. If resetting the cube to this demo row makes
  the policy stay in support and close near the cube, the main problem is env
  reset/demo conditioning. If not, continue to robot/pregrasp alignment,
  history seeding, observation semantics, or policy rollout semantics.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `7913a82694f86bd21465145deca452b032070634`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - l401 GitHub fetch failed with `Permission denied (publickey)`; deployed
    the exact commit through a Git bundle, not rsync, into the agent-owned
    l401 worktree.
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `7913a82694f86bd21465145deca452b032070634`, detached clean.
- official Diffusion Policy commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`

Command / Job:
- job_id: `1027773`
- run_name:
  `franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- command:
  `RUN_NAME=franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt SUPPORT_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_EPISODE=24 DEMO_RESET_STEP=0 NUM_ENVS=1 NUM_STEPS=320 VIDEO_LENGTH=320 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=1 DEBUG_POLICY_TRACE_MAX_CALLS=320 DEBUG_POLICY_TRACE_ENV_INDEX=0 PRINT_INTERVAL=32 CAPTURE_VIDEO=True SEED=42 sbatch cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027773.out`
- expected artifacts:
  - `metrics.json`
  - `policy_trace.json`
  - `support_trace.json`
  - `support_trace.csv`
  - `videos/*.mp4`

Acceptance:
- Scheduler success is not enough. Fetch and inspect metrics, support trace,
  policy trace, video, contact sheet, and support-drift report.
- Pass for the hypothesis means the demo reset starts near the selected demo
  row and the rollout enters close/grasp/lift support before closing.
- Failure means support drift persists despite object/demo reset; next bounded
  diagnostic should tighten robot pregrasp alignment and/or history seeding.

## 2026-06-11T16:20:00-07:00 - demo-reset result and robot/demo replay plan

Goal:
- Finish the inspectable artifact bundle for eval job `1027773`, then run the
  next bounded diagnostic to separate robot/demo reset mismatch from
  action/controller semantics and learned support drift.

Hypothesis:
- The object-conditioned reset should have been sufficient if the main issue
  were cube pose/reset randomization. If it still fails while starting close to
  the selected demo lowdim row, then either the Franka robot/finger state is not
  aligned with the demo, the lowdim history/action semantics are still wrong,
  or the learned policy rolls out of support despite matched object state.
- The converted DP dataset stores 21D lowdim observations/actions, not Franka
  joint states, so exact robot joint reset from the dataset is not directly
  feasible. The next practical diagnostic is to replay selected demo labels
  from the selected demo episode/step after applying the same cube/object demo
  reset, rather than using whichever row is nearest after a normal reset.

Result:
- job `1027773` completed `0:0`.
- run:
  `franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700`
- demo reset worked for object state:
  - `cube_pos_l2_diff_env0=0.0`
  - `cube_minus_ee_l2_diff_env0=0.0108979`
  - `lowdim_linf_diff_env0=0.0099964`
- closed-loop behavior still fails:
  - `final_success_rate=0`, `window_success_rate=0`
  - `cube_lift_height max=0`
  - `final_gripper_width=0.0009156 m`
  - `EE-to-cube min/final=0.1314/0.1323 m`
  - `finger-center-to-cube min/final=0.1555/0.1619 m`
  - nearest-demo phase counts: `{"go_to_pre_grasp_pose": 320}`
  - nearest-demo distance: `0.1692 -> 0.9690`
  - first negative gripper step: `235`
  - first hard-close step: `249`
- This is still a closed-loop support-drift failure. Demo/object reset improves
  the initial support distance and raw EE distance versus job `1027767`, but it
  does not make the hand close near the cube or enter close/grasp/lift support.

Artifact bundle:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027773_demoreset_20260611_160700/closed_loop_support_report.md`
- plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027773_demoreset_20260611_160700/closed_loop_support_trace.png`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700/dp_demoreset_contact_sheet.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_framefix_overfit2k_demoreset_ep24s0_video320_20260611_160700/videos/franka-cube-dp-policy-eval-step-0.mp4`
- summary JSON:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027773_demoreset_20260611_160700/closed_loop_support_summary.json`
- key rows CSV:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/closed_loop_supporttrace_1027773_demoreset_20260611_160700/closed_loop_support_key_rows.csv`

Change Plan:
- Add a reusable offline report builder:
  `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`.
- Extend `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py` with:
  - explicit `--demo_reset_dataset/episode/step` support for the same cube
    demo reset used by eval;
  - explicit `--dataset_start_episode/step/row` support so replay labels come
    from a selected demo window instead of the nearest live row;
  - reset/selection metadata in replay JSON/report.
- Extend `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh` to pass those
  options from environment variables.

Validation / Launch Plan:
- Local cheap checks:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- Wrapper checks:
  `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- Commit/push, deploy exact commit to the agent-owned l401 worktree, then
  launch a bounded no-learning replay with:
  - `DEMO_RESET_DATASET=<framefix dataset>`
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`
  - modes `dataset_t,dataset_open_t_plus_7,dp_replan`
  - `STEPS=320`, `NUM_ENVS=1`, `CAPTURE_VIDEO=True`,
    `VIDEO_LENGTH=320`, `SEED=42`.

Acceptance:
- If selected demo labels from matched object/reset support reproduce approach
  and contact/lift, then the closed-loop DP failure is learned policy support
  drift or history/prediction semantics, not controller/action labels.
- If selected demo labels still stall or drift while direction cosines remain
  positive, the issue is reset/robot timing or the converted planned trajectory
  is not closed-loop executable from the actual Franka state.
- No BC/RL scale-up until one of those is resolved.

## 2026-06-11T16:40:00-07:00 - demo-reset fixed-label replay launch

Goal:
- Test robot/demo alignment with a bounded no-learning replay from the selected
  demo window, after applying the same demo-conditioned cube reset as job
  `1027773`.

Hypothesis:
- If selected demo labels from episode `24`, step `0` reproduce approach and
  contact from the demo-conditioned reset, then the action labels/controller are
  executable and the failing DP eval is learned closed-loop support drift or
  policy/history semantics.
- If selected demo labels still stall or close/lift away from contact, then the
  converted cuRobo/planned labels are not closed-loop executable from the live
  Franka reset even after object alignment; root cause shifts toward robot
  state/timing/reset mismatch or dataset trajectory semantics.

Change:
- Added `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py` for
  reusable fetched eval reports.
- Extended `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py` with
  demo-conditioned cube reset plus fixed dataset-start row/episode support.
- Extended `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh` with
  `DEMO_RESET_*` and `DATASET_START_*` environment variables.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `1425add15ce877a1897e1da5a70e636fc16d1f2a`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - l401 GitHub fetch still failed with `Permission denied (publickey)`;
    deployed the exact commit through Git bundle
    `franka-cube-dp-bc-warmstart-1425add.bundle`.
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `1425add15ce877a1897e1da5a70e636fc16d1f2a`, detached clean.
- official Diffusion Policy commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`

Command / Job:
- job_id: `1027792`
- run_name:
  `franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`
- command:
  `RUN_NAME=franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_EPISODE=24 DEMO_RESET_STEP=0 DATASET_START_EPISODE=24 DATASET_START_STEP=0 NUM_ENVS=1 STEPS=320 NUM_INFERENCE_STEPS=100 MODES=dataset_open_t_plus_7,dataset_t,dp_replan PRINT_INTERVAL=32 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-dp-replay-demoreset-fixedlabels SEED=42 sbatch cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027792.out`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `videos/*.mp4` for the first replay mode

Next:
- Monitor job `1027792`, fetch artifacts/logs, create a contact sheet and
  viz-open URLs, then record whether selected demo labels are executable from
  the matched object reset.

## 2026-06-11T16:58:00-07:00 - demo-reset fixed-label replay result and joint-reset plan

Goal:
- Close out job `1027792` with fetched artifacts and move to the next bounded
  robot-state/dataset-semantics diagnostic.

Result:
- status: failed behavior / useful diagnostic.
- job `1027792` completed `0:0`.
- run:
  `franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/replay_franka_cube_dp_actions_1027792.out`
- viewer URLs:
  - report: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_report.md`
  - plot: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_motion.png`
  - contact sheet: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/replay_contact_sheet.jpg`
  - video: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_demoreset_ep24s0_fixedlabels320_20260611_164000/videos/franka-cube-dp-replay-demoreset-fixedlabels-step-0.mp4`
- demo reset:
  - cube pose exactly matched episode `24`, step `0`
    (`cube_pos_l2_diff_env0=0`).
  - compact lowdim mismatch was small but nonzero
    (`cube_minus_ee_l2_diff_env0=0.0108979`,
    `lowdim_linf_diff_env0=0.0099964`).
  - `exact_robot_joint_reset_available=false` in the current lowdim NPZ, so
    the robot stayed at the task reset.
- mode summaries:
  - `dataset_open_t_plus_7`: final/min EE-cube `0.1861/0.1856 m`,
    final/min finger-center-cube `0.1757/0.1757 m`, gripper held open,
    nearest-live phase remained `go_to_pre_grasp_pose`, nearest distance
    `0.166 -> 0.257`, mean direction cosine `0.9735`.
  - `dataset_t`: final/min EE-cube `0.1848/0.1843 m`,
    final/min finger-center-cube `0.1746/0.1746 m`, first negative/hard close
    at steps `297/310`, nearest-live phase remained `go_to_pre_grasp_pose`,
    nearest distance `0.166 -> 0.597`, mean direction cosine `0.9706`.
  - `dp_replan`: final/min EE-cube `0.1323/0.1314 m`,
    final/min finger-center-cube `0.1619/0.1555 m`, first negative/hard close
    at steps `234/248`, nearest-live phase remained `go_to_pre_grasp_pose`,
    nearest distance `0.166 -> 0.968`, mean direction cosine `0.9083`.

Analysis:
- Object reset alone is not enough. Even fixed dataset labels selected from
  the same episode step do not reach contact from the live robot reset.
- The high expected-vs-actual motion direction cosines mean the DEXTRAH
  controller is broadly following the sign/frame of the executed labels at this
  reset. The remaining mismatch is not simply an action sign flip.
- The selected episode's first action is near zero because episode step `0`
  in the converted trajectory is a cuRobo task-space frame already at the
  source trajectory start, not necessarily the live Isaac task reset. Replaying
  it from the task reset therefore tests the wrong robot state.
- Raw source recovery is feasible: metadata maps episode `24` to
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`,
  and that file contains frame-by-frame `joint_position` with 8 values.
  The converted DP NPZ only stores `obs`, `action`, `episode_ends`, and
  `phase_ids`, so joint state must be recovered from the source trajectory or
  added to future converted datasets.

Change Plan:
- Extend `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py` with an
  optional raw trajectory source reset:
  `--demo_reset_trajectory_json <trajectory.json>`.
- When supplied, load the selected frame's `joint_position` and reset the
  Franka articulation joints, position targets, IK controller state, and
  object pose before replay. Report lowdim, cube-minus-EE, joint, and gripper
  mismatch after reset.
- Keep the existing lowdim demo reset as a fallback and keep no-learning replay
  modes unchanged.
- Add a small offline action-semantics audit artifact for the selected episode
  that reports action schema, phase windows, near-zero/clip rates, t->t+1
  action reconstruction error, and the frame/source metadata.

Validation / Launch Plan:
- Local checks:
  `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- Wrapper check:
  `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- Commit/push/deploy exact commit to the agent-owned l401 worktree.
- Launch a bounded one-env replay with:
  - `DEMO_RESET_TRAJECTORY_JSON=/home/lzha/code/.codex-external/.../seed24/trajectory.json`
    mapped to the cluster-visible `/results/.../seed24/trajectory.json`
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`
  - modes `dataset_open_t_plus_7,dataset_t,dp_replan`
  - `STEPS=320`, `NUM_ENVS=1`, `CAPTURE_VIDEO=True`, `SEED=42`.

Acceptance:
- If exact source-joint reset makes fixed labels reach approach/contact, the
  immediate blocker is robot-state/demo reset alignment and future DP data must
  include reproducible robot initial states or an env reset/settle wrapper.
- If exact source-joint reset still stalls far from contact, the next suspect is
  trajectory/action label semantics: cuRobo waypoints may not be one-step
  executable by the DEXTRAH relative-IK controller at the policy control rate,
  or the replay is applying the wrong temporal offset.
- No BC/RL scale-up until this is resolved.

## 2026-06-11T17:09:00-07:00 - source-joint reset implementation and action audit

Goal:
- Implement the exact source-joint reset replay diagnostic requested after job
  `1027792`, and produce an offline action-semantics audit before launching
  the next bounded cluster replay.

Hypothesis:
- The previous replay failed because the cube matched the demo but the robot
  remained at the task reset. If we reset Franka arm/finger state from the raw
  cuRobo source trajectory, fixed demo labels should become a fair test of
  whether planned labels reach approach/contact.

Change:
- `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
  - added `--demo_reset_trajectory_json`.
  - loads selected raw source frame `joint_position`.
  - maps 8D raw Franka state as 7 arm joints plus one finger joint repeated
    onto both Isaac finger joints.
  - writes joint state/targets, resets IK controller, then writes cube
    pose/goal and reports post-reset lowdim/joint mismatch.
- `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
  - added `DEMO_RESET_TRAJECTORY_JSON` path handling, validation, logging, and
    CLI forwarding.
- `dextrah_lab/offline_dp_bc/audit_dataset_action_semantics.py`
  - added a reusable offline audit for selected converted lowdim episodes.
  - reports source frame metadata, action convention, phase windows,
    near-zero/clip rates, and action t-to-t+1 reconstruction error.

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/audit_dataset_action_semantics.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`

Action-semantics audit:
- command:
  `PYTHONPATH=/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.audit_dataset_action_semantics --dataset /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz --episode 24 --selected_step 0 --source_trajectory_json /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json --output_dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dataset_action_semantics_ep24_step0_20260611_170900`
- output_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dataset_action_semantics_ep24_step0_20260611_170900`
- viewer URLs:
  - report: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dataset_action_semantics_ep24_step0_20260611_170900/dataset_action_semantics_report.md`
  - plot: `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/dataset_action_semantics_ep24_step0_20260611_170900/dataset_action_semantics.png`
- key evidence:
  - selected episode `24`, step `0`, phase `go_to_pre_grasp_pose`.
  - selected action:
    `[0, 0, 0, 1.16e-7, -3.58e-13, -1.74e-7, 1]`.
  - raw source frame `0` has `joint_position_dim=8`.
  - pose-action near-zero rate across episode: `0.4972`; clipped pose-action
    rate: `0.0`.
  - one-step reconstruction error is numerical precision only:
    position mean/max `8.63e-12 / 4.66e-10`, rotation mean/max
    `2.12e-11 / 9.88e-10`.
  - first negative/hard-close gripper label steps: `297/310`.

Analysis:
- Converted labels are normalized relative DEXTRAH actions:
  action `t` reconstructs dataset pose `t+1` under
  `apply_normalized_action_to_world_pose`. They are not absolute target poses.
- The near-zero first label is explained by identical or near-identical source
  waypoints at the trajectory start. Replaying that label from task reset holds
  the task reset state, which invalidates `1027792` as a fixed-label robot
  execution test.
- The exact source-joint reset cluster replay is now the right bounded test of
  whether fixed labels reach approach/contact from a matched robot state.

Next:
- Commit/push this implementation and worklog.
- Deploy the exact commit to l401.
- Launch the bounded source-joint replay with episode `24`, step `0`, modes
  `dataset_open_t_plus_7,dataset_t,dp_replan`, 320 steps, one env, video on.

## 2026-06-11T17:14:00-07:00 - source-joint fixed-label replay launch

Goal:
- Test whether fixed cuRobo/demo labels reach approach/contact when both cube
  pose and Franka robot joint state are initialized from the selected raw
  source trajectory frame.

Hypothesis:
- If this replay works, the closed-loop DP failure is primarily a reset/robot
  state alignment issue. If it still fails, then the problem is deeper in
  trajectory/action label semantics or controller execution timing.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit:
  `ecedc9720fa31be7427732a9e08450b0f595a230`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - l401 GitHub fetch is still blocked by SSH auth, so deployed via Git bundle
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-ecedc97.bundle`.
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `ecedc9720fa31be7427732a9e08450b0f595a230`, detached clean.
- official Diffusion Policy commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`

Artifact staging:
- raw source trajectory for episode `24` was copied as an untracked artifact to:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`
- container-visible path:
  `/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`

Command / Job:
- job_id: `1027846`
- run_name:
  `franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`
- command:
  `RUN_NAME=franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json DEMO_RESET_EPISODE=24 DEMO_RESET_STEP=0 DATASET_START_EPISODE=24 DATASET_START_STEP=0 NUM_ENVS=1 STEPS=320 NUM_INFERENCE_STEPS=100 MODES=dataset_open_t_plus_7,dataset_t,dp_replan PRINT_INTERVAL=32 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-dp-replay-sourcejoint SEED=42 sbatch cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027846.out`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- source-joint reset metadata in `demo_reset`
- video/contact sheet after fetch

Next:
- Monitor job `1027846`, fetch artifacts, generate contact sheet / viz-open
  URLs, inspect metrics and video, then decide whether fixed labels reach
  contact from matched robot state.

## 2026-06-11T16:11:42-07:00 - source-joint replay result and action-realization pivot

Goal:
- Resolve whether the DP drift/far-close failure is due to reset mismatch or a
  deeper action/controller semantics mismatch.

Result:
- status: failed as a behavior replay; useful as a root-cause diagnostic.
- job_id: `1027846`
- run_name:
  `franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/replay_franka_cube_dp_actions_1027846.out`
- viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_motion.png`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/videos/franka-cube-dp-replay-sourcejoint-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/replay_contact_sheet.jpg`
  - focused action-realization report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/sourcejoint_action_realization_existing1027846.md`
  - focused action-realization plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_ep24s0_fixedlabels320_20260611_171400/sourcejoint_action_realization_existing1027846.png`

Key evidence:
- Exact reset is available and was applied:
  `exact_robot_joint_reset_available=true`,
  `joint_linf_diff_after_write_env0=0`,
  `lowdim_linf_diff_env0=5.7e-7`,
  `cube_minus_ee_l2_diff_env0=3.0e-7`,
  `ee_pos_l2_diff_env0=3.0e-7`.
- `dataset_open_t_plus_7` final/min EE-to-cube:
  `0.1902 / 0.1900 m`; final finger-center-to-cube `0.1802 m`;
  nearest live phase remains `go_to_pre_grasp_pose`.
- `dataset_t` final/min EE-to-cube:
  `0.1889 / 0.1887 m`; final finger-center-to-cube `0.1791 m`;
  hard close occurs at step `310` while far from the cube.
- `dp_replan` final/min EE-to-cube:
  `0.1276 / 0.1272 m`; final finger-center-to-cube `0.1613 m`;
  nearest-demo distance grows to `0.6944`; first negative gripper action only
  appears at step `316`.
- Source-joint reset video/contact sheet still show the hand away from the
  cube. The video currently records the first mode only because the wrapper
  starts video at global step 0.

Analysis:
- Reset mismatch is ruled out for episode `24`, step `0`: the robot state,
  cube state, lowdim observation, and cube-minus-EE all match the converted
  demo to numerical precision.
- The fixed labels mostly point in the expected direction, but the realized EE
  displacement per env step is much smaller than the action-implied
  kinematic target. Example rows in the focused report show 6-13 mm commanded
  translation with roughly 0.3-1.2 mm realized translation during early
  approach.
- The current converted labels are therefore not behaving as executable
  one-env-step relative IK commands under the live DEXTRAH controller. The
  likely root is controller/action timing or target semantics, not BC capacity.
- No BC/RL scale-up is valid until this controller/action-realization mismatch
  is explained and patched.

Next:
- Patch the replay diagnostic to log a first-class action-semantics audit:
  action scales, root/action frame, gripper target width mapping, selected
  label row/offset, expected kinematic EE target, actual EE delta,
  actual/expected translation and rotation norms, realization ratios, target
  errors, and gripper width errors.
- Fix multi-mode video triggering so bounded replay diagnostics can produce a
  labeled video/contact sheet per mode window.
- Run a small source-joint reset replay with the patched audit before any
  further training.

## 2026-06-11T16:16:00-07:00 - source-joint action-realization audit launch

Goal:
- Compare dataset action labels and DP first actions to actual live EE motion
  under the DEXTRAH Isaac controller from an exact source-joint/cube reset.

Hypothesis:
- The source-joint replay failure is caused by action realization semantics:
  converted labels encode one-step kinematic EE deltas, but the live
  DifferentialIK + PD controller realizes only a fraction of those deltas per
  environment step.

Change:
- Added detailed row-level replay audit fields:
  action scale, root/action frame quaternion, executed label row/offset,
  expected target EE pose, actual EE delta, actual/expected translation and
  rotation norms, realization ratios, target errors, dataset-next errors, and
  gripper target width errors.
- Changed replay video trigger to start a video every `VIDEO_LENGTH` global
  steps so multi-mode bounded diagnostics can capture separate mode windows.

Version Control:
- implementation_commit:
  `5281c9847c0615705cf362d92a47aa37bb0fee68`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - deployed to l401 via Git bundle
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-5281c98.bundle`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `5281c9847c0615705cf362d92a47aa37bb0fee68`, detached clean.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py dextrah_lab/offline_dp_bc/audit_dataset_action_semantics.py dextrah_lab/offline_dp_bc/action_conversion.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Command / Job:
- job_id: `1027855`
- run_name:
  `franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`
- command:
  `RUN_NAME=franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600 CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json DEMO_RESET_EPISODE=24 DEMO_RESET_STEP=0 DATASET_START_EPISODE=24 DATASET_START_STEP=0 NUM_ENVS=1 STEPS=96 NUM_INFERENCE_STEPS=100 MODES=dataset_t,dataset_t_plus_7,dp_replan PRINT_INTERVAL=16 CAPTURE_VIDEO=True VIDEO_LENGTH=96 VIDEO_NAME_PREFIX=franka-cube-dp-replay-actionaudit SEED=42 sbatch --parsable cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`
- remote log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027855.out`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `action_realization_audit.png`
- per-mode video windows if `RecordVideo` starts as intended
- local contact sheet after fetch

Next:
- Monitor `1027855`, fetch outputs, create/open viewer URLs, inspect action
  realization ratios and target errors, then patch conversion/control timing
  rather than training if the under-realization hypothesis holds.

## 2026-06-11T16:20:20-07:00 - source-joint action-realization audit result

Goal:
- Quantify whether converted dataset/DP relative EE commands are realized by
  the live DEXTRAH Franka DifferentialIK + PD controller at the expected
  per-env-step magnitude.

Result:
- status: completed, diagnostic failure confirms action under-realization.
- job_id: `1027855`
- run_name:
  `franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`
- scheduler: `COMPLETED 0:0`, elapsed `00:03:33`, node `pool0-00032`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_logs/l401/replay_franka_cube_dp_actions_1027855.out`
- viewer URLs:
  - filtered report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/action_realization_audit_filtered_report.md`
  - official replay report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/replay_report.md`
  - action audit plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/action_realization_audit.png`
  - motion plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/replay_motion.png`
  - `dataset_t` video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-0.mp4`
  - `dataset_t_plus_7` video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-96.mp4`
  - `dp_replan` video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/videos/franka-cube-dp-replay-actionaudit-step-192.mp4`
  - `dp_replan` contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_actionaudit96_20260611_161600/franka-cube-dp-replay-actionaudit-step-192_contact_sheet.jpg`

Key evidence:
- Reset still matches exactly:
  `joint_linf_diff_after_write_env0=0`,
  `lowdim_linf_diff_env0=5.7e-7`,
  `cube_minus_ee_l2_diff_env0=3.0e-7`.
- Controller/config convention audit passes:
  task and converter both use pose scales
  `[0.06, 0.06, 0.045, 0.25, 0.25, 0.30]`,
  root/action frame is the expected 180-degree yaw quaternion, and gripper
  mapping is `-1` close / `+1` open.
- `dataset_t`:
  final/min EE-to-cube `0.1887 / 0.1887 m`, final finger-center-to-cube
  `0.1815 m`, nearest-live phase remains `go_to_pre_grasp_pose`,
  filtered median xyz realization ratio about `0.093`.
- `dataset_t_plus_7`:
  final/min EE-to-cube `0.1900 / 0.1900 m`, final finger-center-to-cube
  `0.1826 m`, nearest-live phase remains `go_to_pre_grasp_pose`,
  filtered median xyz realization ratio about `0.095`.
- `dp_replan`:
  final/min EE-to-cube `0.1657 / 0.1657 m`, final finger-center-to-cube
  `0.1679 m`, nearest-live phase remains `go_to_pre_grasp_pose`,
  median xyz realization ratio about `0.085`.
- Representative nonzero rows:
  - `dataset_t` step 16 commands `0.01305 m` but realizes
    `0.00118 m` (`ratio=0.090`).
  - `dataset_t_plus_7` step 16 commands `0.01206 m` but realizes
    `0.00115 m` (`ratio=0.095`).
  - `dp_replan` step 32 commands `0.01051 m` but realizes
    `0.00074 m` (`ratio=0.071`).

Analysis:
- This is not a sign/frame bug: direction cosines are mostly high and the
  action/root frame audit matches the converter.
- This is not a gripper convention bug in the approach window: open commands
  keep gripper width near `0.08 m`.
- The bug is temporal/controller semantics: converted labels assume a
  normalized relative EE command reaches the next cuRobo waypoint in one
  1/60-second env step, while the live DifferentialIK + joint PD stack realizes
  only about 8-10% of that translation per env step. The replay reaches hold
  labels while still far from the cube.
- No BC/RL scale-up is valid until dataset conversion or replay/control timing
  is fixed.

Next:
- Add replay-only compensation knobs: pose-action multiplier and action-repeat
  / hold count.
- Run a bounded exact-source-reset sweep with multipliers `3`, `6`, and `10`
  at repeat `1`, short 96-160 step windows, per-mode videos, and
  `action_realization_audit.png`.
- Acceptance is diagnostic only: reduce action realization error and EE-cube
  distance toward the source trajectory without excessive clipping,
  instability, or gripper/control convention regressions.

## 2026-06-11T16:23:00-07:00 - controller compensation sweep launch

Goal:
- Test whether replay-only pose-action scaling can make converted cuRobo
  labels match live DEXTRAH controller EE path magnitude from exact
  source-joint reset.

Hypothesis:
- If the problem is controller under-realization, multiplying the first six
  pose action dimensions should raise the actual/expected realization ratio
  and reduce EE-to-cube distance without changing gripper semantics. Excessive
  multipliers should reveal clipping or instability.

Change:
- Added diagnostic-only `--pose_action_multiplier`.
- Added diagnostic-only `--action_repeat`, with per-env-step observation
  history updates even during held-action repeats.
- Added wrapper variables `POSE_ACTION_MULTIPLIER` and `ACTION_REPEAT`.
- Report now includes multiplier, repeat, mean/max pose clip fraction, and
  action-realization audit fields.

Version Control:
- implementation_commit:
  `3aa54155ec1e15b333ff8e40cb00f4b33b46eef7`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - deployed to l401 via Git bundle
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-3aa5415.bundle`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `3aa54155ec1e15b333ff8e40cb00f4b33b46eef7`, detached clean.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Command / Jobs:
- shared settings:
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`
  - `MODES=dataset_t,dataset_t_plus_7`
  - `STEPS=128`, `ACTION_REPEAT=1`, `NUM_ENVS=1`
  - `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=128`
  - checkpoint:
    `/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt`
  - dataset:
    `/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
- multiplier `3`:
  - job_id: `1027862`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_comp_m3_r1_128_20260611_162300`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027862.out`
- multiplier `6`:
  - job_id: `1027863`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_comp_m6_r1_128_20260611_162300`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027863.out`
- multiplier `10`:
  - job_id: `1027864`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_comp_m10_r1_128_20260611_162300`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027864.out`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `action_realization_audit.png`
- per-mode videos and local contact sheets after fetch

Next:
- Monitor jobs `1027862`, `1027863`, `1027864`, fetch artifacts, create/open
  viewer URLs, compare filtered realization ratio, EE/finger distance,
  nearest-demo support, and clip fractions, then decide whether to patch
  conversion timing or run an action-repeat sweep.

## 2026-06-11T16:35:00-07:00 - controller compensation sweep result

Goal:
- Inspect jobs `1027862`, `1027863`, and `1027864` and decide whether
  replay-only action multiplication is a plausible fix for the converted
  cuRobo label/controller mismatch.

Result:
- status: failed as a fix, useful as a diagnostic.
- All jobs completed `0:0` and artifacts were fetched locally.
- Local report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/controller_compensation_20260611_162300/controller_compensation_report.md`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/controller_compensation_20260611_162300/controller_compensation_report.md`
  - dataset_t_plus_7 plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/controller_compensation_20260611_162300/controller_compensation_dataset_t_plus_7.png`
  - m10 step128 video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_comp_m10_r1_128_20260611_162300/videos/franka-cube-dp-replay-comp-m10-r1-step-128.mp4`

Key evidence:
- m3:
  final EE-to-cube about `0.147-0.150 m`, median nonzero xyz realization
  ratio about `0.081-0.086`, no clipping, nearest-demo support distance about
  `0.49-0.50`.
- m6:
  final EE-to-cube about `0.106-0.108 m`, median realization ratio about
  `0.079-0.085`, first clipping at steps `7-14`, support distance about
  `0.84-0.87`.
- m10:
  minimum EE-to-cube improved to `0.074-0.085 m`, final about `0.101-0.104 m`,
  but max pose clip fraction reached `0.5`, support distance reached `0.91`
  for `dataset_t` and pathological `>150` for `dataset_t_plus_7`.
- No run produces a valid close/contact/lift trajectory. Gripper stays open in
  the fixed-label replay modes, as expected for the selected approach labels.

Analysis:
- Action multiplication is not the real fix. It can reduce raw distance, but
  it does not change the core observation that actual one-step EE motion is
  only about `8-9%` of the label-implied target, and high multipliers create
  clipping/support drift instead of a coherent teacher trajectory.
- The remaining likely root cause is controller/action temporal semantics:
  converted labels are one-step relative target deltas between cuRobo waypoints,
  while DEXTRAH applies them through a DifferentialIK target plus joint-level
  controller over only one env step.

Next:
- Stop treating label scaling as the main path.
- Inspect the DEXTRAH action application and converter end-to-end:
  env decimation, `pre_physics_step`, DifferentialIK command semantics,
  root/body/end-effector frames, normalized-vs-scaled actions, and whether
  dataset labels should be held/integrated over multiple env steps.
- Run only one or two bounded replay diagnostics with videos/plots after a
  narrow semantic patch.

## 2026-06-11T16:36:00-07:00 - live residual target replay plan

Goal:
- Answer why source labels with expected one-step EE deltas of roughly
  `6-13 mm` realize only `0.5-1 mm` in the Isaac controller, without launching
  any BC/RL scale-up.

Hypothesis:
- Converted labels are normalized relative deltas between source cuRobo/FK
  waypoints at 60 Hz. DEXTRAH applies those deltas as DifferentialIK relative
  target-pose setpoints, then joint PD only partially moves toward the setpoint
  over `decimation=2` physics steps. If this is true, recomputing a residual
  action from the live EE pose to a dataset target row every env step should
  track source waypoints better than replaying stale source one-step labels.

Planned Change:
- Add replay-only modes to
  `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`:
  `dataset_target_t_plus_1` and `dataset_target_t_plus_7`.
- These modes compute the normalized action from the current live lowdim EE
  pose/quaternion to the target dataset row's EE pose/quaternion at each env
  step, using the same DEXTRAH frame/scale conversion as the dataset
  converter, and retain the target row's gripper command.
- Extend CSV/JSON/report/plots with target-row tracking error before/after,
  target row phase/episode step, and clip fraction.

Validation Before Cluster:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Planned Cluster Diagnostic:
- Deploy the exact committed patch to the agent-owned l401 worktree.
- Launch a bounded source-joint reset replay with:
  `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`,
  `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`,
  `STEPS=96`, `NUM_ENVS=1`, `ACTION_REPEAT=1`,
  `POSE_ACTION_MULTIPLIER=1`, and modes
  `dataset_t,dataset_target_t_plus_1,dataset_target_t_plus_7`.
- Fetch logs, CSV/JSON/report, plots, videos/contact sheets, open the most
  useful artifacts with `viz-open`, and update this worklog.

Acceptance:
- Diagnostic clarity only. If residual-target modes track the source path
  substantially better, the issue is open-loop/temporal target semantics in the
  converted labels. If they still under-realize, inspect controller gains,
  decimation, target frame, and waypoint cadence before any training.

## 2026-06-11T16:38:00-07:00 - live residual target replay launch

Goal:
- Run the bounded residual-target replay diagnostic on l401 with exact
  source-joint reset and source cube pose reset.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `ce8d94ee4fc1b96f6943264e47edb93cc7bc7736`
- implementation_commit:
  `b9a6009a798d7d39642fd8960049454da207294b`
- changed_files:
  - `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- push/pull:
  - pushed to `origin/codex/franka-cube-diffusion-policy-bc`
  - remote GitHub fetch still blocked by SSH publickey on l401, so deployed
    via Git bundle:
    `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-b9a6009.bundle`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `b9a6009a798d7d39642fd8960049454da207294b`, detached clean.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Command / Job:
- job_id: `1027867`
- run_name:
  `franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_163800`
- launch command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_163800,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt,DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,DEMO_RESET_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json,DEMO_RESET_EPISODE=24,DEMO_RESET_STEP=0,DATASET_START_EPISODE=24,DATASET_START_STEP=0,MODES=dataset_t\\,dataset_target_t_plus_1\\,dataset_target_t_plus_7,STEPS=96,NUM_ENVS=1,ACTION_REPEAT=1,POSE_ACTION_MULTIPLIER=1,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=96,VIDEO_NAME_PREFIX=franka-cube-dp-replay-targetresidual,PRINT_INTERVAL=16,NUM_INFERENCE_STEPS=100,SEED=42 cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_163800`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027867.out`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `action_realization_audit.png`
- per-mode mp4 files under `videos/`

Next:
- Monitor job `1027867`, fetch artifacts locally, generate/open viewer URLs,
  and compare whether residual-target modes reduce tracking error and
  EE-to-cube distance without pathological clipping/support drift.

Update:
- `1027867` was canceled before completion because the `sbatch --export`
  command parsed the comma-separated `MODES` value incorrectly. The replay log
  showed the script received only `--mode dataset_t`, so this run could not
  answer the residual-target hypothesis. Do not use this run as residual-target
  evidence.
- Next launch will use a remote-shell `export MODES=...; sbatch --export=ALL`
  pattern so comma-separated modes are preserved.

## 2026-06-11T16:40:00-07:00 - action repeat temporal semantics plan

Goal:
- Run the bounded action-repeat/hold diagnostic requested by the orchestrator:
  determine whether temporal resampling/action holding can make source labels
  follow the teacher EE geometry, versus needing converter/controller semantic
  changes.

Hypothesis:
- If the DEXTRAH controller simply needs more env steps per source waypoint,
  holding each normalized source action for `2`, `4`, or `8` env steps should
  improve actual EE path magnitude and reduce EE-to-cube/source waypoint error
  without high clipping or leaving demo support.
- If repeat/hold only reduces raw distance while nearest-demo support worsens
  or tracking remains far from source geometry, then the fix is not a simple
  action-repeat bridge; we need a converter/controller semantic patch or a
  controller-rollout dataset.

Planned Jobs:
- Exact source-joint and cube reset at episode `24`, step `0`.
- Fixed label start episode `24`, step `0`.
- One mode per job: `dataset_t`.
- `POSE_ACTION_MULTIPLIER=1`, `CLIP_ACTIONS=1.0`, `NUM_ENVS=1`,
  `STEPS=96`, video enabled.
- Sweep `ACTION_REPEAT=2`, `4`, `8`.

Acceptance:
- Diagnostic clarity only. A useful repeat setting must follow teacher
  geometry without pathological clipping/support drift, not merely reduce final
  EE-to-cube distance.

Expected artifacts per job:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `action_realization_audit.png`
- per-job mp4/contact sheet after local fetch.

Launch:
- implementation_commit:
  `12c44c51fa49407ec3bec7c04c206f87ae1bb1d0`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `12c44c51fa49407ec3bec7c04c206f87ae1bb1d0`, detached clean.
- shared settings:
  - dataset:
    `/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - checkpoint:
    `/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt`
  - source trajectory:
    `/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`
  - `MODES=dataset_t`, `STEPS=96`, `NUM_ENVS=1`
  - `POSE_ACTION_MULTIPLIER=1`, `CLIP_ACTIONS=1.0`
  - `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=96`
- `ACTION_REPEAT=2`:
  - job_id: `1027871`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_repeat2_dataset_t_96_20260611_163750`
  - remote run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_repeat2_dataset_t_96_20260611_163750`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027871.out`
- `ACTION_REPEAT=4`:
  - job_id: `1027872`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_repeat4_dataset_t_96_20260611_163750`
  - remote run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_repeat4_dataset_t_96_20260611_163750`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027872.out`
- `ACTION_REPEAT=8`:
  - job_id: `1027873`
  - run_name:
    `franka_cube_dp_replay_sourcejoint_repeat8_dataset_t_96_20260611_163750`
  - remote run_dir:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_repeat8_dataset_t_96_20260611_163750`
  - log:
    `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027873.out`

Next:
- Monitor jobs `1027871`-`1027873`.
- Fetch completed artifacts, generate contact sheets and a comparison report,
  open viewer URLs, and decide whether repeat/hold is a viable bridge or still
  leaves the policy/demo outside support.

Result:
- status: failed as a fix, useful diagnostic.
- Jobs `1027871`, `1027872`, and `1027873` completed with `DP_REPLAY_DONE`.
- Artifacts were fetched locally.
- Local comparison bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_repeat_temporal_20260611_163750/`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_repeat_temporal_20260611_163750/action_repeat_temporal_report.md`
  - combined plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_repeat_temporal_20260611_163750/action_repeat_temporal_comparison.png`
  - repeat 4 contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/action_repeat_temporal_20260611_163750/repeat4_contact_sheet.jpg`
  - repeat 4 video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_repeat4_dataset_t_96_20260611_163750/videos/franka-cube-dp-replay-repeat4-step-0.mp4`

Metrics:

| repeat | final EE-cube | final finger-cube | final support dist | max support dist | median nonzero xyz realization | median next-row EE error | max clip | verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | `0.1672` | `0.1659` | `0.331` | `0.331` | `0.094` | `0.1781` | `0.000` | advances labels to hold rows while live EE is still far, then stalls |
| 4 | `0.1449` | `0.1488` | `0.337` | `0.337` | `0.093` | `0.0466` | `0.000` | closest raw distance, but support drift grows and visual remains offset |
| 8 | `0.1713` | `0.1667` | `0.162` | `0.162` | `0.094` | `0.0059` | `0.000` | best source-row timing/support, but progresses too slowly and stays far |

Analysis:
- Action holding/resampling alone is not a useful bridge. It changes how fast
  the source label window advances, but it does not change the controller's
  actual-vs-expected EE delta ratio, which remains about `0.09`.
- Repeat 4 reduces raw EE-cube distance most, but the nearest-demo support
  distance climbs to about `0.337`, and the contact sheet/video still show the
  hand offset from the cube.
- Repeat 8 best matches the source row timing over 96 env steps, but only
  because it remains in early approach rows; it still does not approach contact.

Next:
- Rerun the residual-target diagnostic correctly with comma-safe remote-shell
  environment export:
  `MODES=dataset_t,dataset_target_t_plus_1,dataset_target_t_plus_7`,
  exact source-joint reset, `STEPS=96`, video enabled.
- If residual-target modes reduce tracking error and follow source geometry
  without clipping/support drift, the fix is a live-residual/controller-aware
  label conversion. If they fail, move to a controller-rollout dataset or a
  more direct controller semantic patch before any BC/RL training.

## 2026-06-11T16:43:00-07:00 - corrected residual-target replay launch

Goal:
- Test the residual-target hypothesis that was not exercised by canceled job
  `1027867`, using comma-safe environment export.

Version Control:
- implementation_commit:
  `67a3346f812b6419f272712a6f81deb04370b232`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `67a3346f812b6419f272712a6f81deb04370b232`, detached clean.
- deployment:
  Git bundle
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-67a3346.bundle`

Command / Job:
- job_id: `1027877`
- run_name:
  `franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027877.out`
- key settings:
  - `MODES=dataset_t,dataset_target_t_plus_1,dataset_target_t_plus_7`
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=0`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=0`
  - `STEPS=96`, `ACTION_REPEAT=1`, `POSE_ACTION_MULTIPLIER=1`
  - `CLIP_ACTIONS=1.0`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=96`

Expected artifacts:
- `replay_summary.json`
- `replay_steps.csv`
- `replay_report.md`
- `replay_motion.png`
- `action_realization_audit.png`
- per-mode mp4 files under `videos/`

Next:
- Monitor job `1027877`, verify the log includes all three modes, then fetch
  artifacts and compare residual target tracking error, support drift, clip
  fraction, and video/contact sheets.

Result:
- status: failed acceptance, useful diagnostic.
- Job `1027877` completed with `DP_REPLAY_DONE`.
- The log confirmed all three modes were passed correctly:
  `dataset_t`, `dataset_target_t_plus_1`, and `dataset_target_t_plus_7`.
- Artifacts were fetched locally.
- Local run dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300/`
- Local report bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/residual_target_1027877_20260611_164300/`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/residual_target_1027877_20260611_164300/residual_target_report.md`
  - combined plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/residual_target_1027877_20260611_164300/residual_target_comparison.png`
  - `dataset_target_t_plus_1` contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reports/residual_target_1027877_20260611_164300/dataset_target_t_plus_1_contact_sheet.jpg`
  - `dataset_target_t_plus_1` video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_targetresidual_ep24s0_96_20260611_164300/videos/franka-cube-dp-replay-targetresidual-step-96.mp4`

Metrics:

| mode | final EE-cube | min EE-cube | min step | final finger-cube | final support | max support | median nonzero xyz realization | mean clip frac | max clip frac | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dataset_t` | `0.1887` | `0.1887` | `45` | `0.1815` | `0.168` | `0.181` | `0.093` | `0.000` | `0.000` | baseline still stalls when source labels become near-zero |
| `dataset_target_t_plus_1` | `0.1752` | `0.0764` | `33` | `0.2199` | `0.035` | `0.564` | `0.080` | `0.090` | `0.333` | transiently approaches, but clips/support spikes and drifts back |
| `dataset_target_t_plus_7` | `0.1756` | `0.0762` | `28` | `0.2203` | `0.034` | `0.566` | `0.080` | `0.090` | `0.333` | more aggressive transient approach, same clipping/drift failure |

Analysis:
- The residual-target modes validate the diagnosis that source waypoint labels
  are not controller-realized actions. Recomputing live residuals can move the
  hand toward source geometry much faster than `dataset_t`.
- Residual chasing is not acceptable as a direct bridge: both target modes
  require clipped z actions (`max_pose_action_clip_fraction=0.333`), spike
  nearest-demo support distance above `0.56`, and end around `0.175 m`
  EE-cube with finger-center around `0.22 m`.
- The contact sheets show the hand makes a transient close pass near the cube
  but does not settle into coherent approach/contact geometry.
- This rules out simple label scaling, simple action repeat, and naive residual
  target chasing as the BC label convention.

Next:
- Implement a bounded controller-rollout dataset diagnostic: reset to source
  trajectory state, use the DEXTRAH controller in the env to chase raw source
  waypoints with an action-limited residual teacher, and record the actual
  lowdim observations plus executed actions. Acceptance is a short replay that
  follows source EE geometry without large clipping/support spikes.
- If the controller-rollout teacher works, convert that rollout into official
  DP lowdim dataset format and run only a tiny official-DP mechanics smoke
  before any scale-up. If it does not, inspect controller gains/decimation or
  waypoint timing as the next semantic patch.

## 2026-06-11T16:56:00-07:00 - controller-rollout teacher plan

Goal:
- Test a controller-aware label convention without training: source waypoints
  become target goals, but the teacher action is recomputed from the live env
  state and the target row advances only when tracking is close enough or a
  bounded hold limit is reached.

Hypothesis:
- The source cuRobo/FK path may be usable if we record the actual
  DEXTRAH-controller rollout as the BC demonstration instead of directly using
  source waypoint-to-waypoint deltas. This should avoid the source-label stall
  and reduce residual-target clipping/support spikes.

Planned Change:
- Extend `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py` with a
  replay-only mode `controller_target_hold`.
- Add controller rollout parameters:
  `controller_target_lookahead`, `controller_target_tolerance`,
  `controller_target_max_hold`.
- For the new mode, log target row, hold count, target error, support, clip
  fractions, videos, and save a one-episode lowdim `.npz` containing live
  observations and executed actions.
- Extend `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh` to pass the
  controller rollout parameters.

Validation Before Cluster:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Planned Cluster Diagnostic:
- Exact source-joint reset, episode `24`, step `0`.
- Mode: `controller_target_hold`.
- `STEPS=160`, `CONTROLLER_TARGET_LOOKAHEAD=1`,
  `CONTROLLER_TARGET_TOLERANCE=0.015`,
  `CONTROLLER_TARGET_MAX_HOLD=16`, video enabled.

Acceptance:
- The replay should follow the teacher EE geometry with substantially lower
  support drift/clipping than naive residual-target modes. Success is not cube
  lift; it is a controller-realized, inspectable approach trajectory that can
  become a DP dataset candidate.

## 2026-06-11T17:08:00-07:00 - close-reaching controller semantics diagnostic plan

Goal:
- Explain and bound the 8-10% per-step action realization mismatch before any
  further DP BC/RL work.
- Run a replay that can either follow source waypoints far enough to reach
  close/lift phases or provide artifact-backed evidence that the current
  controller/action semantics cannot replay the cuRobo teacher.

Hypothesis:
- DEXTRAH's Franka cube action is a relative DifferentialIK setpoint, not a
  one-step realized EE displacement. The env applies one setpoint per 1/60 s
  RL step and only two physics substeps of joint-position tracking, so
  waypoint-to-waypoint labels from cuRobo/FK are expected to under-realize when
  treated as one-step commands.
- A bounded, absolute-pose-to-relative receding target should be a principled
  diagnostic: hold each source target row until live EE tracking is close or a
  maximum hold count expires, then advance. If this reaches close geometry
  without clipping/support spikes, the BC dataset should be regenerated from
  controller rollouts rather than raw source deltas. If it fails, the remaining
  issue is controller capability/gains/substeps or TCP frame semantics.

Change:
- Finish replay-only `controller_target_hold` mode in
  `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`.
- Log controller target row/phase/hold/advance, target errors, close timing,
  clip fractions, EE/finger/cube distances, and save a one-episode live
  lowdim/action `.npz` artifact for inspection.
- Pass the controller-target parameters through
  `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- worklog:
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cd0aa03a12545c2dadd821c551581fdc805faab2`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`,
  `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`, this worklog.

Validation Before Cluster:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Planned Cluster Diagnostic:
- Exact source-joint reset, episode `24`, step `0`.
- Mode: `controller_target_hold`.
- At least `STEPS=320` so the replay can reach the dataset close boundary or
  clearly prove it cannot.
- Video/contact sheet, `replay_report.md`, `replay_summary.json`,
  `replay_motion.png`, `action_realization_audit.png`, generated rollout
  `.npz`, and fetched local artifacts with `viz-open` URLs.

Acceptance:
- Diagnostic acceptance only. A useful result is one of:
  - controller-held targets follow source geometry into close/lift support with
    low clipping, making controller-rollout relabeling the next dataset path;
  - or the held-target replay still cannot track source geometry, proving the
    blocker is controller/TCP/IK dynamics rather than DP training.

## 2026-06-11T17:22:00-07:00 - controller-target-hold close/lift replay launch plan

Goal:
- Exercise the controller/action semantics at a window that reaches close and
  lift targets, not another early-approach-only replay.

Hypothesis:
- Starting from exact source-joint reset at episode `24` step `260`
  (`hold_at_grasp`, just before `close_fingers` starts at local step `282`)
  removes long-range approach/reset confounds. If a live residual target-hold
  controller cannot remain near the source grasp geometry through close and
  lift target rows from this state, raw cuRobo waypoint labels are not suitable
  BC actions under the DEXTRAH controller.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit:
  `7b903da1e8e96b14b6dbdb87c0311e7b084aac4a`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `7b903da1e8e96b14b6dbdb87c0311e7b084aac4a`, detached clean.
- validation:
  - `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
  - `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
  - `git diff --check`

Planned Command / Job:
- run_name:
  `franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_1722xx`
- mode: `controller_target_hold`
- exact reset:
  - `DEMO_RESET_EPISODE=24`, `DEMO_RESET_STEP=260`
  - `DATASET_START_EPISODE=24`, `DATASET_START_STEP=260`
  - `DEMO_RESET_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`
- controller target settings:
  - `CONTROLLER_TARGET_LOOKAHEAD=1`
  - `CONTROLLER_TARGET_TOLERANCE=0.015`
  - `CONTROLLER_TARGET_MAX_HOLD=2`
- replay:
  - `STEPS=340`, `ACTION_REPEAT=1`, `POSE_ACTION_MULTIPLIER=1`
  - `CLIP_ACTIONS=1.0`, `CAPTURE_VIDEO=True`, `VIDEO_LENGTH=340`

Expected Artifacts:
- `replay_report.md`, `replay_summary.json`, `replay_steps.csv`
- `replay_motion.png`, `action_realization_audit.png`
- controller rollout `.npz` and metadata JSON
- video/contact sheet after fetch

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz CHECKPOINT=/results/dp_bc/checkpoints/franka_cube_curobo32_full_pick_lift_framefix_overfit2k/latest.ckpt DEMO_RESET_DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz DEMO_RESET_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json DEMO_RESET_EPISODE=24 DEMO_RESET_STEP=260 DATASET_START_EPISODE=24 DATASET_START_STEP=260 NUM_ENVS=1 STEPS=340 NUM_INFERENCE_STEPS=100 MODES=controller_target_hold ACTION_REPEAT=1 POSE_ACTION_MULTIPLIER=1 CLIP_ACTIONS=1.0 CONTROLLER_TARGET_LOOKAHEAD=1 CONTROLLER_TARGET_TOLERANCE=0.015 CONTROLLER_TARGET_MAX_HOLD=2 CAPTURE_VIDEO=True VIDEO_LENGTH=340 VIDEO_NAME_PREFIX=franka-cube-dp-replay-controllerhold PRINT_INTERVAL=20 SEED=42 sbatch --parsable cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- job_id: `1027893`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/replay_franka_cube_dp_actions_1027893.out`

Acceptance:
- Diagnostic acceptance only. Check final/min EE-cube, finger-cube, gripper
  width, clip fraction, target close/lift step, cube lift, video/contact sheet,
  and support distance before any BC/RL training.

Result:
- status: failed as a teacher replay, useful diagnostic.
- Job `1027893` completed with `FRANKA_CUBE_DP_DATASET_REPLAY_DONE` and
  `DP_REPLAY_DONE`.
- Remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939`
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939`
- Local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/replay_franka_cube_dp_actions_1027893.out`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/replay_report.md`
  - motion plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/replay_motion.png`
  - action realization plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/action_realization_audit.png`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0_sheet.jpg`
- Generated replay-only lowdim rollout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/controller_target_hold_lowdim_rollout.npz`

Metrics:
- `steps=340`
- `target close step=21`, `target lift step=226`
- `first executed negative gripper=36`, `first hard close=49`
- `final EE-cube=0.0808 m`, `min EE-cube=0.0299 m`
- `final finger-center-cube=0.1247 m`, `min finger-center-cube=0.0701 m`
- `final gripper_width=0.000565 m`
- `final cube lift=0`, with only small transient lift in the CSV
  (`~0.0058 m` near step 319)
- `mean_tracking_target_error_after=0.01315 m`
- `mean/max pose_action_clip_fraction=0/0`
- `final nearest_live_phase=lift_object`, but
  `final nearest_live_distance=36.79`, indicating the live state leaves demo
  support badly even when the target row reaches lift.

Analysis:
- The exact source-joint/cube reset at episode `24` step `260` was excellent:
  lowdim and EE diffs were around `1e-7`, and joint diff after write was `0`.
- The controller-target-hold mode reached close and lift target rows without
  action clipping, so the previous 96-step diagnostic was not merely too short.
- The failure changed shape: the live controller can stay within roughly
  `1.3 cm` mean EE target error, but the fingers remain far from a stable
  grasp and the cube is not lifted. The contact sheet shows close happens near
  the cube, then lift target rows pull away/above while the cube stays on the
  table.
- This is not a DP scale-up candidate. It points to source grasp/TCP/contact
  semantics or demo generation, not just one-step action under-realization.

Next:
- Run one more bounded source-state diagnostic: reset directly to the source
  hard-close row (`episode 24`, local step around `310`) and replay/lift from
  there. If exact hard-close source joint state cannot lift under DEXTRAH
  physics, the cuRobo/GraspGenX generated demonstrations are not physically
  valid for the DEXTRAH Franka cube env without a grasp/contact-aware
  controller-rollout generator or a TCP/grasp-frame correction.

## 2026-06-11T17:36:00-07:00 - target-frame/control-point audit plan

Goal:
- Compare target definitions for the same close/lift window and determine
  whether the converted lowdim target, env FK from source joints, and live
  controller command frame refer to the same control point.

Hypothesis:
- The converted dataset lowdim EE target may match env FK from the raw source
  joints, but the controlled EE/TCP point is not the grasp/contact point needed
  to lift the cube. If true, the remaining blocker is GraspGenX/cuRobo grasp
  frame/contact semantics or controller-rollout relabeling, not DP BC scale.

Change:
- Add `dextrah_lab/rl_games/audit_franka_cube_target_frames.py`.
- Add `cluster/sbatch_audit_franka_cube_target_frames_1gpu.sh`.
- The audit will write:
  `target_frame_state_rows.csv`, `target_frame_one_step.csv`,
  `target_frame_summary.json`, `target_frame_report.md`,
  `target_frame_state_plot.png`, and `target_frame_one_step_plot.png`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `836d22fc03fd793b2eef2b520785572f3bface9a`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/rl_games/audit_franka_cube_target_frames.py`,
  `cluster/sbatch_audit_franka_cube_target_frames_1gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/audit_franka_cube_target_frames.py`
- `bash -n cluster/sbatch_audit_franka_cube_target_frames_1gpu.sh`
- `git diff --check`

Planned Cluster Diagnostic:
- Run one bounded l401 job over episode `24` close/lift sentinel rows:
  `260,282,297,310,312,402,450,487`.
- Inputs:
  - dataset:
    `/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - source trajectory:
    `/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`
  - replay CSV:
    `/results/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/replay_steps.csv`
- Reference video/contact sheet from run `1027893` will be linked in the
  report as the best available visual for the audited target path.

Acceptance:
- If converted lowdim and env FK disagree, fix the converter/FK frame.
- If they agree but FK finger-center distances remain far from contact and
  one-step commands do not improve that, conclude raw cuRobo labels need a
  contact-aware controller-rollout relabeler or different controller/grasp
  target before any DP BC/RL training.

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_target_frame_audit_ep24_close_lift_20260611_171200 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json REPLAY_CSV=/results/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/replay_steps.csv EPISODE=24 EPISODE_STEPS=260,282,297,310,312,402,450,487 REFERENCE_VIDEO=/results/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0.mp4 REFERENCE_CONTACT_SHEET=/results/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0_sheet.jpg SEED=42 sbatch --parsable cluster/sbatch_audit_franka_cube_target_frames_1gpu.sh`
- job_id: `1027903`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/audit_franka_cube_target_frames_1027903.out`

Result:
- status: passed diagnostic, failed BC-readiness gate.
- Job `1027903` completed with `FRANKA_CUBE_TARGET_FRAME_AUDIT_DONE` and
  `TARGET_FRAME_AUDIT_DONE`.
- Remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200`
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200`
- Local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/audit_franka_cube_target_frames_1027903.out`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_report.md`
  - state plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_state_plot.png`
  - one-step plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_one_step_plot.png`
  - reference video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0.mp4`
  - reference contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0_sheet.jpg`

Metrics:
- `max_dataset_vs_fk_ee_pos_l2=2.27e-7 m`: converted lowdim EE target and
  env FK from the raw source joints agree. This rejects a converter/FK
  frame mismatch.
- `min_fk_finger_center_to_cube=0.0682 m`: even the source joint state places
  the finger center about `6.8 cm` from the cube while the controlled EE/TCP is
  only `2.85 cm` from the cube.
- Source-state table:
  - step `260` hold-at-grasp: FK EE-cube `0.02846 m`, FK finger-center-cube
    `0.06816 m`.
  - step `310` hard-close: FK EE-cube `0.02846 m`, FK finger-center-cube
    `0.06816 m`, left/right finger distances about `0.06824/0.06810 m`.
  - step `402` lift target: FK EE-cube `0.02845 m`, FK finger-center-cube
    `0.06816 m`.
- One-step commands from source lowdim and source-joint FK targets are
  effectively identical. During lift rows, one-step target error can be small
  (`~0.0013-0.0064 m`) while finger-center distance remains around
  `0.079-0.085 m`.

Analysis:
- The target-frame audit answers the orchestrator's question: the target row is
  expressed in the same EE/TCP frame the env action controls, but that control
  point is not the physical grasp/contact point for the cube in this generated
  demonstration.
- Raw cuRobo labels therefore cannot be used as a DP BC warm-start dataset for
  the DEXTRAH Franka cube task as-is. The failure is upstream of DP: source
  grasp/contact geometry or TCP definition is incompatible with the env reward
  and contact geometry.
- Scaling, action repeat, residual targets, exact source joint reset, and
  source-FK target definitions have all failed to produce stable close/lift.

Next:
- Do not train DP BC/RL on these raw labels.
- Next useful bounded implementation is a contact-aware controller-rollout
  relabeler/generator that targets finger-center/cube geometry in the live
  DEXTRAH env, or a correction to the GraspGenX/cuRobo EE/TCP/grasp frame
  before conversion. The generated rollout must demonstrate stable close/lift
  in Isaac before official DP training resumes.

## 2026-06-11T17:22:50-07:00 - raw-label blocker and contact-aware rollout smoke plan

Goal:
- Record the raw-label blocker verdict and move only to a bounded
  contact-aware controller rollout diagnostic. This is not DP BC or RL
  training.

Hypothesis:
- Raw GraspGenX/cuRobo labels are internally frame-consistent, but their
  controlled EE/TCP point is not the physical cube grasp point in the DEXTRAH
  Franka cube env. A live controller rollout that targets measured
  finger-center/cube geometry must first demonstrate stable close/lift before
  any relabeled dataset or official-DP BC run is justified.

Blocker Verdict:
- Raw-label BC is blocked for behavior claims. The target-frame audit
  `1027903` showed converted lowdim and source-joint FK agree
  (`max_dataset_vs_fk_ee_pos_l2=2.27e-7 m`), but source rows still leave the
  finger center about `6.8 cm` from the cube at hold/hard-close/lift rows.
- Reference artifacts:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_report.md`
  - state plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_state_plot.png`
  - one-step plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/target_frame_audits/franka_cube_target_frame_audit_ep24_close_lift_20260611_171200/target_frame_one_step_plot.png`
  - reference video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0.mp4`
  - reference contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/replays/franka_cube_dp_replay_sourcejoint_controllerhold_ep24s260_mh2_340_20260611_165939/videos/franka-cube-dp-replay-controllerhold-step-0_sheet.jpg`

Change:
- Add `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`, a bounded
  Isaac smoke that exact-resets to a source episode/step, then drives a live
  relative-EE controller toward measured finger-center targets through
  align-open, close-hold, and lift phases.
- Add `cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh` to run the
  smoke on l401 with DEXTRAH/Isaac container mounts and artifact checks.

Owned Files:
- `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- this worklog

Acceptance Criteria:
- The smoke must write `contact_rollout_report.md`,
  `contact_rollout_summary.json`, `contact_rollout_steps.csv`,
  `contact_rollout_plot.png`, and a video/contact sheet after fetch.
- A variant is only a useful relabeling candidate if video and metrics show the
  hand closes near the cube, finger-center distance reaches contact-scale
  geometry, cube lift exceeds the task success threshold, and pose action
  clipping is not the explanation.
- If no variant lifts, keep DP BC/RL blocked and refine the controller-rollout
  relabeler or grasp/contact frame rather than training.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- `git diff --check`

Planned Cluster Diagnostic:
- run name:
  `franka_cube_contact_rollout_ep24s260_center_sweep_<timestamp>`
- exact reset:
  - `EPISODE=24`, `EPISODE_STEP=260`
  - dataset:
    `/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz`
  - source trajectory:
    `/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json`
- variants: `center,center_high15,center_high30`
- phases: `ALIGN_STEPS=80`, `CLOSE_STEPS=80`, `LIFT_STEPS=120`,
  `LIFT_HEIGHT=0.14`, `FINGER_GAIN=0.75`, `CLIP_ACTIONS=1.0`.
- expected remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/$RUN_NAME`
- local artifact namespace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/$RUN_NAME`

## 2026-06-11T17:26:15-07:00 - contact-aware rollout smoke launched

Goal:
- Run the first bounded contact-aware controller rollout smoke after the
  raw-label blocker. This is a generator/relabeler gate, not DP BC/RL
  training.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- local_commit: `70b7d250f75e3ef27494006de8208c0fee21e195`
- pushed: yes, branch `codex/franka-cube-diffusion-policy-bc`
- remote deployment: Git bundle because l401 GitHub fetch failed with
  `Permission denied (publickey)`.
- remote_commit:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  detached at `70b7d250f75e3ef27494006de8208c0fee21e195`
- changed_files:
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`,
  `cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`: passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`: passed.
- `git diff --check`: passed.

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_rollout_ep24s260_center_sweep_20260611_172603 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json EPISODE=24 EPISODE_STEP=260 VARIANTS=center,center_high15,center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=120 LIFT_HEIGHT=0.14 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=280 VIDEO_NAME_PREFIX=franka-cube-contact-rollout PRINT_INTERVAL=40 SEED=42 sbatch --parsable cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- job_id: `1027908`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_center_sweep_20260611_172603`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_1027908.out`

Expected Artifacts:
- `contact_rollout_report.md`
- `contact_rollout_summary.json`
- `contact_rollout_steps.csv`
- `contact_rollout_plot.png`
- `videos/*.mp4`

Acceptance:
- Inspect report/JSON/CSV/plot/video after fetch. This only unlocks DP BC if
  a variant visually and metrically shows stable close/lift without relying on
  action clipping. Otherwise keep training blocked and patch the bounded
  controller-rollout generator.

Result:
- status: failed before meaningful rollout.
- Slurm state: `FAILED 1:0`, elapsed `00:00:49`, node `pool0-00030`.
- Log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_1027908.out`
- Error:
  `FRANKA_CUBE_CONTACT_ROLLOUT_FAILED AttributeError: 'numpy.ndarray' object has no attribute 'detach'`
  at `contact_aware_franka_cube_rollout.py:389`.
- Additional launch issue: the command line included only `--variant center`
  because Slurm `--export` splits comma-separated values, so
  `VARIANTS=center,center_high15,center_high30` was truncated.

Analysis:
- `_reset_to_source()` returns a NumPy 72D policy observation, while
  `_policy_obs_from_step()` returns a torch tensor. The existing loop assumed
  the lowdim extractor returned a torch tensor in both cases.
- This run has no behavior evidence and should not be used for controller
  rollout conclusions.

Next:
- Patch lowdim extraction to accept both torch tensors and NumPy arrays.
- Patch the wrapper to accept robust repeated variants via
  `VARIANT_COUNT`/`VARIANT_0..N`, then validate, commit, push, deploy exact
  commit, and relaunch a bounded smoke.

## 2026-06-11T17:28:24-07:00 - contact rollout runtime patch before relaunch

Goal:
- Fix the runtime type mismatch and Slurm variant export bug from job
  `1027908` without changing the scope: still only a bounded contact-aware
  relabel/generator smoke.

Change:
- Added `_lowdim_numpy_from_policy_obs()` in
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py` so reset-time
  NumPy observations and step-time torch observations both produce a 1D
  lowdim NumPy vector.
- Updated `cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh` to support
  `VARIANT_COUNT` and `VARIANT_0..N` in addition to the old comma-delimited
  `VARIANTS` default, avoiding Slurm `--export` comma splitting.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `a392e55e9ccfaa9816edbca52b975a643d7fff5f`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`,
  `cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`, this worklog.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- `git diff --check`

Relaunch Plan:
- Launch the same bounded smoke, now with explicit repeated variants:
  `VARIANT_COUNT=3`, `VARIANT_0=center`, `VARIANT_1=center_high15`,
  `VARIANT_2=center_high30`.
- If runtime passes, fetch report/JSON/CSV/plot/video and inspect whether any
  variant demonstrates stable close/lift. No DP BC/RL training.

Command / Job:
- validation:
  - `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`: passed.
  - `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`: passed.
  - `git diff --check`: passed.
- implementation_commit: `06368f2fd12f0beecae8032ded9738e715b64d66`
- pushed: yes.
- remote deployment: Git bundle; remote worktree detached at
  `06368f2fd12f0beecae8032ded9738e715b64d66`.
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json EPISODE=24 EPISODE_STEP=260 VARIANT_COUNT=3 VARIANT_0=center VARIANT_1=center_high15 VARIANT_2=center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=120 LIFT_HEIGHT=0.14 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=280 VIDEO_NAME_PREFIX=franka-cube-contact-rollout PRINT_INTERVAL=40 SEED=42 sbatch --parsable cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- job_id: `1027920`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_1027920.out`

Acceptance:
- Check that the log includes all three `--variant` args, then fetch and
  inspect report/JSON/CSV/plot/video. A clean Slurm exit is not sufficient.

Result:
- status: completed `0:0`, failed strict relabeling gate but produced useful
  contact-aware controller evidence.
- Slurm: `COMPLETED 0:0`, elapsed `00:01:33`, node `pool0-00011`.
- Remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940`
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940`
- Local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/contact_aware_franka_cube_rollout_1027920.out`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940/contact_rollout_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940/contact_rollout_plot.png`
  - best video, `center_high30`:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940/videos/franka-cube-contact-rollout-step-560.mp4`
  - best contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_center3_fix_20260611_172940/videos/franka-cube-contact-rollout-step-560_sheet.jpg`

Metrics:
- `center`: final/max lift `0.08267 m`, min/final finger-center distance
  `0.03835/0.04746 m`, final gripper width `0.05455 m`, max clip fraction
  `0.16667`.
- `center_high15`: final/max lift `0.09324 m`, min/final finger-center
  `0.03792/0.04118 m`, final gripper width `0.05189 m`, no pose clipping.
- `center_high30`: final/max lift `0.11268 m`, min/final finger-center
  `0.03754/0.037998 m`, final gripper width `0.04867 m`, final EE-cube
  `0.01174 m`, no pose clipping.
- Videos are valid MP4s at `1280x720`, about `4.65 s`, `279-280` frames.

Analysis:
- The runtime patch worked: all three variants were passed through Slurm and
  executed.
- The contact-aware heuristic is qualitatively different from raw labels and
  failed DP videos: it approaches the cube and lifts it rather than drifting
  away.
- It is still not BC-ready relabeled data. The script verdict remains
  `No contact-aware rollout variant produced stable lift` because lift did not
  cross the task success threshold, and the gripper remains around
  `4.9-5.5 cm` wide. `center_high30` is the best bounded candidate, but needs
  a higher/longer lift test and closer inspection of whether the cube is
  actually grasped or being pushed/carried by incidental contact.

Next:
- Do not train DP BC/RL.
- Run one narrow follow-up with only `center_high30`, higher lift target, and a
  longer lift phase. Acceptance remains video/metric proof of stable close/lift
  before any relabel dataset generation.

## 2026-06-11T17:33:02-07:00 - contact rollout high-lift follow-up plan

Goal:
- Test whether the promising `center_high30` contact-aware target can clear the
  success-height gate if commanded higher/longer, without action clipping or
  obvious unstable contact.

Hypothesis:
- The previous `center_high30` run maintained finger-center distance around
  `3.8 cm` and lifted to `11.3 cm` with no pose clipping. A larger lift target
  and longer lift phase may reveal whether this is a stable grasp path or only
  partial/incidental lift.

Version Control:
- implementation_commit: `06368f2fd12f0beecae8032ded9738e715b64d66`
- changed source since commit: none
- worklog result commit: pending

Planned Command / Job:
- run name:
  `franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_1733xx`
- setting:
  `VARIANT_COUNT=1`, `VARIANT_0=center_high30`, `ALIGN_STEPS=80`,
  `CLOSE_STEPS=80`, `LIFT_STEPS=160`, `LIFT_HEIGHT=0.22`,
  `FINGER_GAIN=0.75`, `CLIP_ACTIONS=1.0`, `CAPTURE_VIDEO=True`,
  `VIDEO_LENGTH=320`.

Acceptance:
- Strict relabel gate only: stable visual close/lift, lift over task success
  threshold, no significant pose clipping, and metrics/report/video fetched
  locally. This still does not authorize DP BC training by itself; it only
  identifies a candidate controller-rollout relabeler setting.

Command / Job:
- remote deployment: agent-owned l401 worktree detached at
  `7b0da8b73c91e887c7936407448aa9f6d14c1a43`.
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json EPISODE=24 EPISODE_STEP=260 VARIANT_COUNT=1 VARIANT_0=center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=160 LIFT_HEIGHT=0.22 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-contact-rollout-high30-lift22 PRINT_INTERVAL=40 SEED=42 sbatch --parsable cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- job_id: `1027921`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_1027921.out`

Result:
- status: completed `0:0`, but artifact summary exposed post-reset row
  contamination.
- Remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411`
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411`
- Local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/contact_aware_franka_cube_rollout_1027921.out`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411/contact_rollout_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411/contact_rollout_plot.png`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411/videos/franka-cube-contact-rollout-high30-lift22-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_20260611_173411/videos/franka-cube-contact-rollout-high30-lift22-step-0_sheet.jpg`

Metrics:
- It reached `max_cube_lift_height=0.13550 m`, with pre-reset row
  `local_step=280`, `ee_to_cube=0.00751 m`,
  `finger_center_to_cube=0.03787 m`, `gripper_width=0.04962 m`, and no pose
  clipping.
- The final CSV/summary row is post-reset: `cube_lift_height=0`,
  `ee_to_cube=0.19484 m`, `finger_center_to_cube=0.18519 m`,
  `gripper_width=0.08 m`.
- IsaacLab `DirectRLEnv.step()` resets terminated envs before returning
  observations, so this row is not behavior evidence.

Analysis:
- The contact-aware high-lift controller appears to hit the success threshold,
  but the artifact logger must exclude post-reset rows and mark terminal
  success explicitly before this can be used as a relabeler gate.
- The visual contact sheet shows the cube being carried upward, but this still
  needs clean pre-reset metrics/video annotation before any dataset generation.

Next:
- Patch `contact_aware_franka_cube_rollout.py` to drop post-reset rows after
  `terminated/truncated`, annotate the previous row with terminal metadata,
  and summarize final pre-reset state. Relaunch the same high-lift smoke for
  clean artifacts. No DP training.

## 2026-06-11T17:37:36-07:00 - contact rollout post-reset logging fix

Goal:
- Fix the contact-aware rollout artifact semantics so success/reset does not
  make the final metrics look like the hand drifted away.

Change:
- In `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`, detect
  `terminated/truncated` immediately after the env step.
- Do not append the returned post-reset observation row. Instead, annotate the
  previous pre-reset row with `terminated_next_step`, `truncated_next_step`,
  `terminal_reward_next`, and the skipped post-reset step/width/lift.
- Add terminal/skipped-reset fields to the report summary table.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`: passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`: passed.
- `git diff --check`: passed.

Relaunch Plan:
- Same one-variant high-lift smoke as job `1027921`, with run name
  `franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_<timestamp>`.
- Acceptance remains clean report/JSON/CSV/plot/video with pre-reset final
  metrics and visual stable lift.

Command / Job:
- implementation_commit: `909b3429a6ab3e944b5e7ab06750074e7c167533`
- pushed: yes.
- remote deployment: agent-owned l401 worktree detached at
  `909b3429a6ab3e944b5e7ab06750074e7c167533`.
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json EPISODE=24 EPISODE_STEP=260 VARIANT_COUNT=1 VARIANT_0=center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=160 LIFT_HEIGHT=0.22 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-contact-rollout-high30-lift22-postresetfix PRINT_INTERVAL=40 SEED=42 sbatch --parsable cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh`
- job_id: `1027922`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_rollout_1027922.out`

Result:
- status: completed `0:0`; artifacts fetched and inspected.
- Remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835`
- Local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835`
- Local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/contact_aware_franka_cube_rollout_1027922.out`
- Viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835/contact_rollout_report.md`
  - plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835/contact_rollout_plot.png`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835/videos/franka-cube-contact-rollout-high30-lift22-postresetfix-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_rollouts/franka_cube_contact_rollout_ep24s260_high30_lift22_postresetfix_20260611_173835/videos/franka-cube-contact-rollout-high30-lift22-postresetfix-step-0_sheet.jpg`

Metrics:
- `variant=center_high30`, `steps=281`.
- `success_like=true`, `terminated_next_step=true`,
  `truncated_next_step=false`, `skipped_post_reset_local_step=281`.
- `final_cube_lift_height=max_cube_lift_height=0.135498 m`.
- `final_ee_to_cube=0.007513 m`.
- `min_finger_center_to_cube=0.037540 m`,
  `final_finger_center_to_cube=0.037870 m`.
- `final_gripper_width=0.049620 m`.
- `max_pose_action_clip_fraction=0.0`.
- Video validated with `ffprobe`: 1280x720, 60 FPS, 281 frames,
  4.683 s.

Analysis:
- This post-reset-fixed artifact resolves the logging ambiguity from job
  `1027921`: the final behavior row is pre-reset, not a reset observation.
- The contact-aware live controller rollout is the first C-path artifact that
  approaches the cube, closes, and lifts above the task success-height
  threshold under the actual Isaac controller without pose-action clipping.
- This does not unblock DP BC training yet. It only establishes a plausible
  controller-rollout relabeler seed. Raw GraspGenX/cuRobo labels remain
  invalid for behavior claims because source FK/lowdim agreement did not imply
  contact geometry at the controlled fingers.

Next:
- Do not train DP/RL on raw labels.
- Next bounded step should promote this from a single successful smoke to a
  relabeling gate: generate or replay a small set of contact-aware controller
  rollouts across selected source episodes/starts/offsets, require stable
  close/lift videos and clean metrics, then export only passing controller
  rollouts as BC demonstrations.

## 2026-06-11T17:44:39-07:00 - contact-aware relabel set gate plan

Goal:
- Expand the single passing contact-aware controller smoke into a small,
  inspectable relabel rollout set gate without starting DP BC/RL training.

Plan:
- Inspect the framefixed 32-demo dataset and source trajectory layout to choose
  a handful of source episodes/steps that can be reset from available cuRobo
  source joints.
- Add a bounded set-level runner/wrapper around the existing
  `contact_aware_franka_cube_rollout.py` logic rather than changing the
  official DP path. It should run one `center_high30`/high-lift rollout per
  selected source episode/step, record per-rollout CSV/JSON/report/video, and
  aggregate a set-level summary table.
- Add hard gate filters before any relabeled data is considered usable:
  pre-reset final/max lift above task threshold, no post-reset rows in the
  behavior trace, max pose-action clip fraction within tolerance, final
  EE-to-cube and finger-center-to-cube within plausible bounds, terminal metadata
  present when success resets the env, and at least spot-check videos/contact
  sheets for pass/failure modes.
- Validate locally with `python3 -m py_compile`, wrapper `bash -n`, and
  `git diff --check`; then commit/push and deploy the exact commit to the
  agent-owned l401 worktree.
- Launch a small 1-GPU l401 relabel-set smoke only after validation passes,
  fetch all artifacts locally, run `viz-open` on the set report/plot and
  representative pass/fail videos or contact sheets, update this worklog, and
  only then decide whether a tiny official-DP smoke is justified.

Owned files expected:
- `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- A new set-level runner or wrapper under `dextrah_lab/rl_games/` if needed.
- A matching bounded Slurm wrapper under `cluster/`.
- This owned worklog.

No-go:
- No DP BC/RL training or scale-up until the set-level contact-aware relabel
  gate passes with inspectable artifacts.

## 2026-06-11T17:49:21-07:00 - contact-aware relabel set implementation

Goal:
- Implement the small set-level relabel gate planned above, while keeping the
  single-rollout controller behavior unchanged.

Change:
- Add `lowdim_obs`, `source_row`, and `source_trajectory_json` columns to
  `contact_aware_franka_cube_rollout.py` CSV rows so passing rollouts can be
  exported as lowdim/action demonstrations later.
- Add `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`, which
  reads per-rollout summaries/CSVs, applies hard gates, writes
  `contact_relabel_set_summary.json`,
  `contact_relabel_set_rollouts.csv`,
  `contact_relabel_set_failures.csv`,
  `contact_relabel_set_report.md`, and
  `contact_relabel_set_accepted.npz`.
- Add `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`, a
  bounded 1-GPU wrapper that runs multiple source episode/step rollouts inside
  one allocation and then aggregates the set.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`: passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_rollout_1gpu.sh && bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`: passed.
- `git diff --check`: passed.
- Local aggregator smoke on a copied pre-`lowdim_obs` artifact: passed
  mechanically and correctly failed the relabel gate with
  `missing_lowdim_obs_for_relabel_export`, confirming the hard filter is active.

Next:
- Commit/push this implementation, deploy the exact commit to the agent-owned
  l401 worktree, stage the missing local cuRobo trajectory JSONs into the
  agent/result artifact namespace on l401, and launch a small 4-rollout
  relabel-set smoke for episodes `8,16,24,30` at step `260` with
  `center_high30`, `LIFT_HEIGHT=0.22`, `ALIGN_STEPS=80`, `CLOSE_STEPS=80`,
  `LIFT_STEPS=160`.

Command / Job:
- implementation_commit: `55753745fbc2bbdb75402615d2cbb9cf43765915`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`.
- remote deployment: agent-owned l401 worktree detached at
  `55753745fbc2bbdb75402615d2cbb9cf43765915`. Initial SSH fetch failed due
  missing GitHub SSH key on l401; read-only HTTPS fetch succeeded and was used
  for deployment. No tracked source was rsynced.
- staged artifacts: copied missing local cuRobo trajectory JSONs for seeds
  `8`, `16`, and `30` into
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/`;
  seed `24` was already present.
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_20260611_175034 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_ROOT=/results/dp_bc/curobo_plans TRAJECTORY_TEMPLATE=cube_curobo_scale32_20260611_125957_seed{episode}/trajectory.json SPEC_COUNT=4 SPEC_0=8:260 SPEC_1=16:260 SPEC_2=24:260 SPEC_3=30:260 VARIANT=center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=160 LIFT_HEIGHT=0.22 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-contact-relabel PRINT_INTERVAL=80 SEED=42 GATE_MIN_LIFT=0.10 GATE_MAX_POSE_CLIP_FRACTION=0.0 GATE_MAX_FINAL_EE_TO_CUBE=0.05 GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 sbatch --export=ALL --parsable cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- job_id: `1027929`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_20260611_175034`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1027929.out`
- expected artifacts:
  set-level `contact_relabel_set_summary.json`,
  `contact_relabel_set_rollouts.csv`,
  `contact_relabel_set_failures.csv`,
  `contact_relabel_set_report.md`,
  `contact_relabel_set_accepted.npz`, plus per-rollout CSV/JSON/plot/report
  and videos/contact sheets after fetch.

Result:
- status: failed before simulation, `FAILED 2:0`, elapsed `00:00:04`.
- log evidence:
  `Missing trajectory JSON for spec 8:260: /lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json/trajectory.json}`.

Analysis:
- The shell placeholder substitution for `{episode}`/`{seed}` in the relabel
  set wrapper was malformed because the closing brace terminated the shell
  parameter expansion. This produced an invalid trajectory path before entering
  the container.
- This failure happened before any rollout, so it is not behavior evidence.

Change:
- Patch `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` to
  substitute `{episode}` and `{seed}` with `sed` in both host preflight and
  container command construction.

Validation:
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh && git diff --check`: passed.
- `python3 -m py_compile dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`: passed.

Next:
- Commit/push, deploy the exact patch commit, and relaunch the same bounded
  4-rollout relabel-set gate.

## 2026-06-11T17:51:59-07:00 - contact relabel set templatefix relaunch

Goal:
- Relaunch the same four-rollout contact-aware relabel gate after the trajectory
  template fix.

Version Control:
- implementation_commit: `0f663b4c3be569a81ef431ce885099ddf131741c`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`.
- remote deployment: l401 agent-owned worktree detached at
  `0f663b4c3be569a81ef431ce885099ddf131741c`.

Command / Job:
- command:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart RUN_NAME=franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_templatefix_20260611_175159 DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz TRAJECTORY_ROOT=/results/dp_bc/curobo_plans TRAJECTORY_TEMPLATE=cube_curobo_scale32_20260611_125957_seed{episode}/trajectory.json SPEC_COUNT=4 SPEC_0=8:260 SPEC_1=16:260 SPEC_2=24:260 SPEC_3=30:260 VARIANT=center_high30 ALIGN_STEPS=80 CLOSE_STEPS=80 LIFT_STEPS=160 LIFT_HEIGHT=0.22 FINGER_GAIN=0.75 CLIP_ACTIONS=1.0 CAPTURE_VIDEO=True VIDEO_LENGTH=320 VIDEO_NAME_PREFIX=franka-cube-contact-relabel PRINT_INTERVAL=80 SEED=42 GATE_MIN_LIFT=0.10 GATE_MAX_POSE_CLIP_FRACTION=0.0 GATE_MAX_FINAL_EE_TO_CUBE=0.05 GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 sbatch --export=ALL --parsable cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- job_id: `1027930`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_templatefix_20260611_175159`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1027930.out`

Result:
- status: failed before simulation, `FAILED 2:0`, elapsed `00:00:04`.
- log evidence remained:
  `Missing trajectory JSON for spec 8:260: ...seed8/trajectory.json/trajectory.json}`.

Analysis:
- Remote wrapper contents had the `sed` substitution patch, so the remaining
  source was the default assignment itself:
  `TRAJECTORY_TEMPLATE="${TRAJECTORY_TEMPLATE:-...{episode}...}"`. Bash
  parses the `}` in `{episode}` while expanding the default expression, before
  the later `sed` replacement.

Change:
- Patch the wrapper to set `TRAJECTORY_TEMPLATE` in two steps: first read an
  optional env value, then assign the literal default in a normal quoted string
  when empty.

Validation:
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh && git diff --check`: passed.
- `python3 -m py_compile dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`: passed.
- Local shell substitution smoke produced
  `cube_curobo_scale32_20260611_125957_seed8/trajectory.json`.

Next:
- Commit/push, deploy exact commit, and relaunch the same bounded 4-rollout
  relabel-set gate.

## 2026-06-11T17:53:47-07:00 - contact relabel set defaultfix relaunch

Goal:
- Relaunch the four-rollout contact-aware relabel gate after fixing literal
  brace parsing in the wrapper default.

Version Control:
- implementation_commit: `e409721d03da09d3797d75594a50c1ce7ca64fc4`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`.
- remote deployment: l401 agent-owned worktree detached at
  `e409721d03da09d3797d75594a50c1ce7ca64fc4`.

Command / Job:
- command:
  same settings as `1027930`, run name
  `franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347`.
- job_id: `1027932`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1027932.out`

Result:
- status: completed `0:0`, elapsed `00:02:47`; artifacts fetched locally and
  inspected.
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347`
- local log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/logs/contact_aware_franka_cube_relabel_set_1027932.out`

Set-Level Gate:
- verdict:
  `PASS: all contact-aware rollouts satisfied the hard relabel gate; this only permits a tiny official-DP smoke proposal.`
- rollouts: `4`, pass: `4`, failure: `0`.
- accepted relabel dataset:
  `contact_relabel_set_accepted.npz`, with `obs (1126, 21)`,
  `action (1126, 7)`, `episode_ends [282, 563, 844, 1126]`,
  `phase_ids (1126,)`, `rollout_ids (4,)`.
- hard filters:
  `min_lift=0.10 m`, `max_pose_action_clip_fraction=0.0`,
  `max_final_ee_to_cube=0.05 m`,
  `max_final_finger_to_cube=0.08 m`, `require_success_like=true`.

Per-Rollout Metrics:
- `ep08s260_center_high30`: final EE-cube `0.00745 m`,
  final finger-cube `0.03788 m`, final/max lift `0.13621 m`,
  max pose clip `0.0`.
- `ep16s260_center_high30`: final EE-cube `0.00728 m`,
  final finger-cube `0.03802 m`, final/max lift `0.13542 m`,
  max pose clip `0.0`.
- `ep24s260_center_high30`: final EE-cube `0.00751 m`,
  final finger-cube `0.03787 m`, final/max lift `0.13550 m`,
  max pose clip `0.0`.
- `ep30s260_center_high30`: final EE-cube `0.00772 m`,
  final finger-cube `0.03811 m`, final/max lift `0.13642 m`,
  max pose clip `0.0`.

Viewer URLs:
- set report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_report.md`
- set summary JSON:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_summary.json`
- representative pass video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/rollouts/ep08s260/videos/franka-cube-contact-relabel-ep08s260-step-0.mp4`
- representative pass contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/rollouts/ep08s260/videos/franka-cube-contact-relabel-ep08s260-step-0_sheet.jpg`
- last-rollout contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/rollouts/ep30s260/videos/franka-cube-contact-relabel-ep30s260-step-0_sheet.jpg`
- episode 24 trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/rollouts/ep24s260/contact_rollout_plot.png`

Visual Inspection:
- Contact sheets for episodes `8` and `30` show approach, close, and stable
  cube lift. This is qualitatively different from the stale raw-label/DP eval
  drift-away videos.
- No failure-mode video exists for this set because all four rollouts passed
  the hard gate; `contact_relabel_set_failures.csv` is empty.

Analysis:
- The controller-rollout relabeler is now validated on a small, inspectable
  four-episode set. This resolves the immediate relabeler gate requested after
  raw GraspGenX/cuRobo labels were found not to be BC-ready.
- This is still not full BC readiness. It is a small contact-aware dataset
  candidate suitable for the next bounded step: a tiny official Diffusion Policy
  smoke using the official `real-stanford/diffusion_policy` implementation and
  this accepted NPZ, with no BC/RL scale-up.

Next:
- Do not launch full BC/RL.
- Next practical C step is a tiny official-DP config/dataset smoke on
  `contact_relabel_set_accepted.npz`: shape/normalizer check plus one-step or
  very-short debug train, then inspect predicted action ranges before any
  closed-loop DP eval.

## 2026-06-11T18:00:23-07:00 - official DP contact-relabel smoke plan

Goal:
- Prove the accepted contact-aware relabel NPZ can be consumed by the official
  `real-stanford/diffusion_policy` low-dimensional training workspace, without
  launching full BC/RL.

Hypothesis:
- The existing `FrankaCubeLowdimDataset` adapter should work unchanged because
  the accepted relabel set uses the same compact 21D observation and 7D
  normalized DEXTRAH relative EE/gripper action schema as prior official-DP
  debug datasets.

Change:
- Add a small report utility if needed to emit viewer-ready dataset shape,
  episode ends, action/obs range, and official normalizer metadata for any
  accepted contact-aware NPZ.
- Do not alter the official-DP training workspace or env bridge semantics.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- worklog:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `a93e02674eab27bcb83930308a8b560fdb9d5837`
- official_diffusion_policy:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`

Command / Job:
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- intended local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/<timestamp>`
- validation commands:
  `python3 -m py_compile ...`, official-DP adapter shape/normalizer report,
  `validate_dataset_smoke.py`, and one official-DP `train.py` debug run with
  `training.max_train_steps=1`, `training.max_val_steps=1`,
  `training.num_epochs=1`, CPU device, and `num_inference_steps=2`.

Acceptance:
- The dataset report confirms `obs (1126, 21)`, `action (1126, 7)`, and
  `episode_ends [282, 563, 844, 1126]`.
- Official normalizer construction succeeds with identity action normalizer.
- Official `train.py` builds the model/workspace and performs a one-step debug
  update/validation without non-finite losses.
- If a checkpoint is written, run the existing official checkpoint bridge smoke
  and record predicted action ranges; otherwise record the exact blocker.

Next:
- Inspect logs/artifacts after the tiny run, open report/logs with `viz-open`,
  then commit/push the report utility and worklog.

## 2026-06-11T18:04:23-07:00 - official DP contact-relabel smoke result

Goal:
- Run the bounded official Diffusion Policy mechanics smoke on the accepted
  contact-aware relabel set, using only shape/normalizer checks, a one-step
  debug train, and predicted-action range sanity.

Change:
- Added reusable artifact helpers:
  `dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py` and
  `dextrah_lab/offline_dp_bc/make_official_dp_smoke_report.py`.
- No training config semantics were changed. The official DP config remains
  `dextrah_lab/offline_dp_bc/config/franka_cube_lowdim_dp.yaml`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `a93e02674eab27bcb83930308a8b560fdb9d5837`
- implementation_commit: `e26b8ade8428902fb333a8a15d79e1001318f70b`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`.
- changed_files:
  `dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py`,
  `dextrah_lab/offline_dp_bc/make_official_dp_smoke_report.py`,
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- official_diffusion_policy:
  source `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`.

Command / Job:
- job_id: `n/a` local bounded CPU smoke.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_official_dp_smoke_20260611_180153`
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- validation:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py dextrah_lab/offline_dp_bc/make_official_dp_smoke_report.py`,
  `git diff --check`.
- dataset report:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.make_lowdim_dataset_report --dataset $DATASET --output-dir $OUT --horizon 16 --pad-before 1 --pad-after 7 --val-ratio 0.25`
- adapter smoke:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.validate_dataset_smoke --dataset $DATASET --horizon 16 --pad-before 1 --pad-after 7`
- official train smoke:
  `cd $DP && PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp task.dataset_path=$DATASET task.dataset.val_ratio=0.25 training.device=cpu training.max_train_steps=1 training.max_val_steps=1 training.num_epochs=1 policy.num_inference_steps=2 dataloader.batch_size=8 val_dataloader.batch_size=8 hydra.run.dir=$OUT/official_dp_train`
- checkpoint range sanity:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.validate_official_checkpoint_smoke --checkpoint $OUT/official_dp_train/checkpoints/latest.ckpt --dataset $DATASET --device cpu --batch-size 4 --num-inference-steps 2 --row-selector first --warm-history-from-dataset`
  and the same command with `--row-selector gripper_closed`.

Result:
- status: passed.
- dataset adapter:
  `obs (1126, 21)`, `action (1126, 7)`,
  `episode_ends [282, 563, 844, 1126]`, train/val samples `844/282`.
- normalizer:
  official `LinearNormalizer`; obs uses limits fit; action normalizer is
  identity with zero offset and unit scale.
- action range:
  pose action abs max `0.7517907`, pose exact-bound fraction `0.0`;
  overall exact-bound fraction `0.142857` comes from the binary gripper channel
  (`gripper_exact_bound_fraction=1.0`).
- adapter smoke:
  `FRANKA_CUBE_DP_BC_SMOKE_PASSED`, official DP dataset import `true`,
  sample obs/action shapes `[16, 21]` and `[16, 7]`.
- official one-step train:
  model/workspace constructed with official
  `TrainDiffusionUnetLowdimWorkspace`; checkpoint written at
  `$OUT/official_dp_train/checkpoints/latest.ckpt`.
- tiny train metrics:
  `train_loss=1.1225613`, `val_loss=1.1745609`,
  `train_action_mse_error=0.6494607`, `global_step=0`, `epoch=0`.
- predicted-action sanity:
  first and gripper-closed dataset windows both produced finite direct
  `(4, 8, 7)` action chunks and bridge `(4, 7)` actions. The one-step debug
  checkpoint touches normalized bounds in several dimensions, which is expected
  for a mechanics-only smoke and is not a behavior claim.

Viewer URLs:
- official DP smoke report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_official_dp_smoke_20260611_180153/official_dp_smoke_report.md`
- dataset/normalizer/action range report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_official_dp_smoke_20260611_180153/dataset_report.md`
- resolved official DP config:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_official_dp_smoke_20260611_180153/official_dp_train/.hydra/config.yaml`
- tiny train stdout:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_official_dp_smoke_20260611_180153/logs/official_dp_tiny_train.log`

Analysis:
- The accepted contact-aware relabel NPZ is consumable by the official
  `real-stanford/diffusion_policy` lowdim training workspace with the existing
  adapter. This clears only the official-DP mechanics gate requested by the
  user.
- The previous raw-label behavior claims remain invalid/stale. Closed-loop DP
  eval is still gated on a real contact-aware BC checkpoint trained beyond this
  one-step debug smoke, plus the same artifact-heavy eval checks used earlier:
  video/contact sheet, support traces, action range, history cadence, and
  train/eval schema audit.

Next:
- Commit/push this source/worklog checkpoint.
- Before closed-loop DP eval, run a tiny contact-aware BC pretrain/debug job
  with enough steps to reduce train/val action error while still bounded, then
  inspect checkpoint action ranges. Do not proceed to RL warm-start or large
  training until contact-aware DP closed-loop behavior is coherent.

## 2026-06-11T18:07:05-07:00 - official DP contact-aware debug pretrain plan

Goal:
- Run a bounded contact-aware BC debug pretrain from the official
  `real-stanford/diffusion_policy` workspace on the accepted relabel NPZ, with
  enough optimizer steps to inspect train/val loss reduction and checkpoint
  action ranges.

Hypothesis:
- A short local RTX 6000 run with the accepted contact-aware dataset should
  reduce training loss and produce finite action chunks. This is a necessary
  checkpoint before proposing any closed-loop DP eval, but it is not full BC
  readiness.

Change:
- Add a report utility for bounded official-DP pretrains that parses
  `logs.json.txt`, writes a loss CSV/table, plots train/val/action-MSE curves,
  and summarizes checkpoint action-range smoke logs.
- Do not modify the official DP implementation or the existing training config
  semantics.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cb6501561424151b295e88b7f3c9b04a9b4b577d`
- implementation_commit: `b9ca64573a3a0e01ad7c0584d5a88da1ae69e0b1`
- official_diffusion_policy:
  source `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`

Command / Job:
- job_id: `n/a` planned local GPU debug run.
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/<timestamp>`
- planned official DP command:
  `cd $DP && CUDA_VISIBLE_DEVICES=0 PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp task.dataset_path=$DATASET task.dataset.val_ratio=0.25 training.device=cuda:0 training.num_epochs=8 training.max_train_steps=12 training.max_val_steps=4 training.lr_warmup_steps=5 policy.num_inference_steps=8 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir=$OUT/official_dp_train`

Acceptance:
- Training completes without NaNs/divergence and writes a checkpoint.
- `logs.json.txt` contains multiple epochs with lower final train loss than the
  initial epoch, and validation loss is finite/non-explosive.
- Checkpoint bridge smokes for open/closed/lift-high rows produce finite action
  ranges. Range saturation is acceptable only as a debug signal; any severe
  unexpected z/gripper behavior blocks closed-loop eval proposal.

Next:
- Validate the report utility locally, launch the bounded local GPU run,
  inspect logs/curves/checkpoint ranges, open artifacts with `viz-open`, then
  update/commit/push the worklog and report code.

## 2026-06-11T18:13:31-07:00 - official DP debug pretrain identity-normalizer finding

Goal:
- Inspect whether a bounded contact-aware official-DP debug pretrain is
  coherent enough to propose closed-loop DP eval.

Command / Job:
- job_id: `n/a` local RTX 6000 runs.
- run_dirs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain_20260611_180838`
  and
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain40_20260611_181130`
- training commands:
  official `train.py` with the accepted contact-aware NPZ, first
  `num_epochs=8 max_train_steps=12`, then bounded longer
  `num_epochs=40 max_train_steps=20`, both using the existing
  `task.dataset.action_normalizer=identity`.

Result:
- 8-epoch run:
  train loss reduced `1.05396 -> 0.599753`, val loss `1.03991 -> 0.649757`.
  Enhanced action-range smoke showed direct and bridge pose actions still
  touching normalized bounds while label ranges were narrow.
- 40-epoch run:
  train loss reduced to `0.03293`, val loss to `0.05811`,
  train_action_mse_error to `0.57264`.
  EMA, raw-model, and 25-step inference action smokes all still sampled broad
  pose ranges. Example: first/open label first action had `dz` in
  `[-0.585, -0.419]` and gripper `+1`, while policy chunks still touched
  `[-1, 1]` in pose dimensions; closed/lift labels had `dz ~= +0.407` and
  gripper `-1`, but sampled chunks still spanned clip bounds.

Analysis:
- This is not closed-loop eval ready. Loss reduction alone is insufficient.
- Raw vs EMA did not explain the broad samples, and increasing inference steps
  from 8 to 25 did not fix it.
- The likely config issue is the DP internal action normalizer. The adapter
  used identity because DEXTRAH actions are already normalized controller
  commands, but official DP sampling with a clipped DDPM scheduler can still
  explore the full `[-1, 1]` controller range. For this tiny contact-aware
  dataset, `action_normalizer=limits` should train/sample in normalized dataset
  coordinates and unnormalize back to the dataset's actual action support.

Next:
- Run one bounded limits-normalizer diagnostic with the same accepted NPZ and
  short local GPU budget. Do not run closed-loop DP eval, full BC, or RL.

## 2026-06-11T18:19:01-07:00 - official DP contact-aware debug pretrain artifacts

Goal:
- Produce the requested bounded official-DP debug pretrain artifacts and decide
  whether checkpoint evidence is coherent enough to propose closed-loop DP eval.

Change:
- Added `limits_clamp_constant` action normalization in
  `dextrah_lab/offline_dp_bc/dp_dataset.py`: ordinary action dimensions use
  limits normalization, while near-constant action dimensions unnormalize
  clipped samples to `mean +/- 5e-5` instead of full `[-1, 1]` controller
  commands. This keeps zero-rotation contact-aware labels near zero while
  preserving DEXTRAH's 7D action schema.
- Enhanced `validate_official_checkpoint_smoke.py` with selected dataset label
  action ranges, full-chunk ranges, and `--policy-source {auto,ema,raw}`.
- Added `make_official_dp_pretrain_report.py` for loss CSV/PNG and
  action-range report generation.
- Updated `make_lowdim_dataset_report.py` to record the action normalizer used.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cb6501561424151b295e88b7f3c9b04a9b4b577d`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/offline_dp_bc/dp_dataset.py`,
  `dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py`,
  `dextrah_lab/offline_dp_bc/make_official_dp_pretrain_report.py`,
  `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`,
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`.
- official_diffusion_policy:
  source `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`.

Command / Job:
- job_id: `n/a`, local RTX 6000 debug pretrains.
- accepted dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- final selected run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656`
- final train command:
  `cd $DP && CUDA_VISIBLE_DEVICES=0 PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp task.dataset_path=$DATASET task.dataset.val_ratio=0.25 task.dataset.action_normalizer=limits_clamp_constant training.device=cuda:0 training.num_epochs=100 training.max_train_steps=20 training.max_val_steps=4 training.lr_warmup_steps=10 training.checkpoint_every=10 policy.num_inference_steps=8 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir=$OUT/official_dp_train`
- checkpoint smokes:
  `validate_official_checkpoint_smoke.py` on `first`,
  `gripper_closed`, and `lift_high` rows with
  `--num-inference-steps 8 --warm-history-from-dataset`.

Intermediate Results:
- Identity action normalizer:
  40-epoch bounded run reached train loss `0.03293`, val loss `0.05811`, but
  EMA/raw/25-step action smokes still sampled broad pose ranges; not eval-ready.
- Official `limits` action normalizer:
  controlled xyz action range but let near-zero rotation channels unnormalize
  to full `[-1, 1]`; not eval-ready.
- `limits_clamp_constant` action normalizer:
  fixed pose/rotation range coherence. 40-epoch run reached
  train_action_mse_error `0.21911`; 100-epoch run reached `0.21772`.

Final Result:
- status: diagnostic complete, checkpoint verdict `needs_review`.
- final checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/official_dp_train/checkpoints/latest.ckpt`
- loss reduction:
  train loss `1.04153 -> 0.01449`, val loss `1.02373 -> 0.08477`.
- action-MSE:
  `0.28863 -> 0.21772`; improved but plateaued above a comfortable eval gate.
- action-range smokes:
  pose/rotation ranges are now bounded by dataset support and constant rotations
  stay near `+/-5e-5`, but gripper sign remains mixed. Open rows have label
  gripper `+1` while predicted direct/bridge first actions include negative
  gripper. Closed/lift rows have label gripper `-1` while predicted first
  action max remains positive (`~0.74` bridge in the final run).
- decision:
  Do not launch closed-loop DP eval, full BC, or RL warm-start from this
  checkpoint. The next fix should target gripper conditioning/loss/schedule
  before simulator eval.

Viewer URLs:
- pretrain report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/official_dp_pretrain_report.md`
- loss plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/loss_curves.png`
- parsed loss CSV:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/loss_history.csv`
- resolved Hydra config:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/official_dp_train/.hydra/config.yaml`
- train stdout:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/logs/official_dp_debug_pretrain.log`
- action-range smoke logs:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/logs/checkpoint_action_range_first.log`,
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/logs/checkpoint_action_range_gripper_closed.log`,
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/logs/checkpoint_action_range_lift_high.log`
- summary JSON:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_clampconst_20260611_181656/official_dp_pretrain_summary.json`

Analysis:
- The official-DP mechanics and loss gates are now proven on contact-aware
  relabel data, and the custom action normalizer resolves the translation and
  constant-rotation range bug introduced by raw identity/limits normalization.
- BC readiness is still blocked by gripper sign uncertainty. Since close/lift
  success depends on gripper timing, closed-loop eval would likely produce
  another ambiguous or misleading video until gripper behavior is fixed.

Next:
- Keep the checkpoint/artifacts as a diagnostic baseline only.
- Next bounded fix options: add an explicit gripper-phase/timestep conditioning
  feature to the 21D lowdim obs, use a deterministic gripper schedule wrapper
  for this staged contact-aware dataset, or train a separate binary gripper
  head/distillation target. Any option needs a new small smoke and action-range
  artifact before closed-loop DP eval.

## 2026-06-11T18:27:42-07:00 - official DP gripper sign mismatch audit plan

Goal:
- Isolate the remaining contact-aware official-DP gripper sign incoherence
  before any closed-loop eval, full BC, or RL handoff.

Hypothesis:
- The current `needs_review` verdict may be caused by either a real learned
  gripper sign/conditioning failure or a row/window comparison bug in the
  action-range smoke. The bounded next step is to query the official
  `real-stanford/diffusion_policy` checkpoint offline on exact dataset windows,
  compare predictions to labels under the policy's `oa_step_convention`, and
  produce per-channel label-vs-predicted distributions by row selector/phase.

Change:
- Planned only before edits. Extend the existing offline official-DP action
  semantics diagnostic rather than adding an overlapping reimplementation.
- Required checks: DEXTRAH action dim 6 convention (`+1` open, `-1` close),
  dataset open/closed/lift rows, checkpoint normalizer, bridge history/extract
  path, predicted-vs-label action distributions, and temporal offsets
  `t`, `t+1`, and future horizon labels.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- worklog:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `70ce1596b7e31695d32d4f9a52a5682e1a25e5fd`
- implementation_commit: pending
- changed_files: pending
- official_diffusion_policy:
  source `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`.

Command / Job:
- Planned local offline command only, no simulator rollout:
  `diagnose_dp_action_semantics.py --checkpoint <latest.ckpt> --dataset <contact_relabel_set_accepted.npz> --output-dir <gripper_audit_run> ...`

Result:
- status: planned.

Next:
- Patch diagnostics, validate locally, run the bounded audit, inspect plots/CSV,
  and only then decide whether a bounded training/loss/config fix is warranted.

## 2026-06-11T18:40:00-07:00 - official DP gripper sign audit results

Goal:
- Verify gripper label convention, normalizer behavior, and row-conditioned
  official-DP predictions before trying any bounded fix.

Change:
- Extended `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py` to:
  sample bulk row selectors (`first`, `gripper_open`, `gripper_closed`,
  `lift_high`), decode contact-aware relabel phases (`align_open`,
  `close_hold`, `lift`), dump checkpoint action normalizer stats, and produce
  per-channel label-vs-predicted CSV/PNG artifacts.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `70ce1596b7e31695d32d4f9a52a5682e1a25e5fd`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`,
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`.

Command / Job:
- command:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python -m dextrah_lab.offline_dp_bc.diagnose_dp_action_semantics --checkpoint $CKPT --dataset $DATASET --output-dir $OUT --diffusion-policy-root $DP --device cuda:0 --num-inference-steps 8 --policy-source auto --episode-index 2 --row-selector first --row-selector gripper_open --row-selector gripper_closed --row-selector lift_high --samples-per-selector 16 --gripper-pass-fraction 0.95 --report-all-channels`
- job_id: `n/a`, local offline checkpoint query.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835`
- logs:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/logs/gripper_sign_audit.log`

Result:
- status: failed gripper gate, but diagnostic is coherent.
- action dim 6 convention: dataset and DEXTRAH bridge use `+1` open,
  `-1` close.
- dataset labels: contact-aware NPZ phases are `align_open`, `close_hold`,
  `lift`; phase 0 labels are all `+1`, phases 1/2 are all `-1`.
- normalizer: checkpoint action dim 6 min/max is `-1/+1`, scale/offset is
  `1/0`; no normalizer sign flip.
- EMA checkpoint sign match: open rows `0.5909`, closed/lift rows `0.5556`;
  gate threshold `0.95`, verdict `fail`.
- Raw model check also failed: open `0.5294`, closed/lift `0.5294`.
- Phase note: the earlier
  `gripper_sign_audit_clampconst100_20260611_1829` artifact used stale
  pick/lift phase decoding and should not be used for phase claims; the
  phasefix artifact above supersedes it.

Viewer URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/action_semantics_report.md`
- gripper distribution plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/gripper_label_vs_prediction.png`
- per-channel scatter:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/per_channel_first_action_scatter.png`
- CSV:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/action_semantics_rows.csv`
- channel CSV:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_gripper_audits/gripper_sign_audit_clampconst100_phasefix_20260611_1835/action_semantics_channel_stats.csv`

Analysis:
- This rules out a DEXTRAH gripper sign flip and checkpoint normalizer flip.
- The returned-action label alignment is still not strong: best-offset counts
  are often `-2` or `+7`, and both EMA/raw models behave like a noisy,
  partially fit distribution on gripper dim 6. The next bounded fix should
  target official-DP training semantics before any simulator eval.

Next:
- Try one bounded official-DP pretrain with `pred_action_steps_only=true` so
  the diffusion loss is applied to the same 8-step action window consumed by
  the eval bridge. Do not run closed-loop DP eval unless row-conditioned
  open/closed/lift gripper smokes pass.

## 2026-06-11T18:41:00-07:00 - pred-action-steps-only bounded pretrain launch

Goal:
- Test whether applying official-DP loss only to the returned 8-step action
  window fixes contact-aware gripper sign predictions.

Hypothesis:
- The previous checkpoint trained the full 16-step trajectory while eval uses
  only the `oa_step_convention` returned action window. With the tiny
  contact-aware dataset and abrupt open/close phase transitions, unused horizon
  loss may be diluting the gripper schedule. `pred_action_steps_only=true`
  should align training loss with eval/bridge consumption.

Change:
- Config-only bounded attempt from official
  `real-stanford/diffusion_policy`; no DEXTRAH source edits after commit
  `5d845f7`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `5d845f74f8d55a93065b810a8ada01215acda0a0`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- changed_files: worklog launch entry pending
- official_diffusion_policy:
  source `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`,
  commit `5ba07ac6661db573af695b419a7947ecb704690f`,
  remote `https://github.com/real-stanford/diffusion_policy`.

Command / Job:
- job_id: `n/a`, local RTX 6000 debug pretrain.
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841`
- train command:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp task.dataset_path=$DATASET task.dataset.val_ratio=0.25 task.dataset.action_normalizer=limits_clamp_constant pred_action_steps_only=true training.device=cuda:0 training.num_epochs=100 training.max_train_steps=20 training.max_val_steps=4 training.lr_warmup_steps=10 training.checkpoint_every=10 policy.num_inference_steps=8 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir=$RUN/official_dp_train`

Acceptance:
- finite train/val losses with reduction;
- generated report, loss CSV/PNG, resolved config, stdout, checkpoint path;
- checkpoint smokes for `gripper_open`, `gripper_closed`, and `lift_high`;
- corrected action-semantics diagnostic must pass or clearly improve gripper
  sign for open rows and closed/lift rows. No closed-loop eval on failure.

Result:
- status: initial launch failed before training.
- error:
  Hydra rejected `policy.action_loss_weights=[1,1,1,1,1,1,8]` because the
  config is structured and the key is new. This is a launch syntax issue.
- fix:
  Relaunch with additive override
  `+policy.action_loss_weights=[1,1,1,1,1,1,8]`.

## 2026-06-11T18:44:00-07:00 - weighted gripper-loss bounded pretrain result

Goal:
- Evaluate whether the weighted gripper-loss official-DP checkpoint fixes
  open/closed/lift gripper sign under row-conditioned smokes.

Result:
- status: partially passed; no closed-loop eval launched.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/official_dp_train/checkpoints/latest.ckpt`
- official DP policy target:
  `dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy`
- train/val loss:
  weighted train `2.13880 -> 0.04900`, weighted val
  `2.13588 -> 0.16774`, `train_action_mse_error=0.19449`.
- 8-step inference smokes: still `needs_review`; bulk gripper gate failed
  with open sign match `0.4545`, closed/lift sign match `0.5778`.
- 100-step inference smokes: row-conditioned selectors passed for both
  direct official-DP action and PPO bridge action:
  - `first`: label `+1`, direct gripper `0.952..1.000`, bridge
    `0.907..1.000`.
  - `gripper_open`: label `+1`, direct `0.927..1.000`, bridge
    `0.818..1.000`.
  - `gripper_closed`: label `-1`, direct `-1.000..-0.966`, bridge
    `-1.000..-0.973`.
  - `lift_high`: label `-1`, direct `-1.000..-0.965`, bridge
    `-1.000..-0.971`.
- 100-step bulk action-semantics audit:
  aggregate gripper gate `pass`; open sign match `1.0`, closed/lift sign
  match `0.9556`. One exact first `close_hold` demo reference still predicted
  open (`+0.38`), so this is a gripper-sign mechanics pass, not a closed-loop
  readiness claim.

Viewer URLs:
- weighted pretrain report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/official_dp_pretrain_report.md`
- weighted loss plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/loss_curves.png`
- 8-step gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/gripper_sign_audit/gripper_label_vs_prediction.png`
- 100-step gripper report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/gripper_inference100_report.md`
- 100-step gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/gripper_sign_audit_100steps/gripper_label_vs_prediction.png`
- 100-step per-channel plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/gripper_sign_audit_100steps/per_channel_first_action_scatter.png`
- 100-step summary JSON:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/gripper_inference100_summary.json`
- resolved config:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/official_dp_train/.hydra/config.yaml`
- train stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/logs/official_dp_debug_pretrain.log`

Analysis:
- The gripper sign incoherence was not a label sign, normalizer, bridge flip,
  or EMA-only bug. It is sensitive to diffusion sampling noise and loss
  weighting. The accepted bounded setting is currently: weighted gripper loss
  `8`, `pred_action_steps_only=true`, and `num_inference_steps=100`.
- The 8-step checkpoint smokes for this checkpoint remain invalid for behavior
  claims. Any later closed-loop eval must use the 100-step inference setting
  and trace action timing.
- The first close-boundary reference remains a risk; a closed-loop eval could
  still delay close by one/few steps. This should be traced explicitly rather
  than hidden.

Next:
- Proposed next action, not launched here: a bounded no-video closed-loop
  DEXTRAH/Isaac trace using this weighted checkpoint with
  `num_inference_steps=100`, `ACTION_CHUNK_STEPS=1` or a very small chunk,
  support tracing, gripper/EE/cube plots, and contact sheet/video only if the
  no-video trace is sane.

## 2026-06-11T18:44:04-07:00 - weighted checkpoint closed-loop trace plan

Goal:
- Run a bounded no-video DEXTRAH/Isaac closed-loop trace for the weighted
  contact-aware DP checkpoint that passed offline gripper sign mechanics at
  100 inference steps.

Hypothesis:
- If the remaining train/eval path is coherent, the trace should have finite
  actions, history gap `1`, support phase progression from `align_open` toward
  `close_hold/lift`, and gripper close timing that does not occur while the
  end-effector/fingers are obviously far from the cube. Failure should identify
  whether the issue is action timing, observation/history bridge, support drift,
  chunking, or policy output.

Change:
- Patch planned/implemented before launch:
  - Decode contact-aware relabel phases as `align_open`, `close_hold`, `lift`
    in `eval_franka_cube_dp_policy.py`.
  - Write `eval_config.json` beside metrics for closed-loop trace provenance.
  - Add `closed_loop_action_components.png` to
    `make_closed_loop_support_report.py`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `4d51e503d87bf7e527ddd34ac192a4025dce7b3d`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`,
  `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`,
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`

Command / Job:
- planned run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_1844`
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt`
- support dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`
- expected settings:
  `NUM_ENVS=1`, `NUM_STEPS=96`, `NUM_INFERENCE_STEPS=100`,
  `ACTION_CHUNK_STEPS=1`, `CAPTURE_VIDEO=False`,
  `DEBUG_POLICY_TRACE_MAX_CALLS=96`, `SUPPORT_DATASET=<accepted contact-aware NPZ>`.
- expected artifacts: stdout log, `metrics.json`, `eval_config.json`,
  `policy_trace.json`, `support_trace.json/csv`, local support report/plots.

Acceptance:
- Bounded trace completes requested steps with finite actions and clean env
  close.
- History gaps remain `1`.
- Action schema remains 7D and gripper sign/timing is understandable.
- If support/behavior fails, do not run video or scale; inspect traces and
  patch the concrete mismatch.

Result:
- status: planned, pending commit/deploy/launch.

## 2026-06-11T18:42:00-07:00 - pred-action-steps-only bounded pretrain result and weighted-loss plan

Goal:
- Inspect the `pred_action_steps_only=true` bounded official-DP run and decide
  whether it clears the gripper-sign gate.

Result:
- status: failed gripper gate; no closed-loop eval authorized.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/official_dp_train/checkpoints/latest.ckpt`
- train/val loss:
  train `1.04719 -> 0.01737`, val `1.02318 -> 0.07671`;
  `train_action_mse_error=0.19694`.
- official-DP config mechanics: passed finite train and checkpoint creation.
- checkpoint action-range report verdict: `needs_review`.
- corrected action semantics audit:
  open sign match `0.4091`, closed/lift sign match `0.5778`,
  gripper gate `fail`.

Viewer URLs:
- pretrain report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/official_dp_pretrain_report.md`
- loss plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/loss_curves.png`
- gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/gripper_sign_audit/gripper_label_vs_prediction.png`
- per-channel plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/gripper_sign_audit/per_channel_first_action_scatter.png`
- train stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/logs/official_dp_debug_pretrain.log`
- resolved config:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_predsteps_20260611_1841/official_dp_train/.hydra/config.yaml`

Analysis:
- This rejects the hypothesis that full-horizon loss alone caused the
  gripper-sign incoherence. Gripper predictions remain noisy/saturated and
  often wrong even when training only the returned action window.
- The next conservative fix should keep the 21D lowdim bridge schema intact:
  add a small official-DP subclass that preserves the official sampler/model
  and applies a heavier per-channel denoising loss weight on action dim 6.

Next:
- Validate and commit `WeightedDiffusionUnetLowdimPolicy`, then run one
  bounded local official-DP pretrain with
  `policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy`,
  `pred_action_steps_only=true`, and gripper loss weight `8`. Stop after
  checkpoint smokes and action-semantics artifacts.

## 2026-06-11T18:43:00-07:00 - weighted gripper-loss bounded pretrain launch

Goal:
- Test whether a per-channel gripper loss weight fixes row-conditioned gripper
  sign while keeping the accepted 21D contact-aware dataset and PPO bridge
  schema unchanged.

Change:
- Added `dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy`,
  a small subclass of the official lowdim Diffusion Policy that only applies
  action-channel weights inside `compute_loss`. Inference, normalizer, sampler,
  and model architecture remain official DP.

Version Control:
- implementation_commit: `c7b9701cf06d6a1aea05647519102d030a7e3347`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- changed_files:
  `dextrah_lab/offline_dp_bc/weighted_diffusion_policy.py`,
  `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`.

Command / Job:
- job_id: `n/a`, local RTX 6000 debug pretrain.
- planned run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_pretrain/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843`
- train command:
  `PYTHONPATH=$DP:$DEX $VENV/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy 'policy.action_loss_weights=[1,1,1,1,1,1,8]' task.dataset_path=$DATASET task.dataset.val_ratio=0.25 task.dataset.action_normalizer=limits_clamp_constant pred_action_steps_only=true training.device=cuda:0 training.num_epochs=100 training.max_train_steps=20 training.max_val_steps=4 training.lr_warmup_steps=10 training.checkpoint_every=10 policy.num_inference_steps=8 dataloader.batch_size=32 val_dataloader.batch_size=32 hydra.run.dir=$RUN/official_dp_train`

Acceptance:
- Same as previous gate: finite loss reduction plus row-conditioned gripper
  sign pass for open rows and closed/lift rows. Failure means no closed-loop
  eval and likely requires explicit phase/progress conditioning or a
  deterministic gripper schedule wrapper.

Result:
- status: launching.

## 2026-06-11T18:47:32-07:00 - weighted checkpoint closed-loop trace launch

Goal:
- Run the first bounded DEXTRAH/Isaac closed-loop trace for the weighted
  contact-aware official-DP checkpoint after the offline 100-step gripper-sign
  gate passed. This is trace-only: no video, no full BC, no RL.

Hypothesis:
- If the weighted checkpoint and PPO-observation bridge are mechanically
  coherent in Isaac, a 96-step `ACTION_CHUNK_STEPS=1` trace should stay finite,
  show correct 21D lowdim/support-trace decoding, and expose whether gripper
  timing or EE/cube geometry fails before a video launch.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `eeac1dfeaa29c0ea1a8b126a719065efeddf37e3`
- official_dp_commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- push/pull: pushed local branch; l401 GitHub SSH fetch was externally blocked
  by `Permission denied (publickey)`, so the exact commit was deployed to the
  agent-owned l401 worktree via `git bundle` and checked out detached.
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `eeac1dfeaa29c0ea1a8b126a719065efeddf37e3`, detached clean.

Command / Job:
- job_id: `1027977`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732,NUM_ENVS=1,NUM_STEPS=96,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=96,CAPTURE_VIDEO=False,VIDEO_LENGTH=96,PRINT_INTERVAL=12,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=96,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027977.out`
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt`
- support_dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz`

Acceptance:
- Finite sim and traces, `eval_config.json` present, no obvious
  action-schema/normalizer/history mismatch, support/action traces inspectable.
  A video launch is not allowed unless this no-video trace is coherent.

Result:
- status: running on `pool0-00004` as of initial log poll.

## 2026-06-11T18:53:20-07:00 - weighted trace96 result and source-joint reset patch

Goal:
- Inspect the first weighted-checkpoint closed-loop no-video trace and decide
  whether it is sane enough for video or needs a narrower train/eval-support
  diagnostic.

Version Control:
- base_commit: `eeac1dfeaa29c0ea1a8b126a719065efeddf37e3`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`,
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`,
  `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`,
  this worklog.

Command / Job:
- completed job_id: `1027977`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732/logs/eval_franka_cube_dp_policy_1027977.out`

Artifacts:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732/closed_loop_support_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732/closed_loop_support_trace.png`
- action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace96_chunk1_20260611_184732/closed_loop_action_components.png`
- metrics/config/traces:
  `metrics.json`, `policy_trace.json`, `support_trace.csv/json`,
  `eval_config.json` in the same local artifact dir.

Result:
- status: failed support-drift gate; no video launch and no scale-up.
- Slurm: `COMPLETED 0:0`.
- official DP checkpoint loaded as
  `WeightedDiffusionUnetLowdimPolicy`, `num_inference_steps=100`,
  `action_chunk_steps=1`, `debug_policy_trace_records=96`.
- metrics:
  success/window success `0/0`, cube lift max `0`, reward mean/final
  `1.540/1.790`, final gripper width `0.01538 m`,
  final/min EE-to-cube `0.178/0.178 m`, final/min finger-center-to-cube
  `0.1577/0.1577 m`.
- action range:
  xyz min/max `[-0.00956,-0.01684,-0.73772]` /
  `[-0.00956,0.24866,0.33659]`, gripper `[-1.0,0.62325]`.
- support trace:
  nearest phase `align_open` for all 96 steps, nearest row episode/step
  `1/0`, history gaps `[0,1]`, support distance start/final
  `29.57/20.85`.
- event timing:
  first negative gripper at step `1`; first hard close at step `5`, while
  EE-to-cube was still `0.231 m` and finger-center-to-cube `0.218 m`.
- live-vs-demo geometry:
  live cube-minus-EE at start/final
  `[0.1456,-0.1812,0.0178]` / `[0.1428,-0.1047,0.0186]`;
  nearest relabel row cube-minus-EE
  `[0.000018,-0.01989,-0.02012]`.

Analysis:
- The policy/bridge mechanics are finite, and the observation history cadence
  remains fixed. The failure is not chunking.
- The relabel dataset begins from a contact-aware source-joint/finger-center
  state near the cube; the normal task reset starts far outside that support.
  This means a cube-only reset or normal reset cannot evaluate whether the
  weighted checkpoint is a coherent relabel prior.
- Existing `--demo_reset_dataset` only writes cube pose/goal. That is
  insufficient for the contact-aware set because the accepted NPZ intentionally
  dropped source robot joint metadata.

Change:
- Added optional `--demo_reset_source_trajectory_json` and
  `--demo_reset_source_frame` to `eval_franka_cube_dp_policy.py`.
- When supplied with `--demo_reset_dataset`, the evaluator now writes the raw
  source `joint_position` to the Franka articulation and controller targets,
  matching the contact-aware relabel rollout reset path.
- Added matching Slurm wrapper environment variables and report fields for
  source-joint reset availability/frame and joint write Linf diff.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`
- all passed.

Next:
- Commit/push/deploy this patch, then run a bounded no-video matched reset
  trace using accepted contact episode `1` step `0` with source trajectory
  `/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json`
  and source frame `260`. Acceptance is improved reset lowdim diff/support
  distance and coherent gripper timing; if that still hard-closes away from
  the cube, the next issue is policy output/conditioning, not reset.

## 2026-06-11T18:55:03-07:00 - matched source-joint reset trace launch

Goal:
- Test whether starting the eval env from the same contact-aware relabel
  robot/cube reset eliminates the support drift seen in normal reset.

Hypothesis:
- If the weighted checkpoint is usable when initialized inside relabel support,
  the source-joint reset should report low reset diffs, nearest-demo phase
  should advance beyond `align_open`, and gripper closure should occur near
  contact instead of at 18-23 cm away.

Version Control:
- implementation_commit: `ec5ebb05611dde63ebbb7f42fb64d5563daa08cb`
- push/pull: pushed to `origin/codex/franka-cube-diffusion-policy-bc`;
  deployed to l401 agent worktree via Git bundle because l401 GitHub SSH fetch
  remains blocked.
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `ec5ebb05611dde63ebbb7f42fb64d5563daa08cb`, detached clean.

Command / Job:
- job_id: `1027980`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503,NUM_ENVS=1,NUM_STEPS=160,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=160,CAPTURE_VIDEO=False,VIDEO_LENGTH=160,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=160,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027980.out`

Acceptance:
- Finite no-video trace, source joint reset actually applied with low joint and
  lowdim/cube-minus-EE reset diffs, history gaps `[0,1]`, support trace no
  longer starts tens of normalized units away. If gripper still closes early
  away from the cube, policy output/conditioning remains the blocker.

Result:
- status: completed and inspected; no DP/RL scale-up.
- Slurm: `COMPLETED 0:0`, elapsed `00:02:21`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939`
- fetched artifacts:
  `metrics.json`, `policy_trace.json`, `support_trace.csv/json`,
  `eval_config.json`, stdout log, mp4, labeled contact sheet,
  `closed_loop_support_report.md`, `closed_loop_support_trace.png`,
  `closed_loop_action_components.png`,
  `closed_loop_support_summary.json`, `closed_loop_support_key_rows.csv`.
- viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939/closed_loop_support_report.md`
  - support plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939/closed_loop_support_trace.png`
  - action plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939/closed_loop_action_components.png`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939/closed_loop_contact_sheet.jpg`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939/videos/franka-cube-dp-weighted-sourcejoint-step-0.mp4`
- video metadata: `1280x720`, `159` frames, `2.65 s`, `60 fps`.
- reset gate: exact again. `source_joint_reset_available=true`,
  `joint_linf_diff_after_write_env0=0`, `lowdim_l2_diff_env0=0`,
  `cube_minus_ee_l2_diff_env0=0`.
- final metrics:
  success/window success `0/0`, reward mean/final `4.284/8.158`,
  cube lift max/final `0.10099 m`, final EE-to-cube `0.00976 m`,
  final finger-center-to-cube `0.04032 m`, final gripper width
  `0.04650 m`, final cube goal height error `0.05901 m`.
- support/action trace:
  history gaps `[0,1]`; nearest phases `align_open=28`,
  `close_hold=65`, `lift=67`; support distance start/final
  `0.04035/1.395`. First negative gripper at step `27`; first hard
  close at step `29`, with EE-to-cube already around `6.7 mm`.
- visual inspection:
  the labeled contact sheet and mp4 show the hand starts near/contacting the
  cube, closes/lifts it, and holds it near the gripper. This is not the old
  drift-away/ignore-cube failure mode.

Analysis:
- The matched source-joint reset resolves the earlier closed-loop support
  mismatch for this checkpoint: reset lowdim, cube pose, and source joints all
  match, and the policy reaches/lifts the cube.
- The run still fails the task success gate. The cube success predicate in
  `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  requires `cube_lift_height >= cube_success_lift_height`; the configured
  threshold is `0.12 m`, while this bounded run reaches `0.10099 m`.
  XY and hand-distance terms are already within tolerance, so the immediate
  measured blocker is insufficient lift height.
- The gripper remains partly open at about `4.65 cm`. It is not directly part
  of the success predicate, but it likely limits lift robustness and should be
  audited before any closed-loop scale-up.
- This result justifies more contact-aware relabel/policy debugging, not
  full DP BC or RL warm-start. The next bounded path should target lift-height
  and gripper closure/hold under matched reset, then re-test normal-reset
  support only after the matched-reset policy reliably reaches success.

Next:
- Do not scale RL or full BC. Candidate bounded diagnostics are: extend the
  matched-reset horizon modestly to see whether it crosses `0.12 m`, inspect
  weighted-checkpoint gripper/lift action over the final lift rows, and/or add
  more accepted contact-aware relabel lift support with stronger close/hold
  before any new official DP training.

## 2026-06-11T19:08:46-07:00 - matched source-joint trace240 launch plan

Goal:
- Run the cheapest bounded lift/gripper diagnostic after the matched-reset
  video: extend only the matched source-joint rollout horizon, with no video
  and no training, to test whether the current weighted checkpoint crosses the
  `0.12 m` lift success threshold.

Hypothesis:
- In job `1027987`, lift was still increasing at step `160` and reached
  `0.10099 m`; a modest `240`-step no-video trace should determine whether
  the current policy simply needed more horizon or whether lift/gripper
  geometry saturates below success.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: pending worklog commit before launch
- changed_files: owned worklog only

Command / Job:
- planned run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846`
- planned command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846,NUM_ENVS=1,NUM_STEPS=240,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,CAPTURE_VIDEO=False,VIDEO_LENGTH=240,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=240,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846`
- expected logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_<job_id>.out`

Acceptance:
- Fetch metrics/traces/logs and generate the support/action report. If max
  lift crosses `0.12 m` or reaches near-threshold with coherent success-region
  terms, run one short matching video/contact sheet. If lift saturates below
  threshold or success remains false for concrete geometry reasons, record the
  blocker and move to gripper/lift action audit or relabel support augmentation.

Result:
- status: launched as Slurm job `1027995`; monitoring.

## 2026-06-11T19:13:34-07:00 - matched source-joint trace240 result

Goal:
- Inspect the longer-horizon matched-reset trace and decide whether the
  current weighted checkpoint can cross the lift success threshold without
  any training or relabel changes.

Version Control:
- implementation_commit: `10f7a0ac9dc0c7bf52debf5b993aec2af5ae9a2b`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `10f7a0ac9dc0c7bf52debf5b993aec2af5ae9a2b`, detached clean.

Command / Job:
- job_id: `1027995`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/logs/eval_franka_cube_dp_policy_1027995.out`

Viewer URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/closed_loop_support_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/closed_loop_support_trace.png`
- action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/closed_loop_action_components.png`
- lift threshold audit:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/lift_threshold_audit.png`
- lift threshold CSV:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace240_chunk1_sourcejoint_ep1s0_20260611_190846/lift_threshold_audit.csv`

Result:
- status: transient matched-reset success; not durable task success; no
  BC/RL scale-up.
- Slurm: `COMPLETED 0:0`.
- reset gate: exact. `source_joint_reset_available=true`,
  `joint_linf_diff_after_write_env0=0`, `lowdim_l2_diff_env0=0`,
  `cube_minus_ee_l2_diff_env0=0`.
- official DP checkpoint:
  `/results/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt`,
  official DP commit `5ba07ac6661db573af695b419a7947ecb704690f`.
- steps/traces: `240`, `policy_trace_records=240`,
  `support_trace_records=240`, history gaps `[0,1]`.
- lift/success:
  first success step `172`, last success step `183`, max lift
  `0.13634 m` at step `183`, `success_steps=12`,
  `window_success_rate=0.15`.
- hold/loss:
  by step `184`, metrics show cube lift reset to `0`, gripper width returns
  open around `0.08 m`, EE-to-cube jumps to `0.184 m`, and reward later
  returns to reset-like values. Final success/lift are `0/0`.
- final metrics after the drop:
  final gripper width `0.01185 m`, final EE-to-cube `0.1615 m`,
  final finger-center-to-cube `0.1647 m`, final reward `1.677`.

Analysis:
- Horizon alone is enough for the current weighted checkpoint to cross the
  environment success predicate under exact source-joint reset. This resolves
  the earlier “cannot reach 0.12 m” question.
- The behavior is not durable: it holds success only for about 12 env steps
  before the cube is lost/reset. This is a hold-stability/grasp robustness
  blocker, not a broad reset-drift or action-schema blocker.
- Because the trace crosses success and then drops immediately, one short
  matched-reset video is warranted to inspect the hold/loss event. The video
  should stop near `190` steps to capture the success interval and immediate
  loss without producing unnecessary video spam.

Next:
- Launch one bounded matched-reset `NUM_STEPS=190` video/contact-sheet run with
  the same checkpoint/reset/settings. Acceptance is visual confirmation of the
  transient lift and drop/reset timing. Do not train or scale RL.

## 2026-06-11T19:15:11-07:00 - matched source-joint video190 launch

Goal:
- Capture the transient success and immediate hold/loss behavior found in
  trace job `1027995` without running a broad video/eval sweep.

Version Control:
- implementation_commit: `9bb669227de9e09fa456dc2ffc87e195743e9932`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `9bb669227de9e09fa456dc2ffc87e195743e9932`, detached clean.

Command / Job:
- job_id: `1028005`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511,NUM_ENVS=1,NUM_STEPS=190,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,CAPTURE_VIDEO=True,VIDEO_LENGTH=190,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-sourcejoint-hold,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=190,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028005.out`

Acceptance:
- Fetch video/log/metrics/traces, generate support/action plots and a labeled
  contact sheet. The visual should answer whether the cube is dropped, reset
  after success, or held but failing a metric. No training or RL scale-up.

Result:
- status: completed and inspected; matched-reset task success achieved, then
  environment auto-reset; no BC/RL scale-up.
- Slurm: `COMPLETED 0:0`, elapsed `00:02:35`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511`
- fetched artifacts:
  `metrics.json`, `policy_trace.json`, `support_trace.csv/json`,
  `eval_config.json`, stdout log, mp4, `video_ffprobe.json`, labeled contact
  sheet, `closed_loop_support_report.md`, `closed_loop_support_trace.png`,
  `closed_loop_action_components.png`, `lift_threshold_audit.png/csv/json`,
  `closed_loop_support_summary.json`, `closed_loop_support_key_rows.csv`.
- viewer URLs:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/closed_loop_support_report.md`
  - support plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/closed_loop_support_trace.png`
  - action plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/closed_loop_action_components.png`
  - lift/hold audit:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/lift_threshold_audit.png`
  - lift/hold CSV:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/lift_threshold_audit.csv`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/closed_loop_contact_sheet.jpg`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video190_chunk1_sourcejoint_ep1s0_20260611_191511/videos/franka-cube-dp-weighted-sourcejoint-hold-step-0.mp4`
- video metadata: `1280x720`, `189` frames, `3.15 s`, `60 fps`.
- metrics:
  first success step `172`, last success step `183`, `success_steps=12`,
  window success `0.15`, max lift `0.13691 m` at step `183`, max/final
  success `1/0`, final lift `0`.
- gripper/contact during success:
  at first success, gripper width `0.04628 m`, EE-to-cube `0.00984 m`,
  finger-center-to-cube `0.04033 m`; at max lift, gripper width
  `0.04635 m`, EE-to-cube `0.00981 m`, finger-center-to-cube `0.04032 m`.
- post-success reset:
  step `184` shows lift `0`, gripper width `0.08 m`, EE-to-cube
  `0.184 m`, nearest-demo distance `24.4`, and then final success remains
  `0`. `done_count=1`.
- env semantics audit:
  `dextrah_lab/tasks/dextrah_franka_cube_grasp/franka_cube_grasp_env.py`
  terminates on `success_done` when `time_in_success_region >=
  cfg.success_timeout` and `episode_length_buf >=
  min_episode_steps_before_success`. Config sets `success_timeout=0.20`.
  The 12-step success interval is consistent with this success termination;
  the visible post-step-184 table state is an automatic reset after success,
  not a physical slip before success.

Analysis:
- The current weighted official-DP checkpoint can reach the Franka cube task
  success predicate under exact source-joint/contact-aware matched reset.
- This is still only transient success, not a durable warm-start claim:
  `success_steps=12`, `window_success_rate=0.15`, and the labeled video shows
  the success/max-lift window followed by a post-success reset/drop-looking
  state by frame `188`.
- The env code explains why final metrics are reset-contaminated:
  `success_done` terminates after `time_in_success_region >=
  success_timeout`, and `success_timeout=0.20`. Thus the visible post-step-184
  table state is consistent with an automatic success reset, not proof that
  the cube slipped before the env's own success termination.
- For warm-start readiness, this remains a hold-stability/contact-retention
  blocker: the current eval has not demonstrated that the checkpoint can hold
  the grasp beyond the 0.2 s success timeout, and final post-reset metrics are
  unusable for judging durable retention.
- This does not justify full BC/RL scale-up: success is only under exact
  source-joint matched reset from the tiny contact-aware relabel support. The
  normal task reset still needs either support expansion, reset conditioning,
  or a staged/evaluation wrapper before claiming a usable warm-start prior.

Next:
- Stop this bounded diagnostic path here. Do not run full DP BC/RL. The next
  bounded development step should specifically test hold stability/contact
  retention after lift, e.g. an eval mode that records max/window success and
  optionally continues physics for a short fixed horizon after success without
  auto-reset, or a small matched-reset-conditioned eval set across several
  accepted source episodes/seeds. Keep any follow-up trace-first and
  artifact-heavy.

## 2026-06-11T18:58:15-07:00 - matched source-joint trace160 result

Goal:
- Inspect job `1027980` artifacts before deciding whether video is warranted.

Version Control:
- implementation_commit: `ec5ebb05611dde63ebbb7f42fb64d5563daa08cb`
- remote_commit/status: l401 agent worktree at the same detached commit.

Command / Job:
- job_id: `1027980`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503/logs/eval_franka_cube_dp_policy_1027980.out`

Viewer URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503/closed_loop_support_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503/closed_loop_support_trace.png`
- action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace160_chunk1_sourcejoint_ep1s0_20260611_185503/closed_loop_action_components.png`

Result:
- status: coherent trace but not success-ready; no RL/scale-up.
- Slurm: `COMPLETED 0:0`.
- reset gate: passed exactly. `source_joint_reset_available=true`,
  `joint_linf_diff_after_write_env0=0`, `lowdim_l2_diff_env0=0`,
  `cube_minus_ee_l2_diff_env0=0`.
- mechanics:
  `steps=160`, `debug_policy_trace_records=160`,
  `support_trace_records=160`, history gaps `[0,1]`.
- final metrics:
  reward mean/final `4.065/7.599`, success/window success `0/0`,
  cube lift max/final `0.09025 m`, final EE-to-cube `0.00970 m`,
  final finger-center-to-cube `0.04031 m`, final gripper width
  `0.04667 m`.
- support:
  nearest phase counts `align_open=28`, `close_hold=72`, `lift=60`.
  Nearest-demo distance started low at `0.0403`, ended `1.418`.
- close timing:
  first negative gripper at step `27`, still nearest `align_open`, but
  already near the cube: EE-to-cube `0.00654 m`,
  finger-center-to-cube `0.04047 m`, live width `0.06386 m`.
  First hard close at step `29`, nearest `close_hold`, EE-to-cube
  `0.00673 m`, finger-center-to-cube `0.04014 m`.
- lift:
  `cube_lift_height > 1 cm` at step `105`; `> 8 cm` at step `153`;
  final lift `9.0 cm`, below the environment success/lift target.

Analysis:
- The original drift/ignore-cube video was caused in large part by
  train/eval reset support mismatch. With exact source joint and cube reset,
  the same weighted checkpoint reaches contact and lifts, so this is no
  longer the earlier train/eval mismatch failure mode.
- The remaining blocker is not action-schema or history cadence: it is
  gripper/contact/lift-goal geometry and possibly insufficient lift horizon or
  insufficient gripper closure/hold. Final gripper width around `4.7 cm`
  suggests the cube is being pinched/lifted but not squeezed to a fully closed
  state; success remains false because the cube lift goal is still about
  `7 cm` higher than reached.
- Support distance grows during lift because the live cube/EE relative
  geometry diverges from the small relabel set while still physically lifting.
  This means the next training data fix should expand contact-aware relabel
  support around lift trajectories rather than return to raw cuRobo labels.

Decision:
- A single short matched-reset video is warranted for visual confirmation,
  because the no-video trace is finite and coherent. This is not video spam and
  not a scale-up; it should use the same checkpoint/reset/settings and produce
  video/contact artifacts for inspection.

Next:
- Launch one bounded video eval with the same source-joint reset and
  `NUM_STEPS=160`, fetch video plus metrics/traces, generate contact sheet if
  possible, then decide whether to patch for longer lift horizon, gripper
  schedule/weighting, or a larger contact-aware relabel set.

## 2026-06-11T18:59:39-07:00 - matched source-joint video160 launch

Goal:
- Produce exactly one viewer-ready video for the coherent matched source-joint
  trace to verify visually whether the policy really contacts/lifts the cube
  or whether metrics are misleading.

Version Control:
- implementation_commit: `bfcfa3ff01333646f1ed3d44934952aa7f7b5c0b`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `bfcfa3ff01333646f1ed3d44934952aa7f7b5c0b`, detached clean.

Command / Job:
- job_id: `1027987`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939,NUM_ENVS=1,NUM_STEPS=160,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=160,CAPTURE_VIDEO=True,VIDEO_LENGTH=160,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-sourcejoint,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=160,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_video160_chunk1_sourcejoint_ep1s0_20260611_185939`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1027987.out`

Acceptance:
- Same metrics as trace160 plus an inspectable mp4/contact sheet. If the video
  confirms contact/lift, the next blocker is lift height/gripper geometry, not
  reset drift. If video contradicts metrics, debug visualization/metrics.

Result:
- status: completed and inspected; bounded matched source-joint no-reset hold
  diagnostic passes.
- Slurm: `COMPLETED 0:0`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200`
- fetched artifacts:
  `metrics.json`, `policy_trace.json`, `support_trace.csv/json`,
  `eval_config.json`, stdout log, `closed_loop_support_report.md`,
  `closed_loop_support_trace.png`, `closed_loop_action_components.png`,
  `closed_loop_support_summary.json`, `closed_loop_support_key_rows.csv`,
  `hold_retention_audit.png/csv/json`.
- viewer URLs:
  - hold retention plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200/hold_retention_audit.png`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200/closed_loop_support_report.md`
  - support plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200/closed_loop_support_trace.png`
- key metrics:
  `steps_completed=260`, `done_count=0`, `final_success_rate=1.0`,
  `window_success_rate=1.0`, `first_success_step=172`,
  `last_success_step=260`, `success_steps=89`, final/max lift
  `0.2457067 m`, final EE-to-cube `0.00953 m`, final
  finger-center-to-cube `0.04029 m`, final gripper width `0.04700 m`.
- timeout audit:
  `success_timeout_override={"original": 0.2, "override": 999.0}`.
  The previous post-success reset/drop-looking video was caused by normal env
  success termination after the built-in `0.20 s` success timeout; with reset
  disabled, the matched source-joint rollout keeps lifting and remains in the
  success region through the 260-step horizon.

Verdict:
- This is a real pass for the narrow hold-retention diagnostic under exact
  source-joint matched reset, official DP checkpoint, and no-reset eval.
- Caveat remains critical: this does not prove normal-reset generalization or
  BC/RL readiness. The run deliberately used exact source-joint/cube reset and
  an eval-only success timeout override. Normal task resets and broader support
  remain unresolved.

Next:
- Launch exactly one short video/contact-sheet confirmation with the same
  no-reset matched-source settings (`NUM_STEPS=260`, `CAPTURE_VIDEO=True`,
  `SUCCESS_TIMEOUT_OVERRIDE=999.0`). Acceptance is visual confirmation that
  the gripper retains and lifts the cube through the horizon. No training or
  RL scale-up.

## 2026-06-11T19:42:08-07:00 - no-reset hold video confirmation plan

Goal:
- Produce one visual artifact for the matched source-joint no-reset pass so
  the user/orchestrator can inspect the actual contact and lift behavior.

Plan:
- Reuse implementation commit `9a10582d857998055e2d0e0f9c571758c6d1cd9d`
  already deployed on l401.
- Run one video eval with the same checkpoint, reset, `ACTION_CHUNK_STEPS=1`,
  `NUM_INFERENCE_STEPS=100`, and `SUCCESS_TIMEOUT_OVERRIDE=999.0`.
- Fetch video, metrics, traces, stdout, generate support/action plots and a
  contact sheet, then open the video/contact sheet/report with `viz-open`.

Acceptance:
- The video should show the matched-reset policy contacting, lifting, and
  retaining the cube through the 260-step no-reset horizon.
- If visual artifacts contradict the trace metrics, treat it as a visualization
  or metric bug and debug before any next training/eval. Otherwise the next
  bounded issue is normal-reset generalization/support expansion, not hold
  retention under matched reset.

## 2026-06-11T19:43:00-07:00 - no-reset hold video confirmation launch

Version Control:
- implementation_commit:
  `a1340ba3aa4453689aa0f8a7251357d59c27e435`
- runtime code change from `9a10582d857998055e2d0e0f9c571758c6d1cd9d`
  is only worklog/result recording; eval code is unchanged.
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `a1340ba3aa4453689aa0f8a7251357d59c27e435`, detached clean.

Command / Job:
- job_id: `1028059`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-sourcejoint-noreset,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028059.out`

Acceptance:
- Fetch video, metrics, traces, stdout. Generate support/action plots,
  hold-retention audit, contact sheet, and report. Open video/contact
  sheet/report with `viz-open`.

Result:
- status: completed and inspected; video confirms the matched source-joint
  no-reset hold pass.
- Slurm: `COMPLETED 0:0`, elapsed `00:03:13`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300`
- fetched/generated artifacts:
  `metrics.json`, `policy_trace.json`, `support_trace.csv/json`,
  `eval_config.json`, stdout log, mp4, `video_ffprobe.json`,
  `closed_loop_contact_sheet.jpg`, `closed_loop_support_report.md`,
  `closed_loop_support_trace.png`, `closed_loop_action_components.png`,
  `closed_loop_support_summary.json`, `closed_loop_support_key_rows.csv`,
  `hold_retention_audit.png/csv/json`.
- viewer URLs:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/videos/franka-cube-dp-weighted-sourcejoint-noreset-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/closed_loop_contact_sheet.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/closed_loop_support_report.md`
  - hold retention plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/hold_retention_audit.png`
- video metadata:
  `1280x720`, `259` frames, `4.3167 s`, `60 fps`.
- metrics:
  `steps_completed=260`, `done_count=0`, `final_success_rate=1.0`,
  `window_success_rate=1.0`, `first_success_step=172`,
  `last_success_step=260`, `success_steps=89`, final/max lift
  `0.2457067 m`, final EE-to-cube `0.00953 m`, final
  finger-center-to-cube `0.04029 m`, final gripper width `0.04700 m`.
- visual read:
  Contact sheet starts from first usable rendered frame at step `2`; the cube
  is grasped near the fingers, crosses success at step `172`, and remains
  visually retained through final step `260` while lift increases from
  `0.121 m` to `0.246 m`.

Verdict:
- The hold-stability/contact-retention blocker for exact source-joint matched
  reset is cleared under the eval-only no-reset condition.
- This supersedes the earlier apparent post-success drop: that video was
  reset-contaminated by the normal `success_timeout=0.20` termination.
- Caveat remains explicit: this is not normal-reset generalization and not a
  broad BC/RL warm-start readiness claim. It depends on exact source-joint
  matched reset and a success-timeout override. The next bounded work should
  target normal-reset support/conditioning or a staged reset-to-contact
  relabel/eval path, not more hold debugging under the matched reset.

## 2026-06-11T19:52:50-07:00 - closed-loop report verdict correction plan

Goal:
- Fix stale `closed_loop_support_report.md` verdict text for the no-reset
  matched source-joint hold-pass artifacts. The generated report currently
  still says `INCONCLUSIVE` and references the old drift-away failure, which
  conflicts with the metrics/contact sheet and worklog.

Plan:
- Patch `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py` so it
  emits a bounded pass verdict when final/window success are `1`, `done_count`
  is `0`, lift is above threshold, and a success-timeout override is present.
- Preserve the caveat that this is a no-learning diagnostic under exact
  source-joint matched reset with success-timeout override, not normal-reset
  generalization or BC/RL scale-up readiness.
- Regenerate the local trace/video reports for jobs `1028052` and `1028059`
  from the existing fetched artifacts. No new eval/training job.
- Validate with `python3 -m py_compile`, `git diff --check`, grep the reports
  for stale text, then commit/push code and worklog.

Result:
- status: completed; stale report verdict corrected in generator and local
  artifact bundles.
- changed file:
  `dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`.
- regenerated local reports:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200/closed_loop_support_report.md`
  and
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/closed_loop_support_report.md`.
- corrected viewer URL:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_chunk1_sourcejoint_ep1s0_20260611_194300/closed_loop_support_report.md`
- corrected verdict now reads:
  `PASS (bounded): exact source-joint matched reset with success-timeout
  override retains and lifts the cube through the rollout horizon.`
- caveat remains in the report:
  no-learning diagnostic, exact source-joint matched reset, eval-only
  success-timeout override, not normal-reset generalization and not BC/RL
  scale-up readiness evidence.
- validation:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`,
  `git diff --check`, and `rg` checks for stale `INCONCLUSIVE` /
  `closing away` text in both regenerated reports passed.

## 2026-06-11T19:29:22-07:00 - hold-stability/contact-retention plan

Goal:
- Diagnose whether the weighted contact-aware DP policy can retain the cube
  after first reaching the success lift region, or whether the prior
  post-success drop is physical contact loss rather than the env's normal
  success auto-reset.

Plan:
- Add an eval-only `success_timeout` override to
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py` and expose it through
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.
- Keep the override off by default so normal evaluation semantics are
  unchanged. For this diagnostic only, set the timeout longer than the rollout
  horizon so the env does not terminate immediately after the built-in
  `0.20 s` success hold.
- Validate locally with `python3 -m py_compile`, `bash -n`, and
  `git diff --check`.
- Commit/push/deploy the exact commit to the l401 agent worktree before
  launching.

Bounded launch:
- Run one no-video matched source-joint trace first:
  `NUM_ENVS=1`, `NUM_STEPS=260`, `ACTION_CHUNK_STEPS=1`,
  `NUM_INFERENCE_STEPS=100`, `SUCCESS_TIMEOUT_OVERRIDE=999.0`,
  `SUCCESS_WINDOW=80`, `DEBUG_POLICY_TRACE_MAX_CALLS=260`, same weighted
  checkpoint and same source-joint reset (`episode=1`, `step=0`,
  `source_frame=260`).
- Gate: durable final/window success with lift above target and no reset/done
  is a pass; physical drop/loss before the horizon is a hold/contact-retention
  blocker. If the trace is pass/near-pass or ambiguous, launch exactly one
  short video/contact-sheet eval for visual confirmation.

Constraints:
- No broad DP BC training and no RL scale-up.
- This tests hold stability after the already observed transient matched-reset
  success; it does not claim normal-reset generalization.

## 2026-06-11T19:32:00-07:00 - no-reset hold trace launch

Goal:
- Run the first bounded hold-retention diagnostic with success auto-reset
  disabled via a long eval-only timeout.

Version Control:
- implementation_commit:
  `9a10582d857998055e2d0e0f9c571758c6d1cd9d`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `9a10582d857998055e2d0e0f9c571758c6d1cd9d`, detached clean.
- branch pushed:
  `codex/franka-cube-diffusion-policy-bc`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  passed.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` passed.
- `git diff --check` passed.

Command / Job:
- job_id: `1028052`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-sourcejoint-noreset,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_chunk1_sourcejoint_ep1s0_20260611_193200`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028052.out`

Acceptance:
- Inspect metrics/traces/logs after completion. Pass requires durable
  final/window success without reset; failure with no reset indicates real
  hold/contact-retention loss after transient lift. Video is deferred until
  the no-video trace says whether visual confirmation is needed.

Result:
- status: running.

Status update:
- job `1028052` completed and was fetched/inspected. Detailed metrics and
  viewer links are recorded in the no-reset hold pass result above. The
  follow-up video confirmation job `1028059` also completed and is recorded
  above with mp4/contact-sheet/report links. No active C jobs remain from this
  diagnostic loop.

## 2026-06-11T19:56:51-07:00 - normal-reset no-reset generalization trace plan

Goal:
- Move one bounded step from exact source-joint matched reset toward normal
  task-reset behavior without training or RL scale-up.

Hypothesis:
- The weighted contact-aware DP checkpoint may rely strongly on exact
  source-joint/contact-aware reset support. Running the same checkpoint from
  the normal DEXTRAH task reset, while keeping the no-reset
  `success_timeout_override=999.0`, separates policy/reset-distribution
  behavior from the env's success auto-reset semantics.
- If normal reset succeeds or nearly succeeds, the next issue is support
  expansion/evaluation across resets. If it fails, the support trace, live
  geometry, and policy trace should show whether the state leaves contact-aware
  demo support before grasp/lift.

Plan:
- No code changes expected. Reuse corrected commit
  `c67dde23bcda9d9facd2ed4b62fab958d1a7dc41`.
- Deploy the exact commit to the l401 agent-owned worktree.
- Launch one no-video normal-reset trace:
  `NUM_ENVS=1`, `NUM_STEPS=260`, `ACTION_CHUNK_STEPS=1`,
  `NUM_INFERENCE_STEPS=100`, `SUCCESS_TIMEOUT_OVERRIDE=999.0`,
  `SUCCESS_WINDOW=80`, `DEBUG_POLICY_TRACE_MAX_CALLS=260`, same weighted
  checkpoint and same accepted contact-aware support dataset, but no
  `DEMO_RESET_*` arguments.
- Fetch logs/metrics/traces and generate a support/action report plus
  hold/normal-reset audit from the existing local artifact tooling.
- Gate:
  - If final/window success is coherent, run one video/contact-sheet
    confirmation and keep the caveat that this is no-reset eval only.
  - If failure is informative, run one short video/contact-sheet confirmation
    to show normal-reset behavior and support drift.
  - Do not launch DP BC training or RL.

Acceptance:
- Artifact bundle must include stdout, `eval_config.json`, `metrics.json`,
  `policy_trace.json`, `support_trace.csv/json`, support/action plots,
  `closed_loop_support_report.md`, and viewer links. Video/contact sheet is
  required only after the trace identifies a clear pass/failure worth visual
  confirmation.

## 2026-06-11T20:00:00-07:00 - normal-reset no-reset trace launch

Version Control:
- implementation_commit:
  `cb9689b8b4c70ab268a571f031bcecd0e92355b2`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  at `cb9689b8b4c70ab268a571f031bcecd0e92355b2`, detached clean.

Command / Job:
- job_id: `1028064`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-normalreset-noreset,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028064.out`

Acceptance:
- Scheduler completion is not enough. Fetch and inspect metrics/logs/traces.
- If the normal-reset trace is a clear pass or informative failure, launch one
  video/contact-sheet confirmation only after this no-video result is
  understood.

Result:
- status: running.

Result update:
- status: completed, informative failure.
- fetched local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000`
- key metrics:
  - `steps_completed=260`, `done_count=0`.
  - `final_success_rate=0.0`, `window_success_rate=0.0`.
  - `cube_lift_height max/final=0.0/0.0 m`.
  - `EE-to-cube min/final=0.141864/0.145302 m`.
  - `finger-center-to-cube min/final=0.110178/0.112240 m`.
  - `final_gripper_width=0.021743 m`.
  - support trace starts far outside the contact-aware demo manifold:
    nearest-demo distance `29.566 -> 22.787`, with nearest phase
    `align_open` for all 260 steps.
- viewer links:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000/closed_loop_support_report.md`
  - support plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000/closed_loop_support_trace.png`
  - action plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_trace260_noreset_normalreset_seed42_20260611_200000/closed_loop_action_components.png`

Analysis:
- This confirms the intended contrast: exact source-joint matched reset with
  success-timeout override can hold/lift, but normal task reset fails even with
  the same no-reset timeout override. The policy closes away from the cube and
  never reaches lift/contact support from the normal reset distribution.
- This is not a DP BC/RL readiness signal. It points to normal-reset support
  generalization / reset distribution conditioning as the next bounded issue.

Next:
- Launch exactly one video/contact-sheet confirmation for the same normal-reset
  no-reset failure (`num_envs=1`, `num_steps=260`, same checkpoint/support
  dataset, no `DEMO_RESET_*` arguments). No training or RL scale-up.

## 2026-06-11T20:07:20-07:00 - normal-reset no-reset video confirmation launch

Goal:
- Produce the single requested visual confirmation for the normal-reset
  no-reset failure found in job `1028064`.

Version Control:
- local_worklog_commit:
  `ff4bd75524f445574d72877733b5b2e01117393a`
- runtime_remote_commit:
  `cb9689b8b4c70ab268a571f031bcecd0e92355b2`
- remote_commit_note:
  l401 could not fetch from GitHub (`git@github.com: Permission denied
  (publickey)`). The only diff from `cb9689b` to `ff4bd75` is this owned
  worklog, so the launched runtime source is unchanged from the no-video trace.

Command / Job:
- job_id: `1028073`
- run_name:
  `franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-weighted-normalreset-noreset,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028073.out`

Acceptance:
- Fetch metrics/logs/traces/video locally, generate report/plots/contact sheet,
  and visually confirm normal-reset closes away from the cube. No training/RL.

Result:
- status: running.

Result update:
- scheduler: `COMPLETED 0:0`, elapsed `00:03:12`.
- fetched local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720`
- final metrics:
  - `steps_completed=260`, `done_count=0`.
  - `final_success_rate=0.0`, `window_success_rate=0.0`.
  - `cube_lift_height max/final=0.0/0.0 m`.
  - `EE-to-cube min/final=0.141898/0.145352 m`.
  - `finger-center-to-cube min/final=0.110207/0.112289 m`.
  - `final_gripper_width=0.021748 m`.
  - nearest-demo support remains far outside the contact-aware dataset:
    starts `29.46` at step 2 and ends `16.58` at step 260.
- visual check:
  - Contact sheet confirms the hand closes beside/away from the cube and never
    lifts it. The trace labels transition to nearest phase `close_hold`, but
    live geometry is still far from the nearest demo close geometry.
- viewer links:
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720/videos/franka-cube-dp-weighted-normalreset-noreset-step-0.mp4`
  - contact sheet:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720/closed_loop_contact_sheet.jpg`
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720/closed_loop_support_report.md`
  - support plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720/closed_loop_support_trace.png`
  - action plot:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_weightedgrip8_inf100_video260_noreset_normalreset_seed42_20260611_200720/closed_loop_action_components.png`

Analysis:
- The contrast is now video-backed:
  - exact source-joint matched reset + success-timeout override:
    `final/window success=1.0/1.0`, final lift `0.2457 m`, final EE-cube
    `0.00953 m`.
  - normal reset + same success-timeout override:
    `final/window success=0.0/0.0`, max lift `0.0 m`, final EE-cube
    `0.14535 m`, final finger-center-cube `0.11229 m`.
- This separates the solved matched-reset hold-retention case from normal-reset
  generalization. The checkpoint can act coherently on exact contact-aware
  support but fails from the normal DEXTRAH reset distribution.
- No DP BC/RL scale-up is justified. The next bounded question is reset/support
  coverage: staged perturbations around accepted demo resets or a small
  normal-reset relabel/eval support expansion, with the same artifact cadence.

Active jobs:
- No active C Slurm jobs remain after `1028073`.

## 2026-06-11T20:32:03-07:00 - reset-support perturbation sweep plan

Goal:
- Bound normal-reset generalization failure by measuring policy support around
  the accepted contact-aware demo reset, without BC/RL scale-up.

Hypothesis:
- The weighted DP checkpoint is coherent on exact source-joint/contact-aware
  support but fails as the reset state moves toward the normal DEXTRAH reset.
  A staged reset perturbation/blend sweep should reveal whether breakage
  correlates with nearest-demo support distance, reset geometry, or a remaining
  observation/action implementation mismatch.

Planned Change:
- Add eval-only reset blend controls to
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`:
  `--demo_reset_joint_blend_alpha` for interpolating from normal reset joints
  to source trajectory joints, and `--demo_reset_cube_pos_blend_alpha` for
  interpolating from normal reset cube position to selected demo cube position.
- Add matching environment variable plumbing to
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.
- Add an offline sweep summarizer under
  `dextrah_lab/offline_dp_bc/` to produce the required JSON/CSV table,
  support-distance-vs-success/lift plot, and markdown verdict from fetched run
  dirs.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `77d562ff1d45810ab4c1c727a482aa59a2701228`
- implementation_commit: pending
- changed_files_planned:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `dextrah_lab/offline_dp_bc/make_reset_support_sweep_report.py`
  - this worklog

Validation Plan:
- Local:
  - `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/make_reset_support_sweep_report.py`
  - `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `git diff --check`
- Remote:
  - push branch and deploy exact commit to the agent-owned l401 worktree via
    Git. If l401 still cannot fetch from GitHub, record that external blocker
    precisely before any source-dependent cluster launch.

Planned Jobs:
- Bounded no-video L401 trace sweep, `NUM_ENVS=1`, `NUM_STEPS=260`,
  `NUM_INFERENCE_STEPS=100`, `ACTION_CHUNK_STEPS=1`,
  `SUCCESS_TIMEOUT_OVERRIDE=999.0`, support tracing enabled, using the accepted
  contact-aware NPZ and weighted checkpoint.
- Initial sweep settings:
  - exact matched context is reused from `1028052`/`1028059`.
  - normal-reset context is reused from `1028064`/`1028073`.
  - new source-cube / joint-blend trace runs for alpha values
    `0.75`, `0.50`, `0.25`, and `0.00` if the source patch deploys cleanly.
- After trace inspection, launch at most one short video/contact-sheet
  confirmation for the first failing perturbation not already covered by the
  matched/normal context videos.

Acceptance:
- Produce a sweep table/JSON with perturbation setting, job id/run dir, success
  and window success, max/final lift, EE/finger distances, gripper width,
  nearest-demo support distance/phase, and failure reason.
- Produce an inspectable plot showing support distance versus success/lift and
  link matched-pass, first-failing, and normal-reset videos/contact sheets.
- Verdict must state whether evidence points to reset support coverage,
  observation normalization, action chunking, or another bug. No DP BC/RL
  scale-up is allowed from this step.

Implementation update:
- Added eval-only reset blend arguments and Slurm env plumbing.
- Added `dextrah_lab/offline_dp_bc/make_reset_support_sweep_report.py`.

Local validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/make_reset_support_sweep_report.py`: pass.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`: pass.
- `git diff --check`: pass.
- `git diff --cached --check`: pass.

Implementation commit:
- `5edcf31f8b21d04a8dfcbe921c6ddcd586a854b1`
- pushed branch: `codex/franka-cube-diffusion-policy-bc`

Remote deploy:
- l401 canonical SSH remote still fails:
  `git@github.com: Permission denied (publickey)`.
- HTTPS Git fetch from `https://github.com/lihzha/DEXTRAH.git` succeeded.
- agent remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_head:
  `5edcf31f8b21d04a8dfcbe921c6ddcd586a854b1`

Launch:
- type: no-video reset-support trace sweep.
- runtime_remote_commit:
  `5edcf31f8b21d04a8dfcbe921c6ddcd586a854b1`
- local_worklog_commit_before_launch:
  `9be8dca9b5e62a30fb9cbdfc69da3390fdff1895`
- common command shape:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=<run>,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=260,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0,DEMO_RESET_JOINT_BLEND_ALPHA=<alpha>,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- jobs:
  - `1028089`: `alpha=0.75`,
    run `franka_cube_dp_eval_reset_support_jointblend_0p75_trace260_20260611_203638`
  - `1028090`: `alpha=0.50`,
    run `franka_cube_dp_eval_reset_support_jointblend_0p50_trace260_20260611_203638`
  - `1028091`: `alpha=0.25`,
    run `franka_cube_dp_eval_reset_support_jointblend_0p25_trace260_20260611_203638`
  - `1028092`: `alpha=0.00`,
    run `franka_cube_dp_eval_reset_support_jointblend_0p00_trace260_20260611_203638`
- run dirs:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/<run>`
- logs:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_<job>.out`

Acceptance before any follow-up:
- Inspect scheduler state, stdout, metrics, support traces, and generated
  per-run plots.
- Build the reset-support sweep bundle locally.
- Launch at most one video for the first failing perturbation if the trace
  makes it useful.

Active jobs:
- `1028089`, `1028090`, `1028091`, `1028092` submitted.

Result:
- scheduler status:
  - `1028089`, `1028090`, `1028091`, `1028092`: `COMPLETED|0:0`.
- fetched local run dirs:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_trace260_20260611_203638`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p50_trace260_20260611_203638`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p25_trace260_20260611_203638`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p00_trace260_20260611_203638`
- generated per-run reports:
  - `closed_loop_support_report.md`
  - `closed_loop_support_trace.png`
  - `closed_loop_action_components.png`
  - `closed_loop_support_summary.json`
- combined sweep artifact bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638`
- combined report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_report.md`
- combined plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_plot.png`

Metrics:
- matched source-joint context video `1028059`:
  `window_success=1.0`, `max/final_lift=0.2457067/0.2457067 m`,
  `final_ee_to_cube=0.00953 m`, `final_support_distance=2.0036`,
  final phase `lift`.
- normal reset context video `1028073`:
  `window_success=0.0`, `max/final_lift=0.0/0.0 m`,
  `final_ee_to_cube=0.14535 m`, `final_support_distance=16.5813`,
  final phase `close_hold`.
- joint blend `0.75`, job `1028089`:
  `cube_minus_ee_l2_from_demo_at_reset=0.03944 m`,
  `window_success=0.0`, `max/final_lift=0.01575/0.0 m`,
  `final_ee_to_cube=0.30212 m`, `final_finger_center_to_cube=0.34577 m`,
  `support_distance_start/final=4.7635/20.5594`, final phase `align_open`.
- joint blend `0.50`, job `1028090`:
  `cube_minus_ee_l2_from_demo_at_reset=0.08035 m`,
  `window_success=0.0`, `max/final_lift=0.01499/0.0 m`,
  `final_ee_to_cube=0.35229 m`, `support_distance_start/final=10.7178/23.8308`.
- joint blend `0.25`, job `1028091`:
  `cube_minus_ee_l2_from_demo_at_reset=0.12239 m`,
  `window_success=0.0`, `max/final_lift=0.0/0.0 m`,
  `final_ee_to_cube=0.11183 m`, `support_distance_start/final=13.8690/12.9817`.
- joint blend `0.00`, job `1028092`:
  `cube_minus_ee_l2_from_demo_at_reset=0.16520 m`,
  `window_success=0.0`, `max/final_lift=0.0/0.0 m`,
  `final_ee_to_cube=0.15057 m`, `support_distance_start/final=19.3631/17.5813`.

Analysis:
- The first tested perturbation from exact matched source support (`joint_blend_alpha=0.75`,
  source cube/object fixed) already fails. It starts close in metric space
  (`~3.94 cm` cube-minus-EE from the accepted reset) but quickly leaves support
  and ends far away from the cube.
- This points primarily to a narrow reset/support basin and weak closed-loop
  recovery, not action chunking: the same checkpoint, normalizer, bridge, and
  `ACTION_CHUNK_STEPS=1` pass under exact source-joint matched reset.
- The observation/action implementation is not cleared globally, but the
  matched-reset pass makes a pure gripper sign, action frame, or chunking bug
  less likely for this failure mode.

Next:
- Launch exactly one bounded video/contact-sheet confirmation for the first
  failing perturbation (`joint_blend_alpha=0.75`, source cube/object fixed).
- Do not run BC/RL scale-up. If the video confirms the trace, the next
  proposed experiment should be small support-expansion relabel/eval around the
  accepted source-joint/contact reset, with a supervised/eval gate before any
  DP training.

Follow-up launch:
- commit_before_launch:
  `f5662bbd2c81f86830c42d98065273ad613c45de`
- runtime_remote_commit:
  `5edcf31f8b21d04a8dfcbe921c6ddcd586a854b1`
- job_id: `1028108`
- run:
  `franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424`
- command:
  `sbatch --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-reset-support-jointblend-0p75,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=260,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_official_dp_debug_pretrain100_weightedgrip8_20260611_1843/latest.ckpt,SUPPORT_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_DATASET=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/contact_relabel_set_ep8_16_24_30_s260_high30_defaultfix_20260611_175347/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=1,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,OFFICIAL_DP_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/external/real-stanford-diffusion_policy cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028108.out`
- acceptance:
  fetch video, metrics, support/action traces, contact sheet, report, and update
  the combined sweep bundle with this video URL if runtime confirms the trace
  failure.

Follow-up result:
- scheduler status:
  `1028108 COMPLETED|0:0`, elapsed `00:03:21`, node `pool0-00010`.
- fetched local run dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/logs/eval_franka_cube_dp_policy_1028108.out`
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/closed_loop_support_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/closed_loop_support_trace.png`
- action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/closed_loop_action_components.png`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/videos/franka-cube-dp-reset-support-jointblend-0p75-step-0.mp4`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_reset_support_jointblend_0p75_video260_20260611_204424/closed_loop_contact_sheet.jpg`

Metrics:
- reset:
  `joint_blend_alpha=0.75`, `cube_pos_blend_alpha=1.0`,
  `cube_minus_ee_l2_from_demo_at_reset=0.039436 m`.
- final/window success: `0.0/0.0`.
- max/final lift: `0.0157515/0.0 m`; the only lift blip is at step `1`.
- min/final EE-to-cube: `0.02230/0.30220 m`.
- min/final finger-center-to-cube: `0.05382/0.34586 m`.
- final gripper width: `0.03671 m`.
- support distance start/min/final:
  `4.7635/4.7635/20.4686`, final nearest phase `align_open`.
- report verdict:
  `FAIL: closed-loop policy still leaves demonstration support and closes away from the cube.`

Artifact updates:
- Rebuilt contact sheet from first-usable/mid/late frames
  `20, 60, 100, 140, 180, 220, 258`.
- Rebuilt combined sweep bundle:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638`
- combined report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_report.md`
- combined plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_plot.png`
- combined table:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_table.csv`
- combined summary:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/reset_support_sweep_jointblend_20260611_203638/reset_support_sweep_summary.json`

Source/tooling fix:
- Tightened `make_closed_loop_support_report.py` failure verdicts so
  no-success, low-final-lift rollouts with large final contact/support distance
  do not report as inconclusive.
- Updated `make_reset_support_sweep_report.py` sort order so the sweep reads
  exact matched reset, decreasing joint blend, then normal-reset context.
- validation:
  - `python3 -m py_compile dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py dextrah_lab/offline_dp_bc/make_reset_support_sweep_report.py`
  - `git diff --check`

Final bounded verdict:
- This reset-support sweep supports reset/support coverage as the dominant
  current blocker. The weighted DP checkpoint can retain/lift under exact
  source-joint matched reset, but a `25%` interpolation from source joints
  toward the normal robot reset already breaks the policy despite the cube
  being fixed to the accepted demo pose.
- This is not explained by action chunking, since all runs use
  `ACTION_CHUNK_STEPS=1` and the exact matched reset passes with the same
  observation bridge, normalizer, gripper convention, and checkpoint.
- Do not scale DP BC/RL. The next bounded experiment should be a small
  support-expansion controller relabel/eval around accepted demo resets
  (robot joint/contact perturbations and possibly cube pose perturbations),
  gated first by controller-rollout success and then by the same official-DP
  offline/eval artifact contract.

Active jobs:
- none after `1028108`.

## 2026-06-11T20:57:39-07:00 - support expansion around first failing reset plan

Goal:
- Run one bounded support-expansion experiment around the accepted source-contact
  reset to test whether local support near the first failing perturbation
  (`joint_blend_alpha=0.75`, source cube fixed) can recover alpha0.75 while
  preserving the exact matched reset behavior.

Hypothesis:
- The current weighted DP checkpoint fails at alpha0.75 because the training
  support contains only exact contact-aware source-joint rollouts. Adding a
  small set of controller-generated relabel demonstrations from exact/0.9/0.75
  robot-state blends may improve local closed-loop recovery around alpha0.75
  without needing broad normal-reset data.

Planned Change:
- Add a relabel-only reset joint-blend option to
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`.
- Thread the option through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` so each
  rollout spec can carry `episode:step:trajectory:joint_blend_alpha`.
- Keep this scoped to contact-aware relabel generation; it does not change the
  DEXTRAH task, DP eval bridge, or RL code.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `57250c0fb861ff66e325e995e97376b03232f67f`
- implementation_commit: pending
- changed_files_planned:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - this worklog

Validation Plan:
- Local:
  - `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `python3 -m py_compile dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `git diff --check`
- Remote:
  - push branch and deploy exact commit to the agent-owned l401 worktree.
  - Launch one bounded relabel-set gate, not DP training:
    - `SPEC_COUNT=3`
    - specs for original cuRobo episode `16`, source step `260`, same source
      trajectory JSON, with `joint_blend_alpha` values `1.0`, `0.9`, `0.75`.
      The earlier DP eval name used relabeled episode `1`, step `0`; that maps
      back to original episode `16`, step `260` in the accepted contact-aware
      relabel set.
    - source cube fixed by the contact-aware rollout reset.
    - `VARIANT=center_high30`, short video enabled for inspectable rollouts.
  - Generate an offline support-expansion dataset report comparing the
    candidate NPZ against the previous accepted contact relabel NPZ: perturbation
    distribution, action/phase coverage, and nearest-support distances.
  - Fetch logs/artifacts, create/open viewer URLs, and inspect the relabel
    gate before deciding whether any official-DP fine-tune smoke is allowed.

Gate:
- Relabel-set hard gate must pass for all generated rollouts:
  final/max lift over threshold, no pose clipping, final EE/finger distance
  plausible, no post-reset rows, and videos/contact sheets visually coherent.
- Only if the relabel gate passes will I propose/run a short official-DP
  fine-tune/debug pretrain using the expanded NPZ, with exact matched and
  alpha0.75 eval gates afterward.
- Normal reset eval remains context only; normal-reset recovery is not required
  for this bounded gate.

## 2026-06-11T21:03:17-07:00 - support expansion relabel implementation checkpoint

Goal:
- Prepare the bounded contact-aware relabel support-expansion sweep around the
  accepted source-contact reset, with exact/0.9/0.75 source-joint blend specs
  and artifact-ready metadata before any cluster launch.

Change:
- Added `--reset_joint_blend_alpha` to
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`, blending normal
  task-reset joints toward source trajectory joints while keeping the cube reset
  on the selected source row.
- Logged reset alignment diagnostics per rollout row and summary: joint distance
  from source/normal, lowdim distance from dataset, cube-minus-EE distance, and
  applied/source/normal joint vectors.
- Extended `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` to
  parse `episode:step:trajectory:joint_blend_alpha` specs and create
  alpha-suffixed rollout directories, avoiding collisions between perturbations.
- Extended `make_contact_relabel_set_report.py` so reset alpha/diagnostics are
  visible in the aggregate CSV/report and accepted NPZ sidecar metadata.
- Added `make_support_expansion_dataset_report.py` for the required offline
  candidate-dataset summary: perturbation distribution, phase/action coverage,
  and nearest-support distances versus the previous accepted contact relabel
  dataset.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- base_commit: `57250c0fb861ff66e325e995e97376b03232f67f`
- implementation_commit: pending
- changed_files:
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - this worklog

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` -> pass
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` -> pass
- `git diff --check` -> pass

Next:
- Commit/push, deploy the exact commit to the agent-owned l401 worktree, then
  launch one bounded relabel-set gate for original cuRobo episode `16`, source
  step `260`, trajectory seed16, joint blend alphas `1.0`, `0.9`, and `0.75`.

## 2026-06-11T21:07:28-07:00 - support expansion relabel deploy boundary

Version Control:
- implementation_commit: `527660b2bcd26272bdb722b064f59f7615d7d6d2`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `527660b2bcd26272bdb722b064f59f7615d7d6d2`
- remote_status: clean detached HEAD

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` -> pass
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` -> pass
- `git diff --check` -> pass

Next:
- Launch the bounded relabel-set gate from the deployed l401 worktree with
  original episode `16`, source step `260`, trajectory seed16, and joint blend
  alphas `1.0`, `0.9`, `0.75`.

## 2026-06-11T21:08:23-07:00 - support expansion relabel gate launch

Goal:
- Generate a tiny contact-aware support-expanded relabel candidate around the
  accepted source-contact reset and the first-failing `alpha=0.75` perturbation.

Command / Job:
- job_id: `1028115`
- run_name:
  `franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `37b6f60d74f79c6e7ec507adccb74309ce8a69ec`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=3,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:1.0,SPEC_1=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.9,SPEC_2=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ALIGN_STEPS=80,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-contact-supportexp,PRINT_INTERVAL=80,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028115.out`

Gate:
- All three controller rollouts must pass the hard relabel gate with final/max
  lift above threshold, no pose-action clipping, final EE/finger distances in
  range, and videos/contact sheets visually coherent before any DP fine-tune is
  considered.

## 2026-06-11T21:15:46-07:00 - support expansion relabel gate result

Result:
- job_id: `1028115`
- scheduler: `COMPLETED 0:0`, elapsed `00:02:17`, node `pool0-00030`.
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823`
- stdout log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/logs/contact_aware_franka_cube_relabel_set_1028115.out`
- gate verdict:
  `FAIL: at least one contact-aware rollout failed the hard relabel gate; do not train DP on this set.`

Rollout Metrics:

| rollout | alpha | gate | final EE-cube | final finger-cube | final/max lift | max clip | failure |
|---|---:|---|---:|---:|---:|---:|---|
| `ep16s260_a1p0_center_high30` | 1.00 | pass | `0.00727` | `0.03803` | `0.13545/0.13545` | `0.000` | |
| `ep16s260_a0p9_center_high30` | 0.90 | pass | `0.00694` | `0.04038` | `0.13631/0.13631` | `0.000` | |
| `ep16s260_a0p75_center_high30` | 0.75 | fail | `0.21257` | `0.24359` | `0.00000/0.01554` | `0.000` | `success_like_false;max_lift_below_threshold;final_lift_below_threshold;final_ee_to_cube_too_large;final_finger_to_cube_too_large` |

Artifact URLs:
- relabel gate report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/contact_relabel_set_report.md`
- support-expansion report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/support_expansion_report/support_expansion_report.md`
- support-expansion plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/support_expansion_report/support_expansion_plot.png`
- exact matched contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/rollouts/ep16s260_a1p0/contact_sheet_a1p0.jpg`
- alpha0.9 contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/rollouts/ep16s260_a0p9/contact_sheet_a0p9.jpg`
- alpha0.75 failure contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/rollouts/ep16s260_a0p75/contact_sheet_a0p75.jpg`
- alpha0.75 failure video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/rollouts/ep16s260_a0p75/videos/franka-cube-contact-supportexp-ep16s260_a0p75-step-0.mp4`
- exact matched pass video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_supportexp_ep16s260_a1_a0p9_a0p75_20260611_210823/rollouts/ep16s260_a1p0/videos/franka-cube-contact-supportexp-ep16s260_a1p0-step-0.mp4`

Support Dataset Summary:
- Accepted candidate NPZ exists but contains only the passing alpha `1.0` and
  `0.9` rollouts: obs/action shape `[565, 21]` / `[565, 7]`, episode ends
  `[284, 565]`.
- Alpha `0.75` is intentionally excluded from the accepted NPZ because it
  failed the hard gate.
- Candidate-vs-baseline nearest-support distance p50/p95/max:
  `2.4024 / 7.5301 / 7.6219`. The high distances mostly come from the alpha
  `0.9` perturbation, while the exact alpha `1.0` rollout stays near prior
  support.

Analysis:
- Local contact-aware relabeling does not yet recover the first-failing
  `alpha=0.75` support gap. The failure is visible and metric-backed: the hand
  closes/lifts away from the cube, with final finger-center distance `0.244 m`
  and no lift.
- This is still a reset/support-coverage problem, but the current simple
  center-high30 controller relabeler only bridges to `alpha=0.9`; it does not
  generate a valid alpha0.75 demonstration.
- Because the bounded relabel gate failed, I did not run official DP fine-tune
  or any RL/scale-up.

Next:
- A reasonable next bounded diagnostic is to generate intermediate controller
  relabel attempts around `alpha=0.85` and/or use a staged two-phase alignment
  that first recovers finger-center geometry before close/lift, then re-test
  alpha0.75. Do not train DP until a controller relabel artifact for alpha0.75
  itself passes the same visual/metric gate.

Active Jobs:
- none after `1028115`.

## 2026-06-11T21:12:41-07:00 - alpha0.75 controller bridge diagnostic plan

Goal:
- Run one bounded controller-relabel bridge diagnostic to test whether the
  relabel controller can recover the first failing `joint_blend_alpha=0.75`
  before any DP fine-tune or RL work.

Hypothesis:
- The default contact-aware relabeler preserves the live reset EE orientation.
  At alpha0.75 the robot/wrist starts far enough from the source contact frame
  that finger-center translation alone closes/lifts away from the cube. Driving
  the EE orientation back to the source row during the finger-center alignment
  phase may restore contact geometry while preserving exact and alpha0.9
  behavior.

Planned Change:
- Add a narrow `--orientation_mode {live,source}` option to
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`.
  - `live` is the current/default behavior.
  - `source` uses the selected dataset/source-row EE quaternion as the target
    orientation when deriving the relative EE action.
- Thread `ORIENTATION_MODE` through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`.
- Record orientation mode in per-row rollout CSVs, per-rollout summaries, and
  aggregate relabel reports.

Validation Plan:
- Local:
  - `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `git diff --check`
- Cluster:
  - Commit/push/deploy exact commit to the agent-owned l401 worktree.
  - Launch one bounded relabel-set gate using original episode `16`, source
    step `260`, trajectory seed16, `ORIENTATION_MODE=source`, and alphas
    `1.0`, `0.9`, `0.85`, `0.8`, `0.75`.
  - Keep `VARIANT=center_high30`, `FINGER_GAIN=0.75`, no DP training.

Gate:
- Exact and alpha0.9 must remain visually/metric coherent.
- A candidate alpha0.75 rollout must pass the same hard relabel gate: final/max
  lift above threshold, no pose-action clipping, plausible final EE/finger
  distances, and video/contact sheet visually coherent.
- If alpha0.75 fails again, stop at artifact/reporting; do not launch DP
  fine-tune or RL.

## 2026-06-11T21:17:22-07:00 - source-orientation bridge implementation checkpoint

Change:
- Implemented `--orientation_mode {live,source}` in
  `contact_aware_franka_cube_rollout.py`.
  - `live` preserves previous behavior.
  - `source` targets the selected source/dataset row EE quaternion while the
    controller translates the measured finger center to the cube/contact target.
- Threaded `ORIENTATION_MODE` through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`.
- Added `orientation_mode` metadata to per-row CSVs, per-rollout summaries,
  aggregate relabel reports, and support-expansion reports.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- base_commit: `b044e200032061123918bf3dcb75b8159ade3a4f`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - this worklog

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` -> pass
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` -> pass
- `git diff --check` -> pass

Next:
- Commit/push/deploy, then launch one bounded relabel-set gate using
  `ORIENTATION_MODE=source` and alphas `1.0`, `0.9`, `0.85`, `0.8`, `0.75`.

## 2026-06-11T21:19:00-07:00 - source-orientation bridge relabel gate launch

Goal:
- Test whether source-row EE orientation targeting can recover alpha0.75 while
  preserving exact/alpha0.9 controller relabel behavior.

Version Control:
- implementation_commit: `6f11d30e4ab921281e92e0171e56bfec2c8bf102`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- remote_worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit: `6f11d30e4ab921281e92e0171e56bfec2c8bf102`
- remote_status: clean detached HEAD

Command / Job:
- job_id: `1028117`
- run_name:
  `franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=5,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:1.0,SPEC_1=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.9,SPEC_2=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.85,SPEC_3=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.8,SPEC_4=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,ALIGN_STEPS=80,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-contact-sourcequat,PRINT_INTERVAL=80,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- expected run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028117.out`

Gate:
- Same hard relabel gate as prior run. No DP fine-tune or RL will be launched
  unless alpha0.75 passes visually and metrically.

## 2026-06-11T21:20:05-07:00 - source-orientation bridge relabel gate result

Goal:
- Bound the alpha0.75 controller-relabel failure before any DP fine-tune by
  testing source-row EE orientation targeting at alphas `1.0`, `0.9`, `0.85`,
  `0.8`, and `0.75`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `6f11d30e4ab921281e92e0171e56bfec2c8bf102`
- remote_commit: `6f11d30e4ab921281e92e0171e56bfec2c8bf102`
- changed_files:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - this worklog

Command / Job:
- job_id: `1028117`
- scheduler_status: `COMPLETED 0:0`
- run_name:
  `franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/logs/contact_aware_franka_cube_relabel_set_1028117.out`

Result:
- status: `failed hard gate`
- aggregate verdict:
  `FAIL: at least one contact-aware rollout failed the hard relabel gate; do not train DP on this set.`
- metrics:

| alpha | hard gate | final EE-cube | final finger-cube | final/max lift | max clip | note |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1.00 | pass | 0.0077 | 0.0377 | 0.1360/0.1360 | 0.000 | exact source-joint context preserved |
| 0.90 | pass | 0.0094 | 0.0382 | 0.1353/0.1353 | 0.000 | prior accepted support point preserved |
| 0.85 | pass | 0.0148 | 0.0408 | 0.1353/0.1353 | 0.000 | first clean bridge pass |
| 0.80 | fail | 0.0184 | 0.0417 | 0.1355/0.1355 | 0.167 | visually lifts, but disqualified by pose-action clipping |
| 0.75 | fail | 0.1936 | 0.2376 | 0.0000/0.0142 | 0.167 | closes/lifts away from cube |

Artifacts:
- contact relabel report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/contact_relabel_set_report.md`
- support expansion report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/support_expansion_report/support_expansion_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/support_expansion_report/support_expansion_plot.png`
- alpha0.9 pass sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p9/contact_sheet_a0p9.jpg`
- alpha0.85 first clean bridge pass sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p85/contact_sheet_a0p85.jpg`
- alpha0.8 clipped near-pass sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p8/contact_sheet_a0p8.jpg`
- alpha0.75 failure sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p75/contact_sheet_a0p75.jpg`
- alpha0.85 video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p85/videos/franka-cube-contact-sourcequat-ep16s260_a0p85-step-0.mp4`
- alpha0.75 video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_bridge_sourcequat_ep16s260_a1_a0p9_a0p85_a0p8_a0p75_20260611_211900/rollouts/ep16s260_a0p75/videos/franka-cube-contact-sourcequat-ep16s260_a0p75-step-0.mp4`

Analysis:
- Source-row orientation targeting is useful but insufficient. It preserves
  exact and alpha0.9, adds a clean alpha0.85 pass, and produces an alpha0.8
  visual lift, but alpha0.8 clips on the initial pose action and alpha0.75
  remains a clear failure.
- The alpha0.75 contact sheet shows the same qualitative issue as before:
  gripper closure/lift occurs while the fingers are offset from the cube, then
  the hand lifts away. This keeps the controller relabel gate closed.
- Because alpha0.75 did not pass the hard relabel gate, no official DP
  fine-tune/debug pretrain or RL handoff is authorized from this result.

Next:
- The next bounded controller diagnostic should target the alpha0.8/0.75 gap:
  either reduce the initial pose-action jump/clipping before testing alpha0.8,
  or implement a staged finger-center/contact alignment phase that drives the
  perturbed robot into the source-contact geometry before close/lift.

## 2026-06-11T21:35:30-07:00 - alpha0.8 clipping bridge plan

Goal:
- Bridge the support-expansion controller gap without starting DP training.
  First remove the alpha0.8 initial pose-action clipping in a principled,
  auditable way; only after alpha0.8 passes both hard metrics and visual
  inspection, retest alpha0.75.

Hypothesis:
- The alpha0.8 failure is not contact geometry; it visually lifts but fails the
  hard gate because the first source-orientation correction saturates one
  normalized rotation component. A controller-side pose-action scaling filter
  should avoid per-component clipping while preserving the same relative EE
  convention and gripper timing.
- If alpha0.8 passes with no executed clipping, alpha0.75 can be retested with
  the same filter. If alpha0.75 still closes/lifts away, the blocker is contact
  alignment/support rather than the action-limit artifact.

Planned change:
- Add an explicit pose-action audit/filter to
  `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`:
  - compute raw unclipped normalized 6D pose commands;
  - support `--pose_action_filter clip|scale`;
  - support `--pose_action_limit` for uniform pose-command scaling before the
    final physical clip;
  - log raw max action, filter scale, executed max action, and clip fraction.
- Thread `POSE_ACTION_FILTER` and `POSE_ACTION_LIMIT` through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`.
- Extend aggregate report rows with the new action audit fields.

Validation before cluster:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- `git diff --check`

Planned cluster run:
- Commit/push/deploy exact commit to the agent-owned l401 worktree.
- Launch one bounded relabel gate with `ORIENTATION_MODE=source`,
  `POSE_ACTION_FILTER=scale`, `POSE_ACTION_LIMIT=0.95`, alphas `1.0`, `0.9`,
  and `0.8`, video enabled, same episode `16`, source step `260`,
  `center_high30`, `FINGER_GAIN=0.75`.
- Do not include alpha0.75 in this first run. Retest alpha0.75 only if alpha0.8
  passes hard gates and video inspection.

Gate:
- Exact/alpha0.9 behavior must remain coherent.
- Alpha0.8 must have final/max lift above threshold, final EE/finger distances
  within gate, `max_pose_action_clip_fraction=0`, and visually coherent contact
  lift.
- No DP fine-tune, RL, or broad training in this iteration.

## 2026-06-11T21:39:06-07:00 - alpha0.8 pose-filter relabel gate launch

Goal:
- Test whether a uniform pose-action scaling filter removes the alpha0.8
  initial clip while preserving exact and alpha0.9 behavior.

Change:
- Added raw/unclipped pose-action audit fields and optional
  `--pose_action_filter scale --pose_action_limit <limit>` to the contact-aware
  controller rollout.
- Threaded `POSE_ACTION_FILTER` and `POSE_ACTION_LIMIT` through the relabel-set
  Slurm wrapper and aggregate reports.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `5ae2c638917d3591f9e2f97516089b0ced5427a4`
- push: pushed to `origin/codex/franka-cube-diffusion-policy-bc`
- remote_commit: `5ae2c638917d3591f9e2f97516089b0ced5427a4`
- remote_status: clean detached HEAD
- remote_deploy_note: l401 could not fetch GitHub due SSH public-key auth, so
  the exact commit was transferred through an agent-owned NFS bare Git remote
  at
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-transfer.git`
  and checked out in the agent worktree.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` -> pass
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` -> pass
- `git diff --check` -> pass

Command / Job:
- job_id: `1028127`
- run_name:
  `franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=3,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:1.0,SPEC_1=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.9,SPEC_2=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.8,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=80,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-contact-posefilter095,PRINT_INTERVAL=80,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- expected remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028127.out`

Gate:
- Do not test alpha0.75 until this alpha0.8 pose-filter gate passes hard
  metrics and visual inspection.

## 2026-06-11T21:42:21-07:00 - alpha0.8 pose-filter gate result and alpha0.75 retest plan

Result:
- job_id: `1028127`
- scheduler_status: `COMPLETED 0:0`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902`
- aggregate verdict:
  `PASS: all contact-aware rollouts satisfied the hard relabel gate; this only permits a tiny official-DP smoke proposal.`
- gate table:

| alpha | gate | final EE-cube | final finger-cube | final/max lift | max executed clip | max raw | min scale | visual |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1.00 | pass | 0.0077 | 0.0377 | 0.1360/0.1360 | 0.000 | 0.585 | 1.000 | coherent lift |
| 0.90 | pass | 0.0094 | 0.0382 | 0.1353/0.1353 | 0.000 | 0.522 | 1.000 | coherent lift |
| 0.80 | pass | 0.0466 | 0.0587 | 0.1357/0.1357 | 0.000 | 1.026 | 0.926 | coherent lift; raw first command would have clipped |

Artifacts:
- report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/contact_relabel_set_report.md`
- support report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/support_expansion_report/support_expansion_report.md`
- support plot:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/support_expansion_report/support_expansion_plot.png`
- alpha0.8 sheet:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/rollouts/ep16s260_a0p8/contact_sheet_a0p8.jpg`
- alpha0.8 video:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/rollouts/ep16s260_a0p8/videos/franka-cube-contact-posefilter095-ep16s260_a0p8-step-0.mp4`

Analysis:
- Alpha0.8 clipping was a controller/action-limit artifact from the source
  orientation correction. With the raw command audited and uniformly scaled
  under `0.95`, alpha0.8 clears hard metrics and visual inspection.
- This does not authorize DP training yet. It only satisfies the prerequisite
  to retest alpha0.75 with the same controller filter.

Next bounded launch:
- Run a one-rollout alpha0.75 retest with the same commit
  `5ae2c638917d3591f9e2f97516089b0ced5427a4`, `ORIENTATION_MODE=source`,
  `POSE_ACTION_FILTER=scale`, `POSE_ACTION_LIMIT=0.95`, same episode/source
  step/settings.
- Gate: alpha0.75 must pass final/max lift, final EE/finger distances, zero
  executed clipping, and visual contact/lift. If it fails, stop at artifact
  reporting; no DP training.

## 2026-06-11T21:42:57-07:00 - alpha0.75 pose-filter retest launch

Goal:
- Test whether the same audited pose-action scaling filter that recovered
  alpha0.8 also recovers the first hard support failure at alpha0.75.

Version Control:
- implementation_commit: `5ae2c638917d3591f9e2f97516089b0ced5427a4`
- remote_commit: `5ae2c638917d3591f9e2f97516089b0ced5427a4`
- source_changes_since_alpha0.8_job: none

Command / Job:
- job_id: `1028128`
- run_name:
  `franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=1,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=80,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-contact-posefilter095,PRINT_INTERVAL=40,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- expected remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028128.out`

Gate:
- If alpha0.75 fails metrics or visuals, no DP training; next recommendation
  should be a staged contact-alignment controller, not BC scale-up.

## 2026-06-11T21:46:28-07:00 - pose-filter alpha0.75 result

Result:
- alpha0.8 job_id: `1028127`, `COMPLETED 0:0`
- alpha0.75 job_id: `1028128`, `COMPLETED 0:0`
- implementation_commit for both jobs:
  `5ae2c638917d3591f9e2f97516089b0ced5427a4`
- status: alpha0.8 clipping fixed; alpha0.75 still fails hard relabel gate.

Metrics:

| case | gate | reset cube-minus-EE L2 | final EE | final finger | final/max lift | max clip | max raw | raw would clip | min scale | interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| alpha0.8 pose-filter | pass | 0.0314 | 0.0466 | 0.0587 | 0.1357/0.1357 | 0.000 | 1.026 | 0.167 | 0.926 | alpha0.8 was primarily an action-limit artifact; uniform pose scaling recovered it |
| alpha0.75 pose-filter | fail | 0.0394 | 0.2091 | 0.2504 | 0.0000/0.0143 | 0.000 | 1.283 | 0.167 | 0.740 | alpha0.75 remains a contact-alignment/support failure after action-limit damping |

Artifact URLs:
- combined report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/posefilter095_bridge_summary_20260611_214249/posefilter095_alpha08_alpha075_report.md`
- combined trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/posefilter095_bridge_summary_20260611_214249/posefilter095_alpha08_alpha075_trace.png`
- alpha0.8 aggregate report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/contact_relabel_set_report.md`
- alpha0.75 aggregate report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249/contact_relabel_set_report.md`
- alpha0.8 pass sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/rollouts/ep16s260_a0p8/contact_sheet_a0p8.jpg`
- alpha0.75 failure sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249/rollouts/ep16s260_a0p75/contact_sheet_a0p75.jpg`
- alpha0.8 video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a1_a0p9_a0p8_20260611_213902/rollouts/ep16s260_a0p8/videos/franka-cube-contact-posefilter095-ep16s260_a0p8-step-0.mp4`
- alpha0.75 video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_posefilter095_ep16s260_a0p75_20260611_214249/rollouts/ep16s260_a0p75/videos/franka-cube-contact-posefilter095-ep16s260_a0p75-step-0.mp4`

Analysis:
- The new raw action audit cleanly separates two issues:
  - alpha0.8 needed only action-limit damping on the initial source-orientation
    command; it then passed metrics and video inspection.
  - alpha0.75 also needed damping, but after damping the align-open phase still
    stalled around `0.097 m` finger-center-to-cube before close. Closing at
    that geometry leaves the cube behind and lift drives the gripper away.
- The alpha0.75 accepted NPZ is empty (`obs (0,21)`, `action (0,7)`), so there
  is no relabel dataset to train on from that rollout.
- This is not a DP/BC training gate pass. No official Diffusion Policy
  fine-tune, RL, or broad training should start from this state.

Next:
- Implement a staged contact-alignment controller diagnostic before close/lift:
  drive finger-center error below a threshold near the source-contact geometry
  with open gripper, optionally using a slower or adaptive gain schedule, then
  close/lift only after the contact-alignment gate is met. Retest alpha0.75
  with the same hard metrics and video inspection.

## 2026-06-11T21:49:45-07:00 - staged live-cube contact alignment plan

Goal:
- Add one narrow staged controller diagnostic for alpha0.75 before any DP/RL
  work: after the pose-filtered open alignment, add an open-gripper
  contact-alignment phase that tracks the *live* cube position before close/lift.

Evidence motivating the change:
- In the alpha0.75 pose-filter trace, the first open-alignment motion pushes the
  cube laterally. The controller then converges to a stale target based on the
  original cube pose:
  - at pre-close step 79, finger-center-to-live-cube is about `0.0977 m`;
  - finger error to the stale target is only about `0.0006 m`;
  - target-minus-live-cube is about `[-0.0117, 0.0901, 0.035]`.
- This explains why close/lift happens away from the cube despite zero executed
  clipping.

Planned change:
- Add opt-in rollout args to `contact_aware_franka_cube_rollout.py`:
  - `--contact_align_steps`
  - `--contact_align_reference initial_cube|live_cube`
  - `--contact_align_threshold`
- Keep default behavior unchanged with `contact_align_steps=0`.
- When enabled with `live_cube`, add a `contact_align_open` phase after
  `align_open` that targets `live_cube_pos + offset` with open gripper and
  records contact-alignment audit fields.
- Freeze the live-cube contact anchor at the end of the contact-align phase for
  close/lift, so the lift target is relative to the corrected contact geometry.
- Thread the new env vars through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- `git diff --check`

Planned first run:
- alpha0.75 only.
- Same source episode/step/variant/pose filter as `1028128`.
- Add `CONTACT_ALIGN_STEPS=80`, `CONTACT_ALIGN_REFERENCE=live_cube`,
  `CONTACT_ALIGN_THRESHOLD=0.06`, and `VIDEO_LENGTH=400`.

Gate:
- Alpha0.75 must pass hard metrics and video contact/lift with zero executed
  clipping. If it fails, stop at diagnostics and recommend the next controller
  design option. Alpha0.8 regression check only if alpha0.75 materially
  improves.

## 2026-06-11T21:54:19-07:00 - launch staged contact alignment alpha0.75

Goal:
- Test whether a live-cube open-gripper contact-alignment phase before
  close/lift recovers the alpha0.75 controller relabel gate without hiding the
  failure behind action clipping.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `316700bc0b35b9e102eddd5d22875db47f12e913`
- remote_commit: `316700bc0b35b9e102eddd5d22875db47f12e913`
- changed_files:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` passed.
- `git diff --check` passed.

Command / Job:
- job_id: `1028129`
- run_name:
  `franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=1,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=80,CONTACT_ALIGN_STEPS=80,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.06,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=400,VIDEO_NAME_PREFIX=franka-cube-contact-align80,PRINT_INTERVAL=40,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028129.out`

Gate:
- Acceptance requires final/max lift over threshold, zero executed clipping,
  plausible final EE/finger distances, and video showing contact/lift.
- If alpha0.75 fails, no DP fine-tune, RL, or broad dataset training.

## 2026-06-11T21:57:38-07:00 - staged contact alignment alpha0.75 invalid run and gate patch

Result:
- job_id: `1028129`
- run_name:
  `franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208`
- scheduler status: `COMPLETED 0:0`
- artifact status: fetched locally.
- verdict: invalid as an alpha0.75 close/lift test, because the script treated
  `contact_align_threshold` as an audit field only. It entered
  `contact_align_open` and reduced finger-center-to-cube from about `0.0977 m`
  to a minimum `0.0562 m`, but kept pushing through the fixed 80-step
  contact-align window and terminated/reset at local step `99` before close or
  lift rows were produced.

Metrics / Evidence:
- `steps=99`, `terminated_next_step=true`, `skipped_post_reset_local_step=99`.
- `pre_close_phase=contact_align_open`, `pre_close_local_step=98`.
- `pre_close_finger_center_to_cube=0.0650`, `min_finger_center_to_cube=0.0562`.
- `final/max lift=0.0032/0.0143 m`; no close/lift gate claim.
- `max_pose_action_clip_fraction=0.0`; `max_raw_pose_action_max_abs=1.283`.

Artifacts:
- aggregate report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208/contact_relabel_set_report.md`
- trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- invalid-run contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208/rollouts/ep16s260_a0p75/contact_sheet_a0p75_contactalign80_invalid_1028129.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208/rollouts/ep16s260_a0p75/videos/franka-cube-contact-align80-ep16s260_a0p75-step-0.mp4`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_live_ep16s260_a0p75_20260611_215208/logs/contact_aware_franka_cube_relabel_set_1028129.out`

Patch:
- Updated `contact_aware_franka_cube_rollout.py` so the optional
  contact-align phase becomes an operational gate:
  - if `finger_center_to_cube <= contact_align_threshold`, close/hold starts on
    the next env step;
  - the live cube anchor is frozen at that threshold crossing for close/lift;
  - report/CSV now include trigger step and close-start step.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset_report.py` passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` passed.
- `git diff --check` passed.

Next:
- Commit/deploy the gate patch and relaunch the same alpha0.75 bounded smoke.
- Still no DP fine-tune, RL, or broad training.

## 2026-06-11T21:58:44-07:00 - launch threshold-gated contact alignment alpha0.75

Goal:
- Retest alpha0.75 with the same live-cube staged contact alignment, now using
  the threshold as an actual transition gate into close/hold.

Version Control:
- implementation_commit: `7fe9f0ed4081486a129e88fc5f2e334bbe3a4ab3`
- remote_commit: `7fe9f0ed4081486a129e88fc5f2e334bbe3a4ab3`
- push/deploy: pushed to origin and to the l401 NFS transfer repo; remote
  worktree checked out detached at the same commit.

Command / Job:
- job_id: `1028134`
- run_name:
  `franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=1,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=80,CONTACT_ALIGN_STEPS=80,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.06,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=400,VIDEO_NAME_PREFIX=franka-cube-contact-gateclose80,PRINT_INTERVAL=40,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028134.out`

Gate:
- Alpha0.75 must pass final/max lift, final EE/finger distance, zero executed
  clipping, and visual contact/lift. If it fails, stop at the controller
  diagnostic and document the failure mode.

## 2026-06-11T22:01:08-07:00 - threshold-gated contact alignment alpha0.75 result

Result:
- job_id: `1028134`
- run_name:
  `franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831`
- scheduler status: `COMPLETED 0:0`
- artifact status: fetched locally, report/plot/video opened with `viz-open`,
  contact sheet generated and inspected.
- verdict: hard-gate failure; do not train DP or launch RL.

Metrics / Evidence:
- No close/lift rows were produced. The run entered `contact_align_open` but
  never crossed the `0.06 m` trigger after the initial source-target align.
- `close_start_local_step=-1`, `contact_align_trigger_step=-1`.
- `steps=99`, `terminated_next_step=true`, `skipped_post_reset_local_step=99`.
- `pre_close_phase=contact_align_open`, `pre_close_local_step=98`.
- `pre_close_finger_center_to_cube=0.0650`, `min_finger_center_to_cube=0.0562`.
- `final/max lift=0.0032/0.0143 m`.
- `max_pose_action_clip_fraction=0.0`, `max_raw_pose_action_max_abs=1.283`.

Artifact URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/contact_relabel_set_report.md`
- trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/contact_sheet_a0p75_gateclose80_1028134.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/videos/franka-cube-contact-gateclose80-ep16s260_a0p75-step-0.mp4`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/logs/contact_aware_franka_cube_relabel_set_1028134.out`

Analysis:
- The threshold gate itself works in code, but alpha0.75 does not reach it after
  the 80-step `align_open` phase. The trace shows the first source-target align
  step starts close enough (`finger_center_to_cube=0.0562`) but the fixed
  align phase then drives the hand/cube out of the contact window
  (`~0.0977 m` by step 79). The live-cube contact-align phase improves back
  toward the cube, but only to `0.0650 m` before task termination/reset.
- This narrows the failure mode: the alpha0.75 issue is not executed clipping
  and not a DP train/eval issue; it is controller support/contact alignment,
  with the stale/source align phase actively damaging the nearby contact state.

Next bounded diagnostic:
- Run one no-initial-align variant: `ALIGN_STEPS=0`,
  `CONTACT_ALIGN_STEPS=80`, `CONTACT_ALIGN_REFERENCE=live_cube`,
  `CONTACT_ALIGN_THRESHOLD=0.06`, same alpha0.75/source-orientation/pose-scale
  settings. This directly tests whether closing from the live contact gate can
  recover alpha0.75 when the damaging source-target align phase is removed.
- If this still fails, stop at diagnostics and recommend a different
  controller design rather than DP/RL scale-up.

## 2026-06-11T22:02:09-07:00 - launch no-align contact-gated alpha0.75 diagnostic

Goal:
- Directly test whether alpha0.75 can close/lift from the current live contact
  neighborhood if the damaging fixed source-target `align_open` phase is
  removed.

Version Control:
- implementation_commit: `978714903f24296b0c09252e7c2586237465b649`
- remote_commit: `978714903f24296b0c09252e7c2586237465b649`
- push/deploy: pushed to origin and l401 transfer repo; remote worktree
  checked out detached at this commit.

Command / Job:
- job_id: `1028135`
- run_name:
  `franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=1,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=80,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.06,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-contact-noalign-gateclose,PRINT_INTERVAL=20,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028135.out`

Gate:
- Pass requires alpha0.75 final/max lift, zero executed clipping, final
  EE/finger distances inside the hard gate, and video contact/lift.
- Failure means the next path is a different contact controller design, not DP
  fine-tune or RL.

## 2026-06-11T22:04:21-07:00 - no-align contact-gated alpha0.75 result

Result:
- job_id: `1028135`
- run_name:
  `franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150`
- scheduler status: `COMPLETED 0:0`
- artifact status: fetched locally; report, plot, contact sheet, and video
  opened with `viz-open`; contact sheet inspected.
- verdict: hard-gate failure; do not train DP or launch RL.

Metrics / Evidence:
- The contact gate triggered immediately:
  - `contact_align_trigger_step=0`
  - `close_start_local_step=1`
  - `pre_close_finger_center_to_cube=0.0562 m`
  - `pre_close_ee_to_cube=0.0243 m`
- Gripper closed fully, but the cube was not grasped:
  - `final_gripper_width=0.000212 m`
  - `final/max lift=0.0000/0.0143 m`
  - `final EE-to-cube=0.2246 m`
  - `final finger-center-to-cube=0.2695 m`
  - `max_pose_action_clip_fraction=0.0`
- Early close rows show why scalar finger-center distance is insufficient:
  - step 0: finger `0.0562`, left `0.0810`, right `0.0533`, EE `0.0243`
  - step 1 after close starts: finger `0.0635`, left `0.0776`, right `0.0685`
  - by lift, finger distance grows monotonically and cube lift stays zero.
- Visual contact sheet shows the hand closes/lifts beside/above the cube rather
  than enclosing it.

Artifact URLs:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/contact_relabel_set_report.md`
- trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/contact_sheet_a0p75_noalign_1028135.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/videos/franka-cube-contact-noalign-gateclose-ep16s260_a0p75-step-0.mp4`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/logs/contact_aware_franka_cube_relabel_set_1028135.out`

Analysis:
- Removing the source-target align phase is not sufficient. The controller can
  enter close/lift with zero clipping, but the gripper does not enclose the cube
  at alpha0.75.
- The hard failure is now sharper: alpha0.75 needs a contact controller that
  reasons about left/right finger placement or a lateral centering sweep, not
  only finger-center-to-cube scalar distance. The current scalar threshold can
  be satisfied while the fingers are arranged in a non-grasping geometry.

Next design option:
- Add a bounded left/right finger geometry gate before close:
  - require both left/right finger distances to be plausible and balanced
    before close;
  - add an open-gripper lateral centering/search phase around the live cube
    rather than a fixed high30 offset;
  - keep the hard relabel gate unchanged and test alpha0.75 first.
- No DP fine-tune, RL, or broad dataset training should start until that
  controller relabel gate passes.

Active jobs:
- No C-owned l401 jobs remain. `squeue` shows unrelated job `1028137`
  (`ggx_lowz_bc`) running under the user account; not launched or owned by this
  Worker C run.

## 2026-06-11T22:06:11-07:00 - alpha0.75 relabel branch blocked from DP/RL

Status:
- Blocked for DP fine-tune, RL warm-start, or broader dataset generation.
- No additional scalar finger-center/contact-threshold relaunch is technically
  justified by the 1028134/1028135 video and trace evidence.
- No new Slurm job launched in this entry.

Evidence:
- `1028134` showed the source-target `align_open` phase moves alpha0.75 out of
  support before close: no close/lift rows, `close_start_local_step=-1`, and
  termination/reset at local step `99`.
- `1028135` removed that align phase and proved the scalar contact gate is
  insufficient: `contact_align_trigger_step=0`, `close_start_local_step=1`,
  zero executed clipping, gripper closes fully, but final EE/finger distances
  drift to `0.2246/0.2695 m` and max lift stays `0.0143 m`.
- The contact sheet/video show the gripper closing and lifting beside/above the
  cube rather than enclosing it. Early rows show unbalanced finger geometry
  (`left=0.0810`, `right=0.0533` at the trigger), so
  `finger_center_to_cube <= 0.06` is not a valid grasp-readiness condition.

Artifact references:
- `1028134` report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/contact_relabel_set_report.md`
- `1028134` plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- `1028134` contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/contact_sheet_a0p75_gateclose80_1028134.jpg`
- `1028134` video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_contactalign80_gateclose_ep16s260_a0p75_20260611_215831/rollouts/ep16s260_a0p75/videos/franka-cube-contact-gateclose80-ep16s260_a0p75-step-0.mp4`
- `1028135` report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/contact_relabel_set_report.md`
- `1028135` plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- `1028135` contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/contact_sheet_a0p75_noalign_1028135.jpg`
- `1028135` video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_noalign_gateclose_ep16s260_a0p75_20260611_220150/rollouts/ep16s260_a0p75/videos/franka-cube-contact-noalign-gateclose-ep16s260_a0p75-step-0.mp4`

Recommendation:
- Replace the scalar finger-center gate with a different contact controller
  design before any more DP/RL work. The next design should explicitly use
  left/right finger geometry and lateral centering around the live cube, or a
  grasp-specific closed-loop controller that searches for balanced finger
  placement before closing. Only after that controller passes the same
  alpha0.75 hard relabel gate should official DP training resume.

## 2026-06-11T22:08:16-07:00 - plan left/right contact gate alpha0.75 diagnostic

Goal:
- Implement one narrow controller/relabel diagnostic for alpha0.75: require
  left/right finger geometry before close and use live-cube lateral centering
  during open-gripper contact alignment.

Planned change:
- Edit only the owned contact-aware rollout/controller path and this worklog:
  - `dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
  - `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- Add opt-in args/env vars with defaults preserving previous behavior:
  - `contact_gate_mode=center|left_right`
  - `finger_gate_max_distance`
  - `finger_gate_balance_threshold`
  - `require_contact_gate`
  - `lateral_centering_gain`
  - `lateral_centering_limit`
  - `lateral_search_amplitude`
  - `lateral_search_period`
- During `contact_align_open`, compute left/right finger distances and an
  XY-axis lateral correction from live finger geometry. Freeze the corrected
  target offset only when the gate passes.
- In `left_right` mode, close can start only when the scalar center threshold,
  both left/right distance bounds, and balance threshold pass. The hard relabel
  gate remains unchanged.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- `git diff --check`

Planned bounded launch:
- One alpha0.75 run only, no DP/RL:
  - `ALIGN_STEPS=0`
  - `CONTACT_ALIGN_STEPS=160`
  - `CONTACT_GATE_MODE=left_right`
  - `REQUIRE_CONTACT_GATE=True`
  - `LATERAL_CENTERING_GAIN=0.75`
  - `LATERAL_CENTERING_LIMIT=0.025`
  - `FINGER_GATE_MAX_DISTANCE=0.075`
  - `FINGER_GATE_BALANCE_THRESHOLD=0.015`
- Acceptance remains the same hard relabel gate plus video/trace inspection.

## 2026-06-11T22:12:17-07:00 - launch left/right contact gate alpha0.75

Goal:
- Test whether explicit left/right finger geometry plus live-cube lateral
  centering/search can recover alpha0.75 before close/lift.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `c68df5c88df843fd8d9d7c3fe92fc6ca162024ee`
- remote_commit: `c68df5c88df843fd8d9d7c3fe92fc6ca162024ee`
- push/deploy: pushed to origin and l401 transfer repo; remote worktree
  checked out detached at the same commit.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py` passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh` passed.
- `git diff --check` passed.

Command / Job:
- job_id: `1028145`
- run_name:
  `franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=1,SPEC_0=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=160,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.055,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.075,FINGER_GATE_BALANCE_THRESHOLD=0.015,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.75,LATERAL_CENTERING_LIMIT=0.025,LATERAL_SEARCH_AMPLITUDE=0.004,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=400,VIDEO_NAME_PREFIX=franka-cube-contact-lrcentering,PRINT_INTERVAL=20,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028145.out`

Gate:
- Same hard relabel gate: final/max lift, zero executed clipping, final
  EE/finger distances, and visual contact/lift. If this fails, no DP/RL.

## 2026-06-11T22:15:49-07:00 - left/right contact gate alpha0.75 result and official-DP smoke plan

Goal:
- Record the accepted alpha0.75 left/right contact-gate diagnostic and move
  one bounded step to an official Diffusion Policy smoke on its accepted relabel
  NPZ.

Result:
- job_id: `1028145`
- run_name:
  `franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000`
- scheduler status: `COMPLETED 0:0`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000`
- accepted relabel NPZ:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/contact_relabel_set_accepted.npz`
- accepted NPZ shape: `obs (240, 21)`, `action (240, 7)`,
  `episode_ends [240]`.
- phase counts: `-1: 22`, `1: 80`, `2: 138`.
- hard-gate metrics:
  - `final/max lift=0.1356/0.1356 m`
  - `final EE-to-cube=0.0298 m`
  - `final finger-center-to-cube=0.0581 m`
  - `max_pose_action_clip_fraction=0.0`
  - `final_gripper_width=0.04174 m`
- report says:
  `PASS: all contact-aware rollouts satisfied the hard relabel gate; this only permits a tiny official-DP smoke proposal.`
- visual contact sheet was inspected. It is plausible enough for the next
  bounded official-DP smoke, but this is still a single-episode relabel
  artifact and not BC/RL readiness.

Viewer URLs:
- relabel report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/contact_relabel_set_report.md`
- trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/rollouts/ep16s260_a0p75/contact_rollout_plot.png`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/rollouts/ep16s260_a0p75/contact_sheet_lrcentering_1028145.jpg`
- video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/rollouts/ep16s260_a0p75/videos/franka-cube-contact-lrcentering-ep16s260_a0p75-step-0.mp4`

Official DP smoke plan:
- Use the official `real-stanford/diffusion_policy` checkout already
  established for this branch:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
  at commit `5ba07ac6661db573af695b419a7947ecb704690f`, remote
  `https://github.com/real-stanford/diffusion_policy`.
- Run locally in the established official-DP venv:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv`.
- Because this accepted NPZ has only one episode, a meaningful held-out episode
  split is not feasible. Set `task.dataset.val_ratio=0.0` and treat validation
  metrics as train-distribution mechanics only. Use checkpoint action smokes as
  the replay-style offline artifact.
- Train command scope:
  - official `train.py`;
  - `policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy`;
  - `+policy.action_loss_weights=[1,1,1,1,1,1,8]`;
  - `pred_action_steps_only=true`;
  - `task.dataset.action_normalizer=limits_clamp_constant`;
  - `policy.num_inference_steps=100`;
  - tiny local run: `training.num_epochs=40`, `training.max_train_steps=10`,
    `training.max_val_steps=1`, batch size `16`.
- Required artifacts:
  - resolved Hydra config;
  - `logs.json.txt` and parsed loss table/plot;
  - checkpoint path;
  - checkpoint action-range smokes for `first`, `gripper_closed`,
    `lift_high`, and the explicit close-boundary row if feasible;
  - gripper/action semantics plot/report;
  - relabel contact sheet/video links as visual sanity context.

Acceptance:
- Official-DP config/model/training runs without non-finite losses and writes a
  checkpoint.
- Loss decreases on this tiny single-episode smoke.
- Checkpoint action smokes are finite and have sensible gripper sign for
  open/closed/lift rows. Failure blocks closed-loop eval and any DP/RL scale-up.

## 2026-06-11T22:19:40-07:00 - official DP alpha0.75 single-episode smoke result

Goal:
- Run the tiny official Diffusion Policy smoke authorized after `1028145`:
  train only on the accepted single-episode alpha0.75 left/right-contact relabel
  NPZ and inspect checkpoint action semantics before any closed-loop eval.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `f1c7bd440b470fe497ac2edfbb31b971ee710d1f`
- changed_files: worklog only for this entry.
- official_diffusion_policy:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
  at `5ba07ac6661db573af695b419a7947ecb704690f`, remote
  `https://github.com/real-stanford/diffusion_policy`.

Command / Job:
- job_id: `n/a`, local RTX 6000 Ada official-DP smoke.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216`
- launch command file:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/launch_command.sh`
- train command summary:
  official `train.py`, `WeightedDiffusionUnetLowdimPolicy`,
  `+policy.action_loss_weights=[1,1,1,1,1,1,8]`,
  `pred_action_steps_only=true`,
  `task.dataset.action_normalizer=limits_clamp_constant`,
  `policy.num_inference_steps=100`,
  `training.num_epochs=40`, `training.max_train_steps=10`,
  `task.dataset.val_ratio=0.0`, batch size `16`.
- accepted dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/contact_relabel_set_accepted.npz`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/official_dp_train/checkpoints/latest.ckpt`

Result:
- status: `needs_review`; do not launch closed-loop DP eval, broad DP
  training, or RL from this checkpoint.
- dataset report passed:
  - `obs (240, 21)`, `action (240, 7)`, `episode_ends [240]`
  - train samples `240`, val samples `0`
  - `val_ratio=0.0` because there is only one episode.
- adapter smoke passed:
  `FRANKA_CUBE_DP_BC_SMOKE_PASSED`, official DP dataset base imported.
- official DP train completed and wrote `latest.ckpt`.
- loss decreased on-train-distribution:
  - train loss `2.1653 -> 0.5293`
  - train action MSE `0.3951 -> 0.1329`
  - validation loss is `nan`/absent because a held-out episode split is not
    feasible for this single-episode smoke.
- checkpoint action-range smokes:
  - `gripper_closed`: pass, gripper predicted negative.
  - `lift_high`: pass, gripper predicted negative.
  - `first/open`: needs review; bridge first-action gripper includes negative
    values despite open labels.
  - `close_boundary` row index `22`: needs review; direct/bridge gripper
    includes positive values despite close labels.
- corrected gripper/action audit with `--episode-index 0`:
  - `gripper_gate_pass=false`
  - open sign match `0.70`, closed/lift sign match `0.96`, pass threshold
    `0.90`.
  - The per-channel scatter also shows broad pose prediction mismatch, not only
    a clean gripper-only issue.

Viewer URLs:
- official DP pretrain report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/official_dp_pretrain_report.md`
- loss plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/loss_curves.png`
- gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/gripper_sign_audit_100steps/gripper_label_vs_prediction.png`
- per-channel action scatter:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/gripper_sign_audit_100steps/per_channel_first_action_scatter.png`
- resolved Hydra config:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/official_dp_train/.hydra/config.yaml`
- train stdout:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_official_dp_smoke_20260611_2216/logs/official_dp_tiny_train.log`
- visual sanity source rollout video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/rollouts/ep16s260_a0p75/videos/franka-cube-contact-lrcentering-ep16s260_a0p75-step-0.mp4`
- visual sanity source contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep16s260_a0p75_20260611_221000/rollouts/ep16s260_a0p75/contact_sheet_lrcentering_1028145.jpg`

Analysis:
- The official implementation consumes the accepted alpha0.75 relabel NPZ and
  trains mechanically, so the official-DP data/config path remains valid.
- This checkpoint is not closed-loop-eval ready. The single-episode dataset
  overfits partly, but the first/open and close-boundary action semantics are
  not stable enough; launching Isaac eval would likely produce another
  ambiguous failure video rather than a useful BC readiness signal.
- The result supports the next bounded direction only: either improve the
  support-expanded relabel set beyond one episode around alpha0.75, or add
  explicit phase/progress conditioning/deterministic gripper scheduling and
  repeat the offline action-semantics gate. It does not authorize DP scale-up or
  RL.

Active jobs:
- No C-owned Slurm jobs or local training processes remain from this smoke.

## 2026-06-11T22:22:43-07:00 - plan alpha0.75 support relabel expansion

Goal:
- Improve the offline official-DP action-semantics gate before any Isaac DP
  eval by expanding accepted alpha0.75 relabel support beyond the single
  episode from `1028145`.

Decision:
- Choose support expansion, not phase/progress conditioning yet. The
  single-episode official-DP smoke trains mechanically but has unstable
  open/close-boundary action semantics. Changing the 21D observation schema or
  adding a deterministic gripper wrapper now would create a new bridge before
  verifying whether the issue is simply insufficient alpha0.75 support.

Planned bounded relabel diagnostic:
- Generate a tiny 4-rollout alpha0.75 relabel set using the same controller
  settings that passed `1028145`:
  - source episodes: `8, 16, 24, 30`
  - source step: `260`
  - reset joint blend alpha: `0.75`
  - `ORIENTATION_MODE=source`
  - `POSE_ACTION_FILTER=scale`, `POSE_ACTION_LIMIT=0.95`
  - `ALIGN_STEPS=0`
  - `CONTACT_ALIGN_STEPS=160`
  - `CONTACT_ALIGN_REFERENCE=live_cube`
  - `CONTACT_ALIGN_THRESHOLD=0.055`
  - `CONTACT_GATE_MODE=left_right`
  - `REQUIRE_CONTACT_GATE=True`
  - `FINGER_GATE_MAX_DISTANCE=0.075`
  - `FINGER_GATE_BALANCE_THRESHOLD=0.015`
  - `LATERAL_CENTERING_GAIN=0.75`
  - `LATERAL_CENTERING_LIMIT=0.025`
  - `LATERAL_SEARCH_AMPLITUDE=0.004`
  - `LATERAL_SEARCH_PERIOD=32`
  - hard relabel gate unchanged:
    `min_lift=0.10`, `max_pose_clip_fraction=0.0`,
    `max_final_ee_to_cube=0.05`, `max_final_finger_to_cube=0.08`.

Validation before launch:
- `python3 -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py dextrah_lab/offline_dp_bc/make_official_dp_pretrain_report.py dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`: passed.
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`: passed.
- `git diff --check`: passed.

Acceptance:
- If all four alpha0.75 relabel rollouts pass the hard gate and visual contact
  sheets look coherent, run one bounded local official-DP offline smoke on the
  accepted NPZ with the existing official `real-stanford/diffusion_policy`
  setup.
- If any rollout fails, do not train DP; fetch/report failure artifacts and
  treat support expansion as blocked at the relabel gate.
- No closed-loop DP eval, broad DP training, or RL in this iteration.

## 2026-06-11T22:23:41-07:00 - launch alpha0.75 support relabel set

Goal:
- Generate a tiny support-expanded alpha0.75 relabel set for the offline
  official-DP action-semantics gate, using the same hard relabel gate and
  left/right contact controller that passed `1028145`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dd6cfe0b2f97a1ab8f19ba8733aad6821c54efa6`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  detached clean at `dd6cfe0b2f97a1ab8f19ba8733aad6821c54efa6`.
- push/deploy: pushed to origin and l401 transfer repo; remote worktree
  checked out detached at the exact commit.

Command / Job:
- job_id: `1028152`
- run_name:
  `franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224,DATASET=/results/dp_bc/datasets/franka_cube_curobo_lowdim_scale32_20260611_125957_full_pick_lift_framefix.npz,TRAJECTORY_ROOT=/results/dp_bc/curobo_plans,SPEC_COUNT=4,SPEC_0=8:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json:0.75,SPEC_1=16:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed16/trajectory.json:0.75,SPEC_2=24:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed24/trajectory.json:0.75,SPEC_3=30:260:/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed30/trajectory.json:0.75,VARIANT=center_high30,ORIENTATION_MODE=source,POSE_ACTION_FILTER=scale,POSE_ACTION_LIMIT=0.95,ALIGN_STEPS=0,CONTACT_ALIGN_STEPS=160,CONTACT_ALIGN_REFERENCE=live_cube,CONTACT_ALIGN_THRESHOLD=0.055,CONTACT_GATE_MODE=left_right,FINGER_GATE_MAX_DISTANCE=0.075,FINGER_GATE_BALANCE_THRESHOLD=0.015,REQUIRE_CONTACT_GATE=True,LATERAL_CENTERING_GAIN=0.75,LATERAL_CENTERING_LIMIT=0.025,LATERAL_SEARCH_AMPLITUDE=0.004,LATERAL_SEARCH_PERIOD=32,CLOSE_STEPS=80,LIFT_STEPS=160,LIFT_HEIGHT=0.22,FINGER_GAIN=0.75,CLIP_ACTIONS=1.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=400,VIDEO_NAME_PREFIX=franka-cube-contact-lrcentering-a0p75-set,PRINT_INTERVAL=40,SEED=42,GATE_MIN_LIFT=0.10,GATE_MAX_POSE_CLIP_FRACTION=0.0,GATE_MAX_FINAL_EE_TO_CUBE=0.05,GATE_MAX_FINAL_FINGER_TO_CUBE=0.08 cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/contact_aware_franka_cube_relabel_set_1028152.out`

Expected artifacts:
- `contact_relabel_set_report.md`, `contact_relabel_set_summary.json`,
  `contact_relabel_set_rollouts.csv`, `contact_relabel_set_failures.csv`, and
  `contact_relabel_set_accepted.npz` if all rollouts pass.
- Per-rollout CSV/JSON/plot/report/video/contact-sheet artifacts for episodes
  `8,16,24,30`.

Next:
- Monitor job `1028152`; fetch and inspect artifacts. If the relabel set
  passes hard/visual gates, run a bounded local official-DP offline smoke on
  the accepted multi-episode NPZ. If it fails, stop at relabel gate diagnostics.

## 2026-06-11T22:27:32-07:00 - alpha0.75 support relabel set result

Goal:
- Complete artifact inspection for the tiny 4-rollout alpha0.75 support
  relabel set before deciding whether any official-DP smoke is permitted.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- launched_remote_commit:
  `dd6cfe0b2f97a1ab8f19ba8733aad6821c54efa6`
- local_result_commit: `pending`
- changed_files: worklog only for this result entry.

Command / Job:
- job_id: `1028152`
- run_name:
  `franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224`
- stdout log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/logs/contact_aware_franka_cube_relabel_set_1028152.out`

Result:
- status: `passed relabel gate`; this only permits a tiny offline official-DP
  smoke, not closed-loop DP eval, broad DP training, or RL.
- aggregate summary:
  - accepted episodes: `4`
  - accepted transitions: `936`
  - accepted NPZ:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz`
  - failure count: `0`
  - hard gate: min lift `0.10`, max executed pose clip fraction `0.0`,
    max final EE-to-cube `0.05`, max final finger-center-to-cube `0.08`.
- per-rollout gate metrics:
  - ep08: final/max lift `0.136285`, final EE `0.007423`,
    final finger `0.051884`, executed clip fraction `0.0`.
  - ep16: final/max lift `0.135575`, final EE `0.029782`,
    final finger `0.058112`, executed clip fraction `0.0`.
  - ep24: final/max lift `0.136432`, final EE `0.011587`,
    final finger `0.053011`, executed clip fraction `0.0`.
  - ep30: final/max lift `0.135385`, final EE `0.007417`,
    final finger `0.052361`, executed clip fraction `0.0`.
- controller caveat:
  ep16 and ep30 used pose-action scaling in early alignment
  (`min_pose_action_filter_scale` `0.740` and `0.694`) because raw pose actions
  would have exceeded the relabel action limit, but executed clipping remained
  zero by design.
- visual inspection:
  Generated local contact sheets for all four rollouts and inspected them.
  They show the gripper reaches the cube, closes around it, and lifts without
  the previous alpha0.75 lateral drift-away failure.

Viewer URLs:
- set report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_report.md`
- set summary:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_summary.json`
- ep08 contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/rollouts/ep08s260_a0p75/contact_sheet.jpg`
- ep16 contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/rollouts/ep16s260_a0p75/contact_sheet.jpg`
- ep24 contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/rollouts/ep24s260_a0p75/contact_sheet.jpg`
- ep30 contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/rollouts/ep30s260_a0p75/contact_sheet.jpg`

Analysis:
- The left/right finger geometry gate plus live-cube lateral centering
  recovered alpha0.75 for this small support-expanded set under the hard
  relabel gate.
- This result only validates the relabel generator for four source-contact
  perturbation rollouts. It does not prove normal-reset generalization and does
  not authorize closed-loop DP eval or RL.
- Because the prior single-episode official-DP smoke had unstable
  open/close-boundary gripper semantics, the next bounded step is a tiny
  official-DP offline smoke on this 4-episode accepted NPZ with a held-out
  split and the same action-semantics gate.

Next:
- Commit this worklog boundary.
- Run one bounded local official `real-stanford/diffusion_policy` smoke on the
  accepted 4-episode alpha0.75 NPZ: dataset/normalizer check, short weighted
  gripper-loss train, checkpoint action-range smokes, gripper/action semantics
  plots, and report. No Isaac closed-loop eval unless that offline gate passes
  in a later reviewed step.

## 2026-06-11T22:30:29-07:00 - phase metadata diagnostic fix before DP smoke

Goal:
- Keep the offline action-semantics gate accurate for contact-aware relabel
  datasets before running the 4-episode official-DP smoke.

Issue:
- The accepted relabel set from `1028152` contains `phase_ids` of `-1`, `1`,
  and `2`. The `-1` rows are the open/contact-alignment rows because the
  rollout step phase is named `contact_align_open`, while the relabel set
  report only mapped `align_open` to phase id `0`.
- Training does not use `phase_ids`, but the action-semantics diagnostic did:
  it would label `-1` rows as the last raw phase and could select the wrong
  demo reference windows.

Change:
- `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`: map
  `contact_align_open` to contact relabel phase `0` for future relabel sets.
- `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`: treat contact
  relabel phase ids in `{-1,0,1,2}` as contact data, with `-1` and `0` both
  mapped to `align_open`, and select first close/lift rows from ids `1/2`.

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py dextrah_lab/offline_dp_bc/make_official_dp_pretrain_report.py dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`: passed.
- `git diff --check`: passed.

Version Control:
- base_commit: `526bf48b9b8457ab57af9585bd4258ae6e766af7`
- implementation_commit: `pending`
- changed_files:
  `dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`,
  `dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py`,
  worklog.

Next:
- Commit and push this diagnostic fix.
- Run the bounded local official-DP offline smoke on the accepted `1028152`
  NPZ with `val_ratio=0.25`, weighted gripper loss, resolved config/log/loss
  artifacts, checkpoint action smokes, and the corrected action-semantics
  report. No Isaac closed-loop eval or RL.

## 2026-06-11T22:32:13-07:00 - launch official DP alpha0.75 set4 offline smoke

Goal:
- Test whether the official `real-stanford/diffusion_policy` implementation
  can consume the support-expanded alpha0.75 contact relabel set and produce a
  bounded checkpoint with coherent offline action/gripper semantics.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- dextrah_commit: `44e049365675074cb09f62b13a6be44b705a1bea`
- official_dp_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`
- official_dp_commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- official_dp_remote: `https://github.com/real-stanford/diffusion_policy`

Command / Job:
- job_id: `n/a`, local bounded official-DP smoke.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202`
- launch script:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/launch_command.sh`
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz`
- launch command:
  `bash /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/launch_command.sh`

Smoke bounds:
- offline only; no Isaac closed-loop eval and no RL.
- dataset expected shapes:
  `obs (936,21)`, `action (936,7)`, `episode_ends [240,480,706,936]`.
- official DP config:
  `WeightedDiffusionUnetLowdimPolicy`,
  `+policy.action_loss_weights=[1,1,1,1,1,1,8]`,
  `pred_action_steps_only=true`,
  `task.dataset.action_normalizer=limits_clamp_constant`,
  `task.dataset.val_ratio=0.25`, `policy.num_inference_steps=100`,
  `training.num_epochs=60`, `training.max_train_steps=10`,
  `training.max_val_steps=2`, batch size `32`.
- action semantics gate:
  checkpoint smokes for `first`, `gripper_open`, `gripper_closed`,
  `lift_high`, and close-boundary rows `22,262,490,721`; corrected
  gripper/per-channel semantics report at 100 inference steps with pass
  threshold `0.90`.

Expected artifacts:
- dataset report/summary/range CSVs.
- resolved Hydra config, train stdout, `logs.json.txt`, loss CSV/plot.
- checkpoint `official_dp_train/checkpoints/latest.ckpt`.
- checkpoint action-range logs.
- `action_semantics_100steps` CSV/JSON/plots/report.
- official DP pretrain report/summary.

Next:
- Run and monitor the local smoke. If the offline gate is `needs_review`, do
  not launch Isaac eval; analyze and patch the offline semantics path instead.

## 2026-06-11T22:38:05-07:00 - official DP alpha0.75 set4 smoke result and phase-progress plan

Goal:
- Inspect the bounded official-DP smoke on the 4-episode alpha0.75 contact
  relabel set and decide whether the checkpoint is eligible for closed-loop
  eval.

Result:
- status: `needs_review`; no closed-loop DP eval, RL, or broad training is
  allowed from this checkpoint.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202`
- dataset:
  `obs (936,21)`, `action (936,7)`, `episode_ends [240,480,706,936]`,
  `val_ratio=0.25`, `limits_clamp_constant` action normalizer.
- official DP:
  `real-stanford/diffusion_policy` at
  `5ba07ac6661db573af695b419a7947ecb704690f`.
- loss gate:
  - train loss `2.10234 -> 0.126737`
  - val loss `2.11187 -> 0.590239`
  - train action MSE `0.461013 -> 0.032911`
  - checkpoint written:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/official_dp_train/checkpoints/latest.ckpt`
- action/gripper gate:
  - `action_range_status=pass`
  - `action_range_semantics=needs_review`
  - corrected 100-step action-semantics audit:
    `gripper_gate_pass=false`
  - open sign match `0.80`
  - closed/lift sign match `0.944444`
  - closed/lift selector rows mostly pass, but exact close-boundary rows are
    unstable:
    row `22` and row `490` can predict positive/open gripper despite
    `label=-1`.

Viewer URLs:
- official DP report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/official_dp_pretrain_report.md`
- loss plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/loss_curves.png`
- gripper semantics plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/action_semantics_100steps/gripper_label_vs_prediction.png`
- per-channel action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_official_dp_smoke_20260611_223202/action_semantics_100steps/per_channel_first_action_scatter.png`
- source relabel contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_sheet_2x2.jpg`

Analysis:
- Support expansion alone improved the dataset size and validation loss, but it
  did not solve the close-boundary/open ambiguity.
- The key ambiguity is structural: at first close, the current lowdim state can
  still have open gripper width, while the correct action should switch to
  close. The 21D state does not encode contact-controller phase or progress, so
  the policy has to infer a time switch from a small support set.
- The next bounded route is an offline-only phase/progress-conditioned smoke:
  append contact phase one-hot plus episode progress to the accepted NPZ and
  test whether official DP action semantics become coherent. This is not a
  closed-loop eval-ready bridge; a runtime eval would need a matching feature
  provider or deterministic schedule.

Change for next attempt:
- Add `make_phase_progress_dataset.py` to create a 25D offline diagnostic NPZ
  from the accepted contact relabel set.
- Update existing dataset/checkpoint/report utilities so they accept augmented
  observation dimensions and direct-only checkpoint smokes without PPO bridge
  validation.

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/make_phase_progress_dataset.py dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py dextrah_lab/offline_dp_bc/validate_dataset_smoke.py dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py dextrah_lab/offline_dp_bc/make_official_dp_pretrain_report.py dextrah_lab/offline_dp_bc/diagnose_dp_action_semantics.py`: passed.
- `git diff --check`: passed.

Version Control:
- base_commit: `4f3f6140f8bd3f0af1fc2a2bfb1e09307bff4248`
- implementation_commit: `pending`
- changed_files:
  `dextrah_lab/offline_dp_bc/make_phase_progress_dataset.py`,
  `dextrah_lab/offline_dp_bc/make_lowdim_dataset_report.py`,
  `dextrah_lab/offline_dp_bc/validate_dataset_smoke.py`,
  `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`,
  `dextrah_lab/offline_dp_bc/make_official_dp_pretrain_report.py`,
  worklog.

Next:
- Commit and push the phase/progress offline tooling.
- Run one bounded official-DP smoke on the 25D phase/progress NPZ:
  dataset report, direct-only checkpoint range smokes, corrected action
  semantics report, and pretrain report. No closed-loop eval/RL.

## 2026-06-11T22:39:03-07:00 - status before phase-progress official DP smoke

Status:
- The 21D set4 official-DP smoke completed and is `needs_review`; all artifacts
  are local and viewer URLs are recorded above.
- No C-owned local DP/training/diagnostic process is active at this moment.
- No C-owned Slurm job is active from this smoke loop.

Version Control:
- phase metadata diagnostic fix commit:
  `44e049365675074cb09f62b13a6be44b705a1bea`
- 21D set4 launch/result worklog commit:
  `4f3f6140f8bd3f0af1fc2a2bfb1e09307bff4248`
- phase/progress offline tooling commit:
  `d2426151e229ed81b72a3fb427cd5d6cdfbf9c4a`
- branch: `codex/franka-cube-diffusion-policy-bc`
- pushed: yes, through `d2426151e229ed81b72a3fb427cd5d6cdfbf9c4a`.

Next:
- Launch one offline-only 25D phase/progress official-DP smoke to test whether
  explicit phase/progress conditioning resolves the close-boundary gripper
  ambiguity. This diagnostic cannot be used for Isaac eval without a matching
  runtime feature provider.

## 2026-06-11T22:40:10-07:00 - launch phase-progress official DP offline smoke

Goal:
- Run one bounded official-DP offline diagnostic with explicit phase/progress
  conditioning to test whether the 21D checkpoint's close-boundary gripper
  ambiguity is due to missing switch-state information.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- dextrah_commit: `9855352b4175eeed9e3cd81ce9aef24a031c5b24`
- official_dp_commit: `5ba07ac6661db573af695b419a7947ecb704690f`
- official_dp_remote: `https://github.com/real-stanford/diffusion_policy`

Command / Job:
- job_id: `n/a`, local bounded official-DP smoke.
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001`
- launch script:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/launch_command.sh`
- launch command:
  `bash /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/launch_command.sh`
- base dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz`
- generated dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`

Smoke bounds:
- offline only; no Isaac closed-loop eval and no RL.
- appends four diagnostic observation features to the 21D state:
  `phase_align_open`, `phase_close_hold`, `phase_lift`, `episode_progress`.
- official DP config:
  `obs_dim=25`, `policy.model.global_cond_dim=50`,
  weighted gripper loss `[1,1,1,1,1,1,8]`,
  `val_ratio=0.25`, `limits_clamp_constant`, `num_epochs=60`,
  `max_train_steps=10`, `max_val_steps=2`.
- checkpoint smokes are `direct-only`; the 25D dataset does not have a PPO
  bridge/runtime feature provider.

Expected artifacts:
- phase/progress dataset report and summary.
- dataset report/summary/range CSVs.
- resolved Hydra config, train stdout, `logs.json.txt`, loss CSV/plot.
- checkpoint `official_dp_train/checkpoints/latest.ckpt`.
- direct-only checkpoint action-range logs.
- corrected action-semantics CSV/JSON/plots/report.
- official DP pretrain report/summary.

Next:
- Run and monitor the local smoke. If this offline gate passes, report it as a
  diagnostic pass only and propose the next separate runtime-feature bridge
  gate; do not launch Isaac eval/RL from this artifact alone.

## 2026-06-11T22:45:30-07:00 - phase-progress official DP offline smoke result

Goal:
- Finish the bounded 25D phase/progress official Diffusion Policy smoke on the
  accepted 4-episode alpha0.75 contact relabel set and upload inspectable
  artifacts.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base/local commit for run launch:
  `9855352b4175eeed9e3cd81ce9aef24a031c5b24`
- phase metadata diagnostic fix commit:
  `44e049365675074cb09f62b13a6be44b705a1bea`
- phase/progress tooling commit:
  `d2426151e229ed81b72a3fb427cd5d6cdfbf9c4a`
- result/source checkpoint commit before handoff hash finalization:
  `3deb41a64045c5166cbf5a1212c7981ee8984408`
- final branch tip:
  reported in the Worker C handoff; embedding the current commit hash in the
  same commit would change the hash.
- official DP commit:
  `5ba07ac6661db573af695b419a7947ecb704690f`
- official DP remote:
  `https://github.com/real-stanford/diffusion_policy`
- changed_files for post-run source fix:
  `dextrah_lab/offline_dp_bc/validate_official_checkpoint_smoke.py`, worklog.

Command / Job:
- job_id: `n/a`; local bounded official-DP smoke.
- launch script:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/launch_command.sh`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001`
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_train/checkpoints/latest.ckpt`

Result:
- status: `passed` as an offline-only action-semantics/debug-pretrain gate.
- dataset shape:
  - base accepted relabel NPZ: `obs (936,21)`, `action (936,7)`,
    `episode_ends [240,480,706,936]`
  - phase/progress NPZ: `obs (936,25)`, `action (936,7)`,
    appended features
    `phase_align_open`, `phase_close_hold`, `phase_lift`,
    `episode_progress`
  - phase counts: `align_open=69`, `close_hold=320`, `lift=547`
- loss gate:
  - train loss `2.12427 -> 0.124252`
  - val loss `2.16282 -> 0.518714`
  - train action MSE `0.470958 -> 0.0244009`
- action semantics:
  - pretrain verdict: `pass`
  - `action_range_status=pass`
  - `action_range_semantics=pass`
  - `gripper_gate_pass=true`
  - open sign match `0.96`
  - closed/lift sign match `0.962963`
  - rows audited: `79`
- post-run source fix:
  - `validate_official_checkpoint_smoke.py` now uses the fixed base lowdim
    gripper-width index `20` for row selectors and selected gripper reporting.
    This matters for augmented offline obs because column `-1` is now
    `episode_progress`.
  - Reran direct-only checkpoint action-range smokes and regenerated the
    official DP pretrain report without retraining.
- local process status:
  no matching C-owned local official-DP, checkpoint-smoke, or action-semantics
  process remains active after the artifact rerun.

Viewer URLs:
- official DP report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_pretrain_report.md`
- phase/progress dataset report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/phase_progress_dataset_report.md`
- loss curves:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/loss_curves.png`
- gripper semantics plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/action_semantics_100steps/gripper_label_vs_prediction.png`
- per-channel action semantics plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/action_semantics_100steps/per_channel_first_action_scatter.png`

Analysis:
- Explicit phase/progress features resolve the 21D smoke's close-boundary
  gripper ambiguity in the offline checkpoint audit.
- This is not Isaac closed-loop-ready. The 25D checkpoint consumes four
  features that are not present in the current 72D PPO observation bridge:
  contact phase one-hot plus episode progress. Running this checkpoint in Isaac
  without a matching runtime feature provider would be another train/eval
  mismatch.
- Pose-channel prediction quality is still loose in the per-channel scatter,
  so the pass should be treated as a gripper/action-semantics mechanics gate,
  not a behavior-readiness claim.

Next:
- Stop before Isaac closed-loop eval/RL from this artifact alone.
- Next bounded bridge plan:
  1. Implement a runtime feature provider that appends the same four
     phase/progress fields to live lowdim observations, driven either by the
     relabel controller phase schedule or a separately validated deterministic
     task-progress state machine.
  2. Validate that provider offline by replaying accepted relabel traces and
     checking exact feature parity with `contact_relabel_set_phase_progress.npz`.
  3. Only after feature parity passes, run a tiny no-video matched-reset
     closed-loop trace with the 25D checkpoint and inspect action/support
     traces before any video, broader eval, BC scale-up, or RL handoff.

## 2026-06-11T22:56:34-07:00 - plan runtime phase-progress bridge

Goal:
- Move one safe step beyond the offline-only 25D DP smoke by implementing a
  runtime feature provider for `phase_align_open`, `phase_close_hold`,
  `phase_lift`, and `episode_progress` without changing the existing 21D eval
  path.

Hypothesis:
- The 25D checkpoint only becomes eligible for a bounded closed-loop trace if
  live observations append the same four features used in
  `contact_relabel_set_phase_progress.npz`.
- A deterministic schedule derived from the accepted contact-relabel phase
  counts is the smallest safe bridge for the first matched-reset trace. It is
  not a general policy-state estimator; it is a parity-preserving diagnostic.

Planned edits:
- Add phase/progress provider helpers in `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  or a nearby offline-DP bridge module:
  - constants for the four feature names and 25D obs dim.
  - deterministic schedule/provider that maps per-env step to phase one-hot and
    normalized episode progress.
  - augmented extraction/action-query helpers that preserve existing 21D
    behavior when no provider is supplied.
- Add an offline parity checker, likely
  `dextrah_lab/offline_dp_bc/validate_phase_progress_runtime_provider.py`,
  which compares provider-generated features against the generated 25D NPZ for
  all accepted set4 rows and writes report/JSON/CSV artifacts.
- Wire `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py` behind explicit
  CLI flags so 25D checkpoints require a provider and 21D checkpoints remain
  unchanged.
- Extend `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` only if needed to
  pass provider flags to l401.

Validation before any cluster eval:
- `python3 -m py_compile` for changed Python modules.
- `bash -n` for any changed wrapper.
- `git diff --check`.
- Run the offline parity checker locally on:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`
  and require exact/near-exact feature parity.

Bounded launch gate:
- Only if parity passes, commit/push/deploy exact commit to the C-owned l401
  worktree and launch one no-video matched source-joint trace:
  `num_envs=1`, short horizon, `ACTION_CHUNK_STEPS=1`,
  `DEBUG_POLICY_TRACE_MAX_CALLS` enabled, no broad video/RL.
- Inspect metrics/support/policy trace before deciding whether a short video is
  warranted.

Version Control:
- base_commit: `3fe930293fa855b75d2d76cda217fa183f1cf434`
- implementation_commit: `pending`
- active local/cluster jobs at plan time: none known.

## 2026-06-11T23:00:00-07:00 - runtime phase-progress provider parity pass

Goal:
- Implement the smallest runtime bridge for the 25D phase/progress checkpoint
  and validate that it reproduces the generated offline feature columns before
  any Isaac trace.

Change:
- Added a dataset-backed phase/progress provider in
  `dextrah_lab/offline_dp_bc/ppo_bridge.py`.
  - It appends `phase_align_open`, `phase_close_hold`, `phase_lift`, and
    `episode_progress` to the extracted 21D lowdim observation.
  - It is explicit and dataset-backed: the first matched-reset trace will use
    the selected accepted relabel episode's stored phase/progress schedule.
  - Existing 21D bridge behavior remains unchanged when no provider is passed.
- Added
  `dextrah_lab/offline_dp_bc/validate_phase_progress_runtime_provider.py`.
  - It compares provider output row-for-row against the generated 25D NPZ and
    writes report/JSON/CSV artifacts.
- Updated `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
  - New explicit flags:
    `--phase_progress_dataset`, `--phase_progress_episode`,
    `--phase_progress_start_step`.
  - 25D checkpoints now fail early without a provider instead of silently
    feeding 21D obs.
  - Policy/support traces include `lowdim_obs_dim` and phase/progress values.
  - Demo reset now tolerates 25D datasets by using only the base 21D fields for
    cube/robot reset comparisons.
- Updated `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` to pass the new
  provider flags through l401.

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/offline_dp_bc/validate_phase_progress_runtime_provider.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`: passed.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`: passed.
- `git diff --check`: passed.
- Offline parity command:
  `PYTHONPATH=$DEX $VENV -m dextrah_lab.offline_dp_bc.validate_phase_progress_runtime_provider --dataset $RUN/contact_relabel_set_phase_progress.npz --output-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/phase_progress_runtime_provider/parity_set4_20260611_2300 --atol 1e-7`

Result:
- status: `passed`; no training and no Isaac rollout was run in this step.
- parity artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/phase_progress_runtime_provider/parity_set4_20260611_2300`
- checked rows: `936`
- max abs feature error: `0.0`
- episode schedules in the accepted set:
  - episode 0: length `240`, phase changes at local steps `[0,22,102]`
  - episode 1: length `240`, phase changes at local steps `[0,22,102]`
  - episode 2: length `226`, phase changes at local steps `[0,10,90]`
  - episode 3: length `230`, phase changes at local steps `[0,15,95]`

Viewer URL:
- parity report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/phase_progress_runtime_provider/parity_set4_20260611_2300/phase_progress_runtime_provider_parity.md`

Analysis:
- The parity result proves the runtime provider can reproduce the 25D training
  features for accepted relabel episodes.
- This is still a deterministic schedule, not a general phase estimator. It is
  appropriate only for the next bounded matched-reset trace; normal-reset
  generalization and RL remain out of scope.

Next:
- Commit/push/deploy this bridge to the C-owned l401 worktree.
- Launch one tiny no-video matched-reset trace using the 25D checkpoint,
  episode 0 schedule, source-joint reset for the corresponding accepted
  relabel rollout, `ACTION_CHUNK_STEPS=1`, and support/policy tracing.
- Inspect metrics/support/policy traces before deciding whether any short video
  is warranted.

## 2026-06-11T23:03:44-07:00 - launch 25D phase-progress matched-reset trace

Goal:
- Run the first closed-loop mechanics trace for the 25D checkpoint only after
  offline provider parity passed. This is no-video, single-env, matched-reset,
  trace-first; no broad eval/RL.

Version Control:
- local implementation commit:
  `f5a02fce81b2373cc29d6d183a186fd7f5147d9d`
- pushed: yes, branch `codex/franka-cube-diffusion-policy-bc`.
- l401 worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- l401 commit:
  `f5a02fce81b2373cc29d6d183a186fd7f5147d9d`
- deployment note:
  remote SSH fetch from `origin` failed with public-key auth, so deployment used
  Git HTTPS fetch from `https://github.com/lihzha/DEXTRAH.git` for the pushed
  agent branch and then detached checkout to the exact commit. No source rsync.

Artifacts staged on l401:
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt`
- phase/progress dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz`
- accepted 21D reset dataset already present:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz`
- source trajectory:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json`

Command / Job:
- job_id: `1028187`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230344`
- command:
  `sbatch --parsable --export=ALL,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230344,NUM_ENVS=1,NUM_STEPS=128,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=32,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,PRINT_INTERVAL=16,DEBUG_POLICY_TRACE_MAX_CALLS=24,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,DEMO_RESET_DATASET=/results/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- expected remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230344`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028187.out`

Acceptance:
- Scheduler completion is not enough.
- Required artifacts: `metrics.json`, `policy_trace.json`,
  `support_trace.json`, `support_trace.csv`, `eval_config.json`.
- Inspect that policy trace obs dim is `25`, phase/progress features follow the
  episode-0 schedule, action values are finite, env closes cleanly, and support
  trace does not show an obvious train/eval feature mismatch.

## 2026-06-11T23:04:30-07:00 - relaunch 25D trace with agent code mount

Result:
- job `1028187` failed before meaningful rollout.
- failure evidence:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028187.out`
  ended with:
  `/isaac-sim/kit/python/bin/python3: can't open file '/code/dextrah_lab/rl_games/eval_franka_cube_dp_policy.py': [Errno 2] No such file or directory`
- root cause:
  the wrapper defaulted `CODE_NFS` to the canonical remote checkout
  `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`, not the C-owned detached
  worktree. The container printed a different code commit
  `378b722a82a42b293b7eea9f27629502cbf44d19`; no policy behavior was evaluated.

Relaunch:
- l401 source check:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  is at `f5a02fce81b2373cc29d6d183a186fd7f5147d9d` and contains
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
- job_id: `1028188`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430`
- changed launch setting:
  `CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- expected remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430`
- expected log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028188.out`

Next:
- Monitor `1028188`; fetch and inspect metrics/traces if it reaches the eval
  wrapper. Do not launch video or broader eval until this trace is understood.

## 2026-06-11T23:18:00-07:00 - inspect 25D phase-progress matched-reset trace 1028188

Goal:
- Inspect the first no-video Isaac trace for the 25D phase/progress official
  DP checkpoint before any video, broader eval, BC scale-up, or RL handoff.

Version Control:
- launched implementation commit:
  `f5a02fce81b2373cc29d6d183a186fd7f5147d9d`
- local source after artifact/report patch: pending commit.
- l401 job code path:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- l401 launch commit:
  `f5a02fce81b2373cc29d6d183a186fd7f5147d9d`

Command / Job:
- job_id: `1028188`
- scheduler state: `COMPLETED`, exit `0:0`, elapsed `00:01:46`,
  node `pool0-00030`.
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430`
- stdout log:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/eval_franka_cube_dp_policy_1028188.out`

Artifacts:
- metrics:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/metrics.json`
- policy trace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/policy_trace.json`
- support trace JSON/CSV:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/support_trace.json`
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/support_trace.csv`
- eval config:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/eval_config.json`
- generated report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/closed_loop_support_report.md`
- support plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/closed_loop_support_trace.png`
- phase/progress plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/closed_loop_phase_progress.png`
- action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/closed_loop_action_components.png`

Result:
- status: `failed closed-loop support gate`; no video was launched.
- 25D runtime bridge mechanics passed the narrow wiring check:
  - `policy_trace.json` has `lowdim_obs_dim=25`.
  - `phase_progress_provider` loaded the expected dataset, episode `0`,
    start step `0`, obs dim `25`, features
    `phase_align_open`, `phase_close_hold`, `phase_lift`,
    `episode_progress`.
  - demo/source reset matched exactly:
    `lowdim_l2_diff_env0=0`, `cube_minus_ee_l2_diff_env0=0`,
    `joint_linf_diff_after_write_env0=0`.
  - history gaps were `[0, 1]`, so the previous cadence bug did not recur.
- behavior metrics:
  - final/window success: `0.0/0.0`.
  - `has_lifted_cube` max: `0`.
  - cube lift max/final: `0.01697/0.0 m`.
  - final gripper width: `0.00859 m`.
  - EE-to-cube min/final: `0.02334/0.18490 m`.
  - finger-center-to-cube min/final: `0.05560/0.17893 m`.
  - support distance start/final: `0.03517/5.55853`.
  - nearest phase counts: `align_open=72`, `close_hold=8`,
    `lift=48`.
- runtime feature schedule did switch as expected:
  - align/open at step `1`, close/hold around step `22`, lift around
    step `102`.
  - Despite this, the nearest-demo support trace stayed/fell back to
    `align_open` for much of the rollout and support distance grew sharply.

Analysis:
- This run rules out the simplest 25D bridge wiring failure: the official DP
  checkpoint consumed 25D observations, the phase/progress provider matched the
  generated NPZ schedule, and the env reset/history plumbing was exact.
- The behavior remains a train/eval-support failure under closed loop. The
  policy begins hard close at step `24`, while the live geometry is already
  drifting out of the support manifold; by the end it is closed but far from
  the cube. This should not be treated as BC/RL readiness.
- Next diagnosis should be bounded and offline/trace-first: compare the 25D
  policy's action predictions on exact dataset windows vs this live trace,
  audit action normalization/sign/timing under the phase-progress checkpoint,
  and check whether the deterministic phase schedule advances faster than live
  contact dynamics. No video, broad eval, DP retrain, or RL launch is justified
  from `1028188`.

Next:
- Commit the report-generator/worklog update.
- Do not launch a video or broad evaluation from this checkpoint.
- If continuing, run a bounded action/phase timing diagnostic from the fetched
  trace and exact dataset windows before any new Isaac job.

## 2026-06-11T23:25:00-07:00 - plan offline 25D action/phase timing diagnostic

Goal:
- Diagnose why the 25D phase/progress checkpoint diverges in closed loop even
  though runtime feature parity and reset/history plumbing passed.

Scope:
- Offline only: load the official Diffusion Policy checkpoint locally, query
  exact 25D dataset windows and selected live trace windows from `1028188`,
  and compare predictions against dataset labels at offsets
  `[-2,-1,0,1,2,4,7]`.
- No Isaac job, no video, no DP training, no RL.

Command / Artifacts:
- script:
  `python -m dextrah_lab.offline_dp_bc.diagnose_dp_action_semantics`
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_train/checkpoints/latest.ckpt`
- dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`
- trace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_trace128_no_video_20260611_230430/policy_trace.json`
- output dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325`

Acceptance:
- Produce CSV/JSON/report and plots for action offsets, per-channel
  prediction-vs-label, and gripper sign behavior.
- Check whether the returned official-DP action aligns with `a[t]` or future
  labels, whether live trace re-query reproduces the executed trace actions,
  and whether phase schedule changes cause premature close/lift relative to
  live support.

## 2026-06-11T23:33:00-07:00 - offline action/phase timing diagnostic result

Command:
- cwd:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- command:
  `PYTHONPATH=$DEX:$DP_ROOT:$PYTHONPATH $VENV -m dextrah_lab.offline_dp_bc.diagnose_dp_action_semantics --checkpoint $RUN/official_dp_train/checkpoints/latest.ckpt --dataset $RUN/contact_relabel_set_phase_progress.npz --output-dir $OUT --diffusion-policy-root $DP_ROOT --device cpu --num-inference-steps 100 --policy-source auto --episode-index 0 --row-selector gripper_open --row-selector gripper_closed --row-selector lift_high --samples-per-selector 8 --trace $TRACE --max-live-records-per-trace 5 --report-all-channels`
- job_id: `n/a` local offline CPU diagnostic.
- output dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325`

Artifacts:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/action_semantics_report.md`
- offset plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/action_semantics_offsets.png`
- gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/gripper_label_vs_prediction.png`
- per-channel plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/per_channel_first_action_scatter.png`
- CSV/JSON:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/action_semantics_rows.csv`
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_set4_trace1028188_20260611_2325/action_semantics_summary.json`

Result:
- status: `failed offline semantics gate`, but the failure is now diagnostic.
- policy source: `ema`; official return start index `1`
  (`oa_step_convention=True`), `n_obs_steps=2`, `n_action_steps=8`,
  `horizon=16`.
- gripper gate: `false`.
  - open sign match: `0.8333`.
  - closed/lift sign match: `0.9444`.
  - threshold: `0.95`.
- exact demo rows:
  - episode start: predicted gripper `0.901`, label `+1`.
  - first close_hold row 22: predicted gripper `0.041`, label `-1`
    (ambiguous/late close at boundary).
  - first lift row 102: predicted gripper `-0.923`, label `-1`.
- live trace rows:
  - live start re-query: predicted gripper `+1`, label `+1`,
    nearest distance `0.0`.
  - live first negative/hard-close rows are nearest align_open rows 18/19
    with labels `+1`, but the re-queried policy predicts closed gripper
    (`-0.893` / `-0.880`) because the runtime phase feature has already
    advanced to close_hold.
  - live nearest distances at those close events are already high
    (`0.804` and `0.886`).

Analysis:
- This does not look like a raw gripper sign flip: exact open and lift rows
  mostly have the correct sign, and the normalizer reports gripper input range
  `[-1, +1]`.
- The concrete failure mode is phase/support timing. The deterministic runtime
  phase schedule follows the dataset clock, but closed-loop robot/cube geometry
  lags and is still nearest to align_open rows when phase_close_hold becomes
  active. The phase-conditioned policy then closes according to phase, not
  according to live contact geometry.
- This explains why 25D offline smokes passed but the matched-reset trace
  failed: offline labels are queried on-manifold; live states after a few steps
  are off-manifold, yet the phase feature advances anyway.

Next:
- Do not run video, broad eval, BC retrain, or RL from this checkpoint.
- Next bounded implementation should test a geometry/contact-gated runtime
  phase provider: keep `phase_align_open=1` until live support/contact geometry
  crosses a close-safe threshold, then advance to close_hold/lift. Validate
  offline logic first, then at most one tiny no-video matched-reset trace.

## 2026-06-12T00:00:00-07:00 - plan video-backed gated phase diagnostic

Goal:
- Honor the artifact preference for videos on the next meaningful closed-loop
  DP diagnostic while keeping the scope bounded and diagnostic-only.

Hypothesis:
- The 25D checkpoint failed because the deterministic dataset-clock phase
  provider advanced to close/lift while live geometry was still align/open.
  A geometry/contact-gated runtime provider should prevent premature phase
  advance. The diagnostic may still fail, but the failure video will show
  policy behavior rather than relabel-controller behavior.

Planned Change:
- Add an opt-in `contact_gated` mode for runtime phase/progress features.
  Default `dataset` mode remains unchanged.
- Gate close/hold until live lowdim geometry is near the cube:
  `||cube_minus_ee||` and gripper width thresholds, with optional dataset-clock
  lower bounds. Then gate lift until the gripper is closed enough.
- Add trace/report fields so `policy_trace.json`, `support_trace.csv`, and
  generated plots show runtime phase switches and gating state.
- Update the l401 wrapper to pass the new options.

Validation:
- Local:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- Local:
  `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- Local:
  `git diff --check`
- Offline sanity:
  instantiate the provider against the 25D NPZ and test feature outputs for
  representative align/close/lift lowdim rows.

Expected Cluster Job:
- One L401 run only, if validation passes.
- `NUM_ENVS=1`, short horizon, matched source-joint reset, `ACTION_CHUNK_STEPS=1`,
  support/policy tracing, `CAPTURE_VIDEO=True`, short video/contact sheet.
- No broad eval, no BC training, no RL.

Acceptance:
- Fetch and inspect metrics, support trace, policy trace, labeled video/contact
  sheet, and plots before declaring anything.
- If it fails, record whether the failure is phase-gating, action semantics,
  history/normalizer, or policy support coverage.

## 2026-06-12T00:08:00-07:00 - launch contact-gated 25D DP video trace

Goal:
- Produce the next meaningful closed-loop DP diagnostic with video, metrics,
  policy trace, and support trace, after adding the contact-gated phase provider.

Version Control:
- implementation_commit:
  `223750e2b091fa4d9914d14f97811e0dd44de8e7`
- local branch: `codex/franka-cube-diffusion-policy-bc`
- remote l401 worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote commit: `223750e2b091fa4d9914d14f97811e0dd44de8e7`
- push/pull: pushed to GitHub and fetched via HTTPS into the C-owned detached
  l401 worktree.

Command / Job:
- job_id: `1028199`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008,NUM_ENVS=1,NUM_STEPS=128,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=32,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=128,VIDEO_NAME_PREFIX=franka-cube-dp-phaseprogress-contactgated,PRINT_INTERVAL=16,DEBUG_POLICY_TRACE_MAX_CALLS=48,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,DEMO_RESET_DATASET=/results/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- stdout log:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028199.out`

Acceptance:
- Must fetch and inspect:
  `metrics.json`, `policy_trace.json`, `support_trace.json/csv`,
  `eval_config.json`, MP4 video, contact sheet, report, plots.
- This is still a no-learning diagnostic; even a visually useful failure video
  is not BC/RL scale-up evidence.

## 2026-06-12T00:35:00-07:00 - result contact-gated 25D DP video trace

Job:
- job_id: `1028199`
- status: completed `0:0`
- run:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- stdout:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/eval_franka_cube_dp_policy_1028199.out`

Viewer artifacts:
- labeled DP policy MP4:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/videos/franka-cube-dp-phaseprogress-contactgated-labeled-step-0.mp4`
- contact sheet:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/dp_contactgated_contact_sheet.jpg`
- support report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/closed_loop_support_report.md`
- phase/progress plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/closed_loop_phase_progress.png`
- support trace plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/closed_loop_support_trace.png`

Metrics:
- `final_success_rate=0.0`, `window_success_rate=0.0`
- cube lift height `max=0.01697 m`, `final=0.0 m`
- final gripper width `0.03655 m`
- EE-to-cube distance `min=0.02031 m`, `final=0.11325 m`
- finger-center-to-cube distance `min=0.05021 m`, `final=0.12189 m`
- support distance `start=0.03517`, `final=3.449`
- action gripper range `[-0.866, 1.0]`

Trace/video interpretation:
- The runtime provider stayed in `align_open` for the whole 128-step rollout;
  it did not advance to close/lift because live support geometry never passed
  the close gate.
- Compared with the prior deterministic dataset-clock trace, this fixed the
  premature phase switch mechanism but did not produce success. The policy
  nudges the cube, loses local support, and ends away from the cube with no
  stable lift.
- The artifact is an actual DP-policy behavior video, not a contact-relabel
  controller video.

Offline action-semantics follow-up:
- output dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_contactgated_trace1028199_20260612_0022`
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_contactgated_trace1028199_20260612_0022/action_semantics_report.md`
- gripper plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_contactgated_trace1028199_20260612_0022/gripper_label_vs_prediction.png`
- per-channel plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/action_semantics/phaseprogress_contactgated_trace1028199_20260612_0022/per_channel_first_action_scatter.png`
- verdict: `gripper_gate_pass=true`, open sign match `1.0`,
  closed/lift sign match `0.95`. This rules out a raw gripper sign flip for
  this failure. The remaining issue is align/open closed-loop support drift
  and insufficient contact/lift geometry before the gated phase can advance.

Decision:
- Do not launch broad DP eval, DP fine-tune, or RL from this checkpoint.
- Next bounded work should target align/open support retention or a more
  train/eval-consistent phase/support representation before any scale-up.
- Active job check after fetch/report generation: no C eval job active in
  `squeue`.

## 2026-06-12T00:52:00-07:00 - plan align/open support drift audit

Goal:
- Diagnose the remaining 25D closed-loop failure before any retrain, broad
  eval, or RL. The target failure mode is align/open support drift before
  contact-gated phase advancement.

Hypothesis:
- The policy is no longer closing from a bad phase clock, but its open/alignment
  actions may still be off-support because of one of:
  action magnitude/normalization, positional convention, history/state mismatch,
  or insufficient corrective align/open data.

Plan:
- Start offline from the existing video-backed DP trace `1028199`.
- Build a compact report/plot artifact that compares live align/open windows
  against nearest accepted relabel dataset windows:
  live vs nearest lowdim deltas, z-scores, cube-minus-EE/finger/EE geometry,
  predicted action vs dataset action labels at nearest row and future offsets,
  action direction relative to cube, gripper command, phase/progress, and
  history step gaps.
- Reuse the existing labeled MP4/contact sheet as the visual behavior artifact;
  launch no new Isaac job unless the offline audit cannot distinguish action
  semantics from support coverage.

Validation:
- Local syntax:
  `python3 -m py_compile <new/changed diagnostic script>`
- Local report generation against:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008`
- Artifact inspection with `viz-open`.

Acceptance:
- Produce `report.md`, JSON/CSV, and at least one compact plot.
- Explicitly classify the evidence among action normalization/magnitude,
  positional convention, history/state mismatch, or insufficient corrective
  data.
- Do not launch DP fine-tune, broad eval, or RL.

## 2026-06-12T01:12:00-07:00 - result align/open support drift audit

Goal:
- Diagnose why the 25D contact-gated DP policy drifts during align/open before
  allowing close/lift.

Change:
- Added a bounded offline diagnostic:
  `dextrah_lab/offline_dp_bc/diagnose_align_open_support_drift.py`.
- It compares `support_trace.json`/`policy_trace.json` from the video-backed
  run against the accepted 25D relabel dataset. It writes a report, CSV, JSON,
  support/action plots, and a per-channel action scatter.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- base_commit: `6080f73908c726180452916617338dddaa9a3693`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/diagnose_align_open_support_drift.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/diagnose_align_open_support_drift.py`
  passed.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` passed.

Command:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.diagnose_align_open_support_drift --dataset /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz --run-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008 --output-dir /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift --video /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/videos/franka-cube-dp-phaseprogress-contactgated-labeled-step-0.mp4 --contact-sheet /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/dp_contactgated_contact_sheet.jpg`

Artifacts:
- report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift/align_open_support_drift_report.md`
- support/action plot:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift/align_open_support_drift.png`
- per-channel action scatter:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift/align_open_action_scatter.png`
- CSV:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift/align_open_support_drift_rows.csv`
- JSON:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/align_open_support_drift/align_open_support_drift_summary.json`
- existing behavior video used as visual context:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_contactgated_video128_20260612_0008/videos/franka-cube-dp-phaseprogress-contactgated-labeled-step-0.mp4`

Result:
- runtime phase counts: `{'align_open': 128}`.
- nearest dataset phase counts: `{'align_open': 45, 'close_hold': 14, 'lift': 69}`.
- nearest support distance grows `0.0352 -> 3.4494`.
- median command cosine toward live cube-minus-EE: `0.2011`.
- median nearest-label cosine toward live cube-minus-EE: `0.8792`.
- median actual EE-delta cosine toward live cube-minus-EE: `0.0911`.
- median command xyz norm: `0.0372 m`.
- median nearest-label xyz norm: `0.0149 m`.
- median actual/command EE realization ratio: `0.0670`.
- step 1 already shows a bad pose command on a near-exact state:
  command cosine `-0.3823` while nearest label cosine is `0.9207`.

Analysis:
- History/state mismatch: unlikely. Support and policy history gaps are `[0,1]`.
- Raw gripper sign: unlikely. The separate official-DP action semantics gate
  passed for this checkpoint.
- Action magnitude too small: unlikely. The DP command norm is larger than the
  nearest-label norm on median.
- Pose action convention/prediction: likely. The relabel dataset actions point
  toward the cube, but the traced DP commands are weakly aligned or sometimes
  anti-aligned; this appears even at the initial near-exact state.
- Controller realization: possible secondary effect. Actual EE motion is much
  smaller than command, but this follows from bad/off-support commands rather
  than proving the controller bridge is the primary bug.
- Corrective support coverage: likely. The four-episode set has little
  recovery coverage after the cube/hand geometry is nudged out of the
  align-open path.

Decision:
- No DP fine-tune, broad eval, or RL launch.
- The next useful bounded gate should improve the pose-channel offline
  action-semantics check for align/open rows before another Isaac run:
  either deterministic/less stochastic DP sampling for exact align rows, a
  stronger pose-channel loss/gate on the current set, or a tiny recovery
  relabel set with an offline pose-action pass. A new video run should wait
  until one of those gates passes.

## 2026-06-12T01:30:00-07:00 - plan eval-only pose action projection diagnostic

Goal:
- Test one bounded correction strategy for pose-channel support drift before
  any retrain, broad eval, or RL.

Hypothesis:
- If replacing only the align/open pose channels with the nearest accepted
  relabel dataset action stabilizes contact/lift under the same official-DP
  checkpoint, then the blocker is the learned pose output/support coverage,
  not the observation bridge, gripper convention, or action magnitude.

Planned Change:
- Add an opt-in eval-only action correction mode to
  `eval_franka_cube_dp_policy.py` and the l401 wrapper.
- Mode: `nearest_label_align_pose`.
  - active only when runtime phase is `align_open`;
  - uses the already supplied support dataset nearest row;
  - replaces or blends only action dims `0:6` with the nearest dataset label;
  - leaves the DP gripper command unchanged;
  - records correction metadata in `support_trace.json/csv`.
- Default remains disabled.

Validation:
- local `py_compile` for touched Python files.
- local `bash -n` for `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.
- local offline sanity for the correction helper against the 1028199 trace.
- `git diff --check`.

Cluster Gate:
- If local checks pass, commit/push/deploy exact commit to the C-owned l401
  worktree and launch one bounded matched-reset video trace:
  `NUM_ENVS=1`, `NUM_STEPS=128`, `ACTION_CHUNK_STEPS=1`,
  `PHASE_PROGRESS_MODE=contact_gated`, `ACTION_CORRECTION_MODE=nearest_label_align_pose`,
  `CAPTURE_VIDEO=True`.

Acceptance:
- Fetch and inspect metrics, support trace, policy trace, labeled MP4/contact
  sheet, and plots.
- Passing the diagnostic means reduced support drift and coherent contact/lift
  relative to the uncorrected run; it is not a DP/BC/RL readiness claim.
- If it fails, record whether nearest-label correction cannot overcome
  controller/contact dynamics or whether the correction is too narrow.

## 2026-06-11T23:35:00-07:00 - launch eval-only align pose correction video

Goal:
- Run the bounded correction diagnostic from the previous plan with a short
  labeled video and full traces.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `d0af26f4eeb3a5a7961832420d0b5b1210f6ab70`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote commit: `d0af26f4eeb3a5a7961832420d0b5b1210f6ab70`
- changed_files:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/diagnose_align_open_support_drift.py`
  passed.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` passed.
- `git diff --check` passed.

Command / Job:
- job_id: `1028230`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527,NUM_ENVS=1,NUM_STEPS=128,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=32,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=128,VIDEO_NAME_PREFIX=franka-cube-dp-phaseprogress-aligncorr,PRINT_INTERVAL=16,DEBUG_POLICY_TRACE_MAX_CALLS=48,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,ACTION_CORRECTION_MODE=nearest_label_align_pose,ACTION_CORRECTION_BLEND=1.0,DEMO_RESET_DATASET=/results/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527`
- stdout:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028230.out`

Expected artifacts:
- `metrics.json`, `eval_config.json`, `policy_trace.json`,
  `support_trace.json/csv`, MP4 video.
- After fetch: labeled MP4/contact sheet, closed-loop report/plots, and
  updated align-open drift audit.

Safety:
- This is an eval-only action projection diagnostic. It is not a trained
  official-DP policy result and does not authorize DP fine-tune, broad eval, or
  RL.

## 2026-06-11T23:41:30-07:00 - result eval-only align pose correction video

Goal:
- Inspect job `1028230` and decide whether nearest-label align/open pose
  projection is a viable bounded correction gate for the 25D official-DP
  support-drift failure.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `d0af26f4eeb3a5a7961832420d0b5b1210f6ab70`
- official Diffusion Policy source:
  `real-stanford/diffusion_policy` @
  `5ba07ac6661db573af695b419a7947ecb704690f`
- remote commit: `d0af26f4eeb3a5a7961832420d0b5b1210f6ab70`

Result:
- status: `failed gate`
- job_id: `1028230`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527`
- fetched artifacts: `metrics.json`, `eval_config.json`,
  `policy_trace.json`, `support_trace.json/csv`, stdout log, MP4 video.
- generated artifacts:
  - `align_pose_correction_gate_report.md`
  - `dp_aligncorr_contact_sheet.jpg`
  - `closed_loop_support_report.md`
  - `closed_loop_support_trace.png`
  - `closed_loop_action_components.png`
  - `closed_loop_phase_progress.png`
  - `align_open_support_drift/align_open_support_drift_report.md`
  - `align_open_support_drift/align_open_support_drift.png`
  - `align_open_support_drift/align_open_action_scatter.png`

Viewer URLs:
- gate report:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/align_pose_correction_gate_report.md
- video:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/videos/franka-cube-dp-phaseprogress-aligncorr-step-0.mp4
- contact sheet:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/dp_aligncorr_contact_sheet.jpg
- support trace plot:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/closed_loop_support_trace.png
- action plot:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/closed_loop_action_components.png
- align/open drift plot:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_aligncorr_video128_20260611_233527/align_open_support_drift/align_open_support_drift.png

Metrics:
- correction mode/blend: `nearest_label_align_pose` / `1.0`
- action correction applied: `122/128` support trace records.
- success/window success: `0.0 / 0.0`.
- cube lift max/final: `0.016865 / 0.0 m`.
- EE-to-cube min/final: `0.007137 / 0.014828 m`.
- finger-center-to-cube min/final: `0.039348 / 0.039525 m`.
- gripper width min/final: `0.060310 / 0.067237 m`.
- nearest support distance start/final: `0.0 -> 1.068283`.
- runtime phase counts from drift audit: `align_open=122`, `close_hold=6`.
- nearest support phase counts: `align_open=21`, `close_hold=107`.
- median command cosine toward live cube-minus-EE: `-0.0956`.
- median nearest-label cosine toward live cube-minus-EE: `0.0625`.
- median actual EE-delta cosine toward live cube-minus-EE: `-0.3237`.
- median actual/command EE realization ratio: `0.0081`.

Analysis:
- The eval-only pose projection changed the failure mode but did not solve the
  gate. The video/contact sheet now shows the hand visually near the cube
  instead of drifting far away, and final EE-to-cube is small.
- There is still no grasp/lift. The cube lift peak is only an initial reset
  bounce and returns to zero; final success and window success remain zero.
- The support distance still grows from the exact support row to about `1.07`.
  The nearest-support phase becomes mostly `close_hold`, while runtime phase
  features stay mostly `align_open`.
- The gripper/phase stream is incoherent relative to the projected pose stream:
  the gripper closes briefly around steps `23-24` but later remains too open
  for retention (`0.067 m` final), and phase progression does not advance to a
  durable lift behavior.
- This rejects the hypothesis that pose-channel projection alone is enough.
  The next useful fix is a coupled support/controller design, such as a tiny
  recovery/contact-retention relabel set or a diagnostic that couples nearest
  pose correction with a validated gripper/phase gate. It does not justify DP
  fine-tune, broad eval, or RL.

Decision:
- Do not launch DP fine-tune, broad eval, or RL from this checkpoint.
- Keep official-DP provenance and the eval-only correction code as a diagnostic
  tool only.

## 2026-06-12T00:02:00-07:00 - plan coherent nearest-label action/phase diagnostic

Goal:
- Run one more bounded diagnostic before any training: test whether the
  accepted relabel set can execute coherently when pose, gripper, and phase are
  all taken from the same nearest support row instead of mixing corrected pose
  with the DP gripper/runtime phase stream.

Hypothesis:
- If a coherent nearest-label correction passes or reaches lift, the current
  blocker is the official-DP output stream and phase/gripper coordination, not
  the DEXTRAH bridge/controller or the accepted relabel data.
- If it still fails, the accepted four-episode set lacks local closed-loop
  recovery/retention support even under an oracle-like nearest-label controller,
  so DP training/eval remains blocked pending relabel/controller redesign.

Planned Change:
- Add an opt-in eval-only `action_correction_mode` to
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
- New mode should:
  - use the existing support dataset and nearest support lookup;
  - replace or blend all seven action dims with the nearest support label;
  - optionally write the nearest row's 25D phase/progress features into the
    lowdim observation before official-DP prediction for logging/coherence;
  - record correction metadata in `support_trace.json/csv`.
- Keep defaults unchanged and retain official Diffusion Policy checkpoint
  loading/provenance. This remains a no-learning diagnostic.

Validation:
- local `py_compile` for touched Python files.
- local `bash -n` for the l401 wrapper if wrapper choices change.
- `git diff --check`.
- Commit/push/deploy exact commit to the C-owned l401 worktree before launch.

Cluster Gate:
- One bounded matched source-joint video trace only:
  `NUM_ENVS=1`, `NUM_STEPS=160`, `ACTION_CHUNK_STEPS=1`,
  `PHASE_PROGRESS_MODE=contact_gated`, `ACTION_CORRECTION_MODE=<new coherent mode>`,
  `CAPTURE_VIDEO=True`.

Acceptance:
- Fetch and inspect metrics, support trace, policy trace, MP4/contact sheet,
  and plots.
- This diagnostic can justify only a next small supervised/eval gate, not broad
  DP training or RL.

Implementation:
- Added `ACTION_CORRECTION_MODE=nearest_label_full_action`.
- The new mode uses the existing nearest-support lookup over the accepted
  relabel dataset, then blends/replaces all seven action dimensions with that
  label so pose and gripper come from the same row.
- Added trace fields for full-action L2 before/after correction and
  gripper before/after/label values.

Local Validation:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/offline_dp_bc/diagnose_align_open_support_drift.py dextrah_lab/offline_dp_bc/make_closed_loop_support_report.py`
  passed.
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh` passed.
- `git diff --check` passed.

## 2026-06-11T23:47:12-07:00 - launch coherent nearest-label full-action correction video

Goal:
- Test the coherent eval-only correction mode with pose and gripper actions
  taken from the same nearest accepted relabel row.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `5b37dc2444813026ef62a308b6000c5683477210`
- local branch: `codex/franka-cube-diffusion-policy-bc`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote commit: `5b37dc2444813026ef62a308b6000c5683477210`
- remote update note: l401 SSH fetch from GitHub failed with
  `Permission denied (publickey)`, so this run used a one-off HTTPS fetch from
  `https://github.com/lihzha/DEXTRAH.git` to materialize the exact pushed
  commit.

Command / Job:
- job_id: `1028239`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712,NUM_ENVS=1,NUM_STEPS=220,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=32,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=220,VIDEO_NAME_PREFIX=franka-cube-dp-phaseprogress-fullcorr,PRINT_INTERVAL=20,DEBUG_POLICY_TRACE_MAX_CALLS=64,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,ACTION_CORRECTION_MODE=nearest_label_full_action,ACTION_CORRECTION_BLEND=1.0,DEMO_RESET_DATASET=/results/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712`
- stdout:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028239.out`

Expected artifacts:
- `metrics.json`, `eval_config.json`, `policy_trace.json`,
  `support_trace.json/csv`, MP4 video.
- After fetch: contact sheet, closed-loop report/plots, align-open/action
  coherence diagnostic, and explicit gate report.

Safety:
- This is still a no-learning eval-only oracle/correction diagnostic. It does
  not authorize DP fine-tune, broad eval, or RL.

## 2026-06-11T23:55:00-07:00 - result coherent nearest-label full-action correction video

Goal:
- Inspect job `1028239` and decide whether coherent nearest-label pose+gripper
  correction closes the support-drift gap enough to justify any next DP step.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `5b37dc2444813026ef62a308b6000c5683477210`
- official Diffusion Policy source:
  `real-stanford/diffusion_policy` @
  `5ba07ac6661db573af695b419a7947ecb704690f`
- remote commit: `5b37dc2444813026ef62a308b6000c5683477210`

Result:
- status: `partial pass for controller/relabel support; failed task/policy readiness`
- job_id: `1028239`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712`
- fetched artifacts: `metrics.json`, `eval_config.json`,
  `policy_trace.json`, `support_trace.json/csv`, stdout log, MP4 video.
- generated artifacts:
  - `coherent_full_action_gate_report.md`
  - `dp_fullcorr_contact_sheet.jpg`
  - `closed_loop_support_report.md`
  - `closed_loop_support_trace.png`
  - `closed_loop_action_components.png`
  - `closed_loop_phase_progress.png`
  - `align_open_support_drift/align_open_support_drift_report.md`
  - `align_open_support_drift/align_open_support_drift.png`
  - `align_open_support_drift/align_open_action_scatter.png`

Viewer URLs:
- gate report:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712/coherent_full_action_gate_report.md
- video:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712/videos/franka-cube-dp-phaseprogress-fullcorr-step-0.mp4
- contact sheet:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712/dp_fullcorr_contact_sheet.jpg
- support trace plot:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video220_20260611_234712/closed_loop_support_trace.png

Metrics:
- correction mode/blend: `nearest_label_full_action` / `1.0`.
- action correction applied: `220/220` support trace records.
- support distance start/final: `0.0 / 0.0`.
- nearest phase counts: `align_open=21`, `close_hold=80`, `lift=119`.
- correction nearest phase counts: `align_open=22`, `close_hold=80`,
  `lift=118`.
- first negative/hard close label step: `23 / 23`.
- first correction lift phase step: `103`.
- first cube lift over `0.05 m`: step `177`.
- first cube lift over `0.10 m`: step `214`.
- success/window success: `0.0 / 0.0`.
- cube lift max/final: `0.108491 / 0.108491 m`.
- EE-to-cube min/final: `0.006990 / 0.007417 m`.
- finger-center-to-cube min/final: `0.051527 / 0.051879 m`.
- gripper width min/final: `0.051343 / 0.052106 m`.

Analysis:
- This rejects a pure controller/action-scale blocker for the accepted relabel
  set. When pose and gripper come coherently from nearest accepted labels, the
  rollout no longer drifts away and does lift the cube.
- It also explains the previous pose-only correction failure: leaving the DP
  gripper/runtime phase stream untouched creates an incoherent state/action
  mix, while nearest-label full actions stay on support.
- The hard task gate still fails at 220 steps. Lift is still rising but remains
  below the task success threshold (`0.108 m < 0.12 m`), and gripper width is
  still about `5.2 cm`.
- This is an oracle/eval-only action replacement, not a trained policy result.
  It does not prove the official DP checkpoint can emit the coherent actions.

Decision:
- No DP fine-tune, broad eval, or RL from this artifact.
- The next bounded choice is either:
  - a 260-step no-learning full-action oracle check to separate horizon
    sensitivity from relabel/controller limits; or
  - an offline official-DP pose+gripper coherence gate that directly penalizes
    the observed mismatch before any more Isaac eval.

## 2026-06-11T23:54:46-07:00 - plan 260-step full-action oracle horizon check

Goal:
- Run one bounded no-learning diagnostic to determine whether the coherent
  nearest-label full-action oracle crosses the hard lift/success threshold with
  a slightly longer horizon.

Hypothesis:
- The 220-step run was still lifting at the final frame (`0.10849 m`), so a
  260-step oracle run may cross the `0.12 m` success threshold. If it does, the
  accepted relabel/controller path is horizon-sensitive but viable under
  oracle coherent actions. If it does not, the current relabel support still
  needs lift/hold/gripper redesign before any DP training.

Change:
- No source-code change from commit
  `f935ebde8385767941ebc1654cfa257eb5a44387`.
- Use `ACTION_CORRECTION_MODE=nearest_label_full_action`,
  `NUM_STEPS=260`, `VIDEO_LENGTH=260`, and otherwise match job `1028239`.

Validation:
- Existing local validation for commit `5b37dc2` covered the code path:
  `py_compile`, `bash -n`, and `git diff --check` passed.
- Current worktree is clean at `f935ebde8385767941ebc1654cfa257eb5a44387`.

Acceptance:
- Fetch and inspect metrics, support trace, policy trace, MP4/contact sheet,
  and plots.
- This is still an oracle/no-learning diagnostic. Even if it reaches success,
  it does not authorize DP fine-tune, broad eval, or RL without a separate
  official-DP output-coherence gate.

## 2026-06-11T23:55:28-07:00 - launch 260-step full-action oracle horizon check

Goal:
- Run the bounded 260-step horizon check from the previous plan.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `f935ebde8385767941ebc1654cfa257eb5a44387`
- local branch: `codex/franka-cube-diffusion-policy-bc`
- remote worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote commit: `f935ebde8385767941ebc1654cfa257eb5a44387`
- remote update note: used HTTPS fetch from
  `https://github.com/lihzha/DEXTRAH.git` because l401 SSH fetch still lacks
  the GitHub key.

Command / Job:
- job_id: `1028246`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528,NUM_ENVS=1,NUM_STEPS=260,NUM_INFERENCE_STEPS=100,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=32,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=260,VIDEO_NAME_PREFIX=franka-cube-dp-phaseprogress-fullcorr260,PRINT_INTERVAL=20,DEBUG_POLICY_TRACE_MAX_CALLS=80,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/contact_relabel_lrcentering_a075_set4_phaseprogress_20260611_224001/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,ACTION_CORRECTION_MODE=nearest_label_full_action,ACTION_CORRECTION_BLEND=1.0,DEMO_RESET_DATASET=/results/contact_relabel_sets/franka_cube_contact_relabel_lrcentering_ep8_16_24_30_a0p75_20260611_2224/contact_relabel_set_accepted.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json,DEMO_RESET_SOURCE_FRAME=260,DEMO_RESET_JOINT_BLEND_ALPHA=0.75,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528`
- stdout:
  `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_franka_cube_dp_policy_1028246.out`

Expected artifacts:
- `metrics.json`, `eval_config.json`, `policy_trace.json`,
  `support_trace.json/csv`, MP4 video.
- After fetch: contact sheet, closed-loop report/plots, align-open/action
  coherence diagnostic, and explicit horizon gate report.

Safety:
- This is a no-learning oracle correction diagnostic only. It does not
  authorize DP fine-tune, broad eval, or RL.

## 2026-06-12T00:02:00-07:00 - result 260-step full-action oracle horizon check

Goal:
- Inspect job `1028246` and decide whether the coherent nearest-label
  full-action oracle crosses the hard success threshold when allowed 260
  env steps.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: `f935ebde8385767941ebc1654cfa257eb5a44387`
- official Diffusion Policy source:
  `real-stanford/diffusion_policy` @
  `5ba07ac6661db573af695b419a7947ecb704690f`
- remote commit: `f935ebde8385767941ebc1654cfa257eb5a44387`

Result:
- status: `bounded oracle pass; not policy readiness`
- job_id: `1028246`
- run_name:
  `franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528`
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528`
- fetched artifacts: `metrics.json`, `eval_config.json`,
  `policy_trace.json`, `support_trace.json/csv`, stdout log, MP4 video.
- generated artifacts:
  - `full_action_oracle_horizon260_report.md`
  - `dp_fullcorr260_contact_sheet.jpg`
  - `closed_loop_support_report.md`
  - `closed_loop_support_trace.png`
  - `closed_loop_action_components.png`
  - `closed_loop_phase_progress.png`
  - `align_open_support_drift/align_open_support_drift_report.md`
  - `align_open_support_drift/align_open_support_drift.png`
  - `align_open_support_drift/align_open_action_scatter.png`

Viewer URLs:
- horizon report:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/full_action_oracle_horizon260_report.md
- video:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/videos/franka-cube-dp-phaseprogress-fullcorr260-step-0.mp4
- contact sheet:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/dp_fullcorr260_contact_sheet.jpg
- support trace plot:
  http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_ep0_fullcorr_video260_20260611_235528/closed_loop_support_trace.png

Metrics:
- correction mode/blend: `nearest_label_full_action` / `1.0`.
- action correction applied: `260/260` support trace records.
- success/window success: `1.0 / 1.0`.
- cube lift max/final: `0.164543 / 0.164543 m`.
- EE-to-cube min/final: `0.006990 / 0.007434 m`.
- finger-center-to-cube min/final: `0.051527 / 0.051892 m`.
- gripper width min/final: `0.051343 / 0.051849 m`.
- first close label step: `23`.
- first lift phase label step: `103`.
- first cube lift over `0.05 / 0.10 / 0.12 m`: `177 / 214 / 229`.
- first `has_lifted_cube` and `in_success_region`: step `229`.
- nearest phase counts: `align_open=21`, `close_hold=80`, `lift=159`.
- final support distance: `0.3302`, expected because the 260-step rollout
  extends beyond the 240-row relabel episode.

Analysis:
- Extending the coherent oracle correction from 220 to 260 steps separates
  horizon sensitivity from controller/relabel viability: 220 ended below
  threshold, while 260 crosses and retains success under the timeout override.
- This validates the accepted relabel/controller path for the matched
  source-joint alpha0.75 reset and horizon.
- It does not validate the official DP checkpoint. The checkpoint was loaded
  and traced for provenance, but executed actions were still nearest-label
  oracle replacements.
- Policy-facing blocker remains: official DP must learn/emit coherent
  pose+gripper+phase actions, especially the coupled lift/close stream, before
  any Isaac closed-loop policy eval or RL handoff.

Decision:
- No DP fine-tune, broad eval, or RL from this artifact alone.
- Next bounded work should be offline official-DP pose+gripper coherence:
  compare checkpoint outputs to these oracle labels over the accepted relabel
  windows and adjust the supervised gate/loss/data only if that offline gate
  explains how to make the checkpoint emit the coupled actions.

## 2026-06-12T00:05:06-07:00 - plan offline pose+gripper+phase coherence gate

Goal:
- Run the bounded next diagnostic requested by the orchestrator: compare the
  official Diffusion Policy checkpoint against the successful oracle/relabel
  labels over accepted phase-progress windows, without any DP fine-tune,
  Isaac closed-loop eval, broad training, or RL.

Hypothesis:
- The 260-step nearest-label full-action oracle succeeds because pose,
  gripper, and phase/progress labels are coherent. The official DP checkpoint
  may still fail closed-loop because its pose channels do not align with the
  same phase-conditioned labels even when gripper sign is mostly correct.

Planned Change:
- Add a small offline report tool under
  `dextrah_lab/offline_dp_bc/` that loads the official
  `real-stanford/diffusion_policy` checkpoint, samples dense accepted relabel
  windows by episode/phase, queries `policy.predict_action`, and writes:
  - per-row CSV of label/predicted first action, temporal offset, phase
    features, pose cosine/norm ratio, and gripper correctness;
  - per-phase JSON/CSV summary;
  - plots for pose cosine, gripper sign, action scatter, and phase timeline;
  - markdown verdict that explicitly labels the previous full-action run as an
    oracle/no-learning action replacement.

Validation:
- Local only:
  `python3 -m py_compile dextrah_lab/offline_dp_bc/<new_script>.py`
  and `git diff --check`.
- Diagnostic command will use:
  - dataset:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz`
  - checkpoint:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_train/checkpoints/latest.ckpt`
  - official DP root:
    `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy`

Acceptance:
- Produce viewer-ready report/plots via `viz-open`.
- Gate remains offline only. If the checkpoint is incoherent, stop before
  Isaac eval/RL and document the policy-output blocker.

## 2026-06-12T00:50:18-07:00 - exhaustive offline coherence gate

Goal:
- Replace the sampled action-semantics report with an all-window offline gate
  over the latest 25D phase/progress checkpoint and accepted relabel dataset.

Hypothesis:
- If the DP checkpoint is policy-ready, querying it on every dataset history
  should return first actions aligned with label `a[t]`, with coherent pose
  direction/norm, high gripper sign match, and best temporal offset 0 across
  `align_open`, `close_hold`, and `lift`.

Change:
- Added `dextrah_lab/offline_dp_bc/diagnose_dp_offline_coherence.py`.
- The script loads the official DP checkpoint, scores all rows, writes
  per-row CSV plus per-phase CSV/JSON/Markdown summaries, and stays offline.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cff80096de7037c78b7e6e12b60c0f371a43f9d4`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/diagnose_dp_offline_coherence.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: n/a, local offline diagnostic only

Command / Job:
- command:
  `PYTHONPATH=$DP:$DEX CUDA_VISIBLE_DEVICES=0 $VENV -m dextrah_lab.offline_dp_bc.diagnose_dp_offline_coherence --checkpoint $EXT/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/official_dp_train/checkpoints/latest.ckpt --dataset $EXT/artifacts/official_dp_contact_relabel_smoke/contact_relabel_lrcentering_a075_set4_phaseprogress_official_dp_smoke_20260611_224001/contact_relabel_set_phase_progress.npz --output-dir $EXT/artifacts/offline_coherence/phaseprogress_allwindows_20260612_005018_gatefix --diffusion-policy-root $DP --device cuda:0 --num-inference-steps 100 --batch-size 64 --policy-source auto --seed 42`
- job_id: n/a local GPU inference
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/offline_coherence/phaseprogress_allwindows_20260612_005018_gatefix`
- artifacts:
  - `offline_coherence_report.md`
  - `offline_coherence_phase_summary.csv`
  - `offline_coherence_rows.csv`
  - `offline_coherence_summary.json`

Result:
- status: failed offline policy-readiness gate
- rows scored: `936`
- overall best offset 0 fraction: `0.0288`
- overall gripper sign match: `0.9947`
- overall pose cosine mean: `0.3228`
- lift pose cosine mean: `0.1000`
- lift best offsets: `-2=388`, `0=4`, `7=117`

Analysis:
- The checkpoint I/O is internally coherent, and gripper sign is mostly
  correct. The failure is policy action coherence: predictions generally do
  not align with current-row labels, and lift pose direction is often wrong.
- This explains why closed-loop DP support drifts while full-action nearest
  label replacement can succeed: the relabel/controller path is viable, but
  the learned denoising policy has not fit coupled pose+gripper+phase actions.

Next:
- Overfit a single accepted phase/progress trajectory locally with the same
  official DP architecture. If one-trajectory overfit cannot pass the same
  offline gate, debug training/normalization/model sampling before any Isaac
  eval or RL handoff.

## 2026-06-12T00:58:13-07:00 - no-EMA overfit sanity checks

Goal:
- Test whether the official Diffusion Policy architecture and DEXTRAH lowdim
  I/O can actually fit the accepted CuRobo/oracle labels when optimization
  pressure is sufficient.

Hypothesis:
- If one-demo and four-demo no-EMA overfits pass dense offline coherence, the
  major remaining issue is not observation/action dimensions, normalization,
  action sign, or `pred_action_steps_only`; it is checkpoint quality and then
  closed-loop simulator distribution shift.

Change:
- Created an explicit one-episode dataset from episode 0:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_one_traj_overfit/phaseprogress_ep0_noema_20260612_005153/contact_relabel_set_phase_progress_ep0.npz`.
- Trained no-EMA official DP overfits with the same 25D phase/progress obs,
  7D relative EE+gripper actions, `horizon=16`, `n_obs_steps=2`,
  `n_action_steps=8`, and `oa_step_convention=true`.
- Reused `diagnose_dp_offline_coherence.py` on every available row.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `cff80096de7037c78b7e6e12b60c0f371a43f9d4`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/diagnose_dp_offline_coherence.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`
- remote_commit/status: n/a, local training and offline diagnostics

Command / Job:
- one-demo train run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_one_traj_overfit/phaseprogress_ep0_noema_20260612_005153`
- four-demo train run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_set4_overfit/phaseprogress_set4_noema_20260612_005448`
- coherence command template:
  `PYTHONPATH=$DP:$DEX CUDA_VISIBLE_DEVICES=0 $VENV -m dextrah_lab.offline_dp_bc.diagnose_dp_offline_coherence --checkpoint <run>/official_dp_train/checkpoints/latest.ckpt --dataset <dataset>.npz --output-dir <run>/offline_coherence_latest_gatefix --diffusion-policy-root $DP --device cuda:0 --num-inference-steps 100 --batch-size 64 --policy-source auto --seed 42`
- job_id: n/a local GPU training/inference

Result:
- status: passed offline overfit sanity checks
- one-demo final train metrics: epoch `299`, global_step `1199`,
  `train_action_mse_error=0.0018`, `train_loss=0.03862`
- one-demo coherence: pass over `240` rows; all-phase pose cosine mean
  `0.997`, gripper sign `1.0`, MSE@0 all `0.00273`
- four-demo final train metrics: epoch `299`, global_step `4499`,
  `train_action_mse_error=0.00008`, `train_loss=0.00986`
- four-demo coherence: pass over `936` rows; all-phase pose cosine mean
  `0.9979`, pose norm median `0.9961`, gripper sign `1.0`,
  MSE@0 all `0.00150`, max pose first-action MAE `0.0118`
- four-demo align/open is also coherent: count `69`, offset0 fraction
  `0.580`, pose cosine mean `0.9962`, gripper sign `1.0`,
  MSE@0 all `0.0191`

Analysis:
- The exact architecture and policy I/O are now verified offline. The model
  sees normalized obs `(B,2,25)`, flattens to global condition `(B,50)`, and
  denoises normalized actions `(B,8,7)` because
  `pred_action_steps_only=true`. Training labels are rows `1:9` under
  `oa_step_convention=true`, so the first eval action corresponds to dataset
  label `a[t]`.
- The inherited checkpoint failed because it did not fit the coupled
  pose+gripper+phase labels, not because the bridge has an obvious
  dimensional, sign, or normalization mismatch.

Next:
- Run a bounded closed-loop Isaac evaluation with correction disabled using
  the four-demo no-EMA checkpoint, phase/progress dataset mode, support trace,
  and video. Local Isaac runtime is unavailable in the default workstation
  Python, so use the existing l401 container wrapper after staging artifacts.

## 2026-06-12T01:11:25-07:00 - no-EMA closed-loop DP evals

Goal:
- Test whether the four-demo no-EMA official-DP overfit that passes dense
  offline coherence can act as a closed-loop BC warm start in the Franka cube
  Isaac task without oracle action correction.

Hypothesis:
- If the policy I/O and training alignment are truly correct, the overfit
  checkpoint should at least reproduce the matched episode-0 trajectory under
  a demo reset. If dataset-clock phase conditioning fails but contact-gated
  phase conditioning succeeds, the main train/eval mismatch is phase schedule.

Change:
- No new source change after commit `aeaf6e3`; staged the four-demo no-EMA
  checkpoint to l401 and ran two bounded 260-step single-env evals with
  correction disabled:
  - dataset-clock phase/progress provider;
  - contact-gated provider with close/lift thresholds.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `aeaf6e3f27cc97277a31205206b4a85268801c76`
- implementation_commit: `aeaf6e3f27cc97277a31205206b4a85268801c76`
- push/pull:
  local branch pushed to GitHub; l401 GitHub fetch was blocked by SSH auth, so
  the exact commit was pushed over SSH to the agent-owned remote source ref and
  checked out in
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- remote_commit/status:
  `aeaf6e3f27cc97277a31205206b4a85268801c76`
- changed_files:
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- dataset-clock job:
  `1028270`
- dataset-clock run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_dataset_video260_20260612_010053`
- contact-gated job:
  `1028273`
- contact-gated run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_contactgated_video260_20260612_010608`
- shared checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_set4_noema_20260612_005448/latest.ckpt`
- shared reset:
  accepted relabel episode `0`, row `0`, source trajectory frame `260`,
  joint blend `0.75`, cube-position blend `1.0`
- local fetched artifact roots:
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_dataset_video260_20260612_010053`
  - `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_contactgated_video260_20260612_010608`

Result:
- status: failed closed-loop warm-start evals
- dataset-clock eval:
  - steps `260`, final/window success `0.0 / 0.0`, done count `0`
  - reward mean/final `2.003 / 1.236`
  - cube lift max/final `0.01683 / 0 m`
  - EE-to-cube min/final `0.02605 / 0.1131 m`
  - finger-center-to-cube min/final `0.05561 / 0.158 m`
  - final gripper width `0.00132 m`
  - first negative gripper command appeared at step `23` while nearest support
    was still `align_open`; final support distance `5.072`
- contact-gated eval:
  - steps `260`, final/window success `0.0 / 0.0`, done count `0`
  - reward mean/final `2.091 / 2.143`
  - cube lift max/final `0.01683 / 0 m`
  - EE-to-cube min/final `0.01603 / 0.01761 m`
  - finger-center-to-cube min/final `0.05561 / 0.05640 m`
  - final gripper width `0.06809 m`
  - runtime phase stayed `align_open` for the whole rollout
  - nearest-demo support distance start/final/delta:
    `0.0137 / 0.8521 / 0.8384`
- video validation:
  both fetched videos are `1280x720`, `259` frames, `4.316667 s`, `60 FPS`.

Key Evidence:
- dataset-clock support report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_dataset_video260_20260612_010053/noema_dataset_support_report/closed_loop_support_report.md`
- contact-gated support report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_contactgated_video260_20260612_010608/noema_contactgated_support_report/closed_loop_support_report.md`
- contact-gated video:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_contactgated_video260_20260612_010608/videos/franka-cube-dp-phaseprogress-noema-contactgated-step-0.mp4`
- contact-gated contact sheet:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_contactgated_video260_20260612_010608/noema_contactgated_contact_sheet.jpg`

Analysis:
- Exact official-DP architecture and lowdim I/O are now verified offline:
  normalized obs `(B,2,25)` -> global condition `(B,50)`; model denoises
  normalized actions `(B,8,7)` because `pred_action_steps_only=true`; first
  returned action corresponds to label `a[t]` under `oa_step_convention=true`.
- The dataset-clock eval demonstrates a real train/eval mismatch: phase
  features advanced to close/lift before the live state reached close/lift
  support, so the policy closed away from the cube.
- The contact-gated eval removes that mismatch and still fails. The provider
  correctly keeps runtime conditioning in `align_open`, but the learned
  align/open action stream does not drive the fingers into a demonstrated
  close-support state. The gripper remains open, cube lift stays zero, and
  support distance steadily grows.
- Therefore the current BC is a valid offline architecture/I/O sanity check,
  not a usable closed-loop warm start. The remaining blocker is closed-loop
  support/compounding error around the align-to-contact transition, not an
  obvious tensor shape, sign, or normalization bug.

Next:
- Do not scale this checkpoint to RL warm start as-is.
- The next bounded fix should add closed-loop support around the align/contact
  transition: options are DAgger-style rollout relabeling, more robust
  align/open controller distillation before the close phase, or a hybrid gate
  that uses an oracle/contact controller only until the live state enters the
  demonstrated close support, then hands off to DP.

## 2026-06-12T01:22:27-07:00 - launch one-demo overfit exact-reset eval

Goal:
- Evaluate the one-demo no-EMA overfit checkpoint on the exact object position
  and reset state of that demo. If it succeeds, scale the same setup; if it
  fails, debug the BC train/eval mismatch before any larger run.

Hypothesis:
- A one-demo checkpoint that passes dense offline coherence should reproduce
  the memorized demo when the cube pose, phase/progress features, support
  dataset, and reset row all come from the same episode. Failure here means the
  remaining bug is in closed-loop state/reset/action execution rather than
  dataset scale.

Change:
- No source changes before launch.
- Staged one-demo artifacts to l401:
  - checkpoint:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_ep0_noema_20260612_005153/latest.ckpt`
  - phase/support dataset:
    `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/phase_progress_ep0_noema_20260612_005153/contact_relabel_set_phase_progress_ep0.npz`

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `76aa04259091cab2e32b5b03bf769125ceb67e9a`
- implementation_commit: `76aa04259091cab2e32b5b03bf769125ceb67e9a`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  detached at `76aa04259091cab2e32b5b03bf769125ceb67e9a`
- changed_files:
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- planned command:
  `RUN_NAME=franka_cube_dp_eval_phaseprogress_ep0_noema_exact_dataset_video260_<timestamp> CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_ep0_noema_20260612_005153/latest.ckpt SUPPORT_DATASET=/results/dp_bc/phase_progress_ep0_noema_20260612_005153/contact_relabel_set_phase_progress_ep0.npz PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_ep0_noema_20260612_005153/contact_relabel_set_phase_progress_ep0.npz PHASE_PROGRESS_MODE=dataset PHASE_PROGRESS_EPISODE=0 PHASE_PROGRESS_START_STEP=0 DEMO_RESET_DATASET=/results/dp_bc/phase_progress_ep0_noema_20260612_005153/contact_relabel_set_phase_progress_ep0.npz DEMO_RESET_EPISODE=0 DEMO_RESET_STEP=0 DEMO_RESET_SOURCE_TRAJECTORY_JSON=/results/dp_bc/curobo_plans/cube_curobo_scale32_20260611_125957_seed8/trajectory.json DEMO_RESET_SOURCE_FRAME=260 DEMO_RESET_JOINT_BLEND_ALPHA=0.75 DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 NUM_ENVS=1 NUM_STEPS=260 NUM_INFERENCE_STEPS=100 ACTION_CHUNK_STEPS=1 ACTION_CORRECTION_MODE=disabled CAPTURE_VIDEO=True bash cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- acceptance:
  exact reset reports `cube_pos_l2_diff_env0=0`, `cube_minus_ee_l2_diff_env0=0`;
  final/window success should be nonzero and video should show grasp/lift.

Result:
- status: launching

## 2026-06-12T04:59:03-07:00 - local one-demo x0-prediction overfit probe

Goal:
- Debug the failed/likely-failing exact one-demo DP eval without changing the
  simulator path: determine whether the epsilon-prediction diffusion objective
  is the source of remaining centimeter-scale first-action error on the critical
  align/close rows.

Hypothesis:
- Forced dataset-label replay succeeds from the exact object reset, and the
  strict epsilon checkpoint predicts on-manifold rows with small but still
  nonzero pose error. Training the same official lowdim UNet policy with
  `noise_scheduler.prediction_type=sample` may overfit x0/action sequences more
  tightly on this tiny deterministic dataset and reduce closed-loop drift.

Change:
- No source changes planned for this attempt.
- Local training variant only: same one-demo 25D dataset, same
  `WeightedDiffusionUnetLowdimPolicy`, same I/O contract, no EMA, but
  `policy.noise_scheduler.prediction_type=sample`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- implementation_commit: `n/a` (config-only local probe)
- changed_files: worklog pending

Command / Job:
- command: pending local `train.py` launch
- job_id: local PID pending
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459`

Next:
- Train locally, run offline coherence against the exact one-demo dataset, and
  stage/evaluate only if row-level errors improve over the strict epsilon
  checkpoint. Continue monitoring active l401 job `1028368`.

Result:
- status: local training completed
- pid: `1579586`
- final metrics: epoch `1999`, global step `9999`, `train_loss≈2e-5`,
  `train_action_mse_error=0.0`.
- offline coherence: pass on all `289` rows.
- all-phase row stats: offset-0 sequence MSE all
  `2.25e-06`, gripper sign match `1.0`, first pose cosine mean
  `0.999982`, best-offset-zero fraction `0.654`.
- critical rows:
  - row `56`: first pose L2 `0.00745`, predicted xyz
    `[-0.8259, 0.8928, -0.0507]` vs label
    `[-0.8196, 0.8897, -0.0530]`.
  - row `83`: first pose L2 `0.00275`, predicted gripper `-0.9999`.
  - row `240`: first pose L2 `0.00136`, predicted gripper `-1.0000`.

Analysis:
- This is a much tighter one-demo action fit than the strict epsilon checkpoint,
  while preserving the same architecture and observation/action contract. The
  remaining proof is closed-loop exact-reset eval.

Next:
- Stage the x0 checkpoint to l401 and launch a fast exact-reset eval using the
  standard chunk8/eight-sample/binary-gripper DP contract without video first.
  If metrics pass, run a video confirmation and then scale.

Follow-up launch:
- staged checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt`
- job_id: `1028370`
- run_name:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk8_avg8_gripvote_novideo_20260612_0503`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk8_avg8_gripvote_novideo_20260612_0503,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=8,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=96,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk8_avg8_gripvote_novideo_20260612_0503`

Next:
- Monitor jobs `1028368` and `1028370`; fetch metrics/support traces and
  inspect before launching any scale-up.

Follow-up launch:
- job_id: `1028371`
- run_name:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_novideo_20260612_0506`
- reason:
  x0 chunk8 showed no lift through step `100`, so this tests whether stale
  future-action chunking is the remaining mismatch. It uses the same x0
  checkpoint, exact object reset, dataset phase/progress, eight DDPM samples,
  and binary gripper voting, but `ACTION_CHUNK_STEPS=1`.
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_novideo_20260612_0506`

## 2026-06-12T05:08:00-07:00 - local x0 support-expanded one-demo training

Goal:
- Address the observed off-support failure: x0 predicts exact demo rows tightly,
  but closed-loop states drift and the policy stops emitting the saturated
  approach actions.

Hypothesis:
- Training the same x0 diffusion objective on a support-expanded one-demo
  dataset, where perturbed EE observations are labeled with actions toward the
  original demo target pose, should teach local correction behavior while the
  original copies preserve the exact demonstration policy.

Change:
- No source change for this run.
- Dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/support_expansion/normalcube_ep16_seed42_supportexp_balanced_20260612_044829/normalcube_ep16_seed42_supportexp_balanced.npz`
- Dataset shape: `9248` rows, `32` episodes, `8` original copies plus `24`
  perturbed copies, pose clip fraction `0.000288`.

Command / Job:
- command: pending local `train.py` launch
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_supportexp_balanced_x0pred_noema_20260612_0508/official_dp_train`

Next:
- Train locally with `prediction_type=sample`, then run offline coherence on
  both the original one-demo dataset and the support-expanded dataset. Stage
  and evaluate only if original-row precision remains close to the x0 exact
  checkpoint and support rows are coherent.

Result:
- status: local training completed
- final log row: epoch `299`, global step `11099`, train loss
  `0.001647`, learning rate `0.0`.
- checkpoint:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_supportexp_balanced_x0pred_noema_20260612_0508/official_dp_train/checkpoints/latest.ckpt`
- original one-demo offline coherence: pass on `289` rows, all-phase offset-0
  MSE `1.381e-04`, gripper sign `1.0`, first-pose L2 mean/max
  `0.00849/0.03762`.
- support-expanded offline coherence: pass on `9248` rows, all-phase offset-0
  MSE `8.815e-04`, gripper sign `1.0`.

Analysis:
- This checkpoint is less exact on original demo rows than the pure one-demo
  x0 model, but it has learned local corrective labels around perturbed EE
  states. The next proof is closed-loop exact reset. If it fails, tighten the
  perturbation radius and increase the original-copy weight instead of scaling.

Follow-up launch:
- staged checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_supportexp_balanced_x0pred_noema_20260612_0508/latest.ckpt`
- job_id: `1028372`
- run_name:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_supportexp_x0pred_chunk8_avg8_gripvote_novideo_20260612_0520`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_supportexp_x0pred_chunk8_avg8_gripvote_novideo_20260612_0520,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=8,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=96,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_supportexp_balanced_x0pred_noema_20260612_0508/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- remote run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_supportexp_x0pred_chunk8_avg8_gripvote_novideo_20260612_0520`

Next:
- Monitor jobs `1028371` and `1028372`. Fetch metrics/support traces and
  inspect artifacts before any scale-up.

## 2026-06-12T04:52:00-07:00 - strict one-demo exact reset chunk1 diagnostic

Goal:
- Continue the exact-object one-demo overfit gate before any scale-up. The
  target condition is a successful closed-loop lift on the same cube position
  used by the overfit trajectory.

Hypothesis:
- The strict one-demo checkpoint fits dataset rows offline, but
  `ACTION_CHUNK_STEPS=8` commits stale open-phase actions through contact. A
  chunk1 exact-reset eval should distinguish stale chunk execution from a
  deeper policy/action I/O mismatch.

Current evidence:
- Strict no-EMA one-demo checkpoint
  `phaseprogress_normalcube_ep16_seed42_strictpose_noema_20260612_1150`
  reached `train_action_mse_error=9.074e-05` and offline coherence
  all-phase offset-0 MSE `3.667e-04`.
- Exact-reset strict chunk8 eval job `1028367`, run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_strictpose_chunk8_avg8_gripvote_video320_20260612_042953`,
  failed: success/window success `0/0`, max/final lift `0.0152/0 m`,
  min/final EE-to-cube `0.0598/0.2486 m`, first hard close at step `90`.
- Policy/action trace shows the live rollout leaves support before close:
  at eval step `73` the history is duplicated after a reset-like event, and
  rows `80`-`96` emit open/large approach actions while dataset labels are
  already close-support actions.
- Forced dataset-label replay on the same exact cube reset passed, so the
  low-level label/control path is viable.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`
  at `dbfed79ba6ec80ed14891ab04b526d7189989d1a`

Command / Job:
- next command: launch strict exact-reset eval with
  `ACTION_CHUNK_STEPS=1`, `NUM_ACTION_SAMPLES=8`,
  `GRIPPER_SAMPLE_AGGREGATION=binary_vote`, same checkpoint/dataset/demo reset,
  and full policy/support tracing.
- job_id: `1028368`
- run_name:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_strictpose_chunk1_avg8_gripvote_video320_20260612_043854`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_strictpose_chunk1_avg8_gripvote_video320_20260612_043854`
- command: `sbatch --export=ALL,CODE_NFS=<agent_worktree>,RUN_NAME=<run>,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=16,SUCCESS_TIMEOUT_OVERRIDE=999.0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_strictpose_noema_20260612_1150/latest.ckpt,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`

Next:
- Submit and monitor chunk1 to completion. If chunk1 succeeds, scale to the
  prepared multi-demo dataset. If chunk1 fails, debug the live observation/action
  mismatch directly rather than scaling.

## 2026-06-12T04:44:00-07:00 - support-expanded one-demo fallback training

Goal:
- Prepare the likely fix while l401 chunk1 eval job `1028368` waits for
  resources: train a one-demo BC checkpoint that is locally robust to the
  1-3 cm live observation drift observed before the close phase.

Hypothesis:
- The strict checkpoint is accurate on demonstration observations but unstable
  off the demonstration support. Adding synthetic local EE perturbations with
  labels recomputed to the original accepted action target should teach the DP
  a corrective vector field without changing the simulator or eval action
  convention.

Change:
- Added `dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py`.
- The tool keeps the original accepted trajectory and appends perturbed copies.
  For each perturbed row it preserves cube/phase context, updates
  `ee_pos` and `cube_minus_ee`, then recomputes the 7D normalized action toward
  the pose produced by the original accepted action. This preserves the original
  label when perturbation is zero.

Validation:
- `python -m py_compile dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py`: passed.
- Generated support-expanded one-demo dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/support_expansion/normalcube_ep16_seed42_supportexp_actiontarget_20260612_044321/normalcube_ep16_seed42_supportexp_actiontarget.npz`
- Dataset summary: `9537` rows, `33` episodes, original demo plus `32`
  support copies; pose clip fraction `0.000594`; max pose/action abs `1.0`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- local training session: `11047`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_supportexp_noema_20260612_044411`
- command: official DP `train.py` with the same 25D lowdim UNet,
  `pred_action_steps_only=true`, `action_normalizer=limits_clamp_constant`,
  `use_ema=false`, `num_epochs=150`, `batch_size=128`,
  `+policy.action_loss_weights=[8,8,8,4,4,4,8]`, and dataset path set to the
  support-expanded NPZ above.

Next:
- Monitor local train to checkpoint completion. If chunk1 strict eval succeeds,
  use the result only as fallback evidence. If chunk1 fails, stage this
  checkpoint/dataset to l401 and evaluate it on the exact object reset.

## 2026-06-12T04:29:00-07:00 - strict one-demo overfit exact-object eval

Goal:
- Re-evaluate a true one-demo overfit on the exact object position of the demo
  before scaling BC to more environments.

Hypothesis:
- The previous one-demo checkpoint passed the coarse offline coherence gate but
  underfit saturated align/open actions around rows 56-80; this caused the
  closed-loop policy to leave demonstration support before gripper close. A
  stricter no-EMA one-demo overfit with weighted xyz/gripper loss should reduce
  row-level action error enough for exact-reset closed-loop success.

Change:
- No source changes after commit `dbfed79ba6ec80ed14891ab04b526d7189989d1a`.
- Trained a new local strict one-demo checkpoint with:
  `training.num_epochs=2001`, `training.lr_scheduler=constant_with_warmup`,
  `training.use_ema=false`, `checkpoint.topk.k=0`,
  `policy.action_loss_weights=[8,8,8,4,4,4,8]`,
  `task.dataset.action_normalizer=limits_clamp_constant`,
  `pred_action_steps_only=true`, `policy.num_inference_steps=100`.
- Staged checkpoint to l401:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_strictpose_noema_20260612_1150/latest.ckpt`.

Version Control:
- agent_id: franka-cube-dp-bc-warmstart-gripvote-dbfed79
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- changed_files: worklog only for this attempt
- remote_commit/status: l401 worktree
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`
  at `dbfed79ba6ec80ed14891ab04b526d7189989d1a`

Command / Job:
- local train run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_strictpose_noema_20260612_1150`
- offline coherence:
  `python -m dextrah_lab.offline_dp_bc.diagnose_dp_offline_coherence --checkpoint .../latest.ckpt --dataset .../contact_relabel_normalcube_ep16_phase_progress.npz --device cuda:0 --num-inference-steps 100`
- exact eval job: `1028366`
- exact eval run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_strictpose_chunk8_avg8_gripvote_video320_20260612_042854`
- exact eval run dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_strictpose_chunk8_avg8_gripvote_video320_20260612_042854`

Result:
- status: exact eval running
- training metrics: epoch `2000`, global step `10004`,
  `train_action_mse_error=9.07e-05`, `train_loss=0.04883`.
- offline coherence: pass on `289` rows; all-phase offset-0 MSE
  `0.0003667`; align/open offset-0 fraction `0.566`, up from the previous
  loose run's `0.152`.
- row-level checks:
  - row 56: first pose L2 `0.0236`, offset-0 sequence MSE `1.01e-04`
  - row 80: first pose L2 `0.0283`, offset-0 sequence MSE `7.53e-05`
  - row 83: predicted gripper `-0.941` for close label `-1`
  - rows 88-104: predicted gripper `-0.986` to `-0.999`

Analysis:
- This fixes the prior offline symptom where stochastic mean predictions were
  visibly attenuated in the align/open phase. The remaining question is whether
  the exact closed-loop rollout stays on support long enough to close and lift.

Next:
- Monitor job `1028366`, fetch metrics/log/video/support trace, inspect with a
  support report and contact sheet. Scale to the prepared 3-demo checkpoint only
  if this exact one-demo eval succeeds.

## 2026-06-12T04:23:00-07:00 - exact-demo DP failure and stricter one-demo overfit

Goal:
- Make the exact object-position one-demo BC eval pass before scaling to the
  three-demo/normal-reset checkpoint.

Hypothesis:
- The existing one-demo checkpoint is not actually overfit tightly enough for
  closed-loop control. Forced dataset-label replay passes, but the DP policy
  leaves support during the saturated align/open approach. Eight-sample pose
  averaging and single-sample stochastic inference both show insufficient
  closed-loop lift, so the next step is a stricter one-demo diffusion overfit
  with more optimizer steps and stronger pose/action weighting.

Evidence:
- Forced dataset replay job `1028361` completed successfully from exact object
  reset. Report/video were fetched locally:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_normalcube_ep16_exact_forcedlabels_20260612_105805`.
  It reached final nearest live row `288`, final EE-to-cube `0.0281 m`, first
  close step `83`, and visual inspection showed a real grasp/lift.
- Exact DP eval with chunk8, eight pose samples, and binary gripper vote job
  `1028363` failed. Max lift was `0.0124 m`, final lift `0`, min/final
  EE-to-cube `0.0397/0.2663 m`, first hard close `87`, final support distance
  `6.01`. Support report verdict: `FAIL: closed-loop policy still leaves
  demonstration support and closes away from the cube`.
- Policy trace shows the runtime leaves align/open support around step `52`;
  by step `56`, the offline demo label has saturated approach
  `[-0.82, 0.89, -0.053, ...]`, while the existing DP checkpoint's sampled
  mean at the exact offline row is about
  `[-0.693, 0.818, -0.040, ...]`.
- Chunk1 exact eval job `1028362` is still running but already showed no lift
  by step `60`; chunk8 single-sample binary-gripper diagnostic job `1028365`
  is running and also showed no lift by step `120`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- changed_files: worklog pending
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`
  at `dbfed79ba6ec80ed14891ab04b526d7189989d1a`

Next:
- Train a stricter local one-demo DP overfit with `obs_dim=25`,
  `pred_action_steps_only=true`, no EMA, constant-with-warmup LR, more
  optimizer steps, and heavier pose/action weights.
- Gate it with a stricter offline check focused on closed-loop-critical rows
  before staging to l401.
- Only if the exact one-demo eval passes, stage and evaluate the prepared
  three-demo checkpoint/dataset.

## 2026-06-12T10:58:05Z - normal-demo exact reset replay controls

Goal:
- Continue the true normal-reset one-demo overfit debug loop after the
  overfitted DP checkpoint failed on the exact object/robot state of its demo.

Hypothesis:
- The exact reset and saved normalizers are likely correct because reset diffs
  are zero and offline coherence passes, but closed-loop diffusion chunks leave
  support and close too late. A forced dataset-action replay under the same
  exact reset will separate controller/env replay issues from diffusion
  prediction or phase/chunk scheduling issues.

Change:
- No source changes for this attempt.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `7adb49dec78a39dc099202bd30993ca9e844a843`
- remote_commit/status: l401 worktree detached at
  `7adb49dec78a39dc099202bd30993ca9e844a843`

Evidence before launch:
- Dataset-phase exact DP eval job `1028354` failed: max lift `0.01495 m`,
  min finger-center distance `0.0602 m`, first negative gripper at step `133`
  after the hand was already away from the cube.
- Contact-gated exact DP eval job `1028360` also failed: max lift
  `0.01236 m`, min finger-center distance `0.06583 m`, first negative
  gripper at step `144`, first hard close at step `157`.
- Contact-gated support report verdict:
  `FAIL: closed-loop policy still leaves demonstration support and closes away
  from the cube.`
- Visual inspection of the contact-gated contact sheet matches the trace: the
  hand approaches open, pushes/leaves the cube, then closes away from it.

Command / Job:
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_replay_normalcube_ep16_exact_forcedlabels_20260612_105805,DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/latest.ckpt,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DATASET_START_EPISODE=0,DATASET_START_STEP=0,NUM_ENVS=1,STEPS=289,NUM_INFERENCE_STEPS=100,MODES=dataset_t\,dataset_t_plus_7\,dataset_target_t_plus_1\,dataset_target_t_plus_7\,controller_target_hold,ACTION_REPEAT=1,POSE_ACTION_MULTIPLIER=1,CLIP_ACTIONS=1.0,CONTROLLER_TARGET_LOOKAHEAD=1,CONTROLLER_TARGET_TOLERANCE=0.015,CONTROLLER_TARGET_MAX_HOLD=16,CAPTURE_VIDEO=True,VIDEO_LENGTH=289,VIDEO_NAME_PREFIX=franka-cube-dp-replay-normalcube-exact,PRINT_INTERVAL=32,SEED=42 cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- job_id: `1028361`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/replays/franka_cube_dp_replay_normalcube_ep16_exact_forcedlabels_20260612_105805`

Result:
- status: pending on l401 resources

Next:
- Monitor the replay to completion, fetch report/CSV/video, inspect the label
  replay behavior, then choose between a diffusion/chunk training fix and an
  eval/control-stack fix.

## 2026-06-12T11:04:20Z - normal-demo exact reset chunk1 DP diagnostic

Goal:
- Test whether the one-demo DP checkpoint can solve the exact normal-demo reset
  when used in receding-horizon first-action mode instead of executing 8
  predicted future actions per query.

Hypothesis:
- Direct checkpoint queries show first actions are mostly coherent but the
  future gripper chunk is smoothed/delayed at the align-to-close boundary.
  `ACTION_CHUNK_STEPS=1` should remove that stale future-action failure mode
  and close when the dataset phase/progress schedule reaches the close rows.

Change:
- No source changes for this attempt.

Version Control:
- implementation_commit: `7adb49dec78a39dc099202bd30993ca9e844a843`

Command / Job:
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_chunk1_avg8_video320_20260612_110420,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-dp-normalcube-ep16-exact-chunk1-avg8,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=320,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1028362`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_chunk1_avg8_video320_20260612_110420`

Result:
- status: pending/running on l401

Next:
- Monitor beside replay job `1028361`, fetch metrics/video/support report, and
  compare close timing and support distance against the chunk8 failures.

## 2026-06-12T11:05:01Z - opt-in binary gripper sample aggregation

Goal:
- Patch the observed chunk8 failure mode where averaging stochastic DP samples
  smooths the binary gripper channel and delays close through the phase
  transition.

Hypothesis:
- Averaging pose channels across DDPM samples is useful, but arithmetic mean is
  wrong for a binary open/close gripper command. Keeping pose averaging while
  using a close vote for gripper should preserve the successful low-variance
  chunk8 pose behavior without suppressing close commands.

Change:
- Added `gripper_sample_aggregation` to
  `predict_action_sequence_from_ppo_obs` and `predict_action_from_ppo_obs`.
- Default remains `mean`.
- New opt-in mode `binary_vote` emits `-1` close when the fraction of sampled
  gripper values below `gripper_close_threshold` is at least
  `gripper_vote_threshold`; otherwise it emits `+1` open.
- Added CLI and Slurm wrapper plumbing:
  `--gripper_sample_aggregation`, `--gripper_close_threshold`,
  `--gripper_vote_threshold` / `GRIPPER_*`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`

Next:
- Commit, push, update the l401 worktree to the exact commit, then launch a
  chunk8 exact normal-demo eval with `NUM_ACTION_SAMPLES=8` and
  `GRIPPER_SAMPLE_AGGREGATION=binary_vote`.

## 2026-06-12T11:10:00Z - chunk8 exact eval with binary gripper vote

Goal:
- Test whether the one-demo exact normal-reset DP eval succeeds when chunk8
  still averages pose across eight DDPM samples but aggregates the gripper as a
  binary close vote.

Hypothesis:
- The failed chunk8 average run was caused by arithmetic averaging suppressing
  close commands in the future gripper horizon. Binary voting with
  `close_threshold=0.5` and `vote_threshold=0.5` should close at the transition
  rows while preserving the pose variance reduction that made chunk8 viable.

Change:
- Source commit `dbfed79ba6ec80ed14891ab04b526d7189989d1a` deployed to an
  isolated l401 worktree:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`
- The original l401 worktree at `7adb49d` was left untouched because queued
  jobs `1028361` and `1028362` still reference it.

Command / Job:
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_chunk8_avg8_gripvote05_video320_20260612_111000,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=8,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-dp-normalcube-ep16-exact-chunk8-avg8-gripvote,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=80,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1028363`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_chunk8_avg8_gripvote05_video320_20260612_111000`

Result:
- status: pending/running on l401

Next:
- Monitor with jobs `1028361` and `1028362`; fetch metrics/video/support
  report and compare against mean-gripper chunk8.

## 2026-06-12T11:14:00Z - local 3-demo accepted-only DP training

Goal:
- Prepare the next BC scale-up candidate from accepted true-normal-reset
  relabel demos while l401 exact-reset diagnostics are pending.

Hypothesis:
- If one-demo exact eval passes with chunk1 or binary gripper voting, the next
  useful scale step is a no-EMA official-DP checkpoint trained on all accepted
  normal-reset demos currently available: the validated ep16 seed42 demo plus
  the two accepted seed45 demos.

Change:
- Combined accepted-only relabel NPZs into:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/combined_contact_relabel_normalcube_3eps_20260612_1110/contact_relabel_normalcube_3eps_accepted.npz`
- Converted to 25D phase/progress dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/combined_contact_relabel_normalcube_3eps_20260612_1110/contact_relabel_normalcube_3eps_phase_progress.npz`
- Dataset summary: 3 episodes, 1133 rows, episode ends `[289, 849, 1133]`,
  phase counts `{0: 239, 1: 240, 2: 654}`, reset alphas all `0.0`.

Command / Job:
- command:
  `PYTHONPATH=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy:/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart WANDB_MODE=offline HYDRA_FULL_ERROR=1 /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python train.py --config-dir /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp obs_dim=25 policy.model.global_cond_dim=50 policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy +policy.action_loss_weights=[1,1,1,1,1,1,8] task.dataset_path=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/combined_contact_relabel_normalcube_3eps_20260612_1110/contact_relabel_normalcube_3eps_phase_progress.npz task.dataset.val_ratio=0.0 task.dataset.action_normalizer=limits_clamp_constant pred_action_steps_only=true training.device=cuda:0 training.use_ema=false training.num_epochs=300 training.max_train_steps=null training.max_val_steps=null training.lr_warmup_steps=20 training.checkpoint_every=50 training.rollout_every=10 training.val_every=10 training.sample_every=10 policy.num_inference_steps=100 dataloader.batch_size=64 val_dataloader.batch_size=64 logging.mode=offline hydra.run.dir=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_3eps/phaseprogress_normalcube_3eps_noema_20260612_111400/official_dp_train`
- pid: pending
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_3eps/phaseprogress_normalcube_3eps_noema_20260612_111400/official_dp_train`

Result:
- status: launching local GPU training

Next:
- Monitor loss/logs/checkpoint. If training completes and the exact one-demo
  diagnostics identify a working eval mode, run offline coherence and stage the
  checkpoint/dataset for l401 eval.

## 2026-06-12T03:15:00-07:00 - raw 32-demo label executability failure and eval phase decoder fix

Goal:
- Continue the exact-reset BC debugging after the one-demo/set4 overfit passed
  with the correct chunked DP execution contract, and avoid misleading phase
  names in 25D support reports.

Result:
- The 32-demo full-pick/lift phase-progress checkpoint failed from exact
  source reset, including close-boundary and lift-boundary segment resets.
- The fixed exact dataset-label replay also failed to execute the raw full-pick
  labels:
  - run:
    `franka_cube_dp_replay_curobo32_phaseprogress_ep0_exact_dataset_t_fix_video720_20260612_0248`

## 2026-06-12T05:27:00-07:00 - one-demo exact x0 chunk1 pass and video confirmation launch

Goal:
- Evaluate the overfitted checkpoint on the exact object position from its one
  demo and only scale after that pass is real.

Hypothesis:
- The strict epsilon checkpoint failed because it did not overfit the tiny
  deterministic dataset tightly enough, and `ACTION_CHUNK_STEPS=8` compounds
  stale future actions. The x0/sample-prediction one-demo checkpoint with
  single-step closed-loop replanning should execute the exact reset.

Change:
- No source changes for this eval. Used the one-demo x0/sample checkpoint,
  dataset phase/progress provider, exact dataset object reset, eight DDPM
  samples with binary gripper voting, and `ACTION_CHUNK_STEPS=1`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`
  at `dbfed79ba6ec80ed14891ab04b526d7189989d1a`

Command / Job:
- passed no-video job: `1028371`
- run_name:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_novideo_20260612_0506`
- fetched run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_novideo_20260612_0506`

Result:
- status: passed metric gate
- metrics: final/window success `1.0/1.0`, final/max lift
  `0.2394/0.2394 m`, final EE-to-cube `0.0393 m`, final gripper width
  `0.0419 m`, steps `320`.
- exact reset evidence: cube position, cube-minus-EE, and lowdim reset diffs
  all `0.0`.
- support report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_novideo_20260612_0506/support_report/closed_loop_support_report.md`

Analysis:
- This answers the user question directly: the earlier failed exact-reset
  overfit was not the final x0/chunk1 run. With the corrected x0 objective and
  single-step replanning, the exact one-demo object-position eval succeeds.
- The support report remains conservative only because this was a no-video run;
  the scalar metrics and reset telemetry are clean.

Next:
- Launched video confirmation job `1028376`, run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_video320_20260612_052713`,
  with the same checkpoint/dataset/reset and only `CAPTURE_VIDEO=True`,
  `VIDEO_LENGTH=320`, and full policy tracing changed.
- Train a 3-demo x0/sample-prediction checkpoint locally before evaluating
  larger-scale environments. The existing 3-demo checkpoint is epsilon
  prediction, so it is not the matched scale-up from the passing overfit.

Follow-up launch:
- local training session: `24812`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_3eps/phaseprogress_normalcube_3eps_x0pred_noema_20260612_052755`
- command:
  `CUDA_VISIBLE_DEVICES=0 PYTHONPATH=$EXT/diffusion_policy:$DEX WANDB_MODE=offline HYDRA_FULL_ERROR=1 $EXT/venv/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp obs_dim=25 policy.model.global_cond_dim=50 policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy +policy.action_loss_weights=[1,1,1,1,1,1,8] policy.noise_scheduler.prediction_type=sample task.dataset_path=$EXT/artifacts/combined_contact_relabel_normalcube_3eps_20260612_1110/contact_relabel_normalcube_3eps_phase_progress.npz task.dataset.val_ratio=0.0 task.dataset.action_normalizer=limits_clamp_constant pred_action_steps_only=true training.device=cuda:0 training.use_ema=false training.num_epochs=1200 training.max_train_steps=null training.max_val_steps=null training.lr_warmup_steps=20 training.checkpoint_every=100 training.rollout_every=100 training.val_every=100 training.sample_every=100 policy.num_inference_steps=100 dataloader.batch_size=64 val_dataloader.batch_size=64 logging.mode=offline hydra.run.dir=<run_dir>/official_dp_train`
- expected acceptance before cluster eval: final loss near the one-demo x0
  scale, offline coherence pass on all 3 demos, and no EMA/train-eval mismatch.

Follow-up result:
- training status: passed
- final metrics: epoch `1199`, global step `21599`, final train loss
  `2.84e-05`, LR `0.0`, `train_action_mse_error=0.0`.
- offline coherence: passed on all `1133` rows with model weights, no EMA.
  All-phase MSE@0 `4.08e-06`, gripper sign `1.0`, pose cosine mean
  `0.999951`, offset-0 fraction `0.645`.
- report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_3eps/phaseprogress_normalcube_3eps_x0pred_noema_20260612_052755/offline_coherence_latest/offline_coherence_report.md`
- staged checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_3eps_x0pred_noema_20260612_052755/latest.ckpt`
- staged dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/phase_progress_normalcube_3eps_x0pred_noema_20260612_052755/contact_relabel_normalcube_3eps_phase_progress.npz`

Scale-up launch:
- Because `eval_franka_cube_dp_policy.py` accepts one
  `PHASE_PROGRESS_EPISODE` / `DEMO_RESET_EPISODE` at a time, launched three
  single-env exact-reset no-video probes, one per accepted demo episode, using
  the same x0/chunk1/eight-sample/binary-gripper contract.
- job `1028377`, ep `0`, `NUM_STEPS=320`, run
  `franka_cube_dp_eval_normalcube_3eps_x0pred_exact_ep0_chunk1_avg8_gripvote_novideo_20260612_053339`
- job `1028378`, ep `1`, `NUM_STEPS=620`, run
  `franka_cube_dp_eval_normalcube_3eps_x0pred_exact_ep1_chunk1_avg8_gripvote_novideo_20260612_053339`
- job `1028379`, ep `2`, `NUM_STEPS=320`, run
  `franka_cube_dp_eval_normalcube_3eps_x0pred_exact_ep2_chunk1_avg8_gripvote_novideo_20260612_053339`
  - replay report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_replays/franka_cube_dp_replay_curobo32_phaseprogress_ep0_exact_dataset_t_fix_video720_20260612_0248/replay_report.md`
  - verdict:
    controller follows the expected dataset action direction but strongly
    under-realizes the one-step delta magnitude; the replay closes far from the
    cube and does not lift.
- Conclusion: do not train further on the raw full-pick CuRobo labels as direct
  BC actions. The executable contact-aware relabel sets remain the right data
  source until the raw-label controller/action convention is redesigned.

Change:
- Updated `eval_franka_cube_dp_policy.py` so 25D phase/progress NPZs with
  collapsed phase IDs decode as `align_open`, `close_hold`, `lift`, matching
  replay diagnostics.
- This only fixes support/demo-reset diagnostics; it does not change policy
  inference or controller behavior.

Validation:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Next:
- Commit/push/deploy the diagnostic fix.
- Continue with executable contact-aware alpha0.75 relabel data; for normal
  reset, the remaining issue is support coverage from normal reset into the
  demonstrated close/lift basin, not the DP tensor I/O.

## 2026-06-12T02:56:43-07:00 - launch alpha ladder contact relabel gate

Goal:
- Test whether the later left/right contact gate plus lateral-centering
  relabel controller can bridge from the passing `alpha=0.75` reset toward the
  normal robot reset (`alpha=0.0`) before any new BC training.

Command / Job:
- job_id: `1028348`
- run:
  `franka_cube_contact_relabel_lrcentering_ep16_alpha_ladder_20260612_025643`
- source:
  l401 worktree detached at `13d4555a1b2eb1381bb7115985990b6866f836a2`
- specs:
  ep16/source step 260 with joint-blend alphas
  `0.75, 0.60, 0.50, 0.40, 0.25, 0.00`
- controller settings:
  `ORIENTATION_MODE=source`, `POSE_ACTION_FILTER=scale`,
  `POSE_ACTION_LIMIT=0.95`, `ALIGN_STEPS=0`,
  `CONTACT_ALIGN_STEPS=240`, `CONTACT_ALIGN_REFERENCE=live_cube`,
  `CONTACT_GATE_MODE=left_right`, `REQUIRE_CONTACT_GATE=True`,
  `LATERAL_CENTERING_GAIN=1.0`, `LATERAL_CENTERING_LIMIT=0.035`,
  `LATERAL_SEARCH_AMPLITUDE=0.006`, `CLOSE_STEPS=80`,
  `LIFT_STEPS=160`.

Acceptance:
- Fetch and inspect `contact_relabel_set_report.md`,
  `contact_relabel_set_summary.json`, videos/contact sheets, and failures.
- If lower alphas pass, expand accepted alphas across seeds `8,16,24,30` and
  train a new no-EMA phase/progress BC on the accepted alpha-mix dataset.
- If the ladder fails above `alpha=0.0`, do not train; use the first failing
  alpha to redesign the relabel controller or reset bridge.

Result:
- Canceled before allocation:
  `1028348|CANCELLED by 158351|0:0|00:00:00|None assigned`.
- Reason: existing normal-reset trace starts around
  `||cube_minus_ee||=0.231 m`, while the alpha ladder would still reset the
  cube to a source row and only blend robot joints. Even `alpha=0.0` would not
  be a true normal-reset relabel target.

## 2026-06-12T03:03:00-07:00 - add normal-cube relabel reset option

Goal:
- Generate executable contact-aware BC labels from actual task-reset cube
  geometry instead of only source-row cube geometry.

Change:
- Added `--reset_cube_pos_blend_alpha` to
  `contact_aware_franka_cube_rollout.py`.
  - `1.0`: old behavior, reset cube to selected source row.
  - `0.0`: keep the task-reset cube pose and collect live lowdim/action rows
    under the contact-aware controller.
- Threaded `RESET_CUBE_POS_BLEND_ALPHA` through
  `cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`.
- Preserved `rollout_reset_cube_pos_blend_alpha` in accepted relabel NPZs and
  phase/progress NPZs.

Validation:
- `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/contact_aware_franka_cube_rollout.py dextrah_lab/offline_dp_bc/make_contact_relabel_set_report.py dextrah_lab/offline_dp_bc/make_phase_progress_dataset.py`
- `bash -n cluster/sbatch_contact_aware_franka_cube_relabel_set_1gpu.sh`
- `git diff --check`

Next:
- Commit/push/deploy this reset option.
- Launch a true normal-cube relabel gate with `RESET_JOINT_BLEND_ALPHA=0.0`
  and `RESET_CUBE_POS_BLEND_ALPHA=0.0` using the left/right contact gate and
  lateral-centering controller. If it passes, expand across seeds/resets and
  retrain no-EMA phase/progress BC.

## 2026-06-12T03:03:46-07:00 - launch true normal-cube relabel gate

Goal:
- Check whether the contact-aware controller can produce an executable
  close/lift demonstration from the actual normal task reset state before
  adding any new BC training data.

Command / Job:
- job_id: `1028349`
- run:
  `franka_cube_contact_relabel_normalcube_ep16_seed42_20260612_030346`
- source:
  l401 worktree detached at `9c7d8b56b034243aa42e93508e4ebc6cf3d0ab4a`
- reset:
  `RESET_JOINT_BLEND_ALPHA=0.0`, `RESET_CUBE_POS_BLEND_ALPHA=0.0`,
  task reset seed `42`, source episode `16` only for reference orientation.
- controller:
  `ORIENTATION_MODE=source`, `POSE_ACTION_FILTER=scale`,
  `POSE_ACTION_LIMIT=0.95`, `CONTACT_ALIGN_STEPS=320`,
  `CONTACT_ALIGN_REFERENCE=live_cube`, `CONTACT_GATE_MODE=left_right`,
  `REQUIRE_CONTACT_GATE=True`, `LATERAL_CENTERING_GAIN=1.0`,
  `LATERAL_CENTERING_LIMIT=0.045`, `LATERAL_SEARCH_AMPLITUDE=0.008`,
  `CLOSE_STEPS=80`, `LIFT_STEPS=160`, video enabled.

Acceptance:
- Fetch and inspect aggregate report, rollout report, summary, video, and
  contact sheet.
- If the hard gate passes visually and metrically, expand normal-cube relabels
  across seeds and train a new no-EMA phase/progress BC.
- If it fails, debug the normal-reset relabel controller before any BC training.

## 2026-06-12T02:41:25-07:00 - 32-demo full-pick exact reset failed

Goal:
- Evaluate the 32-demo full-pick/lift phase-progress BC checkpoint on episode
  0 with exact cube pose and exact source robot joints.

Hypothesis:
- If the checkpoint really overfits the offline GraspGenX/CuRobo/oracle
  labels, an exact source-state reset with dataset-clock phase/progress should
  lift the cube before any normal-reset scale-up.

Change:
- No new source changes after commit `07127c1cc7e7bee831fdafd7a5fe598b23157929`.
- Ran with correction disabled, `ACTION_CHUNK_STEPS=8`,
  `NUM_ACTION_SAMPLES=8`, `NUM_INFERENCE_STEPS=100`, and exact source reset
  from episode 0 / frame 0.

Command / Job:
- job_id: `1028337`
- run:
  `franka_cube_dp_eval_curobo32_phaseprogress_ep0_exact_dataset_chunk8_avg8_video720_20260612_023101`
- remote run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_curobo32_phaseprogress_ep0_exact_dataset_chunk8_avg8_video720_20260612_023101`
- local run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_phaseprogress_ep0_exact_dataset_chunk8_avg8_video720_20260612_023101`

Result:
- status: failed
- reset evidence:
  - cube position L2 diff: `0`
  - cube-minus-EE L2 diff: `3.03e-7`
  - lowdim L2/Linf diff: `7.97e-7` / `5.67e-7`
  - source joint write diff: `0`
- closed-loop metrics:
  - final/window success: `0 / 0`
  - max/final lift: `0.00198 / 0.00198 m`
  - final EE-to-cube: `0.1227 m`
  - final finger-center-to-cube: `0.1279 m`
  - final gripper width: `0.0277 m`
- support report verdict:
  `FAIL: closed-loop policy still leaves demonstration support and closes away from the cube.`
- artifacts:
  - report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_phaseprogress_ep0_exact_dataset_chunk8_avg8_video720_20260612_023101/curobo32_phaseprogress_exact_support_report/closed_loop_support_report.md`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_phaseprogress_ep0_exact_dataset_chunk8_avg8_video720_20260612_023101/videos/franka-cube-dp-curobo32-phaseprogress-ep0-exact-chunk8-avg8-step-0.mp4`

Analysis:
- This is not a normal-reset generalization failure. The exact source reset is
  verified and the policy still misses contact/lift.
- Runtime phase/progress features are correct, but the support-report phase
  name decoder is misleading for collapsed full-pick phase ids; it prints phase
  id `0` as `close_fingers` even though the runtime feature vector is
  `phase_align_open`.
- Next split must separate source label executability from diffusion-policy
  prediction drift.

Next:
- Launch dataset-label replay from the same exact reset/start row.
- Launch shorter exact segment resets at the close and lift boundaries.

## 2026-06-12T02:42:00-07:00 - launch exact replay and segment diagnostics

Goal:
- Determine whether the 32-demo full-pick failure is caused by non-executable
  labels/controller semantics or by the diffusion policy failing to emit the
  right actions.

Hypothesis:
- `dataset_t` replay from exact episode 0 should succeed if the full-pick
  labels are directly executable under the current evaluator.
- Exact reset at source step `302` isolates close/hold-to-lift behavior.
- Exact reset at source step `422` isolates lift behavior after starting from
  the demo's closed-grasp state.

Command / Job:
- replay job_id: `1028342`
  - run:
    `franka_cube_dp_replay_curobo32_phaseprogress_ep0_exact_dataset_t_video720_20260612_0242`
  - wrapper: `cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
  - key settings: `MODES=dataset_t`, `STEPS=720`, exact demo reset episode
    0/step 0, source trajectory JSON episode 0, fixed dataset start episode
    0/step 0, video enabled.
- close-boundary DP job_id: `1028343`
  - run:
    `franka_cube_dp_eval_curobo32_phaseprogress_ep0_close302_exact_chunk8_avg8_video420_20260612_0242`
  - key settings: reset episode 0/step 302, source frame 302,
    `PHASE_PROGRESS_START_STEP=302`, `NUM_STEPS=420`, correction disabled,
    chunk8, 8 action samples.
- lift-boundary DP job_id: `1028344`
  - run:
    `franka_cube_dp_eval_curobo32_phaseprogress_ep0_lift422_exact_chunk8_avg8_video300_20260612_0242`
  - key settings: reset episode 0/step 422, source frame 422,
    `PHASE_PROGRESS_START_STEP=422`, `NUM_STEPS=300`, correction disabled,
    chunk8, 8 action samples.

Result:
- status: submitted; monitoring required.

Next:
- Poll logs to completion, fetch artifacts, inspect replay report/support
  reports/videos, then patch or relaunch based on which split fails.

## 2026-06-12T02:48:00-07:00 - fix and relaunch 25D replay diagnostic

Goal:
- Make the dataset-action replay diagnostic compatible with 25D
  phase/progress datasets so it can answer whether labels are executable.

Hypothesis:
- Replay crash `1028342` is a diagnostic bug: the live env exposes 21D lowdim,
  while the dataset rows include 4 extra phase/progress features.

Change:
- `replay_franka_cube_dataset_actions.py` now uses the first 21 lowdim
  dimensions for reset, nearest-row, and controller-target math when the input
  dataset has phase/progress features.
- Pure label replay no longer loads or queries the DP checkpoint unless
  `dp_replan` mode is requested.
- Phase names for collapsed 3-phase phase/progress datasets decode as
  `align_open`, `close_hold`, `lift`.

Version Control:
- implementation_commit: `9bbe4b2ba9bb2c4d2dfc036dcdca13444631878d`
- push/pull:
  - pushed to GitHub branch `codex/franka-cube-diffusion-policy-bc`
  - pushed directly to `/lustre/fsw/portfolios/nvr/users/lzha/src/DEXTRAH`
    because l401 cannot fetch GitHub SSH
  - l401 agent worktree detached at `9bbe4b2ba9bb2c4d2dfc036dcdca13444631878d`

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/replay_franka_cube_dataset_actions.py`
- `bash -n cluster/sbatch_replay_franka_cube_dp_actions_1gpu.sh`
- `git diff --check`

Result:
- original replay job `1028342` failed with:
  `ValueError: operands could not be broadcast together with shapes (21,) (25,)`.
- relaunched fixed replay:
  - job_id: `1028346`
  - run:
    `franka_cube_dp_replay_curobo32_phaseprogress_ep0_exact_dataset_t_fix_video720_20260612_0248`

Next:
- Monitor `1028346` plus segment jobs `1028343` and `1028344`.

## 2026-06-12T02:40:00-07:00 - broaden BC support with 32-demo phase/progress training

Goal:
- Continue from the one-demo/four-demo exact-reset pass by testing whether the
  working Diffusion Policy I/O can become useful under normal resets with
  broader GraspGenX/CuRobo support.

Hypothesis:
- The four-demo phase/progress checkpoint works on exact resets but fails
  normal resets because its support is too narrow. The older 32-demo 21D
  checkpoint has broader reset coverage but failed closed-loop with noisy
  actions and no phase/progress conditioning. A 32-demo checkpoint using the
  verified 25D phase/progress I/O should preserve the exact-reset contract
  while covering more cube/reset states.

Change:
- Extended `make_phase_progress_dataset.py` with
  `--phase-mode pick_lift_to_contact`, mapping the sorted full-pick/lift phase
  IDs by phase name into the same three runtime phases used by the existing
  providers:
  - align/open: pregrasp, hold-pregrasp, pregrasp-to-grasp, hold-grasp
  - close/hold: close-fingers, hold-after-close
  - lift: lift-object, hold-after-lift
- Preserved the original full-pick/lift phase IDs as `source_phase_ids` in the
  generated NPZ.
- Fixed a false negative in `diagnose_dp_offline_coherence.py`: phases whose
  correct pose command is near zero may now pass by low absolute pose error
  instead of invalid direction/norm-ratio checks.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `9a0ab91ae99b0c3075953ae05269b0e94e64d35a`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/make_phase_progress_dataset.py`
  - `dextrah_lab/offline_dp_bc/diagnose_dp_offline_coherence.py`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Prior normal-reset results:
- job `1028333`, single-env video confirmation of the four-demo checkpoint:
  `franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_video320_20260612_021036`
  - status: failed
  - final/window success `0/0`, `done_count=1`
  - max/final lift `0.0100/0.0 m`
  - min/final EE-to-cube `0.0724/0.1387 m`
  - min/final finger-center-to-cube `0.0825/0.1367 m`
  - final gripper width `0.00328 m`
  - support report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_video320_20260612_021036/normalreset_video_support_report/closed_loop_support_report.md`
  - video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_video320_20260612_021036/videos/franka-cube-dp-set4-noema-normalreset-chunk8-avg8-step-0.mp4`
- job `1028334`, 16-env normal-reset probe of the older 32-demo 21D
  full-pick/lift checkpoint:
  `franka_cube_dp_eval_curobo32_framefix_overfit2k_normalreset_chunk8_avg8_16env_20260612_021330`
  - status: failed
  - final/window success `0/0`, `done_count=2`
  - max/final lift `0.00105/0.0 m`
  - min/final EE-to-cube `0.1084/0.1098 m`
  - min/final finger-center-to-cube `0.1339/0.1446 m`
  - actions saturated/noisy, with no lift
  - support report:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_curobo32_framefix_overfit2k_normalreset_chunk8_avg8_16env_20260612_021330/curobo32_framefix_support_report/closed_loop_support_report.md`

Dataset / Training:
- generated 32-demo 25D phase/progress dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_curobo32_phaseprogress/full_pick_lift_framefix_phaseprogress_20260612_022104/franka_cube_curobo32_full_pick_lift_framefix_phaseprogress.npz`
- dataset shape: obs `(22484,25)`, action `(22484,7)`, episodes `32`
- collapsed phase counts: align/open `9044`, close/hold `3840`, lift `9600`
- dataset report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_curobo32_phaseprogress/full_pick_lift_framefix_phaseprogress_20260612_022104/dataset_report/dataset_report.md`
- trained no-EMA weighted official DP:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_curobo32_phaseprogress/curobo32_phaseprogress_noema_10k_20260612_022223`
- training settings: `obs_dim=25`, `global_cond_dim=50`,
  `WeightedDiffusionUnetLowdimPolicy`, gripper loss weight `8`,
  `pred_action_steps_only=true`, `num_inference_steps=100`,
  `training.use_ema=false`, `batch_size=128`, about `10k` optimizer steps.
- final train loss around `0.0069`.

Offline gate:
- corrected coherence report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_curobo32_phaseprogress/curobo32_phaseprogress_noema_10k_20260612_022223/offline_coherence_nearzero_gatefix/offline_coherence_report.md`
- status: pass over all `22484` rows.
- all-phase metrics: pose cosine mean `0.8488`, gripper sign `0.9997`,
  MSE@0 all `0.000108`, max first-action pose MAE `0.00442`.
- close/hold passed by near-zero pose absolute-error criteria:
  label pose norm median `6.39e-17`, pose MSE `1.64e-6`, max pose MAE
  `0.00290`, gripper sign `0.9984`.

Staged l401 artifacts:
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/curobo32_phaseprogress_noema_10k_20260612_022223/latest.ckpt`
- phase/support dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/phase_progress_curobo32/full_pick_lift_framefix_phaseprogress_20260612_022104.npz`
- exact episode-0 source trajectory:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/curobo_plans/cube_curobo_batch_20260611_122807_seed0/trajectory.json`

Next:
- Commit/push source changes, update the l401 source checkout, then run an
  exact-reset video eval on episode 0 of the 32-demo phase/progress dataset
  with correction disabled, `ACTION_CHUNK_STEPS=8`, and `NUM_ACTION_SAMPLES=8`.
- If exact reset passes, run normal-reset 16-env and video probes with the same
  checkpoint/dataset.

## 2026-06-12T01:55:00-07:00 - exact-reset overfit closed-loop pass and batched reset fix

Goal:
- Finish the requested one-demo exact-object-position overfit evaluation, then
  continue to the next scale checks only if the overfit succeeds.

Hypothesis:
- If the one-demo checkpoint can pass under exact cube/source-joint reset with
  the correct DP execution contract, then the remaining failures are control
  path and scale-up issues rather than tensor shape, normalization, sign, or
  reset-label bugs.

Change:
- Added an eval-only `--demo_reset_replicate_env0_joint_blend` flag and
  `DEMO_RESET_REPLICATE_ENV0_JOINT_BLEND` Slurm wrapper variable.
- Added all-env reset error diagnostics to the demo reset summary. This is for
  batched exact-state diagnostics only; it does not change training or policy
  inference.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `d1fb11d4d26c1f8edc509b41374233a58170ca8b`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- one-demo chunk1 exact reset, correction disabled:
  job `1028292`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_dataset_video260_20260612_012415`
- one-demo chunk8 exact reset, correction disabled:
  job `1028296`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_dataset_chunk8_video260_20260612_012955`
- one-demo full-label oracle control:
  job `1028297`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_fullcorr_video260_20260612_012955`
- one-demo chunk8 + 8-sample averaged exact reset:
  job `1028299`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_chunk8_avg8_video260_20260612_013632`
- one-demo 16-env chunk8 + 8-sample averaged reset:
  job `1028301`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_chunk8_avg8_16env_20260612_014101`
- four-demo no-EMA checkpoint, episode-0 exact reset, chunk8 + 8-sample
  averaged:
  job `1028302`,
  `franka_cube_dp_eval_phaseprogress_set4_noema_ep0_exact_chunk8_avg8_video260_20260612_014233`

Result:
- status: one-demo exact overfit passes with the corrected DP execution
  contract; four-demo exact reset reaches success late; batched exact reset
  needs the new env0 joint-blend replication option.
- One-demo chunk1 failed despite exact reset:
  final/window success `0 / 0`, final EE-to-cube `0.235 m`, final gripper
  width `0.0114 m`. This showed per-step replanning is wrong for this DP
  checkpoint.
- One-demo chunk8 lifted but missed success:
  final/window success `0 / 0`, final cube lift `0.192 m`, final cube XY error
  `0.0968 m`.
- Full-label oracle control passed under the same exact reset/support labels:
  final/window success `1 / 1`, first success at step `229`. This validates
  reset and labels.
- One-demo chunk8 + 8 sampled action sequences averaged passed:
  final/window success `1 / 1`, first success around step `216`, final cube
  lift `0.1816 m`, final cube XY error `0.0668 m`, final EE-to-cube
  `0.0114 m`, reset `lowdim_l2_diff_env0=0`.
- The 16-env run did not represent 16 identical exact resets: env0 was exact,
  but the source-joint blend was computed against each env's randomized normal
  reset. It finished at final/window success `0.0625 / 0.1035` with mean final
  EE-to-cube `0.173 m`, so a proper batched exact-state check needs the new
  env0 joint-blend replication flag.
- The four-demo no-EMA checkpoint with chunk8 + 8-sample averaging reached
  final success on episode 0:
  final/window success `1 / 0.125`, final cube lift `0.124 m`, final cube XY
  error `0.0602 m`, final EE-to-cube `0.00824 m`. It is physically grasping
  and lifting, but too late in a 260-step horizon for a robust warm-start
  claim.

Validation:
- `python3 -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`
- fetched videos are `1280x720`, `259` frames, `4.316667 s`, `60 FPS`.
- artifact viewer URLs:
  - one-demo avg8 pass video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_ep0_noema_exact_chunk8_avg8_video260_20260612_013632/videos/franka-cube-dp-ep0-noema-exact-chunk8-avg8-step-0.mp4`
  - four-demo set4 avg8 video:
    `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_exact_chunk8_avg8_video260_20260612_014233/videos/franka-cube-dp-set4-noema-ep0-exact-chunk8-avg8-step-0.mp4`

Next:
- Commit and deploy the reset replication eval fix to l401.
- Rerun the one-demo 16-env exact-state check with
  `DEMO_RESET_REPLICATE_ENV0_JOINT_BLEND=True`.
- Run a longer four-demo exact reset horizon to verify the late success is a
  stable hold rather than a last-frame threshold crossing.

## 2026-06-12T02:07:00-07:00 - set4 exact-reset BC scale checks pass

Goal:
- Confirm that the BC fix is not just a single-demo artifact by evaluating the
  four-demo no-EMA checkpoint on each accepted set4 exact reset with the same
  DP execution contract.

Hypothesis:
- If chunked execution, 8-sample averaging, exact source-joint reset, and the
  phase/progress clock are the correct inference contract, then the set4
  checkpoint should pass all four memorized exact trajectories over a longer
  320-step horizon.

Change:
- No source changes after commit `d24e5f4a8f52ea0106f094b663c35e48fc8dc523`.
- Ran no-learning Isaac evals only.

Version Control:
- implementation_commit: `d24e5f4a8f52ea0106f094b663c35e48fc8dc523`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  detached at `d24e5f4a8f52ea0106f094b663c35e48fc8dc523`
- changed_files:
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Command / Job:
- one-demo replicated 16-env exact reset:
  job `1028304`,
  `franka_cube_dp_eval_phaseprogress_ep0_noema_exact_chunk8_avg8_16env_repl_20260612_014854`
- set4 episode 0 exact reset, 320-step video:
  job `1028303`,
  `franka_cube_dp_eval_phaseprogress_set4_noema_ep0_exact_chunk8_avg8_video320_20260612_014854`
- set4 episode 1 exact reset:
  job `1028308`,
  `franka_cube_dp_eval_phaseprogress_set4_noema_ep1_exact_chunk8_avg8_320_20260612_015449`
- set4 episode 2 exact reset:
  job `1028306`,
  `franka_cube_dp_eval_phaseprogress_set4_noema_ep2_exact_chunk8_avg8_320_20260612_015449`
- set4 episode 3 exact reset:
  job `1028307`,
  `franka_cube_dp_eval_phaseprogress_set4_noema_ep3_exact_chunk8_avg8_320_20260612_015449`

Result:
- status: BC exact-reset scale checks passed.
- Aggregate metrics:

| run | envs | steps | final/window | lift_final | xy_final | ee_final | done | reset_l2_all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| one16 | 16 | 260 | 1/1 | 0.1850 | 0.0678 | 0.0126 | 0 | 6.755e-7 |
| set4_ep0 | 1 | 320 | 1/1 | 0.2014 | 0.0552 | 0.0083 | 0 | 0 |
| set4_ep1 | 1 | 320 | 1/1 | 0.2582 | 0.0755 | 0.0330 | 0 | 0 |
| set4_ep2 | 1 | 320 | 1/1 | 0.2402 | 0.0078 | 0.0119 | 0 | 0 |
| set4_ep3 | 1 | 320 | 1/1 | 0.2440 | 0.0118 | 0.0082 | 0 | 5.268e-9 |

- All support reports returned:
  `PASS (bounded): exact source-joint matched reset with success-timeout override retains and lifts the cube through the rollout horizon.`
- The corrected 16-env check confirms that the previous 16-env failure was a
  reset batching artifact: copying env0's applied joint blend produced
  all-env reset lowdim max error `6.755e-7` and final/window success `1/1`.
- The set4 320-step video for episode 0 shows a clean grasp, lift, and hold;
  ffprobe reports `1280x720`, `319` frames, `5.316667 s`, `60 FPS`.

Key Evidence:
- set4 episode 0 video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_exact_chunk8_avg8_video320_20260612_014854/videos/franka-cube-dp-set4-noema-ep0-exact-chunk8-avg8-320-step-0.mp4`
- set4 episode 0 support report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_ep0_exact_chunk8_avg8_video320_20260612_014854/set4_320_support_report/closed_loop_support_report.md`

Analysis:
- The BC path now has a concrete working contract:
  official DP `WeightedDiffusionUnetLowdimPolicy`, normalized obs
  `(B,2,25)`, global condition `(B,50)`, normalized action chunks `(B,8,7)`,
  `oa_step_convention=true`, `ACTION_CHUNK_STEPS=8`,
  `NUM_ACTION_SAMPLES=8`, correction disabled.
- Exact-reset BC works for the memorized one-demo and four-demo trajectories.
  This is still a bounded exact-source-joint diagnostic, not a claim of normal
  randomized-reset generalization.

Next:
- Use this checkpoint/inference contract for the BC warm-start path. Any
  normal-reset or RL warm-start experiment should keep `ACTION_CHUNK_STEPS=8`
  and `NUM_ACTION_SAMPLES=8`, and should not use the eval-only oracle
  correction modes.

## 2026-06-12T02:03:38-07:00 - launch no-EMA normal-reset scale probe

Goal:
- Move beyond exact memorized reset replay by evaluating the current four-demo
  no-EMA BC checkpoint from the normal DEXTRAH reset distribution.

Hypothesis:
- The exact-reset pass establishes the DP architecture/I/O and execution
  contract. If the BC is useful as a warm start beyond memorization, the same
  checkpoint should show nonzero contact/lift/success on a 16-env normal-reset
  probe when using the fixed inference contract:
  `ACTION_CHUNK_STEPS=8`, `NUM_ACTION_SAMPLES=8`, `NUM_INFERENCE_STEPS=100`,
  contact-gated phase/progress, and correction disabled.

Change:
- No source changes after `9a0ab91ae99b0c3075953ae05269b0e94e64d35a`.
- Launch one no-video 16-env Isaac eval first. If it fails or is ambiguous,
  fetch metrics/support traces and run one single-env video confirmation.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `9a0ab91ae99b0c3075953ae05269b0e94e64d35a`
- remote_commit/status:
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
  detached at `9a0ab91ae99b0c3075953ae05269b0e94e64d35a`
- changed_files: worklog pending after launch/result

Command / Job:
- planned run name:
  `franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_16env_20260612_020338`
- planned command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_16env_20260612_020338,NUM_ENVS=16,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,ACTION_CHUNK_STEPS=8,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=32,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=40,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_set4_noema_20260612_005448/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,ACTION_CORRECTION_MODE=disabled cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- run_dir:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_16env_20260612_020338`

Acceptance:
- Scheduler completion is not enough. Fetch logs, metrics, support trace, and
  config locally; inspect final/window success, lift, EE/finger distances,
  done count, and env0 support drift.
- If successful, continue to broader environments. If failed, debug whether the
  remaining blocker is normal-reset support coverage, phase gating, or another
  train/eval mismatch.

Result:
- 16-env probe job `1028310` completed `COMPLETED|0:0` in `00:04:04` on
  `pool0-00014`.
- local artifact dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_16env_20260612_020338`
- support report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_16env_20260612_020338/normalreset_16env_support_report/closed_loop_support_report.md`
- status: failed as normal-reset BC warm start.
- metrics:
  - `steps_completed=320`, `num_envs=16`, `done_count=18`.
  - final/window success `0.0/0.0`, `has_lifted_cube.max=0.0`.
  - max/final lift `0.00367/0.00070 m`.
  - min/final EE-to-cube `0.0976/0.1075 m`.
  - min/final finger-center-to-cube `0.1023/0.1058 m`.
  - env0 nearest-demo support distance `8.962 -> 2.862`; runtime phase stayed
    `align_open` for all `320` records.
- report verdict:
  `FAIL: closed-loop policy still leaves demonstration support and closes away from the cube.`

Analysis:
- The current DP execution contract is no longer the immediate blocker. With
  the exact same checkpoint, chunking, sample averaging, bridge, and normalizer,
  exact set4 reset passes but normal reset starts far outside the four-demo
  relabel support and never reaches close/lift support.
- The 16-env metrics are aggregated across env resets, so a single-env video is
  needed to make the failure visually unambiguous before choosing the next
  support-expansion/training run.

Follow-up launch:
- job_id: `1028333`
- run:
  `franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_video320_20260612_021036`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart,RUN_NAME=franka_cube_dp_eval_phaseprogress_set4_noema_normalreset_contactgated_chunk8_avg8_video320_20260612_021036,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,ACTION_CHUNK_STEPS=8,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=True,VIDEO_LENGTH=320,VIDEO_NAME_PREFIX=franka-cube-dp-set4-noema-normalreset-chunk8-avg8,PRINT_INTERVAL=32,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=40,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_set4_noema_20260612_005448/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_set4/contact_relabel_set_phase_progress.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=contact_gated,PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.55,PHASE_LIFT_SUPPORT_DISTANCE_THRESHOLD=0.75,PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.025,ACTION_CORRECTION_MODE=disabled cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- status: pending/running; fetch metrics, video, support report, and inspect
  before any training or RL scale-up.

## 2026-06-12T01:38:00-07:00 - add DP action sample averaging

Goal:
- Reduce stochastic DDPM action error in closed-loop BC inference after the
  one-demo chunk8 eval showed successful lift but lateral goal miss.

Hypothesis:
- The policy is close enough to grasp/lift when executing 8-step chunks, but
  stochastic sample error in each denoised chunk shifts the carried cube in XY.
  Averaging multiple sampled action sequences for the same observation history
  should reduce this variance without oracle labels or changing the dataset.

Change:
- Added `num_action_samples` to `predict_action_sequence_from_ppo_obs`.
- Added `--num_action_samples` to `eval_franka_cube_dp_policy.py` and recorded
  it in run config/metrics.
- Added `NUM_ACTION_SAMPLES` to
  `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `76aa04259091cab2e32b5b03bf769125ceb67e9a`
- implementation_commit: pending
- changed_files:
  - `dextrah_lab/offline_dp_bc/ppo_bridge.py`
  - `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
  - `cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
  - `worklogs/franka-cube-grasp-prior/franka-cube-dp-bc-warmstart.md`

Validation:
- `python3 -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- `bash -n cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- `git diff --check`

Next:
- Commit, deploy to the agent-owned l401 worktree, then test one-demo exact
  reset with `ACTION_CHUNK_STEPS=8` and `NUM_ACTION_SAMPLES=8`.

Next:
- Monitor job to completion, fetch metrics/log/video/support trace, inspect
  video and support plots, then either scale or patch.

## 2026-06-12T03:28:03-07:00 - normal-reset one-demo overfit and scale relabel launch

Goal:
- Continue the BC warm-start loop from the exact-reset overfit: validate a
  true normal-reset relabel demo, overfit official DP to that demo, launch its
  exact-state eval, and scale the relabel data only after the relabel gate
  itself passed.

Result so far:
- True normal-reset contact-aware relabel job `1028349` passed the hard gate:
  `reset_joint_blend_alpha=0.0`, `reset_cube_pos_blend_alpha=0.0`,
  final/max lift `0.1363/0.1363 m`, final EE-to-cube `0.0281 m`,
  final finger-center-to-cube `0.0550 m`, zero executed pose clipping.
- Visual artifact inspected via `viz-open` and contact sheet; rollout shows
  normal reset approach, centered grasp, close, and lift.
- Created 25D one-demo phase/progress dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/contact_relabel_normalcube_ep16_phase_progress.npz`
  with `obs=(289,25)`, `action=(289,7)`, phase counts
  `{0: 83, 1: 80, 2: 126}`.
- Trained no-EMA official DP one-demo overfit using the known-good contract:
  `WeightedDiffusionUnetLowdimPolicy`, `pred_action_steps_only=true`,
  `obs_dim=25`, `global_cond_dim=50`, gripper loss weight `8`,
  `action_normalizer=limits_clamp_constant`, `num_inference_steps=100`.
- Final local train metrics: epoch `299`, global step `1499`,
  `train_action_mse_error=0.00183`, `train_loss=0.04519`.
- Offline coherence passed all `289` rows:
  all-phase pose cosine mean `0.9894`, pose norm ratio median `0.9793`,
  gripper sign match `1.0`, offset-0 sequence MSE all `0.00181`.
- Added and smoke-tested
  `dextrah_lab/offline_dp_bc/combine_contact_relabel_sets.py` for combining
  accepted relabel NPZs while preserving per-episode reset metadata.

Artifacts:
- Normal relabel report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_normalcube_ep16_seed42_20260612_030346/contact_relabel_set_report.md`
- Normal relabel video:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/contact_relabel_sets/franka_cube_contact_relabel_normalcube_ep16_seed42_20260612_030346/rollouts/ep16s260_a0p0/videos/franka-cube-contact-normalcube-ep16s260_a0p0-step-0.mp4`
- Offline coherence report:
  `http://localhost:8765/view?path=.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/offline_coherence_latest/offline_coherence_report.md`

Staged l401 artifacts:
- checkpoint:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/latest.ckpt`
- phase/support dataset:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz`

Submitted jobs:
- Exact normal-demo DP eval job `1028354`, run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_chunk8_avg8_video320_20260612_032738`.
  Uses `ACTION_CHUNK_STEPS=8`, `NUM_ACTION_SAMPLES=8`,
  `ACTION_CORRECTION_MODE=disabled`, dataset phase/progress provider, and
  demo reset with `DEMO_RESET_JOINT_BLEND_ALPHA=0.0`,
  `DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0`.
- Scale relabel jobs `1028350`-`1028353`: seeds `43`, `44`, `45`, `46`, each
  with source episodes `8,16,24,30` at frame `260`, true normal robot/cube
  reset, source orientation, live-cube contact alignment, left/right contact
  gate, and the same hard relabel acceptance thresholds.

Next:
- Monitor jobs to completion. For `1028354`, fetch metrics/log/video/support
  trace and inspect video before deciding pass/fail. For `1028350`-`1028353`,
  fetch every relabel set, inspect summaries/videos, combine accepted NPZs,
  convert to 25D phase/progress, train a no-EMA scaled DP checkpoint, then run
  exact and normal-reset evals with the fixed chunk8/avg8 policy contract.

## 2026-06-12T01:31:00-07:00 - launch one-demo action-chunk and oracle controls

Goal:
- Debug the failed one-demo exact-reset DP eval without changing source:
  distinguish action-chunk/replanning error from bad reset/support labels.

Hypothesis:
- The one-demo checkpoint may fail with `ACTION_CHUNK_STEPS=1` because it was
  trained to emit coherent 8-step chunks, and single-step closed-loop replanning
  compounds small align/open errors immediately. If `ACTION_CHUNK_STEPS=8`
  succeeds, chunking is the first BC fix. If full-label oracle correction fails
  under the same one-demo support dataset, the reset/label control path is bad.

Change:
- No source changes. Launch two single-env exact-reset controls:
  - one-demo DP with `ACTION_CHUNK_STEPS=8`, correction disabled;
  - one-demo `nearest_label_full_action` oracle-control, to validate labels.

Version Control:
- implementation_commit: `76aa04259091cab2e32b5b03bf769125ceb67e9a`

Command / Job:
- pending job ids and run dirs will be recorded after submission.

Result:
- status: launching
## 2026-06-12T05:44:23-07:00 - launch one-action x0 DP ablation

Goal:
- Debug the brittle exact-reset BC behavior by removing the unused 8-step
  action horizon from the DP output while preserving the established 25D
  observation, x0/sample prediction objective, action normalizer, and chunk1
  eval contract.

Hypothesis:
- The current checkpoint learns offline labels, but closed-loop chunk1 eval is
  sensitive around the close boundary. Training `n_action_steps=1` with
  `horizon=2,pad_before=1` makes the model predict only `a[t]` from
  `[obs[t-1], obs[t]]`, reducing future close/lift leakage into the first
  executed action.

Change:
- No source changes for this ablation. Use Hydra overrides on the existing
  `franka_cube_lowdim_dp` config.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- changed_files: worklog only

Command / Job:
- local GPU: RTX 6000 Ada, `cuda:0`
- run_dir:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_x0pred_1act_noema_20260612_0544`
- command:
  `CUDA_VISIBLE_DEVICES=0 PYTHONPATH=$EXT/diffusion_policy:$DEX WANDB_MODE=offline HYDRA_FULL_ERROR=1 $EXT/venv/bin/python train.py --config-dir $DEX/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp horizon=2 n_action_steps=1 obs_dim=25 policy.model.global_cond_dim=50 policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy +policy.action_loss_weights=[1,1,1,1,1,1,8] policy.noise_scheduler.prediction_type=sample task.dataset_path=$EXT/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/contact_relabel_normalcube_ep16_phase_progress.npz task.dataset.val_ratio=0.0 task.dataset.action_normalizer=limits_clamp_constant task.dataset.pad_after=0 pred_action_steps_only=true training.device=cuda:0 training.use_ema=false training.num_epochs=1200 training.max_train_steps=null training.max_val_steps=null training.lr_warmup_steps=20 training.checkpoint_every=100 training.rollout_every=100 training.val_every=100 training.sample_every=100 policy.num_inference_steps=100 dataloader.batch_size=64 val_dataloader.batch_size=64 logging.mode=offline hydra.run.dir=<run_dir>/official_dp_train`

Acceptance:
- Inspect training loss/MSE, run offline coherence against the one-demo
  dataset, then stage and evaluate exact reset with `ACTION_CHUNK_STEPS=1`.

Result:
- First launch failed immediately before completing epoch 0:
  `RuntimeError: Sizes of tensors must match ... Expected size 2 but got size 1`
  inside official `ConditionalUnet1D`. The default three-level U-Net
  downsamples along the predicted action horizon and cannot process a
  length-1 `pred_action_steps_only` trajectory.

Next:
- Relaunch the same one-action ablation with a shallow official U-Net
  `policy.model.down_dims=[128]` so no downsample/upsample path is required.

Follow-up result:
- Shallow local train completed successfully:
  `epoch=1199`, `global_step=5999`, `train_action_mse_error=1e-05`,
  `train_loss=0.00014`.
- 100-step offline coherence passed on the one-demo dataset:
  all-phase MSE@0 `1.265e-05`, gripper sign `1.0`, align-open offset0
  fraction `0.831`, all-phase offset0 fraction `0.484`.
- Staged checkpoint to l401:
  `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_1act_shallow_noema_20260612_0546/latest.ckpt`.
- First sbatch submit command was malformed because the long `--export` list
  was split over shell lines; no Slurm job was submitted from that failed
  attempt.

Closed-loop eval launch:
- job_id: `1028382`
- run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_1act_shallow_chunk1_avg8_gripvote_novideo_20260612_0549`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_1act_shallow_chunk1_avg8_gripvote_novideo_20260612_0549,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=320,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_1act_shallow_noema_20260612_0546/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- success condition: exact-reset scalar pass matching or exceeding the previous
  one-demo no-video pass (`final/window success=1.0`, sustained lift) before
  any scale-up.

## 2026-06-12T12:53:49Z - exact video failure and support-expanded chunk1 ablation

Goal:
- Resolve whether the one-demo overfit actually works under the exact object
  reset, and if not, identify the smallest next BC/debugging change.

Hypothesis:
- The inherited no-video exact-reset pass is brittle. A video-enabled repeat
  with the same zero-diff object reset can expose the contact failure, and the
  already-trained support-expanded checkpoint should be retested under the
  now-working `ACTION_CHUNK_STEPS=1` contract before writing new code.

Change:
- No source changes. Fetched and inspected the video-enabled exact one-demo
  run. Launch a no-video exact-reset eval for the support-expanded checkpoint
  with `ACTION_CHUNK_STEPS=1`, `NUM_ACTION_SAMPLES=8`, binary gripper vote,
  dataset phase/progress, and demo object reset.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- implementation_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- changed_files: worklog only

Evidence:
- Video exact-reset repeat `1028376` failed despite reset diffs all zero:
  final/window success `0/0`, max/final lift `0.01623/0 m`,
  final gripper width `0.0002126 m`.
- Support report verdict: policy leaves demo support and closes away from cube.
  At first hard close step 84, live `cube_minus_ee` was
  `[0.01546, -0.04966, 0.01423]`, EE/finger distances
  `0.0539/0.0608 m`. The matching successful no-video pass closed earlier
  around step 80 with live `cube_minus_ee`
  `[-0.01088, -0.03516, 0.01037]`.
- Shallow one-action eval `1028382` is trending failed: through step 200 it
  remains on-table with no success/lift and delayed close.

Command / Job:
- support-expanded run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_supportexp_x0pred_chunk1_avg8_gripvote_novideo_20260612_0554`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_supportexp_x0pred_chunk1_avg8_gripvote_novideo_20260612_0554,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=320,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_supportexp_balanced_x0pred_noema_20260612_0508/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1028384`

Acceptance:
- If the support-expanded chunk1 exact reset passes, confirm with video, then
  train/evaluate the corresponding multi-demo setup. If it fails, patch the
  dataset/policy/eval contract around close timing and live pose correction
  rather than scaling.

Follow-up diagnostic:
- The earlier full-label oracle pass used a source-joint/pregrasp reset
  (`source_joint_reset_available=True`, `joint_blend_alpha=0.75`), so it does
  not validate the normal robot reset requested here.
- Launch a normalcube exact-cube reset full-label oracle-control run with
  `ACTION_CORRECTION_MODE=nearest_label_full_action` against the same
  normalcube one-demo support dataset. This isolates the normalcube labels from
  DP model error.
- run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_fullcorr_x0pred_chunk1_avg8_gripvote_novideo_20260612_0558`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_fullcorr_x0pred_chunk1_avg8_gripvote_novideo_20260612_0558,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=8,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=80,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=nearest_label_full_action,ACTION_CORRECTION_BLEND=1.0,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`
- job_id: `1028385`

## 2026-06-12T13:01:05Z - ordered-label oracle diagnostic for exact normal reset

Goal:
- Separate "nearest support row drift" from whether the exact one-demo labels
  themselves execute from the normal robot reset and exact object pose.

Change:
- Added eval-only `ACTION_CORRECTION_MODE=dataset_step_full_action` in
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`.
- This mode replaces/blends all seven executed action dimensions with the
  support label at `phase_progress_start_step + rollout_step` inside
  `phase_progress_episode`, matching the forced-label replay semantics. It
  does not change training or normal DP inference.
- Syntax checked locally with:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`
- Copied the patched eval script to remote code checkout
  `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79`.

Evidence motivating this patch:
- Existing forced-label replay
  `franka_cube_dp_replay_normalcube_ep16_exact_forcedlabels_20260612_105805`
  starts with zero reset diff and executes ordered dataset labels. It ends
  near the cube (`final EE-cube 0.0281 m`, `final finger-cube 0.0550 m`) and
  reports controller under-realization rather than wrong action direction.
- `nearest_label_full_action` is still a nearest-neighbor controller. If the
  live trace drifts off the support manifold, it can select labels from the
  wrong part of the demo and obscure whether row-ordered labels are valid.

Closed-loop ordered-label oracle launch:
- job_id: `1028386`
- run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_datasetstep_fullcorr_x0pred_chunk1_novideo_20260612_060105`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_datasetstep_fullcorr_x0pred_chunk1_novideo_20260612_060105,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=1,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=80,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=dataset_step_full_action,ACTION_CORRECTION_BLEND=1.0,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`

Interpretation plan:
- If ordered labels pass but learned DP fails, the issue is BC closed-loop
  tracking/compounding error, so continue with better support/data/training
  under the official epsilon/chunk8 contract.
- If ordered labels fail, debug action conversion or regenerate normal-reset
  contact-aware demos before scaling.

## 2026-06-12T13:04:46Z - learned one-demo exact reset with heavier diffusion sampling

Goal:
- Test whether the learned one-demo x0 checkpoint is failing primarily from
  diffusion sampling variance at contact.

Rationale:
- Offline coherence for
  `phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt`
  passes on the train demo (`MSE@0 all ~= 2.25e-6`, gripper sign fraction
  `1.0`), so the model has memorized the dataset under its own normalizer.
- Ordered-label oracle `1028386` is lifting by step 280 on the exact object
  reset, so labels and action execution are sufficient when row-ordered
  actions are used directly.
- The remaining learned-policy failure can plausibly be small stochastic
  contact error compounded by closed-loop rollout.

Closed-loop learned-policy launch:
- job_id: `1028387`
- run:
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg64_gripvote_novideo_20260612_060446`
- command:
  `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/franka-cube-dp-bc-warmstart-gripvote-dbfed79,RUN_NAME=franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg64_gripvote_novideo_20260612_060446,NUM_ENVS=1,NUM_STEPS=320,NUM_INFERENCE_STEPS=100,NUM_ACTION_SAMPLES=64,GRIPPER_SAMPLE_AGGREGATION=binary_vote,GRIPPER_CLOSE_THRESHOLD=0.5,GRIPPER_VOTE_THRESHOLD=0.5,ACTION_CHUNK_STEPS=1,CLIP_ACTIONS=1.0,SUCCESS_WINDOW=80,SUCCESS_TIMEOUT_OVERRIDE=999.0,CAPTURE_VIDEO=False,VIDEO_LENGTH=320,PRINT_INTERVAL=20,SEED=42,DEBUG_POLICY_TRACE_MAX_CALLS=320,DEBUG_POLICY_TRACE_ENV_INDEX=0,CHECKPOINT=/results/dp_bc/checkpoints/phaseprogress_normalcube_ep16_seed42_x0pred_noema_20260612_0459/latest.ckpt,SUPPORT_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,PHASE_PROGRESS_EPISODE=0,PHASE_PROGRESS_START_STEP=0,PHASE_PROGRESS_MODE=dataset,ACTION_CORRECTION_MODE=disabled,DEMO_RESET_DATASET=/results/dp_bc/phase_progress_normalcube_one/normalcube_ep16_seed42_phase_progress_20260612_032517.npz,DEMO_RESET_EPISODE=0,DEMO_RESET_STEP=0,DEMO_RESET_JOINT_BLEND_ALPHA=0.0,DEMO_RESET_CUBE_POS_BLEND_ALPHA=1.0 cluster/sbatch_eval_franka_cube_dp_policy_1gpu.sh`

Acceptance:
- A scalar pass here requires video confirmation before any scale-up claim.
- If this still fails while `1028386` passes, continue with feedback-robust
  support/data augmentation rather than more one-demo training epochs.

Result update for ordered-label oracle `1028386`:
- Fetched artifacts to:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_datasetstep_fullcorr_x0pred_chunk1_novideo_20260612_060105`.
- Generated support report:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_datasetstep_fullcorr_x0pred_chunk1_novideo_20260612_060105/support_report/closed_loop_support_report.md`.
- Metrics: final/window success `1.0/0.5375`, final/max lift
  `0.1794/0.1794 m`, final reward `24.78`, final gripper width
  `0.04434 m`, reset lowdim/cube diffs all `0`.
- Support trace: phase switches stayed exactly on support at close/lift
  (`support dist 0`), first hard close at step 84 with live
  `cube_minus_ee [-0.009908, -0.02661, -0.0005183]`, and final
  `cube_minus_ee [-0.008283, -0.02675, -0.001882]`.
- Conclusion: exact object reset and normal-reset ordered labels are valid.
  Learned-policy failures are closed-loop BC robustness, not basic reset,
  action convention, or normalizer failure.

## 2026-06-12T13:08:20Z - policy-trace recovery dataset and retrain

Goal:
- If the learned high-sampling one-demo eval still fails, train on actual
  closed-loop failure states labeled by the ordered expert target, rather than
  relying on random support perturbations.

Change:
- Added `dextrah_lab/offline_dp_bc/make_policy_recovery_dataset.py`.
- The script reads failed eval `policy_trace.json` records, uses each 25D live
  `lowdim_obs` as a supervised state, maps the trace step to the matching demo
  row, and labels the state with a clipped residual action toward the demo row's
  commanded target pose. This is a targeted DAgger-style recovery dataset for
  the observed contact miss.
- Syntax check:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/make_policy_recovery_dataset.py`

Recovery dataset build:
- base dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_normalcube_one_traj/phaseprogress_normalcube_ep16_seed42_noema_20260612_032517/contact_relabel_normalcube_ep16_phase_progress.npz`
- trace:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/cluster_evals/franka_cube_dp_eval_normalcube_ep16_seed42_exact_x0pred_chunk1_avg8_gripvote_video320_20260612_052713/policy_trace.json`
- output:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/policy_recovery/normalcube_ep16_x0fail_video_20260612_0607/normalcube_ep16_policy_recovery_x0fail_video.npz`
- command:
  `PYTHONPATH=$PWD /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python -m dextrah_lab.offline_dp_bc.make_policy_recovery_dataset --base_dataset <base> --policy_trace <trace> --output <output> --demo_episode 0 --demo_start_step 0 --original_copies 4 --clip_actions 1.0 --label_mode residual_to_demo_target`
- dataset summary: `1476` steps, `5` episodes (`4` original copies plus
  `320` recovery records), obs dim `25`, pose clip fraction `0.0812`.

Recovery training launch:
- run:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/official_dp_policy_recovery/normalcube_ep16_x0fail_video_recovery_x0pred_noema_20260612_060820`
- command:
  `CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/diffusion_policy:/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart WANDB_MODE=offline HYDRA_FULL_ERROR=1 /home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/venv/bin/python train.py --config-dir /home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart/dextrah_lab/offline_dp_bc/config --config-name franka_cube_lowdim_dp obs_dim=25 policy.model.global_cond_dim=50 policy._target_=dextrah_lab.offline_dp_bc.weighted_diffusion_policy.WeightedDiffusionUnetLowdimPolicy +policy.action_loss_weights=[1,1,1,1,1,1,8] policy.noise_scheduler.prediction_type=sample task.dataset_path=<recovery_npz> task.dataset.val_ratio=0.0 task.dataset.action_normalizer=limits_clamp_constant pred_action_steps_only=true training.device=cuda:0 training.use_ema=false training.num_epochs=800 training.max_train_steps=null training.max_val_steps=null training.lr_warmup_steps=20 training.checkpoint_every=100 training.rollout_every=100 training.val_every=100 training.sample_every=100 policy.num_inference_steps=100 dataloader.batch_size=64 val_dataloader.batch_size=64 logging.mode=offline hydra.run.dir=<run>/official_dp_train`
- status at logging time: running past epoch `100`.
## 2026-06-12T15:20:53Z - timed-action recovery5 overfit

Goal:
- Make the exact one-demo overfit pass from the exact demo object position,
  then use that working baseline before scaling to larger environment sets.

Hypothesis:
- Ordered expert labels already pass when injected directly on the exact
  reset, so the next BC dataset should teach the diffusion policy to output
  that same timestep-indexed action program for both demo states and failed
  closed-loop states. This avoids brittle residual-to-pose labels that keep
  chasing off-manifold geometry and delaying the gripper close.

Change:
- Built a policy recovery dataset with `label_mode=dataset_step_action`,
  `original_copies=16`, and five failed exact-reset traces including the latest
  contact-gated failure.
- Dataset:
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/policy_recovery/normalcube_ep16_timed_action_recovery5_20260612_082049/normalcube_ep16_timed_action_recovery5.npz`
- Summary: `6224` rows, `21` episodes, action abs max `0.95000005`, pose clip
  fraction `0`.

Version Control:
- agent_id: `franka-cube-dp-bc-warmstart`
- worktree:
  `/home/lzha/code/.codex-worktrees/DEXTRAH/franka-cube-dp-bc-warmstart`
- branch: `codex/franka-cube-diffusion-policy-bc`
- base_commit: `dbfed79ba6ec80ed14891ab04b526d7189989d1a`
- implementation_commit: pending
- changed_files:
  `dextrah_lab/offline_dp_bc/make_policy_recovery_dataset.py`,
  `dextrah_lab/rl_games/eval_franka_cube_dp_policy.py`,
  this worklog
- remote_commit/status: remote eval code is staged at the prior deployed
  worktree plus rsynced eval script; no new tracked code needed for this
  timed-action dataset build.

Command / Job:
- build command:
  `PYTHONPATH=$DEX $EXT/venv/bin/python -m dextrah_lab.offline_dp_bc.make_policy_recovery_dataset --base_dataset $BASE --policy_trace <5 traces> --output $OUT/normalcube_ep16_timed_action_recovery5.npz --demo_episode 0 --demo_start_step 0 --original_copies 16 --clip_actions 1.0 --label_mode dataset_step_action`
- next command: local official-DP training on GPU 0.

Result:
- status: pending training

Analysis:
- Latest failed exact reset
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_contactgate4_x0pred_chunk1_avg8_gripvote_novideo_20260612_075532`
  closed at step `203`, after the hand had drifted to about `0.189 m` from
  the cube. The closest approach was step `59` at EE distance `0.054 m` with
  the gripper still open. This confirms the prior contact-gated labels were too
  conservative and still did not keep pose on support.

Next:
- Train the timed-action recovery policy, run offline coherence, stage the
  checkpoint to l401, then evaluate exact reset with no action correction.

## 2026-06-12T16:10:00Z - exact-reset recovery5 diagnostics and recovery6 dataset

Goal:
- Evaluate the overfitted one-demo checkpoint on the exact object position of
  that demo, then debug until BC succeeds.

Result:
- `normalcube_ep16_timed_action_recovery5_x0pred_noema_20260612_082120`
  still fails exact reset without eval action correction.
- `1028507`
  (`franka_cube_dp_eval_normalcube_ep16_seed42_exact_timedrec5_x0pred_chunk1_sample1_gripvote_novideo_20260612_0900`):
  final/window success `0/0`, max lift `0.00653 m`, EE-to-cube min/final
  `0.0558/0.2145 m`, finger-center min/final `0.0674/0.2571 m`.
- `1028508`
  (`franka_cube_dp_eval_normalcube_ep16_seed42_exact_timedrec5_x0pred_chunk8_sample1_gripvote_novideo_20260612_0900`):
  final/window success `0/0`, max lift `0.00629 m`, EE-to-cube min/final
  `0.0504/0.2089 m`, finger-center min/final `0.0647/0.2531 m`.
- The earlier avg8/chunk1 job `1028506` was clearly failed by step `300`
  and was cancelled to free the cluster slot for the chunk8 diagnostic.

Trace analysis:
- The successful dataset-step oracle run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_datasetstep_fullcorr_x0pred_chunk1_novideo_20260612_060105`
  closes at step `84` with live cube-minus-EE about
  `[-0.0099, -0.0266, -0.0005]`, EE distance `0.0284 m`, and later lifts
  to `0.179 m`.
- The learned recovery5 chunk1/sample1 run closes at step `84` with
  cube-minus-EE about `[-0.0477, -0.0451, 0.0099]`, EE distance `0.0664 m`,
  and then pushes/drifts the cube away.
- Offline dataset-state inference is still coherent; one-sample and avg8
  predictions both match labels near 1e-3 on in-dataset histories. The failure
  is therefore closed-loop state dependence: when the live state leaves demo
  support near the end of align/open, the learned policy emits off-label pose
  corrections instead of the timed oracle action program.

Recovery6 dataset:
- Built
  `/home/lzha/code/.codex-external/franka-cube-dp-bc-warmstart/artifacts/policy_recovery/normalcube_ep16_timed_action_recovery6_20260612_0910/normalcube_ep16_timed_action_recovery6.npz`
  using `label_mode=dataset_step_action`, the previous five failed traces,
  and the new chunk1/chunk8 failure traces above.
- Reduced `original_copies` from `16` to `8` so recovery states have comparable
  weight to exact-demo states.
- Summary: `4272` rows, `15` episodes, action abs max `0.95000005`, pose clip
  fraction `0`.

Next:
- Train an official-DP x0/no-EMA checkpoint on recovery6, run offline
  coherence, stage it to l401, and evaluate exact reset again.

## 2026-06-12T10:45:00-07:00 - recovery8 exact pass and 32-env contact-gate fix

Goal:
- Keep pushing until the BC warm start works: first prove the one-demo
  overfit on the exact object pose, then scale to randomized resets and patch
  the failure rather than treating the exact pass as sufficient.

Result:
- Exact one-demo eval passed with checkpoint
  `normalcube_ep16_trunc140_residual_recovery8_x0pred_noema_20260612_095835/epoch200_snapshot.ckpt`.
- No-video run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_trunc140_residual8_epoch200_x0pred_chunk1_sample1_gripvote_novideo_20260612_100232`
  / job `1028520`: final/window success `1.0/0.575`, final/max lift
  `0.1782/0.1782 m`, first hard close step `84`, reset cube/lowdim diffs
  exactly zero.
- Video run
  `franka_cube_dp_eval_normalcube_ep16_seed42_exact_trunc140_residual8_epoch200_x0pred_chunk1_sample1_gripvote_video_20260612_100733`
  / job `1028521`: final/window success `1.0/0.825`, final/max lift
  `0.2078/0.2078 m`; contact sheet/video inspection shows a clean grasp and
  lift.
- First scale probe
  `franka_cube_dp_eval_normalcube_32env_seed42_randomreset_trunc140_residual8_epoch200_x0pred_chunk1_sample1_gripvote_novideo_20260612_101226`
  / job `1028523` only reached final/window success `0.03125/0.01914`.
  Env0 followed the exact trajectory until approach, then closed about
  `3 cm` farther off laterally; the gripper collapsed to near zero width and
  missed the cube.

Analysis:
- The exact overfit failure is solved for the epoch-200 recovery8 checkpoint.
  The random-reset failure is now a closed-loop support/gating problem, not an
  object reset mismatch.
- Existing `ContactGatedPhaseProgressProvider` had a bad lift gate: it
  required the live lifted state to remain close to close-hold support and
  required gripper width below `0.025 m`. The successful grasp holds the cube
  around `0.04-0.05 m`, and lifted states should move away from close-hold
  support. That made the contact-gated mode unusable for a successful lift.

Change:
- Patched `dextrah_lab/offline_dp_bc/ppo_bridge.py` so lift gating depends on
  lifted-state support plus the gripper-width threshold, not on remaining close
  to close-hold support.
- Kept the earlier `make_policy_recovery_dataset.py` trace-step filters
  (`--min_trace_step`, `--max_trace_step`) because they are useful for the next
  DAgger/recovery dataset if contact gating alone is not enough.

Validation:
- command:
  `PYTHONPATH=$DEX $EXT/venv/bin/python -m py_compile dextrah_lab/offline_dp_bc/ppo_bridge.py dextrah_lab/offline_dp_bc/make_policy_recovery_dataset.py dextrah_lab/offline_dp_bc/make_support_expansion_dataset.py`
- provider smoke:
  `ContactGatedPhaseProgressProvider(... close_support_distance_threshold=0.30, lift_gripper_width_threshold=0.06).summary()`
  returns valid phase bounds for the recovery8 dataset.

Next:
- Commit and deploy this patch to the l401 agent worktree.
- Relaunch a 32-env no-video eval with `PHASE_PROGRESS_MODE=contact_gated`,
  `PHASE_CLOSE_SUPPORT_DISTANCE_THRESHOLD=0.30`,
  `PHASE_LIFT_GRIPPER_WIDTH_THRESHOLD=0.06`, and the recovery8 epoch-200
  checkpoint. If it still fails, build a broader residual recovery dataset
  using the random-reset failure traces and the accepted multi-pose contact
  relabel data.
