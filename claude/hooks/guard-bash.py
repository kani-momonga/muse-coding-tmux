#!/usr/bin/env python3
"""PreToolUse hook for Bash (insurance for delegated Claude Code runs).

- Clearly dangerous commands -> deny
- Curated safe commands (repo-local git work, tests, typecheck, lint) -> allow
- Everything else -> no decision (normal prompt; visible/controllable via tmux)

Never raises: any parse problem falls through to the normal prompt flow.
"""
import json
import re
import sys

DENY_PATTERNS = [
    (r"\bgit\s+push\b.*(--force|-f\b)", "force push"),
    (r"\bgit\s+push\b.*\b(origin\s+)?(main|master)\b", "push to main/master"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-z]*f", "git clean -f"),
    (r"\bgit\s+checkout\s+--\s", "discarding changes via checkout --"),
    (r"\bgit\s+restore\s+(?!--staged)", "discarding changes via restore"),
    (r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r", "rm -rf"),
    (r"\bgh\s+pr\s+merge\b", "PR merge (operator's explicit signal required)"),
    (r"\bwrangler\s+deploy\b", "production deploy (explicit signal required)"),
    (r"\bsudo\b", "sudo"),
]

ALLOW_PATTERNS = [
    # read-only git
    r"\bgit\s+(status|diff|log|show|branch|remote|rev-parse|ls-files|blame|describe)\b",
    # repo-local git writes (branch creation, staging, committing, feature push)
    r"\bgit\s+(add|commit|switch|checkout|fetch|pull|stash|merge|rebase|tag|mv|restore\s+--staged)\b",
    r"\bgit\s+push\s+origin\s+(?!main\b|master\b)[A-Za-z0-9._/-]+",
    r"\bgit\s+push\s+-u\s+origin\s+(?!main\b|master\b)[A-Za-z0-9._/-]+",
    # tests / typecheck / lint / local tooling
    r"\b(pnpm|npm)\s+(test|run|exec|install|ci)\b",
    r"\bnpx\s+(vitest|tsc|eslint|jest|tsx|prisma)\b",
    r"\bnode\s+(scripts|node_modules)/",
    r"\bnode_modules/\.bin/(vitest|tsc|eslint|jest)\b",
    r"\bphp\s+(-l|vendor/bin/phpunit)\b",
    r"\b(vitest|jest|pytest)\b",
    # read-only shell inspection
    r"^\s*(ls|cat|head|tail|grep|rg|find|wc|echo|pwd|which|date)\b",
]


def split_commands(command: str):
    """Split a compound command so each segment is judged on its own."""
    parts = re.split(r"\s*(?:&&|\|\||;|\|)\s*", command)
    return [p.strip() for p in parts if p.strip()]


def decide(command: str):
    segments = split_commands(command)
    if not segments:
        return None
    # Any denied segment denies the whole command.
    for seg in segments:
        for pattern, why in DENY_PATTERNS:
            if re.search(pattern, seg):
                return ("deny", f"Blocked by guard-bash hook: {why}")
    # Allow only if every segment is on the safe list.
    if all(any(re.search(p, seg) for p in ALLOW_PATTERNS) for seg in segments):
        return ("allow", "Curated safe command (guard-bash hook)")
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") != "Bash":
            return 0
        command = (payload.get("tool_input") or {}).get("command") or ""
        result = decide(command)
        if result is None:
            return 0
        decision, reason = result
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
