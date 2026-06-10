#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_ggx_star
#SBATCH --partition=batch
#SBATCH --time=0-01:00:00
#SBATCH --mem=80G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/ggx_star_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/graspgenx_ngc2503_base.sqsh}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
GRASPGENX_NFS="${GRASPGENX_NFS:-$NFS_ROOT/src/graspgenx}"
CUROBO_NFS="${CUROBO_NFS:-$NFS_ROOT/src/curobo}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
ENV_NFS="${ENV_NFS:-$NFS_ROOT/envs}"
VENV_NAME="${VENV_NAME:-graspgenx-py312}"
PIP_CACHE_NFS="${PIP_CACHE_NFS:-$NFS_ROOT/cache/pip}"
RUN_NAME="${RUN_NAME:-franka_star_ggx_curobo_${SLURM_JOB_ID:-manual}}"
OUT_SUBDIR="${OUT_SUBDIR:-graspgenx_franka_star}"
OUT_DIR="$RESULTS_NFS/$OUT_SUBDIR/$RUN_NAME"

if [ ! -f "$IMAGE" ]; then
  echo "Missing GraspGenX base image: $IMAGE"
  exit 2
fi
if [ ! -x "$ENV_NFS/$VENV_NAME/bin/python" ]; then
  echo "Missing GraspGenX venv python: $ENV_NFS/$VENV_NAME/bin/python"
  exit 2
fi
if [ ! -f "$GRASPGENX_NFS/end2end/e2e_grasp_demo.py" ]; then
  echo "Missing GraspGenX checkout: $GRASPGENX_NFS"
  exit 2
fi
if [ ! -f "$CUROBO_NFS/curobo/content/configs/robot/franka.yml" ]; then
  echo "Missing cuRobo checkout/config: $CUROBO_NFS"
  exit 2
fi

mkdir -p "$OUT_DIR" "$NFS_ROOT/slurm_logs/dextrah" "$PIP_CACHE_NFS"

echo "Planning DEXTRAH Franka star grasp with GraspGenX + cuRobo"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-manual}"
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"
echo "CODE_NFS=$CODE_NFS"
echo "GRASPGENX_NFS=$GRASPGENX_NFS"
echo "CUROBO_NFS=$CUROBO_NFS"
echo "VENV=$ENV_NFS/$VENV_NAME"
echo "RUN_NAME=$RUN_NAME"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$GRASPGENX_NFS":/graspgenx,"$CUROBO_NFS":/curobo,"$RESULTS_NFS":/results,"$ENV_NFS":/envs,"$PIP_CACHE_NFS":/root/.cache/pip \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1,PYOPENGL_PLATFORM=egl,PYGLET_HEADLESS=true,EGL_PLATFORM=surfaceless,HYDRA_FULL_ERROR=1,PYTHONFAULTHANDLER=1,GRASPGENX_ROOT=/graspgenx,GRASPGENX_CUROBO_DIR=/curobo \
  bash -lc "
    set -euxo pipefail
    export VIRTUAL_ENV=/envs/$VENV_NAME
    export PATH=/envs/$VENV_NAME/bin:\$PATH
    export PYTHONPATH=/code:/graspgenx:/graspgenx/end2end:\${PYTHONPATH:-}
    cd /code

    python - <<'PY'
import sys
import torch
import graspgenx
import curobo
print('python', sys.version)
print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.device_count())
print('graspgenx', getattr(graspgenx, '__file__', 'unknown'))
print('curobo', getattr(curobo, '__file__', 'unknown'))
PY

    python dextrah_lab/scene_scripts/plan_franka_star_graspgenx_curobo.py \
      --output_dir /results/$OUT_SUBDIR \
      --run_name \"$RUN_NAME\" \
      --graspgenx_root /graspgenx \
      --curobo_root /curobo \
      --seed \"${SEED:-0}\" \
      --num_grasps \"${NUM_GRASPS:-200}\" \
      --topk \"${TOPK:-80}\" \
      --grasp_threshold \"${GRASP_THRESHOLD:-0.7}\" \
      --grasp_planner \"${GRASP_PLANNER:-graspmoe}\" \
      --moe_obb_density \"${MOE_OBB_DENSITY:-dense}\" \
      --max_plan_attempts \"${MAX_PLAN_ATTEMPTS:-80}\" \
      \${RANK_GRASPS_BY_CONFIDENCE:+--rank_grasps_by_confidence} \
      --sim_fps \"${SIM_FPS:-60}\" \
      --sim_dt \"${SIM_DT:-0.001}\" \
      --settle_frames \"${SETTLE_FRAMES:-30}\" \
      --object_mass \"${OBJECT_MASS:-0.05}\" \
      --object_mu \"${OBJECT_MU:-10.0}\" \
      --finger_mu \"${FINGER_MU:-3.0}\" \
      --hold_frames \"${HOLD_FRAMES:-60}\" \
      --hold_after_close_frames \"${HOLD_AFTER_CLOSE_FRAMES:-90}\" \
      --close_frames \"${CLOSE_FRAMES:-30}\" \
      --star_outer_radius \"${STAR_OUTER_RADIUS:-0.032}\" \
      --star_inner_radius \"${STAR_INNER_RADIUS:-0.0145}\" \
      --star_thickness \"${STAR_THICKNESS:-0.040}\" \
      --star_start_yaw_deg \"${STAR_START_YAW_DEG:--24.0}\" \
      --fixture_yaw_deg \"${FIXTURE_YAW_DEG:-18.0}\" \
      --fixture_size_x \"${FIXTURE_SIZE_X:-0.18}\" \
      --fixture_size_y \"${FIXTURE_SIZE_Y:-0.18}\" \
      --fixture_thickness \"${FIXTURE_THICKNESS:-0.060}\" \
      --fixture_clearance \"${FIXTURE_CLEARANCE:-0.006}\" \
      --table_center_x \"${TABLE_CENTER_X:--0.72}\" \
      --table_short_x \"${TABLE_SHORT_X:-0.90}\" \
      --table_long_y \"${TABLE_LONG_Y:-1.32}\" \
      --table_height \"${TABLE_HEIGHT:-0.72}\" \
      --table_top_thickness \"${TABLE_TOP_THICKNESS:-0.052}\" \
      --pickup_y \"${PICKUP_Y:--0.26}\" \
      --fixture_y \"${FIXTURE_Y:-0.26}\" \
      --robot_base_z \"${ROBOT_BASE_Z:-0.50}\" \
      --robot_yaw_deg \"${ROBOT_YAW_DEG:-180.0}\"
  "

echo "Done: $OUT_DIR"
echo "Trajectory: $OUT_DIR/trajectory.json"
