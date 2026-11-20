#!/usr/bin/env python3
"""PostToolUse hook: append one JSONL line per tool call to the run log.
Stop hook mode (--stop): record a completion event + per-session marker.

Log dir: ~/agent-runs/ (override with AGENT_RUNS_DIR).
Never raises and never blocks the session.
"""
import json
import os
import sys
from datetime import datetime, timezone

LOG_DIR = os.environ.get(
    "AGENT_RUNS_DIR", os.path.expanduser("~/agent-runs")
)


def append_line(filename: str, record: dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, filename), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        base = {
            "ts": now,
            "session_id": payload.get("session_id"),
            "cwd": payload.get("cwd"),
        }
        if "--stop" in sys.argv:
            record = {**base, "event": "stop"}
            append_line("stop-events.log", record)
            append_line("last-stop.json", record)  # append-only history; tail -1 = latest
        else:
            record = {**base, "tool": payload.get("tool_name")}
            append_line("tool-calls.log", record)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
