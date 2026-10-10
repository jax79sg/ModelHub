"""The run record: what a command fetched, skipped and failed (FR9.2, NFR8.3).

Written beside the output, as JSON with a format version. It never holds a secret (NFR6.1).
"""

from __future__ import annotations

import json
import platform
from collections import Counter
from pathlib import Path

from modelhub import __version__, redact
from modelhub.fsutil import atomic_write_text
from modelhub.record import utc_now

FORMAT_VERSION = "1.0"


class RunRecord:
    def __init__(self, command: str, now=utc_now):
        self.command = command
        self._now = now
        self.started_at = now()
        self.items: list[dict] = []

    def add(self, model: str, status: str, name: str | None = None, **info) -> None:
        item = {"model": model, "status": status}
        if name is not None:
            item["name"] = name
        item.update({k: v for k, v in info.items() if v is not None})
        self.items.append(item)

    def document(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "tool_version": __version__,
            "command": self.command,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "started_at": self.started_at,
            "finished_at": self._now(),
            "summary": dict(Counter(item["status"] for item in self.items)),
            "items": self.items,
        }

    def write(self, path: Path) -> Path:
        text = redact.redact(json.dumps(self.document(), indent=2)) + "\n"
        atomic_write_text(Path(path), text)
        return Path(path)
