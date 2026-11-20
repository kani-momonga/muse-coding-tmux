#!/bin/bash
# Install the tmux driver + hooks into their standard locations.
# Existing config files are never overwritten; snippets are printed instead.
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME/bin" "$HOME/.claude/hooks" "$HOME/.codex" "$HOME/agent-runs"
cp "$SRC/bin/agent-tmux.sh" "$SRC/bin/claude-tmux.sh" "$HOME/bin/"
chmod +x "$HOME/bin/agent-tmux.sh" "$HOME/bin/claude-tmux.sh"
cp "$SRC/claude/hooks/guard-bash.py" "$SRC/claude/hooks/log-tool.py" "$HOME/.claude/hooks/"
chmod +x "$HOME/.claude/hooks/"*.py
cp "$SRC/codex/notify-agent.py" "$HOME/.codex/"
chmod +x "$HOME/.codex/notify-agent.py"
echo "installed: ~/bin/agent-tmux.sh, ~/.claude/hooks/, ~/.codex/notify-agent.py"

if [ -f "$HOME/.claude/settings.json" ]; then
  echo
  echo "~/.claude/settings.json already exists. Merge the hooks block from:"
  echo "  $SRC/claude/settings.example.json"
else
  # Strip the _comment key and write as the initial settings file.
  python3 - "$SRC/claude/settings.example.json" "$HOME/.claude/settings.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
data.pop("_comment", None)
json.dump(data, open(sys.argv[2], "w"), indent=2, ensure_ascii=False)
print("wrote ~/.claude/settings.json from the example")
PY
fi

echo
echo "For Codex completion events, add this line to ~/.codex/config.toml"
echo "(top level, with your real home path):"
echo "  notify = [\"python3\", \"$HOME/.codex/notify-agent.py\"]"
echo
echo "Make sure ~/bin is on your PATH, then:"
echo "  agent-tmux.sh start claude mytask /path/to/repo"
