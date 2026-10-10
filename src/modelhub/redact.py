"""Keep access tokens out of every message, log and record (NFR6.1)."""

from __future__ import annotations

import os
import re

HIDDEN = "[token hidden]"
_TOKEN_SHAPE = re.compile(r"hf_[A-Za-z0-9]{10,}")
_BEARER = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)
_known: set[str] = set()


def remember(secret: str | None) -> None:
    """Also hide a token that was typed at a prompt and so is not in the environment."""
    if secret and len(secret) >= 4:
        _known.add(secret)


def redact(text: str) -> str:
    secrets = set(_known)
    env = os.environ.get("HF_TOKEN")
    if env and len(env) >= 4:
        secrets.add(env)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, HIDDEN)
    text = _TOKEN_SHAPE.sub(HIDDEN, text)
    return _BEARER.sub(lambda m: m.group(1) + HIDDEN, text)
