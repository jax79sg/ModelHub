"""A secret value that cannot be printed (rule BR1.6)."""

from __future__ import annotations

MASK = "[secret]"


class Secret:
    """Holds a secret. Printing, formatting and logging show a fixed mask; only ``reveal`` gives
    the value, and only at the point of use."""

    __slots__ = ("_value", "name")

    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __str__(self) -> str:
        return MASK

    def __repr__(self) -> str:
        return f"Secret({self.name!r}, {MASK})"

    def __format__(self, spec: str) -> str:
        return MASK

    def __reduce__(self):  # no pickling of the value into logs or caches
        raise TypeError("a Secret cannot be pickled")
