"""Drive a finished program file through the whole workflow, the way a person would.

Usage:   python packaging/roundtrip_smoke.py dist/modelhub-linux-x86_64 [org/name]

Two separate key folders stand in for the two sides. The program runs with a scrubbed environment
(nothing from this Python installation). The pull step needs the internet; the rest does not.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_MODEL = "prajjwal1/bert-tiny"  # a small public model, about 17 MB


def run(program, args, home, cwd, stdin=None):
    keep = ("SYSTEMROOT", "TEMP", "TMP", "LANG", "HOME", "USERPROFILE")
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env["PATH"] = os.devnull
    env["MODELHUB_HOME"] = str(home)
    result = subprocess.run(
        [str(program), *args],
        env=env,
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"$ modelhub {' '.join(args)}\n{result.stdout}{result.stderr}")
    if result.returncode != 0:
        raise SystemExit(f"FAILED (exit {result.returncode}): modelhub {' '.join(args)}")
    return result.stdout


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    program = Path(argv[0]).resolve()
    model = argv[1] if len(argv) == 2 else DEFAULT_MODEL
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        online, airgap = root / "online-home", root / "airgap-home"
        out = run(program, ["key", "create"], online, root)
        key_id = re.search(r"Created key (\w+)", out).group(1)
        fingerprint = re.search(r"Fingerprint: (\S+)", out).group(1)
        public = root / "public.key"
        run(program, ["key", "export", key_id, "--out", str(public)], online, root)
        run(program, ["key", "trust", str(public)], airgap, root, stdin=fingerprint + "\n")
        run(program, ["pull", model, "--type", "all", "--work", str(root / "pulled")], online, root)
        record = next((root / "pulled" / "models").rglob("manifest.json")).parent
        run(program, ["bundle", str(record), "--out", str(root / "drive"), "--piece-size", "5MB",
                      "--key", key_id], online, root)  # fmt: skip
        run(program, ["verify", str(root / "drive")], airgap, root)
        run(program, ["unpack", str(root / "drive"), "--store", str(root / "store")], airgap, root)
        listing = run(program, ["list", str(root / "store")], airgap, root)
        run(program, ["verify", str(root / "store")], airgap, root)
        if model not in listing:
            raise SystemExit(f"FAILED: {model} not in the list")
    print("round trip passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
