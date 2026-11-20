#!/bin/bash
# Backward-compatible wrapper: claude-tmux.sh start <session> <workdir> [args]
# maps to agent-tmux.sh start claude <session> <workdir> [args].
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "start" ]; then
  shift
  exec "$DIR/agent-tmux.sh" start claude "$@"
fi
exec "$DIR/agent-tmux.sh" "$@"
