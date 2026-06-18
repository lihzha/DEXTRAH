#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Prepare and launch the neutral table-clutter-removal Codex agent fleet.

Default behavior is --dry-run: generate per-agent prompts/runners and print the
tmux commands without starting agents.

Usage:
  agents/launch/launch_table_clutter_removal_agents_tmux.sh [--dry-run|--launch] [--prepare-worktrees] [--attach] [--session NAME]

Environment overrides:
  ROOT            Canonical DEXTRAH repo path.
  WORKTREE_ROOT   Local agent worktree root.
  REMOTE_ROOT     a1001 remote agent worktree root.
  BASE_REF        Ref used when preparing new agent worktrees. Default: HEAD.
  CODEX_BIN       Codex CLI binary. Default: codex
  SANDBOX         Codex sandbox. Default: danger-full-access
  APPROVAL        Codex approval policy. Default: never
  MODEL           Optional Codex model name.

Examples:
  agents/launch/launch_table_clutter_removal_agents_tmux.sh --prepare-worktrees --dry-run
  agents/launch/launch_table_clutter_removal_agents_tmux.sh --prepare-worktrees --launch
  agents/launch/launch_table_clutter_removal_agents_tmux.sh --launch --attach
USAGE
}

action="dry-run"
attach=0
prepare_worktrees=0
session="${SESSION:-table-clutter-removal-agents}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      action="dry-run"
      shift
      ;;
    --launch)
      action="launch"
      shift
      ;;
    --prepare-worktrees)
      prepare_worktrees=1
      shift
      ;;
    --attach)
      attach=1
      shift
      ;;
    --session)
      session="${2:?missing session name}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

root="${ROOT:-/home/lzha/code/DEXTRAH}"
worktree_root="${WORKTREE_ROOT:-/home/lzha/code/DEXTRAH-worktrees}"
remote_root="${REMOTE_ROOT:-/lustre/fsw/portfolios/nvr/users/lzha/src/worktrees/DEXTRAH}"
base_ref="${BASE_REF:-HEAD}"
prompt_template="${PROMPT_TEMPLATE:-$root/agents/launch/table_clutter_removal_agent_prompt.md}"
prompt_dir="${PROMPT_DIR:-$root/agents/launch/generated/table-clutter-removal}"
runner_dir="$prompt_dir/runners"
log_dir="${LOG_DIR:-$root/agents/logs/table-clutter-removal}"
codex_bin="${CODEX_BIN:-codex}"
sandbox="${SANDBOX:-danger-full-access}"
approval="${APPROVAL:-never}"
model="${MODEL:-}"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "missing required file: $1" >&2
    exit 1
  fi
}

require_dir() {
  if [[ ! -d "$1" ]]; then
    echo "missing required directory: $1" >&2
    exit 1
  fi
}

ensure_clean_root() {
  local status
  status="$(git -C "$root" status --porcelain)"
  if [[ -n "$status" ]]; then
    echo "canonical checkout is dirty; commit or stash before preparing worktrees:" >&2
    echo "$status" >&2
    exit 1
  fi
}

ensure_worktree() {
  local branch="$1"
  local worktree="$2"

  if [[ -d "$worktree/.git" || -f "$worktree/.git" ]]; then
    return 0
  fi
  if [[ -e "$worktree" ]]; then
    echo "path exists but is not a git worktree: $worktree" >&2
    exit 1
  fi

  if git -C "$root" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$root" worktree add "$worktree" "$branch"
  else
    git -C "$root" worktree add -b "$branch" "$worktree" "$base_ref"
  fi
}

require_launchable_worktree() {
  local agent="$1"
  local wt="$2"
  local allowed_report="agents/reports/$agent.md"
  local status
  status="$(git -C "$wt" status --porcelain)"
  [[ -z "$status" ]] && return 0

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    path="${line:3}"
    if [[ "$path" != "$allowed_report" ]]; then
      echo "worktree has non-report changes: $wt" >&2
      echo "$status" >&2
      exit 1
    fi
  done <<< "$status"

  echo "allowing existing agent report in $wt:" >&2
  echo "$status" >&2
}

render_prompt() {
  local agent="$1"
  local branch="$2"
  local worktree="$3"
  local remote_worktree="$4"
  local out="$5"

  sed \
    -e "s|\\[CODEX_AGENT_ID\\]|$agent|g" \
    -e "s|\\[BRANCH_NAME\\]|$branch|g" \
    -e "s|\\[LOCAL_WORKTREE\\]|$worktree|g" \
    -e "s|\\[REMOTE_CODE_NFS\\]|$remote_worktree|g" \
    "$prompt_template" > "$out"
}

write_runner() {
  local agent="$1"
  local worktree="$2"
  local remote_worktree="$3"
  local prompt="$4"
  local log="$5"
  local runner="$6"

  cat > "$runner" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export CODEX_AGENT_ID="$agent"
export CODEX_REMOTE_WORKTREE="$remote_worktree"
mkdir -p "$(dirname "$log")"
cd "$worktree"
EOF

  if [[ -n "$model" ]]; then
    printf '%q -s %q -a %q -m %q exec -C %q - < %q 2>&1 | tee %q\n' \
      "$codex_bin" "$sandbox" "$approval" "$model" "$worktree" "$prompt" "$log" >> "$runner"
  else
    printf '%q -s %q -a %q exec -C %q - < %q 2>&1 | tee %q\n' \
      "$codex_bin" "$sandbox" "$approval" "$worktree" "$prompt" "$log" >> "$runner"
  fi

  chmod +x "$runner"
}

require_dir "$root"
require_file "$prompt_template"
mkdir -p "$worktree_root" "$prompt_dir" "$runner_dir" "$log_dir"

if ! command -v "$codex_bin" >/dev/null 2>&1; then
  echo "Codex binary not found: $codex_bin" >&2
  exit 1
fi

if [[ "$prepare_worktrees" -eq 1 ]]; then
  ensure_clean_root
fi

if [[ "$action" == "launch" ]]; then
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required for --launch" >&2
    exit 1
  fi
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "tmux session already exists: $session" >&2
    echo "Attach with: tmux attach -t $session" >&2
    exit 1
  fi
fi

declare -a runners=()

for i in 01 02 03 04; do
  agent="clutter-removal-a$i"
  branch="agent/clutter-removal/a$i"
  worktree="$worktree_root/$agent"
  remote_worktree="$remote_root/$agent"
  prompt="$prompt_dir/$agent.md"
  runner="$runner_dir/$agent.sh"
  log="$log_dir/$agent.log"

  if [[ "$prepare_worktrees" -eq 1 ]]; then
    ensure_worktree "$branch" "$worktree"
  else
    require_dir "$worktree"
  fi

  require_file "$worktree/auto_research.md"
  require_file "$worktree/agents/launch/table_clutter_removal_agent_prompt.md"
  require_launchable_worktree "$agent" "$worktree"

  current_branch="$(git -C "$worktree" branch --show-current)"
  if [[ "$current_branch" != "$branch" ]]; then
    echo "unexpected branch for $worktree: $current_branch, expected $branch" >&2
    exit 1
  fi

  render_prompt "$agent" "$branch" "$worktree" "$remote_worktree" "$prompt"
  write_runner "$agent" "$worktree" "$remote_worktree" "$prompt" "$log" "$runner"
  runners+=("$runner")
done

echo "Generated prompts under: $prompt_dir"
echo "Generated runners under: $runner_dir"
echo "Logs will be written under: $log_dir"

if [[ "$action" == "dry-run" ]]; then
  echo
  echo "Dry run only. Commands that would be launched:"
  first=1
  for runner in "${runners[@]}"; do
    agent="$(basename "$runner" .sh)"
    if [[ "$first" -eq 1 ]]; then
      printf 'tmux new-session -d -s %q -n %q "bash %q"\n' "$session" "$agent" "$runner"
      first=0
    else
      printf 'tmux new-window -t %q -n %q "bash %q"\n' "$session" "$agent" "$runner"
    fi
  done
  echo
  echo "Launch with:"
  printf '  %q --launch\n' "$0"
  exit 0
fi

first=1
for runner in "${runners[@]}"; do
  agent="$(basename "$runner" .sh)"
  if [[ "$first" -eq 1 ]]; then
    tmux new-session -d -s "$session" -n "$agent" "bash '$runner'"
    first=0
  else
    tmux new-window -t "$session" -n "$agent" "bash '$runner'"
  fi
done

echo "Started tmux session: $session"
echo "Attach with: tmux attach -t $session"
echo "Kill all agents with: tmux kill-session -t $session"

if [[ "$attach" -eq 1 ]]; then
  tmux attach -t "$session"
fi
