"""Secrets and settings, read once at start-up (rules BR1.6, BR1.7, BR1.12).

Every missing or wrong item is collected and reported together, by name and expected type only,
never by value, and the service then stops.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .secrets import Secret

DEFAULT_SECRETS_DIR = "/run/secrets"
SECRETS_DIR_ENV = "MODELHUB_SECRETS_DIR"


class StartupError(Exception):
    """The service cannot start: ``problems`` lists the names (never values) that are wrong."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__("cannot start: " + "; ".join(self.problems))


@dataclass(frozen=True)
class Setting:
    name: str
    type: type = str
    default: Any = None
    required: bool = False
    minimum: float | None = None
    exclusive: bool = False


SHARED_SETTINGS = [
    Setting("MODELHUB_REALM_ISSUER", str, required=True),
    Setting("MODELHUB_AUDIENCE", str, default="modelhub"),
    Setting("MODELHUB_JWKS_URL", str, default=""),
    Setting("MODELHUB_LOG_LEVEL", str, default="info"),
    Setting("MODELHUB_CONNECT_TIMEOUT", float, default=5, minimum=0, exclusive=True),
    Setting("MODELHUB_READ_TIMEOUT", float, default=30, minimum=0, exclusive=True),
    Setting("MODELHUB_PIECE_UPLOAD_TIMEOUT", float, default=600, minimum=0, exclusive=True),
]

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _convert(spec: Setting, raw: str) -> Any:
    if spec.type is bool:
        low = raw.strip().lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
        raise ValueError
    value = spec.type(raw)
    if spec.minimum is not None and (
        value <= spec.minimum if spec.exclusive else value < spec.minimum
    ):
        raise ValueError
    return value


def _settings(specs: Sequence[Setting], environ: Mapping[str, str]) -> tuple[dict, list[str]]:
    values: dict[str, Any] = {}
    problems: list[str] = []
    for spec in specs:
        raw = environ.get(spec.name)
        if raw is None or raw == "":
            if spec.required:
                problems.append(f"setting {spec.name} is missing ({spec.type.__name__})")
            else:
                values[spec.name] = spec.default
            continue
        try:
            values[spec.name] = _convert(spec, raw)
        except (ValueError, TypeError):
            problems.append(f"setting {spec.name} is not a valid {spec.type.__name__}")
    return values, problems


def _secrets(
    names: Sequence[str], directory: Path | str | None, environ: Mapping[str, str]
) -> tuple[dict[str, Secret], list[str]]:
    base = Path(directory or environ.get(SECRETS_DIR_ENV) or DEFAULT_SECRETS_DIR)
    found: dict[str, Secret] = {}
    problems: list[str] = []
    for name in names:
        if "/" in name or "\\" in name or name in ("", ".", ".."):
            problems.append(f"secret {name!r} has an unsafe name")
            continue
        path = base / name
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            problems.append(f"secret {name} is missing")
            continue
        except (OSError, UnicodeDecodeError):
            problems.append(f"secret {name} cannot be read")
            continue
        text = text.removesuffix("\n")
        if not text:
            problems.append(f"secret {name} is empty")
            continue
        found[name] = Secret(name, text)
    return found, problems


def load_secrets(
    names: Sequence[str],
    directory: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Secret]:
    found, problems = _secrets(names, directory, environ if environ is not None else os.environ)
    if problems:
        raise StartupError(problems)
    return found


def load_config(
    settings: Sequence[Setting],
    secret_names: Sequence[str],
    environ: Mapping[str, str] | None = None,
    directory: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Secret]]:
    env = environ if environ is not None else os.environ
    values, problems = _settings(settings, env)
    found, secret_problems = _secrets(secret_names, directory, env)
    if problems or secret_problems:
        raise StartupError(problems + secret_problems)
    return values, found
