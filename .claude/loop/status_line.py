#!/usr/bin/env python3
"""The AI-DLC status line, plus how long ago the engine was last asked what comes next.

Wraps ``aidlc engine statusline`` (which shows stage and unit). The person can see drift at a
glance: a warning appears when the engine has not been asked for longer than the loop guard
allows.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from loop_guard import MAX_AGE_MINUTES, last_engine_call, project_root


def main() -> int:
    stdin = sys.stdin.read()
    try:
        base = subprocess.run(
            ["aidlc", "engine", "statusline"],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        base = ""
    last = last_engine_call(project_root())
    if last is None:
        print(base)
        return 0
    age = (time.time() - last) / 60
    note = f"engine asked {age:.0f}m ago"
    if age > MAX_AGE_MINUTES:
        note = f"⚠ {note}: work is off the AI-DLC loop"
    print(f"{base} · {note}" if base else note)
    return 0


_ = glob
if __name__ == "__main__":
    raise SystemExit(main())
