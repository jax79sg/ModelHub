#!/usr/bin/env python3
"""Stop work that has drifted away from the AI-DLC loop.

A project hook (PreToolUse). It blocks, with a message that says what to do, any tool call
that changes the project or sends work out, unless the AI-DLC engine has been asked what comes
next recently:

  - shell commands that commit, push, merge, open or merge a pull request, or call the
    GitHub merge API;
  - writes to the project's source, test, deploy, documentation and workflow folders.

"Asked recently" means the active intent's ``.aidlc-engine/engine-touch`` marker (touched by every
advancing ``aidlc engine orchestrate next`` and ``report``) is newer than ``MAX_AGE_MINUTES``.
Commands that start with ``aidlc`` are always allowed, since they are how the loop is kept.
With no AI-DLC workflow in the folder, nothing is blocked.

Why it exists: in this project, work carried on for days after a plan was approved without a
single ``next`` or ``report`` (see docs/ai-dlc-working-agreement.md).
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import time

MAX_AGE_MINUTES = float(os.environ.get("AIDLC_LOOP_MAX_AGE_MINUTES", "30"))
GUARDED_SHELL = re.compile(
    r"(^|[;&|(\s])(git\s+(commit|push|merge|rebase|reset\s+--hard|cherry-pick|tag)\b"
    r"|gh\s+pr\s+(create|merge|edit|close|ready)\b"
    r"|gh\s+api\b[^\n]*(merge|-X\s*(PUT|POST|PATCH|DELETE)))"
)
GUARDED_DIRS = (
    "src/",
    "server/",
    "web/",
    "deploy/",
    "tests/",
    "docs/",
    ".github/",
    "tools/",
    "packaging/",
    "README.md",
    "pyproject.toml",
)


def project_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def last_engine_call(root: str) -> float | None:
    """Newest modification time of any intent's engine-touch marker, or None if there is none.

    The engine touches it on every advancing ``next`` or ``report``; a read-only call such as
    ``aidlc engine status`` does not, so it cannot stand in for following the loop."""
    pattern = os.path.join(
        root, "aidlc", "spaces", "*", "intents", "*", ".aidlc-engine", "engine-touch"
    )
    times = [os.path.getmtime(p) for p in glob.glob(pattern)]
    return max(times) if times else None


def guarded(tool: str, tool_input: dict, root: str) -> str | None:
    """Why this call needs a recent engine call, or None when it does not."""
    if tool == "Bash":
        command = str(tool_input.get("command", "")).strip()
        if command.startswith("aidlc "):
            return None
        if GUARDED_SHELL.search(command):
            return "a command that commits, pushes, merges or changes a pull request"
        return None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(tool_input.get("file_path", tool_input.get("notebook_path", "")))
        relative = os.path.relpath(path, root) if os.path.isabs(path) else path
        if relative.startswith(("aidlc/", ".claude/")):
            return None  # the framework's own records and settings
        if relative.startswith(GUARDED_DIRS):
            return f"a change to {relative}"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    root = project_root()
    reason = guarded(str(event.get("tool_name", "")), event.get("tool_input") or {}, root)
    if reason is None:
        return 0
    last = last_engine_call(root)
    if last is None:
        return 0  # no AI-DLC workflow here
    age = (time.time() - last) / 60
    if age <= MAX_AGE_MINUTES:
        return 0
    sys.stderr.write(
        f"Blocked: {reason}, but the AI-DLC engine was last asked what comes next {age:.0f} minutes "
        f"ago (limit {MAX_AGE_MINUTES:.0f}). Run `aidlc engine orchestrate next --resume`, do what "
        "its directive says, report the result with `aidlc engine orchestrate report`, then try "
        "again. If the work is outside the workflow, tell the person and ask first.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
