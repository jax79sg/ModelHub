"""Artifactory's naming rules for Hugging Face repositories (rule BR1.2, FR1.7).

Organisation: letters, numbers and single hyphens, not starting or ending with a hyphen, not only
digits. Model: letters, numbers, hyphen, underscore and period. Revision: here always the full
40-character commit hash.
"""

from __future__ import annotations

import re

_ORG = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_MODEL = re.compile(r"^[A-Za-z0-9._-]+$")
_COMMIT = re.compile(r"^[0-9a-fA-F]{40}$")


def validate_names(model_id: str, commit: str) -> str | None:
    """A plain-words problem naming the field and the rule, or None when all is well."""
    org, _, model = (model_id or "").partition("/")
    if "/" not in (model_id or "") or not _ORG.match(org) or org.isdigit():
        return (
            f"organisation {org!r}: use letters, numbers and single hyphens; not starting or "
            "ending with a hyphen; not only digits"
        )
    if not _MODEL.match(model):
        return f"model {model!r}: use letters, numbers, hyphen, underscore and period"
    if not _COMMIT.match(commit or ""):
        return f"revision {commit!r}: must be the full 40-character commit hash"
    return None
