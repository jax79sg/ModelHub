"""One retry helper: five retries at 1, 2, 4, 8 and 16 seconds, each with a little random extra
wait of up to one second (rule BR1.7, FR1.9). Only the errors named are retried."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

RETRY_WAITS = (1, 2, 4, 8, 16)


def retrying(
    fn: Callable,
    retry_on: tuple[type[BaseException], ...],
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
):
    """Call ``fn``; on one of ``retry_on`` wait and call it again, up to five more times."""
    for wait in RETRY_WAITS:
        try:
            return fn()
        except retry_on:
            sleep(wait + jitter())
    return fn()
