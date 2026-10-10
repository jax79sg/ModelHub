"""Make an offline install pack: this tool and everything it needs, as wheel files, for the
system and Python version this runs on (for computers that have Python but no internet).

Usage:   python packaging/offline_pack.py [output-folder]
Install: pip install --no-index --find-links <folder> modelhub
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pack_name(system: str | None = None, python: str | None = None) -> str:
    system = (system or platform.system()).lower()
    python = python or f"{sys.version_info.major}.{sys.version_info.minor}"
    return f"modelhub-pack-{system}-py{python}"


def command_for(out_dir: Path) -> list[str]:
    return [sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(out_dir), str(ROOT)]


def main(argv: list[str]) -> int:
    out_dir = Path(argv[0]) if argv else ROOT / "dist" / pack_name()
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(command_for(out_dir), check=True)
    print(f"offline pack in {out_dir} ({len(list(out_dir.glob('*.whl')))} wheel files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
