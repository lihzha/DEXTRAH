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
