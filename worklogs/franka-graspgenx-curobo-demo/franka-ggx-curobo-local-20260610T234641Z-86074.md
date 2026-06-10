# Worklog - franka-graspgenx-curobo-demo / franka-ggx-curobo-local-20260610T234641Z-86074

- repo: /home/lzha/code/DEXTRAH
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- created: 2026-06-10T23:46:42Z

## 2026-06-10T23:46:42Z - Local workspace isolation

Goal:
- Continue Franka star GraspGenX/cuRobo demo without sharing the canonical checkout.

Change:
- Created agent-owned worktree and moved the kinematic playback planner diff here.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- changed_files: dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py

Command / Job:
- command: stopped local uv/Docker probes before isolating; no active demo process remains.
- job_id: n/a

Result:
- status: paused
- key evidence: source work will resume from this worktree; shared checkout retains only pre-existing dirty files.

Next:
- Run all future planner/render commands from the agent-owned worktree and namespaced output directories.

## 2026-06-10T23:53:40Z - Local dependency setup and planner fallback

Goal:
- Prepare isolated local planner execution for the Franka star GraspGenX/cuRobo demo.

Change:
- Added kinematic playback support to the DEXTRAH planner so local execution can export a GraspGenX/cuRobo trajectory without requiring Newton.
- The kinematic trajectory augments GraspGenX's JSON with an `object_poses.object` track attached to the Franka tool after close.

Version Control:
- agent_id: franka-ggx-curobo-local-20260610T234641Z-86074
- worktree: /home/lzha/code/.codex-worktrees/DEXTRAH/franka-ggx-curobo-local-20260610T234641Z-86074
- branch: codex/franka-graspgenx-curobo-demo/franka-ggx-curobo-local-20260610T234641Z-86074
- base_commit: b684a9649e046124119bf4b965007f5bad2477ba
- implementation_commit: pending
- changed_files: dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py

Command / Job:
- command: `UV_LINK_MODE=copy uv sync` in the agent-owned GraspGenX worktree
- command: `uv pip install --python <agent-graspgenx>/.venv/bin/python -e <agent-curobo> --no-deps`
- command: `uv pip install --python <agent-graspgenx>/.venv/bin/python 'cuda-core[cu12]<1.0' 'nvidia-cuda-runtime-cu12>=12' 'warp-lang>=0.10.0' numpy-quaternion importlib_resources`
- job_id: n/a
- run_dir: n/a

Result:
- status: passed
- key evidence: imports resolved from isolated GraspGenX and cuRobo worktrees; `torch.cuda.is_available()` returned true with 2 devices.
- validation: `python3 -m py_compile dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py dextrah_lab/scene_scripts/render_star_kitting_env.py`
- validation: `bash -n cluster/sbatch_plan_franka_star_graspgenx_curobo.sh cluster/sbatch_render_star_kitting_env.sh`
- validation: `git diff --check`

Next:
- Commit the DEXTRAH fallback and launch a bounded local planner smoke from the isolated worktree.
