# DEXTRAH Eval Videos - dextrah-eval-videos-20260611T102249

## 2026-06-11 10:22 PDT - Isolated eval setup

Goal:
- Generate validated rollout videos for the completed DEXTRAH Kuka Allegro teacher run `teacher_short_20260609_100021`.

Hypothesis:
- The existing `eval_rollout.py` video path can render deterministic one-env rollouts from the final teacher checkpoint if launched through a Kuka-specific A100 wrapper with the same core task overrides used by teacher training.

Change:
- Added `cluster/sbatch_eval_kuka_allegro_1gpu.sh` for 1-GPU Kuka Allegro checkpoint evaluation with video capture, parameterized source/results paths, camera pose, checkpoint, seed, and run name.

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249`
- worklog: `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- branch: `codex/dextrah-eval-videos/20260611T102249`
- base_commit: `d7ff3d0`
- implementation_commit: `ef4da5f`
- push/pull: pending
- changed_files: `cluster/sbatch_eval_kuka_allegro_1gpu.sh`, `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- remote_commit/status: pending

Command / Job:
- command: `bash -n cluster/sbatch_eval_kuka_allegro_1gpu.sh`; `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`
- job_id: pending
- run_dir: pending
- logs: pending
- artifacts: expected `metrics.json` and `videos/*.mp4`

Result:
- status: local validation passed
- metrics/artifacts: pending cluster launch
- key evidence: shell syntax check passed; evaluator Python compile passed

Analysis:
- The shared checkout is dirty and behind remote, so all edits and launches are isolated in this worktree. Eval will use the final checkpoint `last_dextrah_lstm_ep_20000_rew_673.2542.pth`.

Next:
- Run shell syntax checks, commit/push, deploy the exact commit to an agent-owned A100 worktree, then submit short video eval jobs.

## 2026-06-11 10:28 PDT - Oblique eval video launch

Goal:
- Produce a full-episode oblique-view MP4 and metrics JSON from the final `teacher_short_20260609_100021` checkpoint.

Hypothesis:
- A deterministic 1-env, 600-step rollout with ADR disabled will produce a stable video suitable for visual inspection while still loading the final teacher policy and Kuka Allegro task assets.

Change:
- No source change since `2f6a7ed`; launched the new Kuka eval wrapper from the agent-owned remote worktree.

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249`
- worklog: `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- branch: `codex/dextrah-eval-videos/20260611T102249`
- base_commit: `d7ff3d0`
- implementation_commit: `2f6a7ed181fb230584b3b24f0417a169ee4ed490`
- push/pull: pushed to GitHub and pushed over SSH into the remote A100 repo because the A100 login could not fetch GitHub with public-key auth
- changed_files: `cluster/sbatch_eval_kuka_allegro_1gpu.sh`, this worklog
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249` at `2f6a7ed181fb230584b3b24f0417a169ee4ed490`, detached clean

Command / Job:
- command: `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249,RUN_NAME=dextrah_eval_videos_20260611T102249_oblique,CHECKPOINT=/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_20000_rew_673.2542.pth,NUM_ENVS=1,NUM_STEPS=600,VIDEO_LENGTH=600,CAPTURE_VIDEO=True,USE_CUDA_GRAPH=False,ENABLE_ADR=False,SEED=42,VIDEO_NAME_PREFIX=kuka-allegro-teacher-ep20000-oblique,CAMERA_EYE_X=-1.15,CAMERA_EYE_Y=-0.80,CAMERA_EYE_Z=1.10,CAMERA_TARGET_X=-0.55,CAMERA_TARGET_Y=0.10,CAMERA_TARGET_Z=0.50 cluster/sbatch_eval_kuka_allegro_1gpu.sh`
- job_id: `28985403`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/dextrah_eval_videos_20260611T102249_oblique`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_kuka_allegro_28985403.out`
- artifacts: expected `metrics.json` and `videos/kuka-allegro-teacher-ep20000-oblique-step-0.mp4`

Result:
- status: submitted
- metrics/artifacts: pending
- key evidence: pending

Analysis:
- The first job is intentionally one view so runtime failures or camera issues can be corrected before launching companion views.

Next:
- Monitor queue/logs; if the video and metrics validate, launch an overhead companion view.

## 2026-06-11 10:32 PDT - Overhead success-focused eval launch

Goal:
- Produce a second validated MP4 from an overhead camera focused on the successful lift window.

Hypothesis:
- The same deterministic seed reaches success before the reset; shortening the rollout to 460 steps should produce a cleaner companion video that ends before the reset segment observed in the 600-step oblique rollout.

Change:
- No source change since `2f6a7ed`; launched a second view with overhead camera and `NUM_STEPS=460`.

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249`
- worklog: `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- branch: `codex/dextrah-eval-videos/20260611T102249`
- implementation_commit: `2f6a7ed181fb230584b3b24f0417a169ee4ed490`
- remote_commit/status: `/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249` at `2f6a7ed181fb230584b3b24f0417a169ee4ed490`, detached clean

Command / Job:
- command: `sbatch --parsable --export=ALL,CODE_NFS=/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249,RUN_NAME=dextrah_eval_videos_20260611T102249_overhead_success,CHECKPOINT=/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_20000_rew_673.2542.pth,NUM_ENVS=1,NUM_STEPS=460,VIDEO_LENGTH=460,CAPTURE_VIDEO=True,USE_CUDA_GRAPH=False,ENABLE_ADR=False,SEED=42,VIDEO_NAME_PREFIX=kuka-allegro-teacher-ep20000-overhead-success,CAMERA_EYE_X=-0.55,CAMERA_EYE_Y=0.10,CAMERA_EYE_Z=1.45,CAMERA_TARGET_X=-0.55,CAMERA_TARGET_Y=0.10,CAMERA_TARGET_Z=0.25 cluster/sbatch_eval_kuka_allegro_1gpu.sh`
- job_id: `28985459`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/dextrah_eval_videos_20260611T102249_overhead_success`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_kuka_allegro_28985459.out`
- artifacts: expected `metrics.json` and `videos/kuka-allegro-teacher-ep20000-overhead-success-step-0.mp4`

Result:
- status: submitted
- metrics/artifacts: pending
- key evidence: oblique job `28985403` completed `0:0`, produced 600-frame 1280x720 MP4, and showed valid middle/final frames; first frame was black renderer warmup

Analysis:
- The overhead clip should complement the oblique view and avoid the post-reset tail.

Next:
- Monitor job `28985459`; fetch and validate MP4/metrics after completion.

## 2026-06-11 10:37 PDT - Eval video validation complete

Goal:
- Validate generated eval videos, fetch artifacts locally, and leave no active Slurm work.

Hypothesis:
- The original cluster MP4s plus local trimmed review clips provide usable evaluation videos: the originals preserve the exact run output and metrics, while the trims remove the one-frame renderer warmup and stop before the reset tail.

Change:
- No source changes. Created local derived review clips from the fetched MP4s:
  - `cluster_results/a1002/dextrah_eval_videos_20260611T102249_review_clips/kuka-allegro-teacher-ep20000-oblique-success-trim.mp4`
  - `cluster_results/a1002/dextrah_eval_videos_20260611T102249_review_clips/kuka-allegro-teacher-ep20000-overhead-success-trim.mp4`

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- worktree: `/home/lzha/code/.codex-worktrees/DEXTRAH/dextrah-eval-videos-20260611T102249`
- worklog: `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- branch: `codex/dextrah-eval-videos/20260611T102249`
- implementation_commit: `2f6a7ed181fb230584b3b24f0417a169ee4ed490`
- push/pull: final worklog update pending commit/push
- changed_files: this worklog
- remote_commit/status: launch worktree stayed at `2f6a7ed181fb230584b3b24f0417a169ee4ed490`; no active jobs remain

Command / Job:
- command: `ffprobe` on original and trimmed MP4s; `ffmpeg` frame extraction and trim generation; `viz-open` on both trimmed clips
- job_id: `28985403` and `28985459`
- run_dir: `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/dextrah_eval_videos_20260611T102249_oblique`, `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/dextrah_eval_videos_20260611T102249_overhead_success`
- logs: `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_kuka_allegro_28985403.out`, `/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/eval_kuka_allegro_28985459.out`
- artifacts: original remote/local MP4s, metrics JSON files, validation frames, and local trimmed review clips

Result:
- status: passed with notes
- metrics/artifacts:
  - oblique original: 1280x720, 60 fps, 10.00 s, 600 frames, `done_count=1`, `success_rate_mean=0.6067`, `reward_mean=5.2958`
  - overhead original: 1280x720, 60 fps, 7.65 s, 459 frames, `done_count=1`, `success_rate_mean=0.6565`, `reward_mean=5.5745`
  - oblique trimmed review: 1280x720, 60 fps, 6.90 s, 414 frames
  - overhead trimmed review: 1280x720, 60 fps, 6.70 s, 402 frames
- key evidence: both jobs reached `COMPLETED 0:0`; first/middle/last trimmed frames are non-black and show approach, grasp, and object-in-hand lift; `squeue -u lzha` returned no jobs

Analysis:
- Original videos contain a one-frame black renderer warmup; this is removed from the local review clips. The environment logs missing `Walnut_Planks_BaseColor.png`, so the table renders gray, but robot/object motion and contact are clearly visible. Both original rollouts reset once after a successful hold window; trimmed clips focus on the useful successful segment.

Next:
- Stop. Optional later improvement: add a `--video_start_step` option to `eval_rollout.py` so cluster-produced originals can skip warmup frames without local trimming.

## 2026-06-11 10:42 PDT - Orchestrator merge handoff

Goal:
- Prepare this isolated implementation branch for merge by a separate orchestrator.

Change:
- No runtime or wrapper behavior changes after validation. Added this merge-prep handoff entry only.

Version Control:
- agent_id: dextrah-eval-videos-20260611T102249
- branch: `codex/dextrah-eval-videos/20260611T102249`
- base_commit: `d7ff3d0`
- merge_head_before_this_entry: `49b4eba04f7b02339b7d1b9b0d3d9e7b07c16ec0`
- changed_files_for_merge:
  - `cluster/sbatch_eval_kuka_allegro_1gpu.sh`
  - `worklogs/dextrah-eval-videos/dextrah-eval-videos-20260611T102249.md`
- generated_artifacts_not_committed:
  - local videos/metrics under `/home/lzha/code/cluster_results/a1002/dextrah_eval_videos_20260611T102249_*`
  - remote videos/metrics under `/lustre/fsw/portfolios/nvr/users/lzha/results/dextrah/evals/dextrah_eval_videos_20260611T102249_*`

Validation:
- `bash -n cluster/sbatch_eval_kuka_allegro_1gpu.sh`
- `python3 -m py_compile dextrah_lab/rl_games/eval_rollout.py`
- Slurm jobs `28985403` and `28985459` completed `0:0`
- `ffprobe` validated original and trimmed MP4 frame counts, durations, resolution, and FPS
- first/middle/last representative frames were visually inspected for both trimmed review clips
- `squeue -u lzha` returned no active jobs

Merge Notes:
- This branch is an implementation-agent branch. The orchestrator should merge or cherry-pick it from a clean integration worktree, not from this agent worktree.
- The only source behavior change is the new Kuka Allegro eval wrapper. It is parameterized with `CODE_NFS`, `RUN_NAME`, checkpoint, camera, seed, and runtime settings so it can launch from an isolated cluster worktree.
- The final videos are intentionally not committed to Git. Use the local `cluster_results/a1002/...` paths or remote `/lustre/.../results/dextrah/evals/...` paths for artifact review.
- Known visual caveat: the eval logs report missing `Walnut_Planks_BaseColor.png`, so the table renders gray; robot/object motion remains clear.

Next:
- Orchestrator can fetch `origin/codex/dextrah-eval-videos/20260611T102249`, inspect the two changed files, merge/cherry-pick, and summarize this owned worklog into shared `WORKLOG.md` if desired.
