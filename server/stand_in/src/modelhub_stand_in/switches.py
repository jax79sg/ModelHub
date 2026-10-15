"""Failure switches: instructions from a test to misbehave on purpose (rule BR1.10)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

KINDS = (
    "unauthorised",
    "forbidden",
    "conflict",
    "name-refused",
    "server-error",
    "slow",
    "cut-transfer",
    "half-version",
)
SCOPES = (
    "any-call",
    "upload-calls",
    "large-file-batch",
    "commit",
    "listing",
    "fetch",
    "delete",
)
# the call groups each scope covers
_GROUPS = {
    "upload-calls": {"create", "preupload", "large-file-batch", "large-file-upload", "commit"},
    "large-file-batch": {"large-file-batch"},
    "commit": {"commit"},
    "listing": {"listing"},
    "fetch": {"fetch"},
    "delete": {"delete"},
}


@dataclass
class Switch:
    kind: str
    scope: str = "any-call"
    after_calls: int = 0
    times: int = 1
    sticky: bool = False
    seconds: float = 1.0
    seen: int = 0
    fired: int = 0
    id: int = 0
    note: dict = field(default_factory=dict)

    def matches(self, group: str) -> bool:
        return self.scope == "any-call" or group in _GROUPS.get(self.scope, set())


class SwitchTable:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._switches: list[Switch] = []
        self._next_id = 1

    def add(self, kind: str, **kw) -> Switch:
        if kind not in KINDS:
            raise ValueError(f"unknown failure kind {kind!r}")
        scope = kw.get("scope", "any-call")
        if scope not in SCOPES:
            raise ValueError(f"unknown scope {scope!r}")
        with self._lock:
            switch = Switch(kind=kind, id=self._next_id, **kw)
            self._next_id += 1
            self._switches.append(switch)
            return switch

    def clear(self) -> None:
        with self._lock:
            self._switches.clear()

    def check(self, group: str) -> Switch | None:
        """The switch that fires on this call, if any. Counts every matching call."""
        with self._lock:
            for switch in self._switches:
                if not switch.matches(group):
                    continue
                switch.seen += 1
                if switch.seen <= switch.after_calls:
                    continue
                switch.fired += 1
                if not switch.sticky and switch.fired >= switch.times:
                    self._switches.remove(switch)
                return switch
        return None

    def listing(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": s.id,
                    "kind": s.kind,
                    "scope": s.scope,
                    "after_calls": s.after_calls,
                    "times": s.times,
                    "sticky": s.sticky,
                }
                for s in self._switches
            ]
