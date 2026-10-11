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


def run(program, args, home, cwd, stdin=None, expect=0):
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
    if result.returncode != expect:
        raise SystemExit(
            f"FAILED (exit {result.returncode}, wanted {expect}): modelhub {' '.join(args)}"
        )
    return result.stdout + result.stderr


COMMANDS = ["pull", "bundle", "verify", "unpack", "list", "key"]
KEY_COMMANDS = ["create", "export", "fingerprint", "trust", "untrust", "list"]


def expect_text(output, text, what):
    if text not in output:
        raise SystemExit(f"FAILED: {what}: expected {text!r} in the output:\n{output}")


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    program = Path(argv[0]).resolve()
    model = argv[1] if len(argv) == 2 else DEFAULT_MODEL
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        online, airgap, stranger = root / "online-home", root / "airgap-home", root / "other-home"

        # every command answers --version and --help
        expect_text(run(program, ["--version"], online, root), "modelhub", "--version")
        run(program, ["--help"], online, root)
        for name in COMMANDS:
            run(program, [name, "--help"], online, root)
        for name in KEY_COMMANDS:
            run(program, ["key", name, "--help"], online, root)

        # keys: a key can be named by its id, its fingerprint, with or without dashes
        out = run(program, ["key", "create"], online, root)
        key_id = re.search(r"Created key (\w+)", out).group(1)
        fingerprint = re.search(r"Fingerprint: (\S+)", out).group(1)
        expect_text(run(program, ["key", "list"], online, root), fingerprint, "key list")
        for name in (key_id, fingerprint, fingerprint.replace("-", ""), fingerprint.upper()):
            expect_text(run(program, ["key", "fingerprint", name], online, root), fingerprint, name)
        public = root / "public.key"
        for name in (key_id, fingerprint):
            public.unlink(missing_ok=True)
            run(program, ["key", "export", name, "--out", str(public)], online, root)
        wrong = run(
            program, ["key", "export", "no-such-key", "--out", str(public)], online, root, expect=1
        )
        expect_text(wrong, "no key matches", "unknown key")

        # trust needs the right fingerprint; a bundle from an untrusted key is refused
        run(program, ["key", "trust", str(public)], airgap, root, stdin="0000-0000\n", expect=1)

        # pull: with no type nothing is downloaded and the types are shown
        shown = run(program, ["pull", model, "--work", str(root / "preview")], online, root)
        expect_text(shown, "kinds of files", "file types listed")
        if (root / "preview").exists() and any(p.is_file() for p in (root / "preview").rglob("*")):
            raise SystemExit("FAILED: pull without --type downloaded files")
        run(
            program,
            ["pull", "no-such-org/no-such-model-xyz", "--type", "all"],
            online,
            root,
            expect=1,
        )
        run(program, ["pull", model, "--type", "all", "--work", str(root / "pulled")], online, root)
        record = next((root / "pulled" / "models").rglob("manifest.json")).parent
        run(program, ["pull", model, "--type", "all", "--work", str(root / "pulled")], online, root)

        # bundle (named by fingerprint), then the air-gapped side
        run(program, ["bundle", str(record), "--out", str(root / "drive"), "--piece-size", "5MB",
                      "--key", fingerprint], online, root)  # fmt: skip
        untrusted = run(program, ["verify", str(root / "drive")], airgap, root, expect=1)
        expect_text(untrusted.lower(), "trust", "bundle from an untrusted key")
        run(
            program,
            ["unpack", str(root / "drive"), "--store", str(root / "store")],
            airgap,
            root,
            expect=1,
        )
        if (root / "store" / "models").exists() and any(
            (root / "store" / "models").rglob("*.json")
        ):
            raise SystemExit("FAILED: an untrusted bundle left files in the store")

        run(program, ["key", "trust", str(public)], airgap, root, stdin=fingerprint + "\n")
        run(program, ["verify", str(root / "drive")], airgap, root)

        # a damaged piece is named and fails the check; the repaired one passes
        piece = min((root / "drive").glob("*.part-*"))
        good = piece.read_bytes()
        piece.write_bytes(good[:100] + bytes([good[100] ^ 1]) + good[101:])
        bad = run(program, ["verify", str(root / "drive")], airgap, root, expect=1)
        expect_text(bad, piece.name, "damaged piece named")
        piece.write_bytes(good)

        run(program, ["unpack", str(root / "drive"), "--store", str(root / "store")], airgap, root)
        run(program, ["unpack", str(root / "drive"), "--store", str(root / "store")], airgap, root)
        listing = run(program, ["list", str(root / "store")], airgap, root)
        expect_text(listing, model, "list")
        run(program, ["verify", str(root / "store")], airgap, root)

        # untrusting by fingerprint stops further bundles being accepted
        expect_text(
            run(program, ["key", "untrust", fingerprint], airgap, root), "Removed", "untrust"
        )
        run(program, ["verify", str(root / "drive")], airgap, root, expect=1)
        run(program, ["list", str(root / "store")], stranger, root)
    print("round trip passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
