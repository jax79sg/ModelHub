"""Name, path and revision rules (rules BR1.2, BR1.4, BR1.15).

The naming rules are JFrog's documented ones for Hugging Face repositories; the answers the
stand-in gives when they are broken are an assumption (see the assumption register).
"""

from __future__ import annotations

import hashlib
import re

_ORG = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_MODEL = re.compile(r"^[A-Za-z0-9._-]+$")
_REVISION = re.compile(r"^[A-Za-z0-9.-]+$")
_HASH = re.compile(r"^[0-9a-fA-F]{40}$")
_DRIVE = re.compile(r"^[A-Za-z]:")


def validate_names(organisation: str, model: str, revision: str) -> str | None:
    """Return a readable problem, or None when all three names follow the rules."""
    if not _ORG.match(organisation or "") or organisation.isdigit():
        return (
            "organisation: use letters, numbers and single hyphens, not starting or ending "
            "with a hyphen, and not only digits"
        )
    if not _MODEL.match(model or ""):
        return "model: use letters, numbers, hyphen, underscore and period"
    if not _REVISION.match(revision or ""):
        return "revision: use letters, numbers, hyphen and period"
    return None


def is_commit_hash(value: str) -> bool:
    return bool(_HASH.match(value or ""))


def commit_hash(files: list[tuple[str, str]]) -> str:
    """SHA-1 of the sorted '<path> <sha256>' lines of a version's files, as 40 hex characters."""
    text = "\n".join(f"{path} {sha}" for path, sha in sorted(files))
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()


def safe_relative_path(path: str) -> bool:
    """False for an empty, absolute, drive-lettered, backslashed or escaping path."""
    if not path or path.startswith("/") or "\\" in path or _DRIVE.match(path):
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") for part in parts)
