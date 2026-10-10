"""Naming and sizing of bundle pieces (contract C2)."""

from __future__ import annotations

import re

MIN_PIECE_SIZE = 1024  # the smallest piece size accepted; far below 1 GB (FR6.4)
MAX_PIECES = 999_999  # piece numbers have six digits (NFR1.10)

_UNITS = {
    "b": 1,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
}
_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*$")


def parse_size(text: str) -> int:
    """'900MB' -> 900_000_000. KB, MB, GB are decimal like drive makers; KiB, MiB, GiB are binary."""
    match = _SIZE.match(text)
    if not match:
        raise ValueError(f"cannot read a size from {text!r}; try 900MB or 1.5GB")
    number, unit = match.groups()
    factor = _UNITS.get((unit or "b").lower())
    if factor is None:
        raise ValueError(f"unknown size unit {unit!r}; use KB, MB, GB, KiB, MiB or GiB")
    return int(float(number) * factor)


def stem_for(model_id: str, commit: str) -> str:
    return f"{model_id.replace('/', '--')}--{commit[:12]}"


def piece_name(stem: str, index: int) -> str:
    return f"{stem}.part-{index:06d}"
