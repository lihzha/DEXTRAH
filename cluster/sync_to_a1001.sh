#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-a1001}"
NFS_ROOT="${NFS_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha}"
REMOTE_CODE_DIR="${REMOTE_CODE_DIR:-$NFS_ROOT/src/DEXTRAH}"
REMOTE_FABRICS_DIR="${REMOTE_FABRICS_DIR:-$NFS_ROOT/src/FABRICS}"
REMOTE_ISAACLAB_DIR="${REMOTE_ISAACLAB_DIR:-$NFS_ROOT/src/IsaacLab-v2.2.1}"
ISAACLAB_REF="${ISAACLAB_REF:-v2.2.1}"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/NVlabs/DEXTRAH.git}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
FABRICS_DIR="${FABRICS_DIR:-$(cd "$REPO_DIR/.." && pwd)/FABRICS}"

git_required() {
  if ! git -C "$REPO_DIR" "$@" >/dev/null 2>&1; then
    echo "git $* failed in $REPO_DIR" >&2
    exit 2
  fi
}

LOCAL_BRANCH="${LOCAL_BRANCH:-$(git -C "$REPO_DIR" branch --show-current)}"
if [ -z "$LOCAL_BRANCH" ]; then
  echo "Local checkout is detached; set LOCAL_BRANCH explicitly before syncing." >&2
  exit 2
fi
REMOTE_BRANCH="${REMOTE_BRANCH:-$LOCAL_BRANCH}"
LOCAL_HEAD="$(git -C "$REPO_DIR" rev-parse HEAD)"
ORIGIN_URL="${ORIGIN_URL:-$(git -C "$REPO_DIR" config --get remote.origin.url)}"
if [ -z "$ORIGIN_URL" ]; then
  echo "Local checkout has no origin remote." >&2
  exit 2
fi

if [ -n "$(git -C "$REPO_DIR" status --porcelain)" ]; then
  echo "Refusing to sync dirty local source. Commit and push first." >&2
  git -C "$REPO_DIR" status --short >&2
  exit 2
fi

REMOTE_HEAD="$(git -C "$REPO_DIR" ls-remote --heads origin "refs/heads/$REMOTE_BRANCH" | awk '{print $1}')"
if [ "$REMOTE_HEAD" != "$LOCAL_HEAD" ]; then
  echo "Refusing to sync because origin/$REMOTE_BRANCH is not local HEAD." >&2
  echo "local HEAD: $LOCAL_HEAD" >&2
  echo "origin/$REMOTE_BRANCH: ${REMOTE_HEAD:-missing}" >&2
  echo "Push first: git push origin HEAD:$REMOTE_BRANCH" >&2
  exit 2
fi

FABRICS_URL="${FABRICS_URL:-https://github.com/NVlabs/FABRICS.git}"
FABRICS_BRANCH="${FABRICS_BRANCH:-main}"
if [ -d "$FABRICS_DIR/.git" ]; then
  FABRICS_URL="$(git -C "$FABRICS_DIR" config --get remote.origin.url || printf '%s' "$FABRICS_URL")"
  local_fabrics_branch="$(git -C "$FABRICS_DIR" branch --show-current || true)"
  if [ -n "$local_fabrics_branch" ]; then
    FABRICS_BRANCH="${FABRICS_BRANCH:-$local_fabrics_branch}"
  fi
fi

ssh "$REMOTE" \
  "NFS_ROOT='$NFS_ROOT' REMOTE_CODE_DIR='$REMOTE_CODE_DIR' REMOTE_FABRICS_DIR='$REMOTE_FABRICS_DIR' REMOTE_ISAACLAB_DIR='$REMOTE_ISAACLAB_DIR' ISAACLAB_REF='$ISAACLAB_REF' ORIGIN_URL='$ORIGIN_URL' UPSTREAM_URL='$UPSTREAM_URL' REMOTE_BRANCH='$REMOTE_BRANCH' LOCAL_HEAD='$LOCAL_HEAD' FABRICS_URL='$FABRICS_URL' FABRICS_BRANCH='$FABRICS_BRANCH' bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

mkdir -p \
  "$(dirname "$REMOTE_CODE_DIR")" \
  "$(dirname "$REMOTE_FABRICS_DIR")" \
  "$NFS_ROOT/cache" "$NFS_ROOT/envs" "$NFS_ROOT/results/dextrah" \
  "$NFS_ROOT/slurm_logs/dextrah" "$NFS_ROOT/isaac_cache"

if [ ! -d "$REMOTE_CODE_DIR/.git" ]; then
  if [ -e "$REMOTE_CODE_DIR" ]; then
    backup="${REMOTE_CODE_DIR}.pre_git_sync_$(date +%Y%m%d_%H%M%S)"
    echo "Moving existing non-git checkout to $backup"
    mv "$REMOTE_CODE_DIR" "$backup"
  fi
  git clone --branch "$REMOTE_BRANCH" "$ORIGIN_URL" "$REMOTE_CODE_DIR"
fi

cd "$REMOTE_CODE_DIR"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$ORIGIN_URL"
else
  git remote add origin "$ORIGIN_URL"
fi
if git remote get-url upstream >/dev/null 2>&1; then
  git remote set-url upstream "$UPSTREAM_URL"
else
  git remote add upstream "$UPSTREAM_URL"
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Remote checkout is dirty; preserving source changes in a stash before Git sync."
  git stash push -u -m "pre-git-sync-$(date +%Y%m%d_%H%M%S)" -- . ':!cluster_results' || true
fi

git fetch origin "$REMOTE_BRANCH"
if git rev-parse --verify "$REMOTE_BRANCH" >/dev/null 2>&1; then
  git checkout "$REMOTE_BRANCH"
else
  git checkout -b "$REMOTE_BRANCH" "origin/$REMOTE_BRANCH"
fi
git pull --ff-only origin "$REMOTE_BRANCH"
remote_head="$(git rev-parse HEAD)"
if [ "$remote_head" != "$LOCAL_HEAD" ]; then
  echo "Remote HEAD mismatch after pull: $remote_head != $LOCAL_HEAD" >&2
  exit 2
fi
if git lfs version >/dev/null 2>&1; then
  git lfs install --local
  git lfs pull
else
  echo "Warning: git-lfs is not installed on $(hostname); skipping git lfs pull." >&2
fi

if [ ! -d "$REMOTE_FABRICS_DIR/.git" ]; then
  if [ -e "$REMOTE_FABRICS_DIR" ]; then
    backup="${REMOTE_FABRICS_DIR}.pre_git_sync_$(date +%Y%m%d_%H%M%S)"
    echo "Moving existing non-git FABRICS checkout to $backup"
    mv "$REMOTE_FABRICS_DIR" "$backup"
  fi
  git clone --branch "$FABRICS_BRANCH" "$FABRICS_URL" "$REMOTE_FABRICS_DIR"
else
  cd "$REMOTE_FABRICS_DIR"
  git remote set-url origin "$FABRICS_URL"
  if [ -n "$(git status --porcelain)" ]; then
    echo "FABRICS checkout is dirty; leaving it untouched." >&2
  else
    git fetch origin "$FABRICS_BRANCH"
    git checkout "$FABRICS_BRANCH"
    git pull --ff-only origin "$FABRICS_BRANCH"
  fi
  if git lfs version >/dev/null 2>&1; then
    git lfs install --local
    git lfs pull
  fi
fi

if [ ! -d "$REMOTE_ISAACLAB_DIR/.git" ]; then
  rm -rf "$REMOTE_ISAACLAB_DIR"
  git clone --branch "$ISAACLAB_REF" --depth 1 https://github.com/isaac-sim/IsaacLab.git "$REMOTE_ISAACLAB_DIR"
else
  cd "$REMOTE_ISAACLAB_DIR"
  git fetch --tags --depth 1 origin "$ISAACLAB_REF"
  git checkout "$ISAACLAB_REF"
fi

cd "$REMOTE_CODE_DIR"
echo "Remote DEXTRAH branch: $(git branch --show-current)"
echo "Remote DEXTRAH commit: $(git rev-parse HEAD)"
echo "Remote DEXTRAH status:"
git status --short
REMOTE_SCRIPT

echo "Synced DEXTRAH via Git: $LOCAL_HEAD -> $REMOTE:$REMOTE_CODE_DIR ($REMOTE_BRANCH)"
echo "Prepared FABRICS via Git -> $REMOTE:$REMOTE_FABRICS_DIR"
echo "Prepared IsaacLab $ISAACLAB_REF -> $REMOTE:$REMOTE_ISAACLAB_DIR"
