"""The live and ready checks (rules BR1.10, BR1.11).

The live check answers 200 whenever the process can answer. The ready check runs the checks a
service registered, each at most once every 10 seconds and with a 2-second limit (a hang or an
error counts as down), and says 503 only when a critical check is down or no signing keys are
loaded. The answer holds check names and results only, never a message from a dependency.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from .keys import KeyState

CACHE_SECONDS = 10
CHECK_TIMEOUT_SECONDS = 2


@dataclass
class HealthCheck:
    name: str
    fn: Callable[[], bool | None]
    critical: bool = False
    timeout: float = CHECK_TIMEOUT_SECONDS
    cache_seconds: float = CACHE_SECONDS
    _result: str | None = field(default=None, repr=False)
    _at: float | None = field(default=None, repr=False)


class HealthRegistry:
    def __init__(
        self, checks: Sequence[HealthCheck], clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._checks = list(checks)
        self._clock = clock
        self._pool = ThreadPoolExecutor(max_workers=max(1, len(self._checks)))

    def _run(self, check: HealthCheck) -> str:
        now = self._clock()
        fresh = check._at is not None and now - check._at < check.cache_seconds
        if fresh and check._result is not None:
            return check._result
        future = self._pool.submit(check.fn)
        try:
            outcome = future.result(timeout=check.timeout)
            result = "down" if outcome is False else "ok"
        except (FutureTimeout, Exception):  # noqa: BLE001 - any failure of a check means down
            result = "down"
        check._result, check._at = result, now
        return result

    def ready(self, key_state: KeyState) -> tuple[int, dict]:
        results = {c.name: self._run(c) for c in self._checks}
        critical_down = any(c.critical and results[c.name] == "down" for c in self._checks)
        if critical_down or key_state is KeyState.EMPTY:
            return 503, {"status": "down", "checks": results}
        if any(r == "down" for r in results.values()):
            return 200, {"status": "degraded", "checks": results}
        return 200, {"status": "ok", "checks": results}
