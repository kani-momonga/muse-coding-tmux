#!/bin/bash
# Drive an interactive coding agent (Claude Code / Codex) inside tmux.
#
# Why: running agents with `-p` (print mode) hides approval prompts and
# progress. Inside tmux the session stays visible and controllable:
# you (or an orchestrating agent) can watch the pane, answer prompts with
# send-keys, and keep a full pane log.
#
# Usage:
#   agent-tmux.sh start <claude|codex> <session> <workdir> [extra agent args...]
#       Start the agent in a detached tmux session rooted at <workdir>.
#       Pane output is logged to $AGENT_RUNS_DIR/<session>.pane.log
#       - claude: --permission-mode acceptEdits (plus user-level hooks, see claude/)
#       - codex:  --ask-for-approval on-request --sandbox workspace-write
#                 (turn completion is recorded via the `notify` config, see codex/)
#   agent-tmux.sh send <session> <brief-file>
#       Paste the brief file into the session and submit it.
#   agent-tmux.sh peek <session> [lines]
#       Print the last N lines (default 60) of the pane.
#   agent-tmux.sh keys <session> <key> [key...]
#       Send raw keys (e.g. Enter, Down, Escape, C-c) to answer prompts.
#   agent-tmux.sh list
#   agent-tmux.sh kill <session>
#
# Environment:
#   AGENT_RUNS_DIR  log directory (default: ~/agent-runs)
#   CLAUDE_BIN      Claude Code binary (default: ~/.local/bin/claude, else PATH)
#   CODEX_BIN       Codex binary       (default: ~/.local/bin/codex, else PATH)
set -u
RUNS_DIR="${AGENT_RUNS_DIR:-$HOME/agent-runs}"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
CODEX_BIN="${CODEX_BIN:-$HOME/.local/bin/codex}"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$(command -v claude || true)"
[ -x "$CODEX_BIN" ] || CODEX_BIN="$(command -v codex || true)"
mkdir -p "$RUNS_DIR"

cmd="${1:-}"; shift || true
case "$cmd" in
  start)
    agent="${1:?agent (claude|codex) required}"
    session="${2:?session name required}"
    workdir="${3:?workdir required}"
    shift 3
    if tmux has-session -t "$session" 2>/dev/null; then
      echo "session '$session' already exists" >&2; exit 1
    fi
    case "$agent" in
      claude) launch="$CLAUDE_BIN --permission-mode acceptEdits $*" ;;
      codex)  launch="$CODEX_BIN --ask-for-approval on-request --sandbox workspace-write $*" ;;
      *) echo "unknown agent: $agent" >&2; exit 2 ;;
    esac
    tmux new-session -d -s "$session" -c "$workdir" -x 220 -y 60
    tmux pipe-pane -t "$session" -o "cat >> $RUNS_DIR/$session.pane.log"
    tmux send-keys -t "$session" "$launch" Enter
    echo "started: $agent/$session (log: $RUNS_DIR/$session.pane.log)"
    ;;
  send)
    session="${1:?session required}"
    brief="${2:?brief file required}"
    tmux load-buffer -b brief "$brief"
    tmux paste-buffer -b brief -t "$session"
    sleep 1
    tmux send-keys -t "$session" Enter
    echo "sent brief: $brief -> $session"
    ;;
  peek)
    session="${1:?session required}"
    lines="${2:-60}"
    tmux capture-pane -t "$session" -p -S "-$lines"
    ;;
  keys)
    session="${1:?session required}"
    shift
    tmux send-keys -t "$session" "$@"
    ;;
  list)
    tmux list-sessions 2>/dev/null || echo "(no sessions)"
    ;;
  kill)
    session="${1:?session required}"
    tmux kill-session -t "$session"
    echo "killed: $session"
    ;;
  *)
    echo "usage: $0 {start|send|peek|keys|list|kill} ..." >&2
    exit 2
    ;;
esac
