"""Build the single program file for this operating system (plan step 34, decision T8).

Usage:   python packaging/build.py pyinstaller   (or: nuitka)

A program file can only be built on the system it will run on, so run this once on Linux and
once on Windows. For Linux, build on the oldest system the program must run on (RHEL 8 or
Ubuntu 20.04), so it does not need a newer system library than that system has (NFR7.2).
The build tools are an optional extra: pip install -e ".[build]"
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "packaging" / "entry.py"
# Parts with compiled code that the build tools do not always find by themselves.
NATIVE_PARTS = ("hf_xet", "cryptography")

_MACHINES = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}


def artifact_name(system: str | None = None, machine: str | None = None) -> str:
    system = (system or platform.system()).lower()
    machine = _MACHINES.get((machine or platform.machine()).lower(), (machine or "").lower())
    return f"modelhub-{system}-{machine}" + (".exe" if system == "windows" else "")


def command_for(tool: str, out_dir: Path) -> list[str]:
    name = artifact_name()
    out_dir = Path(out_dir)
    if tool == "pyinstaller":
        command = [
            sys.executable, "-m", "PyInstaller", "--onefile", "--noconfirm", "--clean",
            "--name", name,
            "--distpath", str(out_dir),
            "--workpath", str(out_dir / "work"),
            "--specpath", str(out_dir / "spec"),
            "--collect-submodules", "modelhub",
            "--copy-metadata", "huggingface_hub",
        ]  # fmt: skip
        for part in NATIVE_PARTS:
            command += ["--collect-all", part]
        return [*command, str(ENTRY)]
    if tool == "nuitka":
        command = [
            sys.executable, "-m", "nuitka", "--onefile", "--assume-yes-for-downloads",
            f"--output-filename={name}",
            f"--output-dir={out_dir}",
            "--include-package=modelhub",
            "--include-package-data=huggingface_hub",
        ]  # fmt: skip
        for part in NATIVE_PARTS:
            command.append(f"--include-package={part}")
        return [*command, str(ENTRY)]
    raise ValueError(f"unknown build tool {tool!r}; use pyinstaller or nuitka")


def smoke_check(program: Path, env: dict | None = None) -> str:
    """Run the finished file the way a computer with no Python would: a scrubbed environment,
    with nothing from this Python installation leaking in. Returns what `--version` printed."""
    source = os.environ if env is None else env
    keep = ("SYSTEMROOT", "HOME", "TEMP", "TMP", "LANG")
    clean = {key: source[key] for key in keep if key in source}
    clean["PATH"] = os.devnull
    result = subprocess.run(
        [str(program), "--version"], env=clean, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def build(tool: str, out_dir: Path | None = None) -> Path:
    out_dir = Path(out_dir or ROOT / "dist")
    subprocess.run(command_for(tool, out_dir), check=True, cwd=ROOT)
    return out_dir / artifact_name()


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    program = build(argv[0])
    print(f"built {program}")
    print(f"smoke check: {smoke_check(program)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
