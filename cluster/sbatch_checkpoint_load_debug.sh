#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=nvr_lpr_rvp
#SBATCH --gpus-per-node=1
#SBATCH --job-name=dextrah_ckpt_debug
#SBATCH --partition=batch_singlenode,grizzly,polar,polar3,polar4,interactive_singlenode
#SBATCH --time=0-00:20:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=/lustre/fsw/portfolios/nvr/users/lzha/slurm_logs/dextrah/checkpoint_load_debug_%j.out

set -euo pipefail

NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
CODE_NFS="${CODE_NFS:-$NFS_ROOT/src/DEXTRAH}"
FABRICS_NFS="${FABRICS_NFS:-$NFS_ROOT/src/FABRICS}"
ISAACLAB_NFS="${ISAACLAB_NFS:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
IMAGE="${IMAGE:-$NFS_ROOT/cache/isaac_lab_2.2.0.sqsh}"
ENV_ROOT="${ENV_ROOT:-$NFS_ROOT/envs}"
ENV_NAME="${ENV_NAME:-dextrah-isaaclab}"
RESULTS_NFS="${RESULTS_NFS:-$NFS_ROOT/results/dextrah}"
CACHE_NFS="${CACHE_NFS:-$NFS_ROOT/isaac_cache}"
CHECKPOINT="${CHECKPOINT:-/results/logs/rl_games/dextrah_lstm/teacher_short_20260609_100021/nn/last_dextrah_lstm_ep_510_rew_176.34055.pth}"
CONCURRENT_LOADS="${CONCURRENT_LOADS:-8}"

mkdir -p "$NFS_ROOT/slurm_logs/dextrah" "$RESULTS_NFS/logs"

echo "Running DEXTRAH checkpoint load diagnostic"
echo "SLURM_JOB_ID=$SLURM_JOB_ID"
echo "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-unset}"
echo "CHECKPOINT=$CHECKPOINT"
echo "CONCURRENT_LOADS=$CONCURRENT_LOADS"

srun \
  --ntasks=1 \
  --container-image="$IMAGE" \
  --container-mounts=/dev/shm:/dev/shm,"$CODE_NFS":/code,"$FABRICS_NFS":/fabrics,"$ISAACLAB_NFS":/IsaacLab,"$ENV_ROOT":/envs,"$RESULTS_NFS":/results,"$CACHE_NFS/kit":/isaac-sim/kit/cache,"$CACHE_NFS/ov":/root/.cache/ov,"$CACHE_NFS/pip":/root/.cache/pip,"$CACHE_NFS/glcache":/root/.cache/nvidia/GLCache,"$CACHE_NFS/computecache":/root/.nv/ComputeCache,"$CACHE_NFS/omni_logs":/root/.nvidia-omniverse/logs,"$CACHE_NFS/carb_logs":/isaac-sim/kit/logs/Kit/Isaac-Sim,"$CACHE_NFS/data":/root/.local/share/ov/data,"$CACHE_NFS/documents":/root/Documents \
  --no-container-entrypoint \
  --container-remap-root \
  --container-writable \
  --export=ALL,PYTHONUNBUFFERED=1,TORCH_SHOW_CPP_STACKTRACES=1,ACCEPT_EULA=Y,PRIVACY_CONSENT=Y \
  bash -lc "
    set -euo pipefail
    export SITE='/envs/$ENV_NAME/site'
    export PYTHONPATH=\"\$SITE:/code:/fabrics/src\"
    for d in /IsaacLab/source/*; do
      if [ -d \"\$d\" ]; then
        export PYTHONPATH=\"\$d:\$PYTHONPATH\"
      fi
    done

    cd /code/dextrah_lab/rl_games
    mkdir -p /results/logs
    nvidia-smi || true

    export CHECKPOINT='$CHECKPOINT'
    export CONCURRENT_LOADS='$CONCURRENT_LOADS'

    /isaac-sim/python.sh - <<'PY'
import inspect
import os
import textwrap
import time
import traceback

import torch
from rl_games.algos_torch import torch_ext

path = os.environ['CHECKPOINT']
print('python_pid', os.getpid())
print('checkpoint', path)
print('exists', os.path.exists(path))
if os.path.exists(path):
    st = os.stat(path)
    print('size', st.st_size, 'mtime', st.st_mtime)
print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available(), 'device_count', torch.cuda.device_count())
print('safe_filesystem_op source:')
print(textwrap.indent(inspect.getsource(torch_ext.safe_filesystem_op), '  '))

def summarize_state(state):
    print('state_type', type(state))
    if isinstance(state, dict):
        print('keys', sorted(state.keys()))
        print('epoch', state.get('epoch'), 'frame', state.get('frame'))
        devices = {}
        stack = [state]
        seen = 0
        while stack and seen < 2000:
            item = stack.pop()
            seen += 1
            if isinstance(item, torch.Tensor):
                devices[str(item.device)] = devices.get(str(item.device), 0) + 1
            elif isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, (list, tuple)):
                stack.extend(item)
        print('sample_tensor_devices', devices)

for mode in ('cpu', 'default', 'rl_games'):
    print(f'LOAD_BEGIN {mode}', flush=True)
    try:
        start = time.time()
        if mode == 'cpu':
            state = torch.load(path, map_location='cpu', weights_only=False)
        elif mode == 'default':
            state = torch.load(path, weights_only=False)
        else:
            state = torch_ext.load_checkpoint(path)
        print(f'LOAD_OK {mode} seconds={time.time() - start:.3f}', flush=True)
        summarize_state(state)
        del state
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception as exc:
        print(f'LOAD_FAIL {mode} {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
PY

    /isaac-sim/python.sh - <<'PY'
from pathlib import Path

Path('/tmp/dextrah_load_worker.py').write_text(r'''
import os
import time
import traceback

import torch

path = os.environ['CHECKPOINT']
mode = os.environ.get('LOAD_MODE', 'cpu')
rank = os.environ.get('LOAD_RANK', '0')
try:
    start = time.time()
    if mode == 'cpu':
        state = torch.load(path, map_location='cpu', weights_only=False)
    else:
        state = torch.load(path, weights_only=False)
    epoch = state.get('epoch') if isinstance(state, dict) else None
    print(f'WORKER_OK rank={rank} mode={mode} epoch={epoch} seconds={time.time() - start:.3f}', flush=True)
except Exception as exc:
    print(f'WORKER_FAIL rank={rank} mode={mode} {type(exc).__name__}: {exc}', flush=True)
    traceback.print_exc()
    raise
''')
PY

    for mode in cpu default; do
      echo \"CONCURRENT_BEGIN \$mode\"
      set +e
      pids=()
      for rank in \$(seq 0 \$((CONCURRENT_LOADS - 1))); do
        LOAD_MODE=\"\$mode\" LOAD_RANK=\"\$rank\" /isaac-sim/python.sh /tmp/dextrah_load_worker.py &
        pids+=(\"\$!\")
      done
      failed=0
      for pid in \"\${pids[@]}\"; do
        wait \"\$pid\" || failed=1
      done
      set -e
      echo \"CONCURRENT_DONE \$mode failed=\$failed\"
    done
  "
