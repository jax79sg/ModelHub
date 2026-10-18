"""Search the logs of every container for any secret value (NFR5.1).

    python3 check_logs.py <secrets folder> <log file>

Every file in the secrets folder is a secret. A one-line secret is searched whole; a multi-line
one (a key) is searched line by line, leaving out the BEGIN and END lines. Values shorter than
8 characters are left out (they would match ordinary text). The answer names the secret's file,
never its value. Exit status: 0 nothing found, 1 a secret was found, 2 a folder or file is missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

MIN_LENGTH = 8


def needles(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("-----")]
    return [line for line in lines if len(line) >= MIN_LENGTH]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(__doc__ or "")
        return 2
    folder, logfile = Path(argv[0]), Path(argv[1])
    if not folder.is_dir() or not logfile.is_file():
        sys.stderr.write("check_logs: the secrets folder or the log file is missing\n")
        return 2
    logs = logfile.read_text(encoding="utf-8", errors="replace")
    found = []
    searched = 0
    for secret in sorted(folder.iterdir()):
        if not secret.is_file():
            continue
        values = needles(secret.read_text(encoding="utf-8", errors="replace"))
        if values:
            searched += 1
        if any(value in logs for value in values):
            found.append(secret.name)
    if found:
        sys.stdout.write("A secret is in the logs: " + ", ".join(found) + "\n")
        return 1
    sys.stdout.write(f"No secret found in the logs ({searched} secrets searched).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
