"""Live progress for long steps, so nobody thinks the tool has hung (NFR1.5).

On a terminal the display changes at least every 2 seconds. When output goes to a file or a
pipe, a plain line is written at least every 30 seconds. A step shorter than 2 seconds shows
nothing at all.
"""

from __future__ import annotations

import contextlib
import sys
import threading
import time

from modelhub import redact


def human_bytes(count: float) -> str:
    if count < 1000:
        return f"{int(count)} B"
    value = float(count)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1000
        if value < 1000 or unit == "TB":
            return f"{value:.1f} {unit}"
    return f"{count} B"


def human_duration(seconds: float) -> str:
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60} s"
    return f"{seconds // 3600} h {seconds % 3600 // 60} min"


class NullReporter:
    """Accepts every call and shows nothing; the default when no display is wanted."""

    bytes_done = 0

    def start(self, label, total_bytes=None, total_items=None) -> None:
        pass

    def advance(self, nbytes=0, item=None, item_done=False) -> None:
        pass

    def tick(self) -> None:
        pass

    def message(self, text) -> None:
        pass

    def finish(self) -> None:
        pass

    @contextlib.contextmanager
    def running(self):
        yield self


class Reporter(NullReporter):
    def __init__(
        self,
        out=None,
        is_tty: bool | None = None,
        clock=time.monotonic,
        tty_interval: float = 2.0,
        log_interval: float = 30.0,
        quiet_under: float = 2.0,
    ):
        self.out = out if out is not None else sys.stderr
        self.is_tty = self.out.isatty() if is_tty is None else is_tty
        self.clock = clock
        self.interval = tty_interval if self.is_tty else log_interval
        self.first_after = max(quiet_under, self.interval)
        self._lock = threading.RLock()
        self._reset("")

    def _reset(self, label: str) -> None:
        self.label = label
        self.total_bytes: int | None = None
        self.total_items: int | None = None
        self.bytes_done = 0
        self.items_done = 0
        self.current: str | None = None
        self._started = self.clock() if hasattr(self, "clock") else 0.0
        self._last_emit: float | None = None
        self._line_open = False
        self._emitted = False

    def start(self, label, total_bytes=None, total_items=None) -> None:
        with self._lock:
            self._reset(label)
            self.total_bytes, self.total_items = total_bytes, total_items

    def advance(self, nbytes=0, item=None, item_done=False) -> None:
        with self._lock:
            self.bytes_done += nbytes
            if item:
                self.current = item
            if item_done:
                self.items_done += 1
            self._maybe_emit()

    def tick(self) -> None:
        with self._lock:
            self._maybe_emit()

    def _maybe_emit(self) -> None:
        now = self.clock()
        elapsed = now - self._started
        if self._last_emit is None:
            if elapsed < self.first_after:
                return
        elif now - self._last_emit < self.interval:
            return
        self._last_emit = now
        line = redact.redact(self._line(elapsed))
        if self.is_tty:
            self.out.write("\r" + line.ljust(79))
            self._line_open = True
        else:
            self.out.write(line + "\n")
        self.out.flush()
        self._emitted = True

    def _line(self, elapsed: float) -> str:
        rate = self.bytes_done / elapsed if elapsed > 0 else 0.0
        parts = [self.label]
        if self.total_bytes:
            percent = min(100, int(self.bytes_done * 100 / self.total_bytes))
            parts.append(
                f"{human_bytes(self.bytes_done)} of {human_bytes(self.total_bytes)} ({percent}%)"
            )
        else:
            parts.append(human_bytes(self.bytes_done))
        if rate > 0:
            parts.append(f"{human_bytes(rate)}/s")
            if self.total_bytes and self.bytes_done < self.total_bytes:
                left = (self.total_bytes - self.bytes_done) / rate
                parts.append(f"about {human_duration(left)} left")
        if self.total_items:
            parts.append(f"file {self.items_done}/{self.total_items}")
        if self.current:
            parts.append(f"now: {self.current}")
        return ", ".join(parts)

    def message(self, text) -> None:
        with self._lock:
            if self._line_open:
                self.out.write("\r" + " " * 79 + "\r")
                self._line_open = False
            self.out.write(redact.redact(str(text)) + "\n")
            self.out.flush()

    def finish(self) -> None:
        with self._lock:
            if self._line_open:
                self.out.write("\n")
                self.out.flush()
                self._line_open = False

    @contextlib.contextmanager
    def running(self):
        """Keep the display alive while work is in progress, even if no bytes are arriving."""
        stop = threading.Event()

        def beat() -> None:
            while not stop.wait(min(0.5, self.interval / 4)):
                self.tick()

        thread = threading.Thread(target=beat, daemon=True)
        thread.start()
        try:
            yield self
        finally:
            stop.set()
            thread.join(timeout=2)
            self.finish()
