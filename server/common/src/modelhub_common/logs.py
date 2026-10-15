"""Structured logs on standard output, with secrets redacted (rules BR1.8, BR1.9)."""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone

from .secrets import Secret

REDACTED = "[redacted]"
_SECRET_NAME = re.compile(r"token|password|secret|pepper|authorization|cookie", re.IGNORECASE)
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_STANDARD = set(logging.LogRecord("n", 0, "p", 0, "m", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}
_FIXED = ("event", "requestId", "person")


def valid_request_id(value: str | None) -> bool:
    return bool(value) and bool(_REQUEST_ID.match(value))


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, secrets: Iterable[Secret] = ()) -> None:
        super().__init__()
        self.service = service
        self._secrets = [s for s in secrets]

    def _mask(self, text: str) -> str:
        for secret in self._secrets:
            value = secret.reveal()
            if value:
                text = text.replace(value, REDACTED)
        return text

    def _clean(self, value):
        if isinstance(value, str):
            return self._mask(value)
        if isinstance(value, Secret):
            return REDACTED
        if isinstance(value, bool | int | float) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): self._clean_named(str(k), v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [self._clean(v) for v in value]
        return self._mask(str(value))

    def _clean_named(self, name: str, value):
        if _SECRET_NAME.search(name):
            return REDACTED
        return self._clean(value)

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message += " | " + self.formatException(record.exc_info).replace("\n", " | ")
        line = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": self.service,
            "event": getattr(record, "event", "log"),
            "message": self._mask(message),
        }
        for name in _FIXED[1:]:
            value = getattr(record, name, None)
            if value is not None:
                line[name] = self._clean(value)
        for name, value in record.__dict__.items():
            if name in _STANDARD or name in _FIXED:
                continue
            line[name] = self._clean_named(name, value)
        return json.dumps(line, ensure_ascii=False, default=str)


def configure_logging(
    service: str, level: str = "info", secrets: Iterable[Secret] = ()
) -> logging.Logger:
    """Send all ``modelhub`` logs to standard output as JSON lines."""
    logger = logging.getLogger("modelhub")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service, secrets))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger
