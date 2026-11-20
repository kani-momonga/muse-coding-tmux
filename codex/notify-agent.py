#!/usr/bin/env python3
"""Codex `notify` target: record turn-completion events as JSONL.

Codex invokes the notify program with one JSON argument, e.g.
{"type": "agent-turn-complete", "thread-id": "...", ...}.
Events are appended to $AGENT_RUNS_DIR/codex-events.log
(default ~/agent-runs). Never raises.
"""
import json
import os
import sys
from datetime import datetime, timezone

LOG_DIR = os.environ.get(
    "AGENT_RUNS_DIR", os.path.expanduser("~/agent-runs")
)


def main() -> int:
    try:
        payload = json.loads(sys.argv[-1]) if len(sys.argv) > 1 else {}
        record = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "agent": "codex",
            "event": payload.get("type"),
            "thread_id": payload.get("thread-id"),
            "cwd": payload.get("cwd"),
        }
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "codex-events.log"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
