"""Verbose and debug logging to a file beside the output, with times in UTC (NFR8.4)."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from modelhub import redact

NAME = "modelhub"
_handler: logging.Handler | None = None


class _Formatter(logging.Formatter):
    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        return redact.redact(super().format(record))


def start(level: str | None, folder: Path) -> Path | None:
    """Begin logging to `folder/modelhub.log`. `level` is 'verbose', 'debug' or None (no log)."""
    global _handler
    stop()
    if level is None:
        return None
    logger = logging.getLogger(NAME)
    logger.setLevel(logging.DEBUG if level == "debug" else logging.INFO)
    logger.propagate = False
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = Path(folder) / "modelhub.log"
    _handler = logging.FileHandler(path, encoding="utf-8")
    _handler.setFormatter(_Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S"))
    logger.addHandler(_handler)
    return path


def stop() -> None:
    global _handler
    if _handler is not None:
        logging.getLogger(NAME).removeHandler(_handler)
        _handler.close()
        _handler = None
